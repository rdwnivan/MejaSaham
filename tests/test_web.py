"""Uji dasbor web lokal (K91) — `mejasaham/web/`.

Server sungguhan dijalankan di port bebas dalam utas, lalu tiap layar diminta lewat HTTP: yang
diuji jalur yang dipakai pengguna (permintaan → pekerjaan latar → halaman), bukan hanya fungsi
render. Datanya dibangun lewat jalur tulis aplikasi, sama dengan uji jendela.
"""

from __future__ import annotations

import http.client
import re
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from mejasaham import (
    db,
    ingesti,
    kandidat,
    konfigurasi,
    lokasi,
    pengatur,
    pengumuman_idx,
    posisi,
    potret,
    risiko,
    saring,
)
from mejasaham.ingesti import PENYESUAIAN_TIDAK_DISESUAIKAN, Emiten, HargaHarian, KumpulanData
from mejasaham.web import pekerjaan as modul_pekerjaan
from mejasaham.web import server as modul_server

AKAR = Path(__file__).resolve().parents[1]
SUMBER = "uji-web"
TANGGAL = date(2026, 6, 30)
MOMEN = datetime(2026, 7, 1, 9, 0, 0)
KODE = "AAAA"
KODE_LAIN = "BBBB"
CLOSE = 2_320
HARI = 24

PARAMETER = """
[[lot]]
nilai_lembar  = 100
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06

[[fraksi_harga]]
berlaku_sejak = 2026-01-02
sumber        = "Peraturan Bursa (uji)"
dicatat_pada  = 2026-10-06
rentang = [
  { batas_bawah = 2000, batas_atas = 4999, tick = 10 },
]

[[biaya_broker]]
nama          = "Broker All-in"
sisi_beli     = { persen = 0.15 }
sisi_jual     = { persen = 0.25 }
sudah_termasuk = ["pph_penjualan"]
berlaku_sejak = 2026-01-02
sumber        = "Halaman tarif resmi broker (uji)"
dicatat_pada  = 2026-10-06

[[slippage]]
mode          = "tick"
nilai         = 1
berlaku_sejak = 2026-01-02
sumber        = "Keputusan produk K20 (uji)"
dicatat_pada  = 2026-10-06
"""


def _deret(kode: str) -> tuple[HargaHarian, ...]:
    return tuple(
        HargaHarian(
            kode=kode,
            tanggal=TANGGAL - timedelta(days=HARI - 1 - i),
            open=CLOSE,
            high=CLOSE + 20,
            low=CLOSE - 20,
            close=CLOSE,
            volume=2_000_000,
            nilai=CLOSE * 2_000_000,
            penyesuaian_sumber=PENYESUAIAN_TIDAK_DISESUAIKAN,
        )
        for i in range(HARI)
    )


def _isi(sambungan: sqlite3.Connection) -> None:
    konfigurasi.simpan(sambungan, konfigurasi.urai("skema = 1\n\n" + PARAMETER, asal="uji"))
    ingesti.simpan(
        sambungan,
        KumpulanData(
            sumber=SUMBER,
            emiten=(
                Emiten(kode=KODE, nama="Emiten <A> & Co", sektor_idx_ic="industri", sumber="uji"),
                Emiten(kode=KODE_LAIN, nama="Emiten B", sektor_idx_ic="industri", sumber="uji"),
            ),
            harga_harian=_deret(KODE) + _deret(KODE_LAIN),
        ),
        tanggal_data=TANGGAL,
        momen=MOMEN,
    )
    pengatur.siapkan_preset_bawaan(sambungan, date(2026, 7, 1))
    risiko.simpan_preset(sambungan, risiko.batas_bawaan(date(2026, 7, 1)))
    risiko.catat_ekuitas(sambungan, ekuitas=250_000_000, kas=100_000_000, tanggal=date(2026, 7, 1))
    kandidat.buat(
        sambungan,
        KODE,
        status="watchlist",
        tesis="laba naik, PER di bawah sektor",
        pembatal_fundamental="ROE 5 tahun turun di bawah 10%",
        horizon="6-12 bulan",
        stop_awal=2_240,
        tanggal_tinjau="2026-08-01",
    )
    posisi.catat_transaksi(
        sambungan, KODE, "beli", harga=CLOSE, lembar=100, mode="nyata", tanggal=date(2026, 7, 2)
    )


@pytest.fixture()
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[modul_server.ThreadingHTTPServer]:
    monkeypatch.setenv(lokasi.ENV_FOLDER_DATA, str(tmp_path / "data"))
    # Dasbor memindai folder pantau (K104); folder Unduhan pengguna bukan bahan uji.
    monkeypatch.delenv("MEJASAHAM_FOLDER_PANTAU", raising=False)
    sambungan = db.siapkan()
    try:
        _isi(sambungan)
    finally:
        sambungan.close()
    srv = modul_server.buat_server(port=0)
    utas = threading.Thread(target=srv.serve_forever, daemon=True)
    utas.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


def _minta(
    srv: modul_server.ThreadingHTTPServer,
    jalur: str,
    *,
    metode: str = "GET",
    badan: str | None = None,
    kepala: dict[str, str] | None = None,
) -> tuple[int, str, dict[str, str]]:
    port = srv.server_address[1]
    sambungan = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    kepala_akhir = {"Host": f"127.0.0.1:{port}"}
    if badan is not None:
        kepala_akhir["Content-Type"] = "application/x-www-form-urlencoded"
    kepala_akhir.update(kepala or {})
    sambungan.request(metode, jalur, body=badan, headers=kepala_akhir)
    jawaban = sambungan.getresponse()
    isi = jawaban.read().decode("utf-8")
    sambungan.close()
    return jawaban.status, isi, dict(jawaban.getheaders())


def _tunggu_halaman(srv: modul_server.ThreadingHTTPServer, jalur: str, batas: float = 120) -> str:
    """Minta halaman sampai hitungan latarnya selesai (halaman berhenti memuat ulang diri)."""
    akhir = time.monotonic() + batas
    while time.monotonic() < akhir:
        status, isi, _ = _minta(srv, jalur)
        assert status == 200, isi
        if 'http-equiv="refresh"' not in isi:
            return isi
        time.sleep(0.1)
    raise AssertionError(f"{jalur} masih menghitung setelah {batas} dtk")


