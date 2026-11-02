"""Batas antarmuka (A1, K91): tidak ada Qt di mana pun, dan inti tidak mengimpor dasbor web.

Sejak K91 antarmukanya dasbor web lokal (`mejasaham/web/`), jadi batas lamanya ("hanya `ui/` yang
boleh mengimpor Qt") menjadi lebih ketat: **tidak ada** modul yang boleh mengimpor Qt. Arah
ketergantungannya juga dijaga: `web/` boleh memakai inti dan `layar/`, tetapi inti tidak boleh
memakai `web/` — kalau tidak, mode kepala (AC-11) ikut memuat server HTTP.

Aturan yang hanya ditulis akan bocor pada perubahan pertama, jadi batas ini diuji secara statis
(AST seluruh paket) dan runtime (mode kepala tidak memuat Qt maupun `mejasaham.web`).
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
PAKET = AKAR / "mejasaham"
WEB = PAKET / "web"
QT = {"PySide6", "PyQt6", "PyQt5", "shiboken6"}


def _semua_berkas() -> list[Path]:
    return sorted(PAKET.rglob("*.py"))


def _impor(berkas: Path) -> set[str]:
    # utf-8-sig, bukan utf-8: `ast.parse` menolak BOM di awal teks (SyntaxError), padahal
    # menyimpan berkas UTF-8 ber-BOM itu biasa di Windows.
    pohon = ast.parse(berkas.read_text(encoding="utf-8-sig"), filename=str(berkas))
    nama: set[str] = set()
    for simpul in ast.walk(pohon):
        if isinstance(simpul, ast.Import):
            nama.update(alias.name for alias in simpul.names)
        elif isinstance(simpul, ast.ImportFrom) and simpul.module:
            nama.add(simpul.module)
    return nama


def test_tidak_ada_modul_yang_mengimpor_qt() -> None:
    pelanggar = {
        str(berkas.relative_to(AKAR)): kena
        for berkas in _semua_berkas()
        if (kena := sorted(n for n in _impor(berkas) if n.split(".")[0] in QT))
    }
    assert not pelanggar, f"Qt sudah dihapus (K91), tetapi masih diimpor: {pelanggar}"


def test_inti_tidak_mengimpor_dasbor_web() -> None:
    """Hanya `cli.py` (di dalam cabang dasbornya) yang boleh menyentuh `mejasaham.web`."""
    pelanggar = {
        str(berkas.relative_to(AKAR)): kena
        for berkas in _semua_berkas()
        if WEB not in berkas.parents
        and berkas.name != "cli.py"
        and (kena := sorted(n for n in _impor(berkas) if n.startswith("mejasaham.web")))
    }
    assert not pelanggar, f"Modul inti mengimpor dasbor web: {pelanggar}"


def test_berkas_paket_ditemukan() -> None:
    """Penjaga uji di atas: kalau penelusuran tidak menemukan apa pun, uji itu kosong."""
    nama = {berkas.name for berkas in _semua_berkas()}
    assert {"__main__.py", "cli.py", "server.py"} <= nama, nama


def test_mode_kepala_tidak_memuat_qt_maupun_server(tmp_path: Path) -> None:
    """AC-11: `--refresh --saring` (Task Scheduler) tidak memuat Qt maupun dasbor web.

    `MEJASAHAM_DATA` **wajib** diarahkan ke folder sementara: `--refresh` benar-benar menyentuh
    folder data, dan uji yang menulis ke `%LOCALAPPDATA%\\MejaSaham` milik pengguna bukan uji.
    """
    kode = (
        "import sys\n"
        "from mejasaham.cli import main\n"
        "main(['--refresh', '--saring'])\n"
        "dimuat = [m for m in sys.modules if m.split('.')[0] in {'PySide6', 'shiboken6'}"
        " or m.startswith('mejasaham.web')]\n"
        "print('BERSIH' if not dimuat else f'MEMUAT {dimuat}')\n"
    )
    lingkungan = {**os.environ, "MEJASAHAM_DATA": str(tmp_path / "data")}
    hasil = subprocess.run(
        [sys.executable, "-c", kode], cwd=AKAR, capture_output=True, text=True, env=lingkungan
    )
    assert "BERSIH" in hasil.stdout, hasil.stdout + hasil.stderr
