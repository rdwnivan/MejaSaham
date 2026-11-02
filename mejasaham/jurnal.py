"""F7 — jurnal keputusan & rekap kepatuhan (PRD 9.8, 11.5, 13.1/13.2). Tahap 3 langkah 1.

Empat hal menentukan seluruh bentuk modul ini, dan semuanya bisa diperiksa di keluaran:

1. **Satu keputusan = satu transaksi** (K34). PRD 9.8 menutup katalognya dengan rumus
   "Kepatuhan = transaksi tanpa pelanggaran ÷ seluruh transaksi", jadi penyebutnya transaksi yang
   **tercatat** — bukan niat, dan bukan entri berstatus `ide` (yang justru berarti "belum ada
   tesis", PRD 9.6).

2. **Setiap pelanggaran dibaca dari SATU tempat.** V1/V2/V6 dibaca dari baris `transaksi` tempat
   `posisi.catat_transaksi` mencatatnya; V5 dari baris `posisi` tempat `ubah_stop` mencatatnya;
   V3/V4/V7 **diturunkan di sini** dari baris yang sudah ada (rencana, transaksi, posisi, harga,
   revisi tesis). Tidak ada satu pun kode pelanggaran yang disalin ke tabel `jurnal` — itulah yang
   membuat rekap mustahil menghitung pelanggaran dua kali (kekhawatiran T44), dan tabel `jurnal`
   karena itu hanya memuat yang tidak bisa diturunkan: alasan, pelajaran, tanggal tinjau, dan
   penanda selesai (PRD 11.5 "[Tulis pelajaran] [Tandai selesai]").

3. **Yang tidak dapat dinilai disebut, bukan dianggap patuh** (aturan keras 2). Ada dua wadah yang
   berbeda dan tidak boleh dicampur: `Pelanggaran` (memang dilanggar) dan `TakDinilai` (tidak
   dapat diperiksa, mis. penutupan sebelum tanggal transaksi tidak ada di sumber data). Pelanggaran
   yang tidak bisa diatribusikan ke satu transaksi juga **tidak** dipakai mengubah rasio — ia
   dilaporkan terpisah beserta sebabnya.

4. **Jurnal tidak memblokir apa pun** (K34). Menambah catatan hanya menambah revisi; tidak ada
   penghapusan senyap (PRD 9.8), dan pencatatan transaksi tetap boleh berjalan tanpa jurnal.

Tiga batas yang **diketahui** dan disebut apa adanya, bukan ditutupi:

* **Jumlah peristiwa V5 tidak dapat dipulihkan.** Kolom `posisi.pelanggaran` menyimpan *kode*
  (`_gabung_pelanggaran` menggabungkan tanpa menggandakan), jadi dua kali stop diturunkan pada satu
  posisi terbaca sama dengan sekali. Karena itu V5 dihitung **satu kali per posisi**, dan itu
  dikatakan di keluaran. Menghitungnya sebagai peristiwa berarti mengarang.
* **V7 hanya untuk posisi aktif.** "Posisi dipertahankan setelah pembatal tesis terpicu" hanya bisa
  dinilai pada posisi yang masih terbuka sekarang; posisi yang sudah ditutup tidak lagi
  "dipertahankan", dan menandainya berarti menghukum keputusan yang sudah selesai.
* **Expectancy menuntut putaran yang sudah tertutup.** Hasil separuh jalan bukan hasil: PRD 13.2
  menuntut "positif **setelah biaya dan pajak**", dan PRD 9.8 menuntut hasil dihubungkan lewat
  `id_rencana → id_posisi → transaksi`. Putaran yang belum tertutup, yang 1R-nya tidak dapat
  dinilai, dan yang biayanya belum lengkap dipisahkan beserta sebabnya.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from fractions import Fraction

from mejasaham import dasbor, db, kandidat, penyesuaian, posisi, potret, risiko, tampilan

SUMBER_JURNAL = "dicatat pengguna lewat --jurnal-catat"

#: Katalog pelanggaran PRD 9.8 — **dipinjam** dari `posisi.py`, bukan disalin: kode yang sama
#: dipakai baris yang mencatatnya, dan dua daftar yang berbeda akan membuat kode yang sah di satu
#: tempat tidak dikenal di tempat lain.
KATALOG: Mapping[str, str] = dict(posisi.PELANGGARAN)

#: Di mana tiap kode dideteksi. Satu tempat per kode; disebut di keluaran supaya angka kepatuhan
#: bisa ditelusuri ke barisnya, bukan hanya dipercaya.
DIDETEKSI_DI: Mapping[str, str] = {
    "V1": "baris transaksi (posisi.catat_transaksi)",
    "V2": "baris transaksi (posisi.catat_transaksi)",
    "V3": "baris rencana yang dieksekusi (batasnya dihitung ulang di sini)",
    "V4": "diturunkan dari transaksi + harga + revisi tesis",
    "V5": "baris posisi (posisi.ubah_stop)",
    "V6": "baris transaksi (posisi.catat_transaksi)",
    "V7": "diturunkan dari posisi aktif + penutupan terakhir + harga pembatal tesis",
}

#: PRD 13.2: *"Butuh minimal 30–50 keputusan sebelum dinilai"*. Batas bawah rentang itu dipakai
#: (usulan U22 di `docs/keputusan.md`): di bawahnya expectancy tetap dihitung sebagai **angka
#: sementara**, tetapi dinyatakan belum dapat dinilai.
BATAS_PUTARAN_DINILAI = 30

#: PRD 9.10 & aturan keras 8: rekap ini memuat angka hasil (expectancy, drawdown), jadi
#: pernyataannya ikut — sama seperti setiap ekspor dan ringkasan harian.
BUKAN_NASIAT = "Catatan: rekap ini bukan nasihat investasi (PRD 9.10)."

#: Sebab-sebab yang bisa dipastikan dari data yang tersimpan (barisnya tidak menyimpan pesannya).
_SEBAB_TERSIMPAN: Mapping[str, str] = {
    "V1": "masuk tanpa stop awal: tidak ada stop yang dinyatakan rencana maupun tesis",
    "V2": "lembar posisi melebihi rencana yang dieksekusi",
    "V5": "stop digeser menjauhi harga",
    "V6": "transaksi tanpa rencana tersimpan",
}


class GalatJurnal(RuntimeError):
    """Kesalahan yang pesannya sudah ditujukan untuk pengguna, bukan traceback (aturan keras 7)."""


# ---------------------------------------------------------------------------------------
# Bentuk baris
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Catatan:
    """Satu revisi catatan jurnal. Revisi terakhir = yang berlaku."""

    id_jurnal: int
    revisi: int
    id_transaksi: int
    alasan: str | None
    pelajaran: str | None
    tanggal_tinjau: str | None
    selesai_pada: str | None
    sumber: str
    diketahui_pada: str

    def ringkas(self) -> str:
        bagian = [f"jurnal #{self.id_jurnal} r{self.revisi}", f"transaksi #{self.id_transaksi}"]
        if self.alasan:
            bagian.append(f"alasan: {self.alasan}")
        if self.pelajaran:
            bagian.append(f"pelajaran: {self.pelajaran}")
        if self.tanggal_tinjau:
            bagian.append(f"tinjau {self.tanggal_tinjau}")
        if self.selesai_pada:
            bagian.append(f"SELESAI {self.selesai_pada}")
        return " · ".join(bagian)


@dataclass(frozen=True)
class Pelanggaran:
    """Satu pelanggaran PRD 9.8 atas satu keputusan.

    `id_transaksi = None` berarti pelanggarannya **nyata** tetapi tidak bisa diatribusikan ke satu
    transaksi (mis. rencana yang melanggar batas dan belum pernah dieksekusi). Ia tetap dilaporkan,
    tetapi tidak dipakai mengubah rasio kepatuhan — sebab penyebutnya transaksi (PRD 9.8).
    """

    kode: str
    sebab: str
    dideteksi_di: str
    tanggal: str
    kode_emiten: str
    id_transaksi: int | None

    @property
    def sebutan(self) -> str:
        return f"{self.kode} ({KATALOG.get(self.kode, self.kode)})"

    def ringkas(self) -> str:
        tujuan = (
            f"transaksi #{self.id_transaksi}"
            if self.id_transaksi is not None
            else "TIDAK DIATRIBUSIKAN ke satu transaksi"
        )
        return f"{self.sebutan} · {self.kode_emiten} {self.tanggal} · {tujuan} · {self.sebab}"


@dataclass(frozen=True)
class TakDinilai:
    """Pemeriksaan yang tidak dapat diselesaikan — bukan pelanggaran, bukan pula "patuh"."""

    kode: str
    sebab: str
    kode_emiten: str
    tanggal: str

    def ringkas(self) -> str:
        sebutan = f"{self.kode} ({KATALOG.get(self.kode, self.kode)})"
        return f"{sebutan} · {self.kode_emiten} {self.tanggal} · {self.sebab}"


@dataclass(frozen=True)
class BarisJurnal:
    """Satu keputusan beserta annotasi manusianya dan pelanggaran yang menempel padanya."""

    transaksi: posisi.Transaksi
    catatan: Catatan | None
    rencana: risiko.Rencana | None
    tesis: kandidat.Kandidat | None
    pelanggaran: tuple[Pelanggaran, ...]

    @property
    def patuh(self) -> bool:
        """True bila tidak ada pelanggaran pada keputusan ini (PRD 9.8, ruas pembilang)."""
        return not self.pelanggaran

    @property
    def kode_pelanggaran(self) -> tuple[str, ...]:
        return tuple(sorted({satu.kode for satu in self.pelanggaran}))

    @property
    def lengkap_tesis(self) -> bool:
        """PRD 13.1: keputusan punya tesis, level pembatal, dan stop."""
        if self.tesis is None or self.rencana is None:
            return False
        return bool(
            self.tesis.punya_tesis
            and self.tesis.pembatal_fundamental
            and (self.tesis.harga_pembatal is not None or self.rencana.stop is not None)
        )

    def ringkas(self) -> str:
        t = self.transaksi
        stop = (
            tampilan.rupiah(self.rencana.stop)
            if self.rencana is not None
            else "(tanpa rencana)"
        )
        bagian = [
            f"{t.tanggal}  {t.kode:<5} {t.aksi:<4}",
            f"{tampilan.angka(t.lembar, 0):>9} lbr @ {tampilan.rupiah(t.harga):>10}",
            f"stop {stop:>10}",
            f"biaya {tampilan.rupiah(t.biaya) if t.biaya is not None else '(belum dicatat)'}",
            t.mode,
        ]
        teks = "  ".join(bagian)
        teks += (
            f"\n      transaksi #{t.id_transaksi} r{t.revisi} · posisi #{t.id_posisi}"
            + (f" · rencana #{t.id_rencana}" if t.id_rencana is not None else " · TANPA RENCANA")
        )
        if self.tesis is not None:
            teks += f" · tesis kandidat #{self.tesis.id_kandidat} r{self.tesis.revisi}"
        if self.pelanggaran:
            teks += "\n      PELANGGARAN: " + "; ".join(
                f"{satu.sebutan} — {satu.sebab}" for satu in self.pelanggaran
            )
        else:
            teks += "\n      patuh aturan (PRD 9.8)"
        if self.catatan is None:
            teks += "\n      catatan: (belum ditulis; --jurnal-catat " + str(t.id_transaksi) + ")"
        else:
            if self.catatan.alasan:
                teks += f"\n      alasan   : {self.catatan.alasan}"
            if self.catatan.pelajaran:
                teks += f"\n      pelajaran: {self.catatan.pelajaran}"
            if self.catatan.tanggal_tinjau:
                teks += f"\n      tinjau   : {self.catatan.tanggal_tinjau}"
            if self.catatan.selesai_pada:
                teks += f"\n      selesai  : {self.catatan.selesai_pada}"
            teks += f"\n      (jurnal #{self.catatan.id_jurnal} r{self.catatan.revisi})"
        return teks


@dataclass(frozen=True)
class Putaran:
    """Satu putaran keputusan: rencana → posisi → transaksi (PRD 9.8 "Metrik hasil").

    `r_posisi` adalah 1R menurut PRD 8.2 — risiko awal yang benar-benar diambil, yaitu
    `risiko_nominal` rencana yang dieksekusi, pada **revisi yang berlaku saat eksekusinya**.
    """

    kode: str
    id_posisi: int
    id_rencana: int | None
    revisi_rencana: int | None
    mode: str
    status: str
    tanggal_buka: str
    tanggal_tutup: str | None
    r_posisi: Fraction | None
    alasan_r: str | None
    hasil: int | None
    alasan_hasil: str | None
    dividen: int

    @property
    def tertutup(self) -> bool:
        return self.status == "ditutup" and self.tanggal_tutup is not None

    @property
    def dinilai(self) -> bool:
        """True bila putaran ini boleh masuk expectancy (tertutup, 1R ada, biaya lengkap)."""
        return self.tertutup and self.hasil is not None and self.r_posisi is not None

    @property
    def hasil_r(self) -> Fraction | None:
        if not self.dinilai or self.r_posisi is None or self.hasil is None:
            return None
        return Fraction(self.hasil) / self.r_posisi

    def ringkas(self) -> str:
        bagian = [f"posisi #{self.id_posisi}", self.kode, self.mode, self.status]
        if self.id_rencana is not None:
            bagian.append(f"rencana #{self.id_rencana} r{self.revisi_rencana}")
        bagian.append(
            "1R " + (tampilan.rupiah(float(self.r_posisi)) if self.r_posisi is not None else "—")
        )
        bagian.append(
            "hasil " + (tampilan.rupiah(self.hasil) if self.hasil is not None else "—")
        )
        if self.hasil_r is not None:
            bagian.append(f"{tampilan.angka(float(self.hasil_r), 2)}R")
        if self.tanggal_tutup:
            bagian.append(f"tutup {self.tanggal_tutup}")
        teks = " · ".join(bagian)
        if self.dividen:
            teks += f" (termasuk dividen {tampilan.rupiah(self.dividen)})"
        if self.alasan_r:
            teks += f"\n      1R TIDAK DINILAI: {self.alasan_r}"
        if self.alasan_hasil:
            teks += f"\n      HASIL BELUM LENGKAP: {self.alasan_hasil}"
        return teks


@dataclass(frozen=True)
class Rekap:
    """Rekap kepatuhan PRD 9.8/11.5/13.1 yang bisa diperiksa baris demi baris."""

    bulan: str | None
    mode: str | None
    keputusan: tuple[BarisJurnal, ...]
    pelanggaran: tuple[Pelanggaran, ...]
    di_luar_periode: tuple[Pelanggaran, ...]
    tak_dinilai: tuple[TakDinilai, ...]
    putaran: tuple[Putaran, ...]
    drawdown: risiko.Drawdown

    @property
    def jumlah_keputusan(self) -> int:
        return len(self.keputusan)

    @property
    def jumlah_patuh(self) -> int:
        return sum(1 for satu in self.keputusan if satu.patuh)

    @property
    def persen_patuh(self) -> Fraction | None:
        if not self.keputusan:
            return None
        return Fraction(self.jumlah_patuh, self.jumlah_keputusan) * 100

    @property
    def hitungan_per_kode(self) -> tuple[tuple[str, int], ...]:
        jumlah: dict[str, int] = {}
        for satu in self.pelanggaran:
            jumlah[satu.kode] = jumlah.get(satu.kode, 0) + 1
        return tuple(sorted(jumlah.items()))

    @property
    def putaran_dinilai(self) -> tuple[Putaran, ...]:
        return tuple(satu for satu in self.putaran if satu.dinilai)

    @property
    def expectancy_r(self) -> Fraction | None:
        """Rata-rata hasil per putaran tertutup dalam kelipatan R (PRD 8.2)."""
        dinilai = self.putaran_dinilai
        if not dinilai:
            return None
        total = sum((satu.hasil_r or Fraction(0) for satu in dinilai), Fraction(0))
        return total / len(dinilai)

    @property
    def alasan_expectancy(self) -> str | None:
        """Sebab expectancy belum dapat dinilai — `None` berarti sudah dinilai (PRD 13.2)."""
        if len(self.putaran_dinilai) >= BATAS_PUTARAN_DINILAI:
            return None
        return (
            f"{len(self.putaran_dinilai)} dari {BATAS_PUTARAN_DINILAI} putaran tertutup yang "
            "diperlukan (PRD 13.2: butuh minimal 30–50 keputusan sebelum dinilai)"
        )

    @property
    def lengkap_tesis(self) -> tuple[int, int]:
        """(jumlah keputusan yang lengkap tesis, jumlah keputusan) — PRD 13.1."""
        return (
            sum(1 for satu in self.keputusan if satu.lengkap_tesis),
            len(self.keputusan),
        )

    @property
    def per_bulan(self) -> tuple[tuple[str, int, int, int, int], ...]:
        """(bulan, keputusan, patuh, pelanggaran, putaran tertutup) per bulan, urut tanggal."""
        bulan: dict[str, list[int]] = {}
        for satu in self.keputusan:
            isi = bulan.setdefault(satu.transaksi.tanggal[:7], [0, 0, 0, 0])
            isi[0] += 1
            isi[1] += 1 if satu.patuh else 0
            isi[2] += len(satu.pelanggaran)
        for satu in self.putaran:
            if satu.dinilai and satu.tanggal_tutup:
                bulan.setdefault(satu.tanggal_tutup[:7], [0, 0, 0, 0])[3] += 1
        return tuple((nama, *isi) for nama, isi in sorted(bulan.items()))

    @property
    def per_mode(self) -> tuple[tuple[str, int, int], ...]:
        """(mode, keputusan, patuh) — PRD 9.8: rekap memisahkan data simulasi dan nyata."""
        mode: dict[str, list[int]] = {}
        for satu in self.keputusan:
            isi = mode.setdefault(satu.transaksi.mode, [0, 0])
            isi[0] += 1
            isi[1] += 1 if satu.patuh else 0
        return tuple((nama, *isi) for nama, isi in sorted(mode.items()))

    def ringkas(self) -> str:
        judul_periode = self.bulan or "seluruh periode"
        judul_mode = self.mode or "seluruh mode"
        baris = [f"REKAP KEPATUHAN — {judul_periode} · {judul_mode}", ""]
        if not self.keputusan:
            baris.append(
                "  (belum ada keputusan tercatat — catat eksekusi dengan --catat-transaksi atau "
                "formulir Catat transaksi di Detail emiten (dasbor web); jurnal menilai transaksi, "
                "bukan niat, PRD 9.8/K34)"
            )
            baris.append("")
            baris.append(f"  {BUKAN_NASIAT}")
            return "\n".join(baris)

        persen = self.persen_patuh
        baris.append(
            f"  Keputusan (transaksi) : {self.jumlah_keputusan} · patuh {self.jumlah_patuh}"
            f" ({tampilan.angka(float(persen), 2) if persen is not None else '—'}%)"
            "  ← PRD 9.8: transaksi tanpa pelanggaran ÷ seluruh transaksi"
        )
        hitungan = self.hitungan_per_kode
        if hitungan:
            rinci = " · ".join(f"{kode} {jumlah}×" for kode, jumlah in hitungan)
            baris.append(f"  Pelanggaran           : {len(self.pelanggaran)} · {rinci}")
            for satu in self.pelanggaran:
                baris.append(f"      {satu.ringkas()}")
        else:
            baris.append("  Pelanggaran           : tidak ada")

        for nama, jumlah, patuh in self.per_mode:
            baris.append(
                f"  Mode {nama:<9}: {jumlah} keputusan · patuh {patuh}"
                "  ← PRD 9.8/9.11: kedua mode dilaporkan terpisah"
            )

        lengkap, total = self.lengkap_tesis
        baris.append(
            f"  Kelengkapan tesis     : {lengkap} dari {total} keputusan punya tesis + pembatal + "
            "stop (PRD 13.1 menargetkan 100%)"
        )

        v7 = [satu for satu in self.pelanggaran if satu.kode == "V7"]
        baris.append(
            f"  Tesis batal (V7)      : {len(v7)} posisi aktif dipertahankan setelah pembatal "
            "tesisnya terpicu"
        )
        for satu in v7:
            baris.append(f"      {satu.kode_emiten} · {satu.sebab}")

        dinilai = self.putaran_dinilai
        expectancy = self.expectancy_r
        if self.alasan_expectancy is None and expectancy is not None:
            baris.append(
                f"  Expectancy            : {tampilan.angka(float(expectancy), 2)}R per putaran "
                f"tertutup ({len(dinilai)} putaran, setelah biaya dan pajak)"
            )
        elif expectancy is not None:
            baris.append(
                f"  Expectancy            : BELUM DAPAT DINILAI — {self.alasan_expectancy}"
                f". Angka sementara: {tampilan.angka(float(expectancy), 2)}R per putaran tertutup "
                f"({len(dinilai)} putaran)"
            )
        else:
            baris.append(
                "  Expectancy            : BELUM DAPAT DINILAI — belum ada putaran tertutup yang "
                f"lengkap. {self.alasan_expectancy}"
            )
        tanpa_r = [satu for satu in self.putaran if satu.tertutup and satu.r_posisi is None]
        if tanpa_r:
            baris.append(
                f"      {len(tanpa_r)} putaran tertutup tidak punya 1R (tanpa rencana tersimpan): "
                + ", ".join(f"{satu.kode} (posisi #{satu.id_posisi})" for satu in tanpa_r[:5])
            )
        belum_tertutup = [satu for satu in self.putaran if not satu.tertutup]
        if belum_tertutup:
            baris.append(
                f"      {len(belum_tertutup)} putaran masih terbuka — hasilnya belum final, jadi "
                "belum masuk expectancy"
            )
        if dinilai:
            baris.append(
                "  Putaran tertutup (hasil tiap keputusan dalam R, PRD 9.8/8.2):"
            )
            for satu in dinilai[:20]:
                baris.append(f"      {satu.ringkas()}")
            if len(dinilai) > 20:
                baris.append(f"      … dan {len(dinilai) - 20} putaran lain")

        dd = self.drawdown
        if dd.terkoreksi:
            baris.append(
                f"  Drawdown berjalan     : {tampilan.angka((dd.drawdown_bp or 0) / 100, 2)}% "
                f"dari puncak (maksimum {tampilan.angka((dd.drawdown_maksimum_bp or 0) / 100, 2)}%, "
                "terkoreksi arus dana)"
            )
        else:
            sebab_dd = dd.alasan or "sebabnya tidak dinyatakan"
            baris.append(
                f"  Drawdown berjalan     : TIDAK DAPAT DINILAI — {sebab_dd}"
            )

        if self.di_luar_periode:
            baris.append(
                f"  Di luar periode/tanpa transaksi: {len(self.di_luar_periode)} pelanggaran "
                "(tidak mengubah rasio di atas, PRD 9.8)"
            )
            for satu in self.di_luar_periode:
                baris.append(f"      {satu.ringkas()}")
        if self.tak_dinilai:
            baris.append(f"  Tidak dapat dinilai   : {len(self.tak_dinilai)}")
            for satu in self.tak_dinilai:
                baris.append(f"      {satu.ringkas()}")

        if self.bulan is None:
            baris.append("")
            baris.append("  Per bulan:")
            for nama, jumlah, patuh, pelanggaran, putaran in self.per_bulan:
                baris.append(
                    f"    {nama}  {jumlah} keputusan · patuh {patuh} · {pelanggaran} pelanggaran · "
                    f"{putaran} putaran tertutup"
                )
        baris.append("")
        baris.append(f"  {BUKAN_NASIAT}")
        return "\n".join(baris)


# ---------------------------------------------------------------------------------------
# Catatan jurnal (yang disimpan)
# ---------------------------------------------------------------------------------------

_KOLOM_CATATAN = (
    "id_jurnal",
    "revisi",
    "id_transaksi",
    "alasan",
    "pelajaran",
    "tanggal_tinjau",
    "selesai_pada",
    "sumber",
    "diketahui_pada",
)


def _ke_catatan(baris: sqlite3.Row) -> Catatan:
    return Catatan(**{kolom: baris[kolom] for kolom in _KOLOM_CATATAN})


def catatan_terkini(sambungan: sqlite3.Connection, id_transaksi: int) -> Catatan | None:
    baris = sambungan.execute(
        "SELECT * FROM v_jurnal_terkini WHERE id_transaksi = ? ORDER BY id_jurnal LIMIT 1",
        (id_transaksi,),
    ).fetchone()
    return None if baris is None else _ke_catatan(baris)


def riwayat_catatan(sambungan: sqlite3.Connection, id_jurnal: int) -> tuple[Catatan, ...]:
    """Seluruh revisi satu rantai jurnal, terlama lebih dulu — bukti tidak ada penghapusan senyap."""
    return tuple(
        _ke_catatan(baris)
        for baris in sambungan.execute(
            "SELECT * FROM jurnal WHERE id_jurnal = ? ORDER BY revisi", (id_jurnal,)
        )
    )


def catat(
    sambungan: sqlite3.Connection,
    id_transaksi: int,
    *,
    alasan: str | None = None,
    pelajaran: str | None = None,
    tanggal_tinjau: date | str | None = None,
    selesai_pada: date | str | None = None,
    sumber: str = SUMBER_JURNAL,
    dicatat_pada: str | None = None,
) -> Catatan:
    """Tulis (atau revisi) catatan jurnal untuk satu transaksi.

    PRD 9.8: *"mengubah isi jurnal lama diperbolehkan hanya dengan menyimpan versi sebelumnya"* —
    karena itu fungsi ini **tidak pernah** menimpa: ia menambah revisi pada rantai yang sama, dan
    revisinya **menggabungkan**: bidang yang tidak disebut mempertahankan isi sebelumnya, supaya
    "tulis pelajaran" tidak menghapus alasan yang sudah ditulis. Sebaliknya, mengosongkan satu
    bidang tidak bisa dilakukan lewat fungsi ini — mengosongkan berarti menghapus, dan PRD 9.8
    melarang penghapusan senyap.
    """
    transaksi = sambungan.execute(
        "SELECT * FROM v_transaksi_terkini WHERE id_transaksi = ?", (id_transaksi,)
    ).fetchone()
    if transaksi is None:
        raise GalatJurnal(
            f"transaksi #{id_transaksi} tidak ada di basis data. Jurnal menilai transaksi yang "
            "tercatat (PRD 9.8, K34); catat eksekusinya lebih dulu lewat --catat-transaksi."
        )

    bersih = {
        "alasan": _teks(alasan),
        "pelajaran": _teks(pelajaran),
        "tanggal_tinjau": _tanggal(tanggal_tinjau, "--tanggal-tinjau"),
        "selesai_pada": _tanggal(selesai_pada, "--tandai-selesai"),
    }
    if not any(bersih.values()):
        raise GalatJurnal(
            f"catatan jurnal untuk transaksi #{id_transaksi} kosong: isi minimal satu dari "
            "--alasan, --pelajaran, --tanggal-tinjau, atau --tandai-selesai. Baris jurnal tanpa "
            "isi tidak mencatat apa pun (dan itu ditolak mesin, bukan hanya di sini)."
        )

    lama = catatan_terkini(sambungan, id_transaksi)
    nilai = {
        "id_transaksi": id_transaksi,
        "alasan": bersih["alasan"] or (lama.alasan if lama else None),
        "pelajaran": bersih["pelajaran"] or (lama.pelajaran if lama else None),
        "tanggal_tinjau": bersih["tanggal_tinjau"] or (lama.tanggal_tinjau if lama else None),
        "selesai_pada": bersih["selesai_pada"] or (lama.selesai_pada if lama else None),
        "sumber": sumber,
        "diketahui_pada": dicatat_pada or db.waktu_iso(),
    }
    if lama is not None:
        nilai["id_jurnal"] = lama.id_jurnal
        nilai["revisi"] = lama.revisi + 1
    else:
        nilai["id_jurnal"] = int(
            sambungan.execute("SELECT COALESCE(MAX(id_jurnal), 0) + 1 FROM jurnal").fetchone()[0]
        )
        nilai["revisi"] = 1

    kolom = list(nilai)
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            f"INSERT INTO jurnal ({', '.join(kolom)})"
            f" VALUES ({', '.join('?' for _ in kolom)})",
            [nilai[kolom_satu] for kolom_satu in kolom],
        )
    hasil = catatan_terkini(sambungan, id_transaksi)
    assert hasil is not None  # baru saja ditulis; ketiadaannya berarti basis datanya rusak
    return hasil


def _teks(nilai: object) -> str | None:
    if nilai is None:
        return None
    teks = str(nilai).strip()
    return teks or None


def _tanggal(nilai: date | str | None, sebutan: str) -> str | None:
    if nilai is None:
        return None
    if isinstance(nilai, date):
        return nilai.isoformat()
    teks = str(nilai).strip()
    try:
        return date.fromisoformat(teks).isoformat()
    except ValueError as galat:
        raise GalatJurnal(
            f"{sebutan} menerima tanggal ISO (YYYY-MM-DD), bukan {teks!r}"
        ) from galat


# ---------------------------------------------------------------------------------------
# Pelanggaran: tiap kode dibaca dari satu tempat
# ---------------------------------------------------------------------------------------


def _transaksi_pada(
    sambungan: sqlite3.Connection, id_posisi: int, tanggal: str | None
) -> int | None:
    """Transaksi yang paling relevan dengan kejadian bertanggal `tanggal`.

    Aturannya satu dan dinyatakan terbuka: transaksi **terakhir pada atau sebelum** tanggal
    kejadian; bila kejadiannya mendahului seluruh transaksi, transaksi pertama (dan itu terlihat
    dari tanggalnya, bukan disembunyikan).
    """
    daftar = [
        (baris["tanggal"], int(baris["id_transaksi"]))
        for baris in sambungan.execute(
            "SELECT tanggal, id_transaksi FROM v_transaksi_terkini WHERE id_posisi = ?"
            " ORDER BY tanggal, id_transaksi",
            (id_posisi,),
        )
    ]
    if not daftar:
        return None
    if tanggal is None:
        return daftar[-1][1]
    sebelumnya = [satu for satu in daftar if satu[0] <= tanggal]
    return (sebelumnya or daftar)[-1][1]


def pelanggaran_tersimpan(sambungan: sqlite3.Connection) -> tuple[Pelanggaran, ...]:
    """V1/V2/V6: apa adanya dari baris `transaksi` yang mencatatnya (satu tempat)."""
    hasil: list[Pelanggaran] = []
    for baris in sambungan.execute(
        "SELECT * FROM v_transaksi_terkini WHERE pelanggaran IS NOT NULL"
        " ORDER BY tanggal, id_transaksi"
    ):
        # Pembaca barisnya **dipinjam** dari `posisi.py`, bukan disalin: pemetaan kolom→`Transaksi`
        # hanya boleh punya satu tempat, supaya kolom baru tidak diam-diam terlewat di sini.
        transaksi = posisi._ke_transaksi(baris)
        for kode in transaksi.kode_pelanggaran:
            sebab = _SEBAB_TERSIMPAN.get(kode, KATALOG.get(kode, kode))
            if kode == "V2" and transaksi.id_rencana is not None:
                rencana = risiko.terkini(sambungan, transaksi.id_rencana)
                if rencana is not None:
                    lembar = _lembar_setelah(sambungan, transaksi)
                    sebab += (
                        f": rencana #{rencana.id_rencana} menyatakan {tampilan.angka(rencana.lembar, 0)}"
                        " lembar"
                        + (
                            f", posisinya {tampilan.angka(lembar, 0)} lembar setelah transaksi ini"
                            if lembar is not None
                            else ""
                        )
                    )
            hasil.append(
                Pelanggaran(
                    kode=kode,
                    sebab=sebab,
                    dideteksi_di=DIDETEKSI_DI.get(kode, "baris transaksi"),
                    tanggal=transaksi.tanggal,
                    kode_emiten=transaksi.kode,
                    id_transaksi=transaksi.id_transaksi,
                )
            )
    return tuple(hasil)


def _lembar_setelah(sambungan: sqlite3.Connection, transaksi: posisi.Transaksi) -> int | None:
    angka = posisi.hitungan(sambungan, transaksi.id_posisi, sampai=transaksi.tanggal)
    lembar = angka.lembar_terbuka
    return int(lembar) if lembar.denominator == 1 else None


def pelanggaran_stop(sambungan: sqlite3.Connection) -> tuple[Pelanggaran, ...]:
    """V5: dari baris `posisi` (tempat `ubah_stop` mencatatnya), satu kali per posisi.

    Jumlah **peristiwa**-nya tidak dapat dipulihkan dari skema: `_gabung_pelanggaran` menyimpan
    kode, bukan peristiwa, sehingga dua kali stop diturunkan terbaca sama dengan sekali. Yang
    dilaporkan karena itu perubahan pertama yang terbaca (lama → baru), dan jumlahnya satu per
    posisi. Mengarang jumlah peristiwa akan menjadi angka yang tidak bisa ditelusuri.
    """
    hasil: list[Pelanggaran] = []
    for baris in sambungan.execute(
        "SELECT * FROM v_posisi_terkini WHERE pelanggaran IS NOT NULL ORDER BY id_posisi"
    ):
        # Sama alasannya dengan `_ke_transaksi` di atas: pemetaannya satu tempat.
        posisi_kini = posisi._ke_posisi(baris)
        if "V5" not in posisi_kini.kode_pelanggaran:
            continue
        riwayat = posisi.riwayat(sambungan, posisi_kini.id_posisi)
        lama: int | None = None
        baru: int | None = posisi_kini.stop_terkini
        sebelumnya = None
        for satu in riwayat:
            if "V5" in satu.kode_pelanggaran:
                lama = sebelumnya.stop_terkini if sebelumnya is not None else None
                baru = satu.stop_terkini
                break
            sebelumnya = satu
        sebab = _SEBAB_TERSIMPAN["V5"]
        if lama is not None and baru is not None:
            sebab += f": {tampilan.rupiah(lama)} → {tampilan.rupiah(baru)}"
        elif baru is not None:
            sebab += f": stop terkini {tampilan.rupiah(baru)}"
        tanggal = posisi_kini.tgl_stop or posisi_kini.diketahui_pada[:10]
        sebab += (
            f" (basis {tanggal}" + (", dinyatakan sumbernya" if posisi_kini.tgl_stop else "")
            + ")"
        )
        hasil.append(
            Pelanggaran(
                kode="V5",
                sebab=sebab,
                dideteksi_di=DIDETEKSI_DI["V5"],
                tanggal=tanggal,
                kode_emiten=posisi_kini.kode,
                id_transaksi=_transaksi_pada(sambungan, posisi_kini.id_posisi, tanggal),
            )
        )
    return tuple(hasil)


def _batas_dilanggar(sambungan: sqlite3.Connection, rencana: risiko.Rencana) -> tuple[str, ...]:
    """Batas mana saja yang dilewati rencana ini, dihitung ulang dari angkanya sendiri."""
    sebab: list[str] = []
    if rencana.lembar > rencana.maks_lembar_bobot:
        sebab.append(
            f"bobot: {tampilan.angka(rencana.lembar, 0)} lembar melebihi batas "
            f"{tampilan.angka(rencana.maks_lembar_bobot, 0)} lembar"
        )
    for sebutan, batas in (
        ("sektor", rencana.maks_lembar_sektor),
        ("likuiditas", rencana.maks_lembar_likuiditas),
        ("kas", rencana.maks_lembar_kas),
    ):
        if batas is not None and rencana.lembar > batas:
            sebab.append(
                f"{sebutan}: {tampilan.angka(rencana.lembar, 0)} lembar melebihi batas "
                f"{tampilan.angka(batas, 0)} lembar"
            )
    preset = risiko.muat_preset(sambungan, rencana.id_preset_risiko)
    total_bp = preset.bp("total_risiko_maksimum")
    if rencana.total_risiko_bp > total_bp:
        sebab.append(
            f"total risiko: {tampilan.angka(rencana.total_risiko_bp / 100, 2)}% melebihi batas "
            f"{tampilan.angka(total_bp / 100, 2)}%"
        )
    return tuple(sebab)


def rencana_pada(
    sambungan: sqlite3.Connection, id_rencana: int, momen: str | None
) -> tuple[risiko.Rencana | None, str | None]:
    """Revisi rencana yang **berlaku** pada `momen` (stempel waktu barisnya).

    Penting untuk dua angka sekaligus: 1R (PRD 8.2) dan V3. Rencana yang direvisi sesudah
    dieksekusi tidak boleh mengubah risiko yang benar-benar diambil — dan memakai revisi terakhir
    akan melakukan tepat itu, diam-diam.
    """
    riwayat = risiko.riwayat(sambungan, id_rencana)
    if not riwayat:
        return None, f"rencana #{id_rencana} tidak ada di basis data"
    if momen is None:
        return riwayat[-1], None
    berlaku = [satu for satu in riwayat if satu.dicatat_pada <= momen]
    if berlaku:
        return berlaku[-1], None
    return (
        riwayat[0],
        f"transaksi dicatat {momen}, lebih awal daripada revisi pertama rencana "
        f"#{id_rencana} ({riwayat[0].dicatat_pada}); yang dipakai r{riwayat[0].revisi}",
    )


def pelanggaran_batas(sambungan: sqlite3.Connection) -> tuple[Pelanggaran, ...]:
    """V3: rencana yang melanggar batas — dinilai dari angka rencananya, bukan dari catatannya.

    Atribusinya: rencana yang dieksekusi menempel pada transaksi **pertama** yang mengeksekusinya
    (revisi yang berlaku saat itu); rencana yang belum dieksekusi dilaporkan tanpa transaksi.
    """
    hasil: list[Pelanggaran] = []
    for baris in sambungan.execute("SELECT id_rencana FROM v_rencana_terkini ORDER BY id_rencana"):
        id_rencana = int(baris["id_rencana"])
        pelaksana = [
            (satu["diketahui_pada"], int(satu["id_transaksi"]), satu["tanggal"])
            for satu in sambungan.execute(
                "SELECT id_transaksi, tanggal, diketahui_pada FROM v_transaksi_terkini"
                " WHERE id_rencana = ? ORDER BY tanggal, id_transaksi",
                (id_rencana,),
            )
        ]
        if pelaksana:
            momen, id_transaksi, tanggal = pelaksana[0]
            rencana, catatan = rencana_pada(sambungan, id_rencana, momen)
        else:
            id_transaksi = None
            rencana, catatan = risiko.terkini(sambungan, id_rencana), None
        if rencana is None:
            raise GalatJurnal(f"rencana #{id_rencana} tidak dapat dibaca: {catatan}")
        sebab = _batas_dilanggar(sambungan, rencana)
        if not sebab:
            continue
        teks = (
            f"rencana #{id_rencana} r{rencana.revisi} (rencana yang berlaku saat dieksekusi"
            if pelaksana
            else f"rencana #{id_rencana} r{rencana.revisi} (BELUM dieksekusi"
        )
        teks += "): " + "; ".join(sebab)
        if catatan:
            teks += f". Catatan: {catatan}"
        hasil.append(
            Pelanggaran(
                kode="V3",
                sebab=teks,
                dideteksi_di=DIDETEKSI_DI["V3"],
                tanggal=tanggal if pelaksana else rencana.tanggal,
                kode_emiten=rencana.kode,
                id_transaksi=id_transaksi,
            )
        )
    return tuple(hasil)


def pelanggaran_tambah_rugi(sambungan: sqlite3.Connection) -> tuple[Pelanggaran | TakDinilai, ...]:
    """V4: menambah posisi rugi tanpa tesis baru (PRD 9.8).

    Yang diperiksa, dan ketiganya dinyatakan terbuka:

    1. transaksi **beli** yang bukan pembelian pertama posisi itu (menambah, bukan membuka);
    2. posisinya memang **rugi** saat itu — harga rata-rata (basis sekarang) di atas penutupan
       pada atau sebelum tanggal transaksi (dibawa ke basis sekarang lewat `faktor_lembar`, sebab
       split sesudahnya akan membuat dua angka yang berbeda basis tampak sebanding);
    3. tidak ada revisi `kandidat` (tesis) untuk kode itu yang dicatat **sesudah** transaksi
       sebelumnya pada posisi yang sama — tesis baru itulah yang dituntut PRD 9.8.

    Bila harga penutupannya tidak ada, hasilnya `TakDinilai`: bukan pelanggaran, dan bukan pula
    "patuh".
    """
    label = potret.harga_dipakai(sambungan)
    hasil: list[Pelanggaran | TakDinilai] = []
    for posisi_kini in posisi.daftar(sambungan, status=None):
        transaksi = posisi.daftar_transaksi(sambungan, id_posisi=posisi_kini.id_posisi)
        beli = [satu for satu in transaksi if satu.aksi == "beli"]
        if len(beli) < 2:
            continue
        aksi = posisi.aksi_korporasi(sambungan, [posisi_kini.kode]).get(posisi_kini.kode, ())
        for sebelumnya, sekarang in zip(beli, beli[1:]):
            angka = posisi.hitungan(
                sambungan, posisi_kini.id_posisi, sampai=sebelumnya.tanggal, aksi=aksi
            )
            rata = angka.harga_rata
            if rata is None:
                continue
            acuan, tanggal_acuan, alasan = _penutupan_pada(
                sambungan, posisi_kini.kode, sekarang.tanggal, aksi, label
            )
            if acuan is None:
                hasil.append(
                    TakDinilai(
                        kode="V4",
                        sebab=(
                            f"tidak dapat diperiksa: {alasan} — dibutuhkan penutupan pada atau "
                            f"sebelum {sekarang.tanggal} untuk tahu posisinya rugi atau tidak"
                        ),
                        kode_emiten=posisi_kini.kode,
                        tanggal=sekarang.tanggal,
                    )
                )
                continue
            if rata <= acuan:
                continue  # posisinya tidak rugi saat ditambah: V4 tidak berlaku
            tesis_baru = _tesis_baru_sesudah(sambungan, posisi_kini, sebelumnya.diketahui_pada)
            if tesis_baru is not None:
                continue
            hasil.append(
                Pelanggaran(
                    kode="V4",
                    sebab=(
                        f"menambah posisi yang sedang rugi (rata-rata {tampilan.rupiah(float(rata))} "
                        f"vs penutupan {tampilan.rupiah(float(acuan))} pada {tanggal_acuan}) tanpa "
                        "tesis baru: tidak ada revisi kandidat untuk kode ini sesudah transaksi "
                        f"#{sebelumnya.id_transaksi} ({sebelumnya.tanggal})"
                    ),
                    dideteksi_di=DIDETEKSI_DI["V4"],
                    tanggal=sekarang.tanggal,
                    kode_emiten=sekarang.kode,
                    id_transaksi=sekarang.id_transaksi,
                )
            )
    return tuple(hasil)


def _penutupan_pada(
    sambungan: sqlite3.Connection,
    kode: str,
    tanggal: str,
    aksi: Iterable[object],
    label: potret.PilihanHarga | None,
) -> tuple[Fraction | None, str | None, str]:
    """Penutupan terakhir pada/sebelum `tanggal`, dibawa ke **basis sekarang** (lihat V4)."""
    if label is None:
        return None, None, "belum ada label sumber harga yang bisa dipakai"
    penggalan, argumen = label.syarat()
    baris = sambungan.execute(
        "SELECT tanggal, close FROM v_harga_harian_terkini"
        f" WHERE kode = ? AND {penggalan} AND tanggal <= ? ORDER BY tanggal DESC LIMIT 1",
        (kode, *argumen, tanggal),
    ).fetchone()
    if baris is None:
        return (
            None,
            None,
            f"label sumber {label.label!r} tidak memuat penutupan {kode} pada atau sebelum {tanggal}",
        )
    faktor = penyesuaian.faktor_lembar(aksi, sesudah=date.fromisoformat(baris["tanggal"]))  # type: ignore[arg-type]
    return Fraction(int(baris["close"])) / faktor, str(baris["tanggal"]), ""


def _tesis_baru_sesudah(
    sambungan: sqlite3.Connection, posisi_kini: posisi.Posisi, momen: str
) -> kandidat.Kandidat | None:
    """Revisi tesis (kandidat) untuk kode ini yang dicatat **sesudah** `momen`."""
    baris = sambungan.execute(
        "SELECT id_kandidat FROM kandidat WHERE kode = ? AND dicatat_pada > ?"
        " ORDER BY dicatat_pada DESC, revisi DESC LIMIT 1",
        (posisi_kini.kode, momen),
    ).fetchone()
    if baris is None:
        return None
    return kandidat.terkini(sambungan, int(baris["id_kandidat"]))


def pelanggaran_pembatal(sambungan: sqlite3.Connection) -> tuple[Pelanggaran, ...]:
    """V7: posisi aktif yang dipertahankan setelah pembatal tesisnya terpicu (PRD 9.8).

    Aturan "pembatal terpicu" **tidak** ditulis ulang di sini: ia dibaca dari
    `dasbor.pembatal_terpicu`, tempat yang sama yang mengisi daftar tindakan menunggu dasbor.
    Dua salinan aturan yang sama akan berbeda begitu salah satunya disunting.
    """
    aktif = posisi.ringkasan_semua(sambungan, status="aktif", dengan_dividen=False)
    hasil: list[Pelanggaran] = []
    for satu in dasbor.pembatal_terpicu(sambungan, aktif):
        hasil.append(
            Pelanggaran(
                kode="V7",
                sebab=(
                    f"penutupan {tampilan.rupiah(satu.penutupan)} ({satu.tanggal_harga}) sudah "
                    f"menyentuh harga pembatal tesis {tampilan.rupiah(satu.harga_pembatal)} "
                    f"(kandidat #{satu.id_kandidat} r{satu.revisi_kandidat}); posisinya masih "
                    "terbuka"
                ),
                dideteksi_di=DIDETEKSI_DI["V7"],
                tanggal=satu.tanggal_harga,
                kode_emiten=satu.kode,
                id_transaksi=_transaksi_pada(sambungan, satu.id_posisi, satu.tanggal_harga),
            )
        )
    return tuple(hasil)


def semua_pelanggaran(
    sambungan: sqlite3.Connection,
) -> tuple[tuple[Pelanggaran, ...], tuple[TakDinilai, ...]]:
    """Seluruh pelanggaran V1–V7, masing-masing dari satu tempat, plus yang tak dapat dinilai."""
    tersimpan = pelanggaran_tersimpan(sambungan)
    stop = pelanggaran_stop(sambungan)
    batas = pelanggaran_batas(sambungan)
    tambah = pelanggaran_tambah_rugi(sambungan)
    pembatal = pelanggaran_pembatal(sambungan)

    pelanggaran: list[Pelanggaran] = [*tersimpan, *stop, *batas, *pembatal]
    tak_dinilai: list[TakDinilai] = []
    for satu in tambah:
        if isinstance(satu, Pelanggaran):
            pelanggaran.append(satu)
        else:
            tak_dinilai.append(satu)
    pelanggaran.sort(key=lambda satu: (satu.tanggal, satu.kode_emiten, satu.kode))
    return tuple(pelanggaran), tuple(tak_dinilai)


# ---------------------------------------------------------------------------------------
# Baris jurnal & putaran
# ---------------------------------------------------------------------------------------


def baris(
    sambungan: sqlite3.Connection,
    *,
    bulan: str | None = None,
    kode: str | None = None,
    mode: str | None = None,
) -> tuple[BarisJurnal, ...]:
    """Satu baris jurnal per transaksi (keputusan), urut tanggal."""
    transaksi = posisi.daftar_transaksi(sambungan, kode=kode)
    if mode is not None:
        transaksi = tuple(satu for satu in transaksi if satu.mode == mode)
    if bulan is not None:
        transaksi = tuple(satu for satu in transaksi if satu.tanggal.startswith(bulan))
    pelanggaran, _ = semua_pelanggaran(sambungan)
    peta: dict[int, list[Pelanggaran]] = {}
    for satu in pelanggaran:
        if satu.id_transaksi is not None:
            peta.setdefault(satu.id_transaksi, []).append(satu)

    hasil: list[BarisJurnal] = []
    for satu in transaksi:
        rencana = risiko.terkini(sambungan, satu.id_rencana) if satu.id_rencana else None
        tesis = _tesis_untuk(sambungan, satu, rencana)
        hasil.append(
            BarisJurnal(
                transaksi=satu,
                catatan=catatan_terkini(sambungan, satu.id_transaksi),
                rencana=rencana,
                tesis=tesis,
                pelanggaran=tuple(peta.get(satu.id_transaksi, ())),
            )
        )
    return tuple(hasil)


def _tesis_untuk(
    sambungan: sqlite3.Connection,
    transaksi: posisi.Transaksi,
    rencana: risiko.Rencana | None,
) -> kandidat.Kandidat | None:
    """Tesis yang relevan: lewat rencana yang dieksekusi, atau entri terakhir kode itu."""
    if rencana is not None:
        entri = kandidat.terkini(sambungan, rencana.id_kandidat)
        if entri is not None:
            return entri
    baris_kandidat = sambungan.execute(
        "SELECT id_kandidat FROM v_kandidat_terkini WHERE kode = ? ORDER BY id_kandidat DESC"
        " LIMIT 1",
        (transaksi.kode,),
    ).fetchone()
    if baris_kandidat is None:
        return None
    return kandidat.terkini(sambungan, int(baris_kandidat["id_kandidat"]))


def putaran(
    sambungan: sqlite3.Connection,
    *,
    mode: str | None = None,
    bulan: str | None = None,
) -> tuple[Putaran, ...]:
    """Satu putaran per posisi: rencana → posisi → transaksi (PRD 9.8 "Metrik hasil")."""
    ringkasan = posisi.ringkasan_semua(sambungan, status=None, mode=mode)
    hasil: list[Putaran] = []
    for satu in ringkasan:
        p = satu.posisi
        if bulan is not None and (p.tgl_tutup or "")[:7] != bulan:
            continue
        r_posisi, revisi_rencana, alasan_r = _r_posisi(sambungan, p)
        angka = satu.hitungan
        dividen = satu.dividen.total
        hasil_putaran: int | None = None
        alasan_hasil: str | None = None
        if p.status != "ditutup":
            alasan_hasil = "posisinya masih terbuka; hasilnya belum final (PRD 9.8)"
        elif angka.lembar_terbuka != 0:
            alasan_hasil = (
                f"posisinya berstatus ditutup tetapi masih memegang {angka.lembar_terbuka} lembar; "
                "hasilnya belum lengkap"
            )
        elif satu.hasil_terealisasi is None:
            alasan_hasil = "belum ada penjualan yang bisa dihitung hasilnya"
        elif not angka.biaya_lengkap:
            alasan_hasil = (
                f"{angka.transaksi_tanpa_biaya} dari {angka.jumlah_transaksi} transaksi posisi ini "
                "belum mencatat biayanya, jadi hasilnya belum 'setelah biaya dan pajak' (PRD 9.8)"
            )
        else:
            hasil_putaran = satu.hasil_terealisasi + dividen
        hasil.append(
            Putaran(
                kode=p.kode,
                id_posisi=p.id_posisi,
                id_rencana=p.id_rencana,
                revisi_rencana=revisi_rencana,
                mode=p.mode,
                status=p.status,
                tanggal_buka=p.tgl_buka,
                tanggal_tutup=p.tgl_tutup,
                r_posisi=r_posisi,
                alasan_r=alasan_r,
                hasil=hasil_putaran,
                alasan_hasil=alasan_hasil,
                dividen=dividen,
            )
        )
    return tuple(hasil)


def _r_posisi(
    sambungan: sqlite3.Connection, posisi_kini: posisi.Posisi
) -> tuple[Fraction | None, int | None, str | None]:
    """1R putaran ini (PRD 8.2): `risiko_nominal` rencana yang dieksekusi, saat dieksekusinya."""
    transaksi = posisi.daftar_transaksi(sambungan, id_posisi=posisi_kini.id_posisi)
    dipakai: dict[int, str] = {}
    for satu in transaksi:
        if satu.id_rencana is not None and satu.id_rencana not in dipakai:
            dipakai[satu.id_rencana] = satu.diketahui_pada
    if not dipakai:
        return (
            None,
            None,
            "posisi ini dibuka tanpa rencana tersimpan (V6), sehingga risiko awal yang diambil "
            "tidak dapat dinilai — dan itu bukan nol",
        )
    total = 0
    revisi: int | None = None
    catatan: list[str] = []
    for id_rencana, momen in sorted(dipakai.items()):
        rencana, pesan = rencana_pada(sambungan, id_rencana, momen)
        if rencana is None:
            return None, None, f"rencana #{id_rencana} tidak dapat dibaca: {pesan}"
        total += rencana.risiko_nominal
        revisi = rencana.revisi if revisi is None else max(revisi, rencana.revisi)
        if pesan:
            catatan.append(pesan)
    return Fraction(total), revisi, "; ".join(catatan) or None


# ---------------------------------------------------------------------------------------
# Rekap
# ---------------------------------------------------------------------------------------


def rekap(
    sambungan: sqlite3.Connection,
    *,
    bulan: str | None = None,
    mode: str | None = None,
) -> Rekap:
    """Rekap kepatuhan PRD 9.8/13.1/13.2 untuk satu periode (dan satu mode, bila disebut)."""
    if bulan is not None:
        _periksa_bulan(bulan)
    keputusan = baris(sambungan, bulan=bulan, kode=None, mode=mode)
    semua, tak_dinilai = semua_pelanggaran(sambungan)
    id_dalam = {satu.transaksi.id_transaksi for satu in keputusan}
    dalam = tuple(satu for satu in semua if satu.id_transaksi in id_dalam)
    luar = tuple(satu for satu in semua if satu.id_transaksi not in id_dalam)
    return Rekap(
        bulan=bulan,
        mode=mode,
        keputusan=keputusan,
        pelanggaran=dalam,
        di_luar_periode=luar,
        tak_dinilai=tak_dinilai,
        putaran=putaran(sambungan, mode=mode, bulan=bulan),
        drawdown=risiko.drawdown(sambungan, mode=mode),
    )


def _periksa_bulan(bulan: str) -> None:
    try:
        date.fromisoformat(f"{bulan}-01")
    except ValueError as galat:
        raise GalatJurnal(
            f"bulan {bulan!r} tidak dikenal; tulis YYYY-MM (mis. 2026-10)"
        ) from galat


def kode_ringkas(sambungan: sqlite3.Connection) -> str:
    """Satu baris keadaan jurnal, untuk dasbor atau keluaran singkat."""
    jumlah = sambungan.execute("SELECT COUNT(*) FROM v_transaksi_terkini").fetchone()[0]
    tertulis = sambungan.execute("SELECT COUNT(*) FROM v_jurnal_terkini").fetchone()[0]
    return f"jurnal: {tertulis} dari {jumlah} keputusan (transaksi) sudah punya catatan"
