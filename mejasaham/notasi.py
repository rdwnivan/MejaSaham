"""Notasi khusus, suspensi, dan UMA resmi IDX (P22) — tanpa peramban.

**Temuan yang mengubah keadaan (10 Okt 2026):** jalur resmi IDX **tidak** seluruhnya mati. Yang
memblokir adalah `www.idx.co.id` dan `www2.idx.co.id` (HTTP 403 untuk `requests`/`curl`), sedangkan
domain resmi **`www.idx.id`** melayani halaman yang sama: `urllib` dari pustaka standar menerima
**HTTP 200** (251.947 byte) asalkan permintaannya membawa User-Agent yang menyebut dirinya — UA
bawaan `Python-urllib/3.14` ditolak 403, sedangkan UA jujur `MejaSaham/0.1 (…)` diterima. Terukur
10 Okt 2026: 5 permintaan berturut-turut semuanya 200, 0,56–0,73 detik. Jadi modul ini **tidak**
menyamar sebagai peramban dan **tidak** menambah dependensi apa pun.

Halaman notasi itu tidak merender `<table>`: datanya ada di payload SSR Nuxt
(`<script>window.__NUXT__=…</script>`), dan yang dipakai di sini adalah pola
`FormatEmitenCode:"KODE.NOTASI"` — pola yang memuat kode dan huruf notasinya **tanpa** menuntut
penyelesaian rujukan gaya *devalue* (`Date:b`, `Notation:g`). Yang tetap harus dibaca dari payload
adalah **tanggal datanya**, dan itu dilakukan dengan syarat ketat: seluruh literal tanggal pada
halaman harus menunjuk **satu** tanggal; kalau ada dua yang berbeda, halaman itu ditolak, bukan
diringkas (kesalahan yang sama dengan `sun.py`).

**Arti kolomnya, apa adanya:**

* `jenis` = `papan_pemantauan` bila huruf notasinya memuat **X** (legenda halaman: "Perusahaan
  Tercatat dicatatkan di Papan Pemantauan Khusus"), selain itu `notasi_lainnya`. Keduanya nilai sah
  menurut `berkas.JENIS_NOTASI`, dan huruf mentahnya ikut tersimpan di `keterangan`.
* `tanggal_mulai` = **tanggal data halaman**, bukan tanggal mulai notasi: sumbernya tidak
  menyatakan kapan tiap notasi dimulai, dan kolom kosong ditolak kontrak berkas impor. Asal angka
  itu **ditulis di setiap baris** (`keterangan`) supaya tidak terbaca sebagai "notasi mulai hari
  itu".
* Suspensi/UMA diambil dari API berita IDX yang halaman resminya gunakan. SPT/UPT membentuk
  rentang suspensi; UMA berakhir 30 hari kalender setelah tanggal pengumuman (K35). Pengumuman
  `>1 Kode` ditandai dan dilewati sampai aksi dan tanggal efektif per emitennya direkonsiliasi.
* Baris notasi yang **tidak lagi tercantum** pada pengambilan berikutnya ditutup dengan
  `tanggal_selesai` = tanggal data pengambilan itu, sebab halaman ini adalah daftar keadaan
  terkini: ketidakhadirannya berarti "tidak lagi ber-notasi menurut sumber ini". Yang ditutup hanya
  baris yang **ditulis modul ini** (dikenali dari penanda di `keterangan`); baris isian tangan
  tidak disentuh.

Berkasnya **bertambah**, bukan ditimpa, seperti `imbal-hasil-sun.csv`: baris lama adalah riwayat
point-in-time yang tidak bisa dibangun ulang dari sumbernya (sumbernya tidak punya arsip bulanan).
Penulisan basis data tetap lewat `--impor` (aturan keras 6).
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

from mejasaham import lokasi, tampilan, unggahan_idx
from mejasaham.berkas import PENANDA_CONTOH, PENANDA_NOTASI_TIDAK_LENGKAP

#: Halaman resmi notasi khusus. Domain `www.idx.id` — **bukan** `www.idx.co.id`, yang membalas 403.
ALAMAT = "https://www.idx.id/id/perusahaan-tercatat/notasi-khusus/"

#: UA jujur yang menyebut siapa pengambilnya. Terukur 10 Okt 2026: halaman ini menerimanya
#: (HTTP 200) dan hanya menolak UA bawaan pustaka (`Python-urllib/3.14` → 403).
AGEN_PENGGUNA = "MejaSaham/0.1 (pengambilan berkas publik IDX; python-urllib)"

TIMEOUT_BAWAAN = 60.0
PERCOBAAN_BAWAAN = 3
JEDA_BAWAAN = 2.0

NAMA_BERKAS = "notasi-khusus.csv"
LABEL_SUMBER = "Halaman resmi IDX 'Notasi Khusus' (www.idx.id)"

KEPALA_CSV = ("kode", "jenis", "tanggal_mulai", "tanggal_selesai", "keterangan")

#: Penanda baris yang ditulis modul ini, disimpan di dalam `keterangan` — berkas impor
#: `notasi_khusus` hanya mengenal lima kolom, jadi penandanya tidak boleh jadi kolom sendiri.
#: Hanya baris berpenanda ini yang boleh ditutup otomatis; isian tangan tidak disentuh.
PENANDA_BARIS = "tercantum pada daftar resmi per"

#: Huruf notasi → jenis yang disimpan. `X` = Papan Pemantauan Khusus menurut legenda halaman itu
#: sendiri; sisanya `notasi_lainnya` (huruf mentahnya tetap tersimpan di `keterangan`).
JENIS_PAPAN_PEMANTAUAN = "papan_pemantauan"
JENIS_LAINNYA = "notasi_lainnya"
HURUF_PAPAN_PEMANTAUAN = "X"
#: Daftar notasi khusus mencakup kedua jenis ini secara utuh (lihat `HasilNotasi.jenis_dicakup`).
JENIS_DAFTAR = frozenset({JENIS_PAPAN_PEMANTAUAN, JENIS_LAINNYA})

#: Kode emiten 4 huruf, tetapi halaman resminya juga memuat kode 5 huruf (terukur 10 Okt 2026:
#: `GOTOM`). Pola yang mengunci 4 huruf akan **membuang** baris itu tanpa suara — dan baris yang
#: hilang dari daftar notasi berarti emiten yang boleh lolos saringan padahal tidak.
POLA_BARIS = re.compile(r'FormatEmitenCode:"([A-Z0-9]{4,5})\.([A-Z]*)"')
POLA_TANGGAL = re.compile(r"\d{4}-\d{2}-\d{2}T00:00:00")
POLA_KOMENTAR = re.compile(r"^\s*#")
#: Catatan kepala berkas bertanda jenis yang dijelaskannya (`# CATATAN [suspensi, uma]: …`).
#: Tandanya menentukan catatan mana yang terbawa saat penulisan berikutnya hanya memperbarui
#: jenis lain; catatan lama tanpa tanda tidak bisa dipastikan jenisnya, jadi tidak dibawa.
POLA_CATATAN = re.compile(r"^# CATATAN \[([a-z_, ]+)\]: (.*)$")
POLA_KODE_EFEK = re.compile(r"[A-Z0-9-]{4,12}")

# Endpoint ditemukan dari berkas JavaScript halaman resmi IDX (11 Okt 2026).
ALAMAT_SUSPENSI = "https://www.idx.id/primary/NewsAnnouncement/GetSuspension"
ALAMAT_UMA = "https://www.idx.id/primary/NewsAnnouncement/GetUma"
UMUR_UMA_HARI = 30
UKURAN_HALAMAN_AKTIVITAS = 9999
PENANDA_AKTIVITAS = "IDX API NewsAnnouncement"

#: Daftar pengumuman suspensi `>1 Kode` yang **sudah** dipetakan per emiten (K36–K41, K53; K94),
#: di folder konfigurasi. Kuncinya `Data_Download` API — jalur PDF yang unik per pengumuman.
#: Berkas tidak ada = tidak satu pun dianggap beres (arah yang aman: penanda "tidak lengkap").
NAMA_BERKAS_TEREKONSILIASI = "multi-kode-terekonsiliasi.csv"


class GalatNotasi(RuntimeError):
    """Kesalahan yang pesannya sudah ditujukan untuk pengguna, bukan traceback (aturan keras 7)."""


@dataclass(frozen=True)
class BarisNotasi:
    """Satu baris notasi: satu emiten, satu jenis, satu tanggal mulai menurut sumbernya."""

    kode: str
    jenis: str
    tanggal_mulai: date
    tanggal_selesai: date | None
    keterangan: str

    @property
    def huruf(self) -> str:
        """Huruf notasi apa adanya, dibaca kembali dari `keterangan` (ditulis modul ini)."""
        cocok = re.search(r"notasi ([A-Z,]+)", self.keterangan)
        return cocok.group(1) if cocok else ""

    def sel(self) -> tuple[str, ...]:
        return (
            self.kode,
            self.jenis,
            self.tanggal_mulai.isoformat(),
            "" if self.tanggal_selesai is None else self.tanggal_selesai.isoformat(),
            self.keterangan,
        )


@dataclass(frozen=True)
class HasilNotasi:
    """Hasil satu pengambilan: tanggal data menurut halaman, dan barisnya."""

    tanggal_data: date
    baris: tuple[BarisNotasi, ...]
    sumber: str
    catatan: tuple[str, ...] = ()
    #: Jenis yang dicakup sumbernya secara utuh — baris lama berjenis ini yang tidak tercantum
    #: ditutup. Kosong = diturunkan dari baris yang ada. Daftar notasi mencakup **kedua** jenisnya
    #: walaupun tidak memuat satu pun huruf X: menurunkannya dari baris membuat baris papan
    #: pemantauan lama tidak pernah ditutup ketika daftar baru tidak lagi memuat emiten ber-X.
    jenis_dicakup: frozenset[str] = frozenset()
    #: Sumbernya bukan daftar (mis. PDF pengumuman satuan, K99): tidak ada jenis yang dicakup
    #: utuh, jadi baris lama yang tidak disebut **tidak** ditutup — hanya baris baru yang ditambah.
    hanya_menambah: bool = False
    #: Baris lama yang ditutup **atas pernyataan sumber** (pengumuman pembukaan UPT): kuncinya sama
    #: dengan satu baris terbuka di berkas, `tanggal_selesai`-nya terisi. Berlaku untuk baris dari
    #: asal mana pun; baris yang tidak ada atau sudah tertutup ditolak, bukan ditambah.
    penutupan: tuple[BarisNotasi, ...] = ()

    @property
    def jumlah_papan_pemantauan(self) -> int:
        return sum(1 for satu in self.baris if satu.jenis == JENIS_PAPAN_PEMANTAUAN)

    @property
    def kode_papan_pemantauan(self) -> tuple[str, ...]:
        return tuple(
            sorted(satu.kode for satu in self.baris if satu.jenis == JENIS_PAPAN_PEMANTAUAN)
        )


@dataclass(frozen=True)
class HasilAktivitas:
    baris: tuple[BarisNotasi, ...]
    #: Pengumuman `>1 Kode` yang **belum** direkonsiliasi — hanya ini yang memasang penanda.
    pengumuman_multi_kode: int
    pembukaan_tanpa_awal: int
    #: Pengumuman `>1 Kode` yang tercantum di `multi-kode-terekonsiliasi.csv`.
    multi_kode_terekonsiliasi: int = 0


def baca_terekonsiliasi(folder_konfigurasi: Path) -> frozenset[str]:
    """`Data_Download` pengumuman multi-kode yang sudah dipetakan per emiten (K94)."""
    jalur = folder_konfigurasi / NAMA_BERKAS_TEREKONSILIASI
    if not jalur.exists():
        return frozenset()
    baris = [
        satu
        for satu in jalur.read_text(encoding="utf-8-sig").splitlines()
        if satu.strip() and not POLA_KOMENTAR.match(satu)
    ]
    isi = list(csv.reader(baris, delimiter=";"))
    if not isi or isi[0][:1] != ["data_download"]:
        raise GalatNotasi(f"{jalur.name}: kolom pertama kepala harus `data_download`")
    return frozenset(satu[0].strip() for satu in isi[1:] if satu and satu[0].strip())


# ---------------------------------------------------------------------------------------
# Penguraian (murni: tanpa jaringan, supaya bisa diuji dengan halaman contoh)
# ---------------------------------------------------------------------------------------


def urai(teks: str) -> HasilNotasi:
    """Baca payload halaman notasi menjadi baris-baris; menolak halaman yang tidak berbentuk.

    Penolakannya sengaja keras: halaman tanpa satu baris pun, halaman tanpa tanggal data, dan
    halaman yang menyatakan **dua** tanggal berbeda semuanya gagal dengan pesan yang menyebut
    sebabnya. "Tidak ada notasi" dan "halamannya berubah bentuk" adalah dua keadaan yang berbeda,
    dan mencampurnya akan membuat daftar kosong terbaca sebagai kabar baik.
    """
    temuan = POLA_BARIS.findall(teks)
    if not temuan:
        raise GalatNotasi(
            f"halaman notasi IDX tidak memuat satu baris pun dengan pola "
            f"`FormatEmitenCode:\"KODE.NOTASI\"` ({len(teks)} karakter dibaca). Halamannya "
            "mungkin berubah bentuk — ini bukan berarti tidak ada emiten ber-notasi, dan "
            "karena itu tidak boleh dilaporkan sebagai daftar kosong."
        )

    tanggal = sorted({satu[:10] for satu in POLA_TANGGAL.findall(teks)})
    if not tanggal:
        raise GalatNotasi(
            "halaman notasi IDX tidak menyatakan tanggal datanya; tanpa itu, barisnya tidak bisa "
            "disimpan bertanggal dan akan terbaca sebagai 'diketahui sekarang' (aturan keras 3)"
        )
    if len(tanggal) > 1:
        raise GalatNotasi(
            f"halaman notasi IDX menyatakan {len(tanggal)} tanggal berbeda "
            f"({', '.join(tanggal)}); halaman seperti itu ditolak, bukan diringkas — memilih salah "
            "satunya berarti menebak kapan datanya berlaku"
        )
    tanggal_data = date.fromisoformat(tanggal[0])

    huruf_per_kode: dict[str, set[str]] = {}
    for kode, notasi in temuan:
        # Hurufnya **tergabung** di pola ini: `BOSS.BELYX` berarti B, E, L, Y, X — bukan satu
        # notasi bernama "BELYX". Dipisah per huruf, sebab legenda halaman itu mendefinisikan
        # huruf satu per satu; membacanya sebagai satu token membuat `X` (papan pemantauan
        # khusus) tidak pernah dikenali, dan daftarnya akan tampak kosong.
        huruf_per_kode.setdefault(kode, set()).update(satu for satu in notasi if satu.isalpha())

    return HasilNotasi(
        tanggal_data=tanggal_data,
        baris=_baris_daftar(huruf_per_kode, tanggal_data),
        sumber=f"{LABEL_SUMBER}, data per {tanggal_data.isoformat()}",
        jenis_dicakup=JENIS_DAFTAR,
    )


def _baris_daftar(huruf_per_kode: dict[str, set[str]], tanggal_data: date) -> tuple[BarisNotasi, ...]:
    """Satu baris per emiten dari daftar keadaan terkini — sama untuk halaman dan berkas unduhan,
    supaya daftar yang sama tidak tercatat dua kali dan jadwal membacanya dengan cara yang sama."""
    baris: list[BarisNotasi] = []
    for kode in sorted(huruf_per_kode):
        huruf_set = huruf_per_kode[kode]
        huruf = ",".join(sorted(huruf_set))
        jenis = JENIS_PAPAN_PEMANTAUAN if HURUF_PAPAN_PEMANTAUAN in huruf_set else JENIS_LAINNYA
        baris.append(
            BarisNotasi(
                kode=kode,
                jenis=jenis,
                tanggal_mulai=tanggal_data,
                tanggal_selesai=None,
                keterangan=(
                    f"notasi {huruf}; {PENANDA_BARIS} {tanggal_data.isoformat()} "
                    "(tanggal data halaman — tanggal MULAI notasi tidak dinyatakan sumbernya)"
                ),
            )
        )
    return tuple(baris)


# ---------------------------------------------------------------------------------------
# Berkas unduhan pengguna (K96: aplikasi tidak lagi mengambil halaman IDX sendiri)
# ---------------------------------------------------------------------------------------

LABEL_UNDUHAN = "Notasi Khusus IDX (unduhan pengguna dari situs IDX)"

#: Halaman yang dibuka **pengguna** di perambannya untuk menekan "Unduh" (bukan `ALAMAT`, yang
#: dipakai pengambilan otomatis lama).
ALAMAT_UNDUHAN = "https://www.idx.co.id/id/perusahaan-tercatat/notasi-khusus/"

#: Tombol "Unduh" di halaman Notasi Khusus IDX menamai berkasnya `Notasi Khusus-YYYYMMDD.xlsx`
#: (contoh nyata 29 Okt 2026, data "per 27 Okt 2026 Pkl. 15:00 WIB"). Isi berkasnya **tidak**
#: memuat tanggal, jadi nama berkas satu-satunya sumber tanggal data. Peramban menambah " (1)"
#: pada unduhan kedua bernama sama.
POLA_NAMA_UNDUHAN = re.compile(r"Notasi Khusus-(\d{8})(?: \(\d+\))?\.xlsx", re.IGNORECASE)

#: Kolom `Kode` berbentuk `KODE.HURUF` (mis. `CBMF.LY`, `GOTOM.N`); kolom `Notasi` = `L,Y`.
POLA_KODE_UNDUHAN = re.compile(r"([A-Z0-9]{4,5})\.([A-Z]+)")
KOLOM_UNDUHAN = ("Kode", "Notasi")


def folder_unduhan() -> Path:
    return lokasi.folder_data() / "unduhan-idx" / "notasi-khusus"


def simpan_unduhan(nama_asli: str, isi: bytes, *, momen: datetime | None = None) -> Path:
    """Simpan berkas unggahan mentah apa adanya (bukti asal baris). Basis data tidak disentuh."""
    if not isi:
        raise GalatNotasi("berkasnya kosong (0 bait) — pilih berkas hasil unduhan Notasi Khusus IDX")
    if len(isi) > unggahan_idx.BATAS_BAIT:
        raise GalatNotasi(f"berkasnya {tampilan.angka(len(isi), 0)} bait — kemungkinan salah pilih")
    waktu = (momen or datetime.now().astimezone()).replace(microsecond=0)
    tujuan = lokasi.pastikan_folder(folder_unduhan())
    jalur = tujuan / f"{waktu:%Y%m%dT%H%M%S}_{unggahan_idx.nama_aman(nama_asli)}"
    sementara = jalur.with_name(jalur.name + ".sebagian")
    sementara.write_bytes(isi)
    sementara.replace(jalur)
    return jalur


def baca_unduhan(jalur: Path, *, nama_asli: str | None = None, hari_ini: date | None = None) -> HasilNotasi:
    """Baca berkas Notasi Khusus IDX unduhan pengguna menjadi baris yang sama dengan `urai`.

    Penolakannya sama kerasnya dengan `urai`: berkas tanpa baris, tanpa tanggal yang bisa
    dibuktikan, atau yang kolom `Kode`-nya tidak cocok dengan kolom `Notasi`, gagal dengan
    sebabnya — daftar kosong tidak boleh terbaca sebagai "tidak ada notasi".
    """
    nama = nama_asli or jalur.name
    cocok = POLA_NAMA_UNDUHAN.fullmatch(nama)
    try:
        tanggal_data = datetime.strptime(cocok.group(1), "%Y%m%d").date() if cocok else None
    except ValueError:
        tanggal_data = None
    if tanggal_data is None:
        raise GalatNotasi(
            f"'{nama}': tanggal data tidak terbaca dari nama berkas (bentuk yang dikenal "
            "'Notasi Khusus-YYYYMMDD.xlsx'). Isi berkasnya tidak memuat tanggal, jadi tanpa itu "
            "barisnya tidak bisa disimpan bertanggal (aturan keras 3) — unggah berkas dengan nama "
            "aslinya dari tombol Unduh IDX"
        )
    if tanggal_data > (hari_ini or date.today()):
        raise GalatNotasi(f"'{nama}': tanggal data {tampilan.tanggal(tanggal_data)} sesudah hari ini")

    try:
        with zipfile.ZipFile(jalur) as isi_zip:
            lembar = unggahan_idx.baca_lembar(isi_zip)
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError, IndexError, ValueError) as galat:
        raise GalatNotasi(
            f"'{nama}' tidak terbaca sebagai XLSX ({type(galat).__name__}: {galat}); unggah berkas "
            "hasil tombol Unduh di halaman Notasi Khusus IDX"
        ) from galat
    judul = {teks: kolom for kolom, teks in (lembar[0] if lembar else {}).items()}
    hilang = [satu for satu in KOLOM_UNDUHAN if satu not in judul]
    if hilang:
        raise GalatNotasi(
            f"'{nama}' bukan berkas Notasi Khusus IDX yang dikenal: judul kolom {', '.join(hilang)} "
            "tidak ada di baris 1 (bentuknya mungkin berubah — beri tahu agen)"
        )

    huruf_per_kode: dict[str, set[str]] = {}
    for nomor, sel in enumerate(lembar[1:], start=2):
        if not any(sel.values()):
            continue
        di_mana = f"'{nama}' baris {nomor}"
        teks_kode = sel.get(judul["Kode"], "").upper()
        kode_cocok = POLA_KODE_UNDUHAN.fullmatch(teks_kode)
        if kode_cocok is None:
            raise GalatNotasi(f"{di_mana}: kode '{teks_kode}' bukan bentuk KODE.NOTASI (mis. CBMF.LY)")
        kode, huruf = kode_cocok.groups()
        if kode in huruf_per_kode:
            raise GalatNotasi(f"{di_mana}: kode {kode} muncul dua kali")
        kolom_notasi = {satu.strip() for satu in sel.get(judul["Notasi"], "").upper().split(",") if satu.strip()}
        if set(huruf) != kolom_notasi:
            raise GalatNotasi(
                f"{di_mana}: huruf pada kode ({huruf}) tidak sama dengan kolom Notasi "
                f"({sel.get(judul['Notasi'], '')}); berkas seperti itu tidak ditebak artinya"
            )
        huruf_per_kode[kode] = set(huruf)
    if not huruf_per_kode:
        raise GalatNotasi(
            f"'{nama}' tidak memuat satu emiten pun — ini bukan berarti tidak ada emiten "
            "ber-notasi, jadi tidak diimpor sebagai daftar kosong"
        )
    return HasilNotasi(
        tanggal_data=tanggal_data,
        baris=_baris_daftar(huruf_per_kode, tanggal_data),
        sumber=f"{LABEL_UNDUHAN}, berkas '{nama}', data per {tanggal_data.isoformat()}",
        jenis_dicakup=JENIS_DAFTAR,
    )


def tanggal_daftar_terbaru(baris: Sequence[BarisNotasi]) -> date | None:
    """Tanggal daftar resmi terbaru yang tercantum di baris berpenanda (`PENANDA_BARIS`)."""
    pola = re.compile(re.escape(PENANDA_BARIS) + r" (\d{4}-\d{2}-\d{2})")
    tanggal = [date.fromisoformat(cocok.group(1)) for satu in baris if (cocok := pola.search(satu.keterangan))]
    return max(tanggal, default=None)


def unduh(
    alamat: str = ALAMAT,
    *,
    percobaan: int = PERCOBAAN_BAWAAN,
    jeda: float = JEDA_BAWAAN,
    timeout: float = TIMEOUT_BAWAAN,
) -> str:
    """Ambil halaman notasi. Satu permintaan per jalan; ulangan hanya untuk kegagalan sementara."""
    galat_terakhir: Exception | None = None
    for nomor in range(1, percobaan + 1):
        if nomor > 1:
            time.sleep(jeda * nomor)
        try:
            permintaan = urllib.request.Request(alamat, headers={"User-Agent": AGEN_PENGGUNA})
            with urllib.request.urlopen(permintaan, timeout=timeout) as jawaban:
                return jawaban.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as galat:
            galat_terakhir = galat
    raise GalatNotasi(
        f"gagal mengambil halaman notasi IDX {alamat} setelah {percobaan} percobaan: "
        f"{galat_terakhir}. Periksa koneksi; halaman ini menolak permintaan tanpa User-Agent "
        "yang menyebut dirinya, dan modul ini sudah memakai UA jujur."
    )


def _unduh_daftar_aktivitas(alamat: str, *, jeda: float, timeout: float) -> list[dict[str, object]]:
    """Ambil seluruh hasil endpoint IDX; kegagalan atau respons parsial ditolak."""
    from urllib.parse import urlencode

    time.sleep(jeda)
    parameter = urlencode(
        {"indexFrom": 1, "dateFrom": "", "dateTo": "", "pageSize": UKURAN_HALAMAN_AKTIVITAS,
         "lang": "id", "type": ""}
    )
    permintaan = urllib.request.Request(
        f"{alamat}?{parameter}", headers={"User-Agent": AGEN_PENGGUNA}
    )
    try:
        with urllib.request.urlopen(permintaan, timeout=timeout) as jawaban:
            payload = json.loads(jawaban.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as galat:
        raise GalatNotasi(f"gagal membaca API aktivitas IDX {alamat}: {galat}") from galat
    if not isinstance(payload, dict) or not isinstance(payload.get("Results"), list):
        raise GalatNotasi(f"API aktivitas IDX {alamat} mengembalikan bentuk data yang tidak dikenal")
    jumlah = payload.get("ResultCount")
    hasil = payload["Results"]
    if not isinstance(jumlah, int) or jumlah != len(hasil):
        raise GalatNotasi(
            f"API aktivitas IDX {alamat} menyatakan {jumlah!r} baris tetapi hanya mengirim "
            f"{len(hasil)}; hasil parsial tidak dipakai"
        )
    if not hasil:
        raise GalatNotasi(f"API aktivitas IDX {alamat} mengembalikan daftar kosong; tidak dianggap bersih")
    if not all(isinstance(satu, dict) for satu in hasil):
        raise GalatNotasi(f"API aktivitas IDX {alamat} memuat baris yang bukan objek")
    return hasil


def _tanggal_api(nilai: object, *, alamat: str, kode: str) -> date:
    if not isinstance(nilai, str):
        raise GalatNotasi(f"API {alamat}: tanggal untuk {kode!r} tidak berupa teks")
    try:
        return date.fromisoformat(nilai[:10])
    except ValueError as galat:
        raise GalatNotasi(f"API {alamat}: tanggal {nilai!r} untuk {kode!r} tidak sah") from galat


def unduh_aktivitas(
    *,
    tanggal_data: date,
    jeda: float = 0.4,
    timeout: float = TIMEOUT_BAWAAN,
    terekonsiliasi: frozenset[str] = frozenset(),
) -> HasilAktivitas:
    """Turunkan riwayat suspensi dan UMA dari API berita resmi IDX.

    Pengumuman `>1 Kode` tidak bisa dipetakan otomatis ke emiten. Yang `Data_Download`-nya ada di
    `terekonsiliasi` sudah dipetakan per kode di baris isian berkas notasi (K36–K41), jadi tidak
    dihitung lagi; sisanya memasang `PENANDA_NOTASI_TIDAK_LENGKAP` pada seluruh baris (K94).
    """
    if jeda < 0:
        raise GalatNotasi("nilai --jeda tidak boleh negatif")
    suspensi = _unduh_daftar_aktivitas(ALAMAT_SUSPENSI, jeda=jeda, timeout=timeout)
    uma = _unduh_daftar_aktivitas(ALAMAT_UMA, jeda=jeda, timeout=timeout)

    per_kode: dict[str, list[tuple[date, str, str]]] = {}
    multi_kode = 0
    multi_kode_beres = 0
    for baris in suspensi:
        kode = baris.get("Kode")
        jenis_peristiwa = baris.get("Info_Type")
        judul = baris.get("Judul")
        tanggal = _tanggal_api(baris.get("Date"), alamat=ALAMAT_SUSPENSI, kode=str(kode))
        if kode == ">1 Kode":
            # Kode per PDF sudah dapat ditinjau, tetapi pemetaannya per emiten dikerjakan manusia
            # (K36–K41); hanya yang belum tercantum di daftar rekonsiliasi yang dihitung.
            if baris.get("Data_Download") in terekonsiliasi:
                multi_kode_beres += 1
            else:
                multi_kode += 1
            continue
        if not isinstance(kode, str) or not POLA_KODE_EFEK.fullmatch(kode):
            raise GalatNotasi(f"API suspensi IDX memuat kode emiten tidak sah: {kode!r}")
        if jenis_peristiwa not in {"SPT", "UPT"} or not isinstance(judul, str):
            raise GalatNotasi(f"API suspensi IDX memuat jenis/judul yang tidak dikenal untuk {kode}")
        peristiwa = per_kode.setdefault(kode, [])
        if not any(tanggal_lama == tanggal and jenis_lama == jenis_peristiwa for tanggal_lama, jenis_lama, _ in peristiwa):
            peristiwa.append((tanggal, str(jenis_peristiwa), judul))

    keluar: list[BarisNotasi] = []
    pembukaan_tanpa_awal = 0
    for kode, peristiwa in per_kode.items():
        peristiwa.sort(key=lambda satu: (satu[0], 0 if satu[1] == "SPT" else 1))
        mulai: date | None = None
        judul_mulai = ""
        for tanggal, jenis, judul in peristiwa:
            if jenis == "SPT":
                if mulai is not None:
                    # Suspensi baru mengakhiri episode sebelumnya pada tanggal pengumuman baru.
                    keluar.append(_baris_aktivitas(kode, "suspensi", mulai, tanggal, judul_mulai))
                mulai, judul_mulai = tanggal, judul
            else:
                if mulai is None:
                    # Umumnya pasangan SPT-nya ada di pengumuman massal `>1 Kode` yang
                    # lampirannya tidak dapat dipetakan ke emiten. Catat keterbatasan ini.
                    pembukaan_tanpa_awal += 1
                    continue
                keluar.append(_baris_aktivitas(kode, "suspensi", mulai, tanggal, judul_mulai + " → " + judul))
                mulai = None
        if mulai is not None:
            keluar.append(_baris_aktivitas(kode, "suspensi", mulai, None, judul_mulai))

    uma_per_kunci: dict[tuple[str, date], list[str]] = {}
    for baris in uma:
        kode, judul = baris.get("CompanyID"), baris.get("Judul")
        mulai = _tanggal_api(baris.get("UMADate"), alamat=ALAMAT_UMA, kode=str(kode))
        if not isinstance(kode, str) or not POLA_KODE_EFEK.fullmatch(kode):
            raise GalatNotasi(f"API UMA IDX memuat kode emiten tidak sah: {kode!r}")
        if not isinstance(judul, str):
            raise GalatNotasi(f"API UMA IDX tidak memuat judul untuk {kode}")
        uma_per_kunci.setdefault((kode, mulai), [])
        if judul not in uma_per_kunci[(kode, mulai)]:
            uma_per_kunci[(kode, mulai)].append(judul)

    for (kode, mulai), judul_judul in sorted(uma_per_kunci.items()):
        selesai = mulai + timedelta(days=UMUR_UMA_HARI)
        keluar.append(_baris_aktivitas(kode, "uma", mulai, selesai, " / ".join(judul_judul)))

    # Tanggal pengambilan hanya menjadi batas pemeriksaan; UMA masa depan dari jam sistem tidak
    # boleh masuk sebagai data aktif.
    if any(satu.tanggal_mulai > tanggal_data for satu in keluar):
        raise GalatNotasi("API aktivitas IDX memuat peristiwa bertanggal setelah tanggal pengambilan")
    baris_hasil = tuple(sorted(keluar, key=lambda satu: (satu.kode, satu.jenis, satu.tanggal_mulai)))
    if multi_kode:
        baris_hasil = tuple(
            BarisNotasi(
                satu.kode,
                satu.jenis,
                satu.tanggal_mulai,
                satu.tanggal_selesai,
                f"{satu.keterangan}; {PENANDA_NOTASI_TIDAK_LENGKAP} ({multi_kode} pengumuman)",
            )
            for satu in baris_hasil
        )
    return HasilAktivitas(baris_hasil, multi_kode, pembukaan_tanpa_awal, multi_kode_beres)


def _baris_aktivitas(kode: str, jenis: str, mulai: date, selesai: date | None, judul: str) -> BarisNotasi:
    if selesai is not None and selesai < mulai:
        raise GalatNotasi(f"peristiwa {jenis} {kode} berakhir sebelum dimulai")
    keterangan = f"{PENANDA_AKTIVITAS}; {judul}; aturan UMA {UMUR_UMA_HARI} hari" if jenis == "uma" else f"{PENANDA_AKTIVITAS}; {judul}"
    return BarisNotasi(kode, jenis, mulai, selesai, keterangan)


# ---------------------------------------------------------------------------------------
# Berkas: bertambah, dan yang tidak lagi tercantum ditutup
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HasilTulisNotasi:
    jalur: Path
    jumlah_baris: int
    baru: int
    ditutup: int
    papan_pemantauan: int


def _baca_baris_lama(jalur: Path) -> list[BarisNotasi]:
    """Baca berkas yang sudah ada; baris isian tangan ikut dibaca supaya tidak hilang."""
    if not jalur.exists():
        return []
    teks = jalur.read_text(encoding="utf-8-sig")
    keluar: list[BarisNotasi] = []
    for nomor, baris in enumerate(teks.splitlines(), start=1):
        if not baris.strip() or POLA_KOMENTAR.match(baris) or PENANDA_CONTOH in baris:
            continue
        sel = next(csv.reader([baris], delimiter=";"))
        if sel and sel[0] == KEPALA_CSV[0]:
            continue
        if len(sel) != len(KEPALA_CSV):
            raise GalatNotasi(
                f"{jalur.name} baris {nomor}: {len(sel)} kolom, sedangkan kepalanya "
                f"{len(KEPALA_CSV)} ({';'.join(KEPALA_CSV)})"
            )
        isi = dict(zip(KEPALA_CSV, sel, strict=True))
        keluar.append(
            BarisNotasi(
                kode=isi["kode"].strip().upper(),
                jenis=isi["jenis"].strip(),
                tanggal_mulai=date.fromisoformat(isi["tanggal_mulai"].strip()),
                tanggal_selesai=(
                    date.fromisoformat(isi["tanggal_selesai"].strip())
                    if isi["tanggal_selesai"].strip()
                    else None
                ),
                keterangan=isi["keterangan"].strip(),
            )
        )
    return keluar


def _baca_catatan_lama(jalur: Path) -> list[tuple[frozenset[str], str]]:
    """Catatan bertanda jenis di kepala berkas yang sudah ada."""
    if not jalur.exists():
        return []
    keluar: list[tuple[frozenset[str], str]] = []
    for baris in jalur.read_text(encoding="utf-8-sig").splitlines():
        cocok = POLA_CATATAN.match(baris)
        if cocok:
            jenis = frozenset(satu.strip() for satu in cocok.group(1).split(",") if satu.strip())
            keluar.append((jenis, cocok.group(2)))
    return keluar


def _ditulis_modul_ini(baris: BarisNotasi) -> bool:
    """True bila baris itu berasal dari pengambilan otomatis — hanya baris itu yang boleh ditutup."""
    return PENANDA_BARIS in baris.keterangan or PENANDA_AKTIVITAS in baris.keterangan


def tulis_berkas(
    hasil: HasilNotasi,
    jalur: Path,
    *,
    diakses: date,
    jumlah_akses: int = 0,
) -> HasilTulisNotasi:
    """Perbarui `notasi-khusus.csv`: tambah yang baru, tutup yang tidak lagi tercantum.

    Berkasnya ditulis lewat berkas sementara di folder yang sama lalu diganti namanya, mengikuti
    `kienis.py`/`ksei.py`: berkas separuh jadi adalah **daftar yang salah**, bukan berkas rusak.
    """
    lama = _baca_baris_lama(jalur)
    jenis_diperbarui = (
        frozenset() if hasil.hanya_menambah else hasil.jenis_dicakup or {satu.jenis for satu in hasil.baris}
    )
    if hasil.catatan and not jenis_diperbarui:
        # Catatan bertanda `[]` tidak terbaca `POLA_CATATAN`, jadi akan hilang diam-diam di
        # penulisan berikutnya.
        raise GalatNotasi(
            "Hasil notasi memuat catatan tetapi tidak menyebut jenis yang dicakupnya (tanpa baris "
            "dan tanpa jenis_dicakup); catatannya tidak bisa ditandai jenis."
        )
    kunci_lama = {(satu.kode, satu.jenis, satu.tanggal_mulai) for satu in lama}
    terbuka = {(satu.kode, satu.jenis, satu.tanggal_mulai) for satu in lama if satu.tanggal_selesai is None}
    for satu in hasil.penutupan:
        kunci = (satu.kode, satu.jenis, satu.tanggal_mulai)
        if satu.tanggal_selesai is None or kunci not in terbuka or kunci in {
            (lain.kode, lain.jenis, lain.tanggal_mulai) for lain in hasil.baris
        }:
            raise GalatNotasi(
                f"penutupan {satu.jenis} {satu.kode} mulai {satu.tanggal_mulai.isoformat()} tidak "
                "menunjuk tepat satu baris terbuka di berkas"
            )
    penutupan_per_kunci = {(satu.kode, satu.jenis, satu.tanggal_mulai): satu for satu in hasil.penutupan}
    lama = [penutupan_per_kunci.get((satu.kode, satu.jenis, satu.tanggal_mulai), satu) for satu in lama]
    masuk_per_kunci = {(satu.kode, satu.jenis, satu.tanggal_mulai): satu for satu in hasil.baris}
    baru = [satu for satu in hasil.baris if (satu.kode, satu.jenis, satu.tanggal_mulai) not in kunci_lama]

    masih_tercantum = {(satu.kode, satu.jenis) for satu in hasil.baris}
    ditutup: list[BarisNotasi] = []
    tetap: list[BarisNotasi] = []
    jumlah_ditutup = 0
    for satu in lama:
        pengganti = masuk_per_kunci.get((satu.kode, satu.jenis, satu.tanggal_mulai))
        if (
            satu.tanggal_selesai is None
            and pengganti is not None
            and pengganti.tanggal_selesai is not None
            and _ditulis_modul_ini(satu)
        ):
            ditutup.append(pengganti)
            jumlah_ditutup += 1
            continue
        if (
            pengganti is not None
            and _ditulis_modul_ini(satu)
            and PENANDA_NOTASI_TIDAK_LENGKAP in pengganti.keterangan
            and PENANDA_NOTASI_TIDAK_LENGKAP not in satu.keterangan
        ):
            # Perubahan cakupan sumber adalah revisi provenance. CSV memuat versi terbaru;
            # ingesti menyimpan revisi baru append-only di basis data.
            tetap.append(pengganti)
            continue
        if (
            satu.tanggal_selesai is None
            and _ditulis_modul_ini(satu)
            and satu.jenis in jenis_diperbarui
            and (satu.kode, satu.jenis) not in masih_tercantum
            and satu.tanggal_mulai < hasil.tanggal_data
        ):
            ditutup.append(
                BarisNotasi(
                    kode=satu.kode,
                    jenis=satu.jenis,
                    tanggal_mulai=satu.tanggal_mulai,
                    tanggal_selesai=hasil.tanggal_data,
                    keterangan=(
                        f"{satu.keterangan} — TIDAK LAGI tercantum pada pengambilan "
                        f"{hasil.tanggal_data.isoformat()}"
                    ),
                )
            )
            jumlah_ditutup += 1
            continue
        tetap.append(satu)

    semua = sorted(
        [*tetap, *ditutup, *baru],
        key=lambda satu: (satu.kode, satu.jenis, satu.tanggal_mulai),
    )
    # Kepala ditulis ulang tiap kali; catatan jenis yang tidak diperbarui jalan ini masih
    # berlaku (mis. asal suspensi sesudah unggahan Notasi Khusus), jadi ikut dibawa.
    catatan = [
        *(
            (jenis, teks)
            for jenis, teks in _baca_catatan_lama(jalur)
            if jenis.isdisjoint(jenis_diperbarui)
        ),
        *((frozenset(jenis_diperbarui), teks) for teks in hasil.catatan),
    ]

    jalur.parent.mkdir(parents=True, exist_ok=True)
    sementara = jalur.with_name(f"{jalur.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        with sementara.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
            penulis = csv.writer(berkas_tulis, delimiter=";", lineterminator="\n")
            penulis.writerow(KEPALA_CSV)
            for satu in _komentar(
                hasil, catatan, diakses=diakses, jumlah_akses=jumlah_akses, jalur=jalur
            ):
                berkas_tulis.write(satu + "\n")
            for satu in semua:
                penulis.writerow(satu.sel())
        shutil.move(str(sementara), str(jalur))
    except OSError:
        sementara.unlink(missing_ok=True)
        raise
    return HasilTulisNotasi(
        jalur=jalur,
        jumlah_baris=len(semua),
        baru=len(baru),
        ditutup=jumlah_ditutup + len(hasil.penutupan),
        papan_pemantauan=sum(1 for satu in semua if satu.jenis == JENIS_PAPAN_PEMANTAUAN),
    )


def _komentar(
    hasil: HasilNotasi,
    catatan: Sequence[tuple[frozenset[str], str]],
    *,
    diakses: date,
    jumlah_akses: int,
    jalur: Path,
) -> tuple[str, ...]:
    """Penjelasan yang ikut tertulis di dalam berkas, supaya isinya tidak salah dibaca."""
    return (
        "# " + "=" * 87,
        "# NOTASI KHUSUS, SUSPENSI, DAN UMA IDX (P22)",
        "# " + "=" * 87,
        "#",
        f"# Sumber   : {hasil.sumber or ALAMAT}",
        *(f"# CATATAN [{', '.join(sorted(jenis))}]: {teks}" for jenis, teks in catatan),
        f"# Data per : {tampilan.tanggal(hasil.tanggal_data)} (tanggal data / batas pengambilan)",
        f"# Diakses  : {tampilan.tanggal(diakses)} ({jumlah_akses} permintaan pada jalan ini)",
        "#",
        "# KENAPA BARISNYA BERTAMBAH, BUKAN DITIMPA",
        "#   Halaman itu menyajikan KEADAAN TERKINI dan tidak punya arsip bulanan. Kalau berkasnya",
        "#   ditimpa, riwayat notasi yang sudah lewat hilang dan tidak bisa dibangun ulang dari",
        "#   sumbernya (PRD 9.12) — padahal justru itu yang dibutuhkan perhitungan point-in-time.",
        "#   Baris yang tidak lagi tercantum DITUTUP dengan `tanggal_selesai`, bukan dihapus.",
        "#",
        "# ATURAN BARIS OTOMATIS:",
        "#   notasi khusus: tanggal_mulai adalah tanggal data halaman, bukan awal notasi;",
        "#   suspensi: tanggal_mulai adalah pengumuman suspensi, selesai pada pengumuman pembukaan kembali;",
        "#     baris dari PDF pengumuman unggahan (K99): tanggal_mulai adalah tanggal berlakunya;",
        f"#   UMA: tanggal_mulai adalah tanggal pengumuman, selesai {UMUR_UMA_HARI} hari kemudian.",
        "#   Baris isian tangan tidak ditutup otomatis.",
        "#",
        f"# Berkas: {jalur.name} — hasil unggahan Notasi Khusus IDX di dasbor (Impor & cadangan) atau",
        "# `python -m mejasaham --ambil-notasi`, lalu diimpor dengan `--impor <folder konfigurasi>`.",
        "# " + "=" * 87,
    )


def berkas_tujuan(folder_konfigurasi: Path) -> Path:
    return folder_konfigurasi / NAMA_BERKAS


def baca(folder_konfigurasi: Path) -> tuple[BarisNotasi, ...]:
    """Baca berkas yang ada (untuk laporan); berkas yang tidak ada berarti belum pernah diambil."""
    return tuple(_baca_baris_lama(berkas_tujuan(folder_konfigurasi)))


def ringkas_hasil(hasil: HasilTulisNotasi, baris: Sequence[BarisNotasi]) -> str:
    """Kalimat ringkas untuk keluaran terminal — angka yang dilaporkan apa adanya."""
    ppk = sorted({satu.kode for satu in baris if satu.jenis == JENIS_PAPAN_PEMANTAUAN and satu.tanggal_selesai is None})
    return "\n".join(
        [
            f"notasi-khusus.csv: {hasil.jumlah_baris} baris "
            f"({hasil.baru} baru, {hasil.ditutup} ditutup)",
            f"  papan pemantauan khusus aktif: {len(ppk)} emiten"
            + (f" — {', '.join(ppk[:15])}" + (" …" if len(ppk) > 15 else "") if ppk else ""),
        ]
    )


@dataclass(frozen=True)
class HasilAmbil:
    """Satu pengambilan lengkap `--ambil-notasi` (tombol "Perbarui data" tidak lagi, K96)."""

    notasi: HasilNotasi
    aktivitas: HasilAktivitas
    hasil_aktivitas: HasilNotasi
    tulisan: HasilTulisNotasi
    diakses: date

    def ringkas(self) -> str:
        baris = self.hasil_aktivitas.baris
        bagian = [
            f"Data per : notasi {tampilan.tanggal(self.notasi.tanggal_data)} · aktivitas sampai "
            f"{tampilan.tanggal(self.diakses)}",
            f"Berkas   : {self.tulisan.jalur}",
            ringkas_hasil(self.tulisan, baca(self.tulisan.jalur.parent)),
            f"  Aktivitas IDX: {sum(1 for satu in baris if satu.jenis == 'suspensi')} riwayat suspensi, "
            f"{sum(1 for satu in baris if satu.jenis == 'uma')} UMA; "
            f"{sum(1 for satu in baris if satu.jenis == 'suspensi' and satu.tanggal_selesai is None)} "
            "suspensi aktif",
        ]
        if self.aktivitas.multi_kode_terekonsiliasi:
            bagian.append(
                f"  {self.aktivitas.multi_kode_terekonsiliasi} pengumuman suspensi multi-kode sudah "
                f"dipetakan per kode ({NAMA_BERKAS_TEREKONSILIASI})."
            )
        if self.aktivitas.pengumuman_multi_kode:
            bagian.append(
                f"  PERINGATAN: {self.aktivitas.pengumuman_multi_kode} pengumuman suspensi "
                "multi-kode belum direkonsiliasi per emiten; daftar suspensi tidak lengkap. "
                "Petakan per kode, lalu tambahkan `Data_Download`-nya ke "
                f"{NAMA_BERKAS_TEREKONSILIASI}. Rinciannya tersimpan di komentar CSV."
            )
        if self.aktivitas.pembukaan_tanpa_awal:
            bagian.append(
                f"  PERINGATAN: {self.aktivitas.pembukaan_tanpa_awal} pengumuman pembukaan kembali "
                "tidak punya pasangan suspensi ber-kode tunggal; kemungkinan terkait pengumuman massal."
            )
        return "\n".join(bagian)


def ambil_ke_berkas(folder_konfigurasi: Path, *, jeda: float = JEDA_BAWAAN) -> HasilAmbil:
    """Ambil notasi khusus, suspensi, dan UMA IDX (P22), lalu perbarui `notasi-khusus.csv`.

    Berkasnya **bertambah**, bukan ditimpa: halaman sumbernya hanya menyajikan keadaan terkini,
    sehingga riwayatnya tidak bisa dibangun ulang kalau ditimpa (PRD 9.12). Baris yang tidak lagi
    tercantum ditutup dengan `tanggal_selesai`; baris isian tangan tidak disentuh. Basis data
    tidak ditulis di sini — refresh atau `--impor` membaca berkas ini. Melempar `GalatNotasi`
    (sumber) atau `OSError` (berkas).
    """
    notasi = urai(unduh(jeda=jeda))
    # Catatan ini milik daftar notasi; ditulis bersama daftarnya agar bertanda jenis notasi dan
    # terbawa ke kepala oleh penulisan aktivitas di bawah (`tulis_berkas`).
    notasi = replace(
        notasi,
        catatan=(f"Notasi khusus dinyatakan sumber per {notasi.tanggal_data.isoformat()}.",),
    )
    tujuan = berkas_tujuan(folder_konfigurasi)
    diakses = date.today()
    aktivitas = unduh_aktivitas(
        tanggal_data=diakses, jeda=jeda, terekonsiliasi=baca_terekonsiliasi(folder_konfigurasi)
    )
    hasil_aktivitas = HasilNotasi(
        tanggal_data=diakses,
        baris=aktivitas.baris,
        sumber="Halaman resmi IDX Notasi Khusus + API resmi IDX GetSuspension + GetUma",
        catatan=tuple(
            catatan
            for catatan in (
                (
                    f"{aktivitas.multi_kode_terekonsiliasi} pengumuman suspensi >1 Kode sudah "
                    f"dipetakan per kode (daftar {NAMA_BERKAS_TEREKONSILIASI})."
                )
                if aktivitas.multi_kode_terekonsiliasi
                else None,
                (
                    f"{aktivitas.pengumuman_multi_kode} pengumuman suspensi memakai kode >1 Kode; "
                    "aksi dan tanggal efektif per emiten belum direkonsiliasi, sehingga daftar "
                    "suspensi ini tidak lengkap."
                )
                if aktivitas.pengumuman_multi_kode
                else None,
                (
                    f"{aktivitas.pembukaan_tanpa_awal} pengumuman pembukaan kembali tidak "
                    "memiliki pasangan suspensi ber-kode tunggal; kemungkinan terkait pengumuman massal."
                )
                if aktivitas.pembukaan_tanpa_awal
                else None,
            )
            if catatan is not None
        ),
    )
    tulis_berkas(notasi, tujuan, diakses=diakses, jumlah_akses=1)
    tulisan = tulis_berkas(hasil_aktivitas, tujuan, diakses=diakses, jumlah_akses=3)
    return HasilAmbil(
        notasi=notasi,
        aktivitas=aktivitas,
        hasil_aktivitas=hasil_aktivitas,
        tulisan=tulisan,
        diakses=diakses,
    )
