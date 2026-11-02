"""Pengambil data dari yfinance — sumber **tidak resmi** (P2/Q8, PRD 7.1, 7.2).

Berkas ini sengaja dipisahkan dari `ingesti.py`: hanya di sini yfinance dikenal. Akibatnya
seluruh aturan ingesti bisa diuji tanpa jaringan, dan mengganti sumber data nanti (sumber
resmi berlisensi, PRD Q8) berarti menulis satu adaptor baru — bukan menyentuh aturan datanya.

Empat hal yang dijaga berkas ini:

1. **Label "tidak resmi" tidak bisa hilang.** Setiap baris yang keluar dari sini membawa
   `sumber = SUMBER_YFINANCE`; labelnya melekat pada data, bukan pada log yang bisa terlewat.
2. **Tidak ada pengisian angka diam-diam.** Bar tanpa harga penutupan menjadi `close = None`
   (lihat `ingesti.py`), dan emiten yang gagal diambil masuk `gagal` **beserta alasannya**.
   Sejak U18 alasannya juga membawa **jenisnya** (`permanen`/`sementara`), dan jenis itu
   ditentukan dari jawaban sumbernya — bukan dari tebakan: galat bertipe dimunculkan lebih dulu
   (`_galat_sumber_naik`), lalu hanya alasan yang benar-benar dinyatakan sumber yang dihitung
   permanen (`_klasifikasi_galat`).
3. **Hanya data EOD.** Seluruh permintaan memakai `interval="1d"` (PRD 4.2, 7.2).
4. **Batas laju penyedia dihormati.** Ada jeda antar permintaan dan ulang otomatis dengan
   jeda bertambah; jumlah percobaan dan jedanya bisa diatur, tidak dikarang di dalam kode
   sebagai konstanta tersembunyi.

Catatan yang perlu diketahui pengguna, bukan disembunyikan: yfinance membatasi laju
permintaan, dan terlalu sering dipanggil bisa membuat Yahoo menolak sementara. Karena itu
ingesti berjalan berurutan dengan jeda, bukan paralel.
"""

from __future__ import annotations

import contextlib
import csv
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from mejasaham import berkas
from mejasaham.ingesti import (
    KEGAGALAN_PERMANEN,
    KEGAGALAN_SEMENTARA,
    PENYESUAIAN_SPLIT,
    SUMBER_YFINANCE,
    AksiKorporasi,
    Emiten,
    Fundamental,
    GalatIngesti,
    HargaHarian,
    Kegagalan,
    KumpulanData,
    PenutupanIndeks,
    _ke_lembar,
    _ke_rupiah,
)

#: Indeks yang diambil. Kunci = nama yang dipakai di basis data (`harga_indeks.indeks`),
#: nilai = kode ticker di Yahoo. Nama di basis data sengaja memakai nama yang dikenal di
#: Indonesia, bukan kode Yahoo, supaya isi tabel tidak bergantung pada penyedia.
INDEKS: dict[str, str] = {
    "IHSG": "^JKSE",
    "LQ45": "^JKLQ45",
}

#: Rentang bawaan: 5 tahun, sesuai kriteria keluar Tahap 0 (PRD 16).
PERIODE_BAWAAN = "5y"

#: Jeda antar permintaan (detik). Nilai awal konservatif; bisa diubah lewat argumen.
JEDA_BAWAAN = 0.4

#: Jumlah percobaan ulang per emiten beserta jeda bertambahnya (detik).
PERCOBAAN_BAWAAN = 3
JEDA_ULANG = (2.0, 5.0, 10.0)


class GalatPengambilan(GalatIngesti):
    """Satu kode gagal diambil, **beserta jenis kegagalannya** (U18).

    `jenis` adalah `KEGAGALAN_PERMANEN` atau `KEGAGALAN_SEMENTARA`, dan ia ditentukan di sini
    karena hanya berkas ini yang melihat jawaban sumbernya. Pemanggil (`ingesti.periksa_ambang_gagal`)
    memakainya untuk memutuskan apakah kegagalan itu menahan snapshot atau hanya dilaporkan.
    """

    def __init__(self, pesan: str, *, jenis: str = KEGAGALAN_SEMENTARA) -> None:
        super().__init__(pesan)
        self.jenis = jenis


@contextlib.contextmanager
def _galat_sumber_naik() -> Iterator[None]:
    """Paksa yfinance **memunculkan** galatnya, bukan mengembalikan tabel kosong (U18).

    Inilah yang membuat pemisahan gagal permanen dari gagal sementara mungkin dilakukan sama
    sekali. Bawaan yfinance 1.7.0 (`config.debug.hide_exceptions = True`) menelan galatnya,
    mencatatnya ke log, lalu mengembalikan tabel kosong — sehingga dua keadaan yang sangat
    berbeda ("simbol ini tidak ada" dan "koneksi sedang dibatasi") tiba di aplikasi ini sebagai
    satu gejala yang sama: nol baris.

    Kalau versi yfinance yang terpasang tidak punya tombol itu, fungsinya tidak memaksa apa pun
    dan **tidak** menebak: seluruh kegagalan yang tidak dapat dipastikan jenisnya akan berakhir
    sebagai `KEGAGALAN_SEMENTARA` — yang menahan snapshot, bukan meloloskannya (aturan keras 7).

    Setelannya dipulihkan di `finally`: ia milik pustaka, bukan milik aplikasi ini, dan ingesti
    berjalan berurutan sehingga tidak ada proses lain yang perlu melihatnya berubah.
    """
    _pd, yf = _panda_tersedia()
    debug = getattr(getattr(yf, "config", None), "debug", None)
    if debug is None or not hasattr(debug, "hide_exceptions"):
        yield
        return

    sebelumnya = debug.hide_exceptions
    debug.hide_exceptions = False
    try:
        yield
    finally:
        debug.hide_exceptions = sebelumnya


