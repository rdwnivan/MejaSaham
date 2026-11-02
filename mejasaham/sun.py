"""Imbal hasil SUN dari halaman HPW PHEI (PRD 7.1/8.2) — pengambil otomatis.

Kenapa berkas ini ada
---------------------
`imbal-hasil-sun.csv` tidak punya jalur otomatis sama sekali, sehingga metrik "imbal hasil laba
vs SUN" (PRD 8.2) dan saringan valuasi selalu berstatus "tidak dihitung" — padahal PRD 7.1
menetapkannya sebagai **data** bertanggal (C9), bukan parameter yang boleh dikarang.

Sumbernya, dan kenapa sumber ini
--------------------------------
PT Penilai Harga Efek Indonesia (PHEI) menerbitkan **Harga Pasar Wajar dan Imbal Hasil** harian,
termasuk kurva imbal hasil Surat Berharga Negara per tenor. Halaman `Data/HPW-dan-Imbal-Hasil`
memuatnya sebagai **tabel HTML biasa**, jadi penguraiannya memakai `re` dari pustaka standar —
tidak ada dependensi baru (K3 tidak berubah).

Dua jalur lain diperiksa lebih dulu dan gagal, supaya pilihan ini tidak tampak seperti tebakan:
`bi.go.id` memutus koneksi, dan `api-djppr.kemenkeu.go.id` ternyata CMS yang isinya dirender
aplikasi (tidak ada berkas deret imbal hasil yang bisa diunduh). Rincian beserta buktinya di
`docs/keputusan.md` bagian 5 — termasuk catatan bahwa temuan itu berlaku untuk **satu jaringan**,
seperti temuan `idx.co.id` sebelumnya.

Yang dipakai, dan yang sengaja **tidak**
----------------------------------------
Hanya kolom **Today**, dan hanya tenor yang disebut PRD 8.2 (**10 tahun**). Kolom "Yesterday"
tidak diimpor: halaman ini menyatakan **satu** tanggal valuasi (mis. "per 9-Oktober-2026"),
sedangkan tanggal "kemarin" tidak dinyatakan di mana pun. Menghitungnya sendiri berarti menebak
tanggal, dan baris bertanggal tebakan lebih buruk daripada tidak ada baris — aturan keras 1 dan 3.

Batas yang perlu diketahui
--------------------------
Halaman ini menyajikan nilai **hari itu**, bukan deret riwayat. Jadi berkas ini bertambah satu
baris setiap `--ambil-sun` dijalankan, dan riwayat sebelum pengambil ini ada **tidak bisa** diisi
dari sini. Berkasnya tetap boleh disunting tangan untuk menambah riwayat dari publikasi lain:
pengambilan berikutnya menambah atau memperbarui baris pada `(tanggal, tenor)` yang sama, tidak
menimpa seluruh berkas.

Catatan kecil yang jujur: percobaan ulang unduhan di sini mirip `kalender.unduh` dan
`ksei.unduh_master`. Ketiganya kecil dan masing-masing milik adaptornya; menyatukannya menjadi
satu modul pengunduh adalah kerapian yang belum dikerjakan.
"""

from __future__ import annotations

import csv
import io
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from mejasaham import berkas, tampilan
from mejasaham.berkas import PENANDA_CONTOH
from mejasaham.ingesti import GalatIngesti

#: Halaman kurva imbal hasil SBN (Harga Pasar Wajar & Imbal Hasil) milik PHEI.
POLA_URL_HPW = "https://www.phei.co.id/Data/HPW-dan-Imbal-Hasil"

AGEN_PENGGUNA = "MejaSaham/0.1 (pengambilan berkas publik PHEI; python-urllib)"
TIMEOUT_BAWAAN = 60.0
PERCOBAAN_BAWAAN = 3
JEDA_BAWAAN = 2.0

#: Tenor yang dipakai berhitung. PRD 8.2 menulis "imbal hasil SUN 10 tahun", jadi tenornya bukan
#: pilihan bebas: mengubahnya mengubah arti metrik "imbal hasil laba − SUN".
TENOR_BAWAAN = 10

