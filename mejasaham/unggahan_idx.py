"""Berkas Ringkasan Saham IDX yang diunggah pengguna — bahan sumber harga kedua (K95, PRD 7.3).

Syarat Penggunaan IDX melarang web scraping, jadi aplikasi **tidak** mengambil berkas ini sendiri:
pengguna mengunduhnya dari situs IDX (tombol "Unduh" di halaman Ringkasan Saham), lalu
mengunggahnya lewat dasbor. Modul ini:

1. **Menyimpan berkas mentah apa adanya** di `<folder data>/unduhan-idx/ringkasan-saham/`, dengan
   catatan nama asli, ukuran, SHA-256, dan waktu unggah di `daftar.csv`. Berkas yang isinya sama
   persis tidak disimpan dua kali.
2. **Membaca isinya** (`baca`) dan menuliskannya sebagai `harga-harian.csv` di folder impor milik
   unggahan itu (`siapkan_folder_impor`). Basis data **tidak** disentuh di sini: penulisannya tetap
   lewat jalur impor biasa sesudah konfirmasi (aturan keras 6, K59 d), sehingga validasi berkasnya
   sama persis dengan `--impor`.
3. **Menyusun antrean impor** (`antrean_impor`, K97 langkah 4): unggahan yang tanggalnya belum ada
   di basis data, satu per tanggal (yang terbaru), termasuk tanggal yang **sudah lewat** — hari
   yang terlupa diunggah bisa diisi belakangan, dan beberapa berkas diimpor sekaligus.
4. **Menyusun pengingat** kapan waktunya mengunduh lagi: bila cek sumber kedua belum tepat waktu
   (PRD 7.3, tiap minggu) **dan** belum ada unggahan dalam 7 hari terakhir.

**Bentuk berkasnya** dibaca dari contoh nyata (`Ringkasan Saham-20261028.xlsx`, diunduh pengguna
29 Okt 2026, bukan ditebak — K95): XLSX keluaran SheetJS, satu lembar, baris 1 judul kolom (28
kolom, antara lain `Kode Saham`, `Tanggal Perdagangan Terakhir` berbentuk `28 Okt 2026`,
`Open Price`, `Tertinggi`, `Terendah`, `Penutupan`, `Volume`, `Nilai`), teks sebagai sel
`t="str"`, angka sebagai sel biasa. Dibaca dengan `zipfile` + `xml.etree` pustaka standar — tanpa
dependensi baru. Judul kolom yang dipakai **wajib** ada; bentuk lain ditolak dengan sebabnya.

**Arti nilai 0:** IDX menulis `Open Price` 0 bila tidak ada harga pembukaan (mis. ZONE 28 Okt
2026, `First Trade` juga 0), dan `Tertinggi`/`Terendah` 0 bila tidak ada transaksi. Nol di sana
berarti **tidak ada nilai**, bukan harga nol — jadi disimpan kosong (aturan keras 2). Penutupan
tetap disimpan: untuk saham tanpa transaksi IDX menulis penutupan sebelumnya, dan itulah yang
dibandingkan cek sumber kedua.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree

from mejasaham import ingesti, lokasi, mutu, tampilan

ALAMAT_RINGKASAN_SAHAM = "https://www.idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/"

#: Jeda pengingat sama dengan cadence cek sumber kedua (PRD 7.3, "tiap minggu").
HARI_PENGINGAT = mutu.JEDA_CEK_SUMBER_KEDUA_HARI

#: Batas ukuran **seluruh** berkas dalam satu kiriman formulir (beberapa berkas sekaligus, K97
#: langkah 4). Berkas nyata ±0,85 MB, jadi batas ini muat puluhan hari.
BATAS_BAIT_SEKALIGUS = 64 * 1024 * 1024

#: Batas ukuran satu unggahan. Ringkasan Saham ±960 emiten jauh di bawah ini; batasnya hanya
#: menjaga server lokal dari berkas yang jelas salah pilih.
BATAS_BAIT = 20 * 1024 * 1024

#: Tombol "Unduh" Ringkasan Saham IDX menghasilkan XLSX (contoh nyata 29 Okt 2026).
AKHIRAN_DITERIMA = (".xlsx",)

#: Label sumber harga pembanding. Tetap sama dari minggu ke minggu supaya cek sumber kedua
#: membandingkan satu seri; asal tiap berkas (nama, SHA-256, waktu unggah) ada di `daftar.csv`.
SUMBER_IDX = "IDX Ringkasan Saham (unduhan pengguna dari situs IDX)"

#: Judul kolom berkas IDX → kolom `harga-harian.csv`.
KOLOM_IDX = {
    "Kode Saham": "kode",
    "Tanggal Perdagangan Terakhir": "tanggal",
    "Open Price": "open",
    "Tertinggi": "high",
    "Terendah": "low",
    "Penutupan": "close",
    "Volume": "volume",
    "Nilai": "nilai",
}
#: Kolom yang nol-nya berarti "tidak ada nilai" (lihat docstring modul).
_NOL_BERARTI_KOSONG = ("open", "high", "low")

_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_BULAN = {nama: nomor for nomor, nama in enumerate(tampilan.BULAN_SINGKAT, start=1)}

NAMA_DAFTAR = "daftar.csv"
_KOLOM_DAFTAR = ("diunggah_pada", "nama_asli", "berkas", "ukuran_bait", "sha256")

#: Cache turunan tanggal perdagangan per isi berkas (SHA-256 → tanggal). Membaca satu berkas
#: nyata ±0,36 dtk (terukur 29 Okt 2026), jadi antrean impor tanpa cache akan membaca ulang
#: seluruh unggahan setiap kali halamannya dibuka. Boleh dihapus; ia diisi ulang dari berkasnya.
NAMA_TANGGAL = "tanggal-berkas.csv"


class GalatUnggahan(ValueError):
    """Unggahan ditolak; pesannya siap ditampilkan apa adanya."""


@dataclass(frozen=True)
class Unggahan:
    diunggah_pada: datetime
    nama_asli: str
    berkas: Path
    ukuran_bait: int
    sha256: str


@dataclass(frozen=True)
class HasilSimpan:
    unggahan: Unggahan
    #: True bila isi yang sama persis sudah pernah diunggah — tidak disimpan ulang.
    sudah_ada: bool

    def ringkas(self) -> str:
        u = self.unggahan
        if self.sudah_ada:
            awal = (
                f"Berkas ini sudah pernah diunggah pada {tampilan.tanggal(u.diunggah_pada.date())} "
                f"{u.diunggah_pada:%H.%M} "
                f"(SHA-256 sama); tidak disimpan ulang."
            )
        else:
            awal = (
                f"Tersimpan: {u.berkas} ({tampilan.angka(u.ukuran_bait, 0)} bait, "
                f"SHA-256 {u.sha256[:12]}…)."
            )
        return awal + " Isinya belum masuk basis data sampai impornya dikonfirmasi."


@dataclass(frozen=True)
class RingkasanSaham:
    """Isi satu berkas Ringkasan Saham IDX, siap ditulis sebagai `harga-harian.csv`."""

    tanggal: date
    #: Baris per emiten: kolom `harga-harian.csv` → teks (kosong = tidak ada nilai).
    baris: tuple[dict[str, str], ...]


def folder() -> Path:
    return lokasi.folder_data() / "unduhan-idx" / "ringkasan-saham"


def nama_aman(nama: str) -> str:
    dasar = Path(nama.replace("\\", "/")).name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", dasar).strip("._") or "berkas"


def daftar() -> tuple[Unggahan, ...]:
    """Seluruh unggahan, terlama dulu."""
    jalur = folder() / NAMA_DAFTAR
    if not jalur.exists():
        return ()
    with jalur.open(encoding="utf-8-sig", newline="") as berkas:
        return tuple(
            Unggahan(
                diunggah_pada=datetime.fromisoformat(baris["diunggah_pada"]),
                nama_asli=baris["nama_asli"],
                berkas=folder() / baris["berkas"],
                ukuran_bait=int(baris["ukuran_bait"]),
                sha256=baris["sha256"],
            )
            for baris in csv.DictReader(berkas, delimiter=";")
        )


def terakhir() -> Unggahan | None:
    semua = daftar()
    return semua[-1] if semua else None


def simpan(nama_asli: str, isi: bytes, *, momen: datetime | None = None) -> HasilSimpan:
    """Simpan berkas unggahan mentah. Melempar `GalatUnggahan` atau `lokasi.GalatLokasi`."""
    if not isi:
        raise GalatUnggahan("berkasnya kosong (0 bait) — pilih berkas hasil unduhan Ringkasan Saham")
    if len(isi) > BATAS_BAIT:
        raise GalatUnggahan(
            f"berkasnya {tampilan.angka(len(isi), 0)} bait, lebih dari batas "
            f"{tampilan.angka(BATAS_BAIT, 0)} bait — kemungkinan salah pilih"
        )
    if not nama_asli.lower().endswith(AKHIRAN_DITERIMA):
        raise GalatUnggahan(
            f"'{nama_asli}' bukan berkas tabel ({', '.join(AKHIRAN_DITERIMA)}); unggah berkas "
            "hasil tombol Unduh di halaman Ringkasan Saham IDX"
        )
    sidik = hashlib.sha256(isi).hexdigest()
    for lama in daftar():
        if lama.sha256 == sidik:
            return HasilSimpan(lama, sudah_ada=True)

    waktu = (momen or datetime.now().astimezone()).replace(microsecond=0)
    tujuan = lokasi.pastikan_folder(folder())
    nama = f"{waktu:%Y%m%dT%H%M%S}_{nama_aman(nama_asli)}"
    sementara = tujuan / (nama + ".sebagian")
    sementara.write_bytes(isi)
    sementara.replace(tujuan / nama)

    jalur_daftar = tujuan / NAMA_DAFTAR
    baru = not jalur_daftar.exists()
    with jalur_daftar.open("a", encoding="utf-8-sig" if baru else "utf-8", newline="") as berkas:
        penulis = csv.writer(berkas, delimiter=";")
        if baru:
            penulis.writerow(_KOLOM_DAFTAR)
        penulis.writerow((waktu.isoformat(), nama_asli, nama, len(isi), sidik))
    return HasilSimpan(Unggahan(waktu, nama_asli, tujuan / nama, len(isi), sidik), sudah_ada=False)


def _kolom(rujukan: str) -> str:
    return re.sub(r"\d+", "", rujukan)


def baca_lembar(isi_zip: zipfile.ZipFile) -> list[dict[str, str]]:
    """Baris lembar pertama sebagai {huruf kolom: teks}. Teks bersama (`t="s"`) ikut didukung."""
    nama = sorted(n for n in isi_zip.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
    if not nama:
        raise GalatUnggahan("berkas XLSX tidak memuat lembar kerja")
    bersama: list[str] = []
    if "xl/sharedStrings.xml" in isi_zip.namelist():
        akar = ElementTree.fromstring(isi_zip.read("xl/sharedStrings.xml"))
        bersama = ["".join(t.text or "" for t in si.iter(f"{{{_NS['x']}}}t")) for si in akar.findall("x:si", _NS)]
    akar = ElementTree.fromstring(isi_zip.read(nama[0]))
    hasil: list[dict[str, str]] = []
    for baris in akar.iterfind("x:sheetData/x:row", _NS):
        sel: dict[str, str] = {}
        for c in baris.findall("x:c", _NS):
            jenis = c.get("t", "n")
            if jenis == "inlineStr":
                teks = "".join(t.text or "" for t in c.iter(f"{{{_NS['x']}}}t"))
            else:
                v = c.find("x:v", _NS)
                teks = "" if v is None or v.text is None else v.text
                if jenis == "s" and teks:
                    teks = bersama[int(teks)]
            sel[_kolom(c.get("r", ""))] = teks.strip()
        hasil.append(sel)
    return hasil


def _tanggal_idx(teks: str, di_mana: str) -> date:
    cocok = re.fullmatch(r"(\d{1,2}) (\w{3}) (\d{4})", teks)
    if cocok is None or cocok.group(2) not in _BULAN:
        raise GalatUnggahan(f"{di_mana}: tanggal '{teks}' bukan bentuk '28 Okt 2026'")
    return date(int(cocok.group(3)), _BULAN[cocok.group(2)], int(cocok.group(1)))


def _angka_bulat(teks: str, di_mana: str, kolom: str) -> str:
    """Bilangan bulat sebagai teks; kosong bila tidak ada nilai. Pecahan ditolak, bukan dibulatkan."""
    if teks == "":
        return ""
    try:
        angka = Decimal(teks)
    except InvalidOperation:
        raise GalatUnggahan(f"{di_mana}: kolom {kolom} berisi '{teks}', bukan angka") from None
    if angka != angka.to_integral_value() or angka < 0:
        raise GalatUnggahan(f"{di_mana}: kolom {kolom} berisi '{teks}', bukan bilangan bulat ≥ 0")
    nilai = str(int(angka))
    return "" if kolom in _NOL_BERARTI_KOSONG and nilai == "0" else nilai


def baca(jalur: Path) -> RingkasanSaham:
    """Baca berkas Ringkasan Saham IDX. Bentuk yang tidak dikenal ditolak dengan sebabnya."""
    try:
        with zipfile.ZipFile(jalur) as isi_zip:
            lembar = baca_lembar(isi_zip)
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError, IndexError, ValueError) as galat:
        if isinstance(galat, GalatUnggahan):
            raise
        raise GalatUnggahan(
            f"'{jalur.name}' tidak terbaca sebagai XLSX ({type(galat).__name__}: {galat}); unggah "
            "berkas hasil tombol Unduh di halaman Ringkasan Saham IDX"
        ) from galat
    if not lembar:
        raise GalatUnggahan(f"'{jalur.name}' tidak berisi baris apa pun")

    judul = {teks: kolom for kolom, teks in lembar[0].items()}
    hilang = [nama for nama in KOLOM_IDX if nama not in judul]
    if hilang:
        raise GalatUnggahan(
            f"'{jalur.name}' bukan berkas Ringkasan Saham IDX yang dikenal: judul kolom "
            f"{', '.join(hilang)} tidak ada di baris 1 (bentuknya mungkin berubah — beri tahu agen)"
        )

    baris: list[dict[str, str]] = []
    tanggal: set[date] = set()
    kode_terlihat: set[str] = set()
    for nomor, sel in enumerate(lembar[1:], start=2):
        if not any(sel.values()):
            continue
        di_mana = f"{jalur.name} baris {nomor}"
        isi = {tujuan: sel.get(judul[asal], "") for asal, tujuan in KOLOM_IDX.items()}
        kode = isi["kode"].upper()
        if not re.fullmatch(r"[A-Z0-9]{4,7}", kode):
            raise GalatUnggahan(f"{di_mana}: kode saham '{isi['kode']}' tidak dikenali")
        if kode in kode_terlihat:
            raise GalatUnggahan(f"{di_mana}: kode {kode} muncul dua kali")
        kode_terlihat.add(kode)
        hari = _tanggal_idx(isi["tanggal"], di_mana)
        tanggal.add(hari)
        hasil = {"kode": kode, "tanggal": hari.isoformat()}
        for kolom in ("open", "high", "low", "close", "volume", "nilai"):
            hasil[kolom] = _angka_bulat(isi[kolom], di_mana, kolom)
        if not hasil["close"] or hasil["close"] == "0":
            raise GalatUnggahan(f"{di_mana}: penutupan {kode} kosong atau nol")
        baris.append(hasil)

    if not baris:
        raise GalatUnggahan(f"'{jalur.name}' tidak memuat satu emiten pun")
    if len(tanggal) != 1:
        raise GalatUnggahan(
            f"'{jalur.name}' memuat {len(tanggal)} tanggal perdagangan berbeda "
            f"({', '.join(tampilan.tanggal(t) for t in sorted(tanggal))}); Ringkasan Saham "
            "seharusnya satu hari bursa"
        )
    return RingkasanSaham(tanggal=tanggal.pop(), baris=tuple(baris))


def folder_impor(unggahan: Unggahan | Sequence[Unggahan]) -> Path:
    """Folder impor milik satu unggahan (atau satu gabungan): hanya berisi `harga-harian.csv`.

    Gabungan beberapa unggahan diberi nama dari sidik isinya, sehingga pilihan yang sama selalu
    menulis ke folder yang sama dan label sumber impornya bisa ditelusuri kembali.
    """
    semua = (unggahan,) if isinstance(unggahan, Unggahan) else tuple(unggahan)
    if len(semua) == 1:
        return folder() / "impor" / semua[0].berkas.stem
    sidik = hashlib.sha256("".join(sorted(satu.sha256 for satu in semua)).encode()).hexdigest()
    return folder() / "impor" / f"gabungan-{len(semua)}-{sidik[:16]}"


def siapkan_folder_impor(
    unggahan: Unggahan | Sequence[Unggahan],
    ringkasan: RingkasanSaham | Sequence[RingkasanSaham],
) -> Path:
    """Tulis `harga-harian.csv` untuk jalur impor biasa. Basis data tidak disentuh."""
    isi = (ringkasan,) if isinstance(ringkasan, RingkasanSaham) else tuple(ringkasan)
    tujuan = lokasi.pastikan_folder(folder_impor(unggahan))
    sementara = tujuan / "harga-harian.csv.sebagian"
    kolom = ("kode", "tanggal", "open", "high", "low", "close", "volume", "nilai",
             "penyesuaian_sumber", "sumber")
    with sementara.open("w", encoding="utf-8-sig", newline="") as berkas:
        penulis = csv.writer(berkas, delimiter=";")
        penulis.writerow(kolom)
        for satu_hari in isi:
            for satu in satu_hari.baris:
                # Ringkasan Saham adalah harga perdagangan apa adanya pada hari itu.
                penulis.writerow(
                    [satu[k] for k in kolom[:8]] + [ingesti.PENYESUAIAN_TIDAK_DISESUAIKAN, SUMBER_IDX]
                )
    sementara.replace(tujuan / "harga-harian.csv")
    return tujuan


def _baca_cache_tanggal() -> dict[str, date]:
    jalur = folder() / NAMA_TANGGAL
    if not jalur.exists():
        return {}
    with jalur.open(encoding="utf-8-sig", newline="") as berkas:
        return {
            baris["sha256"]: date.fromisoformat(baris["tanggal"])
            for baris in csv.DictReader(berkas, delimiter=";")
        }


def tanggal_berkas(unggahan: Unggahan) -> date:
    """Tanggal perdagangan isi berkas; dibaca sekali per isi, lalu diingat di `NAMA_TANGGAL`.

    Melempar `GalatUnggahan` bila berkasnya tidak terbaca (tidak diingat: berkas yang sama tetap
    ditolak dengan sebabnya setiap kali).
    """
    cache = _baca_cache_tanggal()
    if unggahan.sha256 in cache:
        return cache[unggahan.sha256]
    hari = baca(unggahan.berkas).tanggal
    jalur = lokasi.pastikan_folder(folder()) / NAMA_TANGGAL
    baru = not jalur.exists()
    with jalur.open("a", encoding="utf-8-sig" if baru else "utf-8", newline="") as berkas:
        penulis = csv.writer(berkas, delimiter=";")
        if baru:
            penulis.writerow(("sha256", "tanggal"))
        penulis.writerow((unggahan.sha256, hari.isoformat()))
    return hari


@dataclass(frozen=True)
class AntreanImpor:
    """Unggahan yang belum masuk basis data, dikelompokkan menurut apa yang bisa dilakukan."""

    #: Tanggal data snapshot terakhir; `None` bila belum ada snapshot.
    tanggal_snapshot: date | None
    #: Siap diimpor: tanggal ≤ snapshot terakhir dan belum ada bar IDX-nya. Satu per tanggal
    #: (unggahan terbaru), urut tanggal.
    siap: tuple[tuple[Unggahan, date], ...] = ()
    #: Tanggalnya sesudah snapshot terakhir: "Perbarui data" dulu.
    menunggu: tuple[tuple[Unggahan, date], ...] = ()
    #: Unggahan lebih lama untuk tanggal yang sama dengan unggahan yang lebih baru (tidak dipakai).
    diganti: tuple[Unggahan, ...] = ()
    #: Unggahan yang isinya tidak terbaca, beserta sebabnya.
    tak_terbaca: tuple[tuple[Unggahan, str], ...] = ()


def antrean_impor(sambungan: sqlite3.Connection) -> AntreanImpor:
    """Unggahan yang tanggalnya belum punya bar IDX di basis data (K97 langkah 4).

    "Sudah diimpor" dinilai dari **tanggal** (ada bar berlabel `SUMBER_IDX` pada tanggal itu),
    bukan dari berkasnya: berkas yang diunduh ulang untuk tanggal yang sudah ada tidak diimpor
    lagi lewat antrean ini.
    """
    terakhir = sambungan.execute(
        "SELECT tanggal_data FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()
    tanggal_snapshot = date.fromisoformat(terakhir[0]) if terakhir else None

    per_tanggal: dict[date, list[Unggahan]] = {}
    tak_terbaca: list[tuple[Unggahan, str]] = []
    for satu in daftar():
        try:
            hari = tanggal_berkas(satu)
        except GalatUnggahan as galat:
            tak_terbaca.append((satu, str(galat)))
            continue
        per_tanggal.setdefault(hari, []).append(satu)

    siap: list[tuple[Unggahan, date]] = []
    menunggu: list[tuple[Unggahan, date]] = []
    diganti: list[Unggahan] = []
    for hari in sorted(per_tanggal):
        ada = sambungan.execute(
            # Penyaring `tanggal` lebih dulu supaya indeks tanggal yang dipakai, bukan pemindaian
            # seluruh bar harga.
            "SELECT 1 FROM harga_harian WHERE tanggal = ? AND sumber = ? LIMIT 1",
            (hari.isoformat(), SUMBER_IDX),
        ).fetchone()
        if ada is not None:
            continue
        *lama, terbaru = per_tanggal[hari]  # `daftar()` urut waktu unggah
        diganti.extend(lama)
        if tanggal_snapshot is not None and hari <= tanggal_snapshot:
            siap.append((terbaru, hari))
        else:
            menunggu.append((terbaru, hari))
    return AntreanImpor(
        tanggal_snapshot=tanggal_snapshot,
        siap=tuple(siap),
        menunggu=tuple(menunggu),
        diganti=tuple(diganti),
        tak_terbaca=tuple(tak_terbaca),
    )


def cari(nama_berkas: str) -> Unggahan | None:
    """Unggahan menurut nama berkas tersimpannya (bukan jalur — isian formulir tidak dipercaya)."""
    return next((satu for satu in daftar() if satu.berkas.name == nama_berkas), None)


def pengingat(sambungan: sqlite3.Connection, hari_ini: date | None = None) -> str | None:
    """Kalimat pengingat untuk dasbor, atau None bila belum waktunya.

    Diam selama cek sumber kedua tepat waktu (PRD 7.3). Selain itu: bila unggahan terakhir masih
    berumur ≤ 7 hari, yang tertunda adalah **impornya**, jadi itu yang diingatkan; bila lebih tua
    (atau belum ada), waktunya mengunduh lagi.
    """
    hari = hari_ini or date.today()
    keadaan = mutu.keadaan_cek_sumber_kedua(sambungan, momen=hari)
    if keadaan.status == mutu.STATUS_TEPAT_WAKTU:
        return None
    akhir = terakhir()
    if akhir is not None and (hari - akhir.diunggah_pada.date()).days <= HARI_PENGINGAT:
        return (
            f"Ringkasan Saham IDX sudah diunggah ({tampilan.tanggal(akhir.diunggah_pada.date())}), "
            "tetapi cek sumber kedua belum lengkap: impor berkasnya di menu Impor & cadangan "
            '(bagian "Belum diimpor", tombol "Impor … berkas").'
        )
    dasar = (
        "belum pernah ada unggahan"
        if akhir is None
        else (
            f"unggahan terakhir {tampilan.tanggal(akhir.diunggah_pada.date())}, "
            f"{(hari - akhir.diunggah_pada.date()).days} hari lalu"
        )
    )
    return (
        "Waktunya mengunduh Ringkasan Saham IDX untuk cek sumber kedua mingguan (PRD 7.3; "
        f"{dasar}). Unduh sesudah bursa tutup, lalu unggah di menu Impor & cadangan."
    )
