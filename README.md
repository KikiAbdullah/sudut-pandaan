# Sudut Pandaan — Website Frontend (HTML statis, tanpa Vite/npm)

Portal informasi hyperlocal **Pandaan, Kabupaten Pasuruan**. Dibangun mengikuti
`uploads/sudut-pandaan-blueprint-lengkap.md` (Bagian 7 Design System, Bagian 8–9
spesifikasi halaman & komponen, Bagian 10–11 arsitektur HTML + CSS/JS murni).

Sumber akun: **Instagram** & **Threads** `@sudutpandaan`.

---

## 1. Cara menjalankan

### a) Pratinjau lokal (disarankan)

> **Pratinjau tidak men-cache apa pun (default).** Server pratinjau kini mengirim
> `Cache-Control: no-store` untuk semua berkas, jadi setiap muat ulang selalu
> menampilkan build terbaru — dulu CSS/JS ditandai `immutable, max-age=1 tahun`
> sehingga setelah rombak tampilan, pane pratinjau masih memakai berkas lama.
> Untuk mengukur Lighthouse sedekat hosting asli (aset immutable 1 tahun), jalankan
> `python3 tools/preview_server.py 8090 --produksi`.
>
> **Versi aset otomatis (`?v=<hash>`).** Setiap build menyisipkan versi berisi hash
> isi berkas pada URL CSS/JS (`style.css?v=8f2102a2`). Jadi walaupun ada pengunjung
> yang masih menyimpan berkas lama, URL-nya berubah setiap kali berkas itu berubah —
> tidak perlu minta pengguna hard-refresh.

> **URL bersih juga jalan di pratinjau.** `tools/preview_server.py` menirukan aturan
> `.htaccess`: `/berita/candra-wilwatikta` (tanpa `.html`) dilayani sama seperti
> `/berita/candra-wilwatikta.html`, dan `/berita/detail.html?slug=<slug>` diarahkan
> **301** ke artikel bila berkasnya ada (kalau tidak, jembatan tetap tampil dengan
> pesan ramah). Jadi seluruh URL di `sitemap.xml` bisa diuji apa adanya di lokal.
```bash
cd sudutpandaan
python3 -m http.server 8080     # lalu buka http://localhost:8080
```
Alasan: beberapa peramban memblokir `fetch()` pada `file://`. Situs tetap memiliki
**fallback data tertanam** (`assets/js/data-embed.js`), jadi sebagian besar konten
juga tampil bila `index.html` dibuka langsung dari berkas — namun server lokal lebih akurat.

### b) Hosting statis (produksi)
Tanpa build step. Unggah seluruh isi folder ini ke:
Cloudflare Pages · Netlify · GitHub Pages · atau shared hosting (folder `public_html`).

Berkas konfigurasi sudah disertakan:
- `_headers` → header keamanan (CSP, X-Content-Type-Options, Referrer-Policy, dll) untuk Netlify/Cloudflare.
- `_redirects` → URL tanpa `.html` + URL gaya Laravel (`/berita/{slug}`) → berkas statis (HTTP 301).
- `.htaccess` → versi Apache (shared hosting): clean URL, kompresi, cache, header keamanan.

> Catatan: preview di dalam aplikasi memakai iframe `sandbox="allow-scripts"` tanpa akses jaringan,
> sehingga **peta (Leaflet/OpenStreetMap) dan font tidak akan tampil** di preview tersebut.
> Di browser biasa / setelah di-hosting, semuanya tampil normal.

---

## 2. Struktur folder

