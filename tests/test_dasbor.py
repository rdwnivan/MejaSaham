"""Uji dasbor harian & "tindakan menunggu" (PRD 9.11/11.1, P16) — `mejasaham/dasbor.py`.

Dasbor adalah satu-satunya tempat aturan PRD 9.11 *"posisi yang penutupannya menembus stop atau
pembatal tesis muncul di daftar tindakan menunggu"* menjadi kenyataan. Yang diuji di sini:

* **Daftarnya benar-benar berisi**, bukan hanya ada: stop yang tertembus, pembatal tesis yang
  terpicu, tesis kedaluwarsa, dan posisi tanpa stop (risikonya tidak dapat dinilai).
* **Yang belum dapat dinilai disebut beserta sebabnya**, bukan dihilangkan dan bukan kalimat tetap:
  sejak **K58** sebabnya dibaca dari data (IHSG ada atau tidak, cukup atau belum), sebab kalimat
  tetap lama — *"rezim pasar & breadth belum dapat dinilai … `harga_indeks` belum diisi"* — terbukti
  salah ketika `harga_indeks` memang terisi.
* **AC-8**: snapshot yang bukan dari hari bursa terakhir diberi peringatan mencolok.
* **Kandidat dibaca dari baris yang tersimpan** (tabel `skor`), bukan dari menjalankan saringan
  ulang di dalam dasbor — sedangkan **konteks pasar** (IHSG, breadth, rezim) dihitung dengan fungsi
  yang **sama** dengan `--saring` (K58/T66); uji `…membaca_konteks_pasar_yang_sama` yang menjaganya.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import (
    __version__,
    cli,
    dasbor,
    db,
    ingesti,
    kandidat,
    konfigurasi,
    lokasi,
    metrik,
    pengatur,
    posisi,
    risiko,
    saring,
)
from mejasaham.skema import VERSI_TERBARU
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    HargaHarian,
    KumpulanData,
    NotasiKhusus,
    PenutupanIndeks,
)

SUMBER = "uji-dasbor"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
HARI_INI = date(2026, 7, 6)
KODE = "AAAA"
LOT = 100
CLOSE = 2_320
RENTANG = 40
HARI = 24
VOLUME = 2_000_000

EMITEN_UJI = (Emiten(kode=KODE, nama="Emiten A", sektor_idx_ic="industri", sumber="uji-rujukan"),)

PARAMETER = """
[[lot]]
nilai_lembar  = 100
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06

[[fraksi_harga]]
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06
rentang = [
  { batas_bawah = 2000, batas_atas = 4999, tick = 10 },
]

