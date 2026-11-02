"""Kalender libur bursa dari pengumuman KSEI — jalur otomatis untuk U5 dan AC-8.

Kenapa modul ini ada
--------------------
`kalender-bursa.csv` menentukan arti "hari bursa terakhir" dan peringatan "snapshot basi"
(AC-8). Selama berkas itu kosong, laporan mutu hanya bisa mengatakan `kalender_bursa_kosong`,
dan "snapshot basi" tidak bisa dihitung sama sekali. IDX menerbitkan Kalender Libur Bursa
tahunan, tetapi **seluruh `idx.co.id` menolak akses otomatis** (HTTP 403, tantangan Cloudflare;
16 variasi URL dan 24 percobaan meniru TLS browser semuanya gagal — `docs/keputusan.md` 5.1).

KSEI menerbitkan hari libur dan cuti bersama sebagai **tindak lanjut eksplisit** atas pengumuman
IDX itu: nomor pengumuman IDX-nya disebut di dalam berkasnya (mis. berkas 2027 menyebut
`Peng-00169/BEI.POP/09-2026` perihal *Kalender Libur Bursa Tahun 2027*). K11 memutuskan sumber
itu boleh dipakai, dengan konsekuensi yang mengikat: hari bursa **diturunkan** sebagai
**hari kerja dikurangi daftar libur resmi**, bukan disalin dari daftar hari bursa (IDX tidak
menerbitkan daftar hari bursanya secara terbuka).

Tanpa dependensi baru
---------------------
Berkasnya PDF, dan PDF umumnya butuh pustaka tambahan. Yang dibutuhkan di sini hanya sebagian
kecil dari PDF: aliran isi halaman yang dipadatkan FlateDecode, dan operator teks `TJ`/`Tj`.
Keduanya bisa diurai dengan `zlib` + `re` dari pustaka bawaan Python, jadi K3 tidak perlu
diubah. Teks di berkas KSEI dipecah menjadi potongan-potongan kecil (satu huruf pun bisa jadi
satu potongan) demi kerning, sehingga modul ini menyusun ulang baris dari **koordinat** `Tm`/`Td`
yang menyertainya — bukan menempelkan potongan begitu saja.

Yang **tidak** dilakukan: OCR, membaca tabel yang berupa gambar, atau menebak potongan yang
tidak terbaca. Glif heksa yang tidak diterjemahkan dihitung dan dilaporkan, bukan dianggap
tidak ada.

Lima pemeriksaan sebelum hasilnya boleh dipakai
-----------------------------------------------
Berkas yang gagal salah satunya **ditolak**, bukan dipakai dengan tebakan (aturan keras 1):

1. balasannya benar-benar PDF (bukan halaman tantangan HTML yang menyamar);
2. di dalamnya disebut nomor pengumuman KSEI (`PENG-…/DIR/KSEI/…`) **dan** nomor pengumuman
   IDX (`Peng-…/BEI.POP/…`) — bukti tindak lanjut yang menjadi dasar K11;
3. setiap baris lampiran menyebut nama hari, dan nama hari itu **cocok** dengan tanggalnya;
4. nomor urut baris tabel lengkap `1..N` — baris yang hilang karena bentuk berkas berubah
   ketahuan, bukan hilang diam-diam;
5. seluruh tanggal di lampiran berada di tahun yang sama dengan tahun pada judul berkasnya;
6. berkasnya menyatakan menindaklanjuti **Kalender Libur Bursa** IDX — bukan sekadar menyebut
   nomor pengumuman IDX. Ini yang menjadi dasar K11, dan tanpa itu tanggalnya tidak boleh
   dipakai sebagai kalender bursa.

Keterbatasan yang diakui, bukan disembunyikan: kalender cara ini tidak tahu hari bursa yang
ditiadakan mendadak, dan tidak memuat hari libur untuk tahun yang pengumumannya sudah tidak
tersedia lagi di halaman KSEI — termasuk tahun yang berkasnya ada tetapi **tidak** menyatakan
menindaklanjuti Kalender Libur Bursa IDX. Berkas seperti itu ditolak dan dilaporkan, bukan
dipakai dengan tafsiran (terukur 9 Okt 2026: berkas 2025 menyebut pengumuman IDX perihal
kalender EBA/sukuk, bukan kalender libur bursa — jadi 2025 memang tidak masuk). Keduanya
dilaporkan apa adanya oleh laporan mutu (`U5`).
"""

from __future__ import annotations

import csv
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

from mejasaham import lokasi, tampilan
from mejasaham.berkas import NAMA_BERKAS_KALENDER, baca_kalender
from mejasaham.ingesti import GalatIngesti


class GalatTindakLanjut(GalatIngesti):
    """Berkas terbaca, tetapi bukan tindak lanjut Kalender Libur Bursa IDX (dasar K11).

    Dibedakan dari kegagalan lain karena penanganannya berbeda: berkas seperti ini **bukan**
    kegagalan seluruh pengambilan. Tahun yang berkasnya sah tetap dipakai, sedangkan tahun ini
    dilaporkan sebagai tidak tersedia — kalender yang lebih pendek lebih baik daripada kalender
    yang memuat tanggal dari sumber yang tidak memutuskan hal itu.
    """

#: Halaman resmi KSEI yang memuat tautan pengumuman hari libur & cuti bersama. Halaman ini yang
#: dipakai sebagai titik masuk, bukan nama berkas yang ditulis di kode: nama berkasnya berubah
#: (mis. `…Tahun_2026.pdf` diganti versi penyesuaian bernomor), sedangkan halamannya tetap
#: menunjuk versi yang berlaku.
POLA_URL_HALAMAN = "https://web.ksei.co.id/services/schedule-c-best-instruction"

#: Agen pengguna apa adanya — sama dengan `ksei.py`. KSEI menerima ini; menyamar sebagai
#: browser tidak diperlukan, dan menyamar berarti berbohong tentang siapa yang mengambil berkas.
AGEN_PENGGUNA = "MejaSaham/0.1 (pengambilan berkas publik KSEI; python-urllib)"

PERCOBAAN_BAWAAN = 3
JEDA_BAWAAN = 2.0
TIMEOUT_BAWAAN = 60.0

#: Kata yang menandai tautan kalender di halaman KSEI ("Jadwal Hari Libur dan Cuti Bersama…").
KATA_KALENDER = ("libur", "cuti bersama")

#: Jumlah baris lampiran paling sedikit yang masih masuk akal untuk satu tahun. Kalender libur
#: bursa selalu memuat belasan tanggal; angka ini hanya penjaga terhadap berkas yang bentuknya
#: berubah sehingga tabelnya tidak terbaca — bukan ambang yang berasal dari aturan bursa.
BARIS_MINIMUM = 5

NAMA_HARI = {
    "senin": 0,
    "selasa": 1,
    "rabu": 2,
    "kamis": 3,
    "jumat": 4,
    "jum'at": 4,
    "sabtu": 5,
    "minggu": 6,
}

#: Singkatan yang dipakai sebagian berkas. Diperiksa setelah nama penuh, dan hanya sebagai kata
#: utuh (`\b`) supaya "Sab" tidak ikut cocok di dalam kata lain.
SINGKATAN_HARI = {
    "sen": 0,
    "sel": 1,
    "rab": 2,
    "kam": 3,
    "jum": 4,
    "sab": 5,
    "min": 6,
}

POLA_TANGGAL = re.compile(r"\b(\d{1,2})-([A-Za-z]{3,5})-(\d{4})\b")
POLA_NAMA_HARI = re.compile(
    r"\b(Senin|Selasa|Rabu|Kamis|Jumat|Jum'at|Sabtu|Minggu|Sen|Sel|Rab|Kam|Jum|Sab|Min)\b",
    re.IGNORECASE,
)
POLA_KEPALA_TABEL = re.compile(r"\bNo\b.*\bTanggal\b.*\bKeterangan\b")
POLA_NOMOR_KSEI = re.compile(r"\bPENG-\d{4}/DIR/KSEI/\d{4}\b", re.IGNORECASE)
POLA_NOMOR_IDX = re.compile(r"\bPeng-\d{4,5}/BEI\.POP/\d{2}-\d{4}\b", re.IGNORECASE)
POLA_TAHUN = re.compile(r"\b(20\d{2})\b")

#: Frasa yang menyatakan bahwa pengumuman KSEI ini menindaklanjuti kalender libur **bursa**
#: (bukan hanya hari libur KSEI sendiri). Dicatat apa adanya di laporan, karena inilah dasar K11.
FRASA_TINDAK_LANJUT = "Kalender Libur Bursa"

