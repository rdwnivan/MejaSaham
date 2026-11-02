# Riset: proses mati di uji jendela — PySide6 6.12.0 + CPython 3.14.7

**Status: ditangkal (T68), belum diperbaiki; sebabnya di luar repositori ini.**
Ditemukan 17 Okt 2026 (sesi 10) saat mengerjakan aksi #20 (dasbor menghitung konteks pasar di utas
pekerja). Berkas ini merangkum **bukti**, **apa yang sudah dicoba**, dan **apa yang belum** —
supaya sesi berikutnya (atau laporan upstream) tidak mengulang jalan yang sama.
**Reproduksi ulang berhasil 19 Okt 2026 (sesi 21): 2 dari 12 jalan suite penuh mati di 3.14.7;
A/B di 3.13.14 = 0 dari 12 — hasil dan bacaannya di bagian 10.**

## 1. Gejala

`tests/test_ui_jendela.py` berhenti **tanpa traceback Python**:

```
Windows fatal exception: access violation      (kadang: Fatal Python error: Aborted)
Thread 0x… [Pekerja] (most recent call first):
  File "tests/test_ui_jendela.py", line 483 in tugas
  File "mejasaham/ui/pekerja.py", line 33 in run
Current thread 0x… (most recent call first):
  File "mejasaham/ui/jendela.py", line 973 in tunggu_pekerja
```

Selalu di jalur tunggu penutupan: `Jendela.tunggu_pekerja()` →
`QApplication.processEvents()` / `QThread.wait(50)`, sementara sebuah `QThread` (dengan `run()`
Python) masih hidup. Kadang muncul sebagai `Aborted`, kadang `access violation` — keduanya proses
mati, bukan uji gagal.

> **Diperbarui 19 Okt 2026 (sesi 21, bagian 10):** pengukuran ulang di **seluruh suite** menemukan
> jalur yang **sedikit berbeda** tetapi satu keluarga: yang muncul di jejak bukan `tunggu_pekerja`,
> melainkan penungguan **di berkas uji sendiri** — `tests/test_ui_jendela.py:195 _tunggu` →
> `pekerja.wait(60_000)` (yaitu `QThread.wait()`), dipanggil dari
> `test_hasil_lama_dibuang_saat_pemuatan_gagal` baris 409. Pada kedua kematian itu **hanya utas utama**
> yang tercetak di dump (tidak ada bingkai `[Pekerja]`), berbeda dengan contoh di atas. Jadi yang
> menjadi ciri bukan nama fungsinya, melainkan **`QThread.wait()` di utas utama sementara pekerja
> hidup/baru selesai**.

## 2. Angka yang memisahkan sebab dari kebetulan

Satu perintah per jalan; hitungan dari 17 Okt 2026.

| Keadaan | Gagal / jalan |
|---|---|
| kode sebelum aksi #20 (`HEAD`) | **0 / 18** |
| kode aksi #20, tanpa penangkal | **7 / 18** |
| kode aksi #20, blok konteks pasar dimatikan | 0 / 12 |
| kode aksi #20, GC siklik dimatikan seluruhnya (plugin uji) | 0 / 12 |
| kode aksi #20, pohon Qt uji **ditahan** hidup | **12 / 12** |
| kode aksi #20 + T68 versi pertama (`Pekerja.run` saja) | 0 / 12 uji jendela, **1 / 8 suite penuh** |
| kode aksi #20 + T68 final (penahan berpenghitung, 2 jalur) | **0 / 10 uji jendela, 0 / 8 suite penuh** |

Bacaannya: yang memicu adalah **pengumpulan sampah siklik** yang berjalan sementara objek Qt
dialokasikan di sekitar utas pekerja. Aksi #20 menambah alokasi (karena itu frekuensi GC) di dalam
utas pekerja — jadi cacat yang tadinya jarang tersentuh menjadi sering.

Versi pertama penangkalnya **bocor** karena `gc.enable()` adalah keadaan **proses**, bukan per-utas:
satu pekerja yang selesai menyalakan kembali GC tepat ketika jalur tunggu masih mengandalkannya
mati. Versi final memakai penghitung (`mejasaham/ui/pekerja.py:tahan_gc_siklik()`) yang dipakai
`Pekerja.run` **dan** `Jendela.tunggu_pekerja`.

## 3. Lingkungan (terukur dari metadata paket)

| | |
|---|---|
| Python | 3.14.7 (MSC v.1944 64 bit) |
| PySide6 / PySide6-Essentials / shiboken6 | 6.12.0 |
| `Requires-Python` PySide6 6.12.0 | `>=3.10,<3.16` |
| Classifier resmi | 3.10 · 3.11 · 3.12 · 3.13 · **3.14** · 3.15 |

