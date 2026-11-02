"""Uji ingesti, mutu data, dan arsip snapshot (F1, PRD 7.2, 7.3, 9.3, 9.13).

Yang diuji di sini bukan "apakah fungsinya jalan", melainkan janji-janji yang membuat Tahap 0
layak dipercaya sebagai fondasi:

* ingesti yang sama dijalankan dua kali **tidak** menumpuk baris (kalau menumpuk, "terkini"
  tidak lagi bermakna dan laporan mutu menghitung ganda);
* nilai yang tidak ada menjadi `None`, **bukan** nol (aturan keras 1);
* nilai berpecahan tidak dibulatkan diam-diam (T8);
* label "tidak resmi" menempel di setiap baris, bukan hanya di log (PRD 7.2);
* kegagalan menulis snapshot tidak meninggalkan data separuh (A6, AC-19);
* emiten yang datanya bolong keluar dari peringkat (PRD 7.3, AC-1);
* arsip snapshot tidak bisa tertimpa arsip snapshot lain (PRD 7.2).

Seluruh uji di berkas ini berjalan **tanpa jaringan**: pengambil data disuntikkan sebagai
objek palsu, sehingga aturan ingestinya bisa diuji tanpa bergantung pada penyedia mana pun.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import arsip, berkas, db, ingesti, lokasi, mutu, pengambil, pengatur
from mejasaham.ingesti import (
    KEGAGALAN_PERMANEN,
    KEGAGALAN_SEMENTARA,
    PENYESUAIAN_SPLIT,
    SUMBER_YFINANCE,
    AksiKorporasi,
    CatatanAksiMutu,
    Emiten,
    GalatIngesti,
    HariBursa,
    HargaHarian,
    ImbalHasilSUN,
    IngestiDibatalkan,
    Kegagalan,
    KumpulanData,
    NotasiKhusus,
    PenutupanIndeks,
    RasioBank,
)

TANGGAL = date(2026, 10, 9)
TANGGAL_LALU = date(2026, 10, 8)
MOMEN = datetime(2026, 10, 9, 18, 0, 0)
#: Momen kedua yang **berbeda detik** dari `MOMEN`. Diperlukan karena `diketahui_pada` disimpan
#: dengan ketelitian detik (T12): dua penulisan dalam detik yang sama tidak bisa menjadi dua
#: revisi — kunci utamanya sama persis, jadi yang kedua memang tidak ditulis.
MOMEN_LANJUT = datetime(2026, 10, 9, 18, 0, 1)
SUMBER_IMPOR = "impor berkas: D:\\impor"

EMITEN_UJI = (
    Emiten(kode="AAAA", nama="Alpha Sentosa", sumber="uji", dicatat_pada=date(2026, 10, 1)),
    Emiten(kode="BBBB", nama="Beta Mandiri", sumber="uji", dicatat_pada=date(2026, 10, 1)),
)


class PengambilPalsu:
    """Pengganti `PengambilYFinance`: memenuhi kontrak yang sama tanpa menyentuh jaringan."""

    def __init__(self, kumpulan: KumpulanData) -> None:
        self.kumpulan = kumpulan
        self.diminta: tuple[str, ...] = ()

    def ambil(self, emiten: Sequence[Emiten]) -> KumpulanData:
        """Memenuhi kontrak yang sama dengan `PengambilYFinance.ambil`.

        Termasuk membawa serta daftar emitennya: itulah yang membuat baris rujukan emiten ikut
        tersimpan, sama seperti jalur sungguhan. Pengambil palsu yang tidak melakukannya akan
        membuat uji lolos atas perilaku yang tidak pernah terjadi di produksi.
        """
        self.diminta = tuple(satu.kode for satu in emiten)
        return replace(self.kumpulan, emiten=tuple(emiten))


def _harga(
    kode: str,
    tanggal: date = TANGGAL,
    *,
    close: int = 1000,
    volume: int = 1_000_000,
    **lain: object,
) -> HargaHarian:
    return HargaHarian(kode=kode, tanggal=tanggal, close=close, volume=volume, **lain)  # type: ignore[arg-type]


def _kumpulan(*harga: HargaHarian, sumber: str = SUMBER_YFINANCE, **lain: object) -> KumpulanData:
    return KumpulanData(sumber=sumber, harga_harian=harga, **lain)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------
# Piranti uji
# ---------------------------------------------------------------------------------------


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Folder data di luar paket (A3), ditimpa lewat MEJASAHAM_DATA seperti di produksi."""
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
def folder_impor(folder_data: Path) -> Path:
    folder = folder_data / "konfigurasi"
    lokasi.pastikan_folder(folder)
    return folder


def _tulis_emiten(folder: Path, *kode: str) -> Path:
    baris = "\n".join(
        f"{satu};Emiten {satu};;;;;;;Daftar uji;2026-10-01" for satu in (kode or ("AAAA", "BBBB"))
    )
    jalur = folder / "emiten.csv"
    jalur.write_text(
        "kode;nama;sektor_idx_ic;jenis;papan;status_notasi;jumlah_saham;free_float_persen;"
        "sumber;dicatat_pada\n" + baris + "\n",
        encoding="utf-8",
    )
    return jalur


# ---------------------------------------------------------------------------------------
# Idempoten: uji regresi untuk bug "diketahui_pada selalu baru"
# ---------------------------------------------------------------------------------------


def test_menjalankan_ingesti_dua_kali_tidak_menumpuk_baris(
    sambungan: sqlite3.Connection,
) -> None:
    """Uji regresi.

    Setiap jalan ingesti memakai `diketahui_pada` = jam berjalan, jadi pencarian "baris ini
    sudah ada?" **tidak boleh** memakai kunci lengkap yang memuat `diketahui_pada`. Kalau
    memakainya, tidak ada satu pun baris yang cocok, seluruh data ditulis ulang, dan
    `(kode, tanggal)` berakhir dengan dua revisi identik:

    * `v_harga_harian_terkini` menjadi tidak bermakna (dua revisi berisi hal yang sama),
    * laporan mutu menghitung setiap bar dua kali,
    * ingesti harian menggelembungkan basis data tanpa menambah informasi.

    Karena itu baris kedua harus melaporkan 0 baris baru.
    """
    kumpulan = _kumpulan(_harga("AAAA"), _harga("AAAA", TANGGAL_LALU, close=990))

    pertama = ingesti.simpan(sambungan, kumpulan, tanggal_data=TANGGAL)
    kedua = ingesti.simpan(sambungan, kumpulan, tanggal_data=TANGGAL)

    assert pertama.baris.total_baru == 2
    assert kedua.baris.total_baru == 0, "ingesti ulang tidak boleh menambah baris"
    assert kedua.baris.total_tetap == 2
    assert sambungan.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0] == 2
    assert sambungan.execute("SELECT COUNT(*) FROM v_harga_harian_terkini").fetchone()[0] == 2


def test_data_yang_berubah_menambah_revisi_bukan_menimpa(sambungan: sqlite3.Connection) -> None:
    """S1: perbaikan data menambah baris baru; angka lama tetap bisa ditelusuri.

    Dua penulisan dilakukan pada momen yang **berbeda detik**: `diketahui_pada` berketelitian
    detik, dan dua penulisan dalam detik yang sama akan bertabrakan di kunci utama tabel.
    """
    ingesti.simpan(
        sambungan, _kumpulan(_harga("AAAA", close=1000)), tanggal_data=TANGGAL, momen=MOMEN
    )
    ingesti.simpan(
        sambungan, _kumpulan(_harga("AAAA", close=1010)), tanggal_data=TANGGAL, momen=MOMEN_LANJUT
    )

    semua = sambungan.execute("SELECT close FROM harga_harian ORDER BY diketahui_pada").fetchall()
    terkini = sambungan.execute("SELECT close FROM v_harga_harian_terkini").fetchall()

    assert [satu[0] for satu in semua] == [1000, 1010], "nilai lama tidak boleh hilang"
    assert [satu[0] for satu in terkini] == [1010], "yang dipakai adalah revisi terakhir"


def test_perbaikan_tanggal_notasi_saja_menambah_revisi(sambungan: sqlite3.Connection) -> None:
    """S3 untuk kolom baru: koreksi satu kolom pun harus menjadi baris baru, bukan diam.

    Keadaan yang diuji adalah keadaan nyata: dua impor berkas rujukan pada tanggal pencatatan
    berbeda, yang **hanya** berbeda di kolom `tanggal_notasi`. Kolom yang tidak ikut disidik
    `_ISI_PER_TABEL` membuat baris kedua dinyatakan "sudah ada dan sama" lalu dibuang — koreksinya
    hilang tanpa satu pun pesan, dan yang terpakai tetap nilai lama.
    """
    def kumpulan(dicatat: date, tanggal: date | None) -> ingesti.KumpulanData:
        return _kumpulan(
            _harga("AAAA"),
            emiten=(
                Emiten(
                    kode="AAAA",
                    nama="Alpha Sentosa",
                    tanggal_notasi=tanggal,
                    sumber="uji",
                    dicatat_pada=dicatat,
                ),
            ),
        )

    ingesti.simpan(
        sambungan, kumpulan(date(2026, 10, 1), date(1989, 11, 25)), tanggal_data=TANGGAL, momen=MOMEN
    )
    ingesti.simpan(
        sambungan,
        kumpulan(date(2026, 10, 2), date(1989, 11, 26)),
        tanggal_data=TANGGAL,
        momen=MOMEN_LANJUT,
    )

    semua = sambungan.execute("SELECT tanggal_notasi FROM emiten ORDER BY diketahui_pada").fetchall()
    terkini = sambungan.execute(
        "SELECT tanggal_notasi FROM v_emiten_terkini WHERE kode = 'AAAA'"
    ).fetchall()

    assert [satu[0] for satu in semua] == ["1989-11-25", "1989-11-26"], "revisi lama tetap ada"
    assert [satu[0] for satu in terkini] == ["1989-11-26"], "yang dipakai revisi terbaru"


