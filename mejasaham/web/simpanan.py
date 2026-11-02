"""Potret + metrik snapshot terakhir, dipakai ulang antar-permintaan dasbor web (T99).

Detail emiten dan screener sama-sama butuh potret snapshot terakhir dan metrik seluruh emiten
(statistik sektor dihitung dari seluruh semesta likuid, PRD 9.5). Atas data kerja keduanya
±28 dtk (±1 juta bar harga), dibayar ulang setiap kode dibuka.

Mengapa memakai ulang itu sah: `potret.muat` hanya membaca baris yang **sudah diketahui** pada
`batas_diketahui` snapshot, termasuk sambungan harga K97 dan kalender — sifat yang sama yang
membuat konteks pasar boleh disimpan (K61). Koreksi yang dicatat sesudahnya tidak termasuk
snapshot itu, jadi tidak ada yang "basi".

Syarat pakainya bagian dari kunci, dibaca ulang dari baris `snapshot` setiap kali:
`id_snapshot` (snapshot baru → muat ulang) **dan** `batas_diketahui` + `versi_skema` (basis data
dipulihkan lalu snapshot dengan nomor sama dibuat ulang → muat ulang, bukan isi lama).

Yang **tidak** dilakukan: menyimpan lebih dari satu snapshot (memori ±1 juta bar), atau melayani
`--sumber` lain — yang disimpan hanya pilihan harga bawaan snapshot itu.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from mejasaham import metrik, potret
from mejasaham.metrik import Nilai


@dataclass(frozen=True)
class IsiPotret:
    bahan: potret.Potret
    #: Hanya-baca: dipakai bersama banyak pekerjaan, jadi satu pemakai tidak boleh mengubahnya.
    angka: Mapping[str, Mapping[str, Nilai]]


class SimpananPotret:
    """Satu potret + metriknya per instans `Aplikasi` (bukan global: tiap server punya basisnya)."""

    def __init__(self) -> None:
        self._kunci: Hashable | None = None
        self._isi: IsiPotret | None = None
        # Dipegang selama memuat: pekerjaan kedua menunggu lalu memakai hasilnya, bukan ikut
        # memuat ±28 dtk yang sama.
        self._kunci_utas = threading.Lock()

    def ambil(self, sambungan: sqlite3.Connection) -> IsiPotret:
        kepala = potret.snapshot_terakhir(sambungan)
        kunci = (kepala["id_snapshot"], kepala["batas_diketahui"], kepala["versi_skema"])
        with self._kunci_utas:
            if self._isi is None or self._kunci != kunci:
                # Nomor snapshot disebut eksplisit: snapshot yang dibuat di antara dua kueri ini
                # tidak boleh tersimpan di bawah kunci snapshot sebelumnya.
                bahan = potret.muat(sambungan, kepala["id_snapshot"])
                angka = metrik.metrik_semua(bahan)
                self._isi = IsiPotret(
                    bahan=bahan,
                    angka=MappingProxyType(
                        {kode: MappingProxyType(dict(isi)) for kode, isi in angka.items()}
                    ),
                )
                self._kunci = kunci
            return self._isi
