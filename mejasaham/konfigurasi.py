"""Parameter bursa bertanggal: dari TOML (alat edit) ke basis data (bukti hitung) — K1, K6, T7.

Aturan yang ditegakkan berkas ini, bukan sekadar didokumentasikan:

1. **Tidak ada nilai tebakan.** Entri hanya ada bila sudah diverifikasi; "belum terverifikasi"
   diwakili oleh **tidak adanya baris**, bukan oleh angka 0 atau nilai default (aturan keras 1,
   PRD bagian 10). Karena itu tidak ada satu pun nilai parameter bursa di dalam kode ini.
2. **Wajib bertanggal dan bersumber.** Setiap entri memuat `berlaku_sejak`, `dicatat_pada`, dan
   `sumber`; entri tanpa salah satunya **ditolak saat dimuat** dengan pesan yang menyebut entri
   mana dan kunci apa yang kurang.
3. **Append-only.** Memuat ulang berkas yang sama tidak menambah baris (sidik jari SHA-256),
   sedangkan entri dengan identitas sama tetapi isi berbeda **gagal berisik** dan tidak menimpa
   apa pun — perbaikannya menambah baris dengan `dicatat_pada` lebih baru (PRD 7.2).
4. **Salah ketik ditolak, bukan diabaikan.** Kunci yang tidak dikenal, tipe yang salah, persen
   di luar 0–100, dan rentang fraksi harga yang berlubang atau tumpang tindih semuanya berhenti
   dengan pesan; berkas konfigurasi yang salah baca lebih berbahaya daripada berkas yang menolak
   dimuat.
5. **Tiga keadaan nilai** (`nilai_efektif`): entri tidak ada → "belum terverifikasi"; entri ada
   dengan `aktif = false` → "sengaja dinonaktifkan"; entri ada dan aktif → dipakai. Yang
   bergantung padanya memakai `StatusParameter.ambil()`, yang menolak berhitung saat keadaan
   bukan "dipakai".

Satuan mengikuti T8/D-8: rupiah dan lembar `INTEGER`; persen masuk sebagai **basis poin**
(1 bp = 0,01%), dikonversi dengan `Decimal` supaya 0,15% menjadi 15 bp — bukan 14 bp seperti
hasil `float` yang dipotong. Format tampilan Indonesia (U11) bukan urusan berkas ini.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from mejasaham import db, lokasi
from mejasaham.skema import ASAL_BERLAKU_SEJAK_SAH, KOMPONEN_BIAYA_BROKER_TERMASUK

NAMA_BERKAS_AKTIF = "parameter-bursa.toml"
NAMA_BERKAS_CONTOH = "parameter-bursa.contoh.toml"
FOLDER_BAWAAN = Path(__file__).resolve().parent / "defaults"

#: Versi bentuk berkas TOML yang dikenal aplikasi ini (`skema = 1` di berkas).
SKEMA_DIDUKUNG = 1

DIPAKAI = "dipakai"
NONAKTIF = "nonaktif"
BELUM_TERVERIFIKASI = "belum_terverifikasi"

#: Kunci yang boleh ada di setiap entri, di luar kunci muatan parameter.
KUNCI_UMUM = frozenset(
    {"berlaku_sejak", "asal_berlaku_sejak", "sumber", "dicatat_pada", "aktif", "uraian"}
)
KUNCI_WAJIB_UMUM = ("berlaku_sejak", "sumber", "dicatat_pada")

#: Kolom kunci kepala yang ikut di setiap tabel muatan.
_KUNCI_KEPALA = ("nama", "kelompok", "berlaku_sejak", "dicatat_pada")

#: Kunci muatan yang **tidak** menjadi kolom tabel muatan, melainkan baris di tabel anaknya.
#: Daftarnya satu tempat dengan penulisnya (`_sisip`), supaya kolom dan tabel tidak bisa berbeda.
_KUNCI_TABEL_ANAK: Mapping[str, str] = {
    "sudah_termasuk": "parameter_biaya_broker_termasuk",
}

#: Kolom tabel anak yang berisi nilai daftarnya.
_KOLOM_TABEL_ANAK = "komponen"


class GalatKonfigurasi(RuntimeError):
    """Berkas parameter tidak bisa dipakai apa adanya."""


class ParameterBelumSiap(GalatKonfigurasi):
    """Parameter diminta untuk berhitung, padahal belum terverifikasi atau dinonaktifkan.

    Ada sebagai kelas tersendiri supaya pemanggil tidak bisa "menyelamatkan" perhitungan dengan
    nilai default tanpa terlihat: aturan keras 1 menuntut fitur menolak menghitung.
    """


# ---------------------------------------------------------------------------------------
# Konversi nilai: TOML bebas tulis → kolom bertipe (T8, D-8)
# ---------------------------------------------------------------------------------------


def _galat(di_mana: str, pesan: str) -> GalatKonfigurasi:
    return GalatKonfigurasi(f"{di_mana}: {pesan}")


def _tanggal(nilai: Any, di_mana: str) -> date:
    if isinstance(nilai, datetime) or not isinstance(nilai, date):
        raise _galat(
            di_mana,
            "harus tanggal TOML tanpa tanda kutip dan tanpa jam, mis. 2026-10-06 "
            f"(yang terbaca: {nilai!r})",
        )
    return nilai


def _teks(nilai: Any, di_mana: str, *, kosong_boleh: bool = False) -> str:
    if not isinstance(nilai, str):
        raise _galat(di_mana, f"harus teks dalam tanda kutip (yang terbaca: {nilai!r})")
    if not nilai.strip() and not kosong_boleh:
        raise _galat(di_mana, "tidak boleh kosong")
    return nilai.strip()


def _integer(nilai: Any, di_mana: str, *, minimum: int | None = None, maksimum: int | None = None) -> int:
    """Bilangan bulat rupiah/lembar/hari. Berpecahan ditolak, bukan dibulatkan diam-diam."""
    if isinstance(nilai, bool) or not isinstance(nilai, (int, float, Decimal)):
        raise _galat(di_mana, f"harus bilangan tanpa tanda kutip (yang terbaca: {nilai!r})")
    try:
        angka = Decimal(str(nilai))
    except InvalidOperation as galat:  # pragma: no cover - str(float/int) selalu bisa diurai
        raise _galat(di_mana, f"bukan bilangan yang bisa dibaca: {nilai!r}") from galat
    if angka != angka.to_integral_value():
        raise _galat(
            di_mana,
            f"harus bilangan bulat; nilai berpecahan tidak dipakai berhitung (T8). "
            f"Yang terbaca: {nilai!r}",
        )
    hasil = int(angka)
    batas = []
    if minimum is not None:
        batas.append(f"minimal {minimum}")
    if maksimum is not None:
        batas.append(f"maksimal {maksimum}")
    if batas and not (
        (minimum is None or hasil >= minimum) and (maksimum is None or hasil <= maksimum)
    ):
        raise _galat(di_mana, f"nilai {hasil} di luar batas yang masuk akal ({', '.join(batas)})")
    return hasil


def _basis_poin(nilai: Any, di_mana: str) -> int:
    """Persen TOML (mis. 0,15) → basis poin INTEGER (15). D-8: tingkat/rasio disimpan bp."""
    if isinstance(nilai, bool) or not isinstance(nilai, (int, float, Decimal)):
        raise _galat(di_mana, f"harus persen sebagai bilangan tanpa tanda kutip (yang terbaca: {nilai!r})")
    try:
        angka = Decimal(str(nilai))
    except InvalidOperation as galat:  # pragma: no cover - str(float/int) selalu bisa diurai
        raise _galat(di_mana, f"bukan bilangan yang bisa dibaca: {nilai!r}") from galat
    # Dibulatkan setengah ke atas pada pecahan basis poin; Decimal dipakai supaya 0,15%
    # tidak menjadi 14 bp karena galat representasi float.
    bp = int((angka * 100).to_integral_value(rounding=ROUND_HALF_UP))
    if bp < 0 or bp > 10000:
        raise _galat(di_mana, f"persen harus antara 0 dan 100 (yang terbaca: {nilai!r})")
    return bp


def _tabel_inline(
    nilai: Any, di_mana: str, kunci_dikenal: frozenset[str], kunci_wajib: frozenset[str]
) -> Mapping[str, Any]:
    """Tabel inline TOML (`{ persen = 0.15, minimum = 10000 }`) dengan kunci yang diperiksa."""
    if not isinstance(nilai, Mapping):
        raise _galat(
            di_mana,
            f"harus tabel inline, mis. {{ persen = 0.15, minimum = 10000 }} "
            f"(yang terbaca: {nilai!r})",
        )
    tak_dikenal = sorted(set(nilai) - kunci_dikenal)
    if tak_dikenal:
        raise _galat(
            di_mana, f"kunci tidak dikenal {tak_dikenal}; kunci yang sah: {sorted(kunci_dikenal)}"
        )
    kurang = sorted(kunci_wajib - set(nilai))
    if kurang:
        raise _galat(di_mana, f"kunci wajib belum ada: {kurang}")
    return nilai


# ---------------------------------------------------------------------------------------
# Spesifikasi tiap parameter: kunci TOML → kolom tabel muatan
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SpesifikasiParameter:
    """Bentuk satu parameter: kunci yang sah, tabel muatan, dan cara mengubah nilainya."""

    nama: str
    #: Nama kunci kelompok di TOML, mis. "nama" (broker) atau "kelompok" (ARA/ARB).
    #: None berarti parameter ini tidak berkelompok.
    kunci_kelompok: str | None
    kunci_payload: frozenset[str]
    kunci_wajib: frozenset[str]
    tabel_muatan: str | None
    pengubah: Callable[[Mapping[str, Any], str], list[dict[str, Any]]]
    kunci_item: frozenset[str] = frozenset()
    kunci_item_wajib: frozenset[str] = frozenset()
    urut_muatan: str | None = None


def _ubah_lot(entri: Mapping[str, Any], di_mana: str) -> list[dict[str, Any]]:
    return [{"nilai_lembar": _integer(entri["nilai_lembar"], f"{di_mana}.nilai_lembar", minimum=1)}]


def _batas_atas(item: Mapping[str, Any], di_mana: str) -> int | None:
    if "batas_atas" not in item:
        # Rentang teratas boleh tanpa batas atas: harga di atas batas bawah terakhir.
        return None
    return _integer(item["batas_atas"], f"{di_mana}.batas_atas", minimum=0)


def _rentang(item: Sequence[Mapping[str, Any]], di_mana: str) -> list[dict[str, Any]]:
    return [
        {
            "batas_bawah": _integer(
                potongan["batas_bawah"], f"{di_mana}.rentang[{i}].batas_bawah", minimum=0
            ),
            "batas_atas": _batas_atas(potongan, f"{di_mana}.rentang[{i}]"),
        }
        for i, potongan in enumerate(item)
    ]


def _ubah_fraksi_harga(entri: Mapping[str, Any], di_mana: str) -> list[dict[str, Any]]:
    baris = _rentang(entri["rentang"], di_mana)
    for i, (potongan, hasil) in enumerate(zip(entri["rentang"], baris)):
        hasil["tick"] = _integer(potongan["tick"], f"{di_mana}.rentang[{i}].tick", minimum=1)
    return baris


def _ubah_auto_rejection(entri: Mapping[str, Any], di_mana: str) -> list[dict[str, Any]]:
    baris = _rentang(entri["rentang"], di_mana)
    for i, (potongan, hasil) in enumerate(zip(entri["rentang"], baris)):
        hasil["ara_persen_bp"] = _basis_poin(potongan["ara_persen"], f"{di_mana}.rentang[{i}].ara_persen")
        hasil["arb_persen_bp"] = _basis_poin(potongan["arb_persen"], f"{di_mana}.rentang[{i}].arb_persen")
    return baris


def _ubah_settlement(entri: Mapping[str, Any], di_mana: str) -> list[dict[str, Any]]:
    return [
        {
            "hari_kerja": _integer(
                entri["hari_kerja"], f"{di_mana}.hari_kerja", minimum=0, maksimum=30
            )
        }
    ]


def _ubah_biaya_broker(entri: Mapping[str, Any], di_mana: str) -> list[dict[str, Any]]:
    """Tarif broker sisi beli & sisi jual (B6/B7).

    `minimum` **opsional** (K22): halaman tarif resmi Stockbit menyatakan `0,15%`/`0,25%` dengan
    tegas tetapi tidak menyatakan tarif minimumnya. Tidak menuliskannya berarti "sumber tidak
    menyatakannya" dan tersimpan sebagai NULL — **bukan** 0, sebab 0 berarti "tidak ada tarif
    minimum", dan itu pernyataan yang sumbernya tidak buat.
    """
    sisi = frozenset({"persen", "minimum"})
    beli = _tabel_inline(entri["sisi_beli"], f"{di_mana}.sisi_beli", sisi, frozenset({"persen"}))
    jual = _tabel_inline(entri["sisi_jual"], f"{di_mana}.sisi_jual", sisi, frozenset({"persen"}))
    muatan: dict[str, Any] = {
        "persen_beli_bp": _basis_poin(beli["persen"], f"{di_mana}.sisi_beli.persen"),
        "minimum_beli": _minimum(beli, f"{di_mana}.sisi_beli"),
        "persen_jual_bp": _basis_poin(jual["persen"], f"{di_mana}.sisi_jual.persen"),
        "minimum_jual": _minimum(jual, f"{di_mana}.sisi_jual"),
    }
    if "sudah_termasuk" in entri:
        muatan["sudah_termasuk"] = _daftar_komponen(
            entri["sudah_termasuk"], f"{di_mana}.sudah_termasuk"
        )
    return [muatan]


def _minimum(sisi: Mapping[str, Any], di_mana: str) -> int | None:
    """Tarif minimum rupiah; `None` bila sumber tidak menyatakannya (K22)."""
    if "minimum" not in sisi:
        return None
    return _integer(sisi["minimum"], f"{di_mana}.minimum", minimum=0)


def _daftar_komponen(nilai: Any, di_mana: str) -> list[str]:
    """Daftar komponen yang dinyatakan sumber sudah termasuk di dalam tarifnya (K23).

    Nilai tak dikenal dan komponen ganda **ditolak berisik**: keduanya sama-sama membuat
    kalkulator biaya salah tanpa terlihat — yang pertama karena komponennya tidak dikenali
    (lalu diam-diam diabaikan), yang kedua karena komponen yang sama bisa dihitung dua kali.
    """
    if not isinstance(nilai, list):
        raise _galat(
            di_mana,
            f"harus daftar teks, mis. {list(KOMPONEN_BIAYA_BROKER_TERMASUK)} "
            f"(yang terbaca: {nilai!r})",
        )
    komponen: list[str] = []
    for i, satu in enumerate(nilai):
        teks = _teks(satu, f"{di_mana}[{i}]")
        if teks not in KOMPONEN_BIAYA_BROKER_TERMASUK:
            raise _galat(
                f"{di_mana}[{i}]",
                f"komponen {teks!r} tidak dikenal; komponen yang sah: "
                f"{list(KOMPONEN_BIAYA_BROKER_TERMASUK)}. Nilai yang tidak dikenal tidak "
                "diabaikan diam-diam: komponen yang hilang membuat biaya kurang dihitung tanpa "
                "satu pun tanda di keluaran",
            )
        if teks in komponen:
            raise _galat(
                f"{di_mana}[{i}]",
                f"komponen {teks!r} disebut lebih dari sekali; daftar komponen tidak boleh "
                "memuat nilai ganda",
            )
        komponen.append(teks)
    # Dikembalikan berurutan: urutan penulisan di berkas bukan fakta, dan memuat berkas yang
    # sama dua kali tidak boleh terlihat berbeda hanya karena urutannya ditulis terbalik (A5).
    return sorted(komponen)


def _ubah_pajak_penjualan(entri: Mapping[str, Any], di_mana: str) -> list[dict[str, Any]]:
    return [
        {
            "persen_bp": _basis_poin(entri["persen"], f"{di_mana}.persen"),
            "dasar": _teks(entri["dasar"], f"{di_mana}.dasar"),
        }
    ]


def _ubah_slippage(entri: Mapping[str, Any], di_mana: str) -> list[dict[str, Any]]:
    mode = _teks(entri["mode"], f"{di_mana}.mode")
    if mode == "tick":
        return [
            {
                "mode": mode,
                "nilai_tick": _integer(entri["nilai"], f"{di_mana}.nilai", minimum=1),
                "nilai_persen_bp": None,
            }
        ]
    if mode == "persen":
        return [
            {
                "mode": mode,
                "nilai_tick": None,
                "nilai_persen_bp": _basis_poin(entri["nilai"], f"{di_mana}.nilai"),
            }
        ]
    raise _galat(di_mana, f"mode harus \"tick\" atau \"persen\" (yang terbaca: {mode!r})")


def _ubah_tanpa_muatan(_entri: Mapping[str, Any], _di_mana: str) -> list[dict[str, Any]]:
    """Parameter yang bentuk terstrukturnya belum diketahui: hanya `uraian` yang tersimpan."""
    return []


_SPESIFIKASI_URUT: tuple[SpesifikasiParameter, ...] = (
    SpesifikasiParameter(
        nama="lot",
        kunci_kelompok=None,
        kunci_payload=frozenset({"nilai_lembar"}),
        kunci_wajib=frozenset({"nilai_lembar"}),
        tabel_muatan="parameter_lot",
        pengubah=_ubah_lot,
    ),
    SpesifikasiParameter(
        nama="fraksi_harga",
        kunci_kelompok=None,
        kunci_payload=frozenset({"rentang"}),
        kunci_wajib=frozenset({"rentang"}),
        kunci_item=frozenset({"batas_bawah", "batas_atas", "tick"}),
        kunci_item_wajib=frozenset({"batas_bawah", "tick"}),
        tabel_muatan="parameter_fraksi_harga_rentang",
        pengubah=_ubah_fraksi_harga,
        urut_muatan="batas_bawah",
    ),
    SpesifikasiParameter(
        nama="papan_pemantauan_khusus",
        kunci_kelompok=None,
        kunci_payload=frozenset(),
        kunci_wajib=frozenset(),
        tabel_muatan=None,
        pengubah=_ubah_tanpa_muatan,
    ),
    SpesifikasiParameter(
        nama="auto_rejection",
        kunci_kelompok="kelompok",
        kunci_payload=frozenset({"rentang"}),
        kunci_wajib=frozenset({"rentang"}),
        kunci_item=frozenset({"batas_bawah", "batas_atas", "ara_persen", "arb_persen"}),
        kunci_item_wajib=frozenset({"batas_bawah", "ara_persen", "arb_persen"}),
        tabel_muatan="parameter_auto_rejection_rentang",
        pengubah=_ubah_auto_rejection,
        urut_muatan="batas_bawah",
    ),
    SpesifikasiParameter(
        nama="settlement",
        kunci_kelompok=None,
        kunci_payload=frozenset({"hari_kerja"}),
        kunci_wajib=frozenset({"hari_kerja"}),
        tabel_muatan="parameter_settlement",
        pengubah=_ubah_settlement,
    ),
    SpesifikasiParameter(
        nama="biaya_broker",
        kunci_kelompok="nama",
        # `sudah_termasuk` (K23) berisi komponen yang dinyatakan sumber sudah tercakup di dalam
        # tarifnya — mis. levy/PPN/PPh final pada tarif all-in Stockbit. Tanpa penanda ini,
        # kalkulator biaya menambahkan B8 (0,1%) di atas tarif yang sudah memuatnya: salah dua
        # kali, dan tidak terlihat di keluaran mana pun — hanya di angkanya.
        kunci_payload=frozenset({"sisi_beli", "sisi_jual", "sudah_termasuk"}),
        kunci_wajib=frozenset({"sisi_beli", "sisi_jual"}),
        tabel_muatan="parameter_biaya_broker",
        pengubah=_ubah_biaya_broker,
    ),
    SpesifikasiParameter(
        nama="pajak_penjualan",
        kunci_kelompok=None,
        kunci_payload=frozenset({"persen", "dasar"}),
        kunci_wajib=frozenset({"persen", "dasar"}),
        tabel_muatan="parameter_pajak_penjualan",
        pengubah=_ubah_pajak_penjualan,
    ),
    SpesifikasiParameter(
        nama="slippage",
        kunci_kelompok=None,
        kunci_payload=frozenset({"mode", "nilai"}),
        kunci_wajib=frozenset({"mode", "nilai"}),
        tabel_muatan="parameter_slippage",
        pengubah=_ubah_slippage,
    ),
)

SPESIFIKASI: dict[str, SpesifikasiParameter] = {
    spesifikasi.nama: spesifikasi for spesifikasi in _SPESIFIKASI_URUT
}


# ---------------------------------------------------------------------------------------
# Entri hasil urai
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EntriParameter:
    """Satu entri parameter yang sudah tervalidasi dan siap disimpan."""

    nama: str
    kelompok: str
    berlaku_sejak: date
    dicatat_pada: date
    sumber: str
    aktif: bool
    uraian: str | None
    muatan: tuple[dict[str, Any], ...]
    sidik_jari: str
    #: Asal `berlaku_sejak` (K22): `'sumber'` bila tanggalnya dinyatakan sumbernya, atau
    #: `'tanggal_pengamatan'` bila yang dipakai tanggal pengamatan. Dibawa sampai barisnya
    #: supaya "tanggal berlaku tidak diketahui" tidak pernah menyamar sebagai "berlaku sejak".
    asal_berlaku_sejak: str = "sumber"

    @property
    def kunci(self) -> tuple[str, str, str, str]:
        """Kunci kepala di basis data (mengikuti urutan kolom `parameter_bursa`)."""
        return (self.nama, self.kelompok, self.berlaku_sejak.isoformat(), self.dicatat_pada.isoformat())

    @property
    def label(self) -> str:
        return f"{self.nama} [{self.kelompok}]" if self.kelompok else self.nama


def _sidik_jari(entri: EntriParameter) -> str:
    isi = {
        "nama": entri.nama,
        "kelompok": entri.kelompok,
        "berlaku_sejak": entri.berlaku_sejak.isoformat(),
        "dicatat_pada": entri.dicatat_pada.isoformat(),
        "sumber": entri.sumber,
        "aktif": entri.aktif,
        "uraian": entri.uraian,
        "muatan": [dict(baris) for baris in entri.muatan],
    }
    kanonik = json.dumps(isi, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(kanonik.encode("utf-8")).hexdigest()


def _periksa_rentang(baris: list[dict[str, Any]], di_mana: str, label: str) -> list[dict[str, Any]]:
    """Rentang harus menutup berurutan tanpa celah dan tanpa tumpang tindih.

    Hanya rentang teratas yang boleh tanpa `batas_atas`. Dikembalikan dalam urutan naik supaya
    yang tersimpan berurutan (A5: urutan tidak boleh bergantung urutan tulis di berkas).
    """
    if not baris:
        raise _galat(di_mana, f"`rentang` {label} tidak boleh kosong")
    urut = sorted(baris, key=lambda potongan: potongan["batas_bawah"])
    for sebelumnya, sekarang in zip(urut, urut[1:]):
        if sebelumnya["batas_atas"] is None:
            raise _galat(
                di_mana,
                f"`rentang` {label}: hanya rentang teratas yang boleh tanpa `batas_atas`, "
                f"tetapi rentang mulai {sebelumnya['batas_bawah']} sudah tanpa batas atas",
            )
        if sekarang["batas_bawah"] != sebelumnya["batas_atas"] + 1:
            raise _galat(
                di_mana,
                f"`rentang` {label} harus menutup tanpa celah dan tanpa tumpang tindih "
                f"(batas atas & bawah inklusif): rentang berakhir di {sebelumnya['batas_atas']}, "
                f"rentang berikutnya mulai di {sekarang['batas_bawah']}",
            )
    return urut


def _urai_entri(
    spesifikasi: SpesifikasiParameter, mentah: Mapping[str, Any], di_mana: str
) -> EntriParameter:
    kunci_dikenal = set(KUNCI_UMUM) | set(spesifikasi.kunci_payload)
    if spesifikasi.kunci_kelompok:
        kunci_dikenal.add(spesifikasi.kunci_kelompok)

    tak_dikenal = sorted(set(mentah) - kunci_dikenal)
    if tak_dikenal:
        raise _galat(
            di_mana,
            f"kunci tidak dikenal {tak_dikenal}; kunci yang sah di sini: {sorted(kunci_dikenal)}",
        )

    for kunci in KUNCI_WAJIB_UMUM:
        if kunci not in mentah:
            raise _galat(di_mana, f"kunci wajib `{kunci}` tidak ada")
    kurang = sorted(spesifikasi.kunci_wajib - set(mentah))
    if kurang:
        raise _galat(di_mana, f"kunci wajib belum ada: {kurang}")
    if spesifikasi.kunci_kelompok and spesifikasi.kunci_kelompok not in mentah:
        raise _galat(
            di_mana,
            f"kunci wajib `{spesifikasi.kunci_kelompok}` tidak ada; parameter "
            f"{spesifikasi.nama} dibedakan per kelompok, jadi kelompoknya harus disebut",
        )

    aktif = mentah.get("aktif", True)
    if not isinstance(aktif, bool):
        raise _galat(di_mana, f"`aktif` harus true atau false (yang terbaca: {aktif!r})")

    # Tanggal & sumber diperiksa lebih dulu daripada muatan: galat bentuk entri lebih menolong
    # daripada galat nilai, dan urutannya tidak bergantung isi parameter.
    berlaku_sejak = _tanggal(mentah["berlaku_sejak"], f"{di_mana}.berlaku_sejak")
    asal_berlaku_sejak = _teks(
        mentah.get("asal_berlaku_sejak", "sumber"), f"{di_mana}.asal_berlaku_sejak"
    )
    if asal_berlaku_sejak not in ASAL_BERLAKU_SEJAK_SAH:
        raise _galat(
            f"{di_mana}.asal_berlaku_sejak",
            f"nilai {asal_berlaku_sejak!r} tidak dikenal; nilai yang sah: "
            f"{list(ASAL_BERLAKU_SEJAK_SAH)}. Dipakai untuk membedakan tanggal yang dinyatakan "
            "sumber dari tanggal pengamatan — tanpa itu, 'tanggal berlaku tidak diketahui' "
            "terbaca sebagai 'berlaku sejak' (K22)",
        )
    dicatat_pada = _tanggal(mentah["dicatat_pada"], f"{di_mana}.dicatat_pada")
    sumber = _teks(mentah["sumber"], f"{di_mana}.sumber")

    uraian = _teks(mentah["uraian"], f"{di_mana}.uraian") if "uraian" in mentah else None
    if spesifikasi.nama == "papan_pemantauan_khusus" and not uraian:
        raise _galat(
            di_mana,
            "aturan papan pemantauan khusus belum punya bentuk terstruktur, jadi `uraian` "
            "wajib diisi apa adanya dari sumber",
        )

    if spesifikasi.kunci_kelompok:
        kelompok = _teks(mentah[spesifikasi.kunci_kelompok], f"{di_mana}.{spesifikasi.kunci_kelompok}")
    else:
        kelompok = ""

    if spesifikasi.kunci_item:
        _periksa_item(mentah, spesifikasi, di_mana)

    muatan = list(spesifikasi.pengubah(mentah, di_mana))
    if spesifikasi.kunci_item:  # parameter berdaftar: periksa kesinambungan & urutkan rentang
        muatan = _periksa_rentang(muatan, di_mana, spesifikasi.nama)
    if spesifikasi.tabel_muatan is not None and not muatan:
        raise _galat(di_mana, f"nilai {spesifikasi.nama} tidak terbaca (kosong)")

    entri = EntriParameter(
        nama=spesifikasi.nama,
        kelompok=kelompok,
        berlaku_sejak=berlaku_sejak,
        dicatat_pada=dicatat_pada,
        sumber=sumber,
        aktif=aktif,
        uraian=uraian,
        muatan=tuple(muatan),
        sidik_jari="",
        asal_berlaku_sejak=asal_berlaku_sejak,
    )
    return replace(entri, sidik_jari=_sidik_jari(entri))


def _periksa_item(mentah: Mapping[str, Any], spesifikasi: SpesifikasiParameter, di_mana: str) -> None:
    """Periksa kunci tiap elemen daftar (`rentang`), termasuk salah ketik di dalamnya."""
    for kunci in spesifikasi.kunci_payload:
        if kunci not in mentah:
            continue
        daftar = mentah[kunci]
        if not isinstance(daftar, list):
            raise _galat(di_mana, f"`{kunci}` harus ditulis sebagai daftar tabel, mis. [[...]]")
        for i, potongan in enumerate(daftar):
            if not isinstance(potongan, Mapping):
                raise _galat(di_mana, f"`{kunci}[{i}]` harus tabel, bukan {type(potongan).__name__}")
            tak_dikenal = sorted(set(potongan) - spesifikasi.kunci_item)
            if tak_dikenal:
                raise _galat(
                    di_mana,
                    f"`{kunci}[{i}]` memuat kunci tidak dikenal {tak_dikenal}; "
                    f"kunci yang sah: {sorted(spesifikasi.kunci_item)}",
                )
            kurang = sorted(spesifikasi.kunci_item_wajib - set(potongan))
            if kurang:
                raise _galat(di_mana, f"`{kunci}[{i}]` belum memuat kunci wajib: {kurang}")


def _urai_dokumen(dokumen: Mapping[str, Any], asal: str) -> tuple[EntriParameter, ...]:
    if "skema" not in dokumen:
        raise GalatKonfigurasi(f"{asal}: wajib memuat `skema = {SKEMA_DIDUKUNG}` di bagian atas")
    if dokumen["skema"] != SKEMA_DIDUKUNG:
        raise GalatKonfigurasi(
            f"{asal}: `skema = {dokumen['skema']!r}` tidak dikenal aplikasi ini "
            f"(yang dikenal: {SKEMA_DIDUKUNG}). Perbarui aplikasi atau berkasnya; "
            "berkas dengan bentuk lebih baru tidak dimuat setengah-setengah."
        )

    tak_dikenal = sorted(set(dokumen) - {"skema"} - set(SPESIFIKASI))
    if tak_dikenal:
        raise GalatKonfigurasi(
            f"{asal}: tabel tidak dikenal {tak_dikenal}; parameter yang dikenal: "
            f"{sorted(SPESIFIKASI)}"
        )

    terlihat: set[tuple[str, str, str, str]] = set()
    entri: list[EntriParameter] = []
    for spesifikasi in _SPESIFIKASI_URUT:
        blok = dokumen.get(spesifikasi.nama, [])
        if not isinstance(blok, list):
            raise GalatKonfigurasi(
                f"{asal}: `{spesifikasi.nama}` harus ditulis sebagai daftar tabel, mis. "
                f"[[{spesifikasi.nama}]]"
            )
        for urutan, mentah in enumerate(blok, start=1):
            di_mana = f"{asal}: [[{spesifikasi.nama}]] ke-{urutan}"
            if not isinstance(mentah, Mapping):
                raise GalatKonfigurasi(f"{di_mana}: harus tabel, bukan {type(mentah).__name__}")
            satu = _urai_entri(spesifikasi, mentah, di_mana)
            if satu.kunci in terlihat:
                raise GalatKonfigurasi(
                    f"{di_mana}: {satu.label} sudah ditulis di tempat lain di berkas ini dengan "
                    f"berlaku_sejak {satu.berlaku_sejak.isoformat()} dan dicatat_pada "
                    f"{satu.dicatat_pada.isoformat()}. Satu entri satu tempat."
                )
            terlihat.add(satu.kunci)
            entri.append(satu)

    return tuple(sorted(entri, key=lambda satu: satu.kunci))


def urai(teks: str, asal: str = "<teks>") -> tuple[EntriParameter, ...]:
    """Urai isi berkas parameter (tanpa menyentuh basis data). Dipakai test dan `--muat-konfigurasi`."""
    try:
        dokumen = tomllib.loads(teks)
    except tomllib.TOMLDecodeError as galat:
        raise GalatKonfigurasi(f"{asal}: bukan TOML yang sah — {galat}") from galat
    return _urai_dokumen(dokumen, asal)


# ---------------------------------------------------------------------------------------
# Berkas: salin bawaan saat belum ada, lalu muat
# ---------------------------------------------------------------------------------------


def berkas_parameter() -> Path:
    """Letak berkas parameter aktif (di folder data pengguna, bukan di dalam paket) — A3."""
    return lokasi.folder_konfigurasi() / NAMA_BERKAS_AKTIF


def siapkan_berkas(berkas: Path | None = None) -> tuple[Path, bool]:
    """Pastikan berkas parameter ada. Kembalikan (jalur, baru_disalin).

    Bila belum ada, template bawaan di `defaults/` disalin apa adanya. Inilah yang membuat
    AC-12 bisa dipenuhi: isi folder data dihapus → aplikasi kembali ke konfigurasi bawaan,
    dan bawaannya tetap kosong dari nilai yang belum diverifikasi.
    """
    tujuan = Path(berkas) if berkas is not None else berkas_parameter()
    if tujuan.exists():
        return tujuan, False

    lokasi.pastikan_folder(tujuan.parent)
    bawaan = FOLDER_BAWAAN / NAMA_BERKAS_CONTOH
    if not bawaan.is_file():
        raise GalatKonfigurasi(
            f"template bawaan '{bawaan}' tidak ditemukan; pemasangan aplikasi tidak lengkap "
            "(folder defaults/ harus ikut ke dalam bundel)"
        )
    try:
        shutil.copyfile(bawaan, tujuan)
    except OSError as galat:
        raise GalatKonfigurasi(
            f"tidak bisa menyalin template parameter ke '{tujuan}': {galat}. Periksa izin folder "
            "itu, atau arahkan MEJASAHAM_DATA ke folder lain yang bisa ditulis."
        ) from galat
    return tujuan, True


def muat_berkas(berkas: Path | None = None) -> tuple[Path, tuple[EntriParameter, ...]]:
    """Baca dan uraikan berkas parameter; tidak menulis apa pun ke basis data."""
    jalur = Path(berkas) if berkas is not None else berkas_parameter()
    if not jalur.is_file():
        raise GalatKonfigurasi(
            f"berkas parameter '{jalur}' tidak ada. Jalankan pemuatan konfigurasi lebih dulu "
            "supaya template bawaan disalin ke sana."
        )
    try:
        # utf-8-sig: berkas yang disunting Notepad bisa ber-BOM, dan BOM akan membuat tomllib
        # menolak baris pertamanya — kegagalan yang membingungkan untuk masalah sepele.
        teks = jalur.read_text(encoding="utf-8-sig")
    except OSError as galat:
        raise GalatKonfigurasi(f"tidak bisa membaca berkas parameter '{jalur}': {galat}") from galat
    return jalur, urai(teks, asal=str(jalur))


# ---------------------------------------------------------------------------------------
# Simpan ke basis data (append-only, idempoten)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HasilMuat:
    """Ringkasan satu kali pemuatan: berapa entri baru, berapa yang sudah ada dan sama."""

    baru: int
    tetap: int
    entri: tuple[EntriParameter, ...]

    @property
    def total(self) -> int:
        return len(self.entri)


def _sisip(sambungan: sqlite3.Connection, entri: EntriParameter) -> None:
    sambungan.execute(
        "INSERT INTO parameter_bursa"
        " (nama, kelompok, berlaku_sejak, dicatat_pada, sumber, aktif, uraian, sidik_jari,"
        "  asal_berlaku_sejak)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            *entri.kunci,
            entri.sumber,
            int(entri.aktif),
            entri.uraian,
            entri.sidik_jari,
            entri.asal_berlaku_sejak,
        ),
    )
    tabel = SPESIFIKASI[entri.nama].tabel_muatan
    if tabel is None:
        return
    for baris in entri.muatan:
        # Kunci yang isinya daftar (mis. `sudah_termasuk`, K23) tidak menjadi kolom: isinya
        # ditulis sebagai baris di tabel anaknya, satu baris per komponen.
        kolom = [nama for nama in baris if nama not in _KUNCI_TABEL_ANAK]
        nilai = [baris[nama] for nama in kolom]
        sambungan.execute(
            f"INSERT INTO {tabel} (nama, kelompok, berlaku_sejak, dicatat_pada,"
            f" {', '.join(kolom)})"
            f" VALUES (?, ?, ?, ?, {', '.join('?' for _ in kolom)})",
            (*entri.kunci, *nilai),
        )
        for kunci_anak, nilai_anak in baris.items():
            if kunci_anak not in _KUNCI_TABEL_ANAK:
                continue
            for satu in nilai_anak:
                sambungan.execute(
                    f"INSERT INTO {_KUNCI_TABEL_ANAK[kunci_anak]}"
                    " (nama, kelompok, berlaku_sejak, dicatat_pada,"
                    f" {_KOLOM_TABEL_ANAK})"
                    " VALUES (?, ?, ?, ?, ?)",
                    (*entri.kunci, satu),
                )


def simpan(sambungan: sqlite3.Connection, entri: Sequence[EntriParameter]) -> HasilMuat:
    """Simpan entri ke basis data dalam satu transaksi (A6).

    Idempoten: entri yang isinya persis sama dengan yang sudah ada dilewati. Entri dengan
    identitas sama tetapi isi berbeda **menggagalkan seluruh pemuatan** — menimpa nilai lama
    dilarang (PRD 7.2), jadi yang benar adalah menambah entri baru dengan `dicatat_pada`
    lebih baru atau `berlaku_sejak` lebih baru.

    Pemeriksaannya dua tingkat, dan urutannya disengaja: **isi** dulu (sidik jari), baru
    **asal tanggal berlaku** (`asal_berlaku_sejak`, K22). Kalau isinya memang sudah berbeda,
    itulah sebabnya — menyebut asal tanggal lebih dulu hanya menyebutkan sebab yang salah.
    """
    urut = tuple(sorted(entri, key=lambda satu: satu.kunci))
    baru = 0
    tetap = 0
    with db.tulis(sambungan):
        for satu in urut:
            lama = sambungan.execute(
                "SELECT sidik_jari, asal_berlaku_sejak FROM parameter_bursa"
                " WHERE nama = ? AND kelompok = ? AND berlaku_sejak = ? AND dicatat_pada = ?",
                satu.kunci,
            ).fetchone()
            if lama is None:
                _sisip(sambungan, satu)
                baru += 1
                continue
            if lama["sidik_jari"] != satu.sidik_jari:
                raise GalatKonfigurasi(
                    f"{satu.label} dengan berlaku_sejak {satu.berlaku_sejak.isoformat()} dan "
                    f"dicatat_pada {satu.dicatat_pada.isoformat()} sudah ada di basis data dengan "
                    "isi yang berbeda. Baris lama tidak boleh ditimpa (append-only, PRD 7.2): "
                    "perbaiki berkas dengan menambah entri baru memakai `dicatat_pada` yang lebih "
                    "baru (nilai lama tetap tersimpan), atau kembalikan isinya seperti semula."
                )
            if lama["asal_berlaku_sejak"] != satu.asal_berlaku_sejak:
                raise GalatKonfigurasi(
                    f"{satu.label} dengan berlaku_sejak {satu.berlaku_sejak.isoformat()} dan "
                    f"dicatat_pada {satu.dicatat_pada.isoformat()} sudah tersimpan dengan "
                    f"asal_berlaku_sejak {lama['asal_berlaku_sejak']!r}, sedangkan berkas ini "
                    f"menyatakan {satu.asal_berlaku_sejak!r}. Keduanya berbeda arti — 'berlaku "
                    "sejak' bukan 'diamati pada' (K22) — dan baris lama tidak boleh ditimpa "
                    "(append-only, PRD 7.2): tambahkan entri baru dengan `dicatat_pada` yang "
                    "lebih baru, atau betulkan nilai di berkas."
                )
            tetap += 1
    return HasilMuat(baru=baru, tetap=tetap, entri=urut)


# ---------------------------------------------------------------------------------------
# Membaca kembali: nilai efektif pada satu tanggal
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StatusParameter:
    """Keadaan satu parameter pada satu tanggal, beserta alasan yang bisa ditampilkan."""

    nama: str
    kelompok: str
    keadaan: str
    entri: EntriParameter | None
    alasan: str

    @property
    def siap(self) -> bool:
        return self.keadaan == DIPAKAI

    def ambil(self) -> EntriParameter:
        """Nilai yang boleh dipakai berhitung; menolak bila belum terverifikasi/nonaktif."""
        if self.entri is None or not self.siap:
            raise ParameterBelumSiap(self.alasan)
        return self.entri

    @property
    def label(self) -> str:
        return f"{self.nama} [{self.kelompok}]" if self.kelompok else self.nama


def _baca_muatan(
    sambungan: sqlite3.Connection, nama: str, kunci: tuple[str, str, str, str]
) -> tuple[dict[str, Any], ...]:
    spesifikasi = SPESIFIKASI[nama]
    if spesifikasi.tabel_muatan is None:
        return ()
    urut = f" ORDER BY {spesifikasi.urut_muatan}" if spesifikasi.urut_muatan else ""
    baris = sambungan.execute(
        f"SELECT * FROM {spesifikasi.tabel_muatan}"
        " WHERE nama = ? AND kelompok = ? AND berlaku_sejak = ? AND dicatat_pada = ?" + urut,
        kunci,
    ).fetchall()
    hasil = [
        {kunci_kolom: satu[kunci_kolom] for kunci_kolom in satu.keys() if kunci_kolom not in _KUNCI_KEPALA}
        for satu in baris
    ]
    for kunci_anak, tabel_anak in _KUNCI_TABEL_ANAK.items():
        if kunci_anak not in spesifikasi.kunci_payload:
            continue
        # Daftarnya dibaca dari tabel anaknya, berurutan menurut nilainya: urutan di berkas
        # bukan fakta, jadi yang tersimpan harus berurutan (A5) — kalau tidak, memuat berkas
        # yang sama dua kali akan terlihat berbeda hanya karena urutan penulisannya.
        isi = [
            satu[_KOLOM_TABEL_ANAK]
            for satu in sambungan.execute(
                f"SELECT {_KOLOM_TABEL_ANAK} FROM {tabel_anak}"
                " WHERE nama = ? AND kelompok = ? AND berlaku_sejak = ? AND dicatat_pada = ?"
                f" ORDER BY {_KOLOM_TABEL_ANAK}",
                kunci,
            )
        ]
        for satu in hasil:
            satu[kunci_anak] = isi
    return tuple(hasil)


def _entri_dari_baris(sambungan: sqlite3.Connection, baris: sqlite3.Row) -> EntriParameter:
    kunci = (baris["nama"], baris["kelompok"], baris["berlaku_sejak"], baris["dicatat_pada"])
    entri = EntriParameter(
        nama=baris["nama"],
        kelompok=baris["kelompok"],
        berlaku_sejak=date.fromisoformat(baris["berlaku_sejak"]),
        dicatat_pada=date.fromisoformat(baris["dicatat_pada"]),
        sumber=baris["sumber"],
        aktif=bool(baris["aktif"]),
        uraian=baris["uraian"],
        muatan=_baca_muatan(sambungan, baris["nama"], kunci),
        sidik_jari=baris["sidik_jari"],
        asal_berlaku_sejak=baris["asal_berlaku_sejak"],
    )
    return entri


def nilai_efektif(
    sambungan: sqlite3.Connection, nama: str, kelompok: str = "", pada: date | None = None
) -> StatusParameter:
    """Entri parameter yang berlaku pada `pada` (default hari ini), beserta keadaannya.

    Yang dipakai adalah entri dengan `berlaku_sejak` terbesar yang tidak melewati `pada`;
    bila ada beberapa pencatatan untuk tanggal berlaku yang sama, yang terakhir dicatat menang
    (`v_parameter_bursa_terkini`). Bila entri terpilih bertanda `aktif = false`, parameter
    dianggap **sengaja dinonaktifkan** sejak tanggal itu — bukan jatuh kembali ke entri lama.
    """
    if nama not in SPESIFIKASI:
        raise GalatKonfigurasi(
            f"parameter '{nama}' tidak dikenal; yang dikenal: {sorted(SPESIFIKASI)}"
        )
    tanggal = pada if pada is not None else date.today()
    baris = sambungan.execute(
        "SELECT * FROM v_parameter_bursa_terkini"
        " WHERE nama = ? AND kelompok = ? AND berlaku_sejak <= ?"
        " ORDER BY berlaku_sejak DESC LIMIT 1",
        (nama, kelompok, tanggal.isoformat()),
    ).fetchone()

    label = f"{nama} [{kelompok}]" if kelompok else nama
    if baris is None:
        return StatusParameter(
            nama=nama,
            kelompok=kelompok,
            keadaan=BELUM_TERVERIFIKASI,
            entri=None,
            alasan=(
                f"parameter {label} belum terverifikasi: tidak ada entri dengan berlaku_sejak "
                f"<= {tanggal.isoformat()}. Isi dari pengumuman resmi di berkas parameter, lalu "
                "muat ulang; sampai itu, fitur yang bergantung padanya menolak menghitung."
            ),
        )

    entri = _entri_dari_baris(sambungan, baris)
    if not entri.aktif:
        return StatusParameter(
            nama=nama,
            kelompok=kelompok,
            keadaan=NONAKTIF,
            entri=entri,
            alasan=(
                f"parameter {label} sengaja dinonaktifkan: entri berlaku "
                f"{entri.berlaku_sejak.isoformat()} (dicatat {entri.dicatat_pada.isoformat()}) "
                f"bertanda aktif = false. Sumber: {entri.sumber}"
            ),
        )
    return StatusParameter(
        nama=nama,
        kelompok=kelompok,
        keadaan=DIPAKAI,
        entri=entri,
        alasan=(
            f"parameter {label} dipakai dari entri berlaku {entri.berlaku_sejak.isoformat()} "
            f"(dicatat {entri.dicatat_pada.isoformat()}). Sumber: {entri.sumber}"
        ),
    )


def ringkasan_status(
    sambungan: sqlite3.Connection, pada: date | None = None
) -> tuple[StatusParameter, ...]:
    """Keadaan seluruh parameter yang dikenal, untuk laporan mode kepala dan jendela."""
    hasil: list[StatusParameter] = []
    for spesifikasi in _SPESIFIKASI_URUT:
        if spesifikasi.kunci_kelompok is None:
            hasil.append(nilai_efektif(sambungan, spesifikasi.nama, "", pada))
            continue
        kelompok = [
            baris["kelompok"]
            for baris in sambungan.execute(
                "SELECT DISTINCT kelompok FROM parameter_bursa WHERE nama = ? ORDER BY kelompok",
                (spesifikasi.nama,),
            )
        ]
        if not kelompok:
            hasil.append(nilai_efektif(sambungan, spesifikasi.nama, "", pada))
        else:
            hasil.extend(nilai_efektif(sambungan, spesifikasi.nama, satu, pada) for satu in kelompok)
    return tuple(hasil)
