"""Uji lapisan **tulis** dasbor (aksi #19, K55/K59/T69; dipakai web sejak K91) — `mejasaham/layar/tulis.py`, tanpa Qt.

Yang diuji di sini bukan tampilannya, melainkan tiga janji yang membuat tombol "tulis" layak
ditekan:

* **Barisnya sama dengan baris perintah.** Tiap tindakan dijalankan **dua kali** atas dua basis
  data yang dibangun identik — sekali lewat `cli.main`, sekali lewat permintaan tulis jendela —
  lalu barisnya dibandingkan kolom demi kolom. Bukan "kira-kira sama": yang berbeda adalah catatan
  keputusan yang tidak bisa dihapus (append-only), dan itu harga yang tidak bisa dibayar ulang.
* **Ringkasan konfirmasi memuat angka yang akan ditulis** (K59 d), bukan angka lain.
* **Kunci tulis yang gagal berakhir sebagai pesan "belum menulis apa pun"** (K59 b) — dan
  sungguh-sungguh tidak menulis baris. Kegagalan lain **tidak** ditelan: ia tetap dilempar supaya
  jejaknya tercetak (aturan keras 7).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from mejasaham import (
    berkas,
    cadangan,
    cli,
    db,
    ingesti,
    jurnal,
    kandidat,
    konfigurasi,
    lokasi,
    pengatur,
    posisi,
    risiko,
    tampilan,
)
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    AksiKorporasi,
    Emiten,
    HargaHarian,
    KumpulanData,
)
from mejasaham.layar import tulis

SUMBER = "uji-tulis-jendela"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
KODE = "AAAA"
CLOSE = 2_320
RENTANG = 40
HARI = 24
VOLUME = 2_000_000

#: Kolom yang memang berbeda antar-jalan (cap waktu), jadi tidak ikut dibandingkan.
KOLOM_WAKTU = ("diketahui_pada", "dicatat_pada")

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

[[slippage]]
mode          = "tick"
nilai         = 1
berlaku_sejak = 2026-01-02
sumber        = "Keputusan produk K20 (uji)"
dicatat_pada  = 2026-10-06
"""


def _deret(kode: str) -> tuple[HargaHarian, ...]:
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


def _isi(sambungan: sqlite3.Connection) -> sqlite3.Connection:
    """Basis data yang cukup untuk ketiga pencatat: parameter, harga, preset, ekuitas, kandidat."""
    konfigurasi.simpan(sambungan, konfigurasi.urai("skema = 1\n\n" + PARAMETER, asal="uji"))
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=(Emiten(kode=KODE, nama="Emiten A", sektor_idx_ic="industri", sumber="uji"),),
            harga_harian=_deret(KODE),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    pengatur.siapkan_preset_bawaan(sambungan, date(2026, 7, 1))
    risiko.simpan_preset(sambungan, risiko.batas_bawaan(date(2026, 7, 1)))
    risiko.catat_ekuitas(
        sambungan, ekuitas=250_000_000, kas=100_000_000, tanggal=date(2026, 7, 1)
    )
    kandidat.buat(
        sambungan,
        KODE,
        status="watchlist",
        tesis="laba naik, PER di bawah sektor",
        pembatal_fundamental="ROE 5 tahun turun di bawah 10%",
        horizon="6-12 bulan",
        stop_awal=2_240,
        tanggal_tinjau="2026-08-01",
    )
    return sambungan


def _dua_basis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, sqlite3.Connection]:
    """Dua basis data identik: satu untuk jalur baris perintah, satu untuk jalur jendela."""
    hasil: dict[str, sqlite3.Connection] = {}
    for nama in ("perintah", "jendela"):
        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / nama))
        hasil[nama] = _isi(db.siapkan())
    return hasil


def _baris(sambungan: sqlite3.Connection, view: str) -> list[dict[str, object]]:
    """Isi satu view tanpa kolom cap waktu, supaya dua jalan bisa dibandingkan apa adanya."""
    return [
        {kunci: baris[kunci] for kunci in baris.keys() if kunci not in KOLOM_WAKTU}
        for baris in sambungan.execute(f"SELECT * FROM {view}")
    ]


#: Kolom `snapshot` yang berisi **waktu impor masing-masing jalan**, bukan isi yang dijanjikan
#: sama antara jendela dan `--impor` (K75/T76). Dikeluarkan **hanya** di uji impor di bawah,
#: bukan di `_baris()` bersama, supaya uji lain tetap membandingkan baris apa adanya.
KOLOM_WAKTU_IMPOR = ("jam_ambil", "batas_diketahui")


def _snapshot_tanpa_waktu_impor(sambungan: sqlite3.Connection) -> list[dict[str, object]]:
    """Baris `snapshot` tanpa kolom waktu impor; kolom lain dibandingkan penuh (K75/T76)."""
    return [
        {kunci: baris[kunci] for kunci in baris.keys() if kunci not in KOLOM_WAKTU_IMPOR}
        for baris in sambungan.execute("SELECT * FROM snapshot")
    ]


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "data"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(folder))
    return folder


@pytest.fixture()
def siap(folder_data: Path) -> Iterator[sqlite3.Connection]:
    sambungan = _isi(db.siapkan())
    try:
        yield sambungan
    finally:
        sambungan.close()


# ---------------------------------------------------------------------------------------
# Ringkasan konfirmasi & penolakan isian
# ---------------------------------------------------------------------------------------


