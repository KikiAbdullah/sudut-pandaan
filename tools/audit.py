# -*- coding: utf-8 -*-
"""
Sudut Pandaan — tools/audit.py
Audit statis menyeluruh: HTML, tautan, gambar, ARIA, JSON-LD, ikon, sitemap,
manifest, data JSON, dan rujukan aset CSS/JS.

Jalankan:  cd sudutpandaan && python3 tools/audit.py
Keluaran: daftar temuan bergaya "BERKAS: pesan" + ringkasan. Kode keluar 1 bila
ada temuan (cocok untuk CI). Tanpa dependensi luar (hanya pustaka standar).
"""

import json
import os
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMUAN = []


def temuan(berkas, pesan, kategori="umum"):
    TEMUAN.append((kategori, berkas, pesan))


# ---------------------------------------------------------------------------
# Pengumpul tag HTML sederhana
# ---------------------------------------------------------------------------
class Kumpul(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tag = []            # (nama, dict-atribut, teks-awal)
        self.ids = defaultdict(int)
        self.judul = []
        self._tumpuk = []        # (nama, teks)

    # -- util --
    def handle_starttag(self, nama, atribut):
        d = dict(atribut)
        self.tag.append((nama, d, ""))
        if d.get("id"):
            self.ids[d["id"]] += 1
        if nama in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._tumpuk.append([nama, ""])

    def handle_startendtag(self, nama, atribut):
        self.handle_starttag(nama, atribut)

    def handle_data(self, data):
        if self._tumpuk:
            self._tumpuk[-1][1] += data

    def handle_endtag(self, nama):
        if self._tumpuk and self._tumpuk[-1][0] == nama:
            n, teks = self._tumpuk.pop()
            self.judul.append((n, re.sub(r"\s+", " ", teks).strip()))


def baca(berkas):
    with open(os.path.join(BASE_DIR, berkas), encoding="utf-8") as f:
        return f.read()


def halaman_semua():
    keluaran = []
    for akar, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in ("assets", "tools", "docs", ".git", "uploads", "__pycache__")]
        for f in files:
            if f.endswith(".html"):
                keluaran.append(os.path.relpath(os.path.join(akar, f), BASE_DIR).replace(os.sep, "/"))
    return sorted(keluaran)


# ---------------------------------------------------------------------------
# Ikon Phosphor: hanya kelas yang ADA di subset yang boleh dipakai
# ---------------------------------------------------------------------------
def kelas_ikon_tersedia():
    css = baca("assets/vendor/phosphor/phosphor.css")
    return set(re.findall(r"\.(ph-[a-z0-9-]+):before", css))


def periksa_ikon(teks, sumber, tersedia):
    dipakai = set(re.findall(r"ph(?:-fill)?\s+(ph-[a-z0-9-]+)", teks))
    dipakai |= set(re.findall(r"\bikon:\s*['\"]([a-z0-9-]+)['\"]", teks))
    for k in sorted(dipakai):
        nama = k if k.startswith("ph-") else "ph-" + k
        if nama not in tersedia:
            temuan(sumber, "ikon Phosphor di luar subset: %s" % nama, "ikon")


