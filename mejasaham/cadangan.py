"""Cadangan portabel basis data dan berkas runtime penting (F12, PRD 9.12)."""

from __future__ import annotations

import filecmp
import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mejasaham import lokasi

#: Tiap cadangan memuat basis data penuh (±250 MB pada data kerja, Okt 2026), jadi yang disimpan
#: tiga terbaru — bukan 14 (K92, atas permintaan pengguna supaya folder tidak membengkak).
RETENSI_BAWAAN = 3
NAMA_DB = "mejasaham.db"
NAMA_MANIFEST = "manifest.json"
ENV_FOLDER_CADANGAN = "MEJASAHAM_BACKUP"


class GalatCadangan(RuntimeError):
    """Kegagalan cadangan/pemulihan yang harus ditampilkan ke operator."""


def folder_bawaan() -> Path:
    """Lokasi bawaan di luar folder runtime agar bertahan saat folder data terhapus."""
    return folder_tujuan()


def folder_tujuan(sumber: Path | None = None, tujuan: Path | None = None) -> Path:
    """Folder tempat cadangan ditulis — **satu** perhitungan, bukan dua.

    Dipisah dari `buat()` supaya konfirmasi di jendela (aksi #19c, K59 d) menyebut folder yang
    **sama** dengan yang benar-benar ditulis. Dua perhitungan yang dimaksudkan sama adalah dua
    kesempatan berbeda: `--folder-cadangan`/`MEJASAHAM_BACKUP` yang hanya dibaca salah satunya
    akan membuat dialog menyebut folder yang tidak pernah menerima cadangan itu.

    Aturannya: `tujuan` eksplisit menang, lalu `MEJASAHAM_BACKUP`, lalu folder saudara folder data.
    """
    if tujuan is not None:
        return tujuan
    khusus = os.environ.get(ENV_FOLDER_CADANGAN)
    if khusus:
        return Path(khusus).expanduser()
    dasar = sumber or lokasi.folder_data()
    return dasar.parent / f"{dasar.name}-cadangan"


def periksa_tujuan(sumber: Path, tujuan: Path) -> None:
    """Tolak folder cadangan yang berada di dalam folder data.

    Dipakai `buat()` **dan** konfirmasi jendela (aksi #19c), lewat fungsi yang sama: pengguna
    tidak boleh diminta menyetujui cadangan yang pasti ditolak, dan syaratnya tidak boleh hidup
    di dua tempat.
    """
    if tujuan.resolve() == sumber.resolve() or sumber.resolve() in tujuan.resolve().parents:
        raise GalatCadangan("folder cadangan harus berada di luar folder data")


