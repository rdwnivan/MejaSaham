"""Kalkulator risiko & ukuran posisi (F5, PRD 9.7) — pintu wajib sebelum rencana disimpan.

Modul ini menjawab satu pertanyaan: **berapa lembar yang boleh dibeli, dan berapa risikonya.**
Empat hal yang ditegakkan di sini, semuanya dari PRD:

1. **Rumusnya persis PRD 9.7.** `lembar mentah = (ekuitas × risiko per posisi) ÷ (harga masuk −
   stop + biaya & slippage per lembar)`; ukuran akhir = nilai terkecil dari lembar mentah, batas
   bobot, batas sektor, batas likuiditas, dan kas tersedia, lalu **dibulatkan ke bawah per lot**.
   Risiko nominal dihitung dari ukuran **akhir** — bukan dari ukuran mentah (PRD 10).
2. **Stop bawaan mengikuti tesis bila lebih ketat** (PRD 9.7): nilai terbesar antara
   `harga masuk − 2 × ATR14` dan `harga pembatal tesis`. Posisi hanya beli (long).
3. **Batas adalah pengaturan berversi, bukan konstanta** (PRD 8.3, K2). Nilainya dibaca dari
   `preset_risiko`, dan `rencana` menyimpan versi yang benar-benar dipakainya.
4. **Bataskah yang tidak bisa dinilai dikatakan, bukan dianggap lolos.** ADTV20 yang "tidak
   dihitung" atau `sektor_idx_ic` yang belum terisi membuat batas itu **tidak dinilai**; kolomnya
   `NULL` dan sebabnya ikut tersimpan — pola yang sama dengan `minimum` tarif broker (K22) dan
   kriteria notasi (K19). Diam-diam menganggapnya longgar akan membuat rencana yang lolos karena
   datanya tidak ada terbaca sama dengan rencana yang lolos karena benar.

**Dua tempat angka dibulatkan, dan arahnya disengaja.** Biaya per lembar dibulatkan **ke atas**
dan stop hasil rumus ATR dibulatkan **ke bawah** ke tick yang sah: keduanya membuat risiko yang
ditampilkan tidak pernah lebih kecil daripada kenyataan (PRD 10: "risiko yang ditampilkan adalah
batas bawah"). Harga masuk dan stop yang **diisi pengguna** tidak dibulatkan diam-diam — harga
yang bukan kelipatan tick ditolak beserta dua tick sah terdekat, sebab menggeser harga masuk
menggeser seluruh angka di bawahnya tanpa satu pun tanda.

**Dua suku risiko berjalan (sejak Tahap 2 langkah 3).** `risiko_berjalan_lengkap` menjumlahkan
`(penutupan terakhir − stop terkini) × lembar` untuk **posisi aktif** (F11) **ditambah** risiko
rencana yang belum dieksekusi (PRD 8.2); rencana yang sudah punya transaksi tidak dijumlahkan dua
kali. Suku yang tidak dapat dinilai — posisi tanpa stop, atau emiten tanpa harga — dilaporkan
beserta sebabnya, bukan dianggap nol.

**Yang belum masuk, dan disebut apa adanya:** tarif minimum broker tidak masuk rumus per lembar
PRD 9.7 dan karena itu dilaporkan sebagai catatan, bukan dihitung diam-diam.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from fractions import Fraction

from mejasaham import db, kandidat, konfigurasi, metrik, potret as modul_potret, tampilan
from mejasaham.skema import MODE_SAH

#: Nama batas yang dikenal — sama persis dengan CHECK di `preset_risiko_nilai` (skema 010).
RISIKO_PER_POSISI = "risiko_per_posisi"
BOBOT_MAKSIMUM = "bobot_maksimum"
BOBOT_SEKTOR_MAKSIMUM = "bobot_sektor_maksimum"
LIKUIDITAS_MAKSIMUM = "likuiditas_maksimum"
TOTAL_RISIKO_MAKSIMUM = "total_risiko_maksimum"

NAMA_BATAS: tuple[str, ...] = (
    RISIKO_PER_POSISI,
    BOBOT_MAKSIMUM,
    BOBOT_SEKTOR_MAKSIMUM,
    LIKUIDITAS_MAKSIMUM,
    TOTAL_RISIKO_MAKSIMUM,
)

#: Sebutan manusia untuk tiap batas, dipakai di pesan dan keluaran.
SEBUTAN_BATAS: Mapping[str, str] = {
    RISIKO_PER_POSISI: "risiko per posisi",
    BOBOT_MAKSIMUM: "bobot maksimum per posisi",
    BOBOT_SEKTOR_MAKSIMUM: "bobot maksimum per sektor",
    LIKUIDITAS_MAKSIMUM: "ukuran maksimum terhadap ADTV20",
    TOTAL_RISIKO_MAKSIMUM: "total risiko berjalan maksimum",
}

#: Nilai awal batas risiko — PRD 9.7 "Batas bawaan". Ini **pengaturan**, bukan parameter bursa:
#: PRD 8.3 menyebutnya nilai awal usulan yang boleh direvisi, dan revisinya menaikkan versi.
#: Yang tidak boleh: menyalinnya menjadi konstanta di dalam rumus — itulah yang dihindari dengan
#: menyimpannya sebagai baris berversi di `preset_risiko`.
BATAS_AWAL_BP: Mapping[str, int] = {
    RISIKO_PER_POSISI: 75,          # 0,75% ekuitas
    BOBOT_MAKSIMUM: 1000,           # 10%
    BOBOT_SEKTOR_MAKSIMUM: 3000,    # 30%
    LIKUIDITAS_MAKSIMUM: 200,       # 2% dari ADTV20
    TOTAL_RISIKO_MAKSIMUM: 500,     # 5% ekuitas
}

NAMA_PRESET_BAWAAN = "risiko-bawaan"
KETERANGAN_PRESET_BAWAAN = (
    "Batas awal PRD 9.7 (batas bawaan): risiko per posisi 0,75%, bobot maksimum 10%, bobot per "
    "sektor maksimum 30%, ukuran maksimum 2% ADTV20, total risiko berjalan maksimum 5%. "
    "Nilai awal usulan (PRD 8.3), bukan kebenaran pasar."
)

#: Q9: pengguna memilih jenis stop per rencana (PRD 9.7, 8.1).
JENIS_STOP_SAH: tuple[str, ...] = ("order_sekuritas", "cek_penutupan")

#: Dari mana angka `stop` datang (kolom `dasar_stop` di `rencana`).
DASAR_STOP_SAH: tuple[str, ...] = ("harga_masuk_minus_2_atr14", "harga_pembatal", "pengguna")

SISI_BELI = "beli"
SISI_JUAL = "jual"

#: Dua kolom sektor yang ada, dan sebutannya untuk manusia (K25). Keduanya **tidak** setara:
#: `sektor_idx_ic` adalah klasifikasi yang dipakai PRD, `sektor_sumber` adalah taksonomi sumber
#: data EOD yang dipakai selama yang pertama belum terisi.
KOLOM_SEKTOR_IDX_IC = "sektor_idx_ic"
KOLOM_SEKTOR_SUMBER = "sektor_sumber"
SEBUTAN_SEKTOR: Mapping[str, str] = {
    KOLOM_SEKTOR_IDX_IC: "IDX-IC",
    KOLOM_SEKTOR_SUMBER: "sumber data (bukan IDX-IC)",
}


def pilih_sektor(emiten: object) -> tuple[str | None, str | None]:
    """Kolom sektor yang dipakai untuk satu emiten, dan nilai sektornya (K25).

    Aturannya satu arah: **`sektor_idx_ic` menang** begitu ia terisi; `sektor_sumber` hanya
    dipakai selama yang pertama kosong. Menggabungkan keduanya dalam satu penjumlahan dilarang —
    dua taksonomi berbeda akan membuat paparan satu sektor tampak lebih kecil daripada kenyataan.
    """
    idx_ic = getattr(emiten, KOLOM_SEKTOR_IDX_IC, None)
    if idx_ic:
        return KOLOM_SEKTOR_IDX_IC, idx_ic
    sumber = getattr(emiten, KOLOM_SEKTOR_SUMBER, None)
    if sumber:
        return KOLOM_SEKTOR_SUMBER, sumber
    return None, None


class GalatRisiko(RuntimeError):
    """Kesalahan yang pesannya sudah ditujukan untuk pengguna, bukan traceback (aturan keras 7)."""


def _persen(basis_poin: float) -> str:
    """Basis poin menjadi teks persen format Indonesia (U11) — satu tempat, tidak diulang."""
    return tampilan.angka(basis_poin / 100, 2) + "%"


# ---------------------------------------------------------------------------------------
# Batas risiko (pengaturan berversi, PRD 8.3)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PresetRisiko:
    """Satu versi batas risiko portofolio."""

    id_preset_risiko: str
    nama: str
    versi: int
    keterangan: str | None
    dibuat_pada: date
    nilai: Mapping[str, int]

    def bp(self, nama: str) -> int:
        """Nilai satu batas dalam basis poin; batas yang tidak ada **ditolak**, bukan dianggap nol."""
        if nama not in self.nilai:
            raise GalatRisiko(
                f"batas risiko {SEBUTAN_BATAS.get(nama, nama)!r} tidak ada di preset "
                f"{self.id_preset_risiko}; batas yang hilang tidak boleh berarti \"tanpa batas\". "
                f"Yang ada: {', '.join(sorted(self.nilai))}"
            )
        return self.nilai[nama]

    def ringkas(self, nama: str) -> str:
        return f"{tampilan.angka(self.bp(nama) / 100, 2)}%"


def batas_bawaan(hari_ini: date | None = None, *, versi: int = 1) -> PresetRisiko:
    """Batas awal PRD 9.7 sebagai satu preset berversi (belum disimpan)."""
    tanggal = hari_ini or date.today()
    return PresetRisiko(
        id_preset_risiko=f"{NAMA_PRESET_BAWAAN}/v{versi}",
        nama=NAMA_PRESET_BAWAAN,
        versi=versi,
        keterangan=KETERANGAN_PRESET_BAWAAN,
        dibuat_pada=tanggal,
        nilai=dict(BATAS_AWAL_BP),
    )


def _sidik_preset(preset: PresetRisiko) -> str:
    isi = ";".join(f"{nama}={preset.nilai[nama]}" for nama in sorted(preset.nilai))
    return f"{preset.nama}/v{preset.versi}|{isi}"


def _periksa_preset(preset: PresetRisiko) -> None:
    tak_dikenal = sorted(set(preset.nilai) - set(NAMA_BATAS))
    if tak_dikenal:
        raise GalatRisiko(
            f"batas risiko tidak dikenal: {', '.join(tak_dikenal)}. Yang sah: {', '.join(NAMA_BATAS)}"
        )
    kurang = [nama for nama in NAMA_BATAS if nama not in preset.nilai]
    if kurang:
        raise GalatRisiko(
            f"preset risiko {preset.id_preset_risiko} tidak memuat batas: {', '.join(kurang)}. "
            "Batas yang tidak dimuat tidak boleh berarti \"tanpa batas\" — lengkapi atau "
            "nonaktifkan dengan sengaja."
        )
    for nama, nilai in preset.nilai.items():
        if not 0 < nilai <= 10000:
            raise GalatRisiko(
                f"batas {nama} = {nilai} bp di luar rentang yang masuk akal (0 < bp <= 10000 bp)"
            )


def simpan_preset(sambungan: sqlite3.Connection, preset: PresetRisiko) -> bool:
    """Simpan satu versi batas risiko. Kembalikan True bila baris baru ditulis.

    Idempoten untuk isi yang sama; isi yang **berbeda** pada id yang sama ditolak berisik —
    rencana lama menunjuk versi ini, dan artinya tidak boleh berubah diam-diam (PRD 8.3).
    """
    _periksa_preset(preset)
    lama = baca_sidik_preset(sambungan, preset.id_preset_risiko)
    if lama is not None:
        if lama != _sidik_preset(preset):
            raise GalatRisiko(
                f"preset risiko {preset.id_preset_risiko} sudah ada dengan isi berbeda. Rencana "
                "lama menunjuk versi ini, jadi artinya tidak boleh berubah: naikkan versinya "
                f"(mis. {preset.nama}/v{preset.versi + 1}) dan simpan sebagai preset baru."
            )
        return False
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO preset_risiko (id_preset_risiko, nama, versi, keterangan, dibuat_pada)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                preset.id_preset_risiko,
                preset.nama,
                preset.versi,
                preset.keterangan,
                preset.dibuat_pada.isoformat(),
            ),
        )
        for nama in NAMA_BATAS:
            koneksi.execute(
                "INSERT INTO preset_risiko_nilai (id_preset_risiko, nama, nilai_bp)"
                " VALUES (?, ?, ?)",
                (preset.id_preset_risiko, nama, preset.nilai[nama]),
            )
        koneksi.execute(
            "INSERT INTO log_jalan (waktu, proses, hasil, pesan) VALUES (?, 'risiko', 'sukses', ?)",
            (db.waktu_iso(), f"preset risiko {preset.id_preset_risiko} disimpan"),
        )
    return True


def baca_sidik_preset(sambungan: sqlite3.Connection, id_preset_risiko: str) -> str | None:
    """Sidik isi preset risiko yang tersimpan, atau None bila belum ada."""
    kepala = sambungan.execute(
        "SELECT nama, versi FROM preset_risiko WHERE id_preset_risiko = ?", (id_preset_risiko,)
    ).fetchone()
    if kepala is None:
        return None
    nilai = {
        baris["nama"]: baris["nilai_bp"]
        for baris in sambungan.execute(
            "SELECT nama, nilai_bp FROM preset_risiko_nilai WHERE id_preset_risiko = ?",
            (id_preset_risiko,),
        )
    }
    isi = ";".join(f"{nama}={nilai[nama]}" for nama in sorted(nilai))
    return f"{kepala['nama']}/v{kepala['versi']}|{isi}"


def muat_preset(sambungan: sqlite3.Connection, id_preset_risiko: str) -> PresetRisiko:
    kepala = sambungan.execute(
        "SELECT * FROM preset_risiko WHERE id_preset_risiko = ?", (id_preset_risiko,)
    ).fetchone()
    if kepala is None:
        raise GalatRisiko(
            f"preset risiko {id_preset_risiko!r} tidak ada. Yang tersedia: "
            f"{', '.join(daftar_preset(sambungan)) or '(belum ada)'}"
        )
    nilai = {
        baris["nama"]: baris["nilai_bp"]
        for baris in sambungan.execute(
            "SELECT nama, nilai_bp FROM preset_risiko_nilai WHERE id_preset_risiko = ?",
            (id_preset_risiko,),
        )
    }
    return PresetRisiko(
        id_preset_risiko=kepala["id_preset_risiko"],
        nama=kepala["nama"],
        versi=kepala["versi"],
        keterangan=kepala["keterangan"],
        dibuat_pada=date.fromisoformat(kepala["dibuat_pada"]),
        nilai=nilai,
    )


def preset_terbaru(sambungan: sqlite3.Connection, nama: str = NAMA_PRESET_BAWAAN) -> PresetRisiko:
    """Versi terakhir satu nama preset risiko (PRD 8.3: perubahan menaikkan versi)."""
    baris = sambungan.execute(
        "SELECT id_preset_risiko FROM preset_risiko WHERE nama = ? ORDER BY versi DESC LIMIT 1",
        (nama,),
    ).fetchone()
    if baris is None:
        raise GalatRisiko(
            f"batas risiko ({nama}) belum ada di basis data. Tanpa batasnya, ukuran posisi tidak "
            "bisa dihitung dari aturan — jalankan: python -m mejasaham --batas-risiko-bawaan"
        )
    return muat_preset(sambungan, baris["id_preset_risiko"])


def daftar_preset(sambungan: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(
        baris["id_preset_risiko"]
        for baris in sambungan.execute(
            "SELECT id_preset_risiko FROM preset_risiko ORDER BY nama, versi"
        )
    )


# ---------------------------------------------------------------------------------------
# Harga & tick (B2)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TabelTick:
    """Tabel fraksi harga B2 yang berlaku pada satu tanggal."""

    rentang: tuple[tuple[int, int | None, int], ...]

    def tick(self, harga: int) -> int | None:
        """Tick untuk satu harga, atau None bila harganya di luar seluruh pita."""
        for batas_bawah, batas_atas, tick in self.rentang:
            if harga >= batas_bawah and (batas_atas is None or harga <= batas_atas):
                return tick
        return None

    def sah(self, harga: int) -> bool:
        tick = self.tick(harga)
        return tick is not None and harga % tick == 0

    def terdekat(self, harga: int) -> tuple[int, ...]:
        """Tick sah terdekat di bawah dan di atas `harga` (untuk pesan penolakan)."""
        tick = self.tick(harga)
        if tick is None:
            return ()
        bawah = harga - (harga % tick)
        atas = bawah + tick
        return tuple(dict.fromkeys((bawah, atas)))

    def bulatkan_ke_bawah(self, harga: int) -> int | None:
        """Harga dibulatkan ke bawah ke tick sah; None bila di luar pita."""
        tick = self.tick(harga)
        if tick is None:
            return None
        return harga - (harga % tick)


def tabel_tick(sambungan: sqlite3.Connection, pada: date | None = None) -> TabelTick:
    """Baca tabel fraksi harga B2 yang berlaku. Menolak bila belum terverifikasi (K1)."""
    status = konfigurasi.nilai_efektif(sambungan, "fraksi_harga", "", pada)
    entri = status.ambil()  # ParameterBelumSiap sudah berisi pesan yang menyebut sebabnya
    rentang = tuple(
        (baris["batas_bawah"], baris["batas_atas"], baris["tick"]) for baris in entri.muatan
    )
    if not rentang:
        raise GalatRisiko(
            "tabel fraksi harga (B2) kosong di basis data; harga tidak bisa dibulatkan ke tick "
            "yang sah. Muat ulang parameter: python -m mejasaham --muat-konfigurasi"
        )
    return TabelTick(rentang=rentang)


def periksa_harga(harga: int, tabel: TabelTick, sebutan: str) -> None:
    """Harga yang diisi pengguna harus kelipatan tick yang sah — tidak digeser diam-diam."""
    tick = tabel.tick(harga)
    if tick is None:
        pita = ", ".join(
            f"Rp{baris[0]}" + (f"–Rp{baris[1]}" if baris[1] is not None else " ke atas")
            for baris in tabel.rentang
        )
        raise GalatRisiko(
            f"{sebutan} Rp{harga} di luar tabel fraksi harga yang berlaku (pita: {pita}). "
            "Harga di luar pita tidak punya tick yang sah, jadi angkanya tidak boleh ditebak."
        )
    if harga % tick != 0:
        terdekat = " atau ".join(f"Rp{satu}" for satu in tabel.terdekat(harga))
        raise GalatRisiko(
            f"{sebutan} Rp{harga} bukan kelipatan tick Rp{tick} pada pita itu (B2). Yang sah di "
            f"sekitarnya: {terdekat}. Angkanya tidak digeser diam-diam: menggeser harga masuk "
            "menggeser ukuran posisi dan risikonya sekaligus."
        )


# ---------------------------------------------------------------------------------------
# Biaya & slippage per lembar (B6/B7/B8/B9, K20/K23)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BiayaSisi:
    """Biaya satu sisi transaksi, per lembar, beserta asalnya."""

    sisi: str
    harga: int
    tarif_bp: int
    minimum: int | None
    pph_bp: int
    pph_dasar: str | None
    komponen_termasuk: tuple[str, ...]
    biaya_per_lembar: int
    rincian: tuple[str, ...]


def _ceil_fraksi(nilai: Fraction) -> int:
    """Bulatkan ke atas: biaya tidak pernah dibulatkan ke bawah (PRD 10, risiko = batas bawah)."""
    return -((-nilai.numerator) // nilai.denominator)


def broker_terpasang(sambungan: sqlite3.Connection) -> tuple[str, ...]:
    """Nama broker yang entri tarifnya ada di basis data (kelompok `biaya_broker`)."""
    return tuple(
        baris["kelompok"]
        for baris in sambungan.execute(
            "SELECT DISTINCT kelompok FROM parameter_bursa WHERE nama = 'biaya_broker'"
            " ORDER BY kelompok"
        )
    )


def biaya_sisi(
    sambungan: sqlite3.Connection,
    sisi: str,
    harga: int,
    pada: date | None = None,
    *,
    broker: str | None = None,
) -> BiayaSisi:
    """Biaya broker satu sisi per lembar + PPh final penjualan bila belum termasuk (K23).

    Tarifnya *all-in*: halaman Stockbit menyatakan `Fee Beli 0,15%` / `Fee Jual 0,25%` sudah
    termasuk levy, PPN, **dan PPh final jual 0,1%**. Menambahkan B8 di atasnya berarti menghitung
    pajak dua kali — kesalahan yang tidak terlihat di keluaran mana pun, hanya di angkanya (K23).
    Karena itu komponen yang sudah termasuk **tidak ditambahkan**, dan penandanya dibawa keluar.

    Bila lebih dari satu broker terpasang, `broker` wajib disebut: memilih yang pertama
    diam-diam akan memakai tarif milik orang lain, dan angkanya tetap tampak sah.
    """
    if sisi not in (SISI_BELI, SISI_JUAL):
        raise GalatRisiko(f"sisi {sisi!r} tidak dikenal; yang sah: {SISI_BELI}, {SISI_JUAL}")
    if harga <= 0:
        raise GalatRisiko(f"harga harus lebih dari nol, bukan {harga}")

    terpasang = broker_terpasang(sambungan)
    if broker is None:
        if not terpasang:
            status = konfigurasi.nilai_efektif(sambungan, "biaya_broker", "", pada)
            raise konfigurasi.ParameterBelumSiap(status.alasan)
        if len(terpasang) > 1:
            raise GalatRisiko(
                f"ada {len(terpasang)} entri tarif broker ({', '.join(terpasang)}); sebutkan yang "
                "dipakai lewat --broker. Memilih yang pertama diam-diam akan memakai tarif yang "
                "mungkin bukan milik Anda."
            )
        broker = terpasang[0]
    elif broker not in terpasang:
        raise GalatRisiko(
            f"broker {broker!r} tidak punya entri tarif. Yang terpasang: "
            f"{', '.join(terpasang) or '(belum ada)'}"
        )

    entri_broker = konfigurasi.nilai_efektif(sambungan, "biaya_broker", broker, pada)
    entri = entri_broker.ambil()

    muatan = entri.muatan[0]
    if sisi == SISI_BELI:
        tarif_bp = int(muatan["persen_beli_bp"])
        minimum = muatan["minimum_beli"]
    else:
        tarif_bp = int(muatan["persen_jual_bp"])
        minimum = muatan["minimum_jual"]
    sudah_termasuk = tuple(muatan.get("sudah_termasuk") or ())

    rincian = [
        f"biaya broker {sisi} {_persen(tarif_bp)} dari {entri_broker.label} "
        f"(berlaku {entri.berlaku_sejak.isoformat()})",
    ]
    biaya = Fraction(tarif_bp * harga, 10000)

    pph_bp = 0
    pph_dasar: str | None = None
    if sisi == SISI_JUAL and "pph_penjualan" not in sudah_termasuk:
        pajak = konfigurasi.nilai_efektif(sambungan, "pajak_penjualan", "", pada)
        entri_pajak = pajak.ambil()
        pph_bp = int(entri_pajak.muatan[0]["persen_bp"])
        pph_dasar = entri_pajak.muatan[0]["dasar"]
        biaya += Fraction(pph_bp * harga, 10000)
        rincian.append(
            f"PPh final penjualan {tampilan.angka(pph_bp / 100, 2)}% ({pph_dasar})"
        )
    elif sisi == SISI_JUAL:
        rincian.append(
            "PPh final penjualan tidak ditambahkan: sumber menyatakan tarif sisi jual sudah "
            "termasuk PPh (K23)"
        )
    if minimum is None:
        rincian.append(
            "tarif minimum tidak dinyatakan sumbernya, jadi tidak diterapkan (K22) — bukan "
            "dianggap nol"
        )
    else:
        rincian.append(
            f"tarif minimum Rp{minimum} per transaksi tidak masuk rumus per lembar PRD 9.7 "
            "(lihat catatan di keluaran kalkulator)"
        )

    return BiayaSisi(
        sisi=sisi,
        harga=harga,
        tarif_bp=tarif_bp,
        minimum=minimum,
        pph_bp=pph_bp,
        pph_dasar=pph_dasar,
        komponen_termasuk=sudah_termasuk,
        biaya_per_lembar=_ceil_fraksi(biaya),
        rincian=tuple(rincian),
    )


def slippage_per_lembar(
    sambungan: sqlite3.Connection, harga: int, tabel: TabelTick, pada: date | None = None
) -> tuple[int, str]:
    """Slippage satu sisi dalam rupiah per lembar (B9/K20) + alasannya."""
    status = konfigurasi.nilai_efektif(sambungan, "slippage", "", pada)
    entri = status.ambil()
    muatan = entri.muatan[0]
    if muatan["mode"] == "tick":
        tick = tabel.tick(harga)
        if tick is None:
            raise GalatRisiko(
                f"slippage mode tick tidak bisa dihitung: harga Rp{harga} di luar tabel fraksi "
                "harga (B2)"
            )
        nilai = int(muatan["nilai_tick"]) * tick
        return nilai, f"slippage {muatan['nilai_tick']} tick × Rp{tick} (B9/K20)"
    nilai = _ceil_fraksi(Fraction(int(muatan["nilai_persen_bp"]) * harga, 10000))
    return nilai, f"slippage {_persen(int(muatan['nilai_persen_bp']))} dari harga"


# ---------------------------------------------------------------------------------------
# Hitungan (murni: tanpa basis data, supaya bisa diuji tanpa apa pun)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Pelanggaran:
    """Satu batas yang dilewati, beserta angkanya — ditampilkan, bukan disembunyikan."""

    batas: str
    pesan: str


@dataclass(frozen=True)
class HasilRisiko:
    """Keluaran kalkulator (PRD 9.7 "Keluaran"), lengkap dengan sebab tiap angka."""

    kode: str
    ekuitas: int
    harga_masuk: int
    stop: int
    dasar_stop: str
    biaya_slippage: int
    risiko_per_lembar: int
    risiko_per_posisi_bp: int
    anggaran_risiko: int
    lembar_mentah: Fraction
    lembar: int
    nilai_posisi: int
    bobot_bp: int
    risiko_nominal: int
    risiko_berjalan: int
    total_risiko_bp: int
    maks_lembar_bobot: int
    maks_lembar_sektor: int | None
    maks_lembar_likuiditas: int | None
    maks_lembar_kas: int | None
    lembar_patuh_total_risiko: int
    pelanggaran: tuple[Pelanggaran, ...]
    catatan: tuple[str, ...]
    batas_tidak_dinilai: tuple[str, ...]
    pembatasan: tuple[str, ...]
    atr14_rupiah: float | None = None
    harga_terakhir: float | None = None
    id_preset_risiko: str = ""
    jenis_stop: str | None = None

    @property
    def patuh(self) -> bool:
        """True bila tidak ada batas yang dilewati pada ukuran akhir."""
        return not self.pelanggaran

    @property
    def ukuran_patuh(self) -> int:
        """Ukuran terbesar yang mematuhi **seluruh** batas yang bisa dinilai (lot penuh)."""
        kandidat = [
            self.maks_lembar_bobot,
            self.maks_lembar_sektor,
            self.maks_lembar_likuiditas,
            self.maks_lembar_kas,
            self.lembar_patuh_total_risiko,
        ]
        return min(satu for satu in kandidat if satu is not None)

    @property
    def nilai_posisi_patuh(self) -> int:
        return self.ukuran_patuh * self.harga_masuk


def hitung(
    *,
    kode: str,
    ekuitas: int,
    harga_masuk: int,
    stop: int,
    biaya_slippage: int,
    lot: int,
    batas: PresetRisiko,
    risiko_berjalan: int = 0,
    adtv20: float | None = None,
    kas: int | None = None,
    nilai_sektor: int | None = None,
    sektor_sebutan: str | None = None,
    sektor_dikecualikan: int = 0,
    dasar_stop: str = "pengguna",
    atr14_rupiah: float | None = None,
    harga_terakhir: float | None = None,
    jenis_stop: str | None = None,
    catatan: Sequence[str] = (),
) -> HasilRisiko:
    """Hitung ukuran posisi menurut PRD 9.7.

    Argumen yang `None` berarti **datanya tidak ada**, dan batas yang bergantung padanya menjadi
    "tidak dinilai" — bukan dianggap longgar (aturan keras 2):

    * `adtv20` None → batas likuiditas tidak dinilai;
    * `kas` None → batas kas tidak dinilai;
    * `nilai_sektor` None → batas sektor tidak dinilai (mis. `sektor_idx_ic` belum terisi).
    """
    if ekuitas <= 0:
        raise GalatRisiko(f"ekuitas harus lebih dari nol, bukan {ekuitas}")
    if harga_masuk <= 0:
        raise GalatRisiko(f"harga masuk harus lebih dari nol, bukan {harga_masuk}")
    if stop >= harga_masuk:
        raise GalatRisiko(
            f"stop {stop} tidak boleh di atas atau sama dengan harga masuk {harga_masuk}: posisi "
            "ini hanya beli (long), jadi stop di atas harga masuk berarti risiko negatif (PRD 9.7)"
        )
    if biaya_slippage < 0:
        raise GalatRisiko(f"biaya & slippage tidak boleh negatif, bukan {biaya_slippage}")
    if lot <= 0:
        raise GalatRisiko(f"jumlah lembar per lot harus lebih dari nol, bukan {lot}")
    if dasar_stop not in DASAR_STOP_SAH:
        raise GalatRisiko(f"dasar_stop {dasar_stop!r} tidak dikenal; yang sah: {DASAR_STOP_SAH}")
    if jenis_stop is not None and jenis_stop not in JENIS_STOP_SAH:
        raise GalatRisiko(
            f"jenis stop {jenis_stop!r} tidak dikenal; yang sah: {JENIS_STOP_SAH} (Q9, PRD 9.7)"
        )

    risiko_per_lembar = harga_masuk - stop + biaya_slippage
    bp_risiko = batas.bp(RISIKO_PER_POSISI)
    anggaran = ekuitas * bp_risiko // 10000
    lembar_mentah = Fraction(anggaran, risiko_per_lembar)

    def lot_penuh(lembar: Fraction) -> int:
        """Lembar dibulatkan **ke bawah** ke lot penuh — jumlah lembar selalu kelipatan lot (PRD 10)."""
        if lembar <= 0:
            return 0
        return (int(lembar) // lot) * lot

    def lembar_dari_pagu(pagu_rupiah: Fraction, harga_per_lembar: int) -> int:
        """Berapa lot penuh yang muat dalam satu pagu rupiah pada harga tertentu."""
        return lot_penuh(pagu_rupiah / harga_per_lembar)

    maks_bobot = lembar_dari_pagu(Fraction(batas.bp(BOBOT_MAKSIMUM) * ekuitas, 10000), harga_masuk)
    maks_likuiditas = (
        None
        if adtv20 is None
        else lembar_dari_pagu(
            Fraction(batas.bp(LIKUIDITAS_MAKSIMUM), 10000) * Fraction(round(adtv20)), harga_masuk
        )
    )
    # Kas harus menutup nilai posisi **dan** biayanya: membeli 100 lembar berarti membayar
    # harga + biaya per lembar, bukan harganya saja.
    maks_kas = (
        None
        if kas is None
        else lot_penuh(Fraction(kas, harga_masuk + biaya_slippage))
    )
    if nilai_sektor is None:
        maks_sektor = None
    else:
        pagu_sektor = Fraction(batas.bp(BOBOT_SEKTOR_MAKSIMUM) * ekuitas, 10000) - nilai_sektor
        maks_sektor = lembar_dari_pagu(max(pagu_sektor, Fraction(0)), harga_masuk)

    pembatasan: list[str] = []
    if lembar_mentah > maks_bobot:
        pembatasan.append(
            f"ukuran mentah {tampilan.angka(float(lembar_mentah), 0)} lembar dibatasi batas "
            f"{SEBUTAN_BATAS[BOBOT_MAKSIMUM]} {batas.ringkas(BOBOT_MAKSIMUM)} -> {maks_bobot} lembar"
        )
    if maks_likuiditas is not None and lembar_mentah > maks_likuiditas:
        pembatasan.append(
            f"ukuran mentah dibatasi {SEBUTAN_BATAS[LIKUIDITAS_MAKSIMUM]} "
            f"{batas.ringkas(LIKUIDITAS_MAKSIMUM)} dari ADTV20 -> {maks_likuiditas} lembar"
        )
    if maks_sektor is not None and lembar_mentah > maks_sektor:
        pembatasan.append(
            f"ukuran mentah dibatasi {SEBUTAN_BATAS[BOBOT_SEKTOR_MAKSIMUM]} "
            f"{batas.ringkas(BOBOT_SEKTOR_MAKSIMUM)}"
            + (f" [{sektor_sebutan}]" if sektor_sebutan else "")
            + f" -> {maks_sektor} lembar"
        )
    if sektor_dikecualikan:
        pembatasan.append(
            f"{sektor_dikecualikan} rencana tersimpan tidak dapat diatribusikan ke sektor mana pun "
            "pada taksonomi yang dipakai, jadi paparan sektornya tidak ikut terhitung"
        )
    if maks_kas is not None and lembar_mentah > maks_kas:
        pembatasan.append(f"ukuran mentah dibatasi kas tersedia -> {maks_kas} lembar")

    plafon = [satu for satu in (maks_bobot, maks_likuiditas, maks_sektor, maks_kas) if satu is not None]
    batas_terketat = min(plafon)
    if lembar_mentah < batas_terketat:
        lembar_akhir = lot_penuh(lembar_mentah)
    else:
        lembar_akhir = batas_terketat

    nilai_posisi = lembar_akhir * harga_masuk
    bobot_bp = nilai_posisi * 10000 // ekuitas
    risiko_nominal = lembar_akhir * risiko_per_lembar
    total_risiko = risiko_berjalan + risiko_nominal
    total_risiko_bp = total_risiko * 10000 // ekuitas

    # "Ukuran yang patuh" untuk batas total risiko (PRD 9.7): sebesar apa pun sisanya, yang
    # boleh dipakai hanyalah sebesar pagu yang belum terpakai.
    pagu_total = Fraction(batas.bp(TOTAL_RISIKO_MAKSIMUM) * ekuitas, 10000) - risiko_berjalan
    lembar_patuh_total = 0
    if pagu_total > 0 and risiko_per_lembar > 0:
        lembar_patuh_total = lot_penuh(pagu_total / risiko_per_lembar)

    pelanggaran: list[Pelanggaran] = []
    if total_risiko_bp > batas.bp(TOTAL_RISIKO_MAKSIMUM):
        pelanggaran.append(
            Pelanggaran(
                batas=TOTAL_RISIKO_MAKSIMUM,
                pesan=(
                    f"total risiko berjalan setelah posisi ini {_persen(total_risiko_bp)} "
                    f"melewati batas {batas.ringkas(TOTAL_RISIKO_MAKSIMUM)}; ukuran yang patuh "
                    f"{lembar_patuh_total} lembar ({lembar_patuh_total // lot} lot)"
                ),
            )
        )

    batas_tidak_dinilai: list[str] = []
    if maks_likuiditas is None:
        batas_tidak_dinilai.append(
            f"{SEBUTAN_BATAS[LIKUIDITAS_MAKSIMUM]} tidak dinilai: ADTV20 emiten ini tidak dihitung"
        )
    if maks_sektor is None:
        batas_tidak_dinilai.append(
            f"{SEBUTAN_BATAS[BOBOT_SEKTOR_MAKSIMUM]} tidak dinilai: sektor emiten belum terisi — "
            "baik `sektor_idx_ic` (klasifikasi PRD) maupun `sektor_sumber` (taksonomi sumber data, "
            "K25) — jadi paparan sektor tidak bisa dijumlahkan"
        )
    if maks_kas is None:
        batas_tidak_dinilai.append(
            f"kas tersedia tidak dinilai: kas belum dicatat di ekuitas harian (F11)"
        )

    semua_catatan = list(catatan)
    semua_catatan.append(
        "risiko eksekusi: stop dicatat sebagai harga rencana, dan aplikasi hanya memakai data "
        "akhir hari — gap harga, batas ARB, dan suspensi bisa membuat stop tidak tereksekusi pada "
        "harganya, sehingga risiko nyata dapat melebihi risiko nominal (PRD 9.7)"
    )
    if batas_tidak_dinilai:
        semua_catatan.append(
            "ada batas yang TIDAK DINILAI pada rencana ini (bukan berarti lolos): "
            + "; ".join(batas_tidak_dinilai)
        )

    return HasilRisiko(
        kode=kode,
        ekuitas=ekuitas,
        harga_masuk=harga_masuk,
        stop=stop,
        dasar_stop=dasar_stop,
        biaya_slippage=biaya_slippage,
        risiko_per_lembar=risiko_per_lembar,
        risiko_per_posisi_bp=bp_risiko,
        anggaran_risiko=anggaran,
        lembar_mentah=lembar_mentah,
        lembar=lembar_akhir,
        nilai_posisi=nilai_posisi,
        bobot_bp=bobot_bp,
        risiko_nominal=risiko_nominal,
        risiko_berjalan=risiko_berjalan,
        total_risiko_bp=total_risiko_bp,
        maks_lembar_bobot=maks_bobot,
        maks_lembar_sektor=maks_sektor,
        maks_lembar_likuiditas=maks_likuiditas,
        maks_lembar_kas=maks_kas,
        lembar_patuh_total_risiko=lembar_patuh_total,
        pelanggaran=tuple(pelanggaran),
        catatan=tuple(semua_catatan),
        batas_tidak_dinilai=tuple(batas_tidak_dinilai),
        pembatasan=tuple(pembatasan),
        atr14_rupiah=atr14_rupiah,
        harga_terakhir=harga_terakhir,
        id_preset_risiko=batas.id_preset_risiko,
        jenis_stop=jenis_stop,
    )


# ---------------------------------------------------------------------------------------
# Ekuitas harian (F11 dasar, PRD 9.11) — masukan kalkulator (PRD 9.7)
# ---------------------------------------------------------------------------------------


def catat_ekuitas(
    sambungan: sqlite3.Connection,
    *,
    ekuitas: int,
    kas: int | None = None,
    arus_dana: int | None = None,
    mode: str | None = None,
    tanggal: date | str | None = None,
    catatan: str | None = None,
    sumber: str = "dicatat pengguna",
    diketahui_pada: str | None = None,
) -> str:
    """Catat ekuitas (dan kas) satu hari. Append-only: koreksi menambah baris baru (aturan 3).

    `kas` bawaan `None` — **bukan 0** — dan itu berarti "kas belum dicatat", sehingga batas kas
    pada kalkulator menjadi tidak dinilai. Menuliskannya 0 akan menghentikan seluruh rencana
    dengan alasan yang salah (aturan keras 2).

    `arus_dana` (setoran positif, penarikan negatif) juga boleh `None`, dan bedanya bukan hiasan:
    AC-13 menuntut setoran/penarikan **tidak mengubah drawdown**, sedangkan deret yang arus
    dananya tidak diketahui tidak boleh dikoreksi — mengoreksinya dengan nol berarti menganggap
    setoran sebagai keuntungan. `mode` `None` = belum dinyatakan (PRD 9.11 memisahkan metrik
    simulasi dan nyata, tetapi baris lama tidak boleh diberi label yang tidak pernah dipilih).
    """
    if ekuitas <= 0:
        raise GalatRisiko(f"ekuitas harus lebih dari nol, bukan {ekuitas}")
    if kas is not None and kas < 0:
        raise GalatRisiko(f"kas tidak boleh negatif, bukan {kas}")
    if mode is not None and mode not in MODE_SAH:
        raise GalatRisiko(f"mode {mode!r} tidak dikenal; yang sah: {', '.join(MODE_SAH)}")
    if not str(sumber).strip():
        raise GalatRisiko("sumber ekuitas wajib diisi: tanpa itu, angkanya tidak bisa ditelusuri")
    hari = date.fromisoformat(tanggal) if isinstance(tanggal, str) else (tanggal or date.today())
    # Revisi dihitung dari baris yang sudah ada, bukan dari jam: dua pencatatan dalam detik yang
    # sama tetap menghasilkan dua baris (kelas cacat yang sama dengan `v_kandidat_terkini`, T37).
    berikutnya = int(
        sambungan.execute(
            "SELECT COALESCE(MAX(revisi), 0) + 1 FROM ekuitas_harian WHERE tanggal = ?",
            (hari.isoformat(),),
        ).fetchone()[0]
    )
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "INSERT INTO ekuitas_harian"
            " (tanggal, revisi, ekuitas, kas, arus_dana, mode, catatan, sumber, diketahui_pada)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                hari.isoformat(),
                berikutnya,
                ekuitas,
                kas,
                arus_dana,
                mode,
                catatan,
                sumber,
                diketahui_pada or db.waktu_iso(),
            ),
        )
    return hari.isoformat()


@dataclass(frozen=True)
class EkuitasTercatat:
    tanggal: str
    ekuitas: int
    kas: int | None
    sumber: str
    arus_dana: int | None = None
    mode: str | None = None


def ekuitas_terakhir(sambungan: sqlite3.Connection, pada: date | None = None) -> EkuitasTercatat | None:
    """Ekuitas harian terakhir yang tidak melewati `pada`; None bila belum pernah dicatat."""
    batas = (pada or date.today()).isoformat()
    baris = sambungan.execute(
        "SELECT * FROM v_ekuitas_harian_terkini WHERE tanggal <= ? ORDER BY tanggal DESC LIMIT 1",
        (batas,),
    ).fetchone()
    if baris is None:
        return None
    return EkuitasTercatat(
        tanggal=baris["tanggal"],
        ekuitas=int(baris["ekuitas"]),
        kas=None if baris["kas"] is None else int(baris["kas"]),
        sumber=baris["sumber"],
        arus_dana=None if baris["arus_dana"] is None else int(baris["arus_dana"]),
        mode=baris["mode"],
    )


# ---------------------------------------------------------------------------------------
# Deret ekuitas & drawdown (F11/AC-13, PRD 8.2)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BarisEkuitas:
    tanggal: str
    revisi: int
    ekuitas: int
    kas: int | None
    arus_dana: int | None
    mode: str | None
    sumber: str


def deret_ekuitas(
    sambungan: sqlite3.Connection,
    *,
    mode: str | None = None,
    sampai: date | None = None,
) -> tuple[BarisEkuitas, ...]:
    """Seluruh catatan ekuitas pada revisi terakhirnya, urut tanggal menaik.

    `mode=None` berarti **semua** baris, termasuk yang modenya belum dinyatakan — pemanggil yang
    mencampurnya wajib melaporkan berapa banyak baris yang belum bermode (PRD 9.11), bukan
    diam-diam menyatukannya dengan yang sudah).
    """
    kueri = "SELECT * FROM v_ekuitas_harian_terkini"
    syarat: list[str] = []
    nilai: list[object] = []
    if mode is not None:
        syarat.append("mode = ?")
        nilai.append(mode)
    if sampai is not None:
        syarat.append("tanggal <= ?")
        nilai.append(sampai.isoformat())
    if syarat:
        kueri += " WHERE " + " AND ".join(syarat)
    kueri += " ORDER BY tanggal"
    return tuple(
        BarisEkuitas(
            tanggal=baris["tanggal"],
            revisi=int(baris["revisi"]),
            ekuitas=int(baris["ekuitas"]),
            kas=None if baris["kas"] is None else int(baris["kas"]),
            arus_dana=None if baris["arus_dana"] is None else int(baris["arus_dana"]),
            mode=baris["mode"],
            sumber=baris["sumber"],
        )
        for baris in sambungan.execute(kueri, nilai)
    )


@dataclass(frozen=True)
class Drawdown:
    """Drawdown dari puncak ekuitas (PRD 8.2), terkoreksi setoran/penarikan **bila bisa**.

    Dua angka, dan keduanya dilaporkan apa adanya:

    * `mentah_*` — dari deret ekuitas apa adanya. Selalu ada, tetapi setoran akan tampak sebagai
      kenaikan dan penarikan sebagai penurunan;
    * `*` (terkoreksi) — dari deret **indeks** yang arus dananya dikeluarkan lebih dulu, sehingga
      setoran/penarikan tidak mengubah drawdown (AC-13). Hanya dapat dihitung bila arus dana
      setiap baris **sesudah baris pertama** diketahui; kalau tidak, `terkoreksi=False` beserta
      sebabnya — bukan dikoreksi dengan nol, sebab itu berarti menganggap setoran sebagai
      keuntungan. Baris **pertama** adalah titik acuan (ia menjadi puncak awal), jadi arus
      dananya memang tidak masuk perhitungan dan tidak perlu diketahui.
    """

    deret: tuple[BarisEkuitas, ...]
    terkoreksi: bool
    alasan: str | None
    drawdown_bp: int | None
    drawdown_maksimum_bp: int | None
    puncak: int | None
    tanggal_puncak: str | None
    mentah_bp: int
    mentah_maksimum_bp: int

    @property
    def jumlah_baris(self) -> int:
        return len(self.deret)


def _drawdown_deret(nilai: Sequence[Fraction]) -> tuple[int, int, int, int]:
    """(drawdown sekarang, drawdown maksimum, puncak, indeks puncak) dalam basis poin."""
    puncak = nilai[0]
    indeks_puncak = 0
    sekarang = 0
    maksimum = 0
    for i, satu in enumerate(nilai):
        if satu > puncak:
            puncak = satu
            indeks_puncak = i
        turun = int((puncak - satu) / puncak * 10000) if puncak else 0
        maksimum = max(maksimum, turun)
        sekarang = turun
    return sekarang, maksimum, int(puncak), indeks_puncak


def drawdown(
    sambungan: sqlite3.Connection,
    *,
    mode: str | None = None,
    sampai: date | None = None,
) -> Drawdown:
    """Drawdown dari puncak ekuitas harian, dikoreksi setoran/penarikan dana (AC-13, PRD 8.2)."""
    deret = deret_ekuitas(sambungan, mode=mode, sampai=sampai)
    if not deret:
        return Drawdown(
            deret=(),
            terkoreksi=False,
            alasan="ekuitas harian belum pernah dicatat",
            drawdown_bp=None,
            drawdown_maksimum_bp=None,
            puncak=None,
            tanggal_puncak=None,
            mentah_bp=0,
            mentah_maksimum_bp=0,
        )

    mentah = [Fraction(satu.ekuitas) for satu in deret]
    mentah_sekarang, mentah_maksimum, puncak_mentah, _ = _drawdown_deret(mentah)

    # Baris pertama sengaja tidak diperiksa: ia titik acuan (I₀ = ekuitas hari pertama), dan arus
    # dana hari itu tidak pernah masuk rumus. Menuntutnya akan menolak mengoreksi deret yang
    # sebenarnya bisa dikoreksi — dan menolak menghitung bukan tindakan yang netral.
    tanpa_arus = [satu.tanggal for satu in deret[1:] if satu.arus_dana is None]
    if tanpa_arus:
        contoh = ", ".join(tanpa_arus[:3])
        sisa = "" if len(tanpa_arus) <= 3 else f" dan {len(tanpa_arus) - 3} tanggal lain"
        return Drawdown(
            deret=deret,
            terkoreksi=False,
            alasan=(
                f"{len(tanpa_arus)} catatan ekuitas belum mencatat arus dananya ({contoh}{sisa}), "
                "sehingga drawdown tidak dapat dikoreksi terhadap setoran/penarikan (AC-13). "
                "Catat arus dananya lewat --arus-dana (0 berarti memang tidak ada)"
            ),
            drawdown_bp=None,
            drawdown_maksimum_bp=None,
            puncak=None,
            tanggal_puncak=None,
            mentah_bp=mentah_sekarang,
            mentah_maksimum_bp=mentah_maksimum,
        )

    # Deret indeks: r_t = (ekuitas_t - arus_dana_t) / ekuitas_{t-1}; I_t = I_{t-1} × r_t.
    # Setoran/penarikan dikeluarkan dari pembilang, jadi ia tidak lagi terlihat sebagai hasil.
    indeks = [Fraction(deret[0].ekuitas)]
    for sebelum, satu in zip(deret, deret[1:]):
        faktor = Fraction(satu.ekuitas - int(satu.arus_dana or 0), sebelum.ekuitas)
        indeks.append(indeks[-1] * faktor)
    sekarang, maksimum, puncak, posisi_puncak = _drawdown_deret(indeks)
    return Drawdown(
        deret=deret,
        terkoreksi=True,
        alasan=None,
        drawdown_bp=sekarang,
        drawdown_maksimum_bp=maksimum,
        puncak=puncak,
        tanggal_puncak=deret[posisi_puncak].tanggal,
        mentah_bp=mentah_sekarang,
        mentah_maksimum_bp=mentah_maksimum,
    )


# ---------------------------------------------------------------------------------------
# Risiko berjalan (PRD 8.2) — rencana belum dieksekusi
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RingkasanRisikoBerjalan:
    """Risiko berjalan portofolio PRD 8.2: posisi aktif **ditambah** rencana belum dieksekusi."""

    total: int
    dari_posisi: int
    dari_rencana: int
    jumlah_rencana_belum: int
    jumlah_posisi_aktif: int
    jumlah_posisi_dinilai: int
    rincian: tuple[str, ...]
    tidak_dinilai: tuple[str, ...]

    @property
    def lengkap(self) -> bool:
        """False bila ada suku yang tidak dapat dinilai — jumlahnya lalu lebih kecil dari kenyataan."""
        return not self.tidak_dinilai

    def ringkas(self) -> str:
        teks = (
            f"risiko berjalan {self.total} = posisi aktif {self.dari_posisi} "
            f"({self.jumlah_posisi_dinilai}/{self.jumlah_posisi_aktif} dinilai) "
            f"+ rencana belum dieksekusi {self.dari_rencana} ({self.jumlah_rencana_belum} rencana)"
        )
        if self.tidak_dinilai:
            teks += (
                f"\n  {len(self.tidak_dinilai)} suku TIDAK DINILAI — jumlah di atas lebih kecil "
                "daripada risiko yang sebenarnya:"
            )
            for satu in self.tidak_dinilai:
                teks += f"\n    - {satu}"
        return teks


def risiko_berjalan_lengkap(
    sambungan: sqlite3.Connection, *, kecuali: int | None = None
) -> RingkasanRisikoBerjalan:
    """Dua suku PRD 8.2 sekaligus: risiko terbuka posisi aktif + rencana yang belum dieksekusi.

    **Rencana yang sudah punya transaksi tidak dijumlahkan lagi.** Risikonya sudah hidup di
    posisinya; menjumlahkan keduanya menghitung risiko yang sama dua kali, dan justru pada saat
    itulah batas 5% paling sering tampak terlampaui padahal tidak. Yang dipakai sebagai penanda
    "sudah dieksekusi" adalah **adanya transaksi** yang menunjuk rencana itu — bukan status
    kandidatnya, sebab status adalah niat dan transaksi adalah kejadian.

    Suku yang tidak dapat dinilai (posisi tanpa stop, atau rencana yang emitennya tidak punya
    harga) **dilaporkan**, tidak dijumlahkan sebagai nol (aturan keras 2).
    """
    # Impor di dalam fungsi: `posisi.py` memakai `risiko.py` (tick, tarif, rencana), jadi impor
    # di tingkat modul akan melingkar.
    from mejasaham import posisi as modul_posisi

    sudah_dieksekusi = modul_posisi.id_rencana_dieksekusi(sambungan)
    rincian: list[str] = []
    dari_rencana = 0
    jumlah_rencana = 0
    for baris in sambungan.execute(
        "SELECT id_rencana, kode, risiko_nominal FROM v_rencana_terkini ORDER BY id_rencana"
    ):
        id_rencana = int(baris["id_rencana"])
        if kecuali is not None and id_rencana == kecuali:
            continue
        if id_rencana in sudah_dieksekusi:
            continue
        jumlah_rencana += 1
        dari_rencana += int(baris["risiko_nominal"])
        rincian.append(
            f"rencana #{id_rencana} {baris['kode']} (belum dieksekusi): {baris['risiko_nominal']}"
        )

    terbuka = modul_posisi.risiko_terbuka(sambungan)
    rincian.extend(terbuka.rincian)
    return RingkasanRisikoBerjalan(
        total=dari_rencana + terbuka.total,
        dari_posisi=terbuka.total,
        dari_rencana=dari_rencana,
        jumlah_rencana_belum=jumlah_rencana,
        jumlah_posisi_aktif=terbuka.jumlah_aktif,
        jumlah_posisi_dinilai=terbuka.jumlah_dinilai,
        rincian=tuple(rincian),
        tidak_dinilai=terbuka.tidak_dinilai,
    )


def risiko_berjalan(
    sambungan: sqlite3.Connection, *, kecuali: int | None = None
) -> tuple[int, tuple[str, ...]]:
    """Jumlah risiko berjalan (PRD 8.2) + rinciannya, termasuk suku yang tidak dapat dinilai.

    Bentuk kembaliannya sengaja tetap `(jumlah, rincian)` supaya pemanggil lama tidak berubah;
    yang butuh pecahannya memakai `risiko_berjalan_lengkap`.
    """
    lengkap = risiko_berjalan_lengkap(sambungan, kecuali=kecuali)
    rincian = list(lengkap.rincian)
    rincian.extend(f"TIDAK DINILAI: {satu}" for satu in lengkap.tidak_dinilai)
    return lengkap.total, tuple(rincian)


def nilai_sektor_berjalan(
    sambungan: sqlite3.Connection,
    kolom: str,
    sektor: str,
    *,
    kecuali: int | None = None,
) -> tuple[int, int]:
    """Nilai posisi yang sudah tersimpan di satu sektor + berapa rencana yang tak terhitung.

    `kolom` adalah taksonomi yang dipakai (`sektor_idx_ic` atau `sektor_sumber`, K25). Rencana
    yang emitennya **tidak punya nilai pada kolom itu** tidak boleh ikut dijumlahkan — mencampur
    dua taksonomi membuat paparan sektor tampak lebih kecil daripada kenyataannya. Karena itu
    jumlah yang dikecualikan dikembalikan untuk dilaporkan, bukan didiamkan.
    """
    if kolom not in (KOLOM_SEKTOR_IDX_IC, KOLOM_SEKTOR_SUMBER):
        raise GalatRisiko(
            f"kolom sektor {kolom!r} tidak dikenal; yang sah: {KOLOM_SEKTOR_IDX_IC}, "
            f"{KOLOM_SEKTOR_SUMBER}"
        )
    total = 0
    dikecualikan = 0
    for baris in sambungan.execute(
        f"SELECT r.id_rencana, r.lembar, r.harga_masuk, e.{kolom} AS sektor"
        " FROM v_rencana_terkini AS r"
        " LEFT JOIN v_emiten_terkini AS e ON e.kode = r.kode"
    ):
        if kecuali is not None and int(baris["id_rencana"]) == kecuali:
            continue
        if not baris["sektor"]:
            dikecualikan += 1
            continue
        if baris["sektor"] != sektor:
            continue
        total += int(baris["lembar"]) * int(baris["harga_masuk"])
    return total, dikecualikan


# ---------------------------------------------------------------------------------------
# Masukan dari basis data & snapshot
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MasukanRisiko:
    """Seluruh masukan kalkulator untuk satu emiten, beserta asal tiap angkanya."""

    kode: str
    potret: modul_potret.Potret
    seri: object
    harga_terakhir: metrik.Nilai
    atr14: metrik.Nilai
    adtv20: metrik.Nilai
    harga_acuan: int
    lot: int
    tabel_tick: TabelTick
    biaya: BiayaSisi
    slippage: int
    asal_slippage: str
    batas: PresetRisiko
    ekuitas: int
    kas: int | None
    asal_ekuitas: str
    risiko_berjalan: int
    rincian_risiko_berjalan: tuple[str, ...]
    #: Kolom sektor yang dipakai berhitung (K25): `sektor_idx_ic` bila terisi, selain itu
    #: `sektor_sumber`. `None` = keduanya kosong, dan batas sektornya tidak dapat dinilai.
    sektor_kolom: str | None
    sektor_sebutan: str | None
    sektor: str | None
    nilai_sektor: int | None
    #: Rencana tersimpan yang tidak ikut dijumlahkan karena emitennya tidak punya sektor pada
    #: taksonomi yang dipakai — dilaporkan, sebab ia membuat paparan sektor tampak lebih kecil.
    sektor_dikecualikan: int = 0
    catatan: tuple[str, ...] = field(default_factory=tuple)


def _lot(sambungan: sqlite3.Connection, pada: date | None) -> int:
    status = konfigurasi.nilai_efektif(sambungan, "lot", "", pada)
    entri = status.ambil()
    return int(entri.muatan[0]["nilai_lembar"])


def siapkan_masukan(
    sambungan: sqlite3.Connection,
    kode: str,
    *,
    pada: date | None = None,
    sumber: str | None = None,
    ekuitas_penimpa: int | None = None,
    kas_penimpa: int | None = None,
    harga_acuan: int | None = None,
    broker: str | None = None,
) -> MasukanRisiko:
    """Kumpulkan seluruh masukan kalkulator dari basis data, atau menolak dengan sebabnya.

    Yang **tidak** dikarang di sini: ekuitas (dari `ekuitas_harian`, F11) dan kas. Bila keduanya
    belum pernah dicatat, kalkulator tetap berjalan tetapi batas kas menjadi "tidak dinilai" —
    kecuali pengguna menimpanya dengan `--ekuitas`/`--kas`, dan penimpanya dilaporkan apa adanya.
    """
    kode = kode.strip().upper()
    potret = modul_potret.muat(sambungan, sumber=sumber)
    if kode not in potret.emiten:
        raise GalatRisiko(
            f"kode {kode!r} tidak ada pada snapshot {potret.id_snapshot} "
            f"({potret.tanggal_data.isoformat()}). Periksa ejaannya, atau jalankan --refresh."
        )

    seri = metrik.seri_harga(potret, kode)
    harga_terakhir = metrik.harga_terakhir(seri)
    atr14 = metrik.atr14_rupiah(seri)
    adtv20 = metrik.adtv20(seri)
    lot = _lot(sambungan, pada)
    tabel = tabel_tick(sambungan, pada)

    acuan = harga_acuan
    if acuan is None:
        if not harga_terakhir.ada:
            raise GalatRisiko(
                f"harga terakhir {kode} tidak bisa dipakai: {harga_terakhir.alasan}. Isi "
                "--harga-masuk sendiri, atau periksa mutu data harga emiten ini (PRD 7.3)."
            )
        mentah = int(round(float(harga_terakhir.nilai)))  # type: ignore[arg-type]
        diturunkan = tabel.bulatkan_ke_bawah(mentah)
        if diturunkan is None:
            raise GalatRisiko(
                f"penutupan terakhir {kode} Rp{mentah} di luar tabel fraksi harga (B2); "
                "isi --harga-masuk dengan harga yang masuk pita."
            )
        acuan = diturunkan
    periksa_harga(acuan, tabel, "harga masuk")

    biaya = biaya_sisi(sambungan, SISI_BELI, acuan, pada, broker=broker)
    slippage, asal_slippage = slippage_per_lembar(sambungan, acuan, tabel, pada)

    emiten = potret.emiten[kode]
    sektor_kolom, sektor = pilih_sektor(emiten)
    nilai_sektor: int | None = None
    sektor_dikecualikan = 0
    if sektor_kolom is not None and sektor is not None:
        nilai_sektor, sektor_dikecualikan = nilai_sektor_berjalan(sambungan, sektor_kolom, sektor)

    catatan: list[str] = []
    tercatat = ekuitas_terakhir(sambungan, pada)
    if ekuitas_penimpa is not None:
        ekuitas = ekuitas_penimpa
        asal_ekuitas = "dari --ekuitas, bukan ekuitas harian yang tercatat (F11)"
    elif tercatat is not None:
        ekuitas = tercatat.ekuitas
        asal_ekuitas = f"ekuitas harian {tercatat.tanggal} ({tercatat.sumber})"
    else:
        raise GalatRisiko(
            "ekuitas portofolio belum pernah dicatat, dan itulah penyebut seluruh risiko "
            "(PRD 9.7). Catat dulu: python -m mejasaham --ekuitas-harian <rupiah> [--kas <rupiah>]"
            " — atau isi --ekuitas untuk perhitungan ini saja."
        )
    kas = kas_penimpa if kas_penimpa is not None else (tercatat.kas if tercatat else None)
    if kas_penimpa is not None and tercatat is not None and tercatat.kas is not None:
        catatan.append(
            f"kas ditimpa --kas {kas_penimpa}; kas tercatat {tercatat.tanggal} "
            f"{tercatat.kas} tidak dipakai"
        )

    berjalan = risiko_berjalan_lengkap(sambungan)
    rincian = berjalan.rincian
    if berjalan.tidak_dinilai:
        catatan.append(
            f"{len(berjalan.tidak_dinilai)} suku risiko berjalan TIDAK DAPAT DINILAI, sehingga "
            "angka risiko berjalan di bawah lebih kecil daripada risiko yang sebenarnya: "
            + "; ".join(berjalan.tidak_dinilai)
        )
    if sektor_kolom is None:
        catatan.append(
            "sektor emiten ini belum terisi — baik `sektor_idx_ic` (klasifikasi yang dipakai PRD) "
            "maupun `sektor_sumber` (taksonomi sumber data, K25) — jadi batas bobot per sektor "
            "tidak dapat dinilai. Isi salah satunya di emiten.csv, atau jalankan --ambil-jenis "
            "untuk menurunkan `sektor_sumber` dari data"
        )
    elif sektor_kolom == KOLOM_SEKTOR_SUMBER:
        catatan.append(
            f"batas bobot per sektor dinilai memakai `sektor_sumber` ({SEBUTAN_SEKTOR[sektor_kolom]}:"
            f" {sektor}) karena `sektor_idx_ic` belum terisi (K25). Begitu `sektor_idx_ic` diisi, "
            "kolom itulah yang dipakai"
        )
    if sektor_dikecualikan:
        catatan.append(
            f"{sektor_dikecualikan} rencana tersimpan tidak ikut dijumlahkan ke paparan sektor "
            f"karena emitennya tidak punya nilai pada `{sektor_kolom}` — paparan sektor yang "
            "terhitung karena itu bisa lebih kecil daripada kenyataan"
        )
    if not adtv20.ada:
        catatan.append(f"ADTV20 tidak dihitung: {adtv20.alasan}")
    if biaya.minimum is not None:
        catatan.append(
            f"tarif minimum broker Rp{biaya.minimum} per transaksi tidak masuk rumus per lembar "
            "PRD 9.7; pada ukuran kecil, risiko nominal bisa lebih besar daripada yang tertulis"
        )

    return MasukanRisiko(
        kode=kode,
        potret=potret,
        seri=seri,
        harga_terakhir=harga_terakhir,
        atr14=atr14,
        adtv20=adtv20,
        harga_acuan=acuan,
        lot=lot,
        tabel_tick=tabel,
        biaya=biaya,
        slippage=slippage,
        asal_slippage=asal_slippage,
        batas=preset_terbaru(sambungan),
        ekuitas=ekuitas,
        kas=kas,
        asal_ekuitas=asal_ekuitas,
        risiko_berjalan=berjalan.total,
        rincian_risiko_berjalan=rincian,
        sektor_kolom=sektor_kolom,
        sektor_sebutan=None if sektor_kolom is None else SEBUTAN_SEKTOR[sektor_kolom],
        sektor=sektor,
        nilai_sektor=nilai_sektor,
        sektor_dikecualikan=sektor_dikecualikan,
        catatan=tuple(catatan),
    )


def stop_bawaan(
    masukan: MasukanRisiko,
    harga_masuk: int,
    *,
    harga_pembatal: int | None = None,
) -> tuple[int, str, tuple[str, ...]]:
    """Stop bawaan PRD 9.7: `max(harga masuk − 2 × ATR14, harga pembatal tesis)`.

    Stop hasil rumus ATR dibulatkan **ke bawah** ke tick yang sah, dan arah itu disengaja:
    stop yang lebih rendah membuat risiko per lembar **lebih besar**, sehingga ukuran posisi
    yang disarankan tidak pernah lebih besar daripada yang pantas (PRD 10: risiko yang
    ditampilkan adalah batas bawah). Harga pembatal dari tesis datang dari pengguna, jadi ia
    tidak digeser: kalau bukan kelipatan tick, ia ditolak beserta tick sah terdekatnya.
    """
    catatan: list[str] = []
    kandidat: list[tuple[int, str]] = []
    if masukan.atr14.ada:
        mentah = harga_masuk - 2 * float(masukan.atr14.nilai)  # type: ignore[arg-type]
        dibulatkan = masukan.tabel_tick.bulatkan_ke_bawah(int(mentah))
        if dibulatkan is None or dibulatkan <= 0:
            catatan.append(
                f"stop dari ATR14 ({mentah:.1f}) jatuh di luar tabel fraksi harga; tidak dipakai"
            )
        else:
            if dibulatkan != int(mentah):
                catatan.append(
                    f"stop ATR14 {tampilan.angka(mentah, 1)} dibulatkan ke bawah ke tick sah {dibulatkan} "
                    "(arah ini membuat risiko tidak pernah lebih kecil daripada kenyataan)"
                )
            kandidat.append((dibulatkan, "harga_masuk_minus_2_atr14"))
    else:
        catatan.append(f"ATR14 tidak dihitung: {masukan.atr14.alasan}")

    if harga_pembatal is not None:
        periksa_harga(harga_pembatal, masukan.tabel_tick, "harga pembatal")
        if harga_pembatal >= harga_masuk:
            raise GalatRisiko(
                f"harga pembatal {harga_pembatal} tidak lebih rendah dari harga masuk "
                f"{harga_masuk}; pembatal tesis yang di atas harga masuk tidak bisa dipakai "
                "sebagai stop posisi beli (PRD 9.7)"
            )
        kandidat.append((harga_pembatal, "harga_pembatal"))

    if not kandidat:
        raise GalatRisiko(
            "stop tidak bisa diturunkan: ATR14 tidak dihitung dan harga pembatal tesis tidak "
            "diisi. Isi --stop, atau --harga-pembatal, atau periksa data harga emiten ini."
        )
    stop, dasar = max(kandidat, key=lambda satu: satu[0])
    if dasar == "harga_pembatal":
        catatan.append(
            "stop memakai harga pembatal tesis karena lebih ketat daripada 2 × ATR14 (PRD 9.7)"
        )
    return stop, dasar, tuple(catatan)


def pakai_ukuran(
    hasil: HasilRisiko, lembar: int, *, lot: int, batas_total_bp: int
) -> HasilRisiko:
    """Salinan hasil dengan ukuran akhir diganti — saat pengguna memilih ukuran yang patuh.

    PRD 9.7 menuntut kalkulator **menawarkan ukuran yang patuh** ketika batas terlewati. Seluruh
    angka turunan dihitung ulang dari ukuran baru, bukan disalin: bobot, risiko nominal, dan
    total risiko harus selalu konsisten dengan jumlah lembar yang disimpan — kalau hanya kolom
    `lembar` yang diganti, rencananya akan berbohong tentang risikonya sendiri.
    """
    if lembar < 0:
        raise GalatRisiko(f"ukuran tidak boleh negatif, bukan {lembar}")
    if lembar % lot != 0:
        raise GalatRisiko(
            f"ukuran {lembar} lembar bukan kelipatan lot {lot}; jumlah lembar selalu kelipatan "
            "lot (PRD 10)"
        )
    nilai_posisi = lembar * hasil.harga_masuk
    bobot_bp = nilai_posisi * 10000 // hasil.ekuitas
    risiko_nominal = lembar * hasil.risiko_per_lembar
    total_risiko_bp = (hasil.risiko_berjalan + risiko_nominal) * 10000 // hasil.ekuitas

    pelanggaran: list[Pelanggaran] = []
    if total_risiko_bp > batas_total_bp:
        pelanggaran.append(
            Pelanggaran(
                batas=TOTAL_RISIKO_MAKSIMUM,
                pesan=(
                    f"total risiko berjalan setelah posisi ini {_persen(total_risiko_bp)} "
                    f"melewati batas {_persen(batas_total_bp)}"
                ),
            )
        )
    if bobot_bp > hasil.bobot_bp:
        # Ukuran yang dipilih justru lebih besar daripada hitungan awal: itu keputusan pengguna,
        # tetapi ia harus terlihat — bukan tersamar sebagai hasil kalkulator.
        pelanggaran.append(
            Pelanggaran(
                batas=BOBOT_MAKSIMUM,
                pesan=(
                    f"ukuran yang dipilih ({lembar} lembar, bobot {_persen(bobot_bp)}) lebih "
                    f"besar daripada hitungan kalkulator ({hasil.lembar} lembar, "
                    f"{_persen(hasil.bobot_bp)})"
                ),
            )
        )

    catatan = (*hasil.catatan, "ukuran diambil dari tawaran ukuran yang patuh (PRD 9.7)")
    return replace(
        hasil,
        lembar=lembar,
        nilai_posisi=nilai_posisi,
        bobot_bp=bobot_bp,
        risiko_nominal=risiko_nominal,
        total_risiko_bp=total_risiko_bp,
        lembar_patuh_total_risiko=min(hasil.lembar_patuh_total_risiko, lembar),
        pelanggaran=tuple(pelanggaran),
        catatan=catatan,
    )


def pakai_ukuran_patuh(hasil: HasilRisiko, masukan: MasukanRisiko) -> HasilRisiko:
    """Hasil dengan ukuran diganti **tawaran ukuran yang patuh** (PRD 9.7).

    Satu tempat untuk dua mode: `--pakai-ukuran-patuh` di baris perintah dan pilihan "Pakai
    ukuran patuh" di layar 11.4 (K63) sama-sama lewat sini. Kalau keduanya menyusun sendiri
    panggilan `pakai_ukuran`-nya, `lot` dan batas total risikonya bisa berbeda diam-diam — dan
    yang berbeda adalah jumlah lembar yang tersimpan sebagai rencana.
    """
    return pakai_ukuran(
        hasil,
        hasil.ukuran_patuh,
        lot=masukan.lot,
        batas_total_bp=masukan.batas.bp(TOTAL_RISIKO_MAKSIMUM),
    )


def hitung_untuk(
    masukan: MasukanRisiko,
    *,
    harga_masuk: int,
    stop_penimpa: int | None = None,
    harga_pembatal: int | None = None,
    jenis_stop: str | None = None,
) -> tuple[HasilRisiko, int]:
    """Hitung ukuran posisi untuk satu masukan. Kembalikan hasil dan stop yang dipakai."""
    catatan = list(masukan.catatan)
    if stop_penimpa is None:
        stop, dasar_stop, catatan_stop = stop_bawaan(
            masukan, harga_masuk, harga_pembatal=harga_pembatal
        )
        catatan.extend(catatan_stop)
    else:
        periksa_harga(stop_penimpa, masukan.tabel_tick, "stop")
        stop, dasar_stop = stop_penimpa, "pengguna"
    if harga_pembatal is not None and stop_penimpa is not None and harga_pembatal > stop_penimpa:
        catatan.append(
            f"stop yang diisi ({stop_penimpa}) lebih rendah daripada harga pembatal tesis "
            f"({harga_pembatal}): pembatal tesis akan terpicu sebelum stop (PRD 9.6)"
        )

    hasil = hitung(
        kode=masukan.kode,
        ekuitas=masukan.ekuitas,
        harga_masuk=harga_masuk,
        stop=stop,
        biaya_slippage=masukan.biaya.biaya_per_lembar + masukan.slippage,
        lot=masukan.lot,
        batas=masukan.batas,
        risiko_berjalan=masukan.risiko_berjalan,
        adtv20=float(masukan.adtv20.nilai) if masukan.adtv20.ada else None,  # type: ignore[arg-type]
        kas=masukan.kas,
        nilai_sektor=masukan.nilai_sektor,
        sektor_sebutan=masukan.sektor_sebutan,
        sektor_dikecualikan=masukan.sektor_dikecualikan,
        dasar_stop=dasar_stop,
        atr14_rupiah=float(masukan.atr14.nilai) if masukan.atr14.ada else None,  # type: ignore[arg-type]
        harga_terakhir=(
            float(masukan.harga_terakhir.nilai) if masukan.harga_terakhir.ada else None  # type: ignore[arg-type]
        ),
        jenis_stop=jenis_stop,
        catatan=catatan,
    )
    return hasil, stop


# ---------------------------------------------------------------------------------------
# Rencana tersimpan (PRD 8.1)
# ---------------------------------------------------------------------------------------

_KOLOM_RENCANA = (
    "id_rencana",
    "revisi",
    "id_kandidat",
    "kode",
    "id_preset_risiko",
    "id_snapshot",
    "tanggal",
    "ekuitas",
    "risiko_per_posisi_bp",
    "harga_masuk",
    "stop",
    "dasar_stop",
    "biaya_slippage",
    "lembar_mentah_mili",
    "lembar",
    "maks_lembar_bobot",
    "maks_lembar_sektor",
    "maks_lembar_likuiditas",
    "maks_lembar_kas",
    "bobot_bp",
    "risiko_nominal",
    "risiko_berjalan",
    "total_risiko_bp",
    "jenis_stop",
    "batas_tidak_dinilai",
    "catatan",
    "dicatat_pada",
)


@dataclass(frozen=True)
class Rencana:
    """Satu revisi rencana ukuran posisi."""

    id_rencana: int
    revisi: int
    id_kandidat: int
    kode: str
    id_preset_risiko: str
    id_snapshot: int
    tanggal: str
    ekuitas: int
    risiko_per_posisi_bp: int
    harga_masuk: int
    stop: int
    dasar_stop: str
    biaya_slippage: int
    lembar_mentah_mili: int
    lembar: int
    maks_lembar_bobot: int
    maks_lembar_sektor: int | None
    maks_lembar_likuiditas: int | None
    maks_lembar_kas: int | None
    bobot_bp: int
    risiko_nominal: int
    risiko_berjalan: int
    total_risiko_bp: int
    jenis_stop: str
    batas_tidak_dinilai: str | None
    catatan: str | None
    dicatat_pada: str

    @property
    def nilai_posisi(self) -> int:
        return self.lembar * self.harga_masuk

    def ringkas(self) -> str:
        """Satu baris untuk daftar rencana. Angka tampil format Indonesia (U11)."""

        bagian = [
            f"#{self.id_rencana} r{self.revisi}",
            self.kode,
            f"{tampilan.angka(self.lembar, 0)} lembar",
            f"masuk {tampilan.rupiah(self.harga_masuk)}",
            f"stop {tampilan.rupiah(self.stop)}",
            f"bobot {tampilan.angka(self.bobot_bp / 100, 2)}%",
            f"risiko {tampilan.rupiah(self.risiko_nominal)}",
            f"total {tampilan.angka(self.total_risiko_bp / 100, 2)}%",
            self.jenis_stop,
        ]
        teks = " · ".join(bagian)
        if self.batas_tidak_dinilai:
            teks += f"\n      BATAS TIDAK DINILAI: {self.batas_tidak_dinilai}"
        return teks


def _ke_rencana(baris: sqlite3.Row) -> Rencana:
    return Rencana(**{kolom: baris[kolom] for kolom in _KOLOM_RENCANA})


def terkini(sambungan: sqlite3.Connection, id_rencana: int) -> Rencana | None:
    baris = sambungan.execute(
        "SELECT * FROM v_rencana_terkini WHERE id_rencana = ?", (id_rencana,)
    ).fetchone()
    return None if baris is None else _ke_rencana(baris)


def daftar(sambungan: sqlite3.Connection, *, kode: str | None = None) -> tuple[Rencana, ...]:
    kueri = "SELECT * FROM v_rencana_terkini"
    nilai: list[object] = []
    if kode is not None:
        kueri += " WHERE kode = ?"
        nilai.append(kode.strip().upper())
    kueri += " ORDER BY id_rencana"
    return tuple(_ke_rencana(baris) for baris in sambungan.execute(kueri, nilai))


def riwayat(sambungan: sqlite3.Connection, id_rencana: int) -> tuple[Rencana, ...]:
    baris = sambungan.execute(
        "SELECT * FROM rencana WHERE id_rencana = ? ORDER BY revisi", (id_rencana,)
    ).fetchall()
    return tuple(_ke_rencana(satu) for satu in baris)


def simpan(
    sambungan: sqlite3.Connection,
    hasil: HasilRisiko,
    *,
    id_kandidat: int,
    jenis_stop: str,
    id_snapshot: int,
    id_rencana: int | None = None,
    tanggal: date | None = None,
    pelanggaran_diterima: bool = False,
    dicatat_pada: str | None = None,
) -> Rencana:
    """Simpan rencana sebagai revisi baru (PRD 8.1, 9.7 "Perilaku menolak").

    Rencana dengan pelanggaran **tidak** ditolak mentah-mentah: PRD 9.7 menuntut pengguna
    memilih lebih dulu, dan pilihannya itu sendiri harus tercatat. Karena itu penerimaan
    pelanggaran wajib dinyatakan lewat `pelanggaran_diterima=True`, lalu alasannya ikut tersimpan
    di kolom `catatan` — bukan hilang.
    """
    if jenis_stop not in JENIS_STOP_SAH:
        raise GalatRisiko(
            f"jenis stop {jenis_stop!r} tidak dikenal; yang sah: {JENIS_STOP_SAH} (Q9, PRD 9.7). "
            "Kolom ini wajib: tanpa itu, cara stop dieksekusi tidak tercatat."
        )
    if hasil.pelanggaran and not pelanggaran_diterima:
        rinci = "; ".join(satu.pesan for satu in hasil.pelanggaran)
        raise GalatRisiko(
            f"rencana belum bisa disimpan: {rinci}. Pilih salah satu (PRD 9.7): pakai ukuran "
            f"yang patuh ({hasil.ukuran_patuh} lembar), atau terima pelanggarannya secara "
            "eksplisit (--terima-pelanggaran) supaya pilihan itu ikut tercatat."
        )
    if hasil.lembar == 0:
        raise GalatRisiko(
            "ukuran akhirnya nol lembar: tidak ada yang bisa dibeli dalam batas yang berlaku. "
            "Rencana nol lembar tidak disimpan — periksa harga masuk, stop, dan batasnya."
        )

    catatan = list(hasil.catatan)
    if hasil.pelanggaran:
        catatan.insert(
            0,
            "PELANGGARAN DITERIMA pengguna: " + "; ".join(satu.pesan for satu in hasil.pelanggaran),
        )
    teks_catatan = "\n".join(catatan)

    baris = {
        "revisi": 1,
        "id_kandidat": id_kandidat,
        "kode": hasil.kode,
        "id_preset_risiko": hasil.id_preset_risiko,
        "id_snapshot": id_snapshot,
        "tanggal": (tanggal or date.today()).isoformat(),
        "ekuitas": hasil.ekuitas,
        "risiko_per_posisi_bp": hasil.risiko_per_posisi_bp,
        "harga_masuk": hasil.harga_masuk,
        "stop": hasil.stop,
        "dasar_stop": hasil.dasar_stop,
        "biaya_slippage": hasil.biaya_slippage,
        "lembar_mentah_mili": int(hasil.lembar_mentah * 1000),
        "lembar": hasil.lembar,
        "maks_lembar_bobot": hasil.maks_lembar_bobot,
        "maks_lembar_sektor": hasil.maks_lembar_sektor,
        "maks_lembar_likuiditas": hasil.maks_lembar_likuiditas,
        "maks_lembar_kas": hasil.maks_lembar_kas,
        "bobot_bp": hasil.bobot_bp,
        "risiko_nominal": hasil.risiko_nominal,
        "risiko_berjalan": hasil.risiko_berjalan,
        "total_risiko_bp": hasil.total_risiko_bp,
        "jenis_stop": jenis_stop,
        "batas_tidak_dinilai": "; ".join(hasil.batas_tidak_dinilai) or None,
        "catatan": teks_catatan or None,
    }
    if id_rencana is not None:
        lama = terkini(sambungan, id_rencana)
        if lama is None:
            raise GalatRisiko(f"rencana #{id_rencana} tidak ada di basis data")
        baris["id_rencana"] = id_rencana
        baris["revisi"] = lama.revisi + 1
    else:
        baris["id_rencana"] = int(
            sambungan.execute("SELECT COALESCE(MAX(id_rencana), 0) + 1 FROM rencana").fetchone()[0]
        )

    kolom = list(baris)
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            f"INSERT INTO rencana ({', '.join(kolom)}, dicatat_pada)"
            f" VALUES ({', '.join('?' for _ in kolom)}, ?)",
            [*baris.values(), dicatat_pada or db.waktu_iso()],
        )
    hasil_rencana = terkini(sambungan, int(baris["id_rencana"]))
    assert hasil_rencana is not None  # baru saja ditulis; ketiadaannya berarti basis datanya rusak
    return hasil_rencana


def ringkas_daftar(daftar_rencana: Iterable[Rencana]) -> str:
    isi = list(daftar_rencana)
    if not isi:
        return "(belum ada rencana tersimpan)"
    return "\n".join(satu.ringkas() for satu in isi)


@dataclass(frozen=True)
class RencanaTersimpan:
    """Hasil `simpan_dari_kandidat`: rencananya, dan apa yang **belum** beres sesudahnya."""

    rencana: Rencana
    status_dipindahkan: bool
    peringatan: str | None

    def ringkas(self) -> str:
        return (
            f"Rencana #{self.rencana.id_rencana} revisi {self.rencana.revisi} disimpan: "
            f"{self.rencana.lembar} lembar @ {self.rencana.harga_masuk}, "
            f"stop {self.rencana.stop}, risiko {self.rencana.risiko_nominal}, "
            f"id_preset_risiko {self.rencana.id_preset_risiko}"
        )


def simpan_dari_kandidat(
    sambungan: sqlite3.Connection,
    hasil: HasilRisiko,
    *,
    entri: kandidat.Kandidat,
    jenis_stop: str,
    id_snapshot: int,
    id_rencana: int | None = None,
    tanggal: date | None = None,
    pelanggaran_diterima: bool = False,
) -> RencanaTersimpan:
    """Simpan rencana atas sebuah entri kandidat, lalu pindahkan statusnya (PRD 9.6, 9.7).

    Dipakai **dua mode** (baris perintah dan jendela) justru karena aturannya mudah bercabang:
    rencana baru menuntut kandidat berstatus `watchlist`, revisi rencana menuntut `--rencana-revisi`,
    dan sesudah rencana tersimpan statusnya berpindah `watchlist` → `rencana`. Salinan aturan itu
    di dua tempat akan berbeda begitu salah satunya disunting — dan yang berbeda adalah tesis mana
    yang menempel pada sebuah posisi.

    Yang **tidak** dilakukan: menelan kegagalan perpindahan statusnya. Rencananya sudah tersimpan
    saat itu, jadi kegagalan itu dilaporkan lewat `peringatan` — pemanggil yang memutuskan cara
    menampilkannya (dan tidak boleh mengaku seluruhnya gagal: barisnya ada).
    """
    sah = (entri.status == "watchlist" and id_rencana is None) or (
        entri.status == "rencana" and id_rencana is not None
    )
    if not sah:
        raise GalatRisiko(
            f"kandidat #{entri.id_kandidat} berstatus {entri.status!r}; rencana baru menuntut status "
            "'watchlist', sedangkan revisi rencana menuntut --rencana-revisi ID (PRD 9.6)."
        )

    rencana = simpan(
        sambungan,
        hasil,
        id_kandidat=entri.id_kandidat,
        jenis_stop=jenis_stop,
        id_snapshot=id_snapshot,
        id_rencana=id_rencana,
        tanggal=tanggal,
        pelanggaran_diterima=pelanggaran_diterima,
    )
    if entri.status != "watchlist":
        return RencanaTersimpan(rencana=rencana, status_dipindahkan=False, peringatan=None)

    # Perpindahan status dilakukan **sesudah** rencananya tersimpan, dan kegagalannya dilaporkan
    # apa adanya: menyembunyikannya akan membuat kandidat tetap berstatus watchlist sementara
    # rencananya sudah ada — dua catatan yang saling bertentangan.
    try:
        kandidat.ubah(sambungan, entri.id_kandidat, {"status": "rencana"})
    except (kandidat.GalatKandidat, db.GalatBasisData) as galat:
        return RencanaTersimpan(
            rencana=rencana,
            status_dipindahkan=False,
            peringatan=(
                f"rencana #{rencana.id_rencana} tersimpan, tetapi status kandidat "
                f"#{entri.id_kandidat} gagal dipindahkan ke 'rencana': {galat}"
            ),
        )
    return RencanaTersimpan(rencana=rencana, status_dipindahkan=True, peringatan=None)


def _batas_lembar(nilai: int | None) -> str:
    """Batas per sisi untuk keluaran: angkanya, atau tanda "tidak dinilai" — bukan nol."""
    return "— (tidak dinilai)" if nilai is None else f"{nilai} lembar"


def ringkas_hasil(hasil: HasilRisiko, masukan: MasukanRisiko) -> str:
    """Seluruh keluaran kalkulator (PRD 9.7/11.4) sebagai teks — **satu** tempat untuk dua mode.

    Baris perintah dan panel jendela menampilkan angka yang sama, jadi teksnya tinggal di sini.
    Dua salinan teks yang sama akan berbeda begitu salah satunya disunting, dan yang berbeda
    adalah angka risiko yang dibaca orang sebelum menekan tombol beli.

    Batas yang datanya tidak ada berbunyi "tidak dinilai", bukan nol (aturan keras 2).
    """
    baris = [
        f"Snapshot          : #{masukan.potret.id_snapshot} "
        f"{masukan.potret.tanggal_data.isoformat()}"
        + (f" · sumber harga {masukan.potret.sumber_harga}" if masukan.potret.sumber_harga else ""),
        f"Kode              : {hasil.kode}",
        f"Ekuitas           : {tampilan.rupiah(hasil.ekuitas)}  ({masukan.asal_ekuitas})",
        f"Risiko per posisi : {tampilan.angka(hasil.risiko_per_posisi_bp / 100, 2)}%  ->  "
        f"{tampilan.rupiah(hasil.anggaran_risiko)}",
        f"Harga masuk       : {tampilan.rupiah(hasil.harga_masuk)}   "
        f"Stop: {tampilan.rupiah(hasil.stop)}   "
        f"(selisih {tampilan.rupiah(hasil.harga_masuk - hasil.stop)}, dasar: {hasil.dasar_stop})",
    ]
    if hasil.atr14_rupiah is not None:
        baris.append(
            f"ATR14             : {tampilan.rupiah(hasil.atr14_rupiah, 2)}  "
            f"(2 × ATR14 = {tampilan.rupiah(2 * hasil.atr14_rupiah, 2)})"
        )
    baris.append(
        f"Biaya+slippage    : {tampilan.rupiah(hasil.biaya_slippage)} per lembar  ->  "
        f"risiko {tampilan.rupiah(hasil.risiko_per_lembar)} per lembar"
    )
    for satu in masukan.biaya.rincian:
        baris.append(f"                    - {satu}")
    baris.append(f"                    - {masukan.asal_slippage}")
    baris.append(f"Ukuran mentah     : {tampilan.angka(float(hasil.lembar_mentah), 1)} lembar")
    baris.append(
        f"Ukuran akhir      : {tampilan.angka(hasil.lembar, 0)} lembar "
        f"({hasil.lembar // masukan.lot} lot)  =  {tampilan.rupiah(hasil.nilai_posisi)}"
    )
    baris.append(
        f"Bobot             : {tampilan.angka(hasil.bobot_bp / 100, 2)}%  "
        f"(batas {masukan.batas.ringkas(BOBOT_MAKSIMUM)} = {hasil.maks_lembar_bobot} lembar)"
    )
    baris.append(
        f"Risiko nominal    : {tampilan.rupiah(hasil.risiko_nominal)}  "
        f"({tampilan.angka(hasil.risiko_nominal * 10000 / hasil.ekuitas / 100, 2)}% ekuitas)"
    )
    baris.append(
        f"Risiko berjalan   : {tampilan.rupiah(hasil.risiko_berjalan)}  ->  setelah posisi ini "
        f"{tampilan.angka(hasil.total_risiko_bp / 100, 2)}%  "
        f"(batas {masukan.batas.ringkas(TOTAL_RISIKO_MAKSIMUM)})"
    )
    for satu in masukan.rincian_risiko_berjalan:
        baris.append(f"                    - {satu}")
    baris.append(
        "Batas lain        : "
        + " | ".join(
            [
                "sektor " + _batas_lembar(hasil.maks_lembar_sektor),
                "likuiditas " + _batas_lembar(hasil.maks_lembar_likuiditas),
                "kas " + _batas_lembar(hasil.maks_lembar_kas),
            ]
        )
    )
    for satu in hasil.pembatasan:
        baris.append(f"  DIBATASI: {satu}")
    for satu in hasil.pelanggaran:
        baris.append(f"  PELANGGARAN: {satu.pesan}")
    baris.append(
        f"Ukuran patuh      : {hasil.ukuran_patuh} lembar "
        f"({hasil.ukuran_patuh // masukan.lot} lot)"
        + ("  (sama dengan ukuran akhir)" if hasil.ukuran_patuh == hasil.lembar else "")
    )
    for satu in hasil.batas_tidak_dinilai:
        baris.append(f"  TIDAK DINILAI: {satu}")
    for satu in hasil.catatan:
        baris.append(f"  catatan: {satu}")
    return "\n".join(baris)
