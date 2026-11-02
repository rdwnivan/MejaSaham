"""Uji definisi metrik PRD 8.2/8.4 (K10) — angka acuannya bisa diperiksa tangan.

Yang diuji di sini adalah definisi yang sudah dikunci di `docs/keputusan.md` 1.4. Satu-satunya
cara sebuah definisi bisa dipercaya adalah bila angkanya bisa dihitung ulang oleh manusia, jadi
setiap uji di bawah menuliskan perhitungannya di docstring dan menuntut angka yang **eksak** —
bukan "kira-kira mendekati":

* PER TTM dari laporan kuartalan **kumulatif** (AC-18): tahunan terakhir + YTD berjalan − YTD
  tahun lalu. Menjumlahkan kuartal apa adanya akan menghitung ganda.
* ROE 5 tahun = **median**; tahun buku dengan ekuitas ≤ 0 dilewati, bukan dianggap nol (P5).
* Volatilitas = simpangan baku **imbal hasil log** × √252 (P7); ATR14 memakai pemulusan
  **Wilder** (P8); jarak 52 minggu memakai **close** tertinggi (P9).
* Nilai tak bermakna → "tidak dihitung" beserta alasannya, bukan nol (P11, aturan keras 2).
* Penanda `penyesuaian_sumber` menentukan penyesuaian harga (K8/C10).
* Set bank diambil dari tabel `rasio_bank` (AC-16). `metrik_emiten` sengaja **tidak**
  menyembunyikan metrik menurut jenis emiten — pemilihan set dilakukan `saring.py` — sehingga
  yang diuji di sini adalah bahwa semuanya benar-benar bisa dihitung.

Seluruh data uji ditulis lewat jalur nyata (`ingesti.simpan` → `potret.muat`), bukan dengan
menyusun objek di memori: dengan begitu pembentukan baris `snapshot` dan `diketahui_pada` ikut
teruji. Deret harga dibangkitkan naik linear (2 rupiah per hari bursa) kecuali bila bentuk lain
justru yang membuat angkanya bisa dihitung tangan.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from fractions import Fraction
from math import log, sqrt
from pathlib import Path

import pytest

from mejasaham import db, ingesti, lokasi, metrik, potret
from mejasaham.ingesti import (
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    AksiKorporasi,
    Emiten,
    Fundamental,
    HargaHarian,
    KumpulanData,
    PenutupanIndeks,
    RasioBank,
)

SUMBER = "uji"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
#: Awal seluruh deret harga sintetis. Semua uji memakai hari bursa berurutan sebagai baris data
#: (P6: jendela metrik berbasis baris, bukan kalender), jadi kalender bursa tidak diperlukan.
HARI0 = date(2025, 1, 1)

#: Susunan modal uji ROE (P5). Angkanya dipilih supaya setiap ROE tahunan eksak:
#: ekuitas naik 1.000 → 2.500 dan laba 100 → 500, sehingga
#: 2021: 100 ÷ ((1.000+1.100)/2) = 2/21 · 2022: 200 ÷ 1.200 = 1/6 · 2023: 300 ÷ 1.450 = 6/29 ·
#: 2024: 400 ÷ 1.800 = 2/9 · 2025: 500 ÷ 2.250 = 2/9.
EKUITAS_PER_TAHUN = {2020: 1_000, 2021: 1_100, 2022: 1_300, 2023: 1_600, 2024: 2_000, 2025: 2_500}
LABA_PER_TAHUN = {2021: 100, 2022: 200, 2023: 300, 2024: 400, 2025: 500}


# ---------------------------------------------------------------------------------------
# Piranti uji
# ---------------------------------------------------------------------------------------


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Folder data di luar paket (A3), ditimpa lewat `MEJASAHAM_DATA` seperti di produksi."""
    folder = tmp_path / "data"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(folder))
    return folder


@pytest.fixture()
def sambungan(folder_data: Path) -> Iterator[sqlite3.Connection]:
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _simpan(
    sambungan: sqlite3.Connection,
    *,
    tanggal_data: date = TANGGAL,
    momen: datetime = MOMEN,
    **isi: object,
) -> int:
    """Tulis satu snapshot lewat jalur nyata dan kembalikan `id_snapshot`-nya."""
    kumpulan = KumpulanData(sumber=SUMBER, **isi)  # type: ignore[arg-type]
    return ingesti.simpan(
        sambungan, kumpulan, tanggal_data=tanggal_data, momen=momen
    ).id_snapshot


def _emiten(kode: str, **ubah: object) -> Emiten:
    return Emiten(kode=kode, nama=f"Emiten {kode}", sumber=SUMBER, **ubah)  # type: ignore[arg-type]


def _bar(
    kode: str, tanggal: date, close: int, *, volume: int = 1_000_000, **lain: object
) -> HargaHarian:
    return HargaHarian(kode=kode, tanggal=tanggal, close=close, volume=volume, **lain)  # type: ignore[arg-type]


def _deret(kode: str, mulai: int, jumlah: int, *, langkah: int = 2) -> tuple[HargaHarian, ...]:
    """Deret harga naik linear `langkah` rupiah per hari bursa.

    Bentuk inilah yang membuat nilai acuan bisa dihitung tangan: rata-rata 50 hari pertama,
    nilai tertinggi, dan selisihnya semuanya angka bulat.
    """
    return tuple(
        _bar(kode, HARI0 + timedelta(days=i), mulai + langkah * i) for i in range(jumlah)
    )


