"""Uji penurunan `jenis` emiten dari sector/industry sumber data (K21), **tanpa jaringan**.

Yang dijaga berkas ini bukan "apakah turunannya jalan", melainkan tiga batas yang membuat K21
boleh dipakai sama sekali:

* **Hanya `bank_keuangan` yang diturunkan.** `siklikal_komoditas` tidak pernah muncul dari
  turunan — ia penilaian analis, dan tidak satu pun sumber data menyatakannya. Sektor
  `Basic Materials` (yang secara intuisi "siklikal") harus tetap menjadi `umum`.
* **"Tidak dinyatakan" berbeda dari `umum`.** Sumber yang tidak menyatakan sector maupun
  industry tidak menghasilkan baris ber-`umum`; kolomnya dibiarkan kosong, dan itu keadaan
  yang sah.
* **`jenis` yang sudah diisi tidak ditimpa**; perubahan isi menambah revisi di basis data,
  sedangkan tanggal provenance `dicatat_pada` saja tidak membuat revisi baru.

Semua data di sini palsu dengan sengaja: uji ini tidak boleh menyentuh yfinance, sebab jalur
jaringan tidak boleh menjadi syarat bagi aturan yang harus tetap benar bertahun-tahun.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import berkas, cli, db, jenis, lokasi, pengambil

DIAMBIL = date(2026, 10, 10)

#: Jawaban palsu sumber data: kode → (sector, industry). Kode yang tidak ada di sini berarti
#: sumber tidak menyatakan sector maupun industry — keadaan yang sah, bukan kegagalan.
SECTOR_PALSU: Mapping[str, tuple[str | None, str | None]] = {
    "BBRI": ("Financial Services", "Banks - Regional"),
    "BMRI": ("Financial Services", "Banks - Regional"),
    "BBCA": ("Financial Services", "Banks - Diversified"),
    "BBNI": ("Financial Services", "Banks - Regional"),
    "BRIS": ("Financial Services", "Banks - Regional"),
    "ASII": ("Consumer Cyclical", "Auto Manufacturers"),
    # Jasa keuangan BUKAN bank: asuransi, manajer investasi, pasar modal. Ketiganya harus
    # menjadi `umum` — PRD 8.4 hanya menyediakan set kriteria bank untuk bank.
    "ASBI": ("Financial Services", "Insurance"),
    "ARTO": ("Financial Services", "Asset Management"),
    "PANS": ("Financial Services", "Capital Markets"),
    # Sektor yang secara intuisi "siklikal" tetap `umum`: K21 melarang menurunkannya.
    "ANTM": ("Basic Materials", "Gold"),
    "PTBA": ("Energy", "Thermal Coal"),
    "GOTO": ("Technology", "Software - Application"),
    # Sumber hanya menyatakan salah satu; `umum` tetap keluar karena ada yang dinyatakan.
    "TLKM": ("Communication Services", None),
    "UNVR": (None, "Household & Personal Products"),
}

#: Kode yang **dijawab sumber tanpa sector/industry** (mis. `info` kosong) — dibedakan dari
#: kode yang tidak ada di `SECTOR_PALSU` supaya dua jalur "tidak dinyatakan" ikut teruji.
TANPA_SECTOR_KARENA_KOSONG = ("MAMIP",)

#: Kode yang pengambilannya gagal; barisnya tetap ditulis dengan `jenis` kosong.
GAGAL_DIAMBIL = {"KREN": "TimeoutError: sumber tidak menjawab"}


@pytest.fixture()
def folder_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "data"
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(folder))
    return folder


@pytest.fixture(autouse=True)
def waktu_ingesti_bertambah(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Berikan waktu deterministik yang berbeda untuk impor berurutan dalam satu detik.

    Timestamp produksi tetap memakai presisi detik. Tes integrasi sering menjalankan dua impor
    langsung berurutan; membiarkan jam nyata memilih apakah keduanya bertabrakan akan membuat
    hasil tes bergantung pada kecepatan mesin.
    """
    from mejasaham import ingesti

    awal = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    berikutnya = awal

    def waktu(momen: datetime | None = None) -> str:
        nonlocal berikutnya
        if momen is not None:
            return db.waktu_iso(momen)
        saat = berikutnya
        berikutnya += timedelta(seconds=1)
        return db.waktu_iso(saat)

    monkeypatch.setattr(ingesti, "_waktu_iso", waktu)
    return awal