def test_ringkasan_konfirmasi_memuat_angka_yang_akan_ditulis() -> None:
    """K59 d: dialog konfirmasi memuat kode, lembar, harga, dan biaya — bukan ringkasan kabur."""
    permintaan = tulis.permintaan_catat_transaksi(
        kode="tlkm",
        aksi="beli",
        lembar=200,
        harga=2320,
        mode="nyata",
        tanggal=date(2026, 7, 2),
        biaya=69_000,
    )
    assert permintaan.judul == "Catat transaksi TLKM beli"
    assert "TLKM" in permintaan.ringkasan
    assert "200 lbr" in permintaan.ringkasan
    assert "Rp 2.320" in permintaan.ringkasan
    assert "Rp 464.000" in permintaan.ringkasan  # nilai bruto 200 × 2.320
    assert "Rp 69.000" in permintaan.ringkasan
    assert "02 Jul 2026" in permintaan.ringkasan
    # Biaya yang tidak diisi tidak dikarang di ringkasan: sebabnya disebut.
    tanpa_biaya = tulis.permintaan_catat_transaksi(
        kode="TLKM", aksi="beli", lembar=200, harga=2320, mode="nyata"
    )
    assert "dihitung dari tarif broker" in tanpa_biaya.ringkasan


def test_isian_wajib_yang_kosong_ditolak_sebelum_pekerjaan_dimulai() -> None:
    """T69 b: isian yang tidak lengkap ditolak di utas tampilan, bukan sebagai kegagalan tulis."""
    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_catat_transaksi(kode="", aksi="beli", lembar=None, harga=None, mode="")
    assert "kode" in str(galat.value) and "lembar" in str(galat.value)
    assert "mode" in str(galat.value)


def test_lembar_atau_harga_nol_ditolak_bukan_dianggap_kosong() -> None:
    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_catat_transaksi(
            kode=KODE, aksi="beli", lembar=0, harga=CLOSE, mode="nyata"
        )
    assert "lebih dari nol" in str(galat.value)


def test_catatan_jurnal_kosong_ditolak() -> None:
    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_catat_jurnal(id_transaksi=1, ringkas_transaksi="…")
    assert "kosong" in str(galat.value)
    assert "Alasan" in str(galat.value)


def test_tandai_selesai_menuntut_tanggalnya() -> None:
    """Tanggal yang tersimpan harus yang dinyatakan pengguna — jendela tidak menebak hari ini."""
    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_catat_jurnal(
            id_transaksi=1, ringkas_transaksi="…", alasan="diterima", tandai_selesai=True
        )
    assert "Tanggal selesai" in str(galat.value)


# ---------------------------------------------------------------------------------------
# Barisnya sama dengan baris perintah (verifikasi aksi #19)
# ---------------------------------------------------------------------------------------


def test_transaksi_dari_jendela_sama_dengan_baris_perintah(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    basis = _dua_basis(tmp_path, monkeypatch)
    try:
        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "perintah"))
        kode_keluar = cli.main(
            [
                "--catat-transaksi", KODE,
                "--aksi", "beli",
                "--lembar", "200",
                "--harga", str(CLOSE),
                "--mode", "nyata",
                "--tanggal", "2026-07-02",
                "--biaya", "69000",
                "--alasan", "eksekusi uji",
            ]
        )
        assert kode_keluar == cli.KODE_OK

        permintaan = tulis.permintaan_catat_transaksi(
            kode=KODE,
            aksi="beli",
            lembar=200,
            harga=CLOSE,
            mode="nyata",
            tanggal=date(2026, 7, 2),
            biaya=69_000,
            catatan="eksekusi uji",
        )
        hasil = tulis.jalankan_permintaan(permintaan, basis["jendela"])
        assert hasil.berhasil, hasil.pesan

        for view in ("v_transaksi_terkini", "v_posisi_terkini"):
            assert _baris(basis["perintah"], view) == _baris(basis["jendela"], view), view
    finally:
        for sambungan in basis.values():
            sambungan.close()


