"""Uji pemuat snapshot point-in-time (A4, S3, aturan keras 3, PRD 7.2/9.9).

Yang diuji di sini bukan "apakah `potret.muat` mengembalikan baris", melainkan dua janji yang
membuat sebuah snapshot layak dipakai menghitung:

* **Fundamental dipakai sejak `tgl_publikasi`, bukan sejak akhir periode** (AC-15). Laporan yang
  belum terbit pada tanggal snapshot tidak boleh ikut menghitung apa pun — dan laporan yang
  terbit **tepat** pada tanggal itu sudah boleh dipakai. Aturan yang sama berlaku untuk
  `rasio_bank`, yang terbit dengan irama berbeda dari laporan keuangan.
* **Point-in-time, bukan "yang terbaru"** (aturan keras 3, PRD 9.9). Revisi harga yang dicatat
  *setelah* snapshot dibuat tidak boleh bocor ke snapshot lama. Itulah bedanya dengan
  `v_<tabel>_terkini`, yang memang menyajikan keadaan basis data **hari ini** — dan uji ini
  membuktikan kueri as-of benar-benar bekerja, bukan sekadar tampilan itu dengan nama lain.
* **Provenance per baris sampai ke pemanggil `Potret`** (K82). `sumber` yang sudah tersimpan
  **tidak boleh hilang saat baris dibaca kembali**: `Potret` adalah satu-satunya pintu masuk
  perhitungan (PRD 5), jadi apa yang tidak dibawanya tidak bisa dilihat modul hilir mana pun.

Seluruh data uji ditulis lewat jalur nyata (`ingesti.simpan` → `potret.muat`), bukan dengan
menyusun objek di memori: yang diuji adalah kueri as-of beserta baris `snapshot`, jadi datanya
harus benar-benar ada di basis data lebih dulu.

Angka harga dan fundamental di sini sengaja kecil dan bulat supaya nilai acuannya bisa
diperiksa tangan, bukan "kira-kira".
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest

from mejasaham import db, ingesti, lokasi, metrik, potret
from mejasaham.ingesti import (
    Emiten,
    Fundamental,
    GalatIngesti,
    HargaHarian,
    KumpulanData,
    RasioBank,
)

SUMBER = "uji"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
#: Momen kedua yang **berbeda detik** dari `MOMEN`: `diketahui_pada` berketelitian detik, jadi
#: dua penulisan dalam detik yang sama akan bertabrakan di kunci utama dan yang kedua tidak
#: ditulis — revisinya tidak akan pernah ada untuk diuji.
MOMEN_LANJUT = datetime(2026, 11, 1, 9, 0, 0)


# ---------------------------------------------------------------------------------------
# Piranti uji
# ---------------------------------------------------------------------------------------


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Folder data di luar paket (A3), ditimpa lewat `MEJASAHAM_DATA` seperti di produksi."""
    folder = tmp_path / "data"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(folder))
    return folder


@pytest.fixture()
def sambungan(folder_data: Path) -> Iterator[sqlite3.Connection]:
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _simpan(
    sambungan: sqlite3.Connection,
    *,
    tanggal_data: date = TANGGAL,
    momen: datetime = MOMEN,
    **isi: object,
) -> int:
    """Tulis satu snapshot lewat jalur nyata dan kembalikan `id_snapshot`-nya."""
    kumpulan = KumpulanData(sumber=SUMBER, **isi)  # type: ignore[arg-type]
    return ingesti.simpan(
        sambungan, kumpulan, tanggal_data=tanggal_data, momen=momen
    ).id_snapshot


def _emiten(kode: str, **ubah: object) -> Emiten:
    return Emiten(kode=kode, nama=f"Emiten {kode}", sumber=SUMBER, **ubah)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------
# AC-15: fundamental sejak tanggal publikasinya
# ---------------------------------------------------------------------------------------


