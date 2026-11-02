"""Kalender libur bursa dari pengumuman KSEI (K11) — tanpa jaringan, tanpa berkas PDF asli.

Berkas uji di sini **dibangun** di dalam uji, bukan disalin dari KSEI: berkas aslinya besar dan
bukan milik repo ini. Bentuk yang dibangun mengikuti apa yang terukur pada berkas KSEI 9 Okt 2026
(dua gaya berbeda, keduanya harus terbaca):

* berkas 2027 menaruh spasi **di dalam** potongan teks (`'Jumat '`) dan memisahkan sel hanya
  dengan lompatan koordinat; kolom "Hari" digambar 0,1 satuan lebih rendah dari tanggalnya;
* berkas 2025 menaruh spasi sebagai potongan tersendiri dan memecah kata (`'S'`, `'enin'`).

Yang tidak bisa dibuktikan uji ini: bahwa berkas **nyata** hari ini masih berbentuk begitu. Itu
diperiksa dengan menjalankan `--ambil-kalender` atas sumbernya dan mencatat hasilnya
(`docs/keputusan.md` bagian 5).
"""

from __future__ import annotations

import urllib.error
import zlib
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

import pytest

from mejasaham import berkas, ingesti, kalender

HALAMAN = "https://web.ksei.co.id/services/schedule-c-best-instruction"
HARI_INI = date(2026, 10, 9)

#: Cuplikan halaman KSEI apa adanya, termasuk `href` yang terpotong `....` — itu bukan salah
#: tulis: berkas 2026 memang tersimpan dengan nama terpotong itu (terukur 9 Okt 2026).
KEPALA_HALAMAN = """
<article>
<h1>Jadwal&nbsp;Operasional dan Libur KSEI</h1>
<p><a href="/files/C-BEST_OPERATIONAL_SCHEDULE6.pdf" target="_blank">Jadwal Instruksi C-BEST</a></p>
"""


def _halaman(*tautan: tuple[int, str]) -> str:
    """Halaman indeks tiruan dengan tautan kalender yang dipilih uji."""
    isi = "".join(
        f'<p><a href="{url}" target="_blank">Jadwal Hari Libur dan Cuti Bersama PT KSEI '
        f"Tahun {tahun}</a></p>"
        for tahun, url in tautan
    )
    return KEPALA_HALAMAN + isi + "</article>\n"

URL_2026 = (
    "https://web.ksei.co.id/files/"
    "1767843003_Penyesuaian_Pengumuman_Hari_Libur_dan_Cuti_Bersama_PT_KSEI_Ta....pdf"
)
URL_2027 = (
    "https://web.ksei.co.id/files/Pengumuman_Hari_Libur_dan_Cuti_Bersama_PT_KSEI_Tahun_2027.pdf"
)
URL_2025 = (
    "https://web.ksei.co.id/files/"
    "Pengumuman_Perubahan_Kedua_Hari_Libur_dan_Cuti_Bersama_PT_KSEI_Tahun_2025.pdf"
)


# ---------------------------------------------------------------------------------------
# Pembangun berkas PDF tiruan
# ---------------------------------------------------------------------------------------


def _tulis(teks: str, x: float, y: float, ukuran: float = 11.04) -> str:
    """Satu blok teks dengan posisi sendiri — bentuk yang dipakai kedua berkas KSEI."""
    return f"BT\n/F1 {ukuran} Tf\n1 0 0 1 {x} {y} Tm\n[({teks})] TJ\nET\n"


def _pdf(*aliran: str) -> bytes:
    """Bungkus aliran isi menjadi berkas yang dikenali pembaca: penanda `%PDF` + FlateDecode."""
    keluar = bytearray(b"%PDF-1.5\n")
    for satu in aliran:
        keluar += b"stream\n" + zlib.compress(satu.encode("latin-1")) + b"\nendstream\n"
    return bytes(keluar)


