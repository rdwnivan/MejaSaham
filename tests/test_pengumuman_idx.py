"""PDF pengumuman suspensi & UMA IDX yang diunggah pengguna (K99): dibaca, digabung, diimpor."""

from __future__ import annotations

import sqlite3
import zlib
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from mejasaham import db, ingesti, jadwal, kalender, lokasi, notasi, pengumuman_idx
from mejasaham.layar import tulis

HARI_INI = date(2026, 10, 29)


# ---------------------------------------------------------------------------------------
# PDF tiruan berbentuk berkas nyata (20261028-UMA_COIN.pdf, 20261028-WAS_Suspensi_PTSP.pdf):
# halaman Inggris lalu halaman Indonesia, dan potongan teks yang memecah nomor serta kode emiten
# sehingga spasi menyelip di dalamnya ("Peng-UMA-00 352 /BEI.WAS/ 10-2026", "( FILM )").
# ---------------------------------------------------------------------------------------


def _halaman(baris: list[str | list[str]]) -> str:
    isi = ""
    y = 780.0
    for satu in baris:
        potongan = [satu] if isinstance(satu, str) else satu
        x = 70.0
        for teks in potongan:
            # Kurung di dalam string PDF di-escape, seperti di berkas nyata.
            aman = teks.replace("(", "\\(").replace(")", "\\)")
            isi += f"BT\n/F1 11 Tf\n1 0 0 1 {x} {y} Tm\n[({aman})] TJ\nET\n"
            x += len(teks) * 6.5 + 4
        y -= 14
    return isi


def _pdf(*halaman: str) -> bytes:
    keluar = bytearray(b"%PDF-1.7\n")
    for satu in halaman:
        keluar += b"stream\n" + zlib.compress(satu.encode("latin-1")) + b"\nendstream\n"
    return bytes(keluar)


def _uma(kode: str = "COIN", nomor: str = "00352", tanggal: str = "28 Oktober 2026") -> bytes:
    inggris = _halaman(["ANNOUNCEMENT", "UNUSUAL MARKET ACTIVITY", f"PT Emiten Tbk ({kode})", "October 28, 2026"])
    indonesia = _halaman(
        [
            "PENGUMUMAN",
            "UNUSUAL MARKET ACTIVITY",
            ["PT Emiten Tbk (", kode, ")"],
            [f"Peng-UMA-00 {nomor[2:]}", "/BEI.WAS/", "10-2026"],
            "Dalam rangka perlindungan Investor, dengan ini kami menginformasikan bahwa telah terjadi",
            f"penurunan harga saham PT Emiten Tbk ({kode}) yang di luar kebiasaan (Unusual Market",
            "Activity).",
            "Demikian untuk diketahui.",
            tanggal,
            "Tembusan:",
            f"4. Yth. Direksi PT Emiten Tbk ({kode});",
        ]
    )
    return _pdf(inggris, indonesia)


def _suspensi(
    kode: str = "PTSP",
    *,
    berlaku: str = "pada tanggal 29 Oktober 2026.",
    jenis: str = "SPT",
    kode_lain: str | None = None,
    nomor: list[str] | None = None,
) -> bytes:
    kode_kedua = f" dan PT Lain Tbk ({kode_lain})" if kode_lain else ""
    indonesia = _halaman(
        [
            "PENGUMUMAN",
            nomor or [f"Peng-{jenis}-00 222", "/BEI.WAS/", "10-2026"],
            "Sehubungan dengan terjadinya peningkatan harga kumulatif yang signifikan pada saham",
            [f"PT Emiten Tbk ({kode})", f"{kode_kedua}, dalam rangka cooling down sebagai bentuk"],
            "perlindungan bagi Investor, PT Bursa Efek Indonesia memandang perlu untuk melakukan",
            f"penghentian sementara perdagangan saham PT Emiten Tbk ({kode})",
            berlaku,
            "Demikian untuk diketahui.",
            "28 Oktober 2026",
            "Tembusan:",
        ]
    )
    return _pdf(_halaman(["ANNOUNCEMENT", "October 28, 2026"]), indonesia)


# ---------------------------------------------------------------------------------------
# Pembaca
# ---------------------------------------------------------------------------------------


