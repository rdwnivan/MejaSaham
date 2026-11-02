"""Daftar emiten dari Master File Efek KSEI — jalur otomatis untuk semesta saham.

Kenapa modul ini ada
--------------------
`emiten.csv` adalah **semesta milik pengguna**: `--refresh` mengambil data untuk kode yang ada di
situ, dan aplikasi tidak mengarang daftarnya sendiri (aturan keras 1; lihat `berkas.py`). Selama
berkas itu belum diisi, aplikasi hanya melihat ~20 kode bootstrap dan laporan mutu menyebut
keterbatasan itu. Mengisinya dengan tangan untuk ~975 emiten bukan pekerjaan yang masuk akal,
sedangkan `idx.co.id` menolak pengambilan otomatis (HTTP 403 tantangan Cloudflare; 16 variasi URL
dan 24 percobaan meniru TLS browser semuanya gagal — dicatat di `docs/keputusan.md` bagian 5.1).

KSEI (Kustodian Sentral Efek Indonesia) menerbitkan **Master File Efek** bulanan di alamat
terbuka `web.ksei.co.id/Download/StatisEfekYYYYMMDD.txt.zip`: satu berkas teks berisi seluruh efek
yang tercatat, termasuk saham IDX. Tanggalnya menempel di nama berkas, dan berkasnya sendiri
menyatakan tanggal datanya di kolom `Date` — jadi asal angkanya bisa diaudit, bukan ditebak.
Alamat itu menerima permintaan tanpa penyamaran (diuji: User-Agent jujur bekerja), jadi modul ini
memakai agen pengguna apa adanya.

Yang diambil, dan yang sengaja TIDAK diambil
--------------------------------------------
Diambil: `kode`, `nama`, `jumlah_saham` (kolom `Num. of Sec`), dan `tanggal_notasi` (kolom
`Listing Date` — tanggal pencatatan sahamnya). Keempatnya dinyatakan berkas sumbernya, bukan
tafsiran. Nama kolom `tanggal_notasi` mengikuti tabel `emiten` di PRD 12 (tabel 23); PRD sendiri
tidak pernah menjelaskan arti nama itu, jadi pemetaannya dicatat sebagai pertanyaan **P18** di
`docs/keputusan.md` — bukan diputuskan diam-diam di sini.

**Tidak** diambil, dan tidak diganti apa pun (aturan keras 1 & 2):

* `sektor_idx_ic` — KSEI memakai taksonomi sendiri (`COMPUTER AND SERVICES`, `FISHERY`, `BANK`),
  bukan IDX-IC yang dipakai PRD. Pemetaan antara keduanya tidak diterbitkan sumber mana pun;
  menuliskannya berarti mengarang pemetaan.
* `papan` — tidak ada di berkas KSEI (tidak ada papan utama/pengembangan/pemantauan).
* `jenis` — `bank_keuangan`/`siklikal_komoditas` adalah keputusan analis, bukan atribut berkas.
* `free_float_persen` — kolom `Local (%)`/`Foreign (%)` KSEI adalah **komposisi kepemilikan**,
  bukan free float. Dua hal berbeda yang mudah tertukar, dan menukarnya menghasilkan metrik yang
  salah tanpa terlihat salah.
* `status_notasi` — `Status = ACTIVE` KSEI berarti efeknya aktif tercatat, **bukan** notasi
  khusus IDX. Notasi khusus punya berkas dan tabelnya sendiri (`notasi-khusus.csv`).

Saham preferen/seri (ISIN berawalan `ID2`) **dikeluarkan** dari daftar, dan pengeluarannya
dilaporkan — bukan dibuang diam-diam. Semesta aplikasi ini saham biasa: `MAMIP` (preferen) dan
`MYRXP` (seri B) tidak diperdagangkan di pasar yang sama dan harga penutupnya 0 di berkas sumber.

Keputusan-keputusan di atas dicatat di `docs/keputusan.md`.
"""

from __future__ import annotations

import csv
import io
import re
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from mejasaham import lokasi, tampilan
from mejasaham.berkas import NAMA_BERKAS_EMITEN, baca_emiten
from mejasaham.ingesti import GalatIngesti