def _klasifikasi_galat(galat: BaseException) -> tuple[str, str]:
    """Terjemahkan galat sumber menjadi (jenis, alasan) — U18.

    Aturannya satu dan sengaja sempit: **permanen hanya bila sumber menyatakan sendiri** bahwa
    kode itu tidak punya data. yfinance 1.7.0 meneruskan alasan Yahoo apa adanya lewat
    `YFPricesMissingError.yahoo_reason` (mis. "No data found, symbol may be delisted"); bila
    atribut itu kosong, yang tersisa hanyalah dugaan pustakanya ("possibly delisted; no price
    data found") — dan **dugaan tidak cukup** untuk meloloskan snapshot.

    Sisanya sementara: `YFRateLimitError`, waktu habis, galat jaringan, dan apa pun yang tidak
    dikenali. Kegagalan yang tidak dapat dipastikan jenisnya memang harus menahan snapshot;
    membalik bawaannya akan membuat snapshot terbit dengan data yang bolong tanpa ada yang tahu.
    """
    try:
        from yfinance.exceptions import YFPricesMissingError  # noqa: PLC0415 - lihat _panda_tersedia
    except ImportError:
        return KEGAGALAN_SEMENTARA, f"{type(galat).__name__}: {galat}".strip()

    if isinstance(galat, YFPricesMissingError):
        alasan_yahoo = getattr(galat, "yahoo_reason", None)
        if alasan_yahoo:
            return KEGAGALAN_PERMANEN, f"sumber menyatakan tidak ada data: {alasan_yahoo}"
    return KEGAGALAN_SEMENTARA, f"{type(galat).__name__}: {galat}".strip()


@dataclass(frozen=True)
class Kemajuan:
    """Laporan kemajuan satu emiten, supaya ingesti panjang tidak terlihat menggantung."""

    nomor: int
    dari: int
    kode: str
    baris: int
    galat: str | None = None


def _panda_tersedia() -> tuple[Any, Any]:
    """Impor pandas & yfinance saat dipakai, bukan saat modul diimpor.

    Alasannya praktis: `mejasaham.ingesti` (inti aturan) harus bisa diimpor di lingkungan tanpa
    yfinance — mis. saat menjalankan saringan dari basis data yang sudah terisi. Impor di
    puncak modul akan membuat seluruh paket bergantung pada satu penyedia data tidak resmi.
    """
    try:
        import pandas as pd  # noqa: PLC0415 - sengaja lambat, lihat docstring
        import yfinance as yf  # noqa: PLC0415
    except ImportError as galat:
        raise GalatIngesti(
            f"yfinance/pandas belum terpasang ({galat}). Pasang dengan "
            "`pip install -r requirements.txt`, atau pakai jalur impor berkas sebagai gantinya."
        ) from galat
    return pd, yf


def _baris_harga(kode: str, tanggal: Any, baris: Any) -> HargaHarian:
    """Ubah satu bar pandas menjadi `HargaHarian` bertipe (T8).

    Volume dari yfinance bisa berpecahan untuk sebagian emiten; karena itu ia melewati konversi
    yang sama dengan harga: yang berhitung `INTEGER`, aslinya tersimpan di `*_mentah`.

    Nilai `*_mentah` yang **sudah** ada di baris tidak ditimpa nilai mentah dari sumber: kolom
    itu milik pemanggil yang menyiapkan barisnya, dan menimpanya berarti membuang angka asli
    yang justru disimpan untuk audit.
    """
    di_mana = f"{kode} {tanggal}"
    buka, buka_mentah = _ke_rupiah(baris.get("Open"), f"{di_mana} open")
    tinggi, tinggi_mentah = _ke_rupiah(baris.get("High"), f"{di_mana} high")
    rendah, rendah_mentah = _ke_rupiah(baris.get("Low"), f"{di_mana} low")
    tutup, tutup_mentah = _ke_rupiah(baris.get("Close"), f"{di_mana} close")
    volume, volume_mentah = _ke_lembar(baris.get("Volume"), f"{di_mana} volume")

    return HargaHarian(
        kode=kode,
        tanggal=tanggal,
        open=buka,
        high=tinggi,
        low=rendah,
        close=tutup,
        volume=volume,
        open_mentah=baris.get("open_mentah") or buka_mentah,
        high_mentah=baris.get("high_mentah") or tinggi_mentah,
        low_mentah=baris.get("low_mentah") or rendah_mentah,
        close_mentah=baris.get("close_mentah") or tutup_mentah,
        volume_mentah=baris.get("volume_mentah") or volume_mentah,
        nilai_mentah=baris.get("nilai_mentah"),
        # K8/C10 — dan ini bukan dugaan: harga yang dikirim Yahoo **sudah** memakai basis
        # pascasplit sementara kejadian split-nya tetap dilaporkan. Diukur pada BBCA (split 5:1,
        # 13 Okt 2021: 7.320 -> 7.525), BMRI, BBNI, TPIA, dan NVDA. Bukti lengkapnya di
        # `docs/keputusan.md` 1.5. Tanpa penanda ini, penyesuaian saat dibaca akan diterapkan
        # untuk kedua kalinya dan angka momentum menjadi salah tanpa terlihat.
        penyesuaian_sumber=PENYESUAIAN_SPLIT,
    )


