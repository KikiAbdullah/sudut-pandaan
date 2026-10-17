# -*- coding: utf-8 -*-
"""
Sudut Pandaan — build.py
Generator situs statis (tanpa npm/Vite). Menghasilkan HTML siap deploy dari:
  - tools/data_seed.py  (data awal / seed, hanya dipakai bila JSON belum ada)
  - assets/data/*.json  (sumber data sesungguhnya — edit file ini untuk memperbarui konten)

Cara pakai:
    cd sudutpandaan && python3 tools/build.py

Hasil: index.html, berita/, wisata/, kuliner/, umkm/, layanan/, peta.html, dst.
Semua HTML dapat dibuka langsung lewat file:// maupun di-hosting statis
(Cloudflare Pages/Netlify/GitHub Pages) tanpa build tool apa pun.

Catatan: setelah mengubah assets/data/*.json, jalankan ulang skrip ini
agar halaman detail dan peta situs ikut diperbarui.
"""

import re
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "assets", "data")
sys.path.insert(0, os.path.join(BASE_DIR, "tools"))

import data_seed as seed  # noqa: E402

WIB = timezone(timedelta(hours=7))

# ---------------------------------------------------------------------------
# 1. SINKRONISASI JSON  (tulis hanya bila belum ada → JSON jadi sumber utama)
# ---------------------------------------------------------------------------
DATA_FILES = {
    "situs.json": seed.SITUS,
    "desa.json": seed.DESA,
    "kategori.json": seed.KATEGORI,
    "penulis.json": seed.PENULIS,
    "berita.json": seed.BERITA,
    "wisata.json": seed.WISATA,
    "kuliner.json": seed.KULINER,
    "umkm.json": seed.UMKM,
    "agenda.json": seed.AGENDA,
    "loker.json": {"catatan": seed.LOKER_CATATAN, "items": seed.LOKER},
    "lalu-lintas.json": {"catatan_template": seed.LALIN_TEMPLATE, "items": seed.LALIN},
    "nomor-penting.json": {"catatan": seed.NOMOR_CATATAN, "items": seed.NOMOR_PENTING},
    "sosmed.json": seed.SOSMED,
    "panduan.json": seed.PANDUAN,
}


def sync_json():
    os.makedirs(DATA_DIR, exist_ok=True)
    created = []
    for name, payload in DATA_FILES.items():
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            created.append(name)
    return created


def load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. UTILITAS
# ---------------------------------------------------------------------------
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def tgl_panjang(s, jam=True):
    d = parse_iso(s)
    if not d:
        return "—"
    out = f"{HARI[d.weekday()]}, {d.day} {BULAN[d.month - 1]} {d.year}"
    if jam:
        out += f", {d.hour:02d}.{d.minute:02d} WIB"
    return out


def tgl_singkat(s):
    d = parse_iso(s)
    return f"{d.day} {BULAN[d.month - 1]} {d.year}" if d else "—"


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def rp(n):
    return "Rp" + f"{n:,}".replace(",", ".")


def jam_html(jb):
    if not jb:
        return "—"
    baris = []
    for k, v in jb.items():
        if k == "catatan":
            continue
        label = {"sen-jum": "Senin–Jumat", "sab-min": "Sabtu–Minggu", "sen-min": "Setiap hari"}.get(k, k)
        baris.append(f"<div><strong>{label}:</strong> {esc(v)}</div>")
    if jb.get("catatan"):
        baris.append(f'<div class="text-muted-2 small mt-1">{esc(jb["catatan"])}</div>')
    return "".join(baris)


def badge_kat(nama, slug):
    return f'<span class="badge-cat cat-{esc(slug)}">{esc(nama)}</span>'


def jsonld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


def breadcrumb_ld(base_url, items):
    return jsonld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{base_url}{u}"}
            for i, (n, u) in enumerate(items)
        ],
    })


# ---------------------------------------------------------------------------
# 3. LAYOUT
# ---------------------------------------------------------------------------
NAV = [
    {"label": "Beranda", "href": "index.html", "key": "beranda"},
    {"label": "Berita", "href": "berita/index.html", "key": "berita", "anak": "kategori"},
    {"label": "Jelajah", "href": "wisata/index.html", "key": "jelajah", "anak": [
        ("Wisata", "wisata/index.html"), ("Kuliner", "kuliner/index.html"),
        ("Peta Pandaan", "peta.html"), ("Panduan", "panduan/index.html")]},
    {"label": "UMKM", "href": "umkm/index.html", "key": "umkm", "anak": [
        ("Direktori UMKM", "umkm/index.html"), ("Daftarkan Usaha", "umkm/daftar.html")]},
    {"label": "Layanan", "href": "layanan/lalu-lintas.html", "key": "layanan", "anak": [
        ("Info Lalu Lintas", "layanan/lalu-lintas.html"), ("Agenda Kegiatan", "layanan/agenda.html"),
        ("Lowongan Kerja", "layanan/loker.html"), ("Nomor Penting", "layanan/nomor-penting.html"),
        ("Lapor / Kirim Info", "layanan/lapor.html")]},
    {"label": "Tentang", "href": "tentang.html", "key": "tentang", "anak": [
        ("Tentang Kami", "tentang.html"), ("Redaksi & Pedoman", "redaksi.html"),
        ("Pasang Iklan", "pasang-iklan.html"), ("Kontak", "kontak.html")]},
]


def navbar(base, active, situs):
    """Navbar model acuan: bening di atas hero, memutih setelah digulir.

    Perilaku visualnya diatur CSS (`body.sp-hero-transparan`) dan kelas
    `.nav-scrolled` yang dipasang assets/js/nav.js. Pencarian memakai panel
    overlay (bukan modal Bootstrap) supaya terasa seperti bilah pencarian acuan.
    """
    anak_ext = {
        "kategori": [("Semua Berita", "berita/index.html")] +
                    [(k["nama"], f'berita/index.html?kategori={k["slug"]}') for k in KATEGORI],
    }

    def item_html(n):
        if n.get("anak"):
            anak = anak_ext.get(n["anak"], n["anak"]) if isinstance(n["anak"], str) else n["anak"]
            kelas = ' sp-dropdown-cols' if len(anak) > 8 else ''
            drops = "".join(
                f'<li><a class="dropdown-item" href="{base}{u}">{esc(t)}</a></li>' for t, u in anak
            )
            aktif = ' active' if active == n["key"] else ''
            return (f'<li class="nav-item dropdown">'
                    f'<a class="nav-link dropdown-toggle{aktif}" href="{base}{n["href"]}" role="button" '
                    f'data-bs-toggle="dropdown" aria-expanded="false">{esc(n["label"])}</a>'
                    f'<ul class="dropdown-menu{kelas}">{drops}</ul></li>')
        return (f'<li class="nav-item"><a class="nav-link {"active" if active == n["key"] else ""}" '
                f'href="{base}{n["href"]}">{esc(n["label"])}</a></li>')

    desktop = "".join(item_html(n) for n in NAV)

    oc = []
    for n in NAV:
        oc.append(f'<li class="nav-item"><a class="nav-link py-2" href="{base}{n["href"]}">{esc(n["label"])}</a></li>')
        anak_oc = anak_ext.get(n["anak"], []) if isinstance(n.get("anak"), str) else (n.get("anak") or [])
        for t, u in anak_oc:
            oc.append(f'<li><a class="nav-link ps-3 py-1 small" href="{base}{u}">— {esc(t)}</a></li>')
    offcanvas_list = "".join(oc)

    return f"""
<nav class="navbar navbar-expand-xl sp-navbar sticky-top" id="navbarUtama" aria-label="Navigasi utama">
  <div class="container">
    <a class="navbar-brand" href="{base}index.html">
      <img class="brand-logo brand-logo-gelap" src="{base}assets/img/logo.svg" alt="" width="40" height="40">
      <img class="brand-logo brand-logo-terang" src="{base}assets/img/logo-terang.svg" alt="" width="40" height="40">
      <span class="d-flex flex-column">
        <span class="brand-nama">Sudut Pandaan</span>
        <span class="brand-tag">Mata Komunitas Pandaan</span>
      </span>
      <span class="visually-hidden">— kembali ke beranda</span>
    </a>

    <div class="collapse navbar-collapse d-none d-xl-flex order-xl-2">
      <ul class="navbar-nav align-items-xl-center ms-xl-auto">{desktop}</ul>
    </div>

    <div class="d-flex align-items-center gap-2 order-xl-3 ms-auto ms-xl-3">
      <button class="btn-ikon-nav d-none d-xl-inline-flex" type="button" data-lompat-buka aria-label="Buka lompat cepat antar halaman (pintasan garis miring)">
        <i class="ph ph-list-numbers" aria-hidden="true"></i>
      </button>
      <button class="btn-ikon-nav" type="button" id="tombolCari" aria-label="Buka pencarian" aria-expanded="false" aria-controls="panelCari">
        <i class="ph ph-magnifying-glass" aria-hidden="true"></i>
      </button>
      <a class="btn btn-navy btn-sm d-none d-xl-inline-flex align-items-center gap-1 nav-kirim" href="{base}layanan/lapor.html">
        <i class="ph ph-paper-plane-tilt" aria-hidden="true"></i><span class="nav-kirim-teks">Kirim Info</span></a>
      <button class="navbar-toggler ms-1" type="button" data-bs-toggle="offcanvas"
              data-bs-target="#menuMobile" aria-controls="menuMobile" aria-label="Buka menu navigasi">
        <span class="navbar-toggler-icon"></span>
      </button>
    </div>
  </div>
</nav>

<!-- Offcanvas menu mobile DIPLACEMENT di luar <nav>: bila berada di dalam
     .navbar-expand-xl, Bootstrap menjadikannya elemen statis saat desktop.
     Breakpoint xl (≥1200 px) dipilih karena menu desktop kita panjang:
     di bawah 1200 px ruangnya tidak cukup dan tombol jadi terpotong. -->
<div class="offcanvas offcanvas-end sp-offcanvas" tabindex="-1" id="menuMobile" aria-labelledby="menuMobileLabel">
  <div class="offcanvas-header">
    <h5 class="offcanvas-title text-white" id="menuMobileLabel">Menu</h5>
    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="offcanvas" aria-label="Tutup menu"></button>
  </div>
  <div class="offcanvas-body">
    <ul class="navbar-nav mb-3">{offcanvas_list}</ul>
    <button class="btn btn-gold w-100 mb-2" type="button" data-lompat-buka data-bs-dismiss="offcanvas">
      <i class="ph ph-list-numbers me-1" aria-hidden="true"></i>Lompat cepat antar halaman</button>
    <a class="btn btn-outline-white w-100 mb-3" href="{base}layanan/lapor.html">
      <i class="ph ph-paper-plane-tilt me-1" aria-hidden="true"></i>Kirim Info / Lapor</a>
    <hr class="border-secondary">
    <p class="small mb-2" style="color:rgba(255,255,255,.7)">Ikuti kami</p>
    <div class="d-flex gap-2">
      <a class="btn-ikon-nav" href="{situs['instagram']}" target="_blank" rel="noopener noreferrer" aria-label="Instagram"><i class="ph ph-instagram-logo" aria-hidden="true"></i></a>
      <a class="btn-ikon-nav" href="{situs['threads']}" target="_blank" rel="noopener noreferrer" aria-label="Threads"><i class="ph ph-threads-logo" aria-hidden="true"></i></a>
      <a class="btn-ikon-nav" href="https://wa.me/{situs['wa_admin']}" target="_blank" rel="noopener noreferrer" aria-label="WhatsApp"><i class="ph ph-whatsapp-logo" aria-hidden="true"></i></a>
    </div>
  </div>
</div>

<!-- Panel pencarian (pola bilah cari acuan) -->
<div class="sp-cari-panel" id="panelCari" role="dialog" aria-modal="true" aria-label="Pencarian situs">
  <form action="{base}berita/index.html" method="get" role="search">
    <i class="ph ph-magnifying-glass fs-4 text-muted-2" aria-hidden="true"></i>
    <label class="visually-hidden" for="inputCari">Kata kunci pencarian</label>
    <input id="inputCari" name="q" type="search" placeholder="Temukan berita, wisata, kuliner, UMKM…" required>
    <button class="btn btn-navy" type="submit">Cari</button>
    <button class="btn-ikon-nav" type="button" id="tutupCari" aria-label="Tutup pencarian">
      <i class="ph ph-x" aria-hidden="true"></i>
    </button>
  </form>
</div>
"""


def img_src(path, base=''):
    """URL gambar: URL luar (mis. Unsplash) dibiarkan apa adanya, aset lokal diberi awalan base."""
    p = '' if path is None else str(path)
    if p.startswith(('http://', 'https://', '//', 'data:')):
        return p
    return base + p


def abs_url(path, situs):
    """URL absolut untuk og:image / JSON-LD. Path lokal diberi domain situs,
    sedangkan hotlink (Unsplash) dan data-URI dibiarkan apa adanya — tanpa ini
    og:image jadi 'https://sudutpandaan.id/https://images.unsplash.com/…'."""
    t = "" if path is None else str(path)
    if t.startswith(("http://", "https://", "//", "data:")):
        return t
    return situs["base_url"].rstrip("/") + "/" + t.lstrip("/")


def img_varian(url, w, h, q=60):
    """Varian ringan sebuah URL gambar Unsplash (galeri/thumbnail tidak perlu
    gambar 1000 px). URL lokal atau tanpa parameter dibiarkan utuh."""
    t = "" if url is None else str(url)
    if "images.unsplash.com" not in t:
        return t
    t = re.sub(r"([?&])w=\d+", lambda m: m.group(1) + "w=" + str(w), t)
    t = re.sub(r"([?&])h=\d+", lambda m: m.group(1) + "h=" + str(h), t)
    t = re.sub(r"([?&])q=\d+", lambda m: m.group(1) + "q=" + str(q), t)
    return t


VARIAN_HERO = (480, 640, 800, 1000)
SIZES_HERO = "(min-width: 1200px) 760px, (min-width: 768px) 66vw, 100vw"


def hero_srcset(url, w=800, h=450, q=60, lebar=VARIAN_HERO):
    """srcset/sizes untuk gambar utama artikel.

    Hanya berlaku untuk hotlink Unsplash (URL lokal tidak punya varian ukuran).
    Halaman detail memakai kolom 8/12, jadi 800–1000 px cukup untuk desktop,
    sedangkan ponsel cukup memakai varian 480/640 px — LCP jadi jauh lebih cepat.
    """
    t = "" if url is None else str(url)
    if "images.unsplash.com" not in t:
        return "", ""
    srcset = ", ".join(
        f"{img_varian(t, x, max(1, round(x * h / w)), q)} {x}w" for x in lebar
    )
    return srcset, SIZES_HERO


HINT_PETA = ('<span class="sp-map-hint" aria-hidden="true">'
             '<i class="ph ph-map-trifold"></i>Memuat peta…</span>')


def div_peta(lat, lng, nama, label, kelas="sp-map sp-map-sm"):
    """Kontainer peta mode "tunggal" — map.js membaca data-lat/lng/nama dari
    elemen terdekat (closest), jadi atributnya wajib ada di elemen ini."""
    return (f'<div id="peta" class="{kelas}" data-peta="tunggal" data-lat="{lat}" '
            f'data-lng="{lng}" data-nama="{esc(nama)}" role="application" '
            f'aria-label="{esc(label)}">{HINT_PETA}</div>')


def img_hero(path, alt, base='', w=800, h=450, q=60):
    """<img> gambar utama: eager, prioritas tinggi, dengan srcset bila Unsplash."""
    url = img_varian(img_src(path, base), w, h, q)
    srcset, sizes = hero_srcset(url, w, h, q)
    atr = f' srcset="{srcset}" sizes="{sizes}"' if srcset else ''
    return (f'<img src="{url}" alt="{esc(alt)}" width="{w}" height="{h}"{atr} '
            f'loading="eager" fetchpriority="high" decoding="async" '
            f'onerror="SP.imgGagal(this)">')


def preload_gambar(path, base='', w=800, h=450, q=60):
    """<link rel=preload> untuk gambar hero (mempercepat LCP)."""
    url = img_varian(img_src(path, base), w, h, q)
    srcset, sizes = hero_srcset(url, w, h, q)
    extra = f' imagesrcset="{srcset}" imagesizes="{sizes}"' if srcset else ''
    return (f'<link rel="preload" as="image" fetchpriority="high" '
            f'href="{url}"{extra}>')


def jam_ld(jam):
    """Ubah jam buka (format 'sen-jum': '08.00–17.00') menjadi
    openingHoursSpecification untuk JSON-LD."""
    if not jam:
        return []
    hari = {"sen-jum": ["Monday", "Friday"], "sab-min": ["Saturday", "Sunday"],
            "sen-min": ["Monday", "Sunday"]}
    hasil = []
    for kunci, daftar in hari.items():
        nilai = jam.get(kunci)
        if not nilai:
            continue
        m = re.match(r"(\d{1,2})[.:](\d{2})\s*[–—-]\s*(\d{1,2})[.:](\d{2})", str(nilai))
        if not m:
            continue
        hasil.append({
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": daftar if len(daftar) > 1 else daftar[0],
            "opens": f"{int(m.group(1)):02d}:{m.group(2)}",
            "closes": f"{int(m.group(3)):02d}:{m.group(4)}",
        })
    return hasil


def harga_ld(w):
    """priceRange teks untuk JSON-LD (mis. 'Rp0–25.000')."""
    mn, mx = w.get("harga_min"), w.get("harga_max")
    # 0 adalah nilai sah (= gratis), jadi jangan dianggap kosong.
    if mn is None and mx is None:
        return None
    if mx in (None, ""):
        return rp(mn)
    if mn in (None, ""):
        return rp(mx)
    if mn == mx:
        return rp(mn)
    return f"{rp(mn)}–{rp(mx)}"


BOTTOM_NAV = [
    ("Beranda", "index.html", "ph ph-house", "beranda"),
    ("Berita", "berita/index.html", "ph ph-newspaper", "berita"),
    ("Jelajah", "wisata/index.html", "ph ph-map-trifold", "jelajah"),
    ("Layanan", "layanan/lalu-lintas.html", "ph ph-headset", "layanan"),
]


def bottom_nav(base, active):
    items = "".join(
        f'<li><a class="{"active" if active == k else ""}" href="{base}{u}">'
        f'<i class="{i}" aria-hidden="true"></i><span>{esc(l)}</span></a></li>'
        for l, u, i, k in BOTTOM_NAV
    )
    items += ('<li><button type="button" class="border-0 bg-transparent w-100" data-bs-toggle="offcanvas" '
              'data-bs-target="#menuMobile" aria-label="Buka menu lengkap">'
              '<span class="d-flex flex-column align-items-center justify-content-center" style="min-height:56px;gap:2px">'
              '<i class="ph ph-list" aria-hidden="true" style="font-size:1.3rem"></i><span style="font-size:.68rem;font-weight:600">Menu</span>'
              '</button></li>')
    return f'<nav class="sp-bottomnav d-lg-none" aria-label="Navigasi bawah">\n<ul>{items}</ul>\n</nav>'


def breaking_bar(base, aktif):
    if not aktif:
        return ""
    b = aktif[0]
    exp = b.get("breaking_until") or ""
    return f"""
<div class="breaking-bar" id="breakingBar" role="status" aria-live="polite" data-expires="{exp}">
  <div class="container d-flex align-items-center gap-3">
    <span class="badge bg-white text-danger flex-shrink-0">INFO TERKINI</span>
    <div class="marquee"><span>{esc(b['judul'])} — {esc(b['ringkasan'])}
      <a href="{base}berita/{b['slug']}.html">Baca selengkapnya</a></span></div>
    <button type="button" class="btn-close flex-shrink-0" data-dismiss-breaking aria-label="Tutup info terkini"></button>
  </div>
</div>"""


def footer(base, situs, kategori):
    kat = "".join(f'<li><a href="{base}berita/index.html?kategori={k["slug"]}">{esc(k["nama"])}</a></li>'
                  for k in kategori[:6])
    return f"""
<footer class="sp-footer">
  <div class="container">
    <div class="row g-4">
      <div class="col-lg-4">
        <a class="d-inline-flex align-items-center gap-2 text-decoration-none mb-3" href="{base}index.html">
          <img src="{base}assets/img/logo.svg" alt="" width="40" height="40">
          <span class="h5 text-white mb-0" style="font-family:var(--sp-font-display)">Sudut Pandaan</span>
        </a>
        <p class="small">{esc(situs['deskripsi'])}</p>
        <p class="small mb-3"><i class="ph ph-map-pin me-1" aria-hidden="true"></i>{esc(situs['alamat'])}<br>
          <i class="ph ph-envelope-simple me-1" aria-hidden="true"></i>{esc(situs['email'])}<br>
          <i class="ph ph-clock me-1" aria-hidden="true"></i>Jam respons redaksi: {esc(situs['jam_respons'])}</p>
        <div class="footer-sosmed d-flex flex-wrap">
          <a href="{situs['instagram']}" target="_blank" rel="noopener noreferrer" aria-label="Instagram"><i class="ph ph-instagram-logo" aria-hidden="true"></i></a>
          <a href="{situs['threads']}" target="_blank" rel="noopener noreferrer" aria-label="Threads"><i class="ph ph-threads-logo" aria-hidden="true"></i></a>
          <a href="https://wa.me/{situs['wa_admin']}" target="_blank" rel="noopener noreferrer" aria-label="WhatsApp"><i class="ph ph-whatsapp-logo" aria-hidden="true"></i></a>
          <a href="{situs['facebook']}" target="_blank" rel="noopener noreferrer" aria-label="Facebook"><i class="ph ph-facebook-logo" aria-hidden="true"></i></a>
          <a href="{situs['tiktok']}" target="_blank" rel="noopener noreferrer" aria-label="TikTok"><i class="ph ph-tiktok-logo" aria-hidden="true"></i></a>
        </div>
      </div>
      <div class="col-6 col-lg-2">
        <h2 class="footer-judul">Jelajahi</h2>
        <ul class="small">
          <li><a href="{base}berita/index.html">Berita</a></li>
          <li><a href="{base}wisata/index.html">Wisata</a></li>
          <li><a href="{base}kuliner/index.html">Kuliner</a></li>
          <li><a href="{base}umkm/index.html">UMKM</a></li>
          <li><a href="{base}peta.html">Peta Pandaan</a></li>
          <li><a href="{base}panduan/index.html">Panduan</a></li>
        </ul>
      </div>
      <div class="col-6 col-lg-2">
        <h2 class="footer-judul">Layanan Warga</h2>
        <ul class="small">
          <li><a href="{base}layanan/lalu-lintas.html">Info Lalu Lintas</a></li>
          <li><a href="{base}layanan/agenda.html">Agenda Kegiatan</a></li>
          <li><a href="{base}layanan/loker.html">Lowongan Kerja</a></li>
          <li><a href="{base}layanan/nomor-penting.html">Nomor Penting</a></li>
          <li><a href="{base}layanan/lapor.html">Lapor / Kirim Info</a></li>
          <li><a href="{base}link/index.html">Link Bio</a></li>
        </ul>
      </div>
      <div class="col-lg-4">
        <h2 class="footer-judul">Kategori Berita</h2>
        <ul class="small">{kat}</ul>
        <h2 class="footer-judul mt-4">Tentang</h2>
        <ul class="small">
          <li><a href="{base}tentang.html">Tentang Kami</a></li>
          <li><a href="{base}redaksi.html">Redaksi &amp; Pedoman</a></li>
          <li><a href="{base}pasang-iklan.html">Pasang Iklan</a></li>
          <li><a href="{base}kontak.html">Kontak</a></li>
        </ul>
      </div>
    </div>
    <hr class="border-secondary mt-4 opacity-25">
    <div class="legal small d-flex flex-wrap gap-3 justify-content-between pb-4">
      <span>© <span id="tahun" data-tahun>2026</span> {esc(situs['nama'])}. Seluruh hak cipta dilindungi.</span>
      <span class="d-flex flex-wrap gap-3">
        <a href="{base}privasi.html">Kebijakan Privasi</a>
        <a href="{base}disclaimer.html">Disclaimer</a>
        <a href="{base}syarat-ketentuan.html">Syarat &amp; Ketentuan</a>
        <a href="{base}redaksi.html">Pedoman Media Siber</a>
      </span>
    </div>
  </div>
</footer>"""


def scripts(base, extra=()):
    files = [f'{base}assets/vendor/bootstrap.bundle.min.js']
    for f in extra:
        files.append(f"{base}{f}")
    files += [
        f'{base}assets/js/data-embed.js',
        f'{base}assets/js/config.js',
        f'{base}assets/js/components.js',
        f'{base}assets/js/pages.js',
        f'{base}assets/js/share.js',
        f'{base}assets/js/nav.js',
        f'{base}assets/js/majalah.js',
        f'{base}assets/js/main.js',
    ]
    # Swiper (hanya beranda) memakai `defer`: modulnya dievaluasi setelah HTML
    # selesai diuraikan, sehingga tidak menahan render pertama dan LCP lebih cepat.
    return "\n".join(
        f'<script src="{f}"{" defer" if "swiper" in f else ""}></script>' for f in files
    )


# CSS vendor dimuat lebih dulu, style.css situs selalu terakhir agar aturan
# situs tidak kalah oleh CSS pustaka (Swiper/Leaflet dimuat lewat extra_css).
CSS_VENDOR = """
<link rel="preconnect" href="https://images.unsplash.com" crossorigin>
<link rel="preload" href="{base}assets/fonts/manrope-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{base}assets/fonts/playfair-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{base}assets/css/fonts.css">
<link rel="stylesheet" href="{base}assets/vendor/bootstrap.min.css">
<link rel="stylesheet" href="{base}assets/vendor/phosphor/phosphor.css">"""

CSS_BASE = """
<link rel="stylesheet" href="{base}assets/css/style.css">"""

