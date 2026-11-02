"""Uji penyesuaian harga aksi korporasi saat dibaca (T5, U4, U6) dan penjaga K8/C10.

`mejasaham/penyesuaian.py` adalah modul murni: masukannya baris harga dan daftar aksi korporasi,
keluarannya deret harga yang sebanding. Karena itu seluruh uji di berkas ini berjalan **tanpa
jaringan, tanpa basis data, dan tanpa menunggu apa pun** — tidak ada `sleep`, tidak ada koneksi,
tidak ada jam.

Yang diuji di sini bukan "apakah fungsinya jalan", melainkan janji-janji yang membuat deret harga
boleh dipakai menghitung momentum, volatilitas, dan stop:

* split dan reverse split menggeser harga **sebelum** tanggal aksi ke basis sesudahnya, dan tidak
  menyentuh harga sesudahnya (kalau tidak, separuh deret salah skala);
* baris yang sumbernya **sudah** menyesuaikan split tidak disesuaikan dua kali (K8/C10 — inilah
  yang membuat harga BBCA tidak dibagi 5 untuk kedua kalinya);
* baris yang penandanya belum dinyatakan **tidak ditebak**: metrik harganya "tidak dihitung"
  beserta alasannya (aturan keras 2, PRD 7.2);
* right issue tidak dihitung dengan rumus karangan, dan itu dikatakan;
* `volume` dan `nilai` tidak ikut bergeser, karena ADTV20 = harga x volume invarian terhadap split;
* hasilnya **tepat**, bukan hampir tepat: perbandingannya memakai `fractions.Fraction`, bukan
  `pytest.approx`, sebab aritmetika rasio memang eksak dan galat pembulatannya nanti menjadi uang
  yang salah (T8).
"""

from __future__ import annotations

from datetime import date
from fractions import Fraction

import pytest

from mejasaham.ingesti import (
    PENYESUAIAN_SPLIT,
    PENYESUAIAN_SPLIT_DIVIDEN,
    PENYESUAIAN_TIDAK_DISESUAIKAN,
    AksiKorporasi,
    HargaHarian,
)
from mejasaham.penyesuaian import faktor_lembar, sesuaikan

KODE = "AAAA"

#: Rentang tanggal uji mengelilingi satu split pada `TANGGAL_SPLIT`.
SEBELUM_SPLIT = date(2026, 1, 5)  # baris yang wajib disesuaikan
SEBELUM_SPLIT_LAIN = date(2026, 2, 10)  # baris lain yang juga sebelum split
TANGGAL_SPLIT = date(2026, 3, 2)  # hari aksi korporasinya
SESUDAH_SPLIT = date(2026, 5, 4)  # sudah di basis pascasplit
SPLIT_KEDUA = date(2026, 6, 1)  # split berikutnya, untuk uji dua split berturut-turut

#: Waktu unduh baris sumber, sebelum dan sesudah `TANGGAL_SPLIT` (format `diketahui_pada` nyata).
DIUNDUH_SEBELUM_SPLIT = "2026-02-20T18:37:51+07:00"
DIUNDUH_SESUDAH_SPLIT = "2026-03-10T18:51:11+07:00"
DIUNDUH_PADA_HARI_SPLIT = "2026-03-02T18:51:11+07:00"

#: Batas tanggal yang jatuh **sebelum** `TANGGAL_SPLIT`: aksi itu belum diketahui saat itu.
BATAS_SEBELUM_SPLIT = date(2026, 2, 1)

VOLUME = 2_500_000
NILAI = 2_550_000_000


def _bar(
    tanggal: date,
    close: int,
    *,
    penanda: str | None = PENYESUAIAN_TIDAK_DISESUAIKAN,
    diketahui_pada: str | None = None,
) -> HargaHarian:
    """Satu bar harga dengan penanda sumbernya eksplisit.

    Bawaannya `tidak_disesuaikan` — baris yang justru **wajib** digeser modul ini. Uji yang
    memaksudkan "penanda belum dinyatakan" harus menulis `penanda=None` sendiri, supaya bedanya
    tidak hilang di balik nilai bawaan.
    """
    return HargaHarian(
        kode=KODE,
        tanggal=tanggal,
        close=close,
        volume=VOLUME,
        penyesuaian_sumber=penanda,
        diketahui_pada=diketahui_pada,
    )


