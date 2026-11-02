"""Folder pantau: berkas IDX yang sudah diunduh pengguna, dikenali untuk diimpor otomatis (K101).

Pengunduhannya tetap **manual** — Syarat Penggunaan IDX melarang scraping (K95/K96), jadi
aplikasi tidak pernah membuka situs IDX. Yang diotomatiskan hanya langkah sesudah pengguna menekan
"Unduh": `--impor-unduhan` (atau tombol dasbor) membaca folder ini, lalu mengimpor lewat jalur yang
**sama** dengan unggahan dasbor (`layar.tulis.permintaan_impor_folder_pantau`).

Modul ini **mengenali** berkas dari namanya dan mencatat jejak tiap jalan impornya di `log_jalan`
(`catat_jalan`/`jalan_terakhir`, supaya jalan dari Task Scheduler yang gagal tampil di dasbor —
AC-9); mengimpor sendiri bukan tugasnya. Nama yang dikenali
adalah nama dari tombol "Unduh" situs IDX (contoh nyata, bukan tebakan):

* `Ringkasan Saham-YYYYMMDD.xlsx` (K95/K97),
* `Notasi Khusus-YYYYMMDD.xlsx` (K96 — tanggal datanya hanya ada di nama itu),
* PDF pengumuman berawalan tanggal, `YYYYMMDD-…pdf` (K99/K100: `20261028-UMA_COIN.pdf`,
  `20261028-WAS_Suspensi_PTSP.pdf`).

Peramban menambah " (1)" pada unduhan kedua bernama sama; itu tetap dikenali. Berkas lain di
folder itu (mis. folder Unduhan biasa) **tidak disentuh dan tidak dilaporkan** — yang bukan milik
aplikasi bukan kegagalan aplikasi. Berkas yang dikenali tetapi isinya tidak terbaca justru
dilaporkan sebagai ditolak (aturan keras 7).
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from mejasaham import db, notasi, tampilan, unggahan_idx

ENV_FOLDER_PANTAU = "MEJASAHAM_FOLDER_PANTAU"
#: `log_jalan.proses` untuk impor folder pantau, dari baris perintah maupun tombol dasbor.
PROSES_IMPOR_UNDUHAN = "impor-unduhan"

POLA_RINGKASAN = re.compile(r"Ringkasan Saham-(\d{8})(?: \(\d+\))?\.xlsx", re.IGNORECASE)
#: Awalan tanggal saja: nama PDF UPT dari situs belum pernah terlihat (K100 memakai PDF riset),
#: sedangkan isi PDF-nya sendiri memuat semua yang dibutuhkan pembaca (`pengumuman_idx.baca`).
POLA_PENGUMUMAN = re.compile(r"\d{8}-.+\.pdf", re.IGNORECASE)


class GalatFolderPantau(RuntimeError):
    """Folder pantau tidak diatur atau tidak bisa dibaca; pesannya untuk pengguna."""


@dataclass(frozen=True)
class Pindaian:
    folder: Path
    #: (jalur, tanggal perdagangan isi berkas), urut tanggal.
    ringkasan: tuple[tuple[Path, date], ...] = ()
    #: (jalur, tanggal daftar dari nama berkas), urut tanggal.
    notasi: tuple[tuple[Path, date], ...] = ()
    pengumuman: tuple[Path, ...] = ()
    #: Dikenali dari namanya tetapi isinya tidak terbaca — tetap di folder, dilaporkan.
    ditolak: tuple[tuple[Path, str], ...] = ()

    @property
    def kosong(self) -> bool:
        return not (self.ringkasan or self.notasi or self.pengumuman or self.ditolak)

    def ringkas(self) -> str:
        if self.kosong:
            return f"Folder pantau {self.folder}: tidak ada berkas IDX yang dikenali."
        baris = [f"Folder pantau {self.folder}:"]
        baris += [f"  Ringkasan Saham {tampilan.tanggal(hari)}: {jalur.name}" for jalur, hari in self.ringkasan]
        baris += [f"  Notasi Khusus per {tampilan.tanggal(hari)}: {jalur.name}" for jalur, hari in self.notasi]
        baris += [f"  PDF pengumuman: {jalur.name}" for jalur in self.pengumuman]
        baris += [f"  DITOLAK {jalur.name}: {sebab}" for jalur, sebab in self.ditolak]
        return "\n".join(baris)


def folder(tujuan: Path | None = None) -> Path | None:
    """Folder yang dipantau: `tujuan` eksplisit, lalu `MEJASAHAM_FOLDER_PANTAU`; tidak ada = mati."""
    if tujuan is not None:
        return tujuan
    khusus = os.environ.get(ENV_FOLDER_PANTAU, "").strip()
    return Path(khusus).expanduser() if khusus else None


def pindai(sasaran: Path) -> Pindaian:
    """Kenali berkas IDX di `sasaran`. Membaca saja; tidak ada yang dipindah atau ditulis."""
    if not sasaran.is_dir():
        raise GalatFolderPantau(f"folder pantau {sasaran} tidak ada atau bukan folder")
    ringkasan: list[tuple[Path, date]] = []
    daftar_notasi: list[tuple[Path, date]] = []
    pengumuman: list[Path] = []
    ditolak: list[tuple[Path, str]] = []
    try:
        isi = sorted(sasaran.iterdir())
    except OSError as galat:
        raise GalatFolderPantau(f"folder pantau {sasaran} tidak bisa dibaca: {galat}") from galat
    for jalur in isi:
        if not jalur.is_file():
            continue
        if POLA_RINGKASAN.fullmatch(jalur.name):
            try:
                ringkasan.append((jalur, unggahan_idx.baca(jalur).tanggal))
            except (unggahan_idx.GalatUnggahan, OSError) as galat:
                ditolak.append((jalur, str(galat)))
        elif cocok := notasi.POLA_NAMA_UNDUHAN.fullmatch(jalur.name):
            hari = _tanggal_nama(cocok.group(1))
            if hari is None:
                ditolak.append((jalur, f"tanggal '{cocok.group(1)}' di nama berkas tidak valid"))
            else:
                daftar_notasi.append((jalur, hari))
        elif POLA_PENGUMUMAN.fullmatch(jalur.name):
            pengumuman.append(jalur)
    return Pindaian(
        folder=sasaran,
        ringkasan=tuple(sorted(ringkasan, key=lambda satu: (satu[1], satu[0].name))),
        notasi=tuple(sorted(daftar_notasi, key=lambda satu: (satu[1], satu[0].name))),
        pengumuman=tuple(pengumuman),
        ditolak=tuple(ditolak),
    )


def _tanggal_nama(teks: str) -> date | None:
    try:
        return datetime.strptime(teks, "%Y%m%d").date()
    except ValueError:
        return None


@dataclass(frozen=True)
class JalanImpor:
    """Satu baris `log_jalan` impor folder pantau."""

    waktu: datetime
    berhasil: bool
    pesan: str


def catat_jalan(sambungan: sqlite3.Connection, *, berhasil: bool, pesan: str) -> None:
    """Catat hasil satu jalan impor folder pantau, di transaksi tersendiri.

    Sukses juga dicatat: kotak "Perlu diperbarui" menampilkan kegagalan hanya selama jalan
    **terakhir** gagal, jadi jalan berikutnya yang berhasil (dari mana pun) menghapusnya.
    """
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO log_jalan (waktu, proses, hasil, pesan) VALUES (?, ?, ?, ?)",
            (db.waktu_iso(), PROSES_IMPOR_UNDUHAN, "sukses" if berhasil else "gagal", pesan),
        )


def jalan_terakhir(sambungan: sqlite3.Connection) -> JalanImpor | None:
    baris = sambungan.execute(
        "SELECT waktu, hasil, pesan FROM log_jalan WHERE proses = ? ORDER BY id_log DESC LIMIT 1",
        (PROSES_IMPOR_UNDUHAN,),
    ).fetchone()
    if baris is None:
        return None
    return JalanImpor(datetime.fromisoformat(baris[0]), baris[1] != "gagal", baris[2] or "")