def versi_aset(path_relatif):
    """Hitung versi ringkas sebuah berkas aset (8 huruf pertama sha1 isinya).

    Dipakai untuk menyisipkan `?v=…` pada URL CSS/JS hasil build. Gunanya: ketika
    tampilan dirombak, URL asetnya BERUBAH sehingga cache lama di browser/pane
    pratinjau (yang sebelumnya ditandai `immutable` setahun) otomatis dilewati —
    pengunjung tidak perlu hard-refresh.
    """
    p = os.path.join(BASE_DIR, path_relatif)
    try:
        with open(p, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()[:8]
    except OSError:
        return "0"


_VERSI_CACHE = {}


def versi_cached(path_relatif):
    """Versi berkas untuk URL relatif halaman mana pun.

    Halaman di subfolder memakai `../assets/...`, sedangkan root memakai
    `assets/...` — keduanya menunjuk berkas yang SAMA, jadi kuncinya
    dinormalkan lebih dulu (buang awalan `./` dan `../`), kalau tidak hash
    untuk subfolder gagal dibaca dan keluar "0".
    """
    kunci = re.sub(r"^(?:\./|\.\./)+", "", path_relatif)
    if kunci not in _VERSI_CACHE:
        _VERSI_CACHE[kunci] = versi_aset(kunci)
    return _VERSI_CACHE[kunci]


def beri_versi_aset(html):
    """Tambahkan ?v=<hash> pada setiap href/src CSS & JS lokal (tanpa query).

    Hanya menyentuh berkas di dalam situs (assets/…), tidak menyentuh URL luar
    (Unsplash/OpenStreetMap) maupun gambar.
    """
    def ganti(m):
        atr, url = m.group(1), m.group(2)
        if "?" in url or url.startswith(("http://", "https://", "//", "data:")):
            return m.group(0)
        if not (url.endswith(".css") or url.endswith(".js")):
            return m.group(0)
        return f'{atr}="{url}?v={versi_cached(url)}"'

    return re.sub(r'(href|src)="([^"]+\.(?:css|js))"', ganti, html)


def page(*, base, out_path, title, description, body, active="", situs=None,
         extra_head="", extra_css="", extra_scripts=(), canonical="",
         og_type="website", og_image="assets/img/og-default.jpg", ld=(), noindex=False,
         hide_breaking=False, body_class="sp-has-bottomnav", robots_extra="", hero=False):
    """Tulis satu halaman HTML."""
    canonical = canonical or situs["base_url"] + "/" + (out_path.replace("index.html", "") if out_path != "index.html" else "")
    head_extra = "\n".join(ld)
    head_tambahan = "\n".join(x for x in (extra_head,) if x)
    breaking_html = BREAKING_HTML.replace("{base}", base)
    if hero:
        body_class = (body_class + " sp-hero-transparan").strip()
    robots = ('<meta name="robots" content="noindex, follow">' if noindex else
              f'<meta name="robots" content="index, follow, max-image-preview:large{robots_extra}">')
    html = f"""<!DOCTYPE html>
<html lang="id" data-bs-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#071C53">
{robots}
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(situs['nama'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{abs_url(og_image, situs)}">
<meta property="og:locale" content="id_ID">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{base}assets/img/favicon/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="{base}assets/img/favicon/favicon-192.png" sizes="192x192">
<link rel="apple-touch-icon" href="{base}assets/img/favicon/apple-touch-icon.png">
<link rel="manifest" href="{base}site.webmanifest">
{CSS_VENDOR.format(base=base)}
{extra_css}
{CSS_BASE.format(base=base)}
{head_tambahan}
{head_extra}
</head>
<body class="{body_class}">
<a class="skip-link" href="#konten">Lewati ke konten utama</a>
{navbar(base, active, situs)}
{"" if hide_breaking else breaking_html}
<main id="konten">
{body}
</main>
{footer(base, situs, KATEGORI)}
{bottom_nav(base, active)}
<button id="backToTop" type="button" aria-label="Kembali ke atas halaman"><i class="ph ph-arrow-up" aria-hidden="true"></i></button>
<div class="toast-container position-fixed bottom-0 start-50 translate-middle-x p-3">
  <div id="spToast" class="toast sp-toast" role="status" aria-live="polite" aria-atomic="true">
    <div class="toast-body"><i class="ph-fill ph-check-circle" aria-hidden="true"></i><span id="spToastText"></span></div>
  </div>
</div>
{scripts(base, extra_scripts)}
</body>
</html>
"""
    # Setiap sub-judul <h2> diberi nomor majalah (01, 02, …) otomatis
    html = nomori_sub_judul(html)
    # ?v=… pada CSS/JS → cache lama terlewati (nilai balik WAJIB dipakai)
    html = beri_versi_aset(html)
    path = os.path.join(BASE_DIR, out_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def h2_tersembunyi_berid(teks, idnya="judulSorotan"):
    """h2 tersembunyi yang punya id — dipakai untuk aria-labelledby seksi
    yang tidak punya judul visual, sekaligus menjaga urutan heading h1→h2→h3."""
    return f'<h2 class="visually-hidden" id="{idnya}">{esc(teks)}</h2>'


def h2_tersembunyi(teks):
    """Heading h2 untuk pembaca layar: menjaga urutan heading (h1 → h2 → h3)
    pada halaman daftar tanpa mengubah tampilan visual."""
    return f'<h2 class="visually-hidden">{esc(teks)}</h2>'


def page_header(title, lead, crumbs, base, nomor="", aksi=None, kelas="", atas="", bawah=""):
    """Kepala halaman dalam bergaya majalah: breadcrumb tipis, judul serif besar,
    nomor seksi opsional (mis. "04"), dan garis pemisah tebal di bawah.

    Dipakai SEMUA halaman dalam (indeks, detail, layanan, statis) supaya terasa
    satu keluarga dengan beranda. Gradien navy lama dibuang — latar krem hangat.
    """
    items = []
    for i, (label, url) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        if last:
            items.append(f'<li class="breadcrumb-item active" aria-current="page">{esc(label)}</li>')
        else:
            items.append(f'<li class="breadcrumb-item"><a href="{base}{url}">{esc(label)}</a></li>')
    nomor_html = f'<span class="nomor" aria-hidden="true">{nomor}</span>' if nomor else ''
    aksi_html = ''
    if aksi:
        aksi_html = '<div class="kepala-aksi">' + "".join(aksi) + '</div>'
    return f"""
<header class="page-header {kelas}">
  <div class="container">
    <nav aria-label="Breadcrumb">
      <ol class="breadcrumb mb-2">{''.join(items)}</ol>
    </nav>
    <div class="kepala-isi">
      {nomor_html}
      <div class="kepala-teks">
        {atas}
        <h1>{title}</h1>
        {f'<p class="kepala-lead">{lead}</p>' if lead else ''}
        {bawah}
      </div>
      {aksi_html}
    </div>
  </div>
</header>"""


def skeleton_grid(n=6, col="col-12 col-md-6 col-lg-4", body_h=None):
    # Tinggi skeleton didekatkan dengan tinggi kartu asli supaya isi halaman
    # tidak "melompat" saat data selesai dirender (CLS).
    gaya = f' style="min-height:{body_h}"' if body_h else ''
    card = ('<div class="{c}"><div class="skeleton-card"><div class="sp-skeleton sk-img"></div>'
            f'<div class="sk-body"{{gaya}}><div class="sp-skeleton sk-line" style="width:34%"></div>'
            '<div class="sp-skeleton sk-line" style="width:92%"></div>'
            '<div class="sp-skeleton sk-line" style="width:78%"></div>'
            '<div class="sp-skeleton sk-line" style="width:64%"></div>'
            '<div class="sp-skeleton sk-line" style="width:46%"></div></div></div></div>')
    return "".join(card.format(c=col, gaya=gaya) for _ in range(n))


def ad_slot(label="Iklan", extra="", h="250px"):
    return (f'<div class="ad-slot mb-3 {extra}" style="min-height:{h}" role="complementary" aria-label="Ruang iklan">'
            f'<div><div class="ad-slot-label mb-1">{esc(label)}</div>'
            f'<div class="small">Slot iklan 300×250 — tersedia untuk UMKM &amp; mitra lokal.<br>'
            f'<a href="{{base}}pasang-iklan.html" class="text-decoration-none">Lihat paket</a></div></div></div>')


# ---------------------------------------------------------------------------
# 4. KOMPONEN HALAMAN YANG DIREKAM (card grid, list, dsb.)
# ---------------------------------------------------------------------------
def share_bar(base, title, extra_class=""):
    return f"""
<div class="sp-share d-flex flex-wrap gap-2 {extra_class}" data-share-title="{esc(title)}" aria-label="Bagikan artikel ini">
  <button class="sh-wa" type="button" data-share="wa" aria-label="Bagikan ke WhatsApp"><i class="ph ph-whatsapp-logo" aria-hidden="true"></i></button>
  <button class="sh-fb" type="button" data-share="fb" aria-label="Bagikan ke Facebook"><i class="ph ph-facebook-logo" aria-hidden="true"></i></button>
  <button class="sh-x" type="button" data-share="x" aria-label="Bagikan ke X"><i class="ph ph-x-logo" aria-hidden="true"></i></button>
  <button class="sh-tg" type="button" data-share="tg" aria-label="Bagikan ke Telegram"><i class="ph ph-telegram-logo" aria-hidden="true"></i></button>
  <button class="sh-copy" type="button" data-copy-link aria-label="Salin tautan artikel"><i class="ph ph-link-simple" aria-hidden="true"></i></button>
  <button class="sh-save" type="button" data-save-article aria-label="Simpan artikel"><i class="ph ph-bookmark-simple" aria-hidden="true"></i></button>
</div>"""


def sidebar(base, situs, toc=""):
    """Sidebar kanan. `toc` = HTML kotak daftar isi (dipakai artikel panjang);
    kotaknya menempel (sticky) saat pembaca menggulir."""
    toc_html = f'<div class="toc-lengket mb-3">{toc}</div>' if toc else ""
    return f"""
<aside class="col-lg-4" aria-label="Sidebar">
  {toc_html}
  {ad_slot("Iklan", "", "250px").replace("{base}", base)}
  <div class="sidebar-widget">
    <h3><i class="ph ph-fire text-gold me-1" aria-hidden="true"></i>Terpopuler</h3>
    <ol class="rank-list list-unstyled mb-0" id="sidebarPopuler">
      <li><a href="{base}berita/index.html">Memuat…</a></li>
    </ol>
  </div>
  <div class="sidebar-widget">
    <h3><i class="ph ph-calendar-dots text-gold me-1" aria-hidden="true"></i>Agenda Terdekat</h3>
    <div id="sidebarAgenda" class="small text-muted-2">Memuat…</div>
  </div>
  <div class="sidebar-widget">
    <h3><i class="ph ph-broadcast text-gold me-1" aria-hidden="true"></i>Ikuti Kami</h3>
    <p class="small mb-3">Update cepat tersedia di Threads &amp; WhatsApp Channel.</p>
    <div class="d-grid gap-2">
      <a class="btn btn-sm btn-outline-primary" href="{situs['instagram']}" target="_blank" rel="noopener noreferrer"><i class="ph ph-instagram-logo me-1" aria-hidden="true"></i>Instagram</a>
      <a class="btn btn-sm btn-outline-primary" href="{situs['threads']}" target="_blank" rel="noopener noreferrer"><i class="ph ph-threads-logo me-1" aria-hidden="true"></i>Threads</a>
      <a class="btn btn-sm btn-wa" href="https://wa.me/{situs['wa_admin']}?text=Saya%20mau%20ikut%20info%20WA%20Channel%20Sudut%20Pandaan" target="_blank" rel="noopener noreferrer"><i class="ph ph-whatsapp-logo me-1" aria-hidden="true"></i>Minta Info WA</a>
    </div>
  </div>
  {ad_slot("Iklan", "d-none d-lg-block", "600px").replace("{base}", base)}
</aside>"""


# ===========================================================================
# 5. PEMBANGUN HALAMAN
# ===========================================================================
def daftar_isi_artikel(html):
    """Beri id pada setiap <h2> di badan artikel + susun kotak daftar isi statis.

    Statis (bukan JS) supaya daftar isi tetap ada tanpa JavaScript dan ikut
    terbaca crawler. majalah.js hanya menambah scrollspy/penanda aktif.
    """
    daftar = []

    def _ganti(m):
        attrs, isi = m.group(1), m.group(2)
        teks = re.sub(r"<[^>]+>", "", isi).strip()
        if "id=" in attrs:
            return m.group(0)
        slug = re.sub(r"[^a-z0-9]+", "-", teks.lower()).strip("-")[:60] or f"bagian-{len(daftar) + 1}"
        daftar.append((slug, teks))
        return f'<h2 id="{slug}"{attrs}>{isi}</h2>'

    html_baru = re.sub(r"<h2([^>]*)>(.*?)</h2>", _ganti, html, flags=re.S)
    if not daftar:
        return html, ""
    isi_toc = "".join(f'<li><a href="#{slug}" data-toc-link="{slug}">{esc(t)}</a></li>' for slug, t in daftar)
    toc = f'<div class="toc-kotak" data-toc><h2>Isi Artikel</h2><ol>{isi_toc}</ol></div>'
    return html_baru, toc


def nomori_sub_judul(html):
    """Ubah SETIAP <h2 class="sp-section-title"> menjadi sub-judul bernomor
    (01, 02, 03 …) sesuai urutan kemunculan di halaman itu.

    Satu implementasi untuk seluruh situs → semua halaman dalam otomatis
    punya penomoran majalah yang konsisten tanpa harus menyentuh 30-an
    pemanggilan judul satu per satu.
    """
    nomor = itertools.count(1)

    def _g(m):
        attrs, isi = m.group(1), m.group(2)
        n = f"{next(nomor):02d}"
        return (f'<div class="sub-judul"><span class="nomor" aria-hidden="true">{n}</span>'
                f'<h2{attrs}>{isi}</h2></div>')

    return re.sub(r'<h2([^>]*\bsp-section-title\b[^>]*)>(.*?)</h2>', _g, html, flags=re.S)


NODE = shutil.which("node")


def render_statis(berkas_data, fungsi, base="", urut=None, arah="naik", batas=None, cadangan=""):
    """Render potongan HTML statis memakai tools/render_stat.js (Node) sehingga
    hasilnya IDENTIK dengan render JavaScript di peramban (SEO + tanpa JS).

    Bila Node tidak tersedia atau gagal, kembalikan `cadangan` (mis. skeleton)
    supaya build tetap jalan tanpa perkakas tambahan.
    """
    if not NODE:
        return cadangan
    opsi = {"base": base}
    if urut:
        opsi["urutKunci"] = urut
        opsi["arah"] = arah
    if batas:
        opsi["batas"] = batas
    try:
        hasil = subprocess.run(
            [NODE, os.path.join(BASE_DIR, "tools", "render_stat.js"),
             BASE_DIR, berkas_data, fungsi, json.dumps(opsi)],
            capture_output=True, text=True, check=True, timeout=60)
        keluaran = hasil.stdout.strip()
        # Ampersand pada URL (mis. srcset Unsplash) di-escape agar HTML valid
        # — sekaligus membuat keluaran statis identik dengan serialisasi peramban.
        keluaran = re.sub(r"&(?!(?:[A-Za-z]+|#\d+|#[xX][0-9A-Fa-f]+);)", "&amp;", keluaran)
        return keluaran or cadangan
    except Exception as galat:  # noqa: BLE001 — build harus tetap jalan
        print("   ! render_statis gagal (%s/%s): %s" % (berkas_data, fungsi, galat))
        return cadangan


def bar_filter(cari=None, pilih=(), tombol=(), chips=(), aria="Filter daftar",
               lengket=True, kelas=""):
    """Bilah filter SERAGAM untuk semua halaman daftar (pola indeks berita).

    cari   : {id, label, placeholder, nilai?}          → kolom cari berikon
    pilih  : [{id, label, ikon, opsi=[(nilai, teks)], terpilih?}]
             → select "pil" berikon (mis. urutkan, jenis pekerjaan, bulan)
    tombol : [{teks, ikon, kelas, id?, type?}]          → tombol aksi kanan
    chips  : [{label, ikon, html}]                      → baris chip di bawah

    Semua ikon memakai Phosphor (ph-*). ID elemen dipertahankan apa adanya
    supaya kait JavaScript (pages.js/map.js) tidak perlu diubah.
    """
    kolom = ""
    if cari:
        nilai = f' value="{esc(cari.get("nilai"))}"' if cari.get("nilai") else ""
        kolom += (f'<div class="sp-bar-filter-cari">'
                  f'<i class="ph ph-magnifying-glass" aria-hidden="true"></i>'
                  f'<label class="visually-hidden" for="{cari["id"]}">{esc(cari["label"])}</label>'
                  f'<input class="form-control" id="{cari["id"]}" type="search" '
                  f'placeholder="{esc(cari.get("placeholder", ""))}"{nilai}></div>')
    for pl in pilih:
        opsi = "".join(
            f'<option value="{esc(v)}"{" selected" if str(v) == str(pl.get("terpilih", "")) else ""}>{esc(t)}</option>'
            for v, t in pl["opsi"]
        )
        kolom += (f'<div class="sp-bar-filter-pilih">'
                  f'<i class="ph {pl.get("ikon", "ph-list-checks")}" aria-hidden="true"></i>'
                  f'<label class="visually-hidden" for="{pl["id"]}">{esc(pl["label"])}</label>'
                  f'<select class="form-select" id="{pl["id"]}" aria-label="{esc(pl["label"])}">{opsi}</select></div>')
    if tombol:
        isi = "".join(
            f'<button class="btn {t.get("kelas", "btn-outline-navy")}" '
            f'type="{t.get("type", "button")}"'
            + (f' id="{t["id"]}"' if t.get("id") else "")
            + f'><i class="ph {t["ikon"]}" aria-hidden="true"></i>{esc(t["teks"])}</button>'
            for t in tombol
        )
        kolom += f'<div class="sp-bar-filter-aksi">{isi}</div>'

    baris_chip = ""
    for c in chips:
        id_chip = f' id="{c["id"]}"' if c.get("id") else ""
        baris_chip += (
            '<div class="chip-grup">'
            f'<span class="chip-label"><i class="ph {c["ikon"]}" aria-hidden="true"></i>{esc(c["label"])}</span>'
            f'<div class="chip-scroll"{id_chip}>{c["html"]}</div>'
            '</div>'
        )

    isi_bilah = f'<form class="sp-bar-filter" role="search" aria-label="{esc(aria)}">{kolom}</form>{baris_chip}'
    if lengket:
        return f'<div class="bar-lengket mb-4 {kelas}">{isi_bilah}</div>'
    return f'<div class="bilah-filter mb-4 {kelas}">{isi_bilah}</div>'


def judul_seksi(nomor, judul, ket="", aksi=(), id_h2=""):
    """Judul seksi bernomor (pola majalah): "01 / Destinasi" + garis pemisah."""
    aksi_html = "".join(aksi)
    ket_html = f'<p class="judul-seksi-ket">{ket}</p>' if ket else ""
    idnya = f' id="{id_h2}"' if id_h2 else ""
    return f"""
    <div class="judul-seksi">
      <span class="nomor" aria-hidden="true">{nomor}</span>
      <div>
        <h2 class="title-section"{idnya}>{judul}</h2>
        {ket_html}
      </div>
      <div class="aksi">{aksi_html}</div>
    </div>
    <hr class="garis-judul">"""


def rail(items, kelas="", nav_label="Geser daftar"):
    """Bilah geser horizontal (scroll-snap) + tombol geser.

    Tanpa JavaScript pun tetap bisa digeser dengan jari/trackpad; tombolnya
    hanya mempercepat dan dipasang assets/js/majalah.js.
    """
    return f"""
    <div class="rail {kelas}" data-rail>
      <div class="rail-track" role="region" aria-label="{esc(nav_label)}" tabindex="0">
        {items}
      </div>
      <div class="rail-nav mt-2">
        <button type="button" data-rail-mundur aria-label="Geser daftar ke kiri"><i class="ph ph-arrow-left" aria-hidden="true"></i></button>
        <button type="button" data-rail-maju aria-label="Geser daftar ke kanan"><i class="ph ph-arrow-right" aria-hidden="true"></i></button>
      </div>
    </div>"""


def build_home(base, situs):
    """Beranda tata letak "Majalah + Bento".

    Alur: masthead majalah → bento utama (1 berita besar + 2 tile destinasi +
    kartu angka) → 01 Destinasi (rail) → 02 Kuliner (bento: foto + daftar harga)
    → 03 UMKM (bento petak kecil) → 04 Berita (rail + tab kategori) →
    05 Layanan (bento bernomor) → Peta → Angka (blok navy) → Sosmed & langganan.

    Isi dinamis tetap dirender dari assets/data/*.json oleh pages.js lewat
    penanda data-*. Bagian statis (judul seksi, masthead, CTA) ada di build.
    """
    tanggal_edisi = tgl_panjang(datetime.now(WIB).date().isoformat(), jam=False)
    pita = [("Berita", "berita/index.html"), ("Wisata", "wisata/index.html"),
            ("Kuliner", "kuliner/index.html"), ("UMKM", "umkm/index.html"),
            ("Layanan", "layanan/lalu-lintas.html"), ("Peta", "peta.html"),
            ("Agenda", "layanan/agenda.html"), ("Link Bio", "link/index.html")]
    pita_html = "".join(f'<a href="{base}{u}">{esc(t)}</a>' for t, u in pita)

    # Layanan bernomor (bento 05)
    layanan = [
        ("Info Lalu Lintas", "Kondisi jalan, rekayasa, titik rawan macet.", "layanan/lalu-lintas.html", "ph-traffic-signal"),
        ("Agenda Kegiatan", "Jadwal acara warga, pasar, dan komunitas.", "layanan/agenda.html", "ph-calendar-dots"),
        ("Lowongan Kerja", "Loker sekitar Pandaan + peringatan penipuan.", "layanan/loker.html", "ph-briefcase"),
        ("Nomor Penting", "Kontak darurat & layanan publik Pandaan.", "layanan/nomor-penting.html", "ph-phone-call"),
        ("Lapor / Kirim Info", "Kirim foto, kejadian, atau usulan ke redaksi.", "layanan/lapor.html", "ph-paper-plane-tilt"),
        ("Panduan Warga", "Panduan praktis wisata sehari & UMKM.", "panduan/index.html", "ph-book-open-text"),
    ]
    layanan_html = "".join(
        f'<div class="b-4"><a class="tile kartu-layanan" href="{base}{u}">'
        f'<span class="layanan-nomor" aria-hidden="true">{n:02d}</span>'
        f'<div class="tile-isi"><span class="tile-kicker">{t}</span>'
        f'<span class="tile-teks">{esc(d)}</span>'
        f'<span class="tile-tautan">Buka layanan <i class="ph ph-arrow-right" aria-hidden="true"></i></span>'
        f'</div></a></div>'
        for n, (t, d, u, ik) in enumerate(layanan, start=1)
    )

    tabs = "".join(
        f'<button class="nav-link {"active" if i == 0 else ""}" id="tab-{k["slug"]}" data-bs-toggle="pill" '
        f'data-bs-target="#pane-{k["slug"]}" type="button" role="tab" aria-controls="pane-{k["slug"]}" '
        f'aria-selected="{"true" if i == 0 else "false"}">{esc(k["nama"])}</button>'
        for i, k in enumerate(KATEGORI[:6])
    )
    panes = "".join(
        f'<div class="tab-pane fade {"show active" if i == 0 else ""}" id="pane-{k["slug"]}" role="tabpanel" '
        f'aria-labelledby="tab-{k["slug"]}" tabindex="0">'
        f'<div class="row g-4" data-list="kategori-berita" data-kategori="{k["slug"]}" data-limit="3">'
        f'{skeleton_grid(3)}</div>'
        f'<div class="text-center mt-4"><a class="btn btn-outline-navy" '
        f'href="{base}berita/index.html?kategori={k["slug"]}">Lihat semua {esc(k["nama"])} '
        f'<i class="ph ph-arrow-right" aria-hidden="true"></i></a></div></div>'
        for i, k in enumerate(KATEGORI[:6])
    )

    body = f"""
<section class="masthead">
  <div class="container">
    <div class="masthead-baris">
      <span><i class="ph ph-map-pin me-1" aria-hidden="true"></i>Pandaan · Kabupaten Pasuruan</span>
      <span>{tanggal_edisi}</span>
      <span>Edisi digital · diperbarui berkala</span>
    </div>
    <h1 class="masthead-nama">Sudut <em>Pandaan</em></h1>
    <p class="masthead-tag">Kabar warga, destinasi lereng Penanggungan, kuliner legendaris, dan UMKM lokal — dalam satu majalah digital.</p>
    <nav class="masthead-pita" aria-label="Bagian utama">{pita_html}</nav>
  </div>
</section>

<section class="seksi pt-4 pt-lg-5" aria-labelledby="judulSorotan">
  <div class="container">
    {h2_tersembunyi_berid("Sorotan hari ini")}
    <div class="bento">
      <div class="b-8" data-bento-utama>{skeleton_grid(1, col="", body_h=420)}</div>
      <div class="b-4 d-grid gap-3" data-bento-sisi>{skeleton_grid(2, col="", body_h=200)}</div>
      <div class="b-4" data-bento-destinasi>{skeleton_grid(1, col="", body_h=230)}</div>
      <div class="b-4" data-bento-kuliner>{skeleton_grid(1, col="", body_h=230)}</div>
      <div class="b-4"><div class="tile tile-navy h-100">
        <div class="tile-isi">
          <span class="tile-kicker">Sekilas</span>
          <span class="angka-besar" data-counter="18">0</span>
          <span class="angka-label">Desa &amp; kelurahan di Kecamatan Pandaan</span>
          <span class="tile-teks mt-2">18 wilayah: 4 kelurahan dan 14 desa, dari Jogosari sampai Wedoro.</span>
          <a class="tile-tautan" href="{base}tentang.html">Selengkapnya <i class="ph ph-arrow-right" aria-hidden="true"></i></a>
        </div>
      </div></div>
    </div>
  </div>
</section>

<section class="seksi pt-0">
  <div class="container">
    {judul_seksi("01", "Destinasi Wajib Dikunjungi",
                 "Dari taman budaya tepi jalan raya sampai air terjun lereng Penanggungan — lengkap dengan jam buka, kisaran harga, dan tanggal verifikasi.",
                 [f'<a class="btn btn-outline-navy" href="{base}wisata/index.html">Semua destinasi <i class="ph ph-arrow-right ms-1" aria-hidden="true"></i></a>'],
                 id_h2="judulDestinasi")}
    <div class="rail" data-rail>
      <div class="rail-track" role="region" aria-label="Destinasi pilihan" tabindex="0" data-list="wisata-sorotan">{skeleton_grid(3, col="rail-item")}</div>
      <div class="rail-nav mt-2">
        <button type="button" data-rail-mundur aria-label="Geser daftar ke kiri"><i class="ph ph-arrow-left" aria-hidden="true"></i></button>
        <button type="button" data-rail-maju aria-label="Geser daftar ke kanan"><i class="ph ph-arrow-right" aria-hidden="true"></i></button>
      </div>
    </div>
  </div>
</section>

<section class="seksi seksi-krem2">
  <div class="container">
    {judul_seksi("02", "Kuliner Khas Pandaan",
                 "Lesehan legendaris, kripik tempe, sampai kafe kekinian. Kisaran harga wajib dicek ulang sebelum berkunjung.",
                 [f'<a class="btn btn-outline-navy" href="{base}kuliner/index.html">Semua kuliner <i class="ph ph-arrow-right ms-1" aria-hidden="true"></i></a>'],
                 id_h2="judulKuliner")}
    <div class="bento">
      <div class="b-8">
        <div class="bento" data-list="kuliner-foto" data-limit="4" style="row-gap:1rem">
          {skeleton_grid(4, col="b-6")}
        </div>
      </div>
      <div class="b-4">
        <div class="tile h-100">
          <div class="tile-isi">
            <span class="tile-kicker">Daftar harga</span>
            <span class="tile-judul h5">Rentang harga kuliner</span>
            <ul class="daftar-editorial mt-2 mb-0" data-list="kuliner-daftar" data-limit="6"></ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="seksi">
  <div class="container">
    {judul_seksi("03", "UMKM Pilihan Warga",
                 "Produk rumahan, kerajinan, dan jasa tetangga sendiri. Hubungi langsung lewat WhatsApp — tanpa perantara.",
                 [f'<a class="btn btn-outline-navy" href="{base}umkm/index.html">Direktori UMKM</a>',
                  f'<a class="btn btn-navy" href="{base}umkm/daftar.html">Daftarkan usaha</a>'],
                 id_h2="judulUmkm")}
    <div class="bento" data-list="umkm-pilihan" data-limit="4">
      {skeleton_grid(4, col="b-3")}
    </div>
  </div>
</section>

<section class="seksi seksi-kertas">
  <div class="container">
    {judul_seksi("04", "Berita Warga Pandaan",
                 "Peristiwa, lalu lintas, pembangunan, dan agenda — setiap laporan mencantumkan waktu dan sumbernya.",
                 [f'<a class="btn btn-outline-navy" href="{base}berita/index.html">Semua berita <i class="ph ph-arrow-right ms-1" aria-hidden="true"></i></a>'],
                 id_h2="judulBerita")}
    <div class="rail" data-rail>
      <div class="rail-track" role="region" aria-label="Berita terbaru" tabindex="0" data-list="berita-lead" data-limit="8">
        {skeleton_grid(4, col="rail-item")}
      </div>
      <div class="rail-nav mt-2">
        <button type="button" data-rail-mundur aria-label="Geser daftar ke kiri"><i class="ph ph-arrow-left" aria-hidden="true"></i></button>
        <button type="button" data-rail-maju aria-label="Geser daftar ke kanan"><i class="ph ph-arrow-right" aria-hidden="true"></i></button>
      </div>
    </div>
    <div class="mt-5">
      <h3 class="h5 mb-3">Telusuri per kategori</h3>
      <ul class="nav nav-pills sp-tabs mb-4" role="tablist">{tabs}</ul>
      <div class="tab-content">{panes}</div>
    </div>
  </div>
</section>

<section class="seksi">
  <div class="container">
    {judul_seksi("05", "Layanan Warga",
                 "Enam pintu masuk cepat ke layanan yang paling sering dicari warga Pandaan.",
                 [], id_h2="judulLayanan")}
    <div class="bento">{layanan_html}</div>
  </div>
</section>

<section class="seksi seksi-krem2">
  <div class="container">
    <div class="bento align-items-stretch">
      <div class="b-7" style="grid-column: span 8">
        {judul_seksi("06", "Peta Pandaan", "Destinasi, kuliner, UMKM, dan titik rawan macet dalam satu peta interaktif.",
                     [f'<a class="btn btn-outline-navy" href="{base}peta.html">Peta lengkap <i class="ph ph-arrow-right ms-1" aria-hidden="true"></i></a>'],
                     id_h2="judulPeta")}
        <div id="peta" class="sp-map" data-peta="mini" role="img" aria-label="Pratinjau peta titik penting Pandaan. Daftar titik lengkap ada di halaman Peta Pandaan.">{HINT_PETA}</div>
        <p class="small text-muted-2 mt-2 mb-0">Peta dari OpenStreetMap. Bila peta tidak tampil (mis. tanpa internet), gunakan <a href="{base}peta.html">halaman Peta Pandaan</a>.</p>
      </div>
      <div class="b-4">
        <div class="tile h-100">
          <div class="tile-isi">
            <span class="tile-kicker">Titik penting</span>
            <span class="tile-judul h5">Yang ada di peta</span>
            <ul class="daftar-editorial mt-2 mb-0">
              <li><span class="daftar-nomor">01</span><span><strong>Wisata</strong><br><span class="tile-teks">Destinasi keluarga &amp; budaya</span></span></li>
              <li><span class="daftar-nomor">02</span><span><strong>Kuliner</strong><br><span class="tile-teks">Warung, lesehan, dan kafe</span></span></li>
              <li><span class="daftar-nomor">03</span><span><strong>UMKM</strong><br><span class="tile-teks">Produsen &amp; oleh-oleh lokal</span></span></li>
              <li><span class="daftar-nomor">04</span><span><strong>Lalu lintas</strong><br><span class="tile-teks">Titik rawan macet</span></span></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="seksi seksi-navy">
  <div class="container">
    <div class="judul-seksi">
      <span class="nomor text-white" aria-hidden="true" style="color:#fff !important;border-color:rgba(255,255,255,.35)">07</span>
      <div>
        <h2 class="title-section text-white" id="judulAngka">Pandaan dalam Angka</h2>
        <p class="judul-seksi-ket" style="color:rgba(255,255,255,.8)">Angka wilayah bersumber dari data publik; angka audiens ditandai sebagai estimasi.</p>
      </div>
      <div class="aksi"><a class="btn btn-outline-white" href="{base}tentang.html">Sumber data <i class="ph ph-arrow-right ms-1" aria-hidden="true"></i></a></div>
    </div>
    <hr class="garis-judul" style="border-color:rgba(255,255,255,.25)">
    <div class="bento">
      <div class="b-3"><div class="tile tile-navy h-100" style="border-color:rgba(255,255,255,.2)"><div class="tile-isi">
        <span class="angka-besar" data-counter="18">0</span><span class="angka-label">Desa &amp; kelurahan</span></div></div></div>
      <div class="b-3"><div class="tile tile-navy h-100" style="border-color:rgba(255,255,255,.2)"><div class="tile-isi">
        <span class="angka-besar" data-counter="116">0</span><span class="angka-label">Ribu jiwa (estimasi BPS)</span></div></div></div>
      <div class="b-3"><div class="tile tile-navy h-100" style="border-color:rgba(255,255,255,.2)"><div class="tile-isi">
        <span class="angka-besar" data-counter="43">0</span><span class="angka-label">km² luas wilayah</span></div></div></div>
      <div class="b-3"><div class="tile tile-emas h-100"><div class="tile-isi">
        <span class="angka-besar" data-counter="30">0</span><span class="angka-label">Konten terverifikasi (target fase 1)</span></div></div></div>
    </div>
    <p class="small mt-4 mb-0" style="color:rgba(255,255,255,.7)"><i class="ph ph-warning-circle me-1" aria-hidden="true"></i>Kami tidak menampilkan angka pengikut sosial media atau klaim lain yang belum diverifikasi. Lihat <a class="text-white" href="{base}tentang.html">Tentang Kami</a> untuk sumber data.</p>
  </div>
</section>

<section class="seksi">
  <div class="container">
    <div class="bento">
      <div class="b-8">
        {judul_seksi("08", "Dari Sosial Media", "Kartu manual tanpa embed pihak ketiga agar situs tetap cepat dan bebas pelacak.", [], id_h2="judulSosmed")}
        <div class="rail" data-rail>
          <div class="rail-track" role="region" aria-label="Postingan sosial media" tabindex="0" data-list="sosmed" data-limit="6">
            {skeleton_grid(3, col="rail-item")}
          </div>
          <div class="rail-nav mt-2">
            <button type="button" data-rail-mundur aria-label="Geser daftar ke kiri"><i class="ph ph-arrow-left" aria-hidden="true"></i></button>
            <button type="button" data-rail-maju aria-label="Geser daftar ke kanan"><i class="ph ph-arrow-right" aria-hidden="true"></i></button>
          </div>
        </div>
        <p class="tile-teks small mt-3 mb-0">Akun resmi: <a href="https://www.instagram.com/sudutpandaan" target="_blank" rel="noopener noreferrer">@sudutpandaan</a> di Instagram dan Threads.</p>
      </div>
      <div class="b-4">
        <div class="tile tile-navy h-100">
          <div class="tile-isi">
            <span class="tile-kicker">Tetap terhubung</span>
            <span class="tile-judul h4">Jangan lewatkan info Pandaan</span>
            <span class="tile-teks">Ringkasan kabar terkini, agenda, dan info lalu lintas langsung ke email Anda.</span>
            <form class="mt-3 d-grid gap-2" id="formLangganan" novalidate>
              <label class="visually-hidden" for="emailLangganan">Alamat email</label>
              <input class="form-control" id="emailLangganan" type="email" name="email" placeholder="nama@email.com" required>
              <button class="btn btn-gold" type="submit">Berlangganan <i class="ph ph-arrow-right" aria-hidden="true"></i></button>
              <div class="invalid-feedback">Masukkan alamat email yang valid.</div>
            </form>
            <span class="tile-teks small">Fase statis: form belum tersambung ke layanan email (catatan ada di halaman Kontak).</span>
            <a class="btn btn-outline-white mt-3 align-self-start" href="https://wa.me/{situs['wa_admin']}?text=Halo%20Sudut%20Pandaan%2C%20saya%20mau%20ikut%20kanal%20info" target="_blank" rel="noopener noreferrer"><i class="ph ph-whatsapp-logo me-1" aria-hidden="true"></i>Minta info via WhatsApp</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = jsonld({
        "@context": "https://schema.org", "@type": "NewsMediaOrganization",
        "name": situs["nama"], "url": situs["base_url"] + "/",
        "logo": situs["base_url"] + "/assets/img/favicon/favicon-512.png",
        "description": situs["deskripsi"],
        "sameAs": [situs["instagram"], situs["threads"]],
        "areaServed": {"@type": "AdministrativeArea", "name": "Pandaan, Pasuruan, Jawa Timur"},
        "email": situs["email"],
    }) + jsonld({
        "@context": "https://schema.org", "@type": "WebSite",
        "name": situs["nama"], "url": situs["base_url"] + "/",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": situs["base_url"] + "/berita/index.html?q={search_term_string}"},
            "query-input": "required name=search_term_string",
        },
        "inLanguage": "id-ID",
    })

    # Beranda majalah tidak lagi memakai Swiper/korsel hero → CSS Swiper tidak
    # diunduh lagi. Yang di-preload adalah GAMBAR BERITA UTAMA (elemen LCP),
    # dengan srcset yang sama persis seperti yang diminta kartuBeritaLead().
    lead = sorted(BERITA, key=lambda x: x.get("tanggal", ""), reverse=True)[0]
    lead_src = img_varian(lead["gambar"], 800, 500, 60)
    lead_srcset = ", ".join(
        f'{img_varian(lead["gambar"], w, round(w * 0.625), 60)} {w}w' for w in (480, 800, 1000)
    )
    preload_hero = (f'<link rel="preload" as="image" fetchpriority="high" href="{lead_src}" '
                    f'imagesrcset="{lead_srcset}" imagesizes="(min-width: 992px) 60vw, 94vw">')
    return page(
        base=base, out_path="index.html", active="beranda", situs=situs,
        title="Sudut Pandaan — Kabar, Wisata & Kuliner Pandaan Pasuruan",
        description=situs["deskripsi"],
        canonical=situs["base_url"] + "/",
        body=body, ld=[ld], body_class="sp-has-bottomnav",
        extra_head=preload_hero,  # tanpa Swiper: beranda tidak lagi berkorsel
    )


def build_berita_index(base, situs):
    chips_html = ['<a class="chip active" href="?">Semua</a>'] + [
        f'<a class="chip" href="?kategori={k["slug"]}">{esc(k["nama"])}</a>' for k in KATEGORI
    ]
    info_awal = (f"{len(BERITA)} berita ditampilkan, terbaru lebih dulu. "
                 "Gunakan pencarian, filter kategori, atau urutkan sesuai kebutuhan.")
    body = f"""
{page_header("Berita Pandaan", "Kabar peristiwa, lalu lintas, pembangunan, dan kegiatan warga Pandaan. Setiap laporan mencantumkan waktu dan sumber.", [("Beranda", "index.html"), ("Berita", "")], base, nomor="04")}
<section class="section" data-page="berita-index">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        {bar_filter(
            aria="Pencarian & filter berita",
            cari={"id": "qBerita", "label": "Cari kata kunci berita",
                  "placeholder": "Cari berita: macet tol, posyandu, kripik tempe…"},
            pilih=[{"id": "urutBerita", "label": "Urutkan berita", "ikon": "ph-list-numbers",
                    "opsi": [("baru", "Terbaru"), ("populer", "Terpopuler"), ("judul", "Judul (A–Z)")]}],
            tombol=[{"teks": "Cari", "ikon": "ph-magnifying-glass", "kelas": "btn-navy", "type": "submit"},
                    {"teks": "Reset", "ikon": "ph-arrows-clockwise", "kelas": "btn-outline-navy",
                     "id": "resetFilterBerita"}],
            chips=[{"id": "filterKategori", "label": "Kategori", "ikon": "ph-list-checks",
                    "html": "".join(chips_html)}],
        )}

        <p class="small text-muted-2" id="hasilInfo" role="status">{info_awal}</p>
        {h2_tersembunyi("Daftar berita terbaru")}
        <div class="row g-4" id="daftarBerita">{skeleton_grid(6)}</div>
        <nav class="mt-4" aria-label="Navigasi halaman berita"><ul class="pagination justify-content-center" id="paginasiBerita"></ul></nav>

        <section class="mt-5 d-none" id="blokHasilLain" aria-labelledby="hasilLainJudul">
          <h2 class="sp-section-title h5 mb-3" id="hasilLainJudul">Hasil lain untuk pencarian ini</h2>
          <p class="small text-muted-2">Wisata, kuliner, dan UMKM yang cocok dengan kata kunci Anda.</p>
          <div class="row g-3" id="hasilLain"></div>
        </section>
      </div>
      {sidebar(base, situs)}
    </div>
  </div>
</section>
"""
    # JSON-LD: CollectionPage + ItemList artikel terbaru (statis, ikut build).
    urut_terbaru = sorted(BERITA, key=lambda x: x.get("diperbarui") or x["tanggal"], reverse=True)
    item_list = {
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "url": f"{situs['base_url']}/berita/{b['slug']}",
                "name": b["judul"],
            }
            for i, b in enumerate(urut_terbaru, start=1)
        ],
        "numberOfItems": len(urut_terbaru),
    }
    ld = jsonld({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Berita Pandaan Terbaru",
        "description": "Kumpulan berita terbaru seputar Pandaan, Kabupaten Pasuruan.",
        "url": situs["base_url"] + "/berita/",
        "inLanguage": "id-ID",
        "isPartOf": {"@type": "WebSite", "name": situs["nama"], "url": situs["base_url"] + "/"},
        "publisher": {"@type": "NewsMediaOrganization", "name": situs["nama"], "url": situs["base_url"] + "/"},
        "mainEntity": item_list,
    })
    return page(base=base, out_path="berita/index.html", active="berita", situs=situs,
                title="Berita Pandaan Terbaru — Sudut Pandaan",
                description="Berita terbaru Pandaan: peristiwa, lalu lintas, pembangunan, kesehatan, dan kegiatan warga. Disajikan dengan waktu, sumber, dan tanggal pembaruan.",
                canonical=situs["base_url"] + "/berita/",
                body=body, ld=[ld, breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Berita", "/berita/")])])


def build_berita_detail(b, base, situs):
    penulis = next((p for p in PENULIS if p["id"] == b.get("penulis_id")), PENULIS[0])
    # Tetangga kronologis: tautan internal statis yang membantu pembaca (dan crawler)
    # berpindah antar artikel tanpa bergantung JavaScript.
    _kronologis = sorted(BERITA, key=lambda x: x.get("tanggal", ""))
    _i = next((n for n, x in enumerate(_kronologis) if x["slug"] == b["slug"]), 0)
    _lama = _kronologis[_i - 1] if _i > 0 else None
    _baru = _kronologis[_i + 1] if _i + 1 < len(_kronologis) else None

    def _kartu_nav(item, arah):
        if not item:
            return ""
        judul_arah = "Berita sebelumnya" if arah == "lama" else "Berita berikutnya"
        ikon = "ph-arrow-left" if arah == "lama" else "ph-arrow-right"
        kelas = "nav-berita-item nav-lama" if arah == "lama" else "nav-berita-item nav-baru"
        return (f'<a class="{kelas}" href="{base}berita/{item["slug"]}.html">'
                f'<span class="nav-berita-arah"><i class="ph {ikon}" aria-hidden="true"></i> {judul_arah}</span>'
                f'<span class="nav-berita-judul">{esc(item["judul"])}</span></a>')

    nav_sebelumnya = _kartu_nav(_lama, "lama")
    nav_berikutnya = _kartu_nav(_baru, "baru")
    tags = "".join(f'<a class="tag-pill me-1 mb-1" href="{base}berita/index.html?q={esc(t)}">{esc(t)}</a>'
                   for t in b.get("tags", []))
    koreksi = ""
    if b.get("catatan_koreksi"):
        koreksi = f"""
      <div class="correction-box mb-4">
        <p class="mb-1"><span class="badge me-2">Koreksi</span><strong>Catatan koreksi redaksi</strong></p>
        <p class="mb-0 small">{esc(b['catatan_koreksi'])}</p>
      </div>"""
    pembaruan = ""
    if b.get("pembaruan"):
        items = "".join(f'<li><strong>Pembaruan {esc(p["jam"])}:</strong> {esc(p["teks"])}</li>' for p in b["pembaruan"])
        pembaruan = f"""
      <div class="update-box mb-4">
        <p class="mb-1"><i class="ph ph-arrows-clockwise me-1" aria-hidden="true"></i><strong>Pembaruan terbaru</strong></p>
        <ul class="mb-0 small ps-3">{items}</ul>
      </div>"""
    sumber = ""
    if b.get("sumber"):
        li = "".join(f"<li>{esc(s)}</li>" for s in b["sumber"])
        sumber = f"""
      <div class="info-box mt-4">
        <h2 class="h6">Sumber informasi</h2>
        <ul class="small mb-2 ps-3">{li}</ul>
        <p class="small text-muted-2 mb-0">Sumber yang ditandai &ldquo;belum terverifikasi&rdquo; akan diperbarui setelah ada keterangan resmi.</p>
      </div>"""
    diperbarui = (f' · Diperbarui {tgl_panjang(b["diperbarui"])}' if b.get("diperbarui") else "")
    kata = len(b["isi"].replace("<", " <").split())
    menit = max(2, round(kata / 200))
    isi_artikel, toc_html = daftar_isi_artikel(b["isi"].replace("{base}", base))

    # Kicker + meta dipindah ke KEPALA MAJALAH: h1 serif besar, ringkasan
    # sebagai dek, lalu badge kategori, meta penulis/waktu, dan tombol bagi.
    badge_terkini = ('<span class="badge text-bg-danger"><i class="ph ph-broadcast me-1" '
                     'aria-hidden="true"></i>Terkini</span>') if b.get("breaking") else ""
    badge_headline = ('<span class="badge-soft"><i class="ph-fill ph-star me-1 text-gold" '
                      'aria-hidden="true"></i>Headline</span>') if b.get("headline") else ""
    kicker = ('<div class="kepala-atas d-flex flex-wrap align-items-center gap-2 mb-2">'
              + badge_kat(b["kategori"], b["kategori_slug"]) + badge_terkini + badge_headline
              + '</div>')
    meta_pembaruan = (f'<span><i class="ph ph-clock-counter-clockwise me-1" aria-hidden="true"></i>'
                      f'Diperbarui {tgl_panjang(b["diperbarui"])}</span>') if b.get("diperbarui") else ""
    bawah = ('<div class="meta kepala-meta mt-3">'
             f'<span><i class="ph ph-user-circle me-1" aria-hidden="true"></i>{esc(b["penulis"])}</span>'
             f'<span><i class="ph ph-calendar-blank me-1" aria-hidden="true"></i>{tgl_panjang(b["tanggal"])}</span>'
             + meta_pembaruan +
             f'<span><i class="ph ph-hourglass-medium me-1" aria-hidden="true"></i>&plusmn;{menit} menit baca</span>'
             '</div>'
             f'<div class="mt-3">{share_bar(base, b["judul"])}</div>')

    body = f"""
<div class="progress-baca" data-progress-baca role="progressbar" aria-label="Progres baca artikel" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"></div>
{page_header(b['judul'], b['ringkasan'], [("Beranda", "index.html"), ("Berita", "berita/index.html"), (b['kategori'], f'berita/index.html?kategori={b["kategori_slug"]}'), (b['judul'][:38] + ("…" if len(b['judul']) > 38 else ""), "")], base, atas=kicker, bawah=bawah, kelas="artikel-kepala")}
<article class="section pt-4" data-page="detail-berita" data-slug="{b['slug']}">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        {koreksi}
        {pembaruan}
        <figure class="article-hero-fig mb-4">
          {img_hero(b['gambar'], b['alt'], base, w=800, h=450, q=65)}
          <figcaption>{esc(b['alt'])} — <span class="text-muted-2">{esc(b['kredit'])}</span></figcaption>
        </figure>
        <div class="artikel-body" data-artikel>{isi_artikel}</div>
        <div class="d-flex flex-wrap align-items-center gap-2 mt-4">{tags}</div>
        {sumber}
        <div class="info-box mt-4 d-flex gap-3 align-items-start">
          <div class="avatar-lingkar flex-shrink-0" aria-hidden="true">{esc((penulis['nama'] or "R")[0])}</div>
          <div>
            <p class="mb-1 fw-semibold">{esc(penulis['nama'])} <span class="badge-soft ms-1">{esc(penulis['peran'])}</span></p>
            <p class="small mb-2">{esc(penulis['bio'])}</p>
            <a class="small text-decoration-none" href="{base}redaksi.html">Lihat pedoman redaksi <i class="ph ph-arrow-right" aria-hidden="true"></i></a>
          </div>
        </div>
        <div class="mt-4">
          <h2 class="h5 mb-3">Bagikan artikel ini</h2>
          {share_bar(base, b['judul'])}
        </div>
        <div class="ad-slot my-4" style="min-height:250px"><div><div class="ad-slot-label mb-1">Iklan</div><div class="small">Slot 336×280 di akhir artikel</div></div></div>
        <nav class="nav-berita-urut mt-4" aria-label="Navigasi antar berita">
          {nav_sebelumnya}
          {nav_berikutnya}
        </nav>
        <section class="mt-5">
          <h2 class="sp-section-title mb-3">Berita Terkait</h2>
          <div class="row g-4" data-list="terkait-berita" data-kategori="{b['kategori_slug']}" data-exclude="{b['slug']}" data-limit="4">{skeleton_grid(4, col="col-12 col-md-6 col-lg-6")}</div>
        </section>
      </div>
      {sidebar(base, situs, toc=toc_html)}
    </div>
  </div>
</article>
<div class="sp-sticky-share d-lg-none">{share_bar(base, b['judul'])}</div>
"""
    ld = jsonld({
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": b["judul"], "description": b["ringkasan"],
        "image": [abs_url(b["gambar"], situs)],
        "datePublished": b["tanggal"],
        "dateModified": b.get("diperbarui") or b["tanggal"],
        "author": {"@type": "Person", "name": b["penulis"]},
        "publisher": {"@type": "Organization", "name": situs["nama"],
                      "logo": {"@type": "ImageObject", "url": situs["base_url"] + "/assets/img/favicon/favicon-512.png"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{situs['base_url']}/berita/{b['slug']}"},
        "articleSection": b["kategori"],
        "inLanguage": "id-ID",
    }) + breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Berita", "/berita/"), (b["kategori"], f"/berita/?kategori={b['kategori_slug']}"), (b["judul"], f"/berita/{b['slug']}")])
    return page(base=base, out_path=f"berita/{b['slug']}.html", active="berita", situs=situs,
                title=f"{b['judul']} — Sudut Pandaan",
                description=b["ringkasan"][:158],
                canonical=f"{situs['base_url']}/berita/{b['slug']}",
                og_type="article", og_image=b["gambar"].replace("800.webp", "800.webp"),
                body=body, ld=[ld], extra_head=preload_gambar(b["gambar"], base, q=65))


# ---------------------------------------------------------------------------
# Aset peta & lightbox (di-inject per halaman yang membutuhkannya)
# ---------------------------------------------------------------------------
def map_assets(base, cluster=True):
    css = (f'<link rel="stylesheet" href="{base}assets/vendor/leaflet/leaflet.css">')
    js = ["assets/vendor/leaflet/leaflet.js"]
    if cluster:
        css += (f'\n<link rel="stylesheet" href="{base}assets/vendor/MarkerCluster.css">'
                f'\n<link rel="stylesheet" href="{base}assets/vendor/MarkerCluster.Default.css">')
        js.append("assets/vendor/leaflet.markercluster.js")
    js.append("assets/js/map.js")
    return css, tuple(js)


def lightbox_assets(base):
    """CSS tambahan untuk lightbox (berkas .js dimuat lewat scripts())."""
    return ""


def chip(label, kind, value, active=False):
    return (f'<button class="chip{" active" if active else ""}" type="button" data-filter="{kind}" '
            f'data-value="{esc(value)}" aria-pressed="{"true" if active else "false"}">{esc(label)}</button>')


def build_direktori_index(jenis, base, situs):
    conf = {
        "wisata": {
            "judul": "Wisata Pandaan", "active": "jelajah",
            "lead": "Destinasi wisata di Pandaan dan sekitarnya: taman budaya, wisata keluarga, alam, dan edukasi. Setiap data mencantumkan tanggal verifikasi terakhir.",
            "kategori": "Kategori", "extra": "Jarak dari tol",
        },
        "kuliner": {
            "judul": "Kuliner Pandaan", "active": "jelajah",
            "lead": "Dari warung sarapan sampai lesehan malam: pilihan tempat makan di Pandaan beserta kisaran harga dan jam buka.",
            "kategori": "Jenis", "extra": "Waktu makan",
        },
        "umkm": {
            "judul": "Direktori UMKM Pandaan", "active": "umkm",
            "lead": "Etalase gratis untuk pelaku usaha Pandaan: kuliner, kerajinan, fashion, jasa, dan pertanian. Hubungi langsung melalui WhatsApp.",
            "kategori": "Kategori usaha", "extra": "Status",
        },
    }[jenis]
    items = {"wisata": WISATA, "kuliner": KULINER, "umkm": UMKM}[jenis]

    if jenis == "umkm":
        kat_vals = sorted({u["kategori"] for u in items})
        desa_vals = sorted({u["desa"] for u in items})
        chip_direktori = [
            {"label": conf["kategori"], "ikon": "ph-list-checks",
             "html": chip("Semua", "kategori", "semua", True) + "".join(chip(v, "kategori", v) for v in kat_vals)},
            {"label": "Desa/Kelurahan", "ikon": "ph-map-pin",
             "html": chip("Semua", "desa", "semua", True) + "".join(chip(v, "desa", v) for v in desa_vals)},
            {"label": "Status usaha", "ikon": "ph-seal-check",
             "html": '<div class="chip-switch"><input class="form-check-input" type="checkbox" id="hanyaTerverifikasi" data-filter="verified">'
                     '<label class="form-check-label" for="hanyaTerverifikasi">Hanya yang terverifikasi</label></div>'
                     '<div class="chip-switch"><input class="form-check-input" type="checkbox" id="hanyaPremium" data-filter="premium">'
                     '<label class="form-check-label" for="hanyaPremium">Tampilkan premium</label></div>'},
        ]
        cta = (f'<div class="alert alert-light border rounded-card mt-4 small mb-0">'
               f'<strong>Punya usaha di Pandaan?</strong> Daftarkan gratis melalui '
               f'<a href="{base}umkm/daftar.html">form pendaftaran UMKM</a>. Profil akan ditayangkan setelah moderasi.</div>')
    else:
        kat_vals = sorted({k for w in items for k in w.get("kategori_filter", [])})
        fas_vals = sorted({f for w in items for f in w.get("fasilitas", [])})[:6]
        chip_direktori = [
            {"label": conf["kategori"], "ikon": "ph-list-checks",
             "html": chip("Semua", "kategori", "semua", True) + "".join(chip(v, "kategori", v) for v in kat_vals)},
            {"label": "Fasilitas", "ikon": "ph-sparkle",
             "html": chip("Semua", "fasilitas", "semua", True) + "".join(chip(v, "fasilitas", v) for v in fas_vals)},
            {"label": "Kisaran harga", "ikon": "ph-coins",
             "html": chip("Semua", "harga", "semua", True) + chip("Gratis", "harga", "gratis")
                     + chip("≤ Rp20 ribu", "harga", "murah") + chip("Rp20–50 ribu", "harga", "sedang")},
        ]
        cta = (f'<div class="alert alert-light border rounded-card mt-4 small mb-0">'
               f'<strong>Data berubah?</strong> Harga tiket dan jam buka sering berubah. '
               f'<a href="{base}layanan/lapor.html">Laporkan ke redaksi</a> agar kami perbarui tanggal verifikasi.</div>')

    jumlah_entri = len(items)
    # Tinggi kartu asli (diukur di peramban) supaya skeleton → konten tidak
    # menggeser tata letak (CLS). Nilai berbeda per jenis direktori.
    tinggi_kartu = {"wisata": "13.4rem", "kuliner": "13.4rem", "umkm": "12.6rem"}[jenis]
    # "Pandaan" nama diri — jangan ikut dihuruf-kecilkan.
    label_ringkas = {"wisata": "wisata Pandaan", "kuliner": "kuliner Pandaan",
                     "umkm": "UMKM Pandaan"}[jenis]
    info_awal = (f"{jumlah_entri} entri ditampilkan"
                 + (" — lengkap dengan tanggal verifikasi." if jenis != "umkm"
                    else " — hubungi langsung lewat WhatsApp."))

    def _nama(it):
        return it.get("nama") or it.get("nama_usaha") or ""

    def _ringkas(it):
        if jenis == "wisata":
            return f'{it.get("kategori", "")} · {it.get("desa", "")} · {it.get("harga_label", "")}'
        if jenis == "kuliner":
            return f'{it.get("jenis_masakan", "")} · {it.get("desa", "")} · {it.get("harga_per_orang", "")}'
        return f'{it.get("kategori", "")} · {it.get("desa", "")}'

    daftar_ringkas = "".join(
        f'<div class="col-12 col-md-6"><div class="info-box h-100 py-2">'
        f'<a class="fw-semibold text-decoration-none" href="{base}{jenis}/{it["slug"]}.html">{esc(_nama(it))}</a>'
        f'<div class="small text-muted-2">{esc(_ringkas(it))}</div></div></div>'
        for it in items
    )

    body = f"""
{page_header(conf['judul'], conf['lead'], [("Beranda", "index.html"), (conf['judul'], "")], base, nomor=NOMOR_JENIS.get(jenis, ""))}
<section class="section" data-page="direktori" data-jenis="{jenis}">
  <div class="container">
    {bar_filter(
        aria="Pencarian & filter " + conf['judul'],
        cari={"id": "qDirektori", "label": "Cari nama atau kata kunci",
              "placeholder": ("mis. taman, air terjun, petik melon" if jenis == "wisata"
                              else ("mis. ayam goreng, soto, oleh-oleh" if jenis == "kuliner"
                                    else "mis. kripik, mebel, laundry"))},
        tombol=[{"teks": "Reset filter", "ikon": "ph-arrows-clockwise",
                 "kelas": "btn-outline-navy", "id": "resetFilter"}],
        chips=chip_direktori,
    )}
    <p class="small text-muted-2" id="hasilInfoDirektori" role="status">{info_awal}</p>
    {h2_tersembunyi("Daftar direktori")}
    <div class="row g-4" id="daftarDirektori">{skeleton_grid(jumlah_entri, body_h=tinggi_kartu)}</div>
    {cta}
    <section class="mt-5" aria-labelledby="daftarRingkasJudul">
      <h2 class="h5 mb-3" id="daftarRingkasJudul">Daftar ringkas {label_ringkas}</h2>
      <div class="row g-2">
        {daftar_ringkas}
      </div>
      <p class="small text-muted-2 mt-3 mb-0">
        <i class="ph ph-warning-circle me-1" aria-hidden="true"></i>
        Data pada daftar ini adalah <strong>contoh</strong> dan mencantumkan tanggal verifikasi.
        Periksa selalu keterangan terbaru di setiap halaman sebelum berkunjung.
      </p>
    </section>
    <p class="small text-muted-2 mt-4 mb-0"><i class="ph ph-shield-check me-1" aria-hidden="true"></i>Semua entri pada direktori ini adalah <strong>data contoh</strong> untuk keperluan tampilan. Ganti dengan data terverifikasi sebelum dipublikasikan.</p>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), (conf["judul"], f"/{jenis}/")])
    return page(base=base, out_path=f"{jenis}/index.html", active=conf["active"], situs=situs,
                title=f"{conf['judul']} — Direktori & Info Terverifikasi | Sudut Pandaan",
                description=conf["lead"][:158],
                canonical=f"{situs['base_url']}/{jenis}/", body=body, ld=[ld])