#: Batas kewajaran persen. Angka di luar ini berarti kolomnya bergeser atau satuannya berubah —
#: dan menolak lebih baik daripada menyimpan angka yang salah tanpa jejak.
BATAS_PERSEN = (Decimal("0.01"), Decimal("30"))

KEPALA_CSV = ("tanggal", "tenor_tahun", "imbal_hasil_persen", "sumber")

#: Nama bulan pada pernyataan tanggal PHEI ("per 9-Oktober-2026"). Bahasa Indonesianya yang
#: dipakai sumbernya; nama Inggris ikut diterima supaya perubahan kecil tidak langsung mematikan
#: pengambilnya.
BULAN = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7, "august": 8,
    "october": 10, "december": 12,
}

POLA_TANGGAL = re.compile(r"per\s+(\d{1,2})-([A-Za-z]+)-(\d{4})", re.IGNORECASE)
POLA_TABEL = re.compile(r"<table.*?</table>", re.DOTALL | re.IGNORECASE)
POLA_BARIS = re.compile(r"<tr.*?</tr>", re.DOTALL | re.IGNORECASE)
POLA_SEL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL | re.IGNORECASE)
POLA_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class HasilSUN:
    """Satu angka imbal hasil SUN beserta asalnya — apa adanya, tanpa pembulatan diam-diam."""

    tanggal: date
    tenor_tahun: int
    #: Nilai sebagai angka, untuk ditulis ke berkas.
    persen: Decimal
    #: Teks persis seperti dinyatakan sumbernya (mis. `7,1845`), supaya presisinya tidak hilang.
    teks_asli: str
    #: Kalimat asal yang bisa diperiksa manusia: dari halaman mana, tanggal berapa, kapan diakses.
    sumber: str

    def baris_csv(self) -> tuple[str, ...]:
        """Baris berkas impor. Desimal ditulis dengan **titik**: pembacanya `Decimal` ketat."""
        return (
            self.tanggal.isoformat(),
            str(self.tenor_tahun),
            f"{self.persen:f}",
            self.sumber,
        )


@dataclass
class HasilAmbilSUN:
    """Laporan satu jalan `--ambil-sun`: apa yang ditulis, dan apa yang tidak."""

    jalur: Path
    hasil: HasilSUN
    baris_baru: int = 0
    baris_diperbarui: int = 0
    baris_tidak_berubah: int = 0
    jumlah_baris_berkas: int = 0
    peringatan: list[str] = field(default_factory=list)

    def ringkas(self) -> str:
        bagian = [
            f"[ambil-sun] {self.jalur}",
            f"  sumber : PHEI HPW dan Imbal Hasil ({POLA_URL_HPW})",
            f"  nilai  : SUN {self.hasil.tenor_tahun} tahun = {self.hasil.teks_asli}% "
            f"per {tampilan.tanggal(self.hasil.tanggal)}",
            f"  berkas : {self.jumlah_baris_berkas} baris data "
            f"({self.baris_baru} baru, {self.baris_diperbarui} diperbarui, "
            f"{self.baris_tidak_berubah} sudah ada dan sama)",
        ]
        bagian.extend(f"  PERINGATAN: {satu}" for satu in self.peringatan)
        bagian.append(
            "  Jalankan --impor pada folder yang sama untuk memasukkannya ke basis data."
        )
        return "\n".join(bagian)

    def __str__(self) -> str:
        return self.ringkas()


# ---------------------------------------------------------------------------------------
# Pengambilan berkas
# ---------------------------------------------------------------------------------------


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
    """Unduh satu halaman dengan percobaan ulang; kegagalan menyebut sebabnya."""
    pembuka = _buka if buka is None else buka
    galat_terakhir = ""
    for nomor in range(1, percobaan + 1):
        try:
            with pembuka(url, timeout) as balasan:  # type: ignore[union-attr]
                return balasan.read()
        except urllib.error.HTTPError as galat:
            galat_terakhir = f"HTTP {galat.code}"
            if galat.code == 404:
                break
        except (urllib.error.URLError, TimeoutError, OSError) as galat:
            galat_terakhir = f"{type(galat).__name__}: {galat}"
        if nomor < percobaan:
            time.sleep(jeda * nomor)
    raise GalatIngesti(f"{di_mana}: gagal mengunduh {url} — {galat_terakhir}")


