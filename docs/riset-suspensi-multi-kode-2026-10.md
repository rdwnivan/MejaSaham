# Pemetaan lampiran suspensi IDX berkode `>1 Kode`

**Diakses: 11 Okt 2026.** Riset ini memetakan keluaran endpoint `GetSuspension` ke dokumen primer IDX. Tidak ada perubahan ke basis data atau konfigurasi aplikasi.

## Metode dan batas bukti

- API resmi IDX `GetSuspension` mengembalikan 1.919 rekaman saat diperiksa; tepat **56** memiliki `Kode = ">1 Kode"`. Field API yang dicatat: `Date`, `Info_Type` (`SPT`/`UPT`), `Judul`, dan `Data_Download`.
- Semua **56/56** tautan PDF merespons HTTP 200 dan mempunyai teks yang dapat diekstrak (1–6 halaman; tidak ada PDF tanpa teks). Jadi OCR tidak diperlukan untuk daftar ini. Ekstraksi teks tetap alat bantu; tautan PDF primer disediakan untuk pemeriksaan silang.
- Kolom “kode tercantum” adalah kode emiten/efek yang muncul di tabel atau identifikasi emiten pada PDF. Pada PDF massal, sebagian tabel memuat status individual “Aktif” dan “Suspensi”, dan beberapa pengumuman membedakan suspensi baru dari suspensi yang dipertahankan. **Jangan menganggap seluruh kode tercantum sebagai kode yang baru disuspensi/dibuka**; untuk penerapan ke seri suspensi, baca kalimat keputusan dan status pada PDF.
- `UPT` = pembukaan/pencabutan suspensi; `SPT` = penghentian/suspensi. Tautan adalah file `Data_Download` dari API resmi dan tetap pada host IDX.

## 56 pengumuman dan lampiran