#: Nama bulan di lampiran KSEI, diindeks menurut **tiga huruf pertamanya**: berkas yang berbeda
#: menyingkat bulan dengan panjang berbeda (`Jun`, tetapi juga `Agust` dan `Sept`). Dipetakan
#: sendiri, bukan lewat `strptime("%b")`, karena `%b` mengikuti locale mesin — di Windows
#: ber-locale Indonesia hasilnya berbeda untuk masukan yang sama. Salah baca bulan akan
#: ketahuan dari pemeriksaan nama hari terhadap tanggalnya, bukan lolos diam-diam.
BULAN_SINGKAT = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "mei": 5,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "agu": 8,
    "aug": 8,
    "ags": 8,
    "sep": 9,
    "okt": 10,
    "oct": 10,
    "nov": 11,
    "des": 12,
    "dec": 12,
}

KEPALA_CSV = ("tanggal", "hari_bursa", "keterangan", "sumber")


# ---------------------------------------------------------------------------------------
# Bentuk data
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TautanKalender:
    """Satu tautan berkas kalender di halaman KSEI, beserta tahun yang dinyatakannya."""

    tahun: int
    url: str
    judul: str


@dataclass(frozen=True)
class Potongan:
    """Satu potongan teks PDF dan tempatnya digambar.

    `aliran` penting: dua halaman bisa punya koordinat yang sama persis, jadi baris hanya boleh
    disusun di dalam satu aliran. `y` dipakai untuk mengelompokkan satu baris tabel (turun ke
    bawah), `x` untuk mengurutkan sel dari kiri ke kanan. `ukuran` adalah ukuran font yang
    berlaku saat potongan itu digambar — dipakai hanya untuk memperkirakan lebarnya.
    """

    aliran: int
    y: float
    x: float
    teks: str
    ukuran: float = 10.0


@dataclass(frozen=True)
class BarisTeks:
    """Satu baris visual hasil penyusunan potongan, lengkap dengan asal alirannya."""

    aliran: int
    y: float
    teks: str


@dataclass(frozen=True)
class HariLibur:
    """Satu baris lampiran: nomor urut, tanggal, nama hari **menurut sumbernya**, keterangan."""

    nomor: int
    tanggal: date
    hari: str
    keterangan: str


@dataclass(frozen=True)
class KalenderTahun:
    """Hasil urai satu pengumuman KSEI untuk satu tahun."""

    tahun: int
    url: str
    nomor_ksei: str
    nomor_idx: str
    nomor_lain: tuple[str, ...]
    hari_libur: tuple[HariLibur, ...]
    glif_tak_terbaca: int = 0
    #: Catatan bila tanggalnya diambil dari **revisi yang lebih lama** dari pengumuman yang
    #: ditautkan halaman (P19). `None` = berkas yang dipakai memang yang ditautkan halaman.
    revisi: str | None = None

    @property
    def jumlah(self) -> int:
        return len(self.hari_libur)

    def __str__(self) -> str:
        return (
            f"{self.tahun}: {self.jumlah} tanggal libur — KSEI {self.nomor_ksei} "
            f"(IDX {self.nomor_idx})"
        )


@dataclass(frozen=True)
class BarisKalender:
    """Satu baris `kalender-bursa.csv` sebelum ditulis."""

    tanggal: date
    hari_bursa: bool
    keterangan: str | None
    sumber: str


@dataclass(frozen=True)
class HasilAmbilKalender:
    """Laporan satu kali pengambilan kalender."""

    jalur: Path
    tahun: tuple[KalenderTahun, ...]
    baris: tuple[BarisKalender, ...]
    tautan_diabaikan: tuple[str, ...] = ()
    tahun_ditolak: tuple[str, ...] = ()
    #: Catatan percobaan mencari **revisi lebih lama** (P19): revisi mana yang dicoba, dan kenapa
    #: tidak dipakai. Dipisah dari `tahun_ditolak` karena artinya berbeda: daftar itu menjawab
    #: "tahun ini kenapa tidak ada", sedangkan catatan ini menjawab "apa saja yang sudah dicoba".
    catatan_revisi: tuple[str, ...] = ()
    jumlah_terbaca_ulang: int = 0
    jumlah_hari_bursa: int = 0
    jumlah_akhir_pekan: int = 0

    @property
    def jumlah_libur(self) -> int:
        return sum(satu.jumlah for satu in self.tahun)

    @property
    def jumlah_glif_tak_terbaca(self) -> int:
        return sum(satu.glif_tak_terbaca for satu in self.tahun)

    def __str__(self) -> str:
        bagian = ["Kalender libur bursa dari pengumuman KSEI:"]
        for satu in self.tahun:
            bagian.append(f"  {satu}")
            bagian.append(f"      berkas: {satu.url.rsplit('/', 1)[-1]}")
            if satu.revisi:
                bagian.append(f"      {satu.revisi}")
        if self.nomor_lain_semua:
            bagian.append(f"  nomor pengumuman lain yang disebut di berkas: {self.nomor_lain_semua}")
        bagian.append(
            f"  ditulis: {self.jalur} — {len(self.baris)} baris "
            f"({self.jumlah_libur} libur resmi, {self.jumlah_akhir_pekan} akhir pekan, "
            f"{self.jumlah_hari_bursa} hari bursa), {self.jumlah_terbaca_ulang} terbaca ulang"
        )
        if self.tahun_ditolak:
            bagian.append(
                "  TAHUN YANG TIDAK DIPAKAI (berkasnya tidak menindaklanjuti Kalender Libur Bursa "
                "IDX; K11 tidak mencakupnya):"
            )
            bagian.extend(f"    - {satu}" for satu in self.tahun_ditolak)
        if self.catatan_revisi:
            bagian.append("  PERCOBAAN REVISI LEBIH LAMA (P19 — dipakai hanya bila tanggalnya identik):")
            bagian.extend(f"    - {satu}" for satu in self.catatan_revisi)
        if self.tautan_diabaikan:
            bagian.append(
                "  tautan yang TIDAK dipakai (tahunnya tidak bisa dipastikan dari judulnya):"
            )
            bagian.extend(f"    - {satu}" for satu in self.tautan_diabaikan)
        if self.jumlah_glif_tak_terbaca:
            bagian.append(
                f"  CATATAN: {self.jumlah_glif_tak_terbaca} glif heksa tidak diterjemahkan "
                "(bukan bagian dari tabel lampiran); seluruh tanggal tetap terbaca."
            )
        bagian.extend(
            [
                "",
                "Hari bursa DITURUNKAN sebagai hari kerja (Sen–Jum) dikurangi daftar libur resmi —",
                "bukan disalin dari daftar hari bursa, karena IDX tidak menerbitkannya terbuka (K11).",
                "Libur yang ditiadakan mendadak tidak diketahui cara ini; laporan mutu tetap",
                "memperingatkan bila kalender belum memuat tanggal snapshot (U5), bukan menganggapnya lulus.",
                "",
                f'Langkah berikutnya:  python -m mejasaham --impor "{self.jalur.parent}"',
            ]
        )
        return "\n".join(bagian)

    @property
    def nomor_lain_semua(self) -> str:
        lain = sorted({nomor for satu in self.tahun for nomor in satu.nomor_lain})
        return ", ".join(lain)


# ---------------------------------------------------------------------------------------
# Menemukan berkas di halaman KSEI
# ---------------------------------------------------------------------------------------