def test_fundamental_dipakai_sejak_tgl_publikasi_bukan_sejak_akhir_periode(
    sambungan: sqlite3.Connection,
) -> None:
    """AC-15: laporan yang belum terbit pada tanggal snapshot tidak boleh ikut menghitung.

    Data ujinya sengaja memuat tiga laporan dengan DER yang berbeda-beda, sehingga hasilnya
    menunjukkan laporan **mana** yang dipakai:

    * tahunan 31 Des 2025 (terbit 31 Mar 2026) — utang 1.000 jt ÷ ekuitas 2.000 jt → DER 0,5;
    * YTD 30 Jun 2026 (terbit **1 Agu 2026**, setelah tanggal snapshot) — 3.000 ÷ 5.000 → 0,6;
    * YTD 31 Mar 2026 (terbit **tepat** 30 Jun 2026) — 800 ÷ 2.000 → 0,4.

    DER harus 0,4: laporan terakhir yang **sudah terbit** saat snapshot. Bila 0,6 yang keluar,
    laporan yang belum terbit bocor ke perhitungan; bila 0,5, laporan yang terbit tepat pada
    tanggal snapshot justru tertinggal. Keduanya salah dengan cara yang berbeda, dan keduanya
    terlihat dari satu angka.
    """
    laporan_tahunan = Fundamental(
        kode="AAAA",
        periode=date(2025, 12, 31),
        jenis_laporan="tahunan",
        tgl_publikasi=date(2026, 3, 31),
        utang_bunga=1_000_000_000,
        ekuitas_induk=2_000_000_000,
    )
    laporan_belum_terbit = Fundamental(
        kode="AAAA",
        periode=date(2026, 6, 30),
        jenis_laporan="ytd_kumulatif",
        tgl_publikasi=date(2026, 8, 1),
        utang_bunga=3_000_000_000,
        ekuitas_induk=5_000_000_000,
    )
    laporan_tepat_pada_tanggal = Fundamental(
        kode="AAAA",
        periode=date(2026, 3, 31),
        jenis_laporan="ytd_kumulatif",
        tgl_publikasi=TANGGAL,
        utang_bunga=800_000_000,
        ekuitas_induk=2_000_000_000,
    )

    _simpan(
        sambungan,
        emiten=(_emiten("AAAA"),),
        fundamental=(laporan_tahunan, laporan_belum_terbit, laporan_tepat_pada_tanggal),
    )
    potret_uji = potret.muat(sambungan)

    terpakai = [(satu.periode, satu.tgl_publikasi) for satu in potret_uji.fundamental["AAAA"]]
    assert terpakai == [
        (date(2025, 12, 31), date(2026, 3, 31)),
        (date(2026, 3, 31), TANGGAL),
    ], "hanya laporan yang terbit pada atau sebelum tanggal snapshot yang boleh ikut"
    assert metrik.der(potret_uji, "AAAA").nilai == pytest.approx(
        0.4
    ), "DER harus dari laporan 31 Mar 2026 (0,4), bukan dari laporan yang belum terbit (0,6)"


