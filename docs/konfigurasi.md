# Konfigurasi & Parameter Meja Saham

Status: **kerangka untuk isinya, sudah jalan untuk bentuknya.** Semua angka di berkas ini
adalah **nilai awal yang bisa diubah, bukan kebenaran pasar** (PRD catatan pembacaan).
Pemuatnya sudah ada: `mejasaham/konfigurasi.py` + tabel parameter bertanggal (migrasi 002) —
lihat bagian 6. Yang belum ada isinya tetap parameter bursa B1–B9 di bagian 2.

Bentuk berkasnya sudah diputuskan (K6 di `docs/keputusan.md`): parameter bursa di bawah
diisi di TOML, dengan template di
[`mejasaham/defaults/parameter-bursa.contoh.toml`](../mejasaham/defaults/parameter-bursa.contoh.toml).
Template itu sengaja berada **di dalam paket**, bukan di akar repo: AC-12 menuntut aplikasi
kembali ke konfigurasi bawaan setelah isi folder data dihapus, dan itu tidak mungkin kalau
bawaannya tidak ikut dibundel. Preset saringan, bobot faktor, dan batas risiko **tidak** di
TOML — itu baris berversi di basis data.

**Cara menyatakan "belum terverifikasi":** di dokumen ini `[PERLU VERIFIKASI]`; di berkas
TOML, entri itu **tidak ditulis** sama sekali (TOML tidak punya tipe null).

## 1. Aturan yang mengikat

| # | Aturan | Sumber |
|---|--------|--------|
| K1 | Parameter bursa (lot, fraksi harga, batas ARA/ARB, siklus settlement, tarif biaya, pajak) disimpan sebagai konfigurasi **dengan tanggal berlaku** dan diverifikasi ke pengumuman resmi — **bukan konstanta di kode** | PRD 10 |
| K2 | Semua ambang, bobot faktor, batas risiko, dan asumsi biaya adalah pengaturan berversi di berkas konfigurasi; setiap perubahan menaikkan versi preset | PRD 8.3 |
| K3 | Versi preset dicatat pada setiap hasil saringan supaya hasil lama tidak tercampur hasil baru | PRD 8.3, AC-7 |
| K4 | Yang belum terverifikasi ditulis `[PERLU VERIFIKASI]`. Fitur yang bergantung padanya **menolak menghitung** atau menampilkan peringatan — bukan memakai angka tebakan | `docs/keputusan.md` P3, P4 |

### 1.1 Berkas impor: data, bukan aturan

Di samping `parameter-bursa.toml`, folder `konfigurasi/` juga memuat **berkas data** berbentuk
CSV yang dirawat tangan. Bedanya penting: TOML memuat **aturan** bursa (lot, tick, ARA/ARB,
tarif), sedangkan CSV memuat **data** yang memang tidak tersedia dari sumber EOD gratis
(PRD 7.1): daftar emiten, kalender bursa, notasi khusus/suspensi, imbal hasil SUN, aksi
korporasi resmi, dan — bila tidak memakai pengambil otomatis — harga itu sendiri.

| Berkas | Isi | Tanpa berkas ini |
|--------|-----|------------------|
| `emiten.csv` | Daftar emiten: kode, nama, sektor, jenis, papan, status notasi, tanggal pencatatan, jumlah saham, free float | **`--refresh` berhenti.** Semesta saham adalah keputusan pengguna; aplikasi tidak mengarangnya |
| `kalender-bursa.csv` | Hari bursa & hari libur. **Bisa diisi otomatis**: `--ambil-kalender` menuliskannya dari pengumuman KSEI (K11) | "Hari bursa terakhir" dan peringatan snapshot basi (AC-8) belum bisa dihitung |
| `notasi-khusus.csv` | Suspensi, UMA, papan pemantauan. **Bisa diisi otomatis**: `--ambil-notasi` menuliskannya dari halaman resmi IDX di `www.idx.id` (K27); rekaman multi-kode (`>1 Kode`) direkonsiliasi per kode menjadi berkas impor (K36–K51) | Tanpa berkas ini status notasi emiten **belum terverifikasi**: kriteria `pengecualian_notasi` tidak diterapkan dan hasil saringan disebut **"PERINGKAT SEMENTARA"**, bukan kandidat (PRD 7.3). Sejak rekonsiliasi selesai dan penandanya dilepas (K52, 16 Okt 2026) keadaan itu **tidak lagi berlaku atas data lokal**; yang masih belum selesai (K46, 65 episode bertanggal mulai proxy) tetap disebut di kolom `keterangan` barisnya |
| `imbal-hasil-sun.csv` | Imbal hasil SUN per tanggal & tenor | Saringan "imbal hasil laba di atas SUN" berstatus "tidak dihitung" |
| `aksi-korporasi.csv` | Split, reverse split, right issue, dividen — termasuk `tenggat` (batas waktu pelaksanaan) yang **hanya** berlaku untuk `right_issue`; kosong berarti "belum dinyatakan sumbernya", bukan "tidak ada" | Penyesuaian harga historis & arus kas posisi kehilangan masukannya; tanpa baris `right_issue`, tenggat & keputusannya tidak bisa dinilai (dan **tidak ada** sumber otomatis untuknya: sumber EOD menerbitkan 0 baris `right_issue` dari 2.141 baris aksi korporasi) |
| `harga-harian.csv`, `harga-indeks.csv` | OHLCV & penutupan indeks | Hanya perlu bila tidak memakai `--refresh` |