[[biaya_broker]]
nama          = "Broker All-in"
sisi_beli     = { persen = 0.15 }
sisi_jual     = { persen = 0.25 }
sudah_termasuk = ["pph_penjualan"]
berlaku_sejak = 2026-01-02
sumber        = "Halaman tarif resmi broker (uji)"
dicatat_pada  = 2026-10-06
"""


def _deret(kode: str = KODE) -> tuple[HargaHarian, ...]:
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=HARI - 1 - i),
            open=CLOSE,
            high=CLOSE + RENTANG // 2,
            low=CLOSE - RENTANG // 2,
            close=CLOSE,
            volume=VOLUME,
            nilai=CLOSE * VOLUME,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(HARI)
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
def siap(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    """Basis data lengkap: parameter + data + preset + ekuitas + kalender hari bursa."""
    konfigurasi.simpan(sambungan, konfigurasi.urai("skema = 1\n\n" + PARAMETER, asal="uji"))
    ingesti.simpan(
        sambungan,
        KumpulanData(sumber=SUMBER, emiten=EMITEN_UJI, harga_harian=_deret()),
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
    return sambungan


def _hari_bursa(sambungan: sqlite3.Connection, tanggal: date, hari_bursa: bool = True) -> None:
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO kalender_bursa (tanggal, hari_bursa, keterangan, sumber, diketahui_pada)"
            " VALUES (?, ?, ?, 'uji', '2026-07-01T06:00:00+07:00')",
            (tanggal.isoformat(), 1 if hari_bursa else 0, "uji"),
        )


def _skor(
    sambungan: sqlite3.Connection,
    id_preset: str,
    *,
    skor: int = 8_200,
    dihitung_pada: str = "2026-07-01T07:00:00+07:00",
) -> None:
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO skor (kode, id_snapshot, id_preset, skor_total_bp, peringkat,"
            " dihitung_pada, versi_hitung, penjelasan)"
            " VALUES (?, 1, ?, ?, 1, ?, 'uji', 'uji')",
            (KODE, id_preset, skor, dihitung_pada),
        )


def _posisi_dengan_stop(
    sambungan: sqlite3.Connection,
    *,
    stop_awal: int = 2_200,
    tanggal_tinjau: str = "2026-08-01",
) -> posisi.Posisi:
    kandidat.buat(
        sambungan,
        KODE,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=stop_awal,
        tanggal_tinjau=tanggal_tinjau,
    )
    return posisi.catat_transaksi(
        sambungan, KODE, "beli", harga=CLOSE, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 2)
    ).posisi


# ---------------------------------------------------------------------------------------
# Keluaran dasbor
# ---------------------------------------------------------------------------------------


def test_dasbor_menyebut_snapshot_harga_dan_risiko(siap: sqlite3.Connection) -> None:
    pengatur.siapkan_preset_bawaan(siap)
    _skor(siap, "kualitas-nilai/v1")
    _posisi_dengan_stop(siap)

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)
    teks = laporan.ringkas()

    assert laporan.id_snapshot == 1
    assert "Snapshot   : #1" in teks
    assert SUMBER in teks
    assert "Posisi: 1 aktif" in teks
    assert "dari batas 5,00%" in teks
    assert "AAAA" in teks and "82,0" in teks
    assert "preset kualitas-nilai/v1" in teks


def test_dasbor_menampilkan_kandidat_hanya_dari_skor_tersimpan(siap: sqlite3.Connection) -> None:
    """Tanpa `--saring` yang pernah jalan, tidak ada kandidat — dan itu dikatakan."""
    laporan = dasbor.susun(siap, hari_ini=HARI_INI)

    assert laporan.kandidat_teratas == ()
    assert "belum ada skor tersimpan" in laporan.ringkas()
    assert any("--saring belum pernah dijalankan" in satu for satu in laporan.catatan)


def test_dasbor_menyebut_peringkat_sementara_bila_notasi_belum_ada(siap: sqlite3.Connection) -> None:
    """PRD 7.3: skor tanpa data notasi bukan kandidat — halaman depan menyebutnya seperti --saring."""
    pengatur.siapkan_preset_bawaan(siap)
    _skor(siap, "kualitas-nilai/v1")

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)
    teks = laporan.ringkas()

    assert "notasi khusus" in laporan.sebab_sementara
    assert "PERINGKAT SEMENTARA, BELUM BOLEH DISEBUT KANDIDAT" in teks
    assert "Kandidat   :" not in teks
    assert "AAAA" in teks


def test_dasbor_menyebut_kandidat_bila_notasi_lengkap(sambungan: sqlite3.Connection) -> None:
    konfigurasi.simpan(sambungan, konfigurasi.urai("skema = 1\n\n" + PARAMETER, asal="uji"))
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=EMITEN_UJI,
            harga_harian=_deret(),
            # Notasi yang sudah selesai: datanya ada (terverifikasi) tanpa mengecualikan AAAA.
            notasi_khusus=(
                NotasiKhusus(
                    kode=KODE,
                    jenis="uma",
                    tanggal_mulai=date(2026, 1, 5),
                    tanggal_selesai=date(2026, 1, 9),
                ),
            ),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    pengatur.siapkan_preset_bawaan(sambungan)
    _skor(sambungan, "kualitas-nilai/v1")

    laporan = dasbor.susun(sambungan, hari_ini=HARI_INI)

    assert laporan.sebab_sementara == ""
    assert "Kandidat   : 1 teratas" in laporan.ringkas()
    assert "PERINGKAT SEMENTARA" not in laporan.ringkas()


def test_dasbor_membandingkan_ekuitas_dengan_nilai_posisi_plus_kas(siap: sqlite3.Connection) -> None:
    """K30: ekuitas tetap dicatat pengguna, dan pembandingnya ditampilkan apa adanya.

    Tanpa pembanding ini, angka ekuitas yang dicatat sendiri tidak pernah bisa diperiksa — dan
    `--drawdown` bersandar padanya (AC-13).
    """
    _posisi_dengan_stop(siap)

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)
    teks = laporan.ringkas()

    # Posisi 1.000 lembar x penutupan 2.320 = Rp 2.320.000; kas Rp 100.000.000.
    assert laporan.nilai_posisi == 2_320_000
    assert laporan.nilai_posisi_plus_kas == 102_320_000
    assert "posisi + kas Rp 102.320.000" in teks
    assert "selisih Rp -147.680.000 dari ekuitas tercatat" in teks
    assert any("K30" in satu for satu in laporan.catatan)


def test_pembanding_ekuitas_tidak_dijumlahkan_sebagian(siap: sqlite3.Connection) -> None:
    """Kas yang belum dicatat membuat pembandingnya **tidak ada**, bukan dianggap nol."""
    _posisi_dengan_stop(siap)
    risiko.catat_ekuitas(
        siap,
        ekuitas=250_000_000,
        kas=None,
        arus_dana=0,
        mode="nyata",
        tanggal=date(2026, 7, 3),
    )

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)

    assert laporan.ekuitas is not None and laporan.ekuitas.kas is None
    assert laporan.nilai_posisi_plus_kas is None
    assert "posisi + kas" not in laporan.ringkas()


def test_dasbor_memperingatkan_snapshot_basi(siap: sqlite3.Connection) -> None:
    """AC-8: snapshot bukan dari hari bursa terakhir harus tampak, bukan lewat begitu saja."""
    _hari_bursa(siap, date(2026, 7, 3))

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)

    assert laporan.snapshot_basi
    assert "SNAPSHOT BUKAN DARI HARI BURSA TERAKHIR" in laporan.ringkas()


def test_snapshot_terbaru_tidak_disebut_basi(siap: sqlite3.Connection) -> None:
    _hari_bursa(siap, TANGGAL)

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)

    assert not laporan.snapshot_basi


def test_dasbor_menyebut_yang_belum_dapat_dinilai(siap: sqlite3.Connection) -> None:
    """Yang belum dapat dinilai disebut **sebabnya**, dan sebabnya dibaca dari data (K58).

    Sebelum K58 di sini selalu tercetak kalimat tetap *"rezim pasar & breadth belum dapat dinilai …
    `harga_indeks` … belum diisi sumbernya"*. Di basis data ini IHSG memang belum ada, tetapi
    kalimat itu tidak membedakan "belum diambil" dari "sudah ada tetapi tidak dibaca" — dan pada
    basis data nyata ia **salah**: `harga_indeks` terisi, saringan menghitung breadth darinya,
    sedangkan dasbor menyatakan datanya tidak ada.

    Sejak Tahap 2 langkah 4 (aksi korporasi pada posisi), **right issue bukan lagi** keadaan yang
    "belum dapat dinilai": ia tindakan menunggu yang nyata, dan diuji di
    `tests/test_aksi_korporasi_posisi.py`.
    """
    pengatur.siapkan_preset_bawaan(siap, date(2026, 7, 1))

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)
    teks = laporan.ringkas()

    assert any("penutupan IHSG belum ada di basis data" in satu for satu in laporan.catatan)
    assert not any("aksi korporasi pada posisi" in satu for satu in laporan.catatan)
    assert "CATATAN" in teks
    assert "IHSG belum ada di basis data" in teks
    # Kalimat tetap yang salah tidak boleh kembali dalam bentuk apa pun.
    assert "harga_indeks" not in teks


def test_dasbor_tanpa_snapshot_tetap_jalan(sambungan: sqlite3.Connection) -> None:
    """Basis data kosong: dasbor tetap menjawab, dan menyebut apa yang belum ada."""
    laporan = dasbor.susun(sambungan, hari_ini=HARI_INI)
    teks = laporan.ringkas()

    assert laporan.id_snapshot is None
    assert "belum ada snapshot" in teks
    assert "belum pernah dicatat" in teks
    assert "TINDAKAN MENUNGGU (0)" in teks


# ---------------------------------------------------------------------------------------
# Tindakan menunggu (PRD 9.11, P16)
# ---------------------------------------------------------------------------------------


def test_tindakan_stop_yang_tertembus(siap: sqlite3.Connection) -> None:
    """Stop 2.400 sementara penutupan terakhir 2.320: posisinya sudah menembus stop."""
    pos = _posisi_dengan_stop(siap)
    posisi.ubah_stop(siap, pos.id_posisi, 2_400, tanggal=date(2026, 7, 3))

    tindakan = dasbor.tindakan_menunggu(
        siap, posisi.ringkasan_semua(siap, status="aktif"), hari_ini=HARI_INI
    )

    assert [satu.jenis for satu in tindakan] == ["stop_tertembus"]
    assert "menembus stop" in tindakan[0].pesan


def test_tindakan_posisi_tanpa_stop(siap: sqlite3.Connection) -> None:
    posisi.catat_transaksi(
        siap, KODE, "beli", harga=CLOSE, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 2)
    )

    tindakan = dasbor.tindakan_menunggu(
        siap, posisi.ringkasan_semua(siap, status="aktif"), hari_ini=HARI_INI
    )

    assert [satu.jenis for satu in tindakan] == ["tanpa_stop"]
    assert "TIDAK DINILAI" in tindakan[0].pesan
    # Sejak aksi #19d, tindakan ini bisa dikerjakan dari jendela juga — pesannya tidak boleh
    # menyuruh pindah ke baris perintah seolah itu satu-satunya jalan (K62).
    assert "Ubah stop" in tindakan[0].pesan and "11.1" in tindakan[0].pesan


def test_tindakan_pembatal_tesis_terpicu(siap: sqlite3.Connection) -> None:
    """Harga pembatal di atas penutupan terakhir: tesisnya sudah terpicu (PRD 9.6, V7)."""
    kandidat.buat(
        siap,
        KODE,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_200,
        harga_pembatal=2_400,
        tanggal_tinjau="2026-08-01",
    )
    posisi.catat_transaksi(
        siap, KODE, "beli", harga=CLOSE, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 2)
    )

    tindakan = dasbor.tindakan_menunggu(
        siap, posisi.ringkasan_semua(siap, status="aktif"), hari_ini=HARI_INI
    )

    assert "pembatal_terpicu" in [satu.jenis for satu in tindakan]
    assert any("V7" in satu.pesan for satu in tindakan if satu.jenis == "pembatal_terpicu")


def test_tindakan_tesis_kedaluwarsa(siap: sqlite3.Connection) -> None:
    kandidat.buat(
        siap,
        KODE,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_200,
        tanggal_tinjau="2026-07-03",
    )

    tindakan = dasbor.tindakan_menunggu(siap, (), hari_ini=HARI_INI)

    assert [satu.jenis for satu in tindakan] == ["tesis_kedaluwarsa"]
    assert "3 hari" in tindakan[0].pesan
    assert dasbor.susun(siap, hari_ini=HARI_INI).jumlah_tesis_kedaluwarsa == 1


def test_tindakan_kosong_saat_semuanya_beres(siap: sqlite3.Connection) -> None:
    kandidat.buat(
        siap,
        KODE,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_200,
        tanggal_tinjau="2026-08-01",
    )
    posisi.catat_transaksi(
        siap, KODE, "beli", harga=CLOSE, lembar=1_000, mode="nyata", tanggal=date(2026, 7, 2)
    )

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)

    assert laporan.tindakan == ()
    assert "TINDAKAN MENUNGGU (0)" in laporan.ringkas()
    assert "(tidak ada)" in laporan.ringkas()


# ---------------------------------------------------------------------------------------
# Konteks pasar: IHSG, breadth & rezim (K58, T66; PRD 8.2, 11.1)
# ---------------------------------------------------------------------------------------

#: Panjang deret harga emiten uji: cukup untuk MA50 & ADTV20, tidak lebih.
BAR_EMITEN_PASAR = 60
#: Panjang deret IHSG: cukup untuk MA200 (P6: MA200 = 200 baris, bukan 200 hari kalender).
BAR_IHSG_PASAR = 210
#: Nilai transaksi per bar. Dua angka ini dipilih **jauh** di atas dan di bawah ambang ADTV20
#: PRD 8.2 (Rp 5 miliar), supaya semesta likuidnya tidak berubah kalau ambangnya disesuaikan
#: sedikit — dan supaya penyebut breadth-nya bisa diperiksa tangan.
NILAI_LIKUID = 6_000_000_000
NILAI_SEPI = 100_000_000


def _emiten_pasar(kode: str) -> Emiten:
    return Emiten(kode=kode, nama=f"Emiten {kode}", sektor_idx_ic="industri", sumber="uji-rujukan")


def _deret_pasar(kode: str, *, awal: int, langkah: int, nilai: int) -> tuple[HargaHarian, ...]:
    """`BAR_EMITEN_PASAR` bar berurutan: `awal`, `awal + langkah`, … (naik atau turun linear).

    Emiten yang naik berakhir **di atas** MA50-nya, yang turun **di bawah** — dan keduanya likuid
    atau tidak menurut `nilai` per barnya.
    """
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=BAR_EMITEN_PASAR - 1 - i),
            open=awal + langkah * i,
            high=awal + langkah * i,
            low=awal + langkah * i,
            close=awal + langkah * i,
            volume=1_000_000,
            nilai=nilai,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(BAR_EMITEN_PASAR)
    )


def _ihsg(jumlah: int = BAR_IHSG_PASAR) -> tuple[PenutupanIndeks, ...]:
    """IHSG: seluruh bar di 6.000 kecuali yang terakhir 6.200.

    Dengan 210 bar, MA200-nya = (199 × 6.000 + 6.200) ÷ 200 = **6.001**, jadi penutupan terakhir
    ada **di atas** MA200 — syarat RISK-ON tinggal breadth ≥ 50% (PRD 8.2). Perubahannya +200
    (+3,33%).
    """
    return tuple(
        PenutupanIndeks(
            indeks="IHSG",
            tanggal=TANGGAL - timedelta(days=jumlah - 1 - i),
            close=6_200 if i == jumlah - 1 else 6_000,
        )
        for i in range(jumlah)
    )


def _siapkan_pasar(sambungan: sqlite3.Connection, *, jumlah_ihsg: int = BAR_IHSG_PASAR) -> None:
    """Tulis satu snapshot yang konteks pasarnya bisa dihitung: IHSG + tiga emiten (dua likuid).

    Semesta likuid = {NAIK, TURUN}; SEPI di bawah ambang ADTV20. Dari dua yang likuid, hanya NAIK
    yang penutupannya di atas MA50 → **breadth 1 dari 2 = 50,0%**, dan dengan IHSG di atas MA200
    rezimnya **RISK-ON** (ambang 50% dipenuhi tepat di batasnya).
    """
    konfigurasi.simpan(sambungan, konfigurasi.urai("skema = 1\n\n" + PARAMETER, asal="uji"))
    pengatur.siapkan_preset_bawaan(sambungan, date(2026, 7, 1))
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=(_emiten_pasar("NAIK"), _emiten_pasar("TURUN"), _emiten_pasar("SEPI")),
            harga_harian=(
                _deret_pasar("NAIK", awal=1_000, langkah=2, nilai=NILAI_LIKUID)
                + _deret_pasar("TURUN", awal=1_200, langkah=-2, nilai=NILAI_LIKUID)
                + _deret_pasar("SEPI", awal=1_200, langkah=-2, nilai=NILAI_SEPI)
            ),
            harga_indeks=_ihsg(jumlah_ihsg),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )


@pytest.fixture()
def siap_pasar(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    _siapkan_pasar(sambungan)
    return sambungan


def test_dasbor_dan_saring_membaca_konteks_pasar_yang_sama(
    siap_pasar: sqlite3.Connection,
) -> None:
    """K58/T66: dua layar tidak boleh punya dua pembacaan pasar.

    Cacat yang mendasarinya: dasbor selalu menulis *"rezim pasar & breadth belum dapat dinilai"*
    sementara `--saring` pada snapshot yang sama menghitung `breadth 39,1% · rezim RISK-OFF` dari
    `harga_indeks` yang **terisi**. Yang salah bukan sekadar kalimatnya: satu baris halaman depan
    yang PRD 11.1 minta ada disembunyikan sambil menyatakan datanya tidak ada.
    """
    preset = saring.preset_terbaru(siap_pasar, "kualitas-nilai")
    laporan_saring = pengatur.jalankan_saring(siap_pasar, preset)
    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)

    assert laporan.breadth is not None and laporan.breadth.ada
    assert laporan.breadth.nilai == laporan_saring.breadth.nilai
    assert laporan.rezim == laporan_saring.rezim == "RISK-ON"
    # Semesta likuid 2 dari 3 emiten (SEPI di bawah ambang ADTV20); 1 di antaranya di atas MA50.
    assert laporan.breadth.nilai == pytest.approx(0.5)
    assert "1 dari 2" in (laporan.breadth.asal or "")

    # Bentuk barisnya sama dengan `--saring`, sehingga teksnya bisa dibandingkan apa adanya.
    assert "breadth 50,0% · rezim RISK-ON" in laporan.ringkas()
    assert "  breadth 50,0% · rezim RISK-ON" in laporan_saring.ringkas()
    assert "belum dapat dinilai" not in laporan.ringkas()


def test_dasbor_menampilkan_ihsg_dan_perubahannya(siap_pasar: sqlite3.Connection) -> None:
    """PRD 11.1: `IHSG : 7.842 (+0,42%)` — penutupan terakhir beserta arah perubahannya."""
    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)
    teks = laporan.ringkas()

    assert laporan.pasar is not None
    assert (laporan.pasar.penutupan, laporan.pasar.penutupan_sebelumnya) == (6_200, 6_000)
    assert laporan.pasar.perubahan == 200
    assert "IHSG 6.200" in teks
    assert "+200 (+3,33%)" in teks
    assert "preset kualitas-nilai/v1" in teks


def test_dasbor_netral_bila_ihsg_belum_ada_beserta_sebabnya(siap: sqlite3.Connection) -> None:
    """Tanpa `harga_indeks`, rezimnya NETRAL **beserta sebabnya** — bukan angka karangan."""
    pengatur.siapkan_preset_bawaan(siap, date(2026, 7, 1))

    laporan = dasbor.susun(siap, hari_ini=HARI_INI)

    assert laporan.rezim == "NETRAL (dasar tidak lengkap)"
    assert "rezim NETRAL (dasar tidak lengkap)" in laporan.ringkas()
    assert any(
        "penutupan IHSG belum ada di basis data" in satu for satu in laporan.catatan
    ), "sebabnya harus spesifik: yang belum ada IHSG-nya, bukan 'dasar tidak lengkap' saja"


def test_dasbor_menyebut_bar_ihsg_yang_masih_kurang(sambungan: sqlite3.Connection) -> None:
    """199 bar IHSG belum cukup untuk MA200 (P6) — jumlahnya disebut, ambangnya dipinjam `metrik`."""
    _siapkan_pasar(sambungan, jumlah_ihsg=199)

    laporan = dasbor.susun(sambungan, hari_ini=HARI_INI)

    assert laporan.rezim == "NETRAL (dasar tidak lengkap)"
    # Breadth-nya sendiri tetap bisa dihitung: yang kurang hanya MA200 IHSG.
    assert laporan.breadth is not None and laporan.breadth.ada
    assert any(
        "baru 199 bar" in satu and "MA200 butuh 200" in satu for satu in laporan.catatan
    )


def test_breadth_memakai_preset_yang_menghasilkan_skor_tersimpan(
    siap_pasar: sqlite3.Connection,
) -> None:
    """Semesta likuid ikut ambang ADTV20 **preset** (K6), jadi presetnya yang tercetak di halaman.

    Preset uji di bawah ini menaikkan ambang ADTV20 ke Rp 10 miliar, sehingga kedua emiten likuid
    tadi keluar dari semesta: breadth-nya berhenti bisa dihitung. Kalau dasbor memakai preset lain
    (mis. bawaan `--saring`), jawabannya akan tetap 50,0% — dan halaman itu akan menampilkan
    breadth dari ambang yang tidak sejalan dengan daftar kandidatnya sendiri.
    """
    bawaan = saring.preset_terbaru(siap_pasar, "kualitas-nilai")
    kriteria = tuple(
        dataclasses.replace(satu, ambang_rupiah=10_000_000_000)
        if satu.kriteria == "adtv20"
        else satu
        for satu in bawaan.kriteria
    )
    saring.simpan_preset(
        siap_pasar,
        dataclasses.replace(
            bawaan, id_preset="uji-mahal/v1", nama="uji-mahal", kriteria=kriteria
        ),
    )
    _skor(siap_pasar, "kualitas-nilai/v1", skor=8_000, dihitung_pada="2026-07-01T07:00:00+07:00")
    _skor(siap_pasar, "uji-mahal/v1", skor=7_000, dihitung_pada="2026-07-01T08:00:00+07:00")

    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)

    assert laporan.preset_pasar == "uji-mahal/v1"
    assert "preset uji-mahal/v1" in laporan.ringkas()
    assert laporan.breadth is not None and not laporan.breadth.ada
    assert "tidak ada emiten likuid" in (laporan.breadth.alasan or "")


def test_dasbor_tanpa_preset_menyebut_sebabnya(siap: sqlite3.Connection) -> None:
    """Basis data yang belum punya preset: breadth "tidak dihitung" beserta sebabnya, bukan tebakan.

    Ambang semesta likuid hidup di kriteria preset, jadi tanpa preset tidak ada ambang yang sah —
    dan menebaknya berarti menampilkan `breadth 50%` yang tidak bisa diperiksa ulang.
    """
    laporan = dasbor.susun(siap, hari_ini=HARI_INI)

    assert laporan.preset_pasar is None
    assert laporan.breadth is not None and not laporan.breadth.ada
    assert "preset" in (laporan.breadth.alasan or "")
    assert "breadth tidak dihitung" in laporan.ringkas()
    assert laporan.rezim == "NETRAL (dasar tidak lengkap)"


# ---------------------------------------------------------------------------------------
# Konteks pasar tersimpan (K61; PRD 11.1): --saring menulis, dasbor membaca bila masih sah
# ---------------------------------------------------------------------------------------


def _preset_pasar(sambungan: sqlite3.Connection) -> saring.Preset:
    return saring.preset_terbaru(sambungan, "kualitas-nilai")


def _hitung_ulang_dilarang(*_args: object, **_kwargs: object) -> dasbor.KonteksPasar:
    """Gagal berisik bila dasbor menghitung ulang padahal angka yang sah sudah tersimpan."""
    raise AssertionError(
        "dasbor menghitung ulang konteks pasar padahal angka yang sah sudah tersimpan (K61)"
    )


def _sentinel(*_args: object, **_kwargs: object) -> dasbor.KonteksPasar:
    """Konteks pengganti: kehadirannya membuktikan dasbor TIDAK memakai angka tersimpan."""
    return dasbor.KonteksPasar(
        breadth=metrik.tidak_dihitung("breadth", "rasio", "SENTINEL"),
        rezim="SENTINEL",
        preset="SENTINEL",
    )


def _snapshot_baru(sambungan: sqlite3.Connection, id_snapshot: int = 2) -> None:
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO snapshot (id_snapshot, tanggal_data, batas_diketahui, jam_ambil,"
            " jumlah_emiten, jumlah_gagal, versi_skema, versi_aplikasi)"
            " VALUES (?, ?, ?, ?, 0, 0, ?, ?)",
            (
                id_snapshot,
                TANGGAL.isoformat(),
                "2026-07-01T10:00:00+07:00",
                "2026-07-01T10:00:00+07:00",
                VERSI_TERBARU,
                __version__,
            ),
        )


def test_saring_menyimpan_konteks_pasar(siap_pasar: sqlite3.Connection) -> None:
    """K61: `--saring` menulis breadth + rezim + penutupan indeks, berkunci snapshot & preset."""
    preset = _preset_pasar(siap_pasar)
    laporan_saring = pengatur.jalankan_saring(siap_pasar, preset)

    baris = siap_pasar.execute("SELECT * FROM konteks_pasar").fetchall()

    assert len(baris) == 1
    satu = baris[0]
    assert satu["id_snapshot"] == 1
    assert satu["id_preset"] == preset.id_preset
    assert satu["sumber_harga"] == SUMBER
    assert satu["breadth_nilai"] == pytest.approx(laporan_saring.breadth.nilai)
    assert satu["breadth_status"] == metrik.STATUS_DIHITUNG
    assert satu["breadth_asal"] == laporan_saring.breadth.asal
    assert satu["rezim"] == laporan_saring.rezim == "RISK-ON"
    assert satu["indeks"] == "IHSG"
    assert satu["indeks_tanggal"] == TANGGAL.isoformat()
    assert satu["indeks_penutupan"] == 6_200
    assert satu["indeks_penutupan_sebelumnya"] == 6_000
    assert satu["catatan"] is None


def test_dasbor_memakai_konteks_tersimpan_bukan_menghitung_ulang(
    siap_pasar: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sesudah `--saring`, dasbor tidak boleh membayar potret + seluruh metrik lagi.

    Angkanya harus **sama** dengan yang tertulis di laporan saringan — bukan sekadar cepat.
    """
    preset = _preset_pasar(siap_pasar)
    laporan_saring = pengatur.jalankan_saring(siap_pasar, preset)
    monkeypatch.setattr(dasbor, "_konteks_pasar", _hitung_ulang_dilarang)

    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)

    assert laporan.breadth is not None and laporan.breadth.ada
    assert laporan.breadth == laporan_saring.breadth
    assert laporan.rezim == laporan_saring.rezim == "RISK-ON"
    assert laporan.pasar is not None
    assert laporan.pasar.penutupan == 6_200
    assert laporan.pasar.penutupan_sebelumnya == 6_000
    assert laporan.preset_pasar == preset.id_preset
    assert "breadth 50,0% · rezim RISK-ON" in laporan.ringkas()