def test_pengumuman_uma_menjadi_baris_uma_tiga_puluh_hari() -> None:
    satu = pengumuman_idx.baca(_uma(), nama_berkas="20261028-UMA_COIN.pdf", hari_ini=HARI_INI)

    assert (satu.jenis, satu.kode, satu.nomor) == ("uma", "COIN", "Peng-UMA-00352/BEI.WAS/10-2026")
    baris = satu.baris()
    assert (baris.kode, baris.jenis, baris.tanggal_mulai, baris.tanggal_selesai) == (
        "COIN", "uma", date(2026, 10, 28), date(2026, 11, 27)
    )
    assert "Peng-UMA-00352/BEI.WAS/10-2026" in baris.keterangan
    assert "aturan UMA 30 hari" in baris.keterangan


def test_suspensi_dimulai_pada_tanggal_berlaku_bukan_tanggal_pengumuman() -> None:
    """K99: PTSP diumumkan 28 Okt, dihentikan 29 Okt — hari yang tidak bisa diperdagangkan."""
    satu = pengumuman_idx.baca(
        _suspensi(), nama_berkas="20261028-WAS_Suspensi_PTSP.pdf", hari_ini=HARI_INI
    )

    baris = satu.baris()
    assert (baris.kode, baris.jenis, baris.tanggal_mulai, baris.tanggal_selesai) == (
        "PTSP", "suspensi", date(2026, 10, 29), None
    )
    assert "diumumkan 2026-10-28" in baris.keterangan
    assert "Peng-SPT-00222/BEI.WAS/10-2026" in baris.keterangan


@pytest.mark.parametrize(
    ("isi", "nama", "sebab"),
    [
        (_suspensi(kode_lain="ABCD"), "x.pdf", "lebih dari satu kode"),
        (_suspensi(berlaku="hingga pengumuman lebih lanjut."), "x.pdf", "tanggal berlaku"),
        (b"<html>tantangan</html>", "x.pdf", "bukan berkas PDF"),
        (_uma(), "20261028-UMA_FILM.pdf", "nama berkas"),
        (_uma(), "20261027-UMA_COIN.pdf", "nama berkas"),
        (_uma(tanggal="30 Oktober 2026"), "x.pdf", "sesudah hari ini"),
        (_pdf(_halaman(["ANNOUNCEMENT", "Peng-UMA-00352/BEI.WAS/10-2026"])), "x.pdf", "PENGUMUMAN"),
    ],
    ids=[
        "multi-kode", "tanpa-tanggal-berlaku", "bukan-pdf", "nama-kode-lain",
        "nama-tanggal-lain", "masa-depan", "tanpa-bagian-indonesia",
    ],
)
def test_bentuk_yang_tidak_dikenal_ditolak_dengan_sebabnya(isi: bytes, nama: str, sebab: str) -> None:
    """Bentuk yang belum ada contohnya tidak ditebak (K99): ditolak, bukan dibaca sebagian."""
    with pytest.raises(pengumuman_idx.GalatPengumuman, match=sebab):
        pengumuman_idx.baca(isi, nama_berkas=nama, hari_ini=HARI_INI)


#: Suspensi lanjutan sesudah pembukaan cooling-down (PDF SPT asli IDX 2024–2026 di
#: `.uji-data/riset-idx/riwayat-api-pdf/`, K103): tanpa "pada tanggal", dengan sesi dan pasarnya.
SAMPAI_LANJUT = "sampai dengan Pengumuman Bursa lebih lanjut."


@pytest.mark.parametrize(
    "berlaku",
    [
        f"di Pasar Reguler dan Pasar Tunai mulai sesi I tanggal 29 Oktober 2026 {SAMPAI_LANJUT}",
        # GPSO Nov/Des 2024: potongan PDF memecah kata ("m ulai").
        f"di Pasar Reguler dan Pasar Tunai m ulai sesi I tanggal 29 Oktober 2026 {SAMPAI_LANJUT}",
        # MDIA 12 Agu 2026: sesi pra-pembukaan berjalan sebelum sesi I di hari yang sama.
        f"di Pasar Reguler dan Pasar Tunai mulai Sesi Pra-Pembukaan tanggal 29 Oktober 2026 {SAMPAI_LANJUT}",
    ],
    ids=["sesi-i", "kata-terpecah", "pra-pembukaan"],
)
def test_suspensi_lanjutan_mulai_sesi_tanggal_dikenali(berlaku: str) -> None:
    satu = pengumuman_idx.baca(_suspensi(berlaku=berlaku), nama_berkas="x.pdf", hari_ini=HARI_INI)

    baris = satu.baris()
    assert (baris.kode, baris.jenis, baris.tanggal_mulai, baris.tanggal_selesai) == (
        "PTSP", "suspensi", date(2026, 10, 29), None
    )


