"""Lapisan SQLite: WAL, `busy_timeout`, penulis tunggal, dan migrasi berversi (T1, T9, A2, A6).

Empat aturan yang ditegakkan berkas ini, bukan sekadar didokumentasikan:

1. **A2 / AC-19 — penulis tunggal.** Setiap penulisan melewati `tulis()`, yang membuka
   transaksi dengan `BEGIN IMMEDIATE`. Kunci tulis diambil **di muka**, sehingga proses kedua
   menunggu di `busy_timeout` dan berhenti dengan pesan jelas, bukan gagal di tengah jalan
   setelah sebagian data tertulis.
2. **A6 — tulis atomik.** Satu blok `tulis()` = satu transaksi: semua berhasil atau tidak
   sama sekali.
3. **T9 — skema berversi.** `PRAGMA user_version` menyimpan versi terpasang; migrasi
   dijalankan berurutan dan setiap migrasi berjalan di dalam satu transaksi tersendiri.
4. **Gagal itu berisik.** Tidak ada `except: pass`; setiap kegagalan SQLite dinaikkan ulang
   dengan konteks (versi berapa, berkas mana).

Catatan operator: `PRAGMA foreign_keys` **wajib** dinyalakan per koneksi (SQLite mematikannya
secara bawaan), jadi koneksi tidak boleh dibuat lewat `sqlite3.connect()` langsung di tempat
lain — pakailah `hubungkan()`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time
from pathlib import Path

from mejasaham import lokasi
from mejasaham.skema import MIGRASI, VERSI_TERBARU

# 5 detik: cukup untuk refresh harian yang menulis beberapa ribu baris, tetapi tidak
# membuat mode jendela menggantung tanpa batas ketika proses lain sedang menulis.
BUSY_TIMEOUT_MS = 5000

#: Kalimat **bersama** untuk keadaan "kunci tulis dipegang proses lain" (A2/AC-19, K59).
#: Dipakai `tulis()` di bawah, jadi mode jendela dan mode kepala tidak bisa menjelaskan
#: keadaan yang sama dengan dua kalimat berbeda. Yang **tidak** ikut di sini: kalimat khusus
#: jendela ("Jendela belum menulis apa pun") — itu urusan pemanggil yang memang menulis dari
#: jendela, dan tempatnya `mejasaham/layar/tulis.py`.
KALIMAT_TERKUNCI = (
    "Basis data sedang ditulis proses lain (mis. --refresh atau saringan yang sedang berjalan). "
    "Tunggu sampai proses itu selesai, lalu coba lagi."
)


class GalatBasisData(RuntimeError):
    """Kegagalan lapisan basis data yang sudah diberi konteks bahasa Indonesia."""


class SkemaTerlaluBaru(GalatBasisData):
    """Basis data dibuat versi aplikasi yang lebih baru daripada kode yang berjalan.

    Ditolak, bukan "dipaksa turun": menjalankan kode lama di atas skema baru bisa
    menghilangkan kolom yang sudah dipakai (A8, PRD 9.13).
    """


class BasisDataTerkunci(GalatBasisData):
    """Kunci tulis sedang dipegang proses lain, dan `busy_timeout` sudah habis ditunggu.

    Dibedakan dari galat basis data lain karena **satu** hal yang bisa dikerjakan pengguna:
    menunggu proses lain selesai lalu mencoba lagi. Karena itu pesannya juga dipakai bersama:
    `KALIMAT_TERKUNCI` adalah satu-satunya sumber kalimatnya, supaya mode jendela dan mode
    kepala tidak pernah menjelaskan keadaan yang sama dengan dua kalimat berbeda (A2/AC-19).
    """


def hubungkan(berkas: Path | str | None = None) -> sqlite3.Connection:
    """Buka koneksi ke basis data dan pasang PRAGMA wajib (T1).

    `berkas` None berarti `%LOCALAPPDATA%\\MejaSaham\\mejasaham.db` (A3).
    """
    jalur = Path(berkas) if berkas is not None else lokasi.berkas_basis_data()
    if jalur.parent and not jalur.parent.exists():
        lokasi.pastikan_folder(jalur.parent)

    try:
        # isolation_level=None mematikan manajemen transaksi implisit modul sqlite3;
        # transaksi dibuka eksplisit di `tulis()` supaya kuncinya bisa diambil di muka.
        sambungan = sqlite3.connect(str(jalur), isolation_level=None, timeout=BUSY_TIMEOUT_MS / 1000)
    except sqlite3.Error as galat:
        raise GalatBasisData(f"gagal membuka basis data {jalur}: {galat}") from galat

    sambungan.row_factory = sqlite3.Row
    try:
        sambungan.execute("PRAGMA journal_mode=WAL")
        sambungan.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        sambungan.execute("PRAGMA foreign_keys=ON")
        # NORMAL aman dipakai bersama WAL: hanya transaksi terakhir yang bisa hilang bila
        # listrik mati, bukan seluruh basis data, dan tulis harian jadi jauh lebih cepat.
        sambungan.execute("PRAGMA synchronous=NORMAL")
        # Temp table di MEMORI, bukan berkas di folder temp sistem. SQLite melimpahkan
        # GROUP BY/ORDER BY besar (mis. rekap sumber atas sejuta baris harga saat mengarsipkan
        # snapshot) ke berkas sementara; bila folder temp tidak bisa ditulis — disk penuh,
        # kebijakan IT, atau proses yang dibatasi — kueri gagal dengan pesan menyesatkan
        # "unable to open database file" **setelah** refresh panjang selesai. Diuji 9 Okt 2026:
        # tanpa pragma ini, `SELECT sumber, COUNT(*) ... GROUP BY sumber` atas 999.421 baris
        # gagal; dengan pragma ini berhasil. Ongkosnya memori: hasil antara disimpan di RAM
        # (puluhan MB untuk sejuta baris), dan itu wajar untuk aplikasi satu pengguna.
        sambungan.execute("PRAGMA temp_store=MEMORY")
    except sqlite3.Error as galat:
        sambungan.close()
        raise GalatBasisData(f"gagal memasang PRAGMA pada {jalur}: {galat}") from galat
    return sambungan


def versi_terpasang(sambungan: sqlite3.Connection) -> int:
    return int(sambungan.execute("PRAGMA user_version").fetchone()[0])


def _siapkan_tabel_jejak(sambungan: sqlite3.Connection) -> None:
    """Tabel catatan migrasi.

    `user_version` saja sudah cukup untuk keputusan, tetapi tidak bisa menjawab "migrasi apa
    yang dijalankan kapan" saat menelusuri masalah di komputer pengguna (AC-9).
    """
    sambungan.execute(
        "CREATE TABLE IF NOT EXISTS migrasi_terpasang ("
        " versi INTEGER PRIMARY KEY,"
        " nama TEXT NOT NULL,"
        " waktu TEXT NOT NULL"
        ")"
    )


def terapkan_migrasi(sambungan: sqlite3.Connection) -> int:
    """Jalankan migrasi yang belum terpasang. Kembalikan versi skema setelah selesai.

    Setiap migrasi berjalan di transaksi sendiri (DDL di SQLite transaksional), jadi
    kegagalan di tengah tidak meninggalkan skema separuh jadi (A6).
    """
    _siapkan_tabel_jejak(sambungan)
    sekarang = versi_terpasang(sambungan)

    if sekarang > VERSI_TERBARU:
        raise SkemaTerlaluBaru(
            f"basis data berversi skema {sekarang}, sedangkan aplikasi ini hanya mengenal "
            f"{VERSI_TERBARU}. Perbarui aplikasi; jangan jalankan versi lama di atas skema baru."
        )

    for migrasi in MIGRASI:
        if migrasi.versi <= sekarang:
            continue
        skrip = (
            "BEGIN IMMEDIATE;\n"
            f"{migrasi.sql}\n"
            f"PRAGMA user_version = {migrasi.versi};\n"
            "COMMIT;"
        )
        try:
            sambungan.executescript(skrip)
        except sqlite3.Error as galat:
            if sambungan.in_transaction:
                sambungan.execute("ROLLBACK")
            raise GalatBasisData(
                f"migrasi {migrasi.versi} ({migrasi.nama}) gagal dan dibatalkan: {galat}"
            ) from galat
        # Tercatat setelah COMMIT: baris jejak tidak boleh ada untuk migrasi yang gagal.
        sambungan.execute(
            "INSERT INTO migrasi_terpasang (versi, nama, waktu) VALUES (?, ?, ?)",
            (migrasi.versi, migrasi.nama, _waktu_sekarang()),
        )
        sekarang = migrasi.versi

    return sekarang


def siapkan(berkas: Path | str | None = None) -> sqlite3.Connection:
    """Buka basis data dan pastikan skemanya mutakhir — satu langkah untuk pemanggil."""
    jalur = Path(berkas) if berkas is not None else lokasi.berkas_basis_data()
    # T9: sebelum skema lama diubah, ambil snapshot konsisten terlebih dahulu. Jangan
    # membuat cadangan untuk basis data baru/kosong; tidak ada keadaan pengguna yang perlu dijaga.
    try:
        ada_basis_data = jalur.is_file() and jalur.stat().st_size > 0
    except OSError as galat:
        raise GalatBasisData(f"gagal memeriksa basis data sebelum migrasi {jalur}: {galat}") from galat
    if ada_basis_data:
        pemeriksa = hubungkan(jalur)
        try:
            versi_lama = versi_terpasang(pemeriksa)
            if versi_lama < VERSI_TERBARU:
                from mejasaham import cadangan

                try:
                    cadangan.buat(pemeriksa, folder_data=jalur.parent)
                except (cadangan.GalatCadangan, lokasi.GalatLokasi) as galat:
                    raise GalatBasisData(
                        f"cadangan sebelum migrasi skema {versi_lama} gagal; migrasi dibatalkan: {galat}"
                    ) from galat
        finally:
            pemeriksa.close()
    sambungan = hubungkan(berkas)
    try:
        terapkan_migrasi(sambungan)
    except BaseException:
        # Koneksi tidak boleh tertinggal terbuka saat penyiapan gagal (mis. skema terlalu baru).
        sambungan.close()
        raise
    return sambungan


def _terkunci(galat: sqlite3.Error) -> bool:
    """Apakah galat SQLite ini berarti "kunci tulis sedang dipegang proses lain"?

    Diperiksa dari pesannya, bukan dari `sqlite3.sqlite_errorcode`: atribut itu baru ada sejak
    Python 3.11 dan tidak selalu terisi dari pustaka SQLite yang dipakai. Yang dicari hanya
    bentuknya (`locked`/`busy`), dan galat lain dilewatkan apa adanya — menerjemahkan galat
    yang bukan tentang kunci akan menyembunyikan sebab yang sebenarnya (aturan keras 7).
    """
    pesan = str(galat).lower()
    return "locked" in pesan or "busy" in pesan


@contextmanager
def tulis(sambungan: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Transaksi tulis eksplisit: `BEGIN IMMEDIATE` → `COMMIT`, atau `ROLLBACK` bila gagal.

    Transaksi bersarang ditolak dengan sengaja: SQLite tidak punya transaksi bersarang, dan
    `BEGIN` kedua akan melempar galat yang membingungkan jauh dari penyebabnya.

    **Kunci yang tidak didapat** diterjemahkan menjadi `BasisDataTerkunci` dengan satu kalimat
    bersama (`KALIMAT_TERKUNCI`), bukan dibiarkan sebagai `sqlite3.OperationalError` mentah:
    kunci diambil di muka (`BEGIN IMMEDIATE`), jadi galat di sini pasti berarti **belum satu
    baris pun tertulis** — dan itu yang bisa dijanjikan ke pemanggil, termasuk jendela (K59).
    """
    if sambungan.in_transaction:
        raise GalatBasisData(
            "transaksi sudah terbuka; transaksi bersarang tidak didukung — "
            "selesaikan blok tulis() terluar lebih dulu"
        )

    try:
        sambungan.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as galat:
        if _terkunci(galat):
            raise BasisDataTerkunci(KALIMAT_TERKUNCI) from galat
        raise
    try:
        yield sambungan
    except BaseException:
        # Galat asli yang penting; kegagalan ROLLBACK di sini hanya bisa terjadi bila
        # koneksinya sendiri sudah rusak, dan koneksi itu memang tidak layak dipakai lagi.
        try:
            sambungan.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    else:
        try:
            sambungan.execute("COMMIT")
        except sqlite3.OperationalError as galat:
            # COMMIT bisa gagal karena kunci (mis. checkpoint WAL) — dan bila gagal, SQLite
            # membatalkan transaksinya sendiri: tetap tidak ada baris yang tertulis.
            try:
                sambungan.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            if _terkunci(galat):
                raise BasisDataTerkunci(KALIMAT_TERKUNCI) from galat
            raise


def waktu_iso(momen: datetime | None = None) -> str:
    """Waktu lokal ISO-8601 dengan offset zona waktu (T12).

    Satu-satunya tempat waktu diubah menjadi teks simpan, supaya jejak `diketahui_pada` di
    tabel data dan `waktu` di `log_jalan` tidak bisa berbeda bentuk. Format Indonesia (U11)
    hanya untuk tampilan/ekspor, bukan penyimpanan.

    Menerima `date` juga, tetapi **hanya** sebagai tengah malam waktu lokal — dipakai ketika
    yang diketahui hanyalah tanggalnya (mis. `dicatat_pada` di berkas rujukan). Kolom
    `diketahui_pada` menuntut bentuk lengkap dengan `T`, jadi tanggal saja tidak cukup dan
    tidak boleh diteruskan apa adanya.
    """
    if momen is None:
        momen = datetime.now().astimezone()
    elif isinstance(momen, date) and not isinstance(momen, datetime):
        momen = datetime.combine(momen, time.min).astimezone()
    return momen.replace(microsecond=0).isoformat()


# Nama lama dipertahankan: sudah dipakai di dalam berkas ini dan tidak perlu ikut berubah.
_waktu_sekarang = waktu_iso
