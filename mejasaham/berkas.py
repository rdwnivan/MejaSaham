"""Pembaca berkas impor — jalur cadangan tanpa jaringan (P2, PRD 9.3, Q8).

Jalur ini ada karena beberapa data **tidak** tersedia dari sumber tidak resmi (PRD 7.1):
kalender bursa, notasi khusus/suspensi, aksi korporasi resmi, imbal hasil SUN, klasifikasi
sektor, rasio bank, dan fundamental. Untuk semuanya, berkas yang dirawat manusialah sumbernya —
dan itu berarti berkas yang salah harus **berhenti dengan pesan**, bukan dimuat setengah jalan.

Aturan yang ditegakkan berkas ini:

1. **Salah ketik ditolak, bukan diabaikan.** Kolom tak dikenal, kolom wajib yang hilang, dan
   nilai yang tidak dikenali semuanya menolak berkas. Alasannya sama dengan di
   `konfigurasi.py`: berkas yang salah baca lebih berbahaya daripada berkas yang menolak dimuat.
2. **Gagal berisik dan sekaligus.** Seluruh baris yang salah dilaporkan bersama (berkas + nomor
   baris + kolom), bukan satu per satu, supaya memperbaikinya tidak menjadi permainan tebak-tebakan.
   Yang penting: **tidak ada satu pun** baris yang ditulis bila ada yang salah.
3. **Berkas yang tidak ada dilewati dengan catatan; berkas yang ada tapi salah menolak semuanya.**
   Impor bertahap (mis. baru punya kalender bursa) tetap mungkin, tetapi berkas yang sudah
   disiapkan tidak boleh diabaikan diam-diam.
4. **Tidak ada angka tebakan.** Nilai kosong menjadi `None` (bukan 0) dan dilaporkan sebagai
   lubang oleh `mutu.py`.

Bentuk berkas: CSV ber-header. Pemisah `;` atau `,` dideteksi otomatis dan BOM UTF-8 dari
Excel/Notepad dibuang. Nama berkas menentukan jenis isinya (lihat `BERKAS_IMPOR_DIKENAL`);
template kosongnya ada di `mejasaham/defaults/`.
"""

from __future__ import annotations

import csv
import re
from urllib.parse import urlparse
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from mejasaham.ingesti import (
    ASAL_TGL_PUBLIKASI_BAWAAN,
    ASAL_TGL_PUBLIKASI_SAH,
    BERKAS_IMPOR_DIKENAL,
    FAKTOR_SATUAN_UANG,
    JENIS_EMITEN,
    JENIS_LAPORAN_SAH,
    NAMA_BERKAS_EMITEN,
    PENANDA_PENYESUAIAN_SAH,
    PREFIKS_SUMBER_IMPOR,
    AksiKorporasi,
    CatatanAksiMutu,
    SambunganHarga,
    Emiten,
    Fundamental,
    GalatIngesti,
    HariBursa,
    HargaHarian,
    ImbalHasilSUN,
    KumpulanData,
    NotasiKhusus,
    PenutupanIndeks,
    RasioBank,
    _desimal,
    _ke_basis_poin,
    _ke_lembar,
    _ke_rupiah,
    _ke_tanggal,
    _teks_mentah,
)
from mejasaham import lokasi

#: Berkas bawaan di `mejasaham/defaults/` yang disalin ke folder konfigurasi saat belum ada.
#:
#: Yang disalin hanyalah **bentuk** berkasnya (header + penjelasan + baris contoh bertanda
#: `<<CONTOH>>` yang tidak ikut terimpor). Tidak ada satu pun kode emiten, harga, atau angka
#: bursa yang ikut tersalin — itu akan menjadi data tebakan (aturan keras 1).
#: Nama berkas impor fundamental & rasio bank. Dipakai juga oleh `ingesti.BERKAS_IMPOR_DIKENAL`,
#: jadi namanya ditulis sekali saja di sini.
NAMA_FUNDAMENTAL = "fundamental.csv"
NAMA_RASIO_BANK = "rasio-bank.csv"

#: Nama berkas kalender bursa. Dipakai `kalender.py` (pengambil dari pengumuman KSEI), jadi
#: namanya ditulis sekali saja di sini — sama alasannya dengan dua nama di atas.
NAMA_BERKAS_KALENDER = "kalender-bursa.csv"

#: Nama berkas imbal hasil SUN. Dipakai `sun.py` (pengambil dari halaman HPW PHEI), jadi namanya
#: ditulis sekali saja di sini — alasannya sama dengan nama-nama di atas.
NAMA_BERKAS_SUN = "imbal-hasil-sun.csv"

BAWAAN_DISALIN: Mapping[str, str] = {
    NAMA_BERKAS_EMITEN: "emiten.contoh.csv",
    "harga-harian.csv": "harga-harian.contoh.csv",
    "harga-indeks.csv": "harga-indeks.contoh.csv",
    "aksi-korporasi.csv": "aksi-korporasi.contoh.csv",
    "catatan-aksi-mutu.csv": "catatan-aksi-mutu.contoh.csv",
    NAMA_BERKAS_KALENDER: "kalender-bursa.contoh.csv",
    "notasi-khusus.csv": "notasi-khusus.contoh.csv",
    NAMA_BERKAS_SUN: "imbal-hasil-sun.contoh.csv",
    NAMA_FUNDAMENTAL: "fundamental.contoh.csv",
    NAMA_RASIO_BANK: "rasio-bank.contoh.csv",
}

#: Titik awal yang bisa langsung jalan, masih ditandai "belum diverifikasi" di kolom `sumber`.
#: Hanya dipakai bila pengguna memintanya lewat `--emiten-awal`; `--refresh` tidak pernah
#: memakainya diam-diam, karena semesta saham adalah keputusan pengguna.
BAWAAN_AWAL_EMITEN = "emiten-awal.contoh.csv"

FOLDER_BAWAAN = Path(__file__).resolve().parent / "defaults"


def _tulis_teks(jalur: Path, isi: str) -> None:
    """Tulis berkas teks UTF-8 **tanpa BOM** dan dengan akhir baris `\\n`.

    Sengaja tidak memakai `write_text(..., encoding="utf-8-sig")`: BOM berguna di berkas yang
    dibuka Excel Indonesia (U11), tetapi berkas **bawaan** harus bisa dibaca alat apa pun,
    termasuk `tomllib`, `csv`, dan `git diff`. Pemisah kolom `;` sudah cukup membuat Excel
    membacanya benar. Pembaca di modul ini menerima BOM, jadi berkas yang pengguna simpan
    ulang lewat Excel tetap terbaca.
    """
    with jalur.open("w", encoding="utf-8", newline="\n") as berkas_tulis:
        berkas_tulis.write(isi)


def siapkan_berkas_bawaan(folder: Path) -> tuple[str, ...]:
    """Salin template berkas impor ke `folder` untuk yang belum ada.

    Sama alasannya dengan penyalinan template parameter bursa (AC-12): setelah isi folder data
    dihapus, aplikasi harus bisa kembali ke bentuk bawaannya. Berkas yang **sudah ada tidak
    pernah ditimpa** — berkas itu berisi pekerjaan pengguna.

    Yang disalin hanya bentuk kosongnya. `emiten.csv` hasil salinan tetap tanpa satu pun
    emiten, sehingga `--refresh` berhenti dengan pesan yang menjelaskan apa yang harus diisi —
    bukan diam-diam mengambil semesta yang salah.
    """
    lokasi.pastikan_folder(folder)
    disalin: list[str] = []
    for nama, contoh in BAWAAN_DISALIN.items():
        tujuan = folder / nama
        if tujuan.exists():
            continue
        asal = FOLDER_BAWAAN / contoh
        if not asal.is_file():
            raise GalatIngesti(
                f"template bawaan '{asal}' tidak ada. Pemasangan aplikasi tidak lengkap; "
                "pasang ulang supaya folder defaults/ ikut tersalin."
            )
        try:
            # encoding='utf-8-sig' saat MEMBACA: berkas bawaan yang pernah disunting lewat
            # editor Windows bisa membawa BOM, dan BOM itu tidak boleh ikut tersalin.
            _tulis_teks(tujuan, asal.read_text(encoding="utf-8-sig"))
        except OSError as galat:
            raise GalatIngesti(f"gagal menyalin template '{asal}' ke '{tujuan}': {galat}") from galat
        disalin.append(nama)
    return tuple(disalin)


