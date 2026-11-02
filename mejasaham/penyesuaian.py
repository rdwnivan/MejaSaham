"""Penyesuaian harga aksi korporasi **saat dibaca** (PRD 7.2, T5) — dan penjaga K8/C10.

Berkas ini menjawab satu pertanyaan yang tampak sederhana: "harga ini, dibandingkan harga
setahun lalu, sudah sebanding belum?" Jawabannya tidak bisa disimpan sekali untuk selamanya,
karena arti sebuah baris harga bergantung pada aksi korporasi yang **sudah diketahui** saat
membacanya (PRD 7.2), dan pada apa yang **sudah dilakukan sumber** terhadap baris itu (K8).

Tiga aturan yang ditegakkan di sini:

1. **Split dan reverse split disesuaikan dengan rasio, bukan dengan angka tebakan.** Konvensi
   `skema.py`: harga sebelum tanggal aksi dikali `(rasio_lama / rasio_baru)`. Perkaliannya
   memakai `Fraction`, bukan `float`, supaya hasilnya **tepat** — angka ini nanti dipakai
   menghitung lembar dan stop, dan galat pembulatan di situ menjadi uang yang salah.
2. **Yang sudah dilakukan sumber tidak diulang.** Baris bertanda `split`/`split_dividen`
   dilewati (K8/C10). Tanpa aturan ini, harga Yahoo atas BBCA akan dibagi 5 dua kali dan
   momentumnya salah tanpa satu pun tanda di layar. **Penanda itu hanya mencakup split yang
   tanggalnya tidak sesudah tanggal baris itu diketahui** (P42 c): sumber tidak bisa sudah
   menerapkan split yang belum terjadi saat diunduh. Split sesudahnya tetap diterapkan — inilah
   yang membuat riwayat yang tidak diunduh ulang lagi (deret sambungan IDX) tetap sebanding.
3. **Yang belum dinyatakan tidak ditebak.** Baris tanpa penanda yang punya split relevan
   membuat metrik harganya berstatus "tidak dihitung" beserta alasannya — bukan dipilih salah
   satu diam-diam (aturan keras 2, PRD 7.2).

**Right issue belum diterapkan, dan itu disengaja.** Menyesuaikan right issue menuntut harga
teoretis ex-rights, yang bergantung pada harga pasar saat itu — bukan sekadar rasio. PRD 9.3
memang menyebutnya, tetapi rumusnya tidak ditetapkan PRD dan berkas impor belum tentu memuat
harga tebus yang benar. Selama itu belum ada, emiten yang punya right issue dalam jendela
metriknya berstatus "tidak dihitung" dengan alasan yang menyebut sebabnya — bukan dihitung
dengan rumus karangan.

**Batasan yang perlu diketahui (dan dicatat di `docs/arsitektur.md`).** Karena sumber sudah
menyesuaikan split, deret harga yang tersimpan untuk snapshot lama ikut memakai basis pascasplit
yang diketahui **hari ini**. Untuk imbal hasil (momentum, volatilitas) itu tidak mengubah apa
pun — seluruh deret diskalakan seragam. Yang bisa terpengaruh adalah besaran yang menyandingkan
harga dengan jumlah saham (kapitalisasi, EV/EBITDA), dan itu ditangani dengan mengambil
`jumlah_saham` **pada saat snapshot** dari tabel `emiten` yang append-only.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction

from mejasaham.ingesti import (
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_SPLIT_DIVIDEN,
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    AksiKorporasi,
    HargaHarian,
)

#: Jenis aksi korporasi yang menyesuaikan harga (U4). Dividen **tidak** termasuk: ia masuk arus
#: kas posisi dan imbal hasil dividen, bukan pengubah harga historis.
JENIS_PENYESUAIAN = ("split", "reverse_split", "right_issue")

#: Penanda sumber yang berarti "split sudah diterapkan sumber" (K8/C10).
SUDAH_DITERAPKAN_SUMBER = (PENYESUAIAN_SPLIT, PENYESUAIAN_SPLIT_DIVIDEN)

#: Aksi yang bentuknya belum bisa diterapkan dengan jujur (lihat docstring modul).
JENIS_BELUM_DITERAPKAN = ("right_issue",)


@dataclass(frozen=True)
class BarDisesuaikan:
    """Satu bar harga setelah penyesuaian. Harga sebagai `Fraction` supaya tepat (T8).

    `volume` dan `nilai` **tidak** disesuaikan: nilai transaksi (harga x volume) invarian
    terhadap split, jadi menyesuaikannya justru merusak ADTV20 (U6).
    """

    tanggal: date
    open: Fraction | None
    high: Fraction | None
    low: Fraction | None
    close: Fraction | None
    volume: int | None
    nilai: int | None


@dataclass(frozen=True)
class HasilPenyesuaian:
    """Deret harga siap pakai beserta jejak apa yang dipakai dan apa yang tidak bisa diputuskan."""

    bar: tuple[BarDisesuaikan, ...]
    aksi_diterapkan: tuple[AksiKorporasi, ...] = ()
    aksi_dilewati: tuple[AksiKorporasi, ...] = ()
    aksi_belum_diterapkan: tuple[AksiKorporasi, ...] = ()
    tanggal_tak_diketahui: tuple[date, ...] = ()
    alasan_tak_dihitung: str | None = None

    @property
    def siap(self) -> bool:
        """True bila metrik harga boleh dihitung dari deret ini."""
        return self.alasan_tak_dihitung is None


def _faktor(aksi: AksiKorporasi) -> Fraction:
    """Faktor pengali harga **sebelum** tanggal aksi (konvensi `skema.py`).

    split 1:2 (rasio_lama=1, rasio_baru=2) → 1/2: harga sebelum split dibagi dua.
    """
    if aksi.rasio_lama is None or aksi.rasio_baru is None:
        raise ValueError(f"aksi {aksi.jenis} {aksi.kode} {aksi.tanggal} tanpa rasio")
    return Fraction(aksi.rasio_lama, aksi.rasio_baru)


def aksi_relevan(
    aksi: Iterable[AksiKorporasi], *, batas_tanggal: date | None = None
) -> tuple[AksiKorporasi, ...]:
    """Aksi yang menyesuaikan harga dan sudah terjadi pada (atau sebelum) `batas_tanggal`.

    Aksi setelah tanggal snapshot **tidak** dipakai: memakainya berarti menghitung dengan hal
    yang belum diketahui saat itu (PRD 7.2, semangat AC-15).
    """
    terpilih = [
        satu
        for satu in aksi
        if satu.jenis in JENIS_PENYESUAIAN
        and (batas_tanggal is None or satu.tanggal <= batas_tanggal)
    ]
    return tuple(sorted(terpilih, key=lambda satu: satu.tanggal))


def sesuaikan(
    baris: Sequence[HargaHarian],
    aksi: Iterable[AksiKorporasi] = (),
    *,
    batas_tanggal: date | None = None,
) -> HasilPenyesuaian:
    """Hasilkan deret harga yang sebanding, atau alasan mengapa tidak bisa.

    `baris` boleh datang dalam urutan apa pun; keluarannya selalu urut tanggal menaik.
    """
    bar_urut = sorted(baris, key=lambda satu: satu.tanggal)
    relevan = aksi_relevan(aksi, batas_tanggal=batas_tanggal)

    belum = tuple(satu for satu in relevan if satu.jenis in JENIS_BELUM_DITERAPKAN)
    dipakai = tuple(satu for satu in relevan if satu.jenis not in JENIS_BELUM_DITERAPKAN)

    tak_diketahui: list[date] = []
    tanpa_waktu: list[date] = []
    diterapkan: list[AksiKorporasi] = []
    dilewati: list[AksiKorporasi] = []
    hasil: list[BarDisesuaikan] = []
    for satu in bar_urut:
        penanda = satu.penyesuaian_sumber
        faktor = Fraction(1)
        # Aksi yang tanggalnya SETELAH bar ini yang mengubah harga bar ini (harga sebelum aksi
        # harus dibawa ke basis sesudahnya).
        for tindakan in dipakai:
            if tindakan.tanggal <= satu.tanggal:
                continue
            if penanda in SUDAH_DITERAPKAN_SUMBER:
                diunduh = _tanggal_diketahui(satu)
                if diunduh is None:
                    # Tanpa waktu unduh, "split mana yang sudah diterapkan sumber" tidak bisa
                    # dijawab; menganggap semua atau tidak satu pun sama-sama tebakan.
                    if satu.tanggal not in tanpa_waktu:
                        tanpa_waktu.append(satu.tanggal)
                    continue
                if tindakan.tanggal <= diunduh:
                    # Sumber melaporkan split dalam unduhan yang sama dengan harganya, jadi split
                    # pada hari unduhan sudah ada di angkanya.
                    if tindakan not in dilewati:
                        dilewati.append(tindakan)
                    continue
                faktor *= _faktor(tindakan)
                if tindakan not in diterapkan:
                    diterapkan.append(tindakan)
                continue
            if penanda not in (PENYESUAIAN_TIDAK_DISESUAIKAN,):
                # Belum dinyatakan (`None`) **atau** nilainya tidak dikenal: satu-satunya
                # jawaban jujur adalah mengatakannya. Nilai tak dikenal tidak diperlakukan
                # sebagai "tidak disesuaikan" — itu akan menjadi tebakan yang kebetulan
                # menguntungkan salah satu tafsir (aturan keras 2).
                if satu.tanggal not in tak_diketahui:
                    tak_diketahui.append(satu.tanggal)
                continue
            faktor *= _faktor(tindakan)
            if tindakan not in diterapkan:
                diterapkan.append(tindakan)

        hasil.append(
            BarDisesuaikan(
                tanggal=satu.tanggal,
                open=_kali(satu.open, faktor),
                high=_kali(satu.high, faktor),
                low=_kali(satu.low, faktor),
                close=_kali(satu.close, faktor),
                volume=satu.volume,
                nilai=satu.nilai,
            )
        )

    return HasilPenyesuaian(
        bar=tuple(hasil),
        aksi_diterapkan=tuple(diterapkan),
        aksi_dilewati=tuple(dilewati),
        aksi_belum_diterapkan=belum,
        tanggal_tak_diketahui=tuple(sorted({*tak_diketahui, *tanpa_waktu})),
        alasan_tak_dihitung=_alasan(
            tak_diketahui=tak_diketahui, tanpa_waktu=tanpa_waktu, belum=belum
        ),
    )


def _tanggal_diketahui(bar: HargaHarian) -> date | None:
    """Tanggal (zona waktu yang tersimpan) baris itu diketahui; `None` bila tidak dibawa."""
    if not bar.diketahui_pada:
        return None
    return datetime.fromisoformat(bar.diketahui_pada).date()


def _kali(nilai: int | None, faktor: Fraction) -> Fraction | None:
    return None if nilai is None else Fraction(nilai) * faktor


def _alasan(
    *,
    tak_diketahui: Sequence[date],
    tanpa_waktu: Sequence[date],
    belum: Sequence[AksiKorporasi],
) -> str | None:
    """Alasan "tidak dihitung" yang menyebut sebabnya, bukan sekadar gagal diam-diam."""
    if belum:
        daftar = ", ".join(f"{satu.jenis} {satu.tanggal}" for satu in belum[:3])
        return (
            f"penyesuaian {daftar} belum diterapkan: right issue menuntut harga teoretis "
            "ex-rights yang belum ada datanya"
        )
    if tak_diketahui:
        contoh = ", ".join(tanggal.isoformat() for tanggal in tak_diketahui[:3])
        return (
            "kolom penyesuaian_sumber belum dinyatakan pada "
            f"{len(tak_diketahui)} baris ({contoh}) padahal emiten ini punya split dalam "
            "jendela metriknya; tanpa penanda itu, harga bisa disesuaikan dua kali (K8/C10)"
        )
    if tanpa_waktu:
        contoh = ", ".join(tanggal.isoformat() for tanggal in tanpa_waktu[:3])
        return (
            "diketahui_pada tidak dibawa pada "
            f"{len(tanpa_waktu)} baris berpenanda sudah disesuaikan sumber ({contoh}) padahal "
            "emiten ini punya split sesudahnya; tanpa waktu unduh, tidak bisa dibedakan split "
            "mana yang sudah diterapkan sumber (P42 c)"
        )
    return None


def faktor_lembar(aksi: Iterable[AksiKorporasi], *, sesudah: date) -> Fraction:
    """Pengali jumlah **lembar** untuk split/reverse split yang tanggalnya **setelah** `sesudah`.

    Dipakai kalkulator risiko (Tahap 2), penyesuaian stop, dan penyesuaian transaksi posisi: pada
    split 1:2, satu lembar lama menjadi dua lembar baru, sehingga lembar lama dikali 2. Harga
    dikali 1/2 — hasil kalinya (nilai posisi) tetap, dan itulah yang membuat AC-18 bisa diuji.

    **Arti `sesudah` adalah "kapan angka itu dinyatakan"**, bukan sekadar pembanding tanggal.
    Dua pemakaian nyata di F11:

    * **transaksi** (lembar yang dibeli) — `sesudah = tanggal eksekusinya`. Eksekusi sebelum split
      berada dalam basis lama, jadi lembarnya dikali faktor; eksekusi pada atau sesudah tanggal
      split sudah dalam basis baru. Yang menentukan adalah **tanggal berlakunya** aksi (ex-date),
      dan itu memang tanggal yang disimpan `aksi_korporasi`: pada tanggal itulah harga mulai
      diperdagangkan dalam basis baru.
    * **stop** (`posisi.tgl_stop`) — `sesudah = tanggal basis level stop itu dinyatakan`. Level
      stop adalah angka yang dicatat manusia, dan artinya bergantung pada harga yang ia lihat saat
      mencatatnya. Faktor untuk **harga** adalah kebalikannya: `1 / faktor_lembar(...)`.

    **Right issue sengaja tidak ikut dihitung.** Pemegang right issue menerima lembar baru
    sekaligus membayar harga tebus, sehingga "nilai posisi tetap" tidak berlaku dan rasio saja
    menyesatkan. Selama harganya sendiri belum bisa disesuaikan dengan jujur, lembar pun tidak
    dikira-kira di sini.
    """
    faktor = Fraction(1)
    for satu in aksi_relevan(aksi):
        if satu.jenis in JENIS_BELUM_DITERAPKAN or satu.tanggal <= sesudah:
            continue
        faktor *= 1 / _faktor(satu)
    return faktor
