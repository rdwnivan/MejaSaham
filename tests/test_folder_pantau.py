"""Folder pantau (K101) dan pengingat unduhan IDX (K102).

Pengunduhan tetap manual (K95/K96); yang diuji di sini adalah langkah sesudahnya: berkas di folder
pantau dikenali dari namanya, diimpor lewat jalur yang sama dengan unggahan dasbor, lalu
dipindah — dan yang gagal tetap di tempatnya dengan sebab yang terlihat.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from mejasaham import (
    cli,
    db,
    folder_pantau,
    ingesti,
    jadwal,
    lokasi,
    notasi,
    pengingat,
    pengumuman_idx,
    tampilan,
    unggahan_idx,
)
from mejasaham.ingesti import HariBursa, KumpulanData
from mejasaham.layar import tulis

# Pembuat berkas tiruan yang sama dengan uji pembacanya, supaya bentuknya tidak bercabang.
from tests.test_notasi_unduhan import BARIS_CONTOH, _xlsx as _xlsx_notasi
from tests.test_pengumuman_idx import _suspensi, _uma
from tests.test_unggahan_idx import _baris_idx, _snapshot, _xlsx

HARI_INI = date(2026, 10, 29)


@pytest.fixture()
def sambungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    monkeypatch.delenv(folder_pantau.ENV_FOLDER_PANTAU, raising=False)
    koneksi = db.siapkan()
    lokasi.pastikan_folder(lokasi.folder_konfigurasi())
    try:
        yield koneksi
    finally:
        koneksi.close()


@pytest.fixture()
def pantau(tmp_path: Path) -> Path:
    folder = tmp_path / "Unduhan"
    folder.mkdir()
    return folder


def _ringkasan(folder: Path, hari: date, nama: str | None = None) -> Path:
    teks = f"{hari.day:02d} {tampilan.BULAN_SINGKAT[hari.month - 1]} {hari.year}"
    jalur = folder / (nama or f"Ringkasan Saham-{hari:%Y%m%d}.xlsx")
    jalur.write_bytes(_xlsx([_baris_idx("AADI", **{"Tanggal Perdagangan Terakhir": teks})]))
    return jalur


def _jalankan(sambungan: sqlite3.Connection, folder: Path, tmp_path: Path) -> tulis.HasilTulis:
    permintaan = tulis.permintaan_impor_folder_pantau(
        sambungan, folder=folder, hari_ini=HARI_INI, tujuan_cadangan=tmp_path / "cadangan"
    )
    return tulis.jalankan_permintaan(permintaan, sambungan)


def _jumlah_snapshot(sambungan: sqlite3.Connection) -> int:
    return sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0]


# ---------------------------------------------------------------------------------------
# Pengenalan berkas
# ---------------------------------------------------------------------------------------


def test_folder_pantau_mati_bila_tidak_diatur(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(folder_pantau.ENV_FOLDER_PANTAU, raising=False)
    assert folder_pantau.folder() is None
    monkeypatch.setenv(folder_pantau.ENV_FOLDER_PANTAU, str(tmp_path))
    assert folder_pantau.folder() == tmp_path
    assert folder_pantau.folder(tmp_path / "lain") == tmp_path / "lain", "isian eksplisit menang"


def test_pindai_mengenali_nama_unduhan_idx_dan_tidak_menyentuh_berkas_lain(pantau: Path) -> None:
    _ringkasan(pantau, date(2026, 10, 28), "Ringkasan Saham-20261028 (1).xlsx")
    (pantau / "Notasi Khusus-20261027.xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH))
    (pantau / "20261028-UMA_COIN.pdf").write_bytes(_uma())
    (pantau / "Ringkasan Saham-20261027.xlsx").write_bytes(b"bukan xlsx")
    (pantau / "laporan-bank.pdf").write_bytes(b"%PDF lain")
    (pantau / "foto.jpg").write_bytes(b"x")
    (pantau / "Ringkasan Saham-20261029.xlsx.crdownload").write_bytes(b"setengah")

    hasil = folder_pantau.pindai(pantau)

    assert [(jalur.name, hari) for jalur, hari in hasil.ringkasan] == [
        ("Ringkasan Saham-20261028 (1).xlsx", date(2026, 10, 28))
    ]
    assert [(jalur.name, hari) for jalur, hari in hasil.notasi] == [
        ("Notasi Khusus-20261027.xlsx", date(2026, 10, 27))
    ]
    assert [jalur.name for jalur in hasil.pengumuman] == ["20261028-UMA_COIN.pdf"]
    assert [jalur.name for jalur, _ in hasil.ditolak] == ["Ringkasan Saham-20261027.xlsx"]
    assert "DITOLAK Ringkasan Saham-20261027.xlsx" in hasil.ringkas()


def test_folder_pantau_yang_tidak_ada_ditolak_dengan_sebabnya(
    sambungan: sqlite3.Connection, tmp_path: Path
) -> None:
    with pytest.raises(tulis.GalatTulis, match="tidak ada atau bukan folder"):
        tulis.permintaan_impor_folder_pantau(sambungan, folder=tmp_path / "tidak-ada")


# ---------------------------------------------------------------------------------------
# Impor
# ---------------------------------------------------------------------------------------


def test_tiga_jenis_diimpor_lalu_dipindah_dan_cadangan_dibuat_lebih_dulu(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    _ringkasan(pantau, date(2026, 10, 28))
    (pantau / "Notasi Khusus-20261027.xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH))
    (pantau / "20261028-UMA_COIN.pdf").write_bytes(_uma())
    (pantau / "foto.jpg").write_bytes(b"x")

    hasil = _jalankan(sambungan, pantau, tmp_path)

    assert hasil.berhasil, hasil.pesan
    assert sorted(satu.name for satu in pantau.iterdir()) == ["foto.jpg"], "berkas lain tidak disentuh"
    assert list((tmp_path / "cadangan").iterdir()), "cadangan dibuat sebelum impor"
    assert hasil.pesan.index("Cadangan dibuat") < hasil.pesan.index("== Ringkasan Saham ==")
    assert hasil.pesan.index("== Ringkasan Saham ==") < hasil.pesan.index("== Notasi Khusus ==")
    assert hasil.pesan.index("== Notasi Khusus ==") < hasil.pesan.index("== PDF pengumuman ==")

    idx = sambungan.execute(
        "SELECT COUNT(*) FROM harga_harian WHERE sumber = ? AND tanggal = '2026-10-28'",
        (unggahan_idx.SUMBER_IDX,),
    ).fetchone()[0]
    assert idx == 1
    jenis = {
        tuple(satu)
        for satu in sambungan.execute("SELECT kode, jenis FROM v_notasi_khusus_terkini")
    }
    assert ("COIN", "uma") in jenis
    assert any(kode == "WEGE" for kode, _ in jenis), "daftar Notasi Khusus ikut diimpor"

    # Bukti asal baris tetap ada: berkas mentah disalin ke unduhan-idx/.
    assert [satu.nama_asli for satu in unggahan_idx.daftar()] == ["Ringkasan Saham-20261028.xlsx"]
    assert any(p.name.endswith("Notasi_Khusus-20261027.xlsx") for p in notasi.folder_unduhan().iterdir())
    assert any(p.name.endswith("20261028-UMA_COIN.pdf") for p in pengumuman_idx.folder_unduhan().iterdir())


def test_folder_kosong_tidak_membuat_cadangan_maupun_snapshot(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    sebelum = _jumlah_snapshot(sambungan)

    hasil = _jalankan(sambungan, pantau, tmp_path)

    assert hasil.berhasil, hasil.pesan
    assert "tidak ada berkas IDX yang dikenali" in hasil.pesan
    assert not (tmp_path / "cadangan").exists()
    assert _jumlah_snapshot(sambungan) == sebelum


def test_ringkasan_sesudah_snapshot_menunggu_di_folder_tanpa_dianggap_gagal(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    berkas = _ringkasan(pantau, date(2026, 10, 29))
    sebelum = _jumlah_snapshot(sambungan)

    permintaan = tulis.permintaan_impor_folder_pantau(sambungan, folder=pantau, hari_ini=HARI_INI)
    assert "sesudah snapshot terakhir" in permintaan.ringkasan
    hasil = tulis.jalankan_permintaan(permintaan, sambungan)

    assert hasil.berhasil, hasil.pesan
    assert berkas.exists()
    assert "menunggu snapshot" in hasil.pesan
    assert _jumlah_snapshot(sambungan) == sebelum
    assert not (tmp_path / "cadangan").exists(), "tidak ada impor, tidak ada cadangan"


def test_tanggal_yang_sudah_diimpor_dipindah_tanpa_impor_ulang(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    _ringkasan(pantau, date(2026, 10, 28))
    assert _jalankan(sambungan, pantau, tmp_path).berhasil
    sebelum = _jumlah_snapshot(sambungan)

    # Diunduh lagi (peramban menambah " (1)").
    _ringkasan(pantau, date(2026, 10, 28), "Ringkasan Saham-20261028 (1).xlsx")
    hasil = _jalankan(sambungan, pantau, tmp_path)

    assert hasil.berhasil, hasil.pesan
    assert "sudah ada di basis data" in hasil.pesan
    assert not list(pantau.iterdir())
    assert _jumlah_snapshot(sambungan) == sebelum


def test_dua_ringkasan_bertanggal_sama_tidak_ditebak_dan_jalannya_berisik(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    _ringkasan(pantau, date(2026, 10, 28))
    _ringkasan(pantau, date(2026, 10, 28), "Ringkasan Saham-20261028 (1).xlsx")

    hasil = _jalankan(sambungan, pantau, tmp_path)

    assert hasil.berhasil is False
    assert "tanggal kembar" in hasil.pesan
    assert len(list(pantau.iterdir())) == 2


def test_pdf_yang_ditolak_tetap_di_folder_sedangkan_langkah_sebelumnya_selesai(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    (pantau / "Notasi Khusus-20261027.xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH))
    (pantau / "20261028-WAS_Suspensi_PTSP.pdf").write_bytes(_suspensi(kode_lain="ABCD"))

    hasil = _jalankan(sambungan, pantau, tmp_path)

    assert hasil.berhasil is False
    assert "lebih dari satu kode" in hasil.pesan
    assert [satu.name for satu in pantau.iterdir()] == ["20261028-WAS_Suspensi_PTSP.pdf"]
    assert "Berkas yang belum selesai tetap di folder pantau" in hasil.pesan


def test_notasi_yang_tidak_lebih_baru_dari_daftar_tersimpan_tidak_diimpor(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    (pantau / "Notasi Khusus-20261027.xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH))
    assert _jalankan(sambungan, pantau, tmp_path).berhasil
    sebelum = _jumlah_snapshot(sambungan)

    (pantau / "Notasi Khusus-20261020.xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH[:1]))
    (pantau / "Notasi Khusus-20261027 (1).xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH))
    hasil = _jalankan(sambungan, pantau, tmp_path)

    assert hasil.berhasil, hasil.pesan
    assert "Notasi Khusus tidak diimpor" in hasil.pesan
    assert not list(pantau.iterdir())
    assert _jumlah_snapshot(sambungan) == sebelum, "daftar lama tidak boleh menutup notasi yang berlaku"


def test_berkas_yang_isinya_sudah_diimpor_tidak_dihitung_belum_diimpor(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    """Sesi 66: Ringkasan Saham yang sudah diimpor lewat unggahan dasbor tetap di Unduhan, dan
    kotak "Perlu diperbarui" menyebutnya "belum diimpor". Yang dihitung hanya isi yang belum ada."""
    _snapshot(sambungan, date(2026, 10, 28))
    _ringkasan(pantau, date(2026, 10, 28))
    (pantau / "Notasi Khusus-20261027.xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH))
    assert tulis.jumlah_belum_diimpor(sambungan, folder_pantau.pindai(pantau)) == 2
    assert _jalankan(sambungan, pantau, tmp_path).berhasil

    _ringkasan(pantau, date(2026, 10, 28))  # diunduh lagi sesudah diimpor
    (pantau / "Notasi Khusus-20261027.xlsx").write_bytes(_xlsx_notasi(BARIS_CONTOH))
    assert tulis.jumlah_belum_diimpor(sambungan, folder_pantau.pindai(pantau)) == 0

    _ringkasan(pantau, date(2026, 10, 29))  # sesudah snapshot terakhir: masih harus diimpor
    assert tulis.jumlah_belum_diimpor(sambungan, folder_pantau.pindai(pantau)) == 1


def test_tiap_jalan_dicatat_di_log_jalan_dan_yang_berhasil_menggantikan_yang_gagal(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    """AC-9: jalan dari Task Scheduler tidak punya penonton, jadi hasilnya harus ada di basis data."""
    _snapshot(sambungan, date(2026, 10, 28))
    assert folder_pantau.jalan_terakhir(sambungan) is None
    ditolak = pantau / "Ringkasan Saham-20261027.xlsx"
    ditolak.write_bytes(b"bukan xlsx")

    assert _jalankan(sambungan, pantau, tmp_path).berhasil is False
    jalan = folder_pantau.jalan_terakhir(sambungan)
    assert jalan is not None and jalan.berhasil is False
    assert "ditolak: Ringkasan Saham-20261027.xlsx" in jalan.pesan

    ditolak.unlink()
    _ringkasan(pantau, date(2026, 10, 28))
    assert _jalankan(sambungan, pantau, tmp_path).berhasil
    jalan = folder_pantau.jalan_terakhir(sambungan)
    assert jalan is not None and jalan.berhasil
    assert "== Ringkasan Saham ==" in jalan.pesan


def test_kunci_tulis_proses_lain_menggagalkan_tanpa_memindah_berkas(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path
) -> None:
    """AC-19: dasbor yang sedang menulis tidak ditunggu diam-diam; berkasnya tetap di folder."""
    _snapshot(sambungan, date(2026, 10, 28))
    berkas = _ringkasan(pantau, date(2026, 10, 28))
    sambungan.execute("PRAGMA busy_timeout=50")
    penulis_lain = db.hubungkan(lokasi.folder_data() / lokasi.NAMA_BERKAS_BASIS_DATA)
    penulis_lain.execute("PRAGMA busy_timeout=0")
    try:
        penulis_lain.execute("BEGIN IMMEDIATE")
        hasil = _jalankan(sambungan, pantau, tmp_path)
        penulis_lain.execute("ROLLBACK")
    finally:
        penulis_lain.close()

    assert hasil.berhasil is False
    assert db.KALIMAT_TERKUNCI in hasil.pesan
    assert "jejak jalan ini tidak tercatat di log_jalan" in hasil.pesan, "kunci juga menahan jejaknya"
    assert berkas.exists()


# ---------------------------------------------------------------------------------------
# Baris perintah
# ---------------------------------------------------------------------------------------


def test_impor_unduhan_tanpa_folder_pantau_gagal_berisik(
    sambungan: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["--impor-unduhan"]) == cli.KODE_GAGAL
    assert folder_pantau.ENV_FOLDER_PANTAU in capsys.readouterr().err
    jalan = folder_pantau.jalan_terakhir(sambungan)
    assert jalan is not None and jalan.berhasil is False, "kegagalan sebelum impor tetap tercatat"
    assert folder_pantau.ENV_FOLDER_PANTAU in jalan.pesan


def test_impor_unduhan_tidak_digabung_dengan_refresh(
    sambungan: sqlite3.Connection, pantau: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["--refresh", "--impor-unduhan", "--folder-pantau", str(pantau)]) == cli.KODE_GAGAL
    assert "urutan harian" in capsys.readouterr().err


def test_impor_unduhan_dari_baris_perintah(
    sambungan: sqlite3.Connection, pantau: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    _ringkasan(pantau, date(2026, 10, 28))

    kode = cli.main(
        ["--impor-unduhan", "--folder-pantau", str(pantau), "--folder-cadangan", str(tmp_path / "cad")]
    )

    keluaran = capsys.readouterr()
    assert kode == cli.KODE_OK, keluaran.err
    assert "== Ringkasan Saham ==" in keluaran.out
    assert not list(pantau.iterdir())


# ---------------------------------------------------------------------------------------
# Pengingat (K102)
# ---------------------------------------------------------------------------------------


def _hari(sambungan: sqlite3.Connection, hari: date, *, bursa: bool) -> None:
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber="uji", kalender_bursa=(HariBursa(tanggal=hari, hari_bursa=bursa),)),
        tanggal_data=hari,
    )


def test_pengingat_memuat_butir_idx_yang_belum_terbaru_beserta_tautannya(
    sambungan: sqlite3.Connection,
) -> None:
    _hari(sambungan, HARI_INI, bursa=True)

    daftar = pengingat.susun(sambungan, HARI_INI)

    nama = {satu.nama: satu.alamat for satu in daftar}
    assert nama["Notasi khusus & papan pemantauan (IDX)"] == notasi.ALAMAT_UNDUHAN
    assert nama["Suspensi & UMA (IDX)"] == pengumuman_idx.ALAMAT_PENGUMUMAN
    assert "Harga harian & indeks" not in nama, "harga yfinance tidak diunduh dari situs IDX"
    assert all(satu.alamat for satu in daftar)


def test_suspensi_uma_tidak_diingatkan_di_hari_libur(sambungan: sqlite3.Connection) -> None:
    _hari(sambungan, HARI_INI, bursa=False)

    nama = {satu.nama for satu in pengingat.susun(sambungan, HARI_INI)}

    assert "Suspensi & UMA (IDX)" not in nama
    assert "Notasi khusus & papan pemantauan (IDX)" in nama, "yang jatuh tempo tetap diingatkan"


def test_saat_dibuka_hanya_yang_jatuh_tempo_atau_menunggu() -> None:
    """K104: "tidak dinilai" selalu begitu untuk suspensi/UMA, jadi tidak diberitahukan."""
    daftar = tuple(
        jadwal.Butir(status, "j", status, "b")
        for status in (jadwal.TERBARU, jadwal.JATUH_TEMPO, jadwal.MENUNGGU, jadwal.TIDAK_DINILAI)
    )
    assert [satu.status for satu in pengingat.saat_dibuka(daftar)] == [jadwal.JATUH_TEMPO, jadwal.MENUNGGU]


def test_kotak_pesan_menggabung_tautan_yang_sama_dan_ya_membukanya() -> None:
    daftar = (
        pengingat.Pengingat("Harga harian & indeks", jadwal.JATUH_TEMPO, "b", "https://x/r"),
        pengingat.Pengingat("Cek sumber kedua (PRD 7.3)", jadwal.JATUH_TEMPO, "b", "https://x/r"),
        pengingat.Pengingat("Notasi", jadwal.JATUH_TEMPO, "b", "https://x/n"),
    )
    terbuka: list[str] = []
    terlihat: list[str] = []

    def kotak(judul: str, teks: str) -> int:
        terlihat.append(teks)
        return pengingat.IDYES

    pengingat.tampilkan(daftar, kotak=kotak, buka=lambda alamat: terbuka.append(alamat) or True)

    assert terbuka == ["https://x/r", "https://x/n"]
    assert "Cek sumber kedua (PRD 7.3) — jatuh tempo" in terlihat[0]


def test_menjawab_tidak_tidak_membuka_apa_pun() -> None:
    daftar = (pengingat.Pengingat("Notasi", jadwal.JATUH_TEMPO, "b", "https://x/n"),)

    def jangan(alamat: str) -> bool:
        raise AssertionError("peramban tidak boleh dibuka")

    pengingat.tampilkan(daftar, kotak=lambda judul, teks: 7, buka=jangan)


def test_kotak_pesan_yang_gagal_tampil_dilaporkan_bukan_ditelan() -> None:
    daftar = (pengingat.Pengingat("Notasi", jadwal.JATUH_TEMPO, "b", "https://x/n"),)

    def gagal(judul: str, teks: str) -> int:
        raise pengingat.GalatPengingat("kotak pesan Windows tidak bisa ditampilkan (galat 5)")

    with pytest.raises(pengingat.GalatPengingat, match="galat 5"):
        pengingat.tampilkan(daftar, kotak=gagal)
    with pytest.raises(pengingat.GalatPengingat, match="peramban"):
        pengingat.tampilkan(daftar, kotak=lambda judul, teks: pengingat.IDYES, buka=lambda alamat: False)


def test_ingatkan_tanpa_notifikasi_hanya_mencetak(
    sambungan: sqlite3.Connection, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def jangan(*_: object, **__: object) -> None:
        raise AssertionError("notifikasi tidak boleh ditampilkan")

    monkeypatch.setattr(pengingat, "tampilkan", jangan)

    assert cli.main(["--ingatkan", "--tanpa-notifikasi"]) == cli.KODE_OK
    assert notasi.ALAMAT_UNDUHAN in capsys.readouterr().out
