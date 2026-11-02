"""Uji jalur impor berkas untuk fundamental, rasio bank, dan penanda penyesuaian (P2, PRD 9.3).

Jalur impor adalah satu-satunya jalan masuk data yang **tidak** bisa diperiksa sumbernya oleh
aplikasi: berkasnya ditulis manusia, dari laporan yang diunduh sendiri. Karena itu aturan yang
diuji di sini semuanya berbentuk "berhenti dengan pesan" atau "jangan menebak":

* **Satuan uang dinyatakan berkas, bukan ditebak.** `satuan_uang=juta` mengalikan kolom uang
  dengan 10^6, sedangkan `jumlah_saham` (lembar) dan `dps` (rupiah per lembar) tidak ikut dikali —
  keduanya sudah dinyatakan per satuan di laporan. Salah menebaknya membuat setiap rasio salah
  10^6 tanpa terlihat.
* **Baris fundamental tanpa satu pun angka ditolak**, bukan disimpan sebagai baris kosong yang
  menutupi data lama sebagai "terkini".
* **`mata_uang=USD` disimpan apa adanya**, dan metrik yang mencampurnya dengan harga rupiah
  berstatus "tidak dihitung" beserta alasannya (aturan keras 2).
* **`penyesuaian_sumber` membedakan tiga hal**: nilai sah, nilai tak dikenal (ditolak), dan
  kosong = "belum dinyatakan" — yang terakhir itu **bukan** `tidak_disesuaikan` (K8/C10).
* **Template bawaan boleh tersalin, tetapi tidak boleh terimpor** dan tidak boleh memuat kode
  emiten nyata (aturan keras 1).

Berkas uji ditulis dengan jumlah kolom yang **diturunkan dari `berkas.SPESIFIKASI`**, sehingga
barisnya tidak bisa diam-diam bergeser kolom ketika spesifikasinya berubah — kekeliruan yang
justru sedang diuji di sini.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator, Mapping
from datetime import date, datetime
from pathlib import Path

import pytest

from mejasaham import berkas, db, ingesti, lokasi, metrik, potret
from mejasaham.ingesti import (
    PENANDA_PENYESUAIAN_SAH,
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_SPLIT_DIVIDEN,
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    GalatIngesti,
)

TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)

#: Baris contoh di template bawaan: tidak pernah ikut terimpor.
CONTOH = "<<CONTOH>>"

#: Lima kolom yang angkanya menentukan sebuah baris fundamental "menambah apa pun atau tidak".
#: `dps` dan `jumlah_saham` sengaja bukan bagiannya: keduanya bukan angka periode laporan.
KOLOM_ANGKA_PERIODE = ("pendapatan", "laba_induk", "ekuitas_induk", "ebit", "cfo")


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
def folder_impor(folder_data: Path) -> Path:
    folder = folder_data / "konfigurasi"
    lokasi.pastikan_folder(folder)
    return folder


@pytest.fixture()
def sambungan(folder_data: Path) -> Iterator[sqlite3.Connection]:
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _tulis(folder: Path, nama: str, isi: str) -> Path:
    jalur = folder / nama
    jalur.write_text(isi, encoding="utf-8")
    return jalur


def _header(jenis: str, *, tanpa: tuple[str, ...] = (), ganti: Mapping[str, str] | None = None) -> str:
    """Header berkas dari spesifikasi pembacanya, dengan kolom yang sengaja dirusak."""
    ubah = ganti or {}
    kolom = [
        ubah.get(nama, nama)
        for nama in berkas.SPESIFIKASI[jenis].nama_kolom
        if nama not in tanpa
    ]
    return ";".join(kolom)


def _baris(jenis: str, **nilai: str) -> str:
    """Satu baris data dengan kolom selalu cocok dengan headernya, urut menurut spesifikasi."""
    isi = {nama: "" for nama in berkas.SPESIFIKASI[jenis].nama_kolom}
    isi.update(nilai)
    return ";".join(isi[nama] for nama in berkas.SPESIFIKASI[jenis].nama_kolom) + "\n"


def _baris_fundamental(**angka: str) -> str:
    bawaan = {
        "kode": "AAAA",
        "periode": "2025-12-31",
        "jenis_laporan": "tahunan",
        "tgl_publikasi": "2026-03-31",
        "mata_uang": "IDR",
        "satuan_uang": "juta",
        "sumber": "laporan keuangan uji",
    }
    return _baris("fundamental", **{**bawaan, **angka})


def _baris_rasio_bank(**angka: str) -> str:
    bawaan = {
        "kode": "AAAA",
        "periode": "2025-12-31",
        "tgl_publikasi": "2026-03-31",
        "sumber": "publikasi bank uji",
    }
    return _baris("rasio_bank", **{**bawaan, **angka})


def _baris_harga(**nilai: str) -> str:
    bawaan = {
        "kode": "AAAA",
        "tanggal": "2026-06-30",
        "open": "1000",
        "high": "1010",
        "low": "990",
        "close": "1005",
        "volume": "1000000",
    }
    return _baris("harga_harian", **{**bawaan, **nilai})


def _fundamental_uji(**angka: str) -> str:
    """Berkas fundamental satu baris yang seluruh kolom uangnya terisi angka bulat."""
    lengkap = {
        "pendapatan": "1000",
        "laba_induk": "100",
        "ekuitas_induk": "800",
        "ebit": "150",
        "beban_bunga": "10",
        "da": "30",
        "utang_bunga": "200",
        "kas": "50",
        "cfo": "120",
        "jumlah_saham": "12000000",
        "dps": "250",
    }
    return _header("fundamental") + "\n" + _baris_fundamental(**{**lengkap, **angka})


def test_dua_revisi_periode_sama_dalam_satu_berkas_ditolak_sebelum_menyentuh_basis_data(
    folder_impor: Path,
) -> None:
    """Berkas fundamental hanya boleh memuat **satu** baris per (kode, periode, jenis laporan).

    Dua baris periode sama di satu berkas selalu berarti salah satu dari dua hal: baris kembar
    karena salah salin, atau laporan asli dan restatement-nya ditaruh bersebelahan. Yang kedua
    tampak masuk akal justru karena S1 mendorong perbaikan data menambah baris baru — tetapi
    caranya **bukan** satu berkas berisi dua revisi: satu jalan impor memakai satu
    `diketahui_pada`, sehingga keduanya tidak muat.

    Sebelum penjaga ini ada, berkasnya diterima di sini lalu ditolak saat penulisan, dengan
    pesan yang menyebut kunci basis data — dan seluruh berkas ditolak oleh satu pasang baris
    yang bertabrakan. Sekarang penolakannya menyebut nama berkas dan kedua nomor barisnya.
    """
    _tulis(
        folder_impor,
        "fundamental.csv",
        _header("fundamental")
        + "\n"
        + _baris_fundamental(laba_induk="100")
        + _baris_fundamental(tgl_publikasi="2026-06-30", laba_induk="120"),
    )

    with pytest.raises(GalatIngesti) as keluhan:
        berkas.baca_folder(folder_impor)

    pesan = str(keluhan.value)
    assert "fundamental.csv" in pesan
    assert "baris 2 dan 3" in pesan, "pesannya harus menyebut kedua nomor barisnya"
    assert "satu** baris per kunci" in pesan


def test_baris_kembar_identik_dibiarkan_lewat_penjaga_berkas(folder_impor: Path) -> None:
    """Baris kembar yang **sama persis** bukan kegagalan — penjaganya harus membedakan keduanya.

    Yang berbahaya adalah membuang baris yang berbeda tanpa suara; salah salin yang identik
    tidak mengubah satu angka pun, dan menolaknya hanya menambah pekerjaan orang yang sedang
    memperbaiki berkasnya. Karena itu keputusan "sudah ada dan sama" tetap di titik tulis.
    """
    isi = _fundamental_uji().split("\n", 1)[1]
    _tulis(folder_impor, "fundamental.csv", _header("fundamental") + "\n" + isi + isi)

    hasil = berkas.baca_folder(folder_impor)

    assert len(hasil.kumpulan.fundamental) == 2


def test_dua_rasio_bank_periode_sama_dalam_satu_berkas_ditolak(folder_impor: Path) -> None:
    """Penjaga yang sama berlaku untuk `rasio_bank`, yang kunci alaminya kode + periode."""
    _tulis(
        folder_impor,
        "rasio-bank.csv",
        _header("rasio_bank")
        + "\n"
        + _baris_rasio_bank(npl_kotor_persen="1.9")
        + _baris_rasio_bank(tgl_publikasi="2026-06-30", npl_kotor_persen="2.1"),
    )

    with pytest.raises(GalatIngesti, match="rasio-bank.csv"):
        berkas.baca_folder(folder_impor)


def test_kunci_berbeda_ejaan_tetap_ditolak_karena_penjaganya_menormalkan_teks(folder_impor: Path) -> None:
    """Penjaga berkas membandingkan teks yang sudah dipangkas dan dihuruf-besarkan.

    Batasnya perlu diketahui supaya tidak dikira lebih luas daripada kenyataannya: yang
    dibandingkan adalah **teks**, bukan nilai sesudah diurai. Dua ejaan berbeda yang menunjuk
    periode yang sama karena itu tetap ditolak di sini — dan itu memang yang diinginkan, sebab
    keduanya akan bertabrakan di titik tulis juga. Yang **tidak** bisa ditangkap penjaga ini
    adalah dua ejaan berbeda yang mengurai ke nilai yang sama; bentuk itu tidak ada untuk kolom
    tanggal, dan kalau kelak ada, titik tulis yang tetap menjaganya.
    """
    _tulis(
        folder_impor,
        "rasio-bank.csv",
        _header("rasio_bank")
        + "\n"
        + _baris_rasio_bank(npl_kotor_persen="1.9")
        + _baris_rasio_bank(kode="aaaa", tgl_publikasi="2026-06-30", npl_kotor_persen="2.1"),
    )

    with pytest.raises(GalatIngesti, match="kunci yang sama"):
        berkas.baca_folder(folder_impor)


def _impor_ke_snapshot(sambungan: sqlite3.Connection, folder: Path) -> potret.Potret:
    """Baca folder lewat jalur impor, tulis snapshotted lewat jalur ingesti, lalu muat potretnya."""
    dibaca = berkas.baca_folder(folder)
    id_snapshot = ingesti.simpan(
        sambungan, dibaca.kumpulan, tanggal_data=TANGGAL, momen=MOMEN
    ).id_snapshot
    return potret.muat(sambungan, id_snapshot)


# ---------------------------------------------------------------------------------------
# Provenance per baris `rasio_bank.csv` (K78)
# ---------------------------------------------------------------------------------------


def test_sumber_per_baris_rasio_bank_tersimpan_dan_kembali_lewat_potret(
    folder_impor: Path, sambungan: sqlite3.Connection
) -> None:
    """Asal tiap publikasi bank harus ikut barisnya, bukan menjadi satu label folder (K78).

    Sebelum K78 kolom `sumber` di `rasio-bank.csv` divalidasi lalu dibuang: satu berkas yang
    memuat dua bank menuliskan asal **keduanya** sebagai `impor berkas: <folder>`. Akibatnya
    publikasi BBCA dan publikasi BRIS tidak bisa dibedakan lagi sesudah impor — tepat pada data
    yang paling perlu ditelusuri (PRD 7.1/7.2) — dan cacatnya berlipat bila kelak diperluas ke
    44 bank. Uji ini menempuh jalur yang sebenarnya (berkas → `berkas.baca_folder` →
    `ingesti.simpan` → `potret.muat`), sebab di antara keempatnya ada tiga titik yang bisa
    membuang kolomnya tanpa satu pun galat.
    """
    _tulis(
        folder_impor,
        "rasio-bank.csv",
        _header("rasio_bank")
        + "\n"
        + _baris_rasio_bank(
            kode="BBCA",
            npl_kotor_persen="1.86",
            sumber="Laporan Keuangan Publikasi BBCA 30 Jun 2026 (diakses 19 Okt 2026)",
        )
        + _baris_rasio_bank(
            kode="BRIS",
            npl_kotor_persen="1.80",
            sumber="Laporan Publikasi Triwulanan BRIS Juni 2026 (diakses 19 Okt 2026)",
        ),
    )

    p = _impor_ke_snapshot(sambungan, folder_impor)

    assert p.rasio_bank["BBCA"][0].sumber.startswith("Laporan Keuangan Publikasi BBCA")
    assert p.rasio_bank["BRIS"][0].sumber.startswith("Laporan Publikasi Triwulanan BRIS")

    tersimpan = dict(sambungan.execute("SELECT kode, sumber FROM rasio_bank"))
    assert tersimpan["BBCA"] == "Laporan Keuangan Publikasi BBCA 30 Jun 2026 (diakses 19 Okt 2026)"
    assert tersimpan["BRIS"] == "Laporan Publikasi Triwulanan BRIS Juni 2026 (diakses 19 Okt 2026)"
    assert all(
        not satu.startswith(f"{ingesti.PREFIKS_SUMBER_IMPOR}:") for satu in tersimpan.values()
    ), "label folder tidak boleh menimpa sumber yang dinyatakan barisnya"


def test_rasio_bank_tanpa_sumber_ditolak_menyebut_kolomnya(folder_impor: Path) -> None:
    """Kolom `sumber` wajib **dan** isinya diperiksa, bukan hanya nama kolomnya (K78).

    Kolom ini sudah dinyatakan wajib di `berkas.SPESIFIKASI` dan di template, tetapi sebelum K78
    isinya tidak pernah diperiksa karena memang dibuang. Baris tanpa asal bukan sekadar tidak
    lengkap: ia tampak sama sahnya dengan baris yang asalnya jelas, dan asal itulah yang diminta
    PRD 7.1/7.2 ketika angka bank ditelusuri.
    """
    _tulis(
        folder_impor,
        "rasio-bank.csv",
        _header("rasio_bank") + "\n" + _baris_rasio_bank(npl_kotor_persen="1.86", sumber=""),
    )

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "rasio-bank.csv" in pesan
    assert "baris 2" in pesan
    assert "`sumber`" in pesan
    assert "wajib diisi" in pesan


# ---------------------------------------------------------------------------------------
# Satuan uang (T8): dinyatakan berkas, bukan ditebak
# ---------------------------------------------------------------------------------------


def test_satuan_uang_juta_mengalikan_kolom_uang_tetapi_bukan_jumlah_saham_dan_dps(
    folder_impor: Path,
) -> None:
    """Laporan "dalam jutaan Rupiah" dinormalkan ke rupiah utuh saat impor (T8).

    Setiap kolom uang dikali 10^6, sedangkan `jumlah_saham` (lembar) dan `dps` (rupiah per lembar)
    **tidak** — keduanya sudah dinyatakan per satuan di laporan. Mengalikannya akan membuat jumlah
    lembar 12 juta menjadi 12 triliun, dan setiap rasio per saham salah 10^6 tanpa terlihat.
    Angka aslinya tetap tersimpan di kolom `*_mentah` untuk audit.
    """
    _tulis(folder_impor, "fundamental.csv", _fundamental_uji())

    hasil = berkas.baca_folder(folder_impor)

    satu = hasil.kumpulan.fundamental[0]
    for kolom, harapan in (
        ("pendapatan", 1_000_000_000),
        ("laba_induk", 100_000_000),
        ("ekuitas_induk", 800_000_000),
        ("ebit", 150_000_000),
        ("beban_bunga", 10_000_000),
        ("da", 30_000_000),
        ("utang_bunga", 200_000_000),
        ("kas", 50_000_000),
        ("cfo", 120_000_000),
    ):
        assert getattr(satu, kolom) == harapan, f"{kolom} harus dikali 10^6"
    assert satu.jumlah_saham == 12_000_000, "jumlah saham dalam lembar, bukan satuan laporan"
    assert satu.dps == 250, "dps dalam rupiah per lembar, bukan satuan laporan"
    assert satu.satuan_uang == "juta", "satuan yang dinyatakan berkas ikut tersimpan"
    assert satu.pendapatan_mentah == "1000", "angka asli tetap tersimpan untuk audit (T8)"


def test_satuan_uang_rupiah_tidak_mengubah_angka(folder_impor: Path) -> None:
    """`rupiah` berarti angka di berkas sudah rupiah utuh: tidak ada pengalian sama sekali."""
    _tulis(folder_impor, "fundamental.csv", _fundamental_uji(satuan_uang="rupiah"))

    hasil = berkas.baca_folder(folder_impor)

    satu = hasil.kumpulan.fundamental[0]
    assert satu.satuan_uang == "rupiah"
    assert satu.pendapatan == 1000
    assert satu.laba_induk == 100
    assert satu.cfo == 120
    assert satu.jumlah_saham == 12_000_000
    assert satu.dps == 250


# ---------------------------------------------------------------------------------------
# Baris fundamental tanpa angka
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "angka",
    [
        {nama: "" for nama in KOLOM_ANGKA_PERIODE},
        {
            **{nama: "" for nama in KOLOM_ANGKA_PERIODE},
            "jumlah_saham": "1000000",
            "dps": "250",
        },
    ],
    ids=["seluruh kolom periode kosong", "hanya jumlah saham dan dps"],
)
def test_baris_fundamental_tanpa_satu_pun_angka_ditolak(
    folder_impor: Path, angka: dict[str, str]
) -> None:
    """PRD 7.2: baris yang tidak menambah apa pun ditolak, bukan disimpan sebagai baris kosong.

    Baris seperti itu tetap menjadi "laporan terkini" bagi emiten itu di layar, padahal tidak
    memuat satu angka pun — data lama yang masih benar jadi tersembunyi di belakangnya. Yang
    diperiksa adalah lima kolom arus/posisi (pendapatan, laba, ekuitas, EBIT, arus kas operasi);
    `dps` dan `jumlah_saham` saja **tidak** cukup, karena keduanya bukan laporan periode itu.
    """
    _tulis(folder_impor, "fundamental.csv", _fundamental_uji(**angka))

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "seluruh kolom angka kosong" in pesan
    assert "baris 2" in pesan, "pesannya harus menunjuk baris yang salah"


# ---------------------------------------------------------------------------------------
# Mata uang (PRD 8.2, AC-3)
# ---------------------------------------------------------------------------------------


def test_mata_uang_usd_tersimpan_apa_adanya(
    folder_impor: Path, sambungan: sqlite3.Connection
) -> None:
    """Laporan USD disimpan sebagai USD — tidak dikonversi dan tidak dianggap rupiah.

    Mengonversinya diam-diam menuntut kurs yang tidak ada di basis data, dan menganggapnya rupiah
    membuat PER-nya tampak murah 16.000 kali. Yang dikonversi hanyalah **satuan** angkanya
    (juta → rupiah utuh); mata uangnya tetap seperti yang dinyatakan berkas.
    """
    _tulis(folder_impor, "fundamental.csv", _fundamental_uji(mata_uang="USD"))

    p = _impor_ke_snapshot(sambungan, folder_impor)

    satu = p.fundamental["AAAA"][0]
    assert satu.mata_uang == "USD"
    assert satu.satuan_uang == "juta"
    assert satu.pendapatan == 1_000_000_000, "satuannya tetap dinormalkan, mata uangnya tidak"


@pytest.mark.parametrize("nama_metrik", ["per", "pbv"])
def test_metrik_yang_mencampur_laporan_usd_dengan_harga_rupiah_tidak_dihitung(
    folder_impor: Path, sambungan: sqlite3.Connection, nama_metrik: str
) -> None:
    """PRD 8.2/aturan keras 2: mencampur USD dengan harga rupiah berhenti dihitung, berlasan.

    Harga di berkas dan di layar selalu rupiah; laporan yang dinyatakan USD harus dikonversi
    lebih dulu — dan kursnya bukan milik aplikasi ini. Menghitungnya apa adanya menghasilkan
    PER/PBV yang salah besar **tanpa satu pun tanda**, jadi pilihannya hanya berhenti sambil
    menyebut mata uangnya supaya bisa ditindaklanjuti.
    """
    _tulis(
        folder_impor,
        "emiten.csv",
        _header("emiten")
        + "\n"
        + _baris("emiten", kode="AAAA", nama="Emiten Uji", jumlah_saham="1000000", sumber="uji", dicatat_pada="2026-06-01")
        + "\n",
    )
    _tulis(folder_impor, "harga-harian.csv", _header("harga_harian") + "\n" + _baris_harga())
    _tulis(
        folder_impor,
        "fundamental.csv",
        _fundamental_uji(
            mata_uang="USD",
            satuan_uang="rupiah",
            pendapatan="1000000000",
            laba_induk="100000000",
            ekuitas_induk="800000000",
            ebit="150000000",
            beban_bunga="10000000",
            cfo="120000000",
            jumlah_saham="1000000",
            dps="250",
        ),
    )

    p = _impor_ke_snapshot(sambungan, folder_impor)
    nilai = metrik.metrik_emiten(p, "AAAA")[nama_metrik]

    assert nilai.status == metrik.STATUS_TIDAK_DIHITUNG
    assert nilai.nilai is None, "bukan angka tebakan"
    assert "USD" in (nilai.alasan or ""), "alasannya harus menyebut mata uangnya"
    assert "rupiah" in (nilai.alasan or "")


# ---------------------------------------------------------------------------------------
# Asal tanggal publikasi (migrasi 007, K18)
# ---------------------------------------------------------------------------------------


def test_berkas_tanpa_kolom_asal_tgl_publikasi_tetap_terbaca_sebagai_sumber(
    folder_impor: Path, sambungan: sqlite3.Connection
) -> None:
    """Berkas lama — dan berkas yang diisi tangan — tidak punya kolom ini, dan itu sah.

    `fundamental` append-only, jadi baris lama tidak bisa ditulis ulang untuk mengisi kolom baru.
    Kalau kolom yang tidak ada dianggap "belum dinyatakan", seluruh data lama akan berubah arti
    setelah migrasi 007 tanpa satu pun angka berubah — kekeliruan yang paling sulit terlihat.

    Barisnya sengaja disusun **menurut header lama**, bukan lewat `_baris()` yang mengikuti
    spesifikasi sekarang: yang sedang diuji justru berkas yang ditulis sebelum kolomnya ada.
    """
    kolom = [
        nama
        for nama in berkas.SPESIFIKASI["fundamental"].nama_kolom
        if nama != "asal_tgl_publikasi"
    ]
    isi = {nama: "" for nama in kolom}
    isi.update(
        {
            "kode": "AAAA",
            "periode": "2025-12-31",
            "jenis_laporan": "tahunan",
            "tgl_publikasi": "2026-03-31",
            "mata_uang": "IDR",
            "satuan_uang": "juta",
            "pendapatan": "1000",
            "laba_induk": "100",
            "ekuitas_induk": "800",
            "sumber": "laporan keuangan sebelum kolom ini ada",
        }
    )
    _tulis(
        folder_impor,
        "fundamental.csv",
        ";".join(kolom) + "\n" + ";".join(isi[nama] for nama in kolom) + "\n",
    )

    p = _impor_ke_snapshot(sambungan, folder_impor)

    assert p.fundamental["AAAA"][0].asal_tgl_publikasi == "sumber"


def test_asal_tgl_publikasi_tanggal_pengambilan_sampai_ke_potret(
    folder_impor: Path, sambungan: sqlite3.Connection
) -> None:
    """Jalur otomatis (K18) menandai dirinya, dan tanda itu ikut sampai potret.

    Kalau tandanya hilang di salah satu lapisan, laporan akan menyebut tanggal pengambilan
    sebagai tanggal terbit — satu-satunya hal yang membedakan "diketahui sejak diambil" dari
    "diterbitkan emiten", dan tidak ada angka di layar yang menunjukkan bedanya.
    """
    _tulis(
        folder_impor,
        "fundamental.csv",
        _fundamental_uji(asal_tgl_publikasi="tanggal_pengambilan"),
    )

    p = _impor_ke_snapshot(sambungan, folder_impor)

    satu = p.fundamental["AAAA"][0]
    assert satu.asal_tgl_publikasi == "tanggal_pengambilan"
    assert satu.tgl_publikasi == date(2026, 3, 31), "tanggalnya sendiri tetap dipakai apa adanya"


def test_asal_tgl_publikasi_yang_salah_ketik_ditolak_menyebut_kolomnya(folder_impor: Path) -> None:
    """Salah ketik tidak boleh jatuh ke bawaan `sumber` — itu justru kebalikan artinya."""
    _tulis(
        folder_impor,
        "fundamental.csv",
        _fundamental_uji(asal_tgl_publikasi="tanggal ambil"),
    )

    with pytest.raises(GalatIngesti, match="asal_tgl_publikasi"):
        berkas.baca_folder(folder_impor)


# ---------------------------------------------------------------------------------------
# Daftar emiten: kolom `tanggal_notasi` (PRD 12 tabel 23; pemetaan namanya = P18)
# ---------------------------------------------------------------------------------------


def _berkas_emiten(**nilai: str) -> str:
    bawaan = {"kode": "AAAA", "nama": "Emiten Uji", "sumber": "uji", "dicatat_pada": "2026-06-01"}
    return _header("emiten") + "\n" + _baris("emiten", **{**bawaan, **nilai}) + "\n"


def test_label_sumber_impor_memakai_jalur_absolut_walau_folder_diberi_relatif(
    folder_impor: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--impor .uji-data/...` dan refresh (yang memberi jalur absolut) harus satu label.

    Sejak T100 baris "sudah ada" dibandingkan per sumber, jadi dua ejaan folder yang sama
    terhitung dua sumber — terukur di data kerja sesi 70: 171 revisi `notasi_khusus` yang hanya
    berbeda label.
    """
    _tulis(folder_impor, "harga-harian.csv", _header("harga_harian") + "\n" + _baris_harga())
    monkeypatch.chdir(folder_impor.parent)

    dibaca = berkas.baca_folder(Path(folder_impor.name))

    assert dibaca.kumpulan.sumber == f"{ingesti.PREFIKS_SUMBER_IMPOR}: {folder_impor.resolve()}"


