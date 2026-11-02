# Publikasi GitHub

## Salinan yang dipublikasikan

Gunakan salinan khusus di `.tmp/publikasi-20261103/MejaSaham`, bukan repositori kerja asli.
Salinan dibuat dari daftar berkas Git yang dilacak beserta LICENSE, laporan audit, dan panduan ini,
mengambil isi working tree yang sudah dirapikan. `.git` lama, `.claude/`, berkas yang
diabaikan, basis data, `.venv/`, dan `.uji-data/` tidak disalin. Salinan memiliki satu
commit awal baru. Riwayat asli tetap lokal dan masih memuat email penulis lama;
jangan menambahkan atau menggabungkan riwayat itu ke repositori publik.

Identitas commit lokal salinan adalah `Kontributor MejaSaham <contributors@mejasaham.invalid>`.
Alamat `.invalid` adalah penanda nonpribadi, bukan akun GitHub terverifikasi.
Untuk atribusi akun GitHub pada commit berikutnya, ubah `git config user.name` dan
`git config user.email` di salinan menggunakan nama publik dan alamat noreply yang
ditampilkan GitHub pada Settings → Emails. Jangan memakai email pribadi bila ingin
menjaganya tetap privat.

## Berkas dan hak penggunaan

- LICENSE: MIT, dipilih pengguna pada 03 Nov 2026; pemegang hak ditulis sebagai
  Kontributor MejaSaham agar tidak memuat nama atau email pribadi.
- Lisensi kode tidak mencakup data atau dokumen pihak ketiga. Ketentuan sumber tetap berlaku.
  Rujukan: [MIT](https://opensource.org/license/mit) dan
  [yfinance](https://ranaroussi.github.io/yfinance/).
- Template bawaan dan dua draf PACK manual dengan rujukan KSEI tetap disertakan.
  Data harga/fundamental hasil unduhan, PDF sumber, arsip snapshot, konfigurasi aktif,
  transaksi, dan basis data kerja tidak disertakan.
- `.gitignore` mencegah penambahan biasa atas `.env`, private key, basis data, konfigurasi
  aktif, dan pengaturan mesin. `git add -f` dapat melewati aturan itu; tetap periksa staging.

## Cara mengunggah

Setelah meninjau salinan, buat repositori GitHub kosong tanpa README/license otomatis.
Dari PowerShell di folder salinan, periksa sebelum mengunggah:

```powershell
git status --short
git log --all --format="%h %an <%ae>"
git ls-files
# Ganti URL berikut dengan repositori milik sendiri.
git remote add origin https://github.com/AKUN/MejaSaham.git
git push -u origin main
```

Pembuatan repositori dan push tidak dijalankan oleh tahap persiapan ini. Jangan menjalankan
push dari folder kerja asli. Salinan adalah keadaan saat dibuat; perubahan berikutnya
di folder kerja asli tidak otomatis masuk ke salinan.

## Verifikasi

Uji aplikasi dari akar salinan dengan interpreter pengembangan yang sudah tersedia:
`..\..\..\.venv\Scripts\python -m pytest`. Untuk pemakaian mandiri, buat `.venv`
dan ikuti pemasangan pada README. Versi runtime dan pengembangan mengikuti constraint
`requirements.lock.txt`, termasuk perbaikan keamanan certifi dan setuptools.
Hasil audit dependensi beserta batasnya ada di
[laporan audit](audit-dependensi-2026-11-03.md). Pemindaian pola rahasia adalah pemeriksaan
awal; pemeriksaan pengaturan GitHub belum termasuk tahap ini.
