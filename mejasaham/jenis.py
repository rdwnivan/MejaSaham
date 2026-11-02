"""Menurunkan `jenis` emiten dari data yang **dinyatakan sumbernya** — K21, 10 Okt 2026.

Kenapa modul ini ada, dan apa batasnya
--------------------------------------
PRD 8.4 memakai `jenis` emiten untuk memilih set kriteria: bank dinilai dengan NPL/CAR/BOPO/NIM
dan **tidak** dengan DER/coverage/CFO-NI, sedangkan emiten lain sebaliknya. Selama kolomnya
kosong, kriteria bank tidak pernah berlaku dan rasio utang ikut dihitung untuk bank — diamnya
bukan berarti tidak terjadi. Mengisinya dengan tangan untuk ~975 emiten bukan pekerjaan yang
masuk akal, tetapi **mengarangnya** dilarang aturan keras 1.

Jalan tengahnya diputuskan sebagai **K21**: `jenis` boleh diturunkan dari `sector`/`industry`
yang dinyatakan sumber data, dengan tiga batas yang mengikat:

1. **Label sumber ikut tersimpan.** Ini turunan sumber **tidak resmi**, bukan isian tangan; baris
   yang keluar dari modul ini menyebut sector/industry mentahnya dan menyatakan asalnya.
2. **Hanya `bank_keuangan` yang diturunkan.** `siklikal_komoditas` **tidak pernah** diturunkan:
   "emiten ini siklikal" adalah penilaian analis, dan tidak satu pun sumber data menyatakannya.
   Sisanya `umum` — artinya "pakai set kriteria umum", bukan "sudah dinilai".
3. **Keadaannya dilaporkan**, sebab akibatnya nyata (lihat `docs/keputusan.md` K21).

Yang **tidak** dikerjakan modul ini, dan sengaja:

* `sektor_idx_ic` dibiarkan kosong. Sumber data memakai taksonomi lain (mis.
  `Financial Services`), sedangkan PRD memakai IDX-IC; pemetaan resmi antara keduanya tidak
  diterbitkan siapa pun — K12 sudah menetapkan kolom itu dibiarkan kosong. Memetakannya di sini
  berarti mengarang pemetaan (masih **P16** di `docs/keputusan.md`).
* `siklikal_komoditas` tidak pernah dihasilkan, sekalipun sector-nya `Basic Materials`.
  Menurunkan "siklikal" dari sektor adalah penilaian, bukan pembacaan fakta.

Aturan penurunannya hidup di **satu fungsi murni** (`jenis_dari_sumber`), supaya bisa diuji tanpa
jaringan dan supaya tidak ada aturan kedua yang tumbuh di jalur penulisan berkas.
"""

from __future__ import annotations

import csv
import os
import sqlite3
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mejasaham import berkas, tampilan
from mejasaham.ingesti import JENIS_EMITEN

#: Nilai `jenis` yang boleh dihasilkan modul ini. `siklikal_komoditas` **tidak ada di sini**
#: dengan sengaja: ia penilaian, bukan fakta yang dinyatakan sumber (K21). Daftar nilai sahnya
#: sendiri hidup di `ingesti.JENIS_EMITEN` dan **diimpor**, bukan disalin (aturan keras 5).
JENIS_DITURUNKAN = ("bank_keuangan", "umum")

#: Penanda jenis emiten yang **sudah terisi** dan karena itu tidak ditimpa (K21 batas (b)).
JENIS_BELUM_DIISI: None = None


def _normalkan(teks: object) -> str:
    """Label sumber dibandingkan tanpa memperhatikan huruf besar/kecil dan spasi berlebih.

    `Financial Services` dan `financial services` adalah label yang sama; membedakannya berarti
    satu perubahan kapitalisasi di sisi sumber membuat turunannya diam-diam berhenti bekerja.
    """
    return " ".join(str(teks or "").split()).casefold()