def buat(
    sambungan: sqlite3.Connection,
    *,
    folder_data: Path | None = None,
    tujuan: Path | None = None,
    retensi: int = RETENSI_BAWAAN,
    sekarang: datetime | None = None,
) -> Path:
    """Ambil snapshot konsisten dengan VACUUM INTO, sertakan konfigurasi dan arsip."""
    sumber = folder_data or lokasi.folder_data()
    sasaran = folder_tujuan(sumber, tujuan)
    if retensi < 1:
        raise GalatCadangan("retensi cadangan harus minimal 1")
    periksa_tujuan(sumber, sasaran)
    waktu = (sekarang or datetime.now().astimezone()).astimezone().strftime("%Y%m%dT%H%M%S%f%z")
    hasil = sasaran / waktu
    sementara: Path | None = None
    try:
        # Folder tujuan bisa belum ada atau tidak bisa ditulis (mis. disk eksternal yang belum
        # terpasang). Kegagalan itu dibuat **berisik tapi terbaca**: `GalatCadangan` yang menyebut
        # folder tujuannya, bukan traceback `OSError` — sebab jalur jendela (aksi #19c) hanya bisa
        # menampilkan kegagalan sebagai kalimat yang bisa dikerjakan pengguna.
        sasaran.mkdir(parents=True, exist_ok=True)
        sementara = Path(tempfile.mkdtemp(prefix=".cadangan-", dir=sasaran))
        berkas_db = sementara / NAMA_DB
        # VACUUM INTO aman terhadap WAL dan menghasilkan satu berkas SQLite mandiri.
        sambungan.execute("VACUUM INTO ?", (str(berkas_db),))
        if (sumber / "konfigurasi").exists():
            shutil.copytree(sumber / "konfigurasi", sementara / "konfigurasi")
        if (sumber / "arsip-snapshot").exists():
            shutil.copytree(
                sumber / "arsip-snapshot",
                sementara / "arsip-snapshot",
                copy_function=_tautkan_atau_salin,
            )
        manifest = {
            "format": 1,
            "dibuat_pada": (sekarang or datetime.now().astimezone()).astimezone().isoformat(),
            "versi_skema": int(sambungan.execute("PRAGMA user_version").fetchone()[0]),
            "cakupan": ["basis_data", "konfigurasi", "arsip-snapshot"],
        }
        (sementara / NAMA_MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        sementara.rename(hasil)
        daftar_terbaru = sorted(
            (p for p in sasaran.iterdir() if p.is_dir() and (p / NAMA_MANIFEST).is_file()),
            key=lambda p: p.name,
            reverse=True,
        )
        for usang in daftar_terbaru[retensi:]:
            shutil.rmtree(usang)
        return hasil
    except (OSError, sqlite3.Error, shutil.Error) as galat:
        if sementara is not None and sementara.exists():
            shutil.rmtree(sementara, ignore_errors=False)
        raise GalatCadangan(
            f"gagal membuat cadangan di '{sasaran}': {galat}. Periksa bahwa folder itu bisa "
            f"ditulis, atau arahkan --folder-cadangan / {ENV_FOLDER_CADANGAN} ke folder lain."
        ) from galat


def _tautkan_atau_salin(asal: str, tujuan: str) -> str:
    """Tautkan berkas arsip (hardlink); salin bila sistem berkas menolak tautan (K92).

    Aman karena arsip snapshot **tidak pernah ditimpa di tempat** (`arsip.py` aturan 1–2: tulis ke
    berkas sementara lalu `os.replace`). Penggantian membuat berkas baru, jadi isi yang dipegang
    cadangan tidak ikut berubah; menghapus folder data pun tidak menghapusnya. Konfigurasi tetap
    disalin, sebab berkas itu boleh disunting tangan di tempat.
    """
    try:
        os.link(asal, tujuan)
    except OSError:
        # Cadangan di disk lain, atau sistem berkas tanpa hardlink: salinan penuh tetap benar.
        shutil.copy2(asal, tujuan)
    return tujuan


@dataclass(frozen=True)
class HasilRapikan:
    ditautkan: int
    byte_dihemat: int

    def ringkas(self) -> str:
        if not self.ditautkan:
            return "tidak ada salinan arsip ganda di cadangan"
        return (
            f"{self.ditautkan} berkas arsip di cadangan diganti tautan ke arsip yang sama persis "
            f"(±{self.byte_dihemat / 1_000_000:,.0f} MB dihemat)".replace(",", ".")
        )


def rapikan_arsip(folder: Path | None = None, *, folder_data: Path | None = None) -> HasilRapikan:
    """Ganti salinan arsip di cadangan lama dengan tautan ke arsip folder data (K92).

    Hanya berkas yang isinya **sama persis byte demi byte** dengan berkas di jalur yang sama di
    folder data yang ditautkan; yang berbeda atau tidak ada pasangannya dibiarkan. Penggantian
    atomik (tautan sementara lalu `os.replace`), jadi cadangan tidak pernah kehilangan berkasnya.
    """
    sumber = (folder_data or lokasi.folder_data()) / "arsip-snapshot"
    ditautkan = 0
    dihemat = 0
    if not sumber.exists():
        return HasilRapikan(0, 0)
    for satu in daftar(folder or folder_tujuan(folder_data)):
        arsip_cadangan = satu / "arsip-snapshot"
        if not arsip_cadangan.exists():
            continue
        for berkas in (p for p in arsip_cadangan.rglob("*") if p.is_file()):
            asli = sumber / berkas.relative_to(arsip_cadangan)
            if not asli.is_file() or asli.samefile(berkas):
                continue
            ukuran = berkas.stat().st_size
            if asli.stat().st_size != ukuran or not filecmp.cmp(asli, berkas, shallow=False):
                continue
            sementara = berkas.with_name(berkas.name + ".tautan")
            try:
                os.link(asli, sementara)
                os.replace(sementara, berkas)
            except OSError as galat:
                if sementara.exists():
                    sementara.unlink()
                raise GalatCadangan(f"gagal merapikan arsip di cadangan '{satu}': {galat}") from galat
            ditautkan += 1
            dihemat += ukuran
    return HasilRapikan(ditautkan, dihemat)


def daftar(folder: Path | None = None) -> tuple[Path, ...]:
    """Daftar cadangan tervalidasi paling baru lebih dulu."""
    akar = folder or folder_bawaan()
    if not akar.exists():
        return ()
    return tuple(sorted((p for p in akar.iterdir() if p.is_dir() and (p / NAMA_MANIFEST).is_file()), key=lambda p: p.name, reverse=True))


def ringkas_daftar(folder: Path | None = None) -> str:
    """Daftar cadangan sebagai teks — **satu** tempat untuk baris perintah dan jendela.

    Dipakai `--daftar-cadangan` **dan** menu Berkas → "Daftar cadangan" (aksi #19c), jadi daftar
    di jendela tidak bisa berbeda dari keluaran baris perintah: keduanya memanggil fungsi ini.
    Isinya sengaja hanya jalur folder, satu per baris.
    """
    isi = daftar(folder)
    if not isi:
        return "Belum ada cadangan."
    return "\n".join(str(satu) for satu in isi)


def pulihkan(
    cadangan: Path,
    *,
    folder_data: Path | None = None,
) -> None:
    """Pulihkan satu cadangan tervalidasi; simpan keadaan lama untuk rollback."""
    tujuan = folder_data or lokasi.folder_data()
    sumber = cadangan.resolve()
    manifest_path = sumber / NAMA_MANIFEST
    db_sumber = sumber / NAMA_DB
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != 1 or not db_sumber.is_file():
            raise ValueError("format cadangan tidak dikenal atau basis data tidak ada")
        with sqlite3.connect(f"file:{db_sumber.as_posix()}?mode=ro", uri=True) as uji:
            hasil_integritas = uji.execute("PRAGMA integrity_check").fetchone()[0]
            if hasil_integritas != "ok":
                raise ValueError(f"integritas basis data gagal: {hasil_integritas}")
        lokasi.pastikan_folder(tujuan)
        staging = Path(tempfile.mkdtemp(prefix=".pulihkan-", dir=tujuan.parent))
        lama = staging / "lama"
        baru = staging / "baru"
        baru.mkdir()
        shutil.copy2(db_sumber, baru / NAMA_DB)
        for nama in ("konfigurasi", "arsip-snapshot"):
            asal = sumber / nama
            if asal.exists():
                shutil.copytree(asal, baru / nama)
        sudah_ada = tujuan.exists()
        try:
            if sudah_ada:
                tujuan.rename(lama)
            baru.rename(tujuan)
        except OSError:
            if lama.exists() and not tujuan.exists():
                lama.rename(tujuan)
            raise
        shutil.rmtree(staging)
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError, shutil.Error) as galat:
        raise GalatCadangan(f"gagal memulihkan cadangan '{cadangan}': {galat}") from galat