def test_revisi_emiten_pada_tanggal_catat_yang_sama_memakai_waktu_ingesti(
    sambungan: sqlite3.Connection,
) -> None:
    """Tanggal sumber bukan cap waktu DB; koreksi pada tanggal yang sama tetap append-only."""
    def kumpulan(jenis: str) -> ingesti.KumpulanData:
        return _kumpulan(
            _harga("AAAA"),
            emiten=(
                Emiten(
                    kode="AAAA",
                    nama="Alpha Sentosa",
                    jenis=jenis,
                    sumber=f"daftar sumber; jenis={jenis}",
                    dicatat_pada=date(2026, 10, 9),
                ),
            ),
        )

    ingesti.simpan(
        sambungan,
        kumpulan("umum"),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    ingesti.simpan(
        sambungan,
        kumpulan("bank_keuangan"),
        tanggal_data=TANGGAL,
        momen=MOMEN_LANJUT,
    )

    revisi = sambungan.execute(
        "SELECT jenis, sumber, diketahui_pada FROM emiten WHERE kode = 'AAAA' "
        "ORDER BY diketahui_pada"
    ).fetchall()

    assert [(satu[0], satu[2]) for satu in revisi] == [
        ("umum", db.waktu_iso(MOMEN)),
        ("bank_keuangan", db.waktu_iso(MOMEN_LANJUT)),
    ]
    assert [satu[1] for satu in revisi] == [
        "daftar sumber; jenis=umum",
        "daftar sumber; jenis=bank_keuangan",
    ], "provenance sumber tetap melekat pada setiap revisi"


def test_setiap_kolom_tabel_ikut_disidik_saat_menulis(sambungan: sqlite3.Connection) -> None:
    """Penjaga `_ISI_PER_TABEL`: seluruh kolom tabel harus terdaftar, kecuali kolom kuncinya.

    Uji ini sengaja membaca peta pribadi `ingesti._ISI_PER_TABEL`: yang diperiksa memang
    daftarnya, bukan perilaku satu jalur tulis. Tanpa penjaga ini, menambah kolom ke skema
    (seperti `tanggal_notasi`) dan lupa mendaftarkannya di situ tidak menimbulkan galat apa pun —
    hanya koreksi yang tidak pernah tersimpan.

    Tabel yang ditulis jalur lain (`snapshot`, `log_jalan`, `cek_sumber_kedua`, `skor`) memang
    tidak ikut: jalur itu menambah **peristiwa**, bukan merevisi isi yang bisa "sudah ada dan sama".
    """
    kurang: list[str] = []
    for tabel, disidik in ingesti._ISI_PER_TABEL.items():
        info = sambungan.execute(f"PRAGMA table_info({tabel})").fetchall()
        semua = {baris[1] for baris in info}
        kunci = {baris[1] for baris in info if baris[5]}  # kolom kunci utama tabel
        hilang = sorted(semua - set(disidik) - kunci)
        if hilang:
            kurang.append(f"{tabel}: {', '.join(hilang)}")

    assert not kurang, (
        "kolom yang tidak ikut disidik saat menulis (perbaikannya akan hilang tanpa pesan): "
        + "; ".join(kurang)
    )


def test_snapshot_selalu_diterbitkan_walau_datanya_sama(sambungan: sqlite3.Connection) -> None:
    """Menjalankan ulang tetap mencatat **peristiwa** snapshot, walau barisnya tidak bertambah.

    Snapshot adalah batas waktu ("data ini diketahui per jam ini"), bukan salinan data. Karena
    itu ia tetap dicatat — kalau tidak, "kapan terakhir refresh berhasil" tidak bisa dijawab.
    """
    kumpulan = _kumpulan(_harga("AAAA"))

    ingesti.simpan(sambungan, kumpulan, tanggal_data=TANGGAL)
    ingesti.simpan(sambungan, kumpulan, tanggal_data=TANGGAL)

    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 2
    assert sambungan.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0] == 1


# ---------------------------------------------------------------------------------------
# Konversi: tidak ada angka tebakan (aturan keras 1, T8)
# ---------------------------------------------------------------------------------------


def test_nilai_kosong_menjadi_none_bukan_nol(sambungan: sqlite3.Connection) -> None:
    """PRD 7.2: data yang tidak tersedia TIDAK diganti nol.

    Barisnya tetap ditulis supaya lubangnya terlihat di laporan mutu — menghilangkannya
    justru menyembunyikan masalahnya.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(HargaHarian(kode="AAAA", tanggal=TANGGAL, close=None, volume=None)),
        tanggal_data=TANGGAL,
    )

    baris = sambungan.execute("SELECT close, volume, nilai FROM harga_harian").fetchone()

    assert baris["close"] is None and baris["volume"] is None and baris["nilai"] is None


def test_harga_berpecahan_tidak_dibulatkan_diam_diam(sambungan: sqlite3.Connection) -> None:
    """T8: yang berhitung INTEGER, angka aslinya tersimpan untuk audit.

    Nilai mentah datang dari pembentuk baris (`pengambil._baris_harga` /
    `berkas._baris_harga`), jadi di sini ia diberikan apa adanya seperti yang dilakukan
    kedua jalur itu.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(
            HargaHarian(
                kode="AAAA", tanggal=TANGGAL, close=1000, volume=2_500, close_mentah="1000.7"
            )
        ),
        tanggal_data=TANGGAL,
    )

    baris = sambungan.execute("SELECT close, close_mentah FROM harga_harian").fetchone()

    assert baris["close"] == 1000
    assert baris["close_mentah"] == "1000.7", "angka asli tidak boleh hilang tanpa jejak"


def test_nilai_transaksi_dihitung_dari_close_kali_volume(sambungan: sqlite3.Connection) -> None:
    """U6: `nilai` = close x volume kecuali sumber menyediakan nilai eksplisit."""
    ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA", close=1000, volume=2_500)),
        tanggal_data=TANGGAL,
    )

    baris = sambungan.execute("SELECT nilai, asal_nilai FROM harga_harian").fetchone()

    assert baris["nilai"] == 2_500_000
    assert baris["asal_nilai"] == "hitung"


def test_nilai_transaksi_dari_sumber_tidak_dihitung_ulang(sambungan: sqlite3.Connection) -> None:
    """Bila sumber menerbitkan nilai transaksi sendiri, angka itulah yang dipakai (U6)."""
    ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA", close=1000, volume=2_500, nilai=9_999_999)),
        tanggal_data=TANGGAL,
    )

    baris = sambungan.execute("SELECT nilai, asal_nilai FROM harga_harian").fetchone()

    assert baris["nilai"] == 9_999_999
    assert baris["asal_nilai"] == "impor"


def test_harga_negatif_ditolak_dengan_pesan_yang_menyebut_emitennya(
    sambungan: sqlite3.Connection,
) -> None:
    """Harga negatif tidak bermakna: ditolak di titik tulis, bukan lolos jadi galat CHECK SQLite.

    Pesannya harus menyebut emiten dan tanggalnya. Galat CHECK SQLite hanya menyebut nama
    kolom, dan itu tidak menolong siapa pun yang sedang memperbaiki data 800 emiten.
    """
    with pytest.raises(GalatIngesti) as galat:
        ingesti.simpan(
            sambungan,
            _kumpulan(HargaHarian(kode="AAAA", tanggal=TANGGAL, close=-5, close_mentah="-5")),
            tanggal_data=TANGGAL,
        )

    assert "AAAA" in str(galat.value)
    assert str(TANGGAL) in str(galat.value)
    assert "negatif" in str(galat.value)


def test_tidak_ada_baris_yang_hilang_diam_diam_akibat_pelanggaran_aturan(
    sambungan: sqlite3.Connection,
) -> None:
    """Uji regresi: `INSERT OR IGNORE` pernah dipakai di titik tulis.

    `OR IGNORE` menelan **semua** kegagalan constraint, bukan hanya tabrakan kunci utama —
    termasuk CHECK harga negatif. Akibatnya baris yang melanggar aturan hilang tanpa satu pun
    pesan, dan ingesti melaporkan sukses. Aturan keras 7 melarang tepat hal itu.
    """
    with pytest.raises(GalatIngesti):
        ingesti.simpan(
            sambungan,
            _kumpulan(_harga("AAAA"), _harga("BBBB", close=-1)),
            tanggal_data=TANGGAL,
        )

    assert sambungan.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0] == 0


def test_high_di_bawah_low_ditolak(sambungan: sqlite3.Connection) -> None:
    """Baris seperti ini menandakan data sumber rusak; lebih baik berhenti berisik."""
    with pytest.raises(GalatIngesti, match="high"):
        ingesti.simpan(
            sambungan,
            _kumpulan(HargaHarian(kode="AAAA", tanggal=TANGGAL, high=900, low=1000, close=950)),
            tanggal_data=TANGGAL,
        )


# ---------------------------------------------------------------------------------------
# Label sumber tidak resmi (PRD 7.2, 7.3, P2/Q8)
# ---------------------------------------------------------------------------------------


def test_label_tidak_resmi_menempel_di_setiap_baris(sambungan: sqlite3.Connection) -> None:
    """Label sumber harus ikut datanya, bukan hanya tercatat di log."""
    ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA"), _harga("AAAA", TANGGAL_LALU)),
        tanggal_data=TANGGAL,
    )

    sumber = {satu[0] for satu in sambungan.execute("SELECT DISTINCT sumber FROM harga_harian")}

    assert sumber == {SUMBER_YFINANCE}
    assert "tidak resmi" in SUMBER_YFINANCE


def test_ringkasan_mutu_menyebut_sumber_tidak_resmi(sambungan: sqlite3.Connection) -> None:
    """PRD 7.3: laporan mutu menandai bahwa sumbernya tidak resmi."""
    ingesti.simpan(sambungan, _kumpulan(_harga("AAAA")), tanggal_data=TANGGAL)

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL, sumber=SUMBER_YFINANCE)

    jenis = {satu.jenis for satu in laporan.temuan}
    assert "sumber_tidak_resmi" in jenis