```
sudutpandaan/
├── index.html                  Beranda (hero, breaking, berita, kategori, wisata, kuliner/UMKM, peta, counter, sosmed, newsletter)
├── berita/
│   ├── index.html              Daftar berita + pencarian, filter kategori, urutkan, paginasi (12/halaman)
│   ├── detail.html             Jembatan ?slug=… → halaman artikel statis
│   └── <slug>.html             13 contoh artikel (peristiwa, lalin, pembangunan, wisata, kuliner, UMKM, agenda, kesehatan)
├── wisata/        index.html + 5 detail destinasi (termasuk JSON-LD TouristAttraction + peta)
├── kuliner/       index.html + 6 detail tempat makan (JSON-LD Restaurant)
├── umkm/          index.html + 10 profil usaha (JSON-LD LocalBusiness) + daftar.html (form pendaftaran)
├── panduan/       index.html + 4 artikel pilar (evergreen)
├── layanan/       lalu-lintas · agenda · loker · nomor-penting · lapor
├── peta.html      Peta interaktif (Leaflet + marker cluster) + legenda + filter + daftar titik
├── tentang.html · redaksi.html · pasang-iklan.html · kontak.html
├── privasi.html · disclaimer.html · syarat-ketentuan.html · 404.html
├── link/index.html             Halaman link-in-bio untuk Instagram/Threads
├── robots.txt · sitemap.xml · site.webmanifest
├── assets/
│   ├── css/style.css           Design System (token, komponen, ikon, aksesibilitas, tema terang saja)
│   ├── css/fonts.css           @font-face self-host (Manrope + Playfair, variable font + fallback pengukur CLS)
│   ├── js/
│   │   ├── config.js           Konfigurasi situs + utilitas base path
│   │   ├── components.js       Kartu & komponen + pemuatan data (pakai data sematan dulu, lalu segarkan dari JSON)
│   │   ├── pages.js            Router per halaman; `home()` merender beranda majalah+bento (petak utama, rail, daftar harga, tab kategori)
│   │   ├── map.js              Leaflet: peta tunggal, semua titik, filter, focus
│   │   ├── share.js            Share WA/FB/X/Telegram, salin tautan, simpan artikel
│   │   ├── main.js             Korsel (Swiper dimuat saat idle, hanya bila ada elemennya), counter, back-to-top, breaking bar, peta tertunda
│   │   ├── nav.js              Navbar transparan→putih, panel pencarian, bilah cari
│   │   ├── majalah.js          Tata letak majalah: rail geser, panel lompat cepat (/ & Ctrl+K), daftar isi + progres baca, tahun footer
│   │   └── data-embed.js       HASIL BUILD — salinan data JSON agar tetap jalan via file://
│   ├── data/*.json             ⬅ SUMBER DATA (edit di sini untuk memperbarui konten)
│   ├── vendor/                 Bootstrap 5.3.8, Phosphor Icons 2.1.2 (subset: regular + fill), Swiper 11.2.10 (hanya beranda), Leaflet 1.9.4 + markercluster, bs5-lightbox 1.8.5 (semua di-host sendiri; AOS dibuang karena tidak ada markup animasi yang memakainya)
│   ├── fonts/                  Manrope & Playfair Display (woff2, disubset)
│   └── img/                    logo.svg (navy), logo-terang.svg (di atas hero), favicon, og-default.jpg (1200×630),
│                               foto/umkm-tempe-800.webp (satu-satunya foto lokal yang tersisa),
│                               placeholder/placeholder-umum.webp (cadangan bila foto luar gagal dimuat)
├── docs/
│   ├── kredit-foto.md          Daftar foto Unsplash + fotografernya (ganti bila pakai foto asli)
│   └── screenshots/            Tangkapan layar tampilan terkini
└── tools/
    ├── data_seed.py            Data awal (dipakai HANYA bila JSON belum ada)
    ├── build.py                Generator situs statis (bar_filter(), render_statis(); --prerender mengisi kontainer JS)
    ├── prerender.py            Mengisi kontainer JS dengan HTML jadi lewat Chromium (SEO & pengguna tanpa JS)
    ├── audit.py                Audit statis: tautan, gambar, ARIA, JSON-LD, ikon, sitemap, manifest, data, aset
    ├── audit_peramban.py       Audit di peramban: konsol, 404, gambar rusak, luber, target sentuh, uji interaksi
    ├── render_stat.js          Render potongan HTML statis lewat Node memakai ulang assets/js/components.js
    ├── subset_icons.py         Pembuat subset font+CSS Phosphor (hanya ikon yang dipakai)
    ├── subset_fonts.py         Subset Inter latin (48 KB → 34 KB) + cetak unicode-range-nya
    ├── siapkan-uji.sh          Menyiapkan peramban + pustaka untuk uji otomatis (lihat catatan di bawah)
    ├── dependensi-uji.txt      Daftar paket Debian yang dibutuhkan Chromium headless
    ├── pulihkan-js.sh          Mengembalikan assets/js/* dari cadangan bila berkasnya terputar balik
    ├── js-cadangan/            Cadangan berkas JS versi benar (dipakai pulihkan-js.sh)
    ├── preview_server.py       Server pratinjau lokal dengan gzip (menyerupai hosting asli)
    ├── smoke_test.py           Uji status HTTP semua halaman (Playwright)
    ├── uji_berita.py           Uji khusus bagian Berita: filter/URL, paginasi, jembatan, nav antar-artikel, SEO
    └── cek_tampilan.py         Uji tampilan: ikon tidak kosong, gambar tidak rusak, alt, <h1>, konsol, peta
```

