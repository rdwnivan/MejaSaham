"""PDF pengumuman suspensi & UMA IDX yang diunduh pengguna (K99) → baris `notasi-khusus.csv`.

Sejak K96 aplikasi tidak mengambil apa pun dari IDX; pengguna mengunduh pengumumannya sendiri dari
situs IDX. Bentuknya ditetapkan dari contoh nyata (29 Okt 2026): `20261028-UMA_COIN.pdf`,
`20261028-UMA_FILM.pdf`, `20261028-WAS_Suspensi_PTSP.pdf` — **satu pengumuman, satu emiten**, dua
halaman (Inggris lalu Indonesia), dibuat Microsoft Word.

Yang dibaca dari bagian bahasa Indonesia (mulai baris `PENGUMUMAN` sampai `Tembusan:`):

* nomor `Peng-UMA-00352/BEI.WAS/10-2026` atau `Peng-SPT-00222/BEI.WAS/10-2026` — tepat satu;
* kode emiten dalam kurung, mis. `(PTSP)` — tepat satu kode berbeda;
* tanggal tanda tangan, satu baris sendiri `28 Oktober 2026` = tanggal pengumuman;
* suspensi saja: "penghentian sementara perdagangan … pada tanggal 29 Oktober 2026" = tanggal
  berlaku, dan itulah `tanggal_mulai` (K99). UMA mulai pada tanggal pengumuman dan berakhir
  `notasi.UMUR_UMA_HARI` hari kemudian (K35), sama dengan baris dari API lama. Suspensi lanjutan
  sesudah pembukaan cooling-down (K103, PDF SPT asli IDX 2024–2026) tidak memakai "pada tanggal":
  "… di Pasar Reguler dan Pasar Tunai mulai [sesi I | Sesi Pra-Pembukaan] tanggal 3 Juli 2026
  sampai dengan Pengumuman Bursa lebih lanjut" — dicari di teks tanpa spasi karena potongan PDF
  memecah kata ("m ulai"). Kedua bentuk bersama-sama tetap harus memberi tepat satu tanggal.

Pembukaan kembali (UPT, K100) dibentuk dari PDF UPT asli IDX 2024–2026 di
`.uji-data/riset-idx/riwayat-api-pdf/`: nomor `Peng-UPT-…` tepat satu (nomor `Peng-SPT-…` lain adalah
rujukan ke suspensinya), "suspensi … di Pasar Reguler … dibuka kembali mulai [sesi I | Sesi I
Periodic Call Auction] tanggal 25 Juni 2026". Isinya ditulis dengan font CID, jadi teksnya dibaca
lewat peta `/ToUnicode` (`kalender.potongan_teks(terjemahkan_font=True)`). Pembukaan **menutup**
satu suspensi terbuka emiten itu dengan `tanggal_selesai` = sehari sebelum dibuka kembali (hari
terakhir tidak bisa diperdagangkan; `saring` membaca `tanggal_selesai` inklusif).

Bentuk lain — pembukaan sesi II, pembukaan yang tidak menyebut Pasar Reguler (K39), pengumuman
multi-kode, kalimat tanggal yang berbeda — **ditolak dengan sebabnya** sampai ada contoh nyatanya
(bentuk tidak ditebak, K95). Teks PDF dibaca dengan pengurai pustaka standar milik `kalender.py`;
tidak ada dependensi baru (K3).

Kumpulan PDF bukan daftar: PDF yang tidak diunggah tidak berarti peristiwanya tidak ada. Karena itu
gabungannya **hanya menambah** (`HasilNotasi.hanya_menambah`) dan baris dari sini tidak bertanda
penanda pengambilan otomatis, sehingga tidak pernah ditutup oleh penulisan lain. Satu-satunya
baris lama yang berubah adalah suspensi yang **dinyatakan** dibuka oleh PDF UPT
(`HasilNotasi.penutupan`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from mejasaham import kalender, lokasi, notasi, sun, tampilan, unggahan_idx
from mejasaham.ingesti import GalatIngesti

LABEL_UNGGAHAN = "PDF pengumuman IDX (unduhan pengguna dari situs IDX)"

#: Indeks pengumuman resmi IDX yang dibuka **pengguna** untuk mengunduh PDF-nya (K102: tautan
#: pengingat). Bukan alamat yang diambil aplikasi (K96).
ALAMAT_PENGUMUMAN = "https://www.idx.id/id/berita/pengumuman"

#: Penanda di `keterangan` baris dari modul ini. Sengaja **bukan** `notasi.PENANDA_AKTIVITAS`:
#: baris berpenanda itu ditutup oleh pengambilan API lama bila tidak tercantum, padahal tanggal
#: mulai suspensi di sini (tanggal berlaku) berbeda dari tanggal di API (tanggal pengumuman).
PENANDA = "Pengumuman IDX PDF"

#: Nama berkas dari situs IDX (contoh nyata): `20261028-UMA_COIN.pdf`,
#: `20261028-WAS_Suspensi_PTSP.pdf`; peramban menambah " (1)" pada unduhan kedua bernama sama.
#: Nama lain tetap diterima (isinya memuat semua yang dibutuhkan), tetapi nama berbentuk ini
#: wajib cocok dengan isinya.
POLA_NAMA = re.compile(r"(\d{8})-(UMA|WAS_Suspensi)_([A-Z0-9]{4})(?: \(\d+\))?\.pdf", re.IGNORECASE)
POLA_NOMOR = re.compile(r"Peng-([A-Z]+)-(\d{5})/BEI\.([A-Z]+)/(\d{2})-(\d{4})")
POLA_KODE = re.compile(r"\(([A-Z0-9]{4})\)")
POLA_TANGGAL = re.compile(r"(\d{1,2}) ([A-Za-z]+) (\d{4})")
POLA_BERLAKU = re.compile(r"pada tanggal (\d{1,2}) ([A-Za-z]+) (\d{4})")
#: Suspensi lanjutan (K103), dicocokkan pada teks **tanpa spasi**; sesi selain I/pra-pembukaan ditolak.
POLA_BERLAKU_SESI = re.compile(
    r"PasarRegulerdanPasarTunaimulai(Sesi(?:I+|Pra-Pembukaan))tanggal(\d{1,2})([A-Za-z]+)(\d{4})", re.IGNORECASE
)
SESI_BERLAKU = {"sesii", "sesipra-pembukaan"}
#: Nomor pengumuman IDX berformat apa pun — hanya untuk menyebut nomor yang tidak dikenali.
POLA_NOMOR_LONGGAR = re.compile(r"Peng-[A-Za-z0-9]+(?:-\d+)?/BEI\.[A-Za-z0-9]+[-/]\d{2}-\d{4}")
#: Kalimat pembukaan dari contoh UPT; sesi II tidak pernah terlihat, jadi tidak dikenali.
POLA_DIBUKA = re.compile(
    r"dibuka kembali mulai (?:sesi (I+)(?: periodic call auction)? )?tanggal (\d{1,2}) ([A-Za-z]+) (\d{4})",
    re.IGNORECASE,
)

JENIS_PER_NOMOR = {"UMA": "uma", "SPT": "suspensi", "UPT": "suspensi"}
JENIS_PER_NAMA = {"uma": "uma", "was_suspensi": "suspensi"}


class GalatPengumuman(RuntimeError):
    """Kesalahan yang pesannya sudah ditujukan untuk pengguna, bukan traceback (aturan keras 7)."""


@dataclass(frozen=True)
class Pengumuman:
    nama_berkas: str
    nomor: str
    jenis: str
    kode: str
    tanggal_pengumuman: date
    #: Suspensi: hari perdagangannya dihentikan. UMA: sama dengan tanggal pengumuman. Pembukaan:
    #: hari perdagangannya dibuka kembali.
    tanggal_berlaku: date
    #: True = pengumuman pembukaan kembali (UPT): menutup suspensi, bukan menambah baris.
    pembukaan: bool = False
    #: Nomor `Peng-SPT-…` yang dirujuk pengumuman pembukaan (boleh kosong).
    rujukan: tuple[str, ...] = ()

    @property
    def uraian(self) -> str:
        if self.pembukaan:
            return (
                f"{self.kode} suspensi dibuka kembali {tampilan.tanggal(self.tanggal_berlaku)}, diumumkan "
                f"{tampilan.tanggal(self.tanggal_pengumuman)} ({self.nomor})"
            )
        if self.jenis == "uma":
            return f"{self.kode} UMA {tampilan.tanggal(self.tanggal_berlaku)} ({self.nomor})"
        return (
            f"{self.kode} suspensi mulai {tampilan.tanggal(self.tanggal_berlaku)}, diumumkan "
            f"{tampilan.tanggal(self.tanggal_pengumuman)} ({self.nomor})"
        )

    def _keterangan(self) -> str:
        return (
            f"{PENANDA}; {self.nomor}; diumumkan {self.tanggal_pengumuman.isoformat()}; "
            f"berkas '{self.nama_berkas}'"
        )

    def tutup(self, terbuka: notasi.BarisNotasi) -> notasi.BarisNotasi:
        """Baris suspensi `terbuka` yang ditutup pengumuman pembukaan ini."""
        return notasi.BarisNotasi(
            terbuka.kode,
            terbuka.jenis,
            terbuka.tanggal_mulai,
            self.tanggal_berlaku - timedelta(days=1),
            f"{terbuka.keterangan} → dibuka kembali {self.tanggal_berlaku.isoformat()} "
            f"({self._keterangan()})",
        )

    def baris(self) -> notasi.BarisNotasi:
        if self.pembukaan:
            raise ValueError("pengumuman pembukaan menutup baris, bukan membentuk baris baru")
        keterangan = self._keterangan()
        if self.jenis == "uma":
            return notasi.BarisNotasi(
                self.kode,
                "uma",
                self.tanggal_berlaku,
                self.tanggal_berlaku + timedelta(days=notasi.UMUR_UMA_HARI),
                f"{keterangan}; aturan UMA {notasi.UMUR_UMA_HARI} hari",
            )
        return notasi.BarisNotasi(self.kode, "suspensi", self.tanggal_berlaku, None, keterangan)


def _tanggal(cocok: re.Match[str], di_mana: str) -> date:
    hari, bulan, tahun = cocok.groups()
    nomor_bulan = sun.BULAN.get(bulan.lower())
    try:
        return date(int(tahun), nomor_bulan or 0, int(hari))
    except ValueError as galat:
        raise GalatPengumuman(f"{di_mana}: tanggal '{cocok.group()}' tidak sah") from galat


def _satu(nilai: set[str], di_mana: str, apa: str) -> str:
    if len(nilai) != 1:
        rincian = ", ".join(sorted(nilai)) if nilai else "tidak ada"
        raise GalatPengumuman(f"{di_mana}: {apa} harus tepat satu, terbaca {rincian}")
    return next(iter(nilai))


def baca(data: bytes, *, nama_berkas: str, hari_ini: date | None = None) -> Pengumuman:
    """Baca satu PDF pengumuman. Yang tidak dikenali ditolak, bukan dibaca sebagian."""
    di_mana = f"'{nama_berkas}'"
    try:
        potongan, heksa = kalender.potongan_teks(data, di_mana=di_mana, terjemahkan_font=True)
    except GalatIngesti as galat:
        raise GalatPengumuman(str(galat)) from galat
    if heksa:
        # Glif yang tidak terbaca bisa satu angka tanggal; membaca sisanya berarti menebak.
        raise GalatPengumuman(
            f"{di_mana}: {heksa} glif teks tidak bisa diterjemahkan — berkasnya tidak dibaca sebagian"
        )
    baris = [satu.teks for satu in kalender.baris_teks(potongan) if satu.teks]
    # Potongan PDF kadang memecah judulnya ("PENGU MUMAN").
    awal = [nomor for nomor, teks in enumerate(baris) if teks.replace(" ", "") == "PENGUMUMAN"]
    if len(awal) != 1:
        raise GalatPengumuman(
            f"{di_mana}: bagian bahasa Indonesia (baris 'PENGUMUMAN') tidak ditemukan tepat sekali "
            "— bukan PDF pengumuman IDX yang dikenal (beri tahu agen bila ini memang pengumuman)"
        )
    bagian = baris[awal[0] :]
    akhir = next((nomor for nomor, teks in enumerate(bagian) if teks.startswith("Tembusan")), len(bagian))
    bagian = bagian[:akhir]
    teks = " ".join(" ".join(bagian).split())
    # Potongan PDF menyelipkan spasi di dalam token ("Peng-UMA-00 352 /BEI.WAS/ 10-2026", "( FILM )").
    rapat = re.sub(r"\s+", "", teks)

    semua_nomor = {cocok.group() for cocok in POLA_NOMOR.finditer(rapat)}
    nomor_upt = {satu for satu in semua_nomor if POLA_NOMOR.fullmatch(satu).group(1) == "UPT"}
    rujukan: tuple[str, ...] = ()
    if nomor_upt:
        # Pembukaan merujuk suspensinya ("Menunjuk Pengumuman Bursa Peng-SPT-…"); rujukan itu
        # bukan nomor pengumuman ini.
        nomor = _satu(nomor_upt, di_mana, "nomor pengumuman pembukaan (Peng-UPT-…)")
        lain = semua_nomor - nomor_upt
        if any(POLA_NOMOR.fullmatch(satu).group(1) != "SPT" for satu in lain):
            raise GalatPengumuman(f"{di_mana}: {nomor} merujuk nomor selain Peng-SPT ({', '.join(sorted(lain))})")
        rujukan = tuple(sorted(lain))
    elif "dibuka kembali" in teks.lower():
        # Terukur pada satu UPT 30 Des 2024: nomornya terpotong baris kaki halaman.
        raise GalatPengumuman(
            f"{di_mana}: menyebut 'dibuka kembali' tetapi nomor Peng-UPT-… tidak terbaca utuh — "
            "bukan dibaca sebagai pengumuman lain"
        )
    else:
        if not semua_nomor and (lain := sorted({c.group() for c in POLA_NOMOR_LONGGAR.finditer(rapat)})):
            # Terukur pada Papan Akselerasi (BEI.PLP, 2023) dan Pemantauan Khusus (BEI.PP3, 2024):
            # ketentuan atau kabar suspensi yang masih berjalan, bukan awal suspensi.
            raise GalatPengumuman(
                f"{di_mana}: nomor {', '.join(lain)} berformat lain — yang dikenal Peng-UMA/SPT/UPT-nnnnn/"
                "BEI.XXX/mm-yyyy; bentuk lain tidak ditebak artinya"
            )
        nomor = _satu(semua_nomor, di_mana, "nomor pengumuman")
    jenis_nomor = POLA_NOMOR.fullmatch(nomor).group(1)
    jenis = JENIS_PER_NOMOR.get(jenis_nomor)
    if jenis is None:
        raise GalatPengumuman(
            f"{di_mana}: {nomor}: jenis pengumuman '{jenis_nomor}' belum dikenali (yang dikenal: UMA, SPT, UPT)"
        )
    kode_kode = {cocok.group(1) for cocok in POLA_KODE.finditer(rapat)}
    if len(kode_kode) > 1:
        raise GalatPengumuman(
            f"{di_mana}: menyebut lebih dari satu kode emiten ({', '.join(sorted(kode_kode))}); "
            "pengumuman multi-kode dipetakan per emiten dengan tangan (K36–K41), tidak ditebak"
        )
    kode = _satu(kode_kode, di_mana, "kode emiten dalam kurung")

    tanggal_tanda_tangan = {
        _tanggal(cocok, di_mana) for satu in bagian if (cocok := POLA_TANGGAL.fullmatch(satu.strip()))
    }
    if len(tanggal_tanda_tangan) != 1:
        raise GalatPengumuman(
            f"{di_mana}: tanggal pengumuman (baris tanggal sendiri, mis. '28 Oktober 2026') harus "
            f"tepat satu, terbaca {len(tanggal_tanda_tangan)}"
        )
    (diumumkan,) = tanggal_tanda_tangan
    if diumumkan > (hari_ini or date.today()):
        raise GalatPengumuman(f"{di_mana}: tanggal pengumuman {tampilan.tanggal(diumumkan)} sesudah hari ini")

    if jenis_nomor == "UPT":
        if "suspensi" not in teks.lower() or "pasar reguler" not in teks.lower():
            raise GalatPengumuman(
                f"{di_mana}: {nomor} tidak menyebut pembukaan suspensi di Pasar Reguler — pembukaan "
                "di pasar lain saja tidak menutup suspensi (K39)"
            )
        dibuka = list(POLA_DIBUKA.finditer(teks))
        if len(dibuka) != 1:
            raise GalatPengumuman(
                f"{di_mana}: kalimat 'dibuka kembali mulai … tanggal …' harus tepat satu, terbaca "
                f"{len(dibuka)} — kalimat lain tidak ditebak artinya"
            )
        sesi = dibuka[0].group(1)
        if sesi is not None and sesi.upper() != "I":
            raise GalatPengumuman(f"{di_mana}: pembukaan mulai sesi {sesi} belum dikenali (contohnya baru sesi I)")
        berlaku = _tanggal(POLA_TANGGAL.fullmatch(" ".join(dibuka[0].group(2, 3, 4))), di_mana)
        if berlaku <= diumumkan:
            raise GalatPengumuman(f"{di_mana}: pembukaan berlaku tidak sesudah tanggal pengumumannya")
    elif jenis == "suspensi":
        if "penghentian sementara perdagangan" not in teks.lower():
            raise GalatPengumuman(f"{di_mana}: {nomor} tidak menyebut 'penghentian sementara perdagangan'")
        berlaku_berlaku = {_tanggal(cocok, di_mana) for cocok in POLA_BERLAKU.finditer(teks)}
        for cocok in POLA_BERLAKU_SESI.finditer(rapat):
            if cocok.group(1).lower() not in SESI_BERLAKU:
                raise GalatPengumuman(
                    f"{di_mana}: suspensi mulai sesi {cocok.group(1)[4:]} belum dikenali (contohnya baru sesi I "
                    "dan pra-pembukaan)"
                )
            berlaku_berlaku.add(_tanggal(POLA_TANGGAL.fullmatch(" ".join(cocok.group(2, 3, 4))), di_mana))
        if len(berlaku_berlaku) != 1:
            raise GalatPengumuman(
                f"{di_mana}: tanggal berlaku suspensi ('pada tanggal …' atau 'di Pasar Reguler dan Pasar "
                f"Tunai mulai sesi I tanggal …') harus tepat satu, terbaca {len(berlaku_berlaku)} — kalimat "
                "lain tidak ditebak artinya"
            )
        (berlaku,) = berlaku_berlaku
        if berlaku < diumumkan:
            raise GalatPengumuman(f"{di_mana}: suspensi berlaku sebelum diumumkan")
    else:
        if "unusual market activity" not in teks.lower():
            raise GalatPengumuman(f"{di_mana}: {nomor} tidak menyebut 'Unusual Market Activity'")
        berlaku = diumumkan

    nama = POLA_NAMA.fullmatch(nama_berkas)
    if nama is not None:
        dari_nama = (nama.group(1), JENIS_PER_NAMA[nama.group(2).lower()], nama.group(3).upper())
        dari_isi = (f"{diumumkan:%Y%m%d}", jenis, kode)
        if dari_nama != dari_isi:
            raise GalatPengumuman(
                f"{di_mana}: nama berkas ({' / '.join(dari_nama)}) tidak cocok dengan isinya "
                f"({' / '.join(dari_isi)})"
            )
    return Pengumuman(nama_berkas, nomor, jenis, kode, diumumkan, berlaku, jenis_nomor == "UPT", rujukan)


@dataclass(frozen=True)
class HasilPilah:
    baru: tuple[Pengumuman, ...]
    #: Sudah ada barisnya — dari unggahan sebelumnya, atau dari API lama yang memakai tanggal
    #: pengumuman sebagai tanggal mulai (baris bertanggal antara pengumuman dan berlaku).
    sudah_ada: tuple[Pengumuman, ...]
    hasil: notasi.HasilNotasi


def pilah(pengumuman: Sequence[Pengumuman], lama: Sequence[notasi.BarisNotasi]) -> HasilPilah:
    """Pisahkan yang belum tercatat dari yang sudah, dan susun hasil notasi yang hanya menambah."""
    if not pengumuman:
        raise GalatPengumuman("tidak ada PDF pengumuman yang dibaca")
    for kunci, apa in ((lambda p: p.nomor, "nomor"), (lambda p: (p.kode, p.jenis, p.tanggal_berlaku), "peristiwa")):
        terlihat: dict[object, str] = {}
        for satu in pengumuman:
            if kunci(satu) in terlihat:
                raise GalatPengumuman(
                    f"{apa} {satu.nomor} muncul dua kali ('{terlihat[kunci(satu)]}' dan "
                    f"'{satu.nama_berkas}'); pilih satu berkas per pengumuman"
                )
            terlihat[kunci(satu)] = satu.nama_berkas
    baru: list[Pengumuman] = []
    sudah_ada: list[Pengumuman] = []
    # Pembukaan diproses sesudah semua awal suspensi, supaya SPT dan UPT-nya boleh diunggah bersama.
    for satu in sorted(pengumuman, key=lambda p: (p.pembukaan, p.tanggal_berlaku, p.kode, p.jenis)):
        if satu.pembukaan:
            continue
        tercatat = any(
            baris.kode == satu.kode
            and baris.jenis == satu.jenis
            and satu.tanggal_pengumuman <= baris.tanggal_mulai <= satu.tanggal_berlaku
            for baris in lama
        )
        (sudah_ada if tercatat else baru).append(satu)

    baris_baru = {(satu.kode, satu.tanggal_berlaku): satu.baris() for satu in baru if satu.jenis == "suspensi"}
    baris_lain = [satu.baris() for satu in baru if satu.jenis != "suspensi"]
    penutupan: dict[tuple[str, date], notasi.BarisNotasi] = {}
    for satu in sorted((p for p in pengumuman if p.pembukaan), key=lambda p: (p.tanggal_berlaku, p.kode)):
        terakhir_ditangguhkan = satu.tanggal_berlaku - timedelta(days=1)
        kerja = [
            penutupan.get((baris.kode, baris.tanggal_mulai), baris)
            for baris in (*lama, *baris_baru.values())
            if baris.kode == satu.kode and baris.jenis == "suspensi"
        ]
        if any(
            baris.tanggal_selesai is not None
            and baris.tanggal_mulai <= satu.tanggal_pengumuman <= baris.tanggal_selesai <= terakhir_ditangguhkan
            for baris in kerja
            if (baris.kode, baris.tanggal_mulai) not in penutupan
        ):
            # Sudah ditutup — dari unggahan sebelumnya, atau dari API lama yang menutup suspensi
            # pada tanggal pengumuman pembukaannya.
            sudah_ada.append(satu)
            continue
        terbuka = [
            baris for baris in kerja if baris.tanggal_selesai is None and baris.tanggal_mulai <= terakhir_ditangguhkan
        ]
        if len(terbuka) != 1:
            sebab = (
                "tidak ada suspensi terbuka yang dimulai sebelumnya — unggah PDF penghentiannya (SPT) dulu"
                if not terbuka
                else f"{len(terbuka)} suspensi terbuka; mana yang dibuka tidak ditebak"
            )
            raise GalatPengumuman(f"'{satu.nama_berkas}': {satu.uraian}: {sebab}")
        (lawan,) = terbuka
        # Baris dari PDF menyimpan nomor SPT-nya; baris API lama hanya judulnya, jadi tidak dicocokkan.
        nomor_lawan = {cocok.group() for cocok in POLA_NOMOR.finditer(lawan.keterangan)}
        if satu.rujukan and nomor_lawan and nomor_lawan.isdisjoint(satu.rujukan):
            raise GalatPengumuman(
                f"'{satu.nama_berkas}': {satu.uraian} merujuk {', '.join(satu.rujukan)}, sedangkan suspensi "
                f"terbuka {satu.kode} berasal dari {', '.join(sorted(nomor_lawan))}"
            )
        penutupan[(lawan.kode, lawan.tanggal_mulai)] = satu.tutup(lawan)
        baru.append(satu)

    for kunci in [kunci for kunci in penutupan if kunci in baris_baru]:
        # Suspensi dari unggahan yang sama: ditulis langsung dalam keadaan tertutup.
        baris_baru[kunci] = penutupan.pop(kunci)
    return HasilPilah(
        tuple(baru),
        tuple(sudah_ada),
        notasi.HasilNotasi(
            tanggal_data=max(satu.tanggal_pengumuman for satu in pengumuman),
            baris=tuple(sorted((*baris_lain, *baris_baru.values()), key=lambda b: (b.kode, b.jenis, b.tanggal_mulai))),
            sumber=f"{LABEL_UNGGAHAN}, {len(pengumuman)} berkas",
            hanya_menambah=True,
            penutupan=tuple(penutupan.values()),
        ),
    )


def folder_unduhan() -> Path:
    return lokasi.folder_data() / "unduhan-idx" / "pengumuman"


def simpan_unduhan(nama_asli: str, isi: bytes, *, momen: datetime | None = None) -> Path:
    """Simpan PDF unggahan mentah apa adanya (bukti asal baris). Basis data tidak disentuh."""
    if not isi:
        raise GalatPengumuman(f"'{nama_asli}' kosong (0 bait)")
    if len(isi) > unggahan_idx.BATAS_BAIT:
        raise GalatPengumuman(f"'{nama_asli}' berukuran {tampilan.angka(len(isi), 0)} bait — kemungkinan salah pilih")
    waktu = (momen or datetime.now().astimezone()).replace(microsecond=0)
    jalur = lokasi.pastikan_folder(folder_unduhan()) / f"{waktu:%Y%m%dT%H%M%S}_{unggahan_idx.nama_aman(nama_asli)}"
    sementara = jalur.with_name(jalur.name + ".sebagian")
    sementara.write_bytes(isi)
    sementara.replace(jalur)
    return jalur
