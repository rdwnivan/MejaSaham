"""Pembaruan data harian satu langkah (K92) — dipakai tombol "Perbarui data" di dasbor."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from mejasaham import cadangan, db, ingesti, lokasi, pembaruan
from mejasaham.ingesti import Emiten, HargaHarian, HariBursa, KumpulanData

TANGGAL = date(2026, 10, 9)


class _Pengambil:
    def __init__(self, kumpulan: KumpulanData) -> None:
        self.kumpulan = kumpulan

    def ambil(self, emiten: Sequence[Emiten]) -> KumpulanData:
        return replace(self.kumpulan, emiten=tuple(emiten))


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "data"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(folder))
    # Uji lain bisa meninggalkan nilai ini di lingkungan proses (jebakan sesi 55).
    monkeypatch.setenv(cadangan.ENV_FOLDER_CADANGAN, str(tmp_path / "cadangan"))
    konfigurasi = lokasi.pastikan_folder(folder / "konfigurasi")
    (konfigurasi / "emiten.csv").write_text(
        "kode;nama;sektor_idx_ic;jenis;papan;status_notasi;jumlah_saham;free_float_persen;"
        "sumber;dicatat_pada\nAAAA;Emiten AAAA;;;;;;;Daftar uji;2026-10-01\n",
        encoding="utf-8",
    )
    return folder


def _kumpulan() -> KumpulanData:
    return KumpulanData(
        sumber=ingesti.SUMBER_YFINANCE,
        harga_harian=(HargaHarian(kode="AAAA", tanggal=TANGGAL, close=1000, volume=1_000_000),),
        kalender_bursa=(HariBursa(tanggal=TANGGAL, hari_bursa=True),),
    )


def test_pembaruan_menjalankan_refresh_cadangan_dan_saringan_berurutan(
    folder_data: Path, tmp_path: Path
) -> None:
    tahap: list[str] = []

    hasil = pembaruan.jalankan(_Pengambil(_kumpulan()), lapor=lambda k: tahap.append(k.tahap))

    assert hasil.berhasil, hasil.ringkas()
    assert hasil.refresh.id_snapshot is not None
    assert hasil.saring is not None and hasil.saring.id_snapshot == hasil.refresh.id_snapshot
    assert hasil.cadangan is not None and hasil.cadangan.parent == tmp_path / "cadangan"
    assert list(dict.fromkeys(tahap)) == list(pembaruan.TAHAP)

    sambungan = db.siapkan()
    try:
        keadaan = pembaruan.keadaan(sambungan, momen=TANGGAL)
    finally:
        sambungan.close()
    assert keadaan.terbaru, "snapshot dari hari bursa terakhir berarti data sudah paling baru"


def test_refresh_gagal_tidak_disusul_cadangan_maupun_saringan(
    folder_data: Path, tmp_path: Path
) -> None:
    (folder_data / "konfigurasi" / "emiten.csv").unlink()
    tahap: list[str] = []

    hasil = pembaruan.jalankan(_Pengambil(_kumpulan()), lapor=lambda k: tahap.append(k.tahap))

    assert not hasil.berhasil
    assert "emiten.csv" in hasil.refresh.pesan
    assert hasil.cadangan is None and hasil.saring is None
    assert set(tahap) == {pembaruan.MENGAMBIL}
    assert not (tmp_path / "cadangan").exists()


@pytest.mark.parametrize(
    ("tanggal_data", "hari_bursa", "terbaru"),
    [
        ("2026-10-28", "2026-10-28", True),
        ("2026-10-27", "2026-10-28", False),
        (None, "2026-10-28", False),
        # Kalender kosong = tidak bisa dinilai; lebih baik menawarkan pembaruan.
        ("2026-10-28", None, False),
    ],
)
def test_keadaan_terbaru_hanya_bila_snapshot_dari_hari_bursa_terakhir(
    tanggal_data: str | None, hari_bursa: str | None, terbaru: bool
) -> None:
    assert pembaruan.Keadaan(1, tanggal_data, hari_bursa).terbaru is terbaru


def test_lapor_per_emiten_menghitung_gagal_selagi_berjalan() -> None:
    from mejasaham.pengambil import Kemajuan as KemajuanEmiten

    diterima: list[pembaruan.Kemajuan] = []
    terima = pembaruan.lapor_per_emiten(diterima.append)
    terima(KemajuanEmiten(nomor=1, dari=3, kode="AAAA", baris=10))
    terima(KemajuanEmiten(nomor=2, dari=3, kode="BBBB", baris=0, galat="tidak ada data"))
    terima(KemajuanEmiten(nomor=3, dari=3, kode="CCCC", baris=10))

    assert [(k.nomor, k.dari, k.kode, k.gagal) for k in diterima] == [
        (1, 3, "AAAA", 0),
        (2, 3, "BBBB", 1),
        (3, 3, "CCCC", 1),
    ]


def test_pembaruan_tidak_mengambil_apa_pun_dari_idx(
    folder_data: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """K96: Syarat Penggunaan IDX melarang scraping, jadi tombol tidak lagi memanggil pengambil
    notasi — notasi, suspensi, dan UMA diunduh pengguna lalu diimpor."""
    from mejasaham import notasi

    def dilarang(*_: object, **__: object) -> object:
        raise AssertionError("pembaruan tidak boleh mengambil data IDX (K96)")

    for nama in ("ambil_ke_berkas", "unduh", "unduh_aktivitas"):
        monkeypatch.setattr(notasi, nama, dilarang)

    hasil = pembaruan.jalankan(_Pengambil(_kumpulan()), lapor=lambda k: None)

    assert hasil.berhasil, hasil.ringkas()
    assert "notasi" not in " ".join(pembaruan.TAHAP).lower()