---

## 3. Memperbarui konten

1. Sunting berkas JSON di **`assets/data/`** — ini sumber utama:
   `berita.json`, `wisata.json`, `kuliner.json`, `umkm.json`, `agenda.json`, `loker.json`,
   `lalu-lintas.json`, `nomor-penting.json`, `sosmed.json`, `panduan.json`, `situs.json`, `kategori.json`, `desa.json`, `penulis.json`.
2. Jalankan ulang generator agar halaman detail, sitemap, dan data tertanam ikut diperbarui:
   ```bash
   python3 tools/build.py
   ```
3. Daftar berita/direktori/agenda pada halaman indeks dirender otomatis dari JSON, jadi tidak perlu menyentuh HTML.

`build.py` **tidak menimpa** JSON yang sudah ada (aman untuk pengeditan manual). Untuk
mengembalikan data contoh dari seed: hapus berkas JSON terkait lalu jalankan ulang.

### Yang WAJIB diganti sebelum publikasi (blueprint Bagian 2, 13.5, 22)
- [ ] **Semua foto** saat ini adalah *foto ilustrasi*. Ganti dengan dokumentasi asli (simpan WebP ≤1600px).
- [ ] **Nomor penting** (`nomor-penting.json`): masih banyak entri kosong dan sengaja tidak diisi. Lengkapi dari kanal resmi instansi.
- [ ] **Kontak & paket iklan** (`situs.json`, `pasang-iklan.html`): pastikan nomor WA yang dipublikasikan memang untuk publik.
- [ ] **Data wisata/kuliner/UMKM**: verifikasi harga, jam buka, dan kepemilikan izin; perbarui `terakhir_diverifikasi`.
- [ ] **Redaksi**: isi nama pemimpin redaksi & penanggung jawab di `redaksi.html`.
- [ ] **Pencapaian/angka audiens**: jangan tayangkan angka yang belum diverifikasi (sudah diberi catatan transparansi di `tentang.html`).
- [ ] Analitik & Search Console: sambungkan sebelum promosi. Jika memakai analitik/iklan pihak ketiga, tampilkan banner persetujuan cookie lebih dulu (`privasi.html` sudah menyatakan komitmen ini).

---

## 4. Fitur yang sudah berjalan

| Area | Detail |
|---|---|
| **Beranda (majalah + bento)** | **Masthead majalah** (nama portal Playfair, tanggal edisi, pita tautan 8 bagian) → **bento pembuka** 12 kolom (berita utama besar + 2 kartu sisi + petak wisata + petak kuliner + petak navy "Sekilas") → **01 Destinasi** (rail geser) → **02 Kuliner** (4 petak foto + daftar harga bernomor) → **03 UMKM** (4 petak kecil) → **04 Berita** (rail + tab kategori) → **05 Layanan** (6 kartu bernomor) → **06 Peta** mini + daftar titik penting → **07 Pandaan dalam Angka** (blok navy, counter) → **08 Sosial media** (rail kartu manual) + panel langganan. Setiap seksi punya **judul bernomor 01–08**, garis hairline, dan tombol aksi di kanan |
| **Berita** | Indeks: 8 chip kategori, pencarian (judul, ringkasan, isi, tag), urutkan (terbaru/terpopuler/A–Z), paginasi 12/halaman — semuanya **tersinkron ke URL** (`?q=`, `?kategori=`, `?urut=`, `?halaman=`) sehingga hasil filter bisa dibagikan/di-bookmark, ditambah tombol **Reset**, tutup dengan **Esc**, blok "hasil lain" lintas wisata/kuliner/UMKM, dan JSON-LD `CollectionPage` + `ItemList(13)` + `BreadcrumbList`. Detail: navigasi **Berita sebelumnya/berikutnya**, meta penulis + tanggal + estimasi waktu baca, kotak pembaruan & koreksi, sumber, tag, share, artikel terkait, sidebar terpopuler + agenda. Jembatan `/berita/detail.html?slug=…` aman untuk tiga jalur: slug valid (diantar ke artikel), slug tak dikenal (halaman "artikel tidak ditemukan" + daftar berita, bukan 404 buntu), dan tanpa slug (diarahkan ke indeks). |
| **Wisata/Kuliner** | Direktori dengan **bilah filter seragam** (cari + chip kategori/fasilitas/kisaran harga berikon Phosphor, tampil sebagai satu bilah lengket), kartu dengan status "Buka sekarang/Tutup" otomatis dari jam buka, detail dengan harga, jam buka, fasilitas, tips, galeri lightbox, peta lokasi, "terakhir diverifikasi", peringatan status verifikasi |
| **UMKM** | Direktori dengan **bilah filter seragam** (cari + chip kategori/desa + sakelar terverifikasi/premium), profil usaha, tombol WhatsApp siap pesan, form pendaftaran → WhatsApp dengan honeypot & validasi UU PDP |
| **Layanan** | Info lalu lintas (template laporan + status verifikasi), agenda (bilah seragam: pilih bulan berikon + ekspor `.ics` + Reset), loker (filter + peringatan penipuan), nomor penting (tabel + pencarian), form lapor (validasi → WhatsApp/email dengan honeypot) |
| **Peta** | Leaflet + OSM, marker cluster, legenda, filter per jenis, pencarian titik, tombol "Lihat di peta" & "Rute" ke Google Maps, fallback teks jika Leaflet/gagal |
| **Global** | **Tema terang saja** (latar putih, tanpa dark mode/toggle), **ikon Phosphor** di seluruh UI, skip-link, fokus terlihat, `prefers-reduced-motion`, bottom navigation mobile, badge kategori berwarna sesuai blueprint, skeleton loader, toast, back-to-top, simpan artikel (localStorage), print stylesheet |
| **SEO** | Meta & canonical per halaman, Open Graph/Twitter, JSON-LD: `NewsMediaOrganization`, `WebSite`+SearchAction, `NewsArticle`, `TouristAttraction`, `Restaurant`, `LocalBusiness`, `BreadcrumbList`; `robots.txt`, `sitemap.xml`, `site.webmanifest` |