| # | Tanggal API | Jenis | Kode tercantum pada lampiran | PDF IDX |
|---:|---|---|---|---|
| 01 | 2026-09-18 | UPT | TRUE | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202609/7cb1322c20_5d49bacd92.pdf) |
| 02 | 2026-09-03 | UPT | GTBO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202609/4d3bdb3227_e6046b65f5.pdf) |
| 03 | 2026-09-02 | UPT | CRAB | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202609/3501b1e896_31b5dd776e.pdf) |
| 04 | 2026-07-30 | SPT | ALTO, ARKA, ARMY, ARTI, ASMI, BEBS, BHAT, BIKA, BOSS, BTEL, CBMF, COAL, COWL, CPRI, CRAB, DEAL, DUCK, ENVY, ETWA, GAMA, GOLL, GTBO, HILL, HITS, HKMU, HOME, HOTL, INAF, INCF, INDX, IPPE, JMAS, JSKY, KAYU, KBRI, LCGP, LCKM, LMAS, MABA, MAGP, MKNT, MREI, MTFN, MTRA, NUSA, PLAS, PMMP, POOL, PTDU, PURE, RAFI, RIMO, SBAT, SIMA, SKYB, SMMA, SMRU, SRIL, SUGI, SWAT, TAYS, TDPM, TECH, TELE, TGRA, TOPS, TOYS, TRAM, TRIL, TRUE, UNIT, ZBRA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202607/bd75435b4d_dd1615d9bd.pdf) |
| 05 | 2026-07-03 | SPT | MENN, NINE, SOUL | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202607/316b92da4d_4691e3e11c.pdf) |
| 06 | 2026-07-01 | SPT | ABBA, BATA, CANI, CMPP, CNKO, DIGI, FOOD, IBFN, INTA, KARW, KOIN, MARI, MDRN, MTFN, MYTX, SINI, TIRT, UNSP, WSBP, ARTI, BIKA, GLOB, INAF, WICO, BOSS, BTEL, CNTX, DEAL, ETWA, HKMU, JSKY, OCAP, POLY, POSA, PTDU, SIMA, TRIO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202607/950fb01adf_3be20222ac.pdf) |
| 07 | 2026-07-01 | SPT | MENN, NINE, SOUL | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202607/d72b5a7950_fe05ad7a12.pdf) |
| 08 | 2026-06-30 | SPT | AIMS, ALTO, ARKA, ARMY, ARTI, ASMI, BEBS, BHAT, BIKA, BOSS, BTEL, CBMF, COAL, COWL, CPRI, CRAB, DEAL, DUCK, ENVY, ETWA, GAMA, GOLL, GTBO, HILL, HITS, HKMU, HOME, HOTL, INAF, INCF, INDX, IPPE, JMAS, JSKY, KAYU, KBRI, LCGP, LCKM, LMAS, MABA, MAGP, MREI, MTRA, NUSA, PLAS, PMMP, POOL, PTDU, PURE, RAFI, RIMO, SBAT, SIMA, SKYB, SMRU, SRIL, SUGI, SWAT, TAYS, TDPM, TECH, TELE, TGRA, TOPS, TOYS, TRAM, TRIL, TRUE, UNIT, ZATA, ZBRA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202606/1ec4d8b797_d86275e07f.pdf) |
| 09 | 2026-04-21 | SPT | IBST | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202604/7cd89713b9_dc6277898e.pdf) |
| 10 | 2026-03-25 | UPT | RSGK | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202603/e34e36f7f6_6cda6a2efe.pdf) |
| 11 | 2026-02-20 | UPT | AKKU, INPS | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202602/cd907e072e_475281cb0d.pdf) |
| 12 | 2026-02-19 | UPT | SQMI | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202602/3bbad7e2b8_dfdf89c11d.pdf) |
| 13 | 2026-02-19 | UPT | CLAY, GTBO, MGLV, SAGE, SHID | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202602/ac1f5312a3_6000865adf.pdf) |
| 14 | 2026-02-18 | SPT | AKKU, ARMY, ARTI, BEBS, BIKA, BIMA, BOSS, BTEL, CBMF, CLAY, CPRI, DEAL, DUCK, ENVY, ETWA, FIMP, GAMA, GTBO, HKMU, HOME, HOMI, HOTL, IIKP, INAF, INPS, IPPE, JSKY, KAYU, KBRI, MAGP, MENN, MGLV, MKNT, NUSA, PLAN, POLL, POOL, PTDU, PURE, RAFI, RIMO, SAGE, SHID, SIMA, SMRU, SWAT, TECH, TOPS, TRAM, TRIL | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202602/72a94cd1e7_2adcc2ecc5.pdf) |
| 15 | 2026-02-05 | UPT | MYTX | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202602/bd0287eeed_bc000777c8.pdf) |
| 16 | 2026-02-02 | SPT | ALMI, CBMF, COWL, DEAL, DUCK, ETWA, FASW, GAMA, HKMU, JSKY, KAYU, KBRI, KIAS, LCGP, LMSH, MABA, MAGP, MFMI, MTRA, MTSM, MYTX, NUSA, PLAS, PLIN, RIMO, RSGK, SBAT, SIMA, SKYB, SMCB, SUGI, SUPR, TECH, TOYS, TRIL, TRIO, UNIT, WICO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202602/1f6054a4ae_b3a9192f56.pdf) |
| 17 | 2026-02-01 | SPT | ALTO, ARMY, BEBS, BIKA, BOSS, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, GAMA, GOLL, HKMU, HOME, HOTL, IPPE, JSKY, KAYU, KBRI, LCGP, LMAS, MABA, MAGP, MKNT, MTRA, NUSA, PLAS, PMMP, POLL, POOL, PURE, RIMO, SBAT, SIMA, SKYB, SRIL, SUGI, SWAT, TDPM, TECH, TELE, TOPS, TOYS, TRAM, TRIL, UNIT, ZBRA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202602/5db5e1ca97_1b188478c4.pdf) |
| 18 | 2025-11-10 | UPT | PTDU | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202511/9fe4ab0ccc_b61eb773cf.pdf) |
| 19 | 2025-10-31 | SPT | ALMI, CBMF, COWL, DEAL, DUCK, ETWA, FASW, GAMA, HKMU, JSKY, KAYU, KBRI, KIAS, LCGP, LMSH, MABA, MAGP, MFMI, MKNT, MTRA, MTSM, MYTX, NUSA, PLAS, PLIN, RIMO, RSGK, SBAT, SIMA, SKYB, SMCB, SUGI, SUPR, TECH, TOYS, TRIL, TRIO, WICO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202510/4a50b93a3c_1ca52e23f6.pdf) |
| 20 | 2025-10-30 | SPT | ALTO, ARMY, BEBS, BIKA, BOSS, BTEL, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, GAMA, GOLL, HKMU, HOME, HOTL, IPPE, JSKY, KAYU, KBRI, KOKA, LCGP, LMAS, MABA, MAGP, MKNT, MTRA, NUSA, PLAS, PMMP, POLL, POOL, PTDU, PURE, RIMO, SBAT, SIMA, SKYB, SQMI, SRIL, SUGI, SWAT, TDPM, TECH, TELE, TOPS, TOYS, TRAM, TRIL, UNIT, ZBRA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202510/fed47be7bc_96225a718f.pdf) |
| 21 | 2025-10-27 | UPT | AKKU | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202510/742cd4f0fd_0d41e0d7f1.pdf) |
| 22 | 2025-10-14 | UPT | RAFI | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202510/6854a8efdf_ec92ac3428.pdf) |
| 23 | 2025-10-09 | UPT | BCIC | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202510/947c86e99c_9749b0f98c.pdf) |
| 24 | 2025-09-18 | UPT | FISH | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202509/3b319dd78b_41a15548c6.pdf) |
| 25 | 2025-08-15 | UPT | GGRP | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202508/ec0ab4408d_be31903c8f.pdf) |
| 26 | 2025-08-01 | SPT | MKNT, SBAT, DEAL, TRIL | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202508/6b6cbfb2fe_e0468b3032.pdf) |
| 27 | 2025-08-01 | SPT | MKNT, SBAT, DEAL, TRIL | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202508/21590b4ea5_a2d38a3032.pdf) |
| 28 | 2025-08-01 | SPT | ALMI, BCIC, CBMF, COWL, CPRI, DEAL, DUCK, FASW, FISH, GAMA, GGRP, HKMU, JSKY, KBRI, KIAS, LCGP, LMSH, MABA, MFMI, MKNT, MTRA, MTSM, MYTX, NUSA, PLAS, PLIN, RIMO, RSGK, SBAT, SIMA, SKYB, SMCB, SUGI, SUPR, TECH, TOYS, TRIL, TRIO, WICO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202508/20095b13c5_c29295c3b4.pdf) |
| 29 | 2025-07-30 | SPT | AKKU, ALTO, ARMY, ASLI, BEBS, BIKA, BOSS, BTEL, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, GAMA, GOLL, HKMU, HOME, HOTL, IPPE, JSKY, KAYU, KBRI, LCGP, LMAS, MABA, MAGP, MKNT, MTFN, MTRA, NUSA, PLAS, PMMP, POLL, POOL, PTDU, PURE, RAFI, RIMO, SBAT, SIMA, SKYB, SMRU, SQMI, SRIL, SUGI, SWAT, TDPM, TECH, TELE, TGRA, TGUK, TOPS, TOYS, TRAM, TRIL, UNIT, WMPP, ZBRA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202507/4b4003e991_a32aefd678.pdf) |
| 30 | 2025-07-01 | SPT | AKKU, ALTO, ARMY, BEBS, BIKA, BOSS, BTEL, CBMF, COWL, CPRI, DADA, DEAL, DUCK, ETWA, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, IPPE, JSKY, KAEF, KAYU, KBRI, KJEN, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MKNT, MTFN, MTRA, MYRX, NIPS, NUSA, OASA, PLAS, PMMP, POLL, POOL, PRAS, PTDU, PURE, RAFI, RIMO, SBAT, SIMA, SKYB, SQMI, SRIL, SUGI, SWAT, TDPM, TECH, TELE, TGRA, TOPS, TOYS, TRAM, TRIL, UNIT, WMPP, ZBRA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202507/a2ca2e3b0e_d70251fbac.pdf) |
| 31 | 2025-06-16 | SPT | IIKP, LCGP, SMRU, TRAM, RIMO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202506/1c6d79b5e3_f4fdfcf791.pdf) |
| 32 | 2025-06-16 | SPT | IIKP, LCGP, SMRU, TRAM, RIMO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202506/cbefbafb5d_fba759c74c.pdf) |
| 33 | 2025-04-30 | SPT | ALMI, BCIC, CBMF, COWL, CPRI, DUCK, FASW, FISH, FORZ, GAMA, GGRP, HDTX, HKMU, JSKY, KBRI, KPAL, KPAS, KRAH, LCGP, LMSH, MABA, MAMI, MFMI, MTRA, MTSM, MYRX, MYTX, NUSA, PLAS, PLIN, PRAS, RIMO, RSGK, SIMA, SKYB, SMCB, SUGI, SUPR, TECH, TOYS, TRIO, WICO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202504/83c75d0dbc_dd070e62c5.pdf) |
| 34 | 2025-02-18 | UPT | GPSO, PTDU | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202502/b5cdde5778_205632c1be.pdf) |
| 35 | 2025-02-17 | SPT | ARMY, ARTI, BEBS, BIKA, BOSS, BTEL, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, FORZ, GOLL, GPSO, HDTX, HKMU, HOME, HOMI, HOTL, IIKP, INAF, IPPE, JSKY, KAYU, KBRI, KPAL, KPAS, KRAH, LCGP, LCKM, LMAS, MABA, MAGP, MAMI, MGLV, MKNT, MTRA, MYRX, NIPS, NUSA, POLL, POOL, PRAS, PTDU, PURE, RIMO, RONY, SBAT, SIMA, SKYB, SRIL, SUGI, TDPM, TECH, TELE, TOYS, TRAM, TRIL, WMPP, WMUU | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202502/4d251355fd_19ab06d3e4.pdf) |
| 36 | 2025-01-31 | SPT | ALMI, BCIC, COWL, CPRI, DART, DUCK, FASW, FISH, FORZ, GAMA, GGRP, HDTX, HKMU, JSKY, KBRI, KPAL, KPAS, KRAH, LCGP, LMSH, MABA, MAMI, MFMI, MTRA, MTSM, MYRX, MYTX, NUSA, PLAS, PLIN, PRAS, PURE, RIMO, RSGK, SIMA, SKYB, SMCB, SUGI, TECH, TRIO, WICO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202501/ce653389b1_cfd5536924.pdf) |
| 37 | 2025-01-30 | SPT | ARMY, BOSS, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, JSKY, KAYU, KBRI, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MKNT, MTRA, MYRX, NIPS, NUSA, PBRX, PLAS, POOL, PRAS, PURE, RIMO, SBAT, SIMA, SKYB, SUGI, TDPM, TECH, TOYS, TRAM, TRIL, UNIT | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202501/b3ba69a4ef_24f36f1508.pdf) |
| 38 | 2025-01-17 | UPT | VIVA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202501/dfeac6d6b9_b54ef30cb6.pdf) |
| 39 | 2025-01-16 | UPT | MDIA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202501/86c99bf3cd_f1742d286d.pdf) |
| 40 | 2024-10-30 | SPT | ARMY, ARTI, BOSS, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, JSKY, KAYU, KBRI, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MDIA, MKNT, MTRA, MYRX, NIPS, NUSA, PBRX, PLAS, POLL, POOL, PRAS, PURE, RIMO, SBAT, SIMA, SKYB, SUGI, TDPM, TECH, TOYS, TRAM, TRIL, UNIT, VIVA, ZBRA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202410/cc15c72346_e71876be88.pdf) |
| 41 | 2024-08-29 | UPT | MTFN | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202408/ab305c5eb5_fa25f74aca.pdf) |
| 42 | 2024-08-21 | UPT | BAPI | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202408/24fedc38c1_2040608bcc.pdf) |
| 43 | 2024-07-31 | SPT | ARMY, ARTI, BIKA, BOSS, BTEL, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, INAF, JAWA, JSKY, KAYU, KBRI, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MDIA, MKNT, MTFN, MTRA, MYRX, NIPS, NUSA, PLAS, POLL, POOL, PRAS, PURE, RIMO, SBAT, SIMA, SKYB, SQMI, SUGI, SWAT, TDPM, TECH, TOPS, TOYS, TRAM, TRIL, UNIT, VIVA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202407/38e1f24b0e_14cb139554.pdf) |
| 44 | 2024-07-03 | UPT | XSBC, XSSI | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202407/908acf1ef7_104214caa3.pdf) |
| 45 | 2024-07-02 | SPT | ARMY, ARTI, BIKA, BOSS, BTEL, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, INAF, JSKY, KAYU, KBRI, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MDIA, MKNT, MTFN, MTRA, MYRX, NIPS, NUSA, PLAS, POLL, POOL, PRAS, PURE, RIMO, SBAT, SIMA, SKYB, SUGI, TDPM, TECH, TOPS, TRAM, TRIL, UNIT, VIVA, XSBC, XSSI | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202407/c0241fa7b9_181f6473ea.pdf) |
| 46 | 2024-05-06 | UPT | OCAP | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202405/7539a014ba_05f6173c4a.pdf) |
| 47 | 2024-02-20 | SPT | ARMY, CBMF, COWL, CPRI, DUCK, ENVY, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, JSKY, KBRI, KPAL, KPAS, KRAH, LCGP, MABA, MAGP, MAMI, MTFN, MTRA, MYRX, NIPS, NUSA, PURE, RIMO, SIMA, SKYB, SUGI, TECH, TRAM, TRIL | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202402/ca149bfe63_24ca9b5018.pdf) |
| 48 | 2024-02-20 | UPT | NIRO, WOWS, MDIA, VIVA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202402/c66db3e47c_0de74c1134.pdf) |
| 49 | 2024-02-20 | UPT | NIRO, WOWS, MDIA, VIVA | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202402/25611455dc_792d5748a8.pdf) |
| 50 | 2024-02-19 | UPT | INAF, GPSO | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202402/1b72963370_5b49cc3eaf.pdf) |
| 51 | 2024-02-16 | SPT | BAPI, BOSS, BTEL, CBMF, COWL, CPRI, DEAL, DUCK, ETWA, FORZ, GAMA, GOLL, GPSO, HDTX, HKMU, HOME, HOTL, IIKP, INAF, JSKY, KAYU, KBRI, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MDIA, MTRA, MYRX, NIPS, NIRO, NUSA, POLL, PRAS, PURE, RIMO, SIMA, SKYB, SUGI, TAMU, TDPM, TECH, TRAM, TRIL, VIVA, WOWS | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202402/bef993f9f2_9e7735547a.pdf) |
| 52 | 2024-01-30 | SPT | ARMY, CBMF, COWL, CPRI, DUCK, ENVY, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, JSKY, KBRI, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MTFN, MTRA, MYRX, NIPS, NUSA, PLAS, POOL, PURE, RIMO, SIMA, SKYB, SUGI, TDPM, TECH, TRAM, TRIL, UNIT | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202401/a62a298cfd_cffa51c85b.pdf) |
| 53 | 2024-01-02 | UPT | FLMC | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202401/ef855041c3_a2ea2bd8a9.pdf) |
| 54 | 2023-11-23 | UPT | ARTI | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202311/3f341c0f92_55c7eae9b5.pdf) |
| 55 | 2023-10-30 | SPT | ARMY, BAPI, CBMF, COWL, CPRI, DUCK, ENVY, FORZ, GAMA, GOLL, HKMU, HOME, HOTL, JSKY, KBRI, KPAL, KPAS, KRAH, LCGP, LMAS, MABA, MAGP, MAMI, MTFN, MTRA, MYRX, NIPS, NUSA, PLAS, POOL, PURE, RIMO, SIMA, SKYB, SUGI, TDPM, TECH, TRAM, TRIL, UNIT | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202310/7480f94e89_f2919eaa63.pdf) |
| 56 | 2023-10-19 | UPT | ELTY | [PDF resmi](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202310/239245bfe1_febf937abf.pdf) |