# ---------------------------------------------------------------------------------------
# Penguraian halaman
# ---------------------------------------------------------------------------------------


def _teks(fragmen: str) -> str:
    """Isi sel tabel sebagai teks: tag dibuang, `&nbsp;` jadi spasi, spasi dirapikan."""
    return re.sub(r"\s+", " ", POLA_TAG.sub(" ", fragmen).replace("&nbsp;", " ")).strip()


def _desimal_koma(teks: str) -> Decimal | None:
    """Angka bergaya Indonesia (`7,1845`); titik ribuan dibuang, None bila bukan angka."""
    bersih = teks.strip().replace(".", "").replace(",", ".")
    if not bersih:
        return None
    try:
        return Decimal(bersih)
    except InvalidOperation:
        return None


def tanggal_valuasi(html: str, *, di_mana: str) -> date:
    """Tanggal valuasi yang **dinyatakan** halaman (bentuk `per 9-Oktober-2026`).

    Seluruh pernyataan tanggal di halaman harus sepakat. Kalau tidak, fungsi ini menolak:
    halaman yang memuat dua tanggal berbeda tidak boleh diringkas menjadi satu angka oleh tebakan.
    """
    temuan = POLA_TANGGAL.findall(html)
    if not temuan:
        raise GalatIngesti(
            f"{di_mana}: halaman tidak menyatakan tanggal valuasi (pola 'per <tgl>-<bulan>-<tahun>'). "
            "Tanpa tanggal dari sumbernya, baris yang ditulis akan bertanggal tebakan — dan itu "
            "dilarang aturan keras 1/3. Periksa apakah bentuk halamannya berubah."
        )

    tanggal: list[date] = []
    for hari_teks, bulan_teks, tahun_teks in temuan:
        bulan = BULAN.get(bulan_teks.lower())
        if bulan is None:
            raise GalatIngesti(
                f"{di_mana}: nama bulan {bulan_teks!r} tidak dikenal pada pernyataan tanggal "
                f"'per {hari_teks}-{bulan_teks}-{tahun_teks}'."
            )
        try:
            tanggal.append(date(int(tahun_teks), bulan, int(hari_teks)))
        except ValueError as galat:
            raise GalatIngesti(
                f"{di_mana}: tanggal 'per {hari_teks}-{bulan_teks}-{tahun_teks}' tidak sah"
            ) from galat

    unik = sorted(set(tanggal))
    if len(unik) > 1:
        daftar = ", ".join(satu.isoformat() for satu in unik)
        raise GalatIngesti(
            f"{di_mana}: halaman menyatakan lebih dari satu tanggal valuasi ({daftar}). "
            "Meringkasnya menjadi satu berarti menebak mana yang berlaku untuk tabel tenor."
        )
    return unik[0]


def baris_tenor(html: str, *, di_mana: str, tenor: int = TENOR_BAWAAN) -> tuple[str, list[str]]:
    """Baris tenor yang diminta: (teks tenor, sel-sel angkanya) apa adanya.

    Tabel dikenali dari kepalanya (`Tenor` **dan** `Today`), bukan dari urutannya di halaman:
    halaman yang menambah tabel baru tidak boleh menggeser arti kolomnya.
    """
    kandidat: list[tuple[str, list[str]]] = []
    for tabel in POLA_TABEL.findall(html):
        baris = POLA_BARIS.findall(tabel)
        if not baris:
            continue
        kepala = _teks(baris[0]).lower()
        if "tenor" not in kepala or "today" not in kepala:
            continue
        for baris_satu in baris[1:]:
            sel = [_teks(satu) for satu in POLA_SEL.findall(baris_satu)]
            if len(sel) < 2:
                continue
            angka_tenor = _desimal_koma(sel[0])
            if angka_tenor is None or angka_tenor != Decimal(tenor):
                continue
            kandidat.append((sel[0], sel[1:]))

    if not kandidat:
        raise GalatIngesti(
            f"{di_mana}: tidak ada baris tenor {tenor} pada tabel 'Tenor ... Today'. Bentuk "
            "halaman PHEI mungkin berubah — periksa halamannya sebelum angkanya dipakai."
        )
    if len(kandidat) > 1:
        raise GalatIngesti(
            f"{di_mana}: tenor {tenor} muncul {len(kandidat)} kali pada tabel yang berbeda, "
            "padahal PRD 8.2 hanya menyebut satu angka. Halaman perlu diperiksa manusia."
        )
    return kandidat[0]