def test_impor_ulang_folder_sama_lewat_jalur_relatif_tidak_menulis_revisi_baru(
    folder_impor: Path, sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tulis(folder_impor, "harga-harian.csv", _header("harga_harian") + "\n" + _baris_harga())
    ingesti.simpan(
        sambungan, berkas.baca_folder(folder_impor.resolve()).kumpulan, tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    monkeypatch.chdir(folder_impor.parent)

    kedua = ingesti.simpan(
        sambungan, berkas.baca_folder(Path(folder_impor.name)).kumpulan, tanggal_data=TANGGAL,
        momen=datetime(2026, 7, 2, 9, 0, 0),
    )

    assert kedua.baris.baru == {}
    assert kedua.baris.tetap == {"harga_harian": 1}


def test_tanggal_notasi_dari_berkas_rujukan_sampai_ke_potret(
    folder_impor: Path, sambungan: sqlite3.Connection
) -> None:
    """Kolom yang sudah ada di skema tetapi selalu NULL kini punya jalur masuk yang utuh.

    Diuji sampai potret, bukan hanya sampai objek `Emiten`: di antara berkas dan pemakaian ada
    jalur tulis yang bisa kehilangan satu kolom **tanpa satu pun galat** — gejalanya hanya kolom
    yang selamanya NULL, persis keadaan yang sedang diperbaiki.
    """
    _tulis(folder_impor, "emiten.csv", _berkas_emiten(tanggal_notasi="1989-11-25"))
    _tulis(folder_impor, "harga-harian.csv", _header("harga_harian") + "\n" + _baris_harga())

    p = _impor_ke_snapshot(sambungan, folder_impor)

    assert p.emiten["AAAA"].tanggal_notasi == date(1989, 11, 25)


def test_tanggal_notasi_kosong_tersimpan_null_bukan_tanggal_tebakan(
    folder_impor: Path, sambungan: sqlite3.Connection
) -> None:
    """Kosong berarti "sumbernya tidak menyatakan" (aturan keras 2), bukan diisi tanggal lain.

    Nilainya diperiksa di basis datanya, bukan hanya di objek: `NULL` yang berubah menjadi
    tanggal apa pun (tanggal impor, tanggal hari ini) akan tampak sah di layar.
    """
    _tulis(folder_impor, "emiten.csv", _berkas_emiten(tanggal_notasi=""))
    _tulis(folder_impor, "harga-harian.csv", _header("harga_harian") + "\n" + _baris_harga())

    p = _impor_ke_snapshot(sambungan, folder_impor)

    assert p.emiten["AAAA"].tanggal_notasi is None
    tersimpan = sambungan.execute("SELECT tanggal_notasi FROM emiten").fetchall()
    assert [satu[0] for satu in tersimpan] == [None]


def test_tanggal_notasi_yang_bukan_tanggal_ditolak_menyebut_barisnya(folder_impor: Path) -> None:
    _tulis(folder_impor, "emiten.csv", _berkas_emiten(tanggal_notasi="25/11/1989"))

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "emiten.csv baris 2" in pesan, "pesannya harus menunjuk berkas dan barisnya"
    assert "tanggal_notasi" in pesan
    assert "YYYY-MM-DD" in pesan


# ---------------------------------------------------------------------------------------
# Kolom hilang / salah ketik (aturan berkas impor yang sudah berlaku)
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nama_berkas", "isi", "potongan", "kolom"),
    [
        (
            "fundamental.csv",
            _header("fundamental", tanpa=("sumber",)),
            "kolom wajib tidak ada",
            "sumber",
        ),
        (
            "fundamental.csv",
            _header("fundamental", ganti={"pendapatan": "pendapattan"}),
            "kolom tidak dikenal",
            "pendapattan",
        ),
        (
            "rasio-bank.csv",
            _header("rasio_bank", tanpa=("sumber",)),
            "kolom wajib tidak ada",
            "sumber",
        ),
        (
            "rasio-bank.csv",
            _header("rasio_bank", ganti={"npl_kotor_persen": "npl_kotor_person"}),
            "kolom tidak dikenal",
            "npl_kotor_person",
        ),
    ],
    ids=[
        "fundamental kolom wajib hilang",
        "fundamental salah ketik",
        "rasio bank kolom wajib hilang",
        "rasio bank salah ketik",
    ],
)
def test_kolom_yang_hilang_atau_salah_ketik_menolak_berkas_dengan_nama_kolomnya(
    folder_impor: Path, nama_berkas: str, isi: str, potongan: str, kolom: str
) -> None:
    """Berkas salah baca lebih berbahaya daripada berkas yang menolak dimuat.

    Kolom yang salah ketik akan terbaca sebagai kolom kosong: seluruh angka baris itu hilang dan
    yang tersisa hanyalah baris "terkini" tanpa isi. Karena itu kedua jenis kekeliruan menolak
    berkasnya, dan pesannya menyebut **nama kolomnya** supaya bisa langsung diperbaiki.
    """
    _tulis(folder_impor, nama_berkas, isi + "\n")

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert potongan in pesan
    assert kolom in pesan, "nama kolomnya harus disebut"
    assert nama_berkas in pesan


# ---------------------------------------------------------------------------------------
# Kolom berlebih: isinya hilang tanpa jejak kalau dibiarkan (temuan sesi 7, aksi #18)
# ---------------------------------------------------------------------------------------


def test_kolom_berlebih_yang_berisi_menolak_berkas_menyebut_baris_dan_isinya(folder_impor: Path) -> None:
    """`;` di dalam nilai = kolom tambahan; isinya **tidak boleh** dibuang diam-diam.

    Inilah cacat yang terukur 16 Okt 2026: satu berkas impor yang ditulis dengan penggabungan
    string kehilangan seluruh isi sesudah `;` pertama pada **66 dari 171 baris** — penanda temuan
    dan kutipan keputusan ikut lenyap — tanpa satu pun galat. Pembaca kini menolak baris seperti
    itu dan menyebut barisnya, jumlah kolom berlebih, dan isinya, supaya penyebabnya terlihat.
    """
    _tulis(
        folder_impor,
        "fundamental.csv",
        _fundamental_uji(sumber="laporan uji; catatan: ini akan hilang"),
    )

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "baris 2" in pesan, "nomor barisnya harus disebut"
    assert "kolom berlebih" in pesan
    assert "catatan: ini akan hilang" in pesan, "isi yang akan hilang harus ditampilkan"
    assert "csv.writer" in pesan, "jalan keluarnya harus disebut"


def test_nilai_yang_dikutip_dibaca_utuh_termasuk_pemisahnya(folder_impor: Path) -> None:
    """Bentuk yang benar: nilai yang memuat `;` ditulis dalam kutip, dan terbaca utuh (T62).

    Uji ini yang menjaga "jalan keluarnya": berkas turunan basis data (K51/K52 dan K53/K54)
    memang memuat `;` di `keterangan` — dan itu **bukan** cacat selama ditulis `csv.writer`.
    """
    _tulis(
        folder_impor,
        "fundamental.csv",
        _fundamental_uji(sumber='"catatan: memuat; pemisah"'),
    )

    hasil = berkas.baca_folder(folder_impor)

    assert len(hasil.kumpulan.fundamental) == 1
    assert hasil.kumpulan.fundamental[0].sumber == "catatan: memuat; pemisah"


def test_kolom_berlebih_yang_kosong_tetap_diterima(folder_impor: Path) -> None:
    """`;;` di ujung baris tidak menghilangkan apa pun, jadi tidak ditolak.

    Batas ini disengaja: yang ditolak adalah **isi** yang hilang, bukan bentuk barisnya. Berkas
    yang disunting tangan sering berakhir dengan pemisah, dan menolaknya akan memindahkan
    perhatian dari cacat yang sebenarnya.
    """
    _tulis(
        folder_impor,
        "fundamental.csv",
        _fundamental_uji(satuan_uang="rupiah", pendapatan="1000").rstrip("\n") + ";;\n",
    )

    hasil = berkas.baca_folder(folder_impor)

    assert len(hasil.kumpulan.fundamental) == 1
    assert hasil.kumpulan.fundamental[0].pendapatan == 1000


def test_berkas_yang_diawali_komentar_tetap_terbaca(folder_impor: Path) -> None:
    """Komentar `#` boleh mendahului baris kepala, dan pemisahnya tetap terdeteksi.

    Ditemukan saat menyiapkan berkas verifikasi 973 kode: pemisah kolom dulu dideteksi dari baris
    **fisik** pertama, sehingga berkas yang diawali penjelasan ditolak dengan pesan yang
    menyesatkan — "kolom tidak dikenal ['kode;nama;…']" — padahal isinya benar. Aturan "baris mana
    yang dianggap penjelasan" kini satu definisi, dipakai baik untuk mencari baris kepala maupun
    saat membacanya.
    """
    _tulis(
        folder_impor,
        "fundamental.csv",
        "# penjelasan berkas\n"
        "# boleh beberapa baris\n"
        + _header("fundamental")
        + "\n"
        + _baris_fundamental(pendapatan="1000", laba_induk="100", ekuitas_induk="500"),
    )

    hasil = berkas.baca_folder(folder_impor)

    assert len(hasil.kumpulan.fundamental) == 1
    # `satuan_uang` bawaannya "juta", jadi angkanya ikut dikali 10^6 — bukti barisnya terbaca utuh,
    # bukan hanya baris kepalanya yang berhasil dilewati.
    assert hasil.kumpulan.fundamental[0].pendapatan == 1_000 * 10**6


def test_kepala_yang_terbaca_satu_kolom_menyebut_letak_baris_kepala(folder_impor: Path) -> None:
    """Baris judul sebelum kepala ditolak dengan pesan yang menunjuk **letaknya**, bukan isinya.

    Tanpa pesan ini, pemakainya melihat "kolom tidak dikenal" untuk nama kolom yang jelas benar
    dan tidak terpikir bahwa yang salah adalah letak baris kepalanya.
    """
    _tulis(
        folder_impor,
        "fundamental.csv",
        "Daftar fundamental 2026\n" + _header("fundamental") + "\n" + _baris_fundamental(),
    )

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "satu kolom" in pesan
    assert "baris kepala" in pesan
    assert "fundamental.csv" in pesan


def test_rasio_bank_dengan_seluruh_rasio_kosong_ditolak(folder_impor: Path) -> None:
    """Baris rasio bank tanpa satu pun rasio ditolak (CHECK tabel, ditegakkan juga di pembaca).

    Baris kosong tetap menjadi "rasio terkini" bagi bank itu, sehingga NPL/CAR/BOPO/NIM yang
    sebelumnya sudah diimpor tertutup oleh baris yang tidak memuat apa pun — dan saringan bank
    kehilangan datanya tanpa ada yang berubah di berkas yang terlihat.
    """
    _tulis(
        folder_impor,
        "rasio-bank.csv",
        _header("rasio_bank")
        + "\n"
        + _baris_rasio_bank(keterangan="belum ada publikasi"),
    )

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "tidak ada satu pun rasio" in pesan
    assert "baris 2" in pesan
    for kolom in ("npl_kotor_persen", "car_persen", "bopo_persen", "nim_persen"):
        assert kolom in pesan, "sebutkan kolom mana saja yang harus diisi"


# ---------------------------------------------------------------------------------------
# penyesuaian_sumber pada harga-harian.csv (K8/C10)
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "penanda",
    [PENYESUAIAN_TIDAK_DISESUAIKAN, PENYESUAIAN_SPLIT, PENYESUAIAN_SPLIT_DIVIDEN],
)
def test_penyesuaian_sumber_yang_sah_diterima_apa_adanya(folder_impor: Path, penanda: str) -> None:
    """Nilai sah apa adanya: penanda inilah yang menentukan penyesuaian saat dibaca (K8/C10).

    Baris bertanda `split` dilewati oleh penyesuaian, sedangkan `tidak_disesuaikan` justru
    disesuaikan. Karena itu nilainya tidak boleh dinormalkan, diterjemahkan, atau dibuang.
    """
    _tulis(folder_impor, "harga-harian.csv", _header("harga_harian") + "\n" + _baris_harga(penyesuaian_sumber=penanda))

    hasil = berkas.baca_folder(folder_impor)

    assert hasil.kumpulan.harga_harian[0].penyesuaian_sumber == penanda