def test_pelanggaran_tercatat_bukan_ditolak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transaksi tanpa rencana & tanpa stop tetap tercatat, dan pelanggarannya terlihat."""
    basis = _dua_basis(tmp_path, monkeypatch)
    try:
        permintaan = tulis.permintaan_catat_transaksi(
            kode=KODE, aksi="beli", lembar=100, harga=CLOSE, mode="nyata"
        )
        hasil = tulis.jalankan_permintaan(permintaan, basis["jendela"])
    finally:
        for sambungan in basis.values():
            sambungan.close()

    assert hasil.berhasil
    assert "PELANGGARAN" in hasil.pesan
    assert tulis.PESAN_PELANGGARAN_DICATAT.splitlines()[0][:40] in hasil.pesan


def test_rencana_dari_jendela_sama_dengan_baris_perintah(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    basis = _dua_basis(tmp_path, monkeypatch)
    try:
        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "perintah"))
        kode_keluar = cli.main(
            ["--hitung-risiko", KODE, "--jenis-stop", "order_sekuritas", "--simpan-rencana"]
        )
        assert kode_keluar == cli.KODE_OK

        sambungan = basis["jendela"]
        entri = kandidat.untuk_rencana(sambungan, KODE)
        masukan = risiko.siapkan_masukan(sambungan, KODE)
        hasil_hitung, _stop = risiko.hitung_untuk(
            masukan,
            harga_masuk=masukan.harga_acuan,
            harga_pembatal=entri.harga_pembatal,
            jenis_stop="order_sekuritas",
        )
        permintaan = tulis.permintaan_simpan_rencana(
            hasil=hasil_hitung,
            masukan=masukan,
            entri=entri,
            jenis_stop="order_sekuritas",
            id_snapshot=masukan.potret.id_snapshot,
        )
        assert "jenis stop" in permintaan.ringkasan
        hasil = tulis.jalankan_permintaan(permintaan, sambungan)
        assert hasil.berhasil, hasil.pesan
        assert "watchlist -> rencana" in hasil.pesan

        assert _baris(basis["perintah"], "v_rencana_terkini") == _baris(
            basis["jendela"], "v_rencana_terkini"
        )
        # Perpindahan status kandidat ikut sama — bukan efek samping yang hanya ada di satu jalur.
        assert _baris(basis["perintah"], "v_kandidat_terkini") == _baris(
            basis["jendela"], "v_kandidat_terkini"
        )
    finally:
        for sambungan in basis.values():
            sambungan.close()


def test_catatan_jurnal_dari_jendela_sama_dengan_baris_perintah(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    basis = _dua_basis(tmp_path, monkeypatch)
    for nama, sambungan in basis.items():
        posisi.catat_transaksi(
            sambungan,
            KODE,
            "beli",
            harga=CLOSE,
            lembar=100,
            mode="nyata",
            tanggal=date(2026, 7, 2),
        )
    try:
        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "perintah"))
        kode_keluar = cli.main(
            [
                "--jurnal-catat", "1",
                "--alasan", "pelanggaran diterima secara sadar",
                "--pelajaran", "periksa total risiko sebelum menyimpan rencana",
                "--tandai-selesai",
                "--tanggal", "2026-07-03",
            ]
        )
        assert kode_keluar == cli.KODE_OK

        baris = jurnal.rekap(basis["jendela"]).keputusan[0]
        permintaan = tulis.permintaan_catat_jurnal(
            id_transaksi=baris.transaksi.id_transaksi,
            ringkas_transaksi=baris.ringkas(),
            alasan="pelanggaran diterima secara sadar",
            pelajaran="periksa total risiko sebelum menyimpan rencana",
            tandai_selesai=True,
            tanggal_selesai=date(2026, 7, 3),
        )
        assert "dipertahankan dari catatan sebelumnya" in permintaan.ringkasan
        hasil = tulis.jalankan_permintaan(permintaan, basis["jendela"])
        assert hasil.berhasil, hasil.pesan
        assert "baris jurnal PERTAMA" in hasil.pesan

        assert _baris(basis["perintah"], "v_jurnal_terkini") == _baris(
            basis["jendela"], "v_jurnal_terkini"
        )
    finally:
        for sambungan in basis.values():
            sambungan.close()


def test_revisi_jurnal_menambah_revisi_bukan_menimpa(siap: sqlite3.Connection) -> None:
    """PRD 9.8: catatan kedua menambah revisi, dan bidang yang kosong dipertahankan."""
    posisi.catat_transaksi(
        siap, KODE, "beli", harga=CLOSE, lembar=100, mode="nyata", tanggal=date(2026, 7, 2)
    )
    pertama = tulis.jalankan_permintaan(
        tulis.permintaan_catat_jurnal(id_transaksi=1, ringkas_transaksi="…", alasan="alasan awal"),
        siap,
    )
    assert pertama.berhasil
    kedua = tulis.jalankan_permintaan(
        tulis.permintaan_catat_jurnal(
            id_transaksi=1, ringkas_transaksi="…", pelajaran="pelajaran kedua"
        ),
        siap,
    )
    assert kedua.berhasil
    assert "Revisi r1 disimpan, bukan ditimpa" in kedua.pesan
    terkini = jurnal.catatan_terkini(siap, 1)
    assert terkini is not None and terkini.revisi == 2
    assert terkini.alasan == "alasan awal", "bidang yang tidak diisi dipertahankan"
    assert terkini.pelajaran == "pelajaran kedua"


# ---------------------------------------------------------------------------------------
# Kunci tulis (A2/AC-19, K59)
# ---------------------------------------------------------------------------------------


def test_kunci_tulis_gagal_berpesan_belum_menulis_dan_tidak_menulis_baris(
    siap: sqlite3.Connection, folder_data: Path
) -> None:
    """K59 b: pesannya menyebut "belum menulis apa pun" — dan itu benar, bukan penghibur."""
    # Batas tunggu dikecilkan supaya ujinya cepat; yang diperiksa *adanya* kunci, bukan lamanya.
    siap.execute("PRAGMA busy_timeout=50")
    penulis_lain = db.hubungkan(folder_data / lokasi.NAMA_BERKAS_BASIS_DATA)
    penulis_lain.execute("PRAGMA busy_timeout=0")
    sebelum = siap.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0]
    try:
        penulis_lain.execute("BEGIN IMMEDIATE")
        permintaan = tulis.permintaan_catat_transaksi(
            kode=KODE, aksi="beli", lembar=100, harga=CLOSE, mode="nyata"
        )
        hasil = tulis.jalankan_permintaan(permintaan, siap)
        penulis_lain.execute("ROLLBACK")
    finally:
        penulis_lain.close()

    assert hasil.berhasil is False
    assert db.KALIMAT_TERKUNCI in hasil.pesan
    assert tulis.KALIMAT_BELUM_MENULIS in hasil.pesan
    assert "Tunggu sampai proses itu selesai" in hasil.pesan
    assert siap.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0] == sebelum


def test_kegagalan_selain_kunci_tidak_ditelan(siap: sqlite3.Connection) -> None:
    """Aturan keras 7: hanya kunci tulis yang jadi pesan; galat lain tetap dilempar."""
    permintaan = tulis.permintaan_catat_transaksi(
        kode=KODE, aksi="beli", lembar=100, harga=2001, mode="nyata"  # bukan kelipatan tick
    )
    with pytest.raises(posisi.GalatPosisi):
        tulis.jalankan_permintaan(permintaan, siap)


# ---------------------------------------------------------------------------------------
# Impor berkas dari jendela (aksi #19b, K59 c)
# ---------------------------------------------------------------------------------------

#: Jenis -> nama berkasnya, dibaca dari pembaca impor: nama berkas hanya ditulis sekali di sana.
NAMA_BERKAS = {jenis: nama for nama, jenis in ingesti.BERKAS_IMPOR_DIKENAL}


def _tulis_berkas(folder: Path, jenis: str, baris: tuple[dict[str, str], ...]) -> Path:
    """Tulis satu berkas impor dengan kolom persis menurut spesifikasi pembacanya."""
    kolom = berkas.SPESIFIKASI[jenis].nama_kolom
    isi = [";".join(kolom)]
    for satu in baris:
        lengkap = {nama: "" for nama in kolom}
        lengkap.update(satu)
        isi.append(";".join(lengkap[nama] for nama in kolom))
    jalur = folder / NAMA_BERKAS[jenis]
    jalur.write_text("\n".join(isi) + "\n", encoding="utf-8")
    return jalur


def _folder_impor(tmp_path: Path) -> Path:
    """Folder impor berisi tiga berkas kecil: emiten (2 baris), kalender (3), notasi (1)."""
    folder = tmp_path / "konfigurasi"
    folder.mkdir(parents=True, exist_ok=True)
    _tulis_berkas(
        folder,
        "emiten",
        (
            {"kode": "AAAA", "nama": "Emiten A", "sumber": "uji impor", "dicatat_pada": "2026-10-01"},
            {"kode": "BBBB", "nama": "Emiten B", "sumber": "uji impor", "dicatat_pada": "2026-10-01"},
        ),
    )
    _tulis_berkas(
        folder,
        "kalender_bursa",
        (
            {"tanggal": "2026-07-01", "hari_bursa": "ya", "keterangan": "uji"},
            {"tanggal": "2026-07-02", "hari_bursa": "ya", "keterangan": "uji"},
            {"tanggal": "2026-07-03", "hari_bursa": "tidak", "keterangan": "libur uji"},
        ),
    )
    _tulis_berkas(
        folder,
        "notasi_khusus",
        ({"kode": "AAAA", "jenis": "suspensi", "tanggal_mulai": "2026-07-01"},),
    )
    return folder


def test_ringkasan_impor_memuat_jumlah_baris_per_tabel(tmp_path: Path) -> None:
    """K59 d: yang disetujui pengguna adalah **jumlah baris per tabel**, bukan "folder ini"."""
    folder = _folder_impor(tmp_path)
    pembacaan = tulis.baca_folder_impor(folder)
    assert pembacaan.berhasil, pembacaan.galat

    ringkasan = tulis.ringkasan_impor(pembacaan)

    assert str(folder) in ringkasan
    assert "emiten.csv (2 baris)" in ringkasan
    assert "kalender-bursa.csv (3 baris)" in ringkasan
    assert "notasi-khusus.csv (1 baris)" in ringkasan
    assert "6 baris dari 3 berkas" in ringkasan
    # Berkas yang tidak ada disebut apa adanya — folder yang kehilangan satu berkas tidak boleh
    # tampak seperti folder yang lengkap (impor bertahap memang sah).
    assert "fundamental.csv" in ringkasan
    assert "(seluruh berkas yang dicari ada)" not in ringkasan
    assert f"{ingesti.PREFIKS_SUMBER_IMPOR}: {folder}" in ringkasan
    # Append-only dinyatakan di dialognya, bukan hanya diketahui dari dokumen.
    assert "append-only" in ringkasan


def test_ringkasan_impor_menyebut_bila_semua_berkas_yang_dicari_ada(tmp_path: Path) -> None:
    folder = tmp_path / "lengkap"
    folder.mkdir()
    for nama, jenis in ingesti.BERKAS_IMPOR_DIKENAL:
        _tulis_berkas(folder, jenis, ())
    pembacaan = tulis.baca_folder_impor(folder)
    assert pembacaan.berhasil, pembacaan.galat
    ringkasan = tulis.ringkasan_impor(pembacaan)
    assert "(seluruh berkas yang dicari ada)" in ringkasan
    assert f"0 baris dari {len(ingesti.BERKAS_IMPOR_DIKENAL)} berkas" in ringkasan


def test_impor_dari_jendela_sama_dengan_baris_perintah(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Impor dari jendela menulis baris yang **sama** dengan `--impor`, bukan yang mirip."""
    basis = _dua_basis(tmp_path, monkeypatch)
    folder = _folder_impor(tmp_path)
    try:
        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "perintah"))
        assert cli.main(["--impor", str(folder)]) == cli.KODE_OK

        pembacaan = tulis.baca_folder_impor(folder)
        assert pembacaan.berhasil, pembacaan.galat
        permintaan = tulis.permintaan_impor(pembacaan=pembacaan)
        assert "emiten.csv (2 baris)" in permintaan.ringkasan
        hasil = tulis.jalankan_permintaan(permintaan, basis["jendela"])
        assert hasil.berhasil, hasil.pesan
        assert "baris baru" in hasil.pesan

        for view in ("emiten", "kalender_bursa", "notasi_khusus"):
            assert _baris(basis["perintah"], view) == _baris(basis["jendela"], view), view

        # `snapshot` dibandingkan **tanpa** `jam_ambil`/`batas_diketahui`: keduanya adalah waktu
        # impor masing-masing jalan, dan kedua jalur memang mengimpor pada saat yang berbeda
        # (K75/T76). Kolom lain — termasuk `jumlah_emiten`, `jumlah_gagal`, dan `catatan` — tetap
        # dibandingkan penuh; baris berikutnya menjaga supaya yang dilepas **hanya** dua kolom itu.
        snapshot_perintah = _snapshot_tanpa_waktu_impor(basis["perintah"])
        snapshot_jendela = _snapshot_tanpa_waktu_impor(basis["jendela"])
        assert snapshot_perintah == snapshot_jendela
        assert snapshot_perintah, "impor harus menulis baris snapshot"
        assert set(snapshot_perintah[0]) == {
            "id_snapshot",
            "tanggal_data",
            "jumlah_emiten",
            "jumlah_gagal",
            "versi_skema",
            "versi_aplikasi",
            "catatan",
        }
    finally:
        for sambungan in basis.values():
            sambungan.close()


