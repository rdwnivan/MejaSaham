"""Uji deret sambungan harga resmi (K97 langkah 2, P42) — `potret.harga_dipakai` dan pemakainya.

Janji yang diuji:

* **Satu tanggal sambung untuk seluruh emiten** (K97 a): sebelum tanggal itu bar dari label
  riwayat, sejak tanggal itu dari label resmi. Bar label riwayat sesudah tanggal sambung dan bar
  label resmi sebelum tanggal sambung **tidak** ikut, sehingga tidak ada tanggal yang terduplikasi.
* **Point-in-time**: snapshot yang dibuat sebelum pernyataan sambungan tetap membaca satu label.
* **Pencabutan** (`aktif = tidak`) mengembalikan pilihan K14.
* **`--sumber` menimpa** seluruh pilihan, termasuk sambungan.
* **Satu pemilik**: harga terakhir posisi, peringkat ADTV20 laporan mutu, dan cek sumber kedua
  membaca deret yang sama dengan perhitungan skor.
* **Label tetap terlihat per bagian** (K97 e): label gabungan menyebut keduanya, laporan mutu
  tetap menandai riwayat yfinance tidak resmi.
* **Berkas impor** `sambungan-harga.csv`: satu pernyataan per impor, `aktif` hanya ya/tidak.

Data ditulis lewat jalur nyata (`ingesti.simpan` dan `berkas.baca_folder`).
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import berkas, dasbor, db, ingesti, lokasi, metrik, mutu, pengatur, posisi, potret
from mejasaham.ingesti import (
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    GalatIngesti,
    HargaHarian,
    KumpulanData,
    SambunganHarga,
)
from mejasaham.pengambil import SUMBER_YFINANCE
from mejasaham.unggahan_idx import SUMBER_IDX

#: Tanggal sambung: 10 hari pertama dari yfinance, 10 hari terakhir dari IDX.
AWAL = date(2026, 6, 1)
HARI = 20
SEJAK = AWAL + timedelta(days=10)
AKHIR = AWAL + timedelta(days=HARI - 1)

MOMEN_RIWAYAT = datetime(2026, 6, 25, 18, 0, 0)
MOMEN_SAMBUNG = datetime(2026, 6, 26, 9, 0, 0)
MOMEN_IDX = datetime(2026, 6, 26, 18, 0, 0)

KODE = ("AAAA", "BBBB")
#: Harga yfinance dan IDX sengaja berbeda supaya terlihat bar mana yang terbaca.
CLOSE_YF = 1_000
CLOSE_IDX = 1_100
VOLUME = 10_000_000


@pytest.fixture()
def sambungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _bar(kode: str, tanggal: date, close: int, penanda: str) -> HargaHarian:
    return HargaHarian(
        kode=kode, tanggal=tanggal, close=close, volume=VOLUME, penyesuaian_sumber=penanda
    )


def _riwayat_yfinance(sambungan: sqlite3.Connection) -> int:
    """Seluruh 20 hari dari yfinance — termasuk hari sesudah tanggal sambung."""
    return ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_YFINANCE,
            emiten=tuple(Emiten(kode=k, nama=k, sektor_idx_ic="industri", sumber="uji") for k in KODE),
            harga_harian=tuple(
                _bar(k, AWAL + timedelta(days=i), CLOSE_YF, PENYESUAIAN_SPLIT)
                for k in KODE
                for i in range(HARI)
            ),
        ),
        tanggal_data=AKHIR,
        momen=MOMEN_RIWAYAT,
    ).id_snapshot


def _harga_idx(sambungan: sqlite3.Connection, *, sejak_hari: int = 5) -> int:
    """Bar IDX mulai hari ke-`sejak_hari` — sebagian **sebelum** tanggal sambung (pembanding).

    Sebelum tanggal sambung penutupannya sama dengan yfinance, supaya gerbang sambungan (K97 b)
    lolos; sesudahnya sengaja berbeda supaya terlihat bar mana yang terbaca.
    """

    def close(i: int) -> int:
        return CLOSE_YF if AWAL + timedelta(days=i) < SEJAK else CLOSE_IDX

    return ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER_IDX,
            harga_harian=tuple(
                _bar(k, AWAL + timedelta(days=i), close(i), PENYESUAIAN_TIDAK_DISESUAIKAN)
                for k in KODE
                for i in range(sejak_hari, HARI)
            ),
        ),
        tanggal_data=AKHIR,
        momen=MOMEN_IDX,
    ).id_snapshot


def _nyatakan(
    sambungan: sqlite3.Connection, *, aktif: bool = True, momen: datetime = MOMEN_SAMBUNG
) -> int:
    return ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber="impor berkas: uji",
            sambungan_harga=(
                SambunganHarga(
                    berlaku_sejak=SEJAK, sumber_resmi=SUMBER_IDX, aktif=aktif, sumber="K97 uji"
                ),
            ),
        ),
        tanggal_data=AKHIR,
        momen=momen,
        proses=ingesti.PROSES_IMPOR,
    ).id_snapshot


def _tersambung(sambungan: sqlite3.Connection) -> None:
    _riwayat_yfinance(sambungan)
    _nyatakan(sambungan)
    _harga_idx(sambungan)


# ---------------------------------------------------------------------------------------
# Deret yang dimuat
# ---------------------------------------------------------------------------------------


def test_deret_sambungan_memakai_riwayat_sebelum_dan_resmi_sejak_tanggal_sambung(
    sambungan: sqlite3.Connection,
) -> None:
    _tersambung(sambungan)

    bahan = potret.muat(sambungan)

    for kode in KODE:
        deret = bahan.harga[kode]
        assert [bar.tanggal for bar in deret] == [AWAL + timedelta(days=i) for i in range(HARI)], (
            "satu bar per hari: tidak ada tanggal yang terduplikasi dari dua label"
        )
        assert {bar.close for bar in deret if bar.tanggal < SEJAK} == {CLOSE_YF}
        assert {bar.close for bar in deret if bar.tanggal >= SEJAK} == {CLOSE_IDX}
    assert bahan.pilihan_harga == potret.PilihanHarga(
        dasar=SUMBER_YFINANCE, resmi=SUMBER_IDX, sejak=SEJAK
    )


def test_label_gabungan_menyebut_kedua_sumber_dan_jumlah_bar_tiap_bagian(
    sambungan: sqlite3.Connection,
) -> None:
    _tersambung(sambungan)

    bahan = potret.muat(sambungan)

    assert bahan.sumber_harga == f"{SUMBER_IDX} sejak {SEJAK.isoformat()}; sebelumnya {SUMBER_YFINANCE}"
    assert bahan.bar_per_label == ((SUMBER_YFINANCE, 20), (SUMBER_IDX, 20))
    assert bahan.sumber_diabaikan == (), "kedua label dipakai; tidak ada yang diabaikan"


def test_adtv20_dihitung_utuh_pada_deret_sambungan(sambungan: sqlite3.Connection) -> None:
    """Hari yang terduplikasi akan memakan slot jendela 20 hari dan menjatuhkan ADTV20 (P17)."""
    _tersambung(sambungan)

    bahan = potret.muat(sambungan)

    assert metrik.adtv20(metrik.seri_harga(bahan, "AAAA")).nilai is not None


def test_snapshot_sebelum_pernyataan_sambungan_tetap_satu_label(
    sambungan: sqlite3.Connection,
) -> None:
    lama = _riwayat_yfinance(sambungan)
    _nyatakan(sambungan)
    _harga_idx(sambungan)

    bahan = potret.muat(sambungan, lama)

    assert bahan.sumber_harga == SUMBER_YFINANCE
    assert {bar.close for bar in bahan.harga["AAAA"]} == {CLOSE_YF}


def test_pernyataan_tidak_aktif_mencabut_sambungan(sambungan: sqlite3.Connection) -> None:
    _tersambung(sambungan)
    _nyatakan(sambungan, aktif=False, momen=datetime(2026, 6, 27, 9, 0, 0))

    bahan = potret.muat(sambungan)

    assert bahan.sumber_harga == SUMBER_YFINANCE
    assert {bar.close for bar in bahan.harga["AAAA"]} == {CLOSE_YF}


def test_sumber_eksplisit_menimpa_sambungan(sambungan: sqlite3.Connection) -> None:
    _tersambung(sambungan)

    bahan = potret.muat(sambungan, sumber=SUMBER_YFINANCE)

    assert bahan.sumber_harga == SUMBER_YFINANCE
    assert {bar.close for bar in bahan.harga["AAAA"]} == {CLOSE_YF}


def test_pilihan_sambungan_utuh_diterima_sebagai_sumber(sambungan: sqlite3.Connection) -> None:
    _tersambung(sambungan)
    pilihan = potret.harga_dipakai(sambungan)
    assert pilihan is not None and pilihan.tersambung

    bahan = potret.muat(sambungan, sumber=pilihan)

    assert bahan.pilihan_harga == pilihan
    assert {bar.close for bar in bahan.harga["AAAA"] if bar.tanggal >= SEJAK} == {CLOSE_IDX}


def test_pilihan_sambungan_dengan_label_tanpa_bar_ditolak(sambungan: sqlite3.Connection) -> None:
    _riwayat_yfinance(sambungan)
    pilihan = potret.PilihanHarga(dasar=SUMBER_YFINANCE, resmi=SUMBER_IDX, sejak=SEJAK)

    with pytest.raises(GalatIngesti, match=re.escape(f"sumber harga {SUMBER_IDX!r} tidak punya satu bar")):
        potret.muat(sambungan, sumber=pilihan)


def test_dasbor_jalan_pada_deret_sambungan_tanpa_konteks_tersimpan(
    sambungan: sqlite3.Connection,
) -> None:
    """Regresi 29 Okt 2026: dasbor mengirim label gabungan (teks tampilan) ke `potret.muat`
    sebagai label bar dan gagal setiap kali `--saring` belum menyimpan konteks pasar."""
    _tersambung(sambungan)

    papan = dasbor.susun(sambungan, hari_ini=AKHIR)

    assert papan.sumber_harga == potret.harga_dipakai(sambungan).label


def test_tanpa_pernyataan_pilihan_tetap_label_terbanyak(sambungan: sqlite3.Connection) -> None:
    _riwayat_yfinance(sambungan)
    _harga_idx(sambungan)

    assert potret.harga_dipakai(sambungan) == potret.PilihanHarga(dasar=SUMBER_YFINANCE)


# ---------------------------------------------------------------------------------------
# Pemakai lain membaca deret yang sama
# ---------------------------------------------------------------------------------------


def test_harga_terakhir_posisi_datang_dari_label_resmi(sambungan: sqlite3.Connection) -> None:
    """Stop dan ukuran posisi memakai harga terakhir; ia harus sama dengan deret skor."""
    _tersambung(sambungan)

    terakhir = posisi.harga_terakhir(sambungan, ["AAAA"])["AAAA"]

    assert (terakhir.tanggal, terakhir.close, terakhir.sumber) == (AKHIR, CLOSE_IDX, SUMBER_IDX)


def test_peringkat_adtv_laporan_mutu_tidak_menghitung_hari_dua_kali(
    sambungan: sqlite3.Connection,
) -> None:
    _tersambung(sambungan)

    peringkat = mutu.peringkat_adtv(sambungan, sumber=potret.harga_dipakai(sambungan))

    assert {satu.kode for satu in peringkat} == set(KODE)
    assert {satu.hari_terpakai for satu in peringkat} == {metrik.ADTV_PERIODE}


def test_laporan_mutu_tetap_menandai_riwayat_tidak_resmi(sambungan: sqlite3.Connection) -> None:
    _tersambung(sambungan)

    laporan = mutu.periksa(
        sambungan, tanggal_data=AKHIR, sumber=potret.harga_dipakai(sambungan), momen=AKHIR
    )

    catatan = [satu for satu in laporan.temuan if satu.jenis == "sumber_tidak_resmi"]
    assert len(catatan) == 1
    assert f"sebelum {SEJAK.isoformat()}" in catatan[0].keterangan
    assert SUMBER_IDX in catatan[0].keterangan


def test_cek_sumber_kedua_membalik_utama_dan_pembanding(sambungan: sqlite3.Connection) -> None:
    """K97 f: sejak tanggal sambung, label resmi yang utama dan yfinance yang membandingkan."""
    _tersambung(sambungan)

    laporan = pengatur.cek_sumber_kedua(sambungan, momen=datetime(2026, 6, 27, 9, 0, 0))

    assert laporan.sumber_utama == SUMBER_IDX
    assert laporan.sumber_pembanding == SUMBER_YFINANCE
    assert laporan.belum_dapat_dijalankan == [], (
        "peringkat ADTV20 dihitung dari deret sambungan, bukan dari label resmi saja"
    )
    assert {satu.kode for satu in laporan.diperiksa} == set(KODE)


# ---------------------------------------------------------------------------------------
# Berkas impor sambungan-harga.csv
# ---------------------------------------------------------------------------------------


def _tulis_berkas(folder: Path, *baris: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "sambungan-harga.csv").write_text(
        "berlaku_sejak;sumber_resmi;aktif;keterangan;sumber\n" + "\n".join(baris) + "\n",
        encoding="utf-8-sig",
    )
    return folder


def test_berkas_sambungan_dibaca_menjadi_satu_pernyataan(tmp_path: Path) -> None:
    folder = _tulis_berkas(
        tmp_path / "impor", f"2026-06-11;{SUMBER_IDX};ya;mulai harian;K97 keputusan pengguna"
    )

    hasil = berkas.baca_folder(folder)

    assert hasil.kumpulan.sambungan_harga == (
        SambunganHarga(
            berlaku_sejak=SEJAK,
            sumber_resmi=SUMBER_IDX,
            aktif=True,
            sumber="K97 keputusan pengguna",
            keterangan="mulai harian",
        ),
    )


def test_berkas_dua_isi_berbeda_untuk_tanggal_sama_ditolak(tmp_path: Path) -> None:
    folder = _tulis_berkas(
        tmp_path / "impor",
        f"2026-06-11;{SUMBER_IDX};ya;;K97",
        f"2026-06-11;{SUMBER_IDX};tidak;;K97",
    )

    with pytest.raises(GalatIngesti, match="berlaku_sejak"):
        berkas.baca_folder(folder)


def test_satu_berkas_bisa_mencabut_tanggal_lama_dan_menyatakan_yang_baru(
    sambungan: sqlite3.Connection, tmp_path: Path
) -> None:
    """Memajukan tanggal sambung ke tanggal yang lebih awal = cabut yang lama + nyatakan yang baru."""
    _tersambung(sambungan)
    lebih_awal = SEJAK - timedelta(days=3)
    folder = _tulis_berkas(
        tmp_path / "impor",
        f"{SEJAK.isoformat()};{SUMBER_IDX};tidak;dimajukan;K97",
        f"{lebih_awal.isoformat()};{SUMBER_IDX};ya;dimajukan;K97",
    )
    ingesti.simpan(
        sambungan,
        berkas.baca_folder(folder).kumpulan,
        tanggal_data=AKHIR,
        momen=datetime(2026, 6, 27, 9, 0, 0),
        proses=ingesti.PROSES_IMPOR,
    )

    assert potret.harga_dipakai(sambungan) == potret.PilihanHarga(
        dasar=SUMBER_YFINANCE, resmi=SUMBER_IDX, sejak=lebih_awal
    )


def test_berkas_aktif_yang_bukan_ya_tidak_ditolak(tmp_path: Path) -> None:
    folder = _tulis_berkas(tmp_path / "impor", f"2026-06-11;{SUMBER_IDX};mungkin;;K97")

    with pytest.raises(GalatIngesti, match="aktif"):
        berkas.baca_folder(folder)


def test_pernyataan_yang_sama_diimpor_ulang_tidak_menambah_baris(
    sambungan: sqlite3.Connection,
) -> None:
    _nyatakan(sambungan)
    _nyatakan(sambungan, momen=datetime(2026, 6, 27, 9, 0, 0))

    jumlah = sambungan.execute("SELECT COUNT(*) FROM sambungan_harga").fetchone()[0]

    assert jumlah == 1


def test_pembanding_yang_sama_dengan_sumber_utama_tidak_dianggap_lulus(
    sambungan: sqlite3.Connection,
) -> None:
    """Sejak tanggal sambung, IDX adalah utama; memaksanya sebagai pembanding = memeriksa diri sendiri."""
    _tersambung(sambungan)

    laporan = pengatur.cek_sumber_kedua(
        sambungan, sumber_pembanding=SUMBER_IDX, momen=datetime(2026, 6, 27, 9, 0, 0)
    )

    assert laporan.diperiksa == ()
    assert any("dirinya sendiri" in satu for satu in laporan.belum_dapat_dijalankan)


def test_unggahan_idx_sesudah_tanggal_sambung_dibandingkan_dengan_label_riwayat(
    sambungan: sqlite3.Connection,
) -> None:
    from mejasaham.layar import tulis

    _riwayat_yfinance(sambungan)
    _nyatakan(sambungan)
    _harga_idx(sambungan)
    pilihan = potret.harga_dipakai(sambungan)

    assert pilihan is not None and pilihan.label_pada(AKHIR) == SUMBER_IDX
    assert "UTAMA" in tulis.peran_unggahan_idx(pilihan, AKHIR)
    assert "PEMBANDING" in tulis.peran_unggahan_idx(potret.PilihanHarga(dasar=SUMBER_YFINANCE), AKHIR)


# ---------------------------------------------------------------------------------------
# Laporan mutu sesudah --refresh
# ---------------------------------------------------------------------------------------


class _PengambilYFinance:
    """Pengambil palsu: mengembalikan riwayat yfinance yang sama dengan `_riwayat_yfinance`."""

    def ambil(self, daftar: object) -> KumpulanData:
        kode = tuple(satu.kode for satu in daftar)  # type: ignore[attr-defined]
        return KumpulanData(
            sumber=SUMBER_YFINANCE,
            emiten=tuple(Emiten(kode=k, nama=k, sektor_idx_ic="industri", sumber="uji") for k in kode),
            harga_harian=tuple(
                _bar(k, AWAL + timedelta(days=i), CLOSE_YF, PENYESUAIAN_SPLIT)
                for k in kode
                for i in range(HARI)
            ),
        )


def _tulis_emiten(folder: Path) -> None:
    kolom = berkas.SPESIFIKASI["emiten"].nama_kolom
    lokasi.pastikan_folder(folder)
    baris = []
    for kode in KODE:
        isi = {nama: "" for nama in kolom}
        isi.update({"kode": kode, "nama": kode, "sumber": "uji", "dicatat_pada": "2026-01-01"})
        baris.append(";".join(isi[nama] for nama in kolom))
    (folder / "emiten.csv").write_text(
        ";".join(kolom) + "\n" + "\n".join(baris) + "\n", encoding="utf-8", newline="\n"
    )


def test_laporan_mutu_refresh_membaca_deret_sambungan(
    sambungan: sqlite3.Connection, tmp_path: Path
) -> None:
    """Refresh yang mengambil yfinance tetap memeriksa deret yang dipakai berhitung.

    Sebelumnya laporan mutu refresh menyaring ke label pengambilan, sehingga sesudah tanggal
    sambung ia memeriksa bar yfinance yang tidak dipakai dan menyebut seluruh snapshot tidak resmi.
    """
    _tersambung(sambungan)
    folder = tmp_path / "konfigurasi-uji"
    _tulis_emiten(folder)

    hasil = pengatur.jalankan_refresh(
        sambungan, _PengambilYFinance(), folder_impor=folder, momen=AKHIR
    )

    assert hasil.sukses, hasil.pesan
    assert hasil.laporan_mutu is not None
    catatan = [satu for satu in hasil.laporan_mutu.temuan if satu.jenis == "sumber_tidak_resmi"]
    assert len(catatan) == 1
    assert f"sebelum {SEJAK.isoformat()}" in catatan[0].keterangan
    assert SUMBER_IDX in catatan[0].keterangan
