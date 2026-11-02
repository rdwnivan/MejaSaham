"""Uji aksi korporasi pada posisi (F11, PRD 9.11; AC-18) — `mejasaham/posisi.py` + migrasi 013.

PRD 9.11 menuntut tiga hal, dan ketiganya diuji di sini atas jalur yang **nyata** (data ditulis
lewat `ingesti.simpan`, bukan INSERT tangan):

* *"Split dan reverse split menyesuaikan lembar dan stop otomatis"* — lembar, harga rata-rata,
  hasil, dan **risiko** harus benar sesudah split. Sebelum ini, posisi yang melewati split
  menampilkan lembar dan stop yang salah **tanpa satu pun tanda**, dan angka itulah yang dipakai
  menghitung risiko; uji-uji di bagian pertama menjaga arah itu.
* *"Right issue memunculkan tenggat dan keputusan manual (tebus, jual HMETD, atau abaikan)"* —
  dan keputusan `tebus` **wajib** menunjuk transaksi, sebab lembarnya hanya punya satu tempat.
* *"Dividen dicatat sebagai arus kas dan masuk hasil"* — dihitung dari aksi korporasi × lembar
  pada tanggal ex-date, dengan pajaknya **tidak** dikarang, dan sebagai suku terpisah dari hasil
  perdagangan.

Dua hal yang sengaja diuji sebagai **keadaan tidak dapat dinilai**, bukan angka: stop lama yang
basisnya belum dinyatakan ketika ada split sesudahnya, dan dividen yang sumbernya tidak
menyatakan apa pun. Keduanya lebih berguna terlihat daripada ditebak.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest

from mejasaham import dasbor, db, ingesti, konfigurasi, lokasi, posisi, risiko
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    AksiKorporasi,
    Emiten,
    HargaHarian,
    KumpulanData,
)
from mejasaham.skema import KEPUTUSAN_RIGHT_ISSUE_SAH

SUMBER = "uji-aksi-korporasi"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
KODE = "AAAA"
KODE_LAIN = "BBBB"
SEKTOR = "industri"
CLOSE = 2_320
RENTANG = 40
HARI = 24
VOLUME = 2_000_000

TGL_BELI = date(2026, 6, 10)
TGL_SPLIT = date(2026, 6, 20)
TGL_BASIS_STOP = date(2026, 6, 15)

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
  { batas_bawah = 1,    batas_atas = 199,  tick = 1 },
  { batas_bawah = 200,  batas_atas = 499,  tick = 2 },
  { batas_bawah = 500,  batas_atas = 1999, tick = 5 },
  { batas_bawah = 2000, batas_atas = 4999, tick = 10 },
  { batas_bawah = 5000, tick = 25 },
]
"""

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


def _deret(kode: str, *, hari: int = HARI, close: int = CLOSE) -> tuple[HargaHarian, ...]:
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


def _deret_split(
    kode: str, *, tanggal_split: date, sebelum: int, sesudah: int, hari: int = HARI
) -> tuple[HargaHarian, ...]:
    """Deret harga yang **ikut** berubah pada tanggal split, seperti pasar sesungguhnya.

    Harga saham setelah split 1:2 memang separuh; memakai deret yang tidak berubah akan menguji
    hal yang salah (nilai posisi tampak berlipat, padahal pasarnya yang bergerak).
    """
    hasil = []
    for i in range(hari):
        tanggal = TANGGAL - timedelta(days=hari - 1 - i)
        harga = sebelum if tanggal < tanggal_split else sesudah
        hasil.append(
            HargaHarian(
                kode=kode,
                tanggal=tanggal,
                open=harga,
                high=harga + RENTANG // 2,
                low=harga - RENTANG // 2,
                close=harga,
                volume=VOLUME,
                nilai=harga * VOLUME,
                penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
            )
        )
    return tuple(hasil)


def _simpan_aksi(
    sambungan: sqlite3.Connection,
    *aksi: AksiKorporasi,
    harga: tuple[HargaHarian, ...] | None = None,
    momen: datetime = MOMEN,
) -> None:
    """Aksi korporasi masuk lewat jalur impor yang sebenarnya (`ingesti.simpan`).

    `momen` menjadi `diketahui_pada`: mengubah deret harga untuk kunci yang sama menuntut waktu
    yang **lebih baru**, persis seperti perbaikan data sungguhan (S1, PRD 7.2).
    """
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=EMITEN_UJI,
            harga_harian=harga if harga is not None else _deret(KODE) + _deret(KODE_LAIN),
            aksi_korporasi=aksi,
        ),
        tanggal_data=TANGGAL,
        momen=momen,
    )


def _split(
    kode: str = KODE,
    *,
    tanggal: date = TGL_SPLIT,
    lama: int = 1,
    baru: int = 2,
) -> AksiKorporasi:
    return AksiKorporasi(
        kode=kode,
        tanggal=tanggal,
        jenis="split" if baru >= lama else "reverse_split",
        rasio_lama=lama,
        rasio_baru=baru,
        keterangan="uji",
    )


def _dividen(kode: str, tanggal: date, per_saham: int) -> AksiKorporasi:
    return AksiKorporasi(
        kode=kode, tanggal=tanggal, jenis="dividen", dividen_per_saham=per_saham, keterangan="uji"
    )