def ambil_daftar_awal(folder: Path, *, timpa: bool = False) -> Path:
    """Salin daftar emiten awal (bootstrap) ke `folder/emiten.csv`.

    Daftar itu **bukan** daftar resmi dan hanya berisi kode besar yang umum dikenal, dengan
    seluruh kolom data lain dikosongkan. Dipakai untuk mencoba alur ingesti sebelum daftar IDX
    yang sebenarnya disiapkan; kolom `sumber` tiap barisnya menyatakan itu apa adanya.
    """
    tujuan = folder / NAMA_BERKAS_EMITEN
    if tujuan.exists() and not timpa:
        raise GalatIngesti(
            f"'{tujuan}' sudah ada. Berkas itu berisi daftar emiten Anda sendiri; "
            "pakai --timpa-emiten bila memang ingin menggantinya dengan daftar awal."
        )
    asal = FOLDER_BAWAAN / BAWAAN_AWAL_EMITEN
    if not asal.is_file():
        raise GalatIngesti(f"daftar awal bawaan '{asal}' tidak ada")
    lokasi.pastikan_folder(folder)
    try:
        _tulis_teks(tujuan, asal.read_text(encoding="utf-8-sig"))
    except OSError as galat:
        raise GalatIngesti(f"gagal menulis '{tujuan}': {galat}") from galat
    return tujuan

#: Jenis notasi khusus yang sah (`notasi_khusus.jenis` di `skema.py`).
JENIS_NOTASI: Mapping[str, str] = {
    "suspensi": "suspensi",
    "suspend": "suspensi",
    "uma": "uma",
    "papan_pemantauan": "papan_pemantauan",
    "papan pemantauan": "papan_pemantauan",
    "papan_pemantauan_khusus": "papan_pemantauan",
    "notasi_lainnya": "notasi_lainnya",
    "notasi lainnya": "notasi_lainnya",
    "lainnya": "notasi_lainnya",
    "notasi_khusus": "notasi_lainnya",
}

# Penanda provenance yang dibawa kolom keterangan sampai saringan bila sumber suspensi tidak lengkap.
PENANDA_NOTASI_TIDAK_LENGKAP = "IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAKAN"

#: Jenis aksi korporasi yang sah (`aksi_korporasi.jenis` di `skema.py`).
JENIS_AKSI: Mapping[str, str] = {
    "split": "split",
    "stock_split": "split",
    "pemecahan": "split",
    "reverse_split": "reverse_split",
    "reverse split": "reverse_split",
    "gabung": "reverse_split",
    "right_issue": "right_issue",
    "right issue": "right_issue",
    "hmetd": "right_issue",
    "dividen": "dividen",
    "dividend": "dividen",
}

#: Nilai `hari_bursa` yang diterima (ditulis manusia, jadi "ya/tidak" wajar dipakai).
HARI_BURSA_BENAR = {"1", "ya", "yes", "y", "true", "benar", "bursa"}
HARI_BURSA_SALAH = {"0", "tidak", "no", "n", "false", "salah", "libur", "non-bursa"}


@dataclass(frozen=True)
class Kolom:
    """Satu kolom berkas: nama resmi, wajib atau tidak, dan apakah boleh kosong."""

    nama: str
    wajib: bool = False
    #: True bila kolom boleh kosong (menjadi `None`). Kolom wajib yang kosong tetap ditolak,
    #: karena baris tanpa kolom kuncinya tidak bisa ditempatkan di basis data.
    boleh_kosong: bool = True


@dataclass(frozen=True)
class Spesifikasi:
    """Bentuk satu berkas impor."""

    jenis: str
    kolom: tuple[Kolom, ...]

    @property
    def nama_kolom(self) -> tuple[str, ...]:
        return tuple(satu.nama for satu in self.kolom)

    @property
    def wajib(self) -> tuple[str, ...]:
        return tuple(satu.nama for satu in self.kolom if satu.wajib)


#: Bentuk tiap berkas. Urutan kolom di sini = urutan yang diharapkan di template.
SPESIFIKASI: Mapping[str, Spesifikasi] = {
    "emiten": Spesifikasi(
        jenis="emiten",
        kolom=(
            Kolom("kode", wajib=True, boleh_kosong=False),
            Kolom("nama", wajib=True, boleh_kosong=False),
            Kolom("sektor_idx_ic"),
            # Sektor menurut sumber data (K25) — kolom **berbeda** dari `sektor_idx_ic`, dan
            # namanya sengaja berbeda supaya tidak ada yang tertukar: yang satu IDX-IC, yang lain
            # taksonomi sumber EOD.
            Kolom("sektor_sumber"),
            Kolom("jenis"),
            Kolom("papan"),
            Kolom("status_notasi"),
            # Tanggal pencatatan (listing date) bila sumbernya menyatakannya. Kosong berarti
            # "belum ada datanya" (None), bukan tanggal tebakan — sama seperti kolom lain.
            Kolom("tanggal_notasi"),
            Kolom("jumlah_saham"),
            Kolom("free_float_persen"),
            Kolom("sumber", wajib=True, boleh_kosong=False),
            Kolom("dicatat_pada", wajib=True, boleh_kosong=False),
        ),
    ),
    "harga_harian": Spesifikasi(
        jenis="harga_harian",
        kolom=(
            Kolom("kode", wajib=True, boleh_kosong=False),
            Kolom("tanggal", wajib=True, boleh_kosong=False),
            Kolom("open", wajib=True),
            Kolom("high", wajib=True),
            Kolom("low", wajib=True),
            Kolom("close", wajib=True),
            Kolom("volume", wajib=True),
            # Kolom opsional: bila diisi, nilainya dipakai apa adanya dan `asal_nilai`
            # menjadi 'impor' (U6). Bila kosong, ingesti menghitung close x volume.
            Kolom("nilai"),
            # K8/C10. Wajib dinyatakan untuk berkas **impor**: harga dari berkas bisa saja
            # sudah disesuaikan split (mis. hasil ekspor sumber lain) atau belum sama sekali,
            # dan menebaknya berarti salah satu dari keduanya dipakai tanpa diketahui.
            # Nilai kosong tetap diterima sebagai "belum dinyatakan" — dan itu dibedakan.
            Kolom("penyesuaian_sumber"),
            # Sumber baris ini, opsional. Diisi bila berkas memuat harga dari sumber lain
            # (bahan cek sumber kedua, PRD 7.3). Kosong = ikut label kumpulan, seperti sebelumnya.
            Kolom("sumber"),
        ),
    ),
    "harga_indeks": Spesifikasi(
        jenis="harga_indeks",
        kolom=(
            Kolom("indeks", wajib=True, boleh_kosong=False),
            Kolom("tanggal", wajib=True, boleh_kosong=False),
            Kolom("close", wajib=True),
        ),
    ),
    "aksi_korporasi": Spesifikasi(
        jenis="aksi_korporasi",
        kolom=(
            Kolom("kode", wajib=True, boleh_kosong=False),
            Kolom("tanggal", wajib=True, boleh_kosong=False),
            Kolom("jenis", wajib=True, boleh_kosong=False),
            Kolom("rasio_lama"),
            Kolom("rasio_baru"),
            Kolom("harga_tebus"),
            Kolom("dividen_per_saham"),
            # Batas waktu pelaksanaan right issue (PRD 9.11). Opsional: sumber data EOD tidak
            # menerbitkannya, dan tenggat yang tidak dinyatakan lebih baik kosong daripada
            # dikarang. Kosong = "belum dinyatakan sumbernya", bukan "tidak ada tenggat".
            Kolom("tenggat"),
            Kolom("keterangan"),
        ),
    ),
    "catatan_aksi_mutu": Spesifikasi(
        jenis="catatan_aksi_mutu",
        kolom=(
            Kolom("kode", wajib=True, boleh_kosong=False),
            Kolom("tanggal_efektif", wajib=True, boleh_kosong=False),
            Kolom("instrumen_aksi", wajib=True, boleh_kosong=False),
            Kolom("ringkasan_bukti", wajib=True, boleh_kosong=False),
            Kolom("sumber_url", wajib=True, boleh_kosong=False),
            Kolom("sumber", wajib=True, boleh_kosong=False),
        ),
    ),
    # K97: "sejak `berlaku_sejak`, harga dibaca dari label `sumber_resmi`". `aktif` = ya/tidak;
    # "tidak" mencabut tanggal itu. Yang berlaku adalah tanggal aktif terbesar.
    "sambungan_harga": Spesifikasi(
        jenis="sambungan_harga",
        kolom=(
            Kolom("berlaku_sejak", wajib=True, boleh_kosong=False),
            Kolom("sumber_resmi", wajib=True, boleh_kosong=False),
            Kolom("aktif", wajib=True, boleh_kosong=False),
            Kolom("keterangan"),
            Kolom("sumber", wajib=True, boleh_kosong=False),
        ),
    ),
    "kalender_bursa": Spesifikasi(
        jenis="kalender_bursa",
        kolom=(
            Kolom("tanggal", wajib=True, boleh_kosong=False),
            Kolom("hari_bursa", wajib=True, boleh_kosong=False),
            Kolom("keterangan"),
            # Sumber baris ini, opsional. Diisi oleh `--ambil-kalender` dengan nomor pengumuman
            # KSEI/IDX-nya (baris libur) atau penanda turunan (hari kerja, akhir pekan), supaya
            # asal setiap tanggal bisa ditelusuri. Kosong = ikut label kumpulan, seperti semula.
            Kolom("sumber"),
        ),
    ),
    "notasi_khusus": Spesifikasi(
        jenis="notasi_khusus",
        kolom=(
            Kolom("kode", wajib=True, boleh_kosong=False),
            Kolom("jenis", wajib=True, boleh_kosong=False),
            Kolom("tanggal_mulai", wajib=True, boleh_kosong=False),
            Kolom("tanggal_selesai"),
            Kolom("keterangan"),
        ),
    ),
    "imbal_hasil_sun": Spesifikasi(
        jenis="imbal_hasil_sun",
        kolom=(
            Kolom("tanggal", wajib=True, boleh_kosong=False),
            Kolom("tenor_tahun", wajib=True, boleh_kosong=False),
            Kolom("imbal_hasil_persen", wajib=True, boleh_kosong=False),
            Kolom("sumber"),
        ),
    ),
    # Fundamental (PRD 8.1/12). `mata_uang` dan `satuan_uang` **wajib**: keduanya tidak bisa
    # disimpulkan dari angkanya, dan salah menebaknya membuat seluruh rasio salah tanpa
    # terlihat. `tgl_publikasi` wajib karena fundamental baru dipakai sejak tanggal itu (AC-15).
    "fundamental": Spesifikasi(
        jenis="fundamental",
        kolom=(
            Kolom("kode", wajib=True, boleh_kosong=False),
            Kolom("periode", wajib=True, boleh_kosong=False),
            Kolom("jenis_laporan", wajib=True, boleh_kosong=False),
            Kolom("tgl_publikasi", wajib=True, boleh_kosong=False),
            # Kolom ini **boleh tidak ada** di berkas: berkas lama dan berkas yang diisi tangan
            # memang memuat tanggal publikasi yang sebenarnya, dan itu artinya `sumber`.
            # Mengisinya `tanggal_pengambilan` hanya sah untuk jalur otomatis (K18).
            Kolom("asal_tgl_publikasi"),
            Kolom("mata_uang", wajib=True, boleh_kosong=False),
            Kolom("satuan_uang", wajib=True, boleh_kosong=False),
            Kolom("pendapatan"),
            Kolom("laba_induk"),
            Kolom("ekuitas_induk"),
            Kolom("ebit"),
            Kolom("beban_bunga"),
            Kolom("da"),
            Kolom("utang_bunga"),
            Kolom("kas"),
            Kolom("cfo"),
            Kolom("jumlah_saham"),
            Kolom("dps"),
            Kolom("sumber", wajib=True, boleh_kosong=False),
        ),
    ),
    "rasio_bank": Spesifikasi(
        jenis="rasio_bank",
        kolom=(
            Kolom("kode", wajib=True, boleh_kosong=False),
            Kolom("periode", wajib=True, boleh_kosong=False),
            Kolom("tgl_publikasi", wajib=True, boleh_kosong=False),
            Kolom("npl_kotor_persen"),
            Kolom("car_persen"),
            Kolom("bopo_persen"),
            Kolom("nim_persen"),
            Kolom("keterangan"),
            Kolom("sumber", wajib=True, boleh_kosong=False),
        ),
    ),
}


