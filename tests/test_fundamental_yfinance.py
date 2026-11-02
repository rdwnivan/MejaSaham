"""Uji pemetaan laporan keuangan sumber → baris `fundamental` (K18), **tanpa jaringan**.

Yang diuji di sini bukan "apakah Yahoo menjawab", melainkan aturan yang menentukan apakah angka
yang dijawabnya boleh dipakai. Semuanya berasal dari pengukuran atas 60 emiten nyata 10 Okt 2026:

* **Nama baris arus kas tidak seragam.** Hanya 10% emiten memakai `Operating Cash Flow`; 78%
  memakai bentuk **metode langsung**. Kalau hanya nama pertama yang dikenali, mutu laba (CFO/NI)
  hilang untuk 90% emiten — dan hilangnya tanpa satu pun galat.
* **`info.sharesOutstanding` tidak dapat dipercaya** (17% berbeda >5% dari neraca). Jumlah saham
  harus datang dari neraca, dan itu diuji dengan menunjukkan `sharesOutstanding` **tidak dipakai**
  sama sekali: fungsinya bahkan tidak menerimanya.
* **Kegagalan tidak selalu berbentuk galat** — ada emiten yang membalas tabel kosong. Tabel kosong
  harus terbaca "tanpa laporan", bukan laporan berisi nol.
* **Mata uang tidak boleh ditebak.** 10 dari 60 emiten melapor dalam USD; menebaknya membuat
  seluruh rasio salah 16.000 kali tanpa satu pun tanda.
* **Tanggal publikasi tidak dinyatakan sumbernya**, jadi yang dipakai tanggal pengambilan — dan
  itu harus tercatat sebagai `tanggal_pengambilan`, bukan menyamar sebagai tanggal terbit.
"""

from __future__ import annotations

from datetime import date

import pytest

from mejasaham import pengambil
from mejasaham.ingesti import GalatIngesti

DIAMBIL = date(2026, 10, 10)
SUMBER = "yfinance/Yahoo Finance (tidak resmi); laporan keuangan tahunan; diakses 2026-10-10"


def _laporan(**baris: dict[date, object]) -> dict[str, dict[date, object]]:
    """Tabel laporan seperti yang dihasilkan `tabel_dari_laporan`."""
    return dict(baris)


def _petakan(
    tabel: dict[str, dict[date, object]], *, mata_uang: str | None = "IDR"
) -> pengambil.HasilFundamental:
    return pengambil.fundamental_dari_laporan(
        "AAAA", tabel, diambil_pada=DIAMBIL, mata_uang=mata_uang, sumber=SUMBER
    )


def test_tanpa_laporan_bukan_laporan_berisi_nol() -> None:
    """Sumber yang membalas tabel kosong harus terbaca "tidak ada laporan", bukan nol.

    Ini temuan yang paling mudah terlewat: 13 dari 60 emiten membalas kerangka kosong **tanpa
    exception**. Kalau keadaan itu diperlakukan sebagai laporan, emiten bermasalah akan tampak
    sebagai emiten dengan angka nol — dan nol itu ikut berhitung.
    """
    hasil = pengambil.tabel_dari_laporan(None, None, None)
    assert hasil == {}

    kosong = _petakan({})
    assert kosong.baris == ()
    assert kosong.gagal is not None
    assert "kosong" in kosong.gagal


def test_arus_kas_metode_langsung_dipakai_bila_nama_biasa_tidak_ada() -> None:
    """78% emiten memakai bentuk metode langsung; tanpa nama itu, CFO/NI hilang untuk 90%.

    Uji ini yang menjaga temuan itu: kalau `BARIS_LAPORAN['cfo']` kembali hanya memuat nama biasa,
    uji ini gagal — bukan diam-diam kehilangan satu metrik untuk hampir seluruh semesta.
    """
    tabel = _laporan(
        **{
            "Net Income": {date(2025, 12, 31): 10_000_000_000},
            "Stockholders Equity": {date(2025, 12, 31): 50_000_000_000},
            "Cash Flowsfromusedin Operating Activities Direct": {
                date(2025, 12, 31): 12_000_000_000
            },
        }
    )

    hasil = _petakan(tabel)

    assert hasil.gagal is None
    assert hasil.baris[0].cfo == 12_000_000_000


def test_arus_kas_nama_biasa_diprioritaskan_bila_keduanya_ada() -> None:
    """Bila sumber memuat keduanya, yang dipakai nama bakunya — urutan prioritas, bukan tebakan."""
    tabel = _laporan(
        **{
            "Net Income": {date(2025, 12, 31): 10_000_000_000},
            "Operating Cash Flow": {date(2025, 12, 31): 11_000_000_000},
            "Cash Flowsfromusedin Operating Activities Direct": {
                date(2025, 12, 31): 99_000_000_000
            },
        }
    )

    assert _petakan(tabel).baris[0].cfo == 11_000_000_000


def test_tanggal_publikasi_adalah_tanggal_pengambilan_dan_ditandai_begitu() -> None:
    """AC-15 tetap dijalankan tanpa mengarang tanggal: dipakai sejak diambil, dan itu dikatakan."""
    tabel = _laporan(
        **{"Net Income": {date(2025, 12, 31): 10_000_000_000}, "Total Revenue": {date(2025, 12, 31): 40_000_000_000}}
    )

    satu = _petakan(tabel).baris[0]

    assert satu.tgl_publikasi == DIAMBIL
    assert satu.asal_tgl_publikasi == "tanggal_pengambilan", (
        "tanpa penanda ini, laporan akan menyebut tanggal pengambilan sebagai tanggal terbit"
    )
    assert satu.periode == date(2025, 12, 31), "periode laporannya tetap apa adanya"
    assert satu.jenis_laporan == "tahunan"