def _aksi_korporasi(kode: str, tindakan: Any) -> tuple[AksiKorporasi, ...]:
    """Ubah tabel tindakan yfinance (Dividends, Stock Splits) menjadi aksi korporasi (U4).

    Konvensi rasio (lihat `skema.py`): harga disesuaikan x (`rasio_lama` / `rasio_baru`).
    - Stock split 1:2 dari Yahoo bernilai 2,0 → `rasio_lama=1`, `rasio_baru=2`.
    - Reverse split 2:1 dari Yahoo bernilai 0,5 → `rasio_lama=2`, `rasio_baru=1`.

    Dividen masuk sebagai aksi korporasi jenis `dividen` **tanpa** menyesuaikan harga (U4):
    ia dipakai untuk arus kas posisi dan imbal hasil dividen, bukan untuk mengubah harga
    historis.
    """
    hasil: list[AksiKorporasi] = []
    for cap, isi in tindakan.iterrows():
        tanggal = cap.date() if hasattr(cap, "date") else cap
        dividen = isi.get("Dividends")
        split = isi.get("Stock Splits")

        if dividen is not None and not _nol(dividen):
            per_saham, mentah = _ke_rupiah(dividen, f"{kode} {tanggal} dividen")
            if per_saham is not None:
                hasil.append(
                    AksiKorporasi(
                        kode=kode,
                        tanggal=tanggal,
                        jenis="dividen",
                        dividen_per_saham=per_saham,
                        keterangan=f"dividen {mentah} per saham (nilai mentah sumber)",
                    )
                )

        if split is not None and not _nol(split):
            angka = _desimal_kecil(split, f"{kode} {tanggal} split")
            if angka is not None and angka > 0:
                # Yahoo memberi faktor: 2,0 = pecah 1 menjadi 2; 0,5 = gabung 2 menjadi 1.
                if angka > 1:
                    lama, baru, jenis = 1, int(angka), "split"
                else:
                    lama, baru, jenis = int(Decimal(1) / angka), 1, "reverse_split"
                hasil.append(
                    AksiKorporasi(
                        kode=kode,
                        tanggal=tanggal,
                        jenis=jenis,
                        rasio_lama=lama,
                        rasio_baru=baru,
                        keterangan=f"faktor {angka} dari sumber tidak resmi",
                    )
                )
    return tuple(hasil)


def _desimal_kecil(nilai: object, di_mana: str) -> Decimal | None:
    try:
        angka = Decimal(str(nilai))
    except (InvalidOperation, ValueError) as galat:
        raise GalatIngesti(f"{di_mana}: bukan angka ({nilai!r})") from galat
    return angka if angka.is_finite() else None


def _nol(nilai: object) -> bool:
    """True bila nilainya nol/kosong (Yahoo mengisi 0,0 untuk hari tanpa aksi korporasi)."""
    angka = _desimal_kecil(nilai, "aksi korporasi")
    return angka is None or angka == 0


class PengambilYFinance:
    """Pengambil data EOD dari Yahoo Finance lewat yfinance (sumber tidak resmi).

    Sengaja berbentuk kelas, bukan fungsi, supaya `--refresh` bisa memakai objek ini sambil
    test menyuntikkan pengambil palsu ke `jalankan_refresh` tanpa menyentuh jaringan.
    """

    def __init__(
        self,
        *,
        periode: str = PERIODE_BAWAAN,
        mulai: date | None = None,
        sampai: date | None = None,
        jeda: float = JEDA_BAWAAN,
        percobaan: int = PERCOBAAN_BAWAAN,
        indeks: Iterable[str] = (),
        laporan: Any = None,
    ) -> None:
        self.periode = periode
        self.mulai = mulai
        # `sampai` sengaja tidak dipakai langsung sebagai parameter `end` yfinance: `end`
        # bersifat eksklusif, dan kelebihan satu hari lebih tidak berbahaya daripada
        # kehilangan bar hari terakhir.
        self.sampai = sampai
        self.jeda = jeda
        self.percobaan = percobaan
        self.indeks = tuple(indeks)
        self.laporan = laporan

    # -- bagian dalam ------------------------------------------------------------------

    def _ticker(self, kode: str) -> Any:
        _pd, yf = _panda_tersedia()
        return yf.Ticker(kode)

    def _galat_naik(self) -> Any:
        """Konteks tempat galat sumber dibiarkan naik (U18). Dipisah supaya bisa diganti uji."""
        return _galat_sumber_naik()

    def _riwayat(self, kode: str) -> Any:
        """Ambil riwayat harian dengan ulang otomatis dan jeda bertambah (U18).

        Kegagalan **permanen tidak diulang**. Mengulang jawaban "simbol ini tidak punya data"
        tidak akan mengubah jawabannya, dan setiap permintaan tambahan menambah risiko
        pembatasan laju — risiko yang sudah nyata bagi sumber tidak resmi ini (K7). Yang
        diulang hanyalah kegagalan sementara, dengan jeda bertambah seperti semula.
        """
        ticker = self._ticker(kode)
        alasan: str | None = None
        for nomor in range(self.percobaan):
            try:
                with self._galat_naik():
                    if self.mulai is None and self.sampai is None:
                        return ticker.history(
                            period=self.periode, interval="1d", auto_adjust=False, actions=True
                        )
                    return ticker.history(
                        start=self.mulai.isoformat() if self.mulai else None,
                        end=self.sampai.isoformat() if self.sampai else None,
                        interval="1d",
                        auto_adjust=False,
                        actions=True,
                    )
            except Exception as galat:  # noqa: BLE001 - penyedia data melempar banyak jenis galat
                jenis, alasan = _klasifikasi_galat(galat)
                if jenis == KEGAGALAN_PERMANEN:
                    raise GalatPengambilan(f"{kode}: {alasan}", jenis=jenis) from galat
                if nomor < self.percobaan - 1:
                    time.sleep(self._jeda_ulang(nomor))
        raise GalatPengambilan(
            f"gagal mengambil {kode} setelah {self.percobaan} percobaan — {alasan}",
            jenis=KEGAGALAN_SEMENTARA,
        )

    def _jeda_ulang(self, nomor: int) -> float:
        return JEDA_ULANG[nomor] if nomor < len(JEDA_ULANG) else JEDA_ULANG[-1]

    def _kode_yahoo(self, kode: str) -> str:
        """Kode IDX → kode Yahoo. Kode indeks (berawalan `^`) dibiarkan apa adanya."""
        return kode if kode.startswith("^") else f"{kode}.JK"

    # -- bagian luar -------------------------------------------------------------------

    def ambil(self, emiten: Sequence[Emiten]) -> KumpulanData:
        """Ambil OHLCV + aksi korporasi untuk seluruh emiten, lalu indeksnya."""
        if not emiten:
            raise GalatIngesti("daftar emiten kosong: tidak ada yang bisa diambil")

        harga: list[HargaHarian] = []
        aksi: list[AksiKorporasi] = []
        gagal: list[Kegagalan] = []
        catatan: list[str] = []

        for nomor, satu in enumerate(emiten, start=1):
            galat: str | None = None
            jumlah = 0
            try:
                riwayat = self._riwayat(self._kode_yahoo(satu.kode))
                if riwayat is None or len(riwayat) == 0:
                    # Sampai di sini berarti sumber mengembalikan nol baris **tanpa** galat
                    # bertipe: sebabnya tidak dinyatakan, jadi jenisnya tidak boleh ditebak
                    # permanen (U18). Kalimatnya menyebut itu apa adanya.
                    raise GalatPengambilan(
                        f"{satu.kode}: sumber tidak mengembalikan satu bar pun dan tidak "
                        "menyebut sebabnya",
                        jenis=KEGAGALAN_SEMENTARA,
                    )
                for cap, baris in riwayat.iterrows():
                    if self.sampai is not None and cap.date() > self.sampai:
                        continue
                    harga.append(_baris_harga(satu.kode, cap.date(), baris))
                    jumlah += 1
                aksi.extend(_aksi_korporasi(satu.kode, riwayat))
            except GalatPengambilan as keluhan:
                galat = str(keluhan)
                gagal.append(Kegagalan(satu.kode, galat, keluhan.jenis))
            except GalatIngesti as keluhan:
                # Mis. nilai yang tidak terbaca di tengah baris. Itu cacat data, bukan jawaban
                # sumber tentang kodenya — jadi sementara, dan tetap menahan snapshot.
                galat = str(keluhan)
                gagal.append(Kegagalan(satu.kode, galat, KEGAGALAN_SEMENTARA))

            if self.laporan is not None:
                self.laporan(Kemajuan(nomor=nomor, dari=len(emiten), kode=satu.kode, baris=jumlah, galat=galat))
            if self.jeda and nomor < len(emiten):
                time.sleep(self.jeda)

        indeks: list[PenutupanIndeks] = []
        for nama in self.indeks:
            kode_yahoo = INDEKS.get(nama, nama)
            try:
                riwayat = self._riwayat(kode_yahoo)
                if riwayat is None or len(riwayat) == 0:
                    raise GalatPengambilan(
                        f"{nama}: sumber tidak mengembalikan satu bar pun dan tidak menyebut sebabnya",
                        jenis=KEGAGALAN_SEMENTARA,
                    )
                for cap, baris in riwayat.iterrows():
                    if self.sampai is not None and cap.date() > self.sampai:
                        continue
                    tutup, tutup_mentah = _ke_rupiah(baris.get("Close"), f"{nama} {cap.date()}")
                    indeks.append(
                        PenutupanIndeks(
                            indeks=nama,
                            tanggal=cap.date(),
                            close=tutup,
                            close_mentah=tutup_mentah,
                        )
                    )
            except GalatPengambilan as keluhan:
                # Indeks yang gagal **tidak** dianggap sukses diam-diam: PRD 7.1 menuntut IHSG
                # ada sebelum skor momentum dihitung, jadi kegagalannya harus terlihat.
                gagal.append(Kegagalan(nama, str(keluhan), keluhan.jenis))
            except GalatIngesti as keluhan:
                gagal.append(Kegagalan(nama, str(keluhan), KEGAGALAN_SEMENTARA))
            if self.jeda:
                time.sleep(self.jeda)

        catatan.append(
            f"diambil lewat yfinance periode={self.periode!r}"
            + (f" mulai={self.mulai}" if self.mulai else "")
            + (f" sampai={self.sampai}" if self.sampai else "")
        )
        return KumpulanData(
            sumber=SUMBER_YFINANCE,
            emiten=tuple(emiten),
            harga_harian=tuple(harga),
            harga_indeks=tuple(indeks),
            aksi_korporasi=tuple(aksi),
            gagal=tuple(gagal),
            catatan=tuple(catatan),
        )


