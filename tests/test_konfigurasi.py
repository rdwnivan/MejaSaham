"""Uji pemuatan parameter bursa bertanggal (K1, K6, T7, PRD bagian 10).

Yang diuji di sini bukan "apakah fungsinya jalan", melainkan janji yang membuat aturan keras 1
masuk akal: nilai tebakan tidak bisa masuk diam-diam, entri tanpa tanggal/sumber ditolak,
nilai lama tidak bisa tertimpa, dan parameter yang belum terverifikasi **menolak** dipakai
berhitung — bukan memakai default.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from mejasaham import cli, db, konfigurasi, lokasi

SUMBER = "Pengumuman IDX No. 001 (https://www.idx.co.id/..., diakses 6 Okt 2026)"

LOT_100 = f"""
[[lot]]
nilai_lembar  = 100
berlaku_sejak = 2026-01-02
sumber        = "{SUMBER}"
dicatat_pada  = 2026-10-06
"""

LOT_200 = LOT_100.replace("nilai_lembar  = 100", "nilai_lembar  = 200")

FRAKSI_HARGA = f"""
[[fraksi_harga]]
berlaku_sejak = 2026-01-02
sumber        = "{SUMBER}"
dicatat_pada  = 2026-10-06
rentang = [
  {{ batas_bawah = 500, batas_atas = 1999, tick = 5 }},
  {{ batas_bawah = 1,   batas_atas = 199,  tick = 1 }},
  {{ batas_bawah = 200, batas_atas = 499,  tick = 2 }},
  {{ batas_bawah = 2000, batas_atas = 4999, tick = 10 }},
  {{ batas_bawah = 5000, tick = 25 }},
]
"""

BROKER_A = f"""
[[biaya_broker]]
nama          = "Broker A"
sisi_beli     = {{ persen = 0.15, minimum = 10000 }}
sisi_jual     = {{ persen = 0.25, minimum = 10000 }}
berlaku_sejak = 2026-01-02
sumber        = "Dokumen tarif Broker A (diakses 6 Okt 2026)"
dicatat_pada  = 2026-10-06
"""

BROKER_B = BROKER_A.replace("Broker A", "Broker B").replace("persen = 0.15", "persen = 0.19")

PAJAK_0_15 = f"""
[[pajak_penjualan]]
persen        = 0.15
dasar         = "nilai jual"
berlaku_sejak = 2026-01-02
sumber        = "Dasar hukum (diakses 6 Okt 2026)"
dicatat_pada  = 2026-10-06
"""

SLIPPAGE_TICK = f"""
[[slippage]]
mode          = "tick"
nilai         = 1
berlaku_sejak = 2026-01-02
sumber        = "Dasar penetapan (diakses 6 Okt 2026)"
dicatat_pada  = 2026-10-06
"""

PAPAN_FCS = f"""
[[papan_pemantauan_khusus]]
uraian        = "Ringkasan aturan papan pemantauan khusus, apa adanya dari sumber."
berlaku_sejak = 2026-01-02
sumber        = "{SUMBER}"
dicatat_pada  = 2026-10-06
"""


def _berkas(*blok: str) -> str:
    return "skema = 1\n\n" + "\n\n".join(blok)


def _urai(*blok: str) -> tuple[konfigurasi.EntriParameter, ...]:
    return konfigurasi.urai(_berkas(*blok), asal="uji")


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Folder data di luar paket (A3), ditimpa lewat MEJASAHAM_DATA seperti di produksi."""
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


# --- berkas: bawaan, penyalinan, dan keadaan kosong -------------------------------------


def test_template_bawaan_disalin_saat_berkas_belum_ada(folder_data: Path) -> None:
    jalur, baru = konfigurasi.siapkan_berkas()

    assert baru is True
    assert jalur == lokasi.folder_konfigurasi() / konfigurasi.NAMA_BERKAS_AKTIF
    assert jalur.is_file(), "AC-12: folder data kosong harus kembali ke konfigurasi bawaan"


def test_berkas_yang_sudah_ada_tidak_ditimpa(folder_data: Path) -> None:
    jalur, _ = konfigurasi.siapkan_berkas()
    jalur.write_text(_berkas(LOT_100), encoding="utf-8")

    jalur_kedua, baru = konfigurasi.siapkan_berkas()

    assert baru is False and jalur_kedua == jalur
    assert "lot" in jalur.read_text(encoding="utf-8"), "berkas aktif tidak boleh dikembalikan ke template"