def test_impor_menulis_yang_dikonfirmasi_bukan_isi_folder_saat_itu(
    siap: sqlite3.Connection, tmp_path: Path
) -> None:
    """K59 d sampai ke impor: yang ditulis adalah objek yang dikonfirmasi, bukan bacaan kedua.

    Berkasnya sengaja dihapus **sesudah** konfirmasi. Impor yang membaca ulang akan gagal
    ("folder tidak memuat berkas"); impor yang membawa hasil bacaannya menulis barisnya — dan
    itulah yang benar, sebab itulah yang disetujui pengguna.
    """
    folder = _folder_impor(tmp_path)
    pembacaan = tulis.baca_folder_impor(folder)
    permintaan = tulis.permintaan_impor(pembacaan=pembacaan)
    (folder / NAMA_BERKAS["notasi_khusus"]).unlink()

    hasil = tulis.jalankan_permintaan(permintaan, siap)

    assert hasil.berhasil, hasil.pesan
    assert siap.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0] == 1
    assert siap.execute("SELECT COUNT(*) FROM kalender_bursa").fetchone()[0] == 3


def test_berkas_yang_ditolak_pembaca_ditolak_dengan_pesan_yang_sama(
    siap: sqlite3.Connection,
    folder_data: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Aksi #18 tetap berlaku di jendela: kolom berlebih **yang berisi** menolak seluruh impor.

    Yang dibuktikan dua hal: jendela menolaknya **sebelum** ada dialog tulis (pesannya untuk
    layar, bukan galat), dan kalimatnya sama dengan yang dicetak baris perintah — bukan versi
    kedua yang mirip.
    """
    folder = tmp_path / "rusak"
    folder.mkdir()
    (folder / "notasi-khusus.csv").write_text(
        "kode;jenis;tanggal_mulai;tanggal_selesai;keterangan\n"
        "AAAA;suspensi;2026-07-01;;catatan;ekor-yang-hilang\n",
        encoding="utf-8",
    )

    pembacaan = tulis.baca_folder_impor(folder)
    assert pembacaan.berhasil is False
    assert pembacaan.galat is not None and "ekor-yang-hilang" in pembacaan.galat
    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_impor(pembacaan=pembacaan)
    assert pembacaan.galat in str(galat.value)

    kode_keluar = cli.main(["--impor", str(folder)])

    assert kode_keluar == cli.KODE_GAGAL
    tercetak = capsys.readouterr()
    assert pembacaan.galat in tercetak.err
    assert siap.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0] == 0


def test_impor_yang_terkunci_berhenti_dengan_belum_menulis_apa_pun(
    siap: sqlite3.Connection, folder_data: Path, tmp_path: Path
) -> None:
    """A2/AC-19 + K59 b: impor yang tidak mendapat kunci tulis tidak menulis satu baris pun."""
    siap.execute("PRAGMA busy_timeout=50")
    penulis_lain = db.hubungkan(folder_data / lokasi.NAMA_BERKAS_BASIS_DATA)
    penulis_lain.execute("PRAGMA busy_timeout=0")
    folder = _folder_impor(tmp_path)
    permintaan = tulis.permintaan_impor(pembacaan=tulis.baca_folder_impor(folder))
    try:
        penulis_lain.execute("BEGIN IMMEDIATE")
        hasil = tulis.jalankan_permintaan(permintaan, siap)
    finally:
        penulis_lain.execute("ROLLBACK")
        penulis_lain.close()

    assert hasil.berhasil is False
    assert db.KALIMAT_TERKUNCI in hasil.pesan
    assert tulis.KALIMAT_BELUM_MENULIS in hasil.pesan
    assert siap.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0] == 0
    assert siap.execute("SELECT COUNT(*) FROM kalender_bursa").fetchone()[0] == 0


def test_impor_yang_terkunci_tidak_menambah_penantian_kedua(
    siap: sqlite3.Connection,
    folder_data: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gagal karena kunci **tidak** dicatat ke log: pencatatannya hanya menambah tunggu kedua.

    Terukur 17 Okt 2026 atas data nyata: impor yang terkunci berhenti setelah **11,16 detik**
    (dua penantian `busy_timeout`), padahal K59 a menyebut satu. Log tidak bisa ditulis selama
    kuncinya dipegang proses lain, jadi percobaannya dihapus — dan yang memastikannya uji ini,
    bukan niat. Jalur gagal yang **lain** tetap mencatat log seperti semula (kendali positif).
    """
    from mejasaham import pengatur

    dicatat: list[str] = []
    monkeypatch.setattr(
        pengatur, "_catat_log", lambda *a, **k: dicatat.append(str(k.get("pesan")))
    )

    # (a) gagal karena kunci: tidak ada catatan log, dan pesannya tetap kalimat bersama.
    siap.execute("PRAGMA busy_timeout=50")
    penulis_lain = db.hubungkan(folder_data / lokasi.NAMA_BERKAS_BASIS_DATA)
    penulis_lain.execute("PRAGMA busy_timeout=0")
    folder = _folder_impor(tmp_path)
    permintaan = tulis.permintaan_impor(pembacaan=tulis.baca_folder_impor(folder))
    try:
        penulis_lain.execute("BEGIN IMMEDIATE")
        hasil = tulis.jalankan_permintaan(permintaan, siap)
    finally:
        penulis_lain.execute("ROLLBACK")
        penulis_lain.close()
    assert hasil.berhasil is False
    assert db.KALIMAT_TERKUNCI in hasil.pesan
    assert dicatat == [], "log tidak boleh dicoba selagi kuncinya dipegang proses lain"

    # (b) kendali positif: gagal karena berkasnya tidak ada tetap dicatat ke log.
    tidak_ada = tmp_path / "tidak-ada"
    laporan = pengatur.jalankan_impor(siap, tidak_ada)
    assert laporan.sukses is False
    assert len(dicatat) == 1 and "tidak ada atau bukan folder" in dicatat[0]


# ---------------------------------------------------------------------------------------
# Cadangan dari jendela (aksi #19c, K59 c/e)
# ---------------------------------------------------------------------------------------


def test_ringkasan_cadangan_menyebut_folder_tujuan_dan_retensinya(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """K59 d: yang disetujui pengguna adalah **folder yang menerima cadangan** — dan ia disebut."""
    data = tmp_path / "data"
    tujuan = tmp_path / "cadangan-pilihan"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(data))
    monkeypatch.setenv(cadangan.ENV_FOLDER_CADANGAN, str(tujuan))

    permintaan = tulis.permintaan_cadangan()

    assert permintaan.judul == "Buat cadangan data"
    assert str(data) in permintaan.ringkasan
    assert str(tujuan) in permintaan.ringkasan
    assert f"{cadangan.RETENSI_BAWAAN} cadangan terbaru" in permintaan.ringkasan
    assert "VACUUM INTO" in permintaan.ringkasan
    # Janji yang benar untuk tindakan ini: ia membaca, bukan menulis baris.
    assert "hanya MEMBACA basis data" in permintaan.ringkasan
    assert tulis.catatan_pemulihan() in permintaan.ringkasan
    # Pertanyaannya bukan pertanyaan pencatat: tindakan ini tidak menulis baris apa pun.
    assert permintaan.pertanyaan == tulis.PERTANYAAN_CADANGAN
    assert "baris" not in permintaan.pertanyaan


def test_cadangan_dari_jendela_menghasilkan_folder_yang_lolos_integrity_check(
    siap: sqlite3.Connection, tmp_path: Path
) -> None:
    """Aksi #19c: cadangan dari jendela = folder ber-manifest.json + basis data yang sehat."""
    tujuan = tmp_path / "cadangan"

    hasil = tulis.jalankan_permintaan(tulis.permintaan_cadangan(tujuan=tujuan), siap)

    assert hasil.berhasil, hasil.pesan
    tersimpan = cadangan.daftar(tujuan)
    assert len(tersimpan) == 1
    folder = tersimpan[0]
    assert (folder / cadangan.NAMA_MANIFEST).is_file()
    periksa = sqlite3.connect(folder / cadangan.NAMA_DB)
    try:
        assert periksa.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        periksa.close()
    assert str(folder) in hasil.pesan
    assert "1 cadangan tersimpan" in hasil.pesan
    # Yang belum bisa dikerjakan dari jendela disebut, beserta perintah yang benar (K59 e).
    assert tulis.catatan_pemulihan(folder) in hasil.pesan
    assert "--pulihkan" in hasil.pesan


def test_cadangan_yang_folder_tujuannya_di_dalam_folder_data_ditolak_sebelum_konfirmasi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T69 b: cadangan yang pasti ditolak tidak pernah sampai ke dialog konfirmasi.

    Pemeriksanya sama dengan yang dipakai `cadangan.buat` (satu fungsi), jadi tidak ada syarat
    kedua yang bisa berbeda dari syarat yang menolak nanti.
    """
    data = tmp_path / "data"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(data))

    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_cadangan(tujuan=data / "cadangan")

    assert "di luar folder data" in str(galat.value)


def test_cadangan_yang_gagal_jadi_pesan_bukan_traceback(
    siap: sqlite3.Connection, tmp_path: Path
) -> None:
    """Kegagalan folder tujuan menjadi pesan yang bisa dikerjakan + janji yang benar.

    Kegagalannya **nyata** (path yang sudah dipakai berkas biasa), bukan `buat` yang diganti:
    yang diuji adalah apa yang benar-benar terjadi pada jalur jendela.
    """
    bukan_folder = tmp_path / "bukan-folder"
    bukan_folder.write_text("sudah dipakai berkas lain", encoding="utf-8")

    hasil = tulis.jalankan_permintaan(tulis.permintaan_cadangan(tujuan=bukan_folder), siap)

    assert hasil.berhasil is False
    assert str(bukan_folder) in hasil.pesan
    assert tulis.KALIMAT_BASIS_TIDAK_DISENTUH in hasil.pesan
    # Janji pencatat **tidak** dipakai di sini: yang benar untuk cadangan bukan "belum menulis".
    assert tulis.KALIMAT_BELUM_MENULIS not in hasil.pesan


def test_daftar_cadangan_dari_jendela_sama_dengan_baris_perintah(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Aksi #19c: daftar di jendela bukan salinan — barisnya baris yang sama dengan CLI."""
    data = tmp_path / "data"
    tujuan = tmp_path / "cadangan"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(data))
    sambungan = _isi(db.siapkan())
    try:
        for hari in (1, 2):
            cadangan.buat(
                sambungan,
                folder_data=data,
                tujuan=tujuan,
                sekarang=datetime(2026, 10, hari, 12, 0, tzinfo=timezone.utc),
            )
    finally:
        sambungan.close()

    assert cli.main(["--daftar-cadangan", "--folder-cadangan", str(tujuan)]) == cli.KODE_OK
    tercetak = capsys.readouterr().out.strip().splitlines()

    teks = tulis.ringkasan_daftar_cadangan(tujuan)

    assert len(tercetak) == 2, "dua cadangan tersimpan, dua baris dicetak"
    assert teks.splitlines()[3:5] == tercetak, "baris daftarnya sama persis, bukan mirip"
    assert str(tujuan) in teks
    assert tulis.catatan_pemulihan() in teks


