# Riset seri harga snapshot 4 dan draf aksi PACK

Tanggal pemeriksaan: 22 Okt 2026. Tujuan: menindaklanjuti temuan pada
`docs/keputusan.md` bagian 5, sesi 42. Ini catatan pemeriksaan bukti, bukan otorisasi impor.

## Temuan sumber harga

- **FORU, 14 Sep 2026:** laman informasi saham resmi emiten mencantumkan low 4.330, high 4.650,
  open 4.650, close 4.650, volume 4.375.800. Halaman menyatakan data berasal dari IDX.
  Angka ini menguatkan adanya konflik dengan snapshot vendor (Rp238; volume 85.346.954), tetapi
  tidak membuktikan seri historis vendor benar atau menjelaskan transformasinya.
  Sumber: https://www.dev.foru.co.id/investor-room/stock-information
- Untuk **BNBR (13–16 Feb 2023), COCO (30 Sep 2025), FISH (1 Sep 2025), PYFA (16 Apr 2024), SCCO
  (1 Feb 2024), dan TMAS (23–24 Mei 2023)**, pencarian dalam sesi ini belum memperoleh tabel
  riwayat harian resmi IDX/emiten yang dapat dibandingkan baris per baris. Endpoint yang dicoba: https://www.idx.co.id/primary/TradingSummary/GetStockSummary?date=20230213 (akses langsung HTTP 403). Halaman Ringkasan Saham
  IDX yang terakses adalah ringkasan perdagangan saat ini, bukan arsip harian per tanggal:
  https://www.idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/
- Ketentuan penggunaan IDX menyatakan informasi Perusahaan Tercatat di situs webnya mencakup tiga
  tahun terakhir. Ini membatasi pencarian halaman emiten/index untuk data BNBR Februari 2023 pada
  tanggal pemeriksaan, tetapi bukan bukti bahwa arsip berlisensi atau arsip lain tidak tersedia:
  https://idx.co.id/id/syarat-penggunaan/
- **TMAS:** pemberitaan yang mengutip pengumuman BEI menyebut split 1:10 dan harga teoritis 23 Mei 2023 Rp298; OHLC lengkap tanggal 23–24 Mei tidak tersedia dari sumber primer yang berhasil dibuka. Rujukan sekunder untuk menemukan nomor/pengumuman: https://investor.id/market/330068/susul-samudera-indonesia-smdr-temas-resmi-stock-split. Informasi ini tidak memverifikasi bar vendor.
- Karena belum ada seri primer yang cocok, enam kode di atas tetap **belum terverifikasi**.
  Jangan mengubah harga atau menganggap angka sekunder sebagai kebenaran resmi. FORU tetap memiliki
  satu baris resmi yang cocok, dengan batas bukti seperti dijelaskan di atas.

## Draf aksi PACK

Pengumuman KSEI No. KSEI-0064/DIR/00126 bertanggal 5 Jan 2026 menyatakan ex-date pasar reguler dan
negosiasi 12 Jan 2026; tiap 5 saham menerima 102 HMETD; tiap HMETD memberi hak membeli 1 unit OWK
pada harga Rp100. OWK berkonversi 1:1 menjadi saham baru. Periode perdagangan HMETD tercantum
15–22 Jan dan `Rights Issue Date` tercantum 22 Jan. Sumber resmi:
https://web.ksei.co.id/Announcement/Files/189658_ksei_0064_dir_00126_202601121343.pdf

Draf satu baris tersedia di `docs/draf-aksi-korporasi-PACK-2026-10.csv`. Kolom `rasio_lama:rasio_baru`
5:102 merekam jumlah HMETD per saham lama (unit OWK berkonversi 1:1); harga tebus 100 adalah harga
per unit OWK. `tenggat` sengaja kosong: dokumen memberi periode perdagangan dan tanggal Rights Issue,
tetapi draf ini tidak menyamakan keduanya dengan tenggat pelaksanaan yang diminta oleh skema.
Draf perlu ditinjau untuk kecocokan semantik `right_issue` terhadap instrumen OWK sebelum dimasukkan
ke berkas konfigurasi. Tidak ada harga teoretis yang dihitung. Belum ada impor atau perubahan basis
data.

## Tahap

Tidak menjalankan tes: pekerjaan ini hanya pemeriksaan sumber dan draf dokumen. Tinjauan wajib sebelum
aksi berikutnya sesuai K4. Langkah lanjut: tinjau baris PACK khususnya klasifikasi dan rasio instrumen;
lanjutkan pencarian/permintaan seri primer historis untuk enam kode yang tersisa; setelah ada persetujuan
terhadap draf, baru pertimbangkan impor terpisah.

