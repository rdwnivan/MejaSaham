"""Tindakan yang **menulis** dari jendela (aksi #19, K55/K59/T69) — bebas Qt.

Kenapa berkas ini terpisah dari widget-nya:

* **Bisa diuji tanpa layar.** Isi ringkasan konfirmasi, kelengkapan isian, dan **baris apa yang
  ditulis** tidak butuh platform grafis; yang butuh hanya tombol dan dialognya. Karena itu
  komposisinya tinggal di sini dan diuji `tests/test_ui_tulis.py`.
* **Satu jalur tulis.** Setiap permintaan memanggil fungsi inti yang **sama** dengan baris
  perintah (`posisi.catat_transaksi`, `risiko.simpan_dari_kandidat`, `jurnal.catat`) — bukan
  pernyataan SQL kedua. Jendela yang menulis lewat jalur sendiri akan berbeda dari baris
  perintah begitu salah satunya disunting, dan yang berbeda adalah catatan keputusan yang
  tidak bisa dihapus (append-only).
* **Angka di ringkasan = angka yang ditulis.** Ringkasan konfirmasi (K59 d) disusun dari objek
  yang sama yang diserahkan ke fungsi intinya, bukan dari isian formulir yang dibaca ulang.
* **"Belum menulis apa pun" itu janji, bukan hiasan.** Kunci tulis diambil di muka
  (`db.tulis` → `BEGIN IMMEDIATE`), jadi kegagalan karena terkunci berarti **tidak satu baris
  pun** tersimpan — dan itulah yang dikatakan pesannya (K59 b).

Yang ada di sini sejak aksi #19b: **impor berkas** (K59 c). Ia memakai dua tahap — baca folder
lebih dulu, baru konfirmasi — sebab ringkasan konfirmasinya wajib memuat jumlah baris per tabel,
dan angka itu baru ada sesudah foldernya dibaca. Yang ditulis adalah **objek hasil bacaan yang
sama** dengan yang dikonfirmasi (`pengatur.jalankan_impor(sudah_dibaca=…)`), jadi yang tertulis
tidak bisa berbeda dari yang disetujui pengguna.

Yang ada di sini sejak aksi #19c: **cadangan + daftar cadangan** (F12, K59 c/e). Cadangan tidak
menulis baris apa pun — ia membaca basis data dan menyalinnya keluar — jadi janjinya berbeda dari
pencatat: `KALIMAT_BASIS_TIDAK_DISENTUH`, bukan `KALIMAT_BELUM_MENULIS`, dan pertanyaan penutup
dialognya pun bukan "tulis baris ini". Folder tujuannya dihitung **sekali**
(`cadangan.folder_tujuan`) dan dipakai konfirmasi **dan** penulisan.

Yang ada di sini sejak aksi #19d: **ubah stop** (layar 11.1) dan **keputusan right issue**
(layar 11.3) — dua tindakan yang dituntut layar dasbor sendiri (`stop_tertembus`, `tanpa_stop`,
`pembatal_terpicu`, `right_issue_belum_diputuskan`), dan sebelumnya hanya bisa dieksekusi dari
baris perintah (K62/T71 c). Dua hal yang mengikat bentuknya: `tgl_stop` datang dari tanggal yang
**dinyatakan pengguna** (basis level stop, PRD 9.11), dan keputusan `tebus` hanya boleh **menunjuk**
transaksi yang sudah tercatat — jendela tidak mencatatkan transaksinya diam-diam (T51).

Yang **belum** ada di sini: `--pulihkan`. Ia menimpa basis data dan menunggu tahap tersendiri
(K59 e) — dan itu disebut di layar, bukan dibiarkan disimpulkan.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mejasaham import (
    berkas,
    cadangan,
    db,
    folder_pantau,
    ingesti,
    jurnal,
    kandidat,
    lokasi,
    notasi,
    pengatur,
    pengumuman_idx,
    posisi,
    potret,
    risiko,
    tampilan,
    unggahan_idx,
)

#: Kalimat yang **wajib** ada pada kegagalan tulis dari jendela (K59 b): pengguna harus tahu
#: tidak ada yang setengah tertulis. Satu sumber, supaya tidak ada dua versi janji yang sama.
KALIMAT_BELUM_MENULIS = (
    "Aplikasi belum menulis apa pun: kunci tulis diambil sebelum baris pertama disimpan."
)

#: Jaminan untuk cadangan (aksi #19c) — **lebih kuat** daripada `KALIMAT_BELUM_MENULIS`, sebab
#: cadangan tidak menulis ke basis data sama sekali: ia hanya membacanya dan menyalinnya keluar.
KALIMAT_BASIS_TIDAK_DISENTUH = (
    "Basis data tidak disentuh sama sekali: cadangan hanya membaca dan menyalinnya keluar."
)

#: Pertanyaan penutup dialog konfirmasi. Bawaannya untuk tindakan yang menulis baris; tindakan
#: yang **tidak** menulis baris (cadangan) menyatakan pertanyaannya sendiri, supaya dialognya
#: tidak menjanjikan sesuatu yang tidak dilakukan.
PERTANYAAN_BAWAAN = "Tulis baris ini ke basis data?"

#: Pertanyaan penutup untuk cadangan: yang dikerjakan adalah menulis **berkas**, bukan baris.
PERTANYAAN_CADANGAN = "Buat cadangan ini sekarang?"

#: Pelanggaran PRD 9.8 **dicatat**, bukan ditolak. Kalimatnya dipakai di layar; yang menentukan
#: perilakunya tetap `posisi.catat_transaksi` (pelanggaran tersimpan di barisnya).
PESAN_PELANGGARAN_DICATAT = (
    "Pelanggaran di atas TERCATAT di barisnya, bukan ditolak (PRD 9.8): kepatuhan dihitung dari "
    "transaksi yang tercatat, dan eksekusi yang sudah terjadi tidak menjadi tidak terjadi karena "
    "aplikasi menolak mencatatnya. Rekapnya di layar Jurnal (11.5)."
)

#: Janji `ubah-stop` (aksi #19d): revisi baru, bukan timpa. Dipakai ringkasan konfirmasi **dan**
#: pesan hasilnya, supaya dua tempat tidak menjanjikan hal yang berbeda.
CATATAN_STOP_REVISI = (
    "Stop tersimpan sebagai revisi baru posisi (append-only): level stop lama tidak ditimpa dan "
    "tetap bisa ditelusuri. Menaikkan stop adalah trailing yang sah (PRD 9.11); menurunkannya "
    "tidak ditolak, tetapi tersimpan sebagai pelanggaran V5 di barisnya (PRD 9.8)."
)

#: Hak right issue dihitung dari rasio × lembar, jadi ia **petunjuk**, bukan angka sekuritas
#: (PRD 9.11). Satu tempat: dipakai tabel hak di layar 11.3 **dan** ringkasan konfirmasinya.
CATATAN_HAK_PETUNJUK = (
    "Hak di atas adalah PETUNJUK yang dihitung dari rasio aksi × lembar yang dipegang pada "
    "tanggal aksi (PRD 9.11) — bukan angka dari sekuritas Anda."
)

#: Janji keputusan `tebus` (T51): lembarnya hanya punya satu tempat — `transaksi`.
CATATAN_TEBUS_MENUNJUK_TRANSAKSI = (
    "Keputusan `tebus` menunjuk transaksi pembelian yang sudah tercatat: lembar posisinya naik "
    "dari transaksi itu, bukan dari keputusan ini — aplikasi TIDAK mencatatkan transaksinya "
    "diam-diam (T51)."
)

#: Janji append-only untuk keputusan right issue; sama bunyinya dengan baris perintah.
CATATAN_KEPUTUSAN_REVISI = (
    "Keputusan tersimpan sebagai baris baru (append-only): keputusan sebelumnya tidak dihapus, "
    "dan revisinya bertambah bila diubah (PRD 9.11)."
)


class GalatTulis(RuntimeError):
    """Isian/kondisi yang membuat penulisan tidak bisa dimulai; pesannya untuk manusia."""


@dataclass(frozen=True)
class HasilTulis:
    """Hasil satu tindakan tulis: berhasil atau tidak, beserta pesannya untuk layar.

    Kegagalan karena kunci tulis **tidak** dilempar sebagai galat: ia keadaan yang bisa
    dikerjakan pengguna (tunggu, lalu coba lagi), dan baris perintah pun melaporkannya sebagai
    pesan + kode keluar gagal — bukan traceback. Galat lain tetap dilempar apa adanya supaya
    jejaknya tercetak dan tidak ada kegagalan yang tertelan (aturan keras 7).
    """

    berhasil: bool
    pesan: str


@dataclass(frozen=True)
class PermintaanTulis:
    """Satu tindakan tulis yang sudah siap dijalankan: judulnya, ringkasannya, pekerjaannya."""

    judul: str
    #: Isi dialog konfirmasi: angka yang akan ditulis (K59 d). Teks siap tampil, bukan widget.
    ringkasan: str
    #: Dijalankan di utas pekerja dengan koneksi yang dibuka di utas itu (T69 b).
    #:
    #: Kembaliannya `str` berarti **berhasil** (pesannya untuk layar). Tindakan yang kegagalannya
    #: berupa **nilai**, bukan galat — impor: `pengatur.LaporanJalan.sukses`; cadangan:
    #: `cadangan.GalatCadangan` — mengembalikan `HasilTulis` sendiri, sebab kegagalan yang sudah
    #: dilaporkan tidak perlu dilempar dan tidak boleh terbaca sebagai berhasil (aturan keras 7).
    jalankan: Callable[[sqlite3.Connection], "str | HasilTulis"]
    #: Pertanyaan penutup dialog konfirmasi (lihat `PERTANYAAN_BAWAAN`). Ditaruh terakhir karena
    #: bidang berdefault tidak boleh mendahului bidang tanpa default di `dataclass`.
    pertanyaan: str = PERTANYAAN_BAWAAN
    #: Apakah layar pemanggilnya perlu dimuat ulang sesudah berhasil (T69 e). Bawaannya **ya**:
    #: penulisan biasanya mengubah baris yang dibaca layar. Cadangan tidak: ia hanya membaca
    #: basis data dan menyalinnya keluar. Terukur 17 Okt 2026 atas basis data 231 MB —
    #: `cadangan.buat` **1,38 dtk**, sedangkan pemuatan ulang dasbor yang dipicunya **64,17 dtk**;
    #: jadi hampir seluruh penantian pengguna sesudah menekan "Cadangan basis data" adalah
    #: hitungan yang tidak berubah.
    muat_ulang: bool = True


def jalankan_permintaan(
    permintaan: PermintaanTulis, sambungan: sqlite3.Connection
) -> HasilTulis:
    """Jalankan satu permintaan tulis; kunci yang gagal menjadi pesan, bukan traceback."""
    try:
        hasil = permintaan.jalankan(sambungan)
    except db.BasisDataTerkunci as galat:
        return HasilTulis(berhasil=False, pesan=f"{galat}\n{KALIMAT_BELUM_MENULIS}")
    if isinstance(hasil, HasilTulis):
        return hasil
    return HasilTulis(berhasil=True, pesan=hasil)


@dataclass(frozen=True)
class PembacaanImpor:
    """Hasil membaca satu folder impor — isinya, atau sebab ia tidak bisa dibaca.

    Kegagalan bentuk berkas (`ingesti.GalatIngesti`) **tidak** dilempar: ia keadaan yang bisa
    dikerjakan pengguna (berkas salah bentuk di folder yang ia pilih sendiri), sama kelasnya
    dengan kunci tulis. Galat lain tetap dilempar supaya jejaknya tercetak (aturan keras 7).
    """

    folder: Path
    hasil: berkas.HasilBaca | None = None
    galat: str | None = None

    @property
    def berhasil(self) -> bool:
        return self.hasil is not None


def baca_folder_impor(folder: Path) -> PembacaanImpor:
    """Baca folder impor tanpa menulis apa pun (dipakai sebelum konfirmasi, K59 d)."""
    try:
        return PembacaanImpor(folder=folder, hasil=berkas.baca_folder(folder))
    except ingesti.GalatIngesti as galat:
        return PembacaanImpor(folder=folder, galat=str(galat))


def _baris(nama: str, nilai: object, kosong: str = "(tidak diisi)") -> str:
    teks = "" if nilai is None else str(nilai).strip()
    return f"{nama:<14}: {teks or kosong}"


def _teks_atau_none(nilai: str | None) -> str | None:
    if nilai is None:
        return None
    bersih = nilai.strip()
    return bersih or None


def _tanggal_tampil(nilai: date | str | None, kosong: str = "(tidak diisi)") -> str:
    if nilai is None:
        return kosong
    if isinstance(nilai, str):
        try:
            nilai = date.fromisoformat(nilai)
        except ValueError:
            return nilai
    return tampilan.tanggal(nilai)


# ---------------------------------------------------------------------------------------
# F1: impor berkas (PRD 7.1, aksi #19b/K59 c)
# ---------------------------------------------------------------------------------------


def _baris_berkas(dibaca: berkas.HasilBaca) -> tuple[int, int]:
    """Jumlah baris yang terbaca dan jumlah berkasnya — dihitung, bukan diketik ulang.

    Barisnya dibaca dari `KumpulanData` (objek yang benar-benar diserahkan ke jalur tulis), bukan
    dari teks ringkasan pembaca berkas: kalau keduanya berbeda, yang benar adalah yang ditulis.
    """
    jenis = tuple(jenis for _, jenis in ingesti.BERKAS_IMPOR_DIKENAL)
    jumlah = sum(len(getattr(dibaca.kumpulan, satu, ())) for satu in jenis)
    return jumlah, len(dibaca.dibaca)


def ringkasan_impor(pembacaan: PembacaanImpor) -> str:
    """Isi dialog konfirmasi impor: folder, **jumlah baris per tabel**, dan apa yang ikut ditulis.

    Yang tidak ada berkasnya ikut disebut: impor bertahap memang sah, tetapi folder yang
    kehilangan satu berkas tidak boleh tampak seperti folder yang lengkap.
    """
    dibaca = pembacaan.hasil
    if dibaca is None:  # pragma: no cover - dijaga pemanggil; ini penjaga urutan, bukan alur
        raise GalatTulis(
            f"folder '{pembacaan.folder}' belum dibaca, jadi isinya tidak bisa dikonfirmasi: "
            f"{pembacaan.galat}"
        )
    jumlah, banyak_berkas = _baris_berkas(dibaca)
    bagian = [
        _baris("folder", pembacaan.folder),
        _baris("berkas dibaca", ", ".join(dibaca.dibaca)),
        _baris(
            "tidak ada",
            ", ".join(dibaca.tidak_ada),
            "(seluruh berkas yang dicari ada)",
        ),
        _baris("total", f"{tampilan.angka(jumlah, 0)} baris dari {banyak_berkas} berkas"),
        "",
        "Baris di atas ditulis sebagai revisi baru (append-only): baris yang sudah ada dan isinya "
        "sama tidak ditulis ulang, dan tidak ada baris lama yang ditimpa. Snapshot baru, arsip "
        "snapshot, dan laporan mutunya ikut ditulis, dengan label sumber "
        f"'{dibaca.kumpulan.sumber}'.",
    ]
    return "\n".join(bagian)


def permintaan_impor(
    *, pembacaan: PembacaanImpor, tanggal_data_minimum: date | None = None
) -> PermintaanTulis:
    """Impor satu folder berkas — jalur yang sama dengan `--impor` di baris perintah (PRD 7.1).

    Hasil bacaannya **dibawa** ke penulisan (`sudah_dibaca`), bukan dibaca ulang: ringkasan yang
    disetujui pengguna dan baris yang ditulis harus berasal dari objek yang sama (K59 d) —
    kalau berkasnya berubah di antara konfirmasi dan penulisan, yang benar adalah yang disetujui.
    """
    dibaca = pembacaan.hasil
    if dibaca is None:
        raise GalatTulis(
            f"folder '{pembacaan.folder}' tidak bisa dibaca, jadi tidak ada yang bisa diimpor: "
            f"{pembacaan.galat}"
        )

    def jalankan(sambungan: sqlite3.Connection) -> HasilTulis:
        laporan = pengatur.jalankan_impor(
            sambungan,
            pembacaan.folder,
            sudah_dibaca=dibaca,
            tanggal_data_minimum=tanggal_data_minimum,
        )
        pesan = laporan.ringkas()
        if laporan.sukses:
            pesan += f"\n{dampak_impor()}"
        return HasilTulis(berhasil=laporan.sukses, pesan=pesan)

    return PermintaanTulis(
        judul=f"Impor berkas dari {pembacaan.folder.name}",
        ringkasan=ringkasan_impor(pembacaan),
        jalankan=jalankan,
    )


def _idx_sebagai_utama(pilihan: potret.PilihanHarga | None, tanggal: date) -> bool:
    """Apakah Ringkasan Saham bertanggal `tanggal` adalah harga utama hari itu (K97)."""
    return pilihan is not None and pilihan.label_pada(tanggal) == unggahan_idx.SUMBER_IDX


def peran_unggahan_idx(pilihan: potret.PilihanHarga | None, tanggal: date) -> str:
    """Kalimat konfirmasi: berkas ini masuk sebagai harga utama (sambungan K97) atau pembanding."""
    if _idx_sebagai_utama(pilihan, tanggal) and pilihan is not None and pilihan.sejak is not None:
        return (
            "Harga ini masuk sebagai harga UTAMA hari itu: sambungan harga resmi berlaku sejak "
            f"{tampilan.tanggal(pilihan.sejak)} (K97), jadi saringan berikutnya memakainya. "
            "Sesudah impor, cek sumber kedua (PRD 7.3) langsung dijalankan terhadap label "
            "riwayat dan dicatat."
        )
    return (
        "Harga ini masuk sebagai harga PEMBANDING: saringan tetap memakai sumber dengan "
        "riwayat bar terbanyak (K14), jadi skor tidak berubah. Sesudah impor, cek sumber "
        "kedua (PRD 7.3) langsung dijalankan dan dicatat."
    )


def _peran_per_tanggal(pilihan: potret.PilihanHarga | None, tanggal: Sequence[date]) -> str:
    """Satu baris per tanggal: masuk sebagai harga utama atau pembanding (K97)."""
    baris = []
    for hari in tanggal:
        if _idx_sebagai_utama(pilihan, hari):
            peran = "harga UTAMA (sambungan harga resmi)"
        elif pilihan is not None and pilihan.tersambung:
            peran = "harga PEMBANDING — juga bukti tumpang-tindih gerbang sambungan (K97 b)"
        else:
            peran = "harga PEMBANDING"
        baris.append(f"  {tampilan.tanggal(hari)}: {peran}")
    return "\n".join(baris)


def permintaan_impor_ringkasan_idx(
    sambungan: sqlite3.Connection,
    *,
    unggahan: unggahan_idx.Unggahan | Sequence[unggahan_idx.Unggahan],
) -> PermintaanTulis:
    """Impor satu atau beberapa Ringkasan Saham IDX unggahan pengguna, lalu cek sumber kedua.

    Jalur tulisnya `permintaan_impor` yang sama (berkas `harga-harian.csv` di folder impor milik
    unggahan itu), jadi validasinya sama dengan `--impor`. Beberapa berkas = satu konfirmasi dan
    satu snapshot (K97 langkah 4).

    **Tanggal lampau diterima** (K97 d: hari yang terlupa diunggah bisa diisi belakangan), dengan
    `diketahui_pada` = waktu impor, sehingga snapshot lama tetap tidak melihatnya. Tanggal data
    snapshot baru **tidak mundur** (`tanggal_data_minimum`). Berkas bertanggal **sesudah** snapshot
    terakhir tetap ditolak: snapshot itu belum punya data riwayat hari tersebut, dan menerbitkan
    snapshot bertanggal itu hanya dari berkas IDX akan melompati "Perbarui data".

    Cek sumber kedua (PRD 7.3) membandingkan pada tanggal snapshot, jadi ia hanya dijalankan bila
    salah satu berkas bertanggal itu; selain itu tidak dijalankan, dan hal itu disebut.
    """
    semua = (unggahan,) if isinstance(unggahan, unggahan_idx.Unggahan) else tuple(unggahan)
    if not semua:
        raise GalatTulis("tidak ada berkas Ringkasan Saham yang dipilih untuk diimpor")
    isi: list[unggahan_idx.RingkasanSaham] = []
    for satu in semua:
        try:
            isi.append(unggahan_idx.baca(satu.berkas))
        except unggahan_idx.GalatUnggahan as galat:
            raise GalatTulis(str(galat)) from galat
    per_tanggal: dict[date, list[str]] = {}
    for satu, hari in zip(semua, isi):
        per_tanggal.setdefault(hari.tanggal, []).append(satu.nama_asli)
    kembar = {hari: nama for hari, nama in per_tanggal.items() if len(nama) > 1}
    if kembar:
        rincian = "; ".join(f"{tampilan.tanggal(hari)}: {', '.join(nama)}" for hari, nama in sorted(kembar.items()))
        raise GalatTulis(
            f"beberapa berkas bertanggal sama ({rincian}); pilih satu berkas per tanggal"
        )

    terakhir = sambungan.execute(
        "SELECT id_snapshot, tanggal_data FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()
    if terakhir is None:
        raise GalatTulis("belum ada snapshot; tekan \"Perbarui data\" lebih dulu, baru impor harga pembanding")
    tanggal_snapshot = date.fromisoformat(terakhir[1])
    di_depan = sorted(hari for hari in per_tanggal if hari > tanggal_snapshot)
    if di_depan:
        raise GalatTulis(
            f"Ringkasan Saham bertanggal {', '.join(tampilan.tanggal(hari) for hari in di_depan)}, "
            f"sedangkan snapshot terakhir #{terakhir[0]} berisi data "
            f"{tampilan.tanggal(tanggal_snapshot)}. Tekan \"Perbarui data\" dulu sampai snapshot "
            "berisi data tanggal itu, lalu impor lagi."
        )

    urut = sorted(zip(semua, isi), key=lambda pasangan: pasangan[1].tanggal)
    folder = unggahan_idx.siapkan_folder_impor(
        [satu for satu, _ in urut], [hari for _, hari in urut]
    )
    dasar = permintaan_impor(
        pembacaan=baca_folder_impor(folder), tanggal_data_minimum=tanggal_snapshot
    )
    pilihan = potret.harga_dipakai(sambungan)
    tanggal = [hari.tanggal for _, hari in urut]
    ada_tanggal_snapshot = tanggal_snapshot in per_tanggal
    # Sejak tanggal sambung (K97), berkas bertanggal snapshot adalah harga UTAMA hari itu, dan
    # pembandingnya dipilih otomatis (label riwayat). Memaksa IDX sebagai pembanding saat itu
    # berarti membandingkan IDX dengan dirinya sendiri — "0 ditandai" yang tidak memeriksa apa pun.
    pembanding = (
        None if _idx_sebagai_utama(pilihan, tanggal_snapshot) else unggahan_idx.SUMBER_IDX
    )
    if ada_tanggal_snapshot:
        tentang_cek = peran_unggahan_idx(pilihan, tanggal_snapshot)
    else:
        tentang_cek = (
            f"Cek sumber kedua (PRD 7.3) TIDAK dijalankan sesudah impor ini: ia membandingkan pada "
            f"tanggal snapshot ({tampilan.tanggal(tanggal_snapshot)}), dan tidak ada berkas "
            "bertanggal itu. Snapshot baru tetap bertanggal data "
            f"{tampilan.tanggal(tanggal_snapshot)} (tidak mundur)."
        )

    def jalankan(koneksi: sqlite3.Connection) -> HasilTulis:
        hasil = jalankan_permintaan(dasar, koneksi)
        if not hasil.berhasil:
            return hasil
        if not ada_tanggal_snapshot:
            return HasilTulis(
                berhasil=True,
                pesan=f"{hasil.pesan}\n\nCek sumber kedua tidak dijalankan: tidak ada berkas "
                f"bertanggal snapshot ({tampilan.tanggal(tanggal_snapshot)}).",
            )
        laporan = pengatur.cek_sumber_kedua(koneksi, sumber_pembanding=pembanding)
        return HasilTulis(berhasil=True, pesan=f"{hasil.pesan}\n\n{laporan.ringkas()}")

    judul_tanggal = (
        tampilan.tanggal(tanggal[0])
        if len(tanggal) == 1
        else f"{len(tanggal)} hari ({tampilan.tanggal(tanggal[0])} – {tampilan.tanggal(tanggal[-1])})"
    )
    berkas_baris = [
        _baris("berkas", f"{satu.nama_asli} (SHA-256 {satu.sha256[:12]}…)") for satu, _ in urut
    ]
    return PermintaanTulis(
        judul=f"Impor Ringkasan Saham IDX {judul_tanggal}",
        ringkasan="\n".join(
            [
                *berkas_baris,
                _baris("tanggal", ", ".join(tampilan.tanggal(hari) for hari in tanggal)),
                _baris("emiten", " + ".join(tampilan.angka(len(hari.baris), 0) for _, hari in urut)),
                _baris("label sumber", unggahan_idx.SUMBER_IDX),
                "",
                _peran_per_tanggal(pilihan, tanggal),
                "",
                tentang_cek,
                "",
                dasar.ringkasan,
            ]
        ),
        jalankan=jalankan,
    )


def _sidik(jalur: Path) -> str | None:
    return hashlib.sha256(jalur.read_bytes()).hexdigest() if jalur.exists() else None


def permintaan_impor_notasi_idx(
    sambungan: sqlite3.Connection,
    *,
    jalur: Path,
    nama_asli: str,
    hari_ini: date | None = None,
) -> PermintaanTulis:
    """Impor berkas Notasi Khusus IDX unduhan pengguna (K96) lewat jalur impor biasa.

    Daftar barunya digabung dengan `konfigurasi/notasi-khusus.csv` memakai aturan yang sama dengan
    `--ambil-notasi` (`notasi.tulis_berkas`: bertambah, yang tidak lagi tercantum ditutup, isian
    tangan tidak disentuh). Gabungannya disiapkan di folder impor milik unggahan itu dan
    **dibaca sebelum konfirmasi**; berkas konfigurasi baru diganti sesudah impornya berhasil, dan
    hanya bila belum berubah sejak konfirmasi disusun (K59 d).
    """
    del sambungan  # tidak ada yang dibaca dari basis data; tanda tangannya seragam dengan impor lain
    hari = hari_ini or date.today()
    try:
        hasil = notasi.baca_unduhan(jalur, nama_asli=nama_asli, hari_ini=hari)
        konfigurasi = notasi.berkas_tujuan(lokasi.folder_konfigurasi())
        terbaru = notasi.tanggal_daftar_terbaru(notasi.baca(konfigurasi.parent))
    except notasi.GalatNotasi as galat:
        raise GalatTulis(str(galat)) from galat
    if terbaru is not None and hasil.tanggal_data < terbaru:
        raise GalatTulis(
            f"daftar ini per {tampilan.tanggal(hasil.tanggal_data)}, lebih lama dari daftar yang "
            f"sudah tersimpan (per {tampilan.tanggal(terbaru)}). Mengimpornya akan menutup notasi "
            "yang masih berlaku; unduh daftar terbaru dari situs IDX"
        )

    return _permintaan_gabung_notasi(
        hasil,
        konfigurasi,
        hari=hari,
        judul=f"Impor Notasi Khusus IDX per {tampilan.tanggal(hasil.tanggal_data)}",
        ringkasan=lambda tulisan: [
            _baris("berkas", f"{nama_asli} (SHA-256 {_sidik(jalur)[:12]}…)"),
            _baris("daftar per", tampilan.tanggal(hasil.tanggal_data)),
            _baris(
                "emiten",
                f"{len(hasil.baris)} emiten (papan pemantauan khusus: "
                f"{hasil.jumlah_papan_pemantauan})",
            ),
            _baris(
                "perubahan",
                f"baru: {tulisan.baru}, ditutup: {tulisan.ditutup} (yang tidak lagi tercantum)",
            ),
            "",
            f"Sesudah impor berhasil, {konfigurasi} diganti dengan gabungan ini. Suspensi dan "
            "UMA TIDAK ikut diperbarui oleh berkas ini.",
        ],
    )


def permintaan_impor_pengumuman_idx(
    sambungan: sqlite3.Connection,
    *,
    berkas: Sequence[tuple[Path, str]],
    hari_ini: date | None = None,
) -> PermintaanTulis:
    """Impor PDF pengumuman suspensi & UMA IDX unduhan pengguna (K99) lewat jalur impor biasa.

    `berkas` = (jalur tersimpan, nama asli). Semua PDF dibaca lebih dulu; satu yang tidak dikenali
    menggagalkan seluruh unggahan, supaya tidak ada yang masuk sebagian tanpa disadari. Gabungannya
    **hanya menambah**: kumpulan PDF bukan daftar lengkap, jadi baris yang tidak disebut tidak
    ditutup. Satu-satunya penutupan adalah suspensi yang dinyatakan dibuka oleh PDF UPT (K100).
    """
    del sambungan  # tidak ada yang dibaca dari basis data; tanda tangannya seragam dengan impor lain
    hari = hari_ini or date.today()
    try:
        pengumuman = [
            pengumuman_idx.baca(jalur.read_bytes(), nama_berkas=nama, hari_ini=hari) for jalur, nama in berkas
        ]
        konfigurasi = notasi.berkas_tujuan(lokasi.folder_konfigurasi())
        pilahan = pengumuman_idx.pilah(pengumuman, notasi.baca(konfigurasi.parent))
    except (pengumuman_idx.GalatPengumuman, notasi.GalatNotasi) as galat:
        raise GalatTulis(str(galat)) from galat

    return _permintaan_gabung_notasi(
        pilahan.hasil,
        konfigurasi,
        hari=hari,
        judul=f"Impor {len(pengumuman)} PDF pengumuman suspensi & UMA IDX",
        ringkasan=lambda tulisan: [
            *(_baris("berkas", f"{nama} (SHA-256 {_sidik(jalur)[:12]}…)") for jalur, nama in berkas),
            _baris(
                "perubahan",
                f"baru: {tulisan.baru}, ditutup: {tulisan.ditutup}, sudah tercatat: "
                f"{len(pilahan.sudah_ada)}",
            ),
            *(f"  baru: {satu.uraian}" for satu in pilahan.baru),
            *(f"  sudah tercatat: {satu.uraian}" for satu in pilahan.sudah_ada),
            "",
            "Suspensi mulai pada tanggal berlakunya (K99) dan tetap terbuka sampai PDF pembukaannya "
            "(UPT) diunggah; pembukaan menutupnya sehari sebelum tanggal dibuka kembali (K100). "
            "Pengumuman yang tidak diunggah tidak terdeteksi, jadi kelengkapannya tidak dinilai.",
            f"Sesudah impor berhasil, {konfigurasi} diganti dengan gabungan ini.",
        ],
    )


def _permintaan_gabung_notasi(
    hasil: notasi.HasilNotasi,
    konfigurasi: Path,
    *,
    hari: date,
    judul: str,
    ringkasan: Callable[[notasi.HasilTulisNotasi], list[str]],
) -> PermintaanTulis:
    """Gabungkan `hasil` dengan `notasi-khusus.csv`, baca sebelum konfirmasi, tulis sesudahnya.

    Dipakai unggahan Notasi Khusus (K96) dan PDF pengumuman (K99). Keduanya **harus** lewat folder
    impor yang sama: label sumber impor diturunkan dari foldernya, dan label yang berbeda membuat
    seluruh baris berkas itu tersimpan ulang sebagai revisi walau isinya sama.
    """
    sidik_awal = _sidik(konfigurasi)
    # Folder impornya TETAP, bukan per unggahan: label sumber impor diturunkan dari foldernya, dan
    # label yang berganti tiap minggu membuat seluruh baris berkas ini (termasuk suspensi) tersimpan
    # ulang sebagai revisi walau isinya sama — terukur atas salinan data kerja: 2.603 baris.
    folder = lokasi.pastikan_folder(notasi.folder_unduhan() / "impor")
    gabungan = notasi.berkas_tujuan(folder)
    if sidik_awal is None:
        gabungan.unlink(missing_ok=True)
    else:
        gabungan.write_bytes(konfigurasi.read_bytes())
    tulisan = notasi.tulis_berkas(hasil, gabungan, diakses=hari)
    # Dibekukan sekarang: konfirmasi lain bisa menimpa berkas di folder tetap itu sebelum yang ini
    # ditulis, sedangkan yang ditulis harus yang disetujui (K59 d). Baris impornya sudah terbawa di
    # `sudah_dibaca`.
    isi_gabungan = gabungan.read_bytes()
    dasar = permintaan_impor(pembacaan=baca_folder_impor(folder))

    def jalankan(koneksi: sqlite3.Connection) -> HasilTulis:
        if _sidik(konfigurasi) != sidik_awal:
            return HasilTulis(
                berhasil=False,
                pesan=f"{konfigurasi} berubah sesudah konfirmasi disusun; tidak ada yang ditulis. "
                "Unggah ulang berkasnya supaya gabungannya disusun dari isi yang baru.",
            )
        hasil_impor = jalankan_permintaan(dasar, koneksi)
        if not hasil_impor.berhasil:
            return hasil_impor
        lokasi.pastikan_folder(konfigurasi.parent)
        sementara = konfigurasi.with_name(konfigurasi.name + ".sebagian")
        sementara.write_bytes(isi_gabungan)
        sementara.replace(konfigurasi)
        return HasilTulis(
            berhasil=True, pesan=f"{hasil_impor.pesan}\n\n{konfigurasi.name} diperbarui: {konfigurasi}"
        )

    return PermintaanTulis(
        judul=judul,
        ringkasan="\n".join([*ringkasan(tulisan), "", dasar.ringkasan]),
        jalankan=jalankan,
    )


@dataclass(frozen=True)
class _BagianRingkasan:
    """Ringkasan Saham di folder pantau, dipilah menurut keadaan basis data saat ini."""

    siap: tuple[tuple[Path, date], ...] = ()
    #: Tanggalnya sudah punya bar IDX: tidak diimpor ulang, cukup dipindah.
    sudah_ada: tuple[tuple[Path, date], ...] = ()
    #: Sesudah snapshot terakhir: tetap di folder sampai "Perbarui data" menyusulnya.
    menunggu: tuple[tuple[Path, date], ...] = ()
    #: Lebih dari satu berkas bertanggal sama: tidak ditebak mana yang dipakai.
    kembar: tuple[tuple[Path, date], ...] = ()


def _bagi_ringkasan(
    sambungan: sqlite3.Connection, isi: Sequence[tuple[Path, date]]
) -> _BagianRingkasan:
    terakhir = sambungan.execute(
        "SELECT tanggal_data FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()
    tanggal_snapshot = date.fromisoformat(terakhir[0]) if terakhir else None
    jumlah: dict[date, int] = {}
    for _, hari in isi:
        jumlah[hari] = jumlah.get(hari, 0) + 1
    siap, sudah_ada, menunggu, kembar = [], [], [], []
    for jalur, hari in isi:
        if jumlah[hari] > 1:
            kembar.append((jalur, hari))
        elif sambungan.execute(
            "SELECT 1 FROM harga_harian WHERE tanggal = ? AND sumber = ? LIMIT 1",
            (hari.isoformat(), unggahan_idx.SUMBER_IDX),
        ).fetchone():
            sudah_ada.append((jalur, hari))
        elif tanggal_snapshot is None or hari > tanggal_snapshot:
            menunggu.append((jalur, hari))
        else:
            siap.append((jalur, hari))
    return _BagianRingkasan(tuple(siap), tuple(sudah_ada), tuple(menunggu), tuple(kembar))


def jumlah_belum_diimpor(sambungan: sqlite3.Connection, pindaian: folder_pantau.Pindaian) -> int:
    """Berkas folder pantau yang isinya belum ada di basis data (K104, kotak "Perlu diperbarui").

    Memakai pemilahan yang sama dengan impornya: Ringkasan Saham bertanggal yang sudah punya bar
    IDX dan Notasi Khusus yang tidak lebih baru dari daftar tersimpan tidak dihitung — berkas itu
    bisa saja sudah diimpor lewat unggahan dasbor, jadi tinggal dirapikan, bukan diimpor. PDF
    pengumuman tetap dihitung semua: mengetahui isinya sudah tercatat berarti membaca PDF-nya.
    """
    bagian = _bagi_ringkasan(sambungan, pindaian.ringkasan)
    jumlah = len(bagian.siap) + len(bagian.menunggu) + len(bagian.kembar) + len(pindaian.pengumuman)
    if pindaian.notasi:
        terbaru = notasi.tanggal_daftar_terbaru(notasi.baca(lokasi.folder_konfigurasi()))
        if terbaru is None or pindaian.notasi[-1][1] > terbaru:
            jumlah += 1
    return jumlah


def _daftar_tanggal(isi: Sequence[tuple[Path, date]]) -> str:
    return ", ".join(f"{tampilan.tanggal(hari)} ({jalur.name})" for jalur, hari in isi)


def permintaan_impor_folder_pantau(
    sambungan: sqlite3.Connection,
    *,
    folder: Path,
    hari_ini: date | None = None,
    tujuan_cadangan: Path | None = None,
) -> PermintaanTulis:
    """Impor berkas IDX yang sudah diunduh pengguna ke folder pantau (K101).

    Urutannya: cadangan → Ringkasan Saham → Notasi Khusus → PDF pengumuman. Tiap jenis lewat
    permintaan yang **sama** dengan unggahan dasbor (`permintaan_impor_ringkasan_idx`,
    `_notasi_idx`, `_pengumuman_idx`), jadi validasinya tidak bercabang. Permintaan itu disusun
    **di dalam** `jalankan`, satu per satu: Notasi Khusus dan PDF pengumuman sama-sama mengganti
    `notasi-khusus.csv`, dan permintaan PDF yang disusun sebelum impor notasi akan menolak dirinya
    sendiri ("berkas berubah sesudah konfirmasi"). Akibatnya konfirmasi dasbor hanya menyebut
    berkas dan urutannya; angka per jenis tampil di hasil.

    Berkas yang selesai disalin ke `unduhan-idx/` (bukti asal baris) lalu dihapus dari folder
    pantau. Kegagalan menghentikan langkah berikutnya, dan berkas yang belum selesai tetap di
    tempatnya untuk jalan berikutnya.
    """
    try:
        pindaian = folder_pantau.pindai(folder)
    except folder_pantau.GalatFolderPantau as galat:
        raise GalatTulis(str(galat)) from galat
    hari = hari_ini or date.today()
    rencana = _bagi_ringkasan(sambungan, pindaian.ringkasan)

    def jalankan(koneksi: sqlite3.Connection) -> HasilTulis:
        pesan: list[str] = []

        def gagal(sebab: str) -> HasilTulis:
            pesan.append(f"GAGAL: {sebab}")
            pesan.append("Berkas yang belum selesai tetap di folder pantau untuk jalan berikutnya.")
            return HasilTulis(berhasil=False, pesan="\n".join(pesan))

        bagian = _bagi_ringkasan(koneksi, pindaian.ringkasan)
        ada_impor = bool(bagian.siap or pindaian.notasi or pindaian.pengumuman)
        if ada_impor:
            try:
                hasil_cadangan = cadangan.buat(
                    koneksi, folder_data=lokasi.folder_data(), tujuan=tujuan_cadangan
                )
            except cadangan.GalatCadangan as galat:
                return gagal(f"cadangan sebelum impor gagal, tidak ada yang diimpor: {galat}")
            pesan.append(f"Cadangan dibuat: {hasil_cadangan}")

        try:
            if bagian.siap:
                unggahan = [
                    unggahan_idx.simpan(jalur.name, jalur.read_bytes()).unggahan
                    for jalur, _ in bagian.siap
                ]
                hasil = jalankan_permintaan(
                    permintaan_impor_ringkasan_idx(koneksi, unggahan=unggahan), koneksi
                )
                pesan.append(f"\n== Ringkasan Saham ==\n{hasil.pesan}")
                if not hasil.berhasil:
                    return gagal("impor Ringkasan Saham")
            for jalur, _ in (*bagian.siap, *bagian.sudah_ada):
                unggahan_idx.simpan(jalur.name, jalur.read_bytes())
                jalur.unlink()
            if bagian.sudah_ada:
                pesan.append(
                    "Ringkasan Saham sudah ada di basis data, tidak diimpor ulang: "
                    + _daftar_tanggal(bagian.sudah_ada)
                )

            if pindaian.notasi:
                *lama, (jalur_baru, hari_baru) = pindaian.notasi
                konfigurasi = notasi.berkas_tujuan(lokasi.folder_konfigurasi())
                terbaru = notasi.tanggal_daftar_terbaru(notasi.baca(konfigurasi.parent))
                if terbaru is None or hari_baru > terbaru:
                    hasil = jalankan_permintaan(
                        permintaan_impor_notasi_idx(
                            koneksi, jalur=jalur_baru, nama_asli=jalur_baru.name, hari_ini=hari
                        ),
                        koneksi,
                    )
                    pesan.append(f"\n== Notasi Khusus ==\n{hasil.pesan}")
                    if not hasil.berhasil:
                        return gagal("impor Notasi Khusus")
                else:
                    lama.append((jalur_baru, hari_baru))
                if lama:
                    pesan.append(
                        "Notasi Khusus tidak diimpor (tidak lebih baru dari daftar yang tersimpan "
                        "atau yang baru diimpor): " + _daftar_tanggal(lama)
                    )
                for jalur, _ in pindaian.notasi:
                    notasi.simpan_unduhan(jalur.name, jalur.read_bytes())
                    jalur.unlink()

            if pindaian.pengumuman:
                hasil = jalankan_permintaan(
                    permintaan_impor_pengumuman_idx(
                        koneksi,
                        berkas=[(jalur, jalur.name) for jalur in pindaian.pengumuman],
                        hari_ini=hari,
                    ),
                    koneksi,
                )
                pesan.append(f"\n== PDF pengumuman ==\n{hasil.pesan}")
                if not hasil.berhasil:
                    return gagal("impor PDF pengumuman")
                for jalur in pindaian.pengumuman:
                    pengumuman_idx.simpan_unduhan(jalur.name, jalur.read_bytes())
                    jalur.unlink()
        except GalatTulis as galat:
            return gagal(str(galat))
        except (
            notasi.GalatNotasi,
            pengumuman_idx.GalatPengumuman,
            unggahan_idx.GalatUnggahan,
            lokasi.GalatLokasi,
            OSError,
        ) as galat:
            return gagal(f"{type(galat).__name__}: {galat}" if isinstance(galat, OSError) else str(galat))

        tertinggal = [
            *(f"menunggu snapshot: {_daftar_tanggal([satu])}" for satu in bagian.menunggu),
            *(f"tanggal kembar: {_daftar_tanggal([satu])}" for satu in bagian.kembar),
            *(f"ditolak: {jalur.name} — {sebab}" for jalur, sebab in pindaian.ditolak),
        ]
        if not ada_impor and not bagian.sudah_ada and not tertinggal:
            pesan.append(pindaian.ringkas())
        if tertinggal:
            pesan.append("\nTetap di folder pantau:\n" + "\n".join(f"  {satu}" for satu in tertinggal))
        # Menunggu snapshot bukan kegagalan (jalan berikutnya sesudah "Perbarui data" menyusulnya);
        # berkas yang ditolak atau kembar butuh tangan pengguna, jadi jalannya harus berisik.
        berhasil = not (pindaian.ditolak or bagian.kembar)
        return HasilTulis(berhasil=berhasil, pesan="\n".join(pesan))

    def jalankan_dan_catat(koneksi: sqlite3.Connection) -> HasilTulis:
        # Jalan dari Task Scheduler tidak punya penonton; jejaknya di `log_jalan` yang dibaca
        # kotak "Perlu diperbarui" (AC-9). Jejak yang gagal ditulis tidak menutupi hasil impornya.
        try:
            hasil = jalankan(koneksi)
        except db.BasisDataTerkunci as galat:
            hasil = HasilTulis(berhasil=False, pesan=f"{galat}\n{KALIMAT_BELUM_MENULIS}")
        try:
            folder_pantau.catat_jalan(koneksi, berhasil=hasil.berhasil, pesan=hasil.pesan)
        except db.GalatBasisData as galat:
            return HasilTulis(
                berhasil=hasil.berhasil,
                pesan=f"{hasil.pesan}\nPERINGATAN: jejak jalan ini tidak tercatat di log_jalan: {galat}",
            )
        return hasil

    ringkasan = [pindaian.ringkas()]
    if rencana.menunggu:
        ringkasan.append(
            "Ringkasan Saham sesudah snapshot terakhir — tidak diimpor sekarang, tetap di folder: "
            + _daftar_tanggal(rencana.menunggu)
        )
    if rencana.sudah_ada:
        ringkasan.append("Ringkasan Saham yang sudah ada di basis data: " + _daftar_tanggal(rencana.sudah_ada))
    if rencana.kembar:
        ringkasan.append("Ringkasan Saham bertanggal sama (tidak diimpor): " + _daftar_tanggal(rencana.kembar))
    ringkasan += [
        "",
        "Urutan: cadangan → Ringkasan Saham → Notasi Khusus (hanya daftar terbaru, bila lebih baru "
        "dari yang tersimpan) → PDF pengumuman. Tiap jenis lewat jalur impor yang sama dengan "
        "unggahan dasbor; jumlah barisnya tampil di hasil. Berkas yang selesai disalin ke "
        "unduhan-idx/ lalu dihapus dari folder pantau; yang gagal tetap di sana.",
    ]
    return PermintaanTulis(
        judul=f"Impor unduhan IDX dari {folder}",
        ringkasan="\n".join(ringkasan),
        jalankan=jalankan_dan_catat,
    )


def dampak_impor() -> str:
    """Apa yang **belum** ikut berubah sesudah impor — supaya tidak disangka sudah.

    Impor menambah baris, ia tidak menghitung ulang apa pun: skor dan peringkat baru berubah
    sesudah saringan dijalankan. Layar lain pun hanya dimuat ulang bila diminta, jadi kalimatnya
    menyebut jalan keluarnya, bukan membiarkan pengguna menyangka angkanya sudah baru.
    """
    return (
        "Skor, peringkat, dan saringan TIDAK ikut dihitung ulang — jalankan saringan "
        "(`--saring` atau tombol di layar 11.2), dan muat ulang layar lain lewat menu Berkas → "
        '"Muat ulang semua layar" (Ctrl+R).'
    )


# ---------------------------------------------------------------------------------------
# F12: cadangan & daftar cadangan (PRD 9.12, aksi #19c/K59 c-e)
# ---------------------------------------------------------------------------------------


def catatan_pemulihan(tujuan: Path | None = None) -> str:
    """Kalimat yang menyatakan pemulihan **tidak** ada di dasbor web (K59 e) — satu tempat.

    Dipakai konfirmasi cadangan, pesan hasilnya, dan daftar cadangan (halaman Impor & cadangan
    memuatnya lewat daftar itu, jadi jangan ditambahkan lagi di sana). Yang penting bukan
    kerapian: pemulihan yang disangka ada di menu ini akan dicari tepat saat data sedang rusak,
    jadi keberadaannya **dan** jalan keluarnya disebut, bukan dibiarkan disimpulkan.
    """
    jalur = f' --pulihkan "{tujuan}"' if tujuan is not None else " --pulihkan FOLDER_CADANGAN"
    return (
        "Pemulihan TIDAK ada di dasbor web (K59 e): ia menimpa basis data dan menunggu tahap "
        f"tersendiri. Dari baris perintah: python -m mejasaham{jalur}"
    )


def ringkasan_cadangan(*, sumber: Path, tujuan: Path, retensi: int) -> str:
    """Isi dialog konfirmasi cadangan (K59 d): folder tujuan, retensi, dan cakupannya.

    Yang disebut lebih dulu adalah **folder tujuan** — cadangan yang ditulis ke folder yang tidak
    diharapkan adalah cadangan yang tidak ditemukan saat dibutuhkan, dan pada saat itu
    menyetujuinya sudah tidak bisa dibatalkan.
    """
    return "\n".join(
        [
            _baris("folder data", sumber),
            _baris("folder tujuan", tujuan),
            _baris(
                "retensi",
                f"{tampilan.angka(retensi, 0)} cadangan terbaru (yang lebih tua dibuang otomatis)",
            ),
            _baris(
                "cakupan",
                "basis data (VACUUM INTO), konfigurasi, arsip-snapshot, manifest.json",
            ),
            "",
            "Cadangan ini hanya MEMBACA basis data: tidak ada baris yang ditambah, diubah, atau "
            "dihapus. Yang ditulis adalah berkas di folder tujuan.",
            catatan_pemulihan(),
        ]
    )


def permintaan_cadangan(
    *,
    folder_data: Path | None = None,
    tujuan: Path | None = None,
    retensi: int = cadangan.RETENSI_BAWAAN,
) -> PermintaanTulis:
    """Cadangkan basis data + konfigurasi + arsip (F12) — jalur yang sama dengan `--buat-cadangan`.

    Dua hal yang membuat ini bukan sekadar pembungkus `cadangan.buat`:

    * **folder tujuannya dihitung sekali**, lewat `cadangan.folder_tujuan`, lalu dipakai
      konfirmasi (K59 d) **dan** penulisan. Dialog yang menyebut folder berbeda dari folder yang
      ditulis adalah kesalahan yang tidak terlihat di layar mana pun.
    * **folder di dalam folder data ditolak sebelum konfirmasi** (T69 b), lewat pemeriksa yang
      sama dengan `cadangan.buat` — jadi pengguna tidak pernah diminta menyetujui cadangan yang
      pasti gagal.
    """
    sumber = folder_data or lokasi.folder_data()
    sasaran = cadangan.folder_tujuan(sumber, tujuan)
    try:
        cadangan.periksa_tujuan(sumber, sasaran)
    except cadangan.GalatCadangan as galat:
        raise GalatTulis(str(galat)) from galat

    def jalankan(sambungan: sqlite3.Connection) -> HasilTulis:
        try:
            hasil = cadangan.buat(
                sambungan, folder_data=sumber, tujuan=tujuan, retensi=retensi
            )
        except cadangan.GalatCadangan as galat:
            # Kegagalan ini keadaan yang bisa dikerjakan pengguna (folder tujuan tidak bisa
            # ditulis, disk penuh, folder di dalam folder data) — sama kelasnya dengan berkas
            # impor yang salah bentuk. Ia menjadi pesan di layar, bukan traceback; dan yang
            # dijanjikan berbeda dari pencatat: cadangan tidak menyentuh basis data.
            return HasilTulis(berhasil=False, pesan=f"{galat}\n{KALIMAT_BASIS_TIDAK_DISENTUH}")
        tersimpan = cadangan.daftar(hasil.parent)
        return HasilTulis(
            berhasil=True,
            pesan="\n".join(
                [
                    f"Cadangan dibuat: {hasil}",
                    f"{tampilan.angka(len(tersimpan), 0)} cadangan tersimpan di {hasil.parent} "
                    f"(retensi {tampilan.angka(retensi, 0)}: yang lebih tua dibuang otomatis).",
                    "Konfigurasi dan arsip snapshot ikut disalin; manifest.json mencatat versi "
                    "skemanya.",
                    catatan_pemulihan(hasil),
                ]
            ),
        )

    return PermintaanTulis(
        judul="Buat cadangan data",
        ringkasan=ringkasan_cadangan(sumber=sumber, tujuan=sasaran, retensi=retensi),
        jalankan=jalankan,
        pertanyaan=PERTANYAAN_CADANGAN,
        # Cadangan tidak mengubah satu baris pun, jadi layar yang memuat ulang dirinya sesudah
        # penulisan tidak perlu dipanggil (T69 e). Ini bukan penghematan kecil: pada basis data
        # 231 MB, pemuatan ulang dasbor 64,17 dtk sedangkan cadangannya 1,38 dtk.
        muat_ulang=False,
    )


def ringkasan_daftar_cadangan(folder: Path | None = None) -> str:
    """Isi "Daftar cadangan" di menu Berkas (aksi #19c).

    Baris daftarnya **bukan** salinan: ia memanggil `cadangan.ringkas_daftar` yang sama dengan
    `--daftar-cadangan`, jadi daftar di jendela dan di baris perintah tidak bisa berbeda.
    """
    sasaran = folder or cadangan.folder_bawaan()
    return "\n".join(
        [
            f"Folder cadangan: {sasaran}",
            f"Retensi: {tampilan.angka(cadangan.RETENSI_BAWAAN, 0)} cadangan terbaru "
            "(yang lebih tua dibuang otomatis).",
            "",
            cadangan.ringkas_daftar(folder),
            "",
            "Baris di atas sama dengan keluaran `--daftar-cadangan`.",
            catatan_pemulihan(),
        ]
    )


# ---------------------------------------------------------------------------------------
# F11: catat transaksi (PRD 9.1 langkah 9, layar 11.3)
# ---------------------------------------------------------------------------------------


def permintaan_catat_transaksi(
    *,
    kode: str,
    aksi: str,
    lembar: int | None,
    harga: int | None,
    mode: str,
    tanggal: date | None = None,
    id_rencana: int | None = None,
    id_posisi: int | None = None,
    biaya: int | None = None,
    pajak: int | None = None,
    catatan: str | None = None,
) -> PermintaanTulis:
    """Satu eksekusi manual (F11) — sama dengan `--catat-transaksi` di baris perintah.

    Yang diperiksa di sini hanya kelengkapan isian yang memang wajib di baris perintah
    (kode, lembar, harga, mode); sisanya diperiksa **inti** yang sama, supaya pesannya pun sama.
    """
    kode = kode.strip().upper()
    kurang = [
        nama
        for nama, nilai in (
            ("kode", kode),
            ("lembar", lembar),
            ("harga", harga),
            ("mode", mode),
        )
        if nilai is None or nilai == ""
    ]
    if kurang:
        raise GalatTulis(
            f"Catat transaksi menuntut {', '.join(kurang)}. Mode wajib dinyatakan (simulasi atau "
            "nyata) sebab metrik kedua mode dilaporkan terpisah (PRD 9.11)."
        )
    if lembar is None or lembar <= 0 or harga is None or harga <= 0:
        raise GalatTulis(
            f"Lembar dan harga harus lebih dari nol (lembar {lembar!r}, harga {harga!r}); "
            "kotak yang kosong berarti tidak diisi, bukan nol."
        )
    # Sesudah diperiksa: nilai yang dipakai menulis **dan** yang tampil di ringkasan.
    lembar_isi = int(lembar)
    harga_isi = int(harga)

    ringkasan = "\n".join(
        [
            _baris("kode", kode),
            _baris("aksi", aksi),
            _baris("lembar", tampilan.angka(lembar_isi, 0) + " lbr"),
            _baris("harga", tampilan.rupiah(harga_isi)),
            _baris("nilai bruto", tampilan.rupiah(harga_isi * lembar_isi)),
            _baris("mode", mode),
            _baris("tanggal", _tanggal_tampil(tanggal, "(hari ini)")),
            _baris("id rencana", id_rencana),
            _baris("id posisi", id_posisi),
            _baris(
                "biaya",
                None if biaya is None else tampilan.rupiah(biaya),
                "(dihitung dari tarif broker yang berlaku; NULL bila tarifnya belum diketahui)",
            ),
            _baris("pajak", None if pajak is None else tampilan.rupiah(pajak)),
            _baris("catatan", catatan),
        ]
    )

    def jalankan(sambungan: sqlite3.Connection) -> str:
        hasil = posisi.catat_transaksi(
            sambungan,
            kode,
            aksi,
            harga=harga_isi,
            lembar=lembar_isi,
            mode=mode,
            tanggal=tanggal,
            id_rencana=id_rencana,
            id_posisi=id_posisi,
            biaya=biaya,
            pajak=pajak,
            catatan=catatan,
        )
        bagian = [hasil.ringkas()]
        if hasil.pelanggaran:
            bagian.append(PESAN_PELANGGARAN_DICATAT)
        else:
            bagian.append("Tidak ada pelanggaran yang terdeteksi pada transaksi ini.")
        return "\n".join(bagian)

    return PermintaanTulis(
        judul=f"Catat transaksi {kode} {aksi}", ringkasan=ringkasan, jalankan=jalankan
    )


# ---------------------------------------------------------------------------------------
# F11: ubah stop (PRD 9.11, layar 11.1; aksi #19d/K62/T71 c)
# ---------------------------------------------------------------------------------------


def permintaan_ubah_stop(
    *,
    sasaran: posisi.Posisi | None,
    stop: int | None,
    alasan: str | None = None,
    tanggal: date | None = None,
) -> PermintaanTulis:
    """Ubah stop terkini satu posisi — jalur yang sama dengan `--ubah-stop` (PRD 9.11).

    Dua hal yang membuat ringkasannya bukan sekadar hiasan:

    * **Posisinya dipilih dari daftar** (K64/T71 a), jadi yang sampai ke sini sudah baris
      tersimpan — bukan nomor yang diketik. `None` ditolak berisik: jendela tidak memilihkan
      posisi, dan stop yang menempel pada posisi yang salah tidak terlihat di layar mana pun.
    * **Tanggalnya adalah basis stop** (`tgl_stop`, PRD 9.11/AC-18). Isian kosong berarti
      **hari ini** — sama dengan baris perintah — dan tanggal itu ditulis apa adanya di ringkasan,
      sebab split sesudahnya dipindahkan dari basis itulah, bukan ditebak.

    Yang **tidak** diperiksa di sini: apakah posisinya masih aktif, dan apakah tick stop-nya sah.
    Keduanya diperiksa inti yang sama dengan baris perintah, supaya pesannya pun sama.
    """
    if sasaran is None:
        raise GalatTulis(
            "Ubah stop menuntut posisinya: pilih satu posisi aktif dari daftar. Jendela ini tidak "
            "memilihkan posisi untuk Anda, dan stop yang menempel pada posisi yang salah tidak "
            "terlihat di layar mana pun."
        )
    if stop is None or stop <= 0:
        raise GalatTulis(
            f"Stop baru harus lebih dari nol (stop {stop!r}); kotak yang kosong berarti tidak "
            "diisi, bukan nol."
        )
    nilai = int(stop)
    hari = tanggal or date.today()
    alasan_bersih = _teks_atau_none(alasan)

    ringkasan = "\n".join(
        [
            _baris(
                "posisi",
                f"#{sasaran.id_posisi} {sasaran.kode} · {sasaran.status} · {sasaran.mode}",
            ),
            _baris(
                "stop lama",
                None if sasaran.stop_terkini is None else tampilan.rupiah(sasaran.stop_terkini),
                "(belum ada stop)",
            ),
            _baris("tgl_stop lama", _tanggal_tampil(sasaran.tgl_stop, "(belum dinyatakan)")),
            _baris("stop baru", tampilan.rupiah(nilai)),
            _baris("tgl_stop baru", _tanggal_tampil(hari)),
            _baris("alasan", alasan_bersih),
            "",
            "Tgl_stop baru adalah BASIS level stop ini (PRD 9.11): split yang terjadi sesudah "
            "tanggal itu dipindahkan ke basis barunya, bukan ditebak.",
            CATATAN_STOP_REVISI,
        ]
    )

    def jalankan(sambungan: sqlite3.Connection) -> str:
        hasil = posisi.ubah_stop(
            sambungan,
            sasaran.id_posisi,
            nilai,
            alasan=alasan_bersih,
            tanggal=hari,
        )
        return "\n".join([hasil.ringkas(), CATATAN_STOP_REVISI])

    return PermintaanTulis(
        judul=f"Ubah stop posisi #{sasaran.id_posisi} {sasaran.kode}",
        ringkasan=ringkasan,
        jalankan=jalankan,
    )


# ---------------------------------------------------------------------------------------
# F11: keputusan right issue (PRD 9.11, layar 11.3; aksi #19d/K62/T71 c)
# ---------------------------------------------------------------------------------------


def permintaan_keputusan_right_issue(
    *,
    hak: posisi.HakRightIssue,
    keputusan: str,
    id_transaksi: int | None = None,
    ringkas_transaksi: str | None = None,
    lembar: int | None = None,
    harga: int | None = None,
    biaya: int | None = None,
    catatan: str | None = None,
) -> PermintaanTulis:
    """Catat keputusan manual atas satu right issue — sama dengan `--putuskan-right-issue`.

    Urutan yang mengikat (T71 c): keputusannya menempel pada **peristiwa** yang sudah tersimpan
    (`hak` = kode × tanggal aksi), bukan pada angka yang diketik ulang; keputusan `tebus` hanya
    **menunjuk** transaksi yang sudah tercatat (`id_transaksi`) dan jendela tidak membuatkan
    transaksinya; dan `jual_hmetd` menuntut lembar + harga, sebab hasil penjualan hak tidak bisa
    diturunkan dari data mana pun.

    Pemeriksaan di sini adalah pemeriksaan **bentuk isian** — keputusan yang sah, kelengkapan
    yang dituntut tiap pilihan, dan isian yang tidak dipakai pilihan itu. Sisanya (aksinya ada,
    transaksinya milik posisi ini, lembarnya `beli`) diperiksa inti yang sama dengan baris
    perintah, supaya pesannya pun sama.
    """
    if keputusan not in posisi.KEPUTUSAN_RIGHT_ISSUE_SAH:
        raise GalatTulis(
            f"keputusan {keputusan!r} tidak dikenal; yang sah: "
            f"{', '.join(posisi.KEPUTUSAN_RIGHT_ISSUE_SAH)} (PRD 9.11)"
        )
    if keputusan == "tebus":
        if id_transaksi is None:
            raise GalatTulis(
                "Keputusan `tebus` menuntut transaksi pembelian yang sudah tercatat: lembarnya "
                "hanya punya satu tempat — `transaksi`. Catat dulu belinya lewat tombol "
                '"Catat transaksi" di layar ini, lalu tekan Muat dan pilih transaksinya; jendela '
                "ini TIDAK mencatatkan transaksinya diam-diam (T51)."
            )
        if any(satu is not None for satu in (lembar, harga, biaya)):
            raise GalatTulis(
                "Keputusan `tebus` tidak memakai lembar/harga/biaya: yang menaikkan lembar posisi "
                "adalah transaksinya (T51). Kosongkan isian itu, atau pilih keputusan jual_hmetd."
            )
    else:
        if id_transaksi is not None:
            raise GalatTulis(
                f"keputusan `{keputusan}` tidak memakai transaksi; hanya `tebus` yang menunjuk "
                "pembelian lembar"
            )
        if keputusan != "jual_hmetd" and any(satu is not None for satu in (lembar, harga, biaya)):
            raise GalatTulis(
                f"keputusan `{keputusan}` tidak memakai lembar/harga/biaya; keduanya hanya berlaku "
                "untuk `jual_hmetd`. Menerimanya lalu membuangnya diam-diam akan membuat "
                "keputusannya tampak mencatat penjualan hak yang tidak pernah terjadi"
            )
        if lembar is not None and lembar <= 0:
            raise GalatTulis(f"Lembar hak harus lebih dari nol, bukan {lembar}")
        if harga is not None and harga <= 0:
            raise GalatTulis(f"Harga jual hak harus lebih dari nol, bukan {harga}")
    if keputusan == "jual_hmetd" and (lembar is None or harga is None):
        raise GalatTulis(
            "Keputusan `jual_hmetd` menuntut lembar dan harga jual hak: hasil penjualan hak tidak "
            "bisa diturunkan dari data mana pun."
        )

    catatan_bersih = _teks_atau_none(catatan)
    bagian = [
        _baris("posisi", f"#{hak.id_posisi} {hak.kode}"),
        _baris("keputusan", keputusan),
    ]
    if keputusan == "tebus":
        bagian.append(_baris("transaksi", f"#{id_transaksi}"))
        if ringkas_transaksi:
            bagian.append("  " + ringkas_transaksi)
    elif keputusan == "jual_hmetd":
        bagian.extend(
            [
                _baris("lembar hak dijual", tampilan.angka(int(lembar), 0) + " lbr"),
                _baris("harga jual hak", tampilan.rupiah(int(harga))),
                _baris(
                    "biaya",
                    None if biaya is None else tampilan.rupiah(biaya),
                    "(belum dicatat: hasilnya masih bruto)",
                ),
            ]
        )
    else:
        bagian.append("  Keputusan `abaikan` tidak mengubah lembar maupun uang (PRD 9.11).")
    bagian.extend(
        [
            _baris("catatan", catatan_bersih),
            "",
            "Peristiwa yang diputuskan:",
            f"  {hak.ringkas(dengan_keputusan=False)}",
            CATATAN_HAK_PETUNJUK,
        ]
    )
    if keputusan == "tebus":
        bagian.append(CATATAN_TEBUS_MENUNJUK_TRANSAKSI)
    else:
        bagian.append(CATATAN_KEPUTUSAN_REVISI)
    ringkasan = "\n".join(bagian)

    def jalankan(sambungan: sqlite3.Connection) -> str:
        hasil = posisi.catat_keputusan_right_issue(
            sambungan,
            hak.kode,
            hak.tanggal_aksi,
            keputusan,
            id_posisi=hak.id_posisi,
            id_transaksi=id_transaksi,
            lembar=lembar,
            harga=harga,
            biaya=biaya,
            catatan=catatan_bersih,
        )
        bagian_hasil = [hasil.ringkas()]
        bagian_hasil.append(
            CATATAN_TEBUS_MENUNJUK_TRANSAKSI if keputusan == "tebus" else CATATAN_KEPUTUSAN_REVISI
        )
        return "\n".join(bagian_hasil)

    return PermintaanTulis(
        judul=f"Putuskan right issue {hak.kode} {hak.tanggal_aksi.isoformat()}",
        ringkasan=ringkasan,
        jalankan=jalankan,
    )


# ---------------------------------------------------------------------------------------
# F5: simpan rencana (PRD 9.7, layar 11.4)
# ---------------------------------------------------------------------------------------


def permintaan_simpan_rencana(
    *,
    hasil: risiko.HasilRisiko,
    masukan: risiko.MasukanRisiko,
    entri: kandidat.Kandidat,
    jenis_stop: str,
    id_snapshot: int,
    id_rencana: int | None = None,
) -> PermintaanTulis:
    """Simpan rencana dari hasil kalkulator yang **sedang tampil** (PRD 9.7).

    Angka di ringkasan diambil dari `hasil` — objek yang sama yang diserahkan ke
    `risiko.simpan_dari_kandidat`. Kalkulator menghitung ulang di sini akan membuat ringkasan
    konfirmasi dan baris yang tersimpan berbeda begitu harga atau presetnya berubah di antaranya.
    """
    if not jenis_stop:
        raise GalatTulis(
            "Jenis stop belum dipilih; Q9 menetapkan cara stop dieksekusi dicatat per rencana."
        )
    # Pelanggaran diterima **di sini**, bukan ditanyakan ulang: teks konfirmasinya menyebut
    # pelanggarannya apa adanya, jadi menyetujui dialog itu berarti menerimanya (PRD 9.7).
    diterima = bool(hasil.pelanggaran)

    bagian = [
        risiko.ringkas_hasil(hasil, masukan),
        "",
        _baris("jenis stop", jenis_stop),
        _baris(
            "rencana",
            None if id_rencana is None else f"revisi #{id_rencana}",
            "(baru; kandidat berpindah watchlist -> rencana)",
        ),
    ]
    if diterima:
        bagian.extend(
            [
                "",
                "PELANGGARAN YANG AKAN DITERIMA (PRD 9.7 — pilihannya ikut tercatat di rencana):",
                *[f"  · {satu.pesan}" for satu in hasil.pelanggaran],
            ]
        )
    ringkasan = "\n".join(bagian)

    def jalankan(sambungan: sqlite3.Connection) -> str:
        tersimpan = risiko.simpan_dari_kandidat(
            sambungan,
            hasil,
            entri=entri,
            jenis_stop=jenis_stop,
            id_snapshot=id_snapshot,
            id_rencana=id_rencana,
            pelanggaran_diterima=diterima,
        )
        bagian_hasil = [tersimpan.ringkas()]
        if tersimpan.status_dipindahkan:
            bagian_hasil.append(
                f"Kandidat #{entri.id_kandidat} {entri.kode}: status watchlist -> rencana "
                "(riwayatnya tetap tersimpan)."
            )
        if tersimpan.peringatan is not None:
            bagian_hasil.append(f"PERINGATAN: {tersimpan.peringatan}")
        return "\n".join(bagian_hasil)

    judul = "Simpan rencana" + ("" if id_rencana is None else f" (revisi #{id_rencana})")
    return PermintaanTulis(judul=judul, ringkasan=ringkasan, jalankan=jalankan)


# ---------------------------------------------------------------------------------------
# F7: catatan jurnal (PRD 9.8, layar 11.5)
# ---------------------------------------------------------------------------------------


def permintaan_catat_jurnal(
    *,
    id_transaksi: int,
    ringkas_transaksi: str,
    alasan: str | None = None,
    pelajaran: str | None = None,
    tanggal_tinjau: date | None = None,
    tandai_selesai: bool = False,
    tanggal_selesai: date | None = None,
) -> PermintaanTulis:
    """Tulis satu catatan jurnal atas transaksi **terpilih** (F7).

    Dua aturan PRD 9.8 yang menentukan bentuk ringkasannya:
    (1) revisi **menggabungkan** — bidang yang tidak diisi mempertahankan isi catatan sebelumnya,
    (2) tidak ada penghapusan senyap — mengosongkan satu bidang tidak menghapusnya.
    Karena itu ringkasannya menyebut apa yang **berubah** dan apa yang dipertahankan.
    """
    alasan_bersih = _teks_atau_none(alasan)
    pelajaran_bersih = _teks_atau_none(pelajaran)
    selesai = tanggal_selesai if tandai_selesai else None
    # Sebab yang paling khusus lebih dulu: "tandai selesai" tanpa tanggal juga berarti tidak ada
    # isi, dan pesan "kosong" akan menyembunyikan apa yang sebenarnya kurang.
    if tandai_selesai and tanggal_selesai is None:
        raise GalatTulis(
            "Tandai selesai butuh tanggalnya: isi Tanggal selesai (YYYY-MM-DD). Jendela ini tidak "
            "menebak tanggal — tanggal yang tersimpan harus yang Anda nyatakan."
        )
    if not any((alasan_bersih, pelajaran_bersih, tanggal_tinjau, selesai)):
        raise GalatTulis(
            f"Catatan jurnal untuk transaksi #{id_transaksi} kosong: isi minimal satu dari "
            "Alasan, Pelajaran, Tanggal tinjau, atau Tandai selesai. Baris jurnal tanpa isi tidak "
            "mencatat apa pun — dan itu ditolak mesin, bukan hanya di sini (PRD 9.8)."
        )

    ringkasan = "\n".join(
        [
            _baris("transaksi", f"#{id_transaksi}"),
            f"  {ringkas_transaksi}",
            "",
            _baris("alasan", alasan_bersih, "(dipertahankan dari catatan sebelumnya)"),
            _baris("pelajaran", pelajaran_bersih, "(dipertahankan dari catatan sebelumnya)"),
            _baris(
                "tinjau ulang",
                _tanggal_tampil(tanggal_tinjau, "(dipertahankan dari catatan sebelumnya)"),
            ),
            _baris(
                "selesai",
                _tanggal_tampil(selesai, "(belum dinyatakan selesai)"),
            ),
            "",
            "Catatan lama TIDAK ditimpa: revisinya ditambah (PRD 9.8), dan bidang yang dikosongkan "
            "dipertahankan — mengosongkan berarti menghapus, dan itu tidak boleh senyap.",
        ]
    )

    def jalankan(sambungan: sqlite3.Connection) -> str:
        sebelum = jurnal.catatan_terkini(sambungan, id_transaksi)
        catatan = jurnal.catat(
            sambungan,
            id_transaksi,
            alasan=alasan_bersih,
            pelajaran=pelajaran_bersih,
            tanggal_tinjau=tanggal_tinjau,
            selesai_pada=selesai,
        )
        bagian = [catatan.ringkas()]
        if sebelum is None:
            bagian.append(f"Catatan ini baris jurnal PERTAMA untuk transaksi #{id_transaksi}.")
        else:
            bagian.append(
                f"Revisi r{sebelum.revisi} disimpan, bukan ditimpa (PRD 9.8): {sebelum.ringkas()}"
            )
        bagian.append(
            "Jurnal tidak memblokir apa pun (K34): catatan ini tidak mengubah transaksi, posisi, "
            "maupun pelanggaran yang tercatat di barisnya."
        )
        return "\n".join(bagian)

    return PermintaanTulis(
        judul=f"Catat jurnal transaksi #{id_transaksi}",
        ringkasan=ringkasan,
        jalankan=jalankan,
    )
