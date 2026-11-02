"""Unggahan Ringkasan Saham IDX (K95): disimpan mentah, dibaca, diimpor, dan diingatkan mingguan."""

from __future__ import annotations

import hashlib
import io
import sqlite3
import zipfile
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from mejasaham import berkas, db, ingesti, lokasi, mutu, tampilan, unggahan_idx
from mejasaham.ingesti import Emiten, HargaHarian, HariBursa, KumpulanData
from mejasaham.layar import tulis

WIB = timezone(timedelta(hours=7))
HARI_INI = date(2026, 10, 29)
ISI = b"PK\x03\x04 contoh berkas unduhan"

#: Judul kolom berkas nyata (Ringkasan Saham-20261028.xlsx, diunduh pengguna 29 Okt 2026).
JUDUL_IDX = (
    "No", "Kode Saham", "Nama Perusahaan", "Remarks", "Sebelumnya", "Open Price",
    "Tanggal Perdagangan Terakhir", "First Trade", "Tertinggi", "Terendah", "Penutupan", "Selisih",
    "Volume", "Nilai", "Frekuensi", "Index Individual", "Offer", "Offer Volume", "Bid",
    "Bid Volume", "Listed Shares", "Tradeble Shares", "Weight For Index", "Foreign Sell",
    "Foreign Buy", "Non Regular Volume", "Non Regular Value", "Non Regular Frequency",
)


def _huruf(indeks: int) -> str:
    teks = ""
    indeks += 1
    while indeks:
        indeks, sisa = divmod(indeks - 1, 26)
        teks = chr(65 + sisa) + teks
    return teks


def _xlsx(baris: list[dict[str, object]], judul: tuple[str, ...] = JUDUL_IDX) -> bytes:
    """XLSX berbentuk keluaran SheetJS seperti berkas IDX: teks `t="str"`, angka sel biasa."""
    def sel(r: int, k: int, nilai: object) -> str:
        rujukan = f"{_huruf(k)}{r}"
        if isinstance(nilai, str):
            return f'<c r="{rujukan}" t="str"><v>{nilai}</v></c>'
        return f'<c r="{rujukan}"><v>{nilai}</v></c>'

    isi_baris = ["<row r=\"1\">" + "".join(sel(1, k, j) for k, j in enumerate(judul)) + "</row>"]
    for r, satu in enumerate(baris, start=2):
        isi_baris.append(
            f'<row r="{r}">' + "".join(sel(r, k, satu.get(j, 0)) for k, j in enumerate(judul)) + "</row>"
        )
    lembar = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(isi_baris)}</sheetData></worksheet>"
    )
    keluaran = io.BytesIO()
    with zipfile.ZipFile(keluaran, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", lembar)
    return keluaran.getvalue()


def _baris_idx(kode: str, **ubah: object) -> dict[str, object]:
    dasar: dict[str, object] = {
        "Kode Saham": kode, "Nama Perusahaan": f"Emiten {kode} Tbk.", "Remarks": "--",
        "Tanggal Perdagangan Terakhir": "28 Okt 2026", "Sebelumnya": 1000, "Open Price": 1000,
        "Tertinggi": 1050, "Terendah": 990, "Penutupan": 1020, "Volume": 1000000,
        "Nilai": 1020000000,
    }
    dasar.update(ubah)
    return dasar


@pytest.fixture()
def sambungan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    koneksi = db.siapkan()
    try:
        yield koneksi
    finally:
        koneksi.close()


def _momen(hari: date) -> datetime:
    return datetime(hari.year, hari.month, hari.day, 17, 30, tzinfo=WIB)


def test_berkas_disimpan_mentah_dengan_sidik_dan_tidak_menyentuh_basis_data(
    sambungan: sqlite3.Connection,
) -> None:
    sebelum = sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0]

    hasil = unggahan_idx.simpan("Ringkasan Saham-20261029.xlsx", ISI, momen=_momen(HARI_INI))

    assert not hasil.sudah_ada
    assert hasil.unggahan.berkas.read_bytes() == ISI
    assert hasil.unggahan.berkas.name == "20261029T173000_Ringkasan_Saham-20261029.xlsx"
    assert hasil.unggahan.sha256 == hashlib.sha256(ISI).hexdigest()
    assert unggahan_idx.daftar() == (hasil.unggahan,)
    assert "belum masuk basis data" in hasil.ringkas()
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == sebelum


