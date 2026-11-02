from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mejasaham import cadangan, db


def test_cadangan_vacuum_mencakup_konfigurasi_dan_arsip_dan_pulih_ke_folder_bersih(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "konfigurasi").mkdir()
    (data / "konfigurasi" / "parameter-bursa.toml").write_text("versi = 1\n", encoding="utf-8")
    (data / "arsip-snapshot" / "snapshot-1").mkdir(parents=True)
    (data / "arsip-snapshot" / "snapshot-1" / "bukti.txt").write_text("arsip", encoding="utf-8")
    sumber = db.siapkan(data / "mejasaham.db")
    try:
        with db.tulis(sumber) as koneksi:
            koneksi.execute(
                "INSERT INTO log_jalan (waktu, proses, hasil, pesan) VALUES (?, ?, ?, ?)",
                (db.waktu_iso(), "uji", "sukses", "ada di cadangan"),
            )
        hasil = cadangan.buat(
            sumber,
            folder_data=data,
            tujuan=tmp_path / "backup",
            sekarang=datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc),
        )
    finally:
        sumber.close()

    assert (hasil / "konfigurasi" / "parameter-bursa.toml").is_file()
    assert (hasil / "arsip-snapshot" / "snapshot-1" / "bukti.txt").read_text(encoding="utf-8") == "arsip"
    bersih = tmp_path / "instalasi-bersih"
    cadangan.pulihkan(hasil, folder_data=bersih)
    pulihan = db.hubungkan(bersih / "mejasaham.db")
    try:
        assert pulihan.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert pulihan.execute("SELECT pesan FROM log_jalan WHERE proses='uji'").fetchone()[0] == "ada di cadangan"
    finally:
        pulihan.close()
    assert (bersih / "konfigurasi" / "parameter-bursa.toml").is_file()
    assert (bersih / "arsip-snapshot" / "snapshot-1" / "bukti.txt").is_file()


def test_retensi_membuang_cadangan_tertua(tmp_path: Path) -> None:
    data = tmp_path / "data"
    sambungan = db.siapkan(data / "mejasaham.db")
    folder = tmp_path / "backup"
    try:
        for hari in range(3):
            cadangan.buat(
                sambungan,
                folder_data=data,
                tujuan=folder,
                retensi=2,
                sekarang=datetime(2026, 10, 1 + hari, tzinfo=timezone.utc),
            )
    finally:
        sambungan.close()
    assert len(cadangan.daftar(folder)) == 2


def test_tolak_folder_cadangan_di_dalam_folder_data(tmp_path: Path) -> None:
    data = tmp_path / "data"
    sambungan = db.siapkan(data / "mejasaham.db")
    try:
        with pytest.raises(cadangan.GalatCadangan, match="di luar folder data"):
            cadangan.buat(sambungan, folder_data=data, tujuan=data / "backup")
    finally:
        sambungan.close()


