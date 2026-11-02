# Laporan cacat PySide6 — berkas **siap kirim** (P37/K66)

**Berkas ini turunan, bukan sumber kebenaran.** Isinya = **teks siap tempel** untuk pelacak bug Qt,
ditambah langkah mengirim dan daftar lampirannya. Angka dan konteks teknisnya berasal dari
`docs/riset-pyside6-gc-2026-10.md` — **bagian itu yang berlaku** bila keduanya berbeda; berkas ini
hanya menyajikan ulang isinya dalam bentuk yang bisa langsung ditempel (tanpa kutipan Markdown,
tanpa komentar berbahasa Indonesia).

Pengirimnya **pengguna** (K60 a): laporan ini menyatakan pengalaman Anda dan dikirim atas nama akun
Anda. Sesi agen tidak mengirimnya — **dikunci ulang sebagai K84 (sesi 30):** pengiriman tetap
pekerjaan pengguna; agen hanya boleh menyiapkan teks isian formulir bila diminta.

---

## 1. Sebelum menempel — daftar centang

| # | Yang diperiksa | Kenapa |
|---|---|---|
| 1 | **Akun Qt** di <https://account.qt.io/> | Pelacak Qt menuntut akun untuk membuat isu |
| 2 | **Cari duplikat** di <https://bugreports.qt.io/browse/PYSIDE> (Quick Search, mis. `QThread access violation`, `processEvents crash`, `cyclic gc`) | Isu yang sudah ada cukup diberi komentar + Vote; peluang ditangani lebih besar daripada isu baru |
| 3 | **Isi medan pelacak**: Project **Qt for Python**, Type **Bug**, Component **PySide** (pilihan lain: **Shiboken** — lihat catatan di bawah) | Langkah resmi Qt (lihat bagian 4) |
| 4 | **Tidak ada placeholder yang perlu diganti** — teks di bagian 3 sudah memuat angka dan versi yang sebenarnya (PySide6 6.12.0 / PySide6-Essentials 6.12.0 / shiboken6 6.12.0, CPython 3.14.7, Windows 11 x64). Sesuaikan hanya bila Anda mengubah nama berkas lampirannya | Teks yang masih berbunyi `<...>` akan terbaca sebagai laporan setengah jadi |
| 5 | **Lampirkan berkas** (bagian 2) sebagai **attachment**, jangan menempel kodenya di badan isu | Qt meminta reproducer berupa berkas; kode panjang di badan isu akan diminta dipindah |
| 6 | Tulis **dalam bahasa Inggris** | Aturan pelacak Qt |
| 7 | **Baca catatan reproduktifitas di bagian 3a** — cacat ini **tidak selalu muncul**, dan itu disebutkan di laporan supaya tidak terbaca sebagai janji | Laporan yang menjanjikan "selalu mati 7 dari 18" akan diminta dibuktikan ulang dan menghabiskan satu putaran triage |

**Component: PySide atau Shiboken?** Gejalanya muncul pada interaksi **pengumpulan sampah Python**
dengan utas Qt yang hidup (lihat `docs/riset-pyside6-gc-2026-10.md` bagian 2) — itu wilayah
*object lifetime* yang dekat ke Shiboken, tetapi yang dijalankan aplikasi adalah modul PySide dan
tidak ada galat Python yang bisa ditangkap. Saran: **pilih PySide**, lalu sebutkan di badan isu satu
kalimat bahwa kalau lebih tepat masuk Shiboken, silakan dipindahkan — triage mereka yang menentukan.

