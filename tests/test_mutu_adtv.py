"""Uji dua pemeriksaan mutu yang bergantung ADTV20 (PRD 7.3 dan PRD 9.3/AC-1).

Keduanya sempat tertunda karena "ADTV20 baru ada di Tahap 1", dan pemeriksaan yang tertunda
punya satu sifat berbahaya: ia terlihat seperti lulus. Berkas ini menjaga agar keduanya
benar-benar berjalan, dan yang lebih penting, agar **tidak** bisa diam-diam kembali menjadi
lulus ketika datanya tidak ada.

* **Peringkat ADTV20** (PRD 7.3, 9.3). Dihitung dari baris yang sudah tersimpan, per **hari
  bursa**, bukan per baris mentah. Dua hal itu diuji terpisah karena keduanya bisa salah
  sendiri-sendiri: emiten dengan data 19 hari tidak boleh diperingkat, dan revisi ganda untuk
  satu tanggal tidak boleh menghitung hari yang sama dua kali.
* **Cek sumber kedua** (PRD 7.3) menandai selisih di atas 1%, dan menyebut alasannya ketika
  harga pembanding belum ada — bukan menyatakan lulus. **Cadence-nya** juga diuji: tuntutan
  "tiap minggu" hanya berarti kalau sistem tahu kapan cek terakhir dijalankan, dan cek yang
  berjalan tanpa pembanding tidak boleh dihitung memenuhinya.
* **Gerbang PRD 9.3/AC-1** menolak snapshot ketika emiten ber-ADTV20 tertinggi gagal diambil
  **atau** datanya bolong. Yang gagal diambil justru tetap muncul di peringkat, sebab
  peringkatnya dihitung dari data yang tersimpan; itulah yang membuat kegagalannya terlihat.
* **Penyaringan per sumber** mencegah harga dua sumber dibandingkan satu sama lain dan muncul
  sebagai lonjakan harga yang tidak pernah terjadi.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from mejasaham import db, ingesti, lokasi, mutu, potret
from mejasaham.ingesti import (
    KEGAGALAN_PERMANEN,
    KEGAGALAN_SEMENTARA,
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    GalatIngesti,
    HargaHarian,
    IngestiDibatalkan,
    Kegagalan,
    KumpulanData,
)

TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
SUMBER = "uji"
SUMBER_LAIN = "pembanding"
CLOSE = 1_000


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


def _emiten(kode: str) -> Emiten:
    return Emiten(kode=kode, nama=f"Emiten {kode}", sumber=SUMBER)


def _bar(
    kode: str,
    hari: int,
    *,
    close: int = CLOSE,
    volume: int = 0,
    sumber: str = "",
    tanggal: date | None = None,
) -> HargaHarian:
    """Satu bar pada `TANGGAL - hari`. `nilai` sengaja kosong supaya dihitung close x volume (U6)."""
    return HargaHarian(
        kode=kode,
        tanggal=tanggal or (TANGGAL - timedelta(days=hari)),
        close=close,
        volume=volume,
        penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        sumber=sumber,
    )


def _simpan(
    sambungan: sqlite3.Connection,
    kode: tuple[str, ...],
    *,
    hari: int = 20,
    volume: Mapping[str, int] | None = None,
    hari_terakhir: Mapping[str, int] | None = None,
) -> date:
    """Tulis satu snapshot berisi `kode` dengan `hari` bar masing-masing.

    ADTV20 tiap emiten = `CLOSE` x volume-nya, karena `nilai` dihitung ingesti (U6) —
    jadi angka yang diuji benar-benar berasal dari baris yang tersimpan, bukan dari nilai
    yang ditempel di uji.
    """
    vol = volume or {satu: 1_000 for satu in kode}
    batas = hari_terakhir or {}
    harga = tuple(
        _bar(satu, i, volume=vol[satu])
        for satu in kode
        for i in range(batas.get(satu, 0), hari)
    )
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber=SUMBER, emiten=tuple(_emiten(satu) for satu in kode), harga_harian=harga),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    return TANGGAL


#: 25 kode: cukup untuk menguji pemotongan peringkat sekaligus sisa yang tidak diperiksa.
KODE_25 = tuple(f"E{i:02d}" for i in range(1, 26))


# ---------------------------------------------------------------------------------------
# Peringkat ADTV20
# ---------------------------------------------------------------------------------------


def test_peringkat_adtv_urut_menurun_dan_adtv20_adalah_rata_rata_nilai(sambungan: sqlite3.Connection) -> None:
    """ADTV20 = rata-rata `close x volume` 20 hari bursa; urutannya menurun (PRD 8.2, 9.3)."""
    _simpan(sambungan, ("AAAA", "BBBB", "CCCC"), volume={"AAAA": 100, "BBBB": 300, "CCCC": 200})

    peringkat = mutu.peringkat_adtv(sambungan)

    assert [satu.kode for satu in peringkat] == ["BBBB", "CCCC", "AAAA"]
    assert [int(satu.adtv20) for satu in peringkat] == [CLOSE * 300, CLOSE * 200, CLOSE * 100]
    assert all(satu.hari_terpakai == 20 for satu in peringkat)


def test_emiten_dengan_kurang_dari_20_hari_tidak_diperingkat(sambungan: sqlite3.Connection) -> None:
    """Peringkatnya per hari bursa, bukan per baris: 19 hari belum cukup untuk ADTV20.

    Emiten baru yang ikut diperingkat dari 19 hari akan terlihat lebih likuid daripada
    sebenarnya — dan justru emiten seperti itulah yang paling sering gagal diambil.
    """
    _simpan(sambungan, ("LAMA", "BARU"), volume={"LAMA": 100, "BARU": 900}, hari_terakhir={"BARU": 1})

    peringkat = mutu.peringkat_adtv(sambungan)

    assert [satu.kode for satu in peringkat] == ["LAMA"]
    assert peringkat[0].hari_terpakai == 20


def test_peringkat_belum_bisa_dihitung_bila_hari_bursa_kurang_dari_20(sambungan: sqlite3.Connection) -> None:
    """Kurang dari 20 hari bursa = peringkat kosong, bukan peringkat dari hari seadanya."""
    _simpan(sambungan, ("AAAA",), hari=19)

    assert mutu.peringkat_adtv(sambungan) == ()


def test_hari_yang_sama_tidak_dihitung_dua_kali(sambungan: sqlite3.Connection) -> None:
    """Revisi ganda untuk satu tanggal tidak boleh menggeser peringkat.

    Kalau baris mentah yang dihitung (bukan `v_*_terkini`), emiten dengan satu hari direvisi
    akan tampak punya hari lebih banyak — dan peringkatnya berubah karena sebuah koreksi,
    bukan karena pasar.
    """
    _simpan(sambungan, ("AAAA",), volume={"AAAA": 100})
    revisi = HargaHarian(
        kode="AAAA",
        tanggal=TANGGAL - timedelta(days=5),
        close=CLOSE,
        volume=100,
        penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
    )
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber=SUMBER, harga_harian=(revisi,)),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=1),
    )

    peringkat = mutu.peringkat_adtv(sambungan)

    assert len(peringkat) == 1
    assert peringkat[0].hari_terpakai == 20
    assert int(peringkat[0].adtv20) == CLOSE * 100


def test_peringkat_dibatasi_jumlah_yang_diminta(sambungan: sqlite3.Connection) -> None:
    """`jumlah` memotong peringkat; bawaannya 50 sesuai PRD 9.3."""
    _simpan(sambungan, KODE_25, volume={satu: 100 + i for i, satu in enumerate(KODE_25)})

    assert len(mutu.peringkat_adtv(sambungan, jumlah=10)) == 10
    assert len(mutu.peringkat_adtv(sambungan, jumlah=50)) == 25


# ---------------------------------------------------------------------------------------
# Cek sumber kedua (PRD 7.3)
# ---------------------------------------------------------------------------------------


def test_selisih_di_atas_ambang_ditandai_dan_yang_di_bawah_tidak(sambungan: sqlite3.Connection) -> None:
    """Ambang 1% (PRD 7.3): 2% ditandai, 0,5% tidak; yang tidak bisa dihitung dibedakan."""
    _simpan(
        sambungan,
        ("BEDA", "MIRIP", "LEBIH", "PEMBANDING", "TANPA"),
        hari=20,
        volume={"BEDA": 900, "MIRIP": 800, "LEBIH": 700, "PEMBANDING": 600, "TANPA": 500},
    )
    pembanding = KumpulanData(
        sumber=SUMBER_LAIN,
        harga_harian=(
            _bar("BEDA", 0, close=1_020, volume=500, sumber=SUMBER_LAIN),
            _bar("MIRIP", 0, close=1_005, volume=500, sumber=SUMBER_LAIN),
            _bar("LEBIH", 0, close=500, volume=500, sumber=SUMBER_LAIN),
            _bar("PEMBANDING", 0, close=CLOSE, volume=500, sumber=SUMBER_LAIN),
        ),
    )
    ingesti.simpan(sambungan, pembanding, tanggal_data=TANGGAL, momen=MOMEN + timedelta(hours=2))

    laporan = mutu.bandingkan_sumber_kedua(
        sambungan, tanggal_data=TANGGAL, sumber_utama=SUMBER, sumber_pembanding=SUMBER_LAIN
    )

    assert laporan.sumber_pembanding == SUMBER_LAIN
    assert {satu.kode for satu in laporan.ditandai} == {"BEDA", "LEBIH"}
    # "TANPA" tidak punya bar pembanding pada tanggal itu → dilaporkan, bukan dilewati diam-diam.
    assert any("TANPA" in satu for satu in laporan.belum_dapat_dijalankan)


def test_sumber_pembanding_yang_belum_ada_bukan_berarti_lulus(sambungan: sqlite3.Connection) -> None:
    """Tanpa harga pembanding, PRD 7.3 belum dijalankan — dan itu dikatakan, bukan dianggap lulus."""
    _simpan(sambungan, ("AAAA",))

    laporan = mutu.bandingkan_sumber_kedua(sambungan, tanggal_data=TANGGAL, sumber_utama=SUMBER)

    assert laporan.diperiksa == ()
    assert laporan.ditandai == ()
    assert any("sumber kedua" in satu.lower() for satu in laporan.belum_dapat_dijalankan)


def test_temuan_selisih_menjadi_tak_wajar_dan_tidak_bisa_dihitung_menjadi_catatan() -> None:
    """Tingkat temuannya dibedakan: selisih nyata `TAK_WAJAR`, selisih tak terhitung `CATATAN`."""
    laporan = mutu.LaporanPerbandingan(
        tanggal_data=TANGGAL.isoformat(),
        sumber_utama=SUMBER,
        sumber_pembanding=SUMBER_LAIN,
        diperiksa=(
            mutu.BedaSumber("BEDA", TANGGAL.isoformat(), 1_000, 1_020, mutu.AMBANG_BEDA_SUMBER * 2),
            mutu.BedaSumber("NOL", TANGGAL.isoformat(), 0, 1_000, None),
        ),
    )

    temuan = mutu.temuan_perbandingan(laporan)
    tingkat = {satu.kode: satu.tingkat for satu in temuan}

    assert tingkat == {"BEDA": mutu.TAK_WAJAR, "NOL": mutu.CATATAN}
    assert all(satu.keterangan for satu in temuan)


def test_selisih_tak_terhitung_dilaporkan_bukan_dianggap_sama(sambungan: sqlite3.Connection) -> None:
    """Penutupan kosong di salah satu sumber → selisih tak terhitung, bukan 0% yang terbaca "sama".

    Diuji lewat data yang benar-benar ditulis: baris pembanding ada, tetapi penutupannya kosong
    (`close` NULL) — keadaan yang nyata terjadi ketika sumber menerbitkan volume tanpa harga.
    """
    _simpan(sambungan, ("AAAA",))
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_LAIN,
            harga_harian=(
                HargaHarian(
                    kode="AAAA",
                    tanggal=TANGGAL,
                    volume=500,
                    penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
                    sumber=SUMBER_LAIN,
                ),
            ),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=2),
    )

    laporan = mutu.bandingkan_sumber_kedua(
        sambungan, tanggal_data=TANGGAL, sumber_utama=SUMBER, sumber_pembanding=SUMBER_LAIN
    )

    assert len(laporan.selisih_tak_terhitung) == 1
    assert laporan.selisih_tak_terhitung[0].selisih is None
    assert laporan.ditandai == ()
    assert [satu.tingkat for satu in mutu.temuan_perbandingan(laporan)] == [mutu.CATATAN]


# ---------------------------------------------------------------------------------------
# Cadence cek sumber kedua (PRD 7.3: "tiap minggu")
# ---------------------------------------------------------------------------------------

#: "Hari ini" untuk uji cadence — sengaja dipisah dari `MOMEN` supaya uji bisa memindahkan
#: kapan cek dijalankan tanpa ikut memindahkan hari penilaiannya.
HARI_INI = date(2026, 7, 1)


def _catat_cek(
    sambungan: sqlite3.Connection,
    *,
    momen: datetime,
    lengkap: bool = True,
) -> int:
    """Catat satu jalan cek sumber kedua tanpa menjalankan perbandingannya.

    Yang diuji di bagian ini adalah **pembacaan catatannya**, jadi laporannya disusun langsung:
    perbandingannya sendiri sudah diuji di bagian sebelumnya, dan jalur nyatanya diuji di
    `test_jalur_nyata_...` di bawah.
    """
    laporan = mutu.LaporanPerbandingan(
        tanggal_data=TANGGAL.isoformat(),
        sumber_utama=SUMBER,
        sumber_pembanding=SUMBER_LAIN if lengkap else None,
        diperiksa=(
            (mutu.BedaSumber("AAAA", TANGGAL.isoformat(), CLOSE, CLOSE, Decimal("0")),)
            if lengkap
            else ()
        ),
        belum_dapat_dijalankan=(
            [] if lengkap else ["harga dari sumber kedua belum ada di basis data"]
        ),
    )
    return mutu.catat_cek_sumber_kedua(sambungan, laporan, momen=momen)


def test_cadence_belum_pernah_dijalankan_bukan_lulus(sambungan: sqlite3.Connection) -> None:
    """Tuntutan mingguan yang belum pernah dijalankan harus terlihat, bukan dianggap beres."""
    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)

    assert keadaan.status == mutu.STATUS_BELUM_PERNAH
    assert not keadaan.lulus
    assert keadaan.berlaku_sampai is None
    temuan = keadaan.temuan()
    assert temuan.tingkat == mutu.CATATAN, "bukan menghalangi: tidak ada angka emiten yang salah"
    assert temuan.kode == "-", "temuannya tentang proses, bukan tentang satu emiten"
    assert "belum pernah dijalankan" in temuan.keterangan
    assert "cek-sumber-kedua" in temuan.keterangan, "temuan harus menyebut cara menutupnya"


@pytest.mark.parametrize(
    ("jarak_hari", "status"),
    [
        (0, mutu.STATUS_TEPAT_WAKTU),
        (6, mutu.STATUS_TEPAT_WAKTU),
        (7, mutu.STATUS_TEPAT_WAKTU),  # hari ke-7 adalah jadwal berikutnya, belum lewat
        (8, mutu.STATUS_LEWAT),
        (30, mutu.STATUS_LEWAT),
    ],
)
def test_cadence_batas_tujuh_hari(
    sambungan: sqlite3.Connection, jarak_hari: int, status: str
) -> None:
    """Batasnya 7 hari (PRD 7.3 "tiap minggu"), dan batas itu inklusif di hari ke-7."""
    _catat_cek(sambungan, momen=MOMEN - timedelta(days=jarak_hari))

    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)

    assert keadaan.status == status
    assert keadaan.hari_sejak_lengkap == jarak_hari
    assert keadaan.lulus is (status == mutu.STATUS_TEPAT_WAKTU)
    assert keadaan.berlaku_sampai == (HARI_INI + timedelta(days=7 - jarak_hari)).isoformat()


def test_percobaan_belum_lengkap_tidak_memenuhi_cadence(sambungan: sqlite3.Connection) -> None:
    """Cek yang berjalan tanpa pembanding tidak membandingkan apa pun — jadi bukan cek yang diminta.

    Kasus nyatanya: pengguna menjalankan `--cek-sumber-kedua` sebelum harga pembanding diimpor.
    Kalau catatan itu dihitung memenuhi, peringatan mingguan akan padam justru ketika PRD 7.3
    sama sekali belum dijalankan.
    """
    _catat_cek(sambungan, momen=MOMEN - timedelta(days=8))
    _catat_cek(sambungan, momen=MOMEN, lengkap=False)

    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)

    assert keadaan.status == mutu.STATUS_LEWAT, "cadence dihitung dari cek lengkap terakhir"
    assert keadaan.hari_sejak_lengkap == 8
    assert keadaan.percobaan_terakhir_belum_lengkap
    assert "belum lengkap" in keadaan.ringkas()
    assert "harga dari sumber kedua belum ada" in keadaan.ringkas(), "sebabnya ikut disebut"


def test_hanya_percobaan_belum_lengkap_menyebut_percobaan_itu(sambungan: sqlite3.Connection) -> None:
    """Belum ada cek lengkap ≠ tidak ada usaha: percobaan yang gagal tetap disebutkan."""
    _catat_cek(sambungan, momen=MOMEN, lengkap=False)

    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)

    assert keadaan.status == mutu.STATUS_BELUM_PERNAH
    teks = keadaan.ringkas()
    assert "belum ada cek sumber kedua yang lengkap" in teks
    assert HARI_INI.isoformat() in teks, "tanggal percobaan terakhirnya ikut terlihat"


def test_catatan_bertanggal_di_depan_hari_ini_tidak_dianggap_lulus(sambungan: sqlite3.Connection) -> None:
    """Jam sistem mundur tidak boleh terbaca sebagai "baru saja diperiksa"."""
    _catat_cek(sambungan, momen=MOMEN + timedelta(days=3))

    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)

    assert keadaan.status == mutu.STATUS_TIDAK_DAPAT_DINILAI
    assert not keadaan.lulus
    assert "di depan" in (keadaan.alasan or "")


def test_tanggal_catatan_yang_tidak_terbaca_tidak_dianggap_lulus(
    sambungan: sqlite3.Connection,
) -> None:
    """Baris yang disunting tangan bisa lolos CHECK bentuk tanggal, tetapi bukan tanggal sah."""
    with db.tulis(sambungan):
        sambungan.execute(
            "INSERT INTO cek_sumber_kedua (dijalankan_pada, tanggal_data, jumlah_diperiksa,"
            " jumlah_ditandai, jumlah_tak_terhitung, jumlah_belum_dapat, cakupan)"
            " VALUES ('2026-13-45T99:99:99+07:00', ?, 1, 0, 0, 0, 'lengkap')",
            (TANGGAL.isoformat(),),
        )

    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)

    assert keadaan.status == mutu.STATUS_TIDAK_DAPAT_DINILAI
    assert not keadaan.lulus
    assert "tidak terbaca" in (keadaan.alasan or "")


def test_jalur_nyata_mencatat_cakupan_dan_memenuhi_cadence(sambungan: sqlite3.Connection) -> None:
    """Pencatatan terjadi di jalur yang benar-benar dipakai `--cek-sumber-kedua`, bukan di uji."""
    from mejasaham import pengatur

    _simpan(sambungan, ("AAAA", "BBBB"), volume={"AAAA": 900, "BBBB": 100})

    pertama = pengatur.cek_sumber_kedua(sambungan, sumber_utama=SUMBER, momen=MOMEN)

    assert not pertama.lengkap, "tanpa harga pembanding belum ada yang dibandingkan"
    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)
    assert keadaan.status == mutu.STATUS_BELUM_PERNAH
    assert keadaan.cakupan_terakhir == mutu.CAKUPAN_BELUM_LENGKAP

    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_LAIN,
            harga_harian=tuple(
                _bar(satu, 0, volume=500, sumber=SUMBER_LAIN) for satu in ("AAAA", "BBBB")
            ),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=1),
    )
    kedua = pengatur.cek_sumber_kedua(
        sambungan, sumber_utama=SUMBER, sumber_pembanding=SUMBER_LAIN, momen=MOMEN
    )

    assert kedua.lengkap
    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)
    assert keadaan.status == mutu.STATUS_TEPAT_WAKTU
    assert keadaan.hari_sejak_lengkap == 0
    assert keadaan.berlaku_sampai == (HARI_INI + timedelta(days=7)).isoformat()

    # Cek yang **menemukan** selisih tetap cek yang sudah dijalankan: cakupannya tidak berkurang,
    # dan cadence-nya tetap terpenuhi. Yang berbeda hanyalah temuannya, bukan kehadirannya.
    mutu.catat_cek_sumber_kedua(
        sambungan,
        mutu.LaporanPerbandingan(
            tanggal_data=TANGGAL.isoformat(),
            sumber_utama=SUMBER,
            sumber_pembanding=SUMBER_LAIN,
            diperiksa=(
                mutu.BedaSumber("AAAA", TANGGAL.isoformat(), CLOSE, 1_050, Decimal("0.05")),
            ),
        ),
        momen=MOMEN + timedelta(hours=3),
    )
    setelah_beda = mutu.keadaan_cek_sumber_kedua(sambungan, momen=HARI_INI)
    assert setelah_beda.status == mutu.STATUS_TEPAT_WAKTU
    assert setelah_beda.cakupan_terakhir == mutu.CAKUPAN_LENGKAP


def test_refresh_memperingatkan_cadence_lewat_tanpa_menahan_snapshot(
    sambungan: sqlite3.Connection, folder_data: Path
) -> None:
    """Peringatan sampai ke jalan harian yang benar-benar dijalankan orang (PRD 7.3).

    Snapshotnya tetap terbit: cek mingguan yang tertunda tidak membuat satu pun angka emiten
    salah, dan menahannya akan menukar satu masalah dengan masalah yang lebih besar.
    """
    from mejasaham import pengatur

    _simpan(sambungan, ("AAAA", "BBBB"), volume={"AAAA": 900, "BBBB": 100})
    _catat_cek(sambungan, momen=MOMEN - timedelta(days=9))
    folder = folder_data / "konfigurasi"
    _tulis_emiten(folder, ("AAAA", "BBBB"))

    laporan = pengatur.jalankan_refresh(
        sambungan, _PengambilPalsu(), folder_impor=folder, momen=MOMEN
    )

    assert laporan.sukses and not laporan.dibatalkan
    assert any("cek sumber kedua" in satu for satu in laporan.peringatan)
    assert laporan.laporan_mutu is not None
    assert laporan.laporan_mutu.cek_sumber_kedua is not None
    assert not laporan.laporan_mutu.cek_sumber_kedua.lulus
    assert "cek_sumber_kedua_lewat" in {satu.jenis for satu in laporan.laporan_mutu.temuan}


# ---------------------------------------------------------------------------------------
# Laporan mutu: peringkat, emiten kritis, dan penyaringan per sumber
# ---------------------------------------------------------------------------------------


def test_emiten_kritis_yang_ditandai_tak_wajar_muncul_di_laporan(
    sambungan: sqlite3.Connection,
) -> None:
    """AC-1 dikatakan untuk emiten bolong, tetapi emiten kritis yang **tak wajar** pun harus
    terlihat: ia sama-sama tidak boleh ikut diperingkat, dan itu bukan keadaan yang sepi
    peringatan.

    Jalurnya sengaja dibuat lewat peringkat ADTV20 yang nyata: lonjakan 5x pada hari terakhir
    menaikkan nilai transaksinya sehingga emiten itu justru menduduki peringkat teratas.
    """
    _simpan(sambungan, ("MELONJAK", "TENANG"), volume={"MELONJAK": 900, "TENANG": 100})
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            harga_harian=(_bar("MELONJAK", 0, close=5_000, volume=900),),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=1),
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL, sumber=SUMBER)

    assert [satu.kode for satu in laporan.peringkat_adtv][0] == "MELONJAK"
    assert any(satu.jenis == "lonjakan_tanpa_aksi" and satu.kode == "MELONJAK" for satu in laporan.temuan)
    assert any(satu.jenis == "kritis_bermasalah" and satu.kode == "MELONJAK" for satu in laporan.temuan)
    assert "MELONJAK" in laporan.dikeluarkan


def test_peringkat_hanya_memuat_emiten_dari_sumber_yang_diperiksa(
    sambungan: sqlite3.Connection,
) -> None:
    """Peringkat disaring per sumber; mencampur dua sumber membuatnya bukan peringkat apa pun."""
    _simpan(sambungan, ("UTAMA",), volume={"UTAMA": 100})
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_LAIN,
            harga_harian=tuple(_bar("LAIN", i, volume=900, sumber=SUMBER_LAIN) for i in range(20)),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=2),
    )

    assert [satu.kode for satu in mutu.peringkat_adtv(sambungan, sumber=SUMBER)] == ["UTAMA"]
    assert [satu.kode for satu in mutu.peringkat_adtv(sambungan, sumber=SUMBER_LAIN)] == ["LAIN"]


def test_sumber_utama_bukan_sumber_yang_paling_banyak_baris_pada_satu_tanggal(
    sambungan: sqlite3.Connection,
) -> None:
    """Penentuan sumber utama memakai **riwayat** bar, bukan banyaknya baris pada satu tanggal.

    Kesalahan yang dijaga di sini nyata dan pernah terjadi saat uji lewat baris perintah: harga
    pembanding yang diimpor untuk 16 emiten sekaligus punya jumlah baris **lebih banyak pada
    tanggal snapshot** daripada sumber utamanya, sehingga ia terpilih sebagai sumber utama.
    Akibatnya bukan sekadar salah label: peringkat ADTV20 dihitung dari sumber yang hanya punya
    satu hari, lalu laporannya berkata "ADTV20 belum bisa dihitung" — dan pemeriksaan yang
    sebenarnya bisa dijalankan berubah menjadi tidak bisa dijalankan.
    """
    from mejasaham import pengatur

    _simpan(sambungan, ("AAAA", "BBBB"), volume={"AAAA": 900, "BBBB": 800})
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_LAIN,
            harga_harian=(
                _bar("AAAA", 0, close=1_020, volume=500, sumber=SUMBER_LAIN),
                _bar("BBBB", 0, close=1_005, volume=500, sumber=SUMBER_LAIN),
                _bar("CCCC", 0, close=1_000, volume=500, sumber=SUMBER_LAIN),
            ),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=2),
    )

    laporan = pengatur.cek_sumber_kedua(sambungan)

    assert laporan.sumber_utama == SUMBER
    assert laporan.sumber_pembanding == SUMBER_LAIN
    assert {satu.kode for satu in laporan.diperiksa} == {"AAAA", "BBBB"}
    assert not laporan.belum_dapat_dijalankan


def test_emiten_yang_kehilangan_hari_terakhir_tidak_menggeser_peringkat(
    sambungan: sqlite3.Connection,
) -> None:
    """Daftar kritis memakai hari bursa bersama, bukan 20 hari terakhir milik tiap emiten.

    Emiten yang bar terakhirnya hilang tidak boleh tetap menduduki peringkat teratas dengan
    rata-rata dari hari-hari yang lebih tua: angka itu bukan ADTV20 hari ini, dan memakainya
    akan menahan emiten lain keluar dari daftar 50 teratas — yaitu menahan yang justru perlu
    diperiksa.
    """
    _simpan(
        sambungan,
        ("HILANG", "LENGKAP"),
        volume={"HILANG": 900, "LENGKAP": 100},
        hari_terakhir={"HILANG": 1},
    )

    peringkat = mutu.peringkat_adtv(sambungan)

    assert [satu.kode for satu in peringkat] == ["LENGKAP"]


def test_laporan_tanpa_peringkat_tidak_mengaku_lulus(sambungan: sqlite3.Connection) -> None:
    """Peringkat kosong = peringkatnya belum bisa dihitung, dan itu terlihat di laporan."""
    _simpan(sambungan, ("AAAA",), hari=19)

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL, sumber=SUMBER)

    assert laporan.peringkat_adtv == ()
    assert not any(satu.jenis == "peringkat_adtv20" for satu in laporan.temuan)


def test_dua_sumber_tidak_dibandingkan_satu_sama_lain_sebagai_lonjakan(
    sambungan: sqlite3.Connection,
) -> None:
    """Harga dua sumber pada hari berbeda bukan lonjakan — dan **hanya** penyaringan yang
    mencegahnya terbaca begitu.

    Tanpa penyaringan, baris sumber pembanding menjadi "harga sebelumnya" milik emiten yang
    sama, sehingga lompatan 1.000 → 5.000 muncul sebagai lonjakan 5x tanpa aksi korporasi.
    """
    _simpan(sambungan, ("AAAA",), hari=1)
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_LAIN,
            harga_harian=(_bar("AAAA", 0, close=5_000, volume=500, sumber=SUMBER_LAIN),),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=2),
    )

    tersaring = mutu.periksa(sambungan, tanggal_data=TANGGAL, sumber=SUMBER)
    tercampur = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    assert not any(satu.jenis == "lonjakan_tanpa_aksi" for satu in tersaring.temuan)
    assert any(satu.jenis == "lonjakan_tanpa_aksi" for satu in tercampur.temuan)


def test_penyaringan_sumber_juga_membatasi_jumlah_bar_yang_dilaporkan(sambungan: sqlite3.Connection) -> None:
    """Angka "bar terkini" mengikuti penyaringan, supaya laporan tidak menjumlah dua sumber."""
    _simpan(sambungan, ("AAAA",))
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_LAIN,
            harga_harian=(_bar("AAAA", 0, close=1_500, volume=500, sumber=SUMBER_LAIN),),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN + timedelta(hours=2),
    )

    assert mutu.periksa(sambungan, tanggal_data=TANGGAL, sumber=SUMBER).jumlah_bar_terkini == 20
    assert mutu.periksa(sambungan, tanggal_data=TANGGAL).jumlah_bar_terkini == 21


# ---------------------------------------------------------------------------------------
# Gerbang PRD 9.3 / AC-1
# ---------------------------------------------------------------------------------------


def test_emiten_kritis_yang_gagal_diambil_membatalkan_snapshot() -> None:
    """PRD 9.3: satu saja emiten ber-ADTV20 tertinggi gagal → snapshot tidak diterbitkan."""
    with pytest.raises(IngestiDibatalkan, match="ADTV20"):
        ingesti.periksa_ambang_gagal(
            [Kegagalan("BBCA", "timeout")], 500, ambang_persen=5, emiten_kritis=("BBCA", "BBRI")
        )


def test_kegagalan_bukan_emiten_kritis_tidak_membatalkan_snapshot() -> None:
    """Gagal di emiten biasa tetap dicatat, tetapi tidak membatalkan snapshot (PRD 9.3)."""
    ingesti.periksa_ambang_gagal(
        [Kegagalan("KECIL", "timeout")], 500, ambang_persen=5, emiten_kritis=("BBCA",)
    )


def test_ambang_persen_tetap_berlaku_saat_daftar_kritis_kosong() -> None:
    """Tanpa daftar kritis pun, ambang 5% masih menolak — dua syarat PRD 9.3 berdiri sendiri."""
    with pytest.raises(IngestiDibatalkan, match="5"):
        ingesti.periksa_ambang_gagal(
            [Kegagalan(f"E{i}", "timeout") for i in range(30)], 500, ambang_persen=5, emiten_kritis=()
        )


def test_daftar_kritis_diambil_dari_peringkat_adtv_yang_tersimpan(sambungan: sqlite3.Connection) -> None:
    """Daftar kritis berasal dari peringkat ADTV20, dan emitennya benar-benar yang terbesar."""
    _simpan(sambungan, KODE_25, volume={satu: 100 + i for i, satu in enumerate(KODE_25)})

    kritis = tuple(satu.kode for satu in mutu.peringkat_adtv(sambungan, jumlah=5))

    assert kritis == ("E25", "E24", "E23", "E22", "E21")


class _PengambilPalsu:
    """Pengambil data palsu: menyerahkan harga untuk semua kode kecuali yang diminta gagal.

    Dua daftar kegagalan (`gagal` dan `permanen`) ada supaya uji U18 bisa membuktikan bahwa
    jenisnya benar-benar sampai ke gerbang — bukan hanya tersedia di dalam kelas `Kegagalan`.
    """

    def __init__(self, gagal: tuple[str, ...] = (), permanen: tuple[str, ...] = ()) -> None:
        self.gagal = gagal
        self.permanen = permanen
        self.diminta: tuple[str, ...] = ()

    def ambil(self, daftar: object) -> KumpulanData:
        kode = tuple(satu.kode for satu in daftar)  # type: ignore[attr-defined]
        self.diminta = kode
        semua_gagal = set(self.gagal) | set(self.permanen)
        diambil = tuple(satu for satu in kode if satu not in semua_gagal)
        return KumpulanData(
            sumber=SUMBER,
            emiten=tuple(_emiten(satu) for satu in diambil),
            harga_harian=tuple(_bar(satu, i, volume=1_000) for satu in diambil for i in range(20)),
            gagal=tuple(
                Kegagalan(
                    satu,
                    "sumber menyatakan tidak ada data: No data found, symbol may be delisted"
                    if satu in self.permanen
                    else "timeout",
                    KEGAGALAN_PERMANEN if satu in self.permanen else KEGAGALAN_SEMENTARA,
                )
                for satu in kode
                if satu in semua_gagal
            ),
        )


def _tulis_emiten(folder: Path, kode: tuple[str, ...]) -> None:
    """Tulis `emiten.csv` seperti yang dibaca jalur refresh (AC-12: berkas rujukan pengguna).

    Barisnya disusun dari `berkas.SPESIFIKASI`, sehingga jumlah kolomnya tidak bisa diam-diam
    bergeser ketika spesifikasi berkas berubah.
    """
    from mejasaham import berkas

    kolom = berkas.SPESIFIKASI["emiten"].nama_kolom
    lokasi.pastikan_folder(folder)
    baris = []
    for satu in kode:
        isi = {nama: "" for nama in kolom}
        isi.update(
            {
                "kode": satu,
                "nama": f"Emiten {satu}",
                "sumber": SUMBER,
                "dicatat_pada": "2026-01-01",
            }
        )
        baris.append(";".join(isi[nama] for nama in kolom))
    (folder / "emiten.csv").write_text(
        ";".join(kolom) + "\n" + "\n".join(baris) + "\n", encoding="utf-8"
    )


def test_refresh_membatalkan_snapshot_saat_emiten_ber_adtv20_teratas_gagal(
    sambungan: sqlite3.Connection, folder_data: Path
) -> None:
    """PRD 9.3/AC-1 disambungkan, bukan hanya tersedia: jalur `--refresh` benar-benar memakainya.

    Daftar kritisnya berasal dari peringkat yang **sudah tersimpan** (hari-hari sebelumnya),
    sehingga emiten yang gagal diambil hari ini tetap bisa dikenali sebagai emiten teratas —
    kalau daftarnya dihitung dari data hari ini saja, emiten yang gagal justru tidak akan ada
    di dalamnya, dan kegagalannya lolos tanpa suara.
    """
    from mejasaham import pengatur

    _simpan(sambungan, ("BBCA", "AAAA"), volume={"BBCA": 900, "AAAA": 100})
    folder = folder_data / "konfigurasi"
    _tulis_emiten(folder, ("BBCA", "AAAA"))
    pengambil = _PengambilPalsu(gagal=("BBCA",))

    laporan = pengatur.jalankan_refresh(
        sambungan, pengambil, folder_impor=folder, momen=MOMEN + timedelta(days=1)
    )

    assert laporan.dibatalkan
    assert not laporan.sukses
    assert "BBCA" in laporan.pesan
    # Snapshot tidak diterbitkan: yang tersimpan tetap snapshot lama.
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 1


def test_refresh_lolos_saat_yang_gagal_bukan_emiten_kritis(
    sambungan: sqlite3.Connection, folder_data: Path
) -> None:
    """Kegagalan di emiten biasa tidak membatalkan snapshot — dua syarat PRD 9.3 terpisah.

    Semestanya sengaja 60 emiten supaya daftar kritis 50 teratas benar-benar memotong sesuatu:
    dengan 2 emiten saja, semua emiten "kritis" dan uji ini tidak membuktikan apa pun.
    """
    from mejasaham import pengatur

    kode = tuple(f"E{i:02d}" for i in range(1, 61))
    _simpan(sambungan, kode, volume={satu: i for i, satu in enumerate(kode)})
    folder = folder_data / "konfigurasi"
    _tulis_emiten(folder, kode)
    pengambil = _PengambilPalsu(gagal=("E01",))  # volume terkecil → di luar 50 teratas

    laporan = pengatur.jalankan_refresh(
        sambungan, pengambil, folder_impor=folder, momen=MOMEN + timedelta(days=1)
    )

    assert laporan.sukses
    assert not laporan.dibatalkan
    assert "E01" in " ".join(laporan.peringatan)


def test_refresh_lolos_saat_kegagalan_permanen_di_atas_ambang_lima_persen(
    sambungan: sqlite3.Connection, folder_data: Path
) -> None:
    """U18 pada jalur nyata: 5 dari 60 kode (8,3% > 5%) tidak diperdagangkan lagi.

    Inilah bentuk kejadian 9 Okt 2026 (57 dari 973 kode = 5,9%) dalam ukuran yang bisa diuji:
    ambang persen terlewati, tetapi seluruhnya kegagalan permanen — jadi snapshot **terbit**.
    Semestanya 60 emiten supaya daftar kritis 50 teratas benar-benar memotong sesuatu, dan
    yang gagal sengaja ber-volume terkecil supaya bukan emiten kritis.
    """
    from mejasaham import pengatur

    kode = tuple(f"E{i:02d}" for i in range(1, 61))
    _simpan(sambungan, kode, volume={satu: i for i, satu in enumerate(kode)})
    folder = folder_data / "konfigurasi"
    _tulis_emiten(folder, kode)
    mati = ("E01", "E02", "E03", "E04", "E05")
    pengambil = _PengambilPalsu(permanen=mati)

    laporan = pengatur.jalankan_refresh(
        sambungan, pengambil, folder_impor=folder, momen=MOMEN + timedelta(days=1)
    )

    assert laporan.sukses and not laporan.dibatalkan, "kode mati tidak boleh memblokir selamanya"
    assert "5 permanen, 0 sementara" in laporan.pesan
    assert "5 emiten tidak diperdagangkan lagi" in " ".join(laporan.peringatan)


def test_refresh_membatalkan_saat_kegagalan_sementara_di_atas_ambang_lima_persen(
    sambungan: sqlite3.Connection, folder_data: Path
) -> None:
    """Pembanding yang menentukan bagi uji di atas: jumlah yang sama, jenis yang berbeda.

    Tanpa uji ini, "snapshot terbit" bisa saja terjadi karena gerbangnya memang tidak pernah
    menolak apa pun — dan itu berarti U18 telah melemahkan PRD 9.3, bukan menajamkannya.
    """
    from mejasaham import pengatur

    kode = tuple(f"E{i:02d}" for i in range(1, 61))
    _simpan(sambungan, kode, volume={satu: i for i, satu in enumerate(kode)})
    folder = folder_data / "konfigurasi"
    _tulis_emiten(folder, kode)
    gagal = ("E01", "E02", "E03", "E04", "E05")
    pengambil = _PengambilPalsu(gagal=gagal)

    laporan = pengatur.jalankan_refresh(
        sambungan, pengambil, folder_impor=folder, momen=MOMEN + timedelta(days=1)
    )

    assert laporan.dibatalkan and not laporan.sukses
    assert "gagal diambil sementara" in laporan.pesan
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 1


# ---------------------------------------------------------------------------------------
# Jalur impor: kolom `sumber` per baris
# ---------------------------------------------------------------------------------------


def test_berkas_harga_boleh_menyatakan_sumber_per_baris(tmp_path: Path) -> None:
    """Berkas impor boleh memuat `sumber` sendiri — tanpa itu cek sumber kedua tak mungkin."""
    from mejasaham import berkas

    assert "sumber" in berkas.SPESIFIKASI["harga_harian"].nama_kolom

    folder = tmp_path / "impor"
    folder.mkdir()
    (folder / "harga-harian.csv").write_text(
        ";".join(berkas.SPESIFIKASI["harga_harian"].nama_kolom) + "\n"
        "AAAA;2026-06-30;1000;1050;990;1025;1000000;;tidak_disesuaikan;pembanding\n",
        encoding="utf-8",
    )

    hasil = berkas.baca_folder(folder)

    assert len(hasil.kumpulan.harga_harian) == 1
    assert hasil.kumpulan.harga_harian[0].sumber == "pembanding"