def test_template_bawaan_belum_memuat_entri(folder_data: Path) -> None:
    """Template wajib tetap kosong dari nilai yang belum diverifikasi (K6, aturan keras 1)."""
    konfigurasi.siapkan_berkas()

    _jalur, entri = konfigurasi.muat_berkas()

    assert entri == ()


def test_semua_parameter_belum_terverifikasi_saat_berkas_bawaan(
    folder_data: Path, sambungan: sqlite3.Connection
) -> None:
    """Aturan keras 1: tidak ada nilai tebakan, jadi semuanya menolak dipakai berhitung."""
    konfigurasi.siapkan_berkas()
    _jalur, entri = konfigurasi.muat_berkas()
    konfigurasi.simpan(sambungan, entri)

    status = konfigurasi.ringkasan_status(sambungan, pada=date(2026, 10, 6))

    assert {satu.keadaan for satu in status} == {konfigurasi.BELUM_TERVERIFIKASI}
    assert len(status) == len(konfigurasi.SPESIFIKASI)
    with pytest.raises(konfigurasi.ParameterBelumSiap) as galat:
        konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 10, 6)).ambil()
    assert "belum terverifikasi" in str(galat.value)
    assert konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 10, 6)).siap is False


# --- penolakan berkas yang salah --------------------------------------------------------


def test_berkas_bukan_toml_ditolak() -> None:
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="bukan TOML yang sah"):
        konfigurasi.urai("skema = 1\n[[lot]\nnilai_lembar = 100\n", asal="uji")


def test_skema_berkas_tidak_dikenal_ditolak() -> None:
    """Berkas bentuk lebih baru tidak dimuat setengah-setengah."""
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="skema"):
        konfigurasi.urai("skema = 2\n", asal="uji")
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="skema"):
        konfigurasi.urai("", asal="uji")


def test_tabel_tidak_dikenal_ditolak() -> None:
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="tabel tidak dikenal"):
        konfigurasi.urai(_berkas("[[lot2]]\nnilai_lembar = 100\n"), asal="uji")


@pytest.mark.parametrize(
    ("blok", "potongan_pesan"),
    [
        (LOT_100.replace("berlaku_sejak = 2026-01-02\n", ""), "kunci wajib `berlaku_sejak` tidak ada"),
        (LOT_100.replace("dicatat_pada  = 2026-10-06\n", ""), "kunci wajib `dicatat_pada` tidak ada"),
        (LOT_100.replace(f'sumber        = "{SUMBER}"\n', ""), "kunci wajib `sumber` tidak ada"),
        (LOT_100.replace("nilai_lembar", "nilai_lembar_lembar"), "kunci tidak dikenal"),
        (LOT_100.replace("nilai_lembar  = 100", "nilai_lembar  = 0"), "di luar batas"),
        (LOT_100.replace("nilai_lembar  = 100", "nilai_lembar  = 100.5"), "harus bilangan bulat"),
        (LOT_100.replace("nilai_lembar  = 100", 'nilai_lembar  = "100"'), "tanpa tanda kutip"),
        (LOT_100.replace("berlaku_sejak = 2026-01-02", "berlaku_sejak = 20260102"), "harus tanggal"),
        (LOT_100.replace("berlaku_sejak = 2026-01-02", 'berlaku_sejak = "2026-01-02"'), "harus tanggal"),
        (LOT_100.replace("dicatat_pada  = 2026-10-06", "dicatat_pada  = 2026-10-06T08:00:00"), "harus tanggal"),
        (LOT_100 + 'sumber_lain   = "x"\n', "kunci tidak dikenal"),
        (LOT_100.replace("dicatat_pada  = 2026-10-06", 'dicatat_pada  = 2026-10-06\naktif         = "ya"'), "`aktif` harus true"),
        (LOT_100.replace("dicatat_pada  = 2026-10-06", 'dicatat_pada  = 2026-10-06\nuraian        = ""'), "tidak boleh kosong"),
        (
            PAJAK_0_15.replace("persen        = 0.15", "persen        = 120"),
            "persen harus antara 0 dan 100",
        ),
    ],
)
def test_entri_yang_salah_ditolak(blok: str, potongan_pesan: str) -> None:
    with pytest.raises(konfigurasi.GalatKonfigurasi) as galat:
        _urai(blok)

    assert potongan_pesan in str(galat.value)