# ---------------------------------------------------------------------------------------
# Atomik: gagal di tengah tidak meninggalkan apa pun (A6, AC-19)
# ---------------------------------------------------------------------------------------


def test_kegagalan_di_tengah_tidak_meninggalkan_snapshot_maupun_baris(
    sambungan: sqlite3.Connection,
) -> None:
    """Satu transaksi untuk semuanya: baris, snapshot, dan log.

    Kalau tidak, kegagalan di baris ke-500 dari 800 akan meninggalkan snapshot yang tampak sah
    padahal isinya separuh — persis keadaan yang paling sulit ditelusuri belakangan.
    """
    baik = _harga("AAAA")
    rusak = HargaHarian(kode="BBBB", tanggal=TANGGAL, high=900, low=1000, close=950)

    with pytest.raises(GalatIngesti):
        ingesti.simpan(sambungan, _kumpulan(baik, rusak), tanggal_data=TANGGAL)

    assert sambungan.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0] == 0
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 0
    assert sambungan.execute("SELECT COUNT(*) FROM log_jalan").fetchone()[0] == 0


def test_ambang_kegagalan_terlewati_menolak_snapshot() -> None:
    """PRD 9.3: lebih dari 5% emiten gagal -> snapshot tidak diterbitkan."""
    gagal = [Kegagalan(f"K{n:03d}", "tidak ada data") for n in range(3)]

    with pytest.raises(IngestiDibatalkan, match="snapshot tidak diterbitkan"):
        ingesti.periksa_ambang_gagal(gagal, 20, ambang_persen=5)


def test_kegagalan_di_bawah_ambang_tetap_lanjut() -> None:
    """Kegagalan sebagian yang wajar tidak menghentikan ingesti harian."""
    ingesti.periksa_ambang_gagal([Kegagalan("AAAA", "kosong")], 100, ambang_persen=5)


def test_emiten_kritis_yang_gagal_selalu_menolak_snapshot() -> None:
    """Satu emiten ber-ADTV20 tertinggi gagal sudah cukup (PRD 9.3)."""
    with pytest.raises(IngestiDibatalkan, match="ADTV20"):
        ingesti.periksa_ambang_gagal([Kegagalan("AAAA", "kosong")], 1000, emiten_kritis=["AAAA"])


# ---------------------------------------------------------------------------------------
# U18: gagal permanen dibedakan dari gagal sementara (diputuskan 9 Okt 2026)
# ---------------------------------------------------------------------------------------


def test_kegagalan_permanen_tidak_ikut_menghitung_ambang_lima_persen() -> None:
    """Kejadian nyata 9 Okt 2026: 57 dari 973 kode (5,9%) tidak diperdagangkan lagi.

    Kalau 57 kegagalan permanen itu dihitung seperti kegagalan biasa, snapshot **tidak akan
    pernah** bisa terbit — 916 emiten berhasil pun tidak menolong. Gerbang yang selalu menolak
    berhenti memberi informasi, dan itu kebalikan dari maksud PRD 9.3.
    """
    permanen = [Kegagalan(f"MATI{n:02d}", "sumber menyatakan tidak ada data") for n in range(57)]
    permanen = [replace(satu, jenis=KEGAGALAN_PERMANEN) for satu in permanen]

    # Tidak menolak: 5,9% itu semuanya permanen.
    ingesti.periksa_ambang_gagal(permanen, 973, ambang_persen=5)

    # Pembanding yang menentukan: jumlah yang **sama** sebagai kegagalan sementara tetap menolak.
    sementara = [replace(satu, jenis=KEGAGALAN_SEMENTARA) for satu in permanen]
    with pytest.raises(IngestiDibatalkan, match="gagal diambil sementara"):
        ingesti.periksa_ambang_gagal(sementara, 973, ambang_persen=5)


def test_kegagalan_tanpa_jenis_dihitung_sebagai_sementara() -> None:
    """Bawaan harus menahan snapshot, bukan meloloskannya (aturan keras 7).

    Kegagalan yang jenisnya tidak dapat dipastikan tidak boleh diam-diam dianggap "kode mati":
    itu jalan pintas menuju snapshot yang bolong tanpa ada yang tahu.
    """
    gagal = [Kegagalan(f"K{n}", "sebab tidak dikenali") for n in range(10)]

    assert all(satu.jenis == KEGAGALAN_SEMENTARA for satu in gagal)
    with pytest.raises(IngestiDibatalkan):
        ingesti.periksa_ambang_gagal(gagal, 100, ambang_persen=5)


def test_emiten_kritis_yang_gagal_permanen_tetap_menolak_snapshot() -> None:
    """Kehilangan satu emiten teratas tetap harus terlihat, apa pun jenis kegagalannya.

    "Tidak diperdagangkan lagi" adalah alasan yang sah untuk tidak menghitung ambang persen,
    tetapi bukan alasan membiarkan snapshot terbit tanpa emiten yang paling likuid.
    """
    satu = Kegagalan("BBCA", "sumber menyatakan tidak ada data", KEGAGALAN_PERMANEN)

    with pytest.raises(IngestiDibatalkan, match="ADTV20"):
        ingesti.periksa_ambang_gagal([satu], 1000, emiten_kritis=("BBCA", "BBRI"))


def test_jenis_kegagalan_yang_tidak_dikenal_ditolak_saat_dibuat() -> None:
    """Jenis adalah kontrak, bukan teks bebas: salah ketik harus gagal, bukan lolos."""
    with pytest.raises(GalatIngesti, match="jenis kegagalan"):
        Kegagalan("AAAA", "kosong", "permanen_sekali")


def test_ringkas_kegagalan_memisahkan_dua_jenis() -> None:
    """Laporan menyebut keduanya terpisah, dan menyebut kodenya."""
    gagal = (
        Kegagalan("MATI1", "sumber menyatakan tidak ada data", KEGAGALAN_PERMANEN),
        Kegagalan("MATI2", "sumber menyatakan tidak ada data", KEGAGALAN_PERMANEN),
        Kegagalan("GALAU1", "YFRateLimitError: too many requests", KEGAGALAN_SEMENTARA),
    )

    baris = ingesti.ringkas_kegagalan(gagal)

    assert len(baris) == 2
    assert "2 emiten tidak diperdagangkan lagi" in baris[0] and "MATI1" in baris[0]
    assert "1 emiten gagal sementara" in baris[1] and "GALAU1" in baris[1]
    assert ingesti.ringkas_kegagalan(()) == (), "tidak ada kegagalan -> tidak ada kalimat"


def test_kegagalan_permanen_tidak_diulang() -> None:
    """Inti U18 di sisi pengambil: jawaban "kode ini tidak punya data" tidak diulang.

    Diuji tanpa jaringan: `time.sleep` dan penentuan jenisnya diganti, sehingga yang diperiksa
    benar-benar jumlah percobaan — bukan lamanya menunggu. Mengulanginya juga tidak akan pernah
    berhasil, dan setiap permintaan tambahan menambah risiko pembatasan laju (K7).
    """
    percobaan: list[int] = []
    ticker = _TickerPalsu(
        galat=_galat_yfinance("YFPricesMissingError")(
            "ATPK.JK", "(period=5y)", yahoo_reason="No data found, symbol may be delisted"
        ),
        hitung=percobaan,
    )

    kumpulan = _PengambilUji(ticker, percobaan=3).ambil((_emiten("ATPK"),))

    assert percobaan == [1], "kegagalan permanen tidak boleh diulang"
    assert kumpulan.gagal[0].jenis == KEGAGALAN_PERMANEN
    assert "No data found" in kumpulan.gagal[0].alasan


def test_kegagalan_sementara_diulang_sampai_batas_percobaan() -> None:
    """Pembatasan laju tetap diulang seperti semula; itulah satu-satunya obatnya."""
    percobaan: list[int] = []
    ticker = _TickerPalsu(galat=_galat_yfinance("YFRateLimitError")(), hitung=percobaan)

    kumpulan = _PengambilUji(ticker, percobaan=3).ambil((_emiten("BBBB"),))

    assert percobaan == [1, 2, 3]
    assert kumpulan.gagal[0].jenis == KEGAGALAN_SEMENTARA


def test_galat_tanpa_alasan_yahoo_tidak_dianggap_permanen() -> None:
    """Dugaan pustaka ("possibly delisted") bukan bukti: tanpa alasan Yahoo, jenisnya sementara.

    Ini pembeda yang paling mudah salah: yfinance menamai galatnya `YFPricesMissingError` dan
    menulis "possibly delisted" pada pesannya, tetapi keduanya bisa muncul untuk sebab lain
    (permintaan kosong, periode tidak sah). Yang dihitung permanen hanya alasan yang benar-benar
    dinyatakan sumbernya.
    """
    percobaan: list[int] = []
    ticker = _TickerPalsu(
        galat=_galat_yfinance("YFPricesMissingError")("CCCC.JK", "(period=5y)"), hitung=percobaan
    )

    kumpulan = _PengambilUji(ticker, percobaan=2).ambil((_emiten("CCCC"),))

    assert kumpulan.gagal[0].jenis == KEGAGALAN_SEMENTARA
    assert percobaan == [1, 2], "yang tidak pasti jenisnya harus dicoba lagi"


def test_sumber_yang_diam_tanpa_galat_bertipe_dihitung_sementara() -> None:
    """Nol baris tanpa sebab yang dinyatakan bukan bukti kode mati — dan tidak boleh lolos.

    Justru inilah gejala yang dulu menyamarkan 57 kode mati: galatnya ditelan pustaka, sehingga
    yang sampai ke aplikasi hanya "tidak ada bar". Kegagalan yang tidak dapat dipastikan
    jenisnya harus menahan snapshot, bukan meloloskannya.
    """
    percobaan: list[int] = []
    ticker = _TickerPalsu(galat=None, hitung=percobaan)

    kumpulan = _PengambilUji(ticker, percobaan=3).ambil((_emiten("DDDD"),))

    assert percobaan == [1], "sumber yang menjawab kosong tidak perlu diulang di sini"
    assert kumpulan.gagal[0].jenis == KEGAGALAN_SEMENTARA
    assert "tidak menyebut sebabnya" in kumpulan.gagal[0].alasan