def build_wisata_detail(w, base, situs):
    # Galeri: setiap foto membawa alt + kredit sendiri (data boleh berupa teks
    # lama maupun objek {gambar, alt, kredit}), dan versi thumbnail-nya dikecilkan
    # ke 600×450 agar halaman detail tidak mengunduh gambar 1000 px.
    berkas_galeri = w.get("galeri") or [w["gambar"]]
    bagian_galeri, kredit_galeri = [], []

    def _galeri(u):
        if isinstance(u, dict):
            return u.get("gambar"), u.get("alt") or f"Foto {w['nama']}", u.get("kredit") or w.get("kredit", "")
        return u, w.get("alt") or f"Foto {w['nama']}", w.get("kredit", "")

    for u in berkas_galeri:
        tautan, teks_alt, kredit = _galeri(u)
        bagian_galeri.append(f"""
    <div class="col-6 col-md-4">
      <a href="{img_src(tautan, base)}" data-toggle="lightbox" data-gallery="galeri-{w['slug']}"
         data-caption="{esc(teks_alt)} — {esc(kredit)}">
        <img src="{img_src(img_varian(tautan, 480, 360, 55), base)}" class="img-fluid" alt="{esc(teks_alt)}"
             width="480" height="360" loading="lazy" decoding="async" onerror="SP.imgGagal(this)">
      </a>
    </div>""")
        if kredit and kredit not in kredit_galeri:
            kredit_galeri.append(kredit)
    galeri = "".join(bagian_galeri)
    # Nilai kredit sudah berawalan "Foto: " → hindari "Kredit foto: Foto: …".
    catatan_kredit = (" · ".join(x.replace("Foto: ", "", 1) for x in kredit_galeri)
                      if kredit_galeri else "")
    fas = "".join(f'<li><i class="ph ph-check-circle me-1 text-sp-green" aria-hidden="true"></i>{esc(f)}</li>' for f in w["fasilitas"])
    tips = "".join(f"<li>{esc(t)}</li>" for t in w["tips"])
    harga = w.get("harga_label") or (f"{rp(w['harga_min'])}–{rp(w['harga_max'])}" if w.get("harga_max") else "—")
    # Tautan internal statis ke destinasi lain: membantu pembaca, crawler, dan
    # tetap tampil walau JavaScript belum jalan.
    destinasi_lain = "".join(
        f'<div class="col-12 col-md-6">'
        f'<div class="info-box h-100">'
        f'<h3 class="h6 mb-1"><a class="text-decoration-none" href="{base}wisata/{x["slug"]}.html">{esc(x["nama"])}</a></h3>'
        f'<p class="small text-muted-2 mb-1">{esc(x["kategori"])} · {esc(x["desa"])} · {esc(x.get("jarak_tol", ""))}</p>'
        f'<p class="small mb-0">{esc(x.get("harga_label", ""))}</p>'
        f'</div></div>'
        for x in WISATA if x["slug"] != w["slug"]
    )
    body = f"""
{page_header(w['nama'], w['ringkasan'], [("Beranda", "index.html"), ("Wisata", "wisata/index.html"), (w['nama'], "")], base)}
<article class="section" data-page="detail-wisata" data-slug="{w['slug']}" data-lat="{w['lat']}" data-lng="{w['lng']}" data-nama="{esc(w['nama'])}">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        <figure class="article-hero-fig mb-4">
          {img_hero(w['gambar'], w.get('alt') or w['nama'], base, q=65)}
          <figcaption>{esc(w.get('alt') or 'Foto ilustrasi')}{f' — <span class="text-muted-2">{esc(w["kredit"])}</span>' if w.get('kredit') else ''}</figcaption>
        </figure>
        <div class="d-flex flex-wrap gap-2 mb-3">
          <span class="badge-cat cat-wisata">{esc(w['kategori'])}</span>
          <span class="badge-soft"><i class="ph ph-seal-check me-1" aria-hidden="true"></i>Diverifikasi {tgl_singkat(w['terakhir_diverifikasi'])}</span>
          {f'<span class="badge-premium"><i class="ph-fill ph-star me-1" aria-hidden="true"></i>Pilihan redaksi</span>' if w.get('is_featured') else ''}
          <span class="badge-soft">{esc(w.get("jarak_tol", ""))}</span>
        </div>
        <h2 class="h2 mb-2">{esc(w['nama'])}</h2>
        <div class="article-body">{w['deskripsi']}</div>

        <div class="alert alert-warning small" role="alert">
          <strong>Catatan verifikasi:</strong> {esc(w.get('status_verifikasi', '—'))}. Harga &amp; jam buka dapat berubah kapan saja.
          <a href="{base}layanan/lapor.html" class="alert-link">Laporkan jika ada data keliru</a>.
        </div>

        <div class="row g-4">
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-3"><i class="ph ph-ticket me-1 text-gold" aria-hidden="true"></i>Harga Tiket</h2>
              <p class="mb-1 fw-semibold text-sp-green">{esc(harga)}</p>
              <p class="small text-muted-2 mb-0">Konfirmasi ke pengelola sebelum berangkat.</p>
            </div>
          </div>
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-3"><i class="ph ph-clock me-1 text-gold" aria-hidden="true"></i>Jam Buka</h2>
              <div class="small">{jam_html(w.get('jam_buka'))}</div>
            </div>
          </div>
        </div>

        <div class="row g-4 mt-0">
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-2"><i class="ph ph-map-pin me-1 text-gold" aria-hidden="true"></i>Lokasi</h2>
              <p class="small mb-1">{esc(w['alamat'])}</p>
              <p class="small text-muted-2 mb-2">Desa/Kelurahan: {esc(w['desa'])} · Kode pos 67156</p>
              <div class="d-flex flex-wrap gap-2">
                <a class="btn btn-sm btn-outline-primary" target="_blank" rel="noopener noreferrer"
                   href="https://www.google.com/maps/dir/?api=1&destination={w['lat']},{w['lng']}">
                   <i class="ph ph-signpost me-1" aria-hidden="true"></i>Rute ke lokasi</a>
                <a class="btn btn-sm btn-outline-primary" href="{base}peta.html">
                   <i class="ph ph-map-trifold me-1" aria-hidden="true"></i>Buka di peta besar</a>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-2"><i class="ph ph-list-checks me-1 text-gold" aria-hidden="true"></i>Fasilitas</h2>
              <ul class="list-unstyled small mb-0 columns-2">{fas}</ul>
            </div>
          </div>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Tips Berkunjung</h2>
        <ul class="article-body ps-3">{tips}</ul>

        <h2 class="sp-section-title mt-5 mb-3">Galeri</h2>
        <div class="row g-2 sp-gallery">{galeri}</div>
        <p class="small text-muted-2 mt-2 mb-0">Klik foto untuk memperbesar (lightbox). Gunakan tombol panah &amp; Esc pada keyboard.</p>
        {f'<p class="small text-muted-2 mb-0">Kredit foto: {esc(catatan_kredit)}</p>' if catatan_kredit else ''}

        <h2 class="sp-section-title mt-5 mb-3">Peta Lokasi</h2>
        {div_peta(w['lat'], w['lng'], w['nama'], f"Peta lokasi {w['nama']}")}
        <p class="small text-muted-2 mt-2 mb-0">Koordinat: {w['lat']}, {w['lng']} — data OpenStreetMap. Koordinat bersifat perkiraan; verifikasi di lapangan.</p>

        <div class="mt-5">
          <h2 class="sp-section-title mb-3">Destinasi Lain di Pandaan</h2>
          <div class="row g-3">
            {destinasi_lain}
          </div>
        </div>

        <div class="mt-5">
          <h2 class="sp-section-title mb-3">Kuliner &amp; UMKM di Sekitar</h2>
          <div class="row g-3" data-list="sekitar" data-desa="{esc(w['desa'])}" data-limit="3">
            <div class="col-12"><span class="text-muted-2 small">Memuat…</span></div>
          </div>
        </div>

        <div class="mt-5">
          <h2 class="h5 mb-3">Bagikan</h2>
          {share_bar(base, w['nama'])}
        </div>
      </div>
      {sidebar(base, situs)}
    </div>
  </div>
</article>
"""
    gambar_ld = [abs_url(w["gambar"], situs)] + [
        abs_url(x["gambar"] if isinstance(x, dict) else x, situs) for x in (w.get("galeri") or [])
    ]
    ld_data = {
        "@context": "https://schema.org", "@type": "TouristAttraction",
        "name": w["nama"], "description": w["ringkasan"],
        "image": gambar_ld,
        "address": {"@type": "PostalAddress", "streetAddress": w["alamat"], "addressLocality": "Pandaan",
                    "addressRegion": "Jawa Timur", "postalCode": "67156", "addressCountry": "ID"},
        "geo": {"@type": "GeoCoordinates", "latitude": w["lat"], "longitude": w["lng"]},
        "isAccessibleForFree": bool(w.get("harga_min") == 0),
        "publicAccess": True,
        "touristType": w["kategori"],
        "url": f"{situs['base_url']}/wisata/{w['slug']}",
        "provider": {"@type": "NewsMediaOrganization", "name": situs["nama"], "url": situs["base_url"] + "/"},
    }
    jam_buka_ld = jam_ld(w.get("jam_buka"))
    if jam_buka_ld:
        ld_data["openingHoursSpecification"] = jam_buka_ld
    if harga_ld(w):
        ld_data["priceRange"] = harga_ld(w)
    ld = jsonld(ld_data) + breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Wisata", "/wisata/"), (w["nama"], f"/wisata/{w['slug']}")])
    # Halaman detail: Leaflet TIDAK di jalur kritis. Peta berada jauh di bawah
    # (mode "tunggal"); map.js dimuat oleh main.js (initPetaTertunda) saat peta
    # mendekati viewport, sehingga CSS+JS Leaflet (±46 KB) tidak menunda LCP.
    css, js = "", ()
    js = tuple(list(js) + ["assets/vendor/bs5-lightbox.bundle.min.js"])
    return page(base=base, out_path=f"wisata/{w['slug']}.html", active="jelajah", situs=situs,
                title=f"{w['nama']} — Wisata Pandaan | Sudut Pandaan",
                description=w["ringkasan"][:158], canonical=f"{situs['base_url']}/wisata/{w['slug']}",
                og_image=w["gambar"], extra_css=css, extra_scripts=js, body=body, ld=[ld],
                extra_head=preload_gambar(w["gambar"], base, q=65))


