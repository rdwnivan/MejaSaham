"""Server dasbor web lokal (K91) — `http.server` pustaka standar, lima layar PRD 11.

Tiga aturan yang membentuk berkas ini:

1. **Tidak menghitung sendiri.** Tiap layar memanggil fungsi inti yang sama dengan baris perintah
   dan jendela (`dasbor.susun`, `pengatur.jalankan_saring`, `risiko.hitung_untuk`,
   `jurnal.rekap`), jadi angka web = angka CLI.
2. **Hanya untuk mesin ini.** Server mendengar di `127.0.0.1` dan menolak `Host` lain (penangkal
   DNS rebinding); permintaan POST juga menolak `Origin` lintas situs.
3. **Satu koneksi per pekerjaan** (A2): koneksi SQLite dibuka di utas yang memakainya dan
   ditutup di `finally`, sehingga tidak ada kunci tulis yang menggantung.

Tahap B (28 Okt 2026) menambah tindakan tulis dengan alur yang sama dengan jendela (K59):
formulir → halaman **konfirmasi** berisi `PermintaanTulis.ringkasan` → "Tulis" → penulisan di utas
latar → pesan `HasilTulis`. Permintaan yang dikonfirmasi disimpan di server dan dipakai **sekali**,
sehingga yang ditulis adalah objek yang sama dengan yang ringkasannya disetujui (K59 d), dan
mengirim ulang konfirmasi tidak menulis dua kali. Setiap POST membawa token CSRF milik proses ini.
"""

from __future__ import annotations

import secrets
import sqlite3
import sys
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from email.parser import BytesParser
from email.policy import HTTP
from http import HTTPStatus
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from mejasaham import (
    dasbor,
    db,
    folder_pantau,
    jadwal,
    jurnal,
    kandidat,
    lokasi,
    notasi,
    pembaruan,
    pengatur,
    pengingat,
    pengumuman_idx,
    posisi,
    potret,
    risiko,
    saring,
    skema,
    tampilan,
    unggahan_idx,
)
from mejasaham.layar import tabel, tulis
from mejasaham.web import formulir
from mejasaham.web import halaman as h
from mejasaham.web import simpanan
from mejasaham.web.pekerjaan import DaftarPekerjaan, Pekerjaan, galat_terduga

HOST = "127.0.0.1"
PORT_BAWAAN = 8765
#: Selang muat ulang halaman selama hitungan berjalan.
DETIK_MUAT_ULANG = 2


GalatIsian = formulir.GalatIsian
int_atau_none = formulir.int_atau_none
#: Permintaan yang menunggu konfirmasi kedaluwarsa sesudah ini (detik).
BATAS_KONFIRMASI = 30 * 60
#: Badan POST terbesar yang dibaca (beberapa unggahan Ringkasan Saham + kepala multipart).
BATAS_BADAN = unggahan_idx.BATAS_BAIT_SEKALIGUS + 64 * 1024

#: Berkas unggahan per nama isian: [(nama berkas asli, isi), …] — isian `multiple` bisa banyak.
Unggahan = dict[str, list[tuple[str, bytes]]]


# ---------------------------------------------------------------------------------------
# Jembatan ke basis data dan isian
# ---------------------------------------------------------------------------------------


def dengan_basis(fungsi: Callable[[sqlite3.Connection], Any]) -> Any:
    """Buka basis data, jalankan `fungsi`, lalu **selalu** tutup koneksinya (A2)."""
    sambungan = db.siapkan()
    try:
        return fungsi(sambungan)
    finally:
        sambungan.close()


# ---------------------------------------------------------------------------------------
# Hasil layar yang dihitung di latar
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HasilDetail:
    kode: str
    pesan: str
    identitas: str = ""
    ringkas_skor: str = ""
    faktor_skor: tabel.Isi = ()
    metrik_skor: tabel.Isi = ()
    kriteria: tabel.Isi = ()
    tesis: str = ""
    posisi: tabel.Isi = ()
    hak: tabel.Isi = ()
    #: Pilihan formulir (nilai, label) — dari baris tersimpan kode ini saja (K64/T71 a).
    rencana_pilihan: tuple[tuple[str, str], ...] = ()
    posisi_pilihan: tuple[tuple[str, str], ...] = ()
    hak_pilihan: tuple[tuple[str, str], ...] = ()
    transaksi_pilihan: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class HasilRisiko:
    teks: str
    #: Objek yang dipakai "Simpan rencana" — angka yang **sedang tampil**, bukan hitungan ulang.
    hasil: risiko.HasilRisiko | None = None
    masukan: risiko.MasukanRisiko | None = None
    entri: kandidat.Kandidat | None = None
    jenis_stop: str = ""
    rencana_pilihan: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class HasilDasbor:
    dasbor: dasbor.Dasbor
    #: `dasbor.tanda_data` yang dibaca **sebelum** dasbor disusun: kalau skor ditulis di tengah
    #: penyusunan, tandanya tertinggal dan dasbor dihitung sekali lagi — arah yang aman.
    tanda: tuple[object, ...]


def _tugas_dasbor() -> HasilDasbor:
    def kerja(s: sqlite3.Connection) -> HasilDasbor:
        tanda = dasbor.tanda_data(s)
        return HasilDasbor(dasbor=dasbor.susun(s, teratas=20), tanda=tanda)

    return dengan_basis(kerja)


def _tanda_sekarang() -> tuple[object, ...]:
    # `hubungkan`, bukan `siapkan`: dibaca di utas permintaan setiap kali dasbor dibuka, jadi
    # tidak boleh memeriksa/menjalankan migrasi. Basis datanya pasti sudah disiapkan oleh
    # hitungan dasbor yang hasilnya sedang dicocokkan.
    sambungan = db.hubungkan()
    try:
        return dasbor.tanda_data(sambungan)
    finally:
        sambungan.close()


def _tugas_saring(
    id_preset: str, simpanan_potret: simpanan.SimpananPotret
) -> pengatur.LaporanSaring:
    def kerja(s: sqlite3.Connection) -> pengatur.LaporanSaring:
        preset = saring.muat_preset(s, id_preset)
        isi = simpanan_potret.ambil(s)
        return pengatur.jalankan_saring(s, preset, simpan=True, bahan=isi.bahan, angka=isi.angka)

    return dengan_basis(kerja)


def _tugas_detail(
    kode: str, id_preset: str, simpanan_potret: simpanan.SimpananPotret
) -> HasilDetail:
    """Isi layar 11.3 — urutan dan teksnya sama dengan `PanelDetail.tugas` di jendela."""

    def kerja(s: sqlite3.Connection) -> HasilDetail:
        isi = simpanan_potret.ambil(s)
        p = isi.bahan
        if kode not in p.emiten:
            return HasilDetail(
                kode=kode,
                pesan=(
                    f"Kode {kode} tidak ada pada snapshot #{p.id_snapshot} "
                    f"({p.tanggal_data.isoformat()}). Periksa ejaannya, atau jalankan `--refresh`."
                ),
            )
        emiten = p.emiten[kode]
        taksonomi = "sektor_idx_ic" if emiten.sektor_idx_ic else "sektor_sumber"
        sektor = emiten.sektor_idx_ic or emiten.sektor_sumber
        identitas = "\n".join(
            [
                f"{emiten.kode} — {emiten.nama}",
                f"sektor      : {sektor or tabel.KOSONG}"
                + (f"  (taksonomi: {taksonomi})" if sektor else ""),
                f"jenis       : {emiten.jenis or 'belum terisi'}",
                f"papan       : {emiten.papan or tabel.KOSONG}",
                f"notasi      : {emiten.status_notasi or tabel.KOSONG}",
                f"notasi sejak: {emiten.tanggal_notasi or tabel.KOSONG}",
                "jumlah saham: "
                + (
                    f"{emiten.jumlah_saham:,}".replace(",", ".")
                    if emiten.jumlah_saham
                    else tabel.KOSONG
                ),
                f"free float  : {tabel.persen_bp(emiten.free_float_bp)}%",
                f"sumber      : {emiten.sumber or tabel.KOSONG}",
                f"snapshot    : #{p.id_snapshot} ({tampilan.tanggal(p.tanggal_data)})",
            ]
        )
        preset = saring.muat_preset(s, id_preset)
        laporan = pengatur.jalankan_saring(s, preset, hanya_kode=(kode,), simpan=False, bahan=p, angka=isi.angka)
        hasil_skor = next((satu for satu in laporan.skor if satu.kode == kode), None)
        isi_saring = next((satu for satu in laporan.hasil_saring if satu.kode == kode), None)
        daftar_posisi = posisi.ringkasan_semua(s, status="aktif", kode=kode)
        daftar_hak = posisi.hak_right_issue(s, kode=kode, ringkasan_posisi=daftar_posisi)
        transaksi_beli = tuple(
            t
            for satu in daftar_posisi
            for t in posisi.daftar_transaksi(s, id_posisi=satu.posisi.id_posisi)
            if t.aksi == "beli"
        )
        return HasilDetail(
            kode=kode,
            pesan="",
            identitas=identitas,
            ringkas_skor=tabel.ringkas_skor(preset.id_preset, hasil_skor),
            faktor_skor=tabel.isi_faktor_skor(hasil_skor) if hasil_skor else (),
            metrik_skor=tabel.isi_metrik_skor(hasil_skor) if hasil_skor else (),
            kriteria=tabel.isi_kriteria(isi_saring.penilaian if isi_saring else ()),
            tesis=tabel.ringkas_tesis(kandidat.daftar(s, kode=kode), date.today()),
            posisi=tabel.isi_posisi(daftar_posisi),
            hak=tabel.isi_hak_right_issue(daftar_hak),
            rencana_pilihan=tuple(
                (str(r.id_rencana), tabel.label_rencana(r)) for r in risiko.daftar(s, kode=kode)
            ),
            posisi_pilihan=tuple(
                (str(r.posisi.id_posisi), tabel.label_posisi(r.posisi)) for r in daftar_posisi
            ),
            hak_pilihan=tuple(
                (f"{hk.id_posisi}|{hk.tanggal_aksi.isoformat()}", f"posisi #{hk.id_posisi} · aksi {tampilan.tanggal(hk.tanggal_aksi)}")
                for hk in daftar_hak
            ),
            transaksi_pilihan=tuple((str(t.id_transaksi), tabel.label_transaksi(t)) for t in transaksi_beli),
        )

    return dengan_basis(kerja)


