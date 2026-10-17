# Hasil audit & perbaikan — beranda Sudut Pandaan

Tanggal: 16 Oktober 2026 · Lingkup: `index.html` + komponen bersama (`assets/css`, `assets/js`, `tools/build.py`)
Alat: Lighthouse 12 (mobile, simulasi throttling), Playwright/Chromium, `tools/smoke_test.py`

## 1. Ringkasan skor

Diukur pada `tools/preview_server.py` (server lokal **bergzip**, menyerupai hosting asli
Netlify/Cloudflare). Server `python3 -m http.server` tidak mengompres berkas, sehingga skornya
lebih rendah daripada angka di bawah.

| Kategori | Beranda SEBELUM | Beranda SESUDAH | Daftar berita | Peta | Agenda |
|---|---|---|---|---|---|
| Performance | 65 | **93** (86–95 antar-jalan) | 98 | 81 | 88 |
| Accessibility | 95 | **100** | 100 | 100 | 100 |
| Best Practices | 96 | **100** | 100 | 100 | 100 |
| SEO | 100 | 100 | 100 | 100 | 100 |

Metrik beranda: LCP 5,9 s → **2,7–3,5 s** · CLS 0,128 → **0,016** · TBT 140 → 40–230 ms · berat 1.717 KB → **1.002 KB**.

## 2. Temuan yang diperbaiki

### 2.1 Rusak / tidak jalan (prioritas tertinggi)

| Temuan | Dampak | Perbaikan |
|---|---|---|
| `assets/vendor/phosphor/{regular,bold,fill}/style.css` tidak ada, tetapi dirujuk 61 halaman | **Tanpa ikon di seluruh situs** + 3× HTTP 404 per halaman (console error) | Dibuat ulang sebagai **subset**: `tools/subset_icons.py` + `assets/vendor/phosphor/phosphor.css` (3,4 KB) dan font subset 7,1 KB + 0,8 KB. 674 KB → 11 KB |
| `SP.img()` tidak melewatkan URL absolut | Gambar Unsplash diminta sebagai `…/https://images.unsplash.com/…` → **404 di semua halaman daftar** | `SP.img()`/`SP.url()` mengenali URL absolut, protokol-relatif, dan `data:` lalu meneruskannya tanpa awalan `base` |
| `SP.imgGagal()` dipakai pada 15 titik `onerror` tetapi tidak ada di `config.js` | Fallback gambar mati (error runtime) | Fungsi dipulihkan (placeholder lokal + penanda `data-gagal`) |
| Kotak peta beranda `#peta` ada, tetapi Leaflet tidak pernah dimuat | **Peta mini kosong** di beranda | Aset peta dimuat tertunda via `IntersectionObserver` (Leaflet + `map.js` diunduh saat peta mendekati viewport) |
| `map_assets()` menambahkan `base` dua kali | `../../assets/…` — rusak bila situs di-hosting di subdirektori | Path JS dikembalikan relatif ke root; `scripts()` menambahkan `base` sekali |
| `lightbox_assets()` memuat berkas `.js` dengan `rel="stylesheet"` | Permintaan CSS berisi JS (tidak terpakai) | Fungsi dibersihkan |
| `sp:rendered` bisa terpicu dua kali → `L.map()` dipanggil ulang | Peta diganti pesan gagal "Data peta gagal dimuat." | `SP_MAP.init()` idempoten + perbandingan data stabil (kunci terurut) di `components.js` |

### 2.2 Performa

| Perbaikan | Hasil |
|---|---|
| **Phosphor disubset** (hanya 60 ikon yang dipakai, bukan 1.530) | CSS ikon 234 KB → 3,4 KB; font 441 KB → 8 KB |
| **AOS dibuang** (tidak ada satu pun markup `data-aos`) | 26 KB CSS + 15 KB JS hilang dari setiap halaman |
| **Swiper kondisional** (hanya beranda memakai slider) | 18 KB CSS + 154 KB JS tidak lagi dimuat di 60 halaman lain |
| **Leaflet tertunda** di beranda | ±155 KB JS + 15 KB CSS keluar dari jalur kritis |
| **Urutan CSS**: vendor → CSS tambahan → `style.css` | Aturan situs tidak lagi kalah oleh CSS pustaka (bug laten pada peta/lightbox) |
| **Gambar kartu dikecilkan** via `SP.imgKartu()` (700×438 / 560×560, kualitas 60) | Kartu ±380 px tidak lagi mengunduh gambar 1000 px |
| Slide hero statis 1600×900 (**366 KB**) → 1200×675 (**120 KB**) dan diganti foto Lembah Penanggungan (lebih sesuai tema "Leret Penanggungan") | LCP turun ±1,5 s |
| `<link rel="preload" as="image" fetchpriority="high">` untuk gambar slide pertama + `preconnect` ke `images.unsplash.com` | LCP tidak lagi menunggu Swiper/CSS |
| Preload 2 font latin yang dipakai judul (`poppins-600/700`) | Teks judul cepat stabil |
| `loading="lazy" decoding="async"` konsisten; `fetchpriority="high"` hanya pada gambar utama halaman detail | Byte gambar turun, CLS aman |
| Swiper diinisialisasi **saat idle** (`requestIdleCallback`) | TBT turun (parse+init di luar jendela beban) |
| Render data **dari sematan lebih dulu**, fetch JSON di latar (`sp:data-baru`) | Konten muncul pada paint pertama; 14 permintaan JSON tidak lagi memblokir tampilan |

### 2.3 Aksesibilitas (WCAG 2.2 AA)

