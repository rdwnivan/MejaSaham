"""Uji konteks pasar tersimpan (K61; PRD 8.2/11.1) — `mejasaham/konteks_pasar.py`.

Yang dijaga di sini adalah **syarat sahnya angka tersimpan**, bukan sekadar bisa ditulis:
konteks pasar hanya boleh dibaca kembali bila `id_snapshot`, `id_preset`, label sumber harga,
dan versi cara menghitungnya masih sama. Tanpa salah satu syarat itu, angka lama akan terbaca
sebagai keadaan hari ini — persis kelas kesalahan yang dicegah K58/K61.

Uji perilaku dasbor & `--saring` (termasuk pembuktian bahwa dasbor tidak menghitung ulang) ada
di `tests/test_dasbor.py`, karena di sana fixture data pasar sudah tersedia.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from mejasaham import __version__, db, konteks_pasar, lokasi, metrik
from mejasaham.ingesti import PenutupanIndeks
from mejasaham.skema import VERSI_TERBARU

TANGGAL = date(2026, 7, 1)
PRESET = "uji/v1"
SUMBER = "uji-sumber"


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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


@pytest.fixture()
def kunci(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    """Snapshot #1 dan preset uji yang memenuhi kunci asing tabel `konteks_pasar`."""
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO snapshot (id_snapshot, tanggal_data, batas_diketahui, jam_ambil,"
            " jumlah_emiten, jumlah_gagal, versi_skema, versi_aplikasi)"
            " VALUES (1, ?, '2026-07-01T06:00:00+07:00', '2026-07-01T06:00:00+07:00',"
            " 0, 0, ?, ?)",
            (TANGGAL.isoformat(), VERSI_TERBARU, __version__),
        )
        koneksi.execute(
            "INSERT INTO preset_saring (id_preset, nama, versi, horizon, keterangan, dibuat_pada)"
            " VALUES (?, 'uji', 1, 'bulanan', 'uji', '2026-07-01')",
            (PRESET,),
        )
    return sambungan


def _konteks(*, breadth: metrik.Nilai | None = None, catatan: str | None = None) -> konteks_pasar.KonteksPasar:
    return konteks_pasar.KonteksPasar(
        pasar=konteks_pasar.BarisIndeks(
            indeks="IHSG",
            tanggal=TANGGAL,
            penutupan=6_200,
            penutupan_sebelumnya=6_000,
            tanggal_sebelumnya=date(2026, 6, 30),
        ),
        breadth=breadth
        or metrik.hitung("breadth", 0.5, "rasio", "1 dari 2 emiten likuid", "tidak ada data"),
        rezim="RISK-ON",
        preset=PRESET,
        catatan=catatan,
    )


def _simpan(sambungan: sqlite3.Connection, konteks: konteks_pasar.KonteksPasar) -> None:
    konteks_pasar.simpan(
        sambungan, konteks, id_snapshot=1, id_preset=PRESET, sumber=SUMBER
    )


def test_simpan_dan_muat_bulat_balik(kunci: sqlite3.Connection) -> None:
    """Seluruh isi konteks — termasuk asal breadth dan penutupan sebelumnya — kembali utuh."""
    konteks = _konteks(catatan="rezim pasar NETRAL karena bahannya belum lengkap: uji")
    _simpan(kunci, konteks)

    dibaca = konteks_pasar.muat(kunci, id_snapshot=1, id_preset=PRESET, sumber=SUMBER)

    assert dibaca == konteks
    assert dibaca is not None
    assert dibaca.breadth is not None and dibaca.breadth.ada
    assert dibaca.breadth.asal == "1 dari 2 emiten likuid"


def test_baris_ditulis_ulang_bukan_ditumpuk(kunci: sqlite3.Connection) -> None:
    """Satu (snapshot, preset, sumber) punya satu baris: konteks adalah turunan, bukan riwayat."""
    _simpan(kunci, _konteks())
    _simpan(kunci, _konteks(breadth=metrik.tidak_dihitung("breadth", "rasio", "tidak ada likuid")))

    baris = kunci.execute("SELECT * FROM konteks_pasar").fetchall()

    assert len(baris) == 1
    assert baris[0]["breadth_status"] == metrik.STATUS_TIDAK_DIHITUNG
    assert baris[0]["breadth_alasan"] == "tidak ada likuid"


def test_breadth_tidak_dihitung_dan_indeks_kosong_ikut_bulat_balik(kunci: sqlite3.Connection) -> None:
    """Keadaan "tidak dihitung" bukan angka nol, dan sebabnya ikut tersimpan (aturan keras 2)."""
    konteks = konteks_pasar.KonteksPasar(
        pasar=None,
        breadth=metrik.tidak_dihitung("breadth", "rasio", "tidak ada emiten likuid"),
        rezim="NETRAL (dasar tidak lengkap)",
        preset=PRESET,
        catatan="penutupan IHSG belum ada di basis data",
    )
    _simpan(kunci, konteks)

    dibaca = konteks_pasar.muat(kunci, id_snapshot=1, id_preset=PRESET, sumber=SUMBER)

    assert dibaca == konteks
    assert dibaca is not None
    assert dibaca.pasar is None
    assert dibaca.breadth is not None and not dibaca.breadth.ada
    assert dibaca.breadth.alasan == "tidak ada emiten likuid"
    assert dibaca.catatan == "penutupan IHSG belum ada di basis data"