def test_daftar_cadangan_kosong_dikatakan_apa_adanya(tmp_path: Path) -> None:
    """Belum ada cadangan bukan daftar kosong yang ambigu — dan itu kalimat yang sama dengan CLI."""
    teks = tulis.ringkasan_daftar_cadangan(tmp_path / "belum-ada")
    assert "Belum ada cadangan." in teks


# ---------------------------------------------------------------------------------------
# Aksi #19d: ubah stop + keputusan right issue dari jendela (K62, T71 c)
# ---------------------------------------------------------------------------------------

#: Tanggal aksi right issue uji: sesudah posisinya dibuka (2 Jul 2026), sebelum hari ini.
TGL_RIGHT_ISSUE = date(2026, 7, 10)


def _posisi_terbuka(sambungan: sqlite3.Connection, *, lembar: int = 200) -> posisi.Posisi:
    """Satu posisi aktif di `KODE` — lewat jalur tulis yang sama dengan `--catat-transaksi`.

    Transaksinya membawa stop awal dari tesis kandidat (`stop_awal` 2.240), jadi V5 bisa diuji
    tanpa mengarang level stop: yang menurunkannya adalah stop baru di bawah angka itu.
    """
    posisi.catat_transaksi(
        sambungan,
        KODE,
        "beli",
        harga=CLOSE,
        lembar=lembar,
        mode="nyata",
        tanggal=date(2026, 7, 2),
    )
    return posisi.wajib_ada(sambungan, 1)


