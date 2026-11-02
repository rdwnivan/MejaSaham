"""Uji ekspor F9: metadata point-in-time, format Excel Indonesia, dan tanpa timpa."""

from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from mejasaham import arsip, cli, db, ekspor, lokasi, saring


@pytest.fixture()
def sambungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> sqlite3.Connection:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    koneksi = db.siapkan()
    koneksi.execute(
        "INSERT INTO snapshot (id_snapshot, tanggal_data, batas_diketahui, jam_ambil, jumlah_emiten,"
        " jumlah_gagal, versi_skema, versi_aplikasi, catatan)"
        " VALUES (1, '2026-10-09', '2026-10-09T18:00:00+07:00',"
        " '2026-10-09T18:00:00+07:00', 1, 0, 14, '0.1.0', NULL)"
    )
    preset = saring.preset_bawaan(date(2026, 10, 9))[0]
    saring.simpan_preset(koneksi, preset)
    koneksi.execute(
        "INSERT INTO skor (kode, id_snapshot, id_preset, skor_kualitas_bp, skor_nilai_bp,"
        " skor_momentum_bp, skor_volatilitas_bp, skor_total_bp, peringkat, dihitung_pada,"
        " versi_hitung, penjelasan) VALUES ('AAAA', 1, ?, 7000, 6000, 5000, 4000, 6000, 1,"
        " '2026-10-09T18:01:00+07:00', 'uji', 'skor uji')",
        (preset.id_preset,),
    )
    try:
        yield koneksi
    finally:
        koneksi.close()


def _baca_csv(jalur: Path) -> list[list[str]]:
    return list(csv.reader(jalur.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))


def test_hasil_saring_memuat_kepala_ac7_dan_csv_excel(sambungan: sqlite3.Connection, tmp_path: Path) -> None:
    tujuan = tmp_path / "hasil.csv"
    hasil = ekspor.ekspor(sambungan, "hasil-saring", tujuan)

    isi = tujuan.read_bytes()
    assert isi.startswith(b"\xef\xbb\xbf")
    teks = isi.decode("utf-8-sig")
    assert "# id_snapshot;1" in teks
    assert "# id_preset;kualitas-nilai/v1" in teks
    assert "# versi_preset;1" in teks
    assert ekspor.PERNYATAAN_BUKAN_NASIAT in teks
    baris = _baca_csv(tujuan)
    assert baris[-2][0] == "kode"
    assert baris[-1][0] == "AAAA"
    assert hasil.jumlah_baris == 1


def test_ekspor_memberi_peringatan_sumber_yfinance(
    sambungan: sqlite3.Connection, tmp_path: Path
) -> None:
    sambungan.execute(
        "INSERT INTO harga_harian (kode, tanggal, sumber, diketahui_pada)"
        " VALUES ('AAAA', '2026-10-09', 'yfinance/Yahoo Finance (tidak resmi)',"
        " '2026-10-09T18:00:00+07:00')"
    )

    tujuan = tmp_path / "hasil.csv"
    ekspor.ekspor(sambungan, "hasil-saring", tujuan)
    teks = tujuan.read_text(encoding="utf-8-sig")
    assert "# sumber_harga;yfinance/Yahoo Finance (tidak resmi)" in teks
    assert "# PERINGATAN;" in teks
    assert "JANGAN disebarkan" in teks


@pytest.mark.parametrize("jenis", ("watchlist", "rencana", "jurnal"))
def test_ekspor_laporan_operasional_bisa_kosong(
    sambungan: sqlite3.Connection, tmp_path: Path, jenis: str
) -> None:
    hasil = ekspor.ekspor(sambungan, jenis, tmp_path / f"{jenis}.csv")
    assert hasil.jumlah_baris == 0
    assert hasil.id_snapshot == 1


def test_mutu_diekspor_dari_arsip_snapshot_terkait(
    sambungan: sqlite3.Connection, tmp_path: Path
) -> None:
    folder = arsip.folder_arsip(date(2026, 10, 9), 1)
    folder.mkdir(parents=True)
    (folder / arsip.NAMA_MUTU).write_text(
        "# laporan mutu data Meja Saham\n"
        "# snapshot;2026-10-09\n"
        "tingkat;jenis;kode;keterangan\n"
        "catatan;kalender;AAAA;contoh\n",
        encoding="utf-8-sig",
    )

    tujuan = tmp_path / "mutu.csv"
    hasil = ekspor.ekspor(sambungan, "mutu", tujuan)
    teks = tujuan.read_text(encoding="utf-8-sig")
    assert "# id_snapshot;1" in teks
    assert "# versi_preset;1" in teks
    assert "catatan;kalender;AAAA;contoh" in teks
    assert hasil.jumlah_baris == 1


def test_tujuan_yang_sudah_ada_tidak_ditimpa(sambungan: sqlite3.Connection, tmp_path: Path) -> None:
    tujuan = tmp_path / "lama.csv"
    tujuan.write_text("ekspor lama", encoding="utf-8")

    with pytest.raises(ekspor.GalatEkspor, match="sudah ada"):
        ekspor.ekspor(sambungan, "hasil-saring", tujuan)

    assert tujuan.read_text(encoding="utf-8") == "ekspor lama"


def test_perintah_cli_menulis_ekspor(sambungan: sqlite3.Connection, tmp_path: Path) -> None:
    tujuan = tmp_path / "cli.csv"

    kode = cli.main(["--ekspor", "hasil-saring", "--keluaran", str(tujuan)])

    assert kode == cli.KODE_OK
    assert "# id_snapshot;1" in tujuan.read_text(encoding="utf-8-sig")