def test_rentang_berlubang_ditolak() -> None:
    rusak = FRAKSI_HARGA.replace("batas_bawah = 200, batas_atas = 499", "batas_bawah = 300, batas_atas = 499")

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="tanpa celah"):
        _urai(rusak)


def test_rentang_tumpang_tindih_ditolak() -> None:
    rusak = FRAKSI_HARGA.replace("batas_bawah = 200, batas_atas = 499", "batas_bawah = 199, batas_atas = 499")

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="tanpa celah"):
        _urai(rusak)


def test_dua_rentang_tanpa_batas_atas_ditolak() -> None:
    rusak = FRAKSI_HARGA.replace("{ batas_bawah = 2000, batas_atas = 4999, tick = 10 },", "{ batas_bawah = 2000, tick = 10 },")

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="hanya rentang teratas"):
        _urai(rusak)


def test_kunci_salah_di_dalam_rentang_ditolak() -> None:
    rusak = FRAKSI_HARGA.replace("tick = 1 }", "tickk = 1 }")

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="kunci tidak dikenal"):
        _urai(rusak)


def test_papan_pemantauan_khusus_wajib_uraian() -> None:
    tanpa_uraian = PAPAN_FCS.replace(
        'uraian        = "Ringkasan aturan papan pemantauan khusus, apa adanya dari sumber."\n', ""
    )

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="uraian"):
        _urai(tanpa_uraian)


def test_parameter_berkelompok_wajib_menyebut_kelompoknya() -> None:
    tanpa_kelompok = BROKER_A.replace('nama          = "Broker A"\n', "")

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="`nama` tidak ada"):
        _urai(tanpa_kelompok)


def test_parameter_tak_berkelompok_menolak_kunci_kelompok() -> None:
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="kunci tidak dikenal"):
        _urai(LOT_100.replace("nilai_lembar", 'kelompok      = "X"\nnilai_lembar'))


def test_dua_entri_dengan_identitas_sama_di_satu_berkas_ditolak() -> None:
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="sudah ditulis di tempat lain"):
        _urai(LOT_100, LOT_100)


def test_slippage_dengan_mode_tak_dikenal_ditolak() -> None:
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="tick"):
        _urai(SLIPPAGE_TICK.replace('mode          = "tick"', 'mode          = "per lembar"'))


# --- konversi satuan (T8, D-8) ----------------------------------------------------------


@pytest.mark.parametrize(("persen", "basis_poin"), [(0.15, 15), (0.075, 8), (2.5, 250), (100, 10000)])
def test_persen_menjadi_basis_poin_tanpa_galat_pembulatan(persen: float, basis_poin: int) -> None:
    """0,15% harus menjadi 15 bp — bukan 14 bp seperti hasil pemotongan float."""
    entri = _urai(PAJAK_0_15.replace("persen        = 0.15", f"persen        = {persen}"))

    assert entri[0].muatan[0]["persen_bp"] == basis_poin


def test_slippage_mode_menentukan_kolom_yang_diisi(sambungan: sqlite3.Connection) -> None:
    """Satuannya ditentukan `mode`; angka tick tidak boleh tertukar dengan persen."""
    persen = (
        SLIPPAGE_TICK.replace('mode          = "tick"', 'mode          = "persen"')
        .replace("nilai         = 1", "nilai         = 0.05")
        .replace("berlaku_sejak = 2026-01-02", "berlaku_sejak = 2026-07-01")
    )
    konfigurasi.simpan(sambungan, _urai(SLIPPAGE_TICK, persen))

    tick = konfigurasi.nilai_efektif(sambungan, "slippage", pada=date(2026, 6, 30)).entri
    basis_poin = konfigurasi.nilai_efektif(sambungan, "slippage", pada=date(2026, 7, 1)).entri

    assert tick is not None
    assert tick.muatan == ({"mode": "tick", "nilai_tick": 1, "nilai_persen_bp": None},)
    assert basis_poin is not None
    assert basis_poin.muatan == ({"mode": "persen", "nilai_tick": None, "nilai_persen_bp": 5},)


# --- simpan: append-only & idempoten ----------------------------------------------------


