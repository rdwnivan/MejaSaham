"""Uji jurnal keputusan & rekap kepatuhan (F7, PRD 9.8/11.5/13.1/13.2) — `mejasaham/jurnal.py`.

Yang dijaga berkas ini adalah **angka kepatuhan**, bukan tampilannya:

* **Setiap kode pelanggaran dibaca dari satu tempat** (T44). V1/V2/V6 dari baris transaksi, V5
  dari baris posisi, V3/V4/V7 diturunkan — dan tidak ada kode yang bisa terhitung dua kali.
* **Pelanggaran yang tidak bisa diatribusikan tidak mengubah rasio**, tetapi tetap dilaporkan.
* **Yang tidak dapat dinilai disebut** (aturan keras 2): V4 tanpa penutupan, putaran tanpa 1R,
  hasil yang biayanya belum lengkap, dan expectancy di bawah 30 putaran.
* **Jurnal tidak menimpa**: catatan menambah revisi, dan mesin menolak baris kosong, UPDATE, serta
  dua rantai jurnal untuk satu transaksi.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest

from mejasaham import (
    cli,
    dasbor,
    db,
    ingesti,
    jurnal,
    kandidat,
    konfigurasi,
    lokasi,
    posisi,
    risiko,
    tampilan,
)
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    HargaHarian,
    KumpulanData,
)

SUMBER = "uji-jurnal"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
KODE = "AAAA"
KODE_LAIN = "BBBB"
SEKTOR = "industri"
LOT = 100

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

SLIPPAGE_TICK = """
[[slippage]]
mode          = "tick"
nilai         = 1
berlaku_sejak = 2026-01-02
sumber        = "Keputusan produk K20 (uji)"
dicatat_pada  = 2026-10-06
"""

BROKER_ALL_IN = """
[[biaya_broker]]
nama          = "Broker All-in"
sisi_beli     = { persen = 0.15 }
sisi_jual     = { persen = 0.25 }
sudah_termasuk = ["pph_penjualan", "levy", "ppn"]
berlaku_sejak = 2026-01-02
sumber        = "Halaman tarif resmi broker (uji)"
dicatat_pada  = 2026-10-06
"""


def _urai(*blok: str) -> tuple[konfigurasi.EntriParameter, ...]:
    return konfigurasi.urai("skema = 1\n\n" + "\n\n".join(blok), asal="uji")


def _deret(kode: str, *, close: int = CLOSE, hari: int = HARI) -> tuple[HargaHarian, ...]:
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
def data(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    """KODE_LAIN sengaja **tanpa** bar harga: uji V4 memakainya sebagai "tidak dapat dinilai"."""
    konfigurasi.simpan(sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_ALL_IN, SLIPPAGE_TICK))
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=EMITEN_UJI,
            harga_harian=_deret(KODE),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    return sambungan


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


def _kandidat(
    sambungan: sqlite3.Connection,
    kode: str = KODE,
    *,
    stop_awal: int = 2_180,
    harga_pembatal: int | None = None,
    dicatat_pada: str | None = None,
) -> kandidat.Kandidat:
    return kandidat.buat(
        sambungan,
        kode,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        harga_pembatal=harga_pembatal,
        horizon="1 bulan",
        stop_awal=stop_awal,
        tanggal_tinjau="2026-08-01",
        dicatat_pada=dicatat_pada,
    )


def _rencana(
    sambungan: sqlite3.Connection, kode: str = KODE, *, ukuran: int | None = None, **ganti: int
) -> risiko.Rencana:
    entri = _kandidat(sambungan, kode)
    masukan = risiko.siapkan_masukan(sambungan, kode, pada=date(2026, 7, 1))
    hasil, _stop = risiko.hitung_untuk(masukan, harga_masuk=ganti.get("harga_masuk", CLOSE))
    if ukuran is not None:
        hasil = risiko.pakai_ukuran(hasil, ukuran, lot=LOT, batas_total_bp=500)
    return risiko.simpan(
        sambungan,
        hasil,
        id_kandidat=entri.id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
        pelanggaran_diterima=bool(hasil.pelanggaran),
    )


def _beli(
    sambungan: sqlite3.Connection, kode: str = KODE, **ganti: object
) -> posisi.PendaftaranTransaksi:
    argumen: dict[str, object] = {
        "harga": CLOSE,
        "lembar": 1_000,
        "mode": "nyata",
        "tanggal": date(2026, 7, 2),
    }
    argumen.update(ganti)
    return posisi.catat_transaksi(sambungan, kode, "beli", **argumen)  # type: ignore[arg-type]


def _jual(
    sambungan: sqlite3.Connection, kode: str = KODE, **ganti: object
) -> posisi.PendaftaranTransaksi:
    argumen: dict[str, object] = {
        "harga": CLOSE,
        "lembar": 1_000,
        "mode": "nyata",
        "tanggal": date(2026, 7, 6),
    }
    argumen.update(ganti)
    return posisi.catat_transaksi(sambungan, kode, "jual", **argumen)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------
# Katalog & penjaga mesin
# ---------------------------------------------------------------------------------------


def test_katalog_tujuh_kode_punya_satu_tempat_deteksi_masing_masing() -> None:
    """Katalog PRD 9.8 lengkap, dan tiap kode punya **satu** tempat deteksi yang disebut."""
    assert sorted(jurnal.KATALOG) == ["V1", "V2", "V3", "V4", "V5", "V6", "V7"]
    assert set(jurnal.DIDETEKSI_DI) == set(jurnal.KATALOG)
    # Katalognya **dipinjam** dari posisi.py: dua daftar terpisah akan membuat kode yang sah di
    # satu tempat tidak dikenal di tempat lain.
    assert jurnal.KATALOG == dict(posisi.PELANGGARAN)
    assert not hasattr(posisi, "PELANGGARAN_BELUM_DIHITUNG")


def test_baris_jurnal_kosong_ditolak_mesin(siap: sqlite3.Connection) -> None:
    """Baris jurnal tanpa isi tidak mencatat apa pun — dan itu dijaga CHECK, bukan disiplin."""
    _beli(siap, id_rencana=_rencana(siap).id_rencana)

    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(siap) as koneksi:
            koneksi.execute(
                "INSERT INTO jurnal (id_jurnal, revisi, id_transaksi, sumber, diketahui_pada)"
                " VALUES (1, 1, 1, 'uji', '2026-07-03T09:00:00+07:00')"
            )


def test_jurnal_append_only_menolak_perubahan(siap: sqlite3.Connection) -> None:
    """PRD 9.8: tidak ada penghapusan senyap — versi lama disimpan, bukan ditimpa."""
    _beli(siap, id_rencana=_rencana(siap).id_rencana)
    jurnal.catat(siap, 1, pelajaran="jangan menambah posisi rugi")

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with db.tulis(siap) as koneksi:
            koneksi.execute("UPDATE jurnal SET pelajaran = 'lain' WHERE id_jurnal = 1")


def test_satu_transaksi_hanya_boleh_punya_satu_rantai_jurnal(siap: sqlite3.Connection) -> None:
    """Dua rantai untuk satu keputusan akan menyebar "pelajaran"-nya ke dua tempat."""
    _beli(siap, id_rencana=_rencana(siap).id_rencana)
    jurnal.catat(siap, 1, alasan="alasan pertama")

    with pytest.raises(sqlite3.IntegrityError, match="SATU rantai jurnal"):
        with db.tulis(siap) as koneksi:
            koneksi.execute(
                "INSERT INTO jurnal (id_jurnal, revisi, id_transaksi, alasan, sumber,"
                " diketahui_pada) VALUES (2, 1, 1, 'rantai kedua', 'uji',"
                " '2026-07-04T09:00:00+07:00')"
            )


def test_catatan_menambah_revisi_dan_tidak_menghapus_isi_sebelumnya(siap: sqlite3.Connection) -> None:
    _beli(siap, id_rencana=_rencana(siap).id_rencana)

    pertama = jurnal.catat(siap, 1, alasan="sesuai rencana")
    kedua = jurnal.catat(siap, 1, pelajaran="stop terlalu jauh")

    assert (pertama.id_jurnal, pertama.revisi) == (1, 1)
    assert (kedua.id_jurnal, kedua.revisi) == (1, 2)
    assert kedua.alasan == "sesuai rencana", "revisi tidak boleh menghapus alasan yang sudah ada"
    assert kedua.pelajaran == "stop terlalu jauh"
    riwayat = jurnal.riwayat_catatan(siap, 1)
    assert [satu.revisi for satu in riwayat] == [1, 2]
    assert riwayat[0].pelajaran is None


def test_catatan_untuk_transaksi_yang_tidak_ada_ditolak_berisik(siap: sqlite3.Connection) -> None:
    with pytest.raises(jurnal.GalatJurnal, match="transaksi #9 tidak ada"):
        jurnal.catat(siap, 9, alasan="apa saja")


def test_catatan_kosong_ditolak(siap: sqlite3.Connection) -> None:
    _beli(siap, id_rencana=_rencana(siap).id_rencana)

    with pytest.raises(jurnal.GalatJurnal, match="kosong"):
        jurnal.catat(siap, 1)


# ---------------------------------------------------------------------------------------
# V1/V2/V6 — dibaca dari baris transaksi
# ---------------------------------------------------------------------------------------


def test_v6_dan_v1_dibaca_dari_baris_transaksi(siap: sqlite3.Connection) -> None:
    """Beli tanpa rencana tersimpan: V6 + V1, dan keduanya muncul di jurnal."""
    _beli(siap, id_rencana=None, lembar=100)

    baris = jurnal.baris(siap)
    kode = baris[0].kode_pelanggaran

    assert kode == ("V1", "V6")
    assert not baris[0].patuh
    teks = baris[0].ringkas()
    assert "V1 (masuk tanpa stop awal)" in teks
    assert "V6 (transaksi tanpa rencana tersimpan)" in teks


def test_pelanggaran_yang_sama_tidak_dihitung_dua_kali(siap: sqlite3.Connection) -> None:
    """V1 ada di baris transaksi — dan **tidak** ditambahkan lagi dari baris posisi."""
    _beli(siap, id_rencana=None, lembar=100)

    laporan = jurnal.rekap(siap)

    assert laporan.hitungan_per_kode == (("V1", 1), ("V6", 1))
    assert len(laporan.pelanggaran) == 2
    assert all(satu.id_transaksi == 1 for satu in laporan.pelanggaran)


def test_v2_menyebut_angka_rencana_dan_lembar_posisi(siap: sqlite3.Connection) -> None:
    """V2 harus bisa diperiksa: angkanya disebut, bukan hanya kodenya."""
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, lembar=rencana.lembar, tanggal=date(2026, 7, 2))
    _beli(siap, id_rencana=rencana.id_rencana, lembar=100, tanggal=date(2026, 7, 3))

    pelanggaran = [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V2"]

    assert len(pelanggaran) == 1
    assert f"rencana #{rencana.id_rencana}" in pelanggaran[0].sebab
    assert f"{rencana.lembar + 100:,}".replace(",", ".") in pelanggaran[0].sebab


# ---------------------------------------------------------------------------------------
# V5 — dibaca dari baris posisi
# ---------------------------------------------------------------------------------------


def test_v5_dibaca_dari_baris_posisi_dan_diatribusikan_ke_transaksinya(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))
    posisi.ubah_stop(siap, 1, 2_000, tanggal=date(2026, 7, 3))

    pelanggaran = [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V5"]

    assert len(pelanggaran) == 1
    assert pelanggaran[0].id_transaksi == 1
    assert pelanggaran[0].tanggal == "2026-07-03"
    assert "Rp 2.240" in pelanggaran[0].sebab and "Rp 2.000" in pelanggaran[0].sebab
    assert pelanggaran[0].dideteksi_di == jurnal.DIDETEKSI_DI["V5"]


def test_v5_dihitung_sekali_per_posisi_walau_stop_diturunkan_dua_kali(siap: sqlite3.Connection) -> None:
    """Batas yang **diketahui**: kolomnya menyimpan kode, bukan peristiwa (lihat docstring modul)."""
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))
    posisi.ubah_stop(siap, 1, 2_000, tanggal=date(2026, 7, 3))
    posisi.ubah_stop(siap, 1, 1_900, tanggal=date(2026, 7, 4))

    pelanggaran = [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V5"]

    assert len(pelanggaran) == 1, "dua peristiwa V5 terbaca sebagai satu kode — dan itu dikatakan"


# ---------------------------------------------------------------------------------------
# V3 — dari angka rencana yang dieksekusi
# ---------------------------------------------------------------------------------------


def test_v3_dari_batas_bobot_dan_diatribusikan_ke_transaksi_pelaksananya(
    siap: sqlite3.Connection,
) -> None:
    """Rencana yang ukurannya dinaikkan pengguna melewati batas bobot (PRD 9.7/9.8)."""
    rencana = _rencana(siap, ukuran=11_000)
    assert rencana.lembar == 11_000
    _beli(siap, id_rencana=rencana.id_rencana, lembar=11_000)

    pelanggaran = [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V3"]

    assert len(pelanggaran) == 1
    assert pelanggaran[0].id_transaksi == 1
    assert "bobot" in pelanggaran[0].sebab
    assert "melebihi batas" in pelanggaran[0].sebab


def test_rencana_patuh_tidak_menghasilkan_v3(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana)

    assert [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V3"] == []


def test_v3_rencana_yang_belum_dieksekusi_tidak_mengubah_rasio(siap: sqlite3.Connection) -> None:
    """Penyebutnya transaksi (PRD 9.8): rencana yang tak dieksekusi dilaporkan, bukan dihitung."""
    _rencana(siap, ukuran=11_000)
    _beli(siap, id_rencana=None, lembar=100)  # satu transaksi, patuh kecuali V1/V6

    laporan = jurnal.rekap(siap)
    v3 = [satu for satu in laporan.di_luar_periode if satu.kode == "V3"]

    assert len(v3) == 1 and v3[0].id_transaksi is None
    assert "BELUM dieksekusi" in v3[0].sebab
    assert all(satu.kode != "V3" for satu in laporan.pelanggaran)
    assert "Di luar periode/tanpa transaksi" in laporan.ringkas()


# ---------------------------------------------------------------------------------------
# V4 — menambah posisi rugi tanpa tesis baru
# ---------------------------------------------------------------------------------------


def _posisi_rugi_ditambah(siap: sqlite3.Connection) -> posisi.PendaftaranTransaksi:
    """Beli di 3.000 saat penutupan 2.320, lalu tambah lagi — posisinya rugi saat ditambah."""
    _kandidat(siap, stop_awal=2_900)
    _beli(siap, id_rencana=None, harga=3_000, lembar=100, tanggal=date(2026, 7, 2))
    return _beli(siap, id_rencana=None, harga=2_900, lembar=100, tanggal=date(2026, 7, 3))


def test_v4_menambah_posisi_rugi_tanpa_tesis_baru(siap: sqlite3.Connection) -> None:
    _posisi_rugi_ditambah(siap)

    pelanggaran = [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V4"]

    assert len(pelanggaran) == 1
    assert pelanggaran[0].id_transaksi == 2
    assert "rata-rata Rp 3.000" in pelanggaran[0].sebab
    assert "penutupan Rp 2.320" in pelanggaran[0].sebab
    assert "tanpa tesis baru" in pelanggaran[0].sebab


def test_v4_tidak_berlaku_bila_tesis_diperbarui_lebih_dulu(siap: sqlite3.Connection) -> None:
    """Tesis baru sesudah transaksi sebelumnya — persis yang dituntut PRD 9.8."""
    entri = _kandidat(siap, stop_awal=2_900)
    pertama = _beli(siap, id_rencana=None, harga=3_000, lembar=100, tanggal=date(2026, 7, 2))
    # Revisi tesis yang dicatat **sesudah** transaksi pertama; stempelnya dihitung dari stempel
    # transaksinya supaya ujinya tidak bergantung pada jam mesin.
    setelah = (
        datetime.fromisoformat(pertama.transaksi.diketahui_pada) + timedelta(minutes=1)
    ).isoformat()
    kandidat.ubah(
        siap,
        entri.id_kandidat,
        {"tesis": "ditinjau ulang: harga sudah diskon"},
        dicatat_pada=setelah,
    )
    _beli(siap, id_rencana=None, harga=2_900, lembar=100, tanggal=date(2026, 7, 3))

    assert [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V4"] == []


def test_v4_tidak_berlaku_untuk_pembelian_pertama(siap: sqlite3.Connection) -> None:
    """Membuka posisi yang harganya di bawah stop bukan "menambah posisi rugi"."""
    _kandidat(siap, stop_awal=2_900)
    _beli(siap, id_rencana=None, harga=3_000, lembar=100, tanggal=date(2026, 7, 2))

    assert [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V4"] == []


def test_v4_tanpa_penutupan_pada_tanggal_itu_dinyatakan_tidak_dapat_dinilai(
    siap: sqlite3.Connection,
) -> None:
    """KODE_LAIN sengaja tanpa bar harga: V4 tidak dapat diperiksa, dan itu dikatakan."""
    _kandidat(siap, KODE_LAIN, stop_awal=2_900)
    _beli(siap, KODE_LAIN, id_rencana=None, harga=3_000, lembar=100, tanggal=date(2026, 7, 2))
    _beli(siap, KODE_LAIN, id_rencana=None, harga=2_900, lembar=100, tanggal=date(2026, 7, 3))

    laporan = jurnal.rekap(siap)
    tak_dinilai = [satu for satu in laporan.tak_dinilai if satu.kode == "V4"]

    assert [satu for satu in laporan.pelanggaran if satu.kode == "V4"] == []
    assert len(tak_dinilai) == 1
    assert "tidak dapat diperiksa" in tak_dinilai[0].sebab
    assert "Tidak dapat dinilai" in laporan.ringkas()


def test_v4_membandingkan_dalam_basis_yang_sama_melewati_split(siap: sqlite3.Connection) -> None:
    """Split di antara dua pembelian tidak boleh membuat posisi yang **untung** tampak rugi."""
    _kandidat(siap, stop_awal=2_900)
    _beli(siap, id_rencana=None, harga=3_000, lembar=100, tanggal=date(2026, 7, 2))
    with db.tulis(siap) as koneksi:
        koneksi.execute(
            "INSERT INTO aksi_korporasi (kode, tanggal, jenis, rasio_lama, rasio_baru, sumber,"
            " diketahui_pada)"
            " VALUES (?, '2026-07-03', 'split', 1, 2, 'uji', '2026-07-03T08:00:00+07:00')",
            (KODE,),
        )
    _beli(siap, id_rencana=None, harga=1_400, lembar=200, tanggal=date(2026, 7, 4))

    # Harga rata sebelum = 3.000 dalam basis lama; setelah split 1:2 menjadi 1.500 dalam basis
    # sekarang, sedangkan penutupan 2.320 juga dibagi dua → 1.160. Jadi memang rugi — V4 berlaku,
    # dan yang penting: perbandingannya dilakukan dalam **satu** basis, bukan 3.000 vs 1.160.
    pelanggaran = [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V4"]

    assert len(pelanggaran) == 1
    assert "rata-rata Rp 1.500" in pelanggaran[0].sebab
    assert "penutupan Rp 1.160" in pelanggaran[0].sebab


# ---------------------------------------------------------------------------------------
# V7 — pembatal tesis terpicu
# ---------------------------------------------------------------------------------------


def test_v7_dari_pembatal_tesis_yang_terpicu(siap: sqlite3.Connection) -> None:
    _kandidat(siap, harga_pembatal=2_400, stop_awal=2_180)
    _beli(siap, id_rencana=None, lembar=100)

    pelanggaran = [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V7"]

    assert len(pelanggaran) == 1
    assert pelanggaran[0].id_transaksi == 1
    assert "harga pembatal tesis Rp 2.400" in pelanggaran[0].sebab
    # Aturannya satu tempat: dasbor memakai temuan yang sama.
    temuan = dasbor.pembatal_terpicu(siap, posisi.ringkasan_semua(siap, status="aktif"))
    assert [satu.kode for satu in temuan] == [KODE]


def test_v7_tidak_berlaku_bila_penutupan_di_atas_pembatal(siap: sqlite3.Connection) -> None:
    _kandidat(siap, harga_pembatal=2_000, stop_awal=2_180)
    _beli(siap, id_rencana=None, lembar=100)

    assert [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V7"] == []


def test_v7_tidak_berlaku_untuk_posisi_yang_sudah_ditutup(siap: sqlite3.Connection) -> None:
    """VI "dipertahankan" hanya berlaku pada posisi yang masih terbuka (lihat docstring modul)."""
    _kandidat(siap, harga_pembatal=2_400, stop_awal=2_180)
    _beli(siap, id_rencana=None, lembar=100)
    _jual(siap, lembar=100, tanggal=date(2026, 7, 6))

    assert [satu for satu in jurnal.rekap(siap).pelanggaran if satu.kode == "V7"] == []


# ---------------------------------------------------------------------------------------
# Rasio kepatuhan & rekap
# ---------------------------------------------------------------------------------------


def test_kepatuhan_adalah_transaksi_tanpa_pelanggaran_dibagi_seluruh_transaksi(
    siap: sqlite3.Connection,
) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))
    _jual(siap, lembar=1_000, tanggal=date(2026, 7, 3))
    _beli(siap, id_rencana=None, lembar=100, tanggal=date(2026, 7, 6))  # V1 + V6

    laporan = jurnal.rekap(siap)

    assert laporan.jumlah_keputusan == 3
    assert laporan.jumlah_patuh == 2
    assert laporan.persen_patuh == Fraction(200, 3)
    assert "patuh 2 (66,67%)" in laporan.ringkas()


def test_rekap_memisahkan_mode_simulasi_dan_nyata(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, mode="nyata", tanggal=date(2026, 7, 2))
    _beli(siap, id_rencana=None, mode="simulasi", lembar=100, tanggal=date(2026, 7, 3))

    laporan = jurnal.rekap(siap)

    assert laporan.per_mode == (("nyata", 1, 1), ("simulasi", 1, 0))
    assert "Mode simulasi" in laporan.ringkas()
    assert jurnal.rekap(siap, mode="nyata").jumlah_keputusan == 1


def test_rekap_bulanan_hanya_menghitung_keputusan_bulan_itu(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))
    # Kode lain supaya posisinya baru (bukan menambah posisi Juli) -> V1 + V6 di bulan Agustus.
    _beli(siap, KODE_LAIN, id_rencana=None, lembar=100, tanggal=date(2026, 8, 3))

    juli = jurnal.rekap(siap, bulan="2026-07")
    agustus = jurnal.rekap(siap, bulan="2026-08")
    seluruh = jurnal.rekap(siap)

    assert (juli.jumlah_keputusan, juli.jumlah_patuh) == (1, 1)
    assert (agustus.jumlah_keputusan, agustus.jumlah_patuh) == (1, 0)
    assert seluruh.jumlah_keputusan == 2
    assert seluruh.per_bulan == (
        ("2026-07", 1, 1, 0, 0),
        ("2026-08", 1, 0, 2, 0),
    )


def test_bulan_yang_tidak_dikenal_ditolak(siap: sqlite3.Connection) -> None:
    with pytest.raises(jurnal.GalatJurnal, match="YYYY-MM"):
        jurnal.rekap(siap, bulan="Juli 2026")


def test_kelengkapan_tesis_menuntut_tesis_pembatal_dan_stop(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))
    # Kode lain: posisi baru tanpa rencana, jadi tanpa tesis (V1 + V6) — dan itu tidak lengkap.
    _beli(siap, KODE_LAIN, id_rencana=None, lembar=100, tanggal=date(2026, 7, 3))

    laporan = jurnal.rekap(siap)

    assert laporan.lengkap_tesis == (1, 2)
    assert "Kelengkapan tesis     : 1 dari 2 keputusan" in laporan.ringkas()


# ---------------------------------------------------------------------------------------
# Expectancy dalam R (PRD 8.2/13.2)
# ---------------------------------------------------------------------------------------


def _putaran_tertutup(siap: sqlite3.Connection, *, jual: int) -> risiko.Rencana:
    """Putaran lengkap; 1R-nya = `risiko_nominal` rencana yang dieksekusi (PRD 8.2)."""
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, harga=CLOSE, lembar=rencana.lembar,
          tanggal=date(2026, 7, 2))
    _jual(siap, harga=jual, lembar=rencana.lembar, tanggal=date(2026, 7, 3))
    return rencana


def test_expectancy_dihitung_per_putaran_tertutup_dalam_kelipatan_r(
    siap: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Expectancy = rata-rata (hasil ÷ 1R) atas putaran tertutup. Ambang 30 diturunkan di sini."""
    rencana = _putaran_tertutup(siap, jual=2_500)
    monkeypatch.setattr(jurnal, "BATAS_PUTARAN_DINILAI", 1)

    laporan = jurnal.rekap(siap)
    satu = laporan.putaran_dinilai[0]

    # 1R = risiko nominal rencana, apa adanya dari baris yang tersimpan (PRD 8.2).
    assert satu.r_posisi == Fraction(rencana.risiko_nominal)
    # Hasil dihitung dari tarif entri uji (0,15% beli / 0,25% jual, all-in), dibulatkan KE ATAS
    # per lembar seperti PRD 9.7: 0,15% × 2.320 = 3,48 → Rp 4; 0,25% × 2.500 = 6,25 → Rp 7.
    harapan = (2_500 - CLOSE) * rencana.lembar - (4 + 7) * rencana.lembar
    assert satu.hasil == harapan
    assert satu.hasil_r == Fraction(harapan, rencana.risiko_nominal)
    assert laporan.expectancy_r == satu.hasil_r
    assert laporan.alasan_expectancy is None
    assert "R per putaran tertutup (1 putaran" in laporan.ringkas()


