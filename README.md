# Meja Saham

Aplikasi lokal Windows untuk **screener, penilaian, dan meja keputusan saham IDX** —
pemakaian internal, satu pengguna. Antarmukanya **dasbor web lokal** yang hanya bisa dibuka
dari komputer ini (`http://127.0.0.1:8765`, K91).

Nilai utamanya bukan skornya, melainkan proses yang dipaksa terjadi **sebelum** order:
satu snapshot data dipakai semua layar, tesis + level pembatal wajib diisi sebelum kandidat
masuk watchlist, dan kalkulator risiko boleh menolak ukuran posisi yang melanggar batas.

## Status

**Fitur v0.1 sudah jalan; antarmukanya kini dasbor web lokal (K91, 28 Okt 2026)** — jendela
PySide6 dan EXE PyInstaller sudah dihapus. Daftar emiten diambil dari Master
File Efek KSEI (**973 saham biasa IDX**,
K12), harga 5 tahun lewat `--refresh`, dan seluruh layar PRD 11 — termasuk tindakan menulis —
sudah ada di dasbor web. Yang belum sepenuhnya terisi adalah **data yang hanya bisa disediakan
manusia** (fundamental/rasio bank untuk sebagian emiten, kalender 2021–2024, sebagian notasi).
Yang sudah ada: paket `mejasaham/`, satu titik masuk untuk dua mode, **lapisan basis data**
(`lokasi.py`, `skema.py`, `db.py` — SQLite WAL, skema berversi, tabel append-only, penulis
tunggal), **lapisan konfigurasi** (`konfigurasi.py` — parameter bursa bertanggal dari TOML ke
tabel), **lapisan ingesti** (`ingesti.py`, `pengambil.py`, `berkas.py`, `ksei.py`, `mutu.py`,
`arsip.py`, `pengatur.py`), **lapisan perhitungan** (`potret.py`, `penyesuaian.py`, `metrik.py`,
`saring.py`, `skor.py`, `risiko.py`, `posisi.py`, `jurnal.py`, `dasbor.py`), **ekspor & cadangan**
(`ekspor.py`, `cadangan.py`), dan **jendela** (`ui/`). Uji otomatisnya menjaga batas arsitektur
serta aturan datanya. Keputusan produk dan teknis ada di
[`docs/keputusan.md`](docs/keputusan.md) dan [`docs/arsitektur.md`](docs/arsitektur.md); tidak
ada pertanyaan yang masih memblokir.

| Tahap (PRD 16) | Status |
|----------------|--------|
| Tahap 0 — Fondasi data | **jalan** — daftar 973 emiten bisa diambil (K12), dan refresh nyata atas 916 emiten menghasilkan **999.421 bar harga, 5 tahun, 0 gagal**. Kode yang sumbernya menyatakan tidak diperdagangkan lagi dicatat sebagai lubang yang diketahui (K13), bukan kegagalan yang menahan snapshot. Yang belum: data yang hanya bisa disediakan manusia (kalender 2021–2024, sebagian notasi, fundamental/rasio bank untuk sebagian emiten) |
| Tahap 1 — Saring & skor | **jalan** — metrik 8.2, set bank, preset berversi, kriteria saring, skor z per sektor, peringkat. Faktor kualitas & nilai tetap "tidak dihitung" untuk emiten yang fundamental/rasio bank-nya belum ada — bukan diisi nol |
| Tahap 2 — Keputusan & risiko | **jalan** — kandidat & watchlist/tesis (F4), kalkulator risiko & rencana (F5), **manajemen posisi & ekuitas (F11)**, dan **jendela PySide6** untuk membaca maupun menulis: `--catat-transaksi`, `--posisi`, `--ubah-stop`, `--dasbor`, aksi korporasi pada posisi (split/reverse split, dividen, right issue — K28), risiko berjalan portofolio (AC-6), dan drawdown terkoreksi setoran/penarikan (AC-13) |
| Tahap 3 — Jurnal & tinjauan | **jalan** — **jurnal keputusan & rekap kepatuhan (F7)**, **ekspor CSV (F9)**, dan **cadangan/pemulihan (F12)**. Seluruh katalog pelanggaran PRD 9.8 (V1–V7) dihitung dari satu tempat per kode; rekapnya memuat kepatuhan, kelengkapan tesis, expectancy dalam R, dan drawdown. Impor, cadangan, daftar cadangan, `ubah-stop`, dan keputusan right issue juga tersedia dari jendela (K59 c) |
| Tahap 4 — Simulasi, uji & peringatan | belum mulai — masa simulasi, backtest tanpa lookahead, dan peringatan EOD ada di v0.2 (`docs/ideas.md`) |
| Tahap 5 — Pengemasan aplikasi | **diganti K91** — tidak ada lagi EXE; `MejaSaham.cmd` (klik-ganda) atau `python -m mejasaham` membuka dasbor web lokal. Butuh Python + `.venv` di mesin itu |

