"""Uji kalkulator risiko & ukuran posisi (F5, PRD 9.7) — `mejasaham/risiko.py`.

Yang diuji adalah janji-janji yang membuat angka "berapa lembar" bisa dipercaya:

* **Rumusnya PRD 9.7, bukan selera.** Lembar mentah = (ekuitas × risiko per posisi) ÷ (harga
  masuk − stop + biaya & slippage per lembar); ukuran akhir = nilai terkecil dari lembar mentah,
  batas bobot, batas sektor, batas likuiditas, dan kas tersedia, dibulatkan ke bawah per lot;
  risiko nominal dihitung dari ukuran **akhir**. Rumus yang bergeser sedikit akan menghasilkan
  ukuran yang salah tanpa satu pun galat.
* **Dua arah pembulatan yang disengaja**: biaya dibulatkan **ke atas** dan stop hasil ATR
  dibulatkan **ke bawah** ke tick sah, supaya risiko yang ditampilkan tidak pernah lebih kecil
  daripada kenyataan (PRD 10: risiko yang ditampilkan adalah batas bawah). Keduanya diuji dengan
  angka yang membedakan arahnya.
* **Batas yang datanya tidak ada disebut "tidak dinilai"**, bukan dianggap longgar (aturan keras
  2). Tanpa pembeda itu, rencana yang lolos karena datanya tidak ada akan terbaca sama dengan
  rencana yang lolos karena benar.
* **K23 tidak boleh salah dua kali**: tarif jual Stockbit sudah termasuk PPh final 0,1%, jadi
  kalkulator **tidak** menambahkannya lagi — sedangkan tarif yang tidak menyatakannya tetap
  ditambahi. Keduanya diuji, sebab yang salah hanya terlihat di angkanya.
* **Mesin yang menegakkan bentuknya**: `CHECK (stop < harga_masuk)`, `CHECK` status, dan trigger
  append-only diuji lewat penulisan SQL langsung, bukan lewat modul — aturan yang hanya hidup di
  satu fungsi akan hilang begitu ada jalur tulis kedua.
* **Perilaku menolak PRD 9.7**: rencana dengan pelanggaran hanya bisa disimpan setelah pengguna
  memilih — ukuran yang patuh, atau menerima pelanggarannya secara tercatat.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest

from mejasaham import cli, db, ingesti, kandidat, konfigurasi, lokasi, metrik, risiko
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    HargaHarian,
    KumpulanData,
)

SUMBER = "uji-risiko"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
KODE = "AAAA"
KODE_LAIN = "BBBB"
SEKTOR = "industri"
LOT = 100

#: Deret harga: 24 hari bursa, rentang tetap 40 rupiah, penutupan 2.320.
#: ATR14 Wilder dari deret begini = 40 (rentang sejati selalu 40), sehingga `stop_bawaan`
#: menghasilkan 2.320 − 80 = 2.240 → dibulatkan ke bawah ke tick sah 2.240 (tick 10).
CLOSE = 2_320
RENTANG = 40
HARI = 24
#: Nilai transaksi 2.320 × 2.000.000 = Rp 4,64 miliar per hari.
VOLUME = 2_000_000
ADTV20 = CLOSE * VOLUME

EMITEN_UJI = (
    Emiten(kode=KODE, nama="Emiten A", sektor_idx_ic=SEKTOR, sumber="uji-rujukan"),
    Emiten(kode=KODE_LAIN, nama="Emiten B", sektor_idx_ic=SEKTOR, sumber="uji-rujukan"),
)

LOT_100 = f"""
[[lot]]
nilai_lembar  = 100
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06
"""

FRAKSI_HARGA = f"""
[[fraksi_harga]]
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06
rentang = [
  {{ batas_bawah = 200,  batas_atas = 499,  tick = 2 }},
  {{ batas_bawah = 2000, batas_atas = 4999, tick = 10 }},
  {{ batas_bawah = 5000, tick = 25 }},
  {{ batas_bawah = 1,    batas_atas = 199,  tick = 1 }},
  {{ batas_bawah = 500,  batas_atas = 1999, tick = 5 }},
]
"""

#: Tarif *all-in* seperti Stockbit: PPh final jual sudah termasuk di dalam 0,25% (K23).
BROKER_ALL_IN = f"""
[[biaya_broker]]
nama          = "Broker All-in"
sisi_beli     = {{ persen = 0.15 }}
sisi_jual     = {{ persen = 0.25 }}
sudah_termasuk = ["pph_penjualan", "levy", "ppn"]
berlaku_sejak = 2026-01-02
sumber        = "Halaman tarif resmi broker (uji): fee beli 0,15% / fee jual 0,25% sudah termasuk PPh"
dicatat_pada  = 2026-10-06
"""

#: Tarif yang menyatakan tarifnya saja: PPh final penjualan harus ditambahkan sendiri.
BROKER_TANPA_PPH = f"""
[[biaya_broker]]
nama          = "Broker Biasa"
sisi_beli     = {{ persen = 0.15, minimum = 10000 }}
sisi_jual     = {{ persen = 0.25 }}
berlaku_sejak = 2026-01-02
sumber        = "Dokumen tarif broker (uji)"
dicatat_pada  = 2026-10-06
"""

PAJAK_PENJUALAN = f"""
[[pajak_penjualan]]
persen        = 0.1
dasar         = "nilai jual"
berlaku_sejak = 2026-01-02
sumber        = "Dasar hukum (uji)"
dicatat_pada  = 2026-10-06
"""

SLIPPAGE_TICK = f"""
[[slippage]]
mode          = "tick"
nilai         = 1
berlaku_sejak = 2026-01-02
sumber        = "Keputusan produk K20 (uji)"
dicatat_pada  = 2026-10-06
"""


def _urai(*blok: str) -> tuple[konfigurasi.EntriParameter, ...]:
    return konfigurasi.urai("skema = 1\n\n" + "\n\n".join(blok), asal="uji")


def _deret(kode: str, *, hari: int = HARI) -> tuple[HargaHarian, ...]:
    """Deret dengan rentang tetap: ATR14-nya bisa dihitung tangan (selalu `RENTANG`)."""
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=hari - 1 - i),
            open=CLOSE,
            high=CLOSE + RENTANG // 2,
            low=CLOSE - RENTANG // 2,
            close=CLOSE,
            volume=VOLUME,
            nilai=CLOSE * VOLUME,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(hari)
    )


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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


@pytest.fixture()
def berparameter(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    """Parameter bursa yang sudah terverifikasi (lot, tick, tarif, pajak, slippage)."""
    konfigurasi.simpan(
        sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_ALL_IN, PAJAK_PENJUALAN, SLIPPAGE_TICK)
    )
    return sambungan


@pytest.fixture()
def data(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    """Emiten + 24 hari harga lewat jalur nyata (`ingesti.simpan`), bukan INSERT tangan."""
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=EMITEN_UJI,
            harga_harian=_deret(KODE) + _deret(KODE_LAIN),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    return sambungan


@pytest.fixture()
def siap(berparameter: sqlite3.Connection, data: sqlite3.Connection) -> sqlite3.Connection:
    """Basis data lengkap: parameter + data + batas risiko bawaan + ekuitas harian."""
    risiko.simpan_preset(berparameter, risiko.batas_bawaan(date(2026, 7, 1)))
    risiko.catat_ekuitas(
        berparameter, ekuitas=250_000_000, kas=100_000_000, tanggal=date(2026, 7, 1)
    )
    return berparameter


def _preset(**ganti: int) -> risiko.PresetRisiko:
    bawaan = risiko.batas_bawaan(date(2026, 7, 1))
    nilai = dict(bawaan.nilai)
    nilai.update(ganti)
    return risiko.PresetRisiko(
        id_preset_risiko=bawaan.id_preset_risiko,
        nama=bawaan.nama,
        versi=bawaan.versi,
        keterangan=bawaan.keterangan,
        dibuat_pada=bawaan.dibuat_pada,
        nilai=nilai,
    )


def _hitung(**ganti: object) -> risiko.HasilRisiko:
    argumen: dict[str, object] = {
        "kode": KODE,
        "ekuitas": 250_000_000,
        "harga_masuk": CLOSE,
        "stop": 2_240,
        "biaya_slippage": 14,
        "lot": LOT,
        "batas": _preset(),
    }
    argumen.update(ganti)
    return risiko.hitung(**argumen)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------
# Batas risiko: pengaturan berversi, bukan konstanta (PRD 8.3)
# ---------------------------------------------------------------------------------------


def test_batas_bawaan_sesuai_prd_9_7() -> None:
    """Angka awalnya PRD 9.7 "Batas bawaan" — pengaturan, bukan parameter bursa."""
    bawaan = risiko.batas_bawaan(date(2026, 7, 1))

    assert bawaan.bp(risiko.RISIKO_PER_POSISI) == 75
    assert bawaan.bp(risiko.BOBOT_MAKSIMUM) == 1000
    assert bawaan.bp(risiko.BOBOT_SEKTOR_MAKSIMUM) == 3000
    assert bawaan.bp(risiko.LIKUIDITAS_MAKSIMUM) == 200
    assert bawaan.bp(risiko.TOTAL_RISIKO_MAKSIMUM) == 500
    assert "PRD 9.7" in (bawaan.keterangan or "")


def test_preset_tersimpan_sekali_lalu_idempoten(sambungan: sqlite3.Connection) -> None:
    bawaan = risiko.batas_bawaan(date(2026, 7, 1))

    assert risiko.simpan_preset(sambungan, bawaan) is True
    assert risiko.simpan_preset(sambungan, bawaan) is False
    assert sambungan.execute("SELECT COUNT(*) FROM preset_risiko_nilai").fetchone()[0] == 5


def test_preset_berisi_beda_pada_id_yang_sama_ditolak(sambungan: sqlite3.Connection) -> None:
    """Rencana lama menunjuk versi ini; artinya tidak boleh berubah diam-diam (PRD 8.3)."""
    risiko.simpan_preset(sambungan, risiko.batas_bawaan(date(2026, 7, 1)))

    with pytest.raises(risiko.GalatRisiko, match="naikkan versinya"):
        risiko.simpan_preset(sambungan, _preset(bobot_maksimum=2000))


def test_preset_tanpa_satu_batas_ditolak(sambungan: sqlite3.Connection) -> None:
    """Batas yang hilang tidak boleh berarti "tanpa batas"."""
    bawaan = risiko.batas_bawaan(date(2026, 7, 1))
    kurang = {nama: nilai for nama, nilai in bawaan.nilai.items() if nama != risiko.LIKUIDITAS_MAKSIMUM}
    tanpa = risiko.PresetRisiko(
        id_preset_risiko=bawaan.id_preset_risiko,
        nama=bawaan.nama,
        versi=bawaan.versi,
        keterangan=bawaan.keterangan,
        dibuat_pada=bawaan.dibuat_pada,
        nilai=kurang,
    )

    with pytest.raises(risiko.GalatRisiko, match="likuiditas_maksimum"):
        risiko.simpan_preset(sambungan, tanpa)


def test_batas_yang_hilang_di_basis_data_ditolak_saat_dipakai(sambungan: sqlite3.Connection) -> None:
    """Bahkan bila barisnya hilang diam-diam, pemakaiannya menolak — bukan dianggap nol.

    Disusun langsung lewat SQL (bukan lewat `simpan_preset`, yang memang menolaknya lebih dulu):
    yang diuji di sini adalah bacanya, sebab basis data pengguna bisa saja rusak sebagian.
    """
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO preset_risiko (id_preset_risiko, nama, versi, keterangan, dibuat_pada)"
            " VALUES ('risiko-bawaan/v1', 'risiko-bawaan', 1, NULL, '2026-07-01')"
        )
        for nama, nilai in risiko.BATAS_AWAL_BP.items():
            if nama == risiko.BOBOT_MAKSIMUM:
                continue
            koneksi.execute(
                "INSERT INTO preset_risiko_nilai (id_preset_risiko, nama, nilai_bp)"
                " VALUES ('risiko-bawaan/v1', ?, ?)",
                (nama, nilai),
            )

    with pytest.raises(risiko.GalatRisiko, match="bobot maksimum"):
        risiko.preset_terbaru(sambungan).bp(risiko.BOBOT_MAKSIMUM)


def test_preset_risiko_append_only(sambungan: sqlite3.Connection) -> None:
    """Aturan append-only ditegakkan mesin, bukan disiplin penulisnya (aturan keras 3)."""
    risiko.simpan_preset(sambungan, _preset())

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sambungan.execute("UPDATE preset_risiko_nilai SET nilai_bp = 1")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sambungan.execute("DELETE FROM preset_risiko_nilai")


def test_preset_terbaru_memilih_versi_tertinggi(sambungan: sqlite3.Connection) -> None:
    risiko.simpan_preset(sambungan, _preset())
    kedua = risiko.batas_bawaan(date(2026, 7, 2), versi=2)
    risiko.simpan_preset(sambungan, kedua)

    assert risiko.preset_terbaru(sambungan).versi == 2
    assert risiko.daftar_preset(sambungan) == ("risiko-bawaan/v1", "risiko-bawaan/v2")


def test_preset_belum_ada_menyebut_cara_mengisinya(sambungan: sqlite3.Connection) -> None:
    with pytest.raises(risiko.GalatRisiko, match="--batas-risiko-bawaan"):
        risiko.preset_terbaru(sambungan)


# ---------------------------------------------------------------------------------------
# Tick harga (B2): harga tidak digeser diam-diam
# ---------------------------------------------------------------------------------------


def test_tick_dibaca_per_pita(berparameter: sqlite3.Connection) -> None:
    tabel = risiko.tabel_tick(berparameter, pada=date(2026, 7, 1))

    assert tabel.tick(100) == 1
    assert tabel.tick(250) == 2
    assert tabel.tick(1_000) == 5
    assert tabel.tick(2_320) == 10
    assert tabel.tick(6_000) == 25


def test_harga_bukan_kelipatan_tick_ditolak_beserta_tick_terdekat(
    berparameter: sqlite3.Connection,
) -> None:
    tabel = risiko.tabel_tick(berparameter, pada=date(2026, 7, 1))

    with pytest.raises(risiko.GalatRisiko) as galat:
        risiko.periksa_harga(2_323, tabel, "harga masuk")

    pesan = str(galat.value)
    assert "2320" in pesan and "2330" in pesan
    assert "tidak digeser diam-diam" in pesan


def test_harga_di_luar_pita_ditolak(berparameter: sqlite3.Connection) -> None:
    """Pita yang tidak memuat harganya berarti tidak ada tick yang sah — bukan tick 1."""
    tabel = risiko.TabelTick(rentang=((200, 499, 2), (2000, 4999, 10)))

    assert tabel.tick(10) is None
    with pytest.raises(risiko.GalatRisiko, match="di luar tabel fraksi harga"):
        risiko.periksa_harga(10, tabel, "stop")


def test_tick_belum_terverifikasi_menolak_menghitung(sambungan: sqlite3.Connection) -> None:
    """Aturan keras 1: tanpa tabel fraksi yang sah, harga tidak boleh dibulatkan diam-diam."""
    with pytest.raises(konfigurasi.ParameterBelumSiap):
        risiko.tabel_tick(sambungan, pada=date(2026, 7, 1))


# ---------------------------------------------------------------------------------------
# Biaya & slippage per lembar (B6/B7/B8/B9, K20/K22/K23)
# ---------------------------------------------------------------------------------------


def test_biaya_beli_dibulatkan_ke_atas(berparameter: sqlite3.Connection) -> None:
    """0,15% dari 2.320 = 3,48 → 4 per lembar; arah ini tidak pernah meremehkan risiko."""
    biaya = risiko.biaya_sisi(berparameter, risiko.SISI_BELI, 2_320, date(2026, 7, 1))

    assert biaya.tarif_bp == 15
    assert biaya.biaya_per_lembar == 4
    assert biaya.minimum is None
    assert "pph_penjualan" in biaya.komponen_termasuk


def test_biaya_beli_tidak_menambahkan_pph(berparameter: sqlite3.Connection) -> None:
    """PPh final hanya sisi jual (PRD 10); menambahkannya di sisi beli akan salah sejak awal."""
    biaya = risiko.biaya_sisi(berparameter, risiko.SISI_BELI, 2_320, date(2026, 7, 1))

    assert biaya.pph_bp == 0
    assert all("PPh" not in satu for satu in biaya.rincian)


def test_biaya_jual_tidak_menambah_pph_yang_sudah_termasuk(
    berparameter: sqlite3.Connection,
) -> None:
    """K23: tarif jual Stockbit sudah memuat PPh final 0,1% — menambahkannya salah dua kali."""
    biaya = risiko.biaya_sisi(berparameter, risiko.SISI_JUAL, 2_320, date(2026, 7, 1))

    assert biaya.pph_bp == 0
    assert biaya.biaya_per_lembar == 6  # 0,25% dari 2.320 = 5,8 → 6; PPh TIDAK ditambahkan
    assert any("sudah" in satu and "PPh" in satu for satu in biaya.rincian)


def test_biaya_jual_menambahkan_pph_bila_tidak_termasuk(
    sambungan: sqlite3.Connection,
) -> None:
    """Tarif yang tidak menyatakan PPh di dalamnya tetap ditambahi (B8) — kebalikan K23."""
    konfigurasi.simpan(
        sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_TANPA_PPH, PAJAK_PENJUALAN, SLIPPAGE_TICK)
    )

    biaya = risiko.biaya_sisi(sambungan, risiko.SISI_JUAL, 2_320, date(2026, 7, 1))

    assert biaya.pph_bp == 10
    assert biaya.biaya_per_lembar == 9  # 0,25% + 0,1% = 0,35% dari 2.320 = 8,12 → 9
    assert biaya.pph_dasar == "nilai jual"


def test_minimum_yang_tidak_dinyatakan_tidak_diterapkan_berisik(
    berparameter: sqlite3.Connection,
) -> None:
    """K22: `minimum` yang tidak ada bukan nol — dan ketiadaannya disebut, bukan didiamkan."""
    biaya = risiko.biaya_sisi(berparameter, risiko.SISI_BELI, 2_320, date(2026, 7, 1))

    assert biaya.minimum is None
    assert any("tidak dinyatakan sumbernya" in satu for satu in biaya.rincian)


def test_minimum_yang_ada_disebut_sebagai_catatan(sambungan: sqlite3.Connection) -> None:
    """Tarif minimum hidup per transaksi, sedangkan rumus PRD 9.7 per lembar — ia disebut."""
    konfigurasi.simpan(sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_TANPA_PPH, SLIPPAGE_TICK))

    biaya = risiko.biaya_sisi(sambungan, risiko.SISI_BELI, 2_320, date(2026, 7, 1))

    assert biaya.minimum == 10_000
    assert any("tarif minimum" in satu for satu in biaya.rincian)


def test_dua_broker_terpasang_menuntut_pilihan(sambungan: sqlite3.Connection) -> None:
    """Memilih broker pertama diam-diam akan memakai tarif milik orang lain."""
    konfigurasi.simpan(
        sambungan,
        _urai(LOT_100, FRAKSI_HARGA, BROKER_ALL_IN, BROKER_TANPA_PPH, SLIPPAGE_TICK),
    )

    with pytest.raises(risiko.GalatRisiko, match="--broker"):
        risiko.biaya_sisi(sambungan, risiko.SISI_BELI, 2_320, date(2026, 7, 1))

    dipilih = risiko.biaya_sisi(
        sambungan, risiko.SISI_BELI, 2_320, date(2026, 7, 1), broker="Broker Biasa"
    )
    assert dipilih.tarif_bp == 15


def test_slippage_satu_tick_mengikuti_pita_harga(berparameter: sqlite3.Connection) -> None:
    """B9/K20: satu tick, jadi nilainya otomatis benar di setiap pita harga."""
    tabel = risiko.tabel_tick(berparameter, pada=date(2026, 7, 1))

    assert risiko.slippage_per_lembar(berparameter, 2_320, tabel, date(2026, 7, 1))[0] == 10
    assert risiko.slippage_per_lembar(berparameter, 6_000, tabel, date(2026, 7, 1))[0] == 25
    assert risiko.slippage_per_lembar(berparameter, 250, tabel, date(2026, 7, 1))[0] == 2


# ---------------------------------------------------------------------------------------
# Rumus PRD 9.7 (murni, tanpa basis data)
# ---------------------------------------------------------------------------------------


def test_lembar_mentah_mengikuti_rumus_prd_9_7() -> None:
    """(ekuitas × risiko) ÷ (harga masuk − stop + biaya & slippage), bukan pendekatan lain."""
    hasil = _hitung()

    assert hasil.anggaran_risiko == 1_875_000  # 0,75% × 250 juta
    assert hasil.risiko_per_lembar == 2_320 - 2_240 + 14
    assert hasil.lembar_mentah == Fraction(1_875_000, 94)


def test_ukuran_akhir_dibatasi_bobot_dan_dibulatkan_per_lot() -> None:
    """10% × 250 juta = Rp 25 juta = 10.775,86 lembar → 10.700 lembar (107 lot)."""
    hasil = _hitung()

    assert hasil.maks_lembar_bobot == 10_700
    assert hasil.lembar == 10_700
    assert hasil.lembar % LOT == 0
    assert hasil.pembatasan and "bobot maksimum per posisi" in hasil.pembatasan[0]


def test_risiko_nominal_dihitung_dari_ukuran_akhir() -> None:
    """PRD 10: risiko nominal selalu dari ukuran akhir — bukan dari ukuran mentah."""
    hasil = _hitung()

    assert hasil.risiko_nominal == hasil.lembar * hasil.risiko_per_lembar
    assert hasil.risiko_nominal < int(hasil.lembar_mentah) * hasil.risiko_per_lembar


def test_batas_likuiditas_dua_persen_dari_adtv20() -> None:
    """2% × Rp 4,64 miliar = Rp 92,8 juta ÷ 2.320 = 40.000 lembar."""
    hasil = _hitung(adtv20=ADTV20)

    assert hasil.maks_lembar_likuiditas == 40_000
    assert hasil.lembar == 10_700  # bobot masih lebih ketat


def test_batas_likuiditas_menjadi_penentu_bila_lebih_ketat() -> None:
    hasil = _hitung(adtv20=1_160_000_000)  # 2% = Rp 23,2 juta → 10.000 lembar

    assert hasil.maks_lembar_likuiditas == 10_000
    assert hasil.lembar == 10_000
    assert any("ADTV20" in satu for satu in hasil.pembatasan)


def test_batas_kas_menghitung_biaya_bukan_hanya_harga() -> None:
    """Kas harus menutup harga **dan** biaya per lembar — kalau tidak, ukurannya kelebihan."""
    hasil = _hitung(kas=1_000_000)

    assert hasil.maks_lembar_kas == 400  # 1.000.000 ÷ (2.320 + 14) = 428,4 → 400
    assert hasil.lembar == 400


def test_batas_kas_yang_belum_dicatat_tidak_dinilai() -> None:
    """`None` berarti datanya tidak ada — bukan kas nol, dan bukan batas longgar."""
    hasil = _hitung(kas=None)

    assert hasil.maks_lembar_kas is None
    assert any("kas tersedia" in satu for satu in hasil.batas_tidak_dinilai)
    assert not hasil.pelanggaran


def test_batas_sektor_memakai_paparan_yang_sudah_ada() -> None:
    """30% × 250 juta = Rp 75 juta; sudah terpakai Rp 70 juta → sisa Rp 5 juta → 2.100 lembar."""
    hasil = _hitung(nilai_sektor=70_000_000)

    assert hasil.maks_lembar_sektor == 2_100
    assert hasil.lembar == 2_100
    assert any("sektor" in satu for satu in hasil.pembatasan)


def test_sektor_yang_belum_terisi_disebut_tidak_dinilai() -> None:
    """K25: dua kolom sektor bisa kosong bersama — dan itu dikatakan, bukan dianggap longgar."""
    hasil = _hitung(nilai_sektor=None)

    assert hasil.maks_lembar_sektor is None
    pesan = " ".join(hasil.batas_tidak_dinilai)
    assert "sektor_idx_ic" in pesan and "sektor_sumber" in pesan
    assert any("TIDAK DINILAI" in satu for satu in hasil.catatan)


def test_semua_batas_tidak_dinilai_tetap_tidak_menghasilkan_pelanggaran() -> None:
    """Tidak dinilai ≠ dilanggar; keduanya harus terbedakan di keluaran."""
    hasil = _hitung(adtv20=None, kas=None, nilai_sektor=None)

    assert len(hasil.batas_tidak_dinilai) == 3
    assert hasil.pelanggaran == ()
    assert hasil.lembar == 10_700


def test_peringatan_risiko_eksekusi_selalu_ada() -> None:
    """PRD 9.7: gap, ARB, dan suspensi bisa membuat stop tidak tereksekusi pada harganya."""
    hasil = _hitung()

    assert any("risiko eksekusi" in satu for satu in hasil.catatan)
    assert any("batas bawah" in satu or "melebihi risiko nominal" in satu for satu in hasil.catatan)


def test_total_risiko_melewati_batas_menghasilkan_pelanggaran_dan_ukuran_patuh() -> None:
    """PRD 9.7 "Perilaku menolak": pelanggaran ditampilkan **beserta** ukuran yang patuh."""
    hasil = _hitung(risiko_berjalan=12_000_000)

    assert hasil.pelanggaran and hasil.pelanggaran[0].batas == risiko.TOTAL_RISIKO_MAKSIMUM
    assert hasil.total_risiko_bp > 500
    # Ukuran akhir 10.700 lembar (dibatasi bobot) berisiko Rp 1.005.800; ditambah Rp 12 juta
    # menjadi 5,20% ekuitas. Pagu yang tersisa: 5% × 250 juta − 12 juta = Rp 500.000 ÷ 94
    # = 5.319 lembar → 5.300 lembar.
    assert hasil.lembar_patuh_total_risiko == 5_300
    assert hasil.ukuran_patuh == min(
        hasil.lembar, hasil.maks_lembar_bobot, hasil.lembar_patuh_total_risiko
    )


def test_stop_di_atas_harga_masuk_ditolak() -> None:
    """Posisi ini hanya beli (long): stop di atas harga masuk berarti risiko negatif."""
    with pytest.raises(risiko.GalatRisiko, match="risiko negatif"):
        _hitung(stop=CLOSE + 10)


def test_jenis_stop_tak_dikenal_ditolak() -> None:
    with pytest.raises(risiko.GalatRisiko, match="jenis stop"):
        _hitung(jenis_stop="telepon broker")


def test_dasar_stop_tak_dikenal_ditolak() -> None:
    with pytest.raises(risiko.GalatRisiko, match="dasar_stop"):
        _hitung(dasar_stop="perasaan")


def test_ekuitas_nol_ditolak() -> None:
    with pytest.raises(risiko.GalatRisiko, match="ekuitas"):
        _hitung(ekuitas=0)


def test_pakai_ukuran_menghitung_ulang_seluruh_angka_turunan() -> None:
    """Kalau hanya kolom `lembar` yang diganti, rencananya berbohong tentang risikonya."""
    hasil = _hitung(risiko_berjalan=12_000_000)
    patuh = risiko.pakai_ukuran(
        hasil, hasil.ukuran_patuh, lot=LOT, batas_total_bp=500
    )

    assert patuh.lembar == hasil.ukuran_patuh
    assert patuh.nilai_posisi == patuh.lembar * patuh.harga_masuk
    assert patuh.bobot_bp == patuh.nilai_posisi * 10000 // patuh.ekuitas
    assert patuh.risiko_nominal == patuh.lembar * patuh.risiko_per_lembar
    assert patuh.total_risiko_bp == (patuh.risiko_berjalan + patuh.risiko_nominal) * 10000 // patuh.ekuitas
    assert patuh.pelanggaran == ()


def test_pakai_ukuran_yang_bukan_kelipatan_lot_ditolak() -> None:
    hasil = _hitung()

    with pytest.raises(risiko.GalatRisiko, match="kelipatan lot"):
        risiko.pakai_ukuran(hasil, 10_750, lot=LOT, batas_total_bp=500)


def test_pakai_ukuran_yang_lebih_besar_dari_hitungan_disebut_pelanggaran() -> None:
    """Ukuran yang dinaikkan pengguna adalah keputusan, tetapi tidak boleh tersamar sebagai hasil."""
    hasil = _hitung()
    naik = risiko.pakai_ukuran(hasil, 11_000, lot=LOT, batas_total_bp=500)

    assert naik.pelanggaran and naik.pelanggaran[0].batas == risiko.BOBOT_MAKSIMUM


# ---------------------------------------------------------------------------------------
# Stop bawaan (PRD 9.7): max(harga masuk − 2 × ATR14, harga pembatal tesis)
# ---------------------------------------------------------------------------------------


def test_stop_bawaan_dari_atr_dibulatkan_ke_bawah_ke_tick_sah(siap: sqlite3.Connection) -> None:
    """ATR14 = 40 → 2.320 − 80 = 2.240 (sudah tick sah). Arah pembulatan diuji terpisah."""
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))

    stop, dasar, catatan = risiko.stop_bawaan(masukan, CLOSE)

    assert masukan.atr14.ada and float(masukan.atr14.nilai) == pytest.approx(RENTANG)
    assert (stop, dasar) == (2_240, "harga_masuk_minus_2_atr14")
    assert catatan == ()


def test_stop_atr_yang_sudah_tick_sah_tidak_diubah(siap: sqlite3.Connection) -> None:
    """ATR deret uji = 40 → 2.320 − 80 = 2.240, sudah tick sah, jadi tidak ada catatan pembulatan."""
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))

    stop, dasar, catatan = risiko.stop_bawaan(masukan, CLOSE)

    assert masukan.atr14.ada and float(masukan.atr14.nilai) == pytest.approx(RENTANG)
    assert (stop, dasar) == (2_240, "harga_masuk_minus_2_atr14")
    assert catatan == ()


def test_stop_atr_yang_bukan_tick_dibulatkan_ke_bawah(siap: sqlite3.Connection) -> None:
    """2.320 − 2 × 66,18 = 2.187,64 → **2.180**: risiko jadi lebih besar, bukan lebih kecil."""
    masukan = _masukan_dengan_atr(
        risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1)), 66.18
    )

    stop, _dasar, catatan = risiko.stop_bawaan(masukan, CLOSE)

    assert stop == 2_180
    assert any("dibulatkan ke bawah" in satu for satu in catatan)


def test_harga_pembatal_yang_lebih_ketat_menjadi_stop(siap: sqlite3.Connection) -> None:
    """PRD 9.7: stop mengikuti tesis bila lebih ketat."""
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))

    stop, dasar, catatan = risiko.stop_bawaan(masukan, CLOSE, harga_pembatal=2_300)

    assert (stop, dasar) == (2_300, "harga_pembatal")
    assert any("pembatal tesis" in satu for satu in catatan)


def test_harga_pembatal_yang_bukan_tick_ditolak(siap: sqlite3.Connection) -> None:
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))

    with pytest.raises(risiko.GalatRisiko, match="harga pembatal"):
        risiko.stop_bawaan(masukan, CLOSE, harga_pembatal=2_303)


def test_stop_tidak_bisa_diturunkan_saat_atr_dan_pembatal_sama_sama_tidak_ada(
    siap: sqlite3.Connection,
) -> None:
    masukan = _masukan_tanpa_atr(risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1)))

    with pytest.raises(risiko.GalatRisiko, match="--stop"):
        risiko.stop_bawaan(masukan, CLOSE)


def _masukan_dengan_atr(masukan: risiko.MasukanRisiko, atr: float) -> risiko.MasukanRisiko:
    """Salinan masukan dengan ATR14 diganti — untuk menguji arah pembulatan tanpa data baru."""
    return replace(
        masukan, atr14=masukan.atr14.__class__(nama="atr14_rupiah", nilai=atr, satuan="rupiah")
    )


def _masukan_tanpa_atr(masukan: risiko.MasukanRisiko) -> risiko.MasukanRisiko:
    return replace(masukan, atr14=metrik.tidak_dihitung("atr14_rupiah", "rupiah", "harga tidak siap"))


# ---------------------------------------------------------------------------------------
# Masukan dari basis data: ekuitas harian, kas, risiko berjalan
# ---------------------------------------------------------------------------------------


def test_ekuitas_harian_append_only_dan_revisinya_terbaca(sambungan: sqlite3.Connection) -> None:
    risiko.catat_ekuitas(sambungan, ekuitas=100_000_000, kas=0, tanggal=date(2026, 7, 1))
    risiko.catat_ekuitas(sambungan, ekuitas=120_000_000, tanggal=date(2026, 7, 1))
    risiko.catat_ekuitas(sambungan, ekuitas=90_000_000, tanggal=date(2026, 7, 3))

    terakhir = risiko.ekuitas_terakhir(sambungan, date(2026, 7, 2))

    assert terakhir is not None and terakhir.ekuitas == 120_000_000
    assert sambungan.execute("SELECT COUNT(*) FROM ekuitas_harian").fetchone()[0] == 3
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sambungan.execute("UPDATE ekuitas_harian SET ekuitas = 1")


def test_kas_nol_berbeda_dari_kas_belum_dicatat(sambungan: sqlite3.Connection) -> None:
    """Aturan keras 2: 0 berarti "kas kosong", NULL berarti "belum dicatat"."""
    risiko.catat_ekuitas(sambungan, ekuitas=100_000_000, kas=0, tanggal=date(2026, 7, 1))
    risiko.catat_ekuitas(sambungan, ekuitas=100_000_000, tanggal=date(2026, 7, 2))

    assert risiko.ekuitas_terakhir(sambungan, date(2026, 7, 1)).kas == 0
    assert risiko.ekuitas_terakhir(sambungan, date(2026, 7, 2)).kas is None


def test_ekuitas_nol_ditolak(sambungan: sqlite3.Connection) -> None:
    with pytest.raises(risiko.GalatRisiko, match="ekuitas"):
        risiko.catat_ekuitas(sambungan, ekuitas=0)


def test_hitung_tanpa_ekuitas_tercatat_menyebut_cara_mengisinya(
    berparameter: sqlite3.Connection, data: sqlite3.Connection
) -> None:
    risiko.simpan_preset(berparameter, _preset())

    with pytest.raises(risiko.GalatRisiko, match="--ekuitas-harian"):
        risiko.siapkan_masukan(berparameter, KODE, pada=date(2026, 7, 1))


def test_hitung_memakai_penutupan_terakhir_dibulatkan_ke_tick(siap: sqlite3.Connection) -> None:
    """Harga masuk bawaan dari data: penutupan terakhir dibulatkan ke bawah ke tick sah."""
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))

    assert masukan.harga_acuan == CLOSE
    assert masukan.lot == LOT
    assert masukan.ekuitas == 250_000_000
    assert masukan.kas == 100_000_000
    assert masukan.sektor == SEKTOR


def test_risiko_berjalan_menjumlahkan_rencana_tersimpan(siap: sqlite3.Connection) -> None:
    entri = kandidat.buat(
        siap,
        KODE,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_240,
        tanggal_tinjau="2026-08-01",
    )
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))
    hasil, _stop = risiko.hitung_untuk(masukan, harga_masuk=CLOSE)
    risiko.simpan(
        siap,
        hasil,
        id_kandidat=entri.id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )

    berjalan, rincian = risiko.risiko_berjalan(siap)

    assert berjalan == hasil.risiko_nominal
    assert rincian and "rencana #1" in rincian[0]
    nilai_sektor, dikecualikan = risiko.nilai_sektor_berjalan(siap, "sektor_idx_ic", SEKTOR)
    assert nilai_sektor == hasil.nilai_posisi
    assert dikecualikan == 0


def test_pilih_sektor_mendahulukan_idx_ic() -> None:
    """K25: `sektor_idx_ic` menang begitu terisi; `sektor_sumber` hanya selama ia kosong."""
    from types import SimpleNamespace

    lengkap = SimpleNamespace(sektor_idx_ic="keuangan", sektor_sumber="Financials")
    hanya_sumber = SimpleNamespace(sektor_idx_ic=None, sektor_sumber="Energy")
    kosong = SimpleNamespace(sektor_idx_ic=None, sektor_sumber=None)

    assert risiko.pilih_sektor(lengkap) == ("sektor_idx_ic", "keuangan")
    assert risiko.pilih_sektor(hanya_sumber) == ("sektor_sumber", "Energy")
    assert risiko.pilih_sektor(kosong) == (None, None)


def _simpan_emiten_tambahan(
    sambungan: sqlite3.Connection, kode: str, **atribut: str | None
) -> None:
    """Tambah satu emiten + deret harganya lewat jalur nyata (bukan INSERT tangan)."""
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=(Emiten(kode=kode, nama=f"Emiten {kode}", sumber="uji-rujukan", **atribut),),  # type: ignore[arg-type]
            harga_harian=_deret(kode),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )


def test_batas_sektor_dinilai_dari_sektor_sumber_bila_idx_ic_kosong(
    siap: sqlite3.Connection,
) -> None:
    """K25: tanpa `sektor_idx_ic`, batas 30% tetap ditegakkan — dan taksonominya disebut."""
    _simpan_emiten_tambahan(siap, "CCCC", sektor_sumber="Energy")

    masukan = risiko.siapkan_masukan(siap, "CCCC", pada=date(2026, 7, 1))
    hasil, _stop = risiko.hitung_untuk(masukan, harga_masuk=CLOSE)

    assert masukan.sektor_kolom == "sektor_sumber"
    assert masukan.sektor == "Energy"
    assert masukan.nilai_sektor == 0
    assert hasil.maks_lembar_sektor is not None, "batas sektor sekarang DINILAI, bukan dilewati"
    assert hasil.batas_tidak_dinilai == ()
    assert any("sektor_sumber" in satu for satu in masukan.catatan)


def test_rencana_tanpa_sektor_tidak_ikut_dijumlahkan_dan_dilaporkan(
    siap: sqlite3.Connection,
) -> None:
    """Rencana yang sektornya tidak diketahui tidak boleh diam-diam memperkecil paparan sektor."""
    _simpan_emiten_tambahan(siap, "DDDD")
    entri = kandidat.buat(
        siap,
        "DDDD",
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_240,
        tanggal_tinjau="2026-08-01",
    )
    masukan = risiko.siapkan_masukan(siap, "DDDD", pada=date(2026, 7, 1))
    hasil, _stop = risiko.hitung_untuk(masukan, harga_masuk=CLOSE)
    risiko.simpan(
        siap,
        hasil,
        id_kandidat=entri.id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )

    nilai, dikecualikan = risiko.nilai_sektor_berjalan(siap, "sektor_idx_ic", SEKTOR)

    assert (nilai, dikecualikan) == (0, 1)
    # Dan kalkulator untuk emiten ber-sektor menyebut pengecualian itu di catatannya.
    _simpan_emiten_tambahan(siap, "CCCC", sektor_sumber="Energy")
    masukan_cc = risiko.siapkan_masukan(siap, "CCCC", pada=date(2026, 7, 1))
    assert masukan_cc.sektor_dikecualikan == 1
    assert any("tidak ikut dijumlahkan" in satu for satu in masukan_cc.catatan)
    hasil_cc, _stop_cc = risiko.hitung_untuk(masukan_cc, harga_masuk=CLOSE)
    assert any("tidak dapat diatribusikan ke sektor" in satu for satu in hasil_cc.pembatasan)


def test_kolom_sektor_tak_dikenal_ditolak(siap: sqlite3.Connection) -> None:
    with pytest.raises(risiko.GalatRisiko, match="kolom sektor"):
        risiko.nilai_sektor_berjalan(siap, "sektor_karangan", "Energy")


# ---------------------------------------------------------------------------------------
# Rencana tersimpan: bentuk yang ditegakkan mesin, dan perilaku menolak PRD 9.7
# ---------------------------------------------------------------------------------------


def _rencana_siap(siap: sqlite3.Connection) -> tuple[risiko.HasilRisiko, risiko.MasukanRisiko, int]:
    entri = kandidat.buat(
        siap,
        KODE,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_240,
        tanggal_tinjau="2026-08-01",
    )
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))
    hasil, _stop = risiko.hitung_untuk(masukan, harga_masuk=CLOSE)
    return hasil, masukan, entri.id_kandidat


def test_simpan_rencana_menyimpan_seluruh_keluaran_kalkulator(siap: sqlite3.Connection) -> None:
    hasil, masukan, id_kandidat = _rencana_siap(siap)

    rencana = risiko.simpan(
        siap,
        hasil,
        id_kandidat=id_kandidat,
        jenis_stop="cek_penutupan",
        id_snapshot=masukan.potret.id_snapshot,
    )

    assert rencana.revisi == 1
    assert rencana.lembar == hasil.lembar
    assert rencana.lembar_mentah_mili == int(hasil.lembar_mentah * 1000)
    assert rencana.id_preset_risiko == "risiko-bawaan/v1"
    assert rencana.jenis_stop == "cek_penutupan"
    assert rencana.maks_lembar_sektor is not None, "emiten uji punya sektor, jadi batasnya dinilai"
    assert rencana.batas_tidak_dinilai is None


def test_batas_yang_tidak_dinilai_ikut_tersimpan_saat_datanya_tidak_ada(
    siap: sqlite3.Connection,
) -> None:
    """Rencana yang lolos karena datanya tidak ada tidak boleh terbaca sama dengan yang benar."""
    hasil, masukan, id_kandidat = _rencana_siap(siap)
    # Emiten uji punya sektor, jadi batasnya memang dinilai; di sini keadaannya dibuat seperti
    # data nyata hari ini (sektor belum terisi) supaya yang diuji adalah **apa yang tersimpan**.
    tanpa_sektor = replace(
        risiko.pakai_ukuran(hasil, hasil.lembar, lot=LOT, batas_total_bp=500),
        maks_lembar_sektor=None,
        batas_tidak_dinilai=("bobot maksimum per sektor tidak dinilai: sektor belum terisi",),
        catatan=(),
    )

    rencana = risiko.simpan(
        siap,
        tanpa_sektor,
        id_kandidat=id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )

    assert rencana.batas_tidak_dinilai == "bobot maksimum per sektor tidak dinilai: sektor belum terisi"
    assert "BATAS TIDAK DINILAI" in risiko.ringkas_daftar([rencana])


def test_simpan_menolak_jenis_stop_yang_tidak_disebut(siap: sqlite3.Connection) -> None:
    hasil, masukan, id_kandidat = _rencana_siap(siap)

    with pytest.raises(risiko.GalatRisiko, match="jenis stop"):
        risiko.simpan(
            siap,
            hasil,
            id_kandidat=id_kandidat,
            jenis_stop="",
            id_snapshot=masukan.potret.id_snapshot,
        )


def test_simpan_menolak_pelanggaran_tanpa_pilihan_pengguna(siap: sqlite3.Connection) -> None:
    """PRD 9.7: rencana hanya bisa disimpan setelah pengguna memilih salah satu."""
    _hasil, masukan, id_kandidat = _rencana_siap(siap)
    # Ukuran akhir (10.700 lembar, dibatasi bobot) berisiko Rp 1.005.800; risiko berjalan
    # Rp 12 juta membuat totalnya 5,20% — di atas batas 5%.
    hasil_pelanggaran = _hitung(risiko_berjalan=12_000_000)
    assert hasil_pelanggaran.pelanggaran, "prasyarat uji: harus ada pelanggaran"

    with pytest.raises(risiko.GalatRisiko, match="ukuran yang patuh"):
        risiko.simpan(
            siap,
            hasil_pelanggaran,
            id_kandidat=id_kandidat,
            jenis_stop="order_sekuritas",
            id_snapshot=masukan.potret.id_snapshot,
        )

    diterima = risiko.simpan(
        siap,
        hasil_pelanggaran,
        id_kandidat=id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
        pelanggaran_diterima=True,
    )
    assert "PELANGGARAN DITERIMA" in (diterima.catatan or "")


def test_simpan_menolak_ukuran_nol(siap: sqlite3.Connection) -> None:
    hasil, masukan, id_kandidat = _rencana_siap(siap)
    nol = risiko.pakai_ukuran(hasil, 0, lot=LOT, batas_total_bp=500)

    with pytest.raises(risiko.GalatRisiko, match="nol lembar"):
        risiko.simpan(
            siap,
            nol,
            id_kandidat=id_kandidat,
            jenis_stop="order_sekuritas",
            id_snapshot=masukan.potret.id_snapshot,
        )


def test_rencana_berversi_dan_revisi_lama_tetap_ada(siap: sqlite3.Connection) -> None:
    hasil, masukan, id_kandidat = _rencana_siap(siap)
    pertama = risiko.simpan(
        siap,
        hasil,
        id_kandidat=id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )
    kedua = risiko.simpan(
        siap,
        risiko.pakai_ukuran(hasil, 1_000, lot=LOT, batas_total_bp=500),
        id_kandidat=id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
        id_rencana=pertama.id_rencana,
    )

    assert (kedua.id_rencana, kedua.revisi) == (pertama.id_rencana, 2)
    assert len(risiko.riwayat(siap, pertama.id_rencana)) == 2
    assert risiko.terkini(siap, pertama.id_rencana).lembar == 1_000
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        siap.execute("DELETE FROM rencana")


def test_check_stop_di_atas_harga_masuk_ditegakkan_mesin(siap: sqlite3.Connection) -> None:
    """Posisi ini hanya beli: stop di atas harga masuk selalu salah, dan dijaga `CHECK`."""
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        siap.execute(
            "INSERT INTO rencana (id_rencana, revisi, id_kandidat, kode, id_preset_risiko,"
            " id_snapshot, tanggal, ekuitas, risiko_per_posisi_bp, harga_masuk, stop, dasar_stop,"
            " biaya_slippage, lembar_mentah_mili, lembar, maks_lembar_bobot, bobot_bp,"
            " risiko_nominal, risiko_berjalan, total_risiko_bp, jenis_stop, dicatat_pada)"
            " VALUES (9, 1, 1, ?, 'risiko-bawaan/v1', 1, '2026-07-01', 250000000, 75, 1000, 2000,"
            " 'pengguna', 0, 0, 0, 0, 0, 0, 0, 0, 'order_sekuritas', '2026-07-01T09:00:00+07:00')",
            (KODE,),
        )


def test_daftar_rencana_dan_ringkasannya(siap: sqlite3.Connection) -> None:
    hasil, masukan, id_kandidat = _rencana_siap(siap)
    risiko.simpan(
        siap,
        hasil,
        id_kandidat=id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )

    teks = risiko.ringkas_daftar(risiko.daftar(siap, kode=KODE))

    assert "#1 r1" in teks and KODE in teks
    assert "lembar" in teks and "stop" in teks
    assert risiko.daftar(siap, kode="ZZZZ") == ()
    assert risiko.ringkas_daftar(()) == "(belum ada rencana tersimpan)"


# ---------------------------------------------------------------------------------------
# Alur lengkap lewat baris perintah (AC-11): kandidat → kalkulator → rencana
# ---------------------------------------------------------------------------------------


def _siapkan_kandidat(sambungan: sqlite3.Connection, kode: str = KODE) -> int:
    entri = kandidat.buat(
        sambungan,
        kode,
        status="watchlist",
        tesis="uji alur",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_240,
        tanggal_tinjau="2026-08-01",
    )
    return entri.id_kandidat


def test_kalkulator_menolak_kode_tanpa_kandidat_watchlist(siap: sqlite3.Connection) -> None:
    kode_keluar = cli.main(["--hitung-risiko", KODE_LAIN, "--jenis-stop", "order_sekuritas"])

    assert kode_keluar == cli.KODE_GAGAL


def test_kalkulator_menyimpan_rencana_lalu_memindahkan_status_kandidat(
    siap: sqlite3.Connection,
) -> None:
    id_kandidat = _siapkan_kandidat(siap)

    kode_keluar = cli.main(
        [
            "--hitung-risiko",
            KODE,
            "--harga-masuk",
            str(CLOSE),
            "--jenis-stop",
            "order_sekuritas",
            "--simpan-rencana",
        ]
    )

    assert kode_keluar == cli.KODE_OK
    assert kandidat.wajib_ada(siap, id_kandidat).status == "rencana"
    tersimpan = risiko.daftar(siap)
    assert len(tersimpan) == 1 and tersimpan[0].kode == KODE


def test_simpan_rencana_tanpa_jenis_stop_keluar_gagal(siap: sqlite3.Connection) -> None:
    _siapkan_kandidat(siap)

    kode_keluar = cli.main(["--hitung-risiko", KODE, "--simpan-rencana"])

    assert kode_keluar == cli.KODE_GAGAL
    assert risiko.daftar(siap) == ()


def test_batas_risiko_bawaan_lewat_baris_perintah_idempoten(siap: sqlite3.Connection) -> None:
    assert cli.main(["--batas-risiko-bawaan"]) == cli.KODE_OK
    assert cli.main(["--batas-risiko-bawaan"]) == cli.KODE_OK
    assert siap.execute("SELECT COUNT(*) FROM preset_risiko").fetchone()[0] == 1


# ---------------------------------------------------------------------------------------
# Satu jalur simpan rencana untuk dua mode (T69, aksi #19)
# ---------------------------------------------------------------------------------------


def _rencana_untuk(siap: sqlite3.Connection) -> tuple[risiko.HasilRisiko, risiko.MasukanRisiko]:
    """Hasil kalkulator apa adanya untuk kode uji — sama dengan yang dipakai panel jendela."""
    entri = kandidat.untuk_rencana(siap, KODE)
    masukan = risiko.siapkan_masukan(siap, KODE)
    hasil, _stop = risiko.hitung_untuk(
        masukan,
        harga_masuk=masukan.harga_acuan,
        harga_pembatal=entri.harga_pembatal,
        jenis_stop="order_sekuritas",
    )
    return hasil, masukan


def test_simpan_dari_kandidat_memindahkan_status_watchlist(siap: sqlite3.Connection) -> None:
    id_kandidat = _siapkan_kandidat(siap)
    hasil, masukan = _rencana_untuk(siap)

    tersimpan = risiko.simpan_dari_kandidat(
        siap,
        hasil,
        entri=kandidat.wajib_ada(siap, id_kandidat),
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )

    assert tersimpan.status_dipindahkan is True and tersimpan.peringatan is None
    assert tersimpan.rencana.kode == KODE
    assert kandidat.wajib_ada(siap, id_kandidat).status == "rencana"


def test_simpan_dari_kandidat_menolak_status_yang_tidak_sah(siap: sqlite3.Connection) -> None:
    """Rencana baru menuntut `watchlist`, revisi menuntut id rencananya (PRD 9.6)."""
    entri = kandidat.buat(siap, KODE, status="ide")
    masukan = risiko.siapkan_masukan(siap, KODE)

    with pytest.raises(risiko.GalatRisiko) as galat:
        risiko.simpan_dari_kandidat(
            siap,
            _hitung(),
            entri=entri,
            jenis_stop="order_sekuritas",
            id_snapshot=masukan.potret.id_snapshot,
        )

    assert "berstatus 'ide'" in str(galat.value)
    assert "--rencana-revisi" in str(galat.value)
    assert risiko.daftar(siap) == (), "tidak ada rencana yang tersimpan saat ditolak"


def test_pindah_status_yang_gagal_dilaporkan_tanpa_membatalkan_rencana(
    siap: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rencananya sudah tersimpan saat perpindahan gagal — dan itu dikatakan apa adanya.

    Ini satu-satunya keadaan di mana "belum menulis apa pun" **tidak** berlaku: barisnya ada.
    Karena itu kegagalannya dilaporkan sebagai `peringatan`, bukan sebagai kegagalan penuh.
    """
    id_kandidat = _siapkan_kandidat(siap)
    hasil, masukan = _rencana_untuk(siap)

    def gagal(*argumen: object, **kunci: object) -> object:
        raise kandidat.GalatKandidat("ditolak uji")

    monkeypatch.setattr(kandidat, "ubah", gagal)
    tersimpan = risiko.simpan_dari_kandidat(
        siap,
        hasil,
        entri=kandidat.wajib_ada(siap, id_kandidat),
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )

    assert tersimpan.status_dipindahkan is False
    assert tersimpan.peringatan is not None
    assert "tersimpan, tetapi status kandidat" in tersimpan.peringatan
    assert len(risiko.daftar(siap)) == 1, "rencananya tetap ada"
    assert kandidat.wajib_ada(siap, id_kandidat).status == "watchlist"


def test_ekuitas_harian_lewat_baris_perintah_tercatat(siap: sqlite3.Connection) -> None:
    assert cli.main(["--ekuitas-harian", "300000000", "--kas", "50000000"]) == cli.KODE_OK

    tercatat = risiko.ekuitas_terakhir(siap)
    assert tercatat is not None and tercatat.ekuitas == 300_000_000 and tercatat.kas == 50_000_000
