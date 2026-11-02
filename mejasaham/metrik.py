"""Definisi metrik PRD 8.2 — satu tempat, tanpa UI, bisa diuji tanpa jendela (A1).

Aturan yang mengikat modul ini:

* **Metrik tanpa data berstatus "tidak dihitung"** beserta alasannya (aturan keras 2, AC-3).
  Tidak ada nilai yang diganti nol, rata-rata sektor, atau diabaikan tanpa jejak.
* **Set metrik mengikuti jenis emiten** (PRD 8.4, AC-16): DER, coverage, dan CFO/NI tidak
  pernah dihitung untuk bank; bank memakai NPL/CAR/BOPO/NIM dari `rasio_bank`.
* **Point-in-time** (aturan keras 3, AC-15): `potret.muat()` sudah menyaring fundamental
  menurut `tgl_publikasi`, dan harga disesuaikan hanya dengan aksi yang sudah diketahui
  (`penyesuaian.sesuaikan`).
* **Setiap nilai membawa asalnya** (PRD 10: "metrik tanpa asal data tidak ditampilkan").
* **Format angka bukan urusan modul ini** (U11); ia mengembalikan angka, bukan teks.

Angka dikembalikan sebagai `float` untuk rasio dan statistik, dan sebagai `float` juga untuk
rupiah besar (kapitalisasi pasar). Aritmetika uang yang menuntut ketepatan — ukuran posisi,
lembar, stop — dikerjakan di kalkulator risiko dengan `Fraction`, bukan di sini (T8).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from math import log, sqrt

from mejasaham.ingesti import Fundamental, RasioBank
from mejasaham.penyesuaian import BarDisesuaikan, HasilPenyesuaian, sesuaikan
from mejasaham.potret import Potret

# --- jendela hari bursa (K10/P6) ---------------------------------------------------------
HARI_12_BULAN = 252
HARI_6_BULAN = 126
HARI_60 = 60
BULAN = 21
MA_PENDEK = 50
MA_PANJANG = 200
ATR_PERIODE = 14
ADTV_PERIODE = 20
TAHUN_BUKU = 5
TAHUN_CFO = 3
TAHUN_CAGR = 3

#: Fundamental yang lebih tua dari ini disembunyikan metrik kualitasnya (PRD 7.3, P13).
BATAS_FUNDAMENTAL_BASI_HARI = 18 * 30

#: Indeks acuan pasar (PRD 8.2). Satu tempat: kekuatan relatif, rezim pasar, dan baris IHSG di
#: dasbor (`dasbor.py`) harus menunjuk indeks yang **sama** — kalau tidak, "pasar" berarti dua hal
#: berbeda di dua layar tanpa satu pun galat.
INDEKS_ACUAN = "IHSG"

#: Faktor disetahunkan untuk volatilitas (P7): akar 252 hari bursa.
AKAR_HARI_BURSA = sqrt(252)

STATUS_DIHITUNG = "dihitung"
STATUS_TIDAK_DIHITUNG = "tidak_dihitung"


@dataclass(frozen=True)
class Nilai:
    """Satu metrik: angkanya, satuannya, statusnya, dan dari mana asalnya."""

    nama: str
    nilai: float | None
    satuan: str
    status: str = STATUS_DIHITUNG
    alasan: str | None = None
    asal: str = ""

    @property
    def ada(self) -> bool:
        return self.status == STATUS_DIHITUNG and self.nilai is not None


def hitung(nama: str, nilai: float | None, satuan: str, asal: str, alasan_kosong: str) -> Nilai:
    """Bungkus satu perhitungan: `None` **selalu** menjadi "tidak dihitung" + alasan."""
    if nilai is None:
        return Nilai(nama=nama, nilai=None, satuan=satuan, status=STATUS_TIDAK_DIHITUNG,
                     alasan=alasan_kosong, asal=asal)
    return Nilai(nama=nama, nilai=float(nilai), satuan=satuan, asal=asal)


def tidak_dihitung(nama: str, satuan: str, alasan: str, asal: str = "") -> Nilai:
    return Nilai(nama=nama, nilai=None, satuan=satuan, status=STATUS_TIDAK_DIHITUNG,
                 alasan=alasan, asal=asal)


# --- statistik kecil (tanpa dependensi) --------------------------------------------------


def rata_rata(angka: Sequence[float]) -> float | None:
    return sum(angka) / len(angka) if angka else None


def simpangan_baku(angka: Sequence[float]) -> float | None:
    """Simpangan baku **sampel** (ddof=1) — dipakai volatilitas (P7)."""
    if len(angka) < 2:
        return None
    rerata = sum(angka) / len(angka)
    varian = sum((satu - rerata) ** 2 for satu in angka) / (len(angka) - 1)
    return sqrt(varian)


def median(angka: Sequence[float]) -> float | None:
    if not angka:
        return None
    urut = sorted(angka)
    tengah = len(urut) // 2
    if len(urut) % 2:
        return urut[tengah]
    return (urut[tengah - 1] + urut[tengah]) / 2


def _statistik_populasi(angka: Sequence[float]) -> tuple[float, float]:
    """Rata-rata & simpangan baku **populasi** (ddof=0) untuk z-score sektor (K10/P10)."""
    rerata = sum(angka) / len(angka)
    varian = sum((satu - rerata) ** 2 for satu in angka) / len(angka)
    return rerata, sqrt(varian)


# --- deret harga --------------------------------------------------------------------------


def seri_harga(potret: Potret, kode: str) -> HasilPenyesuaian:
    """Deret harga emiten, sudah disesuaikan dengan aksi yang diketahui saat snapshot (K8).

    Deret sambungan yang tidak lolos gerbang (K97 b) dikembalikan dengan alasannya, sehingga
    seluruh metrik harga emiten itu "tidak dihitung" — di sini, satu pintu untuk semuanya.
    """
    hasil = sesuaikan(
        potret.harga.get(kode, ()),
        potret.aksi.get(kode, ()),
        batas_tanggal=potret.tanggal_data,
    )
    keadaan = potret.keadaan_sambungan
    ditolak = keadaan.ditolak.get(kode) if keadaan is not None else None
    if ditolak is not None and hasil.siap:
        return replace(hasil, alasan_tak_dihitung=ditolak)
    return hasil


def _tutup(bar: Sequence[BarDisesuaikan]) -> list[float]:
    return [float(satu.close) for satu in bar if satu.close is not None]


def _nilai_transaksi(bar: Sequence[BarDisesuaikan]) -> list[float]:
    """`nilai` (rupiah) per bar; bar tanpa nilai transaksi dibuang, bukan dianggap nol (U6)."""
    return [float(satu.nilai) for satu in bar if satu.nilai is not None]


# ---------------------------------------------------------------------------------------
# Metrik harga
# ---------------------------------------------------------------------------------------


def adtv20(seri: HasilPenyesuaian) -> Nilai:
    """ADTV20: rata-rata nilai transaksi 20 hari bursa terakhir (PRD 8.2)."""
    nama = "adtv20"
    if not seri.siap:
        return tidak_dihitung(nama, "rupiah", seri.alasan_tak_dihitung or "harga tidak siap")
    nilai = _nilai_transaksi(seri.bar[-ADTV_PERIODE:])
    if len(nilai) < ADTV_PERIODE:
        return tidak_dihitung(
            nama, "rupiah",
            f"hanya {len(nilai)} dari {ADTV_PERIODE} hari bursa terakhir yang punya nilai transaksi",
        )
    return hitung(nama, rata_rata(nilai), "rupiah", f"{ADTV_PERIODE} hari bursa terakhir", "tidak ada data")


def momentum_12_1(seri: HasilPenyesuaian) -> Nilai:
    """Momentum 12-1: imbal hasil 12 bulan tanpa bulan terakhir (PRD 8.2, P6)."""
    nama = "momentum_12_1"
    if not seri.siap:
        return tidak_dihitung(nama, "rasio", seri.alasan_tak_dihitung or "harga tidak siap")
    tutup = _tutup(seri.bar)
    butuh = HARI_12_BULAN + 1
    if len(tutup) < butuh:
        return tidak_dihitung(nama, "rasio", f"butuh {butuh} hari bursa, tersedia {len(tutup)}")
    awal = tutup[-(HARI_12_BULAN + 1)]
    akhir = tutup[-(BULAN + 1)]
    if awal <= 0:
        return tidak_dihitung(nama, "rasio", "harga awal jendela nol atau kosong")
    return hitung(nama, akhir / awal - 1, "rasio", f"{HARI_12_BULAN} hari bursa (tanpa {BULAN} terakhir)", "tidak ada data")


def kekuatan_relatif_6b(potret: Potret, seri: HasilPenyesuaian) -> Nilai:
    """Kekuatan relatif: imbal hasil 6 bulan saham dikurangi imbal hasil IHSG periode sama."""
    nama = "kekuatan_relatif_6b"
    if not seri.siap:
        return tidak_dihitung(nama, "rasio", seri.alasan_tak_dihitung or "harga tidak siap")
    indeks = potret.indeks.get(INDEKS_ACUAN, ())
    tutup_saham = _tutup(seri.bar)
    tutup_indeks = [float(satu.close) for satu in indeks if satu.close is not None]
    butuh = HARI_6_BULAN + 1
    if len(tutup_saham) < butuh:
        return tidak_dihitung(nama, "rasio", f"butuh {butuh} hari bursa saham, tersedia {len(tutup_saham)}")
    if len(tutup_indeks) < butuh:
        return tidak_dihitung(nama, "rasio", f"IHSG belum tersedia {butuh} hari bursa")
    if tutup_saham[-butuh] <= 0 or tutup_indeks[-butuh] <= 0:
        return tidak_dihitung(nama, "rasio", "harga awal jendela nol atau kosong")
    imbal_saham = tutup_saham[-1] / tutup_saham[-butuh] - 1
    imbal_indeks = tutup_indeks[-1] / tutup_indeks[-butuh] - 1
    return hitung(nama, imbal_saham - imbal_indeks, "rasio", f"{HARI_6_BULAN} hari bursa vs IHSG", "tidak ada data")


def volatilitas_60h(seri: HasilPenyesuaian) -> Nilai:
    """Volatilitas disetahunkan: simpangan baku imbal hasil **log** 60 hari × √252 (P7)."""
    nama = "volatilitas_60h"
    if not seri.siap:
        return tidak_dihitung(nama, "rasio", seri.alasan_tak_dihitung or "harga tidak siap")
    tutup = _tutup(seri.bar)
    if len(tutup) < HARI_60:
        return tidak_dihitung(nama, "rasio", f"butuh {HARI_60} hari bursa, tersedia {len(tutup)}")
    jendela = tutup[-HARI_60:]
    imbal: list[float] = []
    for sebelumnya, sekarang in zip(jendela, jendela[1:]):
        if sebelumnya <= 0 or sekarang <= 0:
            return tidak_dihitung(nama, "rasio", "ada harga nol di dalam jendela")
        imbal.append(log(sekarang / sebelumnya))
    simpangan = simpangan_baku(imbal)
    if simpangan is None:
        return tidak_dihitung(nama, "rasio", "imbal hasil harian tidak cukup untuk disetahunkan")
    return hitung(nama, simpangan * AKAR_HARI_BURSA, "rasio", f"{len(imbal)} imbal hasil harian dari {HARI_60} baris", "tidak ada data")


def atr14_rupiah(seri: HasilPenyesuaian) -> Nilai:
    """ATR14 Wilder dalam **rupiah** (PRD 8.2 butir ATR14; PRD 9.7 memakainya untuk stop bawaan).

    Dipisah dari `atr14_persen` supaya rumusnya hanya ditulis sekali: stop bawaan PRD 9.7
    berbunyi `harga masuk − 2 × ATR14`, dan itu menuntut ATR dalam rupiah — bukan persen yang
    lalu dikalikan harga dengan pembulatan kedua. Nilainya sengaja **tidak** ikut masuk
    `metrik_emiten`: yang diskor saringan adalah `atr14_persen` (PRD 9.5.1), dan menambah
    metrik baru di sana akan mengubah susunan skor tanpa keputusan produk.
    """
    nama = "atr14_rupiah"
    if not seri.siap:
        return tidak_dihitung(nama, "rupiah", seri.alasan_tak_dihitung or "harga tidak siap")
    bar = [satu for satu in seri.bar if satu.high is not None and satu.low is not None and satu.close is not None]
    if len(bar) < ATR_PERIODE + 1:
        return tidak_dihitung(nama, "rupiah", f"butuh {ATR_PERIODE + 1} baris, tersedia {len(bar)}")

    rentang: list[float] = []
    for sebelumnya, sekarang in zip(bar, bar[1:]):
        tinggi = float(sekarang.high)  # type: ignore[arg-type]
        rendah = float(sekarang.low)  # type: ignore[arg-type]
        tutup_lalu = float(sebelumnya.close)  # type: ignore[arg-type]
        rentang.append(max(tinggi - rendah, abs(tinggi - tutup_lalu), abs(rendah - tutup_lalu)))

    # Wilder: nilai pertama = rata-rata sederhana 14 rentang, lalu dilicinkan.
    atr = sum(rentang[:ATR_PERIODE]) / ATR_PERIODE
    for satu in rentang[ATR_PERIODE:]:
        atr = (atr * (ATR_PERIODE - 1) + satu) / ATR_PERIODE
    return hitung(nama, atr, "rupiah", f"ATR{ATR_PERIODE} Wilder", "tidak ada data")


def atr14_persen(seri: HasilPenyesuaian) -> Nilai:
    """ATR14 Wilder sebagai persen harga terakhir (PRD 8.2, P8). Butuh 15 baris."""
    nama = "atr14_persen"
    rupiah = atr14_rupiah(seri)
    if not rupiah.ada:
        return tidak_dihitung(nama, "rasio", rupiah.alasan or "harga tidak siap")
    bar = [satu for satu in seri.bar if satu.close is not None]
    tutup_akhir = float(bar[-1].close)  # type: ignore[arg-type]
    if tutup_akhir <= 0:
        return tidak_dihitung(nama, "rasio", "harga penutupan terakhir nol atau kosong")
    return hitung(
        nama,
        float(rupiah.nilai) / tutup_akhir,  # type: ignore[arg-type]
        "rasio",
        f"ATR{ATR_PERIODE} Wilder",
        "tidak ada data",
    )


def jarak_52_minggu(seri: HasilPenyesuaian) -> Nilai:
    """Jarak dari harga tertinggi 52 minggu: close tertinggi 252 hari bursa (P9)."""
    nama = "jarak_52_minggu"
    if not seri.siap:
        return tidak_dihitung(nama, "rasio", seri.alasan_tak_dihitung or "harga tidak siap")
    tutup = _tutup(seri.bar)
    if len(tutup) < HARI_12_BULAN:
        return tidak_dihitung(nama, "rasio", f"butuh {HARI_12_BULAN} hari bursa, tersedia {len(tutup)}")
    jendela = tutup[-HARI_12_BULAN:]
    tertinggi = max(jendela)
    if tertinggi <= 0:
        return tidak_dihitung(nama, "rasio", "harga tertinggi jendela nol atau kosong")
    return hitung(nama, jendela[-1] / tertinggi - 1, "rasio", f"{HARI_12_BULAN} hari bursa", "tidak ada data")


def _rata_rata_bergerak(seri: HasilPenyesuaian, periode: int, nama: str) -> Nilai:
    if not seri.siap:
        return tidak_dihitung(nama, "rupiah", seri.alasan_tak_dihitung or "harga tidak siap")
    tutup = _tutup(seri.bar)
    if len(tutup) < periode:
        return tidak_dihitung(nama, "rupiah", f"butuh {periode} hari bursa, tersedia {len(tutup)}")
    rerata = rata_rata(tutup[-periode:])
    if rerata is None:
        return tidak_dihitung(nama, "rupiah", "tidak ada harga penutupan")
    return hitung(nama, rerata, "rupiah", f"rata-rata {periode} hari bursa", "tidak ada data")


def ma50(seri: HasilPenyesuaian) -> Nilai:
    return _rata_rata_bergerak(seri, MA_PENDEK, "ma50")


def ma200(seri: HasilPenyesuaian) -> Nilai:
    return _rata_rata_bergerak(seri, MA_PANJANG, "ma200")


def tren_ma200(seri: HasilPenyesuaian, ma: Nilai | None = None) -> Nilai:
    """1 bila harga penutupan di atas MA200, 0 bila di bawah — dipakai sebagai saringan (9.5.1)."""
    nama = "tren_ma200"
    acuan = ma if ma is not None else ma200(seri)
    if not acuan.ada:
        return tidak_dihitung(nama, "boolean", acuan.alasan or "MA200 tidak tersedia")
    tutup = _tutup(seri.bar)
    if not tutup:
        return tidak_dihitung(nama, "boolean", "tidak ada harga penutupan")
    return hitung(nama, 1.0 if tutup[-1] > float(acuan.nilai or 0) else 0.0, "boolean", "harga vs MA200", "tidak ada data")


def harga_terakhir(seri: HasilPenyesuaian) -> Nilai:
    nama = "harga"
    if not seri.siap:
        return tidak_dihitung(nama, "rupiah", seri.alasan_tak_dihitung or "harga tidak siap")
    tutup = _tutup(seri.bar)
    if not tutup:
        return tidak_dihitung(nama, "rupiah", "belum ada baris harga")
    return hitung(nama, tutup[-1], "rupiah", "penutupan terakhir (setelah penyesuaian)", "tidak ada data")


# ---------------------------------------------------------------------------------------
# Fundamental: pelaporan, TTM, dan set bank
# ---------------------------------------------------------------------------------------


def _terpilih(potret: Potret, kode: str) -> dict[tuple[date, str], Fundamental]:
    """Satu laporan terbaik per (periode, jenis): yang publikasinya paling akhir.

    Restatement itu nyata: satu periode bisa punya beberapa baris dengan `tgl_publikasi`
    berbeda, dan yang berlaku pada tanggal snapshot adalah yang terakhir terbit **sampai**
    tanggal itu.
    """
    hasil: dict[tuple[date, str], Fundamental] = {}
    for satu in potret.fundamental.get(kode, ()):
        kunci = (satu.periode, satu.jenis_laporan)
        ada = hasil.get(kunci)
        if ada is None or satu.tgl_publikasi > ada.tgl_publikasi:
            hasil[kunci] = satu
    return hasil


def _tahunan(terpilih: Mapping[tuple[date, str], Fundamental]) -> list[Fundamental]:
    return sorted(
        (satu for (_, jenis), satu in terpilih.items() if jenis == "tahunan"),
        key=lambda satu: satu.periode,
    )


def _ytd(terpilih: Mapping[tuple[date, str], Fundamental]) -> list[Fundamental]:
    return sorted(
        (satu for (_, jenis), satu in terpilih.items() if jenis == "ytd_kumulatif"),
        key=lambda satu: satu.periode,
    )


#: Kolom fundamental yang bisa di-TTM-kan (arus periode). Kolom neraca (ekuitas, utang, kas,
#: jumlah saham) adalah posisi pada satu tanggal — menjumlahkannya tidak bermakna.
KOLOM_ARUS = ("pendapatan", "laba_induk", "ebit", "beban_bunga", "da", "cfo")


def ttm(
    terpilih: Mapping[tuple[date, str], Fundamental], kolom: str
) -> tuple[int | None, str]:
    """Nilai 12 bulan terakhir (PRD 8.2): tahunan terakhir + YTD berjalan − YTD tahun lalu.

    Laporan kuartalan IDX umumnya **kumulatif** (Januari–Juni, bukan April–Juni), sehingga
    penjumlahan langsung akan menghitung ganda. Karena itu bentuknya seperti ini (AC-18).
    Mengembalikan (nilai, keterangan); nilai `None` berarti tidak bisa dihitung.
    """
    tahunan = _tahunan(terpilih)
    if not tahunan:
        return None, "belum ada laporan tahunan"
    dasar = tahunan[-1]
    nilai_dasar = getattr(dasar, kolom)
    if nilai_dasar is None:
        return None, f"laporan tahunan {dasar.periode} tidak memuat {kolom}"

    ytd = [satu for satu in _ytd(terpilih) if satu.periode > dasar.periode]
    if not ytd:
        return nilai_dasar, f"laporan tahunan {dasar.periode}"

    berjalan = ytd[-1]
    if getattr(berjalan, kolom) is None:
        return None, f"laporan YTD {berjalan.periode} tidak memuat {kolom}"
    periode_lalu = berjalan.periode.replace(year=berjalan.periode.year - 1)
    pembanding = next(
        (satu for satu in _ytd(terpilih) if satu.periode == periode_lalu), None
    )
    if pembanding is None or getattr(pembanding, kolom) is None:
        return None, (
            f"YTD {periode_lalu} (pembanding tahun lalu) belum ada, sehingga 12 bulan terakhir "
            f"sampai {berjalan.periode} tidak bisa dihitung"
        )
    return (
        nilai_dasar + getattr(berjalan, kolom) - getattr(pembanding, kolom),
        f"tahunan {dasar.periode} + YTD {berjalan.periode} − YTD {pembanding.periode}",
    )


def _laporan_terakhir(terpilih: Mapping[tuple[date, str], Fundamental]) -> Fundamental | None:
    semua = list(terpilih.values())
    return max(semua, key=lambda satu: (satu.periode, satu.tgl_publikasi)) if semua else None


def _periksa_mata_uang(laporan: Fundamental) -> str | None:
    """Alasan "tidak dihitung" bila laporan tidak dalam rupiah, atau None bila aman.

    Sebagian emiten IDX melaporkan dalam USD. Mencampurnya dengan harga rupiah menghasilkan
    PER/EV-EBITDA yang salah tanpa terlihat, jadi metriknya berhenti di sini.
    """
    if laporan.mata_uang != "IDR":
        return (
            f"laporan dinyatakan dalam {laporan.mata_uang}, sedangkan harga dalam rupiah; "
            "mencampur keduanya menghasilkan angka yang salah"
        )
    return None


def _asing(potret: Potret, kode: str) -> tuple[dict[tuple[date, str], Fundamental], Fundamental | None, str | None]:
    """Laporan terpilih + pemeriksaan menyeluruh yang berlaku untuk semua metrik fundamental."""
    terpilih = _terpilih(potret, kode)
    terakhir = _laporan_terakhir(terpilih)
    if terakhir is None:
        return terpilih, None, "belum ada laporan fundamental untuk emiten ini"
    return terpilih, terakhir, None


def _kolom(laporan: Fundamental, kolom: str) -> int | None:
    nilai = getattr(laporan, kolom)
    return int(nilai) if nilai is not None else None


def roe_5t(potret: Potret, kode: str) -> Nilai:
    """ROE 5 tahun: median ROE tahunan; ekuitas ≤ 0 → tahun itu tidak dihitung (PRD 8.2, P5)."""
    nama = "roe_5t"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    if terakhir.mata_uang != "IDR" and terakhir.mata_uang != "USD":
        return tidak_dihitung(nama, "rasio", f"mata uang {terakhir.mata_uang} tidak dikenal")

    tahunan = _tahunan(terpilih)
    jendela = tahunan[-(TAHUN_BUKU + 1):]
    roe: list[float] = []
    alasan: list[str] = []
    for sebelumnya, sekarang in zip(jendela, jendela[1:]):
        laba = _kolom(sekarang, "laba_induk")
        awal = _kolom(sebelumnya, "ekuitas_induk")
        akhir = _kolom(sekarang, "ekuitas_induk")
        if laba is None or awal is None or akhir is None:
            alasan.append(f"{sekarang.periode.year}: data tidak lengkap")
            continue
        if awal <= 0 or akhir <= 0:
            alasan.append(f"{sekarang.periode.year}: ekuitas ≤ 0")
            continue
        roe.append(laba / ((awal + akhir) / 2))
    if not roe:
        rincian = "; ".join(alasan[:3]) or f"butuh {TAHUN_BUKU + 1} laporan tahunan"
        return tidak_dihitung(nama, "rasio", f"tidak ada tahun buku yang bisa dihitung ({rincian})")
    asal = f"median {len(roe)} tahun buku (dari {TAHUN_BUKU} tahun terakhir)"
    return hitung(nama, median(roe), "rasio", asal, "tidak ada data")


def cagr_pendapatan(potret: Potret, kode: str) -> Nilai:
    """CAGR pendapatan 3 tahun: akar pangkat 3 dari pendapatan terakhir ÷ 3 tahun lalu (8.2)."""
    nama = "cagr_pendapatan"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    tahunan = _tahunan(terpilih)
    if len(tahunan) < TAHUN_CAGR + 1:
        return tidak_dihitung(
            nama, "rasio",
            f"butuh {TAHUN_CAGR + 1} laporan tahunan, tersedia {len(tahunan)}",
        )
    akhir = _kolom(tahunan[-1], "pendapatan")
    awal = _kolom(tahunan[-(TAHUN_CAGR + 1)], "pendapatan")
    if akhir is None or awal is None:
        return tidak_dihitung(nama, "rasio", "pendapatan awal atau akhir jendela tidak ada")
    if awal <= 0 or akhir <= 0:
        return tidak_dihitung(nama, "rasio", "pendapatan nol atau negatif tidak bisa dipangkatkan")
    return hitung(
        nama, (akhir / awal) ** (1 / TAHUN_CAGR) - 1, "rasio",
        f"tahunan {tahunan[-(TAHUN_CAGR + 1)].periode} → {tahunan[-1].periode}", "tidak ada data",
    )


def cfo_ni(potret: Potret, kode: str) -> Nilai:
    """Mutu laba: jumlah arus kas operasi 3 tahun ÷ jumlah laba 3 tahun; laba ≤ 0 → tidak (8.2)."""
    nama = "cfo_ni"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    tahunan = _tahunan(terpilih)[-TAHUN_CFO:]
    if len(tahunan) < TAHUN_CFO:
        return tidak_dihitung(nama, "rasio", f"butuh {TAHUN_CFO} laporan tahunan, tersedia {len(tahunan)}")
    cfo = [_kolom(satu, "cfo") for satu in tahunan]
    laba = [_kolom(satu, "laba_induk") for satu in tahunan]
    if any(satu is None for satu in cfo) or any(satu is None for satu in laba):
        return tidak_dihitung(nama, "rasio", "arus kas operasi atau laba ada yang kosong di jendela 3 tahun")
    jumlah_laba = sum(satu for satu in laba if satu is not None)
    if jumlah_laba <= 0:
        return tidak_dihitung(nama, "rasio", "jumlah laba 3 tahun ≤ 0 sehingga rasionya tidak bermakna (P11)")
    jumlah_cfo = sum(satu for satu in cfo if satu is not None)
    return hitung(nama, jumlah_cfo / jumlah_laba, "rasio", f"jumlah {TAHUN_CFO} tahun buku", "tidak ada data")


def der(potret: Potret, kode: str) -> Nilai:
    """DER: utang berbunga ÷ ekuitas. Tidak pernah dipakai untuk bank (PRD 8.2, 8.4, AC-16)."""
    nama = "der"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    utang = _kolom(terakhir, "utang_bunga")
    ekuitas = _kolom(terakhir, "ekuitas_induk")
    if utang is None:
        return tidak_dihitung(nama, "rasio", f"laporan {terakhir.periode} tidak memuat utang berbunga")
    if ekuitas is None:
        return tidak_dihitung(nama, "rasio", f"laporan {terakhir.periode} tidak memuat ekuitas")
    if ekuitas <= 0:
        return tidak_dihitung(nama, "rasio", "ekuitas ≤ 0 sehingga DER tidak bermakna")
    return hitung(nama, utang / ekuitas, "rasio", f"laporan {terakhir.periode}", "tidak ada data")


def coverage(potret: Potret, kode: str) -> Nilai:
    """Coverage: EBIT ÷ beban bunga (12 bulan terakhir)."""
    nama = "coverage"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    ebit, asal_ebit = ttm(terpilih, "ebit")
    bunga, _ = ttm(terpilih, "beban_bunga")
    if ebit is None:
        return tidak_dihitung(nama, "rasio", f"EBIT 12 bulan terakhir tidak bisa dihitung: {asal_ebit}")
    if bunga is None:
        return tidak_dihitung(nama, "rasio", "beban bunga 12 bulan terakhir tidak bisa dihitung")
    if bunga == 0:
        return tidak_dihitung(nama, "rasio", "beban bunga nol sehingga rasio tidak bermakna")
    return hitung(nama, ebit / bunga, "rasio", asal_ebit, "tidak ada data")


def _jumlah_saham(potret: Potret, kode: str, terakhir: Fundamental | None) -> tuple[int | None, str]:
    """Jumlah saham: dari laporan bila ada, kalau tidak dari daftar emiten (as-of snapshot)."""
    if terakhir is not None and terakhir.jumlah_saham:
        return int(terakhir.jumlah_saham), f"laporan {terakhir.periode}"
    daftar = potret.emiten.get(kode)
    if daftar is not None and daftar.jumlah_saham:
        return int(daftar.jumlah_saham), "daftar emiten"
    return None, "jumlah saham beredar belum ada (di laporan maupun daftar emiten)"


def _kapitalisasi(potret: Potret, kode: str, seri: HasilPenyesuaian) -> tuple[float | None, str, str | None]:
    acuan = harga_terakhir(seri)
    if not acuan.ada:
        return None, "", acuan.alasan
    _, terakhir, galat = _asing(potret, kode)
    if galat:
        return None, "", galat
    saham, asal_saham = _jumlah_saham(potret, kode, terakhir)
    if saham is None:
        return None, "", asal_saham
    return float(acuan.nilai or 0) * saham, f"harga × {saham} lembar ({asal_saham})", None


def per(potret: Potret, kode: str, seri: HasilPenyesuaian) -> Nilai:
    """PER TTM: harga ÷ laba per saham 12 bulan terakhir. Laba ≤ 0 → tidak dihitung (P11)."""
    return _per_umum(potret, kode, seri, nama="per")


def per_normalisasi(potret: Potret, kode: str, seri: HasilPenyesuaian) -> Nilai:
    """PER normalisasi siklikal: harga ÷ rata-rata laba per saham 5 tahun buku (8.4, P12)."""
    nama = "per_normalisasi"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    salah_uang = _periksa_mata_uang(terakhir)
    if salah_uang:
        return tidak_dihitung(nama, "rasio", salah_uang)
    acuan = harga_terakhir(seri)
    if not acuan.ada:
        return tidak_dihitung(nama, "rasio", acuan.alasan or "harga tidak tersedia")
    tahunan = _tahunan(terpilih)[-TAHUN_BUKU:]
    laba = [_kolom(satu, "laba_induk") for satu in tahunan]
    laba = [satu for satu in laba if satu is not None]
    if not laba:
        return tidak_dihitung(nama, "rasio", "laba 5 tahun buku belum ada")
    saham, asal_saham = _jumlah_saham(potret, kode, terakhir)
    if not saham:
        return tidak_dihitung(nama, "rasio", asal_saham)
    eps_rata = (sum(laba) / len(laba)) / saham
    if eps_rata <= 0:
        return tidak_dihitung(
            nama, "rasio",
            f"rata-rata laba {len(laba)} tahun buku ≤ 0 sehingga PER normalisasi tidak bermakna (P11)",
        )
    asal = f"rata-rata {len(laba)} tahun buku (tahun rugi ikut dihitung)"
    return hitung(nama, float(acuan.nilai or 0) / eps_rata, "rasio", asal, "tidak ada data")


def _per_umum(potret: Potret, kode: str, seri: HasilPenyesuaian, *, nama: str) -> Nilai:
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    salah_uang = _periksa_mata_uang(terakhir)
    if salah_uang:
        return tidak_dihitung(nama, "rasio", salah_uang)
    acuan = harga_terakhir(seri)
    if not acuan.ada:
        return tidak_dihitung(nama, "rasio", acuan.alasan or "harga tidak tersedia")
    laba, asal_laba = ttm(terpilih, "laba_induk")
    if laba is None:
        return tidak_dihitung(nama, "rasio", f"laba 12 bulan terakhir tidak bisa dihitung: {asal_laba}")
    saham, asal_saham = _jumlah_saham(potret, kode, terakhir)
    if not saham:
        return tidak_dihitung(nama, "rasio", asal_saham)
    eps = laba / saham
    if eps <= 0:
        return tidak_dihitung(nama, "rasio", "laba per saham ≤ 0 sehingga PER tidak bermakna (P11)")
    return hitung(nama, float(acuan.nilai or 0) / eps, "rasio", f"{asal_laba}; {asal_saham}", "tidak ada data")


def pbv(potret: Potret, kode: str, seri: HasilPenyesuaian) -> Nilai:
    """PBV: harga ÷ nilai buku per saham. Ekuitas ≤ 0 → tidak dihitung."""
    nama = "pbv"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    salah_uang = _periksa_mata_uang(terakhir)
    if salah_uang:
        return tidak_dihitung(nama, "rasio", salah_uang)
    acuan = harga_terakhir(seri)
    if not acuan.ada:
        return tidak_dihitung(nama, "rasio", acuan.alasan or "harga tidak tersedia")
    ekuitas = _kolom(terakhir, "ekuitas_induk")
    if ekuitas is None:
        return tidak_dihitung(nama, "rasio", f"laporan {terakhir.periode} tidak memuat ekuitas")
    if ekuitas <= 0:
        return tidak_dihitung(nama, "rasio", "ekuitas ≤ 0 sehingga PBV tidak bermakna")
    saham, asal_saham = _jumlah_saham(potret, kode, terakhir)
    if not saham:
        return tidak_dihitung(nama, "rasio", asal_saham)
    return hitung(
        nama, float(acuan.nilai or 0) / (ekuitas / saham), "rasio",
        f"laporan {terakhir.periode}; {asal_saham}", "tidak ada data",
    )


def ev_ebitda(potret: Potret, kode: str, seri: HasilPenyesuaian) -> Nilai:
    """EV/EBITDA: (kapitalisasi + utang berbunga − kas) ÷ EBITDA 12 bulan terakhir."""
    nama = "ev_ebitda"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    salah_uang = _periksa_mata_uang(terakhir)
    if salah_uang:
        return tidak_dihitung(nama, "rasio", salah_uang)
    kapitalisasi, asal_kapitalisasi, masalah = _kapitalisasi(potret, kode, seri)
    if kapitalisasi is None:
        return tidak_dihitung(nama, "rasio", masalah or "kapitalisasi pasar tidak bisa dihitung")
    utang = _kolom(terakhir, "utang_bunga")
    kas = _kolom(terakhir, "kas")
    if utang is None or kas is None:
        return tidak_dihitung(nama, "rasio", "utang berbunga atau kas tidak ada di laporan terakhir")
    ebit, asal_ebit = ttm(terpilih, "ebit")
    da, _ = ttm(terpilih, "da")
    if ebit is None:
        return tidak_dihitung(nama, "rasio", f"EBIT 12 bulan terakhir tidak bisa dihitung: {asal_ebit}")
    if da is None:
        return tidak_dihitung(nama, "rasio", "penyusutan & amortisasi 12 bulan terakhir tidak bisa dihitung")
    ebitda = ebit + da
    if ebitda <= 0:
        return tidak_dihitung(nama, "rasio", "EBITDA ≤ 0 sehingga EV/EBITDA tidak bermakna (P11)")
    return hitung(
        nama, (kapitalisasi + utang - kas) / ebitda, "rasio",
        f"{asal_kapitalisasi}; EBITDA {asal_ebit}", "tidak ada data",
    )


def imbal_hasil_laba_minus_sun(potret: Potret, kode: str, seri: HasilPenyesuaian) -> Nilai:
    """Selisih imbal hasil laba (laba ÷ harga) terhadap imbal hasil SUN 10 tahun (PRD 8.2)."""
    nama = "imbal_hasil_laba_minus_sun"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    salah_uang = _periksa_mata_uang(terakhir)
    if salah_uang:
        return tidak_dihitung(nama, "rasio", salah_uang)
    kapitalisasi, asal_kapitalisasi, masalah = _kapitalisasi(potret, kode, seri)
    if kapitalisasi is None or kapitalisasi <= 0:
        return tidak_dihitung(nama, "rasio", masalah or "kapitalisasi pasar nol")
    laba, asal_laba = ttm(terpilih, "laba_induk")
    if laba is None:
        return tidak_dihitung(nama, "rasio", f"laba 12 bulan terakhir tidak bisa dihitung: {asal_laba}")
    if laba <= 0:
        return tidak_dihitung(nama, "rasio", "laba ≤ 0 sehingga imbal hasil laba tidak bermakna (P11)")
    sun = imbal_hasil_sun_terakhir(potret)
    if sun is None:
        return tidak_dihitung(nama, "rasio", "imbal hasil SUN 10 tahun belum ada di basis data")
    return hitung(
        nama, laba / kapitalisasi - sun / 10000, "rasio",
        f"{asal_kapitalisasi}; SUN 10 tahun", "tidak ada data",
    )


def imbal_hasil_sun_terakhir(potret: Potret, tenor: int = 10) -> float | None:
    """Imbal hasil SUN (basis poin) terakhir yang diketahui pada snapshot, atau None."""
    kandidat = [satu for satu in potret.sun if satu.tenor_tahun == tenor]
    return float(kandidat[-1].imbal_hasil_bp) if kandidat else None


def imbal_hasil_dividen(potret: Potret, kode: str, seri: HasilPenyesuaian) -> Nilai:
    """Imbal hasil dividen: dividen per saham 12 bulan terakhir ÷ harga (8.2: ditampilkan saja)."""
    nama = "imbal_hasil_dividen"
    terpilih, terakhir, galat = _asing(potret, kode)
    if galat:
        return tidak_dihitung(nama, "rasio", galat)
    assert terakhir is not None
    salah_uang = _periksa_mata_uang(terakhir)
    if salah_uang:
        return tidak_dihitung(nama, "rasio", salah_uang)
    acuan = harga_terakhir(seri)
    if not acuan.ada or float(acuan.nilai or 0) <= 0:
        return tidak_dihitung(nama, "rasio", acuan.alasan or "harga nol")
    batas = potret.tanggal_data - timedelta(days=365)
    dividen = [
        _kolom(satu, "dps") or 0
        for satu in terpilih.values()
        if satu.periode >= batas and _kolom(satu, "dps") is not None
    ]
    if not dividen:
        return tidak_dihitung(nama, "rasio", "dividen per saham 12 bulan terakhir belum ada")
    return hitung(
        nama, sum(dividen) / float(acuan.nilai or 0), "rasio",
        f"{len(dividen)} pembayaran dividen dalam 12 bulan", "tidak ada data",
    )


# --- set bank (PRD 8.4, Q6, AC-16) --------------------------------------------------------


def _rasio_bank_terakhir(potret: Potret, kode: str) -> tuple[RasioBank | None, str]:
    deret = potret.rasio_bank.get(kode, ())
    if not deret:
        return None, "rasio bank (NPL/CAR/BOPO/NIM) belum diimpor lewat rasio-bank.csv"
    return deret[-1], f"periode {deret[-1].periode}"


def _nilai_rasio(potret: Potret, kode: str, kolom: str, nama: str) -> Nilai:
    # PRD 8.4: "metrik yang tidak bermakna untuk sebuah jenis tidak diterapkan, bukan diisi nol".
    # Penjaga ini ada di sini, bukan hanya di pemilihan kriteria `saring.py`, karena satu baris
    # `rasio-bank.csv` yang salah kode akan menampilkan NPL/CAR/BOPO/NIM sebagai metrik emiten
    # non-bank di **setiap** pemakai `metrik_emiten` (layar detail, ekspor) — bukan hanya di
    # saringan. Salah kode di satu berkas tidak boleh berubah menjadi angka yang tampak sah.
    jenis = jenis_emiten(potret, kode)
    if jenis != "bank_keuangan":
        return tidak_dihitung(
            nama,
            "bp",
            f"rasio bank hanya berlaku untuk bank & lembaga keuangan (PRD 8.4); jenis emiten ini "
            f"{jenis!r}, sehingga baris rasio-bank.csv untuk kode ini tidak dipakai",
        )
    terakhir, asal = _rasio_bank_terakhir(potret, kode)
    if terakhir is None:
        return tidak_dihitung(nama, "bp", asal)
    nilai = getattr(terakhir, kolom)
    if nilai is None:
        return tidak_dihitung(nama, "bp", f"rasio {nama} tidak dilaporkan pada {asal}")
    return hitung(nama, float(nilai), "bp", asal, "tidak ada data")


def npl_kotor(potret: Potret, kode: str) -> Nilai:
    return _nilai_rasio(potret, kode, "npl_kotor_bp", "npl_kotor")


def car(potret: Potret, kode: str) -> Nilai:
    return _nilai_rasio(potret, kode, "car_bp", "car")


def bopo(potret: Potret, kode: str) -> Nilai:
    return _nilai_rasio(potret, kode, "bopo_bp", "bopo")


def nim(potret: Potret, kode: str) -> Nilai:
    return _nilai_rasio(potret, kode, "nim_bp", "nim")


# ---------------------------------------------------------------------------------------
# Rakit: seluruh metrik satu emiten
# ---------------------------------------------------------------------------------------


def jenis_emiten(potret: Potret, kode: str) -> str:
    """Jenis emiten untuk pemilihan set metrik (8.4); 'umum' bila belum diklasifikasi."""
    daftar = potret.emiten.get(kode)
    return (daftar.jenis if daftar is not None and daftar.jenis else "umum")


def metrik_emiten(potret: Potret, kode: str) -> dict[str, Nilai]:
    """Seluruh metrik satu emiten, apa pun jenisnya — pemilihan set dilakukan di `saring.py`."""
    seri = seri_harga(potret, kode)
    nilai: dict[str, Nilai] = {
        # harga & likuiditas
        "harga": harga_terakhir(seri),
        "adtv20": adtv20(seri),
        "momentum_12_1": momentum_12_1(seri),
        "kekuatan_relatif_6b": kekuatan_relatif_6b(potret, seri),
        "volatilitas_60h": volatilitas_60h(seri),
        "atr14_persen": atr14_persen(seri),
        "jarak_52_minggu": jarak_52_minggu(seri),
        "ma50": ma50(seri),
        "ma200": ma200(seri),
        # fundamental umum
        "roe_5t": roe_5t(potret, kode),
        "cfo_ni": cfo_ni(potret, kode),
        "coverage": coverage(potret, kode),
        "der": der(potret, kode),
        "cagr_pendapatan": cagr_pendapatan(potret, kode),
        "per": per(potret, kode, seri),
        "per_normalisasi": per_normalisasi(potret, kode, seri),
        "pbv": pbv(potret, kode, seri),
        "ev_ebitda": ev_ebitda(potret, kode, seri),
        "imbal_hasil_laba_minus_sun": imbal_hasil_laba_minus_sun(potret, kode, seri),
        "imbal_hasil_dividen": imbal_hasil_dividen(potret, kode, seri),
        # set bank
        "npl_kotor": npl_kotor(potret, kode),
        "car": car(potret, kode),
        "bopo": bopo(potret, kode),
        "nim": nim(potret, kode),
    }
    nilai["tren_ma200"] = tren_ma200(seri, nilai["ma200"])

    kapitalisasi, asal, masalah = _kapitalisasi(potret, kode, seri)
    nilai["kapitalisasi_pasar"] = (
        tidak_dihitung("kapitalisasi_pasar", "rupiah", masalah or "tidak bisa dihitung")
        if kapitalisasi is None
        else hitung("kapitalisasi_pasar", kapitalisasi, "rupiah", asal, "tidak ada data")
    )
    return nilai


def metrik_semua(potret: Potret, kode: Iterable[str] | None = None) -> dict[str, dict[str, Nilai]]:
    """Metrik seluruh emiten pada potret. `kode` membatasi bila diisi."""
    daftar = tuple(kode) if kode is not None else potret.kode
    return {satu: metrik_emiten(potret, satu) for satu in daftar}


# ---------------------------------------------------------------------------------------
# Konteks pasar: breadth & rezim (PRD 8.2)
# ---------------------------------------------------------------------------------------

AMBANG_BREADTH_RISK_ON = 0.50
AMBANG_BREADTH_RISK_OFF = 0.40


def breadth(potret: Potret, semesta: Iterable[str]) -> Nilai:
    """Persentase emiten semesta likuid dengan penutupan di atas MA50."""
    nama = "breadth"
    dihitung = 0
    jumlah = 0
    for kode in semesta:
        seri = seri_harga(potret, kode)
        rerata = ma50(seri)
        acuan = harga_terakhir(seri)
        if not rerata.ada or not acuan.ada:
            continue
        jumlah += 1
        if float(acuan.nilai or 0) > float(rerata.nilai or 0):
            dihitung += 1
    if jumlah == 0:
        return tidak_dihitung(nama, "rasio", "tidak ada emiten likuid yang MA50-nya bisa dihitung")
    return hitung(nama, dihitung / jumlah, "rasio", f"{dihitung} dari {jumlah} emiten likuid", "tidak ada data")


def rezim_pasar(potret: Potret, nilai_breadth: Nilai) -> str:
    """RISK-ON / RISK-OFF / NETRAL menurut IHSG vs MA200 dan breadth (PRD 8.2).

    Bila salah satu bahan tidak bisa dihitung, hasilnya **NETRAL beserta alasannya** — memilih
    RISK-ON atau RISK-OFF tanpa dasar berarti menebak keadaan pasar.
    """
    indeks = potret.indeks.get(INDEKS_ACUAN, ())
    tutup = [float(satu.close) for satu in indeks if satu.close is not None]
    if len(tutup) < MA_PANJANG or not nilai_breadth.ada:
        return "NETRAL (dasar tidak lengkap)"
    rerata = rata_rata(tutup[-MA_PANJANG:])
    if rerata is None:
        return "NETRAL (MA200 IHSG tidak bisa dihitung)"
    di_atas = tutup[-1] > rerata
    lebar = float(nilai_breadth.nilai or 0)
    if di_atas and lebar >= AMBANG_BREADTH_RISK_ON:
        return "RISK-ON"
    if not di_atas and lebar < AMBANG_BREADTH_RISK_OFF:
        return "RISK-OFF"
    return "NETRAL"
