"""Uji kandidat & watchlist (F4, PRD 9.6) — `mejasaham/kandidat.py`.

Yang diuji adalah janji-janji yang membuat watchlist bisa dipercaya:

* **AC-4 ditegakkan dua kali.** Modul menolak lebih dulu (pesannya menyebut kolom yang kurang),
  dan `CHECK` di tabel menolaknya juga — uji di sini menembak **basis datanya langsung** untuk
  membuktikan aturannya tidak bergantung pada satu jalur kode. Aturan yang hanya hidup di satu
  fungsi akan hilang begitu ada jalur tulis kedua.
* **Tidak ada penghapusan senyap** (PRD 9.8): mengubah tesis menambah revisi, dan revisi lama
  masih bisa dibaca. Tesis adalah isi basis data yang tidak bisa dibangun ulang (PRD 9.12).
* **"Kandidat" bukan status** (PRD 9.6): status yang sah hanya lima, dan hasil saringan tidak
  pernah menjadi status dengan sendirinya.
* **Kode yang salah ketik ditolak**, sebab watchlist yang memuat kode tidak dikenal akan tampak
  wajar sampai seseorang mencoba memakainya.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import db, ingesti, kandidat, lokasi
from mejasaham.ingesti import Emiten, KumpulanData

SUMBER = "uji"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
HARI_INI = date(2026, 7, 1)
KODE = "AAAA"

#: Kolom wajib AC-4 beserta isiannya, supaya uji "lengkap" dan "kurang satu kolom" bisa ditulis
#: sebagai pembanding yang jelas — bukan sebagai lima kasus yang ditulis terpisah.
WAJIB = {
    "tesis": "pangsa pasar naik, utang turun",
    "pembatal_fundamental": "CFO/NI dua kuartal berturut-turut di bawah 0,5",
    "horizon": "1-6 bulan",
    "stop_awal": 900,
    "tanggal_tinjau": "2026-08-01",
}


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
def emiten(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    """Dua emiten lewat jalur nyata (`ingesti.simpan`), bukan INSERT tangan."""
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=(
                Emiten(kode=KODE, nama="Uji A"),
                Emiten(kode="BBBB", nama="Uji B"),
            ),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    return sambungan


# ---------------------------------------------------------------------------------------
# AC-4: kolom wajib sebelum watchlist
# ---------------------------------------------------------------------------------------


def test_ide_boleh_dicatat_tanpa_tesis(emiten: sqlite3.Connection) -> None:
    """PRD 9.6: `ide` = belum ada tesis. Melarangnya akan membuat ide hilang dari catatan."""
    hasil = kandidat.buat(emiten, KODE)

    assert hasil.status == "ide"
    assert hasil.revisi == 1
    assert hasil.tesis is None
    assert not hasil.kedaluwarsa(HARI_INI)


def test_watchlist_tanpa_kolom_wajib_ditolak(emiten: sqlite3.Connection) -> None:
    with pytest.raises(kandidat.GalatKandidat) as galat:
        kandidat.buat(emiten, KODE, status="watchlist")

    pesan = str(galat.value)
    for sebutan in ("alasan masuk (tesis)", "pembatal fundamental", "horizon", "stop awal", "tanggal tinjau"):
        assert sebutan in pesan, pesan


def test_watchlist_kurang_satu_kolom_ditolak(emiten: sqlite3.Connection) -> None:
    """Empat dari lima kolom terisi tetap ditolak — AC-4 menyebut kelimanya."""
    kurang = {kunci: nilai for kunci, nilai in WAJIB.items() if kunci != "stop_awal"}

    with pytest.raises(kandidat.GalatKandidat, match="stop awal"):
        kandidat.buat(emiten, KODE, status="watchlist", **kurang)


def test_watchlist_dengan_kolom_lengkap_diterima(emiten: sqlite3.Connection) -> None:
    hasil = kandidat.buat(emiten, KODE, status="watchlist", **WAJIB)

    assert hasil.status == "watchlist"
    assert hasil.stop_awal == 900
    assert hasil.dicatat_pada.startswith("2026-")


def test_teks_spasi_saja_dianggap_belum_diisi(emiten: sqlite3.Connection) -> None:
    """`" "` bukan tesis. Tanpa ini, AC-4 bisa dilewati dengan menekan spasi."""
    with pytest.raises(kandidat.GalatKandidat, match="alasan masuk"):
        kandidat.buat(emiten, KODE, status="watchlist", **{**WAJIB, "tesis": "   "})


def test_basis_data_menolak_watchlist_tanpa_tesis(emiten: sqlite3.Connection) -> None:
    """AC-4 ditegakkan `CHECK`, bukan hanya modul: jalur tulis lain pun tunduk padanya."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(emiten):
            emiten.execute(
                "INSERT INTO kandidat (id_kandidat, revisi, kode, status, pembatal_fundamental,"
                " horizon, stop_awal, tanggal_tinjau, dicatat_pada)"
                " VALUES (99, 1, ?, 'watchlist', 'x', 'y', 900, '2026-08-01', ?)",
                (KODE, "2026-07-01T09:00:00+07:00"),
            )