def _kepala_pengumuman(
    nomor_ksei: str, nomor_idx: str, tahun: int, *, kalender_libur_bursa: bool = True
) -> str:
    """Halaman pertama: nomor KSEI, kalimat tindak lanjut, nomor IDX terbelah dua baris.

    Nomor IDX sengaja dipotong di ujung baris seperti berkas nyata ("… No. Peng" /
    "-00169/BEI.POP/09-2026"); pencarian yang hanya melihat satu baris akan melewatkannya.
    """
    teks = _tulis("PENGUMUMAN", 260.2, 746.6, 14.0) + _tulis("No . " + nomor_ksei, 229.4, 730.7)
    if not nomor_idx:
        return teks
    depan, belakang = nomor_idx.split("-", 1)  # "Peng" | "00169/BEI.POP/09-2026"
    perihal = f"perihal Kalender Libur Bursa Tahun {tahun}" if kalender_libur_bursa else (
        "perihal Perubahan Kalender Kegiatan Operasional Perdagangan dan Pelaporan Transaksi "
        "Efek Bersifat Utang dan/atau Sukuk"
    )
    return (
        teks
        + _tulis(
            "Dalam rangka menindaklanjuti surat pengumuman PT Bursa Efek Indonesia No. " + depan,
            70.9,
            690.0,
        )
        + _tulis("-" + belakang, 70.9, 673.8)
        + _tulis(perihal, 240.0, 657.5)
    )


def _kepala_tabel(y: float) -> str:
    return (
        _tulis("No", 87.6, y)
        + _tulis("Hari", 124.7, y)
        + _tulis("Tanggal", 184.2, y)
        + _tulis("Keterangan", 355.1, y)
    )


def _baris_gaya_2027(nomor: int, hari: str, tanggal: str, keterangan: str, y: float) -> str:
    """Gaya berkas 2027: spasi di dalam potongan, kolom hari 0,1 satuan lebih rendah."""
    hari_angka, bulan, tahun = tanggal.split("-")
    return (
        _tulis(str(nomor), 89.2, y)
        + _tulis(hari + " ", 116.1, y - 0.1)
        + _tulis(hari_angka, 178.5, y)
        + _tulis("-", 183.9, y)
        + _tulis(bulan, 187.8, y)
        + _tulis("-", 202.1, y)
        + _tulis(tahun, 206.1, y)
        + _tulis(keterangan, 300.0, y)
    )


def _baris_gaya_2025(nomor: int, hari: str, tanggal: str, keterangan: str, y: float) -> str:
    """Gaya berkas 2025: spasi sebagai potongan tersendiri, nama hari terpecah dua potongan."""
    hari_angka, bulan, tahun = tanggal.split("-")
    return (
        _tulis(str(nomor), 88.7, y)
        + _tulis(" ", 100.6, y)
        + _tulis(hari[:1], 116.1, y)
        + _tulis(hari[1:], 121.9, y)
        + _tulis(" ", 142.8, y)
        + _tulis(hari_angka, 187.5, y)
        + _tulis("-", 193.5, y)
        + _tulis(bulan, 197.9, y)
        + _tulis("-", 214.3, y)
        + _tulis(tahun, 218.7, y)
        + _tulis(" ", 242.3, y)
        + _tulis(keterangan, 253.1, y)
    )


#: Isi lampiran 2027 tiruan: (nomor, hari, tanggal, keterangan).
BARIS_2027 = (
    (1, "Jumat", "1-Jan-2027", "Tahun Baru 2027 Masehi"),
    (2, "Selasa", "5-Jan-2027", "Isra Mikraj Nabi Muhammad S.A.W. 1448 Hijriah"),
    (3, "Jumat", "5-Feb-2027", "Cuti Bersama Tahun Baru Imlek 2578 Kongzili"),
    (4, "Senin", "8-Mar-2027", "Hari Suci Nyepi (Tahun Baru Saka 1949)"),
    (5, "Rabu", "10-Mar-2027", "Idul Fitri 1448 Hijriah"),
    (6, "Jumat", "31-Des-2027", "Libur Bursa"),
)

#: Isi lampiran 2025 tiruan.
BARIS_2025 = (
    (1, "Rabu", "1-Jan-2025", "Tahun Baru 2025 Masehi"),
    (2, "Senin", "27-Jan-2025", "Isra Mikraj Nabi Muhammad SAW"),
    (3, "Kamis", "29-Mei-2025", "Kenaikan Yesus Kristus"),
    (4, "Jumat", "6-Jun-2025", "Idul Adha 1446 Hijriah"),
    (5, "Rabu", "31-Des-2025", "Libur Bursa"),
)


