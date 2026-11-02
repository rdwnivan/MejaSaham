"""Isian formulir web → `layar.tulis.PermintaanTulis` (K91 tahap B).

Berkas ini hanya **menerjemahkan** isian teks menjadi argumen `permintaan_*` — seluruh aturan
kelengkapan dan ringkasan konfirmasi tetap di `mejasaham/layar/tulis.py`, sama dengan jendela,
dan penulisannya lewat fungsi inti yang sama dengan baris perintah.

Yang dipilih dari daftar (posisi, rencana, transaksi, baris right issue) dikirim formulir
sebagai **id**, lalu dicari ulang di basis data saat permintaan disusun: pilihan yang sudah
tidak ada ditolak dengan pesan, bukan diganti entri lain (K64/T71 a).
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from mejasaham import jurnal, posisi
from mejasaham.layar import tulis


class GalatIsian(tulis.GalatTulis):
    """Isian formulir yang salah bentuk; pesannya untuk manusia."""


def int_atau_none(teks: str | None, sebutan: str) -> int | None:
    """Isian kosong berarti "tidak diisi" — **bukan** nol (aturan keras 2)."""
    bersih = (teks or "").strip().replace(".", "").replace(",", "")
    if not bersih:
        return None
    try:
        return int(bersih)
    except ValueError as galat:
        raise GalatIsian(
            f"{sebutan} harus berupa angka bulat, bukan {teks!r}. Kosongkan bila memang tidak "
            "diisi — jangan tulis 0."
        ) from galat


def tanggal_atau_none(teks: str | None, sebutan: str) -> date | None:
    """Tanggal ISO; kosong berarti "tidak diisi", bukan hari ini."""
    bersih = (teks or "").strip()
    if not bersih:
        return None
    try:
        return date.fromisoformat(bersih)
    except ValueError as galat:
        raise GalatIsian(
            f"{sebutan} menerima tanggal ISO (YYYY-MM-DD), bukan {bersih!r}. Contoh: 2026-10-17."
        ) from galat


def teks_atau_none(teks: str | None) -> str | None:
    bersih = (teks or "").strip()
    return bersih or None


# ---------------------------------------------------------------------------------------
# Satu fungsi per tindakan tulis
# ---------------------------------------------------------------------------------------


def ubah_stop(s: sqlite3.Connection, isian: dict[str, str]) -> tulis.PermintaanTulis:
    id_posisi = int_atau_none(isian.get("id_posisi"), "Posisi")
    sasaran = None
    if id_posisi is not None:
        aktif = posisi.ringkasan_semua(s, status="aktif")
        sasaran = next((r.posisi for r in aktif if r.posisi.id_posisi == id_posisi), None)
        if sasaran is None:
            raise GalatIsian(
                f"Posisi #{id_posisi} tidak lagi aktif — muat ulang dasbor dan pilih lagi."
            )
    return tulis.permintaan_ubah_stop(
        sasaran=sasaran,
        stop=int_atau_none(isian.get("stop"), "Stop baru"),
        alasan=isian.get("alasan", ""),
        tanggal=tanggal_atau_none(isian.get("tanggal"), "Tanggal"),
    )


def catat_transaksi(s: sqlite3.Connection, isian: dict[str, str]) -> tulis.PermintaanTulis:
    del s  # id rencana/posisi diperiksa inti yang sama dengan baris perintah
    return tulis.permintaan_catat_transaksi(
        kode=isian.get("kode", ""),
        aksi=isian.get("aksi", ""),
        lembar=int_atau_none(isian.get("lembar"), "Lembar"),
        harga=int_atau_none(isian.get("harga"), "Harga"),
        mode=isian.get("mode", ""),
        tanggal=tanggal_atau_none(isian.get("tanggal"), "Tanggal"),
        id_rencana=int_atau_none(isian.get("id_rencana"), "Rencana"),
        id_posisi=int_atau_none(isian.get("id_posisi"), "Posisi"),
        biaya=int_atau_none(isian.get("biaya"), "Biaya"),
        catatan=teks_atau_none(isian.get("catatan")),
    )


def keputusan_right_issue(s: sqlite3.Connection, isian: dict[str, str]) -> tulis.PermintaanTulis:
    """`hak` dikirim sebagai `id_posisi|tanggal_aksi` — satu peristiwa, bukan angka yang diketik."""
    kode = (isian.get("kode") or "").strip().upper()
    pilihan = (isian.get("hak") or "").strip()
    if not pilihan:
        raise GalatIsian(
            "Pilih satu baris right issue lebih dulu — keputusannya menempel pada satu peristiwa "
            "(kode × tanggal aksi), dan dasbor ini tidak memilihkan barisnya."
        )
    try:
        teks_posisi, teks_tanggal = pilihan.split("|", 1)
        id_posisi, tanggal_aksi = int(teks_posisi), date.fromisoformat(teks_tanggal)
    except ValueError as galat:
        raise GalatIsian(f"Pilihan right issue tidak dikenali: {pilihan!r}") from galat
    aktif = posisi.ringkasan_semua(s, status="aktif", kode=kode)
    hak = next(
        (
            satu
            for satu in posisi.hak_right_issue(s, kode=kode, ringkasan_posisi=aktif)
            if satu.id_posisi == id_posisi and satu.tanggal_aksi == tanggal_aksi
        ),
        None,
    )
    if hak is None:
        raise GalatIsian("Baris right issue itu tidak ada lagi — muat ulang halaman dan pilih lagi.")
    id_transaksi = int_atau_none(isian.get("id_transaksi"), "Transaksi")
    transaksi = None
    if id_transaksi is not None:
        transaksi = next(
            (t for t in posisi.daftar_transaksi(s, id_posisi=id_posisi) if t.id_transaksi == id_transaksi),
            None,
        )
        if transaksi is None:
            raise GalatIsian(
                f"Transaksi #{id_transaksi} bukan milik posisi #{id_posisi} — pilih dari daftarnya."
            )
    return tulis.permintaan_keputusan_right_issue(
        hak=hak,
        keputusan=isian.get("keputusan", ""),
        id_transaksi=None if transaksi is None else transaksi.id_transaksi,
        ringkas_transaksi=None if transaksi is None else transaksi.ringkas(),
        lembar=int_atau_none(isian.get("lembar"), "Lembar hak"),
        harga=int_atau_none(isian.get("harga"), "Harga jual hak"),
        biaya=int_atau_none(isian.get("biaya"), "Biaya"),
        catatan=isian.get("catatan", ""),
    )


def catat_jurnal(s: sqlite3.Connection, isian: dict[str, str]) -> tulis.PermintaanTulis:
    id_transaksi = int_atau_none(isian.get("id_transaksi"), "Transaksi")
    if id_transaksi is None:
        raise GalatIsian(
            "Pilih satu keputusan lebih dulu — catatan jurnal menempel pada satu transaksi "
            "(PRD 9.8), dan dasbor ini tidak memilihkan barisnya."
        )
    baris = next(
        (b for b in jurnal.rekap(s).keputusan if b.transaksi.id_transaksi == id_transaksi), None
    )
    if baris is None:
        raise GalatIsian(f"Transaksi #{id_transaksi} tidak ada di jurnal.")
    return tulis.permintaan_catat_jurnal(
        id_transaksi=id_transaksi,
        ringkas_transaksi=baris.ringkas(),
        alasan=isian.get("alasan", ""),
        pelajaran=isian.get("pelajaran", ""),
        tanggal_tinjau=tanggal_atau_none(isian.get("tanggal_tinjau"), "Tanggal tinjau"),
        tandai_selesai=bool(isian.get("selesai")),
        tanggal_selesai=tanggal_atau_none(isian.get("tanggal_selesai"), "Tanggal selesai"),
    )


def impor(isian: dict[str, str]) -> tulis.PermintaanTulis:
    """Dua tahap seperti jendela: folder dibaca dulu, ringkasannya memuat jumlah baris (K59 c)."""
    folder = (isian.get("folder") or "").strip().strip('"')
    if not folder:
        raise GalatIsian("Folder impor belum diisi.")
    jalur = Path(folder)
    if not jalur.is_dir():
        raise GalatIsian(f"Folder '{jalur}' tidak ada atau bukan folder.")
    return tulis.permintaan_impor(pembacaan=tulis.baca_folder_impor(jalur))


def cadangan() -> tulis.PermintaanTulis:
    return tulis.permintaan_cadangan()
