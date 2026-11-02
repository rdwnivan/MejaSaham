"""Pengingat terjadwal unduhan IDX (K102): notifikasi Windows bila ada berkas IDX yang perlu diunduh.

Isinya **diturunkan dari jadwal** (`jadwal.susun`, K93), bukan aturan kedua: butir yang punya
`alamat` (halaman IDX yang dibuka pengguna) dan belum "terbaru". Suspensi & UMA selalu "tidak
dinilai" (K99 — PDF yang terlewat tidak terdeteksi), jadi butir itu hanya diingatkan pada hari
bursa; selain itu pengingat di hari libur akan berbunyi untuk pengumuman yang tidak mungkin terbit.

`--ingatkan` dijadwalkan **pengguna** di Task Scheduler; aplikasi tidak membuat tugas terjadwal
sendiri (perubahan konfigurasi sistem yang menetap). Aplikasi juga tidak membuka situs IDX: tautan
di notifikasi dibuka pengguna di perambannya (K95/K96).

Notifikasinya **kotak pesan Windows** (`MessageBoxW` dari user32 lewat `ctypes`, pustaka standar,
K3): "Ya" membuka halaman IDX-nya di peramban. Toast lewat PowerShell sempat dibangun dan diuji
29 Okt 2026, tetapi di mesin pengguna gagal dengan dua cara bergantian — PowerShell anak jatuh ke
Constrained Language Mode (kebijakan Code Integrity aktif), atau `CreateToastNotifier` menolak
"process has no package identity" (0x80073D54) — jadi tidak bisa diandalkan untuk Task Scheduler
(T96). Kotak pesan yang gagal tampil adalah kegagalan yang dilaporkan, bukan ditelan (aturan keras
7): teks pengingatnya tetap tercetak, dan kode keluarnya bukan nol.
"""

from __future__ import annotations

import ctypes
import sqlite3
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mejasaham import jadwal

JUDUL = "MejaSaham — unduhan IDX"
MB_YESNO = 0x4
MB_ICONINFORMATION = 0x40
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000
IDYES = 6


class GalatPengingat(RuntimeError):
    """Notifikasi tidak bisa ditampilkan; pesannya untuk pengguna."""


@dataclass(frozen=True)
class Pengingat:
    nama: str
    status: str
    bukti: str
    alamat: str


def _hari_bursa(sambungan: sqlite3.Connection, hari: date) -> bool:
    """Hari bursa menurut kalender; tanggal yang tidak ada di kalender dianggap hari bursa —
    pengingat yang berbunyi sekali lebih banyak lebih murah daripada pengumuman yang terlewat."""
    baris = sambungan.execute(
        "SELECT hari_bursa FROM v_kalender_bursa_terkini WHERE tanggal = ?", (hari.isoformat(),)
    ).fetchone()
    return baris is None or bool(baris[0])


def susun(sambungan: sqlite3.Connection, hari_ini: date | None = None) -> tuple[Pengingat, ...]:
    hari = hari_ini or date.today()
    hasil = []
    for butir in jadwal.susun(sambungan, hari):
        if not butir.alamat or butir.status == jadwal.TERBARU:
            continue
        if butir.status == jadwal.TIDAK_DINILAI and not _hari_bursa(sambungan, hari):
            continue
        hasil.append(Pengingat(butir.nama, butir.status, butir.bukti, butir.alamat))
    return tuple(hasil)


def saat_dibuka(daftar: tuple[jadwal.Butir, ...]) -> tuple[jadwal.Butir, ...]:
    """Butir jadwal yang diberitahukan saat dasbor dibuka (K104 — pengganti tugas terjadwal).

    Hanya "jatuh tempo" dan "menunggu sumber". "Tidak dinilai" tidak ikut: suspensi/UMA,
    fundamental, dan SUN **selalu** tidak dinilai, jadi pemberitahuannya akan muncul tiap kali
    dasbor dibuka — peringatan yang selalu berbunyi berhenti memberi informasi. Butir itu tetap
    tampil di tabel jadwal di bawahnya."""
    return tuple(satu for satu in daftar if satu.status in (jadwal.JATUH_TEMPO, jadwal.MENUNGGU))


def ringkas(pengingat: tuple[Pengingat, ...]) -> str:
    if not pengingat:
        return "Tidak ada unduhan IDX yang perlu diingatkan hari ini."
    baris = ["Unduhan IDX yang perlu dikerjakan (K102):"]
    for satu in pengingat:
        baris.append(f"  {satu.nama} — {satu.status}: {satu.bukti}")
        baris.append(f"    buka {satu.alamat}")
    baris.append(
        "Sesudah mengunduh: --impor-unduhan (folder pantau, K101) atau unggah di menu Impor & cadangan."
    )
    return "\n".join(baris)


def alamat_unik(pengingat: tuple[Pengingat, ...]) -> tuple[str, ...]:
    """Satu tautan per halaman: Ringkasan Saham dipakai dua butir (harga resmi + cek sumber kedua)."""
    return tuple(dict.fromkeys(satu.alamat for satu in pengingat))


def teks_kotak(pengingat: tuple[Pengingat, ...]) -> str:
    baris = [f"• {satu.nama} — {satu.status}" for satu in pengingat]
    baris += ["", "Buka halaman IDX-nya sekarang?", *(f"  {alamat}" for alamat in alamat_unik(pengingat))]
    baris += ["", "Sesudah mengunduh: --impor-unduhan, atau unggah di menu Impor & cadangan."]
    return "\n".join(baris)


def _kotak_windows(judul: str, teks: str) -> int:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    except (AttributeError, OSError) as galat:
        raise GalatPengingat(f"kotak pesan Windows tidak tersedia: {galat}") from galat
    jawab = user32.MessageBoxW(
        None, teks, judul, MB_YESNO | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST
    )
    if jawab == 0:
        raise GalatPengingat(f"kotak pesan Windows tidak bisa ditampilkan (galat {ctypes.get_last_error()})")
    return jawab


def tampilkan(
    pengingat: tuple[Pengingat, ...],
    *,
    kotak: Callable[[str, str], int] = _kotak_windows,
    buka: Callable[[str], bool] = webbrowser.open,
) -> None:
    """Tampilkan kotak pesan; "Ya" membuka tiap halaman IDX. Melempar `GalatPengingat`.

    Menunggu sampai pengguna menjawab — itu memang gunanya pengingat terjadwal.
    """
    if not pengingat:
        return
    if kotak(JUDUL, teks_kotak(pengingat)) != IDYES:
        return
    gagal = [alamat for alamat in alamat_unik(pengingat) if not buka(alamat)]
    if gagal:
        raise GalatPengingat(f"peramban tidak bisa dibuka untuk: {', '.join(gagal)}")