#: Sector yang menyatakan **jasa keuangan** menurut sumber data. Hanya satu nilai, dan itu
#: disengaja: yang boleh masuk daftar ini hanyalah label yang benar-benar berarti jasa keuangan.
SECTOR_JASA_KEUANGAN = ("financial services",)

#: Industry yang menyatakan **bank**. Beberapa label dipakai sumber data untuk hal yang sama
#: (`Banks - Regional` dan `Banks - Diversified`); keduanya menyebut bank secara eksplisit.
#: Label `Insurance`, `Asset Management`, dan `Capital Markets` **tidak** termasuk: perusahaan
#: asuransi bukan bank, dan PRD 8.4 hanya menyediakan set kriteria bank untuk bank.
INDUSTRY_BANK = ("banks - regional", "banks - diversified", "banks")


def sumber_bank(sector: object, industry: object) -> bool:
    """True bila sumber menyatakan **jasa keuangan dan bank** — dua-duanya, bukan salah satu.

    Keduanya disyaratkan sebab masing-masing saja terlalu luas: `Financial Services` juga memuat
    asuransi dan manajer investasi, sedangkan industri yang menyebut bank tanpa sector jasa
    keuangan berarti labelnya tidak konsisten dan lebih baik tidak dipakai.

    Industri dibandingkan dengan awalan `banks`: sumber memakai bentuk berseri
    (`Banks - Regional`), dan bentuk baru seperti `Banks - Syariah` tetap berarti bank.
    """
    if _normalkan(sector) not in SECTOR_JASA_KEUANGAN:
        return False
    industri = _normalkan(industry)
    return industri in INDUSTRY_BANK or industri.startswith("banks")


def jenis_dari_sumber(sector: object, industry: object) -> str | None:
    """`jenis` yang dinyatakan `sector`/`industry` sumber, atau `None` bila tidak ada.

    `None` berarti **"sumber tidak menyatakan sector maupun industry"** — dan itu bukan `umum`.
    Bedanya nyata: `umum` berarti "sumber menyatakan sektornya, dan sektor itu bukan jasa
    keuangan", sedangkan `None` berarti "tidak ada yang bisa disimpulkan". Menyamakan keduanya
    akan mengisi kolom untuk emiten yang sumbernya diam, dan itu bertentangan dengan aturan
    keras 1 (metrik tanpa data = tidak dihitung) serta K21 batas (a) yang menuntut label sumber.

    Nilai yang dikembalikan selalu salah satu dari `JENIS_DITURUNKAN`; `siklikal_komoditas`
    tidak pernah muncul dari sini.
    """
    if not _normalkan(sector) and not _normalkan(industry):
        return None
    if sumber_bank(sector, industry):
        return "bank_keuangan"
    return "umum"


def penjelasan_jenis(jenis: str | None, sector: object, industry: object) -> str:
    """Satu kalimat yang menyebut label **mentah** sumbernya, untuk kolom `sumber` per baris.

    K21 batas (a): label sumber ikut tersimpan. Tanpa label mentahnya, baris hasil turunan tidak
    bisa diperiksa manusia — dan turunan yang tidak bisa diperiksa sama tidak bergunanya dengan
    turunan yang salah.
    """
    mentah = f"sector={str(sector or '').strip() or '(tidak dinyatakan)'}, " f"industry={str(industry or '').strip() or '(tidak dinyatakan)'}"
    if jenis == "bank_keuangan":
        return (
            f"jenis diturunkan dari sector/industry sumber data (label mentah: {mentah}); "
            "label sumber data TIDAK RESMI dan bukan penilaian analis (K21)"
        )
    if jenis == "umum":
        return (
            f"jenis=umum karena sector/industry sumber data menyatakan bukan bank "
            f"(label mentah: {mentah}); sumber data TIDAK RESMI (K21)"
        )
    return (
        f"jenis TIDAK diturunkan: sumber data tidak menyatakan sector maupun industry "
        f"(label mentah: {mentah}). Kosong berarti \"tidak dinyatakan\", bukan umum (K21)"
    )