def _split(tanggal: date, *, lama: int = 1, baru: int = 2) -> AksiKorporasi:
    """Split `lama`:`baru` — `lama` lembar lama menjadi `baru` lembar baru (konvensi `skema.py`)."""
    return AksiKorporasi(
        kode=KODE, tanggal=tanggal, jenis="split", rasio_lama=lama, rasio_baru=baru
    )


def _reverse_split(tanggal: date, *, lama: int = 2, baru: int = 1) -> AksiKorporasi:
    """Reverse split `lama`:`baru` — kebalikan arah split, harga sebelum aksi naik."""
    return AksiKorporasi(
        kode=KODE, tanggal=tanggal, jenis="reverse_split", rasio_lama=lama, rasio_baru=baru
    )


def _dividen(tanggal: date, *, per_saham: int = 25) -> AksiKorporasi:
    """Dividen: aksi korporasi yang **tidak** mengubah harga historis (U4)."""
    return AksiKorporasi(
        kode=KODE, tanggal=tanggal, jenis="dividen", dividen_per_saham=per_saham
    )


def _right_issue(tanggal: date, *, harga_tebus: int = 250) -> AksiKorporasi:
    """Right issue: rasio dan harga tebus wajib ada (CHECK `skema.py`), rumusnya belum ada."""
    return AksiKorporasi(
        kode=KODE,
        tanggal=tanggal,
        jenis="right_issue",
        rasio_lama=5,
        rasio_baru=6,
        harga_tebus=harga_tebus,
    )


# ---------------------------------------------------------------------------------------
# Arah dan besaran penyesuaian (konvensi `skema.py`)
# ---------------------------------------------------------------------------------------


def test_split_menyesuaikan_harga_sebelum_tanggal_aksi_dan_membiarkan_harga_sesudahnya() -> None:
    """Harga sebelum aksi dikali `rasio_lama / rasio_baru`, harga sesudahnya tidak disentuh.

    Split 1:2 berarti satu lembar lama menjadi dua lembar baru, jadi harga sebelum aksi dibagi
    dua. Baris sesudah tanggal aksi **sudah** berada di basis pascasplit; menyesuaikannya lagi akan
    menggeser separuh deret dan membuat imbal hasil di sekitar split salah. Baris tepat pada hari
    aksi diperiksa uji berikutnya.
    """
    baris = (_bar(SEBELUM_SPLIT, 1000), _bar(SESUDAH_SPLIT, 480))

    hasil = sesuaikan(baris, [_split(TANGGAL_SPLIT, lama=1, baru=2)])

    assert hasil.bar[0].close == Fraction(500), "harga sebelum aksi harus dibagi dua"
    assert hasil.bar[1].close == Fraction(480), "harga sesudah aksi tidak boleh tersentuh"


def test_baris_tepat_pada_tanggal_aksi_sudah_memakai_basis_pascasplit() -> None:
    """Batasnya ketat: baris **pada** hari aksi adalah baris pertama basis baru.

    Harga di hari ex-date sudah harga pascasplit — justru di hari itulah harganya turun sendiri.
    Ikut menggesernya membuat harga hari itu separuh dari yang seharusnya, dan imbal hasil tepat
    di sekitar split salah di titik yang paling diperhatikan orang.
    """
    hasil = sesuaikan([_bar(TANGGAL_SPLIT, 480)], [_split(TANGGAL_SPLIT, lama=1, baru=2)])

    assert hasil.bar[0].close == Fraction(480)


def test_reverse_split_menyesuaikan_harga_ke_arah_berlawanan() -> None:
    """Reverse split 2:1: dua lembar lama menjadi satu lembar baru, jadi harga **naik** dua kali.

    Arah yang terbalik menghasilkan deret yang tampak wajar tetapi salah separuh: imbal hasil
    sebelum aksi menjadi seperempat dari yang sebenarnya.
    """
    hasil = sesuaikan([_bar(SEBELUM_SPLIT, 250)], [_reverse_split(TANGGAL_SPLIT, lama=2, baru=1)])

    assert hasil.bar[0].close == Fraction(500), "reverse split menaikkan harga, bukan menurunkannya"


def test_dua_split_berturut_turut_dikalikan_bukan_hanya_yang_terakhir() -> None:
    """Setiap split yang terjadi **setelah** barisnya ikut mengalikan harga baris itu.

    Dua split berturut-turut berarti dua perkalian: 1000 x (1/2) x (1/5) = 100. Kalau hanya split
    terakhir yang dipakai, hasilnya 200 — deretnya tampak masuk akal padahal seluruh riwayat
    sebelum split pertama salah skala.
    """
    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 1000)],
        [_split(TANGGAL_SPLIT, lama=1, baru=2), _split(SPLIT_KEDUA, lama=1, baru=5)],
    )

    assert hasil.bar[0].close == Fraction(100)