Template seluruh berkas di atas ada di `mejasaham/defaults/*.contoh.csv` dan **disalin otomatis**
ke folder konfigurasi saat belum ada (AC-12); berkas yang sudah ada tidak pernah ditimpa.

Aturan bentuknya (ditegakkan `mejasaham/berkas.py`): baris pertama wajib header; pemisah `;`
atau `,` dideteksi otomatis; BOM UTF-8 diterima; baris berawalan `#` dan baris bertanda
`<<CONTOH>>` diabaikan; nama kolom yang salah ketik **menolak** berkas; nilai kosong berarti
"tidak ada datanya" (bukan nol). `mejasaham/defaults/emiten-awal.contoh.csv` berisi 21 kode
emiten besar sebagai titik awal — **bukan daftar resmi dan tidak lengkap**, dan setiap barisnya
menyatakan itu apa adanya di kolom `sumber`.

## 2. Parameter bursa — WAJIB VERIFIKASI SEBELUM DIPAKAI

Kolom "Nilai" hanya diisi dari pengumuman resmi (IDX/OJK/DJP/broker) atau dari keputusan produk
yang dicatat sebagai keputusan; tanggal berlaku dan tautan sumbernya ikut dicatat.
`[PERLU VERIFIKASI]` berarti **belum ada nilainya** — dan fitur yang bergantung padanya menolak
menghitung, bukan memakai angka tebakan (aturan keras 1).