def test_dasbor_memakai_sebab_bahan_kurang_yang_ikut_tersimpan(
    sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sebab "rezim NETRAL karena bahannya kurang" tidak boleh hilang saat dibaca dari simpanan."""
    _siapkan_pasar(sambungan, jumlah_ihsg=199)
    pengatur.jalankan_saring(sambungan, _preset_pasar(sambungan))
    monkeypatch.setattr(dasbor, "_konteks_pasar", _hitung_ulang_dilarang)

    laporan = dasbor.susun(sambungan, hari_ini=HARI_INI)

    assert laporan.rezim == "NETRAL (dasar tidak lengkap)"
    assert any("baru 199 bar" in satu and "MA200 butuh 200" in satu for satu in laporan.catatan)


def test_saring_parsial_tidak_menyimpan_konteks_pasar(siap_pasar: sqlite3.Connection) -> None:
    """`--kode` berjanji tidak menulis apa pun (`simpan=False`); konteks pun tidak ditulis."""
    preset = _preset_pasar(siap_pasar)

    pengatur.jalankan_saring(siap_pasar, preset, hanya_kode=("NAIK",), simpan=False)

    jumlah = siap_pasar.execute("SELECT COUNT(*) FROM konteks_pasar").fetchone()[0]
    assert jumlah == 0


def test_dasbor_tidak_memakai_konteks_snapshot_lain(
    siap_pasar: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Snapshot baru berarti konteks lama bukan keadaan halaman ini — dihitung ulang."""
    pengatur.jalankan_saring(siap_pasar, _preset_pasar(siap_pasar))
    _snapshot_baru(siap_pasar)
    monkeypatch.setattr(dasbor, "_konteks_pasar", _sentinel)

    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)

    assert laporan.id_snapshot == 2
    assert laporan.rezim == "SENTINEL"
    assert laporan.preset_pasar == "SENTINEL"