def _simpan_right_issue(sambungan: sqlite3.Connection) -> None:
    """Satu right issue uji (rasio 5:2, harga tebus = CLOSE) lewat jalur impor yang sebenarnya."""
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=(Emiten(kode=KODE, nama="Emiten A", sektor_idx_ic="industri", sumber="uji"),),
            aksi_korporasi=(
                AksiKorporasi(
                    kode=KODE,
                    tanggal=TGL_RIGHT_ISSUE,
                    jenis="right_issue",
                    rasio_lama=5,
                    rasio_baru=2,
                    harga_tebus=CLOSE,
                    tenggat="2026-07-20",
                    keterangan="baris uji, bukan pengumuman resmi",
                ),
            ),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )


def _hak_tunggal(sambungan: sqlite3.Connection) -> posisi.HakRightIssue:
    hak = posisi.hak_right_issue(sambungan, kode=KODE, hari_ini=date(2026, 7, 11))
    assert len(hak) == 1, f"right issue uji harus satu, bukan {len(hak)}"
    return hak[0]


def test_ringkasan_ubah_stop_memuat_angka_yang_akan_ditulis(
    siap: sqlite3.Connection,
) -> None:
    """K59 d: dialog konfirmasi memuat posisi, stop lama → baru, dan basis `tgl_stop`-nya."""
    sasaran = _posisi_terbuka(siap)

    permintaan = tulis.permintaan_ubah_stop(
        sasaran=sasaran, stop=2500, alasan="naikkan stop", tanggal=date(2026, 7, 3)
    )

    assert permintaan.judul == f"Ubah stop posisi #1 {KODE}"
    assert tampilan.rupiah(sasaran.stop_terkini) in permintaan.ringkasan
    assert tampilan.rupiah(2500) in permintaan.ringkasan
    # Basis stop ditulis apa adanya: tanpa itu, split sesudahnya dipindahkan dari tanggal yang
    # tidak pernah disetujui pengguna.
    assert "03 Jul 2026" in permintaan.ringkasan
    assert "naikkan stop" in permintaan.ringkasan
    assert tulis.CATATAN_STOP_REVISI in permintaan.ringkasan