def rentang_overlap(hari: int = 10) -> tuple[date, date]:
    """Rentang pendek untuk refresh harian: menutup hari libur & perbaikan data sumber.

    Menyegarkan sedikit ke belakang lebih murah daripada kehilangan bar, dan karena tabelnya
    append-only, bar yang sudah ada dan isinya sama tidak menambah baris.
    """
    hari_ini = date.today()
    return hari_ini - timedelta(days=hari), hari_ini


# ---------------------------------------------------------------------------------------
# Fundamental tahunan (K18, 10 Okt 2026)
# ---------------------------------------------------------------------------------------
# PRD 7.1 menulis sumber fundamental sebagai "laporan keuangan emiten; **impor berkas bila
# penyedia tidak lengkap**", dan Q8 (keputusan 17.1) memutuskan "mulai dengan yfinance berlabel
# 'tidak resmi' plus jalur impor berkas sebagai cadangan". Bertentangan dengan catatan P2 yang
# lama ("fundamental tidak ada di yfinance"), sumber ini **memang** memuat laporan keuangannya —
# dan itu terukur 10 Okt 2026, bukan diduga (`ROE` turunan cocok dengan ringkasan sumber, dan
# `CFO` cocok lewat dua jalur independen dengan selisih 0,0%).
#
# Empat hal yang menentukan bentuk kode di bawah, semuanya hasil pengukuran atas 60 emiten:
#
# 1. **Nama barisnya tidak seragam.** Hanya 10% emiten memakai `Operating Cash Flow`; 78% memakai
#    bentuk laporan arus kas **metode langsung** (`...Operating Activities Direct`). Karena itu
#    setiap kolom dipetakan dari daftar nama berurutan prioritas, bukan dari satu nama.
# 2. **Jumlah tahunnya paling banyak 4–5.** Akibatnya ROE 5 tahun dihitung dari tahun yang ada
#    (median), dan `metrik.roe_5t` sudah menangani itu apa adanya.
# 3. **`info.sharesOutstanding` tidak dapat dipercaya** (17% baris berbeda >5% dari neraca; satu
#    emiten meleset 78 kali). Jumlah saham diambil dari **neraca** (`Ordinary Shares Number`).
# 4. **Kegagalan tidak selalu berbentuk galat.** Ada emiten yang membalas tabel kosong tanpa
#    satu pun exception. Karena itu tabel kosong diperiksa **bentuknya**, bukan hanya `except`.
#
# Yang **tidak** diisi di sini, dan itu disengaja: `dps` (dividen per saham menuntut penjumlahan
# per tahun buku dari deret ex-date — turunan yang belum diuji, dan angka dividen yang salah lebih
# berbahaya daripada tidak ada), `mata_uang` yang tidak dinyatakan sumbernya (menebaknya membuat
# seluruh rasio salah 16.000 kali), dan laporan kuartalan (bentuk kuartalan sumber ini **per
# kuartal**, sedangkan skema hanya menerima `tahunan` dan `ytd_kumulatif`; menandainya
# `ytd_kumulatif` akan menghitung ganda di `metrik.ttm` — AC-18).