> **Ketentuan pemakaian sumber data (K7).** Pemeriksaan yang dituntut Q8 sudah dijalankan:
> Syarat Layanan Yahoo melarang pengambilan data otomatis "untuk tujuan apa pun tanpa izin
> tertulis sebelumnya", **tanpa pengecualian pemakaian pribadi**. Karena itu pemakaian
> yfinance di sini dicatat sebagai **risiko yang diterima secara sadar, bukan izin** — dengan
> label "tidak resmi" yang menempel di setiap baris dan setiap berkas arsip, jalur impor
> berkas sebagai warga kelas satu, dan evaluasi sumber resmi sebelum uang nyata. Rinciannya di
> [`docs/keputusan.md`](docs/keputusan.md) bagian 1.3.

## Lisensi dan batas publikasi

Kode dan dokumentasi asli MejaSaham memakai [lisensi MIT](LICENSE). Lisensi ini tidak
memberikan hak atas data pasar, laporan PDF, merek, atau materi pihak ketiga. Hak pemakaian
data mengikuti ketentuan masing-masing sumber; lihat juga [dokumentasi yfinance](https://ranaroussi.github.io/yfinance/).
Repositori publik tidak menyertakan basis data kerja, arsip hasil unduhan, konfigurasi aktif,
transaksi, atau kredensial. Berkas `*.contoh.csv`/`*.contoh.toml` adalah template;
draf PACK di `docs/` adalah catatan manual dengan rujukan KSEI, bukan paket data vendor.
Skor dan hasil aplikasi bukan nasihat investasi.

Persiapan dan cara mengunggah salinan tanpa riwayat pribadi dijelaskan di
[panduan publikasi](docs/publikasi.md).

## Isi repositori

| Berkas | Isi |
|--------|-----|
| [`AGENTS.md`](AGENTS.md) | Aturan kerja yang mengikat agen/kontributor |
| [`PRD-Screener-Saham-IDX-v1.3.docx`](PRD-Screener-Saham-IDX-v1.3.docx) | **Sumber kebenaran produk** (APA & MENGAPA) |
| [`_extract/prd_v1.3.txt`](_extract/prd_v1.3.txt) | Turunan PRD untuk memudahkan pembacaan (di-gitignore, dihasilkan ulang); diawali jejak asal SHA-256 `.docx` |
| [`tools/extract_docx.py`](tools/extract_docx.py) | Alat yang menghasilkan turunan di atas |
| [`MejaSaham.cmd`](MejaSaham.cmd) | Peluncur klik-ganda: menjalankan `.venv` + `python -m mejasaham` (dasbor web) atas data kerja `.uji-data\mejasaham`, kecuali `MEJASAHAM_DATA` sudah dipasang |
| [`docs/keputusan.md`](docs/keputusan.md) | Keputusan yang sudah diambil + pertanyaan yang masih memblokir |
| [`docs/lanjutan.md`](docs/lanjutan.md) | **Titik lanjut kerja** (turunan): keadaan terkini, perintah verifikasi, aksi berikutnya berurutan. Baca ini lebih dulu di sesi baru |
| [`docs/arsitektur.md`](docs/arsitektur.md) | HOW: batas modul, alur data, keputusan teknis |
| [`docs/skema-data.md`](docs/skema-data.md) | Entitas, kunci, aturan append-only/as-of |
| [`docs/konfigurasi.md`](docs/konfigurasi.md) | Parameter bursa & ambang — semua bertanggal dan dapat diubah |
| [`docs/ideas.md`](docs/ideas.md) | Fitur yang sengaja ditunda dari v0.1 |
| [`mejasaham/`](mejasaham) | Paket aplikasi: `__main__.py`, `cli.py`, `lokasi.py`, `skema.py`, `db.py`, `konfigurasi.py`, `ingesti.py`, `pengambil.py`, `berkas.py`, `ksei.py`, `kalender.py`, `sun.py`, `jenis.py`, `notasi.py`, `mutu.py`, `arsip.py`, `pengatur.py`, `potret.py`, `penyesuaian.py`, `metrik.py`, `saring.py`, `skor.py`, `kandidat.py`, `risiko.py`, `posisi.py`, `jurnal.py`, `ekspor.py`, `cadangan.py`, `dasbor.py`, `konteks_pasar.py`, `layar/` (tabel & permintaan tulis), `web/` (dasbor web lokal), `defaults/` |
| [`mejasaham/defaults/parameter-bursa.contoh.toml`](mejasaham/defaults/parameter-bursa.contoh.toml) | Template parameter bursa (B1–B9); seluruh entri dikomentari sampai diverifikasi |
| [`mejasaham/defaults/emiten.contoh.csv`](mejasaham/defaults/emiten.contoh.csv) | Template daftar emiten — **tanpa satu pun kode emiten**, karena semesta saham adalah keputusan pengguna |
| [`mejasaham/defaults/`](mejasaham/defaults) (sisanya) | Template kalender bursa, notasi khusus, imbal hasil SUN, aksi korporasi, harga, fundamental, rasio bank; plus daftar emiten awal (21 kode besar, bertanda belum diverifikasi) |
| [`tests/`](tests) | Uji batas arsitektur (tanpa Qt; inti tidak mengimpor dasbor web), konfigurasi bawaan, letak data runtime, basis data & migrasi, parameter bertanggal, ingesti/mutu/arsip, penyesuaian harga, metrik & potret, saring & skor, kandidat/risiko/posisi, jurnal & kepatuhan V1–V7, ekspor, cadangan, dan dasbor web (layar, alur tulis, CSRF) |
| [`requirements.txt`](requirements.txt) / [`requirements-dev.txt`](requirements-dev.txt) | Dependensi runtime / pengembangan |
| [`requirements.lock.txt`](requirements.lock.txt) | Versi runtime/pengembangan teruji; otomatis menjadi constraint untuk kedua berkas requirements |
| [`pytest.ini`](pytest.ini) | Konfigurasi pytest |

## Cara menjalankan

Pasang dependensi, lalu jalankan uji; aplikasi bisa dipakai lewat dasbor web atau baris perintah:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest
```

Status pemasangan: dependensi runtime hanya `yfinance==1.7.0` ([`requirements.txt`](requirements.txt));
dasbor memakai pustaka standar. `.venv` lama mungkin masih berisi PySide6/PyInstaller dari masa
jendela — aplikasi tidak memakainya lagi (suite lulus dengan impor keduanya diblokir).

**Dasbor web lokal (K91):**

```powershell
.\.venv\Scripts\python -m mejasaham                         # buka http://127.0.0.1:8765, hentikan dengan Ctrl+C
.\.venv\Scripts\python -m mejasaham --port 9000 --tanpa-peramban
```

Atau klik-ganda `MejaSaham.cmd` di akar repositori. Isinya: dasbor 11.1, screener 11.2, detail
emiten & tesis 11.3, kalkulator risiko 11.4, jurnal & kepatuhan 11.5, dan halaman impor &
cadangan — termasuk tindakan tulis (ubah stop, catat transaksi, keputusan right issue, simpan
rencana, catat jurnal, impor, cadangan), masing-masing lewat halaman konfirmasi sebelum menulis.
Tombol **Perbarui data** di dasbor menjalankan pembaruan harian (sama dengan `--refresh --saring`)
dengan halaman kemajuan, dan hanya memberi tahu bila data sudah dari hari bursa terakhir; cadangan
yang disimpan 3 terbaru dengan arsip snapshot ditautkan, bukan disalin (K92).
Bagian **Jadwal pembaruan data** di dasbor (juga di `--dasbor` dan sesudah `--refresh`) menyebut
data mana yang terbaru, jatuh tempo, atau belum bisa dinilai, beserta perintahnya (K93).
Server hanya menerima akses dari `127.0.0.1`. Pemulihan tetap hanya dari baris perintah
(`--pulihkan`). Mode kepala (`--refresh`, `--impor`, `--saring`, dan seluruh perintah lain)
berjalan tanpa dasbor, cocok untuk Task Scheduler.

Yang **sudah** bisa dipakai lewat baris perintah:

```powershell
# Muat parameter bursa dari TOML ke basis data, lalu laporkan keadaan tiap parameter.
# Berkas aktif dibuat otomatis di %LOCALAPPDATA%\MejaSaham\konfigurasi\ bila belum ada.
.\.venv\Scripts\python -m mejasaham --muat-konfigurasi

# Ambil data EOD, periksa mutunya, tulis snapshot, lalu arsipkan. Tanpa jendela (AC-11).
# Butuh konfigurasi\emiten.csv — lihat catatan di bawah.
.\.venv\Scripts\python -m mejasaham --refresh

# Impor data dari berkas CSV (kalender bursa, notasi khusus, SUN, harga, ...).
.\.venv\Scripts\python -m mejasaham --impor "$env:LOCALAPPDATA\MejaSaham\konfigurasi"

# Ambil daftar emiten dari Master File Efek KSEI (bulanan, resmi) -> emiten.csv (K12).
# Kolom sektor IDX-IC, papan, jenis, dan free float SENGAJA dikosongkan: tidak ada di berkas
# KSEI, dan mengisinya berarti mengarang. Berkas yang sudah ada tidak ditimpa tanpa
# --timpa-emiten.
.\.venv\Scripts\python -m mejasaham --ambil-emiten

# Ambil berkas bulan tertentu (tanggalnya menempel di nama berkas KSEI).
.\.venv\Scripts\python -m mejasaham --ambil-emiten --tanggal-master 2026-09-30

# Ambil kurva imbal hasil SBN dari halaman HPW PHEI -> imbal-hasil-sun.csv (K16).
# Yang ditulis: SUN 10 tahun, kolom "Today", bertanggal menurut sumbernya sendiri.
# Perintah ini MENAMBAH satu baris dan tidak menimpa baris lain di berkas itu, jadi riwayat
# yang Anda isi sendiri tetap aman. Panggil --impor sesudahnya untuk masuk ke basis data.
.\.venv\Scripts\python -m mejasaham --ambil-sun

# Coba alur ingesti tanpa daftar KSEI (21 kode besar, BELUM diverifikasi).
.\.venv\Scripts\python -m mejasaham --emiten-awal

# Simpan/segarkan preset bawaan (dua ember K1), lalu lihat daftarnya.
.\.venv\Scripts\python -m mejasaham --preset-bawaan

# Jalankan saringan + skoring preset pada snapshot terakhir (F2/F3, tanpa jendela).
# Bawaannya preset 'kualitas-nilai'; pilih lain dengan --preset momentum/v1.
.\.venv\Scripts\python -m mejasaham --saring --teratas 20

# Periksa satu emiten: seluruh kriterianya, beserta alasan lolos/gagal.
# Catatan: --kode TIDAK menyimpan hasilnya, karena peringkatnya parsial.
.\.venv\Scripts\python -m mejasaham --saring --kode BBCA,TLKM,GOTO

# Bila basis data memuat lebih dari satu label `sumber` harga (harga pembanding PRD 7.3),
# --saring membaca SATU label saja — yang riwayatnya terbanyak — dan menyebutkannya.
# Label lain dipakai dengan --sumber; tanpa itu, dua sumber bercampur dalam satu deret.
.\.venv\Scripts\python -m mejasaham --saring --sumber "nama label sumber"

# --- F11: setelah eksekusi di sekuritas (PRD 9.1 langkah 9) -------------------------------
# Catat transaksi. --mode WAJIB (simulasi/nyata): metrik kedua mode dilaporkan terpisah.
# Batas kas & ekuitasnya berasal dari --ekuitas-harian; stop posisi diambil dari rencana
# yang dieksekusi (--id-rencana) atau dari stop awal tesisnya.
.\.venv\Scripts\python -m mejasaham --catat-transaksi TLKM --aksi beli --lembar 10800 `
    --harga 2320 --mode nyata --id-rencana 1

# Lihat posisi aktif: harga rata-rata, stop terkini, risiko terbuka, hasil belum terealisasi.
.\.venv\Scripts\python -m mejasaham --posisi
.\.venv\Scripts\python -m mejasaham --posisi-semua      # termasuk yang ditutup + transaksinya

# Stop boleh dinaikkan (trailing). Menurunkannya tetap boleh, tetapi tercatat sebagai V5.
.\.venv\Scripts\python -m mejasaham --ubah-stop --id-posisi 1 --stop 2180 --alasan "trailing"

# Jual (sebagian atau seluruhnya; seluruhnya menutup posisinya).
.\.venv\Scripts\python -m mejasaham --catat-transaksi TLKM --aksi jual --lembar 5000 `
    --harga 2360 --mode nyata

# --- aksi korporasi pada posisi (PRD 9.11; split, dividen, right issue) -------------------
# Split/reverse split TIDAK perlu dicatat di posisi: lembar, harga rata-rata, dan stop
# disesuaikan otomatis saat dibaca, dengan basis tanggal stop disimpan di `tgl_stop`.
# Dividen dihitung dari aksi_korporasi x lembar pada tanggal ex-date, tampil di --posisi
# dan --dasbor sebagai suku terpisah (bruto; pajaknya tidak dihitung aplikasi).
# Right issue: lihat haknya beserta tenggat, lalu catat keputusannya.
.\.venv\Scripts\python -m mejasaham --hak-right-issue
.\.venv\Scripts\python -m mejasaham --putuskan-right-issue BBCA --tanggal-aksi 2026-09-15 `
    --keputusan jual_hmetd --lembar 400 --harga 300 --biaya 500
# `--keputusan tebus` menuntut --id-transaksi: menebus = membeli lembar, dan lembarnya hanya
# punya satu tempat — `transaksi`. Catat dulu transaksinya, lalu sebutkan id-nya.

# Ekuitas harian + arus dana (setoran positif / penarikan negatif; 0 = memang tidak ada),
# lalu drawdown terkoreksi: setoran & penarikan tidak terbaca sebagai hasil (AC-13).
.\.venv\Scripts\python -m mejasaham --ekuitas-harian 250000000 --kas 120000000 --arus-dana 0
.\.venv\Scripts\python -m mejasaham --drawdown

# Satu halaman harian (PRD 11.1): keadaan data, watchlist, posisi, risiko berjalan +
# batasnya, ekuitas & drawdown, kandidat tersimpan, dan daftar TINDAKAN MENUNGGU (PRD 9.11).
.\.venv\Scripts\python -m mejasaham --dasbor

# --- F7: jurnal keputusan & rekap kepatuhan (PRD 9.8, 11.5, 13.1/13.2) -------------------
# Satu baris jurnal per TRANSAKSI (keputusan yang tercatat), beserta pelanggaran V1-V7 yang
# menempel padanya. Tiap kode dibaca dari SATU tempat: V1/V2/V6 dari baris transaksi, V5 dari
# baris posisi, V3/V4/V7 diturunkan dari rencana + harga + revisi tesis.
.\.venv\Scripts\python -m mejasaham --jurnal
.\.venv\Scripts\python -m mejasaham --jurnal --bulan 2026-10 --kode TLKM

# Rekap kepatuhan: jumlah keputusan, kepatuhan (PRD 9.8), pelanggaran per kode, kelengkapan
# tesis (13.1), expectancy dalam R per putaran tertutup (13.2), dan drawdown berjalan.
# Di bawah 30 putaran tertutup, angkanya disebut "belum dapat dinilai" beserta sebabnya.
.\.venv\Scripts\python -m mejasaham --rekap-kepatuhan

# Tulis catatan jurnal: alasan, pelajaran, tanggal tinjau, tanda selesai (PRD 11.5).
# Menambah REVISI, tidak menimpa (PRD 9.8), dan tidak memblokir apa pun (K34).
.\.venv\Scripts\python -m mejasaham --jurnal-catat 3 --alasan "sesuai rencana" `
    --pelajaran "stop terlalu jauh" --tanggal-tinjau 2026-11-10
```

Untuk metrik kualitas dan nilai (ROE, DER, PER, PBV, …) aplikasi butuh
`fundamental.csv` dan `rasio-bank.csv` di folder konfigurasi; tanpanya, faktor itu berstatus
"tidak dinilai" beserta alasannya — bukan diisi nol.

Selama parameter bursa belum diisi dari pengumuman resmi, `--muat-konfigurasi` melaporkan
semuanya "belum terverifikasi" dan keluar dengan kode 0 — itu keadaan yang sah, bukan
kegagalan. Fitur yang bergantung padanya nanti **menolak menghitung**, bukan memakai angka
tebakan.

### Yang perlu Anda siapkan sebelum `--refresh` berguna

1. **Daftar emiten** — kini bisa diambil otomatis: `--ambil-emiten` menulis
   `%LOCALAPPDATA%\MejaSaham\konfigurasi\emiten.csv` dari Master File Efek KSEI (**973 saham
   biasa IDX**, terverifikasi 9 Okt 2026). Aplikasi tetap **tidak** mengarang daftar ini, dan
   `--emiten-awal` masih tersedia sebagai 21 kode besar untuk mencoba alur. Yang ikut terisi:
   kode, nama, jumlah saham, dan **tanggal pencatatan** (kolom `Listing Date` — 888 dari 973;
   sisanya kosong di sumbernya, dan kolom kosong berarti "tidak dinyatakan", bukan nol).
   **Yang belum ada di berkas KSEI:** sektor IDX-IC dan papan pencatatan — isi sendiri bila Anda
   punya sumbernya; sampai terisi, kriteria yang memakai statistik sektor memakai statistik
   seluruh semesta likuid dan menyebut alasannya. (Arti nama kolom `tanggal_notasi` **sudah
   dikonfirmasi** 9 Okt 2026 sebagai **tanggal pencatatan saham** — K15.)
2. **Kalender bursa** ke `kalender-bursa.csv` — tanpa ini peringatan snapshot basi (AC-8)
   belum bisa dihitung, dan aplikasi akan mengatakannya apa adanya. Kini bisa diambil otomatis
   dengan `--ambil-kalender`: **2025 (25 libur), 2026 (22), 2027 (20)**. Tahun 2025 diambil dari
   revisi pengumuman KSEI yang lebih lama, dan itu hanya dilakukan karena seluruh tanggalnya
   **terbukti identik** dengan revisi terakhirnya (K17) — syaratnya diperiksa, bukan diandaikan.
   Tahun **2021–2024** sudah tidak tersedia di halaman KSEI (404).
3. **Notasi khusus/suspensi** ke `notasi-khusus.csv` — **satu-satunya berkas yang benar-benar
   tidak punya sumber terjangkau**: seluruh jalur `idx.co.id` menolak akses otomatis (HTTP 403).
4. **Imbal hasil SUN** ke `imbal-hasil-sun.csv` — kini bisa diambil otomatis dengan `--ambil-sun`
   (kurva imbal hasil SBN dari halaman HPW **PHEI**, K16). Tanpa ini metrik "imbal hasil laba −
   SUN" berstatus "tidak dihitung".
5. **Fundamental** ke `fundamental.csv` (dari laporan keuangan yang Anda unduh) dan **rasio
   bank** ke `rasio-bank.csv`. Keduanya wajib menyatakan `mata_uang` dan `satuan_uang`; tanpa
   itu metrik kualitas & nilai berstatus "tidak dihitung". Diperiksa 9 Okt 2026: **tidak ada**
   sumber resmi yang bisa diambil otomatis untuk keduanya (IDX 403; KSEI tidak menerbitkan laba,
   ekuitas, atau arus kas) — ini pekerjaan manusia, dan `--saring` akan berhenti di "0 kandidat"
   sampai berkasnya ada.

Seluruh template berkas itu dibuat otomatis saat `--refresh` pertama dijalankan.

> **Satu hal yang perlu Anda tahu sebelum refresh pertama (temuan 9 Okt 2026).** Daftar KSEI
> memuat kode yang **masih tercatat tetapi tidak diperdagangkan lagi**. Pada percobaan nyata atas
> 973 kode, **57 kode (5,9%)** dijawab sumber harga "No data found, symbol may be delisted",
> sehingga gerbang PRD 9.3 (gagal >5%) **menolak menerbitkan snapshot** — dan itu memang
> perilakunya, bukan kerusakan. Sejak **K13** (9 Okt 2026) kegagalan itu dibedakan: kode yang
> sumbernya sendiri menyatakan tidak punya data dihitung sebagai **lubang yang diketahui** dan
> tidak lagi memblokir snapshot, sedangkan kegagalan sementara tetap dihitung terhadap ambang 5%.
> Kode mati itu tetap dilaporkan (peringatan, temuan mutu `tidak_diperdagangkan`, catatan
> snapshot) — jadi membuangnya dari `emiten.csv` adalah pilihan, bukan keharusan. Perlu diketahui
> juga: `--refresh` menulis seluruh hasilnya dalam satu transaksi, jadi snapshot yang ditolak
> berarti **tidak ada data yang tersimpan** dan unduhan berikutnya mengulang dari awal.
>
> Folder uji itu dibuat dengan `--folder-data .uji-data` — cara yang sama bisa Anda pakai untuk
> mode portabel, tanpa menyentuh `%LOCALAPPDATA%\MejaSaham`.

## Cakupan

**Termasuk v0.1:** ingesti & validasi data EOD, penyaringan + preset berversi, skoring
z per sektor, watchlist & tesis, kalkulator risiko, jurnal & kepatuhan, ekspor CSV,
ekuitas harian & drawdown, cadangan & pemulihan, dan dasbor web lokal (K91).

**Di luar cakupan sama sekali:** eksekusi order otomatis, data real-time/order book,
multi-pengguna, awan, seluler. Lihat [`docs/ideas.md`](docs/ideas.md) untuk yang ditunda.

## Batas hukum

Tanpa eksekusi order otomatis, tanpa pengelolaan dana pihak lain, tanpa penyebaran data
berlisensi. Isi aplikasi dan ekspornya **bukan nasihat investasi**. Data dari sumber tidak
resmi (mis. yfinance) dipakai untuk keperluan pribadi dan selalu diberi label "tidak resmi".