def test_revisi_menambah_baris_dan_muatan_tersimpan_bertipe(sambungan: sqlite3.Connection) -> None:
    entri = _urai(FRAKSI_HARGA)

    hasil = konfigurasi.simpan(sambungan, entri)

    assert hasil.baru == 1
    baris = sambungan.execute(
        "SELECT batas_bawah, batas_atas, tick FROM parameter_fraksi_harga_rentang"
        " WHERE nama = 'fraksi_harga' ORDER BY batas_bawah"
    ).fetchall()
    assert [(satu["batas_bawah"], satu["batas_atas"], satu["tick"]) for satu in baris] == [
        (1, 199, 1),
        (200, 499, 2),
        (500, 1999, 5),
        (2000, 4999, 10),
        (5000, None, 25),
    ], "rentang harus tersimpan berurutan meski di berkas ditulis acak (A5)"
    assert konfigurasi.nilai_efektif(sambungan, "fraksi_harga", pada=date(2026, 10, 6)).entri.muatan == entri[0].muatan


def test_memuat_ulang_berkas_yang_sama_tidak_menambah_baris(sambungan: sqlite3.Connection) -> None:
    entri = _urai(LOT_100, FRAKSI_HARGA, BROKER_A)

    pertama = konfigurasi.simpan(sambungan, entri)
    kedua = konfigurasi.simpan(sambungan, entri)

    assert (pertama.baru, kedua.baru, kedua.tetap) == (3, 0, 3)
    assert sambungan.execute("SELECT COUNT(*) FROM parameter_bursa").fetchone()[0] == 3


def test_entri_sama_dengan_isi_berbeda_gagal_berisik_dan_tidak_menimpa(
    sambungan: sqlite3.Connection,
) -> None:
    konfigurasi.simpan(sambungan, _urai(LOT_100))
    konfigurasi.simpan(sambungan, _urai(PAPAN_FCS))

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="tidak boleh ditimpa"):
        konfigurasi.simpan(sambungan, _urai(LOT_200))

    tersimpan = konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 10, 6)).entri
    assert tersimpan is not None and tersimpan.muatan[0]["nilai_lembar"] == 100


def test_pemuatan_yang_gagal_tidak_menyisakan_baris_separuh(sambungan: sqlite3.Connection) -> None:
    """A6: satu blok pemuatan = satu transaksi."""
    konfigurasi.simpan(sambungan, _urai(LOT_100))

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="tidak boleh ditimpa"):
        konfigurasi.simpan(sambungan, _urai(BROKER_A, LOT_200))

    assert sambungan.execute("SELECT COUNT(*) FROM parameter_bursa").fetchone()[0] == 1
    assert sambungan.execute("SELECT COUNT(*) FROM parameter_biaya_broker").fetchone()[0] == 0


def test_ubah_dan_hapus_baris_parameter_ditolak_trigger(sambungan: sqlite3.Connection) -> None:
    konfigurasi.simpan(sambungan, _urai(LOT_100))

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sambungan.execute("UPDATE parameter_bursa SET sumber = 'lain'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sambungan.execute("DELETE FROM parameter_lot")


# --- nilai efektif: tiga keadaan, tanggal berlaku, dan koreksi ---------------------------


def test_nilai_efektif_memilih_entri_berlaku_terakhir(sambungan: sqlite3.Connection) -> None:
    baru = """
[[lot]]
nilai_lembar  = 50
berlaku_sejak = 2026-07-01
sumber        = "Pengumuman IDX No. 002 (diakses 6 Okt 2026)"
dicatat_pada  = 2026-10-06
"""
    konfigurasi.simpan(sambungan, _urai(LOT_100, baru))

    sebelum = konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 6, 30)).entri
    sesudah = konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 7, 1)).entri

    assert sebelum is not None and sebelum.muatan[0]["nilai_lembar"] == 100
    assert sesudah is not None and sesudah.muatan[0]["nilai_lembar"] == 50


def test_entri_yang_berlaku_di_masa_depan_belum_dipakai(sambungan: sqlite3.Connection) -> None:
    konfigurasi.simpan(sambungan, _urai(LOT_100))

    status = konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 1, 1))

    assert status.keadaan == konfigurasi.BELUM_TERVERIFIKASI
    assert status.entri is None