@pytest.mark.parametrize(
    ("isi", "sebab"),
    [
        (
            _suspensi(berlaku=f"di Pasar Reguler dan Pasar Tunai mulai sesi II tanggal 29 Oktober 2026 {SAMPAI_LANJUT}"),
            "sesi II",
        ),
        (
            _suspensi(
                berlaku="pada tanggal 29 Oktober 2026 di Pasar Reguler dan Pasar Tunai mulai sesi I tanggal "
                f"30 Oktober 2026 {SAMPAI_LANJUT}"
            ),
            "tepat satu, terbaca 2",
        ),
        # Papan Akselerasi FLMC 1 Nov 2023: ketentuan suspensi yang akan datang, bukan awal suspensi.
        (_suspensi(nomor=["No. Peng-S-00007", "/BEI.PLP-11-2023"]), "berformat lain"),
        # OCAP 1 Apr 2024: kabar suspensi Seluruh Pasar yang masih berjalan sejak 2023.
        (_suspensi(nomor=["No: Peng-SPT-00003", "/BEI.PP3/04-2024"]), "berformat lain"),
    ],
    ids=["sesi-ii", "dua-tanggal-berlaku", "nomor-papan-akselerasi", "nomor-pp3"],
)
def test_bentuk_suspensi_lanjutan_yang_tidak_dikenal_ditolak(isi: bytes, sebab: str) -> None:
    with pytest.raises(pengumuman_idx.GalatPengumuman, match=sebab):
        pengumuman_idx.baca(isi, nama_berkas="x.pdf", hari_ini=HARI_INI)


def test_nomor_yang_sama_dua_kali_dalam_satu_unggahan_ditolak() -> None:
    satu = pengumuman_idx.baca(_uma(), nama_berkas="a.pdf", hari_ini=HARI_INI)
    with pytest.raises(pengumuman_idx.GalatPengumuman, match="dua kali"):
        pengumuman_idx.pilah([satu, satu], [])


# ---------------------------------------------------------------------------------------
# Pembukaan kembali (UPT, K100): berkas nyata menulis isinya dengan font CID (`/Identity-H`) yang
# hanya terbaca lewat peta `/ToUnicode` — tiruan ini meniru bentuk itu, termasuk geseran kode glif
# (kode 0x0024 = "A") dan rujukan ke nomor SPT-nya.
# ---------------------------------------------------------------------------------------

#: Seperti berkas nyata: kode glif = kode karakter − 29 (`<0003>` = spasi … `<0061>` = "~").
GESER_GLIF = 29
CMAP_GESER = (
    "/CIDInit /ProcSet findresource begin\nbegincmap\n1 begincodespacerange\n<0000> <FFFF>\n"
    "endcodespacerange\n1 beginbfrange\n<0003> <0061> <0020>\nendbfrange\nendcmap\n"
)


def _glif(teks: str) -> str:
    return "".join(f"{ord(huruf) - GESER_GLIF:04X}" for huruf in teks)


def _pdf_cid(baris: list[str], *, cmap: str = CMAP_GESER, nama_font_kedua: bool = False) -> bytes:
    isi = "BT\n/F1 11 Tf\n1 0 0 1 70 800 Tm\n[(ANNOUNCEMENT)] TJ\nET\n"
    y = 780.0
    for satu in baris:
        isi += f"BT\n/F4 11.04 Tf\n1 0 0 1 70 {y} Tm\n[<{_glif(satu)}>] TJ\nET\n"
        y -= 14
    peta = zlib.compress(cmap.encode("latin-1"))
    halaman = zlib.compress(isi.encode("latin-1"))
    keluar = bytearray(b"%PDF-1.7\n")
    keluar += b"4 0 obj\n<</Type/Page/Resources<</Font<</F1 5 0 R/F4 6 0 R>>>>/Contents 8 0 R>>\nendobj\n"
    keluar += b"5 0 obj\n<</Type/Font/Subtype/TrueType/Encoding/WinAnsiEncoding>>\nendobj\n"
    keluar += b"6 0 obj\n<</Type/Font/Subtype/Type0/Encoding/Identity-H/ToUnicode 7 0 R>>\nendobj\n"
    keluar += b"7 0 obj\n<</Filter/FlateDecode>>\nstream\n" + peta + b"\nendstream\nendobj\n"
    keluar += b"8 0 obj\n<</Filter/FlateDecode>>\nstream\n" + halaman + b"\nendstream\nendobj\n"
    if nama_font_kedua:
        # Halaman lain memakai nama F4 untuk font dengan peta berbeda.
        lain = zlib.compress(b"begincmap\n1 beginbfchar\n<0003> <0041>\nendbfchar\nendcmap\n")
        keluar += b"9 0 obj\n<</Type/Page/Resources<</Font<</F4 10 0 R>>>>>>\nendobj\n"
        keluar += b"10 0 obj\n<</Type/Font/Subtype/Type0/ToUnicode 11 0 R>>\nendobj\n"
        keluar += b"11 0 obj\n<</Filter/FlateDecode>>\nstream\n" + lain + b"\nendstream\nendobj\n"
    return bytes(keluar)