def _lampiran(baris: tuple[tuple[int, str, str, str], ...], *, gaya: str, y_awal: float) -> str:
    keluar = _tulis("Lampiran", 70.9, 745.9, 12.0) + _kepala_tabel(y_awal + 18.0)
    for nomor, hari, tanggal, keterangan in baris:
        pembuat = _baris_gaya_2027 if gaya == "2027" else _baris_gaya_2025
        keluar += pembuat(nomor, hari, tanggal, keterangan, y_awal)
        y_awal -= 23.9
    return keluar


def _pdf_2027(
    *,
    nomor_idx: str = "Peng-00169/BEI.POP/09-2026",
    tahun_judul: int = 2027,
    tahun_tanggal: int = 2027,
    kalender_libur_bursa: bool = True,
    baris: tuple[tuple[int, str, str, str], ...] = BARIS_2027,
) -> bytes:
    isi = tuple(
        (nomor, hari, tanggal.replace("-2027", f"-{tahun_tanggal}"), keterangan)
        for nomor, hari, tanggal, keterangan in baris
    )
    return _pdf(
        _kepala_pengumuman(
            "PENG-0004/DIR/KSEI/0926",
            nomor_idx,
            tahun_judul,
            kalender_libur_bursa=kalender_libur_bursa,
        ),
        _lampiran(isi, gaya="2027", y_awal=638.7),
        "q 0.0 0.0 595.32 841.92 re W* n Q\n",  # aliran tanpa operator teks: harus diabaikan
    )


def _pdf_2025(
    *,
    kalender_libur_bursa: bool = False,
    nomor_ksei: str = "PENG-0007/DIR/KSEI/1225",
    nomor_idx: str = "Peng-00150/BEI.POP/08-2025",
    baris: tuple[tuple[int, str, str, str], ...] = BARIS_2025,
) -> bytes:
    """Berkas 2025 tiruan.

    Bawaannya meniru **berkas yang ditautkan halaman KSEI sekarang** (versi *Perubahan Kedua*,
    `PENG-0007`, menindaklanjuti kalender operasional EBA/sukuk sehingga ditolak syarat T31).
    Nomor dan barisnya bisa diganti untuk meniru revisi lain — itulah yang dipakai uji P19.
    """
    return _pdf(
        _kepala_pengumuman(
            nomor_ksei, nomor_idx, 2025, kalender_libur_bursa=kalender_libur_bursa
        ),
        _lampiran(baris, gaya="2025", y_awal=680.0),
    )


# ---------------------------------------------------------------------------------------
# Pembuka jaringan tiruan
# ---------------------------------------------------------------------------------------


class _Balasan:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_Balasan":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


def _pembuka(isi: Mapping[str, bytes], diminta: list[str]) -> Callable[[str, float], _Balasan]:
    def buka(url: str, timeout: float) -> _Balasan:
        diminta.append(url)
        if url not in isi:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]
        return _Balasan(isi[url])

    return buka


# ---------------------------------------------------------------------------------------
# Menemukan berkas di halaman KSEI
# ---------------------------------------------------------------------------------------


def test_tautan_kalender_ditemukan_beserta_tahunnya() -> None:
    html = _halaman((2027, URL_2027), (2026, URL_2026))
    tautan, diabaikan = kalender.temukan_berkas(html, halaman=HALAMAN)

    assert [satu.tahun for satu in tautan] == [2026, 2027]
    assert tautan[0].url == URL_2026  # href terpotong dipakai apa adanya
    assert tautan[1].url == URL_2027
    assert diabaikan == ()


def test_halaman_tanpa_tautan_kalender_ditolak_dengan_jelas() -> None:
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.temukan_berkas("<p>tidak ada apa-apa</p>", halaman=HALAMAN)
    assert "tidak ada tautan kalender" in str(keluhan.value)


def test_tautan_libur_tanpa_tahun_dilaporkan_bukan_dibuang_diam_diam() -> None:
    html = (
        '<p><a href="/files/Pengumuman_Libur_Tanpa_Tahun.pdf">Jadwal Libur KSEI</a></p>'
        + _halaman((2027, URL_2027))
    )
    tautan, diabaikan = kalender.temukan_berkas(html, halaman=HALAMAN)

    assert len(tautan) == 1
    assert len(diabaikan) == 1 and "Tanpa_Tahun" in diabaikan[0]