def test_aktif_false_berarti_sengaja_dinonaktifkan_bukan_kembali_ke_entri_lama(
    sambungan: sqlite3.Connection,
) -> None:
    dimatikan = """
[[lot]]
nilai_lembar  = 100
berlaku_sejak = 2026-07-01
sumber        = "Pengumuman IDX No. 003 (diakses 6 Okt 2026)"
dicatat_pada  = 2026-10-06
aktif         = false
"""
    konfigurasi.simpan(sambungan, _urai(LOT_100, dimatikan))

    status = konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 8, 1))

    assert status.keadaan == konfigurasi.NONAKTIF
    assert status.siap is False
    assert "sengaja dinonaktifkan" in status.alasan
    with pytest.raises(konfigurasi.ParameterBelumSiap):
        status.ambil()


def test_koreksi_dengan_dicatat_pada_lebih_baru_menang_tanpa_menghapus_yang_lama(
    sambungan: sqlite3.Connection,
) -> None:
    koreksi = LOT_200.replace("dicatat_pada  = 2026-10-06", "dicatat_pada  = 2026-11-01")
    konfigurasi.simpan(sambungan, _urai(LOT_100))
    konfigurasi.simpan(sambungan, _urai(koreksi))

    status = konfigurasi.nilai_efektif(sambungan, "lot", pada=date(2026, 12, 1))

    assert status.entri is not None and status.entri.muatan[0]["nilai_lembar"] == 200
    assert status.entri.dicatat_pada == date(2026, 11, 1)
    jumlah = sambungan.execute(
        "SELECT COUNT(*) FROM parameter_bursa WHERE nama = 'lot'"
    ).fetchone()[0]
    assert jumlah == 2, "catatan lama tetap ada; yang berubah hanya mana yang dipakai"


def test_parameter_berkelompok_dibaca_per_kelompok(sambungan: sqlite3.Connection) -> None:
    konfigurasi.simpan(sambungan, _urai(BROKER_A, BROKER_B))

    a = konfigurasi.nilai_efektif(sambungan, "biaya_broker", "Broker A", pada=date(2026, 10, 6))
    b = konfigurasi.nilai_efektif(sambungan, "biaya_broker", "Broker B", pada=date(2026, 10, 6))
    lain = konfigurasi.nilai_efektif(sambungan, "biaya_broker", "Broker C", pada=date(2026, 10, 6))

    assert a.entri is not None and a.entri.muatan[0]["persen_beli_bp"] == 15
    assert b.entri is not None and b.entri.muatan[0]["persen_beli_bp"] == 19
    assert lain.keadaan == konfigurasi.BELUM_TERVERIFIKASI


def test_ringkasan_menyebut_kelompok_yang_ada_di_basis_data(sambungan: sqlite3.Connection) -> None:
    konfigurasi.simpan(sambungan, _urai(BROKER_A, BROKER_B))

    label = [satu.label for satu in konfigurasi.ringkasan_status(sambungan, pada=date(2026, 10, 6))]

    assert "biaya_broker [Broker A]" in label
    assert "biaya_broker [Broker B]" in label
    assert "lot" in label


def test_parameter_tak_dikenal_ditolak(sambungan: sqlite3.Connection) -> None:
    with pytest.raises(konfigurasi.GalatKonfigurasi, match="tidak dikenal"):
        konfigurasi.nilai_efektif(sambungan, "lot_bursa")


def test_berkas_dari_notepad_ber_bom_tetap_terbaca(folder_data: Path) -> None:
    jalur = konfigurasi.berkas_parameter()
    lokasi.pastikan_folder(jalur.parent)
    jalur.write_text(_berkas(LOT_100), encoding="utf-8-sig")

    _jalur, entri = konfigurasi.muat_berkas()

    assert len(entri) == 1 and entri[0].nama == "lot"


# --- K22/K23: "tidak dinyatakan sumber" adalah keadaan yang sah (10 Okt 2026) ------------
#
# Tarif resmi Stockbit menyatakan `0,15%`/`0,25%` dengan tegas, tetapi **tidak** menyatakan
# tarif minimum maupun tanggal berlakunya (bukti: `.uji-data/riset-tarif-broker/stockbit.md`).
# Yang dijaga uji di bawah: keadaan itu tersimpan **apa adanya** — NULL, bukan 0, dan tanggal
# pengamatan yang **berpenanda**, bukan tanggal yang menyamar sebagai "berlaku sejak".