class _TickerPalsu:
    """Ticker yfinance palsu: mengembalikan tabel kosong atau melempar galat yang diberikan."""

    def __init__(self, *, galat: BaseException | None, hitung: list[int]) -> None:
        self.galat = galat
        self.hitung = hitung

    def history(self, **_kwargs: object) -> object:
        self.hitung.append(len(self.hitung) + 1)
        if self.galat is not None:
            raise self.galat
        return []  # nol baris, tanpa galat — bentuk yang dulu menyamarkan kode mati


class _PengambilUji(pengambil.PengambilYFinance):
    """Pengambil tanpa jaringan: tanpa jeda, tanpa menunggu, dan tanpa menyentuh config yfinance."""

    def __init__(self, ticker: _TickerPalsu, **lain: object) -> None:
        super().__init__(jeda=0.0, **lain)  # type: ignore[arg-type]
        self._ticker_palsu = ticker

    def _ticker(self, kode: str) -> _TickerPalsu:
        return self._ticker_palsu

    def _galat_naik(self) -> object:
        return contextlib.nullcontext()

    def _jeda_ulang(self, nomor: int) -> float:
        return 0.0


def _galat_yfinance(nama: str) -> type:
    """Kelas galat yfinance yang **asli**, supaya uji memakai bentuk yang benar-benar ada."""
    import yfinance.exceptions as pengecualian

    return getattr(pengecualian, nama)


def _emiten(kode: str) -> Emiten:
    return Emiten(kode=kode, nama=f"Emiten {kode}", sumber="uji", dicatat_pada=TANGGAL)


# ---------------------------------------------------------------------------------------
# Laporan mutu (PRD 7.3, AC-1)
# ---------------------------------------------------------------------------------------


def test_emiten_tanpa_bar_hari_terakhir_keluar_dari_peringkat(
    sambungan: sqlite3.Connection,
) -> None:
    """PRD 7.3/AC-1: emiten "data bolong" tidak boleh ikut diperingkat."""
    ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA", TANGGAL), _harga("BBBB", TANGGAL_LALU)),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    assert "BBBB" in laporan.dikeluarkan
    assert "AAAA" not in laporan.dikeluarkan
    assert not laporan.datar


def test_lonjakan_tanpa_aksi_korporasi_ditandai(sambungan: sqlite3.Connection) -> None:
    """PRD 7.3: lonjakan > 3x tanpa aksi korporasi ditandai untuk ditinjau manusia."""
    ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA", TANGGAL_LALU, close=1000), _harga("AAAA", TANGGAL, close=5000)),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    assert "lonjakan_tanpa_aksi" in {satu.jenis for satu in laporan.temuan}
    assert "AAAA" in laporan.dikeluarkan


def test_catatan_aksi_mutu_memberi_konteks_tanpa_menghapus_temuan_lonjakan(
    sambungan: sqlite3.Connection, tmp_path: Path
) -> None:
    """K90: konteks khusus mutu terpisah dan hanya terlihat setelah diketahui."""
    berkas_catatan = tmp_path / "catatan-aksi-mutu.csv"
    berkas_catatan.write_text(
        "kode;tanggal_efektif;instrumen_aksi;ringkasan_bukti;sumber_url;sumber\n"
        'AAAA;2026-10-09;HMETD untuk OWK;"5 saham menerima 102 HMETD; Rp100 per OWK";'
        "https://example.com/pengumuman;contoh resmi\n",
        encoding="utf-8",
    )
    catatan = berkas.baca_folder(tmp_path).kumpulan.catatan_aksi_mutu
    assert len(catatan) == 1
    assert isinstance(catatan[0], CatatanAksiMutu)

    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL_LALU, close=1000),
            _harga("AAAA", TANGGAL, close=5000),
            catatan_aksi_mutu=catatan,
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    revisi = replace(catatan[0], ringkasan_bukti="koreksi: 5 saham menerima 102 HMETD")
    ingesti.simpan(
        sambungan,
        _kumpulan(catatan_aksi_mutu=(revisi,)),
        tanggal_data=TANGGAL,
        momen=datetime(2026, 10, 10, 8, 0, 0),
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL, momen=TANGGAL)
    menurut_jenis = {satu.jenis: satu for satu in laporan.temuan}
    assert menurut_jenis["lonjakan_tanpa_aksi"].tingkat == mutu.TAK_WAJAR
    assert menurut_jenis["konteks_aksi_mutu"].tingkat == mutu.CATATAN
    assert "https://example.com/pengumuman" in menurut_jenis["konteks_aksi_mutu"].keterangan
    assert "Rp100 per OWK" in menurut_jenis["konteks_aksi_mutu"].keterangan

    laporan_setelah_revisi = mutu.periksa(
        sambungan, tanggal_data=TANGGAL, momen=date(2026, 10, 10)
    )
    konteks_terkini = next(satu for satu in laporan_setelah_revisi.temuan if satu.jenis == "konteks_aksi_mutu")
    assert "koreksi: 5 saham menerima 102 HMETD" in konteks_terkini.keterangan

    laporan_sebelum_diketahui = mutu.periksa(sambungan, tanggal_data=TANGGAL, momen=TANGGAL_LALU)
    assert "konteks_aksi_mutu" not in {satu.jenis for satu in laporan_sebelum_diketahui.temuan}


def test_lonjakan_yang_dijelaskan_split_bukan_temuan_tak_wajar(
    sambungan: sqlite3.Connection,
) -> None:
    """Split memang mengubah skala harga; menandainya "data rusak" akan melatih kebiasaan
    mengabaikan peringatan."""
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL_LALU, close=5000),
            _harga("AAAA", TANGGAL, close=1000),
            aksi_korporasi=(
                AksiKorporasi(kode="AAAA", tanggal=TANGGAL, jenis="split", rasio_lama=1, rasio_baru=5),
            ),
        ),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    jenis = {satu.jenis for satu in laporan.temuan}
    assert "lonjakan_dijelaskan_aksi" in jenis
    assert "lonjakan_tanpa_aksi" not in jenis
    assert "AAAA" not in laporan.dikeluarkan


def test_lonjakan_pada_baris_yang_mengaku_sudah_disesuaikan_ditandai_tak_wajar(
    sambungan: sqlite3.Connection,
) -> None:
    """K8/C10: bila sumbernya sudah menyesuaikan split, harga semestinya sambung di tanggal itu.

    Lonjakan di situ berarti basis penyesuaiannya bercampur (mis. sebagian baris dari sumber lain),
    sehingga aksi korporasi tidak boleh lagi dipakai memaafkannya — kalau dimaafkan, laporan mutu
    justru menyembunyikan persis kesalahan yang paling merusak angka momentum.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL_LALU, close=5000, penyesuaian_sumber=PENYESUAIAN_SPLIT),
            _harga("AAAA", TANGGAL, close=1000, penyesuaian_sumber=PENYESUAIAN_SPLIT),
            aksi_korporasi=(
                AksiKorporasi(kode="AAAA", tanggal=TANGGAL, jenis="split", rasio_lama=1, rasio_baru=5),
            ),
        ),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    jenis = {satu.jenis for satu in laporan.temuan}
    assert "lonjakan_pada_baris_tersesuaikan" in jenis
    assert "lonjakan_dijelaskan_aksi" not in jenis
    assert "AAAA" in laporan.dikeluarkan


def test_baris_tanpa_penanda_padahal_ada_split_dilaporkan_di_laporan_mutu(
    sambungan: sqlite3.Connection,
) -> None:
    """K8 menjanjikan baris tanpa penanda **ditandai di laporan mutu**, bukan ditebak.

    Satu temuan per emiten, bukan per baris: 1.200 baris tanpa penanda adalah satu keadaan.
    Yang penting, akibatnya disebut apa adanya — metrik harga emiten itu berhenti dihitung.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL_LALU, close=5000),
            _harga("AAAA", TANGGAL, close=1000),
            aksi_korporasi=(
                AksiKorporasi(kode="AAAA", tanggal=TANGGAL, jenis="split", rasio_lama=1, rasio_baru=5),
            ),
        ),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    temuan = [satu for satu in laporan.temuan if satu.jenis == "penyesuaian_sumber_belum_dinyatakan"]
    assert len(temuan) == 1, "satu temuan per emiten, bukan per baris"
    assert "penyesuaian_sumber" in temuan[0].keterangan
    assert "tidak bisa diperingkat" in temuan[0].keterangan


def test_baris_berpenanda_tidak_dilaporkan_sebagai_penanda_hilang(
    sambungan: sqlite3.Connection,
) -> None:
    """Kebalikannya juga dijaga: yang sudah menyatakan penandanya tidak boleh ikut dituduh.

    Tanpa uji ini, pemeriksaan baru bisa berubah menjadi kebisingan yang selalu menyala — dan
    peringatan yang selalu menyala akan berhenti dibaca orang.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL_LALU, close=5000, penyesuaian_sumber=PENYESUAIAN_SPLIT),
            _harga("AAAA", TANGGAL, close=1000, penyesuaian_sumber=PENYESUAIAN_SPLIT),
            aksi_korporasi=(
                AksiKorporasi(kode="AAAA", tanggal=TANGGAL, jenis="split", rasio_lama=1, rasio_baru=5),
            ),
        ),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    assert "penyesuaian_sumber_belum_dinyatakan" not in {satu.jenis for satu in laporan.temuan}


def test_harga_nol_ditandai_tak_wajar(sambungan: sqlite3.Connection) -> None:
    """PRD 7.3 menyebut harga 0 sebagai nilai tidak wajar."""
    ingesti.simpan(
        sambungan,
        _kumpulan(HargaHarian(kode="AAAA", tanggal=TANGGAL, close=0, volume=1000)),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    assert "harga_nol" in {satu.jenis for satu in laporan.temuan}


def test_snapshot_basi_dilaporkan_saat_kalender_lebih_baru(sambungan: sqlite3.Connection) -> None:
    """AC-8: snapshot yang bukan dari hari bursa terakhir harus terlihat.

    Bentuk nyatanya: kalender sudah tahu `TANGGAL` adalah hari bursa, tetapi data harga baru
    sampai `TANGGAL_LALU`. Justru **itu** yang disebut snapshot basi — ada hari bursa yang
    sudah lewat dan belum punya data.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL_LALU),
            kalender_bursa=(
                HariBursa(tanggal=TANGGAL_LALU, hari_bursa=True),
                HariBursa(tanggal=TANGGAL, hari_bursa=True),
            ),
        ),
        tanggal_data=TANGGAL_LALU,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL_LALU)

    assert laporan.hari_bursa_terakhir == TANGGAL.isoformat()
    assert "snapshot_basi" in {satu.jenis for satu in laporan.temuan}