def _normalkan(nama: str) -> str:
    """Nama kolom dibandingkan tanpa peduli huruf besar/kecil, spasi, dan garis bawah."""
    return re.sub(r"[\s_\-]+", "_", nama.strip().lower()).strip("_")


def _baca_baris(jalur: Path) -> tuple[tuple[str, ...], list[tuple[int, dict[str, str]]]]:
    """Baca CSV ber-header: kembalikan (header ternormalisasi, baris beserta nomor barisnya).

    Pemisah dideteksi dari **baris kepala**, yaitu baris pertama yang bukan penjelasan dan bukan
    baris contoh. Sebelumnya ia diambil dari baris fisik pertama, dan itu membuat berkas yang
    diawali komentar ditolak dengan pesan yang menyesatkan ("kolom tidak dikenal ['kode;nama;…']")
    — padahal isinya benar dan yang salah hanya letak baris kepalanya. Baris penjelasan `#` memang
    boleh ada, jadi baris kepalanya juga harus dicari dengan aturan yang sama.

    Pemisah `;` dipakai Excel Indonesia (U11), `,` dipakai hampir semua alat lain. BOM UTF-8
    dibuang supaya berkas hasil Excel tetap terbaca. Dua hal sengaja diabaikan, supaya template
    bawaan bisa dibaca apa adanya tanpa diedit: baris berawalan `#` (penjelasan) dan baris yang
    dimulai `<<CONTOH>>` (baris contoh yang tidak boleh ikut terimpor).
    """
    try:
        teks = jalur.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as galat:
        raise GalatIngesti(
            f"{jalur.name}: berkas bukan teks UTF-8 ({galat}). Simpan ulang sebagai CSV UTF-8."
        ) from galat
    except OSError as galat:
        raise GalatIngesti(f"{jalur.name}: tidak bisa dibaca ({galat})") from galat

    if not teks.strip():
        raise GalatIngesti(f"{jalur.name}: berkas kosong. Isi baris header dan datanya, atau hapus berkasnya.")

    baris_mentah = teks.splitlines()
    # Pemisah dideteksi dari baris kepala — baris pertama yang bukan penjelasan dan bukan baris
    # contoh, memakai aturan `_diabaikan` yang sama dengan pembacaannya.
    nomor_kepala = next(
        (i for i, satu in enumerate(baris_mentah) if not _diabaikan(next(csv.reader([satu]), []))),
        None,
    )
    baris_kepala = baris_mentah[nomor_kepala] if nomor_kepala is not None else ""
    pemisah = ";" if ";" in baris_kepala and baris_kepala.count(";") >= baris_kepala.count(",") else ","
    # Nomor baris ikut dibawa supaya pesan galat menunjuk baris yang benar di berkas aslinya,
    # bukan nomor urut setelah baris penjelasan dibuang.
    semua = [
        (nomor, satu)
        for nomor, satu in enumerate(csv.reader(baris_mentah, delimiter=pemisah), start=1)
        if not _diabaikan(satu)
    ]
    if not semua:
        raise GalatIngesti(f"{jalur.name}: tidak ada baris header maupun data yang bisa dibaca")

    header = tuple(_normalkan(nama) for nama in semua[0][1])
    if not any(header):
        raise GalatIngesti(f"{jalur.name}: baris pertama harus berisi nama kolom")
    # Sisa baris **mentah** (bukan hasil urai) dipakai sebagai bukti: kalau pemisahnya salah tebak,
    # seluruh baris menjadi satu kolom, sehingga bukti "berkas ini berkolom" harus dicari di teksnya.
    _periksa_kepala_satu_kolom(
        jalur, header, pemisah, baris_mentah[nomor_kepala + 1 :] if nomor_kepala is not None else []
    )

    isi: list[tuple[int, dict[str, str]]] = []
    for nomor, baris in semua[1:]:
        if not any(satu.strip() for satu in baris):
            continue  # baris kosong di tengah berkas diabaikan, bukan dianggap data
        _periksa_kolom_berlebih(jalur, nomor, header, baris)
        # Kolom yang **hilang** tetap dibaca sebisanya: nilainya menjadi '' dan dilaporkan sebagai
        # nilai kosong pada kolom itu — pesannya lebih menolong daripada "baris rusak". Kolom yang
        # **berlebih dan berisi** justru ditolak sebelum sampai ke sini (`_periksa_kolom_berlebih`).
        nilai = {header[i]: (baris[i] if i < len(baris) else "") for i in range(len(header))}
        isi.append((nomor, nilai))
    return header, isi