BROKER_STOCKBIT = f"""
[[biaya_broker]]
nama               = "Stockbit (PT Stockbit Sekuritas Digital)"
sisi_beli          = {{ persen = 0.15 }}
sisi_jual          = {{ persen = 0.25 }}
sudah_termasuk     = ["levy", "ppn", "pph_penjualan"]
berlaku_sejak      = 2026-10-10
asal_berlaku_sejak = "tanggal_pengamatan"
sumber             = "Halaman tarif resmi Stockbit https://stockbit.com/ (blok 'Biaya Normal'), diakses 10 Okt 2026 00:13 WIB"
dicatat_pada       = 2026-10-06
"""


def test_minimum_yang_tidak_dinyatakan_tersimpan_null_bukan_nol(
    sambungan: sqlite3.Connection,
) -> None:
    """K22: "sumber tidak menyatakan minimum" harus berbeda dari "tidak ada minimum".

    Nol berarti "tidak ada tarif minimum" — pernyataan tentang bursa. Sumbernya tidak membuat
    pernyataan itu, jadi menuliskan 0 di sini adalah angka karangan (aturan keras 1). Uji ini
    yang membuktikan bedanya: baris tanpa `minimum` dan baris ber-`minimum = 0` harus bisa
    dibedakan di basis data, dan yang pertama **bukan** 0.
    """
    nol = BROKER_A.replace("minimum = 10000", "minimum = 0")
    konfigurasi.simpan(sambungan, _urai(BROKER_STOCKBIT, nol))

    tanpa_minimum = konfigurasi.nilai_efektif(
        sambungan, "biaya_broker", "Stockbit (PT Stockbit Sekuritas Digital)", pada=date(2026, 10, 10)
    ).entri
    dengan_nol = konfigurasi.nilai_efektif(
        sambungan, "biaya_broker", "Broker A", pada=date(2026, 10, 10)
    ).entri

    assert tanpa_minimum is not None and dengan_nol is not None
    assert tanpa_minimum.muatan[0]["minimum_beli"] is None
    assert tanpa_minimum.muatan[0]["minimum_jual"] is None
    assert dengan_nol.muatan[0]["minimum_beli"] == 0, (
        "nol harus tetap bisa ditulis bila sumbernya memang menyatakan tidak ada minimum"
    )
    # Dan yang tersimpan di mesin pun NULL, bukan 0 yang menyamar.
    baris = sambungan.execute(
        "SELECT minimum_beli, minimum_jual FROM parameter_biaya_broker"
        " WHERE kelompok = 'Stockbit (PT Stockbit Sekuritas Digital)'"
    ).fetchone()
    assert (baris["minimum_beli"], baris["minimum_jual"]) == (None, None)


def test_sudah_termasuk_tersimpan_sebagai_komponen_yang_bisa_ditanyakan(
    sambungan: sqlite3.Connection,
) -> None:
    """K23: penanda all-in disimpan per komponen, supaya B8 tidak dijumlahkan dua kali.

    Tanpa penanda ini, tarif jual 0,25% yang **sudah** memuat PPh final 0,1% akan ditambahi B8
    lagi oleh kalkulator biaya Tahap 2 — salah dua kali, dan tidak terlihat di keluaran mana
    pun, hanya di angkanya.
    """
    konfigurasi.simpan(sambungan, _urai(BROKER_STOCKBIT))

    komponen = [
        satu["komponen"]
        for satu in sambungan.execute(
            "SELECT komponen FROM parameter_biaya_broker_termasuk ORDER BY komponen"
        )
    ]
    assert komponen == ["levy", "pph_penjualan", "ppn"]
    tersimpan = konfigurasi.nilai_efektif(
        sambungan, "biaya_broker", "Stockbit (PT Stockbit Sekuritas Digital)", pada=date(2026, 10, 10)
    ).entri
    assert tersimpan is not None
    assert tersimpan.muatan[0]["sudah_termasuk"] == ["levy", "pph_penjualan", "ppn"]