def _right_issue(
    kode: str = KODE,
    *,
    tanggal: date = date(2026, 6, 25),
    lama: int = 5,
    baru: int = 2,
    harga_tebus: int = 1_000,
    tenggat: str | None = "2026-07-10",
) -> AksiKorporasi:
    return AksiKorporasi(
        kode=kode,
        tanggal=tanggal,
        jenis="right_issue",
        rasio_lama=lama,
        rasio_baru=baru,
        harga_tebus=harga_tebus,
        tenggat=tenggat,
        keterangan="uji",
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
    """Basis data lengkap: parameter bursa + data + batas risiko + ekuitas harian."""
    konfigurasi.simpan(
        sambungan, _urai(LOT_100, FRAKSI_HARGA, BROKER_ALL_IN, PAJAK_PENJUALAN, SLIPPAGE_TICK)
    )
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=EMITEN_UJI,
            harga_harian=_deret(KODE) + _deret(KODE_LAIN),
        ),
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


def _beli(
    sambungan: sqlite3.Connection,
    kode: str = KODE,
    *,
    harga: int = CLOSE,
    lembar: int = 1_000,
    tanggal: date = TGL_BELI,
) -> posisi.PendaftaranTransaksi:
    return posisi.catat_transaksi(
        sambungan, kode, "beli", harga=harga, lembar=lembar, mode="nyata", tanggal=tanggal
    )


def _ringkas(sambungan: sqlite3.Connection, kode: str = KODE) -> posisi.RingkasanPosisi:
    isi = posisi.ringkasan_semua(sambungan, status=None, kode=kode)
    assert isi, f"tidak ada posisi {kode}"
    return isi[0]


# ---------------------------------------------------------------------------------------
# AC-18 — split & reverse split menyesuaikan lembar, harga rata-rata, dan stop
# ---------------------------------------------------------------------------------------


def test_split_menyesuaikan_lembar_harga_rata_dan_risiko(siap: sqlite3.Connection) -> None:
    """Split 1:2 atas 1.000 lembar: menjadi 2.000 lembar, rata-rata separuh, stop ikut separuh.

    Risiko terbukanya diperiksa angkanya: (2.320 − 1.100) × 2.000 = Rp 2.440.000. Angka yang
    sama dari lembar yang **belum** disesuaikan akan berbunyi Rp 1.220.000 — separuh dari
    kenyataan, dan itulah bentuk kesalahannya sebelum langkah ini.
    """
    _beli(siap)
    posisi.ubah_stop(siap, 1, 2_200, tanggal=TGL_BASIS_STOP)  # basis sebelum split
    _simpan_aksi(siap, _split())

    satu = _ringkas(siap)

    assert satu.lembar_terbuka == 2_000
    assert satu.hitungan.lembar_terbuka_tercatat == 1_000
    assert satu.hitungan.harga_rata == Fraction(CLOSE, 2)
    assert satu.stop.tercatat == 2_200
    assert satu.stop.nilai == Fraction(1_100)
    assert [(a.jenis, a.tanggal, a.rasio_lama, a.rasio_baru) for a in satu.stop.aksi] == [
        ("split", TGL_SPLIT, 1, 2)
    ]
    assert satu.risiko_terbuka == 2_440_000


def test_reverse_split_menyesuaikan_lembar_dan_stop(siap: sqlite3.Connection) -> None:
    """Reverse split 2:1: lembar menjadi separuh, harga rata-rata dan stop menjadi dua kali."""
    _beli(siap, lembar=1_000)
    posisi.ubah_stop(siap, 1, 2_200, tanggal=TGL_BASIS_STOP)
    _simpan_aksi(siap, _split(lama=2, baru=1))

    satu = _ringkas(siap)

    assert satu.lembar_terbuka == 500
    assert satu.hitungan.harga_rata == CLOSE * 2
    assert satu.stop.nilai == 4_400
    assert satu.risiko_terbuka == 0  # penutupan 2.320 sudah di bawah stop 4.400


def test_transaksi_pada_tanggal_split_sudah_dalam_basis_baru(siap: sqlite3.Connection) -> None:
    """Tanggal aksi adalah tanggal berlakunya: eksekusi pada hari itu tidak dikali lagi."""
    _beli(siap, lembar=1_000, tanggal=TGL_SPLIT)
    _simpan_aksi(siap, _split())

    satu = _ringkas(siap)

    assert satu.lembar_terbuka == 1_000
    assert satu.hitungan.aksi == ()


def test_penjualan_pra_split_ikut_diskalakan_sehingga_hasil_terealisasi_benar(
    siap: sqlite3.Connection,
) -> None:
    """Beli 1.000 @2.320, jual 500 @2.500 sebelum split, lalu split 1:2.

    Pokok penjualan harus memakai lembar yang **sudah** diskalakan (1.000 lembar pascasplit),
    sehingga hasilnya (2.500 − 2.320) × 500 = Rp 90.000 — bukan angka yang berasal dari
    mencampur lembar pra-split dengan harga rata-rata pascasplit.
    """
    _beli(siap, lembar=1_000)
    posisi.catat_transaksi(
        siap, KODE, "jual", harga=2_500, lembar=500, mode="nyata", tanggal=date(2026, 6, 12)
    )
    _simpan_aksi(siap, _split())

    satu = _ringkas(siap)

    assert satu.lembar_terbuka == 1_000  # (1.000 − 500) × 2
    assert satu.hitungan.lembar_jual == 1_000
    # 2.500 x 500 = 1.250.000, dikurangi pokok 1.160 x 1.000 = 1.160.000, biaya jual all-in
    # 0,25% x 2.500 = 6,25 -> 7 per lembar = 3.500, dan biaya beli yang menempel pada lembar yang
    # dijual 4.000 x 1.000/2.000 = 2.000. Hasilnya 84.500.
    assert satu.hasil_terealisasi == 84_500