def test_expectancy_belum_dapat_dinilai_di_bawah_ambang_dengan_angka_sementara(
    siap: sqlite3.Connection,
) -> None:
    _putaran_tertutup(siap, jual=2_500)

    laporan = jurnal.rekap(siap)
    teks = laporan.ringkas()

    assert laporan.expectancy_r is not None, "angkanya tetap dihitung, hanya belum dinilai"
    assert laporan.alasan_expectancy is not None
    assert "1 dari 30 putaran tertutup" in laporan.alasan_expectancy
    assert "BELUM DAPAT DINILAI" in teks and "Angka sementara" in teks


def test_rekap_menampilkan_putaran_tertutup_beserta_1r_dan_rencananya(
    siap: sqlite3.Connection,
) -> None:
    """PRD 9.8: hasil tiap keputusan dalam R — jadi angkanya harus **terlihat**, bukan hanya rata-rata."""
    rencana = _putaran_tertutup(siap, jual=2_500)
    hasil = (2_500 - CLOSE) * rencana.lembar - (4 + 7) * rencana.lembar

    teks = jurnal.rekap(siap).ringkas()

    assert "Putaran tertutup (hasil tiap keputusan dalam R, PRD 9.8/8.2)" in teks
    assert f"rencana #{rencana.id_rencana} r1" in teks, "revisi rencana yang memberi 1R ikut tampil"
    assert f"1R {tampilan.rupiah(rencana.risiko_nominal)}" in teks
    assert f"hasil {tampilan.rupiah(hasil)}" in teks
    assert f"{tampilan.angka(float(Fraction(hasil, rencana.risiko_nominal)), 2)}R" in teks


