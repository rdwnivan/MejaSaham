# Riset sumber data resmi untuk menutup kekurangan MejaSaham

**Diakses 11 Okt 2026.** Fokus: sumber primer yang dapat memperbaiki klasifikasi emiten, suspensi/UMA, kalender, harga pembanding, dan fundamental. Sumber resmi memberi fakta dan dokumen; otomatisasi tetap harus menolak data yang tidak lengkap atau format yang berubah.

## Ringkasan rekomendasi

| Kebutuhan | Sumber terbaik yang ditemukan | Status untuk MejaSaham | Langkah yang disarankan |
|---|---|---|---|
| Sektor dan klasifikasi IDX-IC | Daftar Saham + profil perusahaan resmi IDX | Halaman dapat diakses; tombol unduh ada, endpoint stabil belum dibuktikan | Unduh XLSX dari halaman Daftar Saham, arsipkan mentah bertanggal, impor `sektor_idx_ic` dan `papan`. Profil emiten menyediakan sektor sampai subindustri. Untuk `jenis=bank_keuangan`, petakan hanya label yang jelas menyebut bank; sektor Financials juga mencakup asuransi, pembiayaan, investasi, dan holding. |
| Suspensi dan UMA | API berita/pengumuman resmi IDX + dokumen pengumuman | API sudah dipakai aplikasi; pengumuman multi-kode yang pemetaan PDF pindainya belum tuntas tetap menjadi celah | Pertahankan API sebagai jalur utama. Untuk setiap berita multi-kode, verifikasi PDF pengumuman satu per satu dan tambahkan kode yang disebut. Jangan menyatakan daftar lengkap sebelum seluruh 56 dokumen terdahulu ditinjau. |
| Kalender 2026 | Pengumuman BEI yang ditindaklanjuti KSEI | **Sudah tersedia dan sudah dimuat**; CSV lokal mencakup sampai 2027 | Tidak perlu mencari kalender lain. Pada snapshot Minggu, 11 Okt 2026, 09 Okt adalah hari bursa terakhir yang telah terjadi; pesan “kalender berhenti di 09 Okt” tidak membuktikan cakupan CSV berhenti di sana. Bedakan cakupan kalender dari hari bursa terakhir yang telah lewat. |
| Harga pembanding | Ringkasan Saham / data statistik resmi IDX | Tampilan resmi menyediakan harga dan volume harian serta tombol unduh. Ketersediaan arsip harian yang dapat diambil otomatis belum dipastikan | Gunakan sebagai benchmark cek mingguan atas 20 saham likuid. Unduh hasil resmi dan bandingkan tanggal, OHLC/penutupan, volume, serta aksi korporasi. Bila butuh arsip/otomatisasi penuh, minta penawaran lisensi data IDX; jangan anggap API gratis tersedia. |
| Fundamental resmi | IDX Financial Data and Ratio + Laporan Keuangan dan Tahunan/XBRL | IDX menyediakan unduhan Excel bulanan untuk metrik inti, serta filing per emiten/periode dengan XLSX dan `inlineXBRL.zip` | Gunakan tabel Excel resmi untuk metrik cakupannya; ambil filing XBRL resmi untuk pos yang tidak ada di ringkasan, khususnya rasio bank. Simpan tanggal publikasi, periode, URL dan tag/halaman bukti. |

## 1. Sektor dan jenis emiten