def _tugas_risiko(
    kode: str,
    harga: int | None,
    stop: int | None,
    jenis_stop: str,
    ekuitas: int | None,
    kas: int | None,
    pakai_patuh: bool,
) -> HasilRisiko:
    """Urutan sama dengan `--hitung-risiko`: tesis diperiksa lebih dulu (PRD 9.6). Tidak menyimpan."""

    def kerja(s: sqlite3.Connection) -> HasilRisiko:
        entri = kandidat.untuk_rencana(s, kode)
        masukan = risiko.siapkan_masukan(
            s, kode, ekuitas_penimpa=ekuitas, kas_penimpa=kas, harga_acuan=harga
        )
        hasil, _stop = risiko.hitung_untuk(
            masukan,
            harga_masuk=masukan.harga_acuan,
            stop_penimpa=stop,
            harga_pembatal=entri.harga_pembatal,
            jenis_stop=jenis_stop,
        )
        if pakai_patuh:
            hasil = risiko.pakai_ukuran_patuh(hasil, masukan)
        return HasilRisiko(
            teks=risiko.ringkas_hasil(hasil, masukan),
            hasil=hasil,
            masukan=masukan,
            entri=entri,
            jenis_stop=jenis_stop,
            rencana_pilihan=tuple(
                (str(r.id_rencana), tabel.label_rencana(r)) for r in risiko.daftar(s, kode=kode)
            ),
        )

    return dengan_basis(kerja)


def _tugas_jurnal(bulan: str | None, mode: str | None) -> jurnal.Rekap:
    return dengan_basis(lambda s: jurnal.rekap(s, bulan=bulan, mode=mode))


def _pengambil_yfinance(laporan: Callable[[object], None]) -> pengatur.SumberData:
    """Pengambil yang sama dengan `--refresh` (harga + indeks, jeda bawaan)."""
    from mejasaham import pengambil

    return pengambil.PengambilYFinance(
        jeda=pengambil.JEDA_BAWAAN, indeks=pengambil.INDEKS, laporan=laporan
    )


#: Kunci pekerjaan pembaruan data — satu saja per proses, jadi tombol yang ditekan dua kali tidak
#: memulai pengambilan kedua.
KUNCI_PERBARUI = ("perbarui",)


def _penanda_kirim() -> str:
    """Penanda unik per pengiriman formulir.

    Kunci pekerjaan memuatnya, sehingga menekan tombol lagi menghitung ulang (data bisa sudah
    berubah), sedangkan muat ulang otomatis halaman "sedang menghitung" — URL yang sama — memakai
    hasil yang sedang berjalan, bukan memulainya lagi tanpa akhir.
    """
    return f'<input type=hidden name=kirim value="{time.time_ns()}">'


# ---------------------------------------------------------------------------------------
# Aplikasi: rute → HTML
# ---------------------------------------------------------------------------------------


@dataclass
class Jawaban:
    status: int
    isi: str = ""
    lokasi: str | None = None
    jenis: str = "text/html; charset=utf-8"


#: Ikon aplikasi (dulu dipasang di EXE, T82) — kini ikon tab peramban.
IKON = Path(__file__).with_name("ikon.svg")