def test_isi_yang_sama_tidak_disimpan_dua_kali(sambungan: sqlite3.Connection) -> None:
    pertama = unggahan_idx.simpan("a.xlsx", ISI, momen=_momen(HARI_INI))
    kedua = unggahan_idx.simpan("nama-lain.xlsx", ISI, momen=_momen(HARI_INI + timedelta(days=1)))

    assert kedua.sudah_ada and kedua.unggahan == pertama.unggahan
    assert len(unggahan_idx.daftar()) == 1
    assert len([p for p in unggahan_idx.folder().iterdir() if p.name != unggahan_idx.NAMA_DAFTAR]) == 1


@pytest.mark.parametrize(
    ("nama", "isi", "sebab"),
    [
        ("ringkasan.xlsx", b"", "kosong"),
        ("ringkasan.pdf", ISI, "bukan berkas tabel"),
        ("ringkasan.xlsx", b"x" * (unggahan_idx.BATAS_BAIT + 1), "lebih dari batas"),
    ],
    ids=["kosong", "pdf", "terlalu-besar"],
)
def test_unggahan_yang_jelas_salah_ditolak_tanpa_menulis(
    sambungan: sqlite3.Connection, nama: str, isi: bytes, sebab: str
) -> None:
    with pytest.raises(unggahan_idx.GalatUnggahan, match=sebab):
        unggahan_idx.simpan(nama, isi)
    assert not unggahan_idx.folder().exists()


def test_nama_berkas_tidak_bisa_keluar_dari_folder_unggahan(sambungan: sqlite3.Connection) -> None:
    hasil = unggahan_idx.simpan("..\\..\\konfigurasi\\emiten.xlsx", ISI, momen=_momen(HARI_INI))
    assert hasil.unggahan.berkas.parent == unggahan_idx.folder()
    assert hasil.unggahan.berkas.name.endswith("_emiten.xlsx")


def test_pengingat_muncul_bila_belum_ada_unggahan_dan_cek_belum_tepat_waktu(
    sambungan: sqlite3.Connection,
) -> None:
    teks = unggahan_idx.pengingat(sambungan, HARI_INI)
    assert teks is not None and "belum pernah ada unggahan" in teks


@pytest.mark.parametrize(
    ("umur", "isi_pengingat"), [(7, "sudah diunggah"), (8, "Waktunya mengunduh")]
)
def test_pengingat_mingguan_dihitung_dari_unggahan_terakhir_inklusif_tujuh_hari(
    sambungan: sqlite3.Connection, umur: int, isi_pengingat: str
) -> None:
    """≤ 7 hari: yang tertunda impornya; lebih tua: waktunya mengunduh lagi."""
    unggahan_idx.simpan("a.xlsx", ISI, momen=_momen(HARI_INI - timedelta(days=umur)))
    teks = unggahan_idx.pengingat(sambungan, HARI_INI)
    assert teks is not None and isi_pengingat in teks
    if umur > 7:
        assert f"{umur} hari lalu" in teks


def test_pengingat_diam_bila_cek_sumber_kedua_tepat_waktu(
    sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        mutu,
        "keadaan_cek_sumber_kedua",
        lambda *_, **__: mutu.KeadaanCekSumberKedua(status=mutu.STATUS_TEPAT_WAKTU),
    )
    assert unggahan_idx.pengingat(sambungan, HARI_INI) is None


# -- pembaca berkas (bentuk dari contoh nyata, K95) ---------------------------------------


def _unggah_xlsx(isi: bytes) -> unggahan_idx.Unggahan:
    return unggahan_idx.simpan("Ringkasan Saham-20261028.xlsx", isi, momen=_momen(HARI_INI)).unggahan