Artinya ini **kombinasi yang didukung** oleh paketnya, bukan pemakaian di luar dukungan. Karena itu
laporan upstream sah, dan memin versi Python bukan satu-satunya jalan.

## 4. Yang sudah dicoba untuk mempersempit (dan hasilnya)

> **Diperbarui 17 Okt 2026 (sesi 14): angka di bagian ini — termasuk "7 dari 18 jalan mati" — adalah
> pengukuran sesi 10 dan **tetap sah**. Hari itu cacatnya muncul 39% jalan; pada 24 jalan tanpa
> penangkal di sesi 14 ia **tidak muncul sekali pun** (bagian 8.5). Jadi angka-angka di bawah
> menggambarkan keadaan yang **bergantung waktu**, bukan laju yang bisa diandalkan. Baca bagian 8.5
> sebelum memakai angka mana pun dari dokumen ini.

Percobaan ada di `.uji-data/riset-idx/pyside6-gc/`:

1. **`repro-minimal.py`** — `QThread` dengan `run()` Python + signal ke widget, pohon widget kecil
   yang ditinggalkan, `gc.collect()` sementara utas hidup. **30 putaran: tidak ada proses mati.**
2. **`repro-jendela.py`** — ditambah: `QMainWindow` + `QTabWidget` + lima "layar" (tabel, kotak
   teks, tombol ke bound method), **tiga** pekerja per putaran, jalur tunggu yang sama
   (`processEvents` + `wait(50)`), dan **atribut pemilik pekerja ditimpa** sementara pekerja lama
   masih berjalan (pola `jendela._pekerja_kode = pekerja`). **12 putaran × 4 jalan: tidak ada
   proses mati.**

Jadi cacat ini **belum terisolasi di luar pytest**: ia muncul pada kombinasi suite uji (urutan
banyak pohon Qt + sampah siklik + pekerja hidup), bukan pada pola kecil yang bisa diprediksi.
Itu sendiri informasi untuk laporan upstream — dan alasan mengapa penangkalnya tetap dipasang di
aplikasi, bukan hanya di uji.

## 5. Yang **belum** dicoba (urut dari yang paling murah)

> **Diperbarui 17 Okt 2026 (sesi 15):** nomor 2 **sudah dijalankan** (bagian 8.5) dan hasilnya **belum
> dapat disimpulkan**; rencana berikutnya yang sudah dikunci ada di **bagian 9** (K69). Nomor 1
> (laporan upstream) berkasnya **sudah siap** di `docs/laporan-pyside6-siap-kirim.md` dan menunggu
> dikirim pengguna (K66). Daftar di bawah tetap ditulis apa adanya sebagai urutan aslinya.
>
> **Diperbarui 19 Okt 2026 (sesi 21):** langkah 1 rencana bagian 9 **sudah dijalankan** dan
> **berhasil mereproduksi** cacatnya (2 dari 12 jalan mati di 3.14.7), lalu langkah 2 (A/B 3.13)
> juga dijalankan: **0 dari 12 mati**. Hasil lengkapnya di **bagian 10**. Nomor 3 (uji versi PySide6
> lain) **belum** dijalankan dan **tidak** dipicu oleh hasil ini.

1. **Laporan upstream** ke `bugreports.qt.io` (proyek *Qt for Python*) dengan lampiran: versi
   (bagian 3), tabel angka (bagian 2), dan `tests/test_ui_jendela.py` sebagai repro yang bisa
   dijalankan (7 dari 18 jalan pada kode tanpa penangkal).
2. **Uji pada Python 3.13** dengan PySide6 6.12.0 yang sama: bila tidak lagi mati, pin versi Python
   adalah jawaban yang paling murah. Menuntut pemasangan interpreter + PySide6 untuk interpreter itu
   (keputusan dependensi — lihat skill `adding-dependencies`). **→ sudah dijalankan 17 Okt 2026;
   hasilnya di bagian 8.5 (belum dapat disimpulkan).**
3. **Uji PySide6 versi lain** (6.11 / 6.13) pada Python 3.14 yang sama. **→ langkah inilah yang
   tersisa, dan menjadi cabang ke-3 K69.**
4. Menelusuri `Qt for Python Development Notes` dan basis bug Qt untuk "GC + QThread + 3.14";
   penelusuran awal 17 Okt 2026 belum menemukan laporan yang cocok (hasil pencarian yang muncul
   hanya petunjuk umum soal masa hidup pembungkus shiboken).

## 6. Keputusan yang berlaku sekarang

* **T68** (`docs/arsitektur.md`): GC siklik dimatikan selama tugas pekerja berjalan **dan** selama
  jalur tunggu penutupan. Ia **penangkal**, bukan perbaikan: yang hilang hanya gejalanya.
