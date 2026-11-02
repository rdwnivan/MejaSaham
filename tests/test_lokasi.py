"""Uji letak data runtime (A3, PRD 6.1, AC-12).

Yang diuji bukan "apakah fungsinya mengembalikan Path", melainkan janji yang membuat AC-12
masuk akal: data runtime berada di luar paket dan bisa dipindahkan lewat satu variabel
lingkungan (dipakai test dan mode portabel).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mejasaham import lokasi


def test_penimpaan_lewat_variabel_lingkungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data-uji"))

    assert lokasi.folder_data() == tmp_path / "data-uji"
    assert lokasi.berkas_basis_data() == tmp_path / "data-uji" / "mejasaham.db"


def test_seluruh_folder_turunan_berada_di_bawah_folder_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path))
    akar = lokasi.folder_data()

    for folder in (
        lokasi.folder_konfigurasi(),
        lokasi.folder_log(),
        lokasi.folder_arsip_snapshot(),
        lokasi.folder_cadangan(),
    ):
        assert akar in folder.parents, folder


def test_data_runtime_di_luar_paket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A3: kode dan data tidak boleh tinggal di folder yang sama."""
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path))
    paket = Path(lokasi.__file__).resolve().parent

    assert paket not in lokasi.folder_data().resolve().parents


@pytest.mark.skipif(sys.platform != "win32", reason="aturan bawaan hanya berlaku di Windows")
def test_bawaan_windows_memakai_localappdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(lokasi.ENV_FOLDER_DATA, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert lokasi.folder_data() == tmp_path / lokasi.NAMA_APLIKASI


def test_pastikan_folder_membuat_induk_yang_belum_ada(tmp_path: Path) -> None:
    dalam = tmp_path / "a" / "b" / "c"

    assert not dalam.exists()
    assert lokasi.pastikan_folder(dalam) == dalam
    assert dalam.is_dir()


def test_folder_yang_tidak_bisa_dibuat_gagal_berisik(tmp_path: Path) -> None:
    """Aturan keras 7: gagal membuat folder data harus berhenti dengan pesan yang menolong.

    Diuji dengan menaruh **berkas** di posisi yang seharusnya folder, sehingga `mkdir` gagal
    tanpa perlu mengubah izin apa pun di mesin yang menjalankan test.
    """
    penghalang = tmp_path / "berkas.txt"
    penghalang.write_text("bukan folder", encoding="utf-8")

    with pytest.raises(lokasi.GalatLokasi) as galat:
        lokasi.pastikan_folder(penghalang / "sub")

    assert lokasi.ENV_FOLDER_DATA in str(galat.value), "pesan harus menyebut jalan keluarnya"
