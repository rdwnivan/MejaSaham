"""Dasbor harian & "tindakan menunggu" (PRD 9.11, 11.1; pertanyaan P16).

PRD 11.1 menggambarkan satu halaman yang menjawab: *keadaan data, rezim pasar, kandidat teratas,
posisi berjalan, dan tindakan yang menunggu*. Modul ini menyusunnya untuk mode kepala, dan
alasannya bukan kelengkapan: PRD 9.11 menetapkan bahwa **posisi yang penutupannya menembus stop
atau pembatal tesis muncul di daftar "tindakan menunggu"** — daftar yang tidak ada berarti aturan
itu hanya hidup di atas kertas.

**Isi "tindakan menunggu" mengikuti usulan P16** (`docs/keputusan.md` bagian 3): posisi yang
penutupannya menembus stop atau pembatal tesis terpicu, tesis kedaluwarsa > 30 hari, dan right
issue dengan tenggat. Dua hal ditambahkan di luar usulan itu — **posisi tanpa stop** (sebab risiko
terbukanya tidak dapat dinilai) dan **right issue yang belum diputuskan tanpa tenggat yang
dinyatakan** — sebab keduanya tindakan yang menunggu sama seperti stop yang sudah tertembus, dan
yang kedua justru yang paling mudah terlewat. Right issue yang **tenggatnya sudah lewat** tanpa
keputusan tidak lagi masuk daftar tindakan (jendelanya tertutup) tetapi muncul di catatan: lubang
yang tidak disebut akan terbaca sebagai "tidak pernah terjadi".

**Stop dibandingkan dalam basis harga sekarang.** Sejak migrasi 013, `posisi.stop_terkini`
dipindahkan lebih dulu oleh split yang terjadi setelah basisnya (`posisi.tgl_stop`) lewat
`posisi.stop_dalam_basis()`. Membandingkan level stop pra-split dengan penutupan pasca-split akan
memunculkan "stop tertembus" yang tidak pernah terjadi — dan menghilangkan yang benar-benar
terjadi. Kalau basisnya tidak dapat dinilai, itu dikatakan, bukan dipaksa.

**Yang dibaca dasbor bukan hasil hitungan baru.** Kandidat teratas diambil dari tabel `skor` yang
**sudah** tersimpan untuk snapshot terakhir — menjalankan saringan ulang di sini akan membuat
dasbor memakan waktu puluhan detik dan, lebih buruk, menampilkan angka yang belum tentu sama
dengan yang terakhir dilihat pengguna (PRD 10: laporan selalu menyebut snapshot & versi presetnya).

**Rezim pasar, breadth, dan IHSG tetap memakai fungsi yang sama dengan `--saring`** (K58, T66) —
`metrik.breadth` + `metrik.rezim_pasar` atas semesta likuid `saring.semesta_likuid`. Sejak **K61**,
`--saring` menyimpan hasilnya beserta kunci (snapshot, preset, label harga, versi hitung), dan
dasbor membacanya kembali **hanya** bila kuncinya masih sama; selain itu dihitung ulang. Yang
dilarang bukan "membaca simpanan", melainkan angka milik keadaan lain tampil sebagai keadaan hari
ini. Ambangnya karena itu tetap tidak disalin ke modul ini. Bila bahannya belum cukup, yang
tercetak **NETRAL beserta sebabnya**, bukan kalimat tetap yang menyatakan datanya tidak ada:
kalimat lama itu terbukti salah (`harga_indeks` memang terisi) dan salahnya ke arah yang paling
merugikan — menyembunyikan satu baris halaman depan.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from fractions import Fraction

from mejasaham import (
    ingesti,
    kandidat,
    konteks_pasar,
    metrik,
    mutu,
    posisi,
    potret,
    risiko,
    saring,
    tampilan,
)
from mejasaham.konteks_pasar import BarisIndeks, KonteksPasar


class GalatDasbor(RuntimeError):
    """Kesalahan yang pesannya sudah ditujukan untuk pengguna, bukan traceback (aturan keras 7)."""


#: Jenis tindakan menunggu. Sengaja kode tetap, bukan teks bebas: daftar ini yang nanti dihitung
#: sebagai cakupan tindak lanjut, dan teks bebas tidak bisa dihitung.
JENIS_TINDAKAN: dict[str, str] = {
    "stop_tertembus": "penutupan terakhir sudah menembus stop",
    "pembatal_terpicu": "pembatal tesis terpicu",
    "tanpa_stop": "posisi berjalan tanpa stop",
    "tesis_kedaluwarsa": "tesis belum ditinjau melewati jatuh temponya",
    "right_issue_belum_diputuskan": (
        "right issue yang menyentuh posisi ini belum diputuskan (tebus / jual HMETD / abaikan)"
    ),
}


@dataclass(frozen=True)
class TindakanMenunggu:
    """Satu hal yang menuntut keputusan manusia, beserta rujukan barisnya."""

    jenis: str
    kode: str
    rujukan: str
    pesan: str

    def ringkas(self) -> str:
        return f"[{self.jenis}] {self.kode} · {self.rujukan} — {self.pesan}"


@dataclass(frozen=True)
class BarisSkor:
    kode: str
    peringkat: int | None
    skor_total_bp: int


#: Preset yang dipakai menghitung semesta likuid konteks pasar bila halaman ini belum punya skor
#: tersimpan. Namanya **sama** dengan bawaan `--saring` (`cli.jalankan_saring`), supaya dua mode
#: tidak memakai ambang ADTV20 yang berbeda untuk pertanyaan yang sama.
PRESET_PASAR_BAWAAN = "kualitas-nilai"


@dataclass(frozen=True)
class PembatalTerpicu:
    """Posisi aktif yang penutupan terakhirnya sudah menyentuh harga pembatal tesisnya.

    Temuan ini dipakai **dua** tempat: daftar tindakan menunggu di sini (PRD 9.11) dan pelanggaran
    V7 di `jurnal.py` (PRD 9.8). Karena itu aturannya tinggal di satu fungsi (`pembatal_terpicu`),
    bukan ditulis dua kali — dua salinan aturan yang sama akan berbeda begitu salah satunya
    disunting, dan yang berbeda adalah angka kepatuhan.
    """

    id_posisi: int
    kode: str
    id_kandidat: int
    revisi_kandidat: int
    harga_pembatal: int
    tanggal_harga: str
    penutupan: int


def pembatal_terpicu(
    sambungan: sqlite3.Connection,
    posisi_aktif: Sequence[posisi.RingkasanPosisi],
) -> tuple[PembatalTerpicu, ...]:
    """Pembatal tesis yang sudah terpicu pada posisi aktif — hukuman V7 ada di `jurnal.py`."""
    hasil: list[PembatalTerpicu] = []
    for satu in posisi_aktif:
        harga = satu.harga
        entri = _kandidat_entri(sambungan, satu)
        if (
            entri is not None
            and entri.harga_pembatal is not None
            and harga is not None
            and harga.close <= entri.harga_pembatal
        ):
            hasil.append(
                PembatalTerpicu(
                    id_posisi=satu.posisi.id_posisi,
                    kode=satu.posisi.kode,
                    id_kandidat=entri.id_kandidat,
                    revisi_kandidat=entri.revisi,
                    harga_pembatal=entri.harga_pembatal,
                    tanggal_harga=harga.tanggal.isoformat(),
                    penutupan=harga.close,
                )
            )
    return tuple(hasil)


@dataclass(frozen=True)
class Dasbor:
    """Satu halaman keadaan (PRD 11.1), seluruh angkanya berasal dari baris yang sudah tersimpan."""

    hari_ini: date
    id_snapshot: int | None
    tanggal_data: date | None
    batas_diketahui: str | None
    jumlah_emiten_snapshot: int
    sumber_harga: str | None
    sumber_tidak_dipakai: tuple[tuple[str, int], ...]
    hari_bursa_terakhir: str | None
    #: Konteks pasar snapshot ini (K58, T66): penutupan indeks acuan terakhir + perubahannya,
    #: breadth atas semesta likuid, dan rezimnya. Ketiganya `None`/kosong hanya bila belum ada
    #: snapshot sama sekali — bukan bila datanya ada tetapi tidak dibaca.
    pasar: BarisIndeks | None
    breadth: metrik.Nilai | None
    rezim: str | None
    preset_pasar: str | None
    jumlah_watchlist: int
    jumlah_tesis_kedaluwarsa: int
    posisi_aktif: tuple[posisi.RingkasanPosisi, ...]
    risiko: risiko.RingkasanRisikoBerjalan
    batas_total_risiko_bp: int | None
    ekuitas: risiko.EkuitasTercatat | None
    nilai_posisi: int | None
    drawdown: risiko.Drawdown
    id_preset_skor: str | None
    kandidat_teratas: tuple[BarisSkor, ...]
    tindakan: tuple[TindakanMenunggu, ...]
    catatan: tuple[str, ...]
    #: Sebab skor tersimpan itu baru **peringkat sementara** (PRD 7.3; K97 d) — kalimat yang
    #: sama dengan `--saring`; kosong bila boleh disebut kandidat. Tanpa ini, halaman depan
    #: menyebut "kandidat" untuk daftar yang layar Screener sebut belum boleh disebut kandidat.
    sebab_sementara: str = ""

    @property
    def snapshot_basi(self) -> bool:
        """AC-8: snapshot bukan dari hari bursa terakhir — dinyatakan, bukan dibiarkan tampak normal."""
        if self.tanggal_data is None or self.hari_bursa_terakhir is None:
            return False
        return self.tanggal_data.isoformat() < self.hari_bursa_terakhir

    @property
    def nilai_posisi_plus_kas(self) -> int | None:
        """Pembanding untuk ekuitas yang **dicatat pengguna** (K30).

        `None` bila salah satu sukunya tidak ada: posisi yang tidak punya penutupan terakhir, atau
        kas yang belum dicatat. Menjumlahkan sebagian akan terbaca sebagai nilai portofolio —
        persis kesalahan yang pembanding ini dibuat untuk mencegahnya.
        """
        if self.nilai_posisi is None or self.ekuitas is None or self.ekuitas.kas is None:
            return None
        return self.nilai_posisi + self.ekuitas.kas

    def ringkas(self) -> str:
        baris: list[str] = ["MEJA SAHAM — DASBOR HARIAN          " + tampilan.tanggal(self.hari_ini)]
        if self.id_snapshot is None:
            baris.append("Snapshot   : (belum ada snapshot — jalankan --refresh)")
        else:
            baris.append(
                f"Snapshot   : #{self.id_snapshot} · data {tampilan.tanggal(self.tanggal_data)} · "
                f"batas diketahui {self.batas_diketahui}"
            )
            peringatan = (
                "  >>> SNAPSHOT BUKAN DARI HARI BURSA TERAKHIR (AC-8)"
                if self.snapshot_basi
                else ""
            )
            baris.append(
                f"Hari bursa : terakhir {self.hari_bursa_terakhir or '(kalender kosong)'}"
                f"{peringatan}"
            )
            baris.append(
                f"Harga      : {self.sumber_harga or '(belum ada bar harga)'} — "
                f"{tampilan.angka(self.jumlah_emiten_snapshot, 0)} emiten punya bar pada tanggal data"
            )
            for label, jumlah in self.sumber_tidak_dipakai:
                baris.append(
                    f"             label lain TIDAK dipakai berhitung: {label} ({tampilan.angka(jumlah, 0)} bar)"
                )
            baris.append(
                "Pasar      : "
                + _teks_pasar(self.pasar, self.breadth, self.rezim, self.preset_pasar)
            )
        baris.append(
            f"Watchlist  : {self.jumlah_watchlist} entri"
            + (f" ({self.jumlah_tesis_kedaluwarsa} kedaluwarsa)" if self.jumlah_tesis_kedaluwarsa else "")
            + f" · Posisi: {len(self.posisi_aktif)} aktif"
        )
        for satu in self.posisi_aktif:
            p = satu.posisi
            baris.append(
                f"  #{p.id_posisi} {p.kode:<6} {tampilan.angka(float(satu.lembar_terbuka), 0):>10} lbr"
                f" · rata-rata {tampilan.rupiah(float(satu.hitungan.harga_rata)) if satu.hitungan.harga_rata is not None else '(tidak ada)'}"
                f" · stop {satu.stop.ringkas()}"
            )
            if satu.hitungan.disesuaikan:
                baris.append(
                    "             lembarnya disesuaikan aksi korporasi: "
                    + ", ".join(
                        f"{satu_aksi.jenis} {satu_aksi.rasio_lama}:{satu_aksi.rasio_baru} "
                        f"({satu_aksi.tanggal.isoformat()})"
                        for satu_aksi in satu.hitungan.aksi
                    )
                )
            if satu.dividen.ada:
                baris.append(
                    f"             dividen diterima: {tampilan.rupiah(satu.dividen.total)} bruto "
                    f"dari {len(satu.dividen.peristiwa)} pembayaran"
                )

        if self.ekuitas is None:
            baris.append("Ekuitas    : belum pernah dicatat — kalkulator risiko menolak menghitung")
        else:
            baris.append(
                f"Ekuitas    : {tampilan.rupiah(self.ekuitas.ekuitas)} ({self.ekuitas.tanggal}"
                + (
                    f", kas {tampilan.rupiah(self.ekuitas.kas)}"
                    if self.ekuitas.kas is not None
                    else ", kas belum dicatat"
                )
                + ")"
                + (
                    f" · nilai posisi {tampilan.rupiah(self.nilai_posisi)}"
                    if self.nilai_posisi is not None
                    else ""
                )
                + (
                    f" · posisi + kas {tampilan.rupiah(self.nilai_posisi_plus_kas)} "
                    f"(selisih {tampilan.rupiah(self.nilai_posisi_plus_kas - self.ekuitas.ekuitas)} "
                    "dari ekuitas tercatat)"
                    if self.nilai_posisi_plus_kas is not None
                    else ""
                )
            )
        dd = self.drawdown
        if dd.terkoreksi:
            baris.append(
                f"Drawdown   : {tampilan.angka((dd.drawdown_bp or 0) / 100, 2)}% dari puncak "
                f"(terkoreksi arus dana; puncak {dd.tanggal_puncak}) · maksimum "
                f"{tampilan.angka((dd.drawdown_maksimum_bp or 0) / 100, 2)}%"
            )
        else:
            baris.append(
                f"Drawdown   : TIDAK DAPAT DINILAI terkoreksi — {dd.alasan}. "
                f"Mentah (tanpa koreksi): {tampilan.angka(dd.mentah_bp / 100, 2)}% dari puncak, "
                f"maksimum {tampilan.angka(dd.mentah_maksimum_bp / 100, 2)}%"
            )

        if self.batas_total_risiko_bp is None:
            baris.append(
                f"Risiko     : berjalan {tampilan.rupiah(self.risiko.total)} — batas total belum "
                "tersimpan (jalankan --batas-risiko-bawaan), jadi tidak ada pembandingnya"
            )
        elif self.ekuitas is None:
            baris.append(
                f"Risiko     : berjalan {tampilan.rupiah(self.risiko.total)} — persentasenya tidak "
                "dapat dihitung karena ekuitasnya belum dicatat"
            )
        else:
            bp = self.risiko.total * 10000 // self.ekuitas.ekuitas
            baris.append(
                f"Risiko     : berjalan {tampilan.rupiah(self.risiko.total)} "
                f"({tampilan.angka(bp / 100, 2)}% dari batas "
                f"{tampilan.angka(self.batas_total_risiko_bp / 100, 2)}%) = posisi aktif "
                f"{tampilan.rupiah(self.risiko.dari_posisi)} "
                f"({self.risiko.jumlah_posisi_dinilai}/{self.risiko.jumlah_posisi_aktif} dinilai) "
                f"+ rencana belum dieksekusi {tampilan.rupiah(self.risiko.dari_rencana)} "
                f"({self.risiko.jumlah_rencana_belum} rencana)"
            )

        if self.kandidat_teratas and self.sebab_sementara:
            baris.append(
                f"Peringkat  : {len(self.kandidat_teratas)} teratas dari skor tersimpan "
                f"(preset {self.id_preset_skor}, snapshot #{self.id_snapshot}) — PERINGKAT "
                "SEMENTARA, BELUM BOLEH DISEBUT KANDIDAT"
            )
            baris.append(f"             sebabnya: {self.sebab_sementara}")
        elif self.kandidat_teratas:
            baris.append(
                f"Kandidat   : {len(self.kandidat_teratas)} teratas dari skor tersimpan "
                f"(preset {self.id_preset_skor}, snapshot #{self.id_snapshot})"
            )
        if self.kandidat_teratas:
            for satu in self.kandidat_teratas:
                baris.append(
                    f"  {satu.peringkat or 0:>3}  {satu.kode:<6} {tampilan.angka(satu.skor_total_bp / 100, 1):>6}"
                )
        else:
            baris.append(
                "Kandidat   : (belum ada skor tersimpan untuk snapshot terakhir — jalankan --saring)"
            )

        baris.append(f"\nTINDAKAN MENUNGGU ({len(self.tindakan)})")
        if self.tindakan:
            for nomor, satu in enumerate(self.tindakan, start=1):
                baris.append(f"  {nomor}. {satu.ringkas()}")
        else:
            baris.append("  (tidak ada)")

        if self.risiko.tidak_dinilai:
            baris.append(f"\nRISIKO YANG TIDAK DAPAT DINILAI ({len(self.risiko.tidak_dinilai)})")
            for satu in self.risiko.tidak_dinilai:
                baris.append(f"  - {satu}")
        if self.catatan:
            baris.append("\nCATATAN")
            for satu in self.catatan:
                baris.append(f"  - {satu}")
        return "\n".join(baris)


# ---------------------------------------------------------------------------------------
# Penyusunan
# ---------------------------------------------------------------------------------------


def _kepala_snapshot(sambungan: sqlite3.Connection) -> sqlite3.Row | None:
    return sambungan.execute("SELECT * FROM snapshot ORDER BY id_snapshot DESC LIMIT 1").fetchone()


def tanda_data(sambungan: sqlite3.Connection) -> tuple[object, ...]:
    """Sidik murah atas snapshot terakhir dan skor tersimpan yang dibaca `susun`.

    Dipakai pemanggil yang menyimpan dasbor jadi (dasbor web) untuk tahu bahwa hasilnya sudah
    basi karena snapshot atau skor ditulis di luar sepengetahuannya — mis. `--saring` dari baris
    perintah. `skor` ditulis ulang dengan hapus-lalu-sisip, jadi rowid tidak cukup; stempel
    `dihitung_pada` dan jumlah barisnya yang dipakai.
    """
    return tuple(
        sambungan.execute(
            "SELECT (SELECT MAX(id_snapshot) FROM snapshot),"
            " (SELECT MAX(dihitung_pada) FROM skor), (SELECT COUNT(*) FROM skor)"
        ).fetchone()
    )


def _skor_terakhir(
    sambungan: sqlite3.Connection, id_snapshot: int, batas: int
) -> tuple[str | None, tuple[BarisSkor, ...]]:
    """Skor yang **sudah** tersimpan untuk snapshot itu, dari preset yang terakhir dihitung."""
    baris = sambungan.execute(
        "SELECT id_preset, MAX(dihitung_pada) AS terakhir FROM skor WHERE id_snapshot = ?"
        " GROUP BY id_preset ORDER BY terakhir DESC, id_preset ASC LIMIT 1",
        (id_snapshot,),
    ).fetchone()
    if baris is None:
        return None, ()
    id_preset = str(baris["id_preset"])
    isi = tuple(
        BarisSkor(
            kode=satu["kode"],
            peringkat=satu["peringkat"],
            skor_total_bp=int(satu["skor_total_bp"]),
        )
        for satu in sambungan.execute(
            "SELECT kode, peringkat, skor_total_bp FROM skor"
            " WHERE id_snapshot = ? AND id_preset = ? AND peringkat IS NOT NULL"
            " ORDER BY peringkat LIMIT ?",
            (id_snapshot, id_preset, batas),
        )
    )
    return id_preset, isi


def _sebab_sementara(
    sambungan: sqlite3.Connection,
    pilihan: potret.PilihanHarga | None,
    tanggal_data: date,
    batas: str,
) -> str:
    """Sebab peringkat sementara snapshot ini, dinilai seperti `--saring` menilainya.

    Bahannya dibaca ulang as-of batas snapshot (notasi + gerbang sambungan), bukan disimpan
    bersama skor: keduanya milik snapshot, jadi jawabannya sama dengan saat saringan berjalan.
    Seperti konteks pasar, deret yang dinilai adalah deret bawaan — skor dari `--sumber` lain
    tidak dibedakan (tabel `skor` tidak mencatat labelnya).
    """
    keadaan = (
        potret.periksa_sambungan(sambungan, pilihan, tanggal_data=tanggal_data, batas=batas)
        if pilihan is not None
        else None
    )
    return saring.sebab_peringkat_sementara(
        notasi_lengkap=saring.notasi_terverifikasi(potret.notasi_as_of(sambungan, batas=batas)),
        sambungan_sementara=keadaan.sementara if keadaan is not None else None,
    )


def _kandidat_entri(sambungan: sqlite3.Connection, satu: posisi.RingkasanPosisi) -> kandidat.Kandidat | None:
    """Tesis yang relevan untuk satu posisi: lewat rencananya, atau entri terakhir kode itu."""
    if satu.posisi.id_rencana is not None:
        rencana = risiko.terkini(sambungan, satu.posisi.id_rencana)
        if rencana is not None:
            entri = kandidat.terkini(sambungan, rencana.id_kandidat)
            if entri is not None:
                return entri
    baris = sambungan.execute(
        "SELECT id_kandidat FROM v_kandidat_terkini WHERE kode = ? ORDER BY id_kandidat DESC LIMIT 1",
        (satu.posisi.kode,),
    ).fetchone()
    return None if baris is None else kandidat.terkini(sambungan, int(baris["id_kandidat"]))


def tindakan_menunggu(
    sambungan: sqlite3.Connection,
    posisi_aktif: Sequence[posisi.RingkasanPosisi],
    *,
    hari_ini: date | None = None,
) -> tuple[TindakanMenunggu, ...]:
    """Daftar tindakan PRD 9.11 + P16. Urut jenisnya tetap, supaya keluarannya deterministik (A5)."""
    momen = hari_ini or date.today()
    hasil: list[TindakanMenunggu] = []

    for satu in posisi_aktif:
        rujukan = f"posisi #{satu.posisi.id_posisi}"
        harga = satu.harga
        if satu.posisi.stop_terkini is None:
            hasil.append(
                TindakanMenunggu(
                    jenis="tanpa_stop",
                    kode=satu.posisi.kode,
                    rujukan=rujukan,
                    pesan=(
                        "berjalan tanpa stop (pelanggaran V1, PRD 9.8), jadi risiko terbukanya "
                        'TIDAK DINILAI — tetapkan levelnya lewat `--ubah-stop`, atau lewat '
                        'formulir "Ubah stop" di layar 11.1 (aksi #19d)'
                    ),
                )
            )
        elif satu.stop.nilai is None:
            hasil.append(
                TindakanMenunggu(
                    jenis="tanpa_stop",
                    kode=satu.posisi.kode,
                    rujukan=rujukan,
                    pesan=(
                        "stopnya ada, tetapi levelnya tidak dapat dinilai sehingga risiko "
                        f"terbukanya TIDAK DINILAI: {satu.stop.alasan}"
                    ),
                )
            )
        elif harga is not None and Fraction(harga.close) <= satu.stop.nilai:
            selisih = posisi.bulat_rupiah(satu.stop.nilai - Fraction(harga.close))
            hasil.append(
                TindakanMenunggu(
                    jenis="stop_tertembus",
                    kode=satu.posisi.kode,
                    rujukan=rujukan,
                    pesan=(
                        f"penutupan {tampilan.rupiah(harga.close)} ({harga.tanggal.isoformat()}) "
                        f"menembus stop {tampilan.rupiah(float(satu.stop.nilai))}"
                        + (
                            f" [tercatat {tampilan.rupiah(satu.posisi.stop_terkini)} pada basis "
                            f"{satu.stop.basis.isoformat()}]"
                            if satu.stop.disesuaikan
                            else ""
                        )
                        + f" (selisih {tampilan.rupiah(selisih)}) — "
                        "PRD 9.11: putuskan eksekusinya, dan catat transaksinya"
                    ),
                )
            )
        # Pesannya disusun dari temuan `pembatal_terpicu` supaya aturannya cuma satu tempat.
        for temuan in pembatal_terpicu(sambungan, [satu]):
            hasil.append(
                TindakanMenunggu(
                    jenis="pembatal_terpicu",
                    kode=temuan.kode,
                    rujukan=rujukan,
                    pesan=(
                        f"penutupan {tampilan.rupiah(temuan.penutupan)} sudah menyentuh harga "
                        f"pembatal tesis {tampilan.rupiah(temuan.harga_pembatal)} (kandidat "
                        f"#{temuan.id_kandidat} r{temuan.revisi_kandidat}, PRD 9.6). Posisi yang "
                        "dipertahankan setelah pembatalnya terpicu adalah pelanggaran V7 "
                        "(PRD 9.8) — terhitung di --rekap-kepatuhan"
                    ),
                )
            )

    for entri in kandidat.daftar(sambungan, status=("watchlist", "rencana", "posisi")):
        if entri.kedaluwarsa(momen):
            hasil.append(
                TindakanMenunggu(
                    jenis="tesis_kedaluwarsa",
                    kode=entri.kode,
                    rujukan=f"kandidat #{entri.id_kandidat}",
                    pesan=(
                        f"tanggal tinjau {entri.tanggal_tinjau} sudah lewat "
                        f"{entri.terlambat_hari(momen)} hari (PRD 9.6, 13.1) — tinjau ulang lewat "
                        "--tinjau-ulang, atau buang beserta alasannya"
                    ),
                )
            )

    for hak in posisi.hak_right_issue(sambungan, ringkasan_posisi=posisi_aktif, hari_ini=momen):
        if hak.sudah_diputuskan or hak.tenggat_lewat(momen):
            # Yang tenggatnya sudah lewat bukan lagi "menunggu keputusan" — jendelanya tertutup.
            # Ia tetap dilaporkan, tetapi sebagai lubang catatan (lihat `susun`), bukan sebagai
            # tindakan yang bisa dikerjakan hari ini.
            continue
        sisa = hak.sisa_hari(momen)
        hasil.append(
            TindakanMenunggu(
                jenis="right_issue_belum_diputuskan",
                kode=hak.kode,
                rujukan=f"posisi #{hak.id_posisi}",
                pesan=(
                    f"right issue {hak.tanggal_aksi.isoformat()}"
                    + (
                        f", tenggat {hak.tenggat.isoformat()} ({sisa} hari lagi)"
                        if hak.tenggat is not None and sisa is not None
                        else ", TENGGAT BELUM DINYATAKAN sumbernya — periksa di sekuritas Anda"
                    )
                    + (
                        f"; hak ~ {tampilan.angka(float(hak.lembar_hak), 0)} lembar"
                        + (
                            f" = {tampilan.rupiah(hak.biaya_tebus)} untuk ditebus"
                            if hak.biaya_tebus is not None
                            else ""
                        )
                        if hak.lembar_hak is not None
                        else f"; hak tidak dapat dihitung: {hak.alasan_hak}"
                    )
                    + ". Putuskan lewat `--putuskan-right-issue` (tebus / jual_hmetd / abaikan), "
                    "atau lewat tabel hak di layar 11.3 (aksi #19d)"
                    + (f" {hak.catatan_lot()}" if hak.catatan_lot() else "")
                ),
            )
        )
    return tuple(hasil)


# ---------------------------------------------------------------------------------------
# Konteks pasar: IHSG, breadth, rezim (K58, T66; PRD 8.2, 11.1)
# ---------------------------------------------------------------------------------------


def _preset_untuk_pasar(
    sambungan: sqlite3.Connection, id_preset_skor: str | None
) -> tuple[saring.Preset | None, str | None]:
    """Preset yang dipakai menghitung semesta likuid breadth, beserta sebab bila tidak ada.

    Yang dipakai lebih dulu adalah preset **yang menghasilkan skor tersimpan di halaman ini**:
    semesta likuid ikut ambang ADTV20 preset (K6), jadi memakai preset lain berarti halaman yang
    sama menampilkan breadth dari ambang yang tidak sejalan dengan daftar kandidatnya — persis
    dua-keluaran-yang-bertentangan yang dicegah K58/T66. Baris `skor` yang menunjuk preset yang
    sudah tidak ada **tidak** diganti diam-diam: itu dilaporkan, karena arti skor di halaman itu
    sendiri sudah tidak bisa diperiksa.
    """
    if id_preset_skor is not None:
        try:
            return saring.muat_preset(sambungan, id_preset_skor), None
        except ingesti.GalatIngesti as galat:
            return None, (
                f"preset skor {id_preset_skor!r} yang menghasilkan kandidat di halaman ini tidak "
                f"dapat dimuat: {galat}"
            )
    try:
        return saring.preset_terbaru(sambungan, PRESET_PASAR_BAWAAN), None
    except ingesti.GalatIngesti as galat:
        return None, f"preset bawaan {PRESET_PASAR_BAWAAN!r} belum ada: {galat}"


def _konteks_pasar(
    sambungan: sqlite3.Connection,
    id_snapshot: int,
    *,
    sumber: potret.PilihanHarga | None,
    preset: saring.Preset | None,
    sebab_preset: str | None,
) -> KonteksPasar:
    """IHSG, breadth, dan rezim satu snapshot lewat jalur yang **sama** dengan `--saring`.

    Urutannya mengikat dan disebut PRD 9.5: potret → metrik → semesta likuid → breadth → rezim.
    Preset & sebabnya diserahkan pemanggil supaya `_preset_untuk_pasar` (yang juga menentukan
    kunci konteks tersimpan) dipanggil **sekali** — dua panggilan bisa berbeda bila ada baris
    preset baru di antaranya.

    Yang tidak dikerjakan di sini: menulis apa pun. Dasbor karena itu aman dijalankan berkali-kali
    dan bisa dipanggil dari utas pekerja jendela (T65); penulisan konteks dilakukan `--saring`
    (`pengatur.jalankan_saring`) karena hanya di sanalah hasilnya baru dihitung.
    """
    bahan = potret.muat(sambungan, id_snapshot, sumber=sumber)
    if preset is None:
        # Tanpa preset, ambang ADTV20 semesta likuidnya tidak diketahui — jadi breadth-nya
        # "tidak dihitung" beserta sebabnya, bukan dihitung dengan ambang tebakan. Rezimnya tetap
        # lewat fungsi yang sama supaya jawabannya NETRAL beserta alasan, bukan angka.
        lebar = metrik.tidak_dihitung("breadth", "rasio", sebab_preset or "preset tidak tersedia")
        return konteks_pasar.dari_bahan(
            bahan,
            lebar,
            metrik.rezim_pasar(bahan, lebar),
            preset=None,
            catatan=konteks_pasar.sebab_bahan_kurang(bahan, lebar),
        )
    angka = metrik.metrik_semua(bahan)
    likuid = saring.semesta_likuid(bahan, preset, metrik=angka)
    lebar = metrik.breadth(bahan, likuid)
    return konteks_pasar.dari_bahan(
        bahan,
        lebar,
        metrik.rezim_pasar(bahan, lebar),
        preset=preset.id_preset,
        catatan=konteks_pasar.sebab_bahan_kurang(bahan, lebar),
    )


def _teks_pasar(
    pasar: BarisIndeks | None,
    breadth: metrik.Nilai | None,
    rezim: str | None,
    preset: str | None,
) -> str:
    """Satu baris konteks pasar (PRD 11.1): IHSG, breadth, rezim — beserta asal dan presetnya.

    Bentuk `breadth X% · rezim Y` sengaja **sama** dengan `pengatur.LaporanSaring.ringkas`,
    sehingga dua layar tidak bisa menampilkan dua pembacaan pasar yang berbeda: yang berbeda
    hanyalah keterangan asalnya (`LaporanSaring` menyebutnya di barisnya sendiri).
    """
    bagian = [
        pasar.ringkas()
        if pasar is not None
        else f"{metrik.INDEKS_ACUAN} belum ada di basis data"
    ]
    if breadth is not None and breadth.ada:
        # Asal & presetnya lebih dulu, supaya `breadth X% · rezim Y` tetap berdiri berdampingan —
        # bentuk yang **sama** dengan `pengatur.LaporanSaring.ringkas`, sehingga dua layar bisa
        # dibandingkan apa adanya. Semesta likuid ikut preset (ambang ADTV20), jadi preset yang
        # tidak disebut berarti angka yang tidak bisa diperiksa ulang.
        asal = [satu for satu in (breadth.asal, f"preset {preset}" if preset else None) if satu]
        if asal:
            bagian.append(f"{asal[0]} ({asal[1]})" if len(asal) > 1 else asal[0])
        bagian.append(f"breadth {tampilan.persen(breadth.nilai)}")
        bagian.append(f"rezim {rezim or 'tidak dapat dinilai'}")
    else:
        alasan = breadth.alasan if breadth is not None else "tidak dihitung"
        bagian.append(f"breadth tidak dihitung ({alasan})")
        bagian.append(f"rezim {rezim or 'tidak dapat dinilai'}")
    return " · ".join(bagian)


def susun(
    sambungan: sqlite3.Connection,
    *,
    hari_ini: date | None = None,
    teratas: int = 5,
) -> Dasbor:
    """Susun dasbor dari baris yang sudah tersimpan — tanpa menulis apa pun dan tanpa refresh.

    Kandidatnya **dibaca** dari tabel `skor` (bukan dihitung ulang); **konteks pasar** — IHSG,
    breadth, rezim — **dihitung** di sini lewat jalur yang sama dengan saringan (K58/T66), dan
    itulah sebabnya dasbor ikut membayar beban potret + seluruh metrik. Lihat `_konteks_pasar`.
    """
    momen = hari_ini or date.today()
    catatan: list[str] = []
    kepala = _kepala_snapshot(sambungan)

    id_snapshot: int | None = None
    tanggal_data: date | None = None
    batas: str | None = None
    sumber_harga: str | None = None
    # Pilihan utuh, bukan `sumber_harga`: label sambungan K97 adalah teks tampilan, dan
    # `potret.muat` menolaknya sebagai label bar (dasbor gagal di data kerja, 29 Okt 2026).
    pilihan_harga: potret.PilihanHarga | None = None
    tidak_dipakai: tuple[tuple[str, int], ...] = ()
    jumlah_emiten = 0
    id_preset: str | None = None
    kandidat_teratas: tuple[BarisSkor, ...] = ()
    sebab_sementara = ""
    if kepala is None:
        catatan.append(
            "belum ada snapshot: jalankan --refresh (atau --impor) supaya kandidat dan mutu data "
            "bisa ditampilkan"
        )
    else:
        id_snapshot = int(kepala["id_snapshot"])
        tanggal_data = date.fromisoformat(kepala["tanggal_data"])
        batas = kepala["batas_diketahui"]
        riwayat = potret.riwayat_sumber(sambungan, batas=batas)
        pilihan = potret.harga_dipakai(sambungan, batas=batas)
        if pilihan is not None:
            pilihan_harga = pilihan
            sumber_harga = pilihan.label
            tidak_dipakai = tuple(
                satu for satu in riwayat if satu[0] not in pilihan.label_dipakai
            )
            jumlah_emiten = int(
                sambungan.execute(
                    "SELECT COUNT(DISTINCT kode) FROM harga_harian WHERE tanggal = ? AND sumber = ?",
                    (tanggal_data.isoformat(), pilihan.label_pada(tanggal_data)),
                ).fetchone()[0]
            )
        else:
            catatan.append("belum ada bar harga sama sekali pada snapshot ini")
        id_preset, kandidat_teratas = _skor_terakhir(sambungan, id_snapshot, teratas)
        if kandidat_teratas:
            sebab_sementara = _sebab_sementara(sambungan, pilihan, tanggal_data, batas)
        if id_preset is None:
            catatan.append(
                "--saring belum pernah dijalankan pada snapshot ini, jadi tidak ada kandidat "
                "tersimpan untuk ditampilkan"
            )

    daftar_aktif = posisi.ringkasan_semua(sambungan, status="aktif")
    ringkasan_risiko = risiko.risiko_berjalan_lengkap(sambungan)
    ekuitas = risiko.ekuitas_terakhir(sambungan, momen)
    dd = risiko.drawdown(sambungan, sampai=momen)
    nilai_posisi: int | None = None
    if daftar_aktif:
        bagian = [satu.nilai_pasar for satu in daftar_aktif if satu.nilai_pasar is not None]
        nilai_posisi = sum(bagian) if len(bagian) == len(daftar_aktif) else None
        if nilai_posisi is None:
            catatan.append(
                "sebagian posisi tidak punya penutupan terakhir, jadi nilai posisinya tidak "
                "dijumlahkan — jumlah sebagian akan terbaca sebagai nilai portofolio"
            )
    if nilai_posisi is not None and ekuitas is not None and ekuitas.kas is not None:
        catatan.append(
            f"ekuitas dicatat pengguna ({tampilan.rupiah(ekuitas.ekuitas)}), sedangkan pembandingnya "
            f"`nilai posisi + kas` = {tampilan.rupiah(nilai_posisi + ekuitas.kas)} hanya menjumlahkan "
            "posisi yang tercatat aplikasi + kas yang Anda catat. Selisihnya wajar dan bukan "
            "kesalahan hitung: posisi yang belum tercatat tidak ikut terhitung (K30)"
        )

    try:
        batas_bp: int | None = risiko.preset_terbaru(sambungan).bp(risiko.TOTAL_RISIKO_MAKSIMUM)
    except risiko.GalatRisiko:
        batas_bp = None

    entri_hidup = kandidat.daftar(sambungan, status=("watchlist", "rencana", "posisi"))
    jumlah_kedaluwarsa = sum(1 for satu in entri_hidup if satu.kedaluwarsa(momen))

    if dd.deret:
        tanpa_mode = sum(1 for satu in dd.deret if satu.mode is None)
        if tanpa_mode:
            catatan.append(
                f"{tanpa_mode} dari {len(dd.deret)} catatan ekuitas belum menyatakan modenya "
                "(simulasi/nyata), jadi metrik kedua mode belum bisa dipisahkan (PRD 9.11)"
            )

    # Right issue yang tenggatnya sudah lewat tanpa keputusan bukan lagi tindakan yang bisa
    # dikerjakan — jendelanya tertutup — tetapi ia lubang di catatan, dan lubang yang tidak
    # disebut akan terbaca sebagai "tidak pernah terjadi".
    lewat = [
        satu
        for satu in posisi.hak_right_issue(sambungan, ringkasan_posisi=daftar_aktif, hari_ini=momen)
        if not satu.sudah_diputuskan and satu.tenggat_lewat(momen)
    ]
    if lewat:
        catatan.append(
            f"{len(lewat)} right issue tanpa keputusan yang tenggatnya sudah lewat "
            "(jendela keputusannya tertutup, tetapi kejadiannya tetap perlu dicatat): "
            + "; ".join(
                f"posisi #{satu.id_posisi} {satu.kode} ({satu.tanggal_aksi.isoformat()}, tenggat "
                f"{satu.tenggat.isoformat() if satu.tenggat else 'tidak dinyatakan'})"
                for satu in lewat
            )
        )
    dividen_aktif = sum(satu.dividen.total for satu in daftar_aktif)
    if dividen_aktif:
        label = sorted({satu for pos in daftar_aktif for satu in pos.dividen.sumber})
        catatan.append(
            f"dividen yang dihitung atas posisi aktif: {tampilan.rupiah(dividen_aktif)} bruto "
            "(dihitung dari aksi korporasi × lembar pada tanggal ex-date, bukan dicatat pengguna; "
            "pajaknya tidak dihitung"
            + (f"; sumber: {', '.join(label)}" if label else "")
            + ")"
        )
    tanpa_dividen = [
        satu for satu in daftar_aktif if not satu.dividen.ada and satu.dividen.catatan
    ]
    if tanpa_dividen:
        catatan.append(
            "dividen tidak dapat dihitung untuk: "
            + "; ".join(f"#{satu.posisi.id_posisi} {satu.posisi.kode}" for satu in tanpa_dividen)
            + f" (sebabnya di --posisi; contoh: {tanpa_dividen[0].dividen.catatan})"
        )
    # Konteks pasar (K58/T66, K61). Angka yang sah dibaca dari simpanan `--saring`; bila tidak
    # ada — snapshot baru, preset lain, label harga lain, atau versi hitung lain — dihitung ulang
    # lewat jalur yang sama dengan saringan. Menghitung ulang selalu benar; yang tidak boleh
    # adalah memakai angka milik keadaan lain (K61). `_preset_untuk_pasar` dipanggil di sini dan
    # hasilnya diserahkan, supaya kunci simpanan dan perhitungan memakai preset yang sama persis.
    konteks = KonteksPasar()
    if id_snapshot is not None:
        preset_pasar, sebab_preset = _preset_untuk_pasar(sambungan, id_preset)
        tersimpan = (
            konteks_pasar.muat(
                sambungan,
                id_snapshot=id_snapshot,
                id_preset=preset_pasar.id_preset,
                sumber=sumber_harga,
            )
            if preset_pasar is not None
            else None
        )
        konteks = (
            tersimpan
            if tersimpan is not None
            else _konteks_pasar(
                sambungan,
                id_snapshot,
                sumber=pilihan_harga,
                preset=preset_pasar,
                sebab_preset=sebab_preset,
            )
        )
    if konteks.catatan:
        catatan.append(konteks.catatan)

    return Dasbor(
        hari_ini=momen,
        id_snapshot=id_snapshot,
        tanggal_data=tanggal_data,
        batas_diketahui=batas,
        jumlah_emiten_snapshot=jumlah_emiten,
        sumber_harga=sumber_harga,
        sumber_tidak_dipakai=tidak_dipakai,
        hari_bursa_terakhir=mutu.hari_bursa_terakhir(sambungan, momen),
        pasar=konteks.pasar,
        breadth=konteks.breadth,
        rezim=konteks.rezim,
        preset_pasar=konteks.preset,
        jumlah_watchlist=len(entri_hidup),
        jumlah_tesis_kedaluwarsa=jumlah_kedaluwarsa,
        posisi_aktif=daftar_aktif,
        risiko=ringkasan_risiko,
        batas_total_risiko_bp=batas_bp,
        ekuitas=ekuitas,
        nilai_posisi=nilai_posisi,
        drawdown=dd,
        id_preset_skor=id_preset,
        kandidat_teratas=kandidat_teratas,
        tindakan=tindakan_menunggu(sambungan, daftar_aktif, hari_ini=momen),
        catatan=tuple(catatan),
        sebab_sementara=sebab_sementara,
    )