class Aplikasi:
    """Rute dasbor. Dipisah dari `BaseHTTPRequestHandler` supaya bisa diuji tanpa soket."""

    def __init__(self) -> None:
        self.pekerjaan = DaftarPekerjaan(lambda: lokasi.folder_log() / "web.log")
        self.simpanan_potret = simpanan.SimpananPotret()
        #: Token CSRF proses ini; setiap formulir POST membawanya.
        self.csrf = secrets.token_urlsafe(24)
        self._kunci = threading.Lock()
        #: Permintaan tulis yang menunggu konfirmasi: token → (permintaan, URL kembali, waktu).
        self._menunggu: dict[str, tuple[tulis.PermintaanTulis, str, float]] = {}
        #: Hasil tulis per token, untuk halaman `/hasil`: token → (judul, URL kembali).
        self._tulis: dict[str, tuple[str, str]] = {}
        #: Hasil kalkulator yang sedang tampil, untuk "Simpan rencana": token → hasil.
        self._risiko: dict[str, HasilRisiko] = {}
        #: Pembuat pengambil data untuk "Perbarui data"; uji menggantinya dengan pengambil palsu.
        self.buat_pengambil: Callable[[Callable[[object], None]], pengatur.SumberData] = (
            _pengambil_yfinance
        )
        #: Kemajuan pembaruan yang sedang berjalan (K92), dibaca halaman `/perbarui`.
        self._kemajuan: pembaruan.Kemajuan | None = None
        #: Konfirmasi "Mulai pembaruan" yang belum dipakai: token → waktu dibuat.
        self._token_perbarui: dict[str, float] = {}

    # -- pembantu ----------------------------------------------------------------------

    def _tunggu_atau(
        self,
        pekerjaan: Pekerjaan,
        judul: str,
        aktif: str,
        tampilkan: Callable[[Any], str],
        *,
        kepala: str = "",
        keterangan: str = "",
    ) -> Jawaban:
        if pekerjaan.berjalan:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    judul,
                    kepala + h.memuat(pekerjaan.lama_detik, judul.lower()),
                    aktif=aktif,
                    muat_ulang_detik=DETIK_MUAT_ULANG,
                ),
            )
        if pekerjaan.galat is not None:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(judul, kepala + h.galat(pekerjaan.galat, pekerjaan.jejak), aktif=aktif),
            )
        return Jawaban(
            HTTPStatus.OK,
            h.kerangka(
                judul,
                kepala + tampilkan(pekerjaan.hasil),
                aktif=aktif,
                keterangan=keterangan or f"Dihitung dalam {pekerjaan.lama_detik:.1f} dtk.",
            ),
        )

    def _daftar_preset(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (id_preset, f"{nama} v{versi} · {horizon}")
            for id_preset, nama, versi, horizon in dengan_basis(saring.daftar_preset)
        )

    def _galat_halaman(self, judul: str, aktif: str, teks: str) -> Jawaban:
        return Jawaban(HTTPStatus.OK, h.kerangka(judul, h.galat(teks, None), aktif=aktif))

    # -- rute --------------------------------------------------------------------------

    def tangani(
        self, metode: str, jalur: str, kueri: dict[str, str], unggahan: Unggahan | None = None
    ) -> Jawaban:
        rute: Callable[[dict[str, str]], Jawaban] | None
        if metode == "GET":
            rute = {
                "/": self.dasbor,
                "/screener": self.screener,
                "/emiten": self.emiten,
                "/risiko": self.risiko,
                "/jurnal": self.jurnal,
                "/berkas": self.berkas,
                "/hasil": self.hasil_tulis,
                "/perbarui": self.kemajuan_perbarui,
                "/favicon.svg": self.ikon,
            }.get(jalur)
        elif metode == "POST":
            if not secrets.compare_digest(kueri.get("csrf", ""), self.csrf):
                return Jawaban(
                    HTTPStatus.FORBIDDEN,
                    h.kerangka(
                        "Ditolak",
                        h.pesan(
                            "Formulir ini berasal dari halaman lama (server sudah dijalankan ulang) "
                            "atau dari situs lain. Muat ulang halamannya lalu kirim lagi — belum "
                            "ada yang ditulis.",
                            "galat",
                        ),
                        aktif="",
                    ),
                )
            if jalur.startswith("/tulis/"):
                aksi = jalur.removeprefix("/tulis/")
                rute = lambda isian: self.siapkan_tulis(aksi, isian)  # noqa: E731
            else:
                rute = {
                    "/screener": self.jalankan_screener,
                    "/konfirmasi": self.konfirmasi,
                    "/perbarui": self.minta_perbarui,
                    "/perbarui/mulai": self.mulai_perbarui,
                    "/unggah/ringkasan-saham": lambda isian: self.unggah_ringkasan_saham(
                        unggahan or {}
                    ),
                    "/unggah/notasi-khusus": lambda isian: self.unggah_notasi_khusus(unggahan or {}),
                    "/unggah/pengumuman-idx": lambda isian: self.unggah_pengumuman_idx(unggahan or {}),
                }.get(jalur)
        else:
            rute = None
        if rute is None:
            return Jawaban(
                HTTPStatus.NOT_FOUND,
                h.kerangka("Tidak ditemukan", h.pesan(f"Tidak ada halaman {jalur}.", "galat"), aktif=""),
            )
        return rute(kueri)

    # -- alur tulis (K59, tahap B) -----------------------------------------------------

    def _kembali(self, kueri: dict[str, str], bawaan: str) -> str:
        """URL kembali hanya jalur lokal — bukan alamat lain (penangkal pengalihan terbuka)."""
        kembali = kueri.get("kembali") or bawaan
        return kembali if kembali.startswith("/") and not kembali.startswith("//") else bawaan

    def _susun_permintaan(self, aksi: str, isian: dict[str, str]) -> tulis.PermintaanTulis | None:
        if aksi == "impor":
            return formulir.impor(isian)
        if aksi == "cadangan":
            return formulir.cadangan()
        if aksi == "impor-ringkasan":
            # Beberapa berkas = nama berkas tersimpan dipisah koma (nama aman tidak memuat koma).
            nama = [satu for satu in isian.get("berkas", "").split(",") if satu]
            dipilih = [unggahan_idx.cari(satu) for satu in nama]
            if not dipilih or any(satu is None for satu in dipilih):
                raise GalatIsian("Unggahan itu tidak ditemukan; unggah ulang berkasnya.")
            return dengan_basis(
                lambda s: tulis.permintaan_impor_ringkasan_idx(
                    s, unggahan=[satu for satu in dipilih if satu is not None]
                )
            )
        if aksi == "impor-unduhan":
            folder = (isian.get("folder") or "").strip().strip('"')
            if not folder:
                raise GalatIsian(
                    "Folder pantau belum diisi (atau atur variabel lingkungan "
                    f"{folder_pantau.ENV_FOLDER_PANTAU})."
                )
            return dengan_basis(
                lambda s: tulis.permintaan_impor_folder_pantau(s, folder=Path(folder))
            )
        if aksi == "rencana":
            return self._permintaan_rencana(isian)
        fungsi = {
            "stop": formulir.ubah_stop,
            "transaksi": formulir.catat_transaksi,
            "right-issue": formulir.keputusan_right_issue,
            "jurnal": formulir.catat_jurnal,
        }.get(aksi)
        if fungsi is None:
            return None
        return dengan_basis(lambda s: fungsi(s, isian))

    def _permintaan_rencana(self, isian: dict[str, str]) -> tulis.PermintaanTulis:
        with self._kunci:
            tersimpan = self._risiko.get(isian.get("hasil", ""))
        if (
            tersimpan is None
            or tersimpan.hasil is None
            or tersimpan.masukan is None
            or tersimpan.entri is None
        ):
            raise GalatIsian(
                "Hasil hitungan itu sudah tidak ada (server dijalankan ulang atau terlalu lama). "
                "Tekan Hitung lagi, lalu simpan dari hasil yang baru."
            )
        return tulis.permintaan_simpan_rencana(
            hasil=tersimpan.hasil,
            masukan=tersimpan.masukan,
            entri=tersimpan.entri,
            jenis_stop=tersimpan.jenis_stop,
            id_snapshot=tersimpan.masukan.potret.id_snapshot,
            id_rencana=int_atau_none(isian.get("id_rencana"), "Rencana"),
        )

    def siapkan_tulis(self, aksi: str, isian: dict[str, str]) -> Jawaban:
        """Susun permintaan dari formulir, lalu tampilkan konfirmasinya. Belum menulis apa pun."""
        kembali = self._kembali(isian, "/")
        try:
            permintaan = self._susun_permintaan(aksi, isian)
        except Exception as galat:  # noqa: BLE001 — galat terduga jadi pesan; sisanya dilempar
            if not (isinstance(galat, tulis.GalatTulis) or galat_terduga(galat)):
                raise
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    "Belum ditulis",
                    h.galat(str(galat), None)
                    + h.pesan("Belum ada yang ditulis.")
                    + f'<p><a href="{h.e(kembali)}">Kembali</a></p>',
                    aktif="",
                ),
            )
        if permintaan is None:
            return Jawaban(
                HTTPStatus.NOT_FOUND,
                h.kerangka("Tidak ditemukan", h.pesan(f"Tidak ada tindakan {aksi}.", "galat"), aktif=""),
            )
        return self._konfirmasi(permintaan, kembali)

    def _konfirmasi(self, permintaan: tulis.PermintaanTulis, kembali: str, awal: str = "") -> Jawaban:
        """Halaman konfirmasi + token sekali pakai. Belum menulis apa pun."""
        token = secrets.token_urlsafe(16)
        sekarang = time.monotonic()
        with self._kunci:
            for lama in [k for k, (_, _, w) in self._menunggu.items() if sekarang - w > BATAS_KONFIRMASI]:
                del self._menunggu[lama]
            self._menunggu[token] = (permintaan, kembali, sekarang)
        isi = (
            awal
            + h.pra(permintaan.ringkasan, bungkus=True)
            + f"<p><strong>{h.e(permintaan.pertanyaan)}</strong></p>"
            + '<form method=post action="/konfirmasi" class=baris-tombol>'
            + f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
            + f'<input type=hidden name=token value="{h.e(token)}">'
            + "<button name=jawab value=tulis>Tulis</button>"
            + "<button class=kedua name=jawab value=batal>Batal</button></form>"
        )
        return Jawaban(HTTPStatus.OK, h.kerangka(f"Konfirmasi: {permintaan.judul}", isi, aktif=""))

    def konfirmasi(self, isian: dict[str, str]) -> Jawaban:
        token = isian.get("token", "")
        with self._kunci:
            menunggu = self._menunggu.pop(token, None)
        if menunggu is None:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    "Konfirmasi tidak berlaku",
                    h.pesan(
                        "Konfirmasi ini sudah dipakai, kedaluwarsa, atau berasal dari server yang "
                        "sudah dijalankan ulang. Tidak ada yang ditulis dari pengiriman ini.",
                        "galat",
                    )
                    + '<p><a href="/">Ke dasbor</a></p>',
                    aktif="",
                ),
            )
        permintaan, kembali, _ = menunggu
        if isian.get("jawab") != "tulis":
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    "Dibatalkan",
                    h.pesan(f"Dibatalkan: {permintaan.judul} tidak ditulis.")
                    + f'<p><a href="{h.e(kembali)}">Kembali</a></p>',
                    aktif="",
                ),
            )

        def kerja() -> tulis.HasilTulis:
            hasil = dengan_basis(lambda s: tulis.jalankan_permintaan(permintaan, s))
            if hasil.berhasil and permintaan.muat_ulang:
                # Layar yang membaca baris yang baru ditulis tidak boleh menampilkan hasil lama.
                for awalan in ("dasbor", "emiten", "jurnal", "risiko"):
                    self.pekerjaan.lupakan(awalan)
            return hasil

        with self._kunci:
            self._tulis[token] = (permintaan.judul, kembali)
        self.pekerjaan.mulai(("tulis", token), kerja)
        return Jawaban(HTTPStatus.SEE_OTHER, lokasi=h.tautan("/hasil", id=token))

    def hasil_tulis(self, kueri: dict[str, str]) -> Jawaban:
        token = kueri.get("id", "")
        with self._kunci:
            catatan = self._tulis.get(token)
        pekerjaan = self.pekerjaan.ambil(("tulis", token))
        if catatan is None or pekerjaan is None:
            return Jawaban(
                HTTPStatus.NOT_FOUND,
                h.kerangka("Tidak ditemukan", h.pesan("Hasil penulisan ini tidak dikenal.", "galat"), aktif=""),
            )
        judul, kembali = catatan

        def tampilkan(hasil: tulis.HasilTulis) -> str:
            return h.pesan(hasil.pesan, "oke" if hasil.berhasil else "galat") + (
                f'<p><a href="{h.e(kembali)}">Kembali</a></p>'
            )

        return self._tunggu_atau(pekerjaan, judul, "", tampilkan)

    def ikon(self, kueri: dict[str, str]) -> Jawaban:
        del kueri
        return Jawaban(HTTPStatus.OK, IKON.read_text(encoding="utf-8"), jenis="image/svg+xml")

    def berkas(self, kueri: dict[str, str]) -> Jawaban:
        del kueri
        try:
            folder_bawaan = str(lokasi.folder_konfigurasi())
            daftar = tulis.ringkasan_daftar_cadangan()
        except Exception as galat:  # noqa: BLE001 — tampil di halaman, bukan ditelan
            return self._galat_halaman("Impor & cadangan", "/berkas", f"{type(galat).__name__}: {galat}")
        isi = (
            "<h2>Impor berkas</h2>"
            + h.kartu(
                h.borang_tulis(
                    "impor",
                    self.csrf,
                    f"<label>Folder berisi berkas CSV{h.isian('folder', folder_bawaan, lebar=60)}</label>",
                    "Baca folder",
                    tersembunyi={"kembali": "/berkas"},
                )
                + "<p class=redup>Folder dibaca lebih dulu; konfirmasi menyebut jumlah baris per "
                "tabel sebelum apa pun ditulis — sama dengan <code>--impor</code>.</p>"
            )
            + self._bagian_folder_pantau()
            + self._bagian_unggah_ringkasan()
            + self._bagian_unggah_notasi()
            + self._bagian_unggah_pengumuman()
            + "<h2>Cadangan</h2>"
            + h.kartu(
                h.borang_tulis(
                    "cadangan", self.csrf, "", "Cadangkan basis data", tersembunyi={"kembali": "/berkas"}
                )
                + "<h2>Daftar cadangan</h2>"
                + h.pra(daftar)
            )
        )
        return Jawaban(HTTPStatus.OK, h.kerangka("Impor & cadangan", isi, aktif="/berkas"))

    def _bagian_folder_pantau(self) -> str:
        """Impor unduhan IDX dari folder pantau (K101) — pengganti tiga unggahan di bawah."""
        sasaran = folder_pantau.folder()
        if sasaran is None:
            keadaan = (
                "<p class=redup>Folder pantau belum diatur. Isi foldernya di sini, atau atur "
                f"variabel lingkungan <code>{folder_pantau.ENV_FOLDER_PANTAU}</code> supaya "
                "<code>--impor-unduhan</code> (Task Scheduler) memakai folder yang sama.</p>"
            )
        else:
            try:
                keadaan = h.pra(folder_pantau.pindai(sasaran).ringkas())
            except folder_pantau.GalatFolderPantau as galat:
                keadaan = h.pesan(str(galat), "galat")
        return (
            "<h2>Impor unduhan IDX dari folder pantau</h2>"
            + h.kartu(
                "<p>Simpan unduhan IDX (Ringkasan Saham, Notasi Khusus, PDF pengumuman) ke satu "
                "folder dengan nama aslinya, lalu impor semuanya sekaligus. Cadangan dibuat lebih "
                "dulu; berkas yang selesai dipindah ke <code>unduhan-idx</code>, yang ditolak "
                "tetap di folder dengan sebabnya (K101). Pengunduhannya tetap manual (K95).</p>"
                + h.borang_tulis(
                    "impor-unduhan",
                    self.csrf,
                    "<label>Folder pantau"
                    f"{h.isian('folder', str(sasaran) if sasaran else '', lebar=60)}</label>",
                    "Baca folder",
                    tersembunyi={"kembali": "/berkas"},
                )
                + keadaan
            )
        )

    def _bagian_unggah_ringkasan(self) -> str:
        """Unggah Ringkasan Saham IDX (K95): diunduh pengguna, bukan diambil aplikasi."""
        try:
            akhir = unggahan_idx.terakhir()
        except (OSError, ValueError, KeyError) as galat:
            keadaan = h.galat(f"daftar unggahan tidak terbaca — {type(galat).__name__}: {galat}", None)
        else:
            keadaan = (
                "<p class=redup>Belum ada unggahan.</p>"
                if akhir is None
                else "<p class=redup>Unggahan terakhir "
                f"{h.e(tampilan.tanggal(akhir.diunggah_pada.date()))} "
                f"{akhir.diunggah_pada:%H.%M}: {h.e(akhir.nama_asli)}.</p>"
            )
        antrean = self._antrean_impor_ringkasan()
        alamat = h.e(unggahan_idx.ALAMAT_RINGKASAN_SAHAM)
        return (
            "<h2>Ringkasan Saham IDX (sumber harga kedua)</h2>"
            + h.kartu(
                f'<p>Unduh dari <a href="{alamat}" target=_blank rel=noopener>halaman Ringkasan '
                "Saham IDX</a> (tombol <strong>Unduh</strong>) sesudah bursa tutup — seminggu sekali untuk cek sumber kedua, setiap hari bursa bila sambungan harga resmi berlaku — "
                "lalu unggah di sini. Hari yang terlewat boleh diunggah belakangan, dan beberapa "
                "berkas boleh dipilih sekaligus (K97). Aplikasi tidak mengambilnya sendiri: "
                "Syarat Penggunaan IDX melarang scraping (K95).</p>"
                + '<form class=borang method=post action="/unggah/ringkasan-saham" '
                'enctype="multipart/form-data">'
                + f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
                + "<label>Berkas unduhan<input type=file name=berkas multiple required "
                f'accept="{",".join(unggahan_idx.AKHIRAN_DITERIMA)}"></label>'
                + "<button>Unggah</button></form>"
                + keadaan
                + antrean
                + "<p class=redup>Berkas disimpan mentah apa adanya (SHA-256 dicatat). Isinya masuk "
                "basis data sebagai harga pembanding hanya sesudah impornya dikonfirmasi.</p>"
            )
        )

    def _bagian_unggah_notasi(self) -> str:
        """Unggah Notasi Khusus IDX (K96): diunduh pengguna, bukan diambil aplikasi."""
        return (
            "<h2>Notasi Khusus IDX</h2>"
            + h.kartu(
                f'<p>Unduh dari <a href="{h.e(notasi.ALAMAT_UNDUHAN)}" target=_blank rel=noopener>'
                "halaman Notasi Khusus IDX</a> (tombol <strong>Unduh</strong>) — mingguan, atau "
                "begitu IDX menerbitkan daftar baru — lalu unggah di sini dengan nama aslinya "
                "(<code>Notasi Khusus-YYYYMMDD.xlsx</code>; tanggal datanya dibaca dari nama itu). "
                "Aplikasi tidak mengambilnya sendiri (K96).</p>"
                + '<form class=borang method=post action="/unggah/notasi-khusus" '
                'enctype="multipart/form-data">'
                + f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
                + '<label>Berkas unduhan<input type=file name=berkas required accept=".xlsx"></label>'
                + "<button>Unggah dan baca</button></form>"
                + "<p class=redup>Berkas disimpan mentah apa adanya. Halaman berikutnya menyebut "
                "jumlah emiten, baris baru, dan baris yang ditutup; basis data dan "
                "<code>notasi-khusus.csv</code> baru berubah sesudah Anda menekan Tulis. Suspensi dan "
                "UMA tidak ikut diperbarui oleh berkas ini — unggah PDF pengumumannya di bawah.</p>"
            )
        )

    def _bagian_unggah_pengumuman(self) -> str:
        """Unggah PDF pengumuman suspensi & UMA IDX (K99): satu pengumuman satu berkas."""
        return (
            "<h2>Pengumuman suspensi &amp; UMA IDX (PDF)</h2>"
            + h.kartu(
                "<p>Unduh PDF tiap pengumuman suspensi dan UMA dari "
                f'<a href="{h.e(pengumuman_idx.ALAMAT_PENGUMUMAN)}" target=_blank rel=noopener>'
                "halaman Pengumuman IDX</a> (menu Berita) — "
                "mis. <code>20261028-UMA_COIN.pdf</code>, "
                "<code>20261028-WAS_Suspensi_PTSP.pdf</code> — lalu unggah di sini; beberapa berkas "
                "boleh dipilih sekaligus. Suspensi dicatat mulai tanggal berlakunya (K99); PDF "
                "pembukaan kembali (UPT) menutupnya sehari sebelum tanggal dibuka (K100). "
                "Pengumuman multi-kode belum dibaca dan akan ditolak dengan sebabnya.</p>"
                + '<form class=borang method=post action="/unggah/pengumuman-idx" '
                'enctype="multipart/form-data">'
                + f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
                + '<label>Berkas PDF<input type=file name=berkas multiple required accept=".pdf"></label>'
                + "<button>Unggah dan baca</button></form>"
                + "<p class=redup>Berkas disimpan mentah apa adanya. Unggahan hanya menambah baris: "
                "pengumuman yang tidak diunggah tidak terdeteksi, jadi jadwal tidak menilai "
                "kelengkapannya. Basis data dan <code>notasi-khusus.csv</code> baru berubah sesudah "
                "Anda menekan Tulis.</p>"
            )
        )

    def unggah_notasi_khusus(self, unggahan: Unggahan) -> Jawaban:
        judul = "Unggah Notasi Khusus IDX"
        berkas = unggahan.get("berkas") or []
        if len(berkas) != 1:
            return self._galat_halaman(judul, "/berkas", "pilih tepat satu berkas Notasi Khusus")
        ((nama, isi),) = berkas
        try:
            jalur = notasi.simpan_unduhan(nama, isi)
            permintaan = dengan_basis(
                lambda s: tulis.permintaan_impor_notasi_idx(s, jalur=jalur, nama_asli=nama)
            )
        except (notasi.GalatNotasi, tulis.GalatTulis, lokasi.GalatLokasi, OSError) as galat:
            return self._galat_halaman(judul, "/berkas", f"{nama}: {galat}")
        return self._konfirmasi(
            permintaan, "/berkas", h.pesan(f"{nama}: tersimpan mentah di {jalur}.", "oke")
        )

    def unggah_pengumuman_idx(self, unggahan: Unggahan) -> Jawaban:
        judul = "Unggah PDF pengumuman suspensi & UMA IDX"
        berkas = unggahan.get("berkas") or []
        if not berkas:
            return self._galat_halaman(judul, "/berkas", "tidak ada berkas yang dikirim — pilih PDF-nya dulu")
        try:
            tersimpan = [(pengumuman_idx.simpan_unduhan(nama, isi), nama) for nama, isi in berkas]
            permintaan = dengan_basis(
                lambda s: tulis.permintaan_impor_pengumuman_idx(s, berkas=tersimpan)
            )
        except (pengumuman_idx.GalatPengumuman, tulis.GalatTulis, lokasi.GalatLokasi, OSError) as galat:
            return self._galat_halaman(judul, "/berkas", str(galat))
        return self._konfirmasi(
            permintaan,
            "/berkas",
            h.pesan(f"{len(tersimpan)} PDF tersimpan mentah di {tersimpan[0][0].parent}.", "oke"),
        )

    def _terbaca(self, unggahan: unggahan_idx.Unggahan) -> str:
        """Isi satu unggahan dibaca dulu, supaya bentuk yang salah terlihat di sini, bukan baru
        di halaman konfirmasi."""
        try:
            isi = unggahan_idx.baca(unggahan.berkas)
        except (unggahan_idx.GalatUnggahan, OSError) as galat:
            return h.pesan(f"Isi berkas tidak terbaca: {galat}", "galat")
        return h.pesan(
            f"Terbaca: Ringkasan Saham {tampilan.tanggal(isi.tanggal)}, "
            f"{tampilan.angka(len(isi.baris), 0)} emiten.",
            "oke",
        )

    def _antrean_impor_ringkasan(self) -> str:
        """Unggahan yang tanggalnya belum ada di basis data, dan satu tombol untuk mengimpornya."""
        try:
            antrean = dengan_basis(unggahan_idx.antrean_impor)
        except (OSError, ValueError, KeyError, sqlite3.Error, lokasi.GalatLokasi) as galat:
            return h.galat(f"antrean impor tidak terbaca — {type(galat).__name__}: {galat}", None)
        bagian = []
        if antrean.siap:
            daftar_tanggal = ", ".join(tampilan.tanggal(hari) for _, hari in antrean.siap)
            bagian.append(
                h.pesan(f"{len(antrean.siap)} berkas siap diimpor: {daftar_tanggal}.", "oke")
                + h.borang_tulis(
                    "impor-ringkasan",
                    self.csrf,
                    "",
                    f"Impor {len(antrean.siap)} berkas",
                    tersembunyi={
                        "berkas": ",".join(satu.berkas.name for satu, _ in antrean.siap),
                        "kembali": "/berkas",
                    },
                )
            )
        if antrean.menunggu:
            snapshot = (
                tampilan.tanggal(antrean.tanggal_snapshot) if antrean.tanggal_snapshot else "(belum ada)"
            )
            bagian.append(
                h.pesan(
                    "Menunggu: "
                    + ", ".join(tampilan.tanggal(hari) for _, hari in antrean.menunggu)
                    + f" — sesudah snapshot terakhir ({snapshot}). Tekan \"Perbarui data\" dulu, "
                    "lalu impor dari sini.",
                )
            )
        if antrean.diganti:
            bagian.append(
                "<p class=redup>Tidak dipakai (ada unggahan lebih baru bertanggal sama): "
                + h.e(", ".join(satu.nama_asli for satu in antrean.diganti))
                + ".</p>"
            )
        for satu, sebab in antrean.tak_terbaca:
            bagian.append(h.pesan(f"{satu.nama_asli}: isi berkas tidak terbaca — {sebab}", "galat"))
        if not bagian:
            return "<p class=redup>Tidak ada unggahan yang belum diimpor.</p>"
        return "".join(bagian)

    def unggah_ringkasan_saham(self, unggahan: Unggahan) -> Jawaban:
        judul = "Unggah Ringkasan Saham IDX"
        kembali = '<p><a href="/berkas">Kembali ke Impor &amp; cadangan</a></p>'
        berkas = unggahan.get("berkas") or []
        if not berkas:
            return self._galat_halaman(judul, "/berkas", "tidak ada berkas yang dikirim — pilih berkasnya dulu")
        hasil_semua = []
        for nama, isi in berkas:
            try:
                hasil = unggahan_idx.simpan(nama, isi)
            except (unggahan_idx.GalatUnggahan, lokasi.GalatLokasi, OSError) as galat:
                hasil_semua.append(h.pesan(f"Unggahan ditolak ({nama}): {galat}", "galat"))
                continue
            hasil_semua.append(
                h.pesan(f"{nama}: {hasil.ringkas()}", "oke") + self._terbaca(hasil.unggahan)
            )
        self.pekerjaan.lupakan("dasbor")
        return Jawaban(
            HTTPStatus.OK,
            h.kerangka(
                judul,
                "".join(hasil_semua)
                + "<h2>Belum diimpor</h2>"
                + self._antrean_impor_ringkasan()
                + kembali,
                aktif="/berkas",
            ),
        )

    def dasbor(self, kueri: dict[str, str]) -> Jawaban:
        kunci = ("dasbor",)
        if kueri.get("segarkan"):
            self.pekerjaan.mulai(kunci, _tugas_dasbor, ulang=True)
            return Jawaban(HTTPStatus.SEE_OTHER, lokasi="/")
        # Snapshot/skor bisa ditulis di luar server ini (`--saring`, `--refresh` dari baris
        # perintah) atau oleh saringan yang selesai sesudah dasbor dihitung. Dasbor jadi yang
        # tandanya sudah tidak cocok dihitung ulang, bukan ditampilkan dengan kandidat lama.
        lama = self.pekerjaan.ambil(kunci)
        basi = (
            lama is not None
            and isinstance(lama.hasil, HasilDasbor)
            and lama.hasil.tanda != _tanda_sekarang()
        )
        pekerjaan = self.pekerjaan.mulai(kunci, _tugas_dasbor, ulang=basi)

        def tampilkan(hasil_kerja: HasilDasbor) -> str:
            hasil = hasil_kerja.dasbor
            peringatan: list[str] = []
            if hasil.id_snapshot is None:
                peringatan.append(
                    "BELUM ADA SNAPSHOT: tekan \"Perbarui data\" di atas (atau `--refresh`); "
                    "kandidat dan mutu data belum bisa ditampilkan"
                )
            elif hasil.snapshot_basi:
                peringatan.append(
                    "SNAPSHOT BUKAN DARI HARI BURSA TERAKHIR (AC-8): angka di layar ini berasal "
                    f"dari {hasil.tanggal_data} sedangkan hari bursa terakhir "
                    f"{hasil.hari_bursa_terakhir}"
                )
            keadaan = (
                h.pesan("\n".join(peringatan), "galat") if peringatan else h.pesan("Data siap.", "oke")
            )
            asal_skor = (
                f" (preset {hasil.id_preset_skor}, snapshot #{hasil.id_snapshot})"
                if hasil.kandidat_teratas
                else ""
            )
            return (
                keadaan
                + '<p><a href="/?segarkan=1">Muat ulang</a></p>'
                + "<h2>Tindakan menunggu</h2>"
                + h.tabel(tabel.kepala_tindakan(), tabel.isi_tindakan(hasil.tindakan))
                + self._borang_stop(hasil)
                + (
                    f"<h2>Peringkat sementara dari skor tersimpan{h.e(asal_skor)}</h2>"
                    + h.pesan(
                        "PERINGKAT SEMENTARA — BELUM BOLEH DISEBUT KANDIDAT. Sebabnya: "
                        f"{hasil.sebab_sementara}.",
                        "galat",
                    )
                    if hasil.kandidat_teratas and hasil.sebab_sementara
                    else f"<h2>Kandidat teratas dari skor tersimpan{h.e(asal_skor)}</h2>"
                )
                + (
                    # Saringan preset lain menulis tabelnya di tempat yang sama (aturan keras 9).
                    "<p class=redup>Skor hanya sebanding di dalam satu preset.</p>"
                    if hasil.kandidat_teratas
                    else ""
                )
                + h.tabel(
                    tabel.kepala_kandidat_dasbor(),
                    tabel.isi_kandidat_dasbor(hasil.kandidat_teratas),
                    tautan_kolom={1: "/emiten?kode={nilai}"},
                )
                + self._bagian_jadwal()
                + "<h2>Halaman keadaan (sama dengan <code>--dasbor</code>)</h2>"
                + h.pra(hasil.ringkas())
            )

        return self._tunggu_atau(
            pekerjaan,
            "Dasbor harian",
            "/",
            tampilkan,
            kepala=self._perlu_diperbarui() + self._kartu_pembaruan(),
        )

    # -- pemberitahuan saat dasbor dibuka (K104) --------------------------------------

    def _perlu_diperbarui(self) -> str:
        """Apa yang belum diperbarui, ditampilkan saat dasbor dibuka (K104).

        Pengganti tugas terjadwal K101/K102: pengguna memperbarui ketika ia mau, jadi
        pengingatnya muncul ketika aplikasi dibuka — bukan pada jam tertentu. Isinya diturunkan
        dari jadwal (K93), pengingat unduh K95, dan folder pantau (K101); tidak ada aturan baru.
        Ditaruh di kepala halaman supaya tampil sebelum hitungan dasbor selesai. Kosong bila
        tidak ada yang perlu dikerjakan.
        """
        butir: list[str] = []
        try:
            daftar = pengingat.saat_dibuka(dengan_basis(jadwal.susun))
            unduh = dengan_basis(unggahan_idx.pengingat)
        except Exception as galat:  # noqa: BLE001 — tampil di halaman, bukan ditelan
            return h.galat(f"pemberitahuan pembaruan — {type(galat).__name__}: {galat}", None)
        for satu in daftar:
            tautan = (
                f' · <a href="{h.e(satu.alamat)}" target=_blank rel=noopener>buka halaman IDX</a>'
                if satu.alamat
                else ""
            )
            butir.append(
                f"<li><b>{h.e(satu.nama)}</b> — {h.e(satu.status)}: {h.e(satu.bukti)}{tautan}"
                f"<br><span class=redup>{h.e(satu.tindakan)}</span></li>"
            )
        if unduh is not None:
            butir.append(f"<li>{h.e(unduh)}</li>")
        butir += self._unduhan_belum_diimpor()
        if not butir:
            return ""
        return (
            '<div class="kartu perlu" id=perlu-diperbarui><b>Perlu diperbarui</b><ul>'
            + "".join(butir)
            + '</ul><p class=redup>Tidak ada yang dijalankan otomatis. Harga: tombol "Perbarui '
            'data" di bawah. Berkas IDX: unduh dari situsnya, lalu <a href="/berkas">Impor &amp; '
            "cadangan</a>.</p></div>"
        )

    def _unduhan_belum_diimpor(self) -> list[str]:
        """Berkas IDX yang sudah diunduh ke folder pantau tetapi isinya belum diimpor (K101).

        Berkas yang isinya sudah ada (mis. diimpor lewat unggahan dasbor) tidak diberitahukan.
        Jalan impor terakhir yang gagal (mis. dari Task Scheduler) diberitahukan sampai ada jalan
        yang berhasil — termasuk bila folder pantau belum diatur, karena itu sebab yang mungkin.
        """
        butir: list[str] = []
        jalan = dengan_basis(folder_pantau.jalan_terakhir)
        if jalan is not None and not jalan.berhasil:
            butir.append(
                f"<li><b>Impor unduhan IDX</b> — jalan terakhir gagal "
                f"{h.e(tampilan.tanggal(jalan.waktu.date()))} {jalan.waktu:%H.%M}: "
                f"{h.e(_baris_gagal(jalan.pesan))} · "
                '<a href="/berkas">ulangi di Impor &amp; cadangan</a></li>'
            )
        sasaran = folder_pantau.folder()
        if sasaran is None:
            return butir
        try:
            pindaian = folder_pantau.pindai(sasaran)
            siap = dengan_basis(lambda s: tulis.jumlah_belum_diimpor(s, pindaian))
        except (folder_pantau.GalatFolderPantau, notasi.GalatNotasi) as galat:
            return [*butir, f"<li><b>Folder pantau</b> — {h.e(galat)}</li>"]
        bagian = [f"{siap} berkas IDX belum diimpor"] if siap else []
        if pindaian.ditolak:
            bagian.append(f"{len(pindaian.ditolak)} ditolak (isinya tidak terbaca)")
        if not bagian:
            return butir
        return [
            *butir,
            f"<li><b>Folder pantau</b> — {h.e(', '.join(bagian))} di {h.e(sasaran)} · "
            '<a href="/berkas">impor di Impor &amp; cadangan</a></li>'
        ]

    # -- pembaruan data (K92) ---------------------------------------------------------

    def _kartu_pembaruan(self) -> str:
        pekerjaan = self.pekerjaan.ambil(KUNCI_PERBARUI)
        if pekerjaan is not None and pekerjaan.berjalan:
            return h.kartu(
                self._isi_kemajuan(pekerjaan, ringkas=True)
                + '<p><a href="/perbarui">Lihat kemajuan pembaruan</a></p>'
            )
        return h.kartu(
            '<form class=baris-tombol method=post action="/perbarui">'
            f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
            "<button>Perbarui data</button>"
            "<span class=redup>Mengambil harga hari ini, menulis snapshot, mencadangkan, lalu "
            "menjalankan saringan — sama dengan <code>--refresh --saring</code>.</span></form>"
        )

    def minta_perbarui(self, isian: dict[str, str]) -> Jawaban:
        """Tombol "Perbarui data": beri tahu bila sudah terbaru; selain itu minta konfirmasi."""
        judul = "Perbarui data"
        pekerjaan = self.pekerjaan.ambil(KUNCI_PERBARUI)
        if pekerjaan is not None and pekerjaan.berjalan:
            return Jawaban(HTTPStatus.SEE_OTHER, lokasi="/perbarui")
        try:
            keadaan = dengan_basis(pembaruan.keadaan)
        except Exception as galat:  # noqa: BLE001 — tampil di halaman, bukan ditelan
            return self._galat_halaman(judul, "/", f"{type(galat).__name__}: {galat}")
        if keadaan.terbaru and not isian.get("paksa"):
            isi = (
                h.pesan(
                    f"Data sudah paling baru: snapshot #{keadaan.id_snapshot} berisi data "
                    f"{_tanggal_teks(keadaan.tanggal_data)}, sama dengan hari bursa terakhir. "
                    "Tidak ada yang perlu diperbarui.",
                    "oke",
                )
                + "<p class=redup>Bila sebagian emiten belum punya harga hari ini (sumber data "
                "sering terlambat beberapa jam), pembaruan ulang bisa melengkapinya. Itu "
                "menulis snapshot baru dan satu cadangan lagi.</p>"
                + '<form class=baris-tombol method=post action="/perbarui">'
                + f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
                + "<input type=hidden name=paksa value=1>"
                + '<a class=tombol-kedua href="/">Ke dasbor</a>'
                + "<button class=kedua>Tetap perbarui…</button></form>"
            )
            return Jawaban(HTTPStatus.OK, h.kerangka(judul, isi, aktif="/"))

        token = secrets.token_urlsafe(16)
        sekarang = time.monotonic()
        with self._kunci:
            for lama in [k for k, w in self._token_perbarui.items() if sekarang - w > BATAS_KONFIRMASI]:
                del self._token_perbarui[lama]
            self._token_perbarui[token] = sekarang
        if keadaan.id_snapshot is None:
            keadaan_teks = "Belum ada snapshot."
        else:
            keadaan_teks = (
                f"Snapshot terakhir #{keadaan.id_snapshot}, data "
                f"{_tanggal_teks(keadaan.tanggal_data)}; hari bursa terakhir "
                f"{_tanggal_teks(keadaan.hari_bursa_terakhir)}."
            )
        ringkasan = (
            f"{keadaan_teks}\n\n"
            "Yang akan dikerjakan, berurutan:\n"
            + "\n".join(f"  {i}. {tahap}" for i, tahap in enumerate(pembaruan.TAHAP, start=1))
            + "\n\nPengambilan ±970 emiten makan waktu sekitar 20 menit. Snapshot lama tidak "
            "diubah (data append-only); cadangan yang disimpan 3 terbaru, dan arsip snapshot tidak "
            "pernah dihapus. Bila dijalankan sebelum bursa tutup, harga hari ini bisa belum final."
        )
        isi = (
            h.pra(ringkasan, bungkus=True)
            + "<p><strong>Mulai pembaruan sekarang?</strong></p>"
            + '<form method=post action="/perbarui/mulai" class=baris-tombol>'
            + f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
            + f'<input type=hidden name=token value="{h.e(token)}">'
            + "<button name=jawab value=mulai>Mulai pembaruan</button>"
            + "<button class=kedua name=jawab value=batal>Batal</button></form>"
        )
        return Jawaban(HTTPStatus.OK, h.kerangka(f"Konfirmasi: {judul}", isi, aktif="/"))

    def mulai_perbarui(self, isian: dict[str, str]) -> Jawaban:
        with self._kunci:
            sah = self._token_perbarui.pop(isian.get("token", ""), None) is not None
        if not sah:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    "Konfirmasi tidak berlaku",
                    h.pesan(
                        "Konfirmasi ini sudah dipakai, kedaluwarsa, atau berasal dari server yang "
                        "sudah dijalankan ulang. Pembaruan tidak dimulai dari pengiriman ini.",
                        "galat",
                    )
                    + '<p><a href="/">Ke dasbor</a></p>',
                    aktif="/",
                ),
            )
        if isian.get("jawab") != "mulai":
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    "Dibatalkan",
                    h.pesan("Dibatalkan: pembaruan tidak dimulai.")
                    + '<p><a href="/">Ke dasbor</a></p>',
                    aktif="/",
                ),
            )

        def lapor(kemajuan: pembaruan.Kemajuan) -> None:
            with self._kunci:
                self._kemajuan = kemajuan

        def kerja() -> pembaruan.HasilPembaruan:
            lapor(pembaruan.Kemajuan(pembaruan.MENGAMBIL))
            hasil = pembaruan.jalankan(
                self.buat_pengambil(pembaruan.lapor_per_emiten(lapor)),
                lapor=lapor,
            )
            # Layar yang membaca snapshot lama tidak boleh menampilkan hasil yang sudah usang.
            for awalan in ("dasbor", "saring", "emiten", "risiko", "jurnal"):
                self.pekerjaan.lupakan(awalan)
            return hasil

        self.pekerjaan.mulai(KUNCI_PERBARUI, kerja, ulang=True)
        return Jawaban(HTTPStatus.SEE_OTHER, lokasi="/perbarui")

    def _isi_kemajuan(self, pekerjaan: Pekerjaan, *, ringkas: bool = False) -> str:
        with self._kunci:
            kemajuan = self._kemajuan
        tahap = kemajuan.tahap if kemajuan is not None else pembaruan.MENGAMBIL
        menit, detik = divmod(int(pekerjaan.lama_detik), 60)
        kepala = (
            f"<p><strong>Tahap {pembaruan.TAHAP.index(tahap) + 1} dari {len(pembaruan.TAHAP)}: "
            f"{h.e(tahap)}</strong> <span class=redup>· berjalan {menit} mnt {detik} dtk</span></p>"
        )
        if kemajuan is not None and tahap == pembaruan.MENGAMBIL and kemajuan.dari:
            persen = 100 * kemajuan.nomor // kemajuan.dari
            batang = (
                f'<progress max="{kemajuan.dari}" value="{kemajuan.nomor}"></progress>'
                f"<p>{kemajuan.nomor} dari {kemajuan.dari} emiten ({persen}%)"
                f" · terakhir: {h.e(kemajuan.kode)} · gagal diambil: {kemajuan.gagal}</p>"
            )
        else:
            # Tahap tanpa hitungan per emiten: batang tanpa nilai (berjalan, sisanya belum diketahui).
            batang = "<progress></progress>"
        if ringkas:
            return kepala + batang
        return (
            kepala
            + batang
            + "<p class=redup>Halaman ini memuat ulang sendiri. Boleh ditinggal ke layar lain — "
            "pembaruan tetap berjalan selama jendela MejaSaham (cmd) terbuka.</p>"
        )

    def kemajuan_perbarui(self, kueri: dict[str, str]) -> Jawaban:
        del kueri
        judul = "Perbarui data"
        ke_dasbor = '<p><a href="/">Ke dasbor</a></p>'
        pekerjaan = self.pekerjaan.ambil(KUNCI_PERBARUI)
        if pekerjaan is None:
            isi = h.pesan("Belum ada pembaruan yang dijalankan sejak server dibuka.") + ke_dasbor
            return Jawaban(HTTPStatus.OK, h.kerangka(judul, isi, aktif="/"))
        if pekerjaan.berjalan:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    judul,
                    h.kartu(self._isi_kemajuan(pekerjaan)),
                    aktif="/",
                    muat_ulang_detik=DETIK_MUAT_ULANG,
                ),
            )
        if pekerjaan.galat is not None:
            isi = h.galat(pekerjaan.galat, pekerjaan.jejak) + ke_dasbor
            return Jawaban(HTTPStatus.OK, h.kerangka(judul, isi, aktif="/"))
        hasil: pembaruan.HasilPembaruan = pekerjaan.hasil
        menit, detik = divmod(int(pekerjaan.lama_detik), 60)
        if hasil.berhasil:
            kalimat = h.pesan(
                f"Pembaruan selesai dalam {menit} mnt {detik} dtk: snapshot "
                f"#{hasil.refresh.id_snapshot} tersimpan, cadangan dibuat, saringan dijalankan.",
                "oke",
            )
        elif hasil.refresh.sukses:
            kalimat = h.pesan(
                f"Snapshot #{hasil.refresh.id_snapshot} tersimpan, tetapi langkah sesudahnya "
                f"GAGAL: {hasil.galat_lanjutan}",
                "galat",
            )
        else:
            kalimat = h.pesan(f"GAGAL — tidak ada snapshot baru: {hasil.refresh.pesan}", "galat")
        isi = kalimat + ke_dasbor + self._bagian_jadwal() + "<h2>Rincian</h2>" + h.pra(hasil.ringkas())
        return Jawaban(HTTPStatus.OK, h.kerangka(judul, isi, aktif="/"))

    def _bagian_jadwal(self) -> str:
        """Daftar periksa jadwal pembaruan (K93). Dibaca saat halaman disusun — cepat, dan tidak
        boleh basi terhadap pembaruan yang baru selesai."""
        try:
            daftar = dengan_basis(jadwal.susun)
        except Exception as galat:  # noqa: BLE001 — tampil di halaman, bukan ditelan
            return "<h2>Jadwal pembaruan data</h2>" + h.galat(f"{type(galat).__name__}: {galat}", None)
        return (
            "<h2>Jadwal pembaruan data</h2>"
            + "<p class=redup>Hanya memberi tahu — tidak ada yang dijalankan otomatis (K89). "
            "Statusnya dibaca dari tanggal isi data, bukan dari kapan berkas terakhir dibaca.</p>"
            + h.tabel(tabel.kepala_jadwal(), tabel.isi_jadwal(daftar))
        )

    def _borang_stop(self, hasil: dasbor.Dasbor) -> str:
        """Ubah stop di dasbor — tempat tindakannya dituntut (aksi #19d/K62)."""
        if not hasil.posisi_aktif:
            return ""
        pilihan = (("", tabel.PILIH_POSISI),) + tuple(
            (str(r.posisi.id_posisi), tabel.label_posisi(r.posisi)) for r in hasil.posisi_aktif
        )
        return (
            "<h2>Ubah stop posisi</h2>"
            + h.kartu(
                h.borang_tulis(
                    "stop",
                    self.csrf,
                    f"<label>Posisi{h.pilihan('id_posisi', pilihan, '')}</label>"
                    f"<label>Stop baru{h.isian('stop', '', petunjuk='wajib, rupiah', lebar=10)}</label>"
                    f"<label>Tanggal{h.isian('tanggal', '', petunjuk='YYYY-MM-DD · kosong = hari ini', lebar=16)}</label>"
                    f"<label>Alasan{h.isian('alasan', '', petunjuk='kosong = tanpa alasan', lebar=24)}</label>",
                    "Ubah stop",
                    tersembunyi={"kembali": "/"},
                )
                + "<p class=redup>Tanggal menjadi <code>tgl_stop</code> — basis level stop (PRD 9.11). "
                "Menaikkan stop adalah trailing yang sah; menurunkannya tidak ditolak, tetapi "
                "tercatat sebagai pelanggaran V5 (PRD 9.8).</p>"
            )
        )

    def screener(self, kueri: dict[str, str]) -> Jawaban:
        try:
            daftar = self._daftar_preset()
        except Exception as galat:  # noqa: BLE001 — tampil di halaman, bukan ditelan
            return self._galat_halaman("Screener", "/screener", f"{type(galat).__name__}: {galat}")
        if not daftar:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    "Screener",
                    h.pesan(
                        "Belum ada preset tersimpan. Jalankan `--preset-bawaan` lebih dulu (K6: "
                        "preset adalah baris berversi di basis data, bukan konstanta di kode).",
                        "galat",
                    ),
                    aktif="/screener",
                ),
            )
        id_preset = kueri.get("preset") or daftar[0][0]
        try:
            teratas = max(1, min(200, int_atau_none(kueri.get("teratas"), "Teratas") or 20))
        except GalatIsian as galat:
            return self._galat_halaman("Screener", "/screener", str(galat))
        kode_rinci = (kueri.get("kode") or "").strip().upper()
        borang = h.kartu(
            '<form class=borang method=post action="/screener">'
            f'<input type=hidden name=csrf value="{h.e(self.csrf)}">'
            f"<label>Preset{h.pilihan('preset', daftar, id_preset)}</label>"
            f"<label>Teratas{h.isian('teratas', str(teratas), lebar=4)}</label>"
            "<button>Jalankan saringan</button></form>"
            '<p class=redup>Menjalankan saringan menyimpan skornya ke basis data, sama seperti '
            "<code>--saring</code>; dasbor membaca skor tersimpan itu.</p>"
        )
        pekerjaan = self.pekerjaan.ambil(("saring", id_preset))
        if pekerjaan is None:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(
                    "Screener",
                    borang + h.pesan("Pilih preset, lalu tekan Jalankan saringan."),
                    aktif="/screener",
                ),
            )

        def tampilkan(laporan: pengatur.LaporanSaring) -> str:
            daftar_teratas = laporan.teratas(teratas)
            teks = laporan.ringkas()
            if not daftar_teratas:
                teks += "\n" + laporan.catatan_peringkat_kosong()
            if not laporan.peringkat_sementara:
                status = h.pesan("Hasil saringan: kandidat (data notasi khusus ada).", "oke")
            else:
                status = h.pesan(
                    "PERINGKAT SEMENTARA — BELUM BOLEH DISEBUT KANDIDAT. Sebabnya: "
                    f"{laporan.sebab_sementara()}.",
                    "galat",
                )
            rinci = ""
            if kode_rinci:
                isi = next((s for s in laporan.hasil_saring if s.kode == kode_rinci), None)
                rinci = f"<h2>Rincian kriteria {h.e(kode_rinci)}</h2>" + (
                    h.pesan(isi.ringkas()) + h.tabel(tabel.kepala_kriteria(), tabel.isi_kriteria(isi.penilaian))
                    if isi is not None
                    else h.pesan(f"{kode_rinci}: tidak ada rincian kriteria pada laporan ini.")
                )
            pola = h.tautan("/screener", preset=id_preset, teratas=teratas) + "&kode={nilai}"
            kolom_kode = tabel.kepala_skor().index("kode")
            return (
                status
                + f"<p class=redup>Snapshot #{laporan.id_snapshot} · preset {h.e(laporan.id_preset)}"
                + f" · sumber harga {h.e(laporan.sumber_harga or tabel.KOSONG)}</p>"
                + h.tabel(
                    tabel.kepala_skor(),
                    tabel.isi_skor(daftar_teratas),
                    tautan_kolom={kolom_kode: pola},
                    kosong="Tidak ada emiten yang diperingkat.",
                )
                + rinci
                + "<h2>Ringkasan (sama dengan <code>--saring</code>)</h2>"
                + h.pra(teks)
            )

        return self._tunggu_atau(pekerjaan, "Screener", "/screener", tampilkan, kepala=borang)

    def jalankan_screener(self, kueri: dict[str, str]) -> Jawaban:
        id_preset = kueri.get("preset", "")
        if not id_preset:
            return self._galat_halaman("Screener", "/screener", "Preset belum dipilih.")

        def kerja() -> pengatur.LaporanSaring:
            laporan = _tugas_saring(id_preset, self.simpanan_potret)
            # Skor tersimpan berubah → dasbor yang sudah jadi tidak lagi sejalan. Dilupakan
            # sesudah skornya tertulis, bukan saat saringan mulai: dasbor yang dibuka selama
            # saringan berjalan belum melihat skor baru.
            self.pekerjaan.lupakan("dasbor")
            return laporan

        self.pekerjaan.mulai(("saring", id_preset), kerja, ulang=True)
        return Jawaban(
            HTTPStatus.SEE_OTHER,
            lokasi=h.tautan("/screener", preset=id_preset, teratas=kueri.get("teratas")),
        )

    def emiten(self, kueri: dict[str, str]) -> Jawaban:
        try:
            daftar = self._daftar_preset()
        except Exception as galat:  # noqa: BLE001
            return self._galat_halaman("Detail emiten", "/emiten", f"{type(galat).__name__}: {galat}")
        kode = (kueri.get("kode") or "").strip().upper()
        id_preset = kueri.get("preset") or (daftar[0][0] if daftar else "")
        borang = h.kartu(
            '<form class=borang method=get action="/emiten">'
            f"<label>Kode{h.isian('kode', kode, petunjuk='mis. BBCA', lebar=8)}</label>"
            f"<label>Preset{h.pilihan('preset', daftar, id_preset)}</label>"
            "<button>Muat</button></form>"
        )
        if not kode:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka("Detail emiten & tesis", borang + h.pesan("Isi kode, lalu tekan Muat."), aktif="/emiten"),
            )
        if not id_preset:
            return self._galat_halaman(
                "Detail emiten & tesis",
                "/emiten",
                "Belum ada preset; skor tidak bisa dihitung tanpa preset (K6). Jalankan `--preset-bawaan`.",
            )
        kunci = ("emiten", kode, id_preset)
        if kueri.get("segarkan"):
            self.pekerjaan.mulai(
                kunci, lambda: _tugas_detail(kode, id_preset, self.simpanan_potret), ulang=True
            )
            return Jawaban(HTTPStatus.SEE_OTHER, lokasi=h.tautan("/emiten", kode=kode, preset=id_preset))
        pekerjaan = self.pekerjaan.mulai(kunci, lambda: _tugas_detail(kode, id_preset, self.simpanan_potret))

        def tampilkan(hasil: HasilDetail) -> str:
            if hasil.pesan:
                return h.pesan(hasil.pesan, "galat")
            segarkan = h.tautan("/emiten", kode=kode, preset=id_preset, segarkan=1)
            risiko_url = h.tautan("/risiko", kode=kode)
            return (
                f'<p><a href="{h.e(segarkan)}">Muat ulang</a> · '
                f'<a href="{h.e(risiko_url)}">Hitung risiko {h.e(kode)}</a></p>'
                + h.pra(hasil.identitas)
                + "<h2>Skor</h2>"
                + h.pesan(hasil.ringkas_skor)
                + (
                    h.tabel(tabel.kepala_faktor_skor(), hasil.faktor_skor)
                    + h.tabel(tabel.kepala_metrik_skor(), hasil.metrik_skor)
                    if hasil.faktor_skor
                    else ""
                )
                + "<h2>Kriteria saringan</h2>"
                + h.tabel(tabel.kepala_kriteria(), hasil.kriteria, kosong="Tidak ada kriteria.")
                + "<h2>Tesis</h2>"
                + h.pra(hasil.tesis or "Belum ada tesis.")
                + "<h2>Posisi aktif</h2>"
                + h.tabel(tabel.kepala_posisi(), hasil.posisi, kosong="Tidak ada posisi aktif.")
                + self._borang_transaksi(kode, hasil, kembali=segarkan)
                + "<h2>Hak right issue</h2>"
                + h.tabel(tabel.kepala_hak_right_issue(), hasil.hak, kosong="Tidak ada hak right issue.")
                + self._borang_right_issue(kode, hasil, kembali=segarkan)
            )

        return self._tunggu_atau(
            pekerjaan, "Detail emiten & tesis", "/emiten", tampilkan, kepala=borang
        )

    def _borang_transaksi(self, kode: str, hasil: HasilDetail, *, kembali: str) -> str:
        mode = (("", "— pilih mode —"),) + tuple((m, m) for m in skema.MODE_SAH)
        aksi = tuple((a, a) for a in posisi.AKSI_SAH)
        rencana = (("", tabel.TANPA_RENCANA),) + hasil.rencana_pilihan
        pos = (("", tabel.TANPA_POSISI),) + hasil.posisi_pilihan
        return (
            f"<h2>Catat transaksi {h.e(kode)}</h2>"
            + h.kartu(
                h.borang_tulis(
                    "transaksi",
                    self.csrf,
                    f"<label>Aksi{h.pilihan('aksi', aksi, 'beli')}</label>"
                    f"<label>Lembar{h.isian('lembar', '', petunjuk='wajib, kelipatan lot', lebar=10)}</label>"
                    f"<label>Harga{h.isian('harga', '', petunjuk='wajib, sesuai tick', lebar=10)}</label>"
                    f"<label>Mode{h.pilihan('mode', mode, '')}</label>"
                    f"<label>Tanggal{h.isian('tanggal', '', petunjuk='YYYY-MM-DD · kosong = hari ini', lebar=16)}</label>"
                    f"<label>Rencana{h.pilihan('id_rencana', rencana, '')}</label>"
                    f"<label>Posisi{h.pilihan('id_posisi', pos, '')}</label>"
                    f"<label>Biaya{h.isian('biaya', '', petunjuk='kosong = dari tarif broker', lebar=14)}</label>"
                    f"<label>Catatan{h.isian('catatan', '', petunjuk='kosong = tanpa catatan', lebar=24)}</label>",
                    "Catat transaksi",
                    tersembunyi={"kode": kode, "kembali": kembali},
                )
                + "<p class=redup>Sama dengan <code>--catat-transaksi</code>. Pelanggaran PRD 9.8 "
                "dicatat di barisnya, bukan ditolak.</p>"
            )
        )

    def _borang_right_issue(self, kode: str, hasil: HasilDetail, *, kembali: str) -> str:
        if not hasil.hak_pilihan:
            return ""
        hak = (("", "— pilih baris right issue —"),) + hasil.hak_pilihan
        keputusan = (("", "— pilih keputusan —"),) + tuple(
            (k, k) for k in posisi.KEPUTUSAN_RIGHT_ISSUE_SAH
        )
        transaksi = (("", tabel.TANPA_TRANSAKSI),) + hasil.transaksi_pilihan
        return h.kartu(
            h.borang_tulis(
                "right-issue",
                self.csrf,
                f"<label>Right issue{h.pilihan('hak', hak, '')}</label>"
                f"<label>Keputusan{h.pilihan('keputusan', keputusan, '')}</label>"
                f"<label>Transaksi tebus{h.pilihan('id_transaksi', transaksi, '')}</label>"
                f"<label>Lembar hak{h.isian('lembar', '', petunjuk='hanya jual_hmetd', lebar=10)}</label>"
                f"<label>Harga jual hak{h.isian('harga', '', petunjuk='hanya jual_hmetd', lebar=10)}</label>"
                f"<label>Biaya{h.isian('biaya', '', petunjuk='hanya jual_hmetd', lebar=10)}</label>"
                f"<label>Catatan{h.isian('catatan', '', lebar=24)}</label>",
                "Catat keputusan",
                tersembunyi={"kode": kode, "kembali": kembali},
            )
            + h.pesan(tulis.CATATAN_TEBUS_MENUNJUK_TRANSAKSI)
        )

    def risiko(self, kueri: dict[str, str]) -> Jawaban:
        judul = "Kalkulator risiko"
        kode = (kueri.get("kode") or "").strip().upper()
        jenis_stop = kueri.get("jenis_stop") or risiko.JENIS_STOP_SAH[0]
        pakai_patuh = bool(kueri.get("patuh"))
        borang = h.kartu(
            '<form class=borang method=get action="/risiko">'
            f"<label>Kode{h.isian('kode', kode, petunjuk='mis. TLKM', lebar=8)}</label>"
            f"<label>Harga masuk{h.isian('harga', kueri.get('harga'), petunjuk='kosong = penutupan terakhir')}</label>"
            f"<label>Stop{h.isian('stop', kueri.get('stop'), petunjuk='kosong = 2 × ATR14')}</label>"
            f"<label>Jenis stop{h.pilihan('jenis_stop', tuple((j, j) for j in risiko.JENIS_STOP_SAH), jenis_stop)}</label>"
            f"<label>Ekuitas (penimpa){h.isian('ekuitas', kueri.get('ekuitas'), petunjuk='kosong = tercatat')}</label>"
            f"<label>Kas (penimpa){h.isian('kas', kueri.get('kas'), petunjuk='kosong = tidak dinilai')}</label>"
            f'<label class=centang><input type=checkbox name=patuh value=1{" checked" if pakai_patuh else ""}>'
            "Pakai ukuran patuh (PRD 9.7)</label>"
            f"{_penanda_kirim()}<button>Hitung</button></form>"
            "<p class=redup>Angkanya sama persis dengan <code>--hitung-risiko</code>. Menyimpan "
            "rencana menyimpan <strong>angka yang tampil</strong>; kalau isian diubah, tekan "
            "Hitung lagi lebih dulu.</p>"
        )
        if not kode:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(judul, borang + h.pesan("Isi kode, lalu tekan Hitung."), aktif="/risiko"),
            )
        try:
            harga = int_atau_none(kueri.get("harga"), "Harga masuk")
            stop = int_atau_none(kueri.get("stop"), "Stop")
            ekuitas = int_atau_none(kueri.get("ekuitas"), "Ekuitas")
            kas = int_atau_none(kueri.get("kas"), "Kas")
        except GalatIsian as galat:
            return Jawaban(
                HTTPStatus.OK, h.kerangka(judul, borang + h.galat(str(galat), None), aktif="/risiko")
            )
        if jenis_stop not in risiko.JENIS_STOP_SAH:
            return Jawaban(
                HTTPStatus.OK,
                h.kerangka(judul, borang + h.galat(f"Jenis stop tidak sah: {jenis_stop!r}", None), aktif="/risiko"),
            )
        kunci = ("risiko", kode, harga, stop, jenis_stop, ekuitas, kas, pakai_patuh, kueri.get("kirim"))
        pekerjaan = self.pekerjaan.mulai(
            kunci, lambda: _tugas_risiko(kode, harga, stop, jenis_stop, ekuitas, kas, pakai_patuh)
        )
        kembali = h.tautan("/risiko", kode=kode)

        def tampilkan(hasil: HasilRisiko) -> str:
            token = secrets.token_urlsafe(16)
            with self._kunci:
                self._risiko[token] = hasil
                while len(self._risiko) > 32:
                    del self._risiko[next(iter(self._risiko))]
            rencana = (("", tabel.RENCANA_BARU),) + hasil.rencana_pilihan
            return h.pra(hasil.teks) + "<h2>Simpan rencana (PRD 9.7)</h2>" + h.kartu(
                h.borang_tulis(
                    "rencana",
                    self.csrf,
                    f"<label>Rencana{h.pilihan('id_rencana', rencana, '')}</label>",
                    "Simpan rencana",
                    tersembunyi={"hasil": token, "kembali": kembali},
                )
            )

        return self._tunggu_atau(pekerjaan, judul, "/risiko", tampilkan, kepala=borang)

    def jurnal(self, kueri: dict[str, str]) -> Jawaban:
        judul = "Jurnal & kepatuhan"
        bulan = (kueri.get("bulan") or "").strip() or None
        mode = kueri.get("mode") or None
        if mode not in (None, "nyata", "simulasi"):
            return self._galat_halaman(judul, "/jurnal", f"Mode tidak sah: {mode!r}")
        borang = h.kartu(
            '<form class=borang method=get action="/jurnal">'
            f"<label>Bulan{h.isian('bulan', bulan, petunjuk='YYYY-MM · kosong = semua', lebar=10)}</label>"
            f"<label>Mode{h.pilihan('mode', (('', 'seluruh mode'), ('nyata', 'nyata'), ('simulasi', 'simulasi')), mode or '')}</label>"
            f"{_penanda_kirim()}<button>Tampilkan</button></form>"
        )
        kunci = ("jurnal", bulan, mode, kueri.get("kirim"))
        pekerjaan = self.pekerjaan.mulai(kunci, lambda: _tugas_jurnal(bulan, mode))

        def tampilkan(rekap: jurnal.Rekap) -> str:
            return (
                "<h2>Keputusan</h2>"
                + h.tabel(tabel.kepala_jurnal(), tabel.isi_jurnal(rekap.keputusan), kosong="Belum ada keputusan.")
                + self._borang_jurnal(rekap)
                + "<h2>Pelanggaran</h2>"
                + h.tabel(tabel.kepala_pelanggaran(), tabel.isi_pelanggaran(rekap.pelanggaran), kosong="Tidak ada pelanggaran.")
                + "<h2>Tidak dapat dinilai</h2>"
                + h.tabel(tabel.kepala_tak_dinilai(), tabel.isi_tak_dinilai(rekap.tak_dinilai), kosong="Tidak ada.")
                + "<h2>Rekap (sama dengan <code>--rekap-kepatuhan</code>)</h2>"
                + h.pra(rekap.ringkas())
            )

        return self._tunggu_atau(pekerjaan, judul, "/jurnal", tampilkan, kepala=borang)


    def _borang_jurnal(self, rekap: jurnal.Rekap) -> str:
        if not rekap.keputusan:
            return ""
        pilihan = (("", "— pilih keputusan —"),) + tuple(
            (str(b.transaksi.id_transaksi), tabel.label_transaksi(b.transaksi)) for b in rekap.keputusan
        )
        return "<h2>Catatan jurnal</h2>" + h.kartu(
            h.borang_tulis(
                "jurnal",
                self.csrf,
                f"<label>Keputusan{h.pilihan('id_transaksi', pilihan, '')}</label>"
                f"<label>Alasan{h.isian('alasan', '', lebar=24)}</label>"
                f"<label>Pelajaran{h.isian('pelajaran', '', lebar=24)}</label>"
                f"<label>Tinjau ulang{h.isian('tanggal_tinjau', '', petunjuk='YYYY-MM-DD', lebar=12)}</label>"
                + h.centang("selesai", "Tandai selesai")
                + f"<label>Tanggal selesai{h.isian('tanggal_selesai', '', petunjuk='YYYY-MM-DD', lebar=12)}</label>",
                "Tulis catatan",
                tersembunyi={"kembali": "/jurnal"},
            )
            + "<p class=redup>Menambah revisi, tidak menimpa (PRD 9.8): bidang kosong "
            "mempertahankan isi catatan sebelumnya.</p>"
        )