def test_kode_tidak_dikenal_ditolak(emiten: sqlite3.Connection) -> None:
    with pytest.raises(kandidat.GalatKandidat, match="tidak ada di daftar emiten"):
        kandidat.buat(emiten, "ZZZZ")


# ---------------------------------------------------------------------------------------
# Status: perpindahan, pembuangan, dan riwayat
# ---------------------------------------------------------------------------------------


def test_perpindahan_maju_diizinkan(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE)
    watchlist = kandidat.ubah(emiten, ide.id_kandidat, {"status": "watchlist", **WAJIB})
    rencana = kandidat.ubah(emiten, watchlist.id_kandidat, {"status": "rencana"})
    posisi = kandidat.ubah(emiten, rencana.id_kandidat, {"status": "posisi"})

    assert (watchlist.revisi, rencana.revisi, posisi.revisi) == (2, 3, 4)
    assert posisi.status == "posisi"


def test_perpindahan_mundur_ditolak(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE, status="watchlist", **WAJIB)

    with pytest.raises(kandidat.GalatKandidat, match="tidak diizinkan"):
        kandidat.ubah(emiten, ide.id_kandidat, {"status": "ide"})


def test_dibuang_menuntut_alasan(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE)

    with pytest.raises(kandidat.GalatKandidat, match="alasan"):
        kandidat.ubah(emiten, ide.id_kandidat, {"status": "dibuang"})


def test_entri_yang_dibuang_bersifat_final(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE)
    dibuang = kandidat.ubah(
        emiten, ide.id_kandidat, {"status": "dibuang", "alasan_dibuang": "tesis tidak terbukti"}
    )

    assert dibuang.status == "dibuang"
    with pytest.raises(kandidat.GalatKandidat, match="final"):
        kandidat.ubah(emiten, ide.id_kandidat, {"tesis": "berubah pikiran"})


def test_entri_baru_tidak_boleh_langsung_dibuang(emiten: sqlite3.Connection) -> None:
    """Membuang sesuatu yang belum pernah dicatat bukan keputusan, melainkan salah ketik."""
    with pytest.raises(kandidat.GalatKandidat, match="langsung"):
        kandidat.buat(emiten, KODE, status="dibuang")


def test_ubah_menambah_revisi_dan_revisi_lama_tetap_ada(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE, tesis="versi pertama")
    kandidat.ubah(emiten, ide.id_kandidat, {"tesis": "versi kedua"})

    riwayat = kandidat.riwayat(emiten, ide.id_kandidat)
    sekarang = kandidat.wajib_ada(emiten, ide.id_kandidat)

    assert [satu.revisi for satu in riwayat] == [1, 2]
    assert riwayat[0].tesis == "versi pertama", "revisi lama tidak boleh hilang (PRD 9.8)"
    assert sekarang.tesis == "versi kedua"
    assert emiten.execute("SELECT COUNT(*) FROM kandidat").fetchone()[0] == 2


def test_ubah_tanpa_perubahan_tidak_menambah_revisi(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE, tesis="tetap")

    with pytest.raises(kandidat.GalatKandidat, match="tidak ada yang berubah"):
        kandidat.ubah(emiten, ide.id_kandidat, {"tesis": "tetap"})


def test_kode_tidak_bisa_dipindah_ke_emiten_lain(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE)

    with pytest.raises(kandidat.GalatKandidat, match="kode tidak bisa diubah"):
        kandidat.ubah(emiten, ide.id_kandidat, {"kode": "BBBB"})


def test_status_tidak_dikenal_ditolak_dengan_daftar_yang_sah(emiten: sqlite3.Connection) -> None:
    with pytest.raises(kandidat.GalatKandidat) as galat:
        kandidat.buat(emiten, KODE, status="kandidat")

    pesan = str(galat.value)
    assert "kandidat" in pesan and "bukan status" in pesan
    assert "watchlist" in pesan