def test_hari_bursa_yang_belum_terjadi_tidak_menyebut_snapshot_basi(
    sambungan: sqlite3.Connection,
) -> None:
    """Kalender setahun penuh memuat hari bursa di depan; hari itu belum terjadi.

    Sejak `--ambil-kalender` mengisi kalender dari pengumuman tahunan KSEI, kalender lazim
    memuat hari bursa sampai akhir tahun. Tanpa pembatasan pada hari yang sudah lewat, snapshot
    yang benar akan disebut basi setiap hari sampai Desember — peringatan mencolok yang salah,
    dan peringatan yang sering salah berhenti dibaca orang.
    """
    jauh_di_depan = TANGGAL + timedelta(days=30)
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL),
            kalender_bursa=(
                HariBursa(tanggal=TANGGAL, hari_bursa=True),
                HariBursa(tanggal=jauh_di_depan, hari_bursa=True),
            ),
        ),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL, momen=TANGGAL)

    jenis = {satu.jenis for satu in laporan.temuan}
    assert "snapshot_basi" not in jenis
    assert "kalender_belum_memuat" not in jenis
    assert laporan.hari_bursa_terakhir == TANGGAL.isoformat()


def test_sumber_baris_kalender_ikut_tersimpan(sambungan: sqlite3.Connection) -> None:
    """Asal setiap tanggal kalender harus bisa ditelusuri, bukan hanya "impor berkas"."""
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL),
            kalender_bursa=(
                HariBursa(
                    tanggal=TANGGAL,
                    hari_bursa=False,
                    keterangan="Tahun Baru",
                    sumber="PENG-0004/DIR/KSEI/0926 (menindaklanjuti IDX Peng-00169/BEI.POP/09-2026)",
                ),
                HariBursa(tanggal=TANGGAL_LALU, hari_bursa=True),
            ),
        ),
        tanggal_data=TANGGAL,
    )

    sumber = dict(
        sambungan.execute("SELECT tanggal, sumber FROM kalender_bursa ORDER BY tanggal")
    )
    assert sumber[TANGGAL.isoformat()].startswith("PENG-0004/DIR/KSEI/0926")
    # Baris tanpa sumber sendiri tetap memakai label kumpulannya, seperti sebelum kolom ini ada.
    assert sumber[TANGGAL_LALU.isoformat()] == SUMBER_YFINANCE


