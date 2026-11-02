"""Kandidat & watchlist (F4, PRD 9.6) — tesis wajib sebelum berstatus watchlist (AC-4).

Alasan modul ini ada, apa adanya dari PRD: nilai produk ini bukan skornya, melainkan **proses
yang dipaksa terjadi sebelum order** (PRD 2.3). Tiga hal yang ditegakkan di sini:

1. **Tanpa kolom wajib, entri tidak bisa disimpan** (PRD 9.6, AC-4). Tesis, pembatal fundamental,
   horizon, stop awal, dan tanggal tinjau diperiksa modul ini — dan dijaga `CHECK` di tabel
   `kandidat`, supaya aturannya berlaku pada penulisan mana pun, bukan hanya lewat jalur ini.
2. **Tidak ada penghapusan senyap.** Perubahan status/tesis menambah **revisi baru**; revisi lama
   tetap ada dan bisa dibaca (PRD 9.8). Tesis adalah isi basis data yang tidak bisa dibangun ulang
   dari sumber mana pun (PRD 9.12), jadi menghilangkannya tidak bisa diperbaiki belakangan.
3. **Status berbeda dari "kandidat hari ini".** PRD 9.6 menegaskan: "kandidat hari ini" di dasbor
   hanyalah hasil saringan berskor tinggi, **bukan** status. Karena itu status yang sah hanya
   lima (`ide`, `watchlist`, `rencana`, `posisi`, `dibuang`) dan tidak ada status "kandidat".

**Asumsi yang dinyatakan terbuka (P23 di `docs/keputusan.md` bagian 3):** `tanggal_tinjau` dibaca
sebagai **tanggal tinjau berikutnya** — sesuai keluaran F4 yang menyebut "tanggal tinjau
berikutnya" — sehingga entri disebut **kedaluwarsa ketika tanggal itu sudah lewat**, bukan ketika
"30 hari sejak terakhir dilihat". Angka 30 hari (PRD 9.6, 13.1) dipakai sebagai **saran** jarak
tinjauan (`saran_tanggal_tinjau`), bukan untuk menuduh entri yang baru dibuat. Kalau pengguna
memilih tafsir yang lain, yang berubah hanya fungsi `kedaluwarsa`, bukan bentuk tabelnya.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from mejasaham import db

#: Status yang sah (PRD 9.6, 12). Tidak ada status "kandidat": itu hasil saringan, bukan keadaan.
STATUS_SAH = ("ide", "watchlist", "rencana", "posisi", "dibuang")

#: Jarak tinjauan yang disarankan (PRD 9.6, 13.1: "ditinjau ulang tiap 30 hari").
BATAS_TINJAU_HARI = 30

#: Kolom wajib sebelum berstatus watchlist (PRD 9.6, AC-4): nama kolom → sebutan untuk manusia.
KOLOM_WAJIB_WATCHLIST: tuple[tuple[str, str], ...] = (
    ("tesis", "alasan masuk (tesis)"),
    ("pembatal_fundamental", "pembatal fundamental (kondisi terukur)"),
    ("horizon", "horizon"),
    ("stop_awal", "stop awal indikatif"),
    ("tanggal_tinjau", "tanggal tinjau"),
)

#: Perpindahan status yang diizinkan (PRD 9.6: ide → watchlist → rencana → posisi).
#: `dibuang` boleh dari mana saja dan bersifat **final** — entri yang sudah dibuang tidak
#: dihidupkan lagi; membuat entri baru lebih jujur daripada menuliskan ulang yang lama.
PERPINDAHAN_SAH: Mapping[str, tuple[str, ...]] = {
    "ide": ("watchlist", "dibuang"),
    "watchlist": ("rencana", "dibuang"),
    "rencana": ("posisi", "dibuang"),
    "posisi": (),
    "dibuang": (),
}

#: Kolom yang boleh diubah lewat `ubah()`. `id_kandidat`, `revisi`, dan `dicatat_pada` bukan
#: isian manusia: ketiganya ditentukan modul ini.
KOLOM_DAPAT_DIUBAH = (
    "kode",
    "status",
    "tesis",
    "pembatal_fundamental",
    "harga_pembatal",
    "horizon",
    "target",
    "stop_awal",
    "tanggal_tinjau",
    "alasan_dibuang",
)

_KOLOM_TABEL = ("id_kandidat", "revisi") + KOLOM_DAPAT_DIUBAH + ("dicatat_pada",)


class GalatKandidat(RuntimeError):
    """Kesalahan yang pesannya sudah ditujukan untuk pengguna, bukan traceback (aturan keras 7)."""


@dataclass(frozen=True)
class Kandidat:
    """Satu revisi entri kandidat. Revisi terakhir = keadaan sekarang."""

    id_kandidat: int
    revisi: int
    kode: str
    status: str
    tesis: str | None
    pembatal_fundamental: str | None
    harga_pembatal: int | None
    horizon: str | None
    target: int | None
    stop_awal: int | None
    tanggal_tinjau: str | None
    alasan_dibuang: str | None
    dicatat_pada: str

    @property
    def punya_tesis(self) -> bool:
        return bool(self.tesis and self.tesis.strip())

    def terlambat_hari(self, hari_ini: date | None = None) -> int:
        """Berapa hari tinjauannya sudah lewat. 0 atau kurang berarti belum jatuh tempo."""
        if self.tanggal_tinjau is None:
            return 0
        sekarang = hari_ini or date.today()
        return (sekarang - date.fromisoformat(self.tanggal_tinjau)).days

    def kedaluwarsa(self, hari_ini: date | None = None) -> bool:
        """True bila tanggal tinjau berikutnya sudah lewat (PRD 9.6; tafsirnya di docstring modul)."""
        if self.status in ("ide", "dibuang") or not self.punya_tesis:
            return False
        return self.terlambat_hari(hari_ini) > 0

    def ringkas(self, hari_ini: date | None = None) -> str:
        """Satu baris untuk keluaran terminal. Angka ditulis apa adanya, bukan diformat di sini."""
        bagian = [f"#{self.id_kandidat} r{self.revisi}", self.kode, self.status]
        if self.stop_awal is not None:
            bagian.append(f"stop {self.stop_awal}")
        if self.harga_pembatal is not None:
            bagian.append(f"pembatal {self.harga_pembatal}")
        if self.tanggal_tinjau:
            bagian.append(f"tinjau {self.tanggal_tinjau}")
        if self.kedaluwarsa(hari_ini):
            bagian.append(f"KEDALUWARSA (+{self.terlambat_hari(hari_ini)} hari)")
        teks = " · ".join(bagian)
        if self.status == "dibuang" and self.alasan_dibuang:
            teks += f"\n      alasan dibuang: {self.alasan_dibuang}"
        elif self.tesis:
            teks += f"\n      tesis: {self.tesis}"
        return teks


def saran_tanggal_tinjau(hari_ini: date | None = None, *, hari: int = BATAS_TINJAU_HARI) -> str:
    """Tanggal tinjau yang disarankan (hari ini + 30 hari) — saran, bukan bawaan paksa.

    Sengaja hanya saran: mengisi otomatis akan membuat kolom wajib AC-4 terisi tanpa pengguna
    benar-benar memilih, dan tanggal tinjau yang tidak dipilih tidak akan pernah ditinjau.
    """
    return ((hari_ini or date.today()) + timedelta(days=hari)).isoformat()


# ---------------------------------------------------------------------------------------
# Pemeriksaan
# ---------------------------------------------------------------------------------------


def _periksa_status(status: str) -> None:
    if status not in STATUS_SAH:
        raise GalatKandidat(
            f"status {status!r} tidak dikenal. Yang sah: {', '.join(STATUS_SAH)}. "
            "Catatan: \"kandidat\" bukan status (PRD 9.6) — itu hasil saringan berskor tinggi."
        )


def _periksa_kelengkapan(status: str, nilai: Mapping[str, object]) -> None:
    """AC-4: kolom wajib sebelum watchlist. Diperiksa di sini agar pesannya menyebut kolomnya."""
    if status == "dibuang":
        # Dibuang justru sering terjadi **karena** tesisnya tidak pernah lengkap. Yang dituntut
        # hanya alasannya (PRD 9.6) — kalau kelengkapan ikut dituntut, pembuangan yang jujur
        # menjadi mustahil dan entri tanpa tesis akan menumpuk selamanya di daftar.
        if not str(nilai.get("alasan_dibuang") or "").strip():
            raise GalatKandidat("status 'dibuang' menuntut alasan (PRD 9.6): isi --alasan")
        return
    if status == "ide":
        return
    kosong = [
        sebutan
        for kolom, sebutan in KOLOM_WAJIB_WATCHLIST
        if nilai.get(kolom) is None
        or (isinstance(nilai.get(kolom), str) and not str(nilai[kolom]).strip())
    ]
    if kosong:
        raise GalatKandidat(
            f"status {status!r} menuntut kolom wajib yang belum terisi: {', '.join(kosong)} "
            "(PRD 9.6, AC-4). Entri tanpa kolom itu tidak bisa disimpan — dibuat sebagai "
            "status 'ide' bila memang belum lengkap."
        )


def _periksa_kode_dikenal(sambungan: sqlite3.Connection, kode: str) -> None:
    """Kode harus ada di daftar emiten. Salah ketik adalah cara termudah merusak watchlist.

    Diperiksa ke `v_emiten_terkini` (revisi terakhir), bukan ke tabel mentah: revisi lama yang
    sudah digantikan tidak boleh membuat kode yang sudah tidak ada tetap lolos.
    """
    baris = sambungan.execute(
        "SELECT 1 FROM v_emiten_terkini WHERE kode = ?", (kode,)
    ).fetchone()
    if baris is None:
        raise GalatKandidat(
            f"kode {kode!r} tidak ada di daftar emiten. Jalankan --refresh atau --impor lebih "
            "dulu, atau periksa ejaannya — kode yang salah ketik akan lolos diam-diam kalau "
            "tidak diperiksa."
        )


def _periksa_perpindahan(lama: str, baru: str) -> None:
    if baru == lama:
        return
    if baru not in PERPINDAHAN_SAH[lama]:
        boleh = PERPINDAHAN_SAH[lama]
        raise GalatKandidat(
            f"perpindahan status {lama!r} → {baru!r} tidak diizinkan (PRD 9.6). "
            + (f"Dari {lama!r} hanya boleh: {', '.join(boleh)}." if boleh else
               f"Status {lama!r} bersifat final.")
            + " Menghidupkan entri yang sudah dibuang dilakukan dengan membuat entri baru, "
            "bukan dengan menuliskan ulang yang lama."
        )


# ---------------------------------------------------------------------------------------
# Baca
# ---------------------------------------------------------------------------------------


def _ke_kandidat(baris: sqlite3.Row) -> Kandidat:
    return Kandidat(**{kolom: baris[kolom] for kolom in _KOLOM_TABEL})


def terkini(sambungan: sqlite3.Connection, id_kandidat: int) -> Kandidat | None:
    baris = sambungan.execute(
        "SELECT * FROM v_kandidat_terkini WHERE id_kandidat = ?", (id_kandidat,)
    ).fetchone()
    return None if baris is None else _ke_kandidat(baris)


def wajib_ada(sambungan: sqlite3.Connection, id_kandidat: int) -> Kandidat:
    kandidat = terkini(sambungan, id_kandidat)
    if kandidat is None:
        raise GalatKandidat(f"kandidat #{id_kandidat} tidak ada di basis data")
    return kandidat


def daftar(
    sambungan: sqlite3.Connection,
    status: str | Sequence[str] | None = None,
    *,
    kode: str | None = None,
) -> tuple[Kandidat, ...]:
    """Entri pada revisi terakhirnya, urut `id_kandidat` (urut dibuat)."""
    kueri = "SELECT * FROM v_kandidat_terkini"
    syarat: list[str] = []
    nilai: list[object] = []
    if status is not None:
        satu_status = (status,) if isinstance(status, str) else tuple(status)
        if not satu_status:
            return ()
        syarat.append(f"status IN ({', '.join('?' for _ in satu_status)})")
        nilai.extend(satu_status)
    if kode is not None:
        syarat.append("kode = ?")
        nilai.append(kode.strip().upper())
    if syarat:
        kueri += " WHERE " + " AND ".join(syarat)
    kueri += " ORDER BY id_kandidat"
    return tuple(_ke_kandidat(baris) for baris in sambungan.execute(kueri, nilai).fetchall())


def riwayat(sambungan: sqlite3.Connection, id_kandidat: int) -> tuple[Kandidat, ...]:
    """Seluruh revisi satu entri, terlama lebih dulu — bukti "tidak ada penghapusan senyap"."""
    baris = sambungan.execute(
        "SELECT * FROM kandidat WHERE id_kandidat = ? ORDER BY revisi", (id_kandidat,)
    ).fetchall()
    return tuple(_ke_kandidat(satu) for satu in baris)


def untuk_rencana(
    sambungan: sqlite3.Connection, kode: str, id_kandidat: int | None = None
) -> Kandidat:
    """Kandidat yang mendasari sebuah rencana: harus ada dan berstatus watchlist/rencana.

    Dipanggil sebelum kalkulator risiko berjalan, dan itu disengaja: PRD 9.6 menetapkan urutan
    ide → watchlist → rencana, sehingga rencana tanpa tesis bukan "rencana", melainkan ukuran
    posisi tanpa alasan. Menghitungnya lebih dulu lalu menolak menyimpannya membuang kerja
    pengguna tanpa sebab yang terlihat.

    Aturan ini tinggal di sini — bukan di `cli.py` — karena panel jendela (PRD 11.4) memakai
    kalkulator yang sama. Dua salinan aturan akan berbeda begitu salah satunya disunting, dan
    yang berbeda adalah tesis mana yang menempel pada sebuah posisi. Yang **tidak** boleh
    dilakukan salah satunya: memilih entri pertama diam-diam ketika kodenya punya beberapa
    entri, atau menerima entri berstatus `ide`/`dibuang`.
    """
    kode = kode.strip().upper()
    if id_kandidat is not None:
        entri = wajib_ada(sambungan, id_kandidat)
        if entri.kode != kode:
            raise GalatKandidat(f"kandidat #{id_kandidat} adalah {entri.kode}, bukan {kode}")
        calon = [entri]
    else:
        calon = [
            satu
            for satu in daftar(sambungan)
            if satu.kode == kode and satu.status in ("watchlist", "rencana")
        ]
    if not calon:
        raise GalatKandidat(
            f"tidak ada kandidat berstatus watchlist untuk {kode}. Kalkulator risiko adalah pintu "
            "menuju status 'rencana' (PRD 9.6), jadi tesisnya harus lebih dulu lengkap: "
            f"python -m mejasaham --kandidat-ubah <ID> --jadi watchlist --tesis \"...\" "
            f"--pembatal \"...\" --horizon \"...\" --stop-awal <harga> --tinjau <tanggal>"
        )
    if len(calon) > 1:
        daftar_id = ", ".join(f"#{satu.id_kandidat} ({satu.status})" for satu in calon)
        raise GalatKandidat(
            f"{kode} punya {len(calon)} entri kandidat: {daftar_id}. Sebutkan yang dipakai lewat "
            "--kandidat ID — memilih yang pertama diam-diam akan menempelkan rencananya pada "
            "tesis yang mungkin bukan tesisnya."
        )
    return calon[0]


# ---------------------------------------------------------------------------------------
# Tulis
# ---------------------------------------------------------------------------------------


def _nilai_bersih(nilai: Mapping[str, object]) -> dict[str, object]:
    """Buang spasi di tepi teks, dan samakan None/"" menjadi None supaya CHECK tidak tertipu."""
    bersih: dict[str, object] = {}
    for kolom, isi in nilai.items():
        if isinstance(isi, str):
            isi = isi.strip()
            if isi == "":
                isi = None
        bersih[kolom] = isi
    return bersih


def _sisip(sambungan: sqlite3.Connection, nilai: Mapping[str, object], *, dicatat_pada: str | None) -> None:
    kolom = [*nilai.keys(), "dicatat_pada"]
    tanda = ", ".join("?" for _ in kolom)
    with db.tulis(sambungan):
        sambungan.execute(
            f"INSERT INTO kandidat ({', '.join(kolom)}) VALUES ({tanda})",
            [*nilai.values(), dicatat_pada or db.waktu_iso()],
        )


def buat(
    sambungan: sqlite3.Connection,
    kode: str,
    *,
    status: str = "ide",
    tesis: str | None = None,
    pembatal_fundamental: str | None = None,
    harga_pembatal: int | None = None,
    horizon: str | None = None,
    target: int | None = None,
    stop_awal: int | None = None,
    tanggal_tinjau: str | None = None,
    dicatat_pada: str | None = None,
) -> Kandidat:
    """Buat entri kandidat baru (revisi 1).

    Status bawaan `ide` — entri yang belum lengkap tetap boleh **dicatat** sebagai ide, tetapi
    tidak boleh masuk watchlist (PRD 9.6, AC-4). Justru itu gunanya: ide yang belum punya tesis
    tidak hilang, dan tidak bisa menyamar sebagai keputusan.
    """
    _periksa_status(status)
    kode = kode.strip().upper()
    if status == "dibuang":
        raise GalatKandidat(
            "entri baru tidak bisa langsung berstatus 'dibuang' — buat dulu entrinya, lalu "
            "pindahkan statusnya beserta alasannya"
        )
    nilai = _nilai_bersih(
        {
            "kode": kode,
            "status": status,
            "tesis": tesis,
            "pembatal_fundamental": pembatal_fundamental,
            "harga_pembatal": harga_pembatal,
            "horizon": horizon,
            "target": target,
            "stop_awal": stop_awal,
            "tanggal_tinjau": tanggal_tinjau,
            "alasan_dibuang": None,
        }
    )
    _periksa_kelengkapan(status, nilai)
    _periksa_kode_dikenal(sambungan, kode)

    berikutnya = int(
        sambungan.execute("SELECT COALESCE(MAX(id_kandidat), 0) + 1 FROM kandidat").fetchone()[0]
    )
    _sisip(sambungan, {"id_kandidat": berikutnya, "revisi": 1, **nilai}, dicatat_pada=dicatat_pada)
    return wajib_ada(sambungan, berikutnya)


def ubah(
    sambungan: sqlite3.Connection,
    id_kandidat: int,
    perubahan: Mapping[str, object] | None = None,
    *,
    dicatat_pada: str | None = None,
) -> Kandidat:
    """Ubah entri dengan **menambah revisi**, bukan menimpa (PRD 9.8).

    Perubahan yang tidak mengubah apa pun ditolak: menambah revisi kosong membuat riwayatnya
    sulit dibaca, dan riwayat itu justru yang dipakai menilai kepatuhan.
    """
    return _ubah(
        sambungan,
        id_kandidat,
        perubahan,
        dicatat_pada=dicatat_pada,
        izinkan_tanpa_perubahan=False,
    )


def _ubah(
    sambungan: sqlite3.Connection,
    id_kandidat: int,
    perubahan: Mapping[str, object] | None,
    *,
    dicatat_pada: str | None,
    izinkan_tanpa_perubahan: bool,
) -> Kandidat:
    lama = wajib_ada(sambungan, id_kandidat)
    if lama.status == "dibuang":
        raise GalatKandidat(
            f"kandidat #{id_kandidat} sudah dibuang dan bersifat final. Buat entri baru bila "
            "idenya muncul lagi — perubahan setelah pembuangan akan menghapus alasan pembuangannya"
        )

    perubahan = _nilai_bersih(perubahan or {})
    tak_dikenal = sorted(set(perubahan) - set(KOLOM_DAPAT_DIUBAH))
    if tak_dikenal:
        raise GalatKandidat(
            f"kolom tidak dikenal: {', '.join(tak_dikenal)}. Yang bisa diubah: "
            f"{', '.join(KOLOM_DAPAT_DIUBAH)}"
        )

    baru = {kolom: perubahan.get(kolom, getattr(lama, kolom)) for kolom in KOLOM_DAPAT_DIUBAH}
    if baru["kode"] != lama.kode:
        raise GalatKandidat(
            "kode tidak bisa diubah setelah entri dibuat — kode yang berpindah akan membuat "
            "riwayat tesis menempel pada emiten yang salah. Buat entri baru."
        )
    baru["kode"] = lama.kode

    _periksa_status(str(baru["status"]))
    _periksa_perpindahan(lama.status, str(baru["status"]))
    _periksa_kelengkapan(str(baru["status"]), baru)

    beda = [
        kolom for kolom in KOLOM_DAPAT_DIUBAH if getattr(lama, kolom) != baru[kolom]
    ]
    if not beda and not izinkan_tanpa_perubahan:
        raise GalatKandidat(
            f"tidak ada yang berubah pada kandidat #{id_kandidat}; revisi tidak ditambah"
        )

    _sisip(
        sambungan,
        {"id_kandidat": id_kandidat, "revisi": lama.revisi + 1, **baru},
        dicatat_pada=dicatat_pada,
    )
    return wajib_ada(sambungan, id_kandidat)


def tinjau(
    sambungan: sqlite3.Connection,
    id_kandidat: int,
    tanggal_tinjau: str | None = None,
    *,
    hari_ini: date | None = None,
    dicatat_pada: str | None = None,
) -> Kandidat:
    """Catat **peristiwa** tinjauan: tanggal tinjau berikutnya diperbarui.

    Berbeda dari `ubah()`, revisinya tetap ditulis walaupun tanggal barunya kebetulan sama dengan
    yang lama — dan itu memang terjadi setiap kali tinjauan dilakukan tepat waktu (saran 30 hari
    menghasilkan tanggal yang sama bila tinjauan sebelumnya juga memakai saran). Yang dicatat di
    sini adalah "entri ini ditinjau hari ini", dan cakupan tinjauan PRD 13.1 dihitung dari
    peristiwa itu, bukan dari tanggal yang kebetulan tidak berubah.
    """
    return _ubah(
        sambungan,
        id_kandidat,
        {"tanggal_tinjau": tanggal_tinjau or saran_tanggal_tinjau(hari_ini)},
        dicatat_pada=dicatat_pada,
        izinkan_tanpa_perubahan=True,
    )


def ringkas_daftar(daftar_kandidat: Iterable[Kandidat], hari_ini: date | None = None) -> str:
    """Keluaran untuk terminal: satu baris per entri, kedaluwarsa ditandai mencolok."""
    isi = list(daftar_kandidat)
    if not isi:
        return "(belum ada entri kandidat)"
    baris = [satu.ringkas(hari_ini) for satu in isi]
    jumlah_kedaluwarsa = sum(1 for satu in isi if satu.kedaluwarsa(hari_ini))
    if jumlah_kedaluwarsa:
        baris.append(f"  {jumlah_kedaluwarsa} entri kedaluwarsa — tinjau ulang (PRD 9.6).")
    return "\n".join(baris)