* Uji jendela karena itu tetap dijalankan apa adanya (bukan `gc.disable()` di seluruh sesi uji):
  mematikan GC untuk uji akan menyembunyikan cacatnya dari suite, sedangkan aplikasinya tetap
  memakai jalur yang sama.
* Yang **tidak** boleh dilakukan sebagai "perbaikan": mematikan GC di seluruh proses, atau
  memindahkan pekerjaan ke utas tampilan (itu mengembalikan jendela yang membeku — T65).

## 7. Draf laporan upstream (siap ditempel)

Ditulis dalam bahasa Inggris karena itu bahasa pelacak bug Qt; yang perlu diganti hanya tanda
`<...>`. Isinya sengaja ringkas dan hanya memuat yang **terukur**.

**Berkas siap tempelnya sudah disiapkan (P37/K66): `docs/laporan-pyside6-siap-kirim.md`** — berisi
teks di bawah dalam bentuk yang bisa ditempel apa adanya (tanpa kutipan Markdown), langkah
mengirimnya menurut halaman resmi Qt, daftar lampiran, dan batas yang harus disebut apa adanya
(tidak ada reproducer minimal). Bagian ini tetap yang berlaku bila keduanya berbeda.

> **Title:** Intermittent native crash (access violation / abort) in `QThread.wait()` +
> `QApplication.processEvents()` while a Python-implemented `QThread` is running (PySide6 6.12.0,
> CPython 3.14.7, Windows)
>
> **Environment:** Windows 11 x64; Python 3.14.7 (MSC v.1944 64 bit); PySide6 6.12.0
> (PySide6-Essentials 6.12.0, shiboken6 6.12.0); Qt platform plugin `offscreen`; no Qt GUI session.
>
> **Description.** In a test suite that repeatedly creates and drops `QWidget` trees while
> `QThread` subclasses with a Python `run()` are running, the process intermittently dies with
> `Windows fatal exception: access violation` or `Fatal Python error: Aborted`, **without any
> Python traceback**. The faulting frames are always:
>
> ```
> Current thread (main):
>   File ".../jendela.py", line ..., in tunggu_pekerja      # QApplication.processEvents(); QThread.wait(50)
> Thread ... [worker]:
>   File ".../test_ui_jendela.py", line ..., in tugas       # time.sleep()
> ```
>
> The main thread is in a cooperative wait loop:
>
> ```python
> for pekerja in self.pekerja_aktif():
>     while pekerja.isRunning():
>         QApplication.processEvents()
>         pekerja.wait(50)
> ```
>
> **Reproduction.** `<repo>/tests/test_ui_jendela.py` (attached, together with the smallest data
> fixture it needs). Measured over 18 runs of that file: **7 runs die, 11 pass** on the code
> without the mitigation; **0 of 18** before the feature that added heavy Python allocation inside
> the worker. With `gc.disable()` for the whole run: **0 of 12**. With the abandoned `QWidget`
> trees kept alive (so the cyclic GC has nothing of ours to collect): **12 of 12 die** — i.e. the
> crash correlates with cyclic garbage collection happening while a worker thread is alive, not
> with one particular object being freed.
>
> **What I tried.** (1) `gc.disable()` during `QThread.run()`: reduces but does not remove it
> (1 of 8 full-suite runs, because `gc.enable()` is process-wide and a finishing worker re-enables
> it while another thread still relies on it being off). (2) A reference-counted "hold" used by
> both the worker body and the closing wait loop: 0 of 10 file runs and 0 of 8 full-suite runs —
> i.e. a workaround, not a fix. (3) Two standalone minimal reproducers (a small `QThread` +
> widget tree + explicit `gc.collect()`, and a window-shaped one with three workers and the same
> wait loop) did **not** reproduce it in 30 and 48 rounds respectively.
>
> **Expected:** no process termination; at worst a Python exception that can be caught.
>
> Please tell me what diagnostic output would help (e.g. a shiboken debug build, `faulthandler`
> dumps with C stacks) and I will provide it.

**Setelah terkirim:** catat tautan isunya di sini (satu baris) supaya P38 punya titik rujuk dan T68
 bisa dicabut kelak kalau jawabannya sudah ada.

## 8. Uji Python 3.13 — keputusan dependensi (K67/P38; **sudah dijalankan**, hasilnya di 8.5)

**Tujuan (K60 b):** menentukan apakah proses yang mati di `tests/test_ui_jendela.py` hilang pada
CPython **3.13** dengan **PySide6 6.12.0 yang sama**. Bila hilang, jawabannya adalah **pin versi
Python** (keputusan tersendiri, sesudah hasilnya ada); bila tidak, langkah berikutnya menurut K60
adalah menguji versi PySide6 lain. **T68 tetap berlaku** sampai ada jawaban yang lebih baik.