def test_baca_ringkasan_saham_mengambil_kolom_harga_dan_nol_berarti_tidak_ada(
    sambungan: sqlite3.Connection,
) -> None:
    unggahan = _unggah_xlsx(
        _xlsx(
            [
                _baris_idx("AADI", **{"Open Price": 11750, "Tertinggi": 11850, "Terendah": 11425,
                                      "Penutupan": 11650, "Volume": 12253000, "Nilai": 142560192500}),
                # Tanpa harga pembukaan (ZONE 28 Okt 2026): Open Price & First Trade 0.
                _baris_idx("ZONE", **{"Open Price": 0, "First Trade": 0, "Penutupan": 695}),
                # Tanpa transaksi: tertinggi/terendah/volume 0, penutupan = sebelumnya.
                _baris_idx("FISH", **{"Open Price": 0, "Tertinggi": 0, "Terendah": 0, "Volume": 0,
                                      "Nilai": 0, "Penutupan": 10350}),
            ]
        )
    )

    isi = unggahan_idx.baca(unggahan.berkas)

    assert isi.tanggal == date(2026, 10, 28)
    baris = {satu["kode"]: satu for satu in isi.baris}
    assert baris["AADI"] == {
        "kode": "AADI", "tanggal": "2026-10-28", "open": "11750", "high": "11850", "low": "11425",
        "close": "11650", "volume": "12253000", "nilai": "142560192500",
    }
    assert baris["ZONE"]["open"] == "" and baris["ZONE"]["close"] == "695"
    assert (baris["FISH"]["high"], baris["FISH"]["low"], baris["FISH"]["volume"]) == ("", "", "0")


@pytest.mark.parametrize(
    ("isi", "sebab"),
    [
        (b"bukan zip", "tidak terbaca sebagai XLSX"),
        (_xlsx([_baris_idx("AADI")], judul=JUDUL_IDX[:10]), "Penutupan"),
        (_xlsx([_baris_idx("AADI"), _baris_idx("AALI", **{"Tanggal Perdagangan Terakhir": "27 Okt 2026"})]),
         "2 tanggal perdagangan"),
        (_xlsx([_baris_idx("AADI", Penutupan="11650.5")]), "bukan bilangan bulat"),
        (_xlsx([_baris_idx("AADI", Penutupan=0)]), "penutupan AADI kosong atau nol"),
        (_xlsx([_baris_idx("AADI"), _baris_idx("AADI")]), "muncul dua kali"),
        (_xlsx([_baris_idx("AADI", **{"Tanggal Perdagangan Terakhir": "2026-10-28"})]), "28 Okt 2026"),
    ],
    ids=["bukan-xlsx", "kolom-hilang", "dua-tanggal", "pecahan", "tutup-nol", "kode-ganda", "tanggal-iso"],
)
def test_bentuk_berkas_yang_tidak_dikenal_ditolak_dengan_sebabnya(
    sambungan: sqlite3.Connection, isi: bytes, sebab: str
) -> None:
    unggahan = _unggah_xlsx(isi)
    with pytest.raises(unggahan_idx.GalatUnggahan, match=sebab):
        unggahan_idx.baca(unggahan.berkas)


def test_folder_impor_lolos_validasi_impor_biasa_dengan_label_pembanding(
    sambungan: sqlite3.Connection,
) -> None:
    unggahan = _unggah_xlsx(_xlsx([_baris_idx("AADI"), _baris_idx("ZONE", **{"Open Price": 0})]))

    folder = unggahan_idx.siapkan_folder_impor(unggahan, unggahan_idx.baca(unggahan.berkas))
    harga = {satu.kode: satu for satu in berkas.baca_folder(folder).kumpulan.harga_harian}

    assert set(harga) == {"AADI", "ZONE"}
    assert harga["ZONE"].open is None and harga["ZONE"].close == 1020
    assert {satu.sumber for satu in harga.values()} == {unggahan_idx.SUMBER_IDX}
    assert {satu.penyesuaian_sumber for satu in harga.values()} == {ingesti.PENYESUAIAN_TIDAK_DISESUAIKAN}


def _snapshot(sambungan: sqlite3.Connection, tanggal: date) -> None:
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=ingesti.SUMBER_YFINANCE,
            emiten=(Emiten(kode="AADI", nama="Emiten AADI", sumber="uji"),),
            harga_harian=(HargaHarian(kode="AADI", tanggal=tanggal, close=1000, volume=1000),),
            kalender_bursa=(HariBursa(tanggal=tanggal, hari_bursa=True),),
        ),
        tanggal_data=tanggal,
        # Waktu lampau: impor sesudahnya tidak boleh jatuh pada detik yang sama (T12).
        momen=datetime(tanggal.year, tanggal.month, tanggal.day, 18, tzinfo=WIB),
    )