def test_mata_uang_yang_tidak_dinyatakan_sumber_ditolak_bukan_ditebak() -> None:
    """16,7% emiten melapor dalam USD; menebak IDR membuat rasio salah 16.000 kali."""
    tabel = _laporan(**{"Net Income": {date(2025, 12, 31): 10_000_000_000}})

    hasil = _petakan(tabel, mata_uang=None)

    assert hasil.baris == (), "tidak ada baris yang ditulis"
    assert hasil.gagal is not None
    assert "mata uang" in hasil.gagal

    asing = _petakan(tabel, mata_uang="SGD")
    assert asing.baris == ()
    assert asing.gagal is not None


def test_mata_uang_usd_disimpan_apa_adanya() -> None:
    """Laporan USD tetap USD: metrik yang mencampurnya dengan harga rupiah jadi "tidak dihitung"."""
    tabel = _laporan(**{"Net Income": {date(2025, 12, 31): 1_000_000}})

    satu = _petakan(tabel, mata_uang="USD").baris[0]

    assert satu.mata_uang == "USD"
    assert satu.satuan_uang == "rupiah", "satuannya rupiah utuh: nilai sumber sudah satuan penuh"


def test_jumlah_saham_hanya_dari_neraca() -> None:
    """`info.sharesOutstanding` tidak dipakai sama sekali — buktinya, fungsinya tidak menerimanya."""
    tanpa_neraca = _laporan(**{"Net Income": {date(2025, 12, 31): 10_000_000_000}})
    assert _petakan(tanpa_neraca).baris[0].jumlah_saham is None

    dengan_neraca = _laporan(
        **{
            "Net Income": {date(2025, 12, 31): 10_000_000_000},
            "Ordinary Shares Number": {date(2025, 12, 31): 8_956_361_206},
        }
    )
    assert _petakan(dengan_neraca).baris[0].jumlah_saham == 8_956_361_206


def test_kolom_yang_tidak_boleh_negatif_dilepas_beserta_alasannya() -> None:
    """Nilai negatif di kolom yang dijaga CHECK berarti kolomnya tertukar — bukan disimpan.

    Barisnya tetap ditulis dengan kolom lain yang benar: yang salah adalah satu kolom, bukan
    seluruh laporannya. Yang penting: ada catatan yang menyebut kolom dan tahunnya.
    """
    tabel = _laporan(
        **{
            "Net Income": {date(2025, 12, 31): 10_000_000_000},
            "Total Revenue": {date(2025, 12, 31): -5_000_000_000},
        }
    )

    hasil = _petakan(tabel)

    assert hasil.baris[0].pendapatan is None
    assert hasil.baris[0].laba_induk == 10_000_000_000
    assert any("pendapatan" in satu and "negatif" in satu for satu in hasil.catatan)


def test_tahun_tanpa_angka_dilewati_bukan_ditulis_kosong() -> None:
    """Tahun yang seluruh angkanya kosong tidak menambah apa pun; menulisnya hanya menutupi data."""
    tabel = _laporan(
        **{
            "Net Income": {date(2025, 12, 31): 10_000_000_000, date(2024, 12, 31): None},
            "Total Revenue": {date(2025, 12, 31): 40_000_000_000},
        }
    )

    hasil = _petakan(tabel)

    assert [satu.periode for satu in hasil.baris] == [date(2025, 12, 31)]
    assert any("2024" in satu for satu in hasil.catatan)


def test_angka_berpecahan_yang_berarti_ditolak_berisik() -> None:
    """Pecahan yang berarti terhadap besarannya = kolomnya salah baca (T8), bukan dibulatkan."""
    tabel = _laporan(**{"Net Income": {date(2025, 12, 31): 1.5}})

    with pytest.raises(GalatIngesti, match="berpecahan"):
        _petakan(tabel)


def test_artefak_penyimpanan_dibulatkan_beserta_catatannya() -> None:
    """Nilai nyata dari sumber: 1.374.923.392.560,987 (MBSS 2022) — sisa 0,013 rupiah.

    Menolak seluruh emiten karena satu sel seperti ini membuang data yang sah; membulatkannya
    tanpa catatan menyembunyikan bahwa ada yang diubah. Dua-duanya dihindari di sini.
    """
    tabel = _laporan(**{"Total Revenue": {date(2022, 12, 31): 1374923392560.987}})

    hasil = _petakan(tabel)

    assert hasil.baris[0].pendapatan == 1374923392561
    assert any("dibulatkan" in satu and "2022" in satu for satu in hasil.catatan)


def test_nilai_bukan_angka_ditolak_menyebut_kolomnya() -> None:
    tabel = _laporan(**{"Net Income": {date(2025, 12, 31): "sepuluh miliar"}})

    with pytest.raises(GalatIngesti, match="bukan angka"):
        _petakan(tabel)


def test_nan_dibaca_sebagai_tidak_ada_data_bukan_angka() -> None:
    """Sel kosong pandas sering tiba sebagai NaN; itu "tidak ada datanya", bukan nol."""
    tabel = _laporan(
        **{
            "Net Income": {date(2025, 12, 31): 10_000_000_000},
            "Total Revenue": {date(2025, 12, 31): float("nan")},
        }
    )

    hasil = _petakan(tabel)

    assert hasil.baris[0].pendapatan is None
    assert hasil.baris[0].laba_induk == 10_000_000_000