def test_tautan_yang_bukan_pdf_diabaikan() -> None:
    html = '<a href="/files/Jadwal_Libur_2027.xlsx">Jadwal Libur KSEI Tahun 2027</a>'
    with pytest.raises(ingesti.GalatIngesti):
        kalender.temukan_berkas(html, halaman=HALAMAN)


# ---------------------------------------------------------------------------------------
# Penguraian lampiran
# ---------------------------------------------------------------------------------------


def test_urai_kalender_gaya_2027_terbaca() -> None:
    hasil = kalender.urai_kalender(_pdf_2027(), url=URL_2027, tahun=2027)

    assert hasil.tahun == 2027
    assert hasil.nomor_ksei == "PENG-0004/DIR/KSEI/0926"
    assert hasil.nomor_idx == "Peng-00169/BEI.POP/09-2026"
    assert hasil.jumlah == 6
    assert hasil.hari_libur[0].tanggal == date(2027, 1, 1)
    assert hasil.hari_libur[0].keterangan == "Tahun Baru 2027 Masehi"
    assert hasil.hari_libur[-1].tanggal == date(2027, 12, 31)
    assert hasil.hari_libur[-1].keterangan == "Libur Bursa"


def test_urai_kalender_gaya_2025_terbaca_walau_kata_terpecah() -> None:
    """Nama hari yang terpecah antar potongan ("S" + "enin") tetap harus utuh terbaca."""
    hasil = kalender.urai_kalender(
        _pdf_2025(kalender_libur_bursa=True), url=URL_2025, tahun=2025
    )

    assert [satu.hari for satu in hasil.hari_libur][:2] == ["Rabu", "Senin"]
    assert hasil.hari_libur[1].keterangan == "Isra Mikraj Nabi Muhammad SAW"
    assert hasil.hari_libur[1].tanggal == date(2025, 1, 27)


def test_balasan_bukan_pdf_ditolak() -> None:
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.urai_kalender(b"<html>challenge</html>", url=URL_2027, tahun=2027)
    assert "bukan berkas PDF" in str(keluhan.value)


def test_tanpa_nomor_pengumuman_idx_ditolak() -> None:
    """K11 membolehkan KSEI **karena** berkasnya menindaklanjuti pengumuman IDX."""
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.urai_kalender(_pdf_2027(nomor_idx=""), url=URL_2027, tahun=2027)
    assert "BEI.POP" in str(keluhan.value)


def test_tanpa_frasa_kalender_libur_bursa_ditolak_khusus() -> None:
    """Berkas 2025 nyata menindaklanjuti kalender EBA/sukuk, bukan kalender libur bursa."""
    with pytest.raises(kalender.GalatTindakLanjut) as keluhan:
        kalender.urai_kalender(_pdf_2025(), url=URL_2025, tahun=2025)

    pesan = str(keluhan.value)
    assert "Kalender Libur Bursa" in pesan
    assert "Peng-00150/BEI.POP/08-2025" in pesan


def test_nama_hari_yang_tidak_cocok_ditolak() -> None:
    """Nama hari di berkas adalah pemeriksaan silang: kalau tidak cocok, uraiannya salah."""
    baris = (
        (1, "Senin", "1-Jan-2027", "Tahun Baru 2027 Masehi"),  # 1 Jan 2027 = Jumat
        (2, "Selasa", "5-Jan-2027", "Isra Mikraj"),
        (3, "Jumat", "5-Feb-2027", "Imlek"),
        (4, "Senin", "8-Mar-2027", "Nyepi"),
        (5, "Rabu", "10-Mar-2027", "Idul Fitri"),
    )
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.urai_kalender(_pdf_2027(baris=baris), url=URL_2027, tahun=2027)
    assert "1-Jan-2027" in str(keluhan.value) and "jumat" in str(keluhan.value)


