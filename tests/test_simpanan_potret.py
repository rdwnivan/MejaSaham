"""Uji simpanan potret dasbor web (T99) — `mejasaham/web/simpanan.py`.

Satu potret + metrik seluruh emiten makan ±28 dtk di data kerja, dan hasilnya fungsi
deterministik dari satu snapshot (`potret.muat` hanya membaca baris yang diketahui sampai
`batas_diketahui`, K61). Yang diuji di sini adalah syarat pakai ulangnya:

* snapshot yang sama → tidak dimuat ulang;
* snapshot baru → dimuat ulang;
* nomor snapshot sama tetapi `batas_diketahui` lain (basis data dipulihkan lalu snapshot dibuat
  ulang) → dimuat ulang, bukan memakai isi basis data lama;
* muat yang gagal tidak disimpan.
"""

from __future__ import annotations

import sqlite3

import pytest

from mejasaham import metrik, potret
from mejasaham.web import simpanan


class _Palsu:
    """Pengganti `potret.muat`/`metrik_semua` yang mencatat pemanggilannya."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.kepala: dict[str, object] = {
            "id_snapshot": 24,
            "batas_diketahui": "2026-10-29T19:00:45+07:00",
            "versi_skema": 30,
        }
        self.dimuat: list[int] = []
        self.gagal = False
        monkeypatch.setattr(potret, "snapshot_terakhir", lambda _s: dict(self.kepala))
        monkeypatch.setattr(potret, "muat", self._muat)
        monkeypatch.setattr(metrik, "metrik_semua", lambda bahan: {"AAAA": {"x": bahan}})

    def _muat(self, _s: sqlite3.Connection, id_snapshot: int | None = None) -> object:
        if self.gagal:
            raise RuntimeError("basis data rusak")
        assert id_snapshot == self.kepala["id_snapshot"], "nomor snapshot harus disebut eksplisit"
        self.dimuat.append(id_snapshot)
        return (id_snapshot, self.kepala["batas_diketahui"])


def test_snapshot_yang_sama_tidak_dimuat_ulang(monkeypatch: pytest.MonkeyPatch) -> None:
    palsu = _Palsu(monkeypatch)
    isi = simpanan.SimpananPotret()
    pertama = isi.ambil(None)  # type: ignore[arg-type]
    kedua = isi.ambil(None)  # type: ignore[arg-type]
    assert palsu.dimuat == [24]
    assert kedua.bahan is pertama.bahan and kedua.angka is pertama.angka
    assert kedua.angka["AAAA"]["x"] is pertama.bahan, "metrik dihitung dari potret yang sama"


def test_snapshot_baru_dimuat_ulang(monkeypatch: pytest.MonkeyPatch) -> None:
    palsu = _Palsu(monkeypatch)
    isi = simpanan.SimpananPotret()
    isi.ambil(None)  # type: ignore[arg-type]
    palsu.kepala["id_snapshot"] = 25
    assert isi.ambil(None).bahan == (25, palsu.kepala["batas_diketahui"])  # type: ignore[arg-type]
    assert palsu.dimuat == [24, 25]


def test_nomor_sama_dengan_batas_lain_dimuat_ulang(monkeypatch: pytest.MonkeyPatch) -> None:
    """`--pulihkan` lalu `--refresh` bisa membuat ulang snapshot #24 dengan isi lain."""
    palsu = _Palsu(monkeypatch)
    isi = simpanan.SimpananPotret()
    isi.ambil(None)  # type: ignore[arg-type]
    palsu.kepala["batas_diketahui"] = "2026-10-30T18:00:00+07:00"
    isi.ambil(None)  # type: ignore[arg-type]
    assert palsu.dimuat == [24, 24]


def test_muat_yang_gagal_tidak_disimpan(monkeypatch: pytest.MonkeyPatch) -> None:
    palsu = _Palsu(monkeypatch)
    isi = simpanan.SimpananPotret()
    palsu.gagal = True
    with pytest.raises(RuntimeError, match="rusak"):
        isi.ambil(None)  # type: ignore[arg-type]
    palsu.gagal = False
    isi.ambil(None)  # type: ignore[arg-type]
    assert palsu.dimuat == [24]


def test_metrik_tersimpan_tidak_bisa_diubah_pemakainya(monkeypatch: pytest.MonkeyPatch) -> None:
    _Palsu(monkeypatch)
    angka = simpanan.SimpananPotret().ambil(None).angka  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        angka["BBBB"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        angka["AAAA"]["y"] = None  # type: ignore[index]
