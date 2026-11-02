# Ide yang Ditunda

Tempat menampung hal yang **sengaja tidak dikerjakan di v0.1**. Bukan tong sampah: setiap
entri mencatat alasan penundaan dan pemicu kapan ia layak diangkat.

Aturan: jangan hapus entri tanpa keputusan pemilik produk. Kalau sebuah ide dikerjakan,
pindahkan keputusannya ke `docs/keputusan.md` dan tandai entri di sini selesai.

## Dasar penundaan (U16 di `docs/keputusan.md`)

| Ide | Kondisi | Kapan layak diangkat |
|-----|---------|----------------------|
| **Backtest (F8)** | Ditunda ke v0.2; berada di Tahap 4 PRD 16 | Setelah alur keputusan harian terbukti dipakai. Syarat keluar Tahap 4: di luar sampel tidak lebih buruk daripada median portofolio acak & tolok ukur IHSG/LQ45 setelah biaya — atau preset direvisi |
| **Peringatan EOD (F6)** | v0.2; berada di Tahap 4 | Setelah data & jurnal stabil, karena peringatan butuh pembanding status |
| **Laporan PDF** | Tidak masuk v0.1 (PRD tabel 5) | Setelah ekspor CSV/Excel terpakai dan formatnya stabil |
| **Bobot per rezim pasar** | v0.2 (PRD 8.2: "bobot per rezim di v0.2") | Setelah rezim pasar (RISK-ON/NETRAL/RISK-OFF) tervalidasi pada data nyata |
| **Pembelajaran mesin (ML)** | Tidak masuk v0.1 | Hanya setelah backtest tanpa lookahead ada dan hasilnya terukur |
| **Backtest intraday** | Di luar cakupan (PRD tabel 5) | Tidak direncanakan |
| **Data real-time / order book** | Di luar cakupan (PRD tabel 5) | Tidak direncanakan — data berlisensi & berbayar |
| **Eksekusi order otomatis ke broker** | Di luar cakupan (PRD tabel 5) | Tidak direncanakan — batas hukum produk |
| **Multi-pengguna, awan, seluler** | Di luar cakupan (PRD tabel 5) | Tidak direncanakan — produk satu pengguna, satu komputer |

## Ide baru (isi saat muncul)

### Satu modul pengunduh bersama untuk adaptor sumber
- Tanggal dicatat: 9 Okt 2026
- Apa: `ksei.py`, `kalender.py`, dan `sun.py` masing-masing punya percobaan-ulang unduhan yang
  hampir sama (`_buka` + `unduh` dengan jeda bertambah). Sekarang ada **tiga** salinan.
- Kenapa ditunda: ketiganya kecil (±20 baris), masing-masing milik adaptornya, dan menyatukannya
  berarti menyentuh tiga modul yang sudah terverifikasi atas sumber nyata — ongkosnya lebih besar
  daripada manfaatnya saat ini. Yang penting sudah dijaga: **tidak ada** aturan data yang
  diduplikasi, hanya mekanisme I/O-nya.
- Pemicu diangkat: saat adaptor keempat ditulis, atau saat salah satu perilaku unduhan perlu
  diubah (mis. kebijakan jeda baru) dan harus diubah di tiga tempat.
- Asal: `mejasaham/sun.py` (catatan di docstringnya), langkah 10

### Menyiapkan kerangka `fundamental.csv` dari semesta likuid
- Tanggal dicatat: 9 Okt 2026
- Apa: perintah yang menulis `fundamental.csv` berisi daftar kode emiten likuid dengan seluruh
  kolom angka **kosong** (bentuknya benar, isinya belum), supaya yang mengisi tidak perlu mengetik
  ±235 kode dan tidak salah eja.
- Kenapa ditunda: bentuk berkasnya sudah ada (template), dan yang menentukan apakah ini berguna
  adalah **berapa banyak emiten yang benar-benar akan diisi** — kalau hanya 20, mengetiknya lebih
  cepat daripada memeriksa kerangkanya. Menuliskan kerangka 235 baris juga mengundang godaan
  mengisinya dengan angka asal-asalan, dan itu justru yang paling berbahaya.
- Pemicu diangkat: setelah pengguna mencoba mengisi satu emiten secara manual dan menyatakan
  kerangkanya menolong.
- Asal: permintaan pengguna 9 Okt 2026 ("cari atau bikin berkas yang dibutuhkan sendiri"),
  langkah 10
- **Catatan 17 Okt 2026:** kerangka untuk **berkas lain** — `rasio-bank.csv` — justru **diangkat
  menjadi keputusan (K57)**, dan itu **tidak** berarti kerangka `fundamental.csv` ikut diangkat.
  Alasannya berbeda dan disengaja: daftar bank hanya **49 kode** dari 916 (mudah salah eja, dan
  seluruh sektor keuangan hilang dari peringkat tanpa datanya), sedangkan fundamental menyangkut
  ratusan emiten yang isinya jauh lebih panjang — di situ kerangka kosong lebih mengundang diisi
  angka asal-asalan. Pemicu di atas tetap berlaku untuk fundamental.

### Metrik khusus bank syariah (NPF, NOM/Net Imbalan) sebagai kolom sendiri
- Tanggal dicatat: 19 Okt 2026
- Apa: kolom tersendiri untuk ukuran yang **diterbitkan** bank syariah — **NPF gross** (bukan NPL) dan
  **Net Imbalan**/**NOM** (bukan NIM) — beserta kriteria saringnya sendiri, supaya bank syariah
  (mis. BRIS) tidak hanya dinilai dari CAR dan BOPO.
- Kenapa ditunda: PRD 8.4 menetapkan NPL/CAR/BOPO/NIM untuk bank, dan NPF bukan NPL (definisi &
  penyebutnya berbeda). Memetakannya diam-diam ke kolom NPL/NIM akan mengubah arti ambang tanpa
  jejak, jadi untuk v0.1 keduanya dibiarkan **"tidak dihitung" beserta alasannya** (**K77**). Kolom
  baru menuntut perubahan skema, preset, dan arti skor — itu keputusan produk, bukan tambalan.
- Pemicu diangkat: ketika bank syariah benar-benar dipertimbangkan masuk peringkat (mis. setelah
  rasio bank terisi untuk cukup banyak bank), **atau** bila PRD merevisi kriteria bank.
- Asal: pilot #21b (sesi 25–26), **K77**, `docs/rasio-bank-kandidat-2026-10.md`

Format entri:

```markdown
### <judul singkat>
- Tanggal dicatat: <tanggal>
- Apa: <satu-dua kalimat>
- Kenapa ditunda: <alasan jujur, bukan "nanti saja">
- Pemicu diangkat: <kondisi terukur yang membuatnya layak>
- Asal: <percakapan/keputusan/berkas>
```
