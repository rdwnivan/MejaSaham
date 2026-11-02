"""Arsip snapshot harian — "arsip dimulai sejak hari pertama pemakaian" (PRD 7.2, Tahap 0).

Alasan berkas ini ada, apa adanya dari PRD: **data point-in-time tidak bisa direkonstruksi
belakangan.** Sumber gratis tidak menyimpan emiten yang sudah delisting, dan sumber tidak resmi
diam-diam menyajikan harga yang sudah disesuaikan hari ini — bukan seperti yang terlihat pada
September lalu. Kalau arsipnya tidak ditulis saat itu, ia tidak akan pernah bisa ditulis lagi.

Tiga aturan yang ditegakkan:

1. **Tulis atomik.** Setiap berkas ditulis ke berkas sementara lalu `os.replace`-nya. Arsip yang
   separuh tertulis lebih berbahaya daripada arsip yang tidak ada: ia tampak lengkap.
2. **Snapshot lama tidak pernah ditimpa.** Setiap `id_snapshot` punya foldernya sendiri, jadi
   memperbaiki data berarti **menambah** arsip, bukan mengganti yang lama (S1) — sama seperti
   basis datanya.
3. **Berkasnya menyebut dirinya sendiri.** Setiap CSV dimulai dengan baris kepala berisi
   `id_snapshot`, tanggal data, batas diketahui, versi skema, dan versi aplikasi, ditutup
   pernyataan "bukan nasihat investasi" (AC-7, aturan keras 8). Arsip yang ditemukan setahun
   lagi harus bisa menjelaskan asalnya tanpa membuka basis data.

Format CSV mengikuti U11: UTF-8 BOM, pemisah `;`, supaya terbaca benar di Excel Indonesia.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mejasaham import db, lokasi
from mejasaham import __version__
from mejasaham.ingesti import GalatIngesti

#: Pernyataan wajib di setiap ekspor (PRD 9.10, aturan keras 8).
PERNYATAAN_BUKAN_NASIAT = "Isi berkas ini bukan nasihat investasi."

#: Sumber data tidak resmi wajib menyatakan hubungannya dengan penyedianya (PRD 7.2, Q8).
#:
#: Kalimat ini bukan formalitas. Pemeriksaan ketentuan pemakaian (dijalankan sebelum Tahap 0
#: dinyatakan selesai, Q8) menemukan bahwa **Syarat Layanan Yahoo melarang pengambilan data
#: secara otomatis untuk tujuan apa pun tanpa izin tertulis sebelumnya, tanpa pengecualian
#: pemakaian pribadi** (Yahoo ToS bagian 2.4, butir akses otomatis). Karena itu label ini
#: ditulis apa adanya: yang dipakai adalah data dari sumber yang tidak memberi izin, dipakai
#: untuk keperluan pribadi, dan berkas ekspor adalah jalur penyebarannya — sehingga setiap
#: berkas yang bisa keluar dari komputer ini harus membawa peringatannya.
PERNYATAAN_SUMBER_TIDAK_RESMI = (
    "Data harga di berkas ini berasal dari sumber TIDAK RESMI (Yahoo Finance lewat yfinance) — "
    "tidak berafiliasi dengan, tidak disponsori, dan tidak diverifikasi Yahoo Inc. "
    "Untuk pemakaian pribadi; JANGAN disebarkan, JANGAN dipakai untuk tujuan komersial. "
    "Ketentuan: https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html"
)

#: Nama berkas di dalam folder arsip.
NAMA_META = "meta.json"
NAMA_MUTU = "laporan-mutu.csv"

#: Bentuk CSV tiap tabel arsip: nama berkas → (kolom, kunci urut).
#:
#: Sengaja **tidak** memakai `SELECT *`: arsip adalah format yang dibaca alat lain, jadi
#: urutan dan nama kolomnya harus tetap sama walaupun tabelnya nanti bertambah kolom.
TABEL_ARSIP: Mapping[str, tuple[str, tuple[str, ...]]] = {
    "harga.csv": (
        "SELECT kode, tanggal, open, high, low, close, volume, nilai, asal_nilai,"
        " open_mentah, high_mentah, low_mentah, close_mentah, volume_mentah, nilai_mentah,"
        " sumber, diketahui_pada FROM v_harga_harian_terkini ORDER BY kode, tanggal",
        (
            "kode",
            "tanggal",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "nilai",
            "asal_nilai",
            "open_mentah",
            "high_mentah",
            "low_mentah",
            "close_mentah",
            "volume_mentah",
            "nilai_mentah",
            "sumber",
            "diketahui_pada",
        ),
    ),
    "indeks.csv": (
        "SELECT indeks, tanggal, close, close_mentah, sumber, diketahui_pada"
        " FROM v_harga_indeks_terkini ORDER BY indeks, tanggal",
        ("indeks", "tanggal", "close", "close_mentah", "sumber", "diketahui_pada"),
    ),
    "aksi-korporasi.csv": (
        "SELECT kode, tanggal, jenis, rasio_lama, rasio_baru, harga_tebus, dividen_per_saham,"
        " keterangan, sumber, diketahui_pada FROM v_aksi_korporasi_terkini"
        " ORDER BY kode, tanggal, jenis",
        (
            "kode",
            "tanggal",
            "jenis",
            "rasio_lama",
            "rasio_baru",
            "harga_tebus",
            "dividen_per_saham",
            "keterangan",
            "sumber",
            "diketahui_pada",
        ),
    ),
    "kalender-bursa.csv": (
        "SELECT tanggal, hari_bursa, keterangan, sumber, diketahui_pada"
        " FROM v_kalender_bursa_terkini ORDER BY tanggal",
        ("tanggal", "hari_bursa", "keterangan", "sumber", "diketahui_pada"),
    ),
    "notasi-khusus.csv": (
        "SELECT kode, jenis, tanggal_mulai, tanggal_selesai, keterangan, sumber, diketahui_pada"
        " FROM v_notasi_khusus_terkini ORDER BY kode, tanggal_mulai",
        ("kode", "jenis", "tanggal_mulai", "tanggal_selesai", "keterangan", "sumber", "diketahui_pada"),
    ),
    "imbal-hasil-sun.csv": (
        "SELECT tanggal, tenor_tahun, imbal_hasil_bp, imbal_hasil_mentah, sumber, diketahui_pada"
        " FROM v_imbal_hasil_sun_terkini ORDER BY tanggal, tenor_tahun",
        ("tanggal", "tenor_tahun", "imbal_hasil_bp", "imbal_hasil_mentah", "sumber", "diketahui_pada"),
    ),
    "emiten.csv": (
        "SELECT kode, nama, sektor_idx_ic, sektor_sumber, jenis, papan, status_notasi,"
        " tanggal_notasi, jumlah_saham, free_float_bp, sumber, diketahui_pada"
        " FROM v_emiten_terkini ORDER BY kode",
        (
            "kode",
            "nama",
            "sektor_idx_ic",
            "sektor_sumber",
            "jenis",
            "papan",
            "status_notasi",
            "tanggal_notasi",
            "jumlah_saham",
            "free_float_bp",
            "sumber",
            "diketahui_pada",
        ),
    ),
}


@dataclass(frozen=True)
class HasilArsip:
    """Apa yang benar-benar ditulis ke arsip, supaya bisa dilaporkan dan diperiksa."""

    folder: Path
    berkas: tuple[str, ...]
    jumlah_baris: Mapping[str, int]

    @property
    def total_baris(self) -> int:
        return sum(self.jumlah_baris.values())


# ---------------------------------------------------------------------------------------
# Penulisan tahan-gagal
# ---------------------------------------------------------------------------------------


def _sumber_dominan(sambungan: sqlite3.Connection) -> str | None:
    """Label sumber yang paling banyak dipakai baris harga/indeks saat ini.

    Dipakai hanya untuk baris kepala arsip. Bila ada lebih dari satu sumber, yang terbanyak
    yang ditulis dan sisanya dilaporkan — bukan digabung menjadi satu kalimat yang menyembunyikan
    asal sebagian baris.
    """
    for tabel in ("v_harga_harian_terkini", "v_harga_indeks_terkini"):
        baris = sambungan.execute(
            f"SELECT sumber, COUNT(*) AS jumlah FROM {tabel} GROUP BY sumber ORDER BY jumlah DESC"
        ).fetchall()
        if baris:
            utama = str(baris[0]["sumber"])
            if len(baris) > 1:
                lain = ", ".join(f"{satu['sumber']} ({satu['jumlah']} baris)" for satu in baris[1:])
                return f"{utama} | sumber lain: {lain}"
            return utama
    return None


def _tulis_atomik(jalur: Path, isi: str) -> None:
    """Tulis berkas lewat berkas sementara + `os.replace` (atomik di sistem berkas yang sama).

    Kalau proses mati di tengah penulisan, yang tertinggal hanyalah berkas `.sementara` —
    bukan arsip yang tampak lengkap tetapi isinya separuh.
    """
    sementara = jalur.with_suffix(jalur.suffix + ".sementara")
    try:
        sementara.write_text(isi, encoding="utf-8-sig", newline="")
        os.replace(sementara, jalur)
    except OSError as galat:
        sementara.unlink(missing_ok=True)
        raise GalatIngesti(f"gagal menulis arsip '{jalur}': {galat}") from galat


def _sel_csv(nilai: object) -> str:
    if nilai is None:
        return ""
    return str(nilai).replace(";", ",").replace("\r", " ").replace("\n", " ")


def _kepala(judul: str, keterangan: Mapping[str, object], sumber: object) -> list[str]:
    """Baris kepala arsip: menyebut dirinya sendiri (AC-7, aturan keras 8).

    Ditulis sebagai baris berawalan `#` supaya tetap sah dibaca sebagai CSV oleh Excel
    maupun pandas (`comment='#'`). Peringatan sumber tidak resmi ikut ditulis **di dalam
    berkasnya**, bukan hanya di aplikasi: berkas ini yang bisa berpindah tangan.
    """
    baris = [f"# {judul} — arsip snapshot Meja Saham", f"# dibuat_pada;{db.waktu_iso()}"]
    baris.extend(f"# {kunci};{_sel_csv(nilai)}" for kunci, nilai in keterangan.items())
    if isinstance(sumber, str) and "tidak resmi" in sumber:
        baris.append(f"# PERINGATAN;{PERNYATAAN_SUMBER_TIDAK_RESMI}")
    baris.append(f"# {PERNYATAAN_BUKAN_NASIAT} (PRD 9.10).")
    return baris


# ---------------------------------------------------------------------------------------
# Penulisan arsip
# ---------------------------------------------------------------------------------------


def folder_arsip(tanggal_data: date | str, id_snapshot: int) -> Path:
    """Folder arsip satu snapshot: `<arsip>/<tanggal>/snapshot-<id>`.

    `id_snapshot` ikut ke nama folder dengan sengaja: memperbaiki data menambah snapshot baru,
    dan arsip lama **tidak boleh** tertimpa (S1). Snapshot berbeda = folder berbeda.
    """
    tanggal_teks = tanggal_data.isoformat() if isinstance(tanggal_data, date) else tanggal_data
    return lokasi.folder_arsip_snapshot() / tanggal_teks / f"snapshot-{id_snapshot}"


def tulis(
    sambungan: sqlite3.Connection,
    *,
    id_snapshot: int,
    laporan_mutu: str | None = None,
    keterangan: Mapping[str, object] | None = None,
) -> HasilArsip:
    """Tulis arsip lengkap untuk satu snapshot.

    `laporan_mutu` adalah isi CSV laporan mutu (`mutu.csv_laporan`) yang ikut diarsipkan: mutu
    data hari itu juga merupakan informasi point-in-time — "kami menandai 12 emiten bolong pada
    tanggal ini" tidak bisa direkonstruksi belakangan.
    """
    baris_snapshot = sambungan.execute(
        "SELECT id_snapshot, tanggal_data, batas_diketahui, jam_ambil, jumlah_emiten,"
        " jumlah_gagal, versi_skema, versi_aplikasi, catatan FROM snapshot WHERE id_snapshot = ?",
        (id_snapshot,),
    ).fetchone()
    if baris_snapshot is None:
        raise GalatIngesti(f"snapshot {id_snapshot} tidak ada di basis data; tidak ada yang bisa diarsipkan")

    folder = folder_arsip(baris_snapshot["tanggal_data"], id_snapshot)
    lokasi.pastikan_folder(folder)

    kepala = {
        "id_snapshot": id_snapshot,
        "tanggal_data": baris_snapshot["tanggal_data"],
        "batas_diketahui": baris_snapshot["batas_diketahui"],
        "jam_ambil": baris_snapshot["jam_ambil"],
        "jumlah_emiten": baris_snapshot["jumlah_emiten"],
        "jumlah_gagal": baris_snapshot["jumlah_gagal"],
        "versi_skema": baris_snapshot["versi_skema"],
        "versi_aplikasi": baris_snapshot["versi_aplikasi"],
    }
    if keterangan:
        kepala.update(keterangan)

    # Sumber diambil dari datanya, bukan dari parameter: label "tidak resmi" harus muncul di
    # berkas yang benar-benar memuat data itu, dan tidak muncul di berkas yang datanya kosong.
    sumber = _sumber_dominan(sambungan)
    kepala["sumber_data"] = sumber or "(belum ada data harga)"

    berkas: list[str] = []
    jumlah: dict[str, int] = {}

    for nama, (kueri, kolom) in TABEL_ARSIP.items():
        baris = sambungan.execute(kueri).fetchall()
        isi = _kepala(nama, kepala, sumber)
        isi.append(";".join(kolom))
        isi.extend(";".join(_sel_csv(satu[nama_kolom]) for nama_kolom in kolom) for satu in baris)
        _tulis_atomik(folder / nama, "\n".join(isi) + "\n")
        berkas.append(nama)
        jumlah[nama] = len(baris)

    if laporan_mutu is not None:
        _tulis_atomik(folder / NAMA_MUTU, laporan_mutu)
        berkas.append(NAMA_MUTU)

    meta = {
        "id_snapshot": id_snapshot,
        "tanggal_data": baris_snapshot["tanggal_data"],
        "batas_diketahui": baris_snapshot["batas_diketahui"],
        "jam_ambil": baris_snapshot["jam_ambil"],
        "jumlah_emiten": baris_snapshot["jumlah_emiten"],
        "jumlah_gagal": baris_snapshot["jumlah_gagal"],
        "versi_skema": baris_snapshot["versi_skema"],
        "versi_aplikasi_saat_snapshot": baris_snapshot["versi_aplikasi"],
        "versi_aplikasi_saat_arsip": __version__,
        "catatan_snapshot": baris_snapshot["catatan"],
        "berkas": list(berkas),
        "jumlah_baris": jumlah,
        "pernyataan": PERNYATAAN_BUKAN_NASIAT,
    }
    _tulis_atomik(folder / NAMA_META, json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    berkas.append(NAMA_META)

    return HasilArsip(folder=folder, berkas=tuple(berkas), jumlah_baris=jumlah)


# ---------------------------------------------------------------------------------------
# Pemeriksaan arsip: membuktikan arsipnya benar-benar bisa dipakai
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Perbandingan:
    """Hasil pembandingan arsip dengan basis data pada saat ini."""

    nama: str
    baris_arsip: int
    baris_database: int

    @property
    def cocok(self) -> bool:
        return self.baris_arsip == self.baris_database


def bandingkan(sambungan: sqlite3.Connection, folder: Path) -> tuple[Perbandingan, ...]:
    """Bandingkan jumlah baris tiap berkas arsip dengan basis data sekarang.

    Gunanya bukan "apakah arsipnya identik" — arsip snapshot lama memang **seharusnya** berbeda
    dari basis data yang sudah bertambah. Gunanya membuktikan arsipnya **terbaca dan masuk
    akal**: barisnya bisa dihitung, kepala berkasnya lengkap, dan tabelnya bukan nol semua.
    Karena itu fungsi ini melaporkan angkanya, bukan memutuskan benar/salah untuk pengguna.
    """
    hasil: list[Perbandingan] = []
    for nama, (kueri, kolom) in TABEL_ARSIP.items():
        jalur = folder / nama
        if not jalur.is_file():
            raise GalatIngesti(f"arsip '{folder}' tidak memuat {nama}")
        teks = jalur.read_text(encoding="utf-8-sig")
        baris = [
            satu
            for satu in teks.splitlines()
            if satu.strip() and not satu.startswith("#") and satu.split(";")[0] != kolom[0]
        ]
        jumlah_db = int(sambungan.execute(f"SELECT COUNT(*) FROM ({kueri})").fetchone()[0])
        hasil.append(Perbandingan(nama=nama, baris_arsip=len(baris), baris_database=jumlah_db))
    return tuple(hasil)


def ringkas_untuk_log(hasil: HasilArsip) -> str:
    """Satu baris untuk `log_jalan`, supaya arsipnya bisa ditelusuri dari basis data."""
    rincian = ", ".join(f"{nama}={jumlah}" for nama, jumlah in sorted(hasil.jumlah_baris.items()))
    return f"arsip {hasil.folder}: {hasil.total_baris} baris ({rincian})"


def daftar_arsip() -> Sequence[Path]:
    """Folder arsip yang sudah ada, terbaru lebih dulu."""
    akar = lokasi.folder_arsip_snapshot()
    if not akar.is_dir():
        return ()
    return tuple(sorted((satu for satu in akar.glob("*/*") if satu.is_dir()), reverse=True))