def test_dasbor_terisi_dan_memuat_pernyataan_wajib(server: modul_server.ThreadingHTTPServer) -> None:
    isi = _tunggu_halaman(server, "/")
    assert "GAGAL" not in isi
    assert "Tindakan menunggu" in isi
    assert "bukan nasihat investasi" in isi
    assert "TIDAK RESMI" in isi
    # Snapshot yang dipakai disebut, sama dengan `--dasbor`.
    assert "snapshot" in isi.lower()


def test_screener_menyimpan_skor_lalu_menampilkan_peringkat(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    status, isi, _ = _minta(server, "/screener")
    assert status == 200
    preset = re.search(r'<option value="([^"]+)" selected', isi)
    assert preset is not None, isi
    status, _, kepala = _minta(
        server,
        "/screener",
        metode="POST",
        badan=f"preset={preset.group(1)}&teratas=10&csrf={server.aplikasi.csrf}",
    )
    assert status == 303
    isi = _tunggu_halaman(server, kepala["Location"])
    assert "GAGAL" not in isi
    assert "Snapshot #" in isi
    # Tanpa data notasi, kata "kandidat" ditahan (PRD 7.3) — sama dengan jendela.
    assert "PERINGKAT SEMENTARA" in isi


def test_detail_emiten_meng_escape_nama_dan_menampilkan_tesis(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    isi = _tunggu_halaman(server, f"/emiten?kode={KODE}")
    assert "GAGAL" not in isi
    assert "Emiten &lt;A&gt; &amp; Co" in isi
    assert "<A>" not in isi
    assert "laba naik" in isi


def test_potret_snapshot_yang_sama_dimuat_sekali_untuk_detail_dan_saringan(
    server: modul_server.ThreadingHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Satu muat potret di data kerja ±20 dtk; detail dulu memuatnya dua kali (sesi 67)."""
    asli = potret.muat
    dimuat: list[object] = []

    def hitung(*argumen: object, **kata: object) -> potret.Potret:
        dimuat.append(argumen)
        return asli(*argumen, **kata)  # type: ignore[arg-type]

    monkeypatch.setattr(potret, "muat", hitung)
    isi = _tunggu_halaman(server, f"/emiten?kode={KODE}")
    assert "GAGAL" not in isi
    assert len(dimuat) == 1
    # T99: snapshot yang sama dipakai ulang — muat ulang detail dan saringan tidak memuatnya lagi.
    status, _, kepala = _minta(server, f"/emiten?kode={KODE}&segarkan=1")
    assert status == 303
    assert "GAGAL" not in _tunggu_halaman(server, kepala["Location"])
    _, layar, _ = _minta(server, "/screener")
    pilihan = re.search(r'<option value="([^"]+)" selected', layar)
    assert pilihan is not None
    status, _, kepala = _minta(
        server,
        "/screener",
        metode="POST",
        badan=f"preset={pilihan.group(1)}&teratas=10&csrf={server.aplikasi.csrf}",
    )
    assert status == 303
    assert "GAGAL" not in _tunggu_halaman(server, kepala["Location"])
    assert len(dimuat) == 1


def test_detail_kode_yang_tidak_ada_menyebut_sebabnya(server: modul_server.ThreadingHTTPServer) -> None:
    isi = _tunggu_halaman(server, "/emiten?kode=ZZZZ")
    assert "tidak ada pada snapshot" in isi


def test_risiko_sama_dengan_baris_perintah(server: modul_server.ThreadingHTTPServer) -> None:
    isi = _tunggu_halaman(server, f"/risiko?kode={KODE}")
    assert "GAGAL" not in isi
    sambungan = db.siapkan()
    try:
        entri = kandidat.untuk_rencana(sambungan, KODE)
        masukan = risiko.siapkan_masukan(sambungan, KODE)
        hasil, _ = risiko.hitung_untuk(
            masukan,
            harga_masuk=masukan.harga_acuan,
            harga_pembatal=entri.harga_pembatal,
            jenis_stop=risiko.JENIS_STOP_SAH[0],
        )
        teks = risiko.ringkas_hasil(hasil, masukan)
    finally:
        sambungan.close()
    from html import escape

    assert escape(teks, quote=True) in isi


def test_risiko_tanpa_tesis_ditolak_dengan_pesan(server: modul_server.ThreadingHTTPServer) -> None:
    isi = _tunggu_halaman(server, f"/risiko?kode={KODE_LAIN}")
    assert "GAGAL" in isi
    # Galat terduga (Galat* inti) tampil sebagai pesan, bukan jejak.
    assert "Jejak lengkap" not in isi


def test_isian_angka_yang_salah_bentuk_ditolak_bukan_dijadikan_nol(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    status, isi, _ = _minta(server, f"/risiko?kode={KODE}&harga=dua+ribu")
    assert status == 200
    assert "harus berupa angka bulat" in isi


def test_jurnal_terisi(server: modul_server.ThreadingHTTPServer) -> None:
    isi = _tunggu_halaman(server, "/jurnal")
    assert "GAGAL" not in isi
    assert KODE in isi


def test_host_asing_ditolak(server: modul_server.ThreadingHTTPServer) -> None:
    status, _, _ = _minta(server, "/", kepala={"Host": "contoh.test"})
    assert status == 400


def test_post_lintas_situs_ditolak(server: modul_server.ThreadingHTTPServer) -> None:
    status, _, _ = _minta(
        server,
        "/screener",
        metode="POST",
        badan="preset=x",
        kepala={"Origin": "http://jahat.test", "Sec-Fetch-Site": "cross-site"},
    )
    assert status == 403


def test_jalur_tak_dikenal_404(server: modul_server.ThreadingHTTPServer) -> None:
    status, _, _ = _minta(server, "/tidak-ada")
    assert status == 404


def test_server_menolak_alamat_selain_lokal() -> None:
    with pytest.raises(ValueError):
        modul_server.buat_server(host="0.0.0.0", port=0)


def test_koneksi_ditutup_peramban_dicatat_satu_baris_bukan_jejak(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class SoketTerputus:
        def write(self, _data: bytes) -> int:
            raise ConnectionAbortedError(10053, "koneksi dibatalkan")

    kelas = modul_server.buat_penangan(modul_server.Aplikasi(), lambda: 8765)
    penangan = kelas.__new__(kelas)
    penangan.wfile = SoketTerputus()
    penangan.request_version = "HTTP/1.1"
    penangan.command = "GET"
    penangan.path = "/screener?kirim=1"
    penangan.requestline = "GET /screener?kirim=1 HTTP/1.1"
    penangan.close_connection = False

    penangan._kirim(modul_server.Jawaban(200, "isi"))

    assert penangan.close_connection is True
    galat = capsys.readouterr().err
    assert "GET /screener" in galat and "Traceback" not in galat


def test_galat_tak_terduga_tampil_dengan_jejak_dan_tercatat(tmp_path: Path) -> None:
    log = tmp_path / "log" / "web.log"
    daftar = modul_pekerjaan.DaftarPekerjaan(lambda: log)

    def rusak() -> None:
        raise KeyError("kolom hilang")

    daftar.mulai(("uji",), rusak)
    hasil = daftar.tunggu(("uji",))
    assert hasil is not None and hasil.galat is not None
    assert "KeyError" in hasil.galat
    assert hasil.jejak and "rusak" in hasil.jejak
    assert "kolom hilang" in log.read_text(encoding="utf-8")


def test_pekerjaan_berkunci_sama_tidak_dihitung_dua_kali() -> None:
    daftar = modul_pekerjaan.DaftarPekerjaan()
    hitungan: list[int] = []
    lepas = threading.Event()

    def tugas() -> int:
        hitungan.append(1)
        lepas.wait(5)
        return 7

    pertama = daftar.mulai(("k",), tugas)
    kedua = daftar.mulai(("k",), tugas, ulang=True)
    lepas.set()
    assert pertama is kedua
    assert daftar.tunggu(("k",)).hasil == 7  # type: ignore[union-attr]
    assert hitungan == [1]


def test_pekerjaan_yang_dilupakan_selagi_berjalan_tidak_dipakai_lagi() -> None:
    # Hasil yang dihitung dari keadaan sebelum penulisan tidak boleh tertinggal sebagai cache
    # hanya karena hitungannya belum selesai saat penulisan itu selesai.
    daftar = modul_pekerjaan.DaftarPekerjaan()
    lepas = threading.Event()
    hitungan: list[int] = []

    def tugas() -> int:
        hitungan.append(1)
        lepas.wait(5)
        return len(hitungan)

    pertama = daftar.mulai(("dasbor",), tugas)
    daftar.lupakan("dasbor")
    lepas.set()
    while pertama.berjalan:
        time.sleep(0.01)
    assert daftar.ambil(("dasbor",)) is None
    kedua = daftar.mulai(("dasbor",), tugas)
    assert kedua is not pertama
    assert daftar.tunggu(("dasbor",)).hasil == 2  # type: ignore[union-attr]


def _kandidat_di_dasbor(isi: str) -> bool:
    return "teratas dari skor tersimpan (preset" in isi


def test_dasbor_menghitung_ulang_bila_skor_tersimpan_berubah_di_luar_web(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    # `--saring` dari baris perintah (atau saringan web yang selesai sesudah dasbor dihitung)
    # menulis skor tanpa sepengetahuan cache dasbor; dasbor tidak boleh terus berkata "kosong".
    assert not _kandidat_di_dasbor(_tunggu_halaman(server, "/"))
    # Data uji ini tidak lolos saringan, jadi baris yang akan ditulis `--saring` disisipkan
    # langsung — yang diuji adalah cache dasbor, bukan saringannya.
    sambungan = db.siapkan()
    try:
        id_preset = saring.daftar_preset(sambungan)[0][0]
        id_snapshot = sambungan.execute("SELECT MAX(id_snapshot) FROM snapshot").fetchone()[0]
        with db.tulis(sambungan) as koneksi:
            koneksi.execute(
                "INSERT INTO skor (kode, id_snapshot, id_preset, skor_total_bp, peringkat,"
                " dihitung_pada, versi_hitung, penjelasan) VALUES (?, ?, ?, 6000, 1, ?, 'uji', 'uji')",
                (KODE, id_snapshot, id_preset, db.waktu_iso()),
            )
    finally:
        sambungan.close()
    isi = _tunggu_halaman(server, "/")
    assert _kandidat_di_dasbor(isi)
    assert f'href="/emiten?kode={KODE}"' in isi
    # Data uji tanpa notasi: skor yang sama disebut peringkat sementara di Screener, jadi halaman
    # depan pun tidak boleh menyebutnya "Kandidat teratas" (PRD 7.3).
    # Saringan preset lain menulis tabelnya di tempat yang sama, jadi presetnya disebut di
    # kepala tabel, bukan hanya di halaman keadaan di bawahnya (aturan keras 9).
    assert (
        f"Peringkat sementara dari skor tersimpan (preset {id_preset}, snapshot #{id_snapshot})" in isi
    )
    assert "Kandidat teratas dari skor tersimpan" not in isi


def test_mengimpor_web_tidak_memuat_qt() -> None:
    kode = (
        "import sys, mejasaham.web.server, mejasaham.cli;"
        "qt=[m for m in sys.modules if m.split('.')[0] in {'PySide6','shiboken6'}];"
        "print(qt); sys.exit(1 if qt else 0)"
    )
    hasil = subprocess.run([sys.executable, "-c", kode], cwd=AKAR, capture_output=True, text=True)
    assert hasil.returncode == 0, hasil.stdout + hasil.stderr


# ---------------------------------------------------------------------------------------
# Tahap B: tindakan tulis (formulir → konfirmasi → tulis → hasil)
# ---------------------------------------------------------------------------------------


def _isian(srv: modul_server.ThreadingHTTPServer, **isian: str) -> str:
    from urllib.parse import urlencode

    return urlencode({"csrf": srv.aplikasi.csrf, **isian})


def _siapkan(srv: modul_server.ThreadingHTTPServer, tindakan: str, /, **isian: str) -> tuple[str, str | None]:
    """Kirim formulir; kembalikan halaman konfirmasi dan tokennya (None bila ditolak)."""
    status, isi, _ = _minta(srv, f"/tulis/{tindakan}", metode="POST", badan=_isian(srv, **isian))
    assert status == 200, isi
    cocok = re.search(r'name=token value="([^"]+)"', isi)
    return isi, None if cocok is None else cocok.group(1)


def _konfirmasi(srv: modul_server.ThreadingHTTPServer, token: str, jawab: str = "tulis") -> str:
    status, isi, kepala = _minta(
        srv, "/konfirmasi", metode="POST", badan=_isian(srv, token=token, jawab=jawab)
    )
    if status == 303:
        return _tunggu_halaman(srv, kepala["Location"])
    assert status == 200, isi
    return isi


def _hitung(tabel_sql: str) -> int:
    sambungan = db.siapkan()
    try:
        return int(sambungan.execute(f"SELECT COUNT(*) FROM {tabel_sql}").fetchone()[0])
    finally:
        sambungan.close()


def _posisi_aktif() -> posisi.Posisi:
    sambungan = db.siapkan()
    try:
        return posisi.ringkasan_semua(sambungan, status="aktif")[0].posisi
    finally:
        sambungan.close()


def test_formulir_tampil_di_tiap_layar(server: modul_server.ThreadingHTTPServer) -> None:
    assert 'action="/tulis/stop"' in _tunggu_halaman(server, "/")
    detail = _tunggu_halaman(server, f"/emiten?kode={KODE}")
    assert 'action="/tulis/transaksi"' in detail
    assert 'action="/tulis/rencana"' in _tunggu_halaman(server, f"/risiko?kode={KODE}")
    assert 'action="/tulis/jurnal"' in _tunggu_halaman(server, "/jurnal")
    berkas = _tunggu_halaman(server, "/berkas")
    assert 'action="/tulis/impor"' in berkas and 'action="/tulis/cadangan"' in berkas
    assert berkas.count("Pemulihan TIDAK ada") == 1, "daftar cadangan sudah memuat kalimatnya"
    assert "jendela ini" not in berkas, "jendela PySide6 sudah dihapus (K91)"


def test_ubah_stop_menulis_sesudah_konfirmasi(server: modul_server.ThreadingHTTPServer) -> None:
    sasaran = _posisi_aktif()
    halaman, token = _siapkan(
        server, "stop", id_posisi=str(sasaran.id_posisi), stop="2250", alasan="trailing"
    )
    assert token is not None, halaman
    # Konfirmasi menyebut angkanya sebelum menulis apa pun (K59 d).
    assert "2.250" in halaman or "2250" in halaman
    assert _posisi_aktif().stop_terkini == sasaran.stop_terkini
    hasil = _konfirmasi(server, token)
    assert "pesan oke" in hasil, hasil
    assert _posisi_aktif().stop_terkini == 2_250


def test_batal_tidak_menulis_dan_token_hanya_sekali_pakai(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    sebelum = _hitung("transaksi")
    isian = dict(kode=KODE, aksi="beli", lembar="100", harga=str(CLOSE), mode="nyata")
    _, token = _siapkan(server, "transaksi", **isian)
    assert token is not None
    assert "Dibatalkan" in _konfirmasi(server, token, jawab="batal")
    assert _hitung("transaksi") == sebelum

    _, token = _siapkan(server, "transaksi", **isian)
    assert token is not None
    assert "pesan oke" in _konfirmasi(server, token)
    # Mengirim ulang konfirmasi yang sama tidak menulis untuk kedua kalinya.
    assert "tidak berlaku" in _konfirmasi(server, token)
    assert _hitung("transaksi") == sebelum + 1


def test_isian_salah_bentuk_ditolak_sebelum_konfirmasi(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    halaman, token = _siapkan(server, "transaksi", kode=KODE, aksi="beli", lembar="seratus", harga="2320", mode="nyata")
    assert token is None
    assert "Belum ada yang ditulis" in halaman
    assert "harus berupa angka bulat" in halaman


def test_post_tanpa_token_csrf_ditolak(server: modul_server.ThreadingHTTPServer) -> None:
    sebelum = _hitung("transaksi")
    status, _, _ = _minta(
        server,
        "/tulis/transaksi",
        metode="POST",
        badan=f"kode={KODE}&aksi=beli&lembar=100&harga={CLOSE}&mode=nyata",
    )
    assert status == 403
    assert _hitung("transaksi") == sebelum


def test_catatan_jurnal_menempel_pada_transaksi_terpilih(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    sambungan = db.siapkan()
    try:
        id_transaksi = posisi.daftar_transaksi(sambungan, id_posisi=_posisi_aktif().id_posisi)[0].id_transaksi
    finally:
        sambungan.close()
    _, token = _siapkan(server, "jurnal", id_transaksi=str(id_transaksi), alasan="sesuai rencana")
    assert token is not None
    assert "pesan oke" in _konfirmasi(server, token)
    halaman = _tunggu_halaman(server, "/jurnal")
    assert "sesuai rencana" in halaman


def test_rencana_disimpan_dari_hasil_yang_tampil(server: modul_server.ThreadingHTTPServer) -> None:
    halaman = _tunggu_halaman(server, f"/risiko?kode={KODE}")
    hasil = re.search(r'name="hasil" value="([^"]+)"', halaman)
    assert hasil is not None, halaman
    _, token = _siapkan(server, "rencana", hasil=hasil.group(1))
    assert token is not None
    assert "pesan oke" in _konfirmasi(server, token)
    sambungan = db.siapkan()
    try:
        assert len(risiko.daftar(sambungan, kode=KODE)) == 1
    finally:
        sambungan.close()


def test_cadangan_dari_web(
    server: modul_server.ThreadingHTTPServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mejasaham import cadangan

    tujuan = tmp_path / "cadangan"
    monkeypatch.setenv(cadangan.ENV_FOLDER_CADANGAN, str(tujuan))
    halaman, token = _siapkan(server, "cadangan")
    assert token is not None, halaman
    # Konfirmasi menyebut folder tujuan yang sama dengan yang akan ditulis (K59 d).
    assert str(tujuan) in halaman.replace("&#x27;", "'")
    hasil = _konfirmasi(server, token)
    assert "pesan oke" in hasil, hasil
    assert list(tujuan.rglob("*.db"))


def test_impor_folder_yang_tidak_ada_menyebut_sebabnya(
    server: modul_server.ThreadingHTTPServer, tmp_path: Path
) -> None:
    halaman, token = _siapkan(server, "impor", folder=str(tmp_path / "tidak-ada"))
    assert token is None
    assert "tidak ada atau bukan folder" in halaman


def test_kunci_tulis_menjadi_pesan_bukan_traceback(
    server: modul_server.ThreadingHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    sebelum = _hitung("transaksi")
    _, token = _siapkan(server, "transaksi", kode=KODE, aksi="beli", lembar="100", harga=str(CLOSE), mode="nyata")
    assert token is not None
    monkeypatch.setattr(db, "BUSY_TIMEOUT_MS", 50)
    penulis_lain = db.hubungkan(lokasi.berkas_basis_data())
    penulis_lain.execute("PRAGMA busy_timeout=0")
    try:
        penulis_lain.execute("BEGIN IMMEDIATE")
        hasil = _konfirmasi(server, token)
        penulis_lain.execute("ROLLBACK")
    finally:
        penulis_lain.close()
    assert "belum menulis apa pun" in hasil
    assert "Jejak lengkap" not in hasil
    assert _hitung("transaksi") == sebelum


def test_post_dari_halaman_sendiri_diterima(server: modul_server.ThreadingHTTPServer) -> None:
    """Kepala yang dikirim peramban untuk formulir dari halaman ini sendiri tidak boleh ditolak."""
    port = server.server_address[1]
    status, isi, _ = _minta(
        server,
        "/tulis/cadangan",
        metode="POST",
        badan=_isian(server),
        kepala={"Origin": f"http://127.0.0.1:{port}", "Sec-Fetch-Site": "same-origin"},
    )
    assert status == 200, isi
    assert "Konfirmasi" in isi


def test_halaman_tidak_memaksa_origin_null(server: modul_server.ThreadingHTTPServer) -> None:
    _, _, kepala = _minta(server, "/berkas")
    assert kepala.get("Referrer-Policy") != "no-referrer"


def test_tanpa_argumen_membuka_dasbor_web(monkeypatch: pytest.MonkeyPatch) -> None:
    """K91 tahap C: `python -m mejasaham` (dan klik-ganda MejaSaham.cmd) membuka dasbor web."""
    from mejasaham import cli

    dipanggil: list[object] = []
    monkeypatch.setattr(cli, "jalankan_web", lambda argumen: dipanggil.append(argumen) or cli.KODE_OK)
    assert cli.main([]) == cli.KODE_OK
    assert len(dipanggil) == 1


def test_peluncur_klik_ganda_menjalankan_modul() -> None:
    peluncur = (AKAR / "MejaSaham.cmd").read_bytes()
    assert b"-m mejasaham" in peluncur
    assert b"\r\n" in peluncur, "berkas .cmd harus CRLF"
    # Data kerja nyata ada di .uji-data\mejasaham; MEJASAHAM_DATA dari lingkungan tetap menang.
    assert b'if not defined MEJASAHAM_DATA set "MEJASAHAM_DATA=%~dp0.uji-data\\mejasaham"' in peluncur


# -- tombol "Perbarui data" (K92) -------------------------------------------------------


class _PengambilWeb:
    """Pengambil palsu yang melaporkan kemajuan per emiten seperti `PengambilYFinance`.

    `tahan` (bila diisi) menahan pengambilan sesudah emiten pertama, supaya halaman kemajuan bisa
    diperiksa selagi pembaruan berjalan.
    """

    def __init__(self, laporan, tahan: threading.Event | None = None) -> None:  # type: ignore[no-untyped-def]
        self.laporan = laporan
        self.tahan = tahan

    def ambil(self, emiten):  # type: ignore[no-untyped-def]
        from dataclasses import replace

        from mejasaham.pengambil import Kemajuan

        for nomor, satu in enumerate(emiten, start=1):
            self.laporan(Kemajuan(nomor=nomor, dari=len(emiten), kode=satu.kode, baris=1))
            if self.tahan is not None and nomor == 1:
                assert self.tahan.wait(30)
        hari = TANGGAL + timedelta(days=1)
        return replace(
            KumpulanData(
                sumber=SUMBER,
                harga_harian=tuple(
                    HargaHarian(kode=satu.kode, tanggal=hari, close=CLOSE, volume=2_000_000)
                    for satu in emiten
                ),
            ),
            emiten=tuple(emiten),
        )


@pytest.fixture()
def server_perbarui(
    server: modul_server.ThreadingHTTPServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> modul_server.ThreadingHTTPServer:
    from mejasaham import cadangan

    monkeypatch.setenv(cadangan.ENV_FOLDER_CADANGAN, str(tmp_path / "cadangan"))
    (tmp_path / "data" / "konfigurasi").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "konfigurasi" / "emiten.csv").write_text(
        "kode;nama;sektor_idx_ic;jenis;papan;status_notasi;jumlah_saham;free_float_persen;"
        f"sumber;dicatat_pada\n{KODE};Emiten A;industri;;;;;;uji;2026-06-01\n"
        f"{KODE_LAIN};Emiten B;industri;;;;;;uji;2026-06-01\n",
        encoding="utf-8",
    )
    return server


def _token_perbarui(srv: modul_server.ThreadingHTTPServer, badan: str = "") -> str:
    status, isi, _ = _minta(
        srv, "/perbarui", metode="POST", badan=f"csrf={srv.aplikasi.csrf}{badan}"
    )
    assert status == 200, isi
    token = re.search(r'name=token value="([^"]+)"', isi)
    assert token is not None, isi
    return token.group(1)


def test_dasbor_menampilkan_tombol_perbarui_data(server: modul_server.ThreadingHTTPServer) -> None:
    isi = _tunggu_halaman(server, "/")
    assert 'action="/perbarui"' in isi and "Perbarui data" in isi


def test_perbarui_saat_data_sudah_terbaru_hanya_memberi_tahu(
    server_perbarui: modul_server.ThreadingHTTPServer,
) -> None:
    from mejasaham.ingesti import HariBursa

    sambungan = db.siapkan()
    try:
        ingesti.simpan(
            sambungan,
            KumpulanData(sumber=SUMBER, kalender_bursa=(HariBursa(tanggal=TANGGAL, hari_bursa=True),)),
            tanggal_data=TANGGAL,
        )
    finally:
        sambungan.close()

    status, isi, _ = _minta(
        server_perbarui, "/perbarui", metode="POST", badan=f"csrf={server_perbarui.aplikasi.csrf}"
    )
    assert status == 200
    assert "Data sudah paling baru" in isi
    assert 'action="/perbarui/mulai"' not in isi, "data terkini tidak boleh langsung diperbarui"
    assert server_perbarui.aplikasi.pekerjaan.ambil(modul_server.KUNCI_PERBARUI) is None
    # Tetap bisa dipaksa — tetapi lewat konfirmasi, tidak langsung jalan.
    assert _token_perbarui(server_perbarui, "&paksa=1")


def test_perbarui_lewat_konfirmasi_lalu_menulis_snapshot_dan_saringan(
    server_perbarui: modul_server.ThreadingHTTPServer, tmp_path: Path
) -> None:
    srv = server_perbarui
    srv.aplikasi.buat_pengambil = lambda laporan: _PengambilWeb(laporan)

    # Batal tidak memulai apa pun.
    token = _token_perbarui(srv)
    _, isi, _ = _minta(
        srv, "/perbarui/mulai", metode="POST",
        badan=f"csrf={srv.aplikasi.csrf}&token={token}&jawab=batal",
    )
    assert "Dibatalkan" in isi
    assert srv.aplikasi.pekerjaan.ambil(modul_server.KUNCI_PERBARUI) is None

    token = _token_perbarui(srv)
    status, _, kepala = _minta(
        srv, "/perbarui/mulai", metode="POST",
        badan=f"csrf={srv.aplikasi.csrf}&token={token}&jawab=mulai",
    )
    assert status == 303 and kepala["Location"] == "/perbarui"
    isi = _tunggu_halaman(srv, "/perbarui")
    assert "Pembaruan selesai" in isi, isi
    assert "GAGAL" not in isi

    # Token konfirmasi dipakai sekali.
    _, isi, _ = _minta(
        srv, "/perbarui/mulai", metode="POST",
        badan=f"csrf={srv.aplikasi.csrf}&token={token}&jawab=mulai",
    )
    assert "Konfirmasi tidak berlaku" in isi

    sambungan = db.siapkan()
    try:
        tanggal, = sambungan.execute(
            "SELECT tanggal_data FROM snapshot ORDER BY id_snapshot DESC LIMIT 1"
        ).fetchone()
        # `konteks_pasar` hanya ditulis saringan yang menyimpan hasilnya (T80).
        tersimpan = sambungan.execute(
            "SELECT COUNT(*) FROM konteks_pasar"
            " WHERE id_snapshot = (SELECT MAX(id_snapshot) FROM snapshot)"
        ).fetchone()[0]
    finally:
        sambungan.close()
    assert tanggal == (TANGGAL + timedelta(days=1)).isoformat()
    assert tersimpan > 0, "saringan sesudah pembaruan harus tersimpan (sama dengan --saring)"
    assert any((tmp_path / "cadangan").iterdir()), "cadangan F12 dibuat sesudah refresh"


def test_halaman_kemajuan_menyebut_tahap_dan_jumlah_emiten_selagi_berjalan(
    server_perbarui: modul_server.ThreadingHTTPServer,
) -> None:
    srv = server_perbarui
    tahan = threading.Event()
    srv.aplikasi.buat_pengambil = lambda laporan: _PengambilWeb(laporan, tahan)
    token = _token_perbarui(srv)
    _minta(
        srv, "/perbarui/mulai", metode="POST",
        badan=f"csrf={srv.aplikasi.csrf}&token={token}&jawab=mulai",
    )
    try:
        akhir = time.monotonic() + 10
        while time.monotonic() < akhir:
            _, isi, _ = _minta(srv, "/perbarui")
            if "1 dari 2 emiten" in isi:
                break
            time.sleep(0.05)
        assert "Tahap 1 dari 5: mengambil harga" in isi, isi
        assert "1 dari 2 emiten (50%)" in isi
        assert "<progress" in isi and 'http-equiv="refresh"' in isi
        # Menekan tombol lagi selagi berjalan tidak memulai pengambilan kedua.
        status, _, kepala = _minta(
            srv, "/perbarui", metode="POST", badan=f"csrf={srv.aplikasi.csrf}"
        )
        assert status == 303 and kepala["Location"] == "/perbarui"
        _, dasbor_isi, _ = _minta(srv, "/")
        assert "Lihat kemajuan pembaruan" in dasbor_isi
    finally:
        tahan.set()
    assert "Pembaruan selesai" in _tunggu_halaman(srv, "/perbarui")


def test_dasbor_memuat_jadwal_pembaruan_data(server: modul_server.ThreadingHTTPServer) -> None:
    """K93: daftar periksa tampil di dasbor, dengan tindakan untuk data yang jatuh tempo."""
    isi = _tunggu_halaman(server, "/")
    assert "Jadwal pembaruan data" in isi
    assert "Harga harian &amp; indeks" in isi
    assert "--ambil-kalender" in isi  # data uji tanpa kalender → jatuh tempo + tindakannya


def _perlu_diperbarui(isi: str) -> str:
    """Kotak pemberitahuan K104 saja, bukan tabel jadwal di bawahnya."""
    cocok = re.search(r'<div class="kartu perlu" id=perlu-diperbarui>.*?</div>', isi, re.S)
    return cocok.group(0) if cocok else ""


def test_dasbor_dibuka_memberitahukan_yang_jatuh_tempo_tanpa_yang_tidak_dinilai(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    """K104: pengganti tugas terjadwal — pemberitahuan saat dasbor dibuka, bahkan sebelum
    hitungan dasbor selesai. "Tidak dinilai" (suspensi/UMA, SUN, fundamental) selalu begitu,
    jadi tidak ikut diberitahukan; tetap ada di tabel jadwal."""
    _, pertama, _ = _minta(server, "/")
    assert "Perlu diperbarui" in pertama, "kotaknya ada di kepala halaman, tidak menunggu hitungan"

    isi = _tunggu_halaman(server, "/")
    kotak = _perlu_diperbarui(isi)
    assert "Kalender bursa (KSEI)" in kotak  # data uji tanpa kalender → jatuh tempo
    assert "Notasi khusus &amp; papan pemantauan (IDX)" in kotak
    assert "buka halaman IDX" in kotak
    assert "Suspensi &amp; UMA" not in kotak and "Fundamental emiten" not in kotak
    assert "Suspensi &amp; UMA" in isi, "yang tidak dinilai tetap tampil di tabel jadwal"


def test_dasbor_memberitahukan_unduhan_di_folder_pantau_yang_belum_diimpor(
    server: modul_server.ThreadingHTTPServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_unggahan_idx import _baris_idx, _xlsx

    pantau = tmp_path / "Unduhan"
    pantau.mkdir()
    monkeypatch.setenv("MEJASAHAM_FOLDER_PANTAU", str(pantau))
    assert "Folder pantau" not in _perlu_diperbarui(_tunggu_halaman(server, "/")), "folder kosong = diam"

    (pantau / "Ringkasan Saham-20261028.xlsx").write_bytes(_xlsx([_baris_idx(KODE)]))
    (pantau / "Ringkasan Saham-20261027.xlsx").write_bytes(b"bukan xlsx")
    (pantau / "foto.jpg").write_bytes(b"x")

    kotak = _perlu_diperbarui(_tunggu_halaman(server, "/"))
    assert "1 berkas IDX belum diimpor, 1 ditolak" in kotak
    assert 'href="/berkas"' in kotak


def test_dasbor_diam_soal_unduhan_yang_isinya_sudah_diimpor(
    server: modul_server.ThreadingHTTPServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_unggahan_idx import _baris_idx, _xlsx

    pantau = tmp_path / "Unduhan"
    pantau.mkdir()
    monkeypatch.setenv("MEJASAHAM_FOLDER_PANTAU", str(pantau))
    (pantau / "Ringkasan Saham-20261028.xlsx").write_bytes(_xlsx([_baris_idx(KODE)]))
    monkeypatch.setattr(modul_server.tulis, "jumlah_belum_diimpor", lambda sambungan, pindaian: 0)

    assert "Folder pantau" not in _perlu_diperbarui(_tunggu_halaman(server, "/"))


def test_dasbor_memberitahukan_impor_unduhan_terakhir_yang_gagal_sampai_ada_yang_berhasil(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    """AC-9: jalan `--impor-unduhan` dari Task Scheduler yang gagal tampil saat dasbor dibuka."""
    from mejasaham import folder_pantau

    sambungan = db.siapkan()
    try:
        folder_pantau.catat_jalan(
            sambungan, berhasil=False, pesan="Cadangan dibuat: x\nGAGAL: impor Notasi Khusus\nBerkas …"
        )
        kotak = _perlu_diperbarui(_tunggu_halaman(server, "/"))
        assert "Impor unduhan IDX" in kotak and "jalan terakhir gagal" in kotak
        assert "GAGAL: impor Notasi Khusus" in kotak and "Cadangan dibuat" not in kotak

        folder_pantau.catat_jalan(sambungan, berhasil=True, pesan="selesai")
        assert "Impor unduhan IDX" not in _perlu_diperbarui(_tunggu_halaman(server, "/"))
    finally:
        sambungan.close()


def test_dasbor_tidak_menampilkan_kotak_bila_tidak_ada_yang_perlu_diperbarui(
    server: modul_server.ThreadingHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mejasaham import pengingat, unggahan_idx

    monkeypatch.setattr(pengingat, "saat_dibuka", lambda daftar: ())
    monkeypatch.setattr(unggahan_idx, "pengingat", lambda sambungan, hari_ini=None: None)
    isi = _tunggu_halaman(server, "/")
    assert "perlu-diperbarui" not in isi and "Perlu diperbarui" not in isi


def _unggah(
    srv: modul_server.ThreadingHTTPServer, nama: str, isi: bytes, *, csrf: str | None = None
) -> tuple[int, str]:
    return _unggah_banyak(srv, [(nama, isi)], csrf=csrf)


def _unggah_banyak(
    srv: modul_server.ThreadingHTTPServer,
    berkas: list[tuple[str, bytes]],
    *,
    csrf: str | None = None,
    jalur: str = "/unggah/ringkasan-saham",
) -> tuple[int, str]:
    """Satu kiriman formulir berisi beberapa berkas di isian `berkas` (input `multiple`)."""
    batas = "----batasUji7d1"
    badan = (
        f"--{batas}\r\nContent-Disposition: form-data; name=\"csrf\"\r\n\r\n"
        f"{srv.aplikasi.csrf if csrf is None else csrf}\r\n"
    ).encode()
    for nama, isi in berkas:
        badan += (
            f"--{batas}\r\nContent-Disposition: form-data; name=\"berkas\"; filename=\"{nama}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + isi + b"\r\n"
    badan += f"--{batas}--\r\n".encode()
    port = srv.server_address[1]
    sambungan = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    sambungan.request(
        "POST",
        jalur,
        body=badan,
        headers={"Host": f"127.0.0.1:{port}", "Content-Type": f"multipart/form-data; boundary={batas}"},
    )
    jawaban = sambungan.getresponse()
    teks = jawaban.read().decode("utf-8")
    sambungan.close()
    return jawaban.status, teks


def test_unggah_ringkasan_saham_menyimpan_berkas_biner_apa_adanya(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    """K95: berkas unduhan IDX diunggah lewat dasbor dan disimpan mentah (bait demi bait)."""
    from mejasaham import unggahan_idx

    isi = bytes(range(256)) * 4 + b"\r\n--bukan-batas\r\n"
    status, teks = _unggah(server, "Ringkasan Saham.xlsx", isi)
    # Isinya bukan XLSX: tersimpan mentah, tetapi tombol impor tidak ditawarkan.
    assert "Isi berkas tidak terbaca" in teks and "impor-ringkasan" not in teks

    assert status == 200, teks
    assert "Tersimpan" in teks and "belum masuk basis data" in teks
    (satu,) = unggahan_idx.daftar()
    assert satu.nama_asli == "Ringkasan Saham.xlsx" and satu.berkas.read_bytes() == isi
    assert "Unggahan terakhir" in _minta(server, "/berkas")[1]


def test_unggah_tanpa_csrf_ditolak_tanpa_menyimpan(server: modul_server.ThreadingHTTPServer) -> None:
    from mejasaham import unggahan_idx

    status, _ = _unggah(server, "a.xlsx", b"isi", csrf="salah")
    assert status == 403
    assert unggahan_idx.daftar() == ()


def test_unggah_berkas_bukan_tabel_ditolak_dengan_pesan(server: modul_server.ThreadingHTTPServer) -> None:
    status, teks = _unggah(server, "foto.png", b"isi")
    assert status == 200 and "Unggahan ditolak" in teks and "bukan berkas tabel" in teks


def test_halaman_impor_menawarkan_unggah_ringkasan_saham(server: modul_server.ThreadingHTTPServer) -> None:
    _, isi, _ = _minta(server, "/berkas")
    assert 'action="/unggah/ringkasan-saham"' in isi and 'enctype="multipart/form-data"' in isi
    assert "melarang scraping" in isi


def test_dasbor_mengingatkan_unduh_ringkasan_saham_sampai_diunggah(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    isi = _tunggu_halaman(server, "/")
    assert "Waktunya mengunduh Ringkasan Saham IDX" in isi
    assert _unggah(server, "a.xlsx", b"isi")[0] == 200
    isi = _tunggu_halaman(server, "/")
    assert "Waktunya mengunduh Ringkasan Saham IDX" not in isi
    assert "sudah diunggah" in isi, "sesudah unggah, yang diingatkan adalah impornya"


def test_unggah_xlsx_yang_terbaca_menawarkan_impor_lewat_konfirmasi(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    from tests.test_unggahan_idx import _baris_idx, _xlsx

    from mejasaham import unggahan_idx

    status, teks = _unggah(server, "Ringkasan Saham-20261028.xlsx", _xlsx([_baris_idx(KODE)]))

    assert status == 200, teks
    assert "Terbaca: Ringkasan Saham 28 Okt 2026, 1 emiten." in teks
    # Data uji web berisi snapshot 30 Jun 2026 → berkas ini menunggu "Perbarui data", tanpa tombol.
    assert "Menunggu" in teks and "Perbarui data" in teks
    assert 'action="/tulis/impor-ringkasan"' not in teks
    (satu,) = unggahan_idx.daftar()
    _, isi, _ = _minta(
        server, "/tulis/impor-ringkasan", metode="POST",
        badan=f"csrf={server.aplikasi.csrf}&berkas={satu.berkas.name}&kembali=/berkas",
    )
    assert "Belum ditulis" in isi and "Perbarui data" in isi


def test_unggah_beberapa_berkas_sekaligus_lalu_impor_dalam_satu_konfirmasi(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    """K97 langkah 4: beberapa hari diunggah sekaligus, termasuk hari lampau, satu konfirmasi."""
    from tests.test_unggahan_idx import _baris_idx, _xlsx

    berkas = [
        (f"Ringkasan Saham-202606{hari}.xlsx",
         _xlsx([_baris_idx(KODE, **{"Tanggal Perdagangan Terakhir": f"{hari} Jun 2026"})]))
        for hari in ("26", "29")
    ]
    status, teks = _unggah_banyak(server, berkas)

    assert status == 200, teks
    assert teks.count("Tersimpan") == 2
    assert "2 berkas siap diimpor" in teks
    nama = re.search(r'name="berkas" value="([^"]+)"', teks)
    assert nama is not None and nama.group(1).count(",") == 1
    _, isi, _ = _minta(
        server, "/tulis/impor-ringkasan", metode="POST",
        badan=f"csrf={server.aplikasi.csrf}&berkas={nama.group(1)}&kembali=/berkas",
    )
    assert "26 Jun 2026" in isi and "29 Jun 2026" in isi
    assert "TIDAK dijalankan" in isi, "tidak ada berkas bertanggal snapshot (30 Jun)"
    assert 'action="/konfirmasi"' in isi


def test_unggah_notasi_khusus_langsung_ke_konfirmasi_lalu_menulis(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    """K96: berkas Notasi Khusus IDX diunggah, dibaca, dikonfirmasi, baru ditulis."""
    from tests.test_notasi_unduhan import BARIS_CONTOH, _xlsx

    from mejasaham import notasi

    assert 'action="/unggah/notasi-khusus"' in _minta(server, "/berkas")[1]
    sebelum = _hitung("notasi_khusus")
    status, isi = _unggah_banyak(
        server, [("Notasi Khusus-20261027.xlsx", _xlsx(BARIS_CONTOH))], jalur="/unggah/notasi-khusus"
    )

    assert status == 200, isi
    assert "tersimpan mentah" in isi and "4 emiten" in isi and "27 Okt 2026" in isi
    assert _hitung("notasi_khusus") == sebelum, "belum ada yang ditulis sebelum Tulis"
    token = re.search(r'name=token value="([^"]+)"', isi)
    assert token is not None
    hasil = _konfirmasi(server, token.group(1))

    assert "pesan oke" in hasil, hasil
    assert _hitung("notasi_khusus") == sebelum + 4
    assert notasi.berkas_tujuan(lokasi.folder_konfigurasi()).exists()


def test_unggah_pdf_pengumuman_langsung_ke_konfirmasi_lalu_menulis(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    """K99: beberapa PDF pengumuman diunggah sekaligus, dibaca, dikonfirmasi, baru ditulis."""
    from tests.test_pengumuman_idx import _suspensi, _uma

    halaman_berkas = _minta(server, "/berkas")[1]
    assert 'action="/unggah/pengumuman-idx"' in halaman_berkas
    # K102: tautan ke indeks pengumuman tempat pengguna mengunduh PDF-nya.
    assert f'href="{pengumuman_idx.ALAMAT_PENGUMUMAN}"' in halaman_berkas
    sebelum = _hitung("notasi_khusus")
    status, isi = _unggah_banyak(
        server,
        [("20261028-UMA_COIN.pdf", _uma()), ("20261028-WAS_Suspensi_PTSP.pdf", _suspensi())],
        jalur="/unggah/pengumuman-idx",
    )

    assert status == 200, isi
    assert "2 PDF tersimpan mentah" in isi and "baru: 2" in isi and "PTSP" in isi
    assert _hitung("notasi_khusus") == sebelum, "belum ada yang ditulis sebelum Tulis"
    token = re.search(r'name=token value="([^"]+)"', isi)
    assert token is not None
    hasil = _konfirmasi(server, token.group(1))

    assert "pesan oke" in hasil, hasil
    assert _hitung("notasi_khusus") == sebelum + 2


def test_impor_folder_pantau_lewat_konfirmasi_lalu_memindah_berkas(
    server: modul_server.ThreadingHTTPServer, tmp_path: Path
) -> None:
    """K101: tombol dasbor memakai jalur yang sama dengan --impor-unduhan, sesudah konfirmasi."""
    from tests.test_pengumuman_idx import _uma

    pantau = tmp_path / "Unduhan"
    pantau.mkdir()
    pdf = pantau / "20261028-UMA_COIN.pdf"
    pdf.write_bytes(_uma())
    assert 'action="/tulis/impor-unduhan"' in _minta(server, "/berkas")[1]
    sebelum = _hitung("notasi_khusus")

    isi, token = _siapkan(server, "impor-unduhan", folder=str(pantau), kembali="/berkas")

    assert token is not None, isi
    assert "20261028-UMA_COIN.pdf" in isi
    assert pdf.exists() and _hitung("notasi_khusus") == sebelum, "belum ada yang ditulis sebelum Tulis"
    hasil = _konfirmasi(server, token)

    assert "pesan oke" in hasil, hasil
    assert "Cadangan dibuat" in hasil
    assert _hitung("notasi_khusus") == sebelum + 1
    assert not pdf.exists()


def test_unggah_pdf_pengumuman_yang_tidak_dikenal_ditolak_tanpa_konfirmasi(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    from tests.test_pengumuman_idx import _suspensi

    status, isi = _unggah_banyak(
        server, [("x.pdf", _suspensi(jenis="UPT"))], jalur="/unggah/pengumuman-idx"
    )
    assert status == 200 and "pembukaan" in isi and "name=token" not in isi


def test_unggah_notasi_khusus_berbentuk_lain_ditolak_tanpa_konfirmasi(
    server: modul_server.ThreadingHTTPServer,
) -> None:
    status, isi = _unggah_banyak(server, [("notasi.xlsx", b"isi")], jalur="/unggah/notasi-khusus")
    assert status == 200 and "nama berkas" in isi and "name=token" not in isi
