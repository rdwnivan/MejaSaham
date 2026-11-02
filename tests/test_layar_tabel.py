"""Uji bentuk tampilan dasbor tanpa Qt (PRD 11) — `mejasaham/layar/tabel.py`.

Yang diuji di sini adalah hal-hal yang tidak terlihat kalau hanya dasbornya yang dicoba:

* **Kolom faktor tidak disalin** — ia dibaca dari `saring.FAKTOR_SAH`. Preset bisa bertambah
  faktor (K6: preset berversi), dan daftar yang disalin ke lapisan tampilan akan ketinggalan
  tanpa satu pun galat.
* **Nilai yang tidak ada tetap "—", bukan nol** (aturan keras 2) — pada skor, pada basis poin,
  dan pada peringkat.
* **Kriteria yang tidak berlaku tetap tampil sebagai barisnya** (PRD 8.4, AC-16): emiten bank
  yang tidak diuji DER harus terlihat "tidak berlaku", bukan hilang dari daftar.
* **Berkas ini tidak mengimpor Qt** — dan justru karena itu ia bisa diuji tanpa layar.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from datetime import date
from fractions import Fraction
from pathlib import Path

from mejasaham import dasbor, jurnal, posisi, risiko, saring, skor
from mejasaham.layar import tabel

AKAR = Path(__file__).resolve().parents[1]
BERKAS = AKAR / "mejasaham" / "layar" / "tabel.py"
QT = {"PySide6", "PyQt6", "PyQt5", "shiboken6"}


def test_kepala_skor_memakai_daftar_faktor_saring() -> None:
    kepala = tabel.kepala_skor()
    assert kepala == ("#", "kode", "skor", *saring.FAKTOR_SAH)
    assert len(kepala) == 3 + len(saring.FAKTOR_SAH)


def test_nilai_yang_tidak_ada_menjadi_tanda_kosong_bukan_nol() -> None:
    """Peringkat yang belum ada dan basis poin yang kosong tidak boleh terbaca "0"."""
    isi = tabel.isi_kandidat_dasbor(
        (dasbor.BarisSkor(kode="AAAA", peringkat=None, skor_total_bp=7420),)
    )
    assert isi == (("—", "AAAA", "74,2"),)
    assert tabel.persen_bp(None) == "—"
    assert tabel.persen_bp(0) == "0,00"


def _penilaian(**ubah: object) -> saring.PenilaianKriteria:
    nilai: dict[str, object] = {
        "kriteria": "der",
        "lolos": True,
        "nilai": 1.5,
        "satuan": "x",
        "ambang": "<= 2,0",
    }
    nilai.update(ubah)
    return saring.PenilaianKriteria(**nilai)  # type: ignore[arg-type]


def test_kriteria_yang_tidak_berlaku_tetap_tampil() -> None:
    """AC-16: DER tidak diterapkan pada bank — barisnya harus terlihat, bukan hilang."""
    isi = tabel.isi_kriteria(
        (
            _penilaian(kriteria="der", berlaku=False, lolos=None, nilai=None, alasan=""),
            _penilaian(kriteria="npl_kotor", lolos=None, nilai=None, alasan="rasio bank belum ada"),
            _penilaian(kriteria="roe_5t", lolos=False, nilai=8.1, ambang=">= 12%"),
        )
    )
    assert isi[0][1] == "tidak berlaku"
    assert isi[1][1] == "tidak dapat dinilai"
    assert isi[1][2] == "—"  # nilainya tidak ada: tanda kosong, bukan 0
    assert isi[1][5] == "rasio bank belum ada"
    assert isi[2][1] == "gagal"


def _hasil_skor(*, peringkat: int | None, faktor_dinilai: int) -> skor.HasilSkor:
    dihitung = skor.KontribusiMetrik(
        metrik="roe_5t", nilai=0.1467, z=0.1774, skor=52.9562, bobot_asli_bp=3000,
        bobot_efektif_bp=3000, arah="tinggi_baik", status="dihitung",
        alasan="roe_5t: nilai 0.1467, z +0.18, skor 53.0, bobot 30%",
    )
    faktor = {}
    for urutan, nama in enumerate(saring.FAKTOR_SAH):
        dinilai = urutan < faktor_dinilai
        faktor[nama] = skor.SkorFaktor(
            faktor=nama,
            skor=55.7432 if dinilai else None,
            bobot_asli_bp=2500,
            bobot_efektif_bp=2500 if dinilai else 0,
            ketersediaan=1.0 if dinilai else 0.0,
            kontribusi=(
                (dihitung, replace(dihitung, metrik="der", fallback_sektor=True))
                if dinilai
                else (
                    replace(
                        dihitung, metrik="per", nilai=None, z=None, skor=None,
                        bobot_efektif_bp=0, status="tidak_dihitung", alasan="laba negatif",
                    ),
                )
            ),
            alasan="bobot metrik dinormalkan atas 100% yang tersedia" if dinilai else "tidak dinilai",
        )
    return skor.HasilSkor(
        kode="AAAA", faktor=faktor, skor_total=55.7432, peringkat=peringkat,
        penjelasan='{"faktor": {}}', diperingkat=peringkat is not None,
    )


def test_ringkas_skor_berangka_indonesia_dan_tanpa_json_mentah() -> None:
    """AGENTS §4: koma desimal; penjelasan JSON adalah artefak simpan, bukan teks layar."""
    teks = tabel.ringkas_skor("kualitas-nilai/v1", _hasil_skor(peringkat=1, faktor_dinilai=4))
    assert teks == "Preset kualitas-nilai/v1 · peringkat 1 · skor 55,7"
    sementara = tabel.ringkas_skor("kualitas-nilai/v1", _hasil_skor(peringkat=None, faktor_dinilai=2))
    assert "tidak diperingkat: hanya 2 dari 4 faktor dinilai" in sementara
    assert "{" not in sementara
    assert "tidak ada skor" in tabel.ringkas_skor("kualitas-nilai/v1", None)


def test_rincian_skor_per_faktor_dan_metrik_tidak_mengulang_angka_berformat_inggris() -> None:
    hasil = _hasil_skor(peringkat=None, faktor_dinilai=3)
    faktor = tabel.isi_faktor_skor(hasil)
    assert [baris[0] for baris in faktor] == list(saring.FAKTOR_SAH)
    assert faktor[0][1:4] == ("55,7", "25,00", "25,00")
    assert faktor[3][1] == "—" and faktor[3][5] == "tidak dinilai"
    metrik = tabel.isi_metrik_skor(hasil)
    assert metrik[0][:4] == (f"[{saring.FAKTOR_SAH[0]}] roe_5t", "0,15", "0,18", "53,0")
    # Alasan "nilai 0.1467, z +0.18 …" hanya mengulang kolom di sebelahnya — dengan titik desimal.
    assert metrik[0][6] == ""
    assert "semesta likuid" in metrik[1][6]
    assert metrik[-1][5] == "tidak dihitung" and metrik[-1][6] == "laba negatif"
    assert not any("0.1467" in sel for baris in metrik for sel in baris)


def test_isi_tindakan_memakai_pesan_dari_dasbor() -> None:
    satu = dasbor.TindakanMenunggu(
        jenis="stop_tertembus", kode="AAAA", rujukan="posisi #1", pesan="penutupan menembus stop"
    )
    assert tabel.isi_tindakan((satu,)) == (
        ("stop_tertembus", "AAAA", "posisi #1", "penutupan menembus stop"),
    )


def test_ringkas_tesis_kosong_disebut_bukan_dibiarkan_kosong() -> None:
    teks = tabel.ringkas_tesis(())
    assert "belum ada" in teks


def test_baris_jurnal_menyebut_pelanggaran_dan_catatan() -> None:
    transaksi = posisi.Transaksi(
        id_transaksi=7,
        revisi=1,
        id_posisi=3,
        id_rencana=None,
        tanggal="2026-07-01",
        kode="AAAA",
        aksi="beli",
        harga=1000,
        lembar=100,
        biaya=None,
        asal_biaya=None,
        pajak=None,
        mode="nyata",
        pelanggaran="V1",
        catatan=None,
        sumber="uji",
        diketahui_pada="2026-07-01T09:00:00+07:00",
    )
    baris_patuh = jurnal.BarisJurnal(
        transaksi=transaksi, catatan=None, rencana=None, tesis=None, pelanggaran=()
    )
    assert tabel.baris_jurnal(baris_patuh)[7] == "patuh"
    assert tabel.baris_jurnal(baris_patuh)[5] == "—"  # tanpa rencana: stop tidak ada, bukan 0


def test_modul_tampilan_tidak_mengimpor_qt() -> None:
    """Berkas ini harus tetap bisa diuji tanpa layar; Qt-nya tinggal di widget-nya."""
    pohon = ast.parse(BERKAS.read_text(encoding="utf-8-sig"), filename=str(BERKAS))
    nama: set[str] = set()
    for simpul in ast.walk(pohon):
        if isinstance(simpul, ast.Import):
            nama.update(alias.name for alias in simpul.names)
        elif isinstance(simpul, ast.ImportFrom) and simpul.module:
            nama.add(simpul.module)
    pelanggar = sorted(satu for satu in nama if satu.split(".")[0] in QT)
    assert not pelanggar, f"mejasaham/layar/tabel.py mengimpor Qt: {pelanggar}"


# ---------------------------------------------------------------------------------------
# Pilihan dari daftar (K64/T71 a)
# ---------------------------------------------------------------------------------------


def _rencana(**ubah: object) -> risiko.Rencana:
    nilai: dict[str, object] = {
        "id_rencana": 1,
        "revisi": 2,
        "id_kandidat": 3,
        "kode": "AAAA",
        "id_preset_risiko": "risiko-bawaan/v1",
        "id_snapshot": 4,
        "tanggal": "2026-07-01",
        "ekuitas": 250_000_000,
        "risiko_per_posisi_bp": 75,
        "harga_masuk": 2_320,
        "stop": 2_180,
        "dasar_stop": "pengguna",
        "biaya_slippage": 14,
        "lembar_mentah_mili": 12_224_000,
        "lembar": 10_800,
        "maks_lembar_bobot": 10_800,
        "maks_lembar_sektor": None,
        "maks_lembar_likuiditas": None,
        "maks_lembar_kas": None,
        "bobot_bp": 1_002,
        "risiko_nominal": 1_663_200,
        "risiko_berjalan": 0,
        "total_risiko_bp": 66,
        "jenis_stop": "order_sekuritas",
        "batas_tidak_dinilai": None,
        "catatan": None,
        "dicatat_pada": "2026-07-01T09:00:00+07:00",
    }
    nilai.update(ubah)
    return risiko.Rencana(**nilai)  # type: ignore[arg-type]


def test_label_rencana_memuat_id_yang_ditulis_beserta_pengenalnya() -> None:
    """Yang ditulis `id_rencana`-nya; labelnya menyebut kode, lembar, harga, dan stop.

    Angka tampil format Indonesia (U11) dan memakai `tampilan.rupiah` — bukan format kedua yang
    bisa berbeda dari keluaran baris perintah.
    """
    label = tabel.label_rencana(_rencana())
    assert label.startswith("#1 r2 · AAAA · 10.800 lbr · masuk Rp 2.320 · stop Rp 2.180")


def test_label_posisi_memuat_id_yang_ditulis_beserta_pengenalnya() -> None:
    p = posisi.Posisi(
        id_posisi=3,
        revisi=1,
        kode="MLPT",
        tgl_buka="2026-07-01",
        tgl_tutup=None,
        status="aktif",
        stop_terkini=17_000,
        tgl_stop="2026-07-15",
        id_rencana=None,
        mode="nyata",
        pelanggaran=None,
        catatan=None,
        sumber="uji",
        diketahui_pada="2026-07-01T09:00:00+07:00",
    )
    assert tabel.label_posisi(p) == "#3 MLPT · aktif · nyata · stop Rp 17.000"
    # Stop yang tidak diketahui tetap "—": posisi tanpa stop bukan posisi dengan stop nol.
    tanpa_stop = replace(p, stop_terkini=None)
    assert tabel.label_posisi(tanpa_stop).endswith("stop —")


def test_pilihan_tanpa_rencana_dan_tanpa_posisi_dinyatakan_bukan_kotak_kosong() -> None:
    """Transaksi tanpa rencana memang sah (pelanggarannya tercatat), jadi pilihannya ada."""
    assert "tidak memakai rencana" in tabel.TANPA_RENCANA
    assert "V2/V6" in tabel.TANPA_RENCANA
    assert "posisi baru" in tabel.TANPA_POSISI
    assert "rencana baru" in tabel.RENCANA_BARU


# ---------------------------------------------------------------------------------------
# Aksi #19d: pilihan posisi (11.1), transaksi `tebus`, dan tabel hak right issue (11.3)
# ---------------------------------------------------------------------------------------


def _transaksi(**ubah: object) -> posisi.Transaksi:
    nilai: dict[str, object] = {
        "id_transaksi": 6,
        "revisi": 1,
        "id_posisi": 3,
        "id_rencana": None,
        "tanggal": "2026-09-22",
        "kode": "MLPT",
        "aksi": "beli",
        "harga": 2_320,
        "lembar": 6_200,
        "biaya": 21_576,
        "asal_biaya": "tarif",
        "pajak": None,
        "mode": "nyata",
        "pelanggaran": None,
        "catatan": None,
        "sumber": "uji",
        "diketahui_pada": "2026-09-22T09:00:00+07:00",
    }
    nilai.update(ubah)
    return posisi.Transaksi(**nilai)  # type: ignore[arg-type]


def _hak(**ubah: object) -> posisi.HakRightIssue:
    nilai: dict[str, object] = {
        "kode": "MLPT",
        "id_posisi": 3,
        "tanggal_aksi": date(2026, 9, 20),
        "rasio_lama": 4,
        "rasio_baru": 1,
        "harga_tebus": 400,
        "tenggat": date(2026, 9, 30),
        "lembar_hak": Fraction(6_250),
        "alasan_hak": None,
        "keputusan": None,
        "sumber": "uji",
        "lot": 100,
    }
    nilai.update(ubah)
    return posisi.HakRightIssue(**nilai)  # type: ignore[arg-type]


def test_label_transaksi_memuat_id_yang_ditulis_beserta_pengenalnya() -> None:
    """Yang ditulis `id_transaksi`-nya; labelnya menyebut tanggal, aksi, lembar, dan harganya."""
    assert tabel.label_transaksi(_transaksi()) == (
        "#6 r1 · 2026-09-22 · beli · 6.200 lbr @ Rp 2.320"
    )


def test_pilihan_posisi_stop_dan_transaksi_tebus_dinyatakan() -> None:
    """Dua pilihan kosong baru menyebut syaratnya, bukan kotak kosong yang ambigu (K64/T71 a)."""
    assert "posisi aktif" in tabel.PILIH_POSISI
    assert "stop hanya untuk posisi aktif" in tabel.PILIH_POSISI
    assert "transaksi pembelian" in tabel.TANPA_TRANSAKSI


def test_tabel_hak_right_issue_menyebut_tenggat_yang_belum_dinyatakan_dan_sebab_haknya() -> None:
    """Tenggat yang belum dinyatakan (K29) dan hak yang tidak dapat dihitung tetap terbaca."""
    kepala = tabel.kepala_hak_right_issue()
    baris = tabel.isi_hak_right_issue(
        (
            _hak(),
            _hak(
                tenggat=None,
                lembar_hak=None,
                rasio_lama=None,
                alasan_hak="aksinya tidak menyatakan rasio",
            ),
        )
    )
    assert len(baris[0]) == len(kepala)
    assert baris[0][3] == "4:1" and baris[0][4] == "Rp 400"
    assert baris[0][5] == "2026-09-30"
    assert baris[0][6] == "6.250 lbr"
    assert baris[0][7] == "BELUM DIPUTUSKAN"
    # Hak yang tidak dapat dihitung menyebut **sebabnya**, bukan nol (aturan keras 2).
    assert baris[1][6] == "tidak dapat dihitung (aksinya tidak menyatakan rasio)"
    assert baris[1][5] == "BELUM DINYATAKAN sumbernya"
    assert baris[1][3] == tabel.KOSONG
