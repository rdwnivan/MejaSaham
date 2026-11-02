# AGENTS.md — Aturan Kerja Meja Saham

Dokumen ini mengikat setiap agen/kontributor yang bekerja di repositori ini.

## 1. Sumber kebenaran

| Peran | Berkas |
|-------|--------|
| **Sumber kebenaran produk (APA & MENGAPA)** | `PRD-Screener-Saham-IDX-v1.3.docx` |
| Turunan sementara untuk memudahkan pembacaan | `_extract/prd_v1.3.txt` — **bukan** acuan final; jangan dikutip sebagai spesifikasi tanpa mencocokkan ke `.docx` |
| Keputusan & pertanyaan terbuka | `docs/keputusan.md` |
| Cara kerja sistem (HOW) | `docs/arsitektur.md`, `docs/skema-data.md` |
| Parameter bursa & ambang | `docs/konfigurasi.md` |
| Yang sengaja ditunda | `docs/ideas.md` |
| **Titik lanjut kerja** (turunan, bukan acuan) | `docs/lanjutan.md` — keadaan terkini, perintah verifikasi, aksi berikutnya berurutan, jebakan lingkungan yang sudah ditemukan. **Baca ini lebih dulu** di sesi baru |

Bila dokumen saling berbeda, urutannya: PRD `.docx` → `docs/keputusan.md` → dokumen lain.
Perbedaan itu dicatat, bukan dipilih diam-diam.

## 2. Aturan keras (tidak boleh dilanggar)

1. **Jangan mengarang parameter bursa.** Lot, fraksi harga (tick), batas ARA/ARB, siklus
   settlement, tarif broker, PPh penjualan, dan imbal hasil SUN wajib berasal dari pengumuman
   resmi dengan tanggal berlaku (PRD bagian 10). Selama belum terverifikasi, nilainya ditulis
   `[PERLU VERIFIKASI]` dan fitur yang bergantung padanya menolak menghitung atau menampilkan
   peringatan — **bukan** memakai angka tebakan.
2. **Metrik tanpa data berstatus "tidak dihitung".** Tidak diganti nol, tidak diganti rata-rata
   sektor, tidak diabaikan tanpa jejak; bobotnya dialihkan dan alasannya tampil (PRD 7.2, AC-3).
3. **Data append-only dan point-in-time.** Perbaikan data menambah baris baru, bukan menimpa.
   Setiap baris menyimpan `sumber` dan `diketahui_pada`. Fundamental dipakai sejak
   `tgl_publikasi`, bukan akhir periode (PRD 7.2, AC-15).
4. **Parameter bursa adalah konfigurasi bertanggal, bukan konstanta di kode** (PRD bagian 10).
5. **Inti perhitungan tidak boleh mengimpor UI.** Modul inti harus bisa diuji dan dijalankan
   lewat baris perintah tanpa membuka dasbor (PRD 6.1); hanya `cli.py` yang menyentuh
   `mejasaham.web` (diuji `tests/test_batas_ui.py`).
6. **Penulis tunggal.** Dasbor web dan mode kepala tidak boleh menulis basis data bersamaan
   (PRD 6.1, AC-19).
7. **Gagal itu berisik.** Kegagalan sebagian tidak boleh hanya terlihat di keluaran terminal
   (PRD 7.2, AC-9). Jangan menelan error dengan `except: pass`.
8. **Skor bukan nasihat investasi.** Setiap ekspor memuat pernyataan itu beserta `id_snapshot`
   dan versi preset (PRD 9.10, AC-7).
9. **Jangan membandingkan skor lintas preset** atau PER lintas sektor tanpa penyesuaian
   (PRD 10).

## 3. Ritme kerja (keputusan K4 di `docs/keputusan.md`)

- **Berhenti di setiap tahap untuk ditinjau.** Jangan menyambung ke tahap berikutnya tanpa
  persetujuan.
- Setiap akhir tahap melaporkan **empat hal**: (a) test lulus, (b) ringkasan yang dikerjakan,
  (c) daftar yang belum dikerjakan, (d) cara menjalankannya.
- Klaim "selesai" hanya boleh diucapkan setelah perintah verifikasinya dijalankan dan hasilnya
  dilaporkan apa adanya — termasuk bila gagal.
- Setiap akhir tahap juga **memperbarui `docs/lanjutan.md`** (keadaan terkini, aksi berikutnya,
  jebakan baru). Berkas itu turunan, bukan sumber kebenaran baru: isi ringkas + rujukan, bukan
  salinan `docs/keputusan.md`.

## 4. Bahasa & format

- Bahasa Indonesia untuk dokumen, pesan pengguna, dan komentar yang menjelaskan alasan.
- Angka tampil format Indonesia (koma desimal, titik ribuan); tanggal `06 Okt 2026` (usulan U11).
- Ekspor CSV: UTF-8 BOM, pemisah `;`, desimal koma (agar tidak rusak di Excel Indonesia).

## 5. Perintah

Dijalankan dari akar repositori (Windows PowerShell):

```powershell
# Sekali di awal (K3): buat .venv + pasang dependensi
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt   # pengembangan
.\.venv\Scripts\python -m pip install -r requirements.txt       # runtime

# Wajib sebelum klaim "selesai"
.\.venv\Scripts\python -m pytest

# Mode kepala — tanpa dasbor (AC-11, Task Scheduler)
.\.venv\Scripts\python -m mejasaham --refresh --saring

# Muat parameter bursa bertanggal dari TOML ke basis data (K6) + laporan keadaannya
.\.venv\Scripts\python -m mejasaham --muat-konfigurasi

# Dasbor web lokal (K91) — http://127.0.0.1:8765, Ctrl+C untuk berhenti.
# Tanpa argumen = dasbor; klik-ganda MejaSaham.cmd melakukan hal yang sama.
.\.venv\Scripts\python -m mejasaham
.\.venv\Scripts\python -m mejasaham --port 9000 --tanpa-peramban --folder-data .tmp\coba

# Menghasilkan ulang turunan PRD (butuh python-docx dari requirements-dev.txt)
.\.venv\Scripts\python tools\extract_docx.py PRD-Screener-Saham-IDX-v1.3.docx _extract/prd_v1.3.txt
```

Selalu pakai `python -m pytest`, bukan `pytest` langsung, supaya interpreter yang dipakai
pasti milik `.venv`. Status pemasangan terkini dicatat di `docs/keputusan.md` bagian 5.

## 6. Di mana menaruh sesuatu

- Keputusan produk yang sudah dikunci → baris di `docs/keputusan.md` bagian 1.
- Usulan yang belum dikunci → bagian 2 tabel "Usulan" di `docs/keputusan.md`.
- Pertanyaan yang memblokir kerja → bagian 3 di `docs/keputusan.md`, jangan dikarang sendiri.
- Keputusan teknis dengan alasan & tradeoff → `docs/arsitektur.md`.
- Parameter bursa/tarif/ambang → `docs/konfigurasi.md`.
- Keadaan terkini + aksi berikutnya (turunan) → `docs/lanjutan.md`, diperbarui di akhir tahap.
- Fitur di luar cakupan v0.1 → `docs/ideas.md`, bukan dihapus.

Konvensi: rujukan berkas dalam seluruh dokumen ditulis **relatif terhadap akar repositori**,
termasuk ketika ditulis dari dalam `docs/`. Tautan Markdown tetap memakai jalur relatif
terhadap berkas yang memuatnya.