@pytest.fixture()
def sambungan(folder_data: Path) -> Iterator[sqlite3.Connection]:
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _sector_palsu(kode: str, *, jeda: float = 0.0, percobaan: int = 3) -> pengambil.HasilSector:
    """Pengganti `pengambil.sector_emiten` — mematuhi kontraknya, tanpa menyentuh jaringan.

    `jeda` dan `percobaan` diterima supaya tanda tangannya tetap cocok: kalau pemanggil berhenti
    menghormati jeda penyedia, uji ini tidak akan menangkapnya — dan itu memang bukan yang diuji
    di sini (yang diuji adalah aturan turunannya).
    """
    assert jeda >= 0 and percobaan >= 1
    if kode in GAGAL_DIAMBIL:
        return pengambil.HasilSector(kode=kode, gagal=GAGAL_DIAMBIL[kode])
    if kode in TANPA_SECTOR_KARENA_KOSONG:
        return pengambil.HasilSector(kode=kode)
    if kode not in SECTOR_PALSU:
        return pengambil.HasilSector(kode=kode)
    sector, industry = SECTOR_PALSU[kode]
    return pengambil.HasilSector(kode=kode, sector=sector, industry=industry)


@pytest.fixture()
def tanpa_jaringan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ganti seluruh pengambilan sector dengan data palsu — yfinance tidak boleh dipanggil."""
    monkeypatch.setattr(pengambil, "sector_emiten", _sector_palsu)


def _tulis_emiten_awal(folder: Path, baris: list[tuple[str, str, str]]) -> Path:
    """Tulis `emiten.csv` rujukan berisi (kode, nama, jenis) — `jenis` kosong bila belum ada.

    Selnya disusun dari `berkas.SPESIFIKASI["emiten"]`, bukan dari string yang diketik tangan:
    berkas uji yang kolomnya salah jumlah akan gagal di tempat yang salah, dan pesannya menunjuk
    kolom yang tidak berhubungan.

    `folder` adalah **folder konfigurasi**, tempat yang sama dengan yang dipakai `--ambil-jenis`
    dan `--impor` — bukan folder data.
    """
    folder.mkdir(parents=True, exist_ok=True)
    kolom = berkas.SPESIFIKASI["emiten"].nama_kolom
    isi = [";".join(kolom)]
    for kode, nama, jenis_awal in baris:
        sel = {
            "kode": kode,
            "nama": nama,
            "jenis": jenis_awal,
            "sumber": "Daftar uji (diakses 9 Okt 2026)",
            "dicatat_pada": "2026-10-09",
        }
        isi.append(";".join(sel.get(satu, "") for satu in kolom))
    jalur = folder / "emiten.csv"
    jalur.write_text("\n".join(isi) + "\n", encoding="utf-8")
    return jalur


def _konfigurasi() -> Path:
    return lokasi.folder_konfigurasi()


def _impor_awal(sambungan: sqlite3.Connection, baris: list[tuple[str, str, str]]) -> None:
    """Masukkan baris rujukan awal ke basis data lewat pembaca impor yang sebenarnya.

    Berkasnya **ditinggal** di folder konfigurasi, persis seperti sesudah `--impor` yang biasa:
    karena itu uji yang menjalankan `--ambil-jenis` sesudahnya memakai `--timpa-jenis`. Itu juga
    keadaan nyata ketika seseorang hendak memperbarui `jenis` untuk emiten yang baru masuk.
    """
    folder = _konfigurasi()
    _tulis_emiten_awal(folder, baris)
    from mejasaham import pengatur

    hasil = pengatur.jalankan_impor(sambungan, folder)
    assert hasil.sukses, hasil.pesan


# --- aturan turunan: fungsi murni, tanpa berkas dan tanpa basis data ----------------------


@pytest.mark.parametrize(
    ("sector", "industry", "diharapkan"),
    [
        ("Financial Services", "Banks - Regional", "bank_keuangan"),
        ("Financial Services", "Banks - Diversified", "bank_keuangan"),
        ("Financial Services", "Banks", "bank_keuangan"),
        ("financial services", "banks - regional", "bank_keuangan"),
        ("  Financial   Services ", "  Banks  -  Regional  ", "bank_keuangan"),
        ("Financial Services", "Insurance", "umum"),
        ("Financial Services", "Asset Management", "umum"),
        ("Financial Services", "Capital Markets", "umum"),
        # Sector jasa keuangan tanpa industry bank tidak cukup: dua-duanya disyaratkan.
        ("Financial Services", None, "umum"),
        # Industry bank tanpa sector jasa keuangan = label sumber tidak konsisten; jangan dipakai.
        ("Technology", "Banks - Regional", "umum"),
        ("Basic Materials", "Gold", "umum"),
        ("Energy", "Thermal Coal", "umum"),
        # "Tidak dinyatakan" bukan `umum`.
        (None, None, None),
        ("", "", None),
        ("   ", None, None),
        (None, "  ", None),
    ],
)
def test_aturan_turunan(sector: object, industry: object, diharapkan: str | None) -> None:
    assert jenis.jenis_dari_sumber(sector, industry) == diharapkan


def test_siklikal_komoditas_tidak_pernah_diturunkan() -> None:
    """K21 batas (b): "emiten ini siklikal" adalah penilaian, bukan fakta yang dinyatakan sumber.

    Uji ini yang menjaganya: kalau seseorang menambahkan `Basic Materials`/`Energy` ke daftar
    turunan "karena jelas siklikal", uji ini gagal. Sektor komoditas harus tetap `umum`, dan
    `siklikal_komoditas` hanya boleh datang dari isian manusia.
    """
    sektor_komoditas = [
        ("Basic Materials", "Gold"),
        ("Basic Materials", "Specialty Chemicals"),
        ("Energy", "Thermal Coal"),
        ("Energy", "Oil & Gas Integrated"),
        ("Consumer Defensive", "Farm Products"),
    ]

    for sector, industry in sektor_komoditas:
        assert jenis.jenis_dari_sumber(sector, industry) == "umum"
        assert jenis.jenis_dari_sumber(sector, industry) != "siklikal_komoditas"
    assert "siklikal_komoditas" not in jenis.JENIS_DITURUNKAN


def test_daftar_nilai_sah_dipinjam_dari_pemiliknya() -> None:
    """Satu fakta satu tempat: daftar nilai sah hidup di `ingesti`, bukan disalin (aturan 5)."""
    from mejasaham import ingesti

    assert jenis.nilai_sah_dikenal() == ("bank_keuangan", "siklikal_komoditas", "umum")
    assert jenis.nilai_sah_dikenal() == tuple(
        sorted({satu for satu in ingesti.JENIS_EMITEN.values() if satu})
    )
    assert jenis.JENIS_EMITEN is ingesti.JENIS_EMITEN


def test_penjelasan_menyebut_label_mentah_sumbernya() -> None:
    """K21 batas (a): label sumber ikut tersimpan di kolom `sumber` tiap baris."""
    penjelasan = jenis.penjelasan_jenis("bank_keuangan", "Financial Services", "Banks - Regional")

    assert "Financial Services" in penjelasan
    assert "Banks - Regional" in penjelasan
    assert "TIDAK RESMI" in penjelasan

    kosong = jenis.penjelasan_jenis(None, None, None)

    assert "(tidak dinyatakan)" in kosong
    assert "TIDAK diturunkan" in kosong


# --- jalur lengkap: basis data → turunan → berkas → dibaca ulang → diimpor -----------------


def _siapkan(sambungan: sqlite3.Connection) -> None:
    _impor_awal(
        sambungan,
        [
            ("BBRI", "Bank Rakyat Indonesia", ""),
            ("BMRI", "Bank Mandiri", ""),
            ("BBCA", "Bank Central Asia", ""),
            ("BBNI", "Bank Negara Indonesia", ""),
            ("ASBI", "Asuransi Bina", ""),
            ("ANTM", "Aneka Tambang", ""),
            ("TLKM", "Telkom", ""),
            ("MAMIP", "Emiten Tanpa Sector", ""),
            ("KREN", "Emiten Gagal Diambil", ""),
        ],
    )


def test_ambil_jenis_menulis_berkas_yang_terbaca_pembaca_impor(
    sambungan: sqlite3.Connection, tanpa_jaringan: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """Jalur penuh: yang ditulis harus terbaca oleh pembaca yang sama dengan `--impor`."""
    _siapkan(sambungan)
    sambungan.close()

    kode = cli.main(["--ambil-jenis", "--timpa-jenis"])

    assert kode == cli.KODE_OK
    keluaran = capsys.readouterr()
    assert "bank_keuangan 4" in keluaran.out
    assert "BBRI" in keluaran.out, "kode bank yang dikenal harus ditunjukkan sebagai bukti"

    terbaca = berkas.baca_emiten(_konfigurasi())
    per_kode = {satu.kode: satu for satu in terbaca}

    assert per_kode["BBRI"].jenis == "bank_keuangan"
    assert per_kode["BMRI"].jenis == "bank_keuangan"
    assert per_kode["BBCA"].jenis == "bank_keuangan"
    assert per_kode["BBNI"].jenis == "bank_keuangan"
    assert per_kode["ASBI"].jenis == "umum", "asuransi bukan bank (PRD 8.4)"
    assert per_kode["ANTM"].jenis == "umum", "siklikal tidak diturunkan (K21)"
    assert per_kode["TLKM"].jenis == "umum", "sumber menyatakan sector, jadi bukan 'tidak dinyatakan'"
    assert per_kode["MAMIP"].jenis is None, "sumber tidak menyatakan sector/industry"
    assert per_kode["KREN"].jenis is None, "pengambilan gagal: kolom dibiarkan kosong, bukan diisi tebakan"
    assert per_kode["BBRI"].dicatat_pada == date.today(), (
        "dicatat_pada menyimpan tanggal provenance pengambilan"
    )


def test_ambil_jenis_menulis_sektor_sumber_bukan_idx_ic(
    sambungan: sqlite3.Connection, tanpa_jaringan: None
) -> None:
    """K25: sektor sumber ditulis di kolomnya **sendiri**, dan `sektor_idx_ic` tetap kosong.

    Dua kolom itu berbeda, dan menaruh taksonomi sumber di `sektor_idx_ic` akan membuat batas
    bobot per sektor (PRD 9.7) menghitung kelompok yang bukan kelompoknya — tanpa satu pun galat.
    """
    _siapkan(sambungan)
    sambungan.close()

    assert cli.main(["--ambil-jenis", "--timpa-jenis"]) == cli.KODE_OK

    per_kode = {satu.kode: satu for satu in berkas.baca_emiten(_konfigurasi())}

    assert per_kode["BBRI"].sektor_sumber == "Financial Services"
    assert per_kode["ANTM"].sektor_sumber == "Basic Materials"
    assert per_kode["BBRI"].sektor_idx_ic is None, "IDX-IC tidak diturunkan dari sumber (K12)"
    assert per_kode["KREN"].sektor_sumber is None, "pengambilan gagal: kolom dibiarkan kosong"
    assert per_kode["MAMIP"].sektor_sumber is None, "sumber tidak menyatakan sektornya"

    # Dan yang tertulis itu benar-benar masuk basis data lewat jalur impor yang sama.
    assert cli.main(["--impor", str(_konfigurasi())]) == cli.KODE_OK
    periksa = db.siapkan()
    try:
        terbaca = jenis.emiten_tersimpan(periksa, ["BBRI", "ANTM"])
    finally:
        periksa.close()
    assert {satu.kode: satu.sektor_sumber for satu in terbaca} == {
        "BBRI": "Financial Services",
        "ANTM": "Basic Materials",
    }


def test_kolom_jenis_yang_sudah_diisi_tidak_ditimpa(
    sambungan: sqlite3.Connection, tanpa_jaringan: None
) -> None:
    """K21 batas (b) + isian tangan: `siklikal_komoditas` tidak boleh hilang ditimpa turunan.

    Ini yang paling mudah rusak tanpa terlihat: turunan otomatis yang menimpa isian manusia akan
    menghapus satu-satunya nilai yang **tidak bisa** dihasilkan mesin.
    """
    _impor_awal(
        sambungan,
        [
            ("BBRI", "Bank Rakyat Indonesia", "bank_keuangan"),
            ("ANTM", "Aneka Tambang", "siklikal_komoditas"),
            ("ASII", "Astra International", ""),
        ],
    )
    sambungan.close()

    kode = cli.main(["--ambil-jenis", "--timpa-jenis"])

    assert kode == cli.KODE_OK
    per_kode = {satu.kode: satu for satu in berkas.baca_emiten(_konfigurasi())}

    assert per_kode["ANTM"].jenis == "siklikal_komoditas", "isian manusia tidak boleh ditimpa"
    assert per_kode["BBRI"].jenis == "bank_keuangan"
    assert per_kode["ASII"].jenis == "umum", "yang kosong tetap diturunkan"


def test_berkas_yang_sudah_ada_ditolak_tanpa_timpa_jenis(
    sambungan: sqlite3.Connection, tanpa_jaringan: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """`emiten.csv` adalah semesta milik pengguna; menimpanya harus diminta tegas."""
    _siapkan(sambungan)
    tujuan = _konfigurasi() / "emiten.csv"
    sebelum = tujuan.read_text(encoding="utf-8")
    sambungan.close()

    kode = cli.main(["--ambil-jenis"])

    assert kode == cli.KODE_GAGAL
    assert "--timpa-jenis" in capsys.readouterr().err
    assert tujuan.read_text(encoding="utf-8") == sebelum, "berkasnya tidak boleh tersentuh"


def test_berkas_template_boleh_ditimpa_tanpa_timpa_jenis(
    sambungan: sqlite3.Connection, tanpa_jaringan: None
) -> None:
    """Template AC-12 belum memuat satu baris data pun, jadi menulisnya bukan menimpa pekerjaan."""
    _siapkan(sambungan)
    sambungan.close()
    tujuan = _konfigurasi() / "emiten.csv"
    kolom = berkas.SPESIFIKASI["emiten"].nama_kolom
    tujuan.write_text(";".join(kolom) + "\n# belum ada isinya\n", encoding="utf-8")

    kode = cli.main(["--ambil-jenis"])

    assert kode == cli.KODE_OK
    assert len(berkas.baca_emiten(_konfigurasi())) == 9


def test_berkas_separuh_tidak_ditinggalkan(
    sambungan: sqlite3.Connection, tanpa_jaringan: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Berkas ditulis lewat berkas sementara lalu diganti: gagal di tengah ≠ berkas separuh.

    Berkas separuh jadi adalah **semesta yang salah**, bukan berkas yang rusak — ia akan terbaca
    sebagai daftar emiten yang lebih pendek tanpa satu pun tanda bahwa ada yang hilang.
    """
    _siapkan(sambungan)
    sambungan.close()
    tujuan = _konfigurasi() / "emiten.csv"
    tujuan.unlink()

    def gagal_ganti(*_args: object, **_kwargs: object) -> None:
        raise OSError("gagal disengaja saat mengganti berkas")

    monkeypatch.setattr(jenis.os, "replace", gagal_ganti)

    with pytest.raises(OSError, match="gagal disengaja"):
        jenis.tulis_emiten_csv(
            [
                jenis.BarisJenis(
                    tersimpan=jenis.EmitenTersimpan(
                        kode="BBRI",
                        nama="Bank Rakyat Indonesia",
                        sektor_idx_ic=None,
                        sektor_sumber=None,
                        jenis=None,
                        papan=None,
                        status_notasi=None,
                        tanggal_notasi=None,
                        jumlah_saham=None,
                        sumber="uji",
                    ),
                    sector="Financial Services",
                    industry="Banks - Regional",
                    jenis="bank_keuangan",
                )
            ],
            tujuan,
            diambil_pada=DIAMBIL,
        )

    assert not tujuan.exists(), "berkas separuh jadi tidak boleh tertinggal"
    sisa = sorted(satu.name for satu in tujuan.parent.glob("emiten.csv.tmp-*"))
    assert sisa == [], f"berkas sementara tertinggal: {sisa}"


