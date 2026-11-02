"""Penyaringan (F2, PRD 9.4) dan preset berversi (K6, PRD 8.3).

Dua hal yang tinggal di berkas ini, dan alasannya berdampingan:

* **Preset hidup di basis data, bukan di berkas yang bisa disunting** (K6). Arti sebuah skor
  lama tidak boleh berubah diam-diam ketika seseorang mengubah ambangnya: setiap perubahan
  menaikkan versi dan **menambah** baris, sedangkan baris lama tetap ada dan tetap tak berubah.
* **Penilaian kriteria menghasilkan alasan per kriteria**, bukan sekadar lolos/gagal. PRD 9.4
  meminta "daftar emiten lolos beserta alasan lolos/gagal per kriteria"; tanpa itu, saringan
  menjadi kotak hitam yang tidak bisa dipertanggungjawabkan.

Tiga keadaan penilaian, dan bedanya penting:

* `True`  — kriteria terpenuhi;
* `False` — kriteria tidak terpenuhi (nilainya ada, ambangnya diketahui);
* `None`  — kriteria **tidak bisa dinilai** karena metriknya "tidak dihitung".

`None` tidak pernah dianggap lolos. Emiten yang punya kriteria `None` dikeluarkan dari daftar
lolos dan dilaporkan terpisah sebagai "tidak bisa disaring" beserta sebabnya — mengeluarkannya
tanpa suara akan membuat laporan terlihat lebih rapi daripada keadaannya (aturan keras 7, AC-9).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from mejasaham import db, tampilan
from mejasaham.berkas import PENANDA_NOTASI_TIDAK_LENGKAP
from mejasaham.ingesti import GalatIngesti, NotasiKhusus
from mejasaham.metrik import Nilai, metrik_semua
from mejasaham.potret import Potret

#: Kriteria yang **boleh** ada di preset. Daftar ini juga ada di CHECK `preset_kriteria`
#: (`skema.py`), dan pengulangannya disengaja: teks migrasi yang sudah dirilis membeku (T9),
#: sehingga ia tidak boleh dibangkitkan dari konstanta yang ikut berubah. Yang menjaga keduanya
#: tetap sama adalah uji `test_kedua_preset_bawaan_tersimpan_pada_basis_data_kosong`, sedangkan
#: `_periksa_preset` memastikan pelanggarannya berhenti dengan pesan yang menyebut namanya —
#: bukan `sqlite3.IntegrityError` mentah di tengah penulisan.
KRITERIA_SAH = (
    "adtv20",
    "roe_5t",
    "cfo_ni",
    "coverage",
    "der",
    "cagr_pendapatan",
    "npl_kotor",
    "car",
    "bopo",
    "nim",
    "per_relatif_sektor",
    "pbv_relatif_sektor",
    "tren_ma200",
    "kekuatan_relatif",
    "momentum_12_1",
    "pengecualian_notasi",
)

#: Metrik yang boleh diberi bobot (PRD 9.5.1 + set bank & siklikal). Sama alasannya dengan
#: `KRITERIA_SAH`: daftarnya juga ada di CHECK `preset_bobot_metrik`.
METRIK_SAH = (
    "roe_5t",
    "cfo_ni",
    "coverage",
    "der",
    "cagr_pendapatan",
    "npl_kotor",
    "car",
    "bopo",
    "nim",
    "per",
    "per_normalisasi",
    "pbv",
    "ev_ebitda",
    "imbal_hasil_laba_minus_sun",
    "imbal_hasil_dividen",
    "momentum_12_1",
    "kekuatan_relatif_6b",
    "jarak_52_minggu",
    "volatilitas_60h",
    "atr14_persen",
)

#: Jenis emiten yang punya set bobot sendiri (PRD 8.4).
JENIS_SAH = ("umum", "bank_keuangan", "siklikal_komoditas")

#: Faktor skor (PRD 9.5). Ditulis di sini karena preset yang menyimpannya; `skor.py` memakainya
#: sebagai urutan tetap supaya penjelasan skor selalu tampil dalam urutan yang sama.
FAKTOR_SAH = ("kualitas", "nilai", "momentum", "volatilitas")

#: Kriteria yang tidak berlaku untuk bank & lembaga keuangan (PRD 8.4, AC-16).
KRITERIA_BUKAN_BANK = ("cfo_ni", "coverage", "der")

#: Kriteria yang **hanya** berlaku untuk bank & lembaga keuangan (PRD 8.4, Q6).
KRITERIA_HANYA_BANK = ("npl_kotor", "car", "bopo", "nim")

#: Kriteria yang ambangnya "semakin kecil semakin baik" (PRD 8.2). Sisanya "semakin besar
#: semakin baik". Ditulis sekali di sini supaya arah penilaian tidak tersebar di beberapa tempat.
KRITERIA_RENDAH_BAIK = ("der", "npl_kotor", "bopo")

#: Kriteria yang ambangnya **ditampilkan** sebagai persen (bukan rasio). Ini urusan tampilan
#: saja: perbandingannya selalu mengikuti `satuan` metriknya (lihat `_ambang`).
KRITERIA_PERSEN = ("roe_5t", "npl_kotor", "car", "bopo", "nim")


@dataclass(frozen=True)
class BobotMetrik:
    faktor: str
    metrik: str
    jenis_emiten: str
    bobot_bp: int
    arah: str  # 'tinggi_baik' | 'rendah_baik'


@dataclass(frozen=True)
class Kriteria:
    kriteria: str
    urutan: int
    aktif: bool = True
    ambang_rupiah: int | None = None
    ambang_bp: int | None = None
    pembanding: str | None = None


@dataclass(frozen=True)
class Preset:
    id_preset: str
    nama: str
    versi: int
    horizon: str
    dibuat_pada: date
    keterangan: str
    kriteria: tuple[Kriteria, ...]
    bobot_faktor: Mapping[str, int]
    bobot_metrik: tuple[BobotMetrik, ...]

    def bobot_untuk(self, faktor: str, jenis: str) -> tuple[BobotMetrik, ...]:
        """Bobot metrik satu faktor untuk satu jenis emiten.

        Set khusus (`bank_keuangan`, `siklikal_komoditas`) menimpa set `umum` bila ada; kalau
        tidak, set `umum` yang dipakai (PRD 8.4).
        """
        khusus = tuple(
            satu
            for satu in self.bobot_metrik
            if satu.faktor == faktor and satu.jenis_emiten == jenis
        )
        if khusus:
            return khusus
        return tuple(
            satu
            for satu in self.bobot_metrik
            if satu.faktor == faktor and satu.jenis_emiten == "umum"
        )


@dataclass(frozen=True)
class PenilaianKriteria:
    """Hasil satu kriteria untuk satu emiten.

    `berlaku=False` berarti kriteria itu **memang tidak diterapkan** pada jenis emiten ini
    (mis. DER untuk bank, NPL untuk emiten non-bank) — bedanya penting dari `lolos=None`, yang
    berarti kriteria berlaku tetapi metriknya tidak bisa dihitung.
    """

    kriteria: str
    lolos: bool | None
    nilai: float | None
    satuan: str
    ambang: str
    alasan: str = ""
    berlaku: bool = True


@dataclass(frozen=True)
class HasilSaring:
    kode: str
    lolos: bool
    penilaian: tuple[PenilaianKriteria, ...]

    @property
    def tidak_bisa_dinilai(self) -> tuple[PenilaianKriteria, ...]:
        return tuple(satu for satu in self.penilaian if satu.berlaku and satu.lolos is None)

    @property
    def berlaku(self) -> tuple[PenilaianKriteria, ...]:
        return tuple(satu for satu in self.penilaian if satu.berlaku)

    def ringkas(self) -> str:
        gagal = [satu for satu in self.penilaian if satu.lolos is False]
        if self.lolos:
            return "lolos"
        if self.tidak_bisa_dinilai:
            sebab = "; ".join(
                f"{satu.kriteria}: {satu.alasan}" for satu in self.tidak_bisa_dinilai[:2]
            )
            return f"tidak bisa dinilai — {sebab}"
        return "gagal — " + "; ".join(
            f"{satu.kriteria} {satu.ambang}" + (f" ({satu.alasan})" if satu.alasan else "")
            for satu in gagal[:3]
        )


# ---------------------------------------------------------------------------------------
# Preset bawaan (K1: dua ember)
# ---------------------------------------------------------------------------------------


def _bobot_umum() -> tuple[BobotMetrik, ...]:
    """Pemetaan metrik ke faktor menurut PRD 9.5.1 (bobot awal, disimpan di preset)."""
    return (
        # Kualitas 30%: ROE 30 · CFO/NI 20 · Coverage 15 · DER 15 · CAGR pendapatan 20
        BobotMetrik("kualitas", "roe_5t", "umum", 3000, "tinggi_baik"),
        BobotMetrik("kualitas", "cfo_ni", "umum", 2000, "tinggi_baik"),
        BobotMetrik("kualitas", "coverage", "umum", 1500, "tinggi_baik"),
        BobotMetrik("kualitas", "der", "umum", 1500, "rendah_baik"),
        BobotMetrik("kualitas", "cagr_pendapatan", "umum", 2000, "tinggi_baik"),
        # Nilai 30%: PER 30 · PBV 25 · EV/EBITDA 25 · (imbal hasil laba − SUN) 20
        BobotMetrik("nilai", "per", "umum", 3000, "rendah_baik"),
        BobotMetrik("nilai", "pbv", "umum", 2500, "rendah_baik"),
        BobotMetrik("nilai", "ev_ebitda", "umum", 2500, "rendah_baik"),
        BobotMetrik("nilai", "imbal_hasil_laba_minus_sun", "umum", 2000, "tinggi_baik"),
        # Momentum 25%: momentum 12-1 40 · kekuatan relatif 40 · jarak 52 minggu 20
        BobotMetrik("momentum", "momentum_12_1", "umum", 4000, "tinggi_baik"),
        BobotMetrik("momentum", "kekuatan_relatif_6b", "umum", 4000, "tinggi_baik"),
        BobotMetrik("momentum", "jarak_52_minggu", "umum", 2000, "tinggi_baik"),
        # Volatilitas rendah 15%: volatilitas 60 · ATR% 40 (lebih rendah = lebih tinggi)
        BobotMetrik("volatilitas", "volatilitas_60h", "umum", 6000, "rendah_baik"),
        BobotMetrik("volatilitas", "atr14_persen", "umum", 4000, "rendah_baik"),
    )


def _bobot_bank() -> tuple[BobotMetrik, ...]:
    """Set bank (PRD 9.5.1): kualitas ROE 30 · NPL 25 · CAR 15 · BOPO 15 · NIM 15.

    Nilai: PER 40 · PBV 40 · imbal hasil dividen 20. DER, CFO/NI, dan coverage **tidak ada**
    di sini — bukan bernilai nol, memang tidak diterapkan (PRD 8.4, AC-16).
    """
    return (
        BobotMetrik("kualitas", "roe_5t", "bank_keuangan", 3000, "tinggi_baik"),
        BobotMetrik("kualitas", "npl_kotor", "bank_keuangan", 2500, "rendah_baik"),
        BobotMetrik("kualitas", "car", "bank_keuangan", 1500, "tinggi_baik"),
        BobotMetrik("kualitas", "bopo", "bank_keuangan", 1500, "rendah_baik"),
        BobotMetrik("kualitas", "nim", "bank_keuangan", 1500, "tinggi_baik"),
        BobotMetrik("nilai", "per", "bank_keuangan", 4000, "rendah_baik"),
        BobotMetrik("nilai", "pbv", "bank_keuangan", 4000, "rendah_baik"),
        BobotMetrik("nilai", "imbal_hasil_dividen", "bank_keuangan", 2000, "tinggi_baik"),
    )


def _bobot_siklikal() -> tuple[BobotMetrik, ...]:
    """Set siklikal (PRD 8.4): valuasi memakai **PER normalisasi**, PER TTM tetap ditampilkan."""
    return (
        BobotMetrik("nilai", "per_normalisasi", "siklikal_komoditas", 3000, "rendah_baik"),
        BobotMetrik("nilai", "pbv", "siklikal_komoditas", 2500, "rendah_baik"),
        BobotMetrik("nilai", "ev_ebitda", "siklikal_komoditas", 2500, "rendah_baik"),
        BobotMetrik("nilai", "imbal_hasil_laba_minus_sun", "siklikal_komoditas", 2000, "tinggi_baik"),
    )


def _kriteria_likuiditas() -> Kriteria:
    """ADTV20 ≥ Rp 5 miliar (PRD 8.2), ambang yang sama dengan definisi emiten likuid (K9)."""
    return Kriteria("adtv20", urutan=1, ambang_rupiah=5_000_000_000)


def preset_bawaan(hari_ini: date) -> tuple[Preset, ...]:
    """Dua preset awal sesuai K1 — **usulan bobot**, bukan kebenaran yang diturunkan PRD.

    Preset (a) memakai bobot faktor bawaan PRD 9.5 (kualitas 30 / nilai 30 / momentum 25 /
    volatilitas 15) untuk horizon bulanan. Preset (b) adalah ember momentum berhorizon mingguan
    (K1); bobotnya **belum ditetapkan PRD** dan yang tertulis di sini adalah usulan awal yang
    menunggu persetujuan — bukan angka yang diambil dari spesifikasi.
    """
    kualitas_nilai = Preset(
        id_preset="kualitas-nilai/v1",
        nama="kualitas-nilai",
        versi=1,
        horizon="bulanan",
        dibuat_pada=hari_ini,
        keterangan=(
            "Ember kualitas+nilai (K1). Bobot faktor & metrik mengikuti PRD 9.5 dan 9.5.1. "
            "Ambang mengikuti PRD 8.2; semuanya pengaturan awal yang bisa direvisi lewat versi baru."
        ),
        kriteria=(
            _kriteria_likuiditas(),
            Kriteria("pengecualian_notasi", urutan=2),
            Kriteria("roe_5t", urutan=3, ambang_bp=1200),
            Kriteria("cfo_ni", urutan=4, ambang_bp=8000),
            Kriteria("coverage", urutan=5, ambang_bp=30000),
            Kriteria("der", urutan=6, ambang_bp=20000),
            Kriteria("per_relatif_sektor", urutan=7, ambang_bp=12000, pembanding="median_sektor"),
            Kriteria("pbv_relatif_sektor", urutan=8, ambang_bp=15000, pembanding="median_sektor"),
            Kriteria("tren_ma200", urutan=9),
            Kriteria("kekuatan_relatif", urutan=10, ambang_bp=0),
            # Ambang set bank (PRD 8.4, Q6). Tiga kriteria di atas (CFO/NI, coverage, DER)
            # otomatis tidak berlaku untuk bank, dan empat ini otomatis tidak berlaku untuk
            # non-bank — jadi satu preset tetap benar untuk kedua jenis emiten (AC-16).
            Kriteria("npl_kotor", urutan=11, ambang_bp=300),
            Kriteria("car", urutan=12, ambang_bp=1400),
            Kriteria("bopo", urutan=13, ambang_bp=8500),
            Kriteria("nim", urutan=14, ambang_bp=350),
        ),
        bobot_faktor={"kualitas": 3000, "nilai": 3000, "momentum": 2500, "volatilitas": 1500},
        bobot_metrik=_bobot_umum() + _bobot_bank() + _bobot_siklikal(),
    )

    momentum = Preset(
        id_preset="momentum/v1",
        nama="momentum",
        versi=1,
        horizon="mingguan",
        dibuat_pada=hari_ini,
        keterangan=(
            "Ember momentum (K1), horizon mingguan. [USULAN BELUM DIKUNCI] Bobot faktornya "
            "belum ditetapkan PRD; yang dipakai di sini adalah usulan awal dan menunggu "
            "persetujuan pengguna. Kriterianya sengaja tidak memuat saringan fundamental."
        ),
        kriteria=(
            _kriteria_likuiditas(),
            Kriteria("pengecualian_notasi", urutan=2),
            Kriteria("tren_ma200", urutan=3),
            Kriteria("momentum_12_1", urutan=4, ambang_bp=0),
            Kriteria("kekuatan_relatif", urutan=5, ambang_bp=0),
        ),
        bobot_faktor={"kualitas": 1000, "nilai": 1000, "momentum": 6000, "volatilitas": 2000},
        bobot_metrik=_bobot_umum() + _bobot_bank() + _bobot_siklikal(),
    )
    return (kualitas_nilai, momentum)


# ---------------------------------------------------------------------------------------
# Simpan & muat preset
# ---------------------------------------------------------------------------------------


def _sidik_preset(preset: Preset) -> str:
    """Sidik isi preset: muat ulang yang sama tidak menambah baris, perubahan isi berteriak."""
    isi = {
        "id_preset": preset.id_preset,
        "nama": preset.nama,
        "versi": preset.versi,
        "horizon": preset.horizon,
        "keterangan": preset.keterangan,
        "kriteria": [
            [satu.kriteria, satu.urutan, int(satu.aktif), satu.ambang_rupiah, satu.ambang_bp, satu.pembanding]
            for satu in sorted(preset.kriteria, key=lambda s: (s.urutan, s.kriteria))
        ],
        "bobot_faktor": dict(sorted(preset.bobot_faktor.items())),
        "bobot_metrik": sorted(
            [satu.faktor, satu.metrik, satu.jenis_emiten, satu.bobot_bp, satu.arah]
            for satu in preset.bobot_metrik
        ),
    }
    return json.dumps(isi, ensure_ascii=False, sort_keys=True)


def _periksa_preset(preset: Preset) -> None:
    """Tolak preset yang tidak bisa disimpan, **dengan menyebut nama pelanggarnya**.

    Tanpa pemeriksaan ini, kriteria atau metrik yang tidak dikenal baru ketahuan sebagai
    `sqlite3.IntegrityError` mentah di tengah penulisan — pesannya menyebut nama constraint,
    bukan nama kriteria yang salah, dan pemanggil tidak tahu bagian mana yang harus diperbaiki.
    """
    for satu in preset.kriteria:
        if satu.kriteria not in KRITERIA_SAH:
            raise GalatIngesti(
                f"preset {preset.id_preset}: kriteria {satu.kriteria!r} tidak dikenal. "
                f"Yang sah: {', '.join(KRITERIA_SAH)}"
            )
        if satu.urutan <= 0:
            raise GalatIngesti(f"preset {preset.id_preset}: urutan kriteria harus > 0")
    for satu in preset.bobot_metrik:
        if satu.metrik not in METRIK_SAH:
            raise GalatIngesti(
                f"preset {preset.id_preset}: metrik {satu.metrik!r} tidak dikenal. "
                f"Yang sah: {', '.join(METRIK_SAH)}"
            )
        if satu.jenis_emiten not in JENIS_SAH:
            raise GalatIngesti(
                f"preset {preset.id_preset}: jenis emiten {satu.jenis_emiten!r} tidak dikenal. "
                f"Yang sah: {', '.join(JENIS_SAH)}"
            )
        if satu.arah not in ("tinggi_baik", "rendah_baik"):
            raise GalatIngesti(
                f"preset {preset.id_preset}: arah {satu.arah!r} tidak dikenal "
                "(yang sah: tinggi_baik, rendah_baik)"
            )
    if not preset.bobot_faktor or sum(preset.bobot_faktor.values()) <= 0:
        raise GalatIngesti(
            f"preset {preset.id_preset}: bobot faktor kosong atau seluruhnya nol, "
            "sehingga tidak ada yang bisa dinilai"
        )
    for faktor in preset.bobot_faktor:
        if faktor not in FAKTOR_SAH:
            raise GalatIngesti(
                f"preset {preset.id_preset}: faktor {faktor!r} tidak dikenal "
                f"(yang sah: {', '.join(FAKTOR_SAH)})"
            )


def simpan_preset(sambungan: sqlite3.Connection, preset: Preset) -> bool:
    """Simpan preset bila belum ada. Kembalikan True bila baris baru ditulis.

    Idempoten: isi yang sama tidak menambah baris. Isi yang **berbeda** pada `id_preset` yang
    sama ditolak berisik — itulah yang mencegah arti skor lama berubah diam-diam (K6).
    """
    _periksa_preset(preset)
    sidik_lama = baca_sidik_preset(sambungan, preset.id_preset)
    if sidik_lama is not None:
        if sidik_lama != _sidik_preset(preset):
            raise GalatIngesti(
                f"preset {preset.id_preset} sudah ada dengan isi berbeda. Arti skor lama tidak "
                "boleh berubah: naikkan versinya (mis. "
                f"{preset.nama}/v{preset.versi + 1}) dan simpan sebagai preset baru."
            )
        return False

    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO preset_saring (id_preset, nama, versi, horizon, keterangan, dibuat_pada)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                preset.id_preset,
                preset.nama,
                preset.versi,
                preset.horizon,
                preset.keterangan,
                preset.dibuat_pada.isoformat(),
            ),
        )
        for satu in preset.kriteria:
            koneksi.execute(
                "INSERT INTO preset_kriteria (id_preset, kriteria, urutan, aktif, ambang_rupiah,"
                " ambang_bp, pembanding) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    preset.id_preset,
                    satu.kriteria,
                    satu.urutan,
                    int(satu.aktif),
                    satu.ambang_rupiah,
                    satu.ambang_bp,
                    satu.pembanding,
                ),
            )
        for faktor, bobot in sorted(preset.bobot_faktor.items()):
            koneksi.execute(
                "INSERT INTO preset_bobot_faktor (id_preset, faktor, bobot_bp) VALUES (?, ?, ?)",
                (preset.id_preset, faktor, bobot),
            )
        for satu in preset.bobot_metrik:
            koneksi.execute(
                "INSERT INTO preset_bobot_metrik (id_preset, faktor, metrik, jenis_emiten,"
                " bobot_bp, arah) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    preset.id_preset,
                    satu.faktor,
                    satu.metrik,
                    satu.jenis_emiten,
                    satu.bobot_bp,
                    satu.arah,
                ),
            )
        koneksi.execute(
            "INSERT INTO log_jalan (waktu, proses, hasil, pesan) VALUES (?, 'preset', 'sukses', ?)",
            (db.waktu_iso(), f"preset {preset.id_preset} disimpan"),
        )
    return True


def baca_sidik_preset(sambungan: sqlite3.Connection, id_preset: str) -> str | None:
    """Sidik isi preset yang tersimpan, atau None bila preset itu belum ada."""
    kepala = sambungan.execute(
        "SELECT * FROM preset_saring WHERE id_preset = ?", (id_preset,)
    ).fetchone()
    if kepala is None:
        return None
    kriteria = sambungan.execute(
        "SELECT kriteria, urutan, aktif, ambang_rupiah, ambang_bp, pembanding FROM preset_kriteria"
        " WHERE id_preset = ?",
        (id_preset,),
    ).fetchall()
    faktor = sambungan.execute(
        "SELECT faktor, bobot_bp FROM preset_bobot_faktor WHERE id_preset = ?", (id_preset,)
    ).fetchall()
    metrik = sambungan.execute(
        "SELECT faktor, metrik, jenis_emiten, bobot_bp, arah FROM preset_bobot_metrik"
        " WHERE id_preset = ?",
        (id_preset,),
    ).fetchall()
    isi = {
        "id_preset": kepala["id_preset"],
        "nama": kepala["nama"],
        "versi": kepala["versi"],
        "horizon": kepala["horizon"],
        "keterangan": kepala["keterangan"],
        "kriteria": [
            [b["kriteria"], b["urutan"], b["aktif"], b["ambang_rupiah"], b["ambang_bp"], b["pembanding"]]
            for b in sorted(kriteria, key=lambda s: (s["urutan"], s["kriteria"]))
        ],
        "bobot_faktor": {b["faktor"]: b["bobot_bp"] for b in sorted(faktor, key=lambda s: s["faktor"])},
        "bobot_metrik": sorted(
            [b["faktor"], b["metrik"], b["jenis_emiten"], b["bobot_bp"], b["arah"]] for b in metrik
        ),
    }
    return json.dumps(isi, ensure_ascii=False, sort_keys=True)


def muat_preset(sambungan: sqlite3.Connection, id_preset: str) -> Preset:
    """Baca satu preset dari basis data. Preset yang tidak ada ditolak dengan daftar yang ada."""
    kepala = sambungan.execute(
        "SELECT * FROM preset_saring WHERE id_preset = ?", (id_preset,)
    ).fetchone()
    if kepala is None:
        tersedia = [
            baris["id_preset"]
            for baris in sambungan.execute("SELECT id_preset FROM preset_saring ORDER BY id_preset")
        ]
        raise GalatIngesti(
            f"preset {id_preset!r} tidak ada. Yang tersedia: {', '.join(tersedia) or '(belum ada)'}"
        )
    kriteria = tuple(
        Kriteria(
            kriteria=baris["kriteria"],
            urutan=baris["urutan"],
            aktif=bool(baris["aktif"]),
            ambang_rupiah=baris["ambang_rupiah"],
            ambang_bp=baris["ambang_bp"],
            pembanding=baris["pembanding"],
        )
        for baris in sambungan.execute(
            "SELECT * FROM preset_kriteria WHERE id_preset = ? ORDER BY urutan", (id_preset,)
        )
    )
    bobot_faktor = {
        baris["faktor"]: baris["bobot_bp"]
        for baris in sambungan.execute(
            "SELECT faktor, bobot_bp FROM preset_bobot_faktor WHERE id_preset = ?", (id_preset,)
        )
    }
    bobot_metrik = tuple(
        BobotMetrik(
            faktor=baris["faktor"],
            metrik=baris["metrik"],
            jenis_emiten=baris["jenis_emiten"],
            bobot_bp=baris["bobot_bp"],
            arah=baris["arah"],
        )
        for baris in sambungan.execute(
            "SELECT * FROM preset_bobot_metrik WHERE id_preset = ?", (id_preset,)
        )
    )
    return Preset(
        id_preset=kepala["id_preset"],
        nama=kepala["nama"],
        versi=kepala["versi"],
        horizon=kepala["horizon"],
        dibuat_pada=date.fromisoformat(kepala["dibuat_pada"]),
        keterangan=kepala["keterangan"] or "",
        kriteria=kriteria,
        bobot_faktor=bobot_faktor,
        bobot_metrik=bobot_metrik,
    )


def preset_terbaru(sambungan: sqlite3.Connection, nama: str) -> Preset:
    """Versi terakhir satu preset menurut namanya (PRD 8.3: perubahan menaikkan versi)."""
    baris = sambungan.execute(
        "SELECT id_preset FROM preset_saring WHERE nama = ? ORDER BY versi DESC LIMIT 1", (nama,)
    ).fetchone()
    if baris is None:
        raise GalatIngesti(f"preset bernama {nama!r} tidak ada di basis data")
    return muat_preset(sambungan, baris["id_preset"])


def daftar_preset(sambungan: sqlite3.Connection) -> tuple[tuple[str, str, int, str], ...]:
    return tuple(
        (baris["id_preset"], baris["nama"], baris["versi"], baris["horizon"])
        for baris in sambungan.execute(
            "SELECT id_preset, nama, versi, horizon FROM preset_saring ORDER BY nama, versi"
        )
    )


# ---------------------------------------------------------------------------------------
# Penilaian kriteria (F2)
# ---------------------------------------------------------------------------------------


def _median_sektor(
    metrik_semesta: Mapping[str, Mapping[str, Nilai]],
    emiten_sektor: Mapping[str, str],
    sektor: str,
    nama_metrik: str,
) -> float | None:
    """Median satu metrik di dalam sektor — pembanding untuk kriteria relatif (PRD 8.2)."""
    angka = [
        float(nilai.nilai)
        for kode, kumpulan in metrik_semesta.items()
        if emiten_sektor.get(kode) == sektor
        and (nilai := kumpulan.get(nama_metrik)) is not None
        and nilai.ada
    ]
    if not angka:
        return None
    angka.sort()
    tengah = len(angka) // 2
    return angka[tengah] if len(angka) % 2 else (angka[tengah - 1] + angka[tengah]) / 2


def _metrik_untuk(kriteria: str, jenis: str) -> str:
    """Metrik yang dinilai sebuah kriteria, menurut jenis emiten (PRD 8.4)."""
    if kriteria in ("per_relatif_sektor", "pbv_relatif_sektor"):
        if kriteria == "per_relatif_sektor" and jenis == "siklikal_komoditas":
            return "per_normalisasi"
        return "per" if kriteria == "per_relatif_sektor" else "pbv"
    return {
        "tren_ma200": "tren_ma200",
        "kekuatan_relatif": "kekuatan_relatif_6b",
    }.get(kriteria, kriteria)


def notasi_terverifikasi(baris: Sequence[NotasiKhusus]) -> bool:
    """Data notasi hanya dianggap lengkap bila ada isinya dan tidak membawa penanda kekurangan."""
    return bool(baris) and not any(
        PENANDA_NOTASI_TIDAK_LENGKAP in (satu.keterangan or "") for satu in baris
    )


def sebab_peringkat_sementara(*, notasi_lengkap: bool, sambungan_sementara: str | None) -> str:
    """Kalimat sebab peringkat sementara (PRD 7.3; K97 d); kosong bila daftarnya boleh disebut kandidat.

    Satu tempat untuk saringan dan dasbor, supaya dua layar tidak memberi dua sebab berbeda
    untuk skor yang sama.
    """
    bagian = []
    if not notasi_lengkap:
        bagian.append(
            "data notasi khusus (suspensi/UMA/papan pemantauan) belum ada atau belum lengkap, "
            "jadi status tiap emiten belum terverifikasi; saham tersuspensi bisa muncul di "
            "daftar ini (PRD 7.3)"
        )
    if sambungan_sementara is not None:
        bagian.append(f"deret harga resmi: {sambungan_sementara} (K97 d)")
    return "; ".join(bagian)


def _notasi_aktif(potret: Potret, kode: str) -> tuple[str, ...]:
    """Jenis notasi khusus yang masih berjalan pada tanggal snapshot (K9, PRD 7.1)."""
    hasil: list[str] = []
    for satu in potret.notasi:
        if satu.kode != kode:
            continue
        if satu.tanggal_mulai > potret.tanggal_data:
            continue
        if satu.tanggal_selesai is not None and satu.tanggal_selesai < potret.tanggal_data:
            continue
        hasil.append(satu.jenis)
    return tuple(hasil)


def saring_emiten(
    potret: Potret,
    kode: str,
    preset: Preset,
    metrik: Mapping[str, Nilai],
    *,
    jenis: str,
    median_per: float | None,
    median_pbv: float | None,
) -> HasilSaring:
    """Nilai seluruh kriteria aktif satu emiten. Setiap penilaian membawa alasannya."""
    penilaian: list[PenilaianKriteria] = []

    for kriteria in sorted(preset.kriteria, key=lambda satu: satu.urutan):
        if not kriteria.aktif:
            continue
        nama = kriteria.kriteria

        if nama == "pengecualian_notasi":
            if not potret.notasi:
                # **"Tidak ada data" bukan "bersih".** Sebelum ini, tabel notasi yang kosong
                # membuat kriteria ini lolos untuk seluruh emiten — padahal laporan mutu sendiri
                # menyatakan emiten tanpa penanda itu "belum terverifikasi dan tidak dijadikan
                # kandidat otomatis" (PRD 7.3). Dua bagian aplikasi menyatakan hal yang
                # berlawanan, dan yang menang adalah yang diam.
                #
                # Yang dipakai sekarang: kriteria ini **tidak diterapkan** (bukan gagal, bukan
                # lolos) — sama seperti kriteria bank pada emiten non-bank — sehingga peringkat
                # tetap bisa dihitung, sementara kata "kandidat" ditahan di lapisan pelaporan dan
                # keadaannya disebut mencolok. Menjadikannya `lolos=None` akan lebih aman tetapi
                # mematikan seluruh saringan; itu justru mendorong orang menambal berkas kosong.
                penilaian.append(
                    PenilaianKriteria(
                        kriteria=nama,
                        lolos=None,
                        nilai=None,
                        satuan="",
                        ambang="tanpa notasi khusus / suspensi / papan pemantauan",
                        alasan=(
                            "tidak ada data notasi khusus di basis data, sehingga status emiten "
                            "ini belum terverifikasi (PRD 7.3) — kriteria tidak diterapkan, dan "
                            "hasilnya bukan kandidat"
                        ),
                        berlaku=False,
                    )
                )
                continue
            aktif = _notasi_aktif(potret, kode)
            penilaian.append(
                PenilaianKriteria(
                    kriteria=nama,
                    lolos=not aktif,
                    nilai=None,
                    satuan="",
                    ambang="tanpa notasi khusus / suspensi / papan pemantauan",
                    alasan=("" if not aktif else f"tercatat: {', '.join(sorted(set(aktif)))}"),
                )
            )
            continue

        # Saringan fundamental mengikuti jenis emiten (PRD 8.4, AC-16). Kriteria yang tidak
        # berlaku ditandai `berlaku=False` — ia tidak dihitung gagal, dan tidak juga dihitung
        # lolos; ia memang tidak diterapkan.
        if nama in KRITERIA_BUKAN_BANK and jenis == "bank_keuangan":
            penilaian.append(
                PenilaianKriteria(
                    kriteria=nama,
                    lolos=None,
                    nilai=None,
                    satuan="",
                    ambang="tidak berlaku untuk bank & lembaga keuangan",
                    alasan="tidak diterapkan menurut PRD 8.4 (bukan gagal, bukan lolos)",
                    berlaku=False,
                )
            )
            continue
        if nama in KRITERIA_HANYA_BANK and jenis != "bank_keuangan":
            penilaian.append(
                PenilaianKriteria(
                    kriteria=nama,
                    lolos=None,
                    nilai=None,
                    satuan="",
                    ambang="hanya untuk bank & lembaga keuangan",
                    alasan="rasio bank tidak diterapkan pada emiten non-bank (PRD 8.4)",
                    berlaku=False,
                )
            )
            continue

        metrik_nama = _metrik_untuk(nama, jenis)
        nilai = metrik.get(metrik_nama)
        if nilai is None or not nilai.ada:
            penilaian.append(
                PenilaianKriteria(
                    kriteria=nama,
                    lolos=None,
                    nilai=None,
                    satuan="",
                    ambang=_teks_ambang(kriteria),
                    alasan=(nilai.alasan if nilai is not None and nilai.alasan else "metrik tidak tersedia"),
                )
            )
            continue

        angka = float(nilai.nilai or 0)
        if nama == "tren_ma200":
            penilaian.append(
                PenilaianKriteria(
                    kriteria=nama,
                    lolos=angka > 0,
                    nilai=angka,
                    satuan="boolean",
                    ambang="harga di atas MA200",
                    alasan="" if angka > 0 else "harga penutupan di bawah MA200",
                )
            )
            continue

        if kriteria.pembanding == "median_sektor":
            median = median_per if nama == "per_relatif_sektor" else median_pbv
            if median is None or median <= 0:
                penilaian.append(
                    PenilaianKriteria(
                        kriteria=nama,
                        lolos=None,
                        nilai=angka,
                        satuan=nilai.satuan,
                        ambang=_teks_ambang(kriteria),
                        alasan=f"median sektor untuk {metrik_nama} belum bisa dihitung",
                    )
                )
                continue
            batas = median * (kriteria.ambang_bp or 0) / 10000
            penilaian.append(
                PenilaianKriteria(
                    kriteria=nama,
                    lolos=angka <= batas,
                    nilai=angka,
                    satuan=nilai.satuan,
                    ambang=(
                        f"<= {tampilan.angka(batas, 2)} "
                        f"({_teks_ambang(kriteria)}, median sektor {tampilan.angka(median, 2)})"
                    ),
                    alasan=(
                        ""
                        if angka <= batas
                        else f"{tampilan.angka(angka, 2)} di atas batas {tampilan.angka(batas, 2)}"
                    ),
                )
            )
            continue

        if kriteria.ambang_rupiah is not None:
            batas_rupiah = float(kriteria.ambang_rupiah)
            penilaian.append(
                PenilaianKriteria(
                    kriteria=nama,
                    lolos=angka >= batas_rupiah,
                    nilai=angka,
                    satuan=nilai.satuan,
                    ambang=f">= {tampilan.rupiah_singkat(batas_rupiah)}",
                    alasan=(
                        ""
                        if angka >= batas_rupiah
                        else f"{tampilan.rupiah_singkat(angka)} di bawah ambang"
                    ),
                )
            )
            continue

        # Tingkat/rasio dalam basis poin. Arahnya mengikuti kriteria, bukan metriknya:
        # DER/NPL/BOPO lebih rendah lebih baik; ROE/CAR/NIM lebih tinggi lebih baik.
        # Satuannya disamakan lewat `satuan` metriknya, bukan lewat daftar nama kriteria:
        # metrik bank mengembalikan basis poin (190 bp = 1,9%), metrik lain mengembalikan rasio
        # (ROE 0,12). Membandingkan basis poin dengan rasio membuat ambang bank **selalu** lolos.
        batas, ambang_teks = _ambang(kriteria, nilai.satuan)
        if nama in KRITERIA_RENDAH_BAIK:
            lolos = angka <= batas
            tanda = "<="
        else:
            lolos = angka >= batas
            tanda = ">="
        penilaian.append(
            PenilaianKriteria(
                kriteria=nama,
                lolos=lolos,
                nilai=angka,
                satuan=nilai.satuan,
                ambang=f"{tanda} {ambang_teks}",
                alasan="" if lolos else f"{_tampil(angka, nilai.satuan)} tidak memenuhi {tanda} {ambang_teks}",
            )
        )

    # Kriteria yang tidak bisa dinilai (`lolos=None` **dan** berlaku) bukan lolos: emiten
    # dikeluarkan dari daftar lolos, tetapi sebabnya ikut terbawa supaya tidak hilang dari
    # pandangan (aturan keras 7, AC-9). Kriteria yang tidak berlaku tidak dihitung sama sekali.
    dinilai = [satu for satu in penilaian if satu.berlaku]
    lolos = bool(dinilai) and all(satu.lolos is True for satu in dinilai)
    return HasilSaring(kode=kode, lolos=lolos, penilaian=tuple(penilaian))


def saring_semesta(
    potret: Potret,
    preset: Preset,
    *,
    hanya_kode: Iterable[str] | None = None,
    metrik: Mapping[str, Mapping[str, Nilai]] | None = None,
    semesta: Iterable[str] | None = None,
) -> tuple[HasilSaring, ...]:
    """Jalankan saringan preset atas seluruh emiten dalam potret.

    `metrik` boleh diserahkan pemanggil supaya seluruh perhitungan metrik terjadi **sekali**
    untuk satu potret (saringan dan skoring memakai angka yang sama — PRD 5).

    `semesta` membatasi emiten yang dipakai menghitung **median sektor** untuk kriteria relatif.
    Pemanggilnya menyerahkan semesta likuid, karena PRD 9.5 menetapkan statistik sektor dihitung
    dari sana — memakai seluruh emiten (termasuk yang nyaris tidak ditransaksikan, yang PER-nya
    ekstrem) akan membuat ambang "≤ 1,2× median sektor" jauh lebih longgar daripada maksudnya.
    """
    daftar = tuple(hanya_kode) if hanya_kode is not None else potret.kode
    semesta_metrik = metrik if metrik is not None else metrik_semua(potret, daftar)
    pembanding = tuple(semesta) if semesta is not None else tuple(semesta_metrik)
    sektor_pembanding = {
        kode: (potret.emiten[kode].sektor_idx_ic or "")
        for kode in pembanding
        if kode in potret.emiten
    }
    sektor = {kode: (potret.emiten[kode].sektor_idx_ic or "") for kode in daftar}
    jenis = {kode: (potret.emiten[kode].jenis or "umum") for kode in daftar}

    # Median sektor dihitung sekali per (sektor, metrik), bukan sekali per emiten.
    median: dict[tuple[str, str], float | None] = {}
    for nama_sektor in set(sektor.values()):
        for nama_metrik in ("per", "pbv"):
            median[(nama_sektor, nama_metrik)] = _median_sektor(
                semesta_metrik, sektor_pembanding, nama_sektor, nama_metrik
            )

    hasil: list[HasilSaring] = []
    for kode in daftar:
        hasil.append(
            saring_emiten(
                potret,
                kode,
                preset,
                semesta_metrik[kode],
                jenis=jenis[kode],
                median_per=median[(sektor[kode], "per")],
                median_pbv=median[(sektor[kode], "pbv")],
            )
        )
    return tuple(hasil)


def semesta_likuid(
    potret: Potret,
    preset: Preset,
    *,
    metrik: Mapping[str, Mapping[str, Nilai]] | None = None,
) -> tuple[str, ...]:
    """Emiten likuid menurut K9: ADTV20 cukup **dan** lolos pengecualian notasi.

    Dipakai sebagai dasar statistik sektor & breadth (PRD 9.5), jadi ia sengaja **tidak**
    memakai kriteria fundamental: sektor tetap punya statistik meski fundamentalnya belum diimpor.
    """
    ambang = next(
        (satu.ambang_rupiah for satu in preset.kriteria if satu.kriteria == "adtv20"),
        None,
    )
    if ambang is None:
        raise GalatIngesti(f"preset {preset.id_preset} tidak punya kriteria adtv20")

    angka = metrik if metrik is not None else metrik_semua(potret)
    likuid: list[str] = []
    # Iterasi atas kunci `angka`, bukan `potret.kode`: pemanggil boleh menyerahkan himpunan
    # metrik yang lebih sempit (mis. diagnosa satu emiten), dan itu tidak boleh menjadi KeyError.
    for kode in angka:
        if _notasi_aktif(potret, kode):
            continue
        nilai = angka[kode].get("adtv20")
        if nilai is not None and nilai.ada and float(nilai.nilai or 0) >= ambang:
            likuid.append(kode)
    return tuple(likuid)


def _ambang(kriteria: Kriteria, satuan: str) -> tuple[float, str]:
    """Ambang dalam satuan **yang sama dengan metriknya**, beserta bentuk tampilannya.

    Disamakan lewat `satuan` metrik, bukan lewat daftar nama kriteria: metrik bank (NPL, CAR,
    BOPO, NIM) mengembalikan basis poin, sedangkan ROE/CFO-NI/DER mengembalikan rasio.
    Membandingkan keduanya tanpa menyamakan satuan membuat ambang bank selalu lolos.
    """
    bp = float(kriteria.ambang_bp or 0)
    if satuan == "bp":
        return bp, f"{tampilan.angka(bp / 100, 2)}%"
    return bp / 10000, tampilan.angka(bp / 10000, 2)


def _tampil(angka: float, satuan: str) -> str:
    return f"{tampilan.angka(angka / 100, 2)}%" if satuan == "bp" else tampilan.angka(angka, 2)


def _teks_ambang(kriteria: Kriteria) -> str:
    if kriteria.ambang_rupiah is not None:
        return f">= {tampilan.rupiah_singkat(float(kriteria.ambang_rupiah))}"
    if kriteria.ambang_bp is not None:
        # Tampilan saja: kriteria yang lazim dibaca sebagai persen ditulis sebagai persen.
        angka = (
            f"{tampilan.angka(kriteria.ambang_bp / 100, 2)}%"
            if kriteria.kriteria in KRITERIA_PERSEN
            else tampilan.angka(kriteria.ambang_bp / 10000, 2)
        )
        return angka + ("× median sektor" if kriteria.pembanding == "median_sektor" else "")
    return "tanpa ambang angka"


def _rupiah_singkat(angka: float) -> str:
    """Tampilan rupiah singkat (U11). Dipertahankan sebagai nama lama di dalam modul ini."""
    return tampilan.rupiah_singkat(angka)