**Keadaan sekarang: belum ada satu byte pun yang diunduh atau dipasang.** Yang di bawah ini
diperiksa dengan perintah baca-saja pada 17 Okt 2026.

### 8.1 Yang akan dipasang, dan di mana

| Hal | Nilai | Bukti/catatan |
|---|---|---|
| Alat yang dipakai | **`uv 0.12.2`** — sudah ada di mesin ini | `uv --version` → `uv 0.12.2 (46ead6098 2026-08-05 x86_64-pc-windows-msvc)`. **Tidak ada dependensi baru yang ditambahkan ke proyek** — yang dipakai alat yang memang sudah terpasang |
| Interpreter | **CPython 3.13.14** (standalone build uv, `windows-x86_64-none`) | `uv python list` → `cpython-3.13.14-windows-x86_64-none <download available>`. Ia masuk ke folder data uv (bukan `PATH`, bukan registry, bukan Start Menu) |
| Roda PySide6 | **`pyside6-6.12.0-cp310-abi3-win_amd64.whl`** — **abi3**, jadi roda yang **sama** dipakai 3.13 (tidak perlu roda khusus 3.13) | `uv pip install --dry-run --python-version 3.13 --python-platform windows PySide6==6.12.0 -v` memilih `cp310-abi3` untuk `pyside6`, `pyside6-essentials`, `pyside6-addons`, `pyside6-pdf`, `pyside6-webengine`, `shiboken6` |
| Isi lingkungan uji | `requirements.txt` (PySide6 6.12.0 + **yfinance 1.7.0**) + `pytest` | `yfinance` ikut karena `pengatur` mengimpor `pengambil` (`SumberData`), dan `tests/test_ui_jendela.py` mengimpor jalur itu |
| Letak lingkungan | **`.tmp/py313/`** (di dalam repo, sudah gitignored) | `.tmp/` tidak ikut git; `.venv` repo **tidak disentuh** |

### 8.2 Biaya dan cara mencabutnya

* **Disk:** keluarga PySide6+shiboken6 yang terpasang di `.venv` sekarang = **651 MB**
  (`Get-ChildItem .venv\Lib\site-packages`), jadi salinan kedua kira-kira sebesar itu, ditambah
  interpreter (~30–60 MB) dan `yfinance`. Angka unduhan yang sebenarnya akan dilaporkan saat
  pemasangan.
* **Pencabutan (dua baris):** `uv python uninstall 3.13` lalu hapus folder `.tmp\py313`.
* **Yang tidak berubah:** `.venv` repo, `requirements.txt`, `requirements.lock.txt`, dan **pin versi
  Python proyek** (K3) — pin itu keputusan tersendiri sesudah hasil ujinya ada.

### 8.3 Alternatif yang ditimbang (dan kenapa tidak dipilih)

| Alternatif | Kenapa tidak |
|---|---|
| `winget install Python.3.13` | MSI sistem: mengubah `PATH` dan Start Menu, pencabutannya lewat Settings; lebih banyak jejak daripada yang dibutuhkan untuk satu uji |
| Installer python.org | Sama seperti di atas, ditambah kemungkinan menuntut hak admin |
| Python dari Microsoft Store | Integrasi sistem yang paling sulit dicabut |
| **`uv python install 3.13` (dipilih)** | Alatnya **sudah ada**; interpreter-nya terisolasi di folder data uv; pencabutannya satu perintah |

### 8.4 Langkah ujinya (sesudah disetujui)

```powershell
uv venv --python 3.13 .tmp\py313
uv pip install --python .tmp\py313\Scripts\python.exe -r requirements.txt pytest
$env:QT_QPA_PLATFORM = "offscreen"
foreach ($i in 1..12) { .tmp\py313\Scripts\python.exe -m pytest tests\test_ui_jendela.py -q }
```

**Kriteria keluar (K60 b):** 12 jalan **tanpa** proses yang mati → pin versi Python adalah
jawabannya. Hasilnya dicatat di dokumen ini (tanggal, versi, jumlah jalan, jumlah yang mati) —
termasuk bila hasilnya "masih mati", karena itu justru yang menentukan langkah berikutnya.

### 8.5 Hasil uji Python 3.13 (17 Okt 2026) — **belum dapat disimpulkan**

Dijalankan sesuai 8.4, lalu **ditambah satu percobaan yang lebih menentukan**: uji yang sama
dijalankan **tanpa penangkal T68** (`tahan_gc_siklik` diganti blok kosong lewat plugin pytest
`.tmp/plugin_tanpa_tahan.py`), sebab "0 kematian **dengan** penangkal" sudah dijamin penangkalnya dan
karena itu tidak membuktikan apa pun tentang versi Python. A/B dijalankan pada mesin yang sama, hari
yang sama, dua belas jalan masing-masing.

