"""Ingesti data EOD: dua jalur masuk, satu bentuk data, satu penulisan atomik (F1, PRD 9.3).

Berkas ini adalah **inti** ingesti. Ia tidak tahu-menahu soal yfinance: pengambil data dan
pembaca berkas sama-sama menghasilkan `KumpulanData`, lalu berkas ini yang mengubahnya menjadi
baris bertipe dan menuliskannya ke basis data. Pemisahan itu bukan kerapian belaka — inilah
yang membuat seluruh ingesti bisa diuji tanpa jaringan.

Aturan yang ditegakkan di sini, bukan sekadar didokumentasikan:

1. **Tidak ada angka tebakan (aturan keras 1).** Nilai yang tidak terbaca, negatif, atau
   kosong menjadi `None` — *bukan* 0. Baris tetap ditulis supaya lubangnya terlihat di laporan
   mutu, bukan hilang diam-diam.
2. **Nilai berpecahan tidak dibulatkan diam-diam (T8).** Harga dari sumber tidak resmi bisa
   berpecahan; yang berhitung adalah `INTEGER` rupiah, sedangkan angka aslinya disimpan di
   kolom `*_mentah` supaya perbedaan itu bisa diaudit, bukan tersembunyi.
3. **Label sumber tidak resmi ikut ke setiap baris (P2, PRD 7.2/7.3).** yfinance bukan sumber
   resmi; labelnya menempel di kolom `sumber` tiap baris, bukan hanya di log.
4. **Tulis atomik (A6, AC-19).** Seluruh baris + baris `snapshot` + baris `log_jalan` masuk
   dalam **satu** transaksi. Gagal di tengah berarti tidak ada yang tertulis sama sekali, dan
   snapshot lama tetap utuh.
5. **Gagal itu berisik (aturan keras 7, AC-9).** Kegagalan tidak pernah ditelan: ia menaikkan
   `GalatIngesti` dengan konteks, ditulis ke `log_jalan`, lalu dilaporkan ke pemanggil.
   Sejak U18, kegagalan juga **dipisah jenisnya** (`Kegagalan`): "kode tidak diperdagangkan lagi"
   dan "pengambilan gagal sementara" sama-sama terlihat, tetapi hanya yang kedua dihitung
   terhadap ambang 5% PRD 9.3.
6. **Pengambilan data tidak memegang kunci tulis.** Jaringan diakses **sebelum** transaksi
   dibuka, supaya proses lain tidak menunggu selama pengunduhan (A2).
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from mejasaham import __version__, db
from mejasaham.skema import ASAL_TGL_PUBLIKASI_SAH

# ---------------------------------------------------------------------------------------
# Label sumber — satu tempat, supaya "tidak resmi" tidak bisa hilang dari sebagian baris
# ---------------------------------------------------------------------------------------

#: yfinance adalah sumber **tidak resmi**; labelnya wajib menempel di kolom `sumber` setiap
#: baris yang berasal darinya (PRD 7.2, 7.3; Q8). Sengaja menyebut "tidak resmi" apa adanya
#: supaya laporan mutu dan ekspor tidak perlu menebak asal angkanya.
SUMBER_YFINANCE = "yfinance/Yahoo Finance (tidak resmi)"

#: Berkas impor: labelnya menyebut nama berkas, sehingga satu basis data bisa memuat data dari
#: beberapa berkas berbeda tanpa kehilangan jejak asalnya.
PREFIKS_SUMBER_IMPOR = "impor berkas"

PROSES_REFRESH = "refresh"
PROSES_IMPOR = "impor"

NAMA_BERKAS_EMITEN = "emiten.csv"

#: Nama berkas impor yang dikenali di dalam folder impor. Berkas yang tidak ada dilewati
#: dengan catatan; berkas yang ada tetapi salah **menolak** seluruh impor (gagal berisik).
BERKAS_IMPOR_DIKENAL = (
    (NAMA_BERKAS_EMITEN, "emiten"),
    ("harga-harian.csv", "harga_harian"),
    ("harga-indeks.csv", "harga_indeks"),
    ("aksi-korporasi.csv", "aksi_korporasi"),
    ("catatan-aksi-mutu.csv", "catatan_aksi_mutu"),
    ("sambungan-harga.csv", "sambungan_harga"),
    ("kalender-bursa.csv", "kalender_bursa"),
    ("notasi-khusus.csv", "notasi_khusus"),
    ("imbal-hasil-sun.csv", "imbal_hasil_sun"),
    ("fundamental.csv", "fundamental"),
    ("rasio-bank.csv", "rasio_bank"),
)

#: Nilai `jenis` yang sah di tabel `emiten` (PRD 8.1) dan padanan kata yang diterima dari
#: berkas rujukan. Berkas ditulis manusia, jadi ejaan yang wajar diterima; yang **tidak**
#: dikenal tetap ditolak, bukan ditebak.
JENIS_EMITEN: Mapping[str, str | None] = {
    "bank_keuangan": "bank_keuangan",
    "bank": "bank_keuangan",
    "keuangan": "bank_keuangan",
    "bank & keuangan": "bank_keuangan",
    "siklikal_komoditas": "siklikal_komoditas",
    "siklikal": "siklikal_komoditas",
    "komoditas": "siklikal_komoditas",
    "umum": "umum",
    "": None,
    "-": None,
}

#: Penanda apa yang **sudah** dilakukan sumber terhadap harga yang dikirimnya (K8/C10).
#: `None` berarti belum dinyatakan, dan itu **berbeda** dari "tidak disesuaikan": baris tanpa
#: penanda tidak boleh ditebak — lihat `mejasaham/penyesuaian.py`.
PENYESUAIAN_TIDAK_DISESUAIKAN = "tidak_disesuaikan"
PENYESUAIAN_SPLIT = "split"
PENYESUAIAN_SPLIT_DIVIDEN = "split_dividen"
PENANDA_PENYESUAIAN_SAH = (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_SPLIT_DIVIDEN,
)

#: Satuan yang boleh dinyatakan berkas impor fundamental. Nilai uang **dinormalkan ke rupiah
#: utuh** saat impor (T8), karena laporan "dalam jutaan Rupiah" yang diimpor apa adanya membuat
#: setiap rasio salah 10^6 tanpa terlihat.
FAKTOR_SATUAN_UANG: Mapping[str, int] = {
    "rupiah": 1,
    "ribuan": 10**3,
    "juta": 10**6,
    "miliar": 10**9,
}

#: Jenis laporan fundamental (PRD 8.1): tahunan atau kuartalan kumulatif (YTD). PER TTM dihitung
#: dari keduanya, jadi bedanya tidak boleh hilang (AC-18).
JENIS_LAPORAN_SAH = ("tahunan", "ytd_kumulatif")

#: Asal `tgl_publikasi` sebuah baris fundamental (K18). Daftar sahnya hidup di `skema.py`
#: (kolomnya dijaga CHECK di sana) dan **diimpor**, bukan disalin: dua daftar yang bisa berbeda
#: membuat nilai yang lolos di kode ditolak basis data, atau sebaliknya diterima diam-diam.
#:
#: * `sumber` — tanggal publikasi benar-benar dinyatakan sumbernya (berkas impor, laporan resmi).
#: * `tanggal_pengambilan` — sumber tidak menyatakan tanggal terbitnya, sehingga yang dipakai
#:   adalah tanggal datanya diambil. Ini **bukan** tanggal publikasi dan tidak boleh disebut
#:   begitu di laporan mana pun; gunanya supaya aturan point-in-time (AC-15) tetap dijalankan
#:   tanpa mengarang tanggal.
ASAL_TGL_PUBLIKASI_BAWAAN = "sumber"

#: Dua jenis kegagalan pengambilan (U18, diputuskan 9 Okt 2026).
#:
#: * **Permanen** — sumber menyatakan sendiri bahwa kode itu tidak punya data ("No data found,
#:   symbol may be delisted"). Artinya kode masih tercatat di daftar resmi tetapi **tidak
#:   diperdagangkan lagi**; mengulanginya tidak akan pernah berhasil, dan menghitungnya sebagai
#:   "terlalu banyak yang gagal" membuat snapshot mustahil terbit selamanya (9 Okt 2026: 57 dari
#:   973 kode = 5,9%, jadi gerbang 5% PRD 9.3 selalu menolak). Karena itu ia dilaporkan sebagai
#:   **lubang yang diketahui**, bukan dibiarkan tak terlihat.
#: * **Sementara** — pembatasan laju, waktu habis, galat jaringan, atau sebab yang tidak
#:   dinyatakan sumbernya. Inilah yang tetap dihitung terhadap ambang 5% PRD 9.3.
#:
#: Bawaannya **sementara**: kegagalan yang tidak bisa dipastikan jenisnya harus menahan snapshot,
#: bukan meloloskannya (aturan keras 7).
KEGAGALAN_PERMANEN = "permanen"
KEGAGALAN_SEMENTARA = "sementara"
JENIS_KEGAGALAN_SAH = (KEGAGALAN_PERMANEN, KEGAGALAN_SEMENTARA)


class GalatIngesti(RuntimeError):
    """Ingesti tidak bisa dilanjutkan, atau datanya tidak layak dipercaya apa adanya."""


class IngestiDibatalkan(GalatIngesti):
    """Ambang kegagalan terlewati: snapshot **tidak** diterbitkan (PRD 9.3).

    Ada sebagai kelas tersendiri supaya pemanggil bisa membedakan "datanya salah bentuk"
    (yang berarti berkas/sumber harus diperbaiki) dari "terlalu banyak yang gagal diambil"
    (yang berarti snapshot lama tetap dipakai dan pengguna diberi peringatan, AC-8).
    """


# ---------------------------------------------------------------------------------------
# Kontrak data: bentuk yang sama untuk kedua jalur masuk
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Emiten:
    """Baris rujukan emiten. `dicatat_pada` = kapan manusia mencatatnya di berkas rujukan."""

    kode: str
    nama: str
    sektor_idx_ic: str | None = None
    #: Sektor **sebagaimana dinyatakan sumber data** (K25). Bukan IDX-IC: sumber EOD memakai
    #: taksonomi sendiri, dan menamainya `sektor_idx_ic` akan membuat dua hal berbeda tampak sama
    #: — dengan akibat di angka, bukan di tampilan (batas bobot per sektor, PRD 9.7).
    sektor_sumber: str | None = None
    jenis: str | None = None
    papan: str | None = None
    status_notasi: str | None = None
    #: Tanggal pencatatan saham (listing date) menurut sumber yang menyatakannya. Kosong =
    #: sumber tidak menyatakannya — bukan tanggal karangan, dan bukan tanggal hari ini.
    #: Namanya mengikuti tabel `emiten` di PRD 12 (tabel 23); arti namanya dipertanyakan
    #: di `docs/keputusan.md` (P18) sebab PRD tidak pernah menjelaskannya.
    tanggal_notasi: date | None = None
    jumlah_saham: int | None = None
    free_float_bp: int | None = None
    sumber: str = ""
    dicatat_pada: date | None = None


@dataclass(frozen=True)
class HargaHarian:
    """Satu bar EOD. Seluruh nilai uang `INTEGER` rupiah; aslinya di `*_mentah` (T8).

    `nilai` boleh berisi nilai transaksi yang diterbitkan sumber; bila `None`, ingesti
    menghitungnya `close x volume` dengan `asal_nilai = 'hitung'` (U6).
    """

    kode: str
    tanggal: date
    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None
    volume: int | None = None
    nilai: int | None = None
    open_mentah: str | None = None
    high_mentah: str | None = None
    low_mentah: str | None = None
    close_mentah: str | None = None
    volume_mentah: str | None = None
    nilai_mentah: str | None = None
    #: Apa yang sudah dilakukan sumber terhadap harga ini (K8/C10). `None` = belum dinyatakan.
    penyesuaian_sumber: str | None = None
    #: Sumber baris ini bila berbeda dari sumber kumpulannya. Kosong = ikut label kumpulan.
    #: Dipakai jalur impor harga untuk **cek sumber kedua** (PRD 7.3): dua sumber harus bisa
    #: dibedakan di kolom `sumber`, sebab tanpa itu "selisih terhadap sumber kedua" tidak bisa
    #: dihitung sama sekali — dan pemeriksaannya akan selamanya berstatus belum dapat dijalankan.
    sumber: str = ""
    #: Kapan baris ini diketahui — diisi `potret` saat membaca kembali; ingesti **tidak** memakainya
    #: (waktu tulis ditentukan jalan ingestinya). Penanda `split`/`split_dividen` hanya mencakup
    #: split yang sudah terjadi pada waktu ini (P42 c), jadi tanpa nilai ini penanda itu tidak bisa
    #: dibaca dengan jujur.
    diketahui_pada: str | None = None


@dataclass(frozen=True)
class PenutupanIndeks:
    indeks: str
    tanggal: date
    close: int | None = None
    close_mentah: str | None = None


@dataclass(frozen=True)
class AksiKorporasi:
    """Aksi korporasi (U4). Konvensi rasio: harga disesuaikan x (`rasio_lama`/`rasio_baru`).

    `tenggat` hanya berlaku untuk `right_issue` (batas waktu pelaksanaan, PRD 9.11). `None`
    berarti **sumbernya belum menyatakannya** — bukan "tidak ada tenggat", dan berbeda artinya
    ketika keputusan penebusan harus diambil.
    """

    kode: str
    tanggal: date
    jenis: str
    rasio_lama: int | None = None
    rasio_baru: int | None = None
    harga_tebus: int | None = None
    dividen_per_saham: int | None = None
    tenggat: str | None = None
    #: Sumber baris ini bila dinyatakan berkasnya. Kosong = ikut label kumpulan, seperti semula
    #: (pola yang sama dengan `HariBursa.sumber`). Dipakai keluaran agar angka dividen yang ikut
    #: menghitung hasil menyebut asalnya (PRD 10: metrik tanpa asal data tidak ditampilkan).
    sumber: str | None = None
    keterangan: str | None = None


@dataclass(frozen=True)
class CatatanAksiMutu:
    """Konteks aksi bersumber untuk laporan mutu, tanpa makna posisi atau penyesuaian."""

    kode: str
    tanggal_efektif: date
    instrumen_aksi: str
    ringkasan_bukti: str
    sumber_url: str
    sumber: str


@dataclass(frozen=True)
class SambunganHarga:
    """Pernyataan "sejak tanggal ini, harga dibaca dari label resmi" (K97). `aktif=False` mencabutnya."""

    berlaku_sejak: date
    sumber_resmi: str
    aktif: bool
    sumber: str
    keterangan: str | None = None


@dataclass(frozen=True)
class HariBursa:
    tanggal: date
    hari_bursa: bool
    keterangan: str | None = None
    #: Sumber baris ini bila dinyatakan berkasnya (mis. nomor pengumuman KSEI dari
    #: `--ambil-kalender`). Kosong = ikut label kumpulan, seperti sebelum kolom ini ada.
    sumber: str | None = None


@dataclass(frozen=True)
class NotasiKhusus:
    kode: str
    jenis: str
    tanggal_mulai: date
    tanggal_selesai: date | None = None
    keterangan: str | None = None


@dataclass(frozen=True)
class ImbalHasilSUN:
    tanggal: date
    tenor_tahun: int
    imbal_hasil_bp: int
    imbal_hasil_mentah: str | None = None


@dataclass(frozen=True)
class Fundamental:
    """Satu laporan fundamental (PRD 8.1/12), **sejak** `tgl_publikasi` (aturan keras 3, AC-15).

    Kolom uang sudah dalam rupiah utuh (T8); `satuan_uang` menyimpan satuan yang dinyatakan
    sumbernya, dan `*_mentah` menyimpan angka aslinya untuk audit. `mata_uang` yang bukan IDR
    membuat metrik yang mencampur laporan dengan harga rupiah berstatus "tidak dihitung".

    `asal_tgl_publikasi` menyatakan **dari mana** tanggal itu datang (lihat catatan konstanta di
    atas). Bawaannya `sumber`, sebab jalur impor berkas memang memuat tanggal publikasinya;
    pengambil otomatis mengisinya `tanggal_pengambilan` supaya laporan tidak pernah menyebut
    tanggal pengambilan sebagai tanggal terbit.
    """

    kode: str
    periode: date
    jenis_laporan: str
    tgl_publikasi: date
    asal_tgl_publikasi: str = ASAL_TGL_PUBLIKASI_BAWAAN
    mata_uang: str = "IDR"
    satuan_uang: str = "rupiah"
    pendapatan: int | None = None
    laba_induk: int | None = None
    ekuitas_induk: int | None = None
    ebit: int | None = None
    beban_bunga: int | None = None
    da: int | None = None
    utang_bunga: int | None = None
    kas: int | None = None
    cfo: int | None = None
    jumlah_saham: int | None = None
    dps: int | None = None
    pendapatan_mentah: str | None = None
    laba_induk_mentah: str | None = None
    ekuitas_induk_mentah: str | None = None
    #: Label sumber **per baris**, bila berkasnya menyatakannya (kolom `sumber` memang wajib di
    #: `fundamental.csv`). Selama ini kolom itu divalidasi lalu dibuang, sehingga baris hasil
    #: `--ambil-fundamental` — yang wajib berlabel "tidak resmi" (K7) — akan tersimpan sebagai
    #: "impor berkas: <folder>": asalnya hilang tepat pada data yang paling perlu ditandai.
    #: `None` berarti berkasnya tidak menyatakan apa-apa, dan label jalurnya yang dipakai.
    sumber: str | None = None

    def __post_init__(self) -> None:
        """Tolak asal tanggal yang tidak dikenal **di sini**, bukan di lapisan SQLite.

        Pesan SQLite hanya menyebut nama constraint-nya, dan pemanggil tidak tahu baris mana yang
        salah. Nilai yang tidak dikenal juga bukan "belum diisi": ia tanda pemanggil salah
        menuliskan fakta, sehingga berhenti adalah perilaku yang benar (aturan keras 7).
        """
        if self.asal_tgl_publikasi not in ASAL_TGL_PUBLIKASI_SAH:
            raise GalatIngesti(
                f"{self.kode} periode {self.periode}: asal_tgl_publikasi "
                f"{self.asal_tgl_publikasi!r} tidak dikenal. Yang sah: "
                f"{', '.join(ASAL_TGL_PUBLIKASI_SAH)}"
            )


@dataclass(frozen=True)
class RasioBank:
    """Rasio bank (PRD 8.4, Q6). Tingkat dalam basis poin; `None` = tidak dilaporkan."""

    kode: str
    periode: date
    tgl_publikasi: date
    npl_kotor_bp: int | None = None
    car_bp: int | None = None
    bopo_bp: int | None = None
    nim_bp: int | None = None
    keterangan: str | None = None
    #: Label asal **per baris**, bila sumbernya menyatakannya (kolom `sumber` memang wajib di
    #: `rasio-bank.csv`). Sebelum K78 kolom itu divalidasi lalu dibuang, sehingga asal tiap
    #: publikasi bank tersimpan sebagai `impor berkas: <folder>`: pada dua bank provenance-nya
    #: sudah hilang, dan bila kelak diperluas ke 44 bank, 44 dokumen berbeda akan tampak berasal
    #: dari satu folder. `None` berarti pemanggil tidak menyatakan asalnya, dan label jalur
    #: (kumpulan) yang dipakai — sama seperti `fundamental` sejak K18.
    sumber: str | None = None


@dataclass(frozen=True)
class Kegagalan:
    """Satu emiten yang gagal diambil, beserta alasannya dan **jenisnya** (U18).

    `jenis` tidak pernah dikarang di sini: ia datang dari pengambil data, satu-satunya pihak yang
    melihat jawaban sumbernya. Bawaannya `sementara` — lihat catatan `JENIS_KEGAGALAN_SAH`.
    """

    kode: str
    alasan: str
    jenis: str = KEGAGALAN_SEMENTARA

    def __post_init__(self) -> None:
        if self.jenis not in JENIS_KEGAGALAN_SAH:
            raise GalatIngesti(
                f"jenis kegagalan {self.jenis!r} tidak dikenal untuk {self.kode}; "
                f"yang sah: {', '.join(JENIS_KEGAGALAN_SAH)}"
            )

    def baris(self) -> str:
        """Satu baris untuk laporan: jenisnya disebut lebih dulu supaya tidak terlewat."""
        return f"[{self.jenis}] {self.kode}: {self.alasan}"


@dataclass(frozen=True)
class KumpulanData:
    """Seluruh data satu kali pengambilan, apa pun jalur masuknya.

    `sumber` di sini adalah label asal data; tiap tabel memakainya sebagai kolom `sumber`
    (S2). `gagal` memuat kode yang gagal diambil **beserta alasannya** — daftar kosong berarti
    tidak ada yang gagal, bukan "tidak diketahui".
    """

    sumber: str
    emiten: tuple[Emiten, ...] = ()
    harga_harian: tuple[HargaHarian, ...] = ()
    harga_indeks: tuple[PenutupanIndeks, ...] = ()
    aksi_korporasi: tuple[AksiKorporasi, ...] = ()
    catatan_aksi_mutu: tuple[CatatanAksiMutu, ...] = ()
    sambungan_harga: tuple[SambunganHarga, ...] = ()
    kalender_bursa: tuple[HariBursa, ...] = ()
    notasi_khusus: tuple[NotasiKhusus, ...] = ()
    imbal_hasil_sun: tuple[ImbalHasilSUN, ...] = ()
    fundamental: tuple[Fundamental, ...] = ()
    rasio_bank: tuple[RasioBank, ...] = ()
    gagal: tuple[Kegagalan, ...] = ()
    catatan: tuple[str, ...] = ()

    def _jenis(self, jenis: str) -> tuple[Kegagalan, ...]:
        return tuple(satu for satu in self.gagal if satu.jenis == jenis)

    @property
    def gagal_permanen(self) -> tuple[Kegagalan, ...]:
        """Lubang yang diketahui: kode yang sumbernya sendiri nyatakan tidak punya data."""
        return self._jenis(KEGAGALAN_PERMANEN)

    @property
    def gagal_sementara(self) -> tuple[Kegagalan, ...]:
        """Kegagalan yang patut diulang dan dihitung terhadap ambang PRD 9.3."""
        return self._jenis(KEGAGALAN_SEMENTARA)

    def tambah(self, lain: KumpulanData) -> KumpulanData:
        """Gabungkan dua hasil pengambilan (mis. data sumber otomatis + berkas impor).

        Menolak sumber yang berbeda dengan sengaja: satu snapshot disimpan dengan **satu**
        label di kolom `sumber` setiap barisnya (S2), jadi menggabungkan dua label berbeda akan
        membuat asal sebagian baris salah. Kalau memang perlu menggabungkan, pemanggil harus
        menentukan label mana yang benar lebih dulu (lihat `pengatur._tanpa_emiten`).
        """
        if lain.sumber != self.sumber:
            raise GalatIngesti(
                f"tidak bisa menggabungkan data dari sumber berbeda: {self.sumber!r} + {lain.sumber!r}"
            )
        return KumpulanData(
            sumber=self.sumber,
            emiten=self.emiten + lain.emiten,
            harga_harian=self.harga_harian + lain.harga_harian,
            harga_indeks=self.harga_indeks + lain.harga_indeks,
            aksi_korporasi=self.aksi_korporasi + lain.aksi_korporasi,
            catatan_aksi_mutu=self.catatan_aksi_mutu + lain.catatan_aksi_mutu,
            sambungan_harga=self.sambungan_harga + lain.sambungan_harga,
            kalender_bursa=self.kalender_bursa + lain.kalender_bursa,
            notasi_khusus=self.notasi_khusus + lain.notasi_khusus,
            imbal_hasil_sun=self.imbal_hasil_sun + lain.imbal_hasil_sun,
            fundamental=self.fundamental + lain.fundamental,
            rasio_bank=self.rasio_bank + lain.rasio_bank,
            gagal=self.gagal + lain.gagal,
            catatan=self.catatan + lain.catatan,
        )


@dataclass
class HasilTulis:
    """Berapa baris yang benar-benar ditulis, berapa yang sudah ada dan identik."""

    baru: dict[str, int] = field(default_factory=dict)
    tetap: dict[str, int] = field(default_factory=dict)
    #: Revisi harga yang **hanya mengosongkan** penutupan yang sudah diketahui dari sumber yang
    #: sama — ditolak, bukan ditulis (T90): tabel → ["KODE YYYY-MM-DD", …].
    kosong_ditolak: dict[str, list[str]] = field(default_factory=dict)

    @property
    def total_kosong_ditolak(self) -> int:
        return sum(len(satu) for satu in self.kosong_ditolak.values())

    def ringkas_kosong_ditolak(self) -> str:
        """Kalimat peringatan; kosong bila tidak ada yang ditolak."""
        if not self.total_kosong_ditolak:
            return ""
        contoh = [satu for daftar in self.kosong_ditolak.values() for satu in daftar][:10]
        return (
            f"{self.total_kosong_ditolak} revisi berpenutupan kosong ditolak — sumber mengirim "
            "bar tanpa harga penutupan untuk tanggal yang nilainya sudah tersimpan dari sumber yang "
            f"sama, jadi nilai lama tetap dipakai ({', '.join(contoh)})"
        )

    def catat(self, tabel: str, *, baru: bool) -> None:
        keranjang = self.baru if baru else self.tetap
        keranjang[tabel] = keranjang.get(tabel, 0) + 1

    @property
    def total_baru(self) -> int:
        return sum(self.baru.values())

    @property
    def total_tetap(self) -> int:
        return sum(self.tetap.values())


# ---------------------------------------------------------------------------------------
# Konversi ketat: apa pun yang tidak terbaca menjadi None, bukan nol (aturan keras 1, T8)
# ---------------------------------------------------------------------------------------

#: Kata yang dipakai sumber untuk "tidak ada angka". Dikenali supaya tidak diterjemahkan
#: sebagai nilai.
_KOSONG = {"", "-", "--", "n/a", "na", "null", "none", "nan", "tidak ada"}

#: Batas atas penjaga salah ketik, bukan batas kebijakan.
_BATAS_UANG = 10**15
_BATAS_LEMBAR = 10**15


def _teks_mentah(nilai: object) -> str | None:
    """Angka asli apa adanya untuk kolom `*_mentah` (audit), tanpa membulatkannya."""
    if nilai is None:
        return None
    if isinstance(nilai, str):
        bersih = nilai.strip()
        return bersih or None
    return str(nilai)


def _desimal(nilai: object, di_mana: str) -> Decimal | None:
    """Ubah nilai sumber menjadi `Decimal`, atau None bila memang tidak ada angkanya."""
    if nilai is None:
        return None
    if isinstance(nilai, bool):
        raise GalatIngesti(f"{di_mana}: nilai boolean bukan angka ({nilai!r})")
    if isinstance(nilai, str) and nilai.strip().lower() in _KOSONG:
        return None
    try:
        angka = Decimal(str(nilai).strip())
    except (InvalidOperation, ValueError) as galat:
        raise GalatIngesti(f"{di_mana}: bukan angka yang bisa dibaca ({nilai!r})") from galat
    # NaN dan tak berhingga tidak bisa disimpan dan tidak boleh menjadi angka apa pun.
    if not angka.is_finite():
        return None
    return angka


def _ke_rupiah(nilai: object, di_mana: str) -> tuple[int | None, str | None]:
    """Harga rupiah: `INTEGER` + angka aslinya untuk audit (T8).

    Berpecahan **tidak** dibulatkan diam-diam: yang tersimpan berhitung adalah bagian
    bulatnya, dan nilai aslinya ikut tersimpan di kolom `*_mentah`, sehingga selisihnya bisa
    diaudit. Nilai negatif menjadi None (harga negatif tidak bermakna) — bukan 0.
    """
    angka = _desimal(nilai, di_mana)
    if angka is None:
        return None, None
    if angka < 0:
        return None, _teks_mentah(nilai)
    return int(angka // 1), _teks_mentah(nilai)


def _ke_rupiah_bertanda(nilai: object, di_mana: str) -> tuple[int | None, str | None]:
    """Rupiah yang **boleh negatif**: laba rugi, ekuitas negatif, arus kas operasi negatif.

    `_ke_rupiah` sengaja menolak negatif karena harga negatif memang tidak bermakna. Untuk
    laporan keuangan, menolaknya justru membuang keadaan yang nyata — dan menghilangkannya tanpa
    jejak berarti menyembunyikan perusahaan yang sedang rugi (aturan keras 7).
    """
    angka = _desimal(nilai, di_mana)
    if angka is None:
        return None, None
    # int() memotong ke arah nol; bagian pecahannya tetap bisa diaudit lewat `*_mentah` (T8).
    return int(angka), _teks_mentah(nilai)


def _ke_lembar(nilai: object, di_mana: str) -> tuple[int | None, str | None]:
    """Volume/lembar: `INTEGER` + angka aslinya. Sama alasannya dengan `_ke_rupiah`."""
    angka = _desimal(nilai, di_mana)
    if angka is None:
        return None, None
    if angka < 0:
        return None, _teks_mentah(nilai)
    return int(angka // 1), _teks_mentah(nilai)


def _ke_basis_poin(nilai: object, di_mana: str) -> int | None:
    """Persen → basis poin `INTEGER` (D-8), memakai `Decimal` agar 12,5% menjadi 1250 bp."""
    angka = _desimal(nilai, di_mana)
    if angka is None:
        return None
    bp = int(angka * 100)
    if bp < 0 or bp > 10000:
        raise GalatIngesti(f"{di_mana}: persen {angka} di luar 0–100")
    return bp


def _ke_tanggal(nilai: object, di_mana: str) -> date:
    """Tanggal dari `date`/`datetime` (pandas) atau teks ISO `YYYY-MM-DD`."""
    if isinstance(nilai, datetime):
        return nilai.date()
    if isinstance(nilai, date):
        return nilai
    if isinstance(nilai, str):
        teks = nilai.strip()
        if not teks:
            raise GalatIngesti(f"{di_mana}: tanggal kosong")
        try:
            return date.fromisoformat(teks[:10])
        except ValueError as galat:
            raise GalatIngesti(
                f"{di_mana}: tanggal {nilai!r} tidak dikenali; pakai bentuk YYYY-MM-DD"
            ) from galat
    raise GalatIngesti(f"{di_mana}: {nilai!r} bukan tanggal")


def _ke_teks(nilai: object) -> str | None:
    if nilai is None:
        return None
    teks = str(nilai).strip()
    return teks or None


# ---------------------------------------------------------------------------------------
# Waktu & sidik baris
# ---------------------------------------------------------------------------------------


def _waktu_iso(momen: datetime | None = None) -> str:
    """Waktu ISO-8601 dengan offset zona waktu (T12); format tampilan urusan lapisan atas."""
    return db.waktu_iso(momen)


def _sidik(*nilai: object) -> str:
    """Sidik isi baris.

    Dipakai untuk membedakan "baris ini sudah ada dan isinya sama" (tidak perlu ditulis lagi)
    dari "isinya berbeda" (perbaikan → tambah baris baru dengan `diketahui_pada` yang lebih
    baru, sesuai S1). Tanpa ini, menjalankan ulang ingesti yang sama akan menumpuk baris
    identik dan membuat "terkini" bergantung pada urutan penulisan, bukan isi.
    """
    bahan = "\x1f".join("" if satu is None else str(satu) for satu in nilai)
    return hashlib.sha256(bahan.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------
# Penulis baris: tambah bila isinya berbeda, diam bila sudah ada dan sama
# ---------------------------------------------------------------------------------------

#: Kolom yang dibandingkan untuk memutuskan "sudah ada dan sama". Kuncinya adalah kolom kunci
#: alami + `diketahui_pada`; sisanya adalah isi yang bisa diperbaiki lewat baris baru.
#:
#: Kolom `*_mentah` ikut di sini, dan itu bukan kelengkapan belaka: kolom itulah satu-satunya
#: tempat angka asli sumber disimpan (T8). Kalau ia tidak ikut ditulis, jejak audit yang
#: dijanjikan skema tidak pernah benar-benar ada — nilai berpecahan hilang tanpa bekas, dan
#: tidak ada cara memeriksa apakah pembulatan ke rupiah utuh mengubah sesuatu.
_ISI_PER_TABEL: Mapping[str, tuple[str, ...]] = {
    "harga_harian": (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "nilai",
        "asal_nilai",
        "open_mentah",
        "high_mentah",
        "low_mentah",
        "close_mentah",
        "volume_mentah",
        "nilai_mentah",
        "penyesuaian_sumber",
        "sumber",
    ),
    "harga_indeks": ("close", "close_mentah", "sumber"),
    "fundamental": (
        "tgl_publikasi",
        "asal_tgl_publikasi",
        "mata_uang",
        "satuan_uang",
        "pendapatan",
        "laba_induk",
        "ekuitas_induk",
        "ebit",
        "beban_bunga",
        "da",
        "utang_bunga",
        "kas",
        "cfo",
        "jumlah_saham",
        "dps",
        "pendapatan_mentah",
        "laba_induk_mentah",
        "ekuitas_induk_mentah",
        "sumber",
    ),
    "rasio_bank": (
        "tgl_publikasi",
        "npl_kotor_bp",
        "car_bp",
        "bopo_bp",
        "nim_bp",
        "keterangan",
        "sumber",
    ),
    "aksi_korporasi": (
        "rasio_lama",
        "rasio_baru",
        "harga_tebus",
        "dividen_per_saham",
        "tenggat",
        "keterangan",
        "sumber",
    ),
    "catatan_aksi_mutu": ("instrumen_aksi", "ringkasan_bukti", "sumber_url", "sumber"),
    "sambungan_harga": ("sumber_resmi", "aktif", "keterangan", "sumber"),
    "kalender_bursa": ("hari_bursa", "keterangan", "sumber"),
    "notasi_khusus": ("tanggal_selesai", "keterangan", "sumber"),
    "imbal_hasil_sun": ("imbal_hasil_bp", "imbal_hasil_mentah", "sumber"),
    "emiten": (
        "nama",
        "sektor_idx_ic",
        "sektor_sumber",
        "jenis",
        "papan",
        "status_notasi",
        "tanggal_notasi",
        "jumlah_saham",
        "free_float_bp",
        "sumber",
    ),
}


#: Tabel harga yang dilindungi dari revisi berpenutupan kosong (T90).
_TABEL_HARGA = frozenset({"harga_harian", "harga_indeks"})


def _tulis_baris(
    sambungan: sqlite3.Connection,
    tabel: str,
    baris: Mapping[str, object],
    kunci: Sequence[str],
    hasil: HasilTulis,
) -> None:
    """Tulis satu baris: tambah bila isinya baru, diam bila isinya sudah ada.

    **Kunci alami vs kunci tabel.** Perbandingan dilakukan atas kunci **tanpa**
    `diketahui_pada`, bukan atas kunci utama tabelnya. Alasannya penting dan pernah menjadi
    bug nyata: setiap kali ingesti berjalan, `diketahui_pada` bernilai jam yang berbeda,
    sehingga pencarian dengan kunci lengkap **tidak pernah** menemukan baris hasil jalan
    sebelumnya — dan menjalankan ingesti dua kali menumpuk dua salinan identik. Akibatnya
    "terkini" menjadi tidak bermakna (`(kode, tanggal)` punya dua revisi berisi hal yang sama)
    dan laporan mutu menghitung baris dua kali.

    Baris baru tetap ditambahkan bila isinya **berbeda**: itu perbaikan data, dan S1 menuntut
    perbaikan menambah baris baru alih-alih menimpa. `diketahui_pada` tetap ikut kunci utama
    basis data supaya revisi bisa hidup berdampingan.

    **Pembandingnya revisi terkini dari sumber yang sama**, bukan sembarang revisi (sesi 69).
    Dulu baris dianggap "sudah ada" bila sama dengan revisi **mana pun**, sehingga koreksi
    balik A → B → A hilang diam-diam dan lubang kosong lama (T90) tidak pernah tertutup oleh
    nilai yang dikirim ulang. Dibatasi ke sumber yang sama karena satu kunci bisa punya dua
    sumber dengan angka berbeda (yfinance dan Ringkasan Saham IDX): membandingkan dengan
    revisi terkini lintas sumber akan menambah revisi bolak-balik setiap kali salah satunya
    ditulis ulang.
    """
    isi = _ISI_PER_TABEL[tabel]
    kunci_alami = [kolom for kolom in kunci if kolom != "diketahui_pada"]
    syarat = " AND ".join(f"{kolom} = ?" for kolom in kunci_alami)
    terkini_sumber = sambungan.execute(
        f"SELECT {', '.join(isi)} FROM {tabel} WHERE {syarat} AND sumber = ?"
        " ORDER BY diketahui_pada DESC LIMIT 1",
        (*(baris[kolom] for kolom in kunci_alami), baris["sumber"]),
    ).fetchone()

    sidik_baru = _sidik(*(baris[kolom] for kolom in isi))
    if terkini_sumber is not None and _sidik(*terkini_sumber) == sidik_baru:
        hasil.catat(tabel, baru=False)
        return

    if tabel in _TABEL_HARGA and baris["close"] is None:
        # T90: revisi yang **mengosongkan** penutupan yang sudah diketahui bukan perbaikan data —
        # sumber (terukur: Yahoo, bar indeks hari berjalan pukul 02.24) mengirim bar sementara tanpa
        # angka. Menyimpannya menjadikan lubang sebagai "terkini" dan menyembunyikan nilai sah.
        # Ditolak hanya bila revisi terkini dari sumber yang **sama** sudah bernilai; lubang pada
        # tanggal yang belum pernah bernilai tetap tersimpan (aturan keras 2). Penolakan dicatat
        # dan dilaporkan pemanggil (aturan keras 7), bukan dibuang diam-diam.
        terkini = sambungan.execute(
            f"SELECT close FROM {tabel} WHERE {syarat} AND sumber = ?"
            " ORDER BY diketahui_pada DESC LIMIT 1",
            (*(baris[kolom] for kolom in kunci_alami), baris["sumber"]),
        ).fetchone()
        if terkini is not None and terkini[0] is not None:
            label = baris.get("kode") or baris.get("indeks")
            hasil.kosong_ditolak.setdefault(tabel, []).append(f"{label} {baris['tanggal']}")
            return

    kolom = ", ".join([*kunci, *isi])
    tempat = ", ".join("?" for _ in [*kunci, *isi])
    # Sebelum menulis, periksa tabrakan kunci utama **secara eksplisit**. Ini penting: jalur
    # alternatifnya adalah `INSERT OR IGNORE`, dan itu berbahaya di sini — `OR IGNORE` juga
    # menelan kegagalan CHECK, sehingga baris yang melanggar aturan (mis. harga negatif) hilang
    # tanpa suara. Aturan keras 7 menuntut sebaliknya: gagal itu berisik.
    ada_persis = sambungan.execute(
        f"SELECT {', '.join(isi)} FROM {tabel} WHERE " + " AND ".join(f"{kolom} = ?" for kolom in kunci),
        tuple(baris[kolom] for kolom in kunci),
    ).fetchone()
    if ada_persis is not None:
        # Tabrakan kunci utama yang isinya **berbeda** tidak boleh lewat begitu saja.
        # Satu jalan ingesti memakai satu `diketahui_pada` (saat data diketahui), sehingga dua
        # revisi berbeda untuk kunci yang sama tidak bisa hidup berdampingan di dalamnya.
        # Sebelumnya baris kedua dihitung "sudah ada dan sama" lalu dibuang — padahal isinya
        # berbeda. Itu persis jenis kehilangan data yang paling sulit ditelusuri: berkasnya
        # berisi restatement (cara yang justru didorong S1), tabelnya hanya memuat baris
        # pertama, dan lognya menyatakan sukses (aturan keras 7).
        if _sidik(*ada_persis) != sidik_baru:
            raise GalatIngesti(
                f"{tabel}: dua baris berbeda untuk kunci yang sama "
                f"({', '.join(f'{kolom}={baris[kolom]!r}' for kolom in kunci)}) dalam satu jalan. "
                "Satu jalan ingesti memakai satu `diketahui_pada`, jadi revisi kedua tidak bisa "
                "disimpan berdampingan. Dua sebab yang mungkin, dan bedanya penting: (a) jalan "
                "sebelumnya berlangsung pada **detik yang sama**, sehingga kunci waktunya jatuh "
                "persis sama — jalankan ulang impornya setelah jeda sesaat, dan perbaikannya "
                "adalah menunggu, bukan menyunting berkas; (b) kedua baris memang ada di satu "
                "berkas — pisahkan menjadi dua berkas, sebab perbaikan data menambah baris baru "
                "dengan waktu diketahui yang lebih baru (PRD 7.2, S1). Berkas impor yang memuat "
                "dua baris berkunci sama sudah ditolak pembacanya sebelum sampai ke sini, jadi "
                "(b) hanya mungkin lewat jalur lain."
            )
        hasil.catat(tabel, baru=False)
        return

    sambungan.execute(
        f"INSERT INTO {tabel} ({kolom}) VALUES ({tempat})",
        tuple(baris[kolom] for kolom in [*kunci, *isi]),
    )
    hasil.catat(tabel, baru=True)


# ---------------------------------------------------------------------------------------
# Penyusun baris per tabel
# ---------------------------------------------------------------------------------------


def _baris_harga(bar: HargaHarian, sumber: str, diketahui_pada: str) -> dict[str, object]:
    nilai = bar.nilai
    nilai_mentah = bar.nilai_mentah
    asal_nilai: str | None
    if nilai is not None:
        asal_nilai = "impor"
    elif bar.close is not None and bar.volume is not None:
        nilai = bar.close * bar.volume
        asal_nilai = "hitung"  # U6: close x volume
    else:
        nilai, asal_nilai = None, None

    return {
        "kode": bar.kode,
        "tanggal": bar.tanggal.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "nilai": nilai,
        "asal_nilai": asal_nilai,
        "open_mentah": bar.open_mentah,
        "high_mentah": bar.high_mentah,
        "low_mentah": bar.low_mentah,
        "close_mentah": bar.close_mentah,
        "volume_mentah": bar.volume_mentah,
        "nilai_mentah": nilai_mentah,
        "penyesuaian_sumber": bar.penyesuaian_sumber,
        # Sumber per baris menang atas label kumpulan: berkas impor boleh memuat beberapa
        # sumber sekaligus (itulah bahan cek sumber kedua), dan menimpanya dengan satu label
        # folder akan menghapus satu-satunya bukti asal yang membuat perbandingan mungkin.
        "sumber": bar.sumber or sumber,
        "diketahui_pada": diketahui_pada,
    }


def _baris_fundamental(satu: Fundamental, sumber: str, diketahui_pada: str) -> dict[str, object]:
    """Susun baris `fundamental`; nilai uang sudah rupiah utuh, `satuan_uang` jadi jejaknya."""
    return {
        "kode": satu.kode,
        "periode": satu.periode.isoformat(),
        "jenis_laporan": satu.jenis_laporan,
        "tgl_publikasi": satu.tgl_publikasi.isoformat(),
        "asal_tgl_publikasi": satu.asal_tgl_publikasi,
        "mata_uang": satu.mata_uang,
        "satuan_uang": satu.satuan_uang,
        "pendapatan": satu.pendapatan,
        "laba_induk": satu.laba_induk,
        "ekuitas_induk": satu.ekuitas_induk,
        "ebit": satu.ebit,
        "beban_bunga": satu.beban_bunga,
        "da": satu.da,
        "utang_bunga": satu.utang_bunga,
        "kas": satu.kas,
        "cfo": satu.cfo,
        "jumlah_saham": satu.jumlah_saham,
        "dps": satu.dps,
        "pendapatan_mentah": satu.pendapatan_mentah,
        "laba_induk_mentah": satu.laba_induk_mentah,
        "ekuitas_induk_mentah": satu.ekuitas_induk_mentah,
        # Label per baris menang atas label jalur impor: berkas yang menyatakan asalnya (mis.
        # "yfinance ... tidak resmi") tidak boleh kehilangan keterangan itu saat masuk basis data.
        "sumber": satu.sumber or sumber,
        "diketahui_pada": diketahui_pada,
    }


def _baris_rasio_bank(satu: RasioBank, sumber: str, diketahui_pada: str) -> dict[str, object]:
    return {
        "kode": satu.kode,
        "periode": satu.periode.isoformat(),
        "tgl_publikasi": satu.tgl_publikasi.isoformat(),
        "npl_kotor_bp": satu.npl_kotor_bp,
        "car_bp": satu.car_bp,
        "bopo_bp": satu.bopo_bp,
        "nim_bp": satu.nim_bp,
        "keterangan": satu.keterangan,
        # Label per baris menang atas label jalur impor (K78): satu berkas boleh memuat beberapa
        # bank yang publikasinya berbeda, dan menimpanya dengan satu label folder menghapus
        # satu-satunya jejak asal yang membuat angkanya bisa ditelusuri.
        "sumber": satu.sumber or sumber,
        "diketahui_pada": diketahui_pada,
    }


#: Kolom harga pada `harga_harian` yang tidak boleh negatif. Daftar ini mengikuti CHECK di
#: `skema.py`; tujuannya membuat pelanggarannya berhenti di sini dengan pesan yang menyebut
#: emitennya, bukan di lapisan SQLite yang hanya menyebut nama kolom.
_KOLOM_HARGA = ("open", "high", "low", "close", "nilai", "volume")

#: Kolom harga pada `harga_indeks`.
_KOLOM_INDEKS = ("close",)


def _periksa_baris_harga(baris: Mapping[str, object], di_mana: str) -> None:
    """Tolak baris yang melanggar aturan tabel **sebelum** menyentuh basis data.

    Ada dua alasan pemeriksaan ini berada di sini dan bukan hanya di pembentuk baris:

    1. `HargaHarian` adalah kontrak publik; pengambil data baru (atau test) bisa membentuknya
       langsung tanpa melewati konversi `_ke_rupiah`. Tanpa pemeriksaan di titik tulis, nilai
       yang tidak sah baru ketahuan sebagai galat CHECK SQLite — pesannya menyebut nama kolom,
       bukan emiten dan tanggalnya.
    2. Jalur impor dan jalur pengambilan otomatis harus tunduk pada aturan yang sama; menaruh
       pemeriksaan di masing-masing jalur berarti aturannya bisa berbeda di antara keduanya.
    """
    for kolom in _KOLOM_HARGA:
        nilai = baris.get(kolom)
        if isinstance(nilai, int) and nilai < 0:
            raise GalatIngesti(
                f"{di_mana}: {kolom} = {nilai} negatif; nilai negatif tidak bermakna dan "
                "harus menjadi None (bukan angka negatif) supaya terlihat di laporan mutu"
            )
    penanda = baris.get("penyesuaian_sumber")
    if penanda is not None and penanda not in PENANDA_PENYESUAIAN_SAH:
        # Pesan yang menyebut emitennya, bukan "CHECK constraint failed" (K8/C10).
        raise GalatIngesti(
            f"{di_mana}: penyesuaian_sumber = {penanda!r} tidak dikenal; "
            f"yang sah: {', '.join(PENANDA_PENYESUAIAN_SAH)}, atau kosong bila belum dinyatakan"
        )
    _periksa_batas(baris, "harga_harian", di_mana)
    _cek_high_low(baris, di_mana)


def _periksa_batas(baris: Mapping[str, object], tabel: str, di_mana: str) -> None:
    """Penjaga salah ketik yang tidak ditangkap CHECK (mis. 1e15 dari berkas rusak)."""
    for kolom in ("open", "high", "low", "close", "nilai"):
        angka = baris.get(kolom)
        if isinstance(angka, int) and abs(angka) > _BATAS_UANG:
            raise GalatIngesti(f"{di_mana}: {tabel}.{kolom} = {angka} di luar batas yang masuk akal")
    angka = baris.get("volume")
    if isinstance(angka, int) and abs(angka) > _BATAS_LEMBAR:
        raise GalatIngesti(f"{di_mana}: {tabel}.volume = {angka} di luar batas yang masuk akal")


def _cek_high_low(baris: Mapping[str, object], di_mana: str) -> None:
    tinggi, rendah = baris.get("high"), baris.get("low")
    if isinstance(tinggi, int) and isinstance(rendah, int) and tinggi < rendah:
        raise GalatIngesti(
            f"{di_mana}: high ({tinggi}) lebih kecil dari low ({rendah}); "
            "baris harga seperti ini menandakan data sumber rusak"
        )


# ---------------------------------------------------------------------------------------
# Penyimpanan: satu transaksi untuk semuanya (A6, AC-19)
# ---------------------------------------------------------------------------------------

#: Urutan tabel saat menulis, supaya pesan laporan selalu sama.
URUTAN_TABEL = (
    "emiten",
    "harga_harian",
    "harga_indeks",
    "aksi_korporasi",
    "catatan_aksi_mutu",
    "sambungan_harga",
    "kalender_bursa",
    "notasi_khusus",
    "imbal_hasil_sun",
    "fundamental",
    "rasio_bank",
)


@dataclass(frozen=True)
class HasilSimpan:
    """Apa yang terjadi pada satu penulisan snapshot."""

    id_snapshot: int
    diketahui_pada: str
    tanggal_data: str
    jumlah_emiten: int
    jumlah_gagal: int
    baris: HasilTulis


def _id_snapshot_baru(sambungan: sqlite3.Connection) -> int:
    """Nomor snapshot berikutnya.

    Dihitung dari `MAX`, bukan dari `AUTOINCREMENT`: baris snapshot tidak pernah dihapus
    (trigger append-only), jadi tidak ada nomor yang bisa dipakai ulang.
    """
    return int(sambungan.execute("SELECT COALESCE(MAX(id_snapshot), 0) + 1 FROM snapshot").fetchone()[0])


def simpan(
    sambungan: sqlite3.Connection,
    kumpulan: KumpulanData,
    *,
    tanggal_data: date,
    momen: datetime | None = None,
    proses: str = PROSES_REFRESH,
    catatan: str | None = None,
    tambahan: KumpulanData | None = None,
) -> HasilSimpan:
    """Tulis satu snapshot secara atomik: data + baris snapshot + log jalan.

    `tambahan` adalah data dari sumber **lain** yang ikut snapshot yang sama — pada refresh,
    isi berkas di folder konfigurasi (notasi IDX, kalender KSEI, SUN PHEI). Barisnya ditulis
    dengan label `tambahan.sumber`, bukan label `kumpulan` (aturan keras 3): sebelum sesi 56
    keduanya digabung di bawah label pengambil otomatis, sehingga notasi IDX tersimpan sebagai
    "yfinance/Yahoo Finance" dan ditulis ulang setiap refresh.

    `momen` adalah saat data dianggap diketahui (`batas_diketahui`/`jam_ambil`/`diketahui_pada`).
    Bisa diisi tetap oleh test supaya hasilnya bisa dibandingkan; bila `None`, diambil dari jam
    sekarang.

    Semua penulisan berada di **satu** `db.tulis()`: kalau salah satu baris ditolak CHECK atau
    trigger, tidak ada satu pun yang tersisa — termasuk barisnya `snapshot` (A6).
    """
    waktu = _waktu_iso(momen)
    tanggal_teks = tanggal_data.isoformat()
    baris = HasilTulis()

    with db.tulis(sambungan) as koneksi:
        _tulis_kumpulan(koneksi, kumpulan, waktu, baris)
        if tambahan is not None:
            _tulis_kumpulan(koneksi, tambahan, waktu, baris)

        jumlah_emiten = _jumlah_emiten(koneksi, kumpulan)
        id_snapshot = _id_snapshot_baru(koneksi)
        koneksi.execute(
            "INSERT INTO snapshot (id_snapshot, tanggal_data, batas_diketahui, jam_ambil,"
            " jumlah_emiten, jumlah_gagal, versi_skema, versi_aplikasi, catatan)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id_snapshot,
                tanggal_teks,
                waktu,
                waktu,
                jumlah_emiten,
                len(kumpulan.gagal),
                _versi_skema(koneksi),
                __version__,
                catatan,
            ),
        )
        koneksi.execute(
            "INSERT INTO log_jalan (waktu, proses, hasil, pesan, id_snapshot) VALUES (?, ?, ?, ?, ?)",
            (
                waktu,
                proses,
                "sukses",
                f"snapshot {id_snapshot}: {baris.total_baru} baris baru, "
                f"{baris.total_tetap} baris sudah ada dan sama, {len(kumpulan.gagal)} emiten gagal"
                # U18: jumlahnya saja tidak cukup — "tidak diperdagangkan lagi" dan "gagal
                # sementara" menuntut tindakan yang berbeda, dan log adalah tempat mencarinya
                # setelah layar sudah berganti.
                + (
                    f" ({len(kumpulan.gagal_permanen)} permanen, {len(kumpulan.gagal_sementara)} sementara)"
                    if kumpulan.gagal
                    else ""
                )
                + (f"; {baris.ringkas_kosong_ditolak()}" if baris.total_kosong_ditolak else ""),
                id_snapshot,
            ),
        )

    return HasilSimpan(
        id_snapshot=id_snapshot,
        diketahui_pada=waktu,
        tanggal_data=tanggal_teks,
        jumlah_emiten=jumlah_emiten,
        jumlah_gagal=len(kumpulan.gagal),
        baris=baris,
    )


def _tulis_kumpulan(
    koneksi: sqlite3.Connection, kumpulan: KumpulanData, waktu: str, baris: HasilTulis
) -> None:
    """Tulis seluruh tabel data satu kumpulan dengan label `kumpulan.sumber` (kecuali baris yang
    membawa `sumber` sendiri). Dipanggil di dalam transaksi `simpan`."""
    for satu in kumpulan.emiten:
        # `dicatat_pada` adalah tanggal provenance di CSV, bukan waktu aplikasi
        # mengetahui baris ini. Gunakan waktu jalan impor untuk `diketahui_pada` agar
        # revisi berbeda yang dicatat pada tanggal sumber yang sama tetap dapat hidup
        # berdampingan (PRD 7.2, aturan append-only). Tanggal sumber tetap ada di CSV dan
        # keterangannya di `sumber`.
        _tulis_baris(
            koneksi,
            "emiten",
            {
                "kode": satu.kode,
                "nama": satu.nama,
                "sektor_idx_ic": satu.sektor_idx_ic,
                "sektor_sumber": satu.sektor_sumber,
                "jenis": satu.jenis,
                "papan": satu.papan,
                "status_notasi": satu.status_notasi,
                "tanggal_notasi": (
                    satu.tanggal_notasi.isoformat() if satu.tanggal_notasi else None
                ),
                "jumlah_saham": satu.jumlah_saham,
                "free_float_bp": satu.free_float_bp,
                "sumber": satu.sumber or kumpulan.sumber,
                "diketahui_pada": waktu,
            },
            ("kode", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.harga_harian:
        isi = _baris_harga(satu, kumpulan.sumber, waktu)
        di_mana = f"{satu.kode} {satu.tanggal}"
        _periksa_baris_harga(isi, di_mana)
        _tulis_baris(koneksi, "harga_harian", isi, ("kode", "tanggal", "diketahui_pada"), baris)

    for satu in kumpulan.harga_indeks:
        _tulis_baris(
            koneksi,
            "harga_indeks",
            {
                "indeks": satu.indeks,
                "tanggal": satu.tanggal.isoformat(),
                "close": satu.close,
                "close_mentah": satu.close_mentah,
                "sumber": kumpulan.sumber,
                "diketahui_pada": waktu,
            },
            ("indeks", "tanggal", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.aksi_korporasi:
        _tulis_baris(
            koneksi,
            "aksi_korporasi",
            {
                "kode": satu.kode,
                "tanggal": satu.tanggal.isoformat(),
                "jenis": satu.jenis,
                "rasio_lama": satu.rasio_lama,
                "rasio_baru": satu.rasio_baru,
                "harga_tebus": satu.harga_tebus,
                "dividen_per_saham": satu.dividen_per_saham,
                "tenggat": satu.tenggat,
                "keterangan": satu.keterangan,
                "sumber": satu.sumber or kumpulan.sumber,
                "diketahui_pada": waktu,
            },
            ("kode", "tanggal", "jenis", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.catatan_aksi_mutu:
        _tulis_baris(
            koneksi,
            "catatan_aksi_mutu",
            {
                "kode": satu.kode,
                "tanggal_efektif": satu.tanggal_efektif.isoformat(),
                "instrumen_aksi": satu.instrumen_aksi,
                "ringkasan_bukti": satu.ringkasan_bukti,
                "sumber_url": satu.sumber_url,
                "sumber": satu.sumber,
                "diketahui_pada": waktu,
            },
            ("kode", "tanggal_efektif", "instrumen_aksi", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.sambungan_harga:
        _tulis_baris(
            koneksi,
            "sambungan_harga",
            {
                "berlaku_sejak": satu.berlaku_sejak.isoformat(),
                "sumber_resmi": satu.sumber_resmi,
                "aktif": 1 if satu.aktif else 0,
                "keterangan": satu.keterangan,
                "sumber": satu.sumber,
                "diketahui_pada": waktu,
            },
            ("berlaku_sejak", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.kalender_bursa:
        _tulis_baris(
            koneksi,
            "kalender_bursa",
            {
                "tanggal": satu.tanggal.isoformat(),
                "hari_bursa": 1 if satu.hari_bursa else 0,
                "keterangan": satu.keterangan,
                "sumber": satu.sumber or kumpulan.sumber,
                "diketahui_pada": waktu,
            },
            ("tanggal", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.notasi_khusus:
        _tulis_baris(
            koneksi,
            "notasi_khusus",
            {
                "kode": satu.kode,
                "jenis": satu.jenis,
                "tanggal_mulai": satu.tanggal_mulai.isoformat(),
                "tanggal_selesai": satu.tanggal_selesai.isoformat() if satu.tanggal_selesai else None,
                "keterangan": satu.keterangan,
                "sumber": kumpulan.sumber,
                "diketahui_pada": waktu,
            },
            ("kode", "jenis", "tanggal_mulai", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.imbal_hasil_sun:
        _tulis_baris(
            koneksi,
            "imbal_hasil_sun",
            {
                "tanggal": satu.tanggal.isoformat(),
                "tenor_tahun": satu.tenor_tahun,
                "imbal_hasil_bp": satu.imbal_hasil_bp,
                "imbal_hasil_mentah": satu.imbal_hasil_mentah,
                "sumber": kumpulan.sumber,
                "diketahui_pada": waktu,
            },
            ("tanggal", "tenor_tahun", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.fundamental:
        _tulis_baris(
            koneksi,
            "fundamental",
            _baris_fundamental(satu, kumpulan.sumber, waktu),
            ("kode", "periode", "jenis_laporan", "diketahui_pada"),
            baris,
        )

    for satu in kumpulan.rasio_bank:
        _tulis_baris(
            koneksi,
            "rasio_bank",
            _baris_rasio_bank(satu, kumpulan.sumber, waktu),
            ("kode", "periode", "diketahui_pada"),
            baris,
        )


def _jumlah_emiten(sambungan: sqlite3.Connection, kumpulan: KumpulanData) -> int:
    """Jumlah emiten yang benar-benar punya data di basis data (bukan jumlah yang diminta).

    Sengaja dihitung dari basis data: emiten yang gagal diambil tidak boleh ikut terhitung,
    dan emiten yang sudah ada dari run sebelumnya tetap terhitung pada snapshot ini.
    """
    return int(sambungan.execute("SELECT COUNT(*) FROM v_emiten_terkini").fetchone()[0])


def _versi_skema(sambungan: sqlite3.Connection) -> int:
    return db.versi_terpasang(sambungan)


def catat_kegagalan(
    sambungan: sqlite3.Connection,
    *,
    proses: str,
    pesan: str,
    momen: datetime | None = None,
) -> None:
    """Catat kegagalan ke `log_jalan` di transaksi tersendiri (AC-9, aturan keras 7).

    Ada di luar `simpan()` dengan sengaja: ketika `simpan()` dibatalkan, transaksinya sudah
    ditutup, jadi jejaknya harus ditulis terpisah. Kegagalan menulis jejak **tidak** ditelan,
    tetapi juga tidak boleh menutupi galat aslinya — karena itu pemanggilnya yang memutuskan.
    """
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO log_jalan (waktu, proses, hasil, pesan, id_snapshot) VALUES (?, ?, ?, ?, ?)",
            (_waktu_iso(momen), proses, "gagal", pesan, None),
        )


def ringkas_kegagalan(gagal: Sequence[Kegagalan], batas: int = 10) -> tuple[str, ...]:
    """Kalimat laporan untuk kegagalan, dipisah menurut jenisnya (U18).

    Dipisah dengan sengaja: "kode tidak diperdagangkan lagi" dan "pengambilan gagal, ulangi" adalah
    dua keadaan yang menuntut tindakan berbeda, dan menggabungkannya membuat keduanya sama-sama
    tidak terbaca. Daftar kosong menghasilkan kalimat kosong juga — bukan "0 gagal" yang menyamar
    sebagai laporan.
    """
    bagian: list[str] = []
    for jenis, awalan in (
        (KEGAGALAN_PERMANEN, "tidak diperdagangkan lagi (lubang diketahui)"),
        (KEGAGALAN_SEMENTARA, "gagal sementara, patut diulang"),
    ):
        kode = [satu.kode for satu in gagal if satu.jenis == jenis]
        if not kode:
            continue
        tampil = ", ".join(kode[:batas]) + (" ..." if len(kode) > batas else "")
        # Akibatnya disebut di sini juga, bukan hanya di laporan mutu: pembaca `--refresh`
        # melihat kalimat ini lebih dulu, dan "tidak ikut diperingkat" itulah yang menjelaskan
        # mengapa jumlah emiten di layar lebih kecil daripada jumlah di `emiten.csv`.
        bagian.append(f"{len(kode)} emiten {awalan}, tidak ikut diperingkat: {tampil}")
    return tuple(bagian)


def periksa_ambang_gagal(
    gagal: Sequence[Kegagalan],
    diminta: int,
    *,
    ambang_persen: int = 5,
    emiten_kritis: Iterable[str] | None = None,
) -> None:
    """Tolak penerbitan snapshot bila ambang kegagalan terlewati (PRD 9.3), U18.

    Tiga syarat, dan bedanya menentukan:

    1. Ada emiten dari daftar kritis (50 emiten ber-ADTV20 tertinggi) yang gagal — **jenis apa
       pun**. Kegagalan permanen pun tetap menahan snapshot: kehilangan satu emiten teratas tanpa
       disadari lebih berbahaya daripada snapshot yang tidak terbit (aturan keras 7, AC-1).
    2. Lebih dari `ambang_persen` emiten gagal **sementara**. Kegagalan permanen tidak dihitung di
       sini: ia tidak akan pernah berhasil bila diulang, sehingga menghitungnya membuat gerbang
       menolak selamanya — dan gerbang yang selalu menolak berhenti memberi informasi (U18).
    3. Kegagalan permanen tetap **dilaporkan** lewat `ringkas_kegagalan`, bukan dianggap lulus.

    Daftar kritis yang `None` berarti syarat pertama belum dapat diperiksa — dilaporkan sebagai
    belum dapat diperiksa oleh pemanggil, bukan dianggap lulus diam-diam.
    """
    if diminta <= 0:
        raise GalatIngesti("tidak ada emiten yang diminta; tidak ada yang bisa diambil")
    if not gagal:
        return

    if emiten_kritis is not None:
        kritis = set(emiten_kritis)
        tertabrak = [satu for satu in gagal if satu.kode in kritis]
        if tertabrak:
            rincian = ", ".join(f"{satu.kode} ({satu.jenis})" for satu in sorted(tertabrak, key=lambda s: s.kode)[:10])
            raise IngestiDibatalkan(
                f"{len(tertabrak)} emiten ber-ADTV20 tertinggi gagal diambil ({rincian}); "
                "snapshot tidak diterbitkan (PRD 9.3)"
            )

    sementara = [satu for satu in gagal if satu.jenis == KEGAGALAN_SEMENTARA]
    if not sementara:
        return

    persen = len(sementara) / diminta * 100
    if persen > ambang_persen:
        permanen = len(gagal) - len(sementara)
        tambahan = (
            f" {permanen} kegagalan permanen tidak ikut dihitung (kode itu tidak diperdagangkan lagi, U18)."
            if permanen
            else ""
        )
        raise IngestiDibatalkan(
            f"{len(sementara)} dari {diminta} emiten gagal diambil sementara ({persen:.1f}% > "
            f"{ambang_persen}%); snapshot tidak diterbitkan supaya layar tetap memakai snapshot "
            f"sebelumnya (PRD 9.3, AC-8).{tambahan}"
        )