def _periksa_kolom_berlebih(
    jalur: Path, nomor: int, header: tuple[str, ...], baris: list[str]
) -> None:
    """Tolak baris yang memuat kolom **berlebih yang ada isinya** — isinya akan hilang tanpa jejak.

    Pembaca ini mengambil nilai hanya untuk kolom yang ada di kepala, jadi kolom selebihnya dulu
    dibuang **diam-diam**. Cara termudah sebuah baris menjadi berlebih adalah tanda pemisah `;` di
    dalam nilai sebuah kolom pada berkas yang ditulis dengan penggabungan string (`f"{a};{b}"`)
    alih-alih `csv.writer`: seluruh isi sesudah `;` pertama lenyap saat impor, termasuk penanda
    temuan dan kutipan keputusan. Terukur 16 Okt 2026 (sesi 7): **66 dari 171 baris** satu berkas
    kehilangan ekornya seperti itu, tanpa satu pun galat — dan karena tidak ada galat, tidak ada
    yang tahu selama dua sesi.

    Kolom berlebih yang **kosong** (mis. `;;` di ujung baris) tetap diterima: tidak ada isi yang
    hilang, dan bentuk itu lazim pada berkas yang disunting tangan.
    """
    if len(baris) <= len(header):
        return
    berlebih = [satu for satu in baris[len(header) :] if satu.strip()]
    if not berlebih:
        return
    raise GalatIngesti(
        f"{jalur.name} baris {nomor}: ada {len(berlebih)} kolom berlebih berisi data yang tidak "
        f"dikenali {berlebih[:2]!r}. Kolom yang dikenal ({len(header)}): {', '.join(header)}. "
        "Kalau diteruskan, isi kolom itu hilang tanpa jejak. Penyebab yang paling sering: tanda "
        "pemisah `;` di dalam nilai sebuah kolom (mis. `keterangan`) pada berkas yang ditulis "
        "dengan penggabungan string — tulis berkasnya dengan `csv.writer` supaya nilainya dikutip."
    )


#: Penanda baris contoh di template bawaan: tidak pernah ikut terimpor.
PENANDA_CONTOH = "<<CONTOH>>"


def _diabaikan(baris: Sequence[str]) -> bool:
    """Baris penjelasan (`#`) dan baris contoh (`<<CONTOH>>`) bukan data."""
    if not baris:
        return True
    return baris[0].strip().startswith("#") or PENANDA_CONTOH in baris[0]


def _periksa_kepala_satu_kolom(
    jalur: Path, header: Sequence[str], pemisah: str, baris_setelah_kepala: Sequence[str]
) -> None:
    """Tolak baris kepala yang terbaca sebagai satu kolom padahal berkasnya jelas berkolom.

    Keadaan ini tidak menunjuk sebabnya sendiri: pemakainya melihat "kolom tidak dikenal" untuk
    nama kolom yang jelas benar, dan tidak terpikir bahwa yang salah adalah **letak** baris
    kepalanya. Dua bukti dipakai, keduanya dari berkas itu sendiri: nama kolomnya masih memuat
    pemisah lain, atau baris di bawahnya memuat pemisah — yang berarti baris itu memang berkolom,
    sedangkan baris kepala tidak.
    """
    if len(header) != 1:
        return
    lain = next((satu for satu in (";", ",") if satu != pemisah and satu in header[0]), None)
    berkolom = any(
        satu in baris
        for baris in baris_setelah_kepala
        if baris.strip() and not baris.lstrip().startswith("#")
        for satu in (";", ",")
    )
    if lain is None and not berkolom:
        return
    raise GalatIngesti(
        f"{jalur.name}: baris kepala terbaca sebagai satu kolom ({header[0]!r}) padahal berkasnya "
        f"berkolom (pemisah {lain or pemisah!r}). Pemisah dideteksi dari baris pertama yang bukan "
        "penjelasan, jadi pastikan baris kepala (nama kolom) ada di baris paling atas dan baris "
        "penjelasan '#' menyusul di bawahnya."
    )


def _periksa_header(jalur: Path, header: Sequence[str], spesifikasi: Spesifikasi) -> None:
    """Kolom tak dikenal dan kolom wajib yang hilang menolak berkas, dengan menyebut namanya."""
    dikenal = set(spesifikasi.nama_kolom)
    asing = [nama for nama in header if nama and nama not in dikenal]
    if asing:
        mirip = ", ".join(sorted(dikenal))
        raise GalatIngesti(
            f"{jalur.name}: kolom tidak dikenal {asing}. Kolom yang dikenal: {mirip}. "
            "Salah ketik nama kolom berbahaya karena kolomnya lalu dianggap kosong."
        )
    hilang = [nama for nama in spesifikasi.wajib if nama not in header]
    if hilang:
        raise GalatIngesti(f"{jalur.name}: kolom wajib tidak ada: {hilang}")


def _tidak_kosong(nilai: str, di_mana: str, kolom: str) -> str:
    bersih = nilai.strip()
    if not bersih:
        raise GalatIngesti(f"{di_mana}: kolom `{kolom}` wajib diisi")
    return bersih


def _pilihan(nilai: str, di_mana: str, kolom: str, peta: Mapping[str, str]) -> str:
    bersih = _normalkan(nilai)
    if bersih not in peta:
        raise GalatIngesti(
            f"{di_mana}: kolom `{kolom}` berisi {nilai!r} yang tidak dikenal. "
            f"Pilihan yang sah: {', '.join(sorted(set(peta.values())))}"
        )
    return peta[bersih]


def _angka_bulat(nilai: str, di_mana: str, kolom: str) -> int:
    try:
        angka = Decimal(nilai.strip())
    except (InvalidOperation, ValueError) as galat:
        raise GalatIngesti(f"{di_mana}: kolom `{kolom}` berisi {nilai!r} yang bukan angka") from galat
    if not angka.is_finite() or angka != angka.to_integral_value():
        raise GalatIngesti(
            f"{di_mana}: kolom `{kolom}` harus bilangan bulat (T8); yang terbaca {nilai!r}"
        )
    return int(angka)


# ---------------------------------------------------------------------------------------
# Penyusun baris per jenis berkas
# ---------------------------------------------------------------------------------------


def _baris_emiten(nilai: Mapping[str, str], di_mana: str) -> Emiten:
    jenis_teks = (nilai.get("jenis") or "").strip()
    if _normalkan(jenis_teks) not in JENIS_EMITEN:
        raise GalatIngesti(
            f"{di_mana}: kolom `jenis` berisi {jenis_teks!r} yang tidak dikenal. "
            f"Pilihan yang sah: bank_keuangan, siklikal_komoditas, umum (boleh dikosongkan)"
        )
    free_float = (nilai.get("free_float_persen") or "").strip()
    tanggal_notasi = (nilai.get("tanggal_notasi") or "").strip()
    return Emiten(
        kode=_tidak_kosong(nilai.get("kode", ""), di_mana, "kode").upper(),
        nama=_tidak_kosong(nilai.get("nama", ""), di_mana, "nama"),
        sektor_idx_ic=(nilai.get("sektor_idx_ic") or "").strip() or None,
        sektor_sumber=(nilai.get("sektor_sumber") or "").strip() or None,
        jenis=JENIS_EMITEN[_normalkan(jenis_teks)],
        papan=(nilai.get("papan") or "").strip() or None,
        status_notasi=(nilai.get("status_notasi") or "").strip() or None,
        tanggal_notasi=(
            _ke_tanggal(tanggal_notasi, f"{di_mana} tanggal_notasi") if tanggal_notasi else None
        ),
        jumlah_saham=(
            _angka_bulat(nilai["jumlah_saham"], di_mana, "jumlah_saham")
            if (nilai.get("jumlah_saham") or "").strip()
            else None
        ),
        free_float_bp=_ke_basis_poin(free_float, f"{di_mana} free_float_persen") if free_float else None,
        sumber=_tidak_kosong(nilai.get("sumber", ""), di_mana, "sumber"),
        dicatat_pada=_ke_tanggal(
            _tidak_kosong(nilai.get("dicatat_pada", ""), di_mana, "dicatat_pada"),
            f"{di_mana} dicatat_pada",
        ),
    )


