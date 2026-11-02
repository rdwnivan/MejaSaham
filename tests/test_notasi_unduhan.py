"""Berkas Notasi Khusus IDX yang diunduh pengguna (K96): dibaca, ditulis ke CSV, diimpor."""

from __future__ import annotations

import io
import sqlite3
import zipfile
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from mejasaham import db, ingesti, jadwal, lokasi, notasi
from mejasaham.layar import tulis

WIB = timezone(timedelta(hours=7))
HARI_INI = date(2026, 10, 29)

#: Judul kolom berkas nyata (Notasi Khusus-20261027.xlsx, diunduh pengguna 29 Okt 2026).
JUDUL = ("No", "Kode", "Nama", "Notasi", "Keterangan Notasi", "Remarks")


def _xlsx(baris: list[tuple[str, str]], judul: tuple[str, ...] = JUDUL) -> bytes:
    """XLSX berbentuk keluaran SheetJS seperti berkas IDX: teks `t="str"`, nomor sel biasa."""
    def teks(rujukan: str, nilai: str) -> str:
        return f'<c r="{rujukan}" t="str"><v>{nilai}</v></c>'

    huruf = "ABCDEF"
    isi = ["<row r=\"1\">" + "".join(teks(f"{huruf[k]}1", j) for k, j in enumerate(judul)) + "</row>"]
    for r, (kode, nota) in enumerate(baris, start=2):
        isi.append(
            f'<row r="{r}"><c r="A{r}"><v>{r - 1}</v></c>'
            + teks(f"B{r}", kode)
            + teks(f"C{r}", f"PT Emiten {kode} Tbk")
            + teks(f"D{r}", nota)
            + teks(f"E{r}", f"{nota} : keterangan")
            + teks(f"F{r}", "-----")
            + "</row>"
        )
    lembar = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(isi)}</sheetData></worksheet>"
    )
    keluaran = io.BytesIO()
    with zipfile.ZipFile(keluaran, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", lembar)
    return keluaran.getvalue()


BARIS_CONTOH = [("WEGE.M", "M"), ("CBMF.LY", "L,Y"), ("BIMA.DX", "D,X"), ("GOTOM.N", "N")]


def _berkas(tmp_path: Path, isi: bytes, nama: str = "Notasi Khusus-20261027.xlsx") -> Path:
    jalur = tmp_path / nama
    jalur.write_bytes(isi)
    return jalur


# ---------------------------------------------------------------------------------------
# Pembaca
# ---------------------------------------------------------------------------------------


def test_berkas_unduhan_menghasilkan_baris_yang_sama_dengan_halaman_notasi(tmp_path: Path) -> None:
    """Baris dari berkas unduhan identik dengan baris `urai` halaman lama, sehingga daftar yang
    sama tidak tercatat dua kali dan jadwal membaca tanggal daftarnya dengan cara yang sama."""
    halaman = "".join(f'FormatEmitenCode:"{kode}",' for kode, _ in BARIS_CONTOH) + 'Date:"2026-10-27T00:00:00"'

    hasil = notasi.baca_unduhan(_berkas(tmp_path, _xlsx(BARIS_CONTOH)), hari_ini=HARI_INI)

    assert hasil.tanggal_data == date(2026, 10, 27)
    assert hasil.baris == notasi.urai(halaman).baris
    assert hasil.kode_papan_pemantauan == ("BIMA",)
    assert "unduhan pengguna" in hasil.sumber


def test_tanggal_diambil_dari_nama_berkas_termasuk_salinan_peramban(tmp_path: Path) -> None:
    jalur = _berkas(tmp_path, _xlsx(BARIS_CONTOH), "Notasi Khusus-20261027 (1).xlsx")
    assert notasi.baca_unduhan(jalur, hari_ini=HARI_INI).tanggal_data == date(2026, 10, 27)


def test_nama_asli_dipakai_bila_berkas_tersimpan_sudah_berganti_nama(tmp_path: Path) -> None:
    jalur = _berkas(tmp_path, _xlsx(BARIS_CONTOH), "20261029T090000_berkas.xlsx")
    hasil = notasi.baca_unduhan(jalur, nama_asli="Notasi Khusus-20261027.xlsx", hari_ini=HARI_INI)
    assert hasil.tanggal_data == date(2026, 10, 27)


@pytest.mark.parametrize(
    ("nama", "isi", "sebab"),
    [
        ("notasi.xlsx", _xlsx(BARIS_CONTOH), "tanggal"),
        ("Notasi Khusus-20261131.xlsx", _xlsx(BARIS_CONTOH), "tanggal"),
        ("Notasi Khusus-20261030.xlsx", _xlsx(BARIS_CONTOH), "sesudah hari ini"),
        ("Notasi Khusus-20261027.xlsx", _xlsx(BARIS_CONTOH, judul=("No", "Kode", "Nama")), "Notasi"),
        ("Notasi Khusus-20261027.xlsx", _xlsx([]), "tidak memuat satu emiten"),
        ("Notasi Khusus-20261027.xlsx", _xlsx([("WEGE.M", "M"), ("WEGE.M", "M")]), "dua kali"),
        ("Notasi Khusus-20261027.xlsx", _xlsx([("WEGE.M", "X")]), "tidak sama"),
        ("Notasi Khusus-20261027.xlsx", _xlsx([("WEGE", "M")]), "KODE.NOTASI"),
        ("Notasi Khusus-20261027.xlsx", b"bukan zip", "XLSX"),
    ],
)
def test_bentuk_yang_tidak_dikenal_ditolak_dengan_sebabnya(
    tmp_path: Path, nama: str, isi: bytes, sebab: str
) -> None:
    """Daftar kosong atau berbentuk lain tidak boleh terbaca sebagai "tidak ada notasi"."""
    with pytest.raises(notasi.GalatNotasi, match=sebab):
        notasi.baca_unduhan(_berkas(tmp_path, isi, nama), hari_ini=HARI_INI)


# ---------------------------------------------------------------------------------------
# Impor lewat konfirmasi
# ---------------------------------------------------------------------------------------


@pytest.fixture()
def sambungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    koneksi = db.siapkan()
    lokasi.pastikan_folder(lokasi.folder_konfigurasi())
    try:
        yield koneksi
    finally:
        koneksi.close()


def _unggah(isi: bytes, nama: str = "Notasi Khusus-20261027.xlsx") -> Path:
    return notasi.simpan_unduhan(nama, isi)


def _aktif(sambungan: sqlite3.Connection) -> list[tuple[str, str, str]]:
    return [
        tuple(satu)
        for satu in sambungan.execute(
            "SELECT kode, jenis, tanggal_mulai FROM v_notasi_khusus_terkini "
            "WHERE tanggal_selesai IS NULL ORDER BY kode"
        )
    ]


def test_unggahan_disimpan_mentah_tanpa_menyentuh_basis_data(sambungan: sqlite3.Connection) -> None:
    isi = _xlsx(BARIS_CONTOH)
    jalur = _unggah(isi)
    assert jalur.read_bytes() == isi
    assert jalur.parent == lokasi.folder_data() / "unduhan-idx" / "notasi-khusus"
    assert sambungan.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0] == 0


