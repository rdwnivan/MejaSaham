# Kandidat rasio bank — pilot 5 bank (K76, aksi #21b)

**Status: TERVERIFIKASI DAN SUDAH DIIMPOR (19 Okt 2026, snapshot 12); SEJAK SESI 32 DIPAKAI
KRITERIA BANK (snapshot 13).** Berkas ini mula-mula memuat
angka **kandidat** yang dibaca dari publikasi resmi bank; pada **sesi 31** angka itu diverifikasi
ulang terhadap PDF-nya (**14/14 sel cocok persis**, K83/aksi #29) dan kedua barisnya masuk basis data
lewat `konfigurasi/rasio-bank.csv` → `--impor`. Rincian hasilnya di **§8**; riwayat kandidatnya
dipertahankan di bawah apa adanya. Pada **sesi 32** kolom `jenis` emiten diisi, sehingga
**NPL/CAR/BOPO/NIM benar-benar dipakai** untuk 49 bank (BBCA keempatnya; BRIS dua) — rinciannya **§9**.

Tanggal akses seluruh sumber: **19 Okt 2026** · Lingkungan: CPython 3.14.7 + PySide6 6.12.0
(QtPdf) · Batas kerja pilot (K76): *sampai kandidat + kutipan*, **bukan** sampai impor — impornya
baru terjadi di sesi 31 setelah verifikasi K83.

## 0. Status keputusan (19 Okt 2026, sesi 26)

Empat pertanyaan di §5 sudah diputuskan pemilik produk ("sesuai rekomendasi") dan dicatat sebagai
**K77–K80** di `docs/keputusan.md` bagian 1:

| Hal | Keputusan | Akibat untuk berkas ini |
|---|---|---|
| NPF/NI bank syariah | **K77**: tidak dipetakan ke NPL/NIM; tetap kosong + alasan di `keterangan` | baris BRIS **tetap** seperti sekarang |
| Tiga bank yang menolak robots | **K79**: tidak diakali; pilot lanjut dengan 2 bank | BBRI/BMRI/BBNI tetap tanpa angka |
| `sumber` per baris hilang (U33) | **K78**: dikerjakan sebagai **aksi #27**, sebelum impor | **SUDAH SELESAI 19 Okt 2026 (sesi 27, T77)** — asal tiap bank kini tersimpan per baris |
| Sel `sumber` kosong | **K81** (sesi 28): **ditolak per baris** — bukan jatuh ke label kumpulan | isi `sumber` di **setiap** baris `rasio-bank.csv` |
| Verifikasi angka | **K83** (sesi 30): **dialihkan ke agen** dengan pagar "cocok persis" — dikerjakan sebagai **aksi #29** | **SELESAI 19 Okt 2026 (sesi 31): 14/14 sel cocok persis, kedua baris diimpor (snapshot 12)** — lihat §8 |

**Aksi #27, #28, dan #29 sudah selesai**, jadi status berkas ini berubah dari **kandidat** menjadi
**sudah diverifikasi dan sudah diimpor** (19 Okt 2026, snapshot 12) — rinciannya §8. Dua hal yang
sempat terbuka **sudah dikunci** (19 Okt 2026, "sesuai rekomendasi"): **U34 → K86** (`tgl_publikasi`
BRIS **tetap 2026-08-21**) dan **perluasan ke 44 bank → K87 (DITUNDA)**. **Sesi 32 menjalankan
prasyaratnya:** `jenis` diisi (**49 bank_keuangan**) dan kriteria bank kini **diterapkan** (§9);
**44 dokumen tetap ditunda**, sebab peringkat tidak berubah dan **47 dari 49 bank belum berasio**.

---

## 1. Hasil: dua bank terbaca, tiga tidak

| Bank | Posisi | NPL kotor | CAR (KPMM) | BOPO | NIM | Status |
|---|---|---|---|---|---|---|
| **BBCA** | 30 Jun 2026 | **1,86%** | **26,79%** | **41,22%** | **5,32%** | 4 dari 4 rasio terbaca |
| **BRIS** | 30 Jun 2026 | — (NPF gross 1,80%) | **20,41%** | **69,71%** | — (Net Imbalan 5,42%) | 2 dari 4; dua kolom sengaja kosong |
| **BBRI** | 30 Jun 2026 | — | — | — | — | tidak terbaca (lihat §3) |
| **BMRI** | 30 Jun 2026 | — | — | — | — | tidak terbaca (lihat §3) |
| **BBNI** | 30 Jun 2026 | — | — | — | — | tidak terbaca (lihat §3) |

Angka di tabel ini ditulis dengan koma (format tampilan). **Berkas kandidatnya memakai titik
desimal**, karena pembaca impor menolak koma — lihat temuan T1 di §4.

Berkas:

* `.uji-data/riset-idx/rasio-bank/kandidat-rasio-bank.csv` — 2 baris berangka, kolom
  `berkas.SPESIFIKASI["rasio_bank"]` **+** `url`, `tanggal_akses`, `kutipan` (tiga kolom
  pemeriksaan yang tidak ikut diimpor).
* `.uji-data/riset-idx/rasio-bank/kandidat-tidak-terbaca.csv` — 3 bank yang angkanya tidak
  diambil, beserta sebabnya.
* `.uji-data/riset-idx/rasio-bank/bukti-pilot-rasio-bank.txt` — ringkasan bukti + SHA-256.
* `.uji-data/riset-idx/rasio-bank/png/` — **render halaman yang saya lihat** saat membaca angka.

---

## 2. Yang terbaca, beserta kutipan dan sumbernya

### BBCA — 30 Juni 2026 (tidak diaudit)

Sumber resmi: *Laporan Keuangan Publikasi 30 Juni 2026*, halaman 5, tabel
"LAPORAN RASIO KEUANGAN — Pada Tanggal 30 Juni 2026 & 2025".

<https://www.bca.co.id/-/media/Feature/Report/File/S8/Laporan-Triwulan/2026/20260728-laporan-keuangan-juni-2026.pdf>

> 1. Kewajiban Penyediaan Modal Minimum (KPMM) **26,79%** 28,39%
> 5. NPL gross **1,86%** 2,17%
> 10. Net Interest Margin (NIM) **5,32%** 5,78%
> 11. Beban Operasional terhadap Pendapatan Operasional (BOPO) **41,22%** 40,46%

Kolom yang dipakai adalah kolom pertama, **"30 Jun 2026 (Tidak Diaudit)"**. Tanggal publikasi
**28 Jul 2026** diambil dari nama berkas (`20260728-…`) dan header HTTP `Last-Modified`
28 Jul 2026. Halaman itu **masih memuat "Jakarta, 23 Januari 2025"** di blok tanda tangan —
sisa templat lama; tanggal itu tidak dipakai.

### BRIS — 30 Juni 2026 (direviu)

Sumber resmi: *Laporan Publikasi Triwulanan Juni 2026*, blok "Laporan Rasio Keuangan"
(satu halaman poster), ditandatangani **Jakarta, 21 Agustus 2026**.

<https://ir.bankbsi.co.id/misc/Laporan-Keuangan/Tahun-Laporan-2026/Laporan-Publikasi-Triwulan-Jun-ID.pdf>

> 1. Kewajiban Penyediaan Modal Minimum (KPMM) **20,41** 21,38
> 5. Non Performing Financing (NPF) gross **1,80** 1,87
> 9. Net Imbalan (NI) **5,42** 5,73
> 11. Biaya Operasional terhadap Pendapatan Operasional (BOPO) **69,71** 71,02

Kolom pertama = **"30 Juni 2026 (Direviu)"**. Perlu dicatat: lapisan teks PDF menaruh angka
2025 lebih dulu, sedangkan **render halaman** menunjukkan kolom kiri = 2026 — karena itu angka
diambil dari render, dan urutannya sudah dicek ulang di gambar.

**Dua kolom sengaja kosong.** BRIS adalah bank syariah: yang diterbitkan adalah **NPF gross**
(bukan NPL) dan **Net Imbalan** (bukan NIM). Keduanya **tidak** saya isi ke
`npl_kotor_persen`/`nim_persen`, karena NPF ≠ NPL dan NI ≠ NIM; memetakannya diam-diam akan
mengubah arti ambang PRD 8.4 tanpa jejak. Nilainya tetap tercatat di `keterangan` supaya Anda
bisa memutuskan.

---

## 3. Tiga bank yang angkanya tidak diambil (dan sebabnya)

| Bank | Sebab | Bukti |
|---|---|---|
| **BMRI** | `robots.txt` bankmandiri.co.id: `User-Agent: *` / `Disallow: /*.pdf$`. Seluruh publikasinya PDF, jadi jalur otomatisnya ditolak oleh kebijakan situsnya sendiri. Halaman katalog dirender JavaScript. | `https://www.bankmandiri.co.id/robots.txt` |
| **BBNI** | `robots.txt` bni.co.id: `Disallow: /Portals/` — folder tempat seluruh publikasi BNI. Halaman katalog membalas tantangan Incapsula (HTTP 200, 212 byte), juga kepada peramban headless. | `https://www.bni.co.id/robots.txt` |
| **BBRI** | `robots.txt` bri.co.id tidak dapat dibaca (tantangan Incapsula) dan katalog `bri.co.id/laporan` hanya kerangka JavaScript. Dokumen resmi yang bisa dibaca dari `ir-bri.com` (robots-nya mengizinkan) **tidak memuat tabel rasio**: laporan keuangan Q2-2026 (436 hlm.) memuat "BOPO" 0 kali dan "Net Interest Margin" 0 kali; presentasi 1H-2026 memakai **CIR 39,2%**, bukan BOPO. | `pdf/bri-laporan-publikasi-q2-2026-teks.txt`, `pdf/bri-presentasi-1h-2026-teks.txt` |

Dua catatan jujur: satu PDF bulanan BMRI dan dua PDF Pillar 3 BNI **sempat** terunduh sebelum
`robots.txt`-nya saya periksa. Ketiganya tidak memuat angka yang dicari, dan pengambilan
dihentikan begitu robots-nya terbaca. Berkasnya tetap disimpan sebagai bukti
(`pdf/bmri-laporan-publikasi-juni-2026.pdf`, `pdf/uji-bni-*.pdf`).

Jalur IDX tetap tertutup: dua percobaan ke `www.idx.co.id/StaticData/…pdf` menjawab **HTTP 403**
(sama seperti catatan §2.1 di `docs/lanjutan.md`).

---

## 4. Temuan yang mengubah cara pekerjaan ini dilanjutkan

**T1 — desimal koma ditolak pembaca impor.** Versi pertama berkas kandidat memakai `1,86` dan
impor berhenti berisik: `rasio-bank.csv baris 2 npl_kotor_persen: bukan angka yang bisa dibaca
('1,86')`. Pembaca memakai `Decimal("…")`, dan templat
`mejasaham/defaults/rasio-bank.contoh.csv` memang mencontohkan `2.35 untuk 2,35%`. Aturannya:
**berkas impor = titik desimal, tampilan/ekspor = koma desimal.**

**T2 — kolom `sumber` per baris pada `rasio-bank.csv` tidak tersimpan.** `berkas._baris_rasio_bank`
tidak mengisi `sumber` (kelas `RasioBank` tidak punya bidang itu), lalu
`ingesti._baris_rasio_bank` memakai `kumpulan.sumber` = `impor berkas: <folder>`. Akibatnya asal
angka per bank (URL + tanggal) **hilang saat impor**, padahal kolom itu wajib di berkas.
`fundamental` sudah memakai `sumber` per baris sejak K18; `rasio_bank` belum. Uji baca
membuktikannya: `sumber baris: 'impor berkas: …\\uji-baca'`. Diusulkan sebagai **U33**;
**SUDAH DIPERBAIKI 19 Okt 2026 (sesi 27, aksi #27 → K78/T77)** — `sumber` kini dibaca dari berkas,
disimpan per baris, dan dikembalikan `potret`; sel kosong ditolak berisik. Temuan ini dibiarkan
sebagai riwayat pengukuran pilot.

**T3 — NPF/NI bukan NPL/NIM** (lihat §2): menunggu keputusan Anda, bukan dipetakan diam-diam.

---

## 5. Yang perlu Anda periksa (checklist verifikasi)

1. **BBCA**: 26,79 / 1,86 / 41,22 / 5,32 untuk posisi 30 Jun 2026 — cocok dengan halaman 5 PDF
   di tautan §2.
2. **BRIS**: 20,41 (KPMM) dan 69,71 (BOPO) untuk posisi 30 Jun 2026 — cocok dengan blok
   "Laporan Rasio Keuangan" di PDF §2.
3. **Keputusan bank syariah**: NPF gross 1,80% dan Net Imbalan 5,42% — **sudah diputuskan (K77):
   dibiarkan kosong**, tidak dipetakan ke `npl_kotor_persen`/`nim_persen`.
4. **Tiga bank yang belum terbaca**: **sudah diputuskan (K79): tidak diakali, pilot lanjut tanpa
   mereka**; bila kelak diinginkan, Anda mengunduh PDF-nya sendiri ke
   `.uji-data/riset-idx/rasio-bank/pdf/manual/`.
5. **U33** (§4 T2): **sudah diputuskan (K78) dan sudah dikerjakan sesi 27 (aksi #27, T77)** —
   `sumber` per baris kini dipakai, disimpan, dan kembali lewat `potret`.

---

## 6. Sesudah Anda memutuskan (urutan yang saya sarankan)

> **Diperbarui sesi 31 (19 Okt 2026):** aksi #27 (K78/T77), #28 (K82/T78), dan **#29 (K83/T79)**
> sudah selesai. **Verifikasi ulang dijalankan apa adanya:** SHA-256 kedua PDF = manifest, halaman
> dirender ulang, **14/14 sel cocok persis**, lalu cadangan dibuat dan **kedua baris diimpor**
> (`--impor` → snapshot 12). Urutan yang tersisa hanyalah langkah 6 di bawah (**putuskan 44 bank**) —
> dan ingat `--saring` **belum berubah** karena `jenis` 973 emiten masih kosong (§8).

1. ~~**Aksi #27 (K78)**~~ — **SELESAI 19 Okt 2026 (sesi 27)**: `sumber` per baris `rasio_bank` kini
   dipakai, bukan dibuang, sehingga asal angka kedua bank ikut tersimpan saat impor.
2. Perbaiki angka yang keliru (kalau ada) langsung di `kandidat-rasio-bank.csv`.
3. Buang tiga kolom pemeriksaan (`url`, `tanggal_akses`, `kutipan`) → simpan sebagai
   `konfigurasi/rasio-bank.csv` (atau salin ke folder konfigurasi yang Anda pakai). **Setiap baris
   wajib mengisi `sumber`** — sel kosong ditolak per baris (K81).
4. `.\.venv\Scripts\python -m mejasaham --impor <folder-konfigurasi> --folder-data .uji-data\mejasaham`
5. Periksa `v_rasio_bank_terkini` dan `--saring`; bandingkan dengan temuan K68 bahwa
   **0 dari 49 bank tertahan *hanya* oleh rasio bank** — jadi jangan berharap peringkat bank
   berubah hanya karena berkas ini terisi.
6. Baru putuskan perluasan ke 44 bank lain — dan hitung dulu berapa bank yang akan menuntut
   langkah manual (K79: `robots.txt` sebagian bank menolak pengambilan PDF otomatis).

---

## 7. Cara mengulang

```powershell
# 1) Unduh ulang sumber (mencatat status, ukuran, dan SHA-256 ke manifest-unduhan.txt)
.\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\unduh.py "<url>" "<berkas-keluar>"

# 2) Baca teks per halaman + render halaman yang dituju (QtPdf, tanpa dependensi baru)
.\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\baca-pdf.py "pdf/<berkas>.pdf" <halaman>

# 3) Perbesar potongan tabel yang kecil (mis. poster BSI)
.\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\potong-pdf.py "pdf/<berkas>.pdf" 1 0.70 0.06 1.00 0.25 4

# 4) Susun ulang berkas kandidat + uji bahwa jalur impor membacanya benar (tanpa basis data)
.\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\buat-kandidat.py
.\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\uji-baca-kandidat.py
```

Bukti uji jalur: `.uji-data/riset-idx/rasio-bank/bukti-uji-baca.txt` — hasil terakhir
**LULUS** (BBCA `186/2679/4122/532` bp; BRIS `None/2041/6971/None` bp).

---

## 8. Hasil verifikasi ulang dan impor (sesi 31, 19 Okt 2026 — aksi #29/K83)

**Status: TERVERIFIKASI DAN SUDAH DIIMPOR** (snapshot **12**, 19 Okt 2026 18:13 +07:00).

| Langkah | Hasil |
|---|---|
| SHA-256 berkas sumber vs `manifest-unduhan.txt` | **cocok 2/2** — BCA `964526ed…`, BRIS `bc62a12a…` |
| Render ulang halaman (bukan PNG pilot) | BCA hlm. 5 · BRIS poster (blok rasio, kepala kolom, tanda tangan) — `.uji-data/uji-k83/bukti/` |
| Setiap sel: `periode`, `tgl_publikasi`, 4 rasio, `sumber` | **14/14 cocok persis** |
| Tanggal publikasi BCA | `2026-07-28` dari nama berkas **dan** HEAD ulang: `Last-Modified Tue, 28 Jul 2026 09:13:08 GMT`, `Content-Length` 196142 = berkas lokal |
| Tanggal publikasi BRIS | `2026-08-21` dari tanda tangan yang terbaca di render; `Last-Modified` berkasnya **24 Agu 2026** → selisih 3 hari dicatat sebagai **U34**, lalu **diputuskan K86: 21 Agu dipertahankan** (nilai tercetak) |
| Cadangan sebelum menulis | `.uji-data\mejasaham-cadangan\20261019T181212314095+0700` |
| Berkas produksi | `konfigurasi/rasio-bank.csv`, 2 baris, 9 kolom; `keterangan` basi dibersihkan; sha256 `c5d833af…` |
| Impor | keluar **0** · snapshot **12** · `rasio_bank` **0 → 2** · 2330 baris baru / 2898 sama |
| `v_rasio_bank_terkini` | BBCA `186/2679/4122/532` bp · BRIS `None/2041/6971/None` bp, `sumber` per baris |
| `--saring` | **tidak berubah** — 973 emiten, 9 lolos/9 dinilai. Sebab: `jenis` **973 emiten kosong** (kriteria bank tidak diterapkan) dan BBCA/BRIS gagal `coverage` (EBIT tahunan) |
| Integritas | `PRAGMA integrity_check` = `ok` |

**Efek samping yang dilaporkan:** impor dari folder konfigurasi produksi menulis ulang label
`sumber` **2328** baris `notasi_khusus` (+2328 revisi; `tanggal_selesai`/`keterangan` identik).
Dicatat sebagai jebakan di `docs/lanjutan.md` bagian 6 — bukan diperbaiki diam-diam.

**Yang tetap berlaku:** angka yang **tidak** terbaca (NPF/NI BRIS, tiga bank) **tidak** diganti
tebakan; `sumber` per baris ikut tersimpan (K78) dan kembali lewat `potret` (T77/T78); dan
**`--saring` belum berubah** — persis yang diperingatkan K68.

Bukti mentah: `.uji-data/uji-k83/bukti/bukti-ringkas.txt` (+ `bukti-verifikasi.txt`,
`bukti-berkas-produksi.txt`, `bukti-impor.txt`, `bukti-saring*.txt`, `db-sebelum.txt` /
`db-sesudah.txt`). Rincian keputusan: `docs/keputusan.md` bagian 5 (sesi 31) dan **T79**
`docs/arsitektur.md`.

---

## 9. Prasyarat K87 dijalankan — `jenis` terisi, rasio bank kini DIPAKAI (sesi 32, 19 Okt 2026)

**Status: rasio bank dipakai berhitung.** Sebelum sesi 32, kedua baris di §8 tersimpan tetapi
**tidak berpengaruh**: `jenis` 973 emiten kosong, sehingga kriteria bank (NPL/CAR/BOPO/NIM) tidak
diterapkan kepada siapa pun. Sesi 32 menjalankan `--ambil-jenis --timpa-jenis` (K21) atas basis data
kerja — **49 bank_keuangan · 862 umum · 62 kosong** — lalu `--impor` → **snapshot 13**.

| Yang diukur sesudah impor | Hasil |
|---|---|
| `--saring` sebaran jenis | **49 bank_keuangan (dari data)** · 862 umum · 62 belum terisi |
| Kriteria bank untuk **BBCA** | `npl_kotor` **186 bp** lolos (≤ 3,00%) · `car` **2679 bp** lolos (≥ 14,00%) · `bopo` **4122 bp** lolos (≤ 85,00%) · `nim` **532 bp** lolos (≥ 3,50%) — **keempatnya dipakai** |
| Kriteria bukan-bank untuk BBCA | `der`, `coverage`, `cfo_ni` → **`berlaku=False`** ("tidak berlaku untuk bank & lembaga keuangan", PRD 8.4) |
| Kriteria bank untuk **BRIS** | `car` **2041** lolos · `bopo` **6971** lolos · `npl_kotor`/`nim` **tidak dinilai** (*"tidak dilaporkan pada periode 2026-06-30"* — K77: NPF/NI tidak dipetakan) |
| Bank yang punya rasio | **2 dari 49** (BBCA, BRIS); **47** menjawab *"rasio bank … belum diimpor lewat rasio-bank.csv"* |
| Peringkat | **tidak berubah** — 9 lolos · 9 dinilai; sembilan kandidat sama persis; **884 → 883** "tidak bisa disaring" (BBCA kini punya vonis nyata: gagal `pbv_relatif_sektor` + `tren_ma200`) |

**Artinya:** angka di §1–§2 sekarang **bekerja** untuk dua bank; pekerjaan yang tersisa adalah
**47 bank tanpa rasio** — itulah yang akan diisi oleh perluasan **44 dokumen** yang **masih ditunda
(K87)**, bersama **hitung langkah manual (K79)** yang belum dijalankan. **K68 tetap berlaku**:
mengisi rasio tidak dengan sendirinya mengubah peringkat.

Bukti: `.uji-data/uji-jenis-kerja/bukti/` (`saring-sesudah.txt`, `kriteria-sebelum.txt` vs
`kriteria-sesudah.txt`, `ringkas-bank-sesudah.txt`, `db-sebelum.txt` vs `db-sesudah.txt`,
`impor-produksi.txt`, `ambil-jenis.log`, `banding-csv.txt`). Rincian: `docs/keputusan.md` bagian 5
(sesi 32).

---

## 10. Hitung langkah manual (K79) untuk 44 bank — hasil pengukuran (sesi 33, 19 Okt 2026)

**Status: TERUKUR — 8 dari 44 bank menuntut langkah manual, 2 tidak terukur, 34 boleh otomatis.**
Ini **bukan** izin menambah 44 dokumen (K87 masih berlaku); yang dijalankan hanyalah langkah
"hitung dulu berapa bank yang menuntut langkah manual" yang tercatat sebagai sisa pekerjaan K87.

### 10.1 Apa yang diukur, dan apa yang tidak

Yang diukur hanya **kebijakan dan keterjangkauan**, bukan angkanya:

1. **Domain resmi** tiap bank ditetapkan dari halaman depannya (judul halaman menyebut nama bank);
   empat calon domain terbukti salah dari isinya dan diganti: `bumiarta.co.id` ("Coming Soon"),
   `bankoke.com` (halaman parkir), `bankmnc.com` ("Coming Soon"), `bankcapital.id` (tidak ada).
   Untuk bank yang situsnya menolak dibaca (**AGRS**, **SDRA**, **INPC**), domain diambil dari
   rujukan resmi dan **tidak** diklaim sebagai hasil verifikasi halaman.
2. **`robots.txt`** diambil dari host yang menjawab, diurai per grup `User-agent` (token `mejasaham`,
   lalu `*`), dan diuji terhadap **11 jalur wakil** — `/` plus sepuluh jalur PDF yang lazim
   (`/media/`, `/files/`, `/uploads/`, `/Portals/0/`, `/wp-content/uploads/`, `/content/dam/`, …).
3. **Keterjangkauan situs** diuji dengan klien HTTP biasa (`requests`, tanpa peramban), **tiga kali**
   untuk setiap kegagalan, dan halaman yang membalas tantangan (Cloudflare, Incapsula, WAF F5)
   dikenali dari isinya.

Yang **tidak** diukur: apakah laporan publikasi triwulanan benar-benar ada di situs itu, apakah
tabel rasio keuangannya lengkap, dan apakah angkanya terbaca. Itu pekerjaan per dokumen yang
**belum** dimulai (K87) dan masih menuntut pembacaan visual seperti pilot §1–§2 (K76).

### 10.2 Hasil: 44 bank sasaran

Sasaran 44 = 49 `bank_keuangan` − **BBCA/BRIS** (sudah berasio) − **BBRI/BMRI/BBNI** (pilot yang
sudah dinyatakan tidak terbaca di K79).

| Vonis | Jumlah | Bank | Dasar bukti |
|---|---|---|---|
| **MANUAL — robots** | **2** | **BTPS**, **DNAR** | BTPS: `User-agent: *` / `Disallow: /` (seluruh situs). DNAR: `Disallow: /media`, `/images` — folder tempat publikasi biasa diletakkan |
| **MANUAL — akses** | **6** | **AGRS**, **BBMD**, **BBTN**, **BNLI**, **SUPA**, **BACA** | AGRS: WAF F5 "Request Rejected" 3/3 · BBMD: Cloudflare "Just a moment…" 403 3/3 · BBTN: Incapsula 212 byte 3/3 · BNLI: 403 "Access Denied" 3/3 · SUPA: 403 Forbidden 3/3 · BACA: HTTP 502 konsisten 3/3 (situs tidak melayani saat diukur) |
| **Tidak terukur — jaringan** | **2** | **INPC**, **SDRA** | Connect timeout 3/3 (INPC); SSL error 3/3 (SDRA). **Bukan** bukti kebijakan bank — dicatat sebagai batas pengukuran |
| **Otomatis mungkin** | **34** | AGRO, AMAR, ARTO, BABP, BANK, BBHI, BBKP, BBSI, BBYB, BCIC, BDMN, BEKS, BGTG, BINA, BJBR, BJTM, BKSW, BMAS, BNBA, BNGA, BNII, BSIM, BSWD, BTPN, BVIC, MASB, MAYA, MCOR, MEGA, NISP, NOBU, PNBN, PNBS, PNLF | Situs menjawab dan robots mengizinkan |

**Kontrol metode — tiga bank pilot di luar sasaran diukur ulang dan hasilnya konsisten dengan K79:**
**BMRI** `Disallow: /*.pdf$` (semua PDF ditolak), **BBNI** `Disallow: /Portals/` + Incapsula 212 byte
3/3, **BBRI** situsnya **terjangkau** (307 → halaman 351.497 byte pada percobaan ke-2) — yang gagal di
sana memang **dokumennya**, bukan aksesnya, persis catatan §3.

### 10.3 Uji kelayakan: izin robots ≠ dokumen ketemu

Untuk 34 bank "otomatis mungkin", halaman depan dibaca dan tautan yang menyebut
*laporan/publikasi/investor/tahunan* diikuti **satu tingkat**, lalu tautan PDF dihitung. Hasilnya:
**12 dari 34** benar-benar berpindah ke halaman publikasi (16 bila jangkar di halaman depan ikut
dihitung) dan **11 dari 34** memuat tautan PDF pada satu tingkat itu — **isi PDF-nya belum diperiksa**,
jadi belum tentu memuat tabel rasio. Angka itu **batas bawah**, bukan hitungan: situs yang dirender
JavaScript (contohnya BBCA dan BRIS di pilot) tidak menampakkan tautannya kepada klien HTTP biasa.

**Artinya izin robots adalah syarat perlu, bukan cukup.** Dari 34 bank yang "boleh", **22 belum
menunjukkan halaman publikasinya** dalam satu tingkat penjelajahan; menemukannya tetap
pekerjaan per bank.

### 10.4 Yang perlu diputuskan (U35)

Angkanya mengubah bentuk pekerjaan, bukan hanya biayanya:

* **8 bank** paling cepat ditangani dengan **PDF diunduh pengguna** ke
  `.uji-data/riset-idx/rasio-bank/pdf/manual/` (jalan yang sudah ditetapkan K79) — bukan diakali.
* **34 bank** bisa dicoba otomatis, tetapi **tiap bank tetap** menuntut pencarian dokumen + pembacaan
  visual + verifikasi sel (K76/K83). Itu **±34 kali pekerjaan pilot**, bukan satu jalankan skrip.
* **2 bank** belum dapat diputuskan sampai jaringan/sertifikatnya normal.

Karena **0 dari 49 bank tertahan *hanya* oleh rasio bank** (K68), usulan saya: **tetap tunda**
perluasan 44 dokumen; bila kelak dijalankan, urutannya **34 otomatis dulu**, **8 manual** menyusul
hanya bila PDF-nya tersedia. Usulan ini dicatat sebagai **U35** di `docs/keputusan.md` bagian 2 dan
**diputuskan 19 Okt 2026 → K88: 44 dokumen TETAP DITUNDA** (jawaban pengguna "sesuai rekomendasi
saja, catet jangan ngoding"). Keputusan itu tidak mengubah angka di §10.2–§10.3; ia hanya
menetapkan bahwa pekerjaan itu **belum dimulai** sampai ada permintaan baru.

### 10.5 Bukti dan cara mengulang

```powershell
# 1) Domain resmi tiap bank (judul halaman jadi buktinya)
.\.venv\Scripts\python .uji-data\riset-idx\k79\pindai-situs.py

# 2) robots.txt + keterjangkauan situs, 49 bank → CSV + JSON
.\.venv\Scripts\python .uji-data\riset-idx\k79\pindai-robots.py

# 3) Uji kelayakan halaman publikasi (34 bank "otomatis mungkin")
.\.venv\Scripts\python .uji-data\riset-idx\k79\uji-halaman-publikasi.py

# 4) Gabungkan dengan bukti percobaan ulang → tabel final + ringkasan
.\.venv\Scripts\python .uji-data\riset-idx\k79\gabung-hasil.py
```

Bukti mentah (gitignored): `.uji-data/uji-k79/bukti/` — `k79-hasil-final.csv` (49 baris, satu baris
per bank), `k79-ringkasan.txt`, `k79-pindai-robots.csv`/`.json`, `k79-uji-halaman.csv`/`.json`,
`robots-<KODE>.txt` (49 berkas berisi robots.txt apa adanya + status situs), dan log tiap tahap
(`tahap-a-domain.txt`, `tahap-b-robots-final.txt`, `tahap-b-ulang-final.txt`, `tahap-c-halaman.txt`,
`tahap-d-gabung.txt`). **Tanpa perubahan kode/uji dan tanpa satu baris basis data yang ditulis.**

---

## 11. Gelombang 1 perluasan: 5 bank otomatis (sesi 69, 29 Okt 2026)

**Status: TERVERIFIKASI ULANG (K83) DAN SUDAH DIIMPOR (snapshot 25, 29 Okt 2026 21.18) — lihat §11.5.** K88 dicabut oleh permintaan pengguna
(sesi 69: tahap 3 "44 bank", lalu "Lanjut"). Seperti pilot K76, gelombang ini **berhenti di berkas
kandidat**: `konfigurasi/rasio-bank.csv` dan basis data kerja **tidak** disentuh. Impor menunggu
verifikasi ulang "cocok persis" (K83) sesudah tinjauan pengguna.

### 11.1 Hasil

| Kode | Periode | `tgl_publikasi` | KPMM | NPL gross | BOPO | NIM | Dokumen |
|---|---|---|---|---|---|---|---|
| BEKS | 30 Jun 2026 | 14 Agu 2026 (K105) | 33,73 | 4,51 | 91,47 | 3,19 | Lap. Keuangan Publikasi TW II 2026 |
| MEGA | 30 Jun 2026 | 31 Jul 2026 | 25,03 | 1,56 | 72,65 | 4,36 | Lap. Keuangan Publikasi 30 Jun 2026, hlm. 12 |
| BNGA | 30 Sep 2026 | 28 Okt 2026 | 23,00 | 1,42 | 75,47 | 3,56 | Lap. Keuangan Publikasi Sep 2026 (set Bank) |
| BDMN | 30 Sep 2026 | 29 Okt 2026 | 21,69 | 1,60 | 78,06 | 4,27 | Lap. Keuangan Publikasi Sep 2026 (Rasio Bank) |
| BJTM | 30 Jun 2026 | 30 Jul 2026 | 23,72 | 4,38 | 82,14 | 5,90 | Lap. Publikasi Triwulanan Jun 2026 (kolom Bank) |

Setiap angka dibaca dari **render** halaman (potongan PNG di `.uji-data/riset-idx/rasio-bank/png/`),
bukan hanya dari lapisan teks; Bank Jatim bahkan **pindaian tanpa lapisan teks**. URL, kutipan apa
adanya, dan alasan pemilihan baris ada di `kandidat-rasio-bank.csv` (kolom `keterangan`, `url`,
`kutipan`). Uji jalur impor tanpa basis data (`uji-baca-kandidat.py`): **LULUS, 7 baris** (2 lama + 5
baru). SHA-256 kelima berkas tercatat di `manifest-unduhan.txt`.

**Bank kelima diganti:** QNB (BKSW) semula dipilih, tetapi `robots.txt`-nya membalas halaman HTML
"Access Denied" — bukan aturan — sehingga dilewati, bukan ditebak boleh; Bank Jatim menggantikannya.

### 11.2 Yang ditemukan (U39 → **diputuskan K105**, 29 Okt 2026: usulan dipakai apa adanya)

1. **Dua set rasio.** CIMB Niaga dan Danamon menerbitkan set **konsolidasian** dan set **bank**;
   Bank Jatim memisah KPMM individual/konsolidasi. Kandidat memakai set **bank (individual)**:
   hanya set itu yang lengkap di semua bank (set konsolidasian Danamon tidak memuat BOPO, NIM-nya
   termasuk premi penjaminan). Angka konsolidasian dicatat di `keterangan`. BBCA dan MEGA hanya
   menerbitkan satu set.
2. **Tanggal publikasi Bank Banten.** Tanda tangan 27 Jul 2026, tetapi berkas di folder unggah
   `/2026/08/` dengan Last-Modified 14 Agu 2026 (selisih 18 hari). Menurut **K105(b)** (selisih > 7 hari →
   tanggal unggahan) kandidat kini memakai **14 Agu 2026**; tanggal tercetak tetap di `keterangan`.
3. **Dua bank sudah menerbitkan posisi 30 Sep 2026** (CIMB 28 Okt, Danamon 29 Okt); tiga lainnya masih
   30 Jun 2026. Kandidat memakai publikasi **terbaru** yang ada per bank.
4. **PNLF** (Panin Financial) ada di daftar 34 "otomatis", padahal induk asuransi, bukan bank —
   **K105(c): dikeluarkan dari sasaran** — sasaran "otomatis" menjadi 33.

### 11.3 Alat yang ditambah/diubah (`.uji-data/riset-idx/rasio-bank/`, gitignored)

- `cek-robots.py` (baru) — periksa `robots.txt` **host berkas** sebelum unduh (host CDN bisa berbeda
  dari situs utama). 4xx = tidak ada larangan menurut RFC 9309 (kodenya dicetak); 5xx, gagal jaringan,
  atau balasan HTML = **tidak** diizinkan.
- `potong-pdf.py` — render kini ditumpuk di atas latar putih: render QtPdf berlatar transparan
  menampilkan sebagian publikasi Bank Banten sebagai blok hitam.
- `buat-kandidat.py` — 5 baris baru (`TANGGAL_AKSES_G1 = 2026-10-29`).

**Jebakan:** `unduh.py` menafsirkan jalur keluaran **relatif terhadap folder rasio-bank**; memberi
`.uji-data\riset-idx\rasio-bank\pdf\…` membuat folder bersarang (terjadi sekali; berkas dipindah dan
baris manifest dibetulkan). Beri `pdf\<nama>.pdf` saja.

### 11.4 Sisa

- 28 bank "otomatis" lain (34 − 5 − PNLF), 8 manual (K79: PDF diunduh pengguna ke `pdf/manual/`), 2 belum
  terukur (INPC, SDRA).
- ~~Verifikasi ulang K83~~ **selesai**: `.uji-data/uji-g1/verifikasi.py` → keluar 0, seluruh sel
  cocok (hash = manifest, 4 rasio + periode + `tgl_publikasi` + `sumber`, lapisan teks, dan
  `Last-Modified` diambil ulang untuk aturan K105(b)). BJTM (pindaian) dan NPL/BOPO/NIM BEKS tidak ada
  di lapisan teks — render dibaca ulang (`.uji-data/uji-g1/bukti/*.png`). Bukti: `bukti/verifikasi.txt`.
- ~~Impor~~ **selesai** — §11.5.

### 11.5 Impor ke basis data kerja (sesi 70, 29 Okt 2026 — pengguna: "Ya, impor")

| Langkah | Hasil |
|---|---|
| Berkas produksi | `.uji-data/mejasaham/konfigurasi/rasio-bank.csv`: sha256 lama `c5d833af…` dicocokkan dulu, 5 baris **ditambah di ujung** (BBCA/BRIS tidak ditulis ulang; skrip `.uji-data/uji-g1/tulis-produksi.py`) → 7 baris, sha256 `a29dbb49…` |
| Cadangan sebelum menulis | `.uji-data\mejasaham-cadangan\20261029T211841800910+0700` |
| Impor | keluar **0** · snapshot **25** · **176 baris baru** / 5213 sama · `rasio_bank` **2 → 7** |
| `v_rasio_bank_terkini` | lima baris baru persis seperti kandidat (bp): BEKS 451/3373/9147/319 · MEGA 156/2503/7265/436 · BNGA 142/2300/7547/356 · BDMN 160/2169/7806/427 · BJTM 438/2372/8214/590 |
| `--saring` (kualitas-nilai/v1) | **tidak berubah** — 4 lolos/4 dinilai, kandidat sama (AUTO 55,7 · PTBA 54,1 · ERAA 53,9 · LSIP 53,5) |
| Kriteria bank lima bank | **dipakai**: MEGA, BNGA, BDMN lolos keempatnya; BEKS gagal NPL/BOPO/NIM; BJTM gagal NPL. Kelimanya juga gagal kriteria lain (ROE 5 th, PER relatif, MA200, ADTV20) — **K68 tetap: tidak satu pun tertahan *hanya* oleh rasio bank** |
| Integritas | `PRAGMA integrity_check` = `ok`; `user_version` 18 |

**Efek samping (dilaporkan, bukan diperbaiki diam-diam):** 171 dari 176 baris baru adalah `notasi_khusus`
yang **hanya** berbeda di kolom `sumber` — isi (`tanggal_selesai`, `keterangan`) identik dengan revisi
terkini. Sebabnya: `--impor` diberi jalur **relatif** (`.uji-data/mejasaham/konfigurasi`), sehingga labelnya
`impor berkas: .uji-data\mejasaham\konfigurasi`, sedangkan refresh memakai jalur **absolut** (T88); sejak T100
"sudah ada" dibandingkan per sumber, jadi dua ejaan folder yang sama dianggap dua sumber. Pakai jalur
absolut untuk `--impor` folder konfigurasi kerja. Bukti: `.uji-data/uji-g1/bukti/` (`impor.txt`,
`db-sebelum.txt`/`db-sesudah.txt`, `notasi-171.txt`, `saring-sesudah.txt`, `kriteria-sesudah.txt`,
`integritas.txt`, `rasio-bank-sebelum.csv`).

---

## 12. Gelombang 2 perluasan: 5 bank otomatis (sesi 70, 29 Okt 2026)

**Status: TERVERIFIKASI ULANG (K83) DAN SUDAH DIIMPOR (snapshot 26, 29 Okt 2026 23.4x) — U40 → K106; lihat §12.4.** Pola sama dengan §11: berhenti di
berkas kandidat; `konfigurasi/rasio-bank.csv` dan basis data kerja **tidak** disentuh. Basis K105(a)
(set Bank/individual) berlaku — kelima bank kebetulan hanya menerbitkan satu set rasio.

### 12.1 Hasil

| Kode | Periode | `tgl_publikasi` | KPMM | NPL gross | BOPO | NIM | Dokumen |
|---|---|---|---|---|---|---|---|
| NISP | 30 Jun 2026 | 30 Jul 2026 (K106a) | 22,95 | 1,86 | 67,89 | 3,93 | Lap. Publikasi Triwulan II 2026, hlm. 7 |
| BVIC | 30 Sep 2026 | 28 Okt 2026 | 22,07 | 3,36 | 92,90 | 2,47 | Lap. Keuangan Publikasi Sep 2026 (poster) |
| BCIC | 30 Jun 2026 | 11 Agu 2026 (K106a) | 14,53 | 2,78 | 94,00 | 2,11 | Lap. Keuangan Juni 2026, hlm. 7 |
| AGRO | 30 Sep 2026 | 29 Okt 2026 | 42,35 | 2,53 | 98,59 | 5,83 | Lap. Keuangan Triwulan III Sep 2026 (poster) |
| BINA | 30 Jun 2026 | 28 Okt 2026 (K106b) | 15,26 | 4,11 | 92,04 | 2,36 | Lap. Keuangan Triwulan 2 2026 (poster) |

Setiap angka dibaca dari **render** (potongan PNG di `.uji-data/riset-idx/rasio-bank/png/`, nama berawalan
kode kecil). BVIC tidak punya angka tabel di lapisan teks — render saja. URL, kutipan, dan alasan pemilihan
ada di `kandidat-rasio-bank.csv`; SHA-256 di `manifest-unduhan.txt`. `uji-baca-kandidat.py`: **LULUS, 12
baris** (7 lama + 5 baru), dengan nilai basis poin kelima bank baru kini ikut diperiksa (`HARAP`) — sempat
**GAGAL** sekali karena salah ketik nilai harapan BINA (2304, seharusnya 1526), bukti bahwa pemeriksaannya
membedakan.

### 12.2 Yang ditemukan

1. **Tanggal publikasi lemah (U40).** NISP dan BCIC tidak mencetak tanggal; NISP juga tanpa `Last-Modified`.
   BINA: tanda tangan 29 Jul, halaman PSP 15 Agu, PDF dibuat 19 Agu, `Last-Modified` 28 Okt — K105(b)
   harfiah memberi 28 Okt. Kandidat memakai bukti terbit paling akhir; pilihan lain dicatat di `keterangan`.
2. **KPMM AGRO sama di dua kolom (42,35%)** — diperiksa dari modal ÷ ATMR: 2.899.720/6.847.022 dan
   3.352.630/7.915.840 sama-sama 42,35%. Kebetulan, bukan salah cetak.
3. **Tiga bank sudah 30 Sep 2026** (BVIC 28 Okt, AGRO 29 Okt); NISP TW III belum terbit (URL Q3 → 404).
4. **Yang dilewati di gelombang ini:** **BJBR** — `bankbjb.co.id` membalas halaman "Under Maintenance";
   **PNBN** dan **NOBU** — `paninbank.com` dan `banknobu.com` membalas halaman 114 byte yang mengalihkan
   ke `/lander` (pola domain parkir; K79 dulu mencatat keduanya "menjawab"); **BTPN** — robots `smbc.co.id`
   membalas HTML (aturan §11: tidak dianggap boleh); **BNII** — sertifikat `maybank.co.id` gagal diverifikasi
   (K79). Kelimanya tetap di sisa sasaran, belum dinyatakan "tidak terbaca".
5. **Katalog berbasis JavaScript** (OCBC, Bank Raya) dibuka lewat peramban bawaan aplikasi Claude untuk
   menemukan URL berkas; unduhannya tetap lewat `unduh.py` + `cek-robots.py` (robots host berkas
   diperiksa: cdn1.ocbc.id 200, victoriabank.co.id 404 = tidak ada larangan, jtrustbank 200, bankraya 200,
   bankina 200).

### 12.3 Sisa

- 23 bank "otomatis" (33 − 10), termasuk lima yang dilewati di 12.2(4); 8 manual; 2 belum terukur.
- ~~Keputusan U40~~ **K106** (pengguna: "Setuju U40"): usulan dipakai apa adanya — tanggal kandidat tidak berubah.
- ~~Verifikasi ulang K83~~ **selesai**: `.uji-data/uji-g2/verifikasi.py` → keluar 0, seluruh sel cocok (hash = manifest,
  unduh ulang identik, 4 rasio + periode + `tgl_publikasi` + `sumber`, lapisan teks, dan dasar tanggal dihitung ulang dari
  `Last-Modified`/metadata PDF/siaran pers menurut K105(b)/K106). BVIC (angka hanya di render) dirender ulang dan dibaca
  lagi: `.uji-data/uji-g2/bukti/bvic-…-potong-0.01-0.78-0.43-0.87.png`. Bukti: `bukti/verifikasi.txt`.
- ~~Impor~~ **selesai** — §12.4.

### 12.4 Impor ke basis data kerja (sesi 70, 29 Okt 2026 — pengguna: "Ya, impor")

| Langkah | Hasil |
|---|---|
| Pemeriksaan penulis tunggal | tidak ada proses Python/MejaSaham yang berjalan sebelum menulis |
| Berkas produksi | `.uji-data/mejasaham/konfigurasi/rasio-bank.csv`: sha256 lama `a29dbb49…` dicocokkan dulu, 5 baris **ditambah di ujung** (7 baris lama tidak ditulis ulang; `.uji-data/uji-g2/tulis-produksi.py`) → 12 baris, sha256 `8b597b32…` |
| Cadangan sebelum impor | `.uji-data\mejasaham-cadangan\20261029T234828321761+0700` |
| Impor (jalur **absolut**, T101) | keluar **0** · snapshot **26** · **5 baris baru** / 5389 sama · `rasio_bank` **7 → 12**. Efek samping gelombang 1 (171 baris `notasi_khusus` berlabel lain) **tidak terulang**: `notasi_khusus` tetap 19.758 |
| `v_rasio_bank_terkini` | lima baris baru persis seperti kandidat (bp): NISP 186/2295/6789/393 · BVIC 336/2207/9290/247 · BCIC 278/1453/9400/211 · AGRO 253/4235/9859/583 · BINA 411/1526/9204/236 (NPL/CAR/BOPO/NIM) |
| `--saring` (kualitas-nilai/v1) | **tidak berubah** — 4 lolos/4 dinilai, kandidat sama (AUTO 55,7 · PTBA 54,1 · ERAA 53,9 · LSIP 53,5) |
| Kriteria bank kelima bank | **dipakai**: NISP lolos keempatnya; AGRO gagal BOPO; BCIC gagal BOPO/NIM; BINA dan BVIC gagal NPL/BOPO/NIM; CAR lolos semua. Kelimanya juga gagal kriteria lain (MA200 semua; ADTV20 AGRO/BCIC/BINA/BVIC; ROE 5 th NISP) — **K68 tetap: tidak satu pun tertahan *hanya* oleh rasio bank** |
| Integritas | `PRAGMA integrity_check` = `ok`; `user_version` 18 |

Bukti: `.uji-data/uji-g2/bukti/` (`verifikasi.txt`, `db-sebelum.txt`/`db-sesudah.txt`, `cadangan.txt`, `impor.txt`,
`saring-sesudah.txt`, `kriteria-sesudah.txt`, `integritas.txt`, `rasio-bank-sebelum.csv`). **Jebakan kecil:**
`.uji-data/uji-g2/kriteria.py` (salinan pola gelombang 1) butuh `PYTHONPATH=.` bila dijalankan sebagai skrip.

---

## 13. Gelombang 3 perluasan: 5 bank otomatis (sesi 71, 30 Okt 2026)

**Status: TERVERIFIKASI ULANG (K83) DAN SUDAH DIIMPOR (snapshot 27, 30 Okt 2026 00.13) — U41 → K107; lihat §13.4.** Pola sama dengan §11–§12: berhenti di
berkas kandidat; `konfigurasi/`, basis data kerja `.uji-data/mejasaham`, dan kode aplikasi **tidak** disentuh.
Basis K105(a) (set Bank/individual) dan aturan tanggal K105(b)/K106 berlaku. Dua dari lima yang dilewati di
gelombang 2 kini terbaca (BNII, NOBU).

### 13.1 Hasil

| Kode | Periode | `tgl_publikasi` | KPMM | NPL gross | BOPO | NIM | Dokumen |
|---|---|---|---|---|---|---|---|
| BNII | 30 Jun 2026 | 30 Jul 2026 | 21,97 | 2,21 | 92,83 | 3,16 | LKP Triwulanan 30 Jun 2026, hlm. 10 (kolom INDIVIDUAL) |
| NOBU | 30 Jun 2026 | 31 Jul 2026 | 23,04 | 0,53 | 75,87 | 3,53 | Lap. Keuangan 30 Jun 2026 (poster) |
| MAYA | 30 Jun 2026 | 31 Jul 2026 | 11,07 | 4,02 | 98,93 | 2,31 | Publikasi Lap. Keuangan 30 Jun 2026 (poster) |
| AMAR | 30 Jun 2026 | 30 Jul 2026 | 89,86 | 8,96 | 84,17 | 21,91 | Lap. Keuangan Triwulan 30 Jun 2026, hlm. 10 |
| BNBA | 30 Jun 2026 | 31 Jul 2026 | 71,54 | 5,29 | 86,31 | 4,11 | Lap. Keuangan Publikasi Juni 2026, hlm. 4 (pindaian) |

Setiap angka dibaca dari **render** (potongan PNG `.uji-data/riset-idx/rasio-bank/png/<kode kecil>-…`). MAYA
tidak punya angka tabel di lapisan teks dan BNBA pindaian tanpa lapisan teks — keduanya render saja. Tanggal:
semuanya tanggal tanda tangan; `Last-Modified` NOBU/MAYA/BNBA jatuh di hari yang sama, AMAR sehari sesudahnya,
BNII tanpa `Last-Modified` (metadata PDF 31 Jul) — tak satu pun melewati ambang 7 hari K105(b). Tak satu pun
sudah menerbitkan posisi 30 Sep 2026 per 30 Okt. URL, kutipan apa adanya, dan alasan pemilihan ada di
`kandidat-rasio-bank.csv`; SHA-256 di `manifest-unduhan.txt`. `uji-baca-kandidat.py`: **LULUS, 17 baris**
(12 lama + 5 baru), nilai basis poin kelima bank baru ikut diperiksa (`HARAP`).

### 13.2 Yang ditemukan

1. **Domain K79 keliru untuk beberapa bank** (U41a). `banknobu.com` dan `paninbank.com` (pengalih `/lander`) bukan
   situs bank: Nobu ada di **`nobubank.com`** (terbaca), Panin di **`panin.co.id`** (membalas **403** pada
   30 Okt). `bankccb.com` adalah *CCB Community Bank, Andalusia, AL* — bank AS, bukan MCOR (PT Bank China
   Construction Bank Indonesia; `idn.ccb.com` gagal SSL: *hostname mismatch*). `bankmayapada.co.id` tidak
   terjangkau, situs aktifnya **`bankmayapada.com`**. `smbc.co.id` kini berjudul "Home | SMBC India" dan
   `btpn.com` tidak ada di DNS — domain BTPN yang benar **belum** ditemukan, jadi BTPN tetap di sisa.
   Artinya vonis K79 (§10.2) untuk PNBN, NOBU, MCOR, MAYA, BTPN diukur atas domain yang salah.
2. **Tanggal tercetak lebih awal sehari dari berkasnya** (U41b). BNII (tanda tangan 30 Jul; PDF dibuat 31 Jul;
   tanpa `Last-Modified`) dan AMAR (tanda tangan 30 Jul; `Last-Modified` 31 Jul 07.20 GMT). K105(b) memberi
   tanggal tercetak (selisih ≤ 7 hari), dan kandidat memakainya — dicatat, bukan diubah diam-diam.
3. **Angka yang tidak lazim, dicek dan memang tercetak demikian:** AMAR NIM **21,91** dan KPMM **89,86**
   (bank pinjaman digital; 30 Jun 2025: 23,59 dan 119,48); BNBA KPMM **71,54** (sama dengan tabel KPMM hlm. 6);
   MAYA KPMM **11,07** (tabel KPMM: profil risiko 10,82%, CET 1 untuk *buffer* 0,25% sementara *conservation
   buffer* 2,500%). Juga di catatan Mayapada: opini audit atas 31 Des 2025 bertanggal 31 Jul 2026 dengan
   "paragraf penekanan suatu hal" — dicatat sebagai konteks, bukan ditafsirkan.
4. **Dua set rasio:** hanya BNII (individual 21,97/2,21/92,83/3,16 dipakai; konsolidasian 24,32/2,13/87,99/4,28
   di `keterangan`). MAYA dan BNBA mengosongkan/menghitamkan baris konsolidasi.
5. **Katalog berbasis JavaScript** (Maybank, Bumi Arta) dibuka lewat peramban bawaan hanya untuk menemukan URL;
   Bumi Arta menambahkan parameter `?csrt=` ke tautan — dibuang, berkas tetap terunduh utuh. Robots host berkas
   diperiksa: maybank.co.id 200, nobubank.com 200, bankmayapada.com 404, storage.googleapis.com 404,
   bankbba.co.id 404 (4xx = tidak ada larangan).
6. **Dilewati lagi:** **BJBR** — `bankbjb.co.id` masih "Under Maintenance"; **PNBN** — lihat (1), `panin.co.id`
   403; **BTPN** — lihat (1). Tidak ditebak.

### 13.3 Sisa

- **18** bank "otomatis" (33 − 15): ARTO, BABP, BANK, BBHI, BBKP, BBSI, BBYB, BGTG, BJBR, BKSW, BMAS, BSIM, BSWD,
  BTPN, MASB, MCOR, PNBN, PNBS. Dari pemeriksaan robots 30 Okt: BKSW dan BMAS masih membalas HTML (tidak dianggap
  boleh); MCOR butuh domain yang benar. 8 manual; 2 belum terukur.
- ~~Keputusan U41~~ **K107** (pengguna: "Setuju U41"): usulan dipakai apa adanya — domain dikoreksi secara tercatat
  (§13.2), tanggal kandidat tidak berubah.
- ~~Verifikasi ulang K83~~ **selesai**: `.uji-data/uji-g3/verifikasi.py` → keluar 0, seluruh sel cocok (hash = manifest,
  unduh ulang identik, 4 rasio + periode + `tgl_publikasi` + `sumber`, lapisan teks, dan dasar tanggal dihitung ulang dari
  `Last-Modified` menurut K105(b)/K107b). MAYA (angka hanya di render) dan BNBA (pindaian) dirender ulang dengan potongan
  baru dan dibaca lagi: `.uji-data/uji-g3/bukti/maya-…-potong-0.50-0.31-0.69-0.36.png`,
  `bnba-…-hal4-potong-0.05-0.12-0.95-0.35.png`. Bukti: `bukti/verifikasi.txt`.
- ~~Impor~~ **selesai** — §13.4.

### 13.4 Impor ke basis data kerja (sesi 71, 30 Okt 2026 — pengguna: "Ya, impor")

| Langkah | Hasil |
|---|---|
| Pemeriksaan penulis tunggal | tidak ada proses `python.exe`/`pythonw.exe` dan port 8765 bebas sebelum menulis |
| Berkas produksi | `.uji-data/mejasaham/konfigurasi/rasio-bank.csv`: sha256 lama `8b597b32…` dicocokkan dulu, 5 baris **ditambah di ujung** (12 baris lama tidak ditulis ulang — awalan byte identik dengan salinan sebelum; `.uji-data/uji-g3/tulis-produksi.py`) → 17 baris, sha256 `4f9beba8…` |
| Cadangan sebelum impor | `.uji-data\mejasaham-cadangan\20261030T001317283479+0700` |
| Impor (jalur **absolut**, T101) | keluar **0** · snapshot **27** · **5 baris baru** / 5394 sama · `rasio_bank` **12 → 17**; `notasi_khusus` tetap 19.758 |
| `v_rasio_bank_terkini` | lima baris baru persis seperti kandidat (bp, NPL/CAR/BOPO/NIM): BNII 221/2197/9283/316 · NOBU 53/2304/7587/353 · MAYA 402/1107/9893/231 · AMAR 896/8986/8417/2191 · BNBA 529/7154/8631/411 |
| Laporan mutu | sama dengan snapshot 26 kecuali satu catatan baru `snapshot_basi` (hari bursa terakhir 30 Okt, snapshot 29 Okt) — akibat impor lewat tengah malam, bukan akibat baris rasio |
| `--saring` (kualitas-nilai/v1) | **tidak berubah** — 4 lolos/4 dinilai, kandidat sama (AUTO 55,7 · PTBA 54,1 · ERAA 53,9 · LSIP 53,5) |
| Kriteria bank kelima bank | **dipakai**: NOBU lolos keempatnya; AMAR gagal NPL; BNBA gagal NPL/BOPO; BNII gagal BOPO/NIM; MAYA gagal keempatnya (CAR 11,07% < 14,00%). Kelimanya juga gagal ADTV20 dan MA200 — **K68 tetap: tidak satu pun tertahan *hanya* oleh rasio bank** |
| Integritas | `PRAGMA integrity_check` = `ok`; `user_version` 18 |

Bukti: `.uji-data/uji-g3/bukti/` (`verifikasi.txt`, `db-sebelum.txt`/`db-sesudah.txt`, `tulis-produksi.txt`, `cadangan.txt`,
`impor.txt`, `saring-sesudah.txt`, `kriteria-sesudah.txt`, `integritas.txt`, `rasio-bank-sebelum.csv`).

## 14. Gelombang 4 perluasan: 5 bank otomatis (sesi 72, 30 Okt 2026)

**Status: TERVERIFIKASI ULANG (K83) DAN SUDAH DIIMPOR (snapshot 28, 30 Okt 2026 00.42) — lihat §14.4.** Pola sama dengan §11–§13: berhenti di berkas
kandidat; `konfigurasi/`, basis data kerja `.uji-data/mejasaham`, dan kode aplikasi **tidak** disentuh. Basis K105(a)
(set Bank/individual), aturan tanggal K105(b)/K106, domain terkoreksi K107, dan K77 (bank syariah: NPF/NI tidak
dipetakan ke NPL/NIM) berlaku.

### 14.1 Hasil

| Kode | Periode | `tgl_publikasi` | KPMM | NPL gross | BOPO | NIM | Dokumen |
|---|---|---|---|---|---|---|---|
| ARTO | 30 Sep 2026 | 28 Okt 2026 | 27,54 | 0,87 | 89,53 | 8,60 | LK Publikasi 30 Sep 2026 (poster), "Rasio Kinerja (Bank)" |
| BANK | 30 Sep 2026 | 26 Okt 2026 | 38,43 | — (K77) | 95,80 | — (K77) | LK per 30 Sep 2026 (poster), Laporan Rasio Keuangan |
| BBYB | 30 Jun 2026 | 30 Jul 2026 | 50,23 | 2,99 | 82,31 | 13,92 | LK Publikasi 30 Jun 2026, hlm. 7 |
| BSIM | 30 Jun 2026 | 27 Okt 2026 (K105b) | 30,03 | 1,62 | 93,54 | 3,28 | Lap. Publikasi Triwulan Jun 2026 (poster) |
| BBSI | 30 Jun 2026 | 31 Jul 2026 | 36,84 | 3,04 | 91,13 | 19,10 | Lap. Publikasi Triwulan II 2026, hlm. 7 |

Setiap angka dibaca dari **render** (potongan PNG `.uji-data/riset-idx/rasio-bank/png/<kode kecil>-…`; poster ARTO, BANK,
BSIM dipotong dengan perbesaran 6×). Lapisan teks kelimanya memuat angka yang sama. URL, kutipan apa adanya, dan alasan
pemilihan ada di `kandidat-rasio-bank.csv`; SHA-256 di `manifest-unduhan.txt`. `uji-baca-kandidat.py`: **LULUS, 22 baris**
(17 lama + 5 baru), nilai basis poin kelima bank baru ikut diperiksa (`HARAP`).

### 14.2 Yang ditemukan

1. **BSIM: `Last-Modified` jauh sesudah tanda tangan.** Tanda tangan 'Jakarta, 31 Juli 2026', metadata PDF 30 Jul 2026,
   tetapi `Last-Modified` 'Mon, 26 Oct 2026 18:27:32 GMT' (27 Okt WIB) — selisih 88 hari. K105(b) dibaca harfiah seperti
   BINA (K106): kandidat memakai **27 Okt 2026**; tanggal tercetak tetap di `keterangan`. Akibatnya baris ini baru
   "diketahui" sejak 27 Okt (lebih konservatif untuk point-in-time).
2. **BANK (Aladin) bank syariah** — menerbitkan NPF gross 0,84, Net Imbalan 1,48, dan NOM 0,47. Menurut K77 ketiganya
   **tidak** diisi; BANK dinilai pada CAR dan BOPO saja, NPL/NIM "tidak dihitung" beserta sebabnya.
3. **Angka tidak lazim, dicek dan memang tercetak demikian:** NIM BBSI **19,10** (30 Jun 2025: 18,82) dan BBYB **13,92**
   (15,22) — bank digital; KPMM BBYB **50,23**.
4. **Domain:** `krombank.co.id` (K79) kini mengalihkan ke **`krom.id`**; robots `krom.id` diperiksa (200). Berkas Neo
   Commerce di host `www-cms.bankneo.co.id` (robots 200), Jago di `assets.jago.com` (404 = tidak ada larangan).
5. **Katalog berbasis JavaScript** (Jago, Sinarmas) dibuka lewat peramban bawaan hanya untuk menemukan URL; Neo Commerce
   memuat URL berkas di data JSON halamannya.
6. **Dilewati:** **BGTG** (Ganesha) — katalog terbaca, tetapi tombol "Unduh" memanggil API yang membalas 401 "Authentication
   required" bila dipanggil di luar alur halaman; tidak dipaksa. **BABP** — `mncbank.co.id` hanya menampilkan "Test Page for
   the HTTP Server on Red Hat Enterprise Linux". **BBHI** — robots `allobank.com` gagal (ConnectionResetError) = tidak
   diizinkan. **BMAS** dan **BSWD** belum menampakkan halaman publikasi (BSWD tanpa tautan di HTML awal).

### 14.3 Sisa

- **13** bank "otomatis" (18 − 5): BABP, BBHI, BBKP, BGTG, BJBR, BKSW, BMAS, BSWD, BTPN, MASB, MCOR, PNBN, PNBS. Catatan per
  30 Okt: `kbbank.co.id` (BBKP) kini membalas robots 200 dan punya halaman `/investor`; MASB (`bankmas.co.id`) tanpa
  tautan publikasi di beranda. 8 manual; 2 belum terukur.
- ~~Verifikasi ulang K83~~ **selesai** (pengguna: "Ya, verifikasi"): `.uji-data/uji-g4/verifikasi.py` → keluar 0, seluruh sel
  cocok (hash = manifest, unduh ulang identik, 4 rasio + periode + `tgl_publikasi` + `sumber`, BANK: NPL/NIM kosong menurut
  K77, lapisan teks, dan dasar tanggal dihitung ulang dari `Last-Modified` menurut K105(b) — BSIM selisih 88 hari → 27 Okt).
  Poster ARTO, BANK, BSIM dirender ulang dengan potongan baru dan dibaca lagi (dua potongan per bank, baris BOPO
  terpisah): `.uji-data/uji-g4/bukti/*-potong-*.png`. Bukti: `bukti/verifikasi.txt`.
- ~~Impor~~ **selesai** — §14.4.

### 14.4 Impor ke basis data kerja (sesi 72, 30 Okt 2026 — pengguna: "Ya, impor")

| Langkah | Hasil |
|---|---|
| Pemeriksaan penulis tunggal | tidak ada proses `python.exe`/`pythonw.exe` dan port 8765 bebas sebelum menulis |
| Berkas produksi | `.uji-data/mejasaham/konfigurasi/rasio-bank.csv`: sha256 lama `4f9beba8…` dicocokkan dulu, 5 baris **ditambah di ujung** (17 baris lama tidak ditulis ulang — awalan 9.594 byte identik dengan salinan sebelum; `.uji-data/uji-g4/tulis-produksi.py`) → 22 baris, sha256 `d02e3688…` |
| Cadangan sebelum impor | `.uji-data\mejasaham-cadangan\20261030T004151722246+0700` |
| Impor (jalur **absolut**, T101) | keluar **0** · snapshot **28** · **5 baris baru** / 5399 sama · `rasio_bank` **17 → 22**; `notasi_khusus` tetap 19.758 |
| `v_rasio_bank_terkini` | lima baris baru persis seperti kandidat (bp, NPL/CAR/BOPO/NIM): ARTO 87/2754/8953/860 · BANK —/3843/9580/— · BBYB 299/5023/8231/1392 · BSIM 162/3003/9354/328 · BBSI 304/3684/9113/1910 |
| Laporan mutu | sama dengan snapshot 27 (termasuk catatan `snapshot_basi` — hari bursa 30 Okt belum ada datanya) |
| `--saring` (kualitas-nilai/v1) | **tidak berubah** — 4 lolos/4 dinilai, kandidat sama (AUTO 55,7 · PTBA 54,1 · ERAA 53,9 · LSIP 53,5); emiten yang "tidak bisa disaring" turun **880 → 878** karena rasio bank kini tersedia |
| Kriteria bank kelima bank | **dipakai**: BBYB lolos keempatnya; ARTO gagal BOPO; BBSI gagal NPL/BOPO; BSIM gagal BOPO/NIM; BANK lolos CAR, gagal BOPO, NPL/NIM "tidak dilaporkan pada periode 2026-09-30" (K77, tidak dihitung, bukan nol). Kelimanya juga gagal MA200 (dan lainnya: ADTV20, ROE, PER relatif, kekuatan relatif) — **K68 tetap: tidak satu pun tertahan *hanya* oleh rasio bank** |
| Integritas | `PRAGMA integrity_check` = `ok`; `user_version` 18 |

Bukti: `.uji-data/uji-g4/bukti/` (`verifikasi.txt`, `db-sebelum.txt`/`db-sesudah.txt`, `tulis-produksi.txt`, `cadangan.txt`,
`impor.txt`, `saring-sesudah.txt`, `kriteria-sesudah.txt`, `integritas.txt`, `rasio-bank-sebelum.csv`). **Jebakan:**
`kriteria.py` butuh `PYTHONPATH=.` bila dijalankan dari Git Bash (tanpa itu `ModuleNotFoundError: mejasaham`).

## 15. Gelombang 5 perluasan: 4 bank otomatis (sesi 73, 30 Okt 2026)

**Status: TERVERIFIKASI ULANG (K83) DAN SUDAH DIIMPOR (snapshot 29, 30 Okt 2026 01.05) — lihat §15.4.** Pola sama dengan §11–§14: berhenti di berkas
kandidat; `konfigurasi/`, basis data kerja `.uji-data/mejasaham`, dan kode aplikasi **tidak** disentuh. Basis K105(a)
(set Bank/individual), aturan tanggal K105(b)/K106, domain terkoreksi K107, dan K77 (bank syariah) berlaku. Sasaran
5 dari 13; hanya **4** yang dokumennya bisa dicari tanpa menebak atau memaksa — sebab yang lain di §15.2(5).

### 15.1 Hasil

| Kode | Periode | `tgl_publikasi` | KPMM | NPL gross | BOPO | NIM | Dokumen |
|---|---|---|---|---|---|---|---|
| BBKP | 30 Jun 2026 | 18 Sep 2026 | 15,82 | 9,99 | 96,68 | 1,96 | LK Publikasi Triwulanan & Entitas Induk 30 Jun 2026 (diaudit), hlm. 9 |
| BTPN | 30 Jun 2026 | 31 Jul 2026 | 29,27 | 1,49 | 88,45 | 3,78 | Publikasi LK Triwulanan Jun 2026 (poster, render saja) |
| PNBS | 30 Sep 2026 | 28 Okt 2026 | 16,61 | — (K77) | 93,72 | — (K77) | LK posisi Triwulan 3 2026 (poster), Laporan Rasio Keuangan |
| BSWD | 30 Sep 2026 | 29 Okt 2026 | 83,52 | 4,93 | 71,11 | 4,18 | LK Publikasi 30 Sep 2026, hlm. 9 |

Setiap angka dibaca dari **render** (`.uji-data/riset-idx/rasio-bank/png/<kode kecil>-…`): BBKP `-hal9.png`; BTPN
`-hal1-potong-0.03-0.54-0.24-0.62.png` (tabel rasio, 8×) dan `-hal1-potong-0.48-0.67-0.97-0.70.png` (rasio KPMM
individual/konsolidasian); PNBS `-hal1-potong-0.80-0.50-0.99-0.62.png` (7×); BSWD `-hal9-potong-0.00-0.00-1.00-0.45.png`.
BTPN **tidak punya angka di lapisan teks** (hanya blok tanda tangan); tiga lainnya memuat angka yang sama di lapisan
teks. URL, kutipan apa adanya, dan alasan pemilihan ada di `kandidat-rasio-bank.csv`; SHA-256 di `manifest-unduhan.txt`.
`uji-baca-kandidat.py`: **LULUS, 26 baris** (22 lama + 4 baru), nilai basis poin keempat bank baru ikut diperiksa
(`HARAP`); keluaran di `bukti-uji-baca.txt`.

Dasar tanggal (K105(b): tanggal tercetak, kecuali `Last-Modified` > 7 hari sesudahnya) — tak satu pun melewati ambang:

| Kode | Tanda tangan | `Last-Modified` | Metadata PDF |
|---|---|---|---|
| BBKP | 18 Sep 2026 | 18 Sep 2026 12.47 GMT | 18 Sep 2026 18.53 WIB |
| BTPN | 31 Jul 2026 | 31 Jul 2026 02.42 GMT | 30 Jul 2026 10.17 WIB |
| PNBS | 28 Okt 2026 | — (URL dinamis) | 28 Okt 2026 17.30 WIB |
| BSWD | 29 Okt 2026 | 29 Okt 2026 13.11 GMT | 29 Okt 2026 09.47 UTC |

### 15.2 Yang ditemukan

1. **BBKP: posisi Juni terbit 18 Sep dan diaudit.** Kolom 30 Jun 2026 bertanda "Diaudit"; tanda tangan, `Last-Modified`,
   dan metadata PDF sama-sama 18 Sep 2026, jadi `tgl_publikasi` = 18 Sep menurut K105(b). Di katalog tidak tampak versi
   tak diaudit yang lebih awal. Berkas `1. LR_20260630_IND.pdf` di folder yang sama adalah *Leverage Ratio*, bukan rasio
   keuangan (tidak dipakai, tetap diunduh dan dicatat di manifest). Set individual dipakai (KPMM 15,82 = kolom
   INDIVIDUAL tabel KPMM hlm. 6; konsolidasian 17,00).
2. **BTPN: domainnya `smbci.com`.** PT Bank SMBC Indonesia Tbk (dulu BTPN) memakai `smbci.com` (robots 200). Ini
   melengkapi §13.2(1), yang mencatat `smbc.co.id` sebagai "SMBC India" dan domain BTPN "belum ditemukan". Poster
   konsolidasian satu halaman: tabel rasio satu set, cocok dengan kolom INDIVIDUAL tabel KPMM (29,27; konsolidasian 30,68).
3. **PNBS bank syariah** — menerbitkan NPF gross 3,07, Net Imbalan 2,24, dan NOM 0,50. Menurut K77 ketiganya **tidak**
   diisi (seperti BRIS dan BANK). URL unduhan berupa **token terenkripsi** dari katalog `pdsb.co.id/about/laporan_keuangan`
   (berubah tiap kali halaman dimuat), tanpa `Last-Modified`. Token yang dipakai diuji ulang bersama token baru dari
   halaman: keduanya memberi berkas **identik** (sha256 `6795ee2d…`, `filename="LK PT Bank Panin Dubai Syariah Tbk September
   2026.pdf"`), jadi verifikasi ulang K83 bisa memakai URL di berkas kandidat. Render halaman penuh tampak gelap (latar
   transparan); potongan `potong-pdf.py` (latar putih) yang dibaca.
4. **Angka tidak lazim, dicek dan memang tercetak demikian:** BBKP NPL gross **9,99** (30 Jun 2025: 10,08) dan BOPO 96,68
   (103,49); BSWD KPMM **83,52** (89,99) dan BOPO **71,11** (94,15), ROE 2,84 (0,40).
5. **Dilewati (tidak ditebak, tidak dipaksa):**
   - **BJBR**: `bankbjb.co.id` masih berjudul "Under Maintenance" (robots 404).
   - **MASB**: tab "Laporan Triwulan" di `bankmas.co.id` (robots 200) hanya menampilkan daftar laporan tahunan, dan
     HTML/`__NEXT_DATA__`-nya tidak memuat entri triwulan 2026.
   - **BBHI**: robots `www.allobank.com` kini 200, tetapi situsnya tidak punya halaman investor/publikasi. Sitemap
     memuat 14 URL produk/layanan, dan menu "Tentang Kami" tidak bertautan ke laporan. Robots `allobank.com` tanpa
     `www` masih gagal (ConnectionResetError).
   - **BGTG**: katalog terbaca, tetapi tombolnya masih "Unduh" tanpa `href`. Seperti gelombang 4 (API 401), tidak dipaksa.
   - **BABP**: `mncbank.co.id` masih halaman uji Red Hat, dan `bankmnc.co.id` tidak terjangkau.
   - **PNBN**: `panin.co.id` 403. `paninbank.co.id` dan `paninbanksyariah.co.id` tidak terjangkau.
   - **MCOR**: `idn.ccb.com` masih SSL *hostname mismatch*, dan `ccb.co.id` tidak ada di DNS.
   - **BKSW** (`qnb.co.id`) dan **BMAS** (`bankmaspion.co.id`): robots masih membalas HTML, jadi tidak dianggap boleh.

### 15.3 Sisa

- **9** bank "otomatis" (13 − 4): BABP, BBHI, BGTG, BJBR, BKSW, BMAS, MASB, MCOR, PNBN — semuanya terhalang sebab di
  §15.2(5), bukan belum dicoba. Gelombang berikut hanya berguna bila salah satu sebab itu berubah (situs BJBR pulih,
  katalog MASB terisi, dsb.). 8 manual; 2 belum terukur.
- **2 belum terukur, diukur ulang 30 Okt 2026 (sesi 74) — tetap tidak terukur:** INPC connect timeout 3/3 (https/http;
  `www.` tidak ada di DNS); SDRA `CERTIFICATE_VERIFY_FAILED` 3/3 (https, `www.` juga) dan http timeout. Verifikasi
  sertifikat tidak dimatikan. Bukti `.uji-data/uji-g6/bukti/ukur-ulang.txt`, skrip `.uji-data/uji-g6/ukur-ulang.py`.
- ~~Verifikasi ulang K83~~ **selesai** (pengguna: "Ya, verifikasi"): `.uji-data/uji-g5/verifikasi.py` → keluar 0, seluruh sel
  cocok (hash = manifest, unduh ulang identik — termasuk token PNBS, 4 rasio + periode + `tgl_publikasi` + `sumber`, PNBS:
  NPL/NIM kosong menurut K77, lapisan teks — BTPN hanya blok tanda tangan, dan dasar tanggal dihitung ulang dari
  `Last-Modified` menurut K105(b): selisih 0 hari untuk BBKP/BTPN/BSWD, PNBS tanpa `Last-Modified` → tercetak). Poster BTPN
  dan PNBS dirender ulang dengan potongan baru (dua potongan per bank, baris NPL/NIM/BOPO terpisah) dan dibaca lagi — angka
  sama: `.uji-data/uji-g5/bukti/*-potong-*.png`. Bukti: `bukti/verifikasi.txt`.
- ~~Impor~~ **selesai** — §15.4.

### 15.4 Impor ke basis data kerja (sesi 73, 30 Okt 2026 — pengguna: "Ya, impor")

| Langkah | Hasil |
|---|---|
| Pemeriksaan penulis tunggal | tidak ada proses `python.exe`/`pythonw.exe` dan port 8765 bebas sebelum menulis |
| Berkas produksi | `.uji-data/mejasaham/konfigurasi/rasio-bank.csv`: sha256 lama `d02e3688…` dicocokkan dulu, 4 baris **ditambah di ujung** (22 baris lama tidak ditulis ulang — awalan 12.236 byte identik dengan salinan sebelum; `.uji-data/uji-g5/tulis-produksi.py`) → 26 baris, sha256 `10dc5ef3…` |
| Cadangan sebelum impor | `.uji-data\mejasaham-cadangan\20261030T010531573049+0700` |
| Impor (jalur **absolut**, T101) | keluar **0** · snapshot **29** · **4 baris baru** / 5404 sama · `rasio_bank` **22 → 26**; `notasi_khusus` tetap 19.758 |
| `v_rasio_bank_terkini` | empat baris baru persis seperti kandidat (bp, NPL/CAR/BOPO/NIM): BBKP 999/1582/9668/196 · BTPN 149/2927/8845/378 · PNBS —/1661/9372/— · BSWD 493/8352/7111/418 |
| Laporan mutu | sama dengan snapshot 28 (dibandingkan baris per baris); yang berbeda hanya nomor snapshot dan jalur arsip, kini tercetak absolut |
| `--saring` (kualitas-nilai/v1) | **tidak berubah** — 4 lolos/4 dinilai, kandidat sama (AUTO 55,7 · PTBA 54,1 · ERAA 53,9 · LSIP 53,5); "tidak bisa disaring" **tetap 878**, karena keempat bank belum punya laporan fundamental (ROE 5t, PER/PBV relatif sektor tidak dihitung) |
| Kriteria bank keempat bank | **dipakai**: BSWD lolos keempatnya; BTPN gagal BOPO; BBKP lolos CAR, gagal NPL/BOPO/NIM; PNBS lolos CAR, gagal BOPO, NPL/NIM "tidak dilaporkan pada periode 2026-09-30" (K77, tidak dihitung, bukan nol). Keempatnya juga gagal ADTV20 (BBKP dan PNBS juga MA200) — **K68 tetap: tidak satu pun tertahan *hanya* oleh rasio bank** |
| Integritas | `PRAGMA integrity_check` = `ok`; `user_version` 18 |

Bukti: `.uji-data/uji-g5/bukti/` (`verifikasi.txt`, `db-sebelum.txt`/`db-sesudah.txt`, `tulis-produksi.txt`, `cadangan.txt`,
`impor.txt`, `saring-sesudah.txt`, `kriteria-sesudah.txt`, `integritas.txt`, `rasio-bank-sebelum.csv`). **Jebakan:**
keluaran CLI yang dialihkan ke berkas dari Git Bash memakai pengodean konsol (em dash jadi "�") — jalankan dengan
`PYTHONIOENCODING=utf-8` (dipakai untuk `saring-sesudah.txt`/`kriteria-sesudah.txt`; `impor.txt` masih berpengodean konsol).