@dataclass(frozen=True)
class EmitenTersimpan:
    """Revisi terakhir satu emiten di basis data, apa adanya — termasuk `jenis` yang sudah ada.

    `jenis` dibawa serta supaya turunannya **tidak menimpa** isian tangan: begitu seseorang
    mengisi `bank_keuangan` atau `siklikal_komoditas` di `emiten.csv`, nilai itu yang bertahan
    (K21 batas (b)).
    """

    kode: str
    nama: str
    sektor_idx_ic: str | None
    #: Sektor menurut **sumber data** (K25) — bukan IDX-IC, dan tidak pernah ditimpa turunan.
    sektor_sumber: str | None
    jenis: str | None
    papan: str | None
    status_notasi: str | None
    tanggal_notasi: str | None
    jumlah_saham: int | None
    sumber: str


def _baris_terakhir(sambungan: sqlite3.Connection, kode: str) -> EmitenTersimpan:
    baris = sambungan.execute(
        "SELECT kode, nama, sektor_idx_ic, sektor_sumber, jenis, papan, status_notasi,"
        "       tanggal_notasi, jumlah_saham, sumber"
        " FROM v_emiten_terkini WHERE kode = ?",
        (kode,),
    ).fetchone()
    if baris is None:
        raise ValueError(f"kode {kode!r} tidak ada di v_emiten_terkini padahal baru saja dibaca")
    return EmitenTersimpan(
        kode=baris["kode"],
        nama=baris["nama"],
        sektor_idx_ic=baris["sektor_idx_ic"],
        sektor_sumber=baris["sektor_sumber"],
        jenis=baris["jenis"],
        papan=baris["papan"],
        status_notasi=baris["status_notasi"],
        tanggal_notasi=baris["tanggal_notasi"],
        jumlah_saham=baris["jumlah_saham"],
        sumber=baris["sumber"],
    )


def emiten_tersimpan(
    sambungan: sqlite3.Connection, kode: Iterable[str] | None = None
) -> tuple[EmitenTersimpan, ...]:
    """Revisi **terakhir per kode** dari tabel `emiten` di basis data (bukan dari berkas).

    Sumbernya basis data, bukan `emiten.csv`, sebab berkasnya bisa saja sudah disunting tangan
    dan belum diimpor; yang boleh dipakai sebagai dasar turunan adalah yang benar-benar sudah
    tercatat. Kodenya diurutkan supaya jalan yang sama menghasilkan berkas yang sama (A5).
    """
    if kode is None:
        perintah = "SELECT kode FROM v_emiten_terkini ORDER BY kode"
        parameter: tuple[object, ...] = ()
    else:
        diminta = tuple(sorted({satu.strip().upper() for satu in kode if satu and satu.strip()}))
        if not diminta:
            return ()
        perintah = (
            "SELECT kode FROM v_emiten_terkini WHERE kode IN"
            f" ({', '.join('?' for _ in diminta)}) ORDER BY kode"
        )
        parameter = diminta
    return tuple(_baris_terakhir(sambungan, satu["kode"]) for satu in sambungan.execute(perintah, parameter))


def nilai_sah_dikenal() -> tuple[str, ...]:
    """Nilai `jenis` yang sah menurut pemiliknya (`ingesti`), tanpa nilai kosong.

    Dipakai pesan galat dan uji; ia **meminjam** daftarnya, jadi menambah nilai baru di
    `ingesti.JENIS_EMITEN` tidak bisa membuat dua daftar berbeda (aturan keras 5).
    """
    return tuple(sorted({satu for satu in JENIS_EMITEN.values() if satu}))