def test_impor_menulis_basis_data_dan_berkas_konfigurasi_sesudah_konfirmasi(
    sambungan: sqlite3.Connection,
) -> None:
    jalur = _unggah(_xlsx(BARIS_CONTOH))
    konfigurasi = notasi.berkas_tujuan(lokasi.folder_konfigurasi())

    permintaan = tulis.permintaan_impor_notasi_idx(
        sambungan, jalur=jalur, nama_asli="Notasi Khusus-20261027.xlsx", hari_ini=HARI_INI
    )
    assert "27 Okt 2026" in permintaan.ringkasan and "4 emiten" in permintaan.ringkasan
    assert "papan pemantauan khusus: 1" in permintaan.ringkasan
    assert not konfigurasi.exists(), "sebelum konfirmasi, konfigurasi belum disentuh"
    assert _aktif(sambungan) == []

    hasil = tulis.jalankan_permintaan(permintaan, sambungan)

    assert hasil.berhasil, hasil.pesan
    assert _aktif(sambungan) == [
        ("BIMA", "papan_pemantauan", "2026-10-27"),
        ("CBMF", "notasi_lainnya", "2026-10-27"),
        ("GOTOM", "notasi_lainnya", "2026-10-27"),
        ("WEGE", "notasi_lainnya", "2026-10-27"),
    ]
    assert [satu.kode for satu in notasi.baca(konfigurasi.parent)] == ["BIMA", "CBMF", "GOTOM", "WEGE"]
    butir = jadwal._notasi(sambungan, HARI_INI)
    assert "27 Okt 2026" in butir.bukti and butir.status == jadwal.TERBARU


