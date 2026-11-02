"""Format tampilan Indonesia (U11) — satu tempat, supaya tidak ada dua gaya angka di aplikasi.

U11 menetapkan: angka tampil dengan **koma desimal dan titik ribuan**, tanggal ditulis
`06 Okt 2026`. Aturan itu urusan **tampilan**, bukan penyimpanan (T12 menyimpan ISO-8601) dan
bukan perhitungan (`metrik.py` mengembalikan angka, bukan teks).

Modul ini ada sejak sekarang — jauh sebelum jendela PySide6 ditulis — karena satu alasan
praktis: tanpa satu tempat, format angka akan ditulis ulang di baris perintah, layar detail,
ekspor CSV, dan log, lalu berbeda-beda di antaranya. Ekspor CSV punya kebutuhan tambahan
sendiri (`;` sebagai pemisah, desimal koma) dan itu juga di sini.
"""

from __future__ import annotations

from datetime import date

#: Nama bulan singkat Indonesia untuk tampilan tanggal (U11: `06 Okt 2026`).
BULAN_SINGKAT = (
    "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
)


def angka(nilai: float | None, desimal: int = 2, kosong: str = "—") -> str:
    """Angka tampilan: koma desimal, titik ribuan. `None` menjadi tanda kosong, bukan nol."""
    if nilai is None:
        return kosong
    teks = f"{nilai:,.{desimal}f}"
    return teks.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def persen(nilai: float | None, desimal: int = 1, kosong: str = "—") -> str:
    """Rasio (0,356) menjadi `35,6%`."""
    if nilai is None:
        return kosong
    return angka(nilai * 100, desimal, kosong) + "%"


def bertanda(nilai: float | None, desimal: int = 0, kosong: str = "—") -> str:
    """Angka yang arahnya penting: tanda `+` **selalu** ikut bila nilainya positif.

    Dipakai perubahan IHSG (PRD 11.1: `+0,42%`): tanpa tanda `+`, `0,42%` dan `−0,42%` terbaca
    sama sepintas, dan justru itulah angka yang menentukan pembacaan rezim pasar.
    """
    if nilai is None:
        return kosong
    tanda = "+" if nilai >= 0 else "-"
    return tanda + angka(abs(nilai), desimal, kosong)


def rupiah(nilai: float | None, desimal: int = 0, kosong: str = "—") -> str:
    return kosong if nilai is None else "Rp " + angka(nilai, desimal, kosong)


def rupiah_singkat(nilai: float | None, kosong: str = "—") -> str:
    """Rupiah ringkas untuk alasan saringan: `Rp 5,00 M`, `Rp 812,40 M`, `Rp 1,20 T`."""
    if nilai is None:
        return kosong
    for pembagi, satuan in ((10**12, "T"), (10**9, "M"), (10**6, "jt")):
        if abs(nilai) >= pembagi:
            return f"Rp {angka(nilai / pembagi, 2)} {satuan}"
    return "Rp " + angka(nilai, 0)


def tanggal(tanggal: date | None, kosong: str = "—") -> str:
    """Tanggal tampilan: `06 Okt 2026` (U11)."""
    if tanggal is None:
        return kosong
    return f"{tanggal.day:02d} {BULAN_SINGKAT[tanggal.month - 1]} {tanggal.year}"
