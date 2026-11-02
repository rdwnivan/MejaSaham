"""Orkestrasi ingesti & saringan: dari berkas/sumber data ke satu snapshot yang tercatat.

Berkas ini adalah tempat urutan kerjanya terlihat. Dua alur tinggal di sini:

* **Ingesti (F1, Tahap 0)** — ambil → periksa mutu → tulis atomik → arsip. Tiap langkah memakai
  modulnya sendiri (`pengambil`, `berkas`, `mutu`, `ingesti`, `arsip`) dan berkas ini yang
  memutuskan urutannya — termasuk kapan pekerjaan **berhenti tanpa menerbitkan snapshot**
  (PRD 9.3).
* **Saring & skor (F2/F3, Tahap 1)** — potret → metrik → saring → semesta likuid → skor →
  peringkat → simpan. Urutannya mengikat: statistik sektor dihitung dari **semesta likuid**,
  sedangkan skor hanya diberikan kepada emiten yang **lolos saring** (PRD 9.5).

Yang dijaga di sini:

1. **Snapshot lama tetap dipakai bila snapshot baru gagal.** Kegagalan tidak menghapus apa pun;
   ia tercatat di `log_jalan` dan dilaporkan ke pemanggil (AC-8, AC-9).
2. **Kegagalan arsip tidak membatalkan snapshot.** Snapshotnya sudah tercatat di basis data;
   kegagalan menulis arsip dilaporkan sebagai peringatan berisik dan masuk log — bukan
   dibatalkan diam-diam, dan bukan pula menggagalkan seluruh jalan.
3. **Tidak ada keputusan yang dikarang.** Daftar emiten berasal dari berkas rujukan yang
   dirawat pengguna; sumber harga diberi label "tidak resmi" apa adanya; kalender bursa dan
   imbal hasil SUN hanya masuk lewat impor berkas karena memang tidak tersedia dari sumber
   tidak resmi (PRD 7.1).
4. **Metrik dihitung sekali per potret.** Saringan dan skoring memakai himpunan metrik yang
   sama persis; menghitungnya dua kali membuka peluang dua layar menampilkan angka berbeda
   dari snapshot yang sama (PRD 5).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from mejasaham import (
    arsip,
    berkas,
    db,
    ingesti,
    jenis,
    konteks_pasar,
    lokasi,
    metrik,
    mutu,
    potret,
    saring,
    skor,
    tampilan,
)
from mejasaham.ingesti import (
    Emiten,
    GalatIngesti,
    HasilSimpan,
    IngestiDibatalkan,
    KumpulanData,
)


class SumberData(Protocol):
    """Kontrak pengambil data. `PengambilYFinance` memenuhinya; test memakai objek palsu."""

    def ambil(self, emiten: Sequence[Emiten]) -> KumpulanData: ...


@dataclass
class LaporanJalan:
    """Seluruh hasil satu jalan ingesti — satu objek untuk dilaporkan ke pengguna dan ke log."""

    proses: str
    sukses: bool
    pesan: str
    snapshot: HasilSimpan | None = None
    laporan_mutu: mutu.LaporanMutu | None = None
    arsip: arsip.HasilArsip | None = None
    peringatan: list[str] = field(default_factory=list)
    dibatalkan: bool = False

    @property
    def id_snapshot(self) -> int | None:
        return self.snapshot.id_snapshot if self.snapshot else None

    def ringkas(self) -> str:
        if not self.sukses:
            return f"[{self.proses}] GAGAL — {self.pesan}"
        bagian = [f"[{self.proses}] selesai — {self.pesan}"]
        if self.laporan_mutu is not None:
            bagian.append(self.laporan_mutu.ringkas())
            bagian.append(self.laporan_mutu.rincian())
        if self.arsip is not None:
            bagian.append(f"  arsip: {self.arsip.folder} ({self.arsip.total_baris} baris)")
        bagian.extend(f"  PERINGATAN: {satu}" for satu in self.peringatan)
        return "\n".join(bagian)


def _catat_log(
    sambungan: sqlite3.Connection,
    *,
    proses: str,
    hasil: str,
    pesan: str,
    id_snapshot: int | None = None,
) -> None:
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO log_jalan (waktu, proses, hasil, pesan, id_snapshot) VALUES (?, ?, ?, ?, ?)",
            (db.waktu_iso(), proses, hasil, pesan, id_snapshot),
        )


def _tanggal_hari_ini() -> date:
    return date.today()


def jalankan_refresh(
    sambungan: sqlite3.Connection,
    pengambil: SumberData,
    *,
    folder_impor: Path | None = None,
    momen: date | None = None,
    ambang_gagal_persen: int = 5,
    laporan: Callable[[object], None] | None = None,
) -> LaporanJalan:
    """Segarkan data EOD: ambil, periksa, tulis snapshot, arsipkan (F1, PRD 9.3).

    `folder_impor` adalah folder tempat `emiten.csv` (dan berkas lain bila ada) dibaca. Daftar
    emiten **wajib** ada: semesta saham adalah keputusan pengguna, bukan sesuatu yang dikarang
    aplikasi.
    """
    folder = folder_impor if folder_impor is not None else lokasi.folder_konfigurasi()

    # AC-12: setelah isi folder data dihapus, aplikasi harus bisa kembali ke bentuk bawaannya.
    # Karena itu template berkas impor disalin lebih dulu — tanpa satu pun data di dalamnya —
    # sehingga pesan galat berikutnya menunjuk berkas yang benar-benar ada dan bisa diisi.
    try:
        disalin = berkas.siapkan_berkas_bawaan(folder)
    except (GalatIngesti, lokasi.GalatLokasi) as galat:
        _catat_log(sambungan, proses=ingesti.PROSES_REFRESH, hasil="gagal", pesan=str(galat))
        return LaporanJalan(proses=ingesti.PROSES_REFRESH, sukses=False, pesan=str(galat))

    try:
        daftar = berkas.baca_emiten(folder)
    except GalatIngesti as galat:
        _catat_log(sambungan, proses=ingesti.PROSES_REFRESH, hasil="gagal", pesan=str(galat))
        return LaporanJalan(proses=ingesti.PROSES_REFRESH, sukses=False, pesan=str(galat))

    dobel = berkas.kode_duplikat(daftar)
    peringatan: list[str] = []
    if disalin:
        peringatan.append(
            "template berkas dibuat (masih kosong): " + ", ".join(disalin)
        )
    if dobel:
        peringatan.append(
            f"{len(dobel)} kode muncul lebih dari sekali di emiten.csv ({', '.join(dobel[:10])}); "
            "baris terbaru yang dipakai"
        )

    try:
        kumpulan = pengambil.ambil(daftar)
    except GalatIngesti as galat:
        _catat_log(sambungan, proses=ingesti.PROSES_REFRESH, hasil="gagal", pesan=str(galat))
        return LaporanJalan(proses=ingesti.PROSES_REFRESH, sukses=False, pesan=str(galat))

    # Berkas impor (kalender bursa, notasi khusus, SUN, aksi korporasi resmi) digabungkan bila
    # foldernya memuatnya. Ini yang membuat "hari bursa terakhir" dan peringatan snapshot basi
    # bisa dihitung (U5, AC-8) tanpa menuntut berkas itu ada sejak awal.
    #
    # Daftar emiten dari berkas impor dibuang di sini: semesta yang dipakai berhitung adalah
    # `emiten.csv` yang sudah dibaca di atas, dan menulisnya dua kali hanya menambah baris
    # identik. Label sumbernya tetap menyebut folder impor supaya asal tiap baris bisa ditelusuri:
    # baris berkas ditulis sebagai `tambahan` dengan labelnya sendiri, bukan dilebur ke label
    # pengambil otomatis (sesi 56). Foldernya dibuat absolut supaya peluncur (jalur absolut) dan
    # baris perintah (jalur relatif) menghasilkan label yang sama — label yang berganti-ganti
    # menulis ulang seluruh baris berkas sebagai revisi baru setiap refresh.
    dari_berkas: KumpulanData | None = None
    try:
        tambahan = berkas.baca_folder(folder.resolve())
    except GalatIngesti as galat:
        peringatan.append(f"berkas impor tidak dipakai: {galat}")
    else:
        dari_berkas = _tanpa_emiten(tambahan.kumpulan)
        if tambahan.tidak_ada:
            peringatan.append("berkas impor belum ada (dilewati): " + ", ".join(tambahan.tidak_ada))

    # Ambang kegagalan diperiksa **sebelum** apa pun ditulis (PRD 9.3): snapshot yang gagal
    # tidak boleh meninggalkan jejak data separuh.
    #
    # Daftar emiten kritis (50 ber-ADTV20 tertinggi) kini benar-benar diisi. Sebelumnya ia
    # dikirim None, sehingga syarat kedua PRD 9.3/AC-1 hanya dilaporkan sebagai "belum dapat
    # diperiksa" — dan syarat yang tidak pernah diperiksa lama-lama terbaca sebagai lulus.
    #
    # Daftarnya dibaca dari **satu** label sumber (`potret.sumber_utama`), sama dengan label yang
    # dipakai berhitung. Tanpa penyaringan itu, harga pembanding ikut menentukan peringkatnya
    # (P17): himpunan "20 hari bursa terakhir" menjadi gabungan dua sumber, sehingga emiten yang
    # datanya cuma ada di salah satu sumber bisa muncul sebagai emiten teratas hari ini.
    try:
        ingesti.periksa_ambang_gagal(
            kumpulan.gagal,
            len(daftar),
            ambang_persen=ambang_gagal_persen,
            emiten_kritis=tuple(
                satu.kode
                for satu in mutu.peringkat_adtv(
                    sambungan, sumber=potret.harga_dipakai(sambungan)
                )
            ),
        )
    except IngestiDibatalkan as galat:
        _catat_log(sambungan, proses=ingesti.PROSES_REFRESH, hasil="gagal", pesan=str(galat))
        return LaporanJalan(
            proses=ingesti.PROSES_REFRESH,
            sukses=False,
            pesan=str(galat),
            dibatalkan=True,
            peringatan=peringatan,
        )

    try:
        tanggal_data = berkas.tanggal_data_dari(
            kumpulan if dari_berkas is None else kumpulan.tambah(replace(dari_berkas, sumber=kumpulan.sumber))
        )
    except GalatIngesti as galat:
        _catat_log(sambungan, proses=ingesti.PROSES_REFRESH, hasil="gagal", pesan=str(galat))
        return LaporanJalan(proses=ingesti.PROSES_REFRESH, sukses=False, pesan=str(galat))

    # `kumpulan.catatan` bertipe tuple, jadi bagian tambahan harus dibungkus jadi tuple juga.
    # Versi sebelumnya menambahkan `str` langsung ke `tuple`, dan itu membuat **setiap** refresh
    # yang punya emiten gagal — tetapi tidak dibatalkan — mati dengan `TypeError` sesudah
    # pengambilan selesai, yaitu persis keadaan yang paling sering terjadi dalam pemakaian nyata:
    # sebagian kecil emiten gagal, snapshot tetap terbit. Uji integrasi refresh menemukannya.
    gagal_teks = "; ".join(satu.baris() for satu in kumpulan.gagal[:20])
    bagian_catatan = kumpulan.catatan + ((f"gagal: {gagal_teks}",) if gagal_teks else ())
    catatan = " | ".join(bagian_catatan)

    try:
        tersimpan = ingesti.simpan(
            sambungan,
            kumpulan,
            tanggal_data=tanggal_data,
            proses=ingesti.PROSES_REFRESH,
            catatan=catatan or None,
            tambahan=dari_berkas,
        )
    except (GalatIngesti, db.GalatBasisData, sqlite3.Error) as galat:
        pesan = f"penulisan snapshot dibatalkan: {galat}"
        _catat_log(sambungan, proses=ingesti.PROSES_REFRESH, hasil="gagal", pesan=pesan)
        return LaporanJalan(
            proses=ingesti.PROSES_REFRESH, sukses=False, pesan=pesan, peringatan=peringatan
        )

    # Yang diperiksa adalah deret yang dipakai berhitung pada snapshot ini, sama dengan jalur
    # impor — bukan label pengambilan. Sesudah tanggal sambung (K97) label pengambilan hanya
    # riwayat + pembanding; memeriksanya berarti menilai bar yang tidak dipakai.
    laporan_mutu = mutu.periksa(
        sambungan,
        tanggal_data=tanggal_data,
        jumlah_gagal=len(kumpulan.gagal),
        sumber=potret.harga_dipakai(sambungan, batas=tersimpan.diketahui_pada),
        momen=momen,
    )
    # U18: dua jenis kegagalan masuk laporan mutu sebagai temuan yang **berbeda** — "gagal
    # sementara" menuntut pengambilan ulang, "tidak diperdagangkan lagi" menuntut keputusan
    # semesta (buang dari emiten.csv atau terima lubangnya). Menyamakan keduanya membuat
    # tindakan yang benar untuk satu keadaan terlihat benar juga untuk keadaan lainnya.
    laporan_mutu.temuan.extend(
        mutu.Temuan(
            satu.kode,
            mutu.BOLONG,
            "gagal_diambil" if satu.jenis == ingesti.KEGAGALAN_SEMENTARA else "tidak_diperdagangkan",
            f"[{satu.jenis}] {satu.alasan}",
        )
        for satu in kumpulan.gagal
    )

    hasil_arsip: arsip.HasilArsip | None = None
    try:
        hasil_arsip = arsip.tulis(
            sambungan,
            id_snapshot=tersimpan.id_snapshot,
            laporan_mutu=mutu.csv_laporan(laporan_mutu),
        )
    except (GalatIngesti, OSError, lokasi.GalatLokasi) as galat:
        # Snapshotnya sudah tercatat; arsipnya belum. Ini **peringatan**, bukan kegagalan
        # snapshot — tetapi tidak boleh senyap (PRD 7.2, AC-9).
        peringatan.append(f"arsip snapshot gagal ditulis: {galat}")
        _catat_log(
            sambungan,
            proses=ingesti.PROSES_REFRESH,
            hasil="peringatan",
            pesan=f"snapshot {tersimpan.id_snapshot} tersimpan, tetapi arsipnya gagal: {galat}",
            id_snapshot=tersimpan.id_snapshot,
        )

    # U18: "gagal" tidak lagi satu kalimat. Yang tidak diperdagangkan lagi dan yang patut
    # diulang dipisah, karena hanya yang kedua berarti "coba lagi nanti".
    peringatan.extend(ingesti.ringkas_kegagalan(kumpulan.gagal))
    if tersimpan.baris.total_kosong_ditolak:  # T90: tampil di layar, bukan hanya di log
        peringatan.append(tersimpan.baris.ringkas_kosong_ditolak())

    # PRD 7.3 menuntut cek sumber kedua **tiap minggu**. Laporan mutu sudah memuat keadaannya,
    # tetapi refresh adalah jalan harian yang benar-benar dijalankan orang (dan Task Scheduler),
    # jadi keadaannya diulang di sini sebagai peringatan — bukan disimpan di dalam rincian yang
    # harus dibuka lebih dulu. Snapshotnya tetap terbit: cek yang tertunda tidak membuat satu pun
    # angka emiten salah, dan menahan snapshot karenanya akan menukar satu masalah dengan masalah
    # yang lebih besar.
    if laporan_mutu.cek_sumber_kedua is not None and not laporan_mutu.cek_sumber_kedua.lulus:
        peringatan.append(
            "cek sumber kedua (PRD 7.3): " + laporan_mutu.cek_sumber_kedua.ringkas()
        )

    pesan = (
        f"snapshot {tersimpan.id_snapshot} · tanggal data {tersimpan.tanggal_data} · "
        f"{tersimpan.jumlah_emiten} emiten · {tersimpan.baris.total_baru} baris baru, "
        f"{tersimpan.baris.total_tetap} sudah ada dan sama · {len(kumpulan.gagal)} gagal "
        f"({len(kumpulan.gagal_permanen)} permanen, {len(kumpulan.gagal_sementara)} sementara)"
    )
    return LaporanJalan(
        proses=ingesti.PROSES_REFRESH,
        sukses=True,
        pesan=pesan,
        snapshot=tersimpan,
        laporan_mutu=laporan_mutu,
        arsip=hasil_arsip,
        peringatan=peringatan,
    )


def _tanpa_emiten(kumpulan: KumpulanData) -> KumpulanData:
    """Ambil isi berkas impor tanpa daftar emitennya, dengan label sumber aslinya.

    Dua alasan bentuknya begini:

    * Daftar emiten tidak boleh tercampur dua kali: semesta yang dipakai berhitung adalah
      berkas rujukan (`emiten.csv`), sedangkan berkas impor lain (kalender, notasi) menyumbang
      datanya saja.
    * Baris impor membawa label folder impornya, bukan label sumber pengambilan otomatis — dan
      asal Yahoo tetap menempel pada baris harga yang memang berasal dari Yahoo. Pemanggil
      menyerahkannya ke `ingesti.simpan(tambahan=…)`, bukan menggabungkannya (S2).
    """
    return KumpulanData(
        sumber=kumpulan.sumber,
        harga_harian=kumpulan.harga_harian,
        harga_indeks=kumpulan.harga_indeks,
        aksi_korporasi=kumpulan.aksi_korporasi,
        catatan_aksi_mutu=kumpulan.catatan_aksi_mutu,
        sambungan_harga=kumpulan.sambungan_harga,
        kalender_bursa=kumpulan.kalender_bursa,
        notasi_khusus=kumpulan.notasi_khusus,
        imbal_hasil_sun=kumpulan.imbal_hasil_sun,
        catatan=kumpulan.catatan,
    )


def jalankan_impor(
    sambungan: sqlite3.Connection,
    folder: Path,
    *,
    proses: str = ingesti.PROSES_IMPOR,
    sudah_dibaca: berkas.HasilBaca | None = None,
    tanggal_data_minimum: date | None = None,
) -> LaporanJalan:
    """Impor berkas tanpa jaringan: satu-satunya jalur untuk data yang tidak ada di sumber EOD.

    `tanggal_data_minimum` mencegah tanggal data snapshot **mundur** saat berkas yang diimpor
    hanya memuat hari lampau (K97 langkah 4: Ringkasan Saham IDX hari yang terlupa diunggah).
    Snapshot adalah batas waktu data (A4); data yang sudah diketahui sampai tanggal itu tidak
    menjadi tidak diketahui hanya karena berkas yang datang belakangan bertanggal lebih awal.

    Kalender bursa, notasi khusus/suspensi, imbal hasil SUN, aksi korporasi resmi, dan rasio
    bank semuanya masuk lewat sini (PRD 7.1).

    `sudah_dibaca` dipakai pemanggil yang **harus** memperlihatkan isi folder kepada pengguna
    sebelum menulis (jendela, K59 d/T70): yang ditulis adalah objek yang sama dengan yang
    dihitung di ringkasan konfirmasi, bukan hasil pembacaan kedua yang bisa berbeda. Isinya
    wajib berasal dari `berkas.baca_folder(folder)` untuk folder yang sama; `folder` tetap
    dipakai untuk label sumber dan pesan, sehingga jalur tulisnya tetap satu.
    """
    try:
        hasil = sudah_dibaca if sudah_dibaca is not None else berkas.baca_folder(folder)
    except GalatIngesti as galat:
        _catat_log(sambungan, proses=proses, hasil="gagal", pesan=str(galat))
        return LaporanJalan(proses=proses, sukses=False, pesan=str(galat))

    peringatan: list[str] = []
    if hasil.tidak_ada:
        peringatan.append("berkas belum ada dan dilewati: " + ", ".join(hasil.tidak_ada))

    try:
        tanggal_data = berkas.tanggal_data_dari(hasil.kumpulan)
    except GalatIngesti:
        # Impor yang tidak memuat harga (mis. hanya kalender bursa) tetap sah: tanggal datanya
        # diambil dari snapshot terakhir, dan bila belum ada snapshot sama sekali, dipakai
        # tanggal bar terakhir yang bisa ditemukan di antara semua jenis data.
        tanggal_data = _tanggal_data_impor(sambungan, hasil.kumpulan)
    if tanggal_data_minimum is not None:
        tanggal_data = max(tanggal_data, tanggal_data_minimum)

    try:
        tersimpan = ingesti.simpan(
            sambungan,
            hasil.kumpulan,
            tanggal_data=tanggal_data,
            proses=proses,
            catatan=" | ".join(hasil.kumpulan.catatan) or None,
        )
    except (GalatIngesti, db.GalatBasisData, sqlite3.Error) as galat:
        pesan = f"penulisan impor dibatalkan: {galat}"
        if isinstance(galat, db.BasisDataTerkunci):
            # Kuncinya masih dipegang proses lain, jadi menulis log sekarang tidak akan berhasil:
            # ia hanya menambah penantian `busy_timeout` yang **kedua**. Terukur 17 Okt 2026 atas
            # data nyata pada impor yang terkunci: **11,16 detik** (dua penantian 5 detik) —
            # padahal K59 a menyebut satu penantian. Galatnya diteruskan apa adanya supaya
            # pemanggil memakai kalimat bersama + "belum menulis apa pun" (K59 b).
            raise
        _catat_log(sambungan, proses=proses, hasil="gagal", pesan=pesan)
        return LaporanJalan(proses=proses, sukses=False, pesan=pesan, peringatan=peringatan)

    # Laporan mutu mengikuti label harga yang berlaku pada snapshot ini (K14), bukan label
    # folder impor. Impor konfigurasi tidak membawa harga, sehingga label folder seperti
    # "konfigurasi" akan menyaring semua bar harga dan membuat laporan snapshot tampak kosong.
    sumber_harga = potret.harga_dipakai(sambungan, batas=tersimpan.diketahui_pada)
    laporan_mutu = mutu.periksa(sambungan, tanggal_data=tanggal_data, sumber=sumber_harga)
    hasil_arsip: arsip.HasilArsip | None = None
    try:
        hasil_arsip = arsip.tulis(
            sambungan,
            id_snapshot=tersimpan.id_snapshot,
            laporan_mutu=mutu.csv_laporan(laporan_mutu),
        )
    except (GalatIngesti, OSError, lokasi.GalatLokasi) as galat:
        peringatan.append(f"arsip snapshot gagal ditulis: {galat}")
        _catat_log(
            sambungan,
            proses=proses,
            hasil="peringatan",
            pesan=f"snapshot {tersimpan.id_snapshot} tersimpan, tetapi arsipnya gagal: {galat}",
            id_snapshot=tersimpan.id_snapshot,
        )

    if tersimpan.baris.total_kosong_ditolak:  # T90
        peringatan.append(tersimpan.baris.ringkas_kosong_ditolak())
    pesan = (
        f"snapshot {tersimpan.id_snapshot} · tanggal data {tersimpan.tanggal_data} · "
        f"{tersimpan.baris.total_baru} baris baru, {tersimpan.baris.total_tetap} sudah ada dan sama"
    )
    return LaporanJalan(
        proses=proses,
        sukses=True,
        pesan=pesan,
        snapshot=tersimpan,
        laporan_mutu=laporan_mutu,
        arsip=hasil_arsip,
        peringatan=peringatan,
    )


def _tanggal_data_impor(sambungan: sqlite3.Connection, kumpulan: KumpulanData) -> date:
    """Tanggal data untuk impor yang tidak memuat harga sama sekali.

    Urutannya: tanggal terakhir di snapshot terakhir → tanggal terakhir data harga di basis
    data → hari ini. Hanya yang terakhir memakai jam sistem, dan itu dilaporkan apa adanya di
    catatan snapshot supaya tidak tampak seperti tanggal data yang sungguhan.
    """
    baris = sambungan.execute("SELECT MAX(tanggal_data) FROM snapshot").fetchone()
    if baris and baris[0]:
        return date.fromisoformat(baris[0])
    baris = sambungan.execute("SELECT MAX(tanggal) FROM harga_harian").fetchone()
    if baris and baris[0]:
        return date.fromisoformat(baris[0])
    return _tanggal_hari_ini()


# ---------------------------------------------------------------------------------------
# Saring & skor (F2/F3, Tahap 1)
# ---------------------------------------------------------------------------------------


@dataclass
class LaporanSaring:
    """Seluruh hasil satu jalan saring — satu objek untuk dilaporkan ke pengguna dan ke log."""

    id_snapshot: int
    tanggal_data: str
    id_preset: str
    jumlah_emiten: int
    jumlah_likuid: int
    jumlah_lolos: int
    jumlah_dinilai: int
    jumlah_tidak_bisa_dinilai: int
    breadth: metrik.Nilai | None
    rezim: str
    skor: tuple[skor.HasilSkor, ...] = ()
    hasil_saring: tuple[saring.HasilSaring, ...] = ()
    peringatan: list[str] = field(default_factory=list)
    #: Label sumber harga yang dipakai berhitung, dan seluruh label yang ada beserta jumlah
    #: barnya (P17). Dibawa sampai laporan dengan sengaja: angka di layar berasal dari **satu**
    #: sumber, dan sumber mana itu bukan detail teknis — kalau ia tidak terlihat, dua snapshot
    #: dengan sumber berbeda akan tampak sebanding padahal bukan.
    sumber_harga: str | None = None
    sumber_tersedia: tuple[tuple[str, int], ...] = ()
    #: Label yang menyumbang bar pada deret yang dipakai: satu, atau dua pada sambungan K97.
    label_dipakai: tuple[str, ...] = ()
    #: Jumlah bar yang benar-benar dimuat per label (K97 e).
    bar_per_label: tuple[tuple[str, int], ...] = ()
    #: Apakah status notasi khusus emiten sudah bisa diverifikasi (ada datanya). `False` berarti
    #: daftar yang keluar adalah **peringkat sementara**, bukan kandidat (PRD 7.3) — dan lapisan
    #: pelaporan wajib menyebutnya begitu, bukan menyebutnya kandidat.
    notasi_terverifikasi: bool = True
    #: Sebab peringkat sementara dari deret sambungan (K97 d: hari bolong di jendela metrik, atau
    #: kalender yang belum memuat rentangnya); `None` bila tidak ada.
    sambungan_sementara: str | None = None
    #: Sebaran `jenis` emiten pada potret ini (K21). Dibawa sampai laporan sebab begitu `jenis`
    #: terisi, set kriteria yang berlaku **berubah**: kriteria bank mulai diterapkan dan
    #: DER/coverage/CFO-NI berhenti dihitung untuk bank (PRD 8.4, AC-16). Perubahan sebesar itu
    #: tidak boleh hanya terlihat dari angka yang bergeser.
    keadaan_jenis: jenis.KeadaanJenis = jenis.KeadaanJenis()

    @property
    def peringkat_sementara(self) -> bool:
        """Daftar ini belum boleh disebut kandidat (PRD 7.3; K97 d)."""
        return not self.notasi_terverifikasi or self.sambungan_sementara is not None

    def sebab_sementara(self) -> str:
        """Kalimat sebab peringkat sementara untuk layar; kosong bila tidak sementara."""
        return saring.sebab_peringkat_sementara(
            notasi_lengkap=self.notasi_terverifikasi,
            sambungan_sementara=self.sambungan_sementara,
        )

    def teratas(self, jumlah: int = 20) -> tuple[skor.HasilSkor, ...]:
        """Kandidat teratas menurut peringkat (hanya yang diperingkat, urut naik)."""
        layak = [satu for satu in self.skor if satu.peringkat is not None]
        return tuple(sorted(layak, key=lambda satu: satu.peringkat or 0)[:jumlah])

    def catatan_peringkat_kosong(self) -> str:
        """Sebab tidak ada yang bisa diperingkat — **bukan** "tidak ada saham bagus".

        Dipakai dua tempat: baris perintah dan panel jendela. Daftar kosong tanpa sebab akan
        terbaca sebagai penilaian tentang pasar, padahal artinya biasanya penilaian tentang
        data yang belum diimpor. Ambangnya dipinjam dari `skor`, bukan ditulis ulang sebagai
        angka, supaya kalimat ini tidak berbohong begitu ambangnya berubah.
        """
        return (
            "Tidak ada kandidat yang bisa diperingkat. Sebabnya ada di rincian di atas; faktor "
            f"dinilai hanya bila >= {skor.AMBANG_KETERSEDIAAN_FAKTOR:.0%} bobot metriknya "
            "tersedia (biasanya karena fundamental belum diimpor lewat fundamental.csv)."
        )

    def sumber_ringkas(self) -> str:
        """Satu baris tentang sumber harga: yang dipakai, dan yang tidak dipakai berhitung."""
        if self.sumber_harga is None:
            return "  harga: belum ada bar harga sama sekali di basis data"
        if len(self.label_dipakai) > 1:
            rincian = ", ".join(
                f"{label!r} {tampilan.angka(banyak, 0)} bar" for label, banyak in self.bar_per_label
            )
            teks = f"  harga dari deret sambungan {self.sumber_harga!r} ({rincian})"
            diabaikan = tuple(satu for satu in self.sumber_tersedia if satu[0] not in self.label_dipakai)
            if diabaikan:
                lain = ", ".join(f"{label!r} ({tampilan.angka(banyak, 0)} bar)" for label, banyak in diabaikan)
                teks += f" · tidak dipakai berhitung: {lain}"
            return teks
        jumlah = next(
            (banyak for label, banyak in self.sumber_tersedia if label == self.sumber_harga), None
        )
        teks = f"  harga dari sumber {self.sumber_harga!r}"
        if jumlah is not None:
            teks += f" ({tampilan.angka(jumlah, 0)} bar)"
        diabaikan = tuple(satu for satu in self.sumber_tersedia if satu[0] != self.sumber_harga)
        if diabaikan:
            lain = ", ".join(f"{label!r} ({tampilan.angka(banyak, 0)} bar)" for label, banyak in diabaikan)
            teks += f" · tidak dipakai berhitung: {lain} (pakai --sumber untuk menimpanya)"
        return teks

    def ringkas(self) -> str:
        # Saat status notasi belum bisa diverifikasi, kata "lolos saring" tidak boleh berdiri
        # sendiri: ia terbaca sebagai "kandidat" padahal PRD 7.3 belum terpenuhi (lihat
        # `notasi_terverifikasi`). Keadaannya disebut pada barisnya sendiri.
        if not self.notasi_terverifikasi:
            lolos_teks = f"lolos kriteria lain {self.jumlah_lolos} (notasi belum diverifikasi)"
        elif self.sambungan_sementara is not None:
            lolos_teks = f"lolos saring {self.jumlah_lolos} (peringkat sementara: harga resmi bolong)"
        else:
            lolos_teks = f"lolos saring {self.jumlah_lolos}"
        bagian = [
            f"[saring] snapshot {self.id_snapshot} · tanggal data {self.tanggal_data} · "
            f"preset {self.id_preset}",
            f"  emiten {self.jumlah_emiten} · likuid {self.jumlah_likuid} · "
            f"{lolos_teks} · dinilai {self.jumlah_dinilai}",
            self.sumber_ringkas(),
        ]
        if self.breadth is not None and self.breadth.ada:
            bagian.append(
                f"  breadth {float(self.breadth.nilai or 0):.1%} · rezim {self.rezim}"
                .replace(".", ",")
            )
        else:
            alasan = self.breadth.alasan if self.breadth is not None else "tidak dihitung"
            bagian.append(f"  breadth tidak dihitung ({alasan}) · rezim {self.rezim}")
        if self.jumlah_tidak_bisa_dinilai:
            bagian.append(
                f"  {self.jumlah_tidak_bisa_dinilai} emiten tidak bisa disaring karena metriknya "
                "tidak dihitung (lihat alasannya di rincian)"
            )
        # Keadaan `jenis` selalu tampil, bukan hanya ketika ada yang kosong: yang berubah ketika
        # kolomnya terisi adalah **aturan yang berlaku**, dan itu harus terbaca walaupun seluruh
        # emiten sudah ber-jenis (K21 batas (c)).
        bagian.append(self.keadaan_jenis.ringkas())
        bagian.extend(f"  PERINGATAN: {satu}" for satu in self.peringatan)
        return "\n".join(bagian)


def jalankan_saring(
    sambungan: sqlite3.Connection,
    preset: saring.Preset,
    *,
    id_snapshot: int | None = None,
    hanya_kode: Sequence[str] | None = None,
    simpan: bool = True,
    sumber: str | None = None,
    bahan: potret.Potret | None = None,
    angka: Mapping[str, Mapping[str, metrik.Nilai]] | None = None,
) -> LaporanSaring:
    """Jalankan saringan + skoring preset atas satu snapshot, lalu simpan skornya.

    Urutannya mengikat dan disebut PRD 9.5: metrik → saring → semesta likuid → statistik sektor
    → skor → peringkat. Semesta likuid dihitung dari ADTV20 **dan** pengecualian notasi (K9),
    bukan dari hasil saringan, supaya skalanya tidak bergeser mengikuti ambang saringan.

    `hanya_kode` membatasi emiten yang **dilaporkan**, bukan yang dipakai menghitung: statistik
    sektor tetap berasal dari seluruh semesta likuid (PRD 9.5), karena kalau tidak, skor satu
    emiten akan berubah hanya karena ia sedang diperiksa sendirian. Peringkatnya pun diberikan
    atas seluruh emiten yang lolos, baru disaring. Karena daftarnya parsial,
    pemanggil yang memakai `hanya_kode` **tidak boleh** menyimpannya sebagai peringkat penuh —
    itulah gunanya `simpan=False` (dan `skor.simpan_skor` menulis ulang per snapshot+preset).

    `sumber` menimpa label sumber harga yang dipakai berhitung (P17); bawaannya label dengan
    riwayat bar terbanyak pada saat snapshot itu. Label yang dipilih **selalu** masuk laporan,
    dan adanya label lain yang tidak dipakai menjadi peringatan — sebab angka dari dua sumber
    yang bercampur atau dari sumber yang salah terlihat sama sehatnya di layar.

    `bahan` = potret yang sudah dimuat pemanggil (detail emiten): memuatnya lagi memakan ±20 dtk
    di data kerja. Snapshot dan sumbernya sudah ditetapkan potret itu, jadi `id_snapshot` atau
    `sumber` yang ikut diberikan ditolak, bukan diabaikan diam-diam. `angka` = metrik seluruh
    emiten atas `bahan` itu (simpanan potret web, T99); tanpa `bahan` ia ditolak, karena metrik
    milik potret lain akan terbaca sebagai milik snapshot ini.
    """
    if angka is not None and bahan is None:
        raise ValueError("jalankan_saring: angka hanya sah bersama bahan yang menghasilkannya")
    if bahan is None:
        bahan = potret.muat(sambungan, id_snapshot, sumber=sumber)
    elif id_snapshot is not None or sumber is not None:
        raise ValueError(
            "jalankan_saring: bahan sudah menetapkan snapshot dan sumber harganya; "
            "jangan berikan id_snapshot atau sumber bersamanya"
        )
    if angka is None:
        angka = metrik.metrik_semua(bahan)
    likuid = saring.semesta_likuid(bahan, preset, metrik=angka)
    # Median sektor untuk kriteria relatif dihitung dari semesta likuid, sejalan dengan
    # statistik sektor untuk skoring (PRD 9.5).
    semua_saring = saring.saring_semesta(bahan, preset, metrik=angka, semesta=likuid)

    dipilih = set(hanya_kode) if hanya_kode is not None else None
    hasil_saring = tuple(
        satu for satu in semua_saring if dipilih is None or satu.kode in dipilih
    )
    # Peringkat diberikan atas seluruh yang lolos, baru disaring ke `hanya_kode`: peringkat di
    # antara kode yang sedang diperiksa saja selalu "1" untuk satu kode (sesi 67).
    semua_lolos = tuple(satu.kode for satu in semua_saring if satu.lolos)
    lolos = tuple(kode for kode in semua_lolos if dipilih is None or kode in dipilih)
    hasil_skor = tuple(
        satu
        for satu in skor.skor_semesta(bahan, preset, likuid, semua_lolos, angka)
        if dipilih is None or satu.kode in dipilih
    )

    nilai_breadth = metrik.breadth(bahan, likuid)
    rezim = metrik.rezim_pasar(bahan, nilai_breadth)
    peringatan: list[str] = []
    jumlah = 0
    if simpan:
        jumlah = skor.simpan_skor(sambungan, bahan, preset, hasil_skor)
        # K61: konteks pasar yang baru dihitung di atas disimpan supaya dasbor tidak menghitungnya
        # ulang. Ditulis **sesudah** skor, dan kegagalannya hanya peringatan: skor sudah tersimpan
        # dan angkanya benar; yang hilang hanyalah jalan pintas, bukan hasil saringan. Kegagalan
        # tetap berisik (aturan keras 7), tidak ditelan.
        try:
            konteks_pasar.simpan(
                sambungan,
                konteks_pasar.dari_bahan(
                    bahan,
                    nilai_breadth,
                    rezim,
                    preset=preset.id_preset,
                    catatan=konteks_pasar.sebab_bahan_kurang(bahan, nilai_breadth),
                ),
                id_snapshot=bahan.id_snapshot,
                id_preset=preset.id_preset,
                sumber=bahan.sumber_harga,
            )
        except (sqlite3.Error, db.GalatBasisData) as galat:
            peringatan.append(
                "konteks pasar tidak tersimpan; dasbor akan menghitung ulang "
                f"(hasil saringan tetap sah): {galat}"
            )
    if bahan.sumber_diabaikan:
        lain = ", ".join(
            f"{label!r} ({tampilan.angka(banyak, 0)} bar)"
            for label, banyak in bahan.sumber_diabaikan
        )
        peringatan.append(
            f"harga dibaca dari satu sumber saja: {bahan.sumber_harga!r} "
            f"({tampilan.angka(bahan.bar_sumber_harga or 0, 0)} bar). Tidak dipakai berhitung: "
            f"{lain}. Dua label dalam satu deret membuat hari terduplikasi dan ADTV20 emiten "
            "jatuh menjadi 'tidak dihitung' (P17); pakai --sumber untuk memilih label lain."
        )
    if not simpan:
        peringatan.append(
            "hasil TIDAK disimpan: --kode hanya melaporkan sebagian emiten, dan menyimpannya akan "
            "menimpa peringkat penuh snapshot ini"
        )
    dinilai = [satu for satu in hasil_skor if satu.diperingkat]
    if len(dinilai) < len(lolos):
        peringatan.append(
            f"{len(lolos) - len(dinilai)} emiten lolos saring tetapi tidak diperingkat "
            "(faktor yang bisa dinilai kurang dari 3)"
        )
    if not likuid:
        peringatan.append(
            "tidak ada emiten likuid: statistik sektor tidak bisa dihitung, sehingga tidak ada "
            "skor yang bisa dibandingkan"
        )
    if not bahan.sun:
        peringatan.append(
            "imbal hasil SUN belum ada di basis data: metrik 'imbal hasil laba − SUN' berstatus "
            "tidak dihitung sampai berkasnya diimpor"
        )
    # PRD 7.3: data notasi harus ada dan lengkap sebelum peringkat boleh disebut kandidat.
    # Penanda aktivitas massal dibawa di `keterangan` saat impor; komentar CSV saja tidak cukup
    # karena komentar tidak masuk ke basis data.
    notasi_terverifikasi = saring.notasi_terverifikasi(bahan.notasi)
    notasi_tidak_lengkap = bool(bahan.notasi) and not notasi_terverifikasi
    if not notasi_terverifikasi:
        if notasi_tidak_lengkap:
            peringatan.append(
                "data suspensi IDX belum lengkap karena aksi pengumuman multi-kode belum direkonsiliasi per emiten; "
                "status notasi seluruh emiten belum terverifikasi, sehingga daftar di bawah ini "
                "PERINGKAT SEMENTARA — bukan kandidat (PRD 7.3)."
            )
        else:
            peringatan.append(
                "data notasi khusus (suspensi/UMA/papan pemantauan) belum ada: status seluruh emiten "
                "belum terverifikasi, sehingga daftar di bawah ini PERINGKAT SEMENTARA — bukan "
                "kandidat (PRD 7.3). Saham yang sedang tersuspensi bisa ikut muncul di dalamnya."
            )
    # K97 (b, d): gerbang sambungan dan hari bolong disebut di laporan saring, bukan hanya di
    # laporan mutu — yang membaca peringkat harus melihat sebab angkanya tidak lengkap.
    keadaan_sambungan = bahan.keadaan_sambungan
    sambungan_sementara = keadaan_sambungan.sementara if keadaan_sambungan is not None else None
    if keadaan_sambungan is not None and keadaan_sambungan.ditolak:
        peringatan.append(
            keadaan_sambungan.ringkas()
            + "; metrik harga emiten yang ditolak tidak dihitung (alasannya di rincian kriteria)"
        )
    if sambungan_sementara is not None:
        peringatan.append(
            f"{sambungan_sementara}, sehingga daftar di bawah ini PERINGKAT SEMENTARA — bukan "
            "kandidat (K97 d)."
        )
    # Jenis emiten menentukan set kriteria mana yang berlaku (PRD 8.4, AC-16). Keadaannya
    # dilaporkan **terbedakan** (K21 batas (c)): berapa yang bank_keuangan dari data, berapa
    # yang umum, dan berapa yang masih kosong. Satu angka "belum terisi" saja akan
    # menyembunyikan justru bagian yang sudah bekerja — begitu `jenis` terisi, kriteria bank
    # mulai berlaku dan DER/coverage/CFO-NI berhenti dihitung untuk bank.
    keadaan_jenis = jenis.KeadaanJenis.dari(
        {kode: bahan.emiten[kode].jenis for kode in bahan.kode}
    )
    peringatan_jenis = keadaan_jenis.peringatan()
    if peringatan_jenis:
        peringatan.append(peringatan_jenis)

    _catat_log(
        sambungan,
        proses="saring",
        hasil="peringatan" if peringatan else "sukses",
        pesan=(
            f"preset {preset.id_preset}: {len(lolos)} lolos dari {len(hanya_kode or bahan.kode)} "
            f"emiten, {jumlah} skor disimpan"
        ),
        id_snapshot=bahan.id_snapshot,
    )

    return LaporanSaring(
        id_snapshot=bahan.id_snapshot,
        tanggal_data=bahan.tanggal_data.isoformat(),
        id_preset=preset.id_preset,
        jumlah_emiten=len(bahan.kode),
        jumlah_likuid=len(likuid),
        jumlah_lolos=len(lolos),
        jumlah_dinilai=len(dinilai),
        jumlah_tidak_bisa_dinilai=sum(1 for satu in hasil_saring if satu.tidak_bisa_dinilai),
        breadth=nilai_breadth,
        rezim=rezim,
        skor=hasil_skor,
        hasil_saring=hasil_saring,
        peringatan=peringatan,
        sumber_harga=bahan.sumber_harga,
        notasi_terverifikasi=notasi_terverifikasi,
        sambungan_sementara=sambungan_sementara,
        sumber_tersedia=bahan.sumber_tersedia,
        label_dipakai=bahan.label_dipakai,
        bar_per_label=bahan.bar_per_label if len(bahan.label_dipakai) > 1 else (),
        keadaan_jenis=keadaan_jenis,
    )


def cek_sumber_kedua(
    sambungan: sqlite3.Connection,
    *,
    sumber_utama: str | potret.PilihanHarga | None = None,
    sumber_pembanding: str | None = None,
    id_snapshot: int | None = None,
    momen: datetime | None = None,
) -> mutu.LaporanPerbandingan:
    """Bandingkan penutupan emiten teratas terhadap sumber kedua (PRD 7.3).

    Dipisah dari `jalankan_refresh` dengan sengaja: PRD menuntut pemeriksaan ini **tiap minggu**,
    sedangkan refresh berjalan tiap hari. Menempelkannya pada refresh berarti menjalankannya
    berkali-kali lipat dari yang diminta, dan menjalankannya di sini berarti pemanggil yang
    menentukan kapan — bukan kode yang menebak dari jam dinding.

    `sumber_utama` bawaannya adalah deret yang sedang dipakai berhitung (`potret.harga_dipakai`):
    label dengan **riwayat bar terbanyak**, atau sejak tanggal sambung (K97) label resmi — dan
    label riwayat menjadi pembandingnya. Satu fungsi yang sama dengan perhitungan, supaya tidak
    ada dua jawaban untuk satu pertanyaan. Yang dihitung **seluruh barisnya**, bukan baris pada tanggal snapshot saja: harga
    pembanding biasanya hanya diimpor untuk beberapa tanggal, sehingga menghitung baris pada satu
    tanggal bisa membuat sumber pembanding terpilih sebagai sumber utama — dan hasilnya "peringkat
    ADTV20 tidak bisa dihitung" yang menyesatkan, bukan perbandingan yang diminta.

    Setiap jalan **dicatat** sebagai peristiwa (`mutu.catat_cek_sumber_kedua`), termasuk jalan
    yang belum lengkap: tanpa catatan itu, tuntutan mingguan PRD 7.3 tidak bisa diperiksa dan
    hanya bisa diasumsikan. `momen` hanya untuk pengujian; bawaannya jam sistem, sama seperti
    pencatatan waktu di seluruh aplikasi.
    """
    if sumber_utama is None:
        # Deret lengkap diteruskan, bukan satu label: peringkat ADTV20 butuh 20 hari dari deret
        # sambungan, sedangkan `bandingkan_sumber_kedua` sendiri memilih label hari datanya —
        # sejak tanggal sambung label resmi, dan label riwayat menjadi pembanding (K97 f).
        sumber_utama = potret.harga_dipakai(sambungan)

    tanggal = potret.snapshot_terakhir(sambungan)["tanggal_data"]
    laporan = mutu.bandingkan_sumber_kedua(
        sambungan,
        tanggal_data=date.fromisoformat(tanggal),
        sumber_utama=sumber_utama,
        sumber_pembanding=sumber_pembanding,
    )
    # Dicatat sebelum dilaporkan: yang dicatat adalah **peristiwanya**, dan peristiwa itu sudah
    # terjadi apa pun hasil perbandingannya — termasuk ketika ia menemukan selisih (kode keluar
    # pemeriksaan itu bukan nol, tetapi ceknya tetap sudah dijalankan).
    mutu.catat_cek_sumber_kedua(sambungan, laporan, momen=momen)
    _catat_log(
        sambungan,
        proses="cek-sumber-kedua",
        hasil="peringatan" if laporan.ditandai or laporan.belum_dapat_dijalankan else "sukses",
        pesan=(
            f"{len(laporan.diperiksa)} emiten diperiksa terhadap {laporan.sumber_pembanding or '(tidak ada)'}: "
            f"{len(laporan.ditandai)} selisih di atas ambang"
            + (f"; belum dapat dijalankan: {'; '.join(laporan.belum_dapat_dijalankan)}"
               if laporan.belum_dapat_dijalankan else "")
        ),
    )
    return laporan


def siapkan_preset_bawaan(sambungan: sqlite3.Connection, hari_ini: date | None = None) -> tuple[str, ...]:
    """Simpan preset bawaan (K1) yang belum ada. Kembalikan daftar preset yang baru ditulis."""
    baru: list[str] = []
    for satu in saring.preset_bawaan(hari_ini or _tanggal_hari_ini()):
        if saring.simpan_preset(sambungan, satu):
            baru.append(satu.id_preset)
    return tuple(baru)