def test_ubah_stop_menolak_posisi_kosong_dan_stop_tidak_diisi(siap: sqlite3.Connection) -> None:
    """Jendela tidak memilihkan posisi, dan kotak kosong berarti tidak diisi — bukan nol."""
    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_ubah_stop(sasaran=None, stop=2500)
    assert "pilih satu posisi" in str(galat.value)

    sasaran = _posisi_terbuka(siap)
    for salah in (None, 0, -1):
        with pytest.raises(tulis.GalatTulis) as galat_nilai:
            tulis.permintaan_ubah_stop(sasaran=sasaran, stop=salah)
        assert "lebih dari nol" in str(galat_nilai.value)


def test_ubah_stop_dari_jendela_sama_dengan_baris_perintah(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Baris `posisi` dari jendela = baris dari `--ubah-stop`, termasuk `tgl_stop`-nya."""
    basis = _dua_basis(tmp_path, monkeypatch)
    try:
        for sambungan in basis.values():
            _posisi_terbuka(sambungan)

        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "perintah"))
        kode_keluar = cli.main(
            [
                "--ubah-stop",
                "--id-posisi", "1",
                "--stop", "2500",
                "--tanggal", "2026-07-03",
                "--alasan", "naikkan stop",
            ]
        )
        assert kode_keluar == cli.KODE_OK

        sasaran = posisi.wajib_ada(basis["jendela"], 1)
        permintaan = tulis.permintaan_ubah_stop(
            sasaran=sasaran, stop=2500, alasan="naikkan stop", tanggal=date(2026, 7, 3)
        )
        hasil = tulis.jalankan_permintaan(permintaan, basis["jendela"])

        assert hasil.berhasil, hasil.pesan
        assert "2.500" in hasil.pesan
        assert _baris(basis["perintah"], "v_posisi_terkini") == _baris(
            basis["jendela"], "v_posisi_terkini"
        )
        # `tgl_stop` = tanggal yang dinyatakan pengguna; revisinya bertambah, bukan menimpa.
        assert (
            basis["jendela"]
            .execute("SELECT tgl_stop FROM posisi WHERE revisi = 2")
            .fetchone()[0]
            == "2026-07-03"
        )
    finally:
        for sambungan in basis.values():
            sambungan.close()


def test_ubah_stop_yang_diturunkan_tercatat_v5_bukan_ditolak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Menurunkan stop boleh, tetapi jejaknya wajib ada — dan barisnya sama dengan CLI."""
    basis = _dua_basis(tmp_path, monkeypatch)
    try:
        for sambungan in basis.values():
            _posisi_terbuka(sambungan)

        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "perintah"))
        assert cli.main(
            [
                "--ubah-stop",
                "--id-posisi", "1",
                "--stop", "2100",
                "--tanggal", "2026-07-04",
                "--alasan", "menurunkan stop",
            ]
        ) == cli.KODE_OK

        sasaran = posisi.wajib_ada(basis["jendela"], 1)
        permintaan = tulis.permintaan_ubah_stop(
            sasaran=sasaran, stop=2100, alasan="menurunkan stop", tanggal=date(2026, 7, 4)
        )
        hasil = tulis.jalankan_permintaan(permintaan, basis["jendela"])

        assert hasil.berhasil, hasil.pesan
        assert "V5" in hasil.pesan
        assert "V5" in basis["jendela"].execute(
            "SELECT pelanggaran FROM v_posisi_terkini"
        ).fetchone()[0]
        assert _baris(basis["perintah"], "v_posisi_terkini") == _baris(
            basis["jendela"], "v_posisi_terkini"
        )
    finally:
        for sambungan in basis.values():
            sambungan.close()


