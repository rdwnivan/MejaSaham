"""Konteks pasar satu snapshot: IHSG, breadth, dan rezim — dihitung sekali, dibaca dua layar.

PRD 11.1 menuntut halaman depan memuat keadaan pasar, dan PRD 8.2 menetapkan cara menghitungnya.
Karena itu **aturannya tidak boleh punya dua salinan**: `metrik.breadth` + `metrik.rezim_pasar`
tetap satu-satunya tempat ambang dan syaratnya hidup, dan modul ini hanya membawa **hasilnya**
beserta syarat sahnya.

Mengapa hasilnya disimpan (K61):

* Konteks pasar adalah fungsi deterministik dari satu snapshot dan satu preset. `potret.muat`
  hanya membaca revisi yang **sudah diketahui** saat snapshot dibuat, jadi menghitung ulang
  untuk snapshot yang sama selalu menghasilkan angka yang sama — membayarnya setiap kali dasbor
  dibuka adalah pekerjaan yang jawabannya sudah ada (terukur 33–61 dtk pada basis data
  999.421 bar, sedangkan dasbor sebelum K58 hanya 2,8 dtk).
* Menyimpannya **tanpa syarat** justru berbahaya: angka milik snapshot atau preset lain akan
  terbaca sebagai keadaan hari ini. Karena itu barisnya berkunci `id_snapshot` + `id_preset` +
  label sumber harga, dan `versi_hitung` ikut diperiksa. Semua syarat itu **bagian dari kunci
  atau dari WHERE**, bukan pencocokan "kira-kira" di Python.
* `catatan` ikut disimpan. Tanpa itu, sebab *"rezim NETRAL karena bahannya belum lengkap"*
  hilang begitu angka dibaca dari simpanan — dan kalimat tanpa sebab terbaca sebagai penilaian
  tentang pasar, padahal artinya penilaian tentang data yang belum diimpor.

Yang **tidak** dilakukan modul ini: menghitung breadth/rezim sendiri. `dari_bahan` hanya
membungkus hasil `metrik` + `potret`; pemanggil (`pengatur.jalankan_saring` dan
`dasbor._konteks_pasar`) tetap memakai jalur yang sama persis.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from mejasaham import db, metrik, potret, tampilan
from mejasaham.ingesti import PenutupanIndeks

#: Versi cara **membaca dan membungkus** konteks pasar. Naikkan bila arti angka yang disimpan
#: berubah — termasuk perubahan pada `metrik.breadth`/`metrik.rezim_pasar` yang mengubah hasil untuk
#: snapshot + preset yang sama (mis. ambang breadth, panjang MA, atau indeks acuan berganti), atau
#: bila `Nilai` breadth berubah bentuk. Baris lama dengan versi lain **tidak dipakai**, sehingga
#: angka lama tidak tampak sebanding dengan angka baru. Pola yang sama dipakai `skor.VERSI_HITUNG`,
#: dan sengaja tidak disamakan dengannya: skor dan konteks pasar berubah karena sebab yang berbeda.
VERSI_HITUNG = "pasar-2"


@dataclass(frozen=True)
class BarisIndeks:
    """Penutupan satu indeks beserta perubahannya terhadap penutupan sebelumnya (PRD 11.1)."""

    indeks: str
    tanggal: date
    penutupan: int
    penutupan_sebelumnya: int | None = None
    #: Tanggal penutupan pembanding. Bukan selalu hari bursa sebelumnya: bar kosong dilewati
    #: (`penutupan_indeks`), jadi tanggalnya disebut supaya selisihnya tidak terbaca harian.
    tanggal_sebelumnya: date | None = None

    @property
    def perubahan(self) -> int | None:
        """Selisih poin terhadap penutupan sebelumnya; `None` bila pembandingnya tidak ada."""
        if self.penutupan_sebelumnya is None:
            return None
        return self.penutupan - self.penutupan_sebelumnya

    @property
    def perubahan_rasio(self) -> float | None:
        """Perubahan relatif (0,0103 = +1,03%); `None` bila tidak dapat dihitung."""
        sebelumnya = self.penutupan_sebelumnya
        if not sebelumnya:
            return None
        perubahan = self.perubahan
        return None if perubahan is None else perubahan / sebelumnya

    def ringkas(self) -> str:
        """`IHSG 6.093 (09 Okt 2026) · +62 (+1,03%) terhadap 08 Okt 2026` — tanda arahnya selalu ikut
        (PRD 11.1), dan tanggal pembandingnya disebut bila diketahui."""
        teks = (
            f"{self.indeks} {tampilan.angka(self.penutupan, 0)} "
            f"({tampilan.tanggal(self.tanggal)})"
        )
        perubahan = self.perubahan
        if perubahan is None:
            return teks + " · perubahan tidak dapat dihitung (penutupan sebelumnya tidak ada)"
        # Poin dan persennya satu kesatuan (`+62 (+1,03%)`), bukan dua bagian terpisah — bentuk
        # yang sama dengan contoh PRD 11.1.
        perubahan_teks = tampilan.bertanda(perubahan, 0)
        rasio = self.perubahan_rasio
        if rasio is not None:
            perubahan_teks += f" ({tampilan.bertanda(rasio * 100, 2)}%)"
        if self.tanggal_sebelumnya is not None:
            perubahan_teks += f" terhadap {tampilan.tanggal(self.tanggal_sebelumnya)}"
        return f"{teks} · {perubahan_teks}"


@dataclass(frozen=True)
class KonteksPasar:
    """Konteks pasar satu snapshot: IHSG, breadth, rezim, preset, dan sebab bila bahannya kurang.

    Presetnya ikut disimpan karena **semesta likuid ikut preset** (ambang ADTV20 hidup di kriteria
    preset, bukan konstanta di kode, K6): angka breadth tanpa presetnya adalah angka yang tidak
    bisa diperiksa ulang. `catatan` hanya terisi bila rezimnya NETRAL **karena datanya kurang** —
    bukan karena pasarnya memang netral.
    """

    pasar: BarisIndeks | None = None
    breadth: metrik.Nilai | None = None
    rezim: str | None = None
    preset: str | None = None
    catatan: str | None = None


def penutupan_indeks(bahan: potret.Potret) -> list[PenutupanIndeks]:
    """Penutupan indeks acuan yang **ada** nilainya, urut tanggal — bahan `metrik.rezim_pasar`.

    Penyaring `close is not None` disengaja dan sama dengan yang dipakai `metrik.rezim_pasar`:
    baris tanpa penutupan bukan penutupan nol, dan menghitungnya sebagai nol akan membuat MA200
    terlihat jatuh.
    """
    return [satu for satu in bahan.indeks.get(metrik.INDEKS_ACUAN, ()) if satu.close is not None]


def baris_indeks(bahan: potret.Potret) -> BarisIndeks | None:
    """Penutupan terakhir indeks acuan beserta pembanding sebelumnya; `None` bila belum ada bar."""
    deret = penutupan_indeks(bahan)
    if not deret:
        return None
    terakhir = deret[-1]
    sebelumnya = deret[-2] if len(deret) > 1 else None
    return BarisIndeks(
        indeks=metrik.INDEKS_ACUAN,
        tanggal=terakhir.tanggal,
        penutupan=int(terakhir.close or 0),
        penutupan_sebelumnya=None if sebelumnya is None else int(sebelumnya.close or 0),
        tanggal_sebelumnya=None if sebelumnya is None else sebelumnya.tanggal,
    )


def sebab_bahan_kurang(bahan: potret.Potret, lebar: metrik.Nilai | None) -> str | None:
    """Sebab rinci bila rezimnya NETRAL **karena bahannya kurang**, bukan karena pasar netral.

    `metrik.rezim_pasar` sudah menyebut alasannya sendiri (`NETRAL (dasar tidak lengkap)`); yang
    ditambahkan di sini adalah **bahan mana** yang kurang, sebab "dasar tidak lengkap" saja tidak
    bisa dikerjakan: yang menambah bar IHSG dan yang mengimpor harga emiten adalah dua tindakan
    berbeda. Jumlah bar dan ambangnya dibaca dari `metrik`, bukan ditulis ulang sebagai angka.
    """
    sebab: list[str] = []
    jumlah = len(penutupan_indeks(bahan))
    if jumlah == 0:
        sebab.append(f"penutupan {metrik.INDEKS_ACUAN} belum ada di basis data")
    elif jumlah < metrik.MA_PANJANG:
        sebab.append(
            f"penutupan {metrik.INDEKS_ACUAN} baru {jumlah} bar, "
            f"MA{metrik.MA_PANJANG} butuh {metrik.MA_PANJANG}"
        )
    if lebar is not None and not lebar.ada:
        sebab.append(f"breadth tidak dihitung ({lebar.alasan})")
    if not sebab:
        return None
    return "rezim pasar NETRAL karena bahannya belum lengkap: " + "; ".join(sebab)


def dari_bahan(
    bahan: potret.Potret,
    breadth: metrik.Nilai,
    rezim: str,
    *,
    preset: str | None,
    catatan: str | None = None,
) -> KonteksPasar:
    """Bungkus hasil `metrik.breadth` + `metrik.rezim_pasar` — tanpa menghitung ulang apa pun."""
    return KonteksPasar(
        pasar=baris_indeks(bahan),
        breadth=breadth,
        rezim=rezim,
        preset=preset,
        catatan=catatan,
    )


def simpan(
    sambungan: sqlite3.Connection,
    konteks: KonteksPasar,
    *,
    id_snapshot: int,
    id_preset: str,
    sumber: str | None,
) -> None:
    """Tulis (atau ganti) konteks satu snapshot+preset+label sumber.

    Ditulis ulang, bukan append-only: ia turunan deterministik, sama seperti `skor` (PRD 8.1),
    bukan data yang direvisi manusia. Yang menjaga kejujurannya adalah kunci lengkapnya dan
    `versi_hitung` — bukan riwayat barisnya.
    """
    if konteks.breadth is None:
        raise ValueError(
            "konteks pasar tanpa breadth tidak bisa disimpan: breadth adalah bagian dari "
            "yang dijanjikan K61 (simpan hasil --saring), dan menyimpannya sebagai NULL akan "
            "membuat pembaca membedakan 'tidak ada hasil' dari 'tidak dihitung' tanpa dasar"
        )
    if konteks.preset is not None and konteks.preset != id_preset:
        raise ValueError(
            f"preset konteks ({konteks.preset!r}) berbeda dari kunci yang akan ditulis "
            f"({id_preset!r}); angka dan kuncinya tidak boleh menunjuk aturan yang berbeda"
        )
    if not (konteks.rezim or "").strip():
        raise ValueError(
            "konteks pasar tanpa rezim tidak bisa disimpan: rezim yang kosong bukan NETRAL, "
            "dan menuliskannya sebagai 'tidak dapat dinilai' akan mengarang hasil"
        )
    lebar = konteks.breadth
    pasar = konteks.pasar
    label = sumber or ""
    with db.tulis(sambungan) as koneksi:
        koneksi.execute(
            "DELETE FROM konteks_pasar"
            " WHERE id_snapshot = ? AND id_preset = ? AND sumber_harga = ?",
            (id_snapshot, id_preset, label),
        )
        koneksi.execute(
            "INSERT INTO konteks_pasar (id_snapshot, id_preset, sumber_harga, versi_hitung,"
            " breadth_nilai, breadth_status, breadth_alasan, breadth_asal, rezim,"
            " indeks, indeks_tanggal, indeks_penutupan, indeks_penutupan_sebelumnya,"
            " indeks_tanggal_sebelumnya, catatan, dihitung_pada)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id_snapshot,
                id_preset,
                label,
                VERSI_HITUNG,
                lebar.nilai,
                lebar.status,
                lebar.alasan,
                lebar.asal,
                konteks.rezim,
                None if pasar is None else pasar.indeks,
                None if pasar is None else pasar.tanggal.isoformat(),
                None if pasar is None else pasar.penutupan,
                None if pasar is None else pasar.penutupan_sebelumnya,
                (
                    None
                    if pasar is None or pasar.tanggal_sebelumnya is None
                    else pasar.tanggal_sebelumnya.isoformat()
                ),
                konteks.catatan,
                db.waktu_iso(),
            ),
        )


def muat(
    sambungan: sqlite3.Connection,
    *,
    id_snapshot: int,
    id_preset: str,
    sumber: str | None,
) -> KonteksPasar | None:
    """Baca konteks yang **masih sah** untuk snapshot+preset+label itu; `None` bila tidak ada.

    `None` berarti pemanggil harus menghitung ulang (atau menyatakan tidak dapat dinilai) —
    bukan berarti "pasarnya tidak ada". Empat syaratnya semua ada di WHERE: snapshot, preset,
    label sumber harga, dan versi cara menghitung.
    """
    baris = sambungan.execute(
        "SELECT * FROM konteks_pasar"
        " WHERE id_snapshot = ? AND id_preset = ? AND sumber_harga = ? AND versi_hitung = ?",
        (id_snapshot, id_preset, sumber or "", VERSI_HITUNG),
    ).fetchone()
    if baris is None:
        return None

    pasar: BarisIndeks | None = None
    if baris["indeks_tanggal"] is not None:
        pasar = BarisIndeks(
            indeks=baris["indeks"],
            tanggal=date.fromisoformat(baris["indeks_tanggal"]),
            penutupan=int(baris["indeks_penutupan"]),
            penutupan_sebelumnya=(
                None
                if baris["indeks_penutupan_sebelumnya"] is None
                else int(baris["indeks_penutupan_sebelumnya"])
            ),
            tanggal_sebelumnya=(
                None
                if baris["indeks_tanggal_sebelumnya"] is None
                else date.fromisoformat(baris["indeks_tanggal_sebelumnya"])
            ),
        )
    lebar = metrik.Nilai(
        # Nama & satuannya milik breadth itu sendiri, bukan data yang bisa berubah per baris:
        # menyimpannya sebagai kolom akan mengundang dua baris yang menyebut satuan berbeda untuk
        # angka yang sama. `breadth_nilai`/`status`/`alasan`/`asal` yang memang bervariasi.
        nama="breadth",
        nilai=baris["breadth_nilai"],
        satuan="rasio",
        status=baris["breadth_status"],
        alasan=baris["breadth_alasan"],
        asal=baris["breadth_asal"],
    )
    return KonteksPasar(
        pasar=pasar,
        breadth=lebar,
        rezim=baris["rezim"],
        preset=baris["id_preset"],
        catatan=baris["catatan"],
    )