def periksa_jenis(jenis: object, di_mana: str) -> str | None:
    """`jenis` dari sumber luar diperiksa terhadap daftar pemiliknya; salah tulis ditolak.

    Tidak dipakai jalur penulisan berkas (di sana nilainya selalu dari `jenis_dari_sumber`),
    melainkan oleh pemanggil yang membaca `jenis` dari basis data dan ingin memastikan isinya
    masih dikenal sebelum dipakai memilih set kriteria.
    """
    teks = str(jenis or "").strip()
    if not teks:
        return None
    sah = nilai_sah_dikenal()
    if teks not in sah:
        raise ValueError(f"{di_mana}: jenis {teks!r} tidak dikenal; yang sah: {list(sah)}")
    return teks


@dataclass(frozen=True)
class KeadaanJenis:
    """Sebaran `jenis` pada satu potret, beserta kalimat laporan dan peringatannya (K21).

    Tiga keadaan dipisahkan, sebab ketiganya berarti hal yang berbeda: **bank dari data**
    (kriteria bank berlaku), **umum dari data** (kriteria bank tidak berlaku, dan itu
    *dinyatakan* sumber), dan **kosong** (belum ada yang bisa disimpulkan). Menggabungkan
    ketiganya menjadi satu angka "belum terisi" menyembunyikan justru bagian yang sudah bekerja.
    """

    bank_keuangan: int = 0
    umum: int = 0
    siklikal_komoditas: int = 0
    kosong: int = 0

    @property
    def total(self) -> int:
        return self.bank_keuangan + self.umum + self.siklikal_komoditas + self.kosong

    @classmethod
    def dari(cls, jenis_per_kode: Mapping[str, str | None]) -> KeadaanJenis:
        return cls(
            bank_keuangan=sum(1 for satu in jenis_per_kode.values() if satu == "bank_keuangan"),
            umum=sum(1 for satu in jenis_per_kode.values() if satu == "umum"),
            siklikal_komoditas=sum(
                1 for satu in jenis_per_kode.values() if satu == "siklikal_komoditas"
            ),
            kosong=sum(1 for satu in jenis_per_kode.values() if not satu),
        )

    def ringkas(self) -> str:
        """Kalimat keadaan untuk `--saring` — pembedaannya yang penting, bukan angkanya saja."""
        bagian = [
            "  jenis emiten: "
            + " · ".join(
                [
                    f"{self.bank_keuangan} bank_keuangan (dari data)",
                    f"{self.umum} umum (dari data)",
                    f"{self.siklikal_komoditas} siklikal_komoditas (isian manusia)",
                    f"{self.kosong} belum terisi",
                ]
            )
        ]
        if self.bank_keuangan:
            bagian.append(
                f"    {self.bank_keuangan} emiten ber-jenis bank_keuangan: kriteria bank "
                "(NPL, CAR, BOPO, NIM) berlaku untuk mereka, dan DER/coverage/CFO-NI TIDAK "
                "dihitung (PRD 8.4, AC-16)"
            )
        if self.kosong:
            bagian.append(
                f"    {self.kosong} emiten belum ber-jenis: set kriteria bank tidak diterapkan "
                "untuk mereka, dan DER/coverage/CFO-NI ikut dihitung — padahal PRD 8.4 "
                "mengecualikannya untuk bank"
            )
        return "\n".join(bagian)

    def peringatan(self) -> str | None:
        """Peringatan yang menyebut **kedua** sisi keadaan, bukan hanya yang kosong.

        `None` bila tidak ada yang kosong: ketika seluruh emiten sudah ber-jenis, tidak ada lagi
        yang perlu diperingatkan, dan peringatan yang selalu berbunyi berhenti memberi informasi.
        """
        if not self.kosong:
            return None
        return (
            f"jenis emiten belum terisi untuk {self.kosong} emiten: set kriteria bank (NPL, CAR, "
            "BOPO, NIM) tidak diterapkan untuk mereka, dan DER/coverage/CFO-NI ikut dihitung "
            "padahal PRD 8.4 mengecualikannya untuk bank. "
            f"Sudah terisi dari data: {self.bank_keuangan} bank_keuangan, {self.umum} umum. "
            "Lengkapi dengan --ambil-jenis (menurunkan bank_keuangan dari sector/industry yang "
            "dinyatakan sumber data, K21) atau isi kolom `jenis` di emiten.csv"
        )