def test_impor_emiten_memakai_waktu_ingesti_bukan_tanggal_catat(
    sambungan: sqlite3.Connection,
    tanpa_jaringan: None,
    waktu_ingesti_bertambah: datetime,
) -> None:
    """Waktu pengetahuan DB berasal dari impor; tanggal provenance tetap terbaca di CSV."""
    _siapkan(sambungan)
    sambungan.close()
    from mejasaham import pengatur

    def _revisi_terkini() -> tuple[int, sqlite3.Row]:
        koneksi = db.siapkan()
        try:
            assert pengatur.jalankan_impor(koneksi, _konfigurasi()).sukses
            jumlah = koneksi.execute(
                "SELECT COUNT(*) FROM emiten WHERE kode = 'BBRI'"
            ).fetchone()[0]
            return jumlah, koneksi.execute(
                "SELECT jenis, diketahui_pada FROM v_emiten_terkini WHERE kode = 'BBRI'"
            ).fetchone()
        finally:
            koneksi.close()

    assert cli.main(["--ambil-jenis", "--timpa-jenis"]) == cli.KODE_OK
    jumlah, terkini = _revisi_terkini()

    assert jumlah == 2, "isi jenis yang berubah menambah revisi append-only"
    assert terkini["jenis"] == "bank_keuangan"
    assert terkini["diketahui_pada"] == db.waktu_iso(waktu_ingesti_bertambah + timedelta(seconds=1))
    # Provenance tanggal sumber tetap ada di CSV, terpisah dari waktu impor DB.
    baris_csv = {satu.kode: satu for satu in berkas.baca_emiten(_konfigurasi())}
    assert baris_csv["BBRI"].dicatat_pada == date.today()


