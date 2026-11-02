"""Memuat **satu snapshot** ke memori sebagai bahan perhitungan (A4, S3, aturan keras 3).

Aturan yang membuat berkas ini ada, dan bukan sekadar "ambil semua baris":

* **Point-in-time, bukan "yang terbaru".** Tampilan `v_<tabel>_terkini` menyajikan revisi
  terakhir yang **ada di basis data hari ini** — termasuk koreksi yang dicatat setelah snapshot
  dibuat. Memakainya untuk menghitung snapshot lama berarti menghitung dengan hal yang belum
  diketahui saat itu. Karena itu setiap kueri di sini menyaring `diketahui_pada <= batas
  snapshot` **dan** memilih revisi terakhir yang memenuhi syarat itu.
* **Fundamental sejak tanggal publikasinya** (aturan keras 3, AC-15). Penyaringan tanggalnya
  dilakukan di sini, sekali, supaya tidak ada modul hilir yang bisa lupa melakukannya.
* **Satu snapshot, satu angka.** Semua layar memakai `Potret` yang sama (PRD 5), sehingga tidak
  mungkin ada dua tabel yang menampilkan dua tanggal data berbeda tanpa disadari.
* **Satu snapshot, satu label sumber harga** (P17). Harga pembanding (PRD 7.3) hidup di tabel
  yang sama dengan harga utama, jadi membacanya tanpa menyaring label akan mencampur dua sumber
  ke dalam satu deret. Aturannya ada di `riwayat_sumber`, hasilnya disimpan di
  `Potret.sumber_harga`, dan label yang tidak dipakai tetap terlihat di `Potret.sumber_tersedia`.
  Pengecualiannya satu, dan tetap satu deret per tanggal: **sambungan harga resmi** (K97) —
  label resmi sejak tanggal sambung, label riwayat sebelumnya (`harga_dipakai`).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from mejasaham.ingesti import (
    AksiKorporasi,
    Emiten,
    Fundamental,
    GalatIngesti,
    HargaHarian,
    ImbalHasilSUN,
    NotasiKhusus,
    PenutupanIndeks,
    RasioBank,
)

#: Kunci alami per tabel data; dipakai menyusun kueri "revisi terakhir per kunci, pada saat itu".
#:
#: `harga_harian` berkunci `kode + tanggal + sumber`, mengikuti migrasi 005: sejak harga
#: pembanding diimpor untuk cek sumber kedua (PRD 7.3), satu `(kode, tanggal)` yang sama punya
#: dua baris yang sah. Tanpa `sumber` di kunci ini, membaca snapshot akan memilih salah satunya
#: secara acak relatif urutan baris — dan itu membuat hasil perhitungan tidak lagi deterministik
#: (A5), bukan sekadar salah.
KUNCI_ALAMI: Mapping[str, tuple[str, ...]] = {
    "emiten": ("kode",),
    "harga_harian": ("kode", "tanggal", "sumber"),
    "harga_indeks": ("indeks", "tanggal"),
    "aksi_korporasi": ("kode", "tanggal", "jenis"),
    "notasi_khusus": ("kode", "jenis", "tanggal_mulai"),
    "imbal_hasil_sun": ("tanggal", "tenor_tahun"),
    "fundamental": ("kode", "periode", "jenis_laporan"),
    "rasio_bank": ("kode", "periode"),
    "kalender_bursa": ("tanggal",),
}


# Aturan pemilihan label sumber harga yang dipakai berhitung (P17).
#
# Sejak migrasi 005 harga pembanding untuk cek sumber kedua (PRD 7.3) hidup di tabel yang sama
# dengan harga utama, sehingga satu `(kode, tanggal)` bisa punya dua baris yang sah. Membaca
# keduanya sebagai **satu** deret bukan "lebih banyak data", melainkan rusak diam-diam:
# `penyesuaian.sesuaikan` mengurutkan bar berdasarkan tanggal saja, jadi hari yang terduplikasi
# memakan satu slot jendela 20 hari dan ADTV20 emiten itu jatuh menjadi "tidak dihitung".
# Terukur 9 Okt 2026 pada salinan basis data uji: semesta likuid 235 → 215, tepat pada emiten
# yang diberi pembanding — dan yang hilang justru emiten paling likuid.
#
# Yang dipakai: **satu label untuk seluruh snapshot**, yaitu label dengan riwayat bar terbanyak
# (seri diputus menurut abjad, supaya jawabannya deterministik dan bukan urutan baris). Label
# per emiten sengaja **tidak** dipakai: dua emiten di peringkat yang sama akan dihitung dari
# sumber berbeda tanpa satu pun tanda di layar, dan itu membuat peringkatnya bukan peringkat
# sumber mana pun.
#
# Pilihan ini **selalu dilaporkan** (`Potret.sumber_harga` + `Potret.sumber_diabaikan`) dan bisa
# ditimpa pemanggil lewat `--sumber`. Aturan yang sama sudah dipakai `pengatur.cek_sumber_kedua`
# sejak langkah 3; sejak langkah 9 keduanya memanggil fungsi di bawah ini supaya tidak ada dua
# jawaban untuk satu pertanyaan.
#
# **Yang belum diputuskan manusia:** P17 di `docs/keputusan.md` bagian 3 (usulan (a) dipakai
# sementara; alternatifnya "pengguna memilih sumber utama per snapshot").


def riwayat_sumber(
    sambungan: sqlite3.Connection, *, batas: str | None = None
) -> tuple[tuple[str, int], ...]:
    """(label sumber, jumlah bar) tiap label, terbanyak lebih dulu; seri menurut abjad.

    `batas` (`diketahui_pada`) membuat pilihan ini ikut point-in-time: label yang baru muncul
    **sesudah** snapshot dibuat tidak boleh mengubah isi snapshot itu. Tanpa `batas`, seluruh
    baris yang ada hari ini yang dihitung — itu yang dipakai pemeriksaan keadaan sekarang
    (mis. cek sumber kedua).

    Label kosong (`''` = baris yang tidak menyatakan sumbernya) tidak ikut: ia bukan label,
    melainkan ketiadaan keterangan.
    """
    syarat = "" if batas is None else " AND diketahui_pada <= ?"
    argumen: tuple[object, ...] = () if batas is None else (batas,)
    baris = sambungan.execute(
        "SELECT sumber, COUNT(*) AS jumlah FROM harga_harian WHERE sumber <> ''"
        + syarat
        + " GROUP BY sumber ORDER BY jumlah DESC, sumber ASC",
        argumen,
    ).fetchall()
    return tuple((satu["sumber"], int(satu["jumlah"])) for satu in baris)


def sumber_utama(sambungan: sqlite3.Connection, *, batas: str | None = None) -> str | None:
    """Label dengan riwayat bar terbanyak (K14); `None` bila belum ada bar harga sama sekali.

    Ini **bukan** jawaban "deret mana yang dipakai berhitung" begitu sambungan harga (K97)
    berlaku — untuk itu pakai `harga_dipakai`.
    """
    riwayat = riwayat_sumber(sambungan, batas=batas)
    return riwayat[0][0] if riwayat else None


# Deret sambungan (K97, P42): sejak `sejak`, bar dibaca dari label resmi (Ringkasan Saham IDX
# unggahan pengguna); sebelumnya dari label riwayat (K14). Satu tanggal untuk seluruh emiten,
# jadi dua emiten pada tanggal yang sama selalu dihitung dari sumber yang sama — alasan K14
# menolak label per emiten tetap terpenuhi. Hari tanpa bar resmi sesudah `sejak` dibiarkan
# bolong, **tidak** diisi dari label riwayat (K97 d).
#
# Seluruh penyaring harga di modul lain memakai `PilihanHarga.syarat`, bukan `sumber = ?`
# sendiri: kalau satu modul membaca deret yang berbeda, skor dihitung dari IDX sementara stop
# dan laporan mutu membaca yfinance, tanpa satu pun tanda.


@dataclass(frozen=True)
class PilihanHarga:
    """Deret harga yang dipakai berhitung: satu label, atau sambungan dua label (K97)."""

    dasar: str
    resmi: str | None = None
    sejak: date | None = None

    @property
    def tersambung(self) -> bool:
        return self.resmi is not None

    @property
    def label(self) -> str:
        """Teks yang ditampilkan dan dipakai sebagai kunci simpanan (mis. `konteks_pasar`)."""
        if self.resmi is None or self.sejak is None:
            return self.dasar
        return f"{self.resmi} sejak {self.sejak.isoformat()}; sebelumnya {self.dasar}"

    @property
    def label_dipakai(self) -> tuple[str, ...]:
        return (self.dasar,) if self.resmi is None else (self.dasar, self.resmi)

    def label_pada(self, tanggal: date) -> str:
        """Satu label yang menyumbang bar pada `tanggal`."""
        if self.resmi is not None and self.sejak is not None and tanggal >= self.sejak:
            return self.resmi
        return self.dasar

    def syarat(self, alias: str = "") -> tuple[str, tuple[object, ...]]:
        """Penggalan SQL (tanpa `WHERE`/`AND`) + argumennya, untuk tanda tanya posisi."""
        if self.resmi is None or self.sejak is None:
            return f"{alias}sumber = ?", (self.dasar,)
        return (
            f"(({alias}sumber = ? AND {alias}tanggal < ?) OR ({alias}sumber = ? AND {alias}tanggal >= ?))",
            (self.dasar, self.sejak.isoformat(), self.resmi, self.sejak.isoformat()),
        )

    def syarat_bernama(self, alias: str = "") -> tuple[str, dict[str, object]]:
        """Sama dengan `syarat`, untuk kueri yang memakai parameter bernama."""
        if self.resmi is None or self.sejak is None:
            return f"{alias}sumber = :ph_dasar", {"ph_dasar": self.dasar}
        return (
            f"(({alias}sumber = :ph_dasar AND {alias}tanggal < :ph_sejak)"
            f" OR ({alias}sumber = :ph_resmi AND {alias}tanggal >= :ph_sejak))",
            {"ph_dasar": self.dasar, "ph_resmi": self.resmi, "ph_sejak": self.sejak.isoformat()},
        )


def sebagai_pilihan(sumber: str | PilihanHarga | None) -> PilihanHarga | None:
    """Terima label tunggal (pemanggil lama, `--sumber`) atau pilihan lengkap."""
    if sumber is None or isinstance(sumber, PilihanHarga):
        return sumber
    return PilihanHarga(dasar=sumber)


def sambungan_berlaku(
    sambungan: sqlite3.Connection, *, batas: str | None = None
) -> sqlite3.Row | None:
    """Sambungan harga yang berlaku pada `batas` (atau hari ini); `None` bila tidak ada.

    Tiap `berlaku_sejak` adalah kunci dengan revisinya sendiri (append-only, seperti tabel data
    lain); yang berlaku adalah tanggal **aktif** terbesar menurut revisi terakhirnya. Mencabut =
    menyatakan tanggal itu `aktif = tidak`. Aturan "pernyataan terakhir menang" sengaja tidak
    dipakai: mengimpor ulang pernyataan lama dilewati sebagai "sudah ada dan sama", sehingga
    pernyataan itu diam-diam tidak berlaku lagi.
    """
    batas_efektif = batas if batas is not None else "9999-12-31T23:59:59"
    return sambungan.execute(
        "SELECT * FROM sambungan_harga AS r"
        " WHERE r.diketahui_pada <= :batas AND r.aktif = 1"
        "   AND NOT EXISTS (SELECT 1 FROM sambungan_harga AS lain"
        "                   WHERE lain.berlaku_sejak = r.berlaku_sejak"
        "                     AND lain.diketahui_pada <= :batas"
        "                     AND lain.diketahui_pada > r.diketahui_pada)"
        " ORDER BY r.berlaku_sejak DESC LIMIT 1",
        {"batas": batas_efektif},
    ).fetchone()


def harga_dipakai(
    sambungan: sqlite3.Connection, *, batas: str | None = None
) -> PilihanHarga | None:
    """Deret harga yang dipakai berhitung pada `batas`; `None` bila belum ada bar harga.

    Tanpa sambungan aktif: label dengan bar terbanyak (K14). Dengan sambungan aktif: label resmi
    sejak `berlaku_sejak`, label terbanyak **selain** label resmi sebelumnya.
    """
    riwayat = riwayat_sumber(sambungan, batas=batas)
    if not riwayat:
        return None
    pernyataan = sambungan_berlaku(sambungan, batas=batas)
    if pernyataan is None:
        return PilihanHarga(dasar=riwayat[0][0])
    resmi = pernyataan["sumber_resmi"]
    dasar = next((label for label, _ in riwayat if label != resmi), None)
    if dasar is None:
        # Belum ada riwayat dari label lain: deretnya memang hanya label resmi.
        return PilihanHarga(dasar=resmi)
    return PilihanHarga(
        dasar=dasar, resmi=resmi, sejak=date.fromisoformat(pernyataan["berlaku_sejak"])
    )


# Gerbang sambungan (K97 b) dan hari bolong (K97 d).
#
# Gerbang: deret emiten yang benar-benar disambung (punya bar label riwayat sebelum tanggal
# sambung **dan** bar label resmi sejak itu) hanya dipakai bila pada hari tumpang-tindih sebelum
# tanggal sambung penutupan kedua label sama persis, minimal `HARI_TUMPANG_TINDIH_MINIMUM` hari.
# Yang diperiksa adalah **setiap** emiten yang disambung, bukan hanya yang likuid: likuiditas
# dihitung dari deret sambungan itu sendiri, jadi menyaringnya lebih dulu akan berputar.
# Penutupan dibandingkan mentah; split di dalam hari tumpang-tindih membuat keduanya berbeda dan
# emiten itu ditolak — berisik, bukan disambung dengan tebakan basis.
#
# Hari bolong: hari bursa (menurut kalender) sejak tanggal sambung yang tidak punya satu bar
# label resmi pun, artinya berkas hari itu tidak diunggah. Bolong per emiten (mis. suspensi)
# bukan urusan ini. Kalender yang belum memuat rentangnya membuat hari bolong tidak bisa
# dihitung, dan itu juga disebut — "tidak bisa dihitung" bukan "tidak ada".

#: Hari tumpang-tindih minimum sebelum tanggal sambung (K97 b, usulan P42 yang disetujui).
HARI_TUMPANG_TINDIH_MINIMUM = 5

#: Hari tumpang-tindih dicari dalam sekian hari kalender sebelum tanggal sambung. Yang menjadi
#: bukti sambungan adalah hari-hari tepat sebelum tanggal itu; batas ini juga membuat kueri
#: memakai indeks `tanggal` — tanpa batas, mencari bar label resmi memindai seluruh riwayat
#: (terukur 17 dtk atas ±1 juta bar, 29 Okt 2026; tidak ada indeks pada `sumber`).
JENDELA_TUMPANG_TINDIH_HARI = 60

#: Jendela (hari bursa) tempat hari bolong membuat peringkat sementara (K97 d). Sama dengan
#: jendela metrik harga terpanjang (`metrik.HARI_12_BULAN`; dijaga uji, karena `metrik`
#: mengimpor modul ini dan tidak bisa diimpor balik).
JENDELA_BOLONG_HARI_BURSA = 252

#: Contoh tanggal yang ditulis dalam alasan, supaya pesan tetap terbaca.
_CONTOH_TANGGAL = 5


@dataclass(frozen=True)
class KeadaanSambungan:
    """Hasil gerbang sambungan (K97 b) dan hari bolong sejak tanggal sambung (K97 d)."""

    pilihan: PilihanHarga
    #: Emiten yang deretnya disambung tetapi tidak lolos gerbang → alasannya. Metrik harganya
    #: "tidak dihitung" dengan alasan ini (`metrik.seri_harga`).
    ditolak: Mapping[str, str]
    #: Penutupan berbeda pada hari tumpang-tindih (bagian dari `ditolak`): kode → (tanggal,
    #: penutupan label riwayat, penutupan label resmi) pertama yang berbeda.
    beda: Mapping[str, tuple[date, int | None, int | None]]
    #: Jumlah emiten yang deretnya disambung dan karena itu diperiksa gerbang.
    diperiksa: int
    #: Hari bursa sejak tanggal sambung (sampai tanggal data) tanpa satu bar label resmi pun.
    hari_bolong: tuple[date, ...] = ()
    #: Bagian `hari_bolong` yang masih di dalam `JENDELA_BOLONG_HARI_BURSA` terakhir.
    bolong_di_jendela: tuple[date, ...] = ()
    #: Alasan hari bolong tidak bisa dihitung; `None` bila kalender memuat seluruh rentangnya.
    kalender_kurang: str | None = None

    @property
    def sementara(self) -> str | None:
        """Sebab peringkat harus disebut PERINGKAT SEMENTARA (K97 d); `None` bila tidak ada."""
        if self.kalender_kurang is not None:
            return (
                "hari bolong sejak tanggal sambung "
                f"{_tanggal(self.pilihan.sejak)} tidak bisa dihitung: {self.kalender_kurang}"
            )
        if self.bolong_di_jendela:
            return (
                f"{len(self.bolong_di_jendela)} hari bolong — hari bursa sejak tanggal sambung "
                f"{_tanggal(self.pilihan.sejak)} tanpa berkas harga {self.pilihan.resmi} di jendela "
                f"metrik ({_daftar_tanggal(self.bolong_di_jendela)}); unggah berkas hari itu"
            )
        return None

    def ringkas(self) -> str:
        """Satu kalimat tentang gerbangnya, untuk laporan."""
        teks = (
            f"gerbang sambungan {_tanggal(self.pilihan.sejak)}: {self.diperiksa} emiten disambung, "
            f"{self.diperiksa - len(self.ditolak)} lolos, {len(self.ditolak)} ditolak"
        )
        if self.beda:
            teks += f" ({len(self.beda)} karena penutupan berbeda)"
        return teks


def _tanggal(nilai: date | None) -> str:
    return nilai.isoformat() if nilai is not None else "(tidak diketahui)"


def _daftar_tanggal(tanggal: Sequence[date]) -> str:
    teks = ", ".join(satu.isoformat() for satu in tanggal[:_CONTOH_TANGGAL])
    return teks + (f" … dan {len(tanggal) - _CONTOH_TANGGAL} lagi" if len(tanggal) > _CONTOH_TANGGAL else "")


def periksa_sambungan(
    sambungan: sqlite3.Connection,
    pilihan: PilihanHarga,
    *,
    tanggal_data: date,
    batas: str | None = None,
) -> KeadaanSambungan | None:
    """Gerbang (K97 b) dan hari bolong (K97 d) deret `pilihan`; `None` bila tidak tersambung.

    `batas` (`diketahui_pada`) membuatnya point-in-time seperti `muat`; tanpa `batas`, seluruh
    baris yang ada hari ini yang dihitung (laporan mutu keadaan sekarang).
    """
    if pilihan.resmi is None or pilihan.sejak is None:
        return None
    batas_efektif = batas if batas is not None else "9999-12-31T23:59:59"
    sejak = pilihan.sejak.isoformat()
    akhir = tanggal_data.isoformat()

    def as_of(tabel: str, syarat: str, **ekstra: object) -> list[sqlite3.Row]:
        return sambungan.execute(
            _sql_as_of(tabel, syarat_tambahan=syarat), {"batas": batas_efektif, **ekstra}
        ).fetchall()

    # Emiten yang deretnya disambung. EXISTS per kode memakai kunci (kode, tanggal, …), jadi
    # riwayat label dasar tidak perlu dipindai seluruhnya.
    disambung = sorted(
        satu["kode"]
        for satu in sambungan.execute(
            "SELECT DISTINCT r.kode FROM harga_harian AS r"
            " WHERE r.sumber = :resmi AND r.tanggal >= :sejak AND r.diketahui_pada <= :batas"
            "   AND EXISTS (SELECT 1 FROM harga_harian AS d"
            "               WHERE d.kode = r.kode AND d.sumber = :dasar AND d.tanggal < :sejak"
            "                 AND d.diketahui_pada <= :batas)",
            {"resmi": pilihan.resmi, "dasar": pilihan.dasar, "sejak": sejak, "batas": batas_efektif},
        )
    )

    resmi_sebelum: dict[str, dict[str, int | None]] = {}
    for baris in as_of(
        "harga_harian",
        " AND r.tanggal >= :awal_jendela AND r.tanggal < :sejak AND r.sumber = :resmi",
        resmi=pilihan.resmi,
        sejak=sejak,
        awal_jendela=(pilihan.sejak - timedelta(days=JENDELA_TUMPANG_TINDIH_HARI)).isoformat(),
    ):
        resmi_sebelum.setdefault(baris["kode"], {})[baris["tanggal"]] = baris["close"]
    dasar_sebelum: dict[str, dict[str, int | None]] = {}
    if resmi_sebelum:
        awal = min(min(per_hari) for per_hari in resmi_sebelum.values())
        for baris in as_of(
            "harga_harian",
            " AND r.sumber = :dasar AND r.tanggal >= :awal AND r.tanggal < :sejak",
            dasar=pilihan.dasar,
            awal=awal,
            sejak=sejak,
        ):
            dasar_sebelum.setdefault(baris["kode"], {})[baris["tanggal"]] = baris["close"]

    ditolak: dict[str, str] = {}
    beda: dict[str, tuple[date, int | None, int | None]] = {}
    for kode in disambung:
        resmi = resmi_sebelum.get(kode, {})
        dasar = dasar_sebelum.get(kode, {})
        sama_hari = sorted(
            hari for hari in resmi.keys() & dasar.keys()
            if resmi[hari] is not None and dasar[hari] is not None
        )
        selisih = [hari for hari in sama_hari if resmi[hari] != dasar[hari]]
        if selisih:
            pertama = selisih[0]
            beda[kode] = (date.fromisoformat(pertama), dasar[pertama], resmi[pertama])
            ditolak[kode] = (
                f"gerbang sambungan (K97 b): penutupan {pilihan.dasar} dan {pilihan.resmi} berbeda "
                f"pada {len(selisih)} dari {len(sama_hari)} hari tumpang-tindih sebelum {sejak} "
                f"(pertama {pertama}: {dasar[pertama]} vs {resmi[pertama]}); deretnya tidak "
                "disambung — periksa kedua sumber, atau nyatakan tanggal sambung lain"
            )
        elif len(sama_hari) < HARI_TUMPANG_TINDIH_MINIMUM:
            ditolak[kode] = (
                f"gerbang sambungan (K97 b): hanya {len(sama_hari)} hari tumpang-tindih sebelum "
                f"{sejak} (dalam {JENDELA_TUMPANG_TINDIH_HARI} hari kalender) dengan penutupan dari kedua sumber, minimal "
                f"{HARI_TUMPANG_TINDIH_MINIMUM}; unggah berkas {pilihan.resmi} untuk hari bursa "
                "sebelum tanggal sambung, atau nyatakan tanggal sambung yang lebih akhir"
            )

    # Hari bolong (K97 d).
    hari_bolong: tuple[date, ...] = ()
    di_jendela: tuple[date, ...] = ()
    kalender_kurang: str | None = None
    if pilihan.sejak <= tanggal_data:
        kalender = {
            baris["tanggal"]: bool(baris["hari_bursa"])
            for baris in as_of(
                "kalender_bursa", " AND r.tanggal >= :sejak AND r.tanggal <= :akhir", sejak=sejak, akhir=akhir
            )
        }
        semua_hari = [
            pilihan.sejak + timedelta(days=i) for i in range((tanggal_data - pilihan.sejak).days + 1)
        ]
        tak_termuat = [hari for hari in semua_hari if hari.isoformat() not in kalender]
        if tak_termuat:
            kalender_kurang = (
                f"kalender bursa belum memuat {len(tak_termuat)} tanggal antara {sejak} dan "
                f"{akhir} ({_daftar_tanggal(tak_termuat)}); perbarui kalender bursa"
            )
        else:
            berkas_ada = {
                baris["tanggal"]
                for baris in sambungan.execute(
                    "SELECT DISTINCT tanggal FROM harga_harian"
                    " WHERE sumber = ? AND tanggal >= ? AND tanggal <= ? AND diketahui_pada <= ?",
                    (pilihan.resmi, sejak, akhir, batas_efektif),
                )
            }
            hari_bursa = [hari for hari in semua_hari if kalender[hari.isoformat()]]
            hari_bolong = tuple(hari for hari in hari_bursa if hari.isoformat() not in berkas_ada)
            jendela = set(hari_bursa[-JENDELA_BOLONG_HARI_BURSA:])
            di_jendela = tuple(hari for hari in hari_bolong if hari in jendela)

    return KeadaanSambungan(
        pilihan=pilihan,
        ditolak=ditolak,
        beda=beda,
        diperiksa=len(disambung),
        hari_bolong=hari_bolong,
        bolong_di_jendela=di_jendela,
        kalender_kurang=kalender_kurang,
    )


@dataclass(frozen=True)
class Potret:
    """Isi satu snapshot, siap dihitung. Seluruh deret sudah urut tanggal menaik."""

    id_snapshot: int
    tanggal_data: date
    batas_diketahui: str
    versi_skema: int
    versi_aplikasi: str
    emiten: Mapping[str, Emiten]
    harga: Mapping[str, tuple[HargaHarian, ...]]
    indeks: Mapping[str, tuple[PenutupanIndeks, ...]]
    aksi: Mapping[str, tuple[AksiKorporasi, ...]]
    fundamental: Mapping[str, tuple[Fundamental, ...]]
    rasio_bank: Mapping[str, tuple[RasioBank, ...]]
    notasi: tuple[NotasiKhusus, ...]
    sun: tuple[ImbalHasilSUN, ...]
    #: Label sumber harga yang **dipakai** deret `harga` di atas (P17). `None` = belum ada bar
    #: harga sama sekali. Ikut disimpan supaya laporan bisa menyebutnya apa adanya, bukan
    #: menyisipkannya dari tempat lain yang tidak tahu snapshot ini dibaca bagaimana.
    sumber_harga: str | None = None
    #: Seluruh label sumber yang **ada** pada saat snapshot ini, beserta jumlah barnya, terbanyak
    #: lebih dulu (bentuknya sama dengan `riwayat_sumber`). Disimpan apa adanya, bukan sebagai
    #: "yang diabaikan": label yang tidak dipakai tetap harus terlihat — kalau ia dibuang tanpa
    #: jejak, "harga pembanding sudah diimpor" dan "harga pembanding tidak ada" akan tampak sama
    #: dari luar, padahal yang pertama menuntut pemeriksaan PRD 7.3 dan yang kedua menuntut impor.
    sumber_tersedia: tuple[tuple[str, int], ...] = ()
    #: Deret yang dipakai (K97); `sumber_harga` adalah `pilihan_harga.label`.
    pilihan_harga: PilihanHarga | None = None
    #: Gerbang dan hari bolong deret sambungan (K97 b, d); `None` bila deretnya tidak disambung.
    keadaan_sambungan: KeadaanSambungan | None = None

    @property
    def label_dipakai(self) -> tuple[str, ...]:
        if self.pilihan_harga is not None:
            return self.pilihan_harga.label_dipakai
        return () if self.sumber_harga is None else (self.sumber_harga,)

    @property
    def sumber_diabaikan(self) -> tuple[tuple[str, int], ...]:
        """Label yang **tidak** dipakai berhitung, beserta jumlah barnya."""
        return tuple(satu for satu in self.sumber_tersedia if satu[0] not in self.label_dipakai)

    @property
    def bar_per_label(self) -> tuple[tuple[str, int], ...]:
        """Jumlah bar yang **benar-benar dimuat** per label, urut seperti `label_dipakai` (K97 e)."""
        hitung = dict.fromkeys(self.label_dipakai, 0)
        for deret in self.harga.values():
            for bar in deret:
                hitung[bar.sumber] = hitung.get(bar.sumber, 0) + 1
        return tuple(hitung.items())

    @property
    def bar_sumber_harga(self) -> int | None:
        """Jumlah bar label yang dipakai; `None` bila tidak ada bar harga sama sekali."""
        if self.pilihan_harga is not None and self.pilihan_harga.tersambung:
            return sum(jumlah for _, jumlah in self.bar_per_label)
        for label, jumlah in self.sumber_tersedia:
            if label == self.sumber_harga:
                return jumlah
        return None

    @property
    def kode(self) -> tuple[str, ...]:
        return tuple(self.emiten)


def _sql_as_of(tabel: str, *, syarat_tambahan: str = "") -> str:
    """Kueri "revisi terakhir per kunci alami yang sudah diketahui pada batas waktu".

    Bentuknya sengaja tidak memakai `v_<tabel>_terkini`: tampilan itu tidak punya dimensi
    waktu, sehingga revisi yang dicatat belakangan akan bocor ke perhitungan snapshot lama.

    `syarat_tambahan` menyaring baris **sebelum** revisi terakhirnya dipilih, dan dipakai
    `harga_harian` untuk membaca satu label sumber saja (lihat `riwayat_sumber`). Menyaringnya
    di Python akan sama hasilnya tetapi menuntut seluruh bar harga dibaca lebih dulu — sejuta
    baris pada basis data nyata.
    """
    kunci = KUNCI_ALAMI[tabel]
    syarat = " AND ".join(f"lain.{kolom} = r.{kolom}" for kolom in kunci)
    return (
        f"SELECT r.* FROM {tabel} AS r\n"
        f"WHERE r.diketahui_pada <= :batas{syarat_tambahan}\n"
        f"  AND NOT EXISTS (\n"
        f"      SELECT 1 FROM {tabel} AS lain\n"
        f"      WHERE {syarat}\n"
        f"        AND lain.diketahui_pada <= :batas\n"
        f"        AND lain.diketahui_pada > r.diketahui_pada\n"
        f"  )"
    )


def notasi_as_of(sambungan: sqlite3.Connection, *, batas: str) -> tuple[NotasiKhusus, ...]:
    """Notasi khusus yang diketahui pada `batas` — bagian `muat` yang juga dibaca dasbor.

    Dasbor butuh status notasi snapshot (peringkat sementara, PRD 7.3) tanpa memuat seluruh
    potret; membacanya lewat kueri yang sama menjamin jawabannya sama dengan saringan.
    """
    return tuple(
        NotasiKhusus(
            kode=baris["kode"],
            jenis=baris["jenis"],
            tanggal_mulai=date.fromisoformat(baris["tanggal_mulai"]),
            tanggal_selesai=(
                date.fromisoformat(baris["tanggal_selesai"]) if baris["tanggal_selesai"] else None
            ),
            keterangan=baris["keterangan"],
        )
        for baris in sambungan.execute(_sql_as_of("notasi_khusus"), {"batas": batas})
    )


def snapshot_terakhir(sambungan: sqlite3.Connection) -> sqlite3.Row:
    """Baris `snapshot` terakhir. Gagal berisik bila belum ada satu pun."""
    baris = sambungan.execute(
        "SELECT * FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()
    if baris is None:
        raise GalatIngesti(
            "belum ada snapshot di basis data. Jalankan `python -m mejasaham --refresh` "
            "(atau --impor) lebih dulu: saringan selalu dihitung atas satu snapshot."
        )
    return baris


def _baris_snapshot(sambungan: sqlite3.Connection, id_snapshot: int | None) -> sqlite3.Row:
    if id_snapshot is None:
        return snapshot_terakhir(sambungan)
    baris = sambungan.execute(
        "SELECT * FROM snapshot WHERE id_snapshot = ?", (id_snapshot,)
    ).fetchone()
    if baris is None:
        raise GalatIngesti(f"snapshot {id_snapshot} tidak ada di basis data")
    return baris


def _harga(baris: Mapping[str, Any]) -> HargaHarian:
    return HargaHarian(
        kode=baris["kode"],
        tanggal=date.fromisoformat(baris["tanggal"]),
        open=baris["open"],
        high=baris["high"],
        low=baris["low"],
        close=baris["close"],
        volume=baris["volume"],
        nilai=baris["nilai"],
        penyesuaian_sumber=baris["penyesuaian_sumber"],
        diketahui_pada=baris["diketahui_pada"],
        sumber=baris["sumber"],
    )


def _fundamental(baris: Mapping[str, Any]) -> Fundamental:
    return Fundamental(
        kode=baris["kode"],
        periode=date.fromisoformat(baris["periode"]),
        jenis_laporan=baris["jenis_laporan"],
        tgl_publikasi=date.fromisoformat(baris["tgl_publikasi"]),
        asal_tgl_publikasi=baris["asal_tgl_publikasi"],
        mata_uang=baris["mata_uang"],
        satuan_uang=baris["satuan_uang"],
        pendapatan=baris["pendapatan"],
        laba_induk=baris["laba_induk"],
        ekuitas_induk=baris["ekuitas_induk"],
        ebit=baris["ebit"],
        beban_bunga=baris["beban_bunga"],
        da=baris["da"],
        utang_bunga=baris["utang_bunga"],
        kas=baris["kas"],
        cfo=baris["cfo"],
        jumlah_saham=baris["jumlah_saham"],
        dps=baris["dps"],
        # Kolom `sumber` NOT NULL dan sudah ditulis per baris sejak K18. Tanpa baris ini provenance
        # laporan hilang tepat saat dibaca kembali — kelas kekeliruan yang sama dengan `rasio_bank`
        # sebelum K78/T77, dan akibatnya sama: pemanggil `Potret` menyimpulkan "sumber tidak
        # dinyatakan" padahal basis datanya menyatakannya.
        sumber=baris["sumber"],
    )


def muat(
    sambungan: sqlite3.Connection,
    id_snapshot: int | None = None,
    *,
    sumber: str | PilihanHarga | None = None,
) -> Potret:
    """Muat satu snapshot beserta seluruh data yang **sudah diketahui** saat itu.

    `sumber` menimpa label sumber harga yang dipakai berhitung; bawaannya label dengan riwayat
    bar terbanyak **pada saat snapshot itu** (lihat `riwayat_sumber`). Label yang tidak punya
    satu bar pun **ditolak**, bukan menghasilkan potret tanpa harga: potret kosong akan terbaca
    sebagai "emitennya belum punya data", padahal yang salah adalah nama labelnya — dan itu
    kekeliruan yang paling mahal untuk ditemukan belakangan.

    `PilihanHarga` utuh (mis. sambungan K97 yang sudah dipilih pemanggil) dipakai apa adanya,
    dengan pemeriksaan yang sama untuk setiap labelnya. `PilihanHarga.label` sambungan adalah
    teks tampilan, bukan label bar — mengirimnya sebagai `str` selalu ditolak.
    """
    kepala = _baris_snapshot(sambungan, id_snapshot)
    batas = kepala["batas_diketahui"]
    tanggal_data = date.fromisoformat(kepala["tanggal_data"])

    riwayat = riwayat_sumber(sambungan, batas=batas)
    label = tuple(satu[0] for satu in riwayat)
    if sumber is None:
        pilihan = harga_dipakai(sambungan, batas=batas)
    else:
        # `--sumber` menimpa seluruh pilihan, termasuk sambungan K97: satu label, apa adanya.
        pilihan = sebagai_pilihan(sumber)
        assert pilihan is not None
        hilang = next((satu for satu in pilihan.label_dipakai if satu not in label), None)
        if hilang is not None:
            ada = (
                f" Label yang ada: {', '.join(label)}."
                if label
                else " Belum ada bar harga sama sekali."
            )
            raise GalatIngesti(
                f"sumber harga {hilang!r} tidak punya satu bar pun yang sudah diketahui pada "
                f"{batas}.{ada} Jalankan --refresh atau --impor lebih dulu, atau pilih salah satu "
                "label di atas lewat --sumber."
            )

    # Kueri harga dibatasi pada label yang dipakai **di dalam SQL**: dua label pada tanggal yang
    # sama membuat tanggal terduplikasi dan ADTV20 emiten berubah menjadi "tidak dihitung" (P17).
    syarat_harga = ""
    parameter_harga: dict[str, object] = {}
    if pilihan is not None:
        penggalan, parameter_harga = pilihan.syarat_bernama("r.")
        syarat_harga = f" AND {penggalan}"

    def ambil(
        tabel: str, *, syarat: str = "", ekstra: Mapping[str, Any] | None = None
    ) -> list[Mapping[str, Any]]:
        return sambungan.execute(
            _sql_as_of(tabel, syarat_tambahan=syarat),
            {"batas": batas, **(ekstra or {})},
        ).fetchall()

    emiten = {
        baris["kode"]: Emiten(
            kode=baris["kode"],
            nama=baris["nama"],
            sektor_idx_ic=baris["sektor_idx_ic"],
            sektor_sumber=baris["sektor_sumber"],
            jenis=baris["jenis"],
            papan=baris["papan"],
            status_notasi=baris["status_notasi"],
            tanggal_notasi=(
                date.fromisoformat(baris["tanggal_notasi"]) if baris["tanggal_notasi"] else None
            ),
            jumlah_saham=baris["jumlah_saham"],
            free_float_bp=baris["free_float_bp"],
            sumber=baris["sumber"],
        )
        for baris in ambil("emiten")
    }

    harga: dict[str, list[HargaHarian]] = {}
    for baris in ambil("harga_harian", syarat=syarat_harga, ekstra=parameter_harga):
        harga.setdefault(baris["kode"], []).append(_harga(baris))
    for deret in harga.values():
        deret.sort(key=lambda satu: satu.tanggal)

    indeks: dict[str, list[PenutupanIndeks]] = {}
    for baris in ambil("harga_indeks"):
        indeks.setdefault(baris["indeks"], []).append(
            PenutupanIndeks(
                indeks=baris["indeks"],
                tanggal=date.fromisoformat(baris["tanggal"]),
                close=baris["close"],
            )
        )
    for deret in indeks.values():
        deret.sort(key=lambda satu: satu.tanggal)

    aksi: dict[str, list[AksiKorporasi]] = {}
    for baris in ambil("aksi_korporasi"):
        aksi.setdefault(baris["kode"], []).append(
            AksiKorporasi(
                kode=baris["kode"],
                tanggal=date.fromisoformat(baris["tanggal"]),
                jenis=baris["jenis"],
                rasio_lama=baris["rasio_lama"],
                rasio_baru=baris["rasio_baru"],
                harga_tebus=baris["harga_tebus"],
                dividen_per_saham=baris["dividen_per_saham"],
                tenggat=baris["tenggat"],
                sumber=baris["sumber"],
                keterangan=baris["keterangan"],
            )
        )
    for deret in aksi.values():
        deret.sort(key=lambda satu: satu.tanggal)

    # AC-15: fundamental hanya dipakai sejak tanggal publikasinya. Disaring di sini supaya
    # tidak ada modul hilir yang bisa lupa.
    fundamental: dict[str, list[Fundamental]] = {}
    for baris in ambil("fundamental"):
        satu = _fundamental(baris)
        if satu.tgl_publikasi > tanggal_data:
            continue
        fundamental.setdefault(satu.kode, []).append(satu)
    for deret in fundamental.values():
        deret.sort(key=lambda satu: (satu.periode, satu.tgl_publikasi))

    rasio_bank: dict[str, list[RasioBank]] = {}
    for baris in ambil("rasio_bank"):
        if date.fromisoformat(baris["tgl_publikasi"]) > tanggal_data:
            continue
        rasio_bank.setdefault(baris["kode"], []).append(
            RasioBank(
                kode=baris["kode"],
                periode=date.fromisoformat(baris["periode"]),
                tgl_publikasi=date.fromisoformat(baris["tgl_publikasi"]),
                npl_kotor_bp=baris["npl_kotor_bp"],
                car_bp=baris["car_bp"],
                bopo_bp=baris["bopo_bp"],
                nim_bp=baris["nim_bp"],
                keterangan=baris["keterangan"],
                # Kolom `sumber` NOT NULL di tabel, jadi provenance yang ditulis K78 ikut kembali
                # ke pemanggil potret — bukan hanya tersimpan di basis data.
                sumber=baris["sumber"],
            )
        )
    for deret in rasio_bank.values():
        deret.sort(key=lambda satu: satu.periode)

    notasi = notasi_as_of(sambungan, batas=batas)

    sun = tuple(
        ImbalHasilSUN(
            tanggal=date.fromisoformat(baris["tanggal"]),
            tenor_tahun=baris["tenor_tahun"],
            imbal_hasil_bp=baris["imbal_hasil_bp"],
        )
        for baris in sorted(ambil("imbal_hasil_sun"), key=lambda b: b["tanggal"])
    )

    return Potret(
        id_snapshot=kepala["id_snapshot"],
        tanggal_data=tanggal_data,
        batas_diketahui=batas,
        versi_skema=kepala["versi_skema"],
        versi_aplikasi=kepala["versi_aplikasi"],
        emiten=emiten,
        harga={kode: tuple(deret) for kode, deret in harga.items()},
        indeks={nama: tuple(deret) for nama, deret in indeks.items()},
        aksi={kode: tuple(deret) for kode, deret in aksi.items()},
        fundamental={kode: tuple(deret) for kode, deret in fundamental.items()},
        rasio_bank={kode: tuple(deret) for kode, deret in rasio_bank.items()},
        notasi=notasi,
        sun=sun,
        sumber_harga=pilihan.label if pilihan is not None else None,
        sumber_tersedia=riwayat,
        pilihan_harga=pilihan,
        keadaan_sambungan=(
            periksa_sambungan(sambungan, pilihan, tanggal_data=tanggal_data, batas=batas)
            if pilihan is not None
            else None
        ),
    )


def waktu_snapshot(potret: Potret) -> datetime:
    """`batas_diketahui` sebagai `datetime` — dipakai modul yang butuh, bukan diulang-ulang."""
    return datetime.fromisoformat(potret.batas_diketahui)