## Pemeriksaan tambahan saat tinjauan draf (22 Okt 2026)

- Draf PACK cocok dengan rasio HMETD dan harga pelaksanaan: KSEI menyebut setiap 5 saham menerima
  102 HMETD, setiap HMETD membeli 1 OWK dengan harga Rp100, dan OWK dikonversi 1:1 menjadi saham.
  Ini memastikan interpretasi satuan pada komentar draf, bukan harga saham atau harga teoretis.
- **Catatan diperbarui sesi 45:** interpretasi bahwa surat 23 Jan memberi contoh pelaksanaan pada
  26 Jan ternyata keliru. Jadwal KSEI memisahkan tanggal pelaksanaan HMETD (22 Jan) dari tanggal
  distribusi OWK (26 Jan); rincian klarifikasi ada di bagian akhir catatan ini.
- Laman Price History KSEI untuk COCO, FISH, SCCO, dan TMAS dapat dibuka, tetapi cuplikan yang
  ditampilkan hanya memuat tanggal akhir 2025/2026; tidak mencakup tanggal anomali yang sedang
  dicari. Halaman BNBR gagal diambil (HTTP 500) dan PYFA timeout pada pemeriksaan ini. Ini bukan
  konfirmasi bahwa data arsip tidak tersedia; hanya berarti halaman publik yang berhasil dibuka
  belum memberi bukti OHLCV untuk tanggal target.
