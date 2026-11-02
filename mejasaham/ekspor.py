"""Ekspor laporan F9 sebagai CSV yang dapat dibuka di Excel (PRD 9.10, U11)."""

from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path
from typing import Sequence

from mejasaham import __version__, arsip, jurnal, kandidat, potret, risiko
from mejasaham import db

PERNYATAAN_BUKAN_NASIAT = "Isi berkas ini bukan nasihat investasi."
JENIS_EKSPOR = ("hasil-saring", "watchlist", "rencana", "jurnal", "mutu")


class GalatEkspor(RuntimeError):
    """Kesalahan ekspor dengan pesan yang bisa ditindaklanjuti pengguna."""


@dataclass(frozen=True)
class HasilEkspor:
    jalur: Path
    jumlah_baris: int
    id_snapshot: int
    id_preset: str


def _aman_kepala(nilai: object) -> str:
    """Jaga metadata satu baris agar label sumber tidak menggeser kolom CSV."""
    return str(nilai).replace(";", ",").replace("\r", " ").replace("\n", " ")


def _konteks(
    sambungan: sqlite3.Connection, id_preset: str | None
) -> tuple[sqlite3.Row, sqlite3.Row]:
    snapshot = sambungan.execute(
        "SELECT * FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()
    if snapshot is None:
        raise GalatEkspor("belum ada snapshot; jalankan --refresh sebelum mengekspor")

    if id_preset is None:
        baris_preset = sambungan.execute(
            "SELECT p.* FROM skor s JOIN preset_saring p USING (id_preset) "
            "WHERE s.id_snapshot = ? ORDER BY s.dihitung_pada DESC, p.id_preset LIMIT 1",
            (snapshot["id_snapshot"],),
        ).fetchone()
    else:
        baris_preset = sambungan.execute(
            "SELECT p.* FROM preset_saring p WHERE p.id_preset = ? AND EXISTS "
            "(SELECT 1 FROM skor s WHERE s.id_snapshot = ? AND s.id_preset = p.id_preset)",
            (id_preset, snapshot["id_snapshot"]),
        ).fetchone()
    if baris_preset is None:
        raise GalatEkspor(
            "tidak ada preset yang sudah diberi skor pada snapshot terakhir; jalankan --saring "
            "lebih dulu atau pilih --preset yang tersedia pada snapshot itu"
        )
    return snapshot, baris_preset


def _baris(
    sambungan: sqlite3.Connection, jenis: str, id_snapshot: int, id_preset: str
) -> tuple[tuple[str, ...], list[Sequence[object]]]:
    if jenis == "hasil-saring":
        kolom = (
            "kode", "peringkat", "skor_kualitas_bp", "skor_nilai_bp", "skor_momentum_bp",
            "skor_volatilitas_bp", "skor_total_bp", "versi_hitung", "penjelasan",
        )
        data = sambungan.execute(
            "SELECT " + ", ".join(kolom) + " FROM skor WHERE id_snapshot = ? AND id_preset = ? "
            "ORDER BY peringkat IS NULL, peringkat, kode",
            (id_snapshot, id_preset),
        ).fetchall()
        return kolom, [tuple(satu) for satu in data]

    if jenis == "watchlist":
        kolom = (
            "id_kandidat", "revisi", "kode", "status", "tesis", "pembatal_fundamental",
            "harga_pembatal", "horizon", "target", "stop_awal", "tanggal_tinjau",
            "alasan_dibuang", "dicatat_pada",
        )
        data = kandidat.daftar(sambungan, status="watchlist")
        return kolom, [tuple(getattr(satu, nama) for nama in kolom) for satu in data]

    if jenis == "rencana":
        kolom = tuple(satu.name for satu in fields(risiko.Rencana))
        data = risiko.daftar(sambungan)
        return kolom, [tuple(getattr(satu, nama) for nama in kolom) for satu in data]

    if jenis == "jurnal":
        kolom = (
            "id_transaksi", "tanggal", "kode", "aksi", "lembar", "harga", "mode",
            "id_rencana", "patuh", "kode_pelanggaran", "alasan", "pelajaran",
            "tanggal_tinjau", "selesai_pada",
        )
        data = jurnal.baris(sambungan)
        hasil = []
        for satu in data:
            t = satu.transaksi
            c = satu.catatan
            hasil.append((
                t.id_transaksi, t.tanggal, t.kode, t.aksi, t.lembar, t.harga, t.mode,
                t.id_rencana, "ya" if satu.patuh else "tidak",
                ",".join(satu.kode_pelanggaran), c.alasan if c else None,
                c.pelajaran if c else None, c.tanggal_tinjau if c else None,
                c.selesai_pada if c else None,
            ))
        return kolom, hasil

    if jenis == "mutu":
        folder = arsip.folder_arsip(snapshot_tanggal(sambungan, id_snapshot), id_snapshot)
        sumber = folder / arsip.NAMA_MUTU
        if not sumber.is_file():
            raise GalatEkspor(
                f"laporan mutu untuk snapshot {id_snapshot} tidak ditemukan di '{sumber}'; "
                "laporan ini hanya bisa diekspor dari arsip snapshot yang sudah tersimpan"
            )
        baris_csv = list(
            csv.reader(sumber.read_text(encoding="utf-8-sig").splitlines(), delimiter=";")
        )
        nomor_kepala = next(
            (
                i
                for i, baris in enumerate(baris_csv)
                if baris[:4] == ["tingkat", "jenis", "kode", "keterangan"]
            ),
            None,
        )
        if nomor_kepala is None:
            raise GalatEkspor(f"format laporan mutu '{sumber}' tidak dikenali")
        return tuple(baris_csv[nomor_kepala]), [
            baris for baris in baris_csv[nomor_kepala + 1 :] if baris
        ]

    raise GalatEkspor(f"jenis ekspor {jenis!r} tidak dikenal; pilih: {', '.join(JENIS_EKSPOR)}")


def snapshot_tanggal(sambungan: sqlite3.Connection, id_snapshot: int) -> date:
    baris = sambungan.execute(
        "SELECT tanggal_data FROM snapshot WHERE id_snapshot = ?", (id_snapshot,)
    ).fetchone()
    if baris is None:
        raise GalatEkspor(f"snapshot {id_snapshot} tidak ditemukan")
    return date.fromisoformat(baris["tanggal_data"])


def ekspor(
    sambungan: sqlite3.Connection,
    jenis: str,
    tujuan: Path,
    *,
    id_preset: str | None = None,
) -> HasilEkspor:
    """Tulis satu CSV atomik, tanpa menimpa berkas tujuan yang sudah ada."""
    if jenis not in JENIS_EKSPOR:
        raise GalatEkspor(f"jenis ekspor harus salah satu dari: {', '.join(JENIS_EKSPOR)}")
    snapshot, preset = _konteks(sambungan, id_preset)
    tujuan = Path(tujuan)
    if tujuan.suffix.lower() != ".csv":
        raise GalatEkspor("berkas ekspor harus memakai akhiran .csv")
    if tujuan.exists():
        raise GalatEkspor(f"berkas '{tujuan}' sudah ada; pilih nama lain agar ekspor lama tetap utuh")
    try:
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        kolom, data = _baris(sambungan, jenis, snapshot["id_snapshot"], preset["id_preset"])
        kepala = (
            f"# jenis_ekspor;{jenis}\n"
            f"# id_snapshot;{snapshot['id_snapshot']}\n"
            f"# tanggal_data;{snapshot['tanggal_data']}\n"
            f"# id_preset;{preset['id_preset']}\n"
            f"# versi_preset;{preset['versi']}\n"
            f"# dibuat_pada;{db.waktu_iso()}\n"
            f"# versi_aplikasi;{__version__}\n"
        )
        pilihan = potret.harga_dipakai(sambungan, batas=snapshot["batas_diketahui"])
        sumber = pilihan.label if pilihan is not None else None
        kepala += f"# sumber_harga;{_aman_kepala(sumber or '(belum ada data harga)')}\n"
        if sumber is not None and "tidak resmi" in sumber.lower():
            kepala += f"# PERINGATAN;{arsip.PERNYATAAN_SUMBER_TIDAK_RESMI}\n"
        kepala += f"# {PERNYATAAN_BUKAN_NASIAT} (PRD 9.10)\n"
        fd, nama_tmp = tempfile.mkstemp(prefix=f".{tujuan.name}.", suffix=".tmp", dir=tujuan.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as berkas:
                berkas.write(kepala)
                penulis = csv.writer(berkas, delimiter=";", lineterminator="\n")
                penulis.writerow(kolom)
                penulis.writerows(data)
                berkas.flush()
                os.fsync(berkas.fileno())
            # Windows rename atomik dan menolak tujuan yang sudah ada. POSIX perlu
            # hard link agar publikasi atomik juga tidak mengganti tujuan yang muncul
            # setelah pemeriksaan exists() di atas.
            if os.name == "nt":
                os.rename(nama_tmp, tujuan)
            else:
                os.link(nama_tmp, tujuan)
        finally:
            Path(nama_tmp).unlink(missing_ok=True)
    except OSError as galat:
        raise GalatEkspor(f"gagal menulis ekspor ke '{tujuan}': {galat}") from galat
    return HasilEkspor(Path(tujuan), len(data), int(snapshot["id_snapshot"]), preset["id_preset"])