def test_penyesuaian_sumber_yang_tidak_dikenal_ditolak_dengan_pilihan_yang_sah(
    folder_impor: Path,
) -> None:
    """Nilai tak dikenal ditolak, dan pesannya menyebut pilihan yang sah.

    "disesuaikan" adalah tebakan yang wajar ditulis orang, tetapi artinya ambigu: sudah
    disesuaikan split saja, atau split dan dividen? Menebaknya berarti memilih salah satu tafsir
    diam-diam — persis yang dilarang K8/C10.
    """
    _tulis(
        folder_impor,
        "harga-harian.csv",
        _header("harga_harian") + "\n" + _baris_harga(penyesuaian_sumber="disesuaikan"),
    )

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "tidak dikenal" in pesan
    assert "Pilihan yang sah" in pesan
    for sah in PENANDA_PENYESUAIAN_SAH:
        assert sah in pesan


@pytest.mark.parametrize("dengan_kolom", [True, False], ids=["kolom kosong", "kolom tidak ada"])
def test_penyesuaian_sumber_kosong_berarti_belum_dinyatakan_bukan_tidak_disesuaikan(
    folder_impor: Path, dengan_kolom: bool
) -> None:
    """Kosong = "belum dinyatakan" (`None`), dan itu **berbeda** dari "tidak disesuaikan".

    Bedanya menentukan: baris bertanda `tidak_disesuaikan` akan **disesuaikan** dengan split yang
    diketahui, sedangkan baris tanpa penanda tidak boleh ditebak sama sekali — metrik harganya
    berhenti dihitung dengan alasan yang menyebut kolom ini. Menyamakan keduanya berarti memilih
    tafsir yang kebetulan menguntungkan salah satu pihak.
    """
    header = (
        _header("harga_harian")
        if dengan_kolom
        else _header("harga_harian", tanpa=("penyesuaian_sumber",))
    )
    _tulis(folder_impor, "harga-harian.csv", header + "\n" + _baris_harga())

    hasil = berkas.baca_folder(folder_impor)

    satu = hasil.kumpulan.harga_harian[0]
    assert satu.penyesuaian_sumber is None
    assert satu.penyesuaian_sumber != PENYESUAIAN_TIDAK_DISESUAIKAN