## Hasil yang bisa langsung dipakai

1. Arsip yang hilang dari daftar aplikasi kini dapat ditinjau dari PDF resmi yang ditautkan di tabel. Mayoritas daftar suspensi massal berisi kode saham langsung pada tabel; tidak ada alasan teknis untuk menebak atau OCR pada berkas-berkas yang diperiksa.
2. Pemetaan ini mengisi **kandidat daftar kode per pengumuman**, bukan otomatis seri suspensi final. Baca bagian keputusan tiap PDF: periksa apakah kode dikenai suspensi baru, hanya dipertahankan, masih aktif, atau justru dicabut; beberapa lampiran menyajikan tabel status yang mencampur keadaan tersebut.
3. Pengumuman koreksi dan pengumuman bertanggal sama dibiarkan sebagai rekaman berbeda karena API mengembalikan URL/PDF berbeda. Jangan deduplikasi hanya dari tanggal atau judul.
4. Untuk melengkapi model aplikasi secara aman, langkah lanjutan adalah menyimpan untuk tiap kode: nomor pengumuman, aksi SPT/UPT yang benar-benar disebut dalam keputusan, tanggal efektif (yang bisa berbeda dari tanggal API), pasar yang terkena, serta rujukan PDF. Jika nomor/tanggal/kode tidak tegas di dokumen, tandai perlu tinjauan visual dan jangan impor.