def test_komponen_all_in_yang_tidak_dikenal_ditolak_berisik_tanpa_menyimpan_apa_pun(
    sambungan: sqlite3.Connection,
) -> None:
    """Komponen yang tidak dikenal tidak boleh diabaikan: komponen yang hilang = biaya kurang."""
    salah = BROKER_STOCKBIT.replace('"ppn"', '"pppn"')

    with pytest.raises(konfigurasi.GalatKonfigurasi) as galat:
        _urai(salah)

    assert "'pppn'" in str(galat.value)
    assert "levy" in str(galat.value), "pesannya harus menyebut daftar yang sah"
    assert sambungan.execute("SELECT COUNT(*) FROM parameter_bursa").fetchone()[0] == 0
    assert sambungan.execute("SELECT COUNT(*) FROM parameter_biaya_broker").fetchone()[0] == 0
    assert (
        sambungan.execute("SELECT COUNT(*) FROM parameter_biaya_broker_termasuk").fetchone()[0] == 0
    ), "penolakan harus terjadi sebelum apa pun tersimpan"


def test_komponen_all_in_ganda_ditolak() -> None:
    ganda = BROKER_STOCKBIT.replace('["levy", "ppn", "pph_penjualan"]', '["levy", "levy"]')

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="lebih dari sekali"):
        _urai(ganda)


def test_komponen_all_in_harus_daftar_bukan_teks() -> None:
    salah = BROKER_STOCKBIT.replace('["levy", "ppn", "pph_penjualan"]', '"levy"')

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="harus daftar teks"):
        _urai(salah)


def test_urutan_komponen_di_berkas_tidak_mengubah_artinya(sambungan: sqlite3.Connection) -> None:
    """Urutan penulisan bukan fakta: berkas yang sama dengan urutan terbalik tetap idempoten."""
    terbalik = BROKER_STOCKBIT.replace(
        '["levy", "ppn", "pph_penjualan"]', '["pph_penjualan", "levy", "ppn"]'
    )

    konfigurasi.simpan(sambungan, _urai(BROKER_STOCKBIT))
    kedua = konfigurasi.simpan(sambungan, _urai(terbalik))

    assert (kedua.baru, kedua.tetap) == (0, 1)


def test_sudah_termasuk_boleh_tidak_ada(sambungan: sqlite3.Connection) -> None:
    """Broker yang tarifnya bukan all-in tidak dipaksa menyatakan apa pun.

    Yang tersimpan adalah daftar **kosong** — bukan daftar berisi tebakan. Kosong di sini
    berarti "tidak satu pun komponen dinyatakan sudah termasuk", dan kalkulator biaya
    memperlakukannya sebagai tarif biasa.
    """
    konfigurasi.simpan(sambungan, _urai(BROKER_A))

    entri = konfigurasi.nilai_efektif(
        sambungan, "biaya_broker", "Broker A", pada=date(2026, 10, 10)
    ).entri

    assert entri is not None and entri.muatan[0]["sudah_termasuk"] == []
    assert (
        sambungan.execute("SELECT COUNT(*) FROM parameter_biaya_broker_termasuk").fetchone()[0] == 0
    )


def test_asal_berlaku_sejak_bawaannya_sumber(sambungan: sqlite3.Connection) -> None:
    """Entri yang tidak menyebut asalnya dibaca `sumber` — dan itu tersimpan apa adanya."""
    konfigurasi.simpan(sambungan, _urai(BROKER_A))

    entri = konfigurasi.nilai_efektif(
        sambungan, "biaya_broker", "Broker A", pada=date(2026, 10, 10)
    ).entri

    assert entri is not None and entri.asal_berlaku_sejak == "sumber"
    assert (
        sambungan.execute(
            "SELECT asal_berlaku_sejak FROM parameter_bursa WHERE nama = 'biaya_broker'"
        ).fetchone()[0]
        == "sumber"
    )


def test_asal_berlaku_sejak_yang_tidak_dikenal_ditolak(sambungan: sqlite3.Connection) -> None:
    """Nilai tak dikenal berhenti berisik, bukan tersimpan sebagai keadaan ketiga (aturan 7)."""
    salah = BROKER_STOCKBIT.replace(
        'asal_berlaku_sejak = "tanggal_pengamatan"', 'asal_berlaku_sejak = "perkiraan"'
    )

    with pytest.raises(konfigurasi.GalatKonfigurasi) as galat:
        _urai(salah)

    assert "asal_berlaku_sejak" in str(galat.value)
    assert "tanggal_pengamatan" in str(galat.value)