def test_putaran_tanpa_rencana_tidak_punya_1r_dan_disebut_sebabnya(siap: sqlite3.Connection) -> None:
    _kandidat(siap, stop_awal=2_180)
    _beli(siap, id_rencana=None, lembar=100, tanggal=date(2026, 7, 2))
    _jual(siap, lembar=100, tanggal=date(2026, 7, 3))

    laporan = jurnal.rekap(siap)
    putaran = laporan.putaran[0]

    assert putaran.tertutup
    assert putaran.r_posisi is None
    assert putaran.alasan_r is not None and "tanpa rencana tersimpan (V6)" in putaran.alasan_r
    assert putaran.hasil is not None, "hasilnya tetap dihitung — yang hilang hanya 1R-nya"
    assert not putaran.dinilai
    assert laporan.expectancy_r is None
    assert "tidak punya 1R" in laporan.ringkas()


def test_biaya_yang_belum_dicatat_membuat_hasil_bukan_setelah_biaya(
    sambungan: sqlite3.Connection,
) -> None:
    """PRD 9.8 menuntut hasil "setelah biaya dan pajak"; biaya NULL bukan nol.

    Transaksinya sengaja bertanggal **sebelum** tarif broker berlaku, jadi biayanya memang tidak
    dapat dihitung — bukan diisi nol (pola yang sama dengan `test_posisi.py`).
    """
    konfigurasi.simpan(sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_ALL_IN, SLIPPAGE_TICK))
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber=SUMBER, emiten=EMITEN_UJI, harga_harian=_deret(KODE)),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    risiko.simpan_preset(sambungan, risiko.batas_bawaan(date(2026, 7, 1)))
    risiko.catat_ekuitas(
        sambungan,
        ekuitas=250_000_000,
        kas=100_000_000,
        arus_dana=0,
        mode="nyata",
        tanggal=date(2026, 7, 1),
    )
    rencana = _rencana(sambungan)
    _beli(sambungan, id_rencana=rencana.id_rencana, lembar=rencana.lembar,
          tanggal=date(2025, 12, 30))
    _jual(sambungan, lembar=rencana.lembar, tanggal=date(2025, 12, 31))

    laporan = jurnal.rekap(sambungan)
    putaran = laporan.putaran[0]

    assert putaran.tertutup
    assert putaran.hasil is None
    assert putaran.alasan_hasil is not None and "belum mencatat biayanya" in putaran.alasan_hasil
    assert not putaran.dinilai
    assert laporan.expectancy_r is None


