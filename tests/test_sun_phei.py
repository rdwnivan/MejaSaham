"""Uji pengambil imbal hasil SUN dari halaman HPW PHEI (PRD 7.1/8.2) — `mejasaham/sun.py`.

Yang diuji di sini bukan "unduhannya jalan", melainkan janji-janji yang membuat satu angka SUN
layak dipakai berhitung:

* **Tanggalnya dari sumbernya, bukan dari jam sistem.** Halaman PHEI menyatakan tanggal valuasi
  ("per 9-Oktober-2026"). Baris yang bertanggal tebakan lebih buruk daripada tidak ada baris
  (aturan keras 1/3) — jadi halaman yang tidak menyatakan tanggalnya **ditolak**, dan halaman yang
  menyatakan dua tanggal berbeda juga ditolak, bukan diringkas jadi satu.
* **Kolomnya dikenali dari kepalanya, bukan dari urutannya.** Tabel dicari dari kata `Tenor` dan
  `Today`; halaman yang menambah tabel baru tidak boleh menggeser arti kolomnya.
* **Angka di luar batas wajar ditolak**, bukan disimpan: kolom yang bergeser menghasilkan angka
  yang terlihat masuk akal di layar.
* **Berkas yang sudah ada tidak ditimpa.** Baris lain — termasuk suntingan tangan dan riwayat dari
  publikasi lain — dipertahankan; hanya baris `(tanggal, tenor)` yang sama yang diperbarui.
* **Bulat-balik lewat pembaca impor yang sebenarnya**: berkas yang ditulis pengambil ini harus
  terbaca `berkas.baca_folder`, dan teks asli sumbernya tersimpan sebagai jejak audit.

Seluruhnya berjalan **tanpa jaringan**: pembuka jaringan disuntikkan sebagai fungsi palsu, sama
seperti uji pengambil kalender KSEI.
"""

from __future__ import annotations

import urllib.error
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from mejasaham import berkas, sun
from mejasaham.ingesti import GalatIngesti

URL = "https://www.phei.co.id/Data/HPW-dan-Imbal-Hasil"
HARI_INI = date(2026, 10, 12)  # sengaja BEDA dari tanggal yang dinyatakan halaman
TANGGAL_SUMBER = date(2026, 10, 9)


# ---------------------------------------------------------------------------------------
# Piranti uji: halaman tiruan yang bentuknya seperti halaman PHEI
# ---------------------------------------------------------------------------------------


def _tabel(baris: list[tuple[str, str, str]]) -> str:
    isi = "".join(
        f"<tr><td>{tenor}</td><td>{today}</td><td>{kemarin}</td></tr>"
        for tenor, today, kemarin in baris
    )
    return (
        "<table><tr><th>Tenor Year</th><th>Today</th><th>Yesterday</th></tr>"
        f"{isi}</table>"
    )


def _halaman(
    *,
    tanggal: str = "per 9-Oktober-2026",
    tenor_10: str = "7,1845",
    tenor_10_kemarin: str = "7,1798",
    tambahan: str = "",
) -> str:
    """Halaman HPW tiruan: dua tabel tenor dan satu pernyataan tanggal, seperti aslinya."""
    return (
        "<html><body>"
        f"<div>Government Bond Benchmark {tanggal}</div>"
        + _tabel(
            [
                ("0,1", "6,3802", "6,3640"),
                ("1,0", "6,6032", "6,6116"),
                ("10,0", tenor_10, tenor_10_kemarin),
                ("15,0", "7,2173", "7,2109"),
            ]
        )
        + _tabel([("16,0", "7,2204", "7,2146"), ("40,0", "7,2356", "7,2376")])
        + tambahan
        + "</body></html>"
    )


class _Balasan:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_Balasan":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


def _pembuka(html: str, diminta: list[str] | None = None) -> Callable[[str, float], _Balasan]:
    def buka(url: str, timeout: float) -> _Balasan:
        if diminta is not None:
            diminta.append(url)
        return _Balasan(html.encode("utf-8"))

    return buka


