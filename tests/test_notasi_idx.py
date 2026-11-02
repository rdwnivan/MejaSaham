"""Uji pengambil notasi khusus IDX (P22) — `mejasaham/notasi.py`.

Yang diuji adalah janji-janji yang membuat daftar ini bisa dipakai berhitung:

* **Hurufnya tergabung, dan `X` harus tetap dikenali.** Pola halaman itu berbunyi
  `FormatEmitenCode:"BOSS.BELYX"` — artinya huruf B, E, L, Y, X, bukan satu notasi bernama
  "BELYX". Membacanya sebagai satu token membuat `X` (papan pemantauan khusus) tidak pernah
  dikenali dan daftarnya tampak kosong — cacat yang benar-benar terjadi saat modul ini ditulis,
  dan uji ini yang menjaganya.
* **Tanggalnya dari halaman, bukan dari jam sistem.** Halaman tanpa tanggal ditolak; halaman yang
  menyatakan dua tanggal berbeda juga ditolak, bukan diringkas. Baris yang bertanggal tebakan akan
  membuat `potret` menganggapnya diketahui pada waktu yang salah.
* **"Tidak ada notasi" dan "halamannya berubah bentuk" adalah dua keadaan berbeda.** Halaman tanpa
  satu baris pun menolak, sebab melaporkannya sebagai daftar kosong akan terbaca sebagai kabar
  baik — dan itu kebalikan dari kebenarannya (aturan keras 7).
* **Berkasnya bertambah, dan yang tidak lagi tercantum ditutup.** Sumbernya hanya menyajikan
  keadaan terkini tanpa arsip, jadi riwayat yang hilang tidak bisa dibangun ulang (PRD 9.12).
  Yang ditutup hanya baris yang ditulis pengambil ini; baris isian tangan tidak disentuh.
* **Bulat-baliknya sampai ke perhitungan**: berkas yang ditulis harus terbaca pembaca impor, dan
  begitu masuk basis data, `--saring` berhenti menyebut daftarnya "PERINGKAT SEMENTARA" —
  itulah gunanya seluruh pekerjaan ini (PRD 7.3, K19).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest

from mejasaham import berkas, db, ingesti, lokasi, notasi, pengatur, potret, saring
from mejasaham.ingesti import (
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    Emiten,
    HargaHarian,
    KumpulanData,
    NotasiKhusus,
)

TANGGAL = date(2026, 9, 30)
MOMEN = datetime(2026, 10, 1, 9, 0, 0)
HARI_INI = date(2026, 10, 1)


#: Payload tiruan yang **meniru bentuk aslinya** (10 Okt 2026): objek baris dengan
#: `FormatEmitenCode` berisi kode + huruf tergabung, dan satu literal tanggal data di ujung
#: payload sebagai argumen fungsi — persis seperti halaman Nuxt sungguhan.
PAYLOAD = """
window.__NUXT__=(function(a,b,c){return {data:{ah:[
{Id:1,EmitenCode:"BOSS",Notation:"B,E,L,Y,X",Date:b,Description:"L : ...",FormatEmitenCode:"BOSS.BELYX",Name:"Boss Inc"},
{Id:2,EmitenCode:"TRAM",Notation:"L,Y,F",Date:b,Description:"L : ...",FormatEmitenCode:"TRAM.LYF",Name:"Tram Inc"},
{Id:3,EmitenCode:"GOTOM",Notation:"N",Date:b,Description:"N : ...",FormatEmitenCode:"GOTOM.N",Name:"-"},
{Id:4,EmitenCode:"ABBA",Notation:"X",Date:b,Description:"X : ...",FormatEmitenCode:"ABBA.X",Name:"Abba Inc"}
],judul:a}}}( "", "2026-10-08T00:00:00", "Indonesia"));
"""


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


def _emiten(kode: str) -> Emiten:
    return Emiten(kode=kode, nama=f"Emiten {kode}", sumber="uji-rujukan")


def _deret(kode: str, hari: int = 24) -> tuple[HargaHarian, ...]:
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - __import__("datetime").timedelta(days=hari - 1 - i),
            open=1_000,
            high=1_020,
            low=980,
            close=1_000,
            volume=10_000_000,
            nilai=10_000_000_000,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(hari)
    )


# ---------------------------------------------------------------------------------------
# Penguraian halaman
# ---------------------------------------------------------------------------------------


def test_huruf_notasi_yang_tergabung_dibaca_per_huruf() -> None:
    """`BOSS.BELYX` = B, E, L, Y, X — dan karena ada X, ia masuk papan pemantauan khusus."""
    hasil = notasi.urai(PAYLOAD)

    per_kode = {satu.kode: satu for satu in hasil.baris}
    assert per_kode["BOSS"].jenis == notasi.JENIS_PAPAN_PEMANTAUAN
    assert per_kode["BOSS"].huruf == "B,E,L,X,Y"
    assert per_kode["ABBA"].jenis == notasi.JENIS_PAPAN_PEMANTAUAN, "notasi tunggal X juga papan"
    assert per_kode["TRAM"].jenis == notasi.JENIS_LAINNYA, "tanpa X berarti bukan papan pemantauan"
    assert per_kode["GOTOM"].jenis == notasi.JENIS_LAINNYA
    assert hasil.jumlah_papan_pemantauan == 2
    assert hasil.kode_papan_pemantauan == ("ABBA", "BOSS")


def test_tanggal_data_diambil_dari_halaman() -> None:
    """Bukan dari jam sistem: halaman menyatakannya, dan itu yang dipakai."""
    hasil = notasi.urai(PAYLOAD)

    assert hasil.tanggal_data == date(2026, 10, 8)
    assert all(satu.tanggal_mulai == date(2026, 10, 8) for satu in hasil.baris)
    assert all("tanggal MULAI notasi tidak dinyatakan" in satu.keterangan for satu in hasil.baris)
    assert all(notasi.PENANDA_BARIS in satu.keterangan for satu in hasil.baris)


def test_halaman_tanpa_baris_ditolak_bukan_dianggap_kosong() -> None:
    """Daftar kosong akan terbaca sebagai kabar baik; halaman yang berubah bentuk harus berisik."""
    with pytest.raises(notasi.GalatNotasi, match="tidak memuat satu baris pun"):
        notasi.urai("<html><body>halaman lain</body></html>")


def test_halaman_tanpa_tanggal_ditolak() -> None:
    with pytest.raises(notasi.GalatNotasi, match="tidak menyatakan tanggal"):
        notasi.urai('FormatEmitenCode:"BOSS.BELYX"')


def test_halaman_dengan_dua_tanggal_ditolak() -> None:
    """Menebak mana yang berlaku adalah persis yang dilarang aturan keras 1."""
    teks = PAYLOAD.replace("2026-10-08T00:00:00", "2026-10-08T00:00:00").replace(
        "judul:a}}", 'judul:a, lain:"2026-10-07T00:00:00"}}'
    )

    with pytest.raises(notasi.GalatNotasi, match="2 tanggal berbeda"):
        notasi.urai(teks)


# ---------------------------------------------------------------------------------------
# Berkas: bertambah, menutup yang hilang, idempoten
# ---------------------------------------------------------------------------------------


def test_berkas_bertambah_dan_yang_hilang_ditutup(tmp_path: Path) -> None:
    jalur = tmp_path / "notasi-khusus.csv"
    pertama = notasi.urai(PAYLOAD)

    hasil_pertama = notasi.tulis_berkas(pertama, jalur, diakses=HARI_INI)

    assert hasil_pertama.baru == 4 and hasil_pertama.ditutup == 0
    assert hasil_pertama.papan_pemantauan == 2
    assert notasi.baca(tmp_path) == pytest.approx(notasi.baca(tmp_path))  # terbaca ulang

    # Pengambilan berikutnya: PPK-nya tinggal satu, dan tanggal datanya bergeser satu hari.
    lanjut = notasi.urai(
        PAYLOAD.replace("2026-10-08T00:00:00", "2026-11-01T00:00:00").replace(
            '{Id:2,EmitenCode:"TRAM",Notation:"L,Y,F",Date:b,Description:"L : ...",FormatEmitenCode:"TRAM.LYF",Name:"Tram Inc"},',
            "",
        )
    )
    hasil_kedua = notasi.tulis_berkas(lanjut, jalur, diakses=date(2026, 11, 1))

    assert hasil_kedua.baru == 3, "tiga kode masih tercantum dengan tanggal data yang baru"
    assert hasil_kedua.ditutup == 1, "hanya TRAM yang tidak lagi tercantum di halaman itu"
    semua = notasi.baca(tmp_path)
    ditutup = [satu for satu in semua if satu.tanggal_selesai == date(2026, 11, 1)]
    assert [satu.kode for satu in ditutup] == ["TRAM"]
    assert all("TIDAK LAGI tercantum" in satu.keterangan for satu in ditutup)
    assert [satu.kode for satu in notasi.baca(tmp_path)] == sorted(
        satu.kode for satu in notasi.baca(tmp_path)
    ), "barisnya ditulis berurutan menurut kode, supaya berkasnya deterministik (A5)"


def test_pengambilan_ulang_pada_tanggal_yang_sama_tidak_menambah_baris(tmp_path: Path) -> None:
    """Idempoten: menjalankan perintah yang sama dua kali tidak boleh menumpuk salinan."""
    jalur = tmp_path / "notasi-khusus.csv"
    hasil = notasi.urai(PAYLOAD)

    notasi.tulis_berkas(hasil, jalur, diakses=HARI_INI)
    kedua = notasi.tulis_berkas(hasil, jalur, diakses=HARI_INI)

    assert kedua.baru == 0 and kedua.ditutup == 0
    assert len(notasi.baca(tmp_path)) == 4


def test_baris_isian_tangan_tidak_ditutup_otomatis(tmp_path: Path) -> None:
    """Sumber lain (mis. salinan pengumuman sekuritas) tidak boleh ditutup oleh pengambil ini."""
    jalur = tmp_path / "notasi-khusus.csv"
    jalur.write_text(
        "kode;jenis;tanggal_mulai;tanggal_selesai;keterangan\n"
        "ZZZZ;suspensi;2026-01-01;;disalin dari pengumuman sekuritas\n",
        encoding="utf-8",
    )

    notasi.tulis_berkas(notasi.urai(PAYLOAD), jalur, diakses=HARI_INI)

    semua = {satu.kode: satu for satu in notasi.baca(tmp_path)}
    assert semua["ZZZZ"].tanggal_selesai is None, "baris isian tangan tidak disentuh"
    assert semua["ZZZZ"].jenis == "suspensi"
    assert len(semua) == 5


def test_berkas_separuh_tidak_ditinggalkan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    jalur = tmp_path / "notasi-khusus.csv"

    def gagal_ganti(*_args: object, **_kwargs: object) -> None:
        raise OSError("gagal disengaja saat mengganti berkas")

    monkeypatch.setattr(notasi.shutil, "move", gagal_ganti)

    with pytest.raises(OSError, match="gagal disengaja"):
        notasi.tulis_berkas(notasi.urai(PAYLOAD), jalur, diakses=HARI_INI)

    assert not jalur.exists()
    assert sorted(satu.name for satu in tmp_path.glob("notasi-khusus.csv.tmp-*")) == []


def test_aktivitas_idx_menutup_suspensi_saat_ada_pengumuman_pembukaan_kembali(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suspensi = [
        {"Kode": "AAAA", "Info_Type": "UPT", "Date": "2026-03-01T00:00:00", "Judul": "Buka"},
        {"Kode": "AAAA", "Info_Type": "SPT", "Date": "2026-02-01T02:00:00", "Judul": "Suspensi koreksi"},
        {"Kode": "AAAA", "Info_Type": "SPT", "Date": "2026-02-01T00:00:00", "Judul": "Suspensi"},
    ]
    uma = [
        {"CompanyID": "BBBB", "UMADate": "2026-10-01T00:00:00", "Judul": "UMA"},
        {"CompanyID": "BBBB", "UMADate": "2026-10-01T00:00:00", "Judul": "UMA koreksi"},
    ]
    respons = iter((suspensi, uma))
    monkeypatch.setattr(notasi, "_unduh_daftar_aktivitas", lambda *args, **kwargs: next(respons))

    hasil = notasi.unduh_aktivitas(tanggal_data=date(2026, 10, 11), jeda=0)

    aktif = next(satu for satu in hasil.baris if satu.kode == "AAAA")
    uma_baris = next(satu for satu in hasil.baris if satu.kode == "BBBB")
    assert sum(1 for satu in hasil.baris if satu.kode == "BBBB") == 1
    assert aktif.tanggal_mulai == date(2026, 2, 1)
    assert aktif.tanggal_selesai == date(2026, 3, 1)
    assert uma_baris.tanggal_selesai == date(2026, 10, 31)


def test_aktivitas_idx_melaporkan_pengumuman_suspensi_multi_kode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respons = iter(
        ([
            {"Kode": ">1 Kode", "Info_Type": "SPT", "Date": "2026-03-01", "Judul": "Suspensi multi"},
            {"Kode": "AAAA", "Info_Type": "SPT", "Date": "2026-03-01", "Judul": "Suspensi"},
         ],
         [{"CompanyID": "BBBB", "UMADate": "2026-03-01", "Judul": "UMA"}])
    )
    monkeypatch.setattr(notasi, "_unduh_daftar_aktivitas", lambda *args, **kwargs: next(respons))

    hasil = notasi.unduh_aktivitas(tanggal_data=date(2026, 10, 11), jeda=0)

    assert hasil.pengumuman_multi_kode == 1
    suspensi = next(satu for satu in hasil.baris if satu.jenis == "suspensi")
    assert notasi.PENANDA_NOTASI_TIDAK_LENGKAP in suspensi.keterangan
    assert not saring.notasi_terverifikasi((NotasiKhusus(
        kode=suspensi.kode,
        jenis=suspensi.jenis,
        tanggal_mulai=suspensi.tanggal_mulai,
        tanggal_selesai=suspensi.tanggal_selesai,
        keterangan=suspensi.keterangan,
    ),))


def test_aktivitas_idx_mencatat_pembukaan_kembali_tanpa_pasangan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respons = iter(
        ([{"Kode": "AAAA", "Info_Type": "UPT", "Date": "2026-03-01", "Judul": "Buka"}],
         [{"CompanyID": "BBBB", "UMADate": "2026-03-01", "Judul": "UMA"}])
    )
    monkeypatch.setattr(notasi, "_unduh_daftar_aktivitas", lambda *args, **kwargs: next(respons))

    hasil = notasi.unduh_aktivitas(tanggal_data=date(2026, 10, 11), jeda=0)
    assert hasil.pembukaan_tanpa_awal == 1


def test_aktivitas_idx_menolak_jeda_negatif() -> None:
    with pytest.raises(notasi.GalatNotasi, match="jeda tidak boleh negatif"):
        notasi.unduh_aktivitas(tanggal_data=date(2026, 10, 11), jeda=-1)


def test_penulisan_mengganti_suspensi_aktif_dengan_riwayat_yang_sudah_ditutup(
    tmp_path: Path,
) -> None:
    jalur = tmp_path / "notasi-khusus.csv"
    aktif = notasi.HasilNotasi(
        date(2026, 3, 1),
        (notasi._baris_aktivitas("AAAA", "suspensi", date(2026, 2, 1), None, "Suspensi"),),
        "IDX",
    )
    notasi.tulis_berkas(aktif, jalur, diakses=date(2026, 3, 1))
    ditutup = notasi.HasilNotasi(
        date(2026, 3, 2),
        (notasi._baris_aktivitas("AAAA", "suspensi", date(2026, 2, 1), date(2026, 3, 1), "Suspensi → Buka"),),
        "IDX",
    )

    notasi.tulis_berkas(ditutup, jalur, diakses=date(2026, 3, 2))

    baris = [satu for satu in notasi.baca(tmp_path) if satu.kode == "AAAA"]
    assert len(baris) == 1
    assert baris[0].tanggal_selesai == date(2026, 3, 1)


def test_penulisan_memperbarui_penanda_cakupan_sumber_di_baris_otomatis(
    tmp_path: Path,
) -> None:
    jalur = tmp_path / "notasi-khusus.csv"
    awal = notasi.HasilNotasi(
        date(2026, 3, 1),
        (notasi._baris_aktivitas("AAAA", "suspensi", date(2026, 2, 1), None, "Suspensi"),),
        "IDX",
    )
    notasi.tulis_berkas(awal, jalur, diakses=date(2026, 3, 1))
    baris = notasi._baris_aktivitas("AAAA", "suspensi", date(2026, 2, 1), None, "Suspensi")
    revisi = notasi.HasilNotasi(
        date(2026, 3, 2),
        (notasi.BarisNotasi(
            baris.kode,
            baris.jenis,
            baris.tanggal_mulai,
            baris.tanggal_selesai,
            f"{baris.keterangan}; {notasi.PENANDA_NOTASI_TIDAK_LENGKAP} (56 pengumuman)",
        ),),
        "IDX",
    )

    notasi.tulis_berkas(revisi, jalur, diakses=date(2026, 3, 2))

    tersimpan = next(satu for satu in notasi.baca(tmp_path) if satu.kode == "AAAA")
    assert notasi.PENANDA_NOTASI_TIDAK_LENGKAP in tersimpan.keterangan


def test_catatan_jenis_yang_tidak_diperbarui_terbawa_ke_kepala_berkas(tmp_path: Path) -> None:
    # Sesi 58: unggahan Notasi Khusus menulis ulang kepala dan membuang catatan asal suspensi.
    jalur = tmp_path / "notasi-khusus.csv"
    aktivitas = notasi.HasilNotasi(
        date(2026, 3, 1),
        (notasi._baris_aktivitas("AAAA", "suspensi", date(2026, 2, 1), None, "Suspensi"),),
        "IDX",
        catatan=("41 pengumuman pembukaan kembali tidak memiliki pasangan.",),
    )
    notasi.tulis_berkas(aktivitas, jalur, diakses=date(2026, 3, 1))
    daftar = notasi.HasilNotasi(
        date(2026, 3, 2),
        (),
        "Unggahan",
        catatan=("Notasi khusus dinyatakan sumber per 2026-03-02.",),
        jenis_dicakup=notasi.JENIS_DAFTAR,
    )

    notasi.tulis_berkas(daftar, jalur, diakses=date(2026, 3, 2))
    notasi.tulis_berkas(daftar, jalur, diakses=date(2026, 3, 2))

    catatan = [satu for satu in jalur.read_text(encoding="utf-8").splitlines() if "CATATAN" in satu]
    assert catatan == [
        "# CATATAN [suspensi]: 41 pengumuman pembukaan kembali tidak memiliki pasangan.",
        "# CATATAN [notasi_lainnya, papan_pemantauan]: Notasi khusus dinyatakan sumber per 2026-03-02.",
    ]

    aktivitas_baru = notasi.HasilNotasi(
        date(2026, 3, 3), aktivitas.baris, "IDX", catatan=("Tanpa pembukaan yatim.",)
    )
    notasi.tulis_berkas(aktivitas_baru, jalur, diakses=date(2026, 3, 3))

    catatan = [satu for satu in jalur.read_text(encoding="utf-8").splitlines() if "CATATAN" in satu]
    assert catatan == [
        "# CATATAN [notasi_lainnya, papan_pemantauan]: Notasi khusus dinyatakan sumber per 2026-03-02.",
        "# CATATAN [suspensi]: Tanpa pembukaan yatim.",
    ]


def test_catatan_tanpa_jenis_ditolak_bukan_hilang_di_penulisan_berikutnya(tmp_path: Path) -> None:
    # Tinjauan K98: catatan bertanda `[]` tidak terbaca `POLA_CATATAN`, jadi dulu hilang diam-diam.
    jalur = tmp_path / "notasi-khusus.csv"
    kosong = notasi.HasilNotasi(date(2026, 3, 2), (), "IDX", catatan=("Aktivitas kosong.",))

    with pytest.raises(notasi.GalatNotasi, match="tidak menyebut jenis"):
        notasi.tulis_berkas(kosong, jalur, diakses=date(2026, 3, 2))
    assert not jalur.exists()


# ---------------------------------------------------------------------------------------
# Bulat-balik: berkas → pembaca impor → basis data → saring
# ---------------------------------------------------------------------------------------


def _siapkan_semesta(sambungan: sqlite3.Connection) -> None:
    kode = ("ABBA", "BOSS", "TRAM", "GOTOM")
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber="uji-rujukan",
            emiten=tuple(_emiten(satu) for satu in kode),
            harga_harian=tuple(bar for satu in kode for bar in _deret(satu)),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    saring.simpan_preset(sambungan, saring.preset_bawaan(HARI_INI)[0])


def test_bulat_balik_sampai_saring_berhenti_menyebut_peringkat_sementara(
    sambungan: sqlite3.Connection, folder_data: Path
) -> None:
    """Inilah gunanya P22: begitu nota sinya ada, daftarnya berhenti disebut "sementara"."""
    _siapkan_semesta(sambungan)
    konfigurasi = lokasi.folder_konfigurasi()
    konfigurasi.mkdir(parents=True, exist_ok=True)
    notasi.tulis_berkas(notasi.urai(PAYLOAD), notasi.berkas_tujuan(konfigurasi), diakses=HARI_INI)

    # Berkas yang ditulis terbaca pembaca yang sama dengan --impor.
    terbaca = berkas.baca_folder(konfigurasi)
    assert any(satu.startswith(notasi.NAMA_BERKAS) for satu in terbaca.dibaca)
    assert {satu.kode for satu in terbaca.kumpulan.notasi_khusus} == {
        "ABBA",
        "BOSS",
        "TRAM",
        "GOTOM",
    }
    assert {
        satu.kode for satu in terbaca.kumpulan.notasi_khusus if satu.jenis == "papan_pemantauan"
    } == {"ABBA", "BOSS"}

    # Sebelum diimpor: tidak ada notasi di basis data, dan potretnya memang kosong.
    assert potret.muat(sambungan).notasi == ()

    ingesti.simpan(sambungan, terbaca.kumpulan, tanggal_data=TANGGAL, momen=MOMEN)
    potret_sesudah = potret.muat(sambungan)

    assert {satu.kode for satu in potret_sesudah.notasi} == {"ABBA", "BOSS", "TRAM", "GOTOM"}
    # ABBA dan BOSS ada di papan pemantauan khusus → tidak boleh jadi kandidat otomatis (PRD 7.3).
    assert set(potret_sesudah.kode) >= {"ABBA", "BOSS", "TRAM", "GOTOM"}


def test_pengumuman_multi_kode_yang_sudah_direkonsiliasi_tidak_memasang_penanda(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """K94: 55 pengumuman `>1 Kode` di API sudah dipetakan per kode (K36–K41, K53) — yang
    tercantum di daftar rekonsiliasi tidak boleh lagi membuat seluruh suspensi/UMA "tidak
    lengkap". Yang belum tercantum tetap menandainya."""
    lama = {"Kode": ">1 Kode", "Info_Type": "SPT", "Date": "2026-03-01", "Judul": "Suspensi multi",
            "Data_Download": "/StaticData/x/lama.pdf"}
    baru = {**lama, "Date": "2026-10-01", "Data_Download": "/StaticData/x/baru.pdf"}
    tunggal = {"Kode": "AAAA", "Info_Type": "SPT", "Date": "2026-03-01", "Judul": "Suspensi"}
    uma = [{"CompanyID": "BBBB", "UMADate": "2026-03-01", "Judul": "UMA"}]

    respons = iter(([lama, tunggal], uma))
    monkeypatch.setattr(notasi, "_unduh_daftar_aktivitas", lambda *args, **kwargs: next(respons))
    hasil = notasi.unduh_aktivitas(
        tanggal_data=date(2026, 10, 11), jeda=0, terekonsiliasi=frozenset({"/StaticData/x/lama.pdf"})
    )
    assert hasil.pengumuman_multi_kode == 0
    assert hasil.multi_kode_terekonsiliasi == 1
    assert all(notasi.PENANDA_NOTASI_TIDAK_LENGKAP not in satu.keterangan for satu in hasil.baris)

    respons = iter(([lama, baru, tunggal], uma))
    hasil = notasi.unduh_aktivitas(
        tanggal_data=date(2026, 10, 11), jeda=0, terekonsiliasi=frozenset({"/StaticData/x/lama.pdf"})
    )
    assert hasil.pengumuman_multi_kode == 1, "pengumuman baru tetap dihitung belum direkonsiliasi"
    assert all(notasi.PENANDA_NOTASI_TIDAK_LENGKAP in satu.keterangan for satu in hasil.baris)


def test_daftar_rekonsiliasi_dibaca_dari_folder_konfigurasi(tmp_path: Path) -> None:
    assert notasi.baca_terekonsiliasi(tmp_path) == frozenset(), "berkas tidak ada = tidak ada yang dianggap beres"
    (tmp_path / notasi.NAMA_BERKAS_TEREKONSILIASI).write_text(
        "# komentar\ndata_download;tanggal;jenis;dasar\n"
        "/StaticData/x/lama.pdf;2026-03-01;SPT;rekonsiliasi uji\n",
        encoding="utf-8",
    )
    assert notasi.baca_terekonsiliasi(tmp_path) == frozenset({"/StaticData/x/lama.pdf"})
