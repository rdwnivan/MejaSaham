# Audit kerentanan dependensi — 03 Nov 2026

## Status setelah perbaikan — 03 Nov 2026

Atas permintaan pengguna, certifi diperbarui ke **2026.10.19**, setuptools ke **84.1.0**,
dan dependensi pengembangan python-docx **1.2.0** dipasang serta ditambahkan ke lock.
`requirements.txt` kini memuat `-c requirements.lock.txt`; requirements pengembangan
mewarisi constraint tersebut, sehingga pytest, python-docx dan transitive memakai versi
terpin. Setuptools juga diminta eksplisit sebagai alat pengembangan agar versi yang
terpasang mengikuti perbaikannya. Paket lainnya tetap pada versi semula.

**Audit ulang lulus:** lock **32 paket** melalui PyPI dan OSV, serta lingkungan **44 paket**
melalui PyPI: semuanya exit **0**, `No known vulnerabilities found`, tanpa paket dilewati.
Seluruh 32 versi lock cocok dengan lingkungan. `pip check` bersih; ekstraksi PRD melalui
`tools/extract_docx.py` berhasil menghasilkan 700 baris dan 31 tabel di folder sementara.
Hasil suite akhir dan regenerasi publikasi dicatat pada `docs/lanjutan.md`.
Suite penuh di salinan publikasi memakai lingkungan yang sudah diperbaiki:
**1.125 tes lulus dalam 94,29 detik**. Root emSign ECC Root CA - G3 tidak ada dalam
trust store certifi baru; HTTPS ke PyPI lewat requests dan curl_cffi berhasil (HTTP 200)
dengan verifikasi TLS default. Salinan dan ZIP diregenerasi, 131 berkas dengan satu
commit nonpribadi. Belum ada push GitHub.
SHA-256 lock baru: `29721a8092bb59ada373d4f01367e676f69347792730248002add3d703e2afa4`.

Temuan awal di bawah dipertahankan sebagai jejak audit, bukan status versi saat ini.

Bukti sesudah perbaikan: `.tmp/perbaikan-dependensi-20261103/lock-pypi.json`,
`lock-osv.json`, `installed-pypi.json`, dan `installed.txt` dalam folder yang sama.
Perintah audit pada laporan ini dapat diulang atas lock yang telah diperbaiki.
Hash artefak belum ditambahkan ke lock; ini tetap batas integritas pemasangan.

## Hasil awal sebelum perbaikan

**Belum lulus audit keamanan dependensi: dua kerentanan unik pada dua paket.**
Pemindaian dengan pip-audit 2.10.1 melalui PyPI dan OSV menghasilkan temuan yang sama.
Keluaran mentah masing-masing menyebut `Found 3 known vulnerabilities in 2 packages`
dan exit code 1. Entri `PYSEC-2026-4320` untuk certifi muncul dua kali dengan ID/versi
identik; dihitung sekali, bukan dua masalah berbeda. Tidak ada paket yang dilewati scanner.

Tidak ada versi paket, requirements, kode aplikasi, atau data kerja yang diubah pada
tahap audit. Salinan publikasi dan ZIP yang disiapkan sebelumnya masih memakai versi
rentan yang sama. Tunda distribusi aplikasi siap pakai sampai perbaikan diuji.

## Cakupan dan bukti

- `requirements.lock.txt`: 31 paket, diperiksa melalui PyPI dan OSV.
- Lingkungan `.venv`: 43 paket, diperiksa melalui PyPI. Dua temuan yang sama, tanpa
  temuan tambahan pada sisa paket Qt/PyInstaller yang masih terpasang lokal.
- Rantai runtime dari metadata `Requires-Dist`, dengan marker lingkungan saat ini:
  24 paket termasuk yfinance. Seluruh versi cocok dengan lock; certifi termasuk runtime,
  setuptools tidak termasuk rantai runtime tersebut.
- `python-docx` tercantum tanpa pin dalam `requirements-dev.txt`, tetapi tidak ada
  di lock maupun lingkungan. Karena itu audit ini **belum menutup dependensi dev tersebut**.
  Metadata PyPI untuk versi 1.2.0 saat diperiksa tidak mencantumkan kerentanan; versi itu
  hanya kandidat untuk tahap perbaikan, belum dipasang atau diuji.
- SHA-256 lock yang diperiksa:
  `996485d1326f316e9f4a7235ba4123b30e7c04470db629863fd591a08f2d9a6a`.
- Bukti lokal: `.tmp/audit-dependensi-20261103/lock-pypi.json`, `lock-osv.json`,
  `installed-pypi.json`, `runtime-graph.json`, `summary.json`, dan inventaris `installed.txt`
  dalam folder yang sama. Bukti tidak memuat kredensial.

## Temuan 1 — certifi 2026.7.22, kritis

