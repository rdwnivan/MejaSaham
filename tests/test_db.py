"""Uji lapisan basis data (T1, T9, A2, A6) dan aturan append-only (S1, aturan keras 3).

Uji di sini sengaja menembak **mesin**, bukan fungsi pembungkus: kalau trigger atau CHECK
dicabut dari `skema.py`, uji ini gagal. Itulah satu-satunya cara aturan "perbaikan data
menambah baris baru" tetap benar setelah seseorang menyunting skema enam bulan lagi.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from mejasaham import db, ingesti
from mejasaham.skema import MIGRASI, VERSI_TERBARU

SUMBER_UJI = "uji"
DIKETAHUI_PAGI = "2026-10-06T08:00:00+07:00"
DIKETAHUI_SORE = "2026-10-06T18:00:00+07:00"
TANGGAL = "2026-10-06"

# Versi migrasi yang sudah pernah **dirilis** ke basis data pengguna. Sampai versi ini,
# teks SQL-nya tidak boleh berubah sama sekali (T9, PRD 9.13): basis data lama sudah
# menjalankannya, jadi menyuntingnya membuat skema di komputer pengguna berbeda dari skema
# di basis data baru — persis keadaan yang paling sulit ditelusuri belakangan.
VERSI_TERKUNCI = 15

# Sidik SHA-256 teks SQL tiap migrasi terkunci. Saat merilis migrasi baru: jalankan
# `python -c "import hashlib; from mejasaham.skema import MIGRASI; print(hashlib.sha256(MIGRASI[-1].sql.encode()).hexdigest())"`
# lalu tambahkan barisnya dan naikkan VERSI_TERKUNCI.
SIDIK_MIGRASI_TERKUNCI = {
    1: "8317790f90a0dd63fe7c3dbaa7963656a13b76280e6d32918f8de488ece6bd43",
    2: "e6a50d26f5c3f9357067b3bb58102bd75a131993805d064db3e80d325b0dfbc8",
    3: "398df8fa28837aa8a018cd0ebcd84ef2e4a4e2dded5e13a20cb33182ef755b0c",
    4: "bbb5671a564a8e1233004b710c1df7da4898d22f0a0c97a61f04715a26f97854",
    5: "6f994bbe7e2098e8a70e0315d6b8a815b8353494e84af216cb46d1ffaa5d1514",
    6: "c9164d6169c7db3e04d437aa80f77b05e1b656e3487189624793f73bbb8f7540",
    7: "857e1de413107f422d51dd7dc896d4eb73a8db863689d349705c13f805f1716d",
    8: "67dd077638cf5f474b3759da7e1d638ef09c211a65283959bbf2654a100f7745",
    9: "a93c0acd078b9c50690b6268ce0baa6d97a2d5a0b3544706f1d494a516f7010f",
    10: "1baab6270d03850a259f0148650bdb144990f3be73d18d667b85d089bf027afc",
    11: "fe58bab99a36ae4e89894a2ec20c2867e6af7e2cb86a5c34b741345515939b21",
    12: "740e2fd0754c02ee1879feb44c31693a32f07f4a6dfb288d3dfc5268784dae8a",
    13: "2e96e3e8e8939635b639ca3a7558b18a669fd6d5e7d2799a167c9f83a07462bb",
    14: "ad9ffe6b4715d80828649c11f3a2ee43c5482625241902f476d9c6880d0e3ff1",
    15: "adf3952d1859827b491ad510893f556043b43a4a0db53784eb2504b33afc8575",
}


@pytest.fixture()
def berkas_db(tmp_path: Path) -> Path:
    return tmp_path / "uji.db"


@pytest.fixture()
def basis_data(berkas_db: Path) -> Iterator[sqlite3.Connection]:
    sambungan = db.siapkan(berkas_db)
    try:
        yield sambungan
    finally:
        sambungan.close()


def _sisip_harga(
    sambungan: sqlite3.Connection,
    *,
    kode: str = "AAAA",
    tanggal: str = TANGGAL,
    close: int = 1000,
    diketahui_pada: str = DIKETAHUI_PAGI,
) -> None:
    sambungan.execute(
        "INSERT INTO harga_harian (kode, tanggal, close, volume, sumber, diketahui_pada)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (kode, tanggal, close, 100, SUMBER_UJI, diketahui_pada),
    )


def _sisip_cek(
    sambungan: sqlite3.Connection,
    *,
    dijalankan_pada: str = DIKETAHUI_SORE,
    cakupan: str = "lengkap",
) -> None:
    """Satu catatan cek sumber kedua (migrasi 006) — bukti kepatuhan mingguan PRD 7.3."""
    sambungan.execute(
        "INSERT INTO cek_sumber_kedua (dijalankan_pada, tanggal_data, jumlah_diperiksa,"
        " jumlah_ditandai, jumlah_tak_terhitung, jumlah_belum_dapat, cakupan)"
        " VALUES (?, ?, 20, 0, 0, 0, ?)",
        (dijalankan_pada, TANGGAL, cakupan),
    )


# --- versi skema (T9) -------------------------------------------------------------------


def test_versi_skema_sesuai_kode(basis_data: sqlite3.Connection) -> None:
    assert db.versi_terpasang(basis_data) == VERSI_TERBARU


def test_migrasi_berurutan_tanpa_lompatan() -> None:
    """Penjaga daftar migrasi: nomor harus 1..N, kalau tidak, versi terpasang menyesatkan."""
    assert [migrasi.versi for migrasi in MIGRASI] == list(range(1, len(MIGRASI) + 1))


def test_migrasi_yang_sudah_dirilis_tidak_disunting() -> None:
    """Sekali terpasang, teks migrasi membeku — perubahan skema berarti migrasi baru (T9)."""
    for migrasi in MIGRASI:
        if migrasi.versi > VERSI_TERKUNCI:
            continue
        terkunci = SIDIK_MIGRASI_TERKUNCI.get(migrasi.versi)
        assert terkunci is not None, (
            f"migrasi {migrasi.versi} ({migrasi.nama}) sudah dirilis tetapi belum dikunci di "
            "SIDIK_MIGRASI_TERKUNCI"
        )
        sidik = hashlib.sha256(migrasi.sql.encode("utf-8")).hexdigest()
        assert sidik == terkunci, (
            f"isi migrasi {migrasi.versi} ({migrasi.nama}) berubah padahal sudah terpasang di "
            "basis data pengguna. Tambahkan migrasi BARU untuk perubahan skema; jangan menyunting "
            "yang sudah dirilis (T9, PRD 9.13)."
        )


def test_setiap_migrasi_tercatat_di_tabel_jejak(basis_data: sqlite3.Connection) -> None:
    tercatat = basis_data.execute(
        "SELECT versi, nama FROM migrasi_terpasang ORDER BY versi"
    ).fetchall()

    assert [(baris["versi"], baris["nama"]) for baris in tercatat] == [
        (migrasi.versi, migrasi.nama) for migrasi in MIGRASI
    ]


def test_siapkan_ulang_tidak_mengubah_apa_pun(berkas_db: Path) -> None:
    pertama = db.siapkan(berkas_db)
    jumlah_jejak = pertama.execute("SELECT COUNT(*) FROM migrasi_terpasang").fetchone()[0]
    pertama.close()

    kedua = db.siapkan(berkas_db)
    try:
        assert db.versi_terpasang(kedua) == VERSI_TERBARU
        assert kedua.execute("SELECT COUNT(*) FROM migrasi_terpasang").fetchone()[0] == jumlah_jejak
    finally:
        kedua.close()


def test_skema_lebih_baru_dari_aplikasi_ditolak(berkas_db: Path) -> None:
    """A8/PRD 9.13: versi lama tidak boleh dipaksa jalan di atas skema yang lebih baru."""
    pendahulu = sqlite3.connect(str(berkas_db))
    pendahulu.execute(f"PRAGMA user_version = {VERSI_TERBARU + 1}")
    pendahulu.close()

    with pytest.raises(db.SkemaTerlaluBaru):
        db.siapkan(berkas_db)


# --- PRAGMA wajib (T1, A2) --------------------------------------------------------------


def test_pragma_wajib_terpasang(basis_data: sqlite3.Connection) -> None:
    assert basis_data.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert basis_data.execute("PRAGMA busy_timeout").fetchone()[0] == db.BUSY_TIMEOUT_MS
    assert basis_data.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_hasil_antara_sqlite_di_memori_bukan_di_folder_temp(
    basis_data: sqlite3.Connection,
) -> None:
    """GROUP BY/ORDER BY besar tidak boleh bergantung pada folder temp sistem yang bisa ditolak.

    Kejadian nyata 9 Okt 2026: setelah refresh 916 emiten (999.421 baris), langkah arsip gagal
    dengan `unable to open database file` karena SQLite mencoba membuat berkas sementara di
    folder temp yang tidak bisa ditulis. Nilai 2 = MEMORY.
    """
    assert basis_data.execute("PRAGMA temp_store").fetchone()[0] == 2


# --- append-only (S1, aturan keras 3) ---------------------------------------------------


def test_revisi_baru_menambah_baris_dan_tampilan_memilih_yang_terakhir(
    basis_data: sqlite3.Connection,
) -> None:
    with db.tulis(basis_data):
        _sisip_harga(basis_data, close=1000, diketahui_pada=DIKETAHUI_PAGI)
        _sisip_harga(basis_data, close=1050, diketahui_pada=DIKETAHUI_SORE)

    jumlah = basis_data.execute(
        "SELECT COUNT(*) FROM harga_harian WHERE kode = 'AAAA' AND tanggal = ?", (TANGGAL,)
    ).fetchone()[0]
    terkini = basis_data.execute(
        "SELECT close FROM v_harga_harian_terkini WHERE kode = 'AAAA' AND tanggal = ?", (TANGGAL,)
    ).fetchone()

    assert jumlah == 2, "perbaikan data harus menambah baris, bukan menimpa"
    assert terkini["close"] == 1050


def test_ubah_baris_ditolak_trigger(basis_data: sqlite3.Connection) -> None:
    with db.tulis(basis_data):
        _sisip_harga(basis_data)

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        basis_data.execute("UPDATE harga_harian SET close = 1")


def test_hapus_baris_ditolak_trigger(basis_data: sqlite3.Connection) -> None:
    with db.tulis(basis_data):
        _sisip_harga(basis_data)

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        basis_data.execute("DELETE FROM harga_harian")


def test_catatan_cek_sumber_kedua_juga_append_only(basis_data: sqlite3.Connection) -> None:
    """Catatan bukti kepatuhan mingguan tidak boleh bisa disunting atau dihapus.

    Kalau barisnya bisa diubah, keadaan cadence bisa dibuat terlihat patuh tanpa pernah
    menjalankan ceknya — persis yang membuat catatan ini ada (PRD 7.3).
    """
    with db.tulis(basis_data):
        _sisip_cek(basis_data)

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        basis_data.execute("UPDATE cek_sumber_kedua SET dijalankan_pada = ?", (DIKETAHUI_PAGI,))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        basis_data.execute("DELETE FROM cek_sumber_kedua")


def test_cakupan_cek_sumber_kedua_yang_tidak_dikenal_ditolak(basis_data: sqlite3.Connection) -> None:
    """Salah ketik cakupan harus gagal berisik, bukan tersimpan sebagai keadaan ketiga."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_cek(basis_data, cakupan="lengkap_sekali")


