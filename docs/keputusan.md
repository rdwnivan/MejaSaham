# Meja Saham — Catatan Keputusan (Bahan Tinjauan)

Status: **bahan tinjauan, bukan spesifikasi final.** Sudah ada kode kerangka, lapisan basis
data, lapisan konfigurasi parameter bertanggal, lapisan ingesti (termasuk pengambilan daftar
emiten dari Master File Efek KSEI, K12), dan lapisan perhitungan
(metrik, saring, skor); risiko, jurnal, ekspor, cadangan/pemulihan F12, jendela PySide6, dan
bundel PyInstaller onedir sudah berjalan (bagian 5; **T81**).
Sumber kebenaran tetap `PRD-Screener-Saham-IDX-v1.3.docx`.
Teks PRD hasil ekstraksi untuk memudahkan rujukan: `_extract/prd_v1.3.txt` (sementara).

Dokumen pendamping: `../AGENTS.md` (aturan kerja), `arsitektur.md` (HOW),
`skema-data.md` (entitas & kunci), `konfigurasi.md` (parameter bursa & ambang),
`ideas.md` (yang ditunda). Semua masih kerangka dan ikut berubah saat bagian 3 dijawab.

Aturan: apa pun yang bertanda **[PERLU VERIFIKASI]** tidak boleh dipakai untuk
keputusan nyata dan tidak boleh dikarang nilainya — harus diisi dari pengumuman
resmi (IDX, OJK, DJP, broker) dengan tanggal berlaku.

---

## 1. Keputusan yang sudah diambil (dijawab 2026)

| No | Pertanyaan | Keputusan | Rujukan PRD |
|----|-----------|-----------|-------------|
| K1 | Basis pemilihan poros produk (Q1) | **Dua ember preset**: (a) kualitas+nilai, horizon bulanan; (b) momentum, horizon mingguan | tabel 29 Q1; tabel 5 |
| K2 | Jalur data awal | **yfinance dulu** dengan label "tidak resmi", **plus impor berkas** sebagai jalur cadangan; ketentuan pemakaian Yahoo dicek sebelum Tahap 0 selesai | Q8 (17.1); 7.2 |
| K3 | Lingkungan Python | Boleh membuat **`.venv` proyek** dan memasang PySide6, yfinance, pytest dari PyPI; versi dipin di `requirements.txt`. **Amandemen 2026: `pyarrow` dicabut** dari pemasangan awal | 6.1 |
| K4 | Ritme kerja | **Berhenti di setiap tahap** untuk ditinjau: test lulus + ringkasan + daftar belum dikerjakan + cara menjalankan | aturan kerja 8 |
| K5 | Penyimpanan data | **SQLite (WAL) satu-satunya sumber kebenaran**; Parquet hanya turunan ekspor/arsip, tidak pernah dibaca sebagai sumber kebenaran | 8.1; 9.13 (AC-19); 9.12 |
| K6 | Bentuk & letak konfigurasi | **Dua tempat**: parameter bursa bertanggal → TOML yang diedit tangan, dimuat ke tabel bertanggal; preset saringan + bobot faktor + batas risiko → **baris berversi di basis data** (bukan berkas yang bisa disunting) | 6.1; 8.3; 10 |
| K7 | Ketentuan pemakaian sumber data (gerbang Q8) | **Diperiksa pada Tahap 0 langkah 3. Hasilnya: Syarat Layanan Yahoo melarang pengambilan data otomatis "untuk tujuan apa pun tanpa izin tertulis sebelumnya", tanpa pengecualian pemakaian pribadi.** Karena itu melanjutkan dengan yfinance dicatat sebagai **risiko yang diterima secara sadar, bukan izin** — dengan tiga syarat yang mengikat: (a) label "tidak resmi" menempel di setiap baris dan setiap ekspor, (b) jalur impor berkas tetap warga kelas satu, (c) sumber resmi/berlisensi dievaluasi sebelum uang nyata | Q8 (17.1); 7.2; 7.3 |
| K8 | C10 — harga sumber yang sudah disesuaikan aksi korporasi | **Penanda per baris.** `harga_harian.penyesuaian_sumber` menyimpan apa yang **sudah** dilakukan sumber (`tidak_disesuaikan`, `split`, `split_dividen`); NULL = belum dinyatakan. Penyesuaian saat dibaca **melewati** aksi yang sudah diterapkan sumber; berkas impor wajib menyatakan penandanya sendiri; baris tanpa penanda ditandai di laporan mutu, bukan ditebak | 7.2; 10; T5 |
| K9 | P1 — definisi "emiten likuid" | **ADTV20 ≥ Rp 5 miliar dan lolos pengecualian** notasi khusus/suspensi/papan pemantauan khusus. Ambangnya tetap dapat diubah di preset | 8.2; 8.3; 9.4 |
| K10 | P5–P12 — definisi metrik 8.2 | **Dipakai apa adanya seperti usulan** (rinciannya di 1.4) | 8.2; 8.3; 9.5 |
| K11 | Sumber kalender bursa setelah IDX menutup akses otomatis | **Kalender hari libur bursa boleh diambil dari pengumuman KSEI**, karena KSEI menerbitkannya sebagai tindak lanjut eksplisit atas pengumuman IDX (yang disebut nomornya), bukan sebagai sumber sekunder yang menafsir. **Sudah dikerjakan 9 Okt 2026** (`mejasaham/kalender.py`, `--ambil-kalender`): berkas PDF-nya diunduh dari halaman resmi KSEI (`/services/schedule-c-best-instruction`) dan diurai **tanpa dependensi baru** (`zlib` + `re` bawaan), lalu ditulis sebagai `kalender-bursa.csv`. Yang dipakai 9 Okt 2026: **KSEI PENG-0002/DIR/KSEI/0126** (penyesuaian, menindaklanjuti **IDX Peng-00171/BEI.POP/09-2025**) dengan **22 tanggal libur 2026**, dan **KSEI PENG-0004/DIR/KSEI/0926** (menindaklanjuti **IDX Peng-00169/BEI.POP/09-2026**) dengan **20 tanggal libur 2027**. Sumber ini **bersyarat**: berkas yang tidak menyatakan menindaklanjuti *Kalender Libur Bursa* IDX ditolak, sekalipun ia menyebut nomor pengumuman IDX — berkas KSEI 2025 yang terukur menindaklanjuti kalender operasional EBA/sukuk, jadi **2025 tidak ada di kalender** (T31). Seluruh `idx.co.id` tetap menolak akses otomatis | 7.1; U5; AC-8 |
| K12 | Sumber daftar emiten (semesta saham) setelah `idx.co.id` menutup akses otomatis | **Daftar emiten boleh diambil dari Master File Efek KSEI** (`web.ksei.co.id/Download/StatisEfekYYYYMMDD.txt.zip`; terbit bulanan, terbuka, dan menerima User-Agent jujur — tidak perlu menyamar sebagai browser). Yang diisi **hanya fakta yang dinyatakan berkasnya**: `kode`, `nama`, `jumlah_saham` (kolom `Num. of Sec`), dan — **ditambahkan 9 Okt 2026 lewat Tahap 1 langkah 7**, tetap menurut aturan yang sama — `tanggal_notasi` (kolom `Listing Date`; pemetaan namanya ditanyakan sebagai P18, lihat bagian 3). Yang **tidak** diisi meski kolomnya ada di sumber: `sektor_idx_ic` (KSEI memakai taksonomi sendiri, bukan IDX-IC), `papan` (tidak ada di berkas KSEI), `jenis` (keputusan analis), `free_float_persen` (kolom Local/Foreign (%) KSEI = komposisi kepemilikan, **bukan** free float), `status_notasi` (`ACTIVE` KSEI = aktif tercatat, bukan notasi khusus IDX). Saham preferen/seri (ISIN `ID2…`) dikeluarkan dan pengeluarannya dilaporkan. Terverifikasi 9 Okt 2026: berkas 30 Sep 2026 memuat 3.681 baris, **975 EQUITY di IDX semuanya ACTIVE → 973 saham biasa** setelah 2 kelas lain dikeluarkan | 7.1; 8.1; 9.4; aturan keras 1 |
| K13 | U18 — gerbang "gagal > 5%" ketika semesta datang dari daftar resmi yang memuat efek **tidak diperdagangkan lagi** | **Bedakan gagal permanen dari gagal sementara** (usulan U18 dipakai apa adanya), diputuskan 9 Okt 2026. Setiap kegagalan membawa `jenis`: **permanen** hanya bila **sumber menyatakan sendiri** bahwa kode itu tidak punya data (yfinance 1.7.0 meneruskannya di `YFPricesMissingError.yahoo_reason`, mis. "No data found, symbol may be delisted"); **sementara** bila pembatasan laju, waktu habis, galat jaringan, atau sebabnya tidak dinyatakan. Hanya yang **sementara** dihitung terhadap ambang 5% PRD 9.3. Yang permanen tidak dihilangkan, melainkan dilaporkan sebagai **lubang yang diketahui**: peringatan `--refresh`, temuan mutu jenis `tidak_diperdagangkan`, dan catatan snapshot. Syarat kedua PRD 9.3 ("ada emiten ber-ADTV20 tertinggi yang gagal") tetap berlaku untuk **kedua** jenis. Bila jenis tidak dapat dipastikan, bawaannya **sementara** — menahan snapshot, bukan meloloskannya. Kegagalan permanen **tidak diulang** | 9.3; 7.2; 7.3; AC-1; AC-9 |
| K14 | P17 — sumber mana yang dipakai berhitung bila ada dua label `sumber` harga? | **Usulan (a) dipakai apa adanya, dan dikonfirmasi pengguna 9 Okt 2026**: satu label per snapshot, yaitu label dengan **riwayat bar terbanyak** (seri diputus menurut abjad), dihitung **pada saat snapshot**; `--sumber` sebagai penimpa; label yang dipakai **dan** yang tidak dipakai selalu dilaporkan, dan adanya label kedua menjadi peringatan. Label yang tidak punya satu bar pun ditolak berisik. Label **per emiten** ditolak dengan alasan: dua emiten di peringkat yang sama akan dihitung dari sumber berbeda tanpa satu pun tanda (A5). **Opsi (b)** — pengguna memilih sumber per snapshot/preset — tidak diambil sekarang; pilihannya terkumpul di satu fungsi (`potret.riwayat_sumber`), jadi bisa ditambahkan tanpa membongkar apa pun bila nanti diperlukan. Ambang angka "label dominan" **sengaja tidak dibuat**: angkanya tidak berasal dari PRD mana pun, dan aturan yang sepenuhnya menentukan jawaban ditambah pelaporan yang tidak bisa dilewatkan sudah menutup alasan ambang itu diusulkan | P17; PRD 7.3; migrasi 005; T32 |
| K15 | P18 — apa arti nama kolom `tanggal_notasi` di tabel `emiten`? | **Tanggal pencatatan saham (listing date)**, dikonfirmasi pengguna 9 Okt 2026. Isinya tetap diambil dari kolom `Listing Date` Master File Efek KSEI (jalur yang sudah berjalan sejak langkah 7), dan pemetaan itu tetap dinyatakan terbuka di penjelasan berkas yang memuatnya. Tafsir "tanggal mulai notasi khusus" **tidak** dipakai — kalau kelak berubah, nilai yang sudah tersimpan **diganti namanya** lewat migrasi + baris baru, bukan ditimpa (aturan keras 3) | PRD 12 tabel 23; K12; langkah 7 |
| K16 | Sumber **imbal hasil SUN** setelah BI dan DJPPR diperiksa | **Kurva imbal hasil SBN dari halaman HPW (Harga Pasar Wajar) PHEI** — PT Penilai Harga Efek Indonesia, lembaga penilai harga efek yang menerbitkan harga pasar wajar & imbal hasil harian, termasuk kurva imbal hasil SBN per tenor. Diambil dari `phei.co.id/Data/HPW-dan-Imbal-Hasil`; yang dipakai **kolom Today** dan **tenor 10 tahun** (yang disebut PRD 8.2). Kolom "Yesterday" **tidak** dipakai, sebab halaman itu menyatakan **satu** tanggal valuasi dan tanggal "kemarin" tidak dinyatakan di mana pun — menghitungnya sendiri berarti menebak tanggal. Dua jalur lain diperiksa lebih dulu dan gagal, dengan bukti di bagian 5.1: `bi.go.id` memutus koneksi, dan `api-djppr.kemenkeu.go.id` ternyata CMS yang isinya dirender aplikasi. **Batas yang diketahui:** halaman itu menyajikan nilai hari itu saja, bukan deret riwayat, jadi berkasnya bertambah satu baris per jalan dan riwayat sebelum pengambil ini ada tidak bisa diisi dari sini. Pengambil: `--ambil-sun` (`mejasaham/sun.py`); penulisan basis data tetap lewat `--impor` | PRD 7.1; 8.2; C9; K3 |
| K17 | P19 — bolehkah tanggal libur bursa 2025 diambil dari revisi pengumuman KSEI yang **sudah digantikan**? | **Boleh, dengan syarat yang bisa diperiksa — disetujui pengguna 9 Okt 2026.** Revisi yang lebih lama dipakai **hanya bila**: (a) berkas yang ditautkan halaman ditolak **semata-mata** oleh syarat T31 (kalau gagal pemeriksaan lain, revisi lama tidak dicari sama sekali — mencari pengganti untuk berkas yang tabelnya rusak akan menutupi kerusakan yang lebih besar), (b) revisi lama lulus **seluruh** pemeriksaan termasuk T31, dan (c) himpunan tanggal liburnya **sama persis** dengan berkas yang ditautkan. Satu tanggal berbeda → revisi lama ditolak dan tahunnya tetap kosong beserta alasannya. Keterangan yang berbeda **tidak** menolak (perbaikan salah ketik pernah terjadi pada berkas nyata 2025) tetapi jumlahnya dilaporkan. Alamat revisi lama diturunkan dari **nama berkas** yang ditautkan dengan melepas penanda revisi (`_Kedua`, lalu `_Perubahan`), maksimum 3 kandidat; setiap kandidat tetap harus lulus syarat (b) dan (c). Seluruh percobaan dilaporkan, dan asal tanggalnya ditulis di berkasnya | P19 (bagian 3.5); K11; T31; T33 |
| K18 | P2 — dari mana fundamental datang, kalau pengguna tidak punya berkasnya? | **Diambil otomatis dari sumber data EOD yang sudah dipakai harga (yfinance), berlabel "tidak resmi" — disetujui pengguna 10 Okt 2026.** Catatan P2 yang lama ("fundamental tidak ada di yfinance") **terbantah pengukuran**: sumber itu memuat laporan keuangan tahunan 4–5 tahun (income statement 38–55 baris, neraca, arus kas) dan turunannya cocok — ROE turunan vs ringkasan sumber 20,44% vs 21,82% (selisihnya justru karena P5 memakai ekuitas rata-rata), dan arus kas operasi cocok lewat dua jalur independen dengan selisih **0,0%** atas 5 emiten. PRD sendiri sudah memutuskan arah ini: tabel 7.1 menulis "*impor berkas bila penyedia tidak lengkap*", dan Q8/17.1 "mulai dengan yfinance berlabel 'tidak resmi' plus jalur impor berkas sebagai cadangan". Yang belum ada hanyalah sumber otomatisnya. Jalurnya `--ambil-fundamental` → `fundamental.csv` → `--impor` (pola yang sama dengan K11/K12/K16), hanya untuk **semesta likuid** secara bawaan (`--semua-emiten` untuk seluruhnya). Empat aturan yang mengikat bentuknya, semuanya dari pengukuran atas 60 emiten: (1) nama baris sumber tidak seragam — hanya 10% memakai `Operating Cash Flow`, 78% memakai bentuk arus kas **metode langsung**, jadi tiap kolom dipetakan dari daftar nama berprioritas; (2) jumlah saham diambil dari **neraca** (`Ordinary Shares Number`), **bukan** `info.sharesOutstanding` yang berbeda >5% pada 17% baris (satu emiten meleset 78 kali); (3) laporan **tidak** dikonversi mata uangnya — 16,7% emiten melapor dalam USD dan `mata_uang` diisi apa adanya, sehingga metrik yang mencampurnya dengan harga rupiah berstatus "tidak dihitung" (AC-3); (4) tabel kosong tanpa exception dibaca sebagai "tanpa laporan", bukan laporan berisi nol | P2 (bagian 3.1); PRD 7.1/Q8/17.1; K7; T32 |
| K19 | Bagaimana memperlakukan **tidak adanya data notasi khusus**, dan tanggal publikasi yang tidak dinyatakan sumber otomatis? | **Dua jawaban, keduanya disetujui pengguna 10 Okt 2026.** (a) **"Tidak ada berkas" ≠ "bersih".** Sebelum ini `_notasi_aktif` mengembalikan tupel kosong untuk dua keadaan yang sangat berbeda, sehingga kriteria `pengecualian_notasi` lolos untuk **seluruh** semesta — padahal laporan mutu aplikasi ini sendiri menulis bahwa emiten tanpa penanda itu "belum terverifikasi dan tidak dijadikan kandidat otomatis" (PRD 7.3). Sekarang kriterianya **tidak diterapkan** (`berlaku=False`, bukan gagal dan bukan lolos) selama belum ada satu baris pun data notasi, peringkatnya tetap dihitung, tetapi **kata "kandidat" ditahan** di lapisan pelaporan (`LaporanSaring.notasi_terverifikasi`), dan laporan menyebut "PERINGKAT SEMENTARA — belum boleh disebut kandidat" beserta sebabnya. (b) **Tanggal publikasi tidak dinyatakan sumber otomatis**, jadi `tgl_publikasi` diisi **tanggal pengambilan** dan kolom baru `asal_tgl_publikasi` (migrasi 007) menandainya `tanggal_pengambilan` — konservatif, karena data tidak pernah dipakai sebelum ia bisa diketahui, dan "tanggal publikasi tidak diketahui" tidak pernah menyamar sebagai tanggal terbit. Kedua nilai dijaga CHECK dan ditolak berisik bila tidak dikenal | PRD 7.3, 7.2, AC-15; aturan keras 1, 3, 7; P2 |
| K20 | P20 — tarif broker (B6/B7) dan slippage (B9) | **Dijawab pengguna 10 Okt 2026: broker yang dipakai adalah Stockbit; slippage memakai usulan — mode `tick`.** (a) **B6/B7 sumbernya broker pengguna sendiri**: tarif sisi beli & sisi jual diambil dari halaman tarif resmi platform/sekuritas itu, **bukan** dari tarif broker lain yang kebetulan terbaca mesin (Mirae 0,15%/0,25% dan Ajaib 0,1513%/0,2513% hanya contoh bahwa tarif broker memang publik). Sampai tarif Stockbit benar-benar diambil dan dimuat, entri `[[biaya_broker]]` **tetap tidak diisi** dan kalkulator biaya **menolak menghitung** — pemuat konfigurasi sendiri menandainya `belum_terverifikasi`. Yang perlu dipastikan saat mengambilnya: nama badan sekuritas di balik platform itu (dipakai sebagai `nama` entri) dan apakah tarifnya sudah termasuk levy + PPN. (b) **B9 = `tick`**, yaitu satu tick memakai tabel fraksi harga B2 — bukan persen tetap. Alasannya: PRD 10 sendiri menulis "slippage satu tick", konvensinya terdokumentasi (`OneTickSlippageFillModel`), dan karena mengikuti tabel B2 ia otomatis benar di setiap pita harga. Karena ini **keputusan produk** dan bukan parameter bursa, nilainya tetap disimpan bertanggal seperti parameter lain, sehingga bisa diganti tanpa menghapus yang lama | P3, P4 (bagian 3.1); PRD 10; K1; `docs/konfigurasi.md` bagian 2 |
| K21 | P21 — bolehkah `jenis` emiten diturunkan dari data? | **Boleh, dengan usulan yang dipakai apa adanya — disetujui pengguna 10 Okt 2026.** `jenis` boleh diturunkan dari `sector`/`industry` yang dinyatakan sumber data (mis. `Financial Services` + `Banks - Regional` → `bank_keuangan`), dengan tiga batas yang mengikat: (a) **label sumbernya ikut tersimpan**, karena ini turunan sumber tidak resmi, bukan isian tangan; (b) **hanya `bank_keuangan` yang diturunkan** — `siklikal_komoditas` **tidak** diturunkan sama sekali, sebab ia penilaian (apakah emiten ini siklikal) yang tidak dinyatakan sumber mana pun, jadi tetap menunggu manusia; sisanya `umum`, yang berarti set kriteria umum; (c) keadaannya tetap **dilaporkan** di `--saring`, karena akibatnya nyata: begitu `jenis` terisi, kriteria bank (NPL, CAR, BOPO, NIM) mulai berlaku dan DER/coverage/CFO-NI berhenti dihitung untuk bank (PRD 8.4). Nilai yang sah hanya tiga: `umum`, `bank_keuangan`, `siklikal_komoditas`; salah ketik ditolak, bukan diabaikan. **Dikerjakan 10 Okt 2026** (Tahap 1 langkah 13, `mejasaham/jenis.py` + `--ambil-jenis`): `jenis` **tetap tinggal di tabel `emiten`** — tidak ada tabel baru, karena K12 sudah menetapkan kolom itu sebagai kolom berkas rujukan `emiten.csv` yang boleh disunting tangan dan `potret`/`arsip`/`saring`/`skor` semuanya sudah membacanya dari sana. Aturan penurunannya satu fungsi murni yang bisa diuji tanpa jaringan; `--ambil-jenis` membaca revisi terakhir **dari basis data**, mengambil `sector`/`industry`, menulis `emiten.csv` (berkas sementara lalu `os.replace`), dan penulisan basis data tetap lewat `--impor`. `jenis` yang sudah terisi **tidak ditimpa**, dan `--saring` melaporkan sebarannya terbedakan (bank dari data / umum dari data / siklikal isian manusia / belum terisi). **Diterapkan ke basis data kerja 19 Okt 2026 (sesi 32):** `--ambil-jenis --timpa-jenis` atas **973** emiten → **49 bank_keuangan · 862 umum · 62 kosong** (55 kode gagal diambil — log menampilkan `HTTPError: HTTP 404` untuk 15 di antaranya — + 7 tanpa sector/industry), diimpor → **snapshot 13**; `--saring` kini menerapkan kriteria bank dan berhenti menghitung DER/coverage/CFO-NI untuk bank — batas (c) K21 terpenuhi di data, bukan hanya di uji | P21 (bagian 3.6); PRD 8.4, AC-16; aturan keras 1; T32; T36 |
| K22 | U20 — bolehkah "tidak dinyatakan sumber" menjadi keadaan yang sah pada parameter bertanggal? | **Boleh — diputuskan 10 Okt 2026, dan itulah satu-satunya cara memuat tarif Stockbit tanpa mengarang.** Halaman tarif resminya menyatakan `0,15%`/`0,25%` dengan tegas tetapi **tidak** menyatakan tarif minimum maupun tanggal berlakunya (bukti: `.uji-data/riset-tarif-broker/stockbit.md` bagian 6). Dua bentuknya: (a) **`minimum` pada `[[biaya_broker]]` boleh TIDAK ADA** → tersimpan `NULL`, yang berarti *"sumber tidak menyatakannya"*. `NULL` **bukan** `0`: nol berarti "tidak ada tarif minimum", dan itu pernyataan tentang bursa yang halaman itu tidak buat. Karena SQLite tidak bisa mencabut `NOT NULL`, tabelnya dibangun ulang **di dalam migrasi 008** (bukan dengan menyunting migrasi 002 yang sudah terpasang, T9); (b) **`berlaku_sejak` boleh berisi tanggal pengamatan**, asalkan ada kolom pendamping `parameter_bursa.asal_berlaku_sejak` bernilai `'sumber'` (bawaan) atau `'tanggal_pengamatan'`, dijaga CHECK dan ditolak berisik bila tidak dikenal. Polanya mengikuti `asal_tgl_publikasi` (K19b, migrasi 007): *"tanggal berlaku tidak diketahui"* tidak pernah menyamar sebagai *"berlaku sejak"*. Tanggal "Diperbarui pada: 05/08/2026" pada artikel bantuan **tidak** dipakai — "diperbarui" bukan "berlaku sejak" | U20 (bagian 2/3.6); PRD 10; aturan keras 1 & 3; K19; T9; T34; T35 |
| K23 | U21 — bagaimana menandai tarif broker yang **all-in**? | **Penandanya disimpan eksplisit di entri — diputuskan 10 Okt 2026.** Bidang `sudah_termasuk` pada `[[biaya_broker]]` berisi daftar komponen yang **dinyatakan sumber** sudah tercakup; nilai yang sah hanya tiga: `levy`, `ppn`, `pph_penjualan` (disimpan sebagai baris di tabel `parameter_biaya_broker_termasuk`, bukan sebagai kalimat, supaya pertanyaannya dijawab mesin). Nilai tak dikenal dan komponen ganda **ditolak berisik**. **Kalkulator biaya kelak MENOLAK menambahkan komponen yang sudah termasuk.** Alasan yang wajib diingat: tanpa penanda ini, tarif jual `0,25%` — yang menurut halaman sumbernya sudah memuat PPh final penjualan `0,1%` — akan dijumlahkan **dua kali** dengan B8 (`[[pajak_penjualan]]` 0,1%): kesalahan yang **tidak terlihat di keluaran mana pun, hanya di angkanya**. Daftar komponen sahnya hidup di `skema.py` dan **diimpor** `konfigurasi.py` (aturan keras 5) | U21 (bagian 2/3.6); PRD 10; aturan keras 1 & 5; K20; T35 |
| K24 | P22 — bagaimana `rasio-bank.csv` (NPL/CAR/BOPO/NIM) diisi, setelah jalur PDF diukur? | **Diisi manusia untuk bank yang masuk kandidat — diputuskan pengguna 10 Okt 2026, dan jalur otomatisnya sengaja TIDAK dibangun sekarang.** Penelusuran P22 sudah sampai dasar dan hasilnya mengubah pertanyaannya: (a) **peramban tidak diperlukan** — `urllib` (stdlib) mengunduh katalog laporan bank **dan** berkas PDF-nya (HTTP 200, `application/pdf`, berkas benar diawali `%PDF-`), sebab situs bank tidak memakai Cloudflare seperti IDX; (b) **pengurai stdlib tidak cukup** — laporan bulanan bisa dibaca (8.473 karakter teks Indonesia dari BCA), tetapi dokumen yang memuat rasionya memakai font CID dengan 44 rujukan `/ToUnicode`, sehingga menuntut pustaka pengurai PDF; menerka pemetaan glyph→huruf sudah dicoba dan **gagal**. Yang diputuskan: **tidak menambah dependensi pengurai sekarang**, karena taruhannya besar dan tidak terlihat (satu pemetaan salah membalik **semua angka** rasio tanpa satu pun galat) sedangkan hasilnya kecil (4 metrik untuk ~15 bank dari ~975 emiten) dan biayanya berulang per bank per periode. **Yang tetap berlaku bila kelak diubah:** jalur otomatisnya terbuka kapan saja, dan keputusan ini tidak menutup apa pun — ia hanya menundanya. **Yang TIDAK terpengaruh keputusan ini:** daftar papan pemantauan khusus, yang narasinya HTML tetapi daftar emitennya justru di lampiran PDF; sumbernya tetap belum ada dan dilaporkan apa adanya. Bukti pengukuran: `docs/lanjutan.md` 2.1a | P22 (bagian 3.6); PRD 8.4; aturan keras 1; K7 |
| K25 | P24 — bagaimana batas bobot per sektor (PRD 9.7) ditegakkan selama `sektor_idx_ic` kosong? | **Kolom sektor KEDUA dari sumber data, berlabel sumbernya — diputuskan pengguna 10 Okt 2026.** Kolom baru `emiten.sektor_sumber` menyimpan sektor **sebagaimana dinyatakan sumber data** (`sector`/`industry` yang sama dengan jalur K21), lengkap dengan label sumber di barisnya, dan **bukan** IDX-IC. Aturan pemakaiannya: (a) `sektor_idx_ic` tetap **satu-satunya** kolom yang dipakai kriteria PRD 8.2/8.4 begitu ia terisi; (b) batas sektor kalkulator risiko memakai `sektor_idx_ic` bila emitennya punya, dan jatuh ke `sektor_sumber` bila tidak — **satu taksonomi per perhitungan**, dan taksonomi yang dipakai disebut di keluaran; (c) karena dua taksonomi tidak boleh dicampur dalam satu penjumlahan paparan, rencana yang sektornya berasal dari taksonomi lain **tidak ikut dijumlahkan** dan jumlah yang dikecualikan itu **dilaporkan**; (d) mengisi `sektor_idx_ic` dengan tangan tetap lebih baik dan tidak dihalangi — begitu terisi, ia yang dipakai. Yang **dilarang**: menamai sektor sumber sebagai `sektor_idx_ic`, atau menafsirkan taksonomi KSEI sebagai IDX-IC | P24 (bagian 3.4); PRD 9.7, 8.2; K12, K21; aturan keras 1 & 2; T36 |
| K26 | P23 — arti `tanggal_tinjau` pada kandidat | **Jatuh tempo berikutnya — diputuskan pengguna 10 Okt 2026, sesuai tafsir yang sudah dikerjakan.** `tanggal_tinjau` adalah tanggal tinjau **berikutnya** (keluaran F4 memang menulis "berikutnya"), dan entri disebut kedaluwarsa ketika tanggal itu **sudah lewat** — bukan ketika "30 hari sejak terakhir dilihat". Angka 30 hari (PRD 9.6, 13.1) tetap dipakai sebagai **saran** jarak tinjauan (`kandidat.saran_tanggal_tinjau`), supaya entri yang baru dibuat tidak langsung dituduh kedaluwarsa. Tidak ada perubahan kode yang dibutuhkan | P23 (bagian 3.4); PRD 9.6, 13.1; T37 |
| K27 | P22 (sisa) — dari mana daftar notasi khusus / papan pemantauan khusus diambil, setelah pengguna menyetujui "cari sumber yang memuat daftarnya sebagai teks"? | **Dari halaman resmi IDX di domain `www.idx.id` — ditemukan 10 Okt 2026, dan itu membatalkan premis "seluruh jalur resmi mati".** Yang memblokir selama ini adalah `www.idx.co.id` dan `www2.idx.co.id` (403), sedangkan `www.idx.id/id/perusahaan-tercatat/notasi-khusus/` melayani halaman yang sama: **HTTP 200**, 251.947 byte, teks di payload SSR Nuxt (bukan PDF, bukan `<table>`), dengan syarat hanya **User-Agent yang menyebut dirinya** — terukur: UA `MejaSaham/0.1 (…)` **diterima**, UA bawaan `Python-urllib/3.14` ditolak 403. Jadi **tidak ada peramban dan tidak ada dependensi baru**. Yang dipakai: pola `FormatEmitenCode:"KODE.HURUF"` (hurufnya **tergabung**, mis. `BOSS.BELYX` = B,E,L,Y,X — bukan satu token), tanggal data dari satu-satunya literal tanggal di halaman itu, `X` → `jenis = papan_pemantauan` (legenda halaman itu sendiri), sisanya `notasi_lainnya`. `tanggal_mulai` = **tanggal data halaman**, dan asal itu ditulis di `keterangan` tiap baris — sumbernya tidak menyatakan kapan notasi dimulai, dan kolom kosong ditolak kontrak impor. Berkasnya **bertambah**; baris yang tidak lagi tercantum **ditutup** (`tanggal_selesai`), dan hanya baris yang ditulis pengambil ini yang boleh ditutup — isian tangan tidak disentuh. Dikerjakan: `mejasaham/notasi.py` + `--ambil-notasi` (**T42**) | P22 (bagian 3.6), K19, K24; PRD 7.3; aturan keras 1 & 3; T31 |
| K28 | Aksi korporasi pada posisi (PRD 9.11): apa yang disimpan dan apa yang diturunkan? | **Hampir semuanya diturunkan — dikerjakan 10 Okt 2026 (Tahap 2 langkah 4).** PRD 9.11 menuntut split/reverse split "menyesuaikan lembar dan stop **otomatis**", dan PRD 7.2 sudah menetapkan polanya untuk harga (disimpan mentah, disesuaikan saat dibaca). Yang **disimpan** hanya yang tidak bisa diturunkan dari mana pun: `posisi.tgl_stop` (basis tanggal level stop — angka yang dicatat manusia, artinya bergantung pada basis harga saat ia menyatakannya) dan tabel `keputusan_right_issue` (tebus / jual HMETD / abaikan — keputusan manusia, bukan turunan data). Kolom `aksi_korporasi.tenggat` ditambahkan untuk batas waktu pelaksanaan right issue; sumber data EOD tidak menerbitkannya, jadi `NULL` berarti **"belum dinyatakan"**, bukan "tidak ada". Tiga konvensi yang mengikat: (1) **lembar** tiap transaksi dikali faktor split yang terjadi **setelah** tanggal eksekusinya (tanggal aksi = tanggal berlakunya, jadi eksekusi pada hari itu sudah basis baru), sedangkan **uangnya tidak** — nilai posisi karena itu tidak berubah oleh split; (2) **stop** dikali kebalikan faktor itu dari basis `tgl_stop`, dan baris lama yang belum menyatakan basisnya **tidak** dikonversi diam-diam: begitu ada split sesudah baris itu dicatat, risikonya berstatus tidak dinilai beserta sebabnya; (3) **dividen** = `dividen_per_saham × lembar pada tanggal ex-date` (transaksi bertanggal **<** ex-date yang berhak), sebab baris dividen yang tersimpan sudah dalam basis sekarang — terukur atas 33 split nyata (SKRN 6 → 6 melewati split 1:5, TMAS 8 → 8 melewati 1:10). Pajak dividen **tidak** dihitung (perlakuannya bergantung status wajib pajak dan reinvestasi, bukan parameter bursa), dan dividen masuk hasil sebagai suku **terpisah** dari hasil perdagangan. Keputusan `tebus` **wajib** menunjuk `id_transaksi`: lembarnya hanya punya satu tempat | PRD 9.11, 7.2, AC-18; aturan keras 1, 2, 3; K8; T32; T43–T51 |
| K29 | P16 — isi daftar "tindakan menunggu" di dasbor (PRD 9.11, 11.1) | **Disahkan pengguna 10 Okt 2026 apa adanya: empat butir usulan + tiga tambahan.** Yang tampil: `stop_tertembus`, `pembatal_terpicu`, `tesis_kedaluwarsa`, `right_issue_belum_diputuskan`, **`tanpa_stop`** (risiko terbukanya tidak dapat dinilai), **stop yang tidak dapat dinilai** (basisnya belum dinyatakan padahal ada split sesudahnya — T49), dan **right issue yang tenggatnya belum dinyatakan** (yang paling mudah terlewat, sebab tidak ada tanggal yang bisa dipakai mengingatkan). Right issue yang tenggatnya **sudah lewat** pindah ke catatan, bukan dihilangkan. Mengubah daftar ini hanya menyentuh `dasbor.tindakan_menunggu()` | P16 (bagian 3.3); PRD 9.11, 11.1; T47, T49 |
| K30 | P25 — ekuitas harian dicatat pengguna atau diturunkan dari transaksi + kas? | **Tetap dicatat pengguna di v0.1 — diputuskan pengguna 10 Okt 2026 ("sesuai rekomendasi"), dan pembandingnya dikerjakan sekarang.** Dasbor menampilkan `nilai posisi + kas` beserta **selisihnya** terhadap ekuitas tercatat, dengan catatan bahwa selisih itu wajar (ekuitas adalah angka yang dicatat manusia, sedangkan pembandingnya hanya menjumlahkan posisi yang tercatat aplikasi + kas yang dicatat). Bila kas belum dicatat, pembandingnya **tidak ada** — bukan dianggap nol (aturan keras 2). Alasan menunda penurunan otomatis: ia menuntut **kas awal** yang belum pernah dicatat di mana pun dan aturan penilaian posisi (penutupan terakhir vs harga transaksi); menebaknya akan membuat AC-13 lulus dengan angka yang tidak bisa diperiksa. Sejak K28, arus kas posisi (dividen, hasil jual HMETD) sudah bisa dihitung, jadi jalan itu terbuka kapan saja | P25 (bagian 3.3); PRD 9.11, AC-13; K28 |
| K31 | P26 — penebusan HMETD yang jumlahnya bukan kelipatan lot | **Aturan lot tetap berlaku (PRD 10) — diputuskan pengguna 10 Okt 2026 ("sesuai rekomendasi"); yang ditambahkan hanya pemberitahuannya lebih awal.** Hak atas right issue adalah rasio × lembar, dan hasilnya tidak selalu kelipatan lot (terukur: 6.250 lembar dari 25.000 × rasio 4:1), sehingga penebusan hanya bisa dicatat sebesar bagian yang bulat lot (6.200) dan sisanya hanya bisa dijual sebagai HMETD. Sejak keputusan ini, `--hak-right-issue`, `--dasbor`, dan ringkasan keputusan **menyebutkan** keadaan itu beserta jumlah yang boleh dicatat — supaya pengguna tidak baru menemukannya saat `--catat-transaksi` menolak. Yang **tidak** dilakukan: mengecualikan penebusan HMETD dari pemeriksaan lot, sebab itu membuat "jumlah lembar selalu kelipatan lot" berarti dua hal | P26 (bagian 3.3); PRD 10, 9.11; K1; K28 |
| K32 | P27 — right issue mematikan metrik harga emiten itu di `--saring` | **Dibiarkan apa adanya di v0.1 — diputuskan pengguna 10 Okt 2026 ("sesuai rekomendasi").** PRD 9.3 menuntut harga disesuaikan terhadap right issue saat dibaca, rumus harga teoretis ex-rights (TERP) tidak ditetapkan PRD, jadi emiten yang punya right issue dalam jendela metriknya berstatus "tidak dihitung" dan keluar dari semesta likuid — terukur pada data uji: **likuid 227 → 225**. Membangun penyesuaian TERP mungkin (datanya sudah ada: penutupan sebelum ex-date, rasio, `harga_tebus` yang sejak K28 wajib diisi), tetapi ia menyentuh angka saringan yang sudah terverifikasi, dan tempatnya satu fungsi (`penyesuaian.sesuaikan`) sehingga bisa dikerjakan kapan saja. Keputusan ini **tidak** mempengaruhi posisi: right issue tidak mengubah lembar posisi (K28) | P27 (bagian 3.3); PRD 9.3, 7.2; U4; K28 |
| K33 | P28 — dividen dihitung, bukan dicatat: perlukah jalur koreksi manual? | **Belum perlu di v0.1 — diputuskan pengguna 10 Okt 2026 ("sesuai rekomendasi").** Dividen tetap **dihitung** dari `aksi_korporasi` × lembar pada tanggal ex-date (K28), dan yang tersedia untuk memeriksanya adalah rincian **per peristiwa** (tanggal, rupiah/lembar, lembar, jumlah) beserta label sumbernya. Mengoreksinya menuntut tabel arus kas posisi yang menampung baris manusia; selama angkanya masih bisa diperiksa per peristiwa terhadap mutasi rekening, tabel itu menambah satu sumber kebenaran baru tanpa menghilangkan kebutuhan memeriksanya. Bila kelak dibutuhkan, ia sekaligus menjadi bahan K30 | P28 (bagian 3.3); PRD 9.11; aturan keras 2; K28, K30 |
| K34 | P15 — "kelengkapan tesis 100%" (13.1): apakah entri "ide" tanpa tesis ikut dihitung? | **Tidak — kepatuhan hanya atas transaksi (V1–V7), diputuskan pengguna 10 Okt 2026 ("sesuai rekomendasi").** Entri berstatus `ide` memang berarti "belum ada tesis" (PRD 9.6), jadi menghitungnya sebagai pelanggaran akan menghukum pencatatan yang jujur — persis yang dihindari PRD 9.8. Kepatuhan dihitung **otomatis** dari baris yang tercatat saat jurnal (F7) dibangun, dan ia **tidak memblokir** apa pun: pencatatan transaksi nyata tetap boleh dengan peringatan + penanda (P14, sudah berlaku) | P15 (bagian 3.3); PRD 13.1, 13.2, 9.6, 9.8; P14 |
| K35 | Masa berlaku suspensi dan UMA | **Sesuai rekomendasi, diputuskan pengguna 11 Okt 2026:** suspensi aktif sampai pengumuman pembukaan kembali; UMA berlaku 30 hari kalender sejak tanggal pengumuman. Rekaman suspensi `>1 Kode` yang aksinya belum direkonsiliasi per emiten ditandai; daftar hasil pengambil belum lengkap untuk rekaman itu, sehingga `--saring` tetap menyebut **PERINGKAT SEMENTARA** | PRD 7.1, 7.3; jawaban pengguna 11 Okt 2026 |
| K36 | Bagaimana hasil rekonsiliasi per kode atas pengumuman suspensi `>1 Kode` masuk ke sistem: berkas impor atau pemeta otomatis di `notasi.py`? | **Berkas + `--impor`, sesuai rekomendasi, disetujui pengguna 12 Okt 2026.** Rekonsiliasi ditulis sebagai berkas di `.uji-data/riset-idx/` lalu dimuat lewat jalur impor yang sama dengan K11/K12/K16/K18, sehingga penulisan basis data tetap **satu jalur** dan isinya dapat diperiksa manusia sebelum masuk. Pemeta otomatis di `notasi.py` **tidak** dibangun di v0.1: penalaran yang dipakai saat merekonsiliasi (dokumen kembar, pembukaan terbatas, sesi per kode, nomor yang tercetak keliru di sumber) belum punya bentuk yang bisa dipercaya sebagai kode | PRD 7.1, 7.3; K35; T58, T59 |
| K37 | Urutan: menutup episode suspensi (UPT) dulu, atau merekonsiliasi seluruh 56 SPT multi-kode dulu? Dan kapan penanda "data suspensi belum lengkap" boleh dilepas? | **Rekonsiliasi seluruh 56 SPT multi-kode lebih dulu, penutupan episode sesudahnya, dan penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` dilepas hanya setelah seluruh 56 SPT terpetakan per kode — disetujui pengguna 12 Okt 2026.** Alasannya terukur: untuk kode yang statusnya `Suspensi di …` (dipertahankan), tanggal mulai episode yang benar bisa **lebih awal** daripada SPT terakhir yang dirujuk UPT, sehingga menutup episode lebih dulu berisiko memasang tanggal mulai yang salah. Melepas penanda lebih awal akan membuat kata "kandidat" dipakai atas data yang belum lengkap — persis yang dicegah K19/K35 | PRD 7.3, 9.3; K19, K35; `pengatur._notasi_terverifikasi` |
| K38 | Bagaimana memperlakukan rekaman API yang **dokumennya identik** (isi PDF sama, URL/nomor API berbeda)? | **Satu peristiwa per dokumen; rekaman API kedua disimpan sebagai provenance (nomor + URL), bukan baris kedua — disetujui pengguna 12 Okt 2026.** Terukur: `2024-02-20_UPT_48.pdf` dan `2024-02-20_UPT_49.pdf` identik byte-per-byte (nomor sama, `Peng-UPT-00003/BEI.PLP/02-2024`), sehingga 8 baris API = **4** peristiwa. Kembar yang sama ditemukan pada SPT: SPT_31≡SPT_32, SPT_26≡SPT_27, SPT_05≡SPT_07. Dua baris untuk satu peristiwa akan menggandakan peristiwa di rekap | PRD 7.1; T58 |
| K39 | Apakah pembukaan suspensi yang **hanya berlaku di satu pasar** (mis. Pasar Negosiasi untuk crossing) menutup episode suspensi? | **Tidak — disetujui pengguna 12 Okt 2026.** Pembukaan seperti itu dicatat sebagai peristiwa tersendiri dengan pasar yang disebut, dan episode suspensinya tetap terbuka. Berlaku untuk **ketiga** UPT OCAP yang sifatnya sama (Mei 2024, Agustus 2024, November 2024): semuanya hanya membuka Pasar Negosiasi untuk pengalihan saham hasil buyback, lalu menyatakan suspensi seluruh pasar diberlakukan kembali pada sesi yang sama. Mencatatnya sebagai "suspensi berakhir" akan salah dan tidak terlihat di keluaran mana pun | PRD 7.1, 9.3; K35 |
| K40 | Bagaimana memperlakukan efek yang **bukan saham emiten** (reksa dana/ETF) dalam data notasi? | **Tetap dicatat sebagai efek tercatat, dengan penanda di `keterangan` baris notasi — disetujui pengguna 12 Okt 2026.** Terukur: `XSBC` (Reksa Dana Indeks Simas ETF IDX30) dan `XSSI` (Reksa Dana Syariah Indeks Simas ETF JII) nyata disuspensi IDX dan dibuka 3 Jul 2024. Menghapusnya membuat daftar tidak lengkap; memasukkannya tanpa penanda membuat kriteria saham (mis. set kriteria bank/umum PRD 8.4) dihitung untuk non-saham. Kolom tersendiri **tidak** dibuat dulu — penanda di `keterangan` cukup dan tidak menuntut migrasi | PRD 8.4, 12; K21 |
| K41 | Bagaimana kode yang SPT penyebabnya **di luar cakupan API** (lebih tua dari 12 Okt 2023)? | **Tetap dicatat, dengan nomor dan tanggal SPT yang disebut di dalam UPT ditambah penanda "di luar cakupan API" — disetujui pengguna 12 Okt 2026.** Terukur: `ARTI` (UPT 23 Nov 2023 merujuk SPT 2021–2023) dan `ELTY` (UPT 19 Okt 2023 merujuk SPT 31 Jul 2023). Pencabutannya dinyatakan tegas oleh UPT, jadi menahan barisnya berarti membuang peristiwa resmi; sebaliknya, menganggapnya lengkap tanpa penanda akan menyembunyikan bahwa PDF SPT-nya belum pernah dilihat **Dijalankan 16 Okt 2026 (sesi 7) lewat K54** (bentuk barisnya) — lihat K54 dan bagian 5 ("Pelaksanaan K53 + K54"): `ELTY` 2023-07-03 → 2023-10-19 · `ARTI` 2021-11-30 → 2023-11-23, dengan penanda "di luar cakupan API" yang berbunyi bahwa PDF SPT-nya belum pernah dilihat | PRD 7.1, 7.3; K35 |
| K42 | Pengesahan usulan **U2–U17, U19, U22, dan U23** yang sudah dipakai sebagai default operasional tetapi belum dikunci | **Disahkan apa adanya sebagai keputusan, disetujui pengguna 12 Okt 2026 ("sesuai rekomendasi").** Keduapuluh usulan itu sudah berjalan di kode dan sudah diuji, jadi menahannya sebagai "usulan" membuat dokumen ini tidak lagi menggambarkan perilaku sistem yang sebenarnya. Isi tiap usulan tetap ada di bagian 2 sebagai riwayat beserta alasannya, dan sekarang berstatus **keputusan**, bukan pertanyaan | PRD 8.2, 9.2, 9.5, 9.7, 10, 11, 13.2; bagian 2 |
| K43 | Parameter bursa (B1–B5, B8) yang sumbernya **sekunder** (pemberitaan + nomor dokumen), karena seluruh `idx.co.id` masih 403 | **Tetap dipakai di v0.1 dengan label `sumber` apa adanya, dan tidak dianggap terverifikasi primer — disetujui pengguna 12 Okt 2026.** Labelnya ikut tercetak di keluaran, sehingga angka yang bertumpu pada sumber sekunder tidak pernah tampil seolah berasal dari pengumuman resmi. Bila SK primer terjangkau, entri **baru bertanggal** ditambahkan (append-only, K6) — entri lama tidak ditimpa, supaya perubahan sumber bisa ditelusuri | Aturan keras 1 & 4; PRD bagian 10; K6, K22 |
| K44 | Penggabungan daftar emiten resmi IDX (962 kode) dengan daftar KSEI yang sudah dipakai (973 kode) | **Ditahan di v0.1; aturannya ditulis sekarang supaya tidak dikarang belakangan — disetujui pengguna 12 Okt 2026.** Bila nanti dijalankan: (a) baris IDX masuk sebagai **revisi dengan `diketahui_pada` sendiri** (waktu pengamatan IDX), bukan memakai tanggal KSEI yang sama — dua isi berbeda tidak boleh berbagi satu cap waktu; (b) append-only, tidak menimpa baris KSEI; (c) kode yang hanya ada di satu sumber tetap tersimpan, dan **tidak** disimpulkan delisting dari selisih; (d) `jenis` tidak diturunkan dari sektor `Financials` saja; (e) `papan` hanya diisi bila pemetaannya dinyatakan terbuka | K12, K21, K25; PRD 7.2, 12 |
| K45 | **P29** (pelanggaran tingkat posisi V5/V7 diatribusikan ke transaksi mana) dan **P30** (arti tombol "[Tandai selesai]" PRD 11.5) | **Disahkan apa adanya, disetujui pengguna 12 Okt 2026.** P29: pelanggaran yang bukan transaksi menempel pada **transaksi terakhir posisi itu pada/sebelum tanggal kejadian**; yang tidak punya transaksi (mis. rencana melanggar batas yang belum dieksekusi) tidak mengubah rasio tetapi tetap dicetak. P30: `tanggal_tinjau` = tanggal tinjau **berikutnya**, `selesai_pada` = tanggal entri jurnal ditandai selesai (`--tandai-selesai`) | P29, P30 (bagian 3.3); PRD 9.8, 11.5, 12, 13.1 |
| K46 | Perlakuan **pengumuman 20 Feb 2024** (`Peng-S-00006/BEI.PLP/02-2024`) yang bertentangan di dalam dirinya: kalimat keputusan menyatakan suspensi **baru** untuk 34 kode, kolom status tabelnya tidak memuat satu pun `Aktif` | **Ditahan dari berkas impor sampai ada tinjauan visual halaman PDF-nya — disetujui pengguna 16 Okt 2026 ("sesuai rekomendasi").** Ke-34 barisnya tetap ada di berkas rekonsiliasi dengan penanda `PERTENTANGAN_KOLOM_STATUS`, tetapi **tidak** disiapkan menjadi baris impor. Alasannya: kedua tafsir tidak bisa dibedakan dari teks (tabel bisa berarti status *sebelum* tindakan, atau status *sesudahnya*), dan salah memilih berarti memasang tanggal mulai yang salah untuk 34 kode sekaligus — sekelas dengan kekeliruan yang dicegah aturan keras 1. Tinjauan yang dituntut kecil dan terbatas: satu halaman tabel, 34 baris **Dilepas 16 Okt 2026 (sesi 7) lewat K53** — pengumuman itu kini menempel pada `keterangan` episode yang sedang berjalan untuk ke-33 kode dan menjadi isi episode MTFN 2023–2024 yang dibentuk; 20 Feb 2024 tetap **tidak** dipakai sebagai `tanggal_mulai`. Rinciannya di bagian 5 ("Pelaksanaan K53 + K54") | `docs/riset-suspensi-multi-kode-2026-10.md` (temuan 1); PRD 7.1, 7.3; aturan keras 1 & 3; K35, K37; T59 |
| K47 | Empat kode yang berstatus `Aktif` **dua kali dalam 30 hari** (`ASMI`, `COAL`, `LCKM` 30 Jun → 30 Jul 2026; `MTFN` 30 Jun → 30 Jul 2025) tanpa pembukaan yang terpantau di antaranya | **Disiapkan apa adanya — dua peristiwa "mulai disuspensi" — dengan penanda di `keterangan`; disetujui pengguna 16 Okt 2026 ("sesuai rekomendasi").** Tidak ditahan dan tidak digabung: peristiwanya nyata di pengumuman resmi (tabel menyebut `Aktif`, kalimat keputusan menyebut jumlahnya), sedangkan menggabungkan atau membuang salah satunya berarti mengarang. Penandanya menyebut keadaannya ("dua `Aktif` berjarak 30 hari tanpa UPT terpantau; kemungkinan suspensi pertama tidak pernah berlaku atau ada pembukaan yang tidak terekam") supaya tinjauan berikutnya tahu apa yang harus dicari — bukan supaya keadaannya disembunyikan | `docs/riset-suspensi-multi-kode-2026-10.md` (temuan 2); PRD 7.1; aturan keras 2 & 3; K35, K41; T60 |
| K48 | Baris tabel yang memuat **dua kode efek** (`MYRX dan MYRXP` pada 16 Jun 2025; `CNTB` pada baris `CNTX` 1 Jul 2026) | **Penanda di `keterangan` cukup, dan tiap kode mendapat barisnya sendiri — disetujui pengguna 16 Okt 2026 ("sesuai rekomendasi").** Impor notasi bekerja per kode, jadi satu baris tabel yang memuat dua kode menghasilkan dua baris impor; keduanya menyebut asalnya ("kode kedua pada satu baris tabel bersama …"). Kolom baru **tidak** dibuat, mengikuti pola K40. Akibatnya yang ikut tercatat: pengumuman 1 Jul 2026 menyebut 13 Perusahaan Tercatat sedangkan tabelnya memuat 14 kode, dan pengumuman 16 Jun 2025 menyebut 6 saham sedangkan daftarnya 7 kode — keduanya keadaan sumber, bukan kesalahan pemetaan | `docs/riset-suspensi-multi-kode-2026-10.md` (temuan 3 & 4); PRD 7.1, 12; K40; T60 |
| K49 | Kode yang **tidak punya riwayat suspensi berkode tunggal di API** (80 dari 162) dan/atau **tidak ada di daftar emiten KSEI maupun IDX** (14 kode) | **Dimuat apa adanya dengan penanda di `keterangan` — disetujui pengguna 16 Okt 2026 ("sesuai rekomendasi").** Bagi 80 kode itu pengumuman massal adalah **satu-satunya** catatan, jadi menahannya berarti membuang peristiwa resmi; dan jalur tulis `notasi_khusus` memang tidak menuntut kodenya ada di tabel `emiten`, sehingga tidak ada yang perlu diakali. Yang **tidak** boleh dilakukan: menyimpulkan delisting dari selisih daftar (K44c), atau menghapus baris yang kodenya tidak dikenal. Keadaan "kode di luar daftar emiten" disebut per baris | `docs/riset-suspensi-multi-kode-2026-10.md` (temuan 5–7); PRD 7.1, 12; K40, K41, K44; T60 |
| K50 | Bentuk baris impor untuk baris yang **tidak menyatakan tanggal mulai** — 936 baris `dipertahankan`: apakah satu baris **per (peristiwa × kode)** seperti T60, atau satu baris **per (kode × episode)**? | **Satu baris per (kode × episode); T60 dibaca begitu, dan itu dinyatakan terbuka di sini.** Terukur saat berkas impornya ditulis: T60 apa adanya menuntut 1.090 baris, dan **850 di antaranya adalah kode yang berstatus `dipertahankan`** — pengumuman itu tidak menyatakan kapan suspensinya mulai, hanya bahwa ia masih berjalan. `tanggal_mulai` satu-satunya yang tersedia untuk mereka adalah tanggal pengumuman, dan memakainya berarti memasang tanggal mulai palsu untuk 850 baris sekaligus — persis yang dilarang aturan keras 1 & 3, dan persis kekeliruan yang dicegah K46. Karena itu tiap kode mendapat **satu baris per episode**, dengan tanggal mulai hanya dari peristiwa yang menyatakannya (kalimat keputusan), dan seluruh pengumuman `dipertahankan` yang menguatkannya masuk `keterangan` baris itu (nomor, berkas PDF, tindakan, pasar, sesi). Hasilnya **171 baris** dengan provenance **lebih lengkap** per baris daripada 1.090 baris yang tanggal mulainya dikarang. Yang tetap dipegang dari T60: bentuk kolomnya, `jenis=suspensi`, satu baris per kode untuk baris tabel dua kode (K48), dan `tanggal_selesai` hanya dari penutup UPT yang terkonfirmasi | Aturan keras 1, 2 & 3; PRD 7.1; K46, K47; T60 |
| K51 | Kapan penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` boleh dilepas, dan bagaimana caranya? | **Sudah dilepas 16 Okt 2026 (K52, sesi 5); caranya dibuktikan bekerja lebih dulu dan itu bagian dari keputusan ini.** Temuannya dua, keduanya terukur: (a) penanda tidak bisa dilepas dengan menyunting `konfigurasi/notasi-khusus.csv` — impor bersifat **menambah revisi, bukan menyinkronkan**, sehingga baris yang hanya ada di basis data tidak akan pernah berubah lewat penyuntingan berkas; (b) jalannya adalah **membangun berkas dari basis data**: ambil revisi terkini tiap kunci (2.447 baris), lepas penandanya, impor ulang sebagai **revisi baru** dengan `diketahui_pada` baru (append-only, K3/S1). Karena itu pelepasan penanda **tidak menuntut perubahan kode** — hanya berkas + impor. **Koreksi premis (16 Okt 2026, sesi 5):** catatan awal K51 menyebut berkas konfigurasi "hanya memuat 122 baris"; itu **salah alamat** — berkas yang dipakai basis data utama (`.uji-data/mejasaham/konfigurasi/notasi-khusus.csv`) memuat **2.276 baris data** sejak 11 Okt 2026, sedangkan 122 baris itu milik `.uji-data/uji-sektor/konfigurasi/notasi-khusus.csv`. Aturannya tidak berubah karenanya; sebabnya di `docs/lanjutan.md` bagian 6 | Aturan keras 3 & 7; PRD 7.3; K19, K37, K42, K52; T60; `docs/lanjutan.md` bagian 4 |
| K52 | Apakah penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` **dilepas**, dan kapan pelaksanaannya? | **Dilepas, sesuai rekomendasi — disetujui pengguna 16 Okt 2026 ("keputusan sesuai rekomendasi mu saja, catat dulu"). Pelaksanaannya DITUNDA ke sesi berikutnya**, sebab pengguna meminta tidak ada pekerjaan teknis pada sesi pencatatan ini. Urutan yang mengikat saat dijalankan: (1) **cadangkan dulu** basis data `.uji-data/mejasaham` (`--buat-cadangan`, F12), karena pelepasan ini menulis ribuan baris revisi; (2) bangun `notasi-khusus.csv` dari **revisi terkini** `notasi_khusus` (2.447 baris) dan lepas penandanya — **jangan** menyunting berkas konfigurasi yang ada (K51); (3) `--impor` sebagai revisi baru (append-only, `diketahui_pada` baru); (4) **perbarui juga** `konfigurasi/notasi-khusus.csv` supaya impor berikutnya tidak memuat kembali penanda yang sudah dilepas; (5) buktikan `--saring` berbunyi **"Kandidat teratas"**, bukan lagi PERINGKAT SEMENTARA — terukur pada basis data uji: likuid tetap 201, lolos saring 9. Konsekuensi yang diterima: sejak itu keluaran aplikasi menyatakan status notasi **terverifikasi**, dan itu memang maksud langkah ini. Yang **tidak** ikut selesai: tinjauan visual ke-34 baris 20 Feb 2024 (K46) dan 65 episode bertanggal mulai proxy — keduanya tetap disebut di `keterangan` barisnya. **Dijalankan 16 Okt 2026 (sesi 5) atas basis data `.uji-data/mejasaham`**: cadangan lebih dulu (`.uji-data/mejasaham-cadangan/20261016T165510578553+0700`) · 171 baris langkah 3 dimuat ke basis data utama (likuid 205 → 201) · berkas turunan basis data tanpa penanda dibangun (2.447 revisi terkini, 2.154 penanda dilepas) · **impor 2.447 baris baru** (bukan 2.154: 293 baris sisanya ikut tertulis karena kolom `sumber`-nya berbeda) · berkas `konfigurasi/notasi-khusus.csv` diganti turunan itu · **`--saring` berbunyi "Kandidat teratas"**, likuid 201 · lolos saring 9. **Koreksi premis, bukan aturan:** berkas `konfigurasi/notasi-khusus.csv` yang di K51 dicatat "hanya 122 baris" ternyata **berkas lain** — yang dipakai basis data utama memuat **2.276 baris data**; sebabnya di `docs/lanjutan.md` bagian 6 | PRD 7.3, 9.3; K19, K37, K46, K50, K51; T58, T61; `docs/lanjutan.md` bagian 4 aksi #15 |
| K53 | Perlakuan baris pengumuman **20 Feb 2024** (`Peng-S-00006/BEI.PLP/02-2024`) **sesudah tinjauan visualnya dijalankan** — apakah penanda `DITAHAN_K46_…` dilepas, dan apakah tanggal 20 Feb 2024 dipakai sebagai `tanggal_mulai`? | **Penandanya DILEPAS (K46 dibuka), dan 20 Feb 2024 TIDAK dipakai sebagai `tanggal_mulai` — disetujui pengguna 16 Okt 2026 ("keputusan sesuai rekomendasi mu, catet aja dulu, kulanjutkan di sesi berikutnya").** Yang dikerjakan saat dijalankan: (1) pengumuman itu masuk **`keterangan` episode yang sedang berjalan** untuk ke-33 kode (sebagai sebab yang menempel, bukan episode baru); (2) **episode MTFN 2023–2024 yang hilang dibentuk** — proxy ≤ 2023-10-30 → `tanggal_selesai` **2024-08-29** dari UPT `Peng-UPT-00011/BEI.PLP/08-2024`, terpisah dari episode 2025-06-30, dan dokumen 2023–2024 dipindahkan ke episode itu; (3) urutannya seperti K51/K52 (cadangkan dulu · bangun berkas dari **revisi terkini basis data** · impor sebagai revisi baru · perbarui `konfigurasi/notasi-khusus.csv` · buktikan `--saring` **tetap** "Kandidat teratas"). **Pelaksanaannya ditunda ke sesi berikutnya**, sebab pengguna meminta tidak ada pekerjaan teknis pada sesi pencatatan ini. Alasan yang mengunci jawabannya: halaman PDF-nya (kedua halaman, dirender lalu dilihat) **tidak memuat legenda/catatan kaki/kolom kelima** yang bisa memutuskan "status sebelum" versus "sesudah", sehingga pertanyaannya diselesaikan dari rekaman — dan rekamannya berbunyi: status ke-34 kode pada rekaman terakhir **sebelum** pengumuman **identik** dengan kolom status di pengumuman itu (**34 identik · 0 berbeda**; 24 *Seluruh Pasar* + 10 *Reguler dan Tunai*), jadi ruang lingkup tindakannya sudah berlaku sebelum tanggal itu dan kedua tafsir kolom menghasilkan akibat data yang **sama**. Bukti terkuat: UPT MTFN 29 Agu 2024 mencabut **delapan** pengumuman sekaligus, `Peng-S-00006/BEI.PLP/02-2024` nomor 6 di antaranya — suspensinya menyatu, bukan episode baru. Temuan yang ikut dikunci di sini: **episode MTFN 2023–2024 hilang dari data** (terukur: **1 dari 2.447 baris terkini** menyebut berkas lebih tua daripada `tanggal_mulai`-nya sendiri, dan baris itu MTFN) **Sudah dijalankan 16 Okt 2026 (sesi 7)** — rincian dan angkanya di bagian 5 ("Pelaksanaan K53 + K54"): **33 episode** memuat catatan pelepasan, **0 baris terkini** berpenanda `DITAHAN_K46_…`, dan MTFN kini punya **dua** episode (2023-10-30 → 2024-08-29 tertutup · 2025-06-30 terbuka). Aturan penempelannya ditentukan data — episode yang **memiliki rekaman SPT tepat sebelumnya** — sebab aturan "episode termuda" terbukti salah untuk `TECH` (episode jalur API 2024-01-09, yang akan memutus rantai SPT-nya); selisih kedua aturan itu dilaporkan per kode, jadi pilihannya bisa diperiksa | `docs/riset-suspensi-multi-kode-2026-10.md` (bagian "Tinjauan visual pengumuman 20 Feb 2024"); `.uji-data/uji-tinjauan-k46/` (`bukti-1` … `bukti-9`); PRD 7.1, 7.3; aturan keras 1 & 3; K46, K50, K51, K52; `docs/lanjutan.md` bagian 4 aksi #16 dan #17 |
| K54 | Bentuk baris untuk **kode yang hanya pencabutannya dinyatakan sumber** dan tanggal mulainya tidak diketahui sama sekali (**K41**: `ARTI`, `ELTY`) — sedangkan `tanggal_mulai` adalah bagian kunci baris | **Pakai tanggal pengumuman SPT terawal yang dirujuk UPT sebagai `tanggal_mulai` proxy, dan tutup dengan `tanggal_selesai` dari UPT-nya — disetujui pengguna 16 Okt 2026 ("keputusan sesuai rekomendasi mu, catet aja dulu").** Terukur yang dipakai: **`ELTY` 2023-07-03 → 2023-10-19** (UPT `Peng-UPT-00002/BEI.PLP/10-2023`, SPT yang dirujuk bertanggal 3 Jul 2023 & 31 Jul 2023) · **`ARTI` 2021-11-30 → 2023-11-23** (UPT `Peng-UPT-00003/BEI.PLP/11-2023`, SPT yang dirujuk 30 Nov 2021 … 31 Jul 2023). `keterangan`-nya memuat nomor+tanggal SPT itu **dan** penanda **"di luar cakupan API"** yang berbunyi bahwa **PDF SPT-nya belum pernah dilihat** serta bahwa tanggal mulai itu **tanggal pengumuman SPT**, bukan tanggal efektif. Yang **tidak** dipakai: tanggal UPT-nya sendiri sebagai mulai — itu tanggal **pencabutan**, sehingga barisnya menjadi bersuspensi nol hari dan menyembunyikan bahwa suspensinya berjalan berbulan-bulan. **Pelaksanaannya ditunda ke sesi berikutnya** bersama K53. Yang membuat keputusan ini perlu: keputusan K41 sudah dikunci 12 Okt 2026 tetapi **belum pernah dijalankan atas data** — terukur: penanda "di luar cakupan API" **0 kali** di seluruh `notasi_khusus` (semua revisi) dan **0 kali** di berkas impor, `ELTY` **0 baris** di basis data dan 0 baris di berkas impor, dan `ARTI` punya baris dari jalur lain (mulai 2024-07-01) tanpa penanda yang diminta **Sudah dijalankan 16 Okt 2026 (sesi 7)** bersama K53 — lihat bagian 5: `ELTY` **2023-07-03 → 2023-10-19** dan `ARTI` **2021-11-30 → 2023-11-23** kini ada di `notasi_khusus` (masing-masing dengan penanda "di luar cakupan API", 2 baris terkini). Tanggal proxy-nya **diperiksa ke teks UPT-nya**, bukan diketik ulang: tanggal terawal di bagian "Sehubungan dengan:" diparse dari kedua PDF UPT dan hasilnya **sama** dengan yang diputuskan; nomor SPT-nya diambil dari kolom `spt_nomor_dirujuk` kutipan UPT (7 nomor untuk ELTY, 19 untuk ARTI). Baris `ARTI` yang sudah ada (mulai 2024-07-01) diberi label "episode 2 dari 2" | `docs/keputusan.md` K41; `docs/riset-suspensi-multi-kode-2026-10.md` (batas bukti + tinjauan 20 Feb 2024); `.uji-data/riset-idx/rekonsiliasi-upt-per-kode-20261012.csv`; `.uji-data/uji-tinjauan-k46/bukti-9-K41-tidak-dijalankan.txt`; PRD 7.1; aturan keras 1 & 3; `docs/lanjutan.md` bagian 4 aksi #17 |
| K55 | Boleh **panel jendela** (PRD 11) menulis ke basis data — catat transaksi, simpan rencana, catat jurnal, impor, cadangan/F12 — atau semua penulisan tetap lewat baris perintah? | **Belum menulis: jendela tahap ini **membaca** saja, dan tindakan tulis menjadi tahap tersendiri (aksi #19 di `docs/lanjutan.md`) — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Syarat yang mengikat tahap itu: (a) memakai **fungsi inti yang sama** dengan baris perintah (`posisi.catat_transaksi`, `risiko.simpan`, `jurnal.catat`, `cadangan.*`) — bukan jalur tulis kedua; (b) **konfirmasi sebelum menulis**; (c) perilaku saat **kunci tulis sedang dipegang proses lain** ditetapkan lebih dulu (A2/AC-19: jendela dan `--refresh` tidak menulis bersamaan; kunci tulis SQLite dengan `busy_timeout` 5 detik), termasuk bunyi pesannya; (d) pesan galat yang **sama** dengan baris perintah | Belum ada satu pun keputusan tentang (c), dan menjawabnya sambil menulis berarti menetapkan perilaku penulisan yang paling sulit diuji secara diam-diam. Jendela yang menulis lewat jalur kedua juga akan berbeda dari baris perintah begitu salah satunya disunting — kelas kesalahan yang sudah terbukti di sesi yang sama (aturan tesis wajib sempat bercabang dua, T65). Yang **tidak** menunggu: seluruh layar baca sudah jalan (aksi #10 tahap 1, T65) |
| K56 | Kalkulator risiko di jendela: boleh menghitung untuk kode **apa pun**, atau tetap menuntut kandidat berstatus watchlist/rencana seperti `--hitung-risiko` (PRD 9.6)? | **Tetap menuntut tesis — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Aturannya tinggal di **satu** tempat, `kandidat.untuk_rencana` (T65); jendela memakai aturan yang sama, termasuk **menolak memilih entri pertama diam-diam** ketika satu kode punya beberapa entri kandidat, dan pesannya sama dengan baris perintah. Alternatifnya — kalkulator bebas, hanya tombol *simpan rencana* yang menuntut tesis — ditolak: ia membuat dua mode berbeda tepat pada aturan yang paling mudah salah, dan "hitungan tanpa tesis" tetap akan menuntut jawaban yang sama begitu rencananya hendak disimpan | PRD 9.6, 9.7; aturan keras 1; T65; K13 |
| K57 | Rasio bank (NPL/CAR/BOPO/NIM) untuk **49 emiten** ber-jenis `bank_keuangan`: diisi manusia, atau bank dibiarkan keluar dari peringkat? | **Diisi manusia, dan aplikasi menyiapkan kerangkanya — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Terukur 17 Okt 2026: tabel `rasio_bank` **0 baris** di basis data lokal, sedangkan `--saring` menyebut **49 emiten** bank; akibatnya keempat kriteria bank berstatus **"tidak dihitung"** (aturan keras 2) dan **bank tidak dapat masuk peringkat sama sekali** — bukan karena banknya buruk, melainkan karena datanya tidak ada. Yang **tetap tidak** dibangun: jalur otomatis dari PDF publikasi bank (K24). Kerangkanya berisi **daftar kode** bank dari `v_emiten_terkini` (supaya tidak ada kode yang salah eja) dengan **seluruh angka dan tanggal dikosongkan** — dan baris yang seluruh rasionya kosong memang **ditolak pembacanya**, jadi kerangka itu **tidak** bisa "terimpor sebagai nol" | Angka rasio bank diterbitkan terpisah dari laporan keuangan dan tidak ada di sumber data yang dipakai (K24), sedangkan akibat "tidak dihitung" di sini bukan satu metrik yang hilang, melainkan **satu sektor penuh yang tidak pernah muncul di daftar**. Kerangka daftar kode adalah bagian yang paling mudah salah kalau diketik manusia (916 kode pada basis data uji, 49 di antaranya bank), dan justru itu yang bisa disiapkan aplikasi — sisanya menuntut sumber resmi dan tetap di tangan Anda |
| K58 | Dasbor (PRD 11.1) selalu menulis kalimat tetap *"rezim pasar & breadth belum dapat dinilai … `harga_indeks` … belum diisi sumbernya"*, padahal `harga_indeks` **terisi** dan saringan menghitung breadth/rezim pada snapshot yang sama. Mana yang benar? | **Dasbor **menampilkan** IHSG (penutupan terakhir + perubahannya), **rezim pasar**, dan **breadth**, memakai fungsi yang sama dengan saringan (`metrik.breadth`, `metrik.rezim_pasar`); kalimat tetap itu **dibuang** — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Cacat yang mendasarinya, terukur 17 Okt 2026: `harga_indeks` memuat **IHSG 1.199 bar dan LQ45 1.199 bar** (2021-10-11 → 2026-10-09; `--refresh` memang mengambil `^JKSE`/`^JKLQ45`, `mejasaham/pengambil.py` baris 60–62), dan `--saring` atas snapshot itu mencetak **`breadth 39,1% · rezim RISK-OFF`**, sedangkan dasbor pada snapshot yang sama menyatakan keduanya belum dapat dinilai. Batasnya dipegang `metrik.rezim_pasar` yang sudah ada: tanpa ≥200 penutupan IHSG hasilnya **NETRAL beserta sebabnya**, bukan angka karangan | PRD 11.1 secara eksplisit meminta baris itu di dasbor (*"IHSG … \| Rezim RISK-ON \| breadth 61%"*), dan kalimat tetap itu salah **ke arah yang paling merugikan**: ia menyembunyikan satu baris halaman depan sambil menyatakan datanya tidak ada. Dua keluaran yang bertentangan (dasbor vs saringan) juga persis kelas kesalahan yang dicegah T65 — karena itu aturannya tetap **satu tempat**, bukan disalin ke dasbor. Beberapa klaim dokumen ikut salah karenanya dan sudah ditandai: `docs/lanjutan.md` — baris dasbor di bagian 2 **dikoreksi**, dan dua daftar sisa pekerjaan di bagian 9 diberi **kotak koreksi**; serta `docs/keputusan.md` bagian 5 (dua daftar lama di sana **dibiarkan sebagai riwayat** — yang berlaku adalah K58 ini, bukan daftar itu) |
| K59 | **Perilaku jendela saat kunci tulis basis data dipegang proses lain, dan cakupan tindakan tulis tahap pertama** — syarat (c) dan (e) yang ditinggalkan K55 | **Disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi"), dan inilah yang mengunci perilaku penulisan jendela (aksi #19).** (a) **Menunggu** sampai `busy_timeout` (5 detik, sudah terpasang di koneksi) sambil menampilkan "bekerja…", lalu bila tetap gagal **berhenti dengan pesan** — bukan berhenti di detik pertama; (b) pesannya **wajib** memuat kalimat bahwa **jendela belum menulis apa pun** (pengguna harus tahu tidak ada yang setengah tertulis), menyebut proses lain sebagai sebab (mis. `--refresh`), dan menyarankan mencoba lagi; (c) **cakupan bertahap**: dahulu tiga pencatat transaksi (`posisi.catat_transaksi`, `risiko.simpan`, `jurnal.catat`), **lalu** impor, dan **cadangan/pulihkan paling akhir** karena `--pulihkan` menimpa basis data; (d) **konfirmasi sebelum menulis untuk semua** tindakan, berisi ringkasan angka yang akan ditulis (kode, lembar, harga, biaya) — untuk pulihkan, konfirmasi kedua yang menyebut folder cadangannya; (e) **F12 di jendela**: **cadangan + daftar** pada tahap ini, **pulihkan menunggu tahap tersendiri** | K55 sudah menetapkan bahwa perilaku inilah yang **harus** ditetapkan lebih dulu, bukan dikarang sambil menulis: ia menyangkut apa yang terjadi pada basis data ketika dua proses menulis bersamaan (A2/AC-19), dan kelas kesalahan yang paling mahal di aplikasi ini adalah penulisan yang tampak berhasil padahal tidak. Memilih **menunggu** (bukan berhenti di detik pertama) karena penolakan yang terlalu cepat menolak penulisan yang sebenarnya bisa berhasil sepersekian detik kemudian; batas 5 detik dipakai apa adanya dari `busy_timeout` yang sudah ada, bukan angka baru. Konfirmasi untuk **semua** (bukan hanya yang merusak) karena setiap baris transaksi/jurnal adalah catatan keputusan yang tidak bisa dihapus (append-only) — salah catat jurnal berarti riwayat kepatuhan yang salah. Bentuk teknisnya **T69** (`docs/arsitektur.md`) |
| K60 | **Cacat PySide6 6.12.0 + CPython 3.14.7** (proses mati di uji jendela): langkah mana yang ditempuh? | **Urutannya: (a) laporan upstream lebih dulu, lalu (b) uji pada Python 3.13 — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** (a) Draf laporannya sudah disiapkan (`docs/riset-pyside6-gc-2026-10.md` bagian 7, lengkap dengan lingkungan, tabel angka, dan `tests/test_ui_jendela.py` sebagai repro) dan **dikirim oleh pengguna** — sesi agen tidak bisa mengirimkannya atas nama Anda; (b) sesudah itu **uji Python 3.13** dengan PySide6 6.12.0 yang sama: bila 12 jalan uji jendela tidak lagi mati, **pin versi Python** adalah jawabannya — dan itu **keputusan dependensi**, jadi pemasangan interpreternya dilaporkan lebih dulu saat dikerjakan (aturan `adding-dependencies`); (c)+(d) uji PySide6 lain dan "terima T68 apa adanya" **tidak** dipilih sekarang, tetapi tetap tercatat sebagai jalan yang tersisa. Penangkal **T68** tetap berlaku sampai ada jawaban yang lebih baik | Kombinasi itu **didukung** paketnya (`Requires-Python >=3.10,<3.16`, classifier 3.14), jadi ini cacat, bukan pemakaian di luar dukungan — karena itu laporan upstream adalah hal yang benar untuk dilakukan lebih dulu, dan ia juga satu-satunya langkah yang tidak menuntut perubahan apa pun di mesin ini. Urutan (a) lalu (b) dipilih sebab (b) menuntut pemasangan interpreter (biaya + risiko lingkungan), sedangkan (a) hanya menuntut salinan draf yang sudah ada. Yang **tidak** boleh dipakai sebagai "perbaikan": mematikan GC di seluruh proses, atau memindahkan pekerjaan kembali ke utas tampilan (T65) |
| K61 | **Konteks pasar di dasbor: dihitung ulang tiap kali, atau disimpan saat `--saring`?** (usulan **U26**) | **Tetap dihitung ulang (keadaan sekarang) — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi"); harganya disebut apa adanya: `--dasbor` 2,8 dtk → 33–61 dtk pada basis data 999.421 bar, setara `--saring`.** **U26 tidak ditutup**: bila suatu saat Anda memintanya, aturannya sudah disepakati lebih dulu — angka tersimpan **hanya** boleh ditampilkan bila `id_snapshot` **dan** versi presetnya masih sama dengan keadaan sekarang; selain itu dihitung ulang atau dinyatakan **"tidak dapat dinilai"**. Yang tersimpan adalah breadth + rezim + penutupan indeks terakhir, ditulis saat `--saring` | Angka pasar yang benar tidak boleh muncul dari dua jalur yang berbeda (K58/T66 menolak "menyalin hasilnya"), dan biaya menghitung ulang adalah harga yang **terlihat** (beban saringan) sedangkan bahaya angka tersimpan adalah harga yang **tidak terlihat** — angka basi terbaca sebagai keadaan hari ini. Karena itu menghitung ulang dipilih selama belum ada kebutuhan yang menuntut sebaliknya; aturan kebasiannya disepakati sekarang supaya pekerjaan itu (bila diminta) tidak perlu bertanya lagi. **DIPERBARUI 19 Okt 2026 (sesi 34): SUDAH DIJALANKAN sebagai U26/aksi #23** — pengguna memilih “#23/U26 — simpan konteks pasar saat --saring” saat sesi baru diminta “Lanjutkan”, jadi pemicu eksplisit yang dituntut K61 terpenuhi. Bentuknya **persis aturan yang sudah disepakati**, ditambah dua kunci yang sama-sama bagian dari arti angkanya: **(a)** `--saring` (hanya bila `simpan=True`) menulis breadth + rezim + penutupan indeks terakhir ke `konteks_pasar` (migrasi 015) lewat `konteks_pasar.simpan`; **(b)** `dasbor.susun` membacanya lewat `konteks_pasar.muat` **hanya** bila `id_snapshot`, `id_preset`, `sumber_harga`, dan `versi_hitung` (`pasar-1`) semuanya sama — keempatnya di WHERE, bukan pencocokan di Python; **(c)** bila tidak cocok, dasbor **menghitung ulang** lewat jalur yang sama dengan saringan, dan **tidak menulis** apa pun; **(d)** `--kode` (`simpan=False`) tidak menulis konteks; **(e)** kegagalan menulis konteks menjadi **peringatan** (skor sudah sah; dasbor akan menghitung ulang), bukan pembatalan saringan. **Terukur atas salinan basis data kerja (snapshot 13):** `--dasbor` **18,95 dtk → 0,74 dtk (25,7×)**, baris `Pasar` **identik** sebelum/sesudah, `--saring` **18,16 dtk**; suite **906 lulus**. **Batas yang disengaja:** dasbor **pertama** sesudah `--refresh` masih membayar hitung ulang sampai `--saring` dijalankan pada snapshot baru — menghitung ulang selalu benar, sedangkan memakai angka snapshot lama tidak. Detail teknis **T80**; bukti `.uji-data/uji-k61/bukti/` |
| K62 | **Sesudah #19b dan #19c, tindakan tulis mana yang masuk jendela lebih dulu?** (P34) | **Ikuti K59 c apa adanya — #19b impor → #19c cadangan + daftar (F12) — lalu #19d = `ubah-stop` + keputusan right issue; `ubah-stop` TIDAK diselipkan sebelum impor — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Yang dipilih sebagai tindakan tulis berikutnya sesudahnya ialah **`ubah-stop`** (stop trailing), bukan `--ekuitas-harian` atau entri kandidat: hanya `ubah-stop` (dan keputusan right issue) yang **dituntut layar dasbor sendiri** lewat daftar tindakan menunggu (`stop_tertembus`, `tanpa_stop`, `pembatal_terpicu`), sedangkan yang lain tidak pernah muncul sebagai ajakan bertindak | Urutan #19b/#19c sudah dikunci K59 c, dan tidak ada alasan cukup untuk membukanya lagi: `ubah-stop` **masih bisa dicatat dari baris perintah** tanpa kehilangan apa pun (tidak ada yang tertahan), sedangkan impor adalah jalan masuk data yang seluruh alur lain bergantung padanya. Yang membuat `ubah-stop` dipilih sebagai #19d adalah alasannya berbeda dari K55: K55 menyebut lima tindakan karena itu yang dituntut PRD 11, sedangkan di sini yang menentukan adalah **layar yang sudah jalan** mengajukan tindakan yang tidak bisa dieksekusi dari jendela — dan itu bentuk janji yang sama dengan K58 (layar tidak boleh menuntut sesuatu yang tidak bisa dikerjakan). Bentuk teknisnya **T71** |
| K63 | **PRD 9.7 di jendela: pilihan "pakai ukuran yang patuh" belum ada — hanya "terima pelanggaran"** (P35) | **Ditambahkan: layar 11.4 memperoleh pilihan "Pakai ukuran patuh" (memakai `risiko.pakai_ukuran` yang sudah ada), dikerjakan bersama #19b — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Urutannya mengikat: ukuran patuh dihitung **lebih dulu**, lalu dialog konfirmasi muncul dengan **angka yang sudah patuh** — sehingga ringkasan konfirmasi dan baris yang tersimpan tetap angka yang sama (K59 d). Menerima pelanggaran tetap mungkin, dan pilihan itu tetap tercatat di `catatan` rencana | PRD 9.7 menuntut rencana yang melanggar disimpan **setelah pengguna memilih** — *"ukuran yang patuh, atau menerima pelanggarannya secara tercatat"* — dan baris perintah memang menyediakan keduanya (`--pakai-ukuran-patuh` dan `--terima-pelanggaran`). Jendela yang hanya menyediakan "terima" membuat pengguna jendela **harus pindah ke baris perintah** untuk pilihan yang justru diminta PRD, dan itu bertentangan dengan peran jendela sebagai jalur harian (K64). Alternatif "biarkan, cukup sebutkan di layar" ditolak karena ia menyelesaikan kelengkapan **kalimat**, bukan kelengkapan **pilihan** |
| K64 | **Seberapa lengkap jendela dibanding baris perintah?** (P36) | **Jendela = jalur harian; baris perintah tetap jalur lengkap — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Yang **wajib** masuk jendela: **pilihan rencana & posisi dari daftar** (bukan mengetik nomor `#1`), dan itu bagian dari pengerjaan #19b/#19d — bukan tambahan opsional. Yang **tetap** hanya di baris perintah: `--id-posisi` eksplisit, pajak/biaya yang dicatat pengguna, pilihan broker, ekspor, entri kandidat, `--ekuitas-harian`, dan **`--pulihkan`** | Yang menentukan bukan "berapa banyak kotak", melainkan **jalan salah yang bisa ditutup**: salah **mengetik** nomor rencana menempelkan eksekusi pada rencana yang salah, dan itu tidak terlihat di layar mana pun — persis kelas kesalahan yang sudah ditolak K56/T65 ("jangan pilih entri pertama diam-diam"). Daftar pilihan menutupnya **tanpa** memindahkan keputusan ke aplikasi: yang tetap dipilih manusia, yang dihilangkan hanya salah ketik. Paritas penuh ditolak karena menambah kotak yang jarang dipakai sekaligus menambah jalan salah-ketik; `--pulihkan` tetap tidak masuk jendela karena menimpa basis data (K59 e). Bentuk teknisnya **T71** |
| K65 | **Tafsir K64 ketika #19b dikerjakan: bolehkah jendela menerima nomor rencana/posisi yang *diketik bebas*** (bukan hanya dipilih dari daftar)? | **Tidak — jendela memilih dari daftar saja; tidak ada kotak isian bebas untuk `id_rencana`/`id_posisi`/revisi rencana — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi").** Angka "`--id-posisi` eksplisit" pada K64 dibaca sebagai **jalan baris perintah** untuk hal yang sama, bukan kotak yang harus disalin ke jendela: yang ditulis tetap `id_rencana`/`id_posisi` yang sama di dua mode, dan jendela hanya menghilangkan salah ketiknya | Menyalin kotak bebas ke jendela akan mengembalikan tepat jalan salah yang K64 tutup (nomor yang salah ketik menempelkan eksekusi pada baris yang salah, dan tidak terlihat di layar mana pun). Kalau kelak pengguna memang ingin mengetik nomor di jendela, itu keputusan baru — bukan tafsir dari K64 |
| K66 | **Laporan cacat PySide6 ke Qt: siapa yang mengirimnya?** (P37) | **Pengguna yang mengirim; sesi agen menyiapkan berkas siap-tempel — dijawab pengguna 17 Okt 2026 ("sesuai rekomendasi").** Berkasnya **`docs/laporan-pyside6-siap-kirim.md`**: teks Inggris siap tempel, langkah mengirim menurut halaman resmi Qt (pelacak `bugreports.qt.io/browse/PYSIDE`, Project *Qt for Python*, Type *Bug*, Component **PySide**, reproducer **wajib berupa lampiran berkas**), daftar lampiran, dan batas yang disebut apa adanya (tidak ada reproducer minimal — dua repro sintetis tidak memicunya dalam 30 dan 48 putaran). **Berkas itu DIPERBARUI 19 Okt 2026 (sesi 21)** sesudah K69: kini memuat **kontrol yang gagal** (2 dari 12 jalan **suite penuh** mati di 3.14.7), lampiran **"sisa suite uji"** (sebab berkas uji sendirian 0 dari 24 jalan), dan catatan bahwa 2 vs 0 di 3.13 **belum bermakna** (p ≈ 0,48). Sesudah terkirim, tautan isunya dicatat di `docs/riset-pyside6-gc-2026-10.md` | Laporan itu menyatakan pengalaman **pengguna** dan dikirim atas nama akunnya; K60 a sudah memisahkan "draf siap" dari "dikirim", dan pemisahan itu yang membuat gerbang K60 b punya titik rujuk |
| K67 | **Uji Python 3.13 (K60 b): dialihkan ke sesi agen?** (P38) | **Ya, dialihkan — dijawab pengguna 17 Okt 2026 ("sesuai rekomendasi"), pemasangannya **disetujui pada sesi yang sama**, dan ujinya **sudah dijalankan**.** Hasilnya: **belum dapat disimpulkan.** Rinciannya `docs/riset-pyside6-gc-2026-10.md` bagian 8.5. Yang terukur: lingkungan terpisah **`.tmp/py313`** (CPython **3.13.14** lewat `uv` yang sudah ada; unduhan interpreter **20,9 MiB**; env **767 MB**; PySide6 6.12.0 + shiboken6 6.12.0 + pytest 9.1.1, `uv pip check` bersih; `.venv` repo tidak disentuh). A/B 12 jalan **dengan** dan **tanpa** penangkal T68, di 3.13 **dan** 3.14: **0 kematian di keempatnya** — padahal pengukuran sesi 10 mencatat **7 dari 18** jalan mati tanpa penangkal di 3.14.7. Jadi cacatnya **bergantung waktu dan tidak selalu dapat direproduksi**, dan "pin versi Python" **belum** bisa diputuskan (itu hanya sah bila 3.13 jelas tidak mati sementara 3.14 jelas mati pada kondisi yang sama). **Langkah berikutnya menurut K60:** buat cacatnya reproduktif lagi (kandidat: seluruh suite 12× tanpa penangkal) **atau** uji **versi PySide6 lain** dengan 3.14.7; **T68 tetap dipakai** — urutan itu dikunci **K69** | Pemasangan interpreter menetap di mesin pengguna: itu kelas keputusan dependensi, dan K60 b sendiri menuntut pemasangannya dilaporkan lebih dulu. Memakai `uv` dipilih karena ia **sudah terpasang** — menambah dependensi baru untuk satu uji justru melanggar urutan "pakai dulu yang sudah ada". Kesimpulan "belum dapat disimpulkan" dilaporkan apa adanya: menyebut 3.13 sebagai jawabannya hanya karena 0 kematian di 12 jalan akan menyesatkan, sebab 0 kematian itu juga terjadi di 3.14 pada hari yang sama |
| K68 | **`rasio-bank.csv`: sesi agen boleh mengumpulkan angkanya?** (P39) | **Boleh sampai batas kandidat + kutipan resmi; yang masuk basis data tetap menunggu verifikasi pengguna — dijawab pengguna 17 Okt 2026 ("sesuai rekomendasi").** Langkah pertamanya **sudah dijalankan** (baca-saja atas salinan uji): lingkupnya 49 bank, dan **0 bank tertahan *hanya* oleh rasio bank** — ke-49 tertahan rasio **dan** metrik lain (`roe_5t` tidak dinilai, `adtv20`/`tren_ma200`/`kekuatan_relatif` gagal, `per_relatif_sektor`/`pbv_relatif_sektor` tidak dinilai). Jadi **mengisi `rasio-bank.csv` saja tidak membuat satu bank pun masuk peringkat** — itu harus dikatakan sebelum pekerjaannya dimulai. K24 (jalur otomatis PDF tidak dibangun) dan aturan keras 1 **tidak berubah**; angka yang belum disahkan pengguna tidak masuk basis data. **Diperbarui K83 (sesi 30):** **pemeriksaan ulang transkripsi** dialihkan ke agen dengan pagar "cocok persis" (aksi #29); persetujuan bahwa publikasi resmi itulah dasarnya tetap milik pengguna. **Dijalankan sesi 31:** 14/14 sel cocok → **dua baris (BBCA, BRIS) masuk basis data** (snapshot 12); `--saring` belum berubah karena `jenis` 973 emiten kosong; yang tersisa milik pengguna **sudah dikunci 19 Okt 2026 ("sesuai rekomendasi"): U34 → K86 (21 Agu dipertahankan) dan 44 bank → K87 (ditunda)** | Bank tidak bisa masuk peringkat selama metrik kualitasnya lubang (K57), dan rasio bank hanya **satu** dari lubang itu. Mengukur lingkupnya lebih dulu mengubah janji "isi rasio lalu bank masuk peringkat" menjadi yang sebenarnya — persis yang dijaga aturan keras 2 (metrik tanpa data berstatus "tidak dihitung", bukan diisi tebakan) |
| K69 | **Langkah lanjutan cacat PySide6 sesudah uji Python 3.13 yang inkonklusif: apa urutannya?** | **Reproduksi ulang cacatnya LEBIH DULU (kontrolnya harus gagal), baru membandingkan versi; pin versi Python hanya sah bila kontrolnya gagal di satu versi dan tidak di versi lain — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi mu aja"), dicatat dulu, dikerjakan di sesi baru.** Urutan mengikatnya: (1) **seluruh suite 12× tanpa penangkal** di CPython 3.14.7 (beban lebih besar daripada satu berkas uji — mendekati kondisi sesi 10 yang mengukur 7/18 mati); (2) **hanya bila ada yang mati**, ulangi perintah yang sama di 3.13.14 sebagai A/B — dan **keputusan pin versi Python adalah keputusan dependensi tersendiri** (mengubah pin K3), bukan lanjutan otomatis; (3) bila reproduksi tetap tidak muncul (atau A/B seri), langkah K60 berikutnya = **uji versi PySide6 lain** dengan 3.14.7, dengan **laporan pemasangan lebih dulu** (pola K67). **T68 tetap dipakai di semua cabang**, dan laporan upstream (K66) **tidak** menunggu langkah ini. Rencana teknis + plugin + patokan "mati" ada di `docs/riset-pyside6-gc-2026-10.md` bagian 9. **— SUDAH DIJALANKAN 19 Okt 2026 (sesi 21):** langkah 1 **berhasil mereproduksi** (2 dari 12 jalan **suite penuh** mati di 3.14.7, `Fatal Python error: Aborted`), lalu langkah 2 (**A/B di 3.13.14**) = **0 dari 12**; hasil, bukti, dan bacaannya di `docs/riset-pyside6-gc-2026-10.md` **bagian 10**. Langkah 3 (versi PySide6 lain) **tidak** dipicu. Keputusan **pin versi Python** dicatat sebagai **U31** (rekomendasi sesi itu: **jangan pin sekarang** — 2 vs 0 dengan p ≈ 0,48 belum membedakan apa pun), dan **diputuskan pengguna 19 Okt 2026 (sesi 22) → K74: jangan pin; T68 tetap** | 8.5 menghasilkan "0 kematian di 24 jalan tanpa penangkal" di **kedua** versi — jadi tidak ada yang bisa dibandingkan. Menyimpulkan "3.13 menyelesaikannya" dari angka itu akan salah, dan memin versi Python berdasarkan kesimpulan salah adalah keputusan dependensi yang mahal untuk dibatalkan. Reproduksi lebih dulu juga yang membuat laporan upstream (K66) punya kontrol yang bisa ditunjukkan ke pelacak Qt |
| K70 | **Folder tujuan cadangan: tetap dari konfigurasi, atau dipilih per-cadangan dari jendela?** (U30, muncul saat aksi #19c dikerjakan) | **Tetap dari konfigurasi — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasimu aja, catet dulu, biar kulanjutkan di sesi baru").** Lokasi cadangan ditentukan **sekali** lewat `--folder-cadangan`/`MEJASAHAM_BACKUP` (bawaan: folder saudara folder data), dan jendela **menyebut** folder itu di dialog konfirmasi sebelum menulis — bukan menyediakan kotak pilih folder per-cadangan. Kotak pilih itu **tidak** ditutup untuk selamanya: bila Anda memintanya, itu keputusan tersendiri (dan bentuknya mengikuti #19c/T73: folder yang **dipilih**, konfirmasi menyebut folder yang **sama** dengan yang ditulis). Yang tetap berlaku di semua cabang: syarat "di luar folder data" ditolak **sebelum** konfirmasi (`cadangan.periksa_tujuan`, T73) | Cadangan yang ditulis ke folder yang tidak diharapkan adalah cadangan yang tidak ditemukan saat dibutuhkan, dan itu justru pada tindakan yang dicari ketika data sudah bermasalah. Karena itu #19c memilih **menyebut** folder tujuannya (terukur: dialog + pesan hasil + daftar) alih-alih menambah satu jalan salah-lokasi yang tidak terlihat di layar. Yang **belum** tertutup, disebut apa adanya: pengguna jendela yang tidak pernah menjalankan `--folder-cadangan` mendapat cadangan di **disk yang sama** dengan datanya, sedangkan PRD 9.12 menyebut "lokasi pilihan pengguna di luar folder data, mis. disk eksternal" — jadi lokasinya perlu diarahkan sekali. Itu **jalan yang sudah ada** (bukan fitur yang hilang), dan menambahkan kotak pilihan menuntut keputusan baru tentang apa yang terjadi bila foldernya tidak bisa ditulis atau di dalam folder data — bukan tafsir dari U30 |
| K71 | **Cacat temuan sesi 18: keputusan `tebus` membuang `--lembar`/`--harga`/`--biaya` diam-diam** (jalur baris perintah) | **Diperbaiki — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi mu saja, catet dulu"); pelaksanaannya aksi #24, sudah dijalankan 19 Okt 2026 (sesi 20) → T75.** Bentuknya mengikuti pemeriksaan yang **sudah ada** untuk arah sebaliknya: `posisi.catat_keputusan_right_issue` menolak `lembar`/`harga`/`biaya` untuk **semua** keputusan selain `jual_hmetd` — termasuk `tebus` — dengan pesan yang menyebut bahwa yang menaikkan lembar adalah `transaksi` (T51), bukan keputusan itu. Satu uji baru yang **terbukti gagal pada kode sekarang** (menjadi dua uji: inti + jalur baris perintah, keduanya gagal pada worktree `HEAD`), dan jendela tetap menolaknya lebih dulu (`ui/tulis.py`) — jalur baris perintah tidak boleh tetap menjadi satu-satunya tempat yang membuang isian tanpa pesan | Aturan keras 7 (gagal itu berisik); PRD 9.11; T51; bukti sesi 18 di bagian 5 |
| K72 | **Cacat temuan sesi 18: `catatan` keputusan right issue menggelembung tiap revisi** | **Diperbaiki — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi mu saja, catet dulu"); pelaksanaannya aksi #25, sudah dijalankan 19 Okt 2026 (sesi 20) → T75.** Bentuknya: catatan **turunan** (`catatan_kaki` — hasil pemeriksaan inti yang teksnya sama tiap revisi) **tidak ditambahkan lagi** bila kalimatnya sudah ada di catatan revisi sebelumnya, sedangkan catatan yang **dinyatakan pengguna** dan `pesan_revisi` tetap disambung apa adanya. Alasan yang mengikat: riwayat lengkap sudah tersimpan di **baris revisinya masing-masing** (append-only), jadi menyalinnya berulang kali adalah duplikasi — dan yang terukur di sesi 18 adalah kalimat yang sama muncul sekali per revisi (revisi ke-5 memuatnya lima kali) | Aturan keras 3 (riwayat tidak hilang karena tidak disalin); PRD 9.11; K45 (P29); bukti sesi 18 di bagian 5 |
| K73 | **Urutan pekerjaan berikutnya sesudah #19d: dua perbaikan cacat, riset PySide6, atau mengisi `rasio-bank.csv`?** | **Dua perbaikan kecil dulu (#24, #25), lalu riset K69, lalu #21b — disetujui pengguna 17 Okt 2026 ("sesuai rekomendasi mu saja, catet dulu").** Alasan urutannya: (a) #24/#25 menutup dua cacat yang **sudah terukur** dan menyentuh jalur yang **baru saja dikerjakan** #19d, jadi perubahannya sempit (satu syarat, satu penyambungan catatan, dua uji); (b) **K69** (reproduksi ulang cacat PySide6) **mekanis dan tidak menunggu apa pun**, dan hasilnya dibutuhkan laporan upstream yang tinggal Anda kirim (K66); (c) **#21b** (`rasio-bank.csv`) sengaja **paling akhir** karena ia menuntut **verifikasi Anda** atas angka kandidatnya (K68) sekaligus hasilnya sudah terukur kecil: **0 dari 49 bank tertahan *hanya* oleh rasio bank**, jadi ia tidak membuka peringkat bank dengan sendirinya. **`--pulihkan` tidak masuk urutan ini** — K59 e/K64 menetapkannya sebagai batas cakupan, bukan pekerjaan tertunda | Aturan kerja K4 (berhenti tiap tahap); K68; K69; K59 e; PRD 9.11/9.12 |
| K74 | **Sesudah K69 (reproduksi 2/12 mati di 3.14.7, A/B 0/12 di 3.13.14): pin CPython 3.13 untuk proyek, atau tetap 3.14 + T68?** (U31) | **JANGAN pin versi Python — disetujui pengguna 19 Okt 2026 ("sesuai rekomendasi aja, catet dulu nanti kulanjutin di sesi baru").** Yang berlaku: **3.14.7 tetap**, **T68 tetap dipakai**, dan **laporan upstream (K66) dikirim** — laporannya kini memuat **kontrol yang gagal** (2 dari 12 jalan suite penuh mati), dan itu yang dibutuhkan pelacak Qt. **Pin hanya ditinjau ulang bila** (a) Qt menjawab, atau (b) cacatnya muncul lagi di pemakaian nyata — dan itu keputusan baru dengan bukti baru, bukan lanjutan otomatis. Bila Anda kelak memang ingin kepastian statistik sebelum memutuskan, itu pekerjaan tersendiri: **±100–150 jalan per versi** (≈ 3–4 jam per versi di mesin ini). **Langkah 3 K69** (uji versi **PySide6** lain) **tetap tidak dipicu** — ia baru relevan bila Qt meminta "uji rilis terbaru" atau bila pin Python ditinjau. **Tidak ada perubahan pada `requirements.txt`/`requirements.lock.txt`, pin Python proyek (K3), atau `.venv`** | 2/12 vs 0/12 dengan uji Fisher dua sisi **p ≈ 0,48** — selisih itu **tidak dapat dibedakan dari kebetulan**, jadi memindahkan pin Python (keputusan dependensi, K3) akan mengubah lingkungan seluruh proyek atas dasar yang belum terbukti, dan hasilnya pun **bukan perbaikan** (paling banyak penurunan laju yang belum terukur). T68 sudah menekan gejalanya ke 0 di 10–12 jalan. Yang benar-benar menambah informasi justru **laporan upstream**: ia menyatakan pengalaman pengguna, tidak menuntut perubahan lingkungan, dan dengan kontrol yang gagal ia jauh lebih kuat daripada sebelumnya |
| K75 | **Uji `tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah` bergantung detik (gagal ±1 dari 12 jalan): dibiarkan atau diperbaiki?** (U32) | **DIPERBAIKI — disetujui pengguna 19 Okt 2026 ("sesuai rekomendasi aja, catet dulu nanti kulanjutin di sesi baru"); pelaksanaannya aksi #26, sudah dijalankan 19 Okt 2026 (sesi 23) → T76.** Bentuknya: perbandingan baris `snapshot` **mengecualikan `jam_ambil` dan `batas_diketahui`** (keduanya waktu **masing-masing impor**), sedangkan kolom lain — `tanggal_data`, `jumlah_emiten`, `jumlah_gagal`, `versi_skema`, `versi_aplikasi`, `catatan` — tetap dibandingkan **penuh**; tiga view lain (`emiten`, `kalender_bursa`, `notasi_khusus`) tidak berubah. Alternatif "membekukan jam" lewat `db.waktu_iso` **tidak** dipilih: ia menuntut menambal **dua** modul (`db` dan `ingesti`), jadi lingkupnya lebih besar daripada cacat yang diperbaiki. Uji tetap harus membuktikan hal yang sama: baris dari jalur jendela **sama** dengan baris dari `--impor`. Bentuk teknisnya dicatat sebagai **T76** di `docs/arsitektur.md` | Uji yang gagal ±1 dari 12 jalan membuat "suite hijau" berhenti bermakna — kegagalan yang timbul-tenggelam melatih orang mengabaikan hasil suite, dan itu kelas yang dilarang aturan keras 7 (gagal itu berisik, **bukan** berisik secara acak). Yang diuji uji itu adalah **isi baris yang sama** antara dua jalur impor, bukan bahwa kedua impor terjadi pada detik yang sama: kolom waktu memang **tidak pernah dijanjikan** sama, sehingga membandingkannya menguji hal yang salah. Bukti kegagalannya `.uji-data/uji-k69/reproduksi-313/jalan-12.txt` (riset bagian 10.3 butir 5) |
| K76 | **Bentuk pelaksanaan aksi #21b: seluruh 49 bank sekaligus, atau pilot lebih dulu?** (pertanyaan penutup sesi 23) | **PILOT 5 BANK LEBIH DULU — disetujui pengguna 19 Okt 2026 ("sesuai rekomendasimu aja, catet dulu kulanjutkan di sesi baru").** **Sudah dijalankan 19 Okt 2026 (sesi 25): KANDIDAT ADA, BELUM DIIMPOR — 2 bank terbaca (BBCA, BRIS), 3 tidak (BMRI, BBNI, BBRI); rinciannya di bagian 5 sesi 25 dan `docs/rasio-bank-kandidat-2026-10.md`.** Sesi berikutnya mengumpulkan **kandidat + kutipan resmi** untuk **BBCA, BBRI, BMRI, BBNI, BRIS** — lima bank besar yang laporan publikasinya paling mudah ditemukan — dan **berhenti di situ**: **tidak ada** nilai yang masuk `konfigurasi/rasio-bank.csv` atau `--impor` sebelum **Anda memverifikasi tiap angka** (K68; aturan keras 1). Berkas kandidat memakai kolom `berkas.SPESIFIKASI["rasio_bank"]` (`kode;periode;tgl_publikasi;npl_kotor_persen;car_persen;bopo_persen;nim_persen;keterangan;sumber`) **ditambah tiga kolom pemeriksaan** — `url`, `tanggal_akses`, `kutipan` (kalimat/baris tabel apa adanya) — yang **tidak** ikut diimpor. Sumbernya **hanya publikasi resmi bank** (Laporan Eksposur Risiko & Permodalan / laporan publikasi triwulanan), dibaca lewat **render QtPdf + pembacaan visual** (tanpa dependensi baru; **tanpa** menebak pemetaan glyph — K24/§2.1a); angka yang tidak terbaca dicatat **"tidak terbaca" beserta sebabnya**, bukan ditebak. Sesudah pilot diverifikasi: isi CSV → `--impor` → periksa `v_rasio_bank_terkini`/`--saring` → **baru** putuskan perluasan ke 44 bank lain | Alasan pilot: (a) **0 dari 49 bank tertahan *hanya* oleh rasio bank** (K68), jadi pengisian ini **bukan** yang membuka peringkat bank — yang diuji adalah **jalur & format kutipannya**; (b) 44 bank sisanya menuntut pekerjaan per bank per periode, dan bentuk berkas yang salah akan mengulang kesalahan itu 44×; (c) bank-bank pilot pun **tetap** gagal kriteria non-rasio pada snapshot #8 (`tren_ma200`; BBCA juga `pbv_relatif_sektor`, BRIS juga `kekuatan_relatif`), jadi pilot **tidak** menjanjikan kenaikan peringkat siapa pun. Batas "sampai kandidat + kutipan" adalah batas K24/aturan keras 1: angka rasio bank **tidak** boleh masuk basis data atas dasar bacaan agen saja |
| K77 | **Bank syariah (BRIS): NPF gross 1,80% dan Net Imbalan 5,42% — diisi ke `npl_kotor_persen`/`nim_persen`, dibiarkan kosong, atau kolom sendiri?** (muncul 19 Okt 2026 dari pilot #21b; pengguna menjawab "sesuai rekomendasimu aja, catet dulu") | **DIBIARKAN KOSONG di v0.1 — disetujui pengguna 19 Okt 2026.** `npl_kotor_persen` dan `nim_persen` baris BRIS **tidak** diisi dari NPF/NI; kedua angka itu tetap tercatat apa adanya di `keterangan` (bersama alasannya), dan **tidak** ada kolom baru. Akibatnya BRIS dinilai hanya pada **CAR** (20,41%) dan **BOPO** (69,71%); NPL dan NIM berstatus **"tidak dihitung" beserta sebabnya** (bobotnya dialihkan, AC-3), bukan nol. Ide kolom khusus bank syariah dicatat di `docs/ideas.md` sebagai tunda | PRD 8.4 menetapkan **NPL, CAR, BOPO, NIM** untuk bank; **NPF** (non-performing financing) dan **Net Imbalan** adalah ukuran yang **berbeda** — definisi dan penyebutnya tidak sama — sehingga memetakannya ke kolom NPL/NIM akan mengubah arti ambang PRD tanpa satu pun jejak (aturan keras 1 dan 2). Aturan keras 2 sudah memberi tempat yang benar untuk keadaan ini: "tidak dihitung" + alasan, bukan angka pengganti |
| K78 | **U33 — `sumber` per baris pada `rasio-bank.csv` tidak tersimpan: dikerjakan atau dibiarkan?** (ditemukan 19 Okt 2026 saat pilot #21b) | **SUDAH DIKERJAKAN sebagai aksi #27 — disetujui pengguna 19 Okt 2026 dan dijalankan sesi 27 hari yang sama (T77).** Bentuknya: bidang `sumber` di `RasioBank`, diisi dari kolom berkas di `berkas._baris_rasio_bank` (kolom itu wajib dan tidak boleh kosong, sama seperti `fundamental` sejak K18), dipakai `ingesti._baris_rasio_bank` (`satu.sumber or kumpulan.sumber`), dan dikembalikan `potret` saat baris dibaca dari basis data; disertai uji yang **terbukti gagal pada `HEAD`** dan dua mutasi terarah. Dikerjakan **sebelum** impor kandidat dan **sebelum** perluasan ke 44 bank. Bukti: `.uji-data/uji-k78/bukti/`; suite **885 lulus**. Tafsir "bila kosong" dikunci **K81** (sel berkas kosong **ditolak**; bidang `RasioBank` kosong → label kumpulan) | Templat dan `berkas.SPESIFIKASI["rasio_bank"]` **mewajibkan** kolom `sumber`, tetapi nilainya dibuang saat dibaca — jadi asal tiap publikasi bank hilang tepat pada data yang paling perlu ditelusuri, dan bila diperluas ke 44 bank, 44 dokumen berbeda akan tampak berasal dari satu folder. Presedennya sudah ada: K18 memperbaiki hal yang sama untuk `fundamental` ("bukan hanya divalidasi lalu dibuang") |
| K79 | **Tiga bank pilot (BBRI, BMRI, BBNI) yang publikasinya tidak bisa diambil otomatis: diakali, dilewati, atau manual?** (muncul 19 Okt 2026; sebabnya di bagian 5 sesi 25) | **TIDAK DIAKALI, DILEWATI UNTUK SEKARANG — disetujui pengguna 19 Okt 2026.** `robots.txt` dihormati: BMRI (`Disallow: /*.pdf$`) dan BBNI (`Disallow: /Portals/`) tidak ditembus — tidak dengan UA peramban, unduhan berulang, maupun peramban headless — dan BBRI tetap tidak punya dokumen resmi **terbaca** yang memuat BOPO/NIM. Pilot berlanjut dengan **2 bank** (BBCA, BRIS). Bila kelak angka ketiga bank itu diinginkan: **pengguna mengunduh PDF-nya sendiri** lewat peramban ke `.uji-data/riset-idx/rasio-bank/pdf/manual/`, lalu pipeline yang sama (`baca-pdf.py`) membacanya — tanpa mengubah kebijakan pengambilan | Kebijakan situs adalah batas yang tidak boleh dilanggar diam-diam. Menembusnya dengan menyamar sebagai peramban akan membuat hasilnya tidak bisa dipertanggungjawabkan sebagai "publikasi resmi yang dibaca". Untuk perluasan ke 44 bank, temuan ini **wajib** masuk perhitungan: sebagian bank akan menuntut langkah manual |
| K80 | **Urutan pekerjaan sesudah pilot #21b** (diputuskan bersama K77–K79, 19 Okt 2026) | **(1) ~~aksi #27~~ (K78, `sumber` per baris) — SELESAI 19 Okt 2026 (sesi 27, T77)**; **(2) verifikasi angka kandidat (K68)** — **diperbarui K83 (sesi 30): pemeriksaan ulangnya dikerjakan agen sebagai aksi #29, dengan pagar "cocok persis"** — **SELESAI 19 Okt 2026 (sesi 31, T79): 14/14 sel cocok**; **(3) isi `konfigurasi/rasio-bank.csv` hanya dengan kolom `rasio_bank`** (tanpa tiga kolom pemeriksaan) → `--impor` → periksa `v_rasio_bank_terkini`/`--saring` — **(2) dan (3) dijalankan sebagai satu aksi #29**, impor hanya bila pemeriksaannya cocok — **SELESAI 19 Okt 2026: 2 baris diimpor (snapshot 12); `--saring` belum berubah karena `jenis` 973 emiten masih kosong**; **(4) baru** putuskan perluasan ke 44 bank — dengan menghitung lebih dulu berapa bank yang menuntut langkah manual — **DITUNDA (K87, sesi 31): `jenis` 973 emiten masih kosong, jadi rasio bank belum berpengaruh; `--ambil-jenis` tidak dijalankan tanpa permintaan** — **DIPERBARUI sesi 32: `jenis` SUDAH diisi (49 bank_keuangan · 862 umum · 62 kosong; snapshot 13) dan kriteria bank kini diterapkan**, tetapi **44 dokumen tetap ditunda** karena peringkat tidak berubah (9 lolos/9 dinilai, sama) dan 47 bank belum berasio. **Aksi #23/U26 SELESAI 19 Okt 2026 (sesi 34, K61/T80)** — konteks pasar disimpan `--saring` dan dibaca dasbor bila kuncinya sama (`--dasbor` **18,95 → 0,74 dtk**; 19 uji baru, suite **906 lulus**), dan **`--pulihkan`** tetap bukan pekerjaan tertunda (K59 e/K64) | Urutannya mengikuti ketergantungan yang terukur: impor sebelum #27 akan membuang provenance (K78), dan keputusan 44 bank sebelum impor 2 bank akan mengulang bentuk yang belum terbukti di data. Verifikasi angka tetap milik pengguna — K68 tidak berubah oleh pilot ini |
| K81 | **Sel `sumber` kosong di `rasio-bank.csv`: ditolak, atau jatuh ke label kumpulan?** (muncul 19 Okt 2026 sesi 27 saat menafsirkan K78) | **DITOLAK — rekomendasi dipakai, disetujui pengguna 19 Okt 2026 ("sesuai rekomendasimu aja, catet dulu").** Kolom `sumber` tetap wajib **dan tidak boleh kosong**: `_tidak_kosong` menolak sel kosong dengan pesan yang menyebut berkas, baris, dan kolomnya. Yang dimaksud K78 dengan "bila kosong: label kumpulan" adalah **bidang** `RasioBank` kosong (`None`, mis. dibentuk program lain) — di lapisan `ingesti` ia memakai label kumpulan. **Tidak ada perubahan kode untuk keputusan ini**; perilaku yang sudah terpasang di aksi #27 itulah yang dikunci | `SPESIFIKASI["rasio_bank"]` menyatakan `boleh_kosong=False`, T67 menyebut sel `sumber` kosong ditolak per baris, dan K18 (`fundamental`) sudah menolak sel kosong dengan cara yang sama. Alasan praktisnya menjadi jelas pada pekerjaan berikutnya: bila 44 bank diketik dalam satu berkas, satu sel `sumber` yang terlupa akan **diam-diam** menjadi `impor berkas: <folder>` — persis lubang provenance yang ditutup K78. Tidak ada data nyata yang terdampak: `rasio-bank.csv` produksi masih template `<<CONTOH>>`, dan berkas kandidat sudah mengisi `sumber` |
| K82 | **`potret._fundamental` masih membuang `Fundamental.sumber` saat membaca ulang — diperbaiki atau dibiarkan?** (temuan sesi 27; batas yang dicatat di T77) | **SUDAH DIKERJAKAN sebagai aksi #28 — disetujui pengguna 19 Okt 2026 dan dijalankan sesi 29 hari yang sama (T78).** Bentuknya: `potret._fundamental` mengisi `sumber=baris["sumber"]` (kolom itu sudah `NOT NULL`), ditambah **dua uji yang terbukti gagal pada `HEAD`** — di `HEAD` nilainya `None`, jadi ujinya berhenti dengan diff yang jelas, bukan `AttributeError`; satu uji untuk sumber **per baris** yang berbeda antarpublikasi, satu untuk bidang kosong yang harus kembali sebagai **label kumpulan**. Bentuk teknisnya **T78**. Bukti: `.uji-data/uji-k82/bukti/`; suite **887 lulus**. Sesudah ini **berhenti menunggu verifikasi pengguna** (K80 langkah 2) — **sejak K83 (sesi 30), pemeriksaan ulangnya dialihkan ke agen**. **44 bank dan aksi #23 tidak dimulai tanpa permintaan** | Sama kelasnya dengan K78: kolom sumber ada sejak K18, tetapi nilai per barisnya hilang saat baris dibaca kembali — sehingga janji "provenance per baris" hanya benar untuk satu dari dua tabel. Belum ada pemakai `Fundamental.sumber` hari ini, jadi **tidak mendesak**; tetapi meninggalkannya berarti pemakai berikutnya (mis. ekspor atau layar) akan menyimpulkan "sumber tidak dinyatakan" padahal basis datanya menyatakannya. Ongkosnya satu baris + satu uji; menundanya tidak menghemat apa pun dan menambah satu jebakan yang harus diingat |
| K83 | **Pekerjaan "manusia" mana yang boleh dialihkan ke agen — khususnya verifikasi angka `rasio_bank` (K68)?** (pengguna bertanya 19 Okt 2026: "kalau ada butuh pekerjaan manusia, bisa kamu aja ga yang lakuin?") | **Verifikasi angka `rasio_bank` DIALIHKAN ke agen, dengan pagar "cocok persis".** Agen membaca **ulang** PDF resmi yang sama (berkas yang sudah diunduh; SHA-256 dicocokkan dengan manifest), merender halamannya, membandingkan **setiap sel** `kandidat-rasio-bank.csv` — empat rasio, `periode`, `tgl_publikasi`, `sumber` — dengan yang tercetak, lalu mencatat buktinya. **Impor hanya boleh jalan bila seluruh sel cocok persis dan hash berkas sama**; satu selisih sekecil apa pun → **berhenti, 0 baris ditulis, lapor**. Angka yang tidak terbaca **tidak diganti tebakan** (aturan keras 1). Dikerjakan sebagai **aksi #29** di sesi baru; bentuk teknis **T79** dicatat saat dikerjakan | Verifikasi angka adalah **pekerjaan pemeriksaan** yang bisa diulang dan dibuktikan (berkas + hash + render + kutipan), berbeda kelas dengan keputusan produk — jadi ia bisa dipindahkan tanpa memindahkan tanggung jawab "asal angka resmi" (PRD bagian 10). Pagar "cocok persis" menjaga agar yang masuk basis data tetap angka yang **tercetak**, bukan tafsir baru; dan bila ragu, kegagalannya **berisik** (berhenti), bukan diam-diam. **Cara membaca "sesuai rekomendasimu aja" (sesi 30):** persetujuan **cara kerja**, **bukan** pernyataan bahwa angkanya sudah benar — status berkas tetap **kandidat, belum diverifikasi, belum diimpor** sampai aksi #29 dijalankan. **SUDAH DIJALANKAN 19 Okt 2026 (sesi 31, T79):** kedua berkas PDF dihitung ulang SHA-256-nya = manifest, halaman dirender ulang, dan **14 dari 14 sel** (`periode`, `tgl_publikasi`, empat rasio, `sumber` × 2 bank) **cocok persis** — jadi impor dijalankan: cadangan lebih dulu (`.uji-data\mejasaham-cadangan\20261019T181212314095+0700`), dua baris ke `konfigurasi/rasio-bank.csv`, `--impor` keluar 0 dengan **snapshot 12** dan **2 baris `rasio_bank`**; `v_rasio_bank_terkini` memuat keduanya dengan `sumber` per baris. **`--saring` tidak berubah** — sebabnya terukur: `jenis` emiten masih kosong untuk **973** emiten sehingga kriteria bank tidak diterapkan kepada siapa pun, dan BBCA/BRIS tetap gagal `coverage` (EBIT tahunan). Satu catatan tanggal **tidak disembunyikan**: BRIS memakai 2026-08-21 (tanda tangan) sedangkan berkasnya dilayani `Last-Modified` 24 Agu 2026 → **U34** |
| K84 | **Laporan PySide6 (K66) — bisakah pengirimannya dikerjakan agen?** (pertanyaan yang sama, 19 Okt 2026) | **TIDAK.** Berkas laporan, kontrol yang gagal (2/12), daftar lampiran, dan langkah mengirim sudah siap di `docs/laporan-pyside6-siap-kirim.md`, tetapi **pengirimannya tetap pengguna**: menuntut akun pelacak Qt, formulir di peramban, dan tindakan **di luar repositori** yang tidak bisa dilakukan atau dipertanggungjawabkan agen. Yang boleh dibantu agen bila diminta: menyiapkan **teks isian formulir** yang tinggal ditempel | Laporan yang dikirim atas nama akun pengguna adalah tindakan **di luar repositori dan tidak bisa ditarik kembali** (tautannya publik). Berkasnya sudah lengkap; sisa pekerjaannya hanya menempel lalu mengirim — ongkos manusia paling kecil di seluruh daftar, dan memindahkannya ke agen tidak menghemat apa pun yang berarti |
| K85 | **Impor yang menulis ulang `sumber` 2.328 baris `notasi_khusus` — diterima, atau dipulihkan dari cadangan?** (muncul 19 Okt 2026, sesi 31, sesudah aksi #29) | **DITERIMA APA ADANYA — tidak ada pemulihan cadangan, tidak ada impor ulang.** Isinya diperiksa satu per satu: **2.328 dari 2.328** baris **hanya** berbeda di kolom `sumber` (dari `impor berkas: …\riset-idx\k53-k54\keluaran` menjadi `impor berkas: …\mejasaham\konfigurasi`); `tanggal_selesai` dan `keterangan` identik, **0 beda lain**. Revisi lama tetap menyimpan label lamanya (append-only), dan label baru menunjuk tempat data itu sekarang dipakai. Cadangan `.uji-data\mejasaham-cadangan\20261019T181212314095+0700` tetap disimpan | Pemulihan akan menghapus **2 baris `rasio_bank`** yang baru diimpor dan menuntut impor ulang dari folder staging — ongkos nyata untuk perubahan isi **nol**. Yang perlu dijaga bukan "jangan ada revisi baru", melainkan "jangan ada isi yang berubah tanpa jejak"; keduanya sudah dibuktikan. Cara impornya yang menimbulkan efek ini dicatat sebagai jebakan di `docs/lanjutan.md` bagian 6, supaya sesi berikutnya bisa memilih impor folder yang hanya memuat berkas yang dimaksud |
| K86 | **U34 — `tgl_publikasi` BRIS: 21 Agu 2026 (tanggal tanda tangan) atau 24 Agu 2026 (`Last-Modified` berkas)?** (diputuskan bersama K85/K87, 19 Okt 2026) | **PERTAHANKAN 2026-08-21 — nilai yang tercetak dan yang diverifikasi (K83); tidak ada baris revisi baru.** Selisih 3 hari tetap disebut di `keterangan` baris BRIS. Bila kelak ada **bukti resmi** tanggal terbit (pengumuman IDX/OJK) yang menyatakan lain, perbaikannya **baris revisi baru** (append-only), bukan `UPDATE` | `tgl_publikasi` adalah pintu point-in-time `potret.muat`, jadi tanggal yang terlalu awal berisiko look-ahead — tetapi mengubahnya tanpa bukti tanggal terbit hanya menukar satu tebakan dengan tebakan lain. Yang tercetak (tanda tangan direktur) adalah satu-satunya tanggal yang bisa dibuktikan sekarang; `Last-Modified` adalah metadata server, bukan pernyataan penerbit. Pengumuman resminya tidak terbaca (robots/IDX 403, K79) |
| K87 | **Perluasan `rasio-bank.csv` ke 44 bank lain** (K80 langkah 4) — dikerjakan sekarang? | **DITUNDA.** Tidak dimulai tanpa permintaan pengguna, dan **prasyaratnya belum terpenuhi**: `jenis` **973 emiten** masih kosong, sehingga kriteria bank (NPL/CAR/BOPO/NIM) tidak diterapkan kepada siapa pun (terukur di `--saring` sesi 31: **0 bank_keuangan**). Bila kelak diminta: hitung dulu berapa bank yang menuntut langkah manual (K79), lalu **isi `jenis` lebih dulu** (K21/`--ambil-jenis` atau isian tangan) dan buktikan rasio bank benar-benar dipakai — **baru** tambah 44 dokumen. `--ambil-jenis` **tidak** dijalankan tanpa permintaan — **DIPERBARUI 19 Okt 2026 (sesi 32):** permintaan itu datang ("Lanjutkan"), sehingga langkah prasyaratnya **dijalankan**: `--ambil-jenis --timpa-jenis` → **49 bank_keuangan · 862 umum · 62 kosong**, diimpor → **snapshot 13**; `--saring` kini **menerapkan** kriteria bank dan berhenti menghitung DER/coverage/CFO-NI untuk bank (terukur: BBCA 186/2679/4122/532 bp, keempatnya lolos; 47 bank lain belum berasio). **Peringkat tidak berubah** (9 lolos/9 dinilai, sembilan kandidat sama) — jadi K68 terbukti lagi dan **44 dokumen TETAP DITUNDA**; **hitung langkah manual (K79) SUDAH DIJALANKAN 19 Okt 2026 (sesi 33): dari 44 bank sasaran, 8 menuntut langkah manual, 2 tidak terukur, 34 boleh otomatis** — rincian `docs/rasio-bank-kandidat-2026-10.md` §10, dan **keputusan lanjutannya K88 (tetap ditunda)** | Menambah 44 baris rasio sebelum `jenis` terisi hanya menambah data yang belum berpengaruh, dan K68 sudah mengukur **0 dari 49 bank tertahan *hanya* oleh rasio bank**. Mengisi `jenis` mengubah hasil saringan lebih luas (DER/coverage/CFO-NI berhenti dihitung untuk bank, PRD 8.4), jadi ia keputusan tersendiri — bukan langkah teknis biasa yang boleh diselipkan |
| K88 | **U35 — perluasan `rasio-bank.csv` ke 44 bank sesudah hitung langkah manual (K79): dilanjutkan, hanya yang otomatis, atau tetap ditunda?** (diputuskan 19 Okt 2026, sesi 33; jawaban pengguna: "sesuai rekomendasi saja, catet jangan ngoding") | **TETAP DITUNDA.** Perluasan 44 dokumen **tidak dimulai**; tidak ada `--ambil-jenis`, impor, atau pengunduhan PDF untuk itu. Bila kelak pengguna memintanya, urutannya sudah terukur: **34 bank "otomatis mungkin" lebih dulu**, lalu **8 bank yang menuntut langkah manual** (**BTPS**, **DNAR**, **AGRS**, **BBMD**, **BBTN**, **BNLI**, **SUPA**, **BACA**) **hanya** bila PDF-nya tersedia — menurut K79 pengguna mengunduh sendiri ke `.uji-data/riset-idx/rasio-bank/pdf/manual/`, **tidak diakali**. **2 bank** (**INPC**, **SDRA**) menunggu jaringan/sertifikatnya normal, bukan dipaksa. Setiap dokumen tetap menuntut pencarian + render + verifikasi sel (K76/K83); izin robots **bukan** jaminan dokumen ketemu (**12/34** halaman publikasi nyata, **11/34** tautan PDF). Rincian angka: `docs/rasio-bank-kandidat-2026-10.md` §10; bukti `.uji-data/uji-k79/bukti/k79-hasil-final.csv` | Pengukurannya membuat biaya itu **terukur**, bukan mengecilkannya: 8/44 menuntut langkah manual (robots/akses), 2 belum terukur, dan 34 "boleh otomatis" pun tetap menuntut pekerjaan per bank — hanya **12 dari 34** menunjukkan halaman publikasinya pada satu tingkat. Sementara **K68 tetap berlaku: 0 dari 49 bank tertahan *hanya* oleh rasio bank**, dan peringkat tidak berubah (9 lolos/9 dinilai) sesudah `jenis` terisi. Jadi menambah 44 dokumen sekarang berarti biaya besar untuk **perubahan hasil nol**; menundanya tidak menutup pintu — urutannya sudah ditetapkan (34 otomatis → 8 manual), dan bentuk kerjanya sudah terbukti di pilot (K76/K83). Yang berubah hanya bila ada **permintaan baru** dari pengguna, bukan karena waktunya sudah cukup — **permintaan itu datang 29 Okt 2026 (sesi 69: pengguna memilih "44 bank" sebagai tahap 3, lalu "Lanjut")**. Gelombang 1 (5 bank otomatis: BEKS, MEGA, BNGA, BDMN, BJTM) dijalankan sebagai **kandidat, belum diimpor**; rincian `docs/rasio-bank-kandidat-2026-10.md` §11, pertanyaan yang muncul **U39** |
| K89 | (**diubah sebagian oleh K94** untuk notasi/suspensi/UMA pada tombol dasbor) **Saat checklist menemukan data jatuh tempo, apakah refresh otomatis menjalankan pengambilan/impor lain atau memberi tahu pengguna?** (diputuskan 22 Okt 2026, sesi 39; usulan U36) | **BERI TAHU DAN TAWARKAN TINDAKAN TERPISAH.** `--refresh` tidak otomatis memulai pengambilan atau impor dataset lain. Aplikasi menampilkan status serta tindakan yang tersedia; pembaruan hanya berjalan setelah pengguna memilihnya, dan baru dianggap selesai setelah data berhasil diimpor. Untuk notasi/suspensi/UMA, sumber otomatis IDX sudah tersedia melalui `--ambil-notasi`, tetapi alur saat ini tetap menulis CSV lalu memerlukan `--impor`. | Refresh harian sudah memakan waktu lama bagi pengguna, sedangkan pembaruan data lain dapat melibatkan unduhan, pemeriksaan, atau impor yang terpisah. Menjalankannya diam-diam akan menambah waktu dan menulis basis data tanpa tindakan pengguna yang jelas; pemberitahuan menjaga kendali pengguna dan mencegah pengulangan yang tidak perlu. Lihat U36 untuk rancangan checklist lintas dataset; implementasi belum dimulai |
| K90 | **Cakupan OWK PACK pada posisi** (diputuskan 22 Okt 2026, sesi 47; jawaban pengguna: “sesuai rekomendasimu”) | **V0.1 hanya mencatat PACK untuk mutu harga; posisi OWK dan konversinya menjadi saham ditunda ke tahap terpisah. Draf tidak boleh diimpor sebagai `right_issue` operasional posisi.** Pencatatan mutu harga baru boleh diimpor setelah tersedia representasi yang tidak memunculkan hak/tindakan posisi yang salah. | HMETD PACK membeli OWK Rp100 per unit, yang dikonversi menjadi saham 1:1; rasio 5:102 adalah saham lama terhadap HMETD. `right_issue` saat ini menghitung hak saham dan menimbulkan keputusan posisi. Memakai jenis itu untuk OWK akan menyatakan perilaku yang tidak didukung. Rujukan: sesi 46–47 di bagian 5, `docs/skema-data.md` §5.14, `mejasaham/posisi.py`, dan `mejasaham/penyesuaian.py` |
| K91 | **Antarmuka: dasbor web lokal menggantikan jendela PySide6 + EXE** (diputuskan pengguna 28 Okt 2026: “ganti aja jadi dashboard web local aja, biar simpel”; lalu memilih tiga rekomendasi) | **Antarmuka menjadi dasbor web lokal** (`python -m mejasaham --web`, `http://127.0.0.1:8765`), dibangun dengan `http.server` pustaka standar — tanpa dependensi baru. Bertahap: **A** lima layar PRD 11 hanya-baca (selesai 28 Okt 2026, disetujui pengguna: “Lanjut tahap B”); **B** formulir tulis lewat `mejasaham/layar/tulis.py` (selesai 28 Okt 2026, disetujui: “Lanjut tahap C”); **C** jendela PySide6, PyInstaller, dan build EXE dihapus; tanpa argumen → dasbor web; peluncur `MejaSaham.cmd` (selesai 28 Okt 2026, menunggu tinjauan). Server hanya mendengar di `127.0.0.1`, menolak `Host` lain dan POST lintas situs. | **Mengubah PRD 6.1** (aplikasi desktop berjendela + `MejaSaham.exe`) dan membuat uji klik-ganda Tahap 5 tidak relevan lagi. Yang **tidak** berubah: mode kepala (AC-11), data di luar paket (AC-12), penulis tunggal (AC-19 lewat `db.tulis`), dan seluruh inti. Konsekuensi: menjalankan dasbor butuh Python + `.venv` di mesin itu (tidak ada lagi EXE mandiri). Rincian teknis T85 `docs/arsitektur.md` |
| K92 | **Tombol "Perbarui data" di dasbor + pembersihan cadangan** (diminta pengguna 28 Okt 2026, sesi 56: “dikasih tombol update data … loading progress … notif kalo data udah paling update … hapus file yang gadiperluin”; kebijakan pembersihan dipilih: “Hemat aman”) | **(a)** Dasbor web punya tombol **Perbarui data** yang menjalankan jalur yang sama dengan `--refresh --saring` (ambil → snapshot/mutu/arsip → cadangan → rapikan → saringan tersimpan), lewat halaman **konfirmasi** (K59) dan halaman **kemajuan** (tahap ke-n dari 5, n dari ±970 emiten, jumlah gagal). **(b)** Bila snapshot terbaru sudah dari hari bursa terakhir (kebalikan AC-8), tombol hanya **memberi tahu** “Data sudah paling baru” dan tidak memulai apa pun; pembaruan ulang tetap bisa dipaksa lewat konfirmasi (untuk emiten yang barnya terlambat). **(c)** Retensi cadangan **14 → 3**; arsip snapshot di dalam cadangan **ditautkan (hardlink)**, bukan disalin; salinan arsip di cadangan lama yang **sama persis byte demi byte** diganti tautan sesudah tiap cadangan. **Arsip snapshot di folder data tidak pernah dihapus** (PRD 7.2/9.12). | Satu cadangan sebelumnya ±1 GB karena menyalin ulang seluruh arsip; 14 di antaranya ±14 GB dan terus tumbuh. Arsip tidak pernah ditimpa di tempat (`arsip.py`: tulis sementara lalu `os.replace`), jadi tautan memegang isi yang sama tanpa salinan kedua, dan menghapus folder data tidak menghapus isi tautan. Yang diterima: cadangan di disk yang sama tidak melindungi dari kerusakan disk — itu memang sudah benar sebelum K92, sebab lokasi bawaannya folder saudara; untuk disk lain pakai `--folder-cadangan` (tautan jatuh kembali ke salinan penuh). Tidak ada jam tutup bursa yang dikarang (aturan keras 1): “terbaru” diputuskan dari kalender bursa, dan konfirmasi menyebut bahwa harga hari ini bisa belum final bila dijalankan sebelum bursa tutup. Rincian teknis **T86** |
| K93 | **U36 — pelacak jadwal pembaruan data** (disetujui pengguna 28 Okt 2026, sesi 56: “nomor 6 juga boleh”) | **Usulan U36 dipakai, dengan satu aturan bukti tambahan.** Daftar periksa sembilan data (harga harian & indeks; suspensi & UMA harian; notasi khusus & papan pemantauan mingguan 7 hari inklusif; cek sumber kedua mingguan; daftar emiten bulanan; kalender bursa tahunan; SUN, fundamental, rasio bank “tidak dinilai”) tampil di dasbor web, `--dasbor`, dan sesudah `--refresh`; hanya memberi tahu dan menyebut tindakan (K89). **Status dibaca dari tanggal ISI data** — tanggal snapshot, tanggal daftar resmi IDX yang tercantum di baris notasi, tanggal Master File KSEI di label emiten, cakupan tahun kalender, catatan `cek_sumber_kedua` — **bukan** dari `diketahui_pada`/label `sumber`. Yang tidak bisa dibuktikan berstatus **“tidak dinilai”** beserta alasannya. | `--refresh` membaca ulang berkas di folder konfigurasi setiap hari, sehingga waktu tulis baris notasi/SUN menjadi baru walaupun isinya lama (terukur 28 Okt 2026: 4.604 baris notasi bertanggal tulis 28 Okt, padahal daftar resminya per 09 Okt). Menilai dari waktu tulis akan menyatakan data 19 hari basi sebagai terbaru — persis kesalahan yang ingin dicegah U36. Selang SUN tidak ditetapkan PRD, dan tanggal terbit laporan berikutnya tidak tercatat, jadi keduanya tidak diberi jatuh tempo karangan. Rincian teknis **T87** |
| K94 | **Notasi, suspensi & UMA IDX diambil otomatis oleh tombol "Perbarui data" — mingguan** (diputuskan pengguna 28 Okt 2026, sesi 56: “boleh tapi seminggu sekali saja”; lalu “Periksa dulu” untuk penanda multi-kode) | **(a) Mengubah K89 untuk satu dataset:** tombol "Perbarui data" menjalankan `notasi.ambil_ke_berkas` **sebelum** pengambilan harga bila butir jadwal notasi belum terbukti terbaru (daftar resmi IDX berumur > 7 hari atau tidak terbaca); refresh lalu membaca `notasi-khusus.csv` dari folder konfigurasi, jadi tidak ada `--impor` terpisah. `--refresh` di baris perintah tetap tidak mengambil dataset lain (K89). Gagal mengambil notasi tidak menahan harga, tetapi hasilnya tidak "berhasil" dan disebut. **(b) Suspensi & UMA mingguan, bukan harian — menyimpang dari PRD 7.1** (yang meminta harian); dicatat di sini, bukan dipilih diam-diam. Daftar periksa K93 menggabungkannya menjadi satu butir mingguan (dipecah lagi oleh **K98**). **(c) Pengumuman `>1 Kode` yang sudah dipetakan per emiten tidak lagi menandai seluruh suspensi/UMA "tidak lengkap":** daftarnya `multi-kode-terekonsiliasi.csv` di folder konfigurasi (kunci `Data_Download` API); pengumuman yang tidak tercantum tetap memasang penanda. | Diperiksa 28 Okt 2026: API IDX memuat 55 pengumuman `>1 Kode`, dan **ke-55-nya sudah direkonsiliasi** pada K36–K41 (56 pengumuman, 11–16 Okt; 55 tercatat per nama PDF, 1 — `2026-02-20` UPT, AKKU/INPS — per nomor pengumuman). Tanpa daftar itu, pengambilan otomatis menandai 2.157 baris "tidak lengkap" dan saringan kembali berlabel PERINGKAT SEMENTARA — alarm palsu yang akan berbunyi setiap minggu. Mingguan dipilih pengguna untuk membatasi beban pengambilan; akibatnya suspensi/UMA bisa basi sampai 7 hari, dan daftar periksa menyebutnya apa adanya. Rincian teknis **T89** |
| K95 | **Sumber harga kedua (PRD 7.3) = Ringkasan Saham IDX yang diunduh pengguna** (P40, disetujui pengguna 29 Okt 2026, sesi 57: “Setuju keduanya”) | Pengguna mengunduh berkas Ringkasan Saham dari situs IDX (tombol “Unduh”) seminggu sekali; berkas itu diimpor dengan label sumber + tanggal akses, lalu `--cek-sumber-kedua` membandingkan 20 emiten ADTV teratas. **Agen tidak memanggil endpoint IDX dari kode.** Pembaca berkas unduhan dibangun dari contoh berkas nyata, bukan dari bentuk yang ditebak | Syarat Penggunaan IDX (diakses 29 Okt 2026) membolehkan penggunaan bukan komersial dengan menyebut sumber, tetapi melarang web scraping/crawling. Uji baca-saja sesi 57: 916/916 penutupan 28 Okt sama dengan yfinance — sumbernya layak sebagai pembanding resmi dan independen. Rincian 3.10 |
| K96 | **Pengambilan otomatis notasi, suspensi & UMA IDX dicabut dari tombol "Perbarui data"** (P41, disetujui pengguna 29 Okt 2026, sesi 57: “Setuju keduanya”; **menggantikan bagian otomatis K94**) | Tombol tidak lagi menyentuh IDX. Jadwal tetap menilai notasi mingguan dari tanggal daftar resminya dan, bila jatuh tempo, menyebut halaman IDX yang diunduh pengguna. `--ambil-notasi` tidak lagi ditawarkan jadwal; perintahnya masih ada sampai diputuskan terpisah | Klausul anti-scraping yang sama (3.10). Akibat yang diterima: tanpa pembaca berkas unduhan IDX, notasi akan menua — jadwal menandainya “jatuh tempo”, dan PERINGKAT SEMENTARA tetap berlaku bila datanya hilang. **Pembaca berkas unduhan Notasi Khusus + unggah lewat dasbor dibangun 29 Okt 2026, sesi 58 (3.12); suspensi/UMA belum (P43)** |
| K97 | **Harga resmi IDX menjadi sumber utama ke depan lewat "deret sambungan"** (P42, disetujui pengguna 29 Okt 2026, sesi 58: “Setuju (a)–(f)”) | Satu tanggal sambung bertanggal untuk seluruh emiten: bar sebelumnya dari yfinance, sejak itu dari Ringkasan Saham IDX yang diunggah pengguna setiap hari bursa. Syarat (a)–(f) di 3.11: gerbang tumpang-tindih, penanda `split` berbatas `diketahui_pada`, hari tanpa berkas = bolong yang tampil (bukan diisi yfinance), label per bar, cek sumber kedua dibalik. **Langkah 1 (syarat c), 2 (deret sambungan), 3 (gerbang b + hari bolong d) dan 4 (unggah tanggal lampau + beberapa berkas) selesai 29 Okt 2026, sesi 58, beserta sisa 1–3 (dasbor menyebut peringkat sementara; laporan mutu refresh membaca deret sambungan; pengingat unggah harian)**; sambungan belum dinyatakan di data kerja | Pengguna ingin harga dari sumber resmi untuk pemakaian pribadi. Syarat Penggunaan IDX melarang scraping, jadi unduhan tetap manual; riwayat panjang hanya tersedia dari yfinance. Rincian dan urutan kerja 3.11 |
| K98 | **Jadwal memisahkan suspensi & UMA dari notasi khusus** (P43, disetujui pengguna 29 Okt 2026, sesi 59: “Setuju P43”; **menggantikan penggabungan satu butir di K94 (b)**) | Butir jadwal "Notasi, suspensi & UMA" dipecah: **"Notasi khusus & papan pemantauan (IDX)"** dinilai mingguan dari tanggal daftar resmi, hanya dari jenis yang dicakup daftar Notasi Khusus (`notasi.JENIS_DAFTAR`); **"Suspensi & UMA (IDX)"** selalu **tidak dinilai**, menyebut jumlah baris dan pengumuman terakhir yang tersimpan, dengan tindakan manual (periksa pengumuman IDX → isi `notasi-khusus.csv` → `--impor`, cadangan dulu). Pembaca berkas unduhan suspensi/UMA dibuat sesudah pengguna memberi contoh berkasnya | Tanggal pengumuman terakhir bukan bukti kesegaran (hari tanpa pengumuman tidak bisa dibedakan dari data yang tidak diperbarui) — K93 aturan 3; bentuk berkas tidak ditebak (K95). `mejasaham/jadwal.py`, `tests/test_jadwal.py` |
| K99 | **Suspensi & UMA masuk lewat unggahan PDF pengumuman IDX satuan** (pengguna 29 Okt 2026, sesi 61, menjawab dua pertanyaan: “Pembaca PDF” dan “Tanggal berlaku”; melanjutkan K98) | Contoh nyata pengguna (`20261028-UMA_COIN.pdf`, `20261028-UMA_FILM.pdf`, `20261028-WAS_Suspensi_PTSP.pdf`) adalah **pengumuman satuan, satu emiten per berkas**, bukan daftar. Pembacanya membaca bagian bahasa Indonesia: nomor `Peng-UMA-…`/`Peng-SPT-…`, satu kode emiten, tanggal pengumuman, dan — untuk suspensi — tanggal berlaku ("pada tanggal …"). **`tanggal_mulai` suspensi = tanggal berlaku**; tanggal pengumuman dan nomornya ditulis di `keterangan`. UMA: mulai = tanggal pengumuman, selesai 30 hari kemudian (K35, sama dengan baris lama). Unggahan **hanya menambah**: tidak ada baris yang ditutup karena tidak tercantum. Pengumuman pembukaan (UPT), multi-kode, atau bentuk lain **ditolak** sampai ada contohnya. Jadwal butir "Suspensi & UMA" tetap **tidak dinilai** | Satu PDF yang terlewat tidak bisa dideteksi dari PDF lain, jadi kelengkapan tidak bisa dibuktikan (K93 aturan 3, K98). Tanggal berlaku dipilih karena itulah hari emitennya tidak bisa diperdagangkan; akibatnya berbeda dari 1.151 baris lama dari API (yang memakai tanggal pengumuman) — pengumuman yang sama tidak dicatat dua kali (baris lama bertanggal antara pengumuman dan berlaku dianggap sudah ada). Teks PDF dibaca dengan pengurai pustaka standar milik `kalender.py`, **tanpa dependensi baru** (K3). Rincian di bagian 3.13 |
| K100 | **PDF pembukaan suspensi (UPT) IDX menutup suspensi terbuka** (pengguna 29 Okt 2026, sesi 61: “Contoh PDF UPT”; melanjutkan K99. Tiga pilihan teknis (a)–(c) diusulkan agen dan **disetujui pengguna 29 Okt 2026: “Setuju, commit”**) | Tidak ada PDF UPT baru dari pengguna; bentuknya diambil dari **18 PDF UPT asli IDX 2024–2026** yang sudah ada di `.uji-data/riset-idx/riwayat-api-pdf/` (riset K36–K41). (a) **`tanggal_selesai` = sehari sebelum tanggal "dibuka kembali mulai … tanggal …"** — hari terakhir yang tidak bisa diperdagangkan, karena `saring` membaca `tanggal_selesai` inklusif. (b) Satu UPT menutup **tepat satu** suspensi terbuka emiten itu yang dimulai sebelum tanggal dibuka, dari asal mana pun (PDF, API lama, isian tangan); nol atau dua lebih → ditolak; bila baris terbukanya memuat nomor SPT dan UPT merujuk nomor SPT lain → ditolak. Suspensi yang sudah ditutup (API lama menutup pada tanggal pengumuman UPT) dihitung "sudah tercatat". (c) Yang **ditolak** sampai ada contohnya: pembukaan sesi II, pembukaan yang tidak menyebut Pasar Reguler (K39), nomor UPT yang terpotong | Isi UPT ditulis dengan font CID: pengurai `kalender.py` kini menerjemahkannya lewat `/ToUnicode` bila diminta (`terjemahkan_font=True`), **tanpa dependensi baru** (K3); glif yang tetap tidak terbaca menolak berkasnya, sebab satu glif bisa satu angka tanggal. Ditemukan sekaligus: pola `Tf` lama tidak pernah cocok (`re.X` membuang spasinya) — diperbaiki; kalender KSEI 2025–2027 nyata **identik** sebelum dan sesudahnya. Rincian di bagian 3.14 |
| K101 | **U37 — impor otomatis berkas IDX yang sudah diunduh pengguna** (disetujui pengguna 29 Okt 2026, sesi 61: “Setuju U37 & U38”; **mengubah K89** hanya untuk perintah ini) | Usulan U37 dipakai: folder pantau dari `--folder-pantau` atau `MEJASAHAM_FOLDER_PANTAU` (tidak diisi = mati); `--impor-unduhan` dan tombol dasbor menjalankan jalur impor yang sama dengan unggahan (Ringkasan Saham → Notasi Khusus → PDF pengumuman), cadangan lebih dulu, berkas yang selesai dipindah ke `unduhan-idx/`, yang ditolak tetap di tempatnya dan gagal berisik. Pengunduhan tetap manual (K95/K96). Rincian pelaksanaan di `docs/arsitektur.md` T96 | Pengguna ingin langkah sesudah klik "Unduh" berjalan sendiri sesuai jadwal; Syarat Penggunaan IDX hanya membatasi pengambilan dari situsnya |
| K102 | **U38 — pengingat terjadwal unduhan IDX** (disetujui bersamaan dengan K101) | Usulan U38 dipakai: `--ingatkan` membaca jadwal (K93) dan, bila ada unduhan IDX yang jatuh tempo, menampilkan **kotak pesan Windows** yang tombol "Ya"-nya membuka halaman IDX di peramban (bukan toast: toast lewat PowerShell gagal di mesin pengguna — T96); tugas Task Scheduler dibuat pengguna sendiri. Rincian di `docs/arsitektur.md` T96 | Isi pengingat sudah ada di jadwal; yang kurang hanya pemicu di luar dasbor |
| K103 | **Pembaca PDF SPT mengenali suspensi lanjutan** (disetujui pengguna 29 Okt 2026, sesi 62: “Setuju, kerjakan” atas usulan (a)–(c)) | (a) Selain "pada tanggal …", tanggal berlaku suspensi juga dibaca dari "di Pasar Reguler dan Pasar Tunai mulai sesi I / Sesi Pra-Pembukaan tanggal … sampai dengan Pengumuman Bursa lebih lanjut", dicari di teks tanpa spasi (potongan PDF memecah "m ulai"); kedua bentuk bersama tetap harus memberi tepat satu tanggal, sesi lain ditolak. (b) Nomor berformat lain (`Peng-S-…/BEI.PLP`, `…/BEI.PP3/…`) ditolak dengan menyebut nomornya — isinya ketentuan atau kabar suspensi yang masih berjalan, bukan awal suspensi. (c) Hitungan di 3.14 dikoreksi: yang ditolak 10, bukan 11. Rincian `docs/arsitektur.md` T97 | 8 dari 10 SPT riset yang ditolak K99 adalah suspensi lanjutan sesudah pembukaan cooling-down; bentuknya seragam di 8 PDF asli IDX 2024–2026, jadi tidak ditebak |
| K104 | **Pemberitahuan saat dasbor dibuka, pengganti tugas terjadwal** (pengguna 29 Okt 2026, sesi 63: “update otomatis tiap hari rada mengganggu … updatenya pas saya pengen update saja”, lalu “kalau saya buka aplikasinya dan belom update atau belom download file dan impor, baru kasih notifikasi aja, karena ga tiap hari saya buka aplikasinya”) | Kedua tugas Task Scheduler K101/K102 **dinonaktifkan** (tidak dihapus; `--impor-unduhan`, `--ingatkan`, folder pantau tetap). Dasbor web menampilkan kotak **"Perlu diperbarui"** di kepala halaman (tampil sebelum hitungan dasbor selesai): butir jadwal K93 berstatus jatuh tempo/menunggu sumber (`pengingat.saat_dibuka`) beserta buktinya, tindakannya, dan tautan halaman IDX; pengingat unduh K95 (dipindah ke kotak ini); dan jumlah berkas IDX di folder pantau yang belum diimpor/ditolak. "Tidak dinilai" (suspensi/UMA, SUN, fundamental) tidak ikut karena selalu begitu — tetap di tabel jadwal. Tidak ada yang dijalankan otomatis (K89). Tidak ada kotak bila tidak ada yang perlu dikerjakan. |
| K105 | **U39 — tiga pertanyaan gelombang 1 perluasan rasio bank** (diputuskan 29 Okt 2026, sesi 70; jawaban pengguna: "Setuju U39") | **Usulan U39 dipakai apa adanya.** (a) **Basis rasio = set Bank/individual** (format Laporan Rasio Keuangan POJK 37/2019); bila dokumen juga menerbitkan set konsolidasian, angkanya dicatat di `keterangan` dan **tidak** diisi ke kolom. (b) **`tgl_publikasi` = tanggal tercetak (tanda tangan/iklan), KECUALI** bila bukti unggahan (folder unggah atau header `Last-Modified`) **lebih dari 7 hari** sesudahnya — maka tanggal unggahan yang dipakai, dan keduanya dicatat di `keterangan`. K86 (BRIS, selisih 3 hari) tetap. Diterapkan pertama pada **BEKS**: 27 Jul → **14 Agu 2026**. (c) **PNLF** (PT Panin Financial Tbk, induk asuransi) **dikeluarkan dari sasaran** perluasan: bukan bank, tidak menerbitkan rasio bank; sasaran "otomatis" menjadi **33** | (a) mencampur basis berarti ambang PRD 8.4 dinilai atas dua definisi berbeda, dan hanya set bank yang lengkap di setiap dokumen (set konsolidasian Danamon tanpa BOPO); (b) point-in-time (AC-15) lebih berat daripada nilai tercetak bila selisihnya besar — tanggal yang terlalu awal membuat angka ikut saringan sebelum publik bisa membacanya; ambang 7 hari menjaga K86 tidak berubah; (c) mencari rasio bank untuk perusahaan non-bank hanya berakhir "tidak terbaca" |
| K106 | **U40 — dua pertanyaan `tgl_publikasi` gelombang 2 perluasan rasio bank** (diputuskan 29 Okt 2026, sesi 70; jawaban pengguna: "Setuju U40") | **Usulan U40 dipakai apa adanya; melengkapi K105(b).** (a) **Dokumen tanpa tanggal tercetak:** `tgl_publikasi` = **bukti terbit paling akhir** di antara header `Last-Modified`, metadata pembuatan PDF, dan siaran pers bank untuk periode yang sama; sumber tanggalnya ditulis di `keterangan`. Diterapkan: **NISP 30 Jul 2026** (siaran pers; PDF dibuat 29 Jul, tanpa `Last-Modified`), **BCIC 11 Agu 2026** (`Last-Modified`; PDF dibuat 10 Agu). (b) **K105(b) dibaca harfiah** walaupun `Last-Modified` mungkin unggah ulang: tanpa bukti lain bahwa berkas dapat dibaca publik lebih awal, tanggal unggahan dipakai. Diterapkan: **BINA 28 Okt 2026** (tanda tangan 29 Jul) | Point-in-time (AC-15): bila bukti tanggal terbit lemah, salah ke arah "terlalu akhir" hanya menunda angka masuk saringan, salah ke arah "terlalu awal" membuat angka dipakai sebelum publik bisa membacanya. Rincian `docs/rasio-bank-kandidat-2026-10.md` §12 |
| K107 | **U41 — dua pertanyaan gelombang 3 perluasan rasio bank** (diputuskan 30 Okt 2026, sesi 71; jawaban pengguna: "Setuju U41") | **Usulan U41 dipakai apa adanya.** (a) **Domain K79 yang keliru dikoreksi secara tercatat, tanpa pengukuran ulang menyeluruh:** domain yang benar dicatat di `docs/rasio-bank-kandidat-2026-10.md` §13.2 (Nobu `nobubank.com`, Panin `panin.co.id`, Mayapada `bankmayapada.com`; `bankccb.com` bukan MCOR; domain BTPN belum ditemukan) dan dipakai di gelombang berikut; vonis baru per bank lahir saat bank itu dikerjakan. Tabel §10.2 tidak ditulis ulang. (b) **K105(b) tetap apa adanya** untuk selisih tanda tangan–berkas ≤ 7 hari: BNII dan AMAR memakai tanggal tercetak **30 Jul 2026** (berkas 31 Jul) | (a) yang menentukan adalah dokumen ketemu di domain resmi; menjalankan ulang K79 untuk 44 bank hanya memperbaiki tabel lama dan tidak mengubah langkah berikutnya; (b) ambang 7 hari K105(b) sengaja menyerap selisih kecil, sejalan dengan K86 (BRIS, 3 hari); selisih 1 hari tidak berarti bagi data triwulanan |

Konsekuensi K11: hari bursa diturunkan sebagai **hari kerja dikurangi daftar libur resmi**, bukan
disalin dari daftar hari bursa (IDX tidak menerbitkan daftar hari bursanya secara terbuka, hanya
daftar liburnya). Yang perlu Anda ketahui: kalender cara ini belum tahu hari bursa yang
ditiadakan mendadak, dan itulah gunanya peringatan "kalender belum memuat tanggal snapshot" yang
sudah ada di laporan mutu — bukan dianggap lulus. Sejak pengambilnya ada (9 Okt 2026), berkasnya
juga **bersyarat**: yang dipakai hanya pengumuman yang menyatakan menindaklanjuti *Kalender Libur
Bursa* IDX, sehingga tahun yang pengumumannya tidak memenuhi syarat itu — terukur: 2025 — memang
tidak ada di kalender, dan laporan mutu akan mengatakannya. Kalender yang lebih pendek lebih baik
daripada kalender yang memuat tanggal dari sumber yang tidak memutuskan hal itu (T31). Karena
pengumumannya **tahunan**, kalendernya memuat hari bursa sampai akhir tahun; "hari bursa terakhir"
karena itu dibatasi pada hari yang sudah lewat, supaya snapshot yang benar tidak disebut basi (T30).

Konsekuensi K7 (rinciannya di bagian 5): semesta emiten **tidak** diambil otomatis dari Yahoo —
daftar emiten adalah berkas rujukan yang dirawat tangan, sehingga aplikasi tidak bergantung pada
endpoint pencarian yang bisa berubah kapan saja (endpoint screener Yahoo sudah menolak akses
tanpa kredensial saat diperiksa 9 Okt 2026, HTTP 401).

Konsekuensi K12: daftar emiten tetap **berkas rujukan milik pengguna** (`emiten.csv`) — yang
berubah hanya cara mengisinya: `--ambil-emiten` menyediakannya dari berkas resmi, dan berkas itu
tetap boleh disunting tangan (menambah sektor IDX-IC, papan, jenis) sebelum dipakai `--refresh`.
Semesta naik dari 21 kode bootstrap menjadi **973 kode**, sehingga kriteria keluar Tahap 0
("data 800+ emiten", PRD 16) kini terpenuhi dari sisi **daftar**; yang belum adalah datanya
(harga 5 tahun), dan itu pekerjaan `--refresh` yang panjang. Sampai `sektor_idx_ic` diisi dari
sumber IDX-IC, kriteria saringan yang memakai statistik sektor memakai statistik seluruh semesta
likuid **dan menyebut alasannya** (PRD 8.4, aturan keras 2) — bukan menebak sektor dari taksonomi
KSEI, yang akan membuat median sektor terlihat ada padahal salah.

Konsekuensi K13: ambang 5% PRD 9.3 kini **hanya** menghitung kegagalan yang masih mungkin berhasil
bila diulang. Ini membuat gerbangnya tetap bermakna pada semesta yang datang dari daftar resmi —
daftar resmi memuat efek yang masih tercatat tetapi tidak diperdagangkan lagi, dan jumlahnya bisa
melewati 5% (terukur 5,9% pada 9 Okt 2026). Yang **tidak** berubah: kehilangan emiten ber-ADTV20
tertinggi tetap menahan snapshot, kegagalan permanen tetap dilaporkan (peringatan, temuan mutu
`tidak_diperdagangkan`, catatan snapshot), dan kegagalan yang jenisnya tidak dapat dipastikan
dihitung sebagai sementara — menahan snapshot, bukan meloloskannya. Rincian teknisnya di bagian 5.

Konsekuensi K1: entitas `Skor` berkunci `kode + id_snapshot + id_preset` (8.1) dan
screening dijalankan per preset; skor tidak pernah dibandingkan lintas preset
(10: skor bersifat relatif sektor, bukan lintas basis).

Konsekuensi K2: setiap baris harga/fundamental menyimpan `sumber` dan
`diketahui_pada`; laporan mutu menandai sumber tidak resmi (7.3).

Konsekuensi K5: `PRAGMA journal_mode=WAL` + `busy_timeout` agar proses kedua menunggu
alih-alih gagal kotor (AC-19); cadangan **wajib** memakai `VACUUM INTO` — saat WAL aktif,
menyalin berkas `.db` mentah bisa menghasilkan cadangan yang tidak lengkap (9.12);
Parquet hanya boleh ditulis sebagai turunan, tidak boleh menjadi masukan perhitungan.

Konsekuensi K6: (a) `Skor` selalu merujuk `id_preset` yang isinya tak berubah — inilah alasan
preset tidak boleh hidup di berkas yang bisa disunting, karena arti skor lama akan berubah
diam-diam; (b) setiap snapshot mencatat parameter efektif yang dipakai; (c) berkas TOML adalah
**alat edit**, sedangkan bukti yang dipakai berhitung adalah baris hasil muatannya;
(d) entri parameter yang belum terverifikasi **tidak ditulis** di TOML (bukan diisi 0) —
lihat catatan TOML di bawah.

### 1.1 Catatan teknis TOML (koreksi atas usulan awal)

Usulan awal saya menyebut nilai belum terverifikasi ditulis `null`. **Itu tidak bisa
dilakukan: TOML tidak punya tipe null.** Aturan yang dipakai menggantikannya:

1. Entri hanya ditulis bila **sudah** diverifikasi; belum terverifikasi → entri **tidak ada**
   di berkas (bentuknya tetap tersedia sebagai contoh yang dikomentari di template).
2. Setiap entri yang ada **wajib** memuat `berlaku_sejak`, `dicatat_pada`, dan `sumber`;
   entri tanpa ketiganya ditolak saat dimuat. `dicatat_pada` ikut wajib karena ia yang membuat
   pemuatan bersifat append-only dan idempoten: entri dengan identitas sama dan tanggal
   pencatatan sama tidak boleh berubah isi (itu ditolak), sedangkan koreksi menambah baris
   dengan `dicatat_pada` lebih baru.
3. Karena itu kode membedakan tiga keadaan: entri tidak ada → "belum terverifikasi";
   entri ada dengan `aktif = false` → "sengaja dinonaktifkan"; entri ada dan aktif → dipakai.

Berkas yang belum terverifikasi **tidak diisi angka tebakan** (aturan K4 di
`konfigurasi.md`). Template: `mejasaham/defaults/parameter-bursa.contoh.toml`.
Pemuatnya: `mejasaham/konfigurasi.py` + tabel parameter bertanggal (migrasi 002); cara jalan:
`python -m mejasaham --muat-konfigurasi`.

### 1.2 Amandemen K3: `pyarrow` dicabut
K3 versi awal menyebut memasang `pyarrow`. Setelah K5, Parquet bukan lagi sumber kebenaran
melainkan turunan ekspor yang belum tentu dibuat; memasang dependensi besar untuk sesuatu
yang belum dipakai bertentangan dengan target biaya Rp 0 (PRD tabel 1) dan ukuran bundel
(PRD 6.1). Jadi: **`pyarrow` dikeluarkan dari pemasangan awal**, ditambahkan kembali saat
ekspor Parquet benar-benar ditulis. `requirements.txt` sudah memuat catatan ini.

Pemisahan berkas dependensi: `requirements.txt` = runtime (ikut ke bundel PyInstaller),
`requirements-dev.txt` = pengembangan (`pytest`, `python-docx`) dan **tidak boleh** ikut ke
bundel.

### 1.3 Hasil pemeriksaan ketentuan pemakaian sumber data (K7, gerbang Q8)

Q8 menetapkan "ketentuan pemakaian dicek sebelum Tahap 0 selesai". Pemeriksaan itu dijalankan
pada 9 Okt 2026. Hasilnya ditulis apa adanya, termasuk bagian yang tidak menyenangkan.

**Yang ditemukan:**

1. **Lisensi `yfinance` (kode) = Apache-2.0**, tanpa batasan bidang pemakaian. Membatasi
   penggunaan *kodenya* bukan masalah.
2. **Syarat Layanan Yahoo (datanya) melarang pengambilan otomatis.** Bagian 2.4 ("Member
   conduct") melarang "access or collect data … using any automated means … **for any purpose
   without our express, prior permission**". **Tidak ada pengecualian pemakaian pribadi** dalam
   teksnya. [Sumber](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)
3. Kalimat "Yahoo Finance API is intended for personal use only" yang sering dikutip berasal
   dari README `yfinance`, **bukan** dari halaman Yahoo. Ia karakterisasi pihak ketiga, bukan
   izin.
4. Ketentuan lain yang jelas melarang: pemakaian komersial (2.5), penyebaran ulang dan
   distribusi turunan (2.8), serta membuat basis data/layanan yang menggantikan layanan Yahoo
   (butir berikutnya di 2.4).
5. **Risiko praktisnya nyata dan berulang:** pembatasan laju (HTTP 429) terjadi massal
   Feb 2025 dan Apr 2025; `yfinance` bawaannya `retries=0`, dan `download()` bawaannya
   menjalankan ~2×CPU permintaan serentak.

**Yang diputuskan (K7):** melanjutkan dengan yfinance sebagai **risiko yang diterima secara
sadar, bukan sebagai izin**. Tiga syarat yang mengikat dan sudah ditanam di kode:

- Label "tidak resmi" **menempel di setiap baris** (kolom `sumber`), bukan hanya di log, dan
  setiap berkas arsip/ekspor membawa peringatan "jangan disebarkan, bukan untuk tujuan
  komersial" beserta tautan ketentuannya (`mejasaham/arsip.py`).
- Jalur **impor berkas tetap warga kelas satu**, bukan cadangan darurat: seluruh data yang
  tidak tersedia dari Yahoo (kalender bursa, notasi khusus/SUN, rasio bank, fundamental)
  hanya masuk lewat jalur itu.
- Sumber resmi/berlisensi dievaluasi sebelum uang nyata (Q8), dan keputusan ini ditinjau ulang
  bila ketentuan Yahoo berubah.

**Dampak teknis yang sudah dijalankan:** ingesti berjalan **berurutan dengan jeda** (bukan
paralel), dengan ulang otomatis berjeda bertambah — karena bawaan yfinance justru pola yang
paling mungkin memicu pemblokiran. Ini juga alasan semesta emiten **tidak** diambil otomatis
dari endpoint pencarian Yahoo: selain tidak resmi dan bisa berubah tanpa pemberitahuan,
endpoint itu sudah menolak akses tanpa kredensial saat diperiksa (HTTP 401).

**Yang belum dapat dipastikan dan tidak dikarang:** jumlah emiten tercatat IDX yang resmi tidak
bisa diverifikasi otomatis — halaman IDX menolak akses otomatis (HTTP 403) dan tabel resminya
berbentuk PDF yang tidak terbaca alat ini. Angka "956 emiten (Mei 2025)" yang beredar berasal
dari pemberitaan sekunder, **bukan** dari IDX, jadi ia tidak dipakai sebagai dasar apa pun.

### 1.4 Definisi metrik yang dikunci (K10, menjawab P5–P12)

Dipakai apa adanya seperti usulan yang Anda setujui. Semuanya menjadi kode di
`mejasaham/metrik.py` dan diuji dengan data uji acuan.

| No | Hal | Yang dipakai |
|----|-----|--------------|
| P5 | ROE tahunan | Laba bersih induk ÷ rata-rata ekuitas induk **awal–akhir tahun buku**. Ekuitas awal tidak ada atau ≤ 0 → ROE tahun itu "tidak dihitung"; metrik 5 tahun = median tahun yang terhitung |
| P6 | Jendela hari bursa | 12 bulan = 252 hari bursa (momentum 12-1 = 231 + 21), 6 bulan = 126, 60 hari = 60 baris, 52 minggu = 252 baris, 5 tahun buku = 5 laporan tahunan. Berbasis baris data, bukan kalender |
| P7 | Volatilitas | Simpangan baku (ddof=1) imbal hasil **log** harian 60 hari × √252 |
| P8 | ATR14 | True range standar, dirata-ratakan **Wilder**; "% harga" = ATR ÷ close terakhir |
| P9 | 52 minggu | **Close** tertinggi 252 hari bursa |
| P10 | z-score & agregasi | Statistik sektor = rata-rata & simpangan baku **populasi** (ddof=0) atas semesta likuid sektor itu; fallback ke semesta likuid penuh bila sektor punya < 8 emiten likuid. `z = −3 → 0`, `z = +3 → 100`, dipotong ±3; metrik "lebih rendah lebih baik" arahnya dibalik. Bobot dinormalkan ulang atas metrik yang tersedia; faktor dinilai bila ≥ 60% bobot metriknya tersedia; emiten diperingkat bila ≥ 3 dari 4 faktor dinilai; bobot faktor yang gugur dialihkan proporsional. Skor total dibulatkan untuk tampilan, urutan peringkat dari nilai tak dibulatkan; seri → ADTV20 lebih besar di atas |
| P11 | Nilai tak bermakna | PER ≤ 0, EV/EBITDA ≤ 0, laba/harga ≤ 0 → "tidak dihitung" (bukan skor 0), bobotnya dialihkan, statusnya tampil di penjelasan skor |
| P12 | PER normalisasi siklikal | Rata-rata EPS 5 tahun buku; tahun rugi tetap diikutkan apa adanya, dan jumlah tahun yang dipakai dicatat |

### 1.5 Bukti C10 (diperiksa 9 Okt 2026 atas data sumbernya, `auto_adjust=False`)

Pertanyaan C10 di bagian 4 dijawab dengan pengukuran, bukan dugaan: apa yang sebenarnya
dilakukan sumber terhadap harga historisnya.

| Emiten | Kejadian | `Close` di sekitar tanggal kejadian | Artinya |
|--------|----------|--------------------------------------|---------|
| BBCA | split 5:1, 13 Okt 2021 | 7.320 → **7.525** → 7.750 | sudah disesuaikan (mentah akan ≈ 36.600) |
| BMRI | split 2:1, 4 Apr 2023 | 5.262 → **5.200** → 5.225 | sudah disesuaikan |
| BBNI | split 2:1, 6 Okt 2023 | 5.187 → **5.200** → 5.100 | sudah disesuaikan |
| TPIA | split 4:1, 23 Agu 2022 | 2.256 → **2.410** → 2.380 | sudah disesuaikan |
| NVDA (acuan konvensi, pasar AS) | split 10:1, 10 Jun 2024 | ~121 (bukan ~1.210) | sudah disesuaikan |

Kesimpulan: sumber **tetap melaporkan kejadian split** di kolom aksi korporasi, tetapi harga
yang dikirimnya **sudah** memakai basis pascasplit. Karena itu mencatat split sebagai aksi
penyesuaian lalu menerapkannya lagi saat dibaca akan menyesuaikan dua kali. Empat dari 21 kode
bootstrap kena, jadi ini bukan kasus pinggiran.

Dampak yang ikut dicatat: penyesuaian sumber membuat harga **tidak melonjak** di tanggal split.
Pemeriksa lonjakan di `mejasaham/mutu.py` karena itu sekarang membaca penandanya, dengan dua
perilaku baru yang sudah berjalan dan teruji: (a) emiten yang punya aksi penyesuaian tetapi
barisnya belum menyatakan penanda dilaporkan sebagai catatan — beserta akibatnya bahwa metrik
harganya berhenti dihitung dan ia tidak bisa diperingkat; (b) lonjakan di sekitar tanggal split
pada baris yang **mengaku** sudah disesuaikan sumber ditandai `TAK_WAJAR`, bukan dimaafkan aksi
korporasi — sebab kalau dimaafkan, laporan mutu justru menyembunyikan persis kesalahan yang
paling merusak angka momentum.

---

## 2. Usulan default saya yang belum Anda putuskan

Ditulis sebagai usulan. **Keadaannya 19 Okt 2026 (sesudah sesi 22): tidak ada usulan yang menunggu
jawaban** — U31 dan U32 sudah diputuskan (→ **K74/K75**). Tiap baris menandai keputusan mana yang
mengunci usulan itu, dan catatan di bawah merangkum riwayatnya.

> **Diperbarui 12 Okt 2026 — bagian ini sudah tidak menunggu jawaban.** Pengguna menjawab "sesuai
> rekomendasi", dan **U2–U17, U19, U22, U23 dikunci sebagai keputusan → K42**. Tabel di bawah
> disimpan sebagai **riwayat usulan beserta alasannya**, bukan daftar pertanyaan. Yang sudah lebih
> dulu dikunci: U1 → K5, U18 → K13, U20 → K22, U21 → K23.
>
> **Diperbarui 16 Okt 2026 (sesi 6) — U24 dan U25 sudah DIJAWAB dan dikunci, jadi bagian ini kembali
> tidak menunggu jawaban.** Keduanya muncul dari tinjauan visual yang dituntut K46 (lihat bagian 5,
> sesi 6, dan `docs/riset-suspensi-multi-kode-2026-10.md`). Pengguna menjawab **"keputusan sesuai
> rekomendasi mu, catet aja dulu, kulanjutkan di sesi berikutnya"** → **U24 = K53** (penanda K46
> dilepas; 20 Feb 2024 **bukan** `tanggal_mulai`; episode MTFN 2023–2024 yang hilang dibentuk) dan
> **U25 = K54** (bentuk baris K41: `ELTY` 2023-07-03 → 2023-10-19 · `ARTI` 2021-11-30 → 2023-11-23).
> **Pelaksanaan keduanya ditunda ke sesi berikutnya** (tidak ada pekerjaan teknis pada sesi
> pencatatan ini) — urutannya di `docs/lanjutan.md` bagian 4 aksi #17. Selebihnya di tabel ini
> tetap riwayat.
>
> **Diperbarui 17 Okt 2026 (sesi 13) — bagian ini kembali MENUNGGU JAWABAN, untuk tiga usulan baru.**
> Pengguna menanyakan apakah tiga butir yang selama ini "menunggu pengguna" (laporan upstream
> PySide6, uji Python 3.13, `rasio-bank.csv`) bisa dikerjakan sesi agen, dan meminta **dicatat dulu**
> sebelum dikerjakan. Ketiganya masuk sebagai **U27–U29** di bawah, dengan pertanyaannya di **3.9
> (P37–P39)**. **Tidak satu pun memblokir aksi #19c** — urutan kerja `docs/lanjutan.md` bagian 4
> tidak berubah.
>
> **Diperbarui 17 Okt 2026 (sesi 16) — satu usulan baru menunggu jawaban: U30.** Ia muncul **saat
> aksi #19c dikerjakan** (cadangan dari jendela): jendela sudah menyebut folder tujuannya dan
> menolak folder di dalam folder data, tetapi **belum** menyediakan pilihan folder per-cadangan.
> Usulannya: tetap seperti sekarang (lokasi diarahkan sekali lewat `--folder-cadangan`/
> `MEJASAHAM_BACKUP`). **Tidak memblokir #19d** — urutan kerja `docs/lanjutan.md` bagian 4 tidak
> berubah.
>
> **Diperbarui 17 Okt 2026 (sesi 17) — U30 sudah DIJAWAB dan dikunci, jadi bagian ini kembali tidak
> menunggu jawaban.** Pengguna menjawab **"sesuai rekomendasimu aja, catet dulu, biar kulanjutkan di
> sesi baru"** → **U30 = K70**: folder tujuan cadangan **tetap dari konfigurasi** (jendela menyebut
> folder itu di dialog, bukan menyediakan kotak pilih folder); kotak pilihnya **tidak** ditutup
> selamanya, tetapi menuntut keputusan tersendiri bila diminta. Sesi itu **hanya mencatat** — tidak
> ada berkas kode yang disentuh.
>
> **Diperbarui 19 Okt 2026 (sesi 21) — bagian ini kembali MENUNGGU JAWABAN, untuk dua usulan baru.**
> Keduanya muncul **saat riset K69 dikerjakan**: **U31** = sesudah reproduksi ulang berhasil (2/12 mati
> di 3.14.7) dan A/B di 3.13 (0/12) selesai, apakah **pin CPython 3.13** diambil sekarang — usulan
> saya **tidak** (selisihnya belum bermakna: p ≈ 0,48); dan **U32** = satu **uji flaky** yang
> ditemukan di pengukuran itu (`test_impor_dari_jendela_sama_dengan_baris_perintah` gagal 1 dari 12
> jalan karena membandingkan kolom waktu yang memang berbeda) — usulan saya **perbaiki** (usulan aksi
> #26). **Tidak satu pun memblokir #21b**; urutan kerja `docs/lanjutan.md` bagian 4 tidak berubah.
>
> **Diperbarui 19 Okt 2026 (sesi 22) — U31 dan U32 sudah DIJAWAB dan dikunci, jadi bagian ini kembali
> tidak menunggu jawaban.** Pengguna menjawab **"sesuai rekomendasi aja, catet dulu nanti kulanjutin
> di sesi baru"** → **U31 = K74**: **jangan pin CPython 3.13** — T68 tetap, laporan upstream (K66)
> dikirim, pin hanya ditinjau ulang bila Qt menjawab atau cacatnya muncul lagi; **U32 = K75**: uji
> flaky **diperbaiki** lewat **aksi #26** (bandingkan baris `snapshot` **tanpa** `jam_ambil`/
> `batas_diketahui`). Sesi itu **hanya mencatat** — tidak ada berkas kode yang disentuh, dan status
> uji dijalankan ulang sesudah pencatatan. Pekerjaan berikutnya karena itu **#26**, lalu **#21b**.
>
> **Diperbarui 19 Okt 2026 (sesi 23) — #26 sudah DIKERJAKAN, jadi bagian ini tetap tidak menunggu
> jawaban.** `tests/test_ui_tulis.py` kini membandingkan baris `snapshot` **tanpa** `jam_ambil`/
> `batas_diketahui` (kolom lain tetap penuh), dengan A/B jam dipaksa, mutasi, 12/12 jalan, dan suite
> **882 lulus**; rincian **T76** dan catatan sesi 23 di bagian 5. **Pekerjaan berikutnya: #21b**
> (`rasio-bank.csv` sampai batas kandidat + kutipan, lalu angka diverifikasi pengguna — K68).
>
> **Diperbarui 19 Okt 2026 (sesi 33) — U35 sudah DIJAWAB dan dikunci, jadi bagian ini kembali tidak
> menunggu jawaban.** Pengguna menjawab **"sesuai rekomendasi saja, catet jangan ngoding"** →
> **U35 = K88: perluasan 44 dokumen TETAP DITUNDA** (bila kelak diminta: 34 bank otomatis dulu, lalu
> 8 bank manual hanya bila PDF-nya tersedia; 2 bank menunggu jaringannya normal — K79).
> Hitung langkah manual (K79) sudah dijalankan sebelum keputusan itu: dari **44 bank sasaran**,
> **8 menuntut langkah manual**, **2 tidak terukur**, **34 boleh otomatis** — tetapi uji satu tingkat
> menunjukkan izin robots **bukan** jaminan dokumen ketemu (**12/34** halaman publikasi nyata,
> **11/34** tautan PDF). Sesi itu **hanya mencatat** — tanpa kode, impor, atau basis data; rincian
> `docs/rasio-bank-kandidat-2026-10.md` §10. **Tidak ada usulan yang menunggu.**
>
> **Diperbarui 19 Okt 2026 (sesi 34) — U26 sudah DIKERJAKAN, jadi bagian ini tetap tidak menunggu
> jawaban.** Pengguna memilih **#23/U26** saat meminta "Lanjutkan"; konteks pasar kini ditulis
> `--saring` dan dibaca dasbor hanya bila snapshot + preset + label sumber harga + versi hitung masih
> sama (**K61/T80**; `--dasbor` **18,95 → 0,74 dtk**). Tidak ada usulan baru; 44 bank tetap ditunda
> (K88) dan satu pekerjaan manusia (laporan PySide6, K84) tidak berubah.

> **Diperbarui 22 Okt 2026 (sesi 38) — U36 menunggu tinjauan.** Pengguna meminta pencatatan dulu
> untuk daftar jadwal pembaruan yang diperiksa saat refresh: tampilkan data yang jatuh tempo,
> data yang sudah diperbarui, dan data yang menunggu sumber/impor; jangan mengunduh ulang jika
> periode jadwalnya sudah dipenuhi. Usulan rinci ada di baris U36. **Belum ada kode atau data yang
> diubah.**
>
> **Diperbarui 22 Okt 2026 (sesi 39) — subkeputusan perilaku pembaruan U36 dikunci sebagai K89.**
> Jika data jatuh tempo, aplikasi memberi tahu dan menawarkan tindakan terpisah; `--refresh` tidak
> otomatis mengunduh/mengimpor dataset lain. Untuk notasi, sumber IDX otomatis sudah tersedia
> (`--ambil-notasi` → CSV → `--impor`). Checklist lintas dataset U36 tetap belum diimplementasikan.

| No | Pertanyaan | Usulan | Alasan |
|----|-----------|--------|--------|
| U37 | → **dikunci 29 Okt 2026 sebagai K101**. **Impor otomatis berkas IDX yang sudah diunduh pengguna** (diminta pengguna 29 Okt 2026, sesi 61: tiga berkas IDX — Ringkasan Saham, Notasi Khusus, PDF suspensi/UMA/UPT — “bisa diunduh otomatis sesuai jadwal?”). Pengunduhannya tetap manual (K95/K96: Syarat Penggunaan IDX melarang scraping/crawling, termasuk bot peramban yang mengeklik "Unduh"); yang ditanyakan: bolehkah **langkah sesudah klik Unduh** berjalan sendiri? **Mengubah K89** (refresh tidak memulai impor dataset lain) bila disetujui | **Usulan:** (a) folder pantau di konfigurasi, **kosong = mati** (bawaan); (b) perintah terpisah `--impor-unduhan` yang boleh dipanggil Task Scheduler atau tombol dasbor — **bukan** bagian `--refresh`, supaya K89 hanya berubah untuk perintah yang memang dipilih pengguna; (c) berkas dikenali dari pola nama yang sudah dipakai pembacanya (`Ringkasan Saham-YYYYMMDD.xlsx`, `Notasi Khusus-YYYYMMDD.xlsx`, PDF pengumuman K99/K100), lalu lewat jalur impor yang **sama** dengan tombol unggah (`permintaan_impor_ringkasan_idx` / `_notasi_idx` / `_pengumuman_idx`), bukan jalur kedua; (d) **cadangan otomatis** sebelum impor pertama tiap jalan; (e) berkas yang berhasil dipindah ke `unduhan-idx/`, yang ditolak dibiarkan di tempatnya dan **gagal berisik** (kode keluar ≠ 0, tampil di dasbor — AC-9), berkas lain di folder itu tidak disentuh; (f) penulis tunggal lewat kunci `db.py` — bila dasbor sedang menulis, jalan itu berhenti dengan pesan, tidak menunggu diam-diam (AC-19); (g) pengumuman multi-kode tetap manual seperti sekarang | Konfirmasi dasbor (token sekali pakai) melindungi dari impor tidak sengaja; di sini perlindungannya diganti cadangan otomatis + berkas yang dipilih pengguna sendiri dengan mengunduhnya. Yang diterima: impor tanpa ditinjau lebih dulu — ditekan oleh gerbang yang sudah ada (tumpang-tindih K97, "sudah ada dan sama", penolakan PDF tak dikenal). Alternatif lain yang sah untuk unduhan otomatis penuh: izin tertulis BEI atau layanan data berlisensi BEI (3.10) |
| U38 | → **dikunci 29 Okt 2026 sebagai K102**. **Pengingat terjadwal untuk unduhan IDX** (diminta bersama U37, sesi 61) | **Usulan:** perintah `--ingatkan` yang membaca `jadwal.susun` dan, bila ada butir IDX "jatuh tempo" atau "tidak dinilai" (suspensi/UMA), menampilkan notifikasi Windows berisi tautan halaman IDX-nya; dijadwalkan pengguna lewat Task Scheduler (misalnya tiap hari bursa 16.30 untuk Ringkasan Saham). Tanpa butir jatuh tempo → tidak ada notifikasi. Aplikasi **tidak** membuat tugas Task Scheduler sendiri; langkah pendaftarannya ditulis di `docs/lanjutan.md`. Bentuk notifikasinya (toast Windows tanpa dependensi baru, atau hanya membuka dasbor) diperiksa dulu sebelum dibangun | Isi pengingat sudah ada di tabel jadwal (K93); yang kurang hanya pemicu di luar dasbor. Membuat tugas terjadwal adalah perubahan konfigurasi sistem yang menetap, jadi tetap dilakukan pengguna. Suspensi/UMA tetap tidak bisa dinilai segar (K99) — pengingatnya hanya "periksa pengumuman hari ini" |
| U41 | → **dikunci 30 Okt 2026 sebagai K107**. **Dua pertanyaan dari gelombang 3 perluasan rasio bank (30 Okt 2026, sesi 71):** (a) **domain K79 keliru** — `banknobu.com`/`paninbank.com` (pengalih `/lander`) bukan situs bank (Nobu: `nobubank.com`; Panin: `panin.co.id`, kini 403), `bankccb.com` adalah bank AS (MCOR: `idn.ccb.com`, SSL *hostname mismatch*), `bankmayapada.co.id` tak terjangkau (aktif: `bankmayapada.com`), `smbc.co.id` kini "SMBC India" (domain BTPN belum ditemukan). Vonis §10.2 untuk PNBN/NOBU/MCOR/MAYA/BTPN diukur atas domain salah — dikoreksi? (b) **tanggal tercetak sehari lebih awal dari berkasnya** — BNII (tanda tangan 30 Jul 2026, PDF dibuat 31 Jul, tanpa `Last-Modified`) dan AMAR (tanda tangan 30 Jul, `Last-Modified` 31 Jul): tetap tanggal tercetak? | **Usulan:** (a) **koreksi tercatat, bukan pengukuran ulang menyeluruh**: catat domain yang benar di `docs/rasio-bank-kandidat-2026-10.md` §13.2 (sudah) dan pakai domain itu di gelombang berikut; vonis baru per bank lahir saat bank itu dikerjakan (PNBN → akses 403, MCOR → SSL), bukan dengan menjalankan ulang K79 untuk 44 bank; (b) **tetap K105(b) apa adanya** (kandidat sudah memakai 30 Jul): selisih 1 hari di bawah ambang 7 hari, sejalan dengan K86 (3 hari); membuat pengecualian satu hari berarti mengubah aturan yang baru dikunci demi selisih yang tidak berarti bagi data triwulanan | (a) yang penting adalah dokumen ketemu di domain resmi; pengukuran ulang 44 bank hanya untuk memperbaiki tabel lama mahal dan tidak mengubah langkah berikutnya; (b) K105(b) sengaja memberi ambang supaya selisih kecil tanda tangan–unggah tidak memicu aturan; kalau pengguna ingin AC-15 seketat mungkin, pilihan lain adalah "selalu tanggal paling akhir dari bukti yang ada", yang akan mengubah BNII/AMAR ke 31 Jul dan BRIS (K86) juga |
| U40 | → **dikunci 29 Okt 2026 sebagai K106**. **Dua pertanyaan `tgl_publikasi` dari gelombang 2 perluasan rasio bank (29 Okt 2026, sesi 70):** (a) **dokumen tanpa tanggal tercetak** — NISP (tanpa tanda tangan, host tanpa `Last-Modified`; metadata PDF dibuat 29 Jul 2026, siaran pers kinerja S1 30 Jul 2026) dan BCIC (tanpa tanda tangan; `Last-Modified` 11 Agu 2026, PDF dibuat 10 Agu) — tanggal apa yang dipakai? (b) **`Last-Modified` jauh sesudah semua bukti lain** — BINA: tanda tangan 29 Jul 2026, halaman PSP 15 Agu, PDF dibuat 19 Agu, `Last-Modified` **28 Okt 2026**; K105(b) dibaca harfiah memberi 28 Okt, padahal header itu bisa berarti unggah ulang | **Usulan:** (a) pakai **bukti terbit paling akhir yang tersedia** di antara `Last-Modified`, metadata pembuatan PDF, dan siaran pers bank untuk periode yang sama (NISP → **30 Jul 2026**, BCIC → **11 Agu 2026**), dan sebutkan sumber tanggalnya di `keterangan`; (b) **pakai K105(b) harfiah** (BINA → **28 Okt 2026**) — kandidat sudah memakai ini: tidak ada bukti bahwa berkas itu dapat dibaca publik sebelum 28 Okt, dan tanggal yang terlalu akhir hanya menunda angka masuk saringan, sedangkan yang terlalu awal melanggar AC-15 | Point-in-time (AC-15) lebih berat daripada kerapian: bila bukti tanggal terbit lemah, kesalahan ke arah "terlalu akhir" aman, ke arah "terlalu awal" tidak. Rinciannya `docs/rasio-bank-kandidat-2026-10.md` §12 |
| U39 | → **dikunci 29 Okt 2026 sebagai K105**. **Tiga pertanyaan dari gelombang 1 perluasan rasio bank (29 Okt 2026, sesi 69):** (a) **basis rasio** — bank yang menerbitkan dua set (CIMB Niaga, Danamon, KPMM Bank Jatim) memakai set **Bank/individual** atau **konsolidasian**? (b) **`tgl_publikasi`** bila tanggal tanda tangan jauh lebih awal dari unggahan (Bank Banten: tanda tangan 27 Jul 2026, folder unggah /2026/08/, Last-Modified 14 Agu 2026 — 18 hari)? (c) **PNLF** (Panin Financial, induk asuransi) ikut sasaran 34 bank padahal bukan bank — dikeluarkan? | **Usulan:** (a) **Bank/individual** — format Laporan Rasio Keuangan POJK 37/2019 adalah milik bank, dan hanya set itu yang memuat keempat rasio di setiap bank (set konsolidasian Danamon tanpa BOPO dan NIM-nya termasuk premi penjaminan Adira); angka konsolidasian tetap dicatat di `keterangan`. (b) pakai **tanggal yang lebih akhir** (unggahan/Last-Modified) bila selisihnya lebih dari 7 hari, supaya tidak ada angka yang terlihat sebelum terbit (AC-15); K86 (BRIS, selisih 3 hari) tetap. (c) keluarkan PNLF dari sasaran, catat sebabnya | (a) mencampur basis membuat ambang PRD 8.4 dibandingkan atas dua definisi berbeda (aturan keras 9 semangatnya); (b) point-in-time lebih berat daripada "nilai tercetak" bila selisihnya besar — memakai tanggal lebih awal berarti angka masuk saringan sebelum publik bisa membacanya; (c) Panin Financial tidak menerbitkan rasio bank, jadi mencarinya hanya akan berakhir "tidak terbaca" |
| U36 | → **dikunci 28 Okt 2026 sebagai K93** (dilaksanakan, T87). **Pelacak jadwal pembaruan data** (diminta pengguna 22 Okt 2026, sesi 38): pada setiap refresh, bagaimana aplikasi memberi tahu data mana yang perlu diperbarui dan mana yang sudah diperbarui? | **Usulan:** tampilkan checklist status yang diturunkan dari sumber data/rekaman pembaruan yang dapat dibuktikan, dan hanya tandai satu periode selesai setelah pengambilan serta impor yang relevan berhasil. Cadence awal: harga harian; suspensi/UMA harian dan notasi/papan pemantauan mingguan (PRD 7.1); cek sumber kedua mingguan (sudah punya rekaman cadence tersendiri); daftar emiten mengikuti Master File KSEI bulanan; fundamental/rasio bank mengikuti publikasi laporan kuartalan/tahunan; kalender bursa tahunan. Imbal hasil SUN ditandai menurut tanggal data saat metrik itu dipakai; cadence tetap perlu diputuskan karena PRD tidak menetapkan interval khusus. Kegagalan atau data yang belum tersedia tetap tampil jatuh tempo/menunggu, tidak dihitung selesai. Refresh tidak diam-diam memulai unduhan lain yang lama. | Pengguna ingin tahu apa yang perlu dikerjakan tanpa mengulang pekerjaan yang periodenya sudah dipenuhi. Status harus mencerminkan data yang benar-benar masuk, bukan sekadar proses pernah dicoba atau berkas CSV pernah dibuat. Cek sumber kedua sudah direkam terpisah di `cek_sumber_kedua` dan batasnya 7 hari inklusif (U19); sumber jadwal lain perlu dipetakan ke tanggal/sumber data yang ada sebelum memutuskan apakah perlu catatan peristiwa tambahan. `--refresh` saat ini hanya memperbarui harga dan memberi peringatan cadence cek sumber kedua; ia belum menampilkan checklist lintas data. Usulan ini **belum disetujui/dikunci** dan implementasi belum dimulai |
| U35 | ~~**Perluasan ke 44 bank sesudah hitung langkah manual (K79): lanjut sekarang, hanya yang otomatis, atau tetap tunda?** (muncul 19 Okt 2026, sesi 33, sesudah pengukurannya dijalankan)~~ → **diputuskan 19 Okt 2026, lihat K88** (tetap ditunda) | ~~**Usulan: tetap tunda.** Bila kelak diminta: kerjakan **34 bank yang "otomatis mungkin" lebih dulu**, lalu **8 bank yang menuntut langkah manual** (BTPS, DNAR, AGRS, BBMD, BBTN, BNLI, SUPA, BACA) hanya bila PDF-nya tersedia — menurut K79 pengguna mengunduh sendiri ke `pdf/manual/`, tidak diakali~~ → **dikunci sebagai K88, usulan dipakai apa adanya** | Pengukurannya (`.uji-data/uji-k79/bukti/k79-hasil-final.csv`, ringkasan di `docs/rasio-bank-kandidat-2026-10.md` §10): dari 44 bank sasaran, **8 menuntut langkah manual** (2 ditolak robots, 6 menolak klien HTTP), **2 tidak terukur** (INPC timeout, SDRA SSL), **34 boleh otomatis**. Tetapi izin robots **bukan** jaminan dokumen ketemu — pada uji satu tingkat, hanya **12 dari 34** benar-benar berpindah ke halaman publikasi (16 bila jangkar ikut dihitung) dan **11 dari 34** memuat tautan PDF — sehingga biayanya tetap **±34 kali pekerjaan pilot** (pencarian dokumen + render + verifikasi sel, K76/K83). Sementara itu **K68 tetap berlaku: 0 dari 49 bank tertahan *hanya* oleh rasio bank**, jadi menambah 44 dokumen tidak mengubah peringkat hari ini |
| U34 | ~~**`tgl_publikasi` BRIS: 21 Agu 2026 (tanggal tanda tangan) atau 24 Agu 2026 (`Last-Modified` berkas)?** (muncul 19 Okt 2026, sesi 31, saat aksi #29 memverifikasi setiap sel)~~ → **diputuskan 19 Okt 2026, lihat K86** (dipertahankan 21 Agu) | **Usulan: pertahankan 2026-08-21** — nilai yang **tercetak** dan yang diverifikasi kandidat. Bila yang lebih konservatif dipilih, tambahkan **baris revisi** bertanggal 2026-08-24 (append-only), bukan `UPDATE` | `tgl_publikasi` adalah pintu point-in-time `potret.muat` (`tgl_publikasi > tanggal_data` → baris dilewati), jadi tanggal yang terlalu awal membuat data dipakai **sebelum** tersedia. Tetapi mengubahnya sekarang berarti menafsir ulang sel yang justru diminta "cocok persis" (K83). Selisih 3 hari itu kecil dibanding ketidakpastian tanggal terbit yang sesungguhnya — pengumuman resmi tidak terbaca (robot/IDX 403, K79). Mencatatnya lebih jujur daripada memilih diam-diam; nilainya juga sudah disebut di `keterangan` baris BRIS |
| U33 | **`sumber` per baris pada `rasio-bank.csv` tidak tersimpan — dipakai atau dibiarkan?** (ditemukan 19 Okt 2026 saat pilot #21b; muncul karena berkas kandidat memuat `url`/`kutipan` per bank, lalu uji jalur menunjukkan kolom wajib itu dibuang) | ~~**Usulan: pakai `sumber` per baris untuk `rasio_bank`, seperti `fundamental` sejak K18** — tambahkan bidang `sumber` di `RasioBank`, isi dari kolom berkas di `berkas._baris_rasio_bank`, dan pakai nilai itu bila ada (bawaan: label kumpulan).~~ → **diputuskan 19 Okt 2026, lihat K78**; pelaksanaannya **aksi #27**, **SUDAH DIKERJAKAN sesi 27 (T77)** | Kolom `sumber` **wajib** di `rasio-bank.csv` (template `mejasaham/defaults/rasio-bank.contoh.csv` dan `berkas.SPESIFIKASI["rasio_bank"]`), tetapi `berkas._baris_rasio_bank` tidak mengisinya — kelas `RasioBank` tidak punya bidang itu — sehingga `ingesti._baris_rasio_bank` menulis `kumpulan.sumber` = `impor berkas: <folder>`. Artinya asal tiap publikasi bank (URL + tanggal) **hilang tepat pada data yang paling perlu ditelusuri** — dan bila diperluas ke 44 bank, 44 dokumen berbeda akan tampak berasal dari satu folder. Uji jalur pilot membuktikannya: `sumber baris: 'impor berkas: …\\uji-baca'` (`.uji-data/riset-idx/rasio-bank/bukti-uji-baca.txt`) |
| U31 | **Sesudah K69: pin CPython 3.13 untuk proyek, atau tetap 3.14 + T68?** (muncul 19 Okt 2026 sesudah reproduksi ulang + A/B dijalankan) | ~~Jangan pin sekarang; T68 tetap; kirim laporan upstream; pin ditinjau ulang hanya bila Qt menjawab atau cacatnya muncul lagi~~ → **diputuskan 19 Okt 2026, lihat K74** (usulan dipakai apa adanya; keputusan **pin** ditunda, bukan ditolak selamanya) | A/B-nya **2/12 vs 0/12**, dan uji Fisher dua sisi memberi **p ≈ 0,48**: selisih itu **tidak dapat dibedakan dari kebetulan**. Menurut huruf K69 pin **boleh** diputuskan (kontrol gagal di satu versi, tidak di versi lain), tetapi memindahkan pin Python proyek (K3) adalah keputusan dependensi yang mahal dibatalkan, dan hasilnya **bukan perbaikan** — paling banyak penurunan laju yang belum terbukti. Yang benar-benar dibutuhkan laporan upstream adalah kontrol yang bisa ditunjukkan, dan itu sudah ada (`.uji-data/uji-k69/bukti-k69.txt`, rincian `docs/riset-pyside6-gc-2026-10.md` bagian 10.4) |
| U32 | **Uji `tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah` bergantung detik — dibiarkan, atau diperbaiki?** (ditemukan 19 Okt 2026 saat K69: gagal 1 dari 12 jalan karena `jam_ambil` kedua impor berbeda 1 detik) | ~~Perbaiki — usulan aksi **#26**: bandingkan baris `snapshot` **tanpa** kolom waktu (`jam_ambil`, `batas_diketahui`)~~ → **diputuskan 19 Okt 2026, lihat K75** (usulan dipakai apa adanya; pelaksanaannya **aksi #26**, sudah dijalankan 19 Okt 2026 sesi 23) | Uji yang gagal ±1 dari 12 jalan membuat "suite hijau" berhenti bermakna: kegagalan yang timbul-tenggelam melatih orang mengabaikan hasil suite, dan itu persis yang dilarang aturan keras 7 (gagal itu berisik, bukan berisik secara acak). Yang diuji uji itu adalah **isi baris yang sama** antara jalur jendela dan baris perintah — bukan bahwa kedua impor terjadi pada detik yang sama; membandingkan kolom waktu menguji hal yang tidak pernah dijanjikan |
| U27 | **Laporan cacat PySide6 ke Qt: siapa yang mengirim?** (P37) | ~~Tetap pengguna yang mengirim; sesi agen merapikan drafnya jadi satu berkas siap-tempel~~ → **diputuskan, lihat K66**; berkasnya `docs/laporan-pyside6-siap-kirim.md` | Mengirim laporan atas nama orang lain ke pelacak pihak ketiga bukan pekerjaan yang boleh diambil alih tanpa keputusan; K60 a sudah memisahkan "draf siap" dari "dikirim", dan pemisahan itu yang membuat urutan K60 b (uji Python 3.13) punya gerbang yang jelas |
| U28 | **Uji Python 3.13 (K60 b): dialihkan ke sesi agen?** (P38) | ~~Bisa dikerjakan sesi agen, dengan syarat keputusan dependensi lebih dulu~~ → **diputuskan, lihat K67**; laporan dependensinya `docs/riset-pyside6-gc-2026-10.md` bagian 8, **pemasangannya masih menunggu persetujuan** | Pemasangan interpreter adalah perubahan lingkungan yang menetap di mesin Anda: itu kelas keputusan dependensi (`.venv` repo tidak boleh disentuh diam-diam), dan urutannya sesudah U27 beres menurut K60 (a) → (b) |
| U29 | **`rasio-bank.csv`: sesi agen boleh mengumpulkan angkanya?** (P39) | ~~Boleh sampai batas kandidat + kutipan, tidak boleh mengisi basis data~~ → **diputuskan, lihat K68**; lingkup pertamanya sudah diukur: **49 bank, 0 di antaranya tertahan hanya oleh rasio bank** | Bank tidak bisa masuk peringkat selama metrik kualitasnya lubang (K57), dan rasio bank hanya **satu** dari lubang itu. Mengukur lingkupnya lebih dulu mengubah janji "isi rasio lalu bank masuk peringkat" menjadi yang sebenarnya — persis yang dijaga aturan keras 2 (metrik tanpa data berstatus "tidak dihitung", bukan diisi tebakan) |
| U30 | **Folder tujuan cadangan: tetap dari konfigurasi, atau dipilih per-cadangan dari jendela?** (muncul saat aksi #19c dikerjakan) | ~~Tetap dari konfigurasi (`--folder-cadangan`/`MEJASAHAM_BACKUP`, bawaan: folder saudara folder data); kotak pilih folder ditambahkan hanya bila Anda memintanya~~ → **diputuskan, lihat K70** | Cadangan yang ditulis ke folder yang tidak diharapkan adalah cadangan yang tidak ditemukan saat dibutuhkan; karena itu #19c memilih **menyebut** folder tujuannya di dialog (dan itu diuji) alih-alih menambah satu jalan salah-lokasi. Yang belum tertutup, disebut apa adanya: pengguna jendela yang tidak pernah menjalankan `--folder-cadangan` mendapat cadangan di **disk yang sama** dengan datanya — PRD 9.12 menyebut "lokasi pilihan pengguna di luar folder data, mis. disk eksternal", dan itu baru tercapai bila lokasinya diarahkan sekali (atau bila kotak pilihan itu ditambahkan) |
| U1 | Penyimpanan: SQLite atau Parquet? | ~~SQLite (WAL) sebagai satu-satunya sumber kebenaran; Parquet hanya turunan arsip harga bila nanti perlu~~ → **diputuskan, lihat K5** | Satu berkas, transaksional, atomik, mudah dicadangkan (F12); Parquet tidak punya transaksi/lock |
| U2 | Rentang & biaya ingesti awal | 5 tahun OHLCV + indeks; ~900 kode `.JK`; jalankan sekali dengan jeda + ulang otomatis; laporan mutu menyebut jumlah gagal | Tahap 0: "data 800+ emiten tersedia untuk 5 tahun terakhir" |
| U3 | Cakupan fundamental | Impor berkas untuk emiten yang lolos saring likuiditas dulu (±150–200), format dibakukan, kolom sumber + tanggal publikasi wajib | risiko 15: "fundamental manual 800+ emiten tidak terkejar" |
| U4 | Aksi korporasi yang menyesuaikan harga | Hanya **split / reverse split / right issue**; dividen **tidak** menyesuaikan harga, tetapi masuk arus kas posisi & imbal hasil dividen | 9.3 bilang "split dan right issue"; 7.1 mencantumkan dividen sebagai data arus kas |
| U5 | Kalender bursa & hari libur | Tabel `kalender_bursa` dirawat manual (impor), dipakai untuk "hari bursa terakhir" & peringatan snapshot basi | 7.1; AC-8; tanpa ini "snapshot basi" tidak bisa dihitung |
| U6 | Nilai transaksi harian | Dihitung `close × volume` (bukan kolom `nilai` dari sumber) kecuali impor menyediakan nilai transaksi eksplisit | 8.2 ADTV20: "harga penutupan x volume" |
| U7 | "Hari bursa" untuk jendela metrik | Berbasis baris data yang ada di `kalender_bursa`, bukan kalender kalender biasa | 8.2 memakai satuan "hari bursa" |
| U8 | R (satuan risiko) | `(harga masuk − stop awal + biaya & slippage per lembar) × lembar akhir = 1R`; expectancy = hasil per keputusan ÷ R | 8.2; 9.8 |
| U9 | Drawdown | Dihitung dari `ekuitas_harian` yang sudah dikoreksi setoran/penarikan (arus dana tidak dihitung sebagai hasil) | 8.2; AC-13 |
| U10 | Tick & lot | Nilai disimpan di konfigurasi bertanggal, **bukan** konstanta kode; belum diisi sampai diverifikasi | 10 |
| U11 | Format tampilan | Angka format Indonesia (koma desimal, titik ribuan), tanggal `06 Okt 2026`; ekspor CSV opsi pemisah `;` + desimal koma, UTF-8 BOM | 11; agar tidak rusak di Excel Indonesia |
| U12 | Ambang "kandidat hari ini" | Skor total ≥ 70 pada snapshot terakhir, dari preset yang sedang dipilih | 8.3; 11.1 |
| U13 | Saran ukuran patuh di kalkulator | Pembulatan lot ke bawah dari batas paling ketat; rencana boleh disimpan setelah pengguna memilih (pelanggaran tetap tercatat di jurnal) | 9.7; AC-5 |
| U14 | Transaksi tanpa rencana (V6) | Tetap boleh dicatat (eksekusi manual nyata harus jujur tercatat), otomatis ditandai pelanggaran V6 + muncul di rekap kepatuhan | 9.8 katalog V6 |
| U15 | Metrik "tidak dihitung" | Tetap **tampil** dengan label "tidak dihitung" + alasan; hanya "metrik kualitas" fundamental > 18 bulan yang disembunyikan (7.3) | 9.5 vs 7.3 |
| U16 | Yang ditunda di v0.1 | Backtest (F8), peringatan EOD (F6), laporan PDF, bobot per rezim, ML → dicatat di `ideas.md`, tidak dikerjakan | tabel 5; 9.2 |
| U17 | Masa simulasi | Dicatat sebagai penanda mode; sistem memperingatkan bila ada transaksi nyata sebelum syarat simulasi terpenuhi, tetapi tidak memblokir | Q7 (17.1); 9.11 |
| U18 | Gerbang "gagal > 5%" ketika semesta datang dari daftar resmi yang memuat efek **tidak diperdagangkan** | ~~Bedakan gagal permanen dari gagal sementara; kode yang sumber harga jawab "simbol tidak ada" dihitung sebagai lubang yang diketahui, ambang 5% tetap berlaku untuk kegagalan sementara~~ → **diputuskan 9 Okt 2026, lihat K13** (usulan ini dipakai apa adanya) | Uji nyata 9 Okt 2026: refresh atas **973 kode** KSEI → **57 kode (5,9%)** dijawab Yahoo "No data found, symbol may be delisted", sehingga snapshot **tidak pernah bisa terbit** walaupun 916 kode lain berhasil diambil. Gerbang yang selalu menolak berhenti memberi informasi — kebalikan dari maksud PRD 9.3. Catatan: "ACTIVE" di Master File Efek KSEI berarti masih tercatat di KSEI, **bukan** masih diperdagangkan di IDX |
| U19 | Batas "tiap minggu" pada cek sumber kedua (PRD 7.3) | **7 hari inklusif**: cek yang berumur tepat 7 hari masih dihitung tepat waktu (hari itu memang jadwal berikutnya), dan "lewat" mulai hari ke-8. Sebuah jalan cek hanya memenuhi tuntutan itu bila cakupannya `lengkap` — cek yang berjalan tanpa harga pembanding, atau yang melewatkan sebagian emiten ber-ADTV20 tertinggi, dicatat tetapi **tidak** memadamkan peringatan | PRD 7.3 berkata "tiap minggu" tanpa menyebut hari batasnya, sedangkan aplikasi harus memutuskan satu angka untuk bisa memperingatkan. Arah pilihannya disengaja: cek tanpa pembanding **tidak** dihitung memenuhi, sebab menilainya memenuhi akan memadamkan peringatan justru ketika PRD 7.3 sama sekali belum dijalankan. Dipakai sejak 9 Okt 2026 (`mutu.JEDA_CEK_SUMBER_KEDUA_HARI`), dan dicatat di sini sebagai usulan supaya Anda bisa mengoreksinya |
| U20 | Bentuk entri `[[biaya_broker]]` ketika sumber **menyatakan tarifnya tetapi tidak menyatakan tarif minimum dan tanggal berlakunya** | ~~Buat "tidak dinyatakan sumber" menjadi keadaan yang sah: (a) `minimum` boleh tidak ada → NULL; (b) `berlaku_sejak` boleh berisi tanggal pengamatan dengan pendamping `asal_berlaku_sejak`~~ → **diputuskan 10 Okt 2026, lihat K22** (usulan ini dipakai apa adanya; migrasi 008 terpasang dan entri Stockbit sudah dimuat) | Terukur 10 Okt 2026 pada halaman tarif **Stockbit**: `Fee Beli 0,15%` / `Fee Jual 0,25%` dinyatakan tegas, sedangkan **tarif minimum tidak disebut sama sekali** dan **tanggal berlaku tidak dinyatakan** (yang ada hanya "Diperbarui pada: 05/08/2026" pada artikel bantuan — dan "diperbarui" bukan "berlaku sejak"). Bentuk entri yang berlaku sekarang **memaksa** salah satu dari dua karangan: `minimum = 0` (menyatakan "tidak ada minimum", padahal sumbernya diam) atau `berlaku_sejak` = tanggal tebakan. Aturan keras 1 melarang keduanya, jadi entrinya sampai sekarang **belum bisa dimuat** — bukan karena tarifnya belum ada, melainkan karena bentuknya belum bisa mengatakan "tidak dinyatakan" |
| U21 | Biaya broker yang **sudah all-in** (levy + PPN + PPh penjualan termasuk di dalamnya) | ~~Simpan penandanya **eksplisit di entri**, bukan di komentar: satu bidang `sudah_termasuk` berisi daftar komponen (`levy`, `ppn`, `pph_penjualan`) yang dinyatakan sumber sudah tercakup; kalkulator biaya **menolak** menambahkan komponen yang sudah termasuk~~ → **diputuskan 10 Okt 2026, lihat K23** (usulan ini dipakai apa adanya, termasuk daftar tiganya — `broker` tidak ikut karena tarif broker adalah tarifnya sendiri) | Halaman tarif Stockbit menyatakan apa adanya: *"Sudah termasuk biaya broker, biaya levy (BEI, KPEI, KSEI) 0,043%, PPN biaya broker 10%, dan PPh final untuk transaksi jual 0,1%"*. Tanpa penanda ini, entri B6/B7 0,15%/0,25% **akan dijumlahkan dua kali** dengan B8 (`[[pajak_penjualan]]` 0,1%) begitu kalkulator biaya dibuat di Tahap 2 — kesalahan yang tidak terlihat di keluaran mana pun, hanya di angkanya. Bandingkan Ajaib (0,1513%/0,2513%) yang juga all-in: dua broker dengan bentuk berbeda tidak boleh dipaksa masuk satu bentuk yang menyembunyikan perbedaan itu |
| U22 | Ambang "expectancy belum dapat dinilai": PRD 13.2 menulis **"30–50 keputusan"** — rentang, sedangkan aplikasi harus memutuskan satu angka | Pakai **batas bawahnya: 30 putaran tertutup**. Di bawah itu, angkanya **tetap dihitung dan ditampilkan** sebagai angka sementara, disertai kalimat "belum dapat dinilai" beserta sebabnya; pada 30 ke atas ia disebut dinilai | Rentang tidak bisa dipakai apa adanya untuk memberi status. Batas bawah dipilih supaya angkanya terlihat lebih awal — menyembunyikannya sampai 50 justru membuat pengguna menghitung sendiri di luar aplikasi — sementara labelnya tetap jujur bahwa sampel sekecil itu belum layak disimpulkan. Teksnya menyebut rentang PRD-nya, jadi yang membaca tetap tahu 30 adalah batas bawah, bukan angka PRD |
| U23 | Penyebut expectancy: **per transaksi** atau **per putaran** (posisi)? Kepatuhan memakai transaksi (PRD 9.8) | **Per putaran tertutup** (satu posisi = satu sampel), sedangkan kepatuhan tetap per transaksi. Keduanya dicetak dengan namanya masing-masing ("keputusan (transaksi)" vs "putaran tertutup") | Satu posisi bisa punya tiga transaksi (beli + dua jual), sedangkan hasilnya **satu**. Menghitungnya per transaksi membuat hasil yang sama masuk tiga kali, dan expectancy menjadi rata-rata yang bergantung pada berapa kali seseorang memecah penjualannya — bukan pada kualitas keputusannya. PRD 9.8 sendiri menghubungkan hasil "lewat `id_rencana` → `id_posisi` → transaksi", yaitu rantai yang berujung di posisi, dan 1R (8.2) juga didefinisikan per posisi |
| U24 | **Perlakuan baris pengumuman 20 Feb 2024 setelah tinjauan visualnya (K46) selesai** — bolehkah penandanya dilepas, dan apakah tanggal 20 Feb 2024 menjadi `tanggal_mulai`? | **DIPUTUSKAN 16 Okt 2026 → K53** (usulan ini dipakai apa adanya; pelaksanaannya ditunda ke sesi berikutnya). **Dilepas (K46 dibuka), dan 20 Feb 2024 TIDAK dipakai sebagai `tanggal_mulai`.** Pengumuman itu masuk `keterangan` episode yang sedang berjalan untuk ke-33 kode (sebagai sebab yang menempel), sedangkan MTFN — satu-satunya kode berpenanda — **mendapat episode yang selama ini hilang**: proxy ≤ 2023-10-30 → `tanggal_selesai` **2024-08-29** dari UPT `Peng-UPT-00011/BEI.PLP/08-2024`, terpisah dari episode 2025-06-30 yang sudah ada, dan dokumen 2023–2024 dipindahkan ke episode itu | Tinjauan visualnya sudah dijalankan 16 Okt 2026 (sesi 6): halaman PDF-nya **tidak memuat legenda/catatan kaki/kolom kelima** yang bisa memutuskan "status sebelum" versus "sesudah", sehingga pertanyaannya diselesaikan dari rekaman, bukan dari halamannya. Terukur: status ke-34 kode pada rekaman terakhir **sebelum** pengumuman (30 Jan/16 Feb 2024) **identik** dengan kolom status di pengumuman itu (34 identik · 0 berbeda; 24 *Seluruh Pasar* + 10 *Reguler dan Tunai*) — jadi ruang lingkup tindakannya sudah berlaku sebelum tanggal itu, dan kedua tafsir kolom menghasilkan akibat data yang sama. Bukti terkuat: UPT MTFN 29 Agu 2024 mencabut **delapan** pengumuman sekaligus dan `Peng-S-00006/BEI.PLP/02-2024` adalah nomor 6 di antaranya — suspensinya menyatu, bukan episode baru. Rincian di `docs/riset-suspensi-multi-kode-2026-10.md` ("Tinjauan visual pengumuman 20 Feb 2024") dan `.uji-data/uji-tinjauan-k46/` — **sudah dijalankan 16 Okt 2026 (sesi 7)**, rinciannya di bagian 5 ("Pelaksanaan K53 + K54") |
| U25 | **Bentuk baris ketika hanya PENCABUTAN yang dinyatakan sumber dan tanggal mulai tidak diketahui sama sekali** (K41: `ARTI`, `ELTY`) — sedangkan `tanggal_mulai` adalah bagian kunci baris | **DIPUTUSKAN 16 Okt 2026 → K54** (usulan ini dipakai apa adanya; pelaksanaannya ditunda ke sesi berikutnya bersama K53). **Pakai tanggal pengumuman SPT terawal yang dirujuk UPT** sebagai `tanggal_mulai` **proxy**, dengan `tanggal_selesai` dari UPT-nya dan penanda eksplisit: `ELTY` 2023-07-03 → 2023-10-19 · `ARTI` 2021-11-30 → 2023-11-23. Penandanya berbunyi bahwa **PDF SPT-nya belum pernah dilihat** dan tanggal mulai itu **tanggal pengumuman SPT**, bukan tanggal efektif | K41 memutuskan kedua kode itu **tetap dicatat** dengan nomor+tanggal SPT dari kutipan UPT — dan tanggal SPT-nya **memang dinyatakan** di dalam UPT (ELTY: 3 Jul 2023 & 31 Jul 2023; ARTI: 30 Nov 2021 … 31 Jul 2023), jadi tidak ada yang perlu dikarang. Yang **tidak** boleh dipakai adalah tanggal UPT-nya sendiri sebagai mulai, sebab ia tanggal **pencabutan** — memakainya membuat baris bersuspensi nol hari dan menyembunyikan bahwa suspensinya berjalan berbulan-bulan. Terukur 16 Okt 2026 (sesi 6): penanda K41 **0 kali** di seluruh `notasi_khusus` (semua revisi) dan 0 kali di berkas impor; `ELTY` **0 baris**, `ARTI` punya baris tetapi dari jalur lain tanpa penandanya — jadi keputusan ini sekaligus menutup janji K41 yang belum dijalankan — **sudah dijalankan 16 Okt 2026 (sesi 7)**, rinciannya di bagian 5 ("Pelaksanaan K53 + K54") |
| U26 | **Konteks pasar di dasbor (IHSG/rezim/breadth) dihitung ulang tiap kali, atau dihitung sekali saat `--saring` lalu dibaca kembali?** | **DIPUTUSKAN 17 Okt 2026 → K61** (usulan ini **dipakai sebagian**: menghitung ulang tetap yang berlaku sekarang, dan aturan kebasiannya disepakati lebih dulu **bila** suatu saat Anda memintanya dikerjakan). Yang berjalan sekarang: `dasbor.susun` memanggil `metrik.breadth` + `metrik.rezim_pasar` lewat jalur yang sama dengan saringan (T66), dengan harga `--dasbor` **2,8 dtk → 33–61 dtk** pada basis data 999.421 bar (setara `--saring` 32–55 dtk; rincian di `.uji-data/uji-dasbor/bukti/bukti-keadaan.txt`). Bentuk yang disepakati bila nanti dikerjakan: saat `--saring` dijalankan, simpan breadth + rezim + penutupan indeks **beserta `id_snapshot` dan versi presetnya**, lalu dasbor membacanya — dan **hanya** bila keduanya masih sama dengan keadaan sekarang; selain itu dihitung ulang atau dinyatakan "tidak dapat dinilai". **DIKERJAKAN 19 Okt 2026 (sesi 34)** setelah pengguna memilih opsi ini saat meminta “Lanjutkan”: `--saring` menulis konteks, dasbor membacanya hanya bila snapshot + preset + label sumber harga + versi hitung masih sama; kalau tidak, dihitung ulang. Terukur **18,95 dtk → 0,74 dtk (25,7×)** pada salinan data kerja, baris `Pasar` identik; bukti `.uji-data/uji-k61/bukti/`. | Angka pasar yang benar tidak boleh muncul dua kali dari dua jalur (K58/T66 menolak "menyalin hasilnya"), tetapi menghitungnya ulang juga berarti dasbor membayar beban saringan **setiap kali dibuka** — dan itu paling terasa di jendela, tempat layar dasbor adalah halaman pertama. Yang membuat pilihan jatuh ke **menghitung ulang** sekarang: biayanya **terlihat** (beban saringan yang sudah dikenal), sedangkan bahaya angka tersimpan **tidak terlihat** — angka basi terbaca sebagai keadaan hari ini, dan itu kelas kesalahan yang dicegah K58. Aturan kebasiannya tetap disepakati sekarang supaya pekerjaan itu (bila diminta) tidak menuntut pertanyaan baru |

---

## 3. Pertanyaan terbuka yang masih memblokir (mohon dijawab)

> **Keadaan 17 Okt 2026 (sesi 14): tidak ada pertanyaan yang memblokir — dan tidak ada yang menunggu
> jawaban.** Yang tersisa di bagian ini adalah riwayat pertanyaan beserta jawabannya. Dua yang
> terakhir di 3.3 — **P29** dan **P30** — sudah disahkan apa adanya → **K45**; sebelumnya P20/P21 →
> K20/K21, P22 → K24/K27, P23 → K26, P24 → K25, P25 → K30, P26 → K31, P27 → K32, P28 → K33, P15 →
> K34, dan P19 → K17. Empat pertanyaan perlakuan impor hasil rekonsiliasi (16 Okt 2026) juga sudah
> dijawab → **K46–K49**; **P31–P33 → K59–K61**; **P34–P36 di 3.8 → K62–K65**, dan yang terakhir
> **P37–P39 di 3.9 → K66–K68** (17 Okt 2026): laporan upstream PySide6 (berkas siap tempelnya sudah
> ada), uji Python 3.13 (dialihkan ke sesi agen, pemasangan interpreter **menunggu persetujuan**), dan
> `rasio-bank.csv` (boleh dikumpulkan sesi agen sampai batas kandidat + kutipan). **Yang tersisa
> sekarang bukan pertanyaan, melainkan pekerjaan:** aksi **#19c/#19d** (tindakan tulis lanjutan dari
> jendela; `#19b` selesai 17 Okt 2026 → T72) — lihat `docs/lanjutan.md` bagian 4.

### 3.1 Data & ingesti

**P2. Berkas yang harus Anda sediakan (yang tidak ada di yfinance).**
yfinance memberi OHLCV, indeks (`^JKSE`, dan proxy LQ45/IDX80), serta sebagian aksi korporasi. Yang tidak tersedia gratis dan harus diimpor: **kalender bursa**, **notasi khusus/suspensi/papan pemantauan**, **jumlah saham beredar & free float**, **aksi korporasi resmi**, **imbal hasil SUN 10 tahun**, **klasifikasi IDX-IC**, **rasio bank (NPL, CAR, BOPO, NIM)**, **fundamental**.
- Maukah Anda menyediakan berkas contoh (CSV/Excel) untuk minimal kalender bursa + notasi khusus + satu emiten fundamental, supaya format impor tidak saya karang?
- Kalau belum ada: saya buat **template + validasi ketat** dan mengosongkan isinya (fitur tetap jalan, tetapi metrik terkait berstatus "tidak dihitung").

**P3. Tarif biaya & pajak (wajib dari Anda, tidak boleh saya karang).**
- Biaya broker sisi beli & jual (persen atau minimum per transaksi) + nama broker;
- PPh final penjualan saham (**[PERLU VERIFIKASI]**: yang umum dikenal 0,1% dari nilai jual — mohon dikonfirmasi ke DJP/broker Anda dengan tanggal berlaku);
- Slippage: PRD 10 bilang "slippage satu tick" — dikonfirmasi satu tick, atau persen tetap?
Kalau belum ada, saya isi berkas konfigurasi dengan penanda `[PERLU VERIFIKASI]` dan kalkulator **menolak menghitung** sampai diisi (bukan memakai angka tebakan).

**P4. Lot & fraksi harga (tick) + batas ARA/ARB.**
- Lot: jumlah lembar per lot **[PERLU VERIFIKASI]** — angka 100 lembar adalah yang lama dan tetap harus dicek.
- Fraksi harga per rentang harga: tabel resmi IDX terbaru **[PERLU VERIFIKASI]** (kelompok fraksi pernah diubah, dan ada aturan khusus papan pemantauan khusus / full call auction).
- ARA/ARB: dipakai untuk backtest (v0.2) dan peringatan; untuk v0.1 hanya peringatan di kalkulator. Perlu tabel resmi + tanggal berlaku **[PERLU VERIFIKASI]**.
Usulan: saya siapkan tabel konfigurasi bertanggal dengan baris kosong bertanda `[PERLU VERIFIKASI]` dan Anda isi; sampai terisi, fitur yang bergantung padanya menampilkan peringatan.

Catatan pencarian (bukan sumber resmi, hanya penunjuk ke arah aturan yang harus dicek):
halaman pengumuman resmi IDX menolak akses otomatis (HTTP 403), jadi verifikasi harus
dilakukan manual di idx.co.id. Beberapa pemberitaan pasar menyebut aturan papan
pemantauan khusus (FCA) dan batas auto rejection berubah belakangan ini
([Kontan](https://investasi.kontan.co.id/news/bei-ubah-aturan-papan-pemantauan-khusus-berlaku-mulai-senin-2892026),
[Bisnis Market](https://market.bisnis.com/read/20260706/7/1985764/bei-siapkan-aturan-baru-auto-rejection-untuk-saham-fca),
[Stabilitas](https://www.stabilitas.id/bei-siapkan-penyempurnaan-mekanisme-fca-batas-auto-rejection-diperluas-jadi-4-kelompok/)).
Karena itu semua parameter bursa disimpan sebagai konfigurasi **bertanggal berlaku** dan
tidak pernah ditulis sebagai konstanta di kode (PRD bagian 10).

### 3.2 Definisi metrik — **sudah dijawab (K10, rincian di 1.4)**

P5–P12 sudah diputuskan. Bagian ini sengaja tidak dihapus, hanya dikosongkan, supaya
pertanyaan yang sama tidak muncul lagi seolah belum pernah dibahas.

**P17. Sumber mana yang dipakai berhitung bila basis data memuat dua label `sumber`?**
**Sudah dijawab 9 Okt 2026 → K14.** Isi pertanyaannya disimpan di sini supaya tidak muncul lagi
seolah belum pernah dibahas, dan supaya alasan teknisnya tetap bisa ditelusuri.

Sejak migrasi 005, harga pembanding untuk cek sumber kedua (PRD 7.3) hidup di tabel yang **sama**
dengan harga utama — itu memang yang membuat perbandingan dua sumber mungkin. Terukur 9 Okt 2026
(langkah 6): pembacaan untuk **perhitungan** belum menyaring sumbernya, sehingga dua bar tanggal
sama dari dua sumber masuk ke satu deret; hari yang terduplikasi memakan satu slot jendela 20 hari,
ADTV20 kedua puluh emiten itu menjadi "tidak dihitung", dan semesta likuid menyusut **235 → 215** —
yang hilang justru emiten paling likuid. Cacat itu **sudah diperbaiki** pada langkah 9 (T32), dan
bentuk aturannya dikonfirmasi pengguna sebagai **K14**: label dengan riwayat bar terbanyak, dengan
`--sumber` sebagai penimpa, selalu dilaporkan. Verifikasi: `--saring` pada `.uji-data/uji-p17`
berbunyi **likuid 235** — sama dengan sebelum harga pembanding diimpor
(`bukti-saring-p17.txt`).

**P18. Apa arti nama kolom `tanggal_notasi` di tabel `emiten` (PRD 12, tabel 23)?**
**Sudah dijawab 9 Okt 2026 → K15: tanggal pencatatan saham (listing date).** PRD mencantumkan
kolomnya tanpa menjelaskan isinya, padahal di bursa Indonesia "notasi" biasanya berarti **notasi
khusus** (suspensi, UMA, papan pemantauan) — dan itu sudah punya tabelnya sendiri
(`notasi_khusus`, lengkap dengan `tanggal_mulai`/`tanggal_selesai`). Karena itu pertanyaannya
pernah diajukan, dan jawabannya mengunci tafsir yang sudah dipakai sejak langkah 7: kolom ini
diisi dari `Listing Date` Master File Efek KSEI. Bukti bahwa sumbernya memang memuat tanggal
pencatatan, bukan tafsiran: GOTO terbaca `2022-04-11`, sama dengan siaran pers resmi GoTo
([GoTo completes landmark listing on IDX](https://www.gotocompany.com/en/news/press/goto-completes-landmark-listing-on-idx)).
Tafsir "tanggal mulai notasi khusus" **tidak** dipakai; bila kelak berubah, nilai yang tersimpan
diganti namanya lewat migrasi + baris baru, bukan ditimpa (aturan keras 3).

### 3.3 Perilaku produk

**P13. Fundamental lebih tua dari 18 bulan (7.3):** metrik kualitas disembunyikan dan emiten dikeluarkan dari saringan fundamental — dihitung dari `tgl_publikasi` terhadap tanggal snapshot? Usulan: ya.

**P14. Masa simulasi (Q7):** apakah pencatatan transaksi **nyata** diblokir sistem sebelum syarat terpenuhi (2 bulan/20 keputusan, kepatuhan ≥ 90%), atau hanya diberi peringatan mencolok? Usulan: peringatan + penanda, tidak memblokir (agar eksekusi manual yang sudah terjadi tetap jujur tercatat).

**P15. "Kelengkapan tesis 100%" (13.1):** jurnal hanya menilai transaksi; apakah entri "ide" tanpa tesis dikecualikan dari perhitungan kepatuhan? Usulan: ya, kepatuhan hanya atas transaksi (V1–V7).
**Sudah dijawab pengguna 10 Okt 2026 → K34.** Isi pertanyaannya disimpan di sini supaya tidak muncul lagi seolah belum pernah dibahas.

**P16. Dasbor "tindakan menunggu" (9.11):** isi minimal di v0.1 = posisi yang penutupannya menembus stop atau pembatal tesis terpicu, + tesis kedaluwarsa > 30 hari, + right issue dengan tenggat. Setuju?
**Sudah dijawab pengguna 10 Okt 2026 → K29: disahkan apa adanya, empat butir usulan + tiga tambahan.**

> **Keadaannya 10 Okt 2026 (Tahap 2 langkah 4):** butir **right issue** kini **dapat dinilai** dan
> sudah masuk daftar: `--dasbor` memunculkan `[right_issue_belum_diputuskan]` beserta tenggat dan
> sisa harinya, dan `--hak-right-issue` menampilkan haknya (rasio × lembar pada tanggal aksi).
> Dua tambahan di luar usulan P16 yang **masih** berlaku: posisi **tanpa stop**, dan right issue
> yang **tenggatnya belum dinyatakan** sumbernya (justru yang paling mudah terlewat). Right issue
> yang tenggatnya **sudah lewat** tanpa keputusan tidak lagi masuk daftar tindakan — jendelanya
> tertutup — tetapi muncul di catatan sebagai lubang yang perlu dicatat. Pertanyaannya tetap
> terbuka untuk **pengesahan**: kalau isinya ingin lain, yang berubah hanya daftar di
> `dasbor.tindakan_menunggu()`, bukan tabel atau modulnya.

**P25. Ekuitas harian: dicatat pengguna atau diturunkan dari transaksi + kas?** PRD 9.11 dan AC-13
menyebut ekuitas harian **"dihitung dari transaksi, kas, dan setoran/penarikan"**, sedangkan yang
dikerjakan sampai Tahap 2 langkah 3 adalah `--ekuitas-harian` yang **mencatat angka dari pengguna**
(sejak migrasi 010) ditambah `--arus-dana` untuk koreksi drawdown. Menurunkannya berarti menetapkan
**kas awal** (yang belum pernah dicatat di mana pun) dan aturan kapan posisi dinilai pada harga
terakhir versus harga transaksi. Usulan: tetap **dicatat pengguna di v0.1**, dengan dasbor
menampilkan `nilai posisi + kas` sebagai pembanding yang bisa diperiksa manusia — dan penurunan
otomatis dikerjakan bersama `posisi` yang lengkap (aksi korporasi & dividen), supaya angka kasnya
tidak setengah benar.
**Sudah dijawab pengguna 10 Okt 2026 → K30: tetap dicatat pengguna di v0.1**, dan dasbor menampilkan
`nilai posisi + kas` beserta selisihnya sebagai pembanding yang bisa diperiksa manusia.

**P23. Arti kolom `tanggal_tinjau` pada kandidat (9.6, 13.1).** PRD menyebut keluaran F4 berupa
"tanggal tinjau **berikutnya**", sedangkan aturannya berbunyi "tesis yang **tidak ditinjau lebih
dari 30 hari** ditandai kedaluwarsa". Dua tafsir yang sama masuk akal:
(a) `tanggal_tinjau` = **jatuh tempo berikutnya**, entri kedaluwarsa ketika tanggal itu sudah lewat;
(b) `tanggal_tinjau` = **terakhir ditinjau**, entri kedaluwarsa ketika lebih dari 30 hari sejak itu.
**Sudah dijawab pengguna 10 Okt 2026 → K26: tafsir (a)**, yaitu tafsir yang memang sudah dikerjakan
di Tahap 2 langkah 1. Isi pertanyaannya disimpan di sini supaya tidak muncul lagi seolah belum
pernah dibahas.

**P24. Batas bobot per sektor tidak dapat dinilai selama `sektor_idx_ic` kosong (9.7, 8.2, 12).**
PRD 9.7 menetapkan ukuran akhir dibatasi juga oleh **batas bobot per sektor 30%**, sedangkan kolom
`sektor_idx_ic` sengaja dibiarkan kosong sejak K12 (taksonomi KSEI bukan IDX-IC) dan seluruh
`idx.co.id` masih 403 dari mesin ini — jadi tidak ada sumber IDX-IC yang bisa diambil otomatis.
**Sudah dijawab pengguna 10 Okt 2026 → K25: kolom sektor KEDUA dari sumber data
(`sektor_sumber`), berlabel sumbernya, dikerjakan sekarang.** Tiga jalan yang dipertimbangkan waktu
itu disimpan sebagai riwayat:

| Jalan | Akibatnya |
|---|---|
| **(a) Biarkan "tidak dinilai"** (keadaan sebelum K25) | Tidak ada angka karangan, tetapi batas 30% praktis tidak ditegakkan — dan itu terlihat di setiap rencana, bukan tersembunyi |
| **(b) `sektor_idx_ic` diisi manusia** di `emiten.csv` (973 baris) | Batas sektor langsung berfungsi dan kriteria "median sektor" PRD 8.2 juga ikut membaik; pekerjaannya manual dan berulang setiap ada emiten baru. **Tetap lebih baik dan tidak dihalangi** — begitu terisi, ia yang dipakai |
| **(c) Kolom sektor kedua dari sumber data yang sudah dipakai** (`sector`/`industry` yang sama dengan `--ambil-jenis`, K21), berlabel sumbernya dan **bukan** IDX-IC — **DIPILIH (K25)** | Batas sektor bisa ditegakkan sekarang tanpa mengarang. Dua taksonomi **tidak boleh dicampur** dalam satu penjumlahan paparan: yang dipakai disebut di keluaran, dan rencana dari taksonomi lain tidak ikut dijumlahkan serta jumlahnya dilaporkan |

**P26. Penebusan HMETD yang jumlahnya bukan kelipatan lot (9.11 vs 10).** PRD 10 menetapkan
"jumlah lembar selalu kelipatan lot", sedangkan hak atas right issue adalah **rasio × lembar yang
dipegang** dan hasilnya tidak selalu kelipatan lot: terukur di bukti langkah 4, hak 6.250 lembar
dari 25.000 lembar × rasio 4:1. `--catat-transaksi` menolaknya (dan itu memang PRD 10) dengan pesan
yang menyebut kelipatan terdekatnya (6.200 atau 6.300), jadi pengguna tidak tertahan — tetapi
artinya penebusan tidak pernah bisa dicatat **seluruhnya** bila haknya berpecahan lot, dan sisa
haknya hanya bisa dijual lewat `jual_hmetd`. Usulan: **tetap seperti sekarang di v0.1** — lot
adalah parameter bursa bertanggal (K1) dan mengecualikannya untuk satu jenis transaksi akan
membuat "lembar" berarti dua hal. Yang **belum** dikerjakan dan mungkin layak: menyebutkan di
`--hak-right-issue` bahwa hak itu bukan kelipatan lot, supaya pengguna tidak menemukan penolakannya
baru saat mencatat. Pertanyaan: apakah pengecualian lot untuk penebusan HMETD memang tidak
diperlukan?
**Sudah dijawab pengguna 10 Okt 2026 → K31: aturan lot tetap berlaku**; yang dikerjakan adalah
memberitahukannya lebih awal (di `--hak-right-issue`, `--dasbor`, dan ringkasan keputusan).

**P27. Right issue mematikan metrik harga emiten itu di `--saring` (9.3, 7.2, U4).** Terukur
10 Okt 2026 (tanpa perubahan kode, hanya dengan menambahkan baris uji right issue): semesta likuid
turun **227 → 225**. Sebabnya aturan lama di `mejasaham/penyesuaian.py` — PRD 9.3 menuntut harga
disesuaikan terhadap right issue saat dibaca, rumus harga teoretis ex-rights (TERP) tidak
ditetapkan PRD, jadi emiten yang punya right issue dalam jendela metriknya berstatus **"tidak
dihitung"** — dan emiten itu lalu keluar dari semesta likuid. Dua jalan: **(a) biarkan** (keadaan
sekarang; tidak ada angka karangan, tetapi satu right issue menghapus emiten itu dari peringkat
selama jendelanya), atau **(b) hitung TERP** `(harga cum × lembar lama + harga tebus × lembar baru)
÷ (lembar lama + lembar baru)` dari data yang **sudah** tersimpan (penutupan sebelum ex-date, rasio,
`harga_tebus` yang sejak migrasi 013 wajib diisi). Usulan: **(a) di v0.1**, sebab rumusnya tidak ada
di PRD dan menyentuh angka saringan yang sudah terverifikasi — sementara (b) terbuka kapan saja
karena tempatnya satu fungsi (`penyesuaian._faktor`/`sesuaikan`). Beda dengan posisi: right issue
**tidak** mengubah lembar posisi (K28), jadi jalur F11 tidak terpengaruh pilihan ini.
**Sudah dijawab pengguna 10 Okt 2026 → K32: dibiarkan apa adanya di v0.1** (TERP tidak dibangun
sekarang).

**P28. Dividen dihitung, bukan dicatat — bagaimana bila angkanya berbeda dari kas yang diterima?**
K28 menetapkan dividen posisi **dihitung** dari `aksi_korporasi` (sumber tidak resmi) × lembar
pada tanggal ex-date, dan masuk hasil sebagai suku terpisah. Yang tersedia untuk memeriksanya:
rincian **per peristiwa** (tanggal, rupiah/lembar, lembar, jumlah) di `--posisi`, dan label
sumbernya disebut. Yang **belum** ada: jalur mengoreksi bila kas yang benar-benar masuk berbeda
(mis. pajak dipotong di sumbernya, atau tanggal ex-date berbeda). Usulan: **belum di v0.1** —
mengoreksinya menuntut tabel arus kas posisi yang menampung baris manusia, dan selama angkanya
masih bisa diperiksa per peristiwa, tabel itu menambah satu sumber kebenaran baru tanpa menghilangkan
kebutuhan memeriksanya. Pertanyaan: apakah cukup, atau perlu `--catat-dividen` sekarang?
**Sudah dijawab pengguna 10 Okt 2026 → K33: cukup di v0.1** — dividen tetap dihitung, dan yang
tersedia untuk memeriksanya adalah rincian per peristiwa beserta label sumbernya.

**P29. Pelanggaran yang bukan transaksi (V5 stop digeser, V7 posisi dipertahankan) dihitung ke
transaksi yang mana?** PRD 9.8 menutup katalognya dengan rumus *"Kepatuhan = transaksi tanpa
pelanggaran ÷ seluruh transaksi"*, sedangkan PRD 13.1 menargetkan *"≥ 90% **keputusan** tanpa
pelanggaran"* — dan V5/V7 bukan transaksi, melainkan tindakan atas posisi. Kalau keduanya
dikeluarkan dari rasio, dua pelanggaran yang paling mudah terjadi tidak akan pernah terlihat di
angka kepatuhan; kalau dimasukkan tanpa aturan, rasio berubah karena kejadian yang tidak pernah
dicatat sebagai keputusan. **Usulan yang sekarang dipakai** (`jurnal.py`): tiap pelanggaran
menempel pada **transaksi terakhir posisi itu pada atau sebelum tanggal kejadian**; V3 pada
transaksi **pertama** yang mengeksekusi rencananya; V7 pada transaksi terakhir posisi yang masih
terbuka. Pelanggaran yang tidak punya transaksi (mis. rencana yang melanggar batas dan belum
dieksekusi) **tidak** mengubah rasio, tetapi tetap dicetak di bagian "di luar periode/tanpa
transaksi". Pertanyaan: apakah aturan itu sudah sesuai maksud Anda, atau pelanggaran tingkat posisi
lebih baik dihitung sebagai **keputusan tersendiri** (penyebutnya "keputusan", bukan "transaksi")?

**P30. Tombol "[Tandai selesai]" (PRD 11.5) tidak punya kolomnya di PRD 12.**
Wireframe 11.5 memuat tiga tombol — `[Ekspor]`, `[Tandai selesai]`, `[Tulis pelajaran]` — sedangkan
tabel `jurnal` di PRD 12 hanya menyebut `id, tanggal, kode, alasan, patuh_aturan,
kode_pelanggaran, pelajaran` (tanpa tanggal tinjau maupun penanda selesai). Dua hal karena itu
dipetakan terbuka: `tanggal_tinjau` = **tanggal tinjau berikutnya** (arti yang sama dengan
`kandidat.tanggal_tinjau`, dan disebut `docs/skema-data.md` 5.15), dan `selesai_pada` = tanggal
entri jurnal itu **ditandai selesai** (tombol `[Tandai selesai]`, diisi lewat `--tandai-selesai`).
Pertanyaan: apakah kedua arti itu yang Anda maksud, atau "tandai selesai" sebenarnya berarti
menutup keputusannya (mis. posisinya sudah ditutup) sehingga tidak perlu kolom sendiri?

### 3.4 Urutan membuka blokir menurut tahap (usulan)
P3/P4 tidak perlu menghambat Tahap 0: fondasi data tidak memakai lot, tick, biaya, atau pajak.
| Tahap mulai | Yang harus sudah dijawab | Dipakai untuk |
|-------------|--------------------------|---------------|
| Tahap 0 | **sudah cukup** (K5 + K6) | Skema, ingesti OHLCV/indeks/aksi korporasi, kalender bursa |
| Tahap 1 | P1, U5, impor notasi khusus | Semesta likuid, statistik sektor, breadth |
| Tahap 2 | P4 (lot & tick), P3 (biaya, PPh, slippage) | Pembulatan lot, ukuran posisi, definisi 1R |
| Sebelum uang nyata | ARA/ARB + aturan papan pemantauan khusus lengkap | Peringatan eksekusi, backtest Tahap 4 |

### 3.5 Kalender 2025 — berkas yang lulus syarat sumber sudah bukan revisi terakhir

**P19. Bolehkah tanggal libur bursa 2025 diambil dari revisi pengumuman KSEI yang sudah
digantikan, kalau tanggalnya terbukti sama dengan revisi terakhirnya?**
**Sudah dijawab 9 Okt 2026 → K17: boleh, dengan syarat tanggalnya identik** — dan syaratnya sudah
dikerjakan (`kalender.cari_revisi_lama` + uji). Isi pertanyaannya disimpan di sini supaya tidak
muncul lagi seolah belum pernah dibahas.

Keadaannya terukur 9 Okt 2026 (langkah 10):

| Berkas di server KSEI | Nomor | Syarat T31 | Tanggal libur |
|---|---|---|---|
| `Pengumuman_Perubahan_…_Tahun_2025.pdf` | KSEI `PENG-0004/DIR/KSEI/0825` · IDX `Peng-00149/BEI.POP/08-2025` | **lulus** (menyatakan menindaklanjuti *Kalender Libur Bursa* IDX) | **25 tanggal** |
| `Pengumuman_Perubahan_Kedua_…_Tahun_2025.pdf` (yang ditautkan halaman sekarang) | KSEI `PENG-0007/DIR/KSEI/1225` · IDX `Peng-00150/BEI.POP/08-2025` | **ditolak** (menindaklanjuti kalender operasional EBA/sukuk) | **25 tanggal, identik** |

Dibandingkan tanggal per tanggal: **tidak ada satu pun tanggal yang berbeda**; satu-satunya
selisih adalah perbaikan salah ketik pada satu keterangan ("Cuti Bersama Tahun Baru Imlek
257 6 Kongzili" → "2576 Kongzili"). Jadi tanggal libur bursa 2025 **sudah diketahui dan dikuatkan
dua dokumen**; yang tidak ada adalah satu berkas yang memenuhi T31 **dan** sekaligus revisi
terakhir.

- **Yang dipakai (K17):** tanggal dari revisi lama, **hanya bila** seluruh tanggalnya identik
  dengan berkas yang ditautkan; kalau ada satu saja yang berbeda, revisi lama ditolak dan tahun
  itu tetap kosong beserta alasannya. Dengan syarat itu, yang dipakai bukan "dokumen basi",
  melainkan tanggal yang sudah dikonfirmasi dokumen yang lebih baru — dan sumbernya tetap
  pengumuman resmi.
- **Terukur sesudahnya:** `--ambil-kalender` memuat **2025 (25 libur) + 2026 (22) + 2027 (20)** =
  1095 baris; laporan mutu tidak lagi memuat temuan `kalender_belum_memuat` untuk 2025, dan
  tanggal 2025 di basis data membawa sumber `PENG-0004/DIR/KSEI/0825`. Bukti:
  `.uji-data/uji-kalender-2025/`.
- **Yang tidak dilakukan:** memakai berkas 2025 apa adanya lalu menganggapnya sah, atau menyalin
  tanggal dari pemberitaan. Keduanya persis yang dilarang aturan keras 1.

**2021–2024 tidak punya pertanyaan yang sama**: berkasnya **404** di KSEI (dicoba dengan tiga pola
nama, termasuk pola yang dipakai tahun lain), dan Arsip Internet hanya menyimpan salinan
**terbaru** halaman itu — setiap percobaan salinan per tahun mengembalikan halaman yang sama
dengan tautan hari ini. Untuk tahun-tahun itu, jalur impor berkas adalah satu-satunya jalan.

### 3.6 Yang menunggu jawaban Anda sekarang (dicatat 10 Okt 2026)

**Sudah dijawab seluruhnya 10 Okt 2026 → K20 dan K21.** Isi pertanyaannya disimpan di bawah supaya
tidak muncul lagi seolah belum pernah dibahas, dan supaya alasan tiap jawabannya tetap bisa
ditelusuri. **Yang tersisa bukan pertanyaan, melainkan pekerjaan**: mencari `notasi-khusus.csv` dan
`rasio-bank.csv` (P22), yang pengguna nyatakan **tidak** dimilikinya — jadi tugas aplikasi/sesi
berikutnya, bukan tugas manusia.

**Ditambahkan 10 Okt 2026 (Tahap 3 langkah 1, F7):** dua pertanyaan **baru** ada di 3.3 — **P29**
pelanggaran tingkat posisi (V5/V7) diatribusikan ke transaksi yang mana, dan **P30** pemetaan tombol
"[Tandai selesai]" PRD 11.5 yang tidak punya kolomnya di PRD 12. Keduanya **tidak memblokir**:
jawabannya hanya mengubah cara menghitung/menamai satu hal, dan keduanya sudah dipakai dengan
pemetaan yang dinyatakan terbuka (`docs/arsitektur.md` T53, `docs/skema-data.md` 5.15).

**P20 (→ K20).** Broker: **Stockbit**; slippage: **mode `tick`**. Yang belum: **tarif** Stockbit
sendiri harus diambil dari halaman tarif resminya — sampai itu, entri `[[biaya_broker]]` tetap
tidak diisi dan kalkulator biaya menolak menghitung. Draf `parameter-bursa.usulan.toml` (6 entri,
lulus pemuat) sudah memuat segalanya kecuali dua itu; **belum dimuat ke basis data**.

Catatan penting untuk B4: rezimnya **berganti dua kali** — Kep-00136/BEI/09-2026 &
Kep-00137/BEI/09-2026 (ditetapkan 21 Sep 2026, **berlaku 28 Sep 2026**), lalu **1 Jan 2027**
(ARB menjadi simetris = ARA). Nilainya harus disimpan **bertanggal-bertingkat**, bukan satu.
Yang belum terbaca dari sumber resmi: **nomor SK** untuk lot/settlement/PPh, **jam sesi FCA**
(B3), dan tarif PPh dari sumber primer — seluruh `idx.co.id` membalas 403 dari mesin ini
(12 jalur diuji, 0 berhasil; `web.ksei.co.id` membalas 200, jadi yang diblokir memang IDX).

**P21 (→ K21).** `jenis` emiten diturunkan dari data, dengan tiga batas di K21.

**P22. `notasi-khusus.csv` dan `rasio-bank.csv` — pengguna tidak memilikinya (10 Okt 2026), jadi
mencarinya adalah pekerjaan aplikasi.**

**Keadaannya 10 Okt 2026 (malam): KEDUANYA TERJAWAB — P22 tertutup.**

* **`rasio-bank.csv` → diputuskan, lihat K24.** Jalur PDF-nya sudah diukur sampai dasar
  (`docs/lanjutan.md` 2.1a): peramban **tidak** diperlukan, tetapi penguraian dokumen rasio
  menuntut pustaka pengurai PDF, dan pengguna memilih **mengisi berkasnya secara manual** untuk
  bank yang masuk kandidat. Jadi ini **bukan lagi pekerjaan aplikasi** — dan bukan pertanyaan
  terbuka.
* **Daftar papan pemantauan khusus → SELESAI, lihat K27.** Pengguna memilih "lanjut cari sumber
  yang memuat daftarnya sebagai teks", dan pencariannya menemukan jalur yang selama ini dianggap
  mati: **`www.idx.id`** (domain resmi IDX yang lain) melayani halaman notasi khusus dengan
  **HTTP 200** untuk UA yang menyebut dirinya. Terukur 10 Okt 2026: **122 baris notasi, 68 emiten
  ber-notasi X (papan pemantauan khusus), data per 08 Okt 2026**, dan sesudah diimpor `--saring`
  berhenti menyebut daftarnya "PERINGKAT SEMENTARA" — kini **"Kandidat teratas"**, dengan semesta
  likuid menyusut 235 → 227 karena delapan emiten ber-notasi tersaring keluar. Adaptornya
  `mejasaham/notasi.py` + `--ambil-notasi`; rinciannya K27 dan **T42**.
  **Yang belum diambil, dan disebut apa adanya:** daftar **suspensi** dan **UMA** (keduanya punya
  halaman sendiri di domain yang sama dan sudah terbukti 200) — ia masuk sebagai `jenis`
  tersendiri kalau nanti diambil, bukan dicampur tanpa penanda.

**Yang perlu diketahui sesi berikutnya sebelum mencoba lagi** (tetap berlaku): **7 jalur sudah
terbukti mati** untuk data IDX — `www.idx.co.id` dan `www2.idx.co.id` (403, Cloudflare), endpoint
JSON (`/primary/...`, `/umbraco/...`), PDF resmi (`/Media/*.pdf`, `/StaticData/*.pdf`), varian
`http://`, `r.jina.ai` (kena challenge di sisinya sendiri), dan empat proxy CORS publik
(522/403/429/000). Jalur peramban sungguhan **sudah diuji** dan batasnya terukur ( bisa menembus
`www.idx.co.id`, tetapi `requests` tidak bisa memakai cookienya dan burst diblok lama) — jadi ia
**bukan** lagi "belum diuji". Jalur yang belum diuji dan masih layak untuk notasi khusus: sumber
sekunder yang memuat **daftar emitennya dalam bentuk teks** (bukan PDF), atau media pasar modal
yang merinci perubahan papan pemantauan per tanggal.

Yang **tidak** menunggu apa pun: kalender **2021–2024** (tidak menghambat hari ini — kalender
2025–2027 sudah terpasang, dan jendela saringan memakai hari bursa terakhir).

### 3.7 Yang menunggu jawaban Anda — **SUDAH DIJAWAB SELURUHNYA 17 Okt 2026 ("sesuai rekomendasi")**

> **Keadaan: tidak ada pertanyaan di bagian ini yang menunggu** — ketiganya sudah dijawab. Isi
> pertanyaannya **dibiarkan apa adanya** di bawah supaya tidak muncul lagi seolah belum pernah
> dibahas dan supaya alasan tiap usulannya tetap bisa ditelusuri. Jawabannya dikunci di bagian 1:
> **P31 → K59** (+ bentuk teknisnya **T69**), **P32 → K60**, **P33 → K61** (dan **U26** di bagian 2
> kini berstatus diputuskan, dengan aturan kebasiannya sudah disepakati bila pekerjaan itu suatu saat
> diminta). Antrean kerjanya di `docs/lanjutan.md` bagian 4: **aksi #19 sudah tidak terhalang apa
> pun**; **#22** berjalan menurut K60 (laporan upstream dikirim pengguna, lalu uji Python 3.13);
> **#23** (simpan konteks pasar) **belum dipicu** — menunggu permintaan Anda. **Yang menunggu di
> bagian 3.8 (P34–P36) juga sudah dijawab** (17 Okt 2026 → **K62–K64**, bentuk teknisnya **T71**),
> jadi **tidak ada pertanyaan yang menunggu di bagian ini.** **(Diperbarui 19 Okt 2026: dua usulan
> baru di bagian 2 — U31 dan U32 — menunggu jawaban saat itu; **keduanya sudah dijawab 19 Okt 2026
> (sesi 22) → K74/K75**.)**

Tiga pertanyaan. Hanya **P31** yang **memblokir** pekerjaan berikutnya (aksi #19); dua lainnya sudah
punya jawaban sementara yang berjalan, dan jawaban Anda menentukan apakah langkah lanjutannya
dikerjakan atau ditutup.

**P31 (memblokir aksi #19) — perilaku jendela saat kunci tulis basis data sedang dipegang proses lain.
→ DIJAWAB 17 Okt 2026: disetujui apa adanya → K59 + T69.**
K55 sudah menetapkan bahwa ini harus dijawab **sebelum** jendela boleh menulis (A2/AC-19: jendela dan
`--refresh` tidak menulis bersamaan; kunci tulis SQLite dengan `busy_timeout` 5 detik). Lima hal yang
ditanyakan, beserta usulan saya — jawab "sesuai rekomendasi" bila setuju semuanya:

* (a) **Menunggu atau langsung berhenti?** Usulan: **menunggu sampai `busy_timeout` habis** (5 detik,
  sudah terpasang di koneksi) sambil menampilkan "bekerja…", lalu bila tetap gagal **berhenti dengan
  pesan**. Alternatifnya: berhenti di detik pertama — lebih cepat memberi tahu, tetapi menolak
  penulisan yang sebenarnya bisa berhasil 0,2 detik kemudian.
* (b) **Bunyi pesannya** (draf, silakan ganti): *"Basis data sedang ditulis proses lain (mis.
  `--refresh`). Jendela belum menulis apa pun. Tunggu sampai proses itu selesai, lalu coba lagi."* —
  kalimat **"belum menulis apa pun"** itu wajib ada: pengguna harus tahu tidak ada yang setengah tertulis.
* (c) **Cakupan tahap ini:** kelima tindakan yang disebut K55 sekaligus (catat transaksi, simpan
  rencana, catat jurnal, impor, cadangan/F12), atau bertahap? Usulan: **bertahap** — dahulu tiga yang
  menambah baris (`posisi.catat_transaksi`, `risiko.simpan`, `jurnal.catat`), **lalu** impor, dan
  **cadangan/pulihkan paling akhir** karena `--pulihkan` menimpa basis data.
* (d) **Konfirmasi sebelum menulis:** untuk semua tindakan, atau hanya yang merusak? Usulan: dialog
  konfirmasi untuk **semua** (K55 syarat (b)), dengan ringkasan angka yang akan ditulis (kode, lembar,
  harga, biaya); untuk pulihkan, konfirmasi kedua yang menyebut folder cadangannya.
* (e) **F12 di jendela:** cadangan saja (buat + daftar) pada tahap ini, atau termasuk pulihkan?
  Usulan: **cadangan + daftar** dahulu; pulihkan menunggu tahap tersendiri.

**P32 — cacat PySide6 6.12.0 + CPython 3.14.7: langkah mana yang ditempuh?
→ DIJAWAB 17 Okt 2026: urutannya (a) laporan upstream lalu (b) uji Python 3.13 → K60.**
Sudah ditangkal (**T68**) dan diriset (`docs/riset-pyside6-gc-2026-10.md`, termasuk **draf laporan
upstream siap tempel** dan dua repro sintetis yang tidak memicunya). Pilihannya: (a) **lapor upstream**
(tidak mengubah kode; Anda yang mengirimkannya), (b) **uji Python 3.13** dengan PySide6 6.12.0 yang
sama — bila tidak lagi mati, pin versi Python adalah jawaban paling murah, tetapi menuntut pemasangan
interpreter (keputusan dependensi), (c) **uji PySide6 versi lain** (6.11 / 6.13) pada Python 3.14,
(d) **terima T68 apa adanya**. Usulan: **(a) lalu (b)**. **Tidak memblokir aksi #19** — penangkalnya
sudah terpasang dan suite penuh 0 gagal dari 8 jalan.

**P33 — biaya konteks pasar di dasbor: teruskan menghitung ulang, atau simpan saat `--saring`?
→ DIJAWAB 17 Okt 2026: **tetap dihitung ulang**; U26 tetap terbuka dengan aturan kebasian yang sudah
disepakati → K61.**
Keadaannya sekarang: `--dasbor` membayar beban yang sama dengan `--saring` (**2,8 dtk → 33–61 dtk**
pada basis data 999.421 bar). Anda sudah menyatakan **terima apa adanya**; yang belum diputuskan
adalah apakah usulan **U26** (simpan breadth + rezim + penutupan indeks saat `--saring`, beserta
`id_snapshot` + versi presetnya, lalu dibaca kembali) dikejar. Bila ya, satu hal lagi yang harus Anda
tetapkan: **kapan angka tersimpan tidak boleh ditampilkan lagi** — usulan: hanya bila `id_snapshot`
**dan** presetnya masih sama dengan keadaan sekarang; selain itu dihitung ulang atau dinyatakan "tidak
dapat dinilai". Bila tidak, U26 **ditutup sebagai ditolak** dan alasannya dicatat di sana.
**Tidak memblokir aksi #19.**

**Yang tetap bukan pertanyaan, melainkan pekerjaan manusia (Anda):** mengisi
`rasio-bank.csv` — kerangkanya sudah dibuat aksi #21 (49 kode bank, `.uji-data/uji-jenis/konfigurasi/`)
dan menunggu angka dari **publikasi resmi** bank/OJK; selama kosong, keempat kriteria bank tetap
"tidak dihitung" dan bank tidak dapat masuk peringkat (K57).

### 3.8 Yang menunggu jawaban Anda sesudah aksi #19 tahap 1 — **SUDAH DIJAWAB SELURUHNYA 17 Okt 2026 ("sesuai rekomendasi")**

> **Keadaan: SUDAH DIJAWAB SELURUHNYA (17 Okt 2026, sesi 11c) — "sesuai rekomendasi".**
> **P34 → K62** (urutan tindakan tulis lanjutan: #19b impor → #19c cadangan + daftar → **#19d
> `ubah-stop` + keputusan right issue**), **P35 → K63** (layar 11.4 memperoleh pilihan **"Pakai
> ukuran patuh"**, dikerjakan bersama #19b), **P36 → K64** (jendela = **jalur harian**, baris
> perintah = jalur lengkap; **pilihan rencana & posisi dari daftar** wajib masuk jendela). Bentuk
> teknisnya **T71** (`docs/arsitektur.md`). Isi pertanyaannya dibiarkan apa adanya di bawah sebagai
> riwayat, dan **tidak satu pun dari ketiganya pernah memblokir pekerjaan**: #19b/#19c sudah berjalan
> menurut K59 c.

**P34 — sesudah #19b dan #19c, tindakan tulis mana yang masuk jendela lebih dulu?**
**→ DIJAWAB 17 Okt 2026: "sesuai rekomendasi" → K62** (ikuti K59 c apa adanya, lalu **#19d
`ubah-stop` + keputusan right issue**; `ubah-stop` tidak diselipkan sebelum impor).
K55 menyebut lima tindakan (catat transaksi, simpan rencana, catat jurnal, impor, cadangan) dan K59 c
mengurutkannya; **tiga tindakan tulis lain sudah ada di baris perintah dan tidak disebut di situ**:
`--ubah-stop` (stop trailing), `--putuskan-right-issue` (+ `--hak-right-issue`), dan
`--ekuitas-harian`. Di antara ketiganya, yang paling sering dituntut **oleh layar Anda sendiri**
adalah `ubah-stop`: dasbor memunculkan `stop_tertembus`, `tanpa_stop`, dan `pembatal_terpicu` sebagai
tindakan menunggu, tetapi menaikkan stop belum bisa dilakukan dari jendela.
Usulan: **ikuti K59 c apa adanya** — #19b impor → #19c cadangan + daftar, lalu **#19d = `ubah-stop` +
keputusan right issue**. Bukan menyelipkan `ubah-stop` sebelum impor, sebab impor adalah jalan masuk
data dan urutannya sudah dikunci, sementara stop masih bisa dicatat dari baris perintah tanpa
kehilangan apa pun (tidak ada yang tertahan).
Alternatif: **`ubah-stop` lebih dulu** karena frekuensinya harian sedangkan impor jarang — sah, tetapi
mengubah urutan yang sudah dikunci di K59 c.

**P35 — PRD 9.7 di jendela: pilihan "pakai ukuran yang patuh" hilang.**
**→ DIJAWAB 17 Okt 2026: "sesuai rekomendasi" → K63** (pilihan **Pakai ukuran patuh** ditambahkan di
layar 11.4, dikerjakan bersama #19b; ukuran patuh dihitung lebih dulu supaya konfirmasinya menampilkan
angka yang benar-benar ditulis).
PRD 9.7 menuntut rencana yang melanggar **disimpan setelah pengguna memilih** — "ukuran yang patuh,
atau menerima pelanggarannya secara tercatat" — dan baris perintah memang menyediakan keduanya
(`--pakai-ukuran-patuh` dan `--terima-pelanggaran`). Jendela sesi 11 baru menyediakan **satu**: dialog
konfirmasi menyebut pelanggarannya apa adanya dan menjawab "Tulis" berarti **menerimanya** (pilihan
itu tersimpan di `catatan` rencana). Artinya pengguna jendela yang ingin ukuran patuh harus pindah ke
baris perintah.
Usulan: tambahkan **pilihan "Pakai ukuran patuh"** di layar 11.4 (tombol di sebelah *Simpan rencana*,
memakai `risiko.pakai_ukuran` yang sudah ada), lalu dialog konfirmasi muncul dengan angka yang sudah
patuh; dikerjakan bersama #19b karena kecil.
Alternatif: biarkan seperti sekarang dan cukup sebutkan di layar bahwa ukuran patuh ada di baris
perintah — jujur, tetapi jendela tetap hanya menawarkan satu dari dua pilihan yang PRD 9.7 minta
dipilih pengguna.

**P36 — seberapa lengkap jendela dibanding baris perintah?**
**→ DIJAWAB 17 Okt 2026: "sesuai rekomendasi" → K64** (jendela = jalur harian; **pilihan rencana &
posisi dari daftar** wajib masuk, sisanya — `id posisi` eksplisit, pajak/biaya pengguna, broker,
ekspor, `--pulihkan` — tetap di baris perintah).
Formulir transaksi jendela belum memuat `id posisi` eksplisit, pajak yang dicatat pengguna, dan
pilihan broker; nomor rencana/posisi masih **diketik tangan**; ekspor dan `--pulihkan` belum ada.
K55 tidak pernah menetapkan seberapa jauh jendela harus mengejar baris perintah.
Usulan: jendela = **jalur harian**, baris perintah tetap **jalur lengkap**. Yang masuk jendela hanya
yang dipakai harian **dan** yang tidak pantas diketik tangan — terutama **pilihan rencana & posisi
dari daftar** (menggantikan mengetik `#1`), sebab salah mengetik nomor rencana menempelkan eksekusi
pada rencana yang salah dan itu tidak terlihat di layar mana pun. Yang **tetap** hanya di baris
perintah: `id posisi` eksplisit, pajak/biaya yang dicatat pengguna, pilihan broker, ekspor, dan
`--pulihkan`.
Alternatif: paritas penuh (setiap argumen baris perintah punya kotaknya) — lebih banyak kotak yang
jarang dipakai, dan `--pulihkan` tetap sebaiknya **tidak** ada di jendela karena ia menimpa basis
data (K59 e: pulihkan menunggu tahap tersendiri, dengan konfirmasi kedua yang menyebut folder
cadangannya).

**Dua hal yang bukan pertanyaan baru, tetapi menunggu Anda:** (a) mengirim draf laporan upstream
PySide6 ke Qt (`docs/riset-pyside6-gc-2026-10.md` bagian 7) — **lalu** sesi berikutnya menguji Python
3.13 menurut K60 b; (b) mengisi `rasio-bank.csv` dari publikasi resmi bank/OJK (lihat penutup 3.7).

### 3.9 Pembagian pekerjaan tiga butir "menunggu pengguna" — **SUDAH DIJAWAB SELURUHNYA 17 Okt 2026 → K66–K68**

> **Keadaan: SUDAH DIJAWAB (17 Okt 2026) — "sesuai rekomendasi" untuk ketiganya.**
> **P37 → K66** (laporan upstream **tetap dikirim pengguna**; berkas siap tempelnya
> `docs/laporan-pyside6-siap-kirim.md`), **P38 → K67** (uji Python 3.13 **dialihkan ke sesi agen**,
> dengan pemasangan interpreter menunggu persetujuan — laporan dependensinya sudah ditulis di
> `docs/riset-pyside6-gc-2026-10.md` bagian 8), **P39 → K68** (`rasio-bank.csv` boleh dikumpulkan
> sesi agen sampai batas kandidat + kutipan resmi; angka masuk basis data hanya sesudah pengguna
> menyatakan sah — dan lingkup pertamanya sudah diukur: **49 bank, 0 tertahan hanya oleh rasio**).
> Isi pertanyaannya dibiarkan apa adanya di bawah sebagai riwayat; **tidak satu pun pernah
> memblokir pekerjaan** — #19c/#19d berjalan tanpa jawaban itu.
>
> **Keadaan asal (sesi 13, sebelum dijawab):** pengguna bertanya apakah
> tiga butir yang selama ini hanya bisa dikerjakan manusia — **laporan upstream PySide6**, **uji
> Python 3.13**, dan **`rasio-bank.csv`** — bisa dialihkan ke sesi agen, dan meminta **dicatat dulu**
> sebelum dikerjakan ("catet dulu"). Karena itu sesi ini **tidak menyentuh kode**: yang berubah hanya
> `docs/keputusan.md` dan `docs/lanjutan.md`. Usulannya ada di **bagian 2 (U27–U29)**; di bawah ini
> pertanyaannya, jawaban yang saya sarankan, dan **apa yang menghalangi kalau bukan keputusan**.

**P37 — laporan cacat PySide6 ke Qt: siapa yang mengirimnya?**
Bisa dikerjakan sesi agen atau tetap Anda?
**→ Usulan: tetap Anda yang mengirim; sesi agen hanya merapikan berkas siap-tempel.**
Yang menghalangi bukan kemampuan teknis: laporan itu menyatakan pengalaman **Anda** (kapan prosesnya
mati, apa yang terlihat) dan akan dikirim atas nama akun Anda ke pelacak pihak ketiga. K60 a sudah
memisahkan "draf siap" dari "dikirim" — dan itulah gerbang K60 b. Yang **bisa** saya kerjakan tanpa
keputusan baru: menyusun ulang `docs/riset-pyside6-gc-2026-10.md` bagian 7 menjadi satu berkas teks
siap tempel (lingkungan, langkah repro, tabel angka, judul yang disarankan), supaya mengirimnya tidak
menuntut penyuntingan lagi.

**P38 — uji Python 3.13 (K60 b): dialihkan ke sesi agen?**
**→ Usulan: ya, dialihkan — dengan satu syarat: keputusan dependensi lebih dulu.**
Saya bisa memasang interpreter Python 3.13 di **lingkungan terpisah** (tanpa menyentuh `.venv` repo),
memasang PySide6 6.12.0 di sana, menjalankan `tests/test_ui_jendela.py` 12×, dan mencatat hasilnya di
`docs/riset-pyside6-gc-2026-10.md` (12 jalan tanpa proses yang mati = pin versi Python adalah
jawabannya). Yang **tidak** saya lakukan sendiri: memasang interpreter di mesin Anda tanpa
melaporkannya lebih dulu — versi, sumber unduhan, ukuran, dan cara mencabutnya dilaporkan sebagai
keputusan dependensi, sesuai K60 b. Urutannya tetap sesudah P37 beres.

**P39 — `rasio-bank.csv`: boleh sesi agen mengumpulkan angkanya?**
**→ Usulan: boleh sampai batas kandidat + kutipan; yang masuk basis data tetap setelah Anda verifikasi.**
Bentuknya: saya ambil **Laporan Eksposur Risiko & Permodalan** tiap bank kandidat dari situs resminya
(jalur terbukti tanpa dependensi baru — §2.1a: `urllib` cukup, BCA dan Mandiri sudah pernah dicoba),
lalu menyusun tabel kandidat NPL/CAR/BOPO/NIM **beserta tautan + tanggal publikasinya** di
`.uji-data/`, untuk Anda periksa. Angkanya baru masuk `rasio-bank.csv` (dan diimpor) sesudah Anda
menyatakan sah — K24 (jalur otomatis PDF tidak dibangun) dan aturan keras 1 tidak berubah. Yang
menentukan bukan siapa yang mengunduh PDF-nya, melainkan siapa yang menyatakan angkanya bersumber
resmi — dan itu tetap Anda.

### 3.10 Sumber harga kedua dan syarat penggunaan situs IDX (29 Okt 2026, sesi 57)

**Temuan:** ringkasan perdagangan harian resmi IDX
(`https://www.idx.id/primary/TradingSummary/GetStockSummary?date=YYYYMMDD`) **dapat diambil** lewat
domain `www.idx.id` dengan UA jujur yang sama dengan `notasi.py` (percobaan sesi 53 memakai
`idx.co.id` → 403). Isinya per emiten: previous, open, high, low, close, volume, nilai, frekuensi,
saham tercatat; juga tanggal lama (Feb 2023). Uji baca-saja 28 Okt 2026 atas basis data kerja:
**916/916 penutupan sama persis** dengan yfinance, 20 emiten ADTV teratas selisih 0%. Tanggal lama
memuat `OpenPrice` 0 (= tidak dilaporkan, bukan nol); FISH 1 Sep 2025 tanpa transaksi (H/L/volume 0).
Ia juga memuat bar keenam ticker yang menunggu OHLCV primer (BNBR, COCO, FISH, PYFA, SCCO, TMAS).

**Penghalang:** [Syarat Penggunaan IDX](https://www.idx.id/id/syarat-penggunaan/) (diakses 29 Okt
2026) membolehkan penggunaan bukan komersial dengan menyebut sumber dan tanggal akses, tetapi
menyatakan pengguna "tidak diperkenankan menggunakan metode web scrapping/crawling". Pemanggilan
endpoint itu dari kode adalah pengambilan otomatis. Sesi 57 sudah melakukan ±15 permintaan uji
(28 Okt 2026 + 11 tanggal keenam ticker) sebelum membaca klausul ini, lalu **berhenti**; tidak ada
yang diimpor. Klausul yang sama **juga mengenai `notasi.py`** (halaman notasi + API suspensi/UMA),
yang sejak K94 dijalankan otomatis oleh tombol "Perbarui data" bila daftarnya berumur > 7 hari.

**P40 — sumber harga kedua (PRD 7.3) dipilih yang mana?**
**→ Usulan: Ringkasan Saham IDX yang Anda unduh sendiri lewat tombol "Unduh" di situs (± 1 menit,
sekali seminggu), lalu `--impor` dengan label sumber + tanggal akses.** Resmi, independen dari
Yahoo, dan sesuai syarat penggunaan (penggunaan pribadi bukan komersial, tanpa scraping). Butuh
pembaca berkas unduhan itu di `berkas.py` (bentuk berkasnya belum diperiksa). Alternatif: layanan data
berlisensi BEI (berbayar), atau meminta izin tertulis BEI untuk pengambilan otomatis. Situs mirror/API
komunitas tetap ditolak (§4 `docs/riset-sumber-data-2026-10.md`).

**P41 — pengambilan otomatis notasi/suspensi/UMA (`notasi.py`, K94) dihentikan?**
**→ Usulan: ya — tombol berhenti mengambil sendiri; jadwal tetap menandai "jatuh tempo" dan
menyebut langkah unduh manual (halaman notasi khusus + pengumuman suspensi/UMA), lalu `--impor`.**
Atau pertahankan sambil meminta izin tertulis BEI. Sampai dijawab, tidak ada pengambilan IDX baru
yang dijalankan agen; pembaruan terjadwal sore 29 Okt tidak mengambil notasi (daftar per 27 Okt belum
jatuh tempo).

### 3.11 Harga resmi IDX sebagai sumber utama ke depan (29 Okt 2026, sesi 58)

Pengguna bertanya apakah harga untuk pemakaian pribadi bisa diambil dari sumber resmi, bukan
yfinance (K7). Ringkasan Saham IDX sudah resmi, sudah terbaca (T93), dan 916/916 penutupan 28 Okt
sama dengan yfinance. Penghalangnya bukan izin, melainkan **riwayat** dan **K14**.

**Keadaan kode yang menentukan (diperiksa 29 Okt 2026):**

1. `potret.sumber_utama` memilih **satu label untuk seluruh snapshot**, yaitu label dengan bar
   terbanyak (K14). Label IDX (`unggahan_idx.SUMBER_IDX`) hanya punya satu bar per emiten per
   berkas, jadi tidak akan pernah menjadi sumber utama. Memaksanya dengan `--sumber` membuat deret
   hanya sepanjang berkas yang diunduh, dan metrik berjendela panjang berstatus "tidak dihitung".
2. **Jebakan penyambungan:** `penyesuaian.py` melewati **semua** split sesudah tanggal bar untuk
   baris berpenanda `split` (`mejasaham/penyesuaian.py`, sekitar baris 150), tanpa melihat kapan baris itu diunduh. Bila yfinance
   berhenti diperbarui, split yang terjadi **sesudah** unduhan terakhir tidak pernah diterapkan ke
   riwayat yfinance. Deretnya patah di tanggal split tanpa satu pun tanda. Selama yfinance terus
   diunduh ulang, cacat ini tertutup karena revisi terbaru sudah disesuaikan oleh sumbernya.
3. Unggahan IDX hanya diterima bila tanggal berkas sama dengan tanggal data snapshot terakhir
   (T93). Hari yang terlewat tidak bisa diisi belakangan lewat tombol.
4. Aksi korporasi (split) sekarang datang dari yfinance (`actions=True`). Kalau yfinance tidak
   dipakai lagi, split harus masuk lewat `--impor` dari pengumuman resmi.

**P42 — harga IDX dijadikan sumber utama mulai suatu tanggal, dengan riwayat yfinance sebelumnya?**
**→ DIJAWAB 29 Okt 2026 (sesi 58): “Setuju (a)–(f)” → K97.**
**→ Usulan: ya, sebagai "deret sambungan" bertanggal, dengan enam syarat:**

- **(a) Satu tanggal sambung untuk seluruh emiten**, disimpan sebagai konfigurasi bertanggal
  (`berlaku_sejak` + `sumber`), bukan konstanta. Bar sebelum tanggal itu dari yfinance, sejak
  tanggal itu dari IDX. Ini **tidak** melanggar alasan K14 menolak label per emiten, karena dua
  emiten di peringkat yang sama tetap dihitung dari sumber yang sama pada tanggal yang sama.
- **(b) Gerbang sambungan:** pada hari tumpang-tindih (minimal 5 hari bursa sebelum tanggal sambung
  dengan kedua sumber), penutupan setiap emiten likuid harus sama. Bila ada selisih, emiten itu
  berstatus "tidak dihitung" beserta alasannya, bukan disambung diam-diam.
- **(c) Penanda `split` diberi batas waktu:** baris sumber yang sudah disesuaikan dianggap
  disesuaikan **hanya** untuk split yang diketahui sampai `diketahui_pada` baris itu. Split sesudah
  itu tetap diterapkan saat dibaca. Ini menutup jebakan nomor 2 dan berlaku juga untuk keadaan
  sekarang. Perlu diuji dulu atas data nyata (split BBCA Okt 2021) sebelum dikunci.
- **(d) Hari bursa tanpa berkas IDX = bolong yang tampil**, bukan diisi dari yfinance. Snapshot
  menyebut jumlah hari bolong sejak tanggal sambung, dan peringkat berstatus PERINGKAT SEMENTARA
  selama ada bolong di jendela metrik. Unggahan untuk tanggal yang terlewat diizinkan (melonggarkan
  syarat T93), dengan `diketahui_pada` = waktu unggah sehingga point-in-time tetap jujur.
- **(e) Label tetap per bar:** laporan snapshot menyebut "IDX sejak <tanggal>, yfinance (tidak
  resmi) sebelumnya" beserta jumlah bar masing-masing. Peringatan "tidak resmi" (T19) tetap
  menempel di ekspor selama ada bar yfinance di jendela metrik.
- **(f) Cek sumber kedua (PRD 7.3) dibalik:** sesudah sambung, yfinance boleh tetap diambil
  seminggu sekali sebagai pembanding. Kalau tidak diambil lagi, PRD 7.3 butuh pembanding lain
  (pertanyaan terpisah).

**Yang diterima bila disetujui:** pengguna mengunduh dan mengunggah satu berkas **setiap hari
bursa** (± 1 menit, ± 245 kali setahun). Riwayat sebelum tanggal sambung tetap tidak resmi sampai
keluar dari jendela metrik terpanjang. Split harus diimpor manual dari pengumuman resmi.

**Alternatif:**

- **Alt-1:** IDX hanya untuk **harga terakhir** yang dipakai `risiko.py`/`posisi.py` (masuk, stop,
  ukuran posisi), sedangkan metrik riwayat tetap dari yfinance. Lebih kecil, tetapi skor tetap dari
  sumber tidak resmi.
- **Alt-2:** Layanan data berlisensi BEI (berbayar) atau izin tertulis BEI untuk pengambilan
  otomatis. Hanya jalan ini yang otomatis dan resmi.
- **Alt-3:** tetap K7 + K95 seperti sekarang.

**Urutan kerja bila (a)–(f) disetujui:** (1) uji dan perbaiki syarat (c) lebih dulu, karena ia
cacat laten yang berdiri sendiri; (2) konfigurasi tanggal sambung + pembacaan deret sambungan di
`potret.py` (satu fungsi, `riwayat_sumber`/`sumber_utama`); (3) gerbang (b) dan laporan bolong (d);
(4) unggahan tanggal lampau dan unggah beberapa berkas sekaligus. Setiap langkah berhenti untuk
ditinjau (K4).

**Langkah 1 selesai (29 Okt 2026, sesi 58):** `HargaHarian.diketahui_pada` diisi `potret` saat
membaca, dan `penyesuaian.py` melewati split hanya bila tanggalnya ≤ tanggal baris itu diketahui
(split pada hari unduhan dianggap sudah diterapkan, karena Yahoo melaporkannya dalam unduhan yang
sama). Baris berpenanda tanpa `diketahui_pada` yang punya split sesudahnya = "tidak dihitung"
dengan alasannya. **Cacat ini ternyata sudah aktif di data kerja:** bar PBSA sebelum 28 Okt 2021
berada di luar jendela unduh 5 tahun, jadi tidak diunduh ulang sesudah split 1:2 tanggal 14 Okt
2026. Deretnya melompat 337 → 175 di batas itu, dan sekarang sambung (168,5 → 175). Perbandingan
lama-baru atas salinan snapshot 17: 916 emiten, 79 punya split, **1 deret berubah (PBSA)**, 0
perubahan status "siap". Suite 963 lulus.

**Langkah 2 selesai (29 Okt 2026, sesi 58):** migrasi 017 `sambungan_harga` + berkas impor
`sambungan-harga.csv`; satu pemilik `potret.PilihanHarga`/`potret.harga_dipakai` yang dipakai
**seluruh** pembaca harga — perhitungan (`potret.muat`), laporan mutu, peringkat ADTV20 untuk
ambang PRD 9.3, harga terakhir posisi, V4 jurnal, dasbor, ekspor, cek sumber kedua. Cakupannya
lebih luas dari yang tertulis di urutan kerja di atas ("satu fungsi di `potret.py`"): delapan
modul menyaring `sumber = ?` sendiri, dan membiarkan satu saja tertinggal membuat skor dihitung
dari IDX sementara stop membaca yfinance. Tiga hal yang diputuskan saat mengerjakan (teknis,
tercatat di sini, bisa ditinjau):

- **Kunci revisi per `berlaku_sejak`**, yang berlaku = tanggal aktif terbesar; mencabut =
  `aktif = tidak` untuk tanggal itu. Aturan "pernyataan terakhir menang" ditolak: mengimpor ulang
  pernyataan lama dilewati sebagai "sudah ada dan sama" sehingga diam-diam tidak berlaku lagi.
- **Tanggal sambung tidak menunggu `tanggal_data`**: bar label resmi sebelum tanggal sambung dan
  bar label riwayat sesudahnya tidak pernah dibaca; snapshot sebelum pernyataan tetap satu label.
- **Cek sumber kedua menerima deret lengkap** (peringkat ADTV20 dari deret sambungan), lalu memilih
  label hari datanya; pembanding yang sama dengan sumber utama ditolak ("dirinya sendiri"), dan
  unggahan IDX di dasbor sesudah tanggal sambung tidak lagi memaksa IDX sebagai pembanding.

**Bukti atas salinan data kerja** (`.tmp/uji-p42c`, migrasi 16 → 17, tanggal sambung uji 28 Okt
2026 — satu-satunya hari berberkas IDX): `--saring` sebelum/sesudah **identik** (likuid 181, lolos
5, AUTO 55,6 · PTBA 54,4 · ERAA 54,1 · LSIP 53,5 · DSNG 52,0, breadth 15,5%); label tampil
"IDX … sejak 2026-10-28; sebelumnya yfinance …" dengan jumlah bar per bagian; laporan mutu
menyebut riwayat sebelum 28 Okt tidak resmi; `--cek-sumber-kedua`: utama IDX, pembanding
yfinance, **20 diperiksa · 0 ditandai**. Percobaan pertama menemukan cacat (pengatur meneruskan
satu label sehingga peringkat ADTV20 hanya punya 1 hari) — diperbaiki dan dijaga uji. Suite 981
lulus. Data kerja **tidak** disentuh: sambungan belum dinyatakan di sana.

**Langkah 3 selesai (29 Okt 2026, sesi 58):** `potret.periksa_sambungan` (satu pemilik, dipakai
`potret.muat` dan `mutu.periksa`) menghasilkan `KeadaanSambungan`; `metrik.seri_harga` — satu
pintu seluruh metrik harga — mengembalikan "tidak dihitung" dengan alasan gerbang. Keputusan
teknis yang diambil saat mengerjakan (bisa ditinjau):

- **Yang diperiksa gerbang = setiap emiten yang benar-benar disambung** (punya bar label riwayat
  sebelum tanggal sambung dan bar label resmi sejak itu), bukan hanya yang likuid: likuiditas
  dihitung dari deret sambungan itu sendiri, jadi menyaring lebih dulu akan berputar.
- **Tumpang-tindih = seluruh hari sebelum tanggal sambung yang punya penutupan dari kedua label;**
  minimal 5 (`potret.HARI_TUMPANG_TINDIH_MINIMUM`), dan **sama persis** (penutupan mentah). Satu
  hari berbeda = ditolak; split di dalam hari tumpang-tindih ikut membuat ditolak (berisik, bukan
  menebak basis). Jalan keluarnya: periksa sumber, atau nyatakan tanggal sambung lain.
- **Laporan mutu:** penutupan berbeda = `sambungan_beda_harga` (tak wajar, per emiten, dikeluarkan
  dari peringkat); tumpang-tindih kurang = **satu** catatan `gerbang_sambungan` (bukti belum cukup,
  bukan cacat data, dan biasanya mengenai semua emiten sekaligus).
- **Hari bolong = hari bursa menurut kalender, sejak tanggal sambung, tanpa satu bar label resmi
  pun** (berkas hari itu tidak diunggah). Bolong per emiten (suspensi) bukan urusan ini. Jendela =
  252 hari bursa terakhir (`potret.JENDELA_BOLONG_HARI_BURSA`, dijaga uji ≥ jendela metrik
  terpanjang). Kalender yang belum memuat rentangnya = **juga** peringkat sementara.
- **PERINGKAT SEMENTARA** kini punya dua sebab: notasi belum terverifikasi (PRD 7.3) atau hari
  bolong (K97 d) — `LaporanSaring.peringkat_sementara` + `sebab_sementara()`, dipakai `--saring`
  dan Screener web.

**Bukti atas salinan** `.tmp/uji-p42c` (snapshot 18, sambung uji 28 Okt — satu-satunya hari
berberkas IDX): gerbang **916 disambung · 0 lolos · 916 ditolak** ("hanya 0 hari tumpang-tindih
… minimal 5"), kalender memuat rentangnya, 0 hari bolong; `--saring` → likuid 0, tidak ada
peringkat, peringatan gerbang tampil. Ini perilaku yang diminta (b): tanggal sambung 28 Okt belum
punya bukti. **Akibat bagi pemakaian nyata:** sebelum menyatakan tanggal sambung, pengguna harus
mengunggah berkas IDX untuk ≥ 5 hari bursa **sebelum** tanggal itu — dengan T93 sekarang artinya
5 hari berturut-turut mengunggah tepat hari itu, lalu menyatakan tanggal sambung hari bursa
berikutnya (langkah 4 akan mengizinkan unggah tanggal lampau). Suite 991 lulus.
**Batas yang diketahui:** dasbor ("Kandidat teratas dari skor tersimpan") belum menyebut peringkat
sementara — sama seperti untuk notasi sebelumnya; laporan mutu sesudah `--refresh` masih memakai
label hasil pengambilan, bukan deret sambungan (sisa langkah 2, `pengatur.py` sekitar baris 261).

**Langkah 4 selesai (29 Okt 2026, sesi 58):** isian unggah di Impor & cadangan menerima beberapa
berkas sekaligus; bagian **"Belum diimpor"** (`unggahan_idx.antrean_impor`) mendaftar unggahan yang
tanggalnya belum punya bar IDX di basis data, dan satu tombol "Impor N berkas" mengimpor semuanya
lewat **satu** konfirmasi dan **satu** snapshot (`tulis.permintaan_impor_ringkasan_idx`). Syarat T93
"tanggal berkas = tanggal snapshot" dilonggarkan menjadi **≤ tanggal snapshot** (K97 d). Keputusan
teknis yang diambil (bisa ditinjau):

- **Tanggal data snapshot tidak mundur:** impor yang hanya berisi hari lampau menerbitkan snapshot
  bertanggal data snapshot terakhir (`pengatur.jalankan_impor(tanggal_data_minimum=)`). Snapshot
  adalah batas waktu data (A4); yang sudah diketahui tidak menjadi tidak diketahui.
- **`diketahui_pada` = waktu impor** (bukan waktu unggah seperti tertulis di syarat d). Waktu impor
  ≥ waktu unggah, jadi lebih ketat: snapshot yang dibuat di antara unggah dan impor tidak
  melihatnya, dan memang belum ada di basis data saat itu.
- **Berkas bertanggal sesudah snapshot terakhir tetap ditolak** dan tampil sebagai "Menunggu"
  ("Perbarui data" dulu). Satu berkas seperti itu menolak seluruh pilihan, bukan diam-diam dilewati.
- **"Sudah diimpor" dinilai per tanggal** (ada bar berlabel IDX pada tanggal itu). Dua unggahan
  bertanggal sama: yang terbaru dipakai, yang lama disebut "tidak dipakai"; memilih keduanya dalam
  satu impor ditolak.
- **Cek sumber kedua** hanya dijalankan bila salah satu berkas bertanggal snapshot; selain itu
  konfirmasi dan hasilnya menyebut "TIDAK dijalankan" beserta sebabnya.
- **Tanggal tiap berkas di-cache** di `unduhan-idx/ringkasan-saham/tanggal-berkas.csv` (SHA-256 →
  tanggal; turunan, boleh dihapus): membaca satu berkas nyata ±0,36 dtk, dan antrean dibuka di
  setiap kunjungan halaman.
- Batas satu kiriman formulir 64 MB (`BATAS_BAIT_SEKALIGUS`; berkas nyata ±0,85 MB).

**Perbaikan kecepatan gerbang langkah 3** (ditemukan saat mencoba): mencari bar label resmi sebelum
tanggal sambung memindai seluruh riwayat (tidak ada indeks pada `sumber`) — **17 dtk** atas salinan
data kerja, dan berjalan dua kali per impor/saringan. Hari tumpang-tindih kini dicari dalam **60 hari
kalender** sebelum tanggal sambung (`potret.JENDELA_TUMPANG_TINDIH_HARI`): **0,8 dtk**. Akibatnya,
bukti tumpang-tindih harus dari hari-hari dekat tanggal sambung — memang itu yang relevan.

**Dicoba di peramban** atas salinan buangan `.tmp/uji-langkah4` (dari `.tmp/uji-p42c`, sudah
dihapus) dengan dua berkas **sintetis** 26 & 27 Okt (2 emiten, penutupan dari bar yfinance
salinan itu; satu-satunya berkas IDX nyata, 28 Okt, sudah diimpor): satu kiriman → "2 berkas siap
diimpor" → konfirmasi menyebut kedua tanggal, peran "PEMBANDING — juga bukti tumpang-tindih", dan
cek sumber kedua TIDAK dijalankan → snapshot 19 **tanggal data tetap 28 Okt**, 4 baris baru,
antrean kosong. Data kerja tidak disentuh.

**Sisa 1 selesai (29 Okt 2026, sesi 58) — dasbor menyebut peringkat sementara:** halaman depan
web dan `--dasbor` menyebut skor tersimpan "Peringkat sementara — belum boleh disebut kandidat"
beserta sebabnya, dengan kalimat yang sama dengan `--saring`/Screener
(`saring.sebab_peringkat_sementara`; `saring.notasi_terverifikasi` pindah dari `pengatur`).
Statusnya **dihitung ulang** as-of batas snapshot (`potret.notasi_as_of` +
`potret.periksa_sambungan`, hanya bila ada skor), bukan disimpan bersama skor: keduanya milik
snapshot, jadi jawabannya sama dengan saat saringan berjalan, tanpa migrasi. Batas yang diterima:
seperti konteks pasar, yang dinilai deret bawaan — skor dari `--sumber` lain tidak dibedakan
(tabel `skor` tidak mencatat labelnya). Biaya: `--dasbor` atas salinan data kerja 7,3 dtk.

**Sisa 2 & 3 selesai (29 Okt 2026, sesi 58):**

- **Laporan mutu sesudah `--refresh`** kini memeriksa deret yang dipakai berhitung
  (`potret.harga_dipakai(batas=diketahui_pada snapshot)`), sama dengan jalur impor — bukan label
  pengambilan. Sebelumnya, sesudah tanggal sambung ia memeriksa bar yfinance yang tidak dipakai dan
  menyebut seluruh snapshot "tidak resmi". Tanpa sambungan hasilnya sama (label terbanyak = label
  pengambilan).
- **Pengingat unggah harian:** sesudah tanggal sambung, butir jadwal "Harga harian & indeks"
  (dasbor web, `--dasbor`, sesudah `--refresh`) baru **terbaru** bila snapshot dari hari bursa
  terakhir **dan** tidak ada hari bolong di jendela metrik; bila ada, **jatuh tempo** dengan
  tanggal yang bolong dan tindakan unggah Ringkasan Saham IDX. Kalender yang belum memuat rentangnya
  = **tidak dinilai**. Hari yang dihitung = `potret.periksa_sambungan`, pemilik yang sama dengan
  sebab PERINGKAT SEMENTARA, jadi jadwal dan saringan tidak saling membantah. Butir cek sumber
  kedua tidak diubah. Bila snapshotnya sendiri belum hari bursa terakhir, tindakannya tetap
  "Perbarui data" dulu; hari bolong baru disebut sesudahnya.

**Sambungan dinyatakan di data kerja (29 Okt 2026, sesi 58):** pengguna mengunggah Ringkasan Saham
21, 22, 23, 26, 27 Okt (snapshot 18–19; 28 Okt sudah ada) dan memilih tanggal sambung **28 Okt**.
Cadangan `.uji-data/mejasaham-cadangan/20261029T061402921884+0700`, lalu `--impor
.uji-data/sambungan-k97` → **snapshot 20**. Gerbang: 916 disambung, **915 lolos**, 1 ditolak —
**FASW** (penutupan IDX 5.275 vs yfinance 5.312 di kelima hari tumpang-tindih; metrik harganya
"tidak dihitung", belum diselidiki sebabnya). `--saring`: **"Kandidat teratas"** (bukan lagi
peringkat sementara), likuid 181 · lolos 5 (AUTO 55,6 · PTBA 54,4 · ERAA 54,1 · LSIP 53,5 · DSNG
52,0), breadth 15,5% RISK-OFF. Mulai 29 Okt setiap hari bursa butuh berkas IDX; bila tidak,
jadwal menyebutnya jatuh tempo dan saringan kembali berbunyi peringkat sementara.

**FASW diselidiki (29 Okt 2026, sesi 58, baca-saja):** penolakan gerbang **benar, bukan cacat**.
FASW disuspensi sejak Sesi I 31 Jan 2025 (Peng-S-00003/BEI.PLP/01-2025, dipertahankan sampai
Peng-S-00003/BEI.PLP/01-2026; sudah tercatat di `notasi_khusus`). Volume > 0 terakhir di basis data
30 Jan 2025. Berkas IDX 21–28 Okt: Open/High/Low 0, Volume 0, Penutupan = Sebelumnya = 5.275.
Deret yfinance untuk hari tanpa transaksi berisi isian datar yang bergeser sendiri (5.450 →
5.276,92 → 5.312,50 sejak 11 Jun 2025), jadi tidak pernah sama dengan IDX. Menyambungnya akan
menciptakan lompatan 0,7% yang tidak ada di pasar. Emiten ini juga sudah gugur di saringan likuiditas.
Tidak ada perubahan kode atau data. Bila suspensinya dicabut, gerbang tetap menolak FASW karena
syaratnya ≥ 5 hari tumpang-tindih **sebelum** tanggal sambung. Itu dibahas nanti bila terjadi.

### 3.12 Unggah Notasi Khusus IDX (29 Okt 2026, sesi 58)

Lanjutan K96: notasi tidak lagi diambil aplikasi, jadi daftarnya diunduh pengguna. Contoh nyata
`Notasi Khusus-20261027.xlsx` (diunduh pengguna 29 Okt 2026; halaman IDX menyebut "Data per tanggal
27 Okt 2026 Pkl. 15:00 WIB"): XLSX SheetJS satu lembar, kolom `No`, `Kode` (`CBMF.LY`, `GOTOM.N`),
`Nama`, `Notasi` (`L,Y`), `Keterangan Notasi`, `Remarks`; 122 baris. **Isinya tidak memuat
tanggal** — tanggal data dibaca dari nama berkas (`Notasi Khusus-YYYYMMDD.xlsx`, akhiran peramban
" (1)" diterima); nama lain ditolak.

**Yang dibangun:** `notasi.baca_unduhan` (baris **identik** dengan `notasi.urai` halaman lama —
terbukti atas data kerja: 122/122 baris per 27 Okt sama persis, 67 papan pemantauan khusus);
`notasi.simpan_unduhan` (berkas mentah di `<folder data>/unduhan-idx/notasi-khusus/`);
`layar.tulis.permintaan_impor_notasi_idx` (gabung dengan `konfigurasi/notasi-khusus.csv` memakai
`notasi.tulis_berkas`, baca sebelum konfirmasi, impor biasa, lalu ganti berkas konfigurasi hanya bila
belum berubah sejak konfirmasi); di web: **Impor & cadangan → "Notasi Khusus IDX" → Unggah dan baca →
konfirmasi → Tulis**. Daftar yang lebih lama dari yang tersimpan ditolak. Suspensi dan UMA **tidak**
ikut diperbarui.

**Dua cacat ditemukan dan diperbaiki:**
- `notasi.tulis_berkas` menurunkan jenis yang "diperbarui" dari baris yang ada. Daftar baru tanpa satu
  pun emiten ber-X membuat baris papan pemantauan lama **tidak pernah ditutup**. Kini daftar notasi
  menyatakan cakupannya (`HasilNotasi.jenis_dicakup` = kedua jenis). Uji regresinya gagal di kode lama.
- Label `sumber` impor diturunkan dari jalur folder. Folder per unggahan membuat **seluruh** baris
  `notasi-khusus.csv` (termasuk suspensi) tersimpan ulang sebagai revisi setiap minggu walau isinya
  sama — terukur atas salinan data kerja: **2.603 baris**. Kini folder impor notasi tetap
  (`unduhan-idx/notasi-khusus/impor/`) dan isi gabungannya dibekukan saat konfirmasi disusun.
  **Akibat yang tersisa:** unggahan **pertama** di data kerja tetap menulis 2.603 revisi sekali, karena
  labelnya berbeda dari impor folder konfigurasi sebelumnya (sejarah data kerja sudah memuat lonjakan
  serupa: jalur relatif → absolut, 29 Okt 02:24). Unggahan berikutnya hanya menulis yang berubah —
  terbukti atas salinan: unggahan kedua **0 baru, 2.603 sudah ada dan sama**.

**P43 — suspensi & UMA sesudah K96 (DIJAWAB 29 Okt 2026 → K98, usulan dipakai apa adanya):** jadwal menilai butir "Notasi, suspensi & UMA"
dari tanggal daftar notasi saja. Setelah daftar notasi diunggah, butir itu tampil **terbaru** walau
suspensi/UMA tidak diperbarui sejak 27 Okt (belum ada jalur unggahnya). **→ Usulan:** pisahkan
menjadi dua butir; suspensi/UMA berstatus "tidak dinilai" dengan tindakan unduh manual dari halaman
pengumuman IDX, sampai pengguna memberi contoh berkas unduhan suspensi/UMA untuk dibuatkan pembacanya
(bentuknya tidak ditebak, K95).

**Sesi 59, catatan kepala `notasi-khusus.csv` terbawa per jenis:** `notasi.tulis_berkas` menulis
ulang kepala komentar tiap kali, sehingga unggahan Notasi Khusus (sesi 58) membuang dua catatan asal
suspensi (55 multi-kode terekonsiliasi, 41 pembukaan tanpa pasangan). Kini catatan ditulis
`# CATATAN [jenis, …]: …` dengan jenis yang diperbarui penulisan itu; penulisan berikutnya membawa
catatan yang jenisnya tidak ia perbarui dan mengganti yang jenisnya ia perbarui. Catatan "Notasi
khusus dinyatakan sumber per …" pindah ke penulisan daftar notasi di `ambil_ke_berkas` agar
bertanda jenis notasi. Catatan lama tanpa tanda tidak dibawa (jenisnya tidak bisa dipastikan) —
sama dengan perilaku lama. Kedua catatan dipulihkan ke kepala `notasi-khusus.csv` data kerja dari
cadangan 20261029T064141675578+0700, bertanda `[suspensi]` (disetujui pengguna; hanya baris
komentar, baris data identik, tanpa impor).
Uji: `tests/test_notasi_idx.py::test_catatan_jenis_yang_tidak_diperbarui_terbawa_ke_kepala_berkas`.

### 3.13 Unggah PDF pengumuman suspensi & UMA IDX (29 Okt 2026, sesi 61 → K99)

Lanjutan K98. Pengguna mengunduh tiga PDF dari situs IDX: `20261028-UMA_COIN.pdf`,
`20261028-UMA_FILM.pdf`, dan `20261028-WAS_Suspensi_PTSP.pdf` (dibuat Microsoft Word 365, dua
halaman: Inggris lalu Indonesia). Isinya **satu pengumuman satu emiten**: judul, nomor
(`Peng-UMA-00352/BEI.WAS/10-2026`, `Peng-SPT-00222/BEI.WAS/10-2026`), nama + kode emiten dalam
kurung, tanggal tanda tangan (`28 Oktober 2026`), dan untuk suspensi kalimat "penghentian sementara
perdagangan saham … pada tanggal 29 Oktober 2026". Teksnya terbaca dengan `kalender.potongan_teks`
(spasi kadang menyelip di dalam token: `Peng-UMA-00 352 /BEI.WAS/ 10-2026`, `( FILM )`).

**Batas yang disengaja (K99):** pembukaan kembali (UPT), pengumuman multi-kode, dan bentuk kalimat
lain ditolak dengan sebabnya sampai ada contoh nyata — bentuknya tidak ditebak (K95). Akibatnya
**suspensi dari PDF tetap terbuka** (tanpa `tanggal_selesai`) sampai pembaca UPT dibuat; suspensi
cooling-down biasanya hanya sehari.

**Yang dibangun:** `mejasaham/pengumuman_idx.py` (`baca`, `pilah`, `simpan_unduhan`; mentah di
`<folder data>/unduhan-idx/pengumuman/`), `notasi.HasilNotasi.hanya_menambah`,
`layar.tulis.permintaan_impor_pengumuman_idx` (gabungan memakai folder impor tetap yang **sama** dengan
unggahan Notasi Khusus, supaya label sumber tidak berganti — lihat 3.12), dan di web **Impor &
cadangan → "Pengumuman suspensi & UMA IDX (PDF)"** (beberapa PDF sekaligus → konfirmasi → Tulis). Jadwal
"Suspensi & UMA" tetap **tidak dinilai**, tindakannya kini menyebut unggahan PDF. Pengumuman yang sudah
tercatat (dari API lama bertanggal pengumuman, atau unggahan sebelumnya) dihitung "sudah tercatat",
tidak dicatat dua kali. Rincian teknis: `docs/arsitektur.md` T94.

**Bukti (29 Okt 2026):** ketiga PDF nyata terbaca: COIN & FILM UMA 28 Okt → 27 Nov, PTSP suspensi
mulai 29 Okt (diumumkan 28 Okt). Atas salinan data kerja `.tmp/uji-pengumuman`: tepat 3 baris baru, 0
baris lama berubah, kedua catatan `[suspensi]` di kepala CSV terbawa, `integrity_check` ok, 50 dtk.
Uji: `tests/test_pengumuman_idx.py` (15), +2 `tests/test_web.py`; uji hanya-menambah terbukti gagal
bila `hanya_menambah` dimatikan.

**Diimpor ke data kerja (29 Okt 2026, atas permintaan pengguna):** sesudah cadangan
20261029T115945518371+0700 → snapshot 22, 3 revisi, label sumber sama dengan impor Notasi Khusus
sebelumnya (2.603 baris lain "sudah ada dan sama"), 0 baris lama berubah, `integrity_check` ok.

---

### 3.14 Pembaca PDF pembukaan suspensi (UPT) IDX (29 Okt 2026, sesi 61 → K100)

**Contoh:** pengguna tidak menaruh PDF UPT baru di Downloads; yang dipakai adalah 18 PDF UPT asli IDX
(FLMC, GPSO, MDIA, NIRO, OCAP, WOWS; 2024–2026) yang sudah diunduh pada riset suspensi Okt 2026
(`.uji-data/riset-idx/riwayat-api-pdf/`, tidak di-commit). Bentuknya seragam: "Menunjuk Pengumuman Bursa
Peng-SPT-… tanggal … perihal Penghentian Sementara Perdagangan (Suspensi) Saham PT … (KODE), maka … suspensi
atas perdagangan saham … di Pasar Reguler dan Pasar Tunai dibuka kembali mulai sesi I tanggal 25 Juni 2026."
Varian yang terlihat: "Sesi I Periodic Call Auction", dan tanpa sesi ("dibuka kembali mulai tanggal …").

**Penyebab "belum terbaca":** isi UPT ditulis dengan font Type0 `/Identity-H` (string heksa); pengurai
lama menghitungnya sebagai glif tak terbaca, sehingga hanya judul, nomor, dan tanggal tanda tangan yang
terlihat. `kalender.potongan_teks(terjemahkan_font=True)` kini membaca objek PDF (termasuk `/ObjStm` dan
pembaruan bertahap), kamus `/Font`, dan peta `bfchar`/`bfrange`. Nama font yang menunjuk dua peta berbeda
ditolak. Jalur KSEI tidak memakai penerjemahan ini.

**Cacat lama yang ikut ditemukan:** pola operator `Tf` ditulis dengan spasi di dalam regex `re.X`, jadi
tidak pernah cocok — ukuran font selalu jatuh ke bawaan 10. Diperbaiki; berkas KSEI 2025, 2026, 2027
diunduh ulang dan `urai_kalender` memberi hasil **identik** dengan pola lama dan baru.

**Hasil atas 18 contoh:** 16 terbaca; 1 (GPSO 30 Des 2024, tata letak lain) nomornya terpotong baris kaki
→ ditolak dengan sebab itu; 2 (OCAP 2024, format `BEI.PLP`, pembukaan Pasar Negosiasi — K39) ditolak.
Ke-16 yang terbaca dipilah terhadap salinan `notasi-khusus.csv` kerja (baca-saja): **16/16 "sudah
tercatat"** — episode API lama yang ditutup pada tanggal pengumuman UPT — 0 penutupan ganda. SPT/UMA
yang sudah terbaca (3 PDF pengguna, 9 SPT riset) tetap terbaca sama. ~~Sebelas~~ **Sepuluh** (koreksi
K103: 19 SPT riset = 9 terbaca + 10 ditolak) SPT riset lain tetap ditolak karena kalimat tanggal
berlakunya berbeda ("pada tanggal" tidak ada) — batas K99, bukan bagian pekerjaan ini. **K103** kemudian
membaca 8 di antaranya (suspensi lanjutan "mulai sesi I tanggal …"); 2 tetap ditolak (nomor berformat lain).

**Yang dibangun:** `pengumuman_idx` (`Pengumuman.pembukaan`/`rujukan`/`tutup`, `pilah` memproses SPT
lebih dulu sehingga SPT + UPT boleh diunggah bersama → satu baris tertutup),
`notasi.HasilNotasi.penutupan` (ditolak bila tidak menunjuk tepat satu baris terbuka), ringkasan
konfirmasi + teks dasbor + tindakan jadwal. Rincian teknis `docs/arsitektur.md` T95.

---

## 4. Kontradiksi kecil di PRD (tidak memblokir, perlu Anda ketahui)

| No | Lokasi | Isi |
|----|--------|-----|
| C1 | 9.2 | Merujuk "tabel 9.2" yang tidak ada; maksudnya tabel 12 (daftar fitur) |
| C2 | 8.3 | Menyebut "ambang tambahan di v1.2" padahal dokumen v1.3 |
| C3 | 17 vs 16 & tabel 5 | Q1–Q5 masih "terbuka" padahal roadmap dan cakupan v0.1 sudah mengandaikan jawabannya (backtest ditunda, basis dua ember) |
| C4 | 8.1 vs 12 | Definisi tabel 12 lebih ringkas dari 8.1 (mis. `harga_harian` tanpa `diketahui_pada` di satu tempat, ada di tempat lain); saya pakai gabungan terlengkap |
| C5 | `skema-data.md` & komentar `skema.py` vs `CREATE TABLE fundamental` | Keduanya dulu menulis **"`tgl_publikasi` ikut kunci"**, padahal kunci utama tabelnya `kode` + `periode` + `jenis_laporan` + **`diketahui_pada`**. Ditemukan 10 Okt 2026 saat menelaah migrasi 007; **kedua tempat sudah dikoreksi**. **Dituntaskan 10 Okt 2026 dengan pengukuran — kuncinya sudah tepat, dan dua cacat ikutannya sudah diperbaiki.** Yang diukur dan hasilnya: (a) dua baris periode sama di **satu berkas** memang bertabrakan; sejak perbaikan ini berkasnya **ditolak pembacanya lebih dulu**, dengan nama berkas dan kedua nomor barisnya, bukan sebagai kegagalan penulisan yang menyebut kunci basis data — dan seluruh berkas 794 baris tidak lagi ditolak oleh satu pasang baris; penjaganya hanya menolak dua baris yang **isinya berbeda**, sedangkan baris kembar identik tetap lewat (keputusan "sudah ada dan sama" tetap di titik tulis); (b) dua baris periode sama dari **dua jalan impor** bisa hidup berdampingan **hanya bila waktunya berbeda detik** — `diketahui_pada` berketelitian detik, jadi dua jalan dalam detik yang sama bertabrakan; (c) pembacaan point-in-time-nya **sudah benar tanpa perlu migrasi**: snapshot yang dibuat sebelum restatement tetap membaca laporan lama, dan snapshot sesudahnya membaca yang baru — jadi kunci yang berlaku sekarang memenuhi AC-15, dan `tgl_publikasi` memang **penyaring**, bukan bagian kunci. Yang diperbaiki bukan skemanya melainkan **pesan galatnya**, yang sebelumnya berbunyi "Perbaiki berkasnya … atau impor revisinya lewat jalan tersendiri yang lebih baru" — yaitu menyuruh melakukan persis hal yang barusan gagal. Sekarang pesannya membedakan dua sebab (detik yang sama vs satu berkas berisi dua revisi) beserta jalan keluar yang benar untuk masing-masing. Bukti: `.tmp/c5_probe.py` (skrip sementara, tidak ikut git) + `tests/test_ingesti.py::test_dua_jalan_pada_detik_yang_sama_ditolak_dengan_sebab_yang_benar` + tiga uji penjaga berkas di `tests/test_impor_berkas.py` |
| C5 | 9.3 vs 7.2 | 9.3 menyebut penyesuaian "split dan right issue", 7.1/7.2/8.1 mencantumkan dividen sebagai aksi korporasi → perlu keputusan U4 |
| C6 | 11.1 vs 11.4 | Angka ilustrasi tidak konsisten (risiko berjalan 3,0% di dasbor vs 2,25% → 2,57% di kalkulator); saya anggap ilustrasi, bukan spesifikasi |
| C7 | Penomoran heading | Campur (3.2 → 4, ada "Heading 3" tanpa "Heading 2"), jadi rujukan nomor sub-bab harus diverifikasi manual |
| C8 | 8.1 (tabel 9) vs 10 | Tabel 9 menaruh `lot` dan `tick` sebagai kolom entitas `Emiten`, sedangkan bagian 10 mewajibkan parameter bursa sebagai konfigurasi **bertanggal**. Dipakai bagian 10 (aturan keras 1 & 4): `lot`/`tick` tidak menjadi kolom `emiten`, melainkan entri konfigurasi bertanggal. Tabel 9 juga menyebut 3 jenis emiten, sedangkan tabel 11 menambah perlakuan "padat modal" — belum diputuskan apakah itu jenis tersendiri atau turunan sektor |
| C9 | 7.1 vs template TOML awal | Imbal hasil SUN 10 tahun tercantum sebagai **data** bulanan bertanggal (PRD 7.1, sudah punya tabel `imbal_hasil_sun`), tetapi template TOML awal menaruhnya sebagai parameter B10. Dua tempat untuk satu fakta = pertanyaan "nilai mana yang dipakai berhitung?" tidak bisa dijawab. **Diputuskan (Tahap 0 langkah 2): SUN tetap data**, blok `[[imbal_hasil_sun]]` dicabut dari template, dan `docs/konfigurasi.md` B10 menunjuk ke tabel itu. Perlu Anda ketahui karena ini mengubah berkas yang sudah Anda lihat |
| C10 | 7.2 ("harga disimpan mentah") vs data sumber yang sudah disesuaikan | **Diputuskan 9 Okt 2026 → K8; buktinya di 1.5.** PRD 7.2 menetapkan harga disimpan mentah dan penyesuaian aksi korporasi dihitung saat dibaca. Harga historis dari Yahoo ternyata **sudah** disesuaikan split oleh sumbernya, sehingga mencatat split sebagai aksi penyesuaian lalu menerapkannya lagi akan menghitung dua kali. Jalan keluarnya: penanda per baris `penyesuaian_sumber`, dan penyesuaian saat dibaca melewati apa yang sudah diterapkan sumber |

---

## 5. Keadaan sekarang & yang belum dikerjakan

### Perbaikan dependensi dan publikasi (03 Nov 2026)

- Pengguna menyetujui perbaikan: certifi 2026.10.19, setuptools 84.1.0, dan python-docx
  1.2.0 dipasang lewat requirements-dev. Lock 32 paket menjadi constraint pemasangan
  runtime/dev; versi lain tetap. Ini menutup dua advisory dan kekosongan dev lock.
- Audit PyPI/OSV lock serta PyPI lingkungan seluruhnya exit 0, tanpa kerentanan diketahui
  atau paket dilewati. Pip check bersih; CA terdampak tidak ada; HTTPS requests/curl_cffi
  dengan TLS aktif dan ekstraksi PRD lulus. Suite salinan: 1.125 lulus, 94,29 detik.
- Salinan/ZIP publikasi diregenerasi (131 berkas, satu commit nonpribadi). Tidak ada push,
  perubahan data kerja, atau perubahan kode aplikasi pada tahap ini. Batas: native/OS,
  pengaturan GitHub, dan hash artefak lock belum ditangani. Rincian laporan audit.


### Audit kerentanan dependensi (03 Nov 2026)

- Audit diminta pengguna; rincian `docs/audit-dependensi-2026-11-03.md`.
- Pip-audit 2.10.1: lock 31 paket melalui PyPI/OSV dan lingkungan 43 paket melalui PyPI,
  exit 1 pada ketiganya. Dua kerentanan unik: certifi 2026.7.22 kritis, setuptools 84.0.0
  rendah. Scanner menampilkan tiga karena duplikasi ID certifi; tidak ada paket dilewati.
- Perbaikan yang tersedia: certifi 2026.10.19 dan setuptools 84.1.0. Belum diterapkan;
  python-docx belum masuk lock/lingkungan, dependensi dev masih perlu dilengkapi.
- Verifikasi aplikasi: 1.125 tes lulus (144,12 detik), pip check bersih. Audit keamanan
  tetap gagal; salinan publikasi/ZIP terdahulu masih memakai versi rentan. Dependensi,
  kode, dan data kerja tidak diubah. Tahap audit berhenti untuk tinjauan sesuai K4.


### Persiapan publikasi GitHub (03 Nov 2026)

- Pengguna menyetujui penanganan empat temuan publikasi dan memilih **MIT**. LICENSE memakai
  atribusi Kontributor MejaSaham; hak data pihak ketiga tetap mengikuti sumbernya.
- Jalur/nama pengguna lokal dalam dokumen disamarkan; `.gitignore` diperkuat untuk kredensial,
  private key, basis data SQLite, konfigurasi aktif, dan pengaturan mesin.
- Salinan publikasi `.tmp/publikasi-20261103/MejaSaham` memakai satu commit awal nonpribadi,
  tanpa `.git` asli atau data kerja. Riwayat asli tetap lokal; jangan di-push ke publik.
- Template bawaan dan draf PACK manual bersumber KSEI tetap ikut; unduhan vendor, PDF sumber,
  snapshot, transaksi, dan basis data tidak ikut. Panduan: `docs/publikasi.md`.
- Verifikasi akhir dan keadaan berikutnya dicatat pada bagian atas `docs/lanjutan.md`.


**Sudah ada (2026):**

- Kerangka dokumen: `AGENTS.md`, `README.md`, `arsitektur.md`, `skema-data.md`,
  `konfigurasi.md`, `ideas.md`.
- Kerangka kode: paket `mejasaham/` (satu titik masuk untuk dua mode, `ui/` sebagai
  satu-satunya tempat Qt boleh diimpor), `requirements.txt` + `requirements-dev.txt`,
  `pytest.ini`, dan dua test penjaga batas.
- Repositori git di `C:\Users\PENGGUNA\Projects\MejaSaham` — **dipindah keluar OneDrive** dengan
  commit dasar dokumen; alasan pemindahan ada di `AGENTS.md` bagian 5 dan commit itu sendiri.
- Template parameter bursa: `mejasaham/defaults/parameter-bursa.contoh.toml` (di dalam paket,
  supaya AC-12 bisa dipenuhi saat folder data dikosongkan).
- Jejak asal pada turunan PRD: `_extract/prd_v1.3.txt` kini memuat SHA-256 `.docx` sumbernya.

**Tahap 0 — langkah 1 (lapisan basis data), selesai 2026:**

- `mejasaham/lokasi.py` — letak data runtime di luar paket (A3); `MEJASAHAM_DATA` menimpanya
  untuk test/mode portabel.
- `mejasaham/skema.py` — migrasi 001 "fondasi data": `emiten`, `harga_harian`, `harga_indeks`,
  `aksi_korporasi`, `kalender_bursa`, `notasi_khusus`, `sektor_idx_ic`, `imbal_hasil_sun`,
  `snapshot`, `log_jalan`; tabel `STRICT`; trigger penolak `UPDATE`/`DELETE`; view
  `v_<tabel>_terkini`.
- `mejasaham/db.py` — WAL, `busy_timeout`, foreign key, `PRAGMA user_version`, tabel jejak
  migrasi, `tulis()` dengan `BEGIN IMMEDIATE`, dan penolakan skema yang lebih baru daripada
  aplikasi.
- `tests/test_lokasi.py` + `tests/test_db.py` — 27 uji lulus.
- Catatan lingkungan (2026): di sesi agen, proses Python anak tidak diizinkan menulis di luar
  folder repositori, sehingga jalur bawaan `%LOCALAPPDATA%\MejaSaham` belum bisa diuji dari
  sesi itu — yang teruji adalah logika jalurnya lewat `MEJASAHAM_DATA`. Di komputer pengguna
  folder itu bisa dibuat seperti biasa (sudah dicoba dari PowerShell). Pesan galat folder data
  sekarang menyebut penyebab + jalan keluarnya, bukan menumpahkan `PermissionError` mentah.

**Tahap 0 — langkah 2 (konfigurasi), selesai 2026:**

- `mejasaham/skema.py` — migrasi 002 "parameter_bursa_bertanggal": tabel kepala
  `parameter_bursa` + sembilan tabel muatan bertipe (`parameter_lot`,
  `parameter_fraksi_harga_rentang`, `parameter_auto_rejection_rentang`,
  `parameter_settlement`, `parameter_biaya_broker`, `parameter_pajak_penjualan`,
  `parameter_slippage`, `parameter_papan_pemantauan_khusus`), trigger append-only, view
  `v_parameter_bursa_terkini`. Daftar tabel/kunci tiap migrasi kini dibekukan per migrasi
  supaya basis data lama dan baru tidak bisa berbeda diam-diam.
- `mejasaham/konfigurasi.py` — muat TOML → validasi ketat → simpan idempoten ke basis data
  (sidik jari SHA-256) → `nilai_efektif()` dengan tiga keadaan dan `ParameterBelumSiap`
  sebagai penolakan berhitung (aturan keras 1). Tidak ada satu pun nilai parameter bursa di
  dalam kode; persen masuk sebagai basis poin lewat `Decimal`.
- `python -m mejasaham --muat-konfigurasi` — mode kepala: menyalin template bawaan bila berkas
  aktif belum ada, memuat, lalu melaporkan keadaan tiap parameter (keluar 1 bila berkas salah).
- Template TOML: aturan pengisian diperjelas (termasuk `dicatat_pada` dan larangan salah
  ketik), dan blok `[[imbal_hasil_sun]]` dicabut — lihat C9 di bagian 4.
- `tests/test_konfigurasi.py` (49 uji) + penjaga sidik migrasi di `tests/test_db.py` —
  seluruhnya 77 uji lulus.

**Tahap 0 — langkah 3 (ingesti, mutu data, arsip snapshot), selesai 2026:**

- `mejasaham/ingesti.py` — aturan ingesti tanpa tahu-menahu soal penyedia data: kontrak
  `KumpulanData` (dipakai bersama kedua jalur masuk), konversi ketat T8 (nilai tak terbaca →
  `None`, **bukan** 0; berpecahan disimpan di kolom `*_mentah`), penulis baris append-only yang
  **idempoten** (isi sama → tidak menambah baris; isi berbeda → tambah revisi, S1), snapshot +
  log jalan dalam **satu** transaksi (A6/AC-19), dan `periksa_ambang_gagal` (PRD 9.3).
- `mejasaham/pengambil.py` — satu-satunya tempat yfinance dikenal. Label
  `yfinance/Yahoo Finance (tidak resmi)` melekat di setiap baris; retry dengan jeda bertambah
  (bawaan yfinance `retries=0`); berurutan dengan jeda, bukan paralel, karena `download()`
  bawaannya menjalankan ~2×CPU permintaan serentak.
- `mejasaham/berkas.py` — pembaca enam jenis berkas impor + rujukan emiten. Kolom tak dikenal
  dan kolom wajib yang hilang **menolak** berkas; seluruh baris yang salah dilaporkan sekaligus
  dengan nama berkas + nomor baris. Pemisah `;`/`,` dideteksi, BOM UTF-8 diterima, baris `#` dan
  baris contoh `<<CONTOH>>` diabaikan. Menyalin template bawaan saat belum ada (AC-12).
- `mejasaham/mutu.py` — laporan mutu PRD 7.3 bertingkat: `BOLONG` (keluar dari peringkat),
  `TAK_WAJAR` (ditinjau manusia), `CATATAN`. Lonjakan diperiksa terhadap aksi korporasi di
  sekitarnya, sehingga split tidak dilaporkan sebagai data rusak. Pemeriksaan yang **belum bisa**
  dijalankan (ADTV20/50 emiten teratas) dilaporkan sebagai belum dapat diperiksa, bukan dianggap
  lulus.
- `mejasaham/arsip.py` — arsip snapshot harian (PRD 7.2), tulis atomik (`os.replace`), satu
  folder per `id_snapshot` sehingga arsip lama tidak bisa tertimpa, baris kepala memuat
  `id_snapshot` + tanggal data + versi skema/aplikasi + peringatan sumber tidak resmi +
  pernyataan bukan nasihat investasi (AC-7, aturan keras 8).
- `mejasaham/pengatur.py` — urutan kerjanya: ambil → periksa ambang → mutu → tulis atomik →
  arsip. Kegagalan arsip menjadi **peringatan**, bukan pembatalan snapshot; kegagalan snapshot
  tidak menghapus apa pun.
- `mejasaham/cli.py` — `--refresh`, `--impor`, `--emiten-awal`, `--folder-data`, `--sejak`,
  `--jeda`. `--saring` masih kode keluar 2 (Tahap 1).
- Template berkas impor di `mejasaham/defaults/`: `emiten.contoh.csv` (**tanpa satu pun kode
  emiten** — semesta saham keputusan pengguna), `harga-harian`, `harga-indeks`, `aksi-korporasi`,
  `kalender-bursa`, `notasi-khusus`, `imbal-hasil-sun`. Plus `emiten-awal.contoh.csv`: 21 kode
  besar sebagai titik awal, seluruh kolom data dikosongkan dan setiap barisnya menyatakan
  "belum diverifikasi".
- `tests/test_ingesti.py` (52 uji, seluruhnya **tanpa jaringan** lewat pengambil palsu) —
  termasuk uji regresi untuk dua bug nyata yang ditemukan saat pengujian langsung: (a) pencarian
  "baris sudah ada?" memakai kunci lengkap yang memuat `diketahui_pada`, sehingga ingesti ulang
  menumpuk salinan identik; (b) `INSERT OR IGNORE` di titik tulis **menelan** kegagalan CHECK
  harga negatif, sehingga baris hilang tanpa suara — bertentangan dengan aturan keras 7.
- Diverifikasi langsung pada 9 Okt 2026: `--refresh` atas 21 emiten mengambil 609 bar harga +
  58 bar indeks dari yfinance, menulis snapshot, dan mengarsipkannya; menjalankan ulang
  melaporkan **0 baris baru** (idempoten).

**Tahap 1 — langkah 1 (keputusan + fondasi data perhitungan), selesai 9 Okt 2026:**

- Keputusan **K8** (C10: penanda penyesuaian sumber), **K9** (P1: emiten likuid), dan **K10**
  (P5–P12: definisi metrik) dikunci, beserta bukti pengukuran C10 di 1.5.
- `mejasaham/skema.py` — migrasi 003 "penyesuaian_sumber_fundamental_rasio_bank": kolom
  `harga_harian.penyesuaian_sumber` (ALTER TABLE, ikut terbaca lewat `v_*_terkini`), tabel
  `fundamental` (dengan `mata_uang` & `satuan_uang`) dan `rasio_bank`; migrasi 004
  "preset_saring_dan_skor": `preset_saring`, `preset_kriteria`, `preset_bobot_faktor`,
  `preset_bobot_metrik`, dan `skor`. Preset & kriterianya append-only (berversi); `skor`
  sengaja **bukan** append-only karena ia turunan deterministik (T27).
- `mejasaham/potret.py` — memuat satu snapshot secara **as-of** (T20): revisi yang
  `diketahui_pada`-nya melewati batas snapshot tidak dipakai, dan fundamental disaring menurut
  `tgl_publikasi` (AC-15). Ini yang membuat `v_*_terkini` tidak boleh dipakai menghitung
  snapshot lama.
- `mejasaham/penyesuaian.py` — penyesuaian harga **saat dibaca** dengan `Fraction` (tepat),
  melewati aksi yang sudah diterapkan sumber (K8/C10), dan menolak menghitung right issue
  dengan alasan yang menyebut sebabnya. Uji AC-18: 20 uji, termasuk bukti bahwa harga 1000
  menjadi 500 pada split 1:2 dan bahwa satu baris tepat di tanggal aksi sudah memakai basis
  pascasplit.

**Tahap 1 — langkah 2 (metrik, saring, skor), selesai 9 Okt 2026:**

- `mejasaham/metrik.py` — seluruh metrik PRD 8.2 (ADTV20, ROE 5 tahun, DER, coverage, CFO/NI,
  CAGR pendapatan, PER TTM dari laporan kumulatif, PER normalisasi, PBV, EV/EBITDA, imbal hasil
  laba vs SUN, momentum 12-1, kekuatan relatif, volatilitas, ATR14 Wilder, jarak 52 minggu,
  tren MA200, kapitalisasi, imbal hasil dividen, breadth, rezim pasar) + set bank (NPL/CAR/BOPO/
  NIM). Setiap nilai membawa satuan, asal, dan — bila tidak bisa dihitung — alasannya (AC-3).
- `mejasaham/saring.py` — preset berversi (K6) dan kriteria PRD 9.4 dengan **tiga keadaan**:
  lolos, gagal, dan "tidak bisa dinilai" (yang tidak pernah dihitung lolos). Kriteria mengikuti
  jenis emiten (AC-16): DER/CFO-NI/coverage tidak berlaku untuk bank, NPL/CAR/BOPO/NIM tidak
  berlaku untuk non-bank — dan "tidak berlaku" dibedakan dari "tidak bisa dinilai".
- `mejasaham/skor.py` — z per sektor (statistik populasi, potong ±3, arah dibalik untuk metrik
  "rendah lebih baik"), pemetaan z → 0–100, pengalihan bobot metrik & faktor (AC-3), statistik
  dari semesta likuid dengan fallback sektor < 8 emiten (AC-17), peringkat dengan pemutus seri
  ADTV20 lalu kode, dan penjelasan tiap kontribusi tersimpan bersama skornya.
- `mejasaham/cli.py` — `--saring`, `--preset`, `--preset-bawaan`, `--kode`, `--teratas`.
  `--kode` sengaja **tidak menyimpan** hasilnya: peringkatnya parsial dan menyimpannya akan
  menimpa peringkat penuh snapshot itu.
- Preset bawaan dua ember (K1): `kualitas-nilai/v1` (bobot faktor & metrik PRD 9.5/9.5.1) dan
  `momentum/v1`. **Bobot `momentum/v1` belum ditetapkan PRD** — yang tertulis adalah usulan
  awal dan masih menunggu persetujuan Anda.
- Diverifikasi langsung pada 9 Okt 2026 lewat baris perintah (bukan pemanggilan fungsi):
  `--impor` atas 16 emiten sintetis menulis 5.239 baris, lalu `--saring` menyaring 16 emiten,
  menilai 5 kandidat, dan memberi peringkat; dua jalan berturut-turut menghasilkan keluaran
  **identik** (AC-2); menjalankan `--impor` ulang melaporkan **0 baris baru** (idempoten);
  `--saring --preset momentum/v1` memberi peringkat berbeda, dan `--saring --kode ...` menolak
  menyimpan hasil parsialnya. Uji ujung-ke-ujung ini menemukan tiga cacat nyata yang sudah
  diperbaiki: kriteria `momentum_12_1` tidak terdaftar di CHECK skema (preset kedua gagal
  disimpan), kriteria bank membandingkan basis poin dengan rasio (ambangnya selalu lolos), dan
  `print()` karakter "≥" membuat proses **crash** di konsol Windows cp1252 setelah pekerjaan
  selesai.
- Uji: `tests/test_penyesuaian.py` (20), `tests/test_potret.py` (5), `tests/test_metrik.py` (27),
  `tests/test_saring.py` (18), `tests/test_skor.py` (15), `tests/test_impor_berkas.py` (23),
  plus uji regresi di `tests/test_ingesti.py` — seluruhnya **242 uji lulus**. Uji baru itu
  menemukan dua bug warisan Tahap 0 yang sudah ditutup: dua revisi berbeda untuk kunci yang sama
  dalam satu jalan ingesti hilang tanpa suara (lognya malah berkata "sudah ada dan sama"), dan
  `metrik_emiten` menampilkan rasio bank untuk emiten non-bank bila berkas `rasio-bank.csv`
  salah kode.
- `mejasaham/mutu.py` menepati janji K8 yang sebelumnya baru tertulis di dokumen: baris tanpa
  penanda pada emiten yang punya aksi penyesuaian dilaporkan (satu catatan per emiten, beserta
  akibatnya), dan lonjakan di sekitar tanggal split pada baris yang mengaku sudah disesuaikan
  sumber ditandai `TAK_WAJAR` — bukan dimaafkan aksi korporasi.
- `mejasaham/tampilan.py` — format tampilan Indonesia (U11) dikumpulkan di satu tempat, dan
  keluaran baris perintah memakainya. Glif yang tidak ada di cp1252 (`≥`, `≤`, `→`) diganti di
  pesan yang **dicetak** — laporan mutu Tahap 0 pun bisa crash tanpanya — dengan
  `errors="replace"` sebagai jaring pengaman terakhir.

**Tahap 1 — langkah 3 (dua pemeriksaan mutu yang tertunda), selesai 9 Okt 2026:**

- Dua pemeriksaan yang selama ini berstatus "belum dapat dijalankan" karena "ADTV20 baru ada di
  Tahap 1" kini benar-benar berjalan. Keadaan itu berbahaya justru karena terlihat seperti lulus,
  jadi menutupnya adalah pekerjaan yang mendesak, bukan kerapian.
- `mejasaham/mutu.py` — `peringkat_adtv()` (ADTV20 dari **20 hari bursa bersama**, disaring per
  label sumber) dan `bandingkan_sumber_kedua()` + `temuan_perbandingan()`. Selisih di atas
  **1%** ditandai `TAK_WAJAR` sesuai PRD 7.3; selisih yang tidak bisa dihitung dilaporkan
  sebagai catatan, **bukan** dianggap sama. Tanpa harga pembanding, hasilnya menyebut alasannya —
  dan baris perintah keluar dengan kode bukan nol, sebab pemeriksaan yang menemukan masalah
  tetapi keluar 0 akan terbaca lulus oleh Task Scheduler (AC-9, AC-11).
- Gerbang **PRD 9.3/AC-1 disambungkan**: `pengatur.jalankan_refresh` mengisi `emiten_kritis`
  dengan 50 emiten ber-ADTV20 tertinggi dari `mutu.peringkat_adtv`. Sebelumnya parameter itu
  dikirim `None`, sehingga syarat "salah satu dari 50 emiten teratas gagal → snapshot tidak
  diterbitkan" tidak pernah diperiksa. Daftarnya diambil dari baris yang **sudah tersimpan**,
  supaya emiten yang gagal diambil hari ini tetap bisa dikenali sebagai emiten teratas.
- `mejasaham/cli.py` — `--cek-sumber-kedua` dan `--sumber-pembanding` (mode kepala, PRD 7.3).
  Dipisah dari `--refresh` dengan sengaja: PRD menuntut pemeriksaan ini **mingguan**, sedangkan
  refresh harian.
- **Migrasi 005** — kunci alami `harga_harian` menjadi `kode + tanggal + sumber`, dan
  `v_harga_harian_terkini` dibentuk ulang. Tanpanya, memasukkan harga pembanding membuat harga
  sumber utama hilang pada tanggal yang sama (rinciannya di `docs/skema-data.md` 5.6).
- Berkas impor harga boleh menyatakan kolom `sumber` per baris; `HargaHarian.sumber` tidak lagi
  ditimpa label kumpulan. Tanpa ini, harga dua sumber tidak bisa dibedakan sama sekali dan cek
  sumber kedua mustahil dijalankan — bukan sulit, tetapi tidak mungkin.
- `mutu.periksa(..., sumber=...)` menyaring lintasan utamanya ke satu label sumber. Dua sumber
  dalam satu lintasan saling dibandingkan sebagai "harga sebelumnya", sehingga selisih antar
  sumber muncul sebagai lonjakan harga yang tidak pernah terjadi.
- Uji: `tests/test_mutu_adtv.py` (24 uji) + penjaga baru di `tests/test_defaults.py` — seluruhnya
  **276 uji lulus**. Uji integrasi langkah ini menemukan tiga cacat nyata yang sudah diperbaiki:
  (a) `pengatur.jalankan_refresh` **mati dengan `TypeError`** setiap kali ada emiten gagal tanpa
  pembatalan — yaitu keadaan yang paling sering terjadi dalam pemakaian nyata, dan tidak pernah
  teruji karena uji lama memakai jalur impor; (b) pemilihan sumber utama menebak dari jumlah
  baris pada satu tanggal, sehingga harga pembanding terpilih sebagai sumber utama dan
  pemeriksaan yang sebenarnya bisa dijalankan berubah menjadi "ADTV20 belum bisa dihitung";
  (c) tiga dari sepuluh template CSV bawaan punya baris contoh yang **jumlah kolomnya tidak cocok
  dengan kepalanya** (`kalender-bursa`, `notasi-khusus`, `imbal-hasil-sun`) — tidak ketahuan
  selama ini karena baris contoh tidak pernah terimpor, padahal ia yang pertama disalin orang.
- Diverifikasi langsung lewat baris perintah pada 9 Okt 2026 atas data sintetis 16 emiten:
  `--impor` melaporkan peringkat ADTV20 di laporan mutu; `--cek-sumber-kedua` **sebelum** harga
  pembanding ada keluar kode 1 dengan alasan "belum dapat diperiksa, ini BUKAN berarti lulus";
  sesudah harga pembanding diimpor, ia memeriksa 16 emiten dan **menandai tepat satu** yang
  selisihnya 2,00%, sementara yang 0,50% tidak ditandai — sesuai PRD 7.3.

**Catatan lingkungan (9 Okt 2026, diperbarui):** sesi agen sempat berjalan dengan sandbox berkas
`workspace-write`, dan pada mode itu **seluruh uji berbasis `tmp_path` gagal di tahap setup**
(169 dari 242 uji) — bukan karena kode, melainkan karena `tempfile` Python 3.14 membuat folder
sementara dengan `os.mkdir(mode=0o700)`, dan folder hasilnya menolak diakses proses di dalam
sandbox. Gejalanya menyesatkan: yang tampak adalah 169 kegagalan uji. Setelah kebijakan sesi
menjadi akses penuh, `python -m pytest` melaporkan **242 uji lulus** tanpa satu pun perubahan
kode, dan 276 uji lulus setelah langkah 3. Catatan ini disimpan supaya kegagalan serupa tidak
dikejar sebagai bug produk di kemudian hari.

**Tahap 1 — langkah 4 (jalur daftar emiten dari Master File Efek KSEI), selesai 9 Okt 2026:**

- `mejasaham/ksei.py` (baru) — unduh → urai → tulis `emiten.csv` → **baca ulang sebagai bukti**
  (dibaca pembaca yang sama dengan yang dipakai `--refresh`). Tanpa dependensi baru: `urllib`,
  `zipfile`, dan `csv` dari pustaka standar, jadi tidak ada paket baru yang ikut ke bundel.
- Perintah baru: `--ambil-emiten` dan `--tanggal-master YYYY-MM-DD`; penjaga `--timpa-emiten` yang
  sudah ada dipakai ulang. Berkas yang sudah ada **tidak** ditimpa tanpa izin, karena isinya
  semesta pilihan pengguna dan mungkin sudah disunting (sektor, jenis, papan dari sumber lain).
- Diverifikasi nyata 9 Okt 2026 atas berkas KSEI 30 Sep 2026 (145.689 byte, 3.681 baris):
  **973 saham biasa IDX aktif** ditulis dan terbaca ulang; 2.698 baris bukan EQUITY, 6 bukan bursa
  IDX, dan 2 saham preferen/seri dikeluarkan. `--impor` menulis **973 baris emiten** ke basis data
  uji dengan `jumlah_saham` terisi seluruhnya, sedangkan sektor/papan/jenis/free float/status
  notasi **NULL** — bukan nol, bukan pendekatan.
- Dua cacat nyata yang hanya ketahuan dari berkas sungguhan, bukan dari uji offline:
  (a) berkas KSEI memuat **satu catatan yang terbelah menjadi dua baris fisik** (baris 3619–3620:
  nama efek sukuk patah di tengah kolom), sehingga pengurai yang menuntut 28 kolom menolak seluruh
  berkas; kini catatan seperti itu disambung **hanya bila jumlah kolomnya kembali tepat** — bukti
  yang bisa diperiksa — dan setiap penyambungan dilaporkan di keluaran, supaya bentuk berkas
  sumber yang cacat tidak hilang dari pandangan. (b) filter `EQUITY` + bursa `IDX` ikut membawa
  **saham preferen/seri** (`MAMIP` ISIN `ID2000052903`, `MYRXP` ISIN `ID2000061706`, keduanya
  berharga penutup 0 di sumber); keduanya dikeluarkan dan pengeluarannya disebut.
- Uji: `tests/test_ksei_emiten.py` (31 uji, seluruhnya **tanpa jaringan** — pengunduh disuntikkan
  sebagai fungsi palsu) — seluruhnya **307 uji lulus**.
- **Belum dikerjakan pada langkah ini:** `sektor_idx_ic`, `papan`, `jenis`, dan `free_float_persen`
  tetap kosong (alasannya di K12); `Listing Date` KSEI — 87 dari 975 kosong di sumbernya — belum
  bisa masuk karena berkas rujukan belum punya kolom `tanggal_notasi`, dan menambahkannya menyentuh
  pembaca berkas, jalur impor, dan template, jadi dikerjakan tersendiri.

**Tahap 1 — langkah 4b (refresh nyata atas semesta KSEI), 9 Okt 2026:**

- Percobaan pertama: `--refresh` atas **973 kode** KSEI apa adanya → 916 emiten berhasil, **57 gagal
  (5,9%)**. Gerbang PRD 9.3 menolak menerbitkan snapshot (ambang >5%) dan **tidak satu baris pun
  tertulis** — 999.421 bar yang sudah diunduh dibuang, bukan disimpan separuh. AC-19 terbukti
  bekerja justru pada kejadian nyata ini.
- Ke-57 kegagalan itu **seragam dan permanen**: Yahoo menjawab `No data found, symbol may be
  delisted`. Artinya kode-kode itu masih tercatat di KSEI tetapi **tidak diperdagangkan lagi** —
  pelajaran yang tidak bisa didapat dari berkas KSEI saja: **"ACTIVE" di Master File Efek berarti
  masih tercatat di KSEI, bukan masih diperdagangkan di IDX.** Usulan penanganannya di **U18**.
- Percobaan kedua atas semesta **916 kode** (daftar KSEI dikurangi 57 kode itu, dengan catatan
  lengkap di kepala berkasnya): **999.421 bar harga, 916 emiten, 0 gagal, rentang
  2021-10-11 → 2026-10-09** (tepat lima tahun), snapshot terbit, arsip tertulis.
- **Cacat ketiga**, ditemukan di langkah paling akhir: arsip snapshot gagal dengan
  `sqlite3.OperationalError: unable to open database file` pada kueri `GROUP BY` di `arsip.py`,
  **sesudah** ~15 menit unduhan. Sebabnya bukan kuerinya: SQLite melimpahkan `GROUP BY` sejuta
  baris ke berkas sementara di folder temp sistem, dan folder itu tidak bisa ditulis di lingkungan
  percobaan ini. Diperbaiki dengan `PRAGMA temp_store=MEMORY` (T22) + uji regresi; refresh diulang
  dan selesai `EXIT=0` dengan arsip **1.004.870 baris**. Perlu diketahui: di mesin biasa folder temp
  bisa ditulis, jadi cacat ini **tidak akan terlihat di sana** — tetapi aplikasi yang gagal di
  langkah terakhir setelah 15 menit kerja, dengan pesan yang tidak menunjuk sebabnya, tetap cacat.
- Idempotensi terverifikasi pada jalur nyata: refresh kedua menulis **6 baris baru, 1.004.864 sudah
  ada dan sama**, 0 gagal.
- `--saring` atas snapshot itu berjalan dan berkata apa adanya: **916 emiten → 235 likuid → 0
  kandidat**, karena `fundamental.csv`, `rasio-bank.csv`, dan `imbal-hasil-sun.csv` belum ada. Nol
  di sini **bukan** kegagalan saringan: alasan tiap faktor tercetak, dan itu data yang hanya Anda
  punya (P2/U3). Laporan mutu snapshot yang sama menyebut **95 bolong + 9 tak wajar → 99 emiten
  dikeluarkan dari peringkat**; mayoritas "bar hari terakhir belum ada" karena `kalender-bursa.csv`
  masih kosong, sehingga aplikasi tidak tahu 9 Okt itu hari bursa atau bukan.
- Uji: **308 uji lulus**.

**Tahap 1 — langkah 5 (U18: gerbang ambang gagal membedakan kegagalan permanen), selesai 9 Okt 2026:**

- Keputusan **K13** dikunci (usulan U18 dipakai apa adanya). Alasannya berubah dari "usulan" menjadi
  keputusan setelah kejadian nyata 9 Okt 2026: semesta resmi KSEI memuat kode yang masih tercatat
  tetapi tidak diperdagangkan lagi, dan gerbang yang menghitungnya menolak snapshot **selamanya**.
- `mejasaham/ingesti.py` — kontrak baru `Kegagalan(kode, alasan, jenis)` untuk `KumpulanData.gagal`,
  dengan bawaan **sementara** dan penolakan jenis tak dikenal (salah ketik harus gagal, bukan lolos);
  `KumpulanData.gagal_permanen` / `gagal_sementara`; `ringkas_kegagalan()` untuk laporan; dan
  `periksa_ambang_gagal` dengan tiga aturan yang eksplisit: emiten kritis **jenis apa pun** → tolak,
  >5% kegagalan **sementara** → tolak, permanen → dilaporkan. Pesan penolakan menyebut berapa
  kegagalan permanen yang tidak ikut dihitung, supaya angkanya bisa diperiksa manusia.
- `mejasaham/pengambil.py` — `GalatPengambilan` membawa jenisnya; `_galat_sumber_naik()` memaksa
  yfinance memunculkan galat bertipe (`config.debug.hide_exceptions = False`, dipulihkan di
  `finally`) karena bawaannya menelan galat dan mengembalikan tabel kosong — sehingga "simbol tidak
  ada" dan "koneksi dibatasi" tiba sebagai gejala yang sama: nol baris; `_klasifikasi_galat()` hanya
  menghitung **pernyataan sumber** sebagai permanen (`YFPricesMissingError.yahoo_reason`), sedangkan
  dugaan pustaka ("possibly delisted") tetap sementara; kegagalan permanen **tidak diulang** (tidak
  akan berubah, dan setiap permintaan tambahan menambah risiko pembatasan laju — K7).
- `mejasaham/pengatur.py` — pesan refresh memuat "N gagal (X permanen, Y sementara)", peringatan
  memisahkan "tidak diperdagangkan lagi (lubang diketahui)" dari "gagal sementara, patut diulang",
  dan temuan laporan mutunya berjenis `tidak_diperdagangkan` — bukan disamakan dengan
  `gagal_diambil`, sebab tindakan yang benar untuk keduanya berbeda.
- `mejasaham/berkas.py` — **dua cacat nyata** yang hanya ketahuan saat menyiapkan berkas verifikasi
  973 kode, keduanya sudah diperbaiki: (a) pemisah kolom dideteksi dari baris **fisik** pertama,
  sehingga berkas yang diawali komentar ditolak dengan pesan menyesatkan ("kolom tidak dikenal
  ['kode;nama;…']") padahal isinya benar — kini baris kepala dicari dengan aturan `_diabaikan` yang
  sama dengan pembacaannya; (b) baris kepala yang tetap terbaca sebagai satu kolom kini ditolak
  dengan pesan yang menyebut **letak** baris kepala, bukan hanya isinya.
- Uji: `tests/test_ingesti.py` (+10), `tests/test_mutu_adtv.py` (+3), `tests/test_impor_berkas.py`
  (+2) — seluruhnya **322 uji lulus**.
- Diverifikasi atas **sumber yang nyata**, bukan hanya objek palsu:
  1. **57 kode mati yang asli** (daftar dari `.uji-data/refresh-973.log`) diminta ulang ke sumber:
     **57 permanen, 0 sementara**, seluruhnya dengan alasan sumbernya sendiri
     ("No data found, symbol may be delisted"). Diumpankan ke gerbang dengan penyebut 973 seperti
     kejadian nyata → **lulus**, sedangkan masukan yang sama bila jenisnya sementara → **ditolak**.
     Bukti: `.uji-data/bukti-u18-57-kode.txt` (`EXIT=0`).
  2. `--refresh` atas semesta 13 kode dari daftar KSEI (5 kode mati + 8 kode hidup; 38% gagal,
     jauh di atas ambang 5%) → **snapshot terbit** (`EXIT=0`), 12.067 baris, 8 emiten berisi
     1.199 bar masing-masing, dan lima kode mati muncul sebagai temuan `tidak_diperdagangkan`
     beserta peringatan "5 emiten tidak diperdagangkan lagi (lubang diketahui), tidak ikut
     diperingkat: ATPK, COWL, CPRI, DUCK, JASS". Jalan kedua menulis **0 baris baru** (12.067
     sudah ada dan sama) — idempotensinya tidak terganggu perubahan ini.
     Bukti: `.uji-data/uji-u18-refresh.log` dan basis data `.uji-data/uji-u18/`.
- **Belum dikerjakan pada langkah ini:** refresh penuh atas 973 kode (butuh ±40 menit unduhan)
  belum dijalankan ulang; yang sudah dibuktikan adalah gerbangnya lulus untuk 57 kegagalan permanen
  dengan penyebut 973, dan snapshot terbit pada semesta campuran yang nyata. Semesta uji
  `.uji-data` masih berisi 916 kode seperti sebelumnya.

**Tahap 1 — langkah 6 (cadence cek sumber kedua: "tiap minggu" yang bisa diperiksa), selesai 9 Okt 2026:**

- Yang ditutup: PRD 7.3 menuntut penutupan 20 emiten ber-ADTV20 tertinggi dibandingkan sumber
  kedua **tiap minggu**. Kodenya sudah ada dan sudah berjalan sejak langkah 3, tetapi tidak ada
  satu pun catatan **kapan** ia terakhir dijalankan — jadi tuntutannya hanya bisa diasumsikan,
  bukan diperiksa. Pemeriksaan yang tidak bisa diperiksa punya sifat yang sama dengan pemeriksaan
  yang tidak pernah dijalankan.
- **Migrasi 006 — tabel `cek_sumber_kedua`** (append-only, seperti `snapshot`/`log_jalan`): satu
  baris = satu jalan cek, dengan `dijalankan_pada`, `tanggal_data`, sumber utama & pembanding,
  jumlah diperiksa/ditandai/tak terhitung/belum dapat, `cakupan` (`lengkap`/`belum_lengkap`), dan
  `catatan` berisi sebabnya. Kenapa bukan disimpulkan dari `log_jalan`: isinya prosa, dan
  menyimpulkan cadence dari teks berarti menebak isinya. Kenapa bukan disimpulkan dari
  ada-tidaknya harga pembanding: pembanding bisa diimpor berkali-kali **tanpa** satu pun
  perbandingan dijalankan — dan justru keadaan itu yang harus terlihat.
- `mejasaham/mutu.py` — `catat_cek_sumber_kedua` (menulis peristiwanya), `keadaan_cek_sumber_kedua`
  (membacanya kembali: **belum pernah**, **tepat waktu**, **lewat**, **tidak dapat dinilai**),
  `LaporanPerbandingan.lengkap`, `LaporanMutu.cek_sumber_kedua`, dan temuan
  `cek_sumber_kedua_<keadaan>` bertingkat `CATATAN`. Tingkatnya `CATATAN` dengan alasan yang
  eksplisit: cek mingguan yang tertunda tidak membuat satu pun angka emiten salah, jadi ia tidak
  boleh mengeluarkan emiten dari peringkat — yang tidak boleh adalah ia tidak terlihat.
- **Yang membedakan cek dari "kelihatan seperti cek":** `cakupan`. Cek yang berjalan tanpa harga
  pembanding (atau yang melewatkan sebagian emiten teratas) dicatat sebagai `belum_lengkap` dan
  **tidak** memenuhi tuntutan mingguan, walaupun ia tercatat berjalan. Sebaliknya cek yang
  **menemukan** selisih di atas 1% tetap `lengkap`: yang berbeda hanyalah temuannya, bukan
  kehadirannya.
- `mejasaham/pengatur.py` — `cek_sumber_kedua` mencatat setiap jalan (termasuk yang belum
  lengkap) dan menerima `momen` untuk pengujian; `jalankan_refresh` meneruskan `momen` ke laporan
  mutu dan menambahkan **PERINGATAN** ketika cadence-nya belum lulus. Snapshotnya **tetap
  terbit**: menahan snapshot karena cek mingguan yang tertunda akan menukar satu masalah dengan
  masalah yang lebih besar, dan keputusan yang lebih buruk itu tidak diminta PRD.
- `mejasaham/cli.py` — `--cek-sumber-kedua` mencetak keadaan cadence sesudah pencatatan
  ("cek terakhir lengkap N hari lalu; batas 7 hari" + "cek berikutnya paling lambat <tanggal>").
  Kode keluarnya tidak berubah: 1 bila ada selisih di atas ambang atau pemeriksaan belum dapat
  dijalankan, 0 bila lengkap dan bersih.
- Batas jeda **7 hari inklusif** (hari ke-7 masih tepat waktu; "lewat" mulai hari ke-8) ada di
  `mutu.JEDA_CEK_SUMBER_KEDUA_HARI` dan dicatat sebagai **U19** di bagian 2 — dipakai sampai Anda
  menyatakan keberatan.
- Uji: `tests/test_mutu_adtv.py` (+12: batas 7 hari, belum pernah, cek belum lengkap tidak
  memenuhi, catatan bertanggal di depan hari ini, tanggal tak terbaca, jalur nyata, peringatan
  refresh), `tests/test_db.py` (+2: append-only dan CHECK `cakupan`), plus sidik migrasi 006 —
  seluruhnya **336 uji lulus**.
- Diverifikasi lewat baris perintah atas **data nyata**, bukan hanya objek palsu:
  1. Salinan basis data uji 916 emiten (`.uji-data/uji-cadence/`): `--cek-sumber-kedua` sebelum
     ada pembanding → keluar **1**, tercatat `belum_lengkap` (0 diperiksa), dan cadence berbunyi
     "belum ada cek sumber kedua yang lengkap ... percobaan terakhir ... belum lengkap".
  2. Di folder yang sama, 20 penutupan pembanding untuk 20 emiten ber-ADTV20 tertinggi diimpor
     (`--impor`, dengan satu kode sengaja berselisih 2%) → `--cek-sumber-kedua` memeriksa **20
     emiten, menandai tepat satu (BBCA, 2,00%)**, keluar 1, dan cadence menjadi "terakhir lengkap
     0 hari lalu (2026-10-09); batas 7 hari · cek berikutnya paling lambat 2026-10-16".
  3. Sesudah pembanding disamakan: `--cek-sumber-kedua` keluar **0**.
  4. Salinan semesta U18 13 kode (`.uji-data/uji-cadence-refresh/`): `--refresh` **sebelum** ada
     cek → snapshot terbit (keluar 0) dengan temuan `cek_sumber_kedua_belum_pernah` **dan**
     peringatan "cek sumber kedua (PRD 7.3): cek sumber kedua belum pernah dijalankan ...";
     sesudah cek lengkap dijalankan (8 dari 8 emiten teratas), `--refresh` berikutnya **berhenti
     memperingatkan** dan laporan mutunya menyebut keadaannya apa adanya.
  Bukti: `.uji-data/uji-cadence/bukti-*.log` dan `.uji-data/uji-cadence-refresh/bukti-*.log`.
- **Ketahuan pada langkah ini, BELUM diperbaiki — cacat yang lebih besar daripada cadence itu
  sendiri.** Verifikasi di atas memakai harga pembanding yang diimpor ke basis data yang sama
  (memang begitu cara kerjanya sejak migrasi 005), dan begitu 20 baris itu masuk, hasil
  `--saring` berubah: **semesta likuid menyusut 235 → 215 emiten**, tepat pada 20 emiten yang
  diberi pembanding. Sebabnya terukur, bukan dugaan: `penyesuaian.sesuaikan` mengurutkan bar
  **berdasarkan tanggal saja**, sehingga dua bar tanggal sama dari dua sumber masuk ke satu
  deret; jendela 20 bar terakhir lalu memuat hari yang terduplikasi dan kehilangan satu hari,
  dan ADTV20 emiten itu berubah menjadi "tidak dihitung" (alasan yang tercetak: "hanya 19 dari
  20 hari bursa terakhir yang punya nilai transaksi"). Yang hilang dari saringan justru
  emiten-emiten paling likuid. `mutu.periksa` sudah menyaring sumbernya sejak langkah 3, tetapi
  `potret`/`metrik`/`saring` — dan daftar kritis di `jalankan_refresh` — belum. Ini bukan cacat
  yang diperkenalkan langkah 6; langkah 6 yang pertama kali **mengukur** akibatnya, karena
  pencatatan cadence memaksa harga pembanding benar-benar ada di basis data.
  **Yang dipakai sekarang:** jangan mengimpor harga pembanding ke folder data yang dipakai
  menyaring. Pertanyaannya diajukan sebagai **P17** di bagian 3. **Sudah diperbaiki pada
  langkah 9** (lihat di bawah): harga dibaca satu label, dan labelnya dilaporkan.
- **Belum dikerjakan pada langkah ini:** cadence **belum** dijadikan penjadwalan otomatis
  (Task Scheduler tetap memanggil `--refresh` harian dan `--cek-sumber-kedua` mingguan secara
  terpisah; aplikasi hanya melaporkan bila minggunya terlewat). Jalan yang "lewat" juga belum
  pernah terlihat pada data nyata — yang membuktikannya uji ber-`momen`, bukan penantian 8 hari.

**Tahap 1 — langkah 7 (kolom `tanggal_notasi`: `Listing Date` KSEI masuk ke berkas rujukan), selesai 9 Okt 2026:**

- Yang ditutup: kolom `tanggal_notasi` sudah ada di tabel `emiten` sejak migrasi 001, tetapi
  **selalu NULL** — tidak ada satu pun jalur yang bisa mengisinya, sebab `emiten.csv` (satu-satunya
  berkas rujukan emiten) belum punya kolomnya. Data yang **ada** di sumber resmi (kolom
  `Listing Date` Master File Efek KSEI) karena itu dibuang setiap kali daftar emiten diambil;
  87 dari 975 barisnya memang kosong di sumber.
- Perubahan menyentuh seluruh rantai, sebab satu kolom yang lupa di salah satu simpul hanya akan
  tampak sebagai "kolom yang selalu kosong" — gejala yang justru sedang diperbaiki: `berkas.py`
  (spesifikasi + pembaca + pesan galat), `ingesti.py` (kontrak `Emiten`, `_ISI_PER_TABEL`, jalur
  tulis), `potret.py` (baca kembali as-of), `ksei.py` (kepala CSV, jalur tulis, penjelasan di
  berkasnya), `arsip.py` (ekspor arsip), serta `defaults/emiten.contoh.csv` dan
  `defaults/emiten-awal.contoh.csv`. Kolomnya **opsional**: berkas rujukan lama tanpa kolom itu
  tetap terbaca dan nilainya NULL, bukan diisi tanggal tebakan.
- **Cacat nyata yang ketahuan dari uji penjaga baru**, bukan dari kecurigaan:
  `imbal_hasil_sun.imbal_hasil_mentah` tidak ikut disidik `_ISI_PER_TABEL` — padahal kolom itulah
  satu-satunya tempat label sumber per baris disimpan (`berkas._baris_sun` menuliskannya di sana).
  Akibatnya impor ulang imbal hasil SUN dengan bp yang sama tetapi teks/sumber berbeda dilaporkan
  "sudah ada dan sama" lalu **dibuang tanpa suara**. Sudah diperbaiki, dan penjaganya sekarang
  memeriksa **setiap** kolom di setiap tabel yang ditulis lewat jalur itu (kecuali kolom kunci) —
  jadi kolom baru di kemudian hari tidak bisa lupa didaftarkan diam-diam.
- Uji: +8 (`tests/test_ksei_emiten.py` +3, `tests/test_impor_berkas.py` +3,
  `tests/test_ingesti.py` +2) — seluruhnya **344 uji lulus**.
- Diverifikasi atas berkas KSEI nyata (diunduh ulang 9 Okt 2026, 973 saham biasa IDX):
  `--ambil-emiten --folder-data .uji-data/uji-tanggal-notasi` menulis **973 baris: 888 terisi,
  85 kosong**, lalu `--impor` memasukkannya ke basis data → `v_emiten_terkini` berisi 888 tanggal
  dan 85 NULL, **tidak ada yang diisi tebakan**. Arsip snapshotnya
  (`arsip-snapshot/2026-10-09/snapshot-1/emiten.csv`) dibandingkan baris per baris dengan basis
  data: **0 selisih**.
- Pemeriksaan kewajaran atas nilainya: rentang **1977-08-10 → 2026-07-10** (tidak ada yang
  melewati tanggal data 30 Sep 2026), sebarannya masuk akal (1 emiten 1970-an, 28 emiten
  1980-an, 317 emiten 2020-an), dan sampelnya **cocok dengan sumber di luar berkas itu**: GOTO =
  11 Apr 2022 sama dengan siaran pers resmi GoTo; BBCA = 31 Mei 2000, sedangkan laporan tahunan
  BCA menyebut penawaran umumnya 11 Mei 2000 — dua peristiwa berbeda, dan yang disimpan di sini
  adalah **tanggal pencatatannya**.
- Berkas rujukan lama (`.uji-data/konfigurasi/emiten.csv`, 916 kode, tanpa kolom baru) **tetap
  terbaca**: 916 emiten, 0 tanggal terisi.
- **Kerapian teks (bukan perubahan perilaku):** glif em dash yang rusak (`â€”`) ditemukan di
  `mejasaham/metrik.py` (10 tempat, seluruhnya komentar/docstring) dan di
  `defaults/emiten-awal.contoh.csv` (1 tempat) — sisa dari berkas yang pernah tersimpan dengan
  penyandian campur. Keduanya dirapikan; tidak ada satu pun pesan yang dibaca pengguna yang
  terkena. Cara memeriksanya dicatat di `docs/lanjutan.md` bagian 6 supaya tidak dikejar lagi.
- **Belum dikerjakan pada langkah ini:** arti nama kolomnya belum dikonfirmasi PRD → pertanyaan
  **P18** di bagian 3 (dipakai sementara sebagai "tanggal pencatatan"). Semesta uji 916 kode juga
  belum ditulis ulang dengan kolom ini — sengaja, berkas itu semesta pilihan pengguna dan
  menimpanya bukan urusan langkah ini.

**Tahap 1 — langkah 8 (pengambil kalender libur bursa dari KSEI, K11), selesai 9 Okt 2026:**

- Yang ditutup: `kalender-bursa.csv` tidak punya jalur otomatis sama sekali, sehingga
  `--muat-konfigurasi`/`--refresh` terus mengeluh `kalender_bursa_kosong` dan peringatan
  "snapshot basi" (AC-8) **tidak bisa dihitung** — padahal IDX menerbitkan kalender libur bursa
  tahunan; hanya saja seluruh `idx.co.id` menolak akses otomatis (403). K11 sudah memutuskan
  sumber penggantinya (KSEI) sejak Tahap 0, tetapi pengambilnya belum pernah ditulis.
- **Berkas sumbernya PDF, dan teksnya dipecah per potongan.** Yang dipakai hanya dua hal:
  aliran isi halaman yang dipadatkan FlateDecode, dan operator teks `TJ`/`Tj`. Keduanya diurai
  dengan `zlib` + `re` dari pustaka standar, jadi **tidak ada dependensi baru** dan K3 tidak
  berubah. Baris tabel disusun ulang dari koordinat `Tm`/`Td`, dan spasi antar potongan
  diputuskan dari perkiraan lebar — dua berkas nyata memakai gaya berbeda (2027 menaruh spasi di
  dalam potongan, 2025 menaruhnya sebagai potongan tersendiri dan memecah kata menjadi `S`+`enin`),
  dan keduanya harus terbaca.
- **Enam pemeriksaan sebelum hasilnya dipakai**, seluruhnya menolak alih-alih menebak: berkasnya
  benar-benar PDF; di dalamnya ada nomor pengumuman KSEI **dan** nomor pengumuman IDX; setiap
  baris lampiran menyebut nama hari yang **cocok** dengan tanggalnya; nomor urut baris tabel
  lengkap `1..N`; seluruh tanggal berada di tahun yang dinyatakan judul berkasnya; dan berkasnya
  menyatakan menindaklanjuti *Kalender Libur Bursa* IDX (T31).
- **Temuan yang mengubah cakupan:** syarat terakhir itu tidak dipenuhi berkas 2025 — berkas itu
  menyebut pengumuman IDX `Peng-00150/BEI.POP/08-2025` tentang *kalender operasional EBA/sukuk*,
  bukan kalender libur bursa. Memakainya berarti memperluas sumber dengan tafsiran sendiri
  (aturan keras 1), jadi **2025 tidak dipakai** dan hal itu dilaporkan di keluaran perintah
  maupun di blok penjelasan berkasnya. Kalender yang lebih pendek lebih baik daripada kalender
  yang memuat tanggal yang bukan urusannya.
- **Temuan kedua:** karena pengumumannya tahunan, kalender kini memuat hari bursa sampai akhir
  tahun — dan `MAX(tanggal) WHERE hari_bursa=1` akan menjawab **2027-12-30** untuk snapshot
  9 Okt 2026, sehingga setiap snapshot yang benar akan diperingatkan "basi" sampai Desember.
  "Hari bursa terakhir" karena itu dibatasi pada hari yang **sudah lewat** (T30). Terukur:
  `sampai=None` → 2027-12-30; `sampai=2026-10-09` → 2026-10-09.
- Kolom `sumber` kalender menjadi **opsional per baris** (seperti `harga_harian`): baris libur
  membawa nomor pengumumannya, baris hari kerja/akhir pekan membawa penanda **turunan**, dan
  baris tanpa sumbernya sendiri tetap memakai label kumpulan seperti sebelumnya.
- Uji: +23 (`tests/test_kalender_ksei.py` 21, `tests/test_ingesti.py` 2) — seluruhnya
  **367 uji lulus**, tanpa jaringan: berkas PDF uji dibangun di dalam uji dengan dua gaya yang
  terukur di atas.
- Diverifikasi atas sumber nyata 9 Okt 2026 (bukti di `.uji-data/uji-kalender/`):
  `--ambil-kalender --timpa-kalender --folder-data .uji-data` menulis **730 baris** (2026: 22
  libur resmi, 239 hari bursa; 2027: 20 libur resmi, 241 hari bursa), **730 terbaca ulang** oleh
  pembaca `--impor`. Impor lalu **idempoten** (jalan kedua: *0 baris baru, 1646 sudah ada dan
  sama*). Laporan mutu sesudahnya: **hari bursa terakhir 2026-10-09** — sama dengan tanggal
  snapshot, dan **tidak ada** temuan `kalender_bursa_kosong`, `kalender_belum_memuat`, maupun
  `snapshot_basi`. Bukti: `bukti-ambil-kalender.log` (keluaran perintah), `bukti-keadaan.txt`
  (isi basis data + temuan mutu), `bukti-isi-kalender.txt` (42 baris libur resmi beserta
  keterangan dan nomor pengumumannya).
- **Belum dikerjakan pada langkah ini:** kalender 2021–2025 tidak ada (berkas tahun-tahun itu
  sudah tidak dipasang lagi di halaman KSEI, dan yang 2025 pun tidak memenuhi syarat T31); libur
  yang ditiadakan mendadak tetap tidak diketahui; penjadwalan pengambilan ulang kalender masih
  manual (seperti cadence cek sumber kedua, langkah 6).

**Tahap 1 — langkah 9 (satu label sumber harga per snapshot: cacat P17 ditutup), selesai 9 Okt 2026:**

- Yang ditutup: begitu harga pembanding (PRD 7.3) diimpor, **angka saringan rusak diam-diam**.
  `penyesuaian.sesuaikan` mengurutkan bar berdasarkan tanggal saja, sehingga dua bar tanggal sama
  dari dua sumber masuk ke satu deret; hari yang terduplikasi memakan slot jendela 20 hari dan
  ADTV20 emiten itu jatuh "tidak dihitung". Terukur waktu itu: semesta likuid **235 → 215**,
  tepat pada 20 emiten yang diberi pembanding. Cacat ini bukan diperkenalkan langkah 6 —
  langkah 6 yang pertama kali **mengukur** akibatnya.
- `mejasaham/potret.py` — **aturan tunggal** `riwayat_sumber` (label dengan jumlah bar terbanyak,
  seri diputus menurut abjad) dan `sumber_utama`; `muat(sumber=...)` menyaring `harga_harian` ke
  satu label **di dalam SQL** (menyaringnya di Python berarti membaca sejuta baris lebih dulu),
  lalu menyimpan hasilnya di `Potret.sumber_harga` dan seluruh label di `Potret.sumber_tersedia`
  (dengan `sumber_diabaikan` dan `bar_sumber_harga` sebagai turunannya). Pilihannya dihitung
  **pada saat snapshot** (`diketahui_pada <= batas`), jadi label yang baru diimpor tidak mengubah
  isi snapshot lama. Label yang tidak punya satu bar pun **ditolak berisik** sambil menyebut label
  yang ada — potret tanpa harga akan terbaca sebagai "emitennya belum punya data", padahal yang
  salah nama labelnya.
- `mejasaham/pengatur.py` — `jalankan_saring(sumber=...)` + laporan menyebut label yang dipakai
  dan yang tidak dipakai, dan adanya label kedua menjadi **peringatan** (angka dari dua sumber yang
  bercampur terlihat sama sehatnya di layar); `jalankan_refresh` mengisi daftar kritis PRD 9.3 dari
  **satu** label; `cek_sumber_kedua` berhenti menulis kueri pemilihan labelnya sendiri dan memanggil
  `potret.sumber_utama` — aturan yang sama, satu tempat.
- `mejasaham/cli.py` — `--sumber LABEL` sebagai penimpa pilihan bawaan.
- Keputusan teknisnya dikunci sebagai **T32** di `docs/arsitektur.md`; **P17 tetap terbuka**
  (bagian 3) karena yang diputuskan manusia adalah *bentuk* aturannya, bukan ada-tidaknya aturan.
- Uji: `tests/test_sumber_harga.py` (9 uji) — seluruhnya **377 uji lulus**. Dua di antaranya adalah
  uji regresi yang diminta `docs/lanjutan.md`, dan keduanya **dibuktikan gagal pada kode lama**
  sebelum diperbaiki: dengan penyaringan label dinonaktifkan sementara, likuid jatuh **10 → 0**
  (pembanding tanpa volume) dan ADTV20 naik diam-diam **Rp 10 miliar → Rp 10,5 miliar**
  (pembanding bervolume, 19 hari utama + 1 bar pembanding pada hari yang sama). Angka 10,5 itu
  hasil ukur, bukan perkiraan — perkiraan pertama saya (Rp 11 miliar) salah dan dikoreksi uji.
- Diverifikasi atas **data nyata**, pada salinan basis data yang sama dengan bukti langkah 6
  (`.uji-data/uji-p17/`): label `yfinance/Yahoo Finance (tidak resmi)` 999.421 bar vs
  `pembanding-uji` 21 bar. `--saring` menjawab **likuid 235** dari 916 emiten — angka yang sama
  dengan sebelum harga pembanding diimpor — dan breadth kembali 38,3% (dari 39,5%); keluarannya
  juga menyebut label yang dipakai beserta jumlah barnya. Bukti: `bukti-saring-p17.txt`.
  `--cek-sumber-kedua` pada basis data yang sama keluarannya **identik** dengan bukti lama
  (`bukti-cek-sumber-p17.txt`), jadi pemindahan aturan pemilihan label tidak mengubah perilakunya.
- **Yang ketahuan dan dicatat apa adanya:** peringkat ADTV20 20 teratas ternyata **sudah sama**
  sebelum dan sesudah pembanding diimpor pada data nyata itu (0 dari 20 baris berbeda). Sebabnya
  kueri peringkat memakai `COUNT(DISTINCT tanggal)` dan `AVG` yang mengabaikan `NULL`, sedangkan
  bar pembanding di sana diimpor tanpa nilai transaksi. Jadi cacat ini tidak terlihat dari daftar
  kritis PRD 9.3 **pada data itu**; ia muncul di jalur deret yang dipakai `--saring`. Penyaringan
  label di `jalankan_refresh` tetap dipasang, sebab bentuk yang sama berubah menjadi salah begitu
  pembanding memuat nilai transaksi — terbukti di uji sintetis, bukan diduga.
- **Belum dikerjakan pada langkah ini:** bentuk akhir aturan P17 masih menunggu jawaban Anda
  (opsi (b) "pilih per snapshot" bisa ditambahkan tanpa membongkar apa pun); ambang "label
  dominan" berupa angka **sengaja tidak dibuat** karena angkanya tidak berasal dari PRD mana pun —
  yang dipakai adalah aturan yang sepenuhnya menentukan jawaban **ditambah** pelaporan yang tidak
  bisa dilewatkan. Penjadwalan otomatis tidak berubah.

**Tahap 1 — langkah 10 (imbal hasil SUN punya sumber otomatis; P17 & P18 dikonfirmasi), selesai 9 Okt 2026:**

- Yang ditutup: `imbal-hasil-sun.csv` tidak punya jalur otomatis sama sekali, sehingga metrik
  "imbal hasil laba − SUN" (PRD 8.2) selalu berstatus "tidak dihitung". Pemicunya permintaan
  pengguna 9 Okt 2026: **"cari atau bikin berkas yang dibutuhkan sendiri"** — jadi yang dikerjakan
  adalah penelusuran sumber yang **terukur**, bukan mengarang isi berkas.
- **Penelusuran sumber, dengan hasil apa adanya** (tabel 5.1 diperbarui):
  - **PHEI — bisa.** Halaman HPW (`phei.co.id/Data/HPW-dan-Imbal-Hasil`, HTTP 200) memuat kurva
    imbal hasil SBN per tenor sebagai **tabel HTML biasa**, lengkap dengan pernyataan tanggal
    valutasinya sendiri ("per 9-Oktober-2026"). Terukur: **SUN 10 tahun = 7,1845%**.
  - **Bank Indonesia — tidak (dari jaringan ini).** `bi.go.id` memutus koneksi
    (`ConnectionResetError [WinError 10054]`) pada beranda maupun halaman indikator.
  - **DJPPR — tidak.** Rute API-nya **dibaca dari bundel aplikasinya** (`assets/js/env.js` →
    `api-djppr.kemenkeu.go.id/web/api/v1`), bukan ditebak: ternyata CMS (`/page?url=...`,
    `/formdata`, `/repeater/filter`) yang mengembalikan JSON widget, tanpa berkas deret imbal hasil.
  - **IDX — tetap tidak.** Tiga jalur yang memuat fundamental (`StaticData/ListedCompanies/…`,
    `StaticData/NewsAndAnnouncement/`, `primary/StockData/GetSecuritiesStock`) membalas **403**.
- Keputusan **K16** dikunci: kurva imbal hasil SBN dari **PHEI**, kolom **Today**, tenor **10**.
  Kolom "Yesterday" sengaja tidak dipakai — halamannya menyatakan **satu** tanggal valuasi, dan
  tanggal "kemarin" tidak dinyatakan di mana pun.
- `mejasaham/sun.py` (baru) — unduh → urai → **tambah satu baris** ke `imbal-hasil-sun.csv`, lalu
  berkasnya dibaca `--impor` seperti berkas impor lain (penulis basis data tetap satu jalur).
  Enam penolakan yang eksplisit, semuanya menyebut sebabnya: halaman tanpa tabel tenor; halaman
  tanpa pernyataan tanggal valuasi; halaman dengan **dua tanggal berbeda** (tidak diringkas);
  tenor 10 tidak ada; tenor 10 muncul di dua tabel; dan nilai di luar batas wajar
  (0,01–30%). Kolom dikenali dari **kepala tabel** (`Tenor` + `Today`), bukan dari urutannya —
  halaman yang menambah tabel baru tidak boleh menggeser arti kolomnya.
- **Berkasnya bertambah, bukan ditimpa**: baris lain dipertahankan apa adanya (termasuk suntingan
  tangan dan riwayat dari publikasi lain), dan hanya baris `(tanggal, tenor)` yang sama yang
  diperbarui. Karena itu perintah ini **tidak punya** `--timpa-sun` — berbeda dari
  `--ambil-kalender` yang menulis ulang seluruh berkas. Nama berkasnya kini satu tempat
  (`berkas.NAMA_BERKAS_SUN`), sama seperti `NAMA_BERKAS_KALENDER`.
- `mejasaham/cli.py` — perintah baru `--ambil-sun`; `--impor` tetap jalur masuk ke basis data.
- Uji: `tests/test_sun_phei.py` (17 uji, seluruhnya **tanpa jaringan** — pembuka jaringan
  disuntikkan sebagai fungsi palsu) — seluruhnya **394 uji lulus**. Uji terpentingnya bukan
  "unduhannya jalan", melainkan bahwa tanggal diambil dari pernyataan sumbernya dan bahwa hasil
  tulisannya bisa dibaca `berkas.baca_folder` (bulat-balik lewat pembaca sebenarnya).
- Diverifikasi atas **sumber nyata** 9 Okt 2026: `--ambil-sun --folder-data .uji-data/uji-sun`
  menulis satu baris untuk **SUN 10 tahun = 7,1845% per 09 Okt 2026**; berkasnya diimpor ke
  salinan basis data 916 emiten → `imbal_hasil_sun_terakhir` = **718 bp**, dan alasan metriknya
  **berubah** dari "imbal hasil SUN 10 tahun belum ada di basis data" menjadi "belum ada laporan
  fundamental untuk emiten ini" — bukti bahwa SUN kini masuk perhitungan, dan bahwa yang tersisa
  memang berkas fundamental. Peringatan `--saring` tentang SUN **hilang**. Bukti:
  `.uji-data/uji-p17/bukti-saring-sun.txt`.
- **Batas yang dicatat apa adanya:** (a) 7,1845% tersimpan sebagai **718 bp** karena kolom basis
  poin `INTEGER` **memotong**, bukan membulatkan — presisinya tetap terjaga di
  `imbal_hasil_mentah` (`7.1845 | PHEI … teks asli '7,1845'`); (b) halaman PHEI menyajikan nilai
  **hari itu** saja, jadi riwayat sebelum pengambil ini ada **tidak bisa** diisi dari sini, dan
  berkasnya tumbuh satu baris per jalan; (c) temuan "BI memutus koneksi" berlaku untuk **satu
  jaringan**, seperti temuan `idx.co.id` sebelumnya.
- **Belum dikerjakan:** `fundamental.csv`, `rasio-bank.csv`, dan `notasi-khusus.csv` **tetap tidak
  bisa** diambil otomatis (403 pada seluruh jalur IDX; KSEI tidak menerbitkan laba/ekuitas/arus
  kas) — jadi berkas itu tetap pekerjaan manusia (P2/U3), dan metrik yang bergantung padanya tetap
  "tidak dihitung" sampai berkasnya ada. Kalender **2021–2024** juga tetap kosong: berkasnya sudah
  **404** di KSEI, dan Arsip Internet hanya menyimpan salinan **terbaru** halaman itu (setiap
  percobaan `web.archive.org/web/<tahun>id_/…` mengembalikan halaman yang sama dengan tautan hari
  ini); API `archive.org/wayback/available` membalas 429 pada semua percobaan.
- **Temuan tambahan yang perlu keputusan Anda (belum diubah perilakunya):** untuk **2025** ada
  **dua** revisi pengumuman KSEI di server — yang ditautkan halaman sekarang,
  `Pengumuman_Perubahan_Kedua_…_Tahun_2025.pdf` (KSEI `PENG-0007/DIR/KSEI/1225`, IDX
  `Peng-00150/BEI.POP/08-2025`), **ditolak** syarat T31 karena tidak menyatakan menindaklanjuti
  *Kalender Libur Bursa*; dan versi sebelumnya, `Pengumuman_Perubahan_…_Tahun_2025.pdf` (KSEI
  `PENG-0004/DIR/KSEI/0825`, IDX `Peng-00149/BEI.POP/08-2025`), yang **lulus** T31 dengan **25
  tanggal libur**. Keduanya dibandingkan tanggal per tanggal: **25 tanggalnya identik**; satu-satunya
  beda adalah perbaikan salah ketik pada satu keterangan ("Cuti Bersama Tahun Baru Imlek
  257 6 Kongzili" → "2576 Kongzili"). Artinya tanggal libur bursa 2025 **sudah diketahui dan
  dikuatkan dua dokumen** — yang belum ada adalah berkas yang memenuhi T31 **dan** sekaligus revisi
  terakhir. Perilakunya **sengaja tidak diubah** sebelum Anda menjawab: memakai dokumen yang sudah
  digantikan adalah keputusan sumber, bukan keputusan teknis, jadi pertanyaannya diajukan ke Anda
  (bagian 3.5).
- **Tambahan pada langkah ini: P19 disetujui pengguna dan dikerjakan → K17.** Aturannya ketat dan
  bisa diperiksa: revisi lama dipakai **hanya bila** berkas yang ditautkan ditolak semata-mata oleh
  syarat T31, revisi lama lulus **seluruh** pemeriksaan, dan himpunan tanggal liburnya **sama
  persis**; satu tanggal berbeda → ditolak, tahunnya tetap kosong. Keterangan yang berbeda tidak
  menolak tetapi dilaporkan (pada berkas nyata 2025: **1 keterangan**, perbaikan salah ketik).
  Alamat revisi lama diturunkan dari **nama berkas** yang ditautkan dengan melepas penanda revisi
  (`_Kedua`, lalu `_Perubahan`), maksimum 3 kandidat; setiap kandidat tetap harus lulus syarat di
  atas. `urai_kalender` menerima `wajib_tindak_lanjut=False` **hanya** untuk mengurai berkas yang
  ditolak sebagai bahan pembanding — hasil bertanda itu tidak pernah dipakai sebagai kalender.
  Seluruh percobaan dilaporkan (`catatan_revisi`, ditulis juga di blok penjelasan berkas), dan bila
  semua tahun gagal, pesan kegagalannya ikut memuat percobaan revisi itu. **Terukur sesudahnya atas
  sumber nyata:** `--ambil-kalender --timpa-kalender --folder-data .uji-data` memuat **2025 (25
  libur) + 2026 (22) + 2027 (20) = 1095 baris**, terbaca ulang 1095; `--impor` menulis 365 baris
  baru, dan tanggal 2025 di basis data membawa sumber
  `PENG-0004/DIR/KSEI/0825 (menindaklanjuti IDX Peng-00149/BEI.POP/08-2025)`. Laporan mutu berhenti
  memuat temuan kalender untuk 2025. Bukti: `.uji-data/uji-kalender-2025/`. Uji: **+6 → 400 lulus**,
  termasuk uji bahwa revisi lama **tidak dicari** ketika berkas yang ditautkan rusak lebih dalam —
  dibuktikan dari daftar alamat yang benar-benar diminta, bukan dari pesannya saja.

**Belum dikerjakan (sengaja):**

- Belum ada logika: risiko, jurnal, ekspor, cadangan. Daftar modul yang belum ada di
  `arsitektur.md` bagian 3.
- Belum ada `kandidat`, `rencana`, `transaksi`, `posisi`, `ekuitas_harian`, `jurnal`
  (migrasi 007+, Tahap 2–3).
- Panel jendela untuk screener (F2) belum ada; `--saring` baru mode kepala (Tahap 2).
- Isian parameter bursa B1–B9 masih menunggu pengumuman resmi (`konfigurasi.md` bagian 2);
  sampai terisi, `--muat-konfigurasi` melaporkannya sebagai "belum terverifikasi" dan fitur
  yang bergantung padanya akan menolak menghitung.
- **Penjadwalan cadence belum otomatis.** Sejak langkah 6, "tiap minggu" (PRD 7.3) **bisa
  diperiksa** dan diperingatkan, tetapi yang memanggil `--cek-sumber-kedua` tetap manusia
  (atau Task Scheduler); aplikasi tidak menjadwalkan sendiri.

- **Pengambil otomatis kalender bursa dari KSEI (K11) sudah ada** sejak langkah 8
  (`--ambil-kalender`). Yang tetap menunggu manusia: kalender 2021–2025 tidak tersedia lagi di
  halaman KSEI (2025 ada, tetapi tidak memenuhi syarat sumber T31), dan impor berkas tetap jalur
  sah untuk tahun-tahun itu bila Anda punya pengumumannya.
- P13–P16 (perilaku produk) masih terbuka. Yang **sudah** dipakai sementara: aturan PRD 7.3
  "fundamental lebih tua dari 18 bulan disembunyikan" ditafsirkan dihitung dari `tgl_publikasi`
  terhadap tanggal snapshot (usulan P13) — dan itu akan dikonfirmasi saat Anda menjawabnya.
- **Yang masih menunggu Anda:** (a) daftar emiten resmi dari idx.co.id **sebagian terjawab K12**
  (975 kode sudah bisa diambil dari KSEI, tetapi **tanpa sektor IDX-IC dan tanpa papan pencatatan**
  — dua kolom itu hanya IDX yang menerbitkan), (b) berkas kalender bursa — **terjawab langkah 8**:
  `--ambil-kalender` mengisinya dari pengumuman KSEI (2026 & 2027; tahun lebih lama tidak lagi
  tersedia di sana), (c) daftar notasi khusus/suspensi — **satu-satunya butir yang benar-benar
  tidak punya sumber terjangkau**, lihat 5.1, (d) imbal hasil SUN dari publikasi resmi, (e) berkas
  fundamental + rasio bank (tanpa itu faktor kualitas & nilai "tidak dinilai"), dan (f) persetujuan
  bobot preset `momentum/v1`. Butir "keputusan C10 sebelum Tahap 1" **sudah dijawab** 9 Okt 2026 →
  K8, bukti di 1.5.
- Tahap 0 belum dinyatakan selesai: kriteria keluarnya (PRD 16) menuntut "data 800+ emiten
  tersedia untuk 5 tahun terakhir" — **daftarnya kini ada (973 kode, K12)**, tetapi **datanya
  belum**: harga 5 tahun untuk ~973 emiten belum pernah diambil, dan itu `--refresh` yang panjang
  (ratusan permintaan berjeda ke sumber tidak resmi).

**Tahap 1 — langkah 12 (riset tarif broker Stockbit + batas jalur peramban IDX), 10 Okt 2026:**

Tanpa perubahan kode; seluruh uji **422 lulus**. Dua pekerjaan yang tidak saling bergantung, dua
hasil yang berbeda sifatnya — satu selesai, satu berhenti di batas yang kini terukur.

- **Tarif broker (B6/B7) — selesai diriset, belum bisa dimuat, dan sebabnya bukan tarifnya.**
  Halaman resmi Stockbit (`https://stockbit.com/`, blok "Biaya Normal", HTTP 200 lewat DOM
  ter-render; badan `web_fetch` kosong karena SPA) menyatakan `Fee Beli 0,15%` / `Fee Jual 0,25%`,
  beserta kalimat yang menentukan artinya: *"Sudah termasuk biaya broker, biaya levy (BEI, KPEI,
  KSEI) 0,043%, PPN biaya broker 10%, dan PPh final untuk transaksi jual 0,1%"*. Badan sekuritas:
  **PT Stockbit Sekuritas Digital**. Yang **tidak** dinyatakan sumbernya: **tarif minimum** dan
  **tanggal berlaku** (hanya ada "Diperbarui pada: 05/08/2026" pada artikel bantuan — dan
  "diperbarui" bukan "berlaku sejak"). Karena bentuk entri `[[biaya_broker]]` menuntut keduanya,
  memuatnya hari ini memaksa satu angka karangan (`minimum = 0`, atau `berlaku_sejak` tebakan),
  jadi entrinya **sengaja tetap dikomentari** → **U20**. Satu bahaya yang ikut terungkap: tarif itu
  **all-in**, sehingga tanpa penanda tersimpan, kalkulator biaya Tahap 2 akan menambahkan B8 (PPh
  final 0,1%, entri yang **sudah ada** di draf) di atas tarif yang sudah memuatnya → **U21**.
  Bukti + kutipan verbatim: `.uji-data/riset-tarif-broker/stockbit.md`.
- **Jalur peramban ke IDX — terobosan yang sekaligus menunjukkan batasnya.** Chromium sungguhan
  membalas **HTTP 200** untuk `https://www.idx.co.id/id` (judul "PT Bursa Efek Indonesia", 44
  tautan, `cf_clearance` terbit). Ini jalur yang selama 7 penelusuran sebelumnya tidak ada. Tiga
  batas terukur yang membuatnya **belum** bisa dipakai aplikasi: (a) `requests` Python tetap **403**
  sekalipun membawa seluruh cookie itu dengan User-Agent yang sama; (b) **burst diblok** — beberapa
  navigasi cepat memicu *"Sorry, you have been blocked"* (blok, bukan tantangan), dan jeda 75 detik
  + mundur 120 detik **tidak memulihkannya** dalam >15 menit; (c) `www2.idx.co.id` (halaman resmi
  *Special Notation*) membalas **403 sekalipun dengan peramban**. Jadi P22 tidak selesai, tetapi
  pertanyaannya berubah bentuk: bukan lagi "jalur mana yang belum dicoba", melainkan "bolehkah
  aplikasi bergantung pada peramban" — dan itu pertanyaan Anda. Bukti:
  `.uji-data/riset-idx/` (`permukaan-api.json`, `jelajah.json`).
- **Jebakan lingkungan baru (sudah masuk `docs/lanjutan.md` bagian 6):** `pytest` gagal massal
  (`PermissionError: [WinError 5]`) ketika folder sementara lama `pytest-of-<user>` menjadi tidak
  bisa diakses sama sekali — 163 lulus/**259 error** tanpa satu pun perubahan kode; obatnya adalah
  **folder sementara baru** setiap jalan (`.tmp\t2` → 422 lulus). Dan `browserType.launch: spawn
  EPERM` di sesi bersandbox (pipa `--remote-debugging-pipe` ditolak), dengan dua jalan keluar yang
  terverifikasi: akses penuh, atau jalankan peramban sendiri + `chromium.connectOverCDP`.
- **Belum dikerjakan:** memuat `[[biaya_broker]]` (menunggu U20/U21); menurunkan `jenis` dari data
  (K21 — sudah diizinkan, aksi 1b); `notasi-khusus.csv` & `rasio-bank.csv` (P22 — jalur (b) sumber
  pihak ketiga dan (c) aggregator belum diuji).

**Tahap 1 — langkah 13 (K22/K23 dimuat; `jenis` emiten diturunkan dari data), 10 Okt 2026:**

Dua pekerjaan yang menunggu jawaban Anda sejak langkah 12, keduanya selesai di sini. Seluruh uji
**477 lulus** (422 → 477; 55 uji baru).

- **B6/B7 akhirnya dimuat tanpa satu pun angka karangan (K22, K23).** Yang menghalangi selama ini
  bukan tarifnya, melainkan **bentuk penyimpanannya**: halaman tarif Stockbit tidak menyatakan
  tarif minimum maupun tanggal berlaku, jadi memuatnya memaksa satu karangan. Dua keputusan
  menutupnya, dan keduanya *mengubah bentuk*, bukan mengubah angka:
  - **K22 — "tidak dinyatakan sumber" adalah keadaan yang sah.** Migrasi 008 menambahkan
    `parameter_bursa.asal_berlaku_sejak` (`'sumber'` bawaan / `'tanggal_pengamatan'`) dan
    **mencabut `NOT NULL`** pada `parameter_biaya_broker.minimum_beli`/`minimum_jual`. Yang
    tersimpan `NULL`, dan `NULL` **bukan 0**: nol berarti "tidak ada tarif minimum" — pernyataan
    tentang bursa yang halaman itu tidak buat. Perbedaannya diuji, bukan diandaikan.
  - **K23 — tarif all-in menyimpan penandanya di entri.** `sudah_termasuk = ["levy", "ppn",
    "pph_penjualan"]`, disimpan sebagai baris di tabel `parameter_biaya_broker_termasuk`. Tanpa
    ini, tarif jual 0,25% yang **sudah** memuat PPh final 0,1% akan ditambahi B8 lagi: salah dua
    kali, dan tidak terlihat di keluaran mana pun — hanya di angkanya.
  - **Rebuild tabel, bukan `ALTER`.** SQLite tidak bisa mencabut `NOT NULL`, jadi tabelnya
    dibangun ulang **di dalam migrasi 008** (migrasi 002 tidak disentuh, T9). Karena tabelnya
    ber-FOREIGN KEY, `PRAGMA foreign_keys` dimatikan hanya selama rebuild, dan dua penjaga jumlah
    baris dipasang **sebelum** tabel lama dibuang — rebuild yang kehilangan baris menghasilkan
    skema yang rapi tetapi salah, dan itu kegagalan yang tidak berisik (T34).
  - Bukti terukurnya: `--muat-konfigurasi` berhenti menandai `biaya_broker` dan `slippage`
    sebagai `belum_terverifikasi` (sebelum: keduanya `belum_terverifikasi`; sesudah: keduanya
    `dipakai`, kode keluar 0, dan tidak ada angka yang tidak dinyatakan sumbernya). Keluarannya
    disimpan di `.uji-data/bukti-muat-konfigurasi-sebelum.txt` dan `…-sesudah.txt`.
- **`jenis` emiten diturunkan dari data (K21), dan pembagiannya dilaporkan.** Perintah baru
  `--ambil-jenis` menurunkan **hanya `bank_keuangan`** dari `sector`/`industry` yang dinyatakan
  sumber data, menulis `emiten.csv` yang bisa diperiksa manusia lebih dulu, lalu `--impor` yang
  memasukkannya — pola yang sama dengan K11/K12/K16/K18, sehingga penulisan basis data tetap satu
  jalur. Aturan penurunannya satu **fungsi murni** di `mejasaham/jenis.py`, jadi bisa diuji tanpa
  jaringan; `siklikal_komoditas` **tidak pernah** dihasilkan (itu penilaian, bukan fakta sumber);
  emiten yang sumbernya tidak menyatakan sector/industry **tetap kosong** (bukan `umum`); dan
  `jenis` yang sudah terisi **tidak ditimpa**, sehingga isian manusia — satu-satunya nilai yang
  tidak bisa dihasilkan mesin — tidak hilang. `--saring` sekarang membedakan tiga keadaan
  (bank dari data · umum dari data · belum terisi) alih-alih satu angka "belum terisi", sebab
  begitu `jenis` terisi, aturan yang berlaku **berubah**: kriteria bank mulai diterapkan dan
  DER/coverage/CFO-NI berhenti dihitung untuk bank (PRD 8.4, AC-16).
- **Satu cacat yang ditemukan dan ditutup saat mengerjakan ini:** menambahkan `asal_berlaku_sejak`
  ke sidik jari entri membuat **seluruh entri yang sudah terpasang** gagal idempoten dengan pesan
  "isi yang berbeda" — padahal isinya sama persis, yang berubah hanya cara aplikasi menghitung
  sidiknya. Pesan itu akan menyuruh pengguna memperbaiki berkas yang tidak salah. Sidik jarinya
  dikembalikan ke bentuk semula, dan **pemeriksaan asal tanggal dipisah** menjadi pemeriksaannya
  sendiri: entri dengan `berlaku_sejak` dan `dicatat_pada` sama tetapi `asal_berlaku_sejak`
  berbeda tetap **ditolak berisik** — "berlaku sejak 10 Okt" bukan "diamati pada 10 Okt" — dengan
  pesan yang menyebut sebabnya, bukan "isi berbeda".
- **Jebakan baru (sudah masuk `docs/lanjutan.md` bagian 6):** `RAISE(ABORT, …)` **hanya sah di
  dalam program trigger**. Penjaga keutuhan yang ditulis sebagai `SELECT RAISE(...) WHERE …` di
  dalam skrip migrasi gagal dengan `RAISE() may only be used within a trigger-program`, dan
  karena `executescript` membatalkan seluruh migrasi, gejalanya muncul sebagai "migrasi 008 gagal"
  — bukan sebagai penjaga yang tidak bekerja. Bentuk yang bekerja: trigger sementara.
- **Belum dikerjakan:** `notasi-khusus.csv` & `rasio-bank.csv` (P22 — jalur (b) dan (c) belum
  diuji; peringkat masih berstatus "sementara"); kalkulator biaya yang **memakai** `sudah_termasuk`
  (Tahap 2); kalender 2021–2024.

### Tahap 2 — langkah 1: kandidat & watchlist (F4, AC-4), 10 Okt 2026

Pintu masuk Tahap 2, dan sengaja dimulai dari sini: PRD 9.7 menghitung stop bawaan dari
**harga pembatal tesis**, jadi kalkulator risiko (F5) butuh entri kandidat lebih dulu. Yang
dikerjakan:

- **Migrasi 009** (`kandidat_watchlist`): tabel `kandidat` berkunci `id_kandidat` + `revisi`,
  append-only, dengan `CHECK` yang menegakkan AC-4; trigger penolak `UPDATE`/`DELETE`;
  `v_kandidat_terkini`. Rinciannya di `docs/skema-data.md` 5.9.
- **`mejasaham/kandidat.py`**: `buat`, `ubah`, `tinjau`, `daftar`, `riwayat`, `terkini`,
  `kedaluwarsa`, `saran_tanggal_tinjau`. Entri **ide** boleh dicatat tanpa tesis; perpindahan ke
  `watchlist` menuntut kelima kolom wajib; `dibuang` menuntut alasan dan bersifat final.
- **Perintah baru** (mode kepala, AC-11): `--kandidat-baru`, `--kandidat-ubah`, `--tinjau-ulang`,
  `--watchlist`, beserta `--tesis`, `--pembatal`, `--horizon`, `--stop-awal`, `--harga-pembatal`,
  `--target`, `--tinjau`, `--jadi`, `--alasan`, `--status-tampil`.
- **Uji**: `tests/test_kandidat.py` (23 uji), seluruhnya **505 lulus**. Salah satunya menembak
  basis data langsung untuk membuktikan AC-4 ditegakkan `CHECK`, bukan hanya oleh modul.
- **Bukti atas data nyata**: `.uji-data/uji-kandidat/bukti-kandidat.txt` — dijalankan atas
  **salinan** basis data uji (`.uji-data/mejasaham.db` tidak disentuh), memperlihatkan penolakan
  watchlist tanpa kolom wajib (kode keluar 1), penerimaan setelah dilengkapi, dan tiga revisi
  yang semuanya masih tersimpan.
- **Dua cacat ditemukan saat menjalankan perintahnya**, bukan saat membaca ulang kode, dan
  keduanya sudah ditutup (**T37** di `docs/arsitektur.md`): (1) `v_kandidat_terkini` semula
  dibangkitkan dengan pembeda stempel waktu, sehingga dua revisi dalam **detik yang sama** tidak
  terbedakan dan yang terbaca kembali justru revisi lama — status tetap `ide` sesudah dipindahkan
  ke `watchlist`; (2) `--tinjau-ulang` menolak tinjauan yang tepat waktu karena tanggal saran
  kebetulan sama, padahal tinjauan itu peristiwa yang dihitung PRD 13.1.
- **Belum**: kalkulator risiko (F5, `rencana`), dasbor "tindakan menunggu" (P16), panel jendela,
  penanda "fundamental baru masuk → tinjau pembatal" (PRD 9.6 kalimat terakhir), dan jawaban
  **P23** (arti `tanggal_tinjau`).

### Tahap 2 — langkah 2: kalkulator risiko & ukuran posisi (F5, PRD 9.7), 10 Okt 2026

Langkah 1 menghasilkan tesis dan watchlist; langkah ini yang mengubahnya menjadi **ukuran posisi
yang boleh dibeli** — dan PRD 9.7 menyebutnya "pintu wajib sebelum rencana disimpan" (PRD 2.3:
"Risiko dihitung belakangan" adalah salah satu masalah yang produk ini selesaikan). Yang dikerjakan:

- **Migrasi 010**: `preset_risiko` + `preset_risiko_nilai` (batas risiko berversi), `ekuitas_harian`
  (F11 dasar, masukan PRD 9.7), `rencana` (keluaran kalkulator, PRD 8.1) — seluruhnya append-only
  dengan `v_rencana_terkini`/`v_ekuitas_harian_terkini`. Rinciannya di `docs/skema-data.md` 5.10.
- **`mejasaham/risiko.py`**: rumus PRD 9.7 apa adanya — `lembar mentah = (ekuitas × risiko per
  posisi) ÷ (harga masuk − stop + biaya & slippage per lembar)`, ukuran akhir = nilai terkecil dari
  lembar mentah, batas bobot, batas sektor, batas likuiditas, dan kas tersedia, dibulatkan ke bawah
  per lot; risiko nominal dihitung dari ukuran **akhir**. Stop bawaan = nilai terbesar antara
  `harga masuk − 2 × ATR14` dan harga pembatal tesis. Hitungannya dipisah dari pembacaan basis data
  (`hitung()` murni), dan `metrik.atr14_rupiah()` ditambahkan supaya rumus ATR hanya ditulis sekali.
- **Perintah baru** (mode kepala, AC-11): `--batas-risiko-bawaan`, `--ekuitas-harian [--kas]`,
  `--hitung-risiko KODE` (+ `--harga-masuk`, `--stop`, `--jenis-stop`, `--broker`, `--ekuitas`,
  `--kas`, `--simpan-rencana`, `--rencana-revisi`, `--pakai-ukuran-patuh`, `--terima-pelanggaran`),
  dan `--rencana`.
- **Kalkulator biaya memakai penanda *all-in* (K23) — yang selama ini jadi pekerjaan terbuka.**
  Sisi jual **tidak** menambahkan PPh final 0,1% bila sumber menyatakan tarifnya sudah memuatnya;
  sisi beli tidak pernah menambahkannya. Diuji dua arah (dengan dan tanpa penanda), sebab yang
  salah hanya terlihat di angkanya. Rinciannya **T39** di `docs/arsitektur.md`.
- **Batas risiko jadi pengaturan berversi** (PRD 8.3): nilai awalnya PRD 9.7 (0,75% / 10% / 30% /
  2% ADTV20 / 5%), disimpan sebagai baris di `preset_risiko` — **bukan konstanta di kode** — dan
  `rencana` menyimpan `id_preset_risiko` yang benar-benar dipakainya (**T38**).
- **Perilaku menolak PRD 9.7 dikerjakan, bukan hanya ditampilkan**: rencana yang melanggar batas
  total risiko **tidak bisa disimpan** sampai pengguna memilih — memakai ukuran yang patuh
  (`--pakai-ukuran-patuh`, seluruh angka turunan dihitung ulang) atau menerima pelanggarannya
  secara tercatat (`--terima-pelanggaran`, alasannya masuk kolom `catatan`).
- **Uji**: `tests/test_risiko.py` (62 uji), seluruhnya **567 lulus**.
- **Bukti atas data nyata**: `.uji-data/uji-risiko/` — salinan bersih `.uji-data/mejasaham.db`
  (999.421 bar, 916 emiten, 7 snapshot). Terukur 10 Okt 2026 di atas TLKM (penutupan 2.320,
  ATR14 Rp 66,18): stop bawaan 2.180 (2187,6 dibulatkan **ke bawah** ke tick sah), biaya beli +
  slippage Rp 14/lembar (0,15% → 4, dibulatkan ke atas; 1 tick → 10), ukuran mentah 12.224 lembar
  → **10.800 lembar** karena batas bobot 10%, risiko nominal Rp 1.663.200 (0,66% ekuitas), dan
  `--simpan-rencana` memindahkan kandidat ke status `rencana`. Bukti pelanggaran: ASII dengan
  ekuitas 36 juta dan TLKM sudah berjalan → total 5,06% > 5%, simpan **ditolak** (keluar 1),
  ukuran patuh 600 lembar disimpan, lalu revisi 2 dengan pelanggaran diterima tersimpan sebagai
  **544 bp**.
- **Dua cacat ditemukan saat menjalankannya**, keduanya sudah ditutup: (1) pagu kas **dibagi harga
  dua kali**, sehingga batas kas selalu 0 lembar dan rencana apa pun tertahan dengan alasan yang
  salah — ditemukan karena angkanya diperiksa tangan, bukan karena ada galat; (2) `ekuitas_harian`
  semula berkunci `(tanggal, diketahui_pada)`, sehingga dua pencatatan dalam **detik yang sama**
  bertabrakan di kunci utama — kelas cacat yang sama dengan T37, dan kini berkunci
  `(tanggal, revisi)` (**T40**).
- **Yang tidak dikerjakan, dan sebabnya**: `transaksi`/`posisi` (F11) belum ada, jadi risiko
  berjalan baru menjumlahkan **rencana belum dieksekusi** (suku pertama PRD 8.2 menyusul bersama
  F11); dasbor "tindakan menunggu" (P16), panel jendela, dan jurnal belum tersentuh.
- **Pertanyaan baru untuk pengguna: P24** (batas bobot per sektor tidak dapat dinilai selama
  `sektor_idx_ic` kosong) — rinciannya di bagian 3.

### Tahap 2 — langkah 2b: sektor dari sumber data (K25) + K26, 10 Okt 2026

Dua pertanyaan yang menunggu dijawab pengguna 10 Okt 2026, dan yang pertama langsung dikerjakan:

- **K26 (P23) — `tanggal_tinjau` = jatuh tempo berikutnya.** Tidak ada perubahan kode: itu memang
  tafsir yang sudah dipakai sejak langkah 1.
- **K25 (P24) — kolom sektor kedua `emiten.sektor_sumber`** (migrasi 011), diisi `--ambil-jenis`
  dari `sector` sumber data — jalur yang sama dengan K21, jadi tidak ada permintaan jaringan baru.
  Yang berubah di kalkulator risiko: batas bobot per sektor 30% **kini ditegakkan**, memakai
  `sektor_idx_ic` bila terisi dan `sektor_sumber` bila tidak; taksonomi yang dipakai disebut di
  keluaran, dan rencana yang tidak dapat diatribusikan ke sektor mana pun pada taksonomi itu
  **tidak ikut dijumlahkan** serta jumlahnya dilaporkan (**T41**). `sektor_idx_ic` tetap kosong dan
  tetap menang begitu diisi manusia (K12 tidak berubah).
- **Uji**: `tests/test_risiko.py` +5 dan `tests/test_jenis_emiten.py` +1; seluruh **573 lulus**.
- **Yang tidak berubah, dan itu disengaja:** kriteria saringan yang memakai statistik sektor
  (median sektor, PRD 8.2) **tetap** memakai `sektor_idx_ic` dan tetap jatuh ke statistik seluruh
  semesta selama kolom itu kosong (konsekuensi K12). `sektor_sumber` dipakai untuk **batas risiko**,
  bukan untuk memilih pembanding sektor — memakainya di sana akan mengubah arti skor yang sudah
  tersimpan, dan itu keputusan tersendiri.

### Tahap 2 — langkah 2c: notasi khusus dari halaman resmi IDX (K27, P22 tertutup), 10 Okt 2026

Pengguna memilih melanjutkan pencarian sumber teks untuk daftar papan pemantauan khusus, dan
pencarian itu **membatalkan premis lama**: yang memblokir bukan "IDX", melainkan dua host-nya.
`www.idx.co.id` dan `www2.idx.co.id` tetap 403, sedangkan **`www.idx.id`** melayani halaman yang
sama dengan **HTTP 200** (251.947 byte) untuk User-Agent yang menyebut dirinya. Terukur 10 Okt 2026
di mesin ini: UA `MejaSaham/0.1 (…)` → 200; UA bawaan `Python-urllib/3.14` → 403; lima permintaan
berturut-turut → lima kali 200 (0,56–0,73 detik). **Tanpa peramban, tanpa cookie, tanpa PDF, tanpa
dependensi baru.**

- **Adaptor baru `mejasaham/notasi.py` + `--ambil-notasi`** → `notasi-khusus.csv` → `--impor`
  (pola yang sama dengan K11/K12/K16/K18/K21; penulisan basis data tetap satu jalur).
- **Yang dibaca dari halaman:** pola `FormatEmitenCode:"KODE.HURUF"`. Dua hal yang ditemukan
  **karena menjalankannya atas halaman sungguhan**, bukan dari bacaan kode: (1) huruf notasinya
  **tergabung** (`BOSS.BELYX` = B, E, L, Y, X), sehingga membacanya sebagai satu token membuat
  seluruh daftar papan pemantauan tampak kosong; (2) kodenya **tidak selalu empat huruf** — halaman
  itu memuat `GOTOM`, jadi pola empat huruf membuang satu baris tanpa suara. Keduanya dikunci uji.
- **Tanggalnya dari halaman, bukan dari jam sistem**: halaman tanpa tanggal ditolak, halaman dengan
  dua tanggal berbeda juga ditolak, bukan diringkas. `tanggal_mulai` = tanggal data halaman, dan
  asal itu ditulis di `keterangan` **tiap baris** supaya tidak terbaca sebagai "notasi mulai hari
  itu" (sumbernya tidak menyatakan kapan notasi dimulai).
- **Berkasnya bertambah, yang tidak lagi tercantum ditutup** (`tanggal_selesai`) — halaman itu
  menyajikan keadaan terkini tanpa arsip, jadi riwayat yang ditimpa tidak bisa dibangun ulang
  (PRD 9.12). Yang ditutup hanya baris bertanda pengambil ini; isian tangan tidak disentuh.
- **Terukur atas data nyata** (`.uji-data/uji-sektor/`): **122 baris notasi, 68 emiten ber-notasi X**
  (papan pemantauan khusus), data per 08 Okt 2026; pengambilan ulang **idempoten** (`0 baru,
  0 ditutup`). Sesudah diimpor, `--saring` berhenti berbunyi "PERINGKAT SEMENTARA" dan berbunyi
  **"Kandidat teratas"**; semesta likuid **235 → 227** (delapan emiten ber-notasi keluar), dan
  kandidatnya tetap 9 — jadi yang berubah adalah **kejujuran daftarnya**, bukan angkanya.
- **Uji**: `tests/test_notasi_idx.py` (10 uji), seluruhnya **583 lulus**.
- **Yang belum diambil, dan itu bukan kelalaian yang disembunyikan:** daftar **suspensi**
  (381 kode, 1.910 peristiwa, 97 masih tersuspensi) dan **UMA** (1.193 catatan) ada di halaman
  lain domain yang sama dan sudah terbukti 200 — keduanya masuk sebagai `jenis` tersendiri kalau
  nanti diambil.

### Tahap 2 — langkah 3: transaksi, posisi & dasbor "tindakan menunggu" (F11), 10 Okt 2026

Pengguna menyetujui langkah ini sebagai lanjutan Tahap 2, dan yang dikerjakan adalah **langkah 9
alur PRD 9.1** — bagian yang membuat rencana berhenti menjadi niat: *"Eksekusi manual di
sekuritas → Catat transaksi"*. Sekaligus dua suku yang selama ini kosong menjadi ada: risiko
berjalan PRD 8.2 (suku posisi aktif) dan drawdown AC-13.

- **Migrasi 012** — `posisi` & `transaksi` (berversi `revisi`, append-only, trigger menolak
  `UPDATE`/`DELETE`) plus kolom `arus_dana` & `mode` pada `ekuitas_harian`. Bentuk dan alasannya di
  `docs/skema-data.md` 5.13; keputusan teknisnya **T43–T47** di `docs/arsitektur.md`.
- **`mejasaham/posisi.py`** — lembar, harga rata-rata, dan hasil **diturunkan dari transaksi**
  (bukan disimpan dua kali), biaya dihitung dari tarif *all-in* tanpa menambah PPh dua kali (K23),
  dan pelanggaran **V1/V2/V5/V6 dicatat di barisnya**, bukan mencegah pencatatan (PRD 9.8).
- **`mejasaham/dasbor.py` + `--dasbor`** — satu halaman PRD 11.1: keadaan snapshot (termasuk
  peringatan basi, AC-8), watchlist, posisi, risiko berjalan + batasnya, ekuitas & drawdown,
  kandidat **dari skor yang sudah tersimpan**, dan daftar **tindakan menunggu** (PRD 9.11).
- **AC-6 terukur atas data nyata** (`.uji-data/uji-posisi/`): risiko berjalan **Rp 1.671.600** =
  posisi TLKM Rp 1.512.000 + rencana ASII yang belum dieksekusi Rp 159.600 — sedangkan rencana #1
  TLKM yang **sudah** dieksekusi tidak dijumlahkan lagi. Sebelumnya angkanya Rp 1.822.800 dari
  rencana saja, yaitu termasuk risiko yang sudah tidak lagi berbentuk rencana.
- **AC-13 terukur dua arah.** Uji: setoran Rp 50 juta disusul rugi 10% → drawdown **mentah 0%**
  (setoran terbaca sebagai kenaikan) sedangkan **terkoreksi 10%**; penarikan Rp 40 juta dari
  ekuitas Rp 100 juta → mentah 40%, terkoreksi 0%. Pada data nyata, deret yang arus dananya belum
  dicatat **tidak** dikoreksi dan sebabnya disebut — bukan dikoreksi dengan nol.
- **V5 terukur atas data nyata:** stop TLKM 2.240 → 2.100 tersimpan sebagai pelanggaran V5
  beserta alasannya di baris posisi, dan kenaikannya kembali ke 2.180 tetap boleh (trailing).
- **Tindakan menunggu terukur:** `--dasbor` atas data nyata berbunyi
  `[stop_tertembus] ASII · posisi #2 — penutupan Rp 4.820 (2026-10-09) menembus stop Rp 4.830`.
- **Uji**: `tests/test_posisi.py` (57) + `tests/test_dasbor.py` (14) + 3 uji migrasi di
  `tests/test_db.py`; seluruh **657 lulus**. Penjaga migrasi 009–012 ikut dikunci sidik SHA-256.
- **Yang belum dikerjakan, dan sebabnya masing-masing:** (a) **V3, V4, V7** — ketiganya menuntut
  tabel `jurnal` (F7, Tahap 3), dan pelanggaran yang dicatat di dua tempat akan dihitung dua kali;
  (b) **aksi korporasi pada posisi** (split/reverse split menyesuaikan lembar & stop, right issue
  dengan tenggat, dividen sebagai arus kas) — inilah sebabnya tenggat right issue di dasbor
  berstatus **tidak dapat dinilai** dan disebut apa adanya; (c) **ekuitas diturunkan dari
  transaksi + kas**: ekuitas harian masih **dicatat pengguna** seperti sebelumnya, jadi AC-13
  lulus untuk drawdown & arus dana, belum untuk penurunan ekuitasnya; (d) **panel jendela
  PySide6** (seluruh F11 jalan di mode kepala); (e) **`harga_indeks`** (rezim pasar/breadth).

### Tahap 2 — langkah 4: aksi korporasi pada posisi (F11, PRD 9.11; AC-18), 10 Okt 2026

Lanjutan Tahap 2 dengan persetujuan pengguna ("lanjutin"), dan yang ditutup adalah **satu-satunya
sebab** butir right issue di dasbor berstatus "tidak dapat dinilai" — sekaligus cacat yang lebih
serius yang belum pernah terlihat: **posisi yang melewati split menampilkan lembar, harga
rata-rata, dan risiko yang salah tanpa satu pun tanda**, dan angka itu yang dipakai menghitung
risiko portofolio.

- **Migrasi 013** — `aksi_korporasi.tenggat` (batas waktu pelaksanaan right issue; NULL = belum
  dinyatakan), `posisi.tgl_stop` (basis tanggal level stop), dan tabel `keputusan_right_issue`
  (tebus / jual HMETD / abaikan, berversi & append-only). Bentuk dan alasannya di
  `docs/skema-data.md` 5.14; keputusan teknisnya **T48–T51** di `docs/arsitektur.md`.
- **`mejasaham/posisi.py`** — lembar tiap transaksi diskalakan ke basis sekarang oleh split yang
  terjadi setelah tanggalnya (uangnya tidak), stop dipindahkan dari basisnya (`tgl_stop`), dividen
  dihitung per peristiwa, dan keputusan right issue disimpan. `mejasaham/dasbor.py` menambahkan
  jenis tindakan `right_issue_belum_diputuskan`; `mejasaham/cli.py` menambahkan
  `--hak-right-issue` dan `--putuskan-right-issue`.
- **AC-18 terukur atas data nyata** (`.uji-data/uji-aksi-korporasi/`): beli MLPT 1.000 lembar
  @Rp 18.750 pada 1 Jul 2026 (sebelum split), stop Rp 17.000 pada basis 15 Jul 2026 → sesudah
  split 1:25 pada 21 Jul 2026 posisinya berbunyi **25.000 lembar, rata-rata Rp 750, stop Rp 680**,
  dan risiko terbuka **Rp 5.875.000** = (915 − 680) × 25.000. Sebelum langkah ini angkanya adalah
  1.000 lembar dengan stop Rp 17.000 di atas penutupan Rp 915 — yang muncul di dasbor sebagai
  **"stop tertembus" yang tidak pernah terjadi**.
- **Dividen terukur atas data nyata:** beli BBCA 1.000 lembar 29 Mei 2026 → dua pembayaran yang
  jatuh selama masa pegang (17 Jun Rp 20/lembar, 31 Agu Rp 25/lembar) = **Rp 45.000 bruto**, dan
  **tidak** dipajaki aplikasi.
- **Right issue terukur lewat baris uji** (sumber data EOD menerbitkan **0** baris `right_issue`
  dari 2.141 baris aksi korporasi, jadi jalurnya tidak bisa diperiksa tanpa baris buatan yang
  ditandai "BUKAN PENGUMUMAN RESMI"): hak dihitung dari rasio × lembar pada tanggal aksi, tenggat
  kosong disebut "BELUM DINYATAKAN", `tebus` menolak tanpa transaksi, `jual_hmetd` menyimpan
  lembar/harga/biaya dan menghitung hasilnya (Rp 119.500), keputusan yang diubah menambah revisi.
- **Uji**: `tests/test_aksi_korporasi_posisi.py` (**39**) + 2 penjaga migrasi di `tests/test_db.py`;
  seluruh **698 lulus**. **38 dari 39 uji baru terbukti gagal pada kode lama** (dijalankan lewat
  `git worktree` atas commit `4c172a0`, tanpa menyentuh working tree); yang lulus di kode lama
  hanya `test_ubah_stop_tetap_menuduh_v5_bila_basisnya_sama` — memang perilaku yang sudah ada.
- **Yang belum dikerjakan, dan sebabnya masing-masing:** (a) **P26** penebusan HMETD yang jumlahnya
  bukan kelipatan lot (PRD 10 menolaknya, dan itu tetap berlaku); (b) **P27** right issue masih
  mematikan metrik harga emiten itu di `--saring` (terukur: likuid 227 → 225) karena rumus TERP
  tidak ditetapkan PRD; (c) **P28** dividen yang dihitung tidak punya jalur koreksi manual;
  (d) `harga_indeks` (rezim pasar/breadth) dan panel jendela PySide6 — keduanya sudah ada di daftar
  kerja sebelum langkah ini.
- **Tindak lanjut 10 Okt 2026 — kelima pertanyaan itu dijawab pengguna ("sesuai rekomendasi"), dan
  dua di antaranya menuntut kerja kecil supaya keputusannya benar-benar jalan, bukan hanya
  tercatat:** **K29** (P16 disahkan apa adanya), **K30** (P25: ekuitas tetap dicatat pengguna, dan
  dasbor kini menampilkan pembanding `nilai posisi + kas` beserta selisihnya — terukur pada data
  uji: `Ekuitas Rp 251.000.000 … posisi + kas Rp 169.428.000 (selisih Rp −81.572.000)`),
  **K31** (P26: aturan lot tetap, dan hak yang bukan kelipatan lot kini disebut lebih awal —
  terukur: `hak 6.250 lembar BUKAN kelipatan lot 100 … penebusan hanya bisa dicatat 6.200 lembar`),
  **K32** (P27: TERP tidak dibangun sekarang), **K33** (P28: dividen tetap dihitung, tanpa jalur
  koreksi manual), dan **K34** (P15: kepatuhan hanya atas transaksi — dibutuhkan sebelum F7).
  Uji: **702 lulus**. Bukti tambahan: `.uji-data/uji-aksi-korporasi/bukti-16-dasbor-dengan-pembanding-ekuitas.txt`
  dan `bukti-17-hak-dengan-catatan-lot.txt`.

### Tahap 3 — langkah 1: jurnal keputusan & rekap kepatuhan (F7, PRD 9.8/11.5/13.1/13.2), 10 Okt 2026

Lanjutan dengan persetujuan pengguna ("lanjutin"), dan yang ditutup adalah **janji yang tertulis di
kode sendiri**: sejak Tahap 2, `posisi.py` menyatakan V3/V4/V7 "belum dihitung" dan menunggu tabel
`jurnal` (T44) — artinya tiga pelanggaran yang justru paling mudah terjadi (melewati batas, menambah
posisi rugi, mempertahankan posisi yang tesisnya sudah batal) tidak muncul di angka kepatuhan mana
pun. Sekarang ketiganya dihitung, dan **rekap kepatuhan PRD 13.1/13.2 untuk pertama kalinya bisa
dibaca**.

- **Migrasi 014** — tabel `jurnal` (berversi, append-only, satu rantai per transaksi) dengan tiga
  penjaga mesin: `CHECK` baris tidak kosong, trigger satu rantai per transaksi, trigger append-only.
  Bentuk dan alasannya di `docs/skema-data.md` 5.15; keputusan teknisnya **T52–T55** di
  `docs/arsitektur.md`.
- **`mejasaham/jurnal.py`** — satu baris jurnal per **transaksi** (K34), tiap kode pelanggaran
  dibaca dari **satu** tempat: V1/V2/V6 dari baris `transaksi`, V5 dari baris `posisi`, V3/V4/V7
  **diturunkan** dari `rencana`, `transaksi`, `posisi`, harga, dan revisi tesis. Karena itu tabel
  `jurnal` hanya menyimpan yang tidak bisa diturunkan (alasan, pelajaran, tanggal tinjau, penanda
  selesai) — `patuh_aturan` dan `kode_pelanggaran` PRD 12 **tidak** disimpan, sebab salinannya akan
  berbunyi lama begitu transaksinya direvisi (dan revisi itu justru diizinkan PRD 9.8).
- **`dasbor.pembatal_terpicu()` baru** — aturan "pembatal tesis terpicu" (PRD 9.6) kini hidup di satu
  fungsi yang dipakai **dua** tempat: daftar tindakan menunggu dasbor (PRD 9.11) dan pelanggaran V7
  (PRD 9.8). Sebelumnya ia hanya hidup di dalam `tindakan_menunggu()`.
- **`posisi.PELANGGARAN_BELUM_DIHITUNG` dihapus**; katalog PRD 9.8 lengkap di `posisi.PELANGGARAN`
  dan **dipinjam** `jurnal.KATALOG`; tempat deteksi tiap kode dinyatakan di `jurnal.DIDETEKSI_DI`.
  `posisi.hitungan()` menerima `sampai=` supaya V4 menilai keadaan posisi **waktu itu**, bukan
  keadaan sekarang.
- **Perintah mode kepala**: `--jurnal` (satu baris per keputusan + catatannya), `--rekap-kepatuhan`
  (rekap per bulan/mode, kelengkapan tesis, expectancy, drawdown), dan `--jurnal-catat` dengan
  `--alasan`/`--pelajaran`/`--tanggal-tinjau`/`--tandai-selesai`. Semuanya tanpa jendela (AC-11).
- **Terukur atas data nyata** (`.uji-data/uji-jurnal/`, salinan `.uji-data/uji-aksi-korporasi`):
  **6 keputusan · patuh 1 (16,67%) · 7 pelanggaran** — V1 2× · V6 3× · **V3 1×** · V5 1×. Yang
  paling penting: **rencana #2 (ASII) yang pelanggaran total risikonya diterima di Tahap 2 kini
  benar-benar muncul** (`total risiko 5,44% melebihi batas 5,00%`), hal yang sebelumnya hanya
  tersimpan sebagai kalimat di kolom `catatan`. V4 **diperiksa dan tidak berlaku** pada MLPT
  (rata-rata Rp 750 vs penutupan Rp 1.125 pada 22 Sep 2026 — posisinya tidak rugi saat ditambah),
  dan itu dibuktikan angkanya di `bukti-keadaan.txt`, bukan disimpulkan dari "tidak ada baris".
  Expectancy berbunyi **"BELUM DAPAT DINILAI: 0 dari 30 putaran tertutup"** beserta sebabnya, dan
  drawdown berjalan **0,39%** terkoreksi arus dana.
- **Uji**: `tests/test_jurnal.py` (**42**) + 3 penjaga migrasi 014 di `tests/test_db.py`
  (`VERSI_TERKUNCI` 13 → 14, sidik SHA-256); seluruh **747 lulus**. Pembuktian kode lama: perintah
  `--rekap-kepatuhan` **tidak dikenal** di HEAD (keluar 2), katalog lama berbunyi
  `PELANGGARAN: V1/V2/V5/V6` + `BELUM DIHITUNG: V3/V4/V7`, dan berkas ujinya gagal saat koleksi
  (modul `jurnal` belum ada) — ketiganya terekam di
  `.uji-data/uji-jurnal/bukti-10-perbandingan-kode-lama.txt`.
- **Yang belum dikerjakan, dan sebabnya masing-masing:** (a) **ekspor (F9)** dan **cadangan (F12)**
  — keduanya bagian Tahap 3 yang sama dan belum tersentuh; (b) **P29** aturan atribusi pelanggaran
  tingkat posisi (V5/V7) ke transaksi, dipakai sekarang dengan aturan yang dinyatakan terbuka;
  (c) **P30** pemetaan `selesai_pada` untuk tombol "[Tandai selesai]" PRD 11.5 yang tidak punya
  kolomnya di PRD 12; (d) **U22/U23** — ambang 30 putaran dan penyebut expectancy per putaran
  (keduanya usulan yang sudah dipakai, tercatat supaya bisa dikoreksi); (e) jumlah **peristiwa** V5
  tidak dapat dipulihkan dari skema (kolomnya menyimpan kode, bukan peristiwa), jadi V5 dihitung
  satu kali per posisi dan itu dikatakan di keluaran; (f) panel jendela PySide6 dan daftar
  suspensi/UMA — sudah ada di daftar kerja sebelum langkah ini.

### Tahap 3 — langkah 2: ekspor laporan (F9, PRD 9.10, 10 Okt 2026)

- **`mejasaham/ekspor.py`** dan `--ekspor` menulis lima jenis laporan: hasil saringan tersimpan,
  watchlist, rencana, jurnal, dan laporan mutu yang berasal dari arsip snapshot terkait.
- Setiap CSV memakai UTF-8 BOM dan pemisah `;`, memuat `id_snapshot`, ID dan versi preset,
  sumber harga, versi aplikasi, serta pernyataan bukan nasihat investasi. Sumber harga tidak resmi
  diberi peringatan K7. Penulisan memakai berkas sementara dan tidak menimpa tujuan yang sudah ada.
- **Uji**: `tests/test_ekspor.py` (8 uji); seluruh suite **755 lulus**. Perintah verifikasi:
  `python -m pytest`.
- **Yang belum dikerjakan:** F12 cadangan/pemulihan (langkah berikutnya), panel jendela PySide6,
  dan daftar suspensi/UMA.

### Tahap 3 — langkah 3: cadangan & pemulihan (F12, PRD 9.12, 11 Okt 2026)

- `mejasaham/cadangan.py` menyediakan cadangan atomik per folder dengan `VACUUM INTO`, konfigurasi
  dan arsip snapshot ikut disalin, manifest versi format/skema, lokasi bawaan di luar folder data,
  serta retensi 14 cadangan (**diubah K92: 3**). `--folder-cadangan` memilih lokasi lain.
- `--buat-cadangan` dan `--daftar-cadangan` mengelola cadangan; `--pulihkan FOLDER` memeriksa
  manifest dan `PRAGMA integrity_check`, menyiapkan salinan penuh, lalu mengganti folder data.
  Folder data yang lama dipertahankan sampai staging siap dan dipulihkan kembali bila penggantian
  gagal.
- Otomatisasi: `db.siapkan()` mencadangkan basis data lama sebelum migrasi; refresh yang berhasil
  mencadangkan setelah koneksi tulis ditutup. Kegagalan backup ditampilkan dan mengembalikan kode
  keluar gagal.
- Verifikasi: `tests/test_cadangan.py` menguji cakupan berkas, pemulihan ke folder bersih,
  `integrity_check`, retensi, penolakan lokasi di dalam folder data, dan cadangan sebelum migrasi.
- **Verifikasi suite:** `python -m pytest` — **759 lulus**. Uji CLI nyata di folder sementara:
  `--buat-cadangan`, `--daftar-cadangan`, dan `--pulihkan` masing-masing keluar 0.
- **Yang belum dikerjakan:** menu F12 pada jendela, panel PySide6, dan daftar suspensi/UMA; yang
  pertama menyusul saat panel UI dikerjakan. Operasi F12 mode CLI dan kriteria AC-14 sudah diuji.

### Tahap 3 — langkah 4: suspensi dan UMA dari IDX (11 Okt 2026)

- `--ambil-notasi` mengambil halaman notasi khusus dan endpoint API resmi `GetSuspension` / `GetUma`
  dari `www.idx.id`; hasil tetap ditulis sebagai CSV dan hanya masuk basis data lewat `--impor`.
- K35 diputuskan pengguna 11 Okt 2026: suspensi terbuka sampai pengumuman pembukaan kembali (UPT);
  UMA berlaku 30 hari kalender dari tanggal pengumuman. Pengumuman duplikat dengan kunci yang sama
  digabung supaya satu jalan impor tetap sesuai kunci append-only.
- Uji nyata 11 Okt 2026: halaman menyatakan data notasi per 09 Okt 2026; API menghasilkan 963 baris
  riwayat suspensi ber-kode tunggal (71 aktif), 1.191 UMA, dan 68 emiten papan pemantauan. Impor ke
  basis data bersih mencatat 2.276 baris: 54 `notasi_lainnya`, 68 `papan_pemantauan`, 963 `suspensi`,
  1.191 `uma`.
- **Batas sumber yang terlihat:** 56 rekaman `>1 Kode` terdiri dari 29 SPT dan 27 UPT. Tindak lanjut
  11 Okt menemukan seluruh 56 PDF langsung dari `Data_Download` IDX, dan teksnya dapat diekstrak
  tanpa OCR; kode yang tercantum serta tautan PDF dicatat di
  `docs/riset-suspensi-multi-kode-2026-10.md`. Namun daftar kode per dokumen belum sama dengan aksi
  per kode: sebagian pengumuman SPT mencampur status `Aktif` dan `Suspensi`, termasuk suspensi yang
  hanya dipertahankan, sedangkan tanggal efektif bisa berbeda dari tanggal API. Karena itu hasil
  ekstraksi belum diimpor. Ada pula 40 pengumuman pembukaan kembali tanpa pasangan suspensi
  berkode tunggal; keterkaitan dengan pengumuman massal masih perlu direkonsiliasi. Sampai aksi dan
  tanggal setiap kode ditinjau terhadap PDF, keluaran tetap menyebut **PERINGKAT SEMENTARA**.
- Uji baru di `tests/test_notasi_idx.py` menjaga penutupan saat UPT, UMA + 30 hari, duplikasi, peringatan
  peristiwa tanpa pasangan, penanda peringkat sementara yang bertahan setelah impor, revisi provenance,
  dan penolakan jeda negatif. Seluruh suite saat tahap implementasi:
  `python -m pytest` — **765 lulus**. Pengambilan dan impor nyata keluar 0; bukti di
  `.uji-data/uji-notasi-aktivitas/`.
- **Tindak lanjut 11 Okt 2026:** daftar kode calon untuk 56 PDF `>1 Kode` dan tautan resmi tersedia
  di `docs/riset-suspensi-multi-kode-2026-10.md`. Semua lampiran ternyata berteks, bukan pindai;
  tetapi klasifikasi kode sebagai suspensi baru/dipertahankan/dibuka dan tanggal efektifnya belum
  tuntas. Pesan aplikasi kini menyebut kekurangan rekonsiliasi itu. Suite setelah pembaruan pesan:
  **765 lulus**. Belum ada impor atau perubahan basis data. **Yang belum dikerjakan:** rekonsiliasi aksi
  per kode untuk daftar tersebut dan 40 pembukaan kembali tanpa pasangan, panel PySide6, dan menu
  F12. Tahap berhenti untuk ditinjau sesuai K4.

### Tindak lanjut data lokal & peringkat (11 Okt 2026)

- Berkas `.uji-data/mejasaham/konfigurasi/emiten.csv` diperiksa sebelum ditimpa: **973 baris**;
  `sektor_idx_ic`, `papan`, dan `jenis` semuanya kosong, jadi tidak ada suntingan tangan pada
  kolom tersebut. Pengambilan ulang `--ambil-jenis --timpa-jenis` dicoba, tetapi permintaan
  sektor tertahan tanpa progres, termasuk setelah akses jaringan penuh diizinkan; proses dihentikan.
  Berkas emiten tidak berubah dan belum ber-jenis.
- Impor konfigurasi lokal pertama menghasilkan snapshot 5 (0 baru, 5.051 sama). `--ambil-sun`
  berhasil mengambil kurva PHEI: SUN 10 tahun **7,1845% per 09 Okt 2026**. Impor berikutnya
  menghasilkan snapshot 6 (1 baru, 5.051 sama).
- `--saring` pada snapshot 6 menghasilkan **9 peringkat sementara**, AUTO 55,8; breadth 34,1%,
  rezim RISK-OFF. Peringkat tetap sementara karena daftar suspensi belum lengkap dan 973 emiten
  belum ber-jenis. Fundamental tetap berlabel tidak resmi. Laporan mutu mencatat kalender berakhir
  09 Okt 2026 dan cek sumber kedua belum pernah dijalankan.
- **Belum dikerjakan:** jenis emiten belum berhasil diambil; cek sumber kedua; memperbarui kalender;
  rekonsiliasi aksi/tanggal efektif 56 pengumuman suspensi multi-kode; panel PySide6 dan menu F12. Suite perubahan kode
  terakhir yang tercatat sebelum tindak lanjut ini adalah **765 lulus**; tidak dijalankan ulang
  karena sesi ini hanya menjalankan impor data dan saringan.
- Cara melanjutkan: ulangi `--ambil-jenis --timpa-jenis --folder-data .uji-data\mejasaham` saat
  sumber tersedia; periksa berkas hasil, impor folder konfigurasi, lalu jalankan `--saring`.
  Jangan sebut peringkat sebagai kandidat sampai kelengkapan notasi diverifikasi.

### Perbaikan ekspor atomik di Windows (11 Okt 2026)

- Verifikasi ulang menemukan 7 uji `tests/test_ekspor.py` gagal karena `os.link` ditolak Windows
  (`WinError 5`) saat menerbitkan CSV dari berkas sementara. Seluruh kegagalan terjadi pada
  pembuatan hard link.
- `mejasaham/ekspor.py` kini memakai `os.rename` di Windows (atomik dan gagal bila tujuan sudah
  ada), sedangkan POSIX tetap memakai `os.link` untuk menjaga syarat tidak menimpa tujuan.
- Verifikasi: `python -m pytest tests/test_ekspor.py` — **8 lulus**; `python -m pytest` —
  **765 lulus**. Pada Windows, `TEMP`/`TMP` diarahkan ke `.tmp/pytest-temp` sesuai jebakan
  lingkungan bagian 6.
- Belum dikerjakan pada tahap perbaikan: pemeriksaan XLSX Daftar Saham resmi IDX sesuai aksi 12.

### Tindak lanjut daftar saham resmi IDX (11 Okt 2026)

- Tombol `Unduh` di halaman resmi tidak menghasilkan berkas karena chunk JavaScript halaman gagal
  dimuat di browser sesi ini; tabel tetap kosong. Endpoint resmi yang dipakai halaman berhasil
  diakses langsung (HTTP 200), sehingga respons JSON bertanggal diarsipkan di
  `.uji-data/riset-idx/idx-daftar-saham-api-20261011.json`.
- Endpoint daftar menghasilkan **962 kode** dengan kolom `Code`, `Name`, `ListingDate`, `Shares`,
  dan `ListingBoard`; tidak ada kolom sektor. Sektor resmi diambil lewat 11 filter sektor pada
  halaman yang sama. Cakupan hasil filter **962 kode unik**, jumlah per filter berjumlah 962,
  dan papan tiap kode konsisten terhadap daftar tanpa filter. Bukti respons lengkap ada di
  `.uji-data/riset-idx/idx-daftar-saham-sektor-20261011.json`.
- Data belum dimuat ke basis data. Sebelum impor, cocokkan sampel sektor/papan/tanggal dengan
  profil emiten IDX dan tinjau perbedaan 962 kode terhadap 973 baris lokal; jangan menimpa isian
  yang ada. XLSX belum didapat karena kontrol unduh halaman gagal.
- Verifikasi kode setelah perbaikan ekspor: uji terarah **8 lulus**, suite **765 lulus**.
- Tahap berhenti untuk ditinjau sesuai K4.

### 5.1 Hasil pemeriksaan "bisa ambil datanya sendiri?" (9 Okt 2026)

Pertanyaan Anda dijawab dengan penelusuran nyata, bukan dugaan. Ringkasnya: **sebagian bisa,
satu butir tidak** — dan yang tidak itu persis salah satu yang paling dibutuhkan.

| Yang dibutuhkan | Bisa diambil otomatis? | Bukti |
|---|---|---|
| **Daftar emiten** (kode + nama) | **Bisa, sebagian** | Master File Efek KSEI (`web.ksei.co.id/Download/StatisEfek20260930.txt.zip`, HTTP 200): 3.678 baris, **975 EQUITY di IDX, semuanya ACTIVE**, lengkap dengan kode, nama, ISIN, tanggal pencatatan, sektor, harga penutup. **Tidak ada** papan pencatatan, dan sektornya klasifikasi gaya JASICA/KSEI — **bukan IDX-IC** yang dipakai PRD |
| **Kalender libur bursa** | **Bisa** | PDF resmi KSEI (HTTP 200, terurai): **PENG-0005/DIR/KSEI/1025** menindaklanjuti **Peng-00171/BEI.POP/09-2025** dan memuat 22 tanggal libur 2026; versi 2027 juga tersedia. Diperiksa ulang 9 Okt 2026 (langkah 10): halaman itu menautkan **2025, 2026, dan 2027** — berkas 2025 yang ditautkan (versi *Perubahan Kedua*) ditolak T31, dan versi *Perubahan*-nya lulus dengan 25 tanggal yang **identik**, sehingga **2025 kini terisi** lewat K17 (sumbernya `PENG-0004/DIR/KSEI/0825`). **2021–2024** sudah 404 di KSEI, dan Arsip Internet hanya menyimpan salinan terbaru halaman itu |
| **Notasi khusus / suspensi / papan pemantauan** | **Tidak** | Halaman resminya ada di `www2.idx.co.id`, tetapi seluruh `idx.co.id` membalas **HTTP 403** dengan tantangan Cloudflare (`cf-mitigated: challenge`) — 16 variasi URL dicoba, termasuk meniru TLS browser (24 percobaan, 4 profil): semuanya 403. Salinan pengumuman IDX beredar di situs sekuritas, tetapi itu **sekunder** dan tidak boleh jadi sumber produksi |
| **Imbal hasil SUN** | **Bisa — terjawab K16** (`--ambil-sun`) | Halaman HPW **PHEI** (`phei.co.id/Data/HPW-dan-Imbal-Hasil`, HTTP 200) memuat tabel kurva imbal hasil SBN per tenor **langsung di HTML**, dengan pernyataan tanggal valuasinya sendiri ("per 9-Oktober-2026"). Terukur 9 Okt 2026: **SUN 10 tahun = 7,1845%**. Dua jalur lain gagal: `bi.go.id` memutus koneksi (`ConnectionResetError` pada beranda dan halaman indikator), dan `api-djppr.kemenkeu.go.id/web/api/v1` (rutenya dibaca dari bundel aplikasinya, bukan ditebak) ternyata CMS — `/page?url=...` mengembalikan JSON widget, tanpa berkas deret imbal hasil yang bisa diunduh |
| **Fundamental & rasio bank** | **Tidak** | Diperiksa ulang 9 Okt 2026: seluruh jalur `idx.co.id` yang memuatnya (`StaticData/ListedCompanies/CorporateAction/`, `StaticData/NewsAndAnnouncement/`, `primary/StockData/GetSecuritiesStock`) membalas **HTTP 403** — sama seperti sebelumnya. Tidak ada sumber resmi lain yang menerbitkan laporan keuangan per emiten dalam bentuk yang bisa diambil otomatis: KSEI menerbitkan daftar efek (jumlah saham, tanggal pencatatan), **bukan** laba/ekuitas/arus kas. Jadi berkas ini tetap **pekerjaan manusia** (P2/U3), dan metrik yang bergantung padanya tetap "tidak dihitung" sampai berkasnya ada |

Yang **tidak** dilakukan: memakai daftar hari libur dari pemberitaan, atau daftar saham dari
situs sekuritas, lalu menuliskannya seolah resmi. Itu persis yang dilarang aturan keras 1.

Catatan pemeriksaan: laporan ini berlaku untuk **satu jaringan** (mesin ini, 9 Okt 2026).
Perilaku dari jaringan lain — termasuk IP residensial Indonesia — belum diuji, jadi "IDX menutup
akses otomatis" adalah temuan tentang jaringan ini, bukan kesimpulan tentang IDX. Sebuah klaim
di repositori pihak ketiga bahwa profil TLS Firefox bisa menembusnya **sudah terbantahkan** di
sini: profil itu ikut 403. Hal yang sama berlaku untuk `bi.go.id`: yang terukur di sini adalah
**koneksi yang diputus dari jaringan ini**, bukan pernyataan bahwa BI menutup akses otomatis.

### Tindak lanjut daftar saham resmi IDX — pemeriksaan sampel & selisih (11 Okt 2026)

- Profil resmi **KAQI** cocok dengan baris API daftar saham: tanggal pencatatan `2025-03-10`
  dan papan `Development` (profil menyebut `Pengembangan`). Filter sektor API menempatkannya pada
  `Consumer Cyclicals`, sesuai sektor profil `Barang Konsumen Non-Primer`. Ini memvalidasi satu
  sampel lintas daftar, filter sektor, dan profil; belum menjadi pemeriksaan menyeluruh.
- Dibandingkan dengan 973 kode dalam `emiten.csv` KSEI: **962 kode IDX ada di lokal**; 5 kode IDX
  belum ada di lokal (**AMAN, KOPI, PPRO, PRIM, TALF**); 16 kode lokal tidak ada di daftar IDX
  (**ATPK, FORZ, GOTOM, HDTX, JASS, JKSW, KPAL, KPAS, KRAH, MAMI, MYRX, NIPS, PAFI, PRAS,
  SING, SUDI**). Daftar lokal tersebut tidak otomatis berarti semuanya saham biasa aktif
  IDX; contoh `GOTOM` bernama `MVS GOTO GOJEK TOKOPEDIA`, sehingga identitas efek/kelas saham perlu
  dipastikan sebelum diperlakukan sebagai emiten tercatat.
- Karena sumber KSEI memuat identitas efek yang berbeda cakupannya, jangan menghapus kode lokal
  atau menimpa konfigurasi dengan daftar IDX secara massal. Siapkan berkas konfigurasi terpisah
  berisi hanya kode yang terverifikasi di daftar IDX, dan pertahankan rekonsiliasi 5+16 kode ini
  untuk tinjauan. Sektor resmi hanya boleh diisi dari pemetaan hasil filter yang telah divalidasi;
  `jenis` tidak diturunkan dari sektor Financials secara luas.
- Bukti: `.uji-data/riset-idx/idx-daftar-saham-api-20261011.json` dan
  `.uji-data/riset-idx/idx-daftar-saham-sektor-20261011.json`; profil resmi:
  [KAQI](https://block.idx.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/KAQI).
  Daftar IDX memuat 962 kode; berkas KSEI lokal memuat 973 kode setelah melewati baris komentar.
- Belum dibuat konfigurasi/impor. Tahap berhenti untuk ditinjau sesuai K4.

### Tindak lanjut daftar saham resmi IDX — berkas terpisah untuk tinjauan (11 Okt 2026)

- Disusun `.uji-data/riset-idx/emiten-idx-20261011.csv` memakai urutan kolom impor `emiten.csv`.
  Berkas memuat 962 kode unik dan 11 sektor; nama, tanggal pencatatan, jumlah saham, dan papan
  berasal dari respons daftar IDX, sektor dari membership 11 filter resmi. Kolom sektor memakai
  nama sektor persis seperti endpoint IDX (bahasa Inggris), bukan terjemahan tebakan.
- Papan dipetakan ke nilai aplikasi: `Main` → `utama`, `Development` → `pengembangan`,
  `Acceleration` → `akselerasi`, `Ekonomi Baru` → `ekonomi_baru`, `Watchlist` →
  `papan_pemantauan`. `jenis`, `sektor_sumber`, `status_notasi`, dan `free_float_persen`
  dikosongkan karena kedua respons ini tidak menyatakannya. `jenis` Financials sengaja tetap
  kosong; seluruh saham sektor itu tidak otomatis dianggap bank. Sumber dan tanggal pencatatan
  dicatat pada tiap baris.
- Rekonsiliasi terpisah disimpan di `.uji-data/riset-idx/rekonsiliasi-kode-20261011.csv`.
  Pemeriksaan data: 962 baris, 962 kode unik, kolom sesuai template, tidak ada nilai kosong pada
  kolom wajib/atribut IDX yang tersedia; sampel KAQI cocok dengan profil IDX. Pemeriksaan ini
  bukan validasi semua profil atau validasi otomatis seluruh format lewat parser aplikasi.
- Tidak mengubah konfigurasi KSEI, tidak menjalankan impor, dan tidak mengubah basis data.
  **Tahap berhenti untuk tinjauan pengguna sesuai K4** sebelum keputusan impor.

### Impor daftar saham resmi IDX ke basis data uji terisolasi (11 Okt 2026)

- Setelah tinjauan pengguna, daftar diimpor melalui `--impor` ke basis data uji baru
  `.uji-data/riset-idx/db/mejasaham.db`; CSV kerja ada di `.uji-data/riset-idx/impor/emiten.csv`.
- Verifikasi perintah: `python -m mejasaham --impor .uji-data\riset-idx\impor --folder-data .uji-data\riset-idx\db`
  menghasilkan **962 baris baru**, 0 baris sama, snapshot 1. Pemeriksaan baca-saja sesudahnya
  menemukan 962 baris terkini, seluruhnya bersumber dari `IDX Daftar Saham API + filter sektor
  resmi (diakses 11 Okt 2026)`.
- Basis data KSEI `.uji-data/mejasaham/mejasaham.db` tidak diubah: pemeriksaan sesudah impor
  tetap menunjukkan 973 baris emiten, 973 terkini, dan 6 snapshot. Alasannya: semua baris KSEI
  diketahui pada 11 Okt 2026, sama dengan tanggal daftar IDX; isinya berbeda dan kunci revisi
  `kode + diketahui_pada` akan bertabrakan. Tanggal tidak dimajukan untuk menghindari pemalsuan
  waktu diketahui.
- Laporan mutu pada basis data kosong menyebut kalender, notasi khusus, dan cek sumber kedua belum
  tersedia; ini keadaan yang diharapkan untuk impor daftar saja. Tidak ada uji otomatis dijalankan.
- Tidak mengubah `emiten.csv` konfigurasi KSEI dan tidak menggabungkan dua sumber ke satu basis
  data. Penggabungan tetap memerlukan dukungan pencatatan waktu yang lebih halus atau keputusan
  model data; jangan mengubah tanggal sumber demi melewati benturan.

### Kandidat pasangan UPT dari sampel suspensi IDX (11 Okt 2026)

- Dibuat `.uji-data/riset-idx/kandidat-pasangan-upt-20261011.csv`: 39 baris kode yang diekstrak
  dari 26 PDF UPT. Enam belas baris memiliki kandidat SPT terdahulu pada sampel; 23 baris tidak
  menemukan kandidat dalam sampel 56 PDF.
- Pasangan bersifat pencarian awal, bukan penetapan peristiwa. Semua baris ditandai
  `KANDIDAT BELUM DIVERIFIKASI PDF`; nomor pengumuman, tanggal efektif, pasar, dan kesinambungan
  periode suspensi belum diperiksa manual. Baris tanpa kandidat tidak membuktikan bahwa tidak
  pernah ada suspensi.
- Pemeriksaan struktur CSV: 39 baris; seluruh status masih belum diverifikasi. Tidak ada impor,
  perubahan basis data, atau uji otomatis. Tahap berhenti untuk tinjauan sesuai K4.

### Rekonsiliasi UPT berbasis PDF — berkas tinjauan (11 Okt 2026)

- Dibuat `.uji-data/riset-idx/rekonsiliasi-upt-pdf-20261011.csv` berisi 39 baris kode dari 26 PDF UPT. Per baris dicatat nomor pengumuman UPT, aksi, tanggal efektif, teks keputusan/waktu, pasar, kutipan baris kode, dan URL PDF; jika ada kandidat SPT, disertakan nomor, status baris kode, kutipan, dan URL PDF SPT.
- Pemeriksaan berkas: 39 baris; nomor UPT terisi 39/39, tanggal efektif 39/39, setiap baris punya kutipan kode, 16 memiliki kandidat SPT pada sampel, 23 tidak menemukan kandidat dari 56 PDF. Semua status tetap `PERLU TINJAUAN MANUAL`; status suspensi pada pengumuman sebelumnya belum membuktikan kesinambungan episode atau pasangan yang tepat. Tanggal dan kutipan diekstrak dari teks PDF lokal, belum ditinjau visual.
- Tidak ada impor atau perubahan basis data. Tes tidak dijalankan karena tahap hanya menyusun bukti PDF dan berkas tinjauan. Tahap berhenti sesuai K4.
- Berikutnya: tinjau berkas CSV terhadap PDF dan rekam persetujuan/koreksi per kode. Cari riwayat IDX di luar sampel untuk 23 baris tanpa kandidat sebelum menetapkan tidak ada pasangan; kemudian baru siapkan rekonsiliasi seluruh SPT multi-kode.

### Pemeriksaan ulang pasangan UPT–SPT dari keputusan PDF (11 Okt 2026)

- Membandingkan seluruh 39 kode UPT dengan keputusan dan tabel status pada PDF SPT sampel, bukan hanya mencocokkan baris yang berstatus `Suspensi`.
- Menambahkan tujuh pasangan pembukaan yang terlewat pencarian kandidat awal: CLAY, GTBO, MGLV, SAGE, SHID → `Peng-S-00005/BEI.PLP/02-2026` (suspensi baru sejak sesi I 18 Feb 2026); GPSO dan PTDU → `Peng-S-00004/BEI.PLP/02-2025` (suspensi baru sejak sesi I 17 Feb 2025). Keduanya tercatat `Aktif` pada tabel status sebelum keputusan, tetapi disebut eksplisit pada bagian keputusan sebagai suspensi baru.
- Hasil kini 23/39 memiliki pasangan SPT dalam sampel dan 16/39 belum ditemukan pada PDF SPT sampel yang lebih awal. Keberadaan pasangan masih memerlukan verifikasi visual, pasar/tanggal efektif per kode, dan riwayat episode di luar sampel. Baris tanpa pasangan bukan bukti bahwa tidak ada pengumuman terdahulu.
- CSV rekonsiliasi diperbarui; tidak ada impor, perubahan basis data, atau uji kode. Tahap berhenti untuk tinjauan sesuai K4. Berikutnya: tinjau PDF visual dan cari riwayat IDX di luar sampel untuk 16 baris tersisa sebelum menyusun daftar aksi final.

### Penelusuran API untuk kode UPT tanpa pasangan sampel (11 Okt 2026)

- Mengambil ulang API resmi `GetSuspension` dengan UA aplikasi yang jujur; respons HTTP 200 memuat 1.919/1.919 rekaman, rentang tanggal 12 Okt 2023–09 Okt 2026. Respons mentah disimpan di `.uji-data/riset-idx/suspensi-pdf/api-suspension-full-20261011.json`.
- Dari 16 baris UPT tanpa pasangan PDF sampel terdapat 12 kode unik. API memuat 38 rekaman berkode tunggal untuk enam kode (FLMC, GPSO, MDIA, NIRO, OCAP, WOWS); enam kode lainnya (ARTI, ELTY, INAF, VIVA, XSBC, XSSI) tidak muncul sebagai `Kode` tunggal. Rinciannya, termasuk judul dan URL PDF dari API, ada di `.uji-data/riset-idx/riwayat-api-kode-tanpa-kandidat-20261011.csv`.
- Cakupan API dimulai 12 Okt 2023 dan karena itu tidak membuktikan ketiadaan pengumuman sebelum tanggal tersebut. Tidak ditemukannya kode tunggal juga tidak menutup kemungkinan kode tercantum dalam PDF multi-kode (`Kode = ">1 Kode"`). Rekaman API bertanggal pengumuman; tanggal efektif dan kesinambungan episode masih harus dibaca dari PDF.
- Pemeriksaan visual satu PDF UPT (`Peng-UPT-00002/BEI.PLP/02-2026`) memastikan judul, tanggal, keputusan suspensi baru, sesi, dan lima kode pada tabel terbaca konsisten; belum semua 26 PDF UPT dan PDF kandidat SPT ditinjau visual. Tidak ada impor atau perubahan basis data. Tes tidak dijalankan (tahap riset data).
- Tahap berhenti sesuai K4. Berikutnya: lanjutkan tinjauan visual PDF UPT/SPT dan buka PDF API untuk enam kode yang memiliki riwayat; untuk enam kode yang tidak muncul sebagai kode tunggal, cari lampiran multi-kode serta pengumuman sebelum 12 Okt 2023. Setelahnya rekam koreksi/konfirmasi per kode dan berhenti untuk tinjauan sebelum impor.

### Pembacaan PDF API untuk kode tanpa pasangan sampel (11 Okt 2026)

- Mengunduh 38 PDF dari riwayat API resmi untuk FLMC, GPSO, MDIA, NIRO, OCAP, dan WOWS. Dua URL berisi spasi literal; setelah spasi di-encode sebagai `%20`, kedua PDF juga berhasil diambil. Semua 38 PDF berhasil diekstrak teksnya; lembar kontak halaman pertama ditinjau visual. Dokumen multi-halaman/keputusan yang masih perlu pencocokan rinci tetap berstatus belum diverifikasi visual per halaman.
- PDF FLMC 1 Nov 2023 (`Peng-S-00007/BEI.PLP-11-2023`) menyatakan suspensi di seluruh pasar sejak Sesi I tanggal 1 Nov 2023. Ini memberi bukti suspensi terdahulu sebelum UPT FLMC 2 Jan 2024, tetapi tanggal efektif pembukaan pada UPT dan detail cakupan pasar tetap perlu dicocokkan langsung sebelum impor.
- PDF UPT kode tunggal menunjukkan tanggal API bukan selalu tanggal efektif: GPSO UPT API 6 Okt 2025 berlaku 7 Okt; NIRO UPT API 18 Nov 2025 berlaku 19 Nov; MDIA UPT API 21 Agu 2026 berlaku 24 Agu. Seri PDF GPSO, MDIA, NIRO, FLMC, dan WOWS berulang kali merujuk nomor SPT spesifik; gunakan rujukan di dalam PDF untuk membentuk episode, bukan kedekatan tanggal API saja.
- Kasus OCAP berbeda: PDF April 2024 menunjukkan suspensi seluruh pasar; UPT Mei dan Agustus 2024 hanya membuka Pasar Negosiasi untuk crossing. UPT November 2024 juga membuka Pasar Negosiasi sementara dan menyatakan suspensi seluruh pasar akan diberlakukan kembali setelah crossing atau paling lambat pukul 14.15. Ketiganya tidak boleh ditafsirkan sebagai pembukaan penuh yang berkelanjutan.
- Pemeriksaan visual ringkas dan teks tidak menyelesaikan 12 kode tanpa pasangan sampel: ARTI, ELTY, FLMC, GPSO, INAF, MDIA, NIRO, OCAP, VIVA, WOWS, XSBC, XSSI. Enam kode tanpa rekaman berkode tunggal (ARTI, ELTY, INAF, VIVA, XSBC, XSSI) masih memerlukan pencarian di PDF multi-kode dan pengumuman sebelum/di luar cakupan API. Kode dengan API tunggal juga belum lengkap riwayat episodenya hanya karena 38 PDF tersedia.
- PDF dan teks hasil ekstraksi berada di `.uji-data/riset-idx/riwayat-api-pdf/`; lembar kontak ada di folder yang sama. Tidak ada basis data yang diubah atau data yang diimpor. Tes kode tidak dijalankan karena tahap ini hanya pemeriksaan sumber.
- Tahap berhenti sesuai K4. Berikutnya: tinjau setiap pasangan UPT/SPT visual dan rekonsiliasi semua 56 PDF multi-kode—termasuk aksi baru/dipertahankan, tanggal efektif, pasar, nomor pengumuman, koreksi, dan duplikat—kemudian minta tinjauan pengguna sebelum menyiapkan impor.

### Rekonsiliasi per kode: pasangan dari nomor yang dirujuk UPT (12 Okt 2026)

- Cara menetapkan pasangan diubah: nomor SPT penyebab dibaca dari **kutipan di dalam PDF UPT sendiri** ("Sehubungan dengan"), bukan dari kedekatan tanggal API. Setiap nomor dicari di **kepala** dokumen pada dua kumpulan PDF yang sudah ada (56 lampiran multi-kode + 38 PDF riwayat kode tunggal), dan hanya sah bila dokumen itu benar-benar memuat kodenya (baris tabel, atau identitas dokumen untuk pengumuman satu emiten). Nomor yang hanya muncul di badan teks tidak dihitung sebagai nomor terbit.
- Keluaran: `.uji-data/riset-idx/rekonsiliasi-upt-per-kode-20261012.csv` — **41 baris** (39 baris tinjauan 11 Okt + 2 baris `2026-02-20_UPT_11` yang tertinggal: AKKU dan INPS), dengan kolom nomor UPT, tanggal dokumen vs tanggal API, pasar, sesi (termasuk sesi per kode bila tabel UPT punya kolomnya), nomor SPT rujukan, berkas PDF-nya, status kode di tabel SPT, episode terakhir, catatan koreksi, dan kalimat keputusan sebagai bukti. Ringkasan: `rekonsiliasi-upt-per-kode-20261012.txt`; verdict mentah: `verdict-upt-20261012.{json,txt}`.
- Hasil: **34 `TERKONFIRMASI`** · **4 `DUPLIKAT_REKAMAN_API`** · **1 `KOREKSI_BUKAN_PENCABUTAN_PENUH`** · **2 `TERKONFIRMASI_TANPA_PDF_SPT`** (ARTI, ELTY).
- Enam belas baris yang tadinya "tanpa kandidat" ternyata punya rujukan tegas: XSBC/XSSI → `Peng-S-00021/BEI.PLP/07-2024` (SPT_45); NIRO/WOWS/MDIA/VIVA/INAF/GPSO → `Peng-S-00005/BEI.PLP/02-2024` (SPT_51); FLMC → `Peng-S-00007/BEI.PLP-11-2023` (PDF riwayat API); OCAP → `Peng-SPT-00003/BEI.PP3/04-2024` (PDF riwayat API). Yang benar-benar tanpa PDF SPT hanya ARTI dan ELTY, sebab rujukannya berasal dari 2021–2023, di luar cakupan API 12 Okt 2023–09 Okt 2026.
- Empat koreksi yang mengubah tafsir: (a) `2024-02-20_UPT_48.pdf` dan `…_UPT_49.pdf` **identik byte-per-byte** (nomor sama `Peng-UPT-00003/BEI.PLP/02-2024`) sehingga delapan baris API = empat peristiwa, dan kembar lain (SPT_31≡SPT_32, SPT_26≡SPT_27, SPT_05≡SPT_07) tidak boleh dihitung dua kali; (b) OCAP `Peng-UPT-00002/BEI.PP3/05-2024` **bukan pencabutan penuh** — hanya Pasar Negosiasi untuk crossing lalu disuspensi kembali sesi yang sama; (c) nomor SPT di UPT INAF/GPSO tercetak `Peng-S-00005/BEI.PLP/05-2024` sedangkan dokumen yang dimaksud bernomor `Peng-S-00005/BEI.PLP/02-2024` (selisih bulan pada dokumen sumber, dicatat apa adanya); (d) status `Aktif` pada tabel SPT berarti kode **baru** disuspensi — terukur empat episode berumur hari (CLAY/GTBO/MGLV/SAGE/SHID 18→19 Feb 2026; GPSO/PTDU 17→18 Feb 2025; AKKU/INPS 18→20 Feb 2026; XSBC/XSSI 1→3 Jul 2024).
- Temuan kecil yang ikut tercatat: sesi berbeda per kode pada satu UPT yang sama (GPSO Pra-pembukaan vs PTDU Sesi I Periodic Call Auction); tanggal dokumen tidak selalu sama dengan tanggal API/nama berkas (MYTX 04-02-2026 vs 2026-02-05, UPT_48/49/50 19-02-2024 vs 2024-02-20); dan SPT FLMC 1 Nov 2023 tidak konsisten di dalam dirinya sendiri (tabel: `Suspensi di Seluruh Pasar`, kalimat keputusan: `di Pasar Reguler dan Pasar Tunai sejak sesi I 1 November 2023`).
- Batas bukti: pemeriksaan berbasis **teks hasil ekstraksi** seluruh 27 PDF UPT dan paragraf keputusan + baris tabel kode pada SPT pasangannya, bukan pemeriksaan visual halaman per halaman; kolom `bukti_kutipan_upt` diisi kalimat keputusan supaya bisa ditilang langsung ke PDF. Rincian per kode ada di `docs/riset-suspensi-multi-kode-2026-10.md`.
- Verifikasi perintah: `.\.venv\Scripts\python -m pytest` — **765 lulus** (59 detik). Tidak ada perubahan kode pada tahap ini; suite dijalankan sebagai pemeriksaan keadaan.
- Tidak ada impor dan tidak ada perubahan basis data. Tahap berhenti sesuai K4: yang menunggu keputusan pengguna adalah **apakah 41 baris ini boleh disiapkan sebagai impor append-only**, termasuk perlakuan untuk baris kembar, OCAP (bukan pencabutan penuh), XSBC/XSSI (reksa dana, bukan saham), dan ARTI/ELTY yang SPT-nya di luar cakupan.

### Jawaban pengguna atas keputusan langkah + pengesahan usulan (12 Okt 2026)

- Setelah tahap rekonsiliasi per kode ditutup untuk tinjauan, saya mengajukan enam keputusan langkah dan empat konfirmasi. Pengguna menjawab **"sesuai rekomendasi"**, dan seluruhnya dicatat sebagai keputusan: **K36** bentuk masuk rekonsiliasi (berkas + `--impor`, bukan pemeta otomatis), **K37** urutan (seluruh 56 SPT multi-kode lebih dulu; penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` dilepas paling akhir), **K38** satu dokumen = satu peristiwa, **K39** pembukaan satu-pasar bukan penutup episode (ketiga UPT OCAP), **K40** efek non-saham (XSBC/XSSI) diberi penanda di `keterangan`, **K41** kode ber-SPT di luar cakupan (ARTI, ELTY) tetap dicatat dengan penanda, **K42** U2–U17/U19/U22/U23 disahkan sebagai keputusan, **K43** parameter bursa bersumber sekunder tetap berlabel apa adanya sampai SK primer terjangkau, **K44** penggabungan daftar emiten IDX↔KSEI tetap ditahan dengan aturannya ditulis sekarang, **K45** P29/P30 disahkan apa adanya. Keputusan teknisnya **T59**; bagian 2 dan bagian 3 kini berstatus riwayat, bukan daftar tunggu.
- Tidak ada kode yang diubah, tidak ada impor, dan tidak ada basis data yang disentuh; suite terakhir **765 lulus** (12 Okt 2026). Rencana kerja berurutan untuk sesi berikutnya ada di bagian atas `docs/lanjutan.md`.

### Rekonsiliasi per kode sisi SPT multi-kode (16 Okt 2026)

- Langkah 1 rencana K36–K41 dikerjakan: **seluruh rekaman SPT multi-kode direkonsiliasi per kode**. Terukur: **29 rekaman SPT = 26 peristiwa** (tiga pasang dokumen kembar: `SPT_31`≡`SPT_32`, `SPT_26`≡`SPT_27`, `SPT_07`≡`SPT_05`), **1.118 baris** per rekaman × kode (1.090 peristiwa unik), **162 kode unik**. Catatan istilah: angka "56" pada K37 adalah jumlah **rekaman multi-kode** (29 SPT + 27 UPT), bukan jumlah SPT — yang direkonsiliasi di sini ke-29 rekaman SPT itu.
- Berkas hasil (tanpa impor, tanpa perubahan basis data): `rekonsiliasi-spt-per-kode-20261016.csv` · `ringkasan-suspensi-per-kode-20261016.csv` (162 kode) · `rekonsiliasi-spt-per-kode-20261016.txt` · `verdict-spt-20261016.json`, semuanya di `.uji-data/riset-idx/`. Rincian metode, tabel ke-29 rekaman, dan temuannya di `docs/riset-suspensi-multi-kode-2026-10.md`.
- Aturan tafsir yang dipakai (K37): `Aktif`/`Active` pada kolom *Status Perdagangan Efek Saat Ini* berarti kode **baru disuspensi** oleh pengumuman itu, `Suspensi di …` berarti **dipertahankan**. Setiap dokumen diperiksa terhadap angka yang disebut kalimatnya sendiri (butir aksi baru, butir "tetap", dan "terdapat N Perusahaan Tercatat" di badan pengumuman). Hasilnya: **satu rekaman** tidak cocok dengan angka butirnya (20 Feb 2024 — temuan (a) di bawah), dan **satu lagi** tidak cocok antara badan pengumuman dan daftarnya (16 Jun 2025 menyebut 6 saham, daftarnya 7 kode — temuan (c)); sisanya cocok.
- Empat temuan yang mengubah tafsir: (a) **pengumuman 20 Feb 2024 (`Peng-S-00006/BEI.PLP/02-2024`) bertentangan di dalam dirinya** — kalimat keputusan menyatakan suspensi **baru** untuk 34 kode sejak Sesi I 20 Feb 2024, sedangkan kolom status tabelnya tidak memuat satu pun `Aktif`; ke-34 baris diberi penanda `PERTENTANGAN_KOLOM_STATUS` dan **belum diputuskan** mana yang dipakai saat impor; (b) **empat kode berstatus `Aktif` dua kali dalam 30 hari** (`ASMI`, `COAL`, `LCKM` 30 Jun → 30 Jul 2026; `MTFN` 30 Jun → 30 Jul 2025) tanpa pembukaan yang terpantau di antaranya; (c) **satu baris tabel memuat dua kode efek** (`MYRX dan MYRXP` pada 16 Jun 2025; `CNTB` pada baris `CNTX` 1 Jul 2026) sehingga pengumuman yang menyebut 13 Perusahaan Tercatat memuat 14 kode; (d) **80 dari 162 kode tidak punya riwayat suspensi berkode tunggal di API** — bagi kode itu pengumuman massal adalah satu-satunya catatan, dan **35 kode** tidak pernah muncul sebagai `Aktif` (episodenya sebelum cakupan API 12 Okt 2023 atau dari pengumuman jenis lain).
- Pemeriksa silang yang dipakai: **API berkode tunggal** (`notasi-khusus.csv`, 963 baris suspensi) dan **rekonsiliasi UPT 12 Okt 2026** (41 baris). Kecocokannya rapi untuk 27 kode yang punya penutup UPT (`XSBC`/`XSSI` 1 Jul → 3 Jul 2024; `AKKU` 18 Feb → 20 Feb 2026; `TRUE` 30 Jun 2026 → 18 Sep 2026), dan itulah bahan untuk langkah berikutnya (menutup episode).
- Ikut dicatat: **14 kode** di rekonsiliasi ini tidak ada di daftar emiten KSEI (916 kode) maupun daftar resmi IDX (962 kode) — dua di antaranya reksa dana (K40), dua kode kedua satu perusahaan. Jalur tulis `notasi_khusus` tidak menuntut kodenya ada di tabel `emiten`, jadi barisnya tetap bisa dimuat; keadaannya disebut supaya tidak terbaca sebagai kelalaian.
- Batas bukti: seluruhnya berbasis **teks hasil ekstraksi** 29 PDF SPT + kalimat keputusannya, bukan tinjauan visual halaman per halaman. Kolom `bukti_kutipan` memuat potongan kalimat keputusan supaya bisa ditilang langsung ke PDF.
- Verifikasi perintah: `.\.venv\Scripts\python -m pytest` → **765 lulus** (55,95 detik). Tidak ada kode yang diubah pada tahap ini; suite dijalankan sebagai pemeriksaan keadaan.
- Tidak ada impor dan tidak ada perubahan basis data. Penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` **belum dilepas** (K37: dilepas paling akhir). Tahap berhenti sesuai K4; yang menunggu keputusan pengguna adalah **apakah hasil ini boleh disiapkan sebagai berkas impor per kode** (langkah 3 rencana), termasuk perlakuan untuk keempat temuan di atas.

### Keputusan pengguna atas perlakuan impor hasil rekonsiliasi (16 Okt 2026)

- Empat pertanyaan perlakuan impor diajukan bersama laporan tahap, dan pengguna menjawab **"putusan sesuai rekomendasi, catat dulu, lanjut sesi berikutnya"** — jadi seluruhnya dicatat sebagai keputusan: **K46** (pengumuman 20 Feb 2024 **ditahan** sampai tinjauan visual; 34 barisnya tetap ada di berkas rekonsiliasi dengan penanda), **K47** (empat kode `Aktif` dua kali dalam 30 hari **disiapkan apa adanya** dengan penanda), **K48** (baris tabel dua kode → **penanda cukup**, satu baris impor per kode), **K49** (kode tanpa riwayat API / di luar daftar emiten → **dimuat apa adanya** dengan penanda). Keputusan teknis bentuk berkas impornya dicatat sebagai **T60** di `docs/arsitektur.md`.
- Pengguna secara eksplisit meminta **tidak ada kode yang dikerjakan pada tahap ini** ("jangan ngoding dulu"), sehingga berkas impornya **belum ditulis** dan impornya **belum dijalankan**. Yang dikerjakan hanya pencatatan: baris K46–K49 di bagian 1, T60 di `docs/arsitektur.md`, dan pembaruan `docs/lanjutan.md` sebagai titik lanjut sesi berikutnya.
- Verifikasi: `.\.venv\Scripts\python -m pytest` → **765 lulus** (48,51 detik; pemeriksaan keadaan yang sama pada akhir tahap rekonsiliasi: 765 lulus · 55,95 detik). Tidak ada kode, basis data, atau berkas data yang berubah; suite dijalankan sebagai pemeriksaan keadaan.

### Berkas impor per kode ditulis dan dimuat ke basis data uji (16 Okt 2026, sesi 4)

- Langkah 3 rencana K36–K41 dikerjakan: **berkas impor per kode ditulis** dari hasil langkah 1 menurut bentuk T60, lalu **dimuat ke basis data uji**. Pembuatnya `.uji-data/riset-idx/buat-impor-suspensi.py` (tidak ikut git, seperti skrip rekonsiliasi); berkasnya `.uji-data/riset-idx/impor-suspensi-20261016/notasi-khusus.csv` beserta `bukti-keadaan.txt`. **Tanpa satu pun perubahan kode aplikasi.**
- Terukur: **171 baris impor** (159 kode unik) dari 162 kode di rekonsiliasi — **138 terbuka, 33 tertutup** oleh penutup UPT yang terkonfirmasi, **65 episode** bertanggal mulai proxy (penanda `TANGGAL_MULAI_TIDAK_DINYATAKAN_SUMBER_MANA_PUN`), **4 penanda K47**, dan **34 baris 20 Feb 2024 ditahan** (K46) sehingga tidak ikut menyusun satu baris pun.
- **Penutup UPT harus dibaca dari dua sumber.** Rekonsiliasi UPT (41 baris, 31 kode) saja **melewatkan penutup yang nyata**: `LCKM` punya `Peng-UPT-00022/BEI.PLP/11-2025` (10 Nov 2025) di kolom `upt_penutup_nomor` rekonsiliasi SPT tetapi tidak muncul di rekonsiliasi UPT, sehingga tanpa penggabungan itu episode 2025 dan 2026 menyatu dan tanggal mulai 2026 hilang. Sesudah digabung, **31 dari 37 penutup terpakai**; 6 sisanya tidak dipakai karena menutup suspensi yang **lebih tua** daripada rekaman pertama kode itu (`ARTI`, `BAPI`, `ELTY`, `FLMC`, `MTFN`, `OCAP`) — keadaannya ditulis di `keterangan` barisnya, bukan disembunyikan.
- **T60 ternyata tidak bisa dipakai apa adanya**, dan itu diputuskan sebagai **K50**: T60 menuntut satu baris per (peristiwa × kode) = 1.090 baris, sedangkan 850 di antaranya adalah kode berstatus `dipertahankan` yang **tidak menyatakan tanggal mulai**. Memakai tanggal pengumuman untuk mereka berarti memasang tanggal mulai palsu untuk 850 baris — persis yang dicegah aturan keras 1 & 3 dan persis kekeliruan yang dicegah K46. Yang dipakai: satu baris **per (kode × episode)**, dengan seluruh pengumuman `dipertahankan` masuk `keterangan` baris itu.
- **Temuan yang mengubah tafsir K46, terukur saat berkasnya disusun:** ke-34 kode yang pengumumannya ditahan **semuanya sudah berstatus `Suspensi di …` pada rekaman sebelum 20 Feb 2024**, jadi tanggal 20 Feb 2024 memang bukan tanggal mulai suspensi mereka. Akibatnya yang ditahan hanyalah **barisnya**, bukan kodenya: ke-34 kode tetap mendapat baris (tanggal mulai proxy + penanda `DITAHAN_K46_PENGUMUMAN_20_FEB_2024`), sehingga tidak ada kode yang hilang dari data hanya karena tinjauan visualnya belum dilakukan.
- Impor ke **basis data uji** (`.uji-data/uji-impor-suspensi`, salinan `.uji-data/mejasaham`): **171 baris baru, 0 sudah ada dan sama**, keluar 0. Bukti sebelum/sesudah: notasi 4.552 → 4.723 baris, suspensi 1.926 → 2.097, suspensi terbuka 142 → 280. `--saring`: likuid **205 → 201**; keempat kode likuid yang keluar karena suspensi multi-kode **`KJEN`, `SINI`, `UNSP`, `ZATA`** — keempatnya kini tersuspensi terbuka dan sebelumnya tidak punya riwayat API, yaitu lubang yang memang ditutup tahap ini.
- **Mekanisme pelepasan penanda dibuktikan bekerja, tanpa perubahan kode** (dicatat sebagai **K51**). Caranya **bukan** menyunting `konfigurasi/notasi-khusus.csv`: berkas itu **sudah tertimpa sesi lain** dan kini hanya memuat 122 baris `papan_pemantauan`, sedangkan basis datanya memuat 2.276 baris berpenanda — berkas yang lebih sempit daripada basis data tidak bisa melepas apa pun. Jalannya: **bangun berkas dari basis data** (2.447 revisi terkini), lepas penandanya, impor ulang sebagai revisi baru. Terbukti di `.uji-data/uji-impor-suspensi-langkah4`: **2.154 baris baru** tertulis, dan `--saring` berubah dari **PERINGKAT SEMENTARA** menjadi **Kandidat teratas** (likuid tetap 201, lolos saring 9). Penandanya sendiri **belum dilepas** — menunggu persetujuan pengguna.
- Verifikasi: `.\.venv\Scripts\python -m pytest` → **765 lulus** (20,23 detik). Seluruh bukti angka di `.uji-data/uji-impor-suspensi/bukti-1` … `bukti-9`. **Tidak ada kode aplikasi, skema, atau `.uji-data/mejasaham` yang disentuh** — impornya hanya ke salinan basis data uji.
- **Koreksi angka pada catatan 16 Okt 2026 di atas.** Tercatat "1.118 baris (1.090 peristiwa unik), 154 baris mulai disuspensi dan 936 dipertahankan" — dua angka terakhir itu **sudah bersih dari rekaman kembar**, sedangkan 1.118 baris adalah angka mentahnya. Rinciannya: 158 baris `mulai_disuspensi` (154 unik) dan **960** baris `dipertahankan` (936 unik), jumlahnya 1.118 − 28 rekaman kembar = 1.090 peristiwa unik. Angka 1.118, 1.090, 162, dan 29 rekaman tetap benar; yang perlu dibaca sebagai "sesudah kembar dibuang" hanya pasangan 154/936 itu. Ditulis di sini supaya penjumlahan yang tidak bertemu tidak terbaca sebagai data yang hilang.

### Keputusan atas pelepasan penanda: dilepas, pelaksanaannya sesi berikutnya (16 Okt 2026, sesi 4)

- Setelah laporan tahap langkah 3, saya mengajukan **satu** keputusan: bolehkah penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` dilepas (langkah 4/K37), dengan rekomendasi **ya — dilepas**, sebab rekonsiliasi yang menjadi syaratnya sudah selesai dan dimuat, dan pelepasan itu **tidak menuntut perubahan kode** (K51). Pengguna menjawab **"keputusan sesuai rekomendasi mu saja, catat dulu biar dilanjutkan di sesi berikutnya"**, dan sekaligus meminta **tidak ada pekerjaan teknis** pada sesi ini.
- Karena itu dicatat sebagai **K52**: penandanya **dilepas**, dan **pelaksanaannya ditunda** ke sesi berikutnya beserta urutan lima langkahnya (cadangkan dulu · bangun berkas dari revisi terkini basis data · impor sebagai revisi baru · perbarui berkas konfigurasi supaya penandanya tidak masuk lagi · buktikan `--saring` berbunyi "Kandidat teratas").
- Verifikasi sesi pencatatan ini: `.\.venv\Scripts\python -m pytest` → **765 lulus** (pemeriksaan keadaan; tidak ada kode yang diubah). Pelepasan penandanya sendiri **belum dijalankan** — tidak pada basis data utama, dan salinan uji yang dipakai membuktikan mekanismenya sudah dibuang setelah buktinya diambil (`bukti-6`/`bukti-7` beserta cara membuat ulangnya).

### Pelepasan penanda notasi dijalankan atas basis data lokal (16 Okt 2026, sesi 5)

- **Langkah 4 rencana K36–K41 (K52) dikerjakan sampai selesai, berurutan, atas basis data `.uji-data/mejasaham`.** Tanpa satu pun perubahan kode aplikasi. Urutannya persis seperti yang dikunci: (1) **cadangan lebih dulu** — `.uji-data/mejasaham-cadangan/20261016T165510578553+0700`; (2) **berkas impor langkah 3 dimuat ke basis data utama** (sebelumnya hanya ke salinan uji) — **171 baris baru**, keluar 0, `--saring` likuid **205 → 201**, masih PERINGKAT SEMENTARA; (3) **berkas turunan basis data tanpa penanda** dibangun pembuat `.uji-data/riset-idx/buat-tanpa-penanda.py` — 2.447 revisi terkini, **2.154 penanda dilepas**, dan berkasnya **dibaca ulang lewat `mejasaham.berkas.baca_folder`** (bulat-balik sama persis, termasuk kolom `keterangan` yang memuat `;` sehingga harus dikutip); (4) **impor sebagai revisi baru** — **2.447 baris baru**, 0 sudah ada dan sama, keluar 0, snapshot 8; (5) **berkas konfigurasi diperbarui** — `konfigurasi/notasi-khusus.csv` diganti turunan itu (berkas lama disimpan sebagai `notasi-khusus-sebelum-diganti.csv`); (6) **dibuktikan**: `--saring` berbunyi **"Kandidat teratas"** (bukan lagi PERINGKAT SEMENTARA), likuid **201**, lolos saring 9, dinilai 9.
- Keadaan basis datanya sesudahnya: **7.170 baris notasi**, **2.447 revisi terkini**, **0 baris terkini berpenanda**, suspensi terbuka **489**, **654 kode** unik. Penanda lain **tetap** di `keterangan` dan itu memang maksudnya: 1 baris `DITAHAN_K46_…`, 3 penanda `AKTIF_DUA_KALI_DALAM_30_HARI`, dan 65 episode berketerangan *"tanggal mulai tidak dinyatakan sumber mana pun"*.
- **Dua angka pada catatan lama dikoreksi di sini, bukan dibiarkan.** (a) K51 dan tabel jebakan `docs/lanjutan.md` mencatat `konfigurasi/notasi-khusus.csv` "hanya memuat 122 baris" — **itu berkas lain**: yang dimaksud adalah `.uji-data/uji-sektor/konfigurasi/notasi-khusus.csv` (161 baris berkas / 122 baris data) dan `.uji-data/konfigurasi/notasi-khusus.csv` (26 baris). Berkas yang benar-benar dipakai basis data utama memuat **2.276 baris data** (2.303 baris berkas, terakhir ditulis 11 Okt 2026 18:xx, diimpor dua kali sehingga tabelnya 4.552 baris). Aturan K51 **tidak berubah** karena koreksi ini — membangun berkas dari basis data tetap jalan yang benar — tetapi premis "berkasnya lebih sempit" salah alamat. (b) Impor revisi barunya menulis **2.447 baris**, bukan 2.154: angka 2.154 adalah jumlah baris **berpenanda**, sedangkan 293 baris sisanya ikut tertulis karena `sumber` ikut dibandingkan saat memutuskan "sudah ada dan sama" (`mejasaham/ingesti.py`, `_ISI_PER_TABEL`) — isi selain `sumber` tidak berubah sedikit pun.
- Verifikasi: `.\.venv\Scripts\python -m pytest` → **765 lulus** (19,51 detik; folder sementara `.tmp\t36`). Bukti lengkap: `.uji-data/uji-lepas-penanda/bukti-0` … `bukti-7` (saring sebelum · cadangan · impor langkah 3 · saring sesudahnya · pembangun berkas · impor tanpa penanda · saring "Kandidat teratas" · keadaan + hash berkas), berkas turunan di `.uji-data/riset-idx/tanpa-penanda-20261016/`, pembuatnya `.uji-data/riset-idx/buat-tanpa-penanda.py`.
- **Yang tidak ikut selesai dan tidak boleh dianggap selesai:** tinjauan **visual** baris pengumuman 20 Feb 2024 (K46; 34 kode yang barisnya berpenanda) dan 65 episode bertanggal mulai proxy. Keduanya tetap disebut di `keterangan` barisnya, jadi pelepasan penanda tidak menghapus jejaknya.

### Tinjauan visual pengumuman 20 Feb 2024 (K46) dan dua temuan yang muncul darinya (16 Okt 2026, sesi 6)

- **Tinjauan yang dituntut K46 sudah dijalankan.** Kedua halaman `2024-02-20_SPT_47.pdf` dirender jadi gambar lalu **dilihat** — perendernya memakai **PySide6 `QtPdf` yang sudah terpasang** (`QPdfDocument.render`), jadi tidak ada dependensi baru dan tidak ada peramban. Yang terlihat: tabelnya persis **empat kolom** (No · Kode · Nama Perusahaan · *Status Perdagangan saat ini*), **tanpa** catatan kaki, tanda bintang, legenda, atau kolom kelima. Jadi halaman itu sendiri **tidak memuat penanda apa pun** yang bisa memutuskan "status sebelum" versus "status sesudah" — dan itu dilaporkan apa adanya, bukan ditutupi dengan tafsir.
- **Pertanyaannya diselesaikan dari rekaman, bukan dari halamannya.** Status ke-34 kode pada rekaman terakhir **sebelum** pengumuman itu (30 Jan/16 Feb 2024) dibandingkan dengan isi kolom status di pengumuman itu: **identik untuk 34 kode, 0 berbeda** (24 *Suspensi di Seluruh Pasar* + 10 *Suspensi di Pasar Reguler dan Tunai* di kedua sisi). Karena ruang lingkup tindakan 20 Feb 2024 (Pasar Reguler dan Pasar Tunai) sudah berlaku untuk ke-34 kode sebelum tanggal itu, **tidak ada status perdagangan yang berubah** pada 20 Feb 2024 — dengan tafsir kolom mana pun. Kesimpulannya: tanggal 20 Feb 2024 **tidak boleh** menjadi `tanggal_mulai` episode baru.
- **Bukti terkuat menyebut pengumumannya sendiri.** UPT MTFN `Peng-UPT-00011/BEI.PLP/08-2024` (29 Agu 2024) mencabut **delapan** pengumuman sekaligus, dan nomor 6 di antaranya adalah `Peng-S-00006/BEI.PLP/02-2024`. Suspensi 20 Feb 2024 memang ada, tetapi **menyatu** dengan suspensi MTFN yang sudah berjalan dan dicabut bersama-sama pada 29 Agu 2024.
- **Temuan 1 — episode MTFN 2023–2024 hilang dari data.** Baris MTFN yang ada sekarang `suspensi` mulai **2025-06-30** (proxy) dan dibiarkan terbuka, tetapi `keterangan`-nya memuat dokumen 2023-10-30, 2024-01-30, 2024-07-02, dan 2024-07-31 — yaitu episode **lama** yang dicabut 2024-08-29, bukan episode 2025 ini. Terukur: dari **2.447 baris terkini**, **hanya 1 baris** yang menyebut berkas lebih tua daripada `tanggal_mulai`-nya sendiri, dan baris itu MTFN. Sebabnya di `_kelompokkan` pembuat berkas impor: `yatim` yang lebih tua daripada seluruh episode ditempelkan ke `episode[0]`, dan UPT yang jatuh sebelum tanggal mulai episode pertama tidak pernah dipakai menutup apa pun (penutup MTFN karena itu berstatus `TIDAK DIPAKAI` di `bukti-keadaan.txt` langkah 3).
- **Temuan 2 — K41 belum dijalankan atas data.** K41 (disetujui 12 Okt 2026) menetapkan `ARTI` dan `ELTY` tetap dicatat dari kutipan UPT-nya + penanda "di luar cakupan API". Terukur: penanda itu **0 kali** di seluruh `notasi_khusus` (semua revisi) dan **0 kali** di berkas impor; `ELTY` **0 baris** di basis data dan 0 baris di berkas impor; `ARTI` punya baris tetapi dari jalur lain (mulai 2024-07-01) tanpa penanda yang diminta. *Pemeriksaannya sengaja diarahkan ke data, bukan ke dokumen* — dan yang ditemukan adalah janji yang belum ditepati, bukan sekadar salah tafsir. Usulan bentuk barisnya diajukan sebagai **U25** (mengapa bukan tanggal UPT-nya sendiri: itu tanggal **pencabutan**, sehingga barisnya menjadi bersuspensi nol hari).
- **Yang dikerjakan sesi ini hanya tinjauan + pencatatan.** Tidak ada perubahan kode aplikasi, tidak ada impor, dan tidak ada baris basis data yang ditulis. Perbaikannya menuntut keputusan lebih dulu → **U24** (perlakuan baris 20 Feb 2024 setelah tinjauan: penanda dilepas, dan episode MTFN yang hilang dibentuk) dan **U25** (bentuk baris K41). Keduanya di bagian 2, **belum dikunci pada saat laporan itu ditulis** — lalu **diputuskan pengguna pada sesi yang sama** menjadi **K53/K54** (lihat bagian di bawah).
- Verifikasi: `.\.venv\Scripts\python -m pytest` → **765 lulus** (26,73 detik; folder sementara `.tmp\t37`). Bukti tinjauan: `.uji-data/uji-tinjauan-k46/` (`bukti-1`/`bukti-2` kedua halaman, `bukti-3` teks ekstraksi, `bukti-4` UPT penutup MTFN, `bukti-5` perbandingan status sebelum–pada, `bukti-6` dokumen lama menempel, `bukti-7` keadaan 34 kode, `bukti-8` rantai ARTI, `bukti-9` pemeriksaan K41, `bukti-keadaan.txt`), pembuatnya `.uji-data/riset-idx/tinjauan-k46/` (semuanya read-only terhadap basis data).

### Keputusan pengguna atas U24/U25: dikunci sebagai K53/K54, pelaksanaannya sesi berikutnya (16 Okt 2026, sesi 6 lanjutan)

- Setelah laporan tahap tinjauan (#16), saya mengajukan **dua** keputusan dengan rekomendasi: **U24** (perlakuan baris pengumuman 20 Feb 2024 sesudah tinjauan visualnya) dan **U25** (bentuk baris K41 ketika hanya pencabutannya yang dinyatakan sumber). Pengguna menjawab **"jangan ngoding dulu, keputusan sesuai rekomendasi mu, catet aja dulu, kulanjutkan di sesi berikutnya"**.
- Keduanya dicatat sebagai keputusan dan **dikunci**: **K53** (penanda `DITAHAN_K46_…` **dilepas**; 20 Feb 2024 **tidak** dipakai sebagai `tanggal_mulai`; pengumuman itu masuk `keterangan` episode yang sedang berjalan; **episode MTFN 2023–2024 yang hilang dibentuk** — proxy ≤ 2023-10-30 → `tanggal_selesai` 2024-08-29 dari UPT-nya) dan **K54** (`ELTY` 2023-07-03 → 2023-10-19 · `ARTI` 2021-11-30 → 2023-11-23, memakai tanggal pengumuman SPT terawal yang dirujuk UPT + penanda "di luar cakupan API"). Baris **U24/U25 di bagian 2 ditandai sudah diputuskan**, dan catatan pembuka bagian 2 diperbarui supaya tidak lagi berbunyi "menunggu jawaban".
- **Pelaksanaannya ditunda ke sesi berikutnya**, sesuai permintaan pengguna: **tidak ada pekerjaan teknis pada sesi pencatatan ini.** Tidak ada perubahan kode aplikasi, tidak ada impor, dan tidak ada baris basis data yang ditulis; urutan pelaksanaannya (cadangkan dulu · bangun berkas dari revisi terkini · impor revisi baru · perbarui berkas konfigurasi · buktikan `--saring` tetap "Kandidat teratas") tercatat di `docs/lanjutan.md` bagian 4 **aksi #17**.
- Verifikasi sesi pencatatan ini: `.\.venv\Scripts\python -m pytest` → **765 lulus** (19,90 detik; folder sementara `.tmp\t39`) — pemeriksaan keadaan; tidak ada kode yang diubah, tidak ada impor, dan tidak ada baris basis data yang ditulis.

### Pelaksanaan K53 + K54 atas basis data lokal (16 Okt 2026, sesi 7)

- **Aksi #17 (`docs/lanjutan.md` bagian 4) dikerjakan sampai selesai atas basis data `.uji-data/mejasaham`, tanpa satu pun perubahan kode aplikasi.** Urutannya persis seperti K51/K52: (1) **cadangan lebih dulu** — `.uji-data/mejasaham-cadangan/20261016T172705653192+0700`; (2) berkas dibangun dari **revisi terkini basis data** — **2.447 baris** pada cadangan pra-impor, dan **2.450 baris** pada pembangunan ulang sesudahnya (hasilnya **byte-identik**, lihat butir idempotensi) — oleh pembangun baru `.uji-data/riset-idx/k53-k54/buat-k53-k54.py` — basis datanya dibuka **read-only**, penalaran bentuk `keterangan` **meminjam modul langkah 3** (`buat-impor-suspensi.py`) sebagai pustaka supaya bentuk barisnya sama; (3) **diimpor sebagai revisi baru**; (4) `konfigurasi/notasi-khusus.csv` diperbarui (berkas lama disimpan sebagai `notasi-khusus-sebelum-k53.csv`); (5) dibuktikan `--saring` **tetap** berbunyi **"Kandidat teratas"** — likuid **201**, lolos saring **9**, dinilai 9, snapshot 10.
- **K53 dijalankan, dan aturan penempelannya ditentukan oleh data — bukan oleh "episode termuda".** Pengumuman `Peng-S-00006/BEI.PLP/02-2024` ditempelkan pada episode yang **memiliki rekaman SPT tepat sebelumnya** untuk kode itu (`2024-02-16_SPT_51.pdf` bagi hampir semua kode). Aturan yang lebih naif — "episode suspensi termuda yang sudah mulai" — **terbukti salah untuk `TECH`**: kode itu punya episode lain dari **jalur API** (mulai 2024-01-09) sehingga aturan naif menempelkan dokumen SPT itu ke episode API dan **memutus rantai SPT**-nya. Aturan naif itu tetap dihitung sebagai **pembanding** dan selisihnya dilaporkan per kode, jadi pilihannya bisa diperiksa; `COWL` juga punya dua episode (2023-10-12 API dan 2023-10-30 SPT) dan di situ kedua aturan **sepakat**. Setiap baris yang mendapat catatan juga menyebut **rekaman mana** yang membuktikan penempelannya.
- **Terukur sesudahnya** (`.uji-data/uji-k53-k54/bukti-9-ringkasan.txt`): **2.450 revisi terkini**; **33 episode** memuat catatan pelepasan K46 **beserta rincian penempelannya**; **0 baris terkini** masih memuat `DITAHAN_K46_PENGUMUMAN_20_FEB_2024` (yang **tetap** ada hanya di riwayat revisi lama — append-only); **2 baris** memuat penanda "di luar cakupan API" (`ELTY`, `ARTI`). **MTFN** kini punya **dua** episode suspensi: `2023-10-30 → 2024-08-29` (**tertutup** oleh `Peng-UPT-00011/BEI.PLP/08-2024`; lima dokumen 2023–2024 pindah ke situ, termasuk pengumuman 20 Feb 2024) dan `2025-06-30 → terbuka` (penanda K47 ikut tertulis lagi). **ELTY** `2023-07-03 → 2023-10-19`; **ARTI** `2021-11-30 → 2023-11-23` plus episode keduanya `2024-07-01 → terbuka` yang kini berlabel "episode 2 dari 2". Notasi di basis data: 7.170 → **9.654 baris** (append-only; revisi terkini tetap satu per kunci).
- **Tanggal mulai proxy K54 diperiksa ke dokumennya, bukan diketik ulang.** Teks kedua PDF UPT diparse dan tanggal **terawal** di bagian "Sehubungan dengan:" diambil — `ELTY` **2023-07-03**, `ARTI` **2021-11-30** — dan keduanya **sama** dengan yang diputuskan K54, jadi keputusannya terbukti cocok dengan sumbernya. Nomor SPT yang dirujuk diambil dari kolom `spt_nomor_dirujuk` kutipan UPT (7 nomor ELTY, 19 nomor ARTI).
- **Pembangunnya idempoten, dan itu diukur, bukan diklaim.** Ia membuang lebih dulu kalimat catatan yang **ditulisnya sendiri** sebelum menambah yang baru, sehingga membangun berkas dari basis data **sesudah** impor menghasilkan berkas **byte-identik** dengan yang dibangun dari **cadangan pra-impor** (SHA-256 sama: `D9328D41B21FE34C90EAA9D4A754906033EC42E3052C2F5A3093100311EAF50A`). Pemeriksaannya **126 syarat**, di antaranya: bentuk episode MTFN 2025-06-30 yang dibangun ulang **sama persis** dengan keluaran importer langkah 3 (jadi "episode yang hilang" itu bukan tafsir), lima dokumen MTFN 2023–2024 terbaca dan berpindah, `jenis`/tanggal sah, kunci unik, serta bulat-balik **2.450 baris** lewat `mejasaham.berkas.baca_folder`.
- **Impor dijalankan dua kali, dan sebabnya dicatat di sini apa adanya.** Impor pertama (17:27) memakai aturan penempelan "episode termuda" yang kemudian terbukti salah untuk `TECH`; berkasnya dibangun ulang dengan aturan pemilik rekaman SPT lalu diimpor lagi (17:32) — **34 baris baru, 2.416 sudah ada dan sama** (33 baris K53 yang catatannya berubah, ditambah baris API `TECH` yang catatannya dikembalikan). Sesuai aturan keras 3 impornya **tidak menimpa**: versi pertama tetap tersimpan sebagai revisi lama, dan revisi terkini adalah yang benar. `--saring` tidak berubah karenanya.
- Verifikasi: `.\.venv\Scripts\python -m pytest` → **765 lulus** (28,01 detik; folder sementara `.tmp\t38`). Bukti: `.uji-data/uji-k53-k54/bukti-0` … `bukti-10` (keadaan sebelum · cadangan · impor · keadaan sesudah · saring · impor koreksi · keadaan final · saring final · ringkasan + hash · pytest), pembangun & pemeriksa read-only di `.uji-data/riset-idx/k53-k54/`.
- **Temuan baru yang muncul di sini (dan pada saat itu belum diperbaiki) — menjadi aksi #18; sudah dijalankan 16 Okt 2026 (sesi 8), lihat bagian di bawah.** Kolom `keterangan` berkas impor langkah 3 memuat `;`, dan berkas itu ditulis dengan **penggabungan string**, bukan `csv.writer`. Pembaca impor mengambil kolom **sebanyak kepala saja** (`mejasaham/berkas.py`), sehingga **66 dari 171 baris** kehilangan seluruh isi sesudah `;` pertama **tanpa satu pun galat**. Terukur akibatnya di revisi terkini: penanda `TANGGAL_MULAI_TIDAK_DINYATAKAN_SUMBER_MANA_PUN` **0 kali** (padahal 65 episode berketerangan proxy), penanda `AKTIF_DUA_KALI_DALAM_30_HARI` hanya **3 dari 4** kode, dan `MTFN` kehilangan **1.326 karakter** (penanda K47 beserta kutipan keputusan). Yang membuktikan sebabnya: untuk **66 baris itu**, keterangan revisi terkini adalah **persis awalan** keterangan di berkas. Ukurannya di `.uji-data/riset-idx/k53-k54/potong-keterangan.txt`. Perbaikannya menuntut keputusan: menulis ulang 66 baris itu dari teks **lengkap** berkas langkah 3 (berkas turunan dengan `csv.writer` sudah terbukti bulat-balik, lihat T62 dan langkah ini), dan/atau membuat pembaca berkas **menolak** kolom berlebih alih-alih membuangnya diam-diam.

### Aksi #18 dijalankan: cacat `;` ditutup dari sisi data dan sisi pembaca (16 Okt 2026, sesi 8)

- **Keputusan pengguna:** atas aksi #18 (dua pilihan yang diajukan — memulihkan datanya saja, atau itu **plus** membuat pembaca berkas berisik), pengguna menjawab **"sesuai rekomendasi mu saja"** → **keduanya dikerjakan**. Aturan pembacanya dikunci sebagai **T64** di `docs/arsitektur.md`.
- **(a) Datanya dipulihkan, bukan dikarang.** Pembangun `.uji-data/riset-idx/k53-k54/buat-k53-k54.py` kini memulihkan `keterangan` dari **baris mentah** berkas impor langkah 3 (isinya dibaca dengan memecah baris apa adanya, karena pembaca berkas memang yang memotongnya). Syaratnya ketat dan bisa diperiksa: keterangan tersimpan — sesudah kalimat yang ditulis skrip itu sendiri dibuang — harus **awalan yang benar** dari keterangan berkas; kalimat penanda `DITAHAN_K46_…` dibuang karena penandanya sudah dilepas K53. **Terukur: 65 baris dipulihkan** dari 66 baris berkas yang memuat `;` — `MTFN` 2025-06-30 **tidak** ikut (barisnya sudah dibangun ulang K53 dengan daftar dokumen yang benar, jadi berkas lama memang bukan sumbernya) dan `ARTI` 2024-07-01 **tidak** dihitung (barisnya sudah lengkap; yang hilang hanya kalimat skrip ini).
- **Angka yang kembali** (`penanda` dihitung atas **revisi terkini**, `.uji-data/uji-aksi-18/bukti-2`): `penanda: TANGGAL_MULAI_TIDAK_DINYATAKAN_SUMBER_MANA_PUN` **0 → 66** (65 episode proxy + episode MTFN yang dibentuk K53) · `penanda: AKTIF_DUA_KALI_DALAM_30_HARI` **3 → 4** — keempat kode K47 (`ASMI`, `COAL`, `LCKM`, `MTFN`) kini lengkap · `kutipan keputusan:` **105 → 172**. `DITAHAN_K46_…` tetap **0** di revisi terkini, dan `di luar cakupan API` tetap **2** (K54).
- **(b) Pembacanya dibuat berisik** (`mejasaham/berkas.py`, `_periksa_kolom_berlebih`): baris dengan kolom **berlebih yang berisi** ditolak, dan pesannya menyebut **nama berkas, nomor baris, isi kolom berlebih yang akan hilang, kolom yang dikenal, penyebab tersering** (`;` di dalam nilai pada berkas yang ditulis dengan penggabungan string) **dan jalan keluarnya** (`csv.writer`). Kolom berlebih yang **kosong** (`;;` di ujung baris) tetap diterima — yang ditolak adalah **isi** yang hilang, bukan bentuk barisnya — dan kolom yang **hilang** tetap dibaca sebagai nilai kosong seperti sebelumnya. Bukti atas **berkas nyata**: berkas impor langkah 3 yang lama kini **ditolak** (diperiksa langsung oleh pembangun, bukan hanya oleh berkas uji).
- **Uji:** tiga uji baru di `tests/test_impor_berkas.py` (menolak kolom berlebih berisi; nilai yang dikutip terbaca utuh termasuk pemisahnya; kolom berlebih kosong tetap diterima). Dijalankan pada **kode lama** (worktree `HEAD`, `.uji-data/uji-aksi-18/bukti-5`): **1 gagal, 37 lulus** — yang gagal justru uji intinya (`DID NOT RAISE GalatIngesti`), dan dua lainnya memang tidak membedakan kode lama dari kode baru (dinyatakan apa adanya, bukan diklaim).
- **Urutannya seperti aksi sebelumnya:** cadangkan dulu (`.uji-data/mejasaham-cadangan/20261016T175015415236+0700`) · bangun berkas dari revisi terkini + pemulihan · impor (**65 baris baru, 2.385 sudah ada dan sama**, snapshot 11) · perbarui `konfigurasi/notasi-khusus.csv` · buktikan `--saring` **tetap** "Kandidat teratas" (likuid **201** · lolos saring 9) · `periksa-aksi-18.py` untuk angka penandanya.
- Verifikasi: `.\.venv\Scripts\python -m pytest` → **768 lulus** (20,42 detik; folder sementara `.tmp\t43`). Bukti: `.uji-data/uji-aksi-18/bukti-0` … `bukti-5`, pembangun & pemeriksa di `.uji-data/riset-idx/k53-k54/` (pembangunnya kini memeriksa **202 syarat**, termasuk segmen terakhir tiap baris yang dipulihkan harus sama dengan berkasnya).

### Panel jendela PySide6: lima layar PRD 11 (17 Okt 2026, sesi 9) — aksi #10, tahap **membaca**

- **Apa yang dikerjakan.** `mejasaham/ui/jendela.py` yang tadinya kerangka 21 baris kini berisi
  **lima layar PRD 11** — dasbor (11.1), screener (11.2), detail emiten & tesis (11.3), kalkulator
  risiko (11.4), jurnal & kepatuhan (11.5) — ditambah dua berkas baru:
  `mejasaham/ui/tabel.py` (bentuk tabel, **bebas Qt**, bisa diuji tanpa layar) dan
  `mejasaham/ui/pekerja.py` (pekerjaan berat di utas pekerja, supaya jendela tidak membeku).
  Keputusan teknisnya dikunci sebagai **T65** di `docs/arsitektur.md`.
- **Jendela tidak menghitung apa pun.** Tiap layar memanggil fungsi inti yang sama dengan baris
  perintah lalu menampilkan `ringkas()`-nya: `dasbor.susun`, `pengatur.jalankan_saring`,
  `jurnal.rekap`, `risiko.siapkan_masukan` + `hitung_untuk`. Karena itu angka di jendela dan
  angka di terminal tidak bisa berbeda diam-diam — dan itu dibuktikan, bukan diklaim: bukti-5
  membandingkan blok kalkulator risiko dari **keduanya** atas basis data yang sama, **24 baris,
  0 perbedaan**.
- **Tiga teks/aturan yang tadinya hanya ada di `cli.py` dipindahkan ke inti**, sebab jendela
  memakainya juga — dan salinan akan berbeda begitu salah satunya disunting:
  (a) `risiko.ringkas_hasil` — seluruh keluaran kalkulator (dipindah dari `_cetak_hasil_risiko`;
  `--hitung-risiko` **terbukti menghasilkan 29 baris yang sama persis** sesudah pemindahan itu,
  dibandingkan terhadap worktree `HEAD` atas basis data yang sama);
  (b) `pengatur.LaporanSaring.catatan_peringkat_kosong` — sebab daftar peringkat kosong, dengan
  ambangnya dipinjam dari `skor.AMBANG_KETERSEDIAAN_FAKTOR`, bukan angka yang ditulis ulang;
  (c) `kandidat.untuk_rencana` — aturan "rencana menuntut tesis" (PRD 9.6).
- **Cacat nyata yang tertangkap justru karena aturan itu dipindahkan, bukan disalin:** versi
  pertama panel risiko mengambil entri kandidat **pertama** untuk satu kode, sedangkan baris
  perintah menolak memilih diam-diam ketika kodenya punya beberapa entri. Sesudah dipindahkan,
  keduanya memakai aturan yang sama dan pesannya sama. Dua cacat lain ditemukan dari bukti atas
  data nyata, bukan dari dugaan: (i) `Pekerja` diberi metode `Panel.tugas` alih-alih **hasil**
  pemanggilannya, sehingga seluruh layar menampilkan "hasil" berupa fungsi; (ii) sesudah
  pemuatan gagal, kotak hasil **masih memuat angka pemuatan sebelumnya** — angka basi di sebelah
  pesan "GAGAL" terbaca sebagai jawaban atas isian yang baru, dan sekarang dibuang oleh
  `Panel.kosongkan()` sebelum pesannya tampil.
- **Proses yang mati, ditemukan dari suite penuh yang gagal sekali lalu lulus berkali-kali.** Sesudah
  seluruh pekerjaan selesai, `pytest` **sekali** berakhir dengan proses yang dihentikan paksa
  ("Current thread's C stack trace", 58 uji baru berjalan) dan pada jalan berikutnya lulus penuh.
  Sebabnya satu-satunya yang cocok: **`QThread` dimusnahkan dalam keadaan hidup** ketika jendela
  ditutup sementara pekerja latar masih berjalan — di Qt itu menghentikan prosesnya, tanpa pesan yang
  bisa dibaca pemakai, dan tepat ketika sebuah saringan sedang menulis skor ke basis data. Ditutup
  dengan `Jendela.closeEvent` + `tunggu_pekerja`: penutupan **menunggu** pekerja selesai (kejadian
  tetap diolah selama menunggu supaya jendelanya tidak membeku), batasnya 60 detik, dan bila batasnya
  lewat pengguna **ditanya** — bukan dipaksa tutup. Dua uji baru menjaganya. Suite penuh dijalankan
  **dua kali berturut-turut** sesudahnya: **793 lulus** dua-duanya.
- **Verifikasi.** `.\.venv\Scripts\python -m pytest` → **793 lulus** (768 + 25 uji baru:
  `tests/test_ui_tabel.py` 7 uji tanpa Qt, `tests/test_ui_jendela.py` 18 uji di platform
  `offscreen`). Dua uji baru — "hasil lama dibuang saat pemuatan gagal" dan "penutupan menunggu
  pekerja latar" — **terbukti gagal pada perilaku lama** (masing-masing lewat plugin pytest sekali
  pakai yang mengembalikan `Panel._gagal` dan `Jendela.closeEvent` ke versi lamanya: **1 gagal**
  dua-duanya). Bukti atas data nyata: `.uji-data/uji-jendela/jendela/`
  (`bukti-1` kerangka lima layar · `bukti-2` dasbor · `bukti-3` saring · `bukti-4` detail TLKM ·
  `bukti-5` risiko identik dengan baris perintah · `bukti-6` jurnal · `bukti-7` kegagalan tampil
  di layar · `bukti-8` ringkasan) beserta **lima tangkapan layar** `tangkapan-1..5-*.png`; seluruh
  jalannya diulang-ulang atas **salinan** `.uji-data/uji-jurnal` sehingga folder data lain tidak
  tersentuh.
- **Batas bukti yang disebut apa adanya.** Jendela dijalankan di platform `offscreen` (tanpa
  layar) dan dirender jadi gambar; **tampilan sesungguhnya di layar pengguna belum pernah
  dilihat** — tata letaknya terbukti masuk akal dari tangkapan itu, tetapi mengklaim lebih dari
  itu berarti mengklaim yang tidak diukur.
- **Yang belum dikerjakan, sengaja:** semua tindakan yang **menulis** dari jendela (catat
  transaksi, simpan rencana, catat jurnal, impor, cadangan/F12) — jendela tahap ini **membaca**;
  menunya menyusul bersama pekerjaan tulis itu. Jendela juga belum diekspor ke `.exe` (Tahap 5).
  **DIPERBARUI 19 Okt 2026:** tindakan tulis jendela sudah lengkap (K59 c, aksi #19b–#19d), dan
  `.exe` sudah dibangun sebagai bundel onedir (**T81**, sesi 35); yang tersisa hanya ikon dan uji
  klik-ganda di mesin tanpa Python.
- **Koreksi di luar lingkup aksi #10 yang dikerjakan sesi ini:** baris keputusan **T62** yang
  hilang dari `docs/arsitektur.md` di working tree sesi 8 (digantikan T63/T64 tanpa sengaja)
  **dipulihkan apa adanya dari `HEAD`**, dan pekerjaan aksi #18 yang belum ter-commit **di-commit**
  lebih dulu (`35aa369`). T62 masih dirujuk T58, `docs/keputusan.md`, dan `tests/test_impor_berkas.py`,
  jadi kehilangannya adalah kehilangan jejak keputusan, bukan sekadar nomor yang kosong.

### Pencatatan keputusan jendela & data: K55–K58 (17 Okt 2026, sesi 9 lanjutan — **tanpa perubahan kode**)

- **Pengguna menjawab "sesuai rekomendasi"** atas empat hal yang diajukan sesudah aksi #10 tahap 1
  selesai, dan meminta **tidak ada pekerjaan teknis** pada sesi pencatatan ini. Keempatnya dikunci
  di bagian 1: **K55** (jendela tahap ini **membaca** saja; tindakan tulis menjadi tahap tersendiri —
  aksi #19 — dengan empat syarat: fungsi inti yang sama, konfirmasi, perilaku saat kunci tulis
  dipegang proses lain, dan pesan galat yang sama dengan baris perintah), **K56** (kalkulator risiko
  di jendela tetap menuntut kandidat berstatus watchlist/rencana, PRD 9.6), **K57** (rasio bank
  diisi manusia, dan aplikasi menyiapkan kerangka daftar kode banknya), **K58** (dasbor menampilkan
  IHSG + rezim + breadth; kalimat tetap yang salah dibuang). Keputusan teknisnya **T66** (rezim &
  breadth tetap satu tempat untuk dua layar) dan **T67** (bentuk kerangka `rasio-bank.csv`) di
  `docs/arsitektur.md`.
- **Yang tidak dikerjakan, sesuai permintaan:** tidak ada perubahan kode, tidak ada impor, dan tidak
  ada baris basis data yang ditulis. Verifikasi keadaan sesi ini: `.\.venv\Scripts\python -m pytest`
  → **793 lulus** — jumlahnya **tidak berubah** dari akhir aksi #10 tahap 1, dan itu memang yang
  diharapkan karena tidak ada kode yang disentuh.
- **Cacat yang mendasari K58 ditemukan saat menyiapkan pertanyaannya, bukan dari pekerjaan sesi ini:**
  `dasbor.susun` **selalu** menambahkan catatan *"rezim pasar & breadth belum dapat dinilai: keduanya
  butuh `harga_indeks` (IHSG/LQ45) yang belum diisi sumbernya"*, padahal terukur 17 Okt 2026:
  `harga_indeks` memuat **IHSG 1.199 bar dan LQ45 1.199 bar** (2021-10-11 → 2026-10-09) — pengambil
  indeksnya memang sudah ada sejak `--refresh` (`mejasaham/pengambil.py` baris 60–62) — dan `--saring`
  atas snapshot yang sama mencetak **`breadth 39,1% · rezim RISK-OFF`**. Jadi dua keluaran aplikasi
  bertentangan pada snapshot yang sama, dan yang salah justru menyembunyikan baris yang PRD 11.1
  minta ada di dasbor. **Tiga klaim dokumen yang salah karenanya sudah dikoreksi** di
  `docs/lanjutan.md`: baris dasbor pada tabel keadaan, daftar sisa pekerjaan yang masih mencantumkan
  `harga_indeks` untuk rezim & breadth (datanya **sudah ada**; yang belum ada adalah **dasbor yang
  memakainya**), dan bagian 9.
- **Pekerjaan berikutnya, urutannya di `docs/lanjutan.md` bagian 4:** aksi **#20** (dasbor
  menampilkan rezim/breadth; K58, T66) dan **#21** (kerangka `rasio-bank.csv`; K57, T67) sebagai
  pekerjaan kecil yang tidak menunggu apa pun, lalu aksi **#19** (tindakan tulis dari jendela; K55)
  yang lebih besar dan menuntut penetapan perilaku kunci tulis **lebih dulu**, bukan sambil menulis.

### Aksi #20 — dasbor menampilkan IHSG, rezim, dan breadth (17 Okt 2026, sesi 10)

- **K58/T66 dijalankan**, tanpa keputusan baru: `mejasaham/dasbor.py` menyusun konteks pasar lewat
  `_konteks_pasar` (potret → `metrik.metrik_semua` → `saring.semesta_likuid` → `metrik.breadth` →
  `metrik.rezim_pasar`) — jalur yang **sama** dengan `pengatur.jalankan_saring` — dan menyimpannya di
  `Dasbor` (`pasar`, `breadth`, `rezim`, `preset_pasar`). Kalimat tetap *"rezim pasar & breadth belum
  dapat dinilai … `harga_indeks` … belum diisi sumbernya"* **dibuang**. `metrik.INDEKS_ACUAN` baru
  (satu tempat untuk "IHSG") dan `tampilan.bertanda` baru (`+62 (+1,03%)`) menyertainya.
- **Terukur atas data nyata** (salinan `.uji-data/uji-jurnal` → `.uji-data/uji-dasbor`, snapshot 12):
  `--saring` dan `--dasbor` sama-sama berbunyi **`88 dari 225 emiten likuid · breadth 39,1% · rezim
  RISK-OFF`** dengan IHSG `6.093 (+62 / +1,03%)`; pada kode lama dasbor berbunyi 2,8 dtk **tanpa**
  baris `Pasar` dan **dengan** kalimat tetap itu. Buktinya `.uji-data/uji-dasbor/bukti/`
  (`bukti-0` kode lama · `bukti-1` `--saring` · `bukti-2` `--dasbor` · `bukti-3` pytest ·
  `bukti-4` contoh proses yang mati · `bukti-keadaan.txt`), pembuatnya
  `.uji-data/riset-idx/dasbor/bukti-dasbor.py`.
- **Keputusan teknis yang ditambahkan pelaksanaannya:** **T68** (GC siklik dimatikan selama tugas
  pekerja latar **dan** selama jalur tunggu penutupan). Dasbor yang baru menghitung potret + seluruh
  metrik di dalam utas pekerja menambah alokasi cukup banyak untuk menyingkap **cacat PySide6 6.12.0 +
  CPython 3.14.7**: `tests/test_ui_jendela.py` berhenti dengan *access violation* / `Fatal Python
  error: Aborted` di tengah `tunggu_pekerja()`, tanpa traceback Python. Angka yang memisahkan sebab
  dari kebetulan: kode lama **0 gagal/18 jalan**, kode baru **7/18**, dengan blok konteks pasar
  dimatikan **0/12**, dengan GC dimatikan **0/12**, dengan pohon Qt uji ditahan hidup **12/12**.
  **Versi pertama penangkalnya bocor** (hanya `Pekerja.run`): karena `gc.enable()` adalah keadaan
  **proses**, satu pekerja yang selesai menyalakan GC kembali tepat ketika jalur tunggu masih
  mengandalkannya mati — suite penuh masih gagal **1 dari 8**. Versi final memakai satu penahan
  berpenghitung, `mejasaham/ui/pekerja.py:tahan_gc_siklik()`, yang dipakai kedua jalur: **0 gagal/10**
  jalan uji jendela+dasbor dan **0 gagal/8** jalan suite penuh.
- **Biaya yang harus disebut apa adanya** (konsekuensi sah dari K58/T66, bukan cacat): karena
  jalurnya sama dengan saringan, `--dasbor` ikut membayar potret + seluruh metrik + breadth. Pada
  basis data 999.421 bar: `--dasbor` **2,8 dtk → 33–61 dtk** (bergantung beban mesin), setara
  `--saring` (32–55 dtk) pada folder yang sama. Rincian per bagian ada di `bukti-keadaan.txt`
  (potret 16–25 dtk · metrik 14–25 dtk · breadth 2,5–4,7 dtk). **Angka `--saring` tidak berubah**:
  yang bertambah hanya pembacaan di dasbor. Alternatif "menyimpan hasilnya di snapshot lalu
  membacanya" **tidak** diambil karena itu "menyalin hasilnya" (T66) dan angka pasar yang basi akan
  terbaca sebagai keadaan hari ini.
- **Verifikasi:** `.\.venv\Scripts\python -m pytest` → **805 lulus** (793 + 6 uji dasbor baru + 4 uji
  penahan GC + 2 uji penjaga glif), dijalankan **delapan kali berturut-turut, delapan lulus** sesudah penangkal final —
  sebelum penangkal suite penuh berhenti di uji jendela pada percobaan pertama. Uji barunya termasuk
  satu yang menuntut **dasbor dan saringan tidak boleh berbeda** pada snapshot yang sama, satu yang
  menuntut **NETRAL beserta sebabnya** (tanpa IHSG, dan dengan 199 bar IHSG), satu yang menuntut
  breadth mengikuti **preset yang menghasilkan skor tersimpan**, serta tiga uji penahan GC (mati
  selama tugas, mati selama jalur tunggu diukur dari utas uji biasa, dan dua pemakai bersarang tidak
  saling menyalakan).
- **Yang belum:** aksi **#21** (kerangka `rasio-bank.csv`) dan **#19** (tindakan tulis dari jendela)
  tetap seperti urutannya; cacat PySide6/CPython di atas **ditangkal, belum hilang** — sesi berikutnya
  yang menemukan jalannya sendiri boleh mengangkatnya sebagai temuan (mis. laporan upstream atau
  pin versi), dan T68 harus dibaca sebagai penangkal, bukan perbaikan.
- **Temuan ketiga, di luar lingkup aksi #20 — SUDAH DIPERBAIKI di sesi yang sama (17 Okt 2026):**
  `mejasaham/metrik.py` memuat **33 glif ber-mojibake di 24 baris** (terukur dari byte: `≤` 12×,
  `÷` 10×, `→` 5×, `−` 3×, `×` 2×, `√` 1×), dan sekitar **sepuluh** di antaranya adalah **teks yang
  tampil ke pengguna** (`alasan`/`asal` metrik seperti `ekuitas â‰¤ 0 sehingga DER tidak bermakna`).
  Klaim `docs/lanjutan.md` bagian 6 bahwa glif ini "Diperbaiki 9 Okt 2026: `mejasaham/metrik.py`
  (10 tempat)" karena itu **belum menyeluruh** dan sudah dikoreksi di sana. Seluruh 33-nya diganti
  glif yang benar (sisa **0** bila diukur dari byte), penjaganya `tests/test_glif_teks.py` —
  memindai byte, bukan tampilan (terminal PowerShell bisa menampakkan glif yang seolah benar), dan
  **terbukti gagal** atas berkas lama (12 `≤`, 10 `÷`, 5 `→`, 3 `−`, 2 `×`). Baris yang ditambahkan
  aksi #20 sendiri bersih (diperiksa per byte). `docs/` sengaja tidak dipindai penjaganya: di sana
  urutan itu dipakai sebagai **kutipan gejala**.

### Aksi #21 — kerangka `rasio-bank.csv` dari daftar emiten bank (17 Okt 2026, sesi 10, lanjutan)

- **K57/T67 dijalankan**, tanpa keputusan baru: perintah **`--kerangka-rasio-bank`**
  (`mejasaham/cli.py`) menulis `rasio-bank.csv` di folder konfigurasi lewat
  `jenis.tulis_kerangka_rasio_bank()` + `jenis.kode_bank()`. Satu baris per kode
  ber-`jenis='bank_keuangan'` pada revisi terkini, **seluruh sel selain `kode` kosong**, bentuk
  kolomnya **dipinjam** dari `berkas.SPESIFIKASI["rasio_bank"]` (bukan bentuk kedua), dan berkasnya
  **tidak** diimpor oleh perintah itu.
- **Terukur atas `.uji-data/uji-jenis`** (salinan yang `jenis`-nya sudah terisi K21): **49 baris**
  (AGRO … SUPA), **sel terisi selain `kode`: 0**; `--impor` atas kerangka yang belum diisi **keluar
  1** dengan pesan **per baris** (`rasio-bank.csv baris 36: kolom `periode` wajib diisi`, 49 baris
  dilaporkan) sementara `rasio_bank` tetap **0 baris**; `--saring` tetap jalan (keluar 0). Bukti
  `.uji-data/uji-kerangka-rasio-bank/bukti/` (`bukti-1` … `bukti-5` + `bukti-keadaan.txt`),
  pembuatnya `.uji-data/riset-idx/kerangka-rasio-bank/bukti-kerangka.py`.
- **Dua batas yang ditetapkan pelaksanaannya** (keduanya dicatat di T67): berkas tujuan yang **sudah
  berisi ditolak** — kecuali masih template bawaan AC-12 — sebab berkas itu diisi manusia dari
  publikasi resmi; dan **tanpa `jenis` terisi** perintahnya melaporkan jalan keluarnya
  (`--ambil-jenis` + `--impor`), bukan menulis kerangka kosong.
- **Cacat yang ditemukan uji barunya sendiri, dan ditutup di sesi yang sama:** perintahnya sempat
  dijalankan **dua kali** dalam satu jalan karena dispatch ganda di `main()` — jalan pertama
  menulis, jalan kedua menolak karena berkasnya sudah ada (keluar 1 walau berkasnya terbit).
- **Verifikasi:** `.\.venv\Scripts\python -m pytest` → **810 lulus** (+5 uji di
  `tests/test_jenis_emiten.py`: kerangka berisi kode bank & seluruh sel lain kosong, ditolak berisik
  tanpa `jenis`, tidak menimpa berkas yang sudah berisi, template bawaan boleh ditimpa, dan
  `--impor` kerangka kosong gagal berisik dengan `rasio_bank` tetap 0 baris).
- **Cacat PySide6/CPython yang tersingkap aksi #20 kini juga DIRISET** (permintaan pengguna pada sesi
  yang sama): `docs/riset-pyside6-gc-2026-10.md` memuat gejalanya, tabel angka pemisah sebab, fakta
  bahwa kombinasi PySide6 6.12.0 + CPython 3.14.7 **didukung** paketnya (`Requires-Python
  >=3.10,<3.16`), dan **dua repro sintetis yang tidak memicunya** (jadi belum terisolasi di luar
  pytest) beserta langkah berikutnya: laporan upstream → uji Python 3.13 → uji PySide6 lain. Yang
  **belum** diputuskan pengguna: apakah menempuh salah satu langkah itu, atau menerima penangkal T68
  apa adanya.
- **Usulan baru U26** (`docs/keputusan.md` bagian 2): konteks pasar dihitung ulang tiap kali
  (**diterima pengguna apa adanya**, harga 33–61 dtk) **atau** disimpan saat `--saring` lalu dibaca
  kembali (belum diputuskan — angka tersimpan bisa basi, dan itu kelas kesalahan yang dicegah K58).

### Sesi pencatatan: tiga keputusan menunggu jawaban (17 Okt 2026, sesi 10b — **tanpa perubahan kode**)

- Pengguna meminta **hanya pencatatan** ("jangan ngoding, catet aja dulu biar lanjut di session
  berikutnya") atas pertanyaan "butuh keputusan apa dari saya?". Tiga pertanyaan dicatat di
  **bagian 3.7**, masing-masing dengan konteks terukur, pilihan, **usulan**, dan apa yang terhalang:
  **P31** (perilaku jendela saat kunci tulis basis data dipegang proses lain — lima butir, semuanya
  berusulan; **memblokir aksi #19**, sebab K55 menetapkan bahwa perilaku itu ditetapkan lebih dulu,
  bukan dikarang sambil menulis), **P32** (langkah cacat PySide6 6.12.0 + CPython 3.14.7: lapor
  upstream / uji Python 3.13 / uji PySide6 lain / terima T68 apa adanya — tidak memblokir),
  **P33** (biaya konteks pasar di dasbor: teruskan menghitung ulang, atau kejar **U26** beserta
  aturan kapan angka tersimpan tidak boleh ditampilkan — tidak memblokir).
- **Antrean kerja diperbarui** di `docs/lanjutan.md` bagian 4: baris **#19** ditandai *menunggu P31*,
  dan dua baris baru ditambahkan sebagai pekerjaan yang **dipicu keputusan** — **#22** (langkah cacat
  PySide6, dipicu P32) dan **#23** (simpan konteks pasar saat `--saring`, dipicu P33, hanya bila
  U26 dikejar). Bagian 9 `docs/lanjutan.md` kini hanya **menunjuk** bagian 3.7, bukan menyalinnya
  (satu fakta satu tempat).
- **Yang tetap bukan keputusan, melainkan pekerjaan manusia:** mengisi `rasio-bank.csv` dari
  publikasi resmi bank/OJK — kerangkanya sudah dibuat aksi #21 (49 kode bank) dan selama kosong
  keempat kriteria bank tetap "tidak dihitung" serta bank tidak dapat masuk peringkat (K57).
- **Verifikasi keadaan:** tidak ada berkas kode yang disentuh pada sesi pencatatan ini; yang berubah
  hanya `docs/keputusan.md` dan `docs/lanjutan.md`. Status uji terakhir (sesi 10a) tetap:
  `.\.venv\Scripts\python -m pytest` → **810 lulus**.

### Jawaban atas P31–P33: K59–K61 (17 Okt 2026, sesi 10c — **tanpa perubahan kode**)

- Pengguna menjawab **"sesuai rekomendasimu, catet dulu, jangan ngoding"** atas tiga pertanyaan yang
  dicatat sesi 10b, lalu meminta pekerjaannya dilanjutkan di sesi berikutnya. Ketiganya dikunci di
  bagian 1: **K59** (perilaku jendela saat kunci tulis dipegang proses lain + cakupan tindakan tulis
  tahap pertama — menunggu `busy_timeout` 5 detik lalu berhenti dengan pesan yang **wajib** memuat
  "jendela belum menulis apa pun"; bertahap tiga pencatat transaksi → impor → cadangan; konfirmasi
  untuk semua tindakan; F12 cadangan+daftar dulu, pulihkan tersendiri), **K60** (cacat PySide6 6.12.0
  + CPython 3.14.7: **laporan upstream lebih dulu** — drafnya sudah siap dan dikirim pengguna — lalu
  **uji Python 3.13**, dan pemasangan interpreternya dilaporkan lebih dulu sebagai keputusan
  dependensi), **K61** (konteks pasar **tetap dihitung ulang**; **U26** tidak ditutup, dan aturan
  kebasiannya disepakati lebih dulu: angka tersimpan hanya boleh ditampilkan bila `id_snapshot` dan
  versi presetnya masih sama).
- **Bentuk teknis kunci tulis** dicatat sebagai **T69** (`docs/arsitektur.md`): satu jalur tulis inti
  (fungsi yang sama dengan baris perintah, tetap lewat `db.tulis`), dijalankan sebagai `Pekerja`
  (konfirmasi & validasi di utas tampilan **sebelum** pekerja mulai), galat "database is locked"
  dipetakan ke `GalatJendela` dengan pesan yang sama + kalimat "belum menulis apa pun", cakupan
  bertahap, dan sesudah berhasil layar dimuat ulang (bukan widget disunting tangan).
- **Antrean kerja diperbarui** di `docs/lanjutan.md`: baris **#19** kini berbunyi **"SIAP
  DIKERJAKAN"** (prasyaratnya sudah lunas), **#22** berjalan menurut K60, **#23** (U26) **belum
  dipicu** dan menunggu permintaan pengguna. Bagian 9 `docs/lanjutan.md` ditulis ulang: tidak ada
  pertanyaan yang menunggu, dan pekerjaan berikutnya adalah **aksi #19**.
- **Verifikasi keadaan:** yang berubah hanya `docs/keputusan.md`, `docs/lanjutan.md`, dan
  `docs/arsitektur.md`; **tidak ada berkas kode yang disentuh**. Status uji terakhir (sesi 10a)
  tetap: `.\.venv\Scripts\python -m pytest` → **810 lulus**.
- **Penegasan pengguna (17 Okt 2026, sesi 10c):** pekerjaannya **dilanjutkan di SESI BARU**, bukan
  dengan melanjutkan sesi ini (*"mau di lanjutkan di sesi baru, bukan sebelumnya, salah saya"*).
  Karena itu `docs/lanjutan.md` diberi blok **"TITIK MULAI UNTUK SESI BARU"** di bagian atas: tiga
  langkah pertama (pytest harus 810 lulus → baca K55/K59/K60/K61 + T65/T69 → mulai aksi #19 dari tiga
  pencatat transaksi), apa yang menunggu pengguna (kirim laporan upstream, isi `rasio-bank.csv`, lalu
  uji Python 3.13), dan keadaan git-nya. Sesi 10c **tidak menyentuh kode**, jadi tidak ada pekerjaan
  setengah jalan yang perlu diselamatkan.

### Pelaksanaan aksi #19 tahap 1: tiga pencatat transaksi dari jendela (17 Okt 2026, sesi 11)

- **Yang dikerjakan (K55 + K59 → T69/T70).** Jendela kini **menulis**, mulai dari yang terkecil
  menurut K59 (c): **catat transaksi** (layar 11.3, `posisi.catat_transaksi`), **simpan rencana**
  (11.4, `risiko.simpan_dari_kandidat`), dan **catat jurnal** (11.5, `jurnal.catat`). Yang mengikat
  K59 dijalankan persis: `busy_timeout` **ditunggu** lalu berhenti dengan pesan yang memuat
  **"Jendela belum menulis apa pun"**; **konfirmasi untuk semua** tindakan, berisi angka yang akan
  ditulis; dan sesudah berhasil layarnya dimuat ulang dari baris tersimpan.
- **Berkas baru `mejasaham/ui/tulis.py` (bebas Qt).** Tiap tindakan menjadi `PermintaanTulis(judul,
  ringkasan, jalankan)`; ringkasannya disusun dari objek yang **sama** yang diserahkan ke fungsi
  intinya. Yang diuji tanpa layar: isi ringkasan, penolakan isian yang tidak lengkap, dan baris apa
  yang ditulis.
- **Dua aturan dipindahkan ke inti supaya dua mode tidak bisa bercabang** (pola yang sama dengan
  T65): (a) aturan status rencana + perpindahan `watchlist` → `rencana` kini di
  **`risiko.simpan_dari_kandidat`** — `cli.py` memakainya juga, dan kegagalan perpindahan statusnya
  dilaporkan sebagai `peringatan` **tanpa** membatalkan rencana yang sudah tersimpan; (b) kunci tulis
  yang gagal kini menjadi **`db.BasisDataTerkunci`** berisi **`db.KALIMAT_TERKUNCI`** di `db.tulis()`
  (satu kalimat untuk dua mode), dan jendela menambahkan kalimat "belum menulis apa pun" di atasnya.
- **Perubahan perilaku yang perlu diketahui:** kunci tulis yang gagal **tidak lagi** menjadi traceback
  `sqlite3.OperationalError` di baris perintah — `--catat-transaksi`, `--hitung-risiko`,
  `--simpan-rencana`, `--jurnal-catat`, `--saring`, `--kandidat-*`, dan `--buat-cadangan` kini
  mencetak kalimat itu dan keluar **1**. Uji lama yang menuntut `sqlite3.OperationalError` di
  `tests/test_db.py` karena itu **diperbarui** — dan sekarang memeriksa bunyi kalimatnya beserta
  janji "tidak ada baris yang tertulis".
- **Letak tindakannya** (dipilih sesi ini, dicatat supaya tidak ditanyakan lagi): transaksi di layar
  **11.3** (per kode, di sebelah posisi kode itu), rencana di **11.4** (PRD 11.4 memang memuat tombol
  *Simpan rencana*), jurnal di **11.5** (PRD 11.5 memuat *Tulis pelajaran*/*Tandai selesai*).
  Jendela tetap **lima layar** — tidak ada tab baru.
- **Yang belum (jadi aksi #19b dan #19c di `docs/lanjutan.md`):** **impor** dari jendela, lalu
  **cadangan + daftar (F12)**; **`--pulihkan` tidak** masuk keduanya karena ia menimpa basis data
  (K59 e). Batas itu disebut di dalam jendela (`_tentang` dan catatan tiap formulir), bukan
  disembunyikan.
- **Verifikasi: `.\.venv\Scripts\python -m pytest` → 833 lulus** (810 + 23 uji baru: 12
  `tests/test_ui_tulis.py`, 8 di `tests/test_ui_jendela.py`, 3 di `tests/test_risiko.py`); uji jendela
  + lapisan tulis dijalankan **8×** berturut-turut tanpa satu pun proses yang mati (cacat PySide6/T68
  tetap tertangkal). **Bukti atas data nyata:**
  `.uji-data/riset-idx/tulis-jendela/bukti-tulis-jendela.py` menjalankan ketiga tindakan **dua kali**
  atas dua salinan `.uji-data/uji-jurnal` — sekali lewat **panel jendela sungguhan** (platform
  `offscreen`), sekali lewat baris perintah — lalu membandingkan `v_transaksi_terkini`,
  `v_posisi_terkini`, `v_rencana_terkini`, `v_kandidat_terkini`, dan `v_jurnal_terkini` kolom demi
  kolom: **seluruhnya SAMA**; kunci tulis yang dipegang proses lain **ditunggu 5,56 detik** lalu
  berhenti dengan pesan itu dan **0 baris tertulis**. Buktinya
  `.uji-data/uji-tulis-jendela/bukti/bukti-tulis-jendela.txt`.
- **Uji barunya bergigi:** perbandingan barisnya **terbukti gagal** ketika biaya di jalur jendela
  dibedakan satu rupiah (mutasi sementara) — jadi "SAMA" pada bukti atas data nyata bukan kebetulan
  uji yang tidak memeriksa apa pun.
- **Keputusan teknisnya T70** (`docs/arsitektur.md`); jebakan baru yang ditemukan dicatat di
  `docs/lanjutan.md` bagian 6 (mutasi uji yang tertinggal karena `git checkout` tidak memulihkan
  berkas *untracked*; slot Qt yang tidak boleh diberi parameter keyword-only).

### Pencatatan tiga pertanyaan sesudah aksi #19 tahap 1 (17 Okt 2026, sesi 11b — **tanpa perubahan kode**)

- Pengguna meminta pekerjaan **dihentikan dulu** ("jangan ngoding dulu") dan menanyakan **apa yang
  perlu diputuskan**, untuk dilanjutkan di **sesi baru**. Karena itu sesi ini **hanya mencatat**:
  yang berubah hanyalah `docs/keputusan.md` dan `docs/lanjutan.md`.
- **Tiga pertanyaan dicatat di bagian 3.8: P34–P36.** (P34) sesudah #19b/#19c, tindakan tulis mana
  yang masuk jendela lebih dulu — usulannya tetap mengikuti K59 c lalu **#19d `ubah-stop` + keputusan
  right issue**; (P35) **PRD 9.7: pilihan "pakai ukuran yang patuh" belum ada di jendela** — usulannya
  menambahkannya di layar 11.4 memakai `risiko.pakai_ukuran` yang sudah ada, dikerjakan bersama #19b;
  (P36) **seberapa lengkap jendela** dibanding baris perintah — usulannya jendela = jalur harian dan
  yang wajib masuk adalah **pilihan rencana & posisi dari daftar** (bukan mengetik `#1`), sedangkan
  `id posisi` eksplisit, pajak/biaya yang dicatat pengguna, broker, ekspor, dan `--pulihkan` tetap di
  baris perintah.
- **Yang tidak menunggu jawaban itu:** **#19b (impor dari jendela)** dan **#19c (cadangan + daftar,
  F12)** — urutannya dikunci K59 c, bentuk teknisnya T69/T70, dan tidak satu pun pertanyaan di atas
  mengubahnya. Jadi urutan kerja sesi berikutnya tetap sama walau P34–P36 belum dijawab.
- **Keadaan git yang perlu diketahui sesi berikutnya:** pekerjaan **sesi 11 (kode + 23 uji) belum
  di-commit pada saat pencatatan ini** — `git status --short` waktu itu menampilkan
  `mejasaham/{cli,db,risiko}.py`, `mejasaham/ui/{jendela,tulis}.py`,
  `tests/{test_db,test_risiko,test_ui_jendela,test_ui_tulis}.py`, dan ketiga berkas `docs/`.
  Pengguna belum memutuskan commit-nya saat itu; **sudah di-commit di sesi 11c** (`874e095` kode +
  uji, `82f3064` catatan) — lihat catatan di bawah.
- **Status uji terakhir (kode sesi 11, tidak berubah oleh sesi pencatatan ini):**
  `.\.venv\Scripts\python -m pytest` → **833 lulus** (62,29 dtk).

### Jawaban atas P34–P36: K62–K64 (17 Okt 2026, sesi 11c — **tanpa perubahan kode**)

- Pengguna menjawab **"sesuai rekomendasimu, catet dulu, nanti di lanjutkan di session baru"** atas
  ketiga pertanyaan yang dicatat sesi 11b, lalu meminta pekerjaannya dilanjutkan di sesi berikutnya.
  Karena itu sesi ini **hanya mencatat**: yang berubah hanyalah `docs/keputusan.md`,
  `docs/arsitektur.md`, dan `docs/lanjutan.md`.
- **Keputusannya dikunci di bagian 1:** **K62** — urutan tindakan tulis lanjutan mengikuti K59 c apa
  adanya (#19b impor → #19c cadangan + daftar), lalu **#19d = `ubah-stop` + keputusan right issue**,
  dan `ubah-stop` **tidak** diselipkan sebelum impor; **K63** — layar 11.4 memperoleh pilihan **"Pakai
  ukuran patuh"** (memakai `risiko.pakai_ukuran`), dihitung **sebelum** konfirmasi supaya dialognya
  menyebut angka yang benar-benar ditulis, dikerjakan bersama #19b; **K64** — jendela = **jalur
  harian**, baris perintah = jalur lengkap, dengan **pilihan rencana & posisi dari daftar** sebagai
  yang **wajib** masuk jendela (bukan mengetik `#1`), sedangkan `--id-posisi` eksplisit, pajak/biaya
  pengguna, broker, ekspor, entri kandidat, `--ekuitas-harian`, dan `--pulihkan` tetap di baris
  perintah.
- **Bentuk teknisnya dicatat sebagai T71** (`docs/arsitektur.md`) **sebelum** dikerjakan — pola yang
  sama dengan T69: pilihan dari daftar (dan penolakan memilih yang pertama bila daftarnya tidak
  tunggal, kelanjutan K56), urutan ukuran patuh → konfirmasi, jalur `ubah-stop`/right issue yang
  memakai fungsi inti yang sudah ada (`tebus` tetap menuntut transaksi tercatat, T51), dan daftar
  batas yang tetap di baris perintah.
- **Antrean kerja tidak berubah urutannya** (K62 hanya menambah satu baris di ujungnya): di
  `docs/lanjutan.md` bagian 4, **#19b** kini memuat K63, **#19c** tetap seperti semula, dan **#19d**
  berhenti menunggu P34. Bagian 9 kembali berbunyi **"tidak ada pertanyaan yang menunggu"**
  (P34–P36 dibiarkan di bagian 3.8 sebagai riwayat beserta jawabannya).
- **Verifikasi keadaan:** **tidak ada berkas kode yang disentuh** pada sesi pencatatan ini (diperiksa
  dari sidik SHA-256 enam berkas kode sesi 11 — semuanya identik sebelum dan sesudah pencatatan);
  status uji terakhir tetap **833 lulus**, dijalankan ulang sesudah pencatatan (**25,16 dtk**).
- **Commit (atas permintaan pengguna, sesudah pencatatan ini):** `874e095` — aksi #19 tahap 1 (kode +
  23 uji, `mejasaham/ui/tulis.py` baru) — lalu `82f3064` — catatan tahap ini (T70/T71, K62–K64, dan
  seluruh pembaruan dokumen). Sesudahnya **working tree bersih**; itu yang diperiksa
  `docs/lanjutan.md` blok TITIK MULAI.

### Pelaksanaan aksi #19b: impor dari jendela + "Pakai ukuran patuh" (17 Okt 2026, sesi 12)

- **Yang dikerjakan, mengikuti K59 c + K63 + K64 apa adanya.** (1) **Impor dari jendela** lewat menu
  **Berkas → Impor berkas…**, dua tahap: folder **dibaca** di utas pekerja, ringkasan konfirmasi
  memuat **jumlah baris per tabel** (K59 d), lalu penulisan di utas pekerja dengan **objek hasil
  bacaan yang sama** (`pengatur.jalankan_impor(sudah_dibaca=…)`) — jadi yang tertulis tidak bisa
  berbeda dari yang disetujui. (2) **"Pakai ukuran patuh"** di layar 11.4 (K63): centangnya dibaca
  **sebelum** hitungan dimulai, hasil patuh itulah yang tampil → dikonfirmasi → disimpan.
  (3) **Pilihan rencana & posisi dari daftar** (K64/T71 a) di 11.3 dan revisi rencana di 11.4.
- **Dua aturan dipindahkan ke inti supaya dua mode tidak bisa bercabang** (pola T70 b): susunan
  `pakai_ukuran` menjadi **`risiko.pakai_ukuran_patuh(hasil, masukan)`** (dipakai `cli.py` **dan**
  layar 11.4 — `lot` dan batas totalnya tidak lagi disusun di dua tempat), dan jalur impor menerima
  `sudah_dibaca` sehingga jendela memakai pembaca berkas yang **sama** dengan `--impor`.
- **Satu cacat perilaku ditemukan dari bukti atas data nyata dan ditutup:** impor yang kuncinya
  dipegang proses lain berhenti setelah **11,16 detik**, bukan ~5 — sebab kegagalan penulisan
  diikuti percobaan **mencatat log**, yang menunggu `busy_timeout` untuk kedua kalinya. Log memang
  tidak bisa ditulis selama kuncinya dipegang proses lain, jadi percobaannya dihapus
  (`pengatur.jalankan_impor`: `BasisDataTerkunci` diteruskan apa adanya). Sesudahnya terukur
  **5,62 detik** dan kalimatnya tetap kalimat bersama + "Jendela belum menulis apa pun".
- **Verifikasi: `.\.venv\Scripts\python -m pytest` → 849 lulus** (26,46 dtk; **+16 uji**: 7 di
  `tests/test_ui_tulis.py`, 3 di `tests/test_ui_tabel.py`, 6 di `tests/test_ui_jendela.py`), dan uji
  jendela+tulis **6× berturut-turut 65 lulus tanpa proses yang mati** (cacat GC PySide6/CPython
  bergantung waktu, jadi satu jalan hijau belum cukup — §6 `docs/lanjutan.md`).
- **Bukti atas data nyata** — `.uji-data/uji-impor-jendela/bukti/bukti-impor-jendela.txt`, pembuatnya
  `.uji-data/riset-idx/impor-jendela/bukti-impor-jendela.py`: dua salinan `.uji-data/uji-jurnal`
  diimpor dengan folder yang **sama dan nyata** (`.uji-data/mejasaham/konfigurasi`, 2.450 baris
  notasi + 707 fundamental + 973 emiten + 1.095 kalender) — sekali lewat `--impor`, sekali lewat
  **menu Berkas jendela sungguhan** (platform `offscreen`). Hasilnya: seluruh **13 tabel/view SAMA**
  baris demi baris (termasuk `harga_harian` 999.421 baris), kedua jalur menulis **4.131 baris baru ·
  1.095 sudah ada dan sama**, dan konfirmasinya berbunyi `total: 5.226 baris dari 9 berkas`.
  Berkas yang ditolak pembaca (kolom berlebih berisi, aksi #18) ditolak **dengan kalimat yang
  sama**, keluar 1, **0 baris** tertulis di kedua jalur. Kunci tulis: **5,62 dtk** lalu 0 baris.
  Ukuran patuh: blok hasil di layar **sama** dengan blok `--hitung-risiko … --pakai-ukuran-patuh`,
  dan `v_rencana_terkini` kedua basis data **SAMA** (revisi rencana #1 menjadi r2). Catatan apa
  adanya: pada basis data itu **ukuran patuh = ukuran akhir** (11.200 lbr) karena batas yang
  mengikat adalah bobot 10%, bukan total risiko — jadi yang dibuktikan di situ adalah **jalur dan
  angkanya sama**, sedangkan ukuran yang benar-benar berubah diuji di `tests/test_risiko.py`.
- **Uji barunya terbukti bergigi:** dijalankan atas kode lama (`HEAD`, worktree terpisah) → **17
  gagal / 48 lulus** di ketiga berkas itu (`bukti-uji-pada-kode-lama.txt`), yaitu seluruh uji yang
  baru **atau** menyesuaikan diri dengan bentuk baru.
- **Tata letak barunya dilihat, bukan diduga:** tiga tangkapan layar `offscreen`
  (`tangkapan-1..3-*.png`, pembuatnya `.uji-data/riset-idx/impor-jendela/tangkap-layar-19b.py`) —
  11.3 dengan kotak **Rencana**/**Posisi** dari daftar (bawaannya "tidak memakai", dengan label yang
  menyebut kode pemilik daftarnya: 2 rencana · 2 posisi · terpilih `None`/`None`), 11.4 tanpa
  centang, dan 11.4 dengan **"Pakai ukuran patuh"** dicentang (baris `Ukuran patuh: 11200 lembar
  (112 lot) (sama dengan ukuran akhir)` + catatan "ukuran diambil dari tawaran ukuran yang patuh").
  Tangkapan sesi 9 **tidak** ditimpa. Batas buktinya sama seperti sebelumnya: dijalankan `offscreen`,
  jadi layar sungguhan di monitor Anda **belum pernah dilihat**.
- **Yang belum dari baris ini (tetap seperti K62/K59 c):** **#19c** cadangan + daftar (F12), lalu
  **#19d** `ubah-stop` + keputusan right issue; `--pulihkan` tetap tidak masuk jendela (K59 e).

### Pencatatan sesi 13: ratifikasi + pembagian pekerjaan tiga butir "menunggu pengguna" (17 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna menjawab "sesuai rekomendasi aja"** atas seluruh pertanyaan sesi 12, **dan** menanyakan
  apakah tiga butir yang selama ini menunggu manusia — **laporan upstream PySide6**, **uji Python
  3.13**, **`rasio-bank.csv`** — bisa dikerjakan sesi agen, dengan permintaan tegas: **"catet dulu"**.
  Karena itu sesi ini **tidak menyentuh kode**; yang berubah hanya `docs/keputusan.md` dan
  `docs/lanjutan.md`.
- **Yang dikunci dari ratifikasi itu: K65** — tafsir K64: jendela memilih rencana/posisi **dari daftar
  saja** (tidak ada kotak isian bebas untuk `id_rencana`/`id_posisi`/revisi rencana). Sesi 12 memang
  membangunnya begitu (K64 sudah dikerjakan #19b), dan angka "`--id-posisi` eksplisit" pada K64 dibaca
  sebagai **jalan baris perintah** untuk hal yang sama, bukan kotak yang disalin ke jendela. Kalau
  kelak jendela memang perlu menerima nomor yang diketik bebas, itu **keputusan baru**.
- **Tiga butir "menunggu pengguna" dicatat sebagai usulan yang menunggu jawaban: U27–U29** (bagian 2)
  dengan pertanyaannya di **3.9 (P37–P39)** — apa yang bisa dialihkan, apa yang tetap manusia, dan
  syaratnya. Ringkas usulannya: (a) **laporan upstream tetap Anda** yang mengirim; sesi agen hanya
  merapikan drafnya jadi satu berkas siap-tempel; (b) **uji Python 3.13 bisa dialihkan** ke sesi agen,
  dengan syarat **keputusan dependensi dilaporkan lebih dulu** (versi, sumber unduhan, cara mencabut)
  dan urutannya sesudah (a) — sesuai K60; (c) **`rasio-bank.csv` boleh dikumpulkan sesi agen sampai
  batas kandidat + kutipan resmi**, sedangkan yang masuk basis data tetap menunggu verifikasi Anda
  (K24 dan aturan keras 1 tidak berubah).
- **Tidak ada yang memblokir:** urutan pekerjaan di `docs/lanjutan.md` bagian 4 tidak berubah —
  berikutnya tetap **#19c** (cadangan + daftar, F12), lalu **#19d**.
- **Verifikasi keadaan:** **tidak ada berkas kode yang disentuh pada sesi pencatatan ini.** Buktinya
  bisa diperiksa sendiri tanpa mempercayai catatan ini: waktu tulis berkas kode masih milik sesi 12
  (`Get-ChildItem mejasaham\*.py, mejasaham\ui\*.py, tests\test_ui_*.py | Select LastWriteTime` →
  21:45–21:58), sedangkan `docs/keputusan.md` dan `docs/lanjutan.md` **22:17**. Berkas kode yang
  tampak "berubah" di `git status --short` adalah pekerjaan **sesi 12 (aksi #19b)** yang memang belum
  di-commit. **Status uji tidak berubah:** `pytest` → **849 lulus** (26,41 dtk).

### Jawaban P37–P39 → K66–K68, dan dua pekerjaan yang sudah disiapkan (17 Okt 2026, sesi 14 — **tanpa perubahan kode aplikasi**)

- **Pengguna menjawab ketiganya "sesuai rekomendasi"**: **P37 → K66**, **P38 → K67**, **P39 → K68**
  (bagian 1). Sesi ini **tidak menyentuh satu berkas kode pun** — yang berubah hanya berkas `docs/`
  plus **dua berkas turunan di `.uji-data/`** (bukti lingkup, gitignored).
- **K66 — berkas siap kirim ditulis:** **`docs/laporan-pyside6-siap-kirim.md`**. Isinya teks Inggris
  siap tempel (tanpa kutipan Markdown), **langkah mengirim menurut halaman resmi Qt** — pelacak
  `bugreports.qt.io/browse/PYSIDE`, Project *Qt for Python*, Type *Bug*, Component **PySide**,
  reproducer **wajib berupa lampiran berkas**, dan pemeriksaan rilis terbaru lebih dulu — daftar
  lampiran, serta **batas yang disebut apa adanya**: tidak ada reproducer minimal (dua repro sintetis
  tidak memicunya dalam 30 dan 48 putaran), jadi lampirannya berkas uji yang benar-benar mati.
  Rujukan langkahnya [Qt for Python/Reporting Bugs](https://wiki.qt.io/Qt_for_Python/Reporting_Bugs).
- **K67 — laporan keputusan dependensi ditulis, pemasangannya BELUM dijalankan:**
  `docs/riset-pyside6-gc-2026-10.md` bagian 8. Ringkasnya, diperiksa dengan perintah baca-saja:
  **`uv 0.12.2` sudah ada di mesin** (jadi tidak ada dependensi baru untuk proyek);
  `uv python list` menyediakan **CPython 3.13.14** standalone; roda PySide6 6.12.0 yang akan dipakai
  adalah **`pyside6-6.12.0-cp310-abi3-win_amd64.whl`** — **abi3**, jadi roda yang **sama** berlaku
  untuk 3.13 (tidak ada roda khusus 3.13); lingkungannya **`.tmp/py313`** (`.venv` repo tidak
  disentuh); keluarga PySide6+shiboken6 yang terpasang sekarang **651 MB**, jadi biaya disk kira-kira
  sebesar itu; pencabutannya `uv python uninstall 3.13` + hapus `.tmp\py313`. Alternatif
  (winget/python.org/Store) ditimbang dan ditolak karena meninggalkan jejak sistem yang lebih besar.
  **Belum ada satu byte pun yang diunduh.**
- **K68 — lingkup `rasio-bank.csv` diukur lebih dulu, dan hasilnya mengubah janji:** atas salinan uji
  `.uji-data/uji-jenis` (49 bank ber-`jenis='bank_keuangan'`, snapshot #8), `pengatur.jalankan_saring`
  dijalankan `simpan=False` di **salinan** `.uji-data/uji-lingkup-p39/` (salinan karena saringan
  **selalu** menulis satu baris `log_jalan`, jadi folder bukti aksi #21 tidak boleh ditulisi).
  Hasilnya (bukti: `.uji-data/uji-lingkup-p39/bukti-lingkup-p39.txt`, pembuatnya
  `.uji-data/riset-idx/rasio-bank/lingkup-p39.py`): likuid 235 · lolos 9 · **49 bank ikut disaring ·
  0 bank lolos · 0 bank tertahan *hanya* oleh rasio bank**. Rincian sebabnya (dihitung dari berkas
  buktinya, 49 baris): keempat rasio bank `npl_kotor`/`car`/`bopo`/`nim` **tidak dinilai pada 49 bank**
  (semuanya), sementara **34 bank juga gagal `adtv20`** (likuiditas), **40 gagal `tren_ma200`**,
  **19 gagal `kekuatan_relatif`**, dan metrik fundamental lain juga lubang (`roe_5t` tidak dinilai 34 ·
  gagal 9; `per_relatif_sektor` tidak dinilai 34 · gagal 3; `pbv_relatif_sektor` tidak dinilai 34 ·
  gagal 1). **Jadi mengisi `rasio-bank.csv` saja tidak membuat satu bank pun masuk peringkat** — dan
  itu dikatakan sebelum pekerjaannya dimulai.
- **Verifikasi keadaan:** `pytest` → **849 lulus** (tidak berubah; tidak ada berkas kode yang
  disentuh). Berkas turunan sesi ini: `docs/laporan-pyside6-siap-kirim.md` (baru),
  `docs/riset-pyside6-gc-2026-10.md` bagian 8, `docs/keputusan.md`, `docs/lanjutan.md`.

### Uji Python 3.13 dijalankan (17 Okt 2026, sesi 14b — **keputusan dependensi disetujui; tanpa perubahan kode**)

- **Pengguna menyetujui pemasangan** yang dilaporkan di `docs/riset-pyside6-gc-2026-10.md` bagian 8
  ("pasang di `.tmp/py313` lalu jalankan uji 12×"). Karena itu sesi ini **memasang** lingkungan
  terpisah dan menjalankan ujinya — **tidak ada berkas kode aplikasi yang disentuh**.
- **Yang dipasang (terukur, bukan perkiraan lagi):** CPython **3.13.14** lewat `uv` (unduhan
  interpreter **20,9 MiB**); `.tmp/py313` = **767 MB**; PySide6 **6.12.0** · shiboken6 **6.12.0** ·
  yfinance 1.7.0 · pytest **9.1.1** (versi pytest sama dengan `.venv`, supaya perbandingannya bersih);
  `uv pip check` → *All installed packages are compatible* (36 paket). `.venv` repo, `requirements.txt`,
  `requirements.lock.txt`, dan pin versi Python proyek **tidak disentuh**.
- **Uji dijalankan dua kali lebih banyak dari yang diminta, dan itu yang membuat hasilnya berarti:**
  12 jalan **dengan** penangkal T68 memang 0 kematian — tetapi 0 kematian itu **dijamin penangkalnya**
  dan karena itu tidak membuktikan apa pun tentang versi Python. Maka uji yang sama dijalankan lagi
  **tanpa penangkal** (`tahan_gc_siklik` diganti blok kosong lewat plugin pytest
  `.tmp/plugin_tanpa_tahan.py`), di **dua** versi: 12 jalan di 3.13.14 dan 12 jalan di 3.14.7.
- **Hasilnya: 0 kematian di keempat percobaan** (24 jalan tanpa penangkal), sedangkan pengukuran sesi
  10 mencatat **7 dari 18** jalan mati tanpa penangkal di 3.14.7. Tiga uji yang gagal di baris "tanpa
  penangkal" adalah **penjaga penangkalnya sendiri** — kegagalan itu justru bukti plugin-nya bekerja
  (GC memang tidak dimatikan). Patokan "mati" = tidak ada ringkasan pytest; **pola teks
  `access violation`/`Aborted` tidak dipakai** karena ia cocok juga dengan docstring uji yang mengutip
  gejalanya (terukur: 24 log bertanda "fatal" semuanya palsu).
- **Kesimpulan yang dilaporkan apa adanya: "belum dapat disimpulkan".** Menyebut 3.13 sebagai
  jawabannya hanya karena 0 kematian di 12 jalan akan menyesatkan, sebab pada hari yang sama 3.14 juga
  0 kematian. Cacatnya **bergantung waktu** (39% jalan di sesi 10, 0% di 24 jalan sesi ini), jadi
  **pin versi Python belum sah diputuskan**. Langkah berikutnya menurut K60: **buat cacatnya
  reproduktif lagi** (kandidat: seluruh suite 12× tanpa penangkal) **atau** uji **versi PySide6 lain**
  dengan 3.14.7 — **T68 tetap dipakai** sampai ada jawaban yang lebih baik.
- **Ikut dikoreksi supaya laporan upstream jujur (K66):** angka 7/18 di draf tetap pengukuran yang
  sah, tetapi `docs/laporan-pyside6-siap-kirim.md` kini memuat **"Note on reproducibility"** di teks
  Inggrisnya (dan bagian 3a + daftar centang di berkas itu) — supaya pelacak tidak menerimanya sebagai
  janji "selalu mati 7 dari 18". Tanpa itu, satu putaran triage akan habis untuk meminta pembuktian
  ulang.
- **Verifikasi keadaan:** `pytest` (`.venv`, CPython 3.14.7) → **849 lulus** — tidak berubah, karena
  tidak ada berkas kode yang disentuh. Uji 3.13: `tests/test_ui_jendela.py` **36 lulus** × 12 jalan
  (dengan penangkal) dan **33 lulus / 3 gagal** × 12 jalan (tanpa penangkal, kegagalannya penjaga
  penangkal).

### Pencatatan sesi 15: langkah lanjutan cacat PySide6 → K69 (17 Okt 2026 — **tanpa perubahan kode, tanpa menjalankan apa pun**)

- **Pengguna menjawab "sesuai rekomendasi mu aja, jangan dijalankan, catet aja dulu, mau aku
  lanjutin ke sesi baru"** atas pertanyaan sesi 14b ("langkah berikutnya: reproduksi ulang cacatnya,
  atau langsung #19c?"). Karena itu sesi ini **hanya mencatat**: yang berubah hanya `docs/keputusan.md`,
  `docs/lanjutan.md`, dan `docs/riset-pyside6-gc-2026-10.md`. **Tidak ada perintah uji yang dijalankan
  ulang** dan **tidak ada berkas kode yang disentuh**.
- **Yang dikunci: K69** — urutan langkah lanjutan cacat PySide6: **reproduksi ulang lebih dulu**
  (seluruh suite 12× tanpa penangkal di 3.14.7), **baru** A/B di 3.13 bila kontrolnya gagal; pin versi
  Python hanya sah bila kontrolnya gagal di satu versi dan tidak di versi lain, dan pin itu keputusan
  dependensi tersendiri. Bila reproduksi tetap tidak muncul → **uji versi PySide6 lain** dengan
  3.14.7 (pola K67). **T68 tetap dipakai**; laporan upstream (K66) tidak menunggu langkah ini.
- **Rencana teknisnya dicatat di `docs/riset-pyside6-gc-2026-10.md` bagian 9** (baru): perintah
  persisnya, patokan "mati" (tidak ada ringkasan pytest — **bukan** pola teks), perkiraan waktu
  (12 × ±27 dtk ≈ 5–6 menit), cabang keputusannya, dan **sumber plugin `plugin_tanpa_tahan.py`
  ditulis di dokumen itu** supaya sesi baru bisa membuatnya lagi meski `.tmp/` (gitignored) terhapus.
- **Prioritas sesi baru:** **#19c** (cadangan + daftar F12) tetap pekerjaan kode berikutnya menurut
  K59 c/K62 — K69 adalah langkah **riset** yang bisa dikerjakan di sesi yang sama sesudah #19c atau
  kapan pun, tanpa menunggu apa pun.
- **Verifikasi keadaan:** **status uji tidak berubah** — angka terakhir yang terukur tetap
  **849 lulus** (sesi 14b, CPython 3.14.7); perintahnya **tidak dijalankan ulang** pada sesi ini
  sesuai permintaan pengguna, dan itu dinyatakan apa adanya.

### Pelaksanaan aksi #19c: cadangan + daftar cadangan dari jendela (17 Okt 2026, sesi 16)

- **Pengguna memilih arah kerja sesi ini: "Aksi #19c — cadangan + daftar (F12) di jendela"**, dari
  dua jalur yang sama-sama "berikutnya" di `docs/lanjutan.md` (#19c dan riset **K69**). Jadi
  **K69 belum dijalankan** dan urutan riset yang dikuncinya tidak berubah.
- **Yang dikerjakan:** menu **Berkas** kini memuat **"Cadangan basis data…"** dan **"Daftar
  cadangan…"**. Cadangan berjalan lewat `Pekerja` dengan konfirmasi yang **menyebut folder
  tujuannya**, lalu menulis lewat `cadangan.buat` — jalur yang sama dengan `--buat-cadangan`.
  Daftarnya memakai teks yang sama dengan `--daftar-cadangan`. **Pemulihan tidak masuk** (K59 e),
  dan ketiadaannya disebut di konfirmasi, pesan hasil, dan daftar — bukan disimpulkan pengguna.
- **Bentuk teknisnya T73** (`docs/arsitektur.md`), dicatat sesudah dikerjakan seperti T72. Tiga hal
  yang paling perlu dibaca sesi berikutnya:
  1. **Folder tujuan dihitung satu kali** (`cadangan.folder_tujuan`), dan syarat "di luar folder
     data" menjadi `cadangan.periksa_tujuan` yang dipakai penulisan **dan** konfirmasi. Jadi
     dialognya menyebut folder yang benar-benar menerima cadangan (termasuk saat
     `--folder-cadangan`/`MEJASAHAM_BACKUP` yang menentukan), dan pengguna tidak pernah diminta
     menyetujui cadangan yang pasti ditolak.
  2. **Satu cacat perilaku ditutup:** `mkdir` folder tujuan berada **di luar** `try`, sehingga
     kegagalan yang paling mungkin pada F12 (folder tujuan tidak bisa ditulis) keluar sebagai
     traceback; pada jalur cadangan sebelum migrasi (`db.siapkan`) ia bahkan lolos dari
     penangkapnya dan berbunyi "tidak bisa membuat folder data … arahkan variabel lingkungan
     **MEJASAHAM_DATA**" — variabel yang salah untuk folder cadangan. Kini `GalatCadangan` menyebut
     folder tujuannya beserta jalan keluarnya (`--folder-cadangan`/`MEJASAHAM_BACKUP`).
  3. **Pemuatan ulang yang tidak dibayar:** `PanelDasbor.sesudah_tulis` memuat ulang dasbor sesudah
     **setiap** penulisan yang berhasil (mekanisme dari impor, aksi #19b), dan cadangan ikut
     membayarnya padahal ia **tidak mengubah satu baris pun**. `PermintaanTulis` kini menyatakan
     `muat_ulang` (cadangan: `False`) **dan** `pertanyaan` (cadangan tidak ditanya "tulis baris
     ini"). Terukur atas basis data 231 MB: `cadangan.buat` **1,26 dtk** sedangkan pemuatan ulang
     dasbor **63,83 dtk** → jalur jendela **54,46 dtk → 3,34 dtk**, dan cadangan sementara penulis
     lain memegang kunci tulis **62,42 dtk → 2,59 dtk**.
- **Yang juga terukur dan perlu diketahui:** cadangan **tidak menunggu kunci tulis** — ia hanya
  membaca basis data (`VACUUM INTO`), jadi perilaku K59 a/b (menunggu `busy_timeout` lalu berbunyi
  "belum menulis apa pun") **tidak** berlaku untuknya; yang berlaku untuknya
  `KALIMAT_BASIS_TIDAK_DISENTUH`. Terukur: cadangan berhasil sementara proses lain memegang
  `BEGIN IMMEDIATE`.
- **Verifikasi:** `.\.venv\Scripts\python -m pytest` → **863 lulus** (849 + **14 uji baru**: 3 di
  `tests/test_cadangan.py`, 6 di `tests/test_ui_tulis.py`, 5 di `tests/test_ui_jendela.py`);
  `pytest tests\test_ui_tulis.py tests\test_ui_jendela.py tests\test_ui_tabel.py -q` **6×
  berturut-turut 76 lulus**, tanpa proses yang mati (cacat PySide6/T68). **Seluruh 14 uji baru
  terbukti gagal pada HEAD** (13 di antaranya pada berkas yang tidak tersentuh #19b — pembanding
  ketat, `cadangan.py`/`tests/test_cadangan.py`); uji pemuatan ulang dibuktikan tambahan lewat
  **mutasi terarah** (`muat_ulang=True`), dan berkasnya dipulihkan **byte-identik** (SHA-256 sama).
- **Bukti atas data nyata** (`.uji-data/uji-cadangan-jendela/bukti/`; salinan `.uji-data/uji-dasbor`
  231 MB + arsip nyata `.uji-data/uji-u18`): **`bukti-cadangan-jendela.txt`** — cadangan dari jendela
  dan dari baris perintah **byte-identik** (`sha256 mejasaham.db` sama), integritas `ok`, total
  **1.008.187 baris sama** di sumber dan kedua cadangan, **23 berkas sama**, manifest sama (tanpa cap
  waktu), **baris daftar sama persis**, dan **cadangan buatan jendela benar-benar dipulihkan** ke
  folder bersih (integritas `ok`, jumlah baris sama, konfigurasi + arsip ikut) ·
  **`bukti-biaya-cadangan.txt`** (1,26 vs 63,83 dtk) · **`bukti-uji-pada-kode-lama.txt`** ·
  **`bukti-uji-mutasi-muat-ulang.txt`** · **empat tangkapan layar `offscreen`** (`tangkapan-1..4`,
  dirender lalu **dilihat**: dialog konfirmasi, pesan hasil di dasbor, dialog daftar cadangan, dan
  menu Berkas). Pembuatnya `.uji-data/riset-idx/cadangan-jendela/`.
- **Batas bukti, apa adanya:** tampilan sesungguhnya di monitor Anda belum pernah dilihat (semua
  dijalankan `offscreen`); tangkapan layarnya memakai salinan uji **kecil** `.uji-data/uji-u18`,
  sedangkan angka waktunya diukur atas salinan 231 MB.
- **Yang belum dikerjakan:** **aksi #19d** (`ubah-stop` + keputusan right issue, K62) tetap
  pekerjaan tulis berikutnya; `--pulihkan` tetap di baris perintah (K59 e); **U30** (folder tujuan
  cadangan dipilih per-cadangan?) dicatat sebagai usulan — **tidak memblokir #19d**; dan **K69**
  (reproduksi ulang cacat PySide6) **belum** dijalankan, sesuai pilihan arah kerja sesi ini.
- **Jebakan baru** yang dicatat di `docs/lanjutan.md` bagian 6: dialog konfirmasi **modal** membuat
  skrip bukti `offscreen` menggantung sampai dibunuh (tambalannya harus berlaku untuk **seluruh**
  jalan skrip), dan `QThread.isRunning()` sempat bernilai salah tepat sesudah `start()`, jadi
  penantian pekerja harus **setidaknya sekali** `wait()`.

### Pencatatan sesi 17: U30 → K70 dan arah sesi berikutnya (17 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna menjawab "sesuai rekomendasimu aja, catet dulu, biar kulanjutkan di sesi baru"** atas
  dua hal yang saya ajukan di akhir sesi 16: (a) **U30** (folder tujuan cadangan) dan (b) **arah
  sesi berikutnya** (#19d atau riset K69). Karena itu sesi ini **hanya mencatat**: tidak ada berkas
  kode yang disentuh, tidak ada impor, dan tidak ada baris basis data yang ditulis.
- **Yang dikunci: K70** — folder tujuan cadangan **tetap dari konfigurasi**
  (`--folder-cadangan`/`MEJASAHAM_BACKUP`, bawaan folder saudara folder data), dan jendela
  **menyebut** folder itu di dialog konfirmasi; **kotak pilih folder per-cadangan tidak
  ditambahkan sekarang**, dan bila kelak diminta ia menjadi keputusan tersendiri (bukan tafsir dari
  U30). Yang **tetap** berlaku: folder di dalam folder data ditolak **sebelum** konfirmasi
  (`cadangan.periksa_tujuan`, T73).
- **Arah sesi berikutnya, apa adanya:** **aksi #19d** (`ubah-stop` + keputusan right issue, K62)
  tetap pekerjaan **kode** berikutnya, dan **K69** (reproduksi ulang cacat PySide6) tetap pekerjaan
  **riset** yang **belum** dijalankan — keduanya tidak menunggu keputusan apa pun, dan urutannya
  tidak berubah oleh pencatatan ini.
- **Tidak ada pertanyaan yang tersisa:** U27–U30 semuanya sudah dijawab (K66–K68, K70), dan P34–P39
  sudah tertutup. Dua pekerjaan yang tinggal **manusia** tidak berubah: mengirim laporan PySide6
  (K66) dan memverifikasi angka `rasio-bank.csv` (K68).
- **Verifikasi keadaan:** `.\.venv\Scripts\python -m pytest` **dijalankan ulang sesudah pencatatan**
  → **863 lulus** (79,73 dtk) — **tidak berubah**, dan itu memang yang diharapkan karena tidak ada
  berkas kode yang disentuh. Angka itu menggantikan 849 lulus (sesi 14b) sebagai pijakan terakhir
  yang terukur.

### Pelaksanaan aksi #19d: `ubah-stop` + keputusan right issue dari jendela (17 Okt 2026, sesi 18)

- **Pengguna menjawab "Lanjutkan"**, jadi sesi ini mengerjakan **pekerjaan kode berikutnya yang
  sudah dikunci**: aksi **#19d** (K62) — `ubah-stop` (stop trailing) dan **keputusan right issue**
  dari jendela, dua tindakan yang **dituntut layar dasbor sendiri** lewat daftar tindakan menunggu
  (`stop_tertembus`, `tanpa_stop`, `pembatal_terpicu`, `right_issue_belum_diputuskan`) dan yang
  sebelumnya hanya bisa dieksekusi dari baris perintah. **K69 belum dijalankan** (urutan riset yang
  dikuncinya tidak berubah), dan tidak ada keputusan pengguna baru yang dibutuhkan untuk sesi ini —
  bentuk teknisnya sudah ditetapkan **T71 c** sebelum dikerjakan.
- **Yang dikerjakan (mengikuti T71 c apa adanya):**
  1. **`ubah-stop` di layar 11.1 (dasbor)** — posisinya **dipilih dari daftar** posisi aktif
     (K64/K65: jendela tidak pernah memilih entri pertama), isiannya stop baru + **tanggal** +
     alasan, dan `tgl_stop` yang tersimpan adalah **tanggal yang dinyatakan pengguna** (kosong =
     hari ini, sama dengan baris perintah) — ditulis apa adanya di dialog konfirmasi, sebab split
     sesudahnya dipindahkan dari basis itulah.
  2. **Keputusan right issue di layar 11.3 (detail emiten)** — tabel hak (`kode · posisi · tanggal
     aksi · rasio · tebus · tenggat · hak · keputusan`) yang barisnya **dipilih pengguna**, lalu
     formulir keputusan (`tebus`/`jual_hmetd`/`abaikan`). Isian yang tidak dipakai pilihan yang
     sedang aktif **dimatikan dan dikosongkan**, dan kotak transaksi `tebus` hanya berisi transaksi
     **beli milik posisi pada baris yang dipilih**.
  3. **Satu jalur inti, seperti #19b/#19c:** `posisi.ubah_stop` dan
     `posisi.catat_keputusan_right_issue` yang sudah ada — **bukan** jalur SQL kedua; `sumber`
     barisnya pun sama (`dicatat pengguna lewat --ubah-stop` / `--putuskan-right-issue`), supaya
     baris dari dua mode **identik**. `tebus` tetap menuntut transaksi yang **sudah tercatat**
     (T51): jendela **tidak** mencatatkan transaksinya diam-diam, dan pesan penolakannya menyebut
     jalan keluarnya (catat dulu lewat tombol "Catat transaksi", tekan Muat, lalu pilih).
- **Dua teks yang ikut berubah karena #19d, dan alasannya:** pesan tindakan menunggu
  `tanpa_stop` berbunyi *"tetapkan levelnya lewat `--ubah-stop`"* dan
  `right_issue_belum_diputuskan` *"Putuskan lewat `--putuskan-right-issue`"*. Sesudah #19d keduanya
  menyuruh pengguna jendela pindah ke baris perintah untuk tindakan yang **tombolnya ada di layar
  yang sama** — persis bentuk janji yang ditolak K58/K62. Keduanya kini menyebut **kedua** jalan
  (baris perintah **atau** layar 11.1/11.3), dan uji `test_tindakan_posisi_tanpa_stop` menjaganya.
- **Verifikasi:** `.\.venv\Scripts\python -m pytest` → **879 lulus** (863 + **16 uji baru**: 8 di
  `tests/test_ui_tulis.py`, 3 di `tests/test_ui_tabel.py`, 5 di `tests/test_ui_jendela.py`).
  **Bukti uji barunya bergigi lewat mutasi terarah** (`.uji-data/uji-stop-right-jendela/bukti/
  bukti-mutasi-19d.txt`): lima janji dimatikan satu per satu — tanggal `tgl_stop` tidak dipakai,
  penjaga `tebus` dimatikan, label transaksi salah kolom, sambungan `currentIndexChanged` dilepas,
  dan `_hak_terpilih` diisi sendiri — **kelimanya membuat uji sasaran gagal**, dan kelima berkasnya
  dipulihkan **byte-identik** (SHA-256 sama). Dijalankan juga pada worktree `HEAD`: **44 gagal /
  48 lulus**, dan itu **bukan** pembanding yang tajam — HEAD (`2e6a292`) adalah kode **sesi 11**,
  sebab pekerjaan sesi 12–17 belum di-commit, jadi uji lama seperti `label_rencana` pun gagal di
  sana. Karena itu bukti utamanya mutasi, bukan HEAD.
- **Bukti atas data nyata** (`.uji-data/uji-stop-right-jendela/bukti/bukti-stop-right-19d.txt`;
  **salinan** `.uji-data/uji-aksi-korporasi` — 999.421 bar, 4 posisi aktif, 4 right issue,
  3 keputusan — dijalankan **sekali lewat baris perintah, sekali lewat jendela sungguhan**
  `offscreen`, lalu dibandingkan):
  - **`v_posisi_terkini` (4 baris), `v_keputusan_right_issue_terkini` (3), dan `v_transaksi_terkini`
    (6) SAMA** antara dua jalur — termasuk `pelanggaran`, `catatan`, dan `tgl_stop`-nya.
  - **MLPT: stop pra-split 17.000 (basis 15 Jul 2026) → 1.200** tanggal 16 Okt 2026; yang muncul di
    layar adalah catatan basisnya (*"stop lama 17000 … menjadi 680 dalam basis sekarang (split 1:25
    pada 2026-07-21)"*) dan **tanpa** V5 — jadi split tidak lagi salah tuduh sebagai penurunan stop.
  - **ASII: 4.830 → 4.700 dicatat sebagai V5**, bukan ditolak; barisnya sama dengan jalur baris
    perintah.
  - **Hak right issue ditampilkan sebagai petunjuk**: MLPT 20 Sep 2026 (rasio 4:1 atas 25.000 lembar)
    → **6.250 lembar**, dengan catatan lot K31 (*"BUKAN kelipatan lot 100 … penebusan hanya bisa
    dicatat 6.200 lembar"*), dan **`tebus` tanpa transaksi ditolak berisik** dengan **0 baris**
    tertulis.
  - **`tebus` yang menunjuk transaksi #6 tersimpan sebagai revisi ke-2** dan barisnya sama dengan
    `--putuskan-right-issue` (keputusan sebelumnya tidak dihapus).
  - **4+2 tangkapan layar `offscreen` dilihat** (`tangkapan-1..6`): formulir ubah stop di 11.1,
    dialog konfirmasinya (stop lama → baru + `tgl_stop`), keadaan sesudah tersimpan, tabel hak +
    formulir keputusan di 11.3, dialog konfirmasi keputusan (memuat peristiwa + kalimat PETUNJUK),
    dan keadaan sesudah keputusan tersimpan. **Batas bukti apa adanya:** tampilan sesungguhnya di
    monitor Anda belum pernah dilihat (semuanya `offscreen`).
- **Dua temuan yang BELUM diperbaiki (dicatat, bukan dikerjakan diam-diam)** — keduanya **sudah
  dikunci sebagai keputusan pada sesi 19** (pencatatan saja): **K71 → aksi #24** dan **K72 → aksi
  #25**, dengan urutan pekerjaannya **K73**. Isi temuannya dibiarkan apa adanya di bawah ini
  sebagai bukti yang mendasarinya:
  1. **`posisi.catat_keputusan_right_issue` membuang `lembar`/`harga`/`biaya` diam-diam untuk
     keputusan `tebus`** (baris `if keputusan == "tebus"` tidak memeriksanya, sedangkan `INSERT`-nya
     menyimpan `NULL`). Jalur baris perintah ikut terkena:
     `--putuskan-right-issue KODE --keputusan tebus --id-transaksi 6 --lembar 500` **keluar 0** dan
     lembar itu hilang tanpa pesan — persis kelas "isian dibuang tanpa suara" yang diperiksa
     berisik untuk arah sebaliknya (`abaikan` + `--lembar`). **Jendela tidak ikut**: lapisan
     `ui/tulis.py` menolaknya sebagai `GalatTulis`. Perbaikannya satu syarat di `posisi.py` + uji
     penjaganya — dan itu menyentuh jalur yang sudah terverifikasi, jadi menunggu keputusan Anda.
  2. **`catatan` keputusan right issue menggelembung tiap revisi**: tiap revisi menyambung
     `catatan` lama **plus** catatan kaki yang sama lagi (*"tenggat right issue ini belum dinyatakan
     sumbernya…"*), sehingga revisi ke-5 menampilkan kalimat itu lima kali (terlihat di tangkapan
     layar 11.3 dan di keluaran `--putuskan-right-issue`). Bukan akibat #19d — perilakunya sudah ada
     sejak Tahap 2 langkah 4 — tetapi layar baru **membuatnya terlihat**.
- **Yang belum dikerjakan:** `--pulihkan` tetap di baris perintah (K59 e, dan K64 menetapkannya
  sebagai batas); **K69** (reproduksi ulang cacat PySide6) belum dijalankan; **aksi #21b** (mengisi
  `rasio-bank.csv` dari publikasi resmi sampai batas kandidat + kutipan) menunggu verifikasi angka
  oleh Anda (K68); **aksi #23** (U26) tetap belum dipicu (K61); dua pekerjaan **manusia** tidak
  berubah (mengirim laporan PySide6 K66, memverifikasi angka `rasio-bank.csv` K68).
- **Jebakan baru** yang dicatat di `docs/lanjutan.md` bagian 6: (a) menyunting berkas lewat
  `Path.write_text` di Windows **mengubah akhir baris** LF menjadi CRLF — sehingga berkas yang
  "dipulihkan" berubah byte-nya (tertangkap pemeriksa hash SHA-256, dan tiga berkas kode sempat
  tercemar sebelum dinormalkan kembali); (b) `Get-Content -Raw … | Set-Content -Encoding utf8`
  menulis ulang skrip Python dengan **penyandian ganda** (glif `—`/`·` menjadi mojibake) — pakai
  alat penyunting berkas, bukan pipa PowerShell, untuk berkas yang memuat glif.

### Pencatatan sesi 19: dua temuan sesi 18 → K71/K72, dan urutan pekerjaan → K73 (17 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna menjawab "sesuai rekomendasi mu saja, catet dulu nanti di lanjutkan di sesi baru"** atas
  tiga hal yang saya ajukan di akhir sesi 18. Karena itu sesi ini **hanya mencatat**: tidak ada
  berkas kode yang disentuh, tidak ada impor, dan tidak ada baris basis data yang ditulis.
- **Yang dikunci di `docs/keputusan.md` bagian 1:**
  1. **K71 → aksi #24** — cacat `tebus` yang **membuang `--lembar`/`--harga`/`--biaya` diam-diam**
     pada jalur baris perintah **diperbaiki**, dengan bentuk yang mengikuti pemeriksaan yang sudah
     ada untuk arah sebaliknya (`abaikan` + `--lembar`): inti menolak isian itu untuk **semua**
     keputusan selain `jual_hmetd`, termasuk `tebus`, dan pesannya menyebut bahwa yang menaikkan
     lembar adalah `transaksi` (T51). Satu uji baru yang harus **terbukti gagal pada kode
     sekarang**; jendela tetap menolaknya lebih dulu.
  2. **K72 → aksi #25** — `catatan` keputusan right issue yang **menggelembung tiap revisi**
     diperbaiki dengan **tidak menambahkan catatan turunan** (`catatan_kaki`) yang kalimatnya sudah
     ada di catatan sebelumnya; catatan yang **dinyatakan pengguna** dan `pesan_revisi` tetap
     disambung apa adanya. Alasan yang mengikat: riwayat lengkap sudah tersimpan di baris revisinya
     masing-masing (append-only), jadi menyalinnya berulang kali adalah duplikasi.
  3. **K73** — **urutan pekerjaan berikutnya: #24 + #25 dulu, lalu riset K69, lalu #21b.** #21b
     diletakkan paling akhir dengan alasan yang sudah terukur: ia menuntut verifikasi angka oleh
     Anda (K68) dan **0 dari 49 bank tertahan *hanya* oleh rasio bank**, jadi ia tidak membuka
     peringkat bank dengan sendirinya. **`--pulihkan` tidak masuk urutan ini** (K59 e/K64 = batas
     cakupan, bukan pekerjaan tertunda).
- **Yang tidak berubah:** dua pekerjaan **manusia** tetap sama — mengirim **laporan PySide6**
  (`docs/laporan-pyside6-siap-kirim.md`, K66; sesudah K69 dijalankan, laporannya bisa memuat kontrol
  yang reproduktif) dan **memverifikasi angka `rasio-bank.csv`** (K68, sesudah saya mengumpulkan
  kandidat + kutipannya). **Aksi #23/U26** tetap belum dipicu (K61).
- **Verifikasi keadaan:** `.\.venv\Scripts\python -m pytest` **dijalankan ulang sesudah pencatatan**
  → **879 lulus** — **tidak berubah**, dan itu memang yang diharapkan karena tidak ada berkas kode
  yang disentuh. Angka itu menggantikan 863 lulus (sesi 17) sebagai pijakan terakhir yang terukur.
- **Keadaan git sesudah sesi ini:** pengguna meminta **commit** di akhir sesi, dan seluruh pekerjaan
  sesi 12–19 **sudah di-commit**: **`3565d02`** = kode + uji aksi #19b/#19c/#19d (13 berkas,
  `833 → 879` uji), **`2aacd2b`** = catatan dokumennya (T72–T74, K55/K59/K62–K73, laporan PySide6
  siap kirim, riset PySide6), lalu commit ketiga = catatan keadaan git (pola yang sama dengan
  `2e6a292`). Working tree **bersih**; commit dilakukan **atas permintaan pengguna**, bukan atas
  inisiatif sesi agen.
- **Berkas bukti tidak ikut commit:** `.uji-data/` dan `.tmp/` **gitignored** (memang untuk itu),
  jadi seluruh bukti #19d (`.uji-data/uji-stop-right-jendela/bukti/`: teks bukti, bukti mutasi, enam
  tangkapan layar) dan pembuatnya (`.uji-data/riset-idx/stop-right-jendela/`) hanya ada di mesin ini —
  skripnya bisa dijalankan ulang kapan pun (perintahnya di `docs/lanjutan.md` bagian 3).

### Pelaksanaan aksi #24 dan #25 (K71/K72): isian `tebus` ditolak berisik, dan catatan revisi berhenti menggelembung (19 Okt 2026 — sesi 20)

- **Pengguna: "lanjutin".** Urutan **K73** sudah mengunci #24 dan #25 sebagai dua langkah pertama.
  Keduanya dikerjakan dalam **satu tahap** karena bersebelahan, kecil, dan menyentuh fungsi yang
  sama (`posisi.catat_keputusan_right_issue`); tidak ada keputusan baru yang diambil — bentuknya
  sudah ditetapkan K71/K72. **Tidak ada baris basis data yang ditulis dan tidak ada impor** selama
  sesi ini (uji memakai basis data sementara).
- **(a) Aksi #24 (K71) — isian yang tidak dipakai `tebus` kini ditolak berisik.** Pemeriksaan
  `lembar`/`harga`/`biaya` dipindahkan menjadi **satu** fungsi,
  `posisi._tolak_isian_yang_tidak_dipakai(keputusan, lembar, harga, biaya)`, yang dipanggil dari
  cabang `tebus` **dan** cabang `abaikan`; untuk `tebus` pesannya menyebut bahwa yang menaikkan
  lembar posisi adalah **transaksinya** (T51), untuk keputusan lain pesannya menyebut isian itu
  hanya berlaku untuk `jual_hmetd`. Sebelumnya pemeriksaan itu hanya ada di cabang `abaikan`,
  sehingga `--putuskan-right-issue … --keputusan tebus --id-transaksi N --lembar 500` **keluar 0**
  dan lembarnya hilang tanpa pesan (temuan sesi 18). Kini perintah yang sama **keluar 1** dengan
  pesan itu dan `keputusan_right_issue` tetap **0 baris**. Jendela tetap menolaknya lebih dulu
  (`ui/tulis.py`, T74) — dua jalur sekarang sepakat, dan inti bukan lagi satu-satunya tempat yang
  membuang isian tanpa suara.
- **(b) Aksi #25 (K72) — catatan turunan tidak lagi disalin tiap revisi.** Sebelum `teks_catatan`
  disusun, `catatan_kaki` disaring terhadap **baris** catatan revisi sebelumnya
  (`set(lama.catatan.splitlines())`): kalimat yang sudah ada tidak ditambahkan lagi, sedangkan
  catatan yang **dinyatakan pengguna** dan `pesan_revisi` tetap disambung apa adanya. Perbandingan
  per baris (bukan substring) disengaja supaya kalimat turunan yang **berubah** — mis. tanggal
  pencatatan yang berbeda — tetap dicatat. `PendaftaranKeputusan.catatan` tetap memuat seluruh
  catatan yang **berlaku** (bukan hanya yang baru ditulis), sebab pertanyaannya "apa yang perlu
  diketahui sekarang"; yang berubah hanya **isi baris yang disimpan**, bukan peringatannya.
- **(c) Verifikasi.**
  - `.\.venv\Scripts\python -m pytest` → **882 lulus** (`882 passed in 141,11s`; jalan pertama
    sesudah perubahan `166,03s`; 879 sebelum sesi ini). `.\.venv\Scripts\python -m pytest tests\test_aksi_korporasi_posisi.py -q` →
    **44 lulus** (41 + 3 uji baru).
  - **Ketiga uji baru terbukti gagal pada worktree `HEAD`** (`97d749e`), dijalankan dengan berkas
    uji dari working tree: `3 failed, 41 deselected` — `test_keputusan_tebus_menolak_isian_yang_tidak_dipakai`
    (tidak melempar galat), `test_baris_perintah_tebus_dengan_lembar_keluar_gagal` (kode keluar 0),
    dan `test_catatan_turunan_tidak_diulang_tiap_revisi` (kalimat turunan muncul 2× pada revisi
    ke-2). Buktinya `.uji-data/uji-k71-k72/bukti/bukti-uji-baru-gagal-pada-head.txt`.
  - Satu uji lama (`tests/test_ui_tulis.py::test_keputusan_right_issue_menolak_isian_yang_tidak_dipakai`)
    hanya diubah **komentarnya** — komentar lamanya menyatakan "inti membuangnya tanpa suara", dan
    itu tidak lagi benar. Perilaku yang diujinya tidak berubah.
- **(d) Yang belum dikerjakan.** **Riset K69** (reproduksi ulang cacat PySide6) adalah pekerjaan
  berikutnya menurut K73 — saat sesi 20 ditulis **belum dijalankan** (**sudah dijalankan sesi 21** —
  lihat catatan sesi 21 di atas); sesudahnya **aksi #21b** (`rasio-bank.csv`, K68).
  **Aksi #23/U26** tetap belum dipicu (K61). Saat sesi 20 ditulis tidak ada pertanyaan yang menunggu
  jawaban (**sesi 21 menambah U31/U32**, dan keduanya tidak memblokir).
- **Berkas yang disentuh:** `mejasaham/posisi.py` (satu fungsi baru + penyaringan catatan),
  `tests/test_aksi_korporasi_posisi.py` (3 uji), `tests/test_ui_tulis.py` (komentar),
  `docs/keputusan.md`, `docs/arsitektur.md` (**T75**), `docs/lanjutan.md`. **Belum di-commit** —
  commit hanya atas permintaan pengguna. Berkas bukti (`.uji-data/uji-k71-k72/`) **gitignored**.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest
  .\.venv\Scripts\python -m pytest tests\test_aksi_korporasi_posisi.py -q
  ```

### Pelaksanaan riset K69: reproduksi ulang dan A/B Python 3.13 (19 Okt 2026 — sesi 21)

- **Pengguna: "lanjutin".** Urutan **K73** menempatkan riset **K69** sebagai pekerjaan berikutnya
  sesudah #24/#25 (yang selesai di sesi 20). Tidak ada keputusan baru yang diambil: langkah 1 dan 2
  K69 sudah ditetapkan bentuknya, dan sesi ini **menjalankannya apa adanya**. **Tidak ada perubahan
  kode aplikasi, tidak ada impor, tidak ada baris basis data yang ditulis.**
- **Pijakan diperiksa lebih dulu:** `.\.venv\Scripts\python -m pytest -q` → **882 lulus**
  (`882 passed in 88,40s`), sama dengan angka yang dicatat sesi 20.
- **(a) Langkah 1 — reproduksi ulang berhasil (kontrol GAGAL).** Seluruh suite dijalankan **12×
  tanpa penangkal T68** di CPython 3.14.7 (`PYTHONPATH=.tmp`, `QT_QPA_PLATFORM=offscreen`,
  `-p plugin_tanpa_tahan`): **2 dari 12 jalan mati** (jalan 1 dan 10). Keduanya
  `Fatal Python error: Aborted`, `exit=3`, **tanpa traceback Python**, dan jejaknya selalu
  `tests/test_ui_jendela.py:195 _tunggu` → `pekerja.wait(60_000)` (yaitu `QThread.wait()`) dari
  `test_hasil_lama_dibuang_saat_pemuatan_gagal` baris 409; dump-nya **hanya utas utama** (tidak ada
  bingkai `[Pekerja]`). 10 jalan lain lulus `3 failed, 879 passed` — ketiga kegagalan itu **penjaga
  penangkalnya sendiri**, jadi justru bukti plugin bekerja. Ini syarat yang dituntut K69 sebelum
  membandingkan versi, dan **8.5 tidak bisa memberikannya** (0 kematian di 24 jalan berkas-tunggal).
- **(b) Langkah 2 — A/B di CPython 3.13.14.** Lingkungan `.tmp/py313` **dibangun ulang** (folder
  lamanya sudah tidak ada; interpreternya masih terpasang di folder data `uv`): `uv venv --python 3.13`
  + `uv pip install -r requirements.txt pytest` → **10,7 dtk, seluruhnya dari cache uv, tanpa
  unduhan**; hasilnya sama dengan 8.5 (PySide6 6.12.0 · shiboken6 6.12.0 · pytest 9.1.1 ·
  yfinance 1.7.0 · **769 MB** · `uv pip check` bersih). Perintah yang **sama persis** dijalankan 12×:
  **0 dari 12 mati** (11 jalan `3 failed, 879 passed`, 1 jalan `4 failed, 878 passed` — lihat (c)).
- **(c) Temuan baru: satu uji flaky (± 1 dari 12 jalan).**
  `tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah` gagal pada jalan 12
  karena membandingkan baris `snapshot` **termasuk `jam_ambil`/`batas_diketahui`**, dan kedua impor
  (baris perintah lalu jendela) melewati batas detik: `…T04:43:32+07:00` vs `…T04:43:33+07:00`.
  Bukan soal versi Python dan bukan kematian proses; dicatat **terpisah** sesuai K69 butir 5, dan
  diusulkan sebagai **U32 → aksi #26** (perbaikan satu berkas uji, **belum** dikerjakan).
- **(d) Pembacaan angkanya.** Menurut huruf K69, pin versi Python **boleh** diputuskan sekarang
  (kontrol gagal di satu versi, tidak di versi lain). Menurut buktinya, **belum pantas**: 2/12 vs
  0/12 dengan uji Fisher dua sisi **p ≈ 0,48** — selisih itu tidak dapat dibedakan dari kebetulan,
  dan kepastian statistik menuntut ±150 jalan per versi (±4–5 jam per versi). **Rekomendasi saya:
  jangan pin sekarang; T68 tetap; kirim laporan upstream (K66) yang kini punya kontrol yang gagal.**
  Usulan itu dicatat sebagai **U31** (bagian 2) — **belum** diputuskan pengguna saat sesi itu ditulis
  (**diputuskan sesi 22 → K74: jangan pin**). Langkah **3** K69
  (uji versi PySide6 lain) **tidak** dipicu.
- **(e) Jebakan pola teks terukur lagi.** Kata `access violation` muncul di **12 dari 12** log —
  semuanya kutipan *docstring* uji, **termasuk 10 log yang prosesnya hidup**. Patokan "mati" tetap
  **tidak ada ringkasan pytest**, seperti dicatat 8.5.
- **(f) Verifikasi & bukti.** Angka di atas dihasilkan skrip, bukan diketik tangan:
  `.uji-data/riset-idx/k69/` (`k69-jalankan.py`, `k69-jalankan-313.py`, `k69-ringkas.py`,
  `plugin_tanpa_tahan.py`); log mentah 24 berkas di `.uji-data/uji-k69/reproduksi/` dan
  `reproduksi-313/`; ringkasannya `.uji-data/uji-k69/bukti-k69.txt`. Rincian risetnya di
  `docs/riset-pyside6-gc-2026-10.md` **bagian 10**, dan laporan siap kirim
  (`docs/laporan-pyside6-siap-kirim.md`) sudah diperbarui dengan pengukuran ini (termasuk lampiran
  "sisa suite uji" — berkas uji sendirian **tidak lagi** memicu).
- **(g) Yang belum dikerjakan.** **Aksi #21b** (`rasio-bank.csv`, K68) adalah pekerjaan berikutnya
  menurut K73 — **belum** dijalankan. **U31** (pin Python) dan **U32** (uji flaky) saat itu menunggu
  jawaban Anda (**diputuskan sesi 22 → K74/K75**), duanya **tidak memblokir** #21b. **Laporan upstream**
  tetap menunggu dikirim pengguna (K66).
- **(h) Berkas yang disentuh:** `docs/riset-pyside6-gc-2026-10.md`, `docs/laporan-pyside6-siap-kirim.md`,
  `docs/keputusan.md`, `docs/lanjutan.md` — **dokumen saja**, tanpa kode. **Belum di-commit** (commit
  hanya atas permintaan pengguna). **Keadaan mesin yang berubah:** `.tmp/py313` ada kembali (769 MB,
  gitignored) supaya A/B bisa diulang.
- **Cara menjalankannya:**
  ```powershell
  $env:PYTHONPATH = "$PWD\.tmp"; $env:QT_QPA_PLATFORM = "offscreen"
  .\.venv\Scripts\python .tmp\k69-jalankan.py 12
  .tmp\py313\Scripts\python .tmp\k69-jalankan-313.py 12
  .\.venv\Scripts\python .tmp\k69-ringkas.py
  ```

### Pencatatan sesi 22: U31/U32 dikunci sebagai K74/K75 (19 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna: "sesuai rekomendasi aja, catet dulu nanti kulanjutin di sesi baru".** Karena itu sesi ini
  **hanya mencatat**: tidak ada berkas kode yang disentuh, tidak ada perintah riset yang dijalankan
  ulang, dan tidak ada baris basis data yang ditulis. Pekerjaan kodenya dilanjutkan di sesi baru.
- **U31 → K74: jangan pin CPython 3.13.** 3.14.7 tetap, **T68 tetap**, dan **laporan upstream (K66)
  dikirim** (berkasnya sudah memuat kontrol yang gagal: 2 dari 12 jalan suite penuh mati). Pin **hanya
  ditinjau ulang** bila Qt menjawab atau cacatnya muncul lagi di pemakaian nyata — dengan bukti baru,
  bukan sebagai lanjutan otomatis. Kepastian statistik, bila kelak diinginkan, adalah pekerjaan
  tersendiri (**±100–150 jalan per versi**, ≈ 3–4 jam per versi). **Langkah 3 K69** (uji versi
  **PySide6** lain) tetap **tidak** dipicu. **Tidak ada** perubahan `requirements.txt`/
  `requirements.lock.txt`, pin Python proyek (K3), atau `.venv`.
- **U32 → K75: uji flaky diperbaiki, pelaksanaannya aksi #26.** Bentuknya: baris `snapshot`
  dibandingkan **tanpa `jam_ambil`/`batas_diketahui`** (waktu masing-masing impor), sedangkan kolom
  lain tetap penuh dan tiga view lain tidak berubah. Alternatif "bekukan jam" lewat `db.waktu_iso`
  **ditolak** karena menuntut menambal `db` **dan** `ingesti` — lingkupnya lebih besar daripada
  cacatnya. **Belum dikerjakan** di sesi ini; #26 adalah pekerjaan kode berikutnya.
- **Urutan kerja sesudah pencatatan:** **#26** (kecil, satu berkas uji, sudah diputuskan) lalu
  **#21b** (`rasio-bank.csv`; tetap menuntut verifikasi angka oleh Anda — K68). **Aksi #23/U26**
  tetap belum dipicu (K61), dan **`--pulihkan` tetap bukan pekerjaan tertunda** (K59 e/K64).
- **Verifikasi sesudah pencatatan:** `.\.venv\Scripts\python -m pytest` → **882 lulus** (**96,59 dtk**)
  — tidak berubah, dan itu memang yang diharapkan karena tidak ada kode yang disentuh. Angka itu
  menggantikan 882 lulus (sesi 21) sebagai pijakan terakhir yang terukur.
- **Berkas yang disentuh:** `docs/keputusan.md` (K74/K75 + baris U31/U32 + catatan ini),
  `docs/arsitektur.md` (**T76** — bentuk teknis perbaikan uji flaky), dan `docs/lanjutan.md`
  (**dokumen saja**). **Belum di-commit** — commit hanya atas permintaan pengguna.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest
  ```

### Pelaksanaan sesi 23: aksi #26 — uji impor tidak lagi bergantung detik (19 Okt 2026)

- **Pengguna: "Lanjutin".** Yang dijalankan adalah **aksi #26** (K75) — pekerjaan kode berikutnya
  menurut urutan yang dikunci sesi 22 — **bukan #21b**, yang tetap pekerjaan berikutnya sesudah ini
  dan tetap menuntut verifikasi angka oleh Anda (K68).
- **Pijakan diperiksa lebih dulu:** `.\.venv\Scripts\python -m pytest` → **882 lulus (50,30 dtk)**,
  sama dengan angka sesi 22, sebelum satu berkas pun disentuh.
- **Yang berubah hanya `tests/test_ui_tulis.py`** — tanpa perubahan kode aplikasi, tanpa menyentuh
  basis data, dan tanpa mengubah perilaku yang diuji. Bentuknya persis K75/T76: konstanta
  `KOLOM_WAKTU_IMPOR = ("jam_ambil", "batas_diketahui")` + helper `_snapshot_tanpa_waktu_impor()`
  yang dipakai **hanya** oleh uji impor itu (helper `_baris()` bersama tidak diubah, supaya uji lain
  tetap membandingkan baris apa adanya), dan uji itu kini menegaskan **himpunan kolom** yang
  dibandingkan (`id_snapshot`, `tanggal_data`, `jumlah_emiten`, `jumlah_gagal`, `versi_skema`,
  `versi_aplikasi`, `catatan`) sehingga perbaikan yang ikut membuang kolom isi akan tertangkap.
- **Bukti, empat lapis dan semuanya dijalankan (bukan disimpulkan):**
  (a) **A/B dengan jam dipaksa** melewati batas detik (plugin `.tmp/plugin_detik.py`; momen eksplisit
  tidak diubah): versi `HEAD` (**versi lama**) **gagal** — `At index 1 diff: batas_diketahui
  '…T05:02:39+07:00' vs '…T05:02:40+07:00'`, hanya dua kolom waktu yang berbeda — sedangkan versi
  K75 **lulus** dengan jam yang sama; jadi cacatnya memang di perbandingan itu, bukan di tempat lain;
  (b) **mutasi "pembanding dibuang terlalu lebar"** (menambahkan `jumlah_emiten` ke kolom yang
  dibuang) **tertangkap**: `Extra items in the right set: 'jumlah_emiten'` — perbaikan tidak boleh
  melepas kolom isi; (c) `tests/test_ui_tulis.py` **12 dari 12** jalan **lulus** (33 uji tiap jalan,
  3,15–3,43 dtk) — pembanding angka sesi 21 yang gagal 1 dari 12; (d) suite penuh
  `.\.venv\Scripts\python -m pytest` → **882 lulus (48,96 dtk)**, angka yang sama dengan pijakan.
  Bukti + cara mengulang: `.uji-data/uji-k75/bukti/` (`bukti-ringkas.txt`, `bukti-ab-kode-lama.txt`,
  `bukti-ab-kode-baru.txt`, `bukti-mutasi-lebih-lebar.txt`, `bukti-12x.txt`), plugin disimpan di
  `.uji-data/riset-idx/k75/plugin_detik.py`.
- **Yang belum dikerjakan:** **aksi #21b** (`rasio-bank.csv` dari publikasi resmi sampai batas
  kandidat + kutipan, lalu **angka diverifikasi Anda** — K68) — pekerjaan berikutnya, dan **aksi #23**
  (U26) tetap belum dipicu (K61). **Dua pekerjaan manusia** tidak berubah: mengirim laporan PySide6
  (K66) dan memverifikasi angka `rasio-bank.csv` (K68). `--pulihkan` tetap **bukan** pekerjaan
  tertunda (K59 e/K64).
- **Berkas yang disentuh:** `tests/test_ui_tulis.py` (satu uji + konstanta + helper) dan tiga berkas
  dokumen — `docs/keputusan.md` (penanda "sudah dijalankan" pada K75 + catatan ini),
  `docs/arsitektur.md` (**T76** diberi status eksekusi + buktinya), `docs/lanjutan.md`
  (keadaan, aksi berikutnya, keadaan git). **Tanpa** perubahan `mejasaham/`, `conftest.py`, atau
  berkas uji lain. **Belum di-commit** — commit hanya atas permintaan pengguna.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest tests\test_ui_tulis.py -q          # 33 lulus
  .\.venv\Scripts\python -m pytest                                    # 882 lulus
  ```

### Pencatatan sesi 24: bentuk pelaksanaan #21b dikunci — pilot 5 bank (19 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna: "sesuai rekomendasimu aja, catet dulu kulanjutkan di sesi baru".** Itu jawaban atas
  pertanyaan penutup sesi 23 (**pilot 3–5 bank lebih dulu, atau seluruh 49 bank sekaligus**) → dikunci
  sebagai **K76**. Karena itu sesi ini **hanya mencatat**: tidak ada berkas kode yang disentuh, tidak
  ada impor, dan tidak ada baris basis data yang ditulis; pelaksanaannya di sesi baru.
- **K76: PILOT 5 BANK LEBIH DULU** — **BBCA, BBRI, BMRI, BBNI, BRIS**. Yang dikumpulkan: **kandidat +
  kutipan resmi** (NPL kotor, CAR, BOPO, NIM; `periode` + `tgl_publikasi`; `sumber`, `url`,
  `tanggal_akses`, dan `kutipan` apa adanya), disimpan sebagai berkas kandidat — **bukan** langsung ke
  `konfigurasi/rasio-bank.csv`. **Tidak satu angka pun masuk basis data sebelum Anda memverifikasinya**
  (K68; aturan keras 1). Bentuk kolomnya `berkas.SPESIFIKASI["rasio_bank"]` + tiga kolom pemeriksaan
  yang tidak ikut diimpor.
- **Alasan pilot (terukur, jangan dibalik):** **0 dari 49 bank tertahan *hanya* oleh rasio bank**
  (K68) — jadi pengisian ini **bukan** yang membuka peringkat bank; yang diuji adalah **jalur &
  format kutipan** sebelum dikerjakan 44× lagi. Bank pilot pun tetap gagal kriteria non-rasio pada
  snapshot #8 (`tren_ma200`; BBCA juga `pbv_relatif_sektor`, BRIS juga `kekuatan_relatif`), jadi
  pilot **tidak** dijanjikan menaikkan peringkat siapa pun.
- **Batas metode yang mengikat:** sumber **hanya publikasi resmi bank** (Laporan Eksposur Risiko &
  Permodalan / laporan publikasi triwulanan); PDF dibaca lewat **render QtPdf + pembacaan visual**
  (tanpa dependensi baru; **tanpa** menebak pemetaan glyph — K24/§2.1a `docs/lanjutan.md`); angka yang
  tidak terbaca dicatat **"tidak terbaca" beserta sebabnya**, bukan ditebak.
- **Urutan sesudahnya:** #21b pilot → **verifikasi angka oleh Anda** → barulah `rasio-bank.csv` diisi
  dan `--impor` dijalankan → periksa `v_rasio_bank_terkini`/`--saring` → **baru** putuskan perluasan
  ke 44 bank lain. **Aksi #23/U26** tetap belum dipicu (K61), dan **`--pulihkan` tetap bukan pekerjaan
  tertunda** (K59 e/K64). Dua pekerjaan manusia tidak berubah: mengirim laporan PySide6 (K66) dan
  memverifikasi angka `rasio-bank.csv` (K68).
- **Verifikasi sesudah pencatatan:** `.\.venv\Scripts\python -m pytest` → **882 lulus (48,98 dtk)** — tidak
  berubah, dan itu memang yang diharapkan karena tidak ada berkas kode yang disentuh.
- **Berkas yang disentuh:** `docs/keputusan.md` (K76 + catatan ini) dan `docs/lanjutan.md`
  (**dokumen saja**). **Tanpa** perubahan `mejasaham/`, `tests/`, atau basis data. **Belum di-commit** —
  commit hanya atas permintaan pengguna.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest
  ```

### Pelaksanaan aksi #21b — pilot 5 bank (19 Okt 2026, sesi 25 — **kandidat, belum diimpor**)

- **Pijakan diperiksa lebih dulu:** `pytest` → **882 lulus (49,60 dtk)**; `git status` memuat
  pekerjaan sesi 20–24 (belum di-commit) — tidak ditimpa.
- **Yang dikerjakan:** mengumpulkan **kandidat + kutipan resmi** untuk lima bank pilot (K76):
  BBCA, BBRI, BMRI, BBNI, BRIS. **Tanpa** menulis `konfigurasi/rasio-bank.csv`, **tanpa** `--impor`,
  **tanpa** satu baris basis data. Metodenya seperti yang diminta K76: PDF diunduh dari situs bank,
  halaman **dirender lewat QtPdf** lalu **dibaca secara visual** (bukan hanya lapisan teks), kutipan
  diambil apa adanya.
- **Hasil: 2 bank terbaca, 3 tidak.**
  - **BBCA** — *Laporan Keuangan Publikasi 30 Juni 2026*, hlm. 5, kolom "30 Jun 2026 (Tidak Diaudit)":
    **NPL gross 1,86% · KPMM 26,79% · BOPO 41,22% · NIM 5,32%**; `tgl_publikasi` **28 Jul 2026** dari
    nama berkas + header HTTP (halaman itu masih memuat tanggal tanda tangan lama *"Jakarta,
    23 Januari 2025"* — tidak dipakai).
  - **BRIS** — *Laporan Publikasi Triwulanan Juni 2026*, blok "Laporan Rasio Keuangan", kolom
    "30 Juni 2026 (Direviu)": **KPMM 20,41 · BOPO 69,71**; ditandatangani **21 Agustus 2026**.
    **NPF gross 1,80%** dan **Net Imbalan 5,42%** **tidak** diisi ke `npl_kotor_persen`/`nim_persen` —
    NPF bukan NPL dan NI bukan NIM; menunggu keputusan pengguna.
  - **BMRI** — `robots.txt`: `User-Agent: *` / `Disallow: /*.pdf$`; seluruh publikasinya PDF.
  - **BBNI** — `robots.txt`: `Disallow: /Portals/` (folder seluruh publikasinya) + tantangan Incapsula
    pada halaman katalog (HTTP 200, 212 byte) bahkan untuk peramban headless.
  - **BBRI** — `robots.txt` tak terbaca (Incapsula) dan katalog `bri.co.id/laporan` hanya kerangka JS;
    dokumen resmi yang **bisa** dibaca dari `ir-bri.com` (robots mengizinkan) tidak memuat BOPO/NIM —
    laporan keuangan Q2-2026 memuat "BOPO" 0 kali, dan presentasi 1H-2026 memakai **CIR 39,2%**
    (bukan BOPO). CIR tidak dipakai sebagai pengganti.
- **Tiga temuan (yang harus dibaca sebelum memperluas ke 44 bank):**
  **(T1) desimal koma ditolak pembaca impor** — versi pertama berkas kandidat memakai `1,86` dan
  impor berhenti berisik (`bukan angka yang bisa dibaca ('1,86')`); templat memang mencontohkan
  `2.35`. Aturannya: **berkas impor = titik, tampilan/ekspor = koma**.
  **(T2) kolom `sumber` per baris `rasio-bank.csv` tidak tersimpan** — `RasioBank` tidak punya bidang
  itu dan `ingesti` memakai label kumpulan (`impor berkas: <folder>`), jadi provenance per bank hilang
  saat impor → **U33** (usulan; belum dikerjakan).
  **(T3) bank syariah tidak menerbitkan NPL/NIM** (NPF/NI), jadi dua kolom BRIS sengaja kosong.
- **Uji jalur & format (bukan uji kebenaran angka):** sesudah tiga kolom pemeriksaan dibuang,
  `berkas.baca_folder` membaca berkas kandidat menjadi **186/2679/4122/532 bp** (BBCA) dan
  **None/2041/6971/None bp** (BRIS) — `bukti-uji-baca.txt` **LULUS**; tidak menulis basis data.
- **Berkas:** `.uji-data/riset-idx/rasio-bank/` (`kandidat-rasio-bank.csv`,
  `kandidat-tidak-terbaca.csv`, `bukti-pilot-rasio-bank.txt`, `pdf/`, `png/`, `unduh.py`,
  `baca-pdf.py`, `potong-pdf.py`, `buat-kandidat.py`, `uji-baca-kandidat.py`, `manifest-unduhan.txt`)
  dan **`docs/rasio-bank-kandidat-2026-10.md`** (ringkasan untuk diperiksa). **Tanpa** perubahan
  `mejasaham/`, `tests/`, `konfigurasi/`, atau basis data; `pytest` tetap **882 lulus**.
- **Pekerjaan berikutnya:** **verifikasi pengguna** atas angka kandidat (K68) + keputusan **U33** dan
  NPF/NI; sesudah itu isi `konfigurasi/rasio-bank.csv` → `--impor` → periksa
  `v_rasio_bank_terkini`/`--saring` → **baru** putuskan perluasan ke 44 bank lain. Ingat temuan K68:
  **0 dari 49 bank tertahan *hanya* oleh rasio bank** — mengisi berkas ini tidak sendirinya membuka
  peringkat bank. **Aksi #23/U26** tetap belum dipicu (K61).
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\buat-kandidat.py
  .\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\uji-baca-kandidat.py   # HASIL: LULUS
  .\.venv\Scripts\python -m pytest                                             # 882 lulus
  ```

### Pencatatan sesi 26: empat keputusan sesudah pilot #21b (19 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna: "sesuai rekomendasimu aja, catet dulu kulanjutkan di sesi baru".** Itu jawaban atas
  empat hal yang saya ajukan di akhir sesi 25 (verifikasi angka, NPF/NI bank syariah, tiga bank yang
  tidak terbaca, dan U33). Karena itu sesi ini **hanya mencatat**: tidak ada berkas kode yang
  disentuh, tidak ada impor, dan tidak ada baris basis data yang ditulis. Pelaksanaannya di sesi baru.
- **K77 — NPF/NI tidak dipetakan ke NPL/NIM.** Baris BRIS tetap **kosong** di `npl_kotor_persen` dan
  `nim_persen`; NPF gross 1,80% dan Net Imbalan 5,42% tetap tercatat di `keterangan`. NPL dan NIM
  BRIS berstatus **"tidak dihitung" beserta sebabnya** (AC-3), bukan nol. Ide kolom khusus bank
  syariah dicatat di `docs/ideas.md` (tunda).
- **K78 — U33 dikerjakan sebagai aksi #27.** Bidang `sumber` di `RasioBank` + pengisian dari kolom
  berkas (bawaan: label kumpulan) + uji yang **terbukti gagal pada `HEAD`**. Dikerjakan **sebelum**
  impor kandidat dan sebelum perluasan ke 44 bank — presedennya K18 untuk `fundamental`.
- **K79 — tiga bank yang menolak robots TIDAK diakali.** BMRI (`Disallow: /*.pdf$`), BBNI
  (`Disallow: /Portals/`), dan BBRI (robots tak terbaca; dokumen resmi yang terbaca tidak memuat
  BOPO/NIM) tetap tanpa angka. Pilot berlanjut dengan **2 bank**. Bila kelak diinginkan: **pengguna
  mengunduh PDF-nya sendiri** ke `.uji-data/riset-idx/rasio-bank/pdf/manual/`, lalu `baca-pdf.py`
  membaca berkas yang sama.
- **K80 — urutan berikutnya:** **(1) aksi #27** → **(2) verifikasi pengguna** atas angka kandidat
  (K68; tetap pekerjaan manusia, tidak berubah oleh pilot) → **(3) isi `konfigurasi/rasio-bank.csv`
  hanya dengan kolom `rasio_bank`** → `--impor` → periksa `v_rasio_bank_terkini`/`--saring` →
  **(4) baru** putuskan perluasan ke 44 bank (hitung dulu berapa bank yang menuntut langkah manual).
  **Aksi #23/U26** tetap belum dipicu (K61); **`--pulihkan`** tetap bukan pekerjaan tertunda.
- **Yang TIDAK berubah:** status berkas kandidat tetap **kandidat** — belum ada angka yang masuk
  basis data, dan **belum diverifikasi pengguna**. `docs/rasio-bank-kandidat-2026-10.md` tetap
  berlaku sebagai berkas pemeriksaan; sesi 26 hanya menambahkan status keputusannya.
- **Verifikasi sesudah pencatatan:** `.\.venv\Scripts\python -m pytest` → **882 lulus** — tidak
  berubah, dan itu memang yang diharapkan karena tidak ada berkas kode yang disentuh.
- **Berkas yang disentuh:** `docs/keputusan.md` (K77–K80, baris U33, catatan ini), `docs/lanjutan.md`,
  `docs/rasio-bank-kandidat-2026-10.md` (status keputusan), dan `docs/ideas.md` (ide kolom bank
  syariah). **Tanpa** perubahan `mejasaham/`, `tests/`, `konfigurasi/`, atau basis data. **Belum
  di-commit** — commit hanya atas permintaan pengguna.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest      # 882 lulus
  ```

### Pelaksanaan sesi 27: aksi #27 — `sumber` per baris `rasio_bank` (19 Okt 2026)

- **Pijakan diperiksa dulu:** `.\.venv\Scripts\python -m pytest` → **882 lulus (50,39 dtk)**. Sesudah
  pekerjaan: **885 lulus** — bertambah tiga uji baru, tidak ada uji lama yang berubah.
- **Yang dikerjakan (K78 → T77).** Tiga berkas kode:
  (a) **`mejasaham/ingesti.py`** — bidang `sumber: str | None = None` pada `RasioBank`, dan
  `_baris_rasio_bank` menulis `satu.sumber or sumber` (label per baris **menang** atas label kumpulan;
  baris yang dibentuk tanpa sumber tetap memakai label jalur impor, seperti sebelumnya).
  (b) **`mejasaham/berkas.py`** — `_baris_rasio_bank` mengisi `sumber` dari kolom berkas dengan
  `_tidak_kosong`, jadi sel kosong **ditolak** dengan pesan yang menyebut berkas, baris, dan kolomnya
  (aturannya sama dengan `fundamental` sejak K18; kolom itu memang `wajib=True, boleh_kosong=False`
  di `SPESIFIKASI` dan di template).
  (c) **`mejasaham/potret.py`** — `RasioBank` yang dibaca dari basis data membawa `sumber`-nya; tanpa
  ini provenance hanya ada di SQL dan hilang dari pemanggil `Potret`.
- **Tiga uji baru:** `tests/test_impor_berkas.py` — dua bank dengan `sumber` berbeda dalam satu berkas
  → tiap baris menyimpan dan mengembalikan sumbernya sendiri, bukan `impor berkas: <folder>`; sel
  `sumber` kosong ditolak per baris. `tests/test_ingesti.py` — `RasioBank` tanpa sumber memakai label
  kumpulan (perilaku lama tetap). **Bukti:** ketiganya **gagal pada worktree `HEAD` `97d749e`**
  (3 failed: `AttributeError`, `DID NOT RAISE GalatIngesti`, `TypeError` — bidangnya belum ada),
  **mutasi terarah 2/2 tertangkap** (ingesti dikembalikan ke label kumpulan → 2 failed; berkas berhenti
  mengisi sumber → 2 failed), dan kedua berkas dipulihkan **byte-identik** (hash dicocokkan). Rincian:
  `.uji-data/uji-k78/bukti/bukti-ringkas.txt`. **Atas berkas kandidat pilot #21b** (tanpa basis data),
  `uji-baca-kandidat.py` kini mencetak sumber **per baris** — BBCA dan BRIS membawa nama publikasinya
  sendiri, bukan `impor berkas: <folder>` (`.uji-data/uji-k78/bukti/bukti-uji-baca-kandidat.txt`).
- **Dua catatan yang harus dibaca sesi berikutnya.** **(1)** Berkas `rasio-bank.csv` yang sel
  `sumber`-nya kosong kini **berhenti berisik** — ini perilaku yang tertulis di spesifikasi dan T67,
  dan tidak ada data nyata yang terdampak (berkas produksi masih template `<<CONTOH>>`; berkas
  kandidat sudah berisi `sumber`), tetapi berkas lama yang selnya kosong akan ditolak per baris.
  **(2)** `potret._fundamental` **masih** tidak mengisi `Fundamental.sumber` saat membaca ulang —
  asimetri yang sekarang tertutup untuk `rasio_bank` masih terbuka untuk `fundamental`; dicatat di
  T77 sebagai batas yang diketahui dan **tidak** dikerjakan di sesi ini.
- **Yang TIDAK berubah:** nilai kandidat `rasio_bank` **belum diverifikasi** dan **belum diimpor**
  (K68); `konfigurasi/rasio-bank.csv` tidak disentuh; tidak ada baris basis data yang ditulis;
  **aksi #23/U26** tetap belum dipicu (K61); **`--pulihkan`** tetap bukan pekerjaan tertunda.
- **Berkas yang disentuh:** `mejasaham/ingesti.py`, `mejasaham/berkas.py`, `mejasaham/potret.py`,
  `tests/test_impor_berkas.py`, `tests/test_ingesti.py`, `docs/keputusan.md` (K78, U33, catatan ini),
  `docs/arsitektur.md` (**T77**), `docs/lanjutan.md`. Bukti di `.uji-data/uji-k78/bukti/`
  (**gitignored**). **Belum di-commit** — commit hanya atas permintaan pengguna.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest                       # 885 lulus
  .\.venv\Scripts\python -m pytest tests\test_impor_berkas.py tests\test_ingesti.py -q `
      -k "sumber_per_baris_rasio or rasio_bank_tanpa_sumber or sumber_baris_rasio"   # 3 lulus
  ```

### Pencatatan sesi 28: K81–K82 (19 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna: "butuh putusan apa dari saya? kalau ada sesuai rekomendasi mu aja, catet dulu, jangan
  ngoding, mau kulanjutkan di sesi berikutnya."** Itu jawaban atas **satu** tafsir yang saya minta
  ditinjau di akhir sesi 27 (sel `sumber` kosong) dan atas **satu** temuan yang saya laporkan
  (`potret._fundamental`). Karena itu sesi ini **hanya mencatat**: tidak ada berkas kode/uji yang
  disentuh, tidak ada impor, dan tidak ada baris basis data yang ditulis.
- **K81 — sel `sumber` kosong di `rasio-bank.csv` DITOLAK.** Perilaku yang sudah terpasang di aksi
  #27 itulah yang dikunci; tidak ada perubahan kode. Alasan: `SPESIFIKASI` menyatakan
  `boleh_kosong=False`, T67 menyebut sel kosong ditolak per baris, dan K18 (`fundamental`) memakai
  aturan yang sama. "Bila kosong: label kumpulan" dari K78 berlaku pada **bidang** `RasioBank` yang
  `None` (mis. dibentuk program lain), bukan sebagai izin bagi sel berkas yang kosong. Ini juga
  menutup kemungkinan satu sel terlupa di antara 44 bank berubah diam-diam menjadi
  `impor berkas: <folder>`.
- **K82 — `potret._fundamental` juga mengisi `Fundamental.sumber` saat membaca ulang; dikerjakan
  sebagai aksi #28.** Temuan sesi 27: kolom `fundamental.sumber` sudah `NOT NULL` sejak K18, tetapi
  `potret._fundamental` tidak meneruskannya, sehingga `Potret` selalu melihat `sumber=None` — kelas
  kekeliruan yang sama dengan K78, hanya berpindah tempat. Bentuknya satu baris (`sumber=baris["sumber"]`)
  + **uji yang terbukti gagal pada `HEAD`** (nilainya `None`, bukan `AttributeError`), dengan bentuk
  teknis **T78** saat dikerjakan. **Aksi #28 adalah pekerjaan agen berikutnya**, lalu **berhenti
  menunggu verifikasi pengguna** (K80 langkah 2); **44 bank dan #23 tidak dimulai tanpa permintaan.**
- **Yang TIDAK berubah:** angka kandidat tetap **belum diverifikasi** dan **belum diimpor** (K68);
  `konfigurasi/rasio-bank.csv` tidak disentuh; aksi #23/U26 tetap belum dipicu (K61); `--pulihkan`
  tetap bukan pekerjaan tertunda (K59 e); seluruh pekerjaan sesi 20–28 **belum di-commit** — commit
  hanya atas permintaan pengguna.
- **Verifikasi sesudah pencatatan:** `.\.venv\Scripts\python -m pytest` → **885 lulus** — tidak
  berubah, dan itu memang yang diharapkan karena tidak ada berkas kode/uji yang disentuh.
- **Berkas yang disentuh:** `docs/keputusan.md` (K78 penanda tafsir, **K81–K82**, catatan ini),
  `docs/arsitektur.md` (**T77** — tafsir K81 + batas yang menjadi #28), `docs/lanjutan.md`, dan
  `docs/rasio-bank-kandidat-2026-10.md` (catatan pengisian `sumber` per baris). **Tanpa** perubahan
  `mejasaham/`, `tests/`, `konfigurasi/`, atau basis data.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest      # 885 lulus
  ```

### Pelaksanaan sesi 29: aksi #28 — `sumber` per baris `fundamental` (19 Okt 2026)

- **Pijakan diperiksa dulu:** `.\.venv\Scripts\python -m pytest` → **885 lulus (45,31 dtk)**.
  Sesudah pekerjaan: **887 lulus (32,09 dtk)** — bertambah **dua** uji baru, tidak ada uji lama yang
  berubah. (Rencana di tabel aksi menyebut satu uji/886; yang dikerjakan dua uji/887 — lihat catatan
  di butir "dua uji baru" di bawah.)
- **Yang dikerjakan (K82 → T78).** Satu baris di `mejasaham/potret.py`:
  `_fundamental` kini mengisi `sumber=baris["sumber"]`. Jalur tulisnya **tidak** disentuh — kolom
  `fundamental.sumber` sudah `NOT NULL` sejak K18 dan `ingesti._baris_fundamental` sudah menulis
  `satu.sumber or kumpulan.sumber`; yang hilang selama ini hanya **pembacaan** saat baris dibaca
  kembali, sehingga `Potret` selalu melihat `None` walaupun basis datanya menyatakan asalnya.
- **Dua uji baru di `tests/test_potret.py`:** **(a)**
  `test_sumber_fundamental_per_baris_ikut_kembali_lewat_potret` — dua laporan dari dua publikasi
  berbeda (BBCA, BRIS) dalam satu kumpulan data; memeriksa **kedua** sisi, yaitu baris tersimpan
  memang berbeda sumbernya **dan** `potret.muat` mengembalikan asal itu per baris. **(b)**
  `test_fundamental_tanpa_sumber_memakai_label_kumpulan_saat_dibaca_ulang` — laporan yang dibentuk
  tanpa `sumber` kembali dengan label kumpulan (`"uji"`), bukan `None`, sebab `None` di bidang itu
  adalah **arti** ("tidak menyatakan asal"), bukan ketiadaan. Uji kedua ditambahkan di luar rencana
  satu-uji karena tanpa ia perbaikan yang hanya memenuhi "bukan `None`" akan lolos; ongkosnya satu
  uji kecil, dan jumlahnya dilaporkan apa adanya (887, bukan 886).
- **Bukti empat lapis** (`.uji-data/uji-k82/bukti/`, **gitignored**): **(a)** kedua uji **gagal pada
  worktree `HEAD` `97d749e`** — `tests/test_potret.py` disalin dari working tree, `mejasaham/` dari
  HEAD — dengan `[None] == [<sumber baris>]` (bukan `AttributeError`, persis catatan K82);
  **(b)** **dua mutasi terarah tertangkap**: `sumber=None` → 2 failed, dan
  `sumber=baris["asal_tgl_publikasi"]` → 2 failed dengan `['sumber'] == ['uji']` (jadi ujinya
  memeriksa **kolomnya**, bukan sekadar "bukan `None`"); berkas dipulihkan **byte-identik**
  (SHA-256 `199E851B…E380B` sebelum dan sesudah kedua mutasi); **(c)** `tests/test_potret.py`
  **7 lulus**; **(d)** suite penuh **887 lulus**.
- **Yang TIDAK berubah:** angka kandidat `rasio_bank` **belum diverifikasi** dan **belum diimpor**
  (K68); `konfigurasi/rasio-bank.csv` tidak disentuh; **tidak ada baris basis data yang ditulis**;
  **aksi #23/U26** tetap belum dipicu (K61); **`--pulihkan`** tetap bukan pekerjaan tertunda
  (K59 e/K64); **44 bank** tidak dimulai.
- **Berkas yang disentuh:** `mejasaham/potret.py` (satu baris + komentar alasannya),
  `tests/test_potret.py` (dua uji + satu butir docstring modul), `docs/keputusan.md` (K82, catatan
  ini), `docs/arsitektur.md` (**T78**, penutup batas di **T77**), `docs/lanjutan.md`, dan
  `docs/rasio-bank-kandidat-2026-10.md` (status #28). **Belum di-commit** — commit hanya atas
  permintaan pengguna.
- **Pekerjaan berikutnya: verifikasi pengguna** atas angka kandidat (K68) — pekerjaan manusia —
  lalu isi `konfigurasi/rasio-bank.csv` (hanya kolom `rasio_bank`), `--impor`, periksa
  `v_rasio_bank_terkini`/`--saring`, **baru** putuskan perluasan ke 44 bank (K80).
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest                       # 887 lulus
  .\.venv\Scripts\python -m pytest tests\test_potret.py -q `
      -k "sumber_fundamental_per_baris or fundamental_tanpa_sumber"   # 2 lulus
  ```

### Pencatatan sesi 30: K83–K84 — pekerjaan manusia mana yang dialihkan (19 Okt 2026 — **tanpa perubahan kode**)

- **Pengguna: "sesuai rekomendasimu aja, kalau ada butuh pekerjaan manusia, bisa kamu aja ga yang
  lakuin? catet dulu nanti kulanjutkan di sesi baru."** Sesi ini **hanya mencatat**: tidak ada berkas
  kode/uji yang disentuh, tidak ada impor, dan tidak ada baris basis data yang ditulis. Yang dikunci:
  **K83** — verifikasi angka `rasio_bank` **dialihkan ke agen** dengan pagar "cocok persis", dikerjakan
  sebagai **aksi #29**; **K84** — pengiriman laporan PySide6 **tidak** dialihkan, tetap pekerjaan
  pengguna.
- **Cara membaca "sesuai rekomendasimu aja":** persetujuan **cara kerja** (verifikasi → isi CSV →
  `--impor` → periksa), **bukan** pernyataan bahwa angkanya sudah benar. Karena itu status berkas
  tetap **kandidat, belum diverifikasi, belum diimpor**, dan `konfigurasi/rasio-bank.csv` di folder
  data **tidak disentuh** di sesi ini. Bila maksud pengguna lain, itu cukup dikoreksi di awal sesi
  baru — hasilnya sama, sebab pemeriksaan ulangnya murah.
- **Pagar aksi #29 (K83), supaya sesi baru tidak menafsir sendiri:** baca **ulang** PDF resmi yang
  sama; cocokkan **SHA-256** berkas dengan manifest; bandingkan **setiap sel** `kandidat-rasio-bank.csv`
  (empat rasio, `periode`, `tgl_publikasi`, `sumber`) dengan yang tercetak; **satu selisih sekecil
  apa pun → berhenti, 0 baris ditulis, lapor** — angka yang tidak terbaca tidak diganti tebakan.
  **Bila cocok persis:** cadangkan basis data kerja dulu (preseden sesi 5/7 sebelum impor), tulis dua
  baris ke `konfigurasi/rasio-bank.csv` di folder data (hanya sembilan kolom
  `berkas.SPESIFIKASI["rasio_bank"]`; tiga kolom pemeriksaan `url`/`tanggal_akses`/`kutipan` dibuang;
  dua kalimat `keterangan` yang **basi** dibersihkan — *"karena kolom `sumber` belum dipakai impor"*
  dan *"menunggu keputusan Anda"* untuk NPF/NI BRIS yang sudah diputuskan K77), lalu `--impor`,
  periksa `v_rasio_bank_terkini` + `--saring`, dan laporkan apa adanya (ingat: **0 dari 49 bank
  tertahan *hanya* oleh rasio bank** — K68).
- **Yang TIDAK berubah:** angka kandidat **belum** masuk basis data; **44 bank** dan **aksi #23/U26**
  tidak dimulai tanpa permintaan (K61); **`--pulihkan`** tetap bukan pekerjaan tertunda (K59 e/K64);
  commit sesi 20–30 **belum** dilakukan — commit hanya atas permintaan pengguna.
- **Verifikasi sesudah pencatatan:** `.\.venv\Scripts\python -m pytest` → **887 lulus** — tidak
  berubah, dan itu memang yang diharapkan karena tidak ada berkas kode/uji yang disentuh.
- **Berkas yang disentuh:** `docs/keputusan.md` (**K83–K84** + penunjuk di K68/K80 + catatan ini),
  `docs/lanjutan.md`, `docs/rasio-bank-kandidat-2026-10.md` (§0 dan §6), dan
  `docs/laporan-pyside6-siap-kirim.md` (penunjuk K84). **Tanpa** perubahan `mejasaham/`, `tests/`,
  `konfigurasi/`, atau basis data.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest      # 887 lulus
  ```

### Pelaksanaan aksi #29: verifikasi ulang angka `rasio_bank` lalu impor (19 Okt 2026 — K83; **tanpa perubahan kode/uji**)

- **Pijakan:** `.\.venv\Scripts\python -m pytest -q` → **887 lulus** (44,93 dtk) sebelum pekerjaan.
- **Pagar K83 dijalankan apa adanya — dan tidak ada satu sel pun yang berbeda:** (a) **SHA-256**
  kedua PDF dihitung ulang dan **sama dengan `manifest-unduhan.txt`** (BCA baris 3, BRIS baris 7);
  (b) kedua halaman **dirender ulang** ke `.uji-data/uji-k83/bukti/` (bukan memakai PNG pilot),
  termasuk potongan kepala kolom dan blok tanda tangan BRIS; (c) **14 dari 14 sel** cocok persis —
  `periode`, `tgl_publikasi`, empat rasio, `sumber` untuk kedua bank; (d) karena tidak ada selisih,
  impor **boleh** dan **dijalankan**.
- **Tanggal publikasi diperiksa, bukan diwarisi:** BCA `2026-07-28` dari nama berkas (`20260728`)
  **dan** HEAD ulang ke URL-nya (`HTTP 200`, `Content-Length 196142` = berkas lokal,
  `Last-Modified Tue, 28 Jul 2026 09:13:08 GMT`); BRIS `2026-08-21` dari tanda tangan yang
  **terbaca di render** ("Jakarta, 21 Agustus 2026"). Tanggal tanda tangan BCA yang basi
  (*"Jakarta, 23 Januari 2025"*) tetap **tidak** dipakai.
- **Cadangan lebih dulu (preseden sesi 5/7):** `--buat-cadangan --folder-data .uji-data\mejasaham`
  → `.uji-data\mejasaham-cadangan\20261019T181212314095+0700`. **Sesudah itu baru menulis.**
- **Berkas produksi:** `konfigurasi/rasio-bank.csv` di folder data — 2 baris, **sembilan kolom**
  (`url`/`tanggal_akses`/`kutipan` dibuang), `sumber` per baris terisi, dan **dua kalimat `keterangan`
  yang basi dibersihkan** (*"karena kolom `sumber` belum dipakai impor"*, *"menunggu keputusan Anda"*
  untuk NPF/NI BRIS — sudah diputuskan K77). Dibaca ulang lewat `berkas.baca_folder` **sebelum**
  impor: seluruh sel sama dengan kandidat terverifikasi (sha256 berkas `c5d833af…`).
- **Impor:** `--impor .uji-data\mejasaham\konfigurasi --folder-data .uji-data\mejasaham` → keluar
  **0**, **snapshot 12** · tanggal data 2026-10-11 · **2330 baris baru, 2898 sudah ada dan sama**.
  Rincian per tabel: `rasio_bank` **0 → 2**; `notasi_khusus` **9719 → 12047 (+2328)** yang
  **hanya berbeda di kolom `sumber`** (label folder impor berubah dari folder riset `k53-k54` ke
  folder konfigurasi produksi; `tanggal_selesai`/`keterangan` identik, 0 beda lain); tabel lain
  **tidak berubah**; `PRAGMA integrity_check` = `ok`.
- **Periksa:** `v_rasio_bank_terkini` memuat dua baris — BBCA `186/2679/4122/532` bp dan BRIS
  `None/2041/6971/None` bp, masing-masing dengan `sumber` publikasinya sendiri. **`--saring` penuh
  tidak berubah:** snapshot 12 · kualitas-nilai/v1 · 973 emiten · **9 lolos · 9 dinilai** (sama
  seperti sebelum impor). **Sebabnya terukur, bukan dugaan:** `jenis` emiten masih kosong untuk
  **973** emiten, sehingga kriteria bank (NPL/CAR/BOPO/NIM) **tidak diterapkan kepada siapa pun**;
  `--saring --kode BBCA,BRIS` juga tetap "tidak bisa dinilai — coverage: EBIT 12 bulan terakhir
  tidak bisa dihitung", dan hasil parsialnya **tidak disimpan** (peringatan perintahnya sendiri).
  Jadi **K68 terbukti lagi**: mengisi rasio bank tidak dengan sendirinya mengubah peringkat.
- **Dua catatan yang tidak disembunyikan:** **(1)** tanggal BRIS `2026-08-21` (tanda tangan) vs
  `Last-Modified` **24 Agu 2026** → dicatat sebagai **U34** (yang diimpor adalah nilai yang tercetak,
  bukan tafsir baru; nilainya juga tertulis di `keterangan` baris BRIS); **(2)** impor **satu folder**
  menulis ulang label `sumber` baris `notasi_khusus` yang labelnya berasal dari folder lain (+2328
  revisi) — dicatat sebagai jebakan di `docs/lanjutan.md` bagian 6, **bukan** diperbaiki diam-diam.
- **Yang TIDAK dikerjakan:** perluasan ke **44 bank** (belum diminta), **#23/U26** (K61),
  **`--pulihkan`** (bukan pekerjaan tertunda, K59 e/K64), dan **commit** (hanya atas permintaan).
- **Berkas yang disentuh:** `konfigurasi/rasio-bank.csv` (folder data), basis data kerja
  (`mejasaham.db` + snapshot 12 + `arsip-snapshot/2026-10-11/snapshot-12/`), dan **empat berkas
  `docs/`** (`docs/keputusan.md`, `docs/arsitektur.md` **T79**, `docs/lanjutan.md`,
  `docs/rasio-bank-kandidat-2026-10.md`) — **tanpa** perubahan `mejasaham/` dan `tests/`.
  Bukti mentah `.uji-data/uji-k83/bukti/` (**gitignored**).
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest                                    # 887 lulus
  .\.venv\Scripts\python .uji-data\uji-k83\verifikasi.py             # 14/14 sel + hash (keluar 0)
  .\.venv\Scripts\python -m mejasaham --saring --folder-data .uji-data\mejasaham
  ```

### Pencatatan sesi 31 (lanjutan): K85–K87 — jawaban "sesuai rekomendasi" (19 Okt 2026 — **tanpa perubahan kode/data**)

- **Pengguna: "sesuai rekomendasi"** atas tiga hal yang diajukan sesudah aksi #29 dilaporkan. Sesi ini
  **hanya mencatat**: tidak ada kode/uji yang disentuh, **tidak ada pemulihan cadangan**, tidak ada
  impor ulang, **tidak ada baris basis data yang ditulis**, `--ambil-jenis` **tidak** dijalankan, dan
  commit tidak dilakukan.
- **Yang dikunci:** **K85** — impor yang menulis ulang `sumber` **2.328** baris `notasi_khusus`
  **diterima apa adanya** (2.328/2.328 hanya kolom `sumber`; 0 beda lain; revisi lama tetap
  menyimpan label lama). **K86** — **U34 ditutup**: `tgl_publikasi` BRIS **tetap 2026-08-21** (tanggal
  tercetak yang diverifikasi); perbaikan kelak hanya lewat baris revisi bila ada bukti resmi tanggal
  terbit. **K87** — perluasan ke **44 bank DITUNDA**: `jenis` **973 emiten** masih kosong sehingga
  rasio bank belum berpengaruh; urutannya bila diminta: hitung langkah manual (K79) → isi `jenis`
  (K21 atau isian tangan) → buktikan rasio dipakai → baru tambah 44 dokumen.
- **Yang TIDAK berubah:** `konfigurasi/rasio-bank.csv` dan basis data (2 baris `rasio_bank`,
  snapshot 12) seperti sesudah aksi #29; cadangan `20261019T181212314095+0700` tetap disimpan;
  **#23/U26** tetap belum dipicu (K61); **`--pulihkan`** tetap bukan pekerjaan tertunda (K59 e/K64);
  pengiriman laporan PySide6 tetap pengguna (K84).
- **Verifikasi sesudah pencatatan:** `.\.venv\Scripts\python -m pytest -q` → **887 lulus** — tidak
  berubah, dan itu memang yang diharapkan karena tidak ada berkas kode/uji yang disentuh.
- **Berkas yang disentuh:** `docs/keputusan.md` (**K85–K87** + penunjuk U34/K80 + catatan ini),
  `docs/lanjutan.md`, `docs/arsitektur.md` (penunjuk K86 di **T79**), dan
  `docs/rasio-bank-kandidat-2026-10.md` (status U34/44 bank). **Tanpa** perubahan
  `mejasaham/`, `tests/`, `konfigurasi/`, atau basis data.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest      # 887 lulus
  ```

### Pelaksanaan prasyarat K87: isi `jenis` dari sumber data (sesi 32, 19 Okt 2026 — **tanpa perubahan kode/uji**)

- **Pengguna: "Lanjutkan."** Dibaca sebagai permintaan menjalankan **langkah prasyarat** yang sudah
  dikunci K87 — **bukan** persetujuan menambah 44 dokumen. Pijakan diperiksa lebih dulu:
  `.\.venv\Scripts\python -m pytest -q` → **887 lulus (29,77 dtk)**.
- **Diukur sebelum menulis:** `jenis` **973 NULL**, `sektor_sumber` **0 terisi**, dan
  `konfigurasi/emiten.csv` di folder data **identik dengan basis data** (0 selisih pada seluruh kolom
  yang dibandingkan) — jadi menimpa berkas itu **tidak menghilangkan suntingan tangan**, dan
  `--timpa-jenis` dipakai dengan alasan yang diperiksa, bukan diasumsikan.
- **Cadangan lebih dulu:** `--buat-cadangan` → `.uji-data\mejasaham-cadangan\20261019T182735608155+0700`.
- **`--ambil-jenis --timpa-jenis`** atas **973** kode (±35 menit, jeda 0,4 dtk): **49 bank_keuangan ·
  862 umum · 62 kosong**. Yang kosong = **55 kode gagal diambil** (log menampilkan `HTTPError: HTTP
  404` untuk 15 di antaranya; mis. ARMY, BTEL, WSKT) + **7** yang
  sumbernya tidak menyatakan sector/industry (mis. BOSS, DEAL, ETWA, KAYU, LAPD); `siklikal_komoditas`
  **0** (tidak pernah diturunkan, K21). Berkas ditulis lalu **dibaca ulang** oleh pembaca impor:
  **973 baris, 49 bank_keuangan**.
- **Diperiksa sebelum impor:** kolom `nama`/`sektor_idx_ic`/`papan`/`status_notasi`/
  `tanggal_notasi`/`jumlah_saham`/`free_float_persen` **0 beda**; 973 kode sama; yang berubah hanya
  `jenis` dan `sektor_sumber` (**911** baris) serta `sumber` (973 baris, kini memuat label mentah
  `sector=`/`industry=` — batas (a) K21).
- **Impor:** `--impor .uji-data\mejasaham\konfigurasi --folder-data .uji-data\mejasaham` → keluar **0**,
  **snapshot 13**, **973 baris baru / 4255 sudah ada dan sama**. `notasi_khusus` **tetap 12.047** —
  berbeda dari sesi 31, karena impor kali ini berasal dari **folder yang sama** sehingga label
  `sumber`-nya tidak berubah; `rasio_bank` tetap **2**, `PRAGMA integrity_check` = `ok`.
  (Simulasi di salinan yang lebih dulu dijalankan memakai folder berbeda dan **memang** menulis ulang
  2.450 baris `notasi_khusus` — jebakan sesi 31 terkonfirmasi ulang, dan itulah sebabnya impor
  produksi dijalankan dari folder aslinya.)
- **Bukti aturan PRD 8.4/AC-16 kini berlaku:** `--saring` melaporkan
  **`49 bank_keuangan (dari data) · 862 umum · 62 belum terisi`**; untuk **BBCA** keempat kriteria bank
  **berlaku dan lolos** — `npl_kotor` 186 bp (≤ 3,00%), `car` 2679 bp (≥ 14,00%), `bopo` 4122 bp
  (≤ 85,00%), `nim` 532 bp (≥ 3,50%) — dan **`der`/`coverage`/`cfo_ni` menjadi `berlaku=False`**
  ("tidak berlaku untuk bank & lembaga keuangan"); untuk **BRIS** hanya `car`+`bopo` yang dinilai,
  sedangkan `npl_kotor`/`nim` menjawab *"tidak dilaporkan pada periode 2026-06-30"* (K77 — NPF/NI
  tidak dipetakan). **47 dari 49 bank** belum punya rasio: kriteria bank berlaku, tetapi alasannya
  *"rasio bank (NPL/CAR/BOPO/NIM) belum diimpor lewat rasio-bank.csv"*.
- **Peringkat TIDAK berubah** — tetap **9 lolos · 9 dinilai**, dan sembilan kandidat (AUTO 55,8 …
  DSNG 51,9) **sama persis**; yang berubah hanya satu angka: **884 → 883** emiten "tidak bisa
  disaring", sebab **BBCA** kini punya vonis nyata (gagal `pbv_relatif_sektor` + `tren_ma200`) alih-alih
  "tidak bisa dinilai (coverage)". Jadi **K68 terbukti lagi**, dan **44 dokumen tetap ditunda (K87)**.
- **Yang TIDAK dikerjakan:** **44 dokumen** (K87), **hitung langkah manual (K79)**, **#23/U26** (K61),
  **`--pulihkan`** (K59 e/K64), dan **commit** (hanya atas permintaan) — **commit lalu dikerjakan
  pada sesi yang sama** atas permintaan pengguna: **`4bbaf20`** = kode + uji sesi 20/23/27/29,
  **`eb30214`** = dokumen sesi 21–32, lalu catatan keadaan git.
- **Berkas yang disentuh:** `konfigurasi/emiten.csv` di folder data (`.uji-data/mejasaham/`,
  **gitignored**), basis data kerja + **snapshot 13** + arsipnya (**gitignored**), dan **tiga berkas
  `docs/`** (`docs/keputusan.md` — catatan ini + penunjuk K21/K80/K87; `docs/lanjutan.md`;
  `docs/rasio-bank-kandidat-2026-10.md` — §9) — **tanpa** perubahan `mejasaham/` dan `tests/`.
  Bukti `.uji-data/uji-jenis-kerja/bukti/` (**gitignored**).
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest                                                    # 887 lulus
  python -m mejasaham --saring --folder-data .uji-data\mejasaham                      # 49 bank_keuangan
  python -m mejasaham --ambil-jenis --timpa-jenis --folder-data .uji-data\mejasaham   # bila diulang
  ```

### Pelaksanaan hitung langkah manual K79 (sesi 33, 19 Okt 2026 — **tanpa perubahan kode/uji, tanpa menulis basis data**)

- **Pengguna: "Lanjutkan."** Dibaca sebagai permintaan menjalankan **langkah yang tersisa dari K87** —
  *hitung dulu berapa bank yang menuntut langkah manual* (K79) — **bukan** persetujuan menambah
  44 dokumen. K87 tetap berlaku: perluasan itu **belum dimulai**.
- **Pijakan diperiksa lebih dulu:** `.\.venv\Scripts\python -m pytest -q` → **887 lulus (46,76 dtk)**.
- **Yang diukur** (baca-saja, klien HTTP biasa tanpa peramban): (a) **domain resmi** tiap bank,
  ditetapkan dari judul halaman depannya — empat calon domain yang salah terbukti dari isinya
  (`bumiarta.co.id` "Coming Soon", `bankoke.com` halaman parkir, `bankmnc.com` "Coming Soon",
  `bankcapital.id` tidak ada) dan diganti sebelum diukur; (b) **`robots.txt`** diurai per grup
  `User-agent` (token `mejasaham` lalu `*`) dan diuji terhadap **11 jalur wakil** (`/` + sepuluh jalur
  PDF lazim); (c) **keterjangkauan situs** dengan tiga percobaan untuk tiap kegagalan, dan halaman
  tantangan (Cloudflare/Incapsula/WAF F5) dikenali dari isinya.
- **Hasil untuk 44 bank sasaran** (49 `bank_keuangan` − BBCA/BRIS − BBRI/BMRI/BBNI):
  **8 MANUAL**, **2 tidak terukur**, **34 otomatis mungkin**.
  **Manual — robots (2):** **BTPS** (`User-agent: *` / `Disallow: /`) dan **DNAR**
  (`Disallow: /media`, `/images`). **Manual — akses (6):** **AGRS** (WAF F5 "Request Rejected" 3/3),
  **BBMD** (Cloudflare "Just a moment…" 403 3/3), **BBTN** (Incapsula 212 byte 3/3), **BNLI**
  (403 "Access Denied" 3/3), **SUPA** (403 Forbidden 3/3), **BACA** (502 konsisten 3/3 — situs tidak
  melayani saat diukur). **Tidak terukur — jaringan (2):** **INPC** (connect timeout 3/3) dan
  **SDRA** (SSL error 3/3) — **bukan** bukti kebijakan bank, dicatat sebagai batas pengukuran.
- **Kontrol metode:** tiga bank pilot di luar sasaran diukur ulang dan **konsisten dengan K79** —
  BMRI `Disallow: /*.pdf$`, BBNI `Disallow: /Portals/` + Incapsula 212 byte, dan **BBRI situsnya
  terjangkau** (307 → halaman 351.497 byte pada percobaan ke-2), jadi yang gagal di sana memang
  dokumennya, bukan aksesnya.
- **Izin robots ≠ dokumen ketemu.** Uji satu tingkat atas 34 bank "otomatis mungkin": **12**
  benar-benar berpindah ke halaman publikasi (16 bila jangkar halaman depan ikut dihitung) dan **11**
  memuat tautan PDF (isinya belum diperiksa). Angka itu **batas bawah** (situs yang dirender
  JavaScript tidak menampakkan tautannya kepada klien HTTP biasa). Jadi 34 bank itu tetap menuntut
  pencarian dokumen + render + verifikasi sel seperti pilot (K76/K83), bukan satu skrip.
- **Akibatnya diusulkan U35** (`docs/keputusan.md` bagian 2): **tetap tunda** perluasan 44 dokumen;
  bila kelak diminta, **34 otomatis dulu**, lalu **8 manual** hanya bila PDF-nya tersedia (K79:
  pengguna mengunduh sendiri, tidak diakali). **K68 tetap berlaku** — 0 dari 49 bank tertahan
  *hanya* oleh rasio bank.
- **Yang TIDAK dikerjakan:** **44 dokumen** (K87), **#23/U26** (K61), **`--pulihkan`** (K59 e/K64),
  dan **commit** (hanya atas permintaan).
- **Berkas yang disentuh:** **tiga berkas `docs/`** (`docs/keputusan.md` — catatan ini + **U35** +
  penunjuk di K87; `docs/lanjutan.md`; `docs/rasio-bank-kandidat-2026-10.md` — **§10**) —
  **tanpa** perubahan `mejasaham/`, `tests/`, atau satu baris basis data. Bukti
  `.uji-data/uji-k79/bukti/` + skrip `.uji-data/riset-idx/k79/` (**gitignored**).
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest                                              # 887 lulus
  .\.venv\Scripts\python .uji-data\riset-idx\k79\pindai-robots.py               # 49 bank, ±4 menit
  .\.venv\Scripts\python .uji-data\riset-idx\k79\uji-halaman-publikasi.py       # uji 34 bank
  .\.venv\Scripts\python .uji-data\riset-idx\k79\gabung-hasil.py                # tabel final + ringkasan
  ```

### Pencatatan sesi 33 (lanjutan): U35 → K88 — jawaban "sesuai rekomendasi saja, catet jangan ngoding" (19 Okt 2026 — **tanpa perubahan kode/data**)

- **Pengguna: "sesuai rekomendasi saja, catet jangan ngoding."** Dibaca sebagai: rekomendasi **U35
  (tetap tunda)** **diterima dan dikunci**, dan sesi ini **hanya mencatat** — **tidak** ada
  `--ambil-jenis`, `--impor`, pengunduhan PDF, atau menyentuh basis data.
- **Yang dikunci — K88:** perluasan `rasio-bank.csv` ke **44 bank tetap DITUNDA**. Bila kelak
  pengguna memintanya, urutannya sudah terukur: **34 bank "otomatis mungkin" lebih dulu**, lalu
  **8 bank yang menuntut langkah manual** (BTPS, DNAR, AGRS, BBMD, BBTN, BNLI, SUPA, BACA) hanya bila
  PDF-nya tersedia — K79: pengguna mengunduh sendiri ke `pdf/manual/`, **tidak diakali**; **INPC** dan
  **SDRA** menunggu jaringan/sertifikatnya normal. Setiap dokumen tetap menuntut pencarian + render +
  verifikasi sel (K76/K83), dan izin robots **bukan** jaminan dokumen ketemu (12/34 halaman
  publikasi nyata, 11/34 tautan PDF).
- **Alasannya** (dari pengukuran, bukan dugaan): 8/44 manual · 2 tidak terukur · 34 otomatis, tetapi
  **K68 tetap berlaku — 0 dari 49 bank tertahan *hanya* oleh rasio bank** dan peringkat tidak berubah
  (9 lolos/9 dinilai, sembilan kandidat sama). Jadi biaya besar itu belum membeli perubahan hasil;
  menundanya tidak menutup pintu karena bentuk kerjanya sudah terbukti di pilot (K76/K83).
- **Tidak ada pertanyaan yang tersisa:** U35 sudah dijawab; **bagian 2 kembali tidak menunggu
  jawaban**. Dua pekerjaan manusia juga tidak berubah: **mengirim laporan PySide6** (K66/K84) —
  verifikasi angka `rasio-bank.csv` sendiri sudah dialihkan dan selesai (K83/aksi #29).
- **Verifikasi sesudah pencatatan:** `.\.venv\Scripts\python -m pytest -q` → **887 lulus** — tidak
  berubah, seperti diharapkan karena tidak ada berkas kode yang disentuh.
- **Berkas yang disentuh:** **tiga berkas `docs/`** (`docs/keputusan.md` — **K88** + baris U35 +
  catatan ini; `docs/lanjutan.md`; `docs/rasio-bank-kandidat-2026-10.md` — §10.4) — **tanpa** kode,
  uji, impor, atau basis data.

### Pelaksanaan aksi #23/U26: konteks pasar disimpan saat `--saring` (19 Okt 2026 — sesi 34)

- **Pemicu.** Pengguna membuka sesi baru dengan **"Lanjutkan"**. Karena tidak ada aksi terkunci yang
  menunggu (K88 menunda 44 bank; #23/U26 belum dipicu; `--pulihkan` batas cakupan), sesi berhenti
  dan **bertanya arah**; pengguna memilih **"#23/U26 — simpan konteks pasar saat `--saring`"**.
  Itulah pemicu eksplisit yang dituntut K61, jadi aturan yang sudah disepakati 17 Okt 2026 dipakai
  apa adanya — bukan keputusan baru.
- **Pijakan.** `pytest` → **887 lulus (44,19 dtk)** sebelum perubahan; yang dibaca lebih dulu:
  K55/K59/K61/K80/K87/K88, **T66**, `docs/skema-data.md` 5.12, dan `_konteks_pasar`/`susun`.
- **Yang dibangun.** **(a)** migrasi **015** `konteks_pasar` — STRICT, kunci asing ke `snapshot` dan
  `preset_saring`, **PK `id_snapshot + id_preset + sumber_harga`**, kolom `versi_hitung`,
  `breadth_nilai/status/alasan/asal`, `indeks/tanggal/penutupan/penutupan_sebelumnya`, `catatan`,
  `dihitung_pada`; CHECK menjaga `dihitung` ⇔ nilai dan `tidak_dihitung` ⇔ alasan (aturan keras 2).
  **(b)** modul baru **`mejasaham/konteks_pasar.py`** — `BarisIndeks`/`KonteksPasar` pindah ke sini,
  ditambah `dari_bahan`, `sebab_bahan_kurang`, `simpan`, `muat`, dan `VERSI_HITUNG = "pasar-1"`.
  **(c)** `pengatur.jalankan_saring` menulis konteks **hanya** bila `simpan=True`; kegagalan
  menulisnya menjadi **peringatan** (skor sudah sah; dasbor akan menghitung ulang), bukan
  pembatalan saringan. **(d)** `dasbor.susun` membaca simpanan lewat `konteks_pasar.muat` hanya
  bila snapshot + preset + label sumber harga + versi hitung **semuanya** cocok; selain itu
  menghitung ulang lewat jalur yang sama dengan saringan, tanpa menulis apa pun. Preset dipilih
  **sekali** (`_preset_untuk_pasar`) lalu dipakai untuk kunci **dan** hitungan, supaya keduanya
  tidak bisa menunjuk preset berbeda.
- **Uji baru 19.** `tests/test_konteks_pasar.py` **9** (bulat-balik penuh, tulis ulang bukan tumpuk,
  keadaan "tidak dihitung" + indeks kosong, versi hitung lain, kunci snapshot/preset/sumber lain,
  sumber `None` = teks kosong, konteks tanpa breadth ditolak, versi tidak kosong, CHECK mesin) +
  `tests/test_dasbor.py` **9** (saring menyimpan; dasbor memakai simpanan dan **tidak** menghitung
  ulang; sebab bahan kurang ikut tersimpan; `simpan=False` tidak menulis; snapshot/preset/sumber/
  versi lain tidak dipakai; kegagalan menulis konteks menjadi peringatan tanpa membatalkan saring) +
  `tests/test_db.py` **1** (bentuk migrasi 015). **Bukti gagal pada `HEAD` `6888b1b`** (worktree
  terpisah, `.uji-data/uji-k61/bukti/uji-baru-pada-head-*.txt`): **5 uji perilaku gagal**
  (`no such table: konteks_pasar` ×3, `AssertionError: dasbor menghitung ulang …` ×1, dan
  `AttributeError: module 'mejasaham.pengatur' has no attribute 'konteks_pasar'` ×1), dan
  `tests/test_konteks_pasar.py` **gagal koleksi** (`ImportError: cannot import name 'konteks_pasar'`).
  Empat uji penjaga lain lulus di HEAD dan tetap lulus di kode baru — gunanya menangkap implementasi
  yang memakai simpanan **tanpa** syarat.
- **Verifikasi.** Suite penuh **906 lulus (31,84 dtk; 44,60 dtk pada jalan sebelumnya)**; uji jendela+tulis+tabel **6× 92 lulus**
  (7,78–10,56 dtk), tanpa proses yang mati. Atas **salinan** basis data kerja (`.uji-data/uji-k61`,
  247 MB, snapshot 13): `--dasbor` **18,95 dtk → 0,74 dtk (25,7×)**, dan baris `Pasar` **identik**
  sebelum/sesudah (`IHSG 6.093 … breadth 33,8% · rezim RISK-OFF`); `--saring` **18,16 dtk**
  (tidak lebih lambat secara terukur); baris `konteks_pasar` = snapshot 13 · `kualitas-nilai/v1` ·
  `yfinance/Yahoo Finance (tidak resmi)` · breadth 0,3383 (68/201) · RISK-OFF · IHSG 6093/6031.
  Pengukuran pertama (konteks dihapus lebih dulu) memberi **26,44 → 0,72 dtk**; angka mesin berayun,
  arah dan baris `Pasar`-nya sama. Bukti `.uji-data/uji-k61/bukti/` (`bukti-k61.txt`, keluaran tiap
  perintah, `uji-jendela-6x.txt`, `uji-baru-pada-head-*.txt`).
- **Yang tidak dikerjakan.** **44 bank** (K88), **#22(a)** pengiriman laporan PySide6 (manusia,
  K84), **`--pulihkan`** (K59 e/K64), dan **commit** (hanya atas permintaan). **Basis data kerja
  tidak disentuh** — hanya salinannya; `konfigurasi/rasio-bank.csv` dan `emiten.csv` juga tidak.
- **Berkas yang disentuh.** Kode: `mejasaham/skema.py`, **`mejasaham/konteks_pasar.py` (baru)**,
  `mejasaham/pengatur.py`, `mejasaham/dasbor.py`. Uji: **`tests/test_konteks_pasar.py` (baru)**,
  `tests/test_dasbor.py`, `tests/test_db.py`. Dokumen: `docs/keputusan.md` (K61/U26 + catatan ini),
  `docs/arsitektur.md` (**T80**), `docs/skema-data.md` (**5.16**), `docs/lanjutan.md`. Bukti dan
  skrip pengukur di `.uji-data/uji-k61/` dan `.uji-data/riset-idx/k61/` (**gitignored**).
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pytest
  .\.venv\Scripts\python -m pytest tests\test_konteks_pasar.py tests\test_dasbor.py -q
  .\.venv\Scripts\python .uji-data\riset-idx\k61\ukur-k61.py         # bukti waktu pada salinan
  .\.venv\Scripts\python .uji-data\riset-idx\k61\uji-jendela-6x.py   # 6× uji jendela
  ```

### Pelaksanaan Tahap 5: bundel PyInstaller onedir (19 Okt 2026 — sesi 35)

- **Pemicu.** Pengguna membuka sesi dengan **"Lanjutkan"**; karena tidak ada aksi terkunci
  (K88 menunda 44 bank, satu pekerjaan manusia adalah laporan PySide6), sesi bertanya arah dan
  pengguna menjawab **"sesuai rekomendasimu"**. Rekomendasinya **Tahap 5 — pengemasan**, dengan
  alasan terukur: seluruh fitur v0.1 sudah jalan (906 uji lulus), **T3** sudah mengunci
  PyInstaller onedir, dan syarat lama "kemas sesudah impor & cadangan punya jalur di jendela"
  sudah terpenuhi. Ini bukan keputusan produk baru; bentuk teknisnya dicatat sebagai **T81**.
- **Pijakan.** `pytest` → **906 lulus (29,08 dtk)**; working tree bersih di `2b90e91`. Yang dibaca
  lebih dulu: `mejasaham/__main__.py`, `cli.main`, `berkas.FOLDER_BAWAAN`/
  `konfigurasi.FOLDER_BAWAAN`, `.gitignore`, dan **T3**. PyInstaller diperiksa kompatibel dengan
  Python 3.14.7 (dukungan 3.14 ada sejak 6.15.0; versi terpasang **6.22.3**).
- **Yang dibangun.** **(a)** `requirements-build.txt` — `-r requirements.txt` + PyInstaller
  **6.22.3** dan transitive-nya dipin (`altgraph`, `pefile`, `pyinstaller-hooks-contrib`,
  `pywin32-ctypes`, `setuptools`); **tidak** masuk `requirements.txt`, jadi tidak ikut bundel.
  **(b)** `tools/entry_exe.py` — titik masuk bundel yang memanggil `cli.main`, jalur yang sama
  dengan `python -m mejasaham`. **(c)** `tools/build_exe.py` — satu daftar argumen
  PyInstaller (`--onedir --console --hide-console hide-early --noupx`,
  `--add-data mejasaham/defaults`), `--dry-run`, dan pemeriksaan berkas hasil; kode keluar
  PyInstaller diteruskan apa adanya. **(d)** `tests/test_pengemasan.py` — dua uji kontrak:
  bentuk perintah build + pemetaan `defaults`, dan kelengkapan sepuluh berkas template.
- **Verifikasi build.** `dist/MejaSaham/MejaSaham.exe` (15,3 MiB) + `_internal/`
  (**184,5 MB**). `--help` keluar 0. `--muat-konfigurasi --folder-data <folder kosong>` menyalin
  `parameter-bursa.toml`, membuat basis data, dan mengeluarkan delapan peringatan
  "belum_terverifikasi" ke stderr dengan **keluar 0** — keadaan yang sah. `--saring` **18,40 dtk**
  dan `--dasbor` **0,97 dtk** pada salinan data kerja (snapshot 13), keluarannya **identik**
  dengan jalur modul (18,13 dtk / 0,76 dtk). `--ambil-fundamental --kode BBCA` berhasil
  mengimpor yfinance/pandas dan menulis 4 baris — jadi impor malas tetap terbawa bundel.
  GUI `offscreen` tetap hidup 8 dtk pada folder data kosong maupun salinan berisi snapshot
  (folder kosong menampilkan kegagalan "belum ada snapshot" lewat pekerja latar — jendela tetap
  hidup; satu-satunya peringatan lain adalah font `offscreen` yang memang tidak dipakai di layar
  nyata). Salinan folder
  aplikasi dijalankan dengan `PATH` **tanpa** `.venv`/Python dan `PYTHONHOME`/`PYTHONPATH`
  dikosongkan: `--help` dan `--muat-konfigurasi` tetap keluar 0.
- **Uji.** Suite penuh **908 lulus** — 906 + 2 uji kontrak pengemasan; terukur **38,12 dtk**
  pada jalan pertama dan **30,91 dtk** pada jalan terakhir. Tidak ada perubahan pada kode
  aplikasi; `requirements.txt` dan basis data kerja tidak disentuh. `.venv` hanya menerima
  **alat build** (PyInstaller + transitive), bukan dependensi runtime baru. Build memakai salinan
  data di `.uji-data/uji-tahap5/` (**gitignored**).
- **Yang belum.** **Ikon aplikasi** — belum ada aset resmi, dan membuatnya sendiri berarti
  mengarang identitas visual; PyInstaller memakai ikon bawaannya. **Uji klik-ganda di mesin yang
  benar-benar tanpa Python terpasang** — yang bisa dibuktikan di sini adalah salinan bersih
  dengan `PATH` tanpa Python. **44 bank** tetap ditunda (K88), dan **pengiriman laporan PySide6**
  tetap pekerjaan manusia (K84). Commit hanya atas permintaan.
- **Berkas yang disentuh.** Build: `requirements-build.txt` (baru), `tools/entry_exe.py` (baru),
  `tools/build_exe.py` (baru). Uji: `tests/test_pengemasan.py` (baru). Dokumen: `README.md`,
  `AGENTS.md`, `docs/arsitektur.md` (**T81**), `docs/keputusan.md` (catatan ini),
  `docs/lanjutan.md`. Keluaran `build/`, `dist/`, dan `.uji-data/uji-tahap5/` **gitignored**.
- **Cara menjalankannya:**
  ```powershell
  .\.venv\Scripts\python -m pip install -r requirements-build.txt
  .\.venv\Scripts\python tools\build_exe.py
  .\dist\MejaSaham\MejaSaham.exe --help
  .\.venv\Scripts\python -m pytest
  ```

### Pelaksanaan ikon aplikasi Tahap 5 (22 Okt 2026 — sesi 36)

- **Pemicu:** pengguna meminta pekerjaan ikon diselesaikan untuknya. Ikon orisinal bertema grafik
  pasar dibuat dari SVG, tanpa logo/merek pihak lain dan tanpa dependensi baru.
- **Implementasi:** assets/mejasaham.svg menjadi sumber; tools/generate_icon.py menghasilkan ICO
  16, 32, 48, dan 256 piksel. Build PyInstaller menyematkan ikon ke EXE dan menyalin ikon ke
  assets/ di bundel. Jendela PySide6 memakai ikon yang sama dan gagal jelas bila aset hilang.
- **Verifikasi:** uji terarah 5 lulus; suite penuh **910 lulus (49,87 dtk)**. Build PyInstaller
  keluar 0 dan menghasilkan EXE 15,5 MiB. Resource ikon bertipe RT_ICON/RT_GROUP_ICON ditemukan
  dalam EXE; ICO di folder bundel terbaca sebagai QIcon. EXE --help keluar 0 dengan PATH yang
  hanya berisi Windows System32/Windows, PYTHONHOME dan PYTHONPATH kosong.
- **Belum dikerjakan:** uji klik-ganda pada mesin yang benar-benar tidak memiliki Python.
  Ikon dapat dilihat sebagai pratinjau SVG di assets/mejasaham.svg.
- **Berkas:** assets/mejasaham.svg, assets/mejasaham.ico, tools/generate_icon.py,
  tools/build_exe.py, mejasaham/ui/jendela.py, tests/test_pengemasan.py,
  tests/test_ui_jendela.py, README.md, docs/arsitektur.md (T82), dan docs/lanjutan.md.
- **Cara menjalankan:** .venv/Scripts/python tools/generate_icon.py;
  .venv/Scripts/python tools/build_exe.py;
  .venv/Scripts/python -m pytest.

### Perbaikan EXE gagal membuka jendela (22 Okt 2026 — sesi 37)

- **Gejala dan sebab:** `MejaSaham.exe --help` berjalan, tetapi GUI gagal memuat `PySide6.QtCore`
  dengan `ImportError: DLL load failed ... The specified procedure could not be found.` Uji
  minimal membuktikan masalah pada bundel PyInstaller. Build mewarisi `PATH` Codex yang berisi
  ICU 78 dari Poppler; DLL itu tidak cocok dengan simbol ICU yang diminta Qt.
- **Perbaikan:** `tools/build_exe.py` menjalankan PyInstaller dengan `PATH` terbatas ke direktori
  Windows, dan tanpa `QT_PLUGIN_PATH`/`QML2_IMPORT_PATH`. Uji regresi menjaga perilaku ini.
- **Verifikasi:** uji terarah 5 lulus; suite penuh **911 lulus (34,23 dtk)**; build baru keluar 0
  (EXE 15,5 MiB). Dengan `PATH` hanya direktori Windows, `--help` keluar 0 dan GUI bertahan
  8 detik; tidak ada galat pemuatan Qt DLL. Uji offscreen ini belum membuktikan klik-ganda di
  desktop pengguna.
- **Berikutnya:** coba klik-ganda `dist\MejaSaham\MejaSaham.exe`. Jika masih gagal, kirim teks
  pesan galat atau tangkapan layar. Untuk menjalankan dari terminal:
  `dist\MejaSaham\MejaSaham.exe`.
- **Berkas:** `tools/build_exe.py`, `tests/test_pengemasan.py`, `README.md`,
  `docs/arsitektur.md` (T83), dan `docs/lanjutan.md`.

### Perbaikan waktu revisi emiten saat impor (22 Okt 2026 — sesi 40)

- **Gejala:** impor EXE menolak revisi AADI pada `diketahui_pada='2026-10-22T00:00:00+07:00'`.
  Pemeriksaan CSV dan SQLite membuktikan bahwa satu baris AADI sudah ada pada cap waktu itu;
  `dicatat_pada` tanggal saja memang dikonversi menjadi tengah malam, jadi menunggu beberapa detik
  tidak menyelesaikan konflik ini.
- **Perbaikan:** `ingesti.simpan()` kini mengisi `diketahui_pada` emiten dari waktu jalan impor yang
  sama dengan baris lain. `dicatat_pada` tetap menjadi tanggal provenance pada CSV; tanggal sumber
  juga tetap ikut pada `sumber`. Jenis revisi berbeda tetap menambah baris, bukan menimpa.
- **Uji:** uji regresi baru gagal sebelum perbaikan dengan konflik tanggal yang sama, lalu lulus
  setelahnya. Uji terarah `test_ingesti.py`, `test_jenis_emiten.py`, dan `test_impor_berkas.py`:
  **152 lulus**. Suite penuh: **912 lulus**.
- **Bundel/data uji:** `tools/build_exe.py` keluar 0, menghasilkan EXE 15,5 MiB. Cadangan dibuat
  lebih dulu di `.uji-data/cadangan-sesi40/20261022T060043875163+0700`. EXE mengimpor folder uji ke
  snapshot 2 dengan **1.708 baris baru**, termasuk **735 baris fundamental**; AADI kini memiliki
  revisi `umum` pada `2026-10-22T06:00:50+07:00`, dan `PRAGMA integrity_check` = `ok`. `--saring`
  melaporkan 49 bank, 862 umum, 62 belum berjenis, dan **tidak ada kandidat** karena metrik belum
  tersedia/terhitung. Notasi khusus dan imbal hasil SUN belum ada pada folder uji.
- **Batas tahap:** tidak ada kandidat yang muncul; hasil ini bukan klaim kelengkapan fundamental
  atau status notasi. Tahap berhenti untuk tinjauan pengguna sesuai K4.
- **Berkas:** `mejasaham/ingesti.py`, `tests/test_ingesti.py`, `tests/test_jenis_emiten.py`,
  `docs/arsitektur.md` (T84), `docs/keputusan.md`, dan `docs/lanjutan.md`.
- **Cara menjalankan:** `python -m pytest`; `python tools/build_exe.py`; lalu
  `dist/MejaSaham/MejaSaham.exe --impor <folder-konfigurasi> --folder-data <folder-data>` dan
  `dist/MejaSaham/MejaSaham.exe --saring --folder-data <folder-data>`.

### Laporan mutu impor konfigurasi memakai sumber harga snapshot (22 Okt 2026 — sesi 41)

- **Gejala:** impor folder konfigurasi menghasilkan `bar terkini: 0` walau tabel harga berisi
  1.002.024 bar. `pengatur.jalankan_impor()` memberi `mutu.periksa()` label sumber folder impor;
  `mutu.periksa()` memakai label itu sebagai filter `WHERE sumber = ?`, sehingga laporan snapshot
  mengosongkan deret harga ketika labelnya `konfigurasi`.
- **Perbaikan:** laporan impor kini memilih sumber harga utama dari baris yang sudah diketahui
  pada waktu snapshot (`potret.sumber_utama(..., batas=tersimpan.diketahui_pada)`), sesuai K14.
  Impor yang membawa harga juga memakai aturan satu sumber yang sama; bila belum ada harga,
  laporan tetap melaporkan keadaan kosong.
- **Cakupan:** hanya pemilihan sumber untuk laporan mutu sesudah impor. Tidak ada perubahan data
  atau skema.
- **Verifikasi:** `python tools/build_exe.py` keluar 0 dan menghasilkan EXE 15,5 MiB. Pengguna
  menjalankan EXE pada folder uji: snapshot 4 melaporkan **1.002.024 bar masuk dan 1.002.024
  bar terkini**, membuktikan laporan mutu memilih sumber harga yang benar. Laporan juga menemukan
  **3 emiten kritis bermasalah** (BNBR, FORU, PACK), **9 temuan tak wajar**, dan mengeluarkan
  **8 emiten dari peringkat**; ini temuan mutu data yang terpisah dari perbaikan filter sumber.
  Pengguna menjalankan suite penuh: **912 lulus (33,28 dtk)**.
- **Berkas:** `mejasaham/pengatur.py`, `docs/keputusan.md`, `docs/lanjutan.md`.
- **Cara menjalankan verifikasi berikutnya:** `python -m pytest`. Untuk mengulang laporan mutu,
  jalankan EXE baru dengan `--impor <folder-konfigurasi> --folder-data <folder-data>`; impor
  berikutnya membuat snapshot baru.

### Tinjauan awal temuan mutu snapshot 4 (22 Okt 2026 — sesi 41)

- **BNBR:** di basis data, bar 13–15 Feb 2023 bernilai 3.800 dengan volume 0; 16 Feb nilainya 71
  dengan volume 26.365.600. Tidak ada aksi korporasi tersimpan di sekitar tanggal itu. Nilai lama
  tidak dianggap harga transaksi yang terverifikasi; verifikasi seri resmi masih terbuka.
- **FORU:** basis data memuat penutupan 238 dan volume 85.346.954 pada 14 Sep 2026, sementara laman
  informasi saham emiten menyatakan penutupan 4.650 dan volume 4.375.800 pada tanggal yang sama.
  KSEI mencatat cum HMETD 21 Sep dan tanggal pencatatan 23 Sep; perbedaan harga 14 Sep ini tidak
  dijelaskan sebagai ex-date HMETD. Bar Yahoo yang ada tidak boleh dianggap harga pasar terverifikasi.
- **PACK:** penurunan 3.280 → 272 pada 12 Jan 2026 bertepatan dengan ex-date HMETD. Jadwal resmi
  KSEI menyatakan rasio 5 saham lama : 102 HMETD untuk OWK dengan harga pelaksanaan Rp100. Namun
  aksi itu belum ada pada tabel `aksi_korporasi`, sehingga laporan mutu menamakannya lonjakan tanpa
  aksi. Ini belum mengesahkan harga Yahoo ataupun menghitung harga teoretis.
- **Batas tinjauan:** temuan COCO, FISH, PYFA, SCCO, dan TMAS belum direkonsiliasi. Tidak ada
  koreksi data atau impor yang dilakukan; data tetap append-only dan perlu bukti resmi untuk revisi.
- **Sumber primer:** [informasi saham FORU](https://www.dev.foru.co.id/investor-room/stock-information),
  [jadwal HMETD FORU di KSEI](https://web.ksei.co.id/services/registered-securities/shares/lc/FORU?setLocale=id-ID),
  [jadwal HMETD/OWK PACK di KSEI](https://web.ksei.co.id/Announcement/Files/189409_ksei_0064_dir_00126_202601051727.pdf).
- **Langkah berikutnya:** verifikasi riwayat harga BNBR dan FORU dari sumber bursa/emiten, lalu
  lengkapi aksi korporasi resmi PACK tanpa menebak penyesuaian; setelah tinjauan itu, lanjutkan
  lima kode lainnya.

### Rekonsiliasi awal delapan emiten temuan mutu snapshot 4 (22 Okt 2026 — sesi 42)

- **Ruang lingkup:** pembacaan laporan `snapshot-4` di `.uji-data/mejasaham-exe/arsip-snapshot/2026-10-21/` dan pencocokan ke sumber resmi emiten/KSEI yang tersedia. Tidak ada impor, koreksi, atau perubahan basis data.
- **BNBR — belum terverifikasi.** Bar 13–15 Feb 2023 sebesar Rp3.800 memiliki volume 0; 16 Feb beralih ke Rp71 dengan volume 26.365.600. Ini tidak membuktikan Rp3.800 sebagai transaksi; riwayat resmi harian yang dapat mengonfirmasi harga tersebut belum ditemukan. Tetap keluarkan dari peringkat sampai seri IDX/emiten dapat dicocokkan.
- **FORU — konflik harga vendor terkonfirmasi, penyebab belum.** Laman informasi saham emiten mencatat 14 Sep 2026 close Rp4.650 dan volume 4.375.800; snapshot Yahoo menyimpan close Rp238 dan volume 85.346.954 pada tanggal sama. KSEI mencatat cum HMETD 21 Sep dan pencatatan 23 Sep. Selisih tanggal/harga ini tidak dapat dijelaskan oleh jadwal tersebut; jangan memperbaiki bar Yahoo dengan angka laman emiten tanpa memperoleh seri resmi lengkap dan memahami basis datanya.
- **PACK — aksi resmi terkonfirmasi, koreksi harga belum.** Pengumuman KSEI mengonfirmasi ex-HMETD 12 Jan 2026, rasio 5 saham lama : 102 HMETD untuk OWK, dan harga pelaksanaan Rp100. Ini cukup untuk mencatat aksi dengan atribut sesuai dokumen, tetapi tidak menetapkan harga teoretis maupun membuktikan close Yahoo Rp272 benar. Tidak ada angka hasil penyesuaian yang dihitung.
- **COCO — tidak ada aksi penjelas yang ditemukan.** KSEI saat ini memuat right distribution COCO pada Juli 2026, bukan aksi pada 30 Sep 2025. Laporan issuer KSEI mencatat status aktif, namun itu tidak menjelaskan lonjakan snapshot 500 → 158. Status/jadwal suspensi dan seri harga September 2025 perlu dicocokkan ke pengumuman IDX sebelum menyimpulkan salah data.
- **FISH — stock split resmi, tetapi tanggal anomali tidak cocok.** KSEI mengonfirmasi rasio 1:10 dengan perdagangan nominal baru mulai 9 Sep 2025; laporan mutu menandai penurunan 10x pada 1 Sep (10350 → 1035), sebelum tanggal efektif. Aksi split tidak cukup untuk membenarkan tanggal bar; perlu seri resmi sekitar 1–11 Sep.
- **PYFA — aksi PMHMETD resmi tidak cocok dengan tanggal anomali.** Prospektus emiten menyebut cum HMETD 19 Apr dan ex HMETD 22 Apr 2024, sedangkan penurunan 1040 → 203 terjadi 16 Apr. Itu bukan tanggal ex yang tercantum. Periksa seri resmi sebelum menempelkan aksi atau mengoreksi harga.
- **SCCO — stock split resmi, tanggal anomali mendahului jadwal.** Keterbukaan emiten menyebut rasio 1:4, akhir perdagangan nominal lama 7 Mar 2024, dan mulai nominal baru 8 Mar. Laporan mutu menandai 9975 → 2493 pada 1 Feb, lebih dari sebulan sebelumnya. Split tidak menjelaskan tanggal tersebut tanpa bukti tentang basis historis vendor.
- **TMAS — split resmi bertepatan, tetapi bar terindikasi tercampur basis.** Pengumuman jadwal menyebut rasio 1:10 dan perdagangan nominal baru mulai 23 Mei 2023. Snapshot menunjukkan 298 → 43 pada 23 Mei lalu 43 → 286 pada 24 Mei; dua bar itu ditandai sudah disesuaikan sumber, sehingga tidak konsisten terhadap rasio maupun harga perdagangan baru. Minta seri resmi harian sebelum koreksi.
- **Bukti sumber primer:** [informasi saham FORU](https://www.dev.foru.co.id/investor-room/stock-information), [KSEI FORU](https://web.ksei.co.id/services/registered-securities/shares/lc/FORU?setLocale=id-ID), [pengumuman KSEI PACK](https://web.ksei.co.id/Announcement/Files/189409_ksei_0064_dir_00126_202601051727.pdf), [prospektus PYFA](https://www.pyfa.co.id/wp-content/uploads/2024/04/PYFA-Prospektus-PMHMETD-I.pdf), [KSEI FISH](https://web.ksei.co.id/services/registered-securities/shares/lc/FISH?setLocale=id-ID), [keterbukaan SCCO](https://www.indopremier.com/xdir/news/stock_split/2024_ss_q1_scco.pdf), [jadwal TMAS](https://www.indopremier.com/ipotnews/newsDetail.php?group_news=RESEARCHNEWS&halaman=1&jdl=Stock_Split_TMAS_Mei_2023&name=&news_id=420692&q=Stock+Split&search=y_general&taging_subtype=COMPANYUPDATE), [KSEI COCO](https://web.ksei.co.id/services/registered-securities/shares/lc/COCO?setLocale=id-ID).
- **Kesimpulan tahap:** hanya aksi PACK dapat disiapkan untuk pencatatan dari bukti yang ditemukan; harga semua bar tetap memerlukan verifikasi terpisah. Tidak mengubah basis data. Tidak menjalankan tes karena tahap ini tinjauan bukti/dokumen. Tahap berhenti untuk tinjauan sesuai K4.
- **Belum dikerjakan / berikutnya:** ambil dan cocokkan seri resmi harian BNBR, FORU, COCO, FISH, PYFA, SCCO, TMAS; untuk PACK siapkan baris aksi append-only dengan kutipan/atribut lengkap tanpa menghitung harga penyesuaian. Sesudah ada bukti/draf yang bisa ditinjau, berhenti sebelum impor.
- **Cara menjalankan pemeriksaan ulang:** buka `laporan-mutu.csv` snapshot 4 di atas; bandingkan hari anomali ke pengumuman dan seri harga IDX/emiten. Jangan gunakan Yahoo sebagai bukti primer.

### Pemeriksaan lanjutan seri harga dan draf aksi PACK (22 Okt 2026 — sesi 43)

- Pemeriksaan menemukan endpoint perdagangan harian pada domain IDX (`/primary/TradingSummary/GetStockSummary?date=YYYYMMDD`), tetapi web reader tidak dapat membukanya dan permintaan langsung mendapat HTTP 403. Karena itu tidak ada seri harian IDX yang dapat dicocokkan untuk BNBR, COCO, FISH, PYFA, SCCO, dan TMAS. Halaman Ringkasan Saham IDX yang tersedia menampilkan ringkasan terkini, bukan arsip per tanggal.
- **FORU saja terverifikasi untuk satu tanggal:** laman issuer menyatakan data bersumber dari IDX dan menampilkan 14 Sep 2026 low 4.330, high/open/close 4.650, volume 4.375.800. Ini memastikan konflik dengan bar vendor pada tanggal tersebut, tetapi belum menjelaskan bagaimana vendor membentuk seri atau mengizinkan koreksi harga historis.
- **TMAS:** sumber sekunder yang mengutip pengumuman BEI menyebut harga teoritis 23 Mei 2023 Rp298 dan split 1:10; tidak ada OHLC lengkap 23–24 Mei dari sumber primer. Ini belum cukup untuk menguji dua bar vendor.
- Draf satu baris PACK disiapkan di `docs/draf-aksi-korporasi-PACK-2026-10.csv`: ex-date 12 Jan 2026, rasio HMETD 5:102, harga Rp100 per unit OWK, tenggat kosong. Keterangan membedakan HMETD/OWK dari saham biasa. **Jangan impor sebelum peninjauan semantik klasifikasi dan rasio**; tidak ada harga teoretis yang dihitung.
- Catatan bukti/sumber: `docs/riset-harga-snapshot4-2026-10.md`. Tidak ada impor atau perubahan basis data. Tes tidak dijalankan karena tahap hanya pemeriksaan sumber dan dokumentasi.
- **Belum dikerjakan:** mendapatkan seri resmi harian enam ticker yang belum terverifikasi; meminta/memperoleh akses IDX yang diizinkan bila endpoint tetap 403; meninjau draf aksi PACK sebelum mempertimbangkan impor.
- **Cara mengulang:** buka tautan issuer FORU dan dokumen KSEI PACK pada catatan riset; uji endpoint IDX dengan tanggal `YYYYMMDD` ketika akses berwenang tersedia; bandingkan OHLCV tanggal temuan ke snapshot 4. Tidak ada perintah tes relevan.
- **Tahap berhenti untuk tinjauan pengguna sesuai K4.**

### Tinjauan sumber tambahan draf PACK (22 Okt 2026 — sesi 44)

- KSEI mengonfirmasi rincian rasio pada draf: 5 saham mendapat 102 HMETD; setiap HMETD membeli 1 OWK seharga Rp100; rasio konversi OWK ke saham 1:1. Tidak ada harga teoretis yang dihitung.
- **Tenggat belum dapat dipastikan.** Jadwal KSEI KSEI-0064/DIR/00126 mencantumkan tanggal pelaksanaan HMETD 22 Jan 2026, sedangkan surat KSEI KSEI-1626/JKU/0126 bertanggal 23 Jan memberi contoh pemegang melaksanakan HMETD pada 26 Jan. Karena `tenggat` dalam skema berarti batas akhir pelaksanaan, draf dibiarkan kosong sampai ada klarifikasi issuer/BAE/KSEI atau dokumen operasional yang menyelesaikan selisih itu. Draf tidak diimpor.
- KSEI Price History untuk COCO, FISH, SCCO, TMAS terbuka tetapi cuplikan yang ditampilkan tidak mencakup tanggal anomali; BNBR menghasilkan HTTP 500 dan PYFA timeout. Halaman-halaman tersebut belum memberikan OHLCV historis yang dibutuhkan. Ini bukan bukti bahwa arsip lain tidak tersedia.
- Catatan rinci dan tautan primer: `docs/riset-harga-snapshot4-2026-10.md` bagian “Pemeriksaan tambahan saat tinjauan draf”. Tidak ada perubahan harga atau basis data; tes tidak dijalankan karena tahap tinjauan sumber/dokumen.
- **Tahap berhenti sesuai K4.** Berikutnya: dapatkan klarifikasi deadline PACK sebelum melengkapi draf; minta akses arsip OHLCV IDX yang diizinkan atau sumber historis issuer untuk enam ticker yang belum terverifikasi. Setelah data harga didapat, cocokkan tanggal temuan ke OHLCV sebelum menyimpulkan atau mengoreksi.
- **Cara menjalankan ulang:** buka tiga pengumuman KSEI PACK yang tertaut dalam catatan riset dan halaman Price History KSEI per kode; untuk seri harga, gunakan akses arsip resmi yang diizinkan. Tidak ada perintah tes relevan.

### Klarifikasi tenggat PACK (22 Okt 2026 — sesi 45)

- Jadwal KSEI No. KSEI-0064/DIR/00126 menunjukkan **22 Jan 2026 sebagai Tanggal Pelaksanaan HMETD**. Tanggal 26 Jan dalam jadwal adalah distribusi OWK atas pelaksanaan HMETD (serta penjatahan pesanan tambahan), bukan tanggal pelaksanaan yang diperpanjang.
- Surat KSEI No. KSEI-1626/JKU/0126 (23 Jan) memberi ilustrasi pemegang yang memiliki HMETD dan akan melaksanakannya; surat itu menjelaskan hak 1 HMETD membeli 1 OWK Rp100 yang dapat dikonversi 1:1, tetapi tidak menetapkan 26 Jan sebagai tanggal pelaksanaan.
- Draf `docs/draf-aksi-korporasi-PACK-2026-10.csv` diperbarui dengan `tenggat=2026-01-22`, sesuai jadwal dan definisi field pada `docs/skema-data.md` §5.14. Draf **belum diimpor**; kecocokan semantik jenis `right_issue` untuk HMETD OWK tetap perlu ditinjau sebelum impor. Tidak ada harga teoretis.
- Tidak ada perubahan basis data. Tes tidak dijalankan (pemeriksaan dokumen). Rincian dan tautan primer ada di `docs/riset-harga-snapshot4-2026-10.md`, bagian “Klarifikasi tenggat PACK”. Tahap berhenti untuk tinjauan sesuai K4.

### Tinjauan semantik draf aksi PACK (22 Okt 2026 — sesi 46)

- **Klasifikasi aksi:** HMETD PACK 5:102 dapat dicatat sebagai `right_issue`. POJK HMETD mendefinisikan hak itu mencakup pembelian saham dan/atau efek ekuitas lain yang dapat dikonversi menjadi saham; dokumen KSEI PACK menyebut setiap HMETD membeli satu OWK yang dikonversi 1:1 menjadi saham. Dengan demikian `rasio_lama=5`, `rasio_baru=102` berarti 5 saham lama memperoleh 102 HMETD, bukan rasio konversi OWK.
- **Harga tebus:** `100` adalah harga per unit OWK sesuai dokumen KSEI, bukan harga per saham dan bukan masukan TERP. Draf menjelaskannya di komentar dan `keterangan`.
- **Batas dukungan produk:** model `keputusan_right_issue` hanya mendukung keputusan tebus yang menunjuk `id_transaksi` saham, jual HMETD, atau abaikan. Tidak ada model posisi untuk kepemilikan OWK atau konversinya. Karena itu draf dapat mendokumentasikan aksi untuk menilai kejadian harga, tetapi belum boleh diimpor sebagai aksi operasional posisi PACK sampai cakupan OWK diputuskan. Ini bukan pengesahan TERP atau harga vendor.
- **Keputusan tahap:** pertahankan CSV sebagai draf; jangan impor dan jangan pindahkan ke konfigurasi. Langkah berikutnya adalah putuskan cakupan OWK pada posisi (tambah dukungan instrumen OWK atau batasi pencatatan PACK untuk mutu harga), baru nilai jalur impor. Enam ticker BNBR, COCO, FISH, PYFA, SCCO, TMAS tetap menunggu OHLCV primer.
- **Verifikasi:** tes tidak dijalankan; pemeriksaan dokumen dan kode saja. Tidak ada perubahan basis data. Sumber primer: POJK HMETD OJK (definisi HMETD mencakup efek ekuitas yang dapat dikonversi) dan jadwal KSEI PACK yang dirujuk pada `docs/riset-harga-snapshot4-2026-10.md`.
- **Cara mengulang:** telaah `docs/draf-aksi-korporasi-PACK-2026-10.csv`, `docs/skema-data.md` §5.14, `mejasaham/posisi.py` (keputusan right issue), serta dokumen KSEI/OJK pada catatan riset. Tidak ada perintah tes relevan.

### Keputusan cakupan OWK PACK (22 Okt 2026 — sesi 47)

- **Keputusan pengguna (K90):** sesuai rekomendasi, v0.1 hanya mencatat PACK untuk mutu harga; kepemilikan OWK dan konversinya menjadi saham ditunda ke tahap terpisah.
- **Batas implementasi saat ini:** jangan impor draf sebagai `right_issue` operasional posisi. `posisi.hak_right_issue()` menafsirkan rasio sebagai jumlah HMETD saham dan keputusan `tebus` harus menunjuk transaksi pembelian saham; model tidak memiliki instrumen OWK. Jenis aksi dapat diterima untuk mendokumentasikan HMETD menurut bukti OJK/KSEI, tetapi perilaku posisi saat ini tidak sesuai.
- **Langkah berikutnya:** rancang representasi aksi untuk laporan mutu harga yang tidak memunculkan hak/tindakan posisi atau penyesuaian harga yang belum terverifikasi; tinjau rancangan sebelum impor. Harga teoretis dan kebenaran bar vendor tetap belum diputuskan. Enam ticker BNBR, COCO, FISH, PYFA, SCCO, TMAS masih menunggu OHLCV primer.
- **Tahap berhenti sesuai K4.** Tes tidak dijalankan (pencatatan keputusan/dokumen); tidak ada kode atau basis data diubah.
- **Cara mengulang:** baca K90, `docs/skema-data.md` §5.14, `mejasaham/posisi.py` (`hak_right_issue`, `catat_keputusan_right_issue`) dan `mejasaham/penyesuaian.py` (`JENIS_BELUM_DITERAPKAN`). Tidak ada perintah tes relevan.

### Rancangan mutu harga PACK (22 Okt 2026 — sesi 48; menunggu tinjauan)

- Melanjutkan K90: usulan memakai tabel/berkas catatan aksi khusus mutu yang terpisah dari `aksi_korporasi` operasional. Catatan hanya memberi konteks bersumber pada laporan mutu; tidak menjadi input posisi, tindakan HMETD, penyesuaian harga, TERP, atau dasbor tindakan.
- Untuk lonjakan yang berdekatan dengan catatan aksi, usulan mempertahankan temuan lonjakan belum terverifikasi dan menambahkan catatan konteks dengan sumber. Peristiwa korporasi tidak membuktikan OHLCV vendor benar.
- Draf `docs/draf-aksi-korporasi-PACK-2026-10.csv` tetap tidak untuk diimpor; jika rancangan disetujui, buat berkas mutu tersendiri dengan tanggal/angka/satuan persis menurut KSEI dan provenance point-in-time.
- Belum diputuskan: skema/kunci final, format impor, tampilan, dan implementasi. Tidak ada kode, basis data, atau tes berubah/dijalankan. Tahap dihentikan untuk tinjauan K4. Rancangan rinci ada di `docs/riset-harga-snapshot4-2026-10.md`, bagian “Usulan rancangan terpisah untuk mutu harga PACK”.

### Implementasi catatan aksi mutu (22 Okt 2026 — sesi 49)

- Pengguna melanjutkan rancangan sesi 48. Migrasi 016 menambah `catatan_aksi_mutu`, view revisi terkini, dan trigger append-only; berkas `catatan-aksi-mutu.csv` memakai parser/jalur impor terpisah dari `aksi-korporasi.csv`.
- Laporan mutu membaca catatan yang sudah diketahui pada tanggal laporan. Bila lonjakan berdekatan lima hari, ia menambahkan temuan `konteks_aksi_mutu` berstatus CATATAN dan sumbernya; temuan lonjakan `tak_wajar` tetap dipertahankan. Catatan ini tidak dibaca posisi/penyesuaian dan tidak menghitung TERP.
- Baris PACK disiapkan di `docs/draf-catatan-aksi-mutu-PACK-2026-10.csv` dari pengumuman KSEI yang dirujuk dalam catatan riset. **Belum diimpor ke basis data runtime**; tinjau baris dan hasil tes sebelum tahap impor berikutnya. Enam seri OHLCV yang tertunda tetap belum terverifikasi.
- Verifikasi akhir: `.\.venv\Scripts\python -m pytest` → **914 lulus** (48,53 dtk). Tidak ada perubahan basis data runtime; migrasi hanya diuji pada basis data sementara. Rincian skema ada di `docs/skema-data.md` §5.17 dan keputusan teknis di `docs/arsitektur.md`.
- Tahap berhenti sesuai K4 sebelum impor runtime. Cara menjalankan ulang verifikasi: `.\.venv\Scripts\python -m pytest`.

### Impor catatan aksi mutu PACK (22 Okt 2026 — sesi 50)

- **Tinjauan dan keputusan:** baris draf `catatan_aksi_mutu` mencatat PACK, tanggal efektif 12 Jan 2026, instrumen “HMETD untuk OWK”, ringkasan rasio/instrumen sesuai dokumen, URL KSEI, dan identitas pengumuman. Impor melalui `catatan-aksi-mutu.csv`, bukan `aksi-korporasi.csv`; tidak memengaruhi posisi, TERP, atau harga.
- **Cadangan dan hasil:** cadangan dibuat sebelum impor di `.uji-data/cadangan-sesi49/20261022T111553703187+0700`. Impor ke basis data kerja `.uji-data/mejasaham` selesai dengan kode keluar 0, membuat snapshot 14 (tanggal data 11 Okt 2026) dan menambah 1 baris. Laporan mutu mencatat 5 konteks aksi dan tetap menyimpan 9 temuan tak wajar; 916 emiten tetap dikeluarkan dari peringkat karena kekosongan data.
- **Verifikasi:** `PRAGMA integrity_check` → `ok`; view `v_catatan_aksi_mutu_terkini` memuat satu catatan PACK dengan `diketahui_pada=2026-10-22T11:15:59+07:00` dan sumber `KSEI-0064/DIR/00126 (5 Jan 2026)`. Suite tes tidak dijalankan pada tahap impor; sesi 49 melaporkan 914 lulus (48,53 dtk).
- **Belum dikerjakan:** OHLCV primer untuk BNBR, COCO, FISH, PYFA, SCCO, dan TMAS masih belum cocok; catatan konteks tidak membuktikan bar vendor benar. Tidak ada klaim bahwa peringkat layak dipakai.
- **Cara menjalankan ulang:** cadangan: `python -m mejasaham --buat-cadangan --folder-data .uji-data/mejasaham --folder-cadangan .uji-data/cadangan-sesi49`; impor: `python -m mejasaham --impor <folder-berisi-catatan-aksi-mutu.csv> --folder-data .uji-data/mejasaham`; integritas: `PRAGMA integrity_check` pada `.uji-data/mejasaham/mejasaham.db`.

### Verifikasi kanal OHLCV primer enam kode (22 Okt 2026 — sesi 51)

- **Tanggal sasaran dari arsip mutu snapshot 4:** BNBR 16 Feb 2023 (bar 13–15 Feb sebelumnya 3.800, lalu 71); COCO 30 Sep 2025 (500 → 158); FISH 1 Sep 2025 (10.350 → 1.035); PYFA 16 Apr 2024 (1.040 → 203); SCCO 1 Feb 2024 (9.975 → 2.493); TMAS 23–24 Mei 2023 (298 → 43 → 286). Nilai ini adalah yang tersimpan pada snapshot, bukan harga primer yang sudah disahkan.
- **Kanal resmi yang diverifikasi:** FAQ IDX menyebut EoD tersedia pada halaman Ringkasan Saham; untuk akses EoD melalui SIPD, pelanggan berlisensi memakai user ID/password. FAQ juga menyatakan format data pelanggan Excel/DBF. Halaman Ringkasan Saham menjelaskan kolom OHLC dan volume untuk perdagangan, tetapi tampilan yang dapat dijangkau pada sesi ini adalah data terkini. Tabel statistik harga saham bulanan IDX menampilkan statistik bulanan, bukan seri OHLCV harian. Pembukaan halaman tabel gagal HTTP 403; permintaan endpoint harian IDX yang dicatat sesi 43 juga gagal 403.
- **Hasil tahap:** tidak memperoleh seri OHLCV harian primer untuk keenam tanggal. Tidak ada data baru yang diimpor atau koreksi harga dibuat. Tes tidak dijalankan karena pemeriksaan kanal/sumber.
- **Belum dikerjakan:** pencocokan setiap hari target dengan arsip EoD resmi. Jalur praktis yang teridentifikasi adalah ekspor resmi dari portal SIPD/licensee atau arsip berlisensi yang disediakan IDX; jangan menggantinya dengan Yahoo atau statistik bulanan.
- **Sumber primer:** [FAQ IDX Data Services](https://data.idx.co.id/faq.php?p=sFWjtRbH1z2wag4), [Ringkasan Saham IDX](https://idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/), [katalog produk IDX Data](https://data.idx.co.id/catalog_product2.php?p=XLoi5RtfUJ8SBrm), [Tabel Statistik Harga Saham bulanan IDX](https://www.idx.id/en/market-data/statistical-reports/digital-statistic/monthly/trading-summary/table-of-stock-price).
- **Empat laporan akhir tahap:** tes: tidak dijalankan; ringkasan: tanggal anomali dipatok ulang dan kanal EoD resmi diverifikasi; belum: enam seri OHLCV harian; cara menjalankan ulang: buka FAQ dan halaman IDX tertaut, lalu bandingkan arsip OHLCV tanggal target dengan `harga.csv` snapshot 4. Tahap berhenti sesuai K4.

### Penelusuran jalur arsip OHLCV berizin (22 Okt 2026 — sesi 52)

- **Bukti tambahan resmi:** FAQ IDX Data Services menyatakan produk IDX mencakup data *Historical* dan EoD tersedia melalui SIPD untuk pelanggan berlisensi menggunakan user ID/password. FAQ juga menyebut format EoD Excel dan DBF; format TXT tidak lagi disediakan demi keamanan data. Katalog IDX Data memuat produk `IDX Equity EoD Professional` dengan field Previous, High, Low, Close, Volume, Value, Freq, Weight, Best Bid, dan Best Offer.
- **Kesimpulan terbatas:** kanal produk resmi mendukung permintaan arsip EoD/bersejarah dengan OHLCV, tetapi halaman publik tidak memberi unduhan arsip tanggal target dan bukti publik tidak memastikan rentang historis yang tersedia atau syarat hak pakai untuk MejaSaham. Tidak ada enam seri harian yang diperoleh atau dicocokkan pada sesi ini.
- **Tindakan:** tidak mengakses akun/licensee, menghubungi IDX/TICMI, mengunduh data berbayar, mengimpor, atau mengoreksi harga. Tahap berikutnya bergantung pada tersedianya ekspor resmi berizin dari pengguna atau kanal yang memang dapat diakses. Bila tersedia, cocokkan BNBR 16 Feb 2023; COCO 30 Sep 2025; FISH 1 Sep 2025; PYFA 16 Apr 2024; SCCO 1 Feb 2024; TMAS 23–24 Mei 2023 terhadap `harga.csv` snapshot 4. Jangan gunakan Yahoo atau statistik bulanan sebagai pengganti.
- **Tes:** tidak dijalankan karena tahap pemeriksaan sumber/dokumen. Tidak ada perubahan basis data atau harga.
- **Sumber primer:** [FAQ IDX Data Services](https://data.idx.co.id/faq.php?p=sFWjtRbH1z2wag4) dan [katalog produk IDX Data](https://data.idx.co.id/catalog_product2.php?p=XLoi5RtfUJ8SBrm).
- **Empat laporan akhir tahap:** tes: tidak dijalankan; ringkasan: jalur produk historis/EoD berlisensi dan field OHLCV dikonfirmasi dari sumber IDX; belum: ekspor dan pencocokan enam seri harian; cara menjalankan ulang: setelah menerima ekspor resmi berizin, bandingkan keenam tanggal di atas dengan `harga.csv` snapshot 4. Tahap berhenti sesuai K4.

### Pencarian arsip harian publik untuk tanggal sasaran (22 Okt 2026 — sesi 53)

- **Pemeriksaan:** pencarian web untuk enam ticker/tanggal dan arsip harian publik tidak menemukan halaman atau dokumen primer IDX yang memuat bar OHLCV tanggal sasaran. Hasil yang muncul antara lain layanan/vendor pihak ketiga dan hasil pencarian yang tidak terkait; semuanya dikesampingkan sebagai bukti harga.
- **Hasil:** tidak ada seri OHLCV primer tambahan yang diperoleh. Endpoint ringkasan perdagangan harian IDX yang telah dicoba sesi 43 tetap terhalang HTTP 403; jalur terverifikasi tetap ekspor EoD/historis berizin dari IDX, bukan pengganti publik yang belum disahkan.
- **Belum dikerjakan:** pencocokan BNBR 16 Feb 2023; COCO 30 Sep 2025; FISH 1 Sep 2025; PYFA 16 Apr 2024; SCCO 1 Feb 2024; TMAS 23–24 Mei 2023. Tidak ada impor atau koreksi harga. Tes tidak dijalankan karena pemeriksaan sumber.
- **Empat laporan akhir tahap:** tes: tidak dijalankan; ringkasan: pencarian publik tidak menghasilkan sumber primer untuk tanggal target; belum: enam seri harian; cara menjalankan ulang: bandingkan ekspor resmi berizin dengan `harga.csv` snapshot 4 jika ekspor tersedia. Tahap berhenti sesuai K4.

### Penelusuran TICMIDATA Pay Per Use (22 Okt 2026 — sesi 54)

- **Sumber:** katalog `Data Transaksi Harian Saham` di [TICMIDATA Pay Per Use](https://ticmidata.co.id/pay_per_use) menyebut kolom Open, High, Low, Previous, Close, Volume, Value, dan Frequency. TICMI juga menjelaskan akses historis dan skema Pay Per Use di [situs TICMIDATA](https://ticmidata.co.id/) serta autentikasi API berbasis perjanjian di [dokumentasi API](https://doc-api.ticmidata.co.id/). Pemeriksaan dilakukan pada pratinjau interaktif, 22 Okt 2026; tidak masuk akun, keranjang, pembayaran, atau mengunduh ekspor.
- **Nilai pratinjau yang didapat:** BNBR 13–16 Feb 2023; COCO 30 Sep 2025; PYFA 16 Apr 2024; SCCO 1 Feb 2024; TMAS 23–24 Mei 2023. Rincian OHLCV langsung ditampilkan pada catatan riset. Nilai ini mengungkap beda dengan arsip snapshot 4 untuk beberapa bar, jadi bukan alasan untuk menimpa harga. FISH 1 Sep 2025 hanya menampilkan Previous/Close 1.035; Open/High/Low/Volume/Value/Frequency tidak tersedia pada tanggal itu, sehingga anomali belum bisa diverifikasi penuh.
- **Perhatian hak pakai:** nilai dilihat di Preview pay-per-use, bukan data yang sudah dibeli/diekspor. Sebelum memasukkan data ke aplikasi atau mendistribusikannya, pastikan lisensi/hak pakai dan dapatkan berkas ekspor resmi dengan provenance. Tidak ada komunikasi ke TICMI/IDX, pembelian, impor, koreksi harga, atau perubahan basis data.
- **Test:** tidak dijalankan karena ini pemeriksaan sumber. **Ringkasan:** jalur TICMI yang menyediakan kolom transaksi harian ditemukan dan lima ticker memiliki bar target pada pratinjau; FISH hanya parsial. **Belum:** konfirmasi hak pakai/ekspor dan pencocokan berlisensi; investigasi basis harga PYFA serta konflik BNBR dan COCO. **Cara menjalankan ulang:** buka Pay Per Use, pilih `Data Transaksi Harian Saham`, ticker serta tanggal yang dirujuk di `docs/riset-harga-snapshot4-2026-10.md`, lalu tekan Preview. Tahap berhenti sesuai K4 untuk tinjauan.

### Pembersihan ruang repositori (27 Okt 2026 — di luar sesi)

- **Permintaan:** pengguna — "hapus file yang ga digunain dong, besar sekali sampai 10 gb". Ukuran awal yang sempat kulaporkan (4,97 GB) **tidak sah**: beberapa folder `.uji-data` tidak terbaca karena ACL sisa sandbox. Rekonstruksi dari hasil ukur: **≈10,4 GB** (2,56 GB sisa + 4,92 GB tahap dua + 2,10 GB tahap satu + 0,09 GB `__pycache__` + 0,77 GB `.tmp/py313`) — perkiraan pengguna "sampai 10 GB" tepat. Sesudah pembersihan: **2,56 GB**, jadi sekitar 7,9 GB berkas hilang, ±7,1 GB di antaranya ruang nyata.
- **Dihapus (semua gitignored dan dapat dibuat ulang):** `.uji-data/mejasaham-exe` 823 MB · `.uji-data/uji-tahap5/salinan` + `salinan-aplikasi` 422 MB · `.uji-data/uji-k61/mejasaham.db` 236 MB · `.uji-data/uji-k61-cadangan` 227 MB · `.tmp/candidate-dist` + `.tmp/candidate-build` 233 MB · `build/` 51 MB · `dist/` 183 MB · `.tmp/py313` 769 MB · `__pycache__` (528 folder) 91 MB · `.uji-data/mejasaham-cadangan/{20261016T175015415236,20261019T181212314095,20261019T182735608155}` 2,60 GB · `.uji-data/cadangan-sesi49/20261022T111550896890+0700` 820 MB · `.uji-data/cadangan-sesi40` 368 MB · `.uji-data/mejasaham-exe-cadangan` 368 MB · `pytest-of-PENGGUNA` 271 MB · `.uji-data/mejasaham.db` 229 MB · `.uji-data/arsip-snapshot` 147 MB · cache uv 1,01 GB (`uv cache clean`).
- **Tetap:** `.uji-data/mejasaham` (basis data kerja + `arsip-snapshot/2026-10-11`), `.uji-data/cadangan-sesi49/20261022T111553703187+0700` (cadangan terakhir sebelum impor sesi 50 — satu-satunya titik balik yang disimpan), `riset-idx`, seluruh berkas bukti kecil (`.txt`, `.csv`, `.png`), dan `.venv` (787 MB, dipakai `pytest`).
- **Kejadian yang perlu diketahui sesi berikutnya:** (a) sandbox `workspace-write` berjalan pada integritas Low dan **menolak** menghapus berkas `.tmp/py313` yang di-hardlink dari cache uv ("Access to the path is denied"); sesudah mode akses penuh, penghapusan berhasil — jangan menyimpulkan proteksi berkas dari penolakan itu. (b) `.tmp/py313` ternyata **hardlink** ke cache uv: menghapusnya hanya membebaskan 1,8 MB ruang nyata; `uv cache prune` tidak menemukan entri tak terpakai, baru `uv cache clean` mengembalikan 960 MB (py313 dibangun ulang perlu unduh ulang lewat `uv`). (c) `dist/` dihapus atas pilihan pengguna → `MejaSaham.exe` **tidak ada** sampai `tools\build_exe.py` dijalankan lagi. (d) `.uji-data/mejasaham.db` (salinan bersih tanpa arsip) hilang; perintah di `docs/lanjutan.md` bagian 3 yang memakainya harus memakai salinan `.uji-data/mejasaham` atau `--buat-cadangan`.
- **Empat laporan akhir tahap:** **tes:** `.\.venv\Scripts\python -m pytest` → **914 lulus (163,62 dtk)**; **ringkasan:** pembersihan ruang ≈7,9 GB berkas (≈10,4 → 2,56 GB) tanpa menyentuh basis data kerja, kode, atau uji; **belum:** membangun ulang `dist/` bila EXE dibutuhkan lagi, dan memindahkan rujukan bukti yang menunjuk cadangan 16/19 Okt yang sudah dihapus; **cara menjalankan:** hapus per kelompok dengan jalur absolut (bukan pola lebar), lalu ukur dengan `Get-ChildItem -Recurse -Force | Measure-Object Length -Sum`. Tahap berhenti sesuai K4.
