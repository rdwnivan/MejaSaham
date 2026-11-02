"""Pekerjaan latar dasbor web — pengganti `ui/pekerja.py` tanpa Qt.

Hitungan layar bisa lama (dasbor atas basis data kerja ±231 MB terukur ±64 dtk, 17 Okt 2026),
jadi permintaan HTTP tidak menunggunya: pekerjaan dijalankan di utas latar, halaman menampilkan
"sedang menghitung" dan memuat ulang dirinya sampai hasilnya ada.

Tiap pekerjaan diberi **kunci** dari isiannya (mis. `("saring", id_preset)`), sehingga memuat
ulang halaman tidak memulai hitungan kedua, dan hasil yang sudah jadi dipakai lagi sampai
pengguna menekan "Muat ulang".

Gagal itu berisik (aturan keras 7): galat ditangkap hanya untuk **dilaporkan** — pesannya tampil
di halaman, dan galat yang tidak terduga juga mencetak jejak penuhnya ke `stderr` serta ke
`log/web.log` di folder data.
"""

from __future__ import annotations

import sys
import threading
import time
import traceback
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

#: Batas jumlah hasil yang disimpan; yang paling lama selesai dibuang lebih dulu.
BATAS_HASIL = 32


def galat_terduga(galat: BaseException) -> bool:
    """Galat yang sudah punya pesan untuk manusia (`Galat*` dari paket inti).

    Galat seperti itu cukup ditampilkan pesannya — mis. "kode belum punya tesis" dari
    `kandidat.GalatKandidat`. Galat lain berarti cacat, dan jejaknya wajib ikut tampil.
    """
    return any(
        kelas.__name__.startswith("Galat") and kelas.__module__.startswith("mejasaham")
        for kelas in type(galat).__mro__
    )


@dataclass
class Pekerjaan:
    """Satu hitungan latar dan keadaannya."""

    kunci: Hashable
    mulai: float = field(default_factory=time.monotonic)
    selesai_pada: float | None = None
    hasil: Any = None
    #: Pesan galat untuk halaman; `None` selama belum gagal.
    galat: str | None = None
    #: Jejak lengkap untuk galat yang tidak terduga; `None` untuk galat terduga.
    jejak: str | None = None
    #: Dilupakan selagi berjalan: hasilnya dihitung dari keadaan sebelum penulisan yang
    #: memicu `lupakan`, jadi dibuang begitu selesai alih-alih disimpan sebagai cache.
    basi: bool = False

    @property
    def berjalan(self) -> bool:
        return self.selesai_pada is None

    @property
    def lama_detik(self) -> float:
        akhir = self.selesai_pada if self.selesai_pada is not None else time.monotonic()
        return akhir - self.mulai


class DaftarPekerjaan:
    """Kumpulan pekerjaan latar, aman dipakai bersamaan oleh banyak utas permintaan."""

    def __init__(self, berkas_log: Callable[[], Path] | None = None) -> None:
        self._kunci = threading.Lock()
        self._isi: dict[Hashable, Pekerjaan] = {}
        self._berkas_log = berkas_log

    def ambil(self, kunci: Hashable) -> Pekerjaan | None:
        with self._kunci:
            return self._isi.get(kunci)

    def mulai(
        self, kunci: Hashable, tugas: Callable[[], Any], *, ulang: bool = False
    ) -> Pekerjaan:
        """Mulai `tugas` di utas latar, kecuali pekerjaan berkunci sama sudah ada.

        `ulang=True` membuang hasil lama dan menghitung lagi — tetapi **tidak** memulai hitungan
        kedua bila yang lama masih berjalan.
        """
        with self._kunci:
            lama = self._isi.get(kunci)
            if lama is not None and (lama.berjalan or not ulang):
                return lama
            pekerjaan = Pekerjaan(kunci=kunci)
            self._isi[kunci] = pekerjaan
            self._pangkas()
        utas = threading.Thread(
            target=self._jalankan, args=(pekerjaan, tugas), name=f"web-{kunci!r}", daemon=True
        )
        utas.start()
        return pekerjaan

    def lupakan(self, awalan: str) -> None:
        """Buang hasil berawalan `awalan` (mis. sesudah saringan disimpan).

        Yang masih berjalan tidak dihentikan — halaman yang menunggunya tetap mendapat jawaban
        dan tidak ada hitungan kedua yang berjalan bersamaan — tetapi ditandai basi, sehingga
        dibuang begitu selesai. Tanpa itu, hitungan yang mulai sebelum penulisan menjadi cache
        yang menampilkan keadaan lama sampai pengguna menekan "Muat ulang".
        """
        with self._kunci:
            for kunci, pekerjaan in list(self._isi.items()):
                if not (isinstance(kunci, tuple) and kunci and kunci[0] == awalan):
                    continue
                if pekerjaan.berjalan:
                    pekerjaan.basi = True
                else:
                    del self._isi[kunci]

    def tunggu(self, kunci: Hashable, batas_detik: float = 120.0) -> Pekerjaan | None:
        """Tunggu sampai pekerjaan selesai (dipakai uji); `None` bila tidak ada."""
        batas = time.monotonic() + batas_detik
        while time.monotonic() < batas:
            pekerjaan = self.ambil(kunci)
            if pekerjaan is None or not pekerjaan.berjalan:
                return pekerjaan
            time.sleep(0.05)
        raise TimeoutError(f"pekerjaan {kunci!r} belum selesai setelah {batas_detik} dtk")

    # -- dalam -------------------------------------------------------------------------

    def _pangkas(self) -> None:
        selesai = sorted(
            (p for p in self._isi.values() if not p.berjalan),
            key=lambda p: p.selesai_pada or 0.0,
        )
        while len(self._isi) > BATAS_HASIL and selesai:
            del self._isi[selesai.pop(0).kunci]

    def _jalankan(self, pekerjaan: Pekerjaan, tugas: Callable[[], Any]) -> None:
        try:
            hasil = tugas()
        except Exception as galat:  # noqa: BLE001 — dilaporkan, bukan ditelan (lihat docstring)
            pekerjaan.galat = f"{type(galat).__name__}: {galat}"
            if not galat_terduga(galat):
                pekerjaan.jejak = traceback.format_exc()
                self._catat(pekerjaan)
        else:
            pekerjaan.hasil = hasil
        finally:
            with self._kunci:
                pekerjaan.selesai_pada = time.monotonic()
                if pekerjaan.basi and self._isi.get(pekerjaan.kunci) is pekerjaan:
                    del self._isi[pekerjaan.kunci]

    def _catat(self, pekerjaan: Pekerjaan) -> None:
        teks = f"[{datetime.now().isoformat(timespec='seconds')}] {pekerjaan.kunci!r}\n{pekerjaan.jejak}"
        print(teks, file=sys.stderr)
        if self._berkas_log is None:
            return
        try:
            berkas = self._berkas_log()
            berkas.parent.mkdir(parents=True, exist_ok=True)
            with berkas.open("a", encoding="utf-8") as keluaran:
                keluaran.write(teks + "\n")
        except OSError as galat:
            # Log yang tidak bisa ditulis tidak boleh menyembunyikan galat aslinya: jejaknya sudah
            # tampil di halaman dan di stderr, dan kegagalan menulis log ikut disebut di stderr.
            print(f"MejaSaham web: log tidak bisa ditulis — {galat}", file=sys.stderr)