def test_migrasi_mengambil_cadangan_basis_data_lama_sebelum_mengubahnya(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    berkas = tmp_path / "data" / "mejasaham.db"
    berkas.parent.mkdir()
    # Berkas SQLite valid tetapi belum memiliki skema aplikasi.
    with sqlite3.connect(berkas) as awal:
        awal.execute("CREATE TABLE nilai_lama (isi TEXT)")
        awal.execute("INSERT INTO nilai_lama VALUES ('sebelum migrasi')")

    tujuan = tmp_path / "cadangan-pilihan"
    monkeypatch.setenv(cadangan.ENV_FOLDER_CADANGAN, str(tujuan))
    baru = db.siapkan(berkas)
    baru.close()
    hasil = cadangan.daftar(tujuan)
    assert len(hasil) == 1
    pulihan = sqlite3.connect(hasil[0] / "mejasaham.db")
    try:
        assert pulihan.execute("SELECT isi FROM nilai_lama").fetchone()[0] == "sebelum migrasi"
    finally:
        pulihan.close()


def test_folder_tujuan_yang_disebut_konfirmasi_adalah_folder_yang_ditulis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aksi #19c/K59 d: folder yang **disebut** konfirmasi harus folder yang menerima cadangan.

    Yang diuji bukan nama fungsinya, melainkan janjinya. `MEJASAHAM_BACKUP` (atau
    `--folder-cadangan`) yang dibaca hanya oleh salah satu pihak akan membuat dialog jendela
    menyebut folder yang tidak pernah menerima cadangan itu — dan itu tidak terlihat di layar
    mana pun, tepat pada tindakan yang dicari saat data sudah bermasalah.
    """
    data = tmp_path / "data"
    sambungan = db.siapkan(data / "mejasaham.db")
    pilihan = tmp_path / "disk-eksternal"
    monkeypatch.setenv(cadangan.ENV_FOLDER_CADANGAN, str(pilihan))
    try:
        hasil = cadangan.buat(sambungan, folder_data=data)
    finally:
        sambungan.close()

    assert cadangan.folder_tujuan(data) == pilihan
    assert hasil.parent == pilihan
    assert cadangan.daftar(pilihan) == (hasil,)


def test_ringkas_daftar_memuat_jalur_cadangan_terbaru_lebih_dulu(tmp_path: Path) -> None:
    """Satu teks untuk baris perintah & jendela (aksi #19c): jalur tiap cadangan, satu per baris."""
    folder = tmp_path / "backup"
    assert cadangan.ringkas_daftar(folder) == "Belum ada cadangan."

    data = tmp_path / "data"
    sambungan = db.siapkan(data / "mejasaham.db")
    try:
        pertama = cadangan.buat(
            sambungan, folder_data=data, tujuan=folder,
            sekarang=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        )
        kedua = cadangan.buat(
            sambungan, folder_data=data, tujuan=folder,
            sekarang=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
        )
    finally:
        sambungan.close()

    assert cadangan.ringkas_daftar(folder).splitlines() == [str(kedua), str(pertama)]


def test_folder_tujuan_yang_tidak_bisa_dibuat_berhenti_sebagai_galat_cadangan(
    tmp_path: Path,
) -> None:
    """Kegagalan folder tujuan (mis. disk eksternal belum terpasang) terbaca, bukan traceback.

    Diuji dengan kegagalan **nyata** — path yang sudah dipakai berkas biasa, sehingga `mkdir`
    gagal di sistem berkas ini — bukan dengan mengganti `buat`. Yang diperiksa: pesannya menyebut
    folder tujuannya dan jalan keluarnya, sebab itulah yang bisa dikerjakan pengguna.
    """
    data = tmp_path / "data"
    sambungan = db.siapkan(data / "mejasaham.db")
    bukan_folder = tmp_path / "bukan-folder"
    bukan_folder.write_text("sudah dipakai berkas lain", encoding="utf-8")
    try:
        with pytest.raises(cadangan.GalatCadangan) as galat:
            cadangan.buat(sambungan, folder_data=data, tujuan=bukan_folder)
    finally:
        sambungan.close()

    pesan = str(galat.value)
    assert str(bukan_folder) in pesan
    assert cadangan.ENV_FOLDER_CADANGAN in pesan


def _data_dengan_arsip(tmp_path: Path) -> tuple[Path, sqlite3.Connection]:
    data = tmp_path / "data"
    (data / "arsip-snapshot" / "2026-10-28" / "snapshot-15").mkdir(parents=True)
    (data / "arsip-snapshot" / "2026-10-28" / "snapshot-15" / "harga.csv").write_text(
        "kode;tutup\nAUTO;2500\n", encoding="utf-8"
    )
    return data, db.siapkan(data / "mejasaham.db")


def test_retensi_bawaan_tiga_cadangan(tmp_path: Path) -> None:
    """K92: tiap cadangan memuat basis data penuh (±250 MB), jadi bawaannya 3, bukan 14."""
    data = tmp_path / "data"
    sambungan = db.siapkan(data / "mejasaham.db")
    folder = tmp_path / "backup"
    try:
        for hari in range(5):
            cadangan.buat(
                sambungan, folder_data=data, tujuan=folder,
                sekarang=datetime(2026, 10, 1 + hari, tzinfo=timezone.utc),
            )
    finally:
        sambungan.close()
    assert cadangan.RETENSI_BAWAAN == 3
    assert [p.name[:8] for p in cadangan.daftar(folder)] == ["20261005", "20261004", "20261003"]


def test_arsip_di_cadangan_ditautkan_bukan_disalin_dan_tetap_utuh(tmp_path: Path) -> None:
    """K92: arsip snapshot tidak pernah ditimpa (arsip.py aturan 2), jadi cadangan menautkannya
    (hardlink) alih-alih menyalin ulang ratusan MB. Berkas asli yang diganti `os.replace` atau
    dihapus tidak mengubah isi cadangan, dan pemulihan tetap mengembalikannya."""
    data, sambungan = _data_dengan_arsip(tmp_path)
    try:
        hasil = cadangan.buat(sambungan, folder_data=data, tujuan=tmp_path / "backup")
    finally:
        sambungan.close()
    relatif = Path("arsip-snapshot") / "2026-10-28" / "snapshot-15" / "harga.csv"
    assert (data / relatif).samefile(hasil / relatif)

    # Penggantian atomik (cara arsip.py menulis) membuat berkas baru; cadangan memegang isi lama.
    pengganti = data / relatif.with_suffix(".tmp")
    pengganti.write_text("isi lain", encoding="utf-8")
    pengganti.replace(data / relatif)
    assert (hasil / relatif).read_text(encoding="utf-8") == "kode;tutup\nAUTO;2500\n"

    import shutil

    shutil.rmtree(data)
    bersih = tmp_path / "bersih"
    cadangan.pulihkan(hasil, folder_data=bersih)
    assert (bersih / relatif).read_text(encoding="utf-8") == "kode;tutup\nAUTO;2500\n"
    assert not (bersih / relatif).samefile(hasil / relatif)


def test_konfigurasi_di_cadangan_tetap_disalin(tmp_path: Path) -> None:
    """Konfigurasi boleh disunting tangan di tempat, jadi ia disalin — bukan ditautkan."""
    data, sambungan = _data_dengan_arsip(tmp_path)
    (data / "konfigurasi").mkdir()
    (data / "konfigurasi" / "emiten.csv").write_text("kode\nAUTO\n", encoding="utf-8")
    try:
        hasil = cadangan.buat(sambungan, folder_data=data, tujuan=tmp_path / "backup")
    finally:
        sambungan.close()
    assert not (data / "konfigurasi" / "emiten.csv").samefile(hasil / "konfigurasi" / "emiten.csv")


def test_rapikan_arsip_menautkan_salinan_identik_saja(tmp_path: Path) -> None:
    """Cadangan lama (sebelum K92) berisi salinan penuh; `rapikan_arsip` menggantinya dengan
    tautan **hanya** bila isinya sama persis byte demi byte dengan arsip di folder data."""
    data, sambungan = _data_dengan_arsip(tmp_path)
    sambungan.close()
    relatif = Path("arsip-snapshot") / "2026-10-28" / "snapshot-15" / "harga.csv"
    lama = tmp_path / "backup" / "20261028T120000000000+0700"
    (lama / relatif.parent).mkdir(parents=True)
    (lama / cadangan.NAMA_MANIFEST).write_text("{}", encoding="utf-8")
    (lama / relatif).write_bytes((data / relatif).read_bytes())
    beda = lama / relatif.with_name("emiten.csv")
    beda.write_text("hanya di cadangan", encoding="utf-8")
    (data / relatif.with_name("emiten.csv")).write_text("isi berbeda", encoding="utf-8")

    hasil = cadangan.rapikan_arsip(tmp_path / "backup", folder_data=data)

    assert (lama / relatif).samefile(data / relatif)
    assert beda.read_text(encoding="utf-8") == "hanya di cadangan"
    assert hasil.ditautkan == 1
    assert hasil.byte_dihemat == (data / relatif).stat().st_size
    # Menjalankan lagi tidak menautkan apa pun: yang sudah tertaut tidak dihitung dua kali.
    assert cadangan.rapikan_arsip(tmp_path / "backup", folder_data=data).ditautkan == 0
