"""Bentuk tabel dan ringkasan untuk jendela dan dasbor web (PRD 11) — **tanpa Qt sama sekali**.

Kenapa berkas ini terpisah dari widget-nya:

* **Bisa diuji tanpa layar.** Uji jendela menuntut Qt dan platform grafis; susunan kolom dan isi
  selnya tidak. Karena itu penentuannya tinggal di sini dan diuji `tests/test_ui_tabel.py`.
* **Satu sumber angka.** Isi tiap sel dibaca dari objek inti yang sama dengan yang dicetak baris
  perintah (`dasbor.Dasbor`, `skor.HasilSkor`, `posisi.RingkasanPosisi`, `jurnal.BarisJurnal`),
  jadi mode jendela dan mode kepala tidak bisa menampilkan angka berbeda diam-diam (A1, PRD 6.1).
* **Yang tidak ada datanya tetap terbaca "—"**, bukan nol (aturan keras 2) — dan itu aturan
  `tampilan.angka`, bukan aturan baru di sini.

Modul ini **tidak** boleh mengimpor Qt (K91: tidak ada lagi tempat Qt boleh diimpor) —
diimpor, bukan tempat setiap berkasnya wajib mengimpornya.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from mejasaham import dasbor, jadwal, jurnal, kandidat, posisi, risiko, saring, skor, tampilan

#: Satu baris tabel: seluruh selnya sudah berupa teks siap tampil.
Baris = tuple[str, ...]
#: Kepala tabel.
Kepala = tuple[str, ...]
#: Seluruh isi tabel.
Isi = tuple[Baris, ...]

KOSONG = "—"


def _angka(nilai: float | None, desimal: int = 2) -> str:
    return tampilan.angka(nilai, desimal)


def persen_bp(nilai: int | None, desimal: int = 2) -> str:
    """Basis poin (1 bp = 0,01%) menjadi persen tampilan; `None` tetap "—", bukan nol."""
    return KOSONG if nilai is None else tampilan.angka(nilai / 100, desimal)


# ---------------------------------------------------------------------------------------
# Dasbor (PRD 11.1)
# ---------------------------------------------------------------------------------------


def kepala_kandidat_dasbor() -> Kepala:
    return ("#", "kode", "skor")


def isi_kandidat_dasbor(daftar: tuple[dasbor.BarisSkor, ...]) -> Isi:
    return tuple(
        (
            KOSONG if satu.peringkat is None else str(satu.peringkat),
            satu.kode,
            persen_bp(satu.skor_total_bp, 1),
        )
        for satu in daftar
    )


def kepala_tindakan() -> Kepala:
    return ("jenis", "kode", "rujukan", "pesan")


def isi_tindakan(daftar: tuple[dasbor.TindakanMenunggu, ...]) -> Isi:
    return tuple((satu.jenis, satu.kode, satu.rujukan, satu.pesan) for satu in daftar)


def kepala_jadwal() -> Kepala:
    return ("status", "data", "jadwal", "dasar status", "tindakan")


def isi_jadwal(daftar: tuple[jadwal.Butir, ...]) -> Isi:
    """Tindakan hanya untuk yang belum terbaru — yang terbaru tidak perlu dikerjakan (K93)."""
    return tuple(
        (
            satu.status,
            satu.nama,
            satu.jadwal,
            satu.bukti,
            satu.tindakan if satu.status != jadwal.TERBARU else "",
        )
        for satu in daftar
    )


# ---------------------------------------------------------------------------------------
# Saringan & skor (PRD 11.2)
# ---------------------------------------------------------------------------------------


def kepala_skor() -> Kepala:
    """Kolom yang sama dengan yang dicetak `--saring`, supaya dua mode tidak berbeda.

    Faktornya mengikuti `saring.FAKTOR_SAH` — bukan daftar yang disalin ke sini, sebab preset
    bisa bertambah faktor dan salinan akan ketinggalan tanpa satu pun galat.
    """
    return ("#", "kode", "skor", *saring.FAKTOR_SAH)


def baris_skor(satu: skor.HasilSkor) -> Baris:
    return (
        KOSONG if satu.peringkat is None else str(satu.peringkat),
        satu.kode,
        _angka(satu.skor_total, 1),
        *(_angka(satu.skor_faktor(faktor), 1) for faktor in saring.FAKTOR_SAH),
    )


def isi_skor(daftar: tuple[skor.HasilSkor, ...]) -> Isi:
    return tuple(baris_skor(satu) for satu in daftar)


def kepala_kriteria() -> Kepala:
    return ("kriteria", "lolos", "nilai", "satuan", "ambang", "alasan")


def isi_kriteria(penilaian: tuple[saring.PenilaianKriteria, ...]) -> Isi:
    """Rincian satu emiten; kriteria yang memang tidak berlaku tetap tampil sebagai barisnya.

    Baris "tidak berlaku" sengaja **tidak** dibuang: menghilangkannya membuat emiten bank tampak
    diperiksa dengan DER padahal tidak (PRD 8.4, AC-16).
    """
    baris: list[Baris] = []
    for satu in penilaian:
        if not satu.berlaku:
            lolos = "tidak berlaku"
        elif satu.lolos is None:
            lolos = "tidak dapat dinilai"
        else:
            lolos = "lolos" if satu.lolos else "gagal"
        baris.append(
            (
                satu.kriteria,
                lolos,
                _angka(satu.nilai, 2),
                satu.satuan,
                satu.ambang,
                satu.alasan,
            )
        )
    return tuple(baris)


def ringkas_skor(id_preset: str, satu: skor.HasilSkor | None) -> str:
    """Satu baris skor di detail emiten (PRD 11.3): preset, peringkat, skor total.

    `penjelasan` (JSON) **tidak** ditampilkan: ia artefak yang disimpan bersama skornya, dan
    angkanya berformat Inggris. Rinciannya tampil sebagai tabel `isi_faktor_skor` +
    `isi_metrik_skor`, dari objek yang sama.
    """
    if satu is None:
        return (
            f"Preset {id_preset}: tidak ada skor untuk kode ini "
            "(faktornya belum cukup tersedia untuk diperingkat)"
        )
    if satu.peringkat is not None:
        posisi_peringkat = f"peringkat {satu.peringkat}"
    else:
        dinilai = sum(1 for faktor in satu.faktor.values() if faktor.skor is not None)
        posisi_peringkat = (
            f"tidak diperingkat: hanya {dinilai} dari {len(saring.FAKTOR_SAH)} faktor dinilai "
            f"(syarat {skor.MIN_FAKTOR_UNTUK_PERINGKAT})"
            if dinilai < skor.MIN_FAKTOR_UNTUK_PERINGKAT
            else "tidak diperingkat"
        )
    return f"Preset {id_preset} · {posisi_peringkat} · skor {_angka(satu.skor_total, 1)}"


def kepala_faktor_skor() -> Kepala:
    return ("faktor", "skor", "bobot preset %", "bobot efektif %", "ketersediaan %", "alasan")


def isi_faktor_skor(satu: skor.HasilSkor) -> Isi:
    """Skor tiap faktor dan bobotnya sesudah faktor yang gugur dialihkan (PRD 9.5, AC-3)."""
    baris: list[Baris] = []
    for faktor in saring.FAKTOR_SAH:
        isi_faktor = satu.faktor.get(faktor)
        if isi_faktor is None:
            continue
        baris.append(
            (
                faktor,
                _angka(isi_faktor.skor, 1),
                persen_bp(isi_faktor.bobot_asli_bp),
                persen_bp(isi_faktor.bobot_efektif_bp),
                tampilan.angka(isi_faktor.ketersediaan * 100, 0),
                isi_faktor.alasan,
            )
        )
    return tuple(baris)


def kepala_metrik_skor() -> Kepala:
    return ("metrik", "nilai", "z", "skor", "bobot efektif %", "status", "alasan")


def isi_metrik_skor(satu: skor.HasilSkor) -> Isi:
    """Rincian tiap metrik yang menyusun skor, per faktor (PRD 11.3).

    Alasan metrik yang **dihitung** hanya mengulang kolom nilai/z/skor/bobot (berformat Inggris,
    karena ia bagian dari penjelasan tersimpan), jadi yang tampil dari situ hanya catatan
    statistik semesta likuid (AC-17). Alasan metrik yang tidak dihitung tetap tampil utuh
    (aturan keras 2).
    """
    baris: list[Baris] = []
    for faktor in saring.FAKTOR_SAH:
        isi_faktor = satu.faktor.get(faktor)
        if isi_faktor is None:
            continue
        for metrik in isi_faktor.kontribusi:
            if metrik.status != "dihitung":
                alasan = metrik.alasan
            elif metrik.fallback_sektor:
                alasan = "statistik semesta likuid: sektor < 8 emiten likuid"
            else:
                alasan = ""
            baris.append(
                (
                    f"[{faktor}] {metrik.metrik}",
                    _angka(metrik.nilai, 2),
                    _angka(metrik.z, 2),
                    _angka(metrik.skor, 1),
                    persen_bp(metrik.bobot_efektif_bp),
                    metrik.status.replace("_", " "),
                    alasan,
                )
            )
    return tuple(baris)


# ---------------------------------------------------------------------------------------
# Posisi (dipakai dasbor & detail)
# ---------------------------------------------------------------------------------------


def kepala_posisi() -> Kepala:
    return (
        "#",
        "kode",
        "status",
        "mode",
        "lembar",
        "rata-rata",
        "stop",
        "nilai pasar",
        "risiko terbuka",
        "belum terealisasi",
        "dividen",
    )


def baris_posisi(satu: posisi.RingkasanPosisi) -> Baris:
    p = satu.posisi
    rata = satu.hitungan.harga_rata
    return (
        str(p.id_posisi),
        p.kode,
        p.status,
        p.mode,
        _angka(float(satu.lembar_terbuka), 0),
        KOSONG if rata is None else tampilan.rupiah(float(rata)),
        satu.stop.ringkas(),
        tampilan.rupiah(satu.nilai_pasar),
        tampilan.rupiah(satu.risiko_terbuka),
        tampilan.rupiah(satu.hasil_belum_terealisasi),
        tampilan.rupiah(satu.dividen.total) if satu.dividen.ada else KOSONG,
    )


def isi_posisi(daftar: tuple[posisi.RingkasanPosisi, ...]) -> Isi:
    return tuple(baris_posisi(satu) for satu in daftar)


# ---------------------------------------------------------------------------------------
# Jurnal & kepatuhan (PRD 11.5)
# ---------------------------------------------------------------------------------------


def kepala_jurnal() -> Kepala:
    return ("tanggal", "kode", "aksi", "lembar", "harga", "stop", "mode", "kepatuhan", "catatan")


def baris_jurnal(satu: jurnal.BarisJurnal) -> Baris:
    t = satu.transaksi
    if not satu.pelanggaran:
        kepatuhan = "patuh"
    else:
        kepatuhan = "melanggar: " + ", ".join(satu.kode_pelanggaran)
    catatan = satu.catatan
    teks_catatan = ""
    if catatan is not None:
        teks_catatan = catatan.alasan or ""
        if catatan.selesai_pada:
            teks_catatan = (teks_catatan + " " if teks_catatan else "") + f"(selesai {catatan.selesai_pada})"
    return (
        t.tanggal,
        t.kode,
        t.aksi,
        _angka(t.lembar, 0),
        tampilan.rupiah(t.harga),
        KOSONG if satu.rencana is None or satu.rencana.stop is None else tampilan.rupiah(satu.rencana.stop),
        t.mode,
        kepatuhan,
        teks_catatan,
    )


def isi_jurnal(daftar: tuple[jurnal.BarisJurnal, ...]) -> Isi:
    return tuple(baris_jurnal(satu) for satu in daftar)


def kepala_pelanggaran() -> Kepala:
    return ("kode", "sebutan", "emiten", "tanggal", "transaksi")


def isi_pelanggaran(daftar: tuple[jurnal.Pelanggaran, ...]) -> Isi:
    return tuple(
        (
            satu.kode,
            satu.sebutan,
            satu.kode_emiten,
            satu.tanggal,
            KOSONG if satu.id_transaksi is None else str(satu.id_transaksi),
        )
        for satu in daftar
    )


def kepala_tak_dinilai() -> Kepala:
    return ("kode", "sebab", "emiten", "tanggal")


def isi_tak_dinilai(daftar: tuple[jurnal.TakDinilai, ...]) -> Isi:
    return tuple(
        (satu.kode, satu.sebab, satu.kode_emiten, satu.tanggal) for satu in daftar
    )


# ---------------------------------------------------------------------------------------
# Tesis (PRD 11.3)
# ---------------------------------------------------------------------------------------


def ringkas_tesis(daftar: Iterable[kandidat.Kandidat], hari_ini: date | None = None) -> str:
    """Tesis kandidat satu kode, apa adanya dari `kandidat.Kandidat.ringkas`."""
    isi = list(daftar)
    if not isi:
        return "Tesis: (belum ada entri kandidat/watchlist untuk kode ini)"
    return "\n".join(satu.ringkas(hari_ini) for satu in isi)


# ---------------------------------------------------------------------------------------
# Pilihan dari daftar (K64/T71 a): rencana & posisi dipilih, bukan diketik nomornya
# ---------------------------------------------------------------------------------------
#
# Yang ditulis tetap `id_rencana`/`id_posisi` yang sama dengan baris perintah; yang dihilangkan
# hanya salah ketik nomornya — kesalahan yang tidak terlihat di layar mana pun. Karena itu tiap
# entri membawa pengenalnya (kode, lembar, harga), dan pilihan "tidak memakai" selalu ada:
# transaksi tanpa rencana memang sah (pelanggarannya tercatat), jadi ia bukan pilihan terlarang
# yang disembunyikan.

#: Pilihan "tidak menempelkan rencana" di formulir transaksi (11.3).
TANPA_RENCANA = "— tidak memakai rencana (V2/V6 tetap tercatat) —"
#: Pilihan "tidak menambah ke posisi yang sudah ada" di formulir transaksi (11.3).
TANPA_POSISI = "— posisi baru (bukan menambah ke posisi yang ada) —"
#: Pilihan "rencana baru" di revisi rencana (11.4); revisi menuntut rencana yang sudah ada.
RENCANA_BARU = "— rencana baru (bukan revisi) —"
#: Pilihan "belum memilih posisi" di formulir ubah stop (11.1). Stop hanya untuk posisi aktif,
#: jadi pilihan kosongnya menyebut syarat itu — bukan "posisi baru" seperti di formulir 11.3.
PILIH_POSISI = "— pilih posisi aktif (stop hanya untuk posisi aktif) —"
#: Pilihan "belum memilih transaksi" di formulir keputusan right issue (11.3). Wajib untuk
#: `tebus` (T51) — dan yang ditawarkan hanya transaksi **beli** posisi yang dipilih.
TANPA_TRANSAKSI = "— pilih transaksi pembelian yang sudah tercatat —"


def label_rencana(satu: risiko.Rencana) -> str:
    """Satu baris untuk kotak pilihan rencana: ID yang ditulis, sisanya pengenal pilihan itu."""
    return (
        f"#{satu.id_rencana} r{satu.revisi} · {satu.kode} · {_angka(satu.lembar, 0)} lbr · "
        f"masuk {tampilan.rupiah(satu.harga_masuk)} · stop {tampilan.rupiah(satu.stop)}"
    )


def label_posisi(satu: posisi.Posisi) -> str:
    """Satu baris untuk kotak pilihan posisi: ID yang ditulis, sisanya pengenal pilihan itu.

    Lembar terbuka tidak ditampilkan di sini: ia turunan transaksi (T43), dan menghitungnya
    berarti membaca ulang seluruh transaksi posisi hanya untuk mengisi satu label.
    """
    stop = KOSONG if satu.stop_terkini is None else tampilan.rupiah(satu.stop_terkini)
    return f"#{satu.id_posisi} {satu.kode} · {satu.status} · {satu.mode} · stop {stop}"


def label_transaksi(satu: posisi.Transaksi) -> str:
    """Satu baris untuk kotak pilihan transaksi (keputusan `tebus`, 11.3).

    Yang ditulis tetap `id_transaksi` yang sama dengan baris perintah (K64/T71 a); labelnya
    membawa pengenalnya supaya transaksi yang dipilih bisa diperiksa sebelum dikonfirmasi.
    """
    return (
        f"#{satu.id_transaksi} r{satu.revisi} · {satu.tanggal} · {satu.aksi} · "
        f"{_angka(satu.lembar, 0)} lbr @ {tampilan.rupiah(satu.harga)}"
    )


# ---------------------------------------------------------------------------------------
# Right issue (PRD 9.11, layar 11.3; aksi #19d)
# ---------------------------------------------------------------------------------------


def kepala_hak_right_issue() -> Kepala:
    return ("kode", "posisi", "tanggal aksi", "rasio", "tebus", "tenggat", "hak", "keputusan")


def baris_hak_right_issue(satu: posisi.HakRightIssue) -> Baris:
    """Satu baris hak right issue: haknya **petunjuk**, dan yang belum diputuskan tetap tampil.

    Dua aturan yang tampak di sini: hak yang tidak dapat dihitung menyebut **sebabnya** (aturan
    keras 2), dan tenggat yang belum dinyatakan sumbernya dikatakan apa adanya — itu keadaan yang
    paling mudah terlewat, sebab tidak ada tanggal yang bisa dipakai mengingatkan (K29).
    """
    rasio = f"{satu.rasio_lama}:{satu.rasio_baru}" if satu.rasio_lama and satu.rasio_baru else KOSONG
    if satu.tenggat is None:
        tenggat = "BELUM DINYATAKAN sumbernya"
    else:
        tenggat = satu.tenggat.isoformat()
    if satu.lembar_hak is None:
        hak = f"tidak dapat dihitung ({satu.alasan_hak})"
    else:
        hak = _angka(float(satu.lembar_hak), 0) + " lbr"
    return (
        satu.kode,
        f"#{satu.id_posisi}",
        satu.tanggal_aksi.isoformat(),
        rasio,
        KOSONG if satu.harga_tebus is None else tampilan.rupiah(satu.harga_tebus),
        tenggat,
        hak,
        "sudah diputuskan" if satu.sudah_diputuskan else "BELUM DIPUTUSKAN",
    )


def isi_hak_right_issue(daftar: tuple[posisi.HakRightIssue, ...]) -> Isi:
    return tuple(baris_hak_right_issue(satu) for satu in daftar)