#: Nama baris laporan sumber untuk tiap kolom `fundamental`, urut prioritas. Nama pertama yang
#: ada di laporan itulah yang dipakai; tidak ada satu pun → kolom itu `None` (bukan nol).
BARIS_LAPORAN: Mapping[str, tuple[str, ...]] = {
    "pendapatan": ("Total Revenue", "Operating Revenue"),
    "laba_induk": (
        "Net Income Common Stockholders",
        "Net Income",
        "Net Income From Continuing Operation Net Minority Interest",
        "Net Income Continuous Operations",
    ),
    "ekuitas_induk": (
        "Stockholders Equity",
        "Common Stock Equity",
        "Total Equity Gross Minority Interest",
    ),
    "ebit": ("EBIT", "Operating Income", "Total Operating Income As Reported"),
    # `Interest Expense` saja. `Net Interest Income` **bukan** beban bunga (itu pendapatan bunga
    # bersih bank); memetakannya ke sini akan membuat coverage bank tampak sehat tanpa dasar.
    "beban_bunga": ("Interest Expense", "Interest Expense Non Operating"),
    "da": ("Reconciled Depreciation", "Depreciation And Amortization", "Depreciation Amortization Depletion"),
    "utang_bunga": ("Total Debt",),
    "kas": ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash Financial"),
    "cfo": (
        "Operating Cash Flow",
        "Total Cash From Operating Activities",
        "Cash Flowsfromusedin Operating Activities Direct",
    ),
    "jumlah_saham": ("Ordinary Shares Number", "Share Issued"),
}

#: Kolom yang tidak boleh negatif (mengikuti CHECK di `skema.py`). Nilai negatif dari sumber
#: berarti barisnya bergeser atau kolomnya tertukar; kolom itu **dilepas** dan alasannya
#: dilaporkan, bukan disimpan sebagai angka yang melanggar aturan tabelnya.
KOLOM_POSITIF = (
    "pendapatan",
    "beban_bunga",
    "da",
    "utang_bunga",
    "kas",
    "jumlah_saham",
)

#: Nama kolom di berkas impor diambil dari spesifikasi pembacanya (`berkas.SPESIFIKASI`), bukan
#: disalin ke sini: berkas yang ditulis dan berkas yang dibaca harus punya satu bentuk, dan dua
#: daftar kolom yang bisa berbeda adalah cara paling tenang untuk membuatnya tidak sama.


def _teks(nilai: object) -> str:
    """Nilai kosong ditulis **kosong** di berkas, bukan "None" dan bukan nol (aturan keras 2)."""
    return "" if nilai is None else str(nilai)


def sel_fundamental(satu: Fundamental) -> dict[str, str]:
    """Satu baris `Fundamental` → sel-sel berkas `fundamental.csv`."""
    return {
        "kode": satu.kode,
        "periode": satu.periode.isoformat(),
        "jenis_laporan": satu.jenis_laporan,
        "tgl_publikasi": satu.tgl_publikasi.isoformat(),
        "asal_tgl_publikasi": satu.asal_tgl_publikasi,
        "mata_uang": satu.mata_uang,
        "satuan_uang": satu.satuan_uang,
        "pendapatan": _teks(satu.pendapatan),
        "laba_induk": _teks(satu.laba_induk),
        "ekuitas_induk": _teks(satu.ekuitas_induk),
        "ebit": _teks(satu.ebit),
        "beban_bunga": _teks(satu.beban_bunga),
        "da": _teks(satu.da),
        "utang_bunga": _teks(satu.utang_bunga),
        "kas": _teks(satu.kas),
        "cfo": _teks(satu.cfo),
        "jumlah_saham": _teks(satu.jumlah_saham),
        # `dps` sengaja kosong: menurunkannya menuntut penjumlahan dividen per tahun buku dari
        # deret ex-date, dan angka dividen yang salah lebih berbahaya daripada tidak ada.
        "dps": "",
        "sumber": satu.sumber or "",
    }


def _komentar_fundamental(diambil_pada: date, jumlah_emiten: int, jumlah_baris: int) -> tuple[str, ...]:
    """Penjelasan yang ikut tertulis **di dalam** berkas, supaya angkanya tidak salah dibaca."""
    return (
        "# =========================================================================================",
        "# FUNDAMENTAL OTOMATIS — Meja Saham",
        "# =========================================================================================",
        f"# Ditulis oleh `--ambil-fundamental` pada {diambil_pada.isoformat()} "
        f"({jumlah_emiten} emiten, {jumlah_baris} baris).",
        "#",
        "# SUMBER TIDAK RESMI (K7, PRD 7.1/Q8): angka di berkas ini berasal dari penyedia data EOD",
        "# gratis, bukan dari laporan resmi emiten. Labelnya ikut di setiap baris pada kolom",
        "# `sumber`, dan laporan mutu menandai snapshot yang memakainya.",
        "#",
        "# ARTI KOLOM YANG BERBEDA DARI TEMPLATE",
        "#   tgl_publikasi       = TANGGAL PENGAMBILAN, bukan tanggal terbit laporan. Sumbernya",
        "#                         tidak menyatakan tanggal terbit, dan mengarang tanggal terbit",
        "#                         akan melanggar aturan point-in-time (AC-15).",
        "#   asal_tgl_publikasi  = tanggal_pengambilan, penanda bahwa baris di atas berlaku.",
        "#   satuan_uang         = rupiah: nilai di berkas sudah dalam satuan uang penuh.",
        "#   mata_uang           = sesuai yang dinyatakan sumbernya. Sebagian emiten (16,7% pada",
        "#                         pengukuran 10 Okt 2026) melapor dalam USD; barisnya **tidak**",
        "#                         dikonversi, dan metrik yang mencampurnya dengan harga rupiah",
        "#                         berstatus \"tidak dihitung\" (PRD 8.2, AC-3).",
        "#   jenis_laporan       = tahunan saja. Laporan kuartalan sumber ini berbentuk per kuartal,",
        "#                         bukan kumulatif (YTD), dan skema hanya menerima `ytd_kumulatif`;",
        "#                         menandainya YTD akan menghitung ganda di `metrik.ttm` (AC-18).",
        "#   dps                 = sengaja kosong, lihat catatan di `pengambil.sel_fundamental`.",
        "#",
        "# BERKAS INI BOLEH ANDA SUNting: perbaiki `tgl_publikasi` bila Anda punya tanggal terbit",
        "# yang sebenarnya (ubah juga `asal_tgl_publikasi` menjadi `sumber`), atau lengkapi kolom",
        "# yang kosong. Baris hasil suntingan Anda ikut terimpor seperti baris lainnya — tetapi",
        "# `--ambil-fundamental --timpa-fundamental` menulis ulang berkas ini dari awal dan akan",
        "# menghapus suntingan yang belum terimpor.",
        "# =========================================================================================",
    )