| Temuan | Perbaikan |
|---|---|
| Kontras badge **Lalu Lintas** 3,08:1 dan **Wisata** 4,32:1 (gagal AA) | Lalu Lintas memakai teks gelap `#16201B` di atas `#EF6C00` → **5,42:1**; Wisata memakai `#00796B` (token `#00897B` tetap untuk aksen) → **5,32:1** |
| Urutan heading melompat `h1 → h3` di 7 halaman daftar | Ditambahkan `<h2 class="visually-hidden">` pada tiap daftar |
| Dua `<h1>` di halaman detail (judul ganda) | Judul di badan artikel menjadi `<h2 class="h2">`, `<h1>` tunggal dari `page_header` |
| `<h6>` di kaki halaman setelah `<h2>` | Menjadi `<h2 class="h6">` (tampilan sama) |
| Titik navigasi Swiper 8×8 px; marker peta 20×20 px | Area sentuh menjadi 32×32 px (titik/pin tetap kecil lewat `::before` dan `.sp-pin`) |
| Peta mini beranda: marker bertumpuk di kotak kecil, sulit disentuh | Mode **mini** yang dekoratif (`role="img"`, tanpa fokus/klik) + tautan ke halaman Peta |

**Hasil:** seluruh audit biner Lighthouse lulus di beranda, daftar berita, agenda, dan peta (skor aksesibilitas 100).

### 2.4 CLS (pergeseran tata letak)

| Penyebab | Perbaikan |
|---|---|
| Baris tombol hero membungkus dua baris saat font fallback lebih lebar | `.hero-actions` dijaga satu baris (`flex-wrap: nowrap` + ukuran tombol mobile) |
| Fallback font tidak bermetrik sama dengan webfont | `@font-face` "Poppins Fallback"/"Inter Fallback" dengan `size-adjust`/`ascent-override` hasil pengukuran |
| Skeleton daftar agenda (3 kartu × 411 px) vs konten asli (4 kartu × 532 px) | `skeleton_grid(4, body_h="18.1rem")` → selisih tinggi 1 px |
| Data baru dirender setelah paint pertama | `loadData()` memakai salinan `data-embed.js` lebih dulu |
| Tombol "Ekspor .ics (agenda terlihat)" membungkus di layar kecil | Label diringkas di mobile (`d-none d-sm-inline`) |

Beranda: CLS 0,128 → **0,016**. Halaman agenda masih 0,157 (skeleton → konten berganti setelah paint
pertama; sudah dicatat sebagai sisa pekerjaan, lihat bagian 4).

## 3. Verifikasi

- `python3 tools/smoke_test.py` → **24/24 halaman OK** (tanpa error console, tanpa HTTP ≥ 400, konten dinamis terisi).
- Pemeriksaan heading otomatis (24 halaman): **0 halaman bermasalah** (satu `<h1>`, urutan berurutan).
- Pemeriksaan ikon di Chromium: semua ikon yang tampak memiliki glyph (`font_terpasang=True`, `gagal_render=0`) di beranda, berita, wisata, kuliner, UMKM, lalu lintas, tentang, dan `/link`.
- Peta: 31 marker terpasang di beranda (mode mini) setelah peta mendekati viewport; halaman Peta & detail memuat peta langsung.
- Rujukan berkas lokal seluruh 61 halaman: **0 rujukan hilang**.

## 4. Sisa pekerjaan / catatan jujur

1. **CLS halaman agenda 0,157.** Penyebab: skeleton dirender lebih dulu oleh browser, lalu diganti konten
   pada ±130 ms. Tinggi skeleton sudah disamakan; opsi berikutnya menghapus skeleton untuk daftar yang
   datanya sudah tersemat, atau merender daftar langsung di `build.py`.
2. **Lighthouse Peta 81 — "Serves images with low resolution".** Ubin OSM raster 256 px yang direntangkan;
   ini bawaan penyedia ubin, hanya bisa dinaikkan dengan `detectRetina` (menggandakan permintaan ubin).
3. **Skor beranda bervariasi 86–95 antar-jalan** karena gambar Unsplash diambil dari CDN eksternal saat
   simulasi throttling. Angka stabil bila foto diunduh ke `assets/img/` dan di-host sendiri.
4. Beberapa gambar ilustrasi masih bernuansa umum (mis. foto "hujan" untuk artikel drainase) karena
   keterbatasan padanan di Unsplash — lihat `docs/kredit-foto.md`.

## 5. Pembersihan berkas

Sisa migrasi foto ke Unsplash meninggalkan **20 berkas foto lokal (3,9 MB)** yang sudah tidak
dirujuk siapa pun (`assets/img/foto/*.jpg` dan varian `*-800.webp` untuk air terjun, hero budaya,
hero tol, ayam, rawon, lembah, melon, wisata air, tempe jpg, serta `foto/og-default.jpg`).
Semua sudah dihapus setelah dicek: **0 rujukan gambar hilang** di 61 halaman + JSON + JS.

- Repo: 8,3 MB → **4,4 MB** (146 berkas)
- Yang tetap lokal (memang dipakai): `logo.svg`, `favicon/*`, `og-default.jpg` (og:image),
  `foto/umkm-tempe-800.webp` (satu-satunya foto dokumentasi), `placeholder/placeholder-umum.webp`,
  dan `placeholder/placeholder-kerajinan.webp` (cadangan tambahan).
- Aset vendor: Bootstrap 5.3.8, Phosphor subset, Swiper (beranda), Leaflet + markercluster, bs5-lightbox.
  AOS dihapus (tidak terpakai); Bootstrap Icons dihapus (sudah diganti Phosphor).