def test_nomor_urut_bolong_ditolak() -> None:
    """Baris yang hilang di tengah tabel tidak boleh menghasilkan kalender yang tampak utuh."""
    baris = (
        (1, "Jumat", "1-Jan-2027", "Tahun Baru"),
        (2, "Selasa", "5-Jan-2027", "Isra Mikraj"),
        (4, "Senin", "8-Mar-2027", "Nyepi"),
        (5, "Rabu", "10-Mar-2027", "Idul Fitri"),
        (6, "Jumat", "31-Des-2027", "Libur Bursa"),
    )
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.urai_kalender(_pdf_2027(baris=baris), url=URL_2027, tahun=2027)
    assert "hilang: [3]" in str(keluhan.value)


def test_lampiran_terlalu_pendek_ditolak() -> None:
    """Lampiran yang bentuknya berubah bisa terbaca sebagai satu-dua baris; itu ditolak."""
    pendek = (
        (1, "Jumat", "1-Jan-2027", "Tahun Baru 2027 Masehi"),
        (2, "Selasa", "5-Jan-2027", "Isra Mikraj Nabi Muhammad S.A.W. 1448 Hijriah"),
    )
    assert len(pendek) < kalender.BARIS_MINIMUM
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.urai_kalender(_pdf_2027(baris=pendek), url=URL_2027, tahun=2027)
    assert "paling sedikit" in str(keluhan.value)


def test_tanggal_di_luar_tahun_judul_ditolak() -> None:
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.urai_kalender(
            _pdf_2027(tahun_judul=2027, tahun_tanggal=2028), url=URL_2027, tahun=2027
        )
    assert "2028" in str(keluhan.value)


def test_tanggal_ganda_ditolak() -> None:
    """Satu tanggal dua keterangan: memilih salah satunya diam-diam berarti mengarang."""
    baris = (
        (1, "Jumat", "1-Jan-2027", "Tahun Baru 2027 Masehi"),
        (2, "Jumat", "1-Jan-2027", "Cuti Bersama Tahun Baru"),
        (3, "Selasa", "5-Jan-2027", "Isra Mikraj Nabi Muhammad S.A.W. 1448 Hijriah"),
        (4, "Jumat", "5-Feb-2027", "Cuti Bersama Tahun Baru Imlek 2578 Kongzili"),
        (5, "Senin", "8-Mar-2027", "Hari Suci Nyepi (Tahun Baru Saka 1949)"),
        (6, "Rabu", "10-Mar-2027", "Idul Fitri 1448 Hijriah"),
    )
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.urai_kalender(_pdf_2027(baris=baris), url=URL_2027, tahun=2027)
    assert "2027-01-01" in str(keluhan.value)


# ---------------------------------------------------------------------------------------
# Baris kalender bursa
# ---------------------------------------------------------------------------------------


def test_hari_bursa_diturunkan_dari_hari_kerja_dikurangi_libur() -> None:
    hasil = kalender.urai_kalender(_pdf_2027(), url=URL_2027, tahun=2027)
    baris = {satu.tanggal: satu for satu in kalender.baris_setahun(hasil)}

    assert len(baris) == 365
    assert baris[date(2027, 1, 1)].hari_bursa is False
    assert baris[date(2027, 1, 1)].keterangan == "Tahun Baru 2027 Masehi"
    assert baris[date(2027, 1, 4)].hari_bursa is True  # Senin biasa
    assert baris[date(2027, 1, 2)].hari_bursa is False
    assert baris[date(2027, 1, 2)].keterangan == "akhir pekan"


def test_sumber_baris_membedakan_pengumuman_dari_turunan() -> None:
    hasil = kalender.urai_kalender(_pdf_2027(), url=URL_2027, tahun=2027)
    baris = {satu.tanggal: satu for satu in kalender.baris_setahun(hasil)}

    assert baris[date(2027, 1, 1)].sumber == (
        "PENG-0004/DIR/KSEI/0926 (menindaklanjuti IDX Peng-00169/BEI.POP/09-2026)"
    )
    assert baris[date(2027, 1, 4)].sumber.startswith("turunan: hari kerja")
    assert baris[date(2027, 1, 2)].sumber.startswith("turunan: akhir pekan")


# ---------------------------------------------------------------------------------------
# Pengambilan penuh: unduh -> tulis -> baca ulang
# ---------------------------------------------------------------------------------------