def test_sumber_baris_rasio_bank_dipakai_dan_kosong_jatuh_ke_label_kumpulan(
    sambungan: sqlite3.Connection,
) -> None:
    """Baris yang menyatakan asalnya sendiri tidak boleh ditimpa label kumpulan (K78).

    `RasioBank` boleh dibentuk tanpa `sumber` (mis. oleh pengambil baru atau uji lain); dalam
    keadaan itu label kumpulan tetap dipakai seperti sebelum kolom ini ada. Yang **tidak** boleh
    adalah membuang sumber yang sudah dinyatakan barisnya — persis cacat yang terukur saat pilot
    #21b: dua bank dalam satu berkas sama-sama tercatat `impor berkas: <folder>`.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL),
            rasio_bank=(
                RasioBank(
                    kode="AAAA",
                    periode=TANGGAL_LALU,
                    tgl_publikasi=TANGGAL,
                    npl_kotor_bp=186,
                    sumber="Laporan Keuangan Publikasi 30 Jun 2026",
                ),
                RasioBank(
                    kode="BBBB",
                    periode=TANGGAL_LALU,
                    tgl_publikasi=TANGGAL,
                    npl_kotor_bp=250,
                ),
            ),
        ),
        tanggal_data=TANGGAL,
    )

    sumber = dict(sambungan.execute("SELECT kode, sumber FROM rasio_bank ORDER BY kode"))
    assert sumber["AAAA"] == "Laporan Keuangan Publikasi 30 Jun 2026"
    assert sumber["BBBB"] == SUMBER_YFINANCE, "baris tanpa sumber sendiri memakai label kumpulan"


def test_kalender_yang_ketinggalan_bukan_snapshot_basi(sambungan: sqlite3.Connection) -> None:
    """Arah perbandingan yang terbalik akan memunculkan peringatan salah setiap hari.
    kalendernya — bukan snapshotnya. Menuduh snapshot basi di keadaan ini berarti menampilkan
    peringatan mencolok (AC-8) yang tidak berdasar, dan peringatan yang sering salah akan
    berhenti dibaca orang.
    """
    ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", TANGGAL),
            kalender_bursa=(HariBursa(tanggal=TANGGAL_LALU, hari_bursa=True),),
        ),
        tanggal_data=TANGGAL,
    )

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    jenis = {satu.jenis for satu in laporan.temuan}
    assert "snapshot_basi" not in jenis
    assert "kalender_belum_memuat" in jenis


def test_pemeriksaan_yang_belum_bisa_dijalankan_dilaporkan_bukan_dianggap_lulus(
    sambungan: sqlite3.Connection,
) -> None:
    """Pemeriksaan 50 emiten ber-ADTV20 tertinggi belum bisa dijalankan di Tahap 0.

    Ia harus **dikatakan** belum bisa diperiksa. Diam-diam menganggapnya lulus berarti
    mengklaim pemeriksaan yang tidak pernah terjadi.
    """
    ingesti.simpan(sambungan, _kumpulan(_harga("AAAA")), tanggal_data=TANGGAL)

    laporan = mutu.periksa(sambungan, tanggal_data=TANGGAL)

    assert laporan.pemeriksaan_belum_dapat_dijalankan
    assert any("ADTV20" in satu for satu in laporan.pemeriksaan_belum_dapat_dijalankan)


# ---------------------------------------------------------------------------------------
# Pembaca berkas impor (jalur cadangan, P2/PRD 9.3)
# ---------------------------------------------------------------------------------------


def _tulis(folder: Path, nama: str, isi: str) -> Path:
    jalur = folder / nama
    jalur.write_text(isi, encoding="utf-8")
    return jalur


def test_berkas_tidak_ada_dilewati_dengan_catatan(folder_impor: Path) -> None:
    """Impor bertahap harus mungkin: kalender bursa belum tentu ada sejak hari pertama."""
    _tulis(folder_impor, "kalender-bursa.csv", "tanggal;hari_bursa;keterangan\n2026-10-09;1;\n")

    hasil = berkas.baca_folder(folder_impor)

    assert hasil.dibaca == ("kalender-bursa.csv (1 baris)",)
    assert "harga-harian.csv" in hasil.tidak_ada
    assert len(hasil.kumpulan.kalender_bursa) == 1


def test_folder_tanpa_berkas_dikenal_ditolak(folder_impor: Path) -> None:
    with pytest.raises(GalatIngesti, match="tidak memuat satu pun berkas"):
        berkas.baca_folder(folder_impor)


def test_kolom_salah_ketik_ditolak(folder_impor: Path) -> None:
    """Berkas salah baca lebih berbahaya daripada berkas yang menolak dimuat."""
    _tulis(folder_impor, "kalender-bursa.csv", "tanggal;hari_bursaa;keterangan\n2026-10-09;1;\n")

    with pytest.raises(GalatIngesti, match="kolom tidak dikenal"):
        berkas.baca_folder(folder_impor)


def test_kolom_wajib_hilang_ditolak(folder_impor: Path) -> None:
    _tulis(folder_impor, "kalender-bursa.csv", "tanggal;keterangan\n2026-10-09;\n")

    with pytest.raises(GalatIngesti, match="kolom wajib tidak ada"):
        berkas.baca_folder(folder_impor)


def test_seluruh_baris_salah_dilaporkan_sekaligus(folder_impor: Path) -> None:
    """Memperbaiki berkas 800 baris satu galat per jalan bukan pengalaman yang bisa dipakai."""
    isi = "tanggal;hari_bursa;keterangan\n" + "".join(
        f"2026-10-0{n};mungkin;\n" for n in range(1, 4)
    )
    _tulis(folder_impor, "kalender-bursa.csv", isi)

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    pesan = str(galat.value)
    assert "3 baris" in pesan
    assert pesan.count("hari_bursa") == 3


def test_baris_komentar_dan_contoh_diabaikan(folder_impor: Path) -> None:
    """Template bawaan harus bisa dibaca apa adanya tanpa diedit lebih dulu."""
    _tulis(
        folder_impor,
        "kalender-bursa.csv",
        "tanggal;hari_bursa;keterangan\n"
        "# ini penjelasan\n"
        "<<CONTOH>>;2026-01-02;1;contoh\n"
        "2026-10-09;1;\n",
    )

    hasil = berkas.baca_folder(folder_impor)

    assert len(hasil.kumpulan.kalender_bursa) == 1
    assert hasil.kumpulan.kalender_bursa[0].tanggal == TANGGAL


def test_pemisah_titik_koma_dan_bom_terbaca(folder_impor: Path) -> None:
    """Excel Indonesia menyimpan CSV UTF-8 ber-BOM dengan pemisah titik koma (U11)."""
    _tulis(folder_impor, "imbal-hasil-sun.csv", "tanggal;tenor_tahun;imbal_hasil_persen;sumber\n2026-10-01;10;6.75;Bank Indonesia\n")

    hasil = berkas.baca_folder(folder_impor)

    assert hasil.kumpulan.imbal_hasil_sun[0].imbal_hasil_bp == 675


@pytest.mark.parametrize(
    ("kolom", "nilai", "potongan"),
    [
        ("hari_bursa", "mungkin", "tidak dikenal"),
        ("tanggal", "10/09/2026", "tidak dikenali"),
    ],
)
def test_nilai_salah_ditolak_dengan_nomor_baris(
    folder_impor: Path, kolom: str, nilai: str, potongan: str
) -> None:
    baris = {"tanggal": "2026-10-09", "hari_bursa": "1"}
    baris[kolom] = nilai
    _tulis(
        folder_impor,
        "kalender-bursa.csv",
        f"tanggal;hari_bursa;keterangan\n{baris['tanggal']};{baris['hari_bursa']};\n",
    )

    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_folder(folder_impor)

    assert potongan in str(galat.value)
    assert "baris 2" in str(galat.value), "pesan harus menunjuk barisnya"


def test_emiten_tanpa_berkas_rujukan_ditolak_dengan_petunjuk(folder_impor: Path) -> None:
    """Semesta saham adalah keputusan pengguna; aplikasi tidak mengarangnya."""
    with pytest.raises(GalatIngesti) as galat:
        berkas.baca_emiten(folder_impor)

    assert "emiten.csv" in str(galat.value)
    assert "kode;nama" in str(galat.value), "pesannya harus menyebut header yang diharapkan"


def test_jenis_emiten_tidak_dikenal_ditolak(folder_impor: Path) -> None:
    _tulis(
        folder_impor,
        "emiten.csv",
        "kode;nama;sektor_idx_ic;jenis;papan;status_notasi;jumlah_saham;free_float_persen;"
        "sumber;dicatat_pada\nAAAA;Alpha;;bank_mega;;;;;uji;2026-10-01\n",
    )

    with pytest.raises(GalatIngesti, match="jenis"):
        berkas.baca_emiten(folder_impor)


def test_jenis_emiten_kosong_menjadi_none_bukan_umum(folder_impor: Path) -> None:
    """"Belum diklasifikasi" berbeda dari "umum" — set metriknya berbeda (PRD 8.4)."""
    _tulis(
        folder_impor,
        "emiten.csv",
        "kode;nama;sektor_idx_ic;jenis;papan;status_notasi;jumlah_saham;free_float_persen;"
        "sumber;dicatat_pada\nAAAA;Alpha;;;;;;;uji;2026-10-01\n",
    )

    daftar = berkas.baca_emiten(folder_impor)

    assert daftar[0].jenis is None


# ---------------------------------------------------------------------------------------
# Arsip snapshot (PRD 7.2: dimulai sejak hari pertama, tidak bisa direkonstruksi)
# ---------------------------------------------------------------------------------------


def test_arsip_menyebut_snapshot_dan_bukan_nasihat_investasi(sambungan: sqlite3.Connection) -> None:
    """AC-7 + aturan keras 8: arsip yang ditemukan setahun lagi harus menjelaskan asalnya."""
    tersimpan = ingesti.simpan(sambungan, _kumpulan(_harga("AAAA")), tanggal_data=TANGGAL)

    hasil = arsip.tulis(sambungan, id_snapshot=tersimpan.id_snapshot)

    isi = (hasil.folder / "harga.csv").read_text(encoding="utf-8-sig")
    assert f"# id_snapshot;{tersimpan.id_snapshot}" in isi
    assert f"# tanggal_data;{TANGGAL.isoformat()}" in isi
    assert "bukan nasihat investasi" in isi
    assert "kode;tanggal;open" in isi


def test_arsip_snapshot_lama_tidak_ditimpa_snapshot_baru(sambungan: sqlite3.Connection) -> None:
    """Setiap snapshot punya foldernya sendiri; memperbaiki data menambah arsip (S1)."""
    pertama = ingesti.simpan(
        sambungan, _kumpulan(_harga("AAAA", close=1000)), tanggal_data=TANGGAL, momen=MOMEN
    )
    kedua = ingesti.simpan(
        sambungan, _kumpulan(_harga("AAAA", close=1010)), tanggal_data=TANGGAL, momen=MOMEN_LANJUT
    )

    folder_pertama = arsip.tulis(sambungan, id_snapshot=pertama.id_snapshot).folder
    folder_kedua = arsip.tulis(sambungan, id_snapshot=kedua.id_snapshot).folder

    assert folder_pertama != folder_kedua
    assert "1000" in (folder_pertama / "harga.csv").read_text(encoding="utf-8-sig")
    assert "1010" in (folder_kedua / "harga.csv").read_text(encoding="utf-8-sig")


def test_arsip_bisa_dibaca_ulang_dan_dibandingkan(sambungan: sqlite3.Connection) -> None:
    """Arsip yang tidak bisa dibaca ulang bukan arsip — hanya berkas."""
    tersimpan = ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA"), _harga("AAAA", TANGGAL_LALU)),
        tanggal_data=TANGGAL,
    )
    hasil = arsip.tulis(sambungan, id_snapshot=tersimpan.id_snapshot)

    perbandingan = {satu.nama: satu for satu in arsip.bandingkan(sambungan, hasil.folder)}

    assert perbandingan["harga.csv"].baris_arsip == 2
    assert perbandingan["harga.csv"].cocok


def test_arsip_data_tidak_resmi_membawa_peringatan_penyebaran(
    sambungan: sqlite3.Connection,
) -> None:
    """Berkas ekspor adalah jalur penyebaran data, jadi peringatannya harus ada di dalam berkas.

    Pemeriksaan ketentuan pemakaian (Q8) menemukan Syarat Layanan Yahoo melarang pengambilan
    data otomatis untuk tujuan apa pun tanpa izin tertulis sebelumnya. Kewajiban praktisnya:
    setiap berkas yang bisa keluar dari komputer ini menyatakan asalnya dan larangan
    menyebarkannya — bukan hanya aplikasinya yang tahu.
    """
    tersimpan = ingesti.simpan(sambungan, _kumpulan(_harga("AAAA")), tanggal_data=TANGGAL)

    hasil = arsip.tulis(sambungan, id_snapshot=tersimpan.id_snapshot)

    isi = (hasil.folder / "harga.csv").read_text(encoding="utf-8-sig")
    assert "tidak resmi" in isi
    assert "tidak berafiliasi" in isi
    assert "JANGAN disebarkan" in isi
    assert "legal.yahoo.com" in isi


def test_arsip_data_bersumber_sendiri_tidak_dilabeli_tidak_resmi(
    sambungan: sqlite3.Connection,
) -> None:
    """Label "tidak resmi" harus jujur: sumber milik pengguna sendiri bukan sumber tidak resmi."""
    tersimpan = ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA"), sumber="impor berkas: D:\\data-saya"),
        tanggal_data=TANGGAL,
    )

    hasil = arsip.tulis(sambungan, id_snapshot=tersimpan.id_snapshot)

    isi = (hasil.folder / "harga.csv").read_text(encoding="utf-8-sig")
    assert "JANGAN disebarkan" not in isi
    assert "bukan nasihat investasi" in isi, "pernyataan bukan nasihat tetap wajib"


def test_arsip_snapshot_yang_tidak_ada_ditolak(sambungan: sqlite3.Connection) -> None:
    with pytest.raises(GalatIngesti, match="tidak ada di basis data"):
        arsip.tulis(sambungan, id_snapshot=999)


def test_arsip_tidak_meninggalkan_berkas_sementara(sambungan: sqlite3.Connection) -> None:
    """Tulis atomik: berkas sementara tidak boleh tertinggal setelah berhasil."""
    tersimpan = ingesti.simpan(sambungan, _kumpulan(_harga("AAAA")), tanggal_data=TANGGAL)

    hasil = arsip.tulis(sambungan, id_snapshot=tersimpan.id_snapshot)

    assert not list(hasil.folder.glob("*.sementara"))


# ---------------------------------------------------------------------------------------
# Orkestrasi: satu jalan penuh tanpa jaringan
# ---------------------------------------------------------------------------------------


def test_refresh_menulis_snapshot_mutu_dan_arsip(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """Satu jalan penuh dengan pengambil palsu: ambil -> mutu -> tulis -> arsip."""
    _tulis_emiten(folder_impor, "AAAA")
    pengambil = PengambilPalsu(_kumpulan(_harga("AAAA"), _harga("AAAA", TANGGAL_LALU)))

    hasil = pengatur.jalankan_refresh(sambungan, pengambil, folder_impor=folder_impor)

    assert hasil.sukses, hasil.pesan
    assert pengambil.diminta == ("AAAA",), "daftar emiten harus dibaca dari berkas rujukan"
    assert hasil.id_snapshot is not None
    assert hasil.laporan_mutu is not None
    assert hasil.arsip is not None and hasil.arsip.folder.is_dir()
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 1


def test_refresh_tanpa_emiten_csv_gagal_berisik_dan_tidak_menulis_apa_pun(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    pengambil = PengambilPalsu(_kumpulan(_harga("AAAA")))

    hasil = pengatur.jalankan_refresh(sambungan, pengambil, folder_impor=folder_impor)

    assert not hasil.sukses
    assert "emiten.csv" in hasil.pesan
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 0
    log = sambungan.execute("SELECT hasil, pesan FROM log_jalan").fetchall()
    assert len(log) == 1 and log[0]["hasil"] == "gagal", "kegagalan wajib tercatat (AC-9)"


def test_refresh_saat_ambang_gagal_terlewati_tidak_menerbitkan_snapshot(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """Snapshot lama tetap dipakai, dan itu dikatakan (PRD 9.3, AC-8)."""
    _tulis_emiten(folder_impor, "AAAA", "BBBB", "CCCC", "DDDD")
    kumpulan = _kumpulan(
        _harga("AAAA"),
        gagal=tuple(
            Kegagalan(kode, "YFRateLimitError: too many requests", KEGAGALAN_SEMENTARA)
            for kode in ("BBBB", "CCCC", "DDDD")
        ),
    )

    hasil = pengatur.jalankan_refresh(
        sambungan, PengambilPalsu(kumpulan), folder_impor=folder_impor, ambang_gagal_persen=5
    )

    assert not hasil.sukses and hasil.dibatalkan
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 0
    assert sambungan.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0] == 0


def test_refresh_menerbitkan_snapshot_saat_yang_gagal_semuanya_permanen(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """U18 pada jalur nyata: 3 dari 4 kode (75%, jauh di atas 5%) tidak diperdagangkan lagi.

    Snapshot **terbit**, dan lubangnya tetap terlihat: jumlahnya disebut di pesan, kodenya di
    peringatan, dan jenisnya di laporan mutu. Yang tidak boleh terjadi adalah snapshot yang
    terbit tanpa satu pun jejak tentang tiga kode yang hilang itu.
    """
    _tulis_emiten(folder_impor, "AAAA", "MATI1", "MATI2", "MATI3")
    kumpulan = _kumpulan(
        _harga("AAAA"),
        gagal=tuple(
            Kegagalan(kode, "sumber menyatakan tidak ada data: No data found", KEGAGALAN_PERMANEN)
            for kode in ("MATI1", "MATI2", "MATI3")
        ),
    )

    hasil = pengatur.jalankan_refresh(
        sambungan, PengambilPalsu(kumpulan), folder_impor=folder_impor, ambang_gagal_persen=5
    )

    assert hasil.sukses and not hasil.dibatalkan
    assert "3 permanen, 0 sementara" in hasil.pesan
    assert "3 emiten tidak diperdagangkan lagi" in " ".join(hasil.peringatan)
    assert hasil.laporan_mutu is not None
    jenis = {satu.jenis: satu for satu in hasil.laporan_mutu.temuan if satu.kode in {"MATI1", "MATI2", "MATI3"}}
    assert set(jenis) == {"tidak_diperdagangkan"}, "jenis temuan wajib berbeda dari gagal sementara"
    assert "[permanen]" in jenis["tidak_diperdagangkan"].keterangan


def test_refresh_membuat_template_berkas_impor_saat_belum_ada(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """AC-12: folder data yang kosong harus kembali ke bentuk bawaan."""
    _tulis_emiten(folder_impor, "AAAA")

    pengatur.jalankan_refresh(
        sambungan, PengambilPalsu(_kumpulan(_harga("AAAA"))), folder_impor=folder_impor
    )

    for nama in ("kalender-bursa.csv", "notasi-khusus.csv", "imbal-hasil-sun.csv"):
        assert (folder_impor / nama).is_file(), f"template {nama} tidak disalin"


def test_berkas_impor_yang_sudah_ada_tidak_ditimpa(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """Berkas pengguna berisi pekerjaannya; template tidak boleh menimpanya."""
    _tulis_emiten(folder_impor, "AAAA")
    isi_saya = "tanggal;hari_bursa;keterangan\n2026-10-09;1;hari saya\n"
    _tulis(folder_impor, "kalender-bursa.csv", isi_saya)

    pengatur.jalankan_refresh(
        sambungan, PengambilPalsu(_kumpulan(_harga("AAAA"))), folder_impor=folder_impor
    )

    assert (folder_impor / "kalender-bursa.csv").read_text(encoding="utf-8") == isi_saya


def test_refresh_menggabungkan_berkas_impor_tanpa_menulis_emiten_dua_kali(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """Kalender bursa dari berkas harus ikut, dan emiten hanya ditulis sekali."""
    _tulis_emiten(folder_impor, "AAAA")
    _tulis(folder_impor, "kalender-bursa.csv", "tanggal;hari_bursa;keterangan\n2026-10-09;1;\n")
    _tulis(folder_impor, "notasi-khusus.csv", "kode;jenis;tanggal_mulai;tanggal_selesai;keterangan\nAAAA;uma;2026-10-01;;\n")

    hasil = pengatur.jalankan_refresh(
        sambungan, PengambilPalsu(_kumpulan(_harga("AAAA"))), folder_impor=folder_impor
    )

    assert hasil.sukses, hasil.pesan
    assert sambungan.execute("SELECT COUNT(*) FROM kalender_bursa").fetchone()[0] == 1
    assert sambungan.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0] == 1
    assert sambungan.execute("SELECT COUNT(*) FROM emiten").fetchone()[0] == 1


def test_refresh_menyimpan_baris_berkas_impor_dengan_label_folder_bukan_label_yfinance(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """Uji regresi (sesi 56): notasi IDX dan SUN dari folder konfigurasi dulu tersimpan berlabel
    `yfinance/Yahoo Finance` — provenance salah (aturan keras 3) — dan karena labelnya berubah,
    setiap refresh menulis ulang seluruh barisnya sebagai revisi baru (4.604 baris pada data kerja).
    """
    _tulis_emiten(folder_impor, "AAAA")
    _tulis(folder_impor, "notasi-khusus.csv", "kode;jenis;tanggal_mulai;tanggal_selesai;keterangan\nAAAA;uma;2026-10-01;;\n")
    _tulis(folder_impor, "imbal-hasil-sun.csv", "tanggal;tenor_tahun;imbal_hasil_persen;sumber\n2026-10-01;10;6.75;PHEI\n")

    # Urutan di data kerja: berkas diimpor sekali, lalu refresh harian membacanya ulang.
    # (`momen` lampau supaya refresh sesudahnya tidak jatuh pada detik yang sama — T12.)
    ingesti.simpan(
        sambungan,
        berkas.baca_folder(folder_impor.resolve()).kumpulan,
        tanggal_data=TANGGAL_LALU,
        momen=MOMEN,
        proses=ingesti.PROSES_IMPOR,
    )
    pengambil = PengambilPalsu(_kumpulan(_harga("AAAA"), _harga("AAAA", TANGGAL_LALU)))
    hasil = pengatur.jalankan_refresh(sambungan, pengambil, folder_impor=folder_impor)
    assert hasil.sukses, hasil.pesan

    label = f"{ingesti.PREFIKS_SUMBER_IMPOR}: {folder_impor.resolve()}"
    for tabel in ("notasi_khusus", "imbal_hasil_sun"):
        baris = sambungan.execute(f"SELECT sumber FROM {tabel}").fetchall()
        assert [satu[0] for satu in baris] == [label], f"{tabel}: label atau jumlah revisi salah"
    # Harga dari pengambil otomatis tetap berlabel sumbernya.
    assert {satu[0] for satu in sambungan.execute("SELECT DISTINCT sumber FROM harga_harian")} == {SUMBER_YFINANCE}


def test_revisi_berpenutupan_kosong_tidak_menutupi_nilai_yang_sudah_diketahui(
    sambungan: sqlite3.Connection,
) -> None:
    """Uji regresi (29 Okt 2026): Yahoo mengirim bar IHSG/LQ45 hari itu dengan `close` kosong
    sesudah nilainya sudah tersimpan; revisi itu menjadi "terkini" dan dasbor mundur ke hari
    sebelumnya. Revisi yang hanya mengosongkan nilai dari sumber yang **sama** ditolak dan
    dilaporkan; bar kosong untuk tanggal yang belum punya nilai tetap tersimpan apa adanya."""
    ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA"), harga_indeks=(PenutupanIndeks("IHSG", TANGGAL, close=5282),)),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    hasil = ingesti.simpan(
        sambungan,
        _kumpulan(
            _harga("AAAA", close=None, volume=None),
            _harga("BBBB", close=None, volume=None),
            harga_indeks=(PenutupanIndeks("IHSG", TANGGAL, close=None),),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN_LANJUT,
    )

    terkini = sambungan.execute(
        "SELECT close FROM v_harga_indeks_terkini WHERE indeks='IHSG' AND tanggal=?",
        (TANGGAL.isoformat(),),
    ).fetchone()[0]
    assert terkini == 5282
    assert sambungan.execute(
        "SELECT close FROM v_harga_harian_terkini WHERE kode='AAAA' AND tanggal=?", (TANGGAL.isoformat(),)
    ).fetchone()[0] == 1000
    assert hasil.baris.kosong_ditolak == {"harga_indeks": ["IHSG 2026-10-09"], "harga_harian": ["AAAA 2026-10-09"]}
    # BBBB belum pernah bernilai: lubangnya tersimpan apa adanya (aturan keras 2), bukan dibuang.
    assert sambungan.execute("SELECT COUNT(*) FROM harga_harian WHERE kode='BBBB'").fetchone()[0] == 1
    log = sambungan.execute("SELECT pesan FROM log_jalan ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert "2 revisi berpenutupan kosong ditolak" in log


def _tulis_lubang_ihsg_lama(sambungan: sqlite3.Connection) -> None:
    """Keadaan data kerja sebelum T90: nilai 5.282, lalu revisi kosong yang menjadi "terkini"."""
    ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA"), harga_indeks=(PenutupanIndeks("IHSG", TANGGAL, close=5282),)),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    # Revisi kosong ditulis langsung, seperti yang dilakukan kode sebelum T90 (29 Okt 02.24).
    sambungan.execute(
        "INSERT INTO harga_indeks (indeks, tanggal, close, close_mentah, sumber, diketahui_pada)"
        " VALUES ('IHSG', ?, NULL, NULL, ?, ?)",
        (TANGGAL.isoformat(), SUMBER_YFINANCE, ingesti._waktu_iso(MOMEN_LANJUT)),
    )


def test_nilai_yang_dikirim_ulang_menutup_revisi_kosong_lama(sambungan: sqlite3.Connection) -> None:
    """Uji regresi (sesi 69): T90 menjanjikan lubang lama "tertutup sendiri begitu sumber mengirim
    nilai penuh", tetapi nilai 5.282 yang dikirim ulang dicatat "sudah ada" karena sama dengan
    revisi **lama** — lubangnya tetap terkini dan dasbor membandingkan IHSG dengan hari sebelumnya."""
    _tulis_lubang_ihsg_lama(sambungan)

    hasil = ingesti.simpan(
        sambungan,
        _kumpulan(_harga("AAAA"), harga_indeks=(PenutupanIndeks("IHSG", TANGGAL, close=5282),)),
        tanggal_data=TANGGAL,
        momen=datetime(2026, 10, 9, 18, 0, 2),
    )

    terkini = sambungan.execute(
        "SELECT close FROM v_harga_indeks_terkini WHERE indeks='IHSG' AND tanggal=?",
        (TANGGAL.isoformat(),),
    ).fetchone()[0]
    assert terkini == 5282
    assert hasil.baris.baru.get("harga_indeks") == 1
    # Harga AAAA sama dengan revisi terkininya: tidak menumpuk salinan.
    assert "harga_harian" not in hasil.baris.baru


def test_koreksi_balik_ke_nilai_lama_tersimpan_sebagai_revisi(sambungan: sqlite3.Connection) -> None:
    """A → B → A: koreksi yang kembali ke nilai lama adalah perbaikan data (S1), bukan salinan."""
    for detik, close in ((0, 1000), (1, 1100), (2, 1000)):
        ingesti.simpan(
            sambungan, _kumpulan(_harga("AAAA", close=close)), tanggal_data=TANGGAL,
            momen=datetime(2026, 10, 9, 18, 0, detik),
        )

    revisi = [
        satu[0]
        for satu in sambungan.execute(
            "SELECT close FROM harga_harian WHERE kode='AAAA' ORDER BY diketahui_pada"
        )
    ]
    assert revisi == [1000, 1100, 1000]
    assert sambungan.execute(
        "SELECT close FROM v_harga_harian_terkini WHERE kode='AAAA'"
    ).fetchone()[0] == 1000


def test_dua_sumber_bergantian_tidak_menumpuk_revisi(sambungan: sqlite3.Connection) -> None:
    """Pembanding "sudah ada" adalah revisi terkini **dari sumber yang sama**: dua sumber yang
    berbeda angkanya untuk kunci yang sama (yfinance dan Ringkasan Saham IDX) tidak saling
    memicu revisi baru setiap kali salah satunya ditulis ulang."""
    for detik in range(4):
        sumber, close = ((SUMBER_YFINANCE, 1000), ("sumber B", 1005))[detik % 2]
        ingesti.simpan(
            sambungan, _kumpulan(_harga("AAAA", close=close), sumber=sumber), tanggal_data=TANGGAL,
            momen=datetime(2026, 10, 9, 18, 0, detik),
        )

    assert sambungan.execute("SELECT COUNT(*) FROM harga_harian WHERE kode='AAAA'").fetchone()[0] == 2


def test_impor_tanpa_harga_tetap_bisa_disimpan(
    sambungan: sqlite3.Connection, folder_impor: Path
) -> None:
    """Kalender bursa sering jadi berkas pertama yang diisi, sebelum harga ada."""
    _tulis(
        folder_impor,
        "kalender-bursa.csv",
        "tanggal;hari_bursa;keterangan\n2026-10-09;1;\n",
    )

    hasil = pengatur.jalankan_impor(sambungan, folder_impor)

    assert hasil.sukses, hasil.pesan
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == 1


# ---------------------------------------------------------------------------------------
# Tidak ada emiten yang dikarang, dan tidak ada data pengguna yang tersentuh
# ---------------------------------------------------------------------------------------


def test_kumpulan_dari_sumber_berbeda_menolak_digabung() -> None:
    """Satu snapshot = satu label sumber (S2); penggabungan harus disengaja pemanggilnya."""
    a = _kumpulan(_harga("AAAA"), sumber="sumber A")
    b = _kumpulan(_harga("BBBB"), sumber="sumber B")

    with pytest.raises(GalatIngesti, match="sumber berbeda"):
        a.tambah(b)


def test_template_bawaan_tidak_memuat_kode_emiten() -> None:
    """Aturan keras 1: daftar emiten tidak boleh dikarang aplikasi.

    Template `emiten.contoh.csv` wajib tetap tanpa satu baris data pun. Daftar bootstrap
    (`emiten-awal.contoh.csv`) boleh ada isinya, tetapi setiap barisnya harus menyatakan
    sendiri bahwa ia belum diverifikasi.
    """
    bawaan = Path(__file__).resolve().parents[1] / "mejasaham" / "defaults"

    kosong = [
        baris
        for baris in (bawaan / "emiten.contoh.csv").read_text(encoding="utf-8-sig").splitlines()
        if baris.strip() and not baris.startswith("#") and "<<CONTOH>>" not in baris
    ]
    assert len(kosong) == 1, f"template emiten harus hanya berisi baris header, bukan: {kosong}"

    awal = [
        baris
        for baris in (bawaan / "emiten-awal.contoh.csv").read_text(encoding="utf-8-sig").splitlines()
        if baris.strip() and not baris.startswith("#")
    ]
    assert awal[0].startswith("kode;"), "baris pertama harus header"
    for baris in awal[1:]:
        kolom = baris.split(";")
        assert len(kolom) == len(awal[0].split(";")), f"jumlah kolom tidak cocok: {baris}"
        assert "belum diverifikasi" in baris, f"baris bootstrap harus menyatakan belum diverifikasi: {baris}"
        assert kolom[2] == "" and kolom[3] == "", "sektor/jenis tidak boleh dikarang"


def test_daftar_awal_menolak_menimpa_tanpa_izin(folder_impor: Path) -> None:
    """Mengganti daftar emiten pengguna harus disengaja, bukan efek samping."""
    _tulis_emiten(folder_impor, "AAAA")

    with pytest.raises(GalatIngesti, match="sudah ada"):
        berkas.ambil_daftar_awal(folder_impor)


# ---------------------------------------------------------------------------------------
# Uji regresi: tabrakan kunci utama yang isinya BERBEDA tidak boleh hilang diam-diam
# ---------------------------------------------------------------------------------------


def test_dua_revisi_berbeda_pada_kunci_sama_ditolak_berisik(sambungan: sqlite3.Connection) -> None:
    """Satu jalan ingesti memakai satu `diketahui_pada`, jadi revisi kedua tidak muat di dalamnya.

    Bug nyata (ditemukan uji metrik pada 9 Okt 2026): baris kedua dihitung "sudah ada dan sama"
    lalu **dibuang**, padahal isinya berbeda — dan laporannya menyatakan sukses. Untuk
    fundamental, bentuk ini persis restatement yang ditulis sebagai baris baru (cara yang
    didorong S1), sehingga angka yang dipakai berhitung adalah angka yang sudah digantikan,
    tanpa satu pun tanda. Aturan keras 7 menuntut sebaliknya: gagal itu berisik.
    """
    kumpulan = _kumpulan(
        _harga("AAAA", close=1000),
        _harga("AAAA", close=1111),  # kunci sama, isi berbeda, dalam satu jalan
    )

    with pytest.raises(GalatIngesti, match="dua baris berbeda untuk kunci yang sama"):
        ingesti.simpan(sambungan, kumpulan, tanggal_data=TANGGAL, momen=MOMEN)


def test_dua_jalan_pada_detik_yang_sama_ditolak_dengan_sebab_yang_benar(
    sambungan: sqlite3.Connection,
) -> None:
    """Dua **jalan** impor dalam detik yang sama bertabrakan, dan pesannya harus menyebut itu.

    Ditemukan 10 Okt 2026 saat mengukur pertanyaan terbuka C5, dan yang salah bukan perilakunya
    melainkan pesannya. `diketahui_pada` berketelitian **detik** (`db.waktu_iso` memotong
    mikrodetik), sedangkan kasus ini muncul justru ketika orang melakukan hal yang benar:
    mengimpor laporan, lalu mengimpor restatement-nya sebagai berkas terpisah. Kalau kedua jalan
    itu jatuh di detik yang sama, kunci waktunya bertabrakan.

    Pesan lamanya berbunyi "Perbaiki berkasnya (satu baris per kunci), atau impor revisinya lewat
    jalan tersendiri yang lebih baru" — yaitu menyuruh melakukan persis hal yang barusan gagal.
    Orang yang membacanya akan menyunting berkas yang sudah benar, lalu menemukan kegagalan yang
    sama. Karena itu uji ini memeriksa **sebabnya disebut**, bukan hanya bahwa galatnya berisik.
    """
    kumpulan_awal = _kumpulan(_harga("AAAA", close=1000))
    kumpulan_revisi = _kumpulan(_harga("AAAA", close=1010))

    ingesti.simpan(sambungan, kumpulan_awal, tanggal_data=TANGGAL, momen=MOMEN)

    detik_sama = MOMEN.replace(microsecond=400_000)
    with pytest.raises(GalatIngesti) as keluhan:
        ingesti.simpan(sambungan, kumpulan_revisi, tanggal_data=TANGGAL, momen=detik_sama)

    pesan = str(keluhan.value)
    assert "detik yang sama" in pesan, "pesannya harus menyebut sebab yang sebenarnya"
    assert "setelah jeda" in pesan, "pesannya harus menyebut jalan keluar yang benar"


def test_dua_baris_identik_dalam_satu_jalan_tidak_menambah_baris(
    sambungan: sqlite3.Connection,
) -> None:
    """Kebalikannya juga dijaga: isi yang sama tetap dihitung "sudah ada", bukan galat.

    Berkas impor yang memuat baris kembar identik adalah kelalaian yang tidak berbahaya; yang
    berbahaya adalah membuang baris yang **berbeda** tanpa suara. Keduanya harus dibedakan,
    dan uji ini yang menjaga batasnya tetap di tempat yang benar.
    """
    kumpulan = _kumpulan(_harga("AAAA", close=1000), _harga("AAAA", close=1000))

    hasil = ingesti.simpan(sambungan, kumpulan, tanggal_data=TANGGAL, momen=MOMEN)

    assert hasil.baris.baru.get("harga_harian") == 1
    assert hasil.baris.tetap.get("harga_harian") == 1
    jumlah = sambungan.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0]
    assert jumlah == 1