def test_baris_di_antara_dua_split_hanya_dikenai_split_setelahnya() -> None:
    """Aksi yang sudah lewat tidak menyesuaikan baris sesudahnya.

    Baris pada 2026-04-01 sudah memakai basis pascasplit Maret, jadi hanya split Juni yang berlaku
    atasnya: 500 x (1/5) = 100. Ikut mengalikannya dengan split Maret berarti menyesuaikannya dua
    kali.
    """
    hasil = sesuaikan(
        [_bar(date(2026, 4, 1), 500)],
        [_split(TANGGAL_SPLIT, lama=1, baru=2), _split(SPLIT_KEDUA, lama=1, baru=5)],
    )

    assert hasil.bar[0].close == Fraction(100)


def test_aksi_yang_benar_benar_dipakai_tercatat_di_aksi_diterapkan() -> None:
    """Jejaknya bisa diaudit: pengguna harus bisa melihat split mana yang menggeser deretnya."""
    aksi = _split(TANGGAL_SPLIT)

    hasil = sesuaikan([_bar(SEBELUM_SPLIT, 1000)], [aksi])

    assert hasil.aksi_diterapkan == (aksi,)


# ---------------------------------------------------------------------------------------
# Yang sudah dinyatakan sumber tidak diulang (K8/C10)
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("penanda", [PENYESUAIAN_SPLIT, PENYESUAIAN_SPLIT_DIVIDEN])
def test_baris_bertanda_sudah_disesuaikan_sumber_tidak_disesuaikan_lagi(penanda: str) -> None:
    """K8/C10: harga yang dikirim sumber **sudah** memakai basis pascasplit.

    Sumber tetap melaporkan kejadian split di kolom aksi korporasi, jadi menerapkannya lagi
    membagi harga BBCA dua kali (7.320 menjadi 3.660) tanpa satu pun tanda di layar. Aksi yang
    dilewati tetap dicatat supaya keputusan itu bisa diperiksa, dan melewatinya **bukan** alasan
    menolak menghitung metrik: bedanya dengan baris tanpa penanda adalah baris ini sudah
    menyatakan keadaannya.
    """
    aksi = _split(TANGGAL_SPLIT, lama=1, baru=2)

    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 1000, penanda=penanda, diketahui_pada=DIUNDUH_SESUDAH_SPLIT)], [aksi]
    )

    assert hasil.bar[0].close == Fraction(1000), "harga sudah disesuaikan sumber; jangan dibagi lagi"
    assert hasil.aksi_dilewati == (aksi,)
    assert hasil.siap


@pytest.mark.parametrize("penanda", [PENYESUAIAN_SPLIT, PENYESUAIAN_SPLIT_DIVIDEN])
def test_split_sesudah_baris_sumber_diunduh_tetap_diterapkan(penanda: str) -> None:
    """P42 (c): penanda sumber hanya mencakup split yang sudah terjadi saat baris itu diunduh.

    Riwayat yfinance yang dibekukan (deret sambungan IDX) tidak pernah diunduh ulang, jadi split
    sesudahnya tidak ada di angkanya. Melewatinya membuat deret patah di tanggal split tanpa satu
    pun tanda — momentum emiten itu anjlok separuh di layar.
    """
    aksi = _split(TANGGAL_SPLIT, lama=1, baru=2)

    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 1000, penanda=penanda, diketahui_pada=DIUNDUH_SEBELUM_SPLIT)], [aksi]
    )

    assert hasil.bar[0].close == Fraction(500), "split terjadi sesudah unduhan; sumber belum tahu"
    assert hasil.aksi_diterapkan == (aksi,)
    assert hasil.aksi_dilewati == ()
    assert hasil.siap


def test_split_pada_hari_unduhan_dianggap_sudah_diterapkan_sumber() -> None:
    """Yahoo melaporkan split dalam unduhan yang sama dengan harganya (`actions=True`).

    Unduhan sore hari ex-date sudah memuat splitnya; menerapkannya lagi membagi harga dua kali.
    """
    aksi = _split(TANGGAL_SPLIT, lama=1, baru=2)

    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 500, penanda=PENYESUAIAN_SPLIT, diketahui_pada=DIUNDUH_PADA_HARI_SPLIT)],
        [aksi],
    )

    assert hasil.bar[0].close == Fraction(500)
    assert hasil.aksi_dilewati == (aksi,)