def test_putaran_yang_masih_terbuka_tidak_masuk_expectancy(siap: sqlite3.Connection) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))

    laporan = jurnal.rekap(siap)

    assert [satu.tertutup for satu in laporan.putaran] == [False]
    assert "1 putaran masih terbuka" in laporan.ringkas()


def test_drawdown_muncul_di_rekap_dan_deretnya_tidak_terkoreksi_tanpa_arus_dana(
    siap: sqlite3.Connection,
) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))
    risiko.catat_ekuitas(siap, ekuitas=240_000_000, tanggal=date(2026, 7, 3), mode="nyata")

    teks = jurnal.rekap(siap).ringkas()

    assert "Drawdown berjalan" in teks
    assert "TIDAK DAPAT DINILAI" in teks, "baris kedua ekuitas tanpa arus dana tidak dikoreksi"


# ---------------------------------------------------------------------------------------
# Mode kepala (AC-11)
# ---------------------------------------------------------------------------------------


def test_cli_jurnal_menampilkan_keputusan_beserta_pelanggarannya(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))
    posisi.ubah_stop(siap, 1, 2_000, tanggal=date(2026, 7, 3))

    kode = cli.main(["--jurnal"])
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "JURNAL KEPUTUSAN" in keluaran
    assert "1 keputusan" in keluaran
    assert "V5 (stop digeser menjauhi harga)" in keluaran
    assert "belum ditulis; --jurnal-catat" in keluaran


