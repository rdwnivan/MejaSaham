"""Penjaga glif teks: tidak boleh ada urutan mojibake di dalam paket — diukur dari **byte**.

Kelas cacat yang dijaga di sini pernah terjadi dua kali: teks UTF-8 dibaca sebagai cp1252 lalu
disimpan kembali sebagai UTF-8, sehingga `≤` menjadi tiga karakter (`â‰¤`). Yang membuatnya mahal
bukan tampilannya, melainkan **cara memeriksanya**: terminal PowerShell bisa menampakkan glif yang
seolah-olah benar (dan sebaliknya), jadi "saya sudah melihatnya di layar" bukan bukti. Uji ini
karena itu memeriksa byte, bukan tampilan.

Diperbaiki tuntas 17 Okt 2026 (sesi 10): 33 glif di `mejasaham/metrik.py` — 12 `≤`, 10 `÷`, 5 `→`,
3 `−`, 2 `×`, 1 `√` — dan sebagian di antaranya **pesan yang tampil ke pengguna**
(`ekuitas â‰¤ 0 sehingga DER tidak bermakna`). `docs/` sengaja **tidak** ikut dipindai: di sana
urutan itu dipakai sebagai **kutipan gejala**, dan menghapusnya justru menghilangkan buktinya.
"""

from __future__ import annotations

from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[1]
PAKET = AKAR / "mejasaham"
#: Berkas teks di dalam paket yang ikut diperiksa.
SUFIKS = (".py", ".toml", ".csv", ".txt")
#: Glif yang bentuk rusaknya kita kenali; `≤` dan `≥` paling sering muncul di pesan metrik.
GLIF = "≤≥×÷√−→←—–·•≈±≠°²³½¼¾…“”‘’"


def urutan_rusak() -> dict[str, str]:
    """(urutan byte mojibake → glif yang benar) untuk tiap glif yang bisa dibalik."""
    peta: dict[str, str] = {}
    for glif in GLIF:
        try:
            rusak = glif.encode("utf-8").decode("cp1252")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if rusak != glif:
            peta[rusak] = glif
    return peta


def _berkas_paket() -> list[Path]:
    return sorted(
        berkas
        for berkas in PAKET.rglob("*")
        if berkas.is_file() and berkas.suffix.lower() in SUFIKS
    )


def test_paket_tidak_memuat_glif_mojibake() -> None:
    """Setiap berkas teks di `mejasaham/` bebas urutan mojibake — diperiksa per byte."""
    peta = urutan_rusak()
    assert peta, "peta glif tidak boleh kosong: kalau kosong, uji ini tidak memeriksa apa pun"

    temuan: list[str] = []
    for berkas in _berkas_paket():
        isi = berkas.read_text(encoding="utf-8")
        for rusak, glif in peta.items():
            banyak = isi.count(rusak)
            if banyak:
                temuan.append(
                    f"{berkas.relative_to(AKAR)}: {banyak}× {rusak!r} — seharusnya {glif!r}"
                )
    assert not temuan, (
        "glif rusak (UTF-8 dibaca sebagai cp1252 lalu disimpan lagi) ditemukan; "
        "perbaikannya: ganti urutan itu kembali dengan glif yang benar, lalu periksa byte-nya — "
        "jangan mengandalkan tampilan terminal.\n  " + "\n  ".join(temuan)
    )


def test_peta_glif_menutup_seluruh_glif_yang_pernah_diperbaiki() -> None:
    """Penjaganya harus benar-benar memeriksa: tiap glif yang diperbaiki punya bentuk rusak dikenali.

    Tanpa uji ini, penjaga di atas bisa menjadi kosong tanpa satu pun galat — mis. kalau daftar
    glifnya disunting dan satu glif terlewat, atau bila `cp1252` tidak lagi bisa membalikkannya.
    """
    peta = urutan_rusak()
    terbalik = set(peta.values())
    for glif in ("≤", "×", "÷", "√", "−", "→"):
        assert glif in terbalik, f"{glif!r} tidak dikenali lagi oleh penjaga glif"