# --- batasan nilai (T8, STRICT) ---------------------------------------------------------


def test_tanggal_bukan_iso_ditolak(basis_data: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_harga(basis_data, tanggal="06 Okt 2026")


def test_harga_berpecahan_ditolak_kolom_integer(basis_data: sqlite3.Connection) -> None:
    """T8: harga INTEGER rupiah; nilai berpecahan sumber masuk kolom `*_mentah`."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            basis_data.execute(
                "INSERT INTO harga_harian (kode, tanggal, close, sumber, diketahui_pada)"
                " VALUES (?, ?, ?, ?, ?)",
                ("AAAA", TANGGAL, "1000.5", SUMBER_UJI, DIKETAHUI_PAGI),
            )


def test_split_tanpa_rasio_ditolak(basis_data: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            basis_data.execute(
                "INSERT INTO aksi_korporasi (kode, tanggal, jenis, sumber, diketahui_pada)"
                " VALUES (?, ?, 'split', ?, ?)",
                ("AAAA", TANGGAL, SUMBER_UJI, DIKETAHUI_PAGI),
            )


def test_log_jalan_menunjuk_snapshot_yang_tidak_ada_ditolak(basis_data: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            basis_data.execute(
                "INSERT INTO log_jalan (waktu, proses, hasil, pesan, id_snapshot)"
                " VALUES (?, 'uji', 'gagal', 'snapshot tidak ada', 99)",
                (DIKETAHUI_SORE,),
            )


# --- transaksi (A6) ---------------------------------------------------------------------


def test_transaksi_gagal_dibatalkan_seluruhnya(basis_data: sqlite3.Connection) -> None:
    with pytest.raises(RuntimeError, match="gagal disengaja"):
        with db.tulis(basis_data):
            _sisip_harga(basis_data)
            raise RuntimeError("gagal disengaja")

    jumlah = basis_data.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0]
    assert jumlah == 0
    assert not basis_data.in_transaction


def test_transaksi_bersarang_ditolak(basis_data: sqlite3.Connection) -> None:
    with db.tulis(basis_data):
        with pytest.raises(db.GalatBasisData, match="bersarang"):
            with db.tulis(basis_data):
                pass


def test_penulis_kedua_gagal_berisik_bukan_menunggu_tanpa_batas(
    basis_data: sqlite3.Connection, berkas_db: Path
) -> None:
    """A2/AC-19: penulis kedua tidak boleh menulis bersamaan.

    Diuji dengan `busy_timeout=0` pada koneksi kedua supaya hasilnya cepat dan pasti:
    yang diperiksa adalah *adanya* kunci tulis, bukan berapa lama ia menunggu.

    Galatnya **bukan** `sqlite3.OperationalError` mentah, melainkan `db.BasisDataTerkunci`
    berisi satu kalimat bersama yang bisa dikerjakan pengguna (K59): jendela dan baris perintah
    menjelaskan keadaan yang sama dengan kalimat yang sama. Kalimatnya diperiksa di sini, bukan
    hanya jenis galatnya — pesan yang berbeda-beda untuk satu keadaan adalah cacatnya sendiri.
    """
    kedua = db.hubungkan(berkas_db)
    kedua.execute("PRAGMA busy_timeout=0")
    sebelum = basis_data.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0]
    try:
        with db.tulis(basis_data):
            _sisip_harga(basis_data)
            with pytest.raises(db.BasisDataTerkunci) as galat:
                with db.tulis(kedua):
                    pass
    finally:
        kedua.close()

    assert str(galat.value) == db.KALIMAT_TERKUNCI
    assert "Tunggu sampai proses itu selesai" in str(galat.value)
    # Yang bisa dijanjikan `tulis()`: kuncinya diambil di muka, jadi tidak ada satu baris pun
    # yang tertulis ketika ia menolak. (Baris di transaksi yang berhasil tetap ada, seperti niat
    # ujinya: 1 harga baru dari koneksi pertama.)
    assert basis_data.execute("SELECT COUNT(*) FROM harga_harian").fetchone()[0] == sebelum + 1


# --- asal tanggal publikasi fundamental (migrasi 007, K18) -------------------------------


def _sisip_fundamental(
    sambungan: sqlite3.Connection,
    *,
    asal: str | None = None,
    diketahui_pada: str = DIKETAHUI_PAGI,
) -> None:
    """Satu baris fundamental. `asal=None` berarti kolomnya **tidak disebut sama sekali** —
    persis seperti basis data lama dan berkas impor lama, yang tidak mengenal kolom ini."""
    kolom = [
        "kode",
        "periode",
        "jenis_laporan",
        "tgl_publikasi",
        "mata_uang",
        "satuan_uang",
        "laba_induk",
        "sumber",
        "diketahui_pada",
    ]
    nilai: list[object] = [
        "AAAA",
        "2025-12-31",
        "tahunan",
        "2026-03-31",
        "IDR",
        "rupiah",
        1_000_000,
        SUMBER_UJI,
        diketahui_pada,
    ]
    if asal is not None:
        kolom.append("asal_tgl_publikasi")
        nilai.append(asal)
    sambungan.execute(
        f"INSERT INTO fundamental ({', '.join(kolom)})"
        f" VALUES ({', '.join('?' * len(nilai))})",
        nilai,
    )


def test_asal_tgl_publikasi_bawaannya_sumber(basis_data: sqlite3.Connection) -> None:
    """Baris yang tidak menyebut asalnya dibaca `sumber`, bukan kosong dan bukan tebakan.

    Inilah yang membuat baris lama (dan berkas impor lama yang tidak punya kolom ini) tetap
    benar setelah migrasi 007: `fundamental` append-only, jadi menulis ulang barisnya untuk
    mengisi kolom baru justru dilarang.
    """
    with db.tulis(basis_data):
        _sisip_fundamental(basis_data)

    asal = basis_data.execute("SELECT asal_tgl_publikasi FROM fundamental").fetchone()[0]
    assert asal == "sumber"


def test_asal_tgl_publikasi_yang_tidak_dikenal_ditolak(basis_data: sqlite3.Connection) -> None:
    """Nilai tak dikenal berhenti berisik, bukan tersimpan sebagai keadaan ketiga (aturan 7)."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_fundamental(basis_data, asal="perkiraan")


def test_asal_tgl_publikasi_kosong_ditolak(basis_data: sqlite3.Connection) -> None:
    """Kosong bukan `sumber`: yang tidak dinyatakan tidak boleh terbaca sebagai "dari sumber"."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_fundamental(basis_data, asal="")


def test_fundamental_menolak_asal_tanggal_yang_tidak_dikenal() -> None:
    """Penjaga di lapisan kode: pesannya menyebut kolomnya, bukan nama constraint SQLite."""
    with pytest.raises(ingesti.GalatIngesti, match="asal_tgl_publikasi"):
        ingesti.Fundamental(
            kode="AAAA",
            periode=date(2025, 12, 31),
            jenis_laporan="tahunan",
            tgl_publikasi=date(2026, 3, 31),
            asal_tgl_publikasi="perkiraan",
            laba_induk=1_000_000,
        )


# --- "tidak dinyatakan sumber" sebagai keadaan yang sah (migrasi 008, K22/K23) -----------
#
# Yang diuji di sini adalah **mesinnya**, bukan pemuat TOML-nya: kalau CHECK-nya dicabut atau
# NOT NULL-nya kembali terpasang, uji ini gagal. Itulah satu-satunya cara aturan "pernyataan
# sumber yang tidak ada tidak boleh menjadi angka" tetap benar setelah skema disunting lagi.


def _sisip_kepala_parameter(
    sambungan: sqlite3.Connection,
    *,
    nama: str = "biaya_broker",
    kelompok: str = "Uji",
    berlaku_sejak: str = TANGGAL,
    asal_berlaku_sejak: str | None = None,
) -> None:
    kolom = [
        "nama",
        "kelompok",
        "berlaku_sejak",
        "dicatat_pada",
        "sumber",
        "aktif",
        "sidik_jari",
    ]
    nilai: list[object] = [nama, kelompok, berlaku_sejak, TANGGAL, SUMBER_UJI, 1, "a" * 64]
    if asal_berlaku_sejak is not None:
        kolom.append("asal_berlaku_sejak")
        nilai.append(asal_berlaku_sejak)
    sambungan.execute(
        f"INSERT INTO parameter_bursa ({', '.join(kolom)})"
        f" VALUES ({', '.join('?' * len(nilai))})",
        nilai,
    )


def _sisip_biaya_broker(
    sambungan: sqlite3.Connection,
    *,
    minimum_beli: int | None = None,
    minimum_jual: int | None = None,
    kelompok: str = "Uji",
) -> None:
    sambungan.execute(
        "INSERT INTO parameter_biaya_broker"
        " (nama, kelompok, berlaku_sejak, dicatat_pada,"
        "  persen_beli_bp, minimum_beli, persen_jual_bp, minimum_jual)"
        " VALUES ('biaya_broker', ?, ?, ?, 15, ?, 25, ?)",
        (kelompok, TANGGAL, TANGGAL, minimum_beli, minimum_jual),
    )


def test_minimum_tarif_broker_boleh_null(basis_data: sqlite3.Connection) -> None:
    """K22: "sumber tidak menyatakan minimum" tersimpan NULL — dan itu bukan 0.

    Uji ini yang membuktikan bedanya. Kalau `NOT NULL` kembali terpasang (seperti di migrasi
    002), baris ini ditolak mesin — dan pemuat konfigurasi kembali dipaksa mengarang angka.
    """
    with db.tulis(basis_data):
        _sisip_kepala_parameter(basis_data)
        _sisip_biaya_broker(basis_data)

    baris = basis_data.execute(
        "SELECT minimum_beli, minimum_jual FROM parameter_biaya_broker"
    ).fetchone()
    assert baris["minimum_beli"] is None
    assert baris["minimum_jual"] is None


def test_minimum_tarif_broker_nol_tetap_bisa_ditulis(basis_data: sqlite3.Connection) -> None:
    """NULL dan 0 harus hidup berdampingan: yang pertama "tidak dinyatakan", yang kedua "tidak ada"."""
    with db.tulis(basis_data):
        _sisip_kepala_parameter(basis_data, kelompok="Tanpa minimum")
        _sisip_kepala_parameter(basis_data, kelompok="Tidak dinyatakan")
        _sisip_biaya_broker(basis_data, minimum_beli=0, minimum_jual=0, kelompok="Tanpa minimum")
        _sisip_biaya_broker(basis_data, kelompok="Tidak dinyatakan")

    baris = {
        satu["kelompok"]: satu["minimum_beli"]
        for satu in basis_data.execute(
            "SELECT kelompok, minimum_beli FROM parameter_biaya_broker"
        )
    }
    assert baris == {"Tanpa minimum": 0, "Tidak dinyatakan": None}


def test_minimum_tarif_broker_negatif_tetap_ditolak(basis_data: sqlite3.Connection) -> None:
    """Yang dilonggarkan hanya `NOT NULL`; batas bawahnya tetap ditegakkan mesin."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_kepala_parameter(basis_data)
            _sisip_biaya_broker(basis_data, minimum_beli=-1)


def test_asal_berlaku_sejak_bawaannya_sumber(basis_data: sqlite3.Connection) -> None:
    """Baris lama (dan berkas lama yang tak mengenal kolom ini) dibaca `sumber`, bukan kosong."""
    with db.tulis(basis_data):
        _sisip_kepala_parameter(basis_data)

    asal = basis_data.execute("SELECT asal_berlaku_sejak FROM parameter_bursa").fetchone()[0]
    assert asal == "sumber"


def test_asal_berlaku_sejak_yang_tidak_dikenal_ditolak(basis_data: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_kepala_parameter(basis_data, asal_berlaku_sejak="perkiraan")


def test_asal_berlaku_sejak_kosong_ditolak(basis_data: sqlite3.Connection) -> None:
    """Kosong bukan `sumber`, sama alasannya dengan `asal_tgl_publikasi` (migrasi 007)."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_kepala_parameter(basis_data, asal_berlaku_sejak="")


def test_komponen_all_in_disimpan_per_komponen_dan_append_only(
    basis_data: sqlite3.Connection,
) -> None:
    """K23: penanda all-in adalah baris di tabel anak, bukan kalimat — dan tak bisa disunting."""
    with db.tulis(basis_data):
        _sisip_kepala_parameter(basis_data)
        _sisip_biaya_broker(basis_data)
        for komponen in ("levy", "ppn", "pph_penjualan"):
            basis_data.execute(
                "INSERT INTO parameter_biaya_broker_termasuk"
                " (nama, kelompok, berlaku_sejak, dicatat_pada, komponen)"
                " VALUES ('biaya_broker', 'Uji', ?, ?, ?)",
                (TANGGAL, TANGGAL, komponen),
            )

    komponen = [
        satu[0]
        for satu in basis_data.execute(
            "SELECT komponen FROM parameter_biaya_broker_termasuk ORDER BY komponen"
        )
    ]
    assert komponen == ["levy", "pph_penjualan", "ppn"]
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        basis_data.execute("DELETE FROM parameter_biaya_broker_termasuk")


def test_komponen_all_in_yang_tidak_dikenal_ditolak(basis_data: sqlite3.Connection) -> None:
    """Daftar sahnya hidup di `skema.py` dan dipakai menyusun CHECK — bukan sekadar dokumentasi."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_kepala_parameter(basis_data)
            _sisip_biaya_broker(basis_data)
            basis_data.execute(
                "INSERT INTO parameter_biaya_broker_termasuk"
                " (nama, kelompok, berlaku_sejak, dicatat_pada, komponen)"
                " VALUES ('biaya_broker', 'Uji', ?, ?, 'broker')",
                (TANGGAL, TANGGAL),
            )


def test_komponen_all_in_tidak_boleh_yatim(basis_data: sqlite3.Connection) -> None:
    """Tabel anaknya berkunci asing ke entri induknya: komponen tanpa tarif tidak punya arti."""
    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            basis_data.execute(
                "INSERT INTO parameter_biaya_broker_termasuk"
                " (nama, kelompok, berlaku_sejak, dicatat_pada, komponen)"
                " VALUES ('biaya_broker', 'Tidak ada', ?, ?, 'levy')",
                (TANGGAL, TANGGAL),
            )


def test_migrasi_008_terpasang_dan_daftar_sahnya_satu_tempat() -> None:
    """Penjaga bentuk: kolomnya ada, versinya naik, dan daftar sahnya tidak disalin ke kode lain."""
    from mejasaham import konfigurasi, skema

    assert VERSI_TERBARU >= 8
    migrasi_008 = next(satu for satu in MIGRASI if satu.versi == 8)
    assert "parameter_biaya_broker_termasuk" in migrasi_008.sql
    assert "asal_berlaku_sejak" in migrasi_008.sql

    # Pemuat mengimpor daftar itu dari pemiliknya, bukan menyalinnya (aturan keras 5).
    assert konfigurasi.KOMPONEN_BIAYA_BROKER_TERMASUK is skema.KOMPONEN_BIAYA_BROKER_TERMASUK
    assert konfigurasi.ASAL_BERLAKU_SEJAK_SAH is skema.ASAL_BERLAKU_SEJAK_SAH


# ---------------------------------------------------------------------------------------
# Migrasi 012 — transaksi & posisi (F11, Tahap 2 langkah 3)
# ---------------------------------------------------------------------------------------


def _sisip_posisi(basis_data: sqlite3.Connection, *, mode: str = "nyata") -> None:
    basis_data.execute(
        "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, tgl_tutup, status, stop_terkini,"
        " id_rencana, mode, pelanggaran, catatan, sumber, diketahui_pada)"
        " VALUES (1, 1, 'AAAA', ?, NULL, 'aktif', 1000, NULL, ?, NULL, NULL, 'uji', ?)",
        (TANGGAL, mode, DIKETAHUI_PAGI),
    )


def test_migrasi_012_terpasang_dan_daftar_mode_satu_tempat() -> None:
    """Penjaga bentuk: tabelnya ada, dan daftar mode yang sah hidup di `skema.py` saja."""
    from mejasaham import posisi, risiko, skema

    assert VERSI_TERBARU >= 12
    migrasi_012 = next(satu for satu in MIGRASI if satu.versi == 12)
    for tabel in ("CREATE TABLE posisi", "CREATE TABLE transaksi", "v_posisi_terkini"):
        assert tabel in migrasi_012.sql
    assert "arus_dana" in migrasi_012.sql and "ADD COLUMN mode" in migrasi_012.sql

    # Modul meminjam daftarnya, bukan menyalinnya (aturan keras 5).
    assert posisi.MODE_SAH is skema.MODE_SAH
    assert risiko.MODE_SAH is skema.MODE_SAH


def test_mode_posisi_dan_transaksi_mengikuti_daftar_sah(basis_data: sqlite3.Connection) -> None:
    """Setiap nilai yang dinyatakan sah diterima mesin, dan yang tidak dikenal ditolak CHECK."""
    from mejasaham.skema import MODE_SAH

    with db.tulis(basis_data):
        for nomor, mode in enumerate(MODE_SAH, start=1):
            basis_data.execute(
                "INSERT INTO posisi (id_posisi, revisi, kode, tgl_buka, tgl_tutup, status,"
                " stop_terkini, id_rencana, mode, pelanggaran, catatan, sumber, diketahui_pada)"
                " VALUES (?, 1, 'AAAA', ?, NULL, 'aktif', 1000, NULL, ?, NULL, NULL, 'uji', ?)",
                (nomor, TANGGAL, mode, DIKETAHUI_PAGI),
            )
    assert (
        basis_data.execute("SELECT COUNT(*) FROM posisi").fetchone()[0] == len(MODE_SAH)
    )

    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            _sisip_posisi(basis_data, mode="karangan")


def test_migrasi_013_terpasang_dan_daftar_keputusan_satu_tempat() -> None:
    """Penjaga bentuk migrasi 013 (aksi korporasi pada posisi, PRD 9.11)."""
    from mejasaham import posisi, skema

    assert VERSI_TERBARU >= 13
    migrasi_013 = next(satu for satu in MIGRASI if satu.versi == 13)
    for bagian in (
        "CREATE TABLE keputusan_right_issue",
        "v_keputusan_right_issue_terkini",
        "ADD COLUMN tenggat",
        "ADD COLUMN tgl_stop",
    ):
        assert bagian in migrasi_013.sql

    # Modul meminjam daftarnya, bukan menyalinnya (aturan keras 5).
    assert posisi.KEPUTUSAN_RIGHT_ISSUE_SAH is skema.KEPUTUSAN_RIGHT_ISSUE_SAH


def test_tenggat_dan_basis_stop_null_bukan_arti_tidak_ada(basis_data: sqlite3.Connection) -> None:
    """`tenggat`/`tgl_stop` kosong = belum dinyatakan; barisnya tetap sah (aturan keras 2)."""
    with db.tulis(basis_data):
        basis_data.execute(
            "INSERT INTO aksi_korporasi (kode, tanggal, jenis, rasio_lama, rasio_baru,"
            " harga_tebus, sumber, diketahui_pada)"
            " VALUES ('AAAA', ?, 'right_issue', 5, 2, 1000, 'uji', ?)",
            (TANGGAL, DIKETAHUI_PAGI),
        )
        _sisip_posisi(basis_data, mode="nyata")
    baris = basis_data.execute(
        "SELECT tenggat FROM v_aksi_korporasi_terkini WHERE jenis = 'right_issue'"
    ).fetchone()
    assert baris["tenggat"] is None
    assert (
        basis_data.execute("SELECT tgl_stop FROM v_posisi_terkini").fetchone()["tgl_stop"] is None
    )


def test_arus_dana_null_berbeda_dari_nol(basis_data: sqlite3.Connection) -> None:
    """Pola K22/T35 di `ekuitas_harian`: NULL = belum dicatat, 0 = benar-benar tidak ada."""
    with db.tulis(basis_data):
        basis_data.execute(
            "INSERT INTO ekuitas_harian (tanggal, revisi, ekuitas, kas, arus_dana, mode, sumber,"
            " diketahui_pada) VALUES (?, 1, 100000000, NULL, 0, 'nyata', 'uji', ?)",
            (TANGGAL, DIKETAHUI_PAGI),
        )
        basis_data.execute(
            "INSERT INTO ekuitas_harian (tanggal, revisi, ekuitas, kas, arus_dana, mode, sumber,"
            " diketahui_pada) VALUES (?, 1, 100000000, NULL, NULL, NULL, 'uji', ?)",
            ("2026-10-07", DIKETAHUI_PAGI),
        )

    arus = [
        satu[0]
        for satu in basis_data.execute("SELECT arus_dana FROM ekuitas_harian ORDER BY tanggal")
    ]
    mode = [
        satu[0]
        for satu in basis_data.execute("SELECT mode FROM ekuitas_harian ORDER BY tanggal")
    ]
    assert arus == [0, None]
    assert mode == ["nyata", None]

    with pytest.raises(sqlite3.IntegrityError):
        with db.tulis(basis_data):
            basis_data.execute(
                "INSERT INTO ekuitas_harian (tanggal, revisi, ekuitas, kas, arus_dana, mode,"
                " sumber, diketahui_pada) VALUES ('2026-10-08', 1, 100000000, NULL, 0, 'karangan',"
                " 'uji', ?)",
                (DIKETAHUI_PAGI,),
            )


# --- Migrasi 014: jurnal keputusan (F7, PRD 9.8) ----------------------------------------


def test_migrasi_014_terpasang_dan_tampilan_revisinya_ada() -> None:
    """Penjaga bentuk migrasi 014 (jurnal keputusan, PRD 9.8/12)."""
    assert VERSI_TERBARU >= 14
    migrasi_014 = next(satu for satu in MIGRASI if satu.versi == 14)
    for bagian in (
        "CREATE TABLE jurnal",
        "v_jurnal_terkini",
        "trg_jurnal_satu_rantai_per_transaksi",
        "id_transaksi   INTEGER NOT NULL",
    ):
        assert bagian in migrasi_014.sql


def test_jurnal_menolak_baris_kosong_dan_dua_rantai_untuk_satu_keputusan(
    basis_data: sqlite3.Connection,
) -> None:
    """Dua penjaga PRD 9.8 di tingkat mesin: baris tanpa isi, dan dua rantai untuk satu keputusan.

    Tanpa yang pertama, jurnal memuat baris yang tidak mencatat apa pun; tanpa yang kedua,
    "pelajaran" untuk satu keputusan tersebar di dua tempat dan tidak ada cara tahu mana yang
    berlaku. Keduanya dijaga `skema.py` (migrasi 014), bukan hanya `jurnal.py`.
    """
    with db.tulis(basis_data):
        _sisip_posisi(basis_data, mode="nyata")

    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        with db.tulis(basis_data):
            basis_data.execute(
                "INSERT INTO jurnal (id_jurnal, revisi, id_transaksi, sumber, diketahui_pada)"
                " VALUES (1, 1, 1, 'uji', ?)",
                (DIKETAHUI_PAGI,),
            )

    with db.tulis(basis_data):
        basis_data.execute(
            "INSERT INTO jurnal (id_jurnal, revisi, id_transaksi, alasan, sumber, diketahui_pada)"
            " VALUES (1, 1, 1, 'catatan pertama', 'uji', ?)",
            (DIKETAHUI_PAGI,),
        )
        # Revisi pada rantai yang sama justru yang dikehendaki PRD 9.8 (versi lama disimpan).
        basis_data.execute(
            "INSERT INTO jurnal (id_jurnal, revisi, id_transaksi, pelajaran, sumber,"
            " diketahui_pada) VALUES (1, 2, 1, 'pelajaran', 'uji', ?)",
            (DIKETAHUI_PAGI,),
        )

    assert basis_data.execute("SELECT COUNT(*) FROM jurnal").fetchone()[0] == 2
    assert basis_data.execute("SELECT revisi FROM v_jurnal_terkini").fetchone()["revisi"] == 2

    with pytest.raises(sqlite3.IntegrityError, match="SATU rantai jurnal"):
        with db.tulis(basis_data):
            basis_data.execute(
                "INSERT INTO jurnal (id_jurnal, revisi, id_transaksi, alasan, sumber,"
                " diketahui_pada) VALUES (2, 1, 1, 'rantai kedua', 'uji', ?)",
                (DIKETAHUI_PAGI,),
            )


def test_jurnal_append_only_menolak_update_dan_delete(basis_data: sqlite3.Connection) -> None:
    """PRD 9.8: *"tidak ada penghapusan senyap"* — ditegakkan trigger, bukan disiplin."""
    with db.tulis(basis_data):
        _sisip_posisi(basis_data, mode="nyata")
        basis_data.execute(
            "INSERT INTO jurnal (id_jurnal, revisi, id_transaksi, alasan, sumber, diketahui_pada)"
            " VALUES (1, 1, 1, 'catatan', 'uji', ?)",
            (DIKETAHUI_PAGI,),
        )

    for pernyataan in (
        "UPDATE jurnal SET alasan = 'ditimpa' WHERE id_jurnal = 1",
        "DELETE FROM jurnal WHERE id_jurnal = 1",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            with db.tulis(basis_data):
                basis_data.execute(pernyataan)


# --- Migrasi 015: konteks pasar tersimpan (K61, PRD 8.2/11.1) -----------------------------


def test_migrasi_015_terpasang_dan_konteks_pasar_berkunci_lengkap(
    basis_data: sqlite3.Connection,
) -> None:
    """Penjaga bentuk migrasi 015: kunci sahnya angka tersimpan ada di skema, bukan hanya kode."""
    assert VERSI_TERBARU >= 15
    migrasi_015 = next(satu for satu in MIGRASI if satu.versi == 15)
    for bagian in (
        "CREATE TABLE konteks_pasar",
        "id_snapshot",
        "id_preset",
        "sumber_harga",
        "versi_hitung",
        "breadth_nilai",
        "breadth_status",
        "rezim",
        "indeks_penutupan",
        "PRIMARY KEY (id_snapshot, id_preset, sumber_harga)",
        "REFERENCES snapshot",
        "REFERENCES preset_saring",
    ):
        assert bagian in migrasi_015.sql

    assert basis_data.execute("SELECT COUNT(*) FROM konteks_pasar").fetchone()[0] == 0
    kolom = {
        baris["name"]
        for baris in basis_data.execute("PRAGMA table_info(konteks_pasar)").fetchall()
    }
    assert {"id_snapshot", "id_preset", "sumber_harga", "versi_hitung", "catatan"} <= kolom
