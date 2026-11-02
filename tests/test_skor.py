"""Uji skoring F3 (PRD 9.5) — `mejasaham/skor.py`.

Empat janji yang diuji di sini, dan semuanya bisa salah tanpa terlihat di layar:

* **Statistik populasi (ddof=0)** untuk z-score sektor (K10/P10). Selisihnya kecil tetapi
  menggeser setiap skor, dan tidak ada cara melihatnya dari satu angka saja.
* **Metrik yang tidak dihitung tidak diberi nilai nol** (aturan keras 2, AC-3). Bobotnya
  dialihkan, faktornya dinilai hanya bila ≥ 60% bobot metriknya tersedia, dan emiten hanya
  diperingkat bila ≥ 3 dari 4 faktornya dinilai — semuanya tertulis di penjelasan.
* **AC-17**: sektor dengan < 8 emiten likuid memakai statistik seluruh semesta likuid, dan hal
  itu tertulis (`fallback_sektor`). Sektor yang cukup besar memakai statistiknya sendiri.
* **Seri diputus ADTV20 lebih besar, lalu kode** (PRD 9.5, AC-2), dan `simpan_skor` menulis
  ulang alih-alih menumpuk — dengan `NULL` yang tetap berarti "tidak dinilai".

Semesta uji dibangun lewat jalur nyata (`ingesti.simpan` → `potret.muat`). Nilai metrik untuk
skoringnya sendiri diserahkan apa adanya sebagai `metrik.Nilai`, karena justru **aritmetika
z-score** yang sedang diuji: dengan rata-rata & simpangan yang ditulis di uji, setiap skor bisa
diperiksa tangan (`z = +3 → 100`, `z = +1 → 66,667`, `z = 0 → 50`).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from datetime import date, datetime, timedelta
from math import sqrt
from pathlib import Path

import pytest

from mejasaham import db, ingesti, lokasi, metrik, potret, saring, skor
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    HargaHarian,
    KumpulanData,
)
from mejasaham.metrik import Nilai
from mejasaham.potret import Potret
from mejasaham.saring import BobotMetrik, Preset
from mejasaham.skor import HasilSkor, StatistikMetrik

SUMBER = "uji"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
SEKTOR = "industri"
CLOSE = 1_000

#: Skor tiap metrik uji, dihitung dari rata-rata & simpangan di `_statistik_uji`:
#: ROE 0,30 pada rata-rata 0,10 & simpangan 0,10 → z = +2 → (2+3)/6 x 100 = 83,333;
#: CFO/NI 1,00 pada rata-rata 1,00 → z = 0 → 50;
#: DER 0,50 pada rata-rata 1,00 & simpangan 0,50 → z = −1, dibalik (rendah lebih baik) → 66,667.
SKOR_ROE = (2 + 3) / 6 * 100
SKOR_CFO = 50.0
SKOR_DER = (1 + 3) / 6 * 100


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


def _n(nama: str, nilai: float, satuan: str = "rasio") -> Nilai:
    """Satu metrik yang sudah dihitung — masukannya `skor_emiten`, bukan hasil perhitungan."""
    return Nilai(nama=nama, nilai=nilai, satuan=satuan, asal="uji")


def _stat(
    rata_rata: float, simpangan: float, jumlah: int = 11, *, dari_fallback: bool = False
) -> StatistikMetrik:
    return StatistikMetrik(
        rata_rata=rata_rata, simpangan=simpangan, jumlah=jumlah, dari_fallback=dari_fallback
    )


def _statistik_uji() -> dict[str, StatistikMetrik]:
    return {
        "roe_5t": _stat(0.10, 0.10),
        "cfo_ni": _stat(1.00, 0.50),
        "der": _stat(1.00, 0.50),
        "per": _stat(10.0, 5.0),
        "momentum_12_1": _stat(0.10, 0.10),
    }


def _preset(*bobot_metrik: BobotMetrik, bobot: Mapping[str, int], id_preset: str = "uji-skor") -> Preset:
    return Preset(
        id_preset=id_preset,
        nama=id_preset,
        versi=1,
        horizon="bulanan",
        dibuat_pada=TANGGAL,
        keterangan="preset uji skoring",
        kriteria=(),
        bobot_faktor=dict(bobot),
        bobot_metrik=bobot_metrik,
    )


def _preset_kualitas() -> Preset:
    """Satu faktor dengan tiga metrik berbobot 50/30/20 supaya pengalihan bobot terlihat."""
    return _preset(
        BobotMetrik("kualitas", "roe_5t", "umum", 5000, "tinggi_baik"),
        BobotMetrik("kualitas", "cfo_ni", "umum", 3000, "tinggi_baik"),
        BobotMetrik("kualitas", "der", "umum", 2000, "rendah_baik"),
        bobot={"kualitas": 10000},
    )


def _preset_satu_metrik(nama: str = "roe_5t", arah: str = "tinggi_baik") -> Preset:
    return _preset(
        BobotMetrik("kualitas", nama, "umum", 10000, arah),
        bobot={"kualitas": 10000},
    )


def _preset_tiga_faktor() -> Preset:
    """Tiga faktor dinilai — syarat minimum supaya emiten diperingkat (PRD 9.5)."""
    return _preset(
        BobotMetrik("kualitas", "roe_5t", "umum", 10000, "tinggi_baik"),
        BobotMetrik("nilai", "per", "umum", 10000, "rendah_baik"),
        BobotMetrik("momentum", "momentum_12_1", "umum", 10000, "tinggi_baik"),
        bobot={"kualitas": 4000, "nilai": 3000, "momentum": 3000},
    )


def _preset_empat_faktor() -> Preset:
    return _preset(
        BobotMetrik("kualitas", "roe_5t", "umum", 10000, "tinggi_baik"),
        BobotMetrik("nilai", "per", "umum", 10000, "rendah_baik"),
        BobotMetrik("momentum", "momentum_12_1", "umum", 10000, "tinggi_baik"),
        BobotMetrik("volatilitas", "volatilitas_60h", "umum", 10000, "rendah_baik"),
        bobot={"kualitas": 2500, "nilai": 2500, "momentum": 2500, "volatilitas": 2500},
    )


def _nilai_tiga(nilai: float = 0.30, per: float = 10.0, momentum: float = 0.20) -> dict[str, Nilai]:
    return {
        "roe_5t": _n("roe_5t", nilai),
        "per": _n("per", per),
        "momentum_12_1": _n("momentum_12_1", momentum),
    }


def _simpan_emiten(sambungan: sqlite3.Connection, volume: Mapping[str, int]) -> Potret:
    """Snapshot uji: emiten + 20 baris harga, dan ADTV20 = 1.000 x `volume` per emiten.

    ADTV20 sengaja datang dari data harga yang benar-benar ditulis, bukan dari angka yang
    ditempel: pemutus seri peringkat (PRD 9.5) membacanya dari sana.
    """
    emiten = tuple(
        Emiten(kode=kode, nama=f"Emiten {kode}", sektor_idx_ic=SEKTOR, sumber=SUMBER)
        for kode in volume
    )
    harga = tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=19 - i),
            close=CLOSE,
            volume=satu_volume,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for kode, satu_volume in volume.items()
        for i in range(20)
    )
    id_snapshot = ingesti.simpan(
        sambungan,
        KumpulanData(sumber=SUMBER, emiten=emiten, harga_harian=harga),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    ).id_snapshot
    return potret.muat(sambungan, id_snapshot)


def _hasil_seri() -> tuple[HasilSkor, ...]:
    """Empat emiten dengan nilai metrik **identik**, jadi skor totalnya pun identik."""
    preset = _preset_tiga_faktor()
    stats = _statistik_uji()
    return tuple(
        skor.skor_emiten(preset, kode, _nilai_tiga(), stats, jenis="umum")
        for kode in ("AAAA", "BBBB", "CCCC", "DDDD")
    )


# ---------------------------------------------------------------------------------------
# Pemetaan z (K10/P10, PRD 9.5)
# ---------------------------------------------------------------------------------------


def test_z_minus_3_memeta_ke_0_dan_z_plus_3_memeta_ke_100() -> None:
    """PRD 9.5/K10: pemetaannya linear — `z = −3 → 0`, `z = 0 → 50`, `z = +3 → 100`.

    Rata-rata 0,10 dan simpangan 0,10 membuat z-nya persis nilai dikurangi 0,1 dibagi 0,1:
    ROE 0,40 → +3 · 0,10 → 0 · −0,20 → −3. Ketiganya angka bulat supaya pemetaannya bisa
    diperiksa tanpa aproksimasi.
    """
    preset = _preset_satu_metrik()
    stats = {"roe_5t": _stat(0.10, 0.10)}

    for nilai, harapan in ((0.40, 100.0), (0.10, 50.0), (-0.20, 0.0)):
        hasil = skor.skor_emiten(
            preset, "AAAA", {"roe_5t": _n("roe_5t", nilai)}, stats, jenis="umum"
        )
        assert hasil.skor_faktor("kualitas") == pytest.approx(harapan), f"ROE {nilai}"


def test_z_dipotong_pada_plus_minus_3() -> None:
    """Nilai ekstrem tidak boleh memberi skor di luar 0–100 (K10/P10: "dipotong ±3").

    Tanpa pemotongan, z = +8 memberi skor 183 dan satu emiten ekstrem akan menarik rata-rata
    seluruh peringkat. Dengan pemotongan, 100 adalah batas atas yang tetap berarti "jauh di atas
    rata-rata" — bukan angka yang bergantung pada seberapa ekstrem outliersnya.
    """
    preset = _preset_satu_metrik()
    stats = {"roe_5t": _stat(0.10, 0.10)}

    tinggi = skor.skor_emiten(preset, "AAAA", {"roe_5t": _n("roe_5t", 0.90)}, stats, jenis="umum")
    rendah = skor.skor_emiten(preset, "BBBB", {"roe_5t": _n("roe_5t", -0.80)}, stats, jenis="umum")

    assert tinggi.skor_faktor("kualitas") == pytest.approx(100.0), "z = +8 dipotong ke +3"
    assert rendah.skor_faktor("kualitas") == pytest.approx(0.0), "z = −9 dipotong ke −3"


def test_arah_rendah_baik_membalik_pemetaan_z() -> None:
    """Metrik "makin rendah makin baik" (DER) arahnya dibalik **sebelum** dipetakan (K10/P10).

    Tanpa pembalikan, DER tinggi mendapat skor tinggi — dan emiten paling berutang akan tampak
    paling sehat. Di sini DER 0,40 (z = +3) harus menjadi 0, sedangkan DER −0,20 (z = −3, di bawah
    rata-rata) menjadi 100.
    """
    preset = _preset_satu_metrik("der", arah="rendah_baik")
    stats = {"der": _stat(0.10, 0.10)}

    tinggi = skor.skor_emiten(preset, "AAAA", {"der": _n("der", 0.40)}, stats, jenis="umum")
    rendah = skor.skor_emiten(preset, "BBBB", {"der": _n("der", -0.20)}, stats, jenis="umum")

    assert tinggi.skor_faktor("kualitas") == pytest.approx(0.0), "DER +3 simpangan → skor 0"
    assert rendah.skor_faktor("kualitas") == pytest.approx(100.0), "DER −3 simpangan → skor 100"


# ---------------------------------------------------------------------------------------
# Statistik populasi (ddof=0) — K10/P10
# ---------------------------------------------------------------------------------------


def test_statistik_sektor_memakai_simpangan_baku_populasi() -> None:
    """K10/P10: z-score sektor memakai simpangan baku **populasi** (ddof=0), bukan sampel.

    Delapan emiten likuid satu sektor dengan ROE 0,00 (tujuh kali) dan 3,00 (sekali): rata-ratanya
    3/8 = 0,375, variannya populasi 63/64 sehingga simpangannya √(63/64) ≈ 0,99216. Kalau ddof=1
    yang dipakai, simpangannya √(9/8) ≈ 1,06066 — sekitar 7% lebih besar, dan itu menggeser z
    setiap emiten di sektor ini tanpa jejak di layar.
    """
    angka = {
        f"E{i}": {"roe_5t": _n("roe_5t", 0.0 if i < 7 else 3.0)} for i in range(8)
    }
    sektor = {kode: SEKTOR for kode in angka}

    stats = skor.statistik_sektor(angka, sektor, tuple(angka), "roe_5t")

    satu = stats[SEKTOR]
    assert satu.jumlah == 8
    assert satu.dari_fallback is False, "delapan emiten likuid: statistik sektornya sendiri"
    assert satu.rata_rata == pytest.approx(3 / 8)
    assert satu.simpangan == pytest.approx(sqrt(63 / 64)), "populasi (ddof=0), bukan sampel (ddof=1)"

    # Dan z-nya benar-benar memakai simpangan itu: (3 − 0,375) ÷ √(63/64) = 2,6458.
    hasil = skor.skor_emiten(
        _preset_satu_metrik(), "E7", angka["E7"], {"roe_5t": satu}, jenis="umum"
    )
    z = hasil.faktor["kualitas"].kontribusi[0].z
    assert z == pytest.approx((3.0 - 3 / 8) / sqrt(63 / 64))


# ---------------------------------------------------------------------------------------
# AC-3: pengalihan bobot
# ---------------------------------------------------------------------------------------


def test_bobot_metrik_yang_tidak_dihitung_dinormalkan_atas_yang_tersedia() -> None:
    """AC-3/PRD 9.5: bobot metrik yang tidak tersedia dialihkan ke metrik yang tersedia.

    Tiga metrik berbobot 50/30/20 dengan skor 83,333 · 50 · 66,667. Tanpa DER, ketersediaannya
    80% (≥ 60%), jadi skor faktornya = (83,333x5000 + 50x3000) ÷ 8000 = 70,833.

    Menganggap DER yang tidak dihitung bernilai nol akan memberi (83,333x5000 + 50x3000) ÷ 10000 =
    56,667 — emiten yang datanya kurang tampak lebih buruk daripada emiten yang DER-nya buruk.
    Itulah yang dilarang aturan keras 2, dan dua angka itu sengaja dibedakan di sini.
    """
    preset = _preset_kualitas()
    stats = _statistik_uji()
    tanpa_der = {"roe_5t": _n("roe_5t", 0.30), "cfo_ni": _n("cfo_ni", 1.00)}

    hasil = skor.skor_emiten(preset, "AAAA", tanpa_der, stats, jenis="umum")
    kualitas = hasil.faktor["kualitas"]
    dihitung = {satu.metrik: satu for satu in kualitas.kontribusi if satu.status == "dihitung"}

    assert kualitas.ketersediaan == pytest.approx(0.8)
    assert dihitung["roe_5t"].skor == pytest.approx(SKOR_ROE)
    assert dihitung["cfo_ni"].skor == pytest.approx(SKOR_CFO)
    assert [satu.metrik for satu in kualitas.kontribusi if satu.status != "dihitung"] == ["der"]
    assert kualitas.skor == pytest.approx((SKOR_ROE * 5000 + SKOR_CFO * 3000) / 8000)
    assert kualitas.skor != pytest.approx((SKOR_ROE * 5000 + SKOR_CFO * 3000) / 10000), (
        "skor faktor bukan hasil menganggap metrik yang hilang bernilai nol"
    )
    der = next(satu for satu in kualitas.kontribusi if satu.metrik == "der")
    assert der.skor is None and der.bobot_efektif_bp == 0
    assert "dinormalkan" in kualitas.alasan


def test_faktor_dengan_ketersediaan_di_bawah_60_persen_tidak_dinilai_beserta_alasannya() -> None:
    """PRD 9.5: faktor dinilai hanya bila ≥ 60% bobot metriknya tersedia.

    Hanya ROE yang ada (50% bobot): faktornya berhenti dinilai — bukan dinilai dari sepotong data
    yang tersisa. Batas 60% itu menjaga agar "kualitas" tidak disimpulkan dari satu metrik saja,
    dan alasannya menyebut persentase, ambangnya, dan metrik yang hilang supaya bisa ditindaklanjuti.
    """
    preset = _preset_kualitas()
    stats = _statistik_uji()

    hasil = skor.skor_emiten(preset, "AAAA", {"roe_5t": _n("roe_5t", 0.30)}, stats, jenis="umum")
    kualitas = hasil.faktor["kualitas"]

    assert kualitas.ketersediaan == pytest.approx(0.5)
    assert kualitas.skor is None
    assert "50%" in kualitas.alasan and "60%" in kualitas.alasan
    assert "cfo_ni" in kualitas.alasan and "der" in kualitas.alasan, "sebutkan yang hilang"
    assert kualitas.bobot_efektif_bp == 0
    assert hasil.diperingkat is False


# ---------------------------------------------------------------------------------------
# PRD 9.5: syarat peringkat & penjelasannya
# ---------------------------------------------------------------------------------------


def test_emiten_dengan_kurang_dari_tiga_faktor_dinilai_tidak_diperingkat_tetapi_skor_totalnya_terisi() -> None:
    """PRD 9.5: peringkat menuntut ≥ 3 dari 4 faktor dinilai; skor totalnya tetap dihitung.

    Dua faktor dinilai (kualitas 83,333 dan nilai 66,667) berbobot sama 2500: bobot yang gugur
    dialihkan proporsional sehingga keduanya menjadi 5000/10000, dan skor totalnya = 83,333x0,5 +
    66,667x0,5 = 75. Angka itu tetap disimpan dan ditampilkan sebagai keadaan emiten, sedangkan
    `peringkat` dibiarkan kosong — dan **alasannya tertulis**, bukan hilang begitu saja.
    """
    preset = _preset_empat_faktor()
    stats = _statistik_uji()
    isi = {"roe_5t": _n("roe_5t", 0.30), "per": _n("per", 5.0)}

    hasil = skor.skor_emiten(preset, "AAAA", isi, stats, jenis="umum")

    assert hasil.diperingkat is False
    assert hasil.peringkat is None
    assert hasil.skor_total == pytest.approx(75.0)
    assert hasil.faktor["kualitas"].bobot_efektif_bp == 5000
    assert hasil.faktor["momentum"].skor is None

    isi_penjelasan = json.loads(hasil.penjelasan)
    assert "tidak diperingkat" in isi_penjelasan["alasan"]
    assert "2 dari 4" in isi_penjelasan["alasan"]
    assert isi_penjelasan["skor_total"] == pytest.approx(75.0)
    assert "tidak diperingkat" in hasil.penjelasan


# ---------------------------------------------------------------------------------------
# AC-17: statistik sektor & fallback ke semesta likuid
# ---------------------------------------------------------------------------------------


def _angka_dua_sektor() -> tuple[dict[str, dict[str, Nilai]], dict[str, str]]:
    """Sektor "besar" berisi 8 emiten likuid, sektor "kecil" 3 emiten — semestanya 11 emiten."""
    angka = {f"EB{i:02d}": {"roe_5t": _n("roe_5t", i / 100)} for i in range(8)}
    angka.update({f"EK{i}": {"roe_5t": _n("roe_5t", float(i))} for i in (1, 2, 3)})
    sektor = {kode: ("besar" if kode.startswith("EB") else "kecil") for kode in angka}
    return angka, sektor


def test_sektor_dengan_kurang_dari_delapan_emiten_likuid_memakai_statistik_semesta_likuid() -> None:
    """AC-17/PRD 8.4: sektor dengan < 8 emiten likuid memakai statistik seluruh semesta likuid.

    Sektor "kecil" hanya punya 3 emiten (ROE 1,00 · 2,00 · 3,00); rata-rata sektornya sendiri 2,00,
    tetapi yang dipakai adalah rata-rata 11 emiten likuid = (0,00+…+0,07+1+2+3) ÷ 11 = 6,28/11 ≈
    0,5709. Memakai rata-rata sektor kecil akan menilai ROE 1,00 sebagai **di bawah** rata-rata;
    dengan statistik semesta, ia di atas rata-rata — dua kesimpulan yang berlawanan.

    `fallback_sektor=True` ikut ke penjelasan supaya pembacanya tahu skala mana yang dipakai.
    """
    angka, sektor = _angka_dua_sektor()
    stats = skor.statistik_sektor(angka, sektor, tuple(angka), "roe_5t")

    kecil = stats["kecil"]
    assert kecil.dari_fallback is True
    assert kecil.jumlah == 11, "yang dihitung adalah seluruh semesta likuid"
    assert kecil.rata_rata == pytest.approx(6.28 / 11)
    assert kecil.rata_rata != pytest.approx(2.0), "bukan rata-rata sektornya sendiri"

    hasil = skor.skor_emiten(
        _preset_satu_metrik(), "EK1", angka["EK1"], {"roe_5t": kecil}, jenis="umum"
    )
    kontribusi = hasil.faktor["kualitas"].kontribusi[0]

    assert kontribusi.fallback_sektor is True
    assert kontribusi.z == pytest.approx((1.0 - kecil.rata_rata) / kecil.simpangan)
    assert '"fallback_sektor": true' in hasil.penjelasan
    assert "sektor < 8 emiten likuid" in kontribusi.alasan


def test_sektor_dengan_delapan_emiten_likuid_memakai_statistiknya_sendiri() -> None:
    """AC-17: sektor dengan ≥ 8 emiten likuid memakai statistiknya sendiri, bukan semesta.

    Sektor "besar" berisi 8 emiten likuid ber-ROE 0,00–0,07: rata-ratanya 0,035, jauh di bawah
    rata-rata semesta 0,5709. Kalau statistik semesta yang dipakai untuk sektor ini, setiap
    emitennya akan tampak sangat murah — persis kesalahan yang dijaga AC-17.
    """
    angka, sektor = _angka_dua_sektor()
    stats = skor.statistik_sektor(angka, sektor, tuple(angka), "roe_5t")

    besar = stats["besar"]
    assert besar.dari_fallback is False
    assert besar.jumlah == 8
    assert besar.rata_rata == pytest.approx(0.035)
    assert besar.rata_rata != pytest.approx(6.28 / 11), "bukan statistik seluruh semesta"

    hasil = skor.skor_emiten(
        _preset_satu_metrik(), "EB00", angka["EB00"], {"roe_5t": besar}, jenis="umum"
    )
    kontribusi = hasil.faktor["kualitas"].kontribusi[0]

    assert kontribusi.fallback_sektor is False
    assert kontribusi.z == pytest.approx((0.0 - 0.035) / besar.simpangan)
    assert '"fallback_sektor": false' in hasil.penjelasan


# ---------------------------------------------------------------------------------------
# Pemutus seri (PRD 9.5) & determinisme (AC-2)
# ---------------------------------------------------------------------------------------


def test_seri_skor_diputus_adtv20_yang_lebih_besar(sambungan: sqlite3.Connection) -> None:
    """PRD 9.5: skor yang sama diputus ADTV20 lebih besar, bukan oleh urutan kedatangan.

    AAAA dan BBBB berskor identik (68,333), tetapi BBBB ber-ADTV20 Rp 30 miliar dan AAAA Rp 20
    miliar: BBBB yang lebih likuid berhak di atas. ADTV20-nya dibaca dari data harga yang benar-
    benar ada di potret, bukan dari angka yang ditempel di uji.
    """
    p = _simpan_emiten(sambungan, {"AAAA": 20_000_000, "BBBB": 30_000_000})
    hasil = _hasil_seri()[:2]
    assert len({satu.skor_total for satu in hasil}) == 1, "serinya harus benar-benar seri"

    angka = metrik.metrik_semua(p)
    urut = {satu.kode: satu for satu in skor.beri_peringkat(hasil, angka)}

    assert angka["BBBB"]["adtv20"].nilai == pytest.approx(30_000_000_000.0)
    assert angka["AAAA"]["adtv20"].nilai == pytest.approx(20_000_000_000.0)
    assert urut["BBBB"].peringkat == 1
    assert urut["AAAA"].peringkat == 2
    assert urut["BBBB"].adtv20 == pytest.approx(30_000_000_000.0)


def test_seri_skor_dan_adtv20_yang_sama_diurutkan_stabil_menurut_kode(
    sambungan: sqlite3.Connection,
) -> None:
    """AC-2: bila skor **dan** ADTV20 sama, urutannya stabil menurut kode — apa pun urutan masuk.

    Tanpa pemutus terakhir, peringkat dua emiten berskor sama bergantung pada urutan baris basis
    data, sehingga dua kali jalan bisa memberi nomor yang berbeda untuk emiten yang sama. Karena
    itu hasilnya dibandingkan dengan urutan masukan yang dibalik: yang menentukan hanyalah kode.
    """
    p = _simpan_emiten(sambungan, {"CCCC": 10_000_000, "DDDD": 10_000_000})
    dua = tuple(satu for satu in _hasil_seri() if satu.kode in ("CCCC", "DDDD"))
    angka = metrik.metrik_semua(p)

    searah = {satu.kode: satu.peringkat for satu in skor.beri_peringkat(dua, angka)}
    terbalik = {
        satu.kode: satu.peringkat for satu in skor.beri_peringkat(tuple(reversed(dua)), angka)
    }

    assert searah == {"CCCC": 1, "DDDD": 2}
    assert terbalik == searah, "peringkat tidak boleh bergantung pada urutan masukan"


# ---------------------------------------------------------------------------------------
# Penyimpanan skor (PRD 8.1)
# ---------------------------------------------------------------------------------------


def _simpan_preset(sambungan: sqlite3.Connection, preset: Preset) -> None:
    """Preset harus ada di basis data sebelum skornya ditulis (kunci asing tabel `skor`)."""
    saring.simpan_preset(sambungan, preset)


def _baris_skor(sambungan: sqlite3.Connection, id_snapshot: int, id_preset: str) -> list[sqlite3.Row]:
    return sambungan.execute(
        "SELECT * FROM skor WHERE id_snapshot = ? AND id_preset = ? ORDER BY kode",
        (id_snapshot, id_preset),
    ).fetchall()


def _hasil_dua_emiten(preset: Preset) -> tuple[HasilSkor, ...]:
    """Dua emiten berskor berbeda, keduanya memenuhi syarat peringkat."""
    stats = _statistik_uji()
    return (
        skor.skor_emiten(preset, "AAAA", _nilai_tiga(nilai=0.30), stats, jenis="umum"),
        skor.skor_emiten(preset, "BBBB", _nilai_tiga(nilai=0.20, per=8.0), stats, jenis="umum"),
    )


def test_simpan_skor_menulis_ulang_bukan_menumpuk(sambungan: sqlite3.Connection) -> None:
    """PRD 8.1: skor adalah turunan deterministik berkunci (kode, snapshot, preset) — ditulis ulang.

    Menyimpannya append-only akan menumpuk salinan identik setiap kali saringan dijalankan, dan
    "skor terkini" kembali bergantung pada urutan penulisan. Karena itu setelah dua kali simpan
    harus tetap ada **satu** baris per emiten, dan peringkatnya ikut tersimpan.
    """
    p = _simpan_emiten(sambungan, {"AAAA": 20_000_000, "BBBB": 30_000_000})
    preset = _preset_tiga_faktor()
    _simpan_preset(sambungan, preset)
    hasil = skor.beri_peringkat(_hasil_dua_emiten(preset), metrik.metrik_semua(p))

    pertama = skor.simpan_skor(sambungan, p, preset, hasil)
    kedua = skor.simpan_skor(sambungan, p, preset, hasil)

    assert (pertama, kedua) == (2, 2)
    baris = _baris_skor(sambungan, p.id_snapshot, preset.id_preset)
    assert [satu["kode"] for satu in baris] == ["AAAA", "BBBB"]
    tersimpan = {satu["kode"]: satu for satu in baris}
    for satu in hasil:
        assert tersimpan[satu.kode]["peringkat"] == satu.peringkat


def test_versi_hitung_tersimpan_bersama_skor(sambungan: sqlite3.Connection) -> None:
    """`versi_hitung` adalah satu-satunya jejak bahwa cara menghitung skor pernah berubah.

    Tanpa kolom itu, skor lama dan skor baru tampak sebanding padahal rumusnya berbeda (PRD 8.1,
    catatan migrasi 004). Karena itu setiap baris wajib memuatnya, bukan mengosongkannya.
    """
    p = _simpan_emiten(sambungan, {"AAAA": 20_000_000})
    preset = _preset_tiga_faktor()
    _simpan_preset(sambungan, preset)
    hasil = skor.beri_peringkat(_hasil_dua_emiten(preset)[:1], metrik.metrik_semua(p))

    skor.simpan_skor(sambungan, p, preset, hasil)

    versi = {satu["versi_hitung"] for satu in _baris_skor(sambungan, p.id_snapshot, preset.id_preset)}
    assert versi == {skor.VERSI_HITUNG}
    assert all(satu.strip() for satu in versi)


def test_skor_faktor_yang_tidak_dinilai_tersimpan_sebagai_null_bukan_nol(
    sambungan: sqlite3.Connection,
) -> None:
    """Aturan keras 2/AC-3: `NULL` (tidak dinilai) dibedakan dari 0 (dinilai paling rendah).

    AAAA punya ROE sangat jauh di bawah rata-rata, sehingga z-nya dipotong ke −3 dan skor
    faktornya **0** — nilai yang sah dan berarti "paling rendah". BBBB tidak punya metriknya
    sama sekali, sehingga faktornya NULL. Kalau keduanya disimpan 0, dua keadaan yang menuntut
    tindakan berbeda (menilai vs melengkapi data) menjadi tidak bisa dibedakan lagi.
    """
    p = _simpan_emiten(sambungan, {"AAAA": 20_000_000, "BBBB": 30_000_000})
    preset = _preset_satu_metrik()
    _simpan_preset(sambungan, preset)
    stats = {"roe_5t": _stat(0.10, 0.10)}
    paling_rendah = skor.skor_emiten(
        preset, "AAAA", {"roe_5t": _n("roe_5t", -0.50)}, stats, jenis="umum"
    )
    tak_dinilai = skor.skor_emiten(preset, "BBBB", {}, stats, jenis="umum")
    assert paling_rendah.faktor["kualitas"].skor == pytest.approx(0.0)
    assert tak_dinilai.faktor["kualitas"].skor is None

    skor.simpan_skor(sambungan, p, preset, (paling_rendah, tak_dinilai))

    tersimpan = {
        satu["kode"]: satu for satu in _baris_skor(sambungan, p.id_snapshot, preset.id_preset)
    }
    assert tersimpan["AAAA"]["skor_kualitas_bp"] == 0, "dinilai, hasilnya paling rendah"
    assert tersimpan["BBBB"]["skor_kualitas_bp"] is None, "tidak dinilai — bukan nol"


def test_urutan_peringkat_dihitung_dari_skor_tak_dibulatkan() -> None:
    """PRD 9.5/P10: urutan memakai nilai tak dibulatkan; pembulatan hanya untuk tampilan.

    Dua emiten berskor 62,3336 dan 62,3317 — selisihnya di bawah satu basis poin, jadi keduanya
    membulat ke basis poin yang sama (6233). Kalau peringkat dihitung dari angka yang sudah
    dibulatkan, keduanya menjadi seri dan pemutusnya jatuh ke kode: AAAA akan berada di atas
    BBBB. Jawaban yang benar adalah BBBB di atas — dari nilai aslinya, bukan dari abjad.
    """
    preset = _preset_tiga_faktor()
    stats = _statistik_uji()
    aaaa = skor.skor_emiten(preset, "AAAA", _nilai_tiga(nilai=0.209976), stats, jenis="umum")
    bbbb = skor.skor_emiten(preset, "BBBB", _nilai_tiga(nilai=0.210004), stats, jenis="umum")

    assert bbbb.skor_total > aaaa.skor_total
    assert bbbb.skor_total - aaaa.skor_total < 0.01, "selisihnya di bawah satu basis poin"

    urut = {satu.kode: satu.peringkat for satu in skor.beri_peringkat((aaaa, bbbb), {})}

    assert urut == {"BBBB": 1, "AAAA": 2}, "urutan dari nilai tak dibulatkan, bukan dari kode"