def _baris_harga(nilai: Mapping[str, str], di_mana: str) -> HargaHarian:
    def rupiah(kolom: str) -> tuple[int | None, str | None]:
        teks = (nilai.get(kolom) or "").strip()
        return (None, None) if not teks else _ke_rupiah(teks, f"{di_mana} {kolom}")

    buka, buka_mentah = rupiah("open")
    tinggi, tinggi_mentah = rupiah("high")
    rendah, rendah_mentah = rupiah("low")
    tutup, tutup_mentah = rupiah("close")
    volume_teks = (nilai.get("volume") or "").strip()
    volume, volume_mentah = (None, None) if not volume_teks else _ke_lembar(volume_teks, f"{di_mana} volume")
    nilai_teks = (nilai.get("nilai") or "").strip()
    nilai_transaksi, nilai_mentah = (
        (None, None) if not nilai_teks else _ke_rupiah(nilai_teks, f"{di_mana} nilai")
    )
    penanda_teks = (nilai.get("penyesuaian_sumber") or "").strip()
    penanda = (
        None
        if not penanda_teks
        else _pilihan(
            penanda_teks,
            di_mana,
            "penyesuaian_sumber",
            {nama: nama for nama in PENANDA_PENYESUAIAN_SAH},
        )
    )

    return HargaHarian(
        kode=_tidak_kosong(nilai.get("kode", ""), di_mana, "kode").upper(),
        tanggal=_ke_tanggal(_tidak_kosong(nilai.get("tanggal", ""), di_mana, "tanggal"), f"{di_mana} tanggal"),
        open=buka,
        high=tinggi,
        low=rendah,
        close=tutup,
        volume=volume,
        nilai=nilai_transaksi,
        open_mentah=buka_mentah,
        high_mentah=tinggi_mentah,
        low_mentah=rendah_mentah,
        close_mentah=tutup_mentah,
        volume_mentah=volume_mentah,
        nilai_mentah=nilai_mentah,
        penyesuaian_sumber=penanda,
        sumber=(nilai.get("sumber") or "").strip(),
    )


def _baris_indeks(nilai: Mapping[str, str], di_mana: str) -> PenutupanIndeks:
    teks = (nilai.get("close") or "").strip()
    tutup, tutup_mentah = (None, None) if not teks else _ke_rupiah(teks, f"{di_mana} close")
    return PenutupanIndeks(
        indeks=_tidak_kosong(nilai.get("indeks", ""), di_mana, "indeks").upper(),
        tanggal=_ke_tanggal(_tidak_kosong(nilai.get("tanggal", ""), di_mana, "tanggal"), f"{di_mana} tanggal"),
        close=tutup,
        close_mentah=tutup_mentah,
    )


def _baris_aksi(nilai: Mapping[str, str], di_mana: str) -> AksiKorporasi:
    jenis = _pilihan(_tidak_kosong(nilai.get("jenis", ""), di_mana, "jenis"), di_mana, "jenis", JENIS_AKSI)

    def angka(kolom: str) -> int | None:
        teks = (nilai.get(kolom) or "").strip()
        return None if not teks else _angka_bulat(teks, di_mana, kolom)

    tenggat = (nilai.get("tenggat") or "").strip()
    hasil = AksiKorporasi(
        kode=_tidak_kosong(nilai.get("kode", ""), di_mana, "kode").upper(),
        tanggal=_ke_tanggal(_tidak_kosong(nilai.get("tanggal", ""), di_mana, "tanggal"), f"{di_mana} tanggal"),
        jenis=jenis,
        rasio_lama=angka("rasio_lama"),
        rasio_baru=angka("rasio_baru"),
        harga_tebus=angka("harga_tebus"),
        dividen_per_saham=angka("dividen_per_saham"),
        tenggat=_ke_tanggal(tenggat, f"{di_mana} tenggat").isoformat() if tenggat else None,
        keterangan=(nilai.get("keterangan") or "").strip() or None,
    )
    # Bentuk yang dituntut tabel (CHECK di `skema.py`) diperiksa di sini juga supaya pesannya
    # menyebut nama berkas dan barisnya, bukan nomor baris basis data.
    if jenis != "dividen" and (hasil.rasio_lama is None or hasil.rasio_baru is None):
        raise GalatIngesti(f"{di_mana}: `{jenis}` wajib mengisi `rasio_lama` dan `rasio_baru`")
    if jenis == "right_issue" and hasil.harga_tebus is None:
        raise GalatIngesti(f"{di_mana}: `right_issue` wajib mengisi `harga_tebus`")
    if jenis == "dividen" and hasil.dividen_per_saham is None:
        raise GalatIngesti(f"{di_mana}: `dividen` wajib mengisi `dividen_per_saham`")
    if hasil.tenggat is not None and jenis != "right_issue":
        raise GalatIngesti(
            f"{di_mana}: `tenggat` hanya berlaku untuk `right_issue`, bukan `{jenis}`. Tenggat pada "
            "aksi lain tidak akan pernah dinilai, dan diam-diam membuat batas waktunya tampak ada"
        )
    return hasil


def _baris_catatan_aksi_mutu(nilai: Mapping[str, str], di_mana: str) -> CatatanAksiMutu:
    """Baca konteks aksi dengan satuan eksplisit; tidak dipetakan ke aksi operasional."""
    sumber_url = _tidak_kosong(nilai.get("sumber_url", ""), di_mana, "sumber_url")
    try:
        alamat = urlparse(sumber_url)
    except ValueError as galat:
        raise GalatIngesti(f"{di_mana}: `sumber_url` tidak dapat dibaca: {galat}") from galat
    if alamat.scheme not in {"http", "https"} or not alamat.netloc:
        raise GalatIngesti(f"{di_mana}: `sumber_url` harus berupa URL http/https lengkap")
    return CatatanAksiMutu(
        kode=_tidak_kosong(nilai.get("kode", ""), di_mana, "kode").upper(),
        tanggal_efektif=_ke_tanggal(
            _tidak_kosong(nilai.get("tanggal_efektif", ""), di_mana, "tanggal_efektif"),
            f"{di_mana} tanggal_efektif",
        ),
        instrumen_aksi=_tidak_kosong(nilai.get("instrumen_aksi", ""), di_mana, "instrumen_aksi"),
        ringkasan_bukti=_tidak_kosong(nilai.get("ringkasan_bukti", ""), di_mana, "ringkasan_bukti"),
        sumber_url=sumber_url,
        sumber=_tidak_kosong(nilai.get("sumber", ""), di_mana, "sumber"),
    )


_AKTIF_BENAR = frozenset({"1", "ya", "yes", "y", "true", "benar"})
_AKTIF_SALAH = frozenset({"0", "tidak", "no", "n", "false", "salah"})


def _baris_sambungan_harga(nilai: Mapping[str, str], di_mana: str) -> SambunganHarga:
    """Pernyataan sambungan harga (K97). `aktif` hanya ya/tidak: nilai lain bukan pernyataan."""
    teks_aktif = _normalkan(_tidak_kosong(nilai.get("aktif", ""), di_mana, "aktif"))
    if teks_aktif not in _AKTIF_BENAR | _AKTIF_SALAH:
        raise GalatIngesti(f"{di_mana}: `aktif` harus ya/tidak, bukan {nilai.get('aktif')!r}")
    return SambunganHarga(
        berlaku_sejak=_ke_tanggal(
            _tidak_kosong(nilai.get("berlaku_sejak", ""), di_mana, "berlaku_sejak"),
            f"{di_mana} berlaku_sejak",
        ),
        sumber_resmi=_tidak_kosong(nilai.get("sumber_resmi", ""), di_mana, "sumber_resmi"),
        aktif=teks_aktif in _AKTIF_BENAR,
        sumber=_tidak_kosong(nilai.get("sumber", ""), di_mana, "sumber"),
        keterangan=(nilai.get("keterangan") or "").strip() or None,
    )


def _baris_kalender(nilai: Mapping[str, str], di_mana: str) -> HariBursa:
    teks = _normalkan(_tidak_kosong(nilai.get("hari_bursa", ""), di_mana, "hari_bursa"))
    if teks in HARI_BURSA_BENAR:
        hari = True
    elif teks in HARI_BURSA_SALAH:
        hari = False
    else:
        raise GalatIngesti(
            f"{di_mana}: kolom `hari_bursa` berisi {nilai.get('hari_bursa')!r} yang tidak dikenal. "
            "Pakai 1/0 atau ya/tidak."
        )
    return HariBursa(
        tanggal=_ke_tanggal(_tidak_kosong(nilai.get("tanggal", ""), di_mana, "tanggal"), f"{di_mana} tanggal"),
        hari_bursa=hari,
        keterangan=(nilai.get("keterangan") or "").strip() or None,
        sumber=(nilai.get("sumber") or "").strip() or None,
    )


def _baris_notasi(nilai: Mapping[str, str], di_mana: str) -> NotasiKhusus:
    selesai = (nilai.get("tanggal_selesai") or "").strip()
    return NotasiKhusus(
        kode=_tidak_kosong(nilai.get("kode", ""), di_mana, "kode").upper(),
        jenis=_pilihan(
            _tidak_kosong(nilai.get("jenis", ""), di_mana, "jenis"), di_mana, "jenis", JENIS_NOTASI
        ),
        tanggal_mulai=_ke_tanggal(
            _tidak_kosong(nilai.get("tanggal_mulai", ""), di_mana, "tanggal_mulai"), f"{di_mana} tanggal_mulai"
        ),
        tanggal_selesai=(
            _ke_tanggal(selesai, f"{di_mana} tanggal_selesai") if selesai else None
        ),
        keterangan=(nilai.get("keterangan") or "").strip() or None,
    )