| Kondisi | CPython 3.14.7 | CPython 3.13.14 |
|---|---|---|
| **Dengan** penangkal T68 | 0 dari 12 mati · 36 lulus | **0 dari 12 mati · 36 lulus** |
| **Tanpa** penangkal T68 | **0 dari 12 mati** · 33 lulus · **3 uji gagal** | **0 dari 12 mati** · 33 lulus · **3 uji gagal** |

* Tiga uji yang gagal di baris "tanpa penangkal" adalah **penjaga penangkalnya sendiri**
  (`test_pekerja_mematikan_gc_siklik_selama_tugasnya`,
  `test_penahan_gc_bersarang_tidak_saling_menyalakan`,
  `test_jalur_tunggu_mematikan_gc_siklik`). Kegagalan itu justru **bukti bahwa plugin-nya bekerja**:
  GC memang tidak dimatikan, dan tetap **tidak ada proses yang mati**.
* Patokan "mati" = **tidak ada ringkasan pytest** (baris terakhir bukan `N passed/failed`). Pola teks
  `access violation`/`Aborted` **tidak boleh** dipakai sebagai penanda: ia cocok juga dengan
  *docstring* uji yang mengutip gejalanya (terukur: tanda "fatal=True" di 24 log, semuanya palsu).
* **Kesimpulannya: TIDAK ADA yang bisa disimpulkan tentang versi Python dari percobaan ini** — cacat
  itu **tidak muncul satu kali pun** di kedua versi begitu penangkalnya dilepas, padahal pengukuran
  17 Okt 2026 sesi sebelumnya (bagian 2) mencatat **7 dari 18 jalan mati** tanpa penangkal pada
  3.14.7. Artinya cacat ini **bergantung waktu dan tidak selalu dapat direproduksi**: hari itu ia
  muncul 39% jalan, hari ini 0% pada 24 jalan.
* **Konsekuensinya untuk langkah berikutnya (K60):** "pin versi Python" **belum** bisa diputuskan —
  memilihnya hanya sah bila 3.13 jelas-jelas tidak mati sementara 3.14 jelas-jelas mati pada kondisi
  yang sama. Yang lebih menentukan lebih dulu: **membuat cacatnya reproduktif lagi** (kontrol harus
  gagal) — kandidatnya menjalankan **seluruh suite** 12× tanpa penangkal, atau menambah beban alokasi
  di utas pekerja seperti kondisi sesi 10 — **atau** melangkah ke langkah K60 berikutnya, yaitu
  menguji **versi PySide6 lain** dengan CPython 3.14.7 yang sama. **T68 tetap dipakai** sampai ada
  jawaban yang lebih baik.
* **Catatan untuk laporan upstream (K66):** angka 7/18 di bagian 7 **tetap pengukuran yang sah**
  (18 jalan, 17 Okt 2026 sesi sebelumnya), tetapi pengirimnya perlu tahu bahwa cacat itu **tidak
  selalu dapat direproduksi**; itu sudah ditambahkan sebagai catatan di
  `docs/laporan-pyside6-siap-kirim.md` supaya tidak terbaca sebagai janji "selalu mati 7 dari 18".

**Lingkungan uji yang dipasang (sekali, bisa dicabut):**

| Hal | Nilai terukur |
|---|---|
| Interpreter | CPython **3.13.14** (`uv`, unduhan **20,9 MiB**; `python --version` → 3.13.14) |
| Paket | PySide6 **6.12.0** · shiboken6 **6.12.0** · yfinance 1.7.0 · pytest **9.1.1** (sama dengan `.venv`) |
| `uv pip check` | **All installed packages are compatible** (36 paket) |
| Letak & ukuran | `.tmp/py313` — **767 MB** di disk (gitignored) |
| Pencabutan | `uv python uninstall 3.13` + hapus `.tmp\py313` |
| Reproduksi A/B | `$env:PYTHONPATH="$PWD\.tmp"; py -m pytest tests\test_ui_jendela.py -q -p plugin_tanpa_tahan` |

## 9. Rencana langkah berikutnya (K69) — **sudah dijalankan 19 Okt 2026**, hasilnya di bagian 10

> **Status 19 Okt 2026 (sesi 21):** langkah 1 dan 2 di bawah **sudah dijalankan apa adanya**; hasil,
> angka, dan bacaannya ada di **bagian 10**. Bagian ini tetap disimpan sebagai rencana aslinya —
> termasuk plugin dan patokan "mati" — supaya pengukuran itu bisa diulang persis. Langkah 3
> (**uji versi PySide6 lain**) **belum** dijalankan; ia hanya dipicu bila reproduksi gagal atau A/B
> seri, dan itu **tidak** terjadi di sini.

