# Skema Data Meja Saham

Status: **kerangka, sebagian sudah dikunci.** Daftar entitas di bawah diambil dari PRD 8.1
(tabel 9). Migrasi 001–015 (fondasi data, parameter bursa bertanggal, penanda penyesuaian
sumber/fundamental/rasio bank, preset & skor, "terkini" per sumber, catatan cek sumber kedua,
kandidat & watchlist, batas risiko & rencana, sektor dari sumber data, transaksi & posisi,
aksi korporasi, jurnal, dan konteks pasar tersimpan) sudah ditulis dan diuji — definisi kolom
yang berlaku ada di `mejasaham/skema.py`; tabel di bagian 5 menjelaskan alasannya. Ekspor F9
memakai berkas turunan, dan cadangan/pemulihan F12 membundel basis data, konfigurasi, serta arsip
snapshot tanpa tabel baru.

## 1. Aturan umum

| # | Aturan | Sumber |
|---|--------|--------|
| S1 | **Append-only.** Perbaikan data menambah baris baru, tidak menimpa. Hasil saringan lama tetap bisa direproduksi | PRD 7.2 |
| S2 | Setiap baris harga/fundamental menyimpan `sumber` dan `diketahui_pada` | PRD 7.2 |
| S3 | **Snapshot = batas waktu (as-of)** + versi skema + versi aplikasi, bukan salinan penuh | PRD 8.1, 7.2 |
| S4 | Fundamental dipakai sejak `tgl_publikasi`, bukan sejak akhir periode | PRD 7.2, AC-15 |
| S5 | Harga disimpan **mentah**; penyesuaian aksi korporasi dihitung saat dibaca, hanya dengan aksi yang diketahui pada tanggal snapshot | PRD 7.2 |
| S6 | Skema berversi; pembaruan aplikasi tidak boleh menghilangkan jurnal atau tesis | PRD 9.13 |
| S7 | Snapshot ditulis atomik (semua atau tidak sama sekali) | PRD 9.13, AC-19 |
| S8 | Hanya satu proses menulis basis data pada satu waktu | PRD 6.1, AC-19 |

## 2. Entitas (PRD 8.1, tabel 9)

| Entitas | Isi | Kunci |
|---------|-----|-------|
| `Emiten` | kode, nama, sektor IDX-IC, jenis (bank & keuangan / siklikal-komoditas / umum), papan pencatatan, lot, tick, status notasi, jumlah saham beredar, free float — **catatan:** tabel 9 menyebut 3 jenis, sedangkan tabel 11 menambah perlakuan "padat modal (properti, infrastruktur, utilitas)"; perlu diputuskan apakah itu jenis tersendiri atau turunan sektor | `kode` |
| `HargaHarian` | tanggal, open, high, low, close (mentah), volume, nilai transaksi, `penyesuaian_sumber`, sumber, `diketahui_pada` — **kunci alami diperluas** menjadi `kode` + `tanggal` + `sumber` (migrasi 005): sejak harga pembanding diimpor untuk cek sumber kedua (PRD 7.3), satu `(kode, tanggal)` punya dua baris yang sah | `kode` + `tanggal` + `sumber` |
| `Fundamental` | periode, jenis laporan (tahunan / YTD kumulatif), `tgl_publikasi`, pendapatan, laba bersih induk, ekuitas induk, EBIT, beban bunga, D&A, utang berbunga, kas, arus kas operasi, jumlah saham, dividen per saham, sumber | `kode` + `periode` + `tgl_publikasi` |
| `AksiKorporasi` | tanggal, jenis, rasio, keterangan | `kode` + `tanggal` + `jenis` |
| `Snapshot` | tanggal data, batas diketahui (as-of), jam ambil, jumlah emiten, jumlah baris gagal, versi skema, versi aplikasi | `id_snapshot` |
| `PresetSaring` | nama, versi, daftar kriteria, bobot faktor, tanggal dibuat, catatan perubahan | `id_preset` |
| `Skor` | kode, `id_snapshot`, `id_preset`, skor tiap faktor, skor total, peringkat, alasan | `kode` + `id_snapshot` + `id_preset` |
| `Kandidat` | kode, tesis, pembatal fundamental, harga pembatal (opsional), horizon, target, stop awal, status (ide / watchlist / rencana / dibuang) | `id_kandidat` |
| `Rencana` | ekuitas, risiko per posisi, harga masuk, stop, biaya & slippage per lembar, ukuran mentah, jumlah lembar akhir, risiko nominal, jenis stop | `id_rencana` |
| `Transaksi` | tanggal, kode, aksi (beli/jual), harga, jumlah, biaya, pajak, hasil, `id_rencana`, `id_posisi`, mode (simulasi/nyata) — **sudah ada**, migrasi 012 (lihat 5.13) | `id_transaksi` + `revisi` |
| `Posisi` | kode, tanggal buka/tutup, lembar, harga rata-rata, stop terkini, status (aktif/ditutup), mode, `id_rencana` — **sudah ada**, migrasi 012 (lihat 5.13); `lembar` dan `harga_rata` **tidak** disimpan karena turunan `transaksi` | `id_posisi` + `revisi` |
| `EkuitasHarian` | tanggal, nilai pasar posisi, kas, setoran/penarikan, ekuitas, drawdown — **sudah ada sebagian**: migrasi 010 + `arus_dana`/`mode` di migrasi 012 (lihat 5.13); `drawdown` **tidak** disimpan karena turunan deret | `tanggal` + `revisi` |
| `HargaIndeks` | tanggal, indeks (IHSG, LQ45/IDX80), penutupan | `indeks` + `tanggal` |
| `KalenderBursa` | tanggal, hari bursa (ya/tidak), keterangan | `tanggal` |
| `Jurnal` | keputusan, alasan, kepatuhan aturan, kode pelanggaran, pelajaran, tanggal tinjau — **sudah ada**, migrasi 014 (lihat 5.15); `patuh_aturan` dan `kode_pelanggaran` **tidak** disimpan karena turunan baris yang mencatatnya | `id_jurnal` + `revisi` |
| `LogJalan` | waktu, jenis proses, hasil, pesan, `id_snapshot` | `id_log` |

Tabel rujukan yang dirawat manual (impor), di luar tabel 9 tetapi wajib ada:
`KalenderBursa` (ada di tabel 9), `NotasiKhusus` (suspensi/UMA/papan pemantauan, bertanggal),
`SektorIDXIC`, dan `ImbalHasilSUN` (PRD 7.1).

## 3. Kunci yang sudah dikunci oleh keputusan, bukan pilihan bebas

- `Skor` berkunci `kode + id_snapshot + id_preset` — konsekuensi K1 (dua ember preset); skor
  tidak pernah dibandingkan lintas preset.
- Setiap ekspor memuat `id_snapshot` + versi preset di baris kepala (AC-7).
- `id_snapshot` ikut tercatat di `LogJalan` supaya kegagalan bisa ditelusuri (AC-9).

## 4. Keputusan detail & yang masih terbuka