---

## 4b. Gaya visual yang berlaku — arah **“Majalah + Bento”**

Tampilan dirombak sekali lagi mengikuti arah yang dipilih pemilik proyek
(**majalah + bento**, palet **navy sinematik + latar krem**, semua fitur UX baru).
Acuan isi/struktur tetap blueprint; yang berubah adalah tata letaknya.

| Aspek | Ketentuan |
|---|---|
| **Latar & palet** | Latar krem hangat `--sp-krem #F6F1E7` (bukan putih polos), seksi selang-seling `--sp-krem-2 #EDE5D6` dan `--sp-kertas #FFFCF6`, blok navy sinematik `#071C53`/`#020B22`, aksen teal `#2095AE` (ikon) + teal gelap `#0F6E80` (teks kecil 5,4:1), emas `#E8B400` untuk kategori UMKM & tombol langganan. Teks sekunder di atas krem: `--sp-ink-warm #55524A` (7,4:1). Garis pemisah: `--sp-garis rgba(7,28,83,.14)`. |
| **Tipografi** | **Playfair Display** untuk judul (masthead, judul seksi, drop cap artikel) + **Manrope** untuk badan — tetap di-host sendiri & disubset (22 KB + 21 KB). |
| **Primitif bento** | `.bento` (grid 12 kolom) + `.b-12/.b-9/.b-8/.b-6/.b-4/.b-3`, petak `.tile` dengan varian `tile-navy`, `tile-teal`, `tile-emas`, `tile-foto` (foto + tirai gradien), ukuran `tile-tinggi`/`tile-pendek`, serta `.angka-besar` untuk angka besar bergaya majalah. |
| **Primitif editorial** | `.masthead` (kepala majalah), `.judul-seksi` + `.nomor` (01–08) + `.garis-judul`, `.sub-judul` (nomor otomatis di semua halaman dalam), `.daftar-editorial`, `.linimasa`, `.papan-status`, `.fakta-kotak`, `.kartu-layanan`. |
| **Kepala halaman dalam** | `.page-header` kini **krem** dengan garis tebal 3 px navy, judul Playfair `clamp(1,9–3,2 rem)`, nomor seksi opsional, dan breadcrumb kecil. Gradien navy lama dihapus total (aturan lama dibuang dari CSS supaya tidak ada sisa teks putih di atas krem). |
| **Artikel majalah** | Kepala besar: badge kategori + judul `clamp(2–3,6 rem)` + dek + meta + tombol bagi; badan artikel dengan **drop cap**, `.figure-lebar`, kutipan bergaris emas; **daftar isi statis** di sidebar (`.toc-kotak`, dibuat saat build) + **scrollspy** dan **bar progres baca** 3 px di atas layar. |
| **Fitur UX baru** | 1) **Rail** geser horizontal (scroll-snap + tombol geser, tanpa pustaka) untuk destinasi, berita, dan sosial media; 2) **Bilah filter lengket** (`.bar-lengket`) di indeks berita & direktori; 3) **Panel lompat cepat** (`/`, `Ctrl`/`⌘`+`K`, atau ikon di navbar) yang mencari **halaman** *dan* **isi situs** (berita/wisata/kuliner/UMKM) lalu bisa dibuka dengan Enter; 4) **Linimasa agenda** terdekat; 5) **Papan status** lalu lintas berkartu (lancar/ramai/padat). Pintasan `/` untuk pencarian situs lama dipindahkan ke panel ini agar tidak ada dua panel yang terbuka bersamaan. |
| **Navbar** | Breakpoint desktop dinaikkan ke **xl (≥1200 px)** karena menunya panjang: di bawah itu menu memakai offcanvas (tanpa overflow horizontal). Di 1200–1439 px label tombol "Kirim Info" disembunyikan (tombol tetap tampil), `brand-tag` hilang ≤1599 px. |
| **Gambar** | Foto ilustrasi Unsplash (tautan langsung, tanpa unduh) dengan varian ukuran per tempat tampil. Gambar **berita utama di beranda di-preload** (`imagesrcset`/`imagesizes` identik dengan yang diminta kartu) karena itulah elemen LCP; beranda **tidak lagi memakai Swiper** sehingga CSS/JS korsel tidak diunduh. |
| **Bottom bar** | Hanya di ponsel (≥992 px disembunyikan). |
| **Ikon** | Tetap 100% **Phosphor** (subset 70 regular + 3 fill, `phosphor.css` 3,9 KB). Setiap ikon baru pada string JS harus ada di subset — `tools/subset_icons.py` memindainya. |