def urai_hpw(
    html: str,
    *,
    di_mana: str,
    tenor: int = TENOR_BAWAAN,
    diakses: date | None = None,
) -> HasilSUN:
    """Baca satu angka imbal hasil SUN dari halaman HPW; menolak bila bentuknya tidak dikenali."""
    if "Tenor" not in html or "Today" not in html:
        raise GalatIngesti(
            f"{di_mana}: halaman tidak memuat tabel tenor/imbal hasil sama sekali. Yang diterima "
            "hanya halaman kurva imbal hasil PHEI; halaman lain (login, galat, pemeliharaan) akan "
            "terlihat seperti ini."
        )

    tanggal = tanggal_valuasi(html, di_mana=di_mana)
    teks_tenor, sel = baris_tenor(html, di_mana=di_mana, tenor=tenor)

    angka = [_desimal_koma(satu) for satu in sel]
    if len(angka) < 2 or any(satu is None for satu in angka):
        raise GalatIngesti(
            f"{di_mana}: baris tenor {teks_tenor} tidak memuat dua kolom angka yang terbaca "
            f"(Today, Yesterday): {sel!r}. Kolomnya mungkin bergeser."
        )
    now = angka[0]
    if now is None:  # tidak mungkin: sudah diperiksa di atas, tetapi tipe harus pasti
        raise GalatIngesti(f"{di_mana}: kolom Today pada tenor {teks_tenor} tidak terbaca")
    if not (BATAS_PERSEN[0] <= now <= BATAS_PERSEN[1]):
        raise GalatIngesti(
            f"{di_mana}: imbal hasil tenor {tenor} terbaca {now}%, di luar batas wajar "
            f"{BATAS_PERSEN[0]}-{BATAS_PERSEN[1]}%. Angka ini tidak disimpan."
        )

    return HasilSUN(
        tanggal=tanggal,
        tenor_tahun=tenor,
        persen=now,
        teks_asli=sel[0],
        sumber=(
            f"PHEI HPW dan Imbal Hasil, kurva imbal hasil SBN per {tampilan.tanggal(tanggal)} "
            f"(diakses {tampilan.tanggal(diakses or date.today())}, teks asli {sel[0]!r})"
        ),
    )


# ---------------------------------------------------------------------------------------
# Menulis berkas
# ---------------------------------------------------------------------------------------


def _potongan(baris_teks: str) -> list[str]:
    return next(csv.reader([baris_teks], delimiter=";"), [])


def _kunci_baris(potongan: Sequence[str]) -> tuple[str, str] | None:
    """(tanggal, tenor) sebuah baris data; None bila barisnya bukan data.

    Baris penjelasan (`#`), baris contoh (`<<CONTOH>>`), baris kosong, baris kepala, dan baris
    yang tanggalnya tidak berbentuk `YYYY-MM-DD` bukan data. Berkas yang rusak karena itu tidak
    "diperbaiki" diam-diam oleh penulis ini.
    """
    if len(potongan) < 3:
        return None
    if potongan[0].strip().startswith("#") or PENANDA_CONTOH in potongan[0]:
        return None
    tanggal = potongan[0].strip()
    if len(tanggal) != 10 or tanggal[4] != "-" or not tanggal.replace("-", "").isdigit():
        return None
    return tanggal, potongan[1].strip()


def _baris_teks(baris: Sequence[str]) -> str:
    """Satu baris data sebagai teks CSV (pemisah `;`), lewat penulis yang sama dengan berkasnya."""
    penyangga = io.StringIO()
    csv.writer(penyangga, delimiter=";", lineterminator="").writerow(baris)
    return penyangga.getvalue()