#: Alamat berkas Master File Efek; `{tanggal}` dalam bentuk `YYYYMMDD`.
POLA_URL_MASTER = "https://web.ksei.co.id/Download/StatisEfek{tanggal}.txt.zip"

#: Agen pengguna apa adanya. KSEI menerima ini (diuji 9 Okt 2026); menyamar sebagai browser
#: tidak diperlukan, dan menyamar berarti berbohong tentang siapa yang mengambil berkas.
AGEN_PENGGUNA = "MejaSaham/0.1 (pengambilan berkas publik KSEI; python-urllib)"

#: Berapa akhir bulan ke belakang dicari bila berkas terbaru belum terbit. Berkasnya bulanan,
#: tetapi tidak setiap bulan ada: 31 Mei 2026 dan 28 Feb 2026 tidak diterbitkan (404), sedangkan
#: 30 Sep, 31 Agu, 31 Jul, 30 Jun, 30 Apr, dan 31 Mar 2026 ada. Karena itu pencarian **mundur**,
#: bukan menebak satu tanggal.
BULAN_DICARI = 6

PERCOBAAN_BAWAAN = 3
JEDA_BAWAAN = 2.0
TIMEOUT_BAWAAN = 60.0

#: Kolom yang wajib ada di kepala berkas KSEI. Berkas yang kepalanya berbeda **ditolak**: tanpa
#: pemeriksaan ini, perubahan bentuk berkas di sisi KSEI akan terbaca sebagai "tidak ada emiten".
KOLOM_WAJIB = (
    "Date",
    "Code",
    "Description",
    "Type",
    "Status",
    "Stock Exchange",
    "Isin Code",
    "Listing Date",
    "Num. of Sec",
)

#: Nama bulan di berkas KSEI memakai singkatan Inggris. Dipetakan sendiri, bukan lewat
#: `strptime("%b")`, karena `%b` mengikuti locale mesin — di Windows ber-locale Indonesia hasilnya
#: berbeda-beda untuk masukan yang sama.
BULAN_KSEI = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

#: Kepala `emiten.csv` — persis sama dengan template bawaan (`defaults/emiten.contoh.csv`).
KEPALA_CSV = (
    "kode",
    "nama",
    "sektor_idx_ic",
    "sektor_sumber",
    "jenis",
    "papan",
    "status_notasi",
    "tanggal_notasi",
    "jumlah_saham",
    "free_float_persen",
    "sumber",
    "dicatat_pada",
)

#: Pola kode saham IDX yang lazim. Kode di luar pola ini **tetap ditulis** (bisa jadi kelas saham
#: baru yang sah, mis. `GOTOM` untuk saham bervoting ganda), tetapi dilaporkan supaya terlihat.
POLA_KODE_LAZIM = re.compile(r"[A-Z]{4}\Z")

#: Berapa baris fisik boleh disambung untuk memulihkan satu catatan yang terbelah. Berkas KSEI
#: 30 Sep 2026 memuat satu catatan yang patah menjadi dua baris (baris 3619–3620); batas ini
#: memberi ruang untuk kejadian serupa tanpa menjelma menjadi penggabungan buta.
BATAS_SAMBUNG = 3


def url_master(tanggal: date) -> str:
    """Alamat berkas Master File Efek untuk satu tanggal."""
    return POLA_URL_MASTER.format(tanggal=tanggal.strftime("%Y%m%d"))


def akhir_bulan(tanggal: date) -> date:
    """Hari terakhir bulan yang memuat `tanggal`."""
    bulan_depan = (tanggal.replace(day=1) + timedelta(days=32)).replace(day=1)
    return bulan_depan - timedelta(days=1)


def kandidat_tanggal(hari_ini: date, *, bulan: int = BULAN_DICARI) -> tuple[date, ...]:
    """Akhir-akhir bulan yang mungkin sudah terbit, dari yang terbaru.

    Bulan berjalan yang **belum** berakhir tidak ikut: berkasnya memang belum ada, dan mencoba
    tanggal yang belum lewat hanya menghasilkan permintaan yang pasti gagal.
    """
    kandidat: list[date] = []
    acuan = hari_ini
    for _ in range(bulan + 1):
        akhir = akhir_bulan(acuan)
        if akhir <= hari_ini and akhir not in kandidat:
            kandidat.append(akhir)
        acuan = acuan.replace(day=1) - timedelta(days=1)
    return tuple(kandidat)