Rekomendasi sesi 15, disetujui pengguna **"sesuai rekomendasi"**, tetapi **diminta dicatat dulu**
("jangan dijalankan, catet aja dulu") karena akan dilanjutkan di sesi baru. Urutannya **mengikat**:

1. **Reproduksi ulang cacatnya lebih dulu — kontrolnya harus gagal.** Pelajaran 8.5: perbandingan
   versi tidak bisa menyimpulkan apa pun bila cacatnya tidak muncul di versi mana pun. Yang dijalankan:
   **seluruh suite** (bukan hanya `tests/test_ui_jendela.py` — bebannya lebih besar dan itu mendekati
   kondisi sesi 10) **12× tanpa penangkal**, di CPython 3.14.7:

   ```powershell
   $env:PYTHONPATH = "$PWD\.tmp"; $env:QT_QPA_PLATFORM = "offscreen"
   foreach ($i in 1..12) { .\.venv\Scripts\python.exe -m pytest -q -p plugin_tanpa_tahan }
   ```

   **Patokan "mati" = tidak ada ringkasan pytest** pada jalan itu. **Jangan** memakai pola teks
   `access violation`/`Aborted` sebagai penanda — terukur 8.5: pola itu cocok juga dengan *docstring*
   uji yang mengutip gejalanya, sehingga 24 log bertanda "fatal" semuanya palsu.
   Perkiraan waktu: 12 × ±27 dtk ≈ **5–6 menit**.
   * Kalau **ada** yang mati → lanjut ke langkah 2 (kontrol sudah gagal, perbandingannya jadi bermakna).
   * Kalau **0 dari 12** juga → **berhenti di sini**: jangan pin versi Python, jangan menyimpulkan
     apa pun tentang 3.13 dari 8.5, dan langsung ke langkah 3.
2. **A/B pada kondisi yang identik** (hanya bila langkah 1 gagal): ulangi **persis** perintah itu di
   3.13.14 (`.tmp\py313\Scripts\python.exe`), 12 jalan, tanpa penangkal. Baru sesudah itu
   **"pin versi Python"** boleh diputuskan — dan itu **keputusan dependensi tersendiri** (mengubah pin
   Python proyek, K3), bukan lanjutan otomatis dari K67.
3. **Bila reproduksi tidak berhasil (atau hasil A/B seri):** langkah K60 berikutnya = **uji versi
   PySide6 lain** dengan CPython 3.14.7 yang sama. Bentuknya mengikuti pola K67 yang sudah terbukti:
   lingkungan **terpisah** (mis. `.tmp/pyside-baru`), **laporan pemasangan lebih dulu** sebagai
   keputusan dependensi (versi, sumber, ukuran, cara mencabut), lalu uji yang sama. Roda PySide6
   kemungkinan juga `cpXXX-abi3`, jadi kemungkinan **tidak** menuntut interpreter baru. Yang dicatat:
   nomor versi, tanggal, jumlah jalan, jumlah yang mati.
4. **Yang tidak berubah di semua cabang:** **T68 tetap dipakai**; **laporan upstream tetap dikirim**
   (K66) dan **tidak** menunggu langkah ini; dan **"0 kematian dengan penangkal" tidak boleh dipakai
   sebagai bukti apa pun** — itu dijamin penangkalnya (kesalahan yang hampir terjadi di 8.5).
5. **Kalau ada uji lain yang gagal di 3.13 karena sebab lain** (mis. perbedaan perilaku antarversi),
   itu dicatat **terpisah** dari hitungan kematian: yang diukur di sini adalah proses yang mati, bukan
   daftar uji yang lulus.

**Isi plugin `plugin_tanpa_tahan.py`** (dipakai di 8.5; disimpan di `.tmp/` yang gitignored, jadi
sumbernya dicatat di sini supaya sesi baru bisa membuatnya lagi apa adanya):

```python
"""Plugin pytest sekali pakai: MATIKAN penangkal T68 supaya cacatnya bisa terlihat."""
from __future__ import annotations

import contextlib
from collections.abc import Iterator

from mejasaham.ui import jendela, pekerja


@contextlib.contextmanager
def _tanpa_tahan() -> Iterator[None]:
    yield


pekerja.tahan_gc_siklik = _tanpa_tahan
jendela.tahan_gc_siklik = _tanpa_tahan
```

Uji penjaga penangkal (tiga buah) akan **gagal** selama plugin ini aktif — itu memang yang
diharapkan, dan justru **bukti** bahwa penangkalnya benar-benar dimatikan.

