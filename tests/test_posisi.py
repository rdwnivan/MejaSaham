"""Uji transaksi & posisi (F11, PRD 9.11) — `mejasaham/posisi.py`.

Yang diuji adalah janji-janji yang membuat catatan eksekusi bisa dipercaya:

* **`transaksi` satu-satunya sumber angka.** Lembar, harga rata-rata, dan hasil diturunkan dari
  baris transaksi; `posisi` tidak menyimpannya. Kalau turunan itu meleset sedikit, seluruh
  keputusan berikutnya memakai angka yang salah tanpa satu pun galat.
* **Pelanggaran dicatat, bukan dicegah** (PRD 9.8). Eksekusi yang sudah terjadi di sekuritas
  tetap bisa dicatat apa adanya; yang diuji di sini adalah V1/V2/V5/V6 benar-benar **terdeteksi
  dan tersimpan** — pelanggaran yang tidak terdeteksi sama dengan pelanggaran yang tidak ada.
* **"Tidak dapat dinilai" bukan nol** (aturan keras 2). Posisi tanpa stop, harga yang tidak ada,
  dan biaya yang belum dicatat membuat angkanya berstatus tidak dinilai — dan itu tampil.
* **AC-6**: risiko berjalan = risiko terbuka posisi aktif + rencana yang **belum** dieksekusi;
  rencana yang sudah punya transaksi tidak dihitung dua kali.
* **AC-13**: setoran/penarikan dana tidak mengubah drawdown — diuji dengan deret yang membuat
  jawaban mentah dan jawaban terkoreksi **berbeda**.
* **Mesin yang menegakkan bentuknya**: append-only, `CHECK` mode, `CHECK` pajak ≤ biaya, dan
  `CHECK` biaya ⇔ asal biaya diuji lewat penulisan SQL langsung, bukan lewat modul.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import cli, db, ingesti, kandidat, konfigurasi, lokasi, posisi, risiko
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    HargaHarian,
    KumpulanData,
)

SUMBER = "uji-posisi"
SUMBER_LAIN = "pembanding-uji"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
KODE = "AAAA"
KODE_LAIN = "BBBB"
SEKTOR = "industri"
LOT = 100

#: Deret harga: 24 hari, rentang tetap 40, penutupan 2.320 (tick 10 pada pita 2.000–4.999).
CLOSE = 2_320
RENTANG = 40
HARI = 24
VOLUME = 2_000_000

EMITEN_UJI = (
    Emiten(kode=KODE, nama="Emiten A", sektor_idx_ic=SEKTOR, sumber="uji-rujukan"),
    Emiten(kode=KODE_LAIN, nama="Emiten B", sektor_idx_ic=SEKTOR, sumber="uji-rujukan"),
)

LOT_100 = """
[[lot]]
nilai_lembar  = 100
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06
"""

FRAKSI_HARGA = """
[[fraksi_harga]]
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06
rentang = [
  { batas_bawah = 200,  batas_atas = 499,  tick = 2 },
  { batas_bawah = 2000, batas_atas = 4999, tick = 10 },
  { batas_bawah = 5000, tick = 25 },
  { batas_bawah = 1,    batas_atas = 199,  tick = 1 },
  { batas_bawah = 500,  batas_atas = 1999, tick = 5 },
]
"""

#: Tarif *all-in* seperti Stockbit: PPh final jual sudah termasuk di dalam 0,25% (K23).
BROKER_ALL_IN = """
[[biaya_broker]]
nama          = "Broker All-in"
sisi_beli     = { persen = 0.15 }
sisi_jual     = { persen = 0.25 }
sudah_termasuk = ["pph_penjualan", "levy", "ppn"]
berlaku_sejak = 2026-01-02
sumber        = "Halaman tarif resmi broker (uji): fee beli 0,15% / fee jual 0,25% sudah termasuk PPh"
dicatat_pada  = 2026-10-06
"""

#: Tarif yang menyatakan tarifnya saja: PPh final penjualan harus ditambahkan sendiri.
BROKER_TANPA_PPH = """
[[biaya_broker]]
nama          = "Broker Biasa"
sisi_beli     = { persen = 0.15, minimum = 10000 }
sisi_jual     = { persen = 0.25 }
berlaku_sejak = 2026-01-02
sumber        = "Dokumen tarif broker (uji)"
dicatat_pada  = 2026-10-06
"""

PAJAK_PENJUALAN = """
[[pajak_penjualan]]
persen        = 0.1
dasar         = "nilai jual"
berlaku_sejak = 2026-01-02
sumber        = "Dasar hukum (uji)"
dicatat_pada  = 2026-10-06
"""

SLIPPAGE_TICK = """
[[slippage]]
mode          = "tick"
nilai         = 1
berlaku_sejak = 2026-01-02
sumber        = "Keputusan produk K20 (uji)"
dicatat_pada  = 2026-10-06
"""


def _urai(*blok: str) -> tuple[konfigurasi.EntriParameter, ...]:
    return konfigurasi.urai("skema = 1\n\n" + "\n\n".join(blok), asal="uji")


def _deret(kode: str, *, hari: int = HARI, close: int = CLOSE, sumber: str = SUMBER) -> tuple[HargaHarian, ...]:
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=hari - 1 - i),
            open=close,
            high=close + RENTANG // 2,
            low=close - RENTANG // 2,
            close=close,
            volume=VOLUME,
            nilai=close * VOLUME,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(hari)
    )


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
def berparameter(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    konfigurasi.simpan(
        sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_ALL_IN, PAJAK_PENJUALAN, SLIPPAGE_TICK)
    )
    return sambungan


@pytest.fixture()
def data(berparameter: sqlite3.Connection) -> sqlite3.Connection:
    ingesti.simpan(
        berparameter,
        KumpulanData(
            sumber=SUMBER,
            emiten=EMITEN_UJI,
            harga_harian=_deret(KODE) + _deret(KODE_LAIN),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    return berparameter


@pytest.fixture()
def siap(data: sqlite3.Connection) -> sqlite3.Connection:
    """Basis data lengkap: parameter + data + batas risiko + ekuitas harian."""
    risiko.simpan_preset(data, risiko.batas_bawaan(date(2026, 7, 1)))
    risiko.catat_ekuitas(
        data,
        ekuitas=250_000_000,
        kas=100_000_000,
        arus_dana=0,
        mode="nyata",
        tanggal=date(2026, 7, 1),
    )
    return data


def _kandidat_watchlist(
    sambungan: sqlite3.Connection, kode: str = KODE, *, stop_awal: int = 2_180
) -> kandidat.Kandidat:
    return kandidat.buat(
        sambungan,
        kode,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=stop_awal,
        tanggal_tinjau="2026-08-01",
    )


def _rencana(sambungan: sqlite3.Connection, kode: str = KODE, **ganti: int) -> risiko.Rencana:
    """Rencana tersimpan lewat kalkulator yang sebenarnya (bukan INSERT tangan)."""
    entri = _kandidat_watchlist(sambungan, kode)
    masukan = risiko.siapkan_masukan(sambungan, kode, pada=date(2026, 7, 1))
    hasil, _stop = risiko.hitung_untuk(masukan, harga_masuk=ganti.get("harga_masuk", CLOSE))
    return risiko.simpan(
        sambungan,
        hasil,
        id_kandidat=entri.id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )


def _beli(sambungan: sqlite3.Connection, kode: str = KODE, **ganti: object) -> posisi.PendaftaranTransaksi:
    argumen: dict[str, object] = {
        "harga": CLOSE,
        "lembar": 1_000,
        "mode": "nyata",
        "tanggal": date(2026, 7, 2),
    }
    argumen.update(ganti)
    return posisi.catat_transaksi(sambungan, kode, "beli", **argumen)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------
# Bentuk baris: mesin yang menegakkan, bukan disiplin penulis kode
# ---------------------------------------------------------------------------------------


def test_posisi_dan_transaksi_append_only(siap: sqlite3.Connection) -> None:
    """Perbaikan data menambah baris (S1); trigger yang menegakkannya, bukan modul."""
    hasil = _beli(siap, id_rencana=None)

    for tabel, kunci in (
        ("posisi", f"id_posisi = {hasil.posisi.id_posisi}"),
        ("transaksi", f"id_transaksi = {hasil.transaksi.id_transaksi}"),
    ):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            siap.execute(f"UPDATE {tabel} SET catatan = 'diubah' WHERE {kunci}")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            siap.execute(f"DELETE FROM {tabel} WHERE {kunci}")


def test_mode_yang_tidak_dikenal_ditolak_check(siap: sqlite3.Connection) -> None:
    """PRD 9.11: mode yang tidak dinyatakan membuat pemisahan simulasi/nyata mustahil."""
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO transaksi (id_transaksi, revisi, id_posisi, tanggal, kode, aksi, harga,"
            " lembar, mode, sumber, diketahui_pada)"
            " VALUES (99, 1, 1, '2026-07-02', 'AAAA', 'beli', 2320, 100, 'karangan', 'uji',"
            " '2026-07-02T09:00:00+07:00')"
        )


def test_pajak_tidak_boleh_melebihi_biaya(siap: sqlite3.Connection) -> None:
    """K23: `pajak` adalah BAGIAN dari biaya — menjumlahkan keduanya menghitung PPh dua kali."""
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO transaksi (id_transaksi, revisi, id_posisi, tanggal, kode, aksi, harga,"
            " lembar, biaya, asal_biaya, pajak, mode, sumber, diketahui_pada)"
            " VALUES (99, 1, 1, '2026-07-02', 'AAAA', 'beli', 2320, 100, 1000,"
            " 'dicatat_pengguna', 2000, 'nyata', 'uji', '2026-07-02T09:00:00+07:00')"
        )


def test_biaya_tanpa_asal_ditolak(siap: sqlite3.Connection) -> None:
    """Biaya yang tidak menyatakan asalnya tidak bisa diperiksa: dicatat atau dihitung?"""
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO transaksi (id_transaksi, revisi, id_posisi, tanggal, kode, aksi, harga,"
            " lembar, biaya, mode, sumber, diketahui_pada)"
            " VALUES (99, 1, 1, '2026-07-02', 'AAAA', 'beli', 2320, 100, 1000, 'nyata', 'uji',"
            " '2026-07-02T09:00:00+07:00')"
        )


def test_tampilan_terkini_memilih_revisi_terakhir_walau_detiknya_sama(
    siap: sqlite3.Connection,
) -> None:
    """Kelas cacat T37: pembeda revisi adalah kolom `revisi`, bukan stempel waktu."""
    hasil = _beli(siap)
    posisi.ubah_stop(siap, hasil.posisi.id_posisi, 2_250, tanggal=date(2026, 7, 3))

    assert posisi.wajib_ada(siap, hasil.posisi.id_posisi).stop_terkini == 2_250
    assert len(posisi.riwayat(siap, hasil.posisi.id_posisi)) == 2


# ---------------------------------------------------------------------------------------
# Catat transaksi: membuka posisi, dan angka yang diturunkan
# ---------------------------------------------------------------------------------------


def test_beli_membuka_posisi_dan_angkanya_diturunkan_dari_transaksi(
    siap: sqlite3.Connection,
) -> None:
    hasil = _beli(siap, lembar=1_000)

    assert hasil.posisi.status == "aktif"
    assert hasil.posisi.tgl_buka == "2026-07-02"
    angka = posisi.hitungan(siap, hasil.posisi.id_posisi)
    assert angka.lembar_beli == 1_000
    assert angka.lembar_terbuka == 1_000
    assert angka.harga_rata == 2_320


def test_harga_rata_adalah_rata_rata_tertimbang(siap: sqlite3.Connection) -> None:
    """(100 × 2.000 + 300 × 2.400) ÷ 400 = 2.300 — bukan rata-rata dua harga."""
    hasil = _beli(siap, harga=2_000, lembar=100)
    _beli(siap, harga=2_400, lembar=300, tanggal=date(2026, 7, 3))

    angka = posisi.hitungan(siap, hasil.posisi.id_posisi)
    assert angka.lembar_terbuka == 400
    assert angka.harga_rata == 2_300
    assert len(posisi.daftar(siap, status="aktif")) == 1  # pembelian kedua menambah posisi yang sama


def test_lembar_bukan_kelipatan_lot_ditolak(siap: sqlite3.Connection) -> None:
    with pytest.raises(posisi.GalatPosisi, match="kelipatan lot 100"):
        _beli(siap, lembar=150)


def test_harga_bukan_tick_sah_ditolak(siap: sqlite3.Connection) -> None:
    with pytest.raises(posisi.GalatPosisi, match="tick"):
        _beli(siap, harga=2_325)


def test_kode_yang_tidak_dikenal_ditolak(siap: sqlite3.Connection) -> None:
    with pytest.raises(posisi.GalatPosisi, match="tidak ada di daftar emiten"):
        _beli(siap, "ZZZZ")


def test_mode_wajib_dinyatakan(siap: sqlite3.Connection) -> None:
    with pytest.raises(posisi.GalatPosisi, match="wajib menyatakan modenya"):
        posisi.catat_transaksi(siap, KODE, "beli", harga=CLOSE, lembar=100, mode=None)  # type: ignore[arg-type]


def test_aksi_yang_tidak_dikenal_ditolak(siap: sqlite3.Connection) -> None:
    """PRD 5: hanya posisi beli — tidak ada short, margin, atau derivatif."""
    with pytest.raises(posisi.GalatPosisi, match="hanya posisi beli"):
        posisi.catat_transaksi(siap, KODE, "short", harga=CLOSE, lembar=100, mode="nyata")


def test_transaksi_bertanggal_mundur_ditolak(siap: sqlite3.Connection) -> None:
    """Urutan tanggal harus terjaga, sebab lembar pada tiap tanggal diturunkan dari urutannya."""
    _beli(siap, tanggal=date(2026, 7, 5))

    with pytest.raises(posisi.GalatPosisi, match="sudah tercatat sampai 2026-07-05"):
        _beli(siap, tanggal=date(2026, 7, 3))


# ---------------------------------------------------------------------------------------
# Pelanggaran V1/V2/V6 dicatat, bukan dicegah (PRD 9.8)
# ---------------------------------------------------------------------------------------


def test_transaksi_tanpa_rencana_mencatat_pelanggaran_v6(siap: sqlite3.Connection) -> None:
    hasil = _beli(siap)

    # Tanpa rencana **dan** tanpa tesis: V6 (tanpa rencana) dan V1 (tanpa stop) dua-duanya nyata.
    assert hasil.pelanggaran == ("V1", "V6")
    assert hasil.transaksi.pelanggaran == "V1;V6"
    assert "tanpa rencana" in hasil.transaksi.ringkas()
    assert "V6 (transaksi tanpa rencana tersimpan)" in hasil.transaksi.ringkas()


def test_beli_tanpa_stop_mencatat_pelanggaran_v1(siap: sqlite3.Connection) -> None:
    """Tidak ada rencana maupun tesis: stop tidak dikarang dari ATR."""
    hasil = _beli(siap)

    assert "V1" in hasil.pelanggaran
    assert hasil.posisi.stop_terkini is None
    ringkasan = posisi.ringkasan(siap, hasil.posisi)
    assert ringkasan.risiko_terbuka is None
    assert "tanpa stop" in (ringkasan.alasan_risiko or "")


def test_stop_diambil_dari_rencana_yang_dieksekusi(siap: sqlite3.Connection) -> None:
    """Stop yang **dinyatakan** rencana dipakai, dan asalnya disebut."""
    rencana = _rencana(siap)
    hasil = _beli(siap, id_rencana=rencana.id_rencana)

    assert hasil.posisi.stop_terkini == rencana.stop
    assert "V1" not in hasil.pelanggaran
    assert "V2" not in hasil.pelanggaran
    assert any("stop dari rencana" in satu for satu in hasil.catatan)


def test_stop_diambil_dari_tesis_kandidat_bila_tanpa_rencana(siap: sqlite3.Connection) -> None:
    _kandidat_watchlist(siap, stop_awal=2_200)

    hasil = _beli(siap)

    assert hasil.posisi.stop_terkini == 2_200
    assert any("stop awal dari tesis kandidat" in satu for satu in hasil.catatan)


def test_lembar_melebihi_rencana_mencatat_pelanggaran_v2(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)

    hasil = _beli(siap, lembar=rencana.lembar + LOT, id_rencana=rencana.id_rencana)

    assert "V2" in hasil.pelanggaran
    assert hasil.transaksi.lembar > rencana.lembar


def test_pembelian_kedua_yang_melewati_rencana_juga_terdeteksi_v2(
    siap: sqlite3.Connection,
) -> None:
    """V2 dinilai dari **lembar posisi**, bukan dari lembar satu transaksi saja."""
    rencana = _rencana(siap)
    _beli(siap, lembar=rencana.lembar, id_rencana=rencana.id_rencana)

    hasil = _beli(siap, lembar=LOT, tanggal=date(2026, 7, 3), id_rencana=rencana.id_rencana)

    assert hasil.pelanggaran == ("V2",)


def test_posisi_yang_sudah_punya_stop_tidak_dianggap_v1(siap: sqlite3.Connection) -> None:
    _kandidat_watchlist(siap, stop_awal=2_200)
    _beli(siap)

    hasil = _beli(siap, lembar=100, tanggal=date(2026, 7, 3))

    assert hasil.pelanggaran == ("V6",)  # pembelian kedua tetap tanpa rencana, tetapi bukan V1


# ---------------------------------------------------------------------------------------
# Penjualan & penutupan posisi
# ---------------------------------------------------------------------------------------


def test_menjual_lebih_banyak_daripada_dimiliki_ditolak(siap: sqlite3.Connection) -> None:
    _beli(siap, lembar=1_000)

    with pytest.raises(posisi.GalatPosisi, match="hanya memegang 1000 lembar"):
        posisi.catat_transaksi(
            siap, KODE, "jual", harga=CLOSE, lembar=1_100, mode="nyata", tanggal=date(2026, 7, 3)
        )


def test_menjual_tanpa_posisi_aktif_ditolak(siap: sqlite3.Connection) -> None:
    with pytest.raises(posisi.GalatPosisi, match="tidak ada posisi aktif"):
        posisi.catat_transaksi(
            siap, KODE, "jual", harga=CLOSE, lembar=100, mode="nyata", tanggal=date(2026, 7, 3)
        )


def test_menjual_seluruh_lembar_menutup_posisi(siap: sqlite3.Connection) -> None:
    _kandidat_watchlist(siap)
    _beli(siap, lembar=1_000)

    hasil = posisi.catat_transaksi(
        siap, KODE, "jual", harga=2_400, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 4)
    )

    assert hasil.posisi.status == "ditutup"
    assert hasil.posisi.tgl_tutup == "2026-07-04"
    assert hasil.posisi.stop_terkini == 2_180  # stop terakhir tetap tersimpan
    ringkasan = posisi.ringkasan(siap, hasil.posisi)
    assert ringkasan.lembar_terbuka == 0
    assert ringkasan.risiko_terbuka == 0
    assert ringkasan.hasil_terealisasi is not None
    assert posisi.risiko_terbuka(siap).total == 0


def test_menjual_sebagian_menyisakan_lembar_terbuka(siap: sqlite3.Connection) -> None:
    _kandidat_watchlist(siap)
    _beli(siap, lembar=1_000)

    hasil = posisi.catat_transaksi(
        siap, KODE, "jual", harga=2_400, lembar=400, mode="nyata", tanggal=date(2026, 7, 4)
    )

    assert hasil.posisi.status == "aktif"
    assert posisi.hitungan(siap, hasil.posisi.id_posisi).lembar_terbuka == 600


def test_penjualan_mewarisi_rencana_posisinya(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana)

    hasil = posisi.catat_transaksi(
        siap, KODE, "jual", harga=2_400, lembar=100, mode="nyata", tanggal=date(2026, 7, 4)
    )

    assert hasil.transaksi.id_rencana == rencana.id_rencana


def test_mode_yang_berbeda_tidak_tercampur(siap: sqlite3.Connection) -> None:
    """PRD 9.11: metrik kedua mode dilaporkan terpisah, jadi posisinya pun tidak boleh tercampur."""
    _beli(siap, mode="nyata")

    with pytest.raises(posisi.GalatPosisi, match="tidak ada posisi aktif"):
        posisi.catat_transaksi(
            siap, KODE, "jual", harga=CLOSE, lembar=100, mode="simulasi", tanggal=date(2026, 7, 3)
        )


def test_dua_posisi_satu_kode_menuntut_id_posisi(siap: sqlite3.Connection) -> None:
    """Dua posisi sah ada (mis. satu simulasi, satu nyata); menebak yang mana tidak boleh."""
    _beli(siap, mode="nyata", tanggal=date(2026, 7, 2))
    _beli(siap, mode="simulasi", tanggal=date(2026, 7, 3))
    with db.tulis(siap) as koneksi:
        # posisi kedua dibuat bermode nyata juga lewat jalur langsung, supaya kodenya sama-sama aktif
        koneksi.execute(
            "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, tgl_tutup, status, stop_terkini,"
            " id_rencana, mode, pelanggaran, catatan, sumber, diketahui_pada)"
            " VALUES (99, 1, 'AAAA', '2026-07-02', NULL, 'aktif', 2200, NULL, 'nyata', NULL, NULL,"
            " 'uji', '2026-07-02T09:00:00+07:00')"
        )

    with pytest.raises(posisi.GalatPosisi, match="sebutkan yang mana lewat --id-posisi"):
        _beli(siap, lembar=100, tanggal=date(2026, 7, 4))


# ---------------------------------------------------------------------------------------
# Biaya: dihitung dari tarif, ditandai asalnya, dan tidak pernah dikarang
# ---------------------------------------------------------------------------------------


def test_biaya_all_in_dihitung_dari_tarif_dan_ditandai(siap: sqlite3.Connection) -> None:
    """Beli 1.000 lembar @2.320: 0,15% × 2.320 = Rp 3,48 → dibulatkan ke atas Rp 4 per lembar."""
    hasil = _beli(siap, lembar=1_000)

    assert hasil.transaksi.biaya == 4_000
    assert hasil.transaksi.asal_biaya == "dihitung_dari_tarif"
    assert hasil.transaksi.pajak is None  # sisi beli tidak ada PPh


def test_pajak_penjualan_dipisahkan_hanya_bila_tarifnya_tidak_all_in(
    sambungan: sqlite3.Connection,
) -> None:
    """K23 dua arah: tarif all-in tidak dipisah, tarif biasa dipisah — keduanya diuji."""
    konfigurasi.simpan(
        sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_TANPA_PPH, PAJAK_PENJUALAN, SLIPPAGE_TICK)
    )
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber=SUMBER, emiten=EMITEN_UJI, harga_harian=_deret(KODE)),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    _beli(sambungan, lembar=1_000)
    jual = posisi.catat_transaksi(
        sambungan, KODE, "jual", harga=CLOSE, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 4)
    )

    # 0,25% × 2.320 = 5,8 → 6 per lembar broker + PPh 0,1% × 2.320 = 2,32 → 3 per lembar.
    assert jual.transaksi.biaya == 9_000
    assert jual.transaksi.pajak == 3_000
    assert jual.transaksi.pajak <= jual.transaksi.biaya


def test_tarif_all_in_tidak_menambahkan_pph_dua_kali(siap: sqlite3.Connection) -> None:
    """Terukur: 0,25% × 2.320 = Rp 5,8 → Rp 6 per lembar, bukan 6 + 3."""
    _beli(siap, lembar=1_000)
    jual = posisi.catat_transaksi(
        siap, KODE, "jual", harga=CLOSE, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 4)
    )

    assert jual.transaksi.biaya == 6_000
    assert jual.transaksi.pajak is None
    assert any("tidak dapat dipisahkan" in satu for satu in jual.catatan)


def test_biaya_yang_tidak_dapat_dihitung_dilaporkan_bukan_nol(
    sambungan: sqlite3.Connection,
) -> None:
    """Tanpa entri tarif broker, biayanya tidak diketahui — dan itu dikatakan, bukan diisi 0."""
    konfigurasi.simpan(sambungan, _urai(LOT_100, FRAKSI_HARGA, SLIPPAGE_TICK))
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber=SUMBER, emiten=EMITEN_UJI, harga_harian=_deret(KODE)),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )

    hasil = _beli(sambungan, lembar=1_000)

    assert hasil.transaksi.biaya is None
    assert hasil.transaksi.asal_biaya is None
    assert any("tidak dapat dihitung dari tarif" in satu for satu in hasil.catatan)
    ringkasan = posisi.ringkasan(sambungan, hasil.posisi)
    assert "belum mencatat biayanya" in (ringkasan.alasan_hasil or "")


def test_biaya_yang_dicatat_pengguna_dipakai_apa_adanya(siap: sqlite3.Connection) -> None:
    hasil = _beli(siap, lembar=1_000, biaya=12_345)

    assert hasil.transaksi.biaya == 12_345
    assert hasil.transaksi.asal_biaya == "dicatat_pengguna"


# ---------------------------------------------------------------------------------------
# Stop terkini: trailing boleh, menjauh dicatat sebagai V5
# ---------------------------------------------------------------------------------------


def test_stop_boleh_dinaikkan_tanpa_pelanggaran(siap: sqlite3.Connection) -> None:
    _kandidat_watchlist(siap, stop_awal=2_200)
    hasil = _beli(siap)

    perubahan = posisi.ubah_stop(siap, hasil.posisi.id_posisi, 2_260, tanggal=date(2026, 7, 3))

    assert perubahan.pelanggaran == ()
    assert perubahan.lama == 2_200
    assert perubahan.posisi.stop_terkini == 2_260


def test_stop_yang_diturunkan_mencatat_pelanggaran_v5(siap: sqlite3.Connection) -> None:
    """PRD 9.11: menggeser stop menjauhi harga dicatat sebagai pelanggaran V5."""
    _kandidat_watchlist(siap, stop_awal=2_200)
    hasil = _beli(siap)

    perubahan = posisi.ubah_stop(siap, hasil.posisi.id_posisi, 2_100, tanggal=date(2026, 7, 3))

    assert perubahan.pelanggaran == ("V5",)
    assert perubahan.posisi.pelanggaran == "V5"
    assert any("MENJAUHI harga" in satu for satu in perubahan.catatan)


def test_ubah_stop_pada_posisi_yang_sudah_ditutup_ditolak(siap: sqlite3.Connection) -> None:
    _kandidat_watchlist(siap)
    _beli(siap, lembar=1_000)
    hasil = posisi.catat_transaksi(
        siap, KODE, "jual", harga=2_400, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 4)
    )

    with pytest.raises(posisi.GalatPosisi, match="sudah ditutup"):
        posisi.ubah_stop(siap, hasil.posisi.id_posisi, 2_300)


def test_stop_di_atas_penutupan_terakhir_disebut(siap: sqlite3.Connection) -> None:
    _kandidat_watchlist(siap, stop_awal=2_200)
    hasil = _beli(siap)

    perubahan = posisi.ubah_stop(siap, hasil.posisi.id_posisi, 2_400, tanggal=date(2026, 7, 3))

    assert any("di ATAS penutupan terakhir" in satu for satu in perubahan.catatan)


# ---------------------------------------------------------------------------------------
# Risiko terbuka & hasil (diturunkan, bukan disimpan)
# ---------------------------------------------------------------------------------------


def test_risiko_terbuka_dari_penutupan_dan_stop(siap: sqlite3.Connection) -> None:
    """(2.320 − 2.180) × 1.000 lembar = Rp 140.000 (PRD 8.2)."""
    _kandidat_watchlist(siap, stop_awal=2_180)
    hasil = _beli(siap, lembar=1_000)

    ringkasan = posisi.ringkasan(siap, hasil.posisi)

    assert ringkasan.risiko_terbuka == 140_000
    assert ringkasan.harga is not None and ringkasan.harga.close == CLOSE


def test_risiko_terbuka_tidak_pernah_negatif(siap: sqlite3.Connection) -> None:
    """Harga di bawah stop berarti "minimal 0" — risiko yang sudah terjadi bukan risiko negatif."""
    _kandidat_watchlist(siap, stop_awal=2_200)
    hasil = _beli(siap, harga=2_100, lembar=1_000)
    posisi.ubah_stop(siap, hasil.posisi.id_posisi, 2_400, tanggal=date(2026, 7, 3))

    ringkasan = posisi.ringkasan(siap, posisi.wajib_ada(siap, hasil.posisi.id_posisi))

    assert ringkasan.posisi.stop_terkini == 2_400
    assert ringkasan.harga is not None and ringkasan.harga.close < 2_400
    assert ringkasan.risiko_terbuka == 0


def test_hasil_terealisasi_setelah_biaya(siap: sqlite3.Connection) -> None:
    """Beli 1.000 @2.320 (biaya 4.000), jual 1.000 @2.400 (biaya 6.000)."""
    _kandidat_watchlist(siap, stop_awal=2_200)
    _beli(siap, harga=2_320, lembar=1_000)
    hasil = posisi.catat_transaksi(
        siap, KODE, "jual", harga=2_400, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 4)
    )

    # (2.400 − 2.320) × 1.000 − 6.000 − 4.000 = 80.000 − 10.000
    assert posisi.ringkasan(siap, hasil.posisi).hasil_terealisasi == 70_000


def test_hasil_belum_terealisasi_memakai_penutupan_terakhir(siap: sqlite3.Connection) -> None:
    """Beli 1.000 @2.320 dengan biaya 4.000; penutupan terakhir 2.320 → hasil = −biaya beli."""
    _kandidat_watchlist(siap, stop_awal=2_200)
    hasil = _beli(siap, harga=2_320, lembar=1_000)

    assert posisi.ringkasan(siap, hasil.posisi).hasil_belum_terealisasi == -4_000


def test_posisi_tanpa_harga_menyebut_sebabnya(sambungan: sqlite3.Connection) -> None:
    """Kode yang tidak punya bar harga: risiko & hasilnya tidak dinilai, dengan alasan."""
    konfigurasi.simpan(
        sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_ALL_IN, PAJAK_PENJUALAN, SLIPPAGE_TICK)
    )
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=EMITEN_UJI,  # BBBB terdaftar sebagai emiten, tetapi tanpa bar harga
            harga_harian=_deret(KODE),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )

    hasil = _beli(sambungan, KODE_LAIN, lembar=1_000, biaya=0)
    posisi.ubah_stop(sambungan, hasil.posisi.id_posisi, 2_100, tanggal=date(2026, 7, 3))
    ringkasan = posisi.ringkasan(sambungan, posisi.wajib_ada(sambungan, hasil.posisi.id_posisi))

    assert ringkasan.harga is None
    assert ringkasan.risiko_terbuka is None
    assert "tidak ada penutupan terakhir" in (ringkasan.alasan_risiko or "")
    assert ringkasan.hasil_belum_terealisasi is None
    assert posisi.risiko_terbuka(sambungan).tidak_dinilai


def test_harga_terakhir_hanya_dari_satu_label_sumber(siap: sqlite3.Connection) -> None:
    """T32: label dengan riwayat terbanyak yang dipakai; pembandingnya tidak mencampuri."""
    _beli(siap, lembar=1_000)
    ingesti.simpan(
        siap,
        KumpulanData(
            sumber=SUMBER_LAIN,
            harga_harian=(
                HargaHarian(
                    kode=KODE,
                    tanggal=TANGGAL + timedelta(days=1),
                    open=9_000,
                    high=9_010,
                    low=8_990,
                    close=9_000,
                    volume=1_000,
                    nilai=9_000_000,
                    penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
                ),
            ),
        ),
        tanggal_data=TANGGAL + timedelta(days=1),
        momen=MOMEN,
    )

    harga = posisi.harga_terakhir(siap, [KODE])

    assert harga[KODE].close == CLOSE  # label dominan (24 bar) tetap yang dipakai
    assert harga[KODE].sumber == SUMBER


# ---------------------------------------------------------------------------------------
# AC-6: risiko berjalan = posisi aktif + rencana belum dieksekusi
# ---------------------------------------------------------------------------------------


def test_risiko_berjalan_menjumlahkan_posisi_dan_rencana_belum_dieksekusi(
    siap: sqlite3.Connection,
) -> None:
    rencana = _rencana(siap, KODE_LAIN)
    _kandidat_watchlist(siap, KODE, stop_awal=2_180)
    hasil = _beli(siap, KODE, lembar=1_000)

    lengkap = risiko.risiko_berjalan_lengkap(siap)

    assert lengkap.dari_posisi == 140_000
    assert lengkap.dari_rencana == rencana.risiko_nominal
    assert lengkap.total == 140_000 + rencana.risiko_nominal
    assert lengkap.jumlah_rencana_belum == 1
    assert lengkap.lengkap


def test_rencana_yang_sudah_dieksekusi_tidak_dihitung_dua_kali(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, lembar=1_000)

    lengkap = risiko.risiko_berjalan_lengkap(siap)

    assert lengkap.dari_rencana == 0
    assert lengkap.jumlah_rencana_belum == 0
    # Stopnya dari rencana (harga masuk − 2 × ATR14 = 2.320 − 80 = 2.240), bukan dari tesis.
    assert lengkap.dari_posisi == (CLOSE - 2_240) * 1_000


def test_risiko_berjalan_melaporkan_suku_yang_tidak_dapat_dinilai(
    siap: sqlite3.Connection,
) -> None:
    _beli(siap, lembar=1_000)  # tanpa stop -> V1

    lengkap = risiko.risiko_berjalan_lengkap(siap)

    assert lengkap.jumlah_posisi_aktif == 1
    assert lengkap.jumlah_posisi_dinilai == 0
    assert not lengkap.lengkap
    assert any("tanpa stop" in satu for satu in lengkap.tidak_dinilai)
    assert "TIDAK DINILAI" in lengkap.ringkas()


def test_kalkulator_risiko_memakai_risiko_berjalan_yang_lengkap(siap: sqlite3.Connection) -> None:
    """Masukan kalkulator membaca suku posisi, dan menyebut suku yang tidak dapat dinilai."""
    _kandidat_watchlist(siap, KODE, stop_awal=2_180)
    _beli(siap, KODE, lembar=1_000)
    _kandidat_watchlist(siap, KODE_LAIN, stop_awal=2_180)

    masukan = risiko.siapkan_masukan(siap, KODE_LAIN, pada=date(2026, 7, 3))

    assert masukan.risiko_berjalan == 140_000
    assert any("posisi #1" in satu for satu in masukan.rincian_risiko_berjalan)


# ---------------------------------------------------------------------------------------
# AC-13: ekuitas harian, arus dana, drawdown
# ---------------------------------------------------------------------------------------


def _ekuitas(sambungan: sqlite3.Connection, tanggal: date, ekuitas: int, **ganti: object) -> None:
    argumen: dict[str, object] = {"ekuitas": ekuitas, "tanggal": tanggal, "mode": "nyata"}
    argumen.update(ganti)
    risiko.catat_ekuitas(sambungan, **argumen)  # type: ignore[arg-type]


def test_setoran_tidak_mengubah_drawdown(sambungan: sqlite3.Connection) -> None:
    """Deret yang membedakan jawaban mentah dan terkoreksi: setoran 50 juta **disusul** rugi 10%."""
    _ekuitas(sambungan, date(2026, 7, 1), 100_000_000, arus_dana=0)
    _ekuitas(sambungan, date(2026, 7, 2), 140_000_000, arus_dana=50_000_000)

    dd = risiko.drawdown(sambungan)

    assert dd.terkoreksi
    assert dd.drawdown_bp == 1_000  # 10%: (100jt × 0,9) = 90jt dari puncak 100jt
    assert dd.mentah_bp == 0  # tanpa koreksi, setoran terbaca sebagai kenaikan


def test_penarikan_tidak_terbaca_sebagai_penurunan(sambungan: sqlite3.Connection) -> None:
    _ekuitas(sambungan, date(2026, 7, 1), 100_000_000, arus_dana=0)
    _ekuitas(sambungan, date(2026, 7, 2), 60_000_000, arus_dana=-40_000_000)

    dd = risiko.drawdown(sambungan)

    assert dd.terkoreksi
    assert dd.drawdown_bp == 0
    assert dd.mentah_bp == 4_000  # mentah: 40% — persis angka yang menyesatkan


def test_drawdown_maksimum_diambil_dari_seluruh_deret(sambungan: sqlite3.Connection) -> None:
    _ekuitas(sambungan, date(2026, 7, 1), 100_000_000, arus_dana=0)
    _ekuitas(sambungan, date(2026, 7, 2), 80_000_000, arus_dana=0)
    _ekuitas(sambungan, date(2026, 7, 3), 95_000_000, arus_dana=0)

    dd = risiko.drawdown(sambungan)

    assert dd.drawdown_bp == 500  # 5% dari puncak 100 juta
    assert dd.drawdown_maksimum_bp == 2_000  # 20% di titik terendah


def test_drawdown_terkoreksi_tidak_dapat_dinilai_tanpa_arus_dana(
    sambungan: sqlite3.Connection,
) -> None:
    _ekuitas(sambungan, date(2026, 7, 1), 100_000_000)
    _ekuitas(sambungan, date(2026, 7, 2), 90_000_000)

    dd = risiko.drawdown(sambungan)

    assert not dd.terkoreksi
    assert dd.drawdown_bp is None
    assert "2026-07-02" in (dd.alasan or "")
    assert dd.mentah_bp == 1_000  # yang mentah tetap dilaporkan, dengan labelnya


def test_arus_dana_nol_dan_belum_dicatat_berbeda(sambungan: sqlite3.Connection) -> None:
    """0 = "benar-benar tidak ada", NULL = "belum dicatat" (pola K22/T35)."""
    _ekuitas(sambungan, date(2026, 7, 1), 100_000_000, arus_dana=0)
    _ekuitas(sambungan, date(2026, 7, 2), 100_000_000, arus_dana=None)

    deret = risiko.deret_ekuitas(sambungan)

    assert [satu.arus_dana for satu in deret] == [0, None]
    assert risiko.drawdown(sambungan).terkoreksi is False


def test_arus_dana_baris_pertama_tidak_menghalangi_koreksi(sambungan: sqlite3.Connection) -> None:
    """Baris pertama titik acuan: arus dananya tidak pernah masuk rumus, jadi tidak dituntut."""
    _ekuitas(sambungan, date(2026, 7, 1), 100_000_000, arus_dana=None)
    _ekuitas(sambungan, date(2026, 7, 2), 90_000_000, arus_dana=0)

    dd = risiko.drawdown(sambungan)

    assert dd.terkoreksi
    assert dd.drawdown_bp == 1_000


def test_mode_yang_tidak_dikenal_pada_ekuitas_ditolak(sambungan: sqlite3.Connection) -> None:
    with pytest.raises(risiko.GalatRisiko, match="mode 'karangan' tidak dikenal"):
        _ekuitas(sambungan, date(2026, 7, 1), 100_000_000, mode="karangan")


# ---------------------------------------------------------------------------------------
# Mode kepala (AC-11)
# ---------------------------------------------------------------------------------------


def test_cli_catat_transaksi_lalu_menampilkan_posisi(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    _kandidat_watchlist(siap, stop_awal=2_180)

    kode = cli.main(
        [
            "--catat-transaksi",
            KODE,
            "--aksi",
            "beli",
            "--lembar",
            "1000",
            "--harga",
            str(CLOSE),
            "--mode",
            "nyata",
            "--tanggal",
            "2026-07-02",
        ]
    )
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "posisi AAAA #1" in keluaran
    assert "stop Rp 2.180" in keluaran

    kode = cli.main(["--posisi"])
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "risiko terbuka" in keluaran
    assert "Rp 140.000" in keluaran


def test_cli_catat_transaksi_tanpa_mode_ditolak(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(
        ["--catat-transaksi", KODE, "--aksi", "beli", "--lembar", "1000", "--harga", str(CLOSE)]
    )
    galat = capsys.readouterr().err

    assert kode == cli.KODE_GAGAL
    assert "--mode" in galat


def test_cli_ubah_stop_menolak_tanpa_id_posisi(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(["--ubah-stop", "--stop", "2200"])

    assert kode == cli.KODE_GAGAL
    assert "--id-posisi" in capsys.readouterr().err


def test_cli_ekuitas_harian_menyimpan_arus_dana_dan_mode(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(
        [
            "--ekuitas-harian",
            "260000000",
            "--kas",
            "120000000",
            "--arus-dana",
            "10000000",
            "--mode",
            "nyata",
            "--tanggal-ekuitas",
            "2026-07-02",
        ]
    )
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "arus dana: 10000000" in keluaran
    assert "mode: nyata" in keluaran
    assert risiko.ekuitas_terakhir(siap).arus_dana == 10_000_000