# ---------------------------------------------------------------------------
# Pemeriksaan per halaman
# ---------------------------------------------------------------------------
def periksa_halaman(berkas, ikon, situs):
    html = baca(berkas)
    kumpul = Kumpul()
    kumpul.feed(html)
    tag = kumpul.tag
    folder = os.path.dirname(berkas)

    # 1. id ganda
    for i, n in kumpul.ids.items():
        if n > 1:
            temuan(berkas, "id ganda: #%s (%d×)" % (i, n), "html")

    # 2. h1 & urutan judul
    hs = [(n, t) for n, t in kumpul.judul if t]
    h1 = [t for n, t in hs if n == "h1"]
    if len(h1) != 1:
        temuan(berkas, "jumlah <h1> = %d (harus 1)" % len(h1), "seo")
    urut = [int(n[1]) for n, t in hs]
    for a, b in zip(urut, urut[1:]):
        if b > a + 1:
            temuan(berkas, "lompatan judul h%d → h%d" % (a, b), "a11y")

    # 3. <head>: title/description/canonical/og
    if "<title>" not in html:
        temuan(berkas, "tanpa <title>", "seo")
    if 'name="description"' not in html:
        temuan(berkas, "tanpa meta description", "seo")
    cam = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    if not cam:
        temuan(berkas, "tanpa rel=canonical", "seo")
    else:
        harap = situs["base_url"].rstrip("/") + "/" + (folder + "/" if folder and folder != "." else "")
        if not cam.group(1).startswith(harap):
            temuan(berkas, "canonical tidak sesuai folder: %s" % cam.group(1), "seo")
    if 'property="og:image"' not in html:
        temuan(berkas, "tanpa og:image", "seo")

    # 4. ikon
    periksa_ikon(html, berkas, ikon)

    # 5. gambar
    for nama, d, _ in tag:
        if nama != "img":
            continue
        src = d.get("src", "")
        if not src:
            temuan(berkas, "<img> tanpa src", "gambar")
            continue
        if "alt" not in d:
            temuan(berkas, "<img> tanpa alt: %s" % src[:70], "a11y")
        if not d.get("width") or not d.get("height"):
            temuan(berkas, "<img> tanpa width/height: %s" % src[:70], "cls")
        if not re.match(r"^(https?:)?//|^data:", src):
            jalur = os.path.normpath(os.path.join(folder, src.split("?")[0]))
            if not os.path.exists(os.path.join(BASE_DIR, jalur)):
                temuan(berkas, "gambar lokal tidak ada: %s" % src, "gambar")
        for kandidat in (d.get("srcset") or "").split(","):
            u = kandidat.strip().split(" ")[0]
            if not u or re.match(r"^(https?:)?//|^data:", u):
                continue
            jalur = os.path.normpath(os.path.join(folder, u.split("?")[0]))
            if not os.path.exists(os.path.join(BASE_DIR, jalur)):
                temuan(berkas, "candidate srcset tidak ada: %s" % u, "gambar")

    # 6. tautan internal & anchor
    id_semua = set(kumpul.ids)
    for nama, d, _ in tag:
        if nama != "a":
            continue
        href = (d.get("href") or "").strip()
        if not href or href == "#":
            temuan(berkas, "tautan href kosong/# : %s" % href, "tautan")
            continue
        if re.match(r"^(https?:|mailto:|tel:|whatsapp:|data:)", href):
            if href.startswith("http") and d.get("target") == "_blank":
                rel = d.get("rel", "")
                if "noopener" not in rel or "noreferrer" not in rel:
                    temuan(berkas, "target=_blank tanpa rel noopener noreferrer: %s" % href[:60], "a11y")
            continue
        if href.startswith("#"):
            if href[1:] not in id_semua:
                temuan(berkas, "anchor tidak ditemukan: %s" % href, "tautan")
            continue
        bersih = href.split("#")[0].split("?")[0]
        frag = href.split("#")[1] if "#" in href else ""
        if not bersih:
            continue
        tujuan = os.path.normpath(os.path.join(folder, bersih))
        if bersih.endswith("/"):
            tujuan = os.path.join(tujuan, "index.html")
        if not os.path.exists(os.path.join(BASE_DIR, tujuan)):
            # rute tanpa ekstensi (mis. "berita") → coba index.html / .html
            alternatif = [tujuan + ".html", os.path.join(tujuan, "index.html")]
            if not any(os.path.exists(os.path.join(BASE_DIR, a)) for a in alternatif):
                temuan(berkas, "tautan internal mati: %s" % href, "tautan")
                continue
            tujuan = next(a for a in alternatif if os.path.exists(os.path.join(BASE_DIR, a)))
        if frag:
            htm = baca(tujuan)
            if ('id="%s"' % frag) not in htm:
                temuan(berkas, "anchor '%s' tidak ada di %s" % (frag, tujuan), "tautan")

    # 7. form: setiap kendali punya label
    label_for = {d.get("for") for n, d, _ in tag if n == "label" and d.get("for")}
    for nama, d, _ in tag:
        if nama not in ("input", "select", "textarea"):
            continue
        tipe = d.get("type", "text")
        if tipe in ("hidden", "submit", "button", "reset", "checkbox", "radio"):
            if tipe in ("checkbox", "radio") and d.get("id") not in label_for and not d.get("aria-label"):
                # boleh dibungkus <label> — dicek kasar lewat teks halaman
                if ('for="%s"' % d.get("id")) not in html:
                    temuan(berkas, "kendali tanpa label: id=%s" % d.get("id"), "a11y")
            continue
        if (d.get("id") in label_for or d.get("aria-label") or d.get("aria-labelledby")
                or d.get("aria-hidden") == "true"):   # mis. honeypot anti-spam (tabindex=-1)
            continue
        temuan(berkas, "kendali tanpa label: %s id=%s" % (nama, d.get("id") or d.get("name")), "a11y")

    # 8. rujukan ARIA
    for nama, d, _ in tag:
        for attr in ("aria-labelledby", "aria-describedby", "aria-controls"):
            for ref in (d.get(attr) or "").split():
                if ref and ref not in id_semua:
                    temuan(berkas, "%s -> #%s tidak ada" % (attr, ref), "a11y")

    # 9. tombol tanpa nama aksesibel (teks kosong & tanpa aria-label/title)
    for blok in re.findall(r"<button\b([^>]*)>(.*?)</button>", html, re.S):
        atribut, isi = blok
        if "aria-label=" in atribut or "title=" in atribut:
            continue
        teks = re.sub(r"<[^>]+>", " ", isi)
        teks = re.sub(r"&[a-z]+;|&#\d+;", " ", teks)
        if not teks.strip():
            temuan(berkas, "tombol tanpa nama aksesibel: <button%s>" % atribut[:80], "a11y")

    # 10. JSON-LD
    for blok in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            json.loads(blok)
        except Exception as e:  # noqa: BLE001
            temuan(berkas, "JSON-LD tidak valid: %s" % str(e)[:80], "seo")

    # 11. sisa skeleton (harus kosong di halaman yang datanya statis)
    if "sp-skeleton" in html and berkas not in ("index.html",):
        jumlah = html.count("sp-skeleton")
        temuan(berkas, "sisa skeleton: %d (cek apakah kontainer terisi JS)" % jumlah, "info")

    # 12. handler inline
    for ev in re.findall(r"\son(click|submit|change|load)=", html):
        temuan(berkas, "atribut event inline: on%s" % ev, "kualitas")

    return kumpul