def test_daftar_baru_menutup_yang_tidak_lagi_tercantum_tanpa_menyentuh_isian_tangan(
    sambungan: sqlite3.Connection,
) -> None:
    konfigurasi = notasi.berkas_tujuan(lokasi.folder_konfigurasi())
    konfigurasi.write_text(
        "kode;jenis;tanggal_mulai;tanggal_selesai;keterangan\n"
        "AALI;suspensi;2026-01-05;;isian tangan\n",
        encoding="utf-8",
        newline="\n",
    )
    pertama = _unggah(_xlsx(BARIS_CONTOH))
    simpan_asli = ingesti.simpan
    with pytest.MonkeyPatch.context() as tambalan:
        # Impor pertama kemarin: dua impor pada detik yang sama berbagi `diketahui_pada` (T12).
        tambalan.setattr(
            ingesti, "simpan", lambda *a, **k: simpan_asli(*a, momen=datetime(2026, 10, 28, 18, tzinfo=WIB), **k)
        )
        assert tulis.jalankan_permintaan(
            tulis.permintaan_impor_notasi_idx(
                sambungan, jalur=pertama, nama_asli="Notasi Khusus-20261027.xlsx", hari_ini=HARI_INI
            ),
            sambungan,
        ).berhasil
    kedua = _unggah(_xlsx([("WEGE.M", "M")]), "Notasi Khusus-20261029.xlsx")

    permintaan = tulis.permintaan_impor_notasi_idx(
        sambungan, jalur=kedua, nama_asli="Notasi Khusus-20261029.xlsx", hari_ini=HARI_INI
    )
    assert "ditutup: 3" in permintaan.ringkasan
    assert tulis.jalankan_permintaan(permintaan, sambungan).berhasil

    assert ("AALI", "suspensi", "2026-01-05") in _aktif(sambungan)
    assert [kode for kode, jenis, _ in _aktif(sambungan) if jenis != "suspensi"] == ["WEGE", "WEGE"]
    tutup = sambungan.execute(
        "SELECT kode, tanggal_selesai FROM v_notasi_khusus_terkini "
        "WHERE tanggal_selesai IS NOT NULL ORDER BY kode"
    ).fetchall()
    assert [tuple(satu) for satu in tutup] == [
        ("BIMA", "2026-10-29"), ("CBMF", "2026-10-29"), ("GOTOM", "2026-10-29"),
    ]