class _PengumpulTautan(HTMLParser):
    """Kumpulkan pasangan (href, teks jangkar) dari halaman KSEI."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tautan: list[tuple[str, str]] = []
        self._href: str | None = None
        self._teks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        self._href = dict(attrs).get("href")
        self._teks = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._teks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        teks = " ".join("".join(self._teks).split())
        self.tautan.append((self._href, teks))
        self._href = None
        self._teks = []


def _tahun_dari(teks: str) -> int | None:
    cocok = POLA_TAHUN.search(teks)
    return int(cocok.group(1)) if cocok else None


def temukan_berkas(
    html: str, *, halaman: str = POLA_URL_HALAMAN
) -> tuple[tuple[TautanKalender, ...], tuple[str, ...]]:
    """Temukan tautan kalender di halaman KSEI; kembalikan (dipakai, diabaikan).

    Tahun diambil dari **judul tautannya** lebih dulu (`… Tahun 2027`), baru dari nama
    berkasnya. Tautan yang menyebut libur/cuti tetapi tahunnya tidak bisa dipastikan
    dikembalikan sebagai "diabaikan" supaya terlihat, bukan hilang tanpa jejak.

    Nama berkas yang dipakai adalah `href` **apa adanya** — termasuk yang di halaman KSEI
    terpotong dengan `....`. Terukur 9 Okt 2026: berkas 2026 memang tersimpan dengan nama
    terpotong itu, jadi menebak nama "yang seharusnya" justru akan gagal.
    """
    pengumpul = _PengumpulTautan()
    pengumpul.feed(html)
    pengumpul.close()

    dipakai: list[TautanKalender] = []
    diabaikan: list[str] = []
    for href, judul in pengumpul.tautan:
        gabungan = f"{href} {judul}".lower()
        if ".pdf" not in href.lower() or not any(kata in gabungan for kata in KATA_KALENDER):
            continue
        tahun = _tahun_dari(judul) or _tahun_dari(href)
        if tahun is None:
            diabaikan.append(f"{judul or '(tanpa judul)'} — {href}")
            continue
        dipakai.append(
            TautanKalender(tahun=tahun, url=urllib.parse.urljoin(halaman, href), judul=judul)
        )

    if not dipakai:
        raise GalatIngesti(
            f"tidak ada tautan kalender libur bursa yang bisa dibaca di {halaman}"
            + (f"; {len(diabaikan)} tautan diabaikan karena tahunnya tidak jelas" if diabaikan else "")
            + ". Halaman KSEI bisa berubah bentuk; periksa halamannya, lalu isi "
            "kalender-bursa.csv dengan tangan bila tautannya memang sudah tidak ada."
        )
    return tuple(sorted(dipakai, key=lambda satu: satu.tahun)), tuple(diabaikan)


def _buka(url: str, timeout: float):
    permintaan = urllib.request.Request(url, headers={"User-Agent": AGEN_PENGGUNA})
    return urllib.request.urlopen(permintaan, timeout=timeout)


def unduh(
    url: str,
    *,
    di_mana: str,
    percobaan: int = PERCOBAAN_BAWAAN,
    jeda: float = JEDA_BAWAAN,
    timeout: float = TIMEOUT_BAWAAN,
    buka: Callable[[str, float], object] | None = None,
) -> bytes:
    """Unduh satu berkas dengan percobaan ulang; kegagalan menyebut sebabnya, bukan "gagal"."""
    pembuka = _buka if buka is None else buka
    galat_terakhir = ""
    for nomor in range(1, percobaan + 1):
        try:
            with pembuka(url, timeout) as balasan:  # type: ignore[union-attr]
                return balasan.read()
        except urllib.error.HTTPError as galat:
            galat_terakhir = f"HTTP {galat.code}"
            if galat.code == 404:
                break  # berkasnya memang tidak ada di alamat itu
        except (urllib.error.URLError, TimeoutError, OSError) as galat:
            galat_terakhir = f"{type(galat).__name__}: {galat}"
        if nomor < percobaan:
            time.sleep(jeda * nomor)
    raise GalatIngesti(f"{di_mana}: gagal mengunduh {url} — {galat_terakhir}")


# ---------------------------------------------------------------------------------------
# Mengurai PDF: aliran teks -> potongan -> baris
# ---------------------------------------------------------------------------------------

#: Satu aliran PDF. Batas akhirnya penanda `endstream` **tanpa** menuntut baris baru di depannya:
#: byte terakhir data terpadat bisa kebetulan berupa `0x0A`, dan menuntut `\n` di situ memotong
#: satu byte dari aliran sehingga dekompresinya gagal (terukur pada berkas uji buatan sendiri).
#: Sisa byte sesudah aliran zlib diabaikan oleh `decompressobj` sebagai `unused_data`.
POLA_ALIRAN = re.compile(rb"stream\r?\n(.*?)endstream", re.S)

#: Operator yang menentukan tempat teks digambar, dan operator yang menggambar teks.
#: `Tm` menetapkan matriks teks (x y mutlak), `Td`/`TD` menggesernya relatif, `T*` turun satu
#: baris. Teks datang sebagai larik `[…] TJ` (dengan angka kerning di antaranya) atau `(…) Tj`.
POLA_OPERATOR = re.compile(
    rb"""
      (?P<tm>(?:-?[\d.]+\s+){6}Tm)
    | (?P<td>(?:-?[\d.]+\s+){2}(?:Td|TD))
    | (?P<turun>T\*)
    | (?P<font>/[^\s/]+\s+[\d.]+\s+Tf)
    | (?P<larik>\[(?:[^\[\]\\]|\\.)*\]\s*TJ)
    | (?P<literal>\((?:\\.|[^()\\])*\)\s*Tj)
    | (?P<heksa><[0-9A-Fa-f\s]*>\s*Tj)
    """,
    re.X | re.S,
)
POLA_LITERAL = re.compile(rb"\(((?:\\.|[^()\\])*)\)", re.S)
POLA_HEKSA_DALAM = re.compile(rb"<([0-9A-Fa-f\s]*)>")
POLA_TOKEN_TEKS = re.compile(rb"\(((?:\\.|[^()\\])*)\)|<([0-9A-Fa-f\s]*)>", re.S)

#: Struktur PDF yang dibutuhkan untuk menerjemahkan glif font CID (`/Identity-H` + `/ToUnicode`):
#: objek bernomor, kamus `/Font` di sumber daya halaman, dan peta `bfchar`/`bfrange`. Pengumuman
#: pembukaan suspensi (UPT) IDX menulis seluruh isinya dengan font seperti itu.
POLA_OBJEK = re.compile(rb"(\d+)\s+\d+\s+obj\b(.*?)endobj", re.S)
POLA_KAMUS_FONT = re.compile(rb"/Font\s*(?:<<(.*?)>>|(\d+)\s+\d+\s+R)", re.S)
POLA_RUJUKAN_NAMA = re.compile(rb"/([^\s/<>\[\]()]+)\s*(\d+)\s+\d+\s+R")
POLA_TOUNICODE = re.compile(rb"/ToUnicode\s+(\d+)\s+\d+\s+R")
POLA_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
POLA_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
POLA_RENTANG = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]*>|\[[^\]]*\])")

#: Tinggi satu baris menurut operator `T*` bila berkas tidak menyatakan `TL` (jarak baris).
TINGGI_BARIS_BAWAAN = 12.0

#: Dua potongan dengan selisih `y` di bawah ini dianggap satu baris. Berkas KSEI memakai selisih
#: 0,1 satuan untuk sel-sel satu baris (mis. hari di 116,1 dan tanggal di 174,6) dan ~23,9
#: satuan antar baris tabel, jadi ambang ini longgar di kedua arah.
TOLERANSI_BARIS = 2.5

#: Perkiraan lebar rata-rata satu karakter dibanding ukuran font, dan kelonggaran sebelum dua
#: potongan dianggap terpisah oleh sel yang berbeda. Dipakai **hanya** untuk memutuskan perlu
#: tidaknya satu spasi di antara dua potongan; salah perkiraan di sini berarti spasi yang
#: kurang atau lebih, bukan tanggal yang salah.
LEBAR_RATA_KARAKTER = 0.5
TOLERANSI_JARAK = 0.25
UKURAN_FONT_BAWAAN = 10.0


def _unescape(mentah: bytes) -> bytes:
    """Terjemahkan escape PDF di dalam string literal (`\\(`, `\\)`, `\\n`, oktal)."""
    keluar = bytearray()
    i = 0
    while i < len(mentah):
        satu = mentah[i : i + 1]
        if satu == b"\\" and i + 1 < len(mentah):
            lanjut = mentah[i + 1 : i + 2]
            peta = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}
            if lanjut in peta:
                keluar += peta[lanjut]
                i += 2
                continue
            if lanjut.isdigit():
                j = 0
                while j < 3 and i + 1 + j < len(mentah) and mentah[i + 1 + j : i + 2 + j].isdigit():
                    j += 1
                keluar.append(int(mentah[i + 1 : i + 1 + j], 8) & 0xFF)
                i += 1 + j
                continue
            keluar += lanjut
            i += 2
            continue
        keluar += satu
        i += 1
    return bytes(keluar)


def _isi_aliran(badan: bytes) -> bytes | None:
    cocok = POLA_ALIRAN.search(badan)
    if cocok is None:
        return None
    if b"/FlateDecode" not in badan[: cocok.start()]:
        return cocok.group(1)
    try:
        return zlib.decompressobj().decompress(cocok.group(1))
    except zlib.error:
        return None


def _objek(data: bytes) -> dict[int, bytes]:
    """Objek bernomor menurut urutan berkas; definisi belakangan (pembaruan bertahap) menang.

    Objek di dalam `/ObjStm` dibongkar di tempat aliran itu berada, supaya urutan "yang belakangan
    menang" tetap berlaku untuknya.
    """
    objek: dict[int, bytes] = {}
    for cocok in POLA_OBJEK.finditer(data):
        nomor, badan = int(cocok.group(1)), cocok.group(2)
        objek[nomor] = badan
        if b"/ObjStm" not in badan.split(b"stream", 1)[0]:
            continue
        isi = _isi_aliran(badan)
        awal = re.search(rb"/First\s+(\d+)", badan)
        if isi is None or awal is None:
            continue
        kepala = [int(satu) for satu in isi[: int(awal.group(1))].split()]
        tempat = [int(awal.group(1)) + satu for satu in kepala[1::2]] + [len(isi)]
        for anak, mulai, akhir in zip(kepala[::2], tempat, tempat[1:]):
            objek[anak] = isi[mulai:akhir]
    return objek


def _peta_cmap(isi: bytes, *, di_mana: str) -> tuple[dict[bytes, str], int]:
    """Peta kode glif → teks Unicode dari satu CMap `/ToUnicode`, beserta panjang kodenya."""
    peta: dict[bytes, str] = {}
    for blok in POLA_BFCHAR.findall(isi):
        heksa = [bytes.fromhex(satu.decode()) for satu in POLA_HEKSA_DALAM.findall(blok)]
        if len(heksa) % 2:
            raise GalatIngesti(f"{di_mana}: blok bfchar ToUnicode tidak berpasangan")
        for asal, tujuan in zip(heksa[::2], heksa[1::2]):
            peta[asal] = tujuan.decode("utf-16-be")
    for blok in POLA_BFRANGE.findall(isi):
        for bawah, atas, tujuan in POLA_RENTANG.findall(blok):
            lebar = len(bawah) // 2
            dari, sampai = int(bawah, 16), int(atas, 16)
            if tujuan.startswith(b"["):
                daftar = [bytes.fromhex(satu.decode()) for satu in POLA_HEKSA_DALAM.findall(tujuan)]
                if len(daftar) != sampai - dari + 1:
                    raise GalatIngesti(f"{di_mana}: rentang bfrange ToUnicode tidak sepanjang larik tujuannya")
                for geser, satu in enumerate(daftar):
                    peta[(dari + geser).to_bytes(lebar, "big")] = satu.decode("utf-16-be")
                continue
            dasar = bytes.fromhex(tujuan.strip(b"<>").decode())
            for geser in range(sampai - dari + 1):
                peta[(dari + geser).to_bytes(lebar, "big")] = (
                    (int.from_bytes(dasar, "big") + geser).to_bytes(len(dasar), "big").decode("utf-16-be")
                )
    panjang = {len(kode) for kode in peta}
    if len(panjang) != 1:
        raise GalatIngesti(f"{di_mana}: CMap ToUnicode {'kosong' if not panjang else 'berpanjang kode campuran'}")
    return peta, panjang.pop()


def _peta_font(data: bytes, *, di_mana: str) -> dict[bytes, tuple[dict[bytes, str], int] | None]:
    """Nama font sumber daya (`F4`) → peta ToUnicode-nya; `None` = nama itu dipakai dua font berbeda.

    Pengurai ini tidak mengikuti halaman per halaman, jadi nama font dibaca dari seluruh kamus
    `/Font` di berkas. Nama yang menunjuk dua peta berbeda tidak ditebak: teks berfont itu ditolak.
    """
    objek = _objek(data)
    rujukan: dict[bytes, set[int]] = {}
    for cocok in POLA_KAMUS_FONT.finditer(data):
        isi = cocok.group(1) if cocok.group(1) is not None else objek.get(int(cocok.group(2)), b"")
        for nama, nomor in POLA_RUJUKAN_NAMA.findall(isi):
            badan = objek.get(int(nomor), b"")
            tounicode = POLA_TOUNICODE.search(badan)
            if b"/Font" in badan and tounicode is not None:
                rujukan.setdefault(nama, set()).add(int(tounicode.group(1)))
    peta: dict[bytes, tuple[dict[bytes, str], int] | None] = {}
    for nama, nomor_cmap in rujukan.items():
        terbaca = set()
        for nomor in nomor_cmap:
            isi = _isi_aliran(objek.get(nomor, b""))
            if isi is None:
                raise GalatIngesti(f"{di_mana}: CMap ToUnicode objek {nomor} tidak terbaca")
            satu, panjang = _peta_cmap(isi, di_mana=di_mana)
            terbaca.add((tuple(sorted(satu.items())), panjang))
        if len(terbaca) == 1:
            butir, panjang = terbaca.pop()
            peta[nama] = (dict(butir), panjang)
        else:
            peta[nama] = None
    return peta


def _genap(heksa: bytes) -> str:
    """String heksa PDF: spasi diabaikan, digit ganjil terakhir dianggap diikuti 0 (ISO 32000 7.3.4.3)."""
    bersih = re.sub(rb"\s+", b"", heksa).decode()
    return bersih + "0" * (len(bersih) % 2)


def _terjemahkan(mentah: bytes, peta: dict[bytes, str], panjang: int) -> tuple[str, int]:
    """Terjemahkan bait glif lewat CMap; kembalikan (teks, jumlah glif yang tidak ada di peta)."""
    teks: list[str] = []
    hilang = 0
    for mulai in range(0, len(mentah) - len(mentah) % panjang, panjang):
        satu = peta.get(mentah[mulai : mulai + panjang])
        if satu is None:
            hilang += 1
        else:
            teks.append(satu)
    return "".join(teks), hilang + (1 if len(mentah) % panjang else 0)


def potongan_teks(
    data: bytes, *, di_mana: str, terjemahkan_font: bool = False
) -> tuple[tuple[Potongan, ...], int]:
    """Kumpulkan seluruh potongan teks PDF beserta koordinatnya; kembalikan (potongan, heksa).

    Aliran yang tidak bisa didekompresi (gambar JPEG, data lain) dilewati tanpa keluhan karena
    memang bukan teks. Balasan yang bukan PDF ditolak di depan: halaman tantangan HTML yang
    menyamar sebagai berkas akan terbaca sebagai "kalender kosong" bila tidak diperiksa.

    `terjemahkan_font=True` menerjemahkan teks berfont yang punya `/ToUnicode` (glif CID, string
    heksa) lewat petanya; glif yang tidak ada di peta ikut dihitung di `heksa`. Bawaannya mati
    supaya pembacaan berkas KSEI tidak berubah.
    """
    if not data.startswith(b"%PDF"):
        awal = data[:16]
        raise GalatIngesti(
            f"{di_mana}: balasan bukan berkas PDF (awalannya {awal!r}). Halaman tantangan atau "
            "halaman galat tidak boleh diperlakukan sebagai kalender kosong."
        )

    peta_font = _peta_font(data, di_mana=di_mana) if terjemahkan_font else {}
    potongan: list[Potongan] = []
    heksa_tak_terbaca = 0
    for nomor, mentah in enumerate(POLA_ALIRAN.findall(data)):
        pengurai = zlib.decompressobj()
        try:
            isi = pengurai.decompress(mentah)
        except zlib.error:
            continue
        if b"TJ" not in isi and b"Tj" not in isi:
            continue
        if not pengurai.eof:
            # Aliran yang memuat teks tetapi tidak selesai utuh: isinya bisa kehilangan baris
            # tabel di ujungnya. Diteruskan berarti ada tanggal yang hilang tanpa suara.
            raise GalatIngesti(
                f"{di_mana}: aliran teks ke-{nomor} di dalam PDF tidak utuh "
                f"({len(isi)} byte terbaca sebelum terpotong). Berkasnya tidak dipakai daripada "
                "membaca kalender yang kehilangan sebagian tanggal."
            )
        x = y = 0.0
        ukuran = UKURAN_FONT_BAWAAN
        font = b""
        for cocok in POLA_OPERATOR.finditer(isi):
            jenis = cocok.lastgroup
            if jenis == "tm":
                angka = cocok.group().split()
                x, y = float(angka[4]), float(angka[5])
                continue
            if jenis == "td":
                angka = cocok.group().split()
                x += float(angka[0])
                y += float(angka[1])
                continue
            if jenis == "turun":
                y -= TINGGI_BARIS_BAWAAN
                continue
            if jenis == "font":
                font = cocok.group().split()[0][1:]
                ukuran = float(cocok.group().split()[-2])
                continue
            if font in peta_font and jenis in ("larik", "literal", "heksa"):
                if peta_font[font] is None:
                    raise GalatIngesti(
                        f"{di_mana}: nama font /{font.decode('latin-1')} menunjuk dua peta ToUnicode "
                        "berbeda; teksnya tidak diterjemahkan dengan tebakan"
                    )
                peta, panjang = peta_font[font]
                bait = b"".join(
                    _unescape(literal) if heksa is None else bytes.fromhex(_genap(heksa))
                    for literal, heksa in (
                        (satu.group(1), None) if satu.group(2) is None else (None, satu.group(2))
                        for satu in POLA_TOKEN_TEKS.finditer(cocok.group())
                    )
                )
                teks, hilang = _terjemahkan(bait, peta, panjang)
                heksa_tak_terbaca += hilang
                if teks:
                    potongan.append(Potongan(aliran=nomor, y=y, x=x, teks=teks, ukuran=ukuran))
                continue
            if jenis == "heksa":
                heksa_tak_terbaca += 1
                continue
            if jenis not in ("larik", "literal"):
                continue
            if jenis == "larik":
                heksa_tak_terbaca += len(POLA_HEKSA_DALAM.findall(cocok.group()))
            teks = b"".join(
                _unescape(satu) for satu in POLA_LITERAL.findall(cocok.group())
            ).decode("latin-1")
            if teks:
                potongan.append(Potongan(aliran=nomor, y=y, x=x, teks=teks, ukuran=ukuran))
    return tuple(potongan), heksa_tak_terbaca


def rapikan(teks: str) -> str:
    """Rapikan satu baris: spasi berlebih hilang, dan spasi di sekitar tanda hubung dibuang.

    Bagian kedua itu bukan kosmetik. Teks PDF datang sebagai potongan terpisah, sehingga
    `Peng-00169/BEI.POP/09-2026` tersusun dari potongan `Peng`, `-`, `00169/BEI.POP/09`, `-`,
    `2026`; tanpa dirapikan, nomor pengumuman dan tanggal tidak bisa dikenali sama sekali.
    """
    return re.sub(r"\s*-\s*", "-", " ".join(teks.split()))


def _pemisah(sebelum: Potongan, sesudah: Potongan) -> str:
    """Putuskan perlu tidaknya satu spasi di antara dua potongan yang berdampingan.

    Berkas KSEI memecah teks dengan dua cara yang berbeda, dan keduanya harus benar:

    * berkas 2025 menaruh spasi sebagai potongan tersendiri (`' '` di antara sel), sehingga
      potongan-potongan di dalam satu kata (`'S'`, `'enin'`) **harus** disambung tanpa spasi;
    * berkas 2027 menaruh spasi di dalam potongan (`'Jumat '`), dan memisahkan sel hanya dengan
      lompatan koordinat.

    Karena itu aturannya: pakai spasi yang sudah ada di dalam potongan bila ada; kalau tidak,
    hitung perkiraan lebar potongan sebelumnya dan baru sisipkan spasi bila `x` potongan
    berikutnya jelas berada di sebelahnya.
    """
    if sebelum.teks[-1:].isspace() or sesudah.teks[:1].isspace():
        return ""
    perkiraan = len(sebelum.teks) * LEBAR_RATA_KARAKTER * sebelum.ukuran
    if sesudah.x - sebelum.x > perkiraan + TOLERANSI_JARAK * sebelum.ukuran:
        return " "
    return ""


def _gabung(grup: Sequence[Potongan]) -> str:
    """Susun potongan satu baris menjadi teks, dengan spasi hanya di tempat yang perlu."""
    teks = grup[0].teks
    for sebelumnya, satu in zip(grup, grup[1:]):
        teks += _pemisah(sebelumnya, satu) + satu.teks
    return teks


def baris_teks(
    potongan: Sequence[Potongan], *, toleransi: float = TOLERANSI_BARIS
) -> tuple[BarisTeks, ...]:
    """Susun potongan menjadi baris: kelompokkan per aliran dan `y`, urutkan per `x`.

    Urutan baca tidak diambil dari urutan operator di dalam berkas (yang bisa melompat), tetapi
    dari koordinat: aliran sesuai urutan di berkas, lalu baris dari atas ke bawah, lalu sel dari
    kiri ke kanan.
    """
    urut = sorted(potongan, key=lambda satu: (satu.aliran, -satu.y, satu.x))
    grup: list[list[Potongan]] = []
    for satu in urut:
        if (
            grup
            and grup[-1][-1].aliran == satu.aliran
            and abs(grup[-1][-1].y - satu.y) <= toleransi
        ):
            grup[-1].append(satu)
            continue
        grup.append([satu])
    return tuple(
        BarisTeks(
            aliran=satu[0].aliran,
            y=satu[0].y,
            # Sel diurutkan menurut `x`, bukan menurut `y`: satu sel bisa digambar 0,1 satuan
            # lebih rendah dari sel lain di baris yang sama (berkas 2027 menaruh kolom "Hari" di
            # y=638,6 sedangkan tanggalnya di y=638,7), dan urutan `y` akan menaruh nama hari di
            # ujung baris.
            teks=rapikan(_gabung(sorted(satu, key=lambda potong: potong.x))),
        )
        for satu in grup
    )


# ---------------------------------------------------------------------------------------
# Mengurai lampiran: baris tabel -> tanggal libur
# ---------------------------------------------------------------------------------------


def _tanggal_lampiran(teks: str, di_mana: str) -> tuple[date, str, re.Match[str]]:
    """Ambil satu tanggal `1-Jan-2027` dari baris tabel; dua tanggal sekaligus ditolak."""
    temuan = list(POLA_TANGGAL.finditer(teks))
    if len(temuan) != 1:
        raise GalatIngesti(
            f"{di_mana}: baris tabel memuat {len(temuan)} tanggal ({teks!r}); diharapkan tepat "
            "satu. Bentuk lampirannya berubah — periksa berkasnya sebelum dipakai."
        )
    cocok = temuan[0]
    hari, bulan, tahun = cocok.groups()
    nomor_bulan = BULAN_SINGKAT.get(bulan[:3].lower())
    if nomor_bulan is None:
        raise GalatIngesti(f"{di_mana}: bulan {bulan!r} tidak dikenali pada {teks!r}")
    try:
        tanggal = date(int(tahun), nomor_bulan, int(hari))
    except ValueError as galat:
        raise GalatIngesti(f"{di_mana}: tanggal {teks!r} tidak ada di kalender ({galat})") from galat
    return tanggal, cocok.group(), cocok


def _hari_lampiran(teks: str, di_mana: str) -> tuple[str, int]:
    """Ambil nama hari dari baris tabel; nama hari itulah yang dipakai memeriksa tanggalnya.

    Nama hari yang dipakai adalah yang berada **sebelum** tanggalnya. Kalau tidak ada di sana,
    seluruh baris dicari sebagai cadangan: urutan kolom bisa berbeda antar berkas, dan yang
    penting bukan letaknya melainkan bahwa nama hari itu ada dan cocok dengan tanggalnya.
    """
    temuan = POLA_NAMA_HARI.findall(teks)
    if len(temuan) != 1:
        raise GalatIngesti(
            f"{di_mana}: baris tabel memuat {len(temuan)} nama hari ({teks!r}); diharapkan tepat "
            "satu. Tanpa nama hari, tanggalnya tidak bisa diperiksa terhadap kalender."
        )
    nama = temuan[0]
    kunci = nama.lower()
    nomor = NAMA_HARI.get(kunci, SINGKATAN_HARI.get(kunci))
    if nomor is None:
        raise GalatIngesti(f"{di_mana}: nama hari {nama!r} tidak dikenali")
    return nama, nomor


def baris_lampiran(teks: str, *, di_mana: str) -> HariLibur:
    """Urai satu baris lampiran: nomor urut, nama hari, tanggal, keterangan.

    Kolomnya dipisahkan menurut **posisi tanggalnya**, bukan menurut urutan potongan: nomor dan
    nama hari harus berada sebelum tanggal, keterangan sesudahnya. Dengan begitu keterangan yang
    kebetulan memuat nama hari tidak membuat barisnya ditolak.

    Nama hari di berkas **diperiksa** terhadap tanggalnya. Kalau tidak cocok, berarti
    penguraiannya salah (koordinat tertukar, kolom meleset) — dan salah di sini berarti kalender
    yang salah tanpa terlihat salah. Karena itu pemeriksaannya menolak, bukan memperingatkan.
    """
    tanggal, tanggal_teks, cocok = _tanggal_lampiran(teks, di_mana)
    sebelum, sesudah = teks[: cocok.start()], teks[cocok.end() :]

    awal = re.match(r"\s*(\d{1,3})(?![\d-])", sebelum)
    if awal is None:
        raise GalatIngesti(
            f"{di_mana}: baris tabel tidak dimulai nomor urut ({teks!r}). Nomor urut dipakai "
            "memastikan tidak ada baris tabel yang hilang."
        )
    nomor = int(awal.group(1))
    sisa = sebelum[awal.end() :]
    hari, nomor_hari = _hari_lampiran(sisa if POLA_NAMA_HARI.search(sisa) else teks, di_mana)

    if nomor_hari != tanggal.weekday():
        nama_benar = [nama for nama, angka in NAMA_HARI.items() if angka == tanggal.weekday()]
        raise GalatIngesti(
            f"{di_mana}: baris {nomor} menyebut {hari} untuk {tanggal_teks}, padahal tanggal itu "
            f"jatuh pada {nama_benar[0]}. Penguraian lampiran tidak bisa dipercaya; periksa "
            "berkasnya."
        )

    keterangan = rapikan(sesudah).strip(" -–—|")
    if not keterangan:
        raise GalatIngesti(
            f"{di_mana}: baris {nomor} ({tanggal_teks}) tidak memuat keterangan apa pun. "
            "Baris tanpa keterangan tidak boleh diteruskan sebagai libur tanpa nama."
        )
    return HariLibur(nomor=nomor, tanggal=tanggal, hari=hari, keterangan=keterangan)


def baris_lampiran_dari(baris: Sequence[BarisTeks], *, di_mana: str) -> tuple[HariLibur, ...]:
    """Ambil baris tabel lampiran: mulai dari kepalanya (`No … Tanggal … Keterangan`) sampai
    baris pertama yang bukan baris tabel.

    Tabelnya dibatasi begitu supaya tanggal yang muncul di luar tabel (tanggal surat, alamat,
    catatan kaki) tidak ikut terbaca sebagai hari libur. Baris yang terlewat di tengah tabel
    tetap ketahuan dari pemeriksaan nomor urut di `urai_kalender`.
    """
    kepala = [nomor for nomor, satu in enumerate(baris) if POLA_KEPALA_TABEL.search(satu.teks)]
    if not kepala:
        raise GalatIngesti(
            f"{di_mana}: kepala tabel lampiran (No … Tanggal … Keterangan) tidak ditemukan. "
            "Bentuk lampiran berubah; kalender tidak diambil dari berkas ini."
        )

    keluar: list[HariLibur] = []
    mulai = kepala[0] + 1
    aliran = baris[kepala[0]].aliran
    for nomor, satu in enumerate(baris[mulai:], start=mulai):
        if satu.aliran != aliran:
            break
        if not re.match(r"\s*\d{1,3}(?![\d-])", satu.teks):
            break
        keluar.append(baris_lampiran(satu.teks, di_mana=f"{di_mana} baris teks {nomor}"))
    return tuple(keluar)


def urai_kalender(
    data: bytes, *, url: str, tahun: int, wajib_tindak_lanjut: bool = True
) -> KalenderTahun:
    """Urai satu berkas pengumuman KSEI menjadi kalender satu tahun.

    Seluruh pemeriksaan di docstring modul dijalankan di sini. Berkas yang gagal salah satunya
    ditolak dengan pesan yang menyebut apa yang tidak cocok — bukan dikembalikan sebagai
    kalender setengah jadi.

    `wajib_tindak_lanjut=False` melewati **hanya** syarat T31 (berkasnya menyatakan menindaklanjuti
    *Kalender Libur Bursa* IDX); seluruh pemeriksaan lain tetap berlaku. Itu dipakai P19: berkas
    yang ditautkan halaman kadang berupa revisi yang menindaklanjuti hal lain, sedangkan
    tanggalnya dibutuhkan sebagai **pembanding** bagi revisi lama yang lulus syarat. Hasil dengan
    tanda ini **tidak pernah** dipakai sebagai kalender; ia hanya bahan perbandingan.
    """
    nama = url.rsplit("/", 1)[-1]
    di_mana = f"{nama} ({url})"
    potongan, heksa = potongan_teks(data, di_mana=di_mana)
    baris = baris_teks(potongan)
    # Seluruh baris disambung untuk mencari nomor pengumuman dan frasa tindak lanjut: keduanya
    # rutin terbelah di ujung baris ("… No. Peng" / "-00169/BEI.POP/09-2026"), sehingga
    # pencarian per baris akan melewatkannya.
    seluruh = re.sub(r"\s*-\s*", "-", " ".join(satu.teks for satu in baris))

    nomor_ksei = POLA_NOMOR_KSEI.findall(seluruh)
    nomor_idx = POLA_NOMOR_IDX.findall(seluruh)
    if not nomor_ksei:
        raise GalatIngesti(
            f"{di_mana}: nomor pengumuman KSEI (PENG-…/DIR/KSEI/…) tidak ditemukan. Tanpa nomor "
            "itu asal tanggalnya tidak bisa ditelusuri, dan aturan keras 1 melarang memakainya."
        )
    if not nomor_idx:
        raise GalatIngesti(
            f"{di_mana}: nomor pengumuman IDX (Peng-…/BEI.POP/…) tidak ditemukan. K11 membolehkan "
            "kalender KSEI dipakai **karena** berkasnya menindaklanjuti pengumuman IDX; tanpa "
            "bukti itu, sumbernya bukan sumber yang diputuskan."
        )

    hari_libur = baris_lampiran_dari(baris, di_mana=di_mana)
    if len(hari_libur) < BARIS_MINIMUM:
        raise GalatIngesti(
            f"{di_mana}: hanya {len(hari_libur)} baris libur yang terbaca (paling sedikit "
            f"{BARIS_MINIMUM}). Periksa apakah lampirannya masih berbentuk tabel teks."
        )

    nomor_urut = sorted(satu.nomor for satu in hari_libur)
    if nomor_urut != list(range(1, len(hari_libur) + 1)):
        hilang = sorted(set(range(1, len(hari_libur) + 1)) - set(nomor_urut))
        raise GalatIngesti(
            f"{di_mana}: nomor urut baris tabel tidak lengkap (hilang: {hilang}). Baris yang "
            "tidak terbaca tidak boleh hilang diam-diam dari kalender."
        )

    tahun_lain = sorted({satu.tanggal.year for satu in hari_libur} - {tahun})
    if tahun_lain:
        raise GalatIngesti(
            f"{di_mana}: lampirannya memuat tanggal tahun {tahun_lain}, sedangkan judul berkasnya "
            f"menyatakan {tahun}. Berkas tahun mana ini tidak bisa dipastikan; kalender ditolak."
        )

    ganda = sorted(
        tanggal for tanggal, jumlah in Counter(satu.tanggal for satu in hari_libur).items()
        if jumlah > 1
    )
    if ganda:
        raise GalatIngesti(
            f"{di_mana}: tanggal {[satu.isoformat() for satu in ganda]} muncul lebih dari sekali "
            "di lampiran. Satu tanggal dengan dua keterangan berbeda tidak boleh dipilih "
            "diam-diam."
        )

    if wajib_tindak_lanjut and FRASA_TINDAK_LANJUT.lower() not in seluruh.lower():
        raise GalatTindakLanjut(
            f"{di_mana}: berkasnya tidak menyatakan menindaklanjuti \"{FRASA_TINDAK_LANJUT}\" IDX. "
            f"Nomor pengumuman IDX yang disebut: {', '.join(sorted(set(nomor_idx)))}. K11 "
            "membolehkan kalender KSEI dipakai karena berkasnya menindaklanjuti kalender libur "
            "bursa; berkas yang menindaklanjuti hal lain (mis. kalender operasional EBA/sukuk) "
            "tidak memenuhi syarat itu, dan tanggalnya tidak dipakai sebagai hari libur bursa."
        )

    return KalenderTahun(
        tahun=tahun,
        url=url,
        nomor_ksei=nomor_ksei[0].upper(),
        nomor_idx=nomor_idx[0],
        nomor_lain=tuple(sorted({satu.upper() for satu in nomor_ksei[1:]})),
        hari_libur=tuple(sorted(hari_libur, key=lambda satu: satu.nomor)),
        glif_tak_terbaca=heksa,
    )


# ---------------------------------------------------------------------------------------
# P19: revisi yang lebih lama, dipakai hanya bila tanggalnya identik
# ---------------------------------------------------------------------------------------

#: Kata penanda revisi pada nama berkas pengumuman KSEI: `Pengumuman_Perubahan_Kedua_…` adalah
#: revisi kedua dari `Pengumuman_Perubahan_…`, dan `Pengumuman_Perubahan_…` adalah revisi pertama
#: dari `Pengumuman_Hari_Libur_…`. Dipakai untuk menyebut versi sebelumnya, **urut dari yang
#: terakhir** — penanda tingkat tinggi dilepas lebih dulu.
KATA_REVISI = ("Kedua", "Ketiga", "Keempat", "Kelima", "Keenam", "Perubahan")

#: Batas jumlah kandidat yang diturunkan dari satu alamat. Revisi sebuah pengumuman bisa beberapa
#: kali, tetapi mencoba lebih dari ini berarti menebak-nebak alamat — dan setiap percobaan adalah
#: satu permintaan ke server orang lain.
KANDIDAT_MAKSIMUM = 3


def kandidat_revisi_lama(url: str) -> tuple[str, ...]:
    """Alamat revisi yang **lebih lama**, diturunkan dari nama berkas yang ditautkan halaman.

    Dasarnya bukan tebakan bebas: KSEI menandai revisi dengan kata di nama berkasnya, jadi revisi
    sebelumnya disebut dengan melepas penanda itu — satu per satu, dari yang terakhir. Kandidat
    yang dihasilkan **belum** dipercaya apa pun: setiap kandidat harus lulus seluruh pemeriksaan
    **dan** tanggalnya harus identik dengan berkas yang ditautkan sebelum dipakai (P19).
    """
    dasar, _, nama = url.rpartition("/")
    keluar: list[str] = []
    sekarang = nama
    for _ in range(KANDIDAT_MAKSIMUM):
        berikutnya: str | None = None
        for kata in KATA_REVISI:
            penanda = f"_{kata}"
            if penanda in sekarang:
                berikutnya = sekarang.replace(penanda, "", 1)
                break
        if berikutnya is None or berikutnya == sekarang:
            break
        sekarang = berikutnya
        keluar.append(f"{dasar}/{sekarang}" if dasar else sekarang)
    return tuple(keluar)


def _tanggal(hari_libur: Sequence[HariLibur]) -> tuple[date, ...]:
    return tuple(sorted(satu.tanggal for satu in hari_libur))


def _keterangan(hari_libur: Sequence[HariLibur]) -> dict[date, str]:
    return {satu.tanggal: satu.keterangan for satu in hari_libur}


def cari_revisi_lama(
    tautan: TautanKalender,
    isi_ditolak: bytes,
    *,
    percobaan: int = PERCOBAAN_BAWAAN,
    jeda: float = JEDA_BAWAAN,
    timeout: float = TIMEOUT_BAWAAN,
    buka: Callable[[str, float], object] | None = None,
) -> tuple[KalenderTahun | None, list[str]]:
    """Cari revisi lebih lama untuk berkas yang ditolak **hanya** oleh syarat tindak lanjut (P19).

    Syaratnya sengaja ketat dan seluruhnya bisa diperiksa:

    1. berkas yang ditautkan halaman tetap harus lolos **seluruh pemeriksaan lain** (kalau tidak,
       yang salah bukan sekadar tindak lanjutnya, dan mencarikan pengganti akan menutupi kerusakan
       yang lebih besar);
    2. revisi lama harus lulus **seluruh** pemeriksaan, termasuk syarat tindak lanjut;
    3. himpunan tanggal liburnya harus **sama persis** dengan berkas yang ditautkan.

    Kalau ada satu tanggal saja yang berbeda, revisi lama **ditolak** dan tahunnya tetap kosong.
    Keterangan yang berbeda tidak menolak (perbaikan salah ketik pernah terjadi pada berkas nyata
    2025), tetapi jumlahnya dilaporkan supaya perbedaannya tidak hilang dari pandangan.
    """
    try:
        pembanding = urai_kalender(
            isi_ditolak, url=tautan.url, tahun=tautan.tahun, wajib_tindak_lanjut=False
        )
    except GalatIngesti as galat:
        # Penjaga, bukan jalan yang biasa dilewati: syarat tindak lanjut diperiksa **terakhir**,
        # jadi berkas yang sampai ke sana sudah lulus seluruh pemeriksaan lain. Cabang ini hidup
        # hanya bila urutan pemeriksaannya berubah — dan kalau itu terjadi, lebih baik dilaporkan
        # daripada diam-diam mencarikan berkas pengganti.
        return None, [f"berkas yang ditautkan juga gagal diperiksa: {galat}"]

    tanggal_pembanding = _tanggal(pembanding.hari_libur)
    catatan: list[str] = []
    for kandidat in kandidat_revisi_lama(tautan.url):
        nama = kandidat.rsplit("/", 1)[-1]
        try:
            isi = unduh(
                kandidat,
                di_mana=f"revisi lama {nama}",
                percobaan=percobaan,
                jeda=jeda,
                timeout=timeout,
                buka=buka,
            )
        except GalatIngesti as galat:
            catatan.append(f"revisi lama TIDAK ADA: {nama} — {galat}")
            continue
        try:
            lama = urai_kalender(isi, url=kandidat, tahun=tautan.tahun)
        except GalatIngesti as galat:
            catatan.append(f"revisi lama DITOLAK: {nama} — {galat}")
            continue

        tanggal_lama = _tanggal(lama.hari_libur)
        if tanggal_lama != tanggal_pembanding:
            hanya_lama = sorted(set(tanggal_lama) - set(tanggal_pembanding))
            hanya_baru = sorted(set(tanggal_pembanding) - set(tanggal_lama))
            catatan.append(
                f"revisi lama DITOLAK (tanggalnya TIDAK identik): {nama} — "
                f"{len(hanya_lama)} tanggal hanya ada di revisi lama "
                f"({', '.join(satu.isoformat() for satu in hanya_lama[:5])}), "
                f"{len(hanya_baru)} hanya ada di berkas yang ditautkan "
                f"({', '.join(satu.isoformat() for satu in hanya_baru[:5])})"
            )
            continue

        beda_ket = sorted(
            tanggal
            for tanggal in set(tanggal_lama) & set(tanggal_pembanding)
            if _keterangan(lama.hari_libur).get(tanggal)
            != _keterangan(pembanding.hari_libur).get(tanggal)
        )
        rincian = (
            f"{len(beda_ket)} keterangan berbeda (tidak menolak; keterangan yang dipakai dari "
            f"berkas yang lulus syarat)"
            if beda_ket
            else "keterangannya pun sama"
        )
        return (
            replace(
                lama,
                revisi=(
                    f"revisi lebih lama dipakai (P19): berkas yang ditautkan halaman "
                    f"({pembanding.nomor_ksei}, ditolak syarat tindak lanjut) memuat "
                    f"{len(tanggal_pembanding)} tanggal yang SAMA PERSIS; yang dipakai "
                    f"{lama.nomor_ksei} menindaklanjuti IDX {lama.nomor_idx} — {rincian}"
                ),
            ),
            catatan,
        )
    return None, catatan


# ---------------------------------------------------------------------------------------
# Menyusun baris kalender bursa
# ---------------------------------------------------------------------------------------

#: Sumber per jenis baris. Ketiganya menyatakan apa adanya: dua yang terakhir adalah **turunan**
#: Meja Saham dari aturan K11, bukan kutipan pengumuman.
SUMBER_LIBUR = "{ksei} (menindaklanjuti IDX {idx})"
SUMBER_HARI_KERJA = "turunan: hari kerja dikurangi libur {ksei}"
SUMBER_AKHIR_PEKAN = "turunan: akhir pekan (Sabtu/Minggu)"


def baris_setahun(kalender: KalenderTahun) -> tuple[BarisKalender, ...]:
    """Susun seluruh tanggal satu tahun: libur resmi, hari kerja, dan akhir pekan.

    Seluruh tanggal ditulis, termasuk akhir pekan, mengikuti aturan template bawaan ("isi seluruh
    tanggal dalam rentang yang Anda pakai"): dengan begitu pertanyaan "apakah tanggal ini hari
    bursa?" selalu bisa dijawab dari berkasnya, bukan dari kalender hari kerja biasa.
    """
    libur = {satu.tanggal: satu.keterangan for satu in kalender.hari_libur}
    sumber_libur = SUMBER_LIBUR.format(ksei=kalender.nomor_ksei, idx=kalender.nomor_idx)
    sumber_kerja = SUMBER_HARI_KERJA.format(ksei=kalender.nomor_ksei)

    keluar: list[BarisKalender] = []
    tanggal = date(kalender.tahun, 1, 1)
    akhir = date(kalender.tahun, 12, 31)
    while tanggal <= akhir:
        if tanggal in libur:
            keluar.append(BarisKalender(tanggal, False, libur[tanggal], sumber_libur))
        elif tanggal.weekday() >= 5:
            keluar.append(BarisKalender(tanggal, False, "akhir pekan", SUMBER_AKHIR_PEKAN))
        else:
            keluar.append(BarisKalender(tanggal, True, None, sumber_kerja))
        tanggal += timedelta(days=1)
    return tuple(keluar)


# ---------------------------------------------------------------------------------------
# Menulis kalender-bursa.csv
# ---------------------------------------------------------------------------------------


def _komentar(
    kalender: Sequence[KalenderTahun],
    *,
    halaman: str,
    dicatat_pada: date,
    ditolak: Sequence[str] = (),
    catatan_revisi: Sequence[str] = (),
) -> Iterator[str]:
    """Penjelasan yang ikut tertulis di berkas: apa yang resmi, apa yang turunan."""
    yield "# " + "=" * 87
    yield "# KALENDER LIBUR BURSA — dari pengumuman resmi KSEI, hari bursa diturunkan"
    yield "# " + "=" * 87
    yield "#"
    yield f"# Halaman sumber: {halaman}"
    yield f"# Ditulis: {tampilan.tanggal(dicatat_pada)} oleh `python -m mejasaham --ambil-kalender`"
    yield "#"
    yield "# Pengumuman yang dipakai:"
    for satu in kalender:
        yield f"#   {satu.tahun}: KSEI {satu.nomor_ksei}, menindaklanjuti IDX {satu.nomor_idx}"
        yield f"#        {satu.url}"
        if satu.revisi:
            yield f"#        {satu.revisi}"
    if ditolak:
        yield "#"
        yield "# Tahun yang TIDAK ada di berkas ini, dan alasannya (bukan lupa):"
        for satu in ditolak:
            yield f"#   {satu}"
    if catatan_revisi:
        yield "#"
        yield "# Percobaan mencari REVISI LEBIH LAMA (P19) — dipakai hanya bila tanggalnya identik:"
        for satu in catatan_revisi:
            yield f"#   {satu}"
    yield "#"
    yield "# ARTI KOLOM"
    yield "#   tanggal      YYYY-MM-DD"
    yield "#   hari_bursa    1 = hari bursa, 0 = bukan hari bursa"
    yield "#   keterangan   nama liburnya menurut pengumuman, \"akhir pekan\", atau kosong"
    yield "#   sumber       pengumuman resmi (baris libur) atau penanda turunan (baris lain)"
    yield "#"
    yield "# ATURAN YANG DIPAKAI (K11) — sengaja dinyatakan, supaya bisa diperiksa:"
    yield "#   * Hari bursa = hari kerja (Senin–Jumat) DIKURANGI daftar libur resmi di atas."
    yield "#     IDX tidak menerbitkan daftar hari bursanya secara terbuka, hanya daftar liburnya."
    yield "#   * Hari libur nasional dan cuti bersama dari pengumuman KSEI ditulis apa adanya,"
    yield "#     dengan nama liburnya. Akhir pekan ditandai, bukan dibiarkan bolong."
    yield "#   * Yang TIDAK diketahui cara ini: hari bursa yang ditiadakan mendadak (mis. karena"
    yield "#     keadaan darurat). Karena itu laporan mutu tetap memperingatkan bila kalender belum"
    yield "#     memuat tanggal snapshot — kalender ini bukan bukti bahwa bursa buka."
    yield "#"
    yield "# Berkas ini boleh disunting tangan (mis. menambah libur yang diumumkan kemudian); impor"
    yield "# berikutnya menambah baris baru, tidak menimpa. Jalankan --ambil-kalender lagi untuk"
    yield "# tahun berikutnya, atau --timpa-kalender untuk menulis ulang seluruh berkas."
    yield "# " + "=" * 87


def tulis_kalender_csv(
    kalender: Sequence[KalenderTahun],
    jalur: Path,
    *,
    halaman: str,
    dicatat_pada: date,
    ditolak: Sequence[str] = (),
    catatan_revisi: Sequence[str] = (),
) -> int:
    """Tulis `kalender-bursa.csv`; kembalikan jumlah baris data.

    Baris kepala ditulis **pertama** (sebelum penjelasan), sama seperti berkas rujukan lain:
    pembaca mendeteksi pemisah kolom dari baris pertama, jadi penjelasan yang mendahuluinya akan
    membuat berkas ini terbaca sebagai berkas berpemisah koma.
    """
    baris = [satu for tahun in kalender for satu in baris_setahun(tahun)]
    baris.sort(key=lambda satu: satu.tanggal)
    with jalur.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
        penulis = csv.writer(berkas_tulis, delimiter=";", lineterminator="\n")
        penulis.writerow(KEPALA_CSV)
        for satu in _komentar(
            kalender,
            halaman=halaman,
            dicatat_pada=dicatat_pada,
            ditolak=ditolak,
            catatan_revisi=catatan_revisi,
        ):
            berkas_tulis.write(satu + "\n")
        for satu in baris:
            penulis.writerow(
                [
                    satu.tanggal.isoformat(),
                    "1" if satu.hari_bursa else "0",
                    satu.keterangan or "",
                    satu.sumber,
                ]
            )
    return len(baris)


# ---------------------------------------------------------------------------------------
# Titik masuk
# ---------------------------------------------------------------------------------------


def ambil_kalender(
    folder: Path,
    *,
    tahun: int | None = None,
    timpa: bool = False,
    hari_ini: date | None = None,
    percobaan: int = PERCOBAAN_BAWAAN,
    jeda: float = JEDA_BAWAAN,
    timeout: float = TIMEOUT_BAWAAN,
    halaman: str = POLA_URL_HALAMAN,
    buka: Callable[[str, float], object] | None = None,
) -> HasilAmbilKalender:
    """Unduh pengumuman kalender KSEI, tulis `folder/kalender-bursa.csv`, lalu baca ulang.

    Berkas yang sudah ada tidak ditimpa tanpa `timpa`: berkas itu bisa saja sudah disunting
    tangan (libur mendadak, tahun yang pengumumannya tidak ada lagi di halaman KSEI).
    """
    tujuan = folder / NAMA_BERKAS_KALENDER
    if tujuan.exists() and not timpa:
        raise GalatIngesti(
            f"'{tujuan}' sudah ada. Berkas itu bisa memuat kalender yang sudah Anda rawat sendiri; "
            "pakai --timpa-kalender bila memang ingin menggantinya dengan kalender KSEI."
        )

    hari = hari_ini or date.today()
    halaman_html = unduh(
        halaman, di_mana="halaman kalender KSEI", percobaan=percobaan, jeda=jeda,
        timeout=timeout, buka=buka,
    ).decode("utf-8", errors="replace")
    tautan, diabaikan = temukan_berkas(halaman_html, halaman=halaman)

    if tahun is not None:
        dipilih = tuple(satu for satu in tautan if satu.tahun == tahun)
        if not dipilih:
            tersedia = ", ".join(str(satu.tahun) for satu in tautan)
            raise GalatIngesti(
                f"tahun {tahun} tidak ada di halaman KSEI {halaman}; yang tersedia: {tersedia}. "
                "Pengumuman tahun lama memang bisa sudah tidak dipasang lagi di sana."
            )
    else:
        dipilih = tautan

    hasil: list[KalenderTahun] = []
    ditolak: list[str] = []
    catatan_revisi: list[str] = []
    for satu in dipilih:
        isi = unduh(
            satu.url, di_mana=f"pengumuman KSEI {satu.tahun}", percobaan=percobaan, jeda=jeda,
            timeout=timeout, buka=buka,
        )
        try:
            hasil.append(urai_kalender(isi, url=satu.url, tahun=satu.tahun))
        except GalatTindakLanjut as galat:
            # P19: berkas yang ditautkan halaman ditolak **hanya** oleh syarat tindak lanjut.
            # Revisi yang lebih lama boleh dipakai, tetapi hanya bila tanggalnya identik —
            # dan seluruh pemeriksaan lain tetap berlaku untuk keduanya.
            revisi, catatan = cari_revisi_lama(
                satu, isi, percobaan=percobaan, jeda=jeda, timeout=timeout, buka=buka
            )
            catatan_revisi.extend(f"{satu.tahun}: {satu_pesan}" for satu_pesan in catatan)
            if revisi is not None:
                hasil.append(revisi)
                catatan_revisi.append(
                    f"{satu.tahun}: DIPAKAI dari revisi lebih lama — {revisi.nomor_ksei}"
                )
                continue
            # Bukan kegagalan seluruh pengambilan: tahun yang berkasnya sah tetap dipakai.
            # Tahun ini dilaporkan, dan alasannya ikut tertulis di berkasnya.
            ditolak.append(f"{satu.tahun}: {galat}")

    if not hasil:
        # Ketika tidak ada satu pun tahun yang bisa dipakai, yang menolong bukan hanya daftar
        # tahun yang ditolak, melainkan juga **apa yang sudah dicoba**: revisi lebih lama yang
        # dicari, dan kenapa ia tidak menolong (P19).
        rincian = [f"  - {satu}" for satu in ditolak]
        if catatan_revisi:
            rincian.append("  percobaan revisi lebih lama (P19):")
            rincian.extend(f"    - {satu}" for satu in catatan_revisi)
        raise GalatIngesti(
            "tidak ada satu pun pengumuman kalender di halaman KSEI yang bisa dipakai. "
            "Alasannya:\n" + "\n".join(rincian)
        )

    lokasi.pastikan_folder(folder)
    try:
        jumlah = tulis_kalender_csv(
            hasil,
            tujuan,
            halaman=halaman,
            dicatat_pada=hari,
            ditolak=ditolak,
            catatan_revisi=catatan_revisi,
        )
    except OSError as galat:
        raise GalatIngesti(f"gagal menulis '{tujuan}': {galat}") from galat

    # Bukti, bukan klaim: berkas dibaca ulang oleh pembaca yang sama dengan yang dipakai --impor.
    terbaca = baca_kalender(folder)
    if len(terbaca) != jumlah:
        raise GalatIngesti(
            f"'{tujuan}' ditulis {jumlah} baris tetapi terbaca ulang {len(terbaca)} baris. "
            "Berkasnya tidak boleh dipakai sebelum diperiksa."
        )
    baris = tuple(satu for kalender in hasil for satu in baris_setahun(kalender))
    return HasilAmbilKalender(
        jalur=tujuan,
        tahun=tuple(hasil),
        baris=baris,
        tautan_diabaikan=diabaikan,
        tahun_ditolak=tuple(ditolak),
        catatan_revisi=tuple(catatan_revisi),
        jumlah_terbaca_ulang=len(terbaca),
        jumlah_hari_bursa=sum(1 for satu in baris if satu.hari_bursa),
        jumlah_akhir_pekan=sum(1 for satu in baris if satu.sumber == SUMBER_AKHIR_PEKAN),
    )
