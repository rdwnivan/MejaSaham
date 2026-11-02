"""Letak data runtime, **di luar** paket dan di luar folder aplikasi (A3, PRD 6.1, AC-12).

Alasan aturan ini ada: perbaikan data dan konfigurasi tidak boleh menuntut rebuild `.exe`.
Karena itu seluruh keadaan aplikasi (basis data, konfigurasi, log, arsip snapshot, cadangan)
tinggal di `%LOCALAPPDATA%\\MejaSaham\\`, dan paket `mejasaham/` tetap hanya berisi kode serta
berkas bawaan.

Berkas ini sengaja tidak mengimpor apa pun dari paket ini supaya bisa dipakai modul mana pun
tanpa risiko impor melingkar. Penimpaan lewat variabel lingkungan `MEJASAHAM_DATA` dipakai
test dan mode portabel; tanpa itu, lokasi mengikuti aturan sistem.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

NAMA_APLIKASI = "MejaSaham"
ENV_FOLDER_DATA = "MEJASAHAM_DATA"

NAMA_BERKAS_BASIS_DATA = "mejasaham.db"


class GalatLokasi(RuntimeError):
    """Folder data tidak bisa dibuat.

    Ada alasannya jadi kelas galat tersendiri: kalau folder data gagal dibuat, aplikasi tidak
    boleh jalan setengah hati dengan data yang entah di mana (aturan keras 7: gagal itu berisik).
    Pesannya menyebut penyebab dan jalan keluarnya, karena ini biasanya masalah izin
    (kebijakan kantor, OneDrive, profil pengguna) — bukan bug aplikasi.
    """


def folder_data() -> Path:
    """Folder induk seluruh data runtime.

    Urutan: `MEJASAHAM_DATA` (test/portabel) → `%LOCALAPPDATA%\\MejaSaham` (Windows)
    → `$XDG_DATA_HOME/MejaSaham` atau `~/.local/share/MejaSaham` (lain-lain, supaya
    pengembangan di luar Windows tidak menulis ke tempat yang tidak terduga).
    """
    khusus = os.environ.get(ENV_FOLDER_DATA)
    if khusus:
        return Path(khusus).expanduser()

    if sys.platform == "win32":
        akar = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
    else:
        akar = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(akar) / NAMA_APLIKASI


def folder_konfigurasi() -> Path:
    return folder_data() / "konfigurasi"


def folder_log() -> Path:
    return folder_data() / "log"


def folder_arsip_snapshot() -> Path:
    return folder_data() / "arsip-snapshot"


def folder_cadangan() -> Path:
    return folder_data() / "cadangan"


def berkas_basis_data() -> Path:
    return folder_data() / NAMA_BERKAS_BASIS_DATA


def pastikan_folder(folder: Path) -> Path:
    """Buat folder (beserta induknya) bila belum ada, lalu kembalikan foldernya."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as galat:
        raise GalatLokasi(
            f"tidak bisa membuat folder data '{folder}': {galat}. Periksa izin folder itu, "
            f"atau arahkan variabel lingkungan {ENV_FOLDER_DATA} ke folder lain yang bisa ditulis."
        ) from galat
    return folder