def test_deret_sambungan_riwayat_beku_dan_harga_mentah_sebanding_sesudah_split() -> None:
    """Deret sambungan P42: riwayat yfinance beku + harga IDX mentah, lalu split di era IDX.

    Bar yfinance diunduh sebelum split (basis lama), bar IDX sebelum split juga basis lama, bar
    IDX sesudah split basis baru. Ketiganya harus berakhir di basis yang sama.
    """
    aksi = _split(TANGGAL_SPLIT, lama=1, baru=2)
    bar = [
        _bar(SEBELUM_SPLIT, 1000, penanda=PENYESUAIAN_SPLIT, diketahui_pada=DIUNDUH_SEBELUM_SPLIT),
        _bar(SEBELUM_SPLIT_LAIN, 1000, penanda=PENYESUAIAN_TIDAK_DISESUAIKAN),
        _bar(SESUDAH_SPLIT, 500, penanda=PENYESUAIAN_TIDAK_DISESUAIKAN),
    ]

    hasil = sesuaikan(bar, [aksi])

    assert [satu.close for satu in hasil.bar] == [Fraction(500)] * 3
    assert hasil.siap


def test_baris_bertanda_sumber_tanpa_waktu_diketahui_tidak_ditebak() -> None:
    """Tanpa `diketahui_pada`, tidak bisa dibedakan split mana yang sudah diterapkan sumber.

    Memilih "sudah semua" atau "belum semua" sama-sama tebakan (aturan keras 2); metriknya
    "tidak dihitung" dan alasannya menyebut sebabnya.
    """
    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 1000, penanda=PENYESUAIAN_SPLIT)], [_split(TANGGAL_SPLIT)]
    )

    assert not hasil.siap
    assert hasil.tanggal_tak_diketahui == (SEBELUM_SPLIT,)
    assert hasil.alasan_tak_dihitung is not None
    assert "diketahui_pada" in hasil.alasan_tak_dihitung


def test_baris_bertanda_tidak_disesuaikan_tetap_disesuaikan() -> None:
    """Penanda `tidak_disesuaikan` justru pernyataan yang **paling** butuh penyesuaian.

    Berkas impor yang menyatakan harganya masih mentah mengandalkan modul ini untuk menggesernya.
    Memperlakukannya seperti `split` akan membiarkan harga sebelum aksi dua kali lebih tinggi dari
    yang seharusnya.
    """
    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 1000, penanda=PENYESUAIAN_TIDAK_DISESUAIKAN)],
        [_split(TANGGAL_SPLIT)],
    )

    assert hasil.bar[0].close == Fraction(500)
    assert hasil.aksi_dilewati == (), "tidak ada yang dilewati pada baris ini"


# ---------------------------------------------------------------------------------------
# Yang belum dinyatakan tidak ditebak (aturan keras 2, PRD 7.2)
# ---------------------------------------------------------------------------------------


def test_baris_tanpa_penanda_yang_punya_split_relevan_tidak_dihitung_dan_menyebut_penyesuaian_sumber() -> None:
    """Baris tanpa penanda bisa berarti dua hal yang berlawanan, jadi tidak dipilih diam-diam.

    "Sumber belum menyesuaikan" berarti harga harus dibagi dua; "sumber sudah menyesuaikan"
    berarti harga harus dibiarkan. Menebak salah satunya menghasilkan momentum yang salah tanpa
    satu pun tanda di layar — karena itu metriknya "tidak dihitung" beserta alasannya.
    """
    hasil = sesuaikan([_bar(SEBELUM_SPLIT, 1000, penanda=None)], [_split(TANGGAL_SPLIT)])

    assert not hasil.siap
    assert "penyesuaian_sumber" in (hasil.alasan_tak_dihitung or "")
    assert hasil.bar[0].close == Fraction(1000), "harga tidak boleh ditebak ke salah satu arah"


def test_baris_tanpa_penanda_dicatat_tanggalnya_supaya_bisa_ditinjau() -> None:
    """Alasan "tidak dihitung" harus menunjuk baris mana yang perlu dilengkapi penandanya."""
    hasil = sesuaikan(
        [
            _bar(SEBELUM_SPLIT, 1000, penanda=None),
            _bar(SEBELUM_SPLIT_LAIN, 990, penanda=None),
        ],
        [_split(TANGGAL_SPLIT)],
    )

    assert hasil.tanggal_tak_diketahui == (SEBELUM_SPLIT, SEBELUM_SPLIT_LAIN)