def build_kuliner_detail(k, base, situs):
    menu = "".join(f"<li>{esc(m)}</li>" for m in k["menu_andalan"])
    body = f"""
{page_header(k['nama'], k['ringkasan'], [("Beranda", "index.html"), ("Kuliner", "kuliner/index.html"), (k['nama'], "")], base)}
<article class="section" data-page="detail-kuliner" data-slug="{k['slug']}" data-lat="{k['lat']}" data-lng="{k['lng']}" data-nama="{esc(k['nama'])}">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        <figure class="article-hero-fig mb-4">
          {img_hero(k['gambar'], k.get('alt') or k['nama'], base, q=65)}
          <figcaption>{esc(k.get('alt') or 'Foto ilustrasi')}{f' — <span class="text-muted-2">{esc(k["kredit"])}</span>' if k.get('kredit') else ''}</figcaption>
        </figure>
        <div class="d-flex flex-wrap gap-2 mb-3">
          <span class="badge-cat cat-kuliner">{esc(k['jenis_masakan'])}</span>
          {'<span class="badge-premium">Legendaris</span>' if k.get('is_legendaris') else ''}
          {f'<span class="badge-soft">Berdiri {esc(k["tahun_berdiri"])}</span>' if k.get('tahun_berdiri') else ''}
          <span class="badge-soft"><i class="ph ph-seal-check me-1" aria-hidden="true"></i>Diverifikasi {tgl_singkat(k['terakhir_diverifikasi'])}</span>
        </div>
        <h2 class="h2 mb-2">{esc(k['nama'])}</h2>
        <div class="article-body">{k['deskripsi']}</div>

        <div class="alert alert-warning small" role="alert">
          <strong>Catatan verifikasi:</strong> {esc(k.get('status_verifikasi', '—'))}. Jam buka &amp; harga dapat berubah.
          <a href="{base}layanan/lapor.html" class="alert-link">Laporkan data keliru</a>.
        </div>

        <div class="row g-4">
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-2"><i class="ph ph-coins me-1 text-gold" aria-hidden="true"></i>Kisaran Harga / Orang</h2>
              <p class="fw-semibold text-sp-green mb-0">{esc(k['harga_per_orang'])}</p>
            </div>
          </div>
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-2"><i class="ph ph-clock me-1 text-gold" aria-hidden="true"></i>Jam Buka</h2>
              <p class="mb-0 small">{esc(k['jam_buka_str'])}</p>
            </div>
          </div>
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-2"><i class="ph ph-credit-card me-1 text-gold" aria-hidden="true"></i>Pembayaran &amp; Parkir</h2>
              <p class="small mb-1">Metode bayar: {esc(k['metode_bayar'])}</p>
              <p class="small mb-0">Parkir bus/minibus: {esc(k['parkir_bus'])}</p>
            </div>
          </div>
          <div class="col-md-6">
            <div class="info-box h-100">
              <h2 class="h6 mb-2"><i class="ph ph-seal-check me-1 text-gold" aria-hidden="true"></i>Info Halal</h2>
              <p class="small mb-0">{esc(k['halal_info'])}</p>
            </div>
          </div>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Menu Andalan</h2>
        <ul class="article-body ps-3">{menu}</ul>

        <h2 class="sp-section-title mt-5 mb-3">Lokasi</h2>
        <p class="small mb-1">{esc(k['alamat'])} · Desa/Kelurahan {esc(k['desa'])} · Kode pos 67156</p>
        {div_peta(k['lat'], k['lng'], k['nama'], f"Peta lokasi {k['nama']}")}
        <div class="d-flex flex-wrap gap-2 mt-3">
          <a class="btn btn-sm btn-outline-primary" target="_blank" rel="noopener noreferrer"
             href="https://www.google.com/maps/dir/?api=1&destination={k['lat']},{k['lng']}">
             <i class="ph ph-signpost me-1" aria-hidden="true"></i>Rute ke lokasi</a>
          <a class="btn btn-sm btn-outline-primary" href="{base}kuliner/index.html"><i class="ph ph-arrow-left me-1" aria-hidden="true"></i>Kembali ke daftar kuliner</a>
        </div>

        <div class="mt-5">
          <h2 class="h5 mb-3">Bagikan</h2>
          {share_bar(base, k['nama'])}
        </div>
        <div class="ad-slot my-4" style="min-height:250px"><div><div class="ad-slot-label mb-1">Iklan</div><div class="small">Slot 336×280</div></div></div>
      </div>
      {sidebar(base, situs)}
    </div>
  </div>
</article>
"""
    ld = jsonld({
        "@context": "https://schema.org", "@type": "Restaurant",
        "name": k["nama"], "description": k["ringkasan"],
        "image": [abs_url(k["gambar"], situs)],
        "servesCuisine": k["jenis_masakan"], "priceRange": k["harga_per_orang"],
        "address": {"@type": "PostalAddress", "addressLocality": "Pandaan", "addressRegion": "Jawa Timur",
                    "postalCode": "67156", "addressCountry": "ID"},
        "geo": {"@type": "GeoCoordinates", "latitude": k["lat"], "longitude": k["lng"]},
    }) + breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Kuliner", "/kuliner/"), (k["nama"], f"/kuliner/{k['slug']}")])
    # Halaman detail: Leaflet TIDAK di jalur kritis. Peta berada jauh di bawah
    # (mode "tunggal"); map.js dimuat oleh main.js (initPetaTertunda) saat peta
    # mendekati viewport, sehingga CSS+JS Leaflet (±46 KB) tidak menunda LCP.
    css, js = "", ()
    return page(base=base, out_path=f"kuliner/{k['slug']}.html", active="jelajah", situs=situs,
                title=f"{k['nama']} — Kuliner Pandaan | Sudut Pandaan",
                description=k["ringkasan"][:158], canonical=f"{situs['base_url']}/kuliner/{k['slug']}",
                og_image=k["gambar"], extra_css=css, extra_scripts=js, body=body, ld=[ld],
                extra_head=preload_gambar(k["gambar"], base, q=65))