# ---------------------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------------------


def _baris_gagal(pesan: str, batas: int = 240) -> str:
    """Kalimat sebab dari pesan impor yang panjang: baris "GAGAL: …" bila ada, selain itu baris pertama."""
    baris = [satu.strip() for satu in pesan.splitlines() if satu.strip()]
    pilihan = next((satu for satu in baris if satu.startswith("GAGAL")), baris[0] if baris else "(tanpa pesan)")
    return pilihan if len(pilihan) <= batas else pilihan[: batas - 1] + "…"


def _tanggal_teks(iso: str | None) -> str:
    return tampilan.tanggal(date.fromisoformat(iso)) if iso else "—"


def _kueri(teks: str) -> dict[str, str]:
    return {k: v[-1] for k, v in parse_qs(teks, keep_blank_values=True).items()}


def _multipart(jenis: str, badan: bytes) -> tuple[dict[str, str], Unggahan]:
    """Urai `multipart/form-data` dengan pustaka standar (modul `cgi` sudah tidak ada)."""
    pesan = BytesParser(policy=HTTP).parsebytes(
        b"Content-Type: " + jenis.encode("latin-1") + b"\r\n\r\n" + badan
    )
    isian: dict[str, str] = {}
    unggahan: Unggahan = {}
    if not pesan.is_multipart():
        return isian, unggahan
    for bagian in pesan.iter_parts():
        nama = bagian.get_param("name", header="content-disposition")
        if not nama:
            continue
        isi = bagian.get_payload(decode=True) or b""
        nama_berkas = bagian.get_filename()
        if nama_berkas is not None:
            if nama_berkas or isi:
                unggahan.setdefault(str(nama), []).append((nama_berkas, isi))
        else:
            isian[str(nama)] = isi.decode("utf-8")
    return isian, unggahan