def test_baris_tanpa_penanda_setelah_semua_split_tidak_menghalangi_metrik() -> None:
    """Batas aturan "belum dinyatakan": hanya baris yang masih bisa terpengaruh aksi.

    Baris sesudah tanggal aksi sudah berada di basis pascasplit — tidak ada aksi setelahnya yang
    membuatnya ambigu, jadi menandainya "tidak dihitung" hanya akan mematikan metrik tanpa sebab
    yang nyata.
    """
    hasil = sesuaikan([_bar(SESUDAH_SPLIT, 480, penanda=None)], [_split(TANGGAL_SPLIT)])

    assert hasil.siap
    assert hasil.bar[0].close == Fraction(480)


# ---------------------------------------------------------------------------------------
# Aksi yang tidak menyesuaikan harga, dan aksi yang belum bisa diterapkan
# ---------------------------------------------------------------------------------------


def test_dividen_tidak_pernah_menyesuaikan_harga() -> None:
    """U4: dividen masuk arus kas posisi dan imbal hasil dividen, bukan pengubah harga historis.

    Karena itu dividen juga bukan alasan "penyesuaian_sumber belum dinyatakan": baris tanpa
    penanda tetap siap dihitung kalau satu-satunya aksi korporasinya dividen.
    """
    hasil = sesuaikan([_bar(SEBELUM_SPLIT, 1000, penanda=None)], [_dividen(TANGGAL_SPLIT)])

    assert hasil.bar[0].close == Fraction(1000)
    assert hasil.aksi_diterapkan == ()
    assert hasil.siap


def test_right_issue_menolak_dihitung_dan_menyebut_sebabnya() -> None:
    """PRD 9.3 menyebut right issue, tetapi rumus harga teoretis ex-rights tidak ditetapkan PRD.

    Harga teoretis itu bergantung pada harga pasar saat itu dan harga tebus — bukan sekadar rasio.
    Selama datanya belum ada, emiten yang punya right issue dalam jendela metriknya berstatus
    "tidak dihitung" beserta alasannya: lebih baik metriknya hilang dengan jelas daripada muncul
    dengan angka karangan.
    """
    aksi = _right_issue(TANGGAL_SPLIT)

    hasil = sesuaikan([_bar(SEBELUM_SPLIT, 1000)], [aksi])

    assert not hasil.siap
    assert "right issue" in (hasil.alasan_tak_dihitung or "")
    assert hasil.bar[0].close == Fraction(1000), "jangan dihitung dengan rumus karangan"
    assert hasil.aksi_belum_diterapkan == (aksi,)


def test_aksi_setelah_batas_tanggal_tidak_dipakai_sama_sekali() -> None:
    """PRD 7.2: deret disesuaikan dengan aksi yang **sudah diketahui** saat snapshot dibuat.

    Aksi bertanggal setelah `batas_tanggal` belum terjadi saat itu, jadi memakainya berarti
    menghitung hari ini dengan hal yang belum diketahui (semangat AC-15). Ia juga tidak muncul
    sebagai "dilewati": bukan dilewati, memang belum dipakai.
    """
    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 1000)],
        [_split(TANGGAL_SPLIT)],
        batas_tanggal=BATAS_SEBELUM_SPLIT,
    )

    assert hasil.bar[0].close == Fraction(1000)
    assert hasil.aksi_diterapkan == ()
    assert hasil.aksi_dilewati == ()


# ---------------------------------------------------------------------------------------
# Volume dan nilai ikut apa adanya (U6 — ADTV20 tidak boleh bergeser)
# ---------------------------------------------------------------------------------------


def test_volume_dan_nilai_tidak_ikut_berubah_saat_harga_disesuaikan() -> None:
    """Nilai transaksi (harga x volume) invarian terhadap split, jadi ADTV20 harus tetap.

    Kalau volume atau nilai ikut dikalikan faktor harga, likuiditas emiten berubah hanya karena
    pernah split — dan ambang 50 emiten ber-ADTV20 tertinggi ikut salah tanpa terlihat.
    """
    bar = HargaHarian(
        kode=KODE,
        tanggal=SEBELUM_SPLIT,
        open=1000,
        high=1040,
        low=980,
        close=1020,
        volume=VOLUME,
        nilai=NILAI,
        penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
    )

    hasil = sesuaikan([bar], [_split(TANGGAL_SPLIT)])

    disesuaikan = hasil.bar[0]
    assert (disesuaikan.open, disesuaikan.high, disesuaikan.low, disesuaikan.close) == (
        Fraction(500),
        Fraction(520),
        Fraction(490),
        Fraction(510),
    )
    assert disesuaikan.volume == VOLUME
    assert disesuaikan.nilai == NILAI