# ---------------------------------------------------------------------------------------
# Menulis emiten.csv — jalur yang sama dengan --ambil-emiten (berkas dulu, impor kemudian)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BarisJenis:
    """Satu baris `emiten.csv` hasil jalur `--ambil-jenis`, lengkap dengan asal turunannya."""

    tersimpan: EmitenTersimpan
    sector: str | None
    industry: str | None
    jenis: str | None

    @property
    def kode(self) -> str:
        return self.tersimpan.kode

    def sumber(self, sumber_turunan: str) -> str:
        """Sumber per baris = sumber yang diteruskan **+** keterangan turunannya (K21 batas (a)).

        Sumber aslinya tidak diganti: menuliskan hanya keterangan turunannya akan menghapus
        dari mana `nama`/`jumlah_saham`/`tanggal_notasi` baris itu berasal.
        """
        return f"{self.tersimpan.sumber} | {sumber_turunan}"


def sumber_turunan(baris: BarisJenis) -> str:
    return penjelasan_jenis(baris.jenis, baris.sector, baris.industry)


def _komentar(
    *, diambil_pada: date, jumlah_baris: int, jumlah_bank: int, jumlah_umum: int, jumlah_kosong: int
) -> tuple[str, ...]:
    """Penjelasan yang ikut tertulis **di dalam** berkas, supaya turunannya tidak salah dibaca.

    Baris kepala ditulis lebih dulu (oleh pemanggil), mengikuti aturan yang sama dengan
    `emiten.csv` dari KSEI: pembaca berkas mendeteksi pemisah kolom dari baris pertamanya.
    """
    return (
        "# " + "=" * 87,
        "# DAFTAR EMITEN — KOLOM `jenis` DITURUNKAN DARI SUMBER DATA (K21)",
        "# " + "=" * 87,
        "#",
        f"# Ditulis: {tampilan.tanggal(diambil_pada)} oleh `python -m mejasaham --ambil-jenis`.",
        f"# Baris: {jumlah_baris} ({jumlah_bank} bank_keuangan, {jumlah_umum} umum, "
        f"{jumlah_kosong} jenis tetap kosong).",
        "#",
        "# APA YANG DITURUNKAN, DAN DARI MANA",
        "#   jenis = bank_keuangan  bila `sector` sumber menyatakan jasa keuangan DAN `industry`",
        "#                          menyebut bank. Label mentahnya ikut di kolom `sumber` tiap baris.",
        "#   jenis = umum           bila sumber menyatakan sector/industry, tetapi bukan bank.",
        "#   jenis = KOSONG         bila sumber tidak menyatakan sector MAUPUN industry. Kosong di",
        "#                          sini berarti \"tidak dinyatakan\", dan itu BUKAN `umum`.",
        "#",
        "# APA YANG **TIDAK** DITURUNKAN — bukan lupa, dan bukan tebakan:",
        "#   siklikal_komoditas  \"emiten ini siklikal\" adalah PENILAIAN analis, dan tidak satu pun",
        "#                       sumber data menyatakannya. Ia tetap menunggu isian manusia.",
        "#   sektor_idx_ic       sumber data memakai taksonomi lain (mis. Financial Services),",
        "#                       bukan IDX-IC yang dipakai PRD. Pemetaan resminya tidak diterbitkan",
        "#                       siapa pun, jadi kolomnya dibiarkan seperti apa adanya (K12, P16).",
        "#   papan, status_notasi, free_float_persen  tidak dinyatakan sumber data ini.",
        "#",
        "# KOLOM `sektor_sumber` — sektor MENURUT SUMBER DATA (K25), dan BUKAN IDX-IC:",
        "#   Diisi dari `sector` sumber (mis. Financials, Energy, Basic Materials). Kolom ini",
        "#   dipakai kalkulator risiko untuk batas bobot per sektor PRD 9.7 SELAMA `sektor_idx_ic`",
        "#   belum terisi; begitu `sektor_idx_ic` diisi manusia, kolom itulah yang dipakai.",
        "#   Dua taksonomi tidak pernah dicampur dalam satu penjumlahan paparan.",
        "#",
        "# AKIBAT YANG PERLU ANDA TAHU: begitu sebuah emiten ber-jenis bank_keuangan, kriteria bank",
        "# (NPL, CAR, BOPO, NIM) mulai berlaku untuknya dan DER/coverage/CFO-NI BERHENTI dihitung",
        "# (PRD 8.4, AC-16). Karena itu `--saring` melaporkan sebarannya.",
        "#",
        "# SUMBER TIDAK RESMI. sector/industry datang dari penyedia data EOD, bukan dari laporan",
        "# resmi emiten; baris hasil turunan mengatakan itu apa adanya di kolom `sumber`.",
        "#",
        "# Kolom `jenis` yang SUDAH terisi tidak ditimpa: isian tangan Anda dipertahankan.",
        "#",
        "# Aturan format: lihat mejasaham/defaults/emiten.contoh.csv",
        "# " + "=" * 87,
    )


