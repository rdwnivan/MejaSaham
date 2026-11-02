"""Definisi skema basis data Meja Saham — daftar migrasi berurutan (T9).

Aturan yang mengikat berkas ini:

* **T8** (`docs/arsitektur.md`) — uang & harga `INTEGER` rupiah, lembar/volume `INTEGER`,
  tingkat & rasio masukan `INTEGER` basis poin (1 bp = 0,01%). Nilai mentah sumber yang
  berpecahan disimpan apa adanya di kolom `*_mentah` `TEXT` untuk audit, **tidak** dipakai
  berhitung.
* **S1 / aturan keras 3** (`AGENTS.md`) — tabel data append-only: kunci utama memuat
  `diketahui_pada`, perbaikan data menambah baris baru, dan trigger menolak `UPDATE`/`DELETE`.
  Tampilan `v_<tabel>_terkini` menyajikan revisi terakhir per kunci alami.
* **S2** — setiap baris menyimpan `sumber` dan `diketahui_pada`.
* Tabel dibuat `STRICT` supaya nilai bertipe salah ditolak mesin, bukan tersimpan diam-diam.

Waktu disimpan ISO-8601 (`2026-10-06`, `2026-10-06T18:05:12+07:00`); format tampilan
Indonesia (U11) urusan lapisan tampilan, bukan penyimpanan.

Cara mengubah skema: **tambah** `Migrasi` baru di `MIGRASI`, jangan menyunting migrasi yang
sudah pernah terpasang — basis data pengguna sudah menjalankannya (T9, PRD 9.13). Karena itu
daftar tabel append-only dan kunci revisi **per migrasi** dipisah (`_..._001`, `_..._002`):
migrasi 001 dibangkitkan dari daftar yang dibekukan, bukan dari daftar yang ikut tumbuh —
kalau tidak, basis data baru dan basis data lama akan punya skema yang berbeda.
`tests/test_db.py` menjaga aturan itu dengan sidik SHA-256 tiap migrasi yang sudah terpasang.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Migrasi:
    versi: int
    nama: str
    sql: str


# Seluruh tabel data migrasi 001: append-only, jadi trigger penolak UPDATE/DELETE dipasang
# untuk semuanya. DIBEKUKAN — jangan disunting; tabel baru masuk ke daftar migrasi berikutnya.
_TABEL_APPEND_ONLY_001 = (
    "emiten",
    "harga_harian",
    "harga_indeks",
    "aksi_korporasi",
    "kalender_bursa",
    "notasi_khusus",
    "sektor_idx_ic",
    "imbal_hasil_sun",
    "snapshot",
    "log_jalan",
)

# Kunci alami (tanpa `diketahui_pada`) per tabel → dasar tampilan "terkini".
# `snapshot` dan `log_jalan` tidak ada di sini: keduanya peristiwa, bukan data yang direvisi.
_KUNCI_REVISI_001: dict[str, tuple[str, ...]] = {
    "emiten": ("kode",),
    "harga_harian": ("kode", "tanggal"),
    "harga_indeks": ("indeks", "tanggal"),
    "aksi_korporasi": ("kode", "tanggal", "jenis"),
    "kalender_bursa": ("tanggal",),
    "notasi_khusus": ("kode", "jenis", "tanggal_mulai"),
    "sektor_idx_ic": ("kode_sektor",),
    "imbal_hasil_sun": ("tanggal", "tenor_tahun"),
}


def _sql_trigger_append_only(tabel_append_only: tuple[str, ...]) -> str:
    """Trigger penolak UPDATE/DELETE: aturan append-only ditegakkan mesin, bukan disiplin."""
    bagian: list[str] = []
    for tabel in tabel_append_only:
        for operasi in ("UPDATE", "DELETE"):
            bagian.append(
                f"CREATE TRIGGER trg_{tabel}_{operasi.lower()}_append_only\n"
                f"BEFORE {operasi} ON {tabel}\n"
                f"BEGIN\n"
                f"    SELECT RAISE(ABORT, '{tabel} append-only: perbaikan data menambah "
                f"baris baru, bukan menimpa (PRD 7.2)');\n"
                f"END;"
            )
    return "\n\n".join(bagian)


def _sql_tampilan_terkini(
    kunci_revisi: dict[str, tuple[str, ...]], kolom_revisi: str = "diketahui_pada"
) -> str:
    """Tampilan revisi terakhir per kunci alami.

    Diperbarui otomatis saat kolom baru ditambahkan: SQLite menyimpan teks view dan
    menyelesaikannya saat dipakai, sehingga `SELECT *` ikut memuat kolom baru.

    `kolom_revisi` adalah kolom yang menentukan revisi terbaru: tabel data memakai
    `diketahui_pada`, sedangkan parameter bursa memakai `dicatat_pada` (tanggal entri dicatat
    manusia) karena yang direvisi di sana adalah pencatatannya, bukan tanggal berlakunya.
    """
    bagian: list[str] = []
    for tabel, kunci in kunci_revisi.items():
        syarat = "\n      AND ".join(f"lain.{kolom} = r.{kolom}" for kolom in kunci)
        bagian.append(
            f"CREATE VIEW v_{tabel}_terkini AS\n"
            f"SELECT *\n"
            f"FROM {tabel} AS r\n"
            f"WHERE NOT EXISTS (\n"
            f"    SELECT 1\n"
            f"    FROM {tabel} AS lain\n"
            f"    WHERE {syarat}\n"
            f"      AND lain.{kolom_revisi} > r.{kolom_revisi}\n"
            f");"
        )
    return "\n\n".join(bagian)


_SQL_001_TABEL = """
-- Emiten: tabel rujukan yang dirawat (impor/penyuntingan manual). `lot` dan `tick`
-- SENGAJA tidak ada di sini meskipun PRD 8.1 (tabel 9) menyebutnya: K1/PRD 10 menetapkan
-- parameter bursa sebagai konfigurasi BERTANGGAL, bukan kolom yang ikut berubah tanpa jejak.
CREATE TABLE emiten (
    kode            TEXT    NOT NULL,
    nama            TEXT    NOT NULL,
    sektor_idx_ic   TEXT,
    -- NULL = belum diklasifikasi; CHECK lolos untuk NULL, jadi nilai salah tetap ditolak.
    jenis           TEXT    CHECK (jenis IN ('bank_keuangan', 'siklikal_komoditas', 'umum')),
    papan           TEXT,
    status_notasi   TEXT,
    tanggal_notasi  TEXT    CHECK (tanggal_notasi IS NULL
                                   OR tanggal_notasi GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    jumlah_saham    INTEGER CHECK (jumlah_saham IS NULL OR jumlah_saham >= 0),
    free_float_bp   INTEGER CHECK (free_float_bp IS NULL
                                   OR (free_float_bp >= 0 AND free_float_bp <= 10000)),
    sumber          TEXT    NOT NULL,
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (kode, diketahui_pada)
) STRICT;

-- Harga mentah (S5: penyesuaian aksi korporasi dihitung saat dibaca, tidak disimpan).
-- Revisi: (kode, tanggal) sama boleh muncul berkali-kali dengan `diketahui_pada` berbeda;
-- `v_harga_harian_terkini` yang menentukan mana yang dipakai.
CREATE TABLE harga_harian (
    kode            TEXT    NOT NULL,
    tanggal         TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    open            INTEGER CHECK (open   IS NULL OR open   >= 0),
    high            INTEGER CHECK (high   IS NULL OR high   >= 0),
    low             INTEGER CHECK (low    IS NULL OR low    >= 0),
    close           INTEGER CHECK (close  IS NULL OR close  >= 0),
    volume          INTEGER CHECK (volume IS NULL OR volume >= 0),
    -- U6: `nilai` dihitung close x volume kecuali sumber menyediakan nilai transaksi
    -- eksplisit; `asal_nilai` mencatat mana yang dipakai supaya asal angka bisa diaudit.
    nilai           INTEGER CHECK (nilai  IS NULL OR nilai  >= 0),
    asal_nilai      TEXT    CHECK (asal_nilai IN ('hitung', 'impor')),
    -- Nilai mentah sumber (mis. harga berpecahan dari sumber tidak resmi) untuk audit (T8).
    open_mentah     TEXT,
    high_mentah     TEXT,
    low_mentah      TEXT,
    close_mentah    TEXT,
    volume_mentah   TEXT,
    nilai_mentah    TEXT,
    sumber          TEXT    NOT NULL,
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    CHECK (high IS NULL OR low IS NULL OR high >= low),
    PRIMARY KEY (kode, tanggal, diketahui_pada)
) STRICT;

CREATE INDEX ix_harga_harian_tanggal ON harga_harian (tanggal);

-- Penutupan indeks (IHSG, LQ45/IDX80) untuk kekuatan relatif & rezim pasar (8.2).
CREATE TABLE harga_indeks (
    indeks          TEXT    NOT NULL,
    tanggal         TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    close           INTEGER CHECK (close IS NULL OR close >= 0),
    close_mentah    TEXT,
    sumber          TEXT    NOT NULL,
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (indeks, tanggal, diketahui_pada)
) STRICT;

CREATE INDEX ix_harga_indeks_tanggal ON harga_indeks (tanggal);

-- Aksi korporasi (U4): hanya split / reverse split / right issue yang menyesuaikan harga;
-- dividen dicatat untuk arus kas posisi & imbal hasil dividen, bukan penyesuaian harga.
-- Konvensi rasio: harga disesuaikan x (rasio_lama / rasio_baru).
--   split 1:2  -> rasio_lama = 1, rasio_baru = 2   (1 lembar lama menjadi 2 lembar baru)
--   reverse 2:1 -> rasio_lama = 2, rasio_baru = 1
CREATE TABLE aksi_korporasi (
    kode              TEXT    NOT NULL,
    tanggal           TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    jenis             TEXT    NOT NULL CHECK (jenis IN ('split', 'reverse_split', 'right_issue', 'dividen')),
    rasio_lama        INTEGER CHECK (rasio_lama IS NULL OR rasio_lama > 0),
    rasio_baru        INTEGER CHECK (rasio_baru IS NULL OR rasio_baru > 0),
    harga_tebus       INTEGER CHECK (harga_tebus IS NULL OR harga_tebus >= 0),
    dividen_per_saham INTEGER CHECK (dividen_per_saham IS NULL OR dividen_per_saham >= 0),
    keterangan        TEXT,
    sumber            TEXT    NOT NULL,
    diketahui_pada    TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    CHECK (jenis = 'dividen'
           OR (rasio_lama IS NOT NULL AND rasio_baru IS NOT NULL)),
    CHECK (jenis <> 'right_issue' OR harga_tebus IS NOT NULL),
    CHECK (jenis <> 'dividen' OR dividen_per_saham IS NOT NULL),
    PRIMARY KEY (kode, tanggal, jenis, diketahui_pada)
) STRICT;

-- Kalender bursa (U5): dasar "hari bursa terakhir" dan peringatan snapshot basi (AC-8).
-- Hari non-bursa tetap disimpan (hari_bursa = 0) supaya rentang tanggal bisa ditanyakan.
CREATE TABLE kalender_bursa (
    tanggal         TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    hari_bursa      INTEGER NOT NULL CHECK (hari_bursa IN (0, 1)),
    keterangan      TEXT,
    sumber          TEXT    NOT NULL,
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (tanggal, diketahui_pada)
) STRICT;

-- Notasi khusus / suspensi / papan pemantauan, bertanggal (P1, PRD 7.1).
-- `tanggal_selesai` NULL berarti masih berjalan pada saat `diketahui_pada`.
CREATE TABLE notasi_khusus (
    kode            TEXT    NOT NULL,
    jenis           TEXT    NOT NULL CHECK (jenis IN ('suspensi', 'uma', 'papan_pemantauan', 'notasi_lainnya')),
    tanggal_mulai   TEXT    NOT NULL CHECK (tanggal_mulai GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    tanggal_selesai TEXT    CHECK (tanggal_selesai IS NULL
                                   OR tanggal_selesai GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    keterangan      TEXT,
    sumber          TEXT    NOT NULL,
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    CHECK (tanggal_selesai IS NULL OR tanggal_selesai >= tanggal_mulai),
    PRIMARY KEY (kode, jenis, tanggal_mulai, diketahui_pada)
) STRICT;

-- Taksonomi IDX-IC (rujukan nama sektor; kode sektor sendiri disimpan di `emiten`).
CREATE TABLE sektor_idx_ic (
    kode_sektor     TEXT    NOT NULL,
    nama            TEXT    NOT NULL,
    id_induk        TEXT,
    sumber          TEXT    NOT NULL,
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (kode_sektor, diketahui_pada)
) STRICT;

-- Imbal hasil SUN (B10) — dipakai pembanding imbal hasil laba. Tingkat disimpan basis poin.
CREATE TABLE imbal_hasil_sun (
    tanggal             TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    tenor_tahun         INTEGER NOT NULL CHECK (tenor_tahun > 0),
    imbal_hasil_bp      INTEGER NOT NULL CHECK (imbal_hasil_bp >= 0),
    imbal_hasil_mentah  TEXT,
    sumber              TEXT    NOT NULL,
    diketahui_pada      TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (tanggal, tenor_tahun, diketahui_pada)
) STRICT;

-- Snapshot = batas waktu (as-of) + versi skema + versi aplikasi, bukan salinan penuh (S3).
-- Ditulis atomik (A6); baris yang sudah ada tidak pernah diubah (trigger append-only).
CREATE TABLE snapshot (
    id_snapshot     INTEGER PRIMARY KEY,
    tanggal_data    TEXT    NOT NULL CHECK (tanggal_data GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    batas_diketahui TEXT    NOT NULL CHECK (batas_diketahui GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    jam_ambil       TEXT    NOT NULL CHECK (jam_ambil GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    jumlah_emiten   INTEGER NOT NULL CHECK (jumlah_emiten >= 0),
    jumlah_gagal    INTEGER NOT NULL CHECK (jumlah_gagal >= 0),
    versi_skema     INTEGER NOT NULL,
    versi_aplikasi  TEXT    NOT NULL,
    catatan         TEXT
) STRICT;

CREATE INDEX ix_snapshot_tanggal_data ON snapshot (tanggal_data);

-- Log jalan: kegagalan tidak boleh senyap (PRD 7.2, AC-9). `id_snapshot` boleh NULL
-- untuk kegagalan yang terjadi sebelum snapshot terbentuk; kalau ada, harus menunjuk
-- snapshot yang benar-benar ada (foreign key ditegakkan: `PRAGMA foreign_keys=ON`).
CREATE TABLE log_jalan (
    id_log          INTEGER PRIMARY KEY,
    waktu           TEXT    NOT NULL CHECK (waktu GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    proses          TEXT    NOT NULL,
    hasil           TEXT    NOT NULL CHECK (hasil IN ('sukses', 'gagal', 'peringatan')),
    pesan           TEXT,
    id_snapshot     INTEGER REFERENCES snapshot (id_snapshot)
) STRICT;

CREATE INDEX ix_log_jalan_waktu ON log_jalan (waktu);
"""

# ---------------------------------------------------------------------------------------
# Migrasi 002 — parameter bursa bertanggal (K1, K6/T7, PRD bagian 10)
# ---------------------------------------------------------------------------------------
# Alasan bentuknya seperti ini:
#   * Parameter bursa (lot, tick, ARA/ARB, settlement, tarif, pajak, slippage) HARAM menjadi
#     konstanta di kode, dan nilainya berubah dari waktu ke waktu → tiap entri punya
#     `berlaku_sejak` dan `sumber`; nilai lama tidak pernah ditimpa (aturan keras 1 & 4).
#   * Berkas TOML adalah **alat edit**; bukti yang dipakai berhitung adalah baris di sini
#     (konsekuensi K6c). Karena itu muatannya bertipe (T8: rupiah INTEGER, tingkat basis
#     poin), bukan JSON yang menyembunyikan salah tipe.
#   * Tiga keadaan nilai dijaga bentuk tabelnya: entri tidak ada = "belum terverifikasi";
#     `aktif = 0` = "sengaja dinonaktifkan"; ada dan aktif = dipakai.
_TABEL_APPEND_ONLY_002 = (
    "parameter_bursa",
    "parameter_lot",
    "parameter_fraksi_harga_rentang",
    "parameter_auto_rejection_rentang",
    "parameter_settlement",
    "parameter_biaya_broker",
    "parameter_pajak_penjualan",
    "parameter_slippage",
    "parameter_papan_pemantauan_khusus",
)

# "Terkini" untuk parameter bukan "revisi terakhir per kunci alami" seperti tabel data,
# melainkan "pencatatan terakhir untuk satu tanggal berlaku": nilai bisa dikoreksi dengan
# `dicatat_pada` yang lebih baru tanpa menghapus catatan lama (D-6, T10).
_KUNCI_REVISI_002: dict[str, tuple[str, ...]] = {
    "parameter_bursa": ("nama", "kelompok", "berlaku_sejak"),
}


def _sql_kepala_parameter() -> str:
    """Kepala entri parameter: identitas, tanggal berlaku, sumber, dan keadaan aktif."""
    return """
CREATE TABLE parameter_bursa (
    nama            TEXT    NOT NULL CHECK (nama IN (
                        'lot', 'fraksi_harga', 'papan_pemantauan_khusus', 'auto_rejection',
                        'settlement', 'biaya_broker', 'pajak_penjualan', 'slippage')),
    -- '' = parameter ini tidak berkelompok. Hanya biaya broker (per broker) dan auto
    -- rejection (per kelompok harga resmi) yang punya kelompok.
    kelompok        TEXT    NOT NULL,
    berlaku_sejak   TEXT    NOT NULL CHECK (berlaku_sejak GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    -- Tanggal entri ini dicatat manusia; ikut kunci supaya memuat berkas dua kali tidak
    -- menambah baris, sedangkan koreksi menambah baris dengan `dicatat_pada` lebih baru.
    dicatat_pada    TEXT    NOT NULL CHECK (dicatat_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    sumber          TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    aktif           INTEGER NOT NULL CHECK (aktif IN (0, 1)),
    uraian          TEXT,
    -- Sidik jari SHA-256 isi entri: dipakai memuat ulang berkas yang sama tanpa menambah
    -- baris, dan menolak entri yang isinya berbeda pada identitas yang sama.
    sidik_jari      TEXT    NOT NULL CHECK (length(sidik_jari) = 64),
    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),
    CHECK (nama IN ('biaya_broker', 'auto_rejection') OR kelompok = ''),
    CHECK (nama NOT IN ('biaya_broker', 'auto_rejection') OR kelompok <> ''),
    -- B3 belum punya bentuk terstruktur; yang bisa diwajibkan sekarang hanya uraiannya.
    CHECK (nama <> 'papan_pemantauan_khusus' OR length(trim(coalesce(uraian, ''))) > 0)
) STRICT;
"""


_SQL_002_MUATAN = "\n".join(
    [
        # B1 — jumlah lembar per lot.
        "CREATE TABLE parameter_lot (\n"
        "    nama           TEXT    NOT NULL,\n"
        "    kelompok       TEXT    NOT NULL,\n"
        "    berlaku_sejak  TEXT    NOT NULL,\n"
        "    dicatat_pada   TEXT    NOT NULL,\n"
        "    nilai_lembar   INTEGER NOT NULL CHECK (nilai_lembar > 0),\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK (nama = 'lot'),\n"
        "    CHECK (kelompok = '')\n"
        ") STRICT;",
        # B2 — fraksi harga per rentang; `batas_atas` NULL = rentang teratas tanpa batas.
        "CREATE TABLE parameter_fraksi_harga_rentang (\n"
        "    nama           TEXT    NOT NULL,\n"
        "    kelompok       TEXT    NOT NULL,\n"
        "    berlaku_sejak  TEXT    NOT NULL,\n"
        "    dicatat_pada   TEXT    NOT NULL,\n"
        "    batas_bawah    INTEGER NOT NULL CHECK (batas_bawah >= 0),\n"
        "    batas_atas     INTEGER CHECK (batas_atas IS NULL OR batas_atas >= batas_bawah),\n"
        "    tick           INTEGER NOT NULL CHECK (tick > 0),\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada, batas_bawah),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK (nama = 'fraksi_harga'),\n"
        "    CHECK (kelompok = '')\n"
        ") STRICT;",
        # B4 — batas auto rejection per kelompok harga; persen disimpan basis poin (D-8).
        "CREATE TABLE parameter_auto_rejection_rentang (\n"
        "    nama           TEXT    NOT NULL,\n"
        "    kelompok       TEXT    NOT NULL,\n"
        "    berlaku_sejak  TEXT    NOT NULL,\n"
        "    dicatat_pada   TEXT    NOT NULL,\n"
        "    batas_bawah    INTEGER NOT NULL CHECK (batas_bawah >= 0),\n"
        "    batas_atas     INTEGER CHECK (batas_atas IS NULL OR batas_atas >= batas_bawah),\n"
        "    ara_persen_bp  INTEGER NOT NULL CHECK (ara_persen_bp BETWEEN 0 AND 10000),\n"
        "    arb_persen_bp  INTEGER NOT NULL CHECK (arb_persen_bp BETWEEN 0 AND 10000),\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada, batas_bawah),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK (nama = 'auto_rejection'),\n"
        "    CHECK (kelompok <> '')\n"
        ") STRICT;",
        # B5 — siklus settlement dalam hari kerja. Batas atas longgar: gunanya menangkap
        # salah ketik (mis. 2 menjadi 20), bukan membatasi pilihan kebijakan bursa.
        "CREATE TABLE parameter_settlement (\n"
        "    nama           TEXT    NOT NULL,\n"
        "    kelompok       TEXT    NOT NULL,\n"
        "    berlaku_sejak  TEXT    NOT NULL,\n"
        "    dicatat_pada   TEXT    NOT NULL,\n"
        "    hari_kerja     INTEGER NOT NULL CHECK (hari_kerja BETWEEN 0 AND 30),\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK (nama = 'settlement'),\n"
        "    CHECK (kelompok = '')\n"
        ") STRICT;",
        # B6/B7 — tarif broker sisi beli & sisi jual.
        "CREATE TABLE parameter_biaya_broker (\n"
        "    nama             TEXT    NOT NULL,\n"
        "    kelompok         TEXT    NOT NULL,\n"
        "    berlaku_sejak    TEXT    NOT NULL,\n"
        "    dicatat_pada     TEXT    NOT NULL,\n"
        "    persen_beli_bp   INTEGER NOT NULL CHECK (persen_beli_bp BETWEEN 0 AND 10000),\n"
        "    minimum_beli     INTEGER NOT NULL CHECK (minimum_beli >= 0),\n"
        "    persen_jual_bp   INTEGER NOT NULL CHECK (persen_jual_bp BETWEEN 0 AND 10000),\n"
        "    minimum_jual     INTEGER NOT NULL CHECK (minimum_jual >= 0),\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK (nama = 'biaya_broker'),\n"
        "    CHECK (kelompok <> '')\n"
        ") STRICT;",
        # B8 — PPh final penjualan; `dasar` menyebut dasar pengenaannya menurut aturan.
        "CREATE TABLE parameter_pajak_penjualan (\n"
        "    nama           TEXT    NOT NULL,\n"
        "    kelompok       TEXT    NOT NULL,\n"
        "    berlaku_sejak  TEXT    NOT NULL,\n"
        "    dicatat_pada   TEXT    NOT NULL,\n"
        "    persen_bp      INTEGER NOT NULL CHECK (persen_bp BETWEEN 0 AND 10000),\n"
        "    dasar          TEXT    NOT NULL CHECK (length(trim(dasar)) > 0),\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK (nama = 'pajak_penjualan'),\n"
        "    CHECK (kelompok = '')\n"
        ") STRICT;",
        # B9 — slippage: satuannya ditentukan `mode`, jadi kolomnya dipisah supaya tidak ada
        # angka yang bisa salah dibaca satuannya (tick vs persen) tanpa jejak.
        "CREATE TABLE parameter_slippage (\n"
        "    nama             TEXT    NOT NULL,\n"
        "    kelompok         TEXT    NOT NULL,\n"
        "    berlaku_sejak    TEXT    NOT NULL,\n"
        "    dicatat_pada     TEXT    NOT NULL,\n"
        "    mode             TEXT    NOT NULL CHECK (mode IN ('tick', 'persen')),\n"
        "    nilai_tick       INTEGER CHECK (nilai_tick IS NULL OR nilai_tick > 0),\n"
        "    nilai_persen_bp  INTEGER CHECK (nilai_persen_bp IS NULL\n"
        "                                     OR nilai_persen_bp BETWEEN 0 AND 10000),\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK ((mode = 'tick' AND nilai_tick IS NOT NULL AND nilai_persen_bp IS NULL)\n"
        "           OR (mode = 'persen' AND nilai_persen_bp IS NOT NULL AND nilai_tick IS NULL)),\n"
        "    CHECK (nama = 'slippage'),\n"
        "    CHECK (kelompok = '')\n"
        ") STRICT;",
        # B3 — aturan papan pemantauan khusus. Sengaja TIDAK punya tabel muatan: bentuk
        # terstrukturnya belum diketahui, dan mengarang kolom sekarang berarti menebak aturan
        # bursa. Yang tersimpan hanya uraian apa adanya dari sumber (di kepala entri).
        "CREATE TABLE parameter_papan_pemantauan_khusus (\n"
        "    nama           TEXT    NOT NULL,\n"
        "    kelompok       TEXT    NOT NULL,\n"
        "    berlaku_sejak  TEXT    NOT NULL,\n"
        "    dicatat_pada   TEXT    NOT NULL,\n"
        "    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)\n"
        "        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),\n"
        "    CHECK (nama = 'papan_pemantauan_khusus'),\n"
        "    CHECK (kelompok = '')\n"
        ") STRICT;",
    ]
)

_SQL_002_TABEL = (
    _sql_kepala_parameter()
    + "\n"
    + _SQL_002_MUATAN
    + "\n\n"
    + _sql_trigger_append_only(_TABEL_APPEND_ONLY_002)
    + "\n\n"
    + _sql_tampilan_terkini(_KUNCI_REVISI_002, kolom_revisi="dicatat_pada")
    + "\n"
)


# ---------------------------------------------------------------------------------------
# Migrasi 003 — penanda penyesuaian sumber, fundamental, rasio bank (K8/C10, PRD 7.2, 8.1)
# ---------------------------------------------------------------------------------------
# Alasan bentuknya seperti ini:
#   * **K8/C10.** Harga dari sumber tidak resmi ternyata **sudah** disesuaikan split oleh
#     sumbernya (bukti pengukuran di `docs/keputusan.md` 1.5). Kalau fakta itu tidak disimpan,
#     penyesuaian saat dibaca akan menerapkannya untuk kedua kali dan tidak ada satu pun angka
#     yang bisa dipakai memeriksanya. Karena itu penandanya disimpan **per baris**, bukan
#     sebagai satu setelan global: satu basis data boleh memuat data dari beberapa sumber yang
#     berperilaku berbeda.
#   * **`fundamental`.** Sesuai PRD 8.1/12. **Dikoreksi 10 Okt 2026:** komentar ini dulu menulis
#     "`tgl_publikasi` ikut kunci", padahal kunci utama tabelnya adalah
#     (kode, periode, jenis_laporan, **diketahui_pada**) — lihat `CREATE TABLE fundamental` di
#     bawah dan `docs/keputusan.md` C5. Yang benar: `tgl_publikasi` **bukan** bagian kunci; ia
#     **penyaring point-in-time** (laporan hanya dipakai sejak tanggal publikasinya, bukan sejak
#     akhir periode — aturan keras 3, AC-15) dan diindeks oleh `ix_fundamental_kode_publikasi`.
#   * **`mata_uang`.** Sebagian emiten IDX melaporkan dalam USD. Mencampur laporan USD dengan
#     harga rupiah menghasilkan PER/EV-EBITDA yang salah tanpa terlihat; karena itu mata uang
#     disimpan dan metrik yang mencampur keduanya menolak dihitung (bukan dianggap rupiah).
#   * **`rasio_bank`** dipisah dari `fundamental` karena butirnya (NPL, CAR, BOPO, NIM) terbit
#     dengan **irama dan butir yang berbeda** dari laporan keuangan; menaruhnya dalam satu baris
#     berarti salah satunya harus dikosongkan dan asal angkanya jadi kabur (PRD 8.4, Q6).
_TABEL_APPEND_ONLY_003 = ("fundamental", "rasio_bank")

_KUNCI_REVISI_003: dict[str, tuple[str, ...]] = {
    "fundamental": ("kode", "periode", "jenis_laporan"),
    "rasio_bank": ("kode", "periode"),
}

#: Apa yang **sudah** dilakukan sumber terhadap harga yang dikirimnya (K8/C10).
#: `NULL` berarti belum dinyatakan — dibedakan dari "tidak disesuaikan", dan perbedaannya
#: dipakai berhitung (lihat `mejasaham/penyesuaian.py`).
PENANDA_PENYESUAIAN_SUMBER = ("tidak_disesuaikan", "split", "split_dividen")


_SQL_003_TABEL = f"""
-- C10/K8: penanda apa yang sudah dilakukan sumber terhadap harganya.
-- Ditambahkan lewat ALTER TABLE, bukan tabel baru: yang berubah adalah arti baris harga yang
-- sudah ada, dan memindahkannya ke tabel lain akan memisahkan harga dari keterangannya.
ALTER TABLE harga_harian ADD COLUMN penyesuaian_sumber TEXT
    CHECK (penyesuaian_sumber IS NULL
           OR penyesuaian_sumber IN ({", ".join(repr(nilai) for nilai in PENANDA_PENYESUAIAN_SUMBER)}));

-- Fundamental (PRD 8.1/12). `jenis_laporan` memisahkan laporan tahunan dari laporan kuartalan
-- kumulatif (YTD); PER TTM dihitung dari keduanya, jadi bedanya tidak boleh hilang (AC-18).
-- Seluruh nilai uang INTEGER rupiah (T8) — nilai berpecahan dari sumber masuk apa adanya ke
-- kolom `*_mentah`, dan `mata_uang` menyatakan mata uang laporannya.
CREATE TABLE fundamental (
    kode            TEXT    NOT NULL,
    periode         TEXT    NOT NULL CHECK (periode GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    jenis_laporan   TEXT    NOT NULL CHECK (jenis_laporan IN ('tahunan', 'ytd_kumulatif')),
    tgl_publikasi   TEXT    NOT NULL CHECK (tgl_publikasi GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    mata_uang       TEXT    NOT NULL CHECK (mata_uang IN ('IDR', 'USD')),
    -- Laporan keuangan Indonesia lazim disajikan "dalam jutaan Rupiah". Angka yang diimpor
    -- apa adanya akan membuat setiap rasio salah 10^6 **tanpa terlihat**, jadi satuannya
    -- dinyatakan di berkas dan ikut disimpan sebagai jejak audit; nilai di kolom uang di bawah
    -- sudah dinormalkan ke rupiah utuh saat impor, dan angka asli sumbernya ada di `*_mentah`.
    satuan_uang     TEXT    NOT NULL CHECK (satuan_uang IN ('rupiah', 'ribuan', 'juta', 'miliar')),
    pendapatan      INTEGER CHECK (pendapatan    IS NULL OR pendapatan    >= 0),
    -- Laba, ekuitas, EBIT, dan arus kas operasi boleh negatif: rugi dan ekuitas negatif itu
    -- keadaan nyata, bukan data rusak. Yang menanganinya adalah aturan "tidak dihitung" (P11).
    laba_induk      INTEGER,
    ekuitas_induk   INTEGER,
    ebit            INTEGER,
    beban_bunga     INTEGER CHECK (beban_bunga   IS NULL OR beban_bunga   >= 0),
    da              INTEGER CHECK (da            IS NULL OR da            >= 0),
    utang_bunga     INTEGER CHECK (utang_bunga   IS NULL OR utang_bunga   >= 0),
    kas             INTEGER CHECK (kas           IS NULL OR kas           >= 0),
    cfo             INTEGER,
    jumlah_saham    INTEGER CHECK (jumlah_saham  IS NULL OR jumlah_saham  >= 0),
    dps             INTEGER CHECK (dps           IS NULL OR dps           >= 0),
    pendapatan_mentah TEXT,
    laba_induk_mentah TEXT,
    ekuitas_induk_mentah TEXT,
    sumber          TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    -- Tanpa satu pun angka, barisnya tidak berisi apa-apa dan hanya menambah baris "terkini"
    -- yang menutupi data lama — itu justru merusak, bukan melengkapi.
    CHECK (pendapatan IS NOT NULL OR laba_induk IS NOT NULL OR ekuitas_induk IS NOT NULL
           OR ebit IS NOT NULL OR cfo IS NOT NULL),
    PRIMARY KEY (kode, periode, jenis_laporan, diketahui_pada)
) STRICT;

CREATE INDEX ix_fundamental_kode_publikasi ON fundamental (kode, tgl_publikasi);

-- Rasio bank (PRD 8.4, Q6). Tingkat disimpan basis poin (T8); NIM boleh negatif (bank bisa
-- rugi bunga), sedangkan CAR dan BOPO dapat melewati 100% sehingga batas atasnya longgar.
CREATE TABLE rasio_bank (
    kode            TEXT    NOT NULL,
    periode         TEXT    NOT NULL CHECK (periode GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    tgl_publikasi   TEXT    NOT NULL CHECK (tgl_publikasi GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    npl_kotor_bp    INTEGER CHECK (npl_kotor_bp IS NULL OR npl_kotor_bp BETWEEN 0 AND 10000),
    car_bp          INTEGER CHECK (car_bp       IS NULL OR car_bp       BETWEEN 0 AND 100000),
    bopo_bp         INTEGER CHECK (bopo_bp      IS NULL OR bopo_bp      BETWEEN 0 AND 100000),
    nim_bp          INTEGER CHECK (nim_bp       IS NULL OR nim_bp       BETWEEN -10000 AND 100000),
    keterangan      TEXT,
    sumber          TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada  TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    CHECK (npl_kotor_bp IS NOT NULL OR car_bp IS NOT NULL
           OR bopo_bp IS NOT NULL OR nim_bp IS NOT NULL),
    PRIMARY KEY (kode, periode, diketahui_pada)
) STRICT;

CREATE INDEX ix_rasio_bank_kode_publikasi ON rasio_bank (kode, tgl_publikasi);
"""

# ---------------------------------------------------------------------------------------
# Migrasi 004 — preset saring berversi & skor (K6, PRD 8.1/9.4/9.5)
# ---------------------------------------------------------------------------------------
# Alasan bentuknya seperti ini:
#   * **Preset tidak hidup di berkas yang bisa disunting** (K6): arti sebuah skor lama tidak
#     boleh berubah diam-diam ketika seseorang mengubah ambangnya. Karena itu setiap perubahan
#     menaikkan `versi` dan **menambah** baris; baris lama tetap ada dan tetap tak berubah.
#   * **Ambang disimpan bertipe**, bukan JSON: T14 menolak JSON karena ia menyembunyikan salah
#     tipe. Ambang di sini hanya punya dua satuan — rupiah (likuiditas) dan basis poin
#     (tingkat/rasio × 100), dan keduanya dibedakan kolomnya, bukan ditafsirkan.
#   * **Arah penilaian ikut disimpan** (`tinggi_baik`/`rendah_baik`): arah itu bagian dari arti
#     metrik (PRD 9.5 "arahkan sesuai arti"), dan menaruhnya di kode berarti mengubah arti skor
#     lama tanpa jejak.
#   * **`skor` sengaja TIDAK append-only.** Ia turunan deterministik (A5) berkunci
#     `kode + id_snapshot + id_preset` seperti PRD 8.1 — bukan data yang direvisi manusia.
#     Menyimpannya append-only akan menumpuk salinan identik setiap kali saringan dijalankan
#     ulang, dan "terkini" kehilangan arti. Yang menjaga kejujurannya: kolom `versi_hitung`
#     supaya perubahan cara menghitung terlihat, bukan tersamar.
_TABEL_APPEND_ONLY_004 = (
    "preset_saring",
    "preset_kriteria",
    "preset_bobot_faktor",
    "preset_bobot_metrik",
)


def _sql_004_preset() -> str:
    """Tabel preset: kepala berversi + kriteria + bobot faktor + bobot metrik."""
    return """
-- Kepala preset. `id_preset` adalah identitas **satu versi** ('kualitas-nilai/v1'), sehingga
-- skor lama tetap menunjuk aturan yang benar-benar dipakainya.
CREATE TABLE preset_saring (
    id_preset   TEXT    NOT NULL CHECK (length(trim(id_preset)) > 0),
    nama        TEXT    NOT NULL CHECK (length(trim(nama)) > 0),
    versi       INTEGER NOT NULL CHECK (versi > 0),
    horizon     TEXT    NOT NULL CHECK (horizon IN ('bulanan', 'mingguan')),
    keterangan  TEXT,
    dibuat_pada TEXT    NOT NULL CHECK (dibuat_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    PRIMARY KEY (id_preset),
    UNIQUE (nama, versi)
) STRICT;

-- Kriteria saring beserta ambangnya (PRD 9.4). `urutan` menentukan urutan pemeriksaan sekaligus
-- urutan alasan yang ditampilkan; `aktif = 0` mematikan satu kriteria tanpa menghapus ambangnya.
CREATE TABLE preset_kriteria (
    id_preset       TEXT    NOT NULL REFERENCES preset_saring (id_preset),
    kriteria        TEXT    NOT NULL CHECK (kriteria IN (
                        'adtv20', 'roe_5t', 'cfo_ni', 'coverage', 'der', 'cagr_pendapatan',
                        'npl_kotor', 'car', 'bopo', 'nim',
                        'per_relatif_sektor', 'pbv_relatif_sektor', 'tren_ma200',
                        'kekuatan_relatif', 'momentum_12_1', 'pengecualian_notasi')),
    urutan          INTEGER NOT NULL CHECK (urutan > 0),
    aktif           INTEGER NOT NULL CHECK (aktif IN (0, 1)),
    ambang_rupiah   INTEGER CHECK (ambang_rupiah IS NULL OR ambang_rupiah >= 0),
    ambang_bp       INTEGER,
    pembanding      TEXT    CHECK (pembanding IS NULL
                                   OR pembanding IN ('tetap', 'median_sektor')),
    PRIMARY KEY (id_preset, kriteria),
    -- Tiap kriteria punya satu satuan saja, dan salah satu kolomnya wajib terisi: ambang yang
    -- hilang tidak boleh berarti "tanpa ambang" tanpa disengaja.
    CHECK (kriteria <> 'adtv20' OR (ambang_rupiah IS NOT NULL AND ambang_bp IS NULL)),
    CHECK (kriteria = 'adtv20' OR ambang_rupiah IS NULL),
    -- Ambang tanpa angka: likuiditas memakai satuan rupiah, sedangkan tren dan pengecualian
    -- notasi memang tidak berambang angka. Selain ketiganya, ambang_bp wajib ada dan
    -- ambang_rupiah wajib kosong.
    CHECK (kriteria IN ('adtv20', 'tren_ma200', 'pengecualian_notasi') OR ambang_bp IS NOT NULL),
    CHECK (kriteria NOT IN ('tren_ma200', 'pengecualian_notasi') OR ambang_bp IS NULL),
    CHECK ((kriteria IN ('per_relatif_sektor', 'pbv_relatif_sektor'))
           = (pembanding = 'median_sektor'))
) STRICT;

-- Bobot faktor (PRD 9.5: kualitas 30%, nilai 30%, momentum 25%, volatilitas 15%).
CREATE TABLE preset_bobot_faktor (
    id_preset   TEXT    NOT NULL REFERENCES preset_saring (id_preset),
    faktor      TEXT    NOT NULL CHECK (faktor IN (
                        'kualitas', 'nilai', 'momentum', 'volatilitas')),
    bobot_bp    INTEGER NOT NULL CHECK (bobot_bp BETWEEN 0 AND 10000),
    PRIMARY KEY (id_preset, faktor)
) STRICT;

-- Bobot metrik di dalam faktornya (PRD 9.5.1), termasuk set khusus bank dan siklikal.
-- `jenis_emiten` = 'umum' dipakai untuk semua emiten yang tidak punya set sendiri (8.4).
CREATE TABLE preset_bobot_metrik (
    id_preset       TEXT    NOT NULL,
    faktor          TEXT    NOT NULL,
    metrik          TEXT    NOT NULL CHECK (metrik IN (
                        'roe_5t', 'cfo_ni', 'coverage', 'der', 'cagr_pendapatan',
                        'npl_kotor', 'car', 'bopo', 'nim',
                        'per', 'per_normalisasi', 'pbv', 'ev_ebitda',
                        'imbal_hasil_laba_minus_sun', 'imbal_hasil_dividen',
                        'momentum_12_1', 'kekuatan_relatif_6b', 'jarak_52_minggu',
                        'volatilitas_60h', 'atr14_persen')),
    jenis_emiten    TEXT    NOT NULL CHECK (jenis_emiten IN (
                        'umum', 'bank_keuangan', 'siklikal_komoditas')),
    bobot_bp        INTEGER NOT NULL CHECK (bobot_bp BETWEEN 0 AND 10000),
    arah            TEXT    NOT NULL CHECK (arah IN ('tinggi_baik', 'rendah_baik')),
    PRIMARY KEY (id_preset, faktor, metrik, jenis_emiten),
    FOREIGN KEY (id_preset, faktor) REFERENCES preset_bobot_faktor (id_preset, faktor)
) STRICT;

-- Hasil skoring (PRD 8.1). Skor disimpan basis poin (0–10000 = 0–100) supaya urutan peringkat
-- dihitung dari nilai tak dibulatkan, sedangkan tampilan boleh dibulatkan (P10).
-- `NULL` pada skor faktor berarti faktor itu **tidak dinilai**, dan itu berbeda artinya dari
-- skor 0 ("dinilai, hasilnya paling rendah") — aturan keras 2.
CREATE TABLE skor (
    kode                TEXT    NOT NULL,
    id_snapshot         INTEGER NOT NULL REFERENCES snapshot (id_snapshot),
    id_preset           TEXT    NOT NULL REFERENCES preset_saring (id_preset),
    skor_kualitas_bp    INTEGER CHECK (skor_kualitas_bp    IS NULL OR skor_kualitas_bp    BETWEEN 0 AND 10000),
    skor_nilai_bp       INTEGER CHECK (skor_nilai_bp       IS NULL OR skor_nilai_bp       BETWEEN 0 AND 10000),
    skor_momentum_bp    INTEGER CHECK (skor_momentum_bp    IS NULL OR skor_momentum_bp    BETWEEN 0 AND 10000),
    skor_volatilitas_bp INTEGER CHECK (skor_volatilitas_bp IS NULL OR skor_volatilitas_bp BETWEEN 0 AND 10000),
    skor_total_bp       INTEGER NOT NULL CHECK (skor_total_bp BETWEEN 0 AND 10000),
    peringkat           INTEGER CHECK (peringkat IS NULL OR peringkat > 0),
    dihitung_pada       TEXT    NOT NULL CHECK (dihitung_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    versi_hitung        TEXT    NOT NULL CHECK (length(trim(versi_hitung)) > 0),
    penjelasan          TEXT    NOT NULL CHECK (length(trim(penjelasan)) > 0),
    PRIMARY KEY (kode, id_snapshot, id_preset)
) STRICT;

CREATE INDEX ix_skor_peringkat ON skor (id_snapshot, id_preset, peringkat);
"""


_SQL_003 = (
    _SQL_003_TABEL
    + "\n\n"
    + _sql_trigger_append_only(_TABEL_APPEND_ONLY_003)
    + "\n\n"
    + _sql_tampilan_terkini(_KUNCI_REVISI_003)
    + "\n"
)

_SQL_004 = (
    _sql_004_preset()
    + "\n\n"
    + _sql_trigger_append_only(_TABEL_APPEND_ONLY_004)
    + "\n"
)

#: Kunci alami `harga_harian` **setelah** migrasi 005. Sama dengan versi 001 ditambah `sumber`.
#:
#: Kunci 001 (`kode + tanggal`) benar selama hanya ada satu sumber harga. Begitu harga
#: pembanding diimpor untuk cek sumber kedua (PRD 7.3), satu `(kode, tanggal)` punya dua baris
#: yang sah — dan tampilan "terkini" yang berkunci `kode + tanggal` hanya menyisakan salah
#: satunya. Akibatnya bukan sekadar tampilan: baris sumber pertama **hilang** dari setiap
#: pembacaan, sehingga harga utamanya surut satu hari di tanggal pembanding dan laporan mutu
#: melaporkannya sebagai data bolong.
_KUNCI_REVISI_005: dict[str, tuple[str, ...]] = {
    "harga_harian": ("kode", "tanggal", "sumber"),
}


def _sql_005() -> str:
    """Bentuk ulang tampilan `v_harga_harian_terkini` agar mengenal sumber (PRD 7.3).

    Tampilan `v_harga_indeks_terkini` tidak ikut diubah: harga indeks tidak diambil dari dua
    sumber, jadi menambahkan `sumber` di sana hanya menambah kunci tanpa menambah kebenaran.

    Kolomnya ditulis eksplisit alih-alih `SELECT *`. Tampilan versi 001 memakai `SELECT *`, dan
    itu memang membuat kolom baru ikut terbaca — tetapi hanya karena SQLite menyelesaikan view
    saat dipakai. Menuliskannya di sini membuat bentuk tampilan ini bisa dibaca dan diuji
    tanpa menjalankan basis data.
    """
    kolom_harga = (
        "kode, tanggal, open, high, low, close, volume, nilai, asal_nilai,"
        " open_mentah, high_mentah, low_mentah, close_mentah, volume_mentah, nilai_mentah,"
        " penyesuaian_sumber, sumber, diketahui_pada"
    )
    syarat = "\n      AND ".join(f"lain.{kolom} = r.{kolom}" for kolom in _KUNCI_REVISI_005["harga_harian"])
    return (
        "DROP VIEW v_harga_harian_terkini;\n\n"
        "CREATE VIEW v_harga_harian_terkini AS\n"
        f"SELECT {kolom_harga}\n"
        "FROM harga_harian AS r\n"
        "WHERE NOT EXISTS (\n"
        "    SELECT 1\n"
        "    FROM harga_harian AS lain\n"
        f"    WHERE {syarat}\n"
        "      AND lain.diketahui_pada > r.diketahui_pada\n"
        ");\n"
    )


# ---------------------------------------------------------------------------------------
# Migrasi 006 — catatan cek sumber kedua (PRD 7.3: "tiap minggu")
# ---------------------------------------------------------------------------------------
# Kenapa tabelnya ada, padahal `log_jalan` sudah mencatat setiap jalan:
#
#   * PRD 7.3 menuntut perbandingan sumber kedua **tiap minggu**, jadi pertanyaan "kapan
#     terakhir dijalankan" harus bisa dijawab sistem. `log_jalan` menyimpan pesan prosa;
#     menyimpulkan cadence dari teksnya berarti menebak isinya.
#   * Yang dicatat adalah **cakupannya** (`lengkap` / `belum_lengkap`), bukan hanya "pernah
#     dijalankan". Cek yang berjalan tanpa harga pembanding tidak memenuhi tuntutan mingguan
#     walaupun ia tercatat berjalan — dan itulah bedanya laporan yang jujur dari yang seolah
#     sudah diperiksa.
#   * Append-only, seperti `snapshot` dan `log_jalan`: catatan bukti kepatuhan tidak boleh
#     bisa disunting belakangan. Menghapusnya akan membuat keadaan cadence berbohong.
_TABEL_APPEND_ONLY_006 = ("cek_sumber_kedua",)

_SQL_006_TABEL = """
CREATE TABLE cek_sumber_kedua (
    id_cek                  INTEGER PRIMARY KEY,
    dijalankan_pada         TEXT    NOT NULL CHECK (dijalankan_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    tanggal_data            TEXT    NOT NULL CHECK (tanggal_data GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    sumber_utama            TEXT,
    sumber_pembanding       TEXT,
    jumlah_diperiksa        INTEGER NOT NULL CHECK (jumlah_diperiksa >= 0),
    jumlah_ditandai         INTEGER NOT NULL CHECK (jumlah_ditandai >= 0),
    jumlah_tak_terhitung    INTEGER NOT NULL CHECK (jumlah_tak_terhitung >= 0),
    jumlah_belum_dapat      INTEGER NOT NULL CHECK (jumlah_belum_dapat >= 0),
    -- 'lengkap' = seluruh emiten ber-ADTV20 tertinggi benar-benar dibandingkan. Perbedaan
    -- harga yang ditemukan TIDAK membuat cakupannya berkurang: cek yang menemukan masalah
    -- tetap cek yang sudah dijalankan.
    cakupan                 TEXT    NOT NULL CHECK (cakupan IN ('lengkap', 'belum_lengkap')),
    catatan                 TEXT
) STRICT;

CREATE INDEX ix_cek_sumber_kedua_waktu ON cek_sumber_kedua (dijalankan_pada);
"""

_SQL_006 = (
    _SQL_006_TABEL
    + "\n\n"
    + _sql_trigger_append_only(_TABEL_APPEND_ONLY_006)
    + "\n"
)

# ---------------------------------------------------------------------------------------
# Migrasi 007 — asal tanggal publikasi fundamental (K18, 10 Okt 2026)
# ---------------------------------------------------------------------------------------
# Alasan bentuknya seperti ini:
#   * `tgl_publikasi` tetap wajib dan tetap yang menentukan sejak kapan sebuah laporan boleh
#     dipakai berhitung (aturan keras 3, AC-15). Yang ditambahkan adalah **keterangan asal**
#     tanggal itu, karena sumber otomatis (yfinance, K18) memberi **akhir periode** laporan
#     tetapi tidak pernah memberi tanggal terbitnya. Menulis akhir periode sebagai
#     `tgl_publikasi` berarti mengarang tanggal; menolak barisnya berarti metrik fundamental
#     selamanya "tidak dihitung" padahal angkanya tersedia dan terukur benar.
#   * Nilai yang dipakai untuk sumber otomatis adalah **tanggal pengambilan** — konservatif,
#     sebab data tidak akan pernah dipakai sebelum ia benar-benar bisa diketahui. Yang dijaga
#     kolom ini: "tanggal publikasi tidak diketahui" tidak boleh berubah menjadi "diterbitkan
#     pada tanggal pengambilan" hanya karena tanggalnya tersimpan rapi di kolom bertipe tanggal.
#   * `NOT NULL DEFAULT 'sumber'` membuat seluruh baris lama tetap benar tanpa ditulis ulang —
#     dan tabel `fundamental` append-only, jadi menulis ulang barisnya memang dilarang.
#   * Nilainya dijaga CHECK, bukan diserahkan pada disiplin penulis: laporan mutu yang salah
#     membaca keadaan ini akan menyatakan "dipakai sejak terbit" untuk data yang tanggal
#     terbitnya tidak diketahui siapa pun.
ASAL_TGL_PUBLIKASI_SAH = ("sumber", "tanggal_pengambilan")

_SQL_007 = f"""
ALTER TABLE fundamental ADD COLUMN asal_tgl_publikasi TEXT NOT NULL DEFAULT 'sumber'
    CHECK (asal_tgl_publikasi IN ({", ".join(repr(nilai) for nilai in ASAL_TGL_PUBLIKASI_SAH)}));
"""


# ---------------------------------------------------------------------------------------
# Migrasi 008 — parameter bertanggal yang "tidak dinyatakan sumber" (K22, K23; 10 Okt 2026)
# ---------------------------------------------------------------------------------------
# Alasan bentuknya seperti ini:
#   * **K22 — "tidak dinyatakan sumber" adalah keadaan yang sah, dan harus terbaca begitu.**
#     Halaman tarif resmi Stockbit menyatakan `0,15%`/`0,25%` dengan tegas, tetapi **tidak**
#     menyatakan tarif minimum maupun tanggal berlakunya (bukti: `.uji-data/riset-tarif-broker/
#     stockbit.md`). Bentuk entri yang menuntut keduanya memaksa satu angka karangan — persis
#     yang dilarang aturan keras 1. Karena itu:
#       - `minimum_beli`/`minimum_jual` boleh **NULL**, dan NULL berarti "sumber tidak
#         menyatakannya". Ia **bukan** 0: "tidak ada tarif minimum" adalah pernyataan tentang
#         bursa, sedangkan "tidak dinyatakan" adalah pernyataan tentang sumber — dan yang kedua
#         tidak boleh menyamar sebagai yang pertama.
#       - `berlaku_sejak` boleh berisi **tanggal pengamatan**, asalkan ada kolom pendamping
#         `asal_berlaku_sejak` yang menyatakan asalnya. Polanya sama dengan `asal_tgl_publikasi`
#         (K19b, migrasi 007): tanggalnya tetap bertipe tanggal dan tetap dipakai berhitung,
#         tetapi "tanggal berlaku tidak diketahui" tidak pernah terbaca sebagai "berlaku sejak".
#   * **K23 — tarif all-in wajib menyimpan penandanya di entri.** `0,15%`/`0,25%` sudah memuat
#     levy (BEI/KPEI/KSEI), PPN biaya broker, dan PPh final penjualan. Tanpa penanda ini,
#     kalkulator biaya akan menambahkan B8 (`pajak_penjualan` 0,1%) di atas tarif yang sudah
#     memuatnya: **salah dua kali, dan tidak terlihat di keluaran mana pun — hanya di angkanya.**
#     Komponennya disimpan sebagai baris di tabel anak, bukan sebagai teks gabungan, supaya
#     pertanyaan "apakah levy sudah termasuk?" dijawab mesin, bukan tafsiran atas kalimat.
#   * **Rebuild tabel, bukan `ALTER TABLE`.** SQLite tidak bisa mencabut `NOT NULL` dari kolom
#     yang sudah ada (`ALTER TABLE ... DROP NOT NULL` tidak ada; `ALTER TABLE ... ALTER COLUMN`
#     juga tidak). Satu-satunya jalan yang benar adalah membangun tabel baru, menyalin barisnya,
#     membuang yang lama, lalu mengganti nama — dan itu dikerjakan **di dalam migrasi ini**,
#     bukan dengan menyunting migrasi 002 yang sudah terpasang di basis data pengguna (T9).
#     Salinan barisnya diperiksa jumlahnya: rebuild yang kehilangan baris harus gagal, bukan
#     menghasilkan skema yang rapi tetapi kosong.
#   * `PRAGMA foreign_keys` dimatikan **hanya** selama rebuild dan dinyalakan kembali di akhir.
#     Tabel itu punya FOREIGN KEY ke `parameter_bursa`; tanpa mematikannya, mengganti nama tabel
#     sementara SQLite sudah menegakkan kunci akan menolak baris yang sebenarnya sah. Sebagai
#     gantinya, `PRAGMA foreign_key_check` dijalankan setelahnya: hasilnya diperiksa, dan baris
#     yatim membuat seluruh migrasi gagal (aturan keras 7).
#
#: Komponen biaya yang boleh dinyatakan **sudah termasuk** di dalam tarif broker (K23).
#: Didefinisikan **sekali** di sini dan dipakai menyusun CHECK; `mejasaham/konfigurasi.py`
#: mengimpornya, tidak menyalinnya (aturan keras 5).
KOMPONEN_BIAYA_BROKER_TERMASUK = ("levy", "ppn", "pph_penjualan")

#: Asal `berlaku_sejak` sebuah entri parameter bursa (K22). Sama polanya dengan
#: `ASAL_TGL_PUBLIKASI_SAH` (migrasi 007): nilainya dijaga CHECK, bukan diserahkan pada disiplin
#: penulis, sebab laporan yang salah membaca keadaan ini akan menyatakan "berlaku sejak" untuk
#: tanggal yang sebenarnya hanya tanggal pengamatan.
ASAL_BERLAKU_SEJAK_SAH = ("sumber", "tanggal_pengamatan")

#: Versi skema saat rebuild tabel di bawah ditulis. Dipakai `RAISE(ABORT, ...)` supaya basis data
#: yang isinya sudah berubah bentuk berhenti berisik, bukan tersalin sebagian.
_SQL_008 = f"""
-- ---------------------------------------------------------------------------------------
-- (1) Asal tanggal berlaku (K22) — lihat penjelasan panjang di komentar atas blok ini.
-- ---------------------------------------------------------------------------------------
-- `NOT NULL DEFAULT 'sumber'` membuat seluruh baris lama tetap benar tanpa ditulis ulang —
-- dan `parameter_bursa` append-only, jadi menulis ulang barisnya memang dilarang.
ALTER TABLE parameter_bursa ADD COLUMN asal_berlaku_sejak TEXT NOT NULL DEFAULT 'sumber'
    CHECK (asal_berlaku_sejak IN ({", ".join(repr(nilai) for nilai in ASAL_BERLAKU_SEJAK_SAH)}));

-- ---------------------------------------------------------------------------------------
-- (2) `minimum_beli`/`minimum_jual` boleh NULL (K22): rebuild karena SQLite tidak bisa
--     mencabut NOT NULL. Foreign key dimatikan hanya selama rebuild.
-- ---------------------------------------------------------------------------------------
PRAGMA foreign_keys = OFF;

CREATE TABLE parameter_biaya_broker_baru (
    nama             TEXT    NOT NULL,
    kelompok         TEXT    NOT NULL,
    berlaku_sejak    TEXT    NOT NULL,
    dicatat_pada     TEXT    NOT NULL,
    persen_beli_bp   INTEGER NOT NULL CHECK (persen_beli_bp BETWEEN 0 AND 10000),
    -- NULL = sumber tidak menyatakan tarif minimum. BUKAN 0: "tidak ada minimum" adalah
    -- pernyataan tentang bursa, "tidak dinyatakan" adalah pernyataan tentang sumber (K22).
    minimum_beli     INTEGER CHECK (minimum_beli IS NULL OR minimum_beli >= 0),
    persen_jual_bp   INTEGER NOT NULL CHECK (persen_jual_bp BETWEEN 0 AND 10000),
    minimum_jual     INTEGER CHECK (minimum_jual IS NULL OR minimum_jual >= 0),
    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada),
    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)
        REFERENCES parameter_bursa (nama, kelompok, berlaku_sejak, dicatat_pada),
    CHECK (nama = 'biaya_broker'),
    CHECK (kelompok <> '')
) STRICT;

-- Rebuild yang menyusut berarti penyalinannya salah. `RAISE(ABORT, ...)` hanya sah di dalam
-- program trigger, jadi pemeriksaannya dipasang sebagai trigger yang memeriksa **sebelum** baris
-- lama dibuang; kalau jumlahnya tidak sama, migrasi berhenti dan tabel aslinya masih utuh.
CREATE TRIGGER trg_008_jumlah_salinan_biaya_broker
BEFORE INSERT ON parameter_biaya_broker_baru
WHEN (SELECT COUNT(*) FROM parameter_biaya_broker_baru) + 1
     > (SELECT COUNT(*) FROM parameter_biaya_broker)
BEGIN
    SELECT RAISE(ABORT, 'migrasi 008: penyalinan parameter_biaya_broker menambah baris');
END;

INSERT INTO parameter_biaya_broker_baru
    (nama, kelompok, berlaku_sejak, dicatat_pada,
     persen_beli_bp, minimum_beli, persen_jual_bp, minimum_jual)
SELECT nama, kelompok, berlaku_sejak, dicatat_pada,
       persen_beli_bp, minimum_beli, persen_jual_bp, minimum_jual
FROM parameter_biaya_broker;

DROP TRIGGER trg_008_jumlah_salinan_biaya_broker;

-- Sisi "berkurang" diperiksa di sini, juga sebelum tabel lama dibuang. `zeroblob(-1)` melempar
-- galat bila dan hanya bila jumlahnya berbeda; bila sama, ekspresinya tidak pernah dievaluasi.
CREATE TEMP TABLE salinan_biaya_broker_008 (baru INTEGER, lama INTEGER);
INSERT INTO salinan_biaya_broker_008
SELECT (SELECT COUNT(*) FROM parameter_biaya_broker_baru),
       (SELECT COUNT(*) FROM parameter_biaya_broker);

CREATE TEMP TRIGGER trg_008_salinan_utuh
BEFORE UPDATE ON salinan_biaya_broker_008
WHEN OLD.baru <> OLD.lama
BEGIN
    SELECT RAISE(ABORT, 'migrasi 008: penyalinan parameter_biaya_broker kehilangan baris');
END;

UPDATE salinan_biaya_broker_008 SET baru = baru;

DROP TRIGGER trg_008_salinan_utuh;
DROP TABLE salinan_biaya_broker_008;

DROP TABLE parameter_biaya_broker;
ALTER TABLE parameter_biaya_broker_baru RENAME TO parameter_biaya_broker;

PRAGMA foreign_keys = ON;

-- Bukti, bukan klaim: kunci asing yang yatim membuat migrasi gagal. `foreign_key_check` diam
-- (tanpa baris) bila seluruhnya utuh; jumlah barisnya diperiksa lewat trigger sementara yang
-- sama polanya, sebab `RAISE` tidak sah di luar program trigger.
CREATE TEMP TABLE kunci_asing_008 (yatim INTEGER);
INSERT INTO kunci_asing_008 SELECT COUNT(*) FROM pragma_foreign_key_check;

CREATE TEMP TRIGGER trg_008_kunci_asing_utuh
BEFORE UPDATE ON kunci_asing_008
WHEN OLD.yatim > 0
BEGIN
    SELECT RAISE(ABORT, 'migrasi 008: ada baris parameter yang kunci asingnya yatim');
END;

UPDATE kunci_asing_008 SET yatim = yatim;

DROP TRIGGER trg_008_kunci_asing_utuh;
DROP TABLE kunci_asing_008;

-- ---------------------------------------------------------------------------------------
-- (3) Komponen tarif yang dinyatakan sumber SUDAH TERMASUK (K23). Tabel anak, bukan kolom
--     teks: pertanyaannya "apakah levy sudah termasuk?" dan jawabannya harus bisa ditanyakan
--     mesin. Tanpa ini, tarif all-in 0,25% dijumlahkan dua kali dengan B8 (0,1%).
-- ---------------------------------------------------------------------------------------
CREATE TABLE parameter_biaya_broker_termasuk (
    nama           TEXT    NOT NULL,
    kelompok       TEXT    NOT NULL,
    berlaku_sejak  TEXT    NOT NULL,
    dicatat_pada   TEXT    NOT NULL,
    komponen       TEXT    NOT NULL CHECK (komponen IN ({", ".join(repr(nilai) for nilai in KOMPONEN_BIAYA_BROKER_TERMASUK)})),
    PRIMARY KEY (nama, kelompok, berlaku_sejak, dicatat_pada, komponen),
    FOREIGN KEY (nama, kelompok, berlaku_sejak, dicatat_pada)
        REFERENCES parameter_biaya_broker (nama, kelompok, berlaku_sejak, dicatat_pada),
    CHECK (nama = 'biaya_broker'),
    CHECK (kelompok <> '')
) STRICT;
"""

_TABEL_APPEND_ONLY_008 = ("parameter_biaya_broker_termasuk",)


# ---------------------------------------------------------------------------------------
# Migrasi 009 — kandidat & watchlist (F4, PRD 9.6). Tahap 2 langkah 1.
# ---------------------------------------------------------------------------------------
# Kenapa revisi, bukan baris yang disunting: PRD 9.8 menuntut "tidak ada penghapusan senyap",
# dan tesis adalah satu-satunya isi basis data ini yang **tidak bisa dibangun ulang dari sumber
# mana pun** (PRD 9.12). Kalau status dan tesis boleh ditimpa, jejak "apa yang saya yakini waktu
# itu" hilang — dan justru itulah yang dinilai di rekap kepatuhan (PRD 13.1).
#
# Kenapa kolom wajibnya dijaga CHECK, bukan hanya oleh modul Python: AC-4 adalah kriteria
# penerimaan, bukan saran. Modul `kandidat.py` memeriksa lebih dulu supaya pesannya menyebut
# kolom yang kurang; CHECK-nya yang membuat aturan itu tetap berlaku pada penulisan mana pun.
_SQL_009 = """
CREATE TABLE kandidat (
    id_kandidat          INTEGER NOT NULL,
    revisi               INTEGER NOT NULL CHECK (revisi >= 1),
    kode                 TEXT    NOT NULL,
    status               TEXT    NOT NULL
                                 CHECK (status IN ('ide', 'watchlist', 'rencana', 'posisi', 'dibuang')),
    -- Isian manusia. NULL = belum diisi; string kosong ditolak oleh CHECK di bawah, sebab
    -- " " bukan tesis dan tidak boleh lolos sebagai kelengkapan (AC-4).
    tesis                TEXT,
    pembatal_fundamental TEXT,
    harga_pembatal       INTEGER CHECK (harga_pembatal IS NULL OR harga_pembatal > 0),
    horizon              TEXT,
    target               INTEGER CHECK (target IS NULL OR target > 0),
    stop_awal            INTEGER CHECK (stop_awal IS NULL OR stop_awal > 0),
    tanggal_tinjau       TEXT    CHECK (tanggal_tinjau IS NULL
                                        OR tanggal_tinjau GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    alasan_dibuang       TEXT,
    dicatat_pada         TEXT    NOT NULL CHECK (dicatat_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),

    -- AC-4: tesis, pembatal fundamental, horizon, stop awal, dan tanggal tinjau wajib terisi
    -- sebelum entri boleh berstatus watchlist — dan tetap wajib sesudahnya (rencana, posisi).
    -- `ide` sengaja dikecualikan: PRD 9.6 menyebut ide sebagai "belum ada tesis". `dibuang`
    -- juga, sebab entri yang dibuang justru sering dibuang **karena** tesisnya tidak pernah
    -- lengkap; menuntut kelengkapannya akan membuat pembuangan yang jujur jadi mustahil.
    CHECK (
        status IN ('ide', 'dibuang')
        OR (
            tesis                IS NOT NULL AND trim(tesis)                <> ''
            AND pembatal_fundamental IS NOT NULL AND trim(pembatal_fundamental) <> ''
            AND horizon              IS NOT NULL AND trim(horizon)              <> ''
            AND stop_awal            IS NOT NULL
            AND tanggal_tinjau       IS NOT NULL
        )
    ),

    -- PRD 9.6: "Dibuang disertai alasan." Entri yang hilang tanpa alasan tidak bisa dibedakan
    -- dari entri yang tidak sengaja terhapus.
    CHECK (status <> 'dibuang' OR (alasan_dibuang IS NOT NULL AND trim(alasan_dibuang) <> '')),

    PRIMARY KEY (id_kandidat, revisi)
) STRICT;

CREATE INDEX ix_kandidat_kode ON kandidat (kode);
"""

_TABEL_APPEND_ONLY_009 = ("kandidat",)

#: Tampilan revisi terakhir `kandidat` **ditulis eksplisit**, tidak memakai pembangkit view yang
#: mengurutkan lewat `dicatat_pada`. Alasannya ditemukan uji: dua revisi yang ditulis dalam detik
#: yang sama (stempel waktu berpresisi detik) menjadi **tidak terbedakan**, dan yang terbaca
#: kembali justru revisi lama. Tabel ini sudah punya kolom `revisi` yang naik satu per perubahan —
#: itulah pembeda yang benar, dan ia tidak bergantung pada resolusi jam.
_SQL_009_TAMPILAN = """
CREATE VIEW v_kandidat_terkini AS
SELECT *
FROM kandidat AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM kandidat AS lain
    WHERE lain.id_kandidat = r.id_kandidat
      AND lain.revisi > r.revisi
);
"""


# ---------------------------------------------------------------------------------------
# Migrasi 010 — batas risiko, ekuitas harian, dan rencana (F5, PRD 8.1/8.3/9.7). Tahap 2 langkah 2.
# ---------------------------------------------------------------------------------------
# Kenapa batas risiko jadi tabel berversi, bukan konstanta di `risiko.py`: PRD 8.3 menetapkan
# ambang, batas risiko, dan asumsi biaya sebagai **pengaturan awal yang bisa diubah**, dan
# "setiap perubahan menaikkan versi preset". Batas yang tertanam di kode akan berubah diam-diam
# setiap kali aplikasi diperbarui — dan rencana lama akan tampak dibuat dengan aturan yang tidak
# pernah berlaku. Karena itu `rencana` menyimpan `id_preset_risiko` yang benar-benar dipakainya.
#
# Kenapa `preset_risiko` dipisah dari `preset_saring`: yang pertama mengatur **ukuran posisi**
# (F5), yang kedua mengatur **pemilihan emiten** (F2/F3). Menggabungkannya membuat menaikkan
# ambang saringan menuntut versi baru untuk batas risiko juga — padahal tidak ada yang berubah.
#
# Kenapa `rencana` berversi seperti `kandidat`: rencana adalah keputusan, dan PRD 9.12 menyebut
# tesis/rencana sebagai isi basis data yang **tidak bisa dibangun ulang dari sumber mana pun**.
# Mengubahnya tanpa menyimpan versi lama akan menghapus "apa yang saya putuskan waktu itu" —
# tepat angka yang dipakai menilai kepatuhan belakangan (PRD 13.1, V2/V3).
#
# Kenapa `maks_lembar_*` boleh NULL: NULL berarti **batas itu tidak dapat dinilai** (mis. ADTV20
# emiten itu "tidak dihitung", atau `sektor_idx_ic` belum terisi), bukan "batasnya longgar" —
# pola yang sama dengan `minimum` tarif broker (K22). Tanpa pembeda itu, rencana yang lolos
# karena datanya tidak ada akan terbaca sama dengan rencana yang lolos karena benar.
_SQL_010 = """
-- Batas risiko portofolio (PRD 8.3, nilai awalnya di 9.7 "Batas bawaan").
CREATE TABLE preset_risiko (
    id_preset_risiko TEXT    NOT NULL CHECK (length(trim(id_preset_risiko)) > 0),
    nama             TEXT    NOT NULL CHECK (length(trim(nama)) > 0),
    versi            INTEGER NOT NULL CHECK (versi > 0),
    keterangan       TEXT,
    dibuat_pada      TEXT    NOT NULL CHECK (dibuat_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    PRIMARY KEY (id_preset_risiko),
    UNIQUE (nama, versi)
) STRICT;

-- Nilai batasnya, satu baris per batas. Kelima nama ini yang dikenal kalkulator risiko; nama
-- lain ditolak CHECK, sebab batas yang tidak dikenal tidak akan pernah dinilai dan diam-diam
-- membuat ukuran posisi lolos.
CREATE TABLE preset_risiko_nilai (
    id_preset_risiko TEXT    NOT NULL REFERENCES preset_risiko (id_preset_risiko),
    nama             TEXT    NOT NULL CHECK (nama IN (
                                 'risiko_per_posisi', 'bobot_maksimum', 'bobot_sektor_maksimum',
                                 'likuiditas_maksimum', 'total_risiko_maksimum')),
    nilai_bp         INTEGER NOT NULL CHECK (nilai_bp > 0 AND nilai_bp <= 10000),
    PRIMARY KEY (id_preset_risiko, nama)
) STRICT;

-- Ekuitas harian (F11 dasar, PRD 9.11) — masukan kalkulator risiko (PRD 9.7 "ekuitas
-- portofolio"). Append-only per tanggal: koreksi menambah baris baru, dan pembacaan memakai
-- revisi terakhir.
--
-- Pembeda revisinya kolom `revisi`, **bukan** stempel waktu: dua pencatatan dalam detik yang
-- sama (skrip, atau dua perintah berturut-turut) akan bertabrakan di kunci utama kalau
-- `diketahui_pada` yang jadi pembeda — kelas cacat yang sama dengan `v_kandidat_terkini` (T37).
-- `diketahui_pada` tetap disimpan sebagai keterangan kapan barisnya dicatat.
--
-- `kas` boleh NULL, dan itu berbeda artinya dari 0: NULL = "kas belum dicatat", 0 = "kas benar-
-- benar kosong". Batas kas yang tidak dicatat membuat batas itu TIDAK DINILAI (aturan keras 2),
-- bukan dianggap longgar sampai tak terhingga.
CREATE TABLE ekuitas_harian (
    tanggal        TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    revisi         INTEGER NOT NULL CHECK (revisi >= 1),
    ekuitas        INTEGER NOT NULL CHECK (ekuitas > 0),
    kas            INTEGER CHECK (kas IS NULL OR kas >= 0),
    catatan        TEXT,
    sumber         TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (tanggal, revisi)
) STRICT;

-- Rencana ukuran posisi (PRD 8.1 & 9.7) — keluaran kalkulator risiko.
--
-- `lembar` **tidak** dijaga CHECK kelipatan lot: lot adalah parameter bursa bertanggal (K1),
-- bukan konstanta yang boleh ditanam di skema. Yang menjaganya `risiko.py`, dan ujinya menembak
-- modul itu — bukan tabelnya. Sebaliknya `stop < harga_masuk` dijaga di sini, sebab posisi ini
-- hanya beli (long): stop di atas harga masuk berarti risiko negatif, dan itu selalu salah.
CREATE TABLE rencana (
    id_rencana             INTEGER NOT NULL,
    revisi                 INTEGER NOT NULL CHECK (revisi >= 1),
    id_kandidat            INTEGER NOT NULL,
    kode                   TEXT    NOT NULL,
    id_preset_risiko       TEXT    NOT NULL REFERENCES preset_risiko (id_preset_risiko),
    id_snapshot            INTEGER NOT NULL REFERENCES snapshot (id_snapshot),
    tanggal                TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    ekuitas                INTEGER NOT NULL CHECK (ekuitas > 0),
    risiko_per_posisi_bp   INTEGER NOT NULL CHECK (risiko_per_posisi_bp > 0 AND risiko_per_posisi_bp <= 10000),
    harga_masuk            INTEGER NOT NULL CHECK (harga_masuk > 0),
    stop                   INTEGER NOT NULL CHECK (stop > 0),
    -- Dari mana `stop` datang: rumus PRD 9.7 (harga masuk − 2 × ATR14), pembatal tesis, atau
    -- isian pengguna. Tanpa kolom ini, angka stop tidak bisa ditelusuri asalnya.
    dasar_stop             TEXT    NOT NULL CHECK (dasar_stop IN (
                                       'harga_masuk_minus_2_atr14', 'harga_pembatal', 'pengguna')),
    biaya_slippage         INTEGER NOT NULL CHECK (biaya_slippage >= 0),
    -- Ukuran mentah disimpan dalam **mili-lembar** (seperseribu lembar): hasil pembagiannya
    -- berpecahan, dan memaksanya jadi bilangan bulat akan membuat rencana tidak bisa diperiksa
    -- ulang dari angkanya sendiri.
    lembar_mentah_mili     INTEGER NOT NULL CHECK (lembar_mentah_mili >= 0),
    lembar                 INTEGER NOT NULL CHECK (lembar >= 0),
    -- Batas per sisi; NULL = batas itu **tidak dapat dinilai** (lihat catatan di atas).
    maks_lembar_bobot      INTEGER NOT NULL CHECK (maks_lembar_bobot >= 0),
    maks_lembar_sektor     INTEGER CHECK (maks_lembar_sektor IS NULL OR maks_lembar_sektor >= 0),
    maks_lembar_likuiditas INTEGER CHECK (maks_lembar_likuiditas IS NULL OR maks_lembar_likuiditas >= 0),
    maks_lembar_kas        INTEGER CHECK (maks_lembar_kas IS NULL OR maks_lembar_kas >= 0),
    bobot_bp               INTEGER NOT NULL CHECK (bobot_bp >= 0),
    risiko_nominal         INTEGER NOT NULL CHECK (risiko_nominal >= 0),
    risiko_berjalan        INTEGER NOT NULL CHECK (risiko_berjalan >= 0),
    total_risiko_bp        INTEGER NOT NULL CHECK (total_risiko_bp >= 0),
    -- Q9: pengguna memilih jenis stop per rencana.
    jenis_stop             TEXT    NOT NULL CHECK (jenis_stop IN ('order_sekuritas', 'cek_penutupan')),
    -- Alasan batas yang tidak dapat dinilai, supaya sebabnya ikut tersimpan (aturan keras 7).
    batas_tidak_dinilai    TEXT,
    catatan                TEXT,
    dicatat_pada           TEXT    NOT NULL CHECK (dicatat_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (id_rencana, revisi),
    CHECK (stop < harga_masuk)
) STRICT;

CREATE INDEX ix_rencana_kode ON rencana (kode);

CREATE INDEX ix_ekuitas_harian_tanggal ON ekuitas_harian (tanggal);
"""

_TABEL_APPEND_ONLY_010 = (
    "preset_risiko",
    "preset_risiko_nilai",
    "ekuitas_harian",
    "rencana",
)

#: Sama alasannya dengan `_SQL_009_TAMPILAN`: pembeda revisi `rencana` adalah kolom `revisi`,
#: bukan stempel waktu — dua revisi dalam detik yang sama tidak boleh saling menutupi (T37).
_SQL_010_TAMPILAN = """
CREATE VIEW v_rencana_terkini AS
SELECT *
FROM rencana AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM rencana AS lain
    WHERE lain.id_rencana = r.id_rencana
      AND lain.revisi > r.revisi
);

CREATE VIEW v_ekuitas_harian_terkini AS
SELECT *
FROM ekuitas_harian AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM ekuitas_harian AS lain
    WHERE lain.tanggal = r.tanggal
      AND lain.revisi > r.revisi
);
"""


# ---------------------------------------------------------------------------------------
# Migrasi 011 — kolom sektor KEDUA dari sumber data (K25, PRD 9.7). Tahap 2 langkah 2b.
# ---------------------------------------------------------------------------------------
# Kenapa kolom baru, bukan mengisi `sektor_idx_ic`: K12 sudah memutuskan kolom itu **khusus
# IDX-IC**, dan sumber EOD memakai taksonomi lain. Mengisinya dengan taksonomi sumber akan membuat
# dua hal yang berbeda tampak sama — dan akibatnya bukan tampilan melainkan **angka**: batas bobot
# per sektor (PRD 9.7) serta median sektor (PRD 8.2) akan dihitung dari kelompok yang bukan
# kelompoknya, tanpa satu pun galat.
#
# Kenapa cukup `ALTER TABLE ADD COLUMN`: `emiten` append-only berkunci `(kode, diketahui_pada)`,
# jadi kolom baru langsung punya tempat di setiap revisi berikutnya, dan `v_emiten_terkini`
# (`SELECT *`) ikut memuatnya tanpa dibangun ulang. Baris lama bernilai NULL — dan NULL berarti
# "sumber belum menyatakannya", bukan "tidak ada sektor" (aturan keras 2).
_SQL_011 = """
ALTER TABLE emiten ADD COLUMN sektor_sumber TEXT;
"""


#: Mode transaksi & posisi (PRD 9.11). **Dipinjam** modul (`risiko.py`, `posisi.py`), bukan
#: disalin: CHECK di migrasi 012 dan pemeriksaan modul harus sepakat, dan nilai yang sah hanya
#: boleh punya satu tempat. Teks SQL migrasinya sendiri sengaja literal — migrasi yang sudah
#: terpasang tidak boleh berubah isinya, jadi ia tidak boleh ikut berubah kalau daftar ini
#: disunting (T9); `tests/test_db.py` yang menjaga keduanya tetap sepakat.
MODE_SAH: tuple[str, ...] = ("simulasi", "nyata")

#: Keputusan manual atas right issue (PRD 9.11: *"tebus, jual HMETD, atau abaikan"*). **Dipinjam**
#: modul (`posisi.py`), bukan disalin — sama alasannya dengan `MODE_SAH`. Teks SQL migrasi 013
#: sengaja literal (migrasi yang sudah terpasang tidak boleh berubah isinya, T9), dan
#: `tests/test_db.py` yang menjaga keduanya tetap sepakat.
KEPUTUSAN_RIGHT_ISSUE_SAH: tuple[str, ...] = ("tebus", "jual_hmetd", "abaikan")


# ---------------------------------------------------------------------------------------
# Migrasi 012 — transaksi & posisi (F11, PRD 8.1/9.11). Tahap 2 langkah 3.
# ---------------------------------------------------------------------------------------
# Kenapa `transaksi` berversi (`revisi`), bukan peristiwa append-only seperti `snapshot`:
# PRD 9.8 menetapkan "mengubah isi jurnal lama diperbolehkan hanya dengan menyimpan versi
# sebelumnya; tidak ada penghapusan senyap", dan `transaksi` adalah **dasar jurnal** itu
# (PRD 12). Transaksi yang salah ketik harus bisa diperbaiki tanpa menghapus angka yang salah
# dari riwayat: kalau barisnya ditimpa, "apa yang saya catat waktu itu" hilang — dan justru itu
# yang dinilai di rekap kepatuhan (PRD 13.1, pelanggaran V2/V6).
#
# Kenapa `posisi` **tidak** menyimpan `lembar` dan `harga_rata` walaupun PRD 12 menyebutnya:
# keduanya turunan dari transaksi, dan menyimpannya berarti ada dua jawaban untuk satu
# pertanyaan — begitu keduanya berbeda, tidak ada cara mengetahui mana yang benar. Yang
# disimpan hanya yang tidak bisa diturunkan dari mana pun: kapan posisi dibuka/ditutup, stop
# terkini (isian manusia; PRD 9.11 "stop terkini boleh dinaikkan"), mode, dan pelanggarannya.
# Pembacaan menurunkannya dari `v_transaksi_terkini`, dan `posisi.py` yang menjadi satu-satunya
# tempat turunan itu dihitung.
#
# Kenapa `stop_terkini` boleh NULL: pelanggaran V1 (PRD 9.8) adalah "masuk tanpa stop awal", dan
# pelanggaran yang mustahil dicatat bukan pelanggaran yang terdeteksi — ia hanya membuat
# pencatatan yang jujur menjadi tidak mungkin. Yang wajib adalah **melaporkannya**, bukan
# melarangnya (pola yang sama dengan `maks_lembar_*` NULL di migrasi 010).
#
# Kenapa `pajak` adalah **bagian** dari `biaya`, bukan tambahan di atasnya: tarif *all-in* K23
# sudah memuat PPh final penjualan (0,1%), sehingga biaya + pajak akan menghitung pajak dua kali
# — kesalahan yang tidak terlihat di keluaran mana pun, hanya di angkanya. `pajak` hanya diisi
# bila bagiannya **dapat dipisahkan** dari sumbernya; NULL berarti "tidak dapat dipisahkan",
# bukan nol.
_SQL_012 = """
-- Siklus hidup satu posisi (PRD 8.1, 9.11 "Manajemen posisi & ekuitas").
CREATE TABLE posisi (
    id_posisi      INTEGER NOT NULL,
    revisi         INTEGER NOT NULL CHECK (revisi >= 1),
    kode           TEXT    NOT NULL CHECK (length(trim(kode)) > 0),
    tgl_buka       TEXT    NOT NULL CHECK (tgl_buka GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    tgl_tutup      TEXT    CHECK (tgl_tutup IS NULL
                                  OR tgl_tutup GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    status         TEXT    NOT NULL CHECK (status IN ('aktif', 'ditutup')),
    -- NULL = posisinya berjalan tanpa stop. Itu pelanggaran V1 yang **dicatat**, bukan keadaan
    -- yang dicegah: yang dicegah adalah pelanggaran yang tidak terlihat.
    stop_terkini   INTEGER CHECK (stop_terkini IS NULL OR stop_terkini > 0),
    -- Rencana yang melahirkan posisi ini; NULL = dibuka tanpa rencana tersimpan (V6).
    id_rencana     INTEGER,
    -- PRD 9.11: setiap transaksi dan posisi bertanda simulasi atau nyata. Tidak boleh NULL:
    -- metrik kedua mode dilaporkan terpisah (PRD 9.11), dan mode yang tidak dinyatakan akan
    -- membuat pemisahan itu mustahil dilakukan belakangan.
    mode           TEXT    NOT NULL CHECK (mode IN ('simulasi', 'nyata')),
    -- Kode pelanggaran yang terdeteksi saat baris ini ditulis (V1, V5, ...), dipisah ';'.
    pelanggaran    TEXT,
    catatan        TEXT,
    sumber         TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (id_posisi, revisi),
    -- Status dan tanggal tutup harus sepakat: posisi "ditutup" tanpa tanggal tidak bisa
    -- dibedakan dari posisi yang lupa ditutup, dan tanggal tutup pada posisi aktif akan
    -- membuat "posisi aktif" berarti dua hal.
    CHECK (status <> 'ditutup' OR tgl_tutup IS NOT NULL),
    CHECK (status <> 'aktif' OR tgl_tutup IS NULL),
    CHECK (tgl_tutup IS NULL OR tgl_tutup >= tgl_buka)
) STRICT;

CREATE INDEX ix_posisi_kode ON posisi (kode);

-- Satu eksekusi manual yang dicatat (PRD 8.1, 9.11). `dasar jurnal dan rekap` (PRD 12).
CREATE TABLE transaksi (
    id_transaksi   INTEGER NOT NULL,
    revisi         INTEGER NOT NULL CHECK (revisi >= 1),
    id_posisi      INTEGER NOT NULL,
    -- Rencana yang dieksekusi transaksi ini. NULL = tanpa rencana tersimpan -> pelanggaran V6
    -- (PRD 9.8), dicatat di kolom `pelanggaran`, bukan ditolak: eksekusi yang sudah terjadi di
    -- sekuritas tetap harus bisa dicatat apa adanya.
    id_rencana     INTEGER,
    tanggal        TEXT    NOT NULL CHECK (tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    kode           TEXT    NOT NULL CHECK (length(trim(kode)) > 0),
    -- PRD 5: hanya posisi beli (long); tidak ada short, margin, atau derivatif.
    aksi           TEXT    NOT NULL CHECK (aksi IN ('beli', 'jual')),
    harga          INTEGER NOT NULL CHECK (harga > 0),
    lembar         INTEGER NOT NULL CHECK (lembar > 0),
    -- Seluruh biaya transaksi (rupiah). NULL = belum dicatat, dan itu **dilaporkan** karena
    -- hasil bersih yang dihitung tanpanya akan tampak lebih baik daripada kenyataan.
    biaya          INTEGER CHECK (biaya IS NULL OR biaya >= 0),
    asal_biaya     TEXT    CHECK (asal_biaya IS NULL
                                  OR asal_biaya IN ('dicatat_pengguna', 'dihitung_dari_tarif')),
    -- Bagian dari `biaya` yang merupakan PPh final penjualan; NULL = tidak dapat dipisahkan.
    pajak          INTEGER CHECK (pajak IS NULL OR pajak >= 0),
    mode           TEXT    NOT NULL CHECK (mode IN ('simulasi', 'nyata')),
    pelanggaran    TEXT,
    catatan        TEXT,
    sumber         TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (id_transaksi, revisi),
    -- `pajak` BUKAN tambahan: ia bagian dari `biaya`. Tanpa penjaga ini, laporan yang menjumlah
    -- keduanya akan menghitung PPh dua kali pada tarif all-in (K23).
    CHECK (pajak IS NULL OR biaya IS NULL OR pajak <= biaya),
    -- Biaya yang tidak menyatakan asalnya tidak bisa diperiksa: ia bisa jadi biaya sungguhan
    -- yang dicatat pengguna, bisa juga hasil hitungan tarif. Keduanya menuntut tindakan berbeda
    -- begitu angkanya dipertanyakan.
    CHECK ((biaya IS NULL) = (asal_biaya IS NULL))
) STRICT;

CREATE INDEX ix_transaksi_kode ON transaksi (kode);

CREATE INDEX ix_transaksi_posisi ON transaksi (id_posisi);

-- PRD 9.11: setoran/penarikan dana adalah masukan F11, dan AC-13 menuntut drawdown **tidak
-- berubah** karenanya. Karena itu arus dananya disimpan di baris ekuitas yang sama.
--
-- `arus_dana` NULL = "belum dicatat", 0 = "benar-benar tidak ada setoran/penarikan" — dua
-- keadaan yang berbeda, dan bedanya bukan hiasan: deret ekuitas yang arus dananya tidak
-- diketahui tidak boleh dikoreksi, sebab mengoreksinya dengan nol berarti menganggap setoran
-- sebagai keuntungan. `mode` NULL = belum dinyatakan (baris lama tidak boleh diberi label yang
-- tidak pernah dipilih pengguna); PRD 9.11 menuntut kedua mode dilaporkan terpisah.
ALTER TABLE ekuitas_harian ADD COLUMN arus_dana INTEGER;

ALTER TABLE ekuitas_harian ADD COLUMN mode TEXT
    CHECK (mode IS NULL OR mode IN ('simulasi', 'nyata'));
"""

_TABEL_APPEND_ONLY_012 = ("posisi", "transaksi")

#: Sama alasannya dengan `_SQL_009_TAMPILAN`/`_SQL_010_TAMPILAN`: pembeda revisinya kolom
#: `revisi`, bukan stempel waktu — dua revisi dalam detik yang sama tidak boleh saling menutupi
#: (T37). `id_posisi`/`id_rencana` sengaja **tanpa** kunci asing, mengikuti `rencana.id_kandidat`:
#: yang dijaga modul (pesannya menyebut kode dan id-nya), dan kunci asing di sini akan menolak
#: baris yang urutan penulisannya sah.
_SQL_012_TAMPILAN = """
CREATE VIEW v_posisi_terkini AS
SELECT *
FROM posisi AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM posisi AS lain
    WHERE lain.id_posisi = r.id_posisi
      AND lain.revisi > r.revisi
);

CREATE VIEW v_transaksi_terkini AS
SELECT *
FROM transaksi AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM transaksi AS lain
    WHERE lain.id_transaksi = r.id_transaksi
      AND lain.revisi > r.revisi
);
"""


# ---------------------------------------------------------------------------------------
# Migrasi 013 — aksi korporasi pada posisi (F11, PRD 9.11). Tahap 2 langkah 4.
# ---------------------------------------------------------------------------------------
# Kenapa hampir seluruhnya **diturunkan**, bukan disimpan: PRD 9.11 menuntut "split dan reverse
# split menyesuaikan lembar dan stop **otomatis**", dan PRD 7.2 sudah menetapkan pola yang sama
# untuk harga ("disimpan mentah, penyesuaian dihitung saat dibaca"). Menyimpan lembar yang sudah
# disesuaikan berarti ada dua jawaban untuk satu pertanyaan: begitu ada split baru, yang tersimpan
# dan yang diturunkan berbeda, dan tidak ada cara mengetahui mana yang benar. Yang menanggung
# risikonya adalah angka yang dipakai menghitung risiko posisi.
#
# Karena itu yang ditambahkan di sini hanya yang **tidak bisa** diturunkan dari mana pun:
#
#   (1) `aksi_korporasi.tenggat` — batas waktu pelaksanaan right issue. Sumber data EOD tidak
#       menerbitkannya, jadi ia hanya bisa datang dari pengumuman atau dari pengguna. NULL berarti
#       "belum dinyatakan sumbernya" (aturan keras 2) — berbeda dari "tidak ada tenggat".
#
#   (2) `posisi.tgl_stop` — **basis** level stop: tanggal harga yang dipakai saat stop itu
#       dinyatakan. `stop_terkini` adalah angka yang dicatat manusia (mis. "stop saya 2.180"), dan
#       artinya bergantung pada basis harga saat itu. Tanpa kolom ini, split yang terjadi *sesudah*
#       stop dicatat tidak bisa dibedakan dari split yang **sudah** tercermin di dalam angka itu —
#       dan menebaknya berarti salah satu dari dua kemungkinan dipilih diam-diam.
#
#   (3) `keputusan_right_issue` — keputusan manual PRD 9.11 (tebus, jual HMETD, atau abaikan).
#       Keputusan bukan turunan data: ia tindakan manusia, dan ia yang diminta PRD 9.11.
_sql_013 = """
-- Batas waktu pelaksanaan right issue (mis. batas akhir penebusan HMETD). NULL = belum
-- dinyatakan sumbernya. Bertanggal, sebab tenggat tanpa tanggal tidak bisa dinilai lewatnya.
ALTER TABLE aksi_korporasi ADD COLUMN tenggat TEXT
    CHECK (tenggat IS NULL OR tenggat GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]');

-- Basis tanggal level stop. NULL = baris lama (sebelum migrasi ini) yang belum menyatakannya;
-- `posisi.py` yang memutuskan apa artinya, dan ia **tidak** menebaknya (lihat modul itu).
ALTER TABLE posisi ADD COLUMN tgl_stop TEXT
    CHECK (tgl_stop IS NULL OR tgl_stop GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]');

-- Keputusan manual atas satu right issue pada satu posisi (PRD 9.11). Berversi seperti `posisi`
-- dan `transaksi`: keputusan boleh berubah, tetapi yang lama tidak boleh hilang.
--
-- Kenapa `tebus` **wajib** menunjuk transaksi: menebus HMETD berarti membeli lembar baru, dan
-- lembarnya sudah punya satu tempat — `transaksi`. Menyalin `lembar`/`harga` ke sini akan membuat
-- dua catatan untuk satu pembelian, dan begitu keduanya berbeda, jumlah lembar posisi menjadi
-- pertanyaan terbuka. Yang tidak punya tempat lain hanyalah `jual_hmetd`: menjual **hak** bukan
-- menjual lembar, sehingga transaksi saham justru akan mengurangi lembar yang sebenarnya masih
-- dipegang. Karena itu hanya di situ `lembar`/`harga` disimpan.
CREATE TABLE keputusan_right_issue (
    id_keputusan   INTEGER NOT NULL,
    revisi         INTEGER NOT NULL CHECK (revisi >= 1),
    id_posisi      INTEGER NOT NULL,
    kode           TEXT    NOT NULL CHECK (length(trim(kode)) > 0),
    -- Tanggal aksi korporasinya (`aksi_korporasi.tanggal`), yaitu kunci alami right issue yang
    -- diputuskan. Disimpan apa adanya supaya keputusan bisa ditelusuri ke baris aksinya.
    tanggal_aksi   TEXT    NOT NULL CHECK (tanggal_aksi GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    keputusan      TEXT    NOT NULL CHECK (keputusan IN ('tebus', 'jual_hmetd', 'abaikan')),
    id_transaksi   INTEGER,
    lembar         INTEGER CHECK (lembar IS NULL OR lembar > 0),
    harga          INTEGER CHECK (harga IS NULL OR harga > 0),
    biaya          INTEGER CHECK (biaya IS NULL OR biaya >= 0),
    catatan        TEXT,
    sumber         TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (id_keputusan, revisi),
    -- `tebus` tanpa transaksi berarti lembar yang ditebus tidak masuk ke buku mana pun.
    CHECK ((keputusan = 'tebus') = (id_transaksi IS NOT NULL)),
    -- Menjual hak menuntut jumlah dan harganya; keduanya tidak bisa diturunkan dari data.
    CHECK (keputusan <> 'jual_hmetd' OR (lembar IS NOT NULL AND harga IS NOT NULL)),
    CHECK (keputusan = 'jual_hmetd' OR (lembar IS NULL AND harga IS NULL AND biaya IS NULL))
) STRICT;

CREATE INDEX ix_keputusan_right_issue_posisi ON keputusan_right_issue (id_posisi);
"""

_TABEL_APPEND_ONLY_013 = ("keputusan_right_issue",)

#: Sama alasannya dengan `_SQL_009_TAMPILAN`/`_SQL_012_TAMPILAN`: pembeda revisinya kolom
#: `revisi`, bukan stempel waktu.
_SQL_013_TAMPILAN = """
CREATE VIEW v_keputusan_right_issue_terkini AS
SELECT *
FROM keputusan_right_issue AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM keputusan_right_issue AS lain
    WHERE lain.id_keputusan = r.id_keputusan
      AND lain.revisi > r.revisi
);
"""


# ---------------------------------------------------------------------------------------
# Migrasi 014 — jurnal keputusan (F7, PRD 9.8/11.5/12). Tahap 3 langkah 1.
# ---------------------------------------------------------------------------------------
# Kenapa tabelnya **hanya** memuat yang tidak bisa diturunkan dari mana pun: PRD 12 menyebut
# `jurnal` dengan kolom `tanggal`, `kode`, `patuh_aturan`, dan `kode_pelanggaran`. Keempatnya
# sudah punya tempatnya sendiri — `tanggal`/`kode` di baris `transaksi` yang diannotasi, dan
# kepatuhan di baris tempat pelanggarannya **dideteksi** (V1/V2/V6 di `transaksi`, V5 di
# `posisi`). Menyalinnya ke sini akan memberi dua jawaban untuk satu pertanyaan: begitu
# transaksinya direvisi — dan revisi itu justru diizinkan PRD 9.8 — salinan di jurnal tetap
# berbunyi lama tanpa satu pun tanda. Pola yang sama sudah dipakai `posisi` (migrasi 012):
# yang disimpan hanya yang tidak bisa diturunkan. Kepatuhan dihitung di `jurnal.py`, satu
# tempat, dan `jurnal.Patuh` tidak pernah tersimpan.
#
# Kenapa `id_transaksi` **bukan** kunci asing: pola yang sama dengan `rencana.id_kandidat` —
# yang menjaganya modul (pesannya menyebut id-nya), dan kunci asing akan menolak urutan
# penulisan yang sah.
#
# Kenapa satu transaksi hanya boleh punya SATU rantai `id_jurnal`: PRD 9.8 "baris jurnal per
# keputusan", dan K34 menetapkan keputusan yang dinilai adalah transaksi. Dua rantai untuk satu
# keputusan akan membuat "pelajaran"-nya tersebar di dua tempat, dan tidak ada cara mengetahui
# mana yang berlaku. Dijaga trigger, bukan disiplin.
#
# Kenapa baris kosong ditolak: baris jurnal tanpa alasan, pelajaran, tanggal tinjau, maupun
# penanda selesai tidak mencatat apa pun — ia hanya menambah baris yang harus dibaca manusia
# untuk tahu bahwa isinya tidak ada.
_SQL_014 = """
CREATE TABLE jurnal (
    id_jurnal      INTEGER NOT NULL,
    revisi         INTEGER NOT NULL CHECK (revisi >= 1),
    -- Keputusan yang diannotasi (PRD 9.8, K34: yang dinilai adalah transaksi).
    id_transaksi   INTEGER NOT NULL,
    alasan         TEXT,
    pelajaran      TEXT,
    tanggal_tinjau TEXT CHECK (tanggal_tinjau IS NULL
                               OR tanggal_tinjau GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    -- PRD 11.5 "[Tandai selesai]": tanggal entri jurnal ini selesai ditinjau.
    selesai_pada   TEXT CHECK (selesai_pada IS NULL
                               OR selesai_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    sumber         TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada TEXT    NOT NULL CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (id_jurnal, revisi),
    CHECK (alasan IS NOT NULL OR pelajaran IS NOT NULL
           OR tanggal_tinjau IS NOT NULL OR selesai_pada IS NOT NULL)
) STRICT;

CREATE INDEX ix_jurnal_transaksi ON jurnal (id_transaksi);

CREATE TRIGGER trg_jurnal_satu_rantai_per_transaksi
BEFORE INSERT ON jurnal
WHEN EXISTS (
    SELECT 1
    FROM jurnal
    WHERE id_transaksi = NEW.id_transaksi
      AND id_jurnal <> NEW.id_jurnal
)
BEGIN
    SELECT RAISE(ABORT, 'jurnal: satu transaksi hanya boleh punya SATU rantai jurnal. Menambah catatan berarti menambah REVISI pada rantai itu, supaya versi sebelumnya tidak hilang (PRD 9.8)');
END;
"""

_TABEL_APPEND_ONLY_014 = ("jurnal",)

#: Sama alasannya dengan `_SQL_009_TAMPILAN`/`_SQL_012_TAMPILAN`: pembeda revisinya kolom
#: `revisi`, bukan stempel waktu — dua revisi dalam detik yang sama tidak boleh saling menutupi.
_SQL_014_TAMPILAN = """
CREATE VIEW v_jurnal_terkini AS
SELECT *
FROM jurnal AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM jurnal AS lain
    WHERE lain.id_jurnal = r.id_jurnal
      AND lain.revisi > r.revisi
);
"""


# ---------------------------------------------------------------------------------------
# Migrasi 015 — konteks pasar tersimpan (K61; PRD 8.2/11.1)
#
# Kenapa disimpan: konteks pasar adalah fungsi deterministik dari satu snapshot + satu preset.
# `potret.muat` hanya membaca revisi yang sudah diketahui saat snapshot dibuat, jadi menghitung
# ulang untuk snapshot yang sama selalu memberi angka yang sama — dan dasbor membayarnya setiap
# kali dibuka (terukur 33–61 dtk pada basis data 999.421 bar, sedangkan sebelum K58 2,8 dtk).
#
# Kenapa kuncinya `id_snapshot + id_preset + sumber_harga`: angka milik snapshot, preset, atau
# label harga lain bukan keadaan halaman ini. P17 menetapkan satu label harga per hitungan, jadi
# label yang berbeda memang menghasilkan deret yang berbeda — bukan detail yang boleh diabaikan.
# `sumber_harga` NOT NULL dengan teks kosong = "belum ada label harga" (keadaan yang sah pada
# basis data kosong); NULL di kolom kunci primer SQLite tidak menjamin keunikan.
#
# Kenapa `versi_hitung` ada: perubahan cara membungkus/menghitung konteks harus membatalkan baris
# lama, bukan membuatnya tampak sebanding. Pola yang sama dengan `skor.versi_hitung` (migrasi 004).
#
# Kenapa `catatan` ikut disimpan: tanpa itu, sebab "rezim NETRAL karena bahannya belum lengkap"
# hilang saat angka dibaca dari simpanan — dan kalimat tanpa sebab terbaca sebagai penilaian
# tentang pasar, padahal artinya penilaian tentang data yang belum diimpor.
#
# Kenapa ditulis ulang (bukan append-only): ia turunan deterministik seperti `skor`, bukan data
# yang direvisi manusia. Yang menjaga kejujurannya adalah kunci lengkap + `versi_hitung`.
#
# CHECK-nya menjaga arti, bukan hiasan: `dihitung` wajib punya nilai dan `tidak_dihitung` wajib
# punya alasan (aturan keras 2); breadth adalah rasio 0–1; penutupan indeks wajib lengkap bila
# indeksnya ada.
_SQL_015 = """
CREATE TABLE konteks_pasar (
    id_snapshot       INTEGER NOT NULL REFERENCES snapshot (id_snapshot),
    id_preset         TEXT    NOT NULL REFERENCES preset_saring (id_preset),
    sumber_harga      TEXT    NOT NULL,
    versi_hitung      TEXT    NOT NULL CHECK (length(trim(versi_hitung)) > 0),
    breadth_nilai     REAL    CHECK (breadth_nilai IS NULL
                                     OR (breadth_nilai >= 0 AND breadth_nilai <= 1)),
    breadth_status    TEXT    NOT NULL CHECK (breadth_status IN ('dihitung', 'tidak_dihitung')),
    breadth_alasan    TEXT,
    breadth_asal      TEXT    NOT NULL,
    rezim             TEXT    NOT NULL CHECK (length(trim(rezim)) > 0),
    indeks            TEXT    CHECK (indeks IS NULL OR length(trim(indeks)) > 0),
    indeks_tanggal    TEXT    CHECK (indeks_tanggal IS NULL
                                     OR indeks_tanggal GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    indeks_penutupan  INTEGER CHECK (indeks_penutupan IS NULL OR indeks_penutupan >= 0),
    indeks_penutupan_sebelumnya INTEGER CHECK (indeks_penutupan_sebelumnya IS NULL
                                               OR indeks_penutupan_sebelumnya >= 0),
    catatan           TEXT,
    dihitung_pada     TEXT    NOT NULL CHECK (dihitung_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (id_snapshot, id_preset, sumber_harga),
    CHECK ((breadth_status = 'dihitung') = (breadth_nilai IS NOT NULL)),
    CHECK ((breadth_status = 'tidak_dihitung') = (breadth_alasan IS NOT NULL)),
    CHECK ((indeks IS NULL) = (indeks_tanggal IS NULL)),
    CHECK ((indeks IS NULL) = (indeks_penutupan IS NULL))
) STRICT;
"""


_SQL_016 = """
CREATE TABLE catatan_aksi_mutu (
    kode            TEXT NOT NULL,
    tanggal_efektif TEXT NOT NULL,
    instrumen_aksi  TEXT NOT NULL,
    diketahui_pada  TEXT NOT NULL,
    ringkasan_bukti TEXT NOT NULL,
    sumber_url      TEXT NOT NULL,
    sumber          TEXT NOT NULL,
    PRIMARY KEY (kode, tanggal_efektif, instrumen_aksi, diketahui_pada),
    CHECK (length(trim(kode)) > 0),
    CHECK (tanggal_efektif GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    CHECK (length(trim(instrumen_aksi)) > 0),
    CHECK (length(trim(ringkasan_bukti)) > 0),
    CHECK (length(trim(sumber_url)) > 0),
    CHECK (length(trim(sumber)) > 0)
) STRICT;

CREATE VIEW v_catatan_aksi_mutu_terkini AS
SELECT *
FROM catatan_aksi_mutu AS r
WHERE NOT EXISTS (
    SELECT 1 FROM catatan_aksi_mutu AS lain
    WHERE lain.kode = r.kode
      AND lain.tanggal_efektif = r.tanggal_efektif
      AND lain.instrumen_aksi = r.instrumen_aksi
      AND lain.diketahui_pada > r.diketahui_pada
);
"""


# ---------------------------------------------------------------------------------------
# Migrasi 017 — sambungan harga: harga resmi IDX sejak satu tanggal (K97, P42)
#
# Satu baris = satu **pernyataan** pengguna: "sejak `berlaku_sejak`, harga dibaca dari label
# `sumber_resmi`; sebelumnya dari label riwayat (K14)". Kuncinya `berlaku_sejak`; revisi
# `aktif = 0` mencabut tanggal itu. Yang berlaku adalah tanggal aktif terbesar menurut revisi
# terakhir yang diketahui pada batas snapshot (`potret.sambungan_berlaku`), sehingga snapshot
# lama tetap membaca deret yang sama walau tanggal sambung diubah belakangan (AC-15).
#
# Kenapa tabel data, bukan entri `parameter-bursa.toml`: ini keputusan pengguna tentang sumber,
# bukan parameter bursa dari pengumuman resmi — laporan parameter akan menyebutnya "belum
# terverifikasi, isi dari pengumuman resmi", dan itu kalimat yang salah. `dicatat_pada` TOML juga
# hanya bertanggal, sedangkan point-in-time snapshot butuh ketelitian detik.
_SQL_017 = """
CREATE TABLE sambungan_harga (
    berlaku_sejak  TEXT    NOT NULL
                   CHECK (berlaku_sejak GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    sumber_resmi   TEXT    NOT NULL CHECK (length(trim(sumber_resmi)) > 0),
    aktif          INTEGER NOT NULL CHECK (aktif IN (0, 1)),
    keterangan     TEXT,
    sumber         TEXT    NOT NULL CHECK (length(trim(sumber)) > 0),
    diketahui_pada TEXT    NOT NULL
                   CHECK (diketahui_pada GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    PRIMARY KEY (berlaku_sejak, diketahui_pada)
) STRICT;
"""


# Migrasi 018 (sesi 69): tanggal penutupan pembanding IHSG ikut disimpan. Tanpanya dasbor tidak
# bisa menyebut bahwa perubahannya dihitung terhadap hari yang lebih lama bila bar di antaranya
# kosong (terukur: 29 Okt dibandingkan dengan 27 Okt, terbaca sebagai perubahan harian).
_SQL_018 = """
ALTER TABLE konteks_pasar ADD COLUMN indeks_tanggal_sebelumnya TEXT
    CHECK (indeks_tanggal_sebelumnya IS NULL
           OR indeks_tanggal_sebelumnya GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]');
"""


MIGRASI: tuple[Migrasi, ...] = (
    Migrasi(
        versi=1,
        nama="fondasi_data",
        sql=_SQL_001_TABEL
        + "\n\n"
        + _sql_trigger_append_only(_TABEL_APPEND_ONLY_001)
        + "\n\n"
        + _sql_tampilan_terkini(_KUNCI_REVISI_001)
        + "\n",
    ),
    Migrasi(
        versi=2,
        nama="parameter_bursa_bertanggal",
        sql=_SQL_002_TABEL,
    ),
    Migrasi(
        versi=3,
        nama="penyesuaian_sumber_fundamental_rasio_bank",
        sql=_SQL_003,
    ),
    Migrasi(
        versi=4,
        nama="preset_saring_dan_skor",
        sql=_SQL_004,
    ),
    Migrasi(
        versi=5,
        nama="harga_terkini_per_sumber",
        sql=_sql_005(),
    ),
    Migrasi(
        versi=6,
        nama="catatan_cek_sumber_kedua",
        sql=_SQL_006,
    ),
    Migrasi(
        versi=7,
        nama="asal_tgl_publikasi_fundamental",
        sql=_SQL_007,
    ),
    Migrasi(
        versi=8,
        nama="parameter_bursa_tanpa_dinyatakan_sumber",
        sql=(
            _SQL_008
            + "\n\n"
            + _sql_trigger_append_only(_TABEL_APPEND_ONLY_008)
            + "\n"
        ),
    ),
    Migrasi(
        versi=9,
        nama="kandidat_watchlist",
        sql=(
            _SQL_009
            + "\n\n"
            + _sql_trigger_append_only(_TABEL_APPEND_ONLY_009)
            + "\n\n"
            + _SQL_009_TAMPILAN
            + "\n"
        ),
    ),
    Migrasi(
        versi=10,
        nama="batas_risiko_ekuitas_dan_rencana",
        sql=(
            _SQL_010
            + "\n\n"
            + _sql_trigger_append_only(_TABEL_APPEND_ONLY_010)
            + "\n\n"
            + _SQL_010_TAMPILAN
            + "\n"
        ),
    ),
    Migrasi(
        versi=11,
        nama="sektor_dari_sumber_data",
        sql=_SQL_011,
    ),
    Migrasi(
        versi=12,
        nama="transaksi_dan_posisi",
        sql=(
            _SQL_012
            + "\n\n"
            + _sql_trigger_append_only(_TABEL_APPEND_ONLY_012)
            + "\n\n"
            + _SQL_012_TAMPILAN
            + "\n"
        ),
    ),
    Migrasi(
        versi=13,
        nama="aksi_korporasi_pada_posisi",
        sql=(
            _sql_013
            + "\n\n"
            + _sql_trigger_append_only(_TABEL_APPEND_ONLY_013)
            + "\n\n"
            + _SQL_013_TAMPILAN
            + "\n"
        ),
    ),
    Migrasi(
        versi=14,
        nama="jurnal_kepatuhan",
        sql=(
            _SQL_014
            + "\n\n"
            + _sql_trigger_append_only(_TABEL_APPEND_ONLY_014)
            + "\n\n"
            + _SQL_014_TAMPILAN
            + "\n"
        ),
    ),
    Migrasi(
        versi=15,
        nama="konteks_pasar_tersimpan",
        sql=_SQL_015,
    ),
    Migrasi(
        versi=16,
        nama="catatan_aksi_khusus_mutu_harga",
        sql=(
            _SQL_016
            + "\n\n"
            + _sql_trigger_append_only(("catatan_aksi_mutu",))
            + "\n"
        ),
    ),
    Migrasi(
        versi=17,
        nama="sambungan_harga_resmi",
        sql=_SQL_017 + "\n\n" + _sql_trigger_append_only(("sambungan_harga",)) + "\n",
    ),
    Migrasi(
        versi=18,
        nama="konteks_pasar_tanggal_pembanding",
        sql=_SQL_018,
    ),
)

VERSI_TERBARU = MIGRASI[-1].versi