def test_ambil_kalender_menulis_berkas_yang_terbaca_pembaca_impor(tmp_path: Path) -> None:
    isi = {HALAMAN: _halaman((2027, URL_2027)).encode("utf-8"), URL_2027: _pdf_2027()}
    diminta: list[str] = []

    hasil = kalender.ambil_kalender(
        tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, diminta), jeda=0.0
    )

    assert [satu.tahun for satu in hasil.tahun] == [2027]
    assert hasil.jumlah_libur == 6
    assert hasil.jumlah_akhir_pekan == 104  # 2027 mulai dan berakhir pada hari Jumat
    assert hasil.jumlah_hari_bursa == 365 - 104 - 6
    assert hasil.jumlah_terbaca_ulang == 365

    terbaca = berkas.baca_kalender(tmp_path)
    assert len(terbaca) == 365
    assert any(satu.sumber and "PENG-0004/DIR/KSEI/0926" in satu.sumber for satu in terbaca)
    assert diminta[0] == HALAMAN  # halaman indeks diambil lebih dulu, baru berkasnya


def test_ambil_kalender_menolak_menimpa_tanpa_izin(tmp_path: Path) -> None:
    (tmp_path / berkas.NAMA_BERKAS_KALENDER).write_text(
        "tanggal;hari_bursa;keterangan\n2026-10-09;1;kalender saya\n", encoding="utf-8"
    )
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.ambil_kalender(tmp_path, hari_ini=HARI_INI, buka=_pembuka({}, []), jeda=0.0)
    assert "--timpa-kalender" in str(keluhan.value)


def test_ambil_kalender_melanjutkan_tahun_lain_saat_satu_tahun_ditolak(tmp_path: Path) -> None:
    """Penolakan satu berkas bukan kegagalan seluruh pengambilan — tetapi harus terlihat."""
    html = _halaman((2025, URL_2025), (2027, URL_2027))
    isi = {HALAMAN: html.encode("utf-8"), URL_2025: _pdf_2025(), URL_2027: _pdf_2027()}

    hasil = kalender.ambil_kalender(
        tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0
    )

    assert [satu.tahun for satu in hasil.tahun] == [2027]
    assert len(hasil.tahun_ditolak) == 1
    assert hasil.tahun_ditolak[0].startswith("2025:")

    isi_berkas = (tmp_path / berkas.NAMA_BERKAS_KALENDER).read_text(encoding="utf-8")
    assert "Tahun yang TIDAK ada di berkas ini" in isi_berkas
    assert "2025:" in isi_berkas


def test_ambil_kalender_tahun_yang_tidak_ada_di_halaman(tmp_path: Path) -> None:
    isi = {HALAMAN: _halaman((2026, URL_2026), (2027, URL_2027)).encode("utf-8")}
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.ambil_kalender(
            tmp_path, tahun=2024, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0
        )
    assert "2024" in str(keluhan.value) and "2026, 2027" in str(keluhan.value)


def test_ambil_kalender_gagal_total_saat_semua_berkas_ditolak(tmp_path: Path) -> None:
    isi = {
        HALAMAN: _halaman((2027, URL_2027)).encode("utf-8"),
        URL_2027: _pdf_2027(kalender_libur_bursa=False),
    }
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.ambil_kalender(tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0)
    assert "tidak ada satu pun pengumuman" in str(keluhan.value)
    assert not (tmp_path / berkas.NAMA_BERKAS_KALENDER).exists()


def test_halaman_yang_menolak_tanpa_berkas_tidak_menulis_apa_apa(tmp_path: Path) -> None:
    """Halaman 500 tanpa PDF: tidak ada berkas yang ditulis, dan galatnya menyebut sebabnya."""
    isi = {HALAMAN: _halaman((2027, URL_2027)).encode("utf-8")}  # PDF-nya tidak ada -> 404
    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.ambil_kalender(tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0)
    assert "404" in str(keluhan.value)
    assert not (tmp_path / berkas.NAMA_BERKAS_KALENDER).exists()


# ---------------------------------------------------------------------------------------
# P19: revisi yang lebih lama, dipakai hanya bila tanggalnya identik
# ---------------------------------------------------------------------------------------

#: Alamat revisi lama 2025, diturunkan dari `URL_2025` dengan melepas penanda "Kedua".
URL_2025_REVISI_LAMA = URL_2025.replace("_Perubahan_Kedua_", "_Perubahan_")