@dataclass(frozen=True)
class HasilTulisJenis:
    """Ringkasan satu kali penulisan `emiten.csv` hasil turunan."""

    jalur: Path
    jumlah_baris: int
    bank_keuangan: int
    umum: int
    kosong: int
    bank: tuple[str, ...]


def tulis_emiten_csv(
    baris: Iterable[BarisJenis],
    jalur: Path,
    *,
    diambil_pada: date,
) -> HasilTulisJenis:
    """Tulis `emiten.csv`; kembalikan ringkasannya.

    Berkasnya ditulis sebagai **berkas sementara di folder yang sama**, lalu diganti namanya
    menimpa tujuan. Folder yang sama dipakai supaya penggantian namanya atomik di filesystem yang
    sama; tanpa itu, kegagalan di tengah penulisan meninggalkan `emiten.csv` separuh jadi — dan
    berkas separuh jadi adalah semesta yang salah, bukan berkas yang rusak.
    """
    kolom = berkas.SPESIFIKASI["emiten"].nama_kolom
    daftar = tuple(sorted(baris, key=lambda satu: satu.kode))
    bank = tuple(satu.kode for satu in daftar if satu.jenis == "bank_keuangan")
    jumlah_umum = sum(1 for satu in daftar if satu.jenis == "umum")
    jumlah_kosong = sum(1 for satu in daftar if not satu.jenis)

    sementara = jalur.with_name(f"{jalur.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        with sementara.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
            penulis = csv.writer(berkas_tulis, delimiter=";", lineterminator="\n")
            penulis.writerow(kolom)
            for satu in _komentar(
                diambil_pada=diambil_pada,
                jumlah_baris=len(daftar),
                jumlah_bank=len(bank),
                jumlah_umum=jumlah_umum,
                jumlah_kosong=jumlah_kosong,
            ):
                berkas_tulis.write(satu + "\n")
            for satu in daftar:
                sel = {
                    "kode": satu.tersimpan.kode,
                    "nama": satu.tersimpan.nama,
                    "sektor_idx_ic": satu.tersimpan.sektor_idx_ic or "",
                    # Sektor menurut sumber data (K25). Yang ditulis adalah `sector` (kelompok
                    # luas seperti "Financials"/"Energy"), bukan `industry` yang lebih rinci:
                    # batas bobot per sektor PRD 9.7 menjaga **paparan satu kelompok**, dan
                    # kelompok yang terlalu rinci akan membuat batas 30% praktis tak terpakai.
                    "sektor_sumber": satu.sector or "",
                    "jenis": satu.jenis or "",
                    "papan": satu.tersimpan.papan or "",
                    "status_notasi": satu.tersimpan.status_notasi or "",
                    "tanggal_notasi": satu.tersimpan.tanggal_notasi or "",
                    "jumlah_saham": (
                        "" if satu.tersimpan.jumlah_saham is None else str(satu.tersimpan.jumlah_saham)
                    ),
                    "free_float_persen": "",  # tidak dinyatakan sumber data ini
                    "sumber": satu.sumber(sumber_turunan(satu)),
                    "dicatat_pada": diambil_pada.isoformat(),
                }
                penulis.writerow([sel[nama] for nama in kolom])
        os.replace(sementara, jalur)
    except OSError:
        # Berkas sementara tidak boleh tertinggal: ia akan terbaca sebagai `emiten.csv.tmp-…`
        # oleh siapa pun yang melihat foldernya, dan sisa yang membingungkan lebih buruk
        # daripada galat yang jelas.
        sementara.unlink(missing_ok=True)
        raise
    return HasilTulisJenis(
        jalur=jalur,
        jumlah_baris=len(daftar),
        bank_keuangan=len(bank),
        umum=jumlah_umum,
        kosong=jumlah_kosong,
        bank=bank,
    )


# ---------------------------------------------------------------------------------------
# Kerangka `rasio-bank.csv` dari daftar bank (K57, T67)
# ---------------------------------------------------------------------------------------


def kode_bank(sambungan: sqlite3.Connection) -> tuple[str, ...]:
    """Kode ber-`jenis='bank_keuangan'` pada revisi emiten terkini — calon isi kerangka (K57).

    Diambil dari basis data (`v_emiten_terkini`), bukan dari `emiten.csv`: berkas itu bisa sudah
    disunting tangan dan belum diimpor. Kodenya diurutkan supaya jalan yang sama menghasilkan
    berkas yang sama (A5).
    """
    return tuple(
        satu.kode for satu in emiten_tersimpan(sambungan) if satu.jenis == "bank_keuangan"
    )


@dataclass(frozen=True)
class HasilKerangkaRasioBank:
    """Ringkasan satu kali penulisan kerangka `rasio-bank.csv`."""

    jalur: Path
    kode: tuple[str, ...]


def _komentar_kerangka_rasio_bank(*, ditulis_pada: date, jumlah: int) -> tuple[str, ...]:
    """Penjelasan yang ikut tertulis **di dalam** kerangka, sesudah baris kepalanya.

    Isinya mengikat tiga hal yang paling mudah salah dibaca dari berkas kosong: bahwa yang kosong
    **memang** sengaja kosong (tidak ada jalur otomatisnya, K24), bahwa baris berasio kosong
    **ditolak** — jadi kerangka ini tidak bisa masuk sebagai nol (aturan keras 2), dan dari mana
    angkanya harus datang (publikasi resmi bank/OJK, bukan tebakan).
    """
    return (
        "# " + "=" * 87,
        "# KERANGKA RASIO BANK — daftar kode ber-jenis bank_keuangan (K21, K57)",
        "# " + "=" * 87,
        "#",
        f"# Ditulis: {tampilan.tanggal(ditulis_pada)} oleh `python -m mejasaham --kerangka-rasio-bank`.",
        f"# Baris: {jumlah} kode bank pada revisi emiten terkini di basis data.",
        "#",
        "# ANGKA DAN TANGGAL SENGAJA DIKOSONGKAN. Aplikasi TIDAK punya sumber otomatisnya: rasio",
        "# bank (NPL/CAR/BOPO/NIM) diterbitkan terpisah dari laporan keuangan, dan jalur PDF",
        "# sengaja tidak dibangun karena satu pemetaan glyph yang salah membalik SEMUA angka",
        "# rasio tanpa satu pun galat (K24).",
        "#",
        "# YANG HARUS ANDA ISI, dari publikasi RESMI bank/OJK (bukan dari blog atau aggregator):",
        "#   periode           akhir periode rasio, YYYY-MM-DD (mis. 2026-06-30)",
        "#   tgl_publikasi     tanggal rasio itu dipublikasikan — dipakai sejak tanggal itu (AC-15)",
        "#   npl_kotor_persen  persen, TITIK desimal (mis. 2.35 untuk 2,35%)",
        "#   car_persen        persen, titik desimal",
        "#   bopo_persen       persen, titik desimal",
        "#   nim_persen        persen, titik desimal",
        "#   sumber            dari mana angkanya + tanggal akses (wajib diisi)",
        "#",
        "# ATURAN YANG DITEGAKKAN PEMBACA BERKAS:",
        "#   * Isi minimal satu rasio per baris. Baris yang seluruh rasionya kosong DITOLAK —",
        "#     kerangka ini karena itu GAGAL BERISIK bila diimpor apa adanya, bukan masuk sebagai nol.",
        "#   * Kolom `kode`, `periode`, `tgl_publikasi`, dan `sumber` wajib; yang kosong ditolak.",
        "#   * Rasio yang kosong berarti \"tidak dilaporkan\", bukan nol: metriknya berstatus",
        "#     \"tidak dihitung\" dan bobotnya dialihkan (AC-3).",
        "#",
        "# BERKAS INI TIDAK DIIMPOR OLEH PERINTAH YANG MEMBUATNYA. Sesudah diisi:",
        "#   python -m mejasaham --impor \"<folder konfigurasi>\" --folder-data <folder data>",
        "#",
        "# Kodenya diambil dari daftar emiten ber-jenis bank_keuangan supaya tidak ada kode yang",
        "# salah eja; daftar itu sendiri datang dari --ambil-jenis (K21) atau isian tangan Anda.",
        "# =========================================================================================",
    )


def tulis_kerangka_rasio_bank(
    kode: Iterable[str], jalur: Path, *, ditulis_pada: date
) -> HasilKerangkaRasioBank:
    """Tulis **kerangka** `rasio-bank.csv`: satu baris per kode bank, seluruh sel selain `kode` kosong.

    Bentuk kolomnya **dipinjam** dari template bawaan (`berkas.SPESIFIKASI["rasio_bank"]`) — bukan
    ditulis ulang di sini: kolom yang ditambahkan ke template harus ikut muncul di kerangka tanpa
    ada berkas kedua yang perlu dirawat.

    Yang **tidak** dikerjakan fungsi ini, dan tidak boleh ditambahkan tanpa keputusan baru:
    mengisi angka rasio (tidak ada sumber otomatisnya, K24) dan mengimpornya. Berkasnya ditulis
    lewat berkas sementara di folder yang sama lalu diganti namanya, seperti `tulis_emiten_csv`:
    kegagalan di tengah penulisan tidak boleh meninggalkan kerangka separuh jadi.
    """
    kolom = berkas.SPESIFIKASI["rasio_bank"].nama_kolom
    daftar = tuple(sorted({satu.strip().upper() for satu in kode if satu and satu.strip()}))

    sementara = jalur.with_name(f"{jalur.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        with sementara.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
            penulis = csv.writer(berkas_tulis, delimiter=";", lineterminator="\n")
            penulis.writerow(kolom)
            for satu in _komentar_kerangka_rasio_bank(
                ditulis_pada=ditulis_pada, jumlah=len(daftar)
            ):
                berkas_tulis.write(satu + "\n")
            for satu in daftar:
                sel = dict.fromkeys(kolom, "")
                sel["kode"] = satu
                penulis.writerow([sel[nama] for nama in kolom])
        os.replace(sementara, jalur)
    except OSError:
        sementara.unlink(missing_ok=True)
        raise
    return HasilKerangkaRasioBank(jalur=jalur, kode=daftar)