def _deret_pipih(kode: str, *, akhir: int, jumlah: int = 50) -> tuple[HargaHarian, ...]:
    """Harga datar 100 selama 49 hari bursa, lalu `akhir` pada hari terakhir.

    MA50-nya karena itu (49 x 100 + akhir) / 50: `akhir=110` menempatkan harga di atas MA50
    (110 > 100,2), sedangkan `akhir=100` membuatnya **tepat sama** dengan MA50 — dan "di atas"
    berarti lebih besar, bukan sama dengan.
    """
    return tuple(
        _bar(kode, HARI0 + timedelta(days=i), akhir if i == jumlah - 1 else 100)
        for i in range(jumlah)
    )


def _tahunan(kode: str, tahun: int, **angka: object) -> Fundamental:
    """Laporan tahunan yang terbit 31 Maret tahun berikutnya (kebiasaan laporan IDX)."""
    return Fundamental(
        kode=kode,
        periode=date(tahun, 12, 31),
        jenis_laporan="tahunan",
        tgl_publikasi=date(tahun + 1, 3, 31),
        **angka,  # type: ignore[arg-type]
    )


def _laporan_bank(kode: str = "BANK", tahun: tuple[int, ...] = (2022, 2023, 2024, 2025)) -> tuple[Fundamental, ...]:
    """Empat laporan tahunan bank yang seragam supaya setiap rasio acuannya eksak.

    Tiap tahun: laba 100 jt, ekuitas 1.000 jt, utang berbunga 500 jt, EBIT 200 jt, beban bunga
    50 jt, arus kas operasi 150 jt, penyusutan 30 jt → DER 0,5 · CFO/NI 450/300 = 1,5 ·
    coverage 200/50 = 4,0 · ROE 100/1.000 = 10%.
    """
    return tuple(
        _tahunan(
            kode,
            satu,
            laba_induk=100_000_000,
            ekuitas_induk=1_000_000_000,
            utang_bunga=500_000_000,
            kas=200_000_000,
            ebit=200_000_000,
            beban_bunga=50_000_000,
            cfo=150_000_000,
            da=30_000_000,
        )
        for satu in tahun
    )


def _terpilih(potret_uji: potret.Potret, kode: str) -> dict[tuple[date, str], Fundamental]:
    """Peta (periode, jenis laporan) → laporan: bentuk masukan publik `metrik.ttm`."""
    return {
        (satu.periode, satu.jenis_laporan): satu
        for satu in potret_uji.fundamental.get(kode, ())
    }


# ---------------------------------------------------------------------------------------
# AC-18: PER TTM dari laporan kuartalan kumulatif
# ---------------------------------------------------------------------------------------