def test_sumber_per_baris_memuat_sumber_lama_dan_keterangan_turunan(
    sambungan: sqlite3.Connection, tanpa_jaringan: None
) -> None:
    """Sumber aslinya diteruskan, bukan diganti: tanpa itu asal `nama`/`jumlah_saham` hilang."""
    _siapkan(sambungan)
    sambungan.close()

    assert cli.main(["--ambil-jenis", "--timpa-jenis"]) == cli.KODE_OK
    per_kode = {satu.kode: satu for satu in berkas.baca_emiten(_konfigurasi())}

    sumber = per_kode["BBRI"].sumber
    assert "Daftar uji (diakses 9 Okt 2026)" in sumber
    assert "Financial Services" in sumber and "Banks - Regional" in sumber
    assert "TIDAK RESMI" in sumber


def test_tabel_emiten_kosong_ditolak_berisik(
    sambungan: sqlite3.Connection, tanpa_jaringan: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """Tanpa satu pun emiten di basis data, tidak ada yang bisa diturunkan — dan itu dikatakan."""
    sambungan.close()

    kode = cli.main(["--ambil-jenis"])

    assert kode == cli.KODE_GAGAL
    assert "masih kosong" in capsys.readouterr().err


# --- laporan --saring: tiga keadaan dibedakan (K21 batas (c)) ------------------------------


@pytest.mark.parametrize(
    ("jenis_per_kode", "diharapkan"),
    [
        (
            {"BBRI": "bank_keuangan", "BMRI": "bank_keuangan", "ASII": "umum"},
            ["2 bank_keuangan", "1 umum", "0 siklikal_komoditas", "0 belum terisi"],
        ),
        (
            {"ASII": "umum", "TLKM": "umum"},
            ["0 bank_keuangan", "2 umum", "0 belum terisi"],
        ),
        (
            {"BBRI": "bank_keuangan", "ANTM": "siklikal_komoditas", "XX": None},
            ["1 bank_keuangan", "0 umum", "1 siklikal_komoditas", "1 belum terisi"],
        ),
    ],
)
def test_keadaan_jenis_membedakan_tiga_keadaan(
    jenis_per_kode: Mapping[str, str | None], diharapkan: list[str]
) -> None:
    """Satu angka "belum terisi" menyembunyikan bagian yang sudah bekerja (K21 batas (c))."""
    keadaan = jenis.KeadaanJenis.dari(jenis_per_kode)

    ringkas = keadaan.ringkas()
    for potongan in diharapkan:
        assert potongan in ringkas, ringkas
    assert keadaan.total == len(jenis_per_kode)


def test_peringatan_hilang_hanya_bila_tidak_ada_yang_kosong() -> None:
    """Peringatan yang selalu berbunyi berhenti memberi informasi."""
    semua_terisi = jenis.KeadaanJenis.dari({"BBRI": "bank_keuangan", "ASII": "umum"})
    ada_yang_kosong = jenis.KeadaanJenis.dari({"BBRI": "bank_keuangan", "XX": None})

    assert semua_terisi.peringatan() is None
    peringatan = ada_yang_kosong.peringatan()
    assert peringatan is not None
    assert "belum terisi untuk 1 emiten" in peringatan
    assert "1 bank_keuangan" in peringatan, "peringatan menyebut juga yang sudah terisi"


def test_keadaan_jenis_selalu_tampil_di_ringkasan_saring() -> None:
    """Keadaan `jenis` dibawa sampai laporan, bukan hanya jadi peringatan saat ada yang kosong.

    Yang berubah ketika kolomnya terisi adalah **aturan yang berlaku** (kriteria bank mulai
    diterapkan), jadi keadaannya harus terbaca walaupun seluruh emiten sudah ber-jenis.
    """
    from mejasaham import pengatur

    laporan = pengatur.LaporanSaring(
        id_snapshot=1,
        tanggal_data="2026-10-09",
        id_preset="kualitas-nilai/v1",
        jumlah_emiten=2,
        jumlah_likuid=2,
        jumlah_lolos=2,
        jumlah_dinilai=2,
        jumlah_tidak_bisa_dinilai=0,
        breadth=None,
        rezim="netral",
        keadaan_jenis=jenis.KeadaanJenis.dari({"BBRI": "bank_keuangan", "ASII": "umum"}),
    )

    ringkas = laporan.ringkas()

    assert "1 bank_keuangan (dari data)" in ringkas
    assert "1 umum (dari data)" in ringkas
    assert "0 belum terisi" in ringkas
    assert "DER/coverage/CFO-NI TIDAK dihitung" in ringkas


# --- kerangka rasio-bank.csv dari daftar bank (K57, T67) ----------------------------------


def _siapkan_dengan_jenis(sambungan: sqlite3.Connection) -> tuple[str, ...]:
    """Basis data yang `jenis`-nya sudah diturunkan **dan diimpor** — syarat aksi #21.

    Kembalikan kode banknya, supaya uji bisa membandingkan kerangka dengan daftar yang sama.
    """
    from mejasaham import pengatur

    _siapkan(sambungan)
    assert cli.main(["--ambil-jenis", "--timpa-jenis"]) == cli.KODE_OK
    hasil = pengatur.jalankan_impor(sambungan, _konfigurasi())
    assert hasil.sukses, hasil.pesan
    return jenis.kode_bank(sambungan)


def _baris_data(jalur: Path) -> tuple[list[str], list[list[str]]]:
    """(kepala, baris data) dari berkas CSV yang memuat baris penjelasan `#`."""
    baris = [
        satu
        for satu in jalur.read_text(encoding="utf-8").splitlines()
        if satu.strip() and not satu.startswith("#")
    ]
    return baris[0].split(";"), [satu.split(";") for satu in baris[1:]]


def test_kerangka_rasio_bank_berisi_kode_bank_dan_selain_kode_kosong(
    sambungan: sqlite3.Connection, tanpa_jaringan: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """K57/T67: satu baris per kode bank, **seluruh** angka & tanggal dikosongkan.

    Bentuk kolomnya harus sama dengan template bawaan — kalau kerangka punya kolom sendiri, satu
    dari dua bentuk itu akan ketinggalan begitu template berubah.
    """
    bank = _siapkan_dengan_jenis(sambungan)
    assert bank == ("BBCA", "BBNI", "BBRI", "BMRI"), "yang ber-jenis bank dari data K21"

    kode = cli.main(["--kerangka-rasio-bank"])
    keluaran = capsys.readouterr()

    assert kode == cli.KODE_OK, keluaran.err
    tujuan = _konfigurasi() / berkas.NAMA_RASIO_BANK
    assert tujuan.exists()
    kepala, data = _baris_data(tujuan)

    assert tuple(kepala) == berkas.SPESIFIKASI["rasio_bank"].nama_kolom
    assert [satu[0] for satu in data] == list(bank)
    for sel in data:
        for nama, isi in zip(kepala, sel):
            if nama != "kode":
                assert isi == "", f"{sel[0]} · {nama} harus kosong di kerangka, bukan {isi!r}"
    assert "DIKOSONGKAN" in tujuan.read_text(encoding="utf-8"), (
        "berkas kosong tanpa penjelasan akan terbaca sebagai 'tidak ada rasio bank di Indonesia'"
    )
    assert sambungan.execute("SELECT COUNT(*) FROM rasio_bank").fetchone()[0] == 0, (
        "perintah ini menulis berkas rujukan, bukan basis data"
    )


def test_kerangka_rasio_bank_ditolak_bila_belum_ada_bank(
    sambungan: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """Tanpa `jenis` terisi: melaporkan jalan keluarnya, bukan menulis kerangka kosong."""
    _siapkan(sambungan)  # `jenis` sengaja dibiarkan kosong: belum --ambil-jenis/--impor

    kode = cli.main(["--kerangka-rasio-bank"])
    keluaran = capsys.readouterr()

    assert kode == cli.KODE_GAGAL
    assert "--ambil-jenis" in keluaran.err
    assert not (_konfigurasi() / berkas.NAMA_RASIO_BANK).exists()


def test_kerangka_rasio_bank_tidak_menimpa_berkas_yang_sudah_diisi(
    sambungan: sqlite3.Connection, tanpa_jaringan: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """Berkas itu diisi manusia dari publikasi resmi — menimpanya menghapus pekerjaan."""
    _siapkan_dengan_jenis(sambungan)
    tujuan = _konfigurasi() / berkas.NAMA_RASIO_BANK
    kolom = berkas.SPESIFIKASI["rasio_bank"].nama_kolom
    isi = dict.fromkeys(kolom, "")
    isi.update(
        {
            "kode": "BBRI",
            "periode": "2026-06-30",
            "tgl_publikasi": "2026-07-25",
            "npl_kotor_persen": "2.35",
            "sumber": "Publikasi resmi bank (diakses 17 Okt 2026)",
        }
    )
    tujuan.write_text(
        ";".join(kolom) + "\n" + ";".join(isi[nama] for nama in kolom) + "\n", encoding="utf-8"
    )
    sebelum = tujuan.read_text(encoding="utf-8")

    kode = cli.main(["--kerangka-rasio-bank"])
    keluaran = capsys.readouterr()

    assert kode == cli.KODE_GAGAL
    assert "sudah ada" in keluaran.err and "pindahkan" in keluaran.err
    assert tujuan.read_text(encoding="utf-8") == sebelum


def test_kerangka_rasio_bank_boleh_menimpa_template_bawaan(
    sambungan: sqlite3.Connection, tanpa_jaringan: None
) -> None:
    """Template bawaan AC-12 bukan pekerjaan manusia: ia selalu ada sejak aplikasi dijalankan.

    Tanpa pengecualian ini, penjaganya berubah menjadi "perintah ini tidak pernah bisa dijalankan
    pada instalasi baru" — dan penjaga yang selalu berbunyi berhenti memberi informasi.
    """
    _siapkan_dengan_jenis(sambungan)
    tujuan = _konfigurasi() / berkas.NAMA_RASIO_BANK
    tujuan.write_text(
        (berkas.FOLDER_BAWAAN / "rasio-bank.contoh.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert cli.main(["--kerangka-rasio-bank"]) == cli.KODE_OK

    kepala, data = _baris_data(tujuan)
    assert tuple(kepala) == berkas.SPESIFIKASI["rasio_bank"].nama_kolom
    assert len(data) == 4, "template diganti kerangka yang berisi daftar bank"


def test_impor_kerangka_yang_belum_diisi_gagal_berisik(
    sambungan: sqlite3.Connection, tanpa_jaringan: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """Kerangka kosong **tidak** boleh masuk sebagai nol (aturan keras 2, K57/T67).

    Rasio kosong berarti "tidak dilaporkan" — dan nol di sini bukan ketidaktepatan kecil,
    melainkan bank yang tampak sehat tanpa dasar (NPL 0%, CAR 0%).
    """
    _siapkan_dengan_jenis(sambungan)
    assert cli.main(["--kerangka-rasio-bank"]) == cli.KODE_OK
    capsys.readouterr()

    kode = cli.main(["--impor", str(_konfigurasi())])
    keluaran = capsys.readouterr()

    assert kode == cli.KODE_GAGAL
    pesan = keluaran.out + keluaran.err
    assert "periode" in pesan, f"kolom wajib yang kosong harus disebut namanya: {pesan!r}"
    assert sambungan.execute("SELECT COUNT(*) FROM rasio_bank").fetchone()[0] == 0
