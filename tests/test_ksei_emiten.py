"""Uji jalur daftar emiten dari Master File Efek KSEI (`mejasaham/ksei.py`).

Yang diuji di sini bukan "apakah unduhannya jalan", melainkan janji-janji yang membuat daftar
emiten layak jadi semesta berhitung:

* hanya **saham biasa IDX yang aktif** yang masuk — efek lain dilewati, dan jumlah yang dilewati
  dilaporkan, bukan dibuang diam-diam;
* saham **preferen/seri** (ISIN `ID2…`) tidak ikut, dan pengeluarannya terlihat di laporan;
* kolom yang tidak ada di berkas KSEI (sektor IDX-IC, papan, jenis, free float, status notasi)
  tetap **kosong** — bukan diisi pendekatan, karena menukar "komposisi kepemilikan" dengan
  "free float" menghasilkan metrik yang salah tanpa terlihat salah;
* berkas yang bentuknya berubah (kepala hilang kolom, jumlah kolom beda, kode ganda, tanggal
  campur) **menolak**, bukan menghasilkan daftar setengah benar;
* `emiten.csv` yang ditulis bisa dibaca ulang oleh pembaca yang sama dengan yang dipakai
  `--refresh` — itu buktinya, bukan klaimnya.

Seluruh uji berjalan **tanpa jaringan**: pengunduh disuntikkan sebagai fungsi palsu.
"""

from __future__ import annotations

import io
import urllib.error
import zipfile
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

import pytest

from mejasaham import berkas, ksei
from mejasaham.ingesti import GalatIngesti

HARI_INI = date(2026, 10, 9)
TANGGAL_MASTER = date(2026, 9, 30)

#: Kepala berkas KSEI apa adanya (28 kolom). Ditulis lengkap supaya uji ini gagal kalau bentuk
#: berkas sumber berubah, bukan diam-diam menyesuaikan diri.
KOLOM_KSEI = (
    "Date",
    "Code",
    "Description",
    "Type",
    "Isin Code",
    "Issuer",
    "Status",
    "Stock Exchange",
    "Listing Date",
    "Currency",
    "Form",
    "Eff. Date Isin",
    "Maturity Date",
    "Expire Date",
    "Exercise Price",
    "Interest",
    "Interest Type",
    "Interest Freq",
    "Nominal Value",
    "Num. of Sec",
    "Originated Amt",
    "Current Amt",
    "Total Scripless",
    "Local (%)",
    "Foreign (%)",
    "Total (%)",
    "Sector",
    "Closing Price",
)


#: Nama kolom KSEI yang mengandung spasi/titik tidak bisa dipakai sebagai nama argumen Python;
#: padanannya ditulis di sini supaya uji tetap menyebut kolom sumbernya, bukan indeksnya.
ALIAS_KOLOM = {
    "Stock_Exchange": "Stock Exchange",
    "Num_of_Sec": "Num. of Sec",
    "Isin_Code": "Isin Code",
    "Listing_Date": "Listing Date",
    "Closing_Price": "Closing Price",
}


def _baris(**nilai: str) -> str:
    """Satu baris KSEI; kolom yang tidak disebut dibiarkan kosong seperti di berkas aslinya."""
    isi = {nama: "" for nama in KOLOM_KSEI}
    for nama, isinya in nilai.items():
        isi[ALIAS_KOLOM.get(nama, nama)] = isinya
    return "|".join(isi[nama] for nama in KOLOM_KSEI)


def _saham(kode: str, nama: str, **ubah: str) -> str:
    """Saham biasa IDX yang aktif — bentuk yang seharusnya masuk semesta."""
    nilai = {
        "Date": "30-SEP-2026",
        "Code": kode,
        "Description": nama,
        "Type": "EQUITY",
        "Isin Code": f"ID1000{kode[:4]}",
        "Issuer": nama,
        "Status": "ACTIVE",
        "Stock Exchange": "IDX",
        "Listing Date": "25-NOV-1989",
        "Currency": "IDR",
        "Num. of Sec": "1000000",
        "Sector": "COMPUTER AND SERVICES",
        "Closing Price": "1234",
    }
    nilai.update(ubah)
    return _baris(**nilai)