def _upt(
    kode: str = "PTSP",
    *,
    dibuka: str = "dibuka kembali mulai sesi I tanggal",
    tanggal_buka: str = "30 Oktober 2026.",
    pasar: str = "di Pasar Reguler dan Pasar Tunai",
    rujukan: str = "Peng-SPT-00222/BEI.WAS/10-2026",
    nomor: str = "Peng-UPT-00230/BEI.WAS/10-2026",
) -> bytes:
    return _pdf_cid(
        [
            "PENGU MUMAN",  # berkas nyata (NIRO 24 Okt 2025) memecah judulnya
            nomor,
            f"Menunjuk Pengumuman Bursa {rujukan} tanggal 28 Oktober 2026 perihal",
            f"Penghentian Sementara Perdagangan (Suspensi) Saham PT Emiten Tbk ({kode}),",
            f"maka dengan ini diumumkan bahwa suspensi atas perdagangan saham PT Emiten Tbk ({kode})",
            f"{pasar} {dibuka}",
            tanggal_buka,
            "Demikian untuk diketahui.",
            "29 Oktober 2026",
            "Tembusan:",
        ]
    )


def test_teks_berfont_cid_diterjemahkan_lewat_tounicode() -> None:
    """Tanpa peta, glif CID hanya terhitung sebagai heksa tak terbaca — isi UPT hilang semua."""
    data = _pdf_cid(["Peng-UPT-00230/BEI.WAS/10-2026"])
    tanpa, heksa_tanpa = kalender.potongan_teks(data, di_mana="uji")
    dengan, heksa_dengan = kalender.potongan_teks(data, di_mana="uji", terjemahkan_font=True)

    assert [satu.teks for satu in tanpa] == ["ANNOUNCEMENT"] and heksa_tanpa == 1
    assert [satu.teks for satu in dengan] == ["ANNOUNCEMENT", "Peng-UPT-00230/BEI.WAS/10-2026"]
    assert heksa_dengan == 0


def test_nama_font_dengan_dua_peta_berbeda_ditolak() -> None:
    with pytest.raises(ingesti.GalatIngesti, match="dua peta ToUnicode"):
        kalender.potongan_teks(_pdf_cid(["Peng"], nama_font_kedua=True), di_mana="uji", terjemahkan_font=True)


def test_pembukaan_dibaca_dengan_tanggal_dibuka_dan_rujukan_spt() -> None:
    satu = pengumuman_idx.baca(_upt(), nama_berkas="upt.pdf", hari_ini=HARI_INI)

    assert (satu.pembukaan, satu.jenis, satu.kode, satu.nomor) == (
        True, "suspensi", "PTSP", "Peng-UPT-00230/BEI.WAS/10-2026"
    )
    assert (satu.tanggal_pengumuman, satu.tanggal_berlaku) == (date(2026, 10, 29), date(2026, 10, 30))
    assert satu.rujukan == ("Peng-SPT-00222/BEI.WAS/10-2026",)


def test_pembukaan_sesi_i_periodic_call_auction_dikenali() -> None:
    satu = pengumuman_idx.baca(
        _upt(dibuka="dibuka kembali mulai Sesi I Periodic Call Auction tanggal"),
        nama_berkas="upt.pdf",
        hari_ini=HARI_INI,
    )
    assert satu.tanggal_berlaku == date(2026, 10, 30)


