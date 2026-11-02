"""Pelacak jadwal pembaruan data (U36 → K93): data mana yang sudah terbaru, mana yang jatuh tempo.

Satu daftar periksa yang dibaca dasbor (web dan `--dasbor`) serta dicetak sesudah `--refresh`.
Isinya hanya **memberi tahu dan menyebut tindakannya** (K89): tidak ada pengambilan atau impor
yang dijalankan dari sini.

Aturan yang dijaga:

1. **Status diturunkan dari data yang benar-benar masuk**, bukan dari "proses pernah dicoba" atau
   "berkas CSV pernah dibuat". Tanggal yang dipakai adalah tanggal **isi** data: tanggal snapshot,
   tanggal daftar resmi IDX yang tercantum di baris notasi, tanggal Master File KSEI di label baris
   emiten, cakupan tahun kalender, catatan cek sumber kedua.
2. **Label `sumber` tidak dipakai sebagai bukti waktu.** `--refresh` membaca ulang berkas di folder
   konfigurasi setiap hari, jadi waktu tulis baris (`diketahui_pada`) bisa baru walaupun isinya lama.
3. **Yang tidak bisa dibuktikan disebut "tidak dinilai" beserta alasannya** — bukan dianggap
   terbaru, dan bukan dianggap jatuh tempo (aturan keras 2, dalam semangatnya).
4. Jadwal di sini adalah jadwal **aplikasi** (U36), bukan parameter bursa: tidak ada jam bursa
   atau tanggal terbit yang dikarang (aturan keras 1).
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, timedelta

from mejasaham import mutu, notasi, pembaruan, pengumuman_idx, potret, tampilan, unggahan_idx

TERBARU = "terbaru"
JATUH_TEMPO = "jatuh tempo"
MENUNGGU = "menunggu sumber"
TIDAK_DINILAI = "tidak dinilai"

#: Notasi khusus, suspensi, dan UMA diperbarui mingguan (K94 — PRD 7.1 meminta suspensi/UMA
#: harian; pengguna memilih mingguan dan perbedaannya dicatat di K94). Batasnya inklusif seperti
#: cek sumber kedua (U19): berumur tepat 7 hari masih terbaru. Sejak K96 pembaruannya diunduh
#: pengguna dari situs IDX (Syarat Penggunaan IDX melarang scraping), bukan diambil aplikasi.
HARI_NOTASI = 7

ALAMAT_RINGKASAN = unggahan_idx.ALAMAT_RINGKASAN_SAHAM

#: `notasi.urai` menulis "... tercantum pada daftar resmi per YYYY-MM-DD ..." di `keterangan`.
_DAFTAR_PER = re.compile(re.escape(notasi.PENANDA_BARIS) + r" (\d{4}-\d{2}-\d{2})")
#: `ksei.py` menulis label "Master File Efek KSEI 30 Sep 2026" (format `tampilan.tanggal`).
_MASTER_FILE = re.compile(r"Master File Efek KSEI (\d{2}) (" + "|".join(tampilan.BULAN_SINGKAT) + r") (\d{4})")

PERINTAH_NOTASI = (
    f"unduh Notasi Khusus dari situs IDX ({notasi.ALAMAT_UNDUHAN}, tombol Unduh), lalu unggah di "
    "menu Impor & cadangan (K96: aplikasi tidak mengambilnya otomatis)"
)
#: K99: suspensi & UMA diunggah sebagai PDF pengumuman satuan dari situs IDX.
PERINTAH_SUSPENSI_UMA = (
    "periksa pengumuman suspensi dan UMA di situs IDX (idx.co.id), unduh PDF tiap pengumuman, "
    "termasuk pembukaan (UPT), lalu unggah di menu Impor & cadangan (K99, K100); pengumuman "
    "multi-kode belum dibaca — isi konfigurasi/notasi-khusus.csv dengan tangan, lalu --impor "
    "(cadangan dulu)"
)


@dataclass(frozen=True)
class Butir:
    nama: str
    jadwal: str
    status: str
    #: Dasar statusnya — tanggal isi data yang dipakai, atau alasan tidak bisa dinilai.
    bukti: str
    #: Yang bisa dikerjakan pengguna (K89: ditawarkan, tidak dijalankan otomatis).
    tindakan: str = ""
    #: Halaman IDX yang dibuka **pengguna** untuk mengunduh berkasnya (K102: dipakai pengingat).
    #: Kosong = data ini tidak diunduh dari situs IDX.
    alamat: str = ""


def _tgl(iso: str | None) -> str:
    return tampilan.tanggal(date.fromisoformat(iso)) if iso else "—"


def _harga(sambungan: sqlite3.Connection, hari_ini: date) -> Butir:
    keadaan = pembaruan.keadaan(sambungan, hari_ini)
    nama, jadwal = "Harga harian & indeks", "tiap hari bursa"
    tindakan = 'tombol "Perbarui data" atau --refresh --saring'
    if keadaan.id_snapshot is None:
        return Butir(nama, jadwal, JATUH_TEMPO, "belum ada snapshot", tindakan)
    if keadaan.hari_bursa_terakhir is None:
        return Butir(
            nama, jadwal, TIDAK_DINILAI,
            f"snapshot #{keadaan.id_snapshot} data {_tgl(keadaan.tanggal_data)}; kalender bursa "
            "kosong, jadi hari bursa terakhir tidak diketahui",
            "isi kalender bursa (--ambil-kalender, lalu --impor)",
        )
    bukti = (
        f"snapshot #{keadaan.id_snapshot} data {_tgl(keadaan.tanggal_data)}; hari bursa terakhir "
        f"{_tgl(keadaan.hari_bursa_terakhir)}"
    )
    if not keadaan.terbaru:
        return Butir(nama, jadwal, JATUH_TEMPO, bukti, tindakan)
    return _harga_resmi(sambungan, keadaan.tanggal_data, nama, bukti) or Butir(nama, jadwal, TERBARU, bukti)


def _harga_resmi(
    sambungan: sqlite3.Connection, tanggal_data: str | None, nama: str, bukti: str
) -> Butir | None:
    """Sesudah tanggal sambung (K97), harga harian baru lengkap bila berkas IDX tiap hari bursa
    sudah diimpor; snapshot yfinance yang terbaru saja tidak cukup. `None` bila tidak tersambung.

    Hari yang dihitung sama dengan sebab PERINGKAT SEMENTARA (`potret.periksa_sambungan`), jadi
    jadwal dan saringan tidak bisa saling membantah."""
    pilihan = potret.harga_dipakai(sambungan)
    if pilihan is None or not pilihan.tersambung or tanggal_data is None:
        return None
    jadwal = f"tiap hari bursa — {pilihan.resmi} sejak {_tgl(pilihan.sejak.isoformat())} (K97)"
    tindakan = (
        "unduh Ringkasan Saham IDX untuk tanggal itu, unggah di menu Impor & cadangan (boleh beberapa "
        'berkas sekaligus), lalu "Impor … berkas"'
    )
    keadaan = potret.periksa_sambungan(sambungan, pilihan, tanggal_data=date.fromisoformat(tanggal_data))
    if keadaan is None:
        return None
    if keadaan.kalender_kurang is not None:
        return Butir(
            nama, jadwal, TIDAK_DINILAI, f"{bukti}; {keadaan.kalender_kurang}", tindakan, ALAMAT_RINGKASAN
        )
    if keadaan.bolong_di_jendela:
        tanggal = ", ".join(satu.isoformat() for satu in keadaan.bolong_di_jendela[:5])
        lagi = len(keadaan.bolong_di_jendela) - 5
        return Butir(
            nama, jadwal, JATUH_TEMPO,
            f"{bukti}; {len(keadaan.bolong_di_jendela)} hari bursa tanpa berkas IDX: {tanggal}"
            + (f" … dan {lagi} lagi" if lagi > 0 else ""),
            tindakan,
            ALAMAT_RINGKASAN,
        )
    return Butir(
        nama, jadwal, TERBARU, f"{bukti}; berkas IDX lengkap sejak tanggal sambung", alamat=ALAMAT_RINGKASAN
    )


def _saringan(sambungan: sqlite3.Connection) -> Butir:
    """Skor disimpan per snapshot, dan impor/refresh tidak menyaring ulang (K89). Snapshot baru tanpa
    skor membuat dasbor tidak punya kandidat untuk ditampilkan — itu yang diberitahukan di sini."""
    nama, jadwal = "Saringan & skor kandidat", "sesudah setiap snapshot baru"
    tindakan = 'Screener → "Jalankan saringan", atau --saring'
    terakhir = sambungan.execute(
        "SELECT id_snapshot, tanggal_data FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()
    if terakhir is None:
        return Butir(nama, jadwal, TIDAK_DINILAI, "belum ada snapshot untuk disaring")
    id_snapshot, tanggal_data = terakhir
    disaring = sambungan.execute(
        "SELECT id_preset, MAX(dihitung_pada) FROM skor WHERE id_snapshot = ?"
        " GROUP BY id_preset ORDER BY 2 DESC LIMIT 1",
        (id_snapshot,),
    ).fetchone()
    if disaring is not None:
        return Butir(
            nama, jadwal, TERBARU,
            f"snapshot #{id_snapshot} disaring {_tgl(disaring[1][:10])} (preset {disaring[0]})",
        )
    (sebelumnya,) = sambungan.execute("SELECT MAX(id_snapshot) FROM skor").fetchone()
    bukti = f"snapshot #{id_snapshot} data {_tgl(tanggal_data)} belum disaring, jadi dasbor tidak punya kandidat"
    bukti += f"; skor terakhir dari snapshot #{sebelumnya}" if sebelumnya is not None else "; belum pernah disaring"
    return Butir(nama, jadwal, JATUH_TEMPO, bukti, tindakan)


def _daftar_notasi_per(sambungan: sqlite3.Connection) -> tuple[bool, str | None]:
    """(ada baris daftar notasi?, tanggal daftar resmi IDX terbaru yang tercantum di barisnya).

    Hanya jenis yang dicakup daftar Notasi Khusus (`notasi.JENIS_DAFTAR`); suspensi/UMA dinilai
    terpisah (P43)."""
    ada = False
    terbaru: str | None = None
    tanda = ",".join("?" * len(notasi.JENIS_DAFTAR))
    for (keterangan,) in sambungan.execute(
        f"SELECT keterangan FROM v_notasi_khusus_terkini WHERE jenis IN ({tanda})",
        sorted(notasi.JENIS_DAFTAR),
    ):
        ada = True
        cocok = _DAFTAR_PER.search(keterangan or "")
        if cocok and (terbaru is None or cocok.group(1) > terbaru):
            terbaru = cocok.group(1)
    return ada, terbaru


def _notasi(sambungan: sqlite3.Connection, hari_ini: date) -> Butir:
    """Notasi khusus dan papan pemantauan — keduanya dari daftar Notasi Khusus IDX yang sama, jadi
    jadwalnya satu: mingguan (K94, diunduh pengguna sejak K96)."""
    nama = "Notasi khusus & papan pemantauan (IDX)"
    jadwal = f"mingguan ({HARI_NOTASI} hari — K94)"
    ada, per = _daftar_notasi_per(sambungan)
    if not ada:
        return Butir(
            nama, jadwal, JATUH_TEMPO, "belum ada data notasi khusus", PERINTAH_NOTASI, notasi.ALAMAT_UNDUHAN
        )
    if per is None:
        return Butir(
            nama, jadwal, TIDAK_DINILAI,
            "tanggal daftar resmi IDX tidak tercantum di baris mana pun, jadi kesegarannya tidak "
            "bisa dibuktikan",
            PERINTAH_NOTASI,
            notasi.ALAMAT_UNDUHAN,
        )
    umur = (hari_ini - date.fromisoformat(per)).days
    bukti = f"daftar resmi IDX per {_tgl(per)} (dari baris notasi yang tersimpan); berumur {umur} hari"
    if umur <= HARI_NOTASI:
        return Butir(nama, jadwal, TERBARU, bukti, alamat=notasi.ALAMAT_UNDUHAN)
    return Butir(nama, jadwal, JATUH_TEMPO, bukti, PERINTAH_NOTASI, notasi.ALAMAT_UNDUHAN)


def _suspensi_uma(sambungan: sqlite3.Connection) -> Butir:
    """P43/K99: selalu "tidak dinilai". Tanggal pengumuman terakhir yang tersimpan bukan bukti
    kesegaran — hari tanpa pengumuman baru tidak bisa dibedakan dari data yang tidak diperbarui,
    dan PDF pengumuman yang tidak diunggah tidak terdeteksi (K93 aturan 3)."""
    nama = "Suspensi & UMA (IDX)"
    jadwal = "tidak dinilai — unggah PDF per pengumuman (K99); PRD 7.1: harian, K94: mingguan"
    jumlah = dict(
        sambungan.execute(
            "SELECT jenis, COUNT(*) FROM v_notasi_khusus_terkini WHERE jenis IN ('suspensi', 'uma') "
            "GROUP BY jenis"
        ).fetchall()
    )
    (terakhir,) = sambungan.execute(
        "SELECT MAX(tanggal_mulai) FROM v_notasi_khusus_terkini WHERE jenis IN ('suspensi', 'uma')"
    ).fetchone()
    if not jumlah:
        bukti = "belum ada baris suspensi/UMA; kesegarannya tidak bisa dibuktikan dari PDF satuan"
    else:
        bukti = (
            f"{tampilan.angka(jumlah.get('suspensi', 0), 0)} suspensi, "
            f"{tampilan.angka(jumlah.get('uma', 0), 0)} UMA; pengumuman terakhir yang tersimpan "
            f"{_tgl(terakhir)} — bukan bukti kesegaran, karena PDF yang terlewat tidak terdeteksi"
        )
    return Butir(
        nama, jadwal, TIDAK_DINILAI, bukti, PERINTAH_SUSPENSI_UMA, pengumuman_idx.ALAMAT_PENGUMUMAN
    )


def _sumber_kedua(sambungan: sqlite3.Connection, hari_ini: date) -> Butir:
    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=hari_ini)
    nama, jadwal = "Cek sumber kedua (PRD 7.3)", f"mingguan ({keadaan.batas_hari} hari)"
    tindakan = (
        "unduh Ringkasan Saham IDX di hari snapshot terakhir, unggah di menu Impor & cadangan, lalu "
        '"Impor … berkas" — cek sumber kedua ikut dijalankan bila ada berkas bertanggal snapshot (K95)'
    )
    if keadaan.status == mutu.STATUS_TEPAT_WAKTU:
        return Butir(
            nama, jadwal, TERBARU,
            f"cek lengkap terakhir {_tgl((keadaan.terakhir_lengkap or '')[:10])}, "
            f"{keadaan.hari_sejak_lengkap} hari lalu",
        )
    if keadaan.status == mutu.STATUS_TIDAK_DAPAT_DINILAI:
        return Butir(nama, jadwal, TIDAK_DINILAI, keadaan.alasan or "catatan cek tidak terbaca", tindakan)
    if keadaan.status == mutu.STATUS_LEWAT:
        return Butir(
            nama, jadwal, JATUH_TEMPO,
            f"cek lengkap terakhir {keadaan.hari_sejak_lengkap} hari lalu", tindakan,
        )
    if keadaan.percobaan_terakhir_belum_lengkap:
        return Butir(
            nama, jadwal, MENUNGGU,
            "belum pernah lengkap; percobaan terakhir: " + (keadaan.catatan_terakhir or "belum lengkap"),
            tindakan,
        )
    return Butir(nama, jadwal, JATUH_TEMPO, "belum pernah dijalankan", tindakan)


def _akhir_bulan_lalu(hari_ini: date) -> date:
    return hari_ini.replace(day=1) - timedelta(days=1)


def _emiten(sambungan: sqlite3.Connection, hari_ini: date) -> Butir:
    nama, jadwal = "Daftar emiten (Master File KSEI)", "bulanan"
    tindakan = "--ambil-emiten --timpa-emiten, lalu --impor"
    tanggal: Counter[date] = Counter()
    jumlah = 0
    for (sumber,) in sambungan.execute("SELECT sumber FROM v_emiten_terkini"):
        jumlah += 1
        cocok = _MASTER_FILE.search(sumber or "")
        if cocok:
            bulan = tampilan.BULAN_SINGKAT.index(cocok.group(2)) + 1
            tanggal[date(int(cocok.group(3)), bulan, int(cocok.group(1)))] += 1
    if not jumlah:
        return Butir(nama, jadwal, JATUH_TEMPO, "belum ada daftar emiten", tindakan)
    if not tanggal:
        return Butir(
            nama, jadwal, TIDAK_DINILAI,
            f"{jumlah} emiten tanpa tanggal Master File KSEI di labelnya (diisi tangan atau dari "
            "sumber lain), jadi kesegarannya tidak bisa dibuktikan",
            tindakan,
        )
    per = max(tanggal)
    bukti = f"Master File per {tampilan.tanggal(per)} ({tanggal[per]} dari {jumlah} emiten)"
    if per >= _akhir_bulan_lalu(hari_ini):
        return Butir(nama, jadwal, TERBARU, bukti)
    return Butir(
        nama, jadwal, JATUH_TEMPO,
        f"{bukti}; berkas akhir {tampilan.tanggal(_akhir_bulan_lalu(hari_ini))} mungkin sudah terbit",
        tindakan,
    )


def _kalender(sambungan: sqlite3.Connection, hari_ini: date) -> Butir:
    nama, jadwal = "Kalender bursa (KSEI)", "tahunan"
    tindakan = "--ambil-kalender, lalu --impor"
    tahun = [
        int(satu)
        for (satu,) in sambungan.execute(
            "SELECT DISTINCT substr(tanggal, 1, 4) FROM v_kalender_bursa_terkini WHERE hari_bursa = 1"
        )
    ]
    if not tahun:
        return Butir(nama, jadwal, JATUH_TEMPO, "kalender bursa kosong", tindakan)
    bukti = f"memuat tahun {', '.join(str(t) for t in sorted(tahun))}"
    if hari_ini.year not in tahun:
        return Butir(nama, jadwal, JATUH_TEMPO, f"{bukti}; tahun {hari_ini.year} belum ada", tindakan)
    if hari_ini.year + 1 not in tahun:
        bukti += f"; tahun {hari_ini.year + 1} belum ada (diambil saat pengumumannya terbit)"
    return Butir(nama, jadwal, TERBARU, bukti)


def _sun(sambungan: sqlite3.Connection) -> Butir:
    (terakhir,) = sambungan.execute("SELECT MAX(tanggal) FROM v_imbal_hasil_sun_terkini").fetchone()
    return Butir(
        "Imbal hasil SUN 10 tahun (PHEI)",
        "belum diputuskan",
        TIDAK_DINILAI,
        f"data terakhir {_tgl(terakhir)}; PRD tidak menetapkan selang pembaruannya (U36)",
        "--ambil-sun, lalu --impor",
    )


def _fundamental(sambungan: sqlite3.Connection) -> tuple[Butir, Butir]:
    terbit, periode, jumlah = sambungan.execute(
        "SELECT MAX(tgl_publikasi), MAX(periode), COUNT(DISTINCT kode) FROM v_fundamental_terkini"
    ).fetchone()
    (bank,) = sambungan.execute("SELECT COUNT(DISTINCT kode) FROM v_rasio_bank_terkini").fetchone()
    mengikuti = "mengikuti publikasi laporan"
    alasan = "tanggal terbit laporan berikutnya tidak tercatat, jadi jatuh temponya tidak bisa dihitung"
    return (
        Butir(
            "Fundamental emiten",
            mengikuti,
            TIDAK_DINILAI,
            f"{jumlah} emiten; periode terakhir {_tgl(periode)}, dipakai sejak {_tgl(terbit)}; {alasan}",
            "--ambil-fundamental, lalu --impor",
        ),
        Butir(
            "Rasio bank",
            mengikuti,
            TIDAK_DINILAI,
            f"{bank} bank berasio; perluasan ke bank lain ditunda (K88)",
        ),
    )


def susun(sambungan: sqlite3.Connection, momen: date | None = None) -> tuple[Butir, ...]:
    hari_ini = momen or date.today()
    fundamental, bank = _fundamental(sambungan)
    return (
        _harga(sambungan, hari_ini),
        _saringan(sambungan),
        _notasi(sambungan, hari_ini),
        _suspensi_uma(sambungan),
        # Bahannya Ringkasan Saham yang sama (K95), jadi tautannya juga sama.
        replace(_sumber_kedua(sambungan, hari_ini), alamat=ALAMAT_RINGKASAN),
        _emiten(sambungan, hari_ini),
        _kalender(sambungan, hari_ini),
        _sun(sambungan),
        fundamental,
        bank,
    )


def ringkas(daftar: tuple[Butir, ...]) -> str:
    """Teks untuk baris perintah: satu baris per data, lalu tindakan untuk yang jatuh tempo."""
    lebar = max(len(satu.nama) for satu in daftar)
    baris = ["JADWAL PEMBARUAN DATA (K93 — hanya memberi tahu; tidak ada yang dijalankan otomatis)"]
    for satu in daftar:
        baris.append(f"  [{satu.status.upper():^15}] {satu.nama:<{lebar}}  {satu.jadwal}")
        baris.append(f"  {'':17} {satu.bukti}")
        if satu.tindakan and satu.status != TERBARU:
            baris.append(f"  {'':17} tindakan: {satu.tindakan}")
    return "\n".join(baris)