@dataclass(frozen=True)
class BerkasMaster:
    """Isi mentah satu berkas Master File Efek beserta asalnya."""

    tanggal: date
    url: str
    isi: str


@dataclass(frozen=True)
class BarisMaster:
    """Satu saham biasa IDX sebagaimana dinyatakan berkas KSEI."""

    kode: str
    nama: str
    isin: str
    jumlah_saham: int | None
    tanggal_pencatatan: date | None
    sektor_ksei: str


@dataclass(frozen=True)
class MasterEfek:
    """Hasil urai satu berkas: yang dipakai, dan yang sengaja dibuang (beserta jumlahnya)."""

    tanggal: date
    url: str
    baris: tuple[BarisMaster, ...]
    dilewati_bukan_equity: int = 0
    dilewati_bukan_idx: int = 0
    dilewati_tidak_aktif: int = 0
    kelas_lain: tuple[tuple[str, str], ...] = ()
    kode_tak_lazim: tuple[str, ...] = ()
    baris_tersambung: tuple[tuple[int, int], ...] = ()

    @property
    def jumlah(self) -> int:
        return len(self.baris)

    def __str__(self) -> str:
        bagian = [
            f"Master File Efek KSEI {tampilan.tanggal(self.tanggal)}",
            f"  berkas    : {self.url.rsplit('/', 1)[-1]}",
            f"  saham biasa IDX aktif: {self.jumlah} kode",
        ]
        dilewati = [
            ("bukan EQUITY", self.dilewati_bukan_equity),
            ("bukan bursa IDX", self.dilewati_bukan_idx),
            ("status tidak ACTIVE", self.dilewati_tidak_aktif),
            ("kelas lain (preferen/seri)", len(self.kelas_lain)),
        ]
        for label, jumlah in dilewati:
            if jumlah:
                bagian.append(f"  dilewati — {label}: {jumlah}")
        if self.kelas_lain:
            rinci = ", ".join(f"{kode} ({alasan})" for kode, alasan in self.kelas_lain[:5])
            bagian.append(f"    {rinci}")
        if self.kode_tak_lazim:
            bagian.append(
                "  kode di luar pola 4 huruf (tetap ditulis): "
                + ", ".join(self.kode_tak_lazim[:10])
            )
        if self.baris_tersambung:
            rentang = ", ".join(f"{awal}–{akhir}" for awal, akhir in self.baris_tersambung[:5])
            bagian.append(
                f"  CATATAN: berkas sumber memuat {len(self.baris_tersambung)} catatan yang "
                f"terbelah menjadi beberapa baris fisik (baris {rentang}); disambung ulang hanya "
                "karena jumlah kolomnya kembali tepat. Bentuk aslinya tidak utuh."
            )
        return "\n".join(bagian)


@dataclass(frozen=True)
class HasilAmbil:
    """Laporan satu kali pengambilan daftar emiten."""

    jalur: Path
    master: MasterEfek
    sumber: str
    jumlah_terbaca_ulang: int

    def __str__(self) -> str:
        return "\n".join(
            [
                str(self.master),
                f"  ditulis   : {self.jalur} ({self.jumlah_terbaca_ulang} baris terbaca ulang)",
                f"  sumber    : {self.sumber}",
                "",
                "DIKOSONGKAN dengan sengaja (bukan lupa, bukan nol):",
                "  sektor_idx_ic    KSEI memakai taksonomi sendiri, bukan IDX-IC yang dipakai PRD",
                "  papan            tidak ada di berkas KSEI",
                "  jenis            keputusan analis (bank_keuangan / siklikal_komoditas / umum)",
                "  free_float       kolom Local/Foreign (%) KSEI = komposisi kepemilikan, bukan free float",
                "  status_notasi    Status ACTIVE KSEI bukan notasi khusus IDX (punya berkas sendiri)",
                "",
                "Metrik yang bergantung pada kolom kosong akan berstatus \"tidak dihitung\" (PRD 7.2),",
                "bukan diisi angka tebakan.",
            ]
        )


# ---------------------------------------------------------------------------------------
# Pengambilan berkas
# ---------------------------------------------------------------------------------------


