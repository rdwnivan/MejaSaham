# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Aturan kerja yang mengikat (sumber kebenaran, aturan keras, ritme K4, bahasa, perintah dasar)
ada di AGENTS.md dan berlaku penuh:

@AGENTS.md

Berkas ini hanya menambahkan yang tidak tertulis di sana. **Di sesi baru, baca
`docs/lanjutan.md` lebih dulu** (bagian atasnya saja; berkasnya sangat panjang).

## Perintah tambahan

```powershell
# Satu berkas uji / satu fungsi uji / berdasarkan nama
.\.venv\Scripts\python -m pytest tests/test_skor.py
.\.venv\Scripts\python -m pytest tests/test_skor.py::nama_fungsi
.\.venv\Scripts\python -m pytest -k "kata_kunci"

# Jalankan perintah aplikasi tanpa menyentuh data kerja di %LOCALAPPDATA%\MejaSaham
.\.venv\Scripts\python -m mejasaham --saring --folder-data .tmp\data-coba
```

- Tidak ada linter/formatter yang dikonfigurasi; ikuti gaya berkas di sekitarnya.
- Suite penuh lambat (±50–160 dtk); jalankan berkas yang relevan saat iterasi, suite penuh
  sebelum klaim "selesai".
- Letak data runtime: `--folder-data` atau variabel lingkungan `MEJASAHAM_DATA` →
  `%LOCALAPPDATA%\MejaSaham` (`mejasaham/lokasi.py`). Uji memakai folder sementara, bukan data
  kerja. `.uji-data/mejasaham` berisi basis data kerja nyata — jangan dihapus/ditimpa; buat
  cadangan (`--buat-cadangan`) sebelum impor ke sana.

## Gambaran arsitektur

Rinciannya di `docs/arsitektur.md` (§2 alur data, §3 batas modul, §4 keputusan teknis T-nn) dan
`docs/skema-data.md`. Yang perlu dipahami lintas berkas:

- **Satu titik masuk.** `mejasaham/__main__.py` → `cli.py`. Tanpa perintah membuka dasbor web lokal
  (`mejasaham/web/`, K91 — jendela PySide6 dan EXE sudah dihapus); perintah lain (`--refresh`,
  `--saring`, …) berjalan tanpa dasbor. `MejaSaham.cmd` = peluncur klik-ganda (harus CRLF).
- **Web:** `web/server.py` (rute → fungsi inti yang sama dengan CLI),
  `web/pekerjaan.py` (hitungan di utas latar, halaman memuat ulang diri sampai selesai — kunci
  pekerjaan memakai penanda `kirim` agar muat ulang tidak memulai hitungan baru),
  `web/halaman.py` (HTML + escape), `web/formulir.py` (isian → `layar.tulis.permintaan_*`). Tulis
  selalu lewat `POST /tulis/<aksi>` → konfirmasi → `POST /konfirmasi` (token sekali pakai + CSRF). Susunan tabel/permintaan tulis bebas Qt ada di
  `mejasaham/layar/`, dipakai jendela dan web.
- **Batas diuji.** `tests/test_batas_ui.py`: tidak ada impor Qt di mana pun, dan inti tidak
  mengimpor `mejasaham.web` (hanya `cli.py`, di dalam cabang dasbor). Mode kepala tidak boleh
  memuat keduanya.
- **Jaringan dipisah dari aturan.** Adaptor sumber (`pengambil.py` = satu-satunya tempat yfinance,
  `ksei.py`, `kalender.py`, `sun.py`, `notasi.py`) hanya mengambil data dan **menulis berkas CSV
  rujukan** ke `konfigurasi/`; basis data diisi lewat `--impor` (`berkas.py` membaca bentuk berkas,
  `ingesti.py` menegakkan kontrak data). Uji menyuntikkan pengambil palsu — tidak ada uji yang
  butuh jaringan.
- **Alur data:** ingesti → snapshot atomik (`pengatur.py`, `arsip.py`) → laporan mutu (`mutu.py`)
  → `potret.py` memuat SATU snapshot secara as-of → `penyesuaian.py` (penyesuaian split saat
  dibaca, memakai `Fraction`) → `metrik.py` (nilai atau alasan "tidak dihitung"; tidak tahu preset)
  → `saring.py`/`skor.py` (preset berversi, z per sektor) → `kandidat.py` (tesis wajib) →
  `risiko.py` → `posisi.py` → `jurnal.py` (V1–V7) → `ekspor.py`/`dasbor.py`.
- **Point-in-time:** modul hilir membaca lewat `potret.py`, bukan view `v_<tabel>_terkini` —
  view itu memuat koreksi yang dicatat setelah snapshot dibuat.
- **Basis data:** SQLite WAL; migrasi berversi + trigger append-only di `skema.py`; koneksi dan
  kunci penulis tunggal di `db.py`. Perubahan skema = migrasi baru, bukan menyunting yang lama.
- **Konfigurasi:** `mejasaham/defaults/*.contoh.*` disalin ke folder data bila belum ada (AC-12)
  dan ikut dibundel oleh `tools/build_exe.py`. Parameter bursa dimuat dari TOML oleh
  `konfigurasi.py`; entri tanpa `berlaku_sejak`/`sumber` ditolak.
- **Penamaan:** istilah domain persis PRD dalam bahasa Indonesia (`id_snapshot`,
  `diketahui_pada`, `HargaHarian`); istilah teknis tetap Inggris (`connect`, `main`).