| # | Pertanyaan | Catatan |
|---|-----------|---------|
| D-1 | ~~SQLite atau Parquet?~~ | **Terjawab — K5**: SQLite WAL, Parquet hanya turunan |
| D-2 | Kontradiksi C4: `HargaHarian` tanpa `diketahui_pada` di satu tempat PRD, ada di tempat lain | Usulan `docs/keputusan.md`: pakai gabungan terlengkap → `diketahui_pada` disertakan |
| D-3 | Tipe kolom uang: integer rupiah atau desimal? | **Terjawab — T8 di `docs/arsitektur.md`**: INTEGER rupiah, nilai mentah berpecahan di kolom `*_mentah` TEXT |
| D-4 | Strategi penyesuaian (split/right issue) disimpan sebagai tabel turunan atau dihitung saat baca? | **Terjawab — T5**: dihitung saat dibaca, di-cache per `id_snapshot`; tidak ada tabel harga tersesuaikan |
| D-5 | Definisi teknis "versi skema" & cara migrasi | **Terjawab — T9**: `PRAGMA user_version` + daftar migrasi berurutan, cadangan sebelum migrasi |
| D-6 | Kunci tabel append-only: PRD menyebut `HargaHarian` berkunci `kode + tanggal`, tetapi S1 mewajibkan perbaikan menambah baris | **Terjawab — T10**: kunci utama memuat `diketahui_pada`, sehingga `(kode, tanggal)` boleh punya banyak revisi; tampilan `v_<tabel>_terkini` yang menentukan revisi terpakai. Tanpa ini, "perbaikan menambah baris" dan "kunci kode+tanggal" tidak bisa benar bersamaan |
| D-7 | `lot` & `tick` ada di kolom `Emiten` (PRD 8.1 tabel 9), padahal PRD 10 mewajibkan parameter bursa sebagai konfigurasi bertanggal | **Diputuskan ikut K1/PRD 10**: keduanya **tidak** menjadi kolom `emiten`; tempatnya konfigurasi bertanggal + tabel parameter. Perbedaan dengan tabel 9 dicatat di sini dan di `docs/keputusan.md` bagian 4 |
| D-8 | Satuan kolom tingkat/rasio (imbal hasil, free float) | **Terjawab**: INTEGER basis poin (1 bp = 0,01%), mis. `imbal_hasil_bp`, `free_float_bp`; nilai berpecahan sumber tetap di kolom `*_mentah`. Alasan: sebanding dengan T8 dan tidak menimbulkan galat pembulatan saat dibandingkan |
| D-9 | Format waktu di basis data | **Terjawab — T12**: ISO-8601 (`2026-10-06`, `2026-10-06T18:00:00+07:00`) di basis data; format Indonesia (U11) hanya di lapisan tampilan/ekspor |
| D-10 | Apakah aturan append-only cukup ditulis di dokumen? | **Terjawab — T10**: tidak. Setiap tabel data punya trigger yang menolak `UPDATE`/`DELETE`, jadi aturan ditegakkan mesin, bukan disiplin penulis kode |
| D-11 | Asal kolom `nilai` transaksi (U6: dihitung vs dari sumber) | **Terjawab**: kolom `asal_nilai` (`hitung`/`impor`) mencatat asal angka, supaya nilai hasil hitungan tidak tertukar dengan nilai terbitan sumber |

## 5. Definisi tabel yang berlaku (migrasi 001 — Tahap 0)

**Sumber kebenaran yang bisa dieksekusi:** `mejasaham/skema.py`. Tabel di bawah menjelaskan
**alasan** tiap batasan; kalau keduanya berbeda, `skema.py` yang benar dan berkas ini yang
harus diperbaiki.

Tabel dibuat `STRICT` supaya nilai bertipe salah ditolak mesin (D-8, T8), dan setiap tabel di
bawah ini bersifat append-only (D-6, D-10) kecuali disebut lain.

| Tabel | Isi | Kunci utama | Catatan/alasan |
|-------|-----|-------------|----------------|
| `emiten` | kode, nama, sektor IDX-IC, jenis, papan, status notasi, tanggal notasi, jumlah saham, free float (bp), sumber, `diketahui_pada` | `kode` + `diketahui_pada` | `jenis` dibatasi 3 nilai PRD 8.1; `NULL` = belum diklasifikasi (belum diputuskan apakah "padat modal" jenis tersendiri — lihat D-7 & catatan tabel 11). `tanggal_notasi` diisi dari `Listing Date` Master File Efek KSEI lewat `--ambil-emiten` (sejak 9 Okt 2026); PRD tidak menjelaskan arti nama kolomnya, jadi pemetaan itu dicatat sebagai **P18** di `keputusan.md` |
| `harga_harian` | kode, tanggal, open/high/low/close, volume, nilai, `asal_nilai`, `penyesuaian_sumber`, kolom `*_mentah`, sumber, `diketahui_pada` | `kode` + `tanggal` + `sumber` + `diketahui_pada` | Harga mentah (S5); `high >= low` dijaga CHECK; indeks tambahan pada `tanggal` untuk pertanyaan lintas emiten per hari. `sumber` masuk kunci utama di **migrasi 005** — lihat 5.6 |
| `harga_indeks` | indeks, tanggal, close, `close_mentah`, sumber, `diketahui_pada` | `indeks` + `tanggal` + `diketahui_pada` | IHSG, LQ45/IDX80 (8.2 kekuatan relatif) |
| `aksi_korporasi` | kode, tanggal, jenis, `rasio_lama`, `rasio_baru`, `harga_tebus`, `dividen_per_saham`, keterangan, sumber, `diketahui_pada` | `kode` + `tanggal` + `jenis` + `diketahui_pada` | U4: hanya split/reverse split/right issue menyesuaikan harga. Konvensi rasio: harga disesuaikan × (`rasio_lama` / `rasio_baru`) — split 1:2 → 1 dan 2. Jenis wajib mengisi kolom yang relevan (CHECK) |
| `kalender_bursa` | tanggal, `hari_bursa` (0/1), keterangan, sumber, `diketahui_pada` | `tanggal` + `diketahui_pada` | U5: hari non-bursa tetap disimpan, supaya rentang tanggal bisa ditanyakan dan AC-8 ("snapshot basi") bisa dihitung. Sejak 9 Okt 2026 kolom `sumber` boleh diisi **per baris** (lewat `--ambil-kalender`): baris libur membawa nomor pengumuman KSEI/IDX-nya, baris hari kerja/akhir pekan membawa penanda **turunan** karena hari bursa diturunkan sebagai hari kerja dikurangi libur resmi (K11, T31). Kosong = ikut label kumpulan seperti sebelumnya |
| `notasi_khusus` | kode, jenis (suspensi/UMA/papan pemantauan/lainnya), `tanggal_mulai`, `tanggal_selesai`, keterangan, sumber, `diketahui_pada` | `kode` + `jenis` + `tanggal_mulai` + `diketahui_pada` | P1: pengecualian emiten likuid. `tanggal_selesai` NULL = masih berjalan pada saat `diketahui_pada` |
| `sektor_idx_ic` | kode sektor, nama, id induk, sumber, `diketahui_pada` | `kode_sektor` + `diketahui_pada` | Rujukan nama sektor; jenis emiten tetap di `emiten` |
| `imbal_hasil_sun` | tanggal, tenor (tahun), `imbal_hasil_bp`, `imbal_hasil_mentah`, sumber, `diketahui_pada` | `tanggal` + `tenor_tahun` + `diketahui_pada` | B10; dipakai pembanding imbal hasil laba |
| `snapshot` | `id_snapshot`, `tanggal_data`, `batas_diketahui`, `jam_ambil`, `jumlah_emiten`, `jumlah_gagal`, `versi_skema`, `versi_aplikasi`, catatan | `id_snapshot` | S3/A4: batas waktu, bukan salinan penuh. Ditulis atomik (A6). `jumlah_gagal` menghitung **kedua** jenis kegagalan (permanen + sementara, K13); pemisahannya ada di `catatan` (`[permanen] kode: alasan`, `[sementara] …`) — kolomnya sendiri belum dipecah, dan menambahkannya berarti migrasi |
| `log_jalan` | `id_log`, waktu, proses, hasil (sukses/gagal/peringatan), pesan, `id_snapshot` | `id_log` | AC-9. `id_snapshot` boleh NULL untuk kegagalan sebelum snapshot terbentuk; kalau ada, harus menunjuk snapshot yang benar-benar ada (foreign key) |

Tampilan `v_<tabel>_terkini` disediakan untuk delapan tabel berversi (D-6); `snapshot` dan
`log_jalan` tidak punya karena keduanya peristiwa, bukan data yang direvisi.

### 5.2 Cara baris ditulis (Tahap 0 langkah 3)

Skema ini hanya berguna kalau penulisnya mematuhi artinya. Tiga hal yang ditegakkan di
`mejasaham/ingesti.py` dan diuji di `tests/test_ingesti.py`:

