"""Laporan mutu data (PRD 7.3) — "kekosongan data bersuara" (prinsip produk 5).

Berkas ini menjawab satu pertanyaan: **data mana yang tidak layak dipakai berhitung, dan
mengapa.** Ia tidak memperbaiki apa pun dan tidak mengisi lubang dengan angka netral; ia hanya
menemukan dan memberi nama. Perilaku yang dituntut PRD 7.3 karena itu muncul di sini sebagai
temuan bertingkat, bukan sebagai pembersihan diam-diam.

Tiga tingkat temuan, dan bedanya penting:

* `BOLONG` — data hari terakhir tidak ada bagi emiten itu. Emiten **dikeluarkan dari peringkat**
  (PRD 7.3, AC-1). Ini keadaan yang menghalangi perhitungan.
* `TAK_WAJAR` — nilainya ada tetapi tidak masuk akal (harga 0, lonjakan tanpa aksi korporasi).
  Ditandai untuk **ditinjau manusia** dan tidak dipakai dalam skoring (PRD 7.3).
* `CATATAN` — perlu diketahui, tidak menghalangi: kalender bursa belum memuat tanggal itu,
  snapshot lebih tua dari hari bursa terakhir, dividen besar yang bisa menjelaskan lonjakan.
  Ini yang membuat "sumber tidak resmi" dan "snapshot basi" terlihat, bukan tersembunyi.

Satu hal yang sengaja **tidak** dilakukan di sini: memutuskan emiten mana yang likuid. Semesta
likuid adalah urusan saringan (`saring.semesta_likuid`, K9). Yang dihitung laporan ini hanya
**peringkat ADTV20**, karena dua aturan PRD bergantung padanya:

* **PRD 7.3** — penutupan 20 emiten ber-ADTV20 tertinggi dibandingkan sumber kedua tiap minggu,
  selisih di atas 1% ditandai (`bandingkan_sumber_kedua`), dan **kapan pemeriksaan itu terakhir
  dijalankan** dicatat sebagai peristiwa (`catat_cek_sumber_kedua`) sehingga tuntutan "tiap
  minggu" bisa diperiksa, bukan diasumsikan.
* **PRD 9.3 / AC-1** — snapshot ditolak bila salah satu dari 50 emiten ber-ADTV20 tertinggi
  gagal atau datanya bolong. Daftar kritis itu diambil dari `peringkat_adtv` di sini, sehingga
  emiten yang gagal diambil **pun** ikut terperiksa: peringkatnya dihitung dari baris yang
  sudah tersimpan, bukan dari hasil pengambilan hari itu.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from mejasaham import metrik, potret
from mejasaham.ingesti import (
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_SPLIT_DIVIDEN,
    SUMBER_YFINANCE,
)

#: Penanda yang berarti "split sudah diterapkan sumber" (K8/C10).
SUDAH_DITERAPKAN_SUMBER = (PENYESUAIAN_SPLIT, PENYESUAIAN_SPLIT_DIVIDEN)

# ---------------------------------------------------------------------------------------
# Klasifikasi temuan
# ---------------------------------------------------------------------------------------

BOLONG = "bolong"
TAK_WAJAR = "tak_wajar"
CATATAN = "catatan"

#: Urutan tingkat dari yang paling menghalangi. Dipakai untuk mengurutkan laporan supaya yang
#: harus ditangani lebih dulu terbaca lebih dulu.
URUTAN_TINGKAT: Mapping[str, int] = {BOLONG: 0, TAK_WAJAR: 1, CATATAN: 2}

#: Temuan yang membuat emiten keluar dari peringkat (PRD 7.3, AC-1).
MENGHALANGI = frozenset({BOLONG, TAK_WAJAR})

#: Ambang lonjakan harga mencurigakan (PRD 7.3: "lonjakan > 3x tanpa aksi korporasi").
AMBANG_LONJAKAN = Decimal("3")

#: Rentang hari untuk mencari aksi korporasi di sekitar lonjakan. Aksi korporasi sering
#: tercatat beberapa hari sebelum/ sesudah harga ex-date, jadi menuntut tanggal yang sama
#: persis akan menghasilkan temuan palsu.
HARI_SEKITAR_AKSI = 5

#: Jumlah emiten teratas yang wajib dibandingkan ke sumber kedua tiap minggu (PRD 7.3).
JUMLAH_CEK_SUMBER_KEDUA = 20

#: Jumlah emiten ber-ADTV20 tertinggi yang kegagalannya membatalkan snapshot (PRD 9.3, AC-1).
JUMLAH_KRITIS = 50

#: Ambang selisih harga antar sumber (PRD 7.3: "selisih > 1% ditandai", ambang awal).
AMBANG_BEDA_SUMBER = Decimal("0.01")

#: Jeda maksimum antar cek sumber kedua (PRD 7.3: "tiap minggu"). Batasnya **7 hari**, dan cek
#: yang berumur tepat 7 hari masih dihitung tepat waktu — hari itu memang jadwal berikutnya.
#: "Lewat" mulai pada hari ke-8.
JEDA_CEK_SUMBER_KEDUA_HARI = 7

#: Cakupan satu jalan cek. Perbedaan harga yang ditemukan **tidak** mengurangi cakupan:
#: cek yang menemukan masalah tetap cek yang sudah dijalankan.
CAKUPAN_LENGKAP = "lengkap"
CAKUPAN_BELUM_LENGKAP = "belum_lengkap"

#: Keadaan cadence cek sumber kedua.
STATUS_BELUM_PERNAH = "belum_pernah"
STATUS_TEPAT_WAKTU = "tepat_waktu"
STATUS_LEWAT = "lewat"
#: Catatannya ada, tetapi tidak bisa dipakai menilai cadence (tanggalnya di depan hari ini, atau
#: tidak terbaca). Dilaporkan apa adanya dan **tidak** dianggap lulus.
STATUS_TIDAK_DAPAT_DINILAI = "tidak_dapat_dinilai"


@dataclass(frozen=True)
class Temuan:
    """Satu masalah data, diberi nama dan tingkatnya."""

    kode: str
    tingkat: str
    jenis: str
    keterangan: str

    def baris(self) -> str:
        return f"[{self.tingkat}] {self.kode}: {self.jenis} — {self.keterangan}"


@dataclass(frozen=True)
class KeadaanEmiten:
    """Ringkasan mutu satu emiten."""

    kode: str
    tanggal_terakhir: str | None
    jumlah_bar: int
    bolong: bool
    tak_wajar: bool
    catatan: int


@dataclass(frozen=True)
class PeringkatADTV:
    """Satu emiten dalam peringkat ADTV20 beserta angkanya.

    `nilai` disimpan sebagai `Decimal` supaya ambang pembanding (mis. Rp 5 miliar, K9) tidak
    pernah dibandingkan lewat `float` — selisih satu rupiah pun bisa membalik keputusan lolos.
    """

    kode: str
    adtv20: Decimal
    hari_terpakai: int


@dataclass(frozen=True)
class BedaSumber:
    """Selisih penutupan satu emiten antara sumber utama dan sumber kedua (PRD 7.3)."""

    kode: str
    tanggal: str
    close_utama: int
    close_pembanding: int
    selisih: Decimal | None

    @property
    def ditandai(self) -> bool:
        """True bila selisihnya melewati ambang. Selisih yang tidak bisa dihitung **tidak**
        dianggap lolos (aturan keras 2): ia dilaporkan sebagai temuan tersendiri."""
        return self.selisih is not None and self.selisih > AMBANG_BEDA_SUMBER


@dataclass
class LaporanPerbandingan:
    """Hasil satu jalan cek sumber kedua."""

    tanggal_data: str
    sumber_utama: str | None
    sumber_pembanding: str | None
    #: Daftar sumber yang benar-benar ada di basis data untuk tanggal itu.
    sumber_tersedia: tuple[str, ...] = ()
    diperiksa: tuple[BedaSumber, ...] = ()
    belum_dapat_dijalankan: list[str] = field(default_factory=list)

    @property
    def ditandai(self) -> tuple[BedaSumber, ...]:
        return tuple(satu for satu in self.diperiksa if satu.ditandai)

    @property
    def selisih_tak_terhitung(self) -> tuple[BedaSumber, ...]:
        return tuple(satu for satu in self.diperiksa if satu.selisih is None)

    @property
    def lengkap(self) -> bool:
        """True bila **seluruh** emiten teratas benar-benar dibandingkan.

        Inilah satu-satunya hal yang memenuhi tuntutan mingguan PRD 7.3. Cek yang berjalan
        tanpa pembanding — atau yang melewatkan sebagian emiten teratas — bukan cek yang
        diminta, walaupun ia "sudah dijalankan".
        """
        return bool(self.diperiksa) and not self.belum_dapat_dijalankan

    def ringkas(self) -> str:
        bagian = [
            f"Perbandingan sumber kedua — tanggal data {self.tanggal_data}",
            f"  sumber utama     : {self.sumber_utama or '(tidak diketahui)'}",
            f"  sumber pembanding: {self.sumber_pembanding or '(belum ada)'}",
            f"  {len(self.diperiksa)} emiten teratas diperiksa · {len(self.ditandai)} ditandai "
            f"(selisih > {AMBANG_BEDA_SUMBER:.0%})",
        ]
        for satu in self.ditandai:
            bagian.append(
                f"  [{TAK_WAJAR}] {satu.kode} {satu.tanggal}: {satu.close_utama} vs "
                f"{satu.close_pembanding} (selisih {satu.selisih:.2%})"
            )
        for satu in self.selisih_tak_terhitung:
            bagian.append(
                f"  [catatan] {satu.kode} {satu.tanggal}: selisih tidak bisa dihitung "
                "(salah satu penutupan nol atau kosong)"
            )
        bagian.extend(f"  [belum dapat diperiksa] {satu}" for satu in self.belum_dapat_dijalankan)
        return "\n".join(bagian)


@dataclass(frozen=True)
class KeadaanCekSumberKedua:
    """Kapan cek sumber kedua terakhir benar-benar dijalankan (PRD 7.3: tiap minggu).

    Yang dinilai adalah **cek yang lengkap**, bukan sekadar "pernah dijalankan": cek yang
    berjalan tanpa harga pembanding tidak membandingkan apa pun, jadi ia tidak boleh
    memadamkan peringatan mingguan. Percobaan yang belum lengkap tetap dilaporkan — supaya
    terlihat ada usaha yang gagal, bukan tidak ada usaha sama sekali.
    """

    status: str
    batas_hari: int = JEDA_CEK_SUMBER_KEDUA_HARI
    #: Catatan terbaru, apa pun cakupannya (ISO-8601).
    terakhir_dijalankan: str | None = None
    cakupan_terakhir: str | None = None
    catatan_terakhir: str | None = None
    #: Cek **lengkap** terbaru, dan jaraknya ke hari ini dalam hari.
    terakhir_lengkap: str | None = None
    hari_sejak_lengkap: int | None = None
    #: True bila percobaan terakhir lebih baru daripada cek lengkap terakhir — keadaan yang
    #: perlu disebut, sebab pengguna mungkin mengira ceknya sudah beres.
    percobaan_terakhir_belum_lengkap: bool = False
    #: Alasan status `tidak_dapat_dinilai`.
    alasan: str | None = None

    @property
    def lulus(self) -> bool:
        """Hanya `tepat_waktu` yang memenuhi PRD 7.3 — sisanya belum, termasuk yang tak terbaca."""
        return self.status == STATUS_TEPAT_WAKTU

    @property
    def berlaku_sampai(self) -> str | None:
        """Tanggal (ISO) paling lambat cek berikutnya, bila ada cek lengkap yang tercatat."""
        if self.terakhir_lengkap is None:
            return None
        tanggal = _tanggal_dari_iso(self.terakhir_lengkap)
        if tanggal is None:
            return None
        return (tanggal + timedelta(days=self.batas_hari)).isoformat()

    def ringkas(self) -> str:
        """Satu-dua kalimat tentang keadaan cadence, siap dicetak apa adanya."""
        if self.status == STATUS_TEPAT_WAKTU:
            inti = (
                f"cek sumber kedua terakhir yang lengkap {self.hari_sejak_lengkap} hari lalu "
                f"({_tanggal_tampil(self.terakhir_lengkap)}); batas {self.batas_hari} hari"
            )
        elif self.status == STATUS_LEWAT:
            inti = (
                f"cek sumber kedua terakhir yang lengkap {self.hari_sejak_lengkap} hari lalu "
                f"({_tanggal_tampil(self.terakhir_lengkap)}), sudah lewat batas {self.batas_hari} "
                "hari (PRD 7.3)"
            )
        elif self.status == STATUS_TIDAK_DAPAT_DINILAI:
            inti = f"cadence cek sumber kedua tidak dapat dinilai: {self.alasan}"
        elif self.terakhir_dijalankan is None:
            inti = (
                "cek sumber kedua belum pernah dijalankan, padahal PRD 7.3 menuntutnya tiap "
                f"{self.batas_hari} hari"
            )
        else:
            inti = (
                "belum ada cek sumber kedua yang lengkap, padahal PRD 7.3 menuntutnya tiap "
                f"{self.batas_hari} hari"
            )

        if self.percobaan_terakhir_belum_lengkap:
            inti += (
                f"; percobaan terakhir {_tanggal_tampil(self.terakhir_dijalankan)} belum lengkap"
                + (f" ({self.catatan_terakhir})" if self.catatan_terakhir else "")
            )
        return inti

    def temuan(self) -> Temuan:
        """Temuan laporan mutu untuk keadaan ini.

        Tingkatnya `CATATAN` untuk semua keadaan — termasuk yang belum pernah dijalankan.
        Cek mingguan yang tertunda tidak membuat satu pun angka emiten salah, jadi ia tidak
        boleh mengeluarkan emiten dari peringkat; yang tidak boleh adalah ia **tidak terlihat**.
        """
        keterangan = self.ringkas()
        if not self.lulus:
            keterangan += (
                "; jalankan `--cek-sumber-kedua` (harga pembanding masuk lewat `--impor` dengan "
                "kolom `sumber` terisi)"
            )
        return Temuan("-", CATATAN, f"cek_sumber_kedua_{self.status}", keterangan)


@dataclass
class LaporanMutu:
    """Seluruh hasil pemeriksaan satu snapshot."""

    tanggal_data: str
    hari_bursa_terakhir: str | None
    jumlah_emiten: int
    jumlah_bar_mentah: int
    jumlah_bar_terkini: int
    jumlah_gagal_ambil: int
    temuan: list[Temuan] = field(default_factory=list)
    emiten_bermasalah: dict[str, KeadaanEmiten] = field(default_factory=dict)
    #: Peringkat ADTV20 yang dipakai laporan ini (PRD 7.3 & 9.3). Kosong berarti peringkatnya
    #: belum bisa dihitung — bukan berarti tidak ada emiten teratas.
    peringkat_adtv: tuple[PeringkatADTV, ...] = ()
    pemeriksaan_belum_dapat_dijalankan: list[str] = field(default_factory=list)
    #: Keadaan cadence cek sumber kedua saat laporan ini dibuat (PRD 7.3, "tiap minggu").
    cek_sumber_kedua: KeadaanCekSumberKedua | None = None

    def tingkat(self, tingkat: str) -> list[Temuan]:
        return [satu for satu in self.temuan if satu.tingkat == tingkat]

    @property
    def dikeluarkan(self) -> tuple[str, ...]:
        """Emiten yang tidak boleh ikut diperingkat (PRD 7.3, AC-1)."""
        return tuple(
            sorted(kode for kode, satu in self.emiten_bermasalah.items() if satu.bolong or satu.tak_wajar)
        )

    @property
    def datar(self) -> bool:
        """Bersih dari temuan yang menghalangi — bukan berarti tanpa catatan sama sekali."""
        return not self.tingkat(BOLONG) and not self.tingkat(TAK_WAJAR)

    def ringkas(self) -> str:
        """Ringkasan tiga baris untuk terminal/log (PRD 7.2 "kegagalan tidak boleh senyap")."""
        bagian = [
            f"Laporan mutu — snapshot {self.tanggal_data}"
            + (f" (hari bursa terakhir: {self.hari_bursa_terakhir})" if self.hari_bursa_terakhir else ""),
            f"  emiten: {self.jumlah_emiten} | bar masuk: {self.jumlah_bar_mentah} "
            f"| bar terkini: {self.jumlah_bar_terkini} | gagal diambil: {self.jumlah_gagal_ambil}",
            f"  {len(self.tingkat(BOLONG))} bolong · {len(self.tingkat(TAK_WAJAR))} tak wajar "
            f"· {len(self.tingkat(CATATAN))} catatan"
            f" | dikeluarkan dari peringkat: {len(self.dikeluarkan)} emiten",
        ]
        return "\n".join(bagian)

    def rincian(self, batas: int = 20) -> str:
        """Rincian temuan, yang menghalangi lebih dulu, dibatasi supaya terminal tetap terbaca."""
        terurut = sorted(self.temuan, key=lambda satu: (URUTAN_TINGKAT[satu.tingkat], satu.kode, satu.jenis))
        if not terurut:
            return "  tidak ada temuan."
        baris = [f"  {satu.baris()}" for satu in terurut[:batas]]
        if len(terurut) > batas:
            baris.append(f"  ... dan {len(terurut) - batas} temuan lain (lihat berkas laporan mutu)")
        for satu in self.pemeriksaan_belum_dapat_dijalankan:
            baris.append(f"  [belum dapat diperiksa] {satu}")
        return "\n".join(baris)


# ---------------------------------------------------------------------------------------
# Pemeriksaan
# ---------------------------------------------------------------------------------------


def _desimal(nilai: object) -> Decimal | None:
    if nilai is None:
        return None
    try:
        angka = Decimal(str(nilai))
    except (InvalidOperation, ValueError):
        return None
    return angka if angka.is_finite() else None


def _syarat_sumber(
    sumber: str | potret.PilihanHarga | None, awal: str
) -> tuple[str, tuple[object, ...]]:
    """Penyaring label harga (satu label atau deret sambungan K97), diawali `awal`."""
    pilihan = potret.sebagai_pilihan(sumber)
    if pilihan is None:
        return "", ()
    penggalan, argumen = pilihan.syarat()
    return f"{awal}{penggalan}", argumen


def peringkat_adtv(
    sambungan: sqlite3.Connection,
    *,
    jumlah: int = JUMLAH_KRITIS,
    sumber: str | potret.PilihanHarga | None = None,
) -> tuple[PeringkatADTV, ...]:
    """Peringkat emiten menurut ADTV20: rata-rata `nilai` transaksi 20 **hari bursa** terakhir.

    Dua hal yang membuat kueri ini berbeda dari "20 baris terakhir per emiten":

    1. **Hari bursa, bukan baris** (P6/U7). Tanggalnya diambil lebih dulu sebagai satu himpunan
       (20 tanggal terakhir yang ada), baru nilainya dirata-ratakan per emiten. Emiten yang
       baru punya beberapa hari karena itu **tidak** ikut diperingkat — bukan diberi rata-rata
       dari hari yang lebih sedikit, yang akan membuat ADTV20-nya terlihat lebih besar.
    2. **`v_harga_harian_terkini`**, bukan tabel mentahnya. Revisi ganda untuk satu tanggal akan
       menghitung hari yang sama dua kali dan menggeser peringkatnya.

    Jendelanya **bersama**, bukan 20 hari terakhir milik masing-masing emiten. Emiten yang bar
    terakhirnya hilang karena itu tidak tetap menduduki peringkat teratas dengan rata-rata dari
    hari-hari yang lebih tua: angka itu bukan ADTV20 hari ini, dan memakainya akan menahan
    emiten lain keluar dari daftar 50 teratas — justru menahan yang perlu diperiksa. Emiten
    yang datanya bolong tetap terperiksa lewat jalur lain: kegagalan pengambilan diperiksa
    sebelum snapshot ditulis (`ingesti.periksa_ambang_gagal`), dan emiten yang barisnya ada
    tetapi tidak lengkap tetap muncul di peringkat selama 20 hari bersama itu terisi.

    Peringkat ini yang dipakai sebagai daftar kritis PRD 9.3/AC-1. Karena ia dihitung dari
    baris yang **sudah tersimpan**, emiten yang gagal diambil hari ini tetap muncul di sini
    dengan data terakhirnya — justru itulah yang membuat kegagalannya bisa dikenali sebagai
    kegagalan emiten teratas, bukan sebagai emiten yang kebetulan tidak ada.

    `sumber` menyaring peringkat ke satu label sumber; tanpa penyaringan, harga dua sumber akan
    tercampur dan peringkatnya bukan peringkat sumber mana pun.
    """
    syarat, argumen = _syarat_sumber(sumber, " WHERE ")
    tanggal = sambungan.execute(
        "SELECT DISTINCT tanggal FROM v_harga_harian_terkini" + syarat + " ORDER BY tanggal DESC LIMIT ?",
        (*argumen, metrik.ADTV_PERIODE),
    ).fetchall()
    if len(tanggal) < metrik.ADTV_PERIODE:
        return ()

    tanggal_terpilih = [baris[0] for baris in tanggal]
    tanda = ", ".join("?" for _ in tanggal_terpilih)
    syarat_sumber, _ = _syarat_sumber(sumber, " AND ")
    baris = sambungan.execute(
        "SELECT kode, AVG(nilai) AS adtv, COUNT(DISTINCT tanggal) AS hari"
        " FROM v_harga_harian_terkini"
        f" WHERE nilai IS NOT NULL AND tanggal IN ({tanda}){syarat_sumber}"
        " GROUP BY kode HAVING COUNT(DISTINCT tanggal) = ?"
        " ORDER BY adtv DESC, kode ASC",
        (*tanggal_terpilih, *argumen, len(tanggal_terpilih)),
    ).fetchall()

    hasil: list[PeringkatADTV] = []
    for satu in baris[:jumlah]:
        angka = _desimal(satu["adtv"])
        if angka is None:
            continue
        hasil.append(PeringkatADTV(kode=satu["kode"], adtv20=angka, hari_terpakai=int(satu["hari"])))
    return tuple(hasil)


def _penutupan_per_sumber(
    sambungan: sqlite3.Connection, tanggal: date, sumber: str | None = None
) -> dict[str, int | None]:
    """Penutupan terkini per emiten pada satu tanggal, untuk satu sumber atau seluruh sumber.

    Nilai `None` berarti barisnya ada tetapi penutupannya kosong. Itu dibedakan dari "emitennya
    tidak ada di sumber itu", sebab keduanya berakibat berbeda pada pemeriksaan.
    """
    syarat = "" if sumber is None else " AND sumber = ?"
    argumen: tuple[object, ...] = () if sumber is None else (sumber,)
    return {
        baris["kode"]: baris["close"]
        for baris in sambungan.execute(
            "SELECT kode, close FROM v_harga_harian_terkini WHERE tanggal = ?" + syarat,
            (tanggal.isoformat(), *argumen),
        )
    }


def _sumber_pada(
    sambungan: sqlite3.Connection, tanggal: date, selain: str | None = None
) -> tuple[str, ...]:
    """Label sumber yang punya bar pada tanggal itu, terurut; `selain` dibuang bila diisi."""
    return tuple(
        baris[0]
        for baris in sambungan.execute(
            "SELECT DISTINCT sumber FROM v_harga_harian_terkini WHERE tanggal = ? ORDER BY sumber",
            (tanggal.isoformat(),),
        )
        if baris[0] and baris[0] != selain
    )


def bandingkan_sumber_kedua(
    sambungan: sqlite3.Connection,
    *,
    tanggal_data: date,
    sumber_utama: str | potret.PilihanHarga | None = None,
    sumber_pembanding: str | None = None,
    jumlah: int = JUMLAH_CEK_SUMBER_KEDUA,
) -> LaporanPerbandingan:
    """Bandingkan penutupan emiten ber-ADTV20 tertinggi antara dua sumber (PRD 7.3).

    PRD menuntut perbandingan ini **tiap minggu**, dengan selisih di atas 1% ditandai. Yang
    dihitung di sini adalah perbandingannya: peringkat 20 emiten ber-ADTV20 tertinggi, selisih
    penutupan tiap emiten antara dua label sumber, dan temuannya.

    Kapan pemeriksaan ini dijalankan **tidak** disimpulkan di sini: itu bukan pertanyaan tentang
    isi basis data, dan menebaknya akan menjadi karangan. Yang menjawabnya adalah
    `catat_cek_sumber_kedua` (menulis peristiwanya saat cek benar-benar berjalan) dan
    `keadaan_cek_sumber_kedua` (membacanya kembali sebagai keadaan cadence).

    Bila harga pembanding belum pernah diimpor, hasilnya **bukan** "lulus": laporannya menyebut
    bahwa pemeriksaan belum dapat dijalankan beserta alasannya (aturan keras 7 dan 2).
    """
    peringkat = peringkat_adtv(sambungan, jumlah=jumlah, sumber=sumber_utama)
    # Penutupan pada `tanggal_data` hanya datang dari satu label, juga pada deret sambungan
    # (K97): sejak tanggal sambung label resminya, sehingga label riwayat menjadi pembanding (f).
    pilihan = potret.sebagai_pilihan(sumber_utama)
    sumber_utama = pilihan.label_pada(tanggal_data) if pilihan is not None else None
    tersedia = _sumber_pada(sambungan, tanggal_data, selain=sumber_utama)
    pembanding = sumber_pembanding
    if pembanding is None and tersedia:
        pembanding = tersedia[0]

    laporan = LaporanPerbandingan(
        tanggal_data=tanggal_data.isoformat(),
        sumber_utama=sumber_utama,
        sumber_pembanding=pembanding,
        sumber_tersedia=tersedia,
    )
    if not peringkat:
        laporan.belum_dapat_dijalankan.append(
            f"peringkat ADTV20 belum bisa dihitung: butuh {metrik.ADTV_PERIODE} hari bursa"
            + (f" dari sumber {sumber_utama!r}" if sumber_utama else "")
            + " yang sama-sama punya nilai transaksi"
        )
    if pembanding is None:
        laporan.belum_dapat_dijalankan.append(
            "harga dari sumber kedua belum ada di basis data. Cek sumber kedua (PRD 7.3) baru "
            "bisa dijalankan setelah harga pembanding diimpor lewat --impor dengan kolom "
            "`sumber` terisi; tanpa itu pemeriksaan ini **belum** dianggap lulus"
        )
        return laporan
    if pembanding == sumber_utama:
        # Sejak tanggal sambung (K97) label resmi adalah sumber utama hari itu; memintanya
        # sebagai pembanding berarti membandingkan sumber dengan dirinya sendiri.
        laporan.belum_dapat_dijalankan.append(
            f"sumber pembanding {pembanding!r} sama dengan sumber utama pada {tanggal_data}; "
            "perbandingan dengan dirinya sendiri tidak memeriksa apa pun"
        )
        return laporan

    utama = _penutupan_per_sumber(sambungan, tanggal_data, sumber_utama)
    lain = _penutupan_per_sumber(sambungan, tanggal_data, pembanding)

    diperiksa: list[BedaSumber] = []
    for satu in peringkat:
        if satu.kode not in utama or satu.kode not in lain:
            laporan.belum_dapat_dijalankan.append(
                f"{satu.kode} masuk peringkat ADTV20 tetapi tidak punya penutupan di kedua "
                f"sumber pada {tanggal_data} (utama: {'ada' if satu.kode in utama else 'tidak ada'}, "
                f"{pembanding}: {'ada' if satu.kode in lain else 'tidak ada'})"
            )
            continue
        tutup_utama, tutup_lain = utama[satu.kode], lain[satu.kode]
        if tutup_utama is None or tutup_lain is None:
            selisih = None
        elif tutup_utama == 0:
            # Pembagi nol: selisih relatif tidak bermakna. Dibiarkan None supaya dilaporkan
            # sebagai "tidak bisa dihitung", bukan menjadi angka tak hingga yang lolos diam-diam.
            selisih = None
        else:
            selisih = abs(Decimal(tutup_lain) - Decimal(tutup_utama)) / Decimal(tutup_utama)
        diperiksa.append(
            BedaSumber(
                kode=satu.kode,
                tanggal=tanggal_data.isoformat(),
                close_utama=int(tutup_utama or 0),
                close_pembanding=int(tutup_lain or 0),
                selisih=selisih,
            )
        )

    laporan.diperiksa = tuple(diperiksa)
    return laporan


def temuan_perbandingan(laporan: LaporanPerbandingan) -> list[Temuan]:
    """Ubah hasil cek sumber kedua menjadi temuan laporan mutu (PRD 7.3).

    Selisih di atas ambang menjadi `TAK_WAJAR` — nilainya ada tetapi tidak masuk akal untuk
    dua sumber yang seharusnya melaporkan pasar yang sama, dan PRD menuntutnya ditandai.
    """
    temuan = [
        Temuan(
            satu.kode,
            TAK_WAJAR,
            "beda_sumber_kedua",
            f"penutupan {satu.tanggal}: sumber utama {satu.close_utama} vs pembanding "
            f"{satu.close_pembanding} (selisih {satu.selisih:.2%}, ambang {AMBANG_BEDA_SUMBER:.0%})",
        )
        for satu in laporan.ditandai
        if satu.selisih is not None
    ]
    temuan.extend(
        Temuan(
            satu.kode,
            CATATAN,
            "beda_sumber_tak_terhitung",
            f"penutupan {satu.tanggal}: selisih tidak bisa dihitung karena salah satu "
            "penutupan nol atau kosong",
        )
        for satu in laporan.selisih_tak_terhitung
    )
    return temuan


# ---------------------------------------------------------------------------------------
# Cadence cek sumber kedua (PRD 7.3: "tiap minggu")
# ---------------------------------------------------------------------------------------


def catat_cek_sumber_kedua(
    sambungan: sqlite3.Connection,
    laporan: LaporanPerbandingan,
    *,
    momen: datetime | None = None,
) -> int:
    """Catat satu jalan cek sumber kedua sebagai peristiwa, lalu kembalikan `id_cek`-nya.

    Pencatatannya terjadi **saat cek dijalankan**, bukan disimpulkan belakangan dari isi basis
    data: hanya di sini yang tahu apakah perbandingannya benar-benar lengkap, sedangkan
    pemeriksaan yang cuma "ada barisnya" tidak membuktikan apa pun (lihat `keadaan_cek_sumber_kedua`).

    `momen` hanya untuk pengujian dan pemanggilan ulang yang sadar waktu; bawaannya jam sistem.
    """
    cakupan = CAKUPAN_LENGKAP if laporan.lengkap else CAKUPAN_BELUM_LENGKAP
    # Sebab utamanya disimpan supaya peringatan berikutnya bisa menyebut **kenapa** cek terakhir
    # belum lengkap, bukan hanya bahwa ia belum lengkap. Dipotong supaya kolomnya tetap terbaca.
    catatan = "; ".join(laporan.belum_dapat_dijalankan[:5]) or None

    from mejasaham import db  # impor lokal: hanya jalur tulis ini yang memakai lapisan basis data

    with db.tulis(sambungan) as koneksi:
        kursor = koneksi.execute(
            "INSERT INTO cek_sumber_kedua ("
            " dijalankan_pada, tanggal_data, sumber_utama, sumber_pembanding,"
            " jumlah_diperiksa, jumlah_ditandai, jumlah_tak_terhitung, jumlah_belum_dapat,"
            " cakupan, catatan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                db.waktu_iso(momen),
                laporan.tanggal_data,
                laporan.sumber_utama,
                laporan.sumber_pembanding,
                len(laporan.diperiksa),
                len(laporan.ditandai),
                len(laporan.selisih_tak_terhitung),
                len(laporan.belum_dapat_dijalankan),
                cakupan,
                catatan,
            ),
        )
        id_cek = int(kursor.lastrowid or 0)
    return id_cek


def keadaan_cek_sumber_kedua(
    sambungan: sqlite3.Connection,
    *,
    momen: date | None = None,
) -> KeadaanCekSumberKedua:
    """Keadaan cadence cek sumber kedua dibandingkan `momen` (bawaannya hari ini).

    Dibaca dari **catatan peristiwa** di tabel `cek_sumber_kedua`, bukan disimpulkan dari
    keberadaan harga pembanding: harga pembanding bisa diimpor berkali-kali tanpa satu pun
    perbandingan dijalankan, dan keadaan itu justru yang harus terlihat.

    Tiga hal yang sengaja dibedakan, karena tindakan yang benar untuk masing-masing berbeda:
    belum pernah dijalankan, sudah lewat batas, dan **tidak dapat dinilai** (tanggal catatannya
    di depan hari ini, atau tidak terbaca — jam sistem mundur, atau barisnya disunting tangan).
    Yang terakhir tidak dianggap lulus.

    Urutannya diambil dari `id_cek` — urutan **pencatatan** — bukan dari teks `dijalankan_pada`:
    cap waktu ISO dengan offset berbeda tidak terurut secara leksikografis, dan urutan yang salah
    akan menilai cadence dari cek yang bukan yang terakhir. Tabelnya append-only, jadi urutan
    pencatatan memang urutan kejadiannya.
    """
    hari_ini = _sebagai_tanggal(momen)

    terakhir = sambungan.execute(
        "SELECT id_cek, dijalankan_pada, cakupan, catatan FROM cek_sumber_kedua"
        " ORDER BY id_cek DESC LIMIT 1"
    ).fetchone()
    lengkap = sambungan.execute(
        "SELECT id_cek, dijalankan_pada FROM cek_sumber_kedua WHERE cakupan = ?"
        " ORDER BY id_cek DESC LIMIT 1",
        (CAKUPAN_LENGKAP,),
    ).fetchone()

    terakhir_dijalankan = str(terakhir["dijalankan_pada"]) if terakhir else None
    cakupan_terakhir = str(terakhir["cakupan"]) if terakhir else None
    catatan_terakhir = (terakhir["catatan"] or None) if terakhir else None
    terakhir_lengkap = str(lengkap["dijalankan_pada"]) if lengkap else None
    # Percobaan terakhir "belum lengkap" bila pencatatan terakhir bukan pencatatan lengkap
    # terakhir. Dibandingkan lewat `id_cek`, bukan lewat cap waktunya (lihat catatan di atas).
    percobaan_belum_lengkap = bool(
        terakhir is not None
        and (lengkap is None or terakhir["id_cek"] != lengkap["id_cek"])
        and cakupan_terakhir == CAKUPAN_BELUM_LENGKAP
    )

    umum = {
        "batas_hari": JEDA_CEK_SUMBER_KEDUA_HARI,
        "terakhir_dijalankan": terakhir_dijalankan,
        "cakupan_terakhir": cakupan_terakhir,
        "catatan_terakhir": catatan_terakhir,
        "terakhir_lengkap": terakhir_lengkap,
    }
    if terakhir_lengkap is None:
        return KeadaanCekSumberKedua(
            status=STATUS_BELUM_PERNAH,
            percobaan_terakhir_belum_lengkap=percobaan_belum_lengkap,
            **umum,
        )

    tanggal = _tanggal_dari_iso(terakhir_lengkap)
    if tanggal is None:
        return KeadaanCekSumberKedua(
            status=STATUS_TIDAK_DAPAT_DINILAI,
            alasan=(
                f"tanggal catatan cek {terakhir_lengkap!r} tidak terbaca sebagai tanggal "
                "ISO-8601; periksa barisnya di tabel cek_sumber_kedua"
            ),
            **umum,
        )

    selisih = (hari_ini - tanggal).days
    if selisih < 0:
        return KeadaanCekSumberKedua(
            status=STATUS_TIDAK_DAPAT_DINILAI,
            alasan=(
                f"catatan cek terakhir bertanggal {terakhir_lengkap} — {abs(selisih)} hari di "
                f"depan {hari_ini.isoformat()}; jam sistem atau catatannya perlu diperiksa"
            ),
            hari_sejak_lengkap=selisih,
            **umum,
        )

    return KeadaanCekSumberKedua(
        status=STATUS_TEPAT_WAKTU if selisih <= JEDA_CEK_SUMBER_KEDUA_HARI else STATUS_LEWAT,
        hari_sejak_lengkap=selisih,
        percobaan_terakhir_belum_lengkap=percobaan_belum_lengkap,
        **umum,
    )


def _tanggal_dari_iso(teks: str | None) -> date | None:
    waktu = _waktu_dari_iso(teks)
    return waktu.date() if waktu is not None else None


def _waktu_dari_iso(teks: str | None) -> datetime | None:
    if not teks:
        return None
    try:
        return datetime.fromisoformat(teks)
    except ValueError:
        return None


def _sebagai_tanggal(momen: date | datetime | None) -> date:
    """Hari ini menurut pemanggil; `datetime` dipotong tanggalnya, `None` berarti jam sistem."""
    if momen is None:
        return date.today()
    return momen.date() if isinstance(momen, datetime) else momen


def _tanggal_tampil(teks: str | None) -> str:
    """Tanggal bagian depan cap waktu ISO, apa adanya; cap waktu yang aneh dibiarkan terlihat."""
    if not teks:
        return "(tidak ada)"
    return teks.split("T", 1)[0]


def hari_bursa_terakhir(sambungan: sqlite3.Connection, sampai: date | None = None) -> str | None:
    """Tanggal hari bursa terakhir yang **sudah lewat** (U5, T30) — untuk dibaca modul lain.

    Pembungkus publik dari `_hari_bursa_terakhir`: pertanyaan "hari bursa terakhir yang mana"
    hanya boleh punya satu jawaban di seluruh aplikasi (T26), dan dasbor membutuhkannya untuk
    mengatakan snapshotnya basi atau tidak (AC-8) tanpa menghitung ulang dari kalender.
    """
    return _hari_bursa_terakhir(sambungan, sampai)


def _hari_bursa_terakhir(sambungan: sqlite3.Connection, sampai: date | None = None) -> str | None:
    """Tanggal hari bursa terakhir menurut `kalender_bursa` (U5); None bila kalendernya kosong.

    Sengaja **tidak** menebak dari hari kerja biasa: kalender bursa punya hari libur yang tidak
    mengikuti kalender umum, dan menebaknya akan membuat peringatan "snapshot basi" salah.

    `sampai` membatasi pencarian pada hari yang sudah lewat. Kalender yang diisi dari pengumuman
    tahunan memuat hari bursa sampai akhir tahun, dan hari yang belum terjadi tidak boleh dipakai
    menyebut snapshot sekarang basi.
    """
    syarat = "hari_bursa = 1"
    argumen: tuple[object, ...] = ()
    if sampai is not None:
        syarat += " AND tanggal <= ?"
        argumen = (sampai.isoformat(),)
    baris = sambungan.execute(
        f"SELECT MAX(tanggal) FROM v_kalender_bursa_terkini WHERE {syarat}", argumen
    ).fetchone()
    return baris[0] if baris and baris[0] else None


def _aksi_per_kode(sambungan: sqlite3.Connection) -> dict[str, list[tuple[date, str, Decimal | None]]]:
    """Aksi korporasi terkini per kode, untuk membedakan lonjakan wajar dari yang mencurigakan."""
    hasil: dict[str, list[tuple[date, str, Decimal | None]]] = {}
    for baris in sambungan.execute(
        "SELECT kode, tanggal, jenis, rasio_lama, rasio_baru, dividen_per_saham"
        " FROM v_aksi_korporasi_terkini"
    ):
        try:
            tanggal = date.fromisoformat(baris["tanggal"])
        except ValueError:
            continue
        faktor: Decimal | None = None
        if baris["rasio_lama"] and baris["rasio_baru"]:
            faktor = Decimal(baris["rasio_baru"]) / Decimal(baris["rasio_lama"])
        hasil.setdefault(baris["kode"], []).append((tanggal, baris["jenis"], faktor))
    return hasil


def _catatan_mutu_di_sekitar(
    sambungan: sqlite3.Connection, kode: str, tanggal: date, diketahui_sampai: date
) -> tuple[sqlite3.Row, ...]:
    """Konteks aksi mutu yang berlaku dekat lonjakan dan sudah diketahui saat laporan dibuat."""
    hasil: list[sqlite3.Row] = []
    for baris in sambungan.execute(
        "SELECT kode, tanggal_efektif, instrumen_aksi, ringkasan_bukti, sumber_url, sumber, diketahui_pada "
        "FROM catatan_aksi_mutu AS r WHERE kode = ? AND substr(r.diketahui_pada, 1, 10) <= ? "
        "AND NOT EXISTS (SELECT 1 FROM catatan_aksi_mutu AS lain "
        "WHERE lain.kode = r.kode AND lain.tanggal_efektif = r.tanggal_efektif "
        "AND lain.instrumen_aksi = r.instrumen_aksi "
        "AND substr(lain.diketahui_pada, 1, 10) <= ? AND lain.diketahui_pada > r.diketahui_pada) "
        "ORDER BY tanggal_efektif, instrumen_aksi",
        (kode, diketahui_sampai.isoformat(), diketahui_sampai.isoformat()),
    ):
        try:
            tanggal_aksi = date.fromisoformat(baris["tanggal_efektif"])
        except ValueError as galat:
            raise ValueError(
                f"catatan_aksi_mutu memuat tanggal efektif tidak sah untuk {kode}: "
                f"{baris['tanggal_efektif']!r}"
            ) from galat
        if abs((tanggal_aksi - tanggal).days) <= HARI_SEKITAR_AKSI:
            hasil.append(baris)
    return tuple(hasil)


def _ada_aksi_di_sekitar(
    aksi: Sequence[tuple[date, str, Decimal | None]], tanggal: date, jenis: Iterable[str] | None = None
) -> tuple[date, str, Decimal | None] | None:
    diizinkan = set(jenis) if jenis is not None else None
    for satu_tanggal, satu_jenis, faktor in aksi:
        if diizinkan is not None and satu_jenis not in diizinkan:
            continue
        if abs((satu_tanggal - tanggal).days) <= HARI_SEKITAR_AKSI:
            return satu_tanggal, satu_jenis, faktor
    return None


def _lonjakan(faktor: Decimal | None) -> bool:
    if faktor is None:
        return False
    return faktor > AMBANG_LONJAKAN or faktor < (1 / AMBANG_LONJAKAN)


def _baris_per_kode(baris_semua: Sequence[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    """Kelompokkan baris terkini per emiten untuk pemeriksaan yang bersifat per emiten.

    Dipisah dari lintasan utama supaya pemeriksaan yang butuh "seluruh baris emiten ini"
    (seperti penanda penyesuaian sumber) tidak memaksa lintasan itu menyimpan semua baris.
    """
    hasil: dict[str, list[Mapping[str, object]]] = {}
    for baris in baris_semua:
        hasil.setdefault(str(baris["kode"]), []).append(baris)
    return hasil


def periksa(
    sambungan: sqlite3.Connection,
    *,
    tanggal_data: date,
    jumlah_gagal: int = 0,
    jumlah_bar_mentah: int | None = None,
    sumber: str | potret.PilihanHarga | None = None,
    momen: date | None = None,
) -> LaporanMutu:
    """Periksa satu snapshot dan kembalikan laporannya (PRD 7.3).

    `sumber` melakukan dua hal sekaligus, dan keduanya perlu:

    * **Menyaring lintasan utama** ke satu label sumber. Bila harga dua sumber ada di basis data
      (harga tidak resmi + harga pembanding hasil impor), memeriksanya dalam satu lintasan akan
      membandingkan baris sumber yang berbeda sebagai "harga sebelumnya" — dan selisih antar
      sumber muncul sebagai lonjakan harga yang tidak pernah terjadi.
    * **Menandai laporan** yang seluruhnya berasal dari sumber tidak resmi; PRD 7.3 menuntut
      sumbernya **tertulis** di laporan mutu, bukan hanya di log.

    `momen` adalah "hari ini" menurut pemanggil; bawaannya jam sistem. Ia dipakai menilai
    cadence cek sumber kedua (PRD 7.3) **dan** membatasi "hari bursa terakhir" pada hari yang
    sudah lewat. Yang kedua itu perlu sejak `--ambil-kalender` mengisi kalender satu tahun penuh
    dari pengumuman KSEI: kalender memang memuat hari bursa sampai akhir tahun, tetapi hari yang
    belum terjadi tidak bisa membuat snapshot hari ini disebut basi. Tanpa pembatasan itu,
    snapshot yang benar akan diperingatkan basi setiap hari sampai Desember.
    """
    tanggal_teks = tanggal_data.isoformat()
    hari_bursa = _hari_bursa_terakhir(sambungan, sampai=_sebagai_tanggal(momen))
    aksi = _aksi_per_kode(sambungan)

    # (0) Peringkat ADTV20 (PRD 7.3 & 9.3). Dihitung **sebelum** lintasan utama karena ia yang
    # menentukan emiten mana yang tidak boleh bolong.
    peringkat = peringkat_adtv(sambungan, jumlah=JUMLAH_KRITIS, sumber=sumber)

    # Lintasan utama dibatasi pada satu label sumber bila diminta. Dua sumber yang tercampur
    # dalam satu lintasan akan saling dibandingkan sebagai "baris sebelumnya milik emiten yang
    # sama", sehingga selisih antar sumber muncul sebagai lonjakan harga yang tidak pernah ada.
    pilihan = potret.sebagai_pilihan(sumber)
    syarat_sumber, argumen_baris = _syarat_sumber(pilihan, " WHERE ")
    jumlah_bar_terkini = int(
        sambungan.execute(
            "SELECT COUNT(*) FROM v_harga_harian_terkini" + syarat_sumber, argumen_baris
        ).fetchone()[0]
    )
    if jumlah_bar_mentah is None:
        jumlah_bar_mentah = int(sambungan.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0])

    # Seluruh bar terkini, terurut per kode lalu tanggal: satu lintasan untuk semua pemeriksaan
    # per emiten, sehingga laporan tetap cepat pada 800+ emiten (PRD 9.13).
    baris_semua = sambungan.execute(
        "SELECT kode, tanggal, open, high, low, close, volume, penyesuaian_sumber"
        " FROM v_harga_harian_terkini" + syarat_sumber + " ORDER BY kode, tanggal",
        argumen_baris,
    ).fetchall()

    temuan: list[Temuan] = []
    keadaan: dict[str, KeadaanEmiten] = {}
    jumlah_emiten = 0
    sebelumnya: dict[str, tuple[date, Decimal | None]] = {}

    for baris in baris_semua:
        kode = baris["kode"]
        if kode not in keadaan:
            jumlah_emiten += 1
            keadaan[kode] = KeadaanEmiten(
                kode=kode, tanggal_terakhir=None, jumlah_bar=0, bolong=False, tak_wajar=False, catatan=0
            )
        try:
            tanggal = date.fromisoformat(baris["tanggal"])
        except ValueError:
            temuan.append(
                Temuan(kode, TAK_WAJAR, "tanggal_tidak_sah", f"tanggal {baris['tanggal']!r} tidak dikenali")
            )
            continue

        tutup = _desimal(baris["close"])
        volume = _desimal(baris["volume"])

        # (1) Harga 0 / harga hilang padahal volumenya ada → nilai tidak wajar (PRD 7.3).
        if tutup is not None and tutup == 0:
            temuan.append(Temuan(kode, TAK_WAJAR, "harga_nol", f"harga penutupan 0 pada {tanggal}"))
        elif tutup is None and baris["close"] is not None:
            temuan.append(
                Temuan(kode, TAK_WAJAR, "harga_tidak_terbaca", f"harga penutupan {baris['close']!r} pada {tanggal}")
            )
        elif tutup is None:
            temuan.append(Temuan(kode, BOLONG, "harga_kosong", f"harga penutupan kosong pada {tanggal}"))
        if volume is None and baris["volume"] is None:
            temuan.append(Temuan(kode, BOLONG, "volume_kosong", f"volume kosong pada {tanggal}"))

        # (2) Lonjakan mencurigakan tanpa aksi korporasi (PRD 7.3). Selalu dibandingkan dengan
        # bar **sebelumnya milik emiten yang sama**; kalau ada aksi korporasi di sekitarnya
        # (split/reverse split yang menjelaskan perubahan skala, atau dividen yang menjelaskan
        # penurunan), yang dilaporkan hanya catatan — bukan tuduhan data rusak.
        #
        # K8/C10 membalik satu hal di sini: bila barisnya **dinyatakan sudah disesuaikan sumber**,
        # harga justru seharusnya sambung di sekitar tanggal split. Lonjakan di situ berarti
        # sumbernya sendiri tidak konsisten (mis. berkas impor bercampur basis penyesuaian), jadi
        # aksi korporasi tidak boleh lagi dipakai memaafkannya.
        lalu = sebelumnya.get(kode)
        if lalu is not None and tutup is not None and lalu[1] not in (None, 0):
            faktor = tutup / lalu[1]
            if _lonjakan(faktor):
                catatan_mutu = _catatan_mutu_di_sekitar(
                    sambungan, kode, tanggal, _sebagai_tanggal(momen)
                )
                penjelas = _ada_aksi_di_sekitar(aksi.get(kode, ()), tanggal, ("split", "reverse_split"))
                sudah_disesuaikan = baris["penyesuaian_sumber"] in SUDAH_DITERAPKAN_SUMBER
                if penjelas is not None and sudah_disesuaikan:
                    temuan.append(
                        Temuan(
                            kode,
                            TAK_WAJAR,
                            "lonjakan_pada_baris_tersesuaikan",
                            f"harga {lalu[1]} -> {tutup} ({faktor:.2f}x) pada {tanggal} bertepatan "
                            f"dengan {penjelas[1]} {penjelas[0]}, padahal baris ini dinyatakan "
                            "sudah disesuaikan sumber — harga semestinya sambung di sekitar "
                            "tanggal itu; periksa apakah berkas/sumbernya bercampur basis",
                        )
                    )
                    keadaan[kode] = _tandai(keadaan[kode], tak_wajar=True)
                elif penjelas is not None:
                    keadaan[kode] = _tambah_catatan(
                        keadaan[kode],
                        temuan,
                        kode,
                        "lonjakan_dijelaskan_aksi",
                        f"harga {lalu[1]} -> {tutup} ({faktor:.2f}x) bertepatan dengan "
                        f"{penjelas[1]} pada {penjelas[0]}",
                    )
                else:
                    dividen = _ada_aksi_di_sekitar(aksi.get(kode, ()), tanggal, ("dividen",))
                    if dividen is not None and faktor < 1:
                        keadaan[kode] = _tambah_catatan(
                            keadaan[kode],
                            temuan,
                            kode,
                            "penurunan_dijelaskan_dividen",
                            f"harga {lalu[1]} -> {tutup} bertepatan dengan dividen pada {dividen[0]}",
                        )
                    else:
                        temuan.append(
                            Temuan(
                                kode,
                                TAK_WAJAR,
                                "lonjakan_tanpa_aksi",
                                f"harga {lalu[1]} -> {tutup} ({faktor:.2f}x) pada {tanggal} "
                                "tanpa aksi korporasi yang menjelaskannya",
                            )
                        )
                        keadaan[kode] = _tandai(keadaan[kode], tak_wajar=True)
                for catatan in catatan_mutu:
                    keadaan[kode] = _tambah_catatan(
                        keadaan[kode],
                        temuan,
                        kode,
                        "konteks_aksi_mutu",
                        f"lonjakan pada {tanggal} berdekatan dengan {catatan['instrumen_aksi']} "
                        f"({catatan['tanggal_efektif']}): {catatan['ringkasan_bukti']}; "
                        f"sumber: {catatan['sumber']} — {catatan['sumber_url']}. "
                        "Konteks ini tidak memverifikasi OHLCV atau mengubah status temuan harga.",
                    )
        if tutup is not None and tutup > 0:
            sebelumnya[kode] = (tanggal, tutup)

        # `keadaan[kode]` disalin lalu diperbarui, bukan dibangun ulang dari nol: penandaan
        # "tak wajar" yang baru saja dipasang pemeriksaan lonjakan tidak boleh terhapus di sini.
        keadaan[kode] = _maju(keadaan[kode], tanggal)

    # (3) Data hari terakhir kosong → emiten "data bolong", keluar dari peringkat (PRD 7.3, AC-1).
    for kode, satu in keadaan.items():
        if satu.tanggal_terakhir != tanggal_teks:
            temuan.append(
                Temuan(
                    kode,
                    BOLONG,
                    "tidak_ada_bar_hari_terakhir",
                    f"bar terakhir {satu.tanggal_terakhir or '(tidak ada)'}, sedangkan tanggal snapshot {tanggal_teks}",
                )
            )
            keadaan[kode] = KeadaanEmiten(
                kode=kode,
                tanggal_terakhir=satu.tanggal_terakhir,
                jumlah_bar=satu.jumlah_bar,
                bolong=True,
                tak_wajar=satu.tak_wajar,
                catatan=satu.catatan,
            )

    # (3b) Penanda penyesuaian sumber yang belum dinyatakan, padahal emiten itu punya aksi
    # penyesuaian harga (K8/C10). Dilaporkan **satu kali per emiten**, bukan per baris: 1.200
    # baris tanpa penanda adalah satu keadaan, bukan 1.200 temuan.
    #
    # Inilah yang dijanjikan K8: "baris tanpa penanda ditandai di laporan mutu, bukan ditebak".
    # Akibatnya nyata dan disebut apa adanya — metrik harga emiten itu berhenti dihitung
    # (`penyesuaian.sesuaikan` menolak menebak), sehingga ia juga tidak bisa diperingkat.
    for kode, deret in _baris_per_kode(baris_semua).items():
        ada_aksi = [
            satu
            for satu in aksi.get(kode, ())
            if satu[1] in ("split", "reverse_split", "right_issue")
        ]
        if not ada_aksi:
            continue
        tanpa_penanda = sum(1 for satu in deret if satu["penyesuaian_sumber"] is None)
        if tanpa_penanda == 0:
            continue
        jenis_aksi = ", ".join(sorted({satu[1] for satu in ada_aksi}))
        keadaan[kode] = _tambah_catatan(
            keadaan[kode],
            temuan,
            kode,
            "penyesuaian_sumber_belum_dinyatakan",
            f"{tanpa_penanda} dari {len(deret)} baris belum menyatakan penyesuaian_sumber, "
            f"padahal emiten ini punya aksi {jenis_aksi}; metrik harganya berhenti dihitung "
            "sampai penandanya dinyatakan (K8/C10), sehingga emiten ini tidak bisa diperingkat",
        )

    # (3b2) Gerbang sambungan dan hari bolong (K97 b, d). Penutupan yang berbeda antara dua
    # sumber pada hari tumpang-tindih adalah cacat data → tak wajar, per emiten. Tumpang-tindih
    # yang kurang bukan cacat data melainkan bukti yang belum cukup, dan biasanya mengenai semua
    # emiten sekaligus (berkasnya belum diunggah) → satu catatan, bukan ratusan baris.
    keadaan_sambungan = (
        potret.periksa_sambungan(sambungan, pilihan, tanggal_data=tanggal_data)
        if pilihan is not None
        else None
    )
    if keadaan_sambungan is not None:
        for kode, alasan in keadaan_sambungan.ditolak.items():
            if kode not in keadaan_sambungan.beda:
                continue
            temuan.append(Temuan(kode, TAK_WAJAR, "sambungan_beda_harga", alasan + "; metrik harganya tidak dihitung"))
            if kode in keadaan:
                keadaan[kode] = _tandai(keadaan[kode], tak_wajar=True)
        kurang = sorted(set(keadaan_sambungan.ditolak) - set(keadaan_sambungan.beda))
        temuan.append(
            Temuan(
                "-",
                CATATAN,
                "gerbang_sambungan",
                keadaan_sambungan.ringkas()
                + (
                    f"; {len(kurang)} emiten kurang hari tumpang-tindih (minimal "
                    f"{potret.HARI_TUMPANG_TINDIH_MINIMUM}) sehingga metrik harganya tidak "
                    f"dihitung: {', '.join(kurang[:10])}" + (" ..." if len(kurang) > 10 else "")
                    if kurang
                    else ""
                ),
            )
        )
        if keadaan_sambungan.kalender_kurang is not None or keadaan_sambungan.hari_bolong:
            temuan.append(
                Temuan(
                    "-",
                    CATATAN,
                    "hari_bolong_sambungan",
                    keadaan_sambungan.sementara
                    or (
                        f"{len(keadaan_sambungan.hari_bolong)} hari bursa sejak tanggal sambung "
                        f"tanpa berkas {pilihan.resmi if pilihan else ''}, di luar jendela metrik "
                        f"({', '.join(satu.isoformat() for satu in keadaan_sambungan.hari_bolong[:5])})"
                    ),
                )
            )

    # (3c) Peringkat ADTV20 sebagai fakta laporan, dan emiten kritis yang bolong.
    #
    # Dua pemeriksaan yang lama tertunda karena "ADTV20 baru ada di Tahap 1" berhenti di sini:
    # peringkatnya kini bisa dihitung, jadi 50 emiten teratas bisa dinamai — dan emiten teratas
    # yang datanya bolong tidak lagi lewat tanpa suara. Yang **belum** bisa dijalankan hanyalah
    # perbandingan ke sumber kedua, dan alasannya dilaporkan sebagai belum-diperiksa, bukan lulus.
    if peringkat:
        temuan.append(
            Temuan(
                "-",
                CATATAN,
                "peringkat_adtv20",
                f"{len(peringkat)} emiten diperingkat menurut ADTV20 ({metrik.ADTV_PERIODE} hari "
                f"bursa); {JUMLAH_KRITIS} teratas: " + ", ".join(satu.kode for satu in peringkat[:10])
                + (" ..." if len(peringkat) > 10 else ""),
            )
        )
        for satu in peringkat:
            if satu.kode not in keadaan:
                temuan.append(
                    Temuan(
                        satu.kode,
                        BOLONG,
                        "kritis_tidak_ada_bar",
                        f"termasuk {JUMLAH_KRITIS} emiten ber-ADTV20 tertinggi tetapi tidak punya "
                        f"bar harga sama sekali pada sumber {pilihan.label if pilihan else '(semua sumber)'}; snapshot "
                        "ditolak menurut PRD 9.3/AC-1",
                    )
                )
                keadaan[satu.kode] = KeadaanEmiten(
                    kode=satu.kode,
                    tanggal_terakhir=None,
                    jumlah_bar=0,
                    bolong=True,
                    tak_wajar=False,
                    catatan=0,
                )
                continue
            if not (keadaan[satu.kode].bolong or keadaan[satu.kode].tak_wajar):
                continue
            alasan = "datanya bolong" if keadaan[satu.kode].bolong else "datanya ditandai tak wajar"
            temuan.append(
                Temuan(
                    satu.kode,
                    BOLONG,
                    "kritis_bermasalah",
                    f"termasuk {JUMLAH_KRITIS} emiten ber-ADTV20 tertinggi tetapi {alasan}; "
                    "snapshot ditolak menurut PRD 9.3/AC-1",
                )
            )

    # (4) Snapshot basi (AC-8), dan kalender yang belum memuat tanggal snapshot (U5).
    #
    # Arah perbandingannya penting dan mudah terbalik:
    #   * kalender memuat hari bursa yang LEBIH BARU dari data  -> snapshotnya basi (AC-8),
    #     karena ada hari bursa yang sudah lewat tetapi belum punya data;
    #   * kalender berhenti SEBELUM tanggal snapshot            -> kalendernya yang ketinggalan.
    #     Ini **bukan** snapshot basi: snapshot justru yang lebih tahu. Menuduhnya basi akan
    #     memunculkan peringatan yang salah setiap kali kalender belum diperbarui, dan
    #     peringatan yang sering salah akan berhenti dibaca orang.
    if hari_bursa is None:
        temuan.append(
            Temuan(
                "-",
                CATATAN,
                "kalender_bursa_kosong",
                "kalender bursa belum diisi, sehingga \"hari bursa terakhir\" dan peringatan "
                "snapshot basi belum bisa dihitung (U5)",
            )
        )
    elif hari_bursa > tanggal_teks:
        temuan.append(
            Temuan(
                "-",
                CATATAN,
                "snapshot_basi",
                f"hari bursa terakhir {hari_bursa}, sedangkan snapshot ini {tanggal_teks}; "
                "layar akan menampilkan peringatan snapshot basi (AC-8)",
            )
        )
    elif hari_bursa < tanggal_teks:
        temuan.append(
            Temuan(
                "-",
                CATATAN,
                "kalender_belum_memuat",
                f"kalender bursa berhenti di {hari_bursa}, sedangkan snapshot ini {tanggal_teks}; "
                "perbarui kalender bursa supaya status hari bursa bisa diverifikasi (U5)",
            )
        )

    # (5) Sumber tidak resmi diberi label (PRD 7.2, 7.3). Tuntutan pemeriksaannya sendiri
    # dilaporkan di (7); mengulang kalimat yang sama di dua temuan membuat yang penting
    # tenggelam di antara salinannya.
    if pilihan is not None and pilihan.dasar == SUMBER_YFINANCE:
        # K97 (e): selama riwayat yfinance masih dibaca, labelnya tetap tampil — juga sesudah
        # tanggal sambung, karena metrik berjendela panjang masih memakai bar sebelum itu.
        bagian = (
            f"harga sebelum {pilihan.sejak.isoformat()} berasal dari sumber tidak resmi "
            f"({pilihan.dasar}); sejak itu dari {pilihan.resmi}"
            if pilihan.tersambung and pilihan.sejak is not None
            else f"seluruh harga snapshot ini berasal dari sumber tidak resmi ({pilihan.dasar})"
        )
        temuan.append(
            Temuan(
                "-",
                CATATAN,
                "sumber_tidak_resmi",
                f"{bagian}; jangan disebarkan dan bukan untuk tujuan komersial (K7). Pemeriksaan "
                "silang yang dituntut PRD 7.3 keadaannya ada di temuan cek_sumber_kedua_*",
            )
        )

    # (6) Suspensi/notasi yang belum diperbarui pada hari bursa (PRD 7.3).
    ada_notasi = int(sambungan.execute("SELECT COUNT(*) FROM v_notasi_khusus_terkini").fetchone()[0])
    if ada_notasi == 0:
        temuan.append(
            Temuan(
                "-",
                CATATAN,
                "notasi_khusus_kosong",
                "tidak ada data suspensi/UMA/papan pemantauan; emiten tanpa penanda ini "
                "berstatus \"belum terverifikasi\" dan tidak dijadikan kandidat otomatis (PRD 7.3)",
            )
        )

    # (7) Cadence cek sumber kedua (PRD 7.3: "tiap minggu"). Yang dibaca di sini adalah catatan
    # peristiwa yang ditulis saat ceknya benar-benar dijalankan (`catat_cek_sumber_kedua`),
    # bukan kesimpulan dari ada-tidaknya harga pembanding: pembanding bisa diimpor berkali-kali
    # tanpa satu pun perbandingan dijalankan, dan justru keadaan itu yang harus terlihat.
    cadence = keadaan_cek_sumber_kedua(sambungan, momen=momen)
    if not cadence.lulus:
        temuan.append(cadence.temuan())

    laporan = LaporanMutu(
        tanggal_data=tanggal_teks,
        hari_bursa_terakhir=hari_bursa,
        jumlah_emiten=jumlah_emiten,
        jumlah_bar_mentah=jumlah_bar_mentah,
        jumlah_bar_terkini=jumlah_bar_terkini,
        jumlah_gagal_ambil=jumlah_gagal,
        temuan=temuan,
        emiten_bermasalah=keadaan,
        peringkat_adtv=peringkat,
        pemeriksaan_belum_dapat_dijalankan=[
            f"cek sumber kedua atas {JUMLAH_CEK_SUMBER_KEDUA} emiten ber-ADTV20 tertinggi "
            "(PRD 7.3) tidak dijalankan oleh laporan ini; "
            + (
                cadence.ringkas()
                if cadence.lulus
                else "keadaannya dilaporkan sebagai temuan tersendiri di daftar temuan"
            )
        ],
        cek_sumber_kedua=cadence,
    )
    return laporan


def _tandai(satu: KeadaanEmiten, *, bolong: bool = False, tak_wajar: bool = False) -> KeadaanEmiten:
    return KeadaanEmiten(
        kode=satu.kode,
        tanggal_terakhir=satu.tanggal_terakhir,
        jumlah_bar=satu.jumlah_bar,
        bolong=satu.bolong or bolong,
        tak_wajar=satu.tak_wajar or tak_wajar,
        catatan=satu.catatan,
    )


def _maju(satu: KeadaanEmiten, tanggal: date) -> KeadaanEmiten:
    """Catat bahwa emiten ini punya satu bar lagi pada `tanggal`."""
    return KeadaanEmiten(
        kode=satu.kode,
        tanggal_terakhir=tanggal.isoformat(),
        jumlah_bar=satu.jumlah_bar + 1,
        bolong=satu.bolong,
        tak_wajar=satu.tak_wajar,
        catatan=satu.catatan,
    )


def _tambah_catatan(
    satu: KeadaanEmiten, temuan: list[Temuan], kode: str, jenis: str, keterangan: str
) -> KeadaanEmiten:
    temuan.append(Temuan(kode, CATATAN, jenis, keterangan))
    return KeadaanEmiten(
        kode=satu.kode,
        tanggal_terakhir=satu.tanggal_terakhir,
        jumlah_bar=satu.jumlah_bar,
        bolong=satu.bolong,
        tak_wajar=satu.tak_wajar,
        catatan=satu.catatan + 1,
    )


# ---------------------------------------------------------------------------------------
# Ekspor laporan
# ---------------------------------------------------------------------------------------

#: Kepala CSV laporan mutu. Dipisah `;` + BOM UTF-8 supaya terbaca benar di Excel Indonesia
#: (U11) — laporan ini memang untuk dibaca manusia di luar aplikasi.
KEPALA_CSV = ("tingkat;jenis;kode;keterangan",)


def csv_laporan(laporan: LaporanMutu) -> str:
    """Laporan mutu sebagai CSV yang siap dibuka di Excel Indonesia (U11)."""
    from mejasaham import db  # impor lokal: db hanya dipakai untuk penulisan waktu

    baris = [
        f"# laporan mutu data Meja Saham",
        f"# snapshot;{laporan.tanggal_data}",
        f"# hari_bursa_terakhir;{laporan.hari_bursa_terakhir or '(kalender belum diisi)'}",
        f"# jumlah_emiten;{laporan.jumlah_emiten}",
        f"# bar_masuk;{laporan.jumlah_bar_mentah}",
        f"# bar_terkini;{laporan.jumlah_bar_terkini}",
        f"# gagal_diambil;{laporan.jumlah_gagal_ambil}",
        f"# dibuat_pada;{db.waktu_iso()}",
        "# Isi berkas ini bukan nasihat investasi (PRD 9.10).",
        *KEPALA_CSV,
    ]
    terurut = sorted(laporan.temuan, key=lambda satu: (URUTAN_TINGKAT[satu.tingkat], satu.kode, satu.jenis))
    for satu in terurut:
        baris.append(f"{satu.tingkat};{satu.jenis};{satu.kode};{_aman_csv(satu.keterangan)}")
    for satu in laporan.pemeriksaan_belum_dapat_dijalankan:
        baris.append(f"belum_diperiksa;belum_dapat_dijalankan;-;{_aman_csv(satu)}")
    return "\n".join(baris) + "\n"


def _aman_csv(teks: str) -> str:
    """Buang pemisah & baris baru dari satu sel supaya jumlah kolom tidak bergeser."""
    return teks.replace(";", ",").replace("\r", " ").replace("\n", " ")
