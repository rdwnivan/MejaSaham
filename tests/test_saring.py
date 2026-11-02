"""Uji saringan F2 (PRD 9.4) dan preset berversi K6 (PRD 8.3) — `mejasaham/saring.py`.

Yang diuji di sini adalah janji-janji yang membuat saringan bisa dipertanggungjawabkan:

* **Preset hidup di basis data dan tidak berubah diam-diam** (K6). Menyimpan ulang preset yang
  sama tidak menambah baris, sedangkan isi yang berbeda pada `id_preset` yang sama ditolak
  berisik — kalau tidak, arti skor lama berubah tanpa satu pun jejak.
* **Tiga keadaan penilaian**: `True`, `False`, dan `None` (metrik "tidak dihitung"). Yang ketiga
  **tidak** dianggap lolos; emitennya dilaporkan terpisah beserta alasannya (aturan keras 2/7,
  AC-9).
* **Saringannya mengikuti jenis emiten** (PRD 8.4, AC-16): kriteria yang `berlaku=False` bukan
  gagal, bukan juga lolos — ia memang tidak diterapkan.
* **Ambang dibandingkan dalam satuan metriknya.** Metrik bank mengembalikan basis poin,
  metrik lain mengembalikan rasio; menyamakannya asal-asalan pernah membuat setiap bank lolos.
* **Semesta likuid (K9)** = ADTV20 ≥ ambang **dan** tanpa notasi khusus yang masih berjalan pada
  tanggal snapshot.

Seluruh data uji ditulis lewat jalur nyata (`ingesti.simpan` → `potret.muat`), bukan dengan
menyusun objek di memori. Semestanya kecil dan angkanya bulat supaya bisa diperiksa tangan:
sepuluh emiten satu sektor, delapan ber-ADTV20 Rp 10 miliar dan dua Rp 100 juta.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import db, ingesti, lokasi, metrik, pengatur, potret, saring
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    Fundamental,
    GalatIngesti,
    HargaHarian,
    KumpulanData,
    NotasiKhusus,
    RasioBank,
)
from mejasaham.potret import Potret
from mejasaham.saring import BobotMetrik, HasilSaring, Kriteria, PenilaianKriteria, Preset

SUMBER = "uji"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
SEKTOR = "industri"

#: ADTV20 = rata-rata close x volume 20 hari bursa terakhir. Harga 1.000 dengan volume
#: 10.000.000 memberi Rp 10 miliar (di atas ambang Rp 5 miliar), sedangkan volume 100.000
#: memberi Rp 100 juta (di bawah ambang) — keduanya angka bulat, tanpa pembulatan tersembunyi.
CLOSE = 1_000
VOLUME_LIKUID = 10_000_000
VOLUME_TIPIS = 100_000
HARI = 20
AMBANG_ADTV = 5_000_000_000

LIKUID = ("AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF", "GGGG", "HHHH")
TIPIS = ("IIII", "JJJJ")

#: Ekuitas & laba enam tahun buku (P5). ROE tahunannya 2/21 · 1/6 · 6/29 · 2/9 · 2/9, sehingga
#: mediannya 6/29 ≈ 0,207 — di atas ambang 12% yang dipakai preset uji.
EKUITAS = {2020: 1_000, 2021: 1_100, 2022: 1_300, 2023: 1_600, 2024: 2_000, 2025: 2_500}
LABA = {2021: 100, 2022: 200, 2023: 300, 2024: 400, 2025: 500}

#: Nama kriteria yang tidak berlaku untuk bank (PRD 8.4, AC-16) dan yang hanya berlaku untuknya.
BUKAN_BANK = ("cfo_ni", "coverage", "der")
HANYA_BANK = ("npl_kotor", "car", "bopo", "nim")


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


def _emiten(
    kode: str, *, sektor: str = SEKTOR, jenis: str | None = None, jumlah_saham: int | None = None
) -> Emiten:
    return Emiten(
        kode=kode,
        nama=f"Emiten {kode}",
        sektor_idx_ic=sektor,
        jenis=jenis,
        jumlah_saham=jumlah_saham,
        sumber=SUMBER,
    )


def _deret(kode: str, *, volume: int = VOLUME_LIKUID, hari: int = HARI) -> tuple[HargaHarian, ...]:
    """Baris harga `hari` hari bursa terakhir, semuanya berpenanda "tidak disesuaikan"."""
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=hari - 1 - i),
            close=CLOSE,
            volume=volume,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(hari)
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


def _laporan_roe(kode: str, *, utang_bunga: int) -> tuple[Fundamental, ...]:
    """Enam laporan tahunan 2020–2025; `utang_bunga` hanya ada di laporan terakhir.

    DER memakai laporan terakhir, jadi utang 1.000 dengan ekuitas 2.500 memberi DER 0,4
    (lolos ambang 2,0) dan utang 10.000 memberi DER 4,0 (gagal).
    """
    return tuple(
        _tahunan(
            kode,
            tahun,
            laba_induk=LABA.get(tahun),
            ekuitas_induk=EKUITAS[tahun],
            utang_bunga=utang_bunga if tahun == 2025 else None,
        )
        for tahun in EKUITAS
    )


def _laporan_sehat(kode: str) -> tuple[Fundamental, ...]:
    """Tiga laporan tahunan dengan CFO/NI 450/300 = 1,5 · coverage 200/50 = 4 · DER 0,5."""
    return tuple(
        _tahunan(
            kode,
            tahun,
            laba_induk=100,
            ekuitas_induk=1_000,
            utang_bunga=500,
            ebit=200,
            beban_bunga=50,
            cfo=150,
        )
        for tahun in (2023, 2024, 2025)
    )


def _simpan(sambungan: sqlite3.Connection, **isi: object) -> int:
    """Tulis satu snapshot lewat jalur nyata dan kembalikan `id_snapshot`-nya."""
    kumpulan = KumpulanData(sumber=SUMBER, **isi)  # type: ignore[arg-type]
    return ingesti.simpan(sambungan, kumpulan, tanggal_data=TANGGAL, momen=MOMEN).id_snapshot


def _preset(*kriteria: Kriteria) -> Preset:
    """Preset uji: saringan tidak memakai bobot, jadi bobotnya sengaja tidak dibuat lengkap."""
    return Preset(
        id_preset="uji/v1",
        nama="uji",
        versi=1,
        horizon="bulanan",
        dibuat_pada=TANGGAL,
        keterangan="preset uji saring",
        kriteria=kriteria,
        bobot_faktor={"kualitas": 10000},
        bobot_metrik=(),
    )


def _kriteria_dasar(*, notasi: bool = False) -> tuple[Kriteria, ...]:
    """ADTV20 + DER + ROE 5 tahun; `notasi` menambahkan pengecualian notasi khusus."""
    kriteria = [Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV)]
    if notasi:
        kriteria.append(Kriteria("pengecualian_notasi", urutan=2))
    kriteria.append(Kriteria("der", urutan=3, ambang_bp=20000))
    kriteria.append(Kriteria("roe_5t", urutan=4, ambang_bp=1200))
    return tuple(kriteria)


def _kriteria_bank() -> tuple[Kriteria, ...]:
    """Kriteria umum **dan** kriteria bank sekaligus (PRD 8.4, AC-16)."""
    return (
        Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV),
        Kriteria("cfo_ni", urutan=2, ambang_bp=8000),
        Kriteria("coverage", urutan=3, ambang_bp=30000),
        Kriteria("der", urutan=4, ambang_bp=20000),
        Kriteria("npl_kotor", urutan=5, ambang_bp=300),
        Kriteria("car", urutan=6, ambang_bp=1400),
        Kriteria("bopo", urutan=7, ambang_bp=8500),
        Kriteria("nim", urutan=8, ambang_bp=350),
    )


def _bank(kode: str, **rasio: int) -> RasioBank:
    """Baris rasio bank yang sudah diketahui snapshot (terbit 31 Maret 2026)."""
    return RasioBank(
        kode=kode,
        periode=date(2025, 12, 31),
        tgl_publikasi=date(2026, 3, 31),
        **rasio,  # type: ignore[arg-type]
    )


def _rasio_bank_sehat(kode: str) -> RasioBank:
    return _bank(kode, npl_kotor_bp=190, car_bp=2_000, bopo_bp=5_820, nim_bp=400)


def _penilaian(hasil: HasilSaring, nama: str) -> PenilaianKriteria:
    """Penilaian satu kriteria; gagal berisik bila kriterianya tidak ada di hasil."""
    return next(satu for satu in hasil.penilaian if satu.kriteria == nama)


def _kriteria_preset(preset: Preset, nama: str) -> Kriteria:
    return next(satu for satu in preset.kriteria if satu.kriteria == nama)


def _simpan_tiga_keadaan(
    sambungan: sqlite3.Connection, *, notasi: tuple[NotasiKhusus, ...] = ()
) -> Potret:
    """Tiga emiten likuid satu sektor: AAAA lolos, BBBB gagal DER, CCCC tanpa laporan."""
    id_snapshot = _simpan(
        sambungan,
        emiten=(
            _emiten("AAAA", jumlah_saham=1_000_000),
            _emiten("BBBB", jumlah_saham=1_000_000),
            _emiten("CCCC", jumlah_saham=1_000_000),
        ),
        harga_harian=_deret("AAAA") + _deret("BBBB") + _deret("CCCC"),
        fundamental=_laporan_roe("AAAA", utang_bunga=1_000)
        + _laporan_roe("BBBB", utang_bunga=10_000),
        notasi_khusus=notasi,
    )
    return potret.muat(sambungan, id_snapshot)


def _simpan_semesta_likuid(
    sambungan: sqlite3.Connection, *, notasi: tuple[NotasiKhusus, ...] = ()
) -> Potret:
    """Sepuluh emiten satu sektor: delapan ber-ADTV20 Rp 10 miliar, dua Rp 100 juta."""
    id_snapshot = _simpan(
        sambungan,
        emiten=tuple(_emiten(kode) for kode in LIKUID + TIPIS),
        harga_harian=tuple(bar for kode in LIKUID for bar in _deret(kode))
        + tuple(bar for kode in TIPIS for bar in _deret(kode, volume=VOLUME_TIPIS)),
        notasi_khusus=notasi,
    )
    return potret.muat(sambungan, id_snapshot)


def _jumlah_baris_preset(sambungan: sqlite3.Connection) -> tuple[int, int, int, int]:
    return tuple(  # type: ignore[return-value]
        sambungan.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]
        for tabel in (
            "preset_saring",
            "preset_kriteria",
            "preset_bobot_faktor",
            "preset_bobot_metrik",
        )
    )


# ---------------------------------------------------------------------------------------
# Preset berversi (K6, PRD 8.3)
# ---------------------------------------------------------------------------------------


def test_kedua_preset_bawaan_tersimpan_pada_basis_data_kosong(
    sambungan: sqlite3.Connection,
) -> None:
    """Penjaga daftar kriteria: kedua preset bawaan harus bisa disimpan pada basis data kosong.

    Uji ini menangkap bug nyata yang pernah terjadi: kriteria `momentum_12_1` dipakai preset
    `momentum/v1` tetapi tidak terdaftar di CHECK `preset_kriteria`, sehingga menyimpan preset
    kedua berhenti di `sqlite3.IntegrityError`. Akibatnya `--saring` tidak pernah bisa berjalan
    pada pemasangan baru — dan kegagalannya muncul sebagai galat basis data mentah, bukan
    sebagai pesan yang bisa ditindaklanjuti.

    Karena itu yang dituntut di sini bukan "fungsinya jalan", melainkan: **seluruh** preset
    bawaan tersimpan, dan kriteria yang tersimpan sama persis dengan yang didefinisikan.
    """
    baru = pengatur.siapkan_preset_bawaan(sambungan, TANGGAL)

    assert set(baru) == {"kualitas-nilai/v1", "momentum/v1"}
    assert {satu[0] for satu in saring.daftar_preset(sambungan)} == {
        "kualitas-nilai/v1",
        "momentum/v1",
    }

    didefinisikan = saring.preset_bawaan(TANGGAL)
    for satu in didefinisikan:
        tersimpan = saring.muat_preset(sambungan, satu.id_preset)
        assert tersimpan.kriteria == satu.kriteria, f"kriteria {satu.id_preset} tidak utuh"
    momentum = saring.muat_preset(sambungan, "momentum/v1")
    assert "momentum_12_1" in [k.kriteria for k in momentum.kriteria], (
        "kriteria inilah yang dulu tidak terdaftar di CHECK preset_kriteria"
    )


def test_menyimpan_preset_yang_sama_dua_kali_tidak_menambah_baris(
    sambungan: sqlite3.Connection,
) -> None:
    """Idempoten (K6): memuat ulang preset yang sama tidak menumpuk salinan.

    Preset dibaca setiap kali saringan dijalankan; kalau penyimpanannya menumpuk, tabel preset
    tumbuh tanpa menambah informasi dan "versi berapa yang berlaku" menjadi tidak terjawab.
    """
    preset = saring.preset_bawaan(TANGGAL)[0]

    assert saring.simpan_preset(sambungan, preset) is True
    sebelum = _jumlah_baris_preset(sambungan)

    assert saring.simpan_preset(sambungan, preset) is False
    assert _jumlah_baris_preset(sambungan) == sebelum


def test_preset_dengan_id_sama_tetapi_isi_berbeda_ditolak_dan_baris_lama_tidak_berubah(
    sambungan: sqlite3.Connection,
) -> None:
    """K6: arti skor lama tidak boleh berubah diam-diam ketika ambangnya disunting.

    Perubahan ambang adalah perubahan aturan: ia harus menaikkan versi dan menjadi preset baru.
    Menimpanya berarti skor yang dihitung bulan lalu tetap tampak sebanding dengan skor hari ini
    padahal aturannya sudah lain — persis yang dilarang `docs/keputusan.md` K6 dan aturan
    keras 9.
    """
    preset = saring.preset_bawaan(TANGGAL)[0]
    saring.simpan_preset(sambungan, preset)
    berbeda = replace(
        preset,
        kriteria=tuple(
            replace(satu, ambang_bp=1500) if satu.kriteria == "roe_5t" else satu
            for satu in preset.kriteria
        ),
    )

    with pytest.raises(GalatIngesti) as galat:
        saring.simpan_preset(sambungan, berbeda)

    pesan = str(galat.value)
    assert "isi berbeda" in pesan
    assert "versi" in pesan, "pesannya harus menyebut jalan keluarnya: naikkan versi"
    assert sambungan.execute("SELECT COUNT(*) FROM preset_saring").fetchone()[0] == 1
    tersimpan = saring.muat_preset(sambungan, preset.id_preset)
    assert _kriteria_preset(tersimpan, "roe_5t").ambang_bp == 1200, "baris lama tidak boleh berubah"


def test_muat_preset_mengembalikan_kriteria_urut_dan_bobot_apa_adanya(
    sambungan: sqlite3.Connection,
) -> None:
    """Yang disimpan itulah yang dibaca: kriteria urut menurut `urutan`, bobot apa adanya.

    Urutan kriteria menentukan urutan alasan yang ditampilkan (PRD 9.4), dan bobot menentukan
    arti skor (PRD 9.5.1). Keduanya harus bolak-balik utuh — termasuk set bank yang menimpa
    set umum untuk jenis emiten tertentu (PRD 8.4).
    """
    preset = Preset(
        id_preset="urut/v1",
        nama="urut",
        versi=1,
        horizon="bulanan",
        dibuat_pada=TANGGAL,
        keterangan="menguji urutan kriteria dan bobot",
        kriteria=(
            Kriteria("roe_5t", urutan=3, ambang_bp=1200),
            Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV),
            Kriteria("pengecualian_notasi", urutan=4, aktif=False),
            Kriteria("der", urutan=2, ambang_bp=20000),
        ),
        bobot_faktor={"nilai": 4000, "kualitas": 6000},
        bobot_metrik=(
            BobotMetrik("kualitas", "roe_5t", "umum", 6000, "tinggi_baik"),
            BobotMetrik("kualitas", "der", "umum", 4000, "rendah_baik"),
            BobotMetrik("kualitas", "npl_kotor", "bank_keuangan", 10000, "rendah_baik"),
        ),
    )
    saring.simpan_preset(sambungan, preset)

    dimuat = saring.muat_preset(sambungan, "urut/v1")

    assert [satu.kriteria for satu in dimuat.kriteria] == [
        "adtv20",
        "der",
        "roe_5t",
        "pengecualian_notasi",
    ]
    assert dimuat.kriteria == tuple(sorted(preset.kriteria, key=lambda satu: satu.urutan))
    assert dimuat.bobot_faktor == {"kualitas": 6000, "nilai": 4000}
    assert set(dimuat.bobot_metrik) == set(preset.bobot_metrik)
    assert dimuat.bobot_untuk("kualitas", "bank_keuangan") == (
        BobotMetrik("kualitas", "npl_kotor", "bank_keuangan", 10000, "rendah_baik"),
    ), "set bank harus menimpa set umum untuk jenis emiten itu (PRD 8.4)"
    assert (dimuat.nama, dimuat.versi, dimuat.horizon, dimuat.dibuat_pada) == (
        "urut",
        1,
        "bulanan",
        TANGGAL,
    )


def test_muat_preset_yang_tidak_dikenal_ditolak_dengan_daftar_yang_tersedia(
    sambungan: sqlite3.Connection,
) -> None:
    """Preset tak dikenal harus menolong: sebutkan yang ada, jangan sekadar "tidak ditemukan"."""
    pengatur.siapkan_preset_bawaan(sambungan, TANGGAL)

    with pytest.raises(GalatIngesti) as galat:
        saring.muat_preset(sambungan, "tidak-ada/v9")

    pesan = str(galat.value)
    assert "tidak-ada/v9" in pesan
    assert "kualitas-nilai/v1" in pesan and "momentum/v1" in pesan


# ---------------------------------------------------------------------------------------
# Tiga keadaan penilaian (aturan keras 2/7, AC-9)
# ---------------------------------------------------------------------------------------


def test_kriteria_yang_terpenuhi_lolos_dan_yang_tidak_terpenuhi_gagal(
    sambungan: sqlite3.Connection,
) -> None:
    """Dua keadaan pertama: nilainya ada, ambangnya diketahui, jadi jawabannya tegas.

    AAAA: ADTV20 Rp 10 miliar ≥ Rp 5 miliar · DER 1.000/2.500 = 0,4 ≤ 2,0 · ROE 6/29 ≈ 0,207 ≥
    0,12 → lolos. BBBB: DER 10.000/2.500 = 4,0 > 2,0 → gagal, dan yang gagal itulah yang
    dilaporkan di ringkasannya — bukan sekadar "gagal".
    """
    p = _simpan_tiga_keadaan(sambungan)
    hasil = {satu.kode: satu for satu in saring.saring_semesta(p, _preset(*_kriteria_dasar()))}

    assert hasil["AAAA"].lolos is True
    assert all(satu.lolos is True for satu in hasil["AAAA"].berlaku)

    assert hasil["BBBB"].lolos is False
    der = _penilaian(hasil["BBBB"], "der")
    assert der.lolos is False
    assert der.nilai == pytest.approx(4.0), "DER 10.000 ÷ 2.500 = 4,0"
    assert "der" in hasil["BBBB"].ringkas(), "kriteria yang menggagalkan harus ikut terlihat"


def test_metrik_yang_tidak_dihitung_tidak_dianggap_lolos_dan_alasannya_dilaporkan(
    sambungan: sqlite3.Connection,
) -> None:
    """Keadaan ketiga: `lolos=None` — kriteria berlaku, tetapi metriknya "tidak dihitung".

    CCCC tidak punya laporan fundamental sama sekali, jadi DER dan ROE-nya tidak bisa dihitung.
    Menganggapnya "lolos" berarti memasukkan emiten yang tidak diperiksa ke daftar kandidat;
    mengeluarkannya tanpa suara berarti laporan tampak lebih rapi daripada keadaannya
    (aturan keras 7, AC-9). Karena itu ia keluar dari daftar lolos **dan** muncul di
    `tidak_bisa_dinilai` beserta alasannya.
    """
    p = _simpan_tiga_keadaan(sambungan)
    hasil = {
        satu.kode: satu
        for satu in saring.saring_semesta(p, _preset(*_kriteria_dasar()), metrik=metrik.metrik_semua(p))
    }

    cccc = hasil["CCCC"]
    assert cccc.lolos is False, "tidak bisa dinilai bukan berarti lolos"
    assert cccc.berlaku, "kriterianya tetap berlaku; yang tidak ada hanya metriknya"

    tidak_dinilai = {satu.kriteria: satu for satu in cccc.tidak_bisa_dinilai}
    assert set(tidak_dinilai) == {"der", "roe_5t"}
    for satu in tidak_dinilai.values():
        assert satu.lolos is None
        assert satu.alasan.strip(), "alasan wajib ada supaya bisa ditampilkan"
    assert "laporan" in tidak_dinilai["der"].alasan, "alasannya harus menyebut apa yang kurang"
    assert "tidak bisa dinilai" in cccc.ringkas()

    assert _penilaian(cccc, "adtv20").lolos is True, (
        "ADTV20-nya justru terhitung: yang hilang hanya metrik fundamentalnya"
    )


# ---------------------------------------------------------------------------------------
# AC-16: saringan mengikuti jenis emiten (PRD 8.4)
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("jenis", "tidak_berlaku"),
    [("bank_keuangan", BUKAN_BANK), (None, HANYA_BANK)],
)
def test_kriteria_yang_tidak_berlaku_mengikuti_jenis_emiten(
    sambungan: sqlite3.Connection, jenis: str | None, tidak_berlaku: tuple[str, ...]
) -> None:
    """AC-16/PRD 8.4: DER, CFO/NI, dan coverage tidak diterapkan pada bank; NPL/CAR/BOPO/NIM
    tidak diterapkan pada non-bank.

    `berlaku=False` adalah keadaan ketiga yang berbeda dari `lolos=None`: yang satu berarti
    "memang tidak diterapkan", yang lain "diterapkan tetapi metriknya tidak ada". Menyamakan
    keduanya membuat bank tanpa data DER tampak "tidak bisa dinilai" — atau lebih buruk,
    membuat NPL dipaksakan ke emiten industri.
    """
    id_snapshot = _simpan(
        sambungan, emiten=(_emiten("AAAA", jenis=jenis),), harga_harian=_deret("AAAA")
    )
    p = potret.muat(sambungan, id_snapshot)
    hasil = saring.saring_semesta(p, _preset(*_kriteria_bank()), metrik=metrik.metrik_semua(p))[0]

    for nama in tidak_berlaku:
        satu = _penilaian(hasil, nama)
        assert satu.berlaku is False, f"{nama} tidak boleh berlaku untuk jenis {jenis!r}"
        assert satu.lolos is None
        assert nama not in {x.kriteria for x in hasil.tidak_bisa_dinilai}, (
            "kriteria yang tidak berlaku bukan 'tidak bisa dinilai'"
        )

    berlaku = set(HANYA_BANK + BUKAN_BANK) - set(tidak_berlaku)
    assert {nama for nama in berlaku if _penilaian(hasil, nama).berlaku} == berlaku


@pytest.mark.parametrize("jenis", ["bank_keuangan", "umum"])
def test_kriteria_yang_tidak_berlaku_tidak_menghalangi_emiten_lolos(
    sambungan: sqlite3.Connection, jenis: str
) -> None:
    """Kriteria yang tidak berlaku tidak boleh ikut dihitung gagal (AC-16).

    Dua arah diuji sekaligus, dan keduanya sengaja **tanpa** data yang tidak berlaku supaya
    kekeliruannya langsung terlihat:

    * bank dengan rasio bank bagus dan tanpa laporan keuangan sama sekali → lolos, karena DER,
      CFO/NI, dan coverage memang tidak diterapkan padanya;
    * emiten umum dengan laporan keuangan sehat dan tanpa `rasio-bank.csv` → lolos, karena
      NPL/CAR/BOPO/NIM memang tidak diterapkan padanya.

    Kalau kriteria yang tidak berlaku ikut dinilai, keduanya akan berakhir "tidak bisa dinilai".
    """
    if jenis == "bank_keuangan":
        isi: dict[str, object] = {
            "emiten": (_emiten("AAAA", jenis=jenis, jumlah_saham=1_000_000_000),),
            "harga_harian": _deret("AAAA"),
            "rasio_bank": (_rasio_bank_sehat("AAAA"),),
        }
    else:
        isi = {
            "emiten": (_emiten("AAAA", jenis=jenis),),
            "harga_harian": _deret("AAAA"),
            "fundamental": _laporan_sehat("AAAA"),
        }
    id_snapshot = _simpan(sambungan, **isi)
    p = potret.muat(sambungan, id_snapshot)

    hasil = saring.saring_semesta(p, _preset(*_kriteria_bank()), metrik=metrik.metrik_semua(p))[0]

    assert hasil.lolos is True, hasil.ringkas()
    assert not hasil.tidak_bisa_dinilai


# ---------------------------------------------------------------------------------------
# Penjaga satuan & arah ambang bank
# ---------------------------------------------------------------------------------------


def test_npl_kotor_190_bp_lolos_dan_350_bp_gagal_pada_ambang_300_bp(
    sambungan: sqlite3.Connection,
) -> None:
    """Penjaga satuan bank: NPL dibandingkan dalam **basis poin**, bukan sebagai rasio.

    `rasio_bank` menyimpan NPL sebagai basis poin (190 bp = 1,9%) dan ambang preset juga
    (300 bp = 3%). Membandingkan 350 (bp) dengan 0,03 (rasio) akan **selalu** lolos: itulah bug
    nyata yang pernah terjadi, dan ia tidak terlihat di layar karena angka yang ditampilkan
    tetap benar. Karena itu kedua arah diuji sekaligus pada ambang yang sama: 190 bp lolos,
    350 bp gagal.
    """
    id_snapshot = _simpan(
        sambungan,
        emiten=(
            _emiten("AAAA", jenis="bank_keuangan", jumlah_saham=1_000_000_000),
            _emiten("BBBB", jenis="bank_keuangan", jumlah_saham=1_000_000_000),
        ),
        harga_harian=_deret("AAAA") + _deret("BBBB"),
        rasio_bank=(
            _bank("AAAA", npl_kotor_bp=190, car_bp=2_000, bopo_bp=5_820, nim_bp=400),
            _bank("BBBB", npl_kotor_bp=350, car_bp=2_000, bopo_bp=5_820, nim_bp=400),
        ),
    )
    p = potret.muat(sambungan, id_snapshot)
    hasil = {
        satu.kode: satu
        for satu in saring.saring_semesta(p, _preset(*_kriteria_bank()), metrik=metrik.metrik_semua(p))
    }

    lolos = _penilaian(hasil["AAAA"], "npl_kotor")
    assert lolos.lolos is True, "190 bp = 1,9% ≤ 3%"
    assert lolos.nilai == pytest.approx(190.0)
    assert lolos.satuan == "bp"
    assert lolos.ambang.startswith("<=")
    assert "3,00%" in lolos.ambang, "ambangnya ditampilkan sebagai persen, bukan rasio 0,03"

    gagal = _penilaian(hasil["BBBB"], "npl_kotor")
    assert gagal.lolos is False, "350 bp = 3,5% > 3%"
    assert gagal.nilai == pytest.approx(350.0)
    assert "3,00%" in gagal.ambang
    assert hasil["AAAA"].lolos is True and hasil["BBBB"].lolos is False


def test_bopo_rendah_lebih_baik_sehingga_5820_bp_lolos_dan_9000_bp_gagal(
    sambungan: sqlite3.Connection,
) -> None:
    """Arah BOPO terkunci: makin **rendah** makin baik, dan ambangnya 8500 bp = 85%.

    BOPO 5820 bp = 58,2% ≤ 85% → lolos. Kalau arahnya terbalik ("semakin tinggi semakin baik"),
    58,2% justru akan gagal — dan bank paling tidak efisien akan tampak paling sehat.
    Pembanding 9000 bp = 90% menjaga agar ujinya tidak sekadar "selalu lolos".
    """
    id_snapshot = _simpan(
        sambungan,
        emiten=(
            _emiten("AAAA", jenis="bank_keuangan", jumlah_saham=1_000_000_000),
            _emiten("BBBB", jenis="bank_keuangan", jumlah_saham=1_000_000_000),
        ),
        harga_harian=_deret("AAAA") + _deret("BBBB"),
        rasio_bank=(
            _bank("AAAA", npl_kotor_bp=190, car_bp=2_000, bopo_bp=5_820, nim_bp=400),
            _bank("BBBB", npl_kotor_bp=190, car_bp=2_000, bopo_bp=9_000, nim_bp=400),
        ),
    )
    p = potret.muat(sambungan, id_snapshot)
    hasil = {
        satu.kode: satu
        for satu in saring.saring_semesta(p, _preset(*_kriteria_bank()), metrik=metrik.metrik_semua(p))
    }

    efisien = _penilaian(hasil["AAAA"], "bopo")
    assert efisien.lolos is True, "58,2% ≤ 85%"
    assert efisien.nilai == pytest.approx(5_820.0)
    assert efisien.satuan == "bp"
    assert efisien.ambang.startswith("<=")
    assert "85,00%" in efisien.ambang

    boros = _penilaian(hasil["BBBB"], "bopo")
    assert boros.lolos is False, "90% > 85%"
    assert "85,00%" in boros.ambang


# ---------------------------------------------------------------------------------------
# Kriteria relatif sektor (PRD 8.2)
# ---------------------------------------------------------------------------------------


def test_per_relatif_sektor_dibandingkan_dengan_median_sektor_emiten_itu(
    sambungan: sqlite3.Connection,
) -> None:
    """PRD 8.2/9.5: PER ≤ 1,2 × **median sektor**, dihitung dari **semesta likuid**.

    PER = harga x jumlah saham ÷ laba 12 bulan terakhir. Dengan harga 1.000 dan 1.000.000
    lembar: AAAA 10 (laba 100 jt), BBBB 20 (50 jt), CCCC 25 (40 jt) di sektor industri; DDDD dan
    EEEE 1 (1 miliar) di sektor keuangan. IIII juga industri dan PER-nya 1, tetapi ADTV20-nya
    Rp 100 juta sehingga **bukan** emiten likuid.

    Median industri dari semesta likuid = 20 → batas 24 → AAAA dan BBBB lolos, CCCC gagal. Dua
    kekeliruan tertangkap sekaligus: kalau seluruh emiten dipakai (IIII ikut), mediannya turun ke
    15 dan BBBB ikut gagal; kalau yang dipakai rata-rata sektor (23,33 → batas 28), CCCC ikut
    lolos. Keduanya berbeda dari jawaban yang benar, jadi uji ini benar-benar menguji
    pembandingnya — termasuk dari emiten mana mediannya dihitung.
    """
    laba = {
        "AAAA": 100_000_000,
        "BBBB": 50_000_000,
        "CCCC": 40_000_000,
        "DDDD": 1_000_000_000,
        "EEEE": 1_000_000_000,
        "IIII": 1_000_000_000,
    }
    sektor = {
        "AAAA": SEKTOR,
        "BBBB": SEKTOR,
        "CCCC": SEKTOR,
        "IIII": SEKTOR,
        "DDDD": "keuangan",
        "EEEE": "keuangan",
    }
    volume = {"IIII": VOLUME_TIPIS}
    id_snapshot = _simpan(
        sambungan,
        emiten=tuple(
            _emiten(kode, sektor=sektor[kode], jumlah_saham=1_000_000) for kode in laba
        ),
        harga_harian=tuple(
            bar for kode in laba for bar in _deret(kode, volume=volume.get(kode, VOLUME_LIKUID))
        ),
        fundamental=tuple(
            _tahunan(kode, 2025, laba_induk=satu_laba, ekuitas_induk=1_000_000_000)
            for kode, satu_laba in laba.items()
        ),
    )
    p = potret.muat(sambungan, id_snapshot)
    angka = metrik.metrik_semua(p)
    assert [angka[kode]["per"].nilai for kode in ("AAAA", "BBBB", "CCCC", "IIII")] == [
        10.0,
        20.0,
        25.0,
        1.0,
    ]
    likuid = ("AAAA", "BBBB", "CCCC", "DDDD", "EEEE")
    preset = _preset(
        Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV),
        Kriteria("per_relatif_sektor", urutan=2, ambang_bp=12000, pembanding="median_sektor"),
    )

    hasil = {
        satu.kode: satu
        for satu in saring.saring_semesta(p, preset, metrik=angka, semesta=likuid)
    }

    for kode in ("AAAA", "BBBB"):
        satu = _penilaian(hasil[kode], "per_relatif_sektor")
        assert satu.lolos is True, f"{kode}: PER {satu.nilai} ≤ 24"
        assert "median sektor 20,00" in satu.ambang, "pembandingnya harus terlihat di alasan"
    cccc = _penilaian(hasil["CCCC"], "per_relatif_sektor")
    assert cccc.lolos is False, "PER 25 > 1,2 x 20 = 24"
    assert cccc.nilai == pytest.approx(25.0)

    dddd = _penilaian(hasil["DDDD"], "per_relatif_sektor")
    assert dddd.lolos is True
    assert "median sektor 1,00" in dddd.ambang, "sektor keuangan punya mediannya sendiri"

    seluruh_emiten = {
        satu.kode: satu for satu in saring.saring_semesta(p, preset, metrik=angka)
    }
    assert _penilaian(seluruh_emiten["BBBB"], "per_relatif_sektor").lolos is False, (
        "tanpa batas semesta likuid, median industri tertarik IIII (PER 1) menjadi 15"
    )


def test_kriteria_relatif_sektor_tidak_dinilai_bila_median_sektor_tidak_bisa_dihitung(
    sambungan: sqlite3.Connection,
) -> None:
    """Tanpa median sektor, kriteria relatifnya "tidak bisa dinilai" — bukan lolos.

    Median tidak bisa dihitung ketika tidak ada satu pun PER sektor yang terhitung (mis. seluruh
    emiten di sektor itu belum punya laporan). Memperlakukan "tidak ada pembanding" sebagai
    "tidak ada batas" akan meloloskan setiap emiten di sektor yang datanya paling buruk —
    kebalikan dari yang diinginkan.
    """
    p = _simpan_tiga_keadaan(sambungan)
    preset = _preset(
        Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV),
        Kriteria("pbv_relatif_sektor", urutan=2, ambang_bp=15000, pembanding="median_sektor"),
    )
    angka = metrik.metrik_semua(p)

    hasil = saring.saring_emiten(
        p,
        "AAAA",
        preset,
        angka["AAAA"],
        jenis="umum",
        median_per=None,
        median_pbv=None,
    )

    satu = _penilaian(hasil, "pbv_relatif_sektor")
    assert satu.lolos is None
    assert satu.berlaku is True, "kriterianya berlaku; yang tidak ada hanya pembandingnya"
    assert "median sektor" in satu.alasan
    assert "pbv" in satu.alasan
    assert hasil.lolos is False


# ---------------------------------------------------------------------------------------
# K9: semesta likuid = ADTV20 cukup dan bukan notasi aktif
# ---------------------------------------------------------------------------------------


def test_semesta_likuid_mengeluarkan_emiten_di_bawah_ambang_adtv20(
    sambungan: sqlite3.Connection,
) -> None:
    """K9/PRD 8.2: emiten likuid adalah yang ADTV20-nya ≥ Rp 5 miliar.

    Ambangnya diambil dari kriteria `adtv20` di preset, bukan dari konstanta di kode, supaya
    definisi likuid bisa direvisi lewat versi preset baru tanpa mengubah arti skor lama.
    """
    p = _simpan_semesta_likuid(sambungan)
    angka = metrik.metrik_semua(p)
    preset = _preset(Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV))

    likuid = saring.semesta_likuid(p, preset, metrik=angka)

    assert set(likuid) == set(LIKUID)
    assert set(likuid).isdisjoint(TIPIS)
    assert angka["IIII"]["adtv20"].nilai == pytest.approx(100_000_000.0), "Rp 100 juta < Rp 5 miliar"


def test_notasi_yang_sudah_berakhir_tidak_mengeluarkan_emiten_dari_semesta_likuid(
    sambungan: sqlite3.Connection,
) -> None:
    """Yang mengeluarkan emiten hanyalah notasi yang **masih berjalan** pada tanggal snapshot.

    Tiga bentuk diuji sekaligus, karena batas waktunya mudah keliru ke arah mana pun:

    * UMA tanpa tanggal selesai → masih berjalan → AAAA keluar;
    * suspensi yang berakhir sehari sebelum snapshot → sudah berakhir → BBBB tetap likuid;
    * papan pemantauan yang mulai sehari setelah snapshot → belum berjalan → CCCC tetap likuid.
    """
    p = _simpan_semesta_likuid(
        sambungan,
        notasi=(
            NotasiKhusus(kode="AAAA", jenis="uma", tanggal_mulai=date(2026, 1, 1)),
            NotasiKhusus(
                kode="BBBB",
                jenis="suspensi",
                tanggal_mulai=date(2025, 1, 1),
                tanggal_selesai=TANGGAL - timedelta(days=1),
            ),
            NotasiKhusus(
                kode="CCCC",
                jenis="papan_pemantauan",
                tanggal_mulai=TANGGAL + timedelta(days=1),
            ),
        ),
    )
    preset = _preset(Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV))

    likuid = saring.semesta_likuid(p, preset, metrik=metrik.metrik_semua(p))

    assert "AAAA" not in likuid, "UMA yang masih berjalan mengeluarkan emitennya (K9)"
    assert {"BBBB", "CCCC"} <= set(likuid), "notasi yang sudah berakhir / belum mulai tidak"
    assert set(likuid) == set(LIKUID) - {"AAAA"}


# ---------------------------------------------------------------------------------------
# AC-2: determinisme
# ---------------------------------------------------------------------------------------


def test_saring_semesta_memberi_hasil_yang_sama_pada_potret_yang_sama(
    sambungan: sqlite3.Connection,
) -> None:
    """AC-2: dua kali jalan atas potret yang sama memberi urutan dan isi yang identik.

    Hasil saringan dipakai sebagai dasar peringkat dan laporan; kalau urutannya bergantung pada
    hal di luar data (mis. urutan baris basis data atau jam), dua layar bisa menampilkan dua
    kandidat teratas yang berbeda tanpa ada data yang berubah.
    """
    p = _simpan_tiga_keadaan(
        sambungan,
        notasi=(NotasiKhusus(kode="CCCC", jenis="uma", tanggal_mulai=date(2026, 1, 1)),),
    )
    preset = _preset(*_kriteria_dasar(notasi=True))
    angka = metrik.metrik_semua(p)

    pertama = saring.saring_semesta(p, preset, metrik=angka)
    kedua = saring.saring_semesta(p, preset, metrik=angka)

    assert [satu.kode for satu in pertama] == list(p.kode)
    assert pertama == kedua
    assert saring.saring_semesta(p, preset) == saring.saring_semesta(p, preset), (
        "perhitungan metrik di dalamnya pun harus deterministik"
    )
    per_kode = {satu.kode: satu for satu in pertama}
    assert _penilaian(per_kode["CCCC"], "pengecualian_notasi").lolos is False, (
        "CCCC ber-UMA aktif, jadi hasilnya tidak seragam supaya determinisme ini bermakna"
    )


def test_jalankan_saring_memakai_potret_yang_diberikan_tanpa_memuat_ulang(
    sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Detail emiten sudah memuat potretnya; memuatnya lagi di sini memakan ±20 dtk di data kerja.

    Hasilnya harus identik dengan memuat sendiri — potret adalah fungsi snapshot yang sama.
    """
    p = _simpan_tiga_keadaan(sambungan)
    pengatur.siapkan_preset_bawaan(sambungan, TANGGAL)
    preset = saring.preset_terbaru(sambungan, "kualitas-nilai")
    sendiri = pengatur.jalankan_saring(sambungan, preset, hanya_kode=("AAAA",), simpan=False)

    def jangan_dimuat(*_: object, **__: object) -> Potret:
        raise AssertionError("potret dimuat ulang padahal sudah diberikan")

    monkeypatch.setattr(potret, "muat", jangan_dimuat)
    diberi = pengatur.jalankan_saring(sambungan, preset, hanya_kode=("AAAA",), simpan=False, bahan=p)
    assert diberi.hasil_saring == sendiri.hasil_saring
    assert diberi.skor == sendiri.skor
    assert diberi.id_snapshot == sendiri.id_snapshot