1. **Idempotensi memakai kunci alami, bukan kunci tabel.** Karena `diketahui_pada` berisi jam
   berjalan, setiap kali ingesti dijalankan nilainya berbeda. Kalau pencarian "baris ini sudah
   ada?" memakai kunci lengkap (yang memuat `diketahui_pada`), tidak ada satu pun baris lama
   yang cocok — dan ingesti ulang menumpuk salinan identik. Akibatnya `v_harga_harian_terkini`
   menyajikan dua revisi berisi hal yang sama dan laporan mutu menghitung setiap baris dua kali.
   Karena itu perbandingan dilakukan atas kunci **tanpa** `diketahui_pada`, lalu isinya
   dibandingkan lewat sidik SHA-256: sama → tidak menulis, berbeda → menambah revisi (S1).
2. **`INSERT OR IGNORE` tidak dipakai di titik tulis (D-12).** `OR IGNORE` menelan semua
   kegagalan constraint — bukan hanya tabrakan kunci utama, tetapi juga CHECK. Baris dengan
   harga negatif hilang tanpa satu pun pesan sementara ingesti melaporkan sukses. Tabrakan
   kunci diperiksa lebih dulu secara eksplisit, lalu `INSERT` biasa dijalankan sehingga
   pelanggaran apa pun naik sebagai galat.
3. **Kolom `*_mentah` benar-benar ditulis (D-13).** Kolom itu satu-satunya tempat angka asli
   sumber disimpan (T8); kalau tidak ikut ditulis, "nilai berpecahan disimpan untuk audit"
   hanya benar di atas kertas.

Semuanya berada dalam **satu** transaksi bersama baris `snapshot` dan `log_jalan`, sehingga
kegagalan di tengah tidak meninggalkan snapshot yang tampak sah padahal isinya separuh (A6).

| # | Pertanyaan | Catatan |
|---|-----------|---------|
| D-12 | Boleh `INSERT OR IGNORE` dipakai supaya ingesti ulang tidak gagal karena kunci kembar? | **Terjawab: tidak.** Ia menelan kegagalan CHECK juga. Tabrakan kunci diperiksa eksplisit lebih dulu (T16 di `docs/arsitektur.md`) |
| D-13 | Apakah kolom `*_mentah` cukup didefinisikan di skema? | **Terjawab: tidak.** Ia harus ikut ditulis; definisi kolom yang tidak pernah diisi sama dengan tidak ada (T17) |

### 5.1 Migrasi 002 — parameter bursa bertanggal (K1, K6, T7)

Bentuknya: **satu tabel kepala** (`parameter_bursa`) + **satu tabel muatan bertipe** per
parameter. Alasannya: parameter bursa haram menjadi konstanta di kode dan nilainya berubah
menurut tanggal (PRD 10), tetapi muatannya berbeda-beda bentuk (satu angka, daftar rentang,
tarif per sisi) — menaruh semuanya sebagai JSON di satu kolom akan menyembunyikan salah tipe,
padahal justru itu yang dijaga T8/T11.

| Tabel | Isi | Catatan/alasan |
|-------|-----|----------------|
| `parameter_bursa` | nama parameter, kelompok, `berlaku_sejak`, `asal_berlaku_sejak`, `dicatat_pada`, `sumber`, `aktif`, `uraian`, `sidik_jari` | Kepala semua entri. Kunci `nama + kelompok + berlaku_sejak + dicatat_pada`: memuat berkas dua kali tidak menambah baris, sedangkan koreksi menambah baris dengan `dicatat_pada` lebih baru. `sidik_jari` = SHA-256 isi entri, penjaga "identitas sama, isi berbeda" → ditolak. `kelompok` hanya untuk `biaya_broker` (per broker) dan `auto_rejection` (per kelompok harga resmi); `uraian` wajib untuk `papan_pemantauan_khusus`. `asal_berlaku_sejak` ditambahkan **migrasi 008** (K22) — lihat 5.8 |
| `parameter_lot` | `nilai_lembar` | B1 |
| `parameter_fraksi_harga_rentang` | `batas_bawah`, `batas_atas` (NULL = tanpa batas atas), `tick` | B2. `batas_bawah` ikut kunci utama karena satu entri punya banyak rentang |
| `parameter_auto_rejection_rentang` | `batas_bawah`, `batas_atas`, `ara_persen_bp`, `arb_persen_bp` | B4; persen disimpan basis poin (D-8) |
| `parameter_settlement` | `hari_kerja` | B5; batas 0–30 hanya penangkap salah ketik |
| `parameter_biaya_broker` | `persen_beli_bp`, `minimum_beli`, `persen_jual_bp`, `minimum_jual` | B6/B7, per broker. Sejak **migrasi 008** (K22) kedua kolom `minimum_*` **boleh NULL** — lihat 5.8 |
| `parameter_biaya_broker_termasuk` | `komponen` (tabel anak, satu baris per komponen) | **Migrasi 008** (K23): komponen yang dinyatakan sumber **sudah termasuk** di dalam tarif broker. Lihat 5.8 |
| `parameter_pajak_penjualan` | `persen_bp`, `dasar` | B8; `dasar` menyebut dasar pengenaan menurut aturan |
| `parameter_slippage` | `mode` (`tick`/`persen`), `nilai_tick`, `nilai_persen_bp` | B9; kolom dipisah supaya satuan tidak bisa salah dibaca tanpa jejak |
| `parameter_papan_pemantauan_khusus` | hanya kunci kepala | B3: bentuk terstrukturnya belum diketahui, dan mengarang kolom berarti menebak aturan bursa. Yang tersimpan hanya `uraian` apa adanya dari sumber |

Tampilan `v_parameter_bursa_terkini` memilih **pencatatan terakhir untuk satu tanggal berlaku**
(`dicatat_pada` terbesar per `nama + kelompok + berlaku_sejak`) — bukan `diketahui_pada` seperti
tabel data, karena yang direvisi di parameter adalah pencatatannya, bukan tanggal berlakunya.
Kepala dan seluruh tabel muatan tetap append-only (trigger menolak `UPDATE`/`DELETE`).

### 5.3 Arsip snapshot harian