def test_ringkasan_keputusan_right_issue_menyebut_haknya_petunjuk(siap: sqlite3.Connection) -> None:
    """Hak right issue adalah **petunjuk** (rasio × lembar), dan itu dikatakan di konfirmasi."""
    _posisi_terbuka(siap)
    _simpan_right_issue(siap)
    hak = _hak_tunggal(siap)
    assert hak.lembar_hak == 80  # 200 lembar × rasio 2:5
    assert hak.sudah_diputuskan is False

    permintaan = tulis.permintaan_keputusan_right_issue(
        hak=hak, keputusan="jual_hmetd", lembar=80, harga=150, biaya=1_000, catatan="jual hak"
    )

    assert permintaan.judul == f"Putuskan right issue {KODE} 2026-07-10"
    assert "jual_hmetd" in permintaan.ringkasan
    assert "80 lbr" in permintaan.ringkasan
    assert tulis.CATATAN_HAK_PETUNJUK in permintaan.ringkasan
    assert hak.ringkas(dengan_keputusan=False) in permintaan.ringkasan
    # K31: hak yang bukan kelipatan lot disebut lebih awal, bukan saat transaksinya ditolak.
    assert hak.catatan_lot() is not None
    assert hak.catatan_lot() in permintaan.ringkasan


def test_keputusan_right_issue_jual_dari_jendela_sama_dengan_baris_perintah(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Baris `keputusan_right_issue` dari jendela = baris dari `--putuskan-right-issue`."""
    basis = _dua_basis(tmp_path, monkeypatch)
    try:
        for sambungan in basis.values():
            _posisi_terbuka(sambungan)
            _simpan_right_issue(sambungan)

        monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "perintah"))
        assert cli.main(
            [
                "--putuskan-right-issue", KODE,
                "--tanggal-aksi", TGL_RIGHT_ISSUE.isoformat(),
                "--keputusan", "jual_hmetd",
                "--lembar", "80",
                "--harga", "150",
                "--biaya", "1000",
                "--alasan", "jual hak",
            ]
        ) == cli.KODE_OK

        hak = _hak_tunggal(basis["jendela"])
        permintaan = tulis.permintaan_keputusan_right_issue(
            hak=hak, keputusan="jual_hmetd", lembar=80, harga=150, biaya=1_000, catatan="jual hak"
        )
        hasil = tulis.jalankan_permintaan(permintaan, basis["jendela"])

        assert hasil.berhasil, hasil.pesan
        assert "jual_hmetd" in hasil.pesan
        assert tulis.CATATAN_KEPUTUSAN_REVISI in hasil.pesan
        assert _baris(basis["perintah"], "v_keputusan_right_issue_terkini") == _baris(
            basis["jendela"], "v_keputusan_right_issue_terkini"
        )
    finally:
        for sambungan in basis.values():
            sambungan.close()


def test_tebus_dari_jendela_menunjuk_transaksi_yang_sudah_tercatat(siap: sqlite3.Connection) -> None:
    """T51: `tebus` menunjuk transaksi yang ada — jendela tidak mencatatkannya diam-diam."""
    _posisi_terbuka(siap)
    _simpan_right_issue(siap)
    hak = _hak_tunggal(siap)

    with pytest.raises(tulis.GalatTulis) as galat:
        tulis.permintaan_keputusan_right_issue(hak=hak, keputusan="tebus")
    assert "TIDAK mencatatkan transaksinya diam-diam" in str(galat.value)

    beli = posisi.catat_transaksi(
        siap,
        KODE,
        "beli",
        harga=CLOSE,
        lembar=100,
        mode="nyata",
        tanggal=date(2026, 7, 12),
        id_posisi=1,
    )
    jumlah_transaksi = siap.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0]

    permintaan = tulis.permintaan_keputusan_right_issue(
        hak=hak,
        keputusan="tebus",
        id_transaksi=beli.transaksi.id_transaksi,
        ringkas_transaksi=beli.transaksi.ringkas(),
    )
    assert tulis.CATATAN_TEBUS_MENUNJUK_TRANSAKSI in permintaan.ringkasan
    hasil = tulis.jalankan_permintaan(permintaan, siap)

    assert hasil.berhasil, hasil.pesan
    assert f"lewat transaksi #{beli.transaksi.id_transaksi}" in hasil.pesan
    # Yang bertambah hanya baris keputusan: transaksinya tidak dibuat ulang oleh jendela.
    assert siap.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0] == jumlah_transaksi
    assert siap.execute("SELECT COUNT(*) FROM keputusan_right_issue").fetchone()[0] == 1


def test_keputusan_right_issue_menolak_isian_yang_tidak_dipakai(siap: sqlite3.Connection) -> None:
    """Isian yang tidak dipakai keputusan ditolak berisik — **tidak** dibuang diam-diam."""
    _posisi_terbuka(siap)
    _simpan_right_issue(siap)
    hak = _hak_tunggal(siap)

    with pytest.raises(tulis.GalatTulis) as galat_abaikan:
        tulis.permintaan_keputusan_right_issue(hak=hak, keputusan="abaikan", lembar=80, harga=150)
    assert "tidak memakai lembar/harga/biaya" in str(galat_abaikan.value)

    # `tebus` pun tidak memakainya; jendela menolaknya lebih dulu, dan sejak K71 inti juga
    # menolak (bukan membuang diam-diam).
    with pytest.raises(tulis.GalatTulis) as galat_tebus:
        tulis.permintaan_keputusan_right_issue(hak=hak, keputusan="tebus", id_transaksi=1, lembar=80)
    assert "tebus" in str(galat_tebus.value)

    with pytest.raises(tulis.GalatTulis):
        tulis.permintaan_keputusan_right_issue(hak=hak, keputusan="jual_hmetd", lembar=80)
    with pytest.raises(tulis.GalatTulis):
        tulis.permintaan_keputusan_right_issue(hak=hak, keputusan="abaikan", id_transaksi=1)
    with pytest.raises(tulis.GalatTulis) as galat_kenal:
        tulis.permintaan_keputusan_right_issue(hak=hak, keputusan="tebus_aja")
    assert "tidak dikenal" in str(galat_kenal.value)