# ---------------------------------------------------------------------------
# Pemeriksaan lintas berkas
# ---------------------------------------------------------------------------
def periksa_sitemap(pages, situs):
    if not os.path.exists(os.path.join(BASE_DIR, "sitemap.xml")):
        temuan("sitemap.xml", "tidak ada", "seo")
        return
    xml = baca("sitemap.xml")
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    for loc in locs:
        if not loc.startswith(situs["base_url"]):
            temuan("sitemap.xml", "URL di luar base_url: %s" % loc, "seo")
            continue
        jalur = loc[len(situs["base_url"]):].strip("/")
        pilihan = []
        if jalur in ("", "/"):
            pilihan = ["index.html"]
        else:
            pilihan = [jalur + ".html", jalur + "/index.html", jalur]
        if not any(os.path.exists(os.path.join(BASE_DIR, k)) for k in pilihan):
            temuan("sitemap.xml", "menunjuk berkas tidak ada: %s" % loc, "seo")
    lok = {l.rstrip("/") for l in locs}
    for p in pages:
        if p.endswith("404.html"):
            continue
        if 'name="robots" content="noindex' in baca(p):   # jembatan/halaman noindex
            continue
        bentu = p[:-5] if p.endswith(".html") else p          # buang .html
        if bentu.endswith("index"):
            bentu = bentu[:-5]                                # berita/index → berita/
        url = situs["base_url"] + "/" + bentu
        if url.rstrip("/") not in lok and url not in lok:
            temuan("sitemap.xml", "halaman tidak terdaftar: %s" % p, "seo")
    if "error" in xml or "semua</error" in xml:
        temuan("sitemap.xml", "format mencurigakan", "seo")


