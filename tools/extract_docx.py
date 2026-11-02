"""Ekstraksi DOCX (paragraf + tabel) ke berkas teks biasa untuk ditinjau.

Pemakaian:
    python tools/extract_docx.py <masukan.docx> <keluaran.txt>

Keluaran adalah **artefak turunan**. Ia selalu diawali kepala jejak asal (nama berkas
sumber, SHA-256, waktu ekstraksi, versi alat) supaya kutipan darinya bisa dilacak
kembali ke revisi `.docx` yang tepat — dokumen PRD ini sudah beberapa kali revisi, dan
tanpa jejak asal sebuah kutipan tidak bisa diverifikasi.

Jangan menyunting keluarannya; jalankan ulang alat ini.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

VERSI_ALAT = "1.1"


def sha256(berkas: Path) -> str:
    sidik = hashlib.sha256()
    with berkas.open("rb") as fh:
        for potongan in iter(lambda: fh.read(1 << 20), b""):
            sidik.update(potongan)
    return sidik.hexdigest()


def iter_block_items(parent):
    """Yield Paragraph and Table objects in document order."""
    from docx.oxml.ns import qn

    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def judul_jejak_asal(sumber: Path, keluaran: Path) -> list[str]:
    waktu = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return [
        "=== ARTEFAK TURUNAN — JANGAN DISUNTING ===",
        f"sumber       : {sumber.name}",
        f"sha256       : {sha256(sumber)}",
        f"diekstraksi  : {waktu}",
        f"alat         : tools/extract_docx.py v{VERSI_ALAT}",
        f"cara ulang   : python tools/extract_docx.py {sumber.name} {keluaran.as_posix()}",
        "=== ISI ===",
    ]


def jadikan_teks(doc) -> tuple[list[str], int]:
    baris: list[str] = []
    tabel_ke = 0
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            teks = block.text.rstrip()
            gaya = block.style.name if block.style is not None else ""
            if not teks:
                baris.append("")
                continue
            if gaya.startswith("Heading") or gaya.startswith("Title"):
                baris.append(f"### [{gaya}] {teks}")
            else:
                baris.append(teks)
        else:
            tabel_ke += 1
            baris.append("")
            baris.append(f"--- TABLE {tabel_ke} ---")
            for row in block.rows:
                sel = [c.text.replace("\n", " / ").strip() for c in row.cells]
                baris.append(" | ".join(sel))
            baris.append(f"--- END TABLE {tabel_ke} ---")
            baris.append("")
    return baris, tabel_ke


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Pemakaian: python tools/extract_docx.py <masukan.docx> <keluaran.txt>",
            file=sys.stderr,
        )
        return 2

    sumber = Path(sys.argv[1])
    keluaran = Path(sys.argv[2])
    if not sumber.is_file():
        print(f"GAGAL: berkas sumber tidak ada: {sumber}", file=sys.stderr)
        return 1

    keluaran.parent.mkdir(parents=True, exist_ok=True)
    isi, tabel_ke = jadikan_teks(Document(str(sumber)))
    baris = judul_jejak_asal(sumber, keluaran) + isi
    keluaran.write_text("\n".join(baris), encoding="utf-8")
    print(
        f"ditulis {keluaran}: {len(baris)} baris, {tabel_ke} tabel, "
        f"sha256 sumber {sha256(sumber)[:12]}…"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