def hanya_template(jalur: Path) -> bool:
    """True bila berkas fundamental belum memuat satu baris data pun.

    AC-12 menyalin template ke folder konfigurasi begitu aplikasi dijalankan, jadi berkas ini
    **selalu** ada sejak awal. Tanpa pemeriksaan ini, penjaga "jangan menimpa berkas Anda"
    berubah menjadi "perintah ini tidak pernah bisa dijalankan tanpa --timpa", dan penjaga yang
    selalu berbunyi berhenti memberi informasi.
    """
    try:
        isi = jalur.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return False
    for baris in isi[1:]:  # baris pertama = kepala, selalu ada
        teks = baris.strip()
        if not teks or teks.startswith("#") or teks.startswith(berkas.PENANDA_CONTOH):
            continue
        return False
    return True


def tulis_fundamental_csv(
    baris: Sequence[Fundamental],
    jalur: Path,
    *,
    diambil_pada: date,
    jumlah_emiten: int,
) -> int:
    """Tulis `fundamental.csv` dalam bentuk yang dibaca `--impor`; kembalikan jumlah baris data.

    Baris kepala ditulis **lebih dulu**, sebelum penjelasan: pembaca berkas mendeteksi pemisah
    kolom dari baris pertamanya, jadi penjelasan yang mendahuluinya membuat berkas ini terbaca
    sebagai berkas berpemisah koma (jebakan yang pernah terjadi di berkas lain).
    """
    kolom = tuple(berkas.SPESIFIKASI["fundamental"].nama_kolom)
    with jalur.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
        penulis = csv.writer(berkas_tulis, delimiter=";", lineterminator="\n")
        penulis.writerow(kolom)
        for satu in _komentar_fundamental(diambil_pada, jumlah_emiten, len(baris)):
            berkas_tulis.write(satu + "\n")
        for satu in baris:
            sel = sel_fundamental(satu)
            penulis.writerow([sel[nama] for nama in kolom])
    return len(baris)


@dataclass(frozen=True)
class HasilFundamental:
    """Hasil pembacaan satu emiten: barisnya, catatannya, dan alasan bila tidak ada baris."""

    kode: str
    baris: tuple[Fundamental, ...] = ()
    catatan: tuple[str, ...] = ()
    gagal: str | None = None


#: Toleransi pembulatan nilai sumber, relatif terhadap besarannya. Sumber menyimpan sebagian
#: angkanya sebagai pecahan biner — terukur 10 Okt 2026: pendapatan 2022 MBSS
#: `1374923392560,987` dan CUAN `97665445,660545`, masing-masing **satu** tahun dari satu emiten,
#: dengan sisa 0,013 rupiah dari 1,37 triliun dan 0,34 dolar dari 97 juta. Itu artefak
#: penyimpanan, bukan angka yang berbeda: membulatkannya tidak mengubah apa pun yang bermakna,
#: sedangkan menolak seluruh emitennnya membuang data yang sah.
#:
#: Yang **tidak** ditoleransi adalah pecahan yang berarti terhadap besarannya (mis. `1,5`):
#: itu tanda kolomnya salah baca, dan membulatkannya diam-diam menyembunyikan tepat kesalahan
#: yang paling sulit ditemukan (T8).
TOLERANSI_BULAT = Decimal("1e-6")


def _bilangan(nilai: object, di_mana: str) -> tuple[int | None, str | None]:
    """Nilai sumber → (rupiah/lembar bulat, catatan pembulatan); `None` bila tidak ada nilainya.

    Nilai berpecahan yang berarti **ditolak**, bukan dibulatkan; yang hanya artefak penyimpanan
    dibulatkan **beserta catatannya**, supaya pembulatan itu tidak pernah tanpa jejak.
    """
    if nilai is None:
        return None, None
    try:
        angka = Decimal(str(nilai))
    except (InvalidOperation, ValueError) as galat:
        raise GalatIngesti(f"{di_mana}: nilai {nilai!r} bukan angka") from galat
    if not angka.is_finite():
        return None, None
    bulat = angka.to_integral_value()
    if angka == bulat:
        return int(bulat), None
    selisih = abs(angka - bulat)
    if selisih > abs(angka) * TOLERANSI_BULAT:
        raise GalatIngesti(
            f"{di_mana}: nilai {nilai!r} berpecahan, padahal laporan dinyatakan dalam satuan penuh"
        )
    return (
        int(bulat),
        f"{di_mana}: nilai {nilai!r} dibulatkan ke {int(bulat)} (selisih {selisih} — artefak "
        "penyimpanan sumber, bukan angka yang berbeda)",
    )


