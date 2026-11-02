# Lanjutan Kerja — titik masuk untuk sesi berikutnya

**Berkas ini turunan, bukan acuan.** Isinya ringkasan keadaan + aksi berikutnya, supaya sesi baru
tidak perlu menebak. Kalau ada yang berbeda dengan sumber kebenaran, yang berlaku urutan ini:
`PRD-Screener-Saham-IDX-v1.3.docx` → `docs/keputusan.md` → `docs/arsitektur.md` → berkas ini.
**Perbarui berkas ini di akhir setiap tahap**, bersama catatan di `docs/keputusan.md` bagian 5.

Terakhir diperbarui: **03 Nov 2026 — perbaikan dependensi dan regenerasi publikasi.**

**Perbaikan dependensi (03 Nov 2026, disetujui pengguna):** certifi **2026.10.19**,
setuptools **84.1.0**, python-docx **1.2.0** terpasang; paket lain tetap. Lock kini **32 paket**;
`requirements.txt` memuat constraint lock, diwarisi requirements-dev, sehingga pemasangan
biasa memakai versi teruji. Setuptools diminta sebagai tooling dev; python-docx sudah
tercakup. **Verifikasi:** audit PyPI/OSV lock 32 paket + PyPI lingkungan 44 paket semuanya
exit 0, `No known vulnerabilities found`, tanpa paket dilewati; `pip check` bersih.
Root `emSign ECC Root CA - G3` terbukti tidak ada di trust store certifi; HTTPS requests
serta curl_cffi ke PyPI lulus dengan TLS aktif. Ekstraksi PRD lulus (700 baris, 31 tabel).
Dari akar salinan publikasi, `..\..\..\.venv\Scripts\python -m pytest` → **1.125 lulus,
94,29 detik**. **Dikerjakan:** instalasi melalui requirements-dev, pin transitive/dev,
laporan audit diperbarui; salinan dan ZIP publikasi diregenerasi dengan **131 berkas**,
satu commit publik nonpribadi. Bukti `.tmp/perbaikan-dependensi-20261103/`.
**Cara menjalankan:** `python -m pip install -r requirements-dev.txt` menggunakan interpreter
`.venv`, lalu perintah audit pada `docs/audit-dependensi-2026-11-03.md`.
**Belum:** push GitHub, audit native/OS/pengaturan GitHub, hash artefak lock.
**Berikutnya:** tinjau hasil, gunakan ZIP terbaru atau salinan untuk publikasi; jangan
push riwayat asli. Data kerja tidak diubah; perubahan repositori asli belum di-commit.
Tahap perbaikan berhenti sesuai K4. Catatan audit gagal di bawah adalah riwayat awal.

**Audit dependensi (03 Nov 2026):** laporan `docs/audit-dependensi-2026-11-03.md`.
Pip-audit 2.10.1 terisolasi melalui uv: 31 paket lock via PyPI dan OSV, 43 paket lingkungan
via PyPI; semua menghasilkan exit 1, `Found 3 known vulnerabilities in 2 packages`.
Setelah duplikasi certifi dihapus: **dua kerentanan unik** — certifi 2026.7.22 **kritis**
(GHSA-6q48-6c7w-9gw2; runtime yfinance → requests/curl_cffi → certifi), setuptools 84.0.0
**rendah** (GHSA-xmj3-9gf7-h52w; tooling instalasi legacy Windows). Tidak ada paket dilewati.
Versi perbaikan 2026.10.19 / 84.1.0 tersedia di PyPI, **belum dipasang**. `python-docx`
belum dipin/di-lock dan tidak terpasang; kelengkapan audit dev belum tertutup.
**Tes:** `.\.venv\Scripts\python -m pytest` → **1.125 lulus, 144,12 detik**;
`python -m pip check` → `No broken requirements found.`. Tes lulus bukan audit keamanan lulus.
**Dikerjakan:** inventaris, graf runtime 24 paket, dua feed advisory, verifikasi relevansi
lokal, laporan dan bukti `.tmp/audit-dependensi-20261103/`. Dependensi/kode/data tidak diubah.
**Belum:** perbaikan versi, dev lock lengkap, audit native/OS dan konfigurasi GitHub;
salinan publikasi/ZIP masih memakai lock rentan. **Berikutnya:** tinjau laporan (K4), lalu
perbaikan dua paket + dev lock → audit/tes ulang → regenerasi salinan/ZIP sebelum distribusi.
**Cara mengulang:** perintah audit terpin dan tes di laporan; `--no-deps --disable-pip`
mengaudit versi lock tanpa memasang target. Temuan mentah tiga bukan tiga kerentanan unik.

**Persiapan publikasi disetujui pengguna (03 Nov 2026):** MIT dipilih; LICENSE dan
`docs/publikasi.md` ditambahkan. Nama/jalur pengguna lokal disamarkan pada dokumen; ignore
kredensial, private key, SQLite, konfigurasi aktif, dan `.claude/` diperkuat. Salinan
`.tmp/publikasi-20261103/MejaSaham` berisi 130 berkas, satu commit awal dengan identitas
nonpribadi; ZIP sumber di `.tmp/publikasi-20261103/MejaSaham-publikasi.zip` tanpa `.git`.
Riwayat asli 129 commit tetap lokal dan **masih memuat email pribadi**: gunakan salinan
untuk publikasi, jangan push/merge riwayat asli. Draf PACK manual dengan rujukan KSEI
ikut; basis data, transaksi, PDF sumber, unduhan vendor dan arsip snapshot tidak ikut.
**Verifikasi:** 11 calon berkas privat diabaikan, 6 contoh/kode tetap diizinkan;
pemindaian 130 berkas tidak menemukan pola token/private key, nama pengguna lokal, atau
email commit lama. Kode, tes, dependensi salinan identik dengan working tree.
Pemeriksaan commit awal juga merapikan baris kosong EOF warisan pada tujuh berkas;
AST tiga modul Python identik sebelum/sesudah perapian (tidak mengubah perilaku).
Dari akar salinan, `..\..\..\.venv\Scripts\python -m pytest` → **1.125 lulus, 126,28 detik**.
**Belum:** pembuatan repositori/push GitHub, audit kerentanan dependensi, dan pengaturan
keamanan akun/repositori GitHub. **Berikutnya:** tinjau salinan/ZIP, lalu ikuti
`docs/publikasi.md` untuk unggah dari salinan. Perilaku aplikasi dan data kerja tidak berubah;
perubahan dokumentasi di repositori asli belum di-commit. Tahap persiapan berhenti sesuai K4.

**Pemeriksaan publikasi GitHub (03 Nov 2026):** pemeriksaan lokal, belum memublikasikan atau mengubah
riwayat Git. Pemindaian pola kredensial pada 894 blob dalam 129 commit (`git rev-list --objects --all`
+ `git cat-file --batch`) tidak menemukan kandidat; ini bukan jaminan bebas rahasia. Tidak ditemukan
berkas basis data atau private key dalam daftar berkas historis yang diperiksa. Temuan: email Gmail
penulis pada metadata commit; jalur pengguna pada dokumen; `.gitignore` belum mengabaikan `.env`,
private key, atau CSV konfigurasi aktif; belum ada LICENSE. Dasbor memiliki pembatasan loopback,
Host, Origin, dan CSRF (`mejasaham/web/server.py`). **Tes:** `.\.venv\Scripts\python -m pytest` →
**1.125 lulus, 100,16 detik**. **Belum:** perapian publikasi, pemilihan lisensi, pemindaian rahasia
khusus, audit kerentanan dependensi, pemeriksaan pengaturan/artefak GitHub jarak jauh.
**Berikutnya:** tinjau temuan dengan pengguna sebelum perubahan persiapan publikasi (K4).
**Cara mengulang:** periksa `git ls-files`, riwayat semua ref lokal, `git check-ignore` untuk calon
berkas sensitif, dan jalankan perintah tes di atas. `RTK.md` yang dirujuk instruksi tidak ditemukan
di akar repositori maupun dua direktori induk yang diperiksa. Kode aplikasi dan data kerja tidak diubah.

**Terbaru — sesi 75 (pengguna: “kasih link tempat downloadnya”):** kartu "Pengumuman suspensi & UMA IDX (PDF)" di
`/berkas` kini menautkan `pengumuman_idx.ALAMAT_PENGUMUMAN` (`https://www.idx.id/id/berita/pengumuman`, K102 — konstanta
yang sudah dipakai `jadwal.py`), sama seperti kartu Notasi Khusus dan Ringkasan Saham. Uji
`test_unggah_pdf_pengumuman_langsung_ke_konfirmasi_lalu_menulis` memeriksa `href`-nya (terbukti gagal tanpa perubahan).
Rasio bank manual dan ukur ulang 9 bank terhalang **ditunda atas permintaan pengguna**.

**Terbaru — sesi 74 (pengguna: “dua duanya” = ukur ulang INPC/SDRA + percepat detail emiten):** tanpa perubahan kode,
basis data kerja tidak ditulis. (1) **INPC/SDRA masih "tidak terukur — jaringan"** (`.uji-data/uji-g6/ukur-ulang.py`,
3 percobaan × 3 URL, bukti `.uji-data/uji-g6/bukti/ukur-ulang.txt`): INPC `bankarthagraha.co.id` connect timeout 3/3 di
https dan http, `www.` tidak ada di DNS; SDRA `bankwoorisaudara.com` (dan `www.`) `CERTIFICATE_VERIFY_FAILED: unable to
get local issuer certificate` 3/3 — kemungkinan rantai sertifikat tak lengkap di server, **tidak** diakali dengan mematikan
verifikasi — http timeout 3/3. Tidak ada gelombang 6. (2) **"Sisa ±30 dtk detail emiten" (sesi 67) ternyata sudah
ditutup T99** (`fb76284`, `mejasaham/web/simpanan.py`); catatan sesi 67 di bawah basi dan kini ditandai. Diukur ulang atas
salinan baca-saja `.tmp/uji-sesi74` (backup API, `integrity_check` ok), satu `SimpananPotret` bersama: detail AUTO
**29,5 dtk** (muat potret pertama) → BBCA **2,7 dtk** → AUTO lagi **2,1 dtk**, skor sama (55,7).
`tests/test_simpanan_potret.py` + `tests/test_web.py` **60 lulus**. Yang tersisa hanya muat pertama per snapshot (±28 dtk)
= opsi (b) yang ditolak T99. **Berikutnya:** tidak ada pekerjaan rasio bank otomatis; 8 bank manual hanya bila pengguna
menaruh PDF di `.uji-data/riset-idx/rasio-bank/pdf/manual/`.

**Terbaru — sesi 73, gelombang 5:** 4 bank otomatis sebagai **kandidat** (sasaran 5; hanya 4 yang bisa dicari tanpa
menebak/memaksa): **BBKP** 15,82/9,99/96,68/1,96 (30 Jun, diaudit; **18 Sep**) · **BTPN** 29,27/1,49/88,45/3,78 (30 Jun;
31 Jul; domain `smbci.com`; poster tanpa angka di lapisan teks — render saja) · **PNBS** 16,61/—/93,72/— (30 Sep; 28 Okt;
syariah, NPF/NI tidak diisi menurut K77) · **BSWD** 83,52/4,93/71,11/4,18 (30 Sep; 29 Okt) — urutan KPMM/NPL gross/BOPO/NIM,
dibaca dari render. Semua tanggal = tanda tangan (tak satu pun melewati ambang 7 hari K105b). `uji-baca-kandidat.py`
**LULUS 26 baris**. Basis data kerja, `konfigurasi/`, kode aplikasi **tidak disentuh** (suite tidak dijalankan — tidak ada
perubahan kode). Tidak ada pertanyaan keputusan baru (U42 tidak dibuat). Dilewati: BJBR (masih "Under Maintenance"),
MASB (tab triwulan hanya berisi laporan tahunan), BBHI (situs tanpa halaman investor), BGTG (tombol "Unduh" → API 401),
BABP (halaman uji Red Hat), PNBN (403), MCOR (SSL), BKSW/BMAS (robots HTML). **Jebakan:** URL unduhan PNBS adalah token
terenkripsi yang berubah tiap muat halaman — diuji: token lama & baru memberi berkas identik (sha `6795ee2d…`); render
halaman penuh PNBS gelap (latar transparan), baca dari `potong-pdf.py`. Rincian `docs/rasio-bank-kandidat-2026-10.md` §15.
Sisa 9 bank otomatis semuanya terhalang (§15.3).
**Lanjutan (pengguna: “Ya, verifikasi”):** `.uji-data/uji-g5/verifikasi.py` → **seluruh sel cocok persis** (keluar 0; unduh
ulang identik, termasuk token PNBS; PNBS NPL/NIM kosong sesuai K77; dasar tanggal dihitung ulang dari `Last-Modified`;
poster BTPN/PNBS dirender ulang dan dibaca lagi; bukti `.uji-data/uji-g5/bukti/`).
**Lanjutan (pengguna: “Ya, impor”):** 4 baris ditambah ke `.uji-data/mejasaham/konfigurasi/rasio-bank.csv` (sha256
`d02e3688…` → `10dc5ef3…`), cadangan `.uji-data\mejasaham-cadangan\20261030T010531573049+0700`, `--impor` jalur absolut →
**snapshot 29**, **4 baris baru**, `rasio_bank` **22 → 26**, `notasi_khusus` tetap, `integrity_check` ok, laporan mutu sama.
`--saring`: **tidak berubah** (4 lolos; AUTO/PTBA/ERAA/LSIP; "tidak bisa disaring" tetap 878 — keempat bank belum punya
fundamental); kriteria bank dipakai untuk keempatnya (BSWD lolos keempatnya; PNBS NPL/NIM tidak dihitung menurut K77), tetapi
semuanya juga gagal ADTV20 (K68 tetap). **Jebakan:** keluaran CLI yang dialihkan dari Git Bash berpengodean konsol — pakai
`PYTHONIOENCODING=utf-8`. Rincian `docs/rasio-bank-kandidat-2026-10.md` §15.4. **Berikutnya:** sudah di-commit `faf6a46`;
sisa 9 bank otomatis terhalang (§15.3).

**Sesi 72, gelombang 4 (pengguna: “Lanjut”):** 5 bank otomatis sebagai **kandidat** (berhenti sebelum
verifikasi ulang & impor): **ARTO** 27,54/0,87/89,53/8,60 (30 Sep; 28 Okt) · **BANK** 38,43/—/95,80/— (30 Sep; 26 Okt;
syariah, NPF/NI tidak diisi menurut K77) · **BBYB** 50,23/2,99/82,31/13,92 (30 Jun; 30 Jul) · **BSIM** 30,03/1,62/93,54/3,28
(30 Jun; **27 Okt** — tanda tangan 31 Jul, `Last-Modified` 88 hari kemudian, K105(b) harfiah seperti BINA/K106) · **BBSI**
36,84/3,04/91,13/19,10 (30 Jun; 31 Jul; domain kini `krom.id`) — urutan KPMM/NPL gross/BOPO/NIM, dibaca dari render.
`uji-baca-kandidat.py` **LULUS 22 baris**. Basis data kerja, `konfigurasi/`, kode aplikasi **tidak disentuh** (suite tidak
dijalankan — tidak ada perubahan kode). Tidak ada pertanyaan keputusan baru (K77/K105/K106/K107 menutup semua kasus).
Dilewati: BGTG (API unduh membalas 401), BABP (situs = halaman uji Red Hat), BBHI (robots gagal), BMAS/BSWD (halaman
publikasi belum tampak). **Jebakan:** `baca-pdf.py`/`potong-pdf.py` menafsirkan jalur PDF relatif terhadap folder
rasio-bank — beri `pdf/<nama>.pdf`, bukan jalur dari akar repo. Rincian `docs/rasio-bank-kandidat-2026-10.md` §14.
**Berikutnya:** tinjauan → verifikasi ulang K83 (salin `.uji-data/uji-g3/verifikasi.py` ke `uji-g4`) → cadangan →
`--impor` jalur absolut; lalu gelombang 5 (13 bank otomatis tersisa).
**Lanjutan (pengguna: “Ya, verifikasi”):** `.uji-data/uji-g4/verifikasi.py` → **seluruh sel cocok persis** (keluar 0; unduh
ulang identik; BANK NPL/NIM kosong sesuai K77; BSIM 27 Okt dihitung ulang dari `Last-Modified`; poster ARTO/BANK/BSIM
dirender ulang dan dibaca lagi; bukti `.uji-data/uji-g4/bukti/`). **Belum diimpor** — menunggu persetujuan: 5 baris ke
`.uji-data/mejasaham/konfigurasi/rasio-bank.csv` → cadangan → `--impor` jalur absolut → `v_rasio_bank_terkini` + `--saring`.
**Lanjutan (pengguna: “Ya, impor”):** 5 baris ditambah ke `.uji-data/mejasaham/konfigurasi/rasio-bank.csv` (sha256
`4f9beba8…` → `d02e3688…`), cadangan `.uji-data\mejasaham-cadangan\20261030T004151722246+0700`, `--impor` jalur absolut →
**snapshot 28**, **5 baris baru**, `rasio_bank` **17 → 22**, `notasi_khusus` tetap, `integrity_check` ok. `--saring`: **tidak
berubah** (4 lolos; AUTO/PTBA/ERAA/LSIP; "tidak bisa disaring" 880 → 878); kriteria bank dipakai untuk kelimanya (BBYB lolos
keempatnya; BANK NPL/NIM tidak dihitung menurut K77), tetapi semuanya juga gagal MA200 (K68 tetap). Rincian
`docs/rasio-bank-kandidat-2026-10.md` §14.4. **Berikutnya:** gelombang 5 (13 bank otomatis tersisa; sudah di-commit `6575491`).

**Terbaru — sesi 71, gelombang 3:** 5 bank otomatis sebagai **kandidat** (berhenti sebelum impor), semuanya posisi
30 Jun 2026: **BNII** 21,97/2,21/92,83/3,16 (set individual; 30 Jul) · **NOBU** 23,04/0,53/75,87/3,53 (31 Jul) ·
**MAYA** 11,07/4,02/98,93/2,31 (31 Jul) · **AMAR** 89,86/8,96/84,17/21,91 (30 Jul) · **BNBA** 71,54/5,29/86,31/4,11
(31 Jul) — urutan KPMM/NPL gross/BOPO/NIM, dibaca dari render (MAYA tanpa angka di lapisan teks, BNBA pindaian).
`uji-baca-kandidat.py` **LULUS 17 baris**. Basis data kerja, `konfigurasi/`, kode aplikasi **tidak disentuh** (suite
tidak dijalankan — tidak ada perubahan kode). **Butuh keputusan U41:** (a) domain K79 keliru untuk PNBN/NOBU/MCOR/MAYA/BTPN
(Nobu = `nobubank.com`, Panin = `panin.co.id` 403, `bankccb.com` = bank AS, Mayapada = `bankmayapada.com`); (b) BNII/AMAR
tanda tangan 30 Jul tetapi berkas 31 Jul — tetap K105(b)? Dilewati: BJBR (masih "Under Maintenance"), PNBN (403), BTPN
(domain belum ditemukan). **Jebakan:** Git Bash mengubah argumen berawalan `/` jadi jalur Windows (`sed -n '/pola/,…'`
rusak) — pakai `grep -A`; `cek-robots.py`/`unduh.py` mengimpor `_buka` dari foldernya, jadi jangan dijalankan dengan
`python -I`. Rincian `docs/rasio-bank-kandidat-2026-10.md` §13. **Berikutnya:** tinjauan + U41 → verifikasi ulang K83
(salin pola `.uji-data/uji-g2/verifikasi.py` ke `uji-g3`) → cadangan → `--impor` jalur absolut; lalu gelombang 4 (18 bank).
**Lanjutan (pengguna: “Setuju U41”) — K107:** domain K79 dikoreksi secara tercatat (§13.2, tanpa ukur ulang 44 bank);
BNII/AMAR tetap 30 Jul (K105b). Verifikasi ulang K83 `.uji-data/uji-g3/verifikasi.py` → **seluruh sel cocok persis**
(keluar 0; unduh ulang identik; MAYA dan BNBA dirender ulang dan dibaca lagi; bukti `.uji-data/uji-g3/bukti/`).
**Belum diimpor** — menunggu persetujuan: 5 baris ke `.uji-data/mejasaham/konfigurasi/rasio-bank.csv` → cadangan →
`--impor` jalur absolut → `v_rasio_bank_terkini` + `--saring`.
**Lanjutan (pengguna: “Ya, impor”):** 5 baris ditambah ke `.uji-data/mejasaham/konfigurasi/rasio-bank.csv` (sha256
`8b597b32…` → `4f9beba8…`), cadangan `.uji-data\mejasaham-cadangan\20261030T001317283479+0700`, `--impor` jalur absolut →
**snapshot 27**, **5 baris baru**, `rasio_bank` **12 → 17**, `notasi_khusus` tetap, `integrity_check` ok. Laporan mutu baru
memuat catatan `snapshot_basi` (impor lewat tengah malam; hari bursa 30 Okt belum ada datanya). `--saring`: **tidak berubah**
(4 lolos; AUTO/PTBA/ERAA/LSIP); kriteria bank dipakai untuk kelimanya (NOBU lolos keempatnya, MAYA gagal keempatnya), tetapi
semuanya juga gagal ADTV20 dan MA200 (K68 tetap). Rincian `docs/rasio-bank-kandidat-2026-10.md` §13.4. **Berikutnya:**
commit; gelombang 4 (18 bank otomatis tersisa; pakai domain terkoreksi §13.2).

**Sesi 70, gelombang 2 (pengguna: “Lanjut gelombang 2”):** 5 bank otomatis sebagai **kandidat**
(berhenti sebelum impor): **NISP** 22,95/1,86/67,89/3,93 (30 Jun) · **BVIC** 22,07/3,36/92,90/2,47 (30 Sep) ·
**BCIC** 14,53/2,78/94,00/2,11 (30 Jun) · **AGRO** 42,35/2,53/98,59/5,83 (30 Sep) · **BINA** 15,26/4,11/92,04/2,36
(30 Jun) — urutan KPMM/NPL gross/BOPO/NIM, dibaca dari render. `uji-baca-kandidat.py` **LULUS 12 baris** (nilai bp
kelima bank baru kini ikut diperiksa). Basis data kerja, `konfigurasi/`, dan kode aplikasi **tidak disentuh**
(suite tidak dijalankan — tidak ada perubahan kode). **Butuh keputusan U40** (`tgl_publikasi`): (a) NISP/BCIC tanpa
tanggal tercetak → bukti terbit paling akhir (30 Jul / 11 Agu); (b) BINA `Last-Modified` 28 Okt jauh sesudah
tanda tangan 29 Jul → K105(b) harfiah (28 Okt). Dilewati: BJBR (situs "Under Maintenance"), PNBN/NOBU (domain
membalas pengalih `/lander`), BTPN (robots berisi HTML), BNII (SSL). **Jebakan:** katalog OCBC & Bank Raya
dirender JavaScript — URL berkas diambil lewat peramban (OCBC: API `ODocuments/DocumentList`; Bank Raya:
`/report-download/<id>`). Rincian `docs/rasio-bank-kandidat-2026-10.md` §12. **Berikutnya:** tinjauan + U40 →
verifikasi ulang K83 (pola `.uji-data/uji-g1/verifikasi.py`) → cadangan → `--impor` jalur absolut; lalu gelombang 3
(23 bank otomatis tersisa).
**Lanjutan (pengguna: “Setuju U40”) — K106:** tanggal kandidat tetap (NISP 30 Jul, BCIC 11 Agu, BINA 28 Okt).
Verifikasi ulang K83 `.uji-data/uji-g2/verifikasi.py` → **seluruh sel cocok persis** (keluar 0; unduh ulang identik;
BVIC dirender ulang dan dibaca lagi; bukti `.uji-data/uji-g2/bukti/`). **Belum diimpor** — menunggu persetujuan:
5 baris ke `.uji-data/mejasaham/konfigurasi/rasio-bank.csv` → cadangan → `--impor` jalur absolut → `v_rasio_bank_terkini`
+ `--saring`.
**Lanjutan (pengguna: “Ya, impor”):** 5 baris ditambah ke `.uji-data/mejasaham/konfigurasi/rasio-bank.csv`, cadangan
`.uji-data\mejasaham-cadangan\20261029T234828321761+0700`, `--impor` jalur absolut → **snapshot 26**, **5 baris baru** (tanpa
efek samping `notasi_khusus` — T101 bekerja), `rasio_bank` **7 → 12**, `integrity_check` ok. `--saring`: **tidak berubah**
(4 lolos; AUTO/PTBA/ERAA/LSIP); kriteria bank dipakai untuk kelimanya (NISP lolos keempatnya), tetapi semuanya juga gagal
MA200 dan kriteria lain (K68 tetap). Rincian `docs/rasio-bank-kandidat-2026-10.md` §12.4. **Berikutnya:**
gelombang 3 (23 bank otomatis tersisa).

**Sesi 70 (pengguna: “Lanjut” = tahap 3 dari 3, 44 bank; K88 dicabut):** T100 sudah di-commit
(`3a9f4cb`). Gelombang 1 = **5 bank otomatis** sebagai **kandidat** (pola pilot K76, berhenti sebelum impor):
**BEKS** 33,73/4,51/91,47/3,19 (30 Jun) · **MEGA** 25,03/1,56/72,65/4,36 (30 Jun) · **BNGA** 23,00/1,42/75,47/3,56
(30 Sep) · **BDMN** 21,69/1,60/78,06/4,27 (30 Sep) · **BJTM** 23,72/4,38/82,14/5,90 (30 Jun) — urutan KPMM/NPL
gross/BOPO/NIM, dibaca dari render. QNB (BKSW) dilewati: robots.txt-nya halaman "Access Denied". `uji-baca-kandidat.py`
**LULUS 7 baris**; basis data kerja, `konfigurasi/`, dan kode aplikasi **tidak disentuh** (suite tidak dijalankan
ulang — tidak ada perubahan kode; terakhir 1.123 lulus). **Butuh keputusan U39** (`docs/keputusan.md`): (a) set
Bank/individual vs konsolidasian (kandidat memakai Bank), (b) `tgl_publikasi` BEKS: tanda tangan 27 Jul vs unggahan
14 Agu, (c) keluarkan PNLF (induk asuransi) dari sasaran. Alat baru `cek-robots.py` (RFC 9309), `potong-pdf.py` kini
berlatar putih. Rincian `docs/rasio-bank-kandidat-2026-10.md` §11. **Berikutnya:** tinjauan + U39 → verifikasi
ulang K83 atas 5 kandidat → cadangan → impor; lalu gelombang 2 (29 bank otomatis tersisa, 5 per gelombang).
**Lanjutan (pengguna: “Setuju U39”) — K105:** basis = set Bank/individual; `tgl_publikasi` = tanggal tercetak
kecuali unggahan > 7 hari sesudahnya (BEKS kini **14 Agu 2026**); PNLF keluar dari sasaran (otomatis tinggal **28**).
Verifikasi ulang K83 `.uji-data/uji-g1/verifikasi.py` → **seluruh sel cocok persis** (keluar 0; bukti
`.uji-data/uji-g1/bukti/`). **Belum diimpor** — menunggu persetujuan: `konfigurasi/rasio-bank.csv` → cadangan →
`--impor` ke `.uji-data/mejasaham` → `v_rasio_bank_terkini` + `--saring`.
**Lanjutan (pengguna: “Ya, impor”):** 5 baris ditambah ke `.uji-data/mejasaham/konfigurasi/rasio-bank.csv`, cadangan
`.uji-data\mejasaham-cadangan\20261029T211841800910+0700`, `--impor` → **snapshot 25**, `rasio_bank` **2 → 7**,
`integrity_check` ok. `--saring`: **tidak berubah** (4 lolos; AUTO/PTBA/ERAA/LSIP) — kriteria bank dipakai untuk
kelimanya, tetapi tak satu pun tertahan hanya oleh rasio bank (K68). **Jebakan baru:** 171 baris `notasi_khusus`
ikut tertulis, isinya identik, hanya label `sumber` — `--impor` diberi jalur **relatif**, refresh memakai jalur
**absolut** (T88), dan sejak T100 keduanya dianggap dua sumber. **Pakai jalur absolut** untuk `--impor` folder
konfigurasi kerja (atau perbaiki: `--impor` menormalkan foldernya ke absolut sebelum membuat label). Rincian
`docs/rasio-bank-kandidat-2026-10.md` §11.5. **Berikutnya:** commit; gelombang 2 (28 bank otomatis).
**Lanjutan (pengguna: “Perbaiki label --impor”) — T101:** `berkas.baca_folder` kini membentuk label dari
`folder.resolve()`, dan dialog konfirmasi menampilkan label hasil bacaan itu; jebakan jalur relatif di atas sudah
tertutup. **Test:** suite **1.125 lulus (140 dtk)**; +2 `tests/test_impor_berkas.py`, keduanya gagal di kode lama.
171 revisi berlabel relatif di data kerja dibiarkan (append-only). **Berikutnya:** commit; gelombang 2 (28 bank).

**Sesi 69 (pengguna memilih ketiganya: impor Ringkasan Saham, uji jalan, 44 bank), tahap 1 dari 3:**
tanpa perubahan kode. Suite **1.117 lulus (80 dtk)**. **Impor:** satu-satunya berkas, `Downloads\Ringkasan
Saham-20261029.xlsx`, sudah ada di basis data (3.852 bar IDX s/d 29 Okt, snapshot #24) — tidak ada yang diimpor.
**Uji jalan** atas salinan baca-saja `.tmp/uji-sesi69` (backup API, `integrity_check` ok; launch `uji-sesi69`,
port 8771): dasbor, Impor & cadangan, jurnal, kalkulator risiko. **Temuan (belum diperbaiki):**
(1) **Cacat data — T90 tidak menutup lubang sendiri.** Revisi IHSG/LQ45 28 Okt ber-`close` kosong (29 Okt
02.24, sebelum T90) masih "terkini", sehingga dasbor menulis `IHSG 5.098 · -168 (-3,19%)` = selisih terhadap
**27 Okt** (5.266), bukan 28 Okt (5.282 → -184, -3,48%), tanpa menyebut tanggal pembandingnya. T90 menyatakan
lubang itu "tertutup sendiri begitu sumber mengirim nilai penuh" — **keliru**: `ingesti._tulis_baris`
membandingkan sidik dengan **semua** revisi, bukan yang terkini, jadi 5.282 yang dikirim ulang dicatat `tetap`.
Terbukti atas salinan kedua `.tmp/uji-sesi69-tutup` (`HasilTulis(tetap={'harga_indeks': 1})`, terkini tetap
NULL). Akibat umumnya: koreksi balik A→B→A di tabel mana pun hilang diam-diam. **Butuh keputusan:** bandingkan
dengan revisi terkini (per kunci alami, mungkin per `sumber` — `harga_harian` punya dua sumber per kunci, jadi
"terkini saja" bisa memicu revisi bolak-balik tiap refresh), lalu IHSG 28 Okt pulih lewat refresh/impor
berikutnya; dan/atau `konteks_pasar.BarisIndeks.ringkas` menyebut tanggal pembanding bila bukan hari bursa
sebelumnya. (2) Jadwal "Cek sumber kedua" menulis `cek lengkap terakhir 2026-10-29T19:01:32+07:00` (ISO,
AGENTS §4) — `mejasaham/jadwal.py:249`. (3) Jadwal harga menulis "Ringkasan Saham IDX Ringkasan Saham (unduhan
…)" — `jadwal.py:113` menambah "Ringkasan Saham" di depan label yang sudah memuatnya. (4) Rekap jurnal di web
menyuruh `--catat-transaksi`, padahal web punya formulirnya di Detail emiten (`jurnal.py:396`).
**Lanjutan (pengguna: “Terkini per sumber”), keempatnya diperbaiki — T100:** (1) `ingesti._tulis_baris` kini
menganggap baris "sudah ada" hanya bila sama dengan **revisi terkini dari sumber yang sama** untuk kunci alaminya;
`konteks_pasar.BarisIndeks` membawa `tanggal_sebelumnya` (**migrasi 018**, `VERSI_HITUNG` `pasar-2`) dan menulis
"… terhadap 28 Okt 2026". (2) "cek lengkap terakhir 29 Okt 2026, …". (3) label harga resmi tidak lagi dobel.
(4) rekap jurnal menyebut `--catat-transaksi` **atau** formulir Catat transaksi di Detail emiten. **Test:** suite
**1.123 lulus (73 dtk)**; +3 `tests/test_ingesti.py` (2 gagal di kode lama; yang ketiga menjaga dua sumber
bergantian tidak menumpuk revisi), +1 `tests/test_konteks_pasar.py`, +1 `tests/test_jadwal.py`, +1
`tests/test_jurnal.py`, 1 uji jadwal diperketat — semua uji baru (selain penjaga dua sumber) gagal di kode lama.
**Bukti** atas salinan `.tmp/uji-sesi69-tutup` (sudah bermigrasi ke 18): kirim ulang IHSG/LQ45 28 Okt →
`baru={harga_indeks: 2}`; `--dasbor` → `IHSG 5.098 (29 Okt 2026) · -184 (-3,48%) terhadap 28 Okt 2026`, kandidat
sama (AUTO 55,7 · PTBA 54,1 · ERAA 53,9 · LSIP 53,5). **Data kerja `.uji-data/mejasaham` tidak disentuh:** migrasi
018 berjalan saat aplikasi berikutnya dibuka (cadangan sebelum migrasi otomatis), lubang IHSG 28 Okt tertutup pada
refresh berikutnya (`periode="5y"` mengirim ulang bar itu), dan konteks pasar `pasar-1` dihitung ulang oleh
`--saring` berikutnya. Rincian `docs/arsitektur.md` T100, `docs/skema-data.md` 5.19.
**Berikutnya:** tinjauan pengguna (K4) + commit; lalu tahap 3 dari 3 (44 bank, mencabut penundaan K88: 34 bank
otomatis dulu, `docs/rasio-bank-kandidat-2026-10.md` §10).

**Terbaru — sesi 67 (pengguna: “testing aplikasinya”), uji jalan dasbor web:** suite **1.105 lulus (73 dtk)**.
Dasbor atas salinan data kerja `.tmp/uji-sesi67` (salin baca-saja, `integrity_check` ok; launch `uji-sesi67`,
port 8770) ditelusuri keenam layarnya: dasbor, screener (momentum/v1 dijalankan, ±55 dtk, 20 kandidat),
detail AUTO, kalkulator risiko (menolak tanpa watchlist — sesuai K56), jurnal, impor & cadangan (cadangan
lewat konfirmasi → `.tmp/uji-sesi67-cadangan`). **Temuan (belum diperbaiki):** (1) detail emiten bagian Skor
menampilkan JSON `penjelasan` mentah dan skor bertitik desimal `55.7` (`web/server.py` `ringkas_skor`,
warisan T65; melanggar AGENTS §4); (2) kalimat "Pemulihan TIDAK ada di jendela ini…" tampil dua kali di
Impor & cadangan dan masih menyebut jendela yang sudah dihapus (K91); (3) kepala tabel "Kandidat teratas
dari skor tersimpan" tidak menyebut preset — sesudah saringan momentum isinya berganti (MGLV 67,4) di
tempat yang sama dengan kualitas-nilai (AUTO 55,7), mudah dibandingkan lintas preset (aturan keras 9);
(4) detail satu emiten ±75 dtk. **Lanjutan (pengguna: “Ya, perbaiki 1–3”), ketiganya diperbaiki:** (1) detail
emiten kini menampilkan baris "Preset … · peringkat 1 · skor 55,7" + tabel faktor (`tabel.isi_faktor_skor`, baru)
dan metrik (`tabel.isi_metrik_skor`, sudah ada tetapi tak terpakai sejak K91); alasan metrik yang dihitung tidak
lagi mengulang angka berformat Inggris, yang tidak dihitung tetap tampil utuh. JSON `penjelasan` tetap disimpan,
tidak ditampilkan. (2) kalimat pemulihan sekali saja, tanpa "jendela ini". (3) kepala tabel dasbor "… dari skor
tersimpan (preset X, snapshot #N)" + "Skor hanya sebanding di dalam satu preset." **Test:** suite **1.107 lulus
(77 dtk)**; +2 `tests/test_layar_tabel.py`, 2 uji `tests/test_web.py` diperketat — keempatnya gagal di kode lama.
**Bukti** di peramban atas `.tmp/uji-sesi67`: detail AUTO angkanya sama dengan JSON lama (faktor 50,2 · 53,1 ·
61,0 · 63,3); kepala dasbor "(preset momentum/v1, snapshot #24)"; "Pemulihan TIDAK ada" 1×. Di-commit (`4e1f73a`).
**Lanjutan (pengguna: “Lanjut temuan 4”):** profil atas salinan: satu `potret.muat` ±19 dtk (±1 juta baris harga:
`fetchall` 12,8 dtk + `_harga` 7 dtk), `metrik_semua` ±9 dtk — dan detail memuat potret **dua kali** (sekali di
`_tugas_detail`, sekali di `pengatur.jalankan_saring`). Kini `jalankan_saring(bahan=)` menerima potret yang sudah
dimuat (bersama `id_snapshot`/`sumber` → `ValueError`, bukan diabaikan) dan detail mengirimnya. **Terukur**
`_tugas_detail('AUTO')` **52,0 → 29,8 dtk**, skor sama (55,7). **Test:** suite **1.110 lulus (62 dtk)**; +2
`tests/test_saring.py`, +1 `tests/test_web.py` (potret dimuat 1×; kode lama 2×) — ketiganya gagal di kode lama.
**Sisa ±30 dtk tidak dikerjakan** (butuh keputusan): (a) cache potret+metrik per `id_snapshot` di proses web —
detail berikutnya beberapa detik, tetapi memori ±1 juta bar dan aturan pembatalannya perlu dicatat sebagai T-baru;
atau (b) mempercepat kueri harga `potret.muat` — menyentuh jalur point-in-time semua modul. **Berikutnya:**
tinjauan pengguna (K4) + commit; putuskan (a)/(b)/biarkan. Di-commit (`c35a7bb`). **Ditutup: (a) dikerjakan sebagai
T99 (`fb76284`); diukur ulang sesi 74 — lihat atas.**
**Lanjutan (pengguna: “sesuai rekomendasi mu aja” → opsi a), T99:** `web/simpanan.SimpananPotret` (satu per
`Aplikasi`) menyimpan potret + metrik snapshot terakhir berkunci `(id_snapshot, batas_diketahui, versi_skema)`;
detail emiten dan screener memakainya lewat `jalankan_saring(bahan=, angka=)`. Rincian `docs/arsitektur.md` T99.
**Terukur** di peramban atas `.tmp/uji-sesi67`: dasbor 1,8 dtk · detail AUTO pertama 30,8 dtk (memuat) · detail
PTBA sesudahnya **2,1 dtk**; skor sama (AUTO 55,7 · PTBA 54,1). **Test:** suite **1.116 lulus (62 dtk)**; +5
`tests/test_simpanan_potret.py`, +1 `tests/test_saring.py`, uji web diperluas (detail + muat ulang + saringan →
1 muat; kode lama 3×). **Cacat lama ditemukan (belum diperbaiki):** `pengatur.jalankan_saring` menyaring `lolos`
ke `hanya_kode` **sebelum** `skor.skor_semesta` memberi peringkat, jadi detail emiten (web) dan `--saring --kode`
selalu menulis "peringkat 1" (PTBA tampil peringkat 1, padahal 2 di dasbor). Nilai skor benar (statistik dari
semesta likuid). Perbaikan usulan: peringkat dihitung atas seluruh `lolos`, lalu hasilnya disaring ke
`hanya_kode`. T99 di-commit (`fb76284`).
**Lanjutan (pengguna: “Commit + perbaiki”), peringkat `hanya_kode`:** `jalankan_saring` kini memberi peringkat atas
**seluruh** emiten lolos (`semua_lolos`), lalu menyaring skor ke `hanya_kode`; `jumlah_lolos` tetap dihitung atas
kode yang dilaporkan. Peringatan `--kode` kini "hanya melaporkan sebagian emiten" (bukan "peringkat parsial").
**Test:** suite **1.117 lulus (76 dtk)**; +1 `tests/test_saring.py` (8 emiten sintetis: CCCC peringkat 6 di
semesta, dulu 1 bila sendirian) — gagal di kode lama. **Bukti** di peramban atas `.tmp/uji-sesi67`, preset
kualitas-nilai/v1: AUTO 1 · PTBA 2 · ERAA 3 · LSIP 4, sama dengan skor tersimpan snapshot #24. **Di-commit
(`160945e`); sesi 68 memeriksa: tidak ada aksi agen yang menunggu** — antrean tersisa butuh keputusan/data
pengguna (sumber harga kedua 3.10, ekuitas begitu dana ada, 44 bank K88).

**Terbaru — sesi 66 lanjutan (pengguna: “dua duanya kerjain ampe selesai”), T98:** (1) kotak "Perlu
diperbarui" kini hanya menghitung berkas folder pantau yang **isinya** belum ada di basis data
(`layar.tulis.jumlah_belum_diimpor`, pemilahan sama dengan impornya) — Ringkasan Saham 29 Okt di Downloads
yang sudah diunggah tidak lagi disebut. (2) Setiap jalan impor folder pantau (CLI dan tombol dasbor,
sukses/gagal, termasuk "folder pantau belum diatur") dicatat di `log_jalan` proses `impor-unduhan`
(`folder_pantau.catat_jalan`); kotak menampilkan jalan terakhir yang gagal sampai ada jalan yang berhasil
(AC-9, K101 e). **Test:** suite **1.105 lulus (78 dtk)**; +2 `tests/test_folder_pantau.py`, +2
`tests/test_web.py`, 2 uji lama diperketat — keenamnya gagal di kode lama. **Bukti** atas salinan data
kerja `.tmp/uji-sesi66` (port 8770, `uji-sesi66` di `.claude/launch.json`): gagal → kotak "Impor unduhan IDX
— jalan terakhir gagal 29 Okt 2026 19.33: folder pantau … tidak ada"; berhasil atas folder kosong → kotak
hilang. Rincian `docs/arsitektur.md` T98. **Tidak ada celah tercatat yang tersisa dari sesi 65/66.**
**Di-commit (`ca3c4f8`); sesi 67 memeriksa: tidak ada aksi agen yang menunggu** — antrean tersisa butuh
keputusan/data pengguna (sumber harga kedua 3.10, ekuitas begitu dana ada, 44 bank K88). Berkas `Downloads\Ringkasan Saham-20261029.xlsx` masih di
Downloads (tidak disentuh); boleh dihapus atau dirapikan lewat tombol impor folder pantau.

**Terbaru — sesi 66 (pengguna: “Lanjut”):** sesi 65 sudah di-commit (`e4fce0a`). Dasbor web data kerja
(`dasbor-kerja`, port 8766, hanya dibuka) menampilkan tabel jadwal "terbaru · Saringan & skor kandidat ·
snapshot #24 disaring 29 Okt 2026 (preset kualitas-nilai/v1)" dan Kandidat teratas AUTO 55,7 · PTBA 54,1 ·
ERAA 53,9 · LSIP 53,5; butir itu tidak muncul di kotak "Perlu diperbarui" karena tidak jatuh tempo — sesuai.
**Temuan kecil (dikerjakan di sesi 66 lanjutan, T98):** kotak menyebut "Folder pantau — 1 berkas IDX belum diimpor": itu
`Downloads\Ringkasan Saham-20261029.xlsx`, yang **sudah** diimpor lewat unggahan (snapshot #24). Folder
pantau hanya melihat berkas yang belum dipindah, bukan isinya; tombol "Impor unduhan IDX dari folder
pantau" akan melaporkan "sudah ada" dan memindahkannya. Tidak ada kode yang diubah; test tidak dijalankan.

**Terbaru — sesi 65 (pengguna: “Lanjut”), pemeriksaan jalan pertama "MejaSaham - Impor harian" (29 Okt):**
`--refresh` (snapshot #23, 18.37) dan `--saring` (18.40) jalan; **`--impor-unduhan` tidak memindahkan
apa pun** — 10 berkas IDX masih di Downloads, tidak ada cadangan/salinan `unduhan-idx/` dari tugas.
Dua cadangan 18.39 di `.uji-data/mejasaham-cadangan` milik sesi 64 (salinan `.tmp/uji-dasbor`), bukan
tugas, jadi perintah itu berhenti **sebelum** `cadangan.buat`. Sebabnya tidak bisa dipastikan (jendela
`pause` tidak tercatat; log Task Scheduler mati): dugaan (a) proses tugas tidak melihat
`MEJASAHAM_FOLDER_PANTAU`, atau (b) bentrok kunci penulis dengan `--buat-cadangan` sesi 64 pada menit
yang sama. **Kode tidak cacat:** dijalankan ulang atas salinan data kerja + salinan 10 berkas → keluar 0,
semua dipindah, Ringkasan "sudah ada", Notasi "tidak lebih baru". Tugas sudah dinonaktifkan (update manual),
jadi tidak diperbaiki. **Jebakan:** di salinan berjalur lain, impor notasi menambah ±2.600 baris "baru"
karena `sumber` memuat jalur folder impor (`impor berkas: <folder>`) — bukan duplikasi di data kerja.
**Celah yang tercatat (belum dikerjakan):** kegagalan `--impor-unduhan` tidak masuk `log_jalan`, jadi
dasbor tidak bisa menampilkannya (AC-9) — hanya relevan bila tugas terjadwal diaktifkan lagi.
**Lanjutan sesi 65 (pengguna: “udah saya impor ringkasan saham 29 oktober malah kosong kandidatnya”):**
impor unggahan 19.00 membuat snapshot #24, tetapi skor tersimpan per snapshot dan impor tidak menyaring
ulang — dasbor hanya mencatatnya di bagian bawah. `--saring` dijalankan di data kerja (pengguna: “Ya,
keduanya”): 4 kandidat (AUTO 55,7 · PTBA 54,1 · ERAA 53,9 · LSIP 53,5), sama dengan hasil di salinan.
**Kode:** butir jadwal baru **"Saringan & skor kandidat"** (`jadwal._saringan`): jatuh tempo bila snapshot
terakhir belum punya skor, jadi ikut kotak "Perlu diperbarui" (K104) dan tabel jadwal. **Test:** suite
**1.101 lulus (80 dtk)**; +2 `tests/test_jadwal.py`, keduanya gagal di kode lama. **Bukti** atas data kerja
(baca-saja): "terbaru — snapshot #24 disaring 29 Okt 2026"; dengan skor #24 dihapus di salinan memori:
"jatuh tempo — snapshot #24 data 29 Okt 2026 belum disaring …; skor terakhir dari snapshot #23". Dicoba
di peramban pada sesi 66. 10 berkas lama di Downloads sudah hilang (bukan dipindah aplikasi; tanpa salinan baru
di `unduhan-idx/`) — sudah diimpor semua, jadi aman.
**Disetujui dan di-commit (`e4fce0a`).**

**Terbaru — sesi 64 (pengguna: “Lanjut”), perbaikan temuan terpisah sesi 63:** dasbor (web dan
`--dasbor`) gagal "sumber harga 'IDX Ringkasan Saham … sejak 2026-10-28; sebelumnya yfinance…' tidak
punya satu bar pun" setiap kali `--saring` belum menyimpan konteks pasar snapshot terakhir. Sebab:
`dasbor.susun` mengirim `PilihanHarga.label` — teks tampilan sambungan K97 — ke `potret.muat(sumber=…)`,
yang memeriksanya sebagai satu label bar. Kini `potret.muat` menerima `PilihanHarga` utuh (setiap label
yang dipakainya diperiksa punya bar) dan dasbor mengirim objek itu; `--sumber` (str) tidak berubah.
**Test:** suite **1.099 lulus (87 dtk)**; +3 `tests/test_sambungan_harga.py`, ketiganya gagal di kode lama. **Bukti** di salinan data
kerja `.tmp/uji-dasbor` (backup baca-saja): `--dasbor` keluar normal atas snapshot #23 (dibuat jalan
Impor harian 29 Okt 18.37), konteks pasar dihitung ulang (±65 dtk; cepat lagi sesudah `--saring`).
Yang terlihat di keluaran itu, bukan cacat kode: "0 emiten punya bar pada tanggal data" karena Ringkasan
Saham 29 Okt belum diunggah (jadwal: jatuh tempo).

**Terbaru — sesi 63, K104:** pengganti jadwal otomatis — kotak "Perlu diperbarui" di kepala dasbor web
(`web/server.py` `_perlu_diperbarui`, `pengingat.saat_dibuka`): butir jadwal jatuh tempo/menunggu,
pengingat K95 (dipindah dari isi dasbor), dan berkas di folder pantau yang belum diimpor. Rincian
`docs/keputusan.md` K104. **Test:** suite **1.096 lulus (75 dtk)**; +3 `tests/test_web.py`, +1
`tests/test_folder_pantau.py`; fixture web kini mengosongkan `MEJASAHAM_FOLDER_PANTAU` (variabel
pengguna sudah di-`setx`, uji tidak boleh membaca Downloads). **Bukti** di salinan data kerja
`.tmp/uji-k104` (backup baca-saja): kotak tampil "Harga harian & indeks — jatuh tempo (snapshot #22
data 28 Okt; hari bursa terakhir 29 Okt)" dan "Folder pantau — 10 berkas IDX belum diimpor".
**Temuan terpisah (belum dikerjakan):** di data kerja, dasbor (web dan `--dasbor`) gagal "sumber harga
'IDX Ringkasan Saham … sejak 2026-10-28; sebelumnya yfinance…' tidak punya satu bar pun yang sudah
diketahui pada 2026-10-29T12:00:52" — sudah ada sebelum K104 (`--dasbor` CLI gagal sama).

**Terbaru — sesi 63 (pengguna: “update otomatis tiap hari rada mengganggu … updatenya pas saya pengen
update saja”):** kedua tugas Task Scheduler K101/K102 **dinonaktifkan** (`Disable-ScheduledTask`, tidak
dihapus): "MejaSaham - Impor harian" dan "MejaSaham - Pengingat unduhan". Kode `--impor-unduhan`,
`--ingatkan`, tombol dasbor, dan `MEJASAHAM_FOLDER_PANTAU` tetap — update kini manual: unduh dari IDX,
lalu dasbor → Impor & cadangan → "Impor unduhan IDX dari folder pantau", atau
`MejaSaham.cmd --refresh` / `--impor-unduhan` / `--saring`. Jalan pertama Impor harian (29 Okt, mulai
18.15) sedang berjalan saat dinonaktifkan dan dibiarkan selesai. Aktifkan lagi:
`Enable-ScheduledTask -TaskName 'MejaSaham - Impor harian'` (sama untuk Pengingat unduhan).

**Terbaru — sesi 62, K103 (pengguna: “Setuju, kerjakan”):** dari 19 SPT riset, 10 ditolak (bukan 11 —
dikoreksi di `docs/keputusan.md` 3.14). 8 di antaranya suspensi lanjutan "di Pasar Reguler dan Pasar
Tunai mulai sesi I / Sesi Pra-Pembukaan tanggal … sampai dengan Pengumuman Bursa lebih lanjut" → kini
dibaca (`pengumuman_idx.POLA_BERLAKU_SESI`, teks tanpa spasi karena "m ulai"); 2 (FLMC 2023 BEI.PLP,
OCAP 2024 BEI.PP3) tetap ditolak, pesannya kini menyebut nomornya. Rincian `docs/arsitektur.md` T97.
**Test:** suite **1.092 lulus (66 dtk)**; +7 `tests/test_pengumuman_idx.py`, ketujuhnya gagal di kode
lama. **Bukti** baca-saja (38 PDF riset + 3 PDF pengguna, salinan `.tmp/uji-pengumuman`): 36 terbaca,
5 ditolak, `pilah` 0 baru / 36 sudah tercatat — data kerja tidak berubah karena perluasan ini.
**Disetujui (“Ya, commit”), di-commit.** **Berikutnya:** periksa jalan pertama "MejaSaham - Impor harian" (29 Okt
18.00).

**Terbaru — sesi 62, pemasangan K101/K102 (pengguna: “Ya, pasang”):** `setx MEJASAHAM_FOLDER_PANTAU
"C:\Users\PENGGUNA\Downloads"` (variabel pengguna). Dua tugas Task Scheduler (hari kerja, Interactive /
hanya saat login, `MejaSaham.cmd`, folder kerja = akar repo): **"MejaSaham - Pengingat unduhan"** 16.30
`--ingatkan`; **"MejaSaham - Impor harian"** 18.00, tiga aksi berurutan `--refresh`, `--impor-unduhan`,
`--saring`. Uji: pengingat dijalankan manual sekali → hasil 0. Impor harian **belum** pernah jalan —
jalan pertama 29 Okt 18.00 memindahkan berkas IDX lama di Downloads ke `unduhan-idx/` (yang sudah diimpor
tidak diimpor ulang). **Berikutnya:** periksa hasil jalan pertama (Riwayat tugas, `unduhan-idx/`, snapshot
baru); bila Ringkasan Saham 29 Okt belum diunduh sebelum 18.00, jalankan ulang tugas sesudah unduh.
Hapus: `Unregister-ScheduledTask -TaskName 'MejaSaham*'`, `reg delete HKCU\Environment /v MEJASAHAM_FOLDER_PANTAU`.

**Terbaru — sesi 61, K101/K102 (pengguna: “Setuju U37 & U38”):** unduhan IDX tetap manual (K95/K96);
yang otomatis kini langkah sesudahnya. **`--impor-unduhan`** + tombol dasbor (Impor & cadangan → "Impor
unduhan IDX dari folder pantau"): `folder_pantau.py` mengenali nama unduhan IDX, lalu
`tulis.permintaan_impor_folder_pantau` → cadangan → Ringkasan Saham → Notasi Khusus → PDF lewat jalur
unggahan yang sama; berkas selesai dipindah ke `unduhan-idx/`. **`--ingatkan`**: kotak pesan Windows
dari butir jadwal yang punya `alamat` (bidang baru `jadwal.Butir.alamat`). Rincian `docs/arsitektur.md`
T96. **Toast PowerShell dibuang** setelah gagal dua cara di mesin ini (Constrained Language Mode
bergantian dengan 0x80073D54) → `MessageBoxW` via `ctypes`. **Test:** suite **1.085 lulus (62 dtk)**;
+20 `tests/test_folder_pantau.py`, +1 `tests/test_web.py`. **Bukti** atas salinan `.tmp/uji-pantau`
(bukan data kerja), 5 berkas nyata dari Downloads + 1 berkas lain: keluar 0, 40 dtk, isi notasi identik
dengan data kerja, `integrity_check` ok, berkas lain tetap; kotak pesan tampil (uji 4 dtk). **Data kerja
tidak disentuh; folder pantau belum diatur; Task Scheduler belum dipasang.** Di-commit (`a1d53d3`).
**Jebakan:** PowerShell anak dari Python `.venv` di mesin ini kadang Constrained Language Mode (Code
Integrity enforced) — jangan bergantung pada skrip PowerShell dari kode.

**Cara memasang (dikerjakan pengguna, sekali):**
1. Pilih folder unduhan, mis. `C:\Users\PENGGUNA\Downloads`, lalu
   `setx MEJASAHAM_FOLDER_PANTAU "C:\Users\PENGGUNA\Downloads"` (buka terminal baru sesudahnya). Berkas IDX
   lama di folder itu ikut dipindah ke `unduhan-idx/` pada jalan pertama (yang sudah diimpor tidak
   diimpor ulang); berkas lain tidak disentuh.
2. Task Scheduler, "Run only when user is logged on" (kotak pesan butuh layar), program
   `C:\Users\PENGGUNA\Projects\MejaSaham\MejaSaham.cmd` (memasang folder data kerja):
   - hari kerja 16.30, argumen `--ingatkan`;
   - hari kerja 18.00 (sesudah unduh), tiga aksi berurutan: `--refresh`, `--impor-unduhan`, `--saring`
     — Ringkasan Saham hanya diterima sampai tanggal snapshot, dan saringan harus membaca snapshot
     sesudah impor. Kegagalan membuat `MejaSaham.cmd` berhenti di `pause` (sengaja terlihat).

**Berikutnya:** tinjauan pengguna (K4) + commit; pasang langkah di atas; PDF UPT PTSP saat terbit;
Ringkasan Saham 29 Okt sesudah bursa tutup.

**Terbaru — sesi 61, K100 (pengguna: “Contoh PDF UPT”):** tidak ada PDF UPT baru di Downloads; dipakai
18 PDF UPT asli IDX dari riset lama (`.uji-data/riset-idx/riwayat-api-pdf/`). Isinya ternyata ditulis
dengan font CID → `kalender.potongan_teks(terjemahkan_font=True)` menerjemahkan lewat `/ToUnicode`
(pustaka standar). **Cacat lama ikut diperbaiki:** pola `Tf` tidak pernah cocok (spasi di regex `re.X`);
kalender KSEI 2025–2027 nyata **identik** sebelum/sesudah. UPT menutup tepat satu suspensi terbuka,
`tanggal_selesai` = sehari sebelum dibuka kembali (`HasilNotasi.penutupan`); sesi II, non-Pasar Reguler
(K39), nomor terpotong → ditolak. Rincian `docs/keputusan.md` K100 + 3.14, `docs/arsitektur.md` T95.
**Test:** suite **1.064 lulus (58 dtk)**; +19 di `tests/test_pengumuman_idx.py`, +1
`tests/test_kalender_ksei.py`; 20 uji baru gagal di kode lama. **Bukti** (baca-saja, salinan
`.tmp/uji-upt/notasi-khusus.csv`): 16 dari 18 UPT terbaca, **16/16 "sudah tercatat"** (episode API lama),
0 penutupan ganda; 3 PDF pengguna tetap terbaca sama.
**Pilihan K100 (a)–(c) disetujui pengguna (“Setuju, commit”); di-commit. Data kerja tidak disentuh.** **Jebakan:** heredoc Bash
yang memuat `'''` gagal diurai tool — tulis skrip ke scratchpad lewat Write. **Berikutnya:**
PDF UPT PTSP saat terbit → unggah (cadangan dulu); 11 SPT riset dengan kalimat tanggal lain masih
ditolak (batas K99); Ringkasan Saham 29 Okt sesudah bursa tutup.

**Terbaru — sesi 61, K99 diimpor ke data kerja (pengguna: “Commit + impor”):** K99 di-commit
(`73c975a`). Cadangan `.uji-data/mejasaham-cadangan/20261029T115945518371+0700`, lalu jalur yang sama
dengan tombol dasbor (`permintaan_impor_pengumuman_idx`, folder data absolut; skrip berhenti bila label
sumber ≠ label impor Notasi Khusus sebelumnya) → **snapshot 22**, **3 revisi** ("2603 sudah ada dan
sama"), 97 dtk: COIN & FILM UMA 28 Okt → 27 Nov, PTSP suspensi mulai 29 Okt (terbuka). 0 baris lama
berubah, `integrity_check` ok. Laporan mutu snapshot 22 identik dengan 20–21 (FORU/PACK
`kritis_bermasalah` sudah ada sebelumnya, bukan akibat impor ini). PDF mentah tersimpan di
`.uji-data/mejasaham/unduhan-idx/pengumuman/`. **Berikutnya:** contoh PDF pembukaan suspensi (UPT) —
PTSP akan tercatat tersuspensi sampai itu; Ringkasan Saham 29 Okt sesudah bursa tutup.

**Terbaru — sesi 61, K99 (unggah PDF pengumuman suspensi & UMA):** pengguna memberi tiga contoh
nyata (`C:\Users\PENGGUNA\Downloads\20261028-UMA_COIN.pdf`, `…UMA_FILM.pdf`,
`…WAS_Suspensi_PTSP.pdf`) — **pengumuman satuan, satu emiten per PDF**, bukan daftar. Pengguna memilih
"Pembaca PDF" dan "Tanggal berlaku" → **K99** (`docs/keputusan.md` 3.13, `docs/arsitektur.md` T94).
Dibangun `mejasaham/pengumuman_idx.py` (teks PDF lewat pengurai pustaka standar `kalender.py`, **tanpa
pypdf**), `HasilNotasi.hanya_menambah`, `tulis.permintaan_impor_pengumuman_idx` (folder impor tetap yang
sama dengan Notasi Khusus), dan menu Impor & cadangan → "Pengumuman suspensi & UMA IDX (PDF)". UPT
(pembukaan), multi-kode, dan kalimat lain **ditolak** — suspensi dari PDF tetap terbuka sampai ada
contoh PDF pembukaan. **Test:** suite **1.045 lulus (112 dtk)**; +15 `tests/test_pengumuman_idx.py`, +2
`tests/test_web.py`. **Bukti** atas salinan `.tmp/uji-pengumuman` (bukan data kerja): tepat 3 baris
baru (COIN/FILM UMA 28 Okt, PTSP suspensi mulai 29 Okt), 0 baris lama berubah, `integrity_check` ok,
50 dtk. **Data kerja tidak disentuh. Belum di-commit.** **Jebakan:** label sumber impor = jalur absolut
folder impor; di salinan jalurnya berbeda sehingga revisi tertulis ulang — nilai salinan dari isi
baris, bukan jumlah revisi. Skrip Python lewat heredoc: jalur `C:\Users\…` di string biasa memicu
`unicodeescape` — pakai Edit atau string mentah. **Berikutnya:** tinjauan pengguna (K4); unggah ketiga
PDF ke data kerja (cadangan dulu); contoh PDF pembukaan suspensi (UPT) → pembacanya; Ringkasan Saham
29 Okt sesudah bursa tutup.

**Terbaru — sesi 60, tinjauan K98 (pengguna: “Saya tinjau K98”, lalu “Ya, perbaiki”):** tiga
temuan ditutup. (1) `notasi.tulis_berkas` kini menolak (`GalatNotasi`) hasil yang memuat catatan
tetapi tanpa baris dan tanpa `jenis_dicakup` — dulu catatannya tertulis `# CATATAN []: …`, tidak
terbaca `POLA_CATATAN`, dan hilang diam-diam di penulisan berikutnya. (2) `docs/keputusan.md`: K98
menyebut menggantikan penggabungan satu butir di K94 (b); K94 diberi penanda yang sama. (3) Teks
jadwal butir "Suspensi & UMA (IDX)" kini "tidak dipantau — belum ada jalur unggah (P43); PRD 7.1:
harian, K94: mingguan". **Test:** suite **1.028 lulus (77 dtk)**; +1 `tests/test_notasi_idx.py`
(gagal di kode lama). Data kerja tidak disentuh. **Belum di-commit.** Ringkasan Saham 29 Okt belum
terbit saat sesi ini (sebelum bursa tutup). **Berikutnya:** unggah/impor Ringkasan Saham 29 Okt
(cadangan dulu); contoh berkas unduhan suspensi/UMA.

**Terbaru — sesi 59, catatan kepala `notasi-khusus.csv`:** pengguna: “lanjut”. Penyebab hilangnya
dua catatan asal suspensi ditutup: `notasi.tulis_berkas` kini menulis `# CATATAN [jenis]: …` dan
membawa catatan jenis yang tidak diperbarui penulisan itu (rincian `docs/keputusan.md`, sesudah
P43). **Test:** suite **1.027 lulus (55 dtk)**; +1 `tests/test_notasi_idx.py` (gagal di kode
lama). Atas persetujuan pengguna (“Ya, pulihkan”), dua catatan dari cadangan
20261029T064141675578+0700 disisipkan ke kepala `.uji-data/mejasaham/konfigurasi/notasi-khusus.csv`
bertanda `[suspensi]` (hanya +2 baris komentar; 2.603 baris data identik; salinan sebelumnya di
`.tmp/notasi-khusus.sebelum-pulih-catatan.csv`). Tanpa impor. Sudah di-commit (`f9537e5`). **Berikutnya:**
tinjauan pengguna (K4); contoh berkas unduhan suspensi/UMA; unggah Ringkasan Saham tiap hari bursa.

**Terbaru — sesi 59, K98 (P43 disetujui: “Setuju P43”):** butir jadwal "Notasi, suspensi & UMA"
dipecah di `mejasaham/jadwal.py`. "Notasi khusus & papan pemantauan (IDX)" dinilai mingguan hanya
dari jenis daftar Notasi Khusus; "Suspensi & UMA (IDX)" selalu **tidak dinilai** + tindakan manual
(isi `notasi-khusus.csv` → `--impor`, cadangan dulu). **Test:** suite **1.026 lulus (69 dtk)**; +1
`tests/test_jadwal.py` (gagal di kode lama), uji lain menyesuaikan nama butir. **Bukti** atas data
kerja (koneksi `mode=ro`): notasi "terbaru — per 27 Okt 2026, berumur 2 hari"; suspensi & UMA
"tidak dinilai — 1.151 suspensi, 1.208 UMA; pengumuman terakhir 27 Okt 2026". Halaman dasbor tidak
dibuka (tabelnya `layar.tabel.isi_jadwal` yang sama, diuji `tests/test_web.py`). Sudah di-commit.
**Jebakan:** koneksi `sqlite3` mentah ke basis data kerja perlu `row_factory = sqlite3.Row`
(`mutu` membaca kolom per nama). **Berikutnya:** tinjauan pengguna (K4); contoh berkas unduhan
suspensi/UMA dari pengguna → pembacanya; dua catatan asal suspensi yang hilang dari kepala
`notasi-khusus.csv` data kerja (ada di cadangan 20261029T064141675578+0700); unggah Ringkasan Saham
tiap hari bursa.

**Terbaru — sesi 58, Notasi Khusus diimpor ke data kerja (atas persetujuan pengguna):** cadangan
`.uji-data/mejasaham-cadangan/20261029T064141675578+0700`, lalu jalur tombol dasbor
(`permintaan_impor_notasi_idx`, folder data absolut seperti `MejaSaham.cmd`) → **snapshot 21**,
2.603 revisi sekali (label baru), 26 dtk. Isi `v_notasi_khusus_terkini` **identik** dengan cadangan
(2.603 baris), `integrity_check` ok, jadwal notasi "terbaru — per 27 Okt 2026". `notasi-khusus.csv`:
baris sama, hanya kepala komentar berganti — **dua catatan asal suspensi (55 multi-kode
terekonsiliasi, 41 pembukaan tanpa pasangan) hilang dari kepala** karena kepala ditulis ulang tiap
penulisan; masih ada di cadangan. Bahan untuk P43. **Belum di-commit.**

**Sesi 58, unggah Notasi Khusus IDX (lanjutan K96):** pengguna memberi contoh nyata
`C:\Users\PENGGUNA\Downloads\Notasi Khusus-20261027.xlsx`. Dibangun `notasi.baca_unduhan` (tanggal dari
nama berkas; isinya tanpa tanggal) + `notasi.simpan_unduhan` + `tulis.permintaan_impor_notasi_idx`
+ menu Impor & cadangan → "Notasi Khusus IDX" (unggah → konfirmasi → Tulis; konfigurasi
`notasi-khusus.csv` diganti sesudah impor berhasil). Baris berkas nyata **identik 122/122** dengan
baris per 27 Okt di data kerja. Dua cacat diperbaiki: baris papan pemantauan tidak pernah ditutup
bila daftar baru tanpa X; folder impor per unggahan menulis ulang 2.603 revisi tiap kali (kini folder
tetap). Rincian `docs/keputusan.md` 3.12. **Test:** +19 `tests/test_notasi_unduhan.py`, +2
`tests/test_web.py`; suite penuh **1.025 lulus (65 dtk)**. **Bukti**
atas salinan `.tmp/uji-notasi` (port 8768, `uji-notasi` di `.claude/launch.json`): unggahan 1 → 2.603
revisi (label baru, sekali), unggahan 2 daftar sama → **0 baru, 2.603 sudah ada dan sama**, ±42 dtk
per impor. **Data kerja tidak disentuh. Belum di-commit.** **Jebakan:** peramban panel tidak bisa
memilih berkas lokal — unggah uji lewat skrip `http.client` multipart ke server yang sama.
**Berikutnya:** tinjauan pengguna (K4); unggah berkas nyata ke data kerja (cadangan dulu; sekali
menulis 2.603 revisi); jawab **P43** (suspensi/UMA tidak punya jalur unggah, jadwal menampilkannya
terbaru begitu notasi diunggah).

**Terbaru — sesi 58, FASW diselidiki (baca-saja):** penolakan gerbang benar. FASW disuspensi
sejak 31 Jan 2025 (tercatat di `notasi_khusus`). IDX memberi penutupan 5.275 dengan volume 0,
sementara yfinance mengisi hari tanpa transaksi dengan nilai datar yang bergeser (5.312,50). Tanpa
perubahan kode/data; rincian `docs/keputusan.md` 3.11. **Berikutnya:** unggah Ringkasan Saham
setiap hari bursa mulai 29 Okt (berkas 29 Okt terbit sesudah penutupan bursa).

**Sesi 58, sambungan di data kerja:** pengguna mengunggah Ringkasan Saham 21–27 Okt
(snapshot 18–19); tanggal sambung **28 Okt** diimpor dari `.uji-data/sambungan-k97/` sesudah
cadangan `.uji-data/mejasaham-cadangan/20261029T061402921884+0700` → **snapshot 20**. Gerbang 915
lolos, **FASW ditolak** (IDX 5.275 vs yfinance 5.312, belum diselidiki). `--saring`: "Kandidat
teratas" AUTO · PTBA · ERAA · LSIP · DSNG. Rincian `docs/keputusan.md` 3.11. Tanpa perubahan kode;
suite tidak dijalankan. **Jebakan:** catatan server "peramban menutup koneksi sebelum jawaban GET
/berkas terkirim" = peramban memuat ulang lebih dulu; impornya tetap jalan (cek `log_jalan`).
**Berikutnya:** mulai 29 Okt unggah Ringkasan Saham setiap hari bursa (jadwal mengingatkan);
opsional selidiki FASW.

**Terbaru — sesi 58, K97 sisa 2 & 3:** sisa 1 sudah di-commit (`77e810e`). Pengguna: “Lanjut”.
(2) Laporan mutu sesudah `--refresh` kini memeriksa deret sambungan (`potret.harga_dipakai`),
sama dengan jalur impor (`mejasaham/pengatur.py`). (3) Butir jadwal "Harga harian & indeks"
sesudah tanggal sambung jatuh tempo bila ada hari bursa tanpa berkas IDX, dengan tanggalnya dan
tindakan unggah (`jadwal._harga_resmi`, memakai `potret.periksa_sambungan`). Rincian
`docs/keputusan.md` 3.11 "Sisa 2 & 3 selesai". **Test:** suite **1.004 lulus (205 dtk)**; +1
`tests/test_sambungan_harga.py`, +1 `tests/test_jadwal.py` (keduanya gagal di kode lama). `--dasbor`
atas `.tmp/uji-p42c`: snapshot salinan belum hari bursa terakhir, jadi cabang baru tidak tersentuh —
bukti positif hanya dari uji. Data kerja tidak disentuh. Sudah di-commit (`e0eb1a9`). **Berikutnya:**
tinjauan pengguna (K4). K97 selesai di kode; tinggal menyatakan sambungan di data kerja (menunggu
unggahan pengguna ≥ 5 hari bursa berturut-turut, lihat entri langkah 4).

**Terbaru — sesi 58, K97 sisa 1 (dasbor menyebut peringkat sementara):** langkah 4 sudah di-commit
(`ea48103`). Pengguna: “Lanjut”. Halaman depan web dan `--dasbor` kini menulis "Peringkat
sementara — belum boleh disebut kandidat" + sebabnya (kalimat sama dengan Screener, kini di
`saring.sebab_peringkat_sementara`), dinilai ulang as-of snapshot. Rincian `docs/keputusan.md`
3.11 "Sisa 1 selesai". **Test:** suite **1.002 lulus (173 dtk)**; +2 `tests/test_dasbor.py` (gagal
di kode lama), +2 asersi `tests/test_web.py`. Dicoba `--saring`/`--dasbor` atas salinan
`.tmp/uji-p42c` (menulis skor ke salinan itu): gerbang menolak 916 emiten, jadi tidak ada peringkat
untuk ditampilkan — bukti positif hanya dari uji. Data kerja tidak disentuh. **Belum di-commit.**
**Berikutnya:** tinjauan pengguna (K4). Sisa K97 yang diketahui: laporan mutu sesudah `--refresh`
masih membaca label pengambilan; pengingat unggah masih mingguan; menyatakan sambungan di data
kerja menunggu unggahan pengguna (lihat entri langkah 4 di bawah).

**Terbaru — sesi 58, K97 langkah 4 (unggah tanggal lampau + beberapa berkas):** langkah 3 di-commit
(`d54f542`). Impor & cadangan: unggah beberapa berkas sekaligus; bagian "Belum diimpor" + satu
tombol "Impor N berkas" (satu konfirmasi, satu snapshot); tanggal berkas boleh ≤ snapshot terakhir,
snapshot tidak mundur; yang di depan snapshot "Menunggu". Gerbang langkah 3 dipercepat 17 → 0,8 dtk
(jendela tumpang-tindih 60 hari kalender). Rincian `docs/keputusan.md` 3.11 "Langkah 4 selesai".
**Test:** suite **1.000 lulus** (+7 `tests/test_unggahan_idx.py`, +1 `tests/test_web.py`, +1
`tests/test_gerbang_sambungan.py`; semuanya gagal di kode lama). Dicoba di peramban atas salinan
buangan dengan dua berkas sintetis (sudah dihapus). Data kerja tidak disentuh. **Belum di-commit.**
**Jebakan:** `write_text` Python di Windows menulis CRLF — pakai `newline="\n"` (repo `eol=lf`).
Impor lewat dasbor atas basis data penuh tetap ±70–100 dtk (laporan mutu + arsip), bukan macet.
**Berikutnya:** tinjauan pengguna (K4). K97 selesai di kode; menyatakan sambungan di data kerja
menunggu pengguna: unggah Ringkasan Saham ≥ 5 hari bursa berturut-turut (boleh belakangan, dalam 60
hari), impor, lalu `sambungan-harga.csv` dengan tanggal hari bursa sesudahnya → `--impor` (cadangan
dulu). Sisa yang diketahui: dasbor belum menyebut peringkat sementara; laporan mutu sesudah
`--refresh` masih membaca label pengambilan; pengingat unggah masih mingguan.

**Sesi 58, K97 langkah 3 (gerbang tumpang-tindih + hari bolong):** pengguna: “Lanjut”.
`potret.periksa_sambungan` → `KeadaanSambungan` (dipakai `potret.muat` dan `mutu.periksa`);
`metrik.seri_harga` memberi "tidak dihitung" + alasan bila emiten gagal gerbang (≥ 5 hari
tumpang-tindih sebelum tanggal sambung, penutupan sama persis). Hari bursa tanpa berkas IDX sejak
tanggal sambung (atau kalender yang belum memuat rentangnya) → `LaporanSaring.peringkat_sementara`
(CLI + Screener web). Rincian keputusan teknis di `docs/keputusan.md` 3.11 "Langkah 3 selesai".
**Test:** suite **991 lulus (175 dtk)**; +10 `tests/test_gerbang_sambungan.py` (semua gagal di kode
lama); fixture `tests/test_sambungan_harga.py` kini memakai penutupan yang sama di hari
tumpang-tindih. **Bukti** atas salinan `.tmp/uji-p42c` (`--saring` menulis skor ke salinan itu):
916 disambung · 0 lolos (0 hari tumpang-tindih) → tidak ada peringkat, peringatan tampil. Data kerja
tidak disentuh. **Belum di-commit.** **Jebakan:** `cat > berkas` tanpa masukan di Bash agen
menggantung sampai batas waktu — tulis skrip ke scratchpad dengan Write. **Berikutnya:** tinjauan
pengguna (K4); lalu K97 langkah 4 (unggah tanggal lampau + beberapa berkas sekaligus) — tanpanya,
5 hari tumpang-tindih hanya bisa dikumpulkan dengan mengunggah tepat hari itu 5 hari berturut-turut.

**Sesi 58, K97 langkah 2 (deret sambungan):** migrasi 017 `sambungan_harga` +
`sambungan-harga.csv` (`berlaku_sejak;sumber_resmi;aktif;keterangan;sumber`); `potret.PilihanHarga`
/ `harga_dipakai` dipakai seluruh pembaca harga (8 modul). Tanpa pernyataan sambungan, perilaku
sama persis seperti sebelumnya. Bukti atas salinan `.tmp/uji-p42c` (sambung uji 28 Okt): saringan
identik, cek sumber kedua utama IDX / pembanding yfinance 20 · 0 ditandai. **Test:** suite **981
lulus (125 dtk)**; +18 uji `tests/test_sambungan_harga.py`. Data kerja tidak disentuh. **Belum
di-commit.** **Jebakan:** heredoc Bash di sesi agen meruntuhkan dua garis miring terbalik menjadi satu — tulis skrip
sunting Python ke berkas (Write) bila teksnya memuat garis miring terbalik. **Berikutnya:**
tinjauan pengguna (K4); lalu K97 langkah 3 (gerbang tumpang-tindih + laporan hari bolong).
Menyatakan sambungan di data kerja **belum** dilakukan — butuh tanggal dari pengguna dan
sebaiknya sesudah langkah 3 (tanpa laporan bolong, hari yang lupa diunggah tidak terlihat).

**Terbaru — sesi 58, K97 langkah 1 (penanda split berbatas waktu):** pengguna menyetujui P42 (a)–(f) → **K97**. Langkah 1 dikerjakan: `HargaHarian.diketahui_pada` (diisi `potret._harga`), dan `penyesuaian.sesuaikan` menerapkan split yang tanggalnya sesudah tanggal baris berpenanda `split` diketahui. Ternyata cacatnya sudah aktif: PBSA melompat 2× di 27→28 Okt 2021 (tepi jendela unduh 5 tahun) sesudah split 14 Okt 2026; kini sambung. Bukti baca-saja atas salinan `.tmp/uji-p42c/mejasaham.db` (snapshot 17): 1 deret berubah dari 916, status siap tidak berubah. **Test:** suite **963 lulus (186 dtk)** (+5 di `tests/test_penyesuaian.py`, 4 gagal di kode lama). Data kerja tidak disentuh. **Belum di-commit.** **Jebakan:** SQLite di sandbox agen gagal "unable to open database file" pada kueri berkelompok besar, karena tidak bisa membuat berkas sementara → `PRAGMA temp_store=MEMORY`; menyalin basis data ke scratchpad juga ditolak, jadi pakai `.tmp/`. **Berikutnya:** tinjauan pengguna (K4), lalu K97 langkah 2 (tanggal sambung + deret sambungan di `potret.py`).

**Terbaru — sesi 58, usulan P42 (harga resmi IDX sebagai sumber utama):** atas pertanyaan pengguna, usulan "deret sambungan" ditulis di `docs/keputusan.md` 3.11: satu tanggal sambung untuk seluruh emiten (yfinance sebelum, IDX sejak), gerbang tumpang-tindih, hari tanpa berkas = bolong yang tampil, label per bar. **Ditemukan cacat laten (belum diperbaiki):** `penyesuaian.py` melewati semua split sesudah tanggal bar untuk baris berpenanda `split`, tanpa melihat `diketahui_pada`; tertutup selama yfinance terus diunduh ulang, tetapi muncul begitu riwayat yfinance dibekukan. Hanya dokumen yang berubah; test tidak dijalankan. **Berikutnya:** jawaban P42.

**Terbaru — sesi 58, perbaikan cache dasbor web:** pengguna melihat "Kandidat teratas" **kosong**
padahal data kerja punya 5 skor untuk snapshot 17 (AUTO, PTBA, ERAA, LSIP, DSNG). Sebabnya: dasbor
web menyimpan hasil jadi di memori, dan hasil yang dihitung **sebelum** skor tertulis tidak pernah
dibuang. Tiga lubang ditutup: (1) `DaftarPekerjaan.lupakan` kini menandai pekerjaan yang masih
berjalan sebagai basi (dibuang begitu selesai), bukan melewatinya; (2) Screener web melupakan dasbor
**sesudah** saringan selesai, bukan saat mulai; (3) dasbor menyimpan `dasbor.tanda_data` (snapshot
terakhir + stempel/jumlah `skor`) dan menghitung ulang bila tanda berubah — menangkap `--saring` /
`--refresh` dari baris perintah. Batas yang diketahui: tulisan CLI ke tabel lain (posisi, ekuitas,
kandidat) masih perlu "Muat ulang". **Test:** suite **958 lulus (175 dtk)**; dua uji regresi baru di
`tests/test_web.py` gagal di kode lama. Data kerja tidak disentuh. **Belum di-commit.**
**Berikutnya:** tinjauan pengguna (K4); dasbor yang sedang terbuka perlu dijalankan ulang (Ctrl+C
lalu `MejaSaham.cmd`) agar kode baru dipakai.

**Terbaru — sesi 57, T93 (pembaca Ringkasan Saham IDX + impor):** pengguna memberi contoh nyata
`C:\Users\PENGGUNA\Downloads\Ringkasan Saham-20261028.xlsx` (SheetJS, 28 kolom, 963 emiten). Pembacanya
(`unggahan_idx.baca`, pustaka standar) + tombol **"Impor sebagai harga pembanding"** di Impor &
cadangan → konfirmasi → impor biasa (label `IDX Ringkasan Saham (unduhan pengguna dari situs IDX)`)
→ cek sumber kedua langsung dijalankan. Syarat: tanggal berkas = tanggal data snapshot terakhir.
**Uji coba atas SALINAN data kerja** (`.tmp/uji-ringkasan`, sudah dihapus): snapshot 17, 963 baris,
95 dtk, **20 emiten diperiksa · 0 ditandai**, cadence jadi tepat waktu, sumber utama tetap yfinance.
Berkas IDX nyata tidak masuk repo (uji memakai XLSX sintetis berbentuk sama). **Test:** suite
**955 lulus (145 dtk)**; di-commit `a26b65b`. **Data kerja (atas persetujuan pengguna):** cadangan
`.uji-data/mejasaham-cadangan/20261029T032529472075+0700`, lalu impor lewat jalur tombol →
**snapshot 17** (data 28 Okt, 963 baris berlabel IDX, 68 dtk), **cek sumber kedua lengkap pertama:
20 emiten · 0 ditandai**, cadence tepat waktu sampai 5 Nov; sumber utama tetap yfinance;
`integrity_check` ok. Saringan belum dijalankan atas snapshot 17 (pembaruan 17.13 akan menjalankannya).

**Terbaru — sesi 57, T92 (unggah Ringkasan Saham lewat dasbor + pengingat):** atas permintaan
pengguna, menu **Impor & cadangan** kini punya formulir unggah berkas Ringkasan Saham IDX; berkas
disimpan mentah di `<folder data>/unduhan-idx/ringkasan-saham/` + `daftar.csv` (SHA-256), basis data
tidak disentuh. Dasbor menampilkan **"Waktunya mengunduh Ringkasan Saham IDX"** bila cek sumber kedua
belum tepat waktu dan belum ada unggahan 7 hari terakhir. Inti `mejasaham/unggahan_idx.py`. Dicoba di
peramban atas `.tmp/web-coba` (unggah biner 12 bait tersimpan sama persis; pengingat tampil; unggahan
uji dihapus lagi). **Test:** suite **943 lulus (141 dtk)** (+10 `tests/test_unggahan_idx.py`, +5
`tests/test_web.py`). **Belum di-commit.** Halaman Ringkasan Saham IDX sempat **kosong** di Chrome pengguna dan di peramban
agen (dini hari 29 Okt; aset JS situs dijawab 403) — coba lagi sesudah bursa tutup. **Berikutnya:**
pengguna mengunggah berkas nyata pertama → agen membangun pembacanya (impor lewat konfirmasi), lalu
`--cek-sumber-kedua`.

**Terbaru — sesi 57, K95/K96 (pengguna: “Setuju keduanya”):** **K96/T91 dikerjakan:** tombol
"Perbarui data" kembali lima tahap dan tidak lagi mengambil notasi/suspensi/UMA IDX; jadwal tetap
menilai notasi mingguan dan menyebut unduh-sendiri dari situs IDX lalu `--impor`. `--ambil-notasi`
masih ada (tidak ditawarkan) sampai diputuskan terpisah. **K95 belum dikerjakan:** pembaca berkas
unduhan Ringkasan Saham IDX menunggu **contoh berkas nyata dari pengguna** (bentuknya tidak ditebak).
Akibat yang diterima: tanpa pembaca berkas unduhan notasi IDX, `notasi-khusus.csv` menua (daftar per
27 Okt jatuh tempo mulai 4 Nov). **Test:** suite **928 lulus (164 dtk)** (931 − 4 uji notasi otomatis
+ 1 uji regresi K96 yang gagal di kode lama). **Belum di-commit.**

**Terbaru — sesi 57, riset sumber harga kedua (29 Okt 2026, dini hari):** ringkasan harian resmi IDX
(`GetStockSummary`) ternyata terbuka lewat `www.idx.id` (sesi 53 mencoba `idx.co.id` → 403); uji
baca-saja 28 Okt: **916/916 penutupan sama persis** dengan yfinance, dan bar keenam ticker yang
menunggu OHLCV primer juga tersedia. **Tetapi** Syarat Penggunaan IDX melarang web scraping/crawling —
berlaku juga untuk `notasi.py` (otomatis sejak K94). Agen berhenti mengambil; tidak ada impor, kode,
atau data kerja yang berubah; test tidak dijalankan (riset). Rincian dan usulan: **P40** (sumber kedua =
unduhan manual Ringkasan Saham IDX → `--impor`) dan **P41** (hentikan pengambilan otomatis notasi) di
`docs/keputusan.md` 3.10. **Pembaruan data terjadwal** sesi ini pukul 17.13 (cadangan → `--refresh
--saring --folder-data .uji-data\mejasaham`; hanya hidup selama sesi terbuka). **Berikutnya:** jawaban
P40/P41.

**Terbaru — sesi 56, data kerja diperbarui lewat jalur tombol (29 Okt 2026, dini hari):** K94 di-commit (`7b0d0c4`). Cadangan `.uji-data/mejasaham-cadangan/20261028T222027979144+0700`, lalu `pembaruan.jalankan` (skrip di scratchpad, jalur yang sama dengan tombol). **Jalan pertama dihentikan:** listrik padam memutus internet ±3 jam (DNSError), 144/800 emiten gagal → pasti dibatalkan ambang 5% (PRD 9.3) tanpa menulis; proses dihentikan, `integrity_check` = ok, snapshot tetap #15. **Jalan ulang berhasil (33 mnt):** notasi IDX per 27 Okt masuk (2.603 baris, label `impor berkas: <folder konfigurasi absolut>`, **0** berpenanda tidak lengkap); **snapshot #16** data 28 Okt, 2.700 baris baru, bolong 151 → 59, dikeluarkan dari peringkat 100 → 8; saringan: likuid 181 · lolos 5 (AUTO 55,6 · PTBA 54,4 · ERAA 54,1 · LSIP 53,5 · DSNG 52,0), breadth 15,5% RISK-OFF; cadangan `20261029T022833643502+0700` (tersimpan 3). Jadwal: notasi **terbaru**; harga **jatuh tempo** karena kalender menghitung 29 Okt sebagai hari bursa sejak tengah malam. **Cacat ditemukan, BELUM diperbaiki:** pukul 02.24 Yahoo mengirim bar IHSG & LQ45 28 Okt dengan `close` kosong; ingesti menyimpannya sebagai revisi baru (append-only), sehingga revisi terkini 28 Okt kosong dan baris `Pasar` dasbor mundur ke IHSG 27 Okt (5.266). Harga saham tidak terkena (94 revisi, 0 kosong). Pulih sendiri bila refresh berikutnya menerima nilai penuh. **Diperbaiki (T90, atas persetujuan pengguna):** revisi harga/indeks yang hanya mengosongkan penutupan yang sudah diketahui dari sumber yang sama kini ditolak dan dilaporkan sebagai peringatan; suite **931 lulus**; bukti luring atas salinan data kerja. Baris kosong 28 Okt di snapshot #16 tetap ada (append-only) sampai sumber mengirim nilai penuh. **Berikutnya:** tinjauan pengguna (K4); tekan "Perbarui data" sesudah bursa tutup 29 Okt.

**Terbaru — sesi 56, K94 (notasi IDX mingguan di tombol Perbarui data):** T88 di-commit (`6c58ecb`). Tombol "Perbarui data" kini mengambil notasi, suspensi & UMA IDX **bila daftar resminya berumur > 7 hari**, sebelum harga, lalu refresh membacanya (tanpa `--impor`). Suspensi/UMA jadi mingguan — **menyimpang dari PRD 7.1 (harian), dicatat di K94**. Pengumuman `>1 Kode` yang sudah dipetakan (K36–K41) didaftar di `.uji-data/mejasaham/konfigurasi/multi-kode-terekonsiliasi.csv` (**56 pengumuman, dibuat sesi ini**); tanpa daftar itu 2.157 baris tertandai "tidak lengkap" → PERINGKAT SEMENTARA. **Test:** suite **930 lulus (92 dtk)**; dua pengambilan IDX sungguhan ke salinan konfigurasi (tanpa/dengan daftar: 2.157 → 0 berpenanda; 174 baris kurasi utuh). **Data kerja:** hanya berkas daftar rekonsiliasi yang ditambahkan; notasi belum diambil — tombol berikutnya akan mengambilnya (daftar per 09 Okt → jatuh tempo). **Belum di-commit.** **Jebakan:** pengumuman `>1 Kode` BARU harus dipetakan per kode dulu, baru `Data_Download`-nya ditambahkan ke daftar; menambahkannya tanpa pemetaan menyembunyikan suspensi yang hilang. **Berikutnya:** tinjauan pengguna (K4).

**Terbaru — sesi 56, T88 (perbaikan label sumber):** K93 di-commit (`b7c1637`). Refresh kini menyimpan isi folder konfigurasi (notasi IDX, SUN, kalender, harga/indeks dari berkas) dengan label `impor berkas: <folder absolut>`, bukan `yfinance/Yahoo Finance`, lewat `ingesti.simpan(tambahan=)` dalam transaksi yang sama. **Test:** suite **925 lulus (79 dtk)**; uji regresi baru gagal di kode lama. Bukti luring atas salinan data kerja: refresh 1 → 2.450 baris notasi + 1 SUN diberi label benar (sekali), refresh 2 → 0. **Data kerja belum disentuh:** refresh/tombol berikutnya akan menambah satu revisi label itu (±2.450 baris), lalu berhenti. Baris lama berlabel yfinance tetap ada (append-only). **Belum di-commit.** **Berikutnya:** tinjauan pengguna (K4); notasi IDX masih jatuh tempo (per 09 Okt) — `--ambil-notasi` lalu `--impor`.

**Terbaru — sesi 56, K93 (U36 pelacak jadwal pembaruan):** K92 di-commit (`55fc9af`). Daftar periksa sembilan data tampil di dasbor web (bagian “Jadwal pembaruan data”, juga di halaman hasil pembaruan), `--dasbor`, dan sesudah `--refresh`; inti `mejasaham/jadwal.py`. Status dari **tanggal isi data**, bukan waktu tulis. Atas data kerja: harga, emiten (Master File 30 Sep), kalender (2025–2027) **terbaru**; suspensi/UMA dan notasi **jatuh tempo** (daftar IDX per 09 Okt, 19 hari); cek sumber kedua **menunggu sumber**; SUN/fundamental/rasio bank **tidak dinilai**. **Test:** suite **924 lulus (52 dtk)**; dilihat di peramban atas data kerja (hanya baca). **Belum di-commit.** **Cacat ditemukan, BELUM diperbaiki:** `pengatur._tanpa_emiten` memberi baris dari berkas konfigurasi label sumber pengambilan otomatis (`yfinance/Yahoo Finance`), padahal docstring-nya menjanjikan label folder impor — setiap `--refresh` menulis ulang 4.604 baris `notasi_khusus` (+ SUN) sebagai revisi berlabel Yahoo (terukur snapshot 15). Provenance salah (aturan keras 3); perlu keputusan perbaikan (mis. simpan berkas impor sebagai kumpulan terpisah berlabel foldernya). **Berikutnya:** tinjauan pengguna (K4), lalu putuskan perbaikan label sumber.

**Terbaru — sesi 56, K92 (tombol Perbarui data + pembersihan cadangan):** dasbor web kini punya tombol **Perbarui data** (konfirmasi → halaman kemajuan “tahap n dari 5 · n dari 973 emiten · gagal”) yang menjalankan jalur `--refresh --saring`; bila snapshot sudah dari hari bursa terakhir, tombol hanya memberi tahu **“Data sudah paling baru”** (bisa dipaksa lewat konfirmasi). Inti di `mejasaham/pembaruan.py`. Cadangan: retensi **3** (dulu 14), arsip **ditautkan** (hardlink), salinan arsip identik di cadangan lama dirapikan otomatis — dijalankan atas data kerja: 126 berkas, cadangan **2,8 GB → 690 MB**, `.uji-data` **4,6 → 2,6 GB**. Arsip snapshot tidak dihapus (PRD). **Test:** suite **910 lulus (78 dtk)**; dicoba di peramban (data kerja → “sudah paling baru”; `.tmp/web-coba` → kemajuan nyata 16/973, lalu dihentikan sebelum menulis). **Belum:** U36 (pelacak jadwal pembaruan lintas data) — disetujui pengguna sebagai tahap berikutnya; perubahan K92 belum di-commit. **Jebakan:** Explorer menghitung berkas bertaut berkali-kali — ukur dengan `du`. Klik saat halaman “sedang menghitung” memuat ulang diri bisa hilang. **Berikutnya:** tinjauan pengguna (K4), lalu U36.

**Terbaru — sesi 56 (pemeriksaan, bukan tahap baru):** suite **893 lulus (50 dtk)**; dasbor web atas salinan `.tmp/web-coba` terbuka (±40 dtk menghitung) dengan peringkat sama (AUTO 55,8 … DSNG 51,9). Temuan: snapshot terakhir **#14 berdata 11 Okt 2026**, hari bursa terakhir 28 Okt → peringatan AC-8 tampil; ekuitas & batas risiko belum pernah dicatat sehingga kalkulator menolak menghitung. Antrean data di baris sesi 55 **tidak bisa dikerjakan agen sendiri**: OHLCV primer enam ticker menunggu ekspor berlisensi (manusia), kalender 2021–2024 404 di KSEI, 44 bank ditunda (K88). **Lanjutan sesi 56 — data kerja diperbarui (atas persetujuan pengguna):** cadangan `.uji-data/mejasaham-cadangan/20261028T183304059079+0700`, lalu `--refresh` (1.129 dtk) → **snapshot 15, data 28 Okt 2026**, 15.387 bar baru, 57 emiten gagal permanen (delisting), 151 bolong (kebanyakan belum ada bar 28 Okt dari yfinance) · 9 tak wajar. **Cacat ditemukan & diperbaiki:** `--refresh --saring` (perintah Task Scheduler AC-11 di AGENTS.md) **tidak pernah menjalankan saringan** sejak Tahap 1 — `cli.jalankan_tanpa_jendela` berhenti sesudah refresh. Kini saringan menyusul bila refresh berhasil; refresh gagal tidak disusul saringan (uji `test_refresh_lalu_saring_menjalankan_keduanya`, gagal di kode lama). `--saring` (22 dtk): likuid 191 · **lolos 5** (AUTO 55,2 · PTBA 54,1 · LSIP 53,7 · ERAA 53,5 · DSNG 52,1); INDF/STAA/MAPI keluar karena di bawah MA200, AKRA karena PBV relatif sektor; breadth 16,2% RISK-OFF, IHSG 5.282. **Test:** suite **895 lulus (78 dtk)**. **Jebakan:** `MejaSaham.cmd`/`python -m mejasaham` tanpa `--folder-data` memakai `%LOCALAPPDATA%\MejaSaham`, yang **belum ada** di mesin ini — data kerja nyata ada di `.uji-data/mejasaham`. Ekuitas & batas risiko belum pernah dicatat; cek sumber kedua (PRD 7.3) belum pernah dijalankan. **Berikutnya:** tinjauan pengguna (K4).

**Lanjutan sesi 56 — peluncur diarahkan ke data kerja (permintaan pengguna):** `MejaSaham.cmd` kini memasang `MEJASAHAM_DATA=%~dp0.uji-data\mejasaham` bila variabel itu belum ada (`--folder-data` tetap menang). `python -m mejasaham` langsung **tidak** berubah — tetap `%LOCALAPPDATA%\MejaSaham` bila tanpa `--folder-data`; Task Scheduler harus menyertakan `--folder-data .uji-data\mejasaham`. Bukti: `MejaSaham.cmd --dasbor` keluar 0, membaca snapshot #15, `%LOCALAPPDATA%\MejaSaham` tidak dibuat; `tests/test_web.py` 29 lulus (uji peluncur kini memeriksa baris itu). Cadangan dari peluncur jatuh ke `.uji-data/mejasaham-cadangan` (folder saudara).

**Lanjutan sesi 56 — batas risiko & cek sumber kedua (rekomendasi agen, disetujui pengguna):** cadangan `.uji-data/mejasaham-cadangan/20261028T185925199918+0700`. `--batas-risiko-bawaan` → preset **risiko-bawaan/v1** tersimpan (0,75% per posisi · bobot 10% · sektor 30% · 2% ADTV20 · total 5%; nilai usulan PRD 8.3). Baris `Risiko` dasbor kini hanya menunggu ekuitas. `--cek-sumber-kedua` → keluar 1, **belum dapat diperiksa**: tidak ada harga dari sumber kedua di basis data (percobaan dicatat, tidak memadamkan peringatan — U19). Ini **terblokir data**, bukan kode: belum ada sumber pembanding yang dipilih; endpoint harian IDX 403 (sesi 53). **Berikutnya:** pengguna belum punya modal (28 Okt 2026) — ekuitas **sengaja tidak dicatat**, termasuk tidak dicatat Rp 0 (0 = benar-benar tidak ada dan menjadi titik awal drawdown). Catat dengan `--ekuitas-harian RUPIAH [--kas RUPIAH]` begitu dana ada; sementara itu simulasi lewat `--hitung-risiko KODE --ekuitas RUPIAH` (tidak disimpan). Pilih sumber harga kedua (keputusan pengguna).

**Terbaru — sesi 55, tahap C (K91):** jendela PySide6, build EXE (PyInstaller, `tools/build_exe.py`, `tools/entry_exe.py`, `tools/generate_icon.py`, `requirements-build.txt`, ikon ICO) dan uji-ujinya **dihapus**. `python -m mejasaham` tanpa argumen → dasbor web; klik-ganda `MejaSaham.cmd` di akar repo melakukan hal yang sama. PySide6 keluar dari `requirements.txt` + lock. **Test:** suite **893 lulus (46 dtk)** dengan impor PySide6/PyInstaller diblokir (plugin pytest di scratchpad, bukan di repo). **Belum / catatan:** `.venv` masih berisi PySide6 + PyInstaller karena skrip riset `.uji-data/riset-idx/*/render-pdf.py`, `baca-pdf.py`, `potong-pdf.py` memakainya; copot hanya bila skrip itu tidak dipakai lagi. Banyak catatan lama di berkas ini (Tahap 5, uji klik-ganda EXE, jebakan Qt/GC) kini **sejarah**. **Berikutnya:** tinjauan pengguna (K4). Sesudahnya kembali ke antrean data: fundamental/rasio bank, kalender 2021–2024, notasi, OHLCV primer BNBR/COCO/FISH/PYFA/SCCO/TMAS, representasi mutu harga PACK (K90).

**Terbaru — sesi 55, tahap B (K91):** dasbor web kini **menulis**: ubah stop (Dasbor), catat transaksi + keputusan right issue (Detail emiten), simpan rencana (Kalkulator risiko), catat jurnal (Jurnal), impor folder + cadangan (menu baru “Impor & cadangan”). Tiap tindakan lewat halaman **konfirmasi** (ringkasan yang sama dengan jendela) sebelum menulis; token sekali pakai + CSRF. **Test:** suite **941 lulus (54 dtk)**, `tests/test_web.py` 27 uji (tulis sesudah konfirmasi, batal tidak menulis, token sekali pakai, CSRF, kunci tulis jadi pesan, cadangan, jurnal, rencana). Dicoba di salinan `.tmp/web-coba`: konfirmasi cadangan di peramban, transaksi simulasi AUTO #1 lewat HTTP. **Belum:** pemulihan (`--pulihkan`) sengaja tidak ada di web (K59 e); tahap C (hapus `ui/`, PySide6, PyInstaller, `tools/build_exe.py`, `tests/test_pengemasan.py`, `tests/test_ui_jendela.py`; tanpa argumen → web). **Berikutnya:** tinjauan pengguna atas tahap B (K4), lalu tahap C. **Jebakan:** `Referrer-Policy: no-referrer` membuat peramban mengirim `Origin: null` sehingga POST tertolak — pakai `same-origin`. Uji cadangan harus memasang `MEJASAHAM_BACKUP` sendiri: uji lain bisa meninggalkan nilai itu di lingkungan proses.

**Terbaru — sesi 55 (K91):** pengguna mengganti antarmuka dari jendela PySide6 + EXE menjadi **dasbor web lokal**. Tahap A selesai: `python -m mejasaham --web` (opsi `--port`, `--tanpa-peramban`) membuka lima layar PRD 11 di `http://127.0.0.1:8765` — dasbor, screener (tombol "Jalankan saringan" menyimpan skor seperti `--saring`), detail emiten, kalkulator risiko (hitung saja), jurnal. Paket baru `mejasaham/web/`; `ui/tabel.py` + `ui/tulis.py` pindah ke `mejasaham/layar/`. **Test:** suite **929 lulus (70 dtk)**, termasuk `tests/test_web.py` (15). Diuji di salinan basis data kerja `.tmp/web-coba` (snapshot 14): peringkat web identik dengan `--saring --teratas 20`. **Belum:** tahap B (formulir tulis: transaksi, rencana, jurnal, ubah stop, right issue, impor, cadangan), tahap C (hapus `ui/`, PySide6, PyInstaller, `tools/build_exe.py`, `tests/test_pengemasan.py`; tanpa argumen → web). Jendela masih ada dan masih jadi bawaan tanpa argumen sampai tahap C. **Berikutnya:** tinjauan pengguna atas tahap A (K4), lalu tahap B. Rincian K91 `docs/keputusan.md`, T85 `docs/arsitektur.md`. **Jebakan:** jangan memulai ulang pekerjaan di setiap GET — halaman "sedang menghitung" memuat ulang diri, jadi kunci pekerjaan memakai penanda `kirim` per pengiriman formulir (bug ini sempat membuat uji menggantung). Dasbor atas basis data kerja masih butuh ±60 dtk bila `--saring` belum dijalankan pada snapshot terakhir.

**Pembersihan ruang 27 Okt 2026 (permintaan pengguna; di luar sesi produk):** repositori **≈10,4 GB → 2,56 GB** (sekitar 7,9 GB berkas terhapus; ±7,1 GB di antaranya ruang nyata). Angka 4,97 GB yang sempat kulaporkan **tidak sah** — banyak folder `.uji-data` tidak terbaca karena ACL sisa sandbox sesi sebelumnya, dan angka 7,48 GB pun baru terukur sesudah tahap pertama. Jadi perkiraan pengguna ("sampai 10 GB") memang tepat. **Dihapus:** sandbox uji (`.uji-data/mejasaham-exe` 823 MB · `uji-tahap5/salinan*` 422 MB · `uji-k61/mejasaham.db` 236 MB · `uji-k61-cadangan` 227 MB), duplikat build (`.tmp/candidate-dist` + `candidate-build` 233 MB · `build/` 51 MB), `dist/` 183 MB (**EXE hilang — bangun ulang dengan `tools\build_exe.py`**), `.tmp/py313` 769 MB, seluruh `__pycache__` 91 MB, cadangan lama (`mejasaham-cadangan` tiga salinan 2,60 GB · `cadangan-sesi49/20261022T111550896890+0700` 820 MB · `cadangan-sesi40` 368 MB · `mejasaham-exe-cadangan` 368 MB), `pytest-of-PENGGUNA` 271 MB, `.uji-data/mejasaham.db` 229 MB, `.uji-data/arsip-snapshot` 147 MB, dan cache uv 1,01 GB (`uv cache clean`, di luar repo). **Tetap:** `.uji-data/mejasaham` (basis data kerja 236 MB + `arsip-snapshot/2026-10-11`), `.uji-data/cadangan-sesi49/20261022T111553703187+0700` (cadangan terakhir sebelum impor sesi 50), `riset-idx`, seluruh berkas bukti kecil, dan `.venv` (787 MB). **Catatan jujur:** (a) `.tmp/py313` ternyata **hardlink** ke cache uv — menghapusnya hanya membebaskan **1,8 MB** ruang nyata, dan baru `uv cache clean` mengembalikan 960 MB; (b) cadangan 16 Okt dan 19 Okt yang dikutip sebagai bukti sesi 37/50 **tidak ada lagi**; (c) `.uji-data/mejasaham.db` (salinan bersih) hilang, jadi perintah bagian 3 yang memakainya kini harus memakai salinan `.uji-data/mejasaham` atau `--buat-cadangan`; (d) `pytest` **914 lulus (163,62 dtk)** — lebih lambat dari 48,53 dtk karena `__pycache__` dihapus. Rincian: `docs/keputusan.md` bagian 5, "Pembersihan ruang repositori (27 Okt 2026)".

**Terbaru — sesi 54:** Pay Per Use TICMIDATA untuk `Data Transaksi Harian Saham` menampilkan bar BNBR (13–16 Feb 2023), COCO, PYFA, SCCO, TMAS (23–24 Mei 2023); FISH hanya previous/close. Nilai detail dalam tabel sesi 54 `docs/riset-harga-snapshot4-2026-10.md`. Ini hasil Preview, bukan ekspor yang dibeli; belum dikonfirmasi hak pakai, sehingga belum diimpor/dibagikan. PYFA punya beda basis besar; BNBR/COCO berbeda dari snapshot. Test tidak dijalankan (riset); tidak ada perubahan database. Berikutnya: tinjau hasil, konfirmasi syarat lisensi melalui kanal TICMI yang dipublikasikan, lalu hanya jika ekspor berizin tersedia cocokkan sumber/provenance dan basis harga. Berhenti sesuai K4. Cara mengulang: halaman TICMIDATA Pay Per Use, jenis `Data Transaksi Harian Saham`, lalu masukkan kode/tanggal target dan Preview; rincian produk/sumber ada di catatan sesi 54 `docs/keputusan.md`.

**Terbaru — sesi 53:** pencarian untuk ticker/tanggal target dan arsip harian publik tidak menemukan OHLCV primer IDX yang dapat dibuka; hasil vendor/pihak ketiga dikesampingkan. Endpoint harian IDX yang dicoba sebelumnya masih 403. Ekspor resmi EoD/historis berizin belum diperoleh. Tes tidak dijalankan (pemeriksaan sumber); tidak ada perubahan data/harga. Berikutnya: cocokkan enam seri hanya bila ekspor berizin tersedia: BNBR 16 Feb 2023; COCO 30 Sep 2025; FISH 1 Sep 2025; PYFA 16 Apr 2024; SCCO 1 Feb 2024; TMAS 23–24 Mei 2023. Lihat sesi 53 dan sesi 52 `docs/keputusan.md`. Tahap berhenti sesuai K4. Cara menjalankan: bandingkan ekspor OHLCV berprovenance yang diizinkan dengan `harga.csv` snapshot 4; tidak ada perintah tes relevan.

**Terbaru — sesi 50:** draf catatan aksi mutu PACK telah ditinjau dan diimpor ke `.uji-data/mejasaham` setelah cadangan. Snapshot 14 memuat 1 baris baru; laporan menampilkan 5 konteks aksi dan tetap memuat 9 temuan tak wajar. `PRAGMA integrity_check` = `ok`. **Test tahap:** tidak dijalankan saat impor; sesi 49 sebelumnya melaporkan suite penuh `914 passed (48,53 dtk)`. **Ringkasan:** impor dan verifikasi provenance catatan PACK. **Belum:** OHLCV primer enam ticker BNBR, COCO, FISH, PYFA, SCCO, TMAS; konteks aksi tidak mengesahkan bar vendor. **Cara menjalankan:** `python -m mejasaham --impor <folder-berisi-catatan-aksi-mutu.csv> --folder-data .uji-data/mejasaham`; rincian/cadangan di sesi 50 `docs/keputusan.md` bagian 5. Tahap berhenti sesuai K4.

**Sesi 47:** pengguna menyetujui rekomendasi: PACK hanya dicatat untuk mutu harga pada v0.1; OWK sebagai instrumen posisi dan konversinya menjadi saham ditunda ke tahap terpisah (K90). Draf `docs/draf-aksi-korporasi-PACK-2026-10.csv` tidak boleh diimpor sebagai `right_issue` operasional: `posisi.hak_right_issue()` menghitung rasio sebagai hak saham dan keputusan `tebus` menunjuk transaksi saham. Belum ada representasi mutu-harga yang terpisah dari aksi posisi; rancang dan tinjau sebelum impor. Tidak ada perubahan kode/basis data; tes tidak dijalankan (pencatatan keputusan). **Berikutnya:** siapkan desain representasi mutu harga yang tidak menimbulkan hak posisi atau penyesuaian harga yang belum terverifikasi, lalu berhenti untuk tinjauan. Enam ticker BNBR, COCO, FISH, PYFA, SCCO, TMAS tetap menunggu OHLCV primer. Rujuk K90 dan sesi 47 `docs/keputusan.md`. Tidak ada perintah tes relevan.

**Sesi 46:** OJK mendefinisikan HMETD mencakup pembelian saham dan/atau efek ekuitas lain yang dapat
dikonversi menjadi saham; KSEI menyebut PACK memberi 102 HMETD per 5 saham dan tiap HMETD membeli
1 OWK Rp100 yang dikonversi 1:1. Karena itu `right_issue`, rasio 5:102, dan harga tebus 100
bermakna untuk merekam aksi. Namun model keputusan posisi hanya mengikat `tebus` ke transaksi saham
dan tidak memodelkan OWK. Draf tetap di `docs/draf-aksi-korporasi-PACK-2026-10.csv`; **jangan impor**
sampai cakupan OWK pada posisi diputuskan. Tidak ada perubahan basis data; tes tidak dijalankan
(pemeriksaan dokumen/kode). Enam ticker BNBR, COCO, FISH, PYFA, SCCO, TMAS masih menunggu OHLCV
primer. **Berikutnya:** putuskan apakah OWK akan didukung sebagai instrumen posisi atau PACK hanya
dicatat untuk mutu harga; setelah itu nilai impor. Lihat sesi 46 `docs/keputusan.md` bagian 5 dan
`docs/riset-harga-snapshot4-2026-10.md`. Cara mengulang: telaah draf, `docs/skema-data.md` §5.14,
serta alur `keputusan_right_issue` di `mejasaham/posisi.py`. Tidak ada perintah tes relevan.

**Sesi 45:** pembacaan ulang KSEI-0064/DIR/00126 memastikan tanggal pelaksanaan HMETD PACK 22 Jan
2026 dan distribusi OWK 26 Jan. Surat 23 Jan menjelaskan hak HMETD dan distribusi; contoh 26 Jan
bukan tanggal pelaksanaan. Draf `docs/draf-aksi-korporasi-PACK-2026-10.csv` kini memuat
`tenggat=2026-01-22`; belum diimpor sambil menunggu tinjauan semantik `right_issue` untuk HMETD OWK.
Rincian dan sumber primer: `docs/riset-harga-snapshot4-2026-10.md` bagian “Klarifikasi tenggat
PACK”. Tidak ada perubahan basis data; tes tidak dijalankan (pemeriksaan dokumen). Tahap berhenti
sesuai K4. **Berikutnya:** tinjau klasifikasi/rasio draf sebelum mempertimbangkan impor; enam kode
BNBR, COCO, FISH, PYFA, SCCO, TMAS tetap menunggu seri OHLCV resmi yang cocok.

Sesi 39 — K89: pembaruan yang jatuh tempo diberitahukan dan ditawarkan sebagai tindakan terpisah;
`--refresh` tidak menjalankan pengambilan/impor dataset lain otomatis. Sumber notasi/suspensi/UMA
resmi IDX tersedia (`--ambil-notasi` → CSV → `--impor`); pengambilan baca-saja berhasil 22 Okt
dengan data halaman notasi per 20 Okt 2026. Checklist U36 lintas dataset belum diimplementasikan.
Sesi 37 — EXE gagal memuat QtCore karena DLL ICU 78 dari PATH build bertabrakan dengan Qt. Build
kini memakai PATH bersih; EXE dibangun ulang, GUI lolos uji offscreen, dan suite penuh 911 lulus.
Pengguna melaporkan GUI sudah terbuka dan refresh pertama berhasil.
**Sesi 34 — AKSI #23/U26 SELESAI: konteks pasar ditulis `--saring` dan dibaca dasbor hanya bila
snapshot + preset + label sumber harga + versi hitung masih sama; `--dasbor` 18,95 dtk → 0,74 dtk
(25,7×) dengan baris `Pasar` identik; migrasi 015; `pytest` → 906 lulus**.
**Sesi 33 — HITUNG LANGKAH MANUAL K79 SELESAI: dari 44 bank sasaran, 8 menuntut langkah manual ·
2 tidak terukur · 34 boleh otomatis; izin robots bukan jaminan dokumen ketemu (12/34 halaman
publikasi nyata — 16 dengan jangkar — dan 11/34 tautan PDF); **U35 dikunci sebagai K88 = tetap
ditunda**; `pytest` → 887 lulus**.
**Sesi 32 — PRASYARAT K87 DIJALANKAN: `jenis` terisi, **49 bank_keuangan** · 862 umum · 62 kosong,
kriteria bank **kini diterapkan**; 44 dokumen rasio **tetap ditunda**; `pytest` → 887 lulus**.
**Sesi 32 mengisi `jenis` dari sumber data** (K21): `--ambil-jenis --timpa-jenis` → 973 baris,
**49 bank_keuangan · 862 umum · 62 kosong** (55 kode gagal diambil — yang tercantum di log
`HTTPError: HTTP 404` — + 7 tanpa sector/industry),
cadangan lebih dulu, lalu `--impor` → **snapshot 13**, **973 baris baru / 4255 sudah sama**, tabel
lain **tidak berubah** (`notasi_khusus` tetap 12.047 — impor dari folder yang **sama** tidak
menulis ulang label; beda dengan jebakan sesi 31). **Akibatnya terukur:** `--saring` kini
melaporkan **49 bank_keuangan (dari data)**, kriteria **NPL/CAR/BOPO/NIM berlaku** untuk mereka dan
**DER/coverage/CFO-NI tidak dihitung** (PRD 8.4/AC-16); **BBCA** mendapat vonis nyata — keempat
rasio bank **lolos** (186/2679/4122/532 bp) dan ia kini gagal karena `pbv_relatif_sektor` +
`tren_ma200`, bukan "tidak bisa dinilai"; **BRIS** hanya `car`+`bopo` yang dinilai (NPF/NI tetap
tidak dipetakan, K77). **Peringkat TIDAK berubah** — tetap **9 lolos/9 dinilai**, sembilan kandidat
sama persis — jadi **K68 terbukti lagi**. **47 dari 49 bank belum punya rasio** (hanya BBCA & BRIS
yang punya), sebabnya berbunyi *"rasio bank … belum diimpor lewat rasio-bank.csv"*; **44 dokumen
tetap ditunda (K87)**, dan **hitung langkah manual (K79) belum dijalankan**. Rincian: blok
"Sesi 32" di bawah, `docs/keputusan.md` bagian 5, bukti `.uji-data/uji-jenis-kerja/bukti/`.
**Aksi #29 (K83, sesi 31) sudah dijalankan:** SHA-256 kedua PDF = manifest, halaman dirender ulang,
**seluruh 14 sel cocok persis**, cadangan dibuat lebih dulu, dua baris masuk
`konfigurasi/rasio-bank.csv`, dan `--impor` keluar 0 → **snapshot 12** dengan **2 baris
`rasio_bank`**; `v_rasio_bank_terkini` memuat keduanya (186/2679/4122/532 bp dan
`None`/2041/6971/`None` bp). **`--saring` belum berubah** — sebabnya terukur: **`jenis` 973 emiten
masih kosong**, jadi kriteria bank tidak diterapkan kepada siapa pun, dan BBCA/BRIS tetap gagal
`coverage` (EBIT tahunan). **Sesi 32 mengisi `jenis`**, jadi sebab itu **sudah hilang**; yang
tersisa dari K87 hanyalah **44 dokumen** (dihitung manual lebih dulu, K79). **K86 menutup U34**:
`tgl_publikasi` BRIS **tetap 2026-08-21** (tanggal tercetak yang diverifikasi).
**Tidak ada usulan yang menunggu jawaban** — K85–K87 dikunci sesi 31; K82 selesai di sesi 29 (aksi
#28/T78), dan sesi 30
mengunci **K83** (verifikasi angka `rasio_bank` **dialihkan ke agen** dengan pagar "cocok persis" →
**aksi #29**) serta **K84** (pengiriman laporan PySide6 **tetap pengguna**). Dua usulan
sesudah K69 juga sudah dikunci: **K74 = jangan pin CPython 3.13**
(3.14.7 + T68 tetap; laporan upstream dikirim; pin hanya ditinjau ulang bila Qt menjawab atau
cacatnya muncul lagi) dan **K75 = perbaiki uji flaky**, pelaksanaannya **aksi #26** — **sudah
selesai di sesi 23** (T76).
**Urutan pekerjaan berikutnya (K80, diperbarui K83): (1) ~~aksi #27~~ SELESAI 19 Okt 2026
(sesi 27)** — bidang `sumber` di `RasioBank` kini diisi dari kolom berkas dan tersimpan per baris,
dan ia kembali lagi lewat `potret` (T77); **(1b) ~~aksi #28~~ SELESAI 19 Okt 2026 (sesi 29)** —
`potret._fundamental` kini mengisi `Fundamental.sumber` saat membaca ulang (T78); **(2) ~~aksi #29~~
SELESAI 19 Okt 2026 (sesi 31, T79)** — verifikasi ulang angka kandidat (K83) **14/14 sel cocok**,
lalu `konfigurasi/rasio-bank.csv` diisi (hanya sembilan kolom `rasio_bank`) dan `--impor` dijalankan
(snapshot 12; `v_rasio_bank_terkini` memuat dua bank), tetap **`--saring` belum berubah** karena
`jenis` kosong — **itu hasil yang dilaporkan, dan sesi ini berhenti di situ**; **(3) berikutnya**
putuskan perluasan ke 44 bank — hitung dulu berapa bank yang menuntut langkah manual (K79; ingat juga
**0 dari 49 bank tertahan *hanya* oleh rasio bank** — K68). **Prasyaratnya sudah dijalankan sesi 32**
(`jenis` terisi: 49 bank, kriteria bank diterapkan, 47 bank belum berasio); **44 dokumen tetap
ditunda (K87)**, dan **K79 SUDAH dihitung sesi 33: 8 manual · 2 tidak terukur · 34 otomatis**, dengan
usulan **U35 = tetap tunda** — **dikunci 19 Okt 2026 sebagai K88** (rincian
`docs/rasio-bank-kandidat-2026-10.md` §10). **Pengiriman
laporan PySide6 tetap pekerjaan manusia (K84).**
**Aksi #23/U26 SELESAI 19 Okt 2026 (sesi 34)** — konteks pasar ditulis `--saring` dan dibaca dasbor
hanya bila snapshot + preset + label sumber harga + versi hitung masih sama (`--dasbor` **18,95 →
0,74 dtk**, 25,7×; **T80**), dan **`--pulihkan` bukan pekerjaan tertunda** (K59 e/K64).
Pekerjaan yang tinggal **manusia** kini **satu**: mengirim **laporan PySide6**
(`docs/laporan-pyside6-siap-kirim.md`, K66 — laporannya sudah memuat kontrol yang gagal: 2/12;
**K84** menegaskan pengiriman tidak dialihkan). Sisa **Tahap 5** juga bukan pekerjaan kode:
**uji klik-ganda di mesin tanpa Python** (**T81/T82**); ikon aplikasi kini dibuat dalam sesi 36. **Verifikasi angka `rasio-bank.csv`** (K68) sudah
**dijalankan 19 Okt 2026 (sesi 31, K83 → aksi #29)** — kandidatnya ada di
`docs/rasio-bank-kandidat-2026-10.md` (**2 bank** berangka, BRIS dua kolom kosong menurut K77) dan
**kedua barisnya kini ada di basis data kerja**. **Seluruh cakupan tindakan tulis jendela (K59 c) sudah
terpenuhi** sejak sesi 18. **Keadaan git:** pekerjaan sesi 11–19 sudah di-commit (`874e095`,
`82f3064`, `3565d02`, `2aacd2b`, lalu catatan keadaan git), dan **sesi 20–32 kini JUGA sudah
di-commit** (19 Okt 2026, atas permintaan pengguna): **`4bbaf20`** = kode + uji sesi 20/23/27/29,
**`eb30214`** = dokumen sesi 21–32, lalu **catatan keadaan git ini**. Data sesi 31–32 (snapshot
12/13, 2 baris `rasio_bank`, `emiten.csv` berisi `jenis`) tetap **gitignored** — tidak ikut commit.
**Sesi 33 dan 34 sudah di-commit** (19 Okt 2026, atas permintaan pengguna): **`c862d16`** = kode +
uji aksi #23, lalu **commit dokumen ini** = catatan sesi 33–34 (K79/K88, K61/T80). Sesi 33
menyunting tiga berkas `docs/`; sesi 34 menyunting empat berkas kode + tiga berkas uji + empat
dokumen (rincian di blok sesi 34). **Sesi 35 sudah di-commit sebagai 517aabc**;
berkasnya `requirements-build.txt`, `tools/entry_exe.py`, `tools/build_exe.py`,
`tests/test_pengemasan.py`, `README.md`, `AGENTS.md`, dan tiga berkas `docs/`.
**Pembersihan ruang 17 Okt 2026 (lanjutan sesi 19,
atas permintaan pengguna):** seluruh salinan basis data + ekspor `arsip-snapshot` di dalam
`.uji-data/uji-*` dan folder
`*-cadangan/`-nya dihapus — total repositori **44,99 GB → 3,49 GB**; basis data kerja, `riset-idx`,
seluruh berkas bukti, dan satu cadangan terbaru **tetap**. Akibatnya perintah di bagian 3 yang menunjuk
`.uji-data/uji-<nama>` **harus membangun ulang sandboxnya lebih dulu** — baca peringatan di awal
bagian 3 dan baris jebakannya di bagian 6.

**Sesi 35 (Tahap 5 — bundel PyInstaller onedir; SELESAI SEBAGIAN, 19 Okt 2026):** "Lanjutkan"
dibaca sebagai permintaan melanjutkan, tetapi tidak ada aksi terkunci; sesi bertanya arah dan
pengguna menjawab **"sesuai rekomendasimu"**. Pilihan yang diambil: **Tahap 5 — pengemasan**,
karena seluruh fitur v0.1 sudah jalan, **T3** sudah mengunci PyInstaller onedir, dan syarat lama
"kemas sesudah impor & cadangan punya jalur di jendela" sudah terpenuhi. Pijakan: `pytest` **906
lulus (29,08 dtk)**, working tree bersih di `2b90e91`. Yang dibangun: **`requirements-build.txt`**
(PyInstaller 6.22.3 + transitive dipin; **tidak** masuk `requirements.txt`), **`tools/entry_exe.py`**
(titik masuk yang memanggil `cli.main`, jalur yang sama dengan `python -m mejasaham`),
**`tools/build_exe.py`** (satu daftar argumen `--onedir --console --hide-console hide-early --noupx`,
`--add-data mejasaham/defaults`, `--dry-run`, kode keluar diteruskan), dan
**`tests/test_pengemasan.py`** (2 uji kontrak). **Bukti:** build → `dist\MejaSaham\MejaSaham.exe`
15,3 MiB + `_internal/` **184,5 MB**; `--help` keluar 0; `--muat-konfigurasi --folder-data` folder
kosong menyalin template + membuat basis data, **keluar 0** dengan peringatan parameter ke stderr;
`--saring` **18,40 dtk** dan `--dasbor` **0,97 dtk** pada salinan data kerja, keluarannya **identik**
dengan jalur modul (18,13 dtk / 0,76 dtk); `--ambil-fundamental --kode BBCA` membuktikan
yfinance/pandas ikut terbawa (4 baris ditulis); GUI `offscreen` hidup 8 dtk pada data kosong dan
salinan berisi snapshot (data kosong menampilkan kegagalan "belum ada snapshot", bukan crash); salinan folder aplikasi dijalankan dengan `PATH` **tanpa** `.venv`/Python
dan `PYTHONHOME`/`PYTHONPATH` kosong → `--help` dan `--muat-konfigurasi` tetap keluar 0. Suite
**908 lulus (38,12 dtk)**. **Yang TIDAK dikerjakan:** ikon aplikasi (belum ada aset; PyInstaller
memakai ikon bawaan), uji klik-ganda di mesin yang benar-benar tanpa Python, **44 bank** (K88),
pengiriman laporan PySide6 (K84), dan commit. **Tanpa** perubahan kode aplikasi, `requirements.txt`,
atau basis data kerja; `.venv` hanya menerima **alat build**, bukan dependensi runtime baru. Bukti di
`.uji-data/uji-tahap5/` (**gitignored**). Rincian:
`docs/keputusan.md` bagian 5 (sesi 35) dan **T81** `docs/arsitektur.md`.

**Sesi 34 (aksi #23/U26 — konteks pasar disimpan saat `--saring`; SELESAI, 19 Okt 2026):**
"Lanjutkan" dibaca sebagai permintaan melanjutkan, tetapi **tidak ada aksi terkunci yang menunggu**
(K88 menunda 44 bank; #23/U26 belum dipicu; `--pulihkan` batas cakupan). Karena itu sesi
**bertanya arah**, dan pengguna memilih **#23/U26** — pemicu eksplisit yang dituntut K61. Pijakan:
`pytest` **887 lulus (44,19 dtk)**. Yang dibangun: migrasi **015** `konteks_pasar` (kunci
snapshot+preset+sumber, `versi_hitung`, breadth status/alasan/asal, indeks, catatan; CHECK
"dihitung"⇔nilai dan "tidak dihitung"⇔alasan); modul baru **`mejasaham/konteks_pasar.py`**
(`BarisIndeks`/`KonteksPasar` pindah ke sana, `simpan`/`muat`/`dari_bahan`/`sebab_bahan_kurang`,
`VERSI_HITUNG="pasar-1"`); `pengatur.jalankan_saring` menulis konteks hanya bila `simpan=True`
(gagal tulis → **peringatan**, saringan tetap sah); `dasbor.susun` membacanya hanya bila
**snapshot + preset + label sumber harga + versi hitung** cocok, selain itu **menghitung ulang**.
**Bukti:** 19 uji baru; **5 uji perilaku gagal pada worktree `HEAD` `6888b1b`** dan modul baru gagal
koleksi; suite **906 lulus**; jendela+tulis+tabel **6× 92 lulus**. Atas **salinan** data kerja
(snapshot 13): `--dasbor` **18,95 → 0,74 dtk (25,7×)**, baris `Pasar` identik, `--saring`
**18,16 dtk**. **Yang TIDAK dikerjakan:** 44 bank (K88), #22(a) (manusia/K84), `--pulihkan`
(K59 e/K64), dan commit — **basis data kerja tidak disentuh** (hanya salinan). Rincian:
`docs/keputusan.md` bagian 5 (sesi 34), **T80**, `docs/skema-data.md` 5.16; bukti
`.uji-data/uji-k61/bukti/`.

**Sesi 33 (K79 — hitung langkah manual untuk 44 bank; SELESAI, 19 Okt 2026):** "Lanjutkan" dibaca
sebagai permintaan menjalankan **langkah yang tersisa dari K87** — *hitung dulu berapa bank yang
menuntut langkah manual* (K79) — **bukan** persetujuan menambah 44 dokumen. Pijakan diperiksa dulu
(`pytest` → **887 lulus**, 46,76 dtk), lalu pengukuran baca-saja dijalankan: **(a) domain resmi**
tiap bank ditetapkan dari judul halaman depannya (empat calon domain terbukti salah dari isinya:
`bumiarta.co.id` "Coming Soon", `bankoke.com` halaman parkir, `bankmnc.com` "Coming Soon",
`bankcapital.id` tidak ada, lalu diganti); **(b) `robots.txt`** diurai per grup `User-agent`
(token `mejasaham` lalu `*`) dan diuji ke **11 jalur wakil**; **(c) keterjangkauan situs** diuji
dengan klien HTTP biasa, **tiga percobaan** untuk tiap kegagalan, halaman tantangan dikenali dari
isinya. **Hasil untuk 44 bank sasaran** (49 `bank_keuangan` − BBCA/BRIS − BBRI/BMRI/BBNI):
**8 MANUAL · 2 tidak terukur · 34 otomatis mungkin**. Manual karena **robots**: **BTPS**
(`Disallow: /`) dan **DNAR** (`/media`, `/images`); manual karena **akses**: **AGRS** (WAF F5 3/3),
**BBMD** (Cloudflare 403 3/3), **BBTN** (Incapsula 212 byte 3/3), **BNLI** (403 Access Denied 3/3),
**SUPA** (403 3/3), **BACA** (502 3/3 — situs tidak melayani saat diukur). Tidak terukur karena
jaringan: **INPC** (connect timeout) dan **SDRA** (SSL error) — **bukan** bukti kebijakan bank.
**Kontrol metode:** ketiga bank pilot di luar sasaran diukur ulang dan **konsisten dengan K79** —
BMRI `Disallow: /*.pdf$`, BBNI `Disallow: /Portals/` + Incapsula, dan **BBRI situsnya terjangkau**
(307 → 351.497 byte pada percobaan ke-2) sehingga yang gagal di sana memang dokumennya.
**Temuan yang mencegah janji berlebih:** uji satu tingkat atas 34 bank "otomatis mungkin" hanya
menemukan **12 halaman publikasi nyata** (16 bila jangkar halaman depan ikut dihitung) dan
**11 tautan PDF** — batas bawah, sebab situs ber-JavaScript tidak menampakkan tautannya kepada klien
HTTP biasa; isi PDF-nya pun belum diperiksa. Jadi **izin robots ≠ dokumen ketemu**; 34 bank
itu tetap menuntut pencarian + render + verifikasi sel seperti pilot (K76/K83). **Usulan U35**
(`docs/keputusan.md` bagian 2): **tetap tunda**; bila kelak diminta, **34 otomatis dulu**, lalu
**8 manual** hanya bila PDF-nya tersedia (K79: pengguna mengunduh sendiri, tidak diakali).
**Sesudah itu pengguna menjawab "sesuai rekomendasi saja, catet jangan ngoding" → U35 dikunci sebagai
K88: 44 dokumen TETAP DITUNDA**, urutan 34-otomatis-dulu tetap berlaku bila kelak diminta; sesi
pencatatan itu **tanpa kode/impor/basis data**, dan **tidak ada pertanyaan yang menunggu**.
**Yang TIDAK dikerjakan:** 44 dokumen (K87/K88), #23/U26 (K61), `--pulihkan` (K59 e/K64), dan commit.
**Tanpa perubahan kode/uji dan tanpa satu baris basis data**; bukti `.uji-data/uji-k79/bukti/`
(`k79-hasil-final.csv` 49 baris, `k79-ringkasan.txt`, `k79-pindai-robots.csv`/`.json`,
`k79-uji-halaman.csv`/`.json`, 49 berkas `robots-<KODE>.txt`, log tiap tahap).
Rincian: `docs/keputusan.md` bagian 5 (sesi 33) dan `docs/rasio-bank-kandidat-2026-10.md` **§10**.

**Sesi 32 (prasyarat K87 — `jenis` diisi dari sumber data; SELESAI, 19 Okt 2026):** "Lanjutkan"
dibaca sebagai permintaan menjalankan **langkah prasyarat** yang sudah dikunci K87, bukan sebagai
persetujuan menambah 44 dokumen. Pijakan diperiksa dulu (`pytest` → **887 lulus**, 29,77 dtk),
lalu: **(a) ukur keadaan** — `jenis` **973 NULL**, `sektor_sumber` **0**, dan `emiten.csv` di folder
data **identik** dengan basis data (0 selisih; jadi menimpa berkasnya tidak menghilangkan suntingan
tangan); **(b) cadangkan** (`--buat-cadangan` → `.uji-data\mejasaham-cadangan\20261019T182735608155+0700`);
**(c) `--ambil-jenis --timpa-jenis`** (973 kode, ~35 menit, 0,4 dtk jeda) → **49 bank_keuangan ·
862 umum · 62 kosong**; 62 kosong = **55 kode gagal diambil** (log menampilkan `HTTPError: HTTP
404` untuk 15 di antaranya) + **7** yang sumbernya tidak
menyatakan sector/industry; **(d) periksa** — kolom selain `jenis`/`sektor_sumber`/`sumber`
**0 beda**, 973 kode sama, `bank_keuangan` 49 (AGRO…SUPA), `siklikal_komoditas` **0** (tidak pernah
diturunkan, K21); **(e) impor** → **snapshot 13**, **973 baris baru / 4255 sudah ada dan sama**,
`notasi_khusus` **tetap 12.047** (impor dari folder yang **sama** tidak menulis ulang label),
`rasio_bank` tetap 2, `PRAGMA integrity_check` = `ok`; **(f) buktikan** — `--saring` kini **49
bank_keuangan**, kriteria bank **diterapkan**, BBCA keempat rasio **lolos** (186/2679/4122/532 bp)
dan vonisnya berubah dari *"tidak bisa dinilai (coverage)"* menjadi **gagal** karena
`pbv_relatif_sektor` + `tren_ma200`; BRIS hanya `car`/`bopo` dinilai (K77). **Peringkat tidak
berubah: 9 lolos/9 dinilai, sembilan kandidat sama persis** — K68 terbukti lagi. **47 dari 49 bank
belum punya rasio** (hanya BBCA & BRIS), dengan alasan *"rasio bank … belum diimpor lewat
rasio-bank.csv"* — itulah yang akan diisi bila 44 dokumen diminta. **Yang TIDAK dikerjakan:** 44
dokumen (K87, tetap ditunda), **hitung langkah manual (K79)** untuk 44 bank, #23/U26 (K61),
`--pulihkan` (K59 e/K64), dan commit — **commit lalu dikerjakan atas permintaan pengguna pada sesi
yang sama** (`4bbaf20` kode sesi 20–29, `eb30214` dokumen sesi 21–32, lalu catatan keadaan git ini). **Tanpa perubahan kode/uji**; bukti
`.uji-data/uji-jenis-kerja/bukti/` (`ambil-jenis.log`, `banding-csv.txt`, `impor-produksi.txt`,
`db-sebelum.txt` vs `db-sesudah.txt`, `saring-sesudah.txt`, `kriteria-sebelum.txt` vs
`kriteria-sesudah.txt`, `ringkas-bank-sesudah.txt`, `impor-sandbox.txt`). Rincian: `docs/keputusan.md`
bagian 5 (sesi 32) dan penunjuk di K21/K80/K87.

**Sesi 31 (aksi #29 — K83: verifikasi ulang angka `rasio_bank` + impor; SELESAI, 19 Okt 2026):**
pijakan diperiksa dulu (`pytest` → **887 lulus**, 44,93 dtk), lalu K83 dijalankan apa adanya.
**(a) Hash:** SHA-256 kedua PDF dihitung ulang dan **sama dengan `manifest-unduhan.txt`** (BCA
`964526…`, BRIS `bc62a1…`). **(b) Render ulang** ke `.uji-data/uji-k83/bukti/` — bukan memakai PNG
pilot — untuk BCA hlm. 5 dan poster BRIS (blok rasio, kepala kolom, tanda tangan). **(c) 14 sel**
(`periode`, `tgl_publikasi`, empat rasio, `sumber` × 2 bank) **cocok persis**; kolom BRIS diputuskan
dari **render**, sebab lapisan teks menaruh "30 Juni 2025" lebih dulu. **(d) Tanggal publikasi** BCA
diperiksa dengan **HEAD ulang** (`Last-Modified Tue, 28 Jul 2026 09:13:08 GMT`; `Content-Length`
196142 = berkas lokal); BRIS 21 Agu 2026 dari tanda tangan yang terbaca. **Cadangan lebih dulu**
(`.uji-data\mejasaham-cadangan\20261019T181212314095+0700`), lalu dua baris ke
`konfigurasi/rasio-bank.csv` (sembilan kolom; `url`/`tanggal_akses`/`kutipan` dibuang; dua kalimat
`keterangan` basi dibersihkan), **dibaca ulang** lewat `berkas.baca_folder` (seluruh sel sama dengan
kandidat), lalu `--impor` → **keluar 0, snapshot 12**, 2330 baris baru / 2898 sudah sama:
**`rasio_bank` 0 → 2**, `notasi_khusus` +2328 yang **hanya** berbeda di kolom `sumber` (label folder
impor; 0 beda lain), tabel lain tidak berubah; `PRAGMA integrity_check` = `ok`. **`--saring` belum
berubah** (973 emiten, **9 lolos/9 dinilai**); sebabnya terukur, bukan dugaan: **`jenis` 973 emiten
masih kosong** sehingga kriteria bank tidak diterapkan, dan BBCA/BRIS tetap gagal `coverage` (EBIT
tahunan). **Dua catatan yang tidak disembunyikan:** **U34** (tanggal BRIS 21 Agu tanda tangan vs
24 Agu `Last-Modified` — yang diimpor nilai tercetak, selisihnya dicatat) dan **jebakan baru**
(impor satu folder menulis ulang label `sumber` baris `notasi_khusus`; bagian 6). **Tanpa perubahan
kode/uji**; bukti `.uji-data/uji-k83/bukti/` (`bukti-ringkas.txt`, `bukti-verifikasi.txt`, render PNG,
`db-sebelum.txt` vs `db-sesudah.txt`). Rincian: `docs/keputusan.md` bagian 5 (sesi 31) dan **T79**
`docs/arsitektur.md`.

**Sesi 31 (lanjutan pencatatan — K85–K87; 19 Okt 2026, tanpa perubahan kode/data):** pengguna
menjawab **"sesuai rekomendasi"** atas tiga hal yang diajukan sesudah aksi #29 dilaporkan. Yang
dikunci: **K85** — impor yang menulis ulang `sumber` **2.328** baris `notasi_khusus` **diterima apa
adanya** (2.328/2.328 hanya `sumber`; 0 beda lain; **tidak** ada pemulihan cadangan). **K86** —
**U34 ditutup**: `tgl_publikasi` BRIS **tetap 2026-08-21**; perbaikan kelak hanya lewat baris revisi
bila ada bukti resmi tanggal terbit. **K87** — **44 bank DITUNDA**; prasyaratnya `jenis` **973**
emiten masih kosong, dan `--ambil-jenis` **tidak** dijalankan tanpa permintaan; urutan bila diminta:
hitung langkah manual (K79) → isi `jenis` → buktikan rasio dipakai → baru tambah 44 dokumen.
**Tidak ada baris basis data yang ditulis**; status uji sesudah pencatatan **`pytest` → 887 lulus**
(tidak berubah). Rincian: `docs/keputusan.md` bagian 1 (K85–K87) dan bagian 5 (catatan sesi 31
lanjutan).

**Sesi 30 (pencatatan saja — K83/K84; 19 Okt 2026):** pengguna menjawab **"sesuai rekomendasimu aja,
kalau ada butuh pekerjaan manusia, bisa kamu aja ga yang lakuin? catet dulu nanti kulanjutkan di sesi
baru"**, jadi sesi ini **hanya mencatat**: tanpa perubahan kode/uji, tanpa impor, tanpa menyentuh
basis data. Yang dikunci: **K83** — **verifikasi angka `rasio_bank` dialihkan ke agen** dengan pagar
"cocok persis" (baca ulang PDF resmi, cocokkan SHA-256 dengan manifest, bandingkan **setiap** sel;
satu selisih → berhenti, 0 baris ditulis), dikerjakan sebagai **aksi #29**; **K84** — **pengiriman
laporan PySide6 tidak dialihkan** (butuh akun + tindakan di luar repositori), tetap pekerjaan
pengguna. **Cara membaca "sesuai rekomendasimu aja" dicatat eksplisit:** persetujuan **cara kerja**,
**bukan** pernyataan bahwa angkanya sudah benar — status berkas tetap **kandidat, belum diverifikasi,
belum diimpor**, dan `konfigurasi/rasio-bank.csv` (folder data) tidak disentuh. Status uji sesudah
pencatatan: **`pytest` → 887 lulus** — tidak berubah, seperti diharapkan. Rincian:
`docs/keputusan.md` bagian 1 (K83–K84) dan bagian 5 (sesi 30).

**Sesi 29 (aksi #28 — K82; SELESAI, 19 Okt 2026):** pijakan diperiksa dulu (`pytest` → **885 lulus**,
45,31 dtk), lalu K82 dijalankan apa adanya: **satu baris** di `mejasaham/potret.py` —
`_fundamental` kini mengisi `sumber=baris["sumber"]` — sehingga provenance laporan tidak lagi hilang
saat baris dibaca kembali. **Jalur tulis tidak disentuh** (kolom `fundamental.sumber` sudah
`NOT NULL` dan sudah ditulis per baris sejak K18), jadi yang ditambahkan hanyalah pembacaan yang
selama ini membuang nilai itu. **Dua uji baru** di `tests/test_potret.py`: **(a)** dua laporan dari
dua publikasi berbeda (BBCA, BRIS) dalam satu kumpulan data → masing-masing membawa sumbernya sendiri
lewat `potret.muat`, dan barisnya memang tersimpan begitu; **(b)** laporan yang dibentuk **tanpa**
`sumber` kembali dengan **label kumpulan** (`"uji"`), bukan `None` — sebab `None` di bidang itu
adalah **arti** ("tidak menyatakan asal"), bukan ketiadaan. Uji kedua di luar rencana satu-uji
(tabel aksi menyebut 886); jumlahnya dilaporkan apa adanya: **887 lulus**. **Bukti empat lapis:**
(a) kedua uji **gagal pada worktree `HEAD` `97d749e`** dengan `[None] == [<sumber baris>]` — bukan
`AttributeError`, persis catatan K82; (b) **dua mutasi terarah tertangkap** (`sumber=None` → 2 failed;
`sumber=baris["asal_tgl_publikasi"]` → 2 failed dengan `['sumber'] == ['uji']`, jadi ujinya memeriksa
**kolomnya**, bukan sekadar "bukan `None`") dan berkas dipulihkan **byte-identik** (SHA-256 dicocokkan
sebelum dan sesudah); (c) `tests/test_potret.py` **7 lulus**; (d) suite penuh **887 lulus**
(32,09 dtk). Bukti mentah `.uji-data/uji-k82/bukti/` (**gitignored**). **Sesudah ini berhenti**
menunggu **verifikasi pengguna** atas angka kandidat (K80 langkah 2); **44 bank dan #23 tidak dimulai
tanpa permintaan**. Rincian: `docs/keputusan.md` bagian 5 (sesi 29) dan **T78** di
`docs/arsitektur.md` — **T77** kini menyebut batas itu **tertutup**.

**Sesi 28 (pencatatan saja — K81–K82; 19 Okt 2026):** pengguna menjawab **"butuh putusan apa dari
saya? kalau ada sesuai rekomendasi mu aja, catet dulu, jangan ngoding, mau kulanjutkan di sesi
berikutnya"**, jadi sesi ini **hanya mencatat**: tanpa perubahan kode/uji, tanpa impor, tanpa
menyentuh basis data. Yang dikunci: **K81** — sel `sumber` kosong di `rasio-bank.csv` **ditolak**
(perilaku yang sudah terpasang di aksi #27; tidak ada perubahan kode). Tafsir "bila kosong: label
kumpulan" dari K78 berlaku pada **bidang** `RasioBank` yang `None`, bukan sebagai izin bagi sel
berkas kosong; alasannya `SPESIFIKASI` `boleh_kosong=False`, T67, dan preseden K18. **K82** —
`potret._fundamental` juga mengisi `Fundamental.sumber` saat membaca ulang (kolomnya sudah
`NOT NULL`; nilainya kini hilang saat baris dibaca kembali), dikerjakan sebagai **aksi #28** dengan
**uji yang terbukti gagal pada `HEAD`** dan bentuk teknis **T78**. **Aksi #28 adalah pekerjaan agen
berikutnya**, lalu **berhenti menunggu verifikasi pengguna** (K80 langkah 2); **44 bank dan #23 tidak
dimulai tanpa permintaan**. Status uji sesudah pencatatan: **`pytest` → 885 lulus** — tidak berubah,
seperti diharapkan. Rincian: `docs/keputusan.md` bagian 1 (K81–K82) dan bagian 5 (sesi 28); tafsir
K81 juga dicatat di **T77** `docs/arsitektur.md`.

**Sesi 27 (aksi #27 — K78: `sumber` per baris `rasio_bank` dipakai; SELESAI, 19 Okt 2026):** pijakan
diperiksa dulu (`pytest` → **882 lulus**, 50,39 dtk), lalu K78 dijalankan apa adanya. **Tiga berkas
kode disentuh, satu bidang ditambahkan:** `RasioBank.sumber` (`mejasaham/ingesti.py`), diisi dari
kolom berkas di `berkas._baris_rasio_bank` (kolom itu **wajib** dan tidak boleh kosong — aturan yang
sama dengan `fundamental` sejak K18), dipakai `ingesti._baris_rasio_bank` (`satu.sumber or
kumpulan.sumber`, jadi `RasioBank` yang dibentuk tanpa sumber tetap memakai label kumpulan seperti
sebelumnya), dan **dikembalikan** `potret` saat baris dibaca dari basis data — tanpa yang terakhir,
provenance hanya ada di SQL dan hilang dari pemanggil `Potret`. **Tiga uji baru** (`tests/
test_impor_berkas.py` 2, `tests/test_ingesti.py` 1): dua bank dengan sumber berbeda dalam satu berkas
→ tiap baris tersimpan dan kembali dengan sumbernya sendiri, bukan `impor berkas: <folder>`; sel
`sumber` kosong di berkas **ditolak** dengan pesan per baris (dulu diterima tanpa diperiksa karena
memang dibuang); dan `RasioBank` tanpa sumber tetap memakai label kumpulan. **Bukti empat lapis:**
(a) pada worktree `HEAD` `97d749e` ketiganya **gagal** (3 failed — `AttributeError`, `DID NOT RAISE`,
`TypeError` — bidang `sumber` belum ada); (b) **mutasi terarah 2/2 tertangkap** — `ingesti` dikembalikan
ke label kumpulan (`2 failed, 1 passed`) dan `berkas` berhenti mengisi sumber (`2 failed, 1 passed`);
kedua berkas dipulihkan **byte-identik** (hash dicocokkan); (c) suite penuh **885 lulus**;
(d) bukti mentah di `.uji-data/uji-k78/bukti/` (`bukti-ringkas.txt`, `bukti-uji-baru-gagal-pada-head.txt`,
dua berkas mutasi, `bukti-uji-baca-kandidat.txt`). **Atas berkas kandidat pilot** (tanpa basis data,
`uji-baca-kandidat.py` yang kini mencetak sumber **per baris**): BBCA dan BRIS masing-masing membawa
nama publikasinya sendiri, sedangkan `sumber kumpulan` tetap label jalur impor — jadi yang berubah
hanya barisnya, bukan arti label kumpulan. **Dua catatan yang harus dibaca sesi berikutnya:** **(1)** sel `sumber` kosong kini
**berhenti berisik** — perilaku ini memang yang tertulis di `berkas.SPESIFIKASI` dan T67, dan tidak ada
data nyata yang terdampak (berkas `rasio-bank.csv` produksi masih template `<<CONTOH>>`; berkas
kandidat sudah berisi `sumber`), tetapi berkas lama yang sel itu kosong akan ditolak **per baris** dan
pesannya menyebut kolomnya — **dikunci K81** (sesi 28); **(2)** `potret._fundamental` **masih** tidak
mengisi `Fundamental.sumber`
saat membaca ulang (perilaku lama, di luar lingkup #27) — jadi asimetri yang sama sekarang **tertutup
untuk `rasio_bank`** dan **masih terbuka untuk `fundamental`**; dicatat di T77 sebagai batas yang
diketahui, dan **dikerjakan sebagai aksi #28 (K82)**. **Pekerjaan berikutnya tetap K80 langkah 2:
verifikasi pengguna** atas
angka kandidat (K68) — pekerjaan manusia — lalu isi `konfigurasi/rasio-bank.csv`, `--impor`, periksa,
baru perluasan ke 44 bank (sesi 28 menyisipkan **aksi #28/K82** sebelum itu). Rincian:
`docs/keputusan.md` bagian 5 (sesi 27) dan **T77** di
`docs/arsitektur.md`.

**Sesi 26 (pencatatan saja — K77–K80 sesudah pilot #21b; 19 Okt 2026):** pengguna menjawab
**"sesuai rekomendasimu aja, catet dulu kulanjutkan di sesi baru"** atas empat hal yang saya ajukan
di akhir sesi 25, jadi sesi ini **hanya mencatat**: tanpa perubahan kode, tanpa impor, tanpa
menyentuh basis data. Yang dikunci: **K77** — NPF gross (1,80%) dan Net Imbalan (5,42%) BRIS
**tidak** dipetakan ke `npl_kotor_persen`/`nim_persen`; keduanya tetap tercatat di `keterangan`, dan
NPL serta NIM BRIS berstatus **"tidak dihitung"** (bukan nol; bobot dialihkan, AC-3); ide kolom
khusus bank syariah dicatat di `docs/ideas.md` (tunda). **K78** — U33 dikerjakan sebagai **aksi #27**
(bidang `sumber` di `RasioBank`, diisi dari kolom berkas, + uji yang terbukti gagal pada `HEAD`),
**sebelum** impor kandidat. **K79** — tiga bank yang menolak robots (**BMRI** `Disallow: /*.pdf$`,
**BBNI** `Disallow: /Portals/`, **BBRI** tanpa dokumen resmi terbaca yang memuat BOPO/NIM) **tidak
diakali**; pilot berlanjut dengan **2 bank**, dan bila kelak diinginkan pengguna mengunduh PDF-nya
sendiri ke `.uji-data/riset-idx/rasio-bank/pdf/manual/`. **K80** — urutan berikutnya: **#27 →
verifikasi pengguna → isi CSV → `--impor` → periksa `v_rasio_bank_terkini`/`--saring` → baru 44
bank** (hitung dulu yang menuntut langkah manual). Status kandidat **tidak berubah** (belum
diverifikasi, belum diimpor). Status uji sesudah pencatatan: **`pytest` → 882 lulus** — tidak
berubah, seperti diharapkan. Rincian: `docs/keputusan.md` bagian 1 (K77–K80) dan bagian 5 (sesi 26);
status ringkas di `docs/rasio-bank-kandidat-2026-10.md` §0.

**Sesi 25 (aksi #21b PILOT — KANDIDAT + KUTIPAN, BELUM DIIMPOR; 19 Okt 2026):** pijakan diperiksa
dulu (`pytest` → **882 lulus**, 49,60 dtk), lalu lima bank pilot (K76) dikerjakan **sampai batas
kandidat**: **2 bank terbaca, 3 tidak**, **tanpa** menulis `konfigurasi/rasio-bank.csv`, **tanpa**
`--impor`, **tanpa** satu baris basis data. Terbaca: **BBCA** — *Laporan Keuangan Publikasi
30 Juni 2026* hlm. 5 (kolom "30 Jun 2026, Tidak Diaudit"): **NPL gross 1,86% · KPMM 26,79% ·
BOPO 41,22% · NIM 5,32%**, `tgl_publikasi` 28 Jul 2026 (nama berkas + header HTTP; halaman itu masih
memuat tanggal tanda tangan lama *"Jakarta, 23 Januari 2025"* — tidak dipakai); **BRIS** — *Laporan
Publikasi Triwulanan Juni 2026*, blok "Laporan Rasio Keuangan" kolom "30 Juni 2026 (Direviu)" —
**KPMM 20,41 · BOPO 69,71**, ditandatangani 21 Agu 2026, sedangkan **NPF gross 1,80%** dan
**Net Imbalan 5,42%** **tidak** diisi ke `npl_kotor_persen`/`nim_persen` (NPF ≠ NPL; NI ≠ NIM —
menunggu keputusan Anda). **Tidak terbaca, dengan sebabnya:** **BMRI** (`robots.txt`:
`Disallow: /*.pdf$`), **BBNI** (`robots.txt`: `Disallow: /Portals/` + tantangan Incapsula),
**BBRI** (`robots.txt` tak terbaca; dokumen resmi yang bisa dibaca dari `ir-bri.com` **tidak memuat
BOPO/NIM** — laporan keuangan Q2-2026 "BOPO" 0 kali, presentasi memakai CIR 39,2%, bukan BOPO).
Metodenya persis K76: PDF diunduh, halaman **dirender QtPdf lalu dibaca visual** (bukan hanya
lapisan teks; pada BRIS urutan kolom di lapisan teks **berbeda** dari gambar, dan yang dipakai
gambar). **Tiga temuan:** **(T1)** desimal koma **ditolak** pembaca impor (`Decimal`), jadi berkas
impor memakai titik — versi pertama gagal berisik; **(T2)** kolom `sumber` per baris
`rasio-bank.csv` **tidak tersimpan** (`RasioBank` tak punya bidang itu; DB memakai
`impor berkas: <folder>`) → usulan **U33**; **(T3)** bank syariah tidak menerbitkan NPL/NIM.
**Uji jalur & format:** sesudah tiga kolom pemeriksaan dibuang, `berkas.baca_folder` membaca berkas
kandidat menjadi **186/2679/4122/532 bp** dan **None/2041/6971/None bp** — `bukti-uji-baca.txt`
**LULUS** (tanpa basis data). Berkas: `.uji-data/riset-idx/rasio-bank/` (`kandidat-rasio-bank.csv`,
`kandidat-tidak-terbaca.csv`, `bukti-pilot-rasio-bank.txt`, `pdf/`, `png/`, skrip) dan
**`docs/rasio-bank-kandidat-2026-10.md`**; rincian keputusan di `docs/keputusan.md` bagian 5.
**Pekerjaan berikutnya: verifikasi Anda** (K68) + keputusan U33/NPF; rinciannya di `docs/keputusan.md`
bagian 5 (sesi 25). **Keempatnya sudah diputuskan di sesi 26 (K77–K80)** — lihat blok sesi 26 di atas. Status uji sesudah pekerjaan: **`pytest` → 882 lulus** — tidak berubah, seperti
diharapkan karena tidak ada kode aplikasi yang disentuh.

**Sesi 24 (pencatatan saja — K76: #21b dimulai sebagai pilot 5 bank; 19 Okt 2026):** pengguna menjawab
**"sesuai rekomendasimu aja, catet dulu kulanjutkan di sesi baru"** atas pertanyaan penutup sesi 23
(pilot 3–5 bank atau 49 bank sekaligus), jadi sesi ini **hanya mencatat**: tanpa perubahan kode, tanpa
impor, tanpa menyentuh basis data. Yang dikunci **K76**: pelaksanaan **#21b** dimulai sebagai **pilot
5 bank** — **BBCA, BBRI, BMRI, BBNI, BRIS** — dengan keluaran **kandidat + kutipan resmi** (kolom
`rasio_bank` + `url`/`tanggal_akses`/`kutipan`), **tanpa** menulis `konfigurasi/rasio-bank.csv` dan
**tanpa** `--impor` sampai **angka diverifikasi Anda** (K68; aturan keras 1). Alasan pilot terukur:
**0 dari 49 bank tertahan *hanya* oleh rasio bank** (K68), dan bank pilot pun masih gagal kriteria
non-rasio (`tren_ma200`; BBCA juga `pbv_relatif_sektor`, BRIS juga `kekuatan_relatif`) — jadi yang
diuji adalah **jalur & format kutipan**, bukan kenaikan peringkat. Metode: publikasi resmi bank, PDF
dibaca lewat **render QtPdf + pembacaan visual** (tanpa dependensi baru, tanpa menebak glyph), angka
yang tidak terbaca dicatat **"tidak terbaca"** beserta sebabnya. **Sesudahnya:** verifikasi Anda → isi
`rasio-bank.csv` → `--impor` → periksa `v_rasio_bank_terkini`/`--saring` → putuskan perluasan ke 44
bank lain. Status uji sesudah pencatatan: **`pytest` → 882 lulus (48,98 dtk)** — tidak berubah, seperti
diharapkan. Rincian keputusan: `docs/keputusan.md` bagian 1 (**K76**) dan bagian 5 (sesi 24).

**Sesi 23 (aksi #26 — K75: uji impor tidak lagi bergantung detik; SELESAI, 19 Okt 2026):** pijakan
diperiksa dulu (`pytest` → **882 lulus**, 50,30 dtk), lalu **satu-satunya berkas kode yang disentuh**
adalah `tests/test_ui_tulis.py`: konstanta `KOLOM_WAKTU_IMPOR = ("jam_ambil", "batas_diketahui")` +
helper `_snapshot_tanpa_waktu_impor()` yang dipakai **hanya** oleh
`test_impor_dari_jendela_sama_dengan_baris_perintah` (helper `_baris()` bersama **tidak** diubah),
dan uji itu menegaskan himpunan kolom yang dibandingkan. **Bukti empat lapis:** (a) **A/B dengan jam
dipaksa** melewati batas detik — versi `HEAD` **gagal** (`At index 1 diff: …T05:02:39+07:00 vs
…T05:02:40+07:00`, hanya dua kolom waktu), versi K75 **lulus** dengan jam yang sama; (b) **mutasi
"pembanding dibuang terlalu lebar"** (`jumlah_emiten` ikut dibuang) **tertangkap** (`Extra items in
the right set: 'jumlah_emiten'`); (c) `tests/test_ui_tulis.py` **12 dari 12** jalan lulus (33 uji,
3,15–3,43 dtk); (d) suite penuh **882 lulus (48,96 dtk)** — sama dengan pijakan. **Tanpa perubahan
kode aplikasi, tanpa menyentuh basis data.** Bukti + cara mengulang: `.uji-data/uji-k75/bukti/`
(`bukti-ringkas.txt`, `bukti-ab-kode-lama.txt`, `bukti-ab-kode-baru.txt`,
`bukti-mutasi-lebih-lebar.txt`, `bukti-12x.txt`), plugin `.uji-data/riset-idx/k75/plugin_detik.py`.
**Pekerjaan berikutnya: aksi #21b** (`rasio-bank.csv` sampai batas kandidat + kutipan, lalu angka
diverifikasi Anda — K68); **#23/U26 tetap belum dipicu** (K61). Rincian sesi: `docs/keputusan.md`
bagian 5 dan **T76** di `docs/arsitektur.md`.

**Sesi 22 (pencatatan saja — U31 → K74, U32 → K75; 19 Okt 2026):** pengguna menjawab **"sesuai
rekomendasi aja, catet dulu nanti kulanjutin di sesi baru"** atas dua usulan yang muncul sesudah
riset K69, jadi sesi ini **hanya mencatat**: tanpa perubahan kode, tanpa menjalankan riset ulang,
tanpa menyentuh basis data. Yang dikunci: **K74** — **jangan pin CPython 3.13**; 3.14.7 + **T68**
tetap, laporan upstream (**K66**) dikirim, dan pin hanya ditinjau ulang bila Qt menjawab atau
cacatnya muncul lagi (kepastian statistik, bila kelak diinginkan, = ±100–150 jalan per versi);
**langkah 3 K69** (uji versi **PySide6** lain) tetap **tidak** dipicu; **tidak ada** perubahan
`requirements.txt`/pin Python (K3)/`.venv`. **K75** — uji **flaky**
`tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah` **diperbaiki**, dengan
bentuk: baris `snapshot` dibandingkan **tanpa `jam_ambil`/`batas_diketahui`** (waktu masing-masing
impor), kolom lain tetap penuh; alternatif "bekukan jam" lewat `db.waktu_iso` **ditolak** karena
menuntut menambal `db` **dan** `ingesti`. Pelaksanaannya **aksi #26**, dan **itu pekerjaan berikutnya**,
lalu **#21b**. Status uji sesudah pencatatan: **`pytest` → 882 lulus (96,59 dtk)** — tidak berubah,
seperti diharapkan. Rincian keputusan: `docs/keputusan.md` bagian 1 (K74/K75) dan bagian 5 (sesi 22).

**Sesi 21 (riset K69 — reproduksi ulang + A/B Python 3.13; SELESAI, 19 Okt 2026):** pijakan diperiksa
dulu (`pytest` → **882 lulus**, 88,40 dtk), lalu **langkah 1** dijalankan apa adanya: **seluruh suite
12× tanpa penangkal T68** di CPython 3.14.7 → **2 dari 12 jalan MATI** (jalan 1 dan 10), keduanya
`Fatal Python error: Aborted`, `exit=3`, **tanpa traceback**, di `tests/test_ui_jendela.py:195
_tunggu` → `pekerja.wait(60_000)` dari `test_hasil_lama_dibuang_saat_pemuatan_gagal` baris 409 — dan
dump-nya **hanya utas utama** (bukan `Jendela.tunggu_pekerja`, bukan bingkai `[Pekerja]`). Jadi
**kontrolnya gagal**, syarat yang dituntut K69 dan yang **tidak bisa diberikan 8.5** (0 kematian di 24
jalan berkas-tunggal). **Langkah 2:** `.tmp/py313` **dibangun ulang** (10,7 dtk dari cache `uv`, tanpa
unduhan; 769 MB; versi sama dengan 8.5) dan perintah yang sama dijalankan 12× di CPython 3.13.14 →
**0 dari 12 mati**. Angkanya: **2/12 vs 0/12, uji Fisher dua sisi p ≈ 0,48** — secara huruf K69 pin
Python **boleh** diputuskan, tetapi secara bukti **belum pantas**; **rekomendasi: jangan pin sekarang**
(**U31**), T68 tetap, dan **laporan upstream (K66) kini punya kontrol yang gagal** — itu yang dikirim.
**Temuan sampingan:** satu uji **flaky** — `tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah`
gagal 1 dari 12 jalan karena membandingkan `jam_ambil`/`batas_diketahui` dua impor yang melewati batas
detik (`…32+07:00` vs `…33+07:00`) → **U32**, usulan **aksi #26**. **Tanpa perubahan kode**; bukti
`.uji-data/uji-k69/` (`reproduksi/jalan-1…12.txt`, `reproduksi-313/jalan-1…12.txt`, `bukti-k69.txt`),
pembuatnya `.uji-data/riset-idx/k69/`; rincian `docs/riset-pyside6-gc-2026-10.md` **bagian 10** dan
`docs/laporan-pyside6-siap-kirim.md` (diperbarui hari itu juga). **Pekerjaan berikutnya saat itu:
aksi #21b** (sesi 22 menambahkan **#26** di depannya, K75).

Keadaan kode sesi 12 (**jendela kini juga MENGIMPOR, dan 11.4 punya pilihan ukuran patuh**):
impor berkas dari **menu Berkas** berjalan dua tahap — folder dibaca di utas pekerja, konfirmasi
memuat **jumlah baris per tabel**, lalu penulisan lewat `pengatur.jalankan_impor(sudah_dibaca=…)`
dengan **objek hasil bacaan yang sama**; layar 11.4 memperoleh centang **"Pakai ukuran patuh"**
(K63) lewat `risiko.pakai_ukuran_patuh` yang sama dengan `--pakai-ukuran-patuh`; dan rencana/posisi
di 11.3–11.4 **dipilih dari daftar**, bukan diketik (K64/T71 a). Satu cacat perilaku ditemukan dari
bukti data nyata dan ditutup: impor yang terkunci berhenti setelah **11,16 dtk** (dua penantian
`busy_timeout`: penulisan + percobaan mencatat log) → sesudah perbaikan **5,62 dtk**.
Terukur atas data nyata (`.uji-data/uji-impor-jendela/bukti/bukti-impor-jendela.txt`): seluruh
**13 tabel/view SAMA** antara jalur jendela dan baris perintah sesudah mengimpor folder konfigurasi
produksi (`.uji-data/mejasaham/konfigurasi`, 4.131 baris baru · 1.095 sudah ada dan sama; konfirmasi
berbunyi `total: 5.226 baris dari 9 berkas`), berkas yang ditolak pembaca ditolak **dengan kalimat
yang sama** dan 0 baris tertulis, dan `v_rencana_terkini` hasil "Pakai ukuran patuh" **SAMA** dengan
`--hitung-risiko … --pakai-ukuran-patuh`. `.\.venv\Scripts\python -m pytest` → **849 lulus**, dan
ketiga berkas uji jendela+tulis **6× berturut-turut 65 lulus** (tanpa proses yang mati).
Rincian sesinya di `docs/keputusan.md` bagian 5; keputusan teknisnya **T72** di `docs/arsitektur.md`.
**Pekerjaan sesi 12 belum di-commit saat itu** (sudah di-commit pada sesi 19 — lihat blok TITIK
MULAI di bawah).

**Sesi 20 (aksi #24 + #25 — K71/K72; SELESAI, 19 Okt 2026):** dua cacat yang terukur sesi 18
ditutup di **inti**, bukan di jendela — jendela memang sudah menolaknya. **(1) K71/#24:**
`posisi.catat_keputusan_right_issue` kini memakai **satu** pemeriksaan
(`_tolak_isian_yang_tidak_dipakai`) untuk **semua** keputusan selain `jual_hmetd`, termasuk
`tebus`; pesannya menyebut bahwa yang menaikkan lembar adalah **transaksinya** (T51), bukan
keputusan itu. Jalur baris perintah yang dulu keluar **0 tanpa pesan** kini keluar **1** dengan
pesan itu dan **0 baris** yang tertulis. **(2) K72/#25:** `catatan` keputusan right issue tidak
lagi menyalin **catatan turunan** yang kalimatnya sudah ada di catatan revisi sebelumnya
(dibandingkan **per baris**, sehingga kalimat yang berubah — mis. tanggal yang berbeda — tetap
dicatat); catatan yang dinyatakan pengguna dan `pesan_revisi` tetap disambung apa adanya, dan
`PendaftaranKeputusan.catatan` tetap memuat catatan yang **berlaku** (bukan hanya yang baru
ditulis). **Verifikasi: `pytest` → 882 lulus** (879 + 3 uji baru). **Ketiga uji baru terbukti
gagal pada worktree `HEAD`** (`97d749e`): `3 failed, 41 deselected` — dan `test_aksi_korporasi_posisi.py`
di working tree `44 passed`; rincian keputusan teknisnya **T75** dan buktinya di
`.uji-data/uji-k71-k72/bukti/` (`bukti-uji-baru-gagal-pada-head.txt`). **Belum dikerjakan:**
riset **K69** (pekerjaan berikutnya menurut K73) dan **#21b**; tidak ada perubahan pada
`docs/keputusan.md` bagian 1 selain penanda "sudah dijalankan" pada K71/K72.

**Sesi 19 (pencatatan saja — tanpa perubahan kode dan tanpa menyentuh basis data):** pengguna
menjawab **"sesuai rekomendasi mu saja, catet dulu nanti di lanjutkan di sesi baru"** atas tiga hal
yang saya ajukan di akhir sesi 18. Yang dikunci: **K71 → aksi #24** (inti menolak
`--lembar`/`--harga`/`--biaya` untuk keputusan selain `jual_hmetd`, **termasuk `tebus`** — mengikuti
pemeriksaan yang sudah ada untuk arah sebaliknya), **K72 → aksi #25** (`catatan` keputusan right
issue berhenti menggelembung: catatan **turunan** yang kalimatnya sudah ada tidak ditambahkan lagi,
sedangkan catatan pengguna dan `pesan_revisi` tetap disambung), dan **K73** (urutan berikutnya:
**#24 + #25 dulu → riset K69 → #21b**). Alasan menaruh #21b paling akhir sudah terukur: **0 dari 49
bank tertahan *hanya* oleh rasio bank** (K68), jadi mengisi berkas itu tidak membuka peringkat bank
dengan sendirinya. **Tidak ada pertanyaan yang tersisa**, dan dua pekerjaan **manusia** tidak
berubah (mengirim laporan PySide6 K66, memverifikasi angka `rasio-bank.csv` K68). Status uji
**dijalankan ulang sesudah pencatatan**: `pytest` → **879 lulus** — tidak berubah, dan itu memang
yang diharapkan karena tidak ada berkas kode yang disentuh.

**Sesi 18 (aksi #19d — `ubah-stop` + keputusan right issue dari jendela; SELESAI):** layar **11.1
(dasbor)** kini punya formulir **"Ubah stop"** — posisinya **dipilih dari daftar** posisi aktif
(K64/K65), `tgl_stop`-nya adalah **tanggal yang dinyatakan pengguna** (kosong = hari ini) dan
muncul apa adanya di dialog konfirmasi; layar **11.3 (detail emiten)** kini punya tabel **hak right
issue** (kode · posisi · tanggal aksi · rasio · tebus · tenggat · hak · keputusan) yang barisnya
dipilih pengguna, beserta formulir keputusannya (`tebus`/`jual_hmetd`/`abaikan`) dengan isian yang
**tidak dipakai** pilihan aktif dimatikan **dan** dikosongkan. Semuanya lewat `posisi.ubah_stop` dan
`posisi.catat_keputusan_right_issue` yang sudah ada (bukan jalur kedua), `tebus` tetap hanya
**menunjuk** transaksi yang sudah tercatat (T51), dan teks tindakan menunggu di dasbor berhenti
menyuruh pindah ke baris perintah. **Verifikasi: `pytest` → 879 lulus** (863 + 16 uji baru);
**mutasi terarah 5/5** membuktikan uji barunya bergigi (berkasnya dipulihkan **byte-identik**), dan
pada worktree `HEAD` hasilnya 44 gagal/48 lulus — **bukan** pembanding tajam, sebab HEAD = kode sesi
11. Terukur atas salinan `.uji-data/uji-aksi-korporasi`: **ketiga view SAMA** antara jalur jendela
dan jalur baris perintah (termasuk `pelanggaran`, `catatan`, `tgl_stop`), MLPT 17.000 (basis
2026-07-15) → 1.200 **tanpa V5 palsu** sesudah split 1:25, ASII 4.830 → 4.700 **tercatat V5**,
hak MLPT 6.250 lembar dengan catatan lot K31, dan **`tebus` tanpa transaksi ditolak berisik dengan
0 baris**. Bukti + 6 tangkapan layar `offscreen` di `.uji-data/uji-stop-right-jendela/bukti/`;
keputusan teknisnya **T74**; rincian sesinya di `docs/keputusan.md` bagian 5. **Dua temuan**
(belum diperbaiki) — **sudah dikunci sesi 19 sebagai K71/K72, pelaksanaannya aksi #24/#25** (lihat
blok di atas dan `docs/keputusan.md` bagian 5 sesi 18): `tebus` di inti membuang
`--lembar`/`--harga`/`--biaya` diam-diam pada jalur baris perintah, dan `catatan` keputusan right
issue menggelembung tiap revisi. **Pekerjaan sesi 12–18 belum di-commit saat itu** — lihat blok TITIK
MULAI di bawah (sesi 19 sudah meng-commit semuanya).

**Sesi 17 (pencatatan saja — tanpa perubahan kode dan tanpa menyentuh basis data):** pengguna
menjawab **"sesuai rekomendasimu aja, catet dulu, biar kulanjutkan di sesi baru"** atas dua hal yang
diajukan di akhir sesi 16. Yang dicatat: **U30 → K70** (`docs/keputusan.md` bagian 1) — folder tujuan
cadangan **tetap dari konfigurasi** (`--folder-cadangan`/`MEJASAHAM_BACKUP`), jendela **menyebut**
folder itu di dialog, dan **kotak pilih folder per-cadangan tidak ditambahkan sekarang** (bila kelak
diminta, itu keputusan tersendiri); syarat "di luar folder data" tetap ditolak **sebelum** konfirmasi
(T73). **Arah sesi berikutnya juga dicatat:** **#19d** (`ubah-stop` + keputusan right issue, K62)
tetap pekerjaan kode berikutnya, dan **K69** (reproduksi ulang cacat PySide6) tetap pekerjaan riset
yang **belum** dijalankan. **Tidak ada pertanyaan yang tersisa** (U27–U30 → K66–K68/K70; P34–P39
tertutup). Status uji **dijalankan ulang sesudah pencatatan**: `pytest` → **863 lulus** (79,73 dtk) —
tidak berubah, dan itu memang yang diharapkan karena tidak ada berkas kode yang disentuh.

**Sesi 16 (aksi #19c — cadangan + daftar cadangan dari jendela; SELESAI):** menu **Berkas** kini
memuat **"Cadangan basis data…"** dan **"Daftar cadangan…"**. Cadangannya berjalan lewat `Pekerja`
dengan konfirmasi yang **menyebut folder tujuannya** (K59 d), lalu menulis lewat `cadangan.buat` —
jalur yang sama dengan `--buat-cadangan`; daftarnya memakai teks yang sama dengan
`--daftar-cadangan`; **pemulihan tetap tidak ada** (K59 e) dan ketiadaannya disebut di konfirmasi,
pesan hasil, dan daftar. Tiga hal yang perlu dibaca sesi berikutnya: (a) **folder tujuan dihitung
satu kali** (`cadangan.folder_tujuan`) dan syarat "di luar folder data" menjadi
`cadangan.periksa_tujuan` yang dipakai penulisan **dan** konfirmasi, jadi dialognya menyebut folder
yang benar dan tidak pernah meminta menyetujui cadangan yang pasti ditolak; (b) **satu cacat
perilaku ditutup** — `mkdir` folder tujuan ada di luar `try`, sehingga kegagalan yang paling mungkin
(folder tidak bisa ditulis) keluar sebagai traceback dan pada jalur sebelum-migrasi berbunyi
`MEJASAHAM_DATA` (variabel yang salah); (c) **pemuatan ulang yang tidak dibayar** — `PermintaanTulis`
kini menyatakan `muat_ulang` **dan** `pertanyaan`, sebab cadangan tidak menulis baris: terukur
`cadangan.buat` **1,26 dtk** vs pemuatan ulang dasbor **63,83 dtk** pada basis data 231 MB → jalur
jendela **54,46 → 3,34 dtk**. Terukur juga: cadangan **tidak menunggu kunci tulis** (ia hanya
membaca). **Verifikasi: `pytest` → 863 lulus** (849 + 14 uji baru), `pytest tests\test_ui_tulis.py
tests\test_ui_jendela.py tests\test_ui_tabel.py -q` **6× 76 lulus tanpa proses yang mati**, seluruh
14 uji baru **terbukti gagal pada HEAD**, dan bukti atas data nyata di
`.uji-data/uji-cadangan-jendela/bukti/` (kedua cadangan **byte-identik**, daftar sama persis,
cadangan buatan jendela **dipulihkan** ke folder bersih, + 4 tangkapan layar `offscreen`).
Keputusan teknisnya **T73**; rincian sesinya di `docs/keputusan.md` bagian 5; usulan **U30** yang
muncul di sini **sudah dikunci sesi 17 sebagai K70**. **Pekerjaan sesi 16 belum di-commit saat itu**
— lihat blok TITIK MULAI di bawah (sesi 19 sudah meng-commit semuanya).

**Sesi 15 (pencatatan saja — tanpa perubahan kode dan tanpa menjalankan perintah apa pun):** pengguna
menjawab **"sesuai rekomendasi mu aja, jangan dijalankan, catet aja dulu, mau aku lanjutin ke sesi
baru"** atas pertanyaan sesi 14b (langkah berikutnya setelah uji 3.13 yang inkonklusif). Yang dicatat:
**K69** (`docs/keputusan.md` bagian 1) — **reproduksi ulang cacatnya lebih dulu** (seluruh suite 12×
tanpa penangkal di 3.14.7), **baru** A/B di 3.13 bila kontrolnya gagal; pin versi Python hanya sah bila
kontrolnya gagal di satu versi dan tidak di versi lain (dan itu keputusan dependensi tersendiri); bila
reproduksi tetap tidak muncul → **uji versi PySide6 lain** (pola K67); **T68 tetap dipakai**. Rencana
teknisnya — perintah, patokan "mati" (tidak ada ringkasan pytest, **bukan** pola teks), cabang
keputusan, dan **sumber plugin `plugin_tanpa_tahan.py`** — ada di
`docs/riset-pyside6-gc-2026-10.md` **bagian 9**, supaya sesi baru bisa menjalankannya meski `.tmp/`
(gitignored) sudah terhapus. Status uji **tidak dijalankan ulang** sesuai permintaan; angka terakhir
yang terukur tetap **849 lulus** (sesi 14b).

---

**Sesi 14b (pemasangan disetujui, uji dijalankan — tanpa perubahan kode aplikasi):** lingkungan
terpisah **`.tmp/py313`** dipasang (CPython **3.13.14** lewat `uv`; PySide6 6.12.0 · shiboken6 6.12.0
· pytest 9.1.1; unduhan interpreter **20,9 MiB**; env **767 MB**; `uv pip check` bersih) dan ujinya
dijalankan **lebih dari yang diminta**: 12 jalan **dengan** penangkal (0 kematian — tapi itu dijamin
penangkalnya, jadi tidak membuktikan apa pun) **dan** 12 jalan **tanpa** penangkal di **3.13** serta
12 jalan **tanpa** penangkal di **3.14** → **0 kematian di keempatnya**, padahal sesi 10 mencatat 7
dari 18 jalan mati tanpa penangkal di 3.14.7. **Kesimpulan: belum dapat disimpulkan** (K67);
langkah berikutnya: reproduksi ulang cacatnya (kandidat: seluruh suite 12× tanpa penangkal) **atau**
uji versi PySide6 lain dengan 3.14.7 — **T68 tetap dipakai**. Draf laporan upstream (K66) ikut
dikoreksi dengan **"Note on reproducibility"** supaya tidak terbaca sebagai janji "selalu mati 7 dari
18"; catatan metodenya (patokan "mati" = tidak ada ringkasan pytest, bukan pola teks) ada di
`docs/riset-pyside6-gc-2026-10.md` bagian 8.5.

**Sesi 14 (tanpa perubahan kode aplikasi):** pengguna menjawab ketiga pertanyaan sesi 13 **"sesuai
rekomendasi"** → **K66–K68** (`docs/keputusan.md` bagian 1). Yang dikerjakan sesi ini: (a) **berkas
laporan PySide6 siap kirim** `docs/laporan-pyside6-siap-kirim.md` + langkah mengirimnya menurut
halaman resmi Qt (pelacak PYSIDE, lampiran berkas wajib) dan daftar lampirannya; (b) **laporan
keputusan dependensi** untuk uji Python 3.13 di `docs/riset-pyside6-gc-2026-10.md` bagian 8 —
`uv 0.12.2` sudah ada, CPython 3.13.14 tersedia, roda PySide6 6.12.0 **abi3** (`cp310-abi3`) jadi
berlaku juga untuk 3.13, lingkungan di `.tmp/py313`, biaya disk kira-kira sebesar salinan PySide6
yang ada (**651 MB**), pencabutan dua baris — **pemasangannya belum dijalankan** (menunggu
persetujuan Anda); (c) **lingkup `rasio-bank.csv` diukur lebih dulu** (salinan uji, `simpan=False`):
49 bank · **0 tertahan hanya oleh rasio bank** · keempat rasio tidak dinilai pada ke-49 bank,
sementara 34 bank juga gagal `adtv20`, 40 gagal `tren_ma200`, 19 gagal `kekuatan_relatif`, dan
`roe_5t`/`per_relatif_sektor`/`pbv_relatif_sektor` juga lubang — bukti
`.uji-data/uji-lingkup-p39/bukti-lingkup-p39.txt`. Status uji tidak berubah (`pytest` → 849 lulus).

**Sesi 13 (pencatatan saja, tanpa perubahan kode):** pengguna menjawab **"sesuai rekomendasi aja"**
atas seluruh pertanyaan sesi 12 (tiga keputusan teknis T72 tetap dipakai; tafsir K64 dikunci sebagai
**K65**: jendela memilih rencana/posisi **dari daftar saja**), lalu menanyakan apakah **tiga butir
"menunggu pengguna"** bisa dikerjakan sesi agen, dengan permintaan **"catet dulu"**. Jawaban
ringkasnya dicatat sebagai **U27–U29** + **P37–P39** (`docs/keputusan.md` bagian 2 dan 3.9) — yang
kemudian dijawab pada sesi 14 → **K66–K68**. Status uji tidak berubah (`pytest` → 849 lulus), karena
tidak ada berkas kode yang disentuh.

---

> **TITIK MULAI UNTUK SESI BARU — dibaca lebih dulu, 3 menit.**
>
> **Dua langkah pertama sesi baru, berurutan:**
>
> 1. **Pastikan pijakannya benar sebelum percaya apa pun:** `.\.venv\Scripts\python -m pytest` harus
>    **908 lulus** (angka terakhir yang terukur: **sesi 35** — 30,91–38,12 dtk; sesi 34 **906**,
>    sesi 35 menambah **2** uji kontrak pengemasan di `tests/test_pengemasan.py`).
>    Bila tidak, periksa dulu bagian 6 (jebakan
>    lingkungan: folder sementara, ACL, dan cacat PySide6/CPython) — bukan kodenya. Uji jendela
>    sebaiknya dijalankan **beberapa kali** (§6: cacat GC-nya bergantung waktu).
> 2. **Baca yang mengikat, bukan yang meringkas:** `docs/keputusan.md` bagian 1 untuk **K55**, **K59**,
>    **K61**, **K62–K88**, `docs/arsitektur.md` untuk **T69–T81**, lalu bagian 4 berkas ini (baris
>    **#24/#25/#26/#27/#28/#29/#23/#22 yang sudah selesai** dan #19d), dan
>    `docs/riset-pyside6-gc-2026-10.md` **bagian 10** untuk hasil K69.
>    **Tahap 5** sudah dikerjakan sesi 35: `tools/build_exe.py` → `dist\MejaSaham\MejaSaham.exe`
>    (**T81/T82**); perbaikan konflik DLL build dicatat sebagai **T83**. Berikutnya pengguna
>    mencoba EXE hasil build lewat klik-ganda.
>
> **Cakupan tindakan tulis K59 c SUDAH LENGKAP (sesi 18):** tiga pencatat → impor (#19b) → cadangan +
> daftar (#19c) → **`ubah-stop` + keputusan right issue (#19d)**. Bentuk teknisnya T71, dan keempat
> pelaksanaannya (**T72**, **T73**, **T74**) memakai pola yang sama: satu jalur inti, konfirmasi di
> utas tampilan **sebelum** pekerja mulai, penulisan di utas pekerja, **pilihan dari daftar, bukan
> diketik** (K64/K65), permintaan tulis yang **menyatakan sendiri** pertanyaannya dan apakah layarnya
> perlu dimuat ulang (T73), dan isian yang tidak dipakai sebuah pilihan **ditolak berisik**, bukan
> dibuang. **Yang tetap di baris perintah:** `--pulihkan` (K59 e, K64) — dan itu **bukan** pekerjaan
> yang menunggu, melainkan batas yang ditetapkan.
>
> **Pekerjaan berikutnya, urutannya sudah dikunci (K73) — tiga yang pertama SELESAI 19 Okt 2026:**
> ~~**(1) aksi #24** (K71)~~ dan ~~**(2) aksi #25** (K72)~~ dikerjakan **sesi 20**: inti kini menolak
> `lembar`/`harga`/`biaya` untuk **semua** keputusan selain `jual_hmetd`, **termasuk `tebus`** — jalur
> baris perintah keluar 1 dengan pesan yang menyebut transaksi (T51), bukan 0 tanpa pesan — dan
> `catatan` keputusan right issue berhenti menggelembung (catatan turunan yang kalimatnya sudah ada
> tidak disalin lagi; catatan pengguna dan `pesan_revisi` tetap disambung). **`pytest` → 882 lulus**;
> rincian **T75** dan `docs/keputusan.md` bagian 5. ~~**(3) riset K69**~~ **dijalankan sesi 21**:
> kontrol **gagal** (2/12 mati di 3.14.7) dan A/B 3.13 = **0/12** (p ≈ 0,48) → **U31** (rekomendasi:
> jangan pin Python) dan **U32** (uji flaky). ~~**(4) aksi #26**~~ **dikerjakan sesi 23**: uji impor
> membandingkan baris `snapshot` **tanpa** `jam_ambil`/`batas_diketahui`, kolom lain tetap penuh;
> A/B dengan jam dipaksa (versi lama **gagal**, versi baru lulus), mutasi "pembanding dibuang terlalu
> lebar" **tertangkap**, 12/12 jalan `tests/test_ui_tulis.py` lulus, `pytest` → **882 lulus**. Bukti
> `.uji-data/uji-k75/bukti/`; rincian **T76** dan `docs/keputusan.md` bagian 5.
> **(5) SELESAI 19 Okt 2026 (sesi 25) — aksi #21b dalam bentuk pilot (K76), SAMPAI BATAS KANDIDAT:**
> **2 bank terbaca, 3 tidak**; **belum** ada yang masuk `konfigurasi/rasio-bank.csv` atau basis data
> (K68). Terbaca: **BBCA** (30 Jun 2026: NPL gross 1,86% · KPMM 26,79% · BOPO 41,22% · NIM 5,32%) dan
> **BRIS** (30 Jun 2026: KPMM 20,41 · BOPO 69,71; NPF/NI **tidak** dipetakan ke NPL/NIM). Tidak
> terbaca: **BMRI** (`robots.txt` `Disallow: /*.pdf$`), **BBNI** (`Disallow: /Portals/` + Incapsula),
> **BBRI** (robots tak terbaca; dokumen resmi yang bisa dibaca tidak memuat BOPO/NIM — presentasi
> memakai CIR). **Pekerjaan berikutnya: verifikasi Anda** atas angka kandidat (K68) + keputusan
> **U33** (`sumber` per baris `rasio-bank.csv` tidak tersimpan) dan NPF/NI — berkasnya
> `docs/rasio-bank-kandidat-2026-10.md`. **`--pulihkan` bukan pekerjaan tertunda** (K59 e/K64 = batas
> cakupan).
>
> **(6) SELESAI 19 Okt 2026 (sesi 27) — aksi #27 (K78):** `sumber` per baris `rasio_bank` **dipakai**,
> bukan dibuang. Bidang `sumber` di `RasioBank` diisi dari kolom berkas, dipakai `ingesti`, dan
> dikembalikan `potret`; sel `sumber` kosong di berkas kini **ditolak per baris** (aturannya sama
> dengan `fundamental` sejak K18). Bukti: ketiga uji baru **gagal pada worktree `HEAD`**, dua mutasi
> terarah **tertangkap**, suite **885 lulus**; rincian **T77** dan `.uji-data/uji-k78/bukti/`.
> **Saat itu (sesudah #27) pekerjaan berikutnya: verifikasi Anda** atas angka kandidat (K68) —
> `docs/rasio-bank-kandidat-2026-10.md` — lalu isi `konfigurasi/rasio-bank.csv` (hanya kolom
> `rasio_bank`), `--impor`, periksa `v_rasio_bank_terkini`/`--saring`, **baru** putuskan 44 bank.
>
> **(7) SELESAI 19 Okt 2026 (sesi 29) — aksi #28 (K82):** `potret._fundamental` kini **mengisi**
> `Fundamental.sumber` saat membaca ulang (`sumber=baris["sumber"]`; kolomnya sudah `NOT NULL` sejak
> K18, nilainya dulu hilang menjadi `None`). **Dua** uji baru — sumber per baris antarpublikasi, dan
> bidang kosong yang kembali sebagai **label kumpulan** — keduanya **terbukti gagal pada worktree
> `HEAD` `97d749e`** (`[None] == [<sumber baris>]`, bukan `AttributeError`), dua mutasi terarah
> **tertangkap**, berkas dipulihkan byte-identik, suite **887 lulus**; rincian **T78** dan
> `.uji-data/uji-k82/bukti/`.
>
> **(8) SELESAI 19 Okt 2026 (sesi 31) — aksi #29 (K83): verifikasi ulang 14/14 sel, lalu impor.**
> SHA-256 kedua PDF = manifest, halaman dirender ulang, setiap sel dibandingkan, cadangan dibuat,
> `--impor` → **snapshot 12** dengan **2 baris `rasio_bank`**; `v_rasio_bank_terkini` memuat keduanya
> (186/2679/4122/532 bp dan `None`/2041/6971/`None` bp). **`--saring` tidak berubah** karena `jenis`
> **973** emiten masih kosong (kriteria bank tidak diterapkan) dan BBCA/BRIS gagal `coverage`
> (EBIT tahunan). Bentuk teknis **T79**, bukti `.uji-data/uji-k83/bukti/`.
>
> **(9) PRASYARAT K87 SELESAI (sesi 32); 44 bank TETAP DITUNDA.** `jenis` **sudah diisi** dari sumber
> data: **49 bank_keuangan · 862 umum · 62 kosong**, impor → **snapshot 13**, dan `--saring` **kini
> menerapkan** kriteria bank (NPL/CAR/BOPO/NIM) serta berhenti menghitung DER/coverage/CFO-NI untuk
> bank (PRD 8.4). **Peringkat tidak berubah** (9 lolos/9 dinilai; sembilan kandidat sama) — K68
> terbukti lagi. **47 dari 49 bank belum punya rasio**; karena itu **44 dokumen tetap ditunda
> (K87)** dan ~~**hitung langkah manual (K79) belum dijalankan**~~ — **SUDAH dijalankan sesi 33**
> (lihat butir 10). **U34 ditutup (K86): 21 Agu
> dipertahankan.** **`notasi_khusus` +2.328 revisi diterima (K85)** — tidak dipulihkan. **#23/U26
> SELESAI sesi 34** (butir 11); **pengiriman laporan PySide6 tetap pengguna (K84)**; `--pulihkan` tetap
> bukan pekerjaan tertunda (K59 e).
>
> **(10) SELESAI 19 Okt 2026 (sesi 33) — hitung langkah manual (K79) untuk 44 bank.**
> **8 dari 44 menuntut langkah manual** (robots: **BTPS** `Disallow: /`, **DNAR** `/media`+`/images`;
> akses: **AGRS** WAF, **BBMD** Cloudflare, **BBTN** Incapsula, **BNLI** 403, **SUPA** 403,
> **BACA** 502), **2 tidak terukur** (INPC timeout, SDRA SSL — bukan bukti kebijakan), **34 boleh
> otomatis**. **Izin robots bukan jaminan dokumen ketemu:** uji satu tingkat hanya menemukan
> **12/34 halaman publikasi nyata** (16 dengan jangkar) dan **11/34 tautan PDF** (batas bawah — situs
> ber-JavaScript tidak menampakkan tautan ke klien HTTP biasa; isi PDF belum diperiksa). **Usulan
> U35 = tetap tunda — DIKUNCI sebagai K88 (19 Okt 2026)**; bila kelak diminta,
> **34 otomatis dulu**, lalu **8 manual** hanya bila PDF-nya tersedia (K79). Bukti
> `.uji-data/uji-k79/bukti/`; rincian `docs/rasio-bank-kandidat-2026-10.md` **§10**.
>
> **(11) SELESAI 19 Okt 2026 (sesi 34) — aksi #23/U26: konteks pasar disimpan `--saring`, dibaca
> dasbor bila kuncinya sama.** `--saring` (hanya `simpan=True`) menulis breadth + rezim + penutupan
> indeks terakhir ke **`konteks_pasar`** (migrasi 015); dasbor membacanya hanya bila `id_snapshot` +
> `id_preset` + `sumber_harga` + `versi_hitung` semuanya sama — keempatnya di WHERE — dan selain itu
> **menghitung ulang**. `--kode` tidak menulis; kegagalan tulis menjadi peringatan, bukan pembatalan.
> **Terukur:** `--dasbor` **18,95 → 0,74 dtk (25,7×)**, baris `Pasar` identik, `--saring` **18,16 dtk**;
> 19 uji baru, suite **906 lulus**; 5 uji perilaku **gagal pada worktree `HEAD` `6888b1b`**. Bentuk
> teknis **T80**, skema **5.16**, bukti `.uji-data/uji-k61/bukti/`.
>
> **(12) SELESAI SEBAGIAN 19 Okt 2026 (sesi 35) — Tahap 5: bundel PyInstaller onedir.** Pengguna
> menjawab **"sesuai rekomendasimu"** saat ditanya arah; pilihannya Tahap 5. `requirements-build.txt`
> (PyInstaller **6.22.3** + transitive), `tools/entry_exe.py`, `tools/build_exe.py`
> (`--onedir --console --hide-console hide-early --add-data mejasaham/defaults`), dan
> `tests/test_pengemasan.py` (2 uji). Hasil: `dist\MejaSaham\MejaSaham.exe` 15,3 MiB +
> `_internal/` **184,5 MB**; `--help`/`--muat-konfigurasi` keluar 0; `--saring`/`--dasbor` identik
> dengan jalur modul; `--ambil-fundamental --kode BBCA` membuktikan yfinance/pandas terbawa; GUI
> `offscreen` hidup; salinan aplikasi berjalan dengan `PATH` tanpa Python; suite **908 lulus**.
> **Tersisa:** ikon aplikasi (belum ada aset) dan uji klik-ganda di mesin tanpa Python. Bentuk
> teknis **T81**, bukti `.uji-data/uji-tahap5/`.
>
> **Hasil riset K69 (SELESAI 19 Okt 2026) — jangan diulang dari nol:** reproduksi ulangnya **berhasil**
> dengan `$env:PYTHONPATH="$PWD\.tmp"; .\.venv\Scripts\python.exe -m pytest -q -p plugin_tanpa_tahan`
> 12× → **2 mati** (`Fatal Python error: Aborted`, di `tests/test_ui_jendela.py:195 _tunggu` →
> `pekerja.wait`, **bukan** `tunggu_pekerja`), lalu A/B yang sama di `.tmp\py313` → **0 mati**.
> **Patokan "mati" = tidak ada ringkasan pytest**, dan kata `access violation` **tidak boleh** dipakai
> sebagai penanda (muncul di 12 dari 12 log — semuanya docstring). Baca
> `docs/riset-pyside6-gc-2026-10.md` **bagian 10** sebelum menjalankan ulang. **Jangan** pin versi
> Python berdasarkan 2 vs 0 (U31); **jangan** menguji versi PySide6 lain kecuali Anda memintanya
> (cabang 3 tidak dipicu). **T68 tetap dipakai.**
>
> **Dua temuan sesi 18 SUDAH DIPERBAIKI (sesi 20, K71/K72 → #24/#25) — jangan dikarang ulang:**
> (a) **K71 → #24**: `posisi.catat_keputusan_right_issue` **membuang `--lembar`/`--harga`/`--biaya`
> diam-diam** untuk keputusan `tebus` (baris perintah keluar 0 tanpa pesan); kini satu pemeriksaan
> `_tolak_isian_yang_tidak_dipakai` menolaknya untuk semua keputusan selain `jual_hmetd`, dengan
> pesan yang menyebut transaksi (T51). (b) **K72 → #25**: `catatan` keputusan right issue
> **menggelembung tiap revisi**; kini catatan turunan yang kalimatnya sudah ada tidak disalin lagi,
> sedangkan catatan pengguna dan `pesan_revisi` tetap disambung. Bentuknya di `docs/keputusan.md`
> bagian 1 (K71/K72) dan **T75**; ketiga uji barunya **terbukti gagal pada `HEAD`**.
>
> **U33 sudah dikunci (K78, sesi 26) dan SUDAH DIKERJAKAN (aksi #27, sesi 27):** dulu kolom `sumber`
> per baris pada `rasio-bank.csv` **tidak tersimpan** (kelas `RasioBank` tak punya bidang itu; `ingesti`
> memakai `impor berkas: <folder>`), jadi asal tiap publikasi bank hilang saat impor. Kini bidang
> `sumber` ada di `RasioBank`, diisi dari berkas, dipakai `ingesti`, dan dikembalikan `potret` (**T77**);
> rincian lengkapnya di `docs/keputusan.md` bagian 5 (sesi 27). **U31 dan U32 sudah dikunci
> 19 Okt 2026 (sesi 22):**
> **K74** = **jangan pin CPython 3.13** (3.14.7 + T68 tetap; laporan upstream dikirim; pin hanya
> ditinjau ulang bila Qt menjawab atau cacatnya muncul lagi; **langkah 3 K69 tetap tidak dipicu**;
> tidak ada perubahan `requirements*`/pin K3/`.venv`) dan **K75** = uji flaky
> `tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah` **diperbaiki** lewat
> **aksi #26** — **sudah dijalankan 19 Okt 2026 (sesi 23)** (baris `snapshot` dibandingkan **tanpa**
> `jam_ambil`/`batas_diketahui`; kolom lain tetap penuh). **U30 sudah dikunci K70** (folder tujuan
> cadangan tetap dari konfigurasi; jendela menyebutnya di dialog; kotak pilih per-cadangan tidak ditambahkan
> sekarang). **Satu hal yang tinggal dikerjakan manusia:** **mengirim laporan PySide6** — berkasnya
> siap dan **kini memuat kontrol yang gagal** (`docs/laporan-pyside6-siap-kirim.md`, K66/K84).
> Verifikasi angka `rasio_bank` **sudah dialihkan ke agen dan selesai** (K83/aksi #29: 14/14 sel
> cocok, dua baris diimpor); yang tersisa milik pengguna hanyalah **pengiriman laporan** itu.
>
> **Keadaan git (diperbarui 19 Okt 2026, sesi 32 — sesi 20–32 SUDAH di-commit):** pekerjaan
> sesi 11 **sudah di-commit** (`874e095` kode + 23 uji, `82f3064` catatan, `2e6a292` catatan keadaan
> git). Pekerjaan **sesi 12 (#19b), 16 (#19c), dan 18 (#19d) kini JUGA sudah di-commit** (atas
> permintaan pengguna): **`3565d02`** = kode + uji ketiga tahap itu (13 berkas; `833 -> 879` uji),
> **`2aacd2b`** = catatan dokumennya (T72–T74, K55/K59/K62–K73, laporan PySide6, riset PySide6), dan
> commit berikutnya = catatan keadaan git itu. **Sesi 19** hanya menyunting **dua berkas `docs/`** —
> **tanpa** perubahan kode. **Sesi 20** menyunting **`mejasaham/posisi.py`**, **dua berkas uji**
> (`tests/test_aksi_korporasi_posisi.py`, `tests/test_ui_tulis.py` — yang kedua hanya komentar), dan
> **tiga berkas `docs/`** (`docs/keputusan.md`, `docs/arsitektur.md`, `docs/lanjutan.md`). **Sesi 21**
> menyunting **empat berkas `docs/` saja** (`docs/riset-pyside6-gc-2026-10.md`,
> `docs/laporan-pyside6-siap-kirim.md`, `docs/keputusan.md`, `docs/lanjutan.md`) — **tanpa** kode.
> **Sesi 22** juga **dokumen saja**: `docs/keputusan.md` (K74/K75, baris U31/U32, catatan sesi 22),
> `docs/arsitektur.md` (**T76**), dan `docs/lanjutan.md`. **Sesi 23** menyunting
> **`tests/test_ui_tulis.py`** (satu uji + konstanta + helper — **tanpa** kode aplikasi) dan **tiga
> berkas `docs/`** (`docs/keputusan.md`, `docs/arsitektur.md`, `docs/lanjutan.md`). **Sesi 24** juga
> **dokumen saja**: `docs/keputusan.md` (**K76** + catatan sesi 24) dan `docs/lanjutan.md`. **Sesi 25**
> menambah **satu berkas `docs/` baru** (`docs/rasio-bank-kandidat-2026-10.md`), menyunting
> `docs/keputusan.md` (**U33** + catatan sesi 25) dan `docs/lanjutan.md` — **tanpa** kode aplikasi,
> **tanpa** impor, **tanpa** basis data; seluruh artefaknya di `.uji-data/riset-idx/rasio-bank/`
> (**gitignored**). **Sesi 26** juga **dokumen saja**: `docs/keputusan.md` (**K77–K80**, baris U33,
> catatan sesi 26), `docs/lanjutan.md`, `docs/rasio-bank-kandidat-2026-10.md` (§0 status keputusan),
> dan `docs/ideas.md` (ide metrik bank syariah) — **tanpa** kode, impor, atau basis data. **Sesi 27**
> menyunting **tiga berkas kode** (`mejasaham/ingesti.py` — bidang `RasioBank.sumber` + pemakaiannya,
> `mejasaham/berkas.py` — pengisian dari kolom berkas, `mejasaham/potret.py` — sumber ikut kembali),
> **dua berkas uji** (`tests/test_impor_berkas.py` 2 uji, `tests/test_ingesti.py` 1 uji), dan **tiga
> berkas `docs/`** (`docs/keputusan.md`, `docs/arsitektur.md` **T77**, `docs/lanjutan.md`) — **tanpa**
> impor dan **tanpa** basis data; bukti di `.uji-data/uji-k78/bukti/` (**gitignored**). **Sesi 28**
> **dokumen saja**: `docs/keputusan.md` (**K81–K82** + catatan sesi 28, penanda tafsir di K78),
> `docs/arsitektur.md` (**T77** — tafsir K81 + batas yang menjadi #28), `docs/lanjutan.md`, dan
> `docs/rasio-bank-kandidat-2026-10.md` (catatan pengisian `sumber` per baris) — **tanpa** kode/uji,
> impor, atau basis data. **Sesi 29** menyunting **satu berkas kode** (`mejasaham/potret.py` —
> `_fundamental` mengisi `sumber=baris["sumber"]`), **satu berkas uji** (`tests/test_potret.py` —
> dua uji baru + satu butir docstring modul), dan **empat berkas `docs/`** (`docs/keputusan.md` **K82**
> + catatan sesi 29, `docs/arsitektur.md` **T78** + penutup batas di **T77**, `docs/lanjutan.md`,
> `docs/rasio-bank-kandidat-2026-10.md` §6 status #28) —
> **tanpa** impor dan **tanpa** basis data; bukti di `.uji-data/uji-k82/bukti/` (**gitignored**).
> **Sesi 30** **dokumen saja**: `docs/keputusan.md` (**K83–K84** + penunjuk di K68/K80 + catatan
> sesi 30), `docs/lanjutan.md`, `docs/rasio-bank-kandidat-2026-10.md` (§0/§6 status verifikasi), dan
> `docs/laporan-pyside6-siap-kirim.md` (penunjuk K84) — **tanpa** kode/uji, impor, atau basis data.
> **Sesi 31** **menulis data, bukan kode**: `konfigurasi/rasio-bank.csv` di folder data
> (`.uji-data/mejasaham/`, **gitignored**), basis data kerja + **snapshot 12** + arsipnya
> (`arsip-snapshot/2026-10-11/snapshot-12/`, **gitignored**), dan **empat berkas `docs/`**
> (`docs/keputusan.md` — catatan sesi 31, K83/K80/K68, **U34**; `docs/arsitektur.md` — **T79**;
> `docs/lanjutan.md`; `docs/rasio-bank-kandidat-2026-10.md` — §8) — **tanpa** perubahan
> `mejasaham/` atau `tests/`; bukti `.uji-data/uji-k83/` (**gitignored**).
> **Sesi 31 (lanjutan) dokumen saja**: `docs/keputusan.md` (**K85–K87** + penunjuk U34/K80 +
> catatan sesi 31 lanjutan), `docs/lanjutan.md`, `docs/arsitektur.md` (penunjuk K86 di **T79**), dan
> `docs/rasio-bank-kandidat-2026-10.md` — **tanpa** kode, data, atau basis data.
> **Sesi 32** **menulis data, bukan kode**: `konfigurasi/emiten.csv` di folder data
> (`.uji-data/mejasaham/`, **gitignored** — kini berisi `jenis`/`sektor_sumber` hasil
> `--ambil-jenis`), basis data kerja + **snapshot 13** + arsipnya **gitignored**, dan **tiga berkas
> `docs/`** (`docs/keputusan.md` — catatan sesi 32 + penunjuk K21/K80/K87; `docs/lanjutan.md`;
> `docs/rasio-bank-kandidat-2026-10.md` — §9) — **tanpa** perubahan `mejasaham/` atau `tests/`;
> bukti `.uji-data/uji-jenis-kerja/` (**gitignored**).
> **Sesi 33 dokumen saja** (tiga berkas `docs/`) dan **sesi 34 kode + uji + dokumen**:
> `mejasaham/skema.py` (migrasi 015), **`mejasaham/konteks_pasar.py` (baru)**,
> `mejasaham/pengatur.py`, `mejasaham/dasbor.py`; **`tests/test_konteks_pasar.py` (baru)**,
> `tests/test_dasbor.py`, `tests/test_db.py`; `docs/keputusan.md` (K61/U26 + sesi 34),
> `docs/arsitektur.md` (**T80**), `docs/skema-data.md` (**5.16**), `docs/lanjutan.md` — **sudah
> di-commit** 19 Okt 2026: **`c862d16`** = kode + uji aksi #23, lalu **commit dokumen ini** =
> catatan sesi 33–34. **Basis data kerja tidak disentuh**; salinan untuk pengukuran ada di
> `.uji-data/uji-k61/` (**gitignored**).
> **Sesi 35 tooling + dokumen**: `requirements-build.txt` (baru), `tools/entry_exe.py` (baru),
> `tools/build_exe.py` (baru), `tests/test_pengemasan.py` (baru); `README.md`, `AGENTS.md`,
> `docs/keputusan.md` (sesi 35), `docs/arsitektur.md` (**T81**), `docs/lanjutan.md` —
> **belum di-commit** (commit hanya atas permintaan). Keluaran `build/`, `dist/`, dan
> `.uji-data/uji-tahap5/` **gitignored**.
> Semua pekerjaan **sesi 20–34 sudah di-commit** (19 Okt 2026, atas permintaan pengguna): **`4bbaf20`**
> = kode + uji (sesi 20/23/27/29), **`eb30214`** = dokumen sesi 21–32, **`c862d16`** = kode + uji
> sesi 34, dan **catatan keadaan git ini**. Data sesi 31–32 (snapshot 12/13, `rasio_bank`,
> `emiten.csv`) tetap **gitignored** — sengaja tidak masuk commit.
> Berkas bukti K69 (`.uji-data/uji-k69/`, `.uji-data/riset-idx/k69/`), K75
> (`.uji-data/uji-k75/`, `.uji-data/riset-idx/k75/`), K78 (`.uji-data/uji-k78/`), K82
> (`.uji-data/uji-k82/`), K61 (`.uji-data/uji-k61/`, `.uji-data/riset-idx/k61/`), pilot rasio bank
> (`.uji-data/riset-idx/rasio-bank/`), dan `.tmp/` **gitignored**.
> Bila `git status` memuat berkas yang tidak ada di daftar itu, itu pekerjaan sesi lain — baca ulang
> berkasnya sebelum menyunting, jangan menimpanya. Commit dilakukan **atas permintaan pengguna**,
> bukan oleh sesi agen.

---

**Sesi 12 (aksi #19b — impor dari jendela + "Pakai ukuran patuh" + pilihan dari daftar):** lihat
ringkasan keadaan di atas dan `docs/keputusan.md` bagian 5 ("Pelaksanaan aksi #19b"). Tiga hal yang
paling perlu dibaca sesi berikutnya: (a) **satu cacat perilaku ditutup** — impor yang terkunci
sebelumnya menunggu **11,16 dtk** (dua penantian `busy_timeout`: penulisan lalu percobaan mencatat
log), sesudahnya **5,62 dtk**; (b) **jebakan baru** masuk bagian 6 (dua pekerja berurutan pada satu
slot `_pekerja`); (c) pada basis data uji, **ukuran patuh = ukuran akhir** karena batas yang mengikat
bobot 10% — jadi bukti data nyata membuktikan **jalur & angkanya sama**, sedangkan ukuran yang
berubah diuji `tests/test_risiko.py`. Bukti: `.uji-data/uji-impor-jendela/bukti/`
(`bukti-impor-jendela.txt`, `bukti-uji-pada-kode-lama.txt`).

**Sesi 11b (pencatatan saja, tanpa perubahan kode):** pengguna meminta pekerjaan **dihentikan dulu**
("jangan ngoding dulu"), menanyakan **apa yang perlu diputuskan**, dan akan melanjutkannya di **sesi
baru**. Karena itu sesi ini **hanya mencatat tiga pertanyaan** di `docs/keputusan.md` bagian **3.8** —
**P34** (tindakan tulis mana yang masuk jendela sesudah #19b/#19c; usulannya tetap mengikuti K59 c
lalu **#19d `ubah-stop` + keputusan right issue**), **P35** (cabang PRD 9.7 **"pakai ukuran yang
patuh"** belum ada di jendela; usulannya ditambahkan di layar 11.4 bersama #19b), dan **P36** (seberapa
lengkap jendela dibanding baris perintah; usulannya jendela = jalur harian, dengan **pilihan rencana &
posisi dari daftar** sebagai yang wajib masuk). **Tidak satu pun memblokir #19b/#19c** — urutan kerja
sesi berikutnya tetap sama walau ketiganya belum dijawab. Yang berubah hanya `docs/keputusan.md` dan
berkas ini; **status uji tidak berubah** (`pytest` → 833 lulus), dan kode sesi 11 **belum** di-commit
saat itu — commitnya menyusul di sesi 11c.

---

**Sesi 11c (pencatatan saja, tanpa perubahan kode):** pengguna menjawab **"sesuai rekomendasi"** atas
P34–P36 dan meminta pekerjaannya dilanjutkan **di sesi baru**. Ketiganya kini **keputusan** di
`docs/keputusan.md` bagian 1 — **K62** (urutan tindakan tulis lanjutan: #19b impor → #19c cadangan +
daftar → **#19d `ubah-stop` + keputusan right issue**; `ubah-stop` **tidak** diselipkan sebelum impor),
**K63** (layar 11.4 memperoleh pilihan **"Pakai ukuran patuh"**, dihitung **sebelum** konfirmasi
supaya dialognya menyebut angka yang benar-benar ditulis, dikerjakan bersama #19b), **K64** (jendela =
**jalur harian**; **pilihan rencana & posisi dari daftar** wajib masuk, sedangkan `--id-posisi`
eksplisit, pajak/biaya pengguna, broker, ekspor, entri kandidat, `--ekuitas-harian`, dan `--pulihkan`
tetap di baris perintah) — dengan bentuk teknisnya **T71** di `docs/arsitektur.md`, dicatat **sebelum**
dikerjakan seperti T69. Yang berubah hanya ketiga berkas `docs/`; **status uji tidak berubah**
(`pytest` → 833 lulus, dijalankan ulang sesudah pencatatan: **25,16 dtk**). **Commitnya:** `874e095`
(kode + 23 uji) lalu `82f3064` (catatan T70/T71 + K62–K64), keduanya atas permintaan pengguna; sesudah
itu working tree **bersih**.

---

**Sesi 11 (aksi #19 tahap 1): tiga pencatat transaksi dari jendela — SELESAI.** (1) **Catat transaksi**
di layar 11.3 · (2) **simpan rencana** di 11.4 · (3) **catat jurnal** di 11.5, ketiganya lewat berkas
baru **`mejasaham/ui/tulis.py`** (bebas Qt, diuji tanpa layar) yang memanggil fungsi inti yang **sama**
dengan baris perintah — bukan jalur SQL kedua. K59 dijalankan apa adanya: kunci tulis **ditunggu**
sampai `busy_timeout` habis lalu berhenti dengan pesan yang memuat **"Jendela belum menulis apa
pun"**; **konfirmasi untuk semua** tindakan, berisi angka yang akan ditulis (dan dialognya menyebut
pelanggaran PRD 9.7 apa adanya — menyetujuinya berarti menerimanya); sesudah berhasil layarnya
**dimuat ulang dari baris tersimpan** dengan pesan hasilnya dipertahankan. Dua aturan **dipindahkan ke
inti** supaya dua mode tidak bisa bercabang (pola T65): perpindahan status `watchlist` → `rencana`
kini di `risiko.simpan_dari_kandidat` (kegagalannya jadi `peringatan`, bukan pembatalan), dan kalimat
kunci tulis kini di `db.KALIMAT_TERKUNCI` (`db.BasisDataTerkunci`) — sehingga kunci yang gagal di
baris perintah **berhenti berbunyi traceback** dan mencetak kalimat yang sama. Tiga hal yang perlu
dibaca sesi berikutnya: (a) **`--pulihkan` tetap tidak ada di jendela** dan itu disebut di layar
(K59 e); (b) **letak tindakannya** dicatat di `docs/keputusan.md` bagian 5 (transaksi 11.3, rencana
11.4, jurnal 11.5 — jendela tetap lima layar); (c) dua **jebakan baru** masuk bagian 6 (mutasi uji
yang tertinggal karena `git checkout` tidak memulihkan berkas *untracked*; slot Qt yang tidak boleh
diberi parameter keyword-only). **Verifikasi: `.\.venv\Scripts\python -m pytest` → 833 lulus**;
8× uji jendela+tulis berturut-turut tanpa proses yang mati; bukti atas data nyata
`.uji-data/uji-tulis-jendela/bukti/bukti-tulis-jendela.txt` (**kelima view SAMA** dengan jalur baris
perintah; kunci tulis ditunggu 5,56 dtk lalu 0 baris tertulis). Rincian sesinya di
`docs/keputusan.md` bagian 5; keputusan teknisnya **T70**.

---

**Sesi 10 (lanjutan sesudah aksi #20): tiga pekerjaan kecil, semuanya selesai.** (1) **Aksi #21** — perintah
baru **`--kerangka-rasio-bank`** menulis `rasio-bank.csv` dari daftar kode ber-`jenis='bank_keuangan'`
pada revisi terkini, **seluruh sel selain `kode` kosong**, bentuk kolomnya dipinjam dari
`berkas.SPESIFIKASI["rasio_bank"]`; terukur atas `.uji-data/uji-jenis`: **49 baris**, sel terisi
selain `kode` **0**, dan `--impor` atas kerangka kosong **keluar 1** dengan pesan per baris
(`rasio-bank.csv baris 36: kolom `periode` wajib diisi`) sementara `rasio_bank` tetap **0 baris** —
jadi kerangka kosong gagal berisik, bukan masuk sebagai nol. Berkas tujuan yang **sudah berisi**
ditolak (kecuali masih template bawaan AC-12). +5 uji; satu cacat ditemukan uji itu sendiri
(perintahnya sempat jalan **dua kali** karena dispatch ganda di `main()`). (2) **Glif rusak** —
`mejasaham/metrik.py` masih memuat **33 glif mojibake di 24 baris** (≤ 12×, ÷ 10×, → 5×, − 3×, × 2×,
√ 1×), sekitar **sepuluh** di antaranya **pesan yang tampil ke pengguna**; semuanya diganti glif yang
benar, **sisa 0** bila diukur dari byte, dan penjaganya `tests/test_glif_teks.py` **terbukti gagal**
atas berkas lama. (3) **Cacat PySide6 6.12.0 + CPython 3.14.7 diriset** → **`docs/riset-pyside6-gc-2026-10.md`**:
kombinasi itu **didukung** paketnya (`Requires-Python >=3.10,<3.16`, classifier 3.14), gejalanya
terukur, dua repro sintetis **tidak** memicunya (jadi belum terisolasi di luar pytest), dan langkah
berikutnya berurut: laporan upstream → uji Python 3.13 → uji PySide6 lain. **Verifikasi:
`.\.venv\Scripts\python -m pytest` → 810 lulus**; bukti aksi #21 di
`.uji-data/uji-kerangka-rasio-bank/bukti/`.

**Sesi 10 (aksi #20, K58/T66):** **dasbor menampilkan IHSG + rezim + breadth.** `mejasaham/dasbor.py`
menyusun konteks pasar lewat `_konteks_pasar` — potret → `metrik.metrik_semua` → `saring.semesta_likuid`
→ `metrik.breadth` → `metrik.rezim_pasar` — jalur yang **sama** dengan `pengatur.jalankan_saring`, dan
menyimpannya di `Dasbor` (`pasar`, `breadth`, `rezim`, `preset_pasar`). Kalimat tetap *"rezim pasar &
breadth belum dapat dinilai … `harga_indeks` … belum diisi sumbernya"* **dibuang**; preset yang dipakai
ialah preset yang menghasilkan skor tersimpan (bila belum ada skor: bawaan `--saring`), dan bila
keduanya tidak ada, breadth dinyatakan **tidak dihitung beserta sebabnya** — bukan dihitung dengan
ambang tebakan. Terukur atas salinan `.uji-data/uji-jurnal` → **`.uji-data/uji-dasbor`** (snapshot 12):
`--saring` dan `--dasbor` sama-sama berbunyi **`88 dari 225 emiten likuid · breadth 39,1% · rezim
RISK-OFF`** dengan `IHSG 6.093 (+62 / +1,03%)`, sedangkan pada kode lama dasbor berbunyi 2,8 dtk
**tanpa** baris `Pasar` dan **dengan** kalimat yang salah itu (`bukti-0-dasbor-kode-lama.txt`).
**Dua temuan yang harus dibaca sesi berikutnya:** (1) **biaya** — karena jalurnya sama dengan saringan,
`--dasbor` ikut membayar potret + seluruh metrik + breadth: **2,8 dtk → 33–61 dtk** pada basis data
999.421 bar (setara `--saring` 32–55 dtk pada folder yang sama; rincian per bagian di
`bukti-keadaan.txt`), sedangkan **angka `--saring` sendiri tidak berubah** — yang bertambah hanya
pembacaan di dasbor; (2) **cacat PySide6 6.12.0 + CPython 3.14.7** — pekerjaan baru di utas pekerja
menyingkap proses yang mati (`access violation` / `Fatal Python error: Aborted`) di
`tests/test_ui_jendela.py`, **tanpa satu pun traceback Python**: kode lama 0 gagal/18 jalan, kode baru
**7/18**, dengan blok konteks pasar dimatikan 0/12, dengan GC siklik dimatikan 0/12, dengan pohon Qt uji
ditahan hidup 12/12 — jadi pemicunya pengumpulan sampah **siklik** sementara utas pekerja hidup.
Penangkalnya **T68** — satu penahan berpenghitung (`mejasaham/ui/pekerja.py:tahan_gc_siklik()`) yang
dipakai `Pekerja.run` **dan** `Jendela.tunggu_pekerja`, sebab `gc.enable()` adalah keadaan **proses**:
versi pertama yang hanya menjaga `Pekerja.run` **bocor** (satu pekerja yang selesai menyalakan GC
kembali tepat ketika jalur tunggu masih mengandalkannya mati) dan suite penuh masih gagal 1 dari 8
jalan. Sesudah penghitungnya ada: **0 gagal/10** jalan uji jendela+dasbor dan **0 gagal/8** jalan
suite penuh (810 lulus tiap jalan; 803 sebelum penjaga glif dan aksi #21). **Verifikasi: `.\.venv\Scripts\python -m pytest` → 805
lulus** sesudah aksi #20 (793 + 6 uji dasbor baru + 4 uji penahan GC + 2 uji penjaga glif `tests/test_glif_teks.py`) — dan **810 lulus** sesudah aksi #21 (+5 uji kerangka rasio bank); delapan kali berturut-turut untuk angka 805, sebelum penangkal,
suite penuh berhenti di uji jendela pada percobaan pertama. Bukti `.uji-data/uji-dasbor/bukti/`,
pembuatnya `.uji-data/riset-idx/dasbor/bukti-dasbor.py`; keputusan teknisnya T66 (diperluas) dan
**T68** di
`docs/arsitektur.md`, catatan sesinya di `docs/keputusan.md` bagian 5.

**Sesi 9 (sebelumnya):** **aksi #10 tahap pertama SELESAI — panel jendela PySide6 (lima layar PRD 11)
sudah jalan; jendela masih MEMBACA saja.**
`mejasaham/ui/jendela.py` yang tadinya kerangka 21 baris kini memuat **lima layar PRD 11** — dasbor
(11.1) · screener (11.2) · detail emiten & tesis (11.3) · kalkulator risiko (11.4) · jurnal &
kepatuhan (11.5) — dengan dua berkas baru: **`mejasaham/ui/tabel.py`** (bentuk tabel, **bebas Qt**,
diuji tanpa layar) dan **`mejasaham/ui/pekerja.py`** (pekerjaan berat di utas pekerja supaya jendela
tidak membeku). Jendela **tidak menghitung apa pun**: tiap layar memanggil fungsi inti yang sama
dengan baris perintah lalu menampilkan `ringkas()`-nya — dan itu dibuktikan: blok kalkulator risiko
dari jendela dan dari `--hitung-risiko` **sama persis, 24 baris, 0 perbedaan**. Tiga teks/aturan yang
tadinya hanya ada di `cli.py` dipindahkan ke inti supaya dua mode tidak bercabang
(`risiko.ringkas_hasil`, `pengatur.LaporanSaring.catatan_peringkat_kosong`,
`kandidat.untuk_rencana`) — dan **justru karena pemindahan itu** tertangkap satu cacat nyata: panel
risiko versi pertama memilih entri kandidat **pertama** diam-diam, sedangkan baris perintah
menolaknya. Dua cacat lain ditemukan dari bukti atas data nyata: pekerja diberi metode `Panel.tugas`
alih-alih hasil pemanggilannya, dan **angka basi tetap tampil di sebelah pesan "GAGAL"** (kini
dibuang `Panel.kosongkan()`). **Cacat keempat muncul dari suite penuh yang sekali berakhir dengan
proses yang mati** (`QThread` dimusnahkan saat jendela ditutup di tengah pekerjaan): penutupan kini
**menunggu** pekerja selesai (`Jendela.closeEvent` + `tunggu_pekerja`), dan batas tunggu yang lewat
bertanya kepada pengguna, bukan memaksa tutup. Keputusan teknisnya **T65** (`docs/arsitektur.md`); rinciannya di
`docs/keputusan.md` bagian 5. **Verifikasi: `.\.venv\Scripts\python -m pytest` → 793 lulus** (768 + 25
uji baru: 7 tanpa Qt, 18 di platform `offscreen`). Buktinya `.uji-data/uji-jendela/jendela/`
(`bukti-1` … `bukti-8`) + **lima tangkapan layar** `tangkapan-1..5-*.png`. **Batas bukti: jendela
dijalankan di platform `offscreen`; tampilan sesungguhnya di layar Anda belum pernah dilihat.**
Sesi ini juga **memulihkan T62 yang hilang** dari `docs/arsitektur.md` dan **meng-commit pekerjaan
aksi #18** yang belum ter-commit (`35aa369`).

**Sesi 9b (pencatatan saja, tanpa perubahan kode):** pengguna menjawab **"sesuai rekomendasi"** atas
empat hal yang diajukan sesudah aksi #10 tahap 1, dan meminta tidak ada pekerjaan teknis pada sesi
pencatatan ini → dikunci **K55–K58** (`docs/keputusan.md` bagian 1) + **T66/T67**
(`docs/arsitektur.md`); rinciannya di `docs/keputusan.md` bagian 5. Urutan pekerjaan berikutnya:
**aksi #20** (dasbor menampilkan IHSG + rezim + breadth; K58/T66) dan **aksi #21** (kerangka
`rasio-bank.csv`; K57/T67) — keduanya kecil dan **tidak menunggu apa pun** — lalu **aksi #19**
(tindakan tulis dari jendela; K55) yang menuntut perilaku kunci tulis ditetapkan **lebih dulu**.
**Satu cacat ikut ditemukan saat menyiapkan pertanyaannya dan kini tercatat sebagai K58:** dasbor
**selalu** menulis *"rezim pasar & breadth belum dapat dinilai"* padahal `harga_indeks` **terisi**
(IHSG & LQ45, 1.199 bar masing-masing, 2021-10-11 → 2026-10-09) dan `--saring` mencetak
`breadth 39,1% · rezim RISK-OFF` **pada snapshot yang sama**. Tiga klaim dokumen yang salah
karenanya **sudah dikoreksi di berkas ini** (baris dasbor di bagian 2; dua daftar sisa pekerjaan di
bagian 9; lihat juga kotak koreksi di bagian 9). Verifikasi keadaan: pytest **793 lulus** — tidak
berubah, dan itu memang yang diharapkan karena tidak ada kode yang disentuh.

**Sesi 8 (sebelumnya):** **aksi #18 SELESAI — cacat `;` ditutup dari dua sisi.**
(**a) Datanya dipulihkan:** **65 baris** `notasi_khusus` yang `keterangan`-nya terpotong di `;` pertama saat
impor langkah 3 kini memuat teks **utuh** dari baris mentah berkasnya (`penanda: TANGGAL_MULAI…` **0 → 66**,
`penanda: AKTIF_DUA_KALI…` **3 → 4** sehingga keempat kode K47 lengkap, `kutipan keputusan:` **105 → 172**);
impor menulis **65 baris baru** (append-only), `konfigurasi/notasi-khusus.csv` diperbarui, dan `--saring`
**tetap** "Kandidat teratas" (likuid **201** · lolos saring **9**). (**b) Pembacanya dibuat berisik:**
`mejasaham/berkas.py` kini **menolak** baris yang memuat kolom berlebih **yang berisi** (pesannya menyebut
berkas, nomor baris, isi yang akan hilang, dan jalan keluarnya `csv.writer`), sedangkan kolom berlebih
**kosong** (`;;` di ujung) tetap diterima; berkas impor langkah 3 yang lama **terbukti ditolak** — bukti
end-to-end, bukan berkas uji. **Verifikasi: `.\.venv\Scripts\python -m pytest` → 768 lulus** (765 + 3 uji
baru; **satu di antaranya terbukti gagal pada kode lama** di worktree `HEAD`: `DID NOT RAISE GalatIngesti`).
Buktinya `.uji-data/uji-aksi-18/` (`bukti-0` … `bukti-5`), pembangun & pemeriksanya di
`.uji-data/riset-idx/k53-k54/`. **Sesi 7 (sebelumnya)** menutup aksi #17 (K53 + K54) — rinciannya di bawah.

**Sesi 7 (sebelumnya):** **aksi #17 SELESAI: K53 + K54 sudah dijalankan atas basis data
`.uji-data/mejasaham`.** (K53) penanda `DITAHAN_K46_PENGUMUMAN_20_FEB_2024` **dilepas**, pengumuman
`Peng-S-00006/BEI.PLP/02-2024` menempel pada `keterangan` episode yang **sedang berjalan** untuk **33 kode**
(bukan sebagai `tanggal_mulai`), dan **episode MTFN 2023–2024 yang hilang dibentuk** — proxy `2023-10-30` →
`2024-08-29` dari `Peng-UPT-00011/BEI.PLP/08-2024`, lima dokumennya pindah dari episode 2025-06-30. (K54) dua
baris K41 ditambahkan: `ELTY` **2023-07-03 → 2023-10-19** · `ARTI` **2021-11-30 → 2023-11-23**, dengan penanda
"di luar cakupan API". Urutannya seperti K51/K52: cadangkan dulu · bangun berkas dari **revisi terkini basis
data** (2.450 baris = 2.447 + 3) · impor sebagai revisi baru · perbarui `konfigurasi/notasi-khusus.csv` ·
buktikan `--saring` **tetap** "Kandidat teratas" (likuid **201** · lolos saring **9**, snapshot 10). **Tanpa
satu pun perubahan kode aplikasi.** **Verifikasi: `.\.venv\Scripts\python -m pytest` → 765 lulus (28,01 dtk;
folder sementara `.tmp\t38`).** Buktinya `.uji-data/uji-k53-k54/` (`bukti-0` … `bukti-10`) dan
`.uji-data/riset-idx/k53-k54/`, pembangunnya `.uji-data/riset-idx/k53-k54/buat-k53-k54.py` (read-only atas
basis data, **idempoten**: hasil dari basis data **sesudah** impor byte-identik dengan hasil dari **cadangan
pra-impor**). **Dua hal yang perlu diketahui sesi berikutnya:** (1) aturan penempelan yang benar adalah
"episode **pemilik rekaman SPT tepat sebelumnya**", bukan "episode termuda" — aturan termuda terbukti salah
untuk `TECH` (episode jalur API 2024-01-09) dan tetap dihitung sebagai pembanding sehingga selisihnya
dilaporkan per kode; (2) **temuan baru yang BELUM diperbaiki (aksi #18):** `keterangan` **66 dari 171 baris**
berkas impor langkah 3 terpotong di `;` pertama **saat impor** (berkas itu ditulis dengan penggabungan string,
bukan `csv.writer`), sehingga penanda `TANGGAL_MULAI_TIDAK_DINYATAKAN_SUMBER_MANA_PUN` **0 kali** di revisi
terkini, penanda K47 tinggal **3 dari 4** kode, dan MTFN kehilangan 1.326 karakter — ukurannya di
`.uji-data/riset-idx/k53-k54/potong-keterangan.txt`.

**Sesi 6 (sebelumnya):** **Tinjauan visual pengumuman 20 Feb 2024 (K46)
SUDAH DIJALANKAN** atas kedua halaman PDF-nya (dirender lalu dilihat, memakai PySide6 `QtPdf` yang
sudah terpasang — tanpa dependensi baru). Dari tinjauan itu muncul **dua temuan**, diajukan sebagai
U24/U25, dan **keduanya sudah diputuskan pengguna pada sesi yang sama** → **K53** dan **K54**:
(**K53**) penanda `DITAHAN_K46_…` **dilepas** — tanggal 20 Feb 2024 **bukan** `tanggal_mulai`
(terukur: status ke-34 kode pada rekaman sebelum pengumuman **identik** dengan kolom di pengumuman
itu, 34 identik · 0 berbeda; UPT MTFN 29 Agu 2024 bahkan mencabut pengumuman itu sebagai salah satu
dari delapan sebab) — sekaligus **episode MTFN 2023–2024 yang hilang** dibentuk (proxy ≤ 2023-10-30 →
selesai **2024-08-29** dari UPT-nya); (**K54**) bentuk baris K41, sebab **K41 ternyata belum
dijalankan atas data** (penanda "di luar cakupan API" **0 kali**, `ELTY` **0 baris**, `ARTI` punya
baris tanpa penandanya) → `ELTY` 2023-07-03 → 2023-10-19 · `ARTI` 2021-11-30 → 2023-11-23.
**Pelaksanaan kedua keputusan itu adalah pekerjaan sesi berikutnya — aksi #17 di bagian 4** (pengguna
meminta tidak ada pekerjaan teknis pada sesi pencatatan ini). **Tanpa satu pun perubahan kode
aplikasi, tanpa impor, tanpa baris basis data yang ditulis.** Buktinya `.uji-data/uji-tinjauan-k46/`
(`bukti-1` … `bukti-9` + `bukti-keadaan.txt`), pembuatnya `.uji-data/riset-idx/tinjauan-k46/`.
**Verifikasi: `.\.venv\Scripts\python -m pytest` → 765 lulus.**

**Sesi 5 (sebelumnya):** **Langkah 3 dan langkah 4 rencana K36–K41 SELESAI**:
penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` **sudah dilepas** atas basis data `.uji-data/mejasaham`
(cadangkan dulu · bangun berkas dari revisi terkini basis data · impor sebagai revisi baru · perbarui
berkas konfigurasi), dan **`--saring` berbunyi "Kandidat teratas"** — likuid **201**, lolos saring 9,
bukan lagi PERINGKAT SEMENTARA. **Tanpa satu pun perubahan kode aplikasi**; **765 uji lulus**.
Terukur dari langkah 3: **171 baris impor /
159 kode** (138 terbuka, 33 tertutup penutup UPT, 65 episode bertanggal mulai proxy, 4 penanda K47),
**34 baris 20 Feb 2024 tetap ditahan** (K46), impor keluar 0, `--saring` likuid **205 → 201**
(`KJEN`, `SINI`, `UNSP`, `ZATA`). Berkasnya `.uji-data/riset-idx/impor-suspensi-20261016/notasi-khusus.csv`,
pembuatnya `.uji-data/riset-idx/buat-impor-suspensi.py`, buktinya `.uji-data/uji-impor-suspensi/bukti-1`
… `bukti-9`. Dua keputusan dari pekerjaan itu: **K50** (T60 dibaca sebagai satu baris per **kode ×
episode**) dan **K51** (cara melepas penanda: **bangun berkas dari basis data**, bukan menyunting
`konfigurasi/notasi-khusus.csv`). Keduanya **sudah dijalankan** pada langkah 4 (sesi 5): 2.447 revisi
baru tertulis dan `--saring` berbunyi **"Kandidat teratas"**, likuid 201. **Tanpa satu pun perubahan
kode aplikasi.**
**Verifikasi: `.\.venv\Scripts\python -m pytest` → 765 lulus (19,51 detik, folder sementara `.tmp\t36`).**
Sisi UPT sudah selesai 12 Okt 2026 (41 baris), sisi SPT 16 Okt 2026 (1.118 baris / 162 kode).
Keputusan K36–K52 (`docs/keputusan.md` bagian 1) dan T59–T61 (`docs/arsitektur.md`) sudah terkunci.
Untuk commit terbaru, jalankan `git log --oneline -3` — berkas ini sengaja tidak menyebut hash-nya
sendiri supaya tidak basi setiap kali di-commit.

**Rencana lanjutan yang sudah dikunci (K36–K41) — kerjakan berurutan:**

1. ~~**Rekonsiliasi seluruh rekaman SPT multi-kode per kode**~~ — **SELESAI 16 Okt 2026** (29 rekaman =
   26 peristiwa; berkas dan temuannya di atas). Sisi UPT juga sudah selesai (12 Okt 2026, 41 baris).
2. **Tutup episode (UPT) sesudahnya** — **sudah dikerjakan sebagai bagian dari langkah 3**, bukan
   sebagai tahap tersendiri: penutup UPT dipakai mengisi `tanggal_selesai` pada **33 episode**, dan
   `tanggal_selesai` hanya diisi dari penutup yang terkonfirmasi (T60). Dua hal yang **belum** selesai
   di sini dan sengaja tidak dikarang: **65 episode** tanggal mulainya tidak dinyatakan sumber mana pun
   (proxy + penanda), dan **6 penutup** tidak dipakai karena menutup suspensi yang lebih tua daripada
   rekaman pertama kode itu (`ARTI`, `BAPI`, `ELTY`, `FLMC`, `MTFN`, `OCAP`) — sebabnya tertulis di
   `keterangan` barisnya, dan daftarnya di `bukti-5`/`bukti-9`.
3. ~~**Tulis berkas impor per kode**, lalu muat lewat `--impor` (K36, T59) ke basis data uji dulu;
   kemudian periksa ulang `--saring`.~~ — **SELESAI 16 Okt 2026 (sesi 4)**; 171 baris, impor keluar 0,
   `--saring` likuid 205 → 201. Bentuk berkasnya T60 **dibaca sebagai T61** (K50): satu baris per
   (kode × episode), seluruh pengumuman `dipertahankan` masuk `keterangan` baris itu.
4. ~~**Penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` dilepas**~~ — **SELESAI 16 Okt 2026 (sesi 5)**;
   diputuskan lewat **K52** dan dijalankan berurutan: cadangan lebih dulu, berkas turunan basis data,
   impor revisi baru, berkas konfigurasi diperbarui, lalu `--saring` dibuktikan berbunyi **"Kandidat
   teratas"**. Rinciannya di bagian 4 aksi #15. **Dua angka pada catatan lama perlu dikoreksi** dan
   koreksinya di bagian 6: berkas `konfigurasi/notasi-khusus.csv` yang dikhawatirkan "hanya 122 baris"
   itu ternyata **berkas lain** — berkas yang dipakai basis data `.uji-data/mejasaham` memuat **2.276
   baris data** sejak 11 Okt 2026, jadi alasan K51 tetap berdiri (bangun dari basis data) tetapi
   premisnya salah alamat. Impor revisi barunya menulis **2.447 baris baru**, bukan 2.154: angka 2.154
   adalah jumlah baris **berpenanda**, sedangkan 293 baris sisanya ikut tertulis karena kolom
   `sumber`-nya berbeda (isi selain `sumber` tidak berubah).
5. **Perlakuan khusus yang sudah diputuskan, jangan dikarang ulang:** pembukaan satu-pasar bukan penutup
   episode (OCAP Mei/Agu/Nov 2024; K39) · XSBC/XSSI reksa dana diberi penanda di `keterangan`, bukan
   dihitung sebagai saham (K40) · ARTI/ELTY dicatat dengan nomor+tanggal SPT dari kutipan UPT beserta
   penanda "di luar cakupan API" (K41 — **keputusannya sah, tetapi per 16 Okt 2026 sesi 6 ternyata
   BELUM DIJALANKAN atas data**: penandanya 0 kali di `notasi_khusus`, `ELTY` 0 baris; bentuk barisnya
   ditanyakan sebagai **U25**) · satu baris per (kode × episode) dengan tanggal mulai **hanya**
   bila dinyatakan sumbernya (K50) · pelepasan penanda lewat berkas turunan basis data (K51/K52).
6. **Yang masih boleh ditunda:** tinjauan **visual** halaman keputusan satu per satu — **yang 20 Feb 2024
   sudah dijalankan 16 Okt 2026 (sesi 6)** dan hasilnya di `.uji-data/uji-tinjauan-k46/`; yang tersisa
   baris `KOREKSI_*` dan **dua baris tanpa PDF SPT** (ARTI/ELTY, kini masuk U25); penggabungan daftar
   emiten IDX↔KSEI (K44, aturannya sudah ditulis); parameter bursa bersumber sekunder tetap berlabel apa
   adanya sampai SK primer terjangkau (K43).
7. Untuk daftar emiten IDX/KSEI, jangan menghapus kode atau menyimpulkan delisting dari selisih saja.
   Jangan turunkan `jenis=bank_keuangan` dari sektor `Financials` saja; taksonomi itu juga mencakup
   lembaga keuangan nonbank. Jangan mengisi `siklikal_komoditas` otomatis.

---

## 1. Baca dulu sebelum menyentuh apa pun (±5 menit)

| Berkas | Untuk apa |
|---|---|
| `AGENTS.md` | Aturan kerja yang mengikat: 9 aturan keras, ritme "berhenti tiap tahap" (K4), format laporan |
| `docs/keputusan.md` bagian 1 | Keputusan yang **sudah dikunci** (K5–K13). Jangan dipertanyakan ulang tanpa alasan baru |
| `docs/keputusan.md` bagian 2 | **U2–U17 masih usulan**; U18 sudah diputuskan (K13) |
| `docs/keputusan.md` bagian 3 | Pertanyaan yang memblokir (P2, P3, P4, …) — butuh jawaban manusia |
| `docs/keputusan.md` bagian 5 | Riwayat tahap: apa yang dikerjakan, apa yang ketahuan, apa yang belum |
| `docs/arsitektur.md` | Cara kerja sistem + keputusan teknis T1–T56 |
| `docs/skema-data.md`, `docs/konfigurasi.md` | Bentuk tabel & parameter bursa bertanggal |
| `docs/ideas.md` | Yang sengaja ditunda (jangan dikerjakan diam-diam) |

---

## 2. Keadaan sekarang: apa yang sudah jalan

| Bagian | Keadaan | Bukti |
|---|---|---|
| Lapisan basis data | SQLite WAL, skema berversi, append-only, **`temp_store=MEMORY`** (T22) | `mejasaham/db.py`, `tests/test_db.py` |
| Daftar emiten otomatis | **`--ambil-emiten`** → `emiten.csv` dari Master File Efek KSEI (973 kode, K12) | `mejasaham/ksei.py`, `tests/test_ksei_emiten.py` |
| **Kalender libur bursa otomatis** | **`--ambil-kalender`** → `kalender-bursa.csv` dari pengumuman KSEI (K11): kini **2025 (25 libur) + 2026 (22) + 2027 (20) = 1095 baris**, hari bursa diturunkan; **tanpa dependensi baru** (PDF diurai dengan `zlib`+`re`). 2025 terisi lewat **K17** (revisi lebih lama, hanya karena tanggalnya identik) | `mejasaham/kalender.py`, `tests/test_kalender_ksei.py`, `.uji-data/uji-kalender-2025/` |
| Tanggal pencatatan emiten | **Kolom `tanggal_notasi` terisi** dari `Listing Date` KSEI: 888 dari 973 baris; 85 kosong karena sumbernya kosong. Pemetaan namanya masih **P18** | `.uji-data/uji-tanggal-notasi/`, `tests/test_impor_berkas.py` |
| Ingesti 5 tahun | **999.421 bar harga, 916 emiten, 0 gagal**, rentang 2021-10-11 → 2026-10-09 | `.uji-data/refresh-916-ulang.log` |
| Mutu & arsip | Laporan mutu PRD 7.3, arsip snapshot per tanggal. Sejak langkah 8: **hari bursa terakhir 2026-10-09** (dibatasi hari yang sudah lewat, T30) dan tidak ada lagi temuan `kalender_bursa_kosong` | `.uji-data/arsip-snapshot/2026-10-09/snapshot-4/`, `.uji-data/uji-kalender/bukti-keadaan.txt` |
| Gerbang ambang gagal | **Membedakan gagal permanen dari sementara** (K13/U18): 57 kode mati tidak lagi memblokir snapshot, tetapi tetap dilaporkan | `.uji-data/bukti-u18-57-kode.txt` |
| **Satu label sumber harga** | Harga dibaca dari **satu** label saja (T32, K14): label dengan riwayat bar terbanyak, dihitung pada saat snapshot, dilaporkan beserta label yang tidak dipakai, bisa ditimpa `--sumber`. Harga pembanding tidak lagi merusak angka | `mejasaham/potret.py`, `tests/test_sumber_harga.py`, `.uji-data/uji-p17/` |
| **Imbal hasil SUN otomatis** | **`--ambil-sun`** → `imbal-hasil-sun.csv` dari kurva imbal hasil SBN halaman HPW **PHEI** (K16): tenor 10 tahun, kolom *Today*, bertanggal menurut sumbernya. Berkasnya **bertambah**, tidak ditimpa. Terukur: SUN 10 tahun = 7,1845% per 09 Okt 2026 → 718 bp | `mejasaham/sun.py`, `tests/test_sun_phei.py`, `.uji-data/uji-sun/` |
| Saring & skor | Jalan, tetapi **0 kandidat** karena fundamental belum ada | `.uji-data/saring.txt` |
| **Fundamental otomatis** | **`--ambil-fundamental`** (K18) mengambil laporan keuangan tahunan dari sumber data EOD (label tidak resmi), menulis `fundamental.csv`, lalu diimpor lewat `--impor`. Terukur 10 Okt 2026: **794 baris dari 200 emiten** (34 tanpa laporan, 1 gagal, 222 catatan pemetaan) atas semesta likuid 235 — dan `--saring` **berhenti mengatakan 0 kandidat**: `lolos kriteria lain 9 · dinilai 9` | `mejasaham/pengambil.py`, `tests/test_fundamental_yfinance.py`, `.uji-data/uji-fundamental/` |
| **Notasi kosong ≠ bersih** | Ditutup (K19): kriteria `pengecualian_notasi` **tidak diterapkan** selama belum ada data notasi, peringkat tetap keluar, tetapi **kata "kandidat" ditahan** ("PERINGKAT SEMENTARA") dan sebabnya tampil di `--saring`. Dua uji barunya **terbukti gagal pada kode lama** (di sana kriterianya `lolos=True`) | `mejasaham/saring.py`, `mejasaham/pengatur.py`, `tests/test_saring.py` |
| **Tanggal publikasi tidak diketahui** | Ditangani (K19): `tgl_publikasi` = tanggal pengambilan + kolom `asal_tgl_publikasi` (migrasi 007), dijaga CHECK dan ditolak berisik bila tidak dikenal | `mejasaham/skema.py`, `.uji-data/bukti-migrasi-007.txt` |
| Cek sumber kedua | Jalan **beserta cadence-nya** (PRD 7.3 "tiap minggu"): setiap jalan dicatat di tabel `cek_sumber_kedua`, cek tanpa pembanding tidak dihitung memenuhi, dan peringatan muncul di `--refresh` bila lewat 7 hari | `mejasaham/mutu.py`, migrasi 006, `.uji-data/uji-cadence/bukti-*.log` |
| **Tarif broker (B6/B7)** | **DIMUAT 10 Okt 2026** (K22/K23, migrasi 008). Halaman resmi **Stockbit** menyatakan `Fee Beli 0,15%` / `Fee Jual 0,25%`, keduanya **all-in** (biaya broker + levy BEI/KPEI/KSEI 0,043% + PPN 10% + PPh final jual 0,1%). Yang **tidak** dinyatakan sumbernya — tarif minimum dan tanggal berlaku — kini punya tempatnya sendiri: `minimum` **tidak ditulis** → tersimpan `NULL` (bukan 0), `berlaku_sejak` = tanggal pengamatan dengan penanda `asal_berlaku_sejak`, dan penanda *all-in* tersimpan sebagai baris di `parameter_biaya_broker_termasuk`. `--muat-konfigurasi` berbunyi **`biaya_broker … dipakai`** dan **`slippage … dipakai`**, keluar 0 | `.uji-data/riset-tarif-broker/stockbit.md`, `.uji-data/bukti-muat-konfigurasi-{sebelum,sesudah}.txt`, `tests/test_konfigurasi.py`, `tests/test_db.py` |
| **`jenis` emiten dari data (K21)** | **DITURUNKAN 10 Okt 2026.** `--ambil-jenis` menurunkan **hanya `bank_keuangan`** dari `sector`/`industry` yang dinyatakan sumber data, menulis `emiten.csv`, lalu `--impor` memasukkannya. Aturannya satu fungsi murni (`mejasaham/jenis.py`), bisa diuji tanpa jaringan; `siklikal_komoditas` **tidak pernah** diturunkan; emiten tanpa sector/industry tetap **kosong**; `jenis` yang sudah terisi **tidak ditimpa**. Terukur atas data nyata 916 emiten: **49 `bank_keuangan`** (BBRI, BMRI, BBCA, BBNI, BRIS, BJBR, BTPS, …) · **862 `umum`** · **5 kosong** (BOSS, DEAL, ETWA, KAYU, LAPD — sumbernya tidak menyatakan sector/industry). `--saring` melaporkan sebarannya terbedakan | `mejasaham/jenis.py`, `tests/test_jenis_emiten.py`, `.uji-data/uji-jenis/` |
| **Peramban sungguhan menembus IDX** | **Baru, 10 Okt 2026**: Chromium sungguhan membalas **HTTP 200** untuk `www.idx.co.id/id` (judul "PT Bursa Efek Indonesia") — 7 jalur mati sebelumnya karena tidak ada peramban. Tetapi `requests` tetap **403** sekalipun membawa cookie `cf_clearance`, dan **burst langsung diblokir** Cloudflare ("You have been blocked", bertahan >15 menit) | `.uji-data/riset-idx/`, bagian 6 tabel jebakan |
| **Berkas .exe** | **DIBANGUN ULANG 22 Okt 2026 (sesi 37)** — memperbaiki QtCore gagal dimuat akibat DLL ICU 78 dari PATH build. Build memakai PATH Windows bersih; --help keluar 0 dan GUI bertahan 8 detik pada uji offscreen. Suite 911 lulus. **Berikutnya:** pengguna mencoba klik-ganda EXE baru dan memberi tahu pesan galat bila masih gagal. | tools/build_exe.py (T83), tests/test_pengemasan.py, assets/mejasaham.svg, assets/mejasaham.ico |
| **Kandidat & watchlist (F4)** | **JALAN** (Tahap 2 langkah 1): `--kandidat-baru`, `--kandidat-ubah`, `--tinjau-ulang`, `--watchlist`. Tesis wajib sebelum watchlist (AC-4) ditegakkan modul **dan** `CHECK`; perubahan menambah revisi, tidak menimpa | `mejasaham/kandidat.py`, migrasi 009, `tests/test_kandidat.py` (23 uji) |
| **Kalkulator risiko & rencana (F5)** | **JALAN** (Tahap 2 langkah 2): `--batas-risiko-bawaan`, `--ekuitas-harian`, `--hitung-risiko KODE`, `--rencana`. Rumus PRD 9.7 apa adanya, batas risiko sebagai preset berversi, stop bawaan `max(harga masuk − 2 × ATR14, harga pembatal)`, biaya memakai penanda *all-in* K23, dan perilaku menolak PRD 9.7 (ukuran patuh atau pelanggaran diterima tercatat). Batas yang datanya tidak ada disebut **"tidak dinilai"**, bukan dianggap longgar | `mejasaham/risiko.py`, migrasi 010, `tests/test_risiko.py` (62 uji), `.uji-data/uji-risiko/` |
| **Sektor dari sumber data (K25)** | **JALAN** (langkah 2b): kolom `emiten.sektor_sumber` (migrasi 011) diisi `--ambil-jenis` dari `sector` sumber; batas bobot per sektor PRD 9.7 kini **ditegakkan** — `sektor_idx_ic` bila terisi, selain itu `sektor_sumber`, dan taksonominya disebut di keluaran. Terukur atas TLKM: batas sektor **21.600 lembar** (30% ekuitas dikurangi paparan sektor yang sudah tersimpan) | `.uji-data/uji-sektor/`, `tests/test_risiko.py`, `tests/test_jenis_emiten.py` |
| **Notasi, suspensi, dan UMA otomatis (K27/K35)** | `--ambil-notasi` mengambil notasi khusus + API resmi `GetSuspension`/`GetUma`; suspensi ditutup pada UPT, UMA berlaku 30 hari kalender (K35). Uji nyata 11 Okt 2026: 963 riwayat suspensi berkode tunggal (71 aktif), 1.191 baris UMA, 68 emiten papan pemantauan. Tindak lanjut menemukan 56 PDF `>1 Kode` (29 SPT, 27 UPT), semuanya bertaut langsung dari API resmi dan teksnya dapat diekstrak. Berkas tinjauan UPT 39 baris sudah berisi nomor/tanggal/teks PDF; seluruhnya masih perlu tinjauan manual. **Sudah diimpor** (2.276 baris; basis data `.uji-data/mejasaham` memuat 4.552 baris notasi); penandanya **sudah dilepas** 16 Okt 2026 (K52) sehingga `--saring` berbunyi **"Kandidat teratas"** | `mejasaham/notasi.py`, `tests/test_notasi_idx.py`, T58/K35, `docs/riset-suspensi-multi-kode-2026-10.md` |
| **Rekonsiliasi suspensi multi-kode per kode (K37)** | **SELESAI 16 Okt 2026** untuk **kedua sisi**: UPT 27 PDF → **41 baris** (12 Okt 2026) dan SPT 29 rekaman → **1.118 baris / 162 kode** (16 Okt 2026). Sisi SPT: 26 peristiwa (3 pasang dokumen kembar K38), **158 baris** "mulai disuspensi" (154 unik) + **960** "dipertahankan" (936 unik), seluruh dokumen kecuali dua cocok dengan angka yang disebut kalimatnya sendiri. **Sudah diimpor** ke basis data uji sebagai bagian langkah 3 | `.uji-data/riset-idx/rekonsiliasi-spt-per-kode-20261016.csv`, `ringkasan-suspensi-per-kode-20261016.csv`, `verdict-spt-20261016.json`, `docs/riset-suspensi-multi-kode-2026-10.md` |
| **Berkas impor suspensi per kode (K50/K51, langkah 3)** | **SELESAI 16 Okt 2026 (sesi 4)**: **171 baris / 159 kode** dari 162 kode — 138 terbuka · 33 tertutup penutup UPT · 65 episode bertanggal mulai proxy (penanda `TANGGAL_MULAI_TIDAK_DINYATAKAN_SUMBER_MANA_PUN`) · 4 penanda K47 · **34 baris 20 Feb 2024 ditahan** (K46). Pembuatnya skrip tanpa jaringan, **tanpa perubahan kode aplikasi**. Terukur: impor keluar 0 (**171 baru**), notasi 4.552 → 4.723, suspensi 1.926 → 2.097, `--saring` likuid **205 → 201** (KJEN, SINI, UNSP, ZATA) | `.uji-data/riset-idx/impor-suspensi-20261016/notasi-khusus.csv`, `.uji-data/riset-idx/buat-impor-suspensi.py`, `.uji-data/uji-impor-suspensi/` (`bukti-1` … `bukti-9`) |
| **Pelepasan penanda notasi (K51/K52)** | **SELESAI 16 Okt 2026 (sesi 5) — dijalankan atas basis data `.uji-data/mejasaham`.** Cadangan lebih dulu (`.uji-data/mejasaham-cadangan/20261016T165510578553+0700`), lalu berkas turunan basis data dibangun **tanpa penanda** (2.447 revisi terkini; 2.154 penanda dilepas), diimpor sebagai revisi baru (**2.447 baris baru**, keluar 0, snapshot 8), berkas `konfigurasi/notasi-khusus.csv` diganti dengan turunan itu, dan **`--saring` berbunyi "Kandidat teratas"** (likuid 201 · lolos saring 9). Basis datanya kini 7.170 baris notasi, **0 baris terkini berpenanda**; yang tetap tertanda di `keterangan`: 1 baris K46, 3 penanda K47, 65 episode bertanggal mulai tidak dinyatakan. **Catatan 16 Okt 2026 (sesi 6):** penanda K46 itu **sudah diputuskan dilepas (K53)** sesudah tinjauan visualnya dijalankan — pelaksanaannya **aksi #17** di bagian 4, sesi berikutnya | `.uji-data/uji-lepas-penanda/` (`bukti-0` … `bukti-7`), `.uji-data/riset-idx/buat-tanpa-penanda.py`, `.uji-data/riset-idx/tanpa-penanda-20261016/`, `.uji-data/uji-tinjauan-k46/` |
| **Pelaksanaan K53 + K54 (aksi #17)** | **SELESAI 16 Okt 2026 (sesi 7) — dijalankan atas basis data `.uji-data/mejasaham`, tanpa perubahan kode aplikasi.** Cadangan lebih dulu (`.uji-data/mejasaham-cadangan/20261016T172705653192+0700`) · berkas dibangun dari **revisi terkini basis data** (2.450 baris = 2.447 + 3) oleh `.uji-data/riset-idx/k53-k54/buat-k53-k54.py` · impor revisi baru (2450 baris, keluar 0) · `konfigurasi/notasi-khusus.csv` diperbarui (berkas lama = `notasi-khusus-sebelum-k53.csv`) · **`--saring` tetap "Kandidat teratas"** (likuid 201 · lolos saring 9). Terukur sesudahnya: **33 episode** memuat catatan pelepasan K46 (dengan rincian rekaman yang membuktikan penempelannya), **0 baris terkini** berpenanda `DITAHAN_K46_…`, **2 baris** berpenanda "di luar cakupan API"; **MTFN dua episode** (2023-10-30 → 2024-08-29 **tertutup** · 2025-06-30 terbuka), **ELTY** 2023-07-03 → 2023-10-19, **ARTI** 2021-11-30 → 2023-11-23. Notasi 7.170 → 9.654 baris. Aturan penempelan = **pemilik rekaman SPT tepat sebelumnya** (aturan "episode termuda" terbukti salah untuk `TECH`; keduanya dihitung dan selisihnya dilaporkan) | `.uji-data/riset-idx/k53-k54/` (`buat-k53-k54.py`, `keadaan-notasi.py`, `ukur-potong-keterangan.py`), `.uji-data/uji-k53-k54/` (`bukti-0` … `bukti-10`) |
| **Jendela (PySide6)** | **JALAN untuk membaca (aksi #10 tahap 1, T65) DAN untuk menulis (aksi #19 tahap 1 + aksi #19b/#19c/#19d, K59/T69/T70/T72/T73/T74)**: lima layar PRD 11 — dasbor 11.1 · screener 11.2 · detail emiten & tesis 11.3 · kalkulator risiko 11.4 · jurnal & kepatuhan 11.5. Tiap layar memanggil fungsi inti yang sama dengan baris perintah; pekerjaan berat di utas pekerja; kegagalan tampil di layar dan hasil lama dibuang. **Menulis**: `posisi.catat_transaksi` (11.3), `risiko.simpan_dari_kandidat` (11.4), `jurnal.catat` (11.5) lewat `mejasaham/ui/tulis.py` — konfirmasi di utas tampilan **sebelum** pekerja mulai (K59 d), penulisan di utas pekerja, layar dimuat ulang dari baris tersimpan sesudahnya, dan kunci tulis yang gagal berbunyi **"Jendela belum menulis apa pun"** (K59 a/b). **Sejak aksi #19b**: **impor berkas** dari menu Berkas (dua tahap: baca di utas pekerja → konfirmasi berisi **jumlah baris per tabel** → tulis dengan objek hasil bacaan yang sama), **"Pakai ukuran patuh"** di 11.4 (K63, lewat `risiko.pakai_ukuran_patuh` yang sama dengan `--pakai-ukuran-patuh`), dan **rencana/posisi dipilih dari daftar** di 11.3–11.4 (K64/T71 a; jendela tidak pernah memilih entri pertama). **GC siklik dimatikan selama tugas pekerja berjalan dan selama jalur tunggu penutupan (T68)** — penangkal cacat PySide6 6.12 + CPython 3.14 yang membuat uji jendela mati secara native tanpa traceback. **Sejak aksi #19c**: **cadangan basis data** dari menu Berkas (konfirmasi menyebut **folder tujuannya**, K59 d) dan **daftar cadangan** dengan baris yang sama dengan `--daftar-cadangan`; `PermintaanTulis` kini juga menyatakan `pertanyaan` dan `muat_ulang`, dan cadangan memakai `muat_ulang=False` (ia tidak mengubah baris apa pun — terukur 54,46 → 3,34 dtk). **Sejak aksi #19d (T74)**: **"Ubah stop" di 11.1** (posisi dipilih dari daftar posisi aktif; `tgl_stop` = tanggal yang dinyatakan pengguna dan muncul apa adanya di konfirmasi) dan **keputusan right issue di 11.3** (tabel hak `kode · posisi · tanggal aksi · rasio · tebus · tenggat · hak · keputusan` + formulir `tebus`/`jual_hmetd`/`abaikan`; isian yang tidak dipakai pilihan aktif dimatikan **dan** dikosongkan; kotak `tebus` hanya berisi transaksi **beli** posisi yang barisnya dipilih). `tebus` tetap hanya **menunjuk** transaksi yang sudah tercatat (T51 — jendela tidak mencatatkannya diam-diam), dan pesan tindakan menunggu di dasbor berhenti menyuruh pindah ke baris perintah. **Yang tetap di baris perintah: `--pulihkan`** (K59 e, K64 — batas yang ditetapkan, bukan pekerjaan tertunda) | `mejasaham/ui/jendela.py`, `mejasaham/ui/tulis.py`, `mejasaham/ui/tabel.py`, `mejasaham/ui/pekerja.py`, `mejasaham/cadangan.py`, `tests/test_ui_tabel.py` (10), `tests/test_ui_jendela.py` (41), `tests/test_ui_tulis.py` (25), `.uji-data/uji-jendela/jendela/` (`bukti-1` … `bukti-8` + 5 tangkapan layar), `.uji-data/uji-tulis-jendela/bukti/bukti-tulis-jendela.txt`, `.uji-data/uji-impor-jendela/bukti/bukti-impor-jendela.txt`, `.uji-data/uji-cadangan-jendela/bukti/` (bukti + 4 tangkapan layar) |
| **Transaksi & posisi (F11)** | **JALAN** (Tahap 2 langkah 3): `--catat-transaksi`, `--posisi`, `--posisi-semua`, `--ubah-stop`. `posisi` **tidak** menyimpan lembar/harga rata-rata (turunan transaksi, T43); pelanggaran **V1/V2/V5/V6** dideteksi & disimpan di barisnya (T44); biaya dihitung dari tarif *all-in* tanpa menambah PPh dua kali (K23) atau dicatat pengguna, dan `NULL` bila tidak dapat diketahui. Terukur atas data nyata: beli TLKM 10.800 lbr @2.320 dari rencana #1, stop dari rencana, biaya Rp 43.200, jual 5.000 lbr → hasil terealisasi Rp 150.000 | `mejasaham/posisi.py`, migrasi 012, `tests/test_posisi.py` (57 uji), `.uji-data/uji-posisi/` |
| **Risiko berjalan lengkap (AC-6)** | **JALAN**: risiko terbuka posisi aktif + rencana yang **belum** punya transaksi; rencana yang sudah dieksekusi tidak dihitung dua kali (T45). Terukur: Rp 1.512.000 (posisi TLKM) + Rp 159.600 (rencana ASII) = **Rp 1.671.600** | `mejasaham/risiko.py` (`risiko_berjalan_lengkap`), `.uji-data/uji-posisi/bukti-4-rencana-setelah-posisi.txt` |
| **Drawdown terkoreksi arus dana (AC-13)** | **JALAN**: `--ekuitas-harian --arus-dana` + `--drawdown`. Deret indeks, jadi setoran/penarikan tidak terbaca sebagai hasil; deret yang arus dananya belum dicatat **tidak** dikoreksi dan sebabnya disebut (T46). Ekuitasnya sendiri masih **dicatat pengguna** (lihat P25) | `mejasaham/risiko.py` (`drawdown`), `.uji-data/uji-posisi/bukti-11-drawdown.txt` |
| **Dasbor harian & "tindakan menunggu" (P16)** | **JALAN**: `--dasbor` = keadaan snapshot (termasuk peringatan basi AC-8), **konteks pasar (IHSG + perubahannya, breadth, rezim) sejak aksi #20/K58/T66** — dihitung lewat fungsi yang **sama** dengan `--saring`, jadi dua layar tidak bisa berbeda pada snapshot yang sama — watchlist, posisi (lembar, rata-rata, stop, dividen), risiko + batasnya, ekuitas & drawdown **+ pembanding `nilai posisi + kas` beserta selisihnya (K30)**, kandidat dari skor tersimpan, dan daftar tindakan (`stop_tertembus`, `pembatal_terpicu`, `tanpa_stop`, `tesis_kedaluwarsa`, `right_issue_belum_diputuskan`). **Harga yang dibayar dan disebut apa adanya:** karena jalurnya sama dengan saringan, `--dasbor` dulu membayar potret + seluruh metrik + breadth — **2,8 dtk → 33–61 dtk** pada basis data 999.421 bar (angka `--saring` tidak berubah; rincian di `.uji-data/uji-dasbor/bukti/bukti-keadaan.txt`). **Sejak sesi 34 (K61/T80)** angkanya **dibaca dari `konteks_pasar`** yang ditulis `--saring` bila snapshot + preset + label sumber harga + versi hitung masih sama — terukur **18,95 → 0,74 dtk (25,7×)** pada salinan data kerja; dasbor **pertama** sesudah `--refresh` masih membayar hitung ulang sampai `--saring` snapshot itu dijalankan (disengaja: menghitung ulang selalu benar) | `mejasaham/dasbor.py`, `tests/test_dasbor.py` (31 uji), `.uji-data/uji-dasbor/bukti/` (`bukti-0` … `bukti-4` + `bukti-keadaan.txt`), `.uji-data/uji-aksi-korporasi/bukti-16-dasbor-dengan-pembanding-ekuitas.txt` |
| **Aksi korporasi pada posisi (K28)** | **JALAN** (Tahap 2 langkah 4): split/reverse split menyesuaikan **lembar, harga rata-rata, stop, dan risiko** (diturunkan saat dibaca, `tgl_stop` menyimpan basisnya); dividen dihitung per peristiwa dan masuk hasil sebagai suku terpisah (bruto, tanpa pajak); right issue memunculkan hak + tenggat + keputusan manual (`--hak-right-issue`, `--putuskan-right-issue`; sejak aksi #19d keputusannya juga dari layar 11.3 — T74, dan haknya tetap **petunjuk**). Terukur atas data nyata: MLPT pra-split 1.000 lbr @18.750 (stop 17.000) → **25.000 lbr, rata-rata Rp 750, stop Rp 680, risiko Rp 5.875.000**; BBCA → dividen Rp 45.000 bruto | `mejasaham/posisi.py`, `mejasaham/dasbor.py`, migrasi 013, `tests/test_aksi_korporasi_posisi.py` (39 uji), `.uji-data/uji-aksi-korporasi/` |
| Transaksi, posisi, jurnal, ekspor, cadangan | **F11, F7, F9, F12 jalan**; cadangan menggunakan `VACUUM INTO`, mencakup konfigurasi + arsip snapshot, retensi 14, pulih dari salinan bersih; otomatis sesudah refresh sukses dan sebelum migrasi | `mejasaham/cadangan.py`, `docs/arsitektur.md` T56–T57 |
| **Jurnal keputusan & rekap kepatuhan (F7)** | **JALAN** (Tahap 3 langkah 1): `--jurnal`, `--rekap-kepatuhan`, `--jurnal-catat`. Seluruh katalog PRD 9.8 (V1–V7) kini dihitung — V1/V2/V6 dibaca dari baris `transaksi`, V5 dari baris `posisi`, V3/V4/V7 diturunkan; **tidak ada kode yang dihitung dua kali** (T44/T52). Terukur atas data nyata di `.uji-data/uji-jurnal`: 6 keputusan · patuh 1 (16,67%) · 7 pelanggaran, termasuk **V3 rencana #2 ASII** (5,44% > 5,00%) yang di Tahap 2 hanya tersimpan sebagai kalimat. Expectancy berbunyi "belum dapat dinilai (0 dari 30 putaran tertutup)", drawdown terkoreksi 0,39% | `mejasaham/jurnal.py`, migrasi 014, `tests/test_jurnal.py` (41 uji), `.uji-data/uji-jurnal/` |
| **Ekspor laporan (F9)** | **JALAN** (Tahap 3 langkah 2): `--ekspor hasil-saring|watchlist|rencana|jurnal|mutu --keluaran berkas.csv`; UTF-8 BOM, `;`, kepala `id_snapshot` + ID/versi preset + sumber harga + disclaimer. Laporan mutu harus tersedia pada arsip snapshot yang sama; berkas tujuan yang sudah ada ditolak | `mejasaham/ekspor.py`, `tests/test_ekspor.py` (8 uji), `docs/arsitektur.md` T56 |
| **Cadangan/pemulihan (F12)** | **JALAN** (Tahap 3 langkah 3): `--buat-cadangan`, `--daftar-cadangan`, `--pulihkan FOLDER`; `--folder-cadangan` untuk lokasi pilihan. Cakupan basis data + konfigurasi + arsip snapshot; validasi SQLite sebelum pulih; otomatis sesudah refresh sukses dan sebelum migrasi; retensi 14; default di luar folder data. **Sejak aksi #19c (T73): cadangan dan daftar cadangan juga dari menu Berkas jendela** (konfirmasi menyebut folder tujuan; daftar memakai teks `cadangan.ringkas_daftar` yang sama dengan `--daftar-cadangan`), sedangkan **pemulihan tetap hanya baris perintah** (K59 e) | `mejasaham/cadangan.py`, `tests/test_cadangan.py`, `docs/arsitektur.md` T57/T73 |

### 2.1 Jawaban pengguna sudah masuk (10 Okt 2026) — **seluruhnya sudah dikerjakan**

**Tidak ada lagi pertanyaan yang menunggu.** Empat jawaban (→ **K20, K21** di `docs/keputusan.md`
bagian 1, konteksnya di bagian 3.6) sudah masuk, dan **dua di antaranya selesai 10 Okt 2026**
(Tahap 1 langkah 13):

| Jawaban | Artinya untuk kerja berikutnya |
|---|---|
| Broker: **Stockbit** | **SELESAI 10 Okt 2026.** Tarif resminya **0,15% beli / 0,25% jual, all-in**, badan sekuritasnya **PT Stockbit Sekuritas Digital**. Yang dulu menghalangi — **minimum** dan **tanggal berlaku** tidak dinyatakan sumbernya — kini punya bentuknya sendiri lewat **K22**, dan bahaya hitung-dua-kali ditutup **K23**. `--muat-konfigurasi` menandainya `dipakai`, bukan lagi `belum_terverifikasi` |
| Slippage: **`tick`** | **SELESAI 10 Okt 2026.** B9 = satu tick memakai tabel fraksi B2, tersimpan bertanggal (tanggal keputusan + penanda asal) supaya bisa diganti tanpa menghapus yang lama |
| `jenis` emiten: **boleh diturunkan dari data** | **SELESAI 10 Okt 2026.** Hanya **`bank_keuangan`** yang diturunkan (dari `sector`/`industry` sumber) dan label sumbernya ikut tersimpan; `siklikal_komoditas` **tidak pernah** diturunkan. Terukur: 49 bank dari 916 emiten. Efeknya sudah tampak di `--saring`: kriteria bank PRD 8.4 kini berlaku untuk 49 emiten itu, dan DER/coverage/CFO-NI berhenti dihitung untuk mereka |
| `notasi-khusus.csv` & `rasio-bank.csv`: **tidak ada — carikan** | **BELUM.** Ini pekerjaan **aplikasi**, bukan pekerjaan manusia, dan sekarang menjadi **satu-satunya aksi besar yang tersisa** di Tahap 1. Mulai dari jalur yang **belum** diuji, jangan ulangi yang sudah mati (daftarnya di butir berikut) |

**P22 — mencari dua berkas itu, tanpa mengulang jalan buntu.** Sudah terbukti **mati** (9 Okt 2026,
7 jalur): `www.idx.co.id` + `www2.idx.co.id` (403 Cloudflare), endpoint JSON (`/primary/...`,
`/umbraco/...`), PDF resmi (`/Media/*.pdf`, `/StaticData/*.pdf`), varian `http://`, `r.jina.ai`
(kena challenge di sisinya sendiri), dan empat proxy CORS publik (522/403/429/000).

**Terobosan 10 Okt 2026 — jalur (a) "peramban sungguhan" TERBUKTI SEBAGIAN, dan batasnya kini
terukur:**

* **Chromium sungguhan menembus Cloudflare**: `https://www.idx.co.id/id` → **HTTP 200**, judul
  "PT Bursa Efek Indonesia", 44 tautan terbaca, cookie `cf_clearance` diterbitkan. Ini jalur yang
  selama ini tidak ada, dan ia memang bekerja.
* **`requests` Python tetap 403** walaupun membawa **seluruh** cookie itu (termasuk
  `cf_clearance`) dengan User-Agent yang sama. Jadi menyalin cookie bukan jalan pintas: aplikasi
  (**`requests`**, tanpa dependensi baru) **tidak bisa** mengambil IDX apa adanya.
* **Burst langsung diblokir, dan bloknya bertahan lama.** Navigasi cepat (beberapa halaman
  berturut-turut) memicu halaman **"Sorry, you have been blocked"** — bukan tantangan, melainkan
  blok. Jeda 75 detik + mundur 120 detik **tidak cukup**: blok bertahan >15 menit, dan tetap
  menolak setelahnya. `peramban` dijalankan dengan profil tetap (`.tmp/idx-profil`) supaya
  `cf_clearance` tersimpan antar-jalan; itu memperbaiki permintaan **pertama**, bukan bloknya.
* **`www2.idx.co.id`** (halaman resmi *Special Notation*) tetap 403 **sekalipun dengan peramban** —
  jalur `www2` tampaknya diblok lebih keras daripada `www`.
* Yang **belum** dicoba dan masih layak: **satu** permintaan per sesi peramban, dijalankan dari
  **jaringan lain** (temuan ini tentang jaringan mesin ini, bukan tentang IDX), atau menunggu blok
  itu benar-benar kedaluwarsa (jam, bukan menit).

Yang **belum** diuji dan layak dicoba lebih dulu: **(b)** sumber pihak ketiga yang memuat laporan
keuangan emiten IDX lengkap dengan NPL/CAR/BOPO/NIM; **(c)** daftar papan pemantauan khusus/suspensi
yang diterbitkan ulang sekuritas atau aggregator (satu contoh nyata muncul di penelusuran 10 Okt 2026:
`webcrp.bcasekuritas.co.id` menerbitkan ulang pengumuman "Pemantauan Khusus" IDX dalam bentuk PDF —
sekunder, jadi belum boleh jadi sumber produksi, tetapi berguna sebagai pembanding isi). Kalau
ketiganya gagal, hasilnya dilaporkan apa adanya — keadaan "notasi belum ada" sudah punya tempatnya
sendiri di keluaran aplikasi.

**Yang TIDAK menunggu apa pun** (jangan berhenti karena ini): kalender 2021–2024, `.exe`
(Tahap 5 — **sudah dibangun sesi 35, T81**), dan seluruh Tahap 2 yang tidak menyentuh
lot/tick/biaya — jurnal, kandidat, rencana, posisi, panel jendela bisa dikerjakan sekarang,
dengan bagian yang bergantung B1–B9 menolak menghitung.

---

## 3. Jalankan dulu ini, sebelum percaya apa pun

> **Sejak 17 Okt 2026 folder sandbox uji sudah dikosongkan** (pembersihan ruang, permintaan
> pengguna): salinan `mejasaham.db` **dan** ekspor `arsip-snapshot/` di dalam **semua**
> `.uji-data/uji-*` beserta folder `*-cadangan/`-nya **sudah dihapus**. Berkas buktinya
> (`bukti*`, `*.txt`, `*.md`, `*.png`, `konfigurasi/`) **tetap utuh**, jadi angka yang dikutip
> dokumen masih bisa diperiksa — tetapi **datanya tidak ada lagi**. Konsekuensi yang mengikat:
> perintah di bagian ini yang menunjuk `.uji-data/uji-<nama>` akan membuat basis data **kosong**
> dan hasilnya tampak "berhasil" padahal salah. Bangun ulang sandboxnya lebih dulu:
> `Copy-Item -Recurse .uji-data\mejasaham .uji-data\uji-<nama>` (pakai `.uji-data\mejasaham.db`
> bila butuh basis data bersih tanpa arsip). Yang **tidak** terpengaruh: `.uji-data/mejasaham`
> (basis data kerja, 999.512 bar), `.uji-data/mejasaham.db`, `.uji-data/riset-idx/`,
> `.uji-data/mejasaham-cadangan/20261016T175015415236+0700`, dan
> `.uji-data/arsip-snapshot/2026-10-09/{snapshot-1,snapshot-4}` — dengan satu catatan jujur:
> `snapshot-1` ternyata **sudah kosong (0 berkas)** sejak sebelum pembersihan ini, padahal
> `docs/keputusan.md` mengutip `snapshot-1/emiten.csv`; yang utuh dan bisa diperiksa adalah
> **`snapshot-4`** (`harga.csv` 146,7 MB + `emiten.csv` + `aksi-korporasi.csv`).
>
> **Dua cadangan yang dulu dikutip sebagai bukti kini TIDAK ADA lagi** (ikut dihapus dalam
> pembersihan yang sama): `mejasaham-cadangan/20261016T165510578553+0700` (K52) dan
> `…/20261016T172705653192+0700` (K53). Catatan peristiwanya tetap lengkap di
> `docs/keputusan.md`; yang hilang hanya salinan basis datanya.

```powershell
# Wajib: seluruh uji harus lulus sebelum klaim apa pun. Saat ini: **908 uji** (terukur 19 Okt 2026
# sesudah Tahap 5/sesi 35: `908 passed in 38,12s`; 906 sesi 34, 887 sesi 29–33, 885 sesudah #27,
# 882 di sesi 20–26, 879 di sesi 19, 849 di sesi 12, 833 sebelum #19b).
# PENTING (terukur 10 Okt 2026, Tahap 3): folder sementara yang **sudah ada** bisa rusak ACL-nya
# dan membuat 483 uji gagal di tahap setup tanpa satu pun perubahan kode — pakai folder BARU
# (`.tmp\t<N>` yang belum pernah dipakai), bukan `.tmp\pytest-temp`. Lihat bagian 6.
# Di sesi agen, arahkan folder sementara ke dalam repo lebih dulu (lihat 6):
$env:TEMP = "$PWD\.tmp\t30"; $env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
.\.venv\Scripts\python -m pytest

# Bangun bundel aplikasi (Tahap 5; T81). Hasil: dist\MejaSaham\MejaSaham.exe + _internal\
.\.venv\Scripts\python -m pip install -r requirements-build.txt
.\.venv\Scripts\python tools\build_exe.py
# Verifikasi cepat tanpa menyentuh data kerja:
.\dist\MejaSaham\MejaSaham.exe --help
.\dist\MejaSaham\MejaSaham.exe --muat-konfigurasi --folder-data .tmp\data-bersih

# Konteks pasar di dasbor (aksi #20, K58/T66; sejak sesi 34/T80 dibaca dari `konteks_pasar`):
# jalankan `--saring` lebih dulu, lalu `--dasbor` pada folder yang sama harus berbunyi SAMA —
# `--saring` menulis snapshot + preset + label sumber + versi hitung, dan dasbor hanya memakai
# simpanan bila keempatnya cocok (kalau tidak, ia menghitung ulang dan membayar beban saringan).
.\.venv\Scripts\python -m mejasaham --saring --teratas 5 --folder-data .uji-data/uji-dasbor
.\.venv\Scripts\python -m mejasaham --dasbor --teratas 5 --folder-data .uji-data/uji-dasbor
#   Bukti: .uji-data\uji-dasbor\bukti\ (bukti-0 kode lama · bukti-1 saring · bukti-2 dasbor ·
#   bukti-3 pytest · bukti-4 contoh proses yang mati · bukti-keadaan.txt)

# Kerangka rasio bank (aksi #21, K57/T67) — butuh `jenis` sudah terisi. Basis data uji yang siap:
# .uji-data/uji-jenis (49 bank_keuangan hasil K21). Perintahnya menulis BERKAS, bukan basis data.
.\.venv\Scripts\python -m mejasaham --kerangka-rasio-bank --folder-data .uji-data/uji-jenis
#   -> 49 baris, seluruh angka & tanggal kosong; berkas yang sudah berisi DITOLAK (tidak ditimpa)
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\uji-jenis\konfigurasi" --folder-data .uji-data/uji-jenis
#   -> keluar 1: "rasio-bank.csv baris 36: kolom `periode` wajib diisi" (bukan masuk sebagai nol)
#   Bukti: .uji-data\uji-kerangka-rasio-bank\bukti\ (bukti-1 … bukti-5 + bukti-keadaan.txt)

# Muat parameter bursa (K22/K23). Harus berbunyi `biaya_broker [Stockbit …] dipakai` dan
# `slippage dipakai`, keluar 0, dan TIDAK ada satu pun angka yang tidak dinyatakan sumbernya:
# `minimum` tersimpan NULL (bukan 0), `berlaku_sejak` bertanda `tanggal_pengamatan`.
.\.venv\Scripts\python -m mejasaham --muat-konfigurasi --folder-data .uji-data
#   Bukti sebelum/sesudah: .uji-data\bukti-muat-konfigurasi-sebelum.txt vs …-sesudah.txt

# Turunkan `jenis` emiten dari sector/industry sumber data (K21) — JARINGAN, ±6 menit untuk
# 916 emiten (satu permintaan per emiten, berjeda). Menulis emiten.csv; TIDAK menulis basis data.
#   Butuh --timpa-jenis bila emiten.csv sudah ada dan sudah berisi.
.\.venv\Scripts\python -m mejasaham --ambil-jenis --timpa-jenis --folder-data .uji-data
# lalu masukkan ke basis data (penulisan basis data tetap satu jalur):
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\konfigurasi" --folder-data .uji-data
#   Hasil terukur 10 Okt 2026 (folder buktinya .uji-data\uji-jenis\): 49 bank_keuangan (BBRI,
#   BMRI, BBCA, BBNI, …) · 862 umum · 5 kosong. `--saring` lalu berbunyi
#   "jenis emiten: 49 bank_keuangan (dari data) · 862 umum (dari data) · … · 5 belum terisi".

# Ambil kalender libur bursa dari pengumuman KSEI (jaringan; menimpa berkas yang sudah ada)
.\.venv\Scripts\python -m mejasaham --ambil-kalender --timpa-kalender --folder-data .uji-data

# Ambil kurva imbal hasil SBN dari halaman HPW PHEI -> imbal-hasil-sun.csv (K16).
# Menambah satu baris; baris lain di berkas itu tidak ditimpa.
.\.venv\Scripts\python -m mejasaham --ambil-sun --folder-data .uji-data/uji-sun
# lalu masukkan ke basis data (penulisan basis data tetap satu jalur):
.\.venv\Scripts\python -m mejasaham --impor .uji-data\uji-sun\konfigurasi --folder-data .uji-data/uji-p17

# Lihat keadaan aplikasi atas data nyata yang sudah ada di folder uji:
.\.venv\Scripts\python -m mejasaham --saring --teratas 20 --folder-data .uji-data

# Cacat P17: bukti harga pembanding tidak lagi merusak angka. Folder ini basis data yang sama
# dengan bukti langkah 6 (999.421 bar utama + 21 bar pembanding). Harus berbunyi likuid 235,
# bukan 215, dan menyebut label mana yang dipakai.
.\.venv\Scripts\python -m mejasaham --saring --teratas 5 --folder-data .uji-data/uji-p17

# Menimpa pilihan label sumber (kalau labelnya salah, angkanya harus ikut berubah — bukan diam)
.\.venv\Scripts\python -m mejasaham --saring --sumber "pembanding-uji" --folder-data .uji-data/uji-p17

# Cadence cek sumber kedua (PRD 7.3) — juga mencetak "cek berikutnya paling lambat":
.\.venv\Scripts\python -m mejasaham --cek-sumber-kedua --folder-data .uji-data

# Kolom `tanggal_notasi` (langkah 7) tanpa jaringan — enam baris contoh dari bukti nyata:
Get-Content .uji-data\uji-tanggal-notasi\konfigurasi\emiten.csv |
  Select-String -Pattern '^(BBCA|GOTO|ANTM|BBRI|AALI);'

# Hasil turunan `jenis` (langkah 13) tanpa jaringan — folder salinannya sudah terisi:
.\.venv\Scripts\python -m mejasaham --saring --teratas 3 --folder-data .uji-data/uji-jenis
Get-Content .uji-data\uji-jenis\konfigurasi\emiten.csv |
  Select-String -Pattern '^(BBRI|BMRI|BBCA|BBNI|ANTM|TLKM);'

# --- Tahap 2: kandidat (langkah 1) dan kalkulator risiko (langkah 2), tanpa jaringan ---------
# Folder buktinya salinan bersih `.uji-data/mejasaham.db`; jangan pakai `.uji-data` langsung
# kalau tidak ingin menambah baris ke basis data utama.
.\.venv\Scripts\python -m mejasaham --batas-risiko-bawaan --folder-data .uji-data/uji-risiko
#   -> risiko-bawaan/v1: 0,75% · 10% · 30% · 2% ADTV20 · 5%; muat ulang TIDAK menambah baris
.\.venv\Scripts\python -m mejasaham --ekuitas-harian 250000000 --kas 120000000 --folder-data .uji-data/uji-risiko
# lalu kalkulatornya (kandidatnya harus berstatus watchlist lebih dulu):
.\.venv\Scripts\python -m mejasaham --hitung-risiko TLKM --jenis-stop order_sekuritas --folder-data .uji-data/uji-risiko
#   -> terukur 10 Okt 2026: stop 2.180 (2 × ATR14 = Rp 132,37 → 2187,6 dibulatkan KE BAWAH),
#      biaya+slippage Rp 14/lembar, ukuran mentah 12.224 → 10.800 lembar (batas bobot 10%),
#      risiko nominal Rp 1.663.200 (0,66% ekuitas), batas sektor "tidak dinilai" (P24)
.\.venv\Scripts\python -m mejasaham --rencana --folder-data .uji-data/uji-risiko
#   -> dua rencana tersimpan beserta revisinya; risiko berjalan = jumlah rencana belum dieksekusi

# --- Notasi khusus dari halaman resmi IDX (K27/P22) — JARINGAN, satu permintaan ---------------
# Domainnya `www.idx.id`, BUKAN `www.idx.co.id` (yang itu tetap 403). Butuh UA yang menyebut
# dirinya; modul ini memakainya sendiri, jadi tidak ada yang perlu diatur.
.\.venv\Scripts\python -m mejasaham --ambil-notasi --folder-data .uji-data/uji-sektor
#   -> 122 baris, 68 emiten papan pemantauan khusus, data per 08 Okt 2026; ulang = 0 baru/0 ditutup
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\uji-sektor\konfigurasi" --folder-data .uji-data/uji-sektor
.\.venv\Scripts\python -m mejasaham --saring --teratas 5 --folder-data .uji-data/uji-sektor
#   -> BERHENTI berbunyi "PERINGKAT SEMENTARA": kini "Kandidat teratas", likuid 227

# --- Tahap 2 langkah 3: transaksi, posisi, ekuitas & dasbor (F11) — tanpa jaringan -------------
# Folder buktinya salinan `.uji-data/uji-sektor` (999.421 bar, 10 snapshot, rencana #1 TLKM &
# #2 ASII sudah ada). JANGAN pakai `.uji-data` langsung kalau tidak ingin menambah posisi ke
# basis data utama. Migrasi 012 terpasang sendiri saat perintah pertama dijalankan (11 -> 12).
# Catatan: `.uji-data/uji-posisi` **sudah berisi** hasil jalan sesi 10 Okt 2026, jadi menjalankan
# blok ini lagi akan MENAMBAH posisi/transaksi di atasnya (dan `--id-rencana 1` yang sama akan
# memicu pelanggaran V2 karena lembarnya melebihi rencana). Untuk mulai bersih, salin dulu:
#   Copy-Item -Recurse .uji-data\uji-sektor .uji-data\uji-posisi-baru
.\.venv\Scripts\python -m mejasaham --rencana --folder-data .uji-data/uji-posisi
#   -> risiko berjalan = posisi aktif + rencana belum dieksekusi, dan rencana yang sudah
#      dieksekusi tidak dihitung dua kali (AC-6)
# Catat eksekusi manual: menuntut --aksi, --lembar, --harga, dan --mode (PRD 9.11)
.\.venv\Scripts\python -m mejasaham --catat-transaksi TLKM --aksi beli --lembar 10800 `
    --harga 2320 --mode nyata --id-rencana 1 --tanggal 2026-10-10 --folder-data .uji-data/uji-posisi
#   -> terukur: biaya Rp 43.200 (0,15% all-in dihitung sendiri, asalnya ditandai),
#      stop posisi diambil dari rencana #1 (Rp 2.180), 0 pelanggaran
.\.venv\Scripts\python -m mejasaham --posisi --folder-data .uji-data/uji-posisi
#   -> risiko terbuka (2.320 - 2.180) x 10.800 = Rp 1.512.000; belum terealisasi Rp -43.200
# Stop boleh dinaikkan (trailing). Menurunkannya TETAP BOLEH, tetapi tercatat sebagai V5:
.\.venv\Scripts\python -m mejasaham --ubah-stop --id-posisi 1 --stop 2100 `
    --alasan "menurunkan stop" --folder-data .uji-data/uji-posisi
# Jual sebagian -> hasil terealisasi (setelah biaya kedua sisi):
.\.venv\Scripts\python -m mejasaham --catat-transaksi TLKM --aksi jual --lembar 5000 `
    --harga 2360 --mode nyata --tanggal 2026-10-16 --folder-data .uji-data/uji-posisi
.\.venv\Scripts\python -m mejasaham --posisi-semua --folder-data .uji-data/uji-posisi
#   -> terukur: terealisasi Rp 150.000 dari 5.000 lembar, sisanya 5.800 lembar masih terbuka
# Ekuitas + arus dana (AC-13) dan drawdownnya:
.\.venv\Scripts\python -m mejasaham --ekuitas-harian 260000000 --kas 150000000 `
    --arus-dana 10000000 --mode nyata --tanggal-ekuitas 2026-10-16 --folder-data .uji-data/uji-posisi
.\.venv\Scripts\python -m mejasaham --drawdown --folder-data .uji-data/uji-posisi
#   -> setoran tidak terbaca sebagai hasil; deret tanpa arus dana TIDAK dikoreksi (sebabnya tampil)
# Satu halaman harian + daftar tindakan menunggu (PRD 11.1, P16):
.\.venv\Scripts\python -m mejasaham --dasbor --teratas 5 --folder-data .uji-data/uji-posisi
#   -> terukur: `[stop_tertembus] ASII · posisi #2 — penutupan Rp 4.820 menembus stop Rp 4.830`
```

```powershell
# --- Tahap 2 langkah 4: aksi korporasi pada posisi (K28) — tanpa jaringan -----------------------
# Folder buktinya salinan `.uji-data/uji-posisi` (999.421 bar, 11 snapshot, rencana #1 TLKM &
# #2 ASII, posisi TLKM #1 & ASII #2 SUDAH ADA). Migrasi 013 terpasang sendiri saat perintah
# pertama. Isi folder itu sekarang: posisi MLPT #3 (split 1:25) dan BBCA #4 (dividen), tiga
# baris uji right issue di `konfigurasi/aksi-korporasi.csv`, dan 3 keputusan right issue.
# Untuk mulai bersih: Copy-Item -Recurse .uji-data\uji-posisi .uji-data\uji-ak-ulang

# AC-18 atas data nyata: MLPT dibeli 1 Jul 2026 (SEBELUM split 1:25 pada 21 Jul 2026)
.\.venv\Scripts\python -m mejasaham --catat-transaksi MLPT --aksi beli --lembar 1000 `
    --harga 18750 --mode nyata --tanggal 2026-07-01 --folder-data .uji-data/uji-aksi-korporasi
#   -> mencatat juga V1 (tanpa stop) & V6 (tanpa rencana); biaya TIDAK dihitung (tarif broker
#      belum berlaku pada 2026-07-01) — dan itu memang jawabannya, bukan nol
.\.venv\Scripts\python -m mejasaham --ubah-stop --id-posisi 3 --stop 17000 `
    --tanggal 2026-07-15 --folder-data .uji-data/uji-aksi-korporasi
#   -> `tgl_stop` = 2026-07-15: level stop dinyatakan dalam basis SEBELUM split
.\.venv\Scripts\python -m mejasaham --posisi --folder-data .uji-data/uji-aksi-korporasi
#   -> TERUKUR: `25.000 lbr (dari 1.000 lbr tercatat, disesuaikan split 1:25 pada 2026-07-21) ·
#      rata-rata Rp 750 · stop Rp 680 (disesuaikan dari Rp 17.000 …)`, risiko Rp 5.875.000
#      Sebelum langkah ini: 1.000 lbr dengan stop 17.000 DI ATAS penutupan 915 → dasbor berbunyi
#      "stop tertembus" yang tidak pernah terjadi

# Dividen: beli BBCA 29 Mei 2026, dua pembayaran jatuh selama masa pegang
.\.venv\Scripts\python -m mejasaham --catat-transaksi BBCA --aksi beli --lembar 1000 `
    --harga 5700 --mode nyata --tanggal 2026-05-29 --folder-data .uji-data/uji-aksi-korporasi
#   -> TERUKUR: `dividen diterima: Rp 45.000 dari 2 pembayaran` (17 Jun Rp 20/lembar ·
#      31 Agu Rp 25/lembar), bruto — pajaknya tidak dihitung aplikasi

# Right issue: TIDAK ada sumber otomatisnya (0 baris right_issue dari 2.141 baris aksi
# korporasi), jadi jalurnya diperiksa lewat baris uji di `konfigurasi/aksi-korporasi.csv`
# yang bertanda "BARIS UJI - bukan pengumuman resmi". Urutannya:
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\uji-aksi-korporasi\konfigurasi" --folder-data .uji-data/uji-aksi-korporasi
.\.venv\Scripts\python -m mejasaham --hak-right-issue --folder-data .uji-data/uji-aksi-korporasi
#   -> hak = rasio × lembar pada tanggal aksi; `tenggat BELUM DINYATAKAN sumbernya` untuk MLPT;
#      baris ASII TIDAK muncul (tanggalnya sebelum posisinya dibuka — memang bukan pemegang)
.\.venv\Scripts\python -m mejasaham --putuskan-right-issue BBCA --tanggal-aksi 2026-09-15 `
    --keputusan jual_hmetd --lembar 400 --harga 300 --biaya 500 --folder-data .uji-data/uji-aksi-korporasi
#   -> hasil Rp 119.500 (400 × 300 − 500); lembar posisi TIDAK berkurang (menjual hak ≠ menjual lembar)
.\.venv\Scripts\python -m mejasaham --putuskan-right-issue MLPT --tanggal-aksi 2026-09-20 `
    --keputusan tebus --folder-data .uji-data/uji-aksi-korporasi
#   -> DITOLAK (keluar 1) dengan pesan yang menyebut --catat-transaksi: lembarnya hanya punya
#      satu tempat. Catat dulu belinya, lalu ulangi dengan --id-transaksi N
.\.venv\Scripts\python -m mejasaham --catat-transaksi MLPT --aksi beli --lembar 6200 `
    --harga 400 --mode nyata --tanggal 2026-09-22 --id-posisi 3 --folder-data .uji-data/uji-aksi-korporasi
#   -> hak 6.250 lembar BUKAN kelipatan lot 100, jadi yang dicatat 6.200; pesan penolakannya
#      menyebut kelipatan terdekatnya (P26)
.\.venv\Scripts\python -m mejasaham --putuskan-right-issue MLPT --tanggal-aksi 2026-09-20 `
    --keputusan tebus --id-transaksi 6 --id-posisi 3 --folder-data .uji-data/uji-aksi-korporasi
#   -> keputusan #3 r1 menunjuk transaksi #6 (lembar posisi naik 25.000 -> 31.200)
.\.venv\Scripts\python -m mejasaham --dasbor --teratas 5 --folder-data .uji-data/uji-aksi-korporasi
#   -> TERUKUR: right issue masuk `TINDAKAN MENUNGGU`, dan yang tenggatnya sudah lewat pindah ke
#      CATATAN ("1 right issue tanpa keputusan yang tenggatnya sudah lewat")
```

# --- Tahap 3 langkah 1: jurnal & rekap kepatuhan (F7) — tanpa jaringan -------------------------
# Folder buktinya salinan `.uji-data/uji-aksi-korporasi` (6 transaksi, 4 posisi, rencana #1 TLKM &
# #2 ASII, migrasi 014 terpasang saat perintah pertama). Seluruh buktinya sudah ada di
# `.uji-data/uji-jurnal/` (bukti-1 … bukti-10 + bukti-keadaan.txt).
.\.venv\Scripts\python -m mejasaham --jurnal --folder-data .uji-data/uji-jurnal
#   -> TERUKUR: 6 keputusan · patuh 1 (16,67%) · 7 pelanggaran (V1 2×, V6 3×, V3 1×, V5 1×)
.\.venv\Scripts\python -m mejasaham --rekap-kepatuhan --folder-data .uji-data/uji-jurnal
#   -> V3 ASII: `total risiko: 5,44% melebihi batas 5,00%`; expectancy "BELUM DAPAT DINILAI:
#      0 dari 30 putaran tertutup"; drawdown 0,39% terkoreksi arus dana; rekap per bulan
.\.venv\Scripts\python -m mejasaham --rekap-kepatuhan --bulan 2026-10 --folder-data .uji-data/uji-jurnal
#   -> 3 keputusan bulan itu (2 pelanggaran); pelanggaran bulan lain pindah ke "di luar periode"
# Menulis catatan jurnal: menambah REVISI, tidak menimpa (PRD 9.8)
.\.venv\Scripts\python -m mejasaham --jurnal-catat 3 --alasan "pelanggaran diterima secara sadar" `
    --pelajaran "periksa total risiko sebelum menyimpan rencana" --tandai-selesai `
    --tanggal 2026-10-17 --folder-data .uji-data/uji-jurnal
#   -> `jurnal #1 r2 …` + `Revisi r1 disimpan, bukan ditimpa`
.\.venv\Scripts\python -m mejasaham --jurnal --kode ASII --folder-data .uji-data/uji-jurnal
#   -> catatan tampil di baris keputusannya, berdampingan dengan pelanggaran V3-nya
```

```powershell
# --- Rekonsiliasi suspensi multi-kode per kode (K37) — tanpa jaringan, TANPA basis data ---------
# Langkah 1 rencana K36–K41. Sisi UPT 41 baris (12 Okt 2026), sisi SPT 1.118 baris / 162 kode
# (16 Okt 2026). Tidak ada impor: berkas-berkas ini bahan tinjauan, bukan data yang sudah masuk.
Get-Content .uji-data\riset-idx\rekonsiliasi-spt-per-kode-20261016.txt        # ringkasan + temuan
Get-Content .uji-data\riset-idx\ringkasan-suspensi-per-kode-20261016.csv |   # 162 kode
  Select-String -Pattern '^(kode|AKKU|XSBC|MTFN|ASMI);'
Get-Content .uji-data\riset-idx\rekonsiliasi-spt-per-kode-20261016.csv |
  Select-String -Pattern ';mulai_disuspensi;' | Select-Object -First 5        # 154 baris "mulai"
#   -> sisi SPT: 29 rekaman = 26 peristiwa; 158 baris "mulai disuspensi" (154 unik) + 960
#      "dipertahankan" (936 unik) = 1.118 baris, 1.090 peristiwa unik; pemeriksa silang API
#      berkode tunggal + rekonsiliasi UPT 12 Okt 2026
Get-Content .uji-data\riset-idx\rekonsiliasi-upt-per-kode-20261012.csv -TotalCount 3   # sisi UPT
```

```powershell
# --- Langkah 3 K36–K41: berkas impor per kode + muat ke basis data UJI — tanpa jaringan ----------
# 171 baris / 159 kode (138 terbuka · 33 tertutup · 65 proxy · 4 penanda K47), 34 baris 20 Feb 2024
# ditahan (K46). TIDAK ada perubahan kode aplikasi; impornya hanya ke SALINAN basis data.
# 1) Hasilkan ulang berkasnya dari tiga berkas rekonsiliasi (tidak menyentuh basis data):
.\.venv\Scripts\python .uji-data\riset-idx\buat-impor-suspensi.py
#   -> .uji-data\riset-idx\impor-suspensi-20261016\notasi-khusus.csv (+ bukti-keadaan.txt)
# 2) Siapkan salinan basis data uji (jangan pakai .uji-data/mejasaham langsung):
$t = ".uji-data\uji-impor-ulang"; New-Item -ItemType Directory -Force -Path $t | Out-Null
Copy-Item .uji-data\mejasaham\mejasaham.db "$t\mejasaham.db"
Copy-Item -Recurse .uji-data\mejasaham\konfigurasi "$t\konfigurasi"
# 3) Muat, lalu periksa: likuid harus TURUN 205 -> 201 (KJEN, SINI, UNSP, ZATA tersuspensi)
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\riset-idx\impor-suspensi-20261016" --folder-data $t
.\.venv\Scripts\python -m mejasaham --saring --teratas 5 --folder-data $t
#   -> masih "PERINGKAT SEMENTARA" (penandanya belum dilepas, K37) tetapi likuid 201
# Bukti hasil sesi 16 Okt 2026 ada di .uji-data\uji-impor-suspensi\ (bukti-1 … bukti-9)
```

```powershell
# --- Langkah 4 (SUDAH DIJALANKAN 16 Okt 2026, sesi 5): lepas penanda kekurangan notasi — tanpa jaringan
# K51: JANGAN menyunting konfigurasi\notasi-khusus.csv sebagai jalan melepas penanda — yang benar
# adalah membangun berkas dari REVISI TERKINI BASIS DATA, karena impor hanya menambah revisi dan
# tidak menyinkronkan. (Koreksi bagian 6: berkas yang "hanya 122 baris" itu berkas lain.)
# Perintahnya, persis seperti yang dijalankan, berurutan:
# 1) cadangkan dulu (F12) — langkah ini menulis ribuan baris revisi:
.\.venv\Scripts\python -m mejasaham --buat-cadangan --folder-data .uji-data/mejasaham
#   -> .uji-data\mejasaham-cadangan\20261016T165510578553+0700
# 2) muat berkas impor langkah 3 ke basis data utama (sebelumnya hanya ke salinan uji):
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\riset-idx\impor-suspensi-20261016" --folder-data .uji-data/mejasaham
#   -> 171 baris baru; likuid 205 -> 201; masih "PERINGKAT SEMENTARA"
# 3) bangun berkas turunan basis data TANPA penanda (read-only atas basis data, tidak menulis apa pun):
.\.venv\Scripts\python .uji-data\riset-idx\buat-tanpa-penanda.py
#   -> revisi terkini 2.447 · penanda dilepas 2.154 · baris ditulis 2.447 · bulat-balik sama persis
#      keluaran: .uji-data\riset-idx\tanpa-penanda-20261016\{notasi-khusus.csv,bukti-keadaan.txt}
# 4) impor sebagai revisi baru (append-only):
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\riset-idx\tanpa-penanda-20261016" --folder-data .uji-data/mejasaham
#   -> 2.447 baris baru, 0 sudah ada dan sama; notasi 4.723 -> 7.170; snapshot 8
# 5) perbarui berkas konfigurasinya supaya impor berikutnya tidak memuat kembali penandanya:
Copy-Item .uji-data\riset-idx\tanpa-penanda-20261016\notasi-khusus.csv .uji-data\mejasaham\konfigurasi\notasi-khusus.csv
# 6) buktikan:
.\.venv\Scripts\python -m mejasaham --saring --teratas 5 --folder-data .uji-data/mejasaham
#   -> "Kandidat teratas" (bukan lagi PERINGKAT SEMENTARA), likuid 201, lolos saring 9, dinilai 9
#   Bukti: .uji-data\uji-lepas-penanda\ (bukti-0 … bukti-7); berkas lama disimpan sebagai
#          notasi-khusus-sebelum-diganti.csv di folder yang sama
```

```powershell
# --- Aksi #17 (SUDAH DIJALANKAN 16 Okt 2026, sesi 7): jalankan K53 + K54 — tanpa jaringan ---------
# Tidak ada perubahan kode aplikasi. Pembangunnya read-only atas basis data dan idempoten, jadi blok
# ini bisa diulang: hasilnya harus sama dengan berkas yang sudah ada.
# 1) cadangkan dulu (bila ingin mengulang dari keadaan sekarang; langkah ini menulis revisi baru):
.\.venv\Scripts\python -m mejasaham --buat-cadangan --folder-data .uji-data/mejasaham
# 2) bangun berkas dari REVISI TERKINI BASIS DATA (jangan menyunting konfigurasi\notasi-khusus.csv):
.\.venv\Scripts\python .uji-data\riset-idx\k53-k54\buat-k53-k54.py
#   -> 2.450 baris (+3) · MTFN dua episode · ELTY/ARTI dua baris baru · 126 syarat lulus
#      Pemeriksa idempotensinya (opsional): bangun juga dari cadangan pra-impor, lalu bandingkan hash
.\.venv\Scripts\python .uji-data\riset-idx\k53-k54\buat-k53-k54.py `
    --db ".uji-data\mejasaham-cadangan\20261016T172705653192+0700\mejasaham.db" `
    --keluaran ".uji-data\riset-idx\k53-k54\keluaran-dari-cadangan"
Get-FileHash .uji-data\riset-idx\k53-k54\keluaran\notasi-khusus.csv,
             .uji-data\riset-idx\k53-k54\keluaran-dari-cadangan\notasi-khusus.csv   # hash harus sama
# 3) impor sebagai revisi baru, lalu perbarui berkas konfigurasi:
.\.venv\Scripts\python -m mejasaham --impor ".uji-data\riset-idx\k53-k54\keluaran" --folder-data .uji-data/mejasaham
Copy-Item .uji-data\riset-idx\k53-k54\keluaran\notasi-khusus.csv .uji-data\mejasaham\konfigurasi\notasi-khusus.csv
# 4) buktikan keadaan + saring:
.\.venv\Scripts\python .uji-data\riset-idx\k53-k54\keadaan-notasi.py --db .uji-data\mejasaham\mejasaham.db
#   -> MTFN: 2023-10-30 -> 2024-08-29 (tertutup) DAN 2025-06-30 (terbuka); ELTY 1 baris; ARTI 3 baris
.\.venv\Scripts\python -m mejasaham --saring --teratas 5 --folder-data .uji-data/mejasaham
#   -> tetap "Kandidat teratas", likuid 201, lolos saring 9
# 5) periksa cacat `;` yang ditemukan sesi ini (belum diperbaiki — aksi #18):
.\.venv\Scripts\python .uji-data\riset-idx\k53-k54\ukur-potong-keterangan.py > .uji-data\riset-idx\k53-k54\potong-keterangan.txt
#   -> 66 dari 171 baris berkas impor langkah 3 kehilangan ekor keterangannya saat impor
#   Bukti: .uji-data\uji-k53-k54\ (bukti-0 … bukti-10)
```

```powershell
# --- Aksi #18 (SUDAH DIJALANKAN 16 Okt 2026, sesi 8): cacat `;` ditutup — tanpa jaringan -----------
# (a) Data: pemulihan keterangan dari baris MENTAH berkas impor langkah 3 sudah menyatu di pembangun
#     yang sama (`lengkapi_keterangan`), jadi perintahnya sama seperti blok aksi #17 di atas:
.\.venv\Scripts\python .uji-data\riset-idx\k53-k54\buat-k53-k54.py
#   -> "65 baris keterangannya DIPULIHKAN…" + 202 syarat lulus (termasuk: MTFN 2025-06-30 TIDAK
#      dipulihkan, dan berkas impor langkah 3 yang lama DITOLAK pembaca berkas)
.\.venv\Scripts\python .uji-data\riset-idx\k53-k54\periksa-aksi-18.py --db .uji-data\mejasaham\mejasaham.db
#   -> penanda: TANGGAL_MULAI… 66 · AKTIF_DUA_KALI… 4 (ASMI, COAL, LCKM, MTFN) · kutipan keputusan: 172
# (b) Pembaca berkas: uji yang membuktikannya (satu di antaranya gagal pada kode lama)
.\.venv\Scripts\python -m pytest tests\test_impor_berkas.py -q      # 38 lulus (3 uji baru)
.\.venv\Scripts\python -m pytest -q                                 # 768 lulus
#   Bukti: .uji-data\uji-aksi-18\ (bukti-0 cadangan · bukti-1 impor 65 baris · bukti-2 keadaan
#          sesudah · bukti-3 --saring · bukti-4 pytest · bukti-5 uji baru pada kode lama)
```

```powershell
# --- Panel jendela PySide6 (aksi #10 tahap 1, T65) — tanpa jaringan, tanpa layar -------------
# Ujinya dijalankan di platform offscreen, jadi tidak membuka jendela dan tidak butuh layar.
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m pytest tests\test_ui_tabel.py tests\test_ui_jendela.py -q   # 46 lulus
# Bukti atas data nyata (salinan .uji-data/uji-jurnal; tombol "Jalankan saringan" MENULIS skor
# ke salinan itu — karena itu jangan diarahkan ke folder data yang dipakai berhitung):
.\.venv\Scripts\python .uji-data\riset-idx\jendela\bukti-jendela.py      # bukti-1 … bukti-8
.\.venv\Scripts\python .uji-data\riset-idx\jendela\tangkap-layar.py      # 5 PNG tiap layar
#   Di mode offscreen Qt tidak menemukan fontnya sendiri (semua teks jadi kotak); skrip
#   tangkapannya sudah menyetel QT_QPA_FONTDIR ke %WINDIR%\Fonts — lihat jebakan di bagian 6.

# Jendela sungguhan (butuh layar; dijalankan pengguna, bukan sesi agen):
.\.venv\Scripts\python -m mejasaham --folder-data .uji-data\uji-jendela
```

```powershell
# --- Tindakan MENULIS dari jendela (aksi #19 tahap 1, K59/T69/T70) — tanpa jaringan, tanpa layar --
# Lapisan tulisnya bebas Qt, jadi sebagian besar ujinya tidak butuh Qt sama sekali:
.\.venv\Scripts\python -m pytest tests\test_ui_tulis.py -q                  # 19 lulus (tanpa Qt)
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m pytest tests\test_ui_jendela.py tests\test_ui_tabel.py -q   # 46 lulus
#   Yang dijaga uji itu: baris dari jendela SAMA dengan baris dari `cli.main` (dibandingkan pada
#   dua basis data yang dibangun identik: v_transaksi/v_posisi/v_rencana/v_kandidat/v_jurnal),
#   konfirmasi memuat angka yang akan ditulis, kunci tulis berbunyi "belum menulis apa pun" dan
#   tidak menulis baris, dan galat selain kunci TIDAK ditelan.

# Bukti atas DATA NYATA (salinan .uji-data/uji-jurnal; basis data aslinya tidak disentuh):
# tiga tindakan dijalankan dua kali — sekali lewat panel jendela sungguhan di platform offscreen,
# sekali lewat baris perintah — lalu kelima view dibandingkan kolom demi kolom.
.\.venv\Scripts\python .uji-data\riset-idx\tulis-jendela\bukti-tulis-jendela.py
#   -> "seluruh view SAMA" · kunci tulis ditunggu 5,56 dtk lalu berhenti dengan pesan (0 baris)
#   Bukti: .uji-data\uji-tulis-jendela\bukti\bukti-tulis-jendela.txt

# --- Aksi #19b: impor dari jendela + "Pakai ukuran patuh" (K59 c/K63/K64, T72) -----------------
# Impor dijalankan dua kali atas dua SALINAN basis data nyata, dengan folder impor yang sama dan
# nyata (.uji-data/mejasaham/konfigurasi): sekali lewat `--impor`, sekali lewat menu Berkas
# jendela sungguhan (platform offscreen). Butuh beberapa menit (basis data 220 MB).
.\.venv\Scripts\python .uji-data\riset-idx\impor-jendela\bukti-impor-jendela.py
#   -> seluruh 13 tabel/view SAMA (termasuk harga_harian 999.421 baris); kedua jalur menulis
#      4.131 baris baru · 1.095 sudah ada dan sama; konfirmasi "total: 5.226 baris dari 9 berkas";
#      berkas yang ditolak pembaca ditolak dengan kalimat yang sama (0 baris); kunci tulis 5,62 dtk
#      lalu berhenti; `v_rencana_terkini` hasil ukuran patuh SAMA dengan baris perintah
#   Bukti: .uji-data\uji-impor-jendela\bukti\bukti-impor-jendela.txt (+ bukti-uji-pada-kode-lama.txt)

# Uji barunya bergigi: dijalankan atas kode lama di worktree terpisah (`git worktree add`)
#   -> 17 gagal / 48 lulus di tiga berkas itu; bukti lengkapnya di
#      .uji-data\uji-impor-jendela\bukti\bukti-uji-pada-kode-lama.txt

# Tata letak barunya DILIHAT (bukan diduga): 3 tangkapan layar di platform offscreen —
# 11.3 dengan kotak Rencana/Posisi dari daftar, 11.4 tanpa centang, 11.4 dengan ukuran patuh.
.\.venv\Scripts\python .uji-data\riset-idx\impor-jendela\tangkap-layar-19b.py
#   -> .uji-data\uji-impor-jendela\bukti\tangkapan-1..3-*.png (tangkapan sesi 9 tidak ditimpa)

# Kunci tulis yang sama dari SISI BARIS PERINTAH (dulu: traceback `sqlite3`):
.\.venv\Scripts\python -m pytest tests\test_db.py -q -k penulis_kedua       # 1 lulus
#   -> `db.tulis` melempar `db.BasisDataTerkunci` berisi `db.KALIMAT_TERKUNCI` — satu kalimat
#      yang dipakai dua mode, bukan dua kalimat yang mirip

# --- Lingkup rasio bank (K68/P39, sesi 14) — baca-saja atas SALINAN, tanpa perubahan kode --------
# Menjawab "bank mana yang menunggu rasio?" SEBELUM mengumpulkan angkanya. Salinan dibuat lebih dulu
# karena `pengatur.jalankan_saring` SELALU menulis satu baris `log_jalan` sekalipun `simpan=False`
# (terukur: koneksi read-only ditolak `attempt to write a readonly database`).
Copy-Item .uji-data\uji-jenis\mejasaham.db .uji-data\uji-lingkup-p39\mejasaham.db -Force
.\.venv\Scripts\python .uji-data\riset-idx\rasio-bank\lingkup-p39.py
#   -> likuid 235 · lolos 9 · 49 bank disaring · 0 lolos · 0 tertahan HANYA oleh rasio bank
#      (empat rasio tidak dinilai pada ke-49 bank; 34 juga gagal adtv20, 40 gagal tren_ma200,
#       19 gagal kekuatan_relatif) → mengisi rasio saja TIDAK membuat bank masuk peringkat
#   Bukti: .uji-data\uji-lingkup-p39\bukti-lingkup-p39.txt

# --- Uji Python 3.13 (K67, sesi 14b) — lingkungan terpisah di .tmp\py313, TANPA menyentuh .venv ---
# Yang menentukan BUKAN "0 mati dengan penangkal" (itu dijamin penangkalnya), melainkan A/B
# TANPA penangkal di dua versi. Plugin .tmp\plugin_tanpa_tahan.py mengganti tahan_gc_siklik
# dengan blok kosong; 3 uji penjaga penangkal akan GAGAL — itu memang diharapkan.
$env:PYTHONPATH = "$PWD\.tmp"; $env:QT_QPA_PLATFORM = "offscreen"
.\.tmp\py313\Scripts\python.exe -m pytest tests\test_ui_jendela.py -q       # 36 lulus (dengan penangkal)
.\.tmp\py313\Scripts\python.exe -m pytest tests\test_ui_jendela.py -q -p plugin_tanpa_tahan  # 33 lulus/3 gagal
.\.venv\Scripts\python.exe     -m pytest tests\test_ui_jendela.py -q -p plugin_tanpa_tahan  # pembanding 3.14
#   -> 17 Okt 2026: 0 proses mati di KEEMPAT percobaan (padahal sesi 10: 7 dari 18 tanpa penangkal)
#      → "belum dapat disimpulkan"; patokan "mati" = tidak ada ringkasan pytest, BUKAN pola teks
#        `access violation` (pola itu cocok juga dengan docstring uji → 24 log bertanda palsu)
#   Cabut lingkungannya: uv python uninstall 3.13; Remove-Item -Recurse .tmp\py313
#   Folder `.tmp\py313` SEMPAT dihapus 17 Okt 2026 (pembersihan ruang), lalu DIBANGUN ULANG
#   19 Okt 2026 (sesi 21, K69) — 10,7 dtk dari cache uv, tanpa unduhan; sekarang ADA (769 MB).
#   Plugin `.tmp\plugin_tanpa_tahan.py` juga masih ada (salinannya di .uji-data\riset-idx\k69\).
#   Bila hilang: `uv venv --python 3.13 .tmp\py313` →
#   `uv pip install --python .tmp\py313\Scripts\python.exe -r requirements.txt pytest`
#   (interpreter 3.13.14 sudah terpasang di folder data uv; rincian di
#    docs/riset-pyside6-gc-2026-10.md bagian 8.5 dan 10).
#   K69 (19 Okt 2026): seluruh suite 12x TANPA penangkal → 3.14.7: 2 mati; 3.13.14: 0 mati.
#   Perintahnya: .\.venv\Scripts\python .tmp\k69-jalankan.py 12
#                .tmp\py313\Scripts\python .tmp\k69-jalankan-313.py 12
#                .\.venv\Scripts\python .tmp\k69-ringkas.py   → .uji-data\uji-k69\bukti-k69.txt
```

```powershell
# --- Aksi #19d: ubah stop (11.1) + keputusan right issue (11.3) dari jendela (K62, T74) ---------
# Uji lapisan tulisnya bebas Qt, jadi sebagian besar ujinya tidak butuh layar:
.\.venv\Scripts\python -m pytest tests\test_ui_tulis.py tests\test_ui_tabel.py -q   # 46 lulus
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m pytest tests\test_ui_jendela.py -q                        # 46 lulus
#   (ketiganya sekaligus: 92 lulus; terukur 4× berturut-turut tanpa proses yang mati — cacat
#    PySide6/T68 bergantung waktu, jadi sekali lulus belum cukup)
#   Yang dijaga uji baru itu: baris `posisi` dari jendela SAMA dengan `--ubah-stop` (termasuk
#   `tgl_stop` dan V5 saat stop diturunkan), keputusan right issue SAMA dengan
#   `--putuskan-right-issue`, `tebus` tanpa transaksi ditolak SEBELUM dialog konfirmasi
#   (jendela tidak mencatatkan transaksinya diam-diam), isian yang tidak dipakai pilihan
#   ditolak berisik, dan jendela tidak pernah memilihkan baris right issue.

# Bukti atas DATA NYATA: dua salinan identik `.uji-data/uji-aksi-korporasi` (999.421 bar,
# 4 posisi, 4 right issue, 3 keputusan) — sekali lewat baris perintah, sekali lewat jendela
# sungguhan (offscreen) — lalu ketiga view dibandingkan kolom demi kolom. Membuat salinannya
# sendiri; basis data aslinya tidak disentuh. ±2 menit (potret + saringan untuk satu kode).
.\.venv\Scripts\python .uji-data\riset-idx\stop-right-jendela\bukti-stop-right-19d.py
#   -> HASIL: LULUS · v_posisi_terkini (4), v_keputusan_right_issue_terkini (3),
#      v_transaksi_terkini (6) SAMA · MLPT 17.000 (basis 15 Jul 2026) -> 1.200 tanpa V5 palsu ·
#      ASII 4.830 -> 4.700 tercatat V5 · hak MLPT 6.250 lbr + catatan lot K31 ·
#      `tebus` tanpa transaksi ditolak berisik & 0 baris · `tebus` lewat transaksi #6 = revisi r2
#   Bukti: .uji-data\uji-stop-right-jendela\bukti\bukti-stop-right-19d.txt

# Tangkapan layar 11.1 & 11.3 (dijalankan SESUDAH skrip bukti di atas; folder buktinya tidak
# dihapus, jadi berkas .txt-nya aman — jebakan "bukti hilang" di bagian 6).
.\.venv\Scripts\python .uji-data\riset-idx\stop-right-jendela\tangkap-layar-19d.py
#   -> tangkapan-1..6-*.png (formulir ubah stop, dialog konfirmasinya, keadaan sesudah tersimpan,
#      tabel hak + formulir keputusan, dialog konfirmasi keputusan, keadaan sesudah tersimpan)

# Bukti uji barunya BERGIGI: lima perilaku #19d dimatikan satu per satu (mutasi terarah), lalu
# uji sasaran harus GAGAL — dan berkasnya dipulihkan byte-identik (diperiksa SHA-256).
.\.venv\Scripts\python .uji-data\riset-idx\stop-right-jendela\uji-mutasi-19d.py
#   -> HASIL: LULUS (5/5), bukti .uji-data\uji-stop-right-jendela\bukti\bukti-mutasi-19d.txt
#   Catatan: menjalankan uji baru pada worktree `HEAD` BUKAN pembanding yang tajam sesi ini —
#   Catatan: uji itu dijalankan ketika HEAD masih `2e6a292` (= kode sesi 11), sebab pekerjaan sesi
#   12-18 belum di-commit saat itu -> 44 gagal/48 lulus. Sesudah commit `3565d02`/`2aacd2b` barulah
#   ada pembanding yang benar-benar "kode lama yang dekat" (dan bukti utamanya tetap mutasi terarah).
```

```powershell
# --- Aksi #19d dari sisi baris perintah (tanpa jendela) — yang harus tetap sama ----------------
# Idempoten hanya pada SALINAN: jalankan atas salinan `.uji-data/uji-aksi-korporasi`, bukan
# aslinya, sebab tiap jalan menambah revisi baru (append-only).
Copy-Item -Recurse .uji-data\uji-aksi-korporasi .uji-data\uji-19d-perintah
.\.venv\Scripts\python -m mejasaham --ubah-stop --id-posisi 2 --stop 4700 `
    --tanggal 2026-10-16 --alasan "menurunkan stop" --folder-data .uji-data/uji-19d-perintah
#   -> `V5` muncul di barisnya (menurunkan stop boleh, tetapi tercatat); `tgl_stop` = tanggal itu
.\.venv\Scripts\python -m mejasaham --putuskan-right-issue MLPT --tanggal-aksi 2026-09-20 `
    --keputusan tebus --id-transaksi 6 --folder-data .uji-data/uji-19d-perintah
#   -> revisi r2 menunjuk transaksi #6; keputusan lama tidak dihapus
```

### Catatan penting soal lokasi data (sudah diuji, jangan diulang)

Data nyata sesi-sesi sebelumnya ditaruh di **`.uji-data/`** (gitignored, memang untuk ini), dan
`%LOCALAPPDATA%\MejaSaham` **belum pernah dibuat**.

* Di dalam sesi agen: selalu tambahkan `--folder-data .uji-data`.
* Dari terminal pengguna sendiri: tanpa `--folder-data`, dan data masuk ke lokasi standar.

Alasannya bergantung pada sandbox sesi, jadi periksa dulu sebelum menyimpulkan ada bug. Yang
terukur 9 Okt 2026 (sesi yang **menyatakan** akses penuh, tetap saja Python tidak bisa keluar repo):

```powershell
.\.venv\Scripts\python -c "import pathlib,os; p=pathlib.Path(os.environ['TEMP'])/'x.txt'; p.write_text('x')"
# PermissionError: [Errno 13] Permission denied: 'C:\Users\PENGGUNA\AppData\Local\Temp\x.txt'
```

Akibatnya `tempfile.gettempdir()` **jatuh ke folder kerja** (Python memilih kandidat pertama yang
bisa ditulis, dan `os.curdir` adalah kandidat terakhir), sehingga `python -m pytest` berjalan
dengan folder sementara di akar repo (`pytest-of-*/`, sudah gitignored). Sebelumnya, ketika
folder sementaranya jatuh di lokasi yang tidak bisa ditulis Python, **seluruh uji berbasis
`tmp_path` gagal di tahap setup** — 195 dari 308 uji pada 9 Okt 2026, dan 214 error lagi di sesi
yang sama, tanpa satu pun perubahan kode. Gejalanya menyesatkan; yang pertama diperiksa adalah
lokasi folder sementaranya, bukan kodenya.

---

## 4. Aksi berikutnya, urut dari yang paling menentukan

Langkah 1 rencana K36–K41 (rekonsiliasi per kode seluruh rekaman SPT multi-kode) **selesai dan
diverifikasi 16 Okt 2026**; langkah 3 dan langkah 4 menyusul dan **keduanya sudah selesai**
(aksi #14 dan #15 di tabel bawah). Dengan selesainya sisi UPT (12 Okt 2026, 41 baris) dan sisi SPT
(16 Okt 2026, 1.118 baris / 162 kode), **seluruh 56 rekaman suspensi multi-kode sudah terpetakan per
kode**, berkas impornya sudah dimuat ke basis data `.uji-data/mejasaham`, dan penandanya **sudah
dilepas** — jadi `--saring` kini berbunyi **"Kandidat teratas"**, bukan lagi PERINGKAT SEMENTARA.
Sesi 6 menutup **tinjauan visual yang dituntut K46** (aksi #16) dan dari situ muncul **dua temuan yang
menuntut keputusan lebih dulu** — **U24/U25** — dan **keduanya sudah diputuskan pengguna pada sesi yang
sama** menjadi **K53/K54** (`docs/keputusan.md` bagian 2), lalu **dijalankan pada sesi 7** (aksi #17, lihat
`docs/keputusan.md` bagian 5 "Pelaksanaan K53 + K54"): penanda `DITAHAN_K46_…` **sudah dilepas**, episode
MTFN 2023–2024 **sudah dibentuk**, dan `ELTY`/`ARTI` **sudah punya barisnya**. Sesi 7 juga menemukan **satu
cacat baru** yang belum diperbaiki — `keterangan` **66 dari 171 baris** berkas impor langkah 3 terpotong di
`;` pertama saat impor (aksi **#18**), dan **#18 sudah dikerjakan pada sesi 8** — keterangan 65 baris
dipulihkan dari baris mentah berkasnya, dan pembaca berkas kini **menolak** kolom berlebih yang berisi
(tiga uji baru, satu terbukti gagal pada kode lama). **Sesi 11 menutup aksi #19 tahap 1** — jendela
kini **menulis** tiga pencatat (catat transaksi, simpan rencana, catat jurnal) lewat jalur inti yang
sama dengan baris perintah; **sesi 12 menutup aksi #19b** — jendela kini juga **mengimpor** dari menu
Berkas, layar 11.4 punya pilihan **"Pakai ukuran patuh"** (K63), dan rencana/posisi **dipilih dari
daftar** (K64). **Sesi 16 menutup aksi #19c** — jendela juga **mencadangkan** (folder tujuannya
disebut di konfirmasi, dan pemuatan ulang dasbor yang tidak perlu tidak lagi dibayar) dan
**menampilkan daftar cadangan** dengan baris yang sama dengan `--daftar-cadangan`. **Sesi 18 menutup
aksi #19d** — jendela juga **mengubah stop** (11.1) dan **memutuskan right issue** (11.3), sehingga
**seluruh cakupan tindakan tulis bertahap K59 c terpenuhi**; yang tetap di baris perintah hanya
`--pulihkan` (K59 e). Sesi 11b mencatat pertanyaan
P34–P36 dan **sesi 11c mencatat jawabannya** ("sesuai rekomendasi" → **K62–K64**, bentuk teknisnya
**T71**, pelaksanaan #19b **T72**, #19c **T73**, #19d **T74**) — jadi **tidak ada pertanyaan yang
menunggu**, urutan kerja di tabel bawah sudah final, dan usulan **U30** yang muncul dari #19c
**sudah dikunci sesi 17 sebagai K70** (folder tujuan cadangan tetap dari konfigurasi).
**Sesi 20 menutup #24 dan #25** (K71/K72, T75), dan **sesi 21 menjalankan riset K69** (baris #22):
reproduksi ulang **berhasil** — suite penuh 12× tanpa penangkal di 3.14.7 → **2 mati**, A/B di
3.13.14 → **0 mati** (p ≈ 0,48) — dan dari situ muncul **U31** (pin Python? rekomendasi: **jangan**)
serta **U32** (uji flaky → usulan **aksi #26**). **Sesi 22 mencatat jawabannya: U31 → K74** (jangan
pin; T68 tetap) dan **U32 → K75** (uji flaky diperbaiki lewat #26). **Sesi 23 menutup #26** (K75/T76:
baris `snapshot` dibandingkan tanpa dua kolom waktu impor; A/B jam dipaksa, mutasi, 12/12 jalan, suite
**882 lulus**). **Sesi 24 mencatat bentuk pelaksanaan #21b sebagai pilot 5 bank (K76)** — BBCA, BBRI,
BMRI, BBNI, BRIS; kandidat + kutipan resmi, tanpa impor sampai angka diverifikasi. **Sesi 25
menjalankan pilot itu sampai batas kandidat: 2 bank terbaca (BBCA, BRIS), 3 tidak (BMRI, BBNI, BBRI)**;
**sesi 26 mencatat empat keputusan sesudahnya (K77–K80)**, dan **sesi 27 menutup #27** — `sumber` per
baris `rasio_bank` kini dipakai, disimpan, dan kembali lewat `potret` (K78/T77). **Sesi 28 mencatat
K81–K82**: sel `sumber` kosong **ditolak** (K81), dan `potret._fundamental` **dikerjakan sebagai
aksi #28** (K82); **sesi 29 menutup #28** — `Fundamental.sumber` kini ikut kembali lewat `potret`,
dengan dua uji yang terbukti gagal pada `HEAD` (T78). **Sesi 30 mencatat K83–K84**: verifikasi angka
kandidat **dialihkan ke agen** dengan pagar "cocok persis" (**aksi #29**), sedangkan **pengiriman
laporan PySide6 tetap manusia** (K84). **Aksi #29 sudah dijalankan (sesi 31)**: verifikasi **14/14 sel** cocok → CSV diisi → `--impor`
(**2 baris, snapshot 12**) → periksa; **`--saring` belum berubah karena `jenis` 973 emiten kosong**
dan BBCA/BRIS gagal `coverage`. **Sesudahnya (sesi 31 lanjutan) K85–K87 dikunci:** revisi `notasi_khusus` diterima, **U34 ditutup**
(21 Agu dipertahankan), dan **44 bank ditunda** sampai `jenis` terisi. **Sesi 32–33** menjalankan
prasyaratnya (`jenis` terisi; K79 = 8 manual · 2 tidak terukur · 34 otomatis) dan **mengunci K88 =
tetap tunda**. **Sesi 34 menutup #23/U26** — konteks pasar kini ditulis `--saring` dan dibaca dasbor
bila kuncinya masih sama (T80: `--dasbor` **18,95 → 0,74 dtk**). **Sesi 35 mengerjakan Tahap 5**
sesudah pengguna menjawab "sesuai rekomendasimu": bundel PyInstaller onedir + skrip build +
`requirements-build.txt`, dengan bukti mode kepala, GUI offscreen, dan salinan aplikasi berjalan
tanpa Python di `PATH` (**T81**; suite **908 lulus**). **Tidak ada aksi agen yang menunggu sekarang:** 44 bank tetap ditunda (K88), pengiriman laporan
PySide6 adalah pekerjaan pengguna (K84), dan --pulihkan tetap di luar cakupan jendela (K59 e/K64).
Ikon aplikasi sudah dibuat dan dipasang sesi 36 (T82). Sesi 37 memperbaiki konflik DLL ICU yang
membuat QtCore gagal dimuat (T83); suite 911 lulus dan GUI bertahan pada uji offscreen. Berikutnya
pengguna mencoba EXE terbaru: `dist\MejaSaham\MejaSaham.exe`.

| # | Aksi | Syarat / pemicu | Yang disentuh | Cara memverifikasi |
|---|---|---|---|---|
| 0 | ~~Putuskan jalur PDF untuk `rasio-bank.csv`~~ | **Selesai 10 Okt 2026 → K24: rasio bank diisi MANUAL** untuk bank yang masuk kandidat; jalur otomatis PDF sengaja tidak dibangun (ukurannya di 2.1a). Jangan tawarkan lagi menambah pustaka pengurai PDF tanpa alasan baru | — | — |
| 0b | ~~Cari daftar papan pemantauan khusus/suspensi~~ | **SELESAI 10 Okt 2026 → K27.** Jalurnya ternyata ada: **`www.idx.id`** (domain resmi IDX yang lain) melayani halaman notasi khusus dengan **HTTP 200** untuk User-Agent yang menyebut dirinya — `www.idx.co.id` tetap 403. `--ambil-notasi` + `mejasaham/notasi.py`; terukur 122 baris / **68 emiten papan pemantauan khusus**, dan `--saring` berhenti menyebut daftarnya "PERINGKAT SEMENTARA" | — | `.uji-data/uji-sektor/bukti-ambil-notasi.txt`, `bukti-saring-notasi.txt` |
| 1a | ~~Putuskan U20/U21, lalu muat entri `[[biaya_broker]]` Stockbit~~ | **SELESAI 10 Okt 2026 → K22/K23**, migrasi 008 terpasang, entri Stockbit **sudah dimuat** ke `.uji-data/konfigurasi/parameter-bursa.toml`. Bukti terukurnya: `--muat-konfigurasi --folder-data .uji-data` berbunyi **`biaya_broker [Stockbit (PT Stockbit Sekuritas Digital)] dipakai`** dan **`slippage dipakai`**, keluar **0**, muat ulang idempoten (`baru disimpan: 0, sudah ada dan sama: 8`). Sebelumnya keduanya `belum_terverifikasi` | `docs/konfigurasi.md` B6/B7/B9, `docs/skema-data.md` 5.8, `docs/arsitektur.md` T34/T35 | `.uji-data/bukti-muat-konfigurasi-sebelum.txt` vs `…-sesudah.txt` |
| 1b | ~~Turunkan `jenis` emiten dari data~~ | **Selesai 10 Okt 2026 (K21)** — `mejasaham/jenis.py` + `--ambil-jenis`, masuk commit `14d4d6b`. Terukur atas data nyata 916 emiten: **49 `bank_keuangan`** (BBRI, BMRI, BBCA, BBNI, BRIS, BJBR, BTPS, …) · **862 `umum`** · **5 kosong** | — | `.uji-data/uji-jenis/` (`bukti-ambil-jenis.log`, `bukti-impor-jenis.log`, `bukti-saring-jenis.txt`) |
| 2a | ~~Kandidat & watchlist (F4)~~ | **SELESAI 10 Okt 2026** — commit `70ad3ec`, migrasi 009, `tests/test_kandidat.py` (23 uji). Status ide → watchlist → rencana → posisi, tesis wajib (AC-4) | — | `.uji-data/uji-kandidat/bukti-kandidat.txt` |
| 2b | ~~Kalkulator risiko & rencana (F5)~~ | **SELESAI 10 Okt 2026** — migrasi 010, `mejasaham/risiko.py`, `tests/test_risiko.py` (62 uji), seluruhnya **567 lulus**. Terukur atas data nyata: TLKM → 10.800 lembar, risiko Rp 1.663.200 (0,66%); pelanggaran total risiko 5,06% **ditolak** simpan, ukuran patuh 600 lembar, revisi dengan pelanggaran diterima tersimpan (544 bp) | `docs/skema-data.md` 5.10, `docs/arsitektur.md` T38–T40 | `.uji-data/uji-risiko/` (12 `bukti-*.txt` + `bukti-keadaan.txt`) |
| 3 | ~~Jawab P24~~ (batas bobot per sektor) | **SELESAI 10 Okt 2026 → K25**: kolom `emiten.sektor_sumber` (migrasi 011) berlabel sumber, diisi `--ambil-jenis`; batas 30% kini ditegakkan dan taksonominya disebut. `sektor_idx_ic` tetap menang begitu diisi manusia | — | `.uji-data/uji-sektor/bukti-hitung-risiko-sektor.txt` |
| 5 | ~~Tahap 2 lanjutan: `transaksi` & `posisi` (F11) + dasbor "tindakan menunggu" (P16)~~ | **SELESAI 10 Okt 2026** — migrasi 012, `mejasaham/posisi.py` + `mejasaham/dasbor.py`, `tests/test_posisi.py` (57) + `tests/test_dasbor.py` (14), seluruhnya **657 lulus**. AC-6 & AC-13 terukur atas data nyata; V5 tercatat. **Panel jendela PySide6 belum** (bagian dari butir ini, dikerjakan tersendiri) | `docs/skema-data.md` 5.13, `docs/arsitektur.md` T43–T47 | `.uji-data/uji-posisi/` (16 `bukti-*.txt` bernomor + `bukti-keadaan.txt`) |
| 6 | ~~Aksi korporasi pada posisi~~ | **SELESAI 10 Okt 2026** — migrasi 013, `mejasaham/posisi.py` + `mejasaham/dasbor.py`, `--hak-right-issue` & `--putuskan-right-issue`, `tests/test_aksi_korporasi_posisi.py` (39 uji), **698 lulus**. AC-18 terukur atas data nyata (MLPT 1:25 → 25.000 lbr / stop Rp 680 / risiko Rp 5.875.000); 38 dari 39 uji barunya **terbukti gagal pada kode lama** | `docs/skema-data.md` 5.14, `docs/arsitektur.md` T48–T51, `docs/keputusan.md` K28 | `.uji-data/uji-aksi-korporasi/` (16 `bukti-*.txt`) |
| 7 | ~~Ekuitas diturunkan dari transaksi + kas (P25)~~ **dijawab 10 Okt 2026 → K30** | **Ekuitas tetap dicatat pengguna** di v0.1, dan yang ditambahkan supaya angkanya bisa diperiksa: dasbor menampilkan pembanding `nilai posisi + kas` **beserta selisihnya** (sudah dikerjakan). Yang tersisa hanyalah bila Anda berubah pikiran: menurunkan ekuitas dari transaksi + kas | `mejasaham/risiko.py`, `pengatur.py` | Dasbor menyebut pembanding + selisihnya (`bukti-16-dasbor-dengan-pembanding-ekuitas.txt`) |
| 8 | ~~Jurnal & kepatuhan (F7, Tahap 3)~~ | **SELESAI 10 Okt 2026** — migrasi 014, `mejasaham/jurnal.py`, `--jurnal`/`--rekap-kepatuhan`/`--jurnal-catat`, `tests/test_jurnal.py` (**42** uji) + **3** penjaga migrasi 014 di `tests/test_db.py`, **747 lulus**. Seluruh katalog V1–V7 kini dihitung dari **satu** tempat per kode; atas data nyata: 6 keputusan · patuh 1 (16,67%) · 7 pelanggaran, termasuk **V3 rencana #2 ASII 5,44% > 5,00%**. Perintahnya tidak dikenal di kode lama (keluar 2) | `docs/skema-data.md` 5.15, `docs/arsitektur.md` T52–T55, `docs/keputusan.md` bagian 5 (Tahap 3 langkah 1) | `.uji-data/uji-jurnal/` (10 `bukti-*.txt` + `bukti-keadaan.txt`) |
| 8b | ~~Ekspor laporan (F9)~~ | **SELESAI 10 Okt 2026 — Tahap 3 langkah 2.** Lima jenis laporan diekspor CSV; AC-7/K7/U11 diterapkan. 8 uji ekspor, suite **755 lulus** | `mejasaham/ekspor.py`, `cli.py`, `docs/keputusan.md` bagian 5 | `python -m pytest`; `--help` menampilkan pilihan ekspor |
| 8c | ~~Cadangan/pemulihan (F12, mode CLI)~~ | **SELESAI 11 Okt 2026** — `VACUUM INTO`, konfigurasi/arsip snapshot, retensi 14, pulihkan dengan validasi integritas, otomatis setelah refresh sukses dan sebelum migrasi. Empat uji baru, termasuk pemulihan instalasi bersih dan snapshot sebelum migrasi. Menu jendela mengikuti pekerjaan panel UI | `mejasaham/cadangan.py`, `cli.py`, `db.py`, `docs/arsitektur.md` T57 | `tests/test_cadangan.py` |
| 9 | ~~Daftar suspensi dan UMA~~ | **SELESAI 11 Okt 2026, Tahap 3 langkah 4 → K35.** API resmi IDX; suspensi sampai UPT; UMA 30 hari. Tindak lanjut menemukan seluruh 56 PDF `>1 Kode` beserta teks dan kandidat kode per dokumen. Aksi/tanggal efektif per kode masih direkonsiliasi, termasuk 40 pembukaan kembali tanpa pasangan. Keluaran dan CSV memperingatkan data belum lengkap; `--saring` tetap berperingkat sementara | `mejasaham/notasi.py`, `cli.py`, T58 | `.uji-data/uji-notasi-aktivitas/` (`bukti-ambil.log`, `bukti-impor.log`, `bukti-jumlah-per-jenis.txt`, `bukti-saring.log`); suite 765 lulus; `docs/riset-suspensi-multi-kode-2026-10.md` |
| 10 | **Panel jendela PySide6** | **TAHAP 1 (MEMBACA) SELESAI 17 Okt 2026 (sesi 9) → T65.** Lima layar PRD 11 jalan: `mejasaham/ui/jendela.py` + `ui/tabel.py` (bebas Qt) + `ui/pekerja.py` (utas pekerja). Tiap layar memakai fungsi inti yang sama dengan baris perintah; teks kalkulator risiko dipindah ke `risiko.ringkas_hasil`, kalimat peringkat kosong ke `pengatur.LaporanSaring.catatan_peringkat_kosong`, aturan tesis ke `kandidat.untuk_rencana`. **25 uji baru**, suite **793 lulus**; bukti atas data nyata `.uji-data/uji-jendela/jendela/` (`bukti-1` … `bukti-8`) + 5 tangkapan layar. **Yang belum: tindakan yang menulis** (lihat aksi #19). Tatap muka sesungguhnya di layar pengguna belum pernah dilihat (dijalankan `offscreen`) | `mejasaham/ui/jendela.py`, `ui/tabel.py`, `ui/pekerja.py`, `tests/test_ui_tabel.py`, `tests/test_ui_jendela.py` | `.\.venv\Scripts\python -m pytest tests\test_ui_tabel.py tests\test_ui_jendela.py -q`; `.\.venv\Scripts\python .uji-data\riset-idx\jendela\bukti-jendela.py`; `.\tangkap-layar.py` untuk PNG-nya |
| 11 | ~~P26–P28~~ **SELESAI — dijawab 10 Okt 2026 ("sesuai rekomendasi") → K29–K34** | **K30** dasbor kini menampilkan pembanding `nilai posisi + kas` + selisihnya terhadap ekuitas tercatat (`bukti-16`); **K31** hak right issue yang bukan kelipatan lot disebut lebih awal (`bukti-17`); **K32** TERP tidak dibangun; **K33** dividen tetap dihitung tanpa jalur koreksi; **K34** kepatuhan hanya atas transaksi (bahan F7). **K29** P16 disahkan apa adanya | `mejasaham/dasbor.py`, `mejasaham/posisi.py`, `tests/test_dasbor.py`, `tests/test_aksi_korporasi_posisi.py` | `.uji-data/uji-aksi-korporasi/bukti-16-*.txt`, `bukti-17-*.txt` |
| 12 | **Sumber resmi IDX & peringkat (lanjutan sesi 11 Okt 2026)** | Data lokal `.uji-data/mejasaham`, snapshot 6. Status: 9 peringkat sementara (AUTO 55,8); 973 emiten belum ber-jenis; 56 rekaman suspensi multi-kode sudah dipetakan kandidat kodenya, tetapi aksi dan tanggal efektif per kode belum direkonsiliasi; 40 pembukaan kembali tanpa pasangan masih ditinjau. Fundamental yang ada 707 baris/178 emiten masih berlabel tidak resmi. Riset menemukan IDX Daftar Saham, profil emiten IDX, Financial Data and Ratio, dan filing XLSX/XBRL. Kalender lokal sudah memuat sampai 2027; 09 Okt adalah hari bursa terakhir yang telah terjadi sebelum snapshot Minggu 11 Okt | `.uji-data/mejasaham/konfigurasi/`, `.uji-data/mejasaham/arsip-snapshot/`, `docs/riset-sumber-data-2026-10.md`, `.uji-data/riset-idx/idx-daftar-saham-sektor-20261011.json` | Berikutnya: rekonsiliasi aksi dan tanggal efektif dari dokumen suspensi multi-kode; pertahankan status sementara sampai cakupan notasi diverifikasi. Rincian daftar saham ada di catatan sumber data dan rincian 56 PDF suspensi ada di `docs/riset-suspensi-multi-kode-2026-10.md` |
| 13 | ~~Rekonsiliasi per kode seluruh rekaman SPT multi-kode (langkah 1 rencana K36–K41)~~ | **SELESAI 16 Okt 2026**: 29 rekaman = 26 peristiwa, **1.118 baris / 162 kode**, 158 "mulai disuspensi" (154 unik) + 960 "dipertahankan" (936 unik). Seluruh dokumen diperiksa terhadap angka yang disebut kalimatnya sendiri; dua tidak cocok dan dicatat (`PERTENTANGAN_KOLOM_STATUS` 20 Feb 2024; badan 16 Jun 2025 menyebut 6 saham sedangkan daftarnya 7 kode). Pemeriksa silang: API berkode tunggal + rekonsiliasi UPT 12 Okt 2026 (27 kode berpasangan rapi) | `.uji-data/riset-idx/rekonsiliasi-spt-per-kode-20261016.csv`, `ringkasan-suspensi-per-kode-20261016.csv`, `rekonsiliasi-spt-per-kode-20261016.txt`, `verdict-spt-20261016.json`, `docs/riset-suspensi-multi-kode-2026-10.md` | `python -m pytest` → **765 lulus** (55,95 dtk); tabel verdict per dokumen lewat `verdict-spt-20261016.json` |
| 14 | ~~Tulis berkas impor per kode dari hasil langkah 1, lalu muat ke basis data uji~~ | **SELESAI 16 Okt 2026 (sesi 4)** — langkah 3 rencana K36–K41. **171 baris / 159 kode**, 34 baris 20 Feb 2024 ditahan (K46), 33 episode ditutup penutup UPT yang terkonfirmasi, 65 episode bertanggal mulai proxy. T60 **dibaca sebagai T61** (K50): satu baris per (kode × episode), seluruh pengumuman `dipertahankan` masuk `keterangan` baris itu — sebabnya di K50/T61. Impor ke **salinan** basis data: 171 baru, keluar 0; `--saring` likuid **205 → 201** | `.uji-data/riset-idx/impor-suspensi-20261016/`, `.uji-data/riset-idx/buat-impor-suspensi.py`, `.uji-data/uji-impor-suspensi/bukti-1` … `bukti-9`, basis data uji `.uji-data/uji-impor-suspensi` | `python -m pytest` → **765 lulus** (20,23 dtk), tanpa perubahan kode; `--impor` keluar 0; bukti angka `bukti-3`/`bukti-4`/`bukti-9` |
| 15 | ~~Lepas penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN`~~ | **SELESAI 16 Okt 2026 (sesi 5) — K52 dijalankan berurutan atas basis data `.uji-data/mejasaham`.** (1) cadangan dibuat lebih dulu: `.uji-data/mejasaham-cadangan/20261016T165510578553+0700`. (2) berkas impor langkah 3 dimuat ke basis data utama (171 baris baru; likuid 205 → 201). (3) berkas turunan basis data **tanpa penanda** dibangun oleh `.uji-data/riset-idx/buat-tanpa-penanda.py` — 2.447 revisi terkini, 2.154 penanda dilepas, bulat-balik lewat pembaca impor aplikasi **sama persis**. (4) `--impor` menulis **2.447 baris baru**, keluar 0, snapshot 8 (bukan 2.154 seperti tertulis di rencana — 2.154 itu jumlah baris **berpenanda**; 293 baris sisanya ikut tertulis karena kolom `sumber`-nya berbeda). (5) `konfigurasi/notasi-khusus.csv` diganti turunan itu (berkas lama disimpan). (6) **`--saring` berbunyi "Kandidat teratas"**, likuid 201, lolos saring 9. Basis data: 7.170 baris notasi, **0 baris terkini berpenanda**, suspensi terbuka 489, 654 kode. Yang **tetap** belum selesai dan tetap disebut di `keterangan`: tinjauan visual 1 baris K46 (34 kode), 3 penanda K47, 65 episode bertanggal mulai proxy | `konfigurasi/notasi-khusus.csv` (turunan basis data), basis data `.uji-data/mejasaham`, `.uji-data/riset-idx/buat-tanpa-penanda.py` | `--saring` **tidak lagi** memuat `PERINGKAT SEMENTARA` (likuid 201, lolos saring 9); bukti `.uji-data/uji-lepas-penanda/bukti-0` … `bukti-7` |
| 16 | ~~Tinjauan **visual** pengumuman 20 Feb 2024 (K46), satu halaman tabel 34 baris~~ | **SELESAI 16 Okt 2026 (sesi 6) — tinjauan dijalankan, DUA TEMUAN muncul, dan keduanya diputuskan pengguna pada sesi yang sama → K53/K54 (pelaksanaannya aksi #17).** Kedua halaman dirender lalu dilihat: tabelnya **empat kolom**, **tanpa** legenda/catatan kaki/tanda bintang → halaman itu sendiri tidak bisa memutuskan "status sebelum vs sesudah". Yang menyelesaikannya: status ke-34 kode pada rekaman terakhir **sebelum** pengumuman **identik** dengan kolom di pengumuman itu (**34 identik · 0 berbeda**; 24 *Seluruh Pasar* + 10 *Reguler dan Tunai*) → ruang lingkup tindakannya sudah berlaku sebelumnya, jadi **20 Feb 2024 bukan `tanggal_mulai`**. Bukti terkuat: UPT MTFN 29 Agu 2024 mencabut **delapan** pengumuman sekaligus dan `Peng-S-00006/BEI.PLP/02-2024` nomor 6 di antaranya. **Temuan 1:** episode MTFN 2023–2024 **hilang** — baris MTFN mulai 2025-06-30 tetapi `keterangan`-nya memuat dokumen 2023–2024, dan penutup UPT-nya berstatus TIDAK DIPAKAI; terukur **1 dari 2.447 baris terkini** berpola ini. **Temuan 2:** **K41 belum dijalankan** — penanda "di luar cakupan API" **0 kali**, `ELTY` **0 baris**, `ARTI` tanpa penandanya. **Tidak ada perubahan kode / impor / baris basis data ditulis** | `docs/riset-suspensi-multi-kode-2026-10.md` (bagian tinjauan), `docs/keputusan.md` bagian 2 (U24/U25) & bagian 5 (sesi 6) | `.uji-data/uji-tinjauan-k46/` (`bukti-1` … `bukti-9` + `bukti-keadaan.txt`); pembuatnya `.uji-data/riset-idx/tinjauan-k46/` (read-only); `python -m pytest` → **765 lulus** (26,73 dtk) |
| 17 | ~~Jalankan K53 + K54~~ | **SELESAI 16 Okt 2026 (sesi 7) — dijalankan atas basis data `.uji-data/mejasaham`, tanpa perubahan kode aplikasi.** Cadangan dulu (`.uji-data/mejasaham-cadangan/20261016T172705653192+0700`) · berkas dibangun dari **revisi terkini basis data** oleh `.uji-data/riset-idx/k53-k54/buat-k53-k54.py` (read-only; **idempoten** — hasil dari basis data sesudah impor **byte-identik** dengan hasil dari cadangan pra-impor, SHA-256 sama) · impor revisi baru · `konfigurasi/notasi-khusus.csv` diperbarui · **`--saring` tetap "Kandidat teratas"** (likuid 201 · lolos saring 9). Terukur: 2.450 baris (+3), **33 episode** bercatatan K53 (masing-masing menyebut rekaman SPT yang membuktikan penempelannya), **0 baris terkini** berpenanda `DITAHAN_K46_…`, **2 baris** "di luar cakupan API"; **MTFN dua episode** (2023-10-30 → 2024-08-29 tertutup · 2025-06-30 terbuka), **ELTY** 2023-07-03 → 2023-10-19, **ARTI** 2021-11-30 → 2023-11-23; 126 syarat pemeriksaan lulus | basis data `.uji-data/mejasaham`, `konfigurasi/notasi-khusus.csv`, pembangun di `.uji-data/riset-idx/k53-k54/` | `.uji-data/uji-k53-k54/` (`bukti-0` … `bukti-10`); `python -m pytest` → **765 lulus** (28,01 dtk) |
| 18 | ~~Perbaiki keterangan yang terpotong `;`~~ | **SELESAI 16 Okt 2026 (sesi 8) — dua-duanya dikerjakan, sesuai rekomendasi.** **(a) Data:** berkas dibangun ulang oleh `.uji-data/riset-idx/k53-k54/buat-k53-k54.py` yang kini **memulihkan** keterangan dari baris **mentah** berkas impor langkah 3 — syaratnya ketat (keterangan tersimpan harus **awalan yang benar** dari keterangan berkas, sesudah kalimat yang ditulis skrip ini dibuang) sehingga baris yang sudah dibangun ulang (MTFN 2025-06-30) **tidak** ikut dipulihkan; kalimat penanda `DITAHAN_K46_…` dibuang karena penandanya sudah dilepas K53. Terukur: **65 baris dipulihkan** (`penanda: TANGGAL_MULAI…` 0 → **66**, `AKTIF_DUA_KALI…` 3 → **4**, `kutipan keputusan:` 105 → **172**), impor **65 baris baru** (append-only), konfigurasi diperbarui, `--saring` tetap "Kandidat teratas" (likuid 201). **(b) Pembaca berkas:** `mejasaham/berkas.py` menolak baris berkolom berlebih **yang berisi** — menyebut nama berkas, nomor baris, isi yang akan hilang, dan jalan keluarnya — sementara kolom berlebih kosong tetap diterima; berkas impor langkah 3 yang lama kini **terbukti ditolak** (bukti langsung atas berkas nyata). 3 uji baru, **1 terbukti gagal pada kode lama**; suite **768 lulus** | `mejasaham/berkas.py`, `tests/test_impor_berkas.py`, basis data `.uji-data/mejasaham`, `konfigurasi/notasi-khusus.csv` | `.uji-data/uji-aksi-18/` (`bukti-0` cadangan · `bukti-1` impor 65 baris · `bukti-2` keadaan sesudah · `bukti-3` `--saring` · `bukti-4` pytest 768 · `bukti-5` uji baru pada kode lama · `bukti-6` ringkasan satu halaman) |
| 19 | ~~**Tindakan yang MENULIS dari jendela — TAHAP 1: tiga pencatat transaksi**~~ | **SELESAI 17 Okt 2026 (sesi 11) → T70.** Yang dijalankan, persis K59 + T69: (a) kunci tulis **ditunggu** sampai `busy_timeout` habis lalu berhenti dengan pesan yang memuat **"Jendela belum menulis apa pun"**; (b) tiga pencatat (`posisi.catat_transaksi` di 11.3, `risiko.simpan_dari_kandidat` di 11.4, `jurnal.catat` di 11.5); (c) **konfirmasi untuk semua**, berisi angka yang akan ditulis; (d) **satu jalur inti** — aturan status + perpindahan `watchlist` → `rencana` dipindah dari `cli.py` ke `risiko.simpan_dari_kandidat`, kalimat kunci bersama ke `db.KALIMAT_TERKUNCI`/`db.BasisDataTerkunci`; (e) sesudah berhasil layarnya **dimuat ulang** dari baris tersimpan, pesannya dipertahankan. Terukur atas data nyata (`.uji-data/uji-tulis-jendela/bukti/bukti-tulis-jendela.txt`): kelima view **SAMA** dengan jalur baris perintah, kunci tulis ditunggu **5,56 dtk** lalu 0 baris tertulis; suite **833 lulus**. **Yang belum dari baris ini: impor (#19b) dan cadangan/daftar F12 (#19c)** | `mejasaham/ui/tulis.py` (baru), `mejasaham/ui/jendela.py`, `mejasaham/db.py`, `mejasaham/risiko.py`, `mejasaham/cli.py`, `tests/test_ui_tulis.py` (12), `tests/test_ui_jendela.py` (30), `tests/test_risiko.py` (72), `tests/test_db.py` | `pytest tests\test_ui_tulis.py tests\test_ui_jendela.py -q`; `python .uji-data\riset-idx\tulis-jendela\bukti-tulis-jendela.py` → "seluruh view SAMA" |
| 19b | ~~**Impor dari jendela + pilihan "Pakai ukuran patuh" di 11.4**~~ (K59 c, **K63**, T70/T71) | **SELESAI 17 Okt 2026 (sesi 12) → T72.** Impor dari **menu Berkas** dua tahap (baca folder di utas pekerja → konfirmasi berisi **jumlah baris per tabel** → tulis dengan **objek hasil bacaan yang sama**), `risiko.pakai_ukuran_patuh` sebagai **satu** jalur untuk `--pakai-ukuran-patuh` **dan** layar 11.4, serta **pilihan rencana/posisi dari daftar** di 11.3–11.4 (jendela tidak pernah memilih entri pertama). **Satu cacat perilaku ditemukan dari bukti & ditutup:** impor yang terkunci menunggu **11,16 dtk** (dua penantian `busy_timeout`: penulisan + percobaan mencatat log) → **5,62 dtk**. **+16 uji**, suite **849 lulus**; 17 uji baru/berubah **terbukti gagal pada kode lama**. Terukur atas data nyata: seluruh **13 tabel/view SAMA** antara jendela & baris perintah setelah mengimpor folder konfigurasi produksi (4.131 baris baru · 1.095 sudah ada dan sama; `total: 5.226 baris dari 9 berkas`), berkas yang ditolak pembaca ditolak **dengan kalimat yang sama** (0 baris), `v_rencana_terkini` hasil ukuran patuh **SAMA**. **Catatan apa adanya: pada basis data uji ukuran patuh = ukuran akhir** (batas yang mengikat bobot 10%, bukan total risiko), dan tata letak barunya **dilihat** lewat 3 tangkapan layar `offscreen` — layar sungguhan di monitor Anda tetap belum pernah dilihat | `mejasaham/ui/jendela.py`, `mejasaham/ui/tulis.py`, `mejasaham/ui/tabel.py`, `mejasaham/pengatur.py`, `mejasaham/risiko.py`, `mejasaham/cli.py`, `tests/test_ui_tulis.py` (19), `tests/test_ui_jendela.py` (36), `tests/test_ui_tabel.py` (10) | `pytest tests\test_ui_tulis.py tests\test_ui_jendela.py tests\test_ui_tabel.py -q` (65 lulus); `python .uji-data\riset-idx\impor-jendela\bukti-impor-jendela.py` → "seluruh tabel impor SAMA"; `python .uji-data\riset-idx\impor-jendela\tangkap-layar-19b.py` → 3 PNG; bukti `.uji-data\uji-impor-jendela\bukti\` (`bukti-impor-jendela.txt`, `bukti-uji-pada-kode-lama.txt`, `tangkapan-1..3-*.png`) |
| 19c | ~~**Cadangan + daftar dari jendela (F12)**~~ (lanjutan K59 c/e) | **SELESAI 17 Okt 2026 (sesi 16) → T73.** Menu **Berkas** memuat **"Cadangan basis data…"** dan **"Daftar cadangan…"**: cadangan lewat `Pekerja` dengan konfirmasi yang **menyebut folder tujuannya** (K59 d), lalu menulis lewat `cadangan.buat` — jalur yang sama dengan `--buat-cadangan`; daftarnya memakai teks `cadangan.ringkas_daftar` yang sama dengan `--daftar-cadangan`; **`--pulihkan` tetap tidak ada** (K59 e) dan ketiadaannya disebut di konfirmasi, pesan hasil, dan daftar. **Dua cacat ditutup dan satu biaya dihapus:** (1) `mkdir` folder tujuan ada **di luar** `try` → kegagalan yang paling mungkin (folder bukan folder / tidak bisa ditulis) keluar sebagai traceback, dan pada jalur sebelum-migrasi berbunyi `MEJASAHAM_DATA` (variabel yang salah) — kini `GalatCadangan` menyebut folder tujuannya + `--folder-cadangan`/`MEJASAHAM_BACKUP`; (2) konfirmasi untuk cadangan tidak lagi berbunyi "tulis baris ini ke basis data" (`PermintaanTulis.pertanyaan`); (3) `PanelDasbor.sesudah_tulis` memuat ulang dasbor sesudah tiap penulisan, dan cadangan ikut membayarnya padahal ia tidak mengubah baris — `PermintaanTulis.muat_ulang=False` untuk cadangan → terukur **54,46 → 3,34 dtk** (basis data 231 MB; `cadangan.buat` 1,26 dtk vs pemuatan ulang dasbor 63,83 dtk), dan cadangan sementara penulis lain memegang kunci tulis **62,42 → 2,59 dtk** (cadangan **tidak menunggu kunci tulis** — ia hanya membaca). **+14 uji**, suite **863 lulus**; seluruh 14 uji baru **terbukti gagal pada HEAD**, dan uji pemuatan ulang juga lewat **mutasi terarah** (berkas dipulihkan byte-identik). Bukti: kedua cadangan (jendela & CLI) **byte-identik**, integritas `ok`, **1.008.187 baris sama**, 23 berkas sama, baris daftar sama persis, dan cadangan buatan jendela **dipulihkan** ke folder bersih; 4 tangkapan layar `offscreen` **dilihat** — layar sungguhan di monitor Anda tetap belum pernah dilihat | `mejasaham/{cadangan,cli}.py`, `mejasaham/ui/{tulis,jendela}.py`, `tests/test_cadangan.py` (7), `tests/test_ui_tulis.py` (25), `tests/test_ui_jendela.py` (41) | `pytest tests\test_cadangan.py tests\test_ui_tulis.py tests\test_ui_jendela.py -q` (73 lulus); `python .uji-data\riset-idx\cadangan-jendela\bukti-cadangan-jendela.py` → "cadangan byte-identik + daftar sama"; `python .uji-data\riset-idx\cadangan-jendela\tangkap-layar-19c.py` → 4 PNG; bukti `.uji-data\uji-cadangan-jendela\bukti\` |
| 19d | ~~**`ubah-stop` + keputusan right issue dari jendela**~~ (**K62**; T71 c) **SELESAI 17 Okt 2026 (sesi 18) → T74; dua temuannya diperbaiki sesi 20 (#24/#25, T75)** | **Formulir "Ubah stop" di layar 11.1** (posisi dipilih **dari daftar** posisi aktif, K64/K65; `tgl_stop` = tanggal yang dinyatakan pengguna, kosong = hari ini, dan ditulis apa adanya di konfirmasi) dan **tabel hak right issue + formulir keputusan di layar 11.3** (`tebus`/`jual_hmetd`/`abaikan`; isian yang tidak dipakai pilihan aktif dimatikan **dan** dikosongkan; kotak `tebus` hanya berisi transaksi **beli** posisi yang barisnya dipilih). Memakai `posisi.ubah_stop` dan `posisi.catat_keputusan_right_issue` yang sudah ada — **bukan** jalur kedua; `sumber` barisnya sama dengan baris perintah, jadi barisnya identik. `tebus` tetap hanya **menunjuk** transaksi yang sudah tercatat (T51) dan jendela **tidak** mencatatkannya diam-diam; `gagal` karena isian ditolak **sebelum** dialog konfirmasi. Dua pesan tindakan menunggu (`tanpa_stop`, `right_issue_belum_diputuskan`) berhenti menyuruh pindah ke baris perintah — sekarang menyebut kedua jalan. **+16 uji**, suite **879 lulus**; **mutasi terarah 5/5** (berkas dipulihkan byte-identik) membuktikan uji barunya bergigi. **Dua temuan sesi 18 sudah diperbaiki sesi 20 (#24/#25, T75):** `tebus` di inti dulu membuang `--lembar`/`--harga`/`--biaya` diam-diam pada jalur baris perintah, dan `catatan` keputusan right issue dulu menggelembung tiap revisi | `mejasaham/ui/tulis.py`, `mejasaham/ui/tabel.py`, `mejasaham/ui/jendela.py`, `mejasaham/dasbor.py` (dua kalimat pesan), `tests/test_ui_tulis.py` (8), `tests/test_ui_tabel.py` (3), `tests/test_ui_jendela.py` (5), `tests/test_dasbor.py` | `pytest tests\test_ui_tulis.py tests\test_ui_tabel.py tests\test_ui_jendela.py -q` (92 lulus, **4× berturut-turut** tanpa proses yang mati); `python .uji-data\riset-idx\stop-right-jendela\bukti-stop-right-19d.py` → **HASIL: LULUS** (ketiga view SAMA antara jendela & baris perintah); `python .uji-data\riset-idx\stop-right-jendela\tangkap-layar-19d.py` → 6 PNG; `python .uji-data\riset-idx\stop-right-jendela\uji-mutasi-19d.py` → **HASIL: LULUS**; bukti `.uji-data\uji-stop-right-jendela\bukti\` |
| 20 | ~~**Dasbor menampilkan IHSG + rezim pasar + breadth** (**K58**, T66)~~ **SELESAI 17 Okt 2026 (sesi 10)** | `dasbor.susun` **memanggil** `metrik.breadth` + `metrik.rezim_pasar` lewat `_konteks_pasar` (potret → `metrik_semua` → `saring.semesta_likuid` → breadth → rezim) dan menyimpannya di `Dasbor` (`pasar`, `breadth`, `rezim`, `preset_pasar`); kalimat tetap yang salah **dibuang**; preset yang dipakai = preset yang menghasilkan skor tersimpan (bila belum ada: bawaan `--saring`), dan tanpa preset sama sekali breadth dinyatakan **tidak dihitung beserta sebabnya**. Terukur pada salinan `.uji-data/uji-jurnal` → `.uji-data/uji-dasbor`: `--saring` **dan** `--dasbor` berbunyi **`88 dari 225 emiten likuid · breadth 39,1% · rezim RISK-OFF`** dengan `IHSG 6.093 (+62 / +1,03%)`; pada kode lama dasbor 2,8 dtk tanpa baris `Pasar` dan dengan kalimat salah itu. **Dua temuan:** (a) **biaya** — `--dasbor` **2,8 → 33–61 dtk** pada basis data 999.421 bar (setara `--saring`, yang angkanya sendiri tidak berubah); (b) **cacat PySide6 6.12.0 + CPython 3.14.7** yang tersingkap pekerjaan baru di utas pekerja (uji jendela mati secara native 7/18 jalan; 0/12 bila GC dimatikan) → ditangkal **T68** (`gc.disable()` selama tugas `Pekerja.run`) dengan bukti angka yang memisahkan sebab dari kebetulan | `mejasaham/dasbor.py`, `mejasaham/metrik.py` (`INDEKS_ACUAN`), `mejasaham/tampilan.py` (`bertanda`), `mejasaham/ui/pekerja.py` (T68), `tests/test_dasbor.py` (22, +6), `tests/test_ui_jendela.py` (22, +4) | `python -m pytest` → **803 lulus** (tiga kali); `--saring` vs `--dasbor` atas `.uji-data/uji-dasbor` harus berbunyi sama; bukti `.uji-data\uji-dasbor\bukti\` + pembuatnya `.uji-data\riset-idx\dasbor\bukti-dasbor.py` |
| 21 | ~~**Kerangka `rasio-bank.csv` dari daftar emiten bank** (**K57**, T67)~~ **SELESAI 17 Okt 2026 (sesi 10)** | Perintah baru **`--kerangka-rasio-bank`** menulis `rasio-bank.csv` di folder konfigurasi: satu baris per kode ber-`jenis='bank_keuangan'` pada revisi terkini, **seluruh sel selain `kode` kosong**, bentuk kolomnya dipinjam dari `berkas.SPESIFIKASI["rasio_bank"]` (bukan bentuk kedua), dan berkasnya **tidak** diimpor (baris berasio kosong memang ditolak pembacanya). Terukur atas `.uji-data/uji-jenis`: **49 baris** (AGRO … SUPA), sel terisi selain `kode` **0**, `--impor` atas kerangka kosong **keluar 1** dengan pesan per baris (`rasio-bank.csv baris 36: kolom `periode` wajib diisi`) dan `rasio_bank` tetap **0 baris**, `--saring` tetap jalan. **Tanpa `jenis` terisi**: melaporkan jalan keluarnya (`--ambil-jenis` + `--impor`), bukan menulis kerangka kosong. **Berkas tujuan yang sudah berisi ditolak** (kecuali masih template bawaan AC-12): berkas itu diisi manusia dari publikasi resmi, jadi tidak ditimpa diam-diam. +5 uji di `tests/test_jenis_emiten.py`; satu cacat ditemukan uji itu sendiri (perintahnya sempat jalan **dua kali** karena dispatch ganda) | `mejasaham/jenis.py` (`kode_bank`, `tulis_kerangka_rasio_bank`), `mejasaham/cli.py`, `tests/test_jenis_emiten.py` (38) | `python -m pytest` → **810 lulus**; `--kerangka-rasio-bank --folder-data .uji-data/uji-jenis`; bukti `.uji-data/uji-kerangka-rasio-bank/bukti/` + pembuatnya `.uji-data/riset-idx/kerangka-rasio-bank/bukti-kerangka.py` |
| 22 | **Langkah cacat PySide6 6.12.0 + CPython 3.14.7** (lapor upstream / uji versi) | **Berjalan menurut K60/K66/K67/K69. (a) laporan upstream: berkas siap kirimnya sudah ada** — `docs/laporan-pyside6-siap-kirim.md`; **19 Okt 2026 berkas itu diperbarui** dengan pengukuran K69 (kontrol yang gagal + lampiran "sisa suite uji"), jadi ia kini punya kontrol yang bisa ditunjukkan ke pelacak Qt. **Pengirimnya Anda** (K66); sesudah terkirim, tautannya dicatat di `docs/riset-pyside6-gc-2026-10.md`. **(b) uji Python 3.13: SUDAH — 8.5 inkonklusif, lalu K69 dijalankan 19 Okt 2026:** reproduksi ulang **berhasil** (suite penuh 12× tanpa penangkal di 3.14.7 → **2 mati**, `Fatal Python error: Aborted`), A/B di 3.13.14 → **0 mati**; rincian + buktinya di riset **bagian 10**. **Keputusan pin versi Python kini = U31** (rekomendasi sesi 21: **jangan pin sekarang** — 2 vs 0, p ≈ 0,48), **belum** diputuskan. **Yang tersisa:** (a) laporan dikirim pengguna; **(c) uji versi PySide6 lain TIDAK dipicu** (hanya bila reproduksi gagal atau A/B seri). **T68 tetap dipakai** | (a) tidak ada berkas repo yang berubah (cukup tautan laporannya dicatat); (b/c) `.tmp/py313` (769 MB, gitignored — **dibangun ulang 19 Okt 2026 dalam 10,7 dtk dari cache uv**; cabut dengan `uv python uninstall 3.13` + hapus folder) | (b) sudah dijalankan: `.\.venv\Scripts\python .tmp\k69-jalankan.py 12` → 2 mati; `.tmp\py313\Scripts\python .tmp\k69-jalankan-313.py 12` → 0 mati; `.\.venv\Scripts\python .tmp\k69-ringkas.py` → `bukti-k69.txt` |
| 21b | **Isi `rasio-bank.csv` dari publikasi resmi bank/OJK** (K68/P39; lanjutan aksi #21; **bentuk pelaksanaannya K76**) | **PILOT DIJALANKAN 19 Okt 2026 (sesi 25); KEDUA BARISNYA DIIMPOR 19 Okt 2026 (sesi 31, aksi #29): 2 bank terbaca, 3 tidak.** Hasil: **BBCA** 30 Jun 2026 (NPL gross 1,86% · KPMM 26,79% · BOPO 41,22% · NIM 5,32%; publikasi 28 Jul 2026) dan **BRIS** 30 Jun 2026 (KPMM 20,41 · BOPO 69,71; NPF gross 1,80% & Net Imbalan 5,42% **tidak** dipetakan ke NPL/NIM), keduanya dengan `url`/`tanggal_akses`/`kutipan`; **BMRI/BBNI/BBRI tidak terbaca** (`robots.txt` `Disallow: /*.pdf$` · `Disallow: /Portals/` + Incapsula · robots tak terbaca + dokumen resmi yang bisa dibaca **tidak memuat BOPO/NIM**). Berkas: `docs/rasio-bank-kandidat-2026-10.md`, `.uji-data/riset-idx/rasio-bank/`; **tidak ada** yang masuk `konfigurasi/rasio-bank.csv`/`--impor`. **Pekerjaan berikutnya:** **K80** — ~~**(1) aksi #27** (K78: `sumber` per baris)~~ **(selesai 19 Okt 2026, sesi 27 → T77)**, (2) ~~verifikasi angka~~ **SELESAI 19 Okt 2026 (sesi 31, aksi #29/T79): 14/14 sel cocok**, (3) ~~isi CSV → `--impor` → periksa~~ **SELESAI: 2 baris `rasio_bank` masuk (snapshot 12), `v_rasio_bank_terkini` memuat keduanya; `--saring` belum berubah karena `jenis` kosong**, (4) **berikutnya**: putuskan 44 bank. **Empat keputusan sesudahnya sudah dikunci 19 Okt 2026 (sesi 26): K77** (NPF/NI tidak dipetakan), **K78** (U33 → #27), **K79** (tiga bank tidak diakali), **K80** (urutan). **Temuan yang harus dibaca sebelum berharap bank masuk peringkat:** pada snapshot #8 (49 bank), **0 bank tertahan *hanya* oleh rasio bank** — keempat rasio tidak dinilai pada ke-49 bank, tetapi 34 bank juga gagal `adtv20`, 40 gagal `tren_ma200`, 19 gagal `kekuatan_relatif`, dan `roe_5t`/`per_relatif_sektor`/`pbv_relatif_sektor` juga lubang; **bank pilot pun** masih gagal `tren_ma200` (BBCA juga `pbv_relatif_sektor`, BRIS juga `kekuatan_relatif`). **Jadi mengisi rasio saja tidak cukup** | `.uji-data/riset-idx/rasio-bank/` (skrip + berkas kandidat), `konfigurasi/rasio-bank.csv` (**hanya sesudah verifikasi**), `mejasaham/jenis.py` (kerangka sudah ada) | Bukti lingkup: `.uji-data/uji-lingkup-p39/bukti-lingkup-p39.txt` + `.uji-data/riset-idx/rasio-bank/lingkup-p39.py`; untuk pengisian: berkas kandidat + kutipan resmi diperiksa pengguna sebelum `--impor`, dan `uji-baca-kandidat.py` → **LULUS** (`.uji-data/riset-idx/rasio-bank/bukti-uji-baca.txt`) |
| 23 | ~~**Simpan konteks pasar saat `--saring`**~~ (usulan **U26**; **K61**) | **SELESAI 19 Okt 2026 (sesi 34) → T80.** `--saring` (hanya bila `simpan=True`) menulis breadth + rezim + penutupan indeks terakhir ke tabel **`konteks_pasar`** (migrasi 015); dasbor membacanya hanya bila **`id_snapshot` + `id_preset` + `sumber_harga` + `versi_hitung`** semuanya sama — keempatnya di WHERE, bukan pencocokan di Python — dan selain itu **menghitung ulang** lewat jalur yang sama dengan saringan. `--kode` (`simpan=False`) tidak menulis konteks; kegagalan menulis konteks menjadi **peringatan** (saringan tetap sah, dasbor menghitung ulang), bukan pembatalan. **Terukur atas salinan data kerja (snapshot 13):** `--dasbor` **18,95 dtk → 0,74 dtk (25,7×)**, baris `Pasar` **identik** sebelum/sesudah, `--saring` **18,16 dtk**; suite **906 lulus**; 5 uji perilaku **gagal pada worktree `HEAD` `6888b1b`** | `mejasaham/skema.py` (migrasi 015), **`mejasaham/konteks_pasar.py` (baru)**, `mejasaham/pengatur.py`, `mejasaham/dasbor.py`, **`tests/test_konteks_pasar.py` (baru, 9 uji)**, `tests/test_dasbor.py` (+9), `tests/test_db.py` (+1) | `pytest` → **906 lulus**; `pytest tests\test_konteks_pasar.py tests\test_dasbor.py -q`; `python .uji-data\riset-idx\k61\ukur-k61.py`; bukti `.uji-data/uji-k61/bukti/` (`bukti-k61.txt`, `uji-jendela-6x.txt`, `uji-baru-pada-head-*.txt`) |
| 24 | **Keputusan `tebus` menolak `--lembar`/`--harga`/`--biaya` yang tidak dipakainya** (**K71**; temuan sesi 18) | **SELESAI 19 Okt 2026 (sesi 20) → T75.** Dulu baris perintah **membuang isian itu diam-diam**: `posisi.catat_keputusan_right_issue` hanya memeriksanya untuk keputusan **selain** `tebus` — terukur di sesi 18: `--putuskan-right-issue MLPT --keputusan tebus --id-transaksi 6 --lembar 500` **keluar 0** dan lembarnya hilang tanpa satu pun pesan. Kini inti memakai **satu** pemeriksaan (`_tolak_isian_yang_tidak_dipakai`) untuk **semua** keputusan selain `jual_hmetd`, **termasuk `tebus`**, dengan pesan yang menyebut bahwa yang menaikkan lembar adalah `transaksi` (T51) | `mejasaham/posisi.py` (`catat_keputusan_right_issue`, `_tolak_isian_yang_tidak_dipakai`), `tests/test_aksi_korporasi_posisi.py` (2 uji baru) | **Terukur:** `pytest` → **882 lulus**; kedua uji baru **terbukti gagal pada worktree `HEAD`**; `--putuskan-right-issue … --keputusan tebus --lembar …` kini **keluar 1** dengan pesan itu dan `keputusan_right_issue` tetap **0 baris**; jendela tetap menolaknya lebih dulu (`tests/test_ui_tulis.py::test_keputusan_right_issue_menolak_isian_yang_tidak_dipakai`) |
| 25 | **`catatan` keputusan right issue berhenti menggelembung tiap revisi** (**K72**; temuan sesi 18) | **SELESAI 19 Okt 2026 (sesi 20) → T75.** Dulu tiap revisi menyambung catatan lama **plus** catatan turunan (`catatan_kaki`) yang kalimatnya **sama lagi** — terukur di sesi 18: revisi ke-5 memuat kalimat *"tenggat right issue ini belum dinyatakan sumbernya"* **lima kali** (terlihat di keluaran `--putuskan-right-issue` dan di layar 11.3). Kini catatan turunan dibandingkan **per baris** dengan catatan revisi sebelumnya: kalimat yang sudah ada tidak ditambahkan lagi, sedangkan catatan yang **dinyatakan pengguna** dan `pesan_revisi` tetap disambung apa adanya — riwayat lengkap sudah tersimpan di baris revisinya masing-masing (append-only) | `mejasaham/posisi.py` (`catat_keputusan_right_issue`), `tests/test_aksi_korporasi_posisi.py` (uji baru) | **Terukur:** `pytest` → **882 lulus**; uji `test_catatan_turunan_tidak_diulang_tiap_revisi` **terbukti gagal pada `HEAD`** (kalimat turunan muncul 2× pada revisi ke-2) dan lulus sesudah perbaikan (muncul **sekali** di tiap revisi; catatan pengguna tetap bertambah apa adanya); riwayat revisi (baris lama) **tidak berubah** |
| 26 | ~~**Perbaiki uji impor yang bergantung detik**~~ (usulan **U32** → **K75**, bentuk teknis **T76**; ditemukan sesi 21 saat menjalankan K69) | **SELESAI 19 Okt 2026 (sesi 23) → T76.** `tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah` dulu membandingkan baris `snapshot` **termasuk `jam_ambil`/`batas_diketahui`** milik **dua impor terpisah**, jadi gagal bila keduanya melewati batas detik walaupun datanya sama (terukur **1 dari 12** jalan suite penuh, `…T04:43:32+07:00` vs `…T04:43:33+07:00`). Kini kedua kolom waktu itu **dikeluarkan** dari pembandingan `snapshot` (konstanta `KOLOM_WAKTU_IMPOR` + helper `_snapshot_tanpa_waktu_impor()` yang dipakai **hanya** uji itu; helper `_baris()` bersama tidak diubah), kolom lain tetap **penuh** dan himpunannya ditegaskan di uji itu; "bekukan jam" lewat `db.waktu_iso` tetap **ditolak** (menuntut menambal `db` **dan** `ingesti`) | `tests/test_ui_tulis.py` (satu uji + konstanta + helper) | **Terukur:** jam dipaksa melewati batas detik → versi `HEAD` **gagal** (hanya dua kolom waktu yang berbeda), versi K75 **lulus**; mutasi "pembanding dibuang terlalu lebar" **tertangkap** (`jumlah_emiten`); `tests/test_ui_tulis.py` **12 dari 12** jalan lulus; suite penuh **882 lulus**. Bukti `.uji-data/uji-k75/bukti/` (`bukti-ringkas.txt` + empat berkas bukti), plugin `.uji-data/riset-idx/k75/plugin_detik.py` |
| 27 | ~~**`sumber` per baris `rasio-bank.csv` dipakai, bukan dibuang**~~ (**U33 → K78**, sesi 26; ditemukan saat pilot #21b) | **SELESAI 19 Okt 2026 (sesi 27) → T77.** Dulu `berkas._baris_rasio_bank` **tidak mengisi** `sumber` (kelas `RasioBank` tidak punya bidang itu), sehingga `ingesti._baris_rasio_bank` menulis `kumpulan.sumber` = `impor berkas: <folder>` — asal tiap publikasi bank hilang saat impor, padahal kolom itu **wajib** di berkas. Kini bidang `sumber` ada di `RasioBank`, diisi dari kolom berkas (`_tidak_kosong`, sama seperti `fundamental` sejak K18), dipakai `ingesti` (`satu.sumber or kumpulan.sumber`), dan **dikembalikan `potret`** saat baris dibaca; sel `sumber` kosong di berkas kini **ditolak per baris** dengan pesan yang menyebut kolomnya (dulu diterima tanpa diperiksa karena dibuang). **Tiga uji baru** — dua bank bersumber berbeda dalam satu berkas → tiap baris menyimpan sumbernya sendiri; sel kosong ditolak; `RasioBank` tanpa sumber tetap memakai label kumpulan. **Bukti:** ketiganya **gagal pada worktree `HEAD` `97d749e`**, **mutasi terarah 2/2 tertangkap** (berkas dipulihkan byte-identik), suite **885 lulus**; bukti di `.uji-data/uji-k78/bukti/` | `mejasaham/ingesti.py` (`RasioBank`, `_baris_rasio_bank`), `mejasaham/berkas.py` (`_baris_rasio_bank`), `mejasaham/potret.py` (pembacaan ulang), `tests/test_impor_berkas.py` (2), `tests/test_ingesti.py` (1) | **Terukur:** `.\.venv\Scripts\python -m pytest` → **885 lulus**; uji `test_sumber_per_baris_rasio_bank_tersimpan_dan_kembali_lewat_potret` + `test_rasio_bank_tanpa_sumber_ditolak_menyebut_kolomnya` + `test_sumber_baris_rasio_bank_dipakai_dan_kosong_jatuh_ke_label_kumpulan` **gagal pada HEAD** (`3 failed`) dan lulus sesudah perbaikan; bukti `.uji-data/uji-k78/bukti/bukti-ringkas.txt` |
| 28 | ~~**`potret._fundamental` juga membawa `sumber` per baris saat membaca ulang**~~ (**K82**, dikunci sesi 28) | **SELESAI 19 Okt 2026 (sesi 29) → T78.** `potret._fundamental` dulu tidak meneruskan `sumber` dari baris basis data, sehingga `Fundamental.sumber` (ada sejak K18) selalu `None` di `Potret` walaupun kolomnya `NOT NULL` dan barisnya menyatakan asalnya — asimetri yang sama dengan K78, hanya berpindah tempat. Kini `_fundamental` mengisi `sumber=baris["sumber"]` (satu baris; **jalur tulis tidak disentuh**). **Dua uji baru**: sumber per baris yang berbeda antarpublikasi (BBCA vs BRIS) ikut kembali lewat `potret.muat`, dan baris yang dibentuk **tanpa** `sumber` kembali sebagai **label kumpulan**, bukan `None`. **Bukti:** keduanya **gagal pada worktree `HEAD` `97d749e`** (`[None] == [<sumber baris>]`, bukan `AttributeError`), **dua mutasi terarah tertangkap** (`sumber=None`, `sumber=baris["asal_tgl_publikasi"]`), berkas dipulihkan byte-identik, suite **887 lulus**. **Sesudahnya berhenti** menunggu verifikasi pengguna (K80 langkah 2); 44 bank dan #23 tidak dimulai tanpa permintaan | `mejasaham/potret.py` (`_fundamental`), `tests/test_potret.py` (2 uji) | **Terukur:** `.\.venv\Scripts\python -m pytest` → **887 lulus**; uji `test_sumber_fundamental_per_baris_ikut_kembali_lewat_potret` + `test_fundamental_tanpa_sumber_memakai_label_kumpulan_saat_dibaca_ulang` **gagal pada HEAD** (`2 failed`) dan lulus sesudah perbaikan; bukti `.uji-data/uji-k82/bukti/` |
| 29 | **Verifikasi ulang angka `rasio_bank` oleh agen + isi CSV + `--impor` bila cocok** (**K83**, dikunci sesi 30; lanjutan K80 langkah 2–3) | **SELESAI 19 Okt 2026 (sesi 31) — 14/14 sel cocok persis, impor dijalankan (T79).** SHA-256 kedua PDF = manifest, halaman dirender ulang (bukan PNG pilot), setiap sel `kandidat-rasio-bank.csv` (empat rasio, `periode`, `tgl_publikasi`, `sumber`) dibandingkan dengan yang tercetak — **kolom BRIS diputuskan dari render**, karena lapisan teks menaruh 2025 lebih dulu. Cadangan dibuat lebih dulu (`.uji-data\mejasaham-cadangan\20261019T181212314095+0700`), dua baris ditulis ke `konfigurasi/rasio-bank.csv` di folder data (sembilan kolom; tiga kolom pemeriksaan dibuang; dua kalimat `keterangan` basi dibersihkan), berkas **dibaca ulang** lewat `berkas.baca_folder`, lalu `--impor` keluar 0 → **snapshot 12**. **Dua catatan:** impor satu folder juga menulis ulang `sumber` **2328** baris `notasi_khusus` (hanya kolom itu; bagian 6), dan **U34** mencatat tanggal BRIS 21 Agu vs 24 Agu (`Last-Modified`) | `konfigurasi/rasio-bank.csv` di folder data (`.uji-data/mejasaham/konfigurasi/`), basis data kerja, `docs/keputusan.md` bagian 5 (catatan sesi pelaksanaan), `docs/arsitektur.md` (**T79**) | **Terukur:** hash PDF = manifest (2/2); **14/14 sel** cocok; `--impor` keluar 0 dengan `rasio_bank` **0 → 2**; `v_rasio_bank_terkini` = BBCA 186/2679/4122/532 bp dan BRIS `None`/2041/6971/`None` bp, `sumber` per baris; `--saring` **tidak berubah** (973 emiten, 9 lolos/9 dinilai) karena `jenis` 973 emiten kosong dan BBCA/BRIS gagal `coverage`; `PRAGMA integrity_check` = `ok` |
| 31 | Tahap 5 — bundel PyInstaller onedir (T3) | **Bundel, ikon, dan perbaikan pemuatan Qt selesai 22 Okt 2026 (sesi 37; T81/T82/T83).** PATH build dibatasi agar DLL ICU milik Poppler tidak terkumpul. Build keluar 0 (EXE 15,5 MiB); --help keluar 0; GUI hidup 8 detik pada uji offscreen; suite 911 lulus. **Berikutnya:** pengguna mencoba EXE baru lewat klik-ganda. | requirements-build.txt, tools/build_exe.py, tools/generate_icon.py, tools/entry_exe.py, assets/mejasaham.svg, assets/mejasaham.ico, mejasaham/ui/jendela.py, tests/test_pengemasan.py, tests/test_ui_jendela.py, README.md, docs/arsitektur.md (T82/T83), docs/keputusan.md, docs/lanjutan.md | .\.venv\Scripts\python tools\build_exe.py; .\.venv\Scripts\python -m pytest (911 lulus)
| 30 | **Perluasan `rasio-bank.csv` ke 44 bank lain** (K80 langkah 4; **K87**) | **44 DOKUMEN MASIH DITUNDA — tetapi prasyaratnya SUDAH DIJALANKAN 19 Okt 2026 (sesi 32).** `jenis` kini terisi: **49 bank_keuangan · 862 umum · 62 kosong** (snapshot 13), dan `--saring` **menerapkan** kriteria bank untuk 49 bank (BBCA keempat rasio lolos; BRIS `car`+`bopo`; K77) serta berhenti menghitung DER/coverage/CFO-NI untuk bank (PRD 8.4). **47 dari 49 bank belum punya rasio** — alasan `tidak bisa dinilai` berbunyi *"rasio bank (NPL/CAR/BOPO/NIM) belum diimpor lewat rasio-bank.csv"*, jadi **itulah** yang akan diisi oleh 44 dokumen. **Peringkat tidak berubah** (9 lolos/9 dinilai; sembilan kandidat sama) — K68 terbukti lagi, dan itulah alasan penundaan K87 tetap berdiri. **Yang belum:** hitung bank yang menuntut langkah manual (K79), lalu putuskan 44 dokumen | `konfigurasi/rasio-bank.csv` (folder data), `konfigurasi/emiten.csv` (sudah diisi sesi 32), basis data kerja | **Terukur sesudah sesi 32:** `--saring` menyebut **49 bank_keuangan** dan NPL/CAR/BOPO/NIM **dinilai** untuk BBCA (186/2679/4122/532 bp); 47 bank menjawab `tidak bisa dinilai` dengan alasan rasio belum diimpor; `v_rasio_bank_terkini` tetap 2 baris |

### 2.1a P22 sudah diukur sampai dasar (10 Okt 2026) — yang tersisa satu keputusan dependensi

Ini menggantikan dugaan "butuh peramban" yang tertulis di 2.1. Tiga hal sudah **dibuktikan
dengan percobaan**, bukan disimpulkan:

1. **Tidak butuh peramban.** `urllib` dari pustaka standar mengunduh katalog laporan bank
   (BCA: HTTP 200, 118.487 byte HTML, 30 tautan PDF; Mandiri: HTTP 200) **dan** berkas PDF-nya
   (Laporan Eksposur Risiko & Permodalan BCA: HTTP 200, `application/pdf`, 3.893.640 byte,
   berkas benar-benar diawali `%PDF-`). Jadi ketergantungan peramban yang dikhawatirkan di 2.1
   **tidak diperlukan** untuk jalur ini — `requests` gagal di IDX, tetapi situs bank tidak
   memakai Cloudflare.
2. **Sebagian PDF bisa diurai dengan stdlib saja.** Pengurai teks buatan sendiri (dekompresi
   `zlib` + operator `Tj`/`TJ`/`Td`) membaca **8.473 karakter** dari laporan publikasi bulanan
   BCA dan **8.081 karakter** dari Mandiri, teks Indonesia yang benar — cukup untuk tabel neraca
   ("9.Kredit dan pembiayaan yang diberikan923.096.220").
3. **Tetapi dokumen yang memuat rasionya tidak.** Laporan Eksposur Risiko & Permodalan memakai
   font **CID (Type0/CIDFontType2)** dengan `/ToUnicode` — 44 rujukan `/ToUnicode` dan 44
   `/Encoding` di dalam berkas. Artinya teksnya **ada dan bisa dipulihkan**, tetapi hanya lewat
   pemetaan glyph→huruf yang benar. Pengurai buatan sendiri menghasilkan 113.115 karakter
   **sampah**, dan menerka pemetaannya (mis. "geser −4") sudah dicoba dan **gagal**. Menebak di
   sini bukan pilihan: satu tebakan yang salah membalik **semua angka** rasio tanpa satu pun
   galat — persis kegagalan yang paling mahal di proyek ini.

**Kesimpulan yang jujur:** jalurnya **layak** (sumbernya resmi — publikasi bank itu sendiri,
bukan pihak ketiga; berkasnya bisa diunduh; isinya ada), dan yang menghalangi hanyalah **satu
dependensi pengurai PDF**. Karena menambah dependensi adalah keputusan pengguna, aksi #0
diajukan sebagai pertanyaan — dan **dijawab 10 Okt 2026 → K24: rasio bank diisi manual**, jalur
otomatisnya tidak dibangun sekarang. Alasan yang dipakai saat memutuskan, supaya tidak
ditawarkan ulang tanpa alasan baru: taruhannya besar dan tidak terlihat (satu pemetaan glyph yang
salah membalik **semua angka** rasio tanpa satu pun galat) sedangkan hasilnya kecil (4 metrik
untuk ~15 bank dari ~975 emiten) dan biayanya berulang **per bank per periode**. Yang tidak
dikerjakan karena keputusan yang sama: daftar emiten papan pemantauan khusus, sebab narasinya
HTML tetapi daftarnya di lampiran PDF.


**Baru dicatat (10 Okt 2026, tanpa perubahan kode): jawaban pengguna atas P20–P22 masuk** —
broker **Stockbit**, slippage **`tick`**, `jenis` emiten **boleh diturunkan dari data** (hanya
`bank_keuangan`, berlabel sumber), dan `notasi-khusus.csv` + `rasio-bank.csv` **tidak dimiliki
pengguna → dicarikan aplikasi** (P22, sekarang jadi aksi #0 di bagian 4). Keputusannya: **K20, K21**
di `docs/keputusan.md`; pertanyaan lama sudah kosong. Yang tersisa dari pekerjaan sebesar ini:
**tarif Stockbit belum diambil**, jadi entri `[[biaya_broker]]` sengaja masih kosong dan kalkulator
biaya menolak menghitung.

**Sebelumnya (10 Okt 2026): "0 kandidat" dibuka tanpa berkas dari manusia** — dan yang
membukanya bukan tebakan, melainkan pembuktian bahwa catatan lama P2 salah. Terukur: sumber data
EOD yang sudah dipakai harga **memuat laporan keuangan tahunan** (4–5 tahun) dan turunannya benar
(arus kas operasi cocok dua jalur independen, selisih **0,0%**). Jalur barunya `--ambil-fundamental`
(K18) menulis `fundamental.csv` lalu `--impor` memuatnya — pola sama dengan K11/K12/K16, sehingga
penulisan basis data tetap satu jalur dan angkanya bisa diperiksa manusia lebih dulu. Hasil atas
data nyata: **794 baris / 200 emiten**, menghasilkan **9 emiten lolos** dan daftar peringkat —
tetapi **kata "kandidat" ditahan** (K19), sebab `notasi-khusus.csv` belum ada, dan itu disebut
mencolok di keluaran. Dua cacat yang ditemukan sekaligus ditutup: (a) tabel notasi yang **kosong**
dulu diperlakukan sebagai **bersih** (kriterianya `lolos=True` untuk seluruh semesta) — sekarang
tidak diterapkan dan peringkatnya disebut "sementara", dengan dua uji yang **terbukti gagal pada
kode lama**; (b) kolom `sumber` per baris di `fundamental.csv` dulu divalidasi lalu **dibuang**,
sehingga label "tidak resmi" akan hilang tepat pada data yang paling perlu ditandai. Rincian
keputusan: **K18, K19, P20** di `docs/keputusan.md`; bukti: `.uji-data/uji-fundamental/`,
`.uji-data/bukti-migrasi-007.txt`, `.uji-data/bukti-saring-fundamental.txt`.

**Baru selesai (9 Okt 2026): imbal hasil SUN & kalender 2025** — permintaan Anda "cari atau bikin
berkas yang dibutuhkan sendiri" dijawab dengan penelusuran **terukur**, bukan berkas karangan.
Dua berkas berhasil: (1) **`imbal-hasil-sun.csv`** dari kurva imbal hasil SBN halaman HPW
**PHEI** (`--ambil-sun`, K16) — terukur SUN 10 tahun 7,1845% → 718 bp; (2) **kalender 2025**
terisi 25 tanggal libur lewat revisi pengumuman KSEI yang lebih lama, karena tanggalnya terbukti
identik dengan revisi terakhir (K17). Kalender kini **2025–2027 = 1095 baris**. Yang tetap tidak
bisa: `fundamental.csv`, `rasio-bank.csv`, `notasi-khusus.csv` (seluruh jalur IDX 403) dan kalender
2021–2024 (berkasnya sudah 404, Arsip Internet hanya menyimpan salinan terbaru). Sekaligus
dikonfirmasi pengguna: **K14** (P17), **K15** (P18). Rincian di `docs/keputusan.md` bagian 5
(Tahap 1 — langkah 10), 3.5, dan 5.1; keputusan teknisnya T32–T33 di `docs/arsitektur.md`.

**Sebelumnya (9 Okt 2026): satu label sumber harga per snapshot (cacat P17 ditutup)** — begitu
harga pembanding PRD 7.3 diimpor, angka saringan rusak **diam-diam**: dua bar tanggal sama dari dua
sumber masuk ke satu deret, hari yang terduplikasi memakan slot jendela 20 hari, dan ADTV20 emiten
itu jatuh "tidak dihitung" (terukur waktu itu: likuid 235 → 215). Sekarang `potret.muat` membaca
**satu** label — label dengan riwayat bar terbanyak, dihitung pada saat snapshot, dilaporkan
beserta label yang tidak dipakai, dan bisa ditimpa `--sumber`. Terverifikasi atas data nyata pada
salinan basis data yang sama dengan bukti langkah 6: `--saring` kembali berbunyi **likuid 235**,
dan `--cek-sumber-kedua` keluarannya identik dengan bukti lama. Sembilan uji baru
(`tests/test_sumber_harga.py`), dan dua uji regresinya **dibuktikan gagal pada kode lama** lebih
dulu (likuid 10 → 0; ADTV20 Rp 10 miliar → Rp 10,5 miliar). Rinciannya di `docs/keputusan.md`
bagian 5 (Tahap 1 — langkah 9), keputusan teknisnya **T32** di `docs/arsitektur.md`.

**Sebelumnya (9 Okt 2026): pengambil kalender libur bursa dari KSEI (K11)** — `--ambil-kalender`
mengunduh pengumuman hari libur & cuti bersama KSEI, mengurai PDF-nya **tanpa dependensi baru**
(`zlib` + `re` bawaan), lalu menulis `kalender-bursa.csv`; hari bursa diturunkan sebagai hari kerja
dikurangi libur resmi. Terverifikasi atas sumber nyata: **730 baris** (2026: 22 libur resmi, 239
hari bursa; 2027: 20 libur, 241 hari bursa), terbaca ulang seluruhnya, impor idempoten, dan
laporan mutu berhenti mengatakan `kalender_bursa_kosong` (hari bursa terakhir 2026-10-09).
Dua temuan yang mengubah perilaku: (a) berkas 2025 **tidak** menyatakan menindaklanjuti kalender
libur bursa IDX — yang dirujuknya kalender EBA/sukuk — jadi tahun itu **ditolak** dan dilaporkan
(T31); (b) "hari bursa terakhir" kini dibatasi pada hari yang sudah lewat, sebab kalender tahunan
memuat hari bursa sampai Desember dan snapshot yang benar tidak boleh disebut basi (T30). Bukti di
`.uji-data/uji-kalender/`; rinciannya di `docs/keputusan.md` bagian 5 (Tahap 1 — langkah 8).

**Sebelumnya lagi (9 Okt 2026): kolom `tanggal_notasi`** — `Listing Date` KSEI (yang selama ini
dibuang setiap kali daftar emiten diambil) kini masuk ke `emiten.csv` → basis data → potret →
arsip. Terverifikasi atas berkas KSEI nyata 30 Sep 2026: **973 baris, 888 terisi, 85 kosong**
(kosongnya berasal dari sumbernya, bukan diisi tebakan), arsip snapshot sama persis dengan basis
data (0 selisih), dan berkas rujukan lama tanpa kolom itu tetap terbaca. Uji penjaga baru
menemukan **cacat nyata**: `imbal_hasil_sun.imbal_hasil_mentah` tidak ikut disidik saat menulis,
jadi impor ulang dengan bp sama tetapi sumber berbeda dibuang tanpa suara — sudah diperbaiki.
Rinciannya di `docs/keputusan.md` bagian 5 (Tahap 1 — langkah 7). Pemetaan nama kolomnya
ditanyakan sebagai **P18**.

**Sebelumnya (9 Okt 2026): cadence cek sumber kedua** (PRD 7.3 "tiap minggu"). Setiap jalan
`--cek-sumber-kedua` dicatat sebagai peristiwa di tabel `cek_sumber_kedua` (migrasi 006) beserta
**cakupannya**, dan keadaannya (belum pernah / tepat waktu / lewat / tidak dapat dinilai) muncul
sebagai temuan laporan mutu + peringatan `--refresh`. Cek tanpa harga pembanding **tidak**
dihitung memenuhi — kalau dihitung, peringatan mingguan justru padam ketika PRD 7.3 belum
dijalankan sama sekali. Rinciannya di `docs/keputusan.md` bagian 5 (Tahap 1 — langkah 6); batas
7 harinya dicatat sebagai usulan **U19**.

**Sebelumnya (9 Okt 2026):** U18 → **K13** — gerbang "gagal >5%" membedakan kegagalan permanen
("kode tidak diperdagangkan lagi") dari kegagalan sementara, jadi snapshot tidak lagi mustahil
terbit ketika daftar resmi memuat kode mati. Bukti: `.uji-data/bukti-u18-57-kode.txt`. Rinciannya
di `docs/keputusan.md` bagian 5 (Tahap 1 — langkah 5).

**Tahap 5 sudah dikerjakan 19 Okt 2026 (sesi 35):** `.exe` **sudah ada** — lihat **T81** dan baris
"Berkas `.exe`" di bagian 2. Alasan lama "jendelanya masih kosong" sudah tidak berlaku; yang
tersisa hanya **ikon** (aset belum ada) dan **uji klik-ganda di mesin tanpa Python**.

---

## 5. Aturan yang paling mudah dilanggar di repo ini

1. **Jangan mengarang parameter bursa** (lot, tick, ARA/ARB, tarif, PPh, SUN). Belum terverifikasi =
   tulis `[PERLU VERIFIKASI]` dan **tolak menghitung**. Sejak K12 ini juga berlaku untuk **sektor
   IDX-IC**: KSEI memakai taksonomi sendiri, jadi `sektor_idx_ic` sengaja dibiarkan kosong.
2. **Metrik tanpa data = "tidak dihitung"**, bukan nol, bukan rata-rata, bukan pendekatan.
3. **Data append-only**: perbaikan menambah baris baru dengan `diketahui_pada` lebih baru.
4. **Gagal itu berisik**: jangan `except: pass`; pesan harus menunjuk berkas/baris/kolomnya.
5. **Berhenti di setiap tahap** untuk ditinjau, dan laporkan **empat hal**: (a) test lulus,
   (b) ringkasan yang dikerjakan, (c) daftar yang belum dikerjakan, (d) cara menjalankannya.
6. **Satu fakta satu tempat**: jangan menyalin isi `docs/keputusan.md` ke berkas ini atau ke README —
   tulis rujukannya.
7. **Nama kolom yang PRD sebut tanpa penjelasan** (contoh hidup: `tanggal_notasi`) dipakai dengan
   pemetaan yang **dinyatakan terbuka** — di kode, di penjelasan berkas yang memuatnya, dan sebagai
   pertanyaan bernomor di `docs/keputusan.md` bagian 3. Menafsirkannya diam-diam = mengarang.

---

## 6. Jebakan lingkungan yang sudah ditemukan (jangan dikejar sebagai bug produk)

| Gejala | Sebabnya | Tindakan |
|---|---|---|
| `PermissionError: [WinError 5]` saat `--ambil-notasi` membuat `%LOCALAPPDATA%\MejaSaham\konfigurasi` | Windows menolak pembuatan folder data bawaan pada profil itu; pengambilan jaringan sudah selesai, tetapi CSV tidak bisa ditulis | Jalankan dengan lokasi data yang bisa ditulis, mis. `--folder-data .uji-data\mejasaham`; impor dari `.uji-data\mejasaham\konfigurasi` dan teruskan `--folder-data .uji-data\mejasaham`. CLI kini menampilkan pesan bantuan alih-alih traceback mentah |
| `PermissionError: [WinError 5]` / `[Errno 13]` saat menulis di `%TEMP%`/`%LOCALAPPDATA%` | Pembatasan proses terhadap **Python** oleh sandbox sesi agen — terukur 9 Okt 2026 bahkan di sesi yang **menyatakan** akses penuh, sementara PowerShell di sesi yang sama bisa menulis ke sana. **Bukan** bug aplikasi | Periksa dulu dengan satu baris: `python -c "import pathlib,os; pathlib.Path(os.environ['TEMP'],'x').write_text('x')"`. Untuk aplikasi: `--folder-data .uji-data`; pengguna menjalankan sendiri untuk lokasi standar |
| Uji berbasis `tmp_path` gagal massal (`PermissionError` di tahap setup), muncul folder `pytest-of-*` di repo | `tempfile.gettempdir()` memilih kandidat pertama yang bisa ditulis; bila temp sistem ditolak, ia **jatuh ke folder kerja** (kandidat terakhirnya `os.curdir`) — sehingga folder sementaranya berpindah ke akar repo | Bukan bug kode. Arahkan lebih dulu: `$env:TEMP="$PWD\.tmp\pytest-temp"; $env:TMP=$env:TEMP` (terverifikasi 9 Okt 2026: 6/6 uji `test_lokasi.py` lulus). Folder `pytest-of-*/` di akar repo adalah gejala yang sama dan sudah gitignored |
| `sqlite3.OperationalError: unable to open database file` pada kueri besar | SQLite menulis hasil antara ke folder temp; **sudah diperbaiki** dengan `PRAGMA temp_store=MEMORY` (T22) | Kalau muncul lagi, periksa T22 lebih dulu. **Terukur lagi 9 Okt 2026** pada skrip pemeriksa sendiri yang memakai `sqlite3.connect()` polos: `GROUP BY sumber` atas 999.421 bar gagal, dan berhasil begitu pragmanya dipasang. Jadi gejalanya bukan ciri kode aplikasi — skrip ad-hoc pun harus memasangnya |
| Log hasil `Tee-Object` tidak terbaca Python | PowerShell menulisnya **UTF-16LE** | Baca dengan `encoding="utf-16"`, bukan `errors="replace"` |
| `â€”` / `�` di keluaran terminal | Artefak penyandian tangkapan PowerShell, bukan aplikasi (pesan cetak sudah dijaga agar aman di cp1252) | Jangan "perbaiki" glifnya di kode |
| Glif rusak **di dalam berkas** (`â€”` alih-alih `—`) | Berkasnya tersimpan dengan penyandian campur pada sesi sebelumnya — beda dari baris di atas, yang cuma artefak tampilan. Klaim lama "tidak ada pesan aplikasi yang terkena, hanya komentar/docstring" **tidak berlaku untuk `mejasaham/metrik.py`** | **Diperbaiki TUNTAS 17 Okt 2026 (sesi 10):** terukur dari byte, `mejasaham/metrik.py` masih memuat **33 glif** rusak (24 baris) — `≤` 12×, `÷` 10×, `→` 5×, `−` 3×, `×` 2×, `√` 1× — dan sekitar **sepuluh** di antaranya **teks yang tampil ke pengguna** (`alasan`/`asal` metrik, mis. `ekuitas â‰¤ 0 sehingga DER tidak bermakna` di rincian `--saring` dan layar detail jendela). Jadi perbaikan 9 Okt 2026 ("10 tempat") **belum menyeluruh**; seluruh 33-nya diganti glif yang benar, dan sesudahnya **sisa 0**. Penjaganya `tests/test_glif_teks.py` — memindai byte (bukan tampilan; terminal bisa menampakkan glif yang seolah benar) dan **terbukti gagal** atas berkas lama (12 `≤`, 10 `÷`, …). `docs/` sengaja tidak dipindai: di sana urutan itu dipakai sebagai **kutipan gejala** |
| **Berkas bukti hasil tangkapan pytest lewat PowerShell memuat `�`** | Pipa PowerShell mendekode stdout anak dengan codepage konsol, lalu `Set-Content`/`Out-File` menulis hasil dekode itu — glif `—`/`·` menjadi `�` (terukur 19 Okt 2026, sesi 20: berkas bukti uji-pada-`HEAD` harus dibuat ulang) | Tangkap keluaran lewat **Python** (`subprocess.run(..., capture_output=True)` dengan `PYTHONIOENCODING=utf-8` pada env anak) dan tulis **bytes**; jangan mengandalkan pipa teks PowerShell untuk berkas bukti. Baca ulang berkasnya dengan pembaca UTF-8 sebelum dikutip |
| Snapshot ditolak gerbang, lalu **tidak ada data tersimpan** | AC-19: seluruh refresh satu transaksi — disengaja | Unduhan berikutnya mengulang dari awal; itu memang harganya |
| 57 kode gagal dengan `No data found, symbol may be delisted` | Kode itu **masih tercatat di KSEI tetapi tidak diperdagangkan lagi**. "ACTIVE" di KSEI ≠ diperdagangkan di IDX | Bukan galat sementara, bukan pembatasan laju; **sudah ditangani** K13/U18 (dilaporkan sebagai lubang, tidak lagi memblokir) |
| Berkas CSV ditolak "kolom tidak dikenal ['kode;nama;…']" padahal isinya benar | (Dulu) pemisah kolom dideteksi dari baris **fisik** pertama, jadi baris penjelasan `#` di atas baris kepala merusak deteksinya | **Sudah diperbaiki** 9 Okt 2026; baris kepala kini dicari dengan aturan yang sama dengan pembacaannya |
| Saringan kehilangan emiten justru **sesudah** harga pembanding diimpor | Harga pembanding hidup di tabel yang sama (memang begitu, migrasi 005), dan pembacaan untuk perhitungan belum menyaring `sumber` — dua bar tanggal sama masuk ke satu deret, jendela 20 hari memuat hari terduplikasi | **Sudah diperbaiki** 9 Okt 2026 (T32, langkah 9): harga dibaca satu label, dan labelnya dilaporkan. Bukti terukurnya di `.uji-data/uji-p17/` — likuid 235, bukan 215. Kalau gejalanya muncul lagi, periksa T32 lebih dulu, bukan `penyesuaian.py` |
| `--saring` menyebut sebuah label sumber dan memperingatkan label lain | Bukan galat: itu aturan satu label per snapshot (T32). Dua label di basis data = harga pembanding PRD 7.3 ada, dan ia **tidak** dipakai berhitung | Jangan "perbaiki" dengan menggabungkan kedua label. Kalau memang ingin label lain: `--sumber LABEL`. Ambang "label dominan" sengaja tidak dibuat (alasannya di `docs/keputusan.md` bagian 3, P17) |
| `pytest` gagal massal `PermissionError: [WinError 5] Access is denied: ...\pytest-of-<user>` — **berbeda** dari baris pertama tabel ini | Folder sementara lama (`pytest-of-PENGGUNA`) menjadi **tidak bisa diakses sama sekali** (tidak bisa dibaca, ditulis, atau dihapus — bahkan oleh PowerShell), sehingga seluruh uji berbasis `tmp_path` gagal di tahap setup. Terukur 10 Okt 2026: 163 lulus / **259 error** tanpa satu pun perubahan kode. Bukan bug aplikasi | **Pakai folder sementara yang BARU setiap kali**, jangan yang sudah ada: `$env:TEMP="$PWD\.tmp\t<N>"; $env:TMP=$env:TEMP`. Terverifikasi 10 Okt 2026 dengan `.tmp\t2`: **422 lulus**. Kalau folder lama perlu dibersihkan, ia mungkin menuntut perbaikan izin tersendiri — jangan dianggap bug produk |
| `browserType.launch: spawn EPERM` saat menjalankan Playwright dari sesi bersandbox | Sandbox memblokir **pipa**: Playwright menjalankan peramban dengan `--remote-debugging-pipe`, dan pipa itu ditolak | Dua jalan, keduanya terverifikasi: (a) **akses penuh** — `chromium.launch()` langsung berhasil; (b) peramban dijalankan sendiri dengan `--remote-debugging-port=9222` lalu `chromium.connectOverCDP('http://127.0.0.1:9222')` (TCP, tanpa pipa). Paket Playwright di mesin ini ada di `C:\Users\PENGGUNA\AppData\Roaming\npm\node_modules\omniroute\node_modules\playwright`, peramban di `%LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win64\chrome.exe` |
| `idx.co.id` membalas **403** untuk `requests`/`curl` — tetapi **200 untuk peramban sungguhan**; lalu setelah beberapa permintaan cepat, **semua** permintaan (termasuk dari peramban) diblok `Sorry, you have been blocked` | Cloudflare: tantangan diselesaikan peramban, **blok burst** tidak. Cookie `cf_clearance` **tidak** cukup bila disalin ke `requests` (terukur: tetap 403) | Perlakukan sebagai pembatas laju, bukan pintu yang bisa dibuka: **satu** permintaan per jalan, berjeda menit, dan jangan dari sesi yang IP-nya sedang diblok. Kalau tujuannya mengambil data untuk aplikasi, ingat `requests` tetap tidak bisa — jadi peramban bukan jalan implementasi kecuali keputusan dependensi dibuat lebih dulu. **DIPERBARUI 10 Okt 2026:** yang memblokir ternyata **dua host itu**, bukan IDX — lihat baris berikutnya |
| Kesimpulan lama "seluruh jalur resmi IDX mati" | **Salah, dan terbukti salah 10 Okt 2026.** Yang membalas 403 adalah `www.idx.co.id` dan `www2.idx.co.id`; domain resmi **`www.idx.id`** melayani halaman yang sama dengan **HTTP 200**. Terukur: UA jujur `MejaSaham/0.1 (…)` → 200 (251.947 byte); UA bawaan `Python-urllib/3.14` → 403; lima permintaan berturut-turut → lima kali 200 (0,56–0,73 detik) | Jangan menyimpulkan "sumbernya mati" dari satu host. Sebelum menyerah: coba domain lain milik lembaga yang sama, dan coba **UA yang menyebut diri sendiri** (bukan menyamar) — dua hal itu saja membuka halaman notasi khusus. Halaman-halaman itu **bukan `<table>`**: datanya di payload SSR Nuxt (`window.__NUXT__`), dan pola seperti `FormatEmitenCode:"KODE.HURUF"` lebih tahan perubahan daripada pengurai JSON penuh |
| Daftar papan pemantauan tampak **kosong** padahal halamannya berisi | Huruf notasi di halaman IDX **tergabung** dalam satu token: `BOSS.BELYX` berarti B, E, L, Y, X. Membacanya sebagai satu notasi bernama "BELYX" membuat `X` (papan pemantauan khusus) tidak pernah dikenali | Pecah per huruf. Juga: kodenya **tidak selalu empat huruf** — halaman itu memuat `GOTOM`, sehingga pola `[A-Z0-9]{4}` membuang satu baris tanpa suara. Dua-duanya dikunci di `tests/test_notasi_idx.py` |
| Migrasi gagal dengan `RAISE() may only be used within a trigger-program` | `RAISE(ABORT, …)` **hanya sah di dalam program trigger**, bukan sebagai pernyataan biasa — jadi penjaga keutuhan yang ditulis `SELECT RAISE(...) WHERE <syarat>` di dalam skrip migrasi selalu gagal, sekalipun syaratnya tidak pernah terpenuhi. Karena `executescript` membatalkan seluruh migrasi, gejalanya muncul sebagai "migrasi N gagal" dan menutupi maksud penjaganya. Terukur 10 Okt 2026 saat menulis migrasi 008 (rebuild `parameter_biaya_broker`) | **Bungkus pemeriksaannya sebagai trigger sementara**, lalu `UPDATE` sebuah tabel temp supaya trigger itu dievaluasi: `CREATE TEMP TRIGGER … BEFORE UPDATE ON tabel_temp WHEN OLD.x <> … BEGIN SELECT RAISE(ABORT, '…'); END;` → `UPDATE tabel_temp SET x = x;` → `DROP TRIGGER`. Trigger-nya dipasang **sebelum** tabel lama dibuang, sebab memeriksa sesudahnya berarti data aslinya sudah terlanjur hilang |
| `git status`/`git log` menunjukkan perubahan yang tidak dibuat sesi ini (mis. berkas `mejasaham/kandidat.py`, commit yang isinya pekerjaan serupa) | **Dua sesi bekerja di working tree yang sama.** Berkas yang terlihat "berubah sendiri" adalah pekerjaan sesi lain, bukan kerusakan repo | Sebelum menyunting berkas yang mungkin disentuh sesi lain (`docs/lanjutan.md`, `docs/keputusan.md`, `docs/arsitektur.md`, `mejasaham/cli.py`, `mejasaham/skema.py`): **baca ulang berkasnya tepat sebelum menyunting** dan pakai `edit` dengan potongan yang spesifik, jangan tulis ulang seluruh berkas dengan `write`. Kalau muncul galat "file changed since it was read", itu memang tanda sesi lain baru menulis — baca ulang, jangan paksa |
| `pytest` gagal massal di tengah jalan: `PermissionError: [WinError 5] ... pytest-of-PENGGUNA`, **folder sementara baru pun** (`.tmp/t13`, `.tmp/t14`) kena — dan `Get-Acl` atas folder itu menjawab "Attempted to perform an unauthorized operation" | **Terukur 10 Okt 2026 (sesi ini).** Folder yang dibuat proses Python yang dibatasi sandbox mendapat DACL bawaan token-nya (CREATOR OWNER/SYSTEM/Administrators, tanpa ACE pengguna), sehingga ia **tidak bisa diakses lagi** — bahkan oleh PowerShell. Bukan bug aplikasi, dan **bukan** kelas ACL yang diperbaiki skrip `diagnose-windows-sandbox-acl` (verdictnya `NOT_THIS_CLASS`, `FIXED=0`, tidak ada perubahan izin). **Terulang lagi 10 Okt 2026 (Tahap 2 langkah 3):** dengan `$env:TEMP=.tmp\pt3`, 217 uji lulus dan **366 error** tanpa satu pun perubahan kode; sesudah sesi beralih ke akses penuh, perintah yang sama menghasilkan **657 lulus dalam 28 detik**. **Terukur lagi 16 Okt 2026 (sesi 3), dengan sebabnya dipersempit:** folder sementara **baru** (`.tmp/t31`, `.tmp/t32`, `.tmp/t33`) **tidak menolong** — 225 lulus / **540 error**; yang gagal adalah pembuatan folder **di dalam** folder yang dibuat Python: `Path('.tmp/t33/pytest-of-PENGGUNA').mkdir(mode=0o700)` **berhasil**, tetapi `mkdir` anak di dalamnya langsung `PermissionError: [WinError 5]`, sedangkan `mkdir` biasa (tanpa `0o700`) di `.tmp` berhasil | Kalau muncul: **jangan** membuat folder sementara baru berulang kali (gejalanya kembali di tengah jalan, dan folder baru pun kena). Yang menyelesaikannya: sesi beralih ke **akses penuh** — terukur 16 Okt 2026: `765 passed in 55.95s`. Folder `.tmp/t13`, `.tmp/t14`, `.tmp/pytest-temp`, `.tmp/pt3`, `.tmp/t31`–`.tmp/t33` yang sudah rusak tinggalkan saja — jangan dianggap kerusakan repo |
| Penyuntingan berkas besar gagal dengan `ReplaceFileW EIO (Win32 1175)` di `mejasaham/skema.py`/`mejasaham/cli.py` | Penggantian berkas atomik tidak bisa menyelesaikan penggantian — antivirus/indeks sedang memegang berkasnya sesaat. Isi berkas **tidak** berubah separuh (sudah diperiksa: jumlah barisnya utuh) | Ulangi perintah suntingnya (berhasil pada percobaan kedua/ketiga). Kalau tetap gagal, periksa dulu apakah perubahannya sebenarnya sudah masuk sebelum menyalahkan yang lain. **Terukur lagi 10 Okt 2026 (langkah 4)** di `mejasaham/posisi.py` — berhasil pada percobaan kedua |
| Perlu membuktikan uji baru **gagal pada kode lama**, tanpa menyentuh working tree | `git stash`/checkout akan mengacaukan pekerjaan yang belum di-commit — dan sesi lain bisa sedang memakai working tree yang sama | **Pakai worktree terpisah**: `git worktree add .tmp\kerja-lama HEAD` lalu jalankan pytest dari sana dengan `.venv` repo ini (`--rootdir` diarahkan ke worktree). Terukur 10 Okt 2026 (langkah 4): 38 dari 39 uji baru gagal di sana. Sesudahnya `git worktree remove --force .tmp\kerja-lama; git worktree prune`. Catatan: uji yang mengimpor nama **baru** di puncak modul (mis. konstanta baru di `skema.py`) akan gagal **saat koleksi**, bukan sebagai kegagalan uji — ganti dulu impornya bila mau bukti yang lebih tajam |
| Menyimpulkan **basis** deret dividen sumber dari satu emiten | Satu emiten tidak membedakan "mentah" dari "sudah disesuaikan split": semua dividennya bisa berada di satu sisi split | **Ukur lintas split**: bandingkan dividen terakhir sebelum dan pertama sesudah tiap split (kasus nyata: 33 split). Kalau nilainya berskala sama (SKRN 6 → 6 melewati 1:5, TMAS 8 → 8 melewati 1:10), deretnya **sudah** dalam basis sekarang — dan itu yang menentukan pasangannya lembar basis sekarang (T50). Cara memeriksanya sekali lagi ada di `docs/keputusan.md` K28 |
| Menyunting `konfigurasi/notasi-khusus.csv` lalu `--impor`, berharap basis data ikut berubah — **tidak terjadi apa-apa**, impornya berbunyi "0 baris baru" | **Impor hanya menambah revisi, ia tidak menyinkronkan:** baris yang tidak ada di berkas tidak bisa berubah, dan baris yang ada tetapi isinya sama dilewati tanpa suara. **KOREKSI 16 Okt 2026 (sesi 5): angka "122 baris" pada catatan lama salah alamat.** Berkas `.uji-data/mejasaham/konfigurasi/notasi-khusus.csv` ternyata memuat **2.276 baris data** (2.303 baris berkas, terakhir ditulis 11 Okt 2026 18:xx — diimpor dua kali sehingga tabelnya 4.552 baris); yang **122 baris** itu `.uji-data/uji-sektor/konfigurasi/notasi-khusus.csv` (161 baris berkas) dan `.uji-data/konfigurasi/notasi-khusus.csv` (26 baris) — dua berkas lain, bukan yang dipakai basis data utama | Aturan kerjanya tidak berubah karena koreksi ini: untuk mengubah baris yang hanya ada di basis data, **bangun berkasnya dari basis data** (revisi terkini tiap kunci) lalu impor sebagai revisi baru — caranya di K51 dan di bagian 3. Sebelum menuduh, bandingkan jumlah baris berkas dengan basis data: `(Get-Content …csv).Count` vs `select count(*) from notasi_khusus` |
| Perlu **melihat** halaman PDF pengumuman IDX (tinjauan visual), dan tidak ada pembaca PDF di `.venv` (`fitz`/`pypdfium2`/`pdf2image` semuanya **tidak ada**) | **Tidak butuh dependensi baru:** `PySide6` sudah terpasang, dan **`PySide6.QtPdf.QPdfDocument.render()`** merender halaman jadi `QImage` yang bisa disimpan PNG. **Terukur 16 Okt 2026 (sesi 6):** kedua halaman `2024-02-20_SPT_47.pdf` jadi PNG 1308×1852 px dalam hitungan detik | Pakai `.uji-data/riset-idx/tinjauan-k46/render-pdf.py` (`QT_QPA_PLATFORM=offscreen`, skala 2.2, halaman 1..N). Jangan memasang pustaka PDF baru hanya untuk *melihat* halaman — lihat aturan `adding-dependencies`. Catatan: teks hasil ekstraksi (`.txt` di sebelah tiap PDF) **bukan** pengganti tinjauan visual: yang menjawab K46 justru hal yang **tidak** ada di sana (ternyata tidak ada legenda/kolom kelima) |
| Membandingkan tanggal di berkas/laporan ini | Dua format hidup berdampingan: `notasi_khusus`/basis data memakai **`YYYY-MM-DD`**, sedangkan berkas rekonsiliasi `.uji-data/riset-idx/rekonsiliasi-*-per-kode-*.csv` memakai **`DD-MM-YYYY`**; berkas CSV-nya juga ber-**BOM UTF-8** sehingga kolom pertama terbaca `'\ufeffkode'` bila dibuka dengan `encoding="utf-8"` | Baca CSV rekonsiliasi dengan `encoding="utf-8-sig"` dan bandingkan tanggal sebagai `YYYY-MM-DD` hasil konversi, bukan sebagai string. Terukur 16 Okt 2026 (sesi 6): perbandingan pertama menghasilkan "34 berbeda" hanya karena `20-02-2024` dibandingkan sebagai teks — sesudah dikonversi hasilnya **34 identik** |
| **Keterangan hilang separuh tanpa galat** setelah `--impor` sebuah berkas yang ditulis dengan penggabungan string (`f"{a};{b};..."`) dan memuat `;` di dalam kolom `keterangan` | Pembaca impor (`mejasaham/berkas.py`) membangun baris sebagai `{header[i]: baris[i] for i in range(len(header))}` — kolom **selebihnya dibuang diam-diam**, tanpa pesan. Terukur 16 Okt 2026 (sesi 7): **66 dari 171 baris** berkas `.uji-data/riset-idx/impor-suspensi-20261016/notasi-khusus.csv` kehilangan seluruh isi sesudah `;` pertama; akibatnya penanda `TANGGAL_MULAI_TIDAK_DINYATAKAN_SUMBER_MANA_PUN` **0 kali** di revisi terkini (padahal 65 episode proxy), penanda K47 **3 dari 4** kode, dan `MTFN` kehilangan **1.326 karakter**. **Bukan** gejala kerusakan berkas: berkasnya utuh, yang hilang hanya saat dibaca | Tulis berkas impor dengan **`csv.writer`** (kutip minimal) — itu sudah cukup, dan terbukti: berkas notasi 2.450 baris yang memuat `;` di beberapa `keterangan` **bulat-balik sama persis** lewat `mejasaham.berkas.baca_folder`. Cara memeriksa berkas yang sudah terlanjur ada: `python .uji-data/riset-idx/k53-k54/ukur-potong-keterangan.py` (mencetak baris yang potongannya > 5 dan ekor yang hilang). **Sudah ditutup 16 Okt 2026 (sesi 8, aksi #18):** pembaca berkas kini **menolak** baris dengan kolom berlebih **yang berisi** — pesannya menyebut nama berkas, nomor baris, isi yang akan hilang, dan jalan keluarnya (`csv.writer`) — sedangkan kolom berlebih yang **kosong** (mis. `;;` di ujung baris) tetap diterima; 65 baris yang terlanjur terpotong **dipulihkan** dari baris mentah berkasnya |

| Menjalankan jendela PySide6 tanpa layar (`QT_QPA_PLATFORM=offscreen`) berhasil, tetapi **seluruh teks tergambar sebagai kotak**, dan stderr berbunyi `QFontDatabase: Cannot find font directory …/PySide6/lib/fonts` + "Qt no longer ships fonts" | Qt yang dipasang di `.venv` ini tidak menemukan folder fontnya sendiri; di platform `offscreen` ia tidak jatuh ke font sistem. Bukan bug aplikasi — jendela sungguhan (platform `windows`) memakai font sistem dan tidak terpengaruh | Setel **`QT_QPA_FONTDIR`** ke folder font sistem sebelum `QApplication` dibuat: `$env:QT_QPA_FONTDIR = "$env:WINDIR\Fonts"` (terukur 17 Okt 2026: `QFontDatabase.families()` 0 → **174**, dan tangkapan layarnya terbaca). Tanpa ini, "tinjauan visual" atas jendela hanya melihat kotak — dan menyimpulkan tata letaknya dari situ berarti menyimpulkan dari yang tidak terlihat |
| **Uji jendela berhenti tanpa traceback**: `Windows fatal exception: access violation` atau `Fatal Python error: Aborted`, jejaknya menunjuk `tunggu_pekerja()` → `QThread.wait()`/`QApplication.processEvents()`, sementara utas pekerja hidup | **Cacat PySide6 6.12.0 + CPython 3.14.7**, bukan logika aplikasi: pengumpulan sampah **siklik** yang berjalan sementara utas pekerja hidup. Terukur 17 Okt 2026 (sesi 10) — kode lama **0 gagal/18 jalan uji jendela**, kode yang menambah alokasi di utas pekerja **7/18**, dengan blok itu dimatikan **0/12**, dengan GC dimatikan **0/12**, dengan pohon Qt uji ditahan hidup **12/12**. Gejalanya bergantung waktu, jadi muncul sebagai "uji yang kadang lulus" — kelas kegagalan yang paling mahal untuk dipercaya | **Sudah ditangkal (T68):** satu penahan berpenghitung (`mejasaham/ui/pekerja.py:tahan_gc_siklik()`) yang dipakai `Pekerja.run` **dan** `Jendela.tunggu_pekerja` (versi pertama yang hanya menjaga `Pekerja.run` bocor: 1 gagal dari 8 jalan suite penuh; sesudah penghitungnya: **0/10** uji jendela dan **0/8** suite penuh). Ini **penangkal, bukan perbaikan** — bila gejalanya muncul lagi di jalur lain (mis. kode Qt yang berjalan **tanpa** `Pekerja`), yang salah bukan kode aplikasi: **jangan** "perbaiki" dengan mematikan GC di seluruh proses. Riset lanjutannya (angka, dua repro sintetis yang **tidak** memicunya, dan urutan langkah berikutnya: laporan upstream → uji Python 3.13 → uji PySide6 lain) ada di **`docs/riset-pyside6-gc-2026-10.md`**; kombinasi PySide6 6.12.0 + CPython 3.14.7 **didukung** paketnya (`Requires-Python >=3.10,<3.16`). **Diperbarui 19 Okt 2026 (K69):** reproduksi ulang **berhasil** — suite penuh 12× tanpa penangkal di 3.14.7 → **2 mati**, sedangkan A/B 3.13.14 → **0 mati** (p ≈ 0,48, jadi **bukan** bukti versi Python menyelesaikannya); kematian kali ini muncul di **`_tunggu` berkas uji** (`pekerja.wait`), bukan hanya di `tunggu_pekerja`, dan dump-nya hanya utas utama. **Patokan "mati" = tidak ada ringkasan pytest**; kata `access violation` **tidak boleh** dipakai sebagai penanda — ia muncul di **12 dari 12** log (semuanya docstring) sehingga log yang hidup pun bertanda "fatal" palsu |
| `--dasbor` terasa jauh lebih lambat daripada sebelumnya (2,8 dtk → puluhan detik) pada basis data nyata | **Bukan kemacetan atau kebocoran:** sejak K58/T66 dasbor menghitung konteks pasar lewat jalur yang **sama** dengan `--saring` (potret + seluruh metrik + breadth), jadi ia memang membayar beban saringan. Terukur 17 Okt 2026 pada 999.421 bar: `potret.muat` 16–25 dtk · `metrik.metrik_semua` 14–25 dtk · `breadth` 2,5–4,7 dtk; angkanya berayun 1–2× mengikuti beban mesin (dan sesi lain yang bekerja bersamaan) | Jangan "mengoptimalkan" dengan menghitung breadth dari ambang sendiri atau membaca angka yang disimpan — itu dua salinan aturan (K58/T66). Kalau memang terlalu lambat, yang benar adalah keputusan baru (mis. menghitungnya sekali saat `--saring` lalu menyimpannya **beserta** snapshot & presetnya) — bukan menyimpang diam-diam. Ukur dulu dengan `.tmp/ukur-dasbor2.py` sebelum menuduh |
| **Mutasi uji untuk membuktikan sebuah uji "bergigi" tertinggal di berkas** sesudah `git checkout -- <berkas>` dijalankan | `git checkout -- <berkas>` **hanya** memulihkan berkas yang **dilacak**; berkas uji baru yang belum pernah di-`git add` bersifat *untracked*, sehingga perintah itu gagal (`pathspec did not match`) — dan bila stderr-nya dibuang (`2>&1 \| Out-Null`), kegagalannya tidak terlihat sama sekali. Terukur 17 Okt 2026 (sesi 11): satu mutasi `biaya=69_001` tertinggal di `tests/test_ui_tulis.py` dan hanya ketahuan dari `Select-String` | Sebelum memulihkan, periksa dengan `git status --short <berkas>`: `??` berarti **tidak** bisa dipulihkan `git checkout`. Cara yang aman untuk mutasi: salin berkasnya dulu (`Copy-Item x x.bak`), atau jalankan mutasinya di **worktree terpisah** (lihat baris di atas), lalu **selalu verifikasi** sesudah memulihkan (`Select-String` atas nilai yang dimutasi) — jangan percaya bahwa perintah pemulihannya berhasil |
| Slot Qt dengan parameter **keyword-only** (`def muat(self, *, pertahankan: bool = False)`) | PySide6 memanggil slot dengan argumen sinyalnya (`clicked` mengirim `checked`) secara **posisional**; parameter keyword-only membuat sambungan itu gagal saat tombolnya ditekan, bukan saat `connect()` | Jangan menaruh parameter baru di slot yang sudah tersambung ke sinyal Qt. Yang dipakai sesi 11 (`_pertahankan_pesan` sebagai keadaan di `Panel`, bukan parameter `muat()`) adalah jalan keluarnya |
| **Dua pekerja berurutan pada satu slot `_pekerja`** (tindakan dua tahap: baca → konfirmasi → tulis) | Slot `_pekerja` dipegang **satu** pekerja; kalau pekerja pembacaan diganti pekerja penulisan sementara utasnya belum benar-benar berhenti, ia **lepas dari `Jendela.pekerja_aktif()`** — dan itu persis keadaan yang membuat penutupan jendela memusnahkan `QThread` yang masih hidup (`access violation`/proses berhenti, T65/T68). Sinyal `selesai` **dikirim dari dalam** `run()`, jadi saat slotnya dipanggil `isRunning()` bisa masih `True` | Tunggu utasnya lebih dulu sebelum melepas slotnya: `pekerja.wait()` di slot penyelesaian (terukur sesi 12: pekerjaan pembacaan sudah mengirim hasilnya, jadi `wait()`-nya tidak menunggu lama). Alternatif yang dipakai: `Panel.jalankan_tulis()` **tidak** memeriksa "masih bekerja?" — pemeriksaan itu ada di `Panel.tulis()`, untuk pemanggil dari tombol |
| Impor yang terkunci berhenti setelah **~11 detik**, bukan ~5 (`busy_timeout`) | Kegagalan penulisan diikuti percobaan **mencatat log** (`pengatur._catat_log`), yang menunggu `busy_timeout` untuk **kedua** kalinya — padahal log tidak bisa ditulis selama kuncinya dipegang proses lain | **Sudah diperbaiki 17 Okt 2026 (aksi #19b):** `pengatur.jalankan_impor` meneruskan `db.BasisDataTerkunci` apa adanya tanpa mencoba mencatat log. Terukur **11,16 dtk → 5,62 dtk**. Jalur gagal yang lain tetap mencatat log seperti semula (`tests/test_ui_tulis.py::test_impor_yang_terkunci_tidak_menambah_penantian_kedua`) |
| **Skrip bukti `offscreen` menggantung** (berjalan terus sampai dibunuh) tepat pada langkah yang memunculkan **dialog konfirmasi** | `Panel.tanya` membuka `QMessageBox` **modal** (`exec()`); di platform `offscreen` tidak ada yang menekan tombolnya, jadi `exec()` tidak pernah kembali. Terukur 17 Okt 2026 (sesi 16, aksi #19c): skrip bukti menggantung di bagian **keenam**, karena tambalan `Panel.tanya` sengaja dilepas sesudah bagian pertama | Tambal `Panel.tanya` **untuk seluruh jalan skrip**, bukan per bagian — atau tambal `QMessageBox.exec`-nya (cara skrip tangkapan layar `tangkap-layar-19c.py`: dialognya tetap dibangun kode asli, digambar, lalu dijawab "Tulis"). Kalau uji/skrip menggantung setelah sebuah penulisan, periksa dulu apakah ada dialog modal yang tidak terjawab |
| `QThread.isRunning()` bernilai **salah** tepat sesudah `start()`, sehingga penantian pekerja yang memeriksanya lebih dulu **melewatkan** penantiannya | `start()` mengembalikan kendali sebelum utasnya benar-benar berjalan; pola `if pekerja.isRunning(): pekerja.wait()` karena itu bisa langsung keluar, dan skrip/uji membaca layar yang masih berbunyi "bekerja…". Terukur 17 Okt 2026 (sesi 16) pada skrip tangkapan layar | Tunggu **setidaknya sekali** (`pekerja.wait(batas)`) tanpa didahului `isRunning()`, lalu baca ulang `panel._pekerja` tiap putaran supaya pemuatan ulang yang memakai pekerja kedua ikut ditunggu (pola `_tunggu_panel` di `tests/test_ui_jendela.py`) |
| **Bukti/tangkapan layar yang sudah dibuat hilang** sesudah menjalankan skrip bukti lain | Skrip bukti biasanya membersihkan foldernya di awal (`shutil.rmtree(AKAR_BUKTI)`) supaya hasilnya bisa diulang dari nol — dan itu ikut menghapus berkas yang dibuat **skrip lain** di folder yang sama. Terukur 17 Okt 2026 (sesi 16): empat PNG `tangkap-layar-19c.py` terhapus oleh `bukti-cadangan-jendela.py` yang dijalankan sesudahnya | Jalankan skrip **pembuat bukti lebih dulu**, skrip **tangkapan layar terakhir** — atau periksa isi folder bukti (`Get-ChildItem`) sebelum melaporkan artefaknya. Kalau ada yang hilang, jalankan ulang skripnya (di sini: 15 detik) dan sebutkan apa adanya bila artefaknya tidak lagi ada |
| Skrip bukti **mengubah akhir baris berkas kode**: `Path.write_text(...)` di Windows menulis LF sebagai **CRLF**, sehingga berkas yang "dipulihkan" berubah byte-nya | `Path.read_text`/`write_text` memakai penerjemahan akhir baris bawaan platform; skrip mutasi sesi 18 membaca berkas (LF) lalu menulisnya kembali sebagai CRLF. Terukur: tiga berkas (`mejasaham/ui/{tulis,tabel,jendela}.py`) berubah dari LF ke CRLF, dan **pemeriksa hash SHA-256** yang menangkapnya (bukan dugaan) | Untuk skrip yang menyunting berkas lalu memulihkannya: baca/tulis **bytes** (`read_bytes`/`write_bytes`, teks dinormalkan `\r\n` → `\n`) dan **periksa hash sesudah memulihkan** — jangan percaya bahwa pemulihannya berhasil. Kalau terlanjur: normalkan kembali (`data.replace(b"\r\n", b"\n")`) dan pastikan `git diff --stat` tidak meledak. Sebagian berkas repo memang sudah CRLF (`mejasaham/notasi.py`, `tests/test_notasi_idx.py`, `docs/*.md`) — itu **tidak** perlu diperbaiki, dan git menormalkannya saat commit |
| Skrip Python yang memuat glif (`—`, `·`, `→`) menjadi **mojibake** sesudah disunting lewat pipa PowerShell | `Get-Content -Raw … \| Set-Content -Encoding utf8` menulis ulang isinya dengan penyandian ganda (terukur 17 Okt 2026, sesi 18: `—` menjadi `Ã¢â‚¬â€`), sehingga potongan teks yang dicocokkan skrip tidak lagi ketemu (`potongan mutasinya tidak unik (0x)`) | Jangan menyunting berkas berkode lewat pipa teks PowerShell — pakai alat penyunting berkas (atau `-Encoding utf8NoBOM` **plus** pemeriksaan hasilnya). Kalau berkas bukti sudah terlanjur mojibake: tulis ulang skripnya, lalu jalankan ulang — jangan "perbaiki" glifnya satu per satu |
| **Berkas `rasio-bank.csv` dengan desimal koma ditolak pembaca impor** | `ingesti._desimal` memakai `Decimal("…")`, jadi `1,86` bukan angka; templat `mejasaham/defaults/rasio-bank.contoh.csv` memang mencontohkan `2.35` untuk 2,35%. Terukur 19 Okt 2026 (sesi 25): versi pertama berkas kandidat gagal berisik — `rasio-bank.csv baris 2 npl_kotor_persen: bukan angka yang bisa dibaca ('1,86')` | **Berkas impor = titik desimal; tampilan & ekspor tetap koma** (U11). Jangan "memperbaiki" dengan menormalkan koma di pembaca: konversi diam-diam bisa mengubah arti ribuan (`1.234` vs `1,234`) — persis kelas kesalahan yang dilarang aturan keras 1 |
| **Publikasi resmi bank tidak bisa diambil otomatis, padahal halamannya terbuka di peramban** | Tiga bank berbeda sebabnya (terukur 19 Okt 2026, sesi 25): **BMRI** `robots.txt` `Disallow: /*.pdf$` (seluruh publikasinya PDF); **BBNI** `Disallow: /Portals/` (folder publikasinya) + tantangan Incapsula yang membalas HTTP 200 212 byte bahkan kepada peramban headless; **BBRI** `robots.txt`-nya sendiri di balik tantangan itu, dan katalog `bri.co.id/laporan` hanya kerangka JavaScript | **Hormati `robots.txt`** — jangan mengakali dengan UA peramban, unduhan berulang, atau peramban headless. Jalur yang tersisa: **pengguna mengunduh manual** lewat peramban, atau keputusan baru. **IDX bukan jalan keluar**: `www.idx.co.id/StaticData/…pdf` tetap **403** (dua kali terukur 19 Okt 2026). Dokumen resmi bank yang *bisa* dibaca belum tentu memuat rasio: laporan keuangan BRI Q2-2026 memuat "BOPO" **0 kali** dan presentasinya memakai **CIR**, bukan BOPO |
| **Baris `rasio-bank.csv` kehilangan `sumber` per barisnya saat diimpor** | `berkas._baris_rasio_bank` tidak mengisi `sumber` (kelas `RasioBank` tidak punya bidang itu), lalu `ingesti._baris_rasio_bank` memakai `kumpulan.sumber` = `impor berkas: <folder>`. Terukur 19 Okt 2026: `sumber baris: 'impor berkas: …\uji-baca'`, padahal berkasnya memuat sumber per bank | **SUDAH DIPERBAIKI 19 Okt 2026 (sesi 27, aksi #27 → K78/T77):** kolom `sumber` kini dibaca, disimpan per baris, dan dikembalikan `potret`; sel kosong bahkan **ditolak per baris**. Kalau menemukan baris `rasio_bank` yang `sumber`-nya masih `impor berkas: …`, itu data **lama** yang diimpor sebelum K78 — perbaiki dengan mengimpor ulang berkasnya (append-only: baris baru), bukan dengan `UPDATE` |
| **Tanggal tanda tangan di halaman publikasi bank berasal dari templat lama** | Bank tidak memperbarui baris tanggal saat memakai ulang templat. Terukur 19 Okt 2026: laporan BCA posisi **30 Jun 2026** masih memuat *"Jakarta, 23 Januari 2025"* di blok tanda tangannya | Jangan memakai baris tanggal tanda tangan sebagai `tgl_publikasi` tanpa memeriksa kewajarannya. Pakai nama berkas (`20260728-…`), header HTTP `Last-Modified`, atau tanggal di situs — dan **catat** bahwa dokumennya memuat tanggal lama. Bandingkan dengan BRIS yang menandatangani "Jakarta, 21 Agustus 2026" (wajar untuk publikasi Juni 2026) |
| **Perintah yang menunjuk `.uji-data/uji-<nama>` tetap "jalan" tetapi mengukur basis data kosong** | Folder sandbox uji dikosongkan 17 Okt 2026 (pembersihan ruang atas permintaan pengguna): `mejasaham.db` + `arsip-snapshot/` di dalam `.uji-data/uji-*` dihapus, berkas buktinya ditinggal (repositori 44,99 → 3,49 GB). `--folder-data` ke folder yang tidak punya basis data **membuat basis data baru yang kosong** — dan saringan atas basis data kosong tetap mencetak ringkasan yang terlihat wajar. **Bukan** kerusakan repo: `pytest` sesudahnya tetap **882 lulus** (uji memakai `tmp_path`, tidak menyentuh `.uji-data`) | Bangun ulang sandboxnya lebih dulu — `Copy-Item -Recurse .uji-data\mejasaham .uji-data\uji-<nama>` — atau pakai `.uji-data/mejasaham` langsung (salin dulu bila akan menulis baris). Peringatan lengkapnya di awal bagian 3 |
| **Impor satu folder menulis ulang label `sumber` baris `notasi_khusus`** (untuk refresh: **diperbaiki sesi 56, T88** — label folder absolut, tidak lagi berlabel yfinance; untuk `--impor` manual dari folder lain masih berlaku) | `kumpulan.sumber` = `impor berkas: <folder>` ikut menjadi isi baris, dan `_tulis_baris` membandingkan isi **termasuk** `sumber` — jadi bila impor terakhir datang dari folder lain, seluruh baris yang isinya sama tetap ditulis ulang sebagai revisi baru. Terukur 19 Okt 2026 (sesi 31, aksi #29): impor dari `.uji-data\mejasaham\konfigurasi` menambah **2.328** revisi `notasi_khusus`, dan **seluruhnya hanya berbeda di `sumber`** (`tanggal_selesai`/`keterangan` identik, 0 beda lain). **Terkonfirmasi sesi 32:** impor dari folder **salinan** (`.uji-data\uji-jenis-uji\konfigurasi`, isinya sama) menulis ulang **2.450** baris, sedangkan impor dari folder **aslinya** **0** — jadi bila label tidak ingin berubah, impor dari folder yang sama | Kalau tujuannya hanya satu jenis data, **impor folder yang hanya memuat berkas itu** (salin dulu berkasnya) — atau terima label folder baru sebagai provenance yang memang berlaku. Jangan "memperbaiki" dengan `UPDATE`: `notasi_khusus` append-only (K51, bagian 5) |
| **Lapisan teks PDF publikasi bank tidak menjaga urutan kolom** | Terukur 19 Okt 2026 (aksi #29): pada poster BRIS, teks menaruh "30 Juni 2025 (Diaudit)" **lebih dulu** daripada "30 Juni 2026 (Direviu)", sedangkan render menunjukkan kolom **kiri = 2026**. Angka yang diambil dari urutan teks akan **tertukar tahun** tanpa galat apa pun | Baca angka **dari render** (`baca-pdf.py`/`potong-pdf.py`) dan periksa **kepala kolomnya di gambar**, bukan hanya keberadaan angkanya di teks. Untuk 44 bank nanti ini pemeriksaan wajib: satu angka tertukar tahun lolos semua pemeriksaan lain |
| **Mengubah cara menghitung breadth/rezim, lalu dasbor tetap menampilkan angka lama** | Sejak K61/T80, `konteks_pasar` menyimpan hasil per (snapshot, preset, sumber) **+ `versi_hitung`**. Bila ambang/rumus breadth berubah tetapi `konteks_pasar.VERSI_HITUNG` tidak dinaikkan, baris lama tetap dianggap sah dan dasbor membacanya — angka lama tampak sebagai keadaan hari ini tanpa satu pun galat. Uji `tests/test_konteks_pasar.py::test_versi_hitung_lain_tidak_dipakai` menjaga mekanismenya, bukan disiplinnya | Setiap perubahan arti breadth/rezim **wajib** menaikkan `konteks_pasar.VERSI_HITUNG` (dan, bila perlu, `skor.VERSI_HITUNG` pada perubahan skor). Baris lama tidak perlu dihapus — ia tidak lagi dipakai; jalankan `--saring` pada snapshot terakhir untuk mengisi versi baru |
| **Bundel `dist\MejaSaham` tidak punya folder `_internal\yfinance`, padahal aplikasi berjalan** | PyInstaller menaruh modul **pure-Python** (yfinance, sebagian pandas) di arsip `PYZ`, bukan sebagai folder; yang tampak sebagai folder hanyalah paket yang membawa data/biner (`pandas`, `PySide6`, `numpy`, …). Terukur 19 Okt 2026 (sesi 35): `yfinance` **ada** di `build\MejaSaham\Analysis-00.toc`, dan `--ambil-fundamental --kode BBCA` dari exe berhasil mengimpor serta menulis 4 baris | Jangan menyimpulkan "tidak terbawa" dari daftar folder. Periksa `Analysis-00.toc`/`warn-MejaSaham.txt`, lalu **jalankan perintah yang benar-benar memakai impor malas** itu — di sini `--ambil-fundamental --kode BBCA` pada folder data uji. `WARNING: Hidden import "jinja2" not found` dan `missing module named scipy/openpyxl/…` berasal dari impor opsional pandas/yfinance dan bukan kegagalan |
| **Peringatan `QFontDatabase: Cannot find font directory .../PySide6/lib/fonts` muncul dari exe, bukan hanya uji** | Qt tidak lagi membawa font, dan platform `offscreen` tidak jatuh ke font sistem. Di jendela Windows sungguhan font sistem dipakai. Bukan cacat pengemasan; jendela `offscreen` hanya perlu `QT_QPA_FONTDIR` (lihat baris font di atas) | Untuk smoke test GUI, setel `$env:QT_QPA_PLATFORM='offscreen'` **dan** `$env:QT_QPA_FONTDIR="$env:WINDIR\Fonts"`; jangan menilai tata letak dari tangkapan layar tanpa font. Untuk pemakaian nyata, jalankan tanpa `QT_QPA_PLATFORM` |

---

## 7. Peta berkas

**Modul inti** (`mejasaham/`): `lokasi.py` letak data · `db.py` SQLite + PRAGMA · `skema.py` migrasi
(terbaru: lihat `VERSI_TERBARU` di `mejasaham/skema.py`; langkah 13 menambahkan 008
`parameter_bursa_tanpa_dinyatakan_sumber`, Tahap 2 langkah 1 menambahkan 009 `kandidat_watchlist`,
Tahap 2 langkah 2 menambahkan 010 `batas_risiko_ekuitas_dan_rencana`; migrasi 013/014/015
`aksi_korporasi_pada_posisi`/`jurnal_kepatuhan`/`konteks_pasar_tersimpan` — lihat
`docs/skema-data.md` 5.8–5.10/5.14–5.16) · `ingesti.py` kontrak data & aturan tulis · `pengambil.py`
**satu-satunya** tempat yfinance dikenal · `berkas.py` pembaca CSV impor + rujukan emiten +
pembaca `kalender-bursa.csv` · `ksei.py` daftar emiten dari KSEI (K12) · `kalender.py` kalender
libur bursa dari pengumuman KSEI, termasuk pengurai PDF tanpa dependensi (K11) ·
**`sun.py` kurva imbal hasil SBN dari halaman HPW PHEI (K16)** ·
**`jenis.py` turunan `jenis` emiten dari sector/industry + penulis `emiten.csv`-nya (K21, langkah 13)
+ `kode_bank()` & `tulis_kerangka_rasio_bank()` (K57, aksi #21)** ·
**`notasi.py` notasi khusus & papan pemantauan dari halaman resmi `www.idx.id` (K27, T42)** ·
**`kandidat.py` F4: tesis wajib sebelum watchlist + riwayat revisi (AC-4, T37)** ·
**`risiko.py` F5: ukuran posisi, batas risiko berversi, biaya & slippage, stop bawaan (T38–T40)
+ risiko berjalan dua suku (T45) + deret ekuitas & drawdown terkoreksi arus dana (T46)** ·
**`posisi.py` F11: catat transaksi, posisi & stop terkini, pelanggaran V1/V2/V5/V6, hasil
terealisasi/belum (T43–T44) + aksi korporasi pada posisi: lembar/harga rata-rata diskalakan split,
stop dalam basis `tgl_stop`, dividen per peristiwa, hak & keputusan right issue (T48–T51, K28)** ·
**`dasbor.py` ringkasan harian satu halaman + daftar tindakan menunggu (T47) + temuan
`pembatal_terpicu()` yang dipakai dua tempat (T54); sejak K61 membaca konteks pasar tersimpan** ·
**`konteks_pasar.py` konteks pasar tersimpan: `BarisIndeks`/`KonteksPasar`, bangun dari hasil
`metrik`, `simpan`/`muat` berkunci snapshot+preset+sumber+`versi_hitung` (K61, T80)** ·
**`jurnal.py` F7: satu baris jurnal per transaksi, katalog V1–V7 dihitung dari satu tempat per kode
(V1/V2/V6 dari `transaksi`, V5 dari `posisi`, V3/V4/V7 diturunkan), rekap kepatuhan + expectancy
dalam R (T52–T55)** ·
`konfigurasi.py` parameter bursa bertanggal · `mutu.py` laporan mutu + peringkat ADTV20 +
**cadence cek sumber kedua** + **hari bursa terakhir yang sudah lewat** (T30) · `arsip.py` arsip
snapshot · `potret.py` muat snapshot as-of + **aturan satu label sumber** (`riwayat_sumber`,
`sumber_utama`; T32) · `penyesuaian.py` penyesuaian harga · `metrik.py`
definisi 8.2 · `saring.py` kriteria + preset · `skor.py` z per sektor + peringkat ·
`pengatur.py` urutan kerja · `tampilan.py` format Indonesia · `cli.py` mode kepala + kode keluar ·
**`ui/jendela.py` satu-satunya tempat PySide6 boleh diimpor** (lima layar PRD 11) ·
**`ui/tabel.py` bentuk tabel jendela, bebas Qt** (diuji tanpa layar) ·
**`ui/tulis.py` tindakan tulis jendela: ringkasan konfirmasi + pemanggilan jalur inti, bebas Qt**
(aksi #19 tahap 1 + impor & ukuran patuh aksi #19b, cadangan/daftar aksi #19c, dan
**`ubah-stop` + keputusan right issue aksi #19d** — T70/T72/T73/T74) ·
**`ui/pekerja.py` pekerjaan berat di utas pekerja** (T65) + **GC siklik dimatikan selama tugasnya**
(T68).

**Build** (`tools/`): **`build_exe.py`** satu daftar argumen PyInstaller onedir + pemeriksaan hasil
(T81) · **`entry_exe.py`** titik masuk bundel yang memanggil `cli.main` · `extract_docx.py`
(turunan PRD). **Dependensi build** di `requirements-build.txt` (PyInstaller + transitive; tidak
masuk bundel runtime).

**Uji** (`tests/`, 908 uji): **`test_pengemasan.py` (2, sesi 35: perintah build tetap `--onedir`,
`--add-data mejasaham/defaults` tepat, `--hide-console` di Windows, dan sepuluh template bawaan
ada) · **`test_ui_tulis.py` (33, baru aksi #19: lapisan tulis jendela **tanpa
Qt** — ringkasan konfirmasi memuat angka yang akan ditulis, isian wajib yang kosong ditolak sebelum
pekerjaan dimulai, **barisnya sama dengan baris perintah** untuk ketiga pencatat (dua basis data
dibangun identik, dibandingkan pada kelima view), revisi jurnal menambah revisi bukan menimpa, kunci
tulis → "belum menulis apa pun" tanpa satu baris pun tertulis, dan galat selain kunci **tidak**
ditelan · **+7 uji aksi #19b**: ringkasan impor memuat **jumlah baris per tabel** (dan menyebut
berkas yang tidak ada), impor dari jendela **sama** dengan `--impor` pada empat tabel + `snapshot`,
yang ditulis adalah **objek yang dikonfirmasi** (berkasnya dihapus sesudah konfirmasi), berkas yang
ditolak pembaca ditolak **dengan pesan yang sama** + 0 baris, impor yang terkunci → 0 baris &
"belum menulis apa pun", dan gagal-karena-kunci **tidak** menambah penantian kedua lewat catatan log)
· **+8 uji aksi #19d (sesi 18)**: ringkasan ubah stop memuat stop lama → baru + `tgl_stop` yang akan
disimpan (dan menolak posisi kosong / stop yang tidak diisi), baris `posisi` dari jendela **sama**
dengan `--ubah-stop` (termasuk `tgl_stop` dan **V5** saat stop diturunkan), keputusan `jual_hmetd`
dari jendela **sama** dengan `--putuskan-right-issue`, **`tebus` tanpa transaksi ditolak sebelum
pekerjaan dimulai** (pesannya menyebut jendela tidak mencatatkan transaksinya), `tebus` yang menunjuk
transaksi **tidak** menambah transaksi kedua, isian yang tidak dipakai keputusan ditolak berisik,
dan ringkasan keputusan menyebut haknya **petunjuk** beserta catatan lot K31
· **`test_ui_tabel.py` (13, baru: bentuk tabel jendela **tanpa Qt** —
kepala skor memakai `saring.FAKTOR_SAH` (bukan daftar salinan), nilai yang tidak ada jadi "—" bukan
nol, kriteria yang tidak berlaku tetap tampil (AC-16), penjaga bahwa berkasnya sendiri tidak
mengimpor Qt, dan **+3 uji aksi #19b**: label rencana/posisi memuat ID yang ditulis beserta
pengenalnya, stop yang tidak diketahui tetap "—", serta pilihan "tanpa rencana/posisi/rencana baru"
dinyatakan bukan kotak kosong) · **+3 uji aksi #19d**: `label_transaksi` menyebut tanggal (yang
ditulis tetap `id_transaksi`-nya), pilihan kosong "posisi aktif"/"transaksi pembelian" dinyatakan
bukan kotak kosong, dan tabel hak right issue menyebut tenggat yang **belum dinyatakan sumbernya**
(K29) serta hak yang tidak dapat dihitung **beserta sebabnya** — bukan nol · **`test_ui_jendela.py` (46, baru: jendela di platform `offscreen` —
lima tab PRD 11,
layar terisi lewat utas pekerja → signal → widget, daftar kode & preset terisi, kata "kandidat"
ditahan tanpa data notasi (K19), sebab daftar peringkat kosong disebut, tabel peringkat terisi,
teks kalkulator risiko **sama persis** dengan `--hitung-risiko`, kotak isian kosong ≠ 0, kode salah
eja ditolak, kode tanpa tesis ditolak (PRD 9.6), dua entri kandidat ditolak, hasil lama dibuang saat
gagal, dan penutupan jendela menunggu pekerja latar selesai (dan batas tunggu yang lewat dilaporkan, bukan diabaikan), serta pekerja latar melaporkan hasil & kegagalannya — **+4 uji aksi #20/T68**: GC siklik mati selama tugas berjalan dan hidup lagi sesudahnya, keadaan pemanggil yang sudah mematikannya tidak dibalik, **jalur tunggu penutupan** juga mematikannya (diukur dari utas uji biasa, bukan dari `Pekerja` yang sudah mematikannya sendiri), dan dua pemakai bersarang tidak saling menyalakan) · **+8 uji aksi #19 tahap 1**: menulis transaksi
dari formulir layar 11.3 (baris tertulis + pesan bertahan sesudah layar dimuat ulang), konfirmasi
yang dibatalkan tidak menulis apa pun, menyimpan rencana dari hasil yang **sedang tampil** di 11.4
(ringkasan konfirmasi dibandingkan dengan rencana yang tersimpan), menolak menyimpan tanpa hasil
hitungan, isian yang berubah membatalkan hasil lama, catatan jurnal untuk baris **terpilih** di 11.5,
menolak menulis tanpa baris terpilih, dan kunci tulis yang pesannya menyebut "belum menulis apa pun"
tanpa menambah baris · **+6 uji aksi #19b**: impor dari **menu Berkas** menulis sesudah konfirmasi
yang menyebut jumlah barisnya (dan pesannya menyebut apa yang **belum** ikut berubah), berkas rusak
menyebut sebabnya tanpa dialog tulis & tanpa menulis, posisi dipilih **dari daftar** (jendela tidak
memilih entri pertama; transaksinya menempel pada posisi yang dipilih), pilihan tidak ikut pindah
kode, revisi rencana dipilih dari daftar (dan daftarnya disegarkan sesudah menyimpan), serta
**"Pakai ukuran patuh" menghasilkan blok hasil & baris `rencana` yang sama dengan
`--hitung-risiko … --pakai-ukuran-patuh`** (dua basis data identik)) · **+5 uji aksi #19d**: formulir
ubah stop di 11.1 menulis revisi `posisi` (dan pilihannya tidak dipilihkan jendela), ubah stop tanpa
posisi terpilih tidak memunculkan dialog tulis & tidak menulis, keputusan right issue untuk baris
terpilih menulis barisnya lalu layarnya dimuat ulang (`BELUM DIPUTUSKAN` → `sudah diputuskan`),
keputusan tanpa baris terpilih ditolak tanpa dialog, dan kotak `tebus` hanya berisi transaksi beli
posisi itu **serta** isian yang tidak dipakai keputusan aktif dimatikan + dikosongkan ·** **`test_jurnal.py` (42, baru: F7 — tiap kode V1–V7 dibaca dari satu
tempat & tidak ada yang terhitung dua kali, V3 dari angka rencana yang dieksekusi, V4 membandingkan
harga dalam **satu basis** melewati split dan berhenti sebagai "tidak dapat dinilai" bila penutupan
acuan tidak ada, V7 memakai temuan yang sama dengan dasbor, rasio kepatuhan = transaksi patuh ÷
seluruh transaksi, pemisahan mode & bulan, expectancy per putaran tertutup lengkap dengan 1R dari
revisi rencana **saat eksekusi**, dan penjaga mesin: baris kosong, dua rantai jurnal untuk satu
transaksi, `UPDATE`/`DELETE`)** ·**`test_aksi_korporasi_posisi.py` (41, baru: aksi korporasi pada posisi
— AC-18 diperiksa angkanya, lembar berpecahan dilaporkan bukan dibulatkan, stop tanpa basis
berstatus tidak dinilai, V5 palsu dicegah, dividen per peristiwa, right issue & `CHECK`-nya,
hak yang bukan kelipatan lot disebut lebih awal (K31); **38 dari uji intinya terbukti gagal pada
kode lama**) ·
**`test_posisi.py` (57, F11 — lembar/harga rata-rata/hasil
diturunkan dari transaksi, V1/V2/V5/V6 terdeteksi & tersimpan, penjualan melebihi milik ditolak,
transaksi bertanggal mundur ditolak, biaya all-in tidak menambah PPh dua kali, AC-6 dua arah, dan
AC-13 dengan deret yang membuat jawaban mentah ≠ terkoreksi)** ·
**`test_dasbor.py` (22, baru: kandidat hanya dari skor tersimpan, peringatan snapshot basi AC-8,
empat jenis tindakan menunggu, **konteks pasar (aksi #20/K58) — dasbor dan saringan tidak boleh
berbeda pada snapshot yang sama (uji yang gagal pada kode lama karena kalimat tetapnya), IHSG +
perubahannya, NETRAL beserta sebabnya saat IHSG belum ada dan saat 199 bar belum cukup untuk MA200,
breadth mengikuti preset yang menghasilkan skor tersimpan, dan tanpa preset sama sekali breadth
dinyatakan "tidak dihitung" — bukan dihitung dengan ambang tebakan**) ·
`test_notasi_idx.py` (**10**: pengambil notasi IDX — huruf
tergabung dibaca per huruf, kode 5 huruf ikut terbaca, tanggal halaman (dan penolakan halaman tanpa
tanggal / dengan dua tanggal), berkas bertambah + yang hilang ditutup + idempoten + baris isian
tangan tidak disentuh, dan bulat-balik sampai `--saring` berhenti menyebut "PERINGKAT SEMENTARA") ·
`test_risiko.py` (62, rumus PRD 9.7 diuji dengan angka yang
bisa diperiksa tangan — lembar mentah, pagu bobot/sektor/likuiditas/kas, risiko nominal dari ukuran
akhir; dua arah pembulatan yang disengaja (biaya ke atas, stop ATR ke bawah); K23 diuji **dua arah**
(tarif jual yang sudah memuat PPh tidak ditambahi, yang tidak memuat ditambahi); batas yang datanya
tidak ada menjadi "tidak dinilai" bukan longgar; perilaku menolak PRD 9.7; dan penjaga mesin —
`CHECK (stop < harga_masuk)`, trigger append-only, revisi rencana) ·
`test_kandidat.py` (23, termasuk penembakan `CHECK` AC-4 langsung ke basis data) ·
`test_kalender_ksei.py` (28, pengambil kalender KSEI: dua gaya teks
PDF, enam pemeriksaan penolakan, berkas tulis–baca-ulang, dan **enam uji K17/P19** — revisi lebih
lama dipakai hanya bila tanggalnya identik, tidak dicari bila berkasnya rusak lebih dalam) ·
`test_sun_phei.py` (17: pengambil imbal hasil SUN — tanggal dari pernyataan sumbernya, enam
penolakan, dan bulat-balik lewat pembaca impor) · `test_ksei_emiten.py` (34, jalur
daftar emiten termasuk `tanggal_notasi`) · `test_ingesti.py` (72, termasuk 10 uji K13/U18, penjaga
"setiap kolom tabel ikut disidik saat menulis", sumber per baris kalender, **sumber per baris
`rasio_bank` (K78)**, dan penjaga hari bursa
yang belum terjadi) · `test_mutu_adtv.py` (37:
peringkat ADTV20, cek sumber kedua, **cadence** — batas 7 hari, cek belum lengkap, tanggal tak
terbaca) · `test_db.py` (37, termasuk append-only, CHECK `cek_sumber_kedua`, asal tanggal
publikasi migrasi 007, dan **11 uji migrasi 008/K22/K23 langsung ke mesin** — `minimum` boleh NULL
tetapi `0` dan NULL harus tetap bisa dibedakan, `asal_berlaku_sejak` tak dikenal/diisi kosong
ditolak CHECK, komponen all-in append-only dan tidak boleh yatim, serta penjaga bahwa daftar
nilai sahnya dipinjam dari `skema.py` bukan disalin; **+3 uji migrasi 012**: `MODE_SAH` satu
tempat untuk `posisi`/`risiko`/skema, setiap mode sah diterima & yang tak dikenal ditolak CHECK,
dan `arus_dana` NULL ≠ `0`) · `test_fundamental_yfinance.py` (**13**: pemetaan laporan keuangan
sumber → baris `fundamental` **tanpa jaringan** — nama baris arus kas metode langsung, mata uang
yang tidak boleh ditebak, jumlah saham hanya dari neraca, dan artefak penyimpanan vs salah baca) ·
`test_impor_berkas.py` (36, termasuk jalur `tanggal_notasi` sampai potret, asal tanggal
publikasi, **dua uji K78** (`sumber` per baris `rasio_bank` sampai potret; sel `sumber` kosong
ditolak), dan **tiga uji aksi #18**: kolom berlebih yang berisi **menolak** berkas sambil
menyebut baris + isi yang akan hilang, nilai yang dikutip tetap terbaca utuh, dan kolom berlebih
yang **kosong** tetap diterima — satu di antaranya **terbukti gagal pada kode lama**) ·
`test_sumber_harga.py` (9: satu label per snapshot — dua uji regresinya terbukti gagal
pada kode lama) · `test_saring.py` (20, termasuk **dua uji K19** — tanpa data notasi kriterianya
tidak diterapkan, dan terbukti `lolos=True` pada kode lama)
· `test_skor.py` (15) · `test_metrik.py` (27) · `test_penyesuaian.py` (20) · `test_potret.py` (5) ·
**`test_konfigurasi.py` (63: termasuk 14 uji K22/K23 — `minimum` tidak ada → NULL **bukan 0**,
komponen `sudah_termasuk` tak dikenal/ganda ditolak **sebelum apa pun tersimpan**, entri all-in
idempoten walau urutan komponennya dibalik, `asal_berlaku_sejak` tak dikenal ditolak, dan asal
tanggal tidak bisa diubah diam-diam)** ·
**`test_jenis_emiten.py` (38: aturan turunan tanpa jaringan — bank → `bank_keuangan`,
`Financial Services` + `Insurance` → `umum`, sector/industry kosong → **tidak ada baris**,
`siklikal_komoditas` **tidak pernah** dihasilkan dari sektor komoditas; jalur lengkap basis data →
berkas → dibaca ulang → diimpor; berkas yang sudah ada ditolak tanpa `--timpa-jenis`;
`dicatat_pada` baru menambah revisi; berkas separuh tidak ditinggalkan; tiga keadaan `--saring`;
**+5 uji kerangka rasio bank (K57, aksi #21)**: kerangka berisi kode bank & seluruh sel selain
`kode` kosong dengan kepala yang sama dengan template, ditolak berisik tanpa `jenis` **tanpa**
menulis berkas, berkas yang sudah berisi tidak ditimpa (isinya diperiksa sama), template bawaan
boleh ditimpa, dan `--impor` atas kerangka kosong gagal berisik dengan `rasio_bank` tetap 0 baris)** ·
**`test_glif_teks.py` (2: penjaga glif teks — memindai **byte** berkas di `mejasaham/` untuk urutan
mojibake (UTF-8 dibaca cp1252 lalu disimpan lagi), dan uji kedua menjaga agar penjaganya tidak
menjadi kosong; **terbukti gagal** atas berkas `metrik.py` yang lama: 12 `≤`, 10 `÷`, 5 `→`)** ·
`test_defaults.py` (13) · `test_lokasi.py` (6) ·
`test_batas_ui.py` (3).

**Data uji nyata** (gitignored, jangan di-commit): `.uji-data/riset-idx/rekonsiliasi-spt-per-kode-20261016.csv`
(**1.118 baris** = satu baris per rekaman SPT × kode; 162 kode unik; kolomnya termasuk `status_tabel`,
`aksi`, `dasar_aksi`, `pasar_aksi`, `sesi_aksi`, `tanggal_efektif`, `asal_tanggal_efektif`,
`status_verifikasi`, `upt_penutup_nomor`, `catatan`, `bukti_kutipan`) ·
`.uji-data/riset-idx/ringkasan-suspensi-per-kode-20261016.csv` (**162 kode**: mulai episode terpantau,
status/aksi terakhir, penutup UPT, riwayat suspensi API, catatan) ·
`.uji-data/riset-idx/rekonsiliasi-spt-per-kode-20261016.txt` (ringkasan angka + temuan: kode tanpa
`Aktif`, kode dengan dua mulai ≤45 hari, kode tanpa riwayat API, pasangan UPT) ·
`.uji-data/riset-idx/verdict-spt-20261016.json` (verdict mentah **per dokumen**: nomor, tanggal,
jumlah baris/kode, sebaran status, angka yang disebut kalimatnya, kalimat keputusan apa adanya,
selisih bilingual, `kembar_dengan`) · `.uji-data/riset-idx/rekonsiliasi-upt-per-kode-20261012.csv`
(**41 baris** sisi UPT) ·
`.uji-data/riset-idx/impor-suspensi-20261016/notasi-khusus.csv` (**171 baris impor / 159 kode**,
langkah 3 — `kode;jenis;tanggal_mulai;tanggal_selesai;keterangan`; `keterangan` memuat nomor
pengumuman, berkas PDF, tindakan, pasar, sesi, asal tanggal mulai, penutup UPT, dan penanda temuan) ·
`.uji-data/riset-idx/impor-suspensi-20261016/bukti-keadaan.txt` (angka + daftar episode per kode +
penutup UPT mana yang dipakai) · `.uji-data/riset-idx/buat-impor-suspensi.py` (**pembuat berkas itu**,
tanpa jaringan dan tidak menyentuh basis data; seluruh penalaran tanggalnya di docstring fungsi
`_kelompokkan`) ·
`.uji-data/uji-impor-suspensi/` (bukti langkah 3: **salinan** `.uji-data/mejasaham` + impornya.
`bukti-1`/`bukti-3` keadaan sebelum–sesudah (notasi 4.552 → 4.723, suspensi 1.926 → 2.097, terbuka
142 → 280) · `bukti-2`/`bukti-4` `--saring` sebelum–sesudah (likuid **205 → 201**, masih PERINGKAT
SEMENTARA) · `bukti-5` daftar episode per kode · `bukti-6`/`bukti-7` keadaan & `--saring` **sesudah
penanda dilepas** (bukti K51: 2.154 baris revisi, "Kandidat teratas") · `bukti-8` jalan ulang
pembuatnya · `bukti-9` efek impor pada semesta likuid: **KJEN, SINI, UNSP, ZATA** keluar karena
suspensi multi-kode) dan `.uji-data/uji-impor-suspensi-langkah4/` (basis data uji terpisah untuk
membuktikan pelepasan penanda; **sudah dibuang** setelah `bukti-6`/`bukti-7` diambil) ·
`.uji-data/riset-idx/buat-tanpa-penanda.py` (**pembuat berkas turunan tanpa penanda**, langkah 4:
membuka basis data **read-only**, mengambil revisi terkini tiap kunci, melepas **hanya** penanda
`IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAKAN`, menulis CSV dengan pemisah `;` + kutip yang benar, lalu
**membaca ulang dengan `mejasaham.berkas.baca_folder`** sebagai pemeriksa bulat-balik) ·
`.uji-data/riset-idx/tanpa-penanda-20261016/` (`notasi-khusus.csv` **2.447 baris tanpa penanda** +
`bukti-keadaan.txt`) ·
`.uji-data/uji-lepas-penanda/` (**bukti langkah 4 / aksi #15, sesi 5**: `bukti-0` `--saring` sebelum ·
`bukti-1` cadangan · `bukti-2` impor berkas langkah 3 ke basis data utama (171 baru) · `bukti-3`
`--saring` sesudahnya (likuid 201, masih PERINGKAT SEMENTARA) · `bukti-4` pembangun berkas tanpa
penanda · `bukti-5` impor 2.447 revisi baru · `bukti-6` `--saring` **"Kandidat teratas"** · `bukti-7`
keadaan basis data + hash berkas konfigurasi · `notasi-khusus-sebelum-diganti.csv` salinan berkas
konfigurasi lama) ·
`.uji-data/uji-tinjauan-k46/` (**bukti tinjauan visual K46 / aksi #16, sesi 6**: `bukti-1`/`bukti-2`
halaman 1–2 pengumuman 20 Feb 2024 sebagai PNG (itulah "tinjauan visual"-nya) · `bukti-3` teks
ekstraksi berkas yang sama · `bukti-4` teks UPT penutup MTFN 29 Agu 2024 (yang mencabut delapan
pengumuman, termasuk yang 20 Feb 2024) · `bukti-5` perbandingan status ke-34 kode sebelum–pada
pengumuman (**34 identik · 0 berbeda**) · `bukti-6` dokumen lama yang menempel pada episode baru
(**1 baris dari 2.447**) · `bukti-7` keadaan 34 kode di basis data · `bukti-8` rantai ARTI · `bukti-9`
pemeriksaan K41 (`ELTY` 0 baris, penanda 0 kali) · `bukti-keadaan.txt` ringkasan perintah+angka) ·
pembuatnya `.uji-data/riset-idx/tinjauan-k46/` (`render-pdf.py`, `status-sebelum.py`,
`serap-dokumen-lama.py`, `keadaan-34-kode.py`, `keadaan-per-kode.py`, `cek-k41.py` — semuanya
**read-only** terhadap basis data) ·
`.uji-data/riset-idx/k53-k54/` (**pembangun + pemeriksa aksi #17, sesi 7**: `buat-k53-k54.py` — membuka
basis data **read-only**, memakai `buat-impor-suspensi.py` sebagai pustaka untuk bentuk `keterangan`,
menerapkan K53 + K54, **idempoten** (kalimat catatannya sendiri dibuang lebih dulu), lalu menulis CSV
dengan `csv.writer` + **membaca ulang lewat `mejasaham.berkas.baca_folder`**; 126 syarat diperiksa) ·
`keadaan-notasi.py` (pencetak keadaan `notasi_khusus`, dipakai sebelum/sesudah impor) ·
`ukur-potong-keterangan.py` + `potong-keterangan.txt` (**pengukur cacat `;`**: 66 dari 171 baris
berkas langkah 3 kehilangan ekornya saat impor, beserta ekor yang hilang) · `recon.py` + `recon.txt`
(bahan mentah 34 baris K46, UPT MTFN/ARTI/ELTY) · `keluaran/notasi-khusus.csv` (2.450 baris) dan
`keluaran-dari-cadangan/notasi-khusus.csv` (**hash SHA-256 sama** — bukti idempotensi) ·
`bukti-keadaan.txt` (angka + 126 pemeriksaan + baris MTFN/ELTY/ARTI apa adanya) ·
`periksa-aksi-18.py` (**pemeriksa aksi #18**: penanda yang kembali muncul, keempat kode K47, segmen
terakhir contoh baris) ·
`.uji-data/uji-aksi-18/` (**bukti aksi #18, sesi 8**: `bukti-0` cadangan · `bukti-1` impor **65 baris
baru** · `bukti-2` keadaan sesudah (penanda `TANGGAL_MULAI…` 66, `AKTIF_DUA_KALI…` 4, `kutipan
keputusan:` 172) · `bukti-3` `--saring` “Kandidat teratas” · `bukti-4` pytest **768 lulus** ·
`bukti-5` uji baru dijalankan pada **kode lama** di worktree `HEAD`: **1 gagal, 37 lulus** ·
`bukti-6` ringkasan satu halaman aksi #18) ·
`.uji-data/uji-k53-k54/` (**bukti aksi #17, sesi 7**: `bukti-0` keadaan sebelum · `bukti-1` cadangan
pra-impor · `bukti-2` impor pertama · `bukti-3` keadaan sesudah · `bukti-4` `--saring` sesudahnya ·
`bukti-5` pytest pertama · `bukti-6` impor koreksi (34 baris baru) · `bukti-7` keadaan final ·
`bukti-8` `--saring` final · `bukti-9` ringkasan + hash · `bukti-10` pytest final) ·
`.uji-data/uji-jendela/` (**bukti panel jendela / aksi #10 tahap 1, sesi 9**: **salinan**
`.uji-data/uji-jurnal` (999.421 bar, snapshot 12, 6 transaksi, 4 posisi, rencana #1 TLKM & #2 ASII,
122 baris notasi) supaya folder data lain tidak tersentuh. Isinya `jendela/`: `bukti-1-kerangka.txt`
(lima layar + jumlah preset & kode), `bukti-2-dasbor.txt`, `bukti-3-saring.txt` (**"Hasil saringan:
kandidat"**, likuid 225 · lolos 9 · 9 baris peringkat), `bukti-4-detail-tlkm.txt` (identitas, tesis,
kriteria per baris termasuk yang **tidak berlaku** untuk non-bank), `bukti-5-risiko-sama-dengan-baris-perintah.txt`
(**24 baris, 0 perbedaan** dengan `--hitung-risiko`), `bukti-6-jurnal.txt` (6 keputusan · patuh 1 ·
7 pelanggaran), `bukti-7-gagal-tampil-di-layar.txt` (kode salah eja + kode tanpa tesis, dan kotak
hasilnya **kosong** — bukan angka lama), `bukti-8-ringkasan.txt`, serta `tangkapan-1..5-*.png` (tiap
layar dirender jadi gambar; lihat jebakan `QT_QPA_FONTDIR` di bagian 6). Pembuatnya
`.uji-data/riset-idx/jendela/` (`bukti-jendela.py` untuk teks, `tangkap-layar.py` untuk PNG;
keduanya menyetel `MEJASAHAM_DATA` ke salinan itu). **Jangan** memakai folder ini sebagai sumber data
pasar: skornya ditulis ulang oleh tombol "Jalankan saringan" di salinan) ·
`.uji-data/uji-dasbor/` (**bukti aksi #20, sesi 10**: **salinan** `.uji-data/uji-jurnal` — 999.421
bar, snapshot 12, 6 transaksi, 4 posisi. Isinya `bukti/`: `bukti-0-dasbor-kode-lama.txt` (keluaran
kode **HEAD** atas folder yang sama: 2,8 dtk, tanpa baris `Pasar`, **dengan** kalimat tetap
"rezim pasar & breadth belum dapat dinilai …"), `bukti-1-saring.txt` (`breadth 39,1% · rezim
RISK-OFF`, likuid 225), `bukti-2-dasbor.txt` (baris `Pasar : IHSG 6.093 (09 Okt 2026) · +62 (+1,03%) ·
88 dari 225 emiten likuid (preset kualitas-nilai/v1) · breadth 39,1% · rezim RISK-OFF`),
`bukti-3-pytest.txt` (**803 lulus**), `bukti-4-jendela-proses-mati.txt` (contoh proses yang mati
sebelum T68), dan `bukti-keadaan.txt` (satu halaman: perintah, angka, biaya, dan tabel angka
percobaan GC). Pembuatnya `.uji-data/riset-idx/dasbor/bukti-dasbor.py` — read-only selain folder
bukti ini, dan `--saring` di dalamnya hanya menulis skor ke **salinan**) ·
`.uji-data/uji-kerangka-rasio-bank/bukti/` (**bukti aksi #21, sesi 10**: `bukti-1-kerangka.txt`
(keluaran perintahnya) · `bukti-2-isi-kerangka.txt` (49 baris, seluruh sel selain `kode` kosong,
berkas apa adanya) · `bukti-3-impor-ditolak.txt` (**keluar 1**, `rasio-bank.csv baris 36: kolom
`periode` wajib diisi`, 49 baris) · `bukti-4-keadaan-basis-data.txt` (`--saring` tetap jalan) ·
`bukti-5-keadaan-basis-data.txt` (`rasio_bank` **0 baris**, `bank_keuangan` **49**) ·
`bukti-keadaan.txt`). Pembuatnya `.uji-data/riset-idx/kerangka-rasio-bank/bukti-kerangka.py`;
berkas yang dibuatnya ada di `.uji-data/uji-jenis/konfigurasi/rasio-bank.csv` (basis datanya
**tidak** disentuh) ·
`.uji-data/riset-idx/pyside6-gc/` (**dua percobaan repro cacat PySide6 6.12 + CPython 3.14**,
sesi 10: `repro-minimal.py` — 30 putaran, **tidak** memicu; `repro-jendela.py` — pohon
`QMainWindow`+`QTabWidget`, tiga pekerja, jalur tunggu `processEvents`+`wait(50)`, atribut pemilik
ditimpa sementara pekerja lama berjalan; 12 putaran × 4 jalan, **tidak** memicu). Ringkasannya di
`docs/riset-pyside6-gc-2026-10.md`; keduanya bisa dijalankan mandiri (`QT_QPA_PLATFORM=offscreen`)
dan boleh dilampirkan ke laporan upstream sebagai "yang sudah dicoba") ·
`.uji-data/mejasaham.db` (999.421 bar harga, 916 emiten, 4 snapshot; **kalender 2026–2027 terpasang** sejak langkah 8) ·
`.uji-data/konfigurasi/kalender-bursa.csv` (730 baris dari pengumuman KSEI; template lamanya
disimpan di `.uji-data/uji-kalender/kalender-bursa-template-lama.csv`) ·
`.uji-data/konfigurasi/emiten.csv` (semesta 916 kode + catatan 57 kode yang
dikeluarkan) · `.uji-data/refresh-973.log` (bukti penolakan gerbang) · `.uji-data/saring.txt` ·
`.uji-data/bukti-u18-57-kode.txt` + `.uji-data/uji-u18-refresh.log` (bukti K13 atas sumber nyata,
folder datanya `.uji-data/uji-u18/`, 13 kode) · `.uji-data/uji-u18-973/` (semesta 973 kode: berkas
rujukan siap pakai, refresh penuhnya belum dijalankan — basis datanya masih **0 snapshot**, sebab
prosesnya dihentikan di tengah dan AC-19 menahannya: tidak ada yang tertulis separuh) ·
`.uji-data/uji-cadence/` + `.uji-data/uji-cadence-refresh/` (salinan basis data uji untuk
memverifikasi cadence cek sumber kedua; buktinya `bukti-*.log`, dan `harga-harian.csv` di dalamnya
**berisi 20 baris pembanding buatan** — bukan data pasar sungguhan, jangan dipakai berhitung) ·
`.uji-data/uji-tanggal-notasi/` (bukti langkah 7: semesta **973 kode** hasil `--ambil-emiten`
9 Okt 2026 dengan `tanggal_notasi` terisi 888 baris, basis datanya, dan arsip snapshot
`arsip-snapshot/2026-10-09/snapshot-1/` yang isinya sama persis dengan basis data) ·
`.uji-data/uji-kalender/` (bukti langkah 8: `bukti-ambil-kalender.log` keluaran perintah,
`bukti-keadaan.txt` isi tabel + temuan mutu, `bukti-isi-kalender.txt` 42 libur resmi beserta
nomor pengumumannya, dan salinan template kalender yang digantikan) ·
`.uji-data/uji-p17/` (bukti langkah 9: **salinan** basis data `.uji-data/uji-cadence` — label
utama `yfinance/Yahoo Finance (tidak resmi)` 999.421 bar + `pembanding-uji` 21 bar; berisi
`bukti-saring-p17.txt` yang berbunyi **likuid 235** dan `bukti-cek-sumber-p17.txt` yang identik
dengan bukti lama. Dua folder itu **jangan** dipakai sebagai sumber data pasar: bar
pembandingnya buatan) ·
`.uji-data/uji-sun/` (bukti langkah 10: `konfigurasi/imbal-hasil-sun.csv` hasil `--ambil-sun`
atas sumber nyata — satu baris, SUN 10 tahun 7,1845% per 09 Okt 2026, beserta penjelasan
template di dalamnya) ·
`.uji-data/uji-kalender-2025/` (bukti K17: `kalender-bursa.csv` 1095 baris untuk 2025–2027
beserta blok penjelasan yang menyebut revisi mana yang dipakai dan mengapa, dan
`bukti-ambil-kalender-p19.txt` keluaran perintahnya) ·
`.uji-data/uji-jenis/` (bukti langkah 13, K21: **salinan** basis data `.uji-data` + `emiten.csv`
semesta 916 kode. `bukti-ambil-jenis.log` = keluaran `--ambil-jenis --timpa-jenis` atas data
nyata: **49 `bank_keuangan`** (AGRO, BBCA, BBNI, BBRI, BJBR, BMRI, BRIS, BTPS, …) · **862 `umum`**
· **5 kosong** (BOSS, DEAL, ETWA, KAYU, LAPD — sumbernya tidak menyatakan sector/industry).
`bukti-impor-jenis.log` = `--impor` atas berkas itu (916 baris baru; basis datanya kini 1.832 baris
`emiten` = 916 kode × **2 revisi**, bukti append-only). `bukti-saring-jenis.txt` = `--saring` yang
berbunyi `49 bank_keuangan (dari data) · 862 umum (dari data) · 0 siklikal_komoditas · 5 belum
terisi`. Basis datanya salinan, jadi aman diutak-atik; **jangan** dipakai sebagai sumber data
pasar tanpa sadar bahwa isinya salinan) ·
`.uji-data/uji-risiko/` (bukti Tahap 2 langkah 2, F5: **salinan** `.uji-data/mejasaham.db` —
999.421 bar, 916 emiten, 7 snapshot, skema 10. Dua belas `bukti-*.txt` berisi keluaran perintah
beserta kode keluarnya (`bukti-9-pelanggaran-ditolak.txt` keluar **1**: rencana dengan total risiko
5,06% memang tidak boleh disimpan), dan `bukti-keadaan.txt` memuat isi tabelnya: `preset_risiko`
(5 baris), `ekuitas_harian` **dua revisi di hari yang sama** (bukti T40), `rencana` #1 TLKM dan
#2 ASII r1/r2 (yang terakhir **544 bp**, pelanggaran yang diterima tercatat), serta penjaga
append-only yang menolak `UPDATE rencana` atas data nyata) ·
`.uji-data/uji-sektor/` (bukti langkah 2b & 2c: **salinan** `.uji-data/uji-risiko/mejasaham.db` +
`konfigurasi/emiten.csv` hasil `--ambil-jenis` (916 baris, kolom `sektor_sumber` terisi) +
`konfigurasi/notasi-khusus.csv` hasil `--ambil-notasi` (122 baris, 68 papan pemantauan khusus).
`bukti-ambil-jenis-sektor.log` = pengambilan sektor (49 bank, 862 umum, 5 kosong) ·
`bukti-hitung-risiko-sektor.txt` = batas sektor **kini dinilai** (21.600 lembar, taksonomi
`sektor_sumber` disebut) · `bukti-ambil-notasi.txt` = dua kali jalan (122 baru, lalu 0 baru/0
ditutup) · `bukti-saring-notasi.txt` = **"Kandidat teratas"**, likuid 227, bukan lagi "PERINGKAT
SEMENTARA") ·
`.uji-data/uji-jurnal/` (bukti Tahap 3 langkah 1, F7: **salinan** `.uji-data/uji-aksi-korporasi` —
999.421 bar, 12 snapshot, 6 transaksi, migrasi **014 terpasang**. Sepuluh `bukti-*.txt` bernomor:
`bukti-1-jurnal.txt` (6 keputusan · patuh 1 · 7 pelanggaran, masing-masing menyebut transaksi mana
yang menerimanya) · `bukti-2-rekap.txt` (**V3 ASII 5,44% > 5,00%**, expectancy "belum dapat
dinilai", drawdown 0,39%, rekap per bulan) · `bukti-3-rekap-okt-2026.txt` (bulan lain pindah ke
"di luar periode") · `bukti-4`/`bukti-5` (catatan jurnal r1 → r2, `Revisi r1 disimpan, bukan
ditimpa`) · `bukti-6-jurnal-asii.txt` (catatan berdampingan dengan pelanggarannya) ·
`bukti-7`/`bukti-8` (dua penolakan berisik: transaksi tidak ada, bulan salah bentuk — keluar 1) ·
`bukti-9-jurnal-tandai-selesai-lalu-jurnal.txt` (jurnal tersaring per kode: `--jurnal --kode TLKM`) ·
`bukti-10-perbandingan-kode-lama.txt` (perintahnya **tidak dikenal** di HEAD, katalog lama masih
V1/V2/V5/V6 + "belum dihitung" V3/V4/V7) ·
`bukti-keadaan.txt` (isi tabel `jurnal` 2 revisi, penjaga yang benar-benar menolak baris kosong,
rantai kedua, `UPDATE`, dan `DELETE`, serta **V4 diperiksa** pada MLPT: rata-rata Rp 750 vs
penutupan Rp 1.125 → tidak rugi, jadi V4 memang tidak berlaku). Basis datanya salinan;
**jangan** dipakai sebagai sumber data pasar tanpa sadar isinya salinan) ·
`.uji-data/uji-posisi/` (bukti Tahap 2 langkah 3, F11: **salinan** `.uji-data/uji-sektor` —
999.421 bar, 10 snapshot, rencana #1 TLKM & #2 ASII. Di folder ini migrasi **012 terpasang**
(11 → 12) dan alurnya dijalankan atas data nyata: `bukti-2-catat-transaksi-beli.txt` (beli TLKM
10.800 lbr @2.320 dari rencana #1, biaya Rp 43.200 dihitung dari tarif all-in, stop posisi diambil
dari rencana = Rp 2.180, **0 pelanggaran**) · `bukti-3-posisi.txt` (risiko terbuka Rp 1.512.000) ·
`bukti-4-rencana-setelah-posisi.txt` (**AC-6**: Rp 1.512.000 + Rp 159.600 = Rp 1.671.600, rencana
yang sudah dieksekusi tidak dihitung dua kali) · `bukti-6-stop-turun-v5.txt` (stop 2.240 → 2.100
tercatat **V5**) · `bukti-8-jual-sebagian.txt` + `bukti-9-posisi-setelah-jual.txt` (jual 5.000 lbr
@2.360 → hasil terealisasi Rp 150.000, sisa 5.800 lbr) · `bukti-11-drawdown.txt` (setoran Rp 10
juta tidak terbaca sebagai hasil; deret tanpa arus dana **tidak** dikoreksi) ·
`bukti-15-dasbor-dengan-tindakan.txt` (**"TINDAKAN MENUNGGU (1): [stop_tertembus] ASII"**) ·
`bukti-keadaan.txt` (isi `posisi` 4 revisi, `transaksi` 3 baris, `ekuitas_harian` 3 revisi, dan
penjaga append-only yang benar-benar menolak `UPDATE` di kedua tabel). Basis datanya salinan;
**jangan** dipakai sebagai sumber data pasar tanpa sadar isinya salinan) ·
`.uji-data/uji-aksi-korporasi/` (bukti Tahap 2 langkah 4, aksi korporasi pada posisi: **salinan**
`.uji-data/uji-posisi` — 999.421 bar, 12 snapshot, migrasi **013 terpasang**. Enam belas
`bukti-*.txt` bernomor: `bukti-2-beli-mlpt-pra-split.txt` (beli 1.000 lbr @18.750 pada 1 Jul 2026,
V1+V6 tercatat, **biaya tidak dapat dihitung** karena tarif broker belum berlaku pada tanggal itu —
bukan nol) · `bukti-3-stop-pra-split.txt` (stop Rp 17.000, basis 2026-07-15) ·
`bukti-4-posisi-setelah-split.txt` (**AC-18**: 25.000 lbr, rata-rata Rp 750, stop Rp 680, risiko
Rp 5.875.000) · `bukti-6-posisi-dengan-dividen.txt` (BBCA: **Rp 45.000** dari 2 pembayaran, bruto) ·
`bukti-8-hak-right-issue.txt` + `bukti-13-hak-sesudah-keputusan.txt` (hak dari rasio, tenggat kosong
disebut, baris ASII tidak muncul karena tanggalnya sebelum posisinya dibuka) ·
`bukti-10`/`bukti-11`/`bukti-12` (keputusan: `abaikan` → direvisi `jual_hmetd` hasil Rp 119.500 tanpa
mengurangi lembar; `tebus` **ditolak** tanpa transaksi lalu diterima dengan `--id-transaksi 6`) ·
`bukti-14-dasbor-sesudah-keputusan.txt` (TINDAKAN MENUNGGU tinggal 2, yang tenggatnya lewat pindah
ke CATATAN) · `bukti-15-saring-tetap-jalan.txt` (**likuid 225**, bukan 227 — sebabnya P27: baris
right issue uji membuat emiten itu berstatus "tidak dihitung" di `penyesuaian.py`, aturan lama yang
**bukan** akibat langkah ini) · `bukti-16-dasbor-dengan-pembanding-ekuitas.txt` (K30:
`posisi + kas Rp 169.428.000`, selisih Rp −81.572.000 dari ekuitas tercatat, beserta sebabnya) ·
`bukti-17-hak-dengan-catatan-lot.txt` (K31: `hak 6.250 lembar BUKAN kelipatan lot 100 … penebusan
hanya bisa dicatat 6.200 lembar`). `konfigurasi/aksi-korporasi.csv` di folder ini memuat **tiga baris
uji** bertanda "BARIS UJI - bukan pengumuman resmi" — **jangan** dipakai sebagai data pasar) ·
`.uji-data/uji-stop-right-jendela/` (**bukti aksi #19d, sesi 18**: `bukti/` memuat
`bukti-stop-right-19d.txt` (perbandingan baris jendela vs baris perintah atas **dua salinan**
`.uji-data/uji-aksi-korporasi`, + dialog konfirmasi apa adanya + hak sebagai petunjuk + `tebus` yang
ditolak), `bukti-mutasi-19d.txt` (5 mutasi terarah, semuanya membuat uji sasaran gagal, berkas
dipulihkan byte-identik), dan **enam tangkapan layar `offscreen`** `tangkapan-1..6-*.png` (formulir
ubah stop 11.1, dialog konfirmasinya, keadaan sesudah tersimpan, tabel hak + formulir keputusan
11.3, dialog konfirmasi keputusan, keadaan sesudah tersimpan). Salinan kerjanya di `perintah/` dan
`jendela/` (dua basis data yang dibandingkan; keduanya **salinan**, bukan data pasar). Pembuatnya
`.uji-data/riset-idx/stop-right-jendela/` (`bukti-stop-right-19d.py`, `tangkap-layar-19d.py`,
`uji-mutasi-19d.py`) — ketiganya menyentuh **salinan** saja)

Kalau folder itu terhapus, seluruhnya bisa dibuat ulang (butuh jaringan, ±15 menit):
```powershell
.\.venv\Scripts\python -m mejasaham --ambil-emiten --folder-data .uji-data
# lalu keluarkan 57 kode mati dari .uji-data\konfigurasi\emiten.csv:
#   daftarnya di .uji-data\refresh-973.log (baris berbunyi "GAGAL ... tidak mengembalikan satu bar pun")
#   atau jalankan .tmp\susun-semesta-uji.py yang dipakai sesi 9 Okt 2026 (skrip sementara, tidak ikut git)
.\.venv\Scripts\python -m mejasaham --refresh --folder-data .uji-data
# kalender libur bursa (2026 & 2027; tahun lebih lama tidak tersedia lagi di halaman KSEI)
.\.venv\Scripts\python -m mejasaham --ambil-kalender --folder-data .uji-data
#   berkasnya sudah ada (template) -> tambahkan --timpa-kalender
```

Catatan: `.uji-data` hanya ada di mesin ini. Sesi berikutnya di mesin lain harus membuatnya sendiri.

---

## 8. Tiga commit terakhir sebelum berkas ini ditulis (untuk orientasi cepat)

| Commit | Isi |
|---|---|
| `6888b1b` | Catat: keadaan git sesudah commit — pekerjaan sesi 20–32 tersimpan di `4bbaf20` dan `eb30214` |
| `c862d16` | Aksi #23: konteks pasar disimpan `--saring`, dibaca dasbor bila kuncinya sama (K61/T80) |
| `6888b1b` | Catat: keadaan git sesudah commit — pekerjaan sesi 20–32 tersimpan di `4bbaf20` dan `eb30214` |
| `eb30214` | Catat sesi 21–32: K74–K87, T76–T79, kandidat rasio bank, jenis terisi |

Tabel ini **tidak** memuat commit yang mengubah berkas ini sendiri: setiap kali `docs/lanjutan.md`
disunting, commit-nya menjadi yang terbaru — jadi `git log --oneline -4` yang menjawabnya, bukan
tabel di atas. **Status 19 Okt 2026 (sesi 34): working tree bersih sesudah commit** —
**`c862d16`** = kode + uji aksi #23, lalu **commit dokumen ini** = catatan sesi 33–34 (K79/K88,
K61/T80); `HEAD` sebelum commit itu adalah **`6888b1b`**. **Basis data kerja tidak berubah**
(pengukuran memakai salinan `.uji-data/uji-k61/`). Data sesi 31–33 (snapshot 12/13, `rasio_bank`,
`emiten.csv`) tetap **gitignored**.

---

## 9. Pertanyaan pertama yang pantas diajukan ke pengguna

**Keadaan sekarang (22 Okt 2026, sesi 36):** tidak ada usulan yang menunggu jawaban atau aksi
agen yang terkunci. K85–K88 sudah dikunci, 44 bank tetap ditunda (K88), #23/U26 selesai
(T80), dan ikon Tahap 5 selesai dibuat serta dipasang (T82; suite 910 lulus). Yang tersisa
untuk Tahap 5 adalah uji klik-ganda pada mesin yang benar-benar tidak memiliki Python. Pekerjaan
manusia lain adalah mengirim laporan PySide6 (K66/K84); verifikasi rasio-bank.csv selesai
(K83). --pulihkan tetap di luar cakupan jendela (K59 e/K64).

Pertanyaan cakupan yang dapat diajukan kemudian: lanjutkan pengumpulan dokumen 44 bank (K88)
atau pertahankan penundaan. Riwayat pertanyaan di bawah ini tetap sebagai jejak:

**Yang menunggu jawaban (17 Okt 2026, sesi 13): P37–P39** — pembagian pekerjaan tiga butir yang
selama ini menunggu manusia (lihat tabel di bawah dan `docs/keputusan.md` 3.9). **Tidak satu pun
memblokir pekerjaan**: #19c dan #19d tetap berjalan tanpa jawaban itu. Sebelumnya, tiga pertanyaan
yang dicatat sesi 11b (**P34–P36**) sudah **dijawab "sesuai rekomendasi"** dan dikunci di
`docs/keputusan.md` bagian 1 — **K62** (urutan tindakan tulis lanjutan), **K63** (pilihan "Pakai
ukuran patuh" di layar 11.4), **K64** (jendela = jalur harian; pilihan rencana & posisi dari daftar
wajib masuk) + **K65** (tafsirnya: dari daftar **saja**, tanpa kotak isian bebas) — dengan bentuk
teknisnya **T71** dan pelaksanaannya **T72** (K62/K63/K64 sudah dijalankan untuk bagian #19b; #19c
dan #19d menyusul menurut urutan yang sama tanpa pertanyaan baru). Isi pertanyaannya dibiarkan di
bagian 3.8 sebagai riwayat:

| # | Pertanyaan (riwayat) | Jawabannya | Yang dipengaruhi |
|---|---|---|---|
| **P34** → **K62** | Sesudah #19b/#19c, tindakan tulis mana yang masuk jendela lebih dulu? | Ikuti K59 c apa adanya (impor → cadangan), lalu **#19d = `ubah-stop` + keputusan right issue**; `ubah-stop` **tidak** diselipkan sebelum impor | Aksi **#19d** |
| **P35** → **K63** | Cabang PRD 9.7 **"pakai ukuran yang patuh"** belum ada di jendela | Pilihan **Pakai ukuran patuh** ditambahkan di layar 11.4, **dihitung sebelum konfirmasi**, dikerjakan bersama #19b | Layar 11.4; kelengkapan pilihan PRD 9.7 |
| **P36** → **K64** (+ **K65**) | Seberapa lengkap jendela dibanding baris perintah? | Jendela = **jalur harian**; **pilihan rencana & posisi dari daftar** wajib masuk; sisanya (`id posisi` eksplisit, pajak/biaya pengguna, broker, ekspor, `--pulihkan`) tetap di baris perintah. **K65** (sesi 13): jendela memilih **dari daftar saja** — tidak ada kotak isian bebas untuk `id_rencana`/`id_posisi`/revisi rencana | Cakupan formulir jendela (#19b/#19d) |

**P37–P39 SUDAH DIJAWAB (17 Okt 2026, sesi 14) → K66–K68** — bukan pertanyaan produk, melainkan
**pembagian pekerjaan** untuk tiga butir yang selama ini menunggu manusia. Isi jawabannya beserta
**hasil yang sudah dikerjakan sesi ini** (rinciannya di `docs/keputusan.md` 3.9 dan bagian 1):

| # | Pertanyaan | Jawabannya | Hasilnya sekarang |
|---|---|---|---|
| **P37** → **K66** | Siapa yang mengirim laporan cacat PySide6 ke Qt? | **Tetap Anda**; sesi agen menyiapkan berkas siap-tempel | **Selesai:** `docs/laporan-pyside6-siap-kirim.md` — teks siap tempel + langkah kirim (pelacak PYSIDE, lampiran berkas wajib) + daftar lampiran |
| **P38** → **K67** | Uji Python 3.13 (K60 b) dialihkan ke sesi agen? | **Ya**, dengan syarat keputusan dependensi lebih dulu | **Sudah dijalankan:** lingkungannya `.tmp/py313` (disetujui pengguna); hasil **"belum dapat disimpulkan"** — 0 kematian di 24 jalan tanpa penangkal (3.13 & 3.14). Rincian `docs/riset-pyside6-gc-2026-10.md` bagian 8.5 |
| **P39** → **K68** | `rasio-bank.csv` boleh dikumpulkan sesi agen? | **Boleh sampai kandidat + kutipan resmi**; basis data menunggu verifikasi Anda | **Lingkupnya sudah diukur** (49 bank · **0 tertahan hanya oleh rasio**) — bukti `.uji-data/uji-lingkup-p39/bukti-lingkup-p39.txt` |

Sesi 10b (**P31–P33**) juga sudah **dijawab "sesuai rekomendasi"** dan dikunci di `docs/keputusan.md`
bagian 1: **K59** + **T69** (kunci tulis jendela: menunggu `busy_timeout` lalu berhenti dengan pesan
"belum menulis apa pun"; cakupan bertahap; konfirmasi semua; F12 cadangan+daftar dulu), **K60** (cacat
PySide6: laporan upstream dulu, lalu uji Python 3.13), **K61** (konteks pasar tetap dihitung ulang;
**U26** tetap terbuka dengan aturan kebasian yang sudah disepakati). Rinciannya di bagian 3.7
(pertanyaan beserta jawabannya, dibiarkan sebagai riwayat) dan bagian 2 (**U26**). **Yang tersisa
seluruhnya pekerjaan**, urutannya di bagian 4:

1. ~~**Aksi #20** — dasbor menampilkan IHSG + rezim + breadth (K58, T66).~~ **SELESAI 17 Okt 2026.**
2. ~~**Aksi #21** — kerangka `rasio-bank.csv` (K57, T67).~~ **SELESAI 17 Okt 2026.**
3. ~~**Aksi #19 tahap 1** — tiga pencatat transaksi dari jendela (K55 + K59 + T69 → T70).~~
   **SELESAI 17 Okt 2026 (sesi 11).**
3b. ~~**Aksi #19b — impor dari jendela + pilihan "Pakai ukuran patuh" (K63) + pilihan rencana/posisi
   dari daftar (K64)**~~ **SELESAI 17 Okt 2026 (sesi 12) → T72.**
3c. ~~**Aksi #19c — cadangan + daftar cadangan (F12) dari menu Berkas**~~ **SELESAI 17 Okt 2026
   (sesi 16) → T73** (konfirmasi menyebut folder tujuan, daftar sama dengan `--daftar-cadangan`,
   `muat_ulang=False` untuk cadangan). `--pulihkan` **tidak** termasuk — ia menimpa basis data
   (K59 e); usulan **U30** (folder tujuan dipilih per-cadangan?) **sudah dikunci sesi 17 sebagai K70** — folder tujuan tetap dari konfigurasi.
3d. ~~**Aksi #19d — `ubah-stop` + keputusan right issue dari jendela** (K62)~~ **SELESAI 17 Okt 2026
   (sesi 18) → T74**: formulir "Ubah stop" di 11.1 (posisi dari daftar, `tgl_stop` = tanggal yang
   dinyatakan pengguna) dan tabel hak + formulir keputusan right issue di 11.3 (`tebus` hanya
   **menunjuk** transaksi yang sudah tercatat, T51) — **dengan ini seluruh cakupan tindakan tulis
   K59 c terpenuhi**; yang tetap di baris perintah hanya `--pulihkan` (K59 e/K64).
3e. ~~**Dua temuan sesi 18**~~ **DIKUNCI sesi 19 → K71/K72, dan DIKERJAKAN sesi 20 sebagai #24/#25
   → T75** (keduanya **selesai 19 Okt 2026**; `pytest` → 882 lulus).
3e-1. ~~**Aksi #24 (K71)**~~ **SELESAI 19 Okt 2026** — `posisi.catat_keputusan_right_issue` **menolak
   `--lembar`/`--harga`/`--biaya`** untuk semua keputusan selain `jual_hmetd`, termasuk `tebus`, lewat
   satu pemeriksaan `_tolak_isian_yang_tidak_dipakai`; jalur baris perintah kini **keluar 1** dengan
   pesan yang menyebut transaksi (T51), bukan 0 tanpa pesan.
3e-2. ~~**Aksi #25 (K72)**~~ **SELESAI 19 Okt 2026** — `catatan` keputusan right issue **berhenti
   menggelembung**: catatan turunan yang kalimatnya sudah ada (dibandingkan per baris) tidak
   ditambahkan lagi; catatan pengguna dan `pesan_revisi` tetap disambung. Riwayat lengkap tetap di
   baris revisinya masing-masing (append-only).
4. ~~**Aksi #22** (cacat PySide6)~~ **SELESAI 19 Okt 2026 (sesi 21) menurut K60/K66/K67/K69**:
   reproduksi ulang **berhasil** — seluruh suite 12× tanpa penangkal di 3.14.7 → **2 mati**
   (`Fatal Python error: Aborted`, di `tests/test_ui_jendela.py:195 _tunggu`) — lalu A/B yang sama di
   3.13.14 → **0 mati** (p ≈ 0,48; rincian `docs/riset-pyside6-gc-2026-10.md` **bagian 10**).
   **Keputusan pin versi Python = U31** (rekomendasi: **jangan sekarang**); **cabang uji versi PySide6
   lain tidak dipicu**. **Yang tinggal manusia:** berkas laporan siap kirimnya
   (`docs/laporan-pyside6-siap-kirim.md`, **diperbarui** dengan kontrol yang gagal) **Anda** yang
   mengirim (K66). **T68 tetap dipakai.**
5. ~~**Aksi #23** (simpan konteks pasar, U26)~~ **SELESAI 19 Okt 2026 (sesi 34) → T80** —
   `--saring` menulis `konteks_pasar` (migrasi 015), dasbor membacanya hanya bila snapshot + preset +
   label sumber harga + versi hitung masih sama; `--dasbor` **18,95 → 0,74 dtk**; 19 uji baru,
   suite **906 lulus**; bukti `.uji-data/uji-k61/bukti/`.
6. Sisa lain: kalender **2021–2024** (berkasnya 404 di KSEI; hanya bisa lewat impor) dan `.exe`
   (Tahap 5 — **sudah dibangun sesi 35, T81**; tersisa ikon dan uji klik-ganda di mesin tanpa
   Python).
7. **~~Aksi #21b~~ — `rasio-bank.csv` (K68): SELESAI 19 Okt 2026 (sesi 31, aksi #29/K83)** — pilot
   19 Okt 2026 (sesi 25) sampai batas kandidat + kutipan (**2 bank terbaca, 3 tidak**), lalu
   **verifikasi ulang 14/14 sel cocok** dan **2 baris diimpor (snapshot 12)**. **U33 sudah dikerjakan
   sesi 27 (#27/K78)** dan NPF/NI sudah diputuskan (**K77**: tidak dipetakan). **Setiap baris wajib
   mengisi `sumber`** — sel kosong **ditolak** per baris (**K81**). **`--saring` belum berubah**
   karena `jenis` 973 emiten kosong — **lalu sesi 32 mengisi `jenis`** (49 bank_keuangan), jadi
   kriteria bank **kini dipakai**: BBCA keempat rasio lolos, 47 bank lain belum berasio. Kerangkanya sudah
   dibuat aksi #21 (49 kode bank). **Baca dulu temuan
   lingkupnya** (`.uji-data/uji-lingkup-p39/`): pada snapshot #8 **0 dari 49 bank tertahan *hanya* oleh
   rasio** — jadi mengisi berkas itu saja **tidak** membuat bank masuk peringkat (K57 tetap berlaku
   untuk metrik lain yang juga lubang).
8. **~~Aksi #28~~ — `potret._fundamental` membawa `sumber` per baris** (**K82**, dikunci sesi 28;
   **SELESAI 19 Okt 2026, sesi 29 → T78**): satu baris `sumber=baris["sumber"]` + **dua uji** yang
   **terbukti gagal pada `HEAD`** (di HEAD nilainya `None`), dua mutasi terarah tertangkap, suite
   **887 lulus**. **Tidak ada pekerjaan berikutnya yang menunggu** — **44 bank ditunda (K87)** dan
   **U34 ditutup (K86)**; pengiriman laporan PySide6 tetap manusia (K84). **Sesi 32 mengisi `jenis`**
   (prasyarat K87): 49 bank_keuangan, kriteria bank diterapkan, peringkat tidak berubah; **44 dokumen
   tetap ditunda** dan **K79 sudah dihitung sesi 33** (8 manual · 2 tidak terukur · 34 otomatis).
   **44 bank tidak dimulai tanpa permintaan**; **#23 SELESAI sesi 34 (T80)**; `--pulihkan` tetap
   bukan pekerjaan tertunda (K59 e).

> **Koreksi daftar sisa pekerjaan (17 Okt 2026).** Dua daftar "yang tinggal pekerjaan" di bagian bawah
> berkas ini (keadaan sebelum F7 dan sesudahnya) masih menyebut **`harga_indeks` untuk rezim pasar &
> breadth** sebagai sesuatu yang belum ada. Itu **salah**, dan koreksinya datang dari pemeriksaan
> 17 Okt 2026: `harga_indeks` **sudah terisi** — IHSG **1.199 bar** dan LQ45 **1.199 bar**, 2021-10-11
> → 2026-10-09 — sebab `--refresh` memang mengambil `^JKSE` dan `^JKLQ45` (`mejasaham/pengambil.py`
> baris 60–62), dan `--saring` sudah menghitung `breadth 39,1% · rezim RISK-OFF` darinya. Yang belum
> ada bukan **datanya**, melainkan **dasbor yang memakainya** — dan itu menjadi **aksi #20/K58**.
> Daftar-daftar lama itu dibiarkan apa adanya sebagai riwayat; yang berlaku adalah koreksi ini.

**Keadaan sesi sebelumnya (16 Okt 2026, sesi 6):** tidak ada pertanyaan yang menunggu. Dua pertanyaan
yang muncul dari tinjauan visual K46 — **U24** dan **U25** — sudah dijawab pengguna dan dikunci
sebagai **K53/K54** di `docs/keputusan.md` bagian 1, lalu **dijalankan** (aksi #17, sesi 7); aksi #18
menutup cacat `;` yang ditemukan di sesi 7 (sesi 8).

Riwayat keputusan yang kini seluruhnya terkunci: **K45** (P29/P30), **K42** (U22/U23 dan U2–U17/U19),
**K46–K49** (perlakuan impor empat temuan rekonsiliasi), **K50** (satuan baris = kode × episode),
**K51** (cara melepas penanda), **K52** (penanda dilepas, pelaksanaannya ditunda), **K53** (20 Feb 2024
bukan tanggal mulai + episode MTFN yang hilang dibentuk), **K54** (bentuk baris K41), dan
**K55–K58** (17 Okt 2026: jendela belum menulis · kalkulator tetap menuntut tesis · rasio bank diisi
manusia + kerangkanya · dasbor menampilkan rezim/breadth) — K53/K54 **dikunci 16 Okt 2026 (sesi 6) dan
pelaksanaannya menjadi aksi #17**. Ringkasnya:

1. **K46** — pengumuman 20 Feb 2024 (`Peng-S-00006/BEI.PLP/02-2024`): ke-34 baris **ditahan** dari berkas
   impor sampai ada tinjauan visual halaman PDF-nya. Temuan tambahan sesi 4: **ke-34 kode itu sudah
   berstatus `Suspensi di …` sebelum 20 Feb 2024**, jadi kodenya tetap dapat baris (dengan penanda
   `DITAHAN_K46_…`); hanya baris 20 Feb 2024 yang tertahan.
2. **K47** — empat kode `Aktif` dua kali dalam 30 hari (`ASMI`, `COAL`, `LCKM`, `MTFN`) **disiapkan apa
   adanya** dengan penanda di `keterangan`; keempatnya memang membawa penanda `AKTIF_DUA_KALI_DALAM_30_HARI`.
3. **K48** — baris tabel dua kode (`MYRX`+`MYRXP`, `CNTX`+`CNTB`): **penanda cukup**, satu baris impor
   per kode, tanpa kolom baru.
4. **K49** — 80 kode tanpa riwayat API dan 14 kode di luar daftar emiten **dimuat apa adanya** dengan
   penanda; **tidak** menyimpulkan delisting dari selisih daftar (K44c).
5. **K50** — T60 dibaca sebagai **satu baris per (kode × episode)**: pengumuman `dipertahankan` tidak
   menyatakan tanggal mulai, jadi memakai tanggal pengumumannya akan memasang tanggal mulai palsu untuk
   936 baris. Hasilnya 171 baris, bukan 1.090.
6. **K51** — cara melepas penanda: **bangun berkas dari basis data** (2.447 revisi terkini), lepas
   penandanya, impor ulang sebagai revisi baru. **Dijalankan 16 Okt 2026 (sesi 5)**: 2.447 baris baru
   tertulis dan `--saring` berubah menjadi **"Kandidat teratas"** (angka "2.154" pada catatan lama
   adalah jumlah baris berpenanda, bukan jumlah baris yang ditulis — lihat koreksi di bagian 6).
7. **K52** — **penanda itu dilepas**, dan pelaksanaannya **sudah dilakukan 16 Okt 2026 (sesi 5)** dengan
   lima langkah berurutan di bagian 4 aksi #15. Risikonya sudah ditutup: cadangan dibuat lebih dulu,
   `tanggal_selesai` dan provenance tidak berubah (hanya penandanya yang dilepas), dan yang tetap belum
   beres — tinjauan visual 34 kode dari baris 20 Feb 2024 serta 65 episode bertanggal mulai proxy —
   tetap **disebut di `keterangan` tiap barisnya**, bukan disembunyikan oleh pelepasan penanda.
8. **K53 & K54 (16 Okt 2026, sesi 6)** — **tinjauan visual yang diminta K46 sudah dijalankan, dan
   hasilnya mengubah dua hal yang tadinya "belum beres" di atas menjadi keputusan yang siap
   dijalankan**: K53 melepas penanda `DITAHAN_K46_…` (20 Feb 2024 **bukan** tanggal mulai; pengumuman
   itu masuk `keterangan` episode yang berjalan) **dan** membentuk episode MTFN 2023–2024 yang hilang
   (≤2023-10-30 → **selesai 2024-08-29** dari UPT-nya); K54 menutup janji **K41** yang ternyata belum
   pernah dijalankan atas data (`ELTY` 2023-07-03 → 2023-10-19 · `ARTI` 2021-11-30 → 2023-11-23,
   dengan penanda "di luar cakupan API"). **Pelaksanaannya ditunda ke sesi berikutnya (aksi #17)**,
   sesuai permintaan pengguna pada sesi pencatatan itu. Yang **tetap** berjalan apa adanya: 3 penanda
   K47 dan 65 episode bertanggal mulai proxy — keduanya memang belum dinyatakan sumbernya.

**Aksi berikutnya (sesi berikutnya)** — **(a) sudah dikerjakan 16 Okt 2026 (sesi 6)**: tinjauan visual
baris pengumuman 20 Feb 2024 **selesai** (aksi #16), dan **dua temuannya sudah diputuskan pada sesi
yang sama → K53/K54** — jadi sesi berikutnya **langsung menjalankan #17**, tanpa menunggu jawaban
apa pun lagi.
Yang tetap pekerjaan (bukan keputusan): **(b) panel jendela PySide6** (aksi #10 di bagian 4) — sisa
terbesar Tahap 2/3; (c) sisa lain yang sudah terdaftar di bagian 4 (kalender 2021–2024,
`harga_indeks` untuk rezim pasar & breadth).

**Riwayat (10 Okt 2026, Tahap 3 langkah 1 — F7).** F7 dikerjakan, dan yang **baru** muncul darinya
dua pertanyaan yang saat itu dipakai dengan pemetaan terbuka, bukan ditahan:

1. **P29 — pelanggaran yang bukan transaksi dihitung ke transaksi yang mana?** PRD 9.8 berkata
   "transaksi tanpa pelanggaran ÷ seluruh transaksi", sedangkan PRD 13.1 berkata "≥ 90% **keputusan**
   tanpa pelanggaran" — dan V5 (stop digeser) serta V7 (posisi dipertahankan setelah pembatal
   terpicu) bukan transaksi. Yang dipakai sekarang: menempel pada **transaksi terakhir posisi itu
   pada/sebelum tanggal kejadian**; yang tidak punya transaksi (mis. rencana melanggar batas yang
   belum dieksekusi) **tidak** mengubah rasio tetapi tetap dicetak. Alternatifnya: menghitungnya
   sebagai keputusan tersendiri, sehingga penyebutnya "keputusan", bukan "transaksi".
2. **P30 — tombol "[Tandai selesai]" (PRD 11.5) tidak punya kolomnya di PRD 12.** Dipetakan
   terbuka: `tanggal_tinjau` = tanggal tinjau **berikutnya**, `selesai_pada` = tanggal entri jurnal
   ditandai selesai (`--tandai-selesai`). Pertanyaannya: apakah itu artinya, atau "tandai selesai"
   berarti sesuatu yang lain (mis. menutup keputusannya)?

Dua usulan yang **sudah dipakai** dan tercatat supaya bisa dikoreksi: **U22** (ambang expectancy
memakai batas bawah rentang PRD 13.2, yaitu **30 putaran tertutup**, dan angkanya tetap ditampilkan
sebagai angka sementara) dan **U23** (expectancy dihitung **per putaran/posisi tertutup**, sedangkan
kepatuhan tetap per transaksi — keduanya dicetak dengan namanya masing-masing). **Keduanya kini
berstatus keputusan (K42), bukan lagi usulan.**

**Yang tinggal pekerjaan, bukan pertanyaan:** (a) **ekspor (F9)** dan **cadangan/pemulihan (F12)** —
sisa Tahap 3 yang sama, dan PRD 16 menutup tahap ini baru setelah keduanya jalan (AC-14);
(b) daftar **suspensi** dan **UMA** dari halaman IDX yang sudah terbukti bisa diambil; (c) panel
jendela PySide6 — seluruh F7 dan F11 sudah jalan di mode kepala; (d) kalender 2021–2024; (e)
`harga_indeks` untuk rezim pasar & breadth.

**Keadaan sebelum F7 (10 Okt 2026, Tahap 2 langkah 4 + tindak lanjutnya).**
**Keenam pertanyaan yang menunggu sudah dijawab pengguna 10 Okt 2026 ("sesuai rekomendasi") →
K29–K34**, dan dua di antaranya dikerjakan sekalian karena keputusannya baru benar-benar jalan
setelah itu:

0. **K29** (P16) daftar "tindakan menunggu" disahkan apa adanya — empat butir usulan + tiga
   tambahan. **K30** (P25) ekuitas **tetap dicatat pengguna**; yang ditambahkan sekarang: dasbor
   menampilkan `nilai posisi + kas` **beserta selisihnya** terhadap ekuitas tercatat, jadi angka
   yang menjadi penyebut seluruh risiko bisa diperiksa. **K31** (P26) aturan lot tetap berlaku
   (PRD 10); yang berubah: hak yang bukan kelipatan lot **disebut lebih awal**, bukan baru saat
   `--catat-transaksi` menolaknya. **K32** (P27) TERP tidak dibangun — emiten ber-right-issue
   tetap keluar dari metrik harga di `--saring`. **K33** (P28) dividen tetap dihitung, tanpa jalur
   koreksi manual. **K34** (P15) kepatuhan hanya atas transaksi (V1–V7) — **bahan yang sudah siap
   untuk F7**.

**Keadaan sebelum tindak lanjut (10 Okt 2026, langkah 4):** yang menunggu waktu itu hanya
**pengesahan dua hal**, dan keduanya tidak menghambat kerja berikutnya:

1. **P16 — isi dasbor "tindakan menunggu"** sudah dikerjakan sesuai usulan (stop tertembus /
   pembatal terpicu, tesis kedaluwarsa, tenggat right issue) **plus tambahan**: posisi
   **tanpa stop**, posisi yang stop-nya tidak dapat dinilai, dan right issue yang tenggatnya belum
   dinyatakan. Kalau tambahan itu tidak dikehendaki, yang berubah hanya satu daftar di
   `dasbor.tindakan_menunggu()`.
2. **P25 — ekuitas harian dicatat pengguna atau diturunkan dari transaksi + kas?** AC-13 berbunyi
   "dihitung dari transaksi, kas, dan setoran/penarikan", sedangkan yang ada sekarang adalah
   pencatatan pengguna + `--arus-dana` untuk koreksi drawdown (lulus untuk drawdown, belum untuk
   penurunan ekuitasnya). Usulan: tetap dicatat pengguna di v0.1, dan dasbor menampilkan
   `nilai posisi + kas` sebagai pembanding. **→ Sudah dijawab 10 Okt 2026 → K30**, dan
   pembandingnya sudah dikerjakan.

**Yang tinggal pekerjaan, bukan pertanyaan:** (a) **jurnal & kepatuhan F7** (V3/V4/V7 menunggu di
sana — dan itu langkah berikutnya yang paling menentukan, karena ia yang mengubah pelanggaran
menjadi rekap kepatuhan); (b) daftar **suspensi** dan **UMA** dari halaman IDX yang sudah terbukti
bisa diambil; (c) panel jendela PySide6 — seluruh F11 sudah jalan di mode kepala; (d) kalender
2021–2024 (berkasnya 404 di KSEI, hanya bisa lewat impor); (e) `harga_indeks` untuk rezim pasar &
breadth. Aksi korporasi pada posisi **sudah selesai** (Tahap 2 langkah 4, K28).

Bagian bertanda kutip di bawah adalah pertanyaan **lama** yang sudah terjawab; ia disimpan supaya
riwayatnya tidak hilang, bukan karena masih menunggu.

**Keadaan sebelum Tahap 2 langkah 2 (10 Okt 2026, langkah 13):** (a) tarif Stockbit **sudah dimuat**
dan `--muat-konfigurasi` menyebut `biaya_broker` + `slippage` sebagai **dipakai** — tanpa satu pun
angka yang tidak dinyatakan sumbernya (K22/K23); (b) `jenis` emiten **sudah diturunkan** untuk 911
dari 916 emiten, dengan **49 bank** yang kini dinilai memakai set kriteria bank (K21); (c) penanda
*all-in* K23 kini benar-benar **dipakai** kalkulator biaya (Tahap 2 langkah 2), bukan hanya
tersimpan.

> "**Dua hal menunggu keputusan Anda, dan keduanya bentuk penyimpanan — bukan data yang belum
> dicari.** (1) **U20**: halaman tarif Stockbit menyatakan tarifnya tegas (0,15%/0,25%, all-in),
> tetapi **tidak** menyatakan tarif minimum maupun tanggal berlakunya. Bentuk entri yang berlaku
> menuntut keduanya, jadi memuatnya hari ini memaksa satu angka karangan. Bolehkah `minimum`
> **tidak ada** (= 'tidak dinyatakan sumber') dan `berlaku_sejak` memakai tanggal pengamatan
> **berpenanda asal** — pola yang sudah Anda setujui untuk `tgl_publikasi` di K19? (2) **U21**:
> 0,15%/0,25% itu **sudah termasuk** levy, PPN, dan PPh final jual. Tanpa penanda *all-in* yang
> tersimpan di entri, kalkulator biaya Tahap 2 akan menambahkan B8 (0,1%) di atasnya — salah dua
> kali, dan tidak terlihat di keluaran mana pun.
>
> Yang **tidak** menunggu jawaban: **`jenis` emiten diturunkan dari data (K21, aksi 1b)** — sudah
> Anda izinkan, tinggal dikerjakan; kalender **2021–2024** (404 di KSEI, tidak menghambat); dan
> seluruh **Tahap 2** yang tidak menyentuh lot/tick/biaya.
>
> Untuk **P22** (notasi khusus & rasio bank): jalur peramban sudah diuji dan batasnya terukur —
> peramban sungguhan **bisa** menembus `www.idx.co.id` (HTTP 200), tetapi `requests` **tidak bisa**
> memakai cookienya, dan burst ke IDX diblok lama. Jadi pertanyaannya berubah bentuk: kalau
> `notasi-khusus.csv` hanya bisa datang lewat peramban, **apakah aplikasi boleh menambah
> ketergantungan peramban** — atau lebih baik berkas itu tetap diisi dari sumber sekunder/manusia
> dengan labelnya dinyatakan apa adanya? Rincian: `docs/keputusan.md` bagian 3.6."

**Catatan yang perlu Anda tahu sebelum menilai langkah 13 — dua hal yang sengaja TIDAK dikerjakan,
dan keduanya akan terlihat seperti kelalaian kalau tidak disebut:**

1. **5 dari 916 emiten tetap tanpa `jenis`** (BOSS, DEAL, ETWA, KAYU, LAPD). Itu bukan kegagalan
   yang ditelan: sumber datanya memang tidak menyatakan `sector` maupun `industry` untuk kode itu,
   dan K21 menetapkan keadaan itu sebagai **"tidak dinyatakan"** — kolomnya dibiarkan kosong,
   **bukan** diisi `umum`. Konsekuensinya tetap terlihat di `--saring` sebagai peringatan yang
   menyebut angkanya (5), jadi ia tidak hilang dari pandangan.
2. **`siklikal_komoditas` tidak dihasilkan satu pun.** Sektor komoditas (`Basic Materials`,
   `Energy`) tetap menjadi `umum`, sekalipun secara intuisi "jelas siklikal" — sebab itu penilaian
   analis, dan K21 melarangnya diturunkan. Nilai itu hanya bisa datang dari isian manusia di
   `emiten.csv`, dan `--ambil-jenis` **tidak menimpanya**. Uji
   `tests/test_jenis_emiten.py::test_siklikal_komoditas_tidak_pernah_diturunkan` menjaga batas ini
   secara eksplisit.

**Catatan yang perlu Anda tahu sebelum menilai pengambil fundamental:** seluruh `idx.co.id` masih
membalas 403 dari mesin ini (12 jalur diuji 9 Okt 2026, 0 berhasil; `web.ksei.co.id` membalas 200,
jadi yang diblokir memang IDX). Karena itu B1/B2/B4/B8 bersandar pada angka yang konsisten lintas
sumber sekunder **beserta nomor dokumennya**. Sejak langkah 13 berkas parameter **aktif**
(`.uji-data/konfigurasi/parameter-bursa.toml`) memang dimuat ke basis data uji — tetapi yang
dimuat adalah entri yang **sumbernya sudah dibaca mesin ini** (B6/B7 Stockbit, B9 keputusan produk)
plus entri B1–B5/B8 yang sudah terpasang sejak sebelumnya; entri yang masih bertumpu pemberitaan
sekunder tetap menyebutkan itu apa adanya di kolom `sumber`-nya.


**Catatan yang perlu Anda tahu sebelum menilai langkah 10:** penelusuran sumber ini berlaku untuk
**satu jaringan** (mesin ini, 9 Okt 2026) — sama seperti temuan `idx.co.id` sebelumnya. Jadi
"`bi.go.id` memutus koneksi" adalah temuan tentang jaringan ini, bukan pernyataan bahwa BI menutup
akses otomatis; dari jaringan lain (mis. IP residensial Indonesia) hasilnya bisa berbeda, dan itu
layak dicoba sebelum menyimpulkan. Yang **tidak** berubah karenanya: seluruh `idx.co.id` membalas
403, sudah diuji berkali-kali termasuk dengan meniru TLS browser.

**Yang berubah dari catatan langkah 8:** dulu tertulis "kalender 2025 tidak bisa diambil dari
KSEI". Itu benar untuk berkas yang ditautkan halaman **saat itu**. Sekarang halaman yang sama
menautkan versi *Perubahan Kedua* (ditolak T31) sekaligus menyimpan versi sebelumnya yang **lulus**
T31 dengan 25 tanggal yang identik — dan sejak **K17** tanggal itulah yang dipakai, dengan syarat
yang bisa diperiksa (lihat `docs/keputusan.md` 3.5).

**Satu hal lagi soal langkah 9 yang perlu Anda tahu, sebab hasilnya bukan yang saya duga:** pada
data nyata, peringkat ADTV20 20 teratas ternyata **sudah sama** sebelum dan sesudah harga
pembanding diimpor (0 dari 20 baris berbeda) — kueri peringkatnya memakai `COUNT(DISTINCT tanggal)`
dan `AVG` yang mengabaikan nilai kosong, sedangkan bar pembanding di data itu diimpor tanpa nilai
transaksi. Jadi cacat P17 **tidak** terlihat lewat daftar kritis PRD 9.3 pada data tersebut; ia
muncul di jalur deret yang dipakai `--saring`. Penyaringan label di `jalankan_refresh` tetap
dipasang karena bentuk yang sama berubah menjadi salah begitu pembanding memuat nilai transaksi —
itu terbukti di uji sintetis, bukan diduga.

### Tindak lanjut IDX: berkas sampel & rekonsiliasi (11 Okt 2026)

- Berkas tinjauan tersedia: `.uji-data/riset-idx/emiten-idx-20261011.csv` (962 kode unik,
  11 sektor) dan `.uji-data/riset-idx/rekonsiliasi-kode-20261011.csv` (5 kode hanya IDX,
  16 kode hanya lokal). Sampel KAQI cocok ke profil resmi pada tanggal, papan, dan sektor.
- Nama sektor memakai label Inggris persis dari endpoint IDX. Papan dipetakan ke enum impor.
  `jenis`, `sektor_sumber`, `status_notasi`, dan `free_float_persen` kosong karena tidak ada di
  sumber; Financials tidak otomatis menjadi `bank_keuangan`.
- Tidak ada impor dan tidak ada perubahan basis data. **Tahap berhenti untuk tinjauan pengguna**
  sesuai K4. Jangan menghapus atau menyimpulkan status kode lokal dari selisih saja.
- Pemeriksaan data/dokumen saja; tes kode tidak dijalankan. Suite terakhir **765 lulus** pada
  tahap perbaikan ekspor. Bukti sumber dan rincian keputusan ada di `docs/keputusan.md` bagian 5.

### Tindak lanjut suspensi multi-kode IDX (11 Okt 2026)

- Endpoint resmi `GetSuspension` saat diperiksa mengembalikan 1.919 rekaman, termasuk 56 dengan
  `Kode = ">1 Kode"`: 29 SPT dan 27 UPT. Field `Data_Download` pada respons memberi tautan PDF
  IDX untuk tiap rekaman.
- Seluruh 56 PDF resmi diunduh (HTTP 200) ke `.uji-data/riset-idx/suspensi-pdf/`; teks dapat
  diekstrak pada semua berkas tanpa OCR. Daftar kode yang tercantum, tanggal API, jenis peristiwa,
  dan tautan langsung tersedia di `docs/riset-suspensi-multi-kode-2026-10.md`.
- Daftar kode adalah ekstraksi dokumen, bukan daftar aksi final. Sejumlah pengumuman SPT memuat
  status `Aktif` dan `Suspensi` sekaligus atau menyebut suspensi baru terpisah dari suspensi yang
  dipertahankan; UPT dapat mencantumkan tanggal efektif tersendiri. Belum ada data yang diimpor
  atau basis data yang diubah. Empat puluh UPT tanpa pasangan tunggal tetap perlu dicocokkan.
- Verifikasi sesudah pembaruan pesan CLI/saringan: `python -m pytest` — **765 lulus**. Tidak ada
  impor atau perubahan basis data. Tahap berhenti sesuai K4. Langkah berikutnya: rekonsiliasi aksi
  serta tanggal efektif setiap kode
  dengan isi keputusan PDF dan riwayat API, lalu tinjau sebelum impor. Jangan menghapus penanda
  data belum lengkap sebelum langkah itu selesai.

### Kandidat pasangan pembukaan kembali (11 Okt 2026)

- Dibuat `.uji-data/riset-idx/kandidat-pasangan-upt-20261011.csv` berisi **39 baris kode UPT**
  yang dapat diekstrak dari 26 PDF UPT dalam sampel. Pencarian menghasilkan pasangan SPT
  terdahulu untuk 16 baris; 23 baris belum memiliki kandidat dalam 56 PDF yang diunduh.
- Seluruh pasangan diberi status **KANDIDAT BELUM DIVERIFIKASI PDF**. Pencocokan otomatis hanya
  memakai tanggal API dan kode/status pada ekstraksi tabel. Itu belum memvalidasi nomor
  pengumuman, pasar, tanggal efektif, ataupun bahwa pasangan tersebut merupakan periode suspensi
  yang sama. Baris tanpa pasangan hanya berarti tidak ditemukan pada sampel ini.
- Tidak ada impor atau perubahan basis data. Tes tidak dijalankan (tahap tinjauan data/dokumen).
  Tahap berhenti untuk tinjauan sesuai K4. Langkah berikutnya: cocokkan setiap baris langsung
  terhadap teks keputusan PDF dan riwayat API, lengkapi atribut wajib, kemudian minta tinjauan
  sebelum menyiapkan impor. Daftar kode aksi SPT multi-kode secara menyeluruh masih perlu
  direkonsiliasi.

### Perbaikan laporan mutu impor konfigurasi (22 Okt 2026 — sesi 41)

- **Gejala dan sebab:** impor konfigurasi memberi `bar terkini: 0` walau basis data memiliki
  1.002.024 bar harga. `pengatur.jalankan_impor()` meneruskan label folder ke `mutu.periksa()`;
  fungsi itu menyaring view harga dengan label tersebut, yang tidak sama dengan sumber harga.
- **Perbaikan:** laporan kini memilih sumber harga utama menurut K14 dari baris yang diketahui
  pada waktu snapshot. Label folder konfigurasi tidak lagi dipakai sebagai filter harga.
- **Verifikasi:** `tools/build_exe.py` keluar 0; EXE baru berukuran 15,5 MiB. **Konfirmasi pengguna:**
  EXE mengimpor ke snapshot 4; `bar masuk` dan `bar terkini` sama-sama **1.002.024**, jadi perilaku
  filter sumber terkonfirmasi. Suite penuh: **912 lulus (33,28 dtk)**. Laporan mutu mencatat 3
  emiten kritis bermasalah (BNBR, FORU, PACK), 9 temuan tak wajar, dan 8 emiten dikeluarkan dari
  peringkat.
- **Belum dikerjakan:** lanjutkan tinjauan temuan BNBR, FORU, PACK, dan lima emiten tak wajar lain
  sebelum memakai peringkat.
- **Berkas:** `mejasaham/pengatur.py`, `docs/keputusan.md`, `docs/lanjutan.md`.

### Tinjauan awal temuan mutu snapshot 4 (22 Okt 2026 — sesi 41)

- Tes penuh yang dijalankan pengguna: **912 lulus (33,28 dtk)**.
- **BNBR:** 13–15 Feb 2023 tercatat 3.800 dengan volume 0; 16 Feb 71 dengan volume 26.365.600.
  Tidak ada aksi di basis data sekitar tanggal itu; seri harga resmi belum dicocokkan.
- **FORU:** harga basis data pada 14 Sep 2026 adalah 238 (volume 85.346.954), tetapi laman emiten
  menyatakan penutupan 4.650 (volume 4.375.800). KSEI mencatat jadwal HMETD cum 21 Sep dan record
  date 23 Sep; bar pada 14 Sep tetap tidak terverifikasi.
- **PACK:** penurunan 3.280 → 272 pada 12 Jan 2026 bertepatan dengan ex-date HMETD. Dokumen KSEI
  menyebut rasio 5:102 untuk OWK dan harga pelaksanaan Rp100. Aksi belum dimuat di tabel
  `aksi_korporasi`; jangan menyimpulkan harga teoretis atau mengubah data dari angka Yahoo saja.
- Temuan COCO, FISH, PYFA, SCCO, dan TMAS belum ditinjau. Tidak ada data yang diubah atau diimpor.
- Sumber primer: laman informasi saham FORU dan jadwal HMETD FORU/PACK di bagian sesi 41
  `docs/keputusan.md`.
- **Berikutnya:** cocokkan seri harga BNBR/FORU ke sumber resmi; rekam aksi PACK dari dokumen KSEI
  bila atribut berkas dapat dipenuhi; lanjutkan lima kode tersisa. Koreksi hanya lewat baris baru
  sesudah bukti diverifikasi.

### Rekonsiliasi per kode: pasangan dari nomor yang dirujuk UPT (12 Okt 2026)

- **Pasangan tidak lagi ditebak dari tanggal.** Nomor SPT penyebab dibaca dari kutipan di dalam
  PDF UPT ("Sehubungan dengan"), lalu dicari di **kepala** dokumen pada 56 lampiran multi-kode dan
  38 PDF riwayat kode tunggal. Pasangan sah hanya bila dokumen itu benar-benar memuat kodenya
  (baris tabel, atau identitas dokumen untuk pengumuman satu emiten). Nomor yang hanya muncul di
  badan teks tidak dihitung sebagai nomor terbit — badan teks memuat kutipan nomor lain yang bisa
  terpotong antar-baris.
- Keluaran: `.uji-data/riset-idx/rekonsiliasi-upt-per-kode-20261012.csv` (**41 baris** = 39 baris
  tinjauan 11 Okt + AKKU/INPS dari `2026-02-20_UPT_11` yang tertinggal) + ringkasan `.txt`.
  Kolomnya: nomor UPT, tanggal dokumen vs tanggal API, pasar, sesi (termasuk sesi per kode bila
  tabel UPT punya kolomnya), nomor SPT rujukan, berkas PDF, status kode di tabel SPT, episode
  terakhir, catatan, dan **kalimat keputusan sebagai bukti**. Verdict mentah:
  `.uji-data/riset-idx/verdict-upt-20261012.{json,txt}`.
- Hasil: 34 `TERKONFIRMASI` · 4 `DUPLIKAT_REKAMAN_API` · 1 `KOREKSI_BUKAN_PENCABUTAN_PENUH`
  (OCAP) · 2 `TERKONFIRMASI_TANPA_PDF_SPT` (ARTI, ELTY). Enam belas baris "tanpa kandidat" ternyata
  punya rujukan tegas: XSBC/XSSI → `Peng-S-00021/BEI.PLP/07-2024`; NIRO/WOWS/MDIA/VIVA/INAF/GPSO
  → `Peng-S-00005/BEI.PLP/02-2024`; FLMC → `Peng-S-00007/BEI.PLP-11-2023`; OCAP →
  `Peng-SPT-00003/BEI.PP3/04-2024`.
- Empat koreksi: UPT_48 ≡ UPT_49 identik byte-per-byte (8 baris API = 4 peristiwa); OCAP hanya
  membuka Pasar Negosiasi untuk crossing lalu disuspensi kembali; nomor SPT di UPT INAF/GPSO
  tercetak `…/05-2024` sedangkan dokumennya `…/02-2024`; status `Aktif` di tabel SPT = kode baru
  disuspensi (empat episode berumur hari). Kembar lain: SPT_31≡SPT_32, SPT_26≡SPT_27,
  SPT_05≡SPT_07.
- Batas bukti: berbasis **teks** ekstraksi (27 PDF UPT + paragraf keputusan/baris tabel SPT
  pasangannya), bukan tinjauan visual halaman per halaman. Rinciannya di
  `docs/riset-suspensi-multi-kode-2026-10.md`; keputusannya di `docs/keputusan.md` bagian 5.
- Verifikasi: `.\.venv\Scripts\python -m pytest` → **765 lulus**. Tidak ada perubahan kode, impor,
  atau perubahan basis data. Tahap berhenti untuk tinjauan sesuai K4.

### Rekonsiliasi temuan mutu delapan emiten snapshot 4 (22 Okt 2026 — sesi 42)

- **Hasil:** bukti resmi mengonfirmasi aksi PACK (HMETD/OWK, ex 12 Jan 2026, 5 saham lama : 102 HMETD, harga pelaksanaan Rp100), split FISH 1:10 (mulai nominal baru 9 Sep 2025), split SCCO 1:4 (mulai nominal baru 8 Mar 2024), split TMAS 1:10 (mulai nominal baru 23 Mei 2023), dan jadwal HMETD PYFA (cum 19 Apr, ex 22 Apr 2024). Anomali FISH/PYFA/SCCO terjadi sebelum aksi; TMAS bertepatan tetapi bar 23–24 Mei tetap tidak konsisten.
- **Belum terverifikasi:** BNBR belum punya seri resmi harian untuk 13–16 Feb 2023; harga FORU pada 14 Sep 2026 bertentangan dengan laman emiten (Yahoo Rp238/volume 85.346.954; emiten Rp4.650/volume 4.375.800); COCO 500 → 158 pada 30 Sep 2025 belum punya aksi penjelas. KSEI COCO menampilkan right distribution Juli 2026, bukan tanggal anomali.
- **Batas tahap:** tidak ada impor, koreksi, atau perubahan basis data. Tidak ada tes dijalankan karena ini tinjauan bukti/dokumen. Jangan menganggap aksi resmi sebagai bukti bahwa bar harga vendor benar.
- **Dokumentasi:** rincian per kode, sumber, dan kesimpulan ditambahkan ke `docs/keputusan.md` bagian 5. Sumber primer tertaut di sana.
- **Berikutnya:** (1) cocokkan seri harian resmi BNBR, FORU, COCO, FISH, PYFA, SCCO, TMAS; (2) siapkan satu baris aksi PACK append-only dari dokumen KSEI, tanpa menghitung harga penyesuaian; (3) berhenti untuk tinjauan sebelum impor.
- **Empat laporan akhir tahap:** tes: tidak dijalankan; ringkasan: rekonsiliasi awal delapan kode; belum: seri harga resmi tujuh kode dan draf aksi PACK; cara mengulang: tinjau `laporan-mutu.csv` di `.uji-data/mejasaham-exe/arsip-snapshot/2026-10-21/snapshot-4/` dan cocokkan setiap tanggal dengan sumber resmi. Tidak ada perintah tes yang relevan untuk tahap dokumentasi ini.


### Pemeriksaan lanjutan seri harga dan draf aksi PACK (22 Okt 2026 — sesi 43)

- Endpoint harian pada domain IDX teridentifikasi (`/primary/TradingSummary/GetStockSummary?date=YYYYMMDD`), tetapi web reader tidak dapat membuka dan permintaan langsung mendapat HTTP 403. Tidak ada seri harga IDX harian yang dapat dibandingkan untuk enam kode.
- FORU saja terverifikasi untuk 14 Sep 2026 dari laman informasi saham emitennya: low Rp4.330, open/high/close Rp4.650, volume 4.375.800. Konflik dengan vendor terbukti, tetapi sebabnya dan seri historis vendor masih belum terurai.
- TMAS: sumber sekunder yang mengutip pengumuman BEI menyebut split 1:10 dan harga teoritis 23 Mei Rp298; OHLC primer 23–24 Mei belum didapat. BNBR, COCO, FISH, PYFA, SCCO juga belum terverifikasi dari harga harian primer.
- Draf PACK dibuat di `docs/draf-aksi-korporasi-PACK-2026-10.csv`: ex-date 12 Jan 2026; rasio HMETD 5:102; harga Rp100 per unit OWK; tenggat kosong. Rasio/instrumen masih perlu ditinjau sebelum konfigurasi dan impor. Bukti lengkap: `docs/riset-harga-snapshot4-2026-10.md` dan sesi 43 `docs/keputusan.md` bagian 5.
- Tidak ada impor/koreksi data; tes tidak dijalankan (tahap riset dan dokumentasi). Langkah berikutnya: tinjau draf PACK dan dapatkan seri harga primer untuk enam ticker melalui akses IDX yang diizinkan. **Berhenti di sini sesuai K4.**
- Cara mengulang: periksa tautan sumber di catatan riset; bila akses endpoint IDX tersedia, query per tanggal temuan dan bandingkan OHLCV dengan `laporan-mutu.csv` snapshot 4.

### Tinjauan tambahan draf PACK dan sumber harga (22 Okt 2026 — sesi 44)

- Rasio PACK 5 saham : 102 HMETD, harga Rp100 per OWK, serta konversi 1:1 terkonfirmasi oleh pengumuman KSEI. Draf tidak diubah dan tidak diimpor karena tanggal pelaksanaan HMETD 22 Jan dalam jadwal KSEI berbeda konteks dengan contoh pelaksanaan 26 Jan pada surat KSEI lanjutan; `tenggat` tetap kosong menunggu klarifikasi.
- Price History KSEI yang terbuka tidak memuat tanggal anomali COCO/FISH/SCCO/TMAS. Halaman BNBR gagal HTTP 500 dan PYFA timeout. Enam ticker masih menunggu seri harga primer yang cocok.
- Tes tidak dijalankan (pemeriksaan sumber/dokumen); tidak ada perubahan basis data atau harga. Rincian/sumber: `docs/riset-harga-snapshot4-2026-10.md`, `docs/keputusan.md` sesi 44.
- **Berikutnya:** minta/temukan klarifikasi resmi deadline PACK; cari akses arsip OHLCV IDX yang diizinkan atau riwayat issuer untuk enam ticker; lalu cocokkan setiap tanggal anomali. Tahap berhenti sesuai K4.
- **Cara mengulang:** telaah pengumuman KSEI PACK dan halaman Price History KSEI yang tertaut di catatan riset; bandingkan OHLCV arsip resmi dengan snapshot 4. Tidak ada perintah tes relevan.

\r\n

**Sesi 48 (22 Okt 2026 — rancangan catatan aksi mutu PACK; menunggu tinjauan):** Mengusulkan representasi terpisah `catatan_aksi_mutu`, append-only dan point-in-time, agar fakta HMETD/OWK PACK hanya menjadi konteks laporan mutu. Usulan menjaga temuan lonjakan sampai OHLCV primer terverifikasi dan tidak mengaitkan baris ini ke posisi, penyesuaian harga, TERP, atau tindakan dasbor. Draf aksi operasional PACK tidak diimpor. Detail rancangan di `docs/riset-harga-snapshot4-2026-10.md`. Belum ada perubahan kode/basis data; tes tidak dijalankan. Tahap berhenti sesuai K4 untuk tinjauan pengguna. Enam emiten BNBR, COCO, FISH, PYFA, SCCO, TMAS tetap menunggu OHLCV primer. Berikutnya setelah tinjauan: setujui/perbaiki rancangan, lalu baru susun skema dan jalur impor terpisah. Tidak ada perintah tes relevan.

**Sesi 50 (22 Okt 2026 — impor catatan aksi mutu PACK):** draf ditinjau lalu diimpor ke basis data kerja `.uji-data/mejasaham` setelah cadangan dibuat di `.uji-data/cadangan-sesi49/20261022T111553703187+0700`. Impor keluar 0, snapshot 14 (tanggal data 11 Okt), 1 baris baru. Laporan mutu menampilkan 5 konteks aksi dan tetap mempertahankan 9 temuan tak wajar; 916 emiten dikeluarkan karena data bolong. `PRAGMA integrity_check` = `ok`; `v_catatan_aksi_mutu_terkini` memuat PACK / 2026-01-12 / `HMETD untuk OWK`, provenance KSEI, diketahui 22 Okt 2026 11:15 WIB. **Test tahap ini:** tidak dijalankan; sesi 49 sebelumnya: 914 lulus (48,53 dtk). **Ringkasan:** impor dan verifikasi catatan mutu PACK. **Belum:** OHLCV primer enam kode BNBR, COCO, FISH, PYFA, SCCO, TMAS; jangan anggap catatan aksi mengesahkan bar harga. **Cara menjalankan:** `python -m mejasaham --impor <folder> --folder-data .uji-data/mejasaham`; integritas via `PRAGMA integrity_check`. Lihat sesi 50 `docs/keputusan.md` bagian 5. Tahap berhenti sesuai K4.

**Sesi 51 (22 Okt 2026 — kanal OHLCV primer enam kode):** tanggal anomali dari arsip snapshot 4 dipatok: BNBR 16 Feb 2023; COCO 30 Sep 2025; FISH 1 Sep 2025; PYFA 16 Apr 2024; SCCO 1 Feb 2024; TMAS 23–24 Mei 2023. Sumber resmi IDX mengonfirmasi ringkasan saham publik dan distribusi EoD berlisensi melalui SIPD; tabel harga yang berhasil diakses hanya statistik bulanan, bukan OHLCV harian, sedangkan endpoint/halaman yang dicoba gagal 403. **Test:** tidak dijalankan (pemeriksaan sumber); tidak ada data/harga berubah. **Ringkasan:** jalur arsip EoD resmi terverifikasi, belum ada OHLCV primer yang diperoleh. **Belum:** cocokkan enam seri harian dari ekspor SIPD/licensee atau arsip resmi yang diizinkan. **Cara menjalankan:** bandingkan OHLCV arsip dengan `harga.csv` snapshot 4 yang dirujuk pada sesi 51 `docs/keputusan.md`. Tahap berhenti sesuai K4.