IDX menyatakan klasifikasi industri perusahaan tercatat bernama **IDX-IC**, berlaku sejak 25 Januari 2021. Halaman [Daftar Saham IDX](https://www.idx.id/id/data-pasar/data-saham/daftar-saham) menyediakan pilihan Sektor/Papan dan tombol **Unduh**; [profil perusahaan tercatat](https://block.idx.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/KAQI) menampilkan sektor, subsektor, industri, subindustri, papan, dan tanggal pencatatan. Ini sumber yang tepat untuk `sektor_idx_ic` dan `papan`. Halaman daftar saham berhasil diminta dari lingkungan ini dengan HTTP 200 pada 11 Okt 2026; URL unduhannya belum diuji.

KSEI juga menyediakan [Unduh Master File Efek](https://web.ksei.co.id/archive_download/master_securities) untuk identitas efek, tetapi berkas itu bukan klasifikasi IDX-IC. Gunakan KSEI untuk kode/nama/identitas efek, bukan sebagai pengganti sektor BEI.

**Dapat diunduh:** tombol unduh terlihat pada halaman Daftar Saham; URL file tetap yang bisa dipanggil tanpa sesi belum terverifikasi. Untuk implementasi awal, unduh manual dari halaman resmi, catat tanggal unduh dan nama file sumber, lalu impor. Otomatisasi baru layak setelah endpoint dan skema file dipastikan. Sektor IDX `Financials` terlalu luas untuk menyimpulkan semua konstituennya bank: IDX menyebut bank, pembiayaan konsumen, modal ventura, jasa investasi, asuransi, dan holding sebagai bagian sektor keuangan. Gunakan subsektor/industri profil untuk mengidentifikasi bank; kalau labelnya belum jelas, jangan menurunkan `jenis`. `siklikal_komoditas` tetap memerlukan penilaian manusia sesuai K21.

## 2. Suspensi, UMA, dan multi-kode

Halaman resmi [Pengumuman IDX](https://www.idx.id/id/berita/pengumuman) adalah indeks dokumen pengumuman; IDX menyatakan data halaman itu hanya tiga tahun terakhir dan riwayat lebih tua diarahkan ke TICMI. Modul yang kini ada sudah menggunakan endpoint resmi yang ditemukan pada JavaScript situs IDX: [`GetSuspension`](https://www.idx.id/primary/NewsAnnouncement/GetSuspension) dan [`GetUma`](https://www.idx.id/primary/NewsAnnouncement/GetUma). Endpoint ini adalah fakta implementasi di `mejasaham/notasi.py`; ini bukan dokumentasi API publik dengan kontrak stabil, sehingga validasi bentuk, jumlah rekaman, dan tanggal tetap wajib.

Masalah tersisa bukan ketiadaan data suspensi tunggal: menurut keadaan proyek, API menghasilkan 963 riwayat suspensi berkode tunggal dan 1.191 baris UMA, tetapi 56 pengumuman suspensi dengan lebih dari satu kode dan 40 pembukaan kembali belum terpetakan penuh. Indeks pengumuman IDX menyediakan dokumen per pengumuman; setiap lampiran multi-kode perlu dibaca untuk mengambil seluruh kode. PDF pindai tidak aman diproses dengan OCR tanpa tinjauan manusia. Buat daftar kerja berisi nomor pengumuman, tautan PDF, semua kode hasil tinjauan, status suspensi, dan tanggal efektif; simpan hasil sebagai revisi append-only. Jangan perlakukan “suspensi > 6 bulan” sebagai daftar suspensi aktif lengkap: halaman [Suspensi Lebih dari 6 Bulan](https://www.idx.co.id/id/perusahaan-tercatat/suspensi-lebih-dari-6-bulan/) hanya mencakup kelompok durasi tersebut.

## 3. Kalender perdagangan 2026

KSEI mempublikasikan [Jadwal Operasional dan Libur](https://web.ksei.co.id/services/schedule-c-best-instruction), termasuk tautan [Kalender Libur KSEI 2026](https://web.ksei.co.id/files/1767843003_Penyesuaian_Pengumuman_Hari_Libur_dan_Cuti_Bersama_PT_KSEI_Ta....pdf). PDF menyebut pengumuman kalender libur Bursa IDX No. PENG-00171/BEI.POP/09-2025 sebagai dasar dan menyatakan tanggal dapat disesuaikan bila ada perubahan dari BEI/BI. Lampirannya memuat 22 tanggal libur/cuti pada 2026.

Menurut `docs/lanjutan.md`, aplikasi sudah mengambil kalender 2025–2027 dari KSEI dan menghitung hari bursa, sehingga kekurangan kalender 2026 tampaknya **sudah ditutup**. Simpan PDF resmi sebagai bukti sumber dan perbarui hanya bila ada ralat/pengumuman susulan. KSEI mengumumkan hari operasional KSEI, bukan selalu keseluruhan kalender perdagangan dalam bentuk daftar hari bursa; gunakan pengumuman BEI yang dirujuk sebagai otoritas jadwal perdagangan.

## 4. Harga sumber kedua

Halaman resmi [Ringkasan Saham IDX](https://www.idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/) menampilkan tanggal perdagangan terakhir, open, high, low, close, volume, nilai, frekuensi, dan tombol **Unduh**. Halaman [Digital Statistic: Daily IDX Indices](https://www.idx.co.id/id/data-pasar/laporan-statistik/digital-statistic/monthly/stock-price-index/daily-idx-indices) menyediakan unduhan PDF/Excel untuk indeks; halaman itu berguna sebagai benchmark indeks, bukan harga tiap emiten.

Ini dapat menjadi pembanding yang independen terhadap harga yfinance pada penutupan hari yang sama. Untuk cek PRD mingguan, unduh data IDX bagi 20 saham ADTV tertinggi, cocokkan tanggal yang sama dan harga penutupan/volume, dan tandai selisih >1% sesuai ambang proyek. Namun halaman publik yang diperiksa tidak membuktikan adanya API tanpa autentikasi untuk sejarah harga massal. Untuk mengambil riwayat historis panjang atau otomatis, jalur yang dapat dipertanggungjawabkan adalah meminta data feed/lisensi langsung dari [Layanan Data BEI](https://www.idx.co.id/id/produk/layanan-data-bei); biaya dan izin penggunaan harus dikonfirmasi ke IDX. Jangan memakai situs mirror atau API komunitas sebagai pengganti sumber resmi.

**Pembaruan 29 Okt 2026 (sesi 57):** endpoint di balik halaman itu,
`https://www.idx.id/primary/TradingSummary/GetStockSummary?length=9999&start=0&date=YYYYMMDD`,
menjawab HTTP 200 di domain `www.idx.id` (bukan `idx.co.id`) dan memuat arsip per tanggal sampai
paling tidak Feb 2023; 28 Okt 2026 cocok 916/916 penutupan dengan yfinance. Namun
[Syarat Penggunaan IDX](https://www.idx.id/id/syarat-penggunaan/) melarang web scraping/crawling,
sehingga pemakaian otomatisnya tidak diusulkan. Usulan dan keputusan yang tertunda: P40/P41 di
`docs/keputusan.md` 3.10.

## 5. Fundamental resmi

IDX menyediakan halaman [Laporan Keuangan dan Tahunan](https://www.idx.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan/) dengan filter kode/nama emiten, jenis laporan, jenis efek, tahun, dan periode. Halaman itu menautkan filing per emiten termasuk PDF, XLSX, `instance.zip`, dan `inlineXBRL.zip` (tergantung laporan). IDX juga menjelaskan [pelaporan XBRL](https://www.idx.id/id/perusahaan-tercatat/xbrl): laporan disampaikan melalui IDXnet dan taksonomi IDX menstandardisasi laporan posisi keuangan, laba rugi, perubahan ekuitas, dan arus kas.

IDX juga menerbitkan [Financial Data and Ratio](https://www.idx.co.id/en/market-data/statistical-reports/digital-statistic/monthly/financial-report-and-ratio-of-listed-companies/financial-data-and-ratio?filter=eyJ5ZWFyIjoiMjAyNSIsIm1vbnRoIjoiNCIsInF1YXJ0ZXIiOjAsInR5cGUiOiJtb250aGx5In0%3D) sebagai statistik bulanan dengan tombol **Download PDF Excel**. Contoh April 2025 mencakup sektor, subindustri, tanggal laporan, tipe laporan, aset, liabilitas, ekuitas, penjualan, EBT, EPS, BVPS, PER, PBV, DER, ROA, ROE, dan NPM. Ini sumber resmi yang lebih terstruktur untuk metrik inti daripada angka vendor. **Batasnya:** tabel yang diperiksa tidak mencakup semua faktor PRD, termasuk NPL/CAR/BOPO/NIM bank; gunakan filing/XBRL bank untuk item yang hilang. Cakupan Excel dan kecocokannya dengan laporan emiten perlu diuji pada unduhan nyata sebelum menyatakan impor massal selesai.

OJK melalui [POJK 14/2022](https://ojk.go.id/id/regulasi/Pages/Penyampaian-Laporan-Keuangan-Berkala-Emiten-atau-Perusahaan-Publik.aspx) mewajibkan laporan keuangan berkala disampaikan kepada OJK dan diumumkan kepada masyarakat. Cakupannya laporan tahunan dan tengah tahunan, dengan posisi keuangan, laba rugi, perubahan ekuitas, arus kas, dan catatan. Jadi sumber faktual untuk fundamental adalah filing emiten yang dipublikasikan IDX/OJK, bukan angka agregat tidak resmi.

**Cara menutup celah dengan impor yang sudah ada:** uji unduhan Excel `Financial Data and Ratio` untuk satu bulan dan cocokkan beberapa pos ke filing sumbernya. Mulai dengan emiten likuid yang benar-benar masuk saringan; untuk nilai yang tidak dicakup ringkasan, gunakan XLSX/XBRL resmi, catat URL dan tanggal publikasi (bukan hanya akhir periode), lalu masukkan pos ke format `fundamental.csv`. Untuk nilai yang tidak tersedia atau tidak dapat dipetakan dengan pasti, biarkan metrik tidak dihitung. Simpan jejak dokumen/halaman/tag dan gunakan koreksi sebagai baris baru. Data yfinance tetap berlabel tidak resmi; jangan campurkan ke seri resmi tanpa label.

## Catatan akses dan batas kepastian

IDX memiliki beberapa domain resmi (`idx.co.id`, `idx.id`, dan domain layanan seperti `block.idx.id`). Sebagian halaman lama pernah mengembalikan 403 untuk klien HTTP biasa; pada 10–11 Okt 2026 halaman publik `www.idx.id` berhasil dibuka dari pengambilan proyek. Karena situs menggunakan JavaScript dan endpoint internalnya bisa berubah, angka/URL API bukan kontrak layanan. Bukti unduhan yang paling stabil untuk tahap sekarang adalah file yang diperoleh lewat tombol **Unduh** atau tautan PDF/XLSX resmi, disimpan lokal bersama tanggal akses dan hash.