# ---------------------------------------------------------------------------------------
# Tinjauan & kedaluwarsa (PRD 9.6)
# ---------------------------------------------------------------------------------------


def test_saran_tanggal_tinjau_30_hari() -> None:
    assert kandidat.saran_tanggal_tinjau(HARI_INI) == (HARI_INI + timedelta(days=30)).isoformat()


def test_kedaluwarsa_ketika_tanggal_tinjau_sudah_lewat(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE, status="watchlist", **{**WAJIB, "tanggal_tinjau": "2026-06-30"})
    sebelum = kandidat.buat(emiten, "BBBB", status="watchlist", **{**WAJIB, "tanggal_tinjau": "2026-07-02"})

    assert ide.kedaluwarsa(date(2026, 7, 1)), "tanggal tinjau 30 Jun sudah lewat pada 1 Jul"
    assert not sebelum.kedaluwarsa(date(2026, 7, 1))
    assert ide.terlambat_hari(date(2026, 7, 3)) == 3


def test_ide_tidak_pernah_kedaluwarsa(emiten: sqlite3.Connection) -> None:
    """Ide memang belum punya tesis; menandainya kedaluwarsa akan menghukum pencatatan jujur."""
    ide = kandidat.buat(emiten, KODE, tanggal_tinjau="2020-01-01")

    assert not ide.kedaluwarsa(HARI_INI)


def test_tinjau_ulang_menggeser_tanggal_tinjau(emiten: sqlite3.Connection) -> None:
    ide = kandidat.buat(emiten, KODE, status="watchlist", **{**WAJIB, "tanggal_tinjau": "2026-06-01"})
    sesudah = kandidat.tinjau(emiten, ide.id_kandidat, hari_ini=HARI_INI)

    assert sesudah.revisi == 2
    assert sesudah.tanggal_tinjau == kandidat.saran_tanggal_tinjau(HARI_INI)
    assert not sesudah.kedaluwarsa(HARI_INI)


def test_tinjauan_tepat_waktu_tetap_tercatat(emiten: sqlite3.Connection) -> None:
    """Tinjauan yang jatuh pada tanggal yang sama bukan "tidak ada perubahan".

    Kasusnya nyata dan ditemukan saat menjalankan perintahnya atas data sungguhan: menyimpan
    `--tinjau-ulang` pada entri yang tanggal tinjaunya sudah "hari ini + 30" menghasilkan tanggal
    yang sama, sehingga pemeriksaan "tidak ada yang berubah" menolaknya — padahal tinjauannya
    benar-benar terjadi, dan PRD 13.1 menghitung cakupan tinjauan dari peristiwa itu.
    """
    tanggal = kandidat.saran_tanggal_tinjau(HARI_INI)
    ide = kandidat.buat(emiten, KODE, status="watchlist", **{**WAJIB, "tanggal_tinjau": tanggal})
    sesudah = kandidat.tinjau(emiten, ide.id_kandidat, hari_ini=HARI_INI)

    assert sesudah.tanggal_tinjau == ide.tanggal_tinjau == tanggal
    assert sesudah.revisi == ide.revisi + 1, "peristiwanya harus tetap tercatat"


def test_baris_kandidat_tidak_bisa_diubah_trigger(emiten: sqlite3.Connection) -> None:
    """Aturan append-only ditegakkan mesin, bukan hanya oleh `ubah()` (S1, PRD 9.8)."""
    ide = kandidat.buat(emiten, KODE, tesis="asli")

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        emiten.execute("UPDATE kandidat SET tesis = 'ditimpa' WHERE id_kandidat = ?", (ide.id_kandidat,))


def test_daftar_dapat_disaring_per_status(emiten: sqlite3.Connection) -> None:
    kandidat.buat(emiten, KODE)
    kandidat.buat(emiten, "BBBB", status="watchlist", **WAJIB)

    assert [satu.kode for satu in kandidat.daftar(emiten)] == [KODE, "BBBB"]
    assert [satu.kode for satu in kandidat.daftar(emiten, "watchlist")] == ["BBBB"]
    assert kandidat.daftar(emiten, "posisi") == ()
    assert [satu.kode for satu in kandidat.daftar(emiten, kode="bbbb")] == ["BBBB"]