### Contoh aksi yang bisa dipastikan dari lampiran

Pengumuman SPT 30 Juli 2026 menyebut keputusan suspensi baru bagi **4 emiten** mulai sesi I pada tanggal itu, sambil mempertahankan suspensi 68 emiten lain. Dalam tabelnya, empat yang berstatus `Aktif` sebelum tindakan adalah **ASMI, COAL, LCKM, dan SMMA**. Jadi empat kode tersebut dapat dicatat sebagai mulai suspensi pada 30 Juli 2026; daftar 68 lainnya adalah kelanjutan, bukan awal baru dari pengumuman itu. [Bukti: PDF resmi IDX, Peng-S-00024/BEI.PLP/07-2026](https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202607/bd75435b4d_dd1615d9bd.pdf).

Ini contoh hasil yang ditinjau terhadap bagian keputusan dan tabel, bukan aturan untuk menerapkan label `Aktif`/`Suspensi` pada semua pengumuman massal. Dokumen lain memakai susunan dan dasar keputusan berbeda.

## Sumber primer

- API resmi IDX: [GetSuspension](https://www.idx.id/primary/NewsAnnouncement/GetSuspension). Endpoint internal yang dipakai situs IDX; bukan dokumentasi API publik dengan kontrak stabil.
- Indeks resmi: [Pengumuman IDX](https://www.idx.id/id/berita/pengumuman).
- Semua lampiran PDF pada tabel berasal dari `Data_Download` yang dikembalikan API tersebut; tautan langsung masing-masing dicantumkan per baris.

## Rekonsiliasi per kode (12 Okt 2026)

Berkas hasil: `.uji-data/riset-idx/rekonsiliasi-upt-per-kode-20261012.csv` (41 baris) beserta
ringkasannya `…-20261012.txt`, dan verdict mentah per baris di
`.uji-data/riset-idx/verdict-upt-20261012.{json,txt}`. Skrip pembuatnya tinggal di `.tmp/`
(tidak ikut git).

### Cara pasangan ditetapkan (menggantikan pencocokan tanggal)

Pasangan SPT tidak lagi ditebak dari kedekatan tanggal. Aturannya sekarang:

1. Baca **nomor pengumuman yang dirujuk UPT sendiri** pada bagian "Sehubungan dengan".
2. Cari nomor itu di **kepala** dokumen (baris `No. …`) di dua kumpulan PDF yang sudah ada:
   56 lampiran multi-kode di `suspensi-pdf/` dan 38 PDF riwayat kode tunggal di `riwayat-api-pdf/`.
   Nomor yang hanya muncul di badan teks tidak dihitung sebagai nomor terbit — badan teks memuat
   kutipan nomor pengumuman lain yang bisa terpotong antar-baris.
3. Pasangan sah hanya bila dokumen itu benar-benar memuat kodenya: sebagai baris tabel, atau
   sebagai identitas dokumen untuk pengumuman satu emiten (mis. `… Perdagangan Efek PT Onix
   Capital Tbk (OCAP)`).
4. Nomor yang dirujuk tetapi tidak ada dokumennya di kedua kumpulan dicatat apa adanya sebagai
   "di luar cakupan" — bukan ditebak.

### Hasil

| Status verifikasi | Baris | Arti |
|---|---:|---|
| `TERKONFIRMASI` | 34 | UPT mencabut suspensi kode itu, pasar dan sesi disebut, dan SPT penyebab (episode terakhir) ditemukan beserta status kodenya |
| `DUPLIKAT_REKAMAN_API` | 4 | Isi PDF identik dengan `2024-02-20_UPT_48.pdf` — satu peristiwa, dua rekaman API |
| `KOREKSI_BUKAN_PENCABUTAN_PENUH` | 1 | OCAP: hanya Pasar Negosiasi untuk crossing, lalu disuspensi kembali pada sesi yang sama |
| `TERKONFIRMASI_TANPA_PDF_SPT` | 2 | ARTI dan ELTY: pencabutan tegas, tetapi PDF SPT penyebabnya di luar cakupan API (2021–2023) |

Enam belas baris yang pada 11 Okt 2026 masih "tanpa kandidat" ternyata **punya rujukan tegas di
UPT-nya sendiri**:

| Kode | SPT yang dirujuk UPT | PDF-nya | Status kode di tabel SPT |
|---|---|---|---|
| XSBC, XSSI | `Peng-S-00021/BEI.PLP/07-2024` | `2024-07-02_SPT_45.pdf` (sampel) | `Aktif` → mulai disuspensi 1 Jul 2024, dibuka 3 Jul 2024 |
| NIRO, WOWS, MDIA, VIVA, INAF, GPSO | `Peng-S-00005/BEI.PLP/02-2024` | `2024-02-16_SPT_51.pdf` (sampel) | `Aktif` → mulai disuspensi 16 Feb 2024, dibuka 19 Feb 2024 |
| FLMC | `Peng-S-00007/BEI.PLP-11-2023` | `FLMC_2023-11-01_SPT_09.pdf` (riwayat API) | `Suspensi di Seluruh Pasar` → dipertahankan |
| OCAP | `Peng-SPT-00003/BEI.PP3/04-2024` | `OCAP_2024-04-01_SPT_36.pdf` (riwayat API) | tanpa tabel; kode pada identitas dokumen |

Hanya **ARTI** dan **ELTY** yang benar-benar tidak punya PDF SPT penyebab: nomor yang dirujuk
UPT-nya berasal dari 2021–2023, sedangkan cakupan API adalah 12 Okt 2023–09 Okt 2026. Episode
keduanya tetap dapat dilacak karena UPT menyebut nomor dan tanggalnya.

### Empat koreksi yang mengubah tafsir

1. **Berkas kembar.** `2024-02-20_UPT_48.pdf` dan `2024-02-20_UPT_49.pdf` identik byte-per-byte
   (nomor sama: `Peng-UPT-00003/BEI.PLP/02-2024`, tanggal dokumen 19 Feb 2024, tanggal API
   20 Feb 2024). Delapan baris API untuk NIRO/WOWS/MDIA/VIVA adalah **empat** peristiwa, bukan
   delapan. Kembar lain yang tidak menyangkut baris UPT: SPT_31≡SPT_32 (2025-06-16),
   SPT_26≡SPT_27 (2025-08-01), SPT_05≡SPT_07 (2026-07-01/03).
2. **OCAP bukan pembukaan penuh.** `Peng-UPT-00002/BEI.PP3/05-2024` membuka perdagangan **hanya
   di Pasar Negosiasi** untuk transaksi crossing, dan menyatakan suspensi seluruh pasar
   diberlakukan kembali pada sesi yang sama. Mencatatnya sebagai "suspensi berakhir" akan salah.
3. **Nomor yang tercetak keliru di dokumen sumber.** UPT INAF/GPSO menulis rujukan
   `Peng-S-00005/BEI.PLP/05-2024`, sedangkan dokumen SPT yang dimaksud (tanggal 16 Feb 2024 dan
   perihalnya sama) bernomor `Peng-S-00005/BEI.PLP/02-2024`. Selisih bulan itu dicatat sebagai
   temuan, bukan diperbaiki diam-diam.
4. **Episode berumur beberapa hari.** Status `Aktif` pada tabel SPT berarti kode **baru**
   disuspensi oleh pengumuman itu (bukan dipertahankan): CLAY/GTBO/MGLV/SAGE/SHID mulai 18 Feb
   dan dibuka 19 Feb 2026; GPSO/PTDU mulai 17 Feb dan dibuka 18 Feb 2025; AKKU/INPS mulai 18 Feb
   dan dibuka 20 Feb 2026; XSBC/XSSI mulai 1 Jul dan dibuka 3 Jul 2024.

Tambahan yang ikut terekam: sesi berbeda per kode pada satu UPT yang sama (GPSO Pra-pembukaan vs
PTDU Sesi I Periodic Call Auction; UPT 19 Feb 2026 memuat kolom Sesi sendiri), dan tanggal dokumen
yang tidak selalu sama dengan tanggal API/nama berkas (MYTX 4 Feb 2026 vs 2026-02-05; UPT_48/49/50
19 Feb 2024 vs 2024-02-20). Satu dokumen juga tidak konsisten di dalam dirinya: SPT FLMC
1 Nov 2023 menulis "Suspensi di Seluruh Pasar" pada tabelnya, sedangkan kalimat keputusannya
menyebut "di Pasar Reguler dan Pasar Tunai sejak sesi I 1 November 2023" — keduanya dicatat apa
adanya dan tidak diratakan diam-diam.

### Batas bukti

- Pemeriksaan ini **berbasis teks hasil ekstraksi** seluruh 27 PDF UPT dan paragraf keputusan +
  baris tabel kode pada PDF SPT pasangannya — bukan pemeriksaan visual halaman per halaman.
  Kolom `bukti_kutipan_upt` sengaja diisi kalimat keputusannya supaya manusia bisa menilang
  langsung ke PDF-nya tanpa mengulang ekstraksi.
- Tanggal, pasar, dan sesi diambil dari kalimat keputusan; bila kalimat itu memakai kata
  "Perseroan" alih-alih kode (RSGK, OCAP), hal itu disebut di kolom `catatan`.
- Belum ada impor dan belum ada perubahan basis data.

## Rekonsiliasi per kode sisi SPT (16 Okt 2026)

Sisi UPT selesai 12 Okt 2026 (41 baris); bagian ini menutup **sisi SPT**: 29 rekaman = **26 peristiwa**,
sebab tiga pasang dokumen isinya identik (K38: `SPT_31`≡`SPT_32`, `SPT_26`≡`SPT_27`, `SPT_07`≡`SPT_05`).

> Catatan istilah: K37 berbunyi "seluruh 56 SPT multi-kode". Angka 56 itu jumlah **rekaman
> multi-kode** (29 SPT + 27 UPT), bukan jumlah SPT — yang direkonsiliasi di sini adalah ke-29
> rekaman SPT itu, dan ke-27 UPT sudah selesai lebih dulu.

| Berkas hasil | Isi |
|---|---|
| `rekonsiliasi-spt-per-kode-20261016.csv` | **1.118 baris** = satu baris per rekaman × kode (1.090 di antaranya peristiwa unik; 28 baris adalah rekaman kembar yang ditandai) |
| `ringkasan-suspensi-per-kode-20261016.csv` | **162 kode**: mulai episode terpantau, status & aksi terakhir, penutup UPT, riwayat API, catatan |
| `rekonsiliasi-spt-per-kode-20261016.txt` | ringkasan angka + seluruh temuan (kode tanpa `Aktif`, kode berjarak ≤45 hari, kode tanpa riwayat API, pasangan UPT) |
| `verdict-spt-20261016.json` | verdict mentah per dokumen, termasuk kalimat kedua bahasa dan angka yang disebut kalimatnya |

### Cara tafsirnya

1. `Aktif`/`Active` pada kolom *Status Perdagangan Efek Saat Ini* berarti kode itu **baru**
   disuspensi oleh pengumuman tersebut; `Suspensi di …` berarti **dipertahankan** (K37). Yang
   dibaca bukan "status tercantum = sedang tersuspensi".
2. Angka yang disebut kalimat keputusan diperiksa terhadap isi tabel: butir aksi baru vs jumlah
   baris `Aktif`, butir "tetap" vs jumlah baris bersuspensi, dan "terdapat N Perusahaan Tercatat"
   di badan pengumuman vs jumlah baris (efek non-saham dikeluarkan dari hitungan perusahaan).
   Selisihnya diberi penanda, bukan diratakan.
3. Salinan dua bahasa digabung per kode; yang berbahasa Indonesia menang, dan padanannya
   dinyatakan (`All Markets` = `Seluruh Pasar`, `Regular and Cash Markets` = `Pasar Reguler dan Tunai`).
4. Tanggal efektif diambil dari kalimat keputusan; bila kalimatnya tidak menyebut tanggal, kolom
   `asal_tanggal_efektif` menyebutkan bahwa yang dipakai tanggal dokumen.
5. Satu baris tabel yang memuat dua kode efek dipecah menjadi dua baris tersendiri (impor notasi
   bekerja per kode), dengan penanda di `catatan`.

### Ke-29 rekaman

| # | Rekaman | Nomor pengumuman | Tgl dokumen | Tgl API | Baris | Baru | Dipertahankan | Verifikasi |
|---:|---|---|---|---|---:|---:|---:|---|
| 1 | `2023-10-30_SPT_55.pdf` | `Peng-S-00006/BEI.PLP-10-2023` | 30-10-2023 | 2023-10-30 | 40 | 0 | 40 | KONSISTEN |
| 2 | `2024-01-30_SPT_52.pdf` | `Peng-S-00002/BEI.PLP/01-2024` | 30-01-2024 | 2024-01-30 | 39 | 0 | 39 | KONSISTEN |
| 3 | `2024-02-16_SPT_51.pdf` | `Peng-S-00005/BEI.PLP/02-2024` | 16-02-2024 | 2024-02-16 | 50 | 11 | 39 | KONSISTEN |
| 4 | `2024-02-20_SPT_47.pdf` | `Peng-S-00006/BEI.PLP/02-2024` | 19-02-2024 | 2024-02-20 | 34 | 0 | 34 | PERTENTANGAN_KOLOM_STATUS |
| 5 | `2024-07-02_SPT_45.pdf` | `Peng-S-00021/BEI.PLP/07-2024` | 01-07-2024 | 2024-07-02 | 55 | 11 | 44 | KONSISTEN |
| 6 | `2024-07-31_SPT_43.pdf` | `Peng-S-00025/BEI.PLP/07-2024` | 30-07-2024 | 2024-07-31 | 57 | 3 | 54 | KONSISTEN |
| 7 | `2024-10-30_SPT_40.pdf` | `Peng-S-00032/BEI.PLP/10-2024` | 30-10-2024 | 2024-10-30 | 51 | 2 | 49 | KONSISTEN |
| 8 | `2025-01-30_SPT_37.pdf` | `Peng-S-00002/BEI.PLP/01-2025` | 30-01-2025 | 2025-01-30 | 46 | 0 | 46 | KONSISTEN |
| 9 | `2025-01-31_SPT_36.pdf` | `Peng-S-00003/BEI.PLP/01-2025` | 31-01-2025 | 2025-01-31 | 41 | 13 | 28 | KONSISTEN |
| 10 | `2025-02-17_SPT_35.pdf` | `Peng-S-00004/BEI.PLP/02-2025` | 17-02-2025 | 2025-02-17 | 61 | 7 | 54 | KONSISTEN |
| 11 | `2025-04-30_SPT_33.pdf` | `Peng-S-00007/BEI.PLP/04-2025` | 30-04-2025 | 2025-04-30 | 42 | 1 | 41 | KONSISTEN |
| 12 | `2025-06-16_SPT_31.pdf` | `Peng-SPT-00004/BEI.PP2/06-2025` + `Peng-SPT-00005/BEI.PP3/06-2025` | 16-06-2025 | 2025-06-16 | 7 | 0 | 0 | DUPLIKAT_REKAMAN_API |
| 13 | `2025-06-16_SPT_32.pdf` | idem (kembar) | 16-06-2025 | 2025-06-16 | 7 | 0 | 0 | DUPLIKAT_REKAMAN_API |
| 14 | `2025-07-01_SPT_30.pdf` | `Peng-SPT-00004/BEI.PLP/06-2025` | 30-06-2025 | 2025-07-01 | 68 | 13 | 55 | KONSISTEN |
| 15 | `2025-07-30_SPT_29.pdf` | `Peng-S-00015/BEI.PLP/07-2025` | 30-07-2025 | 2025-07-30 | 59 | 2 | 57 | KONSISTEN |
| 16 | `2025-08-01_SPT_26.pdf` | `Peng-SPT-00005/BEI.PP1/07-2025` + `Peng-SPT-00011/BEI.PP3/07-2025` | 31-07-2025 | 2025-08-01 | 4 | 0 | 4 | DUPLIKAT_REKAMAN_API |
| 17 | `2025-08-01_SPT_27.pdf` | idem (kembar) | 31-07-2025 | 2025-08-01 | 4 | 0 | 4 | DUPLIKAT_REKAMAN_API |
| 18 | `2025-08-01_SPT_28.pdf` | `Peng-S-00016/BEI.PLP/07-2025` | 31-07-2025 | 2025-08-01 | 39 | 1 | 38 | KONSISTEN |
| 19 | `2025-10-30_SPT_20.pdf` | `Peng-S-00026/BEI.PLP/10-2025` | 30-10-2025 | 2025-10-30 | 52 | 0 | 52 | KONSISTEN |
| 20 | `2025-10-31_SPT_19.pdf` | `Peng-S-00027/BEI.PLP/10-2025` | 31-10-2025 | 2025-10-31 | 38 | 0 | 38 | KONSISTEN |
| 21 | `2026-02-01_SPT_17.pdf` | `Peng-S-00002/BEI.PLP/01-2026` | 30-01-2026 | 2026-02-01 | 48 | 0 | 48 | KONSISTEN |
| 22 | `2026-02-02_SPT_16.pdf` | `Peng-S-00003/BEI.PLP/01-2026` | 30-01-2026 | 2026-02-02 | 38 | 0 | 38 | KONSISTEN |
| 23 | `2026-02-18_SPT_14.pdf` | `Peng-S-00005/BEI.PLP/02-2026` | 18-02-2026 | 2026-02-18 | 50 | 11 | 39 | KONSISTEN |
| 24 | `2026-04-21_SPT_09.pdf` | `Peng-SPT-00009/BEI.PP2/04-2026` | 20-04-2026 | 2026-04-21 | 1 | 0 | 0 | NARATIF_TANPA_TABEL |
| 25 | `2026-06-30_SPT_08.pdf` | `Peng-S-00020/BEI.PLP/06-2026` | 30-06-2026 | 2026-06-30 | 71 | 16 | 55 | KONSISTEN |
| 26 | `2026-07-01_SPT_06.pdf` | `Peng-SPT-00004/BEI.PP1/06-2026` + `Peng-SPT-00011/BEI.PP2/06-2026` + `Peng-SPT-00015/BEI.PP3/06-2026` | 30-06-2026 | 2026-07-01 | 38 | 19 | 18 | KONSISTEN |
| 27 | `2026-07-01_SPT_07.pdf` | `Peng-S-00021/BEI.PLP/06-2026` | 01-07-2026 | 2026-07-01 | 3 | 2 | 1 | DUPLIKAT_REKAMAN_API |
| 28 | `2026-07-03_SPT_05.pdf` | idem (kembar) | 01-07-2026 | 2026-07-03 | 3 | 2 | 1 | DUPLIKAT_REKAMAN_API |
| 29 | `2026-07-30_SPT_04.pdf` | `Peng-S-00024/BEI.PLP/07-2026` | 30-07-2026 | 2026-07-30 | 72 | 4 | 68 | KONSISTEN |

Dua dokumen **tidak memakai tabel** (16 Jun 2025 dan 21 Apr 2026): kodenya diambil dari daftar
identitas/kalimat keputusan, jadi kolom `Baru`/`Dipertahankan` di tabel ini berisi 0 sekalipun
aksinya tercatat (`dipertahankan` untuk 16 Jun 2025, `mulai_disuspensi` untuk IBST 21 Apr 2026).
Rekaman 1 Jul 2026 berisi 38 baris karena satu baris tabelnya memuat dua kode (`CNTX` + `CNTB`).
Pada rekaman 20 Feb 2024 kolom `Dipertahankan` (34) melaporkan **isi kolom status tabelnya**,
sedangkan **aksi** yang dicatat untuk ke-34 baris itu adalah `mulai_disuspensi` menurut kalimat
keputusan — pertentangan itulah temuan nomor 1 di bawah.

### Temuan yang mengubah tafsir

1. **Pengumuman 20 Feb 2024 (`Peng-S-00006/BEI.PLP/02-2024`) bertentangan di dalam dirinya.**
   Kalimat keputusannya menyatakan penghentian sementara **baru** untuk seluruh 34 kode sejak Sesi I
   20 Feb 2024, sedangkan kolom *Status Perdagangan saat ini* tidak memuat satu pun `Aktif`
   (semuanya sudah berstatus `Suspensi di …`). Aksi dicatat menurut kalimat keputusan, ke-34 barisnya
   diberi penanda `PERTENTANGAN_KOLOM_STATUS`, dan **belum diputuskan** mana yang dipakai saat impor.
2. **Empat kode berstatus `Aktif` dua kali dalam 30 hari**: `ASMI`, `COAL`, `LCKM` (30 Jun 2026 →
   30 Jul 2026) dan `MTFN` (30 Jun 2025 → 30 Jul 2025). Tidak ada pembukaan (UPT) yang terpantau di
   antara keduanya, dan keempatnya memang tidak punya riwayat suspensi berkode tunggal di API. Dua
   kemungkinan yang tidak bisa dibedakan dari berkas ini: suspensi pertama tidak pernah berlaku,
   atau ada pembukaan yang tidak terekam. Perlu tinjauan sebelum impor.
3. **Satu baris tabel, dua kode efek.** `PT Hanson International Tbk (MYRX dan MYRXP)` (16 Jun 2025)
   dan `CNTB` pada baris `CNTX` (1 Jul 2026). Keduanya kini punya barisnya sendiri dengan penanda.
   Akibat yang terlihat: pengumuman 1 Jul 2026 menyebut **13 Perusahaan Tercatat** sedangkan tabelnya
   memuat **14 kode**.
4. **Pengumuman 16 Jun 2025 menyebut "6 (enam) saham"** sedangkan daftar identitasnya memuat **7
   kode** (`MYRX` dan `MYRXP` satu perusahaan) — dicatat sebagai temuan, bukan diperbaiki.
5. **80 dari 162 kode tidak punya riwayat suspensi berkode tunggal di API.** Untuk kode-kode itu,
   pengumuman massal inilah **satu-satunya** catatan — persis lubang yang ditutup tahap ini.
6. **35 kode tidak pernah muncul sebagai `Aktif`** dalam ke-29 rekaman ini: episodenya bermula
   sebelum cakupan API (12 Okt 2023) atau dari pengumuman jenis lain (notasi khusus/papan pemantauan).
7. **14 kode tidak ada di daftar emiten KSEI (916 kode) maupun daftar resmi IDX (962 kode)**:
   `CNTB`, `CNTX`, `FORZ`, `HDTX`, `KPAL`, `KPAS`, `KRAH`, `MAMI`, `MYRX`, `MYRXP`, `NIPS`, `PRAS`,
   `XSBC`, `XSSI`. Dua di antaranya reksa dana (K40), dua lagi kode kedua satu perusahaan. Jalur tulis
   `notasi_khusus` **tidak** menuntut kodenya ada di tabel `emiten`, jadi barisnya tetap bisa dimuat —
   keadaan ini dicatat supaya tidak terbaca sebagai kelalaian.
8. **Tautan ke penutup UPT berpasangan rapi** untuk 27 kode: `XSBC`/`XSSI` 1 Jul → 3 Jul 2024 ·
   `AKKU` 18 Feb → 20 Feb 2026 · `CLAY`/`MGLV`/`SAGE`/`SHID` 18 Feb → 19 Feb 2026 · `TRUE`
   30 Jun 2026 → 18 Sep 2026 · `MTFN` 20 Feb → 29 Agu 2024 · `CRAB` 30 Jun → 2 Sep 2026. Kecocokan
   ini yang membuat tanggal mulai hasil tahap ini bisa dipakai menutup episode (langkah K37 berikutnya).

### Temuan tambahan saat berkas impornya disusun (16 Okt 2026, sesi 4)

Tiga hal di bawah ini **tidak** terlihat dari berkas rekonsiliasi sendirian; ketiganya muncul saat
hasil di atas disusun menjadi baris impor (K50, K51) dan sudah dipakai menggantikan tafsir awal.

1. **Ke-34 kode yang pengumumannya ditahan (K46) semuanya sudah berstatus `Suspensi di …` pada
   rekaman sebelum 20 Feb 2024.** Jadi kalimat keputusan pengumuman itu ("suspensi baru untuk 34
   kode") **tidak bisa** dibaca sebagai tanggal mulai yang sah untuk ke-34 kode itu — dan tafsir
   yang dipakai saat impor memang tidak memakainya. Akibatnya yang tertahan hanyalah **baris**
   20 Feb 2024, bukan kodenya: setiap kode tetap mendapat baris impor (tanggal mulai proxy dari
   pengumuman terawal yang mencatatnya masih disuspensi, ditambah penanda
   `DITAHAN_K46_PENGUMUMAN_20_FEB_2024`). Tidak ada kode yang hilang dari data.
2. **Jumlah baris `dipertahankan` adalah 960, bukan 936.** Angka 936 adalah jumlahnya **sesudah
   28 rekaman kembar dibuang** (24 di antaranya dari baris `dipertahankan`); angka mentahnya 960,
   dan 936 + 154 (`mulai_disuspensi` unik) = 1.090 peristiwa unik. Ringkasan di atas menyandingkan
   angka mentah (1.118) dengan angka bersih (154 + 936), sehingga penjumlahannya tampak tidak
   bertemu. Angka 1.118 · 1.090 · 162 · 29 rekaman tetap benar.
3. **Penutup UPT harus dibaca dari dua berkas, bukan satu.** `LCKM` punya penutup
   `Peng-UPT-00022/BEI.PLP/11-2025` (10 Nov 2025) yang muncul di kolom `upt_penutup_nomor`
   rekonsiliasi SPT tetapi **tidak** ada di `rekonsiliasi-upt-per-kode-20261012.csv`. Memakai
   rekonsiliasi UPT saja membuat episode 2025 dan 2026 `LCKM` menyatu — dan tanggal mulai 2026
   hilang tanpa satu pun galat. Sebaliknya, rekonsiliasi UPT memuat lima kode yang tidak ada di
   rekonsiliasi SPT (`ARTI`, `ELTY`, `FLMC`, `OCAP`, `GPSO`) yang penutupnya lebih tua daripada
   rekaman pertama yang tersedia.

### Batas bukti

- Seluruhnya **berbasis teks hasil ekstraksi** 29 PDF SPT dan kalimat keputusannya, bukan tinjauan
  visual halaman per halaman. Kolom `bukti_kutipan` diisi potongan kalimat keputusan (daftar
  perusahaannya dipotong) supaya manusia bisa menilang langsung ke PDF-nya.
- Skrip pembuatnya tinggal di `.tmp/buat_rekonsiliasi_spt.py` (tidak ikut git, seperti skrip sisi UPT),
  dan hanya membaca `.txt` hasil ekstraksi — tidak mengunduh apa pun dan tidak menulis basis data.
- Pemeriksa silangnya ada dua: **API berkode tunggal** (`notasi-khusus.csv`, 963 baris suspensi) dan
  **rekonsiliasi UPT 12 Okt 2026** (41 baris). Keduanya dipakai sebagai pembanding, bukan pengganti.
- **Belum ada impor dan belum ada perubahan basis data.** Penanda
  `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` **belum** dilepas (K37: dilepas paling akhir).
- Perlakuan impor atas keempat temuan di atas **sudah diputuskan 16 Okt 2026 → K46–K49** (20 Feb 2024
  ditahan sampai tinjauan visual; kode `Aktif` dua kali disiapkan apa adanya dengan penanda; baris dua
  kode memakai penanda; kode di luar daftar emiten dimuat apa adanya). Bentuk baris impornya **T60** di
  `docs/arsitektur.md`, pelaksanaannya **T61**; berkas impornya **sudah ada sejak 16 Okt 2026 (sesi 4)**
  di `.uji-data/riset-idx/impor-suspensi-20261016/` (171 baris / 159 kode) beserta pembuatnya
  `.uji-data/riset-idx/buat-impor-suspensi.py`, dan sudah dimuat ke basis data **uji**.
  Penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` **belum dilepas** (K37/K51) **pada saat catatan ini
  ditulis**.

## Pembaruan 16 Okt 2026 (sesi 5) — penanda sudah dilepas, dan impornya sudah masuk basis data utama

- Berkas impor langkah 3 (171 baris / 159 kode) **sudah dimuat juga ke basis data utama**
  `.uji-data/mejasaham` — 171 baris baru, `--saring` likuid **205 → 201**, masih PERINGKAT SEMENTARA.
- Penanda `IDX_SUSPENSI_MULTI_KODE_TIDAK_DIPETAPKAN` **sudah dilepas** (K52) lewat berkas turunan basis
  data (2.447 revisi terkini; 2.154 penanda dilepas; pembuatnya
  `.uji-data/riset-idx/buat-tanpa-penanda.py`), diimpor sebagai **2.447 baris baru**, dan
  `konfigurasi/notasi-khusus.csv` diganti turunan itu. Terukur: `--saring` berbunyi **"Kandidat
  teratas"** (likuid 201 · lolos saring 9). Bukti: `.uji-data/uji-lepas-penanda/bukti-0` … `bukti-7`.
- Yang **tetap** belum selesai dan tidak berubah karenanya: tinjauan visual baris pengumuman
  20 Feb 2024 (1 baris berpenanda K46, mewakili 34 kode) dan 65 episode bertanggal mulai proxy —
  keduanya tetap disebut di `keterangan` barisnya.

## Tinjauan visual pengumuman 20 Feb 2024 (K46) — 16 Okt 2026 (sesi 6)

Tinjauan yang dituntut K46 **sudah dijalankan**: kedua halaman `2024-02-20_SPT_47.pdf` dirender
jadi gambar lalu **dilihat**, bukan disimpulkan dari teks. Bukti:
`.uji-data/uji-tinjauan-k46/` (`bukti-1`/`bukti-2` halaman 1–2, `bukti-3` teks ekstraksi,
`bukti-4` UPT penutup MTFN, `bukti-5` perbandingan status, `bukti-6` dokumen lama menempel,
`bukti-7` keadaan 34 kode, `bukti-8` rantai ARTI, `bukti-9` pemeriksaan K41, `bukti-keadaan.txt`).
Perendernya memakai **PySide6 `QtPdf` yang sudah terpasang** — tidak ada dependensi baru:
`.uji-data/riset-idx/tinjauan-k46/render-pdf.py` (diperiksa: dijalankan ulang dari lokasi itu
menghasilkan PNG yang **hash-nya identik** dengan `bukti-1`/`bukti-2`).

**Apa yang terlihat.** Tabelnya persis empat kolom (No · Kode · Nama Perusahaan · *Status
Perdagangan saat ini*), tanpa kolom kelima, tanpa catatan kaki, tanpa tanda bintang, tanpa
legenda. Halaman itu **tidak memuat penanda apa pun** yang bisa memutuskan "status sebelum"
versus "status sesudah" — jadi tafsir kolom tidak bisa diputuskan dari halamannya sendiri.
Isi kolomnya: 24 kode *Suspensi di Seluruh Pasar* + 10 kode *Suspensi di Pasar Reguler dan Tunai*
= 34 baris, cocok dengan angka yang disebut kalimat butir 3. Dokumennya bertanggal 19 Feb 2024,
butir 3 menyebut catatan Bursa "hingga tanggal 19 Februari 2024", dan kalimat keputusannya
menyatakan suspensi efektif sejak Sesi I 20 Feb 2024.

**Yang menyelesaikannya — perbandingan rekaman, bukan tafsir kolom.** Status ke-34 kode pada
rekaman terakhir **sebelum** pengumuman itu (30 Jan/16 Feb 2024) dibandingkan dengan isi kolom
status di pengumuman itu: **identik untuk 34 kode, 0 berbeda** (24 *Seluruh Pasar* + 10
*Reguler dan Tunai* pada kedua sisi). Artinya ruang lingkup tindakan 20 Feb 2024 (Pasar Reguler
dan Pasar Tunai) **sudah berlaku untuk ke-34 kode sebelum tanggal itu**; tidak ada status
perdagangan yang berubah pada 20 Feb 2024 — dengan tafsir kolom mana pun. Karena itu tanggal
20 Feb 2024 **tidak boleh** dipakai sebagai `tanggal_mulai` episode baru.

**Bukti terkuat menyebut pengumumannya sendiri.** UPT MTFN `Peng-UPT-00011/BEI.PLP/08-2024`
(29 Agu 2024) mencabut **delapan** pengumuman sekaligus, dan nomor 6 di antaranya adalah
`Peng-S-00006/BEI.PLP/02-2024`. Jadi pengumuman 20 Feb 2024 memang menimbulkan suspensi, tetapi
suspensi itu **menyatu** dengan suspensi MTFN yang sudah berjalan dan dicabut bersama-sama
29 Agu 2024 — bukan episode tersendiri yang mulai 20 Feb 2024.

**Dua temuan yang muncul saat tinjauan ini** — keduanya **belum diperbaiki**, sebab butuh keputusan
lebih dulu: diajukan sebagai U24/U25 di `docs/keputusan.md` bagian 2, lalu **diputuskan pengguna pada
sesi yang sama (16 Okt 2026) menjadi K53/K54**, dengan pelaksanaannya menjadi **aksi #17** di
`docs/lanjutan.md` bagian 4 (sesi berikutnya):

1. **Episode MTFN 2023–2024 hilang dari data, dan penutupnya berstatus TIDAK DIPAKAI.** Baris
   MTFN yang ada sekarang `suspensi` mulai 2025-06-30 (proxy) dan dibiarkan terbuka, tetapi
   `keterangan`-nya memuat dokumen 2023-10-30, 2024-01-30, 2024-07-02, dan 2024-07-31 — episode
   **lama** yang dicabut 2024-08-29, bukan episode 2025 ini. Terukur: dari **2.447 baris terkini**,
   hanya **1 baris** yang menyebut berkas lebih tua daripada tanggal mulainya sendiri, dan baris
   itu MTFN. Sebabnya ada di `_kelompokkan` pembuat berkas impor: `yatim` yang lebih tua daripada
   seluruh episode ditempelkan ke `episode[0]`, dan UPT yang jatuh sebelum tanggal mulai episode
   pertama tidak pernah dipakai menutup apa pun.
2. **K41 ("di luar cakupan API") tidak pernah dijalankan atas data.** Penanda itu **0 kali** di
   seluruh `notasi_khusus` (semua revisi) dan **0 kali** di berkas impor; `ELTY` **0 baris** di
   basis data dan 0 baris di berkas impor; `ARTI` punya baris tetapi dari jalur lain (mulai
   2024-07-01) tanpa penanda yang K41 minta. Yang menghalangi bukan kelalaian teknis, melainkan
   bentuk barisnya: untuk kedua kode itu **hanya pencabutannya** yang dinyatakan sumber, sedangkan
   tanggal mulainya tidak diketahui sama sekali — dan `tanggal_mulai` adalah bagian kunci baris.
   Bentuk itulah yang ditanyakan sebagai U25.

Tidak ada perubahan kode, tidak ada impor, dan tidak ada baris basis data yang ditulis pada
tinjauan ini. Verifikasi: `.\.venv\Scripts\python -m pytest` → **765 lulus** (26,73 detik).