def tabel_dari_laporan(
    income: object, balance: object, cashflow: object
) -> dict[str, dict[date, object]]:
    """Ubah tiga kerangka laporan sumber menjadi `{nama baris: {periode: nilai}}`.

    Hanya kerangka yang bentuknya dikenali yang dibaca: sumber yang tidak memuat satu baris pun
    menghasilkan kamus kosong — dan itu dilaporkan sebagai "tanpa laporan", bukan sebagai laporan
    berisi nol (temuan 4 di kepala bagian ini).
    """
    tabel: dict[str, dict[date, object]] = {}
    for kerangka in (income, balance, cashflow):
        if kerangka is None or getattr(kerangka, "empty", True):
            continue
        try:
            kolom = list(kerangka.columns)
            index = list(kerangka.index)
        except AttributeError:
            continue
        for nama in index:
            try:
                deret = kerangka.loc[nama]
            except (KeyError, TypeError, ValueError):
                continue
            isi: dict[date, object] = {}
            for urutan, periode in enumerate(kolom):
                try:
                    nilai = deret.iloc[urutan]
                except (AttributeError, IndexError):
                    continue
                if nilai is None:
                    continue
                isi[periode.date() if hasattr(periode, "date") else periode] = nilai
            if isi:
                tabel.setdefault(str(nama), {}).update(isi)
    return tabel


def fundamental_dari_laporan(
    kode: str,
    tabel: Mapping[str, Mapping[date, object]],
    *,
    diambil_pada: date,
    mata_uang: str | None,
    sumber: str,
) -> HasilFundamental:
    """Susun baris `fundamental` tahunan dari laporan yang sudah berbentuk kamus.

    Terpisah dari pengambilan jaringan supaya seluruh pemetaan — nama baris mana yang dipakai,
    kolom mana yang dilepas, tahun mana yang dilewati — bisa diuji tanpa jaringan sama sekali.
    """
    catatan: list[str] = []
    if mata_uang is None:
        # Menebak mata uang membuat seluruh rasio salah 16.000 kali untuk laporan USD, tanpa satu
        # pun tanda di layar. Sumber yang tidak menyatakannya tidak dipakai (aturan keras 1).
        return HasilFundamental(
            kode=kode,
            gagal="sumber tidak menyatakan mata uang laporannya, dan menebaknya tidak boleh",
        )
    if mata_uang not in ("IDR", "USD"):
        return HasilFundamental(kode=kode, gagal=f"mata uang {mata_uang!r} tidak dikenal skema")

    # Kolom diambil dari daftar prioritas: nama pertama yang **ada isinya** di laporan itu.
    terpetakan: dict[str, dict[date, object]] = {}
    for kolom, nama_baris in BARIS_LAPORAN.items():
        for nama in nama_baris:
            deret = tabel.get(nama)
            if deret:
                terpetakan[kolom] = deret
                break
        else:
            catatan.append(f"{kolom}: tidak ada di laporan sumber")

    periode = sorted({satu for deret in terpetakan.values() for satu in deret})
    if not periode:
        return HasilFundamental(
            kode=kode, catatan=tuple(catatan), gagal="laporan sumber kosong (tidak ada satu tahun pun)"
        )

    baris: list[Fundamental] = []
    for satu_periode in periode:
        angka: dict[str, int | None] = {}
        for kolom, deret in terpetakan.items():
            # `_bilangan` sengaja **tidak** dibungkus try: angka berpecahan atau bukan angka
            # berarti kolomnya salah baca, dan itu harus menghentikan emiten ini dengan suara
            # (aturan keras 7) — bukan menjadi catatan sambil tahun-tahun lain tetap dipakai.
            terhitung, catatan_bulat = _bilangan(
                deret.get(satu_periode), f"{kode} {satu_periode} {kolom}"
            )
            if catatan_bulat:
                catatan.append(catatan_bulat)
            if terhitung is not None and kolom in KOLOM_POSITIF and terhitung < 0:
                catatan.append(
                    f"{kode} {satu_periode} {kolom}: nilai {terhitung} negatif padahal kolom ini "
                    "tidak boleh negatif — dilepas, bukan disimpan"
                )
                continue
            angka[kolom] = terhitung

        if not any(angka.get(nama) is not None for nama in ("pendapatan", "laba_induk", "ekuitas_induk", "ebit", "cfo")):
            catatan.append(f"{kode} {satu_periode}: tidak ada angka yang bisa dipakai — tahun dilewati")
            continue

        baris.append(
            Fundamental(
                kode=kode,
                periode=satu_periode,
                jenis_laporan="tahunan",
                # Tanggal **pengambilan**, bukan tanggal terbit: sumber ini tidak menyatakan
                # tanggal terbit, dan `asal_tgl_publikasi` mencatat itu supaya tidak berbohong.
                tgl_publikasi=diambil_pada,
                asal_tgl_publikasi="tanggal_pengambilan",
                mata_uang=mata_uang,
                satuan_uang="rupiah",
                pendapatan=angka.get("pendapatan"),
                laba_induk=angka.get("laba_induk"),
                ekuitas_induk=angka.get("ekuitas_induk"),
                ebit=angka.get("ebit"),
                beban_bunga=angka.get("beban_bunga"),
                da=angka.get("da"),
                utang_bunga=angka.get("utang_bunga"),
                kas=angka.get("kas"),
                cfo=angka.get("cfo"),
                jumlah_saham=angka.get("jumlah_saham"),
                sumber=sumber,
            )
        )

    if not baris:
        return HasilFundamental(
            kode=kode, catatan=tuple(catatan), gagal="tidak ada tahun buku yang bisa dipakai"
        )
    return HasilFundamental(kode=kode, baris=tuple(baris), catatan=tuple(catatan))