def _baris_sun(nilai: Mapping[str, str], di_mana: str) -> ImbalHasilSUN:
    persen = (nilai.get("imbal_hasil_persen") or "").strip()
    bp = _ke_basis_poin(_tidak_kosong(persen, di_mana, "imbal_hasil_persen"), f"{di_mana} imbal_hasil_persen")
    if bp is None:
        raise GalatIngesti(f"{di_mana}: kolom `imbal_hasil_persen` wajib diisi")
    sumber = (nilai.get("sumber") or "").strip()
    return ImbalHasilSUN(
        tanggal=_ke_tanggal(_tidak_kosong(nilai.get("tanggal", ""), di_mana, "tanggal"), f"{di_mana} tanggal"),
        tenor_tahun=_angka_bulat(
            _tidak_kosong(nilai.get("tenor_tahun", ""), di_mana, "tenor_tahun"), di_mana, "tenor_tahun"
        ),
        imbal_hasil_bp=bp,
        # Sumber per baris ikut disimpan di keterangan mentah supaya asal angkanya tidak
        # hilang saat beberapa berkas berbeda digabung dalam satu impor.
        imbal_hasil_mentah=f"{_teks_mentah(persen)}" + (f" | {sumber}" if sumber else ""),
    )


def _baris_rasio_bank(nilai: Mapping[str, str], di_mana: str) -> RasioBank:
    def persen(kolom: str) -> int | None:
        teks = (nilai.get(kolom) or "").strip()
        return None if not teks else _ke_basis_poin(teks, f"{di_mana} {kolom}")

    hasil = RasioBank(
        kode=_tidak_kosong(nilai.get("kode", ""), di_mana, "kode").upper(),
        periode=_ke_tanggal(
            _tidak_kosong(nilai.get("periode", ""), di_mana, "periode"), f"{di_mana} periode"
        ),
        tgl_publikasi=_ke_tanggal(
            _tidak_kosong(nilai.get("tgl_publikasi", ""), di_mana, "tgl_publikasi"),
            f"{di_mana} tgl_publikasi",
        ),
        npl_kotor_bp=persen("npl_kotor_persen"),
        car_bp=persen("car_persen"),
        bopo_bp=persen("bopo_persen"),
        nim_bp=persen("nim_persen"),
        keterangan=(nilai.get("keterangan") or "").strip() or None,
        # Kolom `sumber` wajib di berkas ini, dan sejak K78 ia **dipakai** — bukan hanya
        # divalidasi lalu dibuang, supaya asal tiap publikasi bank (URL + tanggal) tidak hilang
        # menjadi satu label folder begitu beberapa bank masuk dalam satu kali impor.
        sumber=_tidak_kosong(nilai.get("sumber", ""), di_mana, "sumber"),
    )
    if all(
        satu is None
        for satu in (hasil.npl_kotor_bp, hasil.car_bp, hasil.bopo_bp, hasil.nim_bp)
    ):
        raise GalatIngesti(
            f"{di_mana}: tidak ada satu pun rasio yang diisi (npl_kotor_persen, car_persen, "
            "bopo_persen, nim_persen). Baris kosong hanya akan menutupi data lama."
        )
    return hasil


def _uang_dengan_satuan(
    teks: str, faktor: int, di_mana: str, kolom: str, *, boleh_negatif: bool
) -> tuple[int | None, str | None]:
    """Angka laporan → rupiah utuh, dengan satuan dinyatakan berkas (bukan ditebak).

    Selisih pembulatan **ditolak**, bukan dipotong diam-diam: laporan "dalam jutaan" dengan
    angka berpecahan halus (mis. 0,0000001 juta) tidak punya arti dalam rupiah utuh, dan
    memotongnya berarti menyimpan angka yang berbeda dari sumbernya tanpa jejak.
    """
    bersih = teks.strip()
    if not bersih:
        return None, None
    angka = _desimal(bersih, f"{di_mana} {kolom}")
    if angka is None:
        return None, None
    if angka < 0 and not boleh_negatif:
        raise GalatIngesti(
            f"{di_mana}: kolom `{kolom}` berisi {bersih!r} negatif, padahal nilainya tidak "
            "bermakna negatif. Kosongkan kolomnya bila memang tidak ada."
        )
    nilai = angka * faktor
    if nilai != nilai.to_integral_value():
        raise GalatIngesti(
            f"{di_mana}: kolom `{kolom}` = {bersih!r} dikali satuannya tidak menghasilkan "
            "rupiah utuh; periksa `satuan_uang` berkas ini"
        )
    return int(nilai), _teks_mentah(bersih)


def _baris_fundamental(nilai: Mapping[str, str], di_mana: str) -> Fundamental:
    jenis = _pilihan(
        _tidak_kosong(nilai.get("jenis_laporan", ""), di_mana, "jenis_laporan"),
        di_mana,
        "jenis_laporan",
        {nama: nama for nama in JENIS_LAPORAN_SAH},
    )
    mata_uang = _pilihan(
        _tidak_kosong(nilai.get("mata_uang", ""), di_mana, "mata_uang"),
        di_mana,
        "mata_uang",
        {"idr": "IDR", "rp": "IDR", "rupiah": "IDR", "usd": "USD", "us$": "USD", "dolar": "USD"},
    )
    # Kolom kosong/tiada berarti `sumber`: berkas yang dirawat tangan memuat tanggal publikasi
    # yang sebenarnya. Nilai lain yang tidak dikenal tetap **ditolak**, bukan dianggap `sumber` —
    # salah ketik di sini akan membuat "tanggal pengambilan" terbaca sebagai tanggal terbit.
    asal_tgl_publikasi = _pilihan(
        (nilai.get("asal_tgl_publikasi") or "").strip() or ASAL_TGL_PUBLIKASI_BAWAAN,
        di_mana,
        "asal_tgl_publikasi",
        {nama: nama for nama in ASAL_TGL_PUBLIKASI_SAH},
    )
    satuan = _pilihan(
        _tidak_kosong(nilai.get("satuan_uang", ""), di_mana, "satuan_uang"),
        di_mana,
        "satuan_uang",
        {nama: nama for nama in FAKTOR_SATUAN_UANG},
    )
    faktor = FAKTOR_SATUAN_UANG[satuan]

    def uang(kolom: str, *, boleh_negatif: bool = False) -> tuple[int | None, str | None]:
        return _uang_dengan_satuan(
            nilai.get(kolom) or "", faktor, di_mana, kolom, boleh_negatif=boleh_negatif
        )

    pendapatan, pendapatan_mentah = uang("pendapatan")
    laba, laba_mentah = uang("laba_induk", boleh_negatif=True)
    ekuitas, ekuitas_mentah = uang("ekuitas_induk", boleh_negatif=True)
    ebit, _ = uang("ebit", boleh_negatif=True)
    beban_bunga, _ = uang("beban_bunga")
    da, _ = uang("da")
    utang_bunga, _ = uang("utang_bunga")
    kas, _ = uang("kas")
    cfo, _ = uang("cfo", boleh_negatif=True)
    # Jumlah saham & dividen per saham **tidak** ikut dikali satuan: keduanya sudah dinyatakan
    # per satuan (lembar, rupiah per lembar) di laporan, bukan dalam skala laporan.
    saham_teks = (nilai.get("jumlah_saham") or "").strip()
    dps_teks = (nilai.get("dps") or "").strip()

    hasil = Fundamental(
        kode=_tidak_kosong(nilai.get("kode", ""), di_mana, "kode").upper(),
        periode=_ke_tanggal(
            _tidak_kosong(nilai.get("periode", ""), di_mana, "periode"), f"{di_mana} periode"
        ),
        jenis_laporan=jenis,
        tgl_publikasi=_ke_tanggal(
            _tidak_kosong(nilai.get("tgl_publikasi", ""), di_mana, "tgl_publikasi"),
            f"{di_mana} tgl_publikasi",
        ),
        asal_tgl_publikasi=asal_tgl_publikasi,
        mata_uang=mata_uang,
        satuan_uang=satuan,
        pendapatan=pendapatan,
        laba_induk=laba,
        ekuitas_induk=ekuitas,
        ebit=ebit,
        beban_bunga=beban_bunga,
        da=da,
        utang_bunga=utang_bunga,
        kas=kas,
        cfo=cfo,
        jumlah_saham=(
            _angka_bulat(saham_teks, di_mana, "jumlah_saham") if saham_teks else None
        ),
        dps=_ke_rupiah(dps_teks, f"{di_mana} dps")[0] if dps_teks else None,
        pendapatan_mentah=pendapatan_mentah,
        laba_induk_mentah=laba_mentah,
        ekuitas_induk_mentah=ekuitas_mentah,
        # Kolom `sumber` wajib di berkas ini, dan sejak K18 ia **dipakai** — bukan hanya
        # divalidasi lalu dibuang, supaya label "tidak resmi" milik baris hasil pengambil
        # otomatis tidak hilang saat melewati jalur impor.
        sumber=_tidak_kosong(nilai.get("sumber", ""), di_mana, "sumber"),
    )
    if all(
        satu is None
        for satu in (
            hasil.pendapatan,
            hasil.laba_induk,
            hasil.ekuitas_induk,
            hasil.ebit,
            hasil.cfo,
        )
    ):
        raise GalatIngesti(
            f"{di_mana}: seluruh kolom angka kosong. Baris seperti ini tidak menambah apa pun "
            "dan hanya akan menutupi data lama sebagai baris 'terkini'."
        )
    return hasil


