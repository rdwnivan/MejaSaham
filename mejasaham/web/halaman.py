"""Potongan HTML dasbor web — teks siap tampil masuk, HTML keluar.

Isinya tidak menghitung apa pun: tabel datang dari `mejasaham.layar.tabel` (kepala/isi yang sama
dengan jendela), teks dari `ringkas()` milik inti. Seluruh teks lewat `html.escape`, jadi nama
emiten atau catatan jurnal yang memuat `<` atau `&` tidak bisa berubah arti menjadi markup.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from html import escape
from urllib.parse import urlencode

JUDUL = "Meja Saham"

#: Menu layar PRD 11, urut sama dengan tab jendela.
MENU: tuple[tuple[str, str], ...] = (
    ("/", "Dasbor"),
    ("/screener", "Screener"),
    ("/emiten", "Detail emiten"),
    ("/risiko", "Kalkulator risiko"),
    ("/jurnal", "Jurnal & kepatuhan"),
    ("/berkas", "Impor & cadangan"),
)

#: Sel yang isinya angka tampilan (`1.234,5`, `-3,2%`, `+0,42`) dirata kanan.
_ANGKA = re.compile(r"^[-+−]?(Rp )?[\d.]+(,\d+)?\s?(%|bp|x|R)?$")

CSS = """
:root{--bg:#f7f7f5;--panel:#fff;--teks:#1d1d1b;--redup:#6b6b66;--garis:#e2e1dc;
--aksen:#1f5f8b;--bahaya:#b00020;--bahaya-bg:#fdecee;--aman:#1b5e20;--aman-bg:#e9f5ea;
--kode-bg:#f1f0ec;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141413;--panel:#1d1d1b;
--teks:#ecebe6;--redup:#a3a29b;--garis:#33322f;--aksen:#7fb6dc;--bahaya:#ff8a95;--bahaya-bg:#3a1a1e;
--aman:#8fd19a;--aman-bg:#18301b;--kode-bg:#252523;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--teks);font:15px/1.5 system-ui,"Segoe UI",sans-serif}
header{background:var(--panel);border-bottom:1px solid var(--garis);padding:0 16px}
.atas{max-width:1240px;margin:0 auto;display:flex;flex-wrap:wrap;align-items:center;gap:4px 20px}
.merek{font-weight:650;padding:12px 0}
nav{display:flex;flex-wrap:wrap;gap:2px}
nav a{color:var(--redup);text-decoration:none;padding:12px 10px;border-bottom:2px solid transparent}
nav a:hover{color:var(--teks)}
nav a.aktif{color:var(--teks);border-bottom-color:var(--aksen)}
main{max-width:1240px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:1.35rem;margin:0 0 12px}
h2{font-size:1.05rem;margin:28px 0 8px}
a{color:var(--aksen)}
.kartu{background:var(--panel);border:1px solid var(--garis);border-radius:8px;padding:14px 16px;margin:0 0 14px}
pre.bungkus{white-space:pre-wrap;overflow-wrap:anywhere}
pre{background:var(--kode-bg);border-radius:6px;padding:12px;overflow:auto;font:13px/1.45 ui-monospace,Consolas,monospace;margin:0;white-space:pre}
.gulir{overflow-x:auto;border:1px solid var(--garis);border-radius:8px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--garis);vertical-align:top}
th{position:sticky;top:0;background:var(--panel);font-weight:600;color:var(--redup);white-space:nowrap}
tr:last-child td{border-bottom:0}
td.angka{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.kosong{color:var(--redup);padding:12px}
.pesan{border-radius:8px;padding:10px 14px;margin:0 0 14px;white-space:pre-wrap}
.galat{background:var(--bahaya-bg);color:var(--bahaya);font-weight:600}
.oke{background:var(--aman-bg);color:var(--aman)}
.info{background:var(--kode-bg)}
.perlu{border-left:4px solid var(--aksen)}
.perlu ul{margin:6px 0 0;padding-left:20px}
form.borang{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:flex-end}
label{display:flex;flex-direction:column;gap:3px;font-size:13px;color:var(--redup)}
label.centang{flex-direction:row;align-items:center;gap:6px;color:var(--teks)}
input,select,button{font:inherit;color:var(--teks);background:var(--panel);border:1px solid var(--garis);border-radius:6px;padding:6px 9px;min-height:36px}
input[type=checkbox]{min-height:0}
button{background:var(--aksen);color:#fff;border-color:var(--aksen);cursor:pointer;padding:6px 14px;white-space:nowrap;flex-shrink:0}
button.kedua,a.tombol-kedua{background:transparent;color:var(--aksen);border:1px solid var(--aksen);border-radius:6px;padding:6px 14px;text-decoration:none;display:inline-block}
.baris-tombol{display:flex;gap:10px;align-items:center;margin-top:12px}
.redup{color:var(--redup);font-size:13px}
details summary{cursor:pointer;color:var(--redup)}
footer{max-width:1240px;margin:0 auto;padding:0 16px 32px;color:var(--redup);font-size:13px}
progress{width:100%;height:14px;accent-color:var(--aksen)}
.memuat{display:flex;gap:10px;align-items:center}
.putar{width:16px;height:16px;border:2px solid var(--garis);border-top-color:var(--aksen);border-radius:50%;animation:putar 1s linear infinite}
@keyframes putar{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.putar{animation:none}}
"""


def e(teks: object) -> str:
    return escape(str(teks), quote=True)


def tautan(jalur: str, **parameter: object) -> str:
    isi = {k: v for k, v in parameter.items() if v not in (None, "", False)}
    return jalur + ("?" + urlencode(isi) if isi else "")


def kerangka(
    judul: str,
    isi: str,
    *,
    aktif: str,
    keterangan: str = "",
    muat_ulang_detik: int | None = None,
) -> str:
    """Satu halaman utuh: kepala, menu, isi, dan pernyataan wajib di kaki (aturan keras 8, K7)."""
    menu = "".join(
        f'<a href="{e(jalur)}"{" class=aktif" if jalur == aktif else ""}>{e(nama)}</a>'
        for jalur, nama in MENU
    )
    segarkan = (
        f'<meta http-equiv="refresh" content="{muat_ulang_detik}">' if muat_ulang_detik else ""
    )
    return (
        "<!doctype html><html lang=id><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        f'{segarkan}<link rel=icon href="/favicon.svg" type="image/svg+xml">'
        f"<title>{e(judul)} · {JUDUL}</title><style>{CSS}</style></head><body>"
        f'<header><div class=atas><div class=merek>{JUDUL}</div><nav>{menu}</nav></div></header>'
        f"<main><h1>{e(judul)}</h1>{isi}</main>"
        f"<footer>{e(keterangan) + '<br>' if keterangan else ''}"
        "Harga dari yfinance berasal dari sumber TIDAK RESMI (K7) — label sumber tiap snapshot "
        "tampil di screener; untuk pemakaian pribadi.<br>"
        "Skor dan peringkat di aplikasi ini bukan nasihat investasi (PRD 9.10).</footer>"
        "</body></html>"
    )


def pesan(teks: str, jenis: str = "info") -> str:
    return f'<div class="pesan {e(jenis)}">{e(teks)}</div>' if teks else ""


def pra(teks: str, *, bungkus: bool = False) -> str:
    """Teks apa adanya. `bungkus=True` untuk kalimat panjang (konfirmasi), bukan tabel rata kolom."""
    return f"<pre{' class=bungkus' if bungkus else ''}>{e(teks)}</pre>"


def kartu(isi: str) -> str:
    return f"<div class=kartu>{isi}</div>"


def tabel(
    kepala: Sequence[str],
    isi: Iterable[Sequence[str]],
    *,
    tautan_kolom: dict[int, str] | None = None,
    kosong: str = "Tidak ada baris.",
) -> str:
    """Tabel dari `layar.tabel`. `tautan_kolom` {indeks: pola} menjadikan sel itu tautan.

    Pola memakai `{nilai}` untuk isi sel yang sudah di-URL-kan, mis. `/emiten?kode={nilai}`.
    """
    tautan_kolom = tautan_kolom or {}
    baris_html: list[str] = []
    for baris in isi:
        sel: list[str] = []
        for i in range(len(kepala)):
            nilai = baris[i] if i < len(baris) else ""
            kelas = " class=angka" if _ANGKA.match(nilai.strip()) else ""
            teks = e(nilai)
            if i in tautan_kolom and nilai.strip():
                href = tautan_kolom[i].replace("{nilai}", e(urlencode({"": nilai})[1:]))
                teks = f'<a href="{href}">{teks}</a>'
            sel.append(f"<td{kelas}>{teks}</td>")
        baris_html.append("<tr>" + "".join(sel) + "</tr>")
    if not baris_html:
        return f"<div class=gulir><div class=kosong>{e(kosong)}</div></div>"
    kepala_html = "".join(f"<th>{e(k)}</th>" for k in kepala)
    return (
        f"<div class=gulir><table><thead><tr>{kepala_html}</tr></thead>"
        f"<tbody>{''.join(baris_html)}</tbody></table></div>"
    )


def pilihan(nama: str, entri: Sequence[tuple[str, str]], terpilih: str | None) -> str:
    opsi = "".join(
        f'<option value="{e(nilai)}"{" selected" if nilai == terpilih else ""}>{e(label)}</option>'
        for nilai, label in entri
    )
    return f'<select name="{e(nama)}">{opsi}</select>'


def isian(nama: str, nilai: str | None, *, petunjuk: str = "", lebar: int = 14) -> str:
    return (
        f'<input name="{e(nama)}" value="{e(nilai or "")}" placeholder="{e(petunjuk)}" '
        f'size="{lebar}">'
    )


def borang_tulis(aksi: str, csrf: str, isi: str, tombol: str, *, tersembunyi: dict[str, str] | None = None) -> str:
    """Formulir yang menulis: dikirim ke halaman konfirmasi dulu, belum menulis apa pun (K59 d)."""
    sembunyi = "".join(
        f'<input type=hidden name="{e(k)}" value="{e(v)}">' for k, v in (tersembunyi or {}).items()
    )
    return (
        f'<form class=borang method=post action="/tulis/{e(aksi)}">'
        f'<input type=hidden name=csrf value="{e(csrf)}">{sembunyi}{isi}'
        f"<button>{e(tombol)}…</button></form>"
    )


def centang(nama: str, label: str, tercentang: bool = False) -> str:
    return (
        f'<label class=centang><input type=checkbox name="{e(nama)}" value=1'
        f'{" checked" if tercentang else ""}>{e(label)}</label>'
    )


def memuat(lama_detik: float, keterangan: str) -> str:
    return (
        f'<div class="pesan info memuat"><span class=putar></span>'
        f"<span>Sedang menghitung {e(keterangan)} — {lama_detik:.0f} dtk. Halaman ini memuat "
        "ulang sendiri.</span></div>"
    )


def galat(teks: str, jejak: str | None) -> str:
    rinci = (
        f"<details><summary>Jejak lengkap (juga tercatat di log/web.log)</summary>{pra(jejak)}</details>"
        if jejak
        else ""
    )
    return f'<div class="pesan galat">GAGAL: {e(teks)}</div>{rinci}'