PRD 7.2 menuntut arsip snapshot dimulai sejak hari pertama pemakaian, dengan alasan yang
eksplisit: data point-in-time tidak bisa direkonstruksi belakangan. `mejasaham/arsip.py`
menuliskannya ke `%LOCALAPPDATA%\MejaSaham\arsip-snapshot\<tanggal-data>\snapshot-<id_snapshot>\`:

| Berkas | Isi |
|--------|-----|
| `harga.csv`, `indeks.csv`, `aksi-korporasi.csv`, `kalender-bursa.csv`, `notasi-khusus.csv`, `imbal-hasil-sun.csv`, `emiten.csv` | Isi tabel "terkini" apa adanya pada saat arsip dibuat |
| `laporan-mutu.csv` | Hasil pemeriksaan mutu snapshot itu — mutu data juga informasi point-in-time |
| `meta.json` | `id_snapshot`, tanggal data, batas diketahui, versi skema/aplikasi, jumlah baris tiap berkas |

Aturan penulisannya: **tulis atomik** (berkas sementara lalu `os.replace`), **satu folder per
`id_snapshot`** sehingga memperbaiki data menambah arsip alih-alih menggantinya (S1), dan setiap
CSV dimulai baris kepala berisi `id_snapshot` + tanggal data + versi + peringatan sumber tidak
resmi + pernyataan bukan nasihat investasi (AC-7, aturan keras 8). Format CSV mengikuti U11
(UTF-8 BOM, pemisah `;`).

**Belum dibuat (sengaja, menunggu tahapnya):** `cadangan` (F12). Alasannya sama dengan alasan
folder modul tidak dibuat di muka: tabel kosong menyamarkan apa yang benar-benar sudah jadi.
Menambahkannya berarti migrasi baru (T9).

`rencana`, `transaksi`, `posisi`, `ekuitas_harian` **sudah ada** — migrasi 010 dan 012, lihat 5.10
dan 5.13; `jurnal` **sudah ada** — migrasi 014, lihat 5.15.

`kandidat` **sudah ada** — migrasi 009, lihat 5.9.

`fundamental`, `preset_saring`, dan `skor` **sudah ada** — migrasi 003 dan 004, lihat 5.4 dan 5.5.
Migrasi 005 mengubah kunci `harga_harian`, lihat 5.6; migrasi 006 menambah catatan cek sumber
kedua, lihat 5.7; migrasi 008 menambah bentuk "tidak dinyatakan sumber" pada parameter bursa,
lihat 5.8.

### 5.4 Migrasi 003 — penanda penyesuaian sumber, fundamental, rasio bank (K8, Tahap 1)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `harga_harian.penyesuaian_sumber` | `tidak_disesuaikan` / `split` / `split_dividen`, atau NULL | **K8/C10.** Menyatakan apa yang **sudah** dilakukan sumber terhadap harga baris itu. Ditambahkan lewat `ALTER TABLE` karena yang berubah adalah arti baris harga yang sudah ada; `v_harga_harian_terkini` ikut memuatnya tanpa perlu dibuat ulang (SQLite menyelesaikan `SELECT *` saat dipakai). NULL = belum dinyatakan, dan itu **bukan** "tidak disesuaikan": `penyesuaian.sesuaikan` menolak menghitung metrik harga bila ada split relevan pada baris tanpa penanda |
| `fundamental` | kode, periode, jenis laporan (`tahunan`/`ytd_kumulatif`), `tgl_publikasi`, `mata_uang`, `satuan_uang`, pendapatan, laba induk, ekuitas induk, EBIT, beban bunga, D&A, utang berbunga, kas, arus kas operasi, jumlah saham, DPS, kolom `*_mentah`, sumber, `diketahui_pada` | Kunci utama tabelnya `kode` + `periode` + `jenis_laporan` + **`diketahui_pada`** — **`tgl_publikasi` bukan bagian kunci** (dikoreksi 10 Okt 2026; kalimat "ikut kunci" di tempat ini sebelumnya salah, dan `docs/keputusan.md` C5 mencatatnya beserta pertanyaan yang belum tuntas). `tgl_publikasi` tetap yang **menyaring point-in-time**: laporan hanya dipakai sejak tanggal publikasinya, bukan sejak akhir periode (aturan keras 3, AC-15), dan ia diindeks (`ix_fundamental_kode_publikasi`). `satuan_uang` (rupiah/ribuan/juta/miliar) menyimpan satuan yang dinyatakan sumbernya; nilai di kolom uang sudah **dinormalkan ke rupiah utuh** saat impor, karena laporan "dalam jutaan Rupiah" yang diimpor apa adanya membuat setiap rasio salah 10⁶ tanpa terlihat. Minimal satu dari pendapatan/laba/ekuitas/EBIT/arus kas operasi wajib terisi — baris tanpa angka hanya akan menutupi data lama sebagai baris "terkini" |
| `rasio_bank` | kode, periode, `tgl_publikasi`, `npl_kotor_bp`, `car_bp`, `bopo_bp`, `nim_bp`, keterangan, sumber, `diketahui_pada` | PRD 8.4/Q6. **Dipisah dari `fundamental`** karena terbit dengan irama dan butir yang berbeda dari laporan keuangan; menaruhnya dalam satu baris berarti salah satunya harus dikosongkan dan asal angkanya jadi kabur. Tingkat disimpan basis poin; NIM boleh negatif, CAR dan BOPO boleh melewati 100% |

### 5.5 Migrasi 004 — preset saring berversi & skor (K6, Tahap 1)

| Tabel | Isi | Catatan |
|-------|-----|---------|
| `preset_saring` | `id_preset` ('kualitas-nilai/v1'), nama, versi, horizon, keterangan, `dibuat_pada` | Satu baris = **satu versi**. `UNIQUE (nama, versi)` mencegah dua id untuk nama+versi yang sama. Append-only: mengubah ambang berarti versi baru, bukan menyunting baris lama (K6) |
| `preset_kriteria` | kriteria, urutan, aktif, `ambang_rupiah`, `ambang_bp`, pembanding | Ambang disimpan bertipe, bukan JSON (T14). Saturannya dibedakan kolomnya: likuiditas memakai rupiah, sisanya basis poin. `pembanding = 'median_sektor'` hanya untuk kriteria relatif |
| `preset_bobot_faktor` | faktor, `bobot_bp` | PRD 9.5: kualitas 30 / nilai 30 / momentum 25 / volatilitas 15 |
| `preset_bobot_metrik` | faktor, metrik, `jenis_emiten`, `bobot_bp`, arah | PRD 9.5.1, termasuk set bank dan siklikal. `arah` (`tinggi_baik`/`rendah_baik`) ikut disimpan karena ia bagian dari arti metrik; menaruhnya di kode berarti mengubah arti skor lama tanpa jejak |
| `skor` | kode, `id_snapshot`, `id_preset`, skor tiap faktor (bp), `skor_total_bp`, peringkat, `dihitung_pada`, `versi_hitung`, penjelasan | Kunci `kode + id_snapshot + id_preset` persis PRD 8.1. **Sengaja TIDAK append-only**: ia turunan deterministik, bukan data yang direvisi manusia. Menyimpannya append-only akan menumpuk salinan identik setiap kali saringan dijalankan ulang dan membuat "terkini" kehilangan arti; yang menjaga kejujurannya adalah `versi_hitung` |

**NULL pada skor faktor berarti "faktor tidak dinilai"**, dan itu berbeda artinya dari skor 0
("dinilai, hasilnya paling rendah") — aturan keras 2/AC-3 di permukaan basis data.

### 5.6 Migrasi 005 — "terkini" per sumber untuk harga harian (PRD 7.3)

Satu perubahan, dan alasannya bukan kerapian: **kunci alami `harga_harian` menjadi
`kode + tanggal + sumber`**, dan `v_harga_harian_terkini` dibentuk ulang mengikutinya.

| Yang berubah | Sebelum | Sesudah |
|---|---|---|
| Kunci alami `harga_harian` | `kode + tanggal` | `kode + tanggal + sumber` |
| `v_harga_harian_terkini` | dibuat migrasi 001 dengan `SELECT *` | dibentuk ulang dengan kolom eksplisit, berkunci tiga kolom itu |
| `potret.KUNCI_ALAMI["harga_harian"]` | `kode + tanggal` | `kode + tanggal + sumber` (pembacaan as-of harus sepakat dengan tampilan) |

**Kenapa harus berubah.** Pemeriksaan PRD 7.3 menuntut penutupan 20 emiten ber-ADTV20 tertinggi
dibandingkan ke **sumber kedua**. Sumber kedua itu masuk sebagai baris harga biasa dengan label
`sumber` yang berbeda — dan begitu ada dua label, satu `(kode, tanggal)` punya dua baris yang
sah. Dengan kunci lama, "terkini" hanya menyisakan salah satunya, sehingga:

* harga sumber utama **hilang** pada tanggal yang juga dimiliki sumber pembanding, dan laporan
  mutu melaporkannya sebagai data bolong;
* pembacaan snapshot (`potret.muat`) memilih salah satu baris secara relatif terhadap urutan
  baris — hasil perhitungan menjadi tidak deterministik (A5), dan itu lebih buruk daripada salah
  karena tidak bisa direproduksi.

Migrasi 001 **tidak** disunting meski isinya yang berubah: teks migrasi yang sudah terpasang di
basis data pengguna tidak boleh berubah (T9, PRD 9.13), dan `tests/test_db.py` menjaga itu
dengan sidik SHA-256. Karena itu perubahannya diterbitkan sebagai migrasi 005 yang `DROP VIEW`
lalu `CREATE VIEW`. Sekalian dengan itu, kolomnya kini ditulis eksplisit alih-alih `SELECT *`,
supaya bentuk tampilan ini bisa dibaca dan diuji tanpa menjalankan basis data.

`v_harga_indeks_terkini` **tidak** ikut berubah: harga indeks tidak diambil dari dua sumber, dan
menambahkan `sumber` di sana hanya menambah kunci tanpa menambah kebenaran.

### 5.7 Migrasi 006 — catatan cek sumber kedua (PRD 7.3: "tiap minggu")

| Tabel | Kolom | Kunci | Catatan |
|---|---|---|---|
| `cek_sumber_kedua` | `id_cek`, `dijalankan_pada`, `tanggal_data`, `sumber_utama`, `sumber_pembanding`, `jumlah_diperiksa`, `jumlah_ditandai`, `jumlah_tak_terhitung`, `jumlah_belum_dapat`, `cakupan`, `catatan` | `id_cek` | **Peristiwa**, bukan data yang direvisi: satu baris = satu jalan `--cek-sumber-kedua`. `cakupan` hanya dua nilai: `lengkap` (seluruh emiten ber-ADTV20 tertinggi benar-benar dibandingkan) dan `belum_lengkap` |

**Kenapa tabel baru, padahal `log_jalan` sudah mencatat setiap jalan.** Karena PRD 7.3 menuntut
pemeriksaan ini **tiap minggu**, dan pertanyaan "kapan terakhir dijalankan" harus bisa dijawab
sistem. `log_jalan` menyimpan pesan prosa; menyimpulkan cadence dari teksnya berarti menebak —
termasuk menebak apakah cek yang tercatat itu benar-benar membandingkan atau hanya mencoba.
Karena itu ceknya **dicatat saat dijalankan**, bukan disimpulkan belakangan dari isi basis data
(mis. dari ada-tidaknya harga pembanding: pembanding bisa diimpor berkali-kali tanpa satu pun
perbandingan dijalankan).

`cakupan` sengaja **tidak** terpengaruh hasil perbandingannya: cek yang menemukan selisih di atas
1% tetap cek yang sudah dijalankan. Yang membedakan hanyalah temuannya, bukan kehadirannya.

Tabelnya append-only seperti `snapshot` dan `log_jalan`, dan urutan kejadiannya diambil dari
`id_cek` (urutan pencatatan), bukan dari teks `dijalankan_pada`: cap waktu ISO dengan offset
berbeda tidak terurut secara leksikografis, dan urutan yang salah akan menilai cadence dari cek
yang bukan yang terakhir. Batas jedanya **7 hari inklusif** (hari ke-7 masih tepat waktu; "lewat"
mulai hari ke-8) — angkanya ada di `mutu.JEDA_CEK_SUMBER_KEDUA_HARI`, bukan konstanta yang
disebar.

### 5.8 Migrasi 008 — "tidak dinyatakan sumber" sebagai keadaan yang sah (K22, K23)

Tiga perubahan, dan ketiganya tentang satu hal: **pernyataan sumber yang tidak ada tidak boleh
berubah menjadi angka**. Halaman tarif resmi Stockbit menyatakan `0,15%`/`0,25%` dengan tegas dan
menyatakan sendiri bahwa keduanya *all-in* — tetapi **tidak** menyatakan tarif minimum maupun
tanggal berlakunya (`.uji-data/riset-tarif-broker/stockbit.md` bagian 6).

| Yang berubah | Bentuk | Alasan |
|---|---|---|
| `parameter_bursa.asal_berlaku_sejak` | `TEXT NOT NULL DEFAULT 'sumber'`, `CHECK (IN ('sumber','tanggal_pengamatan'))` | **K22.** Sejak sini `berlaku_sejak` boleh berisi **tanggal pengamatan**, asalkan kolom ini menyatakan asalnya. Tanpa penanda itu, "tanggal berlaku tidak diketahui" terbaca sebagai "berlaku sejak" — persis kesalahan yang sudah ditutup untuk `tgl_publikasi` lewat `asal_tgl_publikasi` (migrasi 007, K19b). `NOT NULL DEFAULT 'sumber'` membuat seluruh baris lama tetap benar tanpa ditulis ulang, dan itu wajib sebab `parameter_bursa` append-only |
| `parameter_biaya_broker.minimum_beli`, `minimum_jual` | `NOT NULL` **dicabut** → boleh `NULL` | **K22.** `NULL` = *"sumber tidak menyatakannya"*; `0` = *"tidak ada tarif minimum"*. Yang kedua pernyataan tentang bursa, dan hanya boleh ditulis bila sumbernya memang menyatakannya. Dua keadaan itu hidup berdampingan dan dibedakan uji (`tests/test_db.py::test_minimum_tarif_broker_nol_tetap_bisa_ditulis`) |
| `parameter_biaya_broker_termasuk` (tabel baru) | `nama`, `kelompok`, `berlaku_sejak`, `dicatat_pada`, `komponen` ∈ {`levy`, `ppn`, `pph_penjualan`} | **K23.** Komponen yang dinyatakan sumber **sudah termasuk** di dalam tarif broker. Satu baris per komponen, supaya pertanyaan "apakah levy sudah termasuk?" dijawab mesin — bukan ditafsirkan dari kalimat. Tanpa ini, kalkulator biaya menambahkan B8 (PPh final 0,1%) di atas tarif jual yang sudah memuatnya: **salah dua kali, dan tidak terlihat di keluaran mana pun** |

**Kenapa `parameter_biaya_broker` dibangun ulang, bukan di-`ALTER`.** SQLite tidak punya cara
mencabut `NOT NULL` dari kolom yang sudah ada (`ALTER TABLE ... ALTER COLUMN` tidak ada), jadi
satu-satunya jalan adalah membangun tabel baru, menyalin barisnya, membuang yang lama, lalu
mengganti nama — dan itu dikerjakan **di dalam migrasi 008**, bukan dengan menyunting migrasi 002
yang sudah terpasang di basis data pengguna (T9). Tabel itu punya FOREIGN KEY ke `parameter_bursa`,
sehingga `PRAGMA foreign_keys` dimatikan **hanya** selama rebuild dan dinyalakan kembali di akhir;
sebagai gantinya `PRAGMA foreign_key_check` dijalankan setelahnya. Dua penjaga ikut dipasang di
dalam migrasinya sendiri: penyalinan yang **menambah** atau **kehilangan** baris membuat migrasi
gagal sebelum tabel lama dibuang, sebab skema yang rapi tetapi kehilangan data lebih buruk daripada
migrasi yang berhenti berisik. Rinciannya (termasuk mengapa penjaganya berbentuk trigger sementara)
di `docs/arsitektur.md`.

Trigger append-only untuk tabel anaknya dipasang seperti tabel parameter lain: `UPDATE`/`DELETE`
ditolak mesin, sehingga penanda *all-in* tidak bisa disunting belakangan tanpa jejak.

### 5.9 Migrasi 009 — kandidat & watchlist (F4, AC-4, Tahap 2)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `kandidat` | `id_kandidat`, `revisi`, `kode`, `status`, `tesis`, `pembatal_fundamental`, `harga_pembatal`, `horizon`, `target`, `stop_awal`, `tanggal_tinjau`, `alasan_dibuang`, `dicatat_pada` | Kunci `id_kandidat` + `revisi`. Status yang sah lima: `ide`, `watchlist`, `rencana`, `posisi`, `dibuang` — **`kandidat` bukan salah satunya**, sebab PRD 9.6 menegaskan "kandidat hari ini" hanyalah hasil saringan berskor tinggi, bukan keadaan yang disimpan |
| `v_kandidat_terkini` | Revisi terakhir per `id_kandidat` | **Ditulis eksplisit** memakai `revisi >`, bukan lewat pembangkit view `_sql_tampilan_terkini` yang mengurutkan dengan stempel waktu. Alasannya ditemukan uji: dua revisi dalam **detik yang sama** tidak terbedakan oleh `dicatat_pada`, dan yang terbaca kembali justru revisi lama (T37) |

**Kenapa revisi, bukan baris yang disunting.** PRD 9.8 menuntut "tidak ada penghapusan senyap",
dan tesis adalah satu-satunya isi basis data ini yang **tidak bisa dibangun ulang dari sumber mana
pun** (PRD 9.12). Kalau status dan tesis boleh ditimpa, jejak "apa yang saya yakini waktu itu"
hilang — padahal justru itulah yang dinilai di rekap kepatuhan (PRD 13.1). Karena itu tabelnya
append-only seperti tabel data lain: `UPDATE`/`DELETE` ditolak trigger.

**Kenapa kolom wajib dijaga `CHECK`, bukan hanya oleh modul.** AC-4 adalah kriteria penerimaan,
bukan saran. `kandidat.py` memeriksa lebih dulu supaya pesannya menyebut kolom yang kurang
(manusia yang membacanya), sedangkan `CHECK`-nya yang membuat aturan itu tetap berlaku pada jalur
tulis mana pun — termasuk jalur yang belum ditulis hari ini. Bentuknya:

* status `watchlist`/`rencana`/`posisi` menuntut `tesis`, `pembatal_fundamental`, `horizon`,
  `stop_awal`, dan `tanggal_tinjau` terisi **dan bukan spasi**;
* `ide` dikecualikan (PRD 9.6: ide = "belum ada tesis") — melarangnya akan membuat ide hilang dari
  catatan, dan yang tidak dicatat tidak akan pernah ditinjau;
* `dibuang` menuntut `alasan_dibuang`, tetapi **tidak** menuntut kelengkapan tesis: entri sering
  dibuang justru karena tesisnya tidak pernah lengkap.

### 5.10 Migrasi 010 — batas risiko, ekuitas harian, rencana (F5, Tahap 2)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `preset_risiko` | `id_preset_risiko` (`risiko-bawaan/v1`), `nama`, `versi`, `keterangan`, `dibuat_pada` | Batas risiko portofolio sebagai **pengaturan berversi** (PRD 8.3), bukan konstanta di kode. Kepalanya dipisah dari `preset_saring` sebab yang satu mengatur **ukuran posisi** (F5) dan yang lain **pemilihan emiten** (F2/F3) — menggabungkannya membuat menaikkan ambang saringan menuntut versi baru untuk batas risiko juga, padahal tidak ada yang berubah |
| `preset_risiko_nilai` | `id_preset_risiko`, `nama`, `nilai_bp` | Lima nama yang sah: `risiko_per_posisi` (75 bp), `bobot_maksimum` (1000), `bobot_sektor_maksimum` (3000), `likuiditas_maksimum` (200 = 2% ADTV20), `total_risiko_maksimum` (500) — nilai awal PRD 9.7 "Batas bawaan". Nama lain ditolak `CHECK`: batas yang tidak dikenal tidak akan pernah dinilai dan diam-diam membuat ukuran lolos |
| `ekuitas_harian` | `tanggal`, **`revisi`**, `ekuitas`, `kas`, `catatan`, `sumber`, `diketahui_pada` | F11 dasar, masukan kalkulator risiko (PRD 9.7). Kunci `tanggal` + `revisi` — pembeda revisinya **kolom**, bukan stempel waktu: dua pencatatan dalam detik yang sama akan bertabrakan kalau `diketahui_pada` yang jadi pembeda (kelas cacat T37, ditemukan uji) |
| `kas` NULL | — | NULL = "kas belum dicatat" (batas kas jadi **tidak dinilai**), 0 = "kas benar-benar kosong". Aturan keras 2 |
| `rencana` | `id_rencana`, `revisi`, `id_kandidat`, `kode`, `id_preset_risiko`, `id_snapshot`, `tanggal`, `ekuitas`, `risiko_per_posisi_bp`, `harga_masuk`, `stop`, `dasar_stop`, `biaya_slippage`, `lembar_mentah_mili`, `lembar`, `maks_lembar_bobot`, `maks_lembar_sektor`, `maks_lembar_likuiditas`, `maks_lembar_kas`, `bobot_bp`, `risiko_nominal`, `risiko_berjalan`, `total_risiko_bp`, `jenis_stop`, `batas_tidak_dinilai`, `catatan`, `dicatat_pada` | Keluaran kalkulator risiko (PRD 8.1, 9.7). Berversi seperti `kandidat`: rencana adalah keputusan, dan PRD 9.12 menyebutnya isi yang tidak bisa dibangun ulang |
| `dasar_stop` | `harga_masuk_minus_2_atr14` · `harga_pembatal` · `pengguna` | Dari mana angka `stop` datang. Tanpa kolom ini, stop tidak bisa ditelusuri asalnya |
| `lembar_mentah_mili` | Ukuran mentah dalam **mili-lembar** (seperseribu) | Hasil pembagiannya berpecahan; memaksanya jadi bilangan bulat membuat rencana tidak bisa diperiksa ulang dari angkanya sendiri |
| `maks_lembar_*` NULL | — | **Batas itu tidak dapat dinilai** (ADTV20 tidak dihitung, `sektor_idx_ic` belum terisi, kas belum dicatat) — bukan "batasnya longgar". Pola yang sama dengan `minimum` tarif broker (K22). `batas_tidak_dinilai` menyimpan sebabnya |
| `CHECK (stop < harga_masuk)` | — | Posisi ini hanya beli (long): stop di atas harga masuk berarti risiko negatif, dan itu selalu salah. `lembar` **tidak** dijaga kelipatan lot di sini — lot adalah parameter bursa bertanggal (K1), yang menjaganya `risiko.py` |
| `v_rencana_terkini`, `v_ekuitas_harian_terkini` | Revisi terakhir per kunci | Ditulis eksplisit memakai `revisi >` (alasan yang sama dengan `v_kandidat_terkini`, T37) |

Empat tabelnya append-only: `UPDATE`/`DELETE` ditolak trigger.

### 5.11 Migrasi 011 — sektor menurut sumber data (K25, PRD 9.7)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `emiten.sektor_sumber` | Sektor **sebagaimana dinyatakan sumber data** (mis. `Financials`, `Energy`, `Basic Materials`) | Kolom **berbeda** dari `sektor_idx_ic`, bukan penggantinya. Dipakai batas bobot per sektor PRD 9.7 **selama** `sektor_idx_ic` belum terisi; begitu ia terisi, ia yang dipakai. Diisi `--ambil-jenis` (jalur yang sama dengan K21) dari `sector` sumber, dan **tidak ditimpa** bila sudah terisi |
| NULL | — | "sumber belum menyatakannya" — bukan "tidak ada sektor". Batas sektor menjadi "tidak dinilai" beserta sebabnya (aturan keras 2) |

Kenapa kolom baru dan bukan mengisi `sektor_idx_ic`: K12 sudah menetapkan kolom itu **khusus
IDX-IC**, dan sumber EOD memakai taksonomi lain. Mengisinya dengan taksonomi sumber membuat dua hal
yang berbeda tampak sama — dan akibatnya bukan tampilan melainkan **angka**: batas bobot per sektor
(PRD 9.7) serta median sektor (PRD 8.2) akan dihitung dari kelompok yang bukan kelompoknya, tanpa
satu pun galat.

Kenapa cukup `ALTER TABLE ADD COLUMN`: `emiten` append-only berkunci `(kode, diketahui_pada)`, jadi
kolom baru langsung punya tempat di setiap revisi berikutnya, dan `v_emiten_terkini` (`SELECT *`)
ikut memuatnya tanpa dibangun ulang. Baris lama bernilai NULL, dan itu memang keadaannya.

### 5.12 Yang belum ada di skema (setelah migrasi 015)

`harga_indeks` yang terisi dan `rasio_bank` sebagai jalur otomatis (K24: diisi manual). Ekspor F9
tidak menambah tabel: CSV adalah turunan dari snapshot, skor/preset, watchlist, rencana, jurnal,
atau arsip mutu yang sudah tersimpan. Migrasi berikutnya bernomor 016 ke atas; migrasi 001–015
**tidak boleh disunting** meski isinya diperbaiki (T9), dan `tests/test_db.py` menjaga itu dengan
sidik SHA-256.

### 5.13 Migrasi 012 — transaksi & posisi (F11, Tahap 2 langkah 3)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `posisi` | `id_posisi`, `revisi`, `kode`, `tgl_buka`, `tgl_tutup`, `status`, `stop_terkini`, `id_rencana`, `mode`, `pelanggaran`, `catatan`, `sumber`, `diketahui_pada` | Kunci `id_posisi` + `revisi`. **Sengaja TIDAK menyimpan `lembar` dan `harga_rata`** walaupun PRD 12 (tabel 23) menyebutnya: keduanya turunan `transaksi`, dan menyimpannya berarti ada dua jawaban untuk satu pertanyaan — begitu keduanya berbeda, tidak ada cara mengetahui mana yang benar. `mejasaham/posisi.py` (`hitungan()`) satu-satunya tempat turunan itu dihitung. `stop_terkini` **boleh NULL** = posisi berjalan tanpa stop, dan itu pelanggaran V1 yang **dicatat**, bukan keadaan yang dicegah; `status` dan `tgl_tutup` dijaga CHECK agar keduanya tidak saling bertentangan |
| `transaksi` | `id_transaksi`, `revisi`, `id_posisi`, `id_rencana`, `tanggal`, `kode`, `aksi`, `harga`, `lembar`, `biaya`, `asal_biaya`, `pajak`, `mode`, `pelanggaran`, `catatan`, `sumber`, `diketahui_pada` | Kunci `id_transaksi` + `revisi`. Berversi, bukan peristiwa append-only seperti `snapshot`: PRD 9.8 menetapkan *"mengubah isi jurnal lama diperbolehkan hanya dengan menyimpan versi sebelumnya"*, dan `transaksi` adalah dasar jurnal itu (PRD 12). `biaya` NULL = belum dicatat (dilaporkan, karena hasil bersihnya lalu tampak lebih baik daripada kenyataan); `asal_biaya` menyatakan apakah angkanya dicatat pengguna atau dihitung dari tarif, dan CHECK menjaga keduanya muncul bersama. **`pajak` adalah BAGIAN dari `biaya`, bukan tambahan** — dijaga `CHECK (pajak <= biaya)`; tanpa itu, laporan yang menjumlahkan keduanya menghitung PPh dua kali pada tarif *all-in* (K23) |
| `ekuitas_harian.arus_dana` | Setoran (positif) / penarikan (negatif) pada tanggal itu | **Migrasi 012.** NULL = belum dicatat, `0` = benar-benar tidak ada. Bedanya bukan hiasan: AC-13 menuntut setoran/penarikan **tidak mengubah** drawdown, dan deret yang arus dananya tidak diketahui tidak boleh dikoreksi dengan nol — itu berarti menganggap setoran sebagai keuntungan |
| `ekuitas_harian.mode` | `simulasi` / `nyata`, atau NULL | **Migrasi 012.** NULL = belum dinyatakan; baris lama tidak diberi label yang tidak pernah dipilih pengguna. PRD 9.11 menuntut metrik kedua mode dilaporkan terpisah, jadi jumlah baris yang belum bermode ikut dilaporkan |
| `v_posisi_terkini`, `v_transaksi_terkini` | Revisi terakhir per kunci | Ditulis eksplisit memakai `revisi >` (alasan yang sama dengan `v_kandidat_terkini`, T37). `id_posisi`/`id_rencana` **tanpa** kunci asing, mengikuti `rencana.id_kandidat`: yang menjaganya modul, dan kunci asing di sini akan menolak baris yang urutan penulisannya sah |

Empat hal append-only seperti tabel lain: `UPDATE`/`DELETE` pada `posisi` dan `transaksi` ditolak
trigger. Yang **tidak** disimpan di skema ini: `drawdown` (PRD 12 menyebutnya sebagai kolom
`ekuitas_harian`) — ia turunan deret ekuitas, dan `risiko.drawdown()` yang menghitungnya.

### 5.14 Migrasi 013 — aksi korporasi pada posisi (F11, PRD 9.11; K28)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `aksi_korporasi.tenggat` | Batas waktu pelaksanaan right issue (mis. batas akhir penebusan HMETD), `YYYY-MM-DD` | **NULL = sumbernya belum menyatakannya**, bukan "tidak ada tenggat" (aturan keras 2): sumber data EOD tidak menerbitkan right issue sama sekali, jadi tenggat hanya bisa datang dari pengumuman atau dari pengguna. Dijaga CHECK bentuk tanggalnya, dan berkas impor **menolak** `tenggat` pada jenis aksi selain `right_issue` — tenggat yang tidak akan pernah dinilai lebih berbahaya daripada tenggat yang kosong |
| `posisi.tgl_stop` | **Basis** level stop: tanggal harga yang dipakai saat stop itu dinyatakan | `stop_terkini` adalah angka yang dicatat manusia ("stop saya 2.180"), dan artinya bergantung pada basis harga saat itu. Tanpa kolom ini, split yang terjadi **sesudah** stop dicatat tidak bisa dibedakan dari split yang sudah tercermin di dalam angkanya — dua kemungkinan itu menghasilkan risiko yang berbeda, dan memilih salah satunya diam-diam berarti memilih angka risiko yang salah. NULL hanya pada baris lama: `posisi.py` **tidak** menebaknya (lihat T49) |
| `keputusan_right_issue` | `id_keputusan`, `revisi`, `id_posisi`, `kode`, `tanggal_aksi`, `keputusan`, `id_transaksi`, `lembar`, `harga`, `biaya`, `catatan`, `sumber`, `diketahui_pada` | Keputusan manual PRD 9.11 (`tebus` / `jual_hmetd` / `abaikan`); nilainya hidup di `skema.KEPUTUSAN_RIGHT_ISSUE_SAH` dan **dipinjam** `posisi.py`. Tiga CHECK yang mengikat: **`tebus` wajib menunjuk `id_transaksi`** (menebus = membeli lembar, dan lembarnya hanya punya satu tempat — `transaksi`; menyalinnya ke sini akan membuat dua catatan untuk satu pembelian), **`jual_hmetd` wajib mengisi `lembar` + `harga`** (hasil penjualan **hak** tidak bisa diturunkan dari data mana pun — dan menjual hak bukan menjual lembar, sehingga transaksi saham justru akan mengurangi lembar yang masih dipegang), dan `abaikan` **tidak boleh** mengisi keduanya |
| `v_keputusan_right_issue_terkini` | Revisi terakhir per `id_keputusan` | Ditulis eksplisit memakai `revisi >` (alasan yang sama dengan `v_kandidat_terkini`, T37). Keputusan yang berubah **menambah revisi**, tidak menimpa |

`keputusan_right_issue` append-only: `UPDATE`/`DELETE` ditolak trigger. Yang **tidak** disimpan:
lembar, harga rata-rata, hasil, dan risiko posisi — keempatnya turunan `transaksi` + `aksi_korporasi`
(K28), dan `posisi.hitungan()` tetap satu-satunya tempat menghitungnya.

### 5.15 Migrasi 014 — jurnal keputusan (F7, PRD 9.8/11.5/12; Tahap 3 langkah 1)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `jurnal` | `id_jurnal`, `revisi`, `id_transaksi`, `alasan`, `pelajaran`, `tanggal_tinjau`, `selesai_pada`, `sumber`, `diketahui_pada` | Satu rantai `id_jurnal` per transaksi, berversi seperti `kandidat`/`posisi`/`transaksi`. **Yang disimpan hanya yang tidak bisa diturunkan**: PRD 12 menyebut pula `tanggal`, `kode`, `patuh_aturan`, dan `kode_pelanggaran`, tetapi keempatnya sudah punya tempatnya sendiri — `tanggal`/`kode` di baris `transaksi` yang diannotasi, dan pelanggaran di baris tempat ia **dideteksi** (V1/V2/V6 di `transaksi`, V5 di `posisi`, V3/V4/V7 dihitung `jurnal.py`). Menyalinnya ke sini akan memberi dua jawaban untuk satu pertanyaan: begitu transaksinya direvisi — dan revisi itu diizinkan PRD 9.8 — salinan di jurnal tetap berbunyi lama tanpa satu pun tanda. Pola yang sama sudah dipakai `posisi` (migrasi 012, T43); keputusannya **T52** |
| `jurnal.selesai_pada` | Tanggal entri jurnal selesai ditinjau | Pemetaan terbuka untuk tombol **"[Tandai selesai]"** PRD 11.5, yang tidak punya kolomnya di PRD 12; `tanggal_tinjau` tetap tanggal tinjau **berikutnya** (kolom yang sama artinya dengan `kandidat.tanggal_tinjau`) |
| Penjaga `jurnal` | `CHECK` baris tidak kosong · trigger satu rantai per transaksi · trigger append-only | Tiga-tiganya **mesin**, bukan disiplin: baris jurnal tanpa isi tidak mencatat apa pun; dua rantai untuk satu keputusan akan menyebar "pelajaran"-nya ke dua tempat; dan PRD 9.8 menuntut versi lama tersimpan, bukan ditimpa. Ketiganya diuji langsung ke basis data di `tests/test_jurnal.py` dan diperiksa atas data nyata di `.uji-data/uji-jurnal/bukti-keadaan.txt` |
| `v_jurnal_terkini` | Revisi terakhir per `id_jurnal` | Ditulis eksplisit memakai `revisi >` (alasan yang sama dengan `v_kandidat_terkini`, T37) |

Yang **tidak** disimpan: `patuh_aturan` dan `kode_pelanggaran` (turunan, dihitung `jurnal.py`),
serta jumlah peristiwa V5 — kolom `posisi.pelanggaran` menyimpan **kode**, bukan peristiwa, jadi dua
kali stop diturunkan pada satu posisi terbaca sama dengan sekali. Itu disebut apa adanya di keluaran
(`jurnal.py`), bukan ditambal dengan angka yang tidak bisa ditelusuri.

### 5.16 Migrasi 015 — konteks pasar tersimpan (K61; PRD 8.2/11.1)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `konteks_pasar` | `id_snapshot`, `id_preset`, `sumber_harga`, `versi_hitung`, `breadth_nilai`, `breadth_status`, `breadth_alasan`, `breadth_asal`, `rezim`, `indeks`, `indeks_tanggal`, `indeks_penutupan`, `indeks_penutupan_sebelumnya`, `catatan`, `dihitung_pada` | Hasil `--saring` yang dibaca dasbor: breadth, rezim, dan penutupan indeks terakhir. Kunci primernya **`id_snapshot + id_preset + sumber_harga`** — ketiganya bagian dari arti angkanya, bukan metadata: semesta likuid ikut ambang ADTV20 preset (K6), dan breadth dihitung dari **satu** label harga (P17). `sumber_harga` `NOT NULL` dengan teks kosong = "belum ada label harga"; NULL di kolom kunci SQLite tidak menjamin keunikan |
| `konteks_pasar.versi_hitung` | Versi cara membungkus/menghitung konteks (`konteks_pasar.VERSI_HITUNG`, sekarang `pasar-2`) | Diperiksa **di WHERE** saat membaca: baris dengan versi lain tidak dipakai, sehingga perubahan rumus membatalkan angka lama alih-alih membuatnya tampak sebanding (pola `skor.versi_hitung`, migrasi 004). Baris lama tidak dihapus — ia tetap bukti apa yang pernah dihitung |
| `konteks_pasar.breadth_status` / `breadth_alasan` | `dihitung` atau `tidak_dihitung`, beserta sebabnya | Dua CHECK menjaga aturan keras 2: `dihitung` **wajib** punya `breadth_nilai`, dan `tidak_dihitung` **wajib** punya `breadth_alasan`. Tanpa itu, baris "tidak dihitung" bisa terbaca sebagai nol, atau "dihitung" tanpa angka |
| `konteks_pasar.catatan` | Sebab rinci bila rezim NETRAL **karena bahannya kurang** (mis. "IHSG baru 199 bar, MA200 butuh 200") | Disimpan bersama angkanya: kalau hanya angkanya yang disimpan, sebabnya hilang saat dibaca dari simpanan dan kalimat tanpa sebab terbaca sebagai penilaian tentang pasar, padahal penilaian tentang data yang belum diimpor (`konteks_pasar.sebab_bahan_kurang`) |

Ditulis **ulang** per kunci, bukan append-only: ia turunan deterministik seperti `skor` (PRD 8.1),
bukan data yang direvisi manusia. Yang menjaga kejujurannya adalah kunci lengkap + `versi_hitung`.
Diisi `pengatur.jalankan_saring` **hanya** bila `simpan=True` (`--kode` parsial tidak menulis apa
pun), dan dibaca `dasbor.susun` hanya bila kunci itu masih sama; selain itu dihitung ulang.

### 5.17 Migrasi 016 — catatan aksi khusus mutu harga (K90)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `catatan_aksi_mutu` | `kode`, `tanggal_efektif`, `instrumen_aksi`, `diketahui_pada`, `ringkasan_bukti`, `sumber_url`, `sumber` | Konteks peristiwa yang tidak didukung sebagai aksi posisi/penyesuaian. Angka dalam `ringkasan_bukti` harus menyebut satuan dan berasal dari sumber yang ditautkan. Kunci revisi: kode + tanggal + instrumen; koreksi menambah baris `diketahui_pada` yang baru |
| `v_catatan_aksi_mutu_terkini` | Revisi terakhir per kode, tanggal efektif, dan instrumen | Laporan mutu membatasi pembacaan pada catatan yang sudah diketahui saat laporan dibuat |

Tabel append-only dengan trigger UPDATE/DELETE. Berkas `catatan-aksi-mutu.csv` memakai jalur
impor umum, terpisah dari `aksi-korporasi.csv`; isinya tidak dibaca modul posisi maupun
penyesuaian. Laporan menambahkan `konteks_aksi_mutu` sebagai temuan CATATAN saat ada lonjakan
dalam rentang lima hari, tetapi mempertahankan temuan lonjakan yang ada dan status tak wajarnya.
Tabel ini tidak menyimpan rasio saham operasional, harga tebus, hasil TERP, atau keputusan tindakan.

### 5.18 Migrasi 017 — sambungan harga resmi (K97, P42)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `sambungan_harga` | `berlaku_sejak`, `sumber_resmi`, `aktif` (0/1), `keterangan`, `sumber`, `diketahui_pada` | Pernyataan pengguna "sejak `berlaku_sejak`, harga dibaca dari label `sumber_resmi`; sebelumnya dari label riwayat (K14)". Kunci revisi: `berlaku_sejak`; revisi `aktif = 0` mencabut tanggal itu |

Tabel append-only dengan trigger UPDATE/DELETE, diisi lewat `sambungan-harga.csv` di jalur impor
umum (kolom `berlaku_sejak;sumber_resmi;aktif;keterangan;sumber`, `aktif` = ya/tidak). Yang
berlaku pada satu snapshot adalah tanggal **aktif terbesar** menurut revisi terakhir yang sudah
diketahui pada batas snapshot (`potret.sambungan_berlaku`), sehingga snapshot lama tidak berubah
saat tanggal sambung diubah. Memajukan tanggal ke yang lebih awal = cabut tanggal lama + nyatakan
yang baru (boleh dalam satu berkas). Seluruh pembaca harga menyaring lewat
`potret.PilihanHarga.syarat`; `--sumber` menimpa sambungan dengan satu label.

### 5.19 Migrasi 018 — tanggal pembanding IHSG di konteks pasar (sesi 69, T100)

| Tabel/kolom | Isi | Catatan |
|-------------|-----|---------|
| `konteks_pasar.indeks_tanggal_sebelumnya` | Tanggal penutupan pembanding `indeks_penutupan_sebelumnya` (`YYYY-MM-DD`, CHECK GLOB), NULL bila tidak ada pembanding | Bar indeks kosong dilewati saat memilih pembanding, jadi pembandingnya tidak selalu hari bursa sebelumnya; dasbor menulis "… terhadap 28 Okt 2026". `konteks_pasar.VERSI_HITUNG` naik ke `pasar-2`, sehingga baris lama tanpa tanggal tidak terpakai dan dihitung ulang |