_PENYUSUN: Mapping[str, Callable[[Mapping[str, str], str], Any]] = {
    "emiten": _baris_emiten,
    "harga_harian": _baris_harga,
    "harga_indeks": _baris_indeks,
    "aksi_korporasi": _baris_aksi,
    "catatan_aksi_mutu": _baris_catatan_aksi_mutu,
    "sambungan_harga": _baris_sambungan_harga,
    "kalender_bursa": _baris_kalender,
    "notasi_khusus": _baris_notasi,
    "imbal_hasil_sun": _baris_sun,
    "fundamental": _baris_fundamental,
    "rasio_bank": _baris_rasio_bank,
}


# ---------------------------------------------------------------------------------------
# Pembacaan satu folder
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HasilBaca:
    """Isi satu folder impor beserta jejak berkas mana yang dibaca dan mana yang tidak ada."""

    kumpulan: KumpulanData
    dibaca: tuple[str, ...]
    tidak_ada: tuple[str, ...]


def baca_folder(folder: Path) -> HasilBaca:
    """Baca seluruh berkas impor yang dikenali di dalam `folder`.

    Berkas yang tidak ada **dilewati dengan catatan**, bukan dianggap kegagalan: impor
    bertahap (mis. baru punya kalender bursa) harus tetap mungkin. Sebaliknya, berkas yang ada
    tetapi isinya salah menolak seluruh impor — tidak ada baris yang ditulis.
    """
    if not folder.is_dir():
        raise GalatIngesti(
            f"folder impor '{folder}' tidak ada atau bukan folder. "
            "Buat foldernya lalu isi berkas CSV sesuai template di mejasaham/defaults/."
        )

    terkumpul: dict[str, list[Any]] = {jenis: [] for _, jenis in BERKAS_IMPOR_DIKENAL}
    dibaca: list[str] = []
    tidak_ada: list[str] = []
    galat: list[str] = []

    for nama_berkas, jenis in BERKAS_IMPOR_DIKENAL:
        jalur = folder / nama_berkas
        if not jalur.is_file():
            tidak_ada.append(nama_berkas)
            continue

        spesifikasi = SPESIFIKASI[jenis]
        header, isi = _baca_baris(jalur)
        _periksa_header(jalur, header, spesifikasi)
        penyusun = _PENYUSUN[jenis]
        # Penjaga "satu baris per kunci" dijalankan **sebelum** apa pun disimpan: berkas yang
        # memuat dua revisi untuk laporan yang sama ditolak di sini, dengan nama berkas dan
        # nomor barisnya, bukan sebagai kegagalan penulisan yang menyebut kunci basis data.
        # Tanpa ini, seluruh berkas 794 baris ditolak oleh satu pasang baris yang bertabrakan.
        if kunci := KUNCI_ALAMI_BERKAS.get(jenis):
            _periksa_kunci_ganda(jalur, isi, kunci)

        jumlah_benar = 0
        for nomor, nilai in isi:
            di_mana = f"{nama_berkas} baris {nomor}"
            try:
                terkumpul[jenis].append(penyusun(_hanya_dikenal(nilai, spesifikasi), di_mana))
                jumlah_benar += 1
            except GalatIngesti as keluhan:
                galat.append(str(keluhan))
        dibaca.append(f"{nama_berkas} ({jumlah_benar} baris)")

    if galat:
        # Seluruh baris yang salah dilaporkan sekaligus: memperbaiki berkas 800 baris satu
        # galat per jalan bukan pengalaman yang bisa dipakai.
        rincian = "\n".join(f"  - {satu}" for satu in galat[:50])
        lebih = f"\n  ... dan {len(galat) - 50} baris salah lainnya" if len(galat) > 50 else ""
        raise GalatIngesti(
            f"{len(galat)} baris di folder '{folder}' tidak bisa dibaca; tidak ada yang diimpor:\n"
            f"{rincian}{lebih}"
        )

    if not dibaca:
        raise GalatIngesti(
            f"folder '{folder}' tidak memuat satu pun berkas impor yang dikenali. "
            f"Nama berkas yang dicari: {', '.join(nama for nama, _ in BERKAS_IMPOR_DIKENAL)}"
        )

    # Jalur absolut: label inilah yang membedakan sumber saat "sudah ada" dibandingkan (T100), jadi
    # `--impor .uji-data/x` dan refresh atas folder yang sama harus menghasilkan label yang sama.
    sumber = f"{PREFIKS_SUMBER_IMPOR}: {folder.resolve()}"
    return HasilBaca(
        kumpulan=KumpulanData(
            sumber=sumber,
            emiten=tuple(terkumpul["emiten"]),
            harga_harian=tuple(terkumpul["harga_harian"]),
            harga_indeks=tuple(terkumpul["harga_indeks"]),
            aksi_korporasi=tuple(terkumpul["aksi_korporasi"]),
            catatan_aksi_mutu=tuple(terkumpul["catatan_aksi_mutu"]),
            sambungan_harga=tuple(terkumpul["sambungan_harga"]),
            kalender_bursa=tuple(terkumpul["kalender_bursa"]),
            notasi_khusus=tuple(terkumpul["notasi_khusus"]),
            imbal_hasil_sun=tuple(terkumpul["imbal_hasil_sun"]),
            fundamental=tuple(terkumpul["fundamental"]),
            rasio_bank=tuple(terkumpul["rasio_bank"]),
            catatan=(f"berkas dibaca: {', '.join(dibaca)}",),
        ),
        dibaca=tuple(dibaca),
        tidak_ada=tuple(tidak_ada),
    )


def _hanya_dikenal(nilai: Mapping[str, str], spesifikasi: Spesifikasi) -> dict[str, str]:
    """Buang kolom di luar spesifikasi.

    Aman karena `_periksa_header` sudah menolak kolom tak dikenal sebelumnya; fungsi ini hanya
    menjaga kolom `None` dari header kosong agar tidak bocor ke penyusun.
    """
    return {nama: (nilai.get(nama) or "") for nama in spesifikasi.nama_kolom}


def baca_emiten(folder: Path) -> tuple[Emiten, ...]:
    """Baca **hanya** berkas rujukan emiten.

    Dipakai `--refresh`: daftar emiten adalah masukan wajib pengambilan data, sedangkan berkas
    lain (fundamental, kalender) boleh belum ada. Memisahkannya mencegah "kalender bursa belum
    saya isi" menjadi alasan refresh tidak bisa jalan sama sekali.
    """
    jalur = folder / NAMA_BERKAS_EMITEN
    if not jalur.is_file():
        raise GalatIngesti(
            f"berkas rujukan emiten '{jalur}' tidak ada.\n"
            "Ingesti butuh daftar emiten yang Anda kendalikan; daftar itu tidak dikarang "
            "aplikasi. Isi berkas CSV dengan header berikut, satu baris per emiten:\n"
            "  kode;nama;sektor_idx_ic;sektor_sumber;jenis;papan;status_notasi;tanggal_notasi;"
            "jumlah_saham;free_float_persen;sumber;dicatat_pada\n"
            "Contoh baris: BBCA;Bank Central Asia;keuangan;Financials;bank_keuangan;utama;;;"
            "Daftar resmi IDX (diakses 9 Okt 2026);2026-10-09\n"
            "`sektor_idx_ic` = klasifikasi IDX-IC (PRD 8.2); `sektor_sumber` = sektor sebagaimana "
            "dinyatakan sumber data — dua hal berbeda, jangan diisi dengan nilai yang sama."
            "Kolom `tanggal_notasi` (tanggal pencatatan saham) diisi bentuk YYYY-MM-DD bila "
            "sumber Anda menyatakannya; kosongkan bila tidak — jangan diisi tanggal tebakan."
        )
    header, isi = _baca_baris(jalur)
    spesifikasi = SPESIFIKASI["emiten"]
    _periksa_header(jalur, header, spesifikasi)

    hasil: list[Emiten] = []
    galat: list[str] = []
    for nomor, nilai in isi:
        di_mana = f"{NAMA_BERKAS_EMITEN} baris {nomor}"
        try:
            hasil.append(_baris_emiten(_hanya_dikenal(nilai, spesifikasi), di_mana))
        except GalatIngesti as keluhan:
            galat.append(str(keluhan))
    if galat:
        rincian = "\n".join(f"  - {satu}" for satu in galat[:50])
        raise GalatIngesti(f"{len(galat)} baris di '{jalur}' tidak bisa dibaca:\n{rincian}")
    if not hasil:
        raise GalatIngesti(
            f"'{jalur}' tidak memuat satu baris emiten pun; tidak ada yang bisa diambil. "
            "Isi berkasnya dari daftar resmi IDX, atau hapus berkasnya bila memang belum siap."
        )
    return tuple(hasil)


