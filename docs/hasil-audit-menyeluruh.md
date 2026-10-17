# Hasil audit menyeluruh — Sudut Pandaan

Tanggal: 17 Oktober 2026 · cakupan: **61 halaman HTML**, 14 berkas data JSON, CSS & JS situs.

Dua alat audit dibuat agar pemeriksaan bisa diulang kapan saja:

```bash
python3 tools/audit.py                                        # statis (tanpa peramban)
python3 tools/audit_peramban.py --base http://127.0.0.1:8090  # di Chromium
```

## Hasil akhir

| Pemeriksaan | Sebelum | Sesudah |
|---|---|---|
| **Audit statis** (`tools/audit.py`) | 325 temuan | **0 temuan** |
| **Audit peramban** (`tools/audit_peramban.py`) | galat konsol, luber horizontal, target sentuh kecil, konten kosong tanpa JS | **0 temuan** |
| 19 uji interaksi (filter, paginasi, peta, form, lightbox, simpan artikel) | 16 lulus / 3 gagal | **19 lulus / 0 gagal** |
| `tools/cek_tampilan.py --peta` | 60 halaman — 0 temuan | 60 halaman — **0 temuan** |
| `tools/smoke_test.py` | 24 OK | **24 OK / 0 gagal** |
| `tools/uji_berita.py` | 33 lulus | **33 lulus / 0 gagal** |

## Bug nyata yang ditemukan & diperbaiki

| # | Temuan | Dampak | Perbaikan |
|---|---|---|---|
| 1 | `background_color`/`theme_color` di `site.webmanifest` masih sisa palet lama (`#FAFBF9` putih, `#0B3D2E` hijau) | warna bilah & splash PWA tidak sesuai palet navy/krem situs | generator manifest diperbaiki (`#F6F1E7`, `#071C53`) lalu dibangun ulang |
| 2 | 5 halaman detail wisata memuat tautan mentah `{base}peta.html` (template tidak dievaluasi) | tombol "Buka di peta besar" mati | `opts.build` memakai `{base}` yang benar + `btn-outline-navy` |
| 3 | Paginasi berita menautkan `location.pathname` absolut (`/berita/index.html`) | tautan rusak bila di-hosting di subfolder atau dibuka lewat `file://` | tautan paginasi memakai nama berkas relatif |
| 4 | Kelas `.sp-skeleton` dipakai sebagai avatar (bukan loader) | audit & pembaca layar membaca "kerangka pemuatan"; ikon `ph-user` belum ada di subset | kelas `.avatar-lingkar` baru + `ph-user` ditambahkan ke subset |
| 5 | Sakelar peta & panel lompat tidak teruji; uji lama memakai selektor salah (`#paginasi`, `[data-simpan]`) | risiko regresi tak terdeteksi | uji diperbaiki (19 uji interaksi) dan seluruhnya lulus |
| 6 | Kesalahan nyata pada audit: `_redirects` pola `:slug` dianggap tautan mati; honeypot dianggap kendali tanpa label; tombol hanya-ikon terdeteksi salah | derau 284 temuan palsu menutupi temuan nyata | aturan audit diperketat (pola rewrite, honeypot `aria-hidden`, analisis blok `<button>`, sitemap URL bersih, halaman `noindex`) |

## Perbaikan mutu (bukan bug, tetapi memenuhi blueprint)

- **Target sentuh** ≥ 44 px: tombol ikon navbar (42→44), rail, `btn-close` offcanvas (32→44), tombol kecil `.btn-sm`, `tag-pill`, tautan pita majalah, tautan daftar ringkas, kontrol zoom peta, tab `nav-pills`.
- **Konten tanpa JavaScript**: 133 kontainer (`#daftarBerita`, `#daftarDirektori`, `#daftarLoker`, `#daftarNomor`, sidebar populer/agenda, rail beranda, tab kategori, dst.) kini juga **dirender saat build** lewat `tools/prerender.py` (Chromium) — hasil statis terbukti **identik** dengan hasil JavaScript, sehingga halaman tetap bermakna bagi crawler dan pengguna tanpa JS.
- **Warna manifest & meta halaman jembatan berita** diselaraskan dengan palet navy/krem.
- `tools/build.py --prerender` menjalankan langkah prerender otomatis setelah build.

## Catatan tanpa temuan (dipastikan bersih)

- 0 galat konsol, 0 permintaan 404/500 internal, 0 gambar rusak di 61 halaman.
- 0 luber horizontal pada 1280 px dan 412 px (termasuk navbar `navbar-expand-xl`).
- Semua ikon memakai Phosphor **subset** (70 regular + 3 fill) — tidak ada kelas di luar subset.
- Semua tautan internal & anchor hidup; semua halaman detail punya pasangan entri JSON; slug unik.
- `sitemap.xml` memuat **59 URL** = seluruh 61 halaman kecuali `404.html` dan halaman `noindex` (`berita/detail.html`) — tidak ada halaman yang terlewat.
- JSON-LD valid di semua halaman yang memuatnya; satu `<h1>` per halaman; urutan judul tanpa lompatan.