def test_rasio_bank_hanya_dipakai_sejak_tgl_publikasinya(sambungan: sqlite3.Connection) -> None:
    """Aturan AC-15 berlaku sama untuk `rasio_bank`, yang terbit dengan irama sendiri (Q6).

    NPL kuartal II 2026 yang baru terbit 15 Agu 2026 belum diketahui saat snapshot 30 Jun 2026,
    jadi yang dipakai adalah NPL kuartal I (250 basis poin). Kalau rasio yang belum terbit ikut
    terpakai, saringan bank akan menilai kesehatan bank dengan angka yang belum ada — dan tidak
    ada satu pun tanda di layar bahwa itu terjadi.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("BBRI", jenis="bank_keuangan"),),
        rasio_bank=(
            RasioBank(
                kode="BBRI",
                periode=date(2026, 3, 31),
                tgl_publikasi=date(2026, 4, 30),
                npl_kotor_bp=250,
                car_bp=2_000,
                bopo_bp=7_000,
                nim_bp=500,
            ),
            RasioBank(
                kode="BBRI",
                periode=date(2026, 6, 30),
                tgl_publikasi=date(2026, 8, 15),
                npl_kotor_bp=300,
                car_bp=2_100,
                bopo_bp=6_900,
                nim_bp=510,
            ),
        ),
    )
    potret_uji = potret.muat(sambungan)

    periode = [satu.periode for satu in potret_uji.rasio_bank["BBRI"]]
    assert periode == [date(2026, 3, 31)], "rasio yang belum terbit tidak boleh ada di potret"
    assert metrik.npl_kotor(potret_uji, "BBRI").nilai == pytest.approx(
        250.0
    ), "NPL harus dari kuartal I (250 bp), bukan dari kuartal II yang belum terbit (300 bp)"


# ---------------------------------------------------------------------------------------
# K82: sumber per baris fundamental ikut kembali lewat potret
# ---------------------------------------------------------------------------------------

#: Dua publikasi **berbeda** dalam satu kumpulan data. Nilainya sengaja tidak sama dengan label
#: kumpulan (`SUMBER`) maupun dengan kode emitennya, supaya `None` atau label yang tertukar tidak
#: lolos sebagai jawaban yang kebetulan benar.
SUMBER_PER_BARIS_BBCA = "Laporan Keuangan Publikasi 30 Juni 2026 (bca.co.id)"
SUMBER_PER_BARIS_BRIS = "Laporan Publikasi Triwulanan Juni 2026, Laporan Rasio Keuangan"


def test_sumber_fundamental_per_baris_ikut_kembali_lewat_potret(
    sambungan: sqlite3.Connection,
) -> None:
    """Provenance per baris harus terbaca pemanggil `Potret`, bukan hanya tersimpan (K82).

    Kolom `fundamental.sumber` sudah `NOT NULL` sejak K18, dan `ingesti` sudah menulis sumber
    **per baris** (`satu.sumber or kumpulan.sumber`). Yang hilang hanya satu langkah: saat baris
    dibaca kembali, `potret._fundamental` tidak meneruskan kolomnya — sehingga dua laporan dari
    dua publikasi yang berbeda tampak berasal dari sumber yang sama, yaitu "tidak dinyatakan",
    padahal basis datanya menyatakannya. Uji ini menempuh jalur nyata (simpan → muat) dan
    memeriksa **kedua** sisinya: barisnya memang tersimpan dengan asalnya masing-masing, dan
    `Potret` mengembalikan asal itu apa adanya.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("BBCA", jenis="bank_keuangan"), _emiten("BRIS", jenis="bank_keuangan")),
        fundamental=(
            Fundamental(
                kode="BBCA",
                periode=date(2026, 3, 31),
                jenis_laporan="ytd_kumulatif",
                tgl_publikasi=date(2026, 4, 30),
                ekuitas_induk=2_000_000_000,
                sumber=SUMBER_PER_BARIS_BBCA,
            ),
            Fundamental(
                kode="BRIS",
                periode=date(2026, 3, 31),
                jenis_laporan="ytd_kumulatif",
                tgl_publikasi=date(2026, 5, 4),
                ekuitas_induk=5_000_000_000,
                sumber=SUMBER_PER_BARIS_BRIS,
            ),
        ),
    )

    tersimpan = {
        baris["kode"]: baris["sumber"]
        for baris in sambungan.execute("SELECT kode, sumber FROM fundamental").fetchall()
    }
    assert tersimpan == {
        "BBCA": SUMBER_PER_BARIS_BBCA,
        "BRIS": SUMBER_PER_BARIS_BRIS,
    }, "dua laporan dari dua publikasi berbeda harus tersimpan dengan asalnya masing-masing"

    potret_uji = potret.muat(sambungan)
    assert [satu.sumber for satu in potret_uji.fundamental["BBCA"]] == [
        SUMBER_PER_BARIS_BBCA
    ], "sumber baris BBCA harus ikut terbaca; `None` berarti provenance-nya hilang saat dimuat"
    assert [satu.sumber for satu in potret_uji.fundamental["BRIS"]] == [
        SUMBER_PER_BARIS_BRIS
    ], "sumber baris BRIS harus ikut terbaca, bukan sumber bank lain atau label kumpulan"


def test_fundamental_tanpa_sumber_memakai_label_kumpulan_saat_dibaca_ulang(
    sambungan: sqlite3.Connection,
) -> None:
    """`sumber=None` berarti "ikut label kumpulan", dan arti itu harus tetap terbaca sesudah muat.

    Baris yang dibentuk tanpa sumber (mis. oleh kode program, bukan berkas) ditulis `ingesti`
    dengan label kumpulannya — aturan yang sama dengan `rasio_bank` (K78). Kalau `potret`
    mengembalikan `None`, arti itu hilang: pemanggil tidak bisa membedakan "barisnya tidak
    menyatakan asalnya" dari "barisnya berasal dari jalur lain". Label kumpulannya di sini
    **berbeda** dari kode emiten, jadi `None` tidak akan lolos sebagai jawaban yang kebetulan
    mirip.
    """
    _simpan(
        sambungan,
        emiten=(_emiten("AAAA"),),
        fundamental=(
            Fundamental(
                kode="AAAA",
                periode=date(2025, 12, 31),
                jenis_laporan="tahunan",
                tgl_publikasi=date(2026, 3, 31),
                laba_induk=1_000_000_000,
            ),
        ),
    )

    potret_uji = potret.muat(sambungan)
    assert [satu.sumber for satu in potret_uji.fundamental["AAAA"]] == [
        SUMBER
    ], "bidang `sumber` yang kosong memakai label kumpulan (K18/K78), bukan `None`"


# ---------------------------------------------------------------------------------------
# Point-in-time: revisi yang belum diketahui saat snapshot tidak boleh bocor
# ---------------------------------------------------------------------------------------