## 10. Hasil K69 — reproduksi ulang dan A/B (19 Okt 2026, sesi 21)

**Status: langkah 1 dan 2 sudah dijalankan.** Reproduksinya **berhasil** (kontrol gagal: **2 dari
12** jalan mati di 3.14.7), dan A/B-nya **0 dari 12** di 3.13.14 — jadi menurut huruf K69 keputusan
pin versi Python **boleh** diambil sekarang, tetapi buktinya **lemah secara statistik** (lihat 10.4).
**T68 tetap dipakai** dan laporan upstream (K66) tetap menunggu dikirim pengguna.

### 10.1 Kondisi pengukuran

| Hal | Nilai |
|---|---|
| Kode yang diuji | working tree 19 Okt 2026 = `HEAD` `97d749e` + perubahan sesi 20 yang **belum di-commit** |
| Perintah | `.\.venv\Scripts\python.exe -m pytest -q -p plugin_tanpa_tahan` (3.14.7) · `.tmp\py313\Scripts\python.exe -m pytest -q -p plugin_tanpa_tahan` (3.13.14) |
| Lingkungan | `PYTHONPATH=.tmp`, `QT_QPA_PLATFORM=offscreen`; plugin penangkal-mati dari bagian 9 |
| Patokan "mati" | **tidak ada ringkasan pytest** pada jalan itu (regex di skrip pemeriksa), **bukan** pola teks |
| Berkas bukti | `.uji-data/uji-k69/reproduksi/jalan-1…12.txt` (3.14) · `.uji-data/uji-k69/reproduksi-313/jalan-1…12.txt` (3.13) · ringkasannya `.uji-data/uji-k69/bukti-k69.txt` |
| Skrip pembuat/periksa | `.uji-data/riset-idx/k69/` (`k69-jalankan.py`, `k69-jalankan-313.py`, `k69-ringkas.py`, `plugin_tanpa_tahan.py`) — salinan dari `.tmp/` yang gitignored |

### 10.2 Hasil

| Kondisi | Jalan | **Mati** | Ringkasan tiap jalan |
|---|---|---|---|
| CPython **3.14.7**, tanpa penangkal (**kontrol**) | 12 | **2** | 10 jalan `3 failed, 879 passed` |
| CPython **3.13.14**, tanpa penangkal (**A/B**) | 12 | **0** | 11 jalan `3 failed, 879 passed` · 1 jalan `4 failed, 878 passed` |

Tiga kegagalan yang muncul di hampir semua jalan adalah **penjaga penangkalnya sendiri**
(`test_pekerja_mematikan_gc_siklik_selama_tugasnya`, `test_penahan_gc_bersarang_tidak_saling_menyalakan`,
`test_jalur_tunggu_mematikan_gc_siklik`) — justru bukti bahwa plugin bekerja. Kegagalan **keempat**
pada satu jalan 3.13 dibahas di 10.3 butir 5; ia **bukan** kematian proses dan **bukan** soal versi.

**Kedua kematian (3.14.7) identik bentuknya:**

* jalan **1** (70 dtk) dan jalan **10** (40 dtk), keduanya `exit=3`;
* `Fatal Python error: Aborted` — **bukan** `access violation`, dan **tanpa** traceback Python;
* jejaknya **selalu**: `tests/test_ui_jendela.py:195 _tunggu` → `pekerja.wait(60_000)` (yaitu
  `QThread.wait()`), dipanggil dari `test_hasil_lama_dibuang_saat_pemuatan_gagal` baris 409;
* dump-nya **hanya memuat utas utama** — tidak ada bingkai `[Pekerja]` seperti pada contoh bagian 1.

### 10.3 Yang perlu dibaca dari angka ini

1. **Kontrolnya gagal — itu inti langkah 1.** Cacatnya bisa direproduksi lagi di 3.14.7 pada beban
   suite penuh, sesudah 8.5 mencatat 0 kematian di 24 jalan berkas-tunggal. Jadi "tidak muncul di
   24 jalan" pada 8.5 **bukan** bukti bahwa cacatnya hilang; bebannya yang kurang.
2. **Laju 2/12 (17%) lebih rendah daripada 7/18 (39%) sesi 10.** Keduanya sah sebagai pengukuran
   pada harinya; cacat ini memang bergantung waktu. Karena itu angka mana pun di dokumen ini harus
   dibaca sebagai **rentang frekuensi**, bukan laju tetap.
3. **Jebakan pola teks terulang dan terukur lagi.** Kata `access violation` muncul di **12 dari 12**
   log — semuanya dari *docstring* uji yang mengutip gejalanya, **termasuk 10 log yang prosesnya
   hidup**. Patokan "tidak ada ringkasan pytest" tetap satu-satunya penanda yang benar.