def periksa_manifest():
    jalur = os.path.join(BASE_DIR, "site.webmanifest")
    if not os.path.exists(jalur):
        temuan("site.webmanifest", "tidak ada", "pwa")
        return
    m = json.loads(baca("site.webmanifest"))
    for k in ("name", "short_name", "start_url", "display", "icons"):
        if k not in m:
            temuan("site.webmanifest", "kunci hilang: %s" % k, "pwa")
    for ikon in m.get("icons", []):
        p = ikon["src"].lstrip("/")
        if not os.path.exists(os.path.join(BASE_DIR, p)):
            temuan("site.webmanifest", "ikon tidak ada: %s" % ikon["src"], "pwa")
    # warna harus sesuai palet sekarang (navy/krem), bukan sisa palet lama
    if m.get("theme_color", "").upper() not in ("#071C53", "#020B22"):
        temuan("site.webmanifest", "theme_color bukan palet navy: %s" % m.get("theme_color"), "pwa")
    if m.get("background_color", "").upper() in ("#FAFBF9", "#FFFFFF"):
        temuan("site.webmanifest", "background_color masih putih lama: %s" % m.get("background_color"), "pwa")


def periksa_css():
    for berkas in ("assets/css/style.css", "assets/css/fonts.css", "assets/vendor/phosphor/phosphor.css"):
        css = baca(berkas)
        for u in re.findall(r"url\((['\"]?)([^)'\"]+)\1\)", css):
            alamat = u[1]
            if re.match(r"^(https?:|data:)", alamat):
                continue
            jalur = os.path.normpath(os.path.join(os.path.dirname(berkas), alamat.split("?")[0].split("#")[0]))
            if not os.path.exists(os.path.join(BASE_DIR, jalur)):
                temuan(berkas, "url() tidak ada: %s" % alamat, "aset")
        if berkas.endswith("style.css") and css.count("{") != css.count("}"):
            temuan(berkas, "kurung tidak seimbang: %d buka / %d tutup" % (css.count("{"), css.count("}")), "css")


def periksa_js():
    js = {}
    for f in os.listdir(os.path.join(BASE_DIR, "assets/js")):
        if f.endswith(".js"):
            js[f] = baca("assets/js/" + f)
    semua_id_html = set()
    for p in halaman_semua():
        htm = baca(p)
        semua_id_html |= set(re.findall(r'id="([^"]+)"', htm))
    for nama, isi in js.items():
        for i in sorted(set(re.findall(r"qs\(['\"]#([A-Za-z0-9_-]+)['\"]\)", isi))):
            if i not in semua_id_html:
                temuan("assets/js/" + nama, "qs('#%s') tidak ada di HTML mana pun" % i, "js")
        for i in sorted(set(re.findall(r"UI\.isi\(['\"]#([A-Za-z0-9_-]+)['\"]", isi))):
            if i not in semua_id_html:
                temuan("assets/js/" + nama, "UI.isi('#%s') tidak ada di HTML mana pun" % i, "js")
    # sintaks JS
    for nama, isi in js.items():
        if isi.count("{") != isi.count("}"):
            temuan("assets/js/" + nama, "kurung tidak seimbang", "js")


