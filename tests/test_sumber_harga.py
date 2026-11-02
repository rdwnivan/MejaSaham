"""Uji aturan **satu label sumber harga per snapshot** (P17) — `mejasaham/potret.py`.

Sejak migrasi 005 harga pembanding untuk cek sumber kedua (PRD 7.3) hidup di **tabel yang sama**
dengan harga utama, dan itu memang yang membuat perbandingan dua sumber mungkin. Sampingannya
baru terukur 9 Okt 2026 (Tahap 1 langkah 6): pembacaan untuk perhitungan belum menyaring
labelnya, sehingga dua bar tanggal sama dari dua sumber masuk ke satu deret, hari yang
terduplikasi memakan satu slot jendela 20 hari, dan ADTV20 emiten itu jatuh menjadi "tidak
dihitung". Terukur pada salinan basis data uji 916 emiten: **semesta likuid 235 → 215**, tepat
pada 20 emiten yang diberi pembanding — dan yang hilang justru emiten paling likuid.

Yang diuji di sini bukan "kuerinya kebetulan menyaring", melainkan janji-janji yang membuat angka
saringan tetap sah ketika harga pembanding ada:

* **Angka saring tidak berubah** sesudah harga pembanding diimpor — uji regresi yang diminta
  `docs/lanjutan.md` bagian 4: likuid, ADTV20 per emiten, dan peringkat ADTV20 yang dipakai
  sebagai daftar kritis PRD 9.3. Dua bentuk akibatnya diuji terpisah, sebab keduanya berbeda
  cara menyakitinya: pembanding **tanpa** volume membuat ADTV20 jatuh "tidak dihitung" (bentuk
  kejadian nyata), sedangkan pembanding **dengan** volume membuat angkanya naik diam-diam.
* **Satu snapshot, satu label** (A5): label dengan riwayat bar terbanyak, seri diputus menurut
  abjad, dan pilihannya ikut **point-in-time** — label yang baru muncul belakangan tidak boleh
  mengubah isi snapshot lama.
* **Label yang tidak dipakai tidak hilang**: ia tetap terlihat di laporan, sebab "pembanding
  sudah diimpor" dan "pembanding tidak ada" menuntut tindakan yang berbeda (PRD 7.3) — dan
  label yang dipakai disebut namanya, bukan disimpulkan pengguna dari angka.
* **Label yang salah ditolak berisik**, bukan menghasilkan potret tanpa harga (aturan keras 7).

Seluruh data uji ditulis lewat jalur nyata (`ingesti.simpan` → `potret.muat`), bukan dengan
menyusun objek di memori. Semestanya kecil dan angkanya bulat supaya bisa diperiksa tangan:
sepuluh emiten satu sektor, ADTV20 Rp 10 miliar (di atas ambang K9 Rp 5 miliar).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import cli, db, ingesti, lokasi, metrik, mutu, pengatur, potret, saring
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    GalatIngesti,
    HargaHarian,
    KumpulanData,
)

#: Dua label sumber. Namanya sengaja menyerupai pemakaian nyata: satu label utama (harga EOD
#: harian) dan satu label pembanding yang hanya diimpor beberapa baris (PRD 7.3).
UTAMA = "uji-utama"
PEMBANDING = "uji-pembanding"

TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
#: Momen kedua yang **berbeda detik** dari `MOMEN`: `diketahui_pada` berketelitian detik, jadi
#: dua penulisan dalam detik yang sama akan bertabrakan di kunci utama dan yang kedua tidak
#: ditulis — revisinya tidak akan pernah ada untuk diuji.
MOMEN_LANJUT = datetime(2026, 7, 2, 9, 0, 0)

SEKTOR = "industri"
CLOSE = 1_000
#: Harga 1.000 x volume 10.000.000 = Rp 10 miliar ADTV20 — angka bulat, jauh di atas ambang.
VOLUME_LIKUID = 10_000_000
HARI = 20
KODE = ("AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF", "GGGG", "HHHH", "IIII", "JJJJ")

SUMBER_EMITEN = "uji-rujukan"


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


def _emiten(kode: str) -> Emiten:
    return Emiten(kode=kode, nama=f"Emiten {kode}", sektor_idx_ic=SEKTOR, sumber=SUMBER_EMITEN)


def _deret(kode: str, *, hari: int = HARI) -> tuple[HargaHarian, ...]:
    """Deret harga utama: `hari` hari bursa terakhir, semuanya berpenanda "tidak disesuaikan"."""
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=hari - 1 - i),
            close=CLOSE,
            volume=VOLUME_LIKUID,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(hari)
    )


def _simpan(
    sambungan: sqlite3.Connection,
    *,
    sumber: str,
    tanggal_data: date = TANGGAL,
    momen: datetime = MOMEN,
    **isi: object,
) -> int:
    """Tulis satu snapshot lewat jalur nyata dan kembalikan `id_snapshot`-nya."""
    kumpulan = KumpulanData(sumber=sumber, **isi)  # type: ignore[arg-type]
    return ingesti.simpan(
        sambungan, kumpulan, tanggal_data=tanggal_data, momen=momen
    ).id_snapshot


def _semesta_utama(sambungan: sqlite3.Connection) -> None:
    """Sepuluh emiten likuid dengan 20 hari harga dari label `UTAMA`."""
    _simpan(
        sambungan,
        sumber=UTAMA,
        emiten=tuple(_emiten(kode) for kode in KODE),
        harga_harian=tuple(bar for kode in KODE for bar in _deret(kode)),
    )


def _impor_pembanding(
    sambungan: sqlite3.Connection, *, volume: int | None = None
) -> None:
    """Impor **satu** bar pembanding per emiten pada hari terakhir — bentuk kejadian nyata.

    Bentuk inilah yang terukur 9 Okt 2026: 20 baris pembanding (satu per emiten ber-ADTV20
    tertinggi) masuk ke basis data yang sudah berisi 999.421 bar harga utama. `volume=None`
    meniru berkas pembanding yang hanya memuat penutupan.
    """
    _simpan(
        sambungan,
        sumber=PEMBANDING,
        momen=MOMEN_LANJUT,
        harga_harian=tuple(
            HargaHarian(
                kode=kode,
                tanggal=TANGGAL,
                close=CLOSE,
                volume=volume,
                penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
            )
            for kode in KODE
        ),
    )


def _saring(sambungan: sqlite3.Connection, **ubah: object) -> pengatur.LaporanSaring:
    pengatur.siapkan_preset_bawaan(sambungan, TANGGAL)
    preset = saring.preset_terbaru(sambungan, "kualitas-nilai")
    return pengatur.jalankan_saring(sambungan, preset, **ubah)  # type: ignore[arg-type]


def _adtv(sambungan: sqlite3.Connection) -> dict[str, float | None]:
    bahan = potret.muat(sambungan)
    return {kode: metrik.adtv20(metrik.seri_harga(bahan, kode)).nilai for kode in KODE}


# ---------------------------------------------------------------------------------------
# Uji regresi: harga pembanding tidak ikut berhitung
# ---------------------------------------------------------------------------------------


def test_adtv20_tidak_jatuh_tidak_dihitung_sesudah_pembanding_tanpa_volume_diimpor(
    sambungan: sqlite3.Connection,
) -> None:
    """Bentuk kejadian nyata 9 Okt 2026: pembanding hanya memuat penutupan, tanpa volume.

    Sebelum diperbaiki, bar pembanding itu masuk ke deret yang sama, `nilai` transaksinya NULL,
    dan jendela 20 bar terakhir berisi 19 hari yang punya nilai — sehingga ADTV20 sepuluh emiten
    paling likuid berubah menjadi "tidak dihitung" dan semesta likuid menyusut. Yang diuji di
    sini: sesudah pembanding diimpor, keadaannya **sama** dengan sebelumnya, dan deret harganya
    benar-benar berisi 20 bar (bukan 21).
    """
    _semesta_utama(sambungan)
    sebelum = _saring(sambungan)
    adtv_sebelum = _adtv(sambungan)

    _impor_pembanding(sambungan, volume=None)

    sesudah = _saring(sambungan)
    adtv_sesudah = _adtv(sambungan)

    assert sebelum.jumlah_likuid == len(KODE), "seluruh sepuluh emiten likuid sejak awal"
    assert sesudah.jumlah_likuid == sebelum.jumlah_likuid, (
        "semesta likuid tidak boleh berubah hanya karena harga pembanding diimpor"
    )
    assert adtv_sesudah == adtv_sebelum, "ADTV20 tiap emiten harus sama persis"
    assert set(adtv_sesudah.values()) == {float(CLOSE * VOLUME_LIKUID)}
    assert potret.muat(sambungan).sumber_harga == UTAMA
    assert len(potret.muat(sambungan).harga["AAAA"]) == HARI, (
        "deret harga hanya boleh memuat bar satu label; 21 berarti bar pembanding ikut masuk"
    )


def test_adtv20_tidak_naik_diam_diam_sesudah_pembanding_bervolume_diimpor(
    sambungan: sqlite3.Connection,
) -> None:
    """Bentuk kedua: pembanding ikut memuat volume, sehingga angkanya **naik** tanpa suara.

    Hari yang terduplikasi dihitung sebagai hari tersendiri: jendela 20 bar terakhir berisi 19
    hari utama ditambah satu bar pembanding pada hari yang sama, sehingga ADTV20 menjadi
    (19 x Rp 10 miliar + Rp 20 miliar) / 20 = **Rp 10,5 miliar** — terukur, bukan dikira-kira.
    Bedanya 5% dan tidak satu pun pesan muncul: inilah jenis kesalahan yang paling mahal, sebab
    hasilnya terlihat wajar. Karena itu yang dituntut di sini bukan "tidak error", melainkan
    angkanya **sama persis** dengan sebelum pembanding diimpor.
    """
    _semesta_utama(sambungan)
    adtv_sebelum = _adtv(sambungan)

    _impor_pembanding(sambungan, volume=VOLUME_LIKUID * 2)

    assert _adtv(sambungan) == adtv_sebelum
    assert set(_adtv(sambungan).values()) == {float(CLOSE * VOLUME_LIKUID)}


def test_peringkat_adtv_yang_jadi_daftar_kritis_tidak_berubah_sesudah_pembanding_diimpor(
    sambungan: sqlite3.Connection,
) -> None:
    """PRD 9.3 memakai 50 emiten ber-ADTV20 tertinggi sebagai daftar kritis; ia satu label juga.

    Tanpa penyaringan label, himpunan "20 hari bursa terakhir" menjadi gabungan dua sumber,
    sehingga emiten yang datanya cuma ada di salah satu sumber bisa muncul sebagai emiten
    teratas hari ini. Yang diperiksa di sini adalah panggilan yang benar-benar dipakai
    `pengatur.jalankan_refresh`: peringkat dari label yang sama dengan yang dipakai berhitung.
    """
    _semesta_utama(sambungan)
    label = potret.sumber_utama(sambungan)
    sebelum = mutu.peringkat_adtv(sambungan, sumber=label)

    _impor_pembanding(sambungan, volume=VOLUME_LIKUID * 2)

    sesudah = mutu.peringkat_adtv(sambungan, sumber=potret.sumber_utama(sambungan))

    assert label == UTAMA
    assert sesudah == sebelum, "peringkat ADTV20 harus sama persis, bukan hanya sama panjangnya"
    assert {satu.kode for satu in sesudah} == set(KODE)


# ---------------------------------------------------------------------------------------
# Aturan pemilihan label (P17)
# ---------------------------------------------------------------------------------------


def test_satu_snapshot_satu_label_sumber_terbanyak(sambungan: sqlite3.Connection) -> None:
    """Label dengan riwayat bar terbanyak yang dipakai, dan label lain tetap terlihat.

    Dua label dengan penutupan yang **berbeda jauh** (1.000 vs 2.000) membuat pilihannya bisa
    diperiksa dari angkanya, bukan dari nama labelnya saja: kalau label yang salah terpakai,
    penutupannya ikut salah.
    """
    _simpan(
        sambungan,
        sumber="aaa",
        emiten=(_emiten("AAAA"),),
        harga_harian=_deret("AAAA"),
    )
    _simpan(
        sambungan,
        sumber="bbb",
        momen=MOMEN_LANJUT,
        harga_harian=tuple(
            HargaHarian(
                kode="AAAA",
                tanggal=bar.tanggal,
                close=2_000,
                volume=VOLUME_LIKUID,
                penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
            )
            for bar in _deret("AAAA")
        ),
    )

    bahan = potret.muat(sambungan)

    assert bahan.sumber_harga == "aaa", "seri jumlah bar diputus menurut abjad, bukan urutan baris"
    assert {float(satu.close) for satu in bahan.harga["AAAA"]} == {float(CLOSE)}
    assert bahan.bar_sumber_harga == HARI
    assert bahan.sumber_diabaikan == (("bbb", HARI),), (
        "label yang tidak dipakai harus tetap terlihat beserta jumlah barnya"
    )


def test_pilihan_label_ikut_point_in_time(sambungan: sqlite3.Connection) -> None:
    """Label yang baru muncul belakangan tidak boleh mengubah isi snapshot lama (aturan keras 3).

    Snapshot pertama hanya mengenal label `utama`. Sesudahnya label `pembanding` diimpor dengan
    bar yang **lebih banyak**, sehingga ia menjadi label terbesar **hari ini**. Snapshot lama
    tetap harus dibaca dengan label yang dikenal saat itu — kalau tidak, isi snapshot lama
    berubah sendiri tanpa satu pun barisnya ditulis ulang.
    """
    _semesta_utama(sambungan)
    pertama = potret.muat(sambungan)
    assert pertama.sumber_harga == UTAMA

    banyak = tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=HARI + i),
            close=CLOSE,
            volume=VOLUME_LIKUID,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for kode in KODE
        for i in range(30)
    )
    _simpan(sambungan, sumber=PEMBANDING, momen=MOMEN_LANJUT, harga_harian=banyak)

    lama = potret.muat(sambungan, pertama.id_snapshot)
    terbaru = potret.muat(sambungan)

    assert potret.sumber_utama(sambungan) == PEMBANDING, "hari ini label pembanding yang terbesar"
    assert lama.sumber_harga == UTAMA, "snapshot lama tetap dibaca dengan label saat itu"
    assert len(lama.harga["AAAA"]) == HARI
    assert terbaru.sumber_harga == PEMBANDING
    assert len(terbaru.harga["AAAA"]) == 30


def test_sumber_yang_diminta_tidak_ada_ditolak_berisik(sambungan: sqlite3.Connection) -> None:
    """Nama label yang salah adalah kekeliruan pengguna, bukan alasan menghitung tanpa harga.

    Kalau label yang tidak ada dibiarkan berarti "tidak ada bar", saringan akan melaporkan
    "0 kandidat" — gejala yang sama dengan "fundamental belum diimpor", padahal sebabnya
    berbeda. Pesannya harus menyebut label yang benar-benar ada (aturan keras 7).
    """
    _semesta_utama(sambungan)

    with pytest.raises(GalatIngesti) as galat:
        potret.muat(sambungan, sumber="yfinance")

    assert "yfinance" in str(galat.value)
    assert UTAMA in str(galat.value), "pesannya harus menyebut label yang ada"


def test_saring_menghormati_sumber_penimpa_dan_melaporkannya(
    sambungan: sqlite3.Connection,
) -> None:
    """`--sumber` menimpa pilihan bawaan, dan akibatnya terlihat — bukan disembunyikan.

    Yang dipakai di sini adalah label pembanding yang hanya punya satu bar per emiten: ADTV20-nya
    memang belum bisa dihitung, jadi tidak ada emiten likuid. Itu **jawaban yang benar** untuk
    pertanyaan itu, dan justru itulah gunanya menimpa: pengguna bisa memeriksa apa yang terjadi
    bila label lain yang dipakai, alih-alih menebak dari angka.
    """
    _semesta_utama(sambungan)
    _impor_pembanding(sambungan, volume=VOLUME_LIKUID)

    bawaan = _saring(sambungan)
    ditimpa = _saring(sambungan, sumber=PEMBANDING)

    assert bawaan.sumber_harga == UTAMA
    assert ditimpa.sumber_harga == PEMBANDING
    assert bawaan.jumlah_likuid == len(KODE)
    assert ditimpa.jumlah_likuid == 0, "satu hari bar belum cukup untuk ADTV20"
    assert UTAMA in ditimpa.sumber_ringkas()


def test_laporan_saring_menyebut_label_yang_dipakai_dan_yang_diabaikan(
    sambungan: sqlite3.Connection,
) -> None:
    """Angka di layar berasal dari satu sumber; sumber mana itu harus terbaca dari laporannya.

    Peringatannya sengaja ada: dua label di basis data berarti ada harga pembanding yang bisa
    diperiksa (PRD 7.3), dan keadaan itu tidak boleh tampak sama dengan basis data yang hanya
    punya satu sumber.
    """
    _semesta_utama(sambungan)
    _impor_pembanding(sambungan, volume=None)

    laporan = _saring(sambungan)

    assert laporan.sumber_tersedia == ((UTAMA, HARI * len(KODE)), (PEMBANDING, len(KODE)))
    assert f"harga dari sumber {UTAMA!r}" in laporan.sumber_ringkas()
    assert PEMBANDING in laporan.sumber_ringkas()
    assert any(PEMBANDING in satu for satu in laporan.peringatan), (
        "label yang tidak dipakai berhitung harus muncul sebagai peringatan, bukan hilang"
    )
    assert "200" in laporan.sumber_ringkas(), "jumlah bar ditulis format Indonesia (titik ribuan)"


def test_mode_kepala_menerima_sumber_penimpa(
    folder_data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--saring --sumber` sampai ke perhitungan, dan labelnya tercetak di keluaran perintah."""
    sambungan = db.siapkan()
    try:
        _semesta_utama(sambungan)
        _impor_pembanding(sambungan, volume=VOLUME_LIKUID)
    finally:
        sambungan.close()

    kode = cli.main(["--saring", "--sumber", PEMBANDING])

    assert kode == cli.KODE_OK
    keluaran = capsys.readouterr().out
    assert f"harga dari sumber {PEMBANDING!r}" in keluaran
    assert UTAMA in keluaran, "label yang tidak dipakai tetap disebut"