### Setiap CSS yang diubah wajib cepat diperiksa
Kurung yang tidak seimbang di `style.css` membuat SELURUH berkas ter-*nest* dan token
seperti `--sp-krem` tidak terdefinisi (gejala: latar kembali putih, teks krem tak terbaca).
Cek cepat: `python3 - <<'PY' … hitung { } … PY` (kedalaman akhir harus 0) atau di peramban
`document.styleSheets` → `cssRules.length` (versi sekarang **646 rule**; kalau 1, berarti
ada kurung yang bocor).

## 4b-2. Bilah filter seragam & HTML statis (SEO)

**Semua bilah filter halaman daftar dibuat oleh satu helper** `bar_filter()` di `tools/build.py`
sehingga bentuknya identik dengan bilah pencarian halaman berita: kolom cari berikon
(`.sp-bar-filter-cari`), pemilih "pil" berikon (`.sp-bar-filter-pilih`), tombol aksi
(`btn-navy` untuk aksi utama + `btn-outline-navy` **Reset**), lalu baris chip berlabel ikon
(`.chip-grup > .chip-label` + `.chip-scroll`). Semua ikon memakai **Phosphor** yang sudah ada
di subset. Halaman peta memakai pola sama dalam bentuk chip sakelar
(`.chip-toggle` / `.chip-switch`) + kolom cari bergaya bilah.

| Halaman | Kontrol (id dipertahankan agar handler lama tetap jalan) |
|---|---|
| `berita/index.html` | `#qBerita` · `#urutBerita` · chip `#filterKategori` · `#resetFilterBerita` |
| `wisata/`, `kuliner/`, `umkm/` (indeks) | `#qDirektori` · `#resetFilter` · chip `#chipDirektori` (kategori/desa/status usaha/sakelar) |
| `layanan/agenda.html` | `#filterBulanAgenda` · `#eksporIcs` · `#resetBulanAgenda` |
| `layanan/loker.html` | `#cariLoker` · `#filterJenisLoker` · `#resetLoker` |
| `layanan/nomor-penting.html` | `#cariNomor` · `#resetNomor` |
| `peta.html` | `#filterPeta` (sakelar) · `#cariTitikPeta` |

**HTML statis (tanpa JavaScript).** Dua daftar yang dulu baru muncul setelah JavaScript
(`#daftarLalin` di Info Lalu Lintas, `#daftarAgenda` di Agenda) kini **dirender saat build**
oleh `tools/render_stat.js` — skrip Node kecil yang **memakai ulang** fungsi komponen
`assets/js/components.js` (yang sama dipakai peramban), jadi hasil statis dan hasil JS
*identik* (sudah diuji dengan membandingkan `innerHTML` di peramban). Bila Node tidak
tersedia, build otomatis jatuh ke skeleton loader seperti sebelumnya.