# ---------------------------------------------------------------------------------------
# Penguraian
# ---------------------------------------------------------------------------------------


def test_membaca_tenor_10_beserta_tanggal_yang_dinyatakan_sumbernya() -> None:
    """Angka dan tanggalnya datang dari halaman, apa adanya.

    7,1845% disimpan sebagai `7.1845` (untuk berkas) **dan** sebagai teks asli `7,1845` (jejak
    audit). Dua-duanya perlu: yang pertama dipakai berhitung, yang kedua membuktikan angka yang
    dihitung memang angka yang dinyatakan sumbernya.
    """
    hasil = sun.urai_hpw(_halaman(), di_mana="uji", diakses=HARI_INI)

    assert hasil.tanggal == TANGGAL_SUMBER, "tanggal dari pernyataan halaman, bukan jam sistem"
    assert hasil.tenor_tahun == 10
    assert hasil.persen == Decimal("7.1845")
    assert hasil.teks_asli == "7,1845"
    assert "09 Okt 2026" in hasil.sumber
    assert "12 Okt 2026" in hasil.sumber, "tanggal akses ikut tercatat supaya bisa diperiksa"
    assert hasil.baris_csv()[2] == "7.1845", "berkas impor memakai titik desimal"


def test_kolom_dikenali_dari_kepala_tabel_bukan_urutan_tabel() -> None:
    """Tabel lain yang muncul lebih dulu tidak boleh menggeser arti kolomnya.

    Ditiru dengan menaruh tabel yang **juga** punya kolom `Tenor` tetapi tanpa `Today` di depan
    (mis. tabel kupon), lalu memastikan angkanya tetap diambil dari tabel yang benar.
    """
    lain = (
        "<table><tr><th>Series</th><th>Tenor Year</th><th>Kupon</th></tr>"
        "<tr><td>FR0109</td><td>10,0</td><td>6,8750</td></tr></table>"
    )
    hasil = sun.urai_hpw(_halaman(tambahan=lain), di_mana="uji")

    assert hasil.persen == Decimal("7.1845"), "bukan 6,8750 milik tabel kupon"


def test_halaman_tanpa_tanggal_valuasi_ditolak() -> None:
    """Tanpa tanggal dari sumbernya, satu-satunya tanggal yang tersisa adalah tebakan."""
    with pytest.raises(GalatIngesti, match="tidak menyatakan tanggal valuasi"):
        sun.urai_hpw(_halaman(tanggal=""), di_mana="uji")


def test_dua_tanggal_berbeda_ditolak_bukan_diringkas() -> None:
    """Halaman dengan dua bagian bertanggal berbeda tidak boleh diwakili satu tanggal."""
    html = _halaman() + "<div>Corporate Bond Benchmark per 10-Oktober-2026</div>"

    with pytest.raises(GalatIngesti) as galat:
        sun.urai_hpw(html, di_mana="uji")

    assert "2026-10-09" in str(galat.value) and "2026-10-10" in str(galat.value), (
        "pesannya harus menyebut kedua tanggalnya, supaya bisa diperiksa manusia"
    )


def test_nama_bulan_tak_dikenal_ditolak() -> None:
    with pytest.raises(GalatIngesti, match="nama bulan"):
        sun.urai_hpw(_halaman(tanggal="per 9-Okto-2026"), di_mana="uji")


def test_tanpa_tenor_yang_diminta_ditolak() -> None:
    """Tenor 10 tahun adalah yang disebut PRD 8.2; kalau tidak ada, tidak ada yang bisa dipakai."""
    html = "<html><body>per 9-Oktober-2026" + _tabel([("5,0", "6,9000", "6,8900")]) + "</body></html>"

    with pytest.raises(GalatIngesti, match="tidak ada baris tenor 10"):
        sun.urai_hpw(html, di_mana="uji")


def test_tenor_yang_muncul_dua_kali_ditolak() -> None:
    """Dua tabel yang sama-sama memuat tenor 10 membuat jawabannya tidak tunggal."""
    html = _halaman() + _tabel([("10,0", "7,5000", "7,4900")])

    with pytest.raises(GalatIngesti, match="muncul 2 kali"):
        sun.urai_hpw(html, di_mana="uji")