# ---------------------------------------------------------------------------------------
# Template bawaan (AC-12, aturan keras 1)
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nama_berkas", "jenis"), [("fundamental.csv", "fundamental"), ("rasio-bank.csv", "rasio_bank")]
)
def test_template_fundamental_dan_rasio_bank_ikut_tersalin(
    folder_impor: Path, nama_berkas: str, jenis: str
) -> None:
    """AC-12: kedua berkas baru ikut disalin saat belum ada, dan headernya sesuai pembacanya.

    Header template yang tidak cocok dengan `SPESIFIKASI` membuat template bawaan ditolak oleh
    pembacanya sendiri — pengguna membuka aplikasi, menyalin template, dan langsung mendapat galat
    "kolom wajib tidak ada" tanpa pernah menyentuh isinya.
    """
    disalin = berkas.siapkan_berkas_bawaan(folder_impor)

    assert nama_berkas in disalin
    jalur = folder_impor / nama_berkas
    assert jalur.is_file()
    header = jalur.read_text(encoding="utf-8").splitlines()[0]
    assert tuple(header.split(";")) == berkas.SPESIFIKASI[jenis].nama_kolom


def test_template_fundamental_dan_rasio_bank_tidak_ikut_terimpor(folder_impor: Path) -> None:
    """Template yang tersalin tetap tidak menambah satu baris pun: barisnya bertanda `<<CONTOH>>`.

    Kalau baris contoh ikut terimpor, pemasangan baru langsung memuat fundamental dan rasio bank
    karangan — angka yang tidak berasal dari laporan siapa pun tetapi tampak sah di layar.
    """
    berkas.siapkan_berkas_bawaan(folder_impor)

    hasil = berkas.baca_folder(folder_impor)

    assert hasil.kumpulan.fundamental == ()
    assert hasil.kumpulan.rasio_bank == ()
    assert "fundamental.csv (0 baris)" in hasil.dibaca
    assert "rasio-bank.csv (0 baris)" in hasil.dibaca