def test_per_ttm_memakai_tahunan_plus_ytd_berjalan_minus_ytd_tahun_lalu(
    sambungan: sqlite3.Connection,
) -> None:
    """AC-18: laporan kuartalan IDX **kumulatif**, jadi 12 bulan terakhir tidak dijumlahkan.

    Dengan tahunan 2025 (laba 1.000 jt), YTD 30 Jun 2026 (700 jt), dan YTD 30 Jun 2025
    (400 jt), laba 12 bulan terakhir = 1.000 + 700 − 400 = 1.300 jt. Menjumlahkan YTD apa
    adanya akan memberi 1.700 jt — semester pertama 2025 terhitung dua kali.

    PER-nya ikut diuji karena di situlah angkanya dipakai: harga 260 ÷ (1.300 jt ÷ 100 jt
    lembar) = 260 ÷ 13 = 20.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("AAAA", jumlah_saham=100_000_000),),
        harga_harian=(_bar("AAAA", TANGGAL, 260),),
        fundamental=(
            _tahunan("AAAA", 2025, laba_induk=1_000_000_000),
            Fundamental(
                kode="AAAA",
                periode=date(2026, 6, 30),
                jenis_laporan="ytd_kumulatif",
                tgl_publikasi=date(2026, 6, 30),
                laba_induk=700_000_000,
            ),
            Fundamental(
                kode="AAAA",
                periode=date(2025, 6, 30),
                jenis_laporan="ytd_kumulatif",
                tgl_publikasi=date(2025, 6, 30),
                laba_induk=400_000_000,
            ),
        ),
    )
    potret_uji = potret.muat(sambungan)

    laba_ttm, asal = metrik.ttm(_terpilih(potret_uji, "AAAA"), "laba_induk")
    assert laba_ttm == 1_300_000_000, f"1.000 + 700 − 400 = 1.300 jt; yang dihitung: {asal}"

    nilai_per = metrik.per(potret_uji, "AAAA", metrik.seri_harga(potret_uji, "AAAA"))
    assert nilai_per.status == metrik.STATUS_DIHITUNG
    assert nilai_per.nilai == pytest.approx(20.0), "260 ÷ (1.300 jt ÷ 100 jt) = 260 ÷ 13 = 20"


def test_per_tidak_dihitung_bila_ytd_pembanding_tahun_lalu_belum_ada(
    sambungan: sqlite3.Connection,
) -> None:
    """Tanpa pembanding tahun lalu, 12 bulan terakhir tidak bisa dihitung — dan itu dikatakan.

    YTD 30 Jun 2026 (700 jt) baru bermakna sebagai "tambahan di atas tahunan 2025" bila semester
    pertama 2025 ikut dikurangkan. Menganggap pembanding yang tidak ada sebagai nol akan
    menaikkan laba TTM sebesar 400 jt tanpa satu pun tanda — persis tebakan yang dilarang
    aturan keras 2. Karena itu alasannya wajib menyebut pembandingnya, bukan sekadar "tidak ada
    data".
    """
    _simpan(
        sambungan,
        emiten=(_emiten("AAAA", jumlah_saham=100_000_000),),
        harga_harian=(_bar("AAAA", TANGGAL, 260),),
        fundamental=(
            _tahunan("AAAA", 2025, laba_induk=1_000_000_000),
            Fundamental(
                kode="AAAA",
                periode=date(2026, 6, 30),
                jenis_laporan="ytd_kumulatif",
                tgl_publikasi=date(2026, 6, 30),
                laba_induk=700_000_000,
            ),
        ),
    )
    potret_uji = potret.muat(sambungan)

    nilai_per = metrik.per(potret_uji, "AAAA", metrik.seri_harga(potret_uji, "AAAA"))

    assert nilai_per.status == metrik.STATUS_TIDAK_DIHITUNG
    assert nilai_per.nilai is None
    assert "pembanding" in (nilai_per.alasan or ""), (
        "alasan harus menyebut apa yang kurang: pembanding tahun lalu, bukan 'data tidak ada'"
    )


# ---------------------------------------------------------------------------------------
# AC-16: set metrik bank (PRD 8.4)
# ---------------------------------------------------------------------------------------


def test_emiten_bank_tetap_bisa_menghitung_der_cfo_ni_dan_coverage(
    sambungan: sqlite3.Connection,
) -> None:
    """AC-16: pemilihan set metrik dilakukan `saring.py`, bukan dengan menyembunyikan metrik.

    PRD 8.4 menetapkan DER, CFO/NI, dan coverage **tidak diterapkan** pada bank. Yang
    menerapkannya adalah kriteria saring (dan di sana pun keputusan itu diambil berdasarkan
    kolom `jenis`). Kalau `metrik_emiten` yang menyembunyikannya, dua hal rusak sekaligus:
    `saring.py` kehilangan bahan untuk memutuskan, dan tidak ada cara menguji bahwa bank
    benar-benar diukur dengan set bank — nilai yang tidak pernah dihitung tidak bisa dibedakan
    dari nilai yang dihitung lalu dibuang.

    Karena itu di sini ketiganya harus **dihitung**, dengan angka yang sudah bisa diperiksa:
    DER 500/1.000 = 0,5 · CFO/NI 450/300 = 1,5 · coverage 200/50 = 4,0.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("BANK", jenis="bank_keuangan", jumlah_saham=1_000_000_000),),
        harga_harian=(_bar("BANK", TANGGAL, 1_000),),
        fundamental=_laporan_bank(),
    )
    potret_uji = potret.muat(sambungan)
    nilai = metrik.metrik_emiten(potret_uji, "BANK")

    assert metrik.jenis_emiten(potret_uji, "BANK") == "bank_keuangan", (
        "jenis inilah yang dipakai saring.py untuk memilih set; ia harus terbaca apa adanya"
    )
    for nama, harapan in (("der", 0.5), ("cfo_ni", 1.5), ("coverage", 4.0)):
        assert nilai[nama].status == metrik.STATUS_DIHITUNG, f"{nama} harus tetap bisa dihitung"
        assert nilai[nama].nilai == pytest.approx(harapan), f"{nama} = {harapan}"


@pytest.mark.parametrize("nama", ["npl_kotor", "car", "bopo", "nim"])
def test_emiten_bank_tanpa_baris_rasio_bank_tidak_menghitung_rasio_banknya(
    sambungan: sqlite3.Connection, nama: str
) -> None:
    """Rasio bank hanya ada bila `rasio-bank.csv` sudah diimpor (Q6, aturan keras 2).

    NPL/CAR/BOPO/NIM tidak bisa dihitung dari laporan keuangan biasa, jadi tanpa tabelnya
    metrik ini memang tidak punya data. Yang tidak boleh terjadi adalah ia menjadi 0: NPL 0%
    berarti "tidak ada kredit bermasalah" — kesimpulan yang tidak didukung data apa pun, dan
    justru membuat bank tanpa data tampak paling sehat. Alasannya menyebut berkas yang harus
    diimpor supaya pengguna tahu apa yang kurang.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("BANK", jenis="bank_keuangan", jumlah_saham=1_000_000_000),),
        harga_harian=(_bar("BANK", TANGGAL, 1_000),),
        fundamental=_laporan_bank(),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.metrik_emiten(potret_uji, "BANK")[nama]

    assert nilai.status == metrik.STATUS_TIDAK_DIHITUNG
    assert nilai.nilai is None, "tanpa data bukan berarti nol"
    assert "rasio-bank.csv" in (nilai.alasan or ""), "alasan harus menyebut berkas yang belum diimpor"


def test_rasio_bank_mengisi_npl_car_bopo_nim_dalam_basis_poin(sambungan: sqlite3.Connection) -> None:
    """Sumber angka rasio bank adalah tabel `rasio_bank`, satuannya basis poin (T8, D-8).

    Nilainya diambil apa adanya dari periode terakhir yang **sudah diketahui** snapshot; uji ini
    memastikan angka itu benar-benar sampai ke metrik (250 bp = 2,5% NPL), bukan dibagi atau
    dikali lagi di perjalanan.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("BANK", jenis="bank_keuangan", jumlah_saham=1_000_000_000),),
        harga_harian=(_bar("BANK", TANGGAL, 1_000),),
        fundamental=_laporan_bank(),
        rasio_bank=(
            RasioBank(
                kode="BANK",
                periode=date(2025, 12, 31),
                tgl_publikasi=date(2026, 3, 31),
                npl_kotor_bp=250,
                car_bp=2_000,
                bopo_bp=7_000,
                nim_bp=500,
            ),
        ),
    )
    potret_uji = potret.muat(sambungan)
    nilai = metrik.metrik_emiten(potret_uji, "BANK")

    for nama, harapan in (
        ("npl_kotor", 250.0),
        ("car", 2_000.0),
        ("bopo", 7_000.0),
        ("nim", 500.0),
    ):
        assert nilai[nama].status == metrik.STATUS_DIHITUNG, f"{nama} harus terisi dari rasio_bank"
        assert nilai[nama].nilai == pytest.approx(harapan)
        assert nilai[nama].satuan == "bp"
        assert "2025-12-31" in nilai[nama].asal, "asal angkanya ikut dibawa (PRD 10)"