# ---------------------------------------------------------------------------------------
# Faktor lembar: arahnya kebalikan faktor harga (AC-18)
# ---------------------------------------------------------------------------------------


def test_faktor_lembar_adalah_kebalikan_faktor_harga_sehingga_nilai_posisi_tetap() -> None:
    """`faktor_lembar` mengalikan **lembar**, bukan harga.

    Pada split 1:2, satu lembar lama menjadi dua lembar baru: lembar dikali 2 sementara harga
    dikali 1/2. Hasil kalinya — nilai posisi — harus tetap: 500 x 2 = 1000, sama dengan sebelum
    split. Kalau arahnya ikut faktor harga, kalkulator risiko (Tahap 2) dan penyesuaian stop akan
    menyarankan ukuran posisi yang salah.
    """
    aksi = (_split(TANGGAL_SPLIT, lama=1, baru=2),)
    hasil = sesuaikan([_bar(SEBELUM_SPLIT, 1000)], aksi)

    lembar = faktor_lembar(aksi, sesudah=SEBELUM_SPLIT)

    assert lembar == Fraction(2)
    assert hasil.bar[0].close * lembar == Fraction(1000), "nilai posisi tidak boleh berubah"


def test_faktor_lembar_hanya_memakai_aksi_setelah_tanggal_yang_diberikan() -> None:
    """Batas `sesudah` eksklusif, sama seperti penyesuaian harga.

    Baris pada tanggal aksi sudah memakai lembar baru, jadi aksi pada hari itu tidak lagi
    mengubah jumlah lembarnya. Memasukkannya akan menggandakan penyesuaian stop.
    """
    aksi = (_split(TANGGAL_SPLIT, lama=1, baru=2),)

    assert faktor_lembar(aksi, sesudah=TANGGAL_SPLIT) == Fraction(1)
    assert faktor_lembar(aksi, sesudah=SEBELUM_SPLIT) == Fraction(2)


# ---------------------------------------------------------------------------------------
# Bentuk keluaran
# ---------------------------------------------------------------------------------------


def test_masukan_dengan_urutan_acak_keluar_urut_tanggal_menaik() -> None:
    """Baris boleh datang dalam urutan apa pun, tetapi keluarannya selalu urut tanggal menaik.

    Urutan "acak" di sini adalah urutan tetap, bukan undian: uji yang bergantung pada undian akan
    gagal sesekali tanpa sebab yang bisa ditelusuri. Yang diperiksa bukan hanya urutan tanggalnya,
    melainkan juga pasangan tanggal-harga tetap utuh — pengurutan yang menukar isi bar akan lolos
    dari pemeriksaan tanggal saja.
    """
    hasil = sesuaikan(
        [
            _bar(SESUDAH_SPLIT, 480),
            _bar(SEBELUM_SPLIT, 1000),
            _bar(SEBELUM_SPLIT_LAIN, 900),
        ],
        [_split(TANGGAL_SPLIT)],
    )

    assert [(satu.tanggal, satu.close) for satu in hasil.bar] == [
        (SEBELUM_SPLIT, Fraction(500)),
        (SEBELUM_SPLIT_LAIN, Fraction(450)),
        (SESUDAH_SPLIT, Fraction(480)),
    ]


def test_tanpa_aksi_korporasi_harga_tidak_berubah_dan_metrik_siap() -> None:
    """Kasus paling umum: emiten yang tidak punya aksi korporasi dalam jendelanya.

    Baris tanpa penanda pun tetap siap dihitung, karena tidak ada aksi yang membuat harganya
    ambigu. Kalau tidak, seluruh emiten tanpa split akan berstatus "tidak dihitung".
    """
    hasil = sesuaikan(
        [_bar(SEBELUM_SPLIT, 1000, penanda=None), _bar(SESUDAH_SPLIT, 480, penanda=None)]
    )

    assert hasil.siap
    assert [satu.close for satu in hasil.bar] == [Fraction(1000), Fraction(480)]
    assert hasil.aksi_diterapkan == ()