@pytest.mark.parametrize(
    ("isi", "sebab"),
    [
        (_upt(dibuka="dibuka kembali mulai sesi II tanggal"), "sesi II"),
        (_upt(pasar="di Pasar Negosiasi"), "K39"),
        (_upt(dibuka="dibuka kembali pada", tanggal_buka="hari bursa berikutnya."), "dibuka kembali mulai"),
        (_upt(nomor="Peng-UPT"), "tidak terbaca utuh"),
        (_upt(tanggal_buka="29 Oktober 2026."), "tidak sesudah"),
        (_upt(rujukan="Peng-UMA-00352/BEI.WAS/10-2026"), "selain Peng-SPT"),
        (
            # Peta tanpa spasi dan huruf awal: glif yang tidak terbaca tidak boleh dilewati diam-diam.
            _pdf_cid(
                ["PENGUMUMAN", "Peng-UPT-00230/BEI.WAS/10-2026", "(PTSP)", "29 Oktober 2026"],
                cmap="begincmap\n1 beginbfrange\n<0010> <0061> <002D>\nendbfrange\nendcmap\n",
            ),
            "glif",
        ),
    ],
    ids=[
        "sesi-ii", "pasar-negosiasi", "kalimat-lain", "nomor-terpotong", "dibuka-hari-itu", "rujukan-uma",
        "glif-hilang",
    ],
)
def test_bentuk_pembukaan_yang_tidak_dikenal_ditolak(isi: bytes, sebab: str) -> None:
    with pytest.raises(pengumuman_idx.GalatPengumuman, match=sebab):
        pengumuman_idx.baca(isi, nama_berkas="upt.pdf", hari_ini=HARI_INI)


def _baris_ptsp(
    keterangan: str = "Pengumuman IDX PDF; Peng-SPT-00222/BEI.WAS/10-2026; diumumkan 2026-10-28",
) -> notasi.BarisNotasi:
    return notasi.BarisNotasi("PTSP", "suspensi", date(2026, 10, 29), None, keterangan)


def test_pembukaan_menutup_suspensi_sehari_sebelum_dibuka() -> None:
    """`saring` membaca `tanggal_selesai` inklusif: 29 Okt masih disuspensi, 30 Okt sudah bisa."""
    upt = pengumuman_idx.baca(_upt(), nama_berkas="upt.pdf", hari_ini=HARI_INI)

    pilahan = pengumuman_idx.pilah([upt], [_baris_ptsp()])

    assert pilahan.hasil.baris == ()
    (tutup,) = pilahan.hasil.penutupan
    assert (tutup.kode, tutup.tanggal_mulai, tutup.tanggal_selesai) == (
        "PTSP", date(2026, 10, 29), date(2026, 10, 29)
    )
    assert "Peng-SPT-00222" in tutup.keterangan and "Peng-UPT-00230" in tutup.keterangan
    assert pilahan.baru == (upt,)


def test_spt_dan_upt_dalam_satu_unggahan_menjadi_satu_baris_tertutup() -> None:
    spt = pengumuman_idx.baca(_suspensi(), nama_berkas="spt.pdf", hari_ini=HARI_INI)
    upt = pengumuman_idx.baca(_upt(), nama_berkas="upt.pdf", hari_ini=HARI_INI)

    pilahan = pengumuman_idx.pilah([upt, spt], [])

    assert pilahan.hasil.penutupan == ()
    (baris,) = pilahan.hasil.baris
    assert (baris.tanggal_mulai, baris.tanggal_selesai) == (date(2026, 10, 29), date(2026, 10, 29))


def test_pembukaan_yang_sudah_ditutup_api_lama_tidak_ditutup_lagi() -> None:
    """API lama menutup suspensi pada tanggal pengumuman pembukaannya (29 Okt)."""
    api = notasi.BarisNotasi(
        "PTSP", "suspensi", date(2026, 10, 28), date(2026, 10, 29), f"{notasi.PENANDA_AKTIVITAS}; PTSP"
    )
    upt = pengumuman_idx.baca(_upt(), nama_berkas="upt.pdf", hari_ini=HARI_INI)

    pilahan = pengumuman_idx.pilah([upt], [api])

    assert pilahan.sudah_ada == (upt,) and pilahan.hasil.penutupan == ()


