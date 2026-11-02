"""Dasbor web lokal (K91): pengganti jendela PySide6, hanya pustaka standar.

Server mendengar di `127.0.0.1` saja dan merender HTML di sisi server. Ia tidak menghitung apa
pun sendiri: tiap halaman memanggil fungsi inti yang sama dengan baris perintah, lalu menampilkan
`ringkas()`-nya dan tabel dari `mejasaham.layar.tabel`. Paket ini tidak boleh mengimpor Qt
(A1, diuji `tests/test_batas_ui.py`).
"""