def test_dasbor_tidak_memakai_konteks_preset_lain(
    siap_pasar: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skor dari preset lain menuntut breadth dari preset itu — konteks preset lama tidak dipakai."""
    bawaan = _preset_pasar(siap_pasar)
    pengatur.jalankan_saring(siap_pasar, bawaan)
    saring.simpan_preset(
        siap_pasar,
        dataclasses.replace(bawaan, id_preset="uji-lain/v1", nama="uji-lain"),
    )
    # Jam di masa depan: `--saring` di atas menulis `dihitung_pada` dengan jam mesin, dan yang
    # diuji di sini adalah "preset yang skornya terakhir dihitung", bukan urutan jam yang wajar.
    _skor(siap_pasar, "uji-lain/v1", skor=7_000, dihitung_pada="2099-01-01T00:00:00+07:00")
    monkeypatch.setattr(dasbor, "_konteks_pasar", _sentinel)

    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)

    assert laporan.id_preset_skor == "uji-lain/v1"
    assert laporan.preset_pasar == "SENTINEL"
    assert laporan.rezim == "SENTINEL"


def test_dasbor_tidak_memakai_konteks_sumber_harga_lain(
    siap_pasar: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Breadth dihitung dari satu label harga (P17); label lain berarti konteks lain."""
    pengatur.jalankan_saring(siap_pasar, _preset_pasar(siap_pasar))
    monkeypatch.setattr(
        dasbor.potret,
        "riwayat_sumber",
        lambda _sambungan, *, batas=None: (("lain", 999), (SUMBER, 1)),
    )
    monkeypatch.setattr(dasbor, "_konteks_pasar", _sentinel)

    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)

    assert laporan.sumber_harga == "lain"
    assert laporan.rezim == "SENTINEL"