def _ambil_laporan(
    kode: str, *, percobaan: int
) -> tuple[dict[str, dict[date, object]], Mapping[str, Any], str | None]:
    """Ambil tiga kerangka laporan + `info`, dengan percobaan ulang **hanya** untuk kegagalan
    pengambilan.

    Percobaan ulang sengaja tidak membungkus pemetaannya: kegagalan membaca data sumber bersifat
    deterministik (mengulanginya menghasilkan jawaban yang sama), sedangkan yang perlu diulang
    hanyalah kegagalan jaringan dan pembatasan laju.
    """
    _pd, yf = _panda_tersedia()
    galat_terakhir = ""
    for urutan in range(percobaan):
        try:
            with _galat_sumber_naik():
                emiten = yf.Ticker(f"{kode}.JK")
                income = emiten.income_stmt
                balance = emiten.balance_sheet
                cashflow = emiten.cashflow
                try:
                    info: Mapping[str, Any] = emiten.info or {}
                except Exception:  # noqa: BLE001 - sumber bisa menolak `info` saja
                    # Bukan kegagalan yang ditelan: tanpa `info` mata uang laporannya tidak
                    # dapat dipastikan, dan `fundamental_dari_laporan` menolak menebaknya.
                    info = {}
            return tabel_dari_laporan(income, balance, cashflow), info, None
        except GalatIngesti as keluhan:
            galat_terakhir = str(keluhan)
        except Exception as keluhan:  # noqa: BLE001 - yfinance memunculkan banyak jenis galat
            galat_terakhir = f"{type(keluhan).__name__}: {keluhan}".strip()
        if urutan + 1 < percobaan:
            time.sleep(JEDA_ULANG[min(urutan, len(JEDA_ULANG) - 1)])
    return {}, {}, galat_terakhir or "gagal diambil tanpa alasan yang dinyatakan"


def fundamental_emiten(
    kode: str,
    *,
    diambil_pada: date,
    jeda: float = JEDA_BAWAAN,
    percobaan: int = PERCOBAAN_BAWAAN,
) -> HasilFundamental:
    """Ambil laporan tahunan satu emiten dari sumber tidak resmi (K18).

    Galat **pemetaan** (angka berpecahan, nilai bukan angka) sengaja dibiarkan naik ke pemanggil:
    angka berpecahan pada laporan yang dinyatakan dalam satuan penuh berarti kolomnya salah baca,
    dan seluruh isi kolom itu patut dicurigai — membuang satu selnya diam-diam justru menyisakan
    tahun-tahun lain yang salah dengan cara yang sama.
    """
    tabel, info, galat = _ambil_laporan(kode, percobaan=percobaan)
    try:
        if galat is not None:
            return HasilFundamental(kode=kode, gagal=galat)
        if not tabel:
            return HasilFundamental(
                kode=kode, gagal="sumber tidak memuat laporan keuangan tahunan untuk kode ini"
            )
        sumber = f"{SUMBER_YFINANCE}; laporan keuangan tahunan; diakses {diambil_pada.isoformat()}"
        return fundamental_dari_laporan(
            kode,
            tabel,
            diambil_pada=diambil_pada,
            mata_uang=info.get("financialCurrency"),
            sumber=sumber,
        )
    finally:
        # Batas laju penyedia dihormati di sini, bukan di pemanggil: jeda yang harus diingat
        # pemanggil adalah jeda yang cepat atau lambat akan terlupa (dan itu membuat penyedianya
        # menolak seluruh permintaan berikutnya).
        if jeda:
            time.sleep(jeda)


#: Kunci `info` yang dipakai untuk menurunkan `jenis` emiten (K21). `sector` dan `industry`
#: adalah label yang **dinyatakan sumbernya**; yang diturunkan darinya hanya `bank_keuangan`,
#: dan aturan penurunannya hidup di `mejasaham/jenis.py` — bukan di sini, supaya bisa diuji
#: tanpa jaringan dan tidak tumbuh menjadi aturan kedua di jalur pengambilan.
KUNCI_SECTOR = "sector"
KUNCI_INDUSTRY = "industry"


@dataclass(frozen=True)
class HasilSector:
    """`sector`/`industry` satu kode sebagaimana dinyatakan sumber, atau alasan ketiadaannya."""

    kode: str
    sector: str | None = None
    industry: str | None = None
    gagal: str | None = None

    @property
    def ada(self) -> bool:
        """True bila sumber menyatakan salah satunya. Dua-duanya kosong = tidak dinyatakan."""
        return bool((self.sector or "").strip() or (self.industry or "").strip())


def sector_emiten(
    kode: str,
    *,
    jeda: float = JEDA_BAWAAN,
    percobaan: int = PERCOBAAN_BAWAAN,
) -> HasilSector:
    """Ambil `sector`/`industry` satu emiten dari sumber data yang sudah dipakai (K21).

    Hanya dua kunci itu yang dibaca dari `info`. Yang **tidak** diambil dan tidak boleh ditebak:
    pemetaan ke taksonomi IDX-IC (K12, P16) — sumber data memakai taksonomi lain, dan pemetaan
    resmi antara keduanya tidak diterbitkan siapa pun.

    Kegagalan mengembalikan `gagal` alih-alih melempar: satu kode tanpa `sector` bukan alasan
    menghentikan seluruh pengambilan, tetapi juga tidak boleh menjadi baris berisi tebakan.
    """
    _pd, yf = _panda_tersedia()
    galat_terakhir = ""
    try:
        for urutan in range(percobaan):
            try:
                with _galat_sumber_naik():
                    info: Mapping[str, Any] = yf.Ticker(f"{kode}.JK").info or {}
                sector = _teks(info.get(KUNCI_SECTOR))
                industry = _teks(info.get(KUNCI_INDUSTRY))
                if not sector and not industry:
                    # Bukan galat: sumber menjawab, tetapi tidak menyatakan sektornya. Keadaan
                    # itu punya tempatnya sendiri — baris **tidak** dibuat (K21).
                    return HasilSector(kode=kode)
                return HasilSector(kode=kode, sector=sector or None, industry=industry or None)
            except GalatIngesti as keluhan:
                galat_terakhir = str(keluhan)
            except Exception as keluhan:  # noqa: BLE001 - yfinance memunculkan banyak jenis galat
                galat_terakhir = f"{type(keluhan).__name__}: {keluhan}".strip()
            if urutan + 1 < percobaan:
                time.sleep(JEDA_ULANG[min(urutan, len(JEDA_ULANG) - 1)])
        return HasilSector(kode=kode, gagal=galat_terakhir or "gagal diambil tanpa alasan yang dinyatakan")
    finally:
        # Jeda dihormati juga saat gagal: sumber yang sedang membatasi laju justru yang paling
        # dirugikan oleh permintaan berikutnya yang datang terlalu cepat.
        if jeda:
            time.sleep(jeda)