def test_impor_ditolak_bila_tanggal_berkas_bukan_tanggal_snapshot(sambungan: sqlite3.Connection) -> None:
    _snapshot(sambungan, date(2026, 10, 27))
    unggahan = _unggah_xlsx(_xlsx([_baris_idx("AADI")]))

    with pytest.raises(tulis.GalatTulis, match="Perbarui data"):
        tulis.permintaan_impor_ringkasan_idx(sambungan, unggahan=unggahan)
    assert not unggahan_idx.folder_impor(unggahan).exists(), "tidak ada yang disiapkan sebelum lolos"


def test_impor_menulis_harga_pembanding_lalu_mencatat_cek_sumber_kedua(
    sambungan: sqlite3.Connection,
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    unggahan = _unggah_xlsx(_xlsx([_baris_idx("AADI", Penutupan=1000)]))

    permintaan = tulis.permintaan_impor_ringkasan_idx(sambungan, unggahan=unggahan)
    assert unggahan_idx.SUMBER_IDX in permintaan.ringkasan and "28 Okt 2026" in permintaan.ringkasan
    hasil = tulis.jalankan_permintaan(permintaan, sambungan)

    assert hasil.berhasil, hasil.pesan
    assert "Perbandingan sumber kedua" in hasil.pesan
    baris = sambungan.execute(
        "SELECT sumber, close FROM v_harga_harian_terkini WHERE kode = 'AADI' AND tanggal = '2026-10-28'"
        " ORDER BY sumber"
    ).fetchall()
    assert [tuple(satu) for satu in baris] == [
        (unggahan_idx.SUMBER_IDX, 1000),
        (ingesti.SUMBER_YFINANCE, 1000),
    ], "harga pembanding hidup berdampingan, tidak menimpa harga utama"
    cek = sambungan.execute("SELECT sumber_pembanding FROM cek_sumber_kedua").fetchall()
    assert [satu[0] for satu in cek] == [unggahan_idx.SUMBER_IDX]


# ---------------------------------------------------------------------------------------
# K97 langkah 4: tanggal lampau dan beberapa berkas sekaligus
# ---------------------------------------------------------------------------------------


def _unggah_tanggal(hari: date, *, close: int = 1000, jam: int = 0) -> unggahan_idx.Unggahan:
    """Berkas Ringkasan Saham bertanggal `hari`, diunggah pada `HARI_INI` (jam beda = isi beda)."""
    teks = f"{hari.day:02d} {tampilan.BULAN_SINGKAT[hari.month - 1]} {hari.year}"
    isi = _xlsx([_baris_idx("AADI", Penutupan=close, **{"Tanggal Perdagangan Terakhir": teks})])
    momen = _momen(HARI_INI) + timedelta(minutes=hari.day + 31 * jam)
    return unggahan_idx.simpan(f"Ringkasan Saham-{hari:%Y%m%d}.xlsx", isi, momen=momen).unggahan


def _tanggal_data_terakhir(sambungan: sqlite3.Connection) -> str:
    return sambungan.execute(
        "SELECT tanggal_data FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
    ).fetchone()[0]


def test_impor_tanggal_lampau_diterima_tanpa_memundurkan_tanggal_snapshot(
    sambungan: sqlite3.Connection,
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    unggahan = _unggah_tanggal(date(2026, 10, 27))

    hasil = tulis.jalankan_permintaan(
        tulis.permintaan_impor_ringkasan_idx(sambungan, unggahan=unggahan), sambungan
    )

    assert hasil.berhasil, hasil.pesan
    assert _tanggal_data_terakhir(sambungan) == "2026-10-28", "snapshot baru tidak boleh mundur"
    baris = sambungan.execute(
        "SELECT COUNT(*) FROM harga_harian WHERE sumber = ? AND tanggal = '2026-10-27'",
        (unggahan_idx.SUMBER_IDX,),
    ).fetchone()[0]
    assert baris == 1
    assert "tidak dijalankan" in hasil.pesan, "tanpa berkas bertanggal snapshot, cek tidak dijalankan"
    assert sambungan.execute("SELECT COUNT(*) FROM cek_sumber_kedua").fetchone()[0] == 0


def test_beberapa_berkas_diimpor_dalam_satu_konfirmasi_dan_satu_snapshot(
    sambungan: sqlite3.Connection,
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    sebelum = sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0]
    unggahan = (_unggah_tanggal(date(2026, 10, 27)), _unggah_tanggal(date(2026, 10, 28)))

    permintaan = tulis.permintaan_impor_ringkasan_idx(sambungan, unggahan=unggahan)
    assert "27 Okt 2026" in permintaan.ringkasan and "28 Okt 2026" in permintaan.ringkasan
    hasil = tulis.jalankan_permintaan(permintaan, sambungan)

    assert hasil.berhasil, hasil.pesan
    assert sambungan.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] == sebelum + 1
    tanggal = [
        satu[0]
        for satu in sambungan.execute(
            "SELECT tanggal FROM harga_harian WHERE sumber = ? ORDER BY tanggal",
            (unggahan_idx.SUMBER_IDX,),
        )
    ]
    assert tanggal == ["2026-10-27", "2026-10-28"]
    assert sambungan.execute("SELECT COUNT(*) FROM cek_sumber_kedua").fetchone()[0] == 1


def test_dua_berkas_bertanggal_sama_dalam_satu_impor_ditolak(sambungan: sqlite3.Connection) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    pertama = _unggah_tanggal(date(2026, 10, 27))
    kedua = _unggah_tanggal(date(2026, 10, 27), close=1010, jam=1)

    with pytest.raises(tulis.GalatTulis, match="bertanggal sama"):
        tulis.permintaan_impor_ringkasan_idx(sambungan, unggahan=(pertama, kedua))


def test_satu_berkas_di_depan_snapshot_menolak_seluruh_impor(sambungan: sqlite3.Connection) -> None:
    _snapshot(sambungan, date(2026, 10, 27))
    unggahan = (_unggah_tanggal(date(2026, 10, 26)), _unggah_tanggal(date(2026, 10, 28)))

    with pytest.raises(tulis.GalatTulis, match="Perbarui data"):
        tulis.permintaan_impor_ringkasan_idx(sambungan, unggahan=unggahan)


def test_antrean_impor_memilih_unggahan_terbaru_per_tanggal_dan_memisahkan_yang_menunggu(
    sambungan: sqlite3.Connection,
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    lama = _unggah_tanggal(date(2026, 10, 27))
    baru = _unggah_tanggal(date(2026, 10, 27), close=1010, jam=1)
    tepat = _unggah_tanggal(date(2026, 10, 28))
    depan = _unggah_tanggal(date(2026, 10, 29))
    rusak = unggahan_idx.simpan("rusak.xlsx", b"bukan zip", momen=_momen(HARI_INI)).unggahan

    antrean = unggahan_idx.antrean_impor(sambungan)

    assert [(u, t) for u, t in antrean.siap] == [(baru, date(2026, 10, 27)), (tepat, date(2026, 10, 28))]
    assert antrean.diganti == (lama,)
    assert antrean.menunggu == ((depan, date(2026, 10, 29)),)
    assert [u for u, _ in antrean.tak_terbaca] == [rusak]


def test_antrean_impor_melewati_tanggal_yang_sudah_ada_di_basis_data(
    sambungan: sqlite3.Connection,
) -> None:
    _snapshot(sambungan, date(2026, 10, 28))
    sudah = _unggah_tanggal(date(2026, 10, 27))
    tulis.jalankan_permintaan(tulis.permintaan_impor_ringkasan_idx(sambungan, unggahan=sudah), sambungan)
    belum = _unggah_tanggal(date(2026, 10, 28))

    antrean = unggahan_idx.antrean_impor(sambungan)

    assert antrean.siap == ((belum, date(2026, 10, 28)),)


def test_tanggal_berkas_dibaca_sekali_lalu_diingat(
    sambungan: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    unggahan = _unggah_tanggal(date(2026, 10, 27))
    assert unggahan_idx.tanggal_berkas(unggahan) == date(2026, 10, 27)

    def jangan_baca(_jalur: Path) -> unggahan_idx.RingkasanSaham:
        raise AssertionError("tanggal berkas yang sama dibaca ulang")

    monkeypatch.setattr(unggahan_idx, "baca", jangan_baca)
    assert unggahan_idx.tanggal_berkas(unggahan) == date(2026, 10, 27)