def test_daftar_yang_sama_diunggah_ulang_tidak_menambah_revisi(sambungan: sqlite3.Connection) -> None:
    """Label sumber impor diturunkan dari folder impornya; folder per unggahan akan menulis ulang
    SELURUH baris notasi (termasuk suspensi) sebagai revisi baru setiap minggu walau isinya sama
    (terukur atas salinan data kerja: 2.603 baris)."""
    def impor(nama: str, jam: int) -> tulis.PermintaanTulis:
        jalur = notasi.simpan_unduhan(
            nama, _xlsx(BARIS_CONTOH), momen=datetime(2026, 10, 29, jam, tzinfo=WIB)
        )
        permintaan = tulis.permintaan_impor_notasi_idx(
            sambungan, jalur=jalur, nama_asli=nama, hari_ini=HARI_INI
        )
        assert tulis.jalankan_permintaan(permintaan, sambungan).berhasil
        return permintaan

    impor("Notasi Khusus-20261027.xlsx", 9)
    sebelum = sambungan.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0]
    kedua = impor("Notasi Khusus-20261027 (1).xlsx", 10)

    assert "baru: 0" in kedua.ringkasan
    assert sambungan.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0] == sebelum


def test_dua_konfirmasi_yang_disusun_berurutan_menulis_isi_yang_masing_masing_disetujui(
    sambungan: sqlite3.Connection,
) -> None:
    """Folder impornya tetap, jadi isi gabungan dibekukan saat konfirmasi disusun (K59 d)."""
    pertama = tulis.permintaan_impor_notasi_idx(
        sambungan, jalur=_unggah(_xlsx(BARIS_CONTOH)), nama_asli="Notasi Khusus-20261027.xlsx",
        hari_ini=HARI_INI,
    )
    tulis.permintaan_impor_notasi_idx(
        sambungan, jalur=_unggah(_xlsx([("WEGE.M", "M")]), "Notasi Khusus-20261029.xlsx"),
        nama_asli="Notasi Khusus-20261029.xlsx", hari_ini=HARI_INI,
    )

    assert tulis.jalankan_permintaan(pertama, sambungan).berhasil

    assert [kode for kode, _, _ in _aktif(sambungan)] == ["BIMA", "CBMF", "GOTOM", "WEGE"]
    assert [satu.kode for satu in notasi.baca(lokasi.folder_konfigurasi())] == [
        "BIMA", "CBMF", "GOTOM", "WEGE",
    ]


def test_daftar_yang_lebih_lama_dari_yang_tersimpan_ditolak(sambungan: sqlite3.Connection) -> None:
    baru = _unggah(_xlsx(BARIS_CONTOH))
    tulis.jalankan_permintaan(
        tulis.permintaan_impor_notasi_idx(
            sambungan, jalur=baru, nama_asli="Notasi Khusus-20261027.xlsx", hari_ini=HARI_INI
        ),
        sambungan,
    )
    lama = _unggah(_xlsx([("WEGE.M", "M")]), "Notasi Khusus-20261009.xlsx")

    with pytest.raises(tulis.GalatTulis, match="lebih lama"):
        tulis.permintaan_impor_notasi_idx(
            sambungan, jalur=lama, nama_asli="Notasi Khusus-20261009.xlsx", hari_ini=HARI_INI
        )


def test_konfigurasi_yang_berubah_sesudah_konfirmasi_disusun_menggagalkan_penulisan(
    sambungan: sqlite3.Connection,
) -> None:
    """Yang ditulis harus sama dengan yang disetujui (K59 d): berkas konfigurasi yang diubah di
    antara konfirmasi dan penulisan tidak boleh ditimpa diam-diam."""
    jalur = _unggah(_xlsx(BARIS_CONTOH))
    permintaan = tulis.permintaan_impor_notasi_idx(
        sambungan, jalur=jalur, nama_asli="Notasi Khusus-20261027.xlsx", hari_ini=HARI_INI
    )
    konfigurasi = notasi.berkas_tujuan(lokasi.folder_konfigurasi())
    konfigurasi.write_text(
        "kode;jenis;tanggal_mulai;tanggal_selesai;keterangan\nAALI;suspensi;2026-01-05;;baru\n",
        encoding="utf-8",
        newline="\n",
    )

    hasil = tulis.jalankan_permintaan(permintaan, sambungan)

    assert not hasil.berhasil and "berubah" in hasil.pesan
    assert _aktif(sambungan) == []
    assert "baru" in konfigurasi.read_text(encoding="utf-8")
