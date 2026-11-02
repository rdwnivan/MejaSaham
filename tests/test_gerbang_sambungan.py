"""Uji gerbang sambungan dan hari bolong (K97 langkah 3, syarat b dan d).

Janji yang diuji:

* **Gerbang (b):** deret yang disambung hanya dipakai bila pada hari tumpang-tindih sebelum
  tanggal sambung (minimal `potret.HARI_TUMPANG_TINDIH_MINIMUM`) penutupan kedua sumber sama
  persis. Bila berbeda atau buktinya kurang, metrik harga emiten itu "tidak dihitung" beserta
  alasannya — bukan disambung diam-diam.
* **Hari bolong (d):** hari bursa sejak tanggal sambung tanpa satu bar resmi pun tetap bolong
  (tidak diisi yfinance), disebut di laporan mutu, dan membuat peringkat berstatus PERINGKAT
  SEMENTARA selama hari itu ada di jendela metrik. Kalender yang belum memuat rentangnya juga
  membuat peringkat sementara: hari bolong yang tidak bisa dihitung bukan berarti tidak ada.

Data ditulis lewat jalur nyata (`ingesti.simpan`).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import db, ingesti, lokasi, metrik, mutu, pengatur, potret
from mejasaham.ingesti import (
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    HargaHarian,
    HariBursa,
    KumpulanData,
    SambunganHarga,
)
from mejasaham.pengambil import SUMBER_YFINANCE
from mejasaham.unggahan_idx import SUMBER_IDX

AWAL = date(2026, 6, 1)
HARI = 20
#: Hari ke-10 = tanggal sambung; hari ke-5..9 = lima hari tumpang-tindih.
SEJAK = AWAL + timedelta(days=10)
AKHIR = AWAL + timedelta(days=HARI - 1)

MOMEN_RIWAYAT = datetime(2026, 6, 25, 18, 0, 0)
MOMEN_SAMBUNG = datetime(2026, 6, 26, 9, 0, 0)
MOMEN_IDX = datetime(2026, 6, 26, 18, 0, 0)

KODE = ("AAAA", "BBBB")
CLOSE = 1_000
#: Sesudah tanggal sambung IDX sengaja berbeda supaya terlihat bar mana yang terbaca.
CLOSE_IDX_SESUDAH = 1_100
VOLUME = 10_000_000


@pytest.fixture()
def sambungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _hari(i: int) -> date:
    return AWAL + timedelta(days=i)


def _bar(kode: str, tanggal: date, close: int, penanda: str) -> HargaHarian:
    return HargaHarian(
        kode=kode, tanggal=tanggal, close=close, volume=VOLUME, nilai=close * VOLUME,
        penyesuaian_sumber=penanda,
    )


def _riwayat(sambungan: sqlite3.Connection, *, kalender: bool = True) -> None:
    """20 hari yfinance + (bila diminta) kalender bursa yang menyatakan 20 hari itu hari bursa."""
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_YFINANCE,
            emiten=tuple(Emiten(kode=k, nama=k, sektor_idx_ic="industri", sumber="uji") for k in KODE),
            harga_harian=tuple(
                _bar(k, _hari(i), CLOSE, PENYESUAIAN_SPLIT) for k in KODE for i in range(HARI)
            ),
            kalender_bursa=(
                tuple(HariBursa(tanggal=_hari(i), hari_bursa=True) for i in range(HARI))
                if kalender
                else ()
            ),
        ),
        tanggal_data=AKHIR,
        momen=MOMEN_RIWAYAT,
    )


def _nyatakan(sambungan: sqlite3.Connection) -> None:
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber="impor berkas: uji",
            sambungan_harga=(
                SambunganHarga(berlaku_sejak=SEJAK, sumber_resmi=SUMBER_IDX, aktif=True, sumber="K97 uji"),
            ),
        ),
        tanggal_data=AKHIR,
        momen=MOMEN_SAMBUNG,
        proses=ingesti.PROSES_IMPOR,
    )


def _idx(
    sambungan: sqlite3.Connection,
    *,
    hari: Sequence[int] = range(5, HARI),
    beda: tuple[str, int] | None = None,
) -> None:
    """Bar IDX pada `hari`; sebelum tanggal sambung penutupannya sama dengan yfinance.

    `beda=(kode, i)` membuat penutupan IDX emiten itu pada hari ke-`i` berbeda satu rupiah.
    """

    def close(kode: str, i: int) -> int:
        dasar = CLOSE if _hari(i) < SEJAK else CLOSE_IDX_SESUDAH
        return dasar + 1 if beda == (kode, i) else dasar

    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_IDX,
            harga_harian=tuple(
                _bar(k, _hari(i), close(k, i), PENYESUAIAN_TIDAK_DISESUAIKAN) for k in KODE for i in hari
            ),
        ),
        tanggal_data=AKHIR,
        momen=MOMEN_IDX,
    )


# ---------------------------------------------------------------------------------------
# Gerbang (b)
# ---------------------------------------------------------------------------------------


def test_tumpang_tindih_lima_hari_yang_sama_lolos_gerbang(sambungan: sqlite3.Connection) -> None:
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan)

    bahan = potret.muat(sambungan)

    assert bahan.keadaan_sambungan is not None
    assert bahan.keadaan_sambungan.ditolak == {}
    assert bahan.keadaan_sambungan.diperiksa == len(KODE)
    assert metrik.seri_harga(bahan, "AAAA").siap


def test_penutupan_berbeda_pada_hari_tumpang_tindih_membuat_metrik_harga_tidak_dihitung(
    sambungan: sqlite3.Connection,
) -> None:
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan, beda=("AAAA", 7))

    bahan = potret.muat(sambungan)
    seri = metrik.seri_harga(bahan, "AAAA")

    assert not seri.siap
    assert "gerbang sambungan" in (seri.alasan_tak_dihitung or "")
    assert _hari(7).isoformat() in (seri.alasan_tak_dihitung or "")
    assert metrik.adtv20(seri).nilai is None, "metrik harga mengikuti deret yang ditolak"
    assert metrik.seri_harga(bahan, "BBBB").siap, "emiten lain tidak ikut ditolak"


def test_tumpang_tindih_kurang_dari_minimum_ditolak_dengan_jumlahnya(
    sambungan: sqlite3.Connection,
) -> None:
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan, hari=range(8, HARI))  # hanya hari ke-8 dan ke-9 sebelum tanggal sambung

    bahan = potret.muat(sambungan)
    alasan = metrik.seri_harga(bahan, "AAAA").alasan_tak_dihitung or ""

    assert "2 hari tumpang-tindih" in alasan
    assert str(potret.HARI_TUMPANG_TINDIH_MINIMUM) in alasan


def test_tanpa_sambungan_tidak_ada_gerbang(sambungan: sqlite3.Connection) -> None:
    _riwayat(sambungan)
    _idx(sambungan, hari=range(18, HARI))

    bahan = potret.muat(sambungan)

    assert bahan.keadaan_sambungan is None
    assert metrik.seri_harga(bahan, "AAAA").siap


# ---------------------------------------------------------------------------------------
# Hari bolong (d)
# ---------------------------------------------------------------------------------------


def test_hari_bursa_tanpa_berkas_idx_sesudah_sambung_tetap_bolong(
    sambungan: sqlite3.Connection,
) -> None:
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan, hari=[i for i in range(5, HARI) if i != 15])

    bahan = potret.muat(sambungan)
    keadaan = bahan.keadaan_sambungan

    assert keadaan is not None
    assert keadaan.hari_bolong == (_hari(15),)
    assert keadaan.bolong_di_jendela == (_hari(15),)
    assert _hari(15) not in {bar.tanggal for bar in bahan.harga["AAAA"]}, (
        "hari bolong tidak diisi dari yfinance"
    )
    assert keadaan.sementara is not None and _hari(15).isoformat() in keadaan.sementara


def test_tanpa_hari_bolong_peringkat_tidak_sementara(sambungan: sqlite3.Connection) -> None:
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan)

    keadaan = potret.muat(sambungan).keadaan_sambungan

    assert keadaan is not None
    assert keadaan.hari_bolong == ()
    assert keadaan.sementara is None


def test_kalender_yang_belum_memuat_rentang_sambung_membuat_peringkat_sementara(
    sambungan: sqlite3.Connection,
) -> None:
    _riwayat(sambungan, kalender=False)
    _nyatakan(sambungan)
    _idx(sambungan)

    keadaan = potret.muat(sambungan).keadaan_sambungan

    assert keadaan is not None
    assert keadaan.kalender_kurang is not None
    assert keadaan.sementara is not None and "kalender" in keadaan.sementara


def test_jendela_hari_bolong_mencakup_jendela_metrik_terpanjang() -> None:
    assert potret.JENDELA_BOLONG_HARI_BURSA >= metrik.HARI_12_BULAN
    assert potret.JENDELA_BOLONG_HARI_BURSA >= metrik.MA_PANJANG


# ---------------------------------------------------------------------------------------
# Yang melihatnya: laporan mutu dan laporan saring
# ---------------------------------------------------------------------------------------


def test_laporan_mutu_menyebut_gerbang_dan_hari_bolong(sambungan: sqlite3.Connection) -> None:
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan, hari=[i for i in range(5, HARI) if i != 15], beda=("AAAA", 7))

    laporan = mutu.periksa(
        sambungan, tanggal_data=AKHIR, sumber=potret.harga_dipakai(sambungan), momen=AKHIR
    )
    jenis = {(satu.kode, satu.jenis): satu for satu in laporan.temuan}

    assert ("AAAA", "sambungan_beda_harga") in jenis
    assert jenis[("AAAA", "sambungan_beda_harga")].tingkat == mutu.TAK_WAJAR
    assert "AAAA" in laporan.dikeluarkan
    assert ("-", "hari_bolong_sambungan") in jenis
    assert _hari(15).isoformat() in jenis[("-", "hari_bolong_sambungan")].keterangan


def test_laporan_saring_berstatus_peringkat_sementara_selama_ada_hari_bolong(
    sambungan: sqlite3.Connection,
) -> None:
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan, hari=[i for i in range(5, HARI) if i != 15])
    pengatur.siapkan_preset_bawaan(sambungan, date(2026, 7, 1))

    laporan = pengatur.jalankan_saring(
        sambungan, pengatur.saring.preset_terbaru(sambungan, "kualitas-nilai"), simpan=False
    )

    assert laporan.peringkat_sementara
    assert laporan.sambungan_sementara is not None
    assert any("PERINGKAT SEMENTARA" in satu and "bolong" in satu for satu in laporan.peringatan)


def test_hari_tumpang_tindih_hanya_dicari_dalam_jendela_sebelum_tanggal_sambung(
    sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bukti sambungan = hari tepat sebelum tanggal sambung; bar resmi yang jauh lebih awal tidak dihitung."""
    _riwayat(sambungan)
    _nyatakan(sambungan)
    _idx(sambungan)  # hari ke-5..9 cocok
    monkeypatch.setattr(potret, "JENDELA_TUMPANG_TINDIH_HARI", 3)  # hanya hari ke-7..9

    alasan = metrik.seri_harga(potret.muat(sambungan), "AAAA").alasan_tak_dihitung or ""

    assert "hanya 3 hari tumpang-tindih" in alasan