def baca_kalender(folder: Path) -> tuple[HariBursa, ...]:
    """Baca **hanya** berkas kalender bursa.

    Dipakai `kalender.py` sebagai bukti baca-ulang sesudah menulis berkasnya, dan sebagai jalan
    masuk yang tidak menyeret berkas lain: kalender adalah masukan tersendiri, dan kesalahan di
    `fundamental.csv` tidak boleh membuat kalender yang sudah benar ikut ditolak.
    """
    jalur = folder / NAMA_BERKAS_KALENDER
    if not jalur.is_file():
        raise GalatIngesti(
            f"berkas kalender bursa '{jalur}' tidak ada.\n"
            "Kalender bursa menentukan arti \"hari bursa terakhir\" dan peringatan snapshot basi. "
            "Isi dengan `python -m mejasaham --ambil-kalender`, atau isi sendiri berkas CSV "
            "dengan header berikut, satu baris per tanggal:\n"
            "  tanggal;hari_bursa;keterangan;sumber\n"
            "Contoh baris: 2027-01-01;0;Tahun Baru 2027 Masehi;PENG-0004/DIR/KSEI/0926\n"
            "Hari libur ditulis juga (hari_bursa=0) supaya rentang tanggal bisa ditanyakan utuh."
        )
    header, isi = _baca_baris(jalur)
    spesifikasi = SPESIFIKASI["kalender_bursa"]
    _periksa_header(jalur, header, spesifikasi)

    hasil: list[HariBursa] = []
    galat: list[str] = []
    for nomor, nilai in isi:
        di_mana = f"{NAMA_BERKAS_KALENDER} baris {nomor}"
        try:
            hasil.append(_baris_kalender(_hanya_dikenal(nilai, spesifikasi), di_mana))
        except GalatIngesti as keluhan:
            galat.append(str(keluhan))
    if galat:
        rincian = "\n".join(f"  - {satu}" for satu in galat[:50])
        raise GalatIngesti(f"{len(galat)} baris di '{jalur}' tidak bisa dibaca:\n{rincian}")
    if not hasil:
        raise GalatIngesti(
            f"'{jalur}' tidak memuat satu tanggal pun; tidak ada yang bisa dipakai. "
            "Isi berkasnya, atau hapus berkasnya bila memang belum siap."
        )
    return tuple(hasil)


def kode_duplikat(emiten: Iterable[Emiten]) -> tuple[str, ...]:
    """Kode yang muncul lebih dari sekali di berkas rujukan.

    Bukan kegagalan (boleh ada dua baris dengan `dicatat_pada` berbeda = koreksi), tetapi
    dilaporkan supaya salah salin tidak lewat tanpa terlihat.
    """
    terlihat: dict[str, int] = {}
    for satu in emiten:
        terlihat[satu.kode] = terlihat.get(satu.kode, 0) + 1
    return tuple(sorted(kode for kode, jumlah in terlihat.items() if jumlah > 1))


#: Berkas impor yang isinya menyimpan **riwayat**: dua baris dengan kunci alami sama di dalam
#: satu berkas selalu berarti salah satu dari dua hal, dan keduanya tidak boleh ditulis.
#:
#: * orang menyalin satu laporan dua kali, sehingga berkasnya memuat baris kembar; atau
#: * orang menaruh laporan asli dan restatement-nya bersebelahan.
#:
#: Yang **tidak** ada di daftar ini: `harga_harian` (revisi harga satu tanggal adalah keadaan
#: biasa), dan `emiten`/`kalender_bursa` (kuncinya memang boleh berulang sebagai koreksi
#: bertanggal — `kode_duplikat` sudah melaporkannya sebagai peringatan, bukan penolakan).
KUNCI_ALAMI_BERKAS: Mapping[str, tuple[str, ...]] = {
    "fundamental": ("kode", "periode", "jenis_laporan"),
    "rasio_bank": ("kode", "periode"),
    "catatan_aksi_mutu": ("kode", "tanggal_efektif", "instrumen_aksi"),
    "sambungan_harga": ("berlaku_sejak",),
}


def _periksa_kunci_ganda(
    jalur: Path,
    isi: Sequence[tuple[int, Mapping[str, str]]],
    kunci: Sequence[str],
) -> None:
    """Tolak berkas yang memuat dua baris **berbeda** untuk kunci riwayat yang sama.

    Yang dibandingkan bukan kuncinya saja melainkan **seluruh baris**: dua baris kembar yang sama
    persis adalah kelalaian yang tidak berbahaya, dan menolaknya hanya menambah pekerjaan orang
    yang sedang memperbaiki berkasnya. Yang berbahaya adalah dua isi berbeda untuk satu kunci —
    di titik tulis keduanya tidak muat, sehingga seluruh berkas ditolak oleh satu pasang baris
    yang bertabrakan.

    Diperiksa di **teks berkas**, bukan pada objeknya: yang bisa dilakukan di sini hanyalah
    membandingkan nilai mentah, sedangkan kesamaan sesudah normalisasi adalah urusan penyusunnya.
    Karena itu baris yang gagal diurai dilewati — ia sudah akan dilaporkan sebagai baris salah
    oleh lintasan utamanya, dan melaporkannya dua kali hanya menambah bising.
    """
    letak: dict[tuple[str, ...], tuple[int, tuple[tuple[str, str], ...]]] = {}
    for nomor, nilai in isi:
        satu_kunci = tuple((nilai.get(kolom) or "").strip().upper() for kolom in kunci)
        if not all(satu_kunci):
            continue
        sidik_baris = tuple(sorted((nama, (angka or "").strip()) for nama, angka in nilai.items()))
        if (lama := letak.get(satu_kunci)) is not None and lama[1] != sidik_baris:
            raise GalatIngesti(
                f"{jalur.name}: baris {lama[0]} dan {nomor} memakai kunci yang sama "
                f"({', '.join(f'{kolom}={bagian}' for kolom, bagian in zip(kunci, satu_kunci))}) "
                "tetapi isinya berbeda. Satu berkas hanya boleh memuat **satu** baris per kunci: "
                "impor memakai satu `diketahui_pada` untuk seluruh berkas, sehingga dua baris "
                "untuk kunci yang sama tidak bisa disimpan berdampingan. Kalau baris kedua adalah "
                "perbaikan (restatement), impor berkasnya terpisah dan jalankan impor itu setelah "
                "jeda — perbaikan data menambah baris baru dengan waktu diketahui yang lebih baru, "
                "bukan satu berkas berisi dua revisi (PRD 7.2, S1)."
            )
        letak[satu_kunci] = (nomor, sidik_baris)


def tanggal_data_dari(kumpulan: KumpulanData) -> date:
    """Tanggal data snapshot: bar terakhir yang tersedia (bukan tanggal hari ini).

    Snapshot adalah **batas waktu data** (A4). Memakai tanggal hari ini akan menyatakan "kami
    punya data sampai hari ini" pada hari libur bursa — pernyataan yang salah dan langsung
    memicu peringatan snapshot basi yang keliru.
    """
    tanggal_harga = [satu.tanggal for satu in kumpulan.harga_harian]
    tanggal_indeks = [satu.tanggal for satu in kumpulan.harga_indeks]
    if not tanggal_harga and not tanggal_indeks:
        raise GalatIngesti(
            "tidak ada satu bar harga pun yang terbaca; tanggal data snapshot tidak bisa "
            "ditentukan dan snapshot kosong tidak diterbitkan"
        )
    return max(tanggal_harga + tanggal_indeks)