def build_umkm_detail(u, base, situs):
    wa_text = f"Halo, saya menemukan profil {u['nama_usaha']} di Sudut Pandaan. Saya ingin bertanya."
    produk = "".join(
        f"""<div class="d-flex justify-content-between border-bottom py-2">
              <span>{esc(p['nama'])}</span><span class="fw-semibold text-sp-green">{esc(p['harga'])}</span></div>"""
        for p in u["produk"])
    terkait = [b for b in BERITA if u["slug"].split("-")[0] in b["slug"] or "kripik" in b["slug"]] if u["kategori"] == "Kuliner" else []
    body = f"""
{page_header(u['nama_usaha'], u['ringkasan'], [("Beranda", "index.html"), ("UMKM", "umkm/index.html"), (u['nama_usaha'], "")], base)}
<article class="section" data-page="detail-umkm" data-slug="{u['slug']}" data-lat="{u['lat']}" data-lng="{u['lng']}" data-nama="{esc(u['nama_usaha'])}">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        <div class="row g-4 align-items-start">
          <div class="col-md-5">
            <img src="{img_src(u['gambar'], base)}" class="img-fluid rounded-card shadow-sm" alt="{esc(u['nama_usaha'])}" width="400" height="400" loading="eager" fetchpriority="high" decoding="async" onerror="SP.imgGagal(this)">
            {f'<p class="small text-muted-2 mt-2 mb-0">{esc(u["kredit"])}</p>' if u.get('kredit') else ''}
          </div>
          <div class="col-md-7">
            <div class="d-flex flex-wrap gap-2 mb-2">
              <span class="badge-cat cat-umkm">{esc(u['kategori'])}</span>
              {'<span class="badge-verify"><i class="ph-fill ph-seal-check me-1" aria-hidden="true"></i>Terverifikasi</span>' if u.get('is_verified') else '<span class="badge-soft">Belum diverifikasi</span>'}
              {'<span class="badge-premium"><i class="ph-fill ph-star me-1" aria-hidden="true"></i>Premium</span>' if u.get('paket') == 'premium' else ''}
            </div>
            <h2 class="h3 mb-1">{esc(u['nama_usaha'])}</h2>
            <p class="small text-muted-2 mb-2">Pemilik: {esc(u['pemilik'])} · Desa/Kelurahan {esc(u['desa'])}</p>
            <p class="mb-3">{esc(u['ringkasan'])}</p>
            <div class="d-grid gap-2">
              <a class="btn btn-wa" target="_blank" rel="noopener noreferrer" href="https://wa.me/{u['whatsapp']}?text={esc(wa_text)}">
                <i class="ph ph-whatsapp-logo me-1" aria-hidden="true"></i>Hubungi via WhatsApp</a>
              {f'<a class="btn btn-outline-primary" target="_blank" rel="noopener noreferrer" href="{u["instagram"]}"><i class="ph ph-instagram-logo me-1" aria-hidden="true"></i>Instagram</a>' if u.get('instagram') and u['instagram'] != '-' else ''}
              <a class="btn btn-outline-primary" target="_blank" rel="noopener noreferrer"
                 href="https://www.google.com/maps/dir/?api=1&destination={u['lat']},{u['lng']}">
                 <i class="ph ph-signpost me-1" aria-hidden="true"></i>Rute ke lokasi</a>
            </div>
            <p class="small text-muted-2 mt-2 mb-0">Jam operasional: {esc(u['jam_buka'])}</p>
          </div>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Cerita Usaha</h2>
        <div class="article-body">{u['cerita']}</div>

        <h2 class="sp-section-title mt-5 mb-3">Produk &amp; Kisaran Harga</h2>
        <div class="info-box">{produk}
          <p class="small text-muted-2 mt-3 mb-0">Harga adalah contoh &amp; dapat berubah. Konfirmasi langsung ke pemilik usaha.</p>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Lokasi</h2>
        <p class="small mb-1">{esc(u['alamat'])} · Kode pos 67156</p>
        {div_peta(u['lat'], u['lng'], u['nama_usaha'], f"Peta lokasi {u['nama_usaha']}")}

        <div class="mt-5">
          <h2 class="h5 mb-3">Bagikan profil usaha ini</h2>
          {share_bar(base, u['nama_usaha'])}
        </div>

        <div class="info-box mt-4">
          <h2 class="h6 mb-2"><i class="ph ph-megaphone me-1 text-gold" aria-hidden="true"></i>Tingkatkan profil usaha</h2>
          <p class="small mb-2">Paket Premium menampilkan badge Premium, urutan atas pada direktori, dan slot di beranda.</p>
          <a class="btn btn-sm btn-gold" href="{base}pasang-iklan.html">Lihat paket &amp; harga</a>
        </div>
      </div>
      {sidebar(base, situs)}
    </div>
  </div>
</article>
"""
    ld = jsonld({
        "@context": "https://schema.org", "@type": "LocalBusiness",
        "name": u["nama_usaha"], "description": u["ringkasan"],
        "image": [abs_url(u["gambar"], situs)],
        "telephone": "+" + u["whatsapp"], "priceRange": u["produk"][0]["harga"] if u.get("produk") else "",
        "address": {"@type": "PostalAddress", "addressLocality": "Pandaan", "addressRegion": "Jawa Timur",
                    "postalCode": "67156", "addressCountry": "ID"},
        "geo": {"@type": "GeoCoordinates", "latitude": u["lat"], "longitude": u["lng"]},
        "areaServed": "Pandaan, Kabupaten Pasuruan",
    }) + breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("UMKM", "/umkm/"), (u["nama_usaha"], f"/umkm/{u['slug']}")])
    # Halaman detail: Leaflet TIDAK di jalur kritis. Peta berada jauh di bawah
    # (mode "tunggal"); map.js dimuat oleh main.js (initPetaTertunda) saat peta
    # mendekati viewport, sehingga CSS+JS Leaflet (±46 KB) tidak menunda LCP.
    css, js = "", ()
    return page(base=base, out_path=f"umkm/{u['slug']}.html", active="umkm", situs=situs,
                title=f"{u['nama_usaha']} — UMKM Pandaan | Sudut Pandaan",
                description=u["ringkasan"][:158], canonical=f"{situs['base_url']}/umkm/{u['slug']}",
                og_image=u["gambar"], extra_css=css, extra_scripts=js, body=body, ld=[ld],
                extra_head=preload_gambar(u["gambar"], base, q=65))


def build_panduan_index(base, situs):
    cards = "".join(f"""
      <div class="col-12 col-md-6 col-lg-4">
        <article class="card-place">
          <div class="card-img-wrap">
            <img src="{img_src(p['gambar'], base)}" alt="{esc(p['judul'])}" loading="lazy" decoding="async" width="800" height="500" onerror="SP.imgGagal(this)">
            <span class="card-badge-float badge-cat cat-{'wisata' if p['jenis'] == 'wisata' else ('kuliner' if p['jenis'] == 'kuliner' else 'lalu-lintas')}">{esc(p['jenis'].title())}</span>
          </div>
          <div class="card-body">
            <h2 class="card-title h6 mb-2"><a class="text-decoration-none stretched-link" href="{base}panduan/{p['slug']}.html">{esc(p['judul'])}</a></h2>
            <p class="small text-muted-2 clamp-2 mb-2">{esc(p['ringkasan'])}</p>
            <div class="meta"><span><i class="ph ph-calendar-blank me-1" aria-hidden="true"></i>{tgl_singkat(p['tanggal'])}</span></div>
          </div>
        </article>
      </div>""" for p in PANDUAN)
    body = f"""
{page_header("Panduan Pandaan", "Artikel panjang (evergreen) yang diperbarui berkala: panduan wisata, peta kuliner, dan titik rawan macet.", [("Beranda", "index.html"), ("Panduan", "")], base, nomor="05")}
<section class="section">
  <div class="container">
    <div class="row g-4">{cards}</div>
    <div class="alert alert-light border rounded-card mt-4 small mb-0">
      Halaman pilar seperti ini sengaja dibuat untuk SEO jangka panjang. Perbarui isinya minimal 3 bulan sekali
      dan cantumkan tanggal pembaruan agar tetap dipercaya pembaca maupun mesin pencari.
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Panduan", "/panduan/")])
    return page(base=base, out_path="panduan/index.html", active="jelajah", situs=situs,
                title="Panduan Wisata, Kuliner & Lalu Lintas Pandaan — Sudut Pandaan",
                description="Panduan lengkap berkunjung ke Pandaan: itinerary satu hari, peta kuliner, titik rawan macet, dan tips untuk pelintas Surabaya–Malang.",
                canonical=situs["base_url"] + "/panduan/", body=body, ld=[ld])


def build_panduan_detail(p, base, situs):
    tags = "".join(f'<a class="tag-pill me-1 mb-1" href="{base}berita/index.html?q={esc(t)}">{esc(t)}</a>' for t in p["tags"])
    body = f"""
{page_header(p['judul'], p['ringkasan'], [("Beranda", "index.html"), ("Panduan", "panduan/index.html"), (p['judul'][:36] + "…", "")], base)}
<article class="section" data-page="detail-panduan" data-slug="{p['slug']}">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        <figure class="article-hero-fig mb-4">
          {img_hero(p['gambar'], p['judul'], base, q=65)}
          <figcaption>Foto ilustrasi. Terakhir diperbarui {tgl_singkat(p['tanggal'])}.</figcaption>
        </figure>
        <div class="meta mb-3">
          <span><i class="ph ph-user-circle me-1" aria-hidden="true"></i>{esc(p['penulis'])}</span>
          <span><i class="ph ph-calendar-blank me-1" aria-hidden="true"></i>{tgl_panjang(p['tanggal'], jam=False)}</span>
          <span><i class="ph ph-arrows-clockwise me-1" aria-hidden="true"></i>Halaman pilar — diperbarui berkala</span>
        </div>
        <div class="article-body">{p['isi']}</div>
        <div class="d-flex flex-wrap align-items-center gap-2 mt-4">{tags}</div>
        <div class="mt-4"><h2 class="h5 mb-3">Bagikan panduan ini</h2>{share_bar(base, p['judul'])}</div>
        <section class="mt-5">
          <h2 class="sp-section-title mb-3">Panduan Lainnya</h2>
          <div class="row g-4" data-list="panduan-lain" data-exclude="{p['slug']}" data-limit="3">{skeleton_grid(3)}</div>
        </section>
      </div>
      {sidebar(base, situs)}
    </div>
  </div>
</article>
"""
    ld = jsonld({
        "@context": "https://schema.org", "@type": "Article",
        "headline": p["judul"], "description": p["ringkasan"],
        "image": [abs_url(p["gambar"], situs)],
        "datePublished": p["tanggal"], "dateModified": p["tanggal"],
        "author": {"@type": "Person", "name": p["penulis"]},
        "publisher": {"@type": "Organization", "name": situs["nama"],
                      "logo": {"@type": "ImageObject", "url": situs["base_url"] + "/assets/img/favicon/favicon-512.png"}},
    }) + breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Panduan", "/panduan/"), (p["judul"], f"/panduan/{p['slug']}")])
    return page(base=base, out_path=f"panduan/{p['slug']}.html", active="jelajah", situs=situs,
                title=f"{p['judul']} — Sudut Pandaan", description=p["ringkasan"][:158],
                canonical=f"{situs['base_url']}/panduan/{p['slug']}", og_type="article",
                og_image=p["gambar"], body=body, ld=[ld],
                extra_head=preload_gambar(p["gambar"], base, q=65))


# ---------------------------------------------------------------------------
# LAYANAN WARGA
# ---------------------------------------------------------------------------
def build_lalu_lintas(base, situs):
    kondisi_legend = """
    <div class="d-flex flex-wrap gap-3 small">
      <span><span class="badge-cat cat-peristiwa me-1">Padat merayap</span> kecepatan rendah / berhenti berkala</span>
      <span><span class="badge-cat cat-lalu-lintas me-1">Padat</span> antrean panjang, masih bergerak</span>
      <span><span class="badge-cat cat-kesehatan me-1">Lancar</span> arus normal</span>
      <span><span class="badge-cat cat-pembangunan me-1">Belum terverifikasi</span> laporan warga</span>
    </div>"""
    body = f"""
{page_header("Info Lalu Lintas Pandaan", "Laporan kondisi arus di ruas tol Pandaan, jalur Tretes, bypass, dan jalan utama kota. Diperbarui berkala oleh redaksi.", [("Beranda", "index.html"), ("Layanan", "layanan/lalu-lintas.html"), ("Info Lalu Lintas", "")], base, nomor="05")}
<section class="section" data-page="lalu-lintas">
  <div class="container">
    <div class="alert alert-warning small" role="alert">
      <strong>Batas layanan:</strong> halaman ini dikelola redaksi dan <em>bukan</em> kanal resmi pengelola jalan.
      Untuk keadaan darurat atau keputusan perjalanan penting, gunakan kanal resmi (call center tol, kepolisian, atau akun resmi instansi).
    </div>
    <div class="card border-0 shadow-sm rounded-card p-3 p-md-4 mb-4">{kondisi_legend}</div>
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
          <h2 class="sp-section-title">Laporan Terbaru</h2>
          <span class="small text-muted-2" id="updateTerakhir"></span>
        </div>
        <div class="list-group list-group-flush" id="daftarLalin">{render_statis(
          "assets/data/lalu-lintas.json", "itemLalin", base, urut="waktu", arah="turun",
          cadangan='<div class="list-group-item px-0"><div class="sp-skeleton sk-line" style="width:80%"></div><div class="sp-skeleton sk-line" style="width:60%"></div></div>')}</div>
        <h2 class="sp-section-title mt-5 mb-3">Format Laporan Redaksi</h2>
        <p class="small text-muted-2">Redaksi memakai format baku berikut agar laporan mudah diverifikasi dan konsisten.</p>
        <pre class="bg-white border rounded-card p-3 small mb-0"><code>{esc(LALIN_TEMPLATE)}</code></pre>
      </div>
      <div class="col-lg-4">
        <div class="sidebar-widget">
          <h3><i class="ph ph-paper-plane-tilt me-1 text-gold" aria-hidden="true"></i>Punya Info Lalu Lintas?</h3>
          <p class="small">Kirim laporan kondisi jalan: sebutkan waktu, lokasi persis, kondisi, dan penyebab (jika tahu).</p>
          <a class="btn btn-gold w-100" href="{base}layanan/lapor.html">Kirim Laporan</a>
        </div>
        {ad_slot("Iklan", "", "250px").replace("{base}", base)}
        <div class="sidebar-widget">
          <h3><i class="ph ph-info me-1 text-gold" aria-hidden="true"></i>Catatan Verifikasi</h3>
          <p class="small mb-0">Laporan warga ditandai <em>belum terverifikasi</em> sampai ada konfirmasi dari sumber resmi atau dua sumber independen.</p>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Layanan", "/layanan/lalu-lintas")])
    return page(base=base, out_path="layanan/lalu-lintas.html", active="layanan", situs=situs,
                title="Info Lalu Lintas Pandaan Hari Ini — Sudut Pandaan",
                description="Kondisi lalu lintas Pandaan terkini: ruas tol Pandaan, jalur Tretes, bypass, dan jalan utama. Laporan berkala redaksi dengan status verifikasi.",
                canonical=situs["base_url"] + "/layanan/lalu-lintas", body=body, ld=[ld])


NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]


def opsi_bulan_agenda_options():
    """Daftar (nilai, teks) bulan agenda untuk bar_filter()."""
    opts = [("semua", "Semua bulan")]
    bulan = {}
    for a in sorted(load("agenda.json"), key=lambda x: x.get("mulai", "")):
        t = (a.get("mulai") or "")[:7]
        if not t:
            continue
        th, bl = int(t[:4]), int(t[5:7])
        bulan[t] = f"{NAMA_BULAN[bl - 1]} {th}"
    opts += list(bulan.items())
    return opts


def opsi_bulan_agenda():
    """Opsi <select> filter bulan agenda — dirender statis.

    Sebelumnya daftar bulan diisi JavaScript setelah paint; <select> yang masih
    kosong jauh lebih sempit sehingga toolbar berubah tinggi (membungkus) dan
    mendorong seluruh daftar agenda turun (CLS 0,095). Format kunci sama dengan
    yang dipakai pages.js: "<tahun>-<bulan tanpa nol di depan>".
    """
    data = load("agenda.json")
    items = data["agenda"] if isinstance(data, dict) else data
    hasil, sudah = ['<option value="semua">Semua bulan</option>'], set()
    for a in sorted(items, key=lambda x: str(x.get("mulai", ""))):
        tanggal = str(a.get("mulai", ""))[:10]
        if len(tanggal) < 10:
            continue
        tahun, bulan = int(tanggal[:4]), int(tanggal[5:7])
        kunci = f"{tahun}-{bulan}"
        if kunci in sudah:
            continue
        sudah.add(kunci)
        hasil.append(f'<option value="{kunci}">{NAMA_BULAN[bulan - 1]} {tahun}</option>')
    return "".join(hasil)


def build_agenda(base, situs):
    body = f"""
{page_header("Agenda Kegiatan Pandaan", "Kalender kegiatan warga: senam bersama, bazar UMKM, layanan posyandu, hingga festival budaya. Jadwal terbaru diurutkan dari yang paling dekat.", [("Beranda", "index.html"), ("Layanan", "layanan/agenda.html"), ("Agenda", "")], base, nomor="05")}
<section class="section" data-page="agenda">
  <div class="container">
    {bar_filter(
        aria="Filter agenda kegiatan",
        pilih=[{"id": "filterBulanAgenda", "label": "Filter bulan", "ikon": "ph-calendar-dots",
                "opsi": opsi_bulan_agenda_options()}],
        tombol=[{"teks": "Ekspor .ics", "ikon": "ph-calendar-plus", "kelas": "btn-navy", "id": "eksporIcs"},
                {"teks": "Reset", "ikon": "ph-arrows-clockwise", "kelas": "btn-outline-navy", "id": "resetBulanAgenda"}],
    )}
    <p class="small text-muted-2" id="hasilInfoAgenda" role="status">Memuat agenda…</p>
    {h2_tersembunyi("Daftar agenda kegiatan")}
    <div class="bento mb-4">
      <div class="b-8"><div class="row g-4" id="daftarAgenda">{render_statis(
            "assets/data/agenda.json", "kartuAgenda", base, urut="mulai", arah="naik",
            cadangan=skeleton_grid(4, body_h="18.1rem"))}</div></div>
      <div class="b-4">
        <div class="tile h-100"><div class="tile-isi">
          <span class="tile-kicker">Linimasa</span>
          <span class="tile-judul h5">Urutan terdekat</span>
          <ol class="linimasa mt-3 mb-0" id="linimasaAgenda">
            <li class="text-muted-2 small">Memuat linimasa…</li>
          </ol>
        </div></div>
      </div>
    </div>
    <div class="alert alert-light border rounded-card mt-4 small mb-0">
      <strong>Status agenda:</strong> entri bertanda <em>“Belum final”</em> menunggu pengumuman resmi penyelenggara.
      Redaksi tidak menampilkan agenda yang belum dapat dikonfirmasi sebagai agenda pasti.
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Layanan", "/layanan/agenda")])
    return page(base=base, out_path="layanan/agenda.html", active="layanan", situs=situs,
                title="Agenda Kegiatan Pandaan — Sudut Pandaan",
                description="Jadwal kegiatan dan agenda warga Pandaan: senam bersama, bazar UMKM, posyandu, festival budaya. Dilengkapi ekspor kalender .ics.",
                canonical=situs["base_url"] + "/layanan/agenda", body=body, ld=[ld])


def build_loker(base, situs):
    loker = load("loker.json")
    body = f"""
{page_header("Lowongan Kerja Pandaan", "Informasi lowongan kerja di Pandaan dan sekitarnya: pabrik, retail, kuliner, jasa, dan pendidikan.", [("Beranda", "index.html"), ("Layanan", "layanan/loker.html"), ("Lowongan Kerja", "")], base, nomor="05")}
<section class="section" data-page="loker">
  <div class="container">
    <div class="alert alert-danger small" role="alert">
      <strong><i class="ph ph-warning me-1" aria-hidden="true"></i>Waspada penipuan lowongan kerja.</strong>
      Sudut Pandaan <strong>tidak pernah memungut biaya</strong> apa pun dari pencari kerja. Jangan transfer uang untuk pendaftaran, pelatihan, seragam, atau jaminan diterima. Jangan kirim KTP/selfie dengan KTP ke pihak tak dikenal.
    </div>
    {bar_filter(
        aria="Pencarian & filter lowongan kerja",
        cari={"id": "cariLoker", "label": "Cari lowongan",
              "placeholder": "Cari posisi atau perusahaan: operator, admin, barista…"},
        pilih=[{"id": "filterJenisLoker", "label": "Jenis pekerjaan", "ikon": "ph-briefcase",
                "opsi": [("semua", "Semua jenis"), ("Penuh waktu", "Penuh waktu"),
                         ("Kontrak", "Kontrak"), ("Paruh waktu", "Paruh waktu")]}],
        tombol=[{"teks": "Reset", "ikon": "ph-arrows-clockwise", "kelas": "btn-outline-navy",
                 "id": "resetLoker"}],
    )}
    <p class="small text-muted-2" id="hasilInfoLoker" role="status">Memuat lowongan…</p>
    {h2_tersembunyi("Daftar lowongan kerja")}
    <div class="row g-4" id="daftarLoker">{skeleton_grid(4, col="col-12 col-lg-6")}</div>
    <div class="card border-0 shadow-sm rounded-card p-3 p-md-4 mt-4">
      <h2 class="h6 mb-2">Catatan redaksi</h2>
      <p class="small mb-0">{loker['catatan']}</p>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Layanan", "/layanan/loker")])
    return page(base=base, out_path="layanan/loker.html", active="layanan", situs=situs,
                title="Lowongan Kerja Pandaan Terbaru — Sudut Pandaan",
                description="Loker Pandaan terbaru: operator produksi, admin, barista, pengajar, kru dapur, dan kurir. Plus tips menghindari penipuan lowongan kerja.",
                canonical=situs["base_url"] + "/layanan/loker", body=body, ld=[ld])