def test_cli_rekap_kepatuhan_keluar_nol(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))

    kode = cli.main(["--rekap-kepatuhan", "--bulan", "2026-07"])
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "REKAP KEPATUHAN — 2026-07" in keluaran
    assert "transaksi tanpa pelanggaran ÷ seluruh transaksi" in keluaran


def test_cli_jurnal_catat_menambah_revisi_dan_melaporkannya(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))

    assert cli.main(["--jurnal-catat", "1", "--alasan", "sesuai rencana"]) == cli.KODE_OK
    pertama = capsys.readouterr().out
    assert "jurnal #1 r1" in pertama

    assert (
        cli.main(
            ["--jurnal-catat", "1", "--pelajaran", "stop terlalu jauh", "--tandai-selesai",
             "--tanggal", "2026-07-05"]
        )
        == cli.KODE_OK
    )
    kedua = capsys.readouterr().out

    assert "jurnal #1 r2" in kedua
    assert "Revisi r1 disimpan, bukan ditimpa" in kedua
    assert "SELESAI 2026-07-05" in kedua
    # Alasan lama tidak hilang oleh revisi yang hanya menulis pelajaran.
    assert jurnal.catatan_terkini(siap, 1).alasan == "sesuai rencana"  # type: ignore[union-attr]


def test_cli_jurnal_catat_untuk_transaksi_yang_tidak_ada_keluar_gagal(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(["--jurnal-catat", "7", "--alasan", "apa saja"])

    assert kode == cli.KODE_GAGAL
    assert "transaksi #7 tidak ada" in capsys.readouterr().err


def test_cli_bulan_yang_tidak_dikenal_keluar_gagal(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(["--rekap-kepatuhan", "--bulan", "2026/07"])

    assert kode == cli.KODE_GAGAL
    assert "YYYY-MM" in capsys.readouterr().err


def test_rekap_memuat_pernyataan_bukan_nasihat_investasi(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """Aturan keras 8 / PRD 9.10: rekap memuat angka hasil, jadi pernyataannya ikut."""
    rencana = _rencana(siap)
    _beli(siap, id_rencana=rencana.id_rencana, tanggal=date(2026, 7, 2))

    assert jurnal.BUKAN_NASIAT in jurnal.rekap(siap).ringkas()
    assert cli.main(["--rekap-kepatuhan"]) == cli.KODE_OK
    assert "bukan nasihat investasi" in capsys.readouterr().out
    # Rekap kosong pun memuatnya: pernyataannya tidak boleh bergantung pada ada-tidaknya isi.
    assert jurnal.BUKAN_NASIAT in jurnal.rekap(siap, bulan="2026-01").ringkas()


def test_cli_jurnal_tanpa_keputusan_mengatakan_sebabnya(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(["--jurnal"])
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "belum ada keputusan tercatat" in keluaran


def test_rekap_kosong_menyebut_jalan_mencatat_di_dasbor_juga(siap: sqlite3.Connection) -> None:
    """Uji regresi (sesi 69): rekap yang sama tampil di dasbor web, tetapi hanya menyebut
    `--catat-transaksi` — padahal web punya formulir Catat transaksi di Detail emiten."""
    teks = jurnal.rekap(siap).ringkas()

    assert "--catat-transaksi" in teks
    assert "Catat transaksi di Detail emiten" in teks
