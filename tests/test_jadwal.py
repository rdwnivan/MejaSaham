"""Pelacak jadwal pembaruan data (U36 → K93)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest

from mejasaham import db, ingesti, jadwal, lokasi, notasi, pengatur, pengingat
from mejasaham.ingesti import Emiten, HargaHarian, HariBursa, KumpulanData, NotasiKhusus

HARI_INI = date(2026, 10, 28)


@pytest.fixture()
def sambungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _simpan(sambungan: sqlite3.Connection, tanggal_data: date, momen: datetime, **isi: object) -> None:
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber="uji", **isi),  # type: ignore[arg-type]
        tanggal_data=tanggal_data,
        momen=momen,
    )


def _butir(sambungan: sqlite3.Connection, nama: str, hari_ini: date = HARI_INI) -> jadwal.Butir:
    return next(satu for satu in jadwal.susun(sambungan, hari_ini) if satu.nama.startswith(nama))


def _papan(per: date) -> NotasiKhusus:
    return NotasiKhusus(
        kode="AAAA",
        jenis="papan_pemantauan",
        tanggal_mulai=per,
        keterangan=f"notasi X; {notasi.PENANDA_BARIS} {per.isoformat()} (tanggal data halaman)",
    )


def test_basis_data_kosong_menyebut_semua_data_wajib_jatuh_tempo(sambungan: sqlite3.Connection) -> None:
    status = {satu.nama: satu.status for satu in jadwal.susun(sambungan, HARI_INI)}
    assert status["Harga harian & indeks"] == jadwal.JATUH_TEMPO
    assert status["Notasi khusus & papan pemantauan (IDX)"] == jadwal.JATUH_TEMPO
    # P43: suspensi/UMA belum punya jalur unggah, jadi kesegarannya tidak bisa dibuktikan.
    assert status["Suspensi & UMA (IDX)"] == jadwal.TIDAK_DINILAI
    assert status["Kalender bursa (KSEI)"] == jadwal.JATUH_TEMPO
    assert status["Daftar emiten (Master File KSEI)"] == jadwal.JATUH_TEMPO
    assert status["Cek sumber kedua (PRD 7.3)"] == jadwal.JATUH_TEMPO
    # Yang jadwalnya belum bisa dihitung tidak dikarang menjadi terbaru atau jatuh tempo.
    assert status["Imbal hasil SUN 10 tahun (PHEI)"] == jadwal.TIDAK_DINILAI
    assert status["Fundamental emiten"] == jadwal.TIDAK_DINILAI


def test_harga_terbaru_hanya_bila_snapshot_dari_hari_bursa_terakhir(sambungan: sqlite3.Connection) -> None:
    kalender = tuple(HariBursa(tanggal=date(2026, 10, d), hari_bursa=True) for d in (27, 28))
    harga = (HargaHarian(kode="AAAA", tanggal=date(2026, 10, 27), close=1000, volume=1),)
    _simpan(sambungan, date(2026, 10, 27), datetime(2026, 10, 27, 18), kalender_bursa=kalender, harga_harian=harga)
    assert _butir(sambungan, "Harga").status == jadwal.JATUH_TEMPO
    assert "tombol" in _butir(sambungan, "Harga").tindakan
    assert _butir(sambungan, "Harga", date(2026, 10, 27)).status == jadwal.TERBARU


def _skor(sambungan: sqlite3.Connection, id_snapshot: int) -> None:
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO skor (kode, id_snapshot, id_preset, skor_total_bp, peringkat,"
            " dihitung_pada, versi_hitung, penjelasan)"
            " VALUES ('AAAA', ?, 'kualitas-nilai/v1', 5000, 1, '2026-10-28T19:00:00+07:00', 'uji', 'uji')",
            (id_snapshot,),
        )


def test_snapshot_baru_tanpa_skor_membuat_saringan_jatuh_tempo(sambungan: sqlite3.Connection) -> None:
    """Impor Ringkasan Saham membuat snapshot baru tanpa menyaring ulang; tanpa butir ini dasbor
    hanya kosong kandidatnya dan pengguna tidak diberi tahu sebabnya (29 Okt 2026)."""
    pengatur.siapkan_preset_bawaan(sambungan)
    harga = (HargaHarian(kode="AAAA", tanggal=date(2026, 10, 27), close=1000, volume=1),)
    _simpan(sambungan, date(2026, 10, 27), datetime(2026, 10, 27, 18), harga_harian=harga)
    _skor(sambungan, 1)
    assert _butir(sambungan, "Saringan").status == jadwal.TERBARU

    harga = (HargaHarian(kode="AAAA", tanggal=date(2026, 10, 28), close=1010, volume=1),)
    _simpan(sambungan, HARI_INI, datetime(2026, 10, 28, 18), harga_harian=harga)
    butir = _butir(sambungan, "Saringan")
    assert butir.status == jadwal.JATUH_TEMPO
    assert "snapshot #2" in butir.bukti and "skor terakhir dari snapshot #1" in butir.bukti
    assert "Jalankan saringan" in butir.tindakan
    assert butir in pengingat.saat_dibuka(jadwal.susun(sambungan, HARI_INI))

    _skor(sambungan, 2)
    assert _butir(sambungan, "Saringan").status == jadwal.TERBARU


def test_saringan_tanpa_snapshot_tidak_dinilai(sambungan: sqlite3.Connection) -> None:
    assert _butir(sambungan, "Saringan").status == jadwal.TIDAK_DINILAI


@pytest.mark.parametrize(("umur", "status"), [(7, jadwal.TERBARU), (8, jadwal.JATUH_TEMPO)])
def test_notasi_mingguan_dinilai_dari_tanggal_daftar_resmi_inklusif_tujuh_hari(
    sambungan: sqlite3.Connection, umur: int, status: str
) -> None:
    per = date(2026, 10, 28 - umur)
    _simpan(sambungan, per, datetime(2026, 10, 28, 18), notasi_khusus=(_papan(per),))
    assert _butir(sambungan, "Notasi khusus").status == status


def test_waktu_tulis_baru_tidak_membuat_notasi_lama_terlihat_terbaru(sambungan: sqlite3.Connection) -> None:
    """K93 aturan 2: `--refresh` menulis ulang baris dari berkas konfigurasi setiap hari, jadi
    `diketahui_pada` hari ini tidak membuktikan bahwa daftar resminya juga dari hari ini."""
    lama = date(2026, 10, 9)
    _simpan(sambungan, HARI_INI, datetime(2026, 10, 28, 18, 51), notasi_khusus=(_papan(lama),))
    butir = _butir(sambungan, "Notasi khusus")
    assert butir.status == jadwal.JATUH_TEMPO
    assert "09 Okt 2026" in butir.bukti and "Impor & cadangan" in butir.tindakan
    assert "--ambil-notasi" not in butir.tindakan, "K96: jadwal tidak menawarkan scraping IDX"


def test_notasi_tanpa_tanggal_daftar_resmi_tidak_dinilai(sambungan: sqlite3.Connection) -> None:
    baris = NotasiKhusus(kode="AAAA", jenis=notasi.JENIS_LAINNYA, tanggal_mulai=date(2026, 10, 1))
    _simpan(sambungan, HARI_INI, datetime(2026, 10, 28, 18), notasi_khusus=(baris,))
    assert _butir(sambungan, "Notasi khusus").status == jadwal.TIDAK_DINILAI


def test_daftar_notasi_terbaru_tidak_membuat_suspensi_uma_terlihat_terbaru(sambungan: sqlite3.Connection) -> None:
    """P43: daftar Notasi Khusus yang diunggah tidak memuat suspensi/UMA, jadi tanggalnya bukan
    bukti bahwa suspensi/UMA juga diperbarui."""
    suspensi = NotasiKhusus(
        kode="BBBB", jenis="suspensi", tanggal_mulai=date(2026, 10, 20),
        keterangan=f"{notasi.PENANDA_AKTIVITAS}; Peng-SPT",
    )
    _simpan(sambungan, HARI_INI, datetime(2026, 10, 28, 18), notasi_khusus=(_papan(HARI_INI), suspensi))
    assert _butir(sambungan, "Notasi khusus").status == jadwal.TERBARU
    butir = _butir(sambungan, "Suspensi & UMA")
    assert butir.status == jadwal.TIDAK_DINILAI
    assert "1 suspensi" in butir.bukti and "20 Okt 2026" in butir.bukti
    assert "idx.co.id" in butir.tindakan and "--ambil-notasi" not in butir.tindakan
    assert "suspensi" not in _butir(sambungan, "Notasi khusus").tindakan


@pytest.mark.parametrize(
    ("label", "status"),
    [
        ("Master File Efek KSEI 30 Sep 2026 (StatisEfek20260930.txt.zip)", jadwal.TERBARU),
        ("Master File Efek KSEI 31 Agu 2026 (StatisEfek20260831.txt.zip)", jadwal.JATUH_TEMPO),
        ("diisi tangan", jadwal.TIDAK_DINILAI),
    ],
)
def test_daftar_emiten_bulanan_dari_tanggal_master_file_di_label(
    sambungan: sqlite3.Connection, label: str, status: str
) -> None:
    _simpan(
        sambungan, HARI_INI, datetime(2026, 10, 28, 18),
        emiten=(Emiten(kode="AAAA", nama="Alpha", sumber=label),),
    )
    assert _butir(sambungan, "Daftar emiten").status == status


def test_kalender_tanpa_tahun_berjalan_jatuh_tempo(sambungan: sqlite3.Connection) -> None:
    _simpan(
        sambungan, date(2025, 12, 30), datetime(2026, 10, 28, 18),
        kalender_bursa=(HariBursa(tanggal=date(2025, 12, 30), hari_bursa=True),),
    )
    assert _butir(sambungan, "Kalender").status == jadwal.JATUH_TEMPO
    assert _butir(sambungan, "Kalender", date(2025, 12, 30)).status == jadwal.TERBARU


def test_ringkas_menyebut_tindakan_hanya_untuk_yang_belum_terbaru(sambungan: sqlite3.Connection) -> None:
    teks = jadwal.ringkas(jadwal.susun(sambungan, HARI_INI))
    assert "tidak ada yang dijalankan otomatis" in teks
    assert "tindakan: --ambil-kalender" in teks


def test_tabel_layar_tidak_menawarkan_tindakan_untuk_yang_terbaru() -> None:
    from mejasaham.layar import tabel

    isi = tabel.isi_jadwal(
        (
            jadwal.Butir("A", "harian", jadwal.TERBARU, "bukti", "jangan tampil"),
            jadwal.Butir("B", "harian", jadwal.JATUH_TEMPO, "bukti", "--refresh"),
        )
    )
    assert [baris[-1] for baris in isi] == ["", "--refresh"]
    assert len(tabel.kepala_jadwal()) == len(isi[0])


def test_sesudah_tanggal_sambung_harga_jatuh_tempo_bila_berkas_idx_hari_bursa_belum_diunggah(
    sambungan: sqlite3.Connection,
) -> None:
    """K97 d: sejak tanggal sambung, harga harian baru lengkap bila Ringkasan Saham IDX hari itu
    sudah diimpor — snapshot yfinance yang terbaru saja tidak cukup."""
    from mejasaham.ingesti import SambunganHarga
    from mejasaham.unggahan_idx import SUMBER_IDX

    hari = tuple(date(2026, 10, d) for d in (26, 27, 28))
    _simpan(
        sambungan, hari[-1], datetime(2026, 10, 28, 18),
        kalender_bursa=tuple(HariBursa(tanggal=satu, hari_bursa=True) for satu in hari),
        harga_harian=tuple(HargaHarian(kode="AAAA", tanggal=satu, close=1000, volume=1) for satu in hari),
    )
    _simpan(
        sambungan, hari[-1], datetime(2026, 10, 28, 19),
        sambungan_harga=(SambunganHarga(berlaku_sejak=hari[1], sumber_resmi=SUMBER_IDX, aktif=True, sumber="uji"),),
    )

    def idx(tanggal: date, momen: datetime) -> None:
        ingesti.simpan(
            sambungan,
            KumpulanData(
                sumber=SUMBER_IDX,
                harga_harian=(HargaHarian(kode="AAAA", tanggal=tanggal, close=1000, volume=1),),
            ),
            tanggal_data=hari[-1],
            momen=momen,
        )

    idx(hari[1], datetime(2026, 10, 28, 20))
    butir = _butir(sambungan, "Harga")
    assert butir.status == jadwal.JATUH_TEMPO
    assert "2026-10-28" in butir.bukti
    assert "Ringkasan Saham" in butir.tindakan
    # Uji regresi (sesi 69): label resmi sudah memuat "Ringkasan Saham"; dulu tertulis dua kali.
    assert butir.jadwal == f"tiap hari bursa — {SUMBER_IDX} sejak 27 Okt 2026 (K97)"

    idx(hari[2], datetime(2026, 10, 28, 21))
    assert _butir(sambungan, "Harga").status == jadwal.TERBARU


def test_cek_sumber_kedua_terakhir_bertanggal_indonesia(sambungan: sqlite3.Connection) -> None:
    """Uji regresi (sesi 69): buktinya menulis `2026-10-29T19:01:32+07:00` (AGENTS §4)."""
    from decimal import Decimal

    from mejasaham import mutu

    laporan = mutu.LaporanPerbandingan(
        tanggal_data="2026-10-27",
        sumber_utama="uji",
        sumber_pembanding="uji lain",
        diperiksa=(mutu.BedaSumber("AAAA", "2026-10-27", 1000, 1000, Decimal("0")),),
        belum_dapat_dijalankan=[],
    )
    mutu.catat_cek_sumber_kedua(sambungan, laporan, momen=datetime(2026, 10, 27, 19, 1, 32))

    butir = _butir(sambungan, "Cek sumber kedua")
    assert butir.status == jadwal.TERBARU
    assert butir.bukti == "cek lengkap terakhir 27 Okt 2026, 1 hari lalu"