def tulis_baris(jalur: Path, hasil: HasilSUN) -> tuple[int, int, int, int]:
    """Tambahkan/perbarui satu baris pada berkas: (baru, diperbarui, tetap, total baris data).

    Berkas yang sudah ada **tidak** ditimpa: baris lain dipertahankan apa adanya — termasuk
    suntingan tangan dan riwayat dari publikasi lain — dan hanya baris dengan `(tanggal, tenor)`
    yang sama yang diperbarui bila isinya berbeda.
    """
    baris_baru = hasil.baris_csv()
    kunci_baru = (baris_baru[0], baris_baru[1])

    if not jalur.exists():
        # AC-12: bentuk bawaannya tetap tersedia. Templatenya disalin lebih dulu supaya penjelasan
        # di dalam berkas berasal dari satu tempat (berkas contoh), bukan disalin ulang di sini.
        berkas.siapkan_berkas_bawaan(jalur.parent)

    isi = jalur.read_text(encoding="utf-8-sig").splitlines()
    keluaran: list[str] = []
    baru = diperbarui = tetap = 0
    ketemu = False
    for baris_teks in isi:
        kunci = _kunci_baris(_potongan(baris_teks))
        if kunci != kunci_baru:
            keluaran.append(baris_teks)
            continue
        ketemu = True
        if [satu.strip() for satu in _potongan(baris_teks)] == [
            satu.strip() for satu in baris_baru
        ]:
            tetap += 1
            keluaran.append(baris_teks)
        else:
            diperbarui += 1
            keluaran.append(_baris_teks(baris_baru))

    if not ketemu:
        baru += 1
        keluaran.append(_baris_teks(baris_baru))

    with jalur.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
        for baris_teks in keluaran:
            berkas_tulis.write(baris_teks + "\n")

    jumlah = sum(1 for satu in keluaran if _kunci_baris(_potongan(satu)) is not None)
    return baru, diperbarui, tetap, jumlah


# ---------------------------------------------------------------------------------------
# Titik masuk
# ---------------------------------------------------------------------------------------


def ambil_sun(
    folder: Path,
    *,
    tenor: int = TENOR_BAWAAN,
    hari_ini: date | None = None,
    percobaan: int = PERCOBAAN_BAWAAN,
    jeda: float = JEDA_BAWAAN,
    timeout: float = TIMEOUT_BAWAAN,
    halaman: str = POLA_URL_HPW,
    buka: Callable[[str, float], object] | None = None,
) -> HasilAmbilSUN:
    """Unduh kurva imbal hasil PHEI, tambahkan satu baris ke `folder/imbal-hasil-sun.csv`.

    Berkasnya dibaca `--impor` seperti berkas impor lain; fungsi ini **tidak** menulis basis data.
    Pemisahan itu disengaja dan sama dengan `--ambil-kalender`: adaptor jaringan menulis berkas
    rujukan yang bisa diperiksa manusia lebih dulu, dan penulisan basis data tetap satu jalur
    (`--impor`) supaya tidak ada angka yang masuk tanpa terlihat.
    """
    hari = hari_ini or date.today()
    halaman_html = unduh(
        halaman, di_mana="halaman HPW PHEI", percobaan=percobaan, jeda=jeda, timeout=timeout,
        buka=buka,
    ).decode("utf-8", errors="replace")
    # Tanggal akses diserahkan dari sini, bukan diambil di dalam pengurai: pengurai harus bisa
    # diuji tanpa bergantung pada jam dinding.
    hasil = urai_hpw(
        halaman_html, di_mana=f"halaman HPW PHEI ({halaman})", tenor=tenor, diakses=hari
    )

    tujuan = folder / berkas.NAMA_BERKAS_SUN
    try:
        baru, diperbarui, tetap, jumlah = tulis_baris(tujuan, hasil)
    except OSError as galat:
        raise GalatIngesti(f"gagal menulis '{tujuan}': {galat}") from galat

    peringatan: list[str] = []
    if tetap:
        peringatan.append(
            "baris untuk (tanggal, tenor) itu sudah ada dan sama — tidak ada yang berubah. "
            "Halaman PHEI menyajikan nilai harian, jadi menjalankan perintah ini dua kali pada "
            "hari yang sama memang tidak menambah data."
        )
    return HasilAmbilSUN(
        jalur=tujuan,
        hasil=hasil,
        baris_baru=baru,
        baris_diperbarui=diperbarui,
        baris_tidak_berubah=tetap,
        jumlah_baris_berkas=jumlah,
        peringatan=peringatan,
    )