def test_versi_hitung_lain_tidak_dipakai(kunci: sqlite3.Connection) -> None:
    """Perubahan cara menghitung membatalkan angka lama — pola `skor.versi_hitung`."""
    _simpan(kunci, _konteks())
    with db.tulis(kunci) as koneksi:
        koneksi.execute("UPDATE konteks_pasar SET versi_hitung = 'pasar-0'")

    assert konteks_pasar.muat(kunci, id_snapshot=1, id_preset=PRESET, sumber=SUMBER) is None


def test_kunci_yang_berbeda_tidak_dipakai(kunci: sqlite3.Connection) -> None:
    """Snapshot, preset, atau label harga yang berbeda bukan konteks yang sama."""
    _simpan(kunci, _konteks())

    assert konteks_pasar.muat(kunci, id_snapshot=2, id_preset=PRESET, sumber=SUMBER) is None
    assert konteks_pasar.muat(kunci, id_snapshot=1, id_preset="lain/v1", sumber=SUMBER) is None
    assert konteks_pasar.muat(kunci, id_snapshot=1, id_preset=PRESET, sumber="lain") is None


def test_sumber_kosong_dan_none_menunjuk_baris_yang_sama(kunci: sqlite3.Connection) -> None:
    """`None` = belum ada label harga; di kunci ia disimpan sebagai teks kosong, bukan NULL.

    Kunci primer SQLite tidak menolak NULL, sehingga NULL di kolom kunci bisa menghasilkan dua
    baris untuk keadaan yang sama. Teks kosong membuat kuncinya benar-benar tunggal.
    """
    konteks = _konteks()
    konteks_pasar.simpan(kunci, konteks, id_snapshot=1, id_preset=PRESET, sumber=None)

    assert konteks_pasar.muat(kunci, id_snapshot=1, id_preset=PRESET, sumber="") == konteks
    assert konteks_pasar.muat(kunci, id_snapshot=1, id_preset=PRESET, sumber=None) == konteks


def test_konteks_tanpa_breadth_ditolak(kunci: sqlite3.Connection) -> None:
    """Konteks yang belum punya hasil breadth bukan keadaan yang bisa disimpan diam-diam."""
    with pytest.raises(ValueError, match="breadth"):
        konteks_pasar.simpan(
            kunci,
            konteks_pasar.KonteksPasar(preset=PRESET),
            id_snapshot=1,
            id_preset=PRESET,
            sumber=SUMBER,
        )


def test_versi_hitung_tidak_kosong() -> None:
    """Versi cara menghitung harus berarti; ia yang membatalkan baris lama setelah rumus berubah."""
    assert konteks_pasar.VERSI_HITUNG.strip()
    assert konteks_pasar.VERSI_HITUNG == "pasar-2"


def _sisip_mentah(kunci: sqlite3.Connection, *, status: str, nilai: float | None, alasan: str | None) -> None:
    with db.tulis(kunci) as koneksi:
        koneksi.execute(
            "INSERT INTO konteks_pasar (id_snapshot, id_preset, sumber_harga, versi_hitung,"
            " breadth_nilai, breadth_status, breadth_alasan, breadth_asal, rezim, dihitung_pada)"
            " VALUES (1, ?, 'uji', 'pasar-2', ?, ?, ?, '', 'RISK-ON',"
            " '2026-07-01T06:00:00+07:00')",
            (PRESET, nilai, status, alasan),
        )


def test_dihitung_wajib_punya_nilai_dan_tidak_dihitung_wajib_punya_alasan(
    kunci: sqlite3.Connection,
) -> None:
    """Aturan keras 2 dijaga mesin: "dihitung" tanpa angka dan "tidak dihitung" tanpa sebab.

    Keduanya akan terbaca sebagai hasil yang sah padahal bukan — persis yang dicegah K61 dan
    aturan "metrik tanpa data berstatus tidak dihitung, bukan nol".
    """
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        _sisip_mentah(kunci, status="dihitung", nilai=None, alasan=None)

    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        _sisip_mentah(kunci, status="tidak_dihitung", nilai=0.5, alasan=None)


def test_bar_kosong_di_tengah_membuat_pembandingnya_disebut() -> None:
    """Uji regresi (sesi 69): bar IHSG 28 Okt kosong, sehingga dasbor membandingkan 29 Okt dengan
    27 Okt (-168, -3,19%) tanpa menyebutnya — terbaca sebagai perubahan harian. Pembandingnya
    kini selalu bertanggal."""
    bahan = SimpleNamespace(
        indeks={
            "IHSG": [
                PenutupanIndeks("IHSG", date(2026, 10, 27), close=5_266),
                PenutupanIndeks("IHSG", date(2026, 10, 28), close=None),
                PenutupanIndeks("IHSG", date(2026, 10, 29), close=5_098),
            ]
        }
    )

    baris = konteks_pasar.baris_indeks(bahan)  # type: ignore[arg-type]

    assert baris is not None
    assert (baris.penutupan_sebelumnya, baris.tanggal_sebelumnya) == (5_266, date(2026, 10, 27))
    assert baris.ringkas() == "IHSG 5.098 (29 Okt 2026) · -168 (-3,19%) terhadap 27 Okt 2026"
