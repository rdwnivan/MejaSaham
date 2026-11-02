"""Meja Saham — inti aplikasi.

Antarmukanya dasbor web lokal (`mejasaham/web/`, K91); jendela PySide6 sudah dihapus. Paket ini
tidak boleh mengimpor Qt lagi, dan inti tidak boleh mengimpor `mejasaham.web` — keduanya diuji
`tests/test_batas_ui.py` (PRD 6.1, AC-11).
"""

from __future__ import annotations

__version__ = "0.0.0"