@pytest.mark.parametrize(
    ("lama", "sebab"),
    [
        ([], "tidak ada suspensi terbuka"),
        (
            [_baris_ptsp(), notasi.BarisNotasi("PTSP", "suspensi", date(2026, 10, 1), None, "isian tangan")],
            "2 suspensi terbuka",
        ),
        ([_baris_ptsp("Pengumuman IDX PDF; Peng-SPT-00199/BEI.WAS/10-2026")], "merujuk"),
    ],
    ids=["tanpa-suspensi", "dua-terbuka", "rujukan-lain"],
)
def test_pembukaan_tanpa_tepat_satu_lawan_ditolak(lama: list[notasi.BarisNotasi], sebab: str) -> None:
    upt = pengumuman_idx.baca(_upt(), nama_berkas="upt.pdf", hari_ini=HARI_INI)
    with pytest.raises(pengumuman_idx.GalatPengumuman, match=sebab):
        pengumuman_idx.pilah([upt], lama)


def test_penutupan_baris_yang_tidak_terbuka_ditolak_penulis(tmp_path: Path) -> None:
    tertutup = notasi.BarisNotasi("PTSP", "suspensi", date(2026, 10, 29), date(2026, 10, 29), "x")
    hasil = notasi.HasilNotasi(
        tanggal_data=HARI_INI, baris=(), sumber="uji", hanya_menambah=True, penutupan=(tertutup,)
    )
    with pytest.raises(notasi.GalatNotasi, match="tepat satu baris terbuka"):
        notasi.tulis_berkas(hasil, tmp_path / "notasi-khusus.csv", diakses=HARI_INI)


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


def _tulis_konfigurasi(baris: list[notasi.BarisNotasi]) -> Path:
    """`notasi-khusus.csv` berisi baris lama (API + daftar notasi) seperti data kerja."""
    jalur = notasi.berkas_tujuan(lokasi.folder_konfigurasi())
    hasil = notasi.HasilNotasi(
        tanggal_data=date(2026, 10, 27), baris=tuple(baris), sumber="uji", jenis_dicakup=frozenset()
    )
    notasi.tulis_berkas(hasil, jalur, diakses=date(2026, 10, 27))
    return jalur


BARIS_LAMA = [
    # Suspensi terbuka dari API lama, emiten lain: tidak boleh ditutup oleh unggahan PDF.
    notasi.BarisNotasi(
        "ARKO", "suspensi", date(2026, 10, 27), None, f"{notasi.PENANDA_AKTIVITAS}; Suspend ARKO"
    ),
    notasi.BarisNotasi(
        "BSML", "uma", date(2026, 10, 27), date(2026, 11, 26),
        f"{notasi.PENANDA_AKTIVITAS}; UMA BSML; aturan UMA 30 hari",
    ),
]


def _permintaan(sambungan: sqlite3.Connection, berkas: list[tuple[str, bytes]]) -> tulis.PermintaanTulis:
    tersimpan = [(pengumuman_idx.simpan_unduhan(nama, isi), nama) for nama, isi in berkas]
    return tulis.permintaan_impor_pengumuman_idx(sambungan, berkas=tersimpan, hari_ini=HARI_INI)


def _aktif(sambungan: sqlite3.Connection) -> list[tuple[str, str, str]]:
    return [
        tuple(satu)
        for satu in sambungan.execute(
            "SELECT kode, jenis, tanggal_mulai FROM v_notasi_khusus_terkini "
            "WHERE tanggal_selesai IS NULL OR tanggal_selesai > '2026-10-29' ORDER BY kode, jenis"
        )
    ]


def test_unggahan_pdf_hanya_menambah_dan_tidak_menutup_baris_lama(sambungan: sqlite3.Connection) -> None:
    """Kumpulan PDF bukan daftar lengkap: suspensi ARKO yang tidak disebut tetap terbuka."""
    konfigurasi = _tulis_konfigurasi(BARIS_LAMA)
    permintaan = _permintaan(
        sambungan,
        [("20261028-UMA_COIN.pdf", _uma()), ("20261028-WAS_Suspensi_PTSP.pdf", _suspensi())],
    )
    assert "baru: 2" in permintaan.ringkasan and "ditutup: 0" in permintaan.ringkasan
    assert "PTSP" in permintaan.ringkasan and "29 Okt 2026" in permintaan.ringkasan

    hasil = tulis.jalankan_permintaan(permintaan, sambungan)

    assert hasil.berhasil, hasil.pesan
    assert _aktif(sambungan) == [
        ("ARKO", "suspensi", "2026-10-27"),
        ("BSML", "uma", "2026-10-27"),
        ("COIN", "uma", "2026-10-28"),
        ("PTSP", "suspensi", "2026-10-29"),
    ]
    tersimpan = {(satu.kode, satu.tanggal_selesai) for satu in notasi.baca(konfigurasi.parent)}
    assert ("ARKO", None) in tersimpan and ("PTSP", None) in tersimpan


