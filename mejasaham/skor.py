"""Skoring & peringkat (F3, PRD 9.5): z per sektor → skor 0–100 → skor total berbobot.

Aturan yang mengikat, semuanya dari PRD 9.5 dan keputusan K10:

* **Statistik dari semesta likuid, bukan dari yang lolos saring** (PRD 9.5). Kalau hanya yang
  lolos yang dipakai, ambang saringan ikut menentukan skalanya dan skor tidak lagi sebanding
  antar-waktu.
* **Sektor dengan kurang dari 8 emiten likuid memakai statistik seluruh semesta likuid**, dan
  hal itu **tertulis di penjelasan** (PRD 8.4, AC-17).
* **Metrik yang tidak dihitung tidak diberi nilai nol** (aturan keras 2, AC-3). Bobotnya
  dialihkan ke metrik lain di faktor yang sama; faktor dinilai bila ≥ 60% bobot metriknya
  tersedia; emiten diperingkat bila ≥ 3 dari 4 faktor dinilai; bobot faktor yang gugur
  dialihkan proporsional. Semuanya ditulis di penjelasan.
* **Determinisme** (A5, AC-2): urutan peringkat dihitung dari nilai tak dibulatkan, dan seri
  diputus oleh ADTV20 lebih besar (PRD 9.5) lalu oleh kode sebagai pemutus terakhir supaya
  hasilnya tidak bergantung pada urutan baris basis data.

Nilai z memakai statistik **populasi** (ddof=0) sesuai K10/P10, dipotong pada ±3, lalu dipetakan
linear: `z = −3 → 0`, `z = +3 → 100`.

Penjelasan disimpan sebagai JSON di kolom `penjelasan`. Ia **bukan** parameter bertipe (T14):
isinya artefak yang harus bisa dibaca manusia dan ikut tersimpan bersama skornya, bukan angka
yang dipakai berhitung.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from mejasaham import db
from mejasaham.metrik import Nilai, _statistik_populasi
from mejasaham.potret import Potret
from mejasaham.saring import FAKTOR_SAH as FAKTOR
from mejasaham.saring import Preset

#: Versi cara menghitung. Naikkan bila rumusnya berubah supaya skor lama tidak tampak sebanding
#: dengan skor baru (baris `skor` memang ditulis ulang — lihat catatan di `skema.py` migrasi 004).
VERSI_HITUNG = "tahap1-1"

#: Ambang "cukup tersedia" untuk sebuah faktor (PRD 9.5: ≥ 60% bobot metriknya tersedia).
AMBANG_KETERSEDIAAN_FAKTOR = 0.60

#: Minimal faktor yang dinilai supaya emiten masuk peringkat (PRD 9.5: ≥ 3 dari 4).
MIN_FAKTOR_UNTUK_PERINGKAT = 3

#: Minimal emiten likuid dalam satu sektor sebelum statistik sektornya dipakai sendiri
#: (PRD 8.4: sektor dengan kurang dari 8 emiten likuid memakai statistik seluruh semesta).
MIN_EMITEN_SEKTOR = 8

#: Faktor skor dipakai dari `saring.FAKTOR_SAH` (satu sumber, bukan dua daftar yang bisa berbeda).

#: Pemotongan z (K10/P10).
Z_MINIMUM = -3.0
Z_MAKSIMUM = 3.0


@dataclass(frozen=True)
class StatistikMetrik:
    """Rata-rata & simpangan baku satu metrik untuk satu kelompok, plus asal kelompoknya."""

    rata_rata: float
    simpangan: float
    jumlah: int
    dari_fallback: bool = False


@dataclass(frozen=True)
class KontribusiMetrik:
    """Satu metrik di dalam sebuah faktor: nilainya, z-nya, dan berapa bobot yang dipakai."""

    metrik: str
    nilai: float | None
    z: float | None
    skor: float | None
    bobot_asli_bp: int
    bobot_efektif_bp: int
    arah: str
    status: str
    alasan: str = ""
    fallback_sektor: bool = False


@dataclass(frozen=True)
class SkorFaktor:
    faktor: str
    skor: float | None
    bobot_asli_bp: int
    bobot_efektif_bp: int
    ketersediaan: float
    kontribusi: tuple[KontribusiMetrik, ...] = ()
    alasan: str = ""


@dataclass(frozen=True)
class HasilSkor:
    kode: str
    faktor: Mapping[str, SkorFaktor]
    skor_total: float
    peringkat: int | None
    penjelasan: str
    diperingkat: bool
    adtv20: float | None = None

    def skor_faktor(self, nama: str) -> float | None:
        satu = self.faktor.get(nama)
        return satu.skor if satu is not None else None


# ---------------------------------------------------------------------------------------
# Statistik sektor (PRD 9.5, 8.4 — AC-17)
# ---------------------------------------------------------------------------------------


def _angka_kelompok(
    metrik: Mapping[str, Mapping[str, Nilai]],
    anggota: Iterable[str],
    nama_metrik: str,
) -> list[float]:
    hasil: list[float] = []
    for kode in anggota:
        nilai = metrik.get(kode, {}).get(nama_metrik)
        if nilai is not None and nilai.ada:
            hasil.append(float(nilai.nilai or 0))
    return hasil


def statistik_sektor(
    metrik: Mapping[str, Mapping[str, Nilai]],
    sektor: Mapping[str, str],
    semesta_likuid: Sequence[str],
    nama_metrik: str,
) -> dict[str, StatistikMetrik]:
    """Statistik per sektor untuk satu metrik, lengkap dengan penandaan fallback (AC-17)."""
    per_sektor: dict[str, list[str]] = {}
    for kode in semesta_likuid:
        per_sektor.setdefault(sektor.get(kode, ""), []).append(kode)

    angka_semesta = _angka_kelompok(metrik, semesta_likuid, nama_metrik)
    statistik_semesta = _statistik_populasi(angka_semesta) if len(angka_semesta) >= 2 else None

    hasil: dict[str, StatistikMetrik] = {}
    for nama_sektor, anggota in per_sektor.items():
        angka = _angka_kelompok(metrik, anggota, nama_metrik)
        # Sektor dipakai sendiri hanya bila ia cukup besar **dan** statistiknya terdefinisi.
        if len(anggota) >= MIN_EMITEN_SEKTOR and len(angka) >= 2:
            rerata, simpangan = _statistik_populasi(angka)
            hasil[nama_sektor] = StatistikMetrik(rerata, simpangan, len(angka))
        elif statistik_semesta is not None:
            rerata, simpangan = statistik_semesta
            hasil[nama_sektor] = StatistikMetrik(
                rerata, simpangan, len(angka_semesta), dari_fallback=True
            )
    return hasil


def _petakan_z(z: float, arah: str) -> float:
    """`z = −3 → 0`, `z = +3 → 100`; metrik "rendah lebih baik" arahnya dibalik (K10/P10)."""
    dipotong = max(Z_MINIMUM, min(Z_MAKSIMUM, z))
    if arah == "rendah_baik":
        dipotong = -dipotong
    return (dipotong - Z_MINIMUM) / (Z_MAKSIMUM - Z_MINIMUM) * 100


def _z(nilai: float, statistik: StatistikMetrik) -> float | None:
    if statistik.simpangan == 0:
        return None
    return (nilai - statistik.rata_rata) / statistik.simpangan


# ---------------------------------------------------------------------------------------
# Skor satu emiten
# ---------------------------------------------------------------------------------------


def metrik_preset(preset: Preset) -> tuple[str, ...]:
    """Seluruh nama metrik yang disebut preset, urut dan tanpa duplikat."""
    return tuple(sorted({satu.metrik for satu in preset.bobot_metrik}))


def skor_emiten(
    preset: Preset,
    kode: str,
    metrik: Mapping[str, Nilai],
    stats_sektor: Mapping[str, StatistikMetrik],
    *,
    jenis: str,
) -> HasilSkor:
    """Hitung skor faktor dan skor total satu emiten, beserta penjelasannya.

    `stats_sektor` sudah berisi statistik **sektor emiten ini** per nama metrik; penyusunannya
    ada di `skor_semesta` supaya statistik dihitung sekali, bukan sekali per emiten.
    """
    faktor_hasil: dict[str, SkorFaktor] = {}

    for faktor in FAKTOR:
        bobot_faktor = preset.bobot_faktor.get(faktor, 0)
        if bobot_faktor <= 0:
            continue
        bobot_metrik = preset.bobot_untuk(faktor, jenis)
        total_bobot = sum(satu.bobot_bp for satu in bobot_metrik)
        kontribusi: list[KontribusiMetrik] = []
        tersedia: list[KontribusiMetrik] = []

        for satu in bobot_metrik:
            nilai = metrik.get(satu.metrik)
            if nilai is None or not nilai.ada:
                kontribusi.append(
                    KontribusiMetrik(
                        metrik=satu.metrik,
                        nilai=None,
                        z=None,
                        skor=None,
                        bobot_asli_bp=satu.bobot_bp,
                        bobot_efektif_bp=0,
                        arah=satu.arah,
                        status="tidak_dihitung",
                        alasan=(
                            nilai.alasan
                            if nilai is not None and nilai.alasan
                            else "metrik tidak tersedia"
                        ),
                    )
                )
                continue
            statistik = stats_sektor.get(satu.metrik)
            if statistik is None:
                kontribusi.append(
                    KontribusiMetrik(
                        metrik=satu.metrik,
                        nilai=float(nilai.nilai or 0),
                        z=None,
                        skor=None,
                        bobot_asli_bp=satu.bobot_bp,
                        bobot_efektif_bp=0,
                        arah=satu.arah,
                        status="tidak_dihitung",
                        alasan="statistik sektor belum bisa dihitung (semesta likuid terlalu kecil)",
                    )
                )
                continue
            z = _z(float(nilai.nilai or 0), statistik)
            if z is None:
                kontribusi.append(
                    KontribusiMetrik(
                        metrik=satu.metrik,
                        nilai=float(nilai.nilai or 0),
                        z=None,
                        skor=None,
                        bobot_asli_bp=satu.bobot_bp,
                        bobot_efektif_bp=0,
                        arah=satu.arah,
                        status="tidak_dihitung",
                        alasan="seluruh emiten likuid bernilai sama, sehingga z tidak terdefinisi",
                        fallback_sektor=statistik.dari_fallback,
                    )
                )
                continue
            satu_kontribusi = KontribusiMetrik(
                metrik=satu.metrik,
                nilai=float(nilai.nilai or 0),
                z=z,
                skor=_petakan_z(z, satu.arah),
                bobot_asli_bp=satu.bobot_bp,
                bobot_efektif_bp=satu.bobot_bp,
                arah=satu.arah,
                status="dihitung",
                fallback_sektor=statistik.dari_fallback,
            )
            kontribusi.append(satu_kontribusi)
            tersedia.append(satu_kontribusi)

        bobot_tersedia = sum(satu.bobot_asli_bp for satu in tersedia)
        ketersediaan = bobot_tersedia / total_bobot if total_bobot else 0.0

        if not tersedia or ketersediaan < AMBANG_KETERSEDIAAN_FAKTOR:
            hilang = [satu for satu in kontribusi if satu.status != "dihitung"]
            rincian = "; ".join(f"{satu.metrik}: {satu.alasan}" for satu in hilang[:2])
            faktor_hasil[faktor] = SkorFaktor(
                faktor=faktor,
                skor=None,
                bobot_asli_bp=bobot_faktor,
                bobot_efektif_bp=0,
                ketersediaan=ketersediaan,
                kontribusi=tuple(kontribusi),
                alasan=(
                    f"tidak dinilai: hanya {ketersediaan:.0%} bobot metriknya tersedia "
                    f"(ambang {AMBANG_KETERSEDIAAN_FAKTOR:.0%}). {rincian}"
                ).strip(),
            )
            continue

        # Bobot dinormalkan ulang atas metrik yang tersedia (PRD 9.5, AC-3). Kontribusi
        # dibangun ulang sebagai daftar baru — mengubah isi list sambil menelusurinya adalah
        # cara halus untuk menghasilkan penjelasan yang tidak cocok dengan angkanya.
        kontribusi = [
            satu
            if satu.status != "dihitung"
            else KontribusiMetrik(
                metrik=satu.metrik,
                nilai=satu.nilai,
                z=satu.z,
                skor=satu.skor,
                bobot_asli_bp=satu.bobot_asli_bp,
                bobot_efektif_bp=satu.bobot_asli_bp,
                arah=satu.arah,
                status=satu.status,
                alasan=(
                    f"{satu.metrik}: nilai {satu.nilai:g}, z {satu.z:+.2f}, skor {satu.skor:.1f}, "
                    f"bobot {satu.bobot_asli_bp / 100:g}%"
                    + (
                        " (statistik semesta likuid: sektor < 8 emiten likuid)"
                        if satu.fallback_sektor
                        else ""
                    )
                ),
                fallback_sektor=satu.fallback_sektor,
            )
            for satu in kontribusi
        ]
        # Skor faktor = rata-rata berbobot skor metriknya, dengan bobot dinormalkan ulang atas
        # metrik yang tersedia (PRD 9.5, AC-3).
        skor = sum(
            float(satu.skor or 0) * satu.bobot_efektif_bp / bobot_tersedia for satu in tersedia
        )
        faktor_hasil[faktor] = SkorFaktor(
            faktor=faktor,
            skor=skor,
            bobot_asli_bp=bobot_faktor,
            bobot_efektif_bp=bobot_faktor,
            ketersediaan=ketersediaan,
            kontribusi=tuple(kontribusi),
            alasan=f"bobot metrik dinormalkan atas {ketersediaan:.0%} yang tersedia",
        )

    dinilai = {nama: satu for nama, satu in faktor_hasil.items() if satu.skor is not None}
    bobot_dinilai = sum(satu.bobot_asli_bp for satu in dinilai.values())

    if bobot_dinilai <= 0:
        return _hasil(
            kode=kode,
            faktor=faktor_hasil,
            skor_total=0.0,
            diperingkat=False,
            alasan="tidak ada satu pun faktor yang bisa dinilai",
            bobot_dinilai=0,
        )

    # Bobot faktor yang gugur dialihkan proporsional ke faktor yang dinilai (PRD 9.5).
    for nama, satu in list(faktor_hasil.items()):
        if satu.skor is None:
            continue
        faktor_hasil[nama] = SkorFaktor(
            faktor=satu.faktor,
            skor=satu.skor,
            bobot_asli_bp=satu.bobot_asli_bp,
            bobot_efektif_bp=round(satu.bobot_asli_bp / bobot_dinilai * 10000),
            ketersediaan=satu.ketersediaan,
            kontribusi=satu.kontribusi,
            alasan=satu.alasan,
        )

    skor_total = sum(
        float(satu.skor or 0) * satu.bobot_efektif_bp / 10000 for satu in faktor_hasil.values()
    )
    cukup = len(dinilai) >= MIN_FAKTOR_UNTUK_PERINGKAT
    alasan = (
        ""
        if cukup
        else (
            f"tidak diperingkat: hanya {len(dinilai)} dari {len(FAKTOR)} faktor dinilai "
            f"(syarat {MIN_FAKTOR_UNTUK_PERINGKAT})"
        )
    )
    return _hasil(
        kode=kode,
        faktor=faktor_hasil,
        skor_total=skor_total,
        diperingkat=cukup,
        alasan=alasan,
        bobot_dinilai=bobot_dinilai,
    )


def _hasil(
    *,
    kode: str,
    faktor: Mapping[str, SkorFaktor],
    skor_total: float,
    diperingkat: bool,
    alasan: str,
    bobot_dinilai: int,
) -> HasilSkor:
    penjelasan = json.dumps(
        {
            "versi_hitung": VERSI_HITUNG,
            "diperingkat": diperingkat,
            "skor_total": round(skor_total, 4),
            "bobot_dinilai_bp": bobot_dinilai,
            "alasan": alasan,
            "faktor": {
                nama: {
                    "skor": round(float(satu.skor), 4) if satu.skor is not None else None,
                    "bobot_asli_bp": satu.bobot_asli_bp,
                    "bobot_efektif_bp": satu.bobot_efektif_bp,
                    "ketersediaan": round(satu.ketersediaan, 4),
                    "alasan": satu.alasan,
                    "metrik": [
                        {
                            "nama": satu_metrik.metrik,
                            "nilai": satu_metrik.nilai,
                            "z": round(satu_metrik.z, 4) if satu_metrik.z is not None else None,
                            "skor": (
                                round(float(satu_metrik.skor), 4)
                                if satu_metrik.skor is not None
                                else None
                            ),
                            "bobot_asli_bp": satu_metrik.bobot_asli_bp,
                            "bobot_efektif_bp": satu_metrik.bobot_efektif_bp,
                            "arah": satu_metrik.arah,
                            "status": satu_metrik.status,
                            "fallback_sektor": satu_metrik.fallback_sektor,
                            "alasan": satu_metrik.alasan,
                        }
                        for satu_metrik in satu.kontribusi
                    ],
                }
                for nama, satu in faktor.items()
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return HasilSkor(
        kode=kode,
        faktor=faktor,
        skor_total=skor_total,
        peringkat=None,
        penjelasan=penjelasan,
        diperingkat=diperingkat,
    )


# ---------------------------------------------------------------------------------------
# Skor seluruh semesta + peringkat
# ---------------------------------------------------------------------------------------


def skor_semesta(
    potret: Potret,
    preset: Preset,
    semesta_likuid: Sequence[str],
    kode_dinilai: Iterable[str],
    metrik: Mapping[str, Mapping[str, Nilai]],
) -> tuple[HasilSkor, ...]:
    """Skor seluruh `kode_dinilai`, dengan statistik sektor dari `semesta_likuid` (PRD 9.5).

    Peringkat diberikan setelah seluruh skor terkumpul, karena urutan hanya bermakna relatif
    terhadap yang lain. Seri diputus ADTV20 lebih besar, lalu kode (supaya deterministik).
    """
    daftar = tuple(kode_dinilai)
    sektor = {kode: (potret.emiten[kode].sektor_idx_ic or "") for kode in potret.kode}
    jenis = {kode: (potret.emiten[kode].jenis or "umum") for kode in potret.kode}

    stats = {
        nama: statistik_sektor(metrik, sektor, semesta_likuid, nama)
        for nama in metrik_preset(preset)
    }

    hasil: list[HasilSkor] = []
    for kode in daftar:
        nama_sektor = sektor[kode]
        stats_kode = {
            nama: tabel[nama_sektor]
            for nama, tabel in stats.items()
            if nama_sektor in tabel
        }
        hasil.append(
            skor_emiten(preset, kode, metrik[kode], stats_kode, jenis=jenis[kode])
        )

    return beri_peringkat(hasil, metrik)


def beri_peringkat(
    hasil: Sequence[HasilSkor], metrik: Mapping[str, Mapping[str, Nilai]]
) -> tuple[HasilSkor, ...]:
    """Beri peringkat pada emiten yang memenuhi syarat; sisanya tetap terbawa tanpa peringkat."""

    def adtv(kode: str) -> float:
        nilai = metrik.get(kode, {}).get("adtv20")
        return float(nilai.nilai or 0) if nilai is not None and nilai.ada else 0.0

    layak = [satu for satu in hasil if satu.diperingkat]
    layak_urut = sorted(layak, key=lambda satu: (-satu.skor_total, -adtv(satu.kode), satu.kode))

    urut = {satu.kode: nomor for nomor, satu in enumerate(layak_urut, start=1)}

    return tuple(
        HasilSkor(
            kode=satu.kode,
            faktor=satu.faktor,
            skor_total=satu.skor_total,
            peringkat=urut.get(satu.kode),
            penjelasan=satu.penjelasan,
            diperingkat=satu.diperingkat,
            adtv20=adtv(satu.kode),
        )
        for satu in hasil
    )


# ---------------------------------------------------------------------------------------
# Penyimpanan
# ---------------------------------------------------------------------------------------


def simpan_skor(
    sambungan: sqlite3.Connection,
    potret: Potret,
    preset: Preset,
    hasil: Sequence[HasilSkor],
) -> int:
    """Tulis hasil skor untuk satu (snapshot, preset).

    `skor` **ditulis ulang**, bukan append-only: ia turunan deterministik berkunci
    `kode + id_snapshot + id_preset` (PRD 8.1), bukan data yang direvisi manusia. Yang menjaga
    kejujurannya adalah kolom `versi_hitung` — perubahan cara menghitung terlihat, bukan samar.
    """
    waktu = db.waktu_iso()
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "DELETE FROM skor WHERE id_snapshot = ? AND id_preset = ?",
            (potret.id_snapshot, preset.id_preset),
        )
        for satu in hasil:
            koneksi.execute(
                "INSERT INTO skor (kode, id_snapshot, id_preset, skor_kualitas_bp, skor_nilai_bp,"
                " skor_momentum_bp, skor_volatilitas_bp, skor_total_bp, peringkat, dihitung_pada,"
                " versi_hitung, penjelasan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    satu.kode,
                    potret.id_snapshot,
                    preset.id_preset,
                    _bp(satu.skor_faktor("kualitas")),
                    _bp(satu.skor_faktor("nilai")),
                    _bp(satu.skor_faktor("momentum")),
                    _bp(satu.skor_faktor("volatilitas")),
                    _bp(satu.skor_total) or 0,
                    satu.peringkat,
                    waktu,
                    VERSI_HITUNG,
                    satu.penjelasan,
                ),
            )
    return len(hasil)


def _bp(skor: float | None) -> int | None:
    """Skor 0–100 → basis poin 0–10000; `None` tetap `None` (faktor tidak dinilai, AC-3)."""
    if skor is None:
        return None
    return max(0, min(10000, round(skor * 100)))