def _buka(url: str, timeout: float):
    permintaan = urllib.request.Request(url, headers={"User-Agent": AGEN_PENGGUNA})
    return urllib.request.urlopen(permintaan, timeout=timeout)


def _urai_zip(data: bytes, url: str) -> str:
    """Buka zip KSEI dan kembalikan teksnya; berkas yang tidak seperti diharapkan ditolak."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zipnya:
            anggota = zipnya.namelist()
            if len(anggota) != 1:
                raise GalatIngesti(
                    f"{url}: berkas zip berisi {len(anggota)} berkas ({', '.join(anggota[:5])}); "
                    "bentuknya berubah dari yang dikenal. Periksa berkasnya sebelum dipakai."
                )
            mentah = zipnya.read(anggota[0])
    except zipfile.BadZipFile as galat:
        raise GalatIngesti(f"{url}: isi balasan bukan berkas zip yang sah ({galat})") from galat

    try:
        return mentah.decode("utf-8")
    except UnicodeDecodeError as galat:
        raise GalatIngesti(
            f"{url}: berkas bukan teks UTF-8 ({galat}). Penguraian dihentikan daripada menebak "
            "isi karakter yang salah."
        ) from galat


def unduh_master(
    *,
    tanggal: date | None = None,
    hari_ini: date | None = None,
    bulan: int = BULAN_DICARI,
    percobaan: int = PERCOBAAN_BAWAAN,
    jeda: float = JEDA_BAWAAN,
    timeout: float = TIMEOUT_BAWAAN,
    buka: Callable[[str, float], object] | None = None,
) -> BerkasMaster:
    """Unduh satu Master File Efek: tanggal tertentu, atau yang terbaru yang sudah terbit.

    Pencarian mundur berhenti pada berkas pertama yang **ada**. Kandidat yang gagal dicatat
    beserta alasannya, dan bila tidak satu pun berhasil, galatnya menyebutkan seluruh kandidat
    yang dicoba — bukan "gagal mengunduh" tanpa jejak.
    """
    pembuka = _buka if buka is None else buka
    kandidat = (tanggal,) if tanggal is not None else kandidat_tanggal(hari_ini or date.today(), bulan=bulan)

    catatan: list[str] = []
    for satu in kandidat:
        alamat = url_master(satu)
        galat_terakhir: str = ""
        for nomor in range(1, percobaan + 1):
            try:
                with pembuka(alamat, timeout) as balasan:  # type: ignore[union-attr]
                    data = balasan.read()
            except urllib.error.HTTPError as galat:
                galat_terakhir = f"HTTP {galat.code}"
                if galat.code == 404:
                    break  # berkas bulan itu memang tidak diterbitkan
            except (urllib.error.URLError, TimeoutError, OSError) as galat:
                galat_terakhir = f"{type(galat).__name__}: {galat}"
            else:
                return BerkasMaster(tanggal=satu, url=alamat, isi=_urai_zip(data, alamat))
            if nomor < percobaan:
                time.sleep(jeda * nomor)
        catatan.append(f"  {tampilan.tanggal(satu)} — {alamat.rsplit('/', 1)[-1]}: {galat_terakhir}")

    raise GalatIngesti(
        "tidak ada Master File Efek KSEI yang bisa diunduh. Kandidat yang dicoba:\n"
        + "\n".join(catatan)
        + "\nPeriksa koneksi jaringan, atau tunjuk berkasnya dengan --tanggal-master YYYY-MM-DD "
        "(tanggalnya menempel di nama berkas, mis. 2026-09-30)."
    )


# ---------------------------------------------------------------------------------------
# Penguraian
# ---------------------------------------------------------------------------------------


def _tanggal_ksei(teks: str, di_mana: str) -> date | None:
    """`25-NOV-1989` menjadi `date(1989, 11, 25)`; kosong berarti tidak dinyatakan."""
    isi = teks.strip()
    if not isi:
        return None
    cocok = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", isi)
    if not cocok or cocok.group(2).upper() not in BULAN_KSEI:
        raise GalatIngesti(f"{di_mana}: tanggal {isi!r} tidak dikenali (diharapkan mis. 25-NOV-1989)")
    hari, bulan, tahun = int(cocok.group(1)), BULAN_KSEI[cocok.group(2).upper()], int(cocok.group(3))
    try:
        return date(tahun, bulan, hari)
    except ValueError as galat:
        raise GalatIngesti(f"{di_mana}: tanggal {isi!r} tidak ada di kalender ({galat})") from galat


def _baris_utuh(
    baris: Sequence[tuple[int, str]], jumlah_kolom: int, di_mana: str
) -> Iterator[tuple[int, list[str], tuple[int, int] | None]]:
    """Keluarkan baris berkas beserta kolomnya, menyambung catatan yang terbelah.

    Berkas KSEI 30 Sep 2026 memuat satu catatan yang patah di tengah kolom (baris 3619–3620:
    nama efeknya terbelah menjadi dua baris fisik). Penyambungan **hanya** diterima bila jumlah
    kolomnya kembali tepat sama — itu bukti yang bisa diperiksa, bukan tebakan. Yang tetap tidak
    utuh ditolak, dan setiap penyambungan dilaporkan supaya bentuk berkas sumber yang cacat tidak
    hilang dari pandangan.
    """
    nomor_urut = 0
    while nomor_urut < len(baris):
        nomor, isi = baris[nomor_urut]
        kolom = isi.split("|")
        dipakai = 1
        sambungan: tuple[int, int] | None = None
        while kolom and len(kolom) < jumlah_kolom and dipakai <= BATAS_SAMBUNG:
            if nomor_urut + dipakai >= len(baris):
                break
            nomor_lanjut, lanjutan = baris[nomor_urut + dipakai]
            # Bila baris terputus tepat di batas kolom (`…|`), menyambungnya tanpa spasi;
            # kalau terputus di tengah isi kolom, satu spasi dikembalikan.
            pemisah = "" if isi.rstrip().endswith("|") else " "
            isi = isi.rstrip() + pemisah + lanjutan.lstrip()
            kolom = isi.split("|")
            sambungan = (nomor, nomor_lanjut)
            dipakai += 1

        if len(kolom) != jumlah_kolom:
            lewat = f" (setelah disambung dengan baris {sambungan[1]})" if sambungan else ""
            raise GalatIngesti(
                f"{di_mana} baris {nomor}{lewat}: {len(kolom)} kolom, seharusnya {jumlah_kolom}. "
                "Baris yang bentuknya berbeda tidak dilewati diam-diam."
            )
        yield nomor, kolom, sambungan
        nomor_urut += dipakai


def urai_master_efek(teks: str, *, url: str = "", di_mana: str = "Master File Efek KSEI") -> MasterEfek:
    """Urai berkas Master File Efek: ambil saham biasa IDX yang aktif, catat sisanya.

    Berkas yang kepalanya tidak memuat kolom wajib, baris yang jumlah kolomnya tidak cocok,
    kode ganda, atau nilai yang bukan angka **ditolak** — semuanya dengan menyebut barisnya.
    """
    # Nomor barisnya nomor **fisik** di berkas, supaya pesan galat bisa dicari langsung di
    # berkas aslinya; baris kosong dilewati tanpa menggeser penomoran.
    semua_baris = [
        (nomor, satu) for nomor, satu in enumerate(teks.splitlines(), start=1) if satu.strip()
    ]
    if not semua_baris:
        raise GalatIngesti(f"{di_mana}: berkas kosong, tidak ada yang bisa diurai")

    kepala = [satu.strip() for satu in semua_baris[0][1].split("|")]
    posisi = {nama: nomor for nomor, nama in enumerate(kepala)}
    hilang = [nama for nama in KOLOM_WAJIB if nama not in posisi]
    if hilang:
        raise GalatIngesti(
            f"{di_mana}: kepala berkas tidak memuat kolom {', '.join(hilang)}. "
            f"Kepala yang terbaca: {'|'.join(kepala[:12])}… Bentuk berkas sumber berubah; "
            "jangan dipakai sebelum diperiksa."
        )

    tanggal_berkas: date | None = None
    terpakai: list[BarisMaster] = []
    terlihat: dict[str, int] = {}
    ganda: list[str] = []
    tak_lazim: list[str] = []
    kelas_lain: list[tuple[str, str]] = []
    tersambung: list[tuple[int, int]] = []
    bukan_equity = bukan_idx = tidak_aktif = 0

    for nomor, sel, sambungan in _baris_utuh(semua_baris[1:], len(kepala), di_mana):
        if sambungan is not None:
            tersambung.append(sambungan)

        tanggal_baris = _tanggal_ksei(sel[posisi["Date"]], f"{di_mana} baris {nomor} kolom Date")
        if tanggal_baris is not None:
            if tanggal_berkas is None:
                tanggal_berkas = tanggal_baris
            elif tanggal_baris != tanggal_berkas:
                raise GalatIngesti(
                    f"{di_mana} baris {nomor}: kolom Date berisi {sel[posisi['Date']]!r}, "
                    f"sedangkan baris sebelumnya {tanggal_berkas.isoformat()}. Satu berkas harus "
                    "satu tanggal data; berkas campuran tidak boleh dipakai untuk point-in-time."
                )

        if sel[posisi["Type"]].strip().upper() != "EQUITY":
            bukan_equity += 1
            continue
        if sel[posisi["Stock Exchange"]].strip().upper() != "IDX":
            bukan_idx += 1
            continue
        if sel[posisi["Status"]].strip().upper() != "ACTIVE":
            tidak_aktif += 1
            continue

        kode = sel[posisi["Code"]].strip().upper()
        if not kode:
            raise GalatIngesti(f"{di_mana} baris {nomor}: kolom Code kosong")
        if kode in terlihat:
            ganda.append(kode)
        terlihat[kode] = nomor

        isin = sel[posisi["Isin Code"]].strip().upper()
        if isin.startswith("ID2"):
            kelas_lain.append((kode, "preferen/seri"))
            continue
        if not isin.startswith("ID1"):
            raise GalatIngesti(
                f"{di_mana} baris {nomor} ({kode}): ISIN {isin!r} bukan saham biasa Indonesia "
                "(ID1…) maupun kelas preferen/seri (ID2…). Kelas efek yang tidak dikenal tidak "
                "dimasukkan ke semesta tanpa diperiksa."
            )

        # Dicatat setelah penyaringan kelas: yang dilaporkan di sini adalah kode yang **benar-benar
        # masuk** semesta, bukan kode yang sudah dikeluarkan.
        if not POLA_KODE_LAZIM.match(kode):
            tak_lazim.append(kode)

        jumlah_teks = sel[posisi["Num. of Sec"]].strip()
        if jumlah_teks and not jumlah_teks.isdigit():
            raise GalatIngesti(
                f"{di_mana} baris {nomor} ({kode}): Num. of Sec berisi {jumlah_teks!r}, "
                "bukan bilangan bulat"
            )

        terpakai.append(
            BarisMaster(
                kode=kode,
                nama=sel[posisi["Description"]].strip(),
                isin=isin,
                jumlah_saham=int(jumlah_teks) if jumlah_teks else None,
                tanggal_pencatatan=_tanggal_ksei(
                    sel[posisi["Listing Date"]], f"{di_mana} baris {nomor} kolom Listing Date"
                ),
                sektor_ksei=sel[posisi["Sector"]].strip() if "Sector" in posisi else "",
            )
        )

    if ganda:
        raise GalatIngesti(
            f"{di_mana}: kode muncul lebih dari sekali ({', '.join(sorted(set(ganda))[:5])}). "
            "Daftar emiten harus satu baris per kode; yang ganda membuat semesta tidak jelas."
        )
    if not terpakai:
        raise GalatIngesti(
            f"{di_mana}: tidak ada satu pun saham biasa IDX yang aktif di berkas ini "
            f"(dilewati: {bukan_equity} bukan EQUITY, {bukan_idx} bukan IDX, {tidak_aktif} tidak "
            "ACTIVE). Menulis berkas kosong akan membuat --refresh berhenti tanpa sebab yang jelas."
        )
    if tanggal_berkas is None:
        raise GalatIngesti(f"{di_mana}: tidak ada baris yang menyatakan tanggal data (kolom Date)")

    return MasterEfek(
        tanggal=tanggal_berkas,
        url=url,
        baris=tuple(terpakai),
        dilewati_bukan_equity=bukan_equity,
        dilewati_bukan_idx=bukan_idx,
        dilewati_tidak_aktif=tidak_aktif,
        kelas_lain=tuple(kelas_lain),
        kode_tak_lazim=tuple(sorted(set(tak_lazim))),
        baris_tersambung=tuple(tersambung),
    )


# ---------------------------------------------------------------------------------------
# Penulisan emiten.csv
# ---------------------------------------------------------------------------------------


def label_sumber(master: MasterEfek, *, diakses_pada: date) -> str:
    """Label asal yang menempel di setiap baris `emiten.csv` (PRD 7.2: asal data terlihat)."""
    return (
        f"Master File Efek KSEI {tampilan.tanggal(master.tanggal)} "
        f"(StatisEfek{master.tanggal.strftime('%Y%m%d')}.txt.zip), diakses {tampilan.tanggal(diakses_pada)}"
    )


def _komentar(master: MasterEfek, sumber: str, dicatat_pada: date) -> Iterator[str]:
    """Penjelasan yang ikut tertulis di berkas, supaya kolom kosong tidak disalahartikan."""
    yield "# " + "=" * 87
    yield f"# DAFTAR EMITEN DARI MASTER FILE EFEK KSEI — {tampilan.tanggal(master.tanggal)}"
    yield "# " + "=" * 87
    yield "#"
    yield f"# Sumber : {sumber}"
    yield f"# Ditulis: {tampilan.tanggal(dicatat_pada)} oleh `python -m mejasaham --ambil-emiten`"
    yield "#"
    yield "# Kolom yang DIISI dari berkas sumber: kode, nama, jumlah_saham (kolom `Num. of Sec`),"
    yield "# dan tanggal_notasi (kolom `Listing Date` = tanggal pencatatan sahamnya)."
    yield "#"
    yield "#   tanggal_notasi  nama kolomnya mengikuti tabel `emiten` di PRD 12 (tabel 23), dan PRD"
    yield "#                   tidak menjelaskan arti nama itu. Isinya di sini adalah `Listing Date`"
    yield "#                   KSEI apa adanya. Pemetaan ini dicatat sebagai pertanyaan P18 di"
    yield "#                   docs/keputusan.md — koreksi bila PRD Anda memaksudkan hal lain."
    yield "#                   Kosong bila sumber tidak menyatakannya (87 dari 975 pada berkas"
    yield "#                   30 Sep 2026); tidak diisi tanggal tebakan."
    yield "#"
    yield "# Kolom yang SENGAJA DIKOSONGKAN — bukan lupa, dan bukan nol:"
    yield "#   sektor_idx_ic   KSEI memakai taksonomi sendiri (mis. COMPUTER AND SERVICES), bukan"
    yield "#                   IDX-IC yang dipakai PRD. Pemetaan resmi tidak ada; mengarang pemetaan"
    yield "#                   akan membuat statistik sektor salah tanpa terlihat salah."
    yield "#   sektor_sumber   sektor menurut sumber DATA EOD (diisi oleh --ambil-jenis, K25), bukan"
    yield "#                   dari berkas KSEI ini. Dua kolom sektor itu berbeda dan tidak boleh"
    yield "#                   diisi dengan nilai yang sama."
    yield "#   papan           tidak ada di berkas KSEI."
    yield "#   jenis           bank_keuangan / siklikal_komoditas / umum adalah keputusan analis."
    yield "#   free_float      kolom Local/Foreign (%) KSEI = komposisi kepemilikan, bukan free float."
    yield "#                   Dua hal berbeda; menukarnya membuat metrik salah tanpa terlihat salah."
    yield "#   status_notasi   Status ACTIVE KSEI berarti aktif tercatat, BUKAN notasi khusus IDX."
    yield "#                   Notasi khusus masuk lewat notasi-khusus.csv."
    yield "#"
    yield "# Saham preferen/seri (ISIN ID2…) tidak ikut: bukan saham biasa, dan bukan kelas yang"
    yield "# diperdagangkan di pasar yang sama."
    yield "#"
    yield "# Metrik yang bergantung pada kolom kosong berstatus \"tidak dihitung\" (PRD 7.2), bukan"
    yield "# diisi angka tebakan. Isi kolom itu sendiri bila Anda punya sumber resminya."
    yield "#"
    yield "# Aturan format: lihat mejasaham/defaults/emiten.contoh.csv"
    yield "# " + "=" * 87


def tulis_emiten_csv(
    master: MasterEfek, jalur: Path, *, sumber: str, dicatat_pada: date
) -> int:
    """Tulis `emiten.csv`; kembalikan jumlah baris data yang ditulis.

    Baris kepala ditulis **pertama** (sebelum penjelasan), mengikuti template bawaan: pembaca
    berkas mendeteksi pemisah kolom dari baris pertama, jadi penjelasan yang mendahuluinya akan
    membuat berkas ini terbaca sebagai berkas berpemisah koma.
    """
    with jalur.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
        penulis = csv.writer(berkas_tulis, delimiter=";", lineterminator="\n")
        penulis.writerow(KEPALA_CSV)
        for satu in _komentar(master, sumber, dicatat_pada):
            berkas_tulis.write(satu + "\n")
        for baris in master.baris:
            penulis.writerow(
                [
                    baris.kode,
                    baris.nama,
                    "",  # sektor_idx_ic  — taksonomi berbeda, lihat penjelasan di atas
                    "",  # sektor_sumber  — diisi --ambil-jenis dari sumber data (K25)
                    "",  # jenis
                    "",  # papan
                    "",  # status_notasi
                    "" if baris.tanggal_pencatatan is None else baris.tanggal_pencatatan.isoformat(),
                    "" if baris.jumlah_saham is None else str(baris.jumlah_saham),
                    "",  # free_float_persen
                    sumber,
                    dicatat_pada.isoformat(),
                ]
            )
    return master.jumlah


def ambil_emiten(
    folder: Path,
    *,
    tanggal: date | None = None,
    timpa: bool = False,
    hari_ini: date | None = None,
    bulan: int = BULAN_DICARI,
    percobaan: int = PERCOBAAN_BAWAAN,
    jeda: float = JEDA_BAWAAN,
    timeout: float = TIMEOUT_BAWAAN,
    buka: Callable[[str, float], object] | None = None,
) -> HasilAmbil:
    """Unduh, urai, tulis `folder/emiten.csv`, lalu **baca ulang** sebagai bukti.

    Berkas yang sudah ada tidak ditimpa tanpa `timpa`: berkas itu berisi semesta yang dipilih
    pengguna, dan bisa saja sudah disunting (sektor, jenis, papan diisi dari sumber lain).
    """
    tujuan = folder / NAMA_BERKAS_EMITEN
    if tujuan.exists() and not timpa:
        raise GalatIngesti(
            f"'{tujuan}' sudah ada. Berkas itu berisi daftar emiten Anda sendiri; "
            "pakai --timpa-emiten bila memang ingin menggantinya dengan daftar KSEI."
        )

    hari = hari_ini or date.today()
    berkas_master = unduh_master(
        tanggal=tanggal,
        hari_ini=hari,
        bulan=bulan,
        percobaan=percobaan,
        jeda=jeda,
        timeout=timeout,
        buka=buka,
    )
    master = urai_master_efek(berkas_master.isi, url=berkas_master.url, di_mana=berkas_master.url)
    sumber = label_sumber(master, diakses_pada=hari)

    lokasi.pastikan_folder(folder)
    try:
        jumlah = tulis_emiten_csv(master, tujuan, sumber=sumber, dicatat_pada=hari)
    except OSError as galat:
        raise GalatIngesti(f"gagal menulis '{tujuan}': {galat}") from galat

    # Bukti, bukan klaim: berkas dibaca ulang oleh pembaca yang sama dengan yang dipakai
    # --refresh. Kalau bentuknya tidak terbaca, lebih baik gagal di sini.
    terbaca = baca_emiten(folder)
    if len(terbaca) != jumlah:
        raise GalatIngesti(
            f"'{tujuan}' ditulis {jumlah} baris tetapi terbaca ulang {len(terbaca)} baris. "
            "Berkasnya tidak boleh dipakai sebelum diperiksa."
        )
    return HasilAmbil(jalur=tujuan, master=master, sumber=sumber, jumlah_terbaca_ulang=len(terbaca))