def test_nilai_posisi_tidak_berubah_karena_split(siap: sqlite3.Connection) -> None:
    """AC-18: split mengubah jumlah lembar dan harga, **bukan** nilai posisi.

    Deret harganya ikut separuh pada tanggal split (seperti pasar), jadi hasil yang benar adalah
    nilai yang sama: 2.320 × 1.000 = 1.160 × 2.000. Kalau lembarnya tidak disesuaikan, hasilnya
    tampak rugi separuh tanpa satu pun galat.
    """
    _beli(siap, lembar=1_000)
    _simpan_aksi(
        siap,
        _split(),
        harga=_deret_split(KODE, tanggal_split=TGL_SPLIT, sebelum=CLOSE, sesudah=CLOSE // 2)
        + _deret(KODE_LAIN, close=CLOSE // 2),
        momen=MOMEN + timedelta(hours=1),
    )

    satu = _ringkas(siap)

    assert satu.lembar_terbuka == 2_000
    assert satu.nilai_pasar == CLOSE * 1_000
    # Beli di 2.320 (basis lama) = 1.160 dalam basis baru: hasil belum terealisasi hanya
    # terpengaruh biaya, bukan "rugi" 1.160.000.
    assert satu.hasil_belum_terealisasi is not None
    assert abs(satu.hasil_belum_terealisasi) < 10_000


def test_lembar_yang_tidak_bulat_dilaporkan_bukan_dibulatkan(siap: sqlite3.Connection) -> None:
    """Reverse split 3:1 atas 1.000 lembar = 333⅓ — dibulatkan diam-diam berarti mengubah risiko."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _split(lama=3, baru=1))

    satu = _ringkas(siap)

    assert satu.lembar_terbuka == Fraction(1_000, 3)
    assert satu.hitungan.lembar_terbuka_bulat is None
    assert "LEMBAR TIDAK BULAT" in satu.ringkas()


def test_stop_baris_lama_tanpa_basis_dan_ada_split_tidak_dinilai(siap: sqlite3.Connection) -> None:
    """Basis stop yang tidak pernah dinyatakan **tidak** ditebak ketika ada split sesudahnya."""
    _beli(siap, lembar=1_000)
    posisi.ubah_stop(siap, 1, 2_200, tanggal=TGL_BASIS_STOP)
    # Baris lama: `tgl_stop` kosong **dan** barisnya ditulis sebelum split — itulah keadaan basis
    # data sebelum migrasi 013, dan justru di situ angkanya menjadi ambigu.
    siap.execute("DROP TRIGGER trg_posisi_update_append_only")
    siap.execute(
        "UPDATE posisi SET tgl_stop = NULL, diketahui_pada = '2026-06-15T09:00:00+07:00'"
        " WHERE id_posisi = 1"
    )
    _simpan_aksi(siap, _split())

    satu = _ringkas(siap)

    assert satu.posisi.stop_terkini == 2_200
    assert satu.stop.nilai is None
    assert satu.stop.alasan is not None and "basis" in satu.stop.alasan
    assert satu.risiko_terbuka is None
    assert "TIDAK DINILAI" in satu.ringkas()


def test_stop_baris_lama_tanpa_split_tetap_dinilai(siap: sqlite3.Connection) -> None:
    """Tanpa split sesudahnya, tidak ada yang ambigu: angkanya sudah dalam basis sekarang."""
    _beli(siap, lembar=1_000)
    posisi.ubah_stop(siap, 1, 2_200, tanggal=TGL_BASIS_STOP)
    siap.execute("DROP TRIGGER trg_posisi_update_append_only")
    siap.execute("UPDATE posisi SET tgl_stop = NULL WHERE id_posisi = 1")

    satu = _ringkas(siap)

    assert satu.stop.nilai == 2_200
    assert satu.stop.disesuaikan is False
    assert satu.risiko_terbuka == 120_000  # (2.320 - 2.200) x 1.000


def test_stop_awal_dari_rencana_memakai_basis_tanggal_rencananya(
    siap: sqlite3.Connection,
) -> None:
    """Stop yang diwarisi rencana dinyatakan dalam basis harga **saat rencana itu dibuat**."""
    from mejasaham import kandidat

    entri = kandidat.buat(
        siap,
        KODE,
        status="watchlist",
        tesis="uji",
        pembatal_fundamental="uji",
        horizon="1 bulan",
        stop_awal=2_180,
        tanggal_tinjau="2026-08-01",
    )
    masukan = risiko.siapkan_masukan(siap, KODE, pada=date(2026, 7, 1))
    hasil, _ = risiko.hitung_untuk(masukan, harga_masuk=CLOSE)
    rencana = risiko.simpan(
        siap,
        hasil,
        id_kandidat=entri.id_kandidat,
        jenis_stop="order_sekuritas",
        id_snapshot=masukan.potret.id_snapshot,
    )

    posisi.catat_transaksi(
        siap,
        KODE,
        "beli",
        harga=CLOSE,
        lembar=1_000,
        mode="nyata",
        tanggal=TGL_BELI,
        id_rencana=rencana.id_rencana,
    )

    baris = siap.execute("SELECT tgl_stop, stop_terkini FROM v_posisi_terkini").fetchone()

    assert baris["stop_terkini"] == rencana.stop
    assert baris["tgl_stop"] == rencana.tanggal


def test_ubah_stop_mencatat_basis_dan_tidak_menuduh_v5_palsu(siap: sqlite3.Connection) -> None:
    """Stop 2.200 (basis pra-split) → 1.200 (basis pascasplit) adalah **kenaikan**, bukan V5.

    Dibandingkan sebagai angka mentah, 1.200 < 2.200 terbaca sebagai penurunan — dan V5 palsu
    itu akan tercatat sebagai pelanggaran yang tidak pernah terjadi.
    """
    _beli(siap, lembar=1_000)
    posisi.ubah_stop(siap, 1, 2_200, tanggal=TGL_BASIS_STOP)
    _simpan_aksi(siap, _split())

    perubahan = posisi.ubah_stop(siap, 1, 1_200, tanggal=date(2026, 6, 25))

    assert perubahan.pelanggaran == ()
    assert perubahan.posisi.tgl_stop == "2026-06-25"
    assert any("basis" in satu for satu in perubahan.catatan)


def test_ubah_stop_tetap_menuduh_v5_bila_basisnya_sama(siap: sqlite3.Connection) -> None:
    """Dalam basis yang sama, menurunkan stop tetap pelanggaran V5 (PRD 9.8)."""
    _beli(siap, lembar=1_000)
    posisi.ubah_stop(siap, 1, 2_200, tanggal=TGL_BASIS_STOP)

    perubahan = posisi.ubah_stop(siap, 1, 2_000, tanggal=date(2026, 6, 16))

    assert perubahan.pelanggaran == ("V5",)


# ---------------------------------------------------------------------------------------
# Dividen — arus kas yang dihitung, dengan sumbernya disebut
# ---------------------------------------------------------------------------------------


def test_dividen_dihitung_dari_lembar_pada_tanggal_ex_date(siap: sqlite3.Connection) -> None:
    """Hanya dividen yang jatuh **selama** posisi dipegang, dan jumlahnya lembar saat itu."""
    _simpan_aksi(
        siap,
        _dividen(KODE, date(2026, 5, 1), 50),  # sebelum posisi dibuka
        _dividen(KODE, date(2026, 6, 15), 40),  # selama dipegang
    )
    _beli(siap, lembar=1_000)  # 2026-06-10

    satu = _ringkas(siap)

    assert satu.dividen.total == 40_000
    assert len(satu.dividen.peristiwa) == 1
    assert satu.dividen.peristiwa[0].tanggal == date(2026, 6, 15)
    assert satu.dividen.peristiwa[0].lembar == 1_000
    assert satu.dividen.sumber == (SUMBER,)


def test_dividen_tidak_memakai_pembelian_pada_tanggal_ex_date(siap: sqlite3.Connection) -> None:
    """Membeli **pada** hari ex-date tidak memberi hak atas dividen hari itu."""
    _simpan_aksi(siap, _dividen(KODE, TGL_BELI, 40))
    _beli(siap, lembar=1_000, tanggal=TGL_BELI)  # beli tepat pada tanggal ex-date

    satu = _ringkas(siap)

    assert satu.dividen.total == 0
    assert not satu.dividen.ada
    assert satu.dividen.catatan is not None


def test_dividen_ikut_diskalakan_oleh_split(siap: sqlite3.Connection) -> None:
    """`dividen_per_saham` tersimpan dalam basis sekarang, jadi pasangannya lembar basis sekarang.

    Beli 1.000 lembar, dividen Rp 50/lembar (basis kini), lalu split 1:2. Nilai dividennya tetap
    Rp 50.000: 50 × (1.000 lembar yang diskalakan menjadi 2.000 × harga yang separuh).
    """
    _simpan_aksi(siap, _dividen(KODE, date(2026, 6, 15), 50), _split())
    _beli(siap, lembar=1_000)

    satu = _ringkas(siap)

    assert satu.dividen.peristiwa[0].lembar == 2_000
    assert satu.dividen.total == 100_000


def test_dividen_tanpa_baris_mengatakan_sumbernya_bukan_nol(siap: sqlite3.Connection) -> None:
    """Tidak ada baris dividen = sumbernya belum menyatakan, bukan "tidak pernah membagi"."""
    _beli(siap, lembar=1_000)

    satu = _ringkas(siap)

    assert satu.dividen.total == 0
    assert satu.dividen.catatan is not None and "tidak menyatakan" in satu.dividen.catatan


def test_dividen_bruto_dan_pajaknya_tidak_dikarang(siap: sqlite3.Connection) -> None:
    """PPh dividen bergantung status wajib pajak — bukan parameter bursa; ia tidak dihitung."""
    _simpan_aksi(siap, _dividen(KODE, date(2026, 6, 15), 100))
    _beli(siap, lembar=1_000)

    satu = _ringkas(siap)

    assert satu.dividen.total == 100_000
    assert "bruto" in satu.dividen.ringkas()
    assert "pajak" in satu.dividen.ringkas()


def test_dividen_masuk_hasil_sebagai_suku_terpisah(siap: sqlite3.Connection) -> None:
    """Dividen bukan hasil perdagangan: ia tampil sebagai barisnya sendiri, dan dijumlahkan."""
    _simpan_aksi(siap, _dividen(KODE, date(2026, 6, 15), 40))
    _beli(siap, lembar=1_000)

    isi = posisi.ringkasan_semua(siap, status="aktif")
    teks = posisi.ringkas_daftar(isi)

    assert "dividen diterima" in teks
    assert "dividen diterima Rp 40.000 (bruto)" in teks
    assert isi[0].hasil_terealisasi is None  # belum ada penjualan


# ---------------------------------------------------------------------------------------
# Right issue — hak (petunjuk), tenggat, dan keputusan manual
# ---------------------------------------------------------------------------------------


def _posisi_lalu_right_issue(sambungan: sqlite3.Connection, **ganti: object) -> posisi.HakRightIssue:
    _beli(sambungan, lembar=1_000)
    _simpan_aksi(sambungan, _right_issue(**ganti))  # type: ignore[arg-type]
    hak = posisi.hak_right_issue(sambungan, hari_ini=date(2026, 7, 1))
    assert len(hak) == 1
    return hak[0]


def test_hak_right_issue_dihitung_dari_rasio_dan_lembar(siap: sqlite3.Connection) -> None:
    """Rasio 5:2 atas 1.000 lembar = 400 lembar hak, dan biaya tebusnya ikut disebut."""
    hak = _posisi_lalu_right_issue(siap, lama=5, baru=2, harga_tebus=1_000)

    assert hak.lembar_hak == 400
    assert hak.biaya_tebus == 400_000
    assert hak.tenggat == date(2026, 7, 10)
    assert hak.sudah_diputuskan is False
    assert "BELUM DIPUTUSKAN" in hak.ringkas()


def test_hak_tidak_muncul_bila_posisi_dibuka_setelah_tanggal_aksi(siap: sqlite3.Connection) -> None:
    """Right issue menyentuh pemegangnya; posisi yang belum ada saat itu bukan pemegang."""
    _beli(siap, lembar=1_000, tanggal=date(2026, 6, 26))
    _simpan_aksi(siap, _right_issue(tanggal=date(2026, 6, 25)))

    assert posisi.hak_right_issue(siap, hari_ini=date(2026, 7, 1)) == ()


def test_tenggat_yang_tidak_dinyatakan_disebut_bukan_dianggap_tidak_ada(
    siap: sqlite3.Connection,
) -> None:
    """Tenggat kosong tetap memunculkan tindakan: jendelanya bisa saja sudah sempit."""
    hak = _posisi_lalu_right_issue(siap, tenggat=None)

    assert hak.tenggat is None
    assert "BELUM DINYATAKAN" in hak.ringkas()


def test_hak_yang_bukan_kelipatan_lot_disebut_lebih_awal(siap: sqlite3.Connection) -> None:
    """P26: hak 625 lembar dari rasio 8:5 tidak bisa ditebus seluruhnya (lot 100).

    Aturannya tidak berubah — PRD 10 tetap menolak pencatatan 625 lembar. Yang berubah: pengguna
    tahu di sini, bukan baru saat `--catat-transaksi` menolaknya.
    """
    hak = _posisi_lalu_right_issue(siap, lama=8, baru=5, harga_tebus=1_000)

    assert hak.lembar_hak == 625
    assert hak.lot == 100
    assert hak.lembar_hak_patut_lot == 600
    catatan = hak.catatan_lot()
    assert catatan is not None and "BUKAN kelipatan lot 100" in catatan and "600" in catatan
    assert "BUKAN kelipatan lot" in hak.ringkas()

    tindakan = dasbor.tindakan_menunggu(
        siap, posisi.ringkasan_semua(siap, status="aktif"), hari_ini=date(2026, 7, 1)
    )
    assert any("BUKAN kelipatan lot" in satu.pesan for satu in tindakan)


def test_hak_yang_sudah_bulat_lot_tidak_diberi_catatan(siap: sqlite3.Connection) -> None:
    """Catatan hanya muncul ketika memang ada yang perlu diketahui — bukan selalu."""
    hak = _posisi_lalu_right_issue(siap, lama=5, baru=2)

    assert hak.lembar_hak == 400
    assert hak.catatan_lot() is None
    assert "kelipatan lot" not in hak.ringkas()


def test_keputusan_tebus_menuntut_transaksi(siap: sqlite3.Connection) -> None:
    """Menebus = membeli lembar; tanpa transaksi, lembar yang ditebus tidak ada di buku mana pun."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue())

    with pytest.raises(posisi.GalatPosisi, match="--id-transaksi"):
        posisi.catat_keputusan_right_issue(siap, KODE, date(2026, 6, 25), "tebus")


def test_keputusan_tebus_menunjuk_transaksi_posisi_lain_ditolak(siap: sqlite3.Connection) -> None:
    """Transaksi yang ditunjuk harus benar-benar milik posisi itu."""
    _beli(siap, lembar=1_000)
    lain = _beli(siap, KODE_LAIN, lembar=1_000)
    _simpan_aksi(siap, _right_issue())

    with pytest.raises(posisi.GalatPosisi, match="milik posisi"):
        posisi.catat_keputusan_right_issue(
            siap, KODE, date(2026, 6, 25), "tebus", id_transaksi=lain.transaksi.id_transaksi
        )


def test_keputusan_tebus_menolak_isian_yang_tidak_dipakai(siap: sqlite3.Connection) -> None:
    """K71: `tebus` tidak memakai lembar/harga/biaya — isiannya ditolak, bukan dibuang diam-diam.

    Yang menaikkan lembar posisi adalah transaksinya (T51), bukan keputusan ini. Sesi 18
    mengukur jalur baris perintah menerimanya lalu keluar 0 tanpa pesan, sedangkan jendela
    sudah menolaknya; aturan yang sama kini berlaku di inti untuk **semua** keputusan selain
    `jual_hmetd`.
    """
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue(harga_tebus=2_400))
    beli_hak = posisi.catat_transaksi(
        siap, KODE, "beli", harga=2_400, lembar=400, mode="nyata", tanggal=date(2026, 6, 26)
    )

    for isian in ({"lembar": 400}, {"harga": 2_400}, {"biaya": 1_000}):
        with pytest.raises(posisi.GalatPosisi, match=r"transaksinya \(T51\)"):
            posisi.catat_keputusan_right_issue(
                siap,
                KODE,
                date(2026, 6, 25),
                "tebus",
                id_transaksi=beli_hak.transaksi.id_transaksi,
                **isian,
            )

    assert siap.execute("SELECT COUNT(*) FROM keputusan_right_issue").fetchone()[0] == 0, (
        "isian yang ditolak tidak boleh meninggalkan baris keputusan"
    )


def test_baris_perintah_tebus_dengan_lembar_keluar_gagal(
    siap: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """K71: jalur baris perintah berhenti **berisik**, bukan keluar 0 tanpa pesan.

    Sesi 18 mengukur `--putuskan-right-issue … --keputusan tebus --lembar 500` keluar 0 dan
    lembarnya hilang tanpa sepatah kata pun; uji ini menjaga gejala yang terlihat pengguna.
    """
    from mejasaham import cli

    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue(harga_tebus=2_400))
    beli_hak = posisi.catat_transaksi(
        siap, KODE, "beli", harga=2_400, lembar=400, mode="nyata", tanggal=date(2026, 6, 26)
    )

    kode = cli.main(
        [
            "--putuskan-right-issue",
            KODE,
            "--tanggal-aksi",
            "2026-06-25",
            "--keputusan",
            "tebus",
            "--id-transaksi",
            str(beli_hak.transaksi.id_transaksi),
            "--lembar",
            "400",
        ]
    )

    assert kode == cli.KODE_GAGAL
    assert "transaksinya (T51)" in capsys.readouterr().err
    assert siap.execute("SELECT COUNT(*) FROM keputusan_right_issue").fetchone()[0] == 0


def test_keputusan_tebus_tersimpan_dan_menunjuk_transaksinya(siap: sqlite3.Connection) -> None:
    """Jalur lengkap: catat pembelian lembar HMETD, lalu putuskan `tebus`."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue(harga_tebus=2_400))
    beli_hak = posisi.catat_transaksi(
        siap,
        KODE,
        "beli",
        harga=2_400,
        lembar=400,
        mode="nyata",
        tanggal=date(2026, 6, 26),
    )

    hasil = posisi.catat_keputusan_right_issue(
        siap,
        KODE,
        date(2026, 6, 25),
        "tebus",
        id_transaksi=beli_hak.transaksi.id_transaksi,
    )

    assert hasil.keputusan.keputusan == "tebus"
    assert hasil.keputusan.id_transaksi == beli_hak.transaksi.id_transaksi
    assert hasil.keputusan.lembar is None and hasil.keputusan.harga is None
    assert _ringkas(siap).lembar_terbuka == 1_400


def test_keputusan_jual_hmetd_menyimpan_lembar_harga_biaya_dan_hasil(
    siap: sqlite3.Connection,
) -> None:
    """Menjual **hak** bukan menjual lembar: ia tidak mengurangi lembar posisi."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue())

    hasil = posisi.catat_keputusan_right_issue(
        siap,
        KODE,
        date(2026, 6, 25),
        "jual_hmetd",
        lembar=400,
        harga=150,
        biaya=1_000,
    )

    assert hasil.keputusan.hasil_penjualan == 59_000
    assert _ringkas(siap).lembar_terbuka == 1_000


def test_keputusan_jual_hmetd_menuntut_lembar_dan_harga(siap: sqlite3.Connection) -> None:
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue())

    with pytest.raises(posisi.GalatPosisi, match="--lembar dan --harga"):
        posisi.catat_keputusan_right_issue(siap, KODE, date(2026, 6, 25), "jual_hmetd", lembar=400)