def build_nomor_penting(base, situs):
    nomor = load("nomor-penting.json")
    body = f"""
{page_header("Nomor Penting Pandaan", "Daftar nomor darurat dan layanan publik di Pandaan. Daftar ini masih dalam proses verifikasi — mohon utamakan kanal resmi instansi.", [("Beranda", "index.html"), ("Layanan", "layanan/nomor-penting.html"), ("Nomor Penting", "")], base, nomor="05")}
<section class="section" data-page="nomor-penting">
  <div class="container">
    <div class="alert alert-warning small" role="alert">
      <strong>Status data:</strong> {nomor['catatan']}
    </div>
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        {bar_filter(
            aria="Pencarian nomor penting",
            cari={"id": "cariNomor", "label": "Cari instansi",
                  "placeholder": "mis. pemadam, puskesmas, tol"},
            tombol=[{"teks": "Reset", "ikon": "ph-arrows-clockwise", "kelas": "btn-outline-navy",
                     "id": "resetNomor"}],
            lengket=False,
        )}
        <div class="table-responsive">
          <table class="table align-middle bg-white rounded-card overflow-hidden">
            <caption class="small text-muted-2">Nomor darurat nasional 112 dapat dihubungi dari seluruh Indonesia.</caption>
            <thead><tr><th scope="col">Instansi</th><th scope="col">Nomor</th><th scope="col">Status verifikasi</th><th scope="col">Aksi</th></tr></thead>
            {h2_tersembunyi("Daftar nomor penting")}
            <tbody id="daftarNomor"></tbody>
          </table>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="sidebar-widget">
          <h3><i class="ph ph-phone-incoming me-1 text-gold" aria-hidden="true"></i>Alur Pelaporan Darurat</h3>
          <ol class="small ps-3 mb-0">
            <li class="mb-2">Hubungi <strong>112</strong> untuk keadaan darurat yang mengancam nyawa.</li>
            <li class="mb-2">Sebutkan lokasi persis (nama jalan, patokan, atau KM tol).</li>
            <li class="mb-2">Jelaskan kondisi dan jumlah korban bila ada.</li>
            <li class="mb-0">Jangan menyebar foto korban ke media sosial.</li>
          </ol>
        </div>
        <div class="sidebar-widget">
          <h3><i class="ph ph-paper-plane-tilt me-1 text-gold" aria-hidden="true"></i>Bantu Verifikasi</h3>
          <p class="small mb-2">Anda tahu nomor resmi yang belum tercantum? Kirim ke redaksi beserta tautan sumbernya.</p>
          <a class="btn btn-gold w-100" href="{base}layanan/lapor.html">Usulkan Nomor</a>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Layanan", "/layanan/nomor-penting")])
    return page(base=base, out_path="layanan/nomor-penting.html", active="layanan", situs=situs,
                title="Nomor Penting & Darurat Pandaan — Sudut Pandaan",
                description="Daftar nomor penting Pandaan: darurat 112, pemadam kebakaran, puskesmas, PLN, BPBD, dan lainnya — lengkap dengan status verifikasi.",
                canonical=situs["base_url"] + "/layanan/nomor-penting", body=body, ld=[ld])


def build_lapor(base, situs):
    desa_opts = "".join(f'<option value="{esc(d["nama"])}">{esc(d["nama"])}</option>' for d in DESA)
    body = f"""
{page_header("Lapor / Kirim Info", "Punya informasi kejadian, kondisi jalan, atau agenda kegiatan? Kirim ke redaksi. Laporan diverifikasi dulu sebelum tayang.", [("Beranda", "index.html"), ("Layanan", "layanan/lapor.html"), ("Lapor / Kirim Info", "")], base, nomor="05")}
<section class="section" data-page="lapor">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-7">
        <form class="card border-0 shadow-sm rounded-card p-3 p-md-4" id="formLapor" novalidate>
          <h2 class="h5 mb-3">Formulir laporan warga</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="namaPelapor">Nama <span class="text-muted-2 fw-normal">(opsional)</span></label>
              <input class="form-control" id="namaPelapor" name="nama" autocomplete="name">
              <div class="form-text">Nama tidak akan dipublikasikan tanpa izin Anda.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="kontakPelapor">Kontak (WA/HP/email) <span class="required-mark">*</span></label>
              <input class="form-control" id="kontakPelapor" name="kontak" required autocomplete="tel">
              <div class="invalid-feedback">Kontak wajib diisi agar redaksi bisa memverifikasi.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="jenisLaporan">Jenis informasi <span class="required-mark">*</span></label>
              <select class="form-select" id="jenisLaporan" name="jenis" required>
                <option value="">Pilih jenis…</option>
                <option>Lalu lintas / kondisi jalan</option>
                <option>Peristiwa / kejadian darurat</option>
                <option>Info kegiatan / agenda</option>
                <option>Lowongan kerja</option>
                <option>Data wisata/kuliner/UMKM keliru</option>
                <option>Nomor penting / instansi</option>
                <option>Lainnya</option>
              </select>
              <div class="invalid-feedback">Pilih jenis informasi.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="desaLaporan">Desa/Kelurahan <span class="required-mark">*</span></label>
              <select class="form-select" id="desaLaporan" name="desa" required>
                <option value="">Pilih wilayah…</option>
                {desa_opts}
                <option>Luar Pandaan</option>
              </select>
              <div class="invalid-feedback">Pilih desa/kelurahan.</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="lokasiLaporan">Lokasi persis <span class="required-mark">*</span></label>
              <input class="form-control" id="lokasiLaporan" name="lokasi" required placeholder="mis. Tol Pandaan KM 17 arah Malang / Jl. Raya Tretes depan SPBU">
              <div class="invalid-feedback">Tuliskan lokasi sejelas mungkin (patokan, KM, atau nama jalan).</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="waktuLaporan">Waktu kejadian <span class="required-mark">*</span></label>
              <input class="form-control" id="waktuLaporan" name="waktu" type="datetime-local" required>
              <div class="invalid-feedback">Isi waktu kejadian.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="tautanMedia">Tautan foto/video <span class="text-muted-2 fw-normal">(opsional)</span></label>
              <input class="form-control" id="tautanMedia" name="media" type="url" placeholder="https://drive.google.com/…">
              <div class="form-text">Unggah ke Google Drive/Dropbox lalu tempel tautannya. Jangan kirim file besar lewat WA.</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="isiLaporan">Apa yang terjadi? <span class="required-mark">*</span></label>
              <textarea class="form-control" id="isiLaporan" name="isi" rows="5" required
                placeholder="Tuliskan kronologi singkat: apa yang Anda lihat langsung, kapan, kondisi terkini, dan sumber informasi."></textarea>
              <div class="invalid-feedback">Ceritakan informasi Anda.</div>
            </div>
            <div class="col-12">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="izinPublikasi" name="izin" required>
                <label class="form-check-label small" for="izinPublikasi">
                  Saya menyatakan informasi ini benar sepengetahuan saya, dan setuju Sudut Pandaan mempublikasikannya setelah diverifikasi.
                  Saya memahami laporan dapat disunting untuk kejelasan. <span class="required-mark">*</span>
                </label>
                <div class="invalid-feedback">Persetujuan publikasi wajib dicentang.</div>
              </div>
            </div>
            <input type="text" name="website" class="sp-hp" tabindex="-1" autocomplete="off" aria-hidden="true">
            <div class="col-12 d-grid d-sm-flex gap-2">
              <button class="btn btn-primary" type="submit"><i class="ph ph-whatsapp-logo me-1" aria-hidden="true"></i>Kirim via WhatsApp</button>
              <button class="btn btn-outline-primary" type="button" id="kirimEmail" data-copy-report><i class="ph ph-envelope-simple me-1" aria-hidden="true"></i>Kirim via Email</button>
            </div>
            <div class="col-12"><p class="small text-muted-2 mb-0">Fase statis: laporan dikirim melalui WhatsApp/email dengan isian otomatis. Setelah migrasi ke Laravel, laporan masuk ke basis data dengan status <em>menunggu moderasi</em>.</p></div>
          </div>
        </form>
      </div>
      <div class="col-lg-5">
        <div class="sidebar-widget">
          <h3><i class="ph ph-list-numbers me-1 text-gold" aria-hidden="true"></i>Alur Laporan Anda</h3>
          <ol class="small ps-3 mb-0">
            <li class="mb-2"><strong>Diterima</strong> — redaksi membaca laporan dan menghubungi kontak Anda bila perlu.</li>
            <li class="mb-2"><strong>Verifikasi</strong> — dicek ke sumber resmi, foto lokasi, atau saksi kedua.</li>
            <li class="mb-2"><strong>Ditayangkan</strong> — jika layak publikasi, dengan label sumber dan kredit (atau anonim atas permintaan).</li>
            <li class="mb-0"><strong>Diperbarui</strong> — perkembangan di tulis sebagai “Pembaruan HH.MM WIB” di atas artikel.</li>
          </ol>
        </div>
        <div class="sidebar-widget">
          <h3><i class="ph ph-shield-warning me-1 text-gold" aria-hidden="true"></i>Pedoman Etika</h3>
          <ul class="small ps-3 mb-0">
            <li class="mb-2">Jangan kirim foto korban anak, korban kekerasan, atau gambar grafis.</li>
            <li class="mb-2">Hindari menyebut dugaan pelaku sebelum ada keterangan resmi.</li>
            <li class="mb-2">Kami tidak mempublikasikan data pribadi (KTP, nomor rumah, dokumen medis).</li>
            <li class="mb-0">Laporan palsu dapat berujung pada konsekuensi hukum — pastikan informasi benar.</li>
          </ul>
        </div>
        <div class="sidebar-widget">
          <h3><i class="ph ph-whatsapp-logo me-1 text-gold" aria-hidden="true"></i>Butuh cepat?</h3>
          <p class="small">Untuk info lalu lintas mendesak, kirim langsung ke WhatsApp redaksi.</p>
          <a class="btn btn-wa w-100" target="_blank" rel="noopener noreferrer" href="https://wa.me/{situs['wa_admin']}?text=Info%20cepat%20untuk%20Sudut%20Pandaan%3A%20">Chat WhatsApp Redaksi</a>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Layanan", "/layanan/lapor")])
    return page(base=base, out_path="layanan/lapor.html", active="layanan", situs=situs,
                title="Lapor / Kirim Info ke Redaksi — Sudut Pandaan",
                description="Kirim informasi kejadian, kondisi jalan, agenda, atau koreksi data ke redaksi Sudut Pandaan. Laporan diverifikasi sebelum tayang.",
                canonical=situs["base_url"] + "/layanan/lapor", body=body, ld=[ld])


def build_umkm_daftar(base, situs):
    desa_opts = "".join(f'<option value="{esc(d["nama"])}">{esc(d["nama"])} ({esc(d["jenis"])})</option>' for d in DESA)
    body = f"""
{page_header("Daftarkan Usaha Anda", "Isi formulir berikut untuk menampilkan profil usaha Anda di Direktori UMKM Sudut Pandaan. Gratis, dengan proses moderasi redaksi.", [("Beranda", "index.html"), ("UMKM", "umkm/index.html"), ("Daftar UMKM", "")], base, nomor="03")}
<section class="section" data-page="umkm-daftar">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-7">
        <form class="card border-0 shadow-sm rounded-card p-3 p-md-4" id="formUmkm" novalidate>
          <h2 class="h5 mb-3">Formulir pendaftaran UMKM</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="namaUsaha">Nama usaha <span class="required-mark">*</span></label>
              <input class="form-control" id="namaUsaha" name="nama_usaha" required>
              <div class="invalid-feedback">Nama usaha wajib diisi.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="namaPemilik">Nama pemilik <span class="required-mark">*</span></label>
              <input class="form-control" id="namaPemilik" name="pemilik" required>
              <div class="invalid-feedback">Nama pemilik wajib diisi.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="kategoriUsaha">Kategori <span class="required-mark">*</span></label>
              <select class="form-select" id="kategoriUsaha" name="kategori" required>
                <option value="">Pilih kategori…</option>
                <option>Kuliner</option><option>Kerajinan</option><option>Fashion</option>
                <option>Jasa</option><option>Pertanian</option><option>Perdagangan</option><option>Lainnya</option>
              </select>
              <div class="invalid-feedback">Pilih kategori usaha.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="desaUsaha">Desa/Kelurahan <span class="required-mark">*</span></label>
              <select class="form-select" id="desaUsaha" name="desa" required>
                <option value="">Pilih wilayah…</option>{desa_opts}
              </select>
              <div class="invalid-feedback">Pilih desa/kelurahan.</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="deskripsiUsaha">Deskripsi singkat <span class="required-mark">*</span></label>
              <textarea class="form-control" id="deskripsiUsaha" name="deskripsi" rows="3" maxlength="500" required
                placeholder="Ceritakan usaha Anda dalam 1–3 kalimat: apa yang dijual, sejak kapan, apa keunggulannya."></textarea>
              <div class="form-text"><span id="sisaKarakter">500</span> karakter tersisa.</div>
              <div class="invalid-feedback">Deskripsi wajib diisi (maks 500 karakter).</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="alamatUsaha">Alamat <span class="required-mark">*</span></label>
              <input class="form-control" id="alamatUsaha" name="alamat" required placeholder="mis. Jl. Melati No. 10, RT 02/RW 03">
              <div class="invalid-feedback">Alamat wajib diisi.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="waUsaha">Nomor WhatsApp <span class="required-mark">*</span></label>
              <input class="form-control" id="waUsaha" name="whatsapp" required inputmode="tel" placeholder="08xxxxxxxxxx">
              <div class="form-text">Gunakan format 08… (akan diubah otomatis ke format internasional 62…).</div>
              <div class="invalid-feedback">Nomor WhatsApp wajib diisi.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="igUsaha">Instagram / marketplace <span class="text-muted-2 fw-normal">(opsional)</span></label>
              <input class="form-control" id="igUsaha" name="instagram" placeholder="mis. @namausaha atau tautan toko">
            </div>
            <div class="col-md-6">
              <label class="form-label" for="jamUsaha">Jam operasional <span class="text-muted-2 fw-normal">(opsional)</span></label>
              <input class="form-control" id="jamUsaha" name="jam" placeholder="mis. 08.00–20.00 WIB">
            </div>
            <div class="col-12">
              <label class="form-label" for="mapsUsaha">Koordinat / tautan Google Maps <span class="text-muted-2 fw-normal">(opsional)</span></label>
              <input class="form-control" id="mapsUsaha" name="maps" placeholder="Tempel tautan lokasi dari Google Maps agar profil tampil di peta">
            </div>
            <div class="col-12">
              <label class="form-label" for="fotoUsaha">Foto produk <span class="text-muted-2 fw-normal">(fase statis: kirim via WhatsApp)</span></label>
              <input class="form-control" id="fotoUsaha" name="foto" type="url" placeholder="Tempel tautan album foto (Google Drive/Dropbox)">
            </div>
            <div class="col-12">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="izinData" required>
                <label class="form-check-label small" for="izinData">
                  Saya setuju data usaha (nama, kontak, alamat) ditampilkan di situs Sudut Pandaan dan digunakan hanya untuk keperluan direktori ini.
                  <span class="required-mark">*</span>
                </label>
                <div class="invalid-feedback">Persetujuan data wajib dicentang (UU PDP).</div>
              </div>
            </div>
            <input type="text" name="website" class="sp-hp" tabindex="-1" autocomplete="off" aria-hidden="true">
            <div class="col-12 d-grid d-sm-flex gap-2">
              <button class="btn btn-primary" type="submit"><i class="ph ph-whatsapp-logo me-1" aria-hidden="true"></i>Kirim Pendaftaran via WhatsApp</button>
            </div>
            <div class="col-12"><p class="small text-muted-2 mb-0">Pendaftaran gratis. Profil tayang setelah redaksi memverifikasi data (biasanya 1–3 hari kerja).</p></div>
          </div>
        </form>
      </div>
      <div class="col-lg-5">
        <div class="sidebar-widget">
          <h3><i class="ph ph-sparkle me-1 text-gold" aria-hidden="true"></i>Kenapa mendaftar?</h3>
          <ul class="small ps-3 mb-0">
            <li class="mb-2">Etalase gratis: profil usaha, produk, dan tombol WhatsApp.</li>
            <li class="mb-2">Ditemukan lewat pencarian Google (“kripik tempe Pandaan”, dan sejenisnya).</li>
            <li class="mb-2">Tampil di peta interaktif bersama destinasi wisata &amp; kuliner.</li>
            <li class="mb-0">Kesempatan diliput dalam artikel profil usaha.</li>
          </ul>
        </div>
        <div class="sidebar-widget">
          <h3><i class="ph ph-shield-check me-1 text-gold" aria-hidden="true"></i>Yang kami verifikasi</h3>
          <p class="small mb-0">Nama &amp; keberadaan usaha, kontak aktif, dan kategori. Kami tidak meminta data sensitif (NIK, rekening, atau dokumen pajak) melalui formulir ini.</p>
        </div>
        <div class="sidebar-widget">
          <h3><i class="ph ph-trend-up me-1 text-gold" aria-hidden="true"></i>Ingin lebih menonjol?</h3>
          <p class="small mb-2">Paket Premium memberi badge Premium, posisi atas di direktori, dan slot di beranda.</p>
          <a class="btn btn-gold w-100" href="{base}pasang-iklan.html">Lihat Paket Premium</a>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("UMKM", "/umkm/"), ("Daftar UMKM", "/umkm/daftar")])
    return page(base=base, out_path="umkm/daftar.html", active="umkm", situs=situs,
                title="Daftarkan Usaha Anda — Direktori UMKM Sudut Pandaan",
                description="Formulir pendaftaran UMKM Pandaan gratis: tampilkan profil usaha, produk, kontak WhatsApp, dan lokasi di direktori serta peta Sudut Pandaan.",
                canonical=situs["base_url"] + "/umkm/daftar", body=body, ld=[ld])


def build_peta(base, situs):
    css, js = map_assets(base, cluster=True)
    legend = """
    <div class="sp-map-legend">
      <p class="fw-semibold mb-2 small">Legenda</p>
      <div class="d-grid gap-1">
        <span><span class="dot" style="background:#00897B"></span>Wisata</span>
        <span><span class="dot" style="background:#8E24AA"></span>Kuliner</span>
        <span><span class="dot" style="background:#E8B400"></span>UMKM</span>
        <span><span class="dot" style="background:#1565C0"></span>Fasilitas umum</span>
        <span><span class="dot" style="background:#EF6C00"></span>Titik rawan macet</span>
      </div>
    </div>"""
    body = f"""
{page_header("Peta Pandaan", "Peta interaktif titik penting Pandaan: wisata, kuliner, UMKM, fasilitas umum, dan titik rawan kepadatan lalu lintas.", [("Beranda", "index.html"), ("Peta", "")], base, nomor="06")}
<section class="section" data-page="peta">
  <div class="container">
    <div class="row g-4">
      <div class="col-lg-8">
        <div id="peta" class="sp-map" data-peta="semua" role="application" aria-label="Peta interaktif Pandaan">{HINT_PETA}</div>
        <p class="small text-muted-2 mt-2 mb-0">
          Data peta &copy; kontributor <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>.
          Koordinat destinasi merupakan perkiraan dan perlu verifikasi lapangan. Tile OSM publik hanya untuk lalu lintas wajar —
          untuk kunjungan tinggi gunakan penyedia tile berlangganan atau host sendiri.
        </p>
      </div>
      <div class="col-lg-4">
        {legend}
        <div class="mt-4">
          <span class="chip-label d-block mb-2"><i class="ph ph-map-trifold" aria-hidden="true"></i>Tampilkan di peta</span>
          <div class="chip-toggle" id="filterPeta">
            <div class="chip-switch"><input class="form-check-input" type="checkbox" value="wisata" id="cbWisata" checked><label class="form-check-label" for="cbWisata"><i class="ph ph-mountains" aria-hidden="true"></i>Wisata</label></div>
            <div class="chip-switch"><input class="form-check-input" type="checkbox" value="kuliner" id="cbKuliner" checked><label class="form-check-label" for="cbKuliner"><i class="ph ph-bowl-food" aria-hidden="true"></i>Kuliner</label></div>
            <div class="chip-switch"><input class="form-check-input" type="checkbox" value="umkm" id="cbUmkm" checked><label class="form-check-label" for="cbUmkm"><i class="ph ph-storefront" aria-hidden="true"></i>UMKM</label></div>
            <div class="chip-switch"><input class="form-check-input" type="checkbox" value="fasilitas" id="cbFasilitas" checked><label class="form-check-label" for="cbFasilitas"><i class="ph ph-bank" aria-hidden="true"></i>Fasilitas umum</label></div>
            <div class="chip-switch"><input class="form-check-input" type="checkbox" value="macet" id="cbMacet"><label class="form-check-label" for="cbMacet"><i class="ph ph-traffic-cone" aria-hidden="true"></i>Titik rawan macet</label></div>
          </div>
        </div>
        <div class="mt-4">
          <label class="chip-label d-block mb-2" for="cariTitikPeta"><i class="ph ph-magnifying-glass" aria-hidden="true"></i>Cari titik</label>
          <div class="sp-bar-filter-cari">
            <i class="ph ph-magnifying-glass" aria-hidden="true"></i>
            <input class="form-control" id="cariTitikPeta" type="search" placeholder="mis. taman, kripik, tol" aria-label="Cari titik di peta">
          </div>
        </div>
      </div>
    </div>
    <h2 class="sp-section-title mt-5 mb-3">Daftar Titik</h2>
    <div class="row g-3" id="daftarTitik">
      <div class="col-12"><span class="text-muted-2 small">Memuat daftar titik…</span></div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Peta", "/peta")])
    # Ubin peta datang dari server OpenStreetMap: buka koneksinya lebih awal agar
    # LCP halaman peta (ubin pertama) tidak menunggu DNS+TLS.
    preconnect_ubin = '<link rel="preconnect" href="https://tile.openstreetmap.org" crossorigin>'
    return page(base=base, out_path="peta.html", active="jelajah", situs=situs,
                title="Peta Pandaan — Wisata, Kuliner, UMKM & Fasilitas Umum",
                description="Peta interaktif Pandaan: lokasi wisata, tempat makan, UMKM, fasilitas umum, dan titik rawan macet. Lengkap dengan tombol rute ke Google Maps.",
                canonical=situs["base_url"] + "/peta", extra_css=css, extra_scripts=js,
                extra_head=preconnect_ubin, body=body, ld=[ld])


# ---------------------------------------------------------------------------
# HALAMAN STATIS
# ---------------------------------------------------------------------------
def build_tentang(base, situs):
    tim = "".join(f"""
      <div class="col-sm-6 col-lg-3">
        <div class="info-box h-100">
          <div class="avatar-lingkar mb-3" aria-hidden="true"><i class="ph ph-user"></i></div>
          <h3 class="h6 mb-1">{esc(p['nama'])}</h3>
          <p class="small text-muted-2 mb-2">{esc(p['peran'])}</p>
          <p class="small mb-0">{esc(p['bio'])}</p>
        </div>
      </div>""" for p in PENULIS)
    desa_list = "".join(f"<li>{esc(d['nama'])} <span class=\"text-muted-2 small\">({esc(d['jenis'])})</span></li>" for d in DESA)
    body = f"""
{page_header("Tentang Sudut Pandaan", "Portal informasi hyperlocal Pandaan, Kabupaten Pasuruan — dikelola dengan prinsip cepat, akurat, hangat, gotong royong, dan membangun.", [("Beranda", "index.html"), ("Tentang", "")], base, nomor="07")}
<section class="section">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-7">
        <h2 class="sp-section-title mb-3">Cerita kami</h2>
        <div class="article-body">
          <p>Sudut Pandaan berawal dari akun komunitas di <a href="{situs['instagram']}" target="_blank" rel="noopener noreferrer">Instagram</a> dan <a href="{situs['threads']}" target="_blank" rel="noopener noreferrer">Threads</a> <strong>@sudutpandaan</strong> yang membagikan kabar cepat seputar kejadian, lalu lintas, dan suasana kota Pandaan.</p>
          <p>Seiring waktu, informasi di linimasa sulit dicari kembali: laporan lalu lintas hilang tertimbun unggahan baru, dan warga sering bertanya hal yang sama. Karena itu kami membangun situs ini sebagai <em>arsip komunitas</em> yang bisa dicari, dibaca ulang, dan dipercaya.</p>
          <p>Situs ini adalah kanal informasi komunitas, bukan produk berita perusahaan. Kami berpegang pada prinsip: <strong>verifikasi sebelum publikasi</strong>, tandai jelas apa yang masih dugaan, dan koreksi terbuka bila ada kesalahan.</p>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Visi &amp; misi</h2>
        <div class="info-box">
          <p class="mb-2"><strong>Visi:</strong> menjadi rujukan pertama informasi Pandaan dan sekitarnya.</p>
          <p class="mb-3"><strong>Misi:</strong> menyajikan informasi lokal yang cepat, benar, dan berguna bagi warga serta pengunjung Pandaan.</p>
          <div class="d-flex flex-wrap gap-2">
            <span class="badge-soft">Cepat</span><span class="badge-soft">Akurat</span><span class="badge-soft">Hangat</span>
            <span class="badge-soft">Gotong royong</span><span class="badge-soft">Membangun</span>
          </div>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Yang bisa Anda temukan di sini</h2>
        <div class="row g-3">
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Kabar cepat</h3><p class="small mb-0">Peristiwa, lalu lintas, dan kondisi jalan di Pandaan.</p></div></div>
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Jelajah Pandaan</h3><p class="small mb-0">Direktori wisata &amp; kuliner dengan tanggal verifikasi data.</p></div></div>
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Etalase UMKM</h3><p class="small mb-0">Profil usaha lokal lengkap dengan kontak WhatsApp.</p></div></div>
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Layanan warga</h3><p class="small mb-0">Agenda, lowongan kerja, nomor penting, dan kanal lapor.</p></div></div>
        </div>
      </div>

      <div class="col-lg-5">
        <div class="info-box mb-3">
          <h2 class="h6 mb-3">Sekilas wilayah Pandaan</h2>
          <dl class="row mb-0 small">
            <dt class="col-5">Provinsi</dt><dd class="col-7">Jawa Timur</dd>
            <dt class="col-5">Kabupaten</dt><dd class="col-7">Pasuruan</dd>
            <dt class="col-5">Kode wilayah</dt><dd class="col-7">35.14.11</dd>
            <dt class="col-5">Kode pos</dt><dd class="col-7">67156</dd>
            <dt class="col-5">Luas</dt><dd class="col-7">± 43,27 km²</dd>
            <dt class="col-5">Penduduk</dt><dd class="col-7">± 115,8 ribu jiwa (estimasi BPS)</dd>
            <dt class="col-5">Wilayah</dt><dd class="col-7">18 desa &amp; kelurahan</dd>
            <dt class="col-5">Akses tol</dt><dd class="col-7">Tol Gempol–Pandaan (± 13,6 km) → Tol Pandaan–Malang</dd>
          </dl>
          <hr>
          <p class="small text-muted-2 mb-0">Sumber: publikasi BPS Kabupaten Pasuruan, Wikipedia (Pasuruan Regency; Gempol–Pandaan Toll Road), serta dokumen publik lain. Angka demografi bersifat estimasi — perbarui bila ada publikasi resmi terbaru.</p>
        </div>
        <div class="info-box">
          <h2 class="h6 mb-2">Daftar desa &amp; kelurahan</h2>
          <p class="small text-muted-2">18 wilayah di Kecamatan Pandaan.</p>
          <ul class="row small mb-0" style="columns:2">{desa_list}</ul>
        </div>
      </div>
    </div>

    <h2 class="sp-section-title mt-5 mb-3">Tim &amp; desk redaksi</h2>
    <div class="row g-3">{tim}</div>
    <p class="small text-muted-2 mt-3">Ingin bergabung sebagai kontributor warga atau koresponden desa? <a href="{base}kontak.html">Hubungi kami</a>.</p>

    <h2 class="sp-section-title mt-5 mb-3">Pencapaian &amp; transparansi</h2>
    <div class="alert alert-warning small" role="alert">
      <strong>Catatan transparansi:</strong> kami tidak menampilkan angka pengikut, jumlah kunjungan, atau klaim pencapaian lain
      yang belum bisa dibuktikan. Jika ingin memasukkan angka audiens di halaman ini, verifikasi lebih dulu dari <em>insight</em>
      platform resmi (Instagram/Threads Insights) dan cantumkan tanggal pengambilan data, misalnya:
      “±X ribu pengikut per [tanggal], sumber: Insight akun”.
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Tentang", "/tentang")])
    return page(base=base, out_path="tentang.html", active="tentang", situs=situs,
                title="Tentang Kami — Sudut Pandaan",
                description="Kenali Sudut Pandaan: visi, misi, nilai, tim redaksi, dan sumber data wilayah. Portal informasi hyperlocal Pandaan, Kabupaten Pasuruan.",
                canonical=situs["base_url"] + "/tentang", body=body, ld=[ld])


def build_redaksi(base, situs):
    body = f"""
{page_header("Redaksi & Pedoman", "Kode etik, kebijakan verifikasi, dan aturan koreksi yang kami pegang. Transparan agar bisa Anda nilai sendiri.", [("Beranda", "index.html"), ("Redaksi & Pedoman", "")], base)}
<section class="section">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        <div class="toc-box mb-4">
          <p class="fw-semibold mb-2">Isi halaman ini</p>
          <ol class="mb-0 small">
            <li><a href="#pedoman-verifikasi">Pedoman verifikasi data</a></li>
            <li><a href="#alur-redaksi">Alur kerja redaksi</a></li>
            <li><a href="#koreksi">Kebijakan koreksi &amp; hak jawab</a></li>
            <li><a href="#konten-berbayar">Pemisahan berita &amp; konten berbayar</a></li>
            <li><a href="#konten-warga">Kebijakan konten kiriman warga</a></li>
            <li><a href="#penggunaan-ai">Penggunaan teknologi &amp; AI</a></li>
          </ol>
        </div>

        <h2 class="sp-section-title mb-3" id="pedoman-verifikasi">1. Pedoman verifikasi data</h2>
        <div class="article-body">
          <ol>
            <li><strong>Dua sumber untuk klaim penting.</strong> Utamakan sumber resmi: kepolisian, petugas tol, BPBD, dishub, pemerintah desa/kelurahan, atau pengelola tempat.</li>
            <li><strong>Foto/video warga wajib dicek.</strong> Verifikasi lokasi, waktu, dan orisinalitas (pencarian gambar terbalik). Sertakan kredit pemilik.</li>
            <li><strong>Tandai “belum terverifikasi”.</strong> Bila informasi masih awal, tulis apa adanya dan perbarui setelah ada konfirmasi.</li>
            <li><strong>Lindungi identitas.</strong> Hindari menyebut identitas anak, korban kekerasan, atau data pribadi tanpa dasar etis dan hukum.</li>
            <li><strong>Hindari spekulasi.</strong> Jangan menulis dugaan penyebab kecelakaan/kriminal sebelum ada keterangan resmi.</li>
            <li><strong>Batasi gambar grafis.</strong> Gunakan foto netral atau samarkan bagian yang sensitif.</li>
            <li><strong>Data komersial diberi tanggal.</strong> Harga tiket, jam buka, dan nomor kontak selalu mencantumkan tanggal verifikasi terakhir.</li>
          </ol>
        </div>

        <h2 class="sp-section-title mt-5 mb-3" id="alur-redaksi">2. Alur kerja redaksi</h2>
        <p class="small text-muted-2">Setiap informasi melewati tahapan berikut sebelum tayang.</p>
        <div class="info-box">
          <p class="small mb-0">
            Sumber (warga/instansi/lapangan) → <strong>Triase admin</strong> → <strong>Verifikasi</strong> (sumber resmi / saksi kedua / foto asli)
            → <strong>Penulisan</strong> (template baku) → <strong>Penyuntingan</strong> (fakta, judul, foto, tag) →
            <strong>Publikasi</strong> (web) → <strong>Distribusi</strong> (Instagram, Threads, kanal WhatsApp) →
            <strong>Pemantauan</strong> (komentar &amp; koreksi) → <strong>Evaluasi mingguan</strong>.
          </p>
        </div>

        <h2 class="sp-section-title mt-5 mb-3" id="koreksi">3. Kebijakan koreksi &amp; hak jawab</h2>
        <div class="article-body">
          <p>Jika kami keliru, kami memperbaiki terbuka:</p>
          <ul>
            <li>Koreksi ditulis di bagian atas artikel, bukan diselipkan diam-diam.</li>
            <li>Pembaruan perkembangan ditulis berlabel <strong>“Pembaruan HH.MM WIB”</strong>.</li>
            <li>Pihak yang merasa dirugikan dapat mengajukan <strong>hak jawab</strong> melalui kanal resmi; tanggapan akan kami tampilkan.</li>
            <li>Permintaan penghapusan konten sensitif (mis. foto korban, data pribadi) kami proses secepatnya.</li>
          </ul>
          <p><a href="{base}layanan/lapor.html">Ajukan koreksi atau hak jawab →</a></p>
        </div>

        <h2 class="sp-section-title mt-5 mb-3" id="konten-berbayar">4. Pemisahan berita &amp; konten berbayar</h2>
        <div class="article-body">
          <p>Semua materi berbayar diberi label jelas: <strong>“Advertorial”</strong>, <strong>“Konten Bersponsor”</strong>, atau <strong>“Didukung oleh …”</strong> pada judul dan/atau bagian atas artikel. Tim penjualan iklan tidak menentukan keputusan redaksi, dan pengiklan tidak memperoleh hak untuk menyetujui atau menolak tulisan berita.</p>
          <p>Listing UMKM gratis maupun Premium tidak memengaruhi penilaian redaksi atas fakta. Badge <i class="ph-fill ph-star me-1" aria-hidden="true"></i>Premium menandakan status komersial, bukan penilaian kualitas produk.</p>
        </div>

        <h2 class="sp-section-title mt-5 mb-3" id="konten-warga">5. Kebijakan konten kiriman warga</h2>
        <div class="article-body">
          <ul>
            <li>Konten yang dikirim warga dapat dipublikasikan <strong>setelah moderasi dan verifikasi</strong>.</li>
            <li>Pemilik foto/video mendapat kredit. Untuk pemakaian komersial, kami meminta izin tertulis (percakapan WhatsApp dapat menjadi bukti).</li>
            <li>Pengirim bertanggung jawab atas kebenaran informasi yang dikirim.</li>
            <li>Kami tidak mempublikasikan data pribadi tanpa izin, dan menghapus konten bila diminta pemiliknya.</li>
          </ul>
        </div>

        <h2 class="sp-section-title mt-5 mb-3" id="penggunaan-ai">6. Penggunaan teknologi &amp; AI</h2>
        <div class="article-body">
          <p>Kami memanfaatkan alat bantu (termasuk perangkat lunak dan alat AI) untuk pekerjaan teknis seperti penyuntingan cepat, penyusunan tabel, atau pengemasan ulang informasi. <strong>Setiap artikel tetap melalui pemeriksaan manusia</strong> sebelum terbit. Konten yang secara substansial dihasilkan otomatis akan kami tandai. Kami tidak mempublikasikan foto atau video sintetis seolah-olah dokumentasi peristiwa nyata.</p>
        </div>
      </div>

      <div class="col-lg-4">
        <div class="sidebar-widget">
          <h3><i class="ph ph-users me-1 text-gold" aria-hidden="true"></i>Penanggung jawab</h3>
          <p class="small mb-2"><strong>Pemimpin Redaksi:</strong> diisi nama penanggung jawab</p>
          <p class="small mb-2"><strong>Alamat redaksi:</strong> {esc(situs['alamat'])}</p>
          <p class="small mb-2"><strong>Email:</strong> <a href="mailto:{situs['email']}">{esc(situs['email'])}</a></p>
          <p class="small mb-0"><strong>WhatsApp redaksi:</strong> {esc(situs['wa_admin_tampil'])}</p>
        </div>
        <div class="sidebar-widget">
          <h3><i class="ph ph-pencil-simple me-1 text-gold" aria-hidden="true"></i>Kirim tulisan</h3>
          <p class="small">Warga, pelajar, atau komunitas yang ingin berkontribusi tulisan/foto bisa mengirim lewat kanal lapor.</p>
          <a class="btn btn-gold w-100" href="{base}layanan/lapor.html">Kirim Kontribusi</a>
        </div>
        <div class="sidebar-widget">
          <h3><i class="ph ph-bank me-1 text-gold" aria-hidden="true"></i>Catatan hukum</h3>
          <p class="small mb-0">Sudut Pandaan sedang menyiapkan pemenuhan ketentuan administratif dan penyelenggaraan media (antara lain pendaftaran badan usaha serta rujukan pada ketentuan Dewan Pers dan Kode Etik Jurnalistik). Status ini diperbarui di halaman legal begitu selesai.</p>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Redaksi & Pedoman", "/redaksi")])
    return page(base=base, out_path="redaksi.html", active="tentang", situs=situs,
                title="Redaksi & Pedoman Media — Sudut Pandaan",
                description="Kode etik, pedoman verifikasi, alur redaksi, kebijakan koreksi & hak jawab, serta aturan pemisahan konten berbayar di Sudut Pandaan.",
                canonical=situs["base_url"] + "/redaksi", body=body, ld=[ld])