def test_butir_rasio_bank_yang_tidak_dilaporkan_tidak_dianggap_nol(
    sambungan: sqlite3.Connection,
) -> None:
    """Satu butir yang tidak dilaporkan bukan berarti nol, dan tidak menjatuhkan butir lain.

    Berkas rujukan boleh hanya memuat sebagian butir (CHECK tabelnya pun menuntut minimal satu).
    NIM yang tidak ada diisi 0 berarti "tidak menghasilkan margin bunga" — penilaian yang tidak
    berdasar; sementara NPL yang ada tetap harus terbaca.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("BANK", jenis="bank_keuangan", jumlah_saham=1_000_000_000),),
        harga_harian=(_bar("BANK", TANGGAL, 1_000),),
        rasio_bank=(
            RasioBank(
                kode="BANK",
                periode=date(2025, 12, 31),
                tgl_publikasi=date(2026, 3, 31),
                npl_kotor_bp=250,
                car_bp=2_000,
            ),
        ),
    )
    potret_uji = potret.muat(sambungan)
    nilai = metrik.metrik_emiten(potret_uji, "BANK")

    assert nilai["npl_kotor"].nilai == pytest.approx(250.0)
    assert nilai["car"].nilai == pytest.approx(2_000.0)
    for nama in ("bopo", "nim"):
        assert nilai[nama].status == metrik.STATUS_TIDAK_DIHITUNG
        assert nilai[nama].nilai is None
        assert "tidak dilaporkan" in (nilai[nama].alasan or "")


def test_emiten_non_bank_tidak_memakai_rasio_bank(sambungan: sqlite3.Connection) -> None:
    """PRD 8.4, AC-16: emiten non-bank diukur dengan metrik yang tersedia, bukan set bank.

    Yang menegakkan pembedaan ini adalah pemilihan set di `saring.py` (kriterianya memakai kolom
    `jenis`), sebab `metrik_emiten` sengaja mengembalikan seluruh metrik apa pun jenisnya.
    Karena itu yang bisa diuji di sini adalah bahannya: emiten non-bank tidak diklasifikasikan
    sebagai bank, dan rasio bank tidak muncul dari mana pun selain tabel `rasio_bank` — tanpa
    tabel itu keempatnya "tidak dihitung", bukan nol dan bukan angka karangan dari laporan
    keuangan biasa.

    Catatan batas: emiten non-bank yang baris `rasio_bank`-nya ada akan tetap mengembalikan
    angka itu di sini — pembuangannya terjadi di `saring.py`. Uji ini tidak menuntut sebaliknya
    supaya tidak mengklaim penjagaan yang memang bukan tugas modul ini.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("UMUM", jenis="umum", jumlah_saham=1_000_000_000),),
        harga_harian=(_bar("UMUM", TANGGAL, 1_000),),
        fundamental=_laporan_bank("UMUM"),
    )
    potret_uji = potret.muat(sambungan)
    nilai = metrik.metrik_emiten(potret_uji, "UMUM")

    assert metrik.jenis_emiten(potret_uji, "UMUM") == "umum", (
        "jenis inilah yang dipakai saring.py untuk tidak memilih kriteria bank"
    )
    for nama in ("npl_kotor", "car", "bopo", "nim"):
        assert nilai[nama].status == metrik.STATUS_TIDAK_DIHITUNG
        assert nilai[nama].nilai is None
        assert "rasio-bank.csv" in (nilai[nama].alasan or "")


# ---------------------------------------------------------------------------------------
# AC-3: metrik tanpa data berstatus "tidak dihitung" beserta alasannya
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("nama", ["roe_5t", "per", "adtv20"])
def test_metrik_tanpa_data_tidak_dihitung_dengan_alasan_yang_tidak_kosong(
    sambungan: sqlite3.Connection, nama: str
) -> None:
    """PRD 7.2, AC-3: metrik tanpa data "tidak dihitung" — bukan nol, bukan rata-rata sektor.

    Ketiga metrik ini kehilangan data dengan cara yang berbeda (tidak ada laporan sama sekali,
    tidak ada harga, dan harga yang ada belum cukup panjang), dan ketiganya harus menjawab dengan
    bentuk yang sama: status "tidak dihitung", `nilai` None, dan `alasan` yang bisa ditampilkan
    di layar detail maupun ekspor. Nol akan membuat emiten tanpa data tampak seperti emiten
    dengan angka buruk — dua hal yang berbeda dan menuntut tindakan yang berbeda pula.
    """
    _simpan(sambungan, emiten=(_emiten("KOSONG"),))
    potret_uji = potret.muat(sambungan)

    nilai = metrik.metrik_emiten(potret_uji, "KOSONG")[nama]

    assert nilai.status == metrik.STATUS_TIDAK_DIHITUNG
    assert nilai.nilai is None, "bukan 0: nilai yang tidak ada tidak boleh diganti angka"
    assert nilai.ada is False
    assert nilai.alasan and nilai.alasan.strip(), "alasan wajib ada supaya bisa ditampilkan"