def test_keputusan_abaikan_menolak_lembar_dan_harga(siap: sqlite3.Connection) -> None:
    """`abaikan` tidak punya jumlah maupun harga; menerimanya lalu membuangnya diam-diam = gagal senyap."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue())

    with pytest.raises(posisi.GalatPosisi, match="tidak memakai --lembar"):
        posisi.catat_keputusan_right_issue(
            siap, KODE, date(2026, 6, 25), "abaikan", lembar=400, harga=150
        )


def test_right_issue_yang_tidak_tercatat_ditolak_berisik(siap: sqlite3.Connection) -> None:
    """Keputusan harus menempel pada peristiwa yang benar-benar ada di basis data."""
    _beli(siap, lembar=1_000)

    with pytest.raises(posisi.GalatPosisi, match="tidak ada right issue"):
        posisi.catat_keputusan_right_issue(siap, KODE, date(2026, 6, 25), "abaikan")


def test_keputusan_yang_berubah_menambah_revisi_bukan_menimpa(siap: sqlite3.Connection) -> None:
    """PRD 9.8: yang lama disimpan, bukan dihapus — keputusan pun begitu."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue())
    pertama = posisi.catat_keputusan_right_issue(siap, KODE, date(2026, 6, 25), "abaikan")

    kedua = posisi.catat_keputusan_right_issue(
        siap, KODE, date(2026, 6, 25), "jual_hmetd", lembar=400, harga=150, biaya=0
    )

    assert kedua.keputusan.id_keputusan == pertama.keputusan.id_keputusan
    assert kedua.keputusan.revisi == 2
    jumlah = siap.execute(
        "SELECT COUNT(*) FROM keputusan_right_issue WHERE id_keputusan = ?",
        (pertama.keputusan.id_keputusan,),
    ).fetchone()[0]
    assert jumlah == 2
    assert kedua.keputusan.catatan is not None and "abaikan" in kedua.keputusan.catatan