def periksa_data(pages):
    data = {}
    for f in sorted(os.listdir(os.path.join(BASE_DIR, "assets", "data"))):
        if not f.endswith(".json"):
            continue
        try:
            data[f] = json.loads(baca("assets/data/" + f))
        except Exception as e:  # noqa: BLE001
            temuan("assets/data/" + f, "JSON tidak valid: %s" % e, "data")
    # slug unik + halaman detail ada
    for nama, kunci, prefiks in (("berita.json", "slug", "berita/"), ("wisata.json", "slug", "wisata/"),
                                 ("kuliner.json", "slug", "kuliner/"), ("umkm.json", "slug", "umkm/")):
        if nama not in data:
            continue
        daftar = data[nama] if isinstance(data[nama], list) else data[nama].get("items", [])
        slug = [d.get(kunci) for d in daftar]
        if len(slug) != len(set(slug)):
            temuan("assets/data/" + nama, "slug ganda", "data")
        for s in slug:
            if s and ("%s%s.html" % (prefiks, s)) not in pages:
                temuan("assets/data/" + nama, "halaman detail hilang untuk slug %s" % s, "data")
    # gambar lokal pada data harus ada
    for nama, isi in data.items():
        teks = json.dumps(isi, ensure_ascii=False)
        for g in set(re.findall(r"[\"'](/assets/img/[^\"']+)[\"']", teks)):
            if not os.path.exists(os.path.join(BASE_DIR, g.lstrip("/"))):
                temuan("assets/data/" + nama, "gambar tidak ada: %s" % g, "data")


def periksa_berkas_server():
    for berkas, syarat in (("robots.txt", "sitemap"), ("_headers", None), ("_redirects", None), (".htaccess", None)):
        if not os.path.exists(os.path.join(BASE_DIR, berkas)):
            temuan(berkas, "tidak ada", "deploy")
    if os.path.exists(os.path.join(BASE_DIR, "robots.txt")):
        if "sitemap" not in baca("robots.txt").lower():
            temuan("robots.txt", "tanpa rujukan sitemap", "seo")
    if os.path.exists(os.path.join(BASE_DIR, "_redirects")):
        for baris in baca("_redirects").splitlines():
            if not baris.strip() or baris.startswith("#"):
                continue
            bagian = baris.split()
            if ":" in baris:      # pola rewrite Cloudflare (mis. /berita/:slug)
                continue
            if len(bagian) >= 2 and bagian[1].endswith(".html"):
                p = bagian[1].lstrip("/")
                if not os.path.exists(os.path.join(BASE_DIR, p)):
                    temuan("_redirects", "tujuan tidak ada: %s" % baris, "deploy")


def main():
    pages = halaman_semua()
    situs = json.loads(baca("assets/data/situs.json"))
    ikon = kelas_ikon_tersedia()
    print("  Ikon tersedia di subset: %d" % len(ikon))
    print("  Halaman diperiksa: %d" % len(pages))
    for p in pages:
        periksa_halaman(p, ikon, situs)
    periksa_sitemap(pages, situs)
    periksa_manifest()
    periksa_css()
    periksa_js()
    periksa_data(pages)
    periksa_berkas_server()

    # ---- ringkasan ----
    per_kategori = defaultdict(list)
    for k, b, p in TEMUAN:
        per_kategori[k].append((b, p))
    print("\n  ── Temuan per kategori ──")
    for k in sorted(per_kategori, key=lambda x: -len(per_kategori[x])):
        print("   %-10s %d" % (k, len(per_kategori[k])))
    print("\n  ── Rincian ──")
    for k in sorted(per_kategori):
        for b, p in per_kategori[k][:60]:
            print("   [%s] %s: %s" % (k, b, p))
        if len(per_kategori[k]) > 60:
            print("   [%s] … %d temuan lain" % (k, len(per_kategori[k]) - 60))
    print("\n  Total temuan: %d" % len(TEMUAN))
    return 1 if TEMUAN else 0


if __name__ == "__main__":
    sys.exit(main())