- Sumber resmi tambahan: [jadwal PACK KSEI, KSEI-0064/DIR/00126](https://web.ksei.co.id/Announcement/Files/189409_ksei_0064_dir_00126_202601051727.pdf),
  [jadwal revisi PACK](https://web.ksei.co.id/Announcement/Files/189658_ksei_0064_dir_00126_202601121343.pdf),
  [klarifikasi pencatatan OWK PACK, KSEI-1626/JKU/0126](https://web.ksei.co.id/Announcement/Files/189940_ksei_1626_jku_0126_202601232123.pdf),
  [Price History COCO di KSEI](https://web.ksei.co.id/services/registered-securities/shares/lc/COCO?setLocale=id-ID),
  [Price History FISH di KSEI](https://web.ksei.co.id/services/registered-securities/shares/lc/FISH?setLocale=id-ID),
  [Price History SCCO di KSEI](https://web.ksei.co.id/services/registered-securities/shares/lc/SCCO?setLocale=id-ID),
  dan [Price History TMAS di KSEI](https://web.ksei.co.id/services/registered-securities/shares/lc/TMAS?setLocale=id-ID).
- Tahap tetap berhenti untuk tinjauan: jangan mengisi tenggat dari salah satu tanggal tanpa menyelesaikan
  perbedaan sumber, jangan mengimpor draf, dan jangan mengoreksi harga vendor.
- Jalur data resmi berizin untuk seri harian: [FAQ IDX Data Services](https://data.idx.co.id/faq.php?p=sFWjtRbH1z2wag4)
  menyebut aliran EoD, akses portal SIPD bagi licensee, dan redistributor untuk koneksi tidak langsung;
  [katalog produk IDX](https://data.idx.co.id/catalog_product2.php?p=XLoi5RtfUJ8SBrm)
  mencantumkan IDX Equity EoD / EoD Professional dengan field OHLCV. Akses halaman data langsung
  dibatasi pada sesi ini, jadi ini jalur permintaan/akses yang teridentifikasi, bukan klaim bahwa
  arsip target sudah tersedia atau telah diperoleh.
- Ketentuan penggunaan IDX menyatakan informasi emiten di situs mencakup tiga tahun terakhir;
  untuk BNBR Februari 2023 dan TMAS Mei 2023, di luar jendela itu per 22 Okt 2026, IDX mengarahkan
  kebutuhan data lebih lama ke TICMI dengan syarat terpisah. Ini batas kanal publik, bukan bukti
  bahwa data berlisensi tidak ada: [Syarat Penggunaan IDX](https://idx.co.id/id/syarat-penggunaan/).

## Klarifikasi tenggat PACK (22 Okt 2026 — sesi 45)

- Jadwal KSEI No. KSEI-0064/DIR/00126 mencantumkan **22 Jan 2026 sebagai Tanggal Pelaksanaan
  HMETD** setelah periode perdagangan 15–22 Jan. Jadwal yang sama mencantumkan **26 Jan 2026 sebagai
  tanggal distribusi OWK atas pelaksanaan HMETD**.
- Surat KSEI No. KSEI-1626/JKU/0126 tanggal 23 Jan tidak menyatakan HMETD dapat dilaksanakan pada
  26 Jan; ia memberi ilustrasi pemegang yang memiliki HMETD dan akan melaksanakannya, lalu
  menjelaskan jumlah OWK yang diterima. Ini konsisten dengan distribusi OWK 26 Jan setelah tanggal
  pelaksanaan 22 Jan.
- Mengikuti definisi `aksi_korporasi.tenggat` sebagai batas waktu pelaksanaan
  (`docs/skema-data.md` §5.14), draf `docs/draf-aksi-korporasi-PACK-2026-10.csv` kini mengisi
  `tenggat=2026-01-22`. Draf belum diimpor; klasifikasi `right_issue` untuk HMETD yang membeli OWK
  masih perlu ditinjau semantik sebelum dipindahkan ke konfigurasi. Tidak ada harga teoretis.
- Tidak ada perubahan basis data. Tes tidak dijalankan karena tahap ini pemeriksaan dokumen.
- Sumber primer: [jadwal KSEI](https://web.ksei.co.id/Announcement/Files/189409_ksei_0064_dir_00126_202601051727.pdf)
  (tabel kegiatan dan distribusi, hlm. 2–3), [surat klarifikasi KSEI](https://web.ksei.co.id/Announcement/Files/189940_ksei_1626_jku_0126_202601232123.pdf).



# Usulan rancangan terpisah untuk mutu harga PACK (22 Okt 2026 — sesi 48)

**Status: usulan untuk tinjauan, belum disetujui dan belum diimplementasikan.** K90 membatasi
OWK di luar posisi v0.1, sementara bukti KSEI tentang HMETD PACK tetap relevan untuk memberi
konteks pada lonjakan harga. Karena `aksi_korporasi` dibaca oleh alur posisi dan penyesuaian,
menaruh PACK di sana akan mengaktifkan makna yang tidak didukung.

## Bentuk yang diusulkan

- Tambahkan tabel khusus, misalnya `catatan_aksi_mutu`, append-only dan point-in-time, terpisah
  dari `aksi_korporasi`. Satu baris merekam emiten, tanggal efektif yang dinyatakan sumber,
  label instrumen/aksi dalam bahasa sumber (HMETD untuk OWK), ringkasan bukti, URL/dokumen sumber,
  serta `diketahui_pada`. Hindari kolom `rasio_lama`, `rasio_baru`, dan `harga_tebus` bernama
  seperti kolom operasional; angka dokumen dapat disimpan sebagai kutipan/atribut bukti dengan
  satuan eksplisit (5 saham → 102 HMETD; Rp100 per OWK), tanpa disalahartikan sebagai rasio saham.
- Baris tersebut hanya dibaca pembuat laporan mutu sebagai konteks peristiwa. Tidak menjadi
  masukan `posisi.aksi_korporasi`, `penyesuaian.sesuaikan`, pengingat HMETD, atau daftar tindakan
  dasbor; tidak menghitung TERP dan tidak menyatakan harga vendor benar.
- Bila tanggal lonjakan berada dalam jendela aksi, laporan tetap mempertahankan temuan lonjakan
  belum terverifikasi/bermasalah sampai harga primer dicocokkan. Tambahkan catatan terpisah bahwa
  ada peristiwa korporasi yang tercatat dan tampilkan sumbernya. Dengan demikian aksi memberi
  konteks, tetapi tidak memaafkan lonjakan ataupun mengubah status harga.
- Impor menggunakan berkas tersendiri, bukan `aksi-korporasi.csv`, supaya jalur impor yang ada
  tidak dapat secara tidak sengaja mengubah perilaku posisi. Koreksi bukti menambah revisi/baris;
  tidak menimpa sejarah.

## Penerapan ke PACK

Draf `docs/draf-aksi-korporasi-PACK-2026-10.csv` saat ini adalah draf **aksi operasional** dan
tidak boleh dipakai untuk impor mutu. Setelah rancangan disetujui, siapkan berkas mutu yang baru
dari sumber KSEI yang sudah dirujuk di bagian pemeriksaan PACK di atas. Tanggal ex-date 12 Jan
2026, rincian rasio HMETD dan harga per OWK dicantumkan sebagai fakta yang dinyatakan sumber;
tidak ada hasil penyesuaian harga yang diturunkan darinya.

## Batas dan tindak lanjut

Rancangan ini belum menetapkan format final tabel/CSV, kunci revisi, UI, atau perubahan kode.
Perlu tinjauan pengguna sebelum tahap implementasi dan impor. Enam emiten BNBR, COCO, FISH, PYFA,
SCCO, dan TMAS tetap membutuhkan seri OHLCV primer; catatan aksi PACK tidak menyelesaikan
verifikasi bar Yahoo.

## Pratinjau TICMIDATA untuk enam tanggal OHLCV (22 Okt 2026 — sesi 54)

Katalog Pay Per Use `Data Transaksi Harian Saham` menawarkan kolom tanggal, kode, Open, High, Low, Previous, Close, Volume, Value, dan Frequency. Pemeriksaan dilakukan langsung pada tabel Preview interaktif [TICMIDATA Pay Per Use](https://ticmidata.co.id/pay_per_use) pada 22 Okt 2026. Nilai di bawah adalah tampilan pratinjau, belum ekspor yang dibeli/dilisensikan; jangan tulis ke `harga.csv` atau distribusikan sebelum hak pakai dikonfirmasi. Halaman TICMIDATA menyatakan data historis sejak 1977 dan opsi Pay Per Use; dokumentasi API menyatakan kredensial API diberikan dalam perjanjian kerja sama ([API docs](https://doc-api.ticmidata.co.id/)).

Angka mengikuti tampilan TICMIDATA (titik sebagai pemisah ribuan; harga dalam rupiah; volume lembar).

| Kode / tanggal | Open | High | Low | Previous | Close | Volume | Value (Rp) | Frequency | Catatan |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BNBR 13 Feb 2023 | 63 | 66 | 60 | 64 | 61 | 257.782.662 | 15.911.032.800 | 3.891 | Berbeda dari snapshot 4 |
| BNBR 14 Feb 2023 | 61 | 64 | 60 | 61 | 62 | 118.776.520 | 7.354.143.300 | 13.086 | Berbeda dari snapshot 4 |
| BNBR 15 Feb 2023 | 62 | 63 | 60 | 62 | 60 | 48.273.935 | 2.960.509.400 | 792 | Berbeda dari snapshot 4 |
| BNBR 16 Feb 2023 | 60 | 62 | 60 | 60 | 60 | 30.991.330 | 1.882.201.500 | — | Value/Frequency tidak ada di Preview |
| COCO 30 Sep 2025 | 106 | 107 | 90 | 106 | 91 | 160.730.903 | 15.319.728.700 | 6.323 | Snapshot 4 mencatat close 158 |
| FISH 1 Sep 2025 | — | — | — | 1.035 | 1.035 | — | — | — | Hanya Previous/Close tersedia |
| PYFA 16 Apr 2024 | 224 | 252 | 202 | 224 | 204 | 55.959.517 | 12.009.547.000 | 1.938 | Snapshot 4: Previous 1.040, Close 203; basis harga perlu diteliti |
| SCCO 1 Feb 2024 | 2.510 | 2.540 | 2.490 | 2.490 | 2.490 | 76.000 | 190.750.000 | 50 | Value/Frequency tersedia; Change kosong |
| TMAS 23 Mei 2023 | 304 | 322 | 292 | 298 | 296 | 25.963.000 | 7.961.694.000 | 4.954 | — |
| TMAS 24 Mei 2023 | 296 | 304 | 276 | 296 | 286 | 9.121.600 | 2.657.314.400 | 1.814 | — |

Pratinjau BNBR memuat semua kolom kecuali Value dan Frequency pada 16 Feb. Untuk FISH, tanda “—” berarti Preview TICMI menampilkan “-” pada kolom itu; sebabnya tidak disimpulkan. Hasil TMAS konsisten dengan harga teoritis Rp298 yang pernah disebut sumber sekunder untuk 23 Mei, tetapi tabel ini tetap pratinjau vendor dan perlu ekspor/provenance berizin sebelum digunakan. Konflik PYFA (Previous TICMI 224 dibanding snapshot 1.040) harus diselesaikan dengan basis harga dan aksi korporasi sebelum menganggap data seri sebanding. Tidak ada harga yang dikoreksi atau diimpor.

**Tahap K4:** Tes tidak dijalankan (pemeriksaan sumber). Ringkasan: lima ticker punya nilai target di Preview, FISH parsial; telah ditemukan kanal berbayar dengan field yang dibutuhkan. Belum: konfirmasi hak pakai/ekspor, pemeriksaan provenance ekspor, dan rekonsiliasi basis PYFA/seri yang berbeda. Cara mengulang: buka halaman Pay Per Use, pilih `Data Transaksi Harian Saham`, lalu masukkan ticker dan tanggal di tabel; klik Preview tanpa memasukkan ke keranjang. Tahap berhenti untuk tinjauan.
