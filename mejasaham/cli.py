"""Satu titik masuk: dasbor web lokal tanpa argumen (K91), mode kepala dengan argumen (AC-11).

Dua aturan yang dijaga berkas ini:

1. `mejasaham.web` diimpor **di dalam** cabang dasbor, bukan di puncak modul, supaya mode kepala
   (Task Scheduler) tidak memuat server HTTP yang tidak dipakainya.
2. Kegagalan selalu berisik (PRD 7.2, AC-9): pesan ke stderr + kode keluar bukan nol.
   Tidak ada `except: pass`.

Berkas ini juga tempat arti kode keluar ditetapkan, karena Task Scheduler (PRD 6.1) hanya
melihat kode keluar, bukan pesannya.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datetime import date

from mejasaham import tampilan

KODE_OK = 0
KODE_GAGAL = 1
KODE_BELUM_DITERAPKAN = 2


def baca_argumen(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="MejaSaham",
        description="Screener, penilaian, dan meja keputusan saham IDX.",
    )
    parser.add_argument("--refresh", action="store_true", help="segarkan data EOD dari sumber data")
    parser.add_argument(
        "--saring",
        action="store_true",
        help="jalankan saringan + skoring preset pada snapshot terakhir (F2/F3)",
    )
    parser.add_argument(
        "--preset",
        metavar="ID_PRESET",
        help="preset yang dipakai --saring (bawaan: versi terakhir preset 'kualitas-nilai')",
    )
    parser.add_argument(
        "--preset-bawaan",
        action="store_true",
        help="simpan/segarkan preset bawaan (dua ember K1) lalu laporkan daftarnya",
    )
    parser.add_argument(
        "--kode",
        metavar="KODE,KODE",
        help="batasi --saring ke kode tertentu (mis. BBCA,TLKM); bawaan: seluruh emiten",
    )
    parser.add_argument(
        "--teratas",
        metavar="N",
        type=int,
        default=None,
        help=(
            "berapa kandidat teratas yang dicetak --saring (bawaan 20) atau --dasbor "
            "(bawaan 5, supaya tetap satu halaman)"
        ),
    )
    parser.add_argument(
        "--sumber",
        metavar="LABEL",
        help=(
            "label sumber harga yang dipakai berhitung pada --saring (bawaan: label dengan "
            "riwayat bar terbanyak). Harga pembanding PRD 7.3 hidup di tabel yang sama, jadi "
            "tanpa satu label yang dipilih, dua sumber bercampur dalam satu deret (P17)"
        ),
    )
    parser.add_argument(
        "--muat-konfigurasi",
        action="store_true",
        help="muat parameter bursa dari TOML ke basis data, lalu laporkan keadaannya",
    )
    parser.add_argument(
        "--impor",
        metavar="FOLDER",
        type=Path,
        help="impor data dari berkas CSV di FOLDER (kalender bursa, notasi khusus, SUN, harga, dll.)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help=(
            "buka dasbor web lokal di http://127.0.0.1:PORT (K91); sama dengan menjalankan "
            "tanpa argumen. Hentikan dengan Ctrl+C"
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="port dasbor web (bawaan 8765); hanya dipakai bersama --web",
    )
    parser.add_argument(
        "--tanpa-peramban",
        action="store_true",
        help="--web tanpa membuka peramban secara otomatis",
    )
    parser.add_argument(
        "--folder-data",
        metavar="FOLDER",
        type=Path,
        help=(
            "folder data runtime; menimpa letak bawaan (LOCALAPPDATA). "
            "Berguna untuk mode portabel"
        ),
    )
    parser.add_argument(
        "--folder-cadangan",
        type=Path,
        help="lokasi cadangan di luar folder data (bawaan: folder saudara MejaSaham-cadangan)",
    )
    parser.add_argument(
        "--folder-pantau",
        metavar="FOLDER",
        type=Path,
        help=(
            "folder tempat Anda menyimpan unduhan IDX untuk --impor-unduhan (bawaan: variabel "
            "lingkungan MEJASAHAM_FOLDER_PANTAU; tidak diisi = fitur mati, K101)"
        ),
    )
    parser.add_argument(
        "--impor-unduhan",
        action="store_true",
        help=(
            "impor Ringkasan Saham, Notasi Khusus, dan PDF pengumuman IDX yang sudah Anda unduh ke "
            "folder pantau: cadangan dulu, berkas yang selesai dipindah ke unduhan-idx (K101)"
        ),
    )
    parser.add_argument(
        "--ingatkan",
        action="store_true",
        help=(
            "notifikasi Windows bila ada berkas IDX yang perlu diunduh menurut jadwal (K102); "
            "untuk Task Scheduler"
        ),
    )
    parser.add_argument(
        "--tanpa-notifikasi",
        action="store_true",
        help="--ingatkan hanya mencetak pengingatnya, tanpa notifikasi Windows",
    )
    parser.add_argument("--buat-cadangan", action="store_true", help="buat cadangan sekarang (F12)")
    parser.add_argument("--daftar-cadangan", action="store_true", help="tampilkan cadangan tersedia (F12)")
    parser.add_argument("--pulihkan", metavar="FOLDER_CADANGAN", type=Path, help="pulihkan data dari folder cadangan (F12)")
    parser.add_argument(
        "--sejak",
        metavar="YYYY-MM-DD",
        help="batasi pengambilan data mulai tanggal ini (bawaan: 5 tahun)",
    )
    parser.add_argument(
        "--emiten-awal",
        action="store_true",
        help=(
            "salin daftar emiten awal (~20 kode besar, BELUM diverifikasi) ke folder "
            "konfigurasi, supaya --refresh bisa dicoba sebelum daftar IDX Anda siap"
        ),
    )
    parser.add_argument(
        "--ambil-emiten",
        action="store_true",
        help=(
            "unduh daftar saham IDX dari Master File Efek KSEI (bulanan, resmi) dan tulis "
            "emiten.csv di folder konfigurasi; kolom sektor/papan/free float sengaja dikosongkan"
        ),
    )
    parser.add_argument(
        "--tanggal-master",
        metavar="YYYY-MM-DD",
        help=(
            "tanggal Master File Efek KSEI yang diambil (bawaan: berkas terbaru yang sudah "
            "terbit); tanggalnya menempel di nama berkas, mis. 2026-09-30"
        ),
    )
    parser.add_argument(
        "--timpa-emiten",
        action="store_true",
        help="izinkan --emiten-awal atau --ambil-emiten mengganti emiten.csv yang sudah ada",
    )
    parser.add_argument(
        "--ambil-kalender",
        action="store_true",
        help=(
            "unduh pengumuman hari libur & cuti bersama dari KSEI (yang menindaklanjuti kalender "
            "libur bursa IDX) dan tulis kalender-bursa.csv di folder konfigurasi; hari bursa "
            "diturunkan sebagai hari kerja dikurangi libur resmi"
        ),
    )
    parser.add_argument(
        "--tahun-kalender",
        metavar="YYYY",
        type=int,
        help=(
            "batasi --ambil-kalender ke satu tahun (bawaan: semua tahun yang pengumumannya masih "
            "dipasang di halaman KSEI)"
        ),
    )
    parser.add_argument(
        "--timpa-kalender",
        action="store_true",
        help="izinkan --ambil-kalender mengganti kalender-bursa.csv yang sudah ada",
    )
    parser.add_argument(
        "--ambil-sun",
        action="store_true",
        help=(
            "unduh kurva imbal hasil SBN dari halaman HPW PHEI dan tambahkan satu baris "
            "(SUN 10 tahun, tanggal menurut sumbernya) ke imbal-hasil-sun.csv di folder "
            "konfigurasi; baris lain di berkas itu tidak ditimpa"
        ),
    )
    parser.add_argument(
        "--ambil-fundamental",
        action="store_true",
        help=(
            "ambil laporan keuangan tahunan emiten dari sumber data EOD (TIDAK RESMI, K18) dan "
            "tulis fundamental.csv di folder konfigurasi; berkasnya diimpor lewat --impor. "
            "Bawaannya hanya semesta likuid (emiten yang lolos ambang ADTV20)"
        ),
    )
    parser.add_argument(
        "--semua-emiten",
        action="store_true",
        help="batasi --ambil-fundamental ke seluruh emiten, bukan hanya semesta likuid",
    )
    parser.add_argument(
        "--timpa-fundamental",
        action="store_true",
        help=(
            "izinkan --ambil-fundamental menulis ulang fundamental.csv yang sudah ada — "
            "suntingan tangan yang belum terimpor ikut hilang"
        ),
    )
    parser.add_argument(
        "--ambil-jenis",
        action="store_true",
        help=(
            "turunkan kolom `jenis` emiten dari sector/industry yang dinyatakan sumber data "
            "(hanya bank_keuangan yang diturunkan, K21) dan tulis emiten.csv di folder "
            "konfigurasi; berkasnya diimpor lewat --impor"
        ),
    )
    parser.add_argument(
        "--timpa-jenis",
        action="store_true",
        help=(
            "izinkan --ambil-jenis menulis ulang emiten.csv yang sudah ada — suntingan tangan "
            "yang belum terimpor ikut hilang"
        ),
    )
    parser.add_argument(
        "--kerangka-rasio-bank",
        action="store_true",
        help=(
            "tulis kerangka rasio-bank.csv dari daftar emiten ber-jenis bank_keuangan (K57): satu "
            "baris per kode, seluruh angka & tanggal dikosongkan, dan berkasnya TIDAK diimpor "
            "(baris berasio kosong memang ditolak pembacanya)"
        ),
    )
    parser.add_argument(
        "--ambil-notasi",
        action="store_true",
        help=(
            "unduh notasi khusus, status suspensi, dan UMA dari sumber resmi IDX di www.idx.id "
            "ke notasi-khusus.csv; berkasnya bertambah dan riwayat tetap tersimpan (P22)"
        ),
    )
    parser.add_argument(
        "--jeda",
        metavar="DETIK",
        type=float,
        default=None,
        help="jeda antar permintaan ke penyedia data (bawaan dari pengambil: 0,4 detik)",
    )
    parser.add_argument(
        "--cek-sumber-kedua",
        action="store_true",
        help=(
            "bandingkan penutupan 20 emiten ber-ADTV20 tertinggi terhadap sumber harga kedua "
            "(PRD 7.3); butuh harga pembanding yang sudah diimpor"
        ),
    )
    parser.add_argument(
        "--sumber-pembanding",
        metavar="LABEL",
        help=(
            "label sumber pembanding untuk --cek-sumber-kedua (bawaan: label sumber lain yang "
            "ada pada tanggal snapshot)"
        ),
    )
    # --- F4: kandidat & watchlist (PRD 9.6, Tahap 2) -------------------------------------
    parser.add_argument(
        "--kandidat-baru",
        metavar="KODE",
        help=(
            "buat entri kandidat untuk KODE (bawaan status 'ide'); status 'watchlist' menuntut "
            "--tesis, --pembatal, --horizon, --stop-awal, dan --tinjau (PRD 9.6, AC-4)"
        ),
    )
    parser.add_argument(
        "--kandidat-ubah",
        metavar="ID",
        type=int,
        help=(
            "ubah entri kandidat ID dengan menambah revisi (tidak menimpa): pakai --jadi untuk "
            "memindahkan status, --tesis/--pembatal/--horizon/--stop-awal/--tinjau untuk "
            "mengubah isi, --alasan bila dibuang"
        ),
    )
    parser.add_argument(
        "--watchlist",
        action="store_true",
        help="tampilkan entri kandidat pada revisi terakhirnya (urut dibuat)",
    )
    parser.add_argument(
        "--tinjau-ulang",
        metavar="ID",
        type=int,
        help=(
            "catat tinjauan entri ID: tanggal tinjau berikutnya diperbarui (bawaan hari ini + "
            "30 hari, bisa ditimpa --tinjau)"
        ),
    )
    parser.add_argument(
        "--status-tampil",
        metavar="STATUS",
        help="batasi --watchlist ke satu status: ide, watchlist, rencana, posisi, atau dibuang",
    )
    parser.add_argument("--tesis", metavar="TEKS", help="alasan masuk (wajib sebelum watchlist)")
    parser.add_argument(
        "--pembatal",
        metavar="TEKS",
        help="pembatal fundamental: kondisi terukur yang membatalkan tesis (wajib sebelum watchlist)",
    )
    parser.add_argument("--horizon", metavar="TEKS", help="horizon, mis. '1-6 bulan'")
    parser.add_argument("--target", metavar="RUPIAH", type=int, help="target harga (opsional)")
    parser.add_argument(
        "--stop-awal",
        metavar="RUPIAH",
        type=int,
        help="stop awal indikatif (wajib sebelum watchlist; dipakai kalkulator risiko)",
    )
    parser.add_argument(
        "--harga-pembatal",
        metavar="RUPIAH",
        type=int,
        help="level pembatal berbasis harga (opsional; bila diisi, dipakai dalam rumus stop, PRD 9.7)",
    )
    parser.add_argument(
        "--tinjau",
        metavar="YYYY-MM-DD",
        help="tanggal tinjau berikutnya (wajib sebelum watchlist; saran: hari ini + 30 hari)",
    )
    parser.add_argument(
        "--jadi",
        metavar="STATUS",
        help="status baru untuk --kandidat-ubah: ide → watchlist → rencana → posisi, atau dibuang",
    )
    parser.add_argument(
        "--alasan",
        metavar="TEKS",
        help=(
            "alasan pembuangan kandidat (wajib bila status 'dibuang'), alasan perubahan stop, atau "
            "alasan pada catatan jurnal (--jurnal-catat)"
        ),
    )
    # --- F5: kalkulator risiko & rencana (PRD 9.7, Tahap 2) ------------------------------
    parser.add_argument(
        "--batas-risiko-bawaan",
        action="store_true",
        help=(
            "simpan batas risiko awal PRD 9.7 (risiko per posisi, bobot per posisi, bobot per "
            "sektor, ukuran terhadap ADTV20, total risiko berjalan) sebagai preset berversi"
        ),
    )
    parser.add_argument(
        "--ekuitas-harian",
        metavar="RUPIAH",
        type=int,
        help=(
            "catat ekuitas portofolio hari ini (F11 dasar) — masukan kalkulator risiko. "
            "Dipakai bersama --kas bila kas tersedia ikut dicatat"
        ),
    )
    parser.add_argument(
        "--kas",
        metavar="RUPIAH",
        type=int,
        help=(
            "kas tersedia: untuk --ekuitas-harian berarti ikut dicatat; untuk --hitung-risiko "
            "berarti menimpa kas tercatat pada perhitungan itu saja"
        ),
    )
    parser.add_argument(
        "--ekuitas",
        metavar="RUPIAH",
        type=int,
        help=(
            "ekuitas yang dipakai untuk perhitungan ini saja (menimpa ekuitas harian); "
            "penimpanya dilaporkan di keluaran, dan tidak dicatat ke basis data"
        ),
    )
    parser.add_argument(
        "--tanggal-ekuitas",
        metavar="YYYY-MM-DD",
        help="tanggal ekuitas harian yang dicatat (bawaan: hari ini)",
    )
    parser.add_argument(
        "--hitung-risiko",
        metavar="KODE",
        help=(
            "hitung ukuran posisi menurut PRD 9.7 untuk KODE (kandidatnya harus berstatus "
            "watchlist); angka yang dipakai berasal dari snapshot terakhir dan parameter bertanggal"
        ),
    )
    parser.add_argument(
        "--harga-masuk",
        metavar="RUPIAH",
        type=int,
        help="harga masuk yang direncanakan (bawaan: penutupan terakhir, dibulatkan ke bawah ke tick sah)",
    )
    parser.add_argument(
        "--stop",
        metavar="RUPIAH",
        type=int,
        help=(
            "stop yang dipakai; bila tidak diisi, stop bawaan PRD 9.7 dipakai: nilai terbesar "
            "antara harga masuk − 2 × ATR14 dan harga pembatal tesis"
        ),
    )
    parser.add_argument(
        "--jenis-stop",
        metavar="JENIS",
        help="cara stop dieksekusi (Q9): order_sekuritas atau cek_penutupan — wajib saat menyimpan",
    )
    parser.add_argument(
        "--broker",
        metavar="NAMA",
        help="entri tarif broker yang dipakai bila di basis data terpasang lebih dari satu",
    )
    parser.add_argument(
        "--simpan-rencana",
        action="store_true",
        help="simpan hasil kalkulator sebagai rencana (menuntut --jenis-stop; PRD 9.7)",
    )
    parser.add_argument(
        "--rencana-revisi",
        metavar="ID",
        type=int,
        help="simpan sebagai revisi baru rencana ID, bukan sebagai rencana baru",
    )
    parser.add_argument(
        "--terima-pelanggaran",
        action="store_true",
        help=(
            "terima pelanggaran batas secara eksplisit supaya rencananya tetap bisa disimpan; "
            "tanpa ini, tawaran ukuran yang patuh yang harus dipilih (PRD 9.7)"
        ),
    )
    parser.add_argument(
        "--pakai-ukuran-patuh",
        action="store_true",
        help="pakai ukuran terbesar yang mematuhi seluruh batas (PRD 9.7: 'menawarkan ukuran yang patuh')",
    )
    parser.add_argument(
        "--rencana",
        action="store_true",
        help="tampilkan rencana tersimpan (revisi terakhir) beserta risiko berjalannya",
    )
    parser.add_argument(
        "--kandidat",
        metavar="ID",
        type=int,
        help="kandidat yang dipakai/ dituju kalkulator risiko (bila kodenya punya lebih dari satu entri)",
    )
    # --- F11: transaksi, posisi, ekuitas & dasbor (PRD 9.11, Tahap 2 langkah 3) -----------
    parser.add_argument(
        "--catat-transaksi",
        metavar="KODE",
        help=(
            "catat satu eksekusi manual (F11, PRD 9.1 langkah 9) dan perbarui posisinya; menuntut "
            "--aksi, --lembar, --harga, dan --mode"
        ),
    )
    parser.add_argument("--aksi", metavar="AKSI", help="beli atau jual (PRD 5: hanya posisi beli)")
    parser.add_argument("--lembar", metavar="LEMBAR", type=int, help="jumlah lembar yang dieksekusi")
    parser.add_argument("--harga", metavar="RUPIAH", type=int, help="harga eksekusi per lembar")
    parser.add_argument(
        "--mode",
        metavar="MODE",
        help=(
            "simulasi atau nyata (PRD 9.11). Wajib untuk transaksi: selama masa simulasi hanya "
            "data simulasi yang dipakai menilai preset, dan mode yang tidak dinyatakan membuat "
            "pemisahan itu mustahil"
        ),
    )
    parser.add_argument(
        "--biaya",
        metavar="RUPIAH",
        type=int,
        help=(
            "biaya transaksi seluruhnya; bila tidak diisi, dihitung dari tarif broker (B6/B7) dan "
            "asalnya ditandai. `--pajak` adalah BAGIAN dari angka ini, bukan tambahan"
        ),
    )
    parser.add_argument(
        "--pajak",
        metavar="RUPIAH",
        type=int,
        help="bagian biaya yang merupakan PPh final penjualan (bukan tambahan di atas --biaya)",
    )
    parser.add_argument(
        "--tanggal",
        metavar="YYYY-MM-DD",
        help="tanggal transaksi/stop (bawaan: hari ini). Transaksi satu posisi harus dicatat berurutan",
    )
    parser.add_argument(
        "--id-rencana",
        metavar="ID",
        type=int,
        help="rencana yang dieksekusi transaksi ini; tanpa itu, transaksinya dicatat sebagai pelanggaran V6",
    )
    parser.add_argument(
        "--id-posisi",
        metavar="ID",
        type=int,
        help="posisi yang dituju: untuk --catat-transaksi, atau posisi yang stopnya diubah",
    )
    parser.add_argument(
        "--posisi",
        action="store_true",
        help="tampilkan posisi aktif beserta risiko terbuka dan hasilnya (F11)",
    )
    parser.add_argument(
        "--posisi-semua",
        action="store_true",
        help="tampilkan seluruh posisi (termasuk yang sudah ditutup) beserta transaksinya",
    )
    parser.add_argument(
        "--ubah-stop",
        action="store_true",
        help=(
            "ubah stop terkini posisi --id-posisi menjadi --stop. Menaikkannya boleh (trailing); "
            "menurunkannya dicatat sebagai pelanggaran V5 (PRD 9.8, 9.11)"
        ),
    )
    parser.add_argument(
        "--arus-dana",
        metavar="RUPIAH",
        type=int,
        help=(
            "setoran (positif) atau penarikan (negatif) pada --ekuitas-harian. 0 berarti "
            "benar-benar tidak ada; tidak diisi berarti belum dicatat — dan drawdown terkoreksi "
            "tidak dapat dinilai (AC-13)"
        ),
    )
    parser.add_argument(
        "--drawdown",
        action="store_true",
        help="tampilkan deret ekuitas harian dan drawdown dari puncaknya (AC-13, PRD 8.2)",
    )
    parser.add_argument(
        "--dasbor",
        action="store_true",
        help=(
            "ringkasan harian satu halaman (PRD 11.1): keadaan data, watchlist, posisi, risiko "
            "berjalan, kandidat tersimpan, dan daftar tindakan menunggu (PRD 9.11, P16)"
        ),
    )
    # --- aksi korporasi pada posisi (PRD 9.11, Tahap 2 langkah 4) --------------------------
    parser.add_argument(
        "--hak-right-issue",
        action="store_true",
        help=(
            "tampilkan right issue yang menyentuh posisi: haknya (perkiraan dari rasio × lembar "
            "saat tanggal aksi), tenggatnya, dan keputusannya (PRD 9.11). Batasi dengan --kode"
        ),
    )
    parser.add_argument(
        "--putuskan-right-issue",
        metavar="KODE",
        help=(
            "catat keputusan manual atas satu right issue (PRD 9.11: tebus / jual HMETD / abaikan). "
            "Menuntut --tanggal-aksi dan --keputusan; `tebus` menuntut --id-transaksi"
        ),
    )
    parser.add_argument(
        "--tanggal-aksi",
        metavar="YYYY-MM-DD",
        help="tanggal aksi korporasi yang diputuskan (kolom `tanggal` pada aksi-korporasi.csv)",
    )
    parser.add_argument(
        "--keputusan",
        metavar="KEPUTUSAN",
        help="tebus | jual_hmetd | abaikan (PRD 9.11)",
    )
    parser.add_argument(
        "--id-transaksi",
        metavar="ID",
        type=int,
        help=(
            "transaksi pembelian yang mengeksekusi penebusan HMETD; wajib untuk keputusan "
            "`tebus`, sebab lembarnya hanya punya satu tempat — `transaksi`"
        ),
    )
    # --- jurnal & kepatuhan (PRD 9.8, 11.5, 13.1/13.2; Tahap 3 langkah 1) -------------------
    parser.add_argument(
        "--jurnal",
        action="store_true",
        help=(
            "tampilkan jurnal keputusan: satu baris per transaksi beserta pelanggaran V1–V7 dan "
            "catatan manusianya (PRD 9.8, 11.5). Batasi dengan --bulan/--kode/--mode"
        ),
    )
    parser.add_argument(
        "--rekap-kepatuhan",
        action="store_true",
        help=(
            "rekap kepatuhan PRD 9.8/13.1/13.2: jumlah keputusan, kepatuhan, pelanggaran per kode, "
            "kelengkapan tesis, expectancy dalam R, dan drawdown. Batasi dengan --bulan/--mode"
        ),
    )
    parser.add_argument(
        "--jurnal-catat",
        metavar="ID_TRANSAKSI",
        type=int,
        help=(
            "tulis/tambah catatan jurnal untuk satu transaksi: --alasan, --pelajaran, "
            "--tanggal-tinjau, --tandai-selesai. Menambah REVISI, tidak menimpa (PRD 9.8)"
        ),
    )
    parser.add_argument(
        "--pelajaran",
        metavar="TEKS",
        help="pelajaran dari satu keputusan, untuk catatan jurnal (PRD 11.5)",
    )
    parser.add_argument(
        "--tanggal-tinjau",
        metavar="YYYY-MM-DD",
        help="tanggal tinjau berikutnya untuk catatan jurnal (PRD 11.5)",
    )
    parser.add_argument(
        "--tandai-selesai",
        action="store_true",
        help="tandai catatan jurnal sudah ditinjau (PRD 11.5); tanggalnya diambil dari --tanggal",
    )
    parser.add_argument(
        "--ekspor",
        choices=("hasil-saring", "watchlist", "rencana", "jurnal", "mutu"),
        help="ekspor hasil saringan, watchlist, rencana, jurnal, atau mutu sebagai CSV (F9)",
    )
    parser.add_argument(
        "--keluaran",
        type=Path,
        help="jalur .csv tujuan untuk --ekspor; berkas yang sudah ada tidak ditimpa",
    )
    parser.add_argument(
        "--bulan",
        metavar="YYYY-MM",
        help="batasi --jurnal/--rekap-kepatuhan pada satu bulan (mis. 2026-10)",
    )
    return parser.parse_args(argv)


def _pakai_folder_data(folder: Path | None) -> None:
    """Arahkan letak data runtime sebelum apa pun menyentuh berkas (A3, mode portabel)."""
    if folder is None:
        return
    import os

    from mejasaham import lokasi

    os.environ[lokasi.ENV_FOLDER_DATA] = str(folder)


def _pakai_folder_cadangan(folder: Path | None) -> None:
    """Buat lokasi yang dipilih berlaku juga untuk cadangan otomatis sebelum migrasi."""
    if folder is None:
        return
    import os

    from mejasaham.cadangan import ENV_FOLDER_CADANGAN

    os.environ[ENV_FOLDER_CADANGAN] = str(folder)


def jalankan_refresh(argumen: argparse.Namespace) -> int:
    """Ambil data EOD, tulis snapshot, arsipkan (F1). Tanpa jendela, bisa dijadwalkan (AC-11)."""
    from datetime import date

    from mejasaham import db, ingesti, lokasi, pengambil, pengatur

    try:
        sampai = date.fromisoformat(argumen.sejak) if argumen.sejak else None
    except ValueError:
        print(f"MejaSaham: --sejak {argumen.sejak!r} bukan tanggal YYYY-MM-DD", file=sys.stderr)
        return KODE_GAGAL

    pengambil_data = pengambil.PengambilYFinance(
        mulai=sampai,
        jeda=pengambil.JEDA_BAWAAN if argumen.jeda is None else argumen.jeda,
        indeks=pengambil.INDEKS,
        laporan=_lapor_kemajuan,
    )

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        hasil = pengatur.jalankan_refresh(sambungan, pengambil_data)
    except ingesti.GalatIngesti as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    finally:
        sambungan.close()

    print(hasil.ringkas())
    if not hasil.sukses:
        print(f"MejaSaham: {hasil.pesan}", file=sys.stderr)
        return KODE_GAGAL
    try:
        from mejasaham import cadangan, pembaruan

        # Jalur yang sama dengan tombol "Perbarui data" di dasbor (K92): cadangan, lalu salinan
        # arsip ganda di cadangan lama ditautkan.
        hasil_cadangan, rapikan = pembaruan.cadangkan_dan_rapikan(tujuan=argumen.folder_cadangan)
        print(f"Cadangan F12: {hasil_cadangan}")
        print(f"Rapikan cadangan: {rapikan.ringkas()}")
    except (cadangan.GalatCadangan, db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: refresh berhasil, tetapi cadangan F12 gagal: {galat}", file=sys.stderr)
        return KODE_GAGAL
    _cetak_jadwal()
    return KODE_OK


def _cetak_jadwal() -> None:
    """Daftar periksa jadwal pembaruan (K93) sesudah refresh — memberi tahu, tidak menjalankan."""
    from mejasaham import db, jadwal

    sambungan = db.hubungkan()
    try:
        print()
        print(jadwal.ringkas(jadwal.susun(sambungan)))
    finally:
        sambungan.close()


def _lapor_kemajuan(kemajuan: object) -> None:
    """Cetak kemajuan per emiten; ingesti 800+ emiten tidak boleh terlihat menggantung.

    Satu baris per emiten ke stderr, **bukan** baris yang ditimpa dengan `\\r`: keluaran ini
    ikut tertangkap Task Scheduler dan log, dan keluaran yang saling menimpa akan membuat
    catatan kegagalan hilang dari pandangan (AC-9).
    """
    nomor = getattr(kemajuan, "nomor", 0)
    dari = getattr(kemajuan, "dari", 0)
    kode = getattr(kemajuan, "kode", "?")
    baris = getattr(kemajuan, "baris", 0)
    galat = getattr(kemajuan, "galat", None)
    tanda = f"GAGAL — {galat}" if galat else f"{baris} bar"
    print(f"  [{nomor}/{dari}] {kode:12s} {tanda}", file=sys.stderr, flush=True)


def jalankan_impor(folder: Path) -> int:
    """Impor berkas tanpa jaringan (PRD 7.1: kalender bursa, notasi khusus, SUN, rasio bank)."""
    from mejasaham import db, lokasi, pengatur

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    try:
        hasil = pengatur.jalankan_impor(sambungan, folder)
    finally:
        sambungan.close()

    print(hasil.ringkas())
    if not hasil.sukses:
        print(f"MejaSaham: {hasil.pesan}", file=sys.stderr)
        return KODE_GAGAL
    return KODE_OK


def jalankan_unduhan_idx(argumen: argparse.Namespace) -> int:
    """`--impor-unduhan` (K101) lalu `--ingatkan` (K102) — perintah tersendiri untuk Task Scheduler.

    Tidak digabung dengan perintah lain dalam satu panggilan: urutan hariannya penting
    (`--refresh` → `--impor-unduhan` → `--saring`, sebab Ringkasan Saham hanya diterima sampai
    tanggal snapshot terakhir dan saringan harus membaca snapshot sesudah impornya), dan urutan
    itu lebih jelas sebagai baris-baris terpisah daripada sebagai aturan tersembunyi di sini.
    """
    lain = [
        nama
        for nama, aktif in (
            ("--refresh", argumen.refresh),
            ("--saring", argumen.saring),
            ("--impor", argumen.impor is not None),
            ("--muat-konfigurasi", argumen.muat_konfigurasi),
        )
        if aktif
    ]
    if lain:
        print(
            f"MejaSaham: --impor-unduhan/--ingatkan dijalankan terpisah dari {', '.join(lain)}; "
            "urutan harian yang disarankan: --refresh, lalu --impor-unduhan, lalu --saring",
            file=sys.stderr,
        )
        return KODE_GAGAL
    if argumen.impor_unduhan:
        kode = jalankan_impor_unduhan(argumen)
        if kode != KODE_OK:
            return kode
    if argumen.ingatkan:
        return jalankan_ingatkan(argumen)
    return KODE_OK


def jalankan_impor_unduhan(argumen: argparse.Namespace) -> int:
    """Impor berkas IDX di folder pantau (K101), jalur yang sama dengan tombol dasbor."""
    from mejasaham import db, folder_pantau, lokasi
    from mejasaham.layar import tulis

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    def gagal_sebelum_impor(pesan: str) -> int:
        # Jalan dari Task Scheduler tidak punya penonton: kegagalan sebelum impor pun harus
        # sampai ke dasbor lewat `log_jalan` (AC-9), bukan hanya ke jendela yang lalu tertutup.
        print(f"MejaSaham: {pesan}", file=sys.stderr)
        try:
            folder_pantau.catat_jalan(sambungan, berhasil=False, pesan=pesan)
        except db.GalatBasisData as galat:
            print(f"MejaSaham: jejak kegagalan tidak tercatat di log_jalan: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        sasaran = folder_pantau.folder(argumen.folder_pantau)
        if sasaran is None:
            return gagal_sebelum_impor(
                "folder pantau belum diatur — isi --folder-pantau FOLDER atau variabel "
                f"lingkungan {folder_pantau.ENV_FOLDER_PANTAU} (K101)"
            )
        try:
            permintaan = tulis.permintaan_impor_folder_pantau(
                sambungan, folder=sasaran, tujuan_cadangan=argumen.folder_cadangan
            )
        except tulis.GalatTulis as galat:
            return gagal_sebelum_impor(str(galat))
        hasil = tulis.jalankan_permintaan(permintaan, sambungan)
    finally:
        sambungan.close()

    print(hasil.pesan)
    if not hasil.berhasil:
        print("MejaSaham: impor unduhan IDX tidak tuntas — lihat pesan di atas", file=sys.stderr)
        return KODE_GAGAL
    return KODE_OK


def jalankan_ingatkan(argumen: argparse.Namespace) -> int:
    """Cetak pengingat unduhan IDX dan tampilkan notifikasi Windows (K102)."""
    from mejasaham import db, lokasi, pengingat

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    try:
        daftar = pengingat.susun(sambungan)
    finally:
        sambungan.close()
    print(pengingat.ringkas(daftar))
    if argumen.tanpa_notifikasi:
        return KODE_OK
    try:
        pengingat.tampilkan(daftar)
    except pengingat.GalatPengingat as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    return KODE_OK


def jalankan_cek_sumber_kedua(argumen: argparse.Namespace) -> int:
    """Cek sumber kedua atas emiten ber-ADTV20 tertinggi (PRD 7.3), tanpa jendela.

    Selisih di atas ambang berarti dua sumber yang seharusnya melaporkan pasar yang sama tidak
    sepakat — itu sebabnya kode keluarnya bukan nol: pemeriksaan yang menemukan masalah tetapi
    keluar 0 akan terbaca sebagai lulus oleh Task Scheduler (AC-9, AC-11).

    Jalan ini juga yang **memenuhi** tuntutan mingguan PRD 7.3, jadi keadaannya (kapan terakhir
    lengkap, sampai kapan berlaku) ikut dicetak — pertanyaan "apakah saya masih patuh?" tidak
    boleh menuntut pengguna menghitung sendiri dari tanggal.
    """
    from mejasaham import db, ingesti, lokasi, mutu, pengatur

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        laporan = pengatur.cek_sumber_kedua(
            sambungan,
            sumber_utama=None,
            sumber_pembanding=argumen.sumber_pembanding,
        )
        # Dibaca **sesudah** pencatatan, sehingga yang tercetak adalah keadaan setelah cek ini.
        keadaan = mutu.keadaan_cek_sumber_kedua(sambungan)
    except ingesti.GalatIngesti as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    finally:
        sambungan.close()

    print(laporan.ringkas())
    print(f"  cadence: {keadaan.ringkas()}")
    if keadaan.berlaku_sampai:
        print(f"  cek berikutnya paling lambat: {keadaan.berlaku_sampai}")
    if laporan.ditandai:
        print(
            f"\nMejaSaham: {len(laporan.ditandai)} emiten berselisih lebih dari ambang antar "
            "sumber. Periksa mana yang benar sebelum angkanya dipakai (PRD 7.3).",
            file=sys.stderr,
        )
        return KODE_GAGAL
    if laporan.belum_dapat_dijalankan:
        print(
            "\nMejaSaham: pemeriksaan belum dapat dijalankan sepenuhnya — lihat alasannya di atas. "
            "Ini BUKAN berarti lulus.",
            file=sys.stderr,
        )
        return KODE_GAGAL
    return KODE_OK


def jalankan_emiten_awal(timpa: bool) -> int:
    """Salin daftar emiten awal (bootstrap) — bukan daftar resmi, dan dikatakan apa adanya."""
    from mejasaham import berkas, ingesti, lokasi

    try:
        tujuan = berkas.ambil_daftar_awal(lokasi.folder_konfigurasi(), timpa=timpa)
    except (ingesti.GalatIngesti, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    print(f"Daftar emiten awal disalin ke: {tujuan}")
    print(
        "\nPERINGATAN: daftar ini BUKAN daftar resmi dan TIDAK LENGKAP. Isinya hanya kode\n"
        "emiten besar yang umum dikenal, tanpa sektor/jenis/jumlah saham — kolom itu sengaja\n"
        "dikosongkan supaya tidak ada data bursa yang dikarang. Untuk pemakaian nyata, ganti\n"
        "isinya dengan daftar resmi dari idx.co.id (lihat mejasaham/defaults/emiten.contoh.csv)."
    )
    return KODE_OK


def jalankan_ambil_emiten(argumen: argparse.Namespace) -> int:
    """Ambil daftar saham IDX dari Master File Efek KSEI, tulis `emiten.csv` (tanpa jendela)."""
    from datetime import date

    from mejasaham import ingesti, ksei, lokasi

    try:
        tanggal = date.fromisoformat(argumen.tanggal_master) if argumen.tanggal_master else None
    except ValueError:
        print(
            f"MejaSaham: --tanggal-master {argumen.tanggal_master!r} bukan tanggal YYYY-MM-DD",
            file=sys.stderr,
        )
        return KODE_GAGAL

    try:
        hasil = ksei.ambil_emiten(
            lokasi.folder_konfigurasi(), tanggal=tanggal, timpa=argumen.timpa_emiten
        )
    except (ingesti.GalatIngesti, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    print(hasil)
    print(
        "\nLangkah berikutnya:\n"
        f'  python -m mejasaham --impor "{hasil.jalur.parent}"   # masukkan daftar ke basis data\n'
        "  python -m mejasaham --refresh                   # ambil harga (lama: ratusan emiten,\n"
        "                                                  #  ada jeda antar permintaan)"
    )
    return KODE_OK


def jalankan_ambil_kalender(argumen: argparse.Namespace) -> int:
    """Ambil hari libur bursa dari pengumuman KSEI, tulis `kalender-bursa.csv` (tanpa jendela)."""
    from mejasaham import ingesti, kalender, lokasi

    try:
        hasil = kalender.ambil_kalender(
            lokasi.folder_konfigurasi(),
            tahun=argumen.tahun_kalender,
            timpa=argumen.timpa_kalender,
        )
    except (ingesti.GalatIngesti, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    print(hasil)
    return KODE_OK


def jalankan_ambil_sun() -> int:
    """Ambil kurva imbal hasil SBN dari halaman HPW PHEI, tambahkan satu baris (tanpa jendela)."""
    from mejasaham import ingesti, lokasi, sun

    try:
        hasil = sun.ambil_sun(lokasi.folder_konfigurasi())
    except (ingesti.GalatIngesti, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    print(hasil)
    return KODE_OK


def jalankan_ambil_fundamental(argumen: argparse.Namespace) -> int:
    """Ambil laporan keuangan tahunan dari sumber tidak resmi, tulis `fundamental.csv` (K18).

    Fungsi ini **tidak** menulis basis data: ia menulis berkas rujukan yang bisa diperiksa dan
    disunting manusia lebih dulu, dan penulisan basis data tetap satu jalur (`--impor`) — pola
    yang sama dengan `--ambil-emiten`, `--ambil-kalender`, dan `--ambil-sun`.
    """
    from mejasaham import db, ingesti, lokasi, pengambil, pengatur, potret, saring

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        pengatur.siapkan_preset_bawaan(sambungan)
        if argumen.kode:
            kode = tuple(
                satu.strip().upper() for satu in argumen.kode.split(",") if satu.strip()
            )
        else:
            p = potret.muat(sambungan)
            if argumen.semua_emiten:
                kode = p.kode
            else:
                preset = saring.preset_terbaru(sambungan, "kualitas-nilai")
                kode = saring.semesta_likuid(p, preset)
                print(
                    f"Semesta likuid: {len(kode)} emiten (ambang ADTV20 preset "
                    f"'{preset.id_preset}'). Pakai --semua-emiten untuk seluruh emiten."
                )
    except (ingesti.GalatIngesti, db.GalatBasisData) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    finally:
        sambungan.close()

    if not kode:
        print("MejaSaham: tidak ada emiten yang bisa diambil.", file=sys.stderr)
        return KODE_GAGAL

    tujuan = lokasi.folder_konfigurasi() / "fundamental.csv"
    # Berkas template dari AC-12 tidak dihitung "berkas pengguna": ia belum memuat satu baris
    # data pun, jadi menulisnya bukan menimpa pekerjaan siapa pun.
    if tujuan.exists() and not argumen.timpa_fundamental and not pengambil.hanya_template(tujuan):
        print(
            f"MejaSaham: '{tujuan}' sudah ada. Berkas itu bisa saja sudah Anda sunting; "
            "pakai --timpa-fundamental bila memang ingin menulisnya ulang dari awal.",
            file=sys.stderr,
        )
        return KODE_GAGAL

    hari = date.today()
    baris: list[ingesti.Fundamental] = []
    tanpa_laporan: list[str] = []
    gagal: list[str] = []
    catatan: list[str] = []
    for urutan, satu in enumerate(kode, start=1):
        try:
            hasil = pengambil.fundamental_emiten(
                satu, diambil_pada=hari, jeda=argumen.jeda if argumen.jeda is not None else pengambil.JEDA_BAWAAN
            )
        except ingesti.GalatIngesti as keluhan:
            gagal.append(f"{satu}: {keluhan}")
            continue
        if hasil.gagal is not None:
            (tanpa_laporan if "tidak memuat laporan" in hasil.gagal else gagal).append(
                f"{satu}: {hasil.gagal}"
            )
            continue
        baris.extend(hasil.baris)
        catatan.extend(hasil.catatan)
        if urutan % 25 == 0:
            print(f"  ... {urutan}/{len(kode)} emiten, {len(baris)} baris")

    if not baris:
        print("MejaSaham: tidak ada satu pun laporan yang bisa dipakai.", file=sys.stderr)
        for satu in (tanpa_laporan + gagal)[:20]:
            print(f"  - {satu}", file=sys.stderr)
        return KODE_GAGAL

    lokasi.pastikan_folder(tujuan.parent)
    try:
        jumlah = pengambil.tulis_fundamental_csv(
            baris, tujuan, diambil_pada=hari, jumlah_emiten=len({s.kode for s in baris})
        )
    except OSError as galat:
        print(f"MejaSaham: gagal menulis '{tujuan}': {galat}", file=sys.stderr)
        return KODE_GAGAL

    print(
        f"\nFundamental ditulis: {jumlah} baris dari {len({s.kode for s in baris})} emiten "
        f"→ {tujuan}"
    )
    print(
        "  Sumber TIDAK RESMI (K7): labelnya ikut di setiap baris, dan tgl_publikasi diisi "
        "tanggal pengambilan dengan penanda asal_tgl_publikasi=tanggal_pengambilan."
    )
    print(f"  Impor ke basis data: python -m mejasaham --impor \"{tujuan.parent}\"")
    _cetak_daftar("Tanpa laporan di sumber", tanpa_laporan)
    _cetak_daftar("Gagal diambil", gagal)
    _cetak_daftar("Catatan pemetaan", catatan)
    return KODE_OK


def jalankan_ambil_jenis(argumen: argparse.Namespace) -> int:
    """Turunkan kolom `jenis` dari sector/industry sumber data, tulis `emiten.csv` (K21).

    Fungsi ini **tidak** menulis basis data: ia menulis berkas rujukan yang bisa diperiksa dan
    disunting manusia lebih dulu, dan penulisan basis data tetap satu jalur (`--impor`) — pola
    yang sama dengan `--ambil-emiten`, `--ambil-kalender`, `--ambil-fundamental`.

    Dasar turunannya adalah **revisi terakhir di basis data**, bukan `emiten.csv` yang ada:
    berkas itu bisa saja sudah disunting tangan dan belum diimpor, dan menyusun turunan di atas
    suntingan yang belum tercatat berarti menuliskan kembali sesuatu yang belum pernah terbukti
    terbaca. `jenis` yang sudah terisi dipertahankan (K21).
    """
    from mejasaham import db, ingesti, jenis, lokasi, pengambil

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        tersimpan = jenis.emiten_tersimpan(sambungan)
    except (ingesti.GalatIngesti, db.GalatBasisData, ValueError) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    finally:
        sambungan.close()

    if not tersimpan:
        print(
            "MejaSaham: tabel `emiten` masih kosong di basis data, jadi tidak ada yang bisa "
            "diturunkan. Impor daftar emitennya lebih dulu:\n"
            '  python -m mejasaham --ambil-emiten --folder-data <folder>\n'
            '  python -m mejasaham --impor "<folder>/konfigurasi"',
            file=sys.stderr,
        )
        return KODE_GAGAL

    tujuan = lokasi.folder_konfigurasi() / ingesti.NAMA_BERKAS_EMITEN
    # Berkas template dari AC-12 tidak dihitung "berkas pengguna": ia belum memuat satu baris
    # data pun, jadi menulisnya bukan menimpa pekerjaan siapa pun (pola yang sama dengan
    # --ambil-emiten dan --ambil-fundamental).
    if tujuan.exists() and not argumen.timpa_jenis and not pengambil.hanya_template(tujuan):
        print(
            f"MejaSaham: '{tujuan}' sudah ada dan sudah berisi. Berkas itu bisa saja sudah Anda "
            "sunting (sektor, jenis, papan); pakai --timpa-jenis bila memang ingin menulisnya "
            "ulang dari turunan data.",
            file=sys.stderr,
        )
        return KODE_GAGAL

    sudah_terisi = [satu for satu in tersimpan if (satu.jenis or "").strip()]
    perlu_diturunkan = [satu for satu in tersimpan if not (satu.jenis or "").strip()]
    print(
        f"Emiten di basis data: {len(tersimpan)} · sudah ber-jenis (dipertahankan): "
        f"{len(sudah_terisi)} · akan diturunkan: {len(perlu_diturunkan)}"
    )

    hasil_sector: dict[str, pengambil.HasilSector] = {}
    gagal: list[str] = []
    for urutan, satu in enumerate(perlu_diturunkan, start=1):
        try:
            jawaban = pengambil.sector_emiten(
                satu.kode,
                jeda=argumen.jeda if argumen.jeda is not None else pengambil.JEDA_BAWAAN,
            )
        except ingesti.GalatIngesti as keluhan:
            gagal.append(f"{satu.kode}: {keluhan}")
            continue
        if jawaban.gagal is not None:
            gagal.append(f"{satu.kode}: {jawaban.gagal}")
            continue
        hasil_sector[satu.kode] = jawaban
        if urutan % 25 == 0:
            print(f"  ... {urutan}/{len(perlu_diturunkan)} emiten")

    baris: list[jenis.BarisJenis] = []
    tanpa_jenis: list[str] = []
    for satu in tersimpan:
        jawaban = hasil_sector.get(satu.kode)
        if (satu.jenis or "").strip():
            # Dipertahankan apa adanya; sector/industry tetap dibawa bila kebetulan terambil,
            # supaya keterangan turunannya jujur tentang apa yang diketahui.
            baris.append(
                jenis.BarisJenis(
                    tersimpan=satu,
                    sector=jawaban.sector if jawaban else None,
                    industry=jawaban.industry if jawaban else None,
                    jenis=satu.jenis,
                )
            )
            continue
        diturunkan = (
            jenis.jenis_dari_sumber(jawaban.sector, jawaban.industry) if jawaban is not None else None
        )
        if diturunkan is None:
            tanpa_jenis.append(satu.kode)
        baris.append(
            jenis.BarisJenis(
                tersimpan=satu,
                sector=jawaban.sector if jawaban else None,
                industry=jawaban.industry if jawaban else None,
                jenis=diturunkan,
            )
        )

    hari = date.today()
    lokasi.pastikan_folder(tujuan.parent)
    try:
        ringkasan = jenis.tulis_emiten_csv(baris, tujuan, diambil_pada=hari)
    except OSError as galat:
        print(f"MejaSaham: gagal menulis '{tujuan}': {galat}", file=sys.stderr)
        return KODE_GAGAL

    # Bukti, bukan klaim: berkasnya dibaca ulang oleh pembaca yang sama dengan yang dipakai
    # --impor. Kalau bentuknya tidak terbaca, lebih baik gagal di sini daripada setelah impor.
    from mejasaham import berkas as pembaca

    try:
        terbaca = pembaca.baca_emiten(tujuan.parent)
    except ingesti.GalatIngesti as galat:
        print(f"MejaSaham: '{tujuan}' ditulis tetapi tidak terbaca ulang — {galat}", file=sys.stderr)
        return KODE_GAGAL
    if len(terbaca) != ringkasan.jumlah_baris:
        print(
            f"MejaSaham: '{tujuan}' ditulis {ringkasan.jumlah_baris} baris tetapi terbaca ulang "
            f"{len(terbaca)} baris. Berkasnya tidak boleh dipakai sebelum diperiksa.",
            file=sys.stderr,
        )
        return KODE_GAGAL
    bank_terbaca = sorted(satu.kode for satu in terbaca if satu.jenis == "bank_keuangan")

    print(
        f"\nemiten.csv ditulis: {ringkasan.jumlah_baris} baris → {tujuan}\n"
        f"  bank_keuangan {ringkasan.bank_keuangan} · umum {ringkasan.umum} · "
        f"jenis tetap kosong {ringkasan.kosong}"
    )
    print(
        "  Hanya bank_keuangan yang diturunkan; siklikal_komoditas TIDAK PERNAH diturunkan "
        "(itu penilaian, bukan fakta sumber). Label sector/industry mentahnya ikut di kolom "
        "`sumber` tiap baris (K21)."
    )
    print(
        f"  Terbaca ulang oleh pembaca impor: {len(terbaca)} baris, "
        f"{len(bank_terbaca)} di antaranya bank_keuangan."
    )
    if bank_terbaca:
        contoh = ", ".join(bank_terbaca[:12])
        print(f"  Kode bank yang dikenal: {contoh}{' …' if len(bank_terbaca) > 12 else ''}")
    print(f"\n  Impor ke basis data: python -m mejasaham --impor \"{tujuan.parent}\"")
    _cetak_daftar("Sumber tidak menyatakan sector/industry (jenis dibiarkan kosong)", tanpa_jenis)
    _cetak_daftar("Gagal diambil", gagal)
    return KODE_OK


def jalankan_kerangka_rasio_bank(argumen: argparse.Namespace) -> int:
    """Tulis kerangka `rasio-bank.csv` dari daftar emiten ber-jenis bank (K57, T67).

    Dua hal yang **tidak** dilakukan perintah ini, dan keduanya disengaja: mengisi angka rasio
    (tidak ada sumber otomatisnya — jalur PDF sengaja tidak dibangun, K24) dan mengimpornya
    (baris yang seluruh rasionya kosong memang ditolak pembacanya, sehingga kerangka kosong gagal
    berisik alih-alih masuk sebagai nol — aturan keras 2).

    Berkas tujuan yang **sudah ada** ditolak kecuali ia masih template bawaan: berkas itu diisi
    manusia dari publikasi resmi, dan menimpanya berarti menghapus pekerjaan yang tidak bisa
    dibuat ulang aplikasi.
    """
    from mejasaham import berkas, db, jenis, lokasi, pengambil

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        try:
            bank = jenis.kode_bank(sambungan)
        except (db.GalatBasisData, ValueError) as galat:
            print(f"MejaSaham: {galat}", file=sys.stderr)
            return KODE_GAGAL
    finally:
        sambungan.close()

    if not bank:
        print(
            "MejaSaham: tidak ada emiten ber-jenis `bank_keuangan` di basis data, jadi tidak ada "
            "yang bisa didaftar. Kolom `jenis` diisi lebih dulu (hanya `bank_keuangan` yang bisa "
            "diturunkan dari data, K21):\n"
            '  python -m mejasaham --ambil-jenis --timpa-jenis --folder-data <folder>\n'
            '  python -m mejasaham --impor "<folder>/konfigurasi" --folder-data <folder>\n'
            "Kalau daftar emitennya sendiri belum ada: --ambil-emiten lebih dulu.",
            file=sys.stderr,
        )
        return KODE_GAGAL

    tujuan = lokasi.folder_konfigurasi() / berkas.NAMA_RASIO_BANK
    if tujuan.exists() and not pengambil.hanya_template(tujuan):
        print(
            f"MejaSaham: '{tujuan}' sudah ada dan sudah berisi. Berkas ini diisi manusia dari "
            "publikasi resmi bank, jadi ia tidak ditimpa diam-diam: pindahkan atau ganti namanya "
            "lebih dulu kalau memang ingin membuat kerangka baru.",
            file=sys.stderr,
        )
        return KODE_GAGAL

    lokasi.pastikan_folder(tujuan.parent)
    try:
        ringkasan = jenis.tulis_kerangka_rasio_bank(bank, tujuan, ditulis_pada=date.today())
    except OSError as galat:
        print(f"MejaSaham: gagal menulis '{tujuan}': {galat}", file=sys.stderr)
        return KODE_GAGAL

    print(
        f"\nKerangka rasio-bank.csv ditulis: {len(ringkasan.kode)} baris → {tujuan}\n"
        "  Seluruh angka & tanggal DIKOSONGKAN dengan sengaja: aplikasi tidak punya sumber "
        "otomatisnya (K24), dan angka tebakan di sini akan membuat bank tampak sehat tanpa dasar."
    )
    contoh = ", ".join(ringkasan.kode[:12])
    print(f"  Kode bank: {contoh}{' …' if len(ringkasan.kode) > 12 else ''}")
    print(
        "  Isi dari publikasi resmi bank/OJK — minimal satu rasio per baris, persen dengan titik "
        "desimal (mis. 2.35) — lalu:\n"
        f'    python -m mejasaham --impor "{tujuan.parent}" --folder-data <folder data>\n'
        "  Kerangka yang belum diisi akan DITOLAK pembacanya (bukan masuk sebagai nol)."
    )
    return KODE_OK


def _cetak_daftar(judul: str, isi: list[str], batas: int = 15) -> None:
    """Cetak daftar kegagalan/catatan apa adanya — dibatasi supaya keluaran tetap terbaca.

    Gagal itu berisik (aturan keras 7): yang tidak muat **disebut jumlahnya**, bukan dihilangkan.
    """
    if not isi:
        return
    print(f"  {judul}: {len(isi)}")
    for satu in isi[:batas]:
        print(f"    - {satu}")
    if len(isi) > batas:
        print(f"    ... dan {len(isi) - batas} lainnya")


def jalankan_kandidat(argumen: argparse.Namespace) -> int:
    """Kandidat & watchlist (F4, PRD 9.6) — tesis wajib sebelum berstatus watchlist (AC-4).

    Perintahnya sengaja kecil dan eksplisit: entri yang **belum** lengkap tetap bisa dicatat
    sebagai `ide`, dan hanya perpindahan ke `watchlist` yang menuntut kolom wajib. Itulah
    maksud AC-4 — bukan melarang mencatat ide, melainkan melarang ide menyamar sebagai keputusan.
    """
    from mejasaham import db, kandidat, lokasi

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    hanya_tampil = not (
        argumen.kandidat_baru or argumen.kandidat_ubah is not None or argumen.tinjau_ulang is not None
    )
    status_tampil = argumen.status_tampil
    if status_tampil and status_tampil not in kandidat.STATUS_SAH:
        print(
            f"MejaSaham: status {status_tampil!r} tidak dikenal. Yang sah: "
            f"{', '.join(kandidat.STATUS_SAH)}",
            file=sys.stderr,
        )
        sambungan.close()
        return KODE_GAGAL

    try:
        try:
            if argumen.kandidat_baru:
                baru = kandidat.buat(
                    sambungan,
                    argumen.kandidat_baru,
                    status=argumen.jadi or "ide",
                    tesis=argumen.tesis,
                    pembatal_fundamental=argumen.pembatal,
                    harga_pembatal=argumen.harga_pembatal,
                    horizon=argumen.horizon,
                    target=argumen.target,
                    stop_awal=argumen.stop_awal,
                    tanggal_tinjau=argumen.tinjau,
                )
                print(f"Kandidat dibuat: #{baru.id_kandidat} {baru.kode} (status {baru.status})")
                if baru.status == "ide":
                    print(
                        "  Status 'ide' belum boleh masuk watchlist. Untuk memindahkannya, isi "
                        "kolom wajibnya (PRD 9.6, AC-4):"
                    )
                    print(
                        f"    python -m mejasaham --kandidat-ubah {baru.id_kandidat} --jadi watchlist "
                        f"--tesis \"...\" --pembatal \"...\" --horizon \"1-6 bulan\" "
                        f"--stop-awal <harga> --tinjau {kandidat.saran_tanggal_tinjau()}"
                    )

            elif argumen.kandidat_ubah is not None:
                perubahan: dict[str, object] = {}
                if argumen.jadi:
                    perubahan["status"] = argumen.jadi
                if argumen.tesis is not None:
                    perubahan["tesis"] = argumen.tesis
                if argumen.pembatal is not None:
                    perubahan["pembatal_fundamental"] = argumen.pembatal
                if argumen.horizon is not None:
                    perubahan["horizon"] = argumen.horizon
                if argumen.target is not None:
                    perubahan["target"] = argumen.target
                if argumen.stop_awal is not None:
                    perubahan["stop_awal"] = argumen.stop_awal
                if argumen.harga_pembatal is not None:
                    perubahan["harga_pembatal"] = argumen.harga_pembatal
                if argumen.tinjau is not None:
                    perubahan["tanggal_tinjau"] = argumen.tinjau
                if argumen.alasan is not None:
                    perubahan["alasan_dibuang"] = argumen.alasan
                hasil = kandidat.ubah(sambungan, argumen.kandidat_ubah, perubahan)
                print(
                    f"Kandidat #{hasil.id_kandidat} {hasil.kode}: status {hasil.status}, "
                    f"revisi {hasil.revisi} (revisi lama tetap tersimpan)"
                )

            elif argumen.tinjau_ulang is not None:
                hasil = kandidat.tinjau(sambungan, argumen.tinjau_ulang, argumen.tinjau)
                print(
                    f"Kandidat #{hasil.id_kandidat} {hasil.kode}: tinjauan dicatat, "
                    f"tanggal tinjau berikutnya {hasil.tanggal_tinjau}"
                )
        except (kandidat.GalatKandidat, db.GalatBasisData) as galat:
            print(f"MejaSaham: {galat}", file=sys.stderr)
            return KODE_GAGAL

        if hanya_tampil or argumen.watchlist:
            semua = kandidat.daftar(sambungan, status_tampil)
            if status_tampil:
                print(f"\nEntri berstatus {status_tampil}: {len(semua)}")
            else:
                hitung: dict[str, int] = {}
                for satu in semua:
                    hitung[satu.status] = hitung.get(satu.status, 0) + 1
                rincian = ", ".join(f"{nama} {hitung[nama]}" for nama in kandidat.STATUS_SAH if nama in hitung)
                print(f"\nEntri kandidat (revisi terakhir): {len(semua)}" + (f" — {rincian}" if rincian else ""))
            print(kandidat.ringkas_daftar(semua))
            if not semua:
                print(
                    "  Mulai dari hasil saringan: --saring, lalu --kandidat-baru KODE. "
                    "Ingat: hasil saringan bukan status (PRD 9.6)."
                )
    finally:
        sambungan.close()
    return KODE_OK


def _cari_kandidat_rencana(
    sambungan: object, kode: str, id_kandidat: int | None
) -> object:
    """Kandidat yang mendasari sebuah rencana.

    Aturannya tinggal di `kandidat.untuk_rencana` — **bukan** di sini — sebab panel jendela
    (PRD 11.4) memakai kalkulator yang sama; dua salinan aturan akan berbeda begitu salah
    satunya disunting, dan yang berbeda adalah tesis mana yang menempel pada sebuah posisi.
    """
    from mejasaham import kandidat

    return kandidat.untuk_rencana(sambungan, kode, id_kandidat)  # type: ignore[arg-type]


def _cetak_hasil_risiko(hasil: object, masukan: object) -> None:
    """Keluaran kalkulator (PRD 9.7), angka apa adanya dengan pemisah ribuan Indonesia.

    Teksnya **tidak** disusun di sini: `risiko.ringkas_hasil` yang menyusunnya, supaya panel
    jendela (PRD 11.4) menampilkan angka yang sama persis — bukan salinan yang bisa berbeda.
    """
    from mejasaham import risiko

    assert isinstance(hasil, risiko.HasilRisiko)
    assert isinstance(masukan, risiko.MasukanRisiko)
    print(risiko.ringkas_hasil(hasil, masukan))


def _tampilkan_rencana_tersimpan(sambungan: object, kode: str | None) -> int:
    from mejasaham import risiko, tampilan

    isi = risiko.daftar(sambungan, kode=kode)  # type: ignore[arg-type]
    print(f"Rencana tersimpan (revisi terakhir): {len(isi)}")
    print(risiko.ringkas_daftar(isi))
    if isi:
        lengkap = risiko.risiko_berjalan_lengkap(sambungan)  # type: ignore[arg-type]
        print(
            f"\nRisiko berjalan (PRD 8.2): {tampilan.rupiah(lengkap.total)} = posisi aktif "
            f"{tampilan.rupiah(lengkap.dari_posisi)} ({lengkap.jumlah_posisi_dinilai}/"
            f"{lengkap.jumlah_posisi_aktif} dinilai) + rencana belum dieksekusi "
            f"{tampilan.rupiah(lengkap.dari_rencana)} ({lengkap.jumlah_rencana_belum} rencana)"
        )
        for satu in lengkap.rincian:
            print(f"  - {satu}")
        for satu in lengkap.tidak_dinilai:
            print(f"  TIDAK DINILAI: {satu}")
        if lengkap.tidak_dinilai:
            print(
                "  Catatan: suku yang TIDAK DINILAI tidak dijumlahkan sebagai nol, sehingga "
                "jumlah di atas lebih kecil daripada risiko yang sebenarnya."
            )
        print(
            "  Catatan: rencana yang sudah punya transaksi tidak dijumlahkan lagi — risikonya "
            "sudah hidup di posisinya (--posisi)."
        )
    return KODE_OK


def jalankan_risiko(argumen: argparse.Namespace) -> int:
    """Kalkulator risiko & rencana (F5, PRD 9.7) — mode kepala, tanpa jendela (AC-11)."""
    from mejasaham import db, ingesti, kandidat, konfigurasi, lokasi, risiko

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        try:
            if argumen.batas_risiko_bawaan:
                preset = risiko.batas_bawaan()
                baru = risiko.simpan_preset(sambungan, preset)
                print(
                    f"Batas risiko {preset.id_preset_risiko}: "
                    f"{'disimpan' if baru else 'sudah ada dan sama (tidak ditulis ulang)'}"
                )
                for nama in risiko.NAMA_BATAS:
                    print(f"  {risiko.SEBUTAN_BATAS[nama]:34s} {preset.ringkas(nama)}")
                print(f"  keterangan: {preset.keterangan}")
                return KODE_OK

            if argumen.ekuitas_harian is not None:
                tanggal = risiko.catat_ekuitas(
                    sambungan,
                    ekuitas=argumen.ekuitas_harian,
                    kas=argumen.kas,
                    arus_dana=argumen.arus_dana,
                    mode=argumen.mode,
                    tanggal=argumen.tanggal_ekuitas,
                    sumber="dicatat pengguna lewat --ekuitas-harian",
                )
                print(
                    f"Ekuitas harian {tanggal}: {argumen.ekuitas_harian}"
                    + ("  kas: (tidak dicatat)" if argumen.kas is None else f"  kas: {argumen.kas}")
                    + (
                        "  arus dana: (belum dicatat)"
                        if argumen.arus_dana is None
                        else f"  arus dana: {argumen.arus_dana}"
                    )
                    + ("" if argumen.mode is None else f"  mode: {argumen.mode}")
                )
                if argumen.kas is None:
                    print(
                        "  Kas tidak dicatat: batas kas pada kalkulator risiko akan berstatus "
                        "'tidak dinilai' — bukan dianggap kosong, dan bukan dianggap longgar."
                    )
                if argumen.arus_dana is None:
                    print(
                        "  Arus dana tidak dicatat: drawdown TIDAK dapat dikoreksi terhadap "
                        "setoran/penarikan (AC-13). Isi --arus-dana (0 = memang tidak ada) bila "
                        "memang tidak ada setoran/penarikan hari itu."
                    )
                if argumen.drawdown:
                    print()
                    return _cetak_drawdown(sambungan)
                return KODE_OK

            if argumen.hitung_risiko is None:
                return _tampilkan_rencana_tersimpan(sambungan, None)

            kode = argumen.hitung_risiko.strip().upper()
            entri = _cari_kandidat_rencana(sambungan, kode, argumen.kandidat)
            masukan = risiko.siapkan_masukan(
                sambungan,
                kode,
                ekuitas_penimpa=argumen.ekuitas,
                kas_penimpa=argumen.kas,
                harga_acuan=argumen.harga_masuk,
                broker=argumen.broker,
            )
            if argumen.harga_masuk is None and masukan.harga_terakhir.ada:
                print(
                    f"Harga masuk tidak diisi: dipakai penutupan terakhir "
                    f"{masukan.harga_terakhir.nilai:.2f} dibulatkan ke bawah ke tick sah "
                    f"{masukan.harga_acuan} (PRD 10)"
                )
            hasil, _stop = risiko.hitung_untuk(
                masukan,
                harga_masuk=masukan.harga_acuan,
                stop_penimpa=argumen.stop,
                harga_pembatal=entri.harga_pembatal,
                jenis_stop=argumen.jenis_stop,
            )
            if (
                argumen.stop is None
                and entri.stop_awal is not None
                and entri.stop_awal != hasil.stop
            ):
                print(
                    f"Catatan: stop awal di tesis kandidat #{entri.id_kandidat} adalah "
                    f"{entri.stop_awal}, sedangkan stop yang dipakai kalkulator {hasil.stop} "
                    "(PRD 9.7: nilai terbesar antara harga masuk − 2 × ATR14 dan harga pembatal "
                    "tesis). Pilih salah satunya dengan --stop bila tesisnya yang berlaku."
                )
            if argumen.pakai_ukuran_patuh:
                sebelum = hasil.lembar
                # Jalurnya tinggal di `risiko` supaya layar 11.4 (K63) memakai perhitungan yang
                # sama persis — bukan salinan yang bisa berbeda begitu batasnya berubah.
                hasil = risiko.pakai_ukuran_patuh(hasil, masukan)
                print(
                    f"Ukuran patuh dipakai: {sebelum} -> {hasil.lembar} lembar "
                    f"({hasil.lembar // masukan.lot} lot)"
                )
            _cetak_hasil_risiko(hasil, masukan)

            if not argumen.simpan_rencana:
                print(
                    "\nRencana belum disimpan. Tambahkan --simpan-rencana --jenis-stop "
                    f"{{{', '.join(risiko.JENIS_STOP_SAH)}}} untuk menyimpannya (PRD 9.7)."
                )
                return KODE_OK

            if argumen.jenis_stop is None:
                print(
                    "MejaSaham: --simpan-rencana menuntut --jenis-stop "
                    f"({' atau '.join(risiko.JENIS_STOP_SAH)}) — Q9 menetapkan cara stop "
                    "dieksekusi dicatat per rencana.",
                    file=sys.stderr,
                )
                return KODE_GAGAL
            # Aturan status + perpindahan watchlist -> rencana tinggal di `risiko`, bukan di sini:
            # panel jendela (PRD 11.4) menyimpan rencana lewat jalur yang sama (T69).
            tersimpan = risiko.simpan_dari_kandidat(
                sambungan,
                hasil,
                entri=entri,
                jenis_stop=argumen.jenis_stop,
                id_snapshot=masukan.potret.id_snapshot,
                id_rencana=argumen.rencana_revisi,
                pelanggaran_diterima=argumen.terima_pelanggaran,
            )
            print("\n" + tersimpan.ringkas())
            if tersimpan.status_dipindahkan:
                baru = kandidat.wajib_ada(sambungan, entri.id_kandidat)
                print(
                    f"Kandidat #{baru.id_kandidat} {baru.kode}: status watchlist -> rencana "
                    f"(revisi {baru.revisi}; riwayatnya tetap tersimpan)"
                )
            if tersimpan.peringatan is not None:
                print(f"PERINGATAN: {tersimpan.peringatan}", file=sys.stderr)
                return KODE_GAGAL
            return KODE_OK
        except (
            risiko.GalatRisiko,
            konfigurasi.GalatKonfigurasi,
            kandidat.GalatKandidat,
            ingesti.GalatIngesti,
            db.GalatBasisData,
        ) as galat:
            print(f"MejaSaham: {galat}", file=sys.stderr)
            return KODE_GAGAL
    finally:
        sambungan.close()


def _cetak_drawdown(sambungan: object, *, mode: str | None = None) -> int:
    """Deret ekuitas harian beserta drawdown dari puncaknya (AC-13, PRD 8.2)."""
    from datetime import date as _tanggal

    from mejasaham import risiko

    dd = risiko.drawdown(sambungan, mode=mode)  # type: ignore[arg-type]
    if not dd.deret:
        print(
            "Ekuitas harian belum pernah dicatat. Catat dengan --ekuitas-harian <rupiah> "
            "[--kas <rupiah>] [--arus-dana <rupiah>]."
        )
        return KODE_OK
    print(f"  {'tanggal':<11} {'ekuitas':>16} {'arus dana':>16} {'mode':>18}")
    for satu in dd.deret:
        arus = "(belum dicatat)" if satu.arus_dana is None else tampilan.angka(satu.arus_dana, 0)
        print(
            f"  {satu.tanggal:<11} {tampilan.angka(satu.ekuitas, 0):>16} {arus:>16} "
            f"{(satu.mode or '(belum dinyatakan)'):>18}"
        )
    hari_ini = _tanggal.today().isoformat()
    belum_terjadi = [satu.tanggal for satu in dd.deret if satu.tanggal > hari_ini]
    if belum_terjadi:
        print(
            f"\n  Catatan: {len(belum_terjadi)} catatan bertanggal SETELAH hari ini "
            f"({', '.join(belum_terjadi[:3])}) ikut ditampilkan di sini, tetapi tidak dipakai "
            "dasbor harian — tanggal yang belum terjadi tidak boleh menjadi bagian keadaan hari ini."
        )
    if dd.terkoreksi:
        print(
            f"\nDrawdown  : {tampilan.angka((dd.drawdown_bp or 0) / 100, 2)}% dari puncak "
            f"(terkoreksi arus dana; puncak {dd.tanggal_puncak}) · maksimum "
            f"{tampilan.angka((dd.drawdown_maksimum_bp or 0) / 100, 2)}%"
        )
        print(
            "  Terkoreksi berarti: setoran dan penarikan dikeluarkan lebih dulu dari deretnya, "
            "jadi keduanya tidak terbaca sebagai hasil (AC-13)."
        )
    else:
        print(
            f"\nDrawdown terkoreksi TIDAK DAPAT DINILAI: {dd.alasan}\n"
            f"  Mentah (tanpa koreksi, setoran terbaca sebagai kenaikan): "
            f"{tampilan.angka(dd.mentah_bp / 100, 2)}% dari puncak · maksimum "
            f"{tampilan.angka(dd.mentah_maksimum_bp / 100, 2)}%"
        )
    return KODE_OK


def _catat_transaksi(sambungan: object, argumen: argparse.Namespace) -> int:
    """Satu eksekusi manual (F11, PRD 9.1 langkah 9)."""
    from mejasaham import posisi

    kurang = [
        nama
        for nama, nilai in (
            ("--aksi", argumen.aksi),
            ("--lembar", argumen.lembar),
            ("--harga", argumen.harga),
            ("--mode", argumen.mode),
        )
        if nilai is None
    ]
    if kurang:
        print(
            f"MejaSaham: --catat-transaksi menuntut {', '.join(kurang)}. Mode wajib dinyatakan "
            "(simulasi atau nyata) sebab metrik kedua mode dilaporkan terpisah (PRD 9.11).",
            file=sys.stderr,
        )
        return KODE_GAGAL
    hasil = posisi.catat_transaksi(
        sambungan,  # type: ignore[arg-type]
        argumen.catat_transaksi,
        argumen.aksi,
        harga=argumen.harga,
        lembar=argumen.lembar,
        mode=argumen.mode,
        tanggal=argumen.tanggal,
        id_rencana=argumen.id_rencana,
        id_posisi=argumen.id_posisi,
        biaya=argumen.biaya,
        pajak=argumen.pajak,
        broker=argumen.broker,
        catatan=argumen.alasan,
    )
    print(hasil.ringkas())
    if hasil.pelanggaran:
        print(
            "\nPelanggaran di atas **tercatat**, bukan ditolak (PRD 9.8): kepatuhan dihitung dari "
            "transaksi yang tercatat (PRD 13.2), dan eksekusi yang sudah terjadi tidak menjadi "
            "tidak terjadi karena aplikasi menolak mencatatnya.",
            file=sys.stderr,
        )
    else:
        print("Tidak ada pelanggaran yang terdeteksi pada transaksi ini.")
    print(
        "\nCatatan: yang dinilai di sini baru V1/V2/V5/V6 (yang terdeteksi saat transaksinya "
        "dicatat). V3 (batas bobot/sektor/total risiko), V4 (menambah posisi rugi tanpa tesis "
        "baru), dan V7 (posisi dipertahankan setelah pembatal tesis terpicu) diturunkan dari baris "
        "yang sudah ada dan terhitung di --rekap-kepatuhan (F7, PRD 9.8)."
    )
    return KODE_OK


def _cetak_hak_right_issue(sambungan: object, argumen: argparse.Namespace) -> int:
    """Right issue yang menyentuh posisi (PRD 9.11): hak, tenggat, dan keputusannya."""
    from datetime import date

    from mejasaham import posisi

    hak = posisi.hak_right_issue(sambungan, kode=argumen.kode, hari_ini=date.today())  # type: ignore[arg-type]
    if not hak:
        print(
            "(tidak ada right issue yang menyentuh posisi mana pun. Right issue masuk lewat "
            "aksi-korporasi.csv → --impor; yang sumber data EOD terbitkan hanya split dan dividen)"
        )
        return KODE_OK
    print(
        "HAK RIGHT ISSUE — dihitung dari rasio aksi × lembar yang dipegang pada tanggal aksi "
        "(petunjuk, bukan angka sekuritas Anda)"
    )
    for satu in hak:
        print(f"  {satu.ringkas()}")
    belum = [satu for satu in hak if not satu.sudah_diputuskan and not satu.tenggat_lewat(date.today())]
    lewat = [satu for satu in hak if not satu.sudah_diputuskan and satu.tenggat_lewat(date.today())]
    print(
        f"  {len(hak)} right issue · {len(belum)} menunggu keputusan · {len(lewat)} tenggatnya "
        "sudah lewat tanpa keputusan"
    )
    if belum or lewat:
        print(
            "\nKeputusan dicatat lewat --putuskan-right-issue KODE --tanggal-aksi YYYY-MM-DD "
            "--keputusan tebus|jual_hmetd|abaikan."
        )
    return KODE_OK


def _putuskan_right_issue(sambungan: object, argumen: argparse.Namespace) -> int:
    """Catat keputusan manual right issue (PRD 9.11)."""
    from mejasaham import posisi

    kurang = [
        nama
        for nama, nilai in (
            ("--tanggal-aksi", argumen.tanggal_aksi),
            ("--keputusan", argumen.keputusan),
        )
        if nilai is None
    ]
    if kurang:
        print(
            f"MejaSaham: --putuskan-right-issue menuntut {', '.join(kurang)}. Keputusan yang sah: "
            "tebus, jual_hmetd, abaikan (PRD 9.11).",
            file=sys.stderr,
        )
        return KODE_GAGAL
    hasil = posisi.catat_keputusan_right_issue(
        sambungan,  # type: ignore[arg-type]
        argumen.putuskan_right_issue,
        argumen.tanggal_aksi,
        argumen.keputusan,
        id_posisi=argumen.id_posisi,
        id_transaksi=argumen.id_transaksi,
        lembar=argumen.lembar,
        harga=argumen.harga,
        biaya=argumen.biaya,
        catatan=argumen.alasan,
    )
    print(hasil.ringkas())
    print(
        "\nKeputusannya tersimpan sebagai baris baru (append-only): keputusan sebelumnya tidak "
        "dihapus, dan revisinya bertambah bila diubah."
    )
    return KODE_OK


def jalankan_posisi(argumen: argparse.Namespace) -> int:
    """F11: transaksi, posisi, stop, dan dasbor harian — mode kepala, tanpa jendela (AC-11)."""
    from mejasaham import db, ingesti, kandidat, konfigurasi, dasbor, lokasi, posisi, risiko

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        try:
            if argumen.catat_transaksi is not None:
                return _catat_transaksi(sambungan, argumen)

            if argumen.putuskan_right_issue is not None:
                return _putuskan_right_issue(sambungan, argumen)

            if argumen.hak_right_issue:
                return _cetak_hak_right_issue(sambungan, argumen)

            if argumen.ubah_stop:
                if argumen.id_posisi is None or argumen.stop is None:
                    print(
                        "MejaSaham: --ubah-stop menuntut --id-posisi ID dan --stop RUPIAH.",
                        file=sys.stderr,
                    )
                    return KODE_GAGAL
                perubahan = posisi.ubah_stop(
                    sambungan,
                    argumen.id_posisi,
                    argumen.stop,
                    alasan=argumen.alasan,
                    tanggal=argumen.tanggal,
                )
                print(perubahan.ringkas())
                return KODE_OK

            if argumen.dasbor:
                # `--teratas` dipakai bersama `--saring` (bawaannya 20); dasbor punya bawaannya
                # sendiri supaya tetap satu halaman, dan `--teratas` tetap menimpanya.
                laporan = dasbor.susun(sambungan, teratas=argumen.teratas or 5)
                print(laporan.ringkas())
                from mejasaham import jadwal

                print()
                print(jadwal.ringkas(jadwal.susun(sambungan)))
                return KODE_OK

            if argumen.drawdown and not argumen.posisi and not argumen.posisi_semua:
                return _cetak_drawdown(sambungan)

            status = None if argumen.posisi_semua else "aktif"
            isi = posisi.ringkasan_semua(sambungan, status=status)
            print(
                "POSISI AKTIF" if status == "aktif" else "SELURUH POSISI",
                "— risiko terbuka = (penutupan terakhir − stop terkini) × lembar (PRD 8.2)",
            )
            print(
                posisi.ringkas_daftar(
                    isi,
                    judul_kosong=(
                        "(belum ada posisi tercatat — buka dengan --catat-transaksi KODE --aksi beli "
                        "--lembar N --harga R --mode nyata)"
                    ),
                )
            )
            if argumen.posisi_semua and isi:
                print("\nTRANSAKSI")
                for satu in posisi.daftar_transaksi(sambungan):
                    print(f"  {satu.ringkas()}")
            if argumen.drawdown:
                print()
                return _cetak_drawdown(sambungan)
            return KODE_OK
        except (
            posisi.GalatPosisi,
            risiko.GalatRisiko,
            dasbor.GalatDasbor,
            konfigurasi.GalatKonfigurasi,
            konfigurasi.ParameterBelumSiap,
            kandidat.GalatKandidat,
            ingesti.GalatIngesti,
            # Kunci tulis yang tidak didapat (A2/AC-19): pesannya satu kalimat bersama dengan
            # mode jendela (`db.KALIMAT_TERKUNCI`), bukan traceback `sqlite3` yang tidak bisa
            # dikerjakan siapa pun.
            db.GalatBasisData,
        ) as galat:
            print(f"MejaSaham: {galat}", file=sys.stderr)
            return KODE_GAGAL
    finally:
        sambungan.close()


def jalankan_jurnal(argumen: argparse.Namespace) -> int:
    """F7: jurnal keputusan & rekap kepatuhan — mode kepala, tanpa jendela (AC-11)."""
    from mejasaham import db, jurnal, kandidat, konfigurasi, lokasi, posisi, risiko

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        try:
            if argumen.jurnal_catat is not None:
                sebelum = jurnal.catatan_terkini(sambungan, argumen.jurnal_catat)
                catatan = jurnal.catat(
                    sambungan,
                    argumen.jurnal_catat,
                    alasan=argumen.alasan,
                    pelajaran=argumen.pelajaran,
                    tanggal_tinjau=argumen.tanggal_tinjau,
                    selesai_pada=argumen.tanggal if argumen.tandai_selesai else None,
                )
                print(catatan.ringkas())
                if sebelum is None:
                    print(
                        f"\nCatatan ini baris jurnal PERTAMA untuk transaksi "
                        f"#{argumen.jurnal_catat}."
                    )
                else:
                    print(
                        f"\nRevisi r{sebelum.revisi} disimpan, bukan ditimpa (PRD 9.8): "
                        f"{sebelum.ringkas()}"
                    )
                print(
                    "Jurnal tidak memblokir apa pun (K34): catatan ini tidak mengubah transaksi, "
                    "posisi, maupun pelanggaran yang tercatat di barisnya."
                )
                if not argumen.jurnal and not argumen.rekap_kepatuhan:
                    return KODE_OK

            keluaran: list[str] = []
            if argumen.jurnal:
                keluaran.append(_cetak_jurnal(sambungan, argumen))
            if argumen.rekap_kepatuhan:
                laporan = jurnal.rekap(sambungan, bulan=argumen.bulan, mode=argumen.mode)
                keluaran.append(laporan.ringkas())
            print("\n\n".join(keluaran))
            return KODE_OK
        except (
            jurnal.GalatJurnal,
            posisi.GalatPosisi,
            risiko.GalatRisiko,
            kandidat.GalatKandidat,
            konfigurasi.GalatKonfigurasi,
            konfigurasi.ParameterBelumSiap,
            # Lihat catatan di jalankan_posisi: kunci tulis yang gagal bukan traceback.
            db.GalatBasisData,
        ) as galat:
            print(f"MejaSaham: {galat}", file=sys.stderr)
            return KODE_GAGAL
    finally:
        sambungan.close()


def _cetak_jurnal(sambungan: object, argumen: argparse.Namespace) -> str:
    """Daftar baris jurnal: satu keputusan per transaksi, beserta pelanggaran yang menempel."""
    from mejasaham import jurnal

    kode = [satu.strip().upper() for satu in (argumen.kode or "").split(",") if satu.strip()]
    isi = []
    for satu in kode or [None]:
        isi.extend(
            jurnal.baris(sambungan, bulan=argumen.bulan, kode=satu, mode=argumen.mode)  # type: ignore[arg-type]
        )
    isi.sort(key=lambda baris: (baris.transaksi.tanggal, baris.transaksi.id_transaksi))
    periode = argumen.bulan or "seluruh periode"
    mode = argumen.mode or "seluruh mode"
    if not isi:
        return (
            f"JURNAL KEPUTUSAN — {periode} · {mode}\n\n"
            "  (belum ada keputusan tercatat pada periode ini. Jurnal menilai transaksi yang "
            "tercatat — PRD 9.8/K34 — jadi ia kosong selama belum ada eksekusi yang dicatat "
            "lewat --catat-transaksi.)"
        )
    patuh = sum(1 for satu in isi if satu.patuh)
    baris = [
        f"JURNAL KEPUTUSAN — {periode} · {mode}",
        f"  {len(isi)} keputusan · patuh aturan {patuh}/{len(isi)} "
        f"({tampilan.angka(patuh / len(isi) * 100, 2)}%) · pelanggaran "
        f"{sum(len(satu.pelanggaran) for satu in isi)}",
        "",
    ]
    for satu in isi:
        baris.append("  " + satu.ringkas())
        baris.append("")
    baris.append(
        "Catatan: kode pelanggaran dibaca dari satu tempat per kode (V1/V2/V6 dari baris "
        "transaksi, V5 dari baris posisi, V3/V4/V7 diturunkan) — tidak ada yang dihitung dua kali. "
        "Rekapnya: --rekap-kepatuhan."
    )
    return "\n".join(baris)


def jalankan_ekspor(argumen: argparse.Namespace) -> int:
    """Ekspor satu laporan F9 sebagai CSV untuk Excel Indonesia."""
    from mejasaham import db, ekspor, lokasi

    if argumen.keluaran is None:
        print("MejaSaham: --ekspor menuntut --keluaran berkas.csv", file=sys.stderr)
        return KODE_GAGAL
    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    try:
        hasil = ekspor.ekspor(
            sambungan, argumen.ekspor, argumen.keluaran, id_preset=argumen.preset
        )
    except (ekspor.GalatEkspor, db.GalatBasisData) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    finally:
        sambungan.close()
    print(
        f"Ekspor {argumen.ekspor}: {hasil.jumlah_baris} baris · snapshot #{hasil.id_snapshot} · "
        f"preset {hasil.id_preset} · {hasil.jalur}"
    )
    return KODE_OK


def jalankan_cadangan(argumen: argparse.Namespace) -> int:
    """Operasi F12 tanpa membuka jendela atau lebih dulu memigrasikan basis data."""
    from mejasaham import cadangan, db, lokasi

    try:
        if argumen.pulihkan is not None:
            cadangan.pulihkan(argumen.pulihkan)
            print(f"Pemulihan selesai dari: {argumen.pulihkan}")
        elif argumen.daftar_cadangan:
            # Teksnya satu tempat dengan menu jendela (aksi #19c): daftar di layar tidak bisa
            # berbeda dari keluaran baris perintah karena keduanya memanggil fungsi ini.
            print(cadangan.ringkas_daftar(argumen.folder_cadangan))
        else:
            sambungan = db.siapkan()
            try:
                hasil = cadangan.buat(sambungan, tujuan=argumen.folder_cadangan)
            finally:
                sambungan.close()
            print(f"Cadangan dibuat: {hasil}")
    except (cadangan.GalatCadangan, db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    return KODE_OK


def jalankan_ambil_notasi(argumen: argparse.Namespace) -> int:
    """Ambil notasi khusus, suspensi, dan UMA IDX (P22) ke `notasi-khusus.csv`.

    Jalurnya `notasi.ambil_ke_berkas`. Tombol "Perbarui data" tidak lagi memanggilnya (K96:
    Syarat Penggunaan IDX melarang scraping); perintah ini tetap ada sampai diputuskan terpisah.
    Penulisan basis data tetap lewat `--impor` (atau refresh, yang membaca berkas yang sama).
    """
    from mejasaham import lokasi, notasi

    tujuan = None
    try:
        tujuan = notasi.berkas_tujuan(lokasi.folder_konfigurasi())
        jeda = argumen.jeda if argumen.jeda is not None else notasi.JEDA_BAWAAN
        hasil = notasi.ambil_ke_berkas(tujuan.parent, jeda=jeda)
    except (notasi.GalatNotasi, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    except OSError as galat:
        print(
            f"MejaSaham: gagal menulis berkas notasi ke '{tujuan}': {galat}. "
            "Pilih folder data yang bisa ditulis dengan --folder-data FOLDER.",
            file=sys.stderr,
        )
        return KODE_GAGAL

    print(hasil.ringkas())
    print(
        "\nLangkah berikutnya (penulisan basis data tetap satu jalur):\n"
        f'  python -m mejasaham --impor "{hasil.tulisan.jalur.parent}"'
        + (
            f" --folder-data {argumen.folder_data}"
            if argumen.folder_data is not None
            else ""
        )
    )
    return KODE_OK


def jalankan_tanpa_jendela(argumen: argparse.Namespace) -> int:
    """Mode kepala untuk ingesti & saringan — satu titik masuk untuk Task Scheduler (AC-11)."""
    if argumen.refresh:
        kode = jalankan_refresh(argumen)
        # `--refresh --saring` menyaring snapshot yang baru ditulis; refresh yang gagal tidak
        # disusul saringan, sebab saringan itu akan memeringkat snapshot lama.
        if kode != KODE_OK or not argumen.saring:
            return kode
        return jalankan_saring(argumen)
    if argumen.saring:
        return jalankan_saring(argumen)
    return KODE_BELUM_DITERAPKAN


def jalankan_preset_bawaan() -> int:
    """Simpan preset bawaan (K1) yang belum ada, lalu laporkan daftarnya."""
    from mejasaham import db, lokasi, pengatur, saring

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL
    try:
        baru = pengatur.siapkan_preset_bawaan(sambungan)
        daftar = saring.daftar_preset(sambungan)
    finally:
        sambungan.close()

    print(f"Preset baru disimpan: {', '.join(baru) if baru else '(tidak ada, sudah lengkap)'}")
    print("Preset di basis data:")
    for id_preset, nama, versi, horizon in daftar:
        print(f"  {id_preset:24s} v{versi} · horizon {horizon}")
    print(
        "\nCatatan: preset adalah baris berversi di basis data (K6). Mengubah ambang berarti "
        "membuat versi baru, bukan menyunting yang lama — supaya arti skor lama tidak berubah."
    )
    return KODE_OK


def jalankan_saring(argumen: argparse.Namespace) -> int:
    """Saringan + skoring pada snapshot terakhir (F2/F3), tanpa jendela (AC-11)."""
    from mejasaham import db, ingesti, lokasi, pengatur, saring

    hanya_kode = None
    if argumen.kode:
        hanya_kode = tuple(
            satu.strip().upper() for satu in argumen.kode.split(",") if satu.strip()
        )

    try:
        sambungan = db.siapkan()
    except (db.GalatBasisData, lokasi.GalatLokasi) as galat:
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    try:
        try:
            baru = pengatur.siapkan_preset_bawaan(sambungan)
            if baru:
                print(f"Preset bawaan disimpan: {', '.join(baru)}")
            preset = (
                saring.muat_preset(sambungan, argumen.preset)
                if argumen.preset
                else saring.preset_terbaru(sambungan, "kualitas-nilai")
            )
            laporan = pengatur.jalankan_saring(
                sambungan,
                preset,
                hanya_kode=hanya_kode,
                simpan=hanya_kode is None,
                sumber=argumen.sumber,
            )
        except (ingesti.GalatIngesti, db.GalatBasisData) as galat:
            # Penyimpanan skor menulis ke basis data: kunci yang tidak didapat dilaporkan dengan
            # kalimat bersama (`db.KALIMAT_TERKUNCI`), bukan traceback `sqlite3` (A2/AC-19).
            print(f"MejaSaham: {galat}", file=sys.stderr)
            return KODE_GAGAL
    finally:
        sambungan.close()

    print(laporan.ringkas())
    teratas = laporan.teratas(argumen.teratas or 20)
    if teratas:
        if not laporan.peringkat_sementara:
            print("\nKandidat teratas (skor 0–100, urut peringkat):")
        else:
            # PRD 7.3: tanpa data notasi khusus, tidak ada emiten yang boleh disebut kandidat.
            # Peringkatnya tetap ditampilkan supaya pekerjaan lain bisa jalan — tetapi menyebutnya
            # "kandidat" akan membuat aplikasi ini menjanjikan pemeriksaan yang belum pernah
            # dilakukan, dan itu justru kerugian yang paling mahal bagi pemakainya.
            print(
                "\nPeringkat sementara — BELUM BOLEH DISEBUT KANDIDAT (skor 0–100, urut peringkat):"
            )
            print(f"  Sebabnya: {laporan.sebab_sementara()}.")
        print(f"  {'#':>3} {'kode':<6} {'skor':>6} {'kualitas':>9} {'nilai':>7} {'momentum':>9} {'volatil':>8}")
        for satu in teratas:
            print(
                f"  {satu.peringkat or 0:>3} {satu.kode:<6} {tampilan.angka(satu.skor_total, 1):>6} "
                f"{_skor_teks(satu.skor_faktor('kualitas')):>9} "
                f"{_skor_teks(satu.skor_faktor('nilai')):>7} "
                f"{_skor_teks(satu.skor_faktor('momentum')):>9} "
                f"{_skor_teks(satu.skor_faktor('volatilitas')):>8}"
            )
    else:
        # Kalimatnya tinggal di `LaporanSaring`, supaya panel jendela (PRD 11.2) menyebut sebab
        # yang sama persis ketika daftarnya kosong.
        print("\n" + laporan.catatan_peringkat_kosong())

    gagal_lolos = [satu for satu in laporan.hasil_saring if not satu.lolos]
    if gagal_lolos and argumen.kode:
        print("\nRincian kriteria (hanya untuk --kode):")
        for satu in gagal_lolos[: len(hanya_kode or ())]:
            print(f"  {satu.kode}: {satu.ringkas()}")
    return KODE_OK


def _skor_teks(skor: float | None) -> str:
    return "—" if skor is None else tampilan.angka(skor, 1)


def jalankan_muat_konfigurasi() -> int:
    """Muat parameter bursa bertanggal dari berkas TOML ke basis data (K6, T7).

    Keluar 0 bila berkas terbaca dan tersimpan — termasuk ketika sebagian parameter masih
    "belum terverifikasi", karena itu keadaan yang sah dan dilaporkan dengan mencolok.
    Keluar 1 bila berkas tidak terbaca, isinya salah, atau basis data menolak.
    """
    from mejasaham import db, konfigurasi, lokasi

    try:
        berkas, disalin = konfigurasi.siapkan_berkas()
        jalur, entri = konfigurasi.muat_berkas(berkas)
        sambungan = db.siapkan()
        try:
            hasil = konfigurasi.simpan(sambungan, entri)
            status = konfigurasi.ringkasan_status(sambungan)
        finally:
            sambungan.close()
    except (konfigurasi.GalatKonfigurasi, db.GalatBasisData, lokasi.GalatLokasi) as galat:
        # Hanya galat yang sudah punya pesan untuk manusia yang ditangkap; bug lain tetap
        # naik sebagai traceback supaya tidak tersembunyi (aturan keras 7).
        print(f"MejaSaham: {galat}", file=sys.stderr)
        return KODE_GAGAL

    print(f"Berkas parameter : {jalur}" + ("  (baru disalin dari template bawaan)" if disalin else ""))
    print(f"Entri di berkas  : {hasil.total} (baru disimpan: {hasil.baru}, sudah ada dan sama: {hasil.tetap})")
    print("Keadaan parameter:")
    for satu in status:
        print(f"  {satu.label:34s} {satu.keadaan}")

    belum_siap = [satu for satu in status if not satu.siap]
    if belum_siap:
        print("", file=sys.stderr)
        print(
            f"Peringatan: {len(belum_siap)} dari {len(status)} parameter belum siap dipakai. "
            "Fitur yang bergantung padanya menolak menghitung sampai diisi dari pengumuman resmi:",
            file=sys.stderr,
        )
        for satu in belum_siap:
            print(f"  - {satu.alasan}", file=sys.stderr)
    return KODE_OK


def jalankan_web(argumen: argparse.Namespace) -> int:
    """Dasbor web lokal (K91): layani sampai Ctrl+C. Tidak mengimpor Qt."""
    from mejasaham import lokasi
    from mejasaham.web import server as web_server

    port = web_server.PORT_BAWAAN if argumen.port is None else argumen.port
    try:
        server = web_server.buat_server(port=port)
    except OSError as galat:
        print(
            f"MejaSaham: dasbor web tidak bisa mendengar di 127.0.0.1:{port} — {galat}. "
            "Mungkin dasbor lain sudah berjalan; pakai --port untuk port lain.",
            file=sys.stderr,
        )
        return KODE_GAGAL
    alamat = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Dasbor Meja Saham berjalan di {alamat}")
    print(f"Folder data: {lokasi.folder_data()}")
    print("Hentikan dengan Ctrl+C.")
    if not argumen.tanpa_peramban:
        import webbrowser

        webbrowser.open(alamat)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Dasbor dihentikan.")
    finally:
        server.server_close()
    return KODE_OK


def _aman_untuk_konsol() -> None:
    """Jangan biarkan satu karakter yang tak terwakili mematikan seluruh jalan.

    Konsol Windows bawaan memakai codepage warisan (mis. cp1252), dan karakter seperti "≥" atau
    "→" tidak ada di sana. Tanpa penjagaan ini, `print()` melempar `UnicodeEncodeError` **setelah**
    pekerjaan selesai — snapshot tersimpan, tetapi proses keluar dengan kode gagal dan pengguna
    hanya melihat traceback (AC-9, AC-11). Karakternya diganti tanda tanya, bukan disembunyikan:
    pesannya tetap terbaca, dan yang hilang hanya glifnya.
    """
    for aliran in (sys.stdout, sys.stderr):
        try:
            aliran.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            # Aliran yang tidak bisa diatur ulang (mis. sudah dibungkus pytest) dibiarkan apa
            # adanya: menolak jalan hanya karena ini akan lebih buruk daripada glif aneh.
            continue


def main(argv: list[str] | None = None) -> int:
    _aman_untuk_konsol()
    argumen = baca_argumen(sys.argv[1:] if argv is None else argv)
    _pakai_folder_data(argumen.folder_data)
    _pakai_folder_cadangan(argumen.folder_cadangan)

    if argumen.buat_cadangan or argumen.daftar_cadangan or argumen.pulihkan is not None:
        return jalankan_cadangan(argumen)

    if argumen.impor_unduhan or argumen.ingatkan:
        return jalankan_unduhan_idx(argumen)

    if argumen.muat_konfigurasi:
        kode = jalankan_muat_konfigurasi()
        if kode != KODE_OK:
            return kode
    if argumen.emiten_awal:
        kode = jalankan_emiten_awal(argumen.timpa_emiten)
        if kode != KODE_OK:
            return kode
    if argumen.ambil_emiten:
        kode = jalankan_ambil_emiten(argumen)
        if kode != KODE_OK:
            return kode
    if argumen.ambil_kalender:
        kode = jalankan_ambil_kalender(argumen)
        if kode != KODE_OK:
            return kode
    if argumen.ambil_sun:
        kode = jalankan_ambil_sun()
        if kode != KODE_OK:
            return kode
    if argumen.ambil_fundamental:
        kode = jalankan_ambil_fundamental(argumen)
        if kode != KODE_OK:
            return kode
    if argumen.ambil_jenis:
        kode = jalankan_ambil_jenis(argumen)
        if kode != KODE_OK:
            return kode
    if argumen.kerangka_rasio_bank:
        kode = jalankan_kerangka_rasio_bank(argumen)
        if kode != KODE_OK:
            return kode
    if argumen.ambil_notasi:
        kode = jalankan_ambil_notasi(argumen)
        if kode != KODE_OK:
            return kode
    if argumen.impor is not None:
        kode = jalankan_impor(argumen.impor)
        if kode != KODE_OK:
            return kode
    if argumen.refresh or argumen.saring:
        return jalankan_tanpa_jendela(argumen)
    if argumen.ekspor is not None:
        return jalankan_ekspor(argumen)
    if argumen.cek_sumber_kedua:
        return jalankan_cek_sumber_kedua(argumen)
    if argumen.preset_bawaan:
        return jalankan_preset_bawaan()
    if (
        argumen.kandidat_baru
        or argumen.kandidat_ubah is not None
        or argumen.tinjau_ulang is not None
        or argumen.watchlist
    ):
        # F4 tidak membuka jendela: kandidat dan watchlist harus bisa dicatat dari baris perintah
        # (AC-11), dan mode tanpa jendela itu satu-satunya jalur yang bisa diuji otomatis.
        return jalankan_kandidat(argumen)
    if (
        argumen.batas_risiko_bawaan
        or argumen.ekuitas_harian is not None
        or argumen.hitung_risiko is not None
        or argumen.rencana
        or argumen.rencana_revisi is not None
    ):
        # F5 juga tidak membuka jendela: kalkulator risiko dan rencananya harus bisa dijalankan
        # dari baris perintah (AC-11), dan itu satu-satunya jalur yang bisa diuji otomatis.
        return jalankan_risiko(argumen)
    if (
        argumen.catat_transaksi is not None
        or argumen.ubah_stop
        or argumen.posisi
        or argumen.posisi_semua
        or argumen.dasbor
        or argumen.drawdown
        or argumen.hak_right_issue
        or argumen.putuskan_right_issue is not None
    ):
        # F11 (transaksi, posisi, dasbor) juga tidak membuka jendela — dan justru inilah jalur
        # yang dipakai setiap hari setelah eksekusi di sekuritas (AC-11).
        return jalankan_posisi(argumen)
    if argumen.jurnal or argumen.rekap_kepatuhan or argumen.jurnal_catat is not None:
        # F7 juga tidak membuka jendela: jurnal keputusan dan rekap kepatuhannya harus bisa
        # dibaca dari baris perintah (AC-11), dan itu satu-satunya jalur yang bisa diuji otomatis.
        return jalankan_jurnal(argumen)
    if argumen.web:
        return jalankan_web(argumen)
    if (
        argumen.muat_konfigurasi
        or argumen.impor is not None
        or argumen.emiten_awal
        or argumen.ambil_emiten
        or argumen.ambil_kalender
        or argumen.ambil_sun
        or argumen.ambil_fundamental
        or argumen.ambil_jenis
        or argumen.kerangka_rasio_bank
        or argumen.ambil_notasi
    ):
        # Hanya memuat konfigurasi/mengimpor/menyiapkan berkas rujukan: tidak ada alasan
        # membuka dasbor.
        return KODE_OK
    # Tanpa perintah apa pun: dasbor web lokal (K91, pengganti jendela PySide6).
    return jalankan_web(argumen)