def test_jalankan_saring_memakai_metrik_yang_diberikan_tanpa_menghitung_ulang(
    sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simpanan potret web (T99) membawa metriknya juga: ±9 dtk di data kerja."""
    p = _simpan_tiga_keadaan(sambungan)
    pengatur.siapkan_preset_bawaan(sambungan, TANGGAL)
    preset = saring.preset_terbaru(sambungan, "kualitas-nilai")
    angka = metrik.metrik_semua(p)
    sendiri = pengatur.jalankan_saring(sambungan, preset, simpan=False)

    def jangan_dihitung(*_: object, **__: object) -> dict[str, object]:
        raise AssertionError("metrik dihitung ulang padahal sudah diberikan")

    monkeypatch.setattr(metrik, "metrik_semua", jangan_dihitung)
    diberi = pengatur.jalankan_saring(sambungan, preset, simpan=False, bahan=p, angka=angka)
    assert diberi.hasil_saring == sendiri.hasil_saring
    assert diberi.skor == sendiri.skor
    with pytest.raises(ValueError, match="bahan"):
        pengatur.jalankan_saring(sambungan, preset, simpan=False, angka=angka)


def test_peringkat_satu_kode_sama_dengan_peringkatnya_di_seluruh_semesta(
    sambungan: sqlite3.Connection,
) -> None:
    """Detail emiten & `--saring --kode`: dulu `lolos` disaring ke `hanya_kode` sebelum diperingkat,
    jadi kode yang diperiksa sendirian selalu "peringkat 1" (PTBA di data kerja, peringkat 2).
    """
    p = _simpan_semesta_likuid(sambungan)
    preset = replace(
        _preset(Kriteria("adtv20", urutan=1, ambang_rupiah=AMBANG_ADTV)),
        bobot_faktor={"kualitas": 4000, "nilai": 3000, "momentum": 3000},
        bobot_metrik=(
            BobotMetrik("kualitas", "roe_5t", "umum", 10000, "tinggi_baik"),
            BobotMetrik("nilai", "per", "umum", 10000, "rendah_baik"),
            BobotMetrik("momentum", "momentum_12_1", "umum", 10000, "tinggi_baik"),
        ),
    )
    # Metrik skor sintetis — makin akhir kodenya makin baik di ketiga faktor — di atas ADTV20 yang
    # dihitung dari harga. Nilai yang seragam tidak bisa dipakai: z-nya tidak terdefinisi.
    angka = {
        kode: {
            **isi,
            "roe_5t": metrik.Nilai(nama="roe_5t", nilai=0.05 * (urutan + 1), satuan="rasio", asal="uji"),
            "per": metrik.Nilai(nama="per", nilai=20.0 - urutan, satuan="rasio", asal="uji"),
            "momentum_12_1": metrik.Nilai(
                nama="momentum_12_1", nilai=0.1 * (urutan + 1), satuan="rasio", asal="uji"
            ),
        }
        for urutan, (kode, isi) in enumerate(sorted(metrik.metrik_semua(p).items()))
    }
    penuh = pengatur.jalankan_saring(sambungan, preset, simpan=False, bahan=p, angka=angka)
    peringkat = {satu.kode: satu.peringkat for satu in penuh.skor}
    assert peringkat["HHHH"] == 1 and peringkat["CCCC"] == 6, peringkat

    satu_kode = pengatur.jalankan_saring(
        sambungan, preset, hanya_kode=("CCCC",), simpan=False, bahan=p, angka=angka
    )
    assert [(satu.kode, satu.peringkat) for satu in satu_kode.skor] == [("CCCC", 6)]
    assert [satu.kode for satu in satu_kode.hasil_saring] == ["CCCC"]
    assert satu_kode.skor[0].skor_total == next(s for s in penuh.skor if s.kode == "CCCC").skor_total


def test_jalankan_saring_menolak_potret_bersama_pilihan_snapshot_atau_sumber(
    sambungan: sqlite3.Connection,
) -> None:
    """Potret yang diberikan sudah menetapkan snapshot dan sumbernya; pilihan kedua akan diabaikan diam-diam."""
    p = _simpan_tiga_keadaan(sambungan)
    pengatur.siapkan_preset_bawaan(sambungan, TANGGAL)
    preset = saring.preset_terbaru(sambungan, "kualitas-nilai")
    with pytest.raises(ValueError, match="bahan"):
        pengatur.jalankan_saring(sambungan, preset, simpan=False, bahan=p, id_snapshot=p.id_snapshot)
    with pytest.raises(ValueError, match="bahan"):
        pengatur.jalankan_saring(sambungan, preset, simpan=False, bahan=p, sumber=SUMBER)


def test_tanpa_data_notasi_status_belum_terverifikasi_bukan_bersih(
    sambungan: sqlite3.Connection,
) -> None:
    """Tabel notasi yang kosong bukan bukti bahwa emitennya bersih (PRD 7.3, aturan keras 7).

    Sebelum ini `_notasi_aktif` mengembalikan tupel kosong untuk **dua** keadaan yang sangat
    berbeda — "tidak ada notasi" dan "tidak ada berkasnya" — sehingga kriteria pengecualian notasi
    lolos untuk seluruh semesta. Akibatnya saringan bisa memunculkan saham tersuspensi sebagai
    kandidat tanpa satu pun tanda, sementara laporan mutu aplikasi ini sendiri menulis bahwa
    emiten tanpa penanda itu "belum terverifikasi dan tidak dijadikan kandidat otomatis".

    Yang benar: kriteria itu **tidak diterapkan** (bukan gagal, bukan lolos) dan alasannya
    menyebut kata "belum terverifikasi" — sehingga peringkat tetap bisa dihitung sementara
    sebutan "kandidat" ditahan di lapisan pelaporan (`pengatur.LaporanSaring`).
    """
    p = _simpan_tiga_keadaan(sambungan)  # tanpa satu pun baris notasi
    hasil = {
        satu.kode: satu
        for satu in saring.saring_semesta(p, _preset(*_kriteria_dasar(notasi=True)))
    }

    penilaian = _penilaian(hasil["AAAA"], "pengecualian_notasi")
    assert penilaian.berlaku is False, "tidak ada data → kriteria tidak diterapkan"
    assert penilaian.lolos is None, "bukan lolos: statusnya tidak pernah diperiksa"
    assert "belum terverifikasi" in penilaian.alasan
    assert "AAAA" not in [satu.kriteria for satu in hasil["AAAA"].tidak_bisa_dinilai], (
        "kriteria yang tidak diterapkan tidak boleh muncul sebagai 'tidak bisa dinilai'"
    )


def test_data_notasi_yang_ada_membuat_kriteria_berlaku_kembali(
    sambungan: sqlite3.Connection,
) -> None:
    """Begitu ada satu baris notasi, penilaian kembali tegas — untuk yang tercatat maupun tidak.

    Ini penjaga arah sebaliknya dari uji di atas: berkas notasi yang **ada** diperlakukan sebagai
    daftar yang lengkap, sehingga emiten yang tidak tercatat di dalamnya memang lolos kriteria.
    """
    p = _simpan_tiga_keadaan(
        sambungan,
        notasi=(NotasiKhusus(kode="BBBB", jenis="suspensi", tanggal_mulai=date(2026, 1, 1)),),
    )
    hasil = {
        satu.kode: satu
        for satu in saring.saring_semesta(p, _preset(*_kriteria_dasar(notasi=True)))
    }

    lolos_notasi = _penilaian(hasil["AAAA"], "pengecualian_notasi")
    assert lolos_notasi.berlaku is True
    assert lolos_notasi.lolos is True

    kena_notasi = _penilaian(hasil["BBBB"], "pengecualian_notasi")
    assert kena_notasi.lolos is False
    assert "suspensi" in kena_notasi.alasan


@pytest.mark.parametrize(
    ("kode_refresh", "diharapkan"),
    [(0, ["refresh", "saring"]), (1, ["refresh"])],
)
def test_refresh_lalu_saring_menjalankan_keduanya(
    monkeypatch: pytest.MonkeyPatch, kode_refresh: int, diharapkan: list[str]
) -> None:
    """AC-11: `--refresh --saring` (Task Scheduler) menyaring snapshot baru, bukan berhenti sesudah
    refresh; refresh yang gagal tidak boleh disusul saringan atas snapshot lama."""
    from mejasaham import cli

    dipanggil: list[str] = []
    monkeypatch.setattr(
        cli, "jalankan_refresh", lambda argumen: dipanggil.append("refresh") or kode_refresh
    )
    monkeypatch.setattr(
        cli, "jalankan_saring", lambda argumen: dipanggil.append("saring") or cli.KODE_OK
    )

    assert cli.main(["--refresh", "--saring"]) == kode_refresh
    assert dipanggil == diharapkan