# ---------------------------------------------------------------------------------------
# K8/C10: penanda penyesuaian sumber menentukan penyesuaian harga
# ---------------------------------------------------------------------------------------


def _deret_dengan_split(kode: str, penanda: str | None) -> tuple[HargaHarian, ...]:
    """50 baris harga pra-split 5.000 dan satu baris pasca-split 1.000 (split 1:5 di akhir).

    Seluruh baris memakai penanda yang sama supaya yang diuji benar-benar penandanya, bukan
    campuran baris bertanda dan tidak.
    """
    return tuple(
        _bar(
            kode,
            HARI0 + timedelta(days=i),
            5_000 if i < 50 else 1_000,
            penyesuaian_sumber=penanda,
        )
        for i in range(51)
    )


def _split(kode: str) -> AksiKorporasi:
    """Split 1:5 pada bar terakhir deret `_deret_dengan_split`."""
    return AksiKorporasi(
        kode=kode,
        tanggal=HARI0 + timedelta(days=50),
        jenis="split",
        rasio_lama=1,
        rasio_baru=5,
    )


def test_penanda_split_menghalangi_penyesuaian_kedua_kali(sambungan: sqlite3.Connection) -> None:
    """K8/C10: harga yang **sudah** disesuaikan sumber tidak boleh disesuaikan lagi.

    Data sumber (Yahoo) ternyata sudah memakai basis pascasplit — buktinya diukur dan dicatat di
    `docs/keputusan.md` 1.5 — sementara kolom aksi korporasi tetap melaporkan kejadian splitnya.
    Tanpa penanda per baris, split 1:5 diterapkan untuk kedua kali dan harga pra-split dibagi 5
    dua kali; momentumnya salah tanpa satu pun tanda di layar.

    Ujinya membandingkan dua emiten dengan baris harga dan aksi yang **sama persis**, berbeda
    hanya penandanya:

    * bertanda `split` → harga dibiarkan apa adanya: MA50 = (49 x 5.000 + 1.000) ÷ 50 = 4.920;
    * bertanda `tidak_disesuaikan` → penyesuaian diterapkan: 5.000 x 1/5 = 1.000, jadi MA50 =
      1.000.

    Kalau penandanya diabaikan, kedua emiten memberi angka yang sama — dan itulah yang membuat
    uji ini bermakna.
    """
    aksi = _split("AAAA")
    aksi_pembanding = _split("CCCC")
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=50),
        emiten=(_emiten("AAAA"), _emiten("CCCC")),
        harga_harian=_deret_dengan_split("AAAA", PENYESUAIAN_SPLIT)
        + _deret_dengan_split("CCCC", PENYESUAIAN_TIDAK_DISESUAIKAN),
        aksi_korporasi=(aksi, aksi_pembanding),
    )
    potret_uji = potret.muat(sambungan)

    sudah_disesuaikan_sumber = metrik.ma50(metrik.seri_harga(potret_uji, "AAAA"))
    belum_disesuaikan = metrik.ma50(metrik.seri_harga(potret_uji, "CCCC"))

    assert sudah_disesuaikan_sumber.nilai == pytest.approx(
        4_920.0
    ), "baris bertanda `split` tidak boleh disesuaikan lagi (49 x 5.000 + 1.000) ÷ 50 = 4.920"
    assert belum_disesuaikan.nilai == pytest.approx(
        1_000.0
    ), "baris bertanda `tidak_disesuaikan` justru harus disesuaikan: 5.000 x 1/5 = 1.000"


def test_baris_tanpa_penanda_membuat_metrik_harga_tidak_dihitung(
    sambungan: sqlite3.Connection,
) -> None:
    """K8/C10: penanda yang belum dinyatakan (NULL) tidak boleh ditebak.

    `NULL` berbeda dari "tidak disesuaikan": yang satu berarti "belum dinyatakan", yang lain
    "sumber belum menyesuaikan". Memilih salah satunya diam-diam berarti menebak, dan tebakan
    yang salah menghasilkan momentum yang salah tanpa jejak. Karena itu seluruh metrik harga
    berhenti dihitung — bukan hanya yang kebetulan terlihat aneh — dan alasannya menyebut kolom
    yang harus diisi supaya bisa diperbaiki.
    """
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=50),
        emiten=(_emiten("BBBB"),),
        harga_harian=_deret_dengan_split("BBBB", None),
        aksi_korporasi=(_split("BBBB"),),
    )
    potret_uji = potret.muat(sambungan)
    seri = metrik.seri_harga(potret_uji, "BBBB")
    nilai = metrik.metrik_emiten(potret_uji, "BBBB")

    assert seri.siap is False, "deret harga tanpa penanda tidak boleh dianggap siap dihitung"
    for nama in ("harga", "ma50", "adtv20"):
        assert nilai[nama].status == metrik.STATUS_TIDAK_DIHITUNG, f"{nama} harus berhenti dihitung"
        assert nilai[nama].nilai is None
        assert "penyesuaian_sumber" in (nilai[nama].alasan or ""), (
            f"alasan {nama} harus menyebut kolom penyesuaian_sumber yang belum diisi"
        )