def test_kandidat_revisi_lama_melepas_penanda_satu_per_satu() -> None:
    """Penurunan alamatnya bukan tebakan bebas: hanya penanda revisi yang dilepas, berurutan."""
    assert kalender.kandidat_revisi_lama(URL_2025) == (
        URL_2025_REVISI_LAMA,
        URL_2025.replace("_Perubahan_Kedua_", "_Perubahan_").replace("_Perubahan_", "_"),
    )
    assert kalender.kandidat_revisi_lama(
        "https://web.ksei.co.id/files/Pengumuman_Hari_Libur_Tahun_2027.pdf"
    ) == (), "berkas tanpa penanda revisi tidak menghasilkan kandidat apa pun"


def test_revisi_lama_dipakai_bila_tanggalnya_identik(tmp_path: Path) -> None:
    """Inti P19: berkas yang ditautkan ditolak syarat sumber, revisi lamanya lulus — dan
    tanggalnya sama persis, jadi tanggal itulah yang dipakai.

    Yang diuji bukan sekadar "2025 akhirnya ada", melainkan bahwa yang dipakai adalah berkas yang
    **lulus seluruh pemeriksaan**, dan bahwa asalnya tercatat: nomor KSEI revisi lama, nomor
    berkas yang ditautkan sebagai pembanding, dan pernyataan bahwa tanggalnya identik.
    """
    isi = {
        HALAMAN: _halaman((2025, URL_2025)).encode("utf-8"),
        URL_2025: _pdf_2025(),  # ditolak T31: menindaklanjuti kalender operasional EBA/sukuk
        URL_2025_REVISI_LAMA: _pdf_2025(
            kalender_libur_bursa=True,
            nomor_ksei="PENG-0004/DIR/KSEI/0825",
            nomor_idx="Peng-00149/BEI.POP/08-2025",
        ),
    }

    hasil = kalender.ambil_kalender(
        tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0
    )

    assert [satu.tahun for satu in hasil.tahun] == [2025], "tahunnya kini terpakai"
    dipakai = hasil.tahun[0]
    assert dipakai.nomor_ksei == "PENG-0004/DIR/KSEI/0825", "yang dipakai berkas yang lulus syarat"
    assert dipakai.url == URL_2025_REVISI_LAMA
    assert dipakai.jumlah == len(BARIS_2025)
    assert dipakai.revisi is not None
    assert "SAMA PERSIS" in dipakai.revisi
    assert "PENG-0007/DIR/KSEI/1225" in dipakai.revisi, "berkas pembandingnya ikut disebut"
    assert "keterangannya pun sama" in dipakai.revisi
    assert hasil.tahun_ditolak == (), "tahunnya tidak lagi masuk daftar yang ditolak"

    isi_berkas = (tmp_path / berkas.NAMA_BERKAS_KALENDER).read_text(encoding="utf-8")
    assert "PENG-0004/DIR/KSEI/0825" in isi_berkas, "asal tanggalnya tertulis di berkasnya"
    assert "Percobaan mencari REVISI LEBIH LAMA" in isi_berkas


def test_revisi_lama_ditolak_bila_ada_satu_tanggal_berbeda(tmp_path: Path) -> None:
    """Syarat yang diminta pengguna: **tanggalnya harus identik**. Satu saja berbeda → ditolak.

    Ini yang membuat aturannya bukan "pakai dokumen lama": revisi lama hanya boleh berbicara
    sejauh ia sepakat dengan berkas yang lebih baru. Nama harinya ikut disesuaikan (30 Des 2025
    adalah Selasa) supaya yang diuji benar-benar perbandingan tanggalnya, bukan pemeriksaan hari.
    """
    baris_berbeda = BARIS_2025[:-1] + ((5, "Selasa", "30-Des-2025", "Libur Bursa"),)
    isi = {
        HALAMAN: _halaman((2025, URL_2025)).encode("utf-8"),
        URL_2025: _pdf_2025(),
        URL_2025_REVISI_LAMA: _pdf_2025(kalender_libur_bursa=True, baris=baris_berbeda),
    }

    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.ambil_kalender(tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0)

    pesan = str(keluhan.value)
    assert "TIDAK identik" in pesan
    assert "2025-12-30" in pesan and "2025-12-31" in pesan, "tanggal yang berbeda disebut keduanya"
    assert not (tmp_path / berkas.NAMA_BERKAS_KALENDER).exists()