@pytest.mark.parametrize("nama_berkas", ["fundamental.contoh.csv", "rasio-bank.contoh.csv"])
def test_template_fundamental_dan_rasio_bank_tidak_memuat_kode_emiten_nyata(
    nama_berkas: str,
) -> None:
    """Aturan keras 1: template tidak boleh memuat kode emiten nyata (pola `emiten.contoh.csv`).

    Baris contoh wajib bertanda `<<CONTOH>>`, sehingga satu-satunya cara sebuah kode emiten masuk
    adalah dengan menghapus penandanya — dan itu langsung terlihat. Sebagai penjaga kedua, tidak
    ada satu pun ruas yang berbentuk kode IDX (empat huruf besar) di baris data mana pun.
    """
    bawaan = Path(__file__).resolve().parents[1] / "mejasaham" / "defaults"
    isi = (bawaan / nama_berkas).read_text(encoding="utf-8-sig")
    baris = [
        satu for satu in isi.splitlines() if satu.strip() and not satu.startswith("#")
    ]

    assert baris[0].startswith("kode;"), "baris pertama harus header"
    data = baris[1:]
    assert data, f"{nama_berkas} tidak punya baris contoh sama sekali"
    for satu in data:
        kolom = satu.split(";")
        assert kolom[0] == CONTOH, f"baris contoh harus bertanda {CONTOH}: {satu}"
        for ruas in kolom[1:]:
            assert not re.fullmatch(r"[A-Z]{4}", ruas.strip()), (
                f"ruas {ruas!r} berbentuk kode emiten: {satu}"
            )
        assert "GANTI" in satu, "baris contoh harus menyatakan bahwa isinya belum diverifikasi"