def test_kolom_today_bukan_angka_ditolak() -> None:
    """Sel yang bukan angka berarti kolomnya bergeser — bukan berarti nilainya kosong.

    Pesannya harus menyebut isi selnya, sebab dari pesan itu orang bisa tahu apakah halamannya
    berubah bentuk atau memang nilainya sedang kosong.
    """
    with pytest.raises(GalatIngesti) as galat:
        sun.urai_hpw(_halaman(tenor_10="-"), di_mana="uji")

    assert "tidak memuat dua kolom angka" in str(galat.value)
    assert "'-'" in str(galat.value), "isi sel yang bermasalah ikut ditampilkan"


def test_nilai_di_luar_batas_wajar_ditolak() -> None:
    """Kolom bergeser menghasilkan angka yang tetap terlihat masuk akal di layar.

    45% untuk SUN 10 tahun bukan angka yang mustahil secara matematis, tetapi mustahil sebagai
    imbal hasil SUN di pasar ini — dan menyimpannya berarti memakai angka yang salah tanpa jejak.
    """
    with pytest.raises(GalatIngesti, match="batas wajar"):
        sun.urai_hpw(_halaman(tenor_10="45,0000"), di_mana="uji")


def test_halaman_yang_bukan_hpw_ditolak() -> None:
    """Halaman login, galat, atau pemeliharaan tidak boleh terbaca sebagai "tidak ada data"."""
    with pytest.raises(GalatIngesti, match="tidak memuat tabel"):
        sun.urai_hpw("<html><body>Silakan masuk</body></html>", di_mana="uji")


# ---------------------------------------------------------------------------------------
# Menulis berkas
# ---------------------------------------------------------------------------------------


def test_menulis_berkas_baru_dari_template_lalu_terbaca_pembaca_impor(tmp_path: Path) -> None:
    """Bulat-balik lewat pembaca yang sebenarnya — bukan lewat pemeriksaan berkas sendiri.

    7,1845% menjadi **718 bp** karena kolom basis poin `INTEGER` (D-8) memotong, bukan membulatkan.
    Yang membuat pemotongan itu jujur adalah kolom jejak: teks asli `7,1845` ikut tersimpan.
    """
    hasil = sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman()), jeda=0.0)

    assert hasil.baris_baru == 1
    assert hasil.jumlah_baris_berkas == 1
    assert hasil.jalur == tmp_path / "imbal-hasil-sun.csv"

    terbaca = berkas.baca_folder(tmp_path)
    baris = terbaca.kumpulan.imbal_hasil_sun
    assert len(baris) == 1
    assert baris[0].tanggal == TANGGAL_SUMBER
    assert baris[0].tenor_tahun == 10
    assert baris[0].imbal_hasil_bp == 718, "7,1845% dipotong ke basis poin bulat"
    assert "7.1845" in (baris[0].imbal_hasil_mentah or ""), "angka yang dihitung ikut tercatat"
    assert "PHEI" in (baris[0].imbal_hasil_mentah or ""), "asal angkanya ikut tercatat"


def test_menjalankan_ulang_pada_tanggal_yang_sama_tidak_menambah_baris(tmp_path: Path) -> None:
    """Idempotensi: halaman PHEI menyajikan nilai harian, jadi jalan kedua memang tak menambah."""
    sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman()), jeda=0.0)
    kedua = sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman()), jeda=0.0)

    assert kedua.baris_baru == 0
    assert kedua.baris_tidak_berubah == 1
    assert kedua.jumlah_baris_berkas == 1
    assert any("tidak ada yang berubah" in satu for satu in kedua.peringatan)