def test_snapshot_lama_tidak_melihat_revisi_harga_yang_diketahui_setelahnya(
    sambungan: sqlite3.Connection,
) -> None:
    """Aturan keras 3 (PRD 9.9): snapshot dihitung dengan yang **sudah diketahui saat itu**.

    Bentuk nyatanya adalah koreksi data. Snapshot pertama (1 Okt 2026) mencatat penutupan
    30 Sep 2026 sebesar 1.000. Sebulan kemudian data yang sama diperbaiki menjadi 1.111 dan
    baris 31 Okt 2026 ditambahkan. Revisi itu benar untuk snapshot terbaru, tetapi **belum ada**
    saat snapshot pertama dibuat.

    Uji ini sengaja membandingkan tiga hal:

    * `potret.muat(id_snapshot=1)` → 1.000 (keadaan saat itu, hanya satu baris);
    * `potret.muat()` → 1.111 dan 1.200 (snapshot terakhir);
    * `v_harga_harian_terkini` → 1.111 juga, dan itulah buktinya: tampilan "terkini" memang
      menyajikan keadaan hari ini. Memakai tampilan itu untuk snapshot lama berarti menghitung
      dengan angka yang belum diketahui saat snapshot dibuat — persis yang dilarang aturan ini.
    """
    pertama = _simpan(
        sambungan,
        tanggal_data=date(2026, 9, 30),
        emiten=(_emiten("AAAA"),),
        harga_harian=(
            HargaHarian(kode="AAAA", tanggal=date(2026, 9, 30), close=1_000, volume=1_000),
        ),
    )
    _simpan(
        sambungan,
        tanggal_data=date(2026, 10, 31),
        momen=MOMEN_LANJUT,
        harga_harian=(
            HargaHarian(kode="AAAA", tanggal=date(2026, 9, 30), close=1_111, volume=1_000),
            HargaHarian(kode="AAAA", tanggal=date(2026, 10, 31), close=1_200, volume=1_000),
        ),
    )

    lama = potret.muat(sambungan, id_snapshot=pertama)
    terbaru = potret.muat(sambungan)

    assert lama.id_snapshot == pertama
    assert lama.tanggal_data == date(2026, 9, 30)
    assert lama.batas_diketahui == MOMEN.isoformat(), "batas waktu snapshot ikut tersimpan"
    assert [(satu.tanggal, satu.close) for satu in lama.harga["AAAA"]] == [
        (date(2026, 9, 30), 1_000)
    ], "revisi yang diketahui setelah snapshot tidak boleh terlihat oleh snapshot lama"
    assert metrik.harga_terakhir(metrik.seri_harga(lama, "AAAA")).nilai == pytest.approx(
        1_000.0
    ), "metrik harga snapshot lama harus memakai angka yang diketahui saat itu"

    assert [(satu.tanggal, satu.close) for satu in terbaru.harga["AAAA"]] == [
        (date(2026, 9, 30), 1_111),
        (date(2026, 10, 31), 1_200),
    ], "snapshot terbaru memakai revisi terakhir"

    terkini = sambungan.execute(
        "SELECT tanggal, close FROM v_harga_harian_terkini ORDER BY tanggal"
    ).fetchall()
    assert [(satu["tanggal"], satu["close"]) for satu in terkini] == [
        ("2026-09-30", 1_111),
        ("2026-10-31", 1_200),
    ], "tampilan terkini memang menyajikan keadaan hari ini — karena itu ia tidak dipakai potret"


def test_snapshot_yang_diminta_tidak_ada_ditolak_berisik(sambungan: sqlite3.Connection) -> None:
    """Memuat snapshot yang tidak ada tidak boleh diam-diam jatuh ke snapshot lain.

    Kalau `id_snapshot` yang salah dibiarkan berarti "pakai yang terakhir", hasil saringan untuk
    tanggal tertentu bisa berisi data tanggal lain tanpa satu pun tanda — dan itu jenis kesalahan
    yang paling sulit ditelusuri belakangan.
    """
    _simpan(sambungan, emiten=(_emiten("AAAA"),))

    with pytest.raises(GalatIngesti, match="tidak ada"):
        potret.muat(sambungan, id_snapshot=99)


def test_memuat_potret_tanpa_snapshot_sama_sekali_menyebut_jalan_keluarnya(
    sambungan: sqlite3.Connection,
) -> None:
    """Basis data yang baru dibuat belum punya snapshot; pesannya harus menolong (aturan keras 7).

    "Belum ada snapshot" bukan kegagalan yang bisa ditebak pengguna dari layar kosong: yang
    menolong adalah menyebut perintah yang harus dijalankan lebih dulu.
    """
    with pytest.raises(GalatIngesti, match="--refresh"):
        potret.muat(sambungan)