def buat_penangan(aplikasi: Aplikasi, port_diizinkan: Callable[[], int]) -> type[BaseHTTPRequestHandler]:
    class Penangan(BaseHTTPRequestHandler):
        server_version = "MejaSaham"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            # Log akses tidak berguna bagi pengguna tunggal; galat tetap tercetak lewat pekerjaan.
            return None

        def _host_sah(self) -> bool:
            port = port_diizinkan()
            host = (self.headers.get("Host") or "").lower()
            return host in {f"127.0.0.1:{port}", f"localhost:{port}"}

        def _asal_sah(self) -> bool:
            if (self.headers.get("Sec-Fetch-Site") or "same-origin") not in {"same-origin", "none"}:
                return False
            asal = self.headers.get("Origin")
            return asal is None or asal == f"http://{self.headers.get('Host')}"

        def _kirim(self, jawaban: Jawaban) -> None:
            data = jawaban.isi.encode("utf-8")
            self.send_response(jawaban.status)
            if jawaban.lokasi:
                self.send_header("Location", jawaban.lokasi)
            self.send_header("Content-Type", jawaban.jenis)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            # `no-referrer` membuat peramban mengirim `Origin: null` pada POST, sehingga
            # formulir sendiri tertolak sebagai lintas situs; `same-origin` tetap tidak membocorkan
            # alamat ke situs lain.
            self.send_header("Referrer-Policy", "same-origin")
            try:
                self.end_headers()
                self.wfile.write(data)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                # Peramban sudah menutup koneksi (pindah halaman, muat ulang otomatis) sebelum
                # jawaban terkirim. Permintaannya sudah diproses; yang hilang hanya halaman
                # balasan, jadi cukup satu baris catatan, bukan jejak galat server.
                self.close_connection = True
                print(
                    f"Catatan: peramban menutup koneksi sebelum jawaban {self.command} "
                    f"{urlsplit(self.path).path} terkirim.",
                    file=sys.stderr,
                )

        def _layani(self, metode: str) -> None:
            if not self._host_sah():
                self._kirim(Jawaban(HTTPStatus.BAD_REQUEST, "Host tidak diizinkan."))
                return
            bagian = urlsplit(self.path)
            kueri = _kueri(bagian.query)
            unggahan: Unggahan = {}
            if metode == "POST":
                # Badan dibaca lebih dulu, bahkan bila permintaannya akan ditolak: menutup koneksi
                # dengan badan yang belum dibaca membuat peramban melihat koneksi terputus, bukan
                # pesan penolakannya.
                panjang = int(self.headers.get("Content-Length") or 0)
                if panjang > BATAS_BADAN:
                    # Badan sebesar itu sengaja tidak dibaca; koneksinya ditutup sesudah jawaban.
                    self.close_connection = True
                    self._kirim(
                        Jawaban(
                            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                            h.kerangka(
                                "Terlalu besar",
                                h.pesan(
                                    f"Kiriman {tampilan.angka(panjang, 0)} bait melebihi batas "
                                    f"{tampilan.angka(BATAS_BADAN, 0)} bait; tidak ada yang disimpan.",
                                    "galat",
                                ),
                                aktif="",
                            ),
                        )
                    )
                    return
                badan = self.rfile.read(panjang)
                if not self._asal_sah():
                    self._kirim(Jawaban(HTTPStatus.FORBIDDEN, "Permintaan lintas situs ditolak."))
                    return
                jenis = self.headers.get("Content-Type") or ""
                if jenis.lower().startswith("multipart/form-data"):
                    isian, unggahan = _multipart(jenis, badan)
                    kueri.update(isian)
                else:
                    kueri.update(_kueri(badan.decode("utf-8")))
            try:
                jawaban = aplikasi.tangani(metode, bagian.path, kueri, unggahan)
            except Exception as galat:  # noqa: BLE001 — dilaporkan di halaman + stderr, bukan ditelan
                jejak = traceback.format_exc()
                print(jejak, file=sys.stderr)
                jawaban = Jawaban(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    h.kerangka("Galat", h.galat(f"{type(galat).__name__}: {galat}", jejak), aktif=""),
                )
            self._kirim(jawaban)

        def do_GET(self) -> None:  # noqa: N802
            self._layani("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._layani("POST")

    return Penangan


def buat_server(host: str = HOST, port: int = PORT_BAWAAN) -> ThreadingHTTPServer:
    """Server siap `serve_forever()`; `port=0` memilih port bebas (dipakai uji)."""
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Dasbor hanya boleh mendengar di 127.0.0.1 (K91).")
    aplikasi = Aplikasi()
    server: ThreadingHTTPServer | None = None
    penangan = buat_penangan(aplikasi, lambda: server.server_address[1])  # type: ignore[union-attr]
    server = ThreadingHTTPServer((host, port), penangan)
    server.daemon_threads = True
    server.aplikasi = aplikasi  # type: ignore[attr-defined]
    return server