def test_baris_lain_dan_suntingan_tangan_tidak_ditimpa(tmp_path: Path) -> None:
    """Berkas ini boleh dirawat tangan untuk mengisi riwayat yang tidak tersedia dari PHEI."""
    jalur = tmp_path / "imbal-hasil-sun.csv"
    jalur.write_text(
        "tanggal;tenor_tahun;imbal_hasil_persen;sumber\n"
        "# catatan tangan yang harus bertahan\n"
        "2026-09-30;10;6.7500;DJPPR (diisi tangan)\n",
        encoding="utf-8",
    )

    sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman()), jeda=0.0)

    isi = jalur.read_text(encoding="utf-8")
    assert "# catatan tangan yang harus bertahan" in isi
    assert "2026-09-30;10;6.7500;DJPPR (diisi tangan)" in isi
    assert "2026-10-09;10;7.1845;" in isi
    assert sun.ambil_sun(
        tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman()), jeda=0.0
    ).jumlah_baris_berkas == 2


def test_baris_dengan_kunci_sama_diperbarui_bukan_digandakan(tmp_path: Path) -> None:
    """Koreksi nilai pada tanggal yang sama menggantikan barisnya; basis data tetap append-only.

    Yang menyimpan riwayat revisi adalah basis data (`diketahui_pada`), bukan berkas ini —
    sedangkan dua baris berkunci sama di dalam **satu** berkas impor akan saling menimpa tanpa
    suara saat masuk.

    Yang diperiksa adalah **barisnya**, lewat pembaca impor yang sebenarnya — bukan seluruh teks
    berkas: berkas itu memang memuat penjelasan template, dan angka contoh di dalam penjelasan
    bukan data. Uji versi pertama memeriksa seluruh teks dan karena itu akan gagal (atau lolos)
    karena komentar, bukan karena datanya.
    """
    sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman()), jeda=0.0)
    kedua = sun.ambil_sun(
        tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman(tenor_10="7,2000")), jeda=0.0
    )

    assert kedua.baris_baru == 0
    assert kedua.baris_diperbarui == 1
    assert kedua.jumlah_baris_berkas == 1

    baris = berkas.baca_folder(tmp_path).kumpulan.imbal_hasil_sun
    assert len(baris) == 1, "koreksi menggantikan barisnya, bukan menambah baris kedua"
    assert baris[0].imbal_hasil_bp == 720, "7,2000% — nilai yang baru, bukan yang lama (718)"


def test_berkas_yang_tanggalnya_rusak_tidak_diperbaiki_diam_diam(tmp_path: Path) -> None:
    """Baris yang tanggalnya tidak berbentuk YYYY-MM-DD dipertahankan, bukan ditafsirkan."""
    jalur = tmp_path / "imbal-hasil-sun.csv"
    jalur.write_text(
        "tanggal;tenor_tahun;imbal_hasil_persen;sumber\n"
        "30/09/2026;10;6.7500;ditulis dengan format lain\n",
        encoding="utf-8",
    )

    sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman()), jeda=0.0)

    isi = jalur.read_text(encoding="utf-8")
    assert "30/09/2026;10;6.7500;ditulis dengan format lain" in isi, "barisnya tidak hilang"
    assert "2026-10-09;10;7.1845;" in isi


def test_gagal_unduh_menyebut_sebabnya(tmp_path: Path) -> None:
    """Kegagalan jaringan tidak boleh menjadi "tidak ada data SUN" yang tampak normal."""

    def buka_gagal(url: str, timeout: float) -> _Balasan:
        raise urllib.error.URLError("koneksi ditolak")

    with pytest.raises(GalatIngesti, match="gagal mengunduh"):
        sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=buka_gagal, jeda=0.0, percobaan=2)


def test_halaman_diminta_dari_alamat_hpw(tmp_path: Path) -> None:
    """Alamat sumbernya satu tempat; dipakai untuk mengunduh **dan** ditulis sebagai asal baris."""
    diminta: list[str] = []
    hasil = sun.ambil_sun(tmp_path, hari_ini=HARI_INI, buka=_pembuka(_halaman(), diminta), jeda=0.0)

    assert diminta == [sun.POLA_URL_HPW]
    assert "PHEI" in hasil.hasil.sumber
    assert sun.POLA_URL_HPW == URL, "alamat yang diuji harus alamat yang benar-benar dipakai"