**Kalau ditanya "apakah masih terjadi di rilis terbaru?"** Jawaban yang benar sekarang: **belum
diuji di versi PySide6 lain** — dan itu **keputusan dependensi tersendiri** (K60 menyebut "uji
PySide6 lain" sebagai langkah berikutnya, dan K69 menyimpannya sebagai cabang yang **tidak** dipicu).
Yang **sudah** ada: A/B Python 3.13.14 (**0 dari 12** mati) melawan 3.14.7 (**2 dari 12**) — sebutkan
apa adanya, termasuk bahwa selisih itu **belum bermakna secara statistik**. Jangan menjawab "belum
diuji" tanpa menyebut bahwa versi yang dipin proyek ini adalah 6.12.0 dan mengapa.

---

## 2. Yang dilampirkan

| Lampiran | Berkas | Catatan |
|---|---|---|
| Reproducer (berkas uji yang di dalamnya prosesnya mati) | `tests/test_ui_jendela.py` | Frame kematian 19 Okt 2026 ada di berkas ini (`_tunggu` → `QThread.wait`). Ia membangun sendiri data ujinya, jadi **tidak** menuntut berkas data tambahan |
| **Sisa suite uji** (pemicu yang andal) | `tests/` selain berkas di atas + `requirements.txt` | Terukur: berkas uji itu **sendirian** 0 mati dari 24 jalan (8.5), sedangkan **suite penuh** 2 mati dari 12 jalan (bagian 10). Tanpa sisa suite, reproducer-nya tidak dipercaya |
| Penangkal yang dipakai sekarang | `mejasaham/ui/pekerja.py` | Berisi `tahan_gc_siklik()` (penahan berpenghitung) + komentar sebabnya — supaya pelapor tidak disarankan melakukan hal yang sudah dicoba |
| Inti jalur tunggu | `mejasaham/ui/jendela.py` | Fungsi `tunggu_pekerja()` — salah satu kerangka yang muncul di jejak |
| (opsional) paket minimal agar uji bisa dijalankan | `mejasaham/` tanpa `ui/`, atau zip repo | Uji mengimpor paket ini (`mejasaham`), jadi reproducer butuh paketnya; kalau mereka meminta yang lebih kecil, tawarkan zip berisi `mejasaham/` + `tests/` + `requirements.txt` |

**Batas yang harus disebut apa adanya di badan isu:** dua reproducer sintetis yang lebih kecil
(satu `QThread` + pohon widget + `gc.collect()` eksplisit; satu berbentuk jendela dengan tiga pekerja
dan jalur tunggu yang sama) **tidak** memicunya dalam 30 dan 48 putaran; berkas uji itu **sendirian**
juga tidak lagi memicunya (0 dari 24 jalan), dan yang memicu adalah **suite penuh** (2 dari 12).
Jadi lampiran yang ada adalah berkas uji yang benar-benar gagal **bersama suite-nya**, bukan
reproducer minimal — dan itu dikatakan, bukan disembunyikan.

---

## 3. Teks siap tempel (bahasa Inggris — tidak ada placeholder)

### 3a. Satu catatan yang harus Anda ketahui sebelum mengirim

Laporan di bagian 3 memuat **tiga pengukuran** yang berbeda, dan ketiganya disebut apa adanya:

1. **18 jalan berkas uji saja** (sesi 10, kode yang menambah alokasi di utas pekerja): **7 mati**.
2. **24 jalan berkas uji saja tanpa penangkal** (A/B 17 Okt 2026: 12 di CPython 3.14.7 + 12 di
   3.13.14): **0 mati** — jadi cacatnya bergantung waktu dan beban (`docs/riset-pyside6-gc-2026-10.md`
   bagian 8.5).
3. **12 jalan suite penuh tanpa penangkal di 3.14.7** (19 Okt 2026, K69): **2 mati**, dan 12 jalan
   yang sama di 3.13.14: **0 mati**. Reproduksi inilah yang membuat laporan ini punya **kontrol yang
   gagal** — persis yang diminta pelacak Qt. Rinciannya di bagian **10** dokumen riset itu.

Kalimat "Note on reproducibility" di teks bawah sudah memuat ketiganya, supaya pelacak tidak
membacanya sebagai janji "selalu mati 7 dari 18"; **jangan dihapus** — justru itu yang membuat
laporannya jujur dan menolong triage menentukan data apa yang mereka butuhkan. Kalimat "2 vs 0"
**tidak** diklaim sebagai bukti versi Python menyelesaikannya (p ≈ 0,48; dokumen riset bagian 10.4).

```text
Intermittent native crash (Fatal Python error: Aborted / access violation) in QThread.wait() while a Python-implemented QThread is running (PySide6 6.12.0, CPython 3.14.7, Windows)

ENVIRONMENT
Windows 11 x64; Python 3.14.7 (MSC v.1944 64 bit); PySide6 6.12.0 (PySide6-Essentials 6.12.0, shiboken6 6.12.0); Qt platform plugin "offscreen"; no Qt GUI session.

DESCRIPTION
In a test suite that repeatedly creates and drops QWidget trees while QThread subclasses with a Python run() are running, the process intermittently dies with "Fatal Python error: Aborted" or "Windows fatal exception: access violation", without any Python traceback. The main thread is always waiting for a worker thread to finish. Two shapes were observed:

  # 1. cooperative wait loop in the application window
  Current thread (main):
    File ".../jendela.py", line ..., in tunggu_pekerja      # QApplication.processEvents(); QThread.wait(50)
  Thread ... [worker]:
    File ".../test_ui_jendela.py", line ..., in tugas       # time.sleep()

  # 2. plain blocking wait in a test helper (most recent measurements)
  Current thread (main):
    File ".../tests/test_ui_jendela.py", line 195, in _tunggu      # QThread.wait(60_000)
    File ".../tests/test_ui_jendela.py", line 409, in test_hasil_lama_dibuang_saat_pemuatan_gagal
  Fatal Python error: Aborted
  (only the main thread was dumped; no worker-thread Python frame was printed)

REPRODUCTION
Attached: tests/test_ui_jendela.py (the file in whose frame the process dies) and the rest of the test suite it belongs to. On my machine the reliable trigger is the whole suite, run repeatedly, with QT_QPA_PLATFORM=offscreen:

  $env:QT_QPA_PLATFORM = "offscreen"
  foreach ($i in 1..12) { python -m pytest -q }

With the workaround disabled — in our tree a local pytest plugin (`-p <plugin>`) replaces the mitigation with a no-op, which also makes the mitigation's own guard tests fail; that is expected and is not what is being counted here.

19 Oct 2026, full suite, workaround disabled: 2 of 12 runs died (both "Fatal Python error: Aborted", exit code 3, after 70 s and 40 s), 10 of 12 passed. The same code and command on CPython 3.13.14 instead of 3.14.7: 0 of 12 died. With numbers this small the difference is not statistically meaningful (Fisher two-sided p = 0.48), so I am not claiming that the Python version fixes it.

Earlier measurements, single test file only: 7 of 18 runs died on the code without the workaround (17 Oct 2026); 0 of 18 died on the code from before the feature that added heavy Python allocation inside the worker thread; with gc.disable() for the whole run: 0 of 12 died; with the abandoned QWidget trees kept alive (so that the cyclic GC has nothing of ours to collect): 12 of 12 died — i.e. the crash correlates with cyclic garbage collection happening while a worker thread is alive, not with one particular object being freed. A later 24-run A/B on that single file (12 runs per interpreter, workaround disabled) produced no crash at all, which is why I recommend the full suite as the reproducer.

Limitation, stated plainly: two standalone minimal reproducers (a small QThread + widget tree + explicit gc.collect(), and a window-shaped one with three workers and the same wait loop) did NOT reproduce it in 30 and 48 rounds respectively. That is why the attachment is the real failing test file (with the rest of its suite) rather than a minimal script.

Note on reproducibility: the failure is timing- and load-dependent — 24 single-file runs without the workaround produced no crash, while 12 full-suite runs produced 2. I am reporting it because it is real, measurable and destructive, not because it triggers on every run.

WHAT I TRIED
1. gc.disable() during QThread.run(): reduces but does not remove it (1 of 8 full-suite runs, because gc.enable() is process-wide and a finishing worker re-enables it while another thread still relies on it being off).
2. A reference-counted "hold" used by both the worker body and the closing wait loop: 0 of 10 file runs and 0 of 8 full-suite runs — a workaround, not a fix.
3. The two minimal reproducers mentioned above.

EXPECTED
No process termination; at worst a Python exception that can be caught.

I can provide whatever diagnostic output would help (e.g. a shiboken debug build, faulthandler dumps with C stacks). If this belongs in the Shiboken component instead of PySide, please move it.
```

---

## 4. Rujukan langkah pengiriman

Langkah di bagian 1 diambil dari halaman resmi Qt untuk melaporkan bug Qt for Python:
[Qt for Python/Reporting Bugs](https://wiki.qt.io/Qt_for_Python/Reporting_Bugs) — pelacaknya
[bugreports.qt.io/browse/PYSIDE](https://bugreports.qt.io/browse/PYSIDE), dengan medan
Project/Type/Component dan kewajiban melampirkan reproducer sebagai berkas (bukan menempel kodenya
di badan isu). Halaman itu juga meminta pemeriksaan rilis terbaru lebih dulu — lihat catatan
"kalau ditanya" di bagian 1.

Setelah isunya terkirim, **catat tautannya** di `docs/riset-pyside6-gc-2026-10.md` (satu baris sudah
cukup) supaya T68 bisa dicabut kelak kalau jawabannya sudah ada, dan supaya langkah berikutnya punya
titik rujuk. Rencana yang dulu disebut di sini (**P38/K67**: uji Python 3.13) **sudah dijalankan**:
hasilnya "belum dapat disimpulkan" (bagian 8.5), lalu dilanjutkan **K69** — reproduksi ulang berhasil
dan A/B 3.13 dijalankan (bagian 10, 19 Okt 2026).