4. **A/B-nya 0/12, tetapi jangan dibaca sebagai "3.13 menyelesaikan cacatnya".** Dengan 2 kematian
   dari 24 jalan seluruhnya, uji Fisher dua sisi memberi **p ≈ 0,48** — perbedaan 2 vs 0 itu **tidak
   dapat dibedakan dari kebetulan**. Untuk daya uji yang layak (mis. 80%) dibutuhkan kira-kira
   **100–150 jalan per versi** (≈ 3–4 jam per versi pada mesin ini), dan itu tidak sepadan untuk
   keputusan yang biayanya besar untuk dibatalkan.
5. **Satu kegagalan tambahan di 3.13 (bukan versi, bukan kematian):**
   `tests/test_ui_tulis.py::test_impor_dari_jendela_sama_dengan_baris_perintah` gagal pada jalan 12
   karena membandingkan baris `snapshot` **termasuk `jam_ambil`/`batas_diketahui`** dari dua impor
   terpisah: `…T04:43:32+07:00` vs `…T04:43:33+07:00`. Uji itu **bergantung detik** dan karena itu
   **flaky** (± 1 dari 12 jalan) — ditemukan di sini; waktu itu **belum** diperbaiki, dan diusulkan
   sebagai pekerjaan tersendiri (U32 di `docs/keputusan.md`, usulan aksi #26). **Sudah diperbaiki
   19 Okt 2026 (sesi 23): K75 → aksi #26 → T76** (bukti `.uji-data/uji-k75/bukti/`). Ia **tidak**
   memengaruhi hitungan kematian (K69 butir 5: kegagalan uji dicatat terpisah).
6. **Satu jalan (3.14, jalan 9) berlangsung 478 dtk** (7:55) alih-alih ± 97 dtk dan **tidak** mati;
   sebabnya tidak diselidiki (beban mesin luar). Ia hanya memperpanjang waktu, tidak mengubah hasil.
7. **Lingkungan 3.13 harus dibangun ulang** karena `.tmp/py313` sudah tidak ada (interpreternya
   masih terpasang di folder data `uv`). Pembangunannya **10,7 dtk, seluruhnya dari cache `uv`** —
   **tanpa unduhan** — dan hasilnya sama dengan 8.5: CPython 3.13.14 · PySide6 6.12.0 · shiboken6
   6.12.0 · pytest 9.1.1 · yfinance 1.7.0 · **769 MB** · `uv pip check` bersih (36 paket).

### 10.4 Kesimpulan, rekomendasi, dan yang belum dikerjakan

* **K69 langkah 1 — selesai, kontrol gagal.** Syarat untuk membandingkan versi terpenuhi.
* **K69 langkah 2 — selesai, A/B seri secara statistik.** Menurut huruf K69, "pin versi Python"
  **boleh** diputuskan sekarang (kontrol gagal di satu versi, tidak di versi lain). Menurut
  **buktinya**, keputusan itu belum pantas: 2 vs 0 dengan p ≈ 0,48.
* **Rekomendasi sesi ini:** **jangan pin versi Python sekarang.** T68 tetap dipakai; **kirim laporan
  upstream** (K66) sebab ia kini punya **kontrol yang gagal** — itu yang diminta pelacak Qt, dan
  lebih bernilai daripada memindahkan seluruh proyek ke 3.13 atas beda 2 vs 0. Bila kelak Qt menjawab,
  atau cacatnya muncul lagi di pemakaian nyata, keputusan pin (dan **langkah 3**: uji PySide6 lain)
  bisa ditinjau ulang dengan bukti baru.
* **Yang belum dikerjakan:** **langkah 3** (uji versi PySide6 lain) — **tidak** dipicu, sebab
  reproduksi berhasil dan A/B tidak seri; **laporan upstream** tetap menunggu pengiriman pengguna;
  ~~**perbaikan uji flaky** (10.3 butir 5) belum dikerjakan~~ → **sudah dikerjakan 19 Okt 2026
  (sesi 23): K75 → aksi #26 → T76**.

**Cara mengulang pengukuran ini:**

```powershell
$env:PYTHONPATH = "$PWD\.tmp"; $env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python .tmp\k69-jalankan.py 12                 # kontrol: 3.14.7
.tmp\py313\Scripts\python .tmp\k69-jalankan-313.py 12          # A/B: 3.13.14
.\.venv\Scripts\python .tmp\k69-ringkas.py                     # ringkasan + bukti-k69.txt
```

Bila `.tmp/py313` tidak ada lagi: `uv venv --python 3.13 .tmp\py313` lalu
`uv pip install --python .tmp\py313\Scripts\python.exe -r requirements.txt pytest` (10,7 dtk dari
cache pada 19 Okt 2026).