| # | Parameter | Nilai | Berlaku sejak | Sumber |
|---|-----------|-------|---------------|--------|
| B1 | Jumlah lembar per lot | `[PERLU VERIFIKASI]` | — | idx.co.id |
| B2 | Fraksi harga (tick) per rentang harga | `[PERLU VERIFIKASI]` | — | idx.co.id |
| B3 | Aturan khusus papan pemantauan khusus / full call auction | `[PERLU VERIFIKASI]` | — | idx.co.id |
| B4 | Batas ARA / ARB per kelompok harga | `[PERLU VERIFIKASI]` | — | idx.co.id |
| B5 | Siklus settlement | `[PERLU VERIFIKASI]` | — | idx.co.id |
| B6 | Biaya broker sisi beli — nama broker: **PT Stockbit Sekuritas Digital** (Stockbit) | **0,15%** — *all-in*: menurut halamannya sudah termasuk biaya broker + levy (BEI, KPEI, KSEI) 0,043% + PPN biaya broker 10%. **Tarif minimum: tidak dinyatakan sumbernya** → tersimpan NULL | **tidak dinyatakan sumbernya** → entri memakai **tanggal pengamatan** dengan penanda `asal_berlaku_sejak = "tanggal_pengamatan"` (K22) | [stockbit.com](https://stockbit.com/) blok "Biaya Normal", diakses 10 Okt 2026 00:13 WIB (HTTP 200, DOM ter-render) |
| B7 | Biaya broker sisi jual | **0,25%** — *all-in*, dan menurut halamannya **termasuk PPh final penjualan 0,1%**. **Tarif minimum: tidak dinyatakan sumbernya** → tersimpan NULL | sama dengan B6 | sama dengan B6; kutipan lengkap di `.uji-data/riset-tarif-broker/stockbit.md` |
| B8 | PPh final penjualan saham | `[PERLU VERIFIKASI]` | — | DJP |
| B9 | Slippage | **satu tick** (`mode = "tick"`, memakai tabel fraksi B2) — keputusan produk **K20**, bukan parameter bursa | **tanggal keputusan** 10 Okt 2026, dengan penanda `asal_berlaku_sejak = "tanggal_pengamatan"` | `docs/keputusan.md` K20; PRD 10 |
| ~~B10~~ | ~~Imbal hasil SUN 10 tahun~~ | **bukan parameter berkas ini** — lihat catatan di bawah | — | Data, bukan aturan |

### Catatan B6/B7 — *all-in*, "tidak dinyatakan", dan mengapa keduanya disimpan apa adanya

Tarif Stockbit **sudah dimuat** ke berkas parameter aktif sejak 10 Okt 2026. Yang membuatnya
sebelumnya tidak bisa dimuat bukan tarifnya, melainkan **dua hal yang halaman sumbernya tidak
nyatakan**: tarif minimum dan tanggal berlaku. Bentuk entri yang lama menuntut keduanya, sehingga
memuatnya memaksa satu angka karangan. Dua hal itu dijawab sebagai **K22** dan **K23**
(`docs/keputusan.md` bagian 1):

* **K22 — "tidak dinyatakan sumber" adalah keadaan yang sah.** Dua bentuknya:
  - `minimum` pada `[[biaya_broker]]` boleh **tidak ditulis**. Yang tersimpan `NULL`, dan `NULL`
    berarti *"sumber tidak menyatakannya"* — **bukan 0**. Nol berarti "tidak ada tarif minimum",
    dan itu pernyataan tentang bursa yang halaman Stockbit tidak buat. Bedanya diuji:
    `tests/test_konfigurasi.py` membuktikan baris tanpa `minimum` dan baris ber-`minimum = 0`
    dapat dibedakan di basis data.
  - `berlaku_sejak` boleh berisi **tanggal pengamatan**, asalkan disertai kolom pendamping
    `asal_berlaku_sejak` bernilai `"sumber"` (bawaan) atau `"tanggal_pengamatan"`. Polanya sama
    dengan `asal_tgl_publikasi` (K19b, migrasi 007): tanggalnya tetap bertipe tanggal dan tetap
    dipakai berhitung, tetapi *"tanggal berlaku tidak diketahui"* tidak pernah terbaca sebagai
    *"berlaku sejak"*. Nilai tak dikenal ditolak berisik.
* **K23 — tarif all-in menyimpan penandanya di entri.** `sudah_termasuk` berisi daftar komponen
  yang **dinyatakan sumber** sudah tercakup. Nilai yang sah hanya tiga: `levy`, `ppn`,
  `pph_penjualan`. Disimpan sebagai baris di tabel `parameter_biaya_broker_termasuk`, bukan
  sebagai kalimat, supaya pertanyaan "apakah levy sudah termasuk?" dijawab mesin. **Tanpa penanda
  ini, kalkulator biaya Tahap 2 akan menambahkan B8 (PPh final 0,1%) di atas tarif jual 0,25%
  yang sudah memuatnya — salah dua kali, dan tidak terlihat di keluaran mana pun, hanya di
  angkanya.** Kalkulator biaya kelak **menolak menambahkan** komponen yang sudah termasuk.

Yang **tetap** `[PERLU VERIFIKASI]` dan tidak boleh disimpulkan dari entri di atas:
komponen `0,043%` levy dan "PPN biaya broker 10%" sebagai parameter tersendiri (keduanya hanya
dikutip dari halaman pemasaran broker, bukan dari peraturan bursa/OJK/DJP), dan B8 sebagai tarif
berdasar hukum. Selama B8 belum terverifikasi, entri broker ini **tidak** membuat perhitungan
biaya jual menjadi lengkap dengan sendirinya.

### Catatan B9 — slippage

Slippage **bukan parameter bursa** melainkan keputusan produk (**K20**): satu tick, memakai tabel
fraksi harga B2, sehingga otomatis benar di setiap pita harga. Karena tidak ada sumber yang
menyatakan "berlaku sejak" untuk sebuah keputusan produk, `berlaku_sejak` diisi **tanggal
keputusan** dan ditandai `asal_berlaku_sejak = "tanggal_pengamatan"` (K22). Nilainya tetap
disimpan bertanggal seperti parameter lain supaya bisa diganti tanpa menghapus yang lama.


Catatan B10 (perbedaan yang disengaja, dicatat di `docs/keputusan.md` bagian 4): imbal hasil
SUN **bukan parameter aturan** melainkan **data** — deret bertanggal (tanggal, tenor, nilai,
sumber) yang diperbarui berkala (PRD 7.1: "Imbal hasil SUN 10 tahun | Publikasi resmi |
Bulanan"). Tempatnya tabel [`imbal_hasil_sun`](skema-data.md), diisi lewat jalur impor berkas.
Blok `[[imbal_hasil_sun]]` karena itu **dicabut** dari template TOML: satu fakta, satu sumber.

Catatan dari `docs/keputusan.md` bagian 3.1: aturan ARA/ARB dan papan pemantauan khusus
dilaporkan berubah belakangan ini, dan halaman pengumuman IDX menolak akses otomatis
(HTTP 403), sehingga verifikasi harus dilakukan **manual** di `idx.co.id`.
Karena itu setiap parameter disimpan **bertanggal berlaku** — nilai lama tidak dihapus.

**B1, B2, B6–B9 saat mencatat transaksi (F11, Tahap 2 langkah 3).** Aturan K4 memberi dua pilihan:
*menolak menghitung* atau *menampilkan peringatan*. Kalkulator risiko (F5) memilih yang pertama —
ia memang sedang menghitung ukuran yang akan dieksekusi. `--catat-transaksi` memilih yang kedua,
dan itu disengaja: yang dicatatnya **kejadian yang sudah terjadi di sekuritas**, dan kejadian tidak
batal karena parameter belum diisi. Karena itu bila fraksi harga (B2) atau lot (B1) belum dapat
dipakai, transaksinya tetap tersimpan dengan **catatan yang menyebut sebabnya** di keluaran; bila
tarif broker (B6/B7) belum ada, kolom `biaya` dibiarkan `NULL` **beserta alasannya** dan hasil
bersihnya ditandai belum lengkap — bukan diisi nol. Yang tetap **ditolak** berisik: harga bukan
tick sah dan lembar bukan kelipatan lot **ketika tabelnya tersedia** (salah ketik adalah cara
termudah membuat posisi menempel pada angka yang tidak pernah terjadi).

## 3. Batas risiko portofolio (PRD 8.2, 8.3) — **sudah berbentuk, ada di basis data**

Sejak Tahap 2 langkah 2 (migrasi 010) batas ini **bukan** angka di berkas ini dan **bukan**
konstanta di kode: ia baris berversi di tabel `preset_risiko` + `preset_risiko_nilai`
(`docs/skema-data.md` 5.10), dibuat lewat
`python -m mejasaham --batas-risiko-bawaan`, dan setiap `rencana`
menyimpan `id_preset_risiko` yang benar-benar dipakainya. Mengubah satu batas berarti **menaikkan
versi**, bukan menyunting nilai — supaya rencana lama tetap menunjuk aturan yang berlaku saat itu
(PRD 8.3).

| # | Parameter (nama di basis data) | Nilai awal | Catatan |
|---|-----------|-----------|---------|
| R1 | `risiko_per_posisi` | 75 bp (0,75% ekuitas) | PRD 9.7 "Batas bawaan"; 1R didefinisikan di 8.2 |
| R2 | `total_risiko_maksimum` | 500 bp (5% ekuitas) | **Pemeriksaan**, bukan pagu: pelanggarannya ditampilkan beserta ukuran yang patuh, dan rencana hanya bisa disimpan setelah pengguna memilih (PRD 9.7) |
| R3 | Maksimum posisi aktif | ≈ 6 | **Turunan**, bukan angka bebas: R2 ÷ R1. Mengubah R1 atau R2 berarti meninjau R3 |
| R4 | `bobot_maksimum` | 1000 bp (10% ekuitas) | Salah satu pagu ukuran akhir (PRD 9.7) |
| R5 | `bobot_sektor_maksimum` | 3000 bp (30% ekuitas) | Salah satu pagu ukuran akhir (PRD 9.7). Paparan sektor dihitung dari **satu taksonomi**: `sektor_idx_ic` bila terisi, selain itu `sektor_sumber` (K25) — rencana yang tidak punya nilai pada taksonomi itu **tidak** ikut dijumlahkan dan jumlahnya dilaporkan. Bila kedua kolom kosong, batas ini "tidak dinilai" beserta sebabnya |
| R5b | `likuiditas_maksimum` | 200 bp (2% ADTV20) | ADTV20 emiten; bila metriknya "tidak dihitung", batas ini tidak dinilai |
| R6 | Drawdown maksimum | ≤ 20% | Ambang awal 8.2; **belum** ada pemeriksanya (butuh ekuitas harian yang berjalan lama, F11) |

Yang **bukan** parameter di sini: `kas tersedia` (datanya dari `ekuitas_harian`, F11) dan tarif
minimum broker (K22: boleh tidak dinyatakan sumber; bila ada, ia per transaksi sedangkan rumus PRD
9.7 per lembar — karena itu ia dilaporkan sebagai catatan, bukan dimasukkan diam-diam).

## 4. Ambang saringan & metrik (PRD 8.2, tabel 10) — nilai awal semua

| Metrik | Ambang awal |
|--------|-------------|
| ADTV20 | ≥ Rp 5 miliar |
| ROE 5 tahun | ≥ 12% (median ROE tahunan; tahun dengan ekuitas ≤ 0 → "tidak dihitung") |
| DER | ≤ 2,0 (tidak dipakai untuk bank & lembaga keuangan) |
| Coverage | ≥ 3x |
| Mutu laba (CFO/NI) | ≥ 0,8 (3 tahun) |
| CAGR pendapatan | ≥ 5% (3 tahun) |
| PER | ≤ 1,2x median sektor (PER ≤ 0 → "tidak dihitung") |
| PBV | ≤ 1,5x median sektor |
| EV/EBITDA | ≤ median sektor |
| Imbal hasil laba | di atas imbal hasil SUN 10 tahun |
| Momentum 12-1 | ≥ 0 |
| Kekuatan relatif (6 bulan vs IHSG) | ≥ 0 |
| Volatilitas disetahunkan | ≤ 40% |
| ATR14 | ≤ 6% harga |
| Jarak 52 minggu | ≥ −25% |
| Tren | di atas MA200 |
| Skor "kandidat hari ini" | ≥ 70 |

Set metrik bank & keuangan (PRD 8.4, ringkas lewat impor berkas): NPL kotor ≤ 3%,
CAR ≥ 14%, BOPO ≤ 85%, NIM ≥ 3,5%. DER, coverage, dan CFO/NI **tidak** dipakai untuk bank.

Set per jenis emiten lain (siklikal & komoditas memakai PER normalisasi; padat modal boleh
memakai ambang DER per sektor; sektor < 8 emiten likuid memakai fallback semesta penuh) diatur
di preset, bukan di kode.

### 4.1 Mengisi kolom `jenis` emiten (K21)

`jenis` menentukan set kriteria mana yang berlaku, jadi mengisinya **mengubah hasil saringan**
— dan karena itu ia tidak boleh dikarang. Tiga nilai sahnya: `umum`, `bank_keuangan`,
`siklikal_komoditas`. Dua jalan mengisinya:

| Jalan | Untuk apa | Yang **tidak** dikerjakan |
|---|---|---|
| `python -m mejasaham --ambil-jenis [--timpa-jenis]` | Menurunkan **hanya** `bank_keuangan` dari `sector`/`industry` yang **dinyatakan sumber data**, lalu menulis `emiten.csv` untuk diimpor lewat `--impor`. Sisanya `umum`. Aturannya satu fungsi murni di [`mejasaham/jenis.py`](../mejasaham/jenis.py) dan bisa diuji tanpa jaringan | `siklikal_komoditas` **tidak pernah** diturunkan; `sektor_idx_ic` tetap kosong; emiten yang sumbernya tidak menyatakan sector/industry tetap **kosong** (bukan `umum`) |
| Menyunting kolom `jenis` di `emiten.csv` dengan tangan | Untuk `siklikal_komoditas` dan untuk mengoreksi hasil turunan | — |

`--ambil-jenis` **tidak menimpa** `jenis` yang sudah terisi, dan menolak menimpa `emiten.csv`
yang sudah ada tanpa `--timpa-jenis`. Karena `dicatat_pada` diisi waktu baru setiap jalan,
impor berikutnya menambah **revisi** di basis data, bukan menimpa. `--saring` melaporkan
sebarannya (K21 batas (c)): berapa `bank_keuangan` dari data, berapa `umum`, berapa
`siklikal_komoditas` (isian manusia), dan berapa yang masih kosong — sebab begitu `jenis` terisi,
kriteria bank mulai berlaku dan DER/coverage/CFO-NI berhenti dihitung untuk bank (PRD 8.4, AC-16).

## 5. Ambang mutu data (PRD 7.3) — nilai awal

| Kondisi | Ambang / perilaku |
|---------|-------------------|
| Data fundamental kedaluwarsa | lebih tua dari 18 bulan → metrik kualitas disembunyikan, emiten keluar dari saringan fundamental |
| Lonjakan harga mencurigakan | > 3x tanpa aksi korporasi → ditandai untuk ditinjau manusia |
| Pengecekan sumber kedua | tiap minggu, 20 emiten ber-ADTV20 tertinggi dibandingkan sumber kedua; selisih > 1% ditandai. **Jeda maksimum 7 hari inklusif** (hari ke-7 masih tepat waktu, "lewat" mulai hari ke-8), dan setiap jalan dicatat sebagai peristiwa di tabel `cek_sumber_kedua` — jadi "kapan terakhir dijalankan" bisa diperiksa, bukan diasumsikan (`mutu.JEDA_CEK_SUMBER_KEDUA_HARI`) |
| Data bolong | harga/volume hari terakhir kosong → emiten ditandai "data bolong", keluar dari peringkat |

## 6. Bentuk teknis (diputuskan: K6; pemuatnya sudah ada)

| Aspek | Keputusan |
|-------|-----------|
| Format parameter bursa | **TOML**, `tomllib` dari stdlib (Python 3.11+) — nol dependensi tambahan; punya tipe tanggal bawaan dan boleh berkomentar, sehingga jejak verifikasi bisa ditulis di sebelah angkanya |
| Template | [`mejasaham/defaults/parameter-bursa.contoh.toml`](../mejasaham/defaults/parameter-bursa.contoh.toml) — seluruh entri dikomentari, placeholder `<...>` supaya tidak ada angka yang bisa tersalin dan disalahartikan |
| Berkas aktif | `%LOCALAPPDATA%\MejaSaham\konfigurasi\parameter-bursa.toml`, dibuat otomatis dari template saat belum ada (AC-12). Berkas yang sudah ada **tidak pernah ditimpa** |
| Cara memuat | `python -m mejasaham --muat-konfigurasi` — membaca berkas, memvalidasi, menyimpan ke tabel bertanggal, lalu melaporkan keadaan tiap parameter dan keluar 1 bila berkasnya salah. Bisa dijalankan tanpa jendela (AC-11) |
| Letak saat jalan | `%LOCALAPPDATA%\MejaSaham\konfigurasi\` (PRD 6.1). TOML adalah alat edit; baris hasil muatannya di basis data yang menjadi bukti perhitungan |
| Preset & batas risiko | **Bukan berkas.** Baris berversi di basis data, supaya `Skor` lama tetap merujuk `id_preset` yang isinya tak berubah (PRD 8.3) |
| Sifat daftar entri | Append-only per parameter: aturan berubah → tambah entri dengan `berlaku_sejak` lebih baru, nilai lama tidak ditimpa |
| Wajib per entri | `berlaku_sejak`, `dicatat_pada`, dan `sumber`; entri tanpa salah satunya ditolak saat dimuat dengan menyebut entri mana |
| Tiga keadaan nilai | entri tidak ada → "belum terverifikasi"; `aktif = false` → "sengaja dinonaktifkan"; ada & aktif → dipakai |
| Satuan di basis data | rupiah & lembar `INTEGER`, persen → **basis poin** `INTEGER` (0,15% = 15 bp) memakai `Decimal`, bukan pemotongan float (T8, D-8) |
| Tabel tujuan | `parameter_bursa` (kepala) + tabel muatan bertipe per parameter; rinciannya di [`skema-data.md`](skema-data.md) bagian 5 |

Yang **ditolak** pemuat (bukan diabaikan; berkas salah baca lebih berbahaya daripada berkas
menolak): kunci yang tidak dikenal (termasuk salah ketik seperti `tickk`), tipe yang salah,
tanggal yang bukan tanggal, `aktif` yang bukan boolean, persen di luar 0–100, nilai
berpecahan pada kolom rupiah/lembar, `rentang` yang berlubang atau tumpang tindih, dua entri
beridentitas sama di satu berkas, dan isi berbeda pada identitas yang sudah tersimpan
(perbaikannya: tambah entri dengan `dicatat_pada` lebih baru).

Validasi bentuk TOML-nya sendiri: template dan seluruh bentuk entri di atas diurai dengan
`tomllib` pada Python 3.12 (stdlib) — sembilan tabel terbaca, `berlaku_sejak` terbaca sebagai
tipe tanggal, tabel inline bersarang dan larik inline juga valid; sejak itu diuji ulang pada
Python 3.14 lewat `tests/test_konfigurasi.py`.