---

## 4b-3. Audit menyeluruh & prerender SEO

Dua alat audit dipakai sebelum publikasi (keduanya keluar dengan kode 1 bila ada temuan):

```bash
python3 tools/audit.py                                  # audit statis, tanpa peramban
python3 tools/audit_peramban.py --base http://127.0.0.1:8090   # audit di Chromium
```

| Alat | Yang diperiksa |
|---|---|
| `tools/audit.py` | id ganda, jumlah & urutan judul, title/description/canonical/og, **ikon Phosphor di luar subset**, gambar (alt, width/height, berkas ada, kandidat `srcset`), tautan internal mati + anchor, label kendali, rujukan `aria-*`, tombol tanpa nama, JSON-LD, event inline, sisa skeleton, sitemap ↔ halaman, manifest, `url()` CSS, id yang dicari JS, slug & halaman detail pada JSON, `_headers`/`_redirects`/`robots.txt` |
| `tools/audit_peramban.py` | seluruh 61 halaman di 1280 px: galat konsol, permintaan gagal/404 (internal & luar), gambar rusak, **luber horizontal**; 10 halaman di 412 px: luber + **target sentuh** (WCAG 2.2 AA 2.5.8: sisi terkecil ≥ 24 px, dan kedua sisi ≥ 44 px); **tanpa JavaScript**: konten & skeleton; lalu **19 uji interaksi** (pencarian/urut/reset/paginasi berita, filter direktori wisata-kuliner-UMKM, agenda, loker, nomor penting, sakelar peta + pencarian titik, panel lompat cepat, validasi form, lightbox, simpan artikel) |

**Prerender (SEO & pengguna tanpa JavaScript).** `tools/build.py --prerender` menjalankan
`tools/prerender.py`: setiap halaman dibuka di Chromium lewat server sementara, lalu
kontainer yang biasanya diisi JS (`#daftarBerita`, `#daftarDirektori`, `#daftarLoker`,
`#sidebarPopuler`, `[data-list="…"]`, tab kategori beranda, dst. — 133 kontainer)
dituliskan kembali ke berkas `.html`. Hasil statis **identik** dengan hasil JS (diuji
dengan membandingkan `innerHTML`), jadi tidak ada lompatan tampilan, tetapi konten
kini terbaca mesin pencari dan pengguna tanpa JS. Bila Playwright tidak tersedia,
langkah ini dilewati dan situs kembali ke perilaku semula (JS mengisi kontainer).

---

## 4c. Hasil audit performa & aksesibilitas (Lighthouse, mobile, hosting bergzip)

Angka di bawah diukur pada build terakhir (server pratinjau bergzip, `tools/preview_server.py`).

| Halaman | Performance | Aksesibilitas | Best Practices | SEO | LCP | TBT |
|---|---|---|---|---|---|---|
| `/` (beranda majalah) | **90–91** | 100 | 100 | 100 | 3,5–4,0 s | 50–90 ms |
| `/berita/` | 93 | 100 | 100 | 100 | 3,1 s | 90 ms |
| artikel berita | 96 | 100 | 100 | 100 | 2,7 s | 10 ms |
| `/wisata/` (direktori) | 98 | 100 | 100 | 100 | 2,2 s | 60 ms |
| `/layanan/agenda` | 91 | 100 | 100 | 100 | 3,4 s | 80 ms |
| `/peta` | 76 | 100 | 96 | 100 | 5,0 s | 270 ms |


Angka Lighthouse bergerak ±3 poin antar-jalan (audit berulang di mesin yang sama); LCP beranda
sangat bergantung pada kecepatan CDN Unsplash karena gambarnya di-hotlink.
Catatan: `/peta` adalah pengecualian yang sudah ada sejak sebelum rombak — halaman itu memuat
Leaflet + ubin OpenStreetMap pihak ketiga (ubin 256 px pada DPR 1,75 juga membuat audit
*image-size-responsive* di Best Practices turun ke 96). Yang menjaga beranda ≥ 90: gambar LCP
di-preload dengan `imagesrcset`, kartu utama memakai `fetchpriority="high"`, gambar lain `lazy`,
CSS Swiper tidak lagi diunduh di beranda, dan evaluasi Swiper hanya terjadi bila ada elemen korsel.