def test_dasbor_tidak_memakai_konteks_dari_versi_hitung_lain(
    siap_pasar: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Perubahan cara menghitung membatalkan baris lama, bukan membuatnya tampak sebanding."""
    pengatur.jalankan_saring(siap_pasar, _preset_pasar(siap_pasar))
    with db.tulis(siap_pasar) as koneksi:
        koneksi.execute("UPDATE konteks_pasar SET versi_hitung = 'pasar-0'")
    monkeypatch.setattr(dasbor, "_konteks_pasar", _sentinel)

    laporan = dasbor.susun(siap_pasar, hari_ini=HARI_INI)

    assert laporan.rezim == "SENTINEL"


def test_kegagalan_menyimpan_konteks_tidak_membatalkan_saringan(
    siap_pasar: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Konteks hanyalah jalan pintas: gagal menulisnya **berisik**, bukan alasan membatalkan skor."""

    def _gagal(*_args: object, **_kwargs: object) -> None:
        raise db.GalatBasisData("uji: tabel konteks tidak bisa ditulis")

    monkeypatch.setattr(pengatur.konteks_pasar, "simpan", _gagal)

    laporan = pengatur.jalankan_saring(siap_pasar, _preset_pasar(siap_pasar))

    assert any("konteks pasar tidak tersimpan" in satu for satu in laporan.peringatan)
    assert laporan.jumlah_likuid == 2  # laporan saring tetap lengkap, bukan dibatalkan
    # Bukti bahwa kegagalannya tercatat berisik di log, bukan ditelan.
    jejak = siap_pasar.execute(
        "SELECT hasil FROM log_jalan WHERE proses = 'saring' ORDER BY id_log DESC LIMIT 1"
    ).fetchone()
    assert jejak is not None and jejak["hasil"] == "peringatan"
    assert siap_pasar.execute("SELECT COUNT(*) FROM konteks_pasar").fetchone()[0] == 0


# ---------------------------------------------------------------------------------------
# Mode kepala
# ---------------------------------------------------------------------------------------


def test_cli_dasbor_keluar_nol_dan_menampilkan_tindakan(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    # Tanggal tinjau jauh di depan: yang diuji di sini tindakan "stop tertembus", bukan tesis
    # kedaluwarsa — dan umur tesis tidak boleh bergantung pada tanggal mesin yang menjalankan uji.
    _posisi_dengan_stop(siap, stop_awal=2_400, tanggal_tinjau="2099-01-01")

    kode = cli.main(["--dasbor"])
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "DASBOR HARIAN" in keluaran
    assert "TINDAKAN MENUNGGU (1)" in keluaran
    assert "stop_tertembus" in keluaran


def test_cli_drawdown_menampilkan_deret_dan_koreksinya(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    kode = cli.main(["--drawdown"])
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "2026-07-01" in keluaran
    assert "terkoreksi arus dana" in keluaran


def test_cli_drawdown_menyebut_bila_belum_bisa_dikoreksi(
    sambungan: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """Satu catatan tanpa arus dana sudah cukup membuat drawdown terkoreksi tidak dapat dinilai."""
    risiko.catat_ekuitas(sambungan, ekuitas=100_000_000, tanggal=date(2026, 7, 1))
    risiko.catat_ekuitas(sambungan, ekuitas=90_000_000, tanggal=date(2026, 7, 2))

    kode = cli.main(["--drawdown"])
    keluaran = capsys.readouterr().out

    assert kode == cli.KODE_OK
    assert "TIDAK DAPAT DINILAI" in keluaran
    assert "Mentah" in keluaran