def build_pasang_iklan(base, situs):
    paket = [
        ("Listing UMKM Gratis", "Profil dasar, 1 foto, tombol WhatsApp", "Rp0", "Cocok untuk memulai"),
        ("UMKM Premium (bulanan)", "Badge ⭐, posisi atas direktori, 10 foto, 1 artikel profil/bulan, tampil di beranda", "Rp150–300 ribu", "Paling diminati UMKM"),
        ("Paket Wisata/Kuliner Unggulan", "Halaman detail khusus + sorotan beranda + 1 reels Instagram", "Rp500 ribu–1,5 juta", "Untuk destinasi & restoran"),
        ("Banner sidebar", "300×250 atau 300×600 per bulan", "Rp300–800 ribu", "Inventaris terbatas"),
        ("Banner header/leaderboard", "728×90 (desktop) / 320×100 (mobile)", "Rp500 ribu–1,5 juta", "Paling terlihat"),
        ("Advertorial", "Artikel berlabel + distribusi Instagram & Threads", "Rp300 ribu–1 juta", "Wajib berlabel"),
        ("Promosi event", "Halaman agenda + sorotan + story", "Rp200–750 ribu", "Untuk kegiatan komunitas"),
        ("Paket Sosmed + Web (combo)", "Website + Instagram + Threads + kanal WhatsApp", "Rp1–3 juta", "Paket terlengkap"),
        ("Loker premium", "Posisi atas halaman lowongan selama 14 hari", "Rp100–250 ribu", "Disaring redaksi"),
        ("Sponsor rubrik", "Mis. “Info Lalu Lintas didukung oleh …”", "Rp1–3 juta/bln", "Iklan paling etis"),
    ]
    rows = "".join(
        f"<tr><th scope=\"row\" class=\"fw-semibold\">{esc(n)}</th><td class=\"small\">{esc(i)}</td>"
        f"<td class=\"fw-semibold text-sp-green text-nowrap\">{esc(h)}</td><td class=\"small text-muted-2\">{esc(c)}</td></tr>"
        for n, i, h, c in paket)
    body = f"""
{page_header("Pasang Iklan &amp; Promosi UMKM", "Media kit ringkas Sudut Pandaan: audiens lokal Pandaan &amp; pelintas jalur Surabaya–Malang, format iklan, dan paket kerja sama.", [("Beranda", "index.html"), ("Pasang Iklan", "")], base, nomor="08")}
<section class="section">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8">
        <div class="alert alert-warning small" role="alert">
          <strong>Harga contoh:</strong> seluruh angka di halaman ini adalah <em>ilustrasi awal untuk diuji pasar</em>, bukan tarif final.
          Sesuaikan setelah 1–2 bulan data nyata terkumpul.
        </div>

        <h2 class="sp-section-title mb-3">Mengapa beriklan di Sudut Pandaan?</h2>
        <div class="row g-3 mb-4">
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Audiens lokal tersegmentasi</h3><p class="small mb-0">Warga Pandaan, pekerja komuter, dan wisatawan yang melewati jalur Surabaya–Malang.</p></div></div>
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Niat beli tinggi</h3><p class="small mb-0">Pembaca mencari tempat makan, penginapan, bengkel, klinik, dan oleh-oleh di sekitar Pandaan.</p></div></div>
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Bisa diukur</h3><p class="small mb-0">Laporan bulanan: tayangan halaman, klik, dan klik WhatsApp dari profil Anda.</p></div></div>
          <div class="col-md-6"><div class="info-box h-100"><h3 class="h6">Tanpa biaya produksi</h3><p class="small mb-0">Cukup kirim foto produk &amp; deskripsi; tim kami menyiapkan materi tampilannya.</p></div></div>
        </div>

        <h2 class="sp-section-title mb-3">Paket &amp; harga (contoh)</h2>
        <div class="table-responsive">
          <table class="table table-bordered align-middle bg-white">
            <thead><tr><th scope="col">Produk</th><th scope="col">Isi</th><th scope="col">Harga</th><th scope="col">Catatan</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Penempatan slot iklan</h2>
        <div class="article-body">
          <ul>
            <li><strong>Header leaderboard</strong> — 728×90 (desktop) / 320×100 (mobile)</li>
            <li><strong>Sidebar atas</strong> — 300×250 (tampil di semua halaman artikel &amp; direktori)</li>
            <li><strong>Sidebar bawah</strong> — 300×600 (sticky di desktop)</li>
            <li><strong>Dalam artikel</strong> — setelah paragraf ke-3 dan ke-7</li>
            <li><strong>Akhir artikel</strong> — 336×280</li>
            <li><strong>Beranda</strong> — di antara bagian Berita dan Jelajah</li>
          </ul>
          <p class="small text-muted-2">Aturan kami: maksimal tiga slot iklan terlihat per layar, tanpa pop-up mengganggu, tinggi slot dipatok agar tidak menggeser tata letak (CLS), dan setiap iklan diberi label “Iklan”.</p>
        </div>

        <h2 class="sp-section-title mt-5 mb-3">Cara kerja sama</h2>
        <ol class="article-body">
          <li>Kirim permintaan via WhatsApp/email dengan menyebut paket yang diminati.</li>
          <li>Kami kirim bukti tayangan halaman bulan berjalan sebagai gambaran audiens.</li>
          <li><strong>Uji coba gratis 1 bulan</strong> untuk 10 UMKM pertama — tanpa biaya, tanpa komitmen lanjutan.</li>
          <li>Setelah sepakat: kirim materi (foto, deskripsi, kontak), kami tayangkan sesuai jadwal.</li>
          <li>Laporan performa dikirim setiap awal bulan. Pembayaran melalui transfer bank atau QRIS.</li>
        </ol>
        <div class="alert alert-light border rounded-card small mb-0">
          <strong>Kebijakan iklan:</strong> konten berbayar selalu berlabel. Kami menolak iklan yang menyesatkan, menjanjikan hasil pasti,
          atau berpotensi merugikan pembaca (mis. investasi cepat kaya, produk kesehatan tanpa izin edar).
        </div>
      </div>

      <div class="col-lg-4">
        <div class="sidebar-widget">
          <h3><i class="ph ph-envelope me-1 text-gold" aria-hidden="true"></i>Minta media kit</h3>
          <p class="small">Kami kirim dokumen media kit lengkap (format iklan, contoh penempatan, dan lembar pemesanan).</p>
          <a class="btn btn-wa w-100 mb-2" target="_blank" rel="noopener noreferrer"
             href="https://wa.me/{situs['wa_admin']}?text=Halo%20Sudut%20Pandaan%2C%20saya%20tertarik%20beriklan.%20Mohon%20dikirim%20media%20kit.">Minta via WhatsApp</a>
          <a class="btn btn-outline-primary w-100" href="mailto:{situs['email']}?subject=Permintaan%20Media%20Kit%20Sudut%20Pandaan">Minta via Email</a>
        </div>
        {ad_slot("Iklan", "", "250px").replace("{base}", base)}
        <div class="sidebar-widget">
          <h3><i class="ph ph-briefcase me-1 text-gold" aria-hidden="true"></i>Cocok untuk</h3>
          <ul class="small ps-3 mb-0">
            <li class="mb-2">UMKM kuliner, kerajinan, fashion, jasa</li>
            <li class="mb-2">Pengelola wisata &amp; penginapan</li>
            <li class="mb-2">Klinik, bengkel, sekolah, dealer, perumahan</li>
            <li class="mb-0">Event organizer &amp; kegiatan komunitas</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Pasang Iklan", "/pasang-iklan")])
    return page(base=base, out_path="pasang-iklan.html", active="tentang", situs=situs,
                title="Pasang Iklan & Promosi UMKM — Media Kit Sudut Pandaan",
                description="Media kit Sudut Pandaan: paket iklan banner, advertorial, listing UMKM Premium, promosi event, dan sponsor rubrik untuk audiens lokal Pandaan.",
                canonical=situs["base_url"] + "/pasang-iklan", body=body, ld=[ld])


def build_kontak(base, situs):
    body = f"""
{page_header("Kontak", "Hubungi redaksi untuk pertanyaan, kerja sama, koreksi berita, atau permintaan data.", [("Beranda", "index.html"), ("Kontak", "")], base, nomor="07")}
<section class="section" data-page="kontak">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-7">
        <form class="card border-0 shadow-sm rounded-card p-3 p-md-4" id="formKontak" novalidate>
          <h2 class="h5 mb-3">Kirim pesan</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="namaKontak">Nama <span class="required-mark">*</span></label>
              <input class="form-control" id="namaKontak" name="nama" required autocomplete="name">
              <div class="invalid-feedback">Nama wajib diisi.</div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="emailKontak">Email <span class="required-mark">*</span></label>
              <input class="form-control" id="emailKontak" name="email" type="email" required autocomplete="email">
              <div class="invalid-feedback">Email wajib diisi dengan format yang benar.</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="subjekKontak">Subjek <span class="required-mark">*</span></label>
              <select class="form-select" id="subjekKontak" name="subjek" required>
                <option value="">Pilih subjek…</option>
                <option>Koreksi berita / hak jawab</option>
                <option>Laporkan data wisata/kuliner/UMKM</option>
                <option>Kerja sama &amp; iklan</option>
                <option>Kirim press release / informasi kegiatan</option>
                <option>Lowongan kerja</option>
                <option>Masalah teknis situs</option>
                <option>Lainnya</option>
              </select>
              <div class="invalid-feedback">Pilih subjek pesan.</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="isiKontak">Pesan <span class="required-mark">*</span></label>
              <textarea class="form-control" id="isiKontak" name="pesan" rows="5" required></textarea>
              <div class="invalid-feedback">Tuliskan pesan Anda.</div>
            </div>
            <div class="col-12">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="izinKontak" required>
                <label class="form-check-label small" for="izinKontak">Saya setuju data yang saya kirim digunakan untuk keperluan menjawab pesan ini. <span class="required-mark">*</span></label>
                <div class="invalid-feedback">Persetujuan diperlukan (UU PDP).</div>
              </div>
            </div>
            <input type="text" name="website" class="sp-hp" tabindex="-1" autocomplete="off" aria-hidden="true">
            <div class="col-12 d-grid d-sm-flex gap-2">
              <button class="btn btn-primary" type="submit"><i class="ph ph-paper-plane-tilt me-1" aria-hidden="true"></i>Kirim Pesan</button>
              <a class="btn btn-outline-primary" href="mailto:{situs['email']}?subject=Kontak%20Sudut%20Pandaan"><i class="ph ph-envelope-simple me-1" aria-hidden="true"></i>Kirim via Email</a>
            </div>
            <div class="col-12"><p class="small text-muted-2 mb-0">Fase statis: form membuka klien email Anda dengan isian otomatis (mailto). Setelah migrasi Laravel, pesan tersimpan di basis data dan tampil di panel admin.</p></div>
          </div>
        </form>
      </div>
      <div class="col-lg-5">
        <div class="info-box mb-3">
          <h2 class="h6 mb-3">Kontak langsung</h2>
          <p class="small mb-2"><i class="ph ph-whatsapp-logo me-2 text-sp-green" aria-hidden="true"></i>WhatsApp redaksi: <a href="https://wa.me/{situs['wa_admin']}" target="_blank" rel="noopener noreferrer">{esc(situs['wa_admin_tampil'])}</a></p>
          <p class="small mb-2"><i class="ph ph-envelope-simple me-2 text-sp-green" aria-hidden="true"></i><a href="mailto:{situs['email']}">{esc(situs['email'])}</a></p>
          <p class="small mb-2"><i class="ph ph-map-pin me-2 text-sp-green" aria-hidden="true"></i>{esc(situs['alamat'])}</p>
          <p class="small mb-0"><i class="ph ph-clock me-2 text-sp-green" aria-hidden="true"></i>Jam respons: {esc(situs['jam_respons'])}</p>
        </div>
        <div class="info-box mb-3">
          <h2 class="h6 mb-2">Ikuti &amp; hubungi lewat sosial media</h2>
          <div class="d-flex flex-wrap gap-2">
            <a class="btn btn-sm btn-outline-primary" href="{situs['instagram']}" target="_blank" rel="noopener noreferrer"><i class="ph ph-instagram-logo me-1" aria-hidden="true"></i>Instagram</a>
            <a class="btn btn-sm btn-outline-primary" href="{situs['threads']}" target="_blank" rel="noopener noreferrer"><i class="ph ph-threads-logo me-1" aria-hidden="true"></i>Threads</a>
            <a class="btn btn-sm btn-outline-primary" href="{situs['facebook']}" target="_blank" rel="noopener noreferrer"><i class="ph ph-facebook-logo me-1" aria-hidden="true"></i>Facebook</a>
            <a class="btn btn-sm btn-outline-primary" href="{situs['tiktok']}" target="_blank" rel="noopener noreferrer"><i class="ph ph-tiktok-logo me-1" aria-hidden="true"></i>TikTok</a>
          </div>
        </div>
        <div class="info-box">
          <h2 class="h6 mb-2">Sebelum menghubungi</h2>
          <ul class="small ps-3 mb-0">
            <li class="mb-2">Untuk koreksi berita, sebutkan tautan artikel dan bagian yang keliru.</li>
            <li class="mb-2">Untuk laporan kondisi jalan, gunakan <a href="{base}layanan/lapor.html">form Lapor</a> agar formatnya lengkap.</li>
            <li class="mb-0">Untuk darurat, hubungi <strong>112</strong> — jangan menunggu balasan redaksi.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Kontak", "/kontak")])
    return page(base=base, out_path="kontak.html", active="tentang", situs=situs,
                title="Kontak Redaksi — Sudut Pandaan",
                description="Hubungi redaksi Sudut Pandaan: WhatsApp, email, dan kanal sosial media. Untuk koreksi berita, kerja sama iklan, atau kirim informasi kegiatan.",
                canonical=situs["base_url"] + "/kontak", body=body, ld=[ld])


