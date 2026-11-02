"""Transaksi & posisi (F11, PRD 9.11) — dari rencana yang disetujui menjadi posisi yang ditinjau.

PRD 9.1 menutup alurnya begini: *"8 Eksekusi manual di sekuritas → 9 Catat transaksi → 10 Tinjau
jurnal & kepatuhan"*. Modul ini mengerjakan langkah 9, dan tiga hal yang membuatnya bukan sekadar
"tabel transaksi":

1. **`transaksi` adalah satu-satunya sumber angka.** `posisi` **tidak** menyimpan `lembar` maupun
   `harga_rata` walaupun PRD 12 menyebutnya: keduanya turunan dari transaksi, dan menyimpannya
   berarti ada dua jawaban untuk satu pertanyaan. Begitu keduanya berbeda, tidak ada cara
   mengetahui mana yang benar — dan yang dirugikan adalah keputusan berikutnya. Karena itu
   `hitungan()` di modul ini satu-satunya tempat lembar, harga rata-rata, dan hasil dihitung.
   Yang disimpan di `posisi` hanyalah yang tidak bisa diturunkan dari mana pun: kapan dibuka dan
   ditutup, stop terkini, mode, dan pelanggaran.

2. **Pelanggaran dicatat, bukan dicegah** (PRD 9.8). Katalognya V1–V7, dan seluruhnya punya
   tempat deteksinya masing-masing: V1/V2/V6 di sini (saat transaksinya dicatat), V5 di sini juga
   (saat stopnya digeser), sedangkan V3/V4/V7 diturunkan `jurnal.py` dari baris yang sudah ada.
   Eksekusi yang sudah terjadi di sekuritas tetap harus bisa dicatat apa adanya; yang tidak boleh
   adalah ia tercatat **seolah patuh**. Katalog kodenya sendiri tinggal di sini, sebab ia yang
   dipakai baris yang mencatatnya — dan `jurnal.KATALOG` meminjamnya, bukan menyalinnya.

3. **Mode simulasi/nyata tidak boleh hilang** (PRD 9.11). Selama masa simulasi (Q7), hanya data
   simulasi yang dipakai menilai preset, dan metrik kedua mode dilaporkan terpisah. Karena itu
   `mode` wajib pada setiap transaksi dan posisi — mode yang tidak dinyatakan akan membuat
   pemisahan itu mustahil dilakukan belakangan.

**Harga tidak diambil dari `potret.muat`.** Posisi adalah keadaan **sekarang**, bukan isi satu
snapshot: yang ditanyakan "berapa penutupan terakhir dan apakah stop sudah tertembus", dan
jawabannya tidak berubah karena ada snapshot baru. Membaca seluruh potret (sejuta baris pada data
nyata) untuk tiga posisi juga ongkos yang tidak sepadan. Yang tetap berlaku adalah aturan **satu
label sumber harga** (T32): penutupan dibaca dari label yang sama dengan yang dipakai berhitung,
dan label itu disebut di keluaran.

**Aksi korporasi pada posisi (PRD 9.11), dan mengapa hampir semuanya diturunkan.** PRD menuntut
"split dan reverse split menyesuaikan lembar dan stop **otomatis**", dan PRD 7.2 sudah menetapkan
polanya untuk harga: disimpan mentah, penyesuaian dihitung saat dibaca. Yang **disimpan** karena
tidak bisa diturunkan dari mana pun hanyalah basis tanggal stop (`posisi.tgl_stop`) dan keputusan
right issue (`keputusan_right_issue`, migrasi 013). Sisanya diturunkan di sini:

1. **lembar & harga rata-rata** — dari transaksi, dengan tiap transaksi diskalakan ke basis
   sekarang oleh split yang terjadi **setelah** tanggal eksekusinya (`penyesuaian.faktor_lembar`).
   Uang yang dibayar tidak ikut berubah: split tidak mengubah nilai posisi. Sebelum ini, posisi
   yang melewati split menampilkan lembar, harga rata-rata, dan risiko yang **salah tanpa satu pun
   tanda** — dan angka itu yang dipakai menghitung risiko.
2. **stop** — level stop adalah angka yang dicatat manusia, jadi artinya bergantung pada basis
   harga saat ia dinyatakan (`posisi.tgl_stop`, migrasi 013). Stop lama dikalikan kebalikan faktor
   lembar (`1 / faktor_lembar`), sebab harga dan lembar bergerak berlawanan arah. Baris lama yang
   **belum** menyatakan basisnya tidak dikonversi diam-diam: begitu ada split setelah baris itu
   dicatat, risikonya berstatus **tidak dinilai** beserta sebabnya — lebih baik daripada angka
   yang dipilih dari dua kemungkinan tanpa dasar.
3. **dividen** — `dividen_per_saham` yang tersimpan sudah dalam basis sekarang (diukur atas 33
   split nyata: 6 → 6 melewati split 1:5, 8 → 8 melewati 1:10), sehingga pasangannya adalah lembar
   dalam basis sekarang juga. Dividen masuk hasil sebagai suku **terpisah** — ia bukan hasil
   perdagangan, dan mencampurnya akan membuat "hasil" berarti dua hal. Pajaknya **tidak**
   dihitung: perlakuan PPh dividen bergantung status wajib pajak dan apakah dividennya
   diinvestasikan kembali, dan itu bukan parameter bursa yang boleh ditetapkan aplikasi.
4. **right issue** — yang diturunkan hanya **haknya** (perkiraan lembar HMETD) sebagai petunjuk
   yang menyebut dasarnya; keputusan tebus/jual/abaikan adalah **tindakan manusia** dan disimpan
   di `keputusan_right_issue`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from fractions import Fraction

from mejasaham import db, konfigurasi, penyesuaian, potret, risiko, tampilan
from mejasaham.ingesti import AksiKorporasi
from mejasaham.skema import KEPUTUSAN_RIGHT_ISSUE_SAH, MODE_SAH

#: PRD 5: hanya posisi beli (long) — tidak ada short, margin, atau derivatif.
AKSI_SAH: tuple[str, ...] = ("beli", "jual")

STATUS_SAH: tuple[str, ...] = ("aktif", "ditutup")

#: Dari mana angka biaya datang. `None` (biaya tidak diketahui) berbeda dari keduanya.
ASAL_BIAYA_SAH: tuple[str, ...] = ("dicatat_pengguna", "dihitung_dari_tarif")

SUMBER_TRANSAKSI = "dicatat pengguna lewat --catat-transaksi"
SUMBER_STOP = "dicatat pengguna lewat --ubah-stop"
SUMBER_KEPUTUSAN_RIGHT_ISSUE = "dicatat pengguna lewat --putuskan-right-issue"

#: Aksi korporasi yang berlaku pada posisi (PRD 9.11). `split`/`reverse_split` mengubah lembar &
#: stop, `right_issue` memunculkan tenggat & keputusan, `dividen` menjadi arus kas dan hasil.
JENIS_AKSI_POSISI: tuple[str, ...] = ("split", "reverse_split", "right_issue", "dividen")

#: Sebab-sebab sebuah angka tidak dapat dinilai, disebut apa adanya di keluaran (aturan keras 2).
ASAL_BASIS_STOP_DINYATAKAN = "dinyatakan"
ASAL_BASIS_STOP_DARI_PENCATATAN = "dari_waktu_pencatatan"

#: Katalog pelanggaran PRD 9.8 seluruhnya. Kodenya dipakai apa adanya supaya rekap kepatuhan
#: (`jurnal.py`, PRD 13.1) memakai kode yang sama dengan yang tercatat di baris. Yang dideteksi di
#: modul ini V1/V2/V5/V6; V3/V4/V7 diturunkan `jurnal.py` dari rencana, transaksi, dan posisi —
#: tempatnya disebut `jurnal.DIDETEKSI_DI`, dan hanya ada **satu** tempat per kode (T44).
PELANGGARAN: Mapping[str, str] = {
    "V1": "masuk tanpa stop awal",
    "V2": "lembar melebihi rencana",
    "V3": "melewati batas bobot/sektor/total risiko",
    "V4": "menambah posisi rugi tanpa tesis baru",
    "V5": "stop digeser menjauhi harga",
    "V6": "transaksi tanpa rencana tersimpan",
    "V7": "posisi dipertahankan setelah pembatal tesis terpicu",
}


class GalatPosisi(RuntimeError):
    """Kesalahan yang pesannya sudah ditujukan untuk pengguna, bukan traceback (aturan keras 7)."""


def sebut_pelanggaran(kode: str) -> str:
    """`V1` → `V1 (masuk tanpa stop awal)`; kode yang tidak dikenal dikembalikan apa adanya."""
    if kode in PELANGGARAN:
        return f"{kode} ({PELANGGARAN[kode]})"
    return kode


def _kode_pelanggaran(teks: str | None) -> tuple[str, ...]:
    return tuple(satu for satu in (teks or "").split(";") if satu)


def _gabung_pelanggaran(baru: Iterable[str], lama: str | None = None) -> str | None:
    """Gabungkan kode pelanggaran tanpa menggandakan, urut kode."""
    kumpulan = {*_kode_pelanggaran(lama), *(satu for satu in baru if satu)}
    return ";".join(sorted(kumpulan)) or None


# ---------------------------------------------------------------------------------------
# Bentuk baris
# ---------------------------------------------------------------------------------------

_KOLOM_TRANSAKSI = (
    "id_transaksi",
    "revisi",
    "id_posisi",
    "id_rencana",
    "tanggal",
    "kode",
    "aksi",
    "harga",
    "lembar",
    "biaya",
    "asal_biaya",
    "pajak",
    "mode",
    "pelanggaran",
    "catatan",
    "sumber",
    "diketahui_pada",
)

_KOLOM_POSISI = (
    "id_posisi",
    "revisi",
    "kode",
    "tgl_buka",
    "tgl_tutup",
    "status",
    "stop_terkini",
    # Basis tanggal level stop (migrasi 013). NULL hanya pada baris lama yang belum
    # menyatakannya — dan itu diperlakukan sebagai "tidak dinyatakan", bukan ditebak.
    "tgl_stop",
    "id_rencana",
    "mode",
    "pelanggaran",
    "catatan",
    "sumber",
    "diketahui_pada",
)

_KOLOM_AKSI = (
    "kode",
    "tanggal",
    "jenis",
    "rasio_lama",
    "rasio_baru",
    "harga_tebus",
    "dividen_per_saham",
    "tenggat",
    "keterangan",
)

_KOLOM_KEPUTUSAN = (
    "id_keputusan",
    "revisi",
    "id_posisi",
    "kode",
    "tanggal_aksi",
    "keputusan",
    "id_transaksi",
    "lembar",
    "harga",
    "biaya",
    "catatan",
    "sumber",
    "diketahui_pada",
)


@dataclass(frozen=True)
class Transaksi:
    """Satu revisi catatan eksekusi. Revisi terakhir = yang berlaku."""

    id_transaksi: int
    revisi: int
    id_posisi: int
    id_rencana: int | None
    tanggal: str
    kode: str
    aksi: str
    harga: int
    lembar: int
    biaya: int | None
    asal_biaya: str | None
    pajak: int | None
    mode: str
    pelanggaran: str | None
    catatan: str | None
    sumber: str
    diketahui_pada: str

    @property
    def nilai(self) -> int:
        """Nilai bruto transaksi (harga × lembar); biaya dan pajak tidak termasuk."""
        return self.harga * self.lembar

    @property
    def kode_pelanggaran(self) -> tuple[str, ...]:
        return _kode_pelanggaran(self.pelanggaran)

    def ringkas(self) -> str:
        bagian = [
            f"#{self.id_transaksi} r{self.revisi}",
            self.tanggal,
            self.kode,
            self.aksi,
            f"{tampilan.angka(self.lembar, 0)} lbr @ {tampilan.rupiah(self.harga)}",
            f"nilai {tampilan.rupiah(self.nilai)}",
            f"biaya {tampilan.rupiah(self.biaya) if self.biaya is not None else '(belum dicatat)'}",
            self.mode,
        ]
        if self.id_rencana is None:
            bagian.append("tanpa rencana")
        else:
            bagian.append(f"rencana #{self.id_rencana}")
        teks = " · ".join(bagian)
        if self.pelanggaran:
            teks += "\n      PELANGGARAN: " + "; ".join(
                sebut_pelanggaran(satu) for satu in self.kode_pelanggaran
            )
        return teks


@dataclass(frozen=True)
class Posisi:
    """Satu revisi posisi. Revisi terakhir = keadaan sekarang."""

    id_posisi: int
    revisi: int
    kode: str
    tgl_buka: str
    tgl_tutup: str | None
    status: str
    stop_terkini: int | None
    tgl_stop: str | None
    id_rencana: int | None
    mode: str
    pelanggaran: str | None
    catatan: str | None
    sumber: str
    diketahui_pada: str

    @property
    def aktif(self) -> bool:
        return self.status == "aktif"

    @property
    def kode_pelanggaran(self) -> tuple[str, ...]:
        return _kode_pelanggaran(self.pelanggaran)


def _ke_transaksi(baris: sqlite3.Row) -> Transaksi:
    return Transaksi(**{kolom: baris[kolom] for kolom in _KOLOM_TRANSAKSI})


def _ke_posisi(baris: sqlite3.Row) -> Posisi:
    return Posisi(**{kolom: baris[kolom] for kolom in _KOLOM_POSISI})


def _ke_aksi(baris: sqlite3.Row) -> AksiKorporasi:
    return AksiKorporasi(
        kode=baris["kode"],
        tanggal=date.fromisoformat(baris["tanggal"]),
        jenis=baris["jenis"],
        rasio_lama=baris["rasio_lama"],
        rasio_baru=baris["rasio_baru"],
        harga_tebus=baris["harga_tebus"],
        dividen_per_saham=baris["dividen_per_saham"],
        tenggat=baris["tenggat"],
        sumber=baris["sumber"],
        keterangan=baris["keterangan"],
    )


def _ke_keputusan(baris: sqlite3.Row) -> "KeputusanRightIssue":
    return KeputusanRightIssue(**{kolom: baris[kolom] for kolom in _KOLOM_KEPUTUSAN})


def aksi_korporasi(
    sambungan: sqlite3.Connection, kode: Iterable[str]
) -> dict[str, tuple[AksiKorporasi, ...]]:
    """Aksi korporasi per kode, dari revisi terakhir tiap baris (`v_aksi_korporasi_terkini`).

    Dipisah dari `potret.muat` dengan alasan yang sama seperti `harga_terakhir`: posisi adalah
    keadaan **sekarang**, dan membaca seluruh potret (1.000+ baris aksi pada data nyata, dan
    seluruh bar harga) untuk beberapa posisi adalah ongkos yang tidak sepadan.
    """
    daftar = tuple({satu.strip().upper() for satu in kode if satu and satu.strip()})
    if not daftar:
        return {}
    tanda = ", ".join("?" for _ in daftar)
    hasil: dict[str, list[AksiKorporasi]] = {}
    for baris in sambungan.execute(
        f"SELECT * FROM v_aksi_korporasi_terkini WHERE kode IN ({tanda}) ORDER BY tanggal, jenis",
        daftar,
    ):
        hasil.setdefault(baris["kode"], []).append(_ke_aksi(baris))
    return {kunci: tuple(nilai) for kunci, nilai in hasil.items()}


# ---------------------------------------------------------------------------------------
# Hitungan yang diturunkan dari transaksi (satu-satunya tempat lembar & hasil dihitung)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HitunganPosisi:
    """Turunan transaksi: lembar terbuka, harga rata-rata, dan biaya per sisi.

    Harga rata-rata memakai **metode biaya rata-rata** (weighted average): seluruh pembelian
    dirata-ratakan, dan penjualan mengurangi lembar tanpa mengubah harga rata-ratanya. Metode ini
    yang paling sederhana yang bisa diperiksa ulang dari barisnya sendiri; FIFO menuntut urutan
    lot yang tidak disimpan di mana pun (dan menyimpannya berarti menambah satu sumber kebenaran
    lagi).

    **Lembar di sini sudah dalam basis sekarang** (split setelah tanggal tiap transaksi sudah
    diterapkan), sedangkan uangnya tidak: `nilai_beli`/`nilai_jual` adalah rupiah yang benar-benar
    dibayar/diterima, dan split tidak mengubahnya. Karena itu `lembar_*` berjenis `Fraction` —
    reverse split yang tidak membagi rata (mis. 3:1 atas 100 lembar) menghasilkan pecahan, dan
    membulatkannya diam-diam berarti mengubah jumlah lembar yang dipakai menghitung risiko.
    `lembar_tercatat` menyimpan angka mentahnya supaya penyesuaiannya bisa diperiksa manusia.
    """

    lembar_beli: Fraction = Fraction(0)
    nilai_beli: int = 0
    biaya_beli: int = 0
    lembar_jual: Fraction = Fraction(0)
    nilai_jual: int = 0
    biaya_jual: int = 0
    pajak_jual: int = 0
    transaksi_tanpa_biaya: int = 0
    jumlah_transaksi: int = 0
    #: Lembar apa adanya dari transaksi, sebelum penyesuaian split (untuk ditampilkan).
    lembar_beli_tercatat: int = 0
    lembar_jual_tercatat: int = 0
    #: Split/reverse split yang benar-benar mengubah salah satu transaksi di atas.
    aksi: tuple[AksiKorporasi, ...] = ()

    @property
    def lembar_terbuka(self) -> Fraction:
        return self.lembar_beli - self.lembar_jual

    @property
    def lembar_terbuka_tercatat(self) -> int:
        return self.lembar_beli_tercatat - self.lembar_jual_tercatat

    @property
    def lembar_terbuka_bulat(self) -> int | None:
        """Lembar terbuka bila bulat; `None` bila split menghasilkan pecahan.

        `None` bukan nol dan bukan hasil pembulatan: ia berarti jumlah lembarnya tidak bisa
        dinyatakan sebagai bilangan bulat, dan itu harus terlihat (mis. reverse split 3:1 atas
        100 lembar → 33⅓).
        """
        lembar = self.lembar_terbuka
        return int(lembar) if lembar.denominator == 1 else None

    @property
    def disesuaikan(self) -> bool:
        """True bila ada split yang mengubah lembar posisi ini."""
        return bool(self.aksi)

    @property
    def harga_rata(self) -> Fraction | None:
        if self.lembar_beli == 0:
            return None
        return Fraction(self.nilai_beli) / self.lembar_beli

    @property
    def biaya_lengkap(self) -> bool:
        """False bila ada transaksi yang biayanya belum dicatat — hasilnya belum lengkap."""
        return self.transaksi_tanpa_biaya == 0

    def biaya_beli_sisa(self) -> Fraction:
        """Bagian biaya beli yang masih menempel pada lembar yang belum dijual."""
        if self.lembar_beli == 0:
            return Fraction(0)
        return Fraction(self.biaya_beli) * self.lembar_terbuka / self.lembar_beli


def hitungan(
    sambungan: sqlite3.Connection,
    id_posisi: int,
    *,
    aksi: Sequence[AksiKorporasi] | None = None,
    sampai: date | str | None = None,
) -> HitunganPosisi:
    """Turunkan lembar, harga rata-rata, dan biaya dari transaksi posisi ini (revisi terkini).

    `aksi=None` berarti "carikan sendiri aksi korporasi kode ini"; `aksi=()` berarti "tidak ada
    aksi korporasi yang perlu diperhitungkan" — pembeda itu dipakai `ringkasan_semua` supaya satu
    pembacaan aksi melayani seluruh posisi, bukan satu kueri per posisi.

    `sampai` membatasi transaksi yang ikut dihitung pada tanggal itu ke belakang. Dipakai
    `jurnal.py` untuk menilai keadaan posisi **saat** sebuah keputusan diambil (pelanggaran V4,
    PRD 9.8), dan tidak mengubah apa pun bagi pemanggil yang tidak menyebutnya.
    """
    kueri = (
        "SELECT aksi, tanggal, harga, lembar, biaya, pajak FROM v_transaksi_terkini"
        " WHERE id_posisi = ?"
    )
    nilai: list[object] = [id_posisi]
    if sampai is not None:
        batas = sampai.isoformat() if isinstance(sampai, date) else str(sampai)
        kueri += " AND tanggal <= ?"
        nilai.append(batas)
    kueri += " ORDER BY tanggal, id_transaksi"
    baris_transaksi = list(sambungan.execute(kueri, nilai))
    if aksi is None:
        baris_kode = sambungan.execute(
            "SELECT kode FROM v_posisi_terkini WHERE id_posisi = ?", (id_posisi,)
        ).fetchone()
        kode = baris_kode["kode"] if baris_kode else None
        aksi = aksi_korporasi(sambungan, [kode]).get(kode, ()) if kode else ()

    lembar_beli = Fraction(0)
    lembar_jual = Fraction(0)
    lembar_beli_tercatat = lembar_jual_tercatat = 0
    nilai_beli = nilai_jual = biaya_beli = biaya_jual = pajak_jual = 0
    tanpa_biaya = jumlah = 0
    diterapkan: dict[tuple[str, str], AksiKorporasi] = {}
    for baris in baris_transaksi:
        jumlah += 1
        if baris["biaya"] is None:
            tanpa_biaya += 1
        biaya = int(baris["biaya"] or 0)
        pajak = int(baris["pajak"] or 0)
        tanggal = date.fromisoformat(baris["tanggal"])
        faktor = penyesuaian.faktor_lembar(aksi, sesudah=tanggal)
        if faktor != 1:
            for satu in aksi:
                if satu.tanggal > tanggal and satu.jenis in ("split", "reverse_split"):
                    diterapkan[(satu.tanggal.isoformat(), satu.jenis)] = satu
        lembar = Fraction(int(baris["lembar"])) * faktor
        if baris["aksi"] == "beli":
            lembar_beli += lembar
            lembar_beli_tercatat += int(baris["lembar"])
            # Uangnya **tidak** ikut diskalakan: split tidak mengubah rupiah yang dibayar.
            nilai_beli += int(baris["harga"]) * int(baris["lembar"])
            biaya_beli += biaya
        else:
            lembar_jual += lembar
            lembar_jual_tercatat += int(baris["lembar"])
            nilai_jual += int(baris["harga"]) * int(baris["lembar"])
            biaya_jual += biaya
            pajak_jual += pajak
    return HitunganPosisi(
        lembar_beli=lembar_beli,
        nilai_beli=nilai_beli,
        biaya_beli=biaya_beli,
        lembar_jual=lembar_jual,
        nilai_jual=nilai_jual,
        biaya_jual=biaya_jual,
        pajak_jual=pajak_jual,
        transaksi_tanpa_biaya=tanpa_biaya,
        jumlah_transaksi=jumlah,
        lembar_beli_tercatat=lembar_beli_tercatat,
        lembar_jual_tercatat=lembar_jual_tercatat,
        aksi=tuple(sorted(diterapkan.values(), key=lambda satu: satu.tanggal)),
    )


def _bulat(nilai: Fraction) -> int:
    """Bulatkan ke rupiah terdekat (setengah ke atas), tanpa bergantung pembulatan biner."""
    return int((nilai + Fraction(1, 2)).__floor__())


def bulat_rupiah(nilai: Fraction) -> int:
    """Rupiah dari nilai berpecahan — dipakai modul lain (mis. dasbor) supaya pembulatannya satu."""
    return _bulat(nilai)


def _ceil(nilai: Fraction) -> int:
    """Bulatkan ke atas: biaya tidak pernah dibulatkan ke bawah (PRD 10, risiko = batas bawah)."""
    return -((-nilai.numerator) // nilai.denominator)


# ---------------------------------------------------------------------------------------
# Harga terakhir (satu label sumber, T32)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HargaTerkini:
    kode: str
    tanggal: date
    close: int
    sumber: str


def harga_terakhir(
    sambungan: sqlite3.Connection,
    kode: Iterable[str],
    *,
    sumber: str | potret.PilihanHarga | None = None,
) -> dict[str, HargaTerkini]:
    """Penutupan terakhir tiap kode dari deret yang dipakai berhitung (T32, K97).

    Deretnya sama dengan yang dipakai berhitung (`potret.harga_dipakai`): label dengan riwayat bar
    terbanyak, atau sambungan harga resmi sejak tanggal sambung. Harga pembanding (PRD 7.3) tidak
    pernah masuk ke sini — kalau ia ikut, "harga terakhir" bisa datang dari sumber yang berbeda
    untuk tiap kode tanpa satu pun tanda.
    """
    daftar = tuple({satu.strip().upper() for satu in kode if satu and satu.strip()})
    if not daftar:
        return {}
    label = potret.sebagai_pilihan(sumber) or potret.harga_dipakai(sambungan)
    if label is None:
        return {}
    penggalan, argumen = label.syarat()
    tanda = ", ".join("?" for _ in daftar)
    terakhir = {
        baris["kode"]: baris["tanggal"]
        for baris in sambungan.execute(
            f"SELECT kode, MAX(tanggal) AS tanggal FROM v_harga_harian_terkini"
            f" WHERE {penggalan} AND kode IN ({tanda}) GROUP BY kode",
            (*argumen, *daftar),
        )
    }
    if not terakhir:
        return {}
    pasangan = [("kode = ? AND tanggal = ?", (kode, tanggal)) for kode, tanggal in terakhir.items()]
    syarat = " OR ".join(f"({satu[0]})" for satu in pasangan)
    nilai: tuple[object, ...] = argumen
    for _, isi in pasangan:
        nilai += isi
    hasil: dict[str, HargaTerkini] = {}
    for baris in sambungan.execute(
        "SELECT kode, tanggal, close, sumber FROM v_harga_harian_terkini"
        f" WHERE {penggalan} AND ({syarat})",
        nilai,
    ):
        hasil[baris["kode"]] = HargaTerkini(
            kode=baris["kode"],
            tanggal=date.fromisoformat(baris["tanggal"]),
            close=int(baris["close"]),
            sumber=baris["sumber"],
        )
    return hasil


# ---------------------------------------------------------------------------------------
# Aksi korporasi pada posisi (PRD 9.11)
# ---------------------------------------------------------------------------------------


def _sebut_aksi(aksi: AksiKorporasi) -> str:
    """`split 1:25 pada 2026-07-21` — sebutan aksi yang menyebut rasionya, bukan hanya jenisnya."""
    if aksi.rasio_lama and aksi.rasio_baru:
        return f"{aksi.jenis} {aksi.rasio_lama}:{aksi.rasio_baru} pada {aksi.tanggal.isoformat()}"
    return f"{aksi.jenis} pada {aksi.tanggal.isoformat()}"


@dataclass(frozen=True)
class StopBasis:
    """Level stop dalam **basis harga sekarang**, beserta asal angka dan basisnya.

    `tercatat` adalah angka yang tersimpan di baris posisi; `nilai` adalah angka yang sama setelah
    dipindahkan ke basis sekarang oleh split yang terjadi setelah `basis`. `nilai=None` padahal
    `tercatat` ada berarti **tidak dapat dinilai** — dan itu bukan nol (aturan keras 2).
    """

    tercatat: int | None
    nilai: Fraction | None
    basis: date | None
    asal_basis: str | None
    aksi: tuple[AksiKorporasi, ...] = ()
    alasan: str | None = None

    @property
    def disesuaikan(self) -> bool:
        return bool(self.aksi)

    @property
    def bulat(self) -> int | None:
        """Level stop bila berupa rupiah bulat; `None` bila hasil penyesuaiannya berpecahan."""
        if self.nilai is None:
            return None
        return int(self.nilai) if self.nilai.denominator == 1 else None

    def ringkas(self) -> str:
        if self.tercatat is None:
            return "tanpa stop (pelanggaran V1)"
        if self.nilai is None:
            return f"{tampilan.rupiah(self.tercatat)} TIDAK DINILAI — {self.alasan}"
        teks = tampilan.rupiah(float(self.nilai))
        if self.disesuaikan:
            teks += (
                f" (disesuaikan dari {tampilan.rupiah(self.tercatat)} yang dinyatakan pada basis "
                f"{self.basis.isoformat()} oleh "
                + ", ".join(_sebut_aksi(satu) for satu in self.aksi)
                + ")"
            )
        return teks


def stop_dalam_basis(posisi: Posisi, aksi: Sequence[AksiKorporasi]) -> StopBasis:
    """Pindahkan level stop ke basis harga sekarang (PRD 9.11: stop menyesuaikan split).

    Basisnya adalah `posisi.tgl_stop` bila dinyatakan. Baris lama yang belum menyatakannya
    memakai waktu pencatatannya sebagai basis **hanya bila tidak ada split setelahnya**; begitu
    ada split, angkanya tidak dipindahkan dan risikonya berstatus tidak dinilai — sebab angka itu
    bisa berarti "sebelum split" atau "sesudah split", dan memilih salah satunya diam-diam berarti
    memilih angka risiko yang salah tanpa satu pun tanda.
    """
    if posisi.stop_terkini is None:
        return StopBasis(tercatat=None, nilai=None, basis=None, asal_basis=None)
    tercatat = int(posisi.stop_terkini)
    if posisi.tgl_stop:
        basis = date.fromisoformat(posisi.tgl_stop)
        asal = ASAL_BASIS_STOP_DINYATAKAN
    else:
        basis = date.fromisoformat(posisi.diketahui_pada[:10])
        asal = ASAL_BASIS_STOP_DARI_PENCATATAN
    terpakai = tuple(
        sorted(
            (
                satu
                for satu in aksi
                if satu.jenis in ("split", "reverse_split") and satu.tanggal > basis
            ),
            key=lambda satu: satu.tanggal,
        )
    )
    if terpakai and asal == ASAL_BASIS_STOP_DARI_PENCATATAN:
        return StopBasis(
            tercatat=tercatat,
            nilai=None,
            basis=basis,
            asal_basis=asal,
            aksi=terpakai,
            alasan=(
                "baris stop ini belum menyatakan basis tanggalnya (kolom `tgl_stop` kosong, "
                "dipakai waktu pencatatan "
                f"{basis.isoformat()}), sedangkan ada {len(terpakai)} split sesudahnya ("
                + ", ".join(_sebut_aksi(satu) for satu in terpakai)
                + "). Angka itu bisa berarti basis sebelum split atau sesudahnya, dan menebaknya "
                "menghasilkan risiko yang salah tanpa terlihat. Tetapkan ulang lewat --ubah-stop "
                "(basisnya ikut tercatat mulai migrasi 013)"
            ),
        )
    return StopBasis(
        tercatat=tercatat,
        nilai=Fraction(tercatat) / penyesuaian.faktor_lembar(aksi, sesudah=basis),
        basis=basis,
        asal_basis=asal,
        aksi=terpakai,
    )


def _lembar_pada(
    sambungan: sqlite3.Connection,
    id_posisi: int,
    tanggal: date,
    aksi: Sequence[AksiKorporasi],
) -> Fraction:
    """Lembar yang dipegang **sebelum** `tanggal`, dalam basis harga sekarang.

    Dipakai dividen, dan karena itu batasnya **tegas**: transaksi pada tanggal ex-date tidak
    berhak atas dividen itu (pada hari itu sahamnya sudah diperdagangkan tanpa hak), sedangkan
    penjualan pada hari itu masih berhak (sahamnya dipegang sebelum ex-date). Aturan ini
    dinyatakan di keluaran, bukan disimpulkan pengguna dari angkanya.
    """
    total = Fraction(0)
    for baris in sambungan.execute(
        "SELECT aksi, tanggal, lembar FROM v_transaksi_terkini"
        " WHERE id_posisi = ? AND tanggal < ? ORDER BY tanggal, id_transaksi",
        (id_posisi, tanggal.isoformat()),
    ):
        faktor = penyesuaian.faktor_lembar(aksi, sesudah=date.fromisoformat(baris["tanggal"]))
        lembar = Fraction(int(baris["lembar"])) * faktor
        total += lembar if baris["aksi"] == "beli" else -lembar
    return total


@dataclass(frozen=True)
class PeristiwaDividen:
    """Satu pembayaran dividen yang jatuh pada masa pegang posisi ini."""

    tanggal: date
    dividen_per_saham: int
    lembar: Fraction
    jumlah: int
    sumber: str | None = None

    def ringkas(self) -> str:
        return (
            f"{self.tanggal.isoformat()} · {tampilan.rupiah(self.dividen_per_saham)}/lembar × "
            f"{tampilan.angka(float(self.lembar), 0)} lbr = {tampilan.rupiah(self.jumlah)}"
        )


@dataclass(frozen=True)
class DividenDiterima:
    """Dividen tunai yang **dihitung** dari aksi korporasi × lembar yang dipegang saat ex-date."""

    total: int = 0
    peristiwa: tuple[PeristiwaDividen, ...] = ()
    catatan: str | None = None
    sumber: tuple[str, ...] = ()

    @property
    def ada(self) -> bool:
        return bool(self.peristiwa)

    def ringkas(self) -> str:
        if not self.ada:
            return f"tidak ada ({self.catatan})" if self.catatan else "tidak ada"
        teks = tampilan.rupiah(self.total) + f" dari {len(self.peristiwa)} pembayaran"
        if self.catatan:
            teks += f" — {self.catatan}"
        return teks


def dividen_diterima(
    sambungan: sqlite3.Connection,
    posisi: Posisi,
    aksi: Sequence[AksiKorporasi],
) -> DividenDiterima:
    """Dividen tunai posisi ini, dihitung dari `aksi_korporasi` × lembar pada saat ex-date.

    Dua hal yang **tidak** dilakukan di sini, dan keduanya disengaja:

    * **Pajak tidak dihitung.** Perlakuan PPh dividen bergantung status wajib pajak dan apakah
      dividennya diinvestasikan kembali — bukan parameter bursa yang boleh ditetapkan aplikasi.
      Angkanya bruto, dan itu dikatakan.
    * **Tidak ada angka bila sumbernya tidak menyatakannya.** Kode yang tidak punya baris dividen
      sama sekali bukan berarti "tidak pernah membagi dividen"; ia berarti sumbernya belum
      menyatakannya, dan itu yang tertulis.
    """
    dividen = [satu for satu in aksi if satu.jenis == "dividen" and satu.dividen_per_saham]
    if not dividen:
        return DividenDiterima(
            catatan=f"sumber data tidak menyatakan satu pun dividen untuk {posisi.kode}"
        )
    buka = date.fromisoformat(posisi.tgl_buka)
    peristiwa: list[PeristiwaDividen] = []
    for satu in sorted(dividen, key=lambda item: item.tanggal):
        if satu.tanggal < buka:
            continue
        lembar = _lembar_pada(sambungan, posisi.id_posisi, satu.tanggal, aksi)
        if lembar <= 0:
            continue
        peristiwa.append(
            PeristiwaDividen(
                tanggal=satu.tanggal,
                dividen_per_saham=int(satu.dividen_per_saham or 0),
                lembar=lembar,
                jumlah=_bulat(Fraction(int(satu.dividen_per_saham or 0)) * lembar),
                sumber=satu.sumber,
            )
        )
    label = tuple(sorted({satu.sumber for satu in peristiwa if satu.sumber}))
    catatan = (
        "bruto, sebelum pajak: perlakuan PPh dividen bergantung status wajib pajak dan apakah "
        "dividennya diinvestasikan kembali — bukan parameter bursa, jadi tidak dihitung aplikasi"
    )
    if not peristiwa:
        catatan = (
            "tidak ada tanggal ex-date dividen selama posisi ini dipegang "
            f"(sejak {posisi.tgl_buka}); sumbernya menyatakan {len(dividen)} peristiwa dividen "
            f"untuk {posisi.kode} di luar masa itu"
        )
    return DividenDiterima(
        total=sum(satu.jumlah for satu in peristiwa),
        peristiwa=tuple(peristiwa),
        catatan=catatan,
        sumber=label,
    )


@dataclass(frozen=True)
class KeputusanRightIssue:
    """Keputusan manual atas satu right issue pada satu posisi (PRD 9.11)."""

    id_keputusan: int
    revisi: int
    id_posisi: int
    kode: str
    tanggal_aksi: str
    keputusan: str
    id_transaksi: int | None
    lembar: int | None
    harga: int | None
    biaya: int | None
    catatan: str | None
    sumber: str
    diketahui_pada: str

    @property
    def hasil_penjualan(self) -> int | None:
        """Uang yang diterima dari menjual hak (setelah biaya, bila biayanya dicatat)."""
        if self.keputusan != "jual_hmetd" or self.lembar is None or self.harga is None:
            return None
        return self.lembar * self.harga - int(self.biaya or 0)

    def ringkas(self) -> str:
        bagian = [
            f"keputusan #{self.id_keputusan} r{self.revisi}",
            self.kode,
            f"right issue {self.tanggal_aksi}",
            self.keputusan,
        ]
        if self.keputusan == "tebus":
            bagian.append(f"lewat transaksi #{self.id_transaksi}")
        elif self.keputusan == "jual_hmetd":
            bagian.append(
                f"{tampilan.angka(self.lembar or 0, 0)} hak @ {tampilan.rupiah(self.harga)}"
            )
            if self.biaya is None:
                bagian.append("biaya belum dicatat")
            bagian.append(f"hasil {tampilan.rupiah(self.hasil_penjualan)}")
        if self.catatan:
            # Catatan tersimpan bisa beberapa baris; di sini ia dirangkai satu baris supaya
            # keputusannya tetap terbaca sebagai satu kalimat di daftar.
            bagian.append(" ".join(self.catatan.split()))
        return " · ".join(bagian)


@dataclass(frozen=True)
class HakRightIssue:
    """Satu right issue yang menyentuh sebuah posisi, beserta hak dan keputusannya."""

    kode: str
    id_posisi: int
    tanggal_aksi: date
    rasio_lama: int | None
    rasio_baru: int | None
    harga_tebus: int | None
    tenggat: date | None
    lembar_hak: Fraction | None
    alasan_hak: str | None
    keputusan: KeputusanRightIssue | None
    sumber: str | None
    #: Satuan lot yang berlaku pada tanggal aksi (B1), atau `None` bila parameternya belum ada.
    #: Dipakai hanya untuk **mengingatkan** bahwa haknya tidak selalu bisa dicatat seluruhnya.
    lot: int | None = None

    @property
    def sudah_diputuskan(self) -> bool:
        return self.keputusan is not None

    @property
    def lembar_hak_patut_lot(self) -> int | None:
        """Bagian hak yang bulat lot; `None` bila haknya sudah bulat atau lotnya tidak diketahui."""
        if self.lembar_hak is None or not self.lot:
            return None
        return int(self.lembar_hak // self.lot * self.lot)

    def catatan_lot(self) -> str | None:
        """Catatan bila haknya **bukan kelipatan lot** (PRD 10, P26).

        Sejak P26 diputuskan (10 Okt 2026), penebusan HMETD tetap tunduk pada aturan lot: hak
        6.250 lembar hanya bisa dicatat 6.200. Yang berubah hanyalah **kapan** pengguna tahu —
        sekarang di sini, bukan baru saat `--catat-transaksi` menolaknya.
        """
        if self.lembar_hak is None or not self.lot or self.lembar_hak % self.lot == 0:
            return None
        return (
            f"hak {tampilan.angka(float(self.lembar_hak), 0)} lembar BUKAN kelipatan lot {self.lot} "
            f"(PRD 10): penebusan hanya bisa dicatat {tampilan.angka(self.lembar_hak_patut_lot or 0, 0)} "
            "lembar, sisanya hanya bisa dijual sebagai HMETD (jual_hmetd)"
        )

    @property
    def biaya_tebus(self) -> int | None:
        """Rupiah yang dibutuhkan untuk menebus seluruh hak; `None` bila haknya tidak dinilai."""
        if self.lembar_hak is None or self.harga_tebus is None:
            return None
        return _bulat(self.lembar_hak * self.harga_tebus)

    def tenggat_lewat(self, hari_ini: date) -> bool:
        return self.tenggat is not None and self.tenggat < hari_ini

    def sisa_hari(self, hari_ini: date) -> int | None:
        return None if self.tenggat is None else (self.tenggat - hari_ini).days

    def ringkas(self, *, dengan_keputusan: bool = True) -> str:
        bagian = [
            f"posisi #{self.id_posisi} {self.kode}",
            f"right issue {self.tanggal_aksi.isoformat()}",
        ]
        if self.rasio_lama and self.rasio_baru:
            bagian.append(f"rasio {self.rasio_lama}:{self.rasio_baru}")
        if self.harga_tebus is not None:
            bagian.append(f"tebus {tampilan.rupiah(self.harga_tebus)}/lembar")
        if self.tenggat is None:
            bagian.append("tenggat BELUM DINYATAKAN sumbernya")
        else:
            bagian.append(f"tenggat {self.tenggat.isoformat()}")
        if self.lembar_hak is None:
            bagian.append(f"hak tidak dapat dihitung: {self.alasan_hak}")
        else:
            bagian.append(
                f"hak {tampilan.angka(float(self.lembar_hak), 0)} lembar"
                + (
                    f" = {tampilan.rupiah(self.biaya_tebus)} untuk ditebus"
                    if self.biaya_tebus is not None
                    else ""
                )
            )
        if dengan_keputusan:
            bagian.append(
                "sudah diputuskan: " + self.keputusan.ringkas()
                if self.keputusan
                else "BELUM DIPUTUSKAN"
            )
        teks = " · ".join(bagian)
        catatan_lot = self.catatan_lot()
        if catatan_lot:
            # Satu baris: `ringkas()` juga dipakai di dalam ringkasan keputusan, dan catatan yang
            # mengandung baris baru akan memecah keluarannya di tengah kalimat.
            teks += f" · {catatan_lot}"
        return teks


def keputusan_terkini(
    sambungan: sqlite3.Connection, id_posisi: int, tanggal_aksi: date
) -> KeputusanRightIssue | None:
    baris = sambungan.execute(
        "SELECT * FROM v_keputusan_right_issue_terkini WHERE id_posisi = ? AND tanggal_aksi = ?",
        (id_posisi, tanggal_aksi.isoformat()),
    ).fetchone()
    return None if baris is None else _ke_keputusan(baris)


def hak_right_issue(
    sambungan: sqlite3.Connection,
    *,
    ringkasan_posisi: Sequence["RingkasanPosisi"] | None = None,
    kode: str | None = None,
    hari_ini: date | None = None,
    batas: int | None = None,
) -> tuple[HakRightIssue, ...]:
    """Right issue yang menyentuh posisi: haknya (petunjuk) dan keputusannya.

    `batas` membatasi berapa baris terbaru yang dikembalikan; yang dipotong **dihitung** dan
    disebut pemanggil, bukan dihilangkan diam-diam.
    """
    momen = hari_ini or date.today()
    daftar_posisi = list(ringkasan_posisi) if ringkasan_posisi is not None else list(
        ringkasan_semua(sambungan, status=None, kode=kode)
    )
    if kode is not None:
        daftar_posisi = [satu for satu in daftar_posisi if satu.posisi.kode == kode.strip().upper()]
    peta = aksi_korporasi(sambungan, [satu.posisi.kode for satu in daftar_posisi])
    hasil: list[HakRightIssue] = []
    for satu in daftar_posisi:
        p = satu.posisi
        buka = date.fromisoformat(p.tgl_buka)
        tutup = date.fromisoformat(p.tgl_tutup) if p.tgl_tutup else None
        aksi = peta.get(p.kode, ())
        for tindakan in aksi:
            if tindakan.jenis != "right_issue" or tindakan.tanggal > momen:
                continue
            if tindakan.tanggal < buka or (tutup is not None and tindakan.tanggal > tutup):
                continue
            lembar_hak: Fraction | None = None
            alasan: str | None = None
            if not tindakan.rasio_lama or not tindakan.rasio_baru:
                alasan = "aksinya tidak menyatakan rasio (rasio_lama/rasio_baru)"
            else:
                dipegang = _lembar_pada(sambungan, p.id_posisi, tindakan.tanggal, aksi)
                if dipegang <= 0:
                    alasan = f"posisinya tidak memegang lembar pada {tindakan.tanggal.isoformat()}"
                else:
                    lembar_hak = dipegang * Fraction(tindakan.rasio_baru, tindakan.rasio_lama)
            hasil.append(
                HakRightIssue(
                    kode=p.kode,
                    id_posisi=p.id_posisi,
                    tanggal_aksi=tindakan.tanggal,
                    rasio_lama=tindakan.rasio_lama,
                    rasio_baru=tindakan.rasio_baru,
                    harga_tebus=tindakan.harga_tebus,
                    tenggat=date.fromisoformat(tindakan.tenggat) if tindakan.tenggat else None,
                    lembar_hak=lembar_hak,
                    alasan_hak=alasan,
                    keputusan=keputusan_terkini(sambungan, p.id_posisi, tindakan.tanggal),
                    sumber=tindakan.sumber,
                    lot=_lot_atau_tidak(sambungan, tindakan.tanggal)[0],
                )
            )
    hasil.sort(key=lambda satu: (satu.tanggal_aksi, satu.id_posisi), reverse=True)
    return tuple(hasil[:batas]) if batas is not None else tuple(hasil)


@dataclass(frozen=True)
class PendaftaranKeputusan:
    """Hasil `catat_keputusan_right_issue`: keputusannya, haknya, dan apa yang perlu diketahui."""

    keputusan: KeputusanRightIssue
    hak: HakRightIssue | None
    catatan: tuple[str, ...]

    def ringkas(self) -> str:
        baris = [self.keputusan.ringkas()]
        if self.hak is not None:
            baris.append(f"      hak: {self.hak.ringkas(dengan_keputusan=False)}")
        for satu in self.catatan:
            baris.append(f"      catatan: {satu}")
        return "\n".join(baris)


def _tolak_isian_yang_tidak_dipakai(
    keputusan: str, lembar: int | None, harga: int | None, biaya: int | None
) -> None:
    """Tolak lembar/harga/biaya untuk **semua** keputusan selain `jual_hmetd` (K71).

    Sebelum ini pemeriksaannya hanya ada di cabang `abaikan`, sehingga `tebus` membuang isian
    yang sama diam-diam di jalur baris perintah — keluar 0 tanpa pesan. Satu aturan di sini
    membuat kedua cabang (dan jendela, yang memeriksa lebih dulu dengan pesan yang sama) tidak
    bisa bercabang. Untuk `tebus`, alasannya berbeda: yang menaikkan lembar posisi adalah
    transaksinya (T51), bukan keputusan itu.
    """
    if keputusan == "jual_hmetd":
        return
    dipakai = [
        nama
        for nama, nilai in (("--lembar", lembar), ("--harga", harga), ("--biaya", biaya))
        if nilai is not None
    ]
    if not dipakai:
        return
    if keputusan == "tebus":
        raise GalatPosisi(
            f"keputusan `tebus` tidak memakai {', '.join(dipakai)}: yang menaikkan lembar posisi "
            "adalah transaksinya (T51), bukan keputusan ini. Kosongkan isian itu, atau pilih "
            "keputusan `jual_hmetd`"
        )
    raise GalatPosisi(
        f"keputusan `{keputusan}` tidak memakai {', '.join(dipakai)}; lembar/harga/biaya hanya "
        "berlaku untuk `jual_hmetd`. Menerimanya lalu membuangnya diam-diam akan membuat "
        "keluarannya tampak mencatat penjualan hak yang tidak pernah terjadi"
    )


def catat_keputusan_right_issue(
    sambungan: sqlite3.Connection,
    kode: str,
    tanggal_aksi: date | str,
    keputusan: str,
    *,
    id_posisi: int | None = None,
    id_transaksi: int | None = None,
    lembar: int | None = None,
    harga: int | None = None,
    biaya: int | None = None,
    catatan: str | None = None,
    sumber: str = SUMBER_KEPUTUSAN_RIGHT_ISSUE,
    dicatat_pada: str | None = None,
) -> PendaftaranKeputusan:
    """Catat keputusan manual atas right issue (PRD 9.11) — tebus, jual HMETD, atau abaikan.

    Yang paling penting di sini adalah apa yang **tidak** boleh terjadi: `tebus` tanpa transaksi.
    Menebus berarti membeli lembar baru, dan lembarnya hanya punya satu tempat — `transaksi`.
    Menerima keputusan `tebus` tanpa transaksinya akan membuat posisinya tampak sudah ditebus
    padahal lembarnya tidak pernah masuk ke buku mana pun.

    Dua aturan bentuk dijaga di sini: isian `lembar`/`harga`/`biaya` hanya berlaku untuk
    `jual_hmetd` dan **ditolak berisik** untuk keputusan lain, termasuk `tebus` (K71); dan
    catatan turunan yang kalimatnya sudah ada di revisi sebelumnya tidak disalin lagi (K72).
    """
    if keputusan not in KEPUTUSAN_RIGHT_ISSUE_SAH:
        raise GalatPosisi(
            f"keputusan {keputusan!r} tidak dikenal; yang sah: {', '.join(KEPUTUSAN_RIGHT_ISSUE_SAH)} "
            "(PRD 9.11)"
        )
    kode = kode.strip().upper()
    _periksa_kode_dikenal(sambungan, kode)
    hari = _hari(tanggal_aksi)
    catatan_kaki: list[str] = []

    posisi_lama = None
    if id_posisi is not None:
        posisi_lama = wajib_ada(sambungan, id_posisi)
    else:
        calon = daftar(sambungan, status=None, kode=kode)
        if len(calon) > 1:
            raise GalatPosisi(
                f"ada {len(calon)} posisi {kode} ({', '.join('#' + str(satu.id_posisi) for satu in calon)}); "
                "sebutkan yang mana lewat --id-posisi"
            )
        posisi_lama = calon[0] if calon else None
    if posisi_lama is None:
        raise GalatPosisi(
            f"tidak ada posisi {kode} yang bisa diputuskan. Right issue menyentuh posisi yang "
            "benar-benar dipegang — kalau posisinya belum tercatat, catat transaksinya lebih dulu"
        )
    if posisi_lama.kode != kode:
        raise GalatPosisi(f"posisi #{posisi_lama.id_posisi} adalah {posisi_lama.kode}, bukan {kode}")

    aksi = aksi_korporasi(sambungan, [kode]).get(kode, ())
    tindakan = next(
        (satu for satu in aksi if satu.jenis == "right_issue" and satu.tanggal == hari), None
    )
    if tindakan is None:
        raise GalatPosisi(
            f"tidak ada right issue {kode} bertanggal {hari.isoformat()} di basis data. Yang ada: "
            + (
                ", ".join(
                    satu.tanggal.isoformat() for satu in aksi if satu.jenis == "right_issue"
                )
                or "(tidak ada satu pun)"
            )
            + ". Impor aksi korporasinya lebih dulu (--impor dengan aksi-korporasi.csv), supaya "
            "keputusannya menempel pada peristiwa yang benar-benar tercatat"
        )

    if keputusan == "tebus":
        if id_transaksi is None:
            raise GalatPosisi(
                "keputusan `tebus` menuntut --id-transaksi: menebus HMETD berarti membeli lembar "
                "baru, dan lembarnya hanya punya satu tempat — `transaksi`. Tanpa itu, posisinya "
                "akan tampak sudah ditebus padahal lembarnya tidak masuk ke buku mana pun. Catat "
                "dulu: --catat-transaksi "
                f"{kode} --aksi beli --lembar N --harga {tindakan.harga_tebus} --mode ..."
            )
        baris = sambungan.execute(
            "SELECT * FROM v_transaksi_terkini WHERE id_transaksi = ?", (id_transaksi,)
        ).fetchone()
        if baris is None:
            raise GalatPosisi(f"transaksi #{id_transaksi} tidak ada di basis data")
        if int(baris["id_posisi"]) != posisi_lama.id_posisi:
            raise GalatPosisi(
                f"transaksi #{id_transaksi} milik posisi #{baris['id_posisi']}, bukan posisi "
                f"#{posisi_lama.id_posisi}"
            )
        if baris["aksi"] != "beli":
            raise GalatPosisi(
                f"transaksi #{id_transaksi} adalah `{baris['aksi']}`; penebusan HMETD adalah pembelian"
            )
        if int(baris["harga"]) != int(tindakan.harga_tebus or 0):
            catatan_kaki.append(
                f"harga transaksi #{id_transaksi} ({tampilan.rupiah(baris['harga'])}) berbeda dari "
                f"harga tebus aksi ({tampilan.rupiah(tindakan.harga_tebus)}) — dicatat apa adanya, "
                "bukan diseragamkan"
            )
        _tolak_isian_yang_tidak_dipakai(keputusan, lembar, harga, biaya)
    else:
        if id_transaksi is not None:
            raise GalatPosisi(
                f"keputusan `{keputusan}` tidak memakai --id-transaksi; hanya `tebus` yang menunjuk "
                "pembelian lembar"
            )
        _tolak_isian_yang_tidak_dipakai(keputusan, lembar, harga, biaya)
        if lembar is not None and lembar <= 0:
            raise GalatPosisi(f"lembar hak harus lebih dari nol, bukan {lembar}")
        if harga is not None and harga <= 0:
            raise GalatPosisi(f"harga jual hak harus lebih dari nol, bukan {harga}")

    if keputusan == "jual_hmetd":
        if lembar is None or harga is None:
            raise GalatPosisi(
                "keputusan `jual_hmetd` menuntut --lembar dan --harga: hasil penjualan hak tidak "
                "bisa diturunkan dari data mana pun"
            )
        if biaya is None:
            catatan_kaki.append(
                "biaya penjualan hak belum dicatat, jadi hasilnya bruto (belum dikurangi biaya "
                "sekuritas)"
            )
    if tindakan.tenggat is not None and date.fromisoformat(tindakan.tenggat) < hari:
        catatan_kaki.append(
            f"keputusan ini dicatat {hari.isoformat()}, setelah tenggat {tindakan.tenggat} yang "
            "dinyatakan sumbernya — dicatat apa adanya, tetapi tenggatnya sudah lewat"
        )
    if tindakan.tenggat is None and keputusan != "abaikan":
        catatan_kaki.append(
            "tenggat right issue ini belum dinyatakan sumbernya; yang tercatat hanya tanggal "
            "aksinya"
        )

    lama = keputusan_terkini(sambungan, posisi_lama.id_posisi, hari)
    # K72: catatan **turunan** (`catatan_kaki`) yang kalimatnya sudah ada di catatan revisi
    # sebelumnya tidak ditambahkan lagi — riwayatnya sudah tersimpan di baris revisinya sendiri
    # (append-only), jadi menyalinnya berulang hanya menggelembungkan `catatan`. Catatan yang
    # **dinyatakan pengguna** dan `pesan_revisi` tetap disambung apa adanya.
    kalimat_lama = set(lama.catatan.splitlines()) if lama is not None and lama.catatan else set()
    catatan_kaki_baru = [satu for satu in catatan_kaki if satu not in kalimat_lama]
    pesan_revisi: str | None = None
    if lama is not None and lama.keputusan != keputusan:
        # Disimpan di barisnya, tetapi **tidak** dikembalikan sebagai catatan: ia sudah tampil
        # lewat `keputusan.ringkas()`, dan menyebutnya dua kali membuat keluarannya terbaca
        # seolah ada dua perubahan.
        pesan_revisi = (
            f"keputusan sebelumnya `{lama.keputusan}` (revisi {lama.revisi}) tidak dihapus: "
            "perubahan menambah revisi, bukan menimpa"
        )
    teks_catatan = (
        "\n".join(
            [
                satu
                for satu in (
                    lama.catatan if lama else None,
                    catatan,
                    *catatan_kaki_baru,
                    pesan_revisi,
                )
                if satu
            ]
        )
        or None
    )

    with db.tulis(sambungan) as koneksi:
        id_keputusan = (
            lama.id_keputusan
            if lama is not None
            else int(
                koneksi.execute(
                    "SELECT COALESCE(MAX(id_keputusan), 0) + 1 FROM keputusan_right_issue"
                ).fetchone()[0]
            )
        )
        revisi = (lama.revisi + 1) if lama is not None else 1
        koneksi.execute(
            "INSERT INTO keputusan_right_issue (id_keputusan, revisi, id_posisi, kode, tanggal_aksi,"
            " keputusan, id_transaksi, lembar, harga, biaya, catatan, sumber, diketahui_pada)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id_keputusan,
                revisi,
                posisi_lama.id_posisi,
                kode,
                hari.isoformat(),
                keputusan,
                id_transaksi if keputusan == "tebus" else None,
                lembar if keputusan == "jual_hmetd" else None,
                harga if keputusan == "jual_hmetd" else None,
                biaya if keputusan == "jual_hmetd" else None,
                teks_catatan,
                sumber,
                dicatat_pada or db.waktu_iso(),
            ),
        )

    baris_baru = sambungan.execute(
        "SELECT * FROM v_keputusan_right_issue_terkini WHERE id_keputusan = ?", (id_keputusan,)
    ).fetchone()
    hak = next(
        (
            satu
            for satu in hak_right_issue(
                sambungan, kode=kode, hari_ini=hari, ringkasan_posisi=None
            )
            if satu.id_posisi == posisi_lama.id_posisi and satu.tanggal_aksi == hari
        ),
        None,
    )
    return PendaftaranKeputusan(
        keputusan=_ke_keputusan(baris_baru),
        hak=hak,
        catatan=tuple(catatan_kaki),
    )


# ---------------------------------------------------------------------------------------
# Ringkasan satu posisi (keadaan sekarang)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RingkasanPosisi:
    """Keadaan satu posisi: turunan transaksi + penilaian pada harga terakhir + risiko terbuka."""

    posisi: Posisi
    hitungan: HitunganPosisi
    harga: HargaTerkini | None
    risiko_terbuka: int | None
    alasan_risiko: str | None
    hasil_terealisasi: int | None
    hasil_belum_terealisasi: int | None
    alasan_hasil: str | None
    #: Level stop dalam basis harga sekarang (PRD 9.11: stop menyesuaikan split).
    stop: StopBasis = StopBasis(tercatat=None, nilai=None, basis=None, asal_basis=None)
    #: Dividen tunai yang dihitung dari aksi korporasi × lembar saat ex-date.
    dividen: DividenDiterima = DividenDiterima()

    @property
    def lembar_terbuka(self) -> Fraction:
        return self.hitungan.lembar_terbuka

    @property
    def nilai_pasar(self) -> int | None:
        """Nilai posisi pada penutupan terakhir; `None` bila harganya tidak ada."""
        if self.harga is None:
            return None
        return _bulat(Fraction(self.harga.close) * self.lembar_terbuka)

    def ringkas(self) -> str:
        p = self.posisi
        bagian = [
            f"#{p.id_posisi} r{p.revisi}",
            p.kode,
            p.status,
            p.mode,
            f"buka {p.tgl_buka}",
        ]
        if p.tgl_tutup:
            bagian.append(f"tutup {p.tgl_tutup}")
        lembar = self.lembar_terbuka
        if self.hitungan.disesuaikan:
            bagian.append(
                f"{tampilan.angka(float(lembar), 0)} lbr "
                f"(dari {tampilan.angka(self.hitungan.lembar_terbuka_tercatat, 0)} lbr tercatat, "
                "disesuaikan "
                + ", ".join(_sebut_aksi(satu) for satu in self.hitungan.aksi)
                + ")"
            )
        else:
            bagian.append(f"{tampilan.angka(float(lembar), 0)} lbr")
        rata = self.hitungan.harga_rata
        bagian.append(
            "rata-rata " + (tampilan.rupiah(float(rata)) if rata is not None else "(tidak ada)")
        )
        if self.harga is not None:
            bagian.append(
                f"terakhir {tampilan.rupiah(self.harga.close)} ({self.harga.tanggal.isoformat()})"
            )
        else:
            bagian.append("terakhir (tidak ada harga)")
        bagian.append("stop " + self.stop.ringkas())
        teks = " · ".join(bagian)
        if self.hitungan.lembar_terbuka_bulat is None:
            teks += (
                "\n      LEMBAR TIDAK BULAT: penyesuaian split menghasilkan "
                f"{lembar} lembar. Jumlah lembar yang dipegang sekuritas Anda yang menentukan; "
                "periksa di sana sebelum memakai angka risiko di bawah"
            )
        if self.risiko_terbuka is not None:
            teks += f"\n      risiko terbuka  : {tampilan.rupiah(self.risiko_terbuka)}"
        if self.hasil_belum_terealisasi is not None:
            teks += f"\n      belum terealisasi: {tampilan.rupiah(self.hasil_belum_terealisasi)}"
        if self.hasil_terealisasi is not None:
            teks += f"\n      terealisasi     : {tampilan.rupiah(self.hasil_terealisasi)}"
        if self.dividen.ada:
            teks += f"\n      dividen diterima: {self.dividen.ringkas()}"
            for satu in self.dividen.peristiwa:
                teks += f"\n        - {satu.ringkas()}"
        if self.alasan_risiko:
            teks += f"\n      RISIKO TIDAK DINILAI: {self.alasan_risiko}"
        if self.alasan_hasil:
            teks += f"\n      HASIL BELUM LENGKAP : {self.alasan_hasil}"
        if p.pelanggaran:
            teks += "\n      PELANGGARAN: " + "; ".join(
                sebut_pelanggaran(satu) for satu in p.kode_pelanggaran
            )
        return teks


def ringkasan(
    sambungan: sqlite3.Connection,
    posisi: Posisi,
    *,
    harga: HargaTerkini | None = None,
    harga_diketahui: bool = False,
    aksi: Sequence[AksiKorporasi] | None = None,
    dengan_dividen: bool = True,
) -> RingkasanPosisi:
    """Hitung keadaan satu posisi.

    `harga_diketahui=True` menyatakan bahwa `harga=None` berarti "sudah dicari dan tidak ada";
    tanpa penanda itu, fungsi ini akan mencarinya sendiri. Pembeda ini penting: "tidak ada harga"
    dan "belum dicari" terlihat sama bagi pemanggil, padahal yang pertama membuat risiko terbuka
    berstatus tidak dinilai dan yang kedua tidak. `aksi` mengikuti pembeda yang sama untuk aksi
    korporasi: `None` = carikan sendiri, `()` = tidak ada.
    """
    if not harga_diketahui and posisi.status == "aktif":
        harga = harga_terakhir(sambungan, [posisi.kode]).get(posisi.kode)
    if aksi is None:
        aksi = aksi_korporasi(sambungan, [posisi.kode]).get(posisi.kode, ())
    angka = hitungan(sambungan, posisi.id_posisi, aksi=aksi)
    lembar = angka.lembar_terbuka
    stop = stop_dalam_basis(posisi, aksi)
    dividen = (
        dividen_diterima(sambungan, posisi, aksi) if dengan_dividen else DividenDiterima()
    )

    risiko_terbuka: int | None = None
    alasan_risiko: str | None = None
    if posisi.status != "aktif" or lembar == 0:
        risiko_terbuka = 0
    elif posisi.stop_terkini is None:
        alasan_risiko = (
            "posisinya berjalan tanpa stop (pelanggaran V1, PRD 9.8), sehingga risiko terbukanya "
            "tidak bisa dihitung — bukan dianggap nol"
        )
    elif stop.nilai is None:
        alasan_risiko = f"level stop tidak dapat dinilai: {stop.alasan}"
    elif harga is None:
        alasan_risiko = (
            f"tidak ada penutupan terakhir untuk {posisi.kode} pada label sumber yang dipakai, "
            "sehingga risiko terbukanya tidak bisa dihitung"
        )
    else:
        # Stop dan penutupan sama-sama dalam basis sekarang, jadi selisihnya sebanding.
        risiko_terbuka = _bulat(max(Fraction(harga.close) - stop.nilai, 0) * lembar)

    hasil_terealisasi: int | None = None
    if angka.lembar_jual:
        rata = angka.harga_rata or Fraction(0)
        pokok = rata * angka.lembar_jual
        biaya_beli_teralokasi = (
            Fraction(angka.biaya_beli) * angka.lembar_jual / angka.lembar_beli
            if angka.lembar_beli
            else Fraction(0)
        )
        hasil_terealisasi = _bulat(
            Fraction(angka.nilai_jual) - pokok - angka.biaya_jual - biaya_beli_teralokasi
        )

    hasil_belum: int | None = None
    alasan_hasil: str | None = None
    if posisi.status == "aktif" and lembar:
        rata = angka.harga_rata
        if rata is None or harga is None:
            alasan_hasil = "harga rata-rata atau penutupan terakhir belum ada"
        else:
            hasil_belum = _bulat(
                (Fraction(harga.close) - rata) * lembar - angka.biaya_beli_sisa()
            )
    if not angka.biaya_lengkap:
        pesan = (
            f"{angka.transaksi_tanpa_biaya} dari {angka.jumlah_transaksi} transaksi posisi ini "
            "belum mencatat biayanya, jadi hasil di atas belum termasuk biaya itu"
        )
        alasan_hasil = f"{alasan_hasil}; {pesan}" if alasan_hasil else pesan

    return RingkasanPosisi(
        posisi=posisi,
        hitungan=angka,
        harga=harga,
        risiko_terbuka=risiko_terbuka,
        alasan_risiko=alasan_risiko,
        hasil_terealisasi=hasil_terealisasi,
        hasil_belum_terealisasi=hasil_belum,
        alasan_hasil=alasan_hasil,
        stop=stop,
        dividen=dividen,
    )


def ringkasan_semua(
    sambungan: sqlite3.Connection,
    *,
    status: str | Sequence[str] | None = "aktif",
    mode: str | None = None,
    kode: str | None = None,
    dengan_dividen: bool = True,
) -> tuple[RingkasanPosisi, ...]:
    """Ringkasan banyak posisi dengan **satu** pembacaan harga dan **satu** pembacaan aksi."""
    daftar_posisi = daftar(sambungan, status=status, mode=mode, kode=kode)
    kode_unik = [satu.kode for satu in daftar_posisi]
    harga = harga_terakhir(sambungan, kode_unik)
    peta_aksi = aksi_korporasi(sambungan, kode_unik)
    return tuple(
        ringkasan(
            sambungan,
            satu,
            harga=harga.get(satu.kode),
            harga_diketahui=True,
            aksi=peta_aksi.get(satu.kode, ()),
            dengan_dividen=dengan_dividen,
        )
        for satu in daftar_posisi
    )


# ---------------------------------------------------------------------------------------
# Risiko terbuka seluruh posisi (suku pertama PRD 8.2, AC-6)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RingkasanRisikoTerbuka:
    """Jumlah risiko terbuka posisi aktif, beserta yang **tidak dapat dinilai** dan sebabnya."""

    total: int
    jumlah_aktif: int
    jumlah_dinilai: int
    rincian: tuple[str, ...]
    tidak_dinilai: tuple[str, ...]

    @property
    def lengkap(self) -> bool:
        return not self.tidak_dinilai


def risiko_terbuka(
    sambungan: sqlite3.Connection,
    *,
    ringkasan_posisi: Sequence[RingkasanPosisi] | None = None,
) -> RingkasanRisikoTerbuka:
    """`(penutupan terakhir − stop terkini) × lembar` untuk tiap posisi aktif (PRD 8.2).

    Posisi yang risikonya tidak dapat dinilai (tanpa stop, atau tanpa harga) **tidak** dijumlahkan
    sebagai nol: ia dilaporkan, sebab jumlah yang lebih kecil daripada kenyataan adalah angka yang
    paling berbahaya untuk sebuah batas risiko (aturan keras 2).
    """
    isi = list(ringkasan_posisi) if ringkasan_posisi is not None else list(ringkasan_semua(sambungan))
    total = 0
    dinilai = 0
    rincian: list[str] = []
    tidak_dinilai: list[str] = []
    aktif = 0
    for satu in isi:
        if not satu.posisi.aktif:
            continue
        aktif += 1
        if satu.risiko_terbuka is None:
            tidak_dinilai.append(
                f"posisi #{satu.posisi.id_posisi} {satu.posisi.kode}: {satu.alasan_risiko}"
            )
            continue
        total += satu.risiko_terbuka
        dinilai += 1
        if satu.risiko_terbuka:
            rincian.append(
                f"posisi #{satu.posisi.id_posisi} {satu.posisi.kode}: "
                f"{satu.risiko_terbuka}"
            )
    return RingkasanRisikoTerbuka(
        total=total,
        jumlah_aktif=aktif,
        jumlah_dinilai=dinilai,
        rincian=tuple(rincian),
        tidak_dinilai=tuple(tidak_dinilai),
    )


# ---------------------------------------------------------------------------------------
# Baca
# ---------------------------------------------------------------------------------------


def terkini(sambungan: sqlite3.Connection, id_posisi: int) -> Posisi | None:
    baris = sambungan.execute(
        "SELECT * FROM v_posisi_terkini WHERE id_posisi = ?", (id_posisi,)
    ).fetchone()
    return None if baris is None else _ke_posisi(baris)


def wajib_ada(sambungan: sqlite3.Connection, id_posisi: int) -> Posisi:
    posisi = terkini(sambungan, id_posisi)
    if posisi is None:
        raise GalatPosisi(f"posisi #{id_posisi} tidak ada di basis data")
    return posisi


def daftar(
    sambungan: sqlite3.Connection,
    *,
    status: str | Sequence[str] | None = None,
    mode: str | None = None,
    kode: str | None = None,
) -> tuple[Posisi, ...]:
    """Posisi pada revisi terakhirnya, urut `id_posisi` (urut dibuka)."""
    kueri = "SELECT * FROM v_posisi_terkini"
    syarat: list[str] = []
    nilai: list[object] = []
    if status is not None:
        satu_status = (status,) if isinstance(status, str) else tuple(status)
        if not satu_status:
            return ()
        syarat.append(f"status IN ({', '.join('?' for _ in satu_status)})")
        nilai.extend(satu_status)
    if mode is not None:
        syarat.append("mode = ?")
        nilai.append(mode)
    if kode is not None:
        syarat.append("kode = ?")
        nilai.append(kode.strip().upper())
    if syarat:
        kueri += " WHERE " + " AND ".join(syarat)
    kueri += " ORDER BY id_posisi"
    return tuple(_ke_posisi(baris) for baris in sambungan.execute(kueri, nilai))


def riwayat(sambungan: sqlite3.Connection, id_posisi: int) -> tuple[Posisi, ...]:
    """Seluruh revisi satu posisi, terlama lebih dulu — bukti "tidak ada penghapusan senyap"."""
    return tuple(
        _ke_posisi(baris)
        for baris in sambungan.execute(
            "SELECT * FROM posisi WHERE id_posisi = ? ORDER BY revisi", (id_posisi,)
        )
    )


def daftar_transaksi(
    sambungan: sqlite3.Connection,
    *,
    id_posisi: int | None = None,
    kode: str | None = None,
) -> tuple[Transaksi, ...]:
    """Transaksi pada revisi terakhirnya, urut tanggal lalu id."""
    kueri = "SELECT * FROM v_transaksi_terkini"
    syarat: list[str] = []
    nilai: list[object] = []
    if id_posisi is not None:
        syarat.append("id_posisi = ?")
        nilai.append(id_posisi)
    if kode is not None:
        syarat.append("kode = ?")
        nilai.append(kode.strip().upper())
    if syarat:
        kueri += " WHERE " + " AND ".join(syarat)
    kueri += " ORDER BY tanggal, id_transaksi"
    return tuple(_ke_transaksi(baris) for baris in sambungan.execute(kueri, nilai))


def riwayat_transaksi(sambungan: sqlite3.Connection, id_transaksi: int) -> tuple[Transaksi, ...]:
    return tuple(
        _ke_transaksi(baris)
        for baris in sambungan.execute(
            "SELECT * FROM transaksi WHERE id_transaksi = ? ORDER BY revisi", (id_transaksi,)
        )
    )


def id_rencana_dieksekusi(sambungan: sqlite3.Connection) -> frozenset[int]:
    """Rencana yang **sudah** punya transaksi — dipakai agar risikonya tidak dihitung dua kali.

    PRD 8.2 menjumlahkan risiko terbuka posisi aktif **ditambah** risiko rencana yang belum
    dieksekusi. Rencana yang transaksinya sudah tercatat bukan lagi "belum dieksekusi": risikonya
    sudah hidup di posisinya, dan menjumlahkan keduanya menghitung risiko yang sama dua kali.
    """
    return frozenset(
        int(baris[0])
        for baris in sambungan.execute(
            "SELECT DISTINCT id_rencana FROM v_transaksi_terkini WHERE id_rencana IS NOT NULL"
        )
    )


# ---------------------------------------------------------------------------------------
# Pemeriksaan masukan
# ---------------------------------------------------------------------------------------


def _periksa_aksi(aksi: str) -> None:
    if aksi not in AKSI_SAH:
        raise GalatPosisi(
            f"aksi {aksi!r} tidak dikenal; yang sah: {', '.join(AKSI_SAH)} (PRD 5: hanya posisi "
            "beli — tidak ada short, margin, atau derivatif)"
        )


def _periksa_mode(mode: str | None) -> str:
    if mode is None:
        raise GalatPosisi(
            "transaksi dan posisi wajib menyatakan modenya ("
            f"{' atau '.join(MODE_SAH)}, PRD 9.11): selama masa simulasi hanya data simulasi yang "
            "dipakai menilai preset, dan mode yang tidak dinyatakan membuat pemisahan itu mustahil"
        )
    if mode not in MODE_SAH:
        raise GalatPosisi(f"mode {mode!r} tidak dikenal; yang sah: {', '.join(MODE_SAH)}")
    return mode


def _periksa_kode_dikenal(sambungan: sqlite3.Connection, kode: str) -> None:
    baris = sambungan.execute("SELECT 1 FROM v_emiten_terkini WHERE kode = ?", (kode,)).fetchone()
    if baris is None:
        raise GalatPosisi(
            f"kode {kode!r} tidak ada di daftar emiten. Jalankan --ambil-emiten/--impor lebih dulu, "
            "atau periksa ejaannya — salah ketik yang lolos akan membuat posisinya menempel pada "
            "emiten yang tidak pernah dibeli"
        )


def _hari(tanggal: date | str | None) -> date:
    if isinstance(tanggal, str):
        try:
            return date.fromisoformat(tanggal)
        except ValueError as galat:
            raise GalatPosisi(
                f"tanggal {tanggal!r} bukan tanggal ISO (YYYY-MM-DD): {galat}"
            ) from galat
    return tanggal or date.today()


def _tabel_tick_atau_tidak(
    sambungan: sqlite3.Connection, pada: date
) -> tuple[risiko.TabelTick | None, str | None]:
    """Tabel fraksi harga (B2) bila sudah terverifikasi; selain itu `None` + sebabnya.

    Bukan kegagalan: mencatat transaksi yang **sudah terjadi** tidak boleh terhalang parameter
    yang belum diisi. Yang tidak boleh adalah penerimaannya diam-diam — karena itu sebabnya
    dikembalikan untuk dilaporkan.
    """
    try:
        return risiko.tabel_tick(sambungan, pada), None
    except (konfigurasi.ParameterBelumSiap, risiko.GalatRisiko) as galat:
        return None, str(galat)


def _lot_atau_tidak(sambungan: sqlite3.Connection, pada: date) -> tuple[int | None, str | None]:
    try:
        status = konfigurasi.nilai_efektif(sambungan, "lot", "", pada)
        return int(status.ambil().muatan[0]["nilai_lembar"]), None
    except (konfigurasi.ParameterBelumSiap, konfigurasi.GalatKonfigurasi) as galat:
        return None, str(galat)


def _stop_awal_untuk(
    sambungan: sqlite3.Connection, kode: str, id_rencana: int | None
) -> tuple[int | None, date | None, str | None]:
    """Stop awal yang **dinyatakan** sumbernya: rencana yang dieksekusi, atau tesis kandidatnya.

    Tidak ada tebakan di sini: kalau keduanya tidak ada, hasilnya `None` — dan itu pelanggaran V1
    yang dicatat, bukan stop yang dikarang dari ATR (stop ATR adalah keluaran kalkulator, dan
    kalkulator yang belum dijalankan bukan alasan menganggap posisinya punya stop).

    **Basis tanggalnya ikut dikembalikan.** Level stop dari sebuah rencana dinyatakan dalam basis
    harga **saat rencana itu dibuat**, bukan saat transaksinya dicatat; kalau di antaranya ada
    split, dua tanggal itu menghasilkan angka risiko yang berbeda. Karena itu basisnya diambil dari
    sumbernya (`rencana.tanggal`, `kandidat.dicatat_pada`), bukan dari waktu pencatatan posisi.
    """
    if id_rencana is not None:
        rencana = risiko.terkini(sambungan, id_rencana)
        if rencana is None:
            raise GalatPosisi(f"rencana #{id_rencana} tidak ada di basis data")
        return (
            int(rencana.stop),
            date.fromisoformat(rencana.tanggal),
            f"stop dari rencana #{id_rencana} (dasar: {rencana.dasar_stop}, "
            f"basis {rencana.tanggal})",
        )
    baris = sambungan.execute(
        "SELECT id_kandidat, revisi, stop_awal, dicatat_pada FROM v_kandidat_terkini"
        " WHERE kode = ? AND status IN ('watchlist', 'rencana', 'posisi') AND stop_awal IS NOT NULL"
        " ORDER BY id_kandidat DESC LIMIT 1",
        (kode,),
    ).fetchone()
    if baris is None:
        return None, None, None
    basis = date.fromisoformat(str(baris["dicatat_pada"])[:10])
    return (
        int(baris["stop_awal"]),
        basis,
        f"stop awal dari tesis kandidat #{baris['id_kandidat']} r{baris['revisi']} (PRD 9.6, "
        f"basis {basis.isoformat()})",
    )


def _biaya(
    sambungan: sqlite3.Connection,
    *,
    aksi: str,
    harga: int,
    lembar: int,
    biaya: int | None,
    pajak: int | None,
    broker: str | None,
    pada: date,
) -> tuple[int | None, str | None, int | None, tuple[str, ...]]:
    """Biaya transaksi + asalnya + bagian pajaknya, atau `None` bila tidak dapat diketahui.

    Tarif *all-in* (K23) sudah memuat PPh final penjualan, jadi `pajak` hanya diisi bila bagiannya
    **dapat dipisahkan**; kalau tidak, ia `None` — dan itu berbeda artinya dari nol.
    """
    if biaya is not None:
        if biaya < 0:
            raise GalatPosisi(f"biaya tidak boleh negatif, bukan {biaya}")
        if pajak is not None and pajak > biaya:
            raise GalatPosisi(
                f"pajak ({pajak}) lebih besar daripada biaya ({biaya}). `pajak` adalah BAGIAN dari "
                "biaya, bukan tambahan di atasnya — menjumlahkan keduanya menghitung PPh dua kali "
                "pada tarif all-in (K23)"
            )
        return biaya, "dicatat_pengguna", pajak, ()

    sisi = risiko.SISI_BELI if aksi == "beli" else risiko.SISI_JUAL
    try:
        rincian_biaya = risiko.biaya_sisi(sambungan, sisi, harga, pada, broker=broker)
    except (konfigurasi.ParameterBelumSiap, konfigurasi.GalatKonfigurasi, risiko.GalatRisiko) as galat:
        return (
            None,
            None,
            None,
            (
                "biaya transaksi tidak dicatat dan tidak dapat dihitung dari tarif: "
                f"{galat}. Transaksinya tetap dicatat, tetapi hasil bersihnya belum termasuk biaya "
                "— itulah sebabnya ia ditandai, bukan dianggap nol",
            ),
        )

    total = rincian_biaya.biaya_per_lembar * lembar
    pajak_hitung: int | None = None
    catatan = list(rincian_biaya.rincian)
    if aksi == "jual":
        if rincian_biaya.pph_bp:
            per_lembar = _ceil(Fraction(rincian_biaya.pph_bp * harga, 10000))
            pajak_hitung = per_lembar * lembar
        else:
            catatan.append(
                "bagian PPh final tidak dapat dipisahkan dari tarif (K23), jadi kolom `pajak` "
                "dibiarkan kosong — bukan nol"
            )
    return total, "dihitung_dari_tarif", pajak_hitung, tuple(catatan)


# ---------------------------------------------------------------------------------------
# Tulis: catat transaksi
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PendaftaranTransaksi:
    """Hasil `catat_transaksi`: barisnya, posisinya, dan apa yang belum beres menurut aturan."""

    transaksi: Transaksi
    posisi: Posisi
    pelanggaran: tuple[str, ...]
    catatan: tuple[str, ...]

    def ringkas(self) -> str:
        baris = [self.transaksi.ringkas(), f"posisi {self.posisi.kode} #{self.posisi.id_posisi}"]
        baris.append(
            f"status posisi: {self.posisi.status}"
            + (
                f" · stop {tampilan.rupiah(self.posisi.stop_terkini)}"
                if self.posisi.stop_terkini is not None
                else " · TANPA STOP (V1)"
            )
        )
        for satu in self.catatan:
            baris.append(f"      catatan: {satu}")
        return "\n".join(baris)


def catat_transaksi(
    sambungan: sqlite3.Connection,
    kode: str,
    aksi: str,
    *,
    harga: int,
    lembar: int,
    mode: str,
    tanggal: date | str | None = None,
    id_rencana: int | None = None,
    id_posisi: int | None = None,
    biaya: int | None = None,
    pajak: int | None = None,
    broker: str | None = None,
    catatan: str | None = None,
    sumber: str = SUMBER_TRANSAKSI,
    dicatat_pada: str | None = None,
) -> PendaftaranTransaksi:
    """Catat satu eksekusi manual (PRD 9.1 langkah 9) dan perbarui posisinya.

    Yang **tidak** dilakukan modul ini: menghalangi pencatatan karena pelanggaran. PRD 9.8 menilai
    kepatuhan dari transaksi yang tercatat, dan eksekusi yang sudah terjadi di sekuritas tidak
    menjadi tidak terjadi karena aplikasi menolak mencatatnya. Yang dilakukan: pelanggarannya
    dideteksi, disimpan di barisnya, dan dikembalikan supaya terlihat di layar.
    """
    _periksa_aksi(aksi)
    mode = _periksa_mode(mode)
    kode = kode.strip().upper()
    _periksa_kode_dikenal(sambungan, kode)
    if harga <= 0:
        raise GalatPosisi(f"harga harus lebih dari nol, bukan {harga}")
    if lembar <= 0:
        raise GalatPosisi(f"lembar harus lebih dari nol, bukan {lembar}")
    hari = _hari(tanggal)

    catatan_kaki: list[str] = []
    tabel, alasan_tabel = _tabel_tick_atau_tidak(sambungan, hari)
    if tabel is None:
        catatan_kaki.append(
            f"fraksi harga (B2) belum dapat dipakai, jadi harga transaksi tidak diperiksa "
            f"terhadap tick: {alasan_tabel}"
        )
    else:
        try:
            risiko.periksa_harga(harga, tabel, "harga transaksi")
        except risiko.GalatRisiko as galat:
            raise GalatPosisi(str(galat)) from galat
    lot, alasan_lot = _lot_atau_tidak(sambungan, hari)
    if lot is None:
        catatan_kaki.append(
            f"parameter lot (B1) belum dapat dipakai, jadi lembar tidak diperiksa kelipatan lot: "
            f"{alasan_lot}"
        )
    elif lembar % lot:
        raise GalatPosisi(
            f"{lembar} lembar bukan kelipatan lot {lot} (PRD 10: jumlah lembar selalu kelipatan "
            f"lot). Kelipatan terdekat: {lembar // lot * lot} atau {(lembar // lot + 1) * lot}"
        )

    # --- posisi yang dituju ---------------------------------------------------------------
    posisi_lama: Posisi | None = None
    if id_posisi is not None:
        posisi_lama = wajib_ada(sambungan, id_posisi)
        if not posisi_lama.aktif:
            raise GalatPosisi(
                f"posisi #{id_posisi} sudah {posisi_lama.status} (tutup {posisi_lama.tgl_tutup}); "
                "transaksi baru menuntut posisi yang masih aktif"
            )
        if posisi_lama.kode != kode:
            raise GalatPosisi(
                f"posisi #{id_posisi} adalah {posisi_lama.kode}, bukan {kode}"
            )
        if posisi_lama.mode != mode:
            raise GalatPosisi(
                f"posisi #{id_posisi} bermode {posisi_lama.mode}, sedangkan transaksinya {mode} "
                "(PRD 9.11: kedua mode dilaporkan terpisah, jadi tidak boleh tercampur)"
            )
    else:
        calon = daftar(sambungan, status="aktif", kode=kode, mode=mode)
        if len(calon) > 1:
            raise GalatPosisi(
                f"ada {len(calon)} posisi aktif {kode} bermode {mode} "
                f"({', '.join('#' + str(satu.id_posisi) for satu in calon)}); sebutkan yang mana "
                "lewat --id-posisi"
            )
        posisi_lama = calon[0] if calon else None
    if aksi == "jual" and posisi_lama is None:
        raise GalatPosisi(
            f"tidak ada posisi aktif {kode} bermode {mode} yang bisa dijual. Penjualan menuntut "
            "posisi yang sudah ada — dan PRD 5 hanya mengizinkan posisi beli (long), jadi menjual "
            "lebih banyak daripada yang dimiliki bukan keadaan yang bisa dicatat"
        )

    # --- rencana & pelanggaran ------------------------------------------------------------
    pelanggaran: list[str] = []
    if id_rencana is None and posisi_lama is not None:
        id_rencana = posisi_lama.id_rencana
    rencana = None
    if id_rencana is not None:
        rencana = risiko.terkini(sambungan, id_rencana)
        if rencana is None:
            raise GalatPosisi(f"rencana #{id_rencana} tidak ada di basis data")
        if rencana.kode != kode:
            raise GalatPosisi(
                f"rencana #{id_rencana} adalah {rencana.kode}, bukan {kode}"
            )

    angka_lama = hitungan(sambungan, posisi_lama.id_posisi) if posisi_lama else HitunganPosisi()
    terbuka_lama = angka_lama.lembar_terbuka
    if aksi == "jual" and lembar > terbuka_lama:
        raise GalatPosisi(
            f"posisi #{posisi_lama.id_posisi} hanya memegang {terbuka_lama} lembar, tidak bisa "
            f"dijual {lembar} lembar (PRD 5: hanya posisi beli, tanpa short)"
        )
    lembar_setelah = terbuka_lama - lembar if aksi == "jual" else terbuka_lama + lembar

    stop_awal: int | None = None
    basis_stop: date | None = None
    if aksi == "beli":
        if id_rencana is None:
            pelanggaran.append("V6")
        elif rencana is not None and lembar_setelah > rencana.lembar:
            pelanggaran.append("V2")
            catatan_kaki.append(
                f"lembar posisi setelah transaksi ini {lembar_setelah} melebihi rencana "
                f"#{id_rencana} ({rencana.lembar} lembar) — pelanggaran V2"
            )
        if posisi_lama is None or posisi_lama.stop_terkini is None:
            # V1 hanya bisa dinilai dari stop yang **dinyatakan** rencana atau tesis; stop ATR
            # adalah keluaran kalkulator, dan kalkulator yang belum dijalankan bukan alasan
            # menganggap posisinya sudah punya stop.
            stop_awal, basis_stop, asal_stop = _stop_awal_untuk(sambungan, kode, id_rencana)
            if stop_awal is None:
                pelanggaran.append("V1")
                catatan_kaki.append(
                    "posisi ini berjalan TANPA STOP: tidak ada rencana tersimpan maupun stop awal "
                    "tesis untuk kode ini (pelanggaran V1, PRD 9.8). Risiko terbukanya karena itu "
                    "tidak dapat dinilai sampai stopnya diisi lewat --ubah-stop"
                )
            elif asal_stop:
                catatan_kaki.append(f"{asal_stop}; dipakai sebagai stop posisi ini")

    if posisi_lama is not None:
        tanggal_terakhir = sambungan.execute(
            "SELECT MAX(tanggal) FROM v_transaksi_terkini WHERE id_posisi = ?",
            (posisi_lama.id_posisi,),
        ).fetchone()[0]
        if tanggal_terakhir and hari.isoformat() < tanggal_terakhir:
            raise GalatPosisi(
                f"transaksi posisi #{posisi_lama.id_posisi} sudah tercatat sampai "
                f"{tanggal_terakhir}; transaksi bertanggal {hari.isoformat()} akan membuat lembar "
                "pada tiap tanggal tidak lagi bisa diturunkan dari urutannya. Catat berurutan "
                "menurut tanggal, atau perbaiki tanggal yang salah lewat revisi"
            )
    elif hari > date.today():
        catatan_kaki.append(
            f"posisi ini dibuka pada {hari.isoformat()}, tanggal yang belum terjadi"
        )

    biaya_rupiah, asal_biaya, pajak_rupiah, catatan_biaya = _biaya(
        sambungan,
        aksi=aksi,
        harga=harga,
        lembar=lembar,
        biaya=biaya,
        pajak=pajak,
        broker=broker,
        pada=hari,
    )
    catatan_kaki.extend(catatan_biaya)

    # --- tulis (satu transaksi basis data) ------------------------------------------------
    teks_pelanggaran = _gabung_pelanggaran(pelanggaran)
    with db.tulis(sambungan) as koneksi:
        if posisi_lama is None:
            id_posisi_baru = int(
                koneksi.execute("SELECT COALESCE(MAX(id_posisi), 0) + 1 FROM posisi").fetchone()[0]
            )
            koneksi.execute(
                "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, tgl_tutup, status,"
                " stop_terkini, tgl_stop, id_rencana, mode, pelanggaran, catatan, sumber,"
                " diketahui_pada)"
                " VALUES (?, 1, ?, ?, NULL, 'aktif', ?, ?, ?, ?, NULL, ?, ?, ?)",
                (
                    id_posisi_baru,
                    kode,
                    hari.isoformat(),
                    stop_awal,
                    basis_stop.isoformat() if (stop_awal is not None and basis_stop) else None,
                    id_rencana,
                    mode,
                    catatan,
                    sumber,
                    dicatat_pada or db.waktu_iso(),
                ),
            )
        else:
            id_posisi_baru = posisi_lama.id_posisi

        id_transaksi = int(
            koneksi.execute("SELECT COALESCE(MAX(id_transaksi), 0) + 1 FROM transaksi").fetchone()[0]
        )
        koneksi.execute(
            "INSERT INTO transaksi (id_transaksi, revisi, id_posisi, id_rencana, tanggal, kode,"
            " aksi, harga, lembar, biaya, asal_biaya, pajak, mode, pelanggaran, catatan, sumber,"
            " diketahui_pada)"
            " VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id_transaksi,
                id_posisi_baru,
                id_rencana,
                hari.isoformat(),
                kode,
                aksi,
                harga,
                lembar,
                biaya_rupiah,
                asal_biaya,
                pajak_rupiah,
                mode,
                teks_pelanggaran,
                catatan,
                sumber,
                dicatat_pada or db.waktu_iso(),
            ),
        )

        if posisi_lama is not None and posisi_lama.stop_terkini is None and stop_awal is not None:
            # Posisi yang tadinya tanpa stop kini punya stop yang **dinyatakan** rencana/tesis.
            # Tanpa revisi ini, V1 akan terus terlihat pada posisi yang stopnya sudah jelas.
            koneksi.execute(
                "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, tgl_tutup, status,"
                " stop_terkini, tgl_stop, id_rencana, mode, pelanggaran, catatan, sumber,"
                " diketahui_pada)"
                " VALUES (?, ?, ?, ?, NULL, 'aktif', ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    posisi_lama.id_posisi,
                    posisi_lama.revisi + 1,
                    posisi_lama.kode,
                    posisi_lama.tgl_buka,
                    stop_awal,
                    basis_stop.isoformat() if basis_stop else None,
                    id_rencana,
                    posisi_lama.mode,
                    posisi_lama.pelanggaran,
                    posisi_lama.catatan,
                    posisi_lama.sumber,
                    dicatat_pada or db.waktu_iso(),
                ),
            )

        if aksi == "jual" and lembar_setelah == 0:
            revisi = (posisi_lama.revisi if posisi_lama else 1) + 1
            koneksi.execute(
                "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, tgl_tutup, status,"
                " stop_terkini, tgl_stop, id_rencana, mode, pelanggaran, catatan, sumber,"
                " diketahui_pada)"
                " VALUES (?, ?, ?, ?, ?, 'ditutup', ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    id_posisi_baru,
                    revisi,
                    kode,
                    posisi_lama.tgl_buka if posisi_lama else hari.isoformat(),
                    hari.isoformat(),
                    posisi_lama.stop_terkini if posisi_lama else stop_awal,
                    posisi_lama.tgl_stop if posisi_lama else None,
                    id_rencana,
                    mode,
                    posisi_lama.pelanggaran if posisi_lama else None,
                    posisi_lama.catatan if posisi_lama else catatan,
                    posisi_lama.sumber if posisi_lama else sumber,
                    dicatat_pada or db.waktu_iso(),
                ),
            )

    baris = sambungan.execute(
        "SELECT * FROM v_transaksi_terkini WHERE id_transaksi = ?", (id_transaksi,)
    ).fetchone()
    posisi_baru = wajib_ada(sambungan, id_posisi_baru)
    return PendaftaranTransaksi(
        transaksi=_ke_transaksi(baris),
        posisi=posisi_baru,
        # Urut kode, sama dengan yang tersimpan di barisnya: hasil yang urutannya berbeda dari
        # yang tersimpan akan membuat dua tempat tampak tidak sepakat.
        pelanggaran=tuple(sorted(pelanggaran)),
        catatan=tuple(catatan_kaki),
    )


# ---------------------------------------------------------------------------------------
# Tulis: stop terkini (trailing; pelanggaran V5 bila menjauh)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PerubahanStop:
    posisi: Posisi
    lama: int | None
    baru: int
    pelanggaran: tuple[str, ...]
    catatan: tuple[str, ...]

    def ringkas(self) -> str:
        teks = (
            f"posisi #{self.posisi.id_posisi} {self.posisi.kode}: stop "
            + (tampilan.rupiah(self.lama) if self.lama is not None else "(belum ada)")
            + " -> "
            + tampilan.rupiah(self.baru)
            + f" (revisi {self.posisi.revisi})"
        )
        for satu in self.catatan:
            teks += f"\n      catatan: {satu}"
        if self.pelanggaran:
            teks += "\n      PELANGGARAN: " + "; ".join(
                sebut_pelanggaran(satu) for satu in self.pelanggaran
            )
        return teks


def ubah_stop(
    sambungan: sqlite3.Connection,
    id_posisi: int,
    stop: int,
    *,
    alasan: str | None = None,
    tanggal: date | str | None = None,
    sumber: str = SUMBER_STOP,
    dicatat_pada: str | None = None,
) -> PerubahanStop:
    """Naikkan atau turunkan stop terkini (PRD 9.11 "Aturan stop").

    Stop **boleh** dinaikkan (trailing). Menurunkannya — menjauhi harga — juga bisa dicatat,
    tetapi sebagai **pelanggaran V5** (PRD 9.8): yang dilarang bukan tindakannya, melainkan
    tindakan yang tidak terlihat jejaknya.
    """
    posisi = wajib_ada(sambungan, id_posisi)
    if not posisi.aktif:
        raise GalatPosisi(
            f"posisi #{id_posisi} sudah {posisi.status}; stop hanya untuk posisi aktif"
        )
    if stop <= 0:
        raise GalatPosisi(f"stop harus lebih dari nol, bukan {stop}")
    hari = _hari(tanggal)

    catatan: list[str] = []
    tabel, alasan_tabel = _tabel_tick_atau_tidak(sambungan, hari)
    if tabel is None:
        catatan.append(
            f"fraksi harga (B2) belum dapat dipakai, jadi stop tidak diperiksa terhadap tick: "
            f"{alasan_tabel}"
        )
    else:
        risiko.periksa_harga(stop, tabel, "stop")

    # V5 dibandingkan dalam **basis yang sama**. Tanpa ini, split di antara dua pencatatan stop
    # membuat perbandingannya menyesatkan: stop 2.180 (basis pra-split 1:25) vs stop baru 90
    # adalah kenaikan, tetapi sebagai angka mentah ia terbaca sebagai penurunan 2.090.
    aksi = aksi_korporasi(sambungan, [posisi.kode]).get(posisi.kode, ())
    lama = posisi.stop_terkini
    lama_kini = stop_dalam_basis(posisi, aksi)
    pelanggaran: list[str] = []
    if lama is not None and lama_kini.nilai is None:
        catatan.append(
            f"stop lama ({lama}) TIDAK dapat dibandingkan dengan stop baru: {lama_kini.alasan}"
        )
    elif lama is not None and stop < lama_kini.nilai:
        pelanggaran.append("V5")
        catatan.append(
            f"stop digeser MENJAUHI harga: {lama} -> {stop} (pelanggaran V5, PRD 9.8). "
            "Stop boleh dinaikkan (trailing); menurunkannya menambah risiko per lembar"
            + (
                f". Pembandingnya dalam basis sekarang: {lama_kini.nilai}"
                if lama_kini.disesuaikan
                else ""
            )
        )
    elif lama is None:
        catatan.append(
            "posisi ini sebelumnya tanpa stop (pelanggaran V1); stop sekarang ada — risiko "
            "terbukanya mulai bisa dinilai"
        )
    if lama_kini.disesuaikan and lama_kini.nilai is not None:
        catatan.append(
            f"stop lama {lama} dinyatakan pada basis {lama_kini.basis.isoformat()} dan menjadi "
            f"{lama_kini.nilai} dalam basis sekarang ("
            + ", ".join(_sebut_aksi(satu) for satu in lama_kini.aksi)
            + ")"
        )

    harga = harga_terakhir(sambungan, [posisi.kode]).get(posisi.kode)
    # Stop baru dinyatakan dalam basis `hari`; penutupan terakhir selalu dalam basis sekarang.
    # Keduanya dibandingkan setelah dipindahkan ke basis yang sama — kalau tidak, stop pra-split
    # 17.000 akan selalu tampak "di atas" penutupan pasca-split 915.
    stop_kini = Fraction(stop) / penyesuaian.faktor_lembar(aksi, sesudah=hari)
    if harga is not None and stop_kini > harga.close:
        catatan.append(
            f"stop {stop} di ATAS penutupan terakhir {harga.close} ({harga.tanggal.isoformat()}): "
            "posisinya sudah menembus stop ini, dan itu muncul di dasbor sebagai tindakan menunggu"
            + (f" (stop dalam basis sekarang: {stop_kini})" if stop_kini != stop else "")
        )
    catatan.append(
        f"basis stop ini dicatat {hari.isoformat()} (kolom `tgl_stop`): level stop yang Anda "
        "tetapkan berlaku untuk harga pada basis itu, sehingga split berikutnya bisa "
        "dipindahkan ke basis barunya tanpa menebak"
    )

    teks_catatan = "\n".join([satu for satu in (posisi.catatan, alasan, *catatan) if satu]) or None
    teks_pelanggaran = _gabung_pelanggaran(pelanggaran, posisi.pelanggaran)
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, tgl_tutup, status,"
            " stop_terkini, tgl_stop, id_rencana, mode, pelanggaran, catatan, sumber,"
            " diketahui_pada)"
            " VALUES (?, ?, ?, ?, NULL, 'aktif', ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                posisi.id_posisi,
                posisi.revisi + 1,
                posisi.kode,
                posisi.tgl_buka,
                stop,
                hari.isoformat(),
                posisi.id_rencana,
                posisi.mode,
                teks_pelanggaran,
                teks_catatan,
                sumber,
                dicatat_pada or db.waktu_iso(),
            ),
        )
    return PerubahanStop(
        posisi=wajib_ada(sambungan, id_posisi),
        lama=lama,
        baru=stop,
        pelanggaran=tuple(pelanggaran),
        catatan=tuple(catatan),
    )


# ---------------------------------------------------------------------------------------
# Keluaran terminal
# ---------------------------------------------------------------------------------------


def ringkas_daftar(
    daftar_ringkasan: Sequence[RingkasanPosisi],
    *,
    judul_kosong: str = "(belum ada posisi)",
) -> str:
    """Daftar posisi beserta jumlahnya; yang tidak dapat dinilai selalu disebut."""
    isi = list(daftar_ringkasan)
    if not isi:
        return judul_kosong
    baris = [satu.ringkas() for satu in isi]
    risiko_total = sum(satu.risiko_terbuka or 0 for satu in isi if satu.posisi.aktif)
    belum = sum(satu.hasil_belum_terealisasi or 0 for satu in isi if satu.posisi.aktif)
    terealisasi = sum(satu.hasil_terealisasi or 0 for satu in isi)
    dividen = sum(satu.dividen.total for satu in isi)
    tidak_dinilai = [satu for satu in isi if satu.posisi.aktif and satu.risiko_terbuka is None]
    baris.append(
        f"  {len(isi)} posisi · risiko terbuka {tampilan.rupiah(risiko_total)} · "
        f"belum terealisasi {tampilan.rupiah(belum)} · terealisasi {tampilan.rupiah(terealisasi)}"
        + (f" · dividen diterima {tampilan.rupiah(dividen)} (bruto)" if dividen else "")
    )
    disesuaikan = [satu for satu in isi if satu.hitungan.disesuaikan]
    if disesuaikan:
        baris.append(
            f"  {len(disesuaikan)} posisi lembarnya disesuaikan aksi korporasi (split/reverse "
            "split): "
            + "; ".join(
                f"#{satu.posisi.id_posisi} {satu.posisi.kode} "
                f"{tampilan.angka(satu.hitungan.lembar_terbuka_tercatat, 0)} -> "
                f"{tampilan.angka(float(satu.lembar_terbuka), 0)} lbr"
                for satu in disesuaikan
            )
        )
    tak_bulat = [satu for satu in isi if satu.hitungan.lembar_terbuka_bulat is None]
    if tak_bulat:
        baris.append(
            f"  {len(tak_bulat)} posisi lembarnya TIDAK BULAT setelah penyesuaian (periksa di "
            "sekuritas): "
            + "; ".join(f"#{satu.posisi.id_posisi} {satu.posisi.kode}" for satu in tak_bulat)
        )
    if tidak_dinilai:
        baris.append(
            f"  {len(tidak_dinilai)} posisi aktif risikonya TIDAK DINILAI (bukan nol): "
            + "; ".join(f"#{satu.posisi.id_posisi} {satu.posisi.kode}" for satu in tidak_dinilai)
        )
    return "\n".join(baris)