`PYSEC-2026-4320` / `GHSA-6q48-6c7w-9gw2`. Bundel CA memuat root emSign yang memiliki
intermediate dengan private key bocor. Penyerang yang memiliki key terkait dan berada
pada jalur jaringan dapat memalsukan sertifikat untuk menyadap/mengubah koneksi TLS yang
mempercayai bundel tersebut. Ini kondisi eksploitasi, bukan bukti proyek telah diserang.

Relevansi lokal: metadata yfinance mengharuskan `requests` dan `curl_cffi`; keduanya
mengharuskan certifi. `requests.certs.where() == certifi.where()` terbukti benar;
kode `curl_cffi/curl.py` juga memakai certifi sebagai fallback CA. Jalur data berpotensi
terpapar pada konfigurasi yang memakai bundel ini, walaupun server dasbor hanya loopback.
Pengambil berbasis `urllib.request` memakai trust store Python/sistem; tidak seluruh
koneksi aplikasi diasumsikan memakai certifi.

Rekomendasi: naikkan certifi ke **2026.10.19 atau lebih baru**, pin versi yang benar-benar
diuji, audit ulang dan regenerasi salinan publikasi. Perbaikan minimum scanner adalah
2026.10.18; advisory database merekomendasikan 2026.10.19 yang memulihkan root tidak terdampak.
Versi 2026.10.19 dikonfirmasi tersedia di PyPI, belum dipasang.

Sumber: [advisory pengelola certifi](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
dan [GitHub Advisory Database](https://github.com/advisories/GHSA-6q48-6c7w-9gw2).

## Temuan 2 — setuptools 84.0.0, rendah

`GHSA-xmj3-9gf7-h52w`. Di Windows, metadata namespace berbahaya dalam wheel dapat
memaksa jalur instalasi legacy `Wheel.install_as_egg()` membuat `__init__.py` dengan
isi tetap di luar direktori tujuan. Parent target harus sudah ada dan penyerang perlu
mengendalikan wheel. Advisory ini tidak membuktikan eksekusi kode jarak jauh.

Paket terpasang dan tercantum di lock, tetapi bukan dependensi runtime yfinance dari
graf metadata yang diperiksa. Risiko utama berada pada tooling/instalasi yang menggunakan
jalur legacy tersebut. Rekomendasi: naikkan ke **84.1.0 atau lebih baru** dan uji kembali.
Versi 84.1.0 dikonfirmasi tersedia di PyPI, belum dipasang.

Sumber: [advisory pengelola setuptools](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w).

## Temuan pengelolaan dependensi

`pytest` dan `python-docx` pada requirements pengembangan belum dipin; lock tidak memiliki
hash artefak. Hasil instalasi baru dari requirements biasa dapat berbeda dari versi yang
diaudit. Ini masalah reproduksibilitas/integritas, bukan tambahan kerentanan yang terkonfirmasi.
Pada tahap berikutnya, lengkapi dev lock termasuk python-docx, pin versi teruji, dan
pertimbangkan pemasangan berbasis lock dengan hash.

## Cara mengulang

Tool dijalankan terisolasi lewat uv; pip-audit tidak ditambahkan ke dependensi aplikasi.
Tidak memakai `--fix`, `--ignore-vuln`, atau mematikan TLS. Jalankan dari akar repositori:

```powershell
uv tool run --from pip-audit==2.10.1 pip-audit -r requirements.lock.txt --no-deps --disable-pip --strict --progress-spinner off -s pypi
uv tool run --from pip-audit==2.10.1 pip-audit -r requirements.lock.txt --no-deps --disable-pip --strict --progress-spinner off -s osv
.\.venv\Scripts\python -m pip check
.\.venv\Scripts\python -m pytest
```

`--no-deps --disable-pip` memeriksa daftar versi lock yang sudah di-resolve, tanpa
menjalankan resolver/instalasi paket target. Inventaris lingkungan ditulis dari
`importlib.metadata.distributions()` dan diaudit memakai opsi yang sama.
Dokumentasi alat: [pip-audit](https://pypi.org/project/pip-audit/).

## Batas kesimpulan

Temuan berdasarkan basis data saat pemeriksaan, bukan jaminan tidak ada kerentanan lain.
PyPI dan OSV dapat berbagi advisory; keduanya bukan dua penelitian independen.
Pustaka native yang dibundel (mis. libcurl/TLS), interpreter Python, sistem operasi,
jalur eksploitasi aplikasi menyeluruh, dan konfigurasi GitHub tidak diaudit terpisah.
`pip check` lulus (`No broken requirements found.`), tetapi itu hanya konsistensi metadata,
bukan hasil audit keamanan. Suite `.\.venv\Scripts\python -m pytest` lulus **1.125 tes dalam 144,12 detik**;
hasil ini tidak menghapus dua temuan keamanan. Ringkasan juga ada di `docs/lanjutan.md`.

Rekomendasi pada tahap audit awal (K4): perbaiki dua versi rentan dan kelengkapan dev lock,
jalankan ulang audit + tes, lalu perbarui salinan publikasi/ZIP. Status tindak lanjut ada
pada bagian atas laporan ini.