def build_legal(base, situs):
    privasi = f"""
<section class="section">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8 article-body">
        <p class="small text-muted-2">Terakhir diperbarui: 16 Oktober 2026</p>
        <p>Halaman ini menjelaskan bagaimana Sudut Pandaan menangani data pribadi Anda. Kami berupaya mematuhi prinsip perlindungan data pribadi sebagaimana diatur dalam UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP).</p>
        <h2>1. Data yang kami kumpulkan</h2>
        <ul>
          <li><strong>Data yang Anda kirim sendiri:</strong> nama, kontak (WhatsApp/email), dan isi pesan melalui form Lapor, Kontak, atau pendaftaran UMKM.</li>
          <li><strong>Data teknis dasar:</strong> jenis perangkat, peramban, halaman yang dikunjungi, dan waktu kunjungan — hanya jika analitik diaktifkan.</li>
          <li><strong>Preferensi lokal:</strong> pilihan mode terang/gelap dan artikel tersimpan disimpan di peramban Anda (localStorage), bukan di server kami.</li>
        </ul>
        <h2>2. Tujuan penggunaan</h2>
        <ul>
          <li>Menjawab pesan dan memverifikasi laporan yang Anda kirim.</li>
          <li>Menayangkan profil usaha pada direktori UMKM (sesuai persetujuan Anda).</li>
          <li>Menyusun laporan statistik internal (jumlah kunjungan, halaman populer) untuk perbaikan layanan.</li>
        </ul>
        <h2>3. Dasar dan batas penggunaan</h2>
        <p>Kami meminta persetujuan eksplisit melalui kotak centang pada setiap formulir, membatasi data pada yang benar-benar diperlukan, dan tidak menjual atau menyewakan data Anda kepada pihak ketiga untuk tujuan pemasaran.</p>
        <h2>4. Data yang tidak kami minta</h2>
        <p>Kami <strong>tidak pernah</strong> meminta NIK, nomor rekening, PIN/OTP, atau dokumen pajak melalui formulir di situs ini. Jika ada pihak yang mengaku dari Sudut Pandaan dan meminta hal tersebut, jangan diikuti dan laporkan kepada kami.</p>
        <h2>5. Cookie &amp; analitik</h2>
        <p>Situs ini menyimpan preferensi tampilan di peramban Anda. Bila nantinya kami mengaktifkan analitik pihak ketiga (mis. Google Analytics) atau iklan (mis. AdSense), kami akan menampilkan banner persetujuan lebih dahulu dan memperbarui halaman ini dengan daftar penyedia beserta tautan kebijakan privasi masing-masing. Untuk saat ini kami menyarankan alat yang lebih ramah privasi (mis. Umami/Plausible) tanpa pelacakan lintas situs.</p>
        <h2>6. Retensi &amp; penghapusan</h2>
        <p>Pesan masuk disimpan selama diperlukan untuk menindaklanjuti laporan, umumnya paling lama 12 bulan setelah selesai ditangani. Anda dapat meminta penghapusan data dan kami akan memprosesnya dalam waktu wajar.</p>
        <h2>7. Hak Anda</h2>
        <ul>
          <li>Meminta akses dan salinan data yang kami simpan tentang Anda.</li>
          <li>Meminta koreksi data yang tidak akurat.</li>
          <li>Meminta penghapusan data dan/atau penarikan persetujuan.</li>
          <li>Mengajukan keberatan atas penggunaan data tertentu.</li>
        </ul>
        <h2>8. Keamanan</h2>
        <p>Kami menggunakan HTTPS, akses terbatas untuk pengelola, dan praktik pengamanan dasar untuk melindungi data. Meski demikian, tidak ada sistem yang sepenuhnya bebas risiko; jangan mengirim dokumen rahasia melalui formulir publik.</p>
        <h2>9. Kontak</h2>
        <p>Permintaan terkait data pribadi: <a href="mailto:{situs['email']}">{esc(situs['email'])}</a> atau WhatsApp {esc(situs['wa_admin_tampil'])} dengan subjek “Permintaan Data Pribadi”.</p>
      </div>
      <div class="col-lg-4">
        <div class="sidebar-widget">
          <h3>Ringkasnya</h3>
          <ul class="small ps-3 mb-0">
            <li class="mb-2">Data form hanya dipakai untuk menjawab/verifikasi.</li>
            <li class="mb-2">Kami tidak minta NIK/rekening/PIN.</li>
            <li class="mb-2">Tidak ada pelacakan lintas situs tanpa persetujuan.</li>
            <li class="mb-0">Anda bisa minta hapus data kapan saja.</li>
          </ul>
        </div>
        <div class="sidebar-widget">
          <h3>Halaman legal lain</h3>
          <ul class="list-unstyled small mb-0">
            <li class="mb-2"><a href="{base}disclaimer.html">Disclaimer</a></li>
            <li class="mb-2"><a href="{base}syarat-ketentuan.html">Syarat &amp; Ketentuan</a></li>
            <li class="mb-0"><a href="{base}redaksi.html">Pedoman Media Siber</a></li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>
"""

    disclaimer = f"""
<section class="section">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8 article-body">
        <p class="small text-muted-2">Terakhir diperbarui: 16 Oktober 2026</p>
        <div class="correction-box">
          <p class="mb-0"><strong>Ringkasan:</strong> Informasi di Sudut Pandaan disajikan sebagai referensi umum. Kami berusaha menjaga akurasi,
          namun harga, jam operasional, dan kondisi lalu lintas dapat berubah sewaktu-waktu. Mohon konfirmasi langsung kepada pengelola
          atau pihak berwenang. Konten bertanda “Bersponsor”/“Advertorial” adalah materi berbayar.</p>
        </div>
        <h2>1. Ketepatan informasi</h2>
        <p>Setiap artikel mencantumkan waktu publikasi, tanggal pembaruan, dan sumber bila memungkinkan. Informasi yang masih dalam proses verifikasi diberi label <em>“belum terverifikasi”</em>. Ketergantungan pada satu sumber laporan lapangan dapat berubah seiring perkembangan.</p>
        <h2>2. Data tempat &amp; harga</h2>
        <p>Harga tiket, jam buka, dan fasilitas pada direktori wisata/kuliner/UMKM adalah data yang kami himpun pada tanggal verifikasi yang tercantum di setiap entri. Perubahan kebijakan pengelola dapat terjadi setelah tanggal tersebut. Redaksi tidak bertanggung jawab atas kerugian akibat perbedaan data, namun kami akan memperbaiki laporan yang terbukti keliru.</p>
        <h2>3. Informasi lalu lintas</h2>
        <p>Halaman Info Lalu Lintas adalah kanal komunitas, <strong>bukan</strong> kanal resmi pengelola jalan atau kepolisian. Untuk keputusan perjalanan maupun keadaan darurat, gunakan kanal resmi. Jangan mengandalkan situs ini untuk situasi yang mengancam keselamatan.</p>
        <h2>4. Konten pihak ketiga &amp; tautan</h2>
        <p>Tautan keluar ke situs lain disediakan untuk kemudahan; kami tidak mengendalikan isi maupun kebijakan privasi situs tersebut. Peta menggunakan data © kontributor OpenStreetMap sesuai lisensi Open Database License (ODbL).</p>
        <h2>5. Konten berbayar</h2>
        <p>Materi berbayar selalu diberi label. Flag “Premium” pada direktori UMKM menunjukkan status komersial, bukan jaminan kualitas. Redaksi tidak menjamin produk/jasa yang diiklankan.</p>
        <h2>6. Tidak sebagai nasihat profesional</h2>
        <p>Konten di situs ini bukan nasihat hukum, medis, keuangan, atau keselamatan. Untuk keputusan penting, konsultasikan kepada pihak yang berkompeten.</p>
        <h2>7. Batasan tanggung jawab</h2>
        <p>Sejauh diizinkan hukum yang berlaku, Sudut Pandaan tidak bertanggung jawab atas kerugian langsung maupun tidak langsung akibat penggunaan informasi di situs ini. Permintaan koreksi dapat dikirim ke <a href="{base}kontak.html">Kontak</a>.</p>
      </div>
      <div class="col-lg-4">
        <div class="sidebar-widget">
          <h3>Perlu koreksi?</h3>
          <p class="small">Kalau ada data yang keliru, kami perbaiki dengan transparan.</p>
          <a class="btn btn-gold w-100" href="{base}layanan/lapor.html">Laporkan Data Keliru</a>
        </div>
      </div>
    </div>
  </div>
</section>
"""

    syarat = f"""
<section class="section">
  <div class="container">
    <div class="row g-4 g-lg-5">
      <div class="col-lg-8 article-body">
        <p class="small text-muted-2">Terakhir diperbarui: 16 Oktober 2026</p>
        <p>Dengan mengakses dan menggunakan situs Sudut Pandaan, Anda dianggap menyetujui ketentuan berikut.</p>
        <h2>1. Penerimaan ketentuan</h2>
        <p>Jika Anda tidak setuju dengan ketentuan ini, mohon tidak menggunakan situs. Kami dapat memperbarui ketentuan ini dan akan mencantumkan tanggal pembaruan di halaman ini.</p>
        <h2>2. Penggunaan yang diizinkan</h2>
        <p>Anda boleh membaca, membagikan tautan, dan mengutip sebagian konten dengan menyebutkan sumber “Sudut Pandaan” beserta tautan artikel aslinya. Anda <strong>tidak boleh</strong> menyalin seluruh artikel untuk diterbitkan ulang, menjual kembali konten kami, atau menggunakannya untuk pelatihan model otomatis tanpa izin tertulis.</p>
        <h2>3. Konten kiriman pengguna</h2>
        <ul>
          <li>Anda menjamin memiliki hak atas materi yang dikirim (foto, video, tulisan).</li>
          <li>Anda memberi Sudut Pandaan izin non-eksklusif untuk menayangkan, menyunting, dan mendistribusikan materi tersebut di kanal kami.</li>
          <li>Kami berhak menolak atau menghapus kiriman yang melanggar hukum, memuat kebencian, fitnah, atau data pribadi pihak lain.</li>
        </ul>
        <h2>4. Iklan &amp; pihak ketiga</h2>
        <p>Kerja sama iklan diatur perjanjian terpisah. Materi berbayar selalu diberi label. Kami tidak bertanggung jawab atas transaksi antara Anda dan pengiklan.</p>
        <h2>5. Merek &amp; hak cipta</h2>
        <p>Nama, logo, dan identitas visual Sudut Pandaan dilindungi. Foto yang kami cantumkan sebagai ilustrasi akan diganti dengan dokumentasi berlisensi seiring ketersediaan aset asli.</p>
        <h2>6. Batasan tanggung jawab</h2>
        <p>Layanan disediakan “sebagaimana adanya”. Kami tidak menjamin situs selalu bebas gangguan, dan tidak bertanggung jawab atas kerugian yang timbul dari gangguan teknis, termasuk ketidaktersediaan sementara.</p>
        <h2>7. Perubahan &amp; penghentian</h2>
        <p>Kami dapat mengubah, menangguhkan, atau menghentikan bagian layanan tanpa pemberitahuan sebelumnya. Untuk layanan berbayar yang sedang berjalan, kami akan menginformasikan perubahan melalui kontak yang Anda berikan.</p>
        <h2>8. Hukum yang berlaku</h2>
        <p>Ketentuan ini tunduk pada hukum yang berlaku di Republik Indonesia. Sengketa diupayakan diselesaikan secara musyawarah terlebih dahulu.</p>
        <h2>9. Kontak</h2>
        <p>Pertanyaan mengenai ketentuan ini: <a href="mailto:{situs['email']}">{esc(situs['email'])}</a>.</p>
      </div>
      <div class="col-lg-4">
        <div class="sidebar-widget">
          <h3>Mengutip konten kami?</h3>
          <p class="small mb-0">Boleh — cukup cantumkan sumber dan tautan. Untuk penerbitan ulang penuh atau kerja sama, hubungi redaksi lebih dulu.</p>
        </div>
      </div>
    </div>
  </div>
</section>
"""

    pages = [
        ("privasi.html", "Kebijakan Privasi", "Bagaimana Sudut Pandaan mengumpulkan, menggunakan, dan melindungi data pribadi Anda. Sesuai prinsip UU Perlindungan Data Pribadi.", privasi),
        ("disclaimer.html", "Disclaimer", "Batasan informasi di Sudut Pandaan: akurasi data wisata, kanal lalu lintas komunitas, konten berbayar, dan tautan pihak ketiga.", disclaimer),
        ("syarat-ketentuan.html", "Syarat & Ketentuan", "Ketentuan penggunaan situs Sudut Pandaan: hak cipta, konten kiriman pengguna, aturan iklan, dan batasan tanggung jawab.", syarat),
    ]
    out = []
    for path, judul, desk, isi in pages:
        ld = breadcrumb_ld(situs["base_url"], [("Beranda", "/"), (judul, "/" + path.replace(".html", ""))])
        out.append(page(base=base, out_path=path, active="tentang", situs=situs, title=f"{judul} — Sudut Pandaan",
                        description=desk, canonical=situs["base_url"] + "/" + path.replace(".html", ""),
                        body=page_header(judul, "", [("Beranda", "index.html"), (judul, "")], base) + isi, ld=[ld]))
    return out


def build_404(base, situs):
    body = f"""
<section class="section">
  <div class="container text-center" style="max-width:720px">
    <p class="display-1 fw-bold text-sp-green mb-0">404</p>
    <h1 class="h3 mb-2">Halaman tidak ditemukan</h1>
    <p class="text-muted-2 mb-4">Tautan mungkin sudah berubah atau salah ketik. Coba salah satu jalur berikut, atau cari langsung di situs.</p>
    <form class="row g-2 justify-content-center mb-4" action="{base}berita/index.html" method="get" role="search">
      <div class="col-sm-8">
        <label class="visually-hidden" for="q404">Cari kata kunci</label>
        <input class="form-control" id="q404" name="q" type="search" placeholder="mis. macet tol, wisata keluarga" required>
      </div>
      <div class="col-sm-4 d-grid"><button class="btn btn-primary" type="submit">Cari</button></div>
    </form>
    <div class="d-flex flex-wrap gap-2 justify-content-center">
      <a class="btn btn-outline-primary" href="{base}index.html">Beranda</a>
      <a class="btn btn-outline-primary" href="{base}berita/index.html">Berita</a>
      <a class="btn btn-outline-primary" href="{base}wisata/index.html">Wisata</a>
      <a class="btn btn-outline-primary" href="{base}kuliner/index.html">Kuliner</a>
      <a class="btn btn-outline-primary" href="{base}umkm/index.html">UMKM</a>
      <a class="btn btn-outline-primary" href="{base}layanan/lalu-lintas.html">Info Lalu Lintas</a>
      <a class="btn btn-outline-primary" href="{base}peta.html">Peta</a>
    </div>
  </div>
</section>
"""
    return page(base=base, out_path="404.html", active="", situs=situs, noindex=True,
                title="Halaman tidak ditemukan (404) — Sudut Pandaan",
                description="Halaman yang Anda cari tidak ditemukan. Gunakan pencarian atau tautan navigasi untuk menemukan informasi Pandaan.",
                canonical=situs["base_url"] + "/404", body=body)


def build_link_bio(base, situs):
    body = f"""
<section class="section">
  <div class="container" style="max-width:560px">
    <div class="text-center mb-4">
      <img src="{base}assets/img/logo.svg" alt="Logo Sudut Pandaan" width="72" height="72" class="mb-2">
      <h1 class="h4 mb-1">Sudut<span class="text-gold-dark">Pandaan</span></h1>
      <p class="text-muted-2 small mb-0">Mata Komunitas Pandaan — kabar, wisata, kuliner, dan UMKM.</p>
    </div>
    <div class="d-grid gap-3">
      <a class="btn btn-primary py-3" href="{base}layanan/lalu-lintas.html"><i class="ph ph-traffic-cone me-2" aria-hidden="true"></i>Info Lalu Lintas Hari Ini</a>
      <a class="btn btn-primary py-3" href="{base}berita/index.html"><i class="ph ph-newspaper me-2" aria-hidden="true"></i>Berita Terbaru</a>
      <a class="btn btn-primary py-3" href="{base}wisata/index.html"><i class="ph ph-signpost me-2" aria-hidden="true"></i>Direktori Wisata</a>
      <a class="btn btn-primary py-3" href="{base}kuliner/index.html"><i class="ph ph-bowl-food me-2" aria-hidden="true"></i>Kuliner Pandaan</a>
      <a class="btn btn-primary py-3" href="{base}umkm/index.html"><i class="ph ph-storefront me-2" aria-hidden="true"></i>Direktori UMKM</a>
      <a class="btn btn-wa py-3" href="https://wa.me/{situs['wa_admin']}?text=Halo%20Sudut%20Pandaan%2C%20saya%20mau%20ikut%20kanal%20info" target="_blank" rel="noopener noreferrer"><i class="ph ph-whatsapp-logo me-2" aria-hidden="true"></i>Minta Info via WhatsApp</a>
      <a class="btn btn-gold py-3" href="{base}layanan/lapor.html"><i class="ph ph-paper-plane-tilt me-2" aria-hidden="true"></i>Kirim Info / Lapor</a>
    </div>
    <div class="d-flex justify-content-center gap-3 mt-4">
      <a class="fs-4 text-decoration-none text-sp-green" href="{situs['instagram']}" target="_blank" rel="noopener noreferrer" aria-label="Instagram"><i class="ph ph-instagram-logo" aria-hidden="true"></i></a>
      <a class="fs-4 text-decoration-none text-sp-green" href="{situs['threads']}" target="_blank" rel="noopener noreferrer" aria-label="Threads"><i class="ph ph-threads-logo" aria-hidden="true"></i></a>
      <a class="fs-4 text-decoration-none text-sp-green" href="{situs['facebook']}" target="_blank" rel="noopener noreferrer" aria-label="Facebook"><i class="ph ph-facebook-logo" aria-hidden="true"></i></a>
      <a class="fs-4 text-decoration-none text-sp-green" href="{situs['tiktok']}" target="_blank" rel="noopener noreferrer" aria-label="TikTok"><i class="ph ph-tiktok-logo" aria-hidden="true"></i></a>
    </div>
    <p class="text-center small text-muted-2 mt-4 mb-0">Halaman ini dibuat khusus sebagai tautan bio Instagram &amp; Threads. <a href="{base}index.html">Masuk ke situs lengkap &rarr;</a></p>
  </div>
</section>
"""
    return page(base=base, out_path="link/index.html", active="", situs=situs,
                title="Link Bio — Sudut Pandaan",
                description="Semua tautan penting Sudut Pandaan: info lalu lintas, berita terbaru, wisata, kuliner, UMKM, dan kanal lapor.",
                canonical=situs["base_url"] + "/link/", body=body, ld=[breadcrumb_ld(situs["base_url"], [("Beranda", "/"), ("Link Bio", "/link/")])])


def build_berita_detail_redirect(base, situs):
    """Jembatan URL lama: /berita/detail.html?slug=<slug> → /berita/<slug>.

    Dipakai untuk tautan yang sudah tersebar (WA/Instagram) maupun saat migrasi
    ke Laravel (blueprint bagian 6.3). Empat perilaku yang dijaga:
      1. slug valid & halamannya ada  → dialihkan (replace, tanpa menumpuk riwayat);
      2. slug valid tetapi tidak ada  → halaman "tidak ditemukan" + daftar berita;
      3. tanpa slug                   → langsung ke indeks berita;
      4. selalu noindex + canonical ke /berita/ agar tidak jadi duplikat di mesin pencari.
    Daftar slug ditulis statis di berkas ini supaya jembatan tetap akurat walau
    JavaScript dimatikan (tidak perlu memuat assets/data/berita.json).
    """
    slug_dikenal = [b["slug"] for b in BERITA]
    daftar_tautan = "".join(
        f'<li><a href="{b["slug"]}.html">{esc(b["judul"])}</a></li>' for b in BERITA[:6]
    )
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mengalihkan… — Sudut Pandaan</title>
<meta name="description" content="Halaman pengalihan ke artikel Sudut Pandaan. Bila tautan tidak berpindah otomatis, gunakan daftar berita terbaru di bawah.">
<meta name="robots" content="noindex, follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Sudut Pandaan">
<meta property="og:title" content="Mengalihkan… — Sudut Pandaan">
<meta property="og:description" content="Halaman pengalihan ke artikel Sudut Pandaan.">
<meta property="og:image" content="{situs['base_url']}/assets/img/og-default.jpg">
<link rel="icon" href="../assets/img/favicon/favicon.ico" sizes="any">
<link rel="canonical" href="{situs['base_url']}/berita/">
<link rel="stylesheet" href="../assets/css/fonts.css">
<link rel="stylesheet" href="../assets/css/style.css">
<script>
  // Daftar slug valid dari build terakhir (nihil permintaan jaringan).
  var SP_SLUG = {json.dumps(slug_dikenal, ensure_ascii=False)};
</script>
</head>
<body class="sp-halaman-jembatan">
<main class="container py-5" style="max-width:640px">
  <p class="text-muted-2 small mb-1">Sudut Pandaan</p>
  <div id="jembatan" class="card border-0 shadow-sm rounded-card p-4">
    <p class="mb-2"><i class="ph ph-clock-counter-clockwise me-1" aria-hidden="true"></i>Mengalihkan ke artikel…</p>
    <p class="small text-muted-2 mb-0">Bila tidak berpindah otomatis, pilih dari daftar di bawah.</p>
  </div>

  <h1 class="h5 mt-4" id="judulJembatan">Daftar berita terbaru</h1>
  <ul class="jembatan-daftar">
    {daftar_tautan}
  </ul>
  <p class="small"><a href="index.html">Lihat semua berita Pandaan</a> · <a href="{base}index.html">Beranda</a></p>
</main>
<script>
  (function () {{
    var p = new URLSearchParams(location.search);
    var bersih = (p.get('slug') || '').toLowerCase().replace(/[^a-z0-9-]/g, '');
    var kotak = document.getElementById('jembatan');
    var judul = document.getElementById('judulJembatan');
    if (!bersih) {{ location.replace('index.html'); return; }}
    if (SP_SLUG.indexOf(bersih) >= 0) {{ location.replace(bersih + '.html'); return; }}
    // Slug tidak dikenal: jangan diam-diam 404 — beri penjelasan dan jalan keluar.
    kotak.innerHTML = '<p class="mb-2"><i class="ph ph-warning-circle me-1 text-danger" aria-hidden="true"></i>' +
      '<strong>Artikel tidak ditemukan</strong></p>' +
      '<p class="small text-muted-2 mb-0">Tautan <code>?slug=' + bersih.replace(/[<>]/g, '') +
      '</code> tidak ada di arsip kami. Artikel mungkin sudah diganti judulnya atau dipindahkan.</p>';
    kotak.classList.add('border-danger');
    judul.textContent = 'Coba salah satu berita berikut';
    document.title = 'Artikel tidak ditemukan — Sudut Pandaan';
  }})();
</script>
</body></html>
"""
    html = beri_versi_aset(html)      # ?v=… pada CSS → cache lama terlewati
    with open(os.path.join(BASE_DIR, "berita", "detail.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.join("berita", "detail.html")


def build_sitemap(situs):
    urls = [
        ("/", "1.0", "daily"), ("/berita/", "0.9", "hourly"), ("/wisata/", "0.9", "weekly"),
        ("/kuliner/", "0.9", "weekly"), ("/umkm/", "0.8", "weekly"), ("/peta", "0.7", "monthly"),
        ("/panduan/", "0.8", "weekly"), ("/layanan/lalu-lintas", "0.8", "hourly"),
        ("/layanan/agenda", "0.7", "daily"), ("/layanan/loker", "0.7", "daily"),
        ("/layanan/nomor-penting", "0.6", "monthly"), ("/layanan/lapor", "0.5", "monthly"),
        ("/umkm/daftar", "0.5", "monthly"), ("/tentang", "0.6", "monthly"), ("/redaksi", "0.5", "monthly"),
        ("/pasang-iklan", "0.6", "monthly"), ("/kontak", "0.5", "yearly"), ("/link/", "0.4", "monthly"),
        ("/privasi", "0.3", "yearly"), ("/disclaimer", "0.3", "yearly"), ("/syarat-ketentuan", "0.3", "yearly"),
    ]
    entries = ""
    for path, prio, freq in urls:
        entries += (f"  <url><loc>{situs['base_url']}{path}</loc>"
                    f"<lastmod>2026-10-16</lastmod><changefreq>{freq}</changefreq>"
                    f"<priority>{prio}</priority></url>\n")
    for b in BERITA:
        entries += (f"  <url><loc>{situs['base_url']}/berita/{b['slug']}</loc>"
                    f"<lastmod>{(b.get('diperbarui') or b['tanggal'])[:10]}</lastmod>"
                    f"<changefreq>weekly</changefreq><priority>0.8</priority></url>\n")
    for w in WISATA:
        entries += (f"  <url><loc>{situs['base_url']}/wisata/{w['slug']}</loc>"
                    f"<lastmod>{w['terakhir_diverifikasi']}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>\n")
    for k in KULINER:
        entries += (f"  <url><loc>{situs['base_url']}/kuliner/{k['slug']}</loc>"
                    f"<lastmod>{k['terakhir_diverifikasi']}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>\n")
    for u in UMKM:
        entries += (f"  <url><loc>{situs['base_url']}/umkm/{u['slug']}</loc>"
                    f"<lastmod>2026-10-16</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>\n")
    for p in PANDUAN:
        entries += (f"  <url><loc>{situs['base_url']}/panduan/{p['slug']}</loc>"
                    f"<lastmod>{p['tanggal'][:10]}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>\n")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + entries + "</urlset>\n")
    with open(os.path.join(BASE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)

    robots = f"""# robots.txt — Sudut Pandaan
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /assets/data/
Disallow: /berita/detail.html

Sitemap: {situs['base_url']}/sitemap.xml
"""
    with open(os.path.join(BASE_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots)
    return "sitemap.xml", "robots.txt"


def build_data_embed():
    """Salinan data JSON sebagai JS, supaya situs tetap berfungsi saat dibuka
    langsung dari berkas (file://) atau offline. Bila dihosting, JS tetap
    memakai fetch ke assets/data/*.json sebagai sumber utama."""
    payload = {}
    for name in ["situs", "desa", "kategori", "penulis", "berita", "wisata", "kuliner",
                 "umkm", "agenda", "loker", "lalu-lintas", "nomor-penting", "sosmed", "panduan"]:
        payload[name] = load(name + ".json")
    js = ("/* Dibuat otomatis oleh tools/build.py — jangan diedit manual.\n"
          "   Ubah assets/data/*.json lalu jalankan ulang: python3 tools/build.py */\n"
          "window.SP_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    path = os.path.join(BASE_DIR, "assets", "js", "data-embed.js")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(js)
    return "assets/js/data-embed.js"


def build_manifest(situs):
    manifest = {
        "name": "Sudut Pandaan — Mata Komunitas Pandaan",
        "short_name": "SudutPandaan",
        "description": situs["deskripsi"],
        "start_url": "/index.html",
        "scope": "/",
        "display": "standalone",
        "background_color": "#F6F1E7",
        "theme_color": "#071C53",
        "lang": "id-ID",
        "icons": [
            {"src": "/assets/img/favicon/favicon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/assets/img/favicon/favicon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    with open(os.path.join(BASE_DIR, "site.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return "site.webmanifest"


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
BREAKING_HTML = ""
# Nomor seksi "majalah": dipakai konsisten di beranda, kepala halaman, dan footer
NOMOR_JENIS = {"wisata": "01", "kuliner": "02", "umkm": "03"}

KATEGORI = []
BERITA = []
WISATA = []
KULINER = []
UMKM = []
PANDUAN = []
PENULIS = []
DESA = []
LALIN_TEMPLATE = ""
SITUS = {}


def main():
    global BREAKING_HTML, KATEGORI, BERITA, WISATA, KULINER, UMKM, PANDUAN, PENULIS, DESA, LALIN_TEMPLATE, SITUS

    created = sync_json()
    SITUS = load("situs.json")
    KATEGORI = load("kategori.json")
    PENULIS = load("penulis.json")
    DESA = load("desa.json")
    BERITA = load("berita.json")
    WISATA = load("wisata.json")
    KULINER = load("kuliner.json")
    UMKM = load("umkm.json")
    PANDUAN = load("panduan.json")
    LALIN_TEMPLATE = load("lalu-lintas.json")["catatan_template"]
    situs = SITUS

    # Breaking bar: ambil 1 berita bertanda breaking yang masih berlaku
    now = datetime.now(WIB)
    aktif = [b for b in BERITA if b.get("breaking") and (not b.get("breaking_until") or parse_iso(b["breaking_until"]) > now)]
    BREAKING_HTML = breaking_bar("", aktif).replace("{base}", "") if aktif else ""
    # (base diganti per halaman di dalam page())
    BREAKING_HTML = BREAKING_HTML.replace('href="berita/', 'href="{base}berita/')

    # data-embed.js ditulis lebih dulu: halaman memakai hash isinya untuk ?v=…
    # Bila ditulis paling akhir, versi yang tertanam tertinggal satu build.
    build_data_embed()

    results = []
    # --- halaman tingkat 1 (root) ---
    b0 = ""
    results.append(build_home(b0, situs))
    results.append(build_berita_index("../", situs))
    for b in BERITA:
        results.append(build_berita_detail(b, "../", situs))
    for w in WISATA:
        results.append(build_wisata_detail(w, "../", situs))
    for k in KULINER:
        results.append(build_kuliner_detail(k, "../", situs))
    for u in UMKM:
        results.append(build_umkm_detail(u, "../", situs))
    for p in PANDUAN:
        results.append(build_panduan_detail(p, "../", situs))
    results.append(build_direktori_index("wisata", "../", situs))
    results.append(build_direktori_index("kuliner", "../", situs))
    results.append(build_direktori_index("umkm", "../", situs))
    results.append(build_panduan_index("../", situs))
    results.append(build_lalu_lintas("../", situs))
    results.append(build_agenda("../", situs))
    results.append(build_loker("../", situs))
    results.append(build_nomor_penting("../", situs))
    results.append(build_lapor("../", situs))
    results.append(build_umkm_daftar("../", situs))
    results.append(build_peta(b0, situs))
    results.append(build_tentang(b0, situs))
    results.append(build_redaksi(b0, situs))
    results.append(build_pasang_iklan(b0, situs))
    results.append(build_kontak(b0, situs))
    results.extend(build_legal(b0, situs))
    results.append(build_404(b0, situs))
    results.append(build_link_bio("../", situs))
    results.append(build_berita_detail_redirect(b0, situs))
    results.append(build_sitemap(situs))
    results.append(build_manifest(situs))

    print(f"✅ Selesai. {len(results)} berkas ditulis.")
    if created:
        print("   JSON baru dibuat dari seed: " + ", ".join(created))
    else:
        print("   JSON sudah ada — dibaca dari assets/data/ (sumber utama).")
    print(f"   Total berita: {len(BERITA)} · wisata: {len(WISATA)} · kuliner: {len(KULINER)} · UMKM: {len(UMKM)} · panduan: {len(PANDUAN)}")
    if "--prerender" in sys.argv:
        # Isi kontainer JS dengan HTML jadi (SEO + pengguna tanpa JS).
        print("   Prerender: mengisi kontainer lewat Chromium…")
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "tools", "prerender.py")], check=False)
    else:
        print("   (opsional) tambahkan --prerender agar kontainer JS juga diisi HTML jadi")
    print("   Jalankan pratinjau:  python3 -m preview_server.py 8090   (dari folder tools/)" if False else
          "   Jalankan pratinjau:  python3 tools/preview_server.py 8090")


if __name__ == "__main__":
    main()



