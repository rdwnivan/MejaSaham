"""Satu titik masuk untuk dua mode (PRD 6.1, diubah K91).

    python -m mejasaham                       -> dasbor web lokal di http://127.0.0.1:8765
    python -m mejasaham --refresh --saring    -> mode kepala, tanpa dasbor (AC-11)
    python -m mejasaham --muat-konfigurasi    -> muat parameter bursa dari TOML (K6)
"""

from __future__ import annotations

import sys

from mejasaham.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