def test_revisi_lama_yang_tidak_lulus_syarat_tetap_ditolak(tmp_path: Path) -> None:
    """Revisi lama yang **juga** tidak menindaklanjuti kalender libur bursa tidak menolong."""
    isi = {
        HALAMAN: _halaman((2025, URL_2025)).encode("utf-8"),
        URL_2025: _pdf_2025(),
        URL_2025_REVISI_LAMA: _pdf_2025(),  # sama-sama ditolak syarat T31
    }

    with pytest.raises(ingesti.GalatIngesti, match="tidak ada satu pun pengumuman"):
        kalender.ambil_kalender(tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, []), jeda=0.0)


def test_revisi_lama_tidak_dicari_bila_berkas_ditautkan_rusak_lebih_dalam(
    tmp_path: Path,
) -> None:
    """Kalau berkas yang ditautkan gagal **pemeriksaan lain**, revisi lama tidak dicari sama sekali.

    Sebabnya penting: mencari pengganti untuk berkas yang tabelnya sendiri rusak akan menutupi
    kerusakan yang lebih besar daripada soal tindak lanjut. Buktinya bukan hanya pesannya,
    melainkan juga bahwa alamat revisi lama **tidak pernah diminta** ke server.
    """
    # Nomor urut tabelnya bolong (3 diganti 9): jumlah barisnya tetap lima, jadi yang gagal
    # memang pemeriksaan nomor urut — bukan pemeriksaan jumlah baris minimum.
    baris_bolong = (
        BARIS_2025[0],
        BARIS_2025[1],
        (9, *BARIS_2025[2][1:]),
        BARIS_2025[3],
        BARIS_2025[4],
    )
    isi = {
        HALAMAN: _halaman((2025, URL_2025)).encode("utf-8"),
        URL_2025: _pdf_2025(baris=baris_bolong),
        URL_2025_REVISI_LAMA: _pdf_2025(kalender_libur_bursa=True),
    }
    diminta: list[str] = []

    with pytest.raises(ingesti.GalatIngesti) as keluhan:
        kalender.ambil_kalender(
            tmp_path, hari_ini=HARI_INI, buka=_pembuka(isi, diminta), jeda=0.0
        )

    assert "nomor urut" in str(keluhan.value)
    assert diminta == [HALAMAN, URL_2025], (
        "berkas yang rusak lebih dalam tidak boleh ditutupi dengan mencari revisi lain"
    )


def test_revisi_lama_yang_tidak_ada_dicatat_bukan_disembunyikan(tmp_path: Path) -> None:
    """Berkas revisi lama yang sudah dihapus dari server tetap dilaporkan — sebagai percobaan."""
    isi = {
        HALAMAN: _halaman((2027, URL_2027)).encode("utf-8"),
        URL_2027: _pdf_2027(),
        # URL_2025_REVISI_LAMA sengaja tidak ada -> 404
        URL_2025: _pdf_2025(),
    }
    html = _halaman((2025, URL_2025), (2027, URL_2027))

    hasil = kalender.ambil_kalender(
        tmp_path, hari_ini=HARI_INI, buka=_pembuka({**isi, HALAMAN: html.encode("utf-8")}, []),
        jeda=0.0,
    )

    assert [satu.tahun for satu in hasil.tahun] == [2027]
    assert len(hasil.tahun_ditolak) == 1, "hanya tahunnya yang masuk daftar ditolak"
    assert any("revisi lama TIDAK ADA" in satu for satu in hasil.catatan_revisi)
    assert any("404" in satu for satu in hasil.catatan_revisi)


def test_ukuran_font_dibaca_dari_operator_tf_berspasi() -> None:
    """`/F1 11.04 Tf` dulu tidak pernah cocok (pola `re.X` membuang spasinya), jadi ukuran selalu 10."""
    potongan, _ = kalender.potongan_teks(_pdf(_tulis("PENGUMUMAN", 260.2, 746.6, 14.0)), di_mana="uji")

    assert [(satu.teks, satu.ukuran) for satu in potongan] == [("PENGUMUMAN", 14.0)]