def test_asal_tanggal_berlaku_tidak_bisa_diubah_diam_diam(sambungan: sqlite3.Connection) -> None:
    """Tanggal sama dengan asal berbeda = dua arti berbeda; yang lama tidak boleh ditimpa.

    "berlaku sejak 10 Okt" bukan "diamati pada 10 Okt". Kalau perubahan itu lolos tanpa suara,
    baris yang sudah tersimpan akan berbohong tentang apa yang sumbernya nyatakan (K22).
    """
    konfigurasi.simpan(sambungan, _urai(BROKER_STOCKBIT))
    jadi_sumber = BROKER_STOCKBIT.replace(
        'asal_berlaku_sejak = "tanggal_pengamatan"', 'asal_berlaku_sejak = "sumber"'
    )

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="berlaku sejak"):
        konfigurasi.simpan(sambungan, _urai(jadi_sumber))

    tersimpan = sambungan.execute(
        "SELECT asal_berlaku_sejak FROM parameter_bursa WHERE nama = 'biaya_broker'"
    ).fetchall()
    assert len(tersimpan) == 1 and tersimpan[0][0] == "tanggal_pengamatan"


def test_memuat_ulang_entri_all_in_tidak_menambah_baris(sambungan: sqlite3.Connection) -> None:
    """Idempoten juga untuk entri yang punya tabel anak: tidak ada komponen yang tergandakan."""
    entri = _urai(BROKER_STOCKBIT)

    pertama = konfigurasi.simpan(sambungan, entri)
    kedua = konfigurasi.simpan(sambungan, entri)

    assert (pertama.baru, kedua.baru, kedua.tetap) == (1, 0, 1)
    assert sambungan.execute("SELECT COUNT(*) FROM parameter_bursa").fetchone()[0] == 1
    assert (
        sambungan.execute("SELECT COUNT(*) FROM parameter_biaya_broker_termasuk").fetchone()[0] == 3
    )


def test_koreksi_tarif_all_in_menambah_baris_dengan_komponennya_sendiri(
    sambungan: sqlite3.Connection,
) -> None:
    """Perbaikan = baris baru beserta komponennya, bukan menimpa yang lama (append-only)."""
    koreksi = BROKER_STOCKBIT.replace("sisi_jual          = { persen = 0.25 }", "sisi_jual          = { persen = 0.28 }").replace(
        "dicatat_pada       = 2026-10-06", "dicatat_pada       = 2026-11-01"
    )
    konfigurasi.simpan(sambungan, _urai(BROKER_STOCKBIT))
    konfigurasi.simpan(sambungan, _urai(koreksi))

    terpilih = konfigurasi.nilai_efektif(
        sambungan, "biaya_broker", "Stockbit (PT Stockbit Sekuritas Digital)", pada=date(2026, 12, 1)
    ).entri

    assert terpilih is not None and terpilih.muatan[0]["persen_jual_bp"] == 28
    assert terpilih.dicatat_pada == date(2026, 11, 1)
    jumlah = sambungan.execute(
        "SELECT COUNT(*) FROM parameter_bursa WHERE nama = 'biaya_broker'"
    ).fetchone()[0]
    assert jumlah == 2, "catatan lama tetap ada; yang berubah hanya mana yang dipakai"
    assert (
        sambungan.execute("SELECT COUNT(*) FROM parameter_biaya_broker_termasuk").fetchone()[0] == 6
    ), "komponen tiap revisi melekat pada revisinya sendiri"


def test_komponen_all_in_ditolak_untuk_parameter_yang_bukan_biaya_broker() -> None:
    """`sudah_termasuk` bukan kunci umum: menaruhnya di lot harus ditolak, bukan diabaikan."""
    salah = LOT_100 + 'sudah_termasuk = ["levy"]\n'

    with pytest.raises(konfigurasi.GalatKonfigurasi, match="kunci tidak dikenal"):
        _urai(salah)


# --- mode kepala (AC-11) ----------------------------------------------------------------


def test_mode_kepala_memuat_konfigurasi(
    folder_data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(["--muat-konfigurasi"])

    assert kode == cli.KODE_OK
    keluaran = capsys.readouterr()
    assert "baru disalin dari template bawaan" in keluaran.out
    assert "belum terverifikasi" in keluaran.err, "parameter yang belum terverifikasi harus berisik"
