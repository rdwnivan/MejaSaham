"""Pembaruan data harian dalam satu langkah — tombol "Perbarui data" di dasbor (K92).

Urutannya sama dengan `--refresh --saring` di baris perintah: ambil harga → snapshot + laporan
mutu + arsip (`pengatur.jalankan_refresh`) → cadangan F12 → rapikan cadangan → saringan tersimpan
(`pengatur.jalankan_saring`). Berkas ini hanya merangkai fungsi inti yang sudah ada; ia tidak
mengimpor UI (aturan keras 5), jadi baris perintah dan dasbor memakai jalur yang sama.

Dua janji yang dijaga:

1. **"Sudah terbaru" diputuskan dari data, bukan dari jam.** Snapshot terbaru dibandingkan dengan
   hari bursa terakhir menurut kalender bursa (`mutu.hari_bursa_terakhir`, U5) — jawaban yang
   sama dengan peringatan AC-8 di dasbor. Tidak ada jam tutup bursa yang dikarang di sini
   (aturan keras 1).
2. **Kemajuan terlihat per emiten.** `lapor` menerima `Kemajuan` setiap kali tahapnya berubah dan
   setiap emiten selesai diambil, supaya pembaruan ±20 menit tidak terlihat menggantung.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mejasaham import cadangan, db, lokasi, mutu, pengatur, saring

#: Tahap pembaruan, urut. Dipakai halaman kemajuan untuk menyebut "tahap 2 dari 5".
#: Notasi, suspensi, dan UMA IDX **tidak** diambil di sini: Syarat Penggunaan IDX melarang web
#: scraping, jadi berkasnya diunduh pengguna lalu diimpor (K96, mencabut bagian otomatis K94).
MENGAMBIL = "mengambil harga"
MENULIS = "menulis snapshot, laporan mutu, dan arsip"
MENCADANGKAN = "membuat cadangan"
MERAPIKAN = "merapikan cadangan lama"
MENYARING = "menjalankan saringan"
TAHAP = (MENGAMBIL, MENULIS, MENCADANGKAN, MERAPIKAN, MENYARING)


@dataclass(frozen=True)
class Keadaan:
    """Apakah snapshot terbaru sudah dari hari bursa terakhir."""

    id_snapshot: int | None
    tanggal_data: str | None
    hari_bursa_terakhir: str | None

    @property
    def terbaru(self) -> bool:
        """Sama dengan kebalikan `Dasbor.snapshot_basi` (AC-8).

        Kalender kosong berarti "tidak bisa dinilai", dan itu **tidak** dianggap terbaru: lebih
        baik menawarkan pembaruan daripada menyatakan data terkini tanpa dasar.
        """
        if self.tanggal_data is None or self.hari_bursa_terakhir is None:
            return False
        return self.tanggal_data >= self.hari_bursa_terakhir


def keadaan(sambungan: sqlite3.Connection, momen: date | None = None) -> Keadaan:
    baris = sambungan.execute(
        "SELECT id_snapshot, tanggal_data FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()
    return Keadaan(
        id_snapshot=baris[0] if baris else None,
        tanggal_data=baris[1] if baris else None,
        hari_bursa_terakhir=mutu.hari_bursa_terakhir(sambungan, momen or date.today()),
    )


@dataclass(frozen=True)
class Kemajuan:
    tahap: str
    nomor: int = 0
    dari: int = 0
    kode: str = ""
    gagal: int = 0

    @property
    def urutan_tahap(self) -> int:
        return TAHAP.index(self.tahap) + 1


@dataclass(frozen=True)
class HasilPembaruan:
    refresh: pengatur.LaporanJalan
    cadangan: Path | None = None
    rapikan: cadangan.HasilRapikan | None = None
    saring: pengatur.LaporanSaring | None = None
    #: Galat sesudah snapshot tersimpan (cadangan/rapikan/saringan) — snapshotnya tetap sah.
    galat_lanjutan: str | None = None

    @property
    def berhasil(self) -> bool:
        return self.refresh.sukses and self.galat_lanjutan is None

    def ringkas(self) -> str:
        bagian = [self.refresh.ringkas()]
        if self.cadangan is not None:
            bagian.append(f"Cadangan F12: {self.cadangan}")
        if self.rapikan is not None:
            bagian.append(f"Rapikan cadangan: {self.rapikan.ringkas()}")
        if self.saring is not None:
            bagian.append(self.saring.ringkas())
        if self.galat_lanjutan is not None:
            bagian.append(f"GAGAL sesudah snapshot tersimpan: {self.galat_lanjutan}")
        return "\n".join(bagian)


def lapor_per_emiten(lapor: Callable[[Kemajuan], None]) -> Callable[[object], None]:
    """Penerjemah `pengambil.Kemajuan` (satu emiten) menjadi `Kemajuan` tahap pengambilan.

    Jumlah gagal dihitung di sini, supaya halaman kemajuan menyebutnya selagi berjalan — bukan
    baru di ringkasan akhir (aturan keras 7).
    """
    gagal = 0

    def terima(satu: object) -> None:
        nonlocal gagal
        if getattr(satu, "galat", None):
            gagal += 1
        lapor(
            Kemajuan(
                MENGAMBIL,
                nomor=getattr(satu, "nomor", 0),
                dari=getattr(satu, "dari", 0),
                kode=getattr(satu, "kode", ""),
                gagal=gagal,
            )
        )

    return terima


def cadangkan_dan_rapikan(
    *, tujuan: Path | None = None, lapor: Callable[[Kemajuan], None] | None = None
) -> tuple[Path, cadangan.HasilRapikan]:
    """Cadangan F12 sesudah refresh berhasil, lalu salinan arsip ganda di cadangan lama ditautkan.

    Satu fungsi untuk `--refresh` dan tombol dasbor, supaya keduanya tidak bisa berbeda soal apa
    yang terjadi sesudah snapshot terbit. Melempar `GalatCadangan`/`GalatBasisData`/`GalatLokasi`.
    """
    if lapor is not None:
        lapor(Kemajuan(MENCADANGKAN))
    sambungan = db.hubungkan()
    try:
        hasil = cadangan.buat(sambungan, folder_data=lokasi.folder_data(), tujuan=tujuan)
    finally:
        sambungan.close()
    if lapor is not None:
        lapor(Kemajuan(MERAPIKAN))
    rapikan = cadangan.rapikan_arsip(hasil.parent, folder_data=lokasi.folder_data())
    return hasil, rapikan


def jalankan(
    pengambil_data: pengatur.SumberData,
    *,
    lapor: Callable[[Kemajuan], None],
    tujuan_cadangan: Path | None = None,
) -> HasilPembaruan:
    """Refresh → cadangan → rapikan → saringan tersimpan.

    `pengambil_data` harus sudah memanggil `lapor` per emiten (lihat `PengambilYFinance(laporan=…)`);
    berkas ini hanya melaporkan perpindahan tahap. Pemanggil yang memeriksa `keadaan`.
    """
    lapor(Kemajuan(MENGAMBIL))
    sambungan = db.siapkan()
    try:
        refresh = pengatur.jalankan_refresh(sambungan, _PengambilBertahap(pengambil_data, lapor))
    finally:
        sambungan.close()
    if not refresh.sukses:
        return HasilPembaruan(refresh=refresh)

    try:
        hasil_cadangan, rapikan = cadangkan_dan_rapikan(tujuan=tujuan_cadangan, lapor=lapor)
    except (cadangan.GalatCadangan, db.GalatBasisData, lokasi.GalatLokasi) as galat:
        return HasilPembaruan(refresh=refresh, galat_lanjutan=f"cadangan F12 gagal: {galat}")

    lapor(Kemajuan(MENYARING))
    sambungan = db.siapkan()
    try:
        pengatur.siapkan_preset_bawaan(sambungan)
        laporan_saring = pengatur.jalankan_saring(
            sambungan, saring.preset_terbaru(sambungan, "kualitas-nilai"), simpan=True
        )
    finally:
        sambungan.close()
    return HasilPembaruan(
        refresh=refresh,
        cadangan=hasil_cadangan,
        rapikan=rapikan,
        saring=laporan_saring,
    )


class _PengambilBertahap:
    """Bungkus pengambil: begitu pengambilan selesai, tahap berpindah ke "menulis".

    Penulisan snapshot + laporan mutu + arsip memakan ±1 menit pada data kerja; tanpa perpindahan
    ini halaman kemajuan akan diam di "973 dari 973" seolah menggantung.
    """

    def __init__(self, asli: pengatur.SumberData, lapor: Callable[[Kemajuan], None]) -> None:
        self._asli = asli
        self._lapor = lapor

    def __getattr__(self, nama: str) -> object:
        return getattr(self._asli, nama)

    def ambil(self, emiten):  # type: ignore[no-untyped-def]
        hasil = self._asli.ambil(emiten)
        self._lapor(Kemajuan(MENULIS))
        return hasil
