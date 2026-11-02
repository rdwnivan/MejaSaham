"""Konfigurasi bawaan harus tetap kosong dari nilai yang belum diverifikasi.

Menguji tiga hal:
  - template konfigurasi bawaan harus tetap terbaca sebagai TOML;
  - nilai yang belum diverifikasi TIDAK ditulis. Kalau seseorang membuka komentar
    sebuah entri di template, uji ini gagal — dan itu memang tujuannya: nilai yang
    sudah diverifikasi harus masuk konfigurasi aktif, bukan template;
  - setiap baris contoh CSV **cocok kolomnya dengan kepalanya**. Baris contoh tidak pernah
    terimpor, jadi kekeliruan di situ tidak akan ketahuan dari jalan mana pun — padahal ia yang
    dilihat orang pertama kali, dan orang menyalin bentuknya. Bentuk yang salah kolom akan
    menghasilkan berkas yang ditolak parser, dengan pesan yang menunjuk berkas pengguna alih-alih
    template yang menyesatkan.
"""

from __future__ import annotations

import csv
import io
import tomllib
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[1]
FOLDER_BAWAAN = AKAR / "mejasaham" / "defaults"
TEMPLATE = FOLDER_BAWAAN / "parameter-bursa.contoh.toml"

#: Penanda baris contoh di template bawaan: tidak pernah ikut terimpor (lihat `berkas.py`).
PENANDA_CONTOH = "<<CONTOH>>"

#: Seluruh template CSV bawaan. Daftarnya ditulis di sini, bukan dibaca dari folder, supaya
#: template baru yang lupa diuji membuat uji ini gagal alih-alih diam-diam tidak diperiksa.
TEMPLATE_CSV = (
    "aksi-korporasi.contoh.csv",
    "catatan-aksi-mutu.contoh.csv",
    "emiten.contoh.csv",
    "emiten-awal.contoh.csv",
    "fundamental.contoh.csv",
    "harga-harian.contoh.csv",
    "harga-indeks.contoh.csv",
    "imbal-hasil-sun.contoh.csv",
    "kalender-bursa.contoh.csv",
    "notasi-khusus.contoh.csv",
    "rasio-bank.contoh.csv",
)

#: Template yang barisnya **data sungguhan**, bukan baris contoh: `--emiten-awal` menyalinnya
#: apa adanya menjadi `emiten.csv`, jadi menambahkan penanda `<<CONTOH>>` di sana justru akan
#: membuat daftar awalnya tidak terpakai sama sekali.
TEMPLATE_TANPA_BARIS_CONTOH = ("emiten-awal.contoh.csv",)


def _muat() -> dict:
    with TEMPLATE.open("rb") as berkas:
        return tomllib.load(berkas)


def test_template_ada_dan_terbaca() -> None:
    assert TEMPLATE.is_file(), f"template bawaan tidak ada: {TEMPLATE}"
    assert _muat()["skema"] == 1


def test_template_tidak_memuat_entri_aktif() -> None:
    aktif = sorted(kunci for kunci in _muat() if kunci != "skema")
    assert not aktif, (
        "Template memuat entri aktif; nilai belum diverifikasi harus tetap "
        f"dikomentari sampai diverifikasi: {aktif}"
    )


def test_daftar_template_csv_lengkap() -> None:
    """Template CSV yang ada di folder bawaan harus terdaftar di uji ini."""
    ada = {jalur.name for jalur in FOLDER_BAWAAN.glob("*.contoh.csv")}

    assert ada == set(TEMPLATE_CSV), (
        "template CSV belum terdaftar di TEMPLATE_CSV: " + ", ".join(sorted(ada - set(TEMPLATE_CSV)))
    )


@pytest.mark.parametrize("nama", TEMPLATE_CSV)
def test_baris_contoh_cocok_kolom_dengan_kepala(nama: str) -> None:
    """Jumlah kolom tiap baris data = jumlah kolom kepala.

    Baris contoh tidak pernah terimpor, jadi kekeliruan jumlah kolom di situ tidak akan ketahuan
    dari jalan mana pun — padahal ia yang pertama dilihat orang, dan orang menyalin bentuknya.
    Baris yang kolomnya kurang akan menggeser seluruh arti kolom tanpa satu pun pesan galat.

    Untuk template yang barisnya data sungguhan (`emiten-awal`), yang diperiksa adalah baris
    datanya; di sana penanda `<<CONTOH>>` justru akan merusak.
    """
    jalur = FOLDER_BAWAAN / nama
    baris = [
        satu
        for satu in csv.reader(io.StringIO(jalur.read_text(encoding="utf-8-sig")), delimiter=";")
        if satu and not satu[0].lstrip().startswith("#")
    ]
    assert baris, f"{nama}: tidak ada baris kepala"

    kepala, *data = baris
    assert data, f"{nama}: tidak ada baris data untuk diperiksa"
    tanpa_contoh = nama in TEMPLATE_TANPA_BARIS_CONTOH
    for nomor, satu in enumerate(data, start=2):
        if tanpa_contoh:
            assert satu[0] != PENANDA_CONTOH, (
                f"{nama} baris {nomor}: template ini dipakai apa adanya, jadi tidak boleh "
                f"memakai penanda {PENANDA_CONTOH}"
            )
        else:
            assert satu[0] == PENANDA_CONTOH, (
                f"{nama} baris {nomor}: baris contoh harus dimulai {PENANDA_CONTOH}, bukan {satu[0]!r}"
            )
        assert len(satu) == len(kepala), (
            f"{nama} baris {nomor}: {len(satu)} kolom, sedangkan kepalanya {len(kepala)} "
            f"({';'.join(kepala)})"
        )