def test_pengumuman_yang_sudah_tercatat_dari_api_tidak_dicatat_dua_kali(
    sambungan: sqlite3.Connection,
) -> None:
    """Baris API memakai tanggal pengumuman, PDF memakai tanggal berlaku: tetap satu peristiwa."""
    _tulis_konfigurasi(
        [notasi.BarisNotasi("PTSP", "suspensi", date(2026, 10, 28), None, f"{notasi.PENANDA_AKTIVITAS}; PTSP")]
    )
    permintaan = _permintaan(sambungan, [("20261028-WAS_Suspensi_PTSP.pdf", _suspensi())])
    assert "baru: 0" in permintaan.ringkasan and "sudah tercatat: 1" in permintaan.ringkasan


def test_pdf_yang_sama_diunggah_ulang_tidak_menambah_revisi(sambungan: sqlite3.Connection) -> None:
    _tulis_konfigurasi(BARIS_LAMA)
    pertama = _permintaan(sambungan, [("20261028-UMA_COIN.pdf", _uma())])
    assert tulis.jalankan_permintaan(pertama, sambungan).berhasil
    jumlah = sambungan.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0]

    kedua = _permintaan(sambungan, [("20261028-UMA_COIN.pdf", _uma())])
    assert "baru: 0" in kedua.ringkasan
    assert tulis.jalankan_permintaan(kedua, sambungan).berhasil
    assert sambungan.execute("SELECT COUNT(*) FROM notasi_khusus").fetchone()[0] == jumlah


def test_jadwal_menyebut_jalur_unggah_pdf_dan_tetap_tidak_dinilai(sambungan: sqlite3.Connection) -> None:
    butir = jadwal._suspensi_uma(sambungan)
    assert butir.status == jadwal.TIDAK_DINILAI
    assert "PDF" in butir.tindakan and "Impor & cadangan" in butir.tindakan
    assert "belum ada jalur unggah" not in butir.jadwal


def test_unggahan_pembukaan_menutup_suspensi_pdf_di_basis_data(
    sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Satu-satunya baris lama yang berubah adalah suspensi yang dibuka; ARKO tetap terbuka."""
    # Dua impor dalam satu detik berbagi `diketahui_pada`; jam tiruan maju sedetik tiap dibaca.
    awal = datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc)
    detik = iter(range(10**6))

    def waktu(momen: datetime | None = None) -> str:
        return db.waktu_iso(momen or awal + timedelta(seconds=next(detik)))

    monkeypatch.setattr(ingesti, "_waktu_iso", waktu)
    _tulis_konfigurasi(BARIS_LAMA)
    assert tulis.jalankan_permintaan(
        _permintaan(sambungan, [("20261028-WAS_Suspensi_PTSP.pdf", _suspensi())]), sambungan
    ).berhasil

    permintaan = _permintaan(sambungan, [("upt.pdf", _upt())])
    assert "baru: 0, ditutup: 1" in permintaan.ringkasan
    assert "dibuka kembali 30 Okt 2026" in permintaan.ringkasan
    hasil = tulis.jalankan_permintaan(permintaan, sambungan)

    assert hasil.berhasil, hasil.pesan
    assert sambungan.execute(
        "SELECT tanggal_selesai FROM v_notasi_khusus_terkini WHERE kode = 'PTSP' AND jenis = 'suspensi'"
    ).fetchone()[0] == "2026-10-29"
    # Baris awal + revisi penutupan: append-only, bukan ditimpa.
    assert sambungan.execute(
        "SELECT COUNT(*) FROM notasi_khusus WHERE kode = 'PTSP' AND jenis = 'suspensi'"
    ).fetchone()[0] == 2
    assert ("ARKO", "suspensi", "2026-10-27") in _aktif(sambungan)