def test_catatan_turunan_tidak_diulang_tiap_revisi(siap: sqlite3.Connection) -> None:
    """K72: catatan turunan yang kalimatnya sudah ada tidak disalin lagi tiap revisi.

    Riwayat lengkap sudah tersimpan di baris revisinya masing-masing (append-only); menyalin
    kalimat yang sama ke revisi berikutnya membuat revisi ke-5 memuatnya lima kali. Catatan
    yang **dinyatakan pengguna** tetap disambung apa adanya.
    """
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue(tenggat=None))

    for _ in range(3):
        posisi.catat_keputusan_right_issue(
            siap,
            KODE,
            date(2026, 6, 25),
            "jual_hmetd",
            lembar=400,
            harga=150,
            catatan="alasan saya",
        )

    baris = [
        satu["catatan"]
        for satu in siap.execute("SELECT catatan FROM keputusan_right_issue ORDER BY revisi")
    ]
    assert len(baris) == 3
    for isi in baris:
        assert isi.count("biaya penjualan hak belum dicatat") == 1
        assert isi.count("tenggat right issue ini belum dinyatakan sumbernya") == 1
    # Catatan pengguna tetap disambung apa adanya (K72), jadi ia bertambah satu tiap revisi.
    assert [isi.count("alasan saya") for isi in baris] == [1, 2, 3]