Yang membuat CLS nol di seluruh halaman:
1. Skeleton loader ditulis statis di HTML dengan tinggi kartu yang sudah diukur
   (`skeleton_grid(n, body_h=…)`) — bukan hanya jumlah baris, tapi tinggi kotaknya.
2. Opsi filter (mis. bulan pada agenda) dirender statis, bukan diisi JS setelah paint.
3. `font-display: swap` + **font fallback dengan `size-adjust`** + `unicode-range` yang sama
   dengan isi berkas font, sehingga pergantian font tidak menggeser tata letak.
4. Gambar selalu punya `width`/`height` atau `aspect-ratio`.

Temuan lain yang sudah dibereskan pada putaran audit terakhir:
- `og:image` & JSON-LD rusak (`https://sudutpandaan.id/https://images.unsplash.com/…`) → helper `abs_url()`.
- 404 gambar sampul (path relatif di dalam JSON) → `img_src()` + `SP.imgGagal()`.
- Ikon kartu/agenda/loker tampil kosong → migrasi penuh ke Phosphor + alias `SP.ikonKelas()`.
- 35 halaman memuat Leaflet di jalur kritis → dimuat tertunda (`initPetaTertunda()`) kecuali `/peta` & beranda.
- Gambar sampul tanpa `srcset` (LCP) → varian 480/640/800/1000 + `preload`; thumbnail galeri 480×360 (q55).
- Teks emas `#E8B400` di atas putih (kontras 1,9:1) → kelas `.text-gold-dark` (#8A6A00, 5,1:1).

Cara mengulang: `python3 tools/preview_server.py 8090` lalu
`npx lighthouse@12 http://127.0.0.1:8090/index.html --form-factor=mobile --screenEmulation.mobile=true --throttling-method=simulate`.
Catatan: server pratinjau bawaan (`python3 -m http.server`) tidak mengompres berkas,
sehingga skornya lebih rendah daripada hosting asli (Netlify/Cloudflare otomatis gzip/brotli).
Rincian temuan dan perbaikannya ada di `docs/hasil-audit-beranda.md`.

Tiga uji otomatis yang dipakai sebelum publikasi:
```bash
python3 tools/smoke_test.py                   # status HTTP semua halaman (base: SP_BASE, default 8080)
python3 tools/cek_tampilan.py --peta --base http://127.0.0.1:8090   # ikon tidak kosong, gambar tidak rusak, alt, <h1>, konsol, peta terpasang
python3 tools/uji_berita.py http://127.0.0.1:8090   # 33 asersi bagian Berita (filter, URL, paginasi, jembatan, nav, SEO)
```

Ketiganya menjalankan Chromium melalui Playwright, sehingga butuh (a) paket `playwright`,
(b) peramban Chromium, dan (c) pustaka sistem yang **tidak ada** di image sandbox ini
(libnss3, libnspr4, font, dll.). Ketiganya disiapkan oleh satu perintah:

```bash
bash tools/siapkan-uji.sh              # ± 35 detik (kokoh, tidak punya akses root)
bash tools/siapkan-uji.sh --bersihkan  # hapus /home/user/_libs lagi setelah uji selesai
```

`tools/siapkan-uji.sh` mengunduh paket Debian dengan `apt-get download`, mengekstraknya ke
`/home/user/_libs/root` (tanpa `sudo`), lalu memangkas bagian yang tidak dipakai Chromium
headless (libLLVM/mesa/dokumen/font tambahan) dari 291 MB menjadi **± 80 MB**.

> **Penting:** `/home/user/_libs` **bukan bagian dari situs**. Ia hanya alat bantu uji —
> halaman, CSS, JS, dan server pratinjau tidak menyentuhnya sama sekali. Folder ini
> sengaja **tidak** disimpan di workspace; kalau diperlukan, buat lagi dengan perintah di atas.
> Menjaga workspace tetap kecil juga menghindari berkas hasil build terputar balik saat
> penyimpanan workspace penuh (pernah terjadi: `assets/js/*` kembali ke versi lama).

### Kalau tampilan tiba-tiba rusak (gejala rollback snapshot)

Workspace ini beberapa kali terputar balik ke versi lama saat penyimpanan penuh. Gejala khas:
ikon tampil **kosong**, atau gambar Unsplash diminta ke `127.0.0.1` (404). Pemeriksa cepat:

```bash
grep -c ikonKelas assets/js/config.js     # harus 3 (kalau 0 → JS sudah versi lama)
grep -rl "vendor/aos" --include="*.html" . # harus kosong (AOS sudah dibuang)
bash tools/pulihkan-js.sh                  # memulihkan assets/js/* dari tools/js-cadangan/
```

`tools/js-cadangan/` **wajib disalin ulang setiap habis mengedit `assets/js/*`**, kalau tidak
skrip pemulihan akan mengembalikan versi lama:

```bash
cp assets/js/*.js tools/js-cadangan/
```

Berkas yang **tidak boleh** ada lagi (sudah dibuang, tak ada satu pun halaman merujuknya):
`assets/vendor/aos.css`, `assets/vendor/aos.js`, `assets/vendor/icons/`.

---

## 5. Catatan teknis penting

1. **Tanpa build tool.** Tidak ada npm/Vite/PostCSS. CSS & JS murni, semua pustaka di-vendor ke `assets/vendor/`
   (menjawab risiko "ketergantungan CDN" pada blueprint Bagian 25).
2. **Font di-host sendiri** (Poppins & Inter, subset latin + latin-ext) agar tidak ada permintaan ke `fonts.googleapis.com`.
   Berkas Inter latin disubset lagi oleh `tools/subset_fonts.py` (hanya karakter yang dipakai) — lihat tabel gaya visual.
3. **Foto Unsplash = tautan luar.** Karena dipakai langsung dari `images.unsplash.com`, situs butuh koneksi internet untuk menampilkan foto ilustrasi di browser pengunjung; CSP `img-src` di `_headers`/`.htaccess` sudah mengizinkan domain tersebut. Kalau nanti ingin sepenuhnya mandiri (offline/hosting tertutup), unduh fotonya ke `assets/img/` dan ganti URL-nya di `assets/data/*.json`—struktur kode tidak perlu diubah.
4. **Keamanan.** Semua data yang dirender di-escape (`esc()`) → mencegah XSS dari berkas JSON.
   Form memakai honeypot + validasi klien. Tidak ada token rahasia di JS. Header keamanan via `_headers`/`.htaccess`.
5. **Aksesibilitas.** Target WCAG 2.2 AA: kontras ≥4.5:1, target sentuh ≥44px, navigasi keyboard,
   tombol slider memiliki `aria-label`, gambar memiliki `alt`, slider tidak memblokir kontrol pengguna.
6. **Performa.** Gambar sampul pakai `srcset` (480/640/800/1000) + `preload`, thumbnail galeri 480×360,
   semua gambar punya `width`/`height` dan `loading="lazy"` (kecuali hero). Leaflet & lightbox hanya
   dimuat di halaman yang memerlukannya; peta halaman detail baru dipasang saat mendekati viewport.
7. **Peta.** Tile memakai server publik OpenStreetMap (kebijakan penggunaan wajar) — untuk trafik tinggi
   gunakan penyedia tile berlangganan atau host sendiri (sudah dicatat di `peta.html`).
8. **URL bersih.** Berkas disimpan sebagai `.html`, tetapi URL tanpa `.html` (`/berita/<slug>`) sudah
   dilayani: `_redirects` (200 rewrite) untuk Netlify/Cloudflare, `.htaccess` untuk Apache, dan
   `tools/preview_server.py` untuk pratinjau lokal — seluruh 59 URL di `sitemap.xml` sudah diuji balik 200.
   Pola lama `/berita/detail.html?slug=…` diarahkan **301** ke halaman statis bila artikelnya ada
   (di Apache & server pratinjau); kalau slug tidak dikenal, halaman jembatan tetap tampil dengan
   pesan "Artikel tidak ditemukan" + daftar berita, jadi tidak ada tautan lama yang buntu.
   Aturan Laravel-nya sudah disiapkan untuk Fase 3 (blueprint Bagian 6.3).

---

## 6. Langkah berikutnya (sesuai roadmap blueprint)

- **Fase 2 lanjutan:** ganti seluruh data contoh dengan konten nyata, publikasikan 30+ artikel sebelum peluncuran.
- **Fase 3:** migrasi ke Laravel tanpa Vite — layout Blade, `@include` untuk navbar/footer,
  migration + seeder dari `assets/data/*.json`, controller & routing pada blueprint Bagian 17.
- **Fase 4:** moderasi UMKM + paket premium, manajemen iklan, API `/api/v1`, PWA (service worker), komentar bermoderasi.
"# sudut-pandaan" 