def _berkas(*baris: str, kepala: str | None = None) -> str:
    return "\n".join([kepala if kepala is not None else "|".join(KOLOM_KSEI), *baris]) + "\n"


def _zip(teks: str, nama: str = "StatisEfek20260930.txt") -> bytes:
    penampung = io.BytesIO()
    with zipfile.ZipFile(penampung, "w") as zipnya:
        zipnya.writestr(nama, teks)
    return penampung.getvalue()


class _Balasan:
    """Pengganti balasan `urlopen`: cukup punya `read()` dan bisa dipakai `with`."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_Balasan":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


def _pembuka(
    isi: Mapping[str, bytes], diminta: list[str]
) -> Callable[[str, float], _Balasan]:
    """Pembuka palsu: URL yang tidak ada dalam `isi` dijawab 404 seperti KSEI."""

    def buka(url: str, timeout: float) -> _Balasan:
        diminta.append(url)
        if url not in isi:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]
        return _Balasan(isi[url])

    return buka


# ---------------------------------------------------------------------------------------
# Penguraian: apa yang masuk, apa yang tidak
# ---------------------------------------------------------------------------------------


def test_hanya_saham_biasa_idx_aktif_yang_masuk() -> None:
    teks = _berkas(
        _saham("AAAA", "Alpha Sentosa Tbk"),
        _baris(  # obligasi korporasi
            Date="30-SEP-2026",
            Code="IIFF02BCN3",
            Description="OBLIGASI BERKELANJUTAN",
            Type="CORPORATE BOND",
            Status="ACTIVE",
            Stock_Exchange="IDX",
        ),
        _saham("BBBB", "Beta Mandiri Tbk"),
        _saham("CCCC", "Gamma Luar Tbk", Stock_Exchange="SGX"),
        _saham("DDDD", "Delta Suspensi Tbk", Status="INACTIVE"),
    )
    hasil = ksei.urai_master_efek(teks)

    assert [satu.kode for satu in hasil.baris] == ["AAAA", "BBBB"]
    assert hasil.dilewati_bukan_equity == 1
    assert hasil.dilewati_bukan_idx == 1
    assert hasil.dilewati_tidak_aktif == 1
    assert hasil.tanggal == TANGGAL_MASTER


def test_saham_preferen_dan_seri_dikeluarkan_dan_dilaporkan() -> None:
    """Kelas lain bukan saham biasa: tidak masuk semesta, tetapi tidak hilang tanpa kabar."""
    teks = _berkas(
        _saham("AAAA", "Alpha Sentosa Tbk"),
        _saham("MAMIP", "MAS MURNI INDONESIA Tbk PREFEREN", Isin_Code="ID2000052903"),
        _saham("MYRXP", "HANSON INTERNATIONAL Tbk - SERI B", Isin_Code="ID2000061706"),
    )
    hasil = ksei.urai_master_efek(teks)

    assert [satu.kode for satu in hasil.baris] == ["AAAA"]
    assert dict(hasil.kelas_lain) == {"MAMIP": "preferen/seri", "MYRXP": "preferen/seri"}
    assert hasil.kode_tak_lazim == ()  # yang dikeluarkan tidak ikut dilaporkan sebagai "ditulis"
    assert "MAMIP" in str(hasil)
    assert "preferen/seri" in str(hasil)


def test_kelas_efek_yang_tidak_dikenal_ditolak() -> None:
    """ISIN di luar ID1/ID2 berarti kelas yang belum diperiksa — jangan dimasukkan diam-diam."""
    teks = _berkas(_saham("AAAA", "Alpha Sentosa Tbk", Isin_Code="US1234567890"))

    with pytest.raises(GalatIngesti, match="ISIN"):
        ksei.urai_master_efek(teks)


def test_kode_luar_pola_empat_huruf_dilaporkan_tetapi_tetap_ditulis() -> None:
    """`GOTOM` (saham bervoting ganda) sah: ditulis, tetapi terlihat di laporan."""
    hasil = ksei.urai_master_efek(_berkas(_saham("GOTOM", "MVS GOTO GOJEK TOKOPEDIA Tbk")))

    assert [satu.kode for satu in hasil.baris] == ["GOTOM"]
    assert hasil.kode_tak_lazim == ("GOTOM",)


def test_tanggal_ksei_diurai_tanpa_bergantung_locale() -> None:
    """Singkatan bulan Inggris dipetakan sendiri; `%b` bergantung locale mesin."""
    hasil = ksei.urai_master_efek(_berkas(_saham("AAAA", "Alpha Tbk", Listing_Date="01-MAY-2020")))

    assert hasil.baris[0].tanggal_pencatatan == date(2020, 5, 1)


def test_tanggal_pencatatan_kosong_menjadi_none_bukan_tanggal_karangan() -> None:
    hasil = ksei.urai_master_efek(_berkas(_saham("AAAA", "Alpha Tbk", Listing_Date="")))

    assert hasil.baris[0].tanggal_pencatatan is None


def test_tanggal_yang_tidak_dikenali_ditolak() -> None:
    with pytest.raises(GalatIngesti, match="tidak dikenali"):
        ksei.urai_master_efek(_berkas(_saham("AAAA", "Alpha Tbk", Listing_Date="30/09/2026")))


def test_jumlah_saham_bukan_angka_ditolak() -> None:
    with pytest.raises(GalatIngesti, match="Num. of Sec"):
        ksei.urai_master_efek(_berkas(_saham("AAAA", "Alpha Tbk", Num_of_Sec="1.000.000")))


# ---------------------------------------------------------------------------------------
# Berkas yang berubah bentuk harus menolak, bukan menghasilkan daftar setengah benar
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("hilang", ["Code", "Num. of Sec", "Stock Exchange", "Status"])
def test_kepala_tanpa_kolom_wajib_ditolak(hilang: str) -> None:
    kepala = "|".join(nama for nama in KOLOM_KSEI if nama != hilang)

    with pytest.raises(GalatIngesti, match=hilang.replace(" ", r"\ ")):
        ksei.urai_master_efek(_berkas(_saham("AAAA", "Alpha Tbk"), kepala=kepala))


def test_baris_dengan_jumlah_kolom_beda_ditolak() -> None:
    teks = _berkas(_saham("AAAA", "Alpha Tbk"), "30-SEP-2026|BBBB|Beta Tbk|EQUITY")

    with pytest.raises(GalatIngesti, match="baris 3"):
        ksei.urai_master_efek(teks)


def test_kode_ganda_ditolak() -> None:
    teks = _berkas(_saham("AAAA", "Alpha Sentosa Tbk"), _saham("AAAA", "Alpha Lain Tbk"))

    with pytest.raises(GalatIngesti, match="lebih dari sekali"):
        ksei.urai_master_efek(teks)


def test_berkas_tanpa_saham_sama_sekali_ditolak() -> None:
    """Menulis berkas kosong akan membuat --refresh berhenti tanpa sebab yang jelas."""
    teks = _berkas(
        _baris(Date="30-SEP-2026", Code="IIFF02BCN3", Type="CORPORATE BOND", Status="ACTIVE")
    )

    with pytest.raises(GalatIngesti, match="tidak ada satu pun saham biasa"):
        ksei.urai_master_efek(teks)


def test_berkas_kosong_ditolak() -> None:
    with pytest.raises(GalatIngesti, match="kosong"):
        ksei.urai_master_efek("")


def test_tanggal_data_campur_ditolak() -> None:
    """Satu berkas = satu tanggal data; berkas campuran merusak point-in-time (PRD 7.2)."""
    teks = _berkas(
        _saham("AAAA", "Alpha Tbk"),
        _saham("BBBB", "Beta Tbk", Date="29-SEP-2026"),
    )

    with pytest.raises(GalatIngesti, match="satu tanggal"):
        ksei.urai_master_efek(teks)


# ---------------------------------------------------------------------------------------
# Catatan yang terbelah di berkas sumber (kejadian nyata: baris 3619–3620 berkas 30 Sep 2026)
# ---------------------------------------------------------------------------------------


def _berkas_dengan_baris_terbelah(baris: str, *, pada: str) -> str:
    """Susun berkas yang satu catatannya patah di tengah kolom, seperti berkas KSEI aslinya."""
    potong = baris.index(pada)
    return (
        "\n".join(
            [
                "|".join(KOLOM_KSEI),
                _saham("AAAA", "Alpha Sentosa Tbk"),
                baris[:potong].rstrip(),
                baris[potong:],
            ]
        )
        + "\n"
    )


def test_catatan_yang_terbelah_disambung_dan_dilaporkan() -> None:
    """Penyambungan hanya diterima kalau jumlah kolomnya kembali tepat — dan selalu dilaporkan."""
    sukuk = _baris(
        Date="30-SEP-2026",
        Code="AGLG01X9SCFS",
        Description="SUKUK MUSYARAKAH BERKELANJUTAN CV AMANAH GEMILANG LOGISTIK TAHAP IX TAHUN 2025",
        Type="SUKUK CROWD FUNDING",
        Isin_Code="IDZ000062100",
        Status="ACTIVE",
        Sector="TRANSPORTATION",
    )
    hasil = ksei.urai_master_efek(_berkas_dengan_baris_terbelah(sukuk, pada="LOGISTIK TAHAP"))

    assert [satu.kode for satu in hasil.baris] == ["AAAA"]
    assert hasil.dilewati_bukan_equity == 1  # catatan sukuk itu terbaca utuh, lalu dilewati
    assert hasil.baris_tersambung == ((3, 4),)
    assert "terbelah" in str(hasil)


def test_baris_terbelah_yang_tetap_tidak_utuh_ditolak() -> None:
    teks = "\n".join(
        ["|".join(KOLOM_KSEI), _saham("AAAA", "Alpha Tbk"), "30-SEP-2026|BBBB|Beta", "Tbk|lagi"]
    )

    with pytest.raises(GalatIngesti) as galat:
        ksei.urai_master_efek(teks)

    assert "baris 3" in str(galat.value)
    assert "seharusnya 28" in str(galat.value)


def test_sambungan_di_batas_kolom_tidak_menambah_spasi() -> None:
    """Terputus tepat di `|` berarti menyambung tanpa spasi; kalau tidak, nama efeknya rusak."""
    kolom = _saham("BBBB", "Beta Mandiri Tbk").split("|")
    teks = "\n".join(
        ["|".join(KOLOM_KSEI), _saham("AAAA", "Alpha Tbk"), "|".join(kolom[:3]) + "|", "|".join(kolom[3:])]
    )

    hasil = ksei.urai_master_efek(teks)

    assert [satu.nama for satu in hasil.baris] == ["Alpha Tbk", "Beta Mandiri Tbk"]


# ---------------------------------------------------------------------------------------
# emiten.csv: bentuk yang bisa dibaca --refresh, dan kolom yang tetap kosong
# ---------------------------------------------------------------------------------------


def _tulis(folder: Path, teks: str) -> ksei.MasterEfek:
    master = ksei.urai_master_efek(teks, url="https://contoh/StatisEfek20260930.txt.zip")
    ksei.tulis_emiten_csv(
        master,
        folder / "emiten.csv",
        sumber=ksei.label_sumber(master, diakses_pada=HARI_INI),
        dicatat_pada=HARI_INI,
    )
    return master


def test_kepala_csv_di_baris_pertama(tmp_path: Path) -> None:
    """Pembaca mendeteksi pemisah dari baris pertama; penjelasan yang mendahuluinya merusaknya."""
    _tulis(tmp_path, _berkas(_saham("AAAA", "Alpha Tbk")))
    baris_pertama = (tmp_path / "emiten.csv").read_text(encoding="utf-8").splitlines()[0]

    assert baris_pertama.startswith("kode;nama;sektor_idx_ic;sektor_sumber;")
    # Jumlah kolomnya diambil dari kontraknya (spesifikasi pembaca), bukan angka yang dihafal:
    # menambah kolom baru cukup diubah di satu tempat, dan berkasnya tetap harus terbaca ulang.
    assert baris_pertama.split(";") == list(berkas.SPESIFIKASI["emiten"].nama_kolom)


def test_csv_yang_ditulis_terbaca_ulang_oleh_pembaca_refresh(tmp_path: Path) -> None:
    _tulis(tmp_path, _berkas(_saham("AAAA", "Alpha Sentosa Tbk"), _saham("BBBB", "Beta Mandiri Tbk")))
    emiten = berkas.baca_emiten(tmp_path)

    assert [satu.kode for satu in emiten] == ["AAAA", "BBBB"]
    assert emiten[0].nama == "Alpha Sentosa Tbk"
    assert emiten[0].jumlah_saham == 1_000_000
    assert emiten[0].dicatat_pada == HARI_INI
    assert "Master File Efek KSEI" in emiten[0].sumber


def test_kolom_tanpa_sumber_resmi_tetap_kosong(tmp_path: Path) -> None:
    """Sektor IDX-IC, papan, jenis, free float, status notasi: kosong, bukan didekati."""
    master = _tulis(tmp_path, _berkas(_saham("AAAA", "Alpha Sentosa Tbk")))
    satu = berkas.baca_emiten(tmp_path)[0]

    assert master.baris[0].sektor_ksei == "COMPUTER AND SERVICES"  # ada di sumber…
    assert satu.sektor_idx_ic is None  # …tetapi bukan IDX-IC, jadi tidak ditulis
    assert satu.papan is None
    assert satu.jenis is None
    assert satu.free_float_bp is None
    assert satu.status_notasi is None


def test_tanggal_pencatatan_ksei_masuk_kolom_tanggal_notasi(tmp_path: Path) -> None:
    """`Listing Date` KSEI dinyatakan sumbernya, jadi ia ditulis — bukan dibiarkan kosong.

    Sebelum 9 Okt 2026 kolom ini selalu NULL karena `emiten.csv` belum punya tempatnya.
    """
    _tulis(tmp_path, _berkas(_saham("AAAA", "Alpha Tbk", Listing_Date="25-NOV-1989")))

    assert berkas.baca_emiten(tmp_path)[0].tanggal_notasi == date(1989, 11, 25)


def test_tanggal_pencatatan_kosong_di_sumber_tetap_kosong_di_berkas(tmp_path: Path) -> None:
    """87 dari 975 baris berkas 30 Sep 2026 tidak menyatakan Listing Date.

    Kolom kosong berarti "sumbernya tidak menyatakan", bukan diisi tanggal berkas, tanggal
    jalan, atau tanggal apa pun yang membuat barisnya tampak lengkap.
    """
    _tulis(tmp_path, _berkas(_saham("AAAA", "Alpha Tbk", Listing_Date="")))

    assert berkas.baca_emiten(tmp_path)[0].tanggal_notasi is None


def test_penjelasan_kolom_tanggal_notasi_ikut_tertulis(tmp_path: Path) -> None:
    """Pemetaan nama kolom PRD ke `Listing Date` harus terbaca dari berkasnya sendiri."""
    _tulis(tmp_path, _berkas(_saham("AAAA", "Alpha Tbk")))
    isi = (tmp_path / "emiten.csv").read_text(encoding="utf-8")

    assert "Listing Date" in isi
    assert "P18" in isi, "pemetaan yang belum dikonfirmasi pengguna harus menunjuk pertanyaannya"


def test_penjelasan_kolom_kosong_ikut_tertulis_di_berkas(tmp_path: Path) -> None:
    """Orang yang membuka berkasnya harus tahu kolom kosong itu sengaja, bukan lupa."""
    _tulis(tmp_path, _berkas(_saham("AAAA", "Alpha Tbk")))
    isi = (tmp_path / "emiten.csv").read_text(encoding="utf-8")

    assert "SENGAJA DIKOSONGKAN" in isi
    assert "IDX-IC" in isi
    assert "bukan free float" in isi


# ---------------------------------------------------------------------------------------
# Pencarian berkas terbaru dan penolakan menimpa
# ---------------------------------------------------------------------------------------


def test_kandidat_tanggal_mundur_dari_akhir_bulan() -> None:
    kandidat = ksei.kandidat_tanggal(HARI_INI, bulan=3)

    assert kandidat[0] == TANGGAL_MASTER
    assert date(2026, 10, 31) not in kandidat  # bulan berjalan belum berakhir
    assert kandidat[1] == date(2026, 8, 31)


def test_unduh_memakai_berkas_pertama_yang_ada() -> None:
    """30 Sep belum terbit, 31 Agu ada: yang dipakai 31 Agu, dan urutannya terlihat."""
    diminta: list[str] = []
    isi = {ksei.url_master(date(2026, 8, 31)): _zip(_berkas(_saham("AAAA", "Alpha Tbk")), "StatisEfek20260831.txt")}

    hasil = ksei.unduh_master(hari_ini=HARI_INI, buka=_pembuka(isi, diminta), jeda=0.0)

    assert hasil.tanggal == date(2026, 8, 31)
    assert [url.rsplit("/", 1)[-1] for url in diminta] == [
        "StatisEfek20260930.txt.zip",
        "StatisEfek20260831.txt.zip",
    ]


def test_semua_kandidat_gagal_menyebut_yang_dicoba() -> None:
    diminta: list[str] = []

    with pytest.raises(GalatIngesti) as galat:
        ksei.unduh_master(hari_ini=HARI_INI, bulan=2, buka=_pembuka({}, diminta), percobaan=1, jeda=0.0)

    pesan = str(galat.value)
    assert "2026-09-30" in pesan and "StatisEfek20260930.txt.zip" in pesan
    assert "HTTP 404" in pesan


def test_balasan_yang_bukan_zip_ditolak() -> None:
    isi = {ksei.url_master(TANGGAL_MASTER): b"<html>bukan zip</html>"}

    with pytest.raises(GalatIngesti, match="zip"):
        ksei.unduh_master(
            hari_ini=HARI_INI, buka=_pembuka(isi, []), percobaan=1, jeda=0.0
        )


def test_emiten_csv_yang_sudah_ada_tidak_ditimpa(tmp_path: Path) -> None:
    """Berkas itu semesta pilihan pengguna; bisa saja sudah disunting dari sumber lain."""
    tujuan = tmp_path / "emiten.csv"
    tujuan.write_text("kode;nama\nAAAA;Punya Saya\n", encoding="utf-8")
    isi = {ksei.url_master(TANGGAL_MASTER): _zip(_berkas(_saham("BBBB", "Beta Tbk")))}

    with pytest.raises(GalatIngesti, match="--timpa-emiten"):
        ksei.ambil_emiten(tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0)

    assert tujuan.read_text(encoding="utf-8") == "kode;nama\nAAAA;Punya Saya\n"


def test_ambil_emiten_menulis_dan_membaca_ulang(tmp_path: Path) -> None:
    isi = {ksei.url_master(TANGGAL_MASTER): _zip(_berkas(_saham("AAAA", "Alpha Tbk")))}

    hasil = ksei.ambil_emiten(tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0)

    assert hasil.jumlah_terbaca_ulang == 1
    assert hasil.jalur == tmp_path / "emiten.csv"
    assert "Master File Efek KSEI 30 Sep 2026" in str(hasil)
    assert "DIKOSONGKAN dengan sengaja" in str(hasil)


def test_tanggal_master_yang_diminta_dipakai_persis() -> None:
    """`--tanggal-master` berarti berkas itu, bukan "yang terbaru dari tanggal itu"."""
    diminta: list[str] = []
    isi = {ksei.url_master(date(2026, 6, 30)): _zip(_berkas(_saham("AAAA", "Alpha Tbk")))}

    hasil = ksei.unduh_master(tanggal=date(2026, 6, 30), buka=_pembuka(isi, diminta), jeda=0.0)

    assert hasil.tanggal == date(2026, 6, 30)
    assert [url.rsplit("/", 1)[-1] for url in diminta] == ["StatisEfek20260630.txt.zip"]