# ---------------------------------------------------------------------------------------
# Dasbor: right issue sebagai tindakan menunggu, dan yang tenggatnya sudah lewat
# ---------------------------------------------------------------------------------------


def test_dasbor_menampilkan_right_issue_sebagai_tindakan_menunggu(
    siap: sqlite3.Connection,
) -> None:
    """P16: right issue dengan tenggat masuk daftar tindakan — lengkap dengan sisa harinya."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue(tenggat="2026-07-10"))

    laporan = dasbor.susun(siap, hari_ini=date(2026, 7, 1))
    jenis = [satu.jenis for satu in laporan.tindakan]

    assert "right_issue_belum_diputuskan" in jenis
    assert "9 hari lagi" in laporan.ringkas()


def test_right_issue_yang_tenggatnya_lewat_jadi_catatan_bukan_tindakan(
    siap: sqlite3.Connection,
) -> None:
    """Jendela yang sudah tertutup bukan tindakan hari ini — tetapi lubangnya tetap disebut."""
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue(tanggal=date(2026, 6, 25), tenggat="2026-06-28"))

    laporan = dasbor.susun(siap, hari_ini=date(2026, 7, 1))

    assert "right_issue_belum_diputuskan" not in [satu.jenis for satu in laporan.tindakan]
    assert any("tenggatnya sudah lewat" in satu for satu in laporan.catatan)


def test_right_issue_yang_sudah_diputuskan_tidak_lagi_menunggu(siap: sqlite3.Connection) -> None:
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue(tenggat="2026-07-10"))
    posisi.catat_keputusan_right_issue(siap, KODE, date(2026, 6, 25), "abaikan")

    laporan = dasbor.susun(siap, hari_ini=date(2026, 7, 1))

    assert "right_issue_belum_diputuskan" not in [satu.jenis for satu in laporan.tindakan]


def test_dasbor_menyebut_dividen_yang_dihitung_beserta_sumbernya(siap: sqlite3.Connection) -> None:
    _simpan_aksi(siap, _dividen(KODE, date(2026, 6, 15), 40))
    _beli(siap, lembar=1_000)

    laporan = dasbor.susun(siap, hari_ini=date(2026, 7, 1))

    assert any("dividen yang dihitung atas posisi aktif" in satu for satu in laporan.catatan)
    assert "Rp 40.000" in laporan.ringkas()


# ---------------------------------------------------------------------------------------
# Mesin yang menegakkan bentuknya (migrasi 013)
# ---------------------------------------------------------------------------------------


def test_keputusan_right_issue_append_only(siap: sqlite3.Connection) -> None:
    _beli(siap, lembar=1_000)
    _simpan_aksi(siap, _right_issue())
    hasil = posisi.catat_keputusan_right_issue(siap, KODE, date(2026, 6, 25), "abaikan")

    for operasi in ("UPDATE", "DELETE"):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            if operasi == "UPDATE":
                siap.execute("UPDATE keputusan_right_issue SET catatan = 'x' WHERE id_keputusan = 1")
            else:
                siap.execute("DELETE FROM keputusan_right_issue WHERE id_keputusan = 1")
    assert hasil.keputusan.id_keputusan == 1


def test_tebus_tanpa_transaksi_ditolak_mesin(siap: sqlite3.Connection) -> None:
    """`CHECK` menegakkannya, bukan hanya modul — supaya jalur tulis mana pun ikut terjaga."""
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO keputusan_right_issue (id_keputusan, revisi, id_posisi, kode,"
            " tanggal_aksi, keputusan, sumber, diketahui_pada)"
            " VALUES (9, 1, 1, 'AAAA', '2026-06-25', 'tebus', 'uji', '2026-07-01T09:00:00+07:00')"
        )


def test_jual_hmetd_tanpa_lembar_dan_harga_ditolak_mesin(siap: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO keputusan_right_issue (id_keputusan, revisi, id_posisi, kode,"
            " tanggal_aksi, keputusan, sumber, diketahui_pada)"
            " VALUES (9, 1, 1, 'AAAA', '2026-06-25', 'jual_hmetd', 'uji',"
            " '2026-07-01T09:00:00+07:00')"
        )


def test_abaikan_dengan_lembar_ditolak_mesin(siap: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO keputusan_right_issue (id_keputusan, revisi, id_posisi, kode,"
            " tanggal_aksi, keputusan, lembar, harga, sumber, diketahui_pada)"
            " VALUES (9, 1, 1, 'AAAA', '2026-06-25', 'abaikan', 400, 150, 'uji',"
            " '2026-07-01T09:00:00+07:00')"
        )


def test_daftar_keputusan_sah_sepakat_dengan_check_skema(siap: sqlite3.Connection) -> None:
    """Satu tempat untuk daftar nilainya; SQL migrasi tidak boleh menyimpang darinya (T9)."""
    for nomor, keputusan in enumerate(KEPUTUSAN_RIGHT_ISSUE_SAH, start=1):
        siap.execute(
            "INSERT INTO keputusan_right_issue (id_keputusan, revisi, id_posisi, kode,"
            " tanggal_aksi, keputusan, id_transaksi, lembar, harga, sumber, diketahui_pada)"
            " VALUES (?, 1, 1, 'AAAA', '2026-06-25', ?, ?, ?, ?, 'uji',"
            " '2026-07-01T09:00:00+07:00')",
            (
                nomor,
                keputusan,
                7 if keputusan == "tebus" else None,
                400 if keputusan == "jual_hmetd" else None,
                150 if keputusan == "jual_hmetd" else None,
            ),
        )
    assert siap.execute("SELECT COUNT(*) FROM keputusan_right_issue").fetchone()[0] == len(
        KEPUTUSAN_RIGHT_ISSUE_SAH
    )
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO keputusan_right_issue (id_keputusan, revisi, id_posisi, kode,"
            " tanggal_aksi, keputusan, sumber, diketahui_pada)"
            " VALUES (99, 1, 1, 'AAAA', '2026-06-25', 'karangan', 'uji',"
            " '2026-07-01T09:00:00+07:00')"
        )


def test_tenggat_hanya_berlaku_untuk_right_issue(siap: sqlite3.Connection) -> None:
    """Tenggat pada aksi lain tidak akan pernah dinilai; berkas impor menolaknya lebih dulu."""
    from mejasaham import berkas

    with pytest.raises(ingesti.GalatIngesti, match="tenggat"):
        berkas._baris_aksi(
            {"kode": "AAAA", "tanggal": "2026-06-20", "jenis": "split", "rasio_lama": "1",
             "rasio_baru": "2", "tenggat": "2026-07-10"},
            "uji.csv:2",
        )


def test_tenggat_dan_basis_stop_dijaga_check(siap: sqlite3.Connection) -> None:
    """Tanggal yang bentuknya salah ditolak mesin, bukan tersimpan diam-diam."""
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO aksi_korporasi (kode, tanggal, jenis, rasio_lama, rasio_baru, tenggat,"
            " sumber, diketahui_pada)"
            " VALUES ('AAAA', '2026-06-20', 'split', 1, 2, '10 Juli 2026', 'uji',"
            " '2026-07-01T09:00:00+07:00')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        siap.execute(
            "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, status, stop_terkini,"
            " tgl_stop, mode, sumber, diketahui_pada)"
            " VALUES (9, 1, 'AAAA', '2026-06-10', 'aktif', 2200, '15 Juni 2026', 'nyata', 'uji',"
            " '2026-07-01T09:00:00+07:00')"
        )