# ---------------------------------------------------------------------------------------
# P5: ROE 5 tahun
# ---------------------------------------------------------------------------------------


def _laporan_roe(kode: str, ekuitas: dict[int, int]) -> tuple[Fundamental, ...]:
    """Laporan tahunan 2020–2025 dengan ekuitas dan laba seperti di `EKUITAS_PER_TAHUN`."""
    return tuple(
        _tahunan(
            kode,
            tahun,
            ekuitas_induk=satu_ekuitas,
            **({"laba_induk": LABA_PER_TAHUN[tahun]} if tahun in LABA_PER_TAHUN else {}),
        )
        for tahun, satu_ekuitas in ekuitas.items()
    )


def test_roe_lima_tahun_adalah_median_dari_roe_tahunan(sambungan: sqlite3.Connection) -> None:
    """P5: ROE 5 tahun = **median** ROE tahunan, bukan rata-rata.

    Rata-rata akan tertarik oleh satu tahun yang luar biasa; median justru itulah gunanya. Data
    ujinya memberi lima ROE yang berbeda — 2/21 ≈ 0,095 · 1/6 ≈ 0,167 · 6/29 ≈ 0,207 · 2/9 ≈
    0,222 · 2/9 ≈ 0,222 — sehingga nilai tengahnya (6/29) hanya bisa keluar dari median: rata-rata
    kelimanya ≈ 0,183, jauh dari angka mana pun di daftar.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("AAAA"),),
        fundamental=_laporan_roe("AAAA", EKUITAS_PER_TAHUN),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.roe_5t(potret_uji, "AAAA")

    assert nilai.status == metrik.STATUS_DIHITUNG
    assert nilai.nilai == pytest.approx(Fraction(6, 29)), "median dari lima ROE tahunan"
    assert "median 5 tahun buku" in nilai.asal


def test_tahun_buku_dengan_ekuitas_tidak_positif_dilewati_bukan_dianggap_nol(
    sambungan: sqlite3.Connection,
) -> None:
    """P5: ekuitas ≤ 0 membuat ROE tahun itu "tidak dihitung" — tahunnya dilewati, bukan dinolkan.

    Ekuitas negatif berarti laba dibagi ekuitas negatif menghasilkan ROE positif palsu; ekuitas
    nol tidak bisa dibagi sama sekali. Keduanya bukan "ROE 0", dan memperlakukannya sebagai 0
    akan menarik median ke bawah dengan angka yang tidak pernah terjadi.

    Di sini ekuitas 2023 dibuat −100: ROE 2023 batal (ekuitas akhir ≤ 0) dan ROE 2024 batal juga
    (ekuitas awalnya ≤ 0), sehingga yang tersisa 2/21, 1/6, dan 2/9 — mediannya 1/6. Kalau tahun
    yang batal dinolkan, mediannya akan menjadi 1/12, dan metriknya sendiri tetap harus
    **dihitung**: satu tahun yang tidak bisa dihitung tidak boleh menggagalkan seluruh metrik.
    """
    ekuitas = {**EKUITAS_PER_TAHUN, 2023: -100}
    _simpan(
        sambungan,
        emiten=(_emiten("AAAA"),),
        fundamental=_laporan_roe("AAAA", ekuitas),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.roe_5t(potret_uji, "AAAA")

    assert nilai.status == metrik.STATUS_DIHITUNG, "satu tahun batal bukan alasan menyerah"
    assert nilai.nilai == pytest.approx(Fraction(1, 6)), "median dari tiga tahun yang terhitung"
    assert "median 3 tahun buku" in nilai.asal, "jumlah tahun yang dipakai harus dicatat"


# ---------------------------------------------------------------------------------------
# P7/P8/P9: statistik harga
# ---------------------------------------------------------------------------------------


def test_volatilitas_60_hari_memakai_imbal_hasil_log_dan_disetahunkan_akar_252(
    sambungan: sqlite3.Connection,
) -> None:
    """P7: simpangan baku (ddof=1) imbal hasil **log** 60 hari × √252.

    Datanya sengaja hanya punya dua imbal hasil yang tidak nol: 100 → 110 → 100 pada dua hari
    terakhir. Sisanya 57 imbal hasil bernilai nol, sehingga rata-ratanya nol dan simpangan
    bakunya = √(2 x (ln 1,1)² ÷ 58) = ln 1,1 ÷ √29. Disetahunkan: ln 1,1 ÷ √29 × √252 ≈ 0,28096.

    Angka ini membedakan tiga kekeliruan sekaligus: imbal hasil sederhana (0,1 ÷ √29 × √252 ≈
    0,29479), lupa disetahunkan (≈ 0,01770), dan simpangan baku populasi (ddof=0, ≈ 0,27857) —
    ketiganya berbeda jauh lebih besar daripada toleransi uji ini.
    """
    tutup = [100] * 60
    tutup[58] = 110
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=59),
        emiten=(_emiten("AAAA"),),
        harga_harian=tuple(
            _bar("AAAA", HARI0 + timedelta(days=i), satu) for i, satu in enumerate(tutup)
        ),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.volatilitas_60h(metrik.seri_harga(potret_uji, "AAAA"))

    assert nilai.nilai == pytest.approx(log(1.1) / sqrt(29) * sqrt(252), rel=1e-9)


def test_atr14_memakai_pemulusan_wilder(sambungan: sqlite3.Connection) -> None:
    """P8: nilai pertama = rata-rata sederhana 14 rentang, lalu setiap rentang baru dilicinkan.

    16 baris harga disusun supaya rentang sebenarnya (TR) bisa dihitung tangan: 13 baris pertama
    ber-high 110 dan ber-low 90 dengan penutupan 100 (TR = 20), lalu dua baris terakhir ber-high
    190 dan ber-low 100 dengan penutupan 100 (TR = 90, karena |190 − 100| = 90).

    Wilder: ATR pertama = (13 x 20 + 90) ÷ 14 = 25, lalu satu langkah pelicinan
    (25 x 13 + 90) ÷ 14 = 415/14. Sebagai persen harga terakhir: (415/14) ÷ 100 = 83/280 ≈
    0,29643. Rata-rata sederhana 14 rentang terakhir akan memberi 0,30 dan rata-rata 15 rentang
    0,29333 — keduanya berbeda dari angka Wilder, jadi uji ini benar-benar menguji pemulusannya.
    """
    baris = [
        _bar("AAAA", HARI0 + timedelta(days=i), 100, high=110, low=90) for i in range(14)
    ] + [_bar("AAAA", HARI0 + timedelta(days=i), 100, high=190, low=100) for i in (14, 15)]
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=15),
        emiten=(_emiten("AAAA"),),
        harga_harian=tuple(baris),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.atr14_persen(metrik.seri_harga(potret_uji, "AAAA"))

    assert nilai.nilai == pytest.approx(83 / 280, rel=1e-12), "ATR Wilder (415/14) ÷ 100"


def test_jarak_52_minggu_memakai_close_tertinggi_bukan_high(sambungan: sqlite3.Connection) -> None:
    """P9: pembandingnya adalah **close** tertinggi 252 hari bursa, bukan high tertinggi.

    Data ujinya naik 2 rupiah per hari sampai 1.250 (hari ke-126), lalu turun 2 rupiah per hari
    sampai 998. Satu baris — tepat di puncak — diberi high 6.000, jauh di atas semua penutupan.

    Dengan close tertinggi (1.250): 998 ÷ 1.250 − 1 = −0,2016. Kalau high yang dipakai, hasilnya
    akan −0,8337: saham yang hanya 20% di bawah puncaknya tampak 83% di bawah puncaknya, dan
    saringan "jarak 52 minggu ≥ −25%" akan membuangnya tanpa alasan.
    """
    baris = []
    for i in range(252):
        close = 1_000 + 2 * i if i <= 125 else 1_250 - 2 * (i - 125)
        baris.append(
            _bar(
                "AAAA",
                HARI0 + timedelta(days=i),
                close,
                high=6_000 if i == 125 else close + 100,
                low=close - 100,
            )
        )
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=251),
        emiten=(_emiten("AAAA"),),
        harga_harian=tuple(baris),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.jarak_52_minggu(metrik.seri_harga(potret_uji, "AAAA"))

    assert nilai.nilai == pytest.approx(998 / 1_250 - 1, rel=1e-12), "998 ÷ 1.250 − 1 = −0,2016"


# ---------------------------------------------------------------------------------------
# P11: nilai yang tidak bermakna tidak dihitung
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("laba", [0, -500])
def test_per_tidak_dihitung_bila_laba_dua_belas_bulan_tidak_positif(
    sambungan: sqlite3.Connection, laba: int
) -> None:
    """P11: PER dengan laba ≤ 0 tidak bermakna, jadi "tidak dihitung" — bukan 0.

    Laba nol membuat pembagiannya tidak terdefinisi; laba negatif menghasilkan PER negatif yang,
    kalau ikut diperingkat, akan tampak **paling murah** justru pada perusahaan yang merugi.
    Alasannya menyebut P11 supaya keputusan ini bisa ditelusuri sampai ke `docs/keputusan.md`.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("AAAA", jumlah_saham=1_000),),
        harga_harian=(_bar("AAAA", TANGGAL, 1_000),),
        fundamental=(_tahunan("AAAA", 2025, laba_induk=laba, ekuitas_induk=10_000),),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.per(potret_uji, "AAAA", metrik.seri_harga(potret_uji, "AAAA"))

    assert nilai.status == metrik.STATUS_TIDAK_DIHITUNG
    assert nilai.nilai is None
    assert "P11" in (nilai.alasan or "")


@pytest.mark.parametrize("ekuitas", [0, -500])
def test_pbv_tidak_dihitung_bila_ekuitas_tidak_positif(
    sambungan: sqlite3.Connection, ekuitas: int
) -> None:
    """P11/P5: PBV dengan ekuitas ≤ 0 tidak bermakna.

    Nilai buku per saham dari ekuitas nol tidak terdefinisi, dan dari ekuitas negatif memberi PBV
    negatif yang terbaca seolah sahamnya dijual di bawah nilai buku. Keduanya harus berhenti
    dihitung dengan alasan yang menyebut ekuitasnya.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("AAAA", jumlah_saham=1_000),),
        harga_harian=(_bar("AAAA", TANGGAL, 1_000),),
        fundamental=(_tahunan("AAAA", 2025, laba_induk=500, ekuitas_induk=ekuitas),),
    )
    potret_uji = potret.muat(sambungan)

    nilai = metrik.pbv(potret_uji, "AAAA", metrik.seri_harga(potret_uji, "AAAA"))

    assert nilai.status == metrik.STATUS_TIDAK_DIHITUNG
    assert nilai.nilai is None
    assert "ekuitas" in (nilai.alasan or "")


# ---------------------------------------------------------------------------------------
# Konteks pasar: breadth & rezim (PRD 8.2)
# ---------------------------------------------------------------------------------------


def test_breadth_hanya_menghitung_emiten_dalam_semesta_yang_diberikan(
    sambungan: sqlite3.Connection,
) -> None:
    """Breadth = persentase emiten **semesta yang diberikan** dengan penutupan di atas MA50.

    Semesta likuid ditentukan di tempat lain (P1: ADTV20 ≥ Rp 5 miliar dan lolos pengecualian),
    jadi `breadth` tidak boleh menyimpulkan semestanya sendiri dari seluruh isi potret. Data
    ujinya memuat empat emiten: AAAA (110 > MA50 100,2), BBBB (130 > 100,6), dan CCCC (100, tepat
    **sama** dengan MA50-nya, jadi tidak dihitung "di atas"), sedangkan DDDD (150) ada di luar
    semesta.

    Semesta (AAAA, BBBB, CCCC) karena itu memberi 2 dari 3 = 2/3: CCCC ikut ke penyebut walau
    tidak dihitung pembilangnya, dan DDDD tidak ikut sama sekali. Semesta (AAAA) saja memberi 1,0
    — buktinya DDDD tidak menyelinap masuk; semesta (CCCC) memberi 0,0, yang tetap nilai yang
    sah dan bukan "tidak dihitung".
    """
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=49),
        emiten=(_emiten("AAAA"), _emiten("BBBB"), _emiten("CCCC"), _emiten("DDDD")),
        harga_harian=(
            _deret_pipih("AAAA", akhir=110)
            + _deret_pipih("BBBB", akhir=130)
            + _deret_pipih("CCCC", akhir=100)
            + _deret_pipih("DDDD", akhir=150)
        ),
    )
    potret_uji = potret.muat(sambungan)

    luas = metrik.breadth(potret_uji, ("AAAA", "BBBB", "CCCC"))
    assert luas.nilai == pytest.approx(2 / 3)
    assert "2 dari 3" in luas.asal, "penyebutnya hanya emiten di dalam semesta"

    assert metrik.breadth(potret_uji, ("AAAA",)).nilai == pytest.approx(1.0), (
        "DDDD di atas MA50 tetapi di luar semesta, jadi tidak boleh ikut terhitung"
    )
    assert metrik.breadth(potret_uji, ("CCCC",)).nilai == pytest.approx(0.0), (
        "harga tepat di MA50 bukan 'di atas MA50'; nol di sini nilai yang sah"
    )


def test_rezim_pasar_netral_bila_breadth_tidak_tersedia(sambungan: sqlite3.Connection) -> None:
    """PRD 8.2: tanpa breadth, rezimnya NETRAL — RISK-ON tidak boleh ditebak dari IHSG saja.

    IHSG di sini naik (6.199 di atas MA200 6.099,5) dan breadth semesta tersedia 1,0, sehingga
    syarat RISK-ON terpenuhi. Begitu breadth tidak bisa dihitung (semesta kosong), satu-satunya
    jawaban jujur adalah "NETRAL (dasar tidak lengkap)": menyebut pasar RISK-ON tanpa tahu
    seberapa luas kenaikannya berarti menebak keadaan pasar, dan keputusan posisi yang mengikuti
    tebakan itu tidak bisa dipertanggungjawabkan.
    """
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=199),
        emiten=(_emiten("AAAA"),),
        harga_harian=_deret_pipih("AAAA", akhir=110),
        harga_indeks=tuple(
            PenutupanIndeks(indeks="IHSG", tanggal=HARI0 + timedelta(days=i), close=6_000 + i)
            for i in range(200)
        ),
    )
    potret_uji = potret.muat(sambungan)

    assert metrik.rezim_pasar(potret_uji, metrik.breadth(potret_uji, ("AAAA",))) == "RISK-ON", (
        "dengan kedua bahan lengkap, syarat RISK-ON memang terpenuhi"
    )
    assert metrik.rezim_pasar(potret_uji, metrik.breadth(potret_uji, ())) == (
        "NETRAL (dasar tidak lengkap)"
    ), "breadth yang tidak bisa dihitung harus membuat rezimnya NETRAL beserta alasannya"


def test_rezim_pasar_netral_bila_ma200_ihsg_belum_tersedia(sambungan: sqlite3.Connection) -> None:
    """PRD 8.2: MA200 IHSG yang belum bisa dihitung juga membuat rezimnya NETRAL.

    199 baris indeks belum cukup untuk MA200 (P6: 252 hari bursa = 12 bulan, MA200 = 200 baris).
    Memakai rata-rata dari 199 baris yang ada akan menghasilkan "MA200" yang sebenarnya bukan
    MA200 — angka yang tampak sah tetapi mengukur hal lain.
    """
    _simpan(
        sambungan,
        tanggal_data=HARI0 + timedelta(days=198),
        emiten=(_emiten("AAAA"),),
        harga_harian=_deret_pipih("AAAA", akhir=110),
        harga_indeks=tuple(
            PenutupanIndeks(indeks="IHSG", tanggal=HARI0 + timedelta(days=i), close=6_000 + i)
            for i in range(199)
        ),
    )
    potret_uji = potret.muat(sambungan)

    lebar = metrik.breadth(potret_uji, ("AAAA",))
    assert lebar.ada is True, "breadth-nya sendiri tersedia; yang kurang hanya MA200 IHSG"

    assert metrik.rezim_pasar(potret_uji, lebar) == "NETRAL (dasar tidak lengkap)"
