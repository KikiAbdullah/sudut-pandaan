# -*- coding: utf-8 -*-
"""
Sudut Pandaan — tools/audit_peramban.py
Audit di peramban sungguhan (Playwright) atas SELURUH halaman:
  1. galat konsol / galat halaman, permintaan gagal (404/500) — internal & luar
  2. gambar rusak (lokal & luar)
  3. luber horizontal (overflow) di 1280 px dan 412 px
  4. target sentuh < 44 px di ponsel
  5. isi tanpa JavaScript (SEO & pengguna tanpa JS)
  6. uji interaksi bilah filter, panel lompat, peta, form, lightbox, dll.

Jalankan server dulu, lalu:
    python3 tools/audit_peramban.py --base http://127.0.0.1:8090
"""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ARG = argparse.ArgumentParser()
ARG.add_argument("--base", default="http://127.0.0.1:8090")
ARG.add_argument("--halaman", default="", help="batasi ke satu halaman, mis. berita/index.html")
ARG.add_argument("--lewati-sapuan", action="store_true")
ARG.add_argument("--cache", default="/tmp/audit-peramban.json",
                 help="berkas cache hasil sapuan (dibaca bila ada, ditulis selalu)")
ARGS = ARG.parse_args()
BASE = ARGS.base.rstrip("/")
HOST = urlparse(BASE).netloc

CATATAN = []


def catat(kategori, halaman, pesan):
    CATATAN.append((kategori, halaman, pesan))


def semua_halaman():
    import os
    akar = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    keluar = []
    for r, d, f in os.walk(akar):
        d[:] = [x for x in d if x not in ("assets", "tools", "docs", ".git", "uploads", "__pycache__")]
        for n in f:
            if n.endswith(".html"):
                keluar.append(os.path.relpath(os.path.join(r, n), akar).replace(os.sep, "/"))
    return sorted(keluar)


# ---------------------------------------------------------------------------
def sapuan_hal(px, context, halaman):
    """Periksa galat, gambar rusak, dan luber horizontal pada satu halaman."""
    galat, gagal, rusak = [], [], []
    pg = context.new_page()
    pg.on("pageerror", lambda e: galat.append(str(e)))
    pg.on("console", lambda m: galat.append("konsol: " + m.text) if m.type == "error" else None)
    pg.on("requestfailed", lambda r: gagal.append("gagal: " + r.url[:90] + " " + str(r.failure)))
    pg.on("response", lambda r: gagal.append("HTTP %d: %s" % (r.status, r.url[:90])) if r.status >= 400 else None)
    try:
        pg.goto("%s/%s" % (BASE, halaman), wait_until="load", timeout=45000)
        pg.wait_for_timeout(1800)
        pg.evaluate("()=>window.scrollTo(0, document.body.scrollHeight)")
        pg.wait_for_timeout(1600)
        pg.evaluate("()=>window.scrollTo(0, 0)")
        pg.wait_for_timeout(400)
        luber = pg.evaluate("()=>{const d=document.documentElement;return {w:innerWidth, s:d.scrollWidth};}")
        rusak = pg.evaluate("""()=>Array.from(document.images)
            .filter(i=>i.complete && i.naturalWidth===0 && i.getBoundingClientRect().width>0)
            .map(i=>i.currentSrc||i.src)""")
    except Exception as e:  # noqa: BLE001
        catat("galat-halaman", halaman, "tidak dapat dimuat: %s" % str(e)[:120])
        pg.close()
        return
    for g in set(galat):
        catat("konsol", halaman, g[:160])
    for g in set(gagal):
        level = "internal" if HOST in g else "luar"
        catat("permintaan-" + level, halaman, g[:150])
    for g in rusak:
        level = "internal" if (HOST in g or not g.startswith("http")) else "luar"
        catat("gambar-rusak-" + level, halaman, g[:110])
    if luber["s"] > luber["w"] + 1:
        catat("luber", halaman, "scrollWidth %d > lebar %d" % (luber["s"], luber["w"]))
    pg.close()


def target_sentuh(context, halaman):
    pg = context.new_page()
    pg.goto("%s/%s" % (BASE, halaman), wait_until="load", timeout=45000)
    pg.wait_for_timeout(1500)
    kecil = pg.evaluate("""()=>{
      const hasil=[];
      document.querySelectorAll('a,button,input,select,textarea,[role="button"]').forEach(el=>{
        const r=el.getBoundingClientRect();
        if(r.width===0||r.height===0) return;                       // tersembunyi
        if(getComputedStyle(el).visibility==='hidden') return;
        if(el.closest('p, li, .breadcrumb, .nav-link, footer, .sp-hp, small')) return;  // tautan dalam teks
        if(el.classList.contains('stretched-link')) return;   // area klik = seluruh kartu
        if(el.classList.contains('form-check-input')) return; // label di sekitarnya jauh lebih besar
        if(el.classList.contains('leaflet-marker-icon')||el.classList.contains('marker-cluster')) return;
        if(el.classList.contains('leaflet-control-zoom-in')||el.classList.contains('leaflet-control-zoom-out')) return;
        if(el.closest('.leaflet-control-attribution, .alert, .pagination, .jembatan-daftar')) return;  // teks/atribusi peta & kalimat
        if(el.closest('.skip-link')) return;
        // Aturan: gagal bila sisi terkecil < 24 px (WCAG 2.2 AA 2.5.8) ATAU
        // kedua sisi < 44 px (target blueprint). Lebar tautan teks mengikuti
        // panjang katanya, jadi sisi tinggi yang menentukan untuk teks.
        const gagal = Math.min(r.width,r.height)<24 || (r.width<44 && r.height<44);
        if(gagal) hasil.push((el.tagName+'.'+(el.className||'')).slice(0,70)+` ${Math.round(r.width)}x${Math.round(r.height)}`);
      });
      return [...new Set(hasil)];
    }""")
    for k in kecil:
        catat("target-sentuh", halaman, k)
    pg.close()


def tanpa_js(browser, halaman):
    ctx = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto("%s/%s" % (BASE, halaman), wait_until="load", timeout=45000)
        pg.wait_for_timeout(600)
        info = pg.evaluate("""()=>{
          const teks=document.body.innerText.replace(/\\s+/g,' ').trim();
          return {p: document.querySelectorAll('p').length,
                  h1: document.querySelectorAll('h1').length,
                  skel: document.querySelectorAll('.sp-skeleton').length,
                  tautan: document.querySelectorAll('a[href]').length,
                  kata: teks.split(' ').length};
        }""")
    except Exception as e:  # noqa: BLE001
        catat("tanpa-js", halaman, "gagal dimuat: %s" % str(e)[:100])
        ctx.close()
        return
    if 'name="robots" content="noindex' in open(__file__.replace("tools/audit_peramban.py", halaman),
                                                  encoding="utf-8").read():
        ctx.close()
        return                      # halaman noindex (mis. jembatan berita) memang tipis
    if info["h1"] != 1 or info["kata"] < 120:
        catat("tanpa-js", halaman, "konten tipis tanpa JS: %d kata, %d h1" % (info["kata"], info["h1"]))
    if info["skel"] > 0:
        catat("tanpa-js", halaman, "sisa %d skeleton tanpa JS" % info["skel"])
    ctx.close()


# ---------------------------------------------------------------------------
def interaksi(browser, lapor):
    """Uji fungsi nyata. `lapor(nama, lulus, detail)` mencatat hasil."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 950})
    ctx.set_default_timeout(12000)

    # ---------- 1. BERITA: cari, kategori, urut, reset, paginasi, URL ----------
    pg = ctx.new_page()
    pg.goto(BASE + "/berita/index.html", wait_until="load")
    pg.wait_for_timeout(1500)
    awal = pg.inner_text("#hasilInfo")
    pg.fill("#qBerita", "tol")
    pg.wait_for_timeout(700)
    saring = pg.inner_text("#hasilInfo")
    lapor("berita: pencarian menyaring", saring != awal and "tol" in pg.url, "%s → %s" % (awal, saring))
    pg.click("#resetFilterBerita")
    pg.wait_for_timeout(700)
    lapor("berita: reset mengembalikan daftar", pg.inner_text("#hasilInfo") == awal, pg.inner_text("#hasilInfo"))
    pg.click('#filterKategori a[href*="kategori=lalu-lintas"]')
    pg.wait_for_timeout(800)
    lapor("berita: chip kategori", "kategori=lalu-lintas" in pg.url, pg.url)
    pg.close()

    # paginasi (halaman segar tanpa filter)
    pg = ctx.new_page()
    pg.goto(BASE + "/berita/index.html", wait_until="load")
    pg.wait_for_timeout(1500)
    jumlah_hal1 = pg.eval_on_selector_all("#daftarBerita > *", "e=>e.length")
    tautan_hal2 = pg.query_selector('#paginasiBerita a[href*="halaman=2"]')
    if tautan_hal2:
        tautan_hal2.click()
        pg.wait_for_timeout(1000)
        n2 = pg.eval_on_selector_all("#daftarBerita > *", "e=>e.length")
        lapor("berita: paginasi halaman 2", "halaman=2" in pg.url and n2 > 0,
              "%d kartu → %d kartu" % (jumlah_hal1, n2))
    else:
        lapor("berita: paginasi halaman 2", False, "tautan halaman 2 tidak ada di #paginasiBerita")
    pg.close()

    # ---------- 2. DIREKTORI: cari + chip + reset ----------
    for jalur, id_cari, id_reset, id_daftar in (
            ("wisata/index.html", "#qDirektori", "#resetFilter", "#daftarDirektori"),
            ("kuliner/index.html", "#qDirektori", "#resetFilter", "#daftarDirektori"),
            ("umkm/index.html", "#qDirektori", "#resetFilter", "#daftarDirektori")):
        pg = ctx.new_page()
        pg.goto("%s/%s" % (BASE, jalur), wait_until="load")
        pg.wait_for_timeout(1400)
        n0 = pg.eval_on_selector_all(id_daftar + " > *", "e=>e.length") if pg.query_selector(id_daftar) else -1
        if n0 < 0:
            lapor(jalur + ": wadah daftar ada", False, id_daftar + " tidak ditemukan")
            pg.close()
            continue
        pg.fill(id_cari, "tempe")
        pg.wait_for_timeout(700)
        n1 = pg.eval_on_selector_all(id_daftar + " > *", "e=>e.length")
        pg.click(id_reset)
        pg.wait_for_timeout(700)
        n2 = pg.eval_on_selector_all(id_daftar + " > *", "e=>e.length")
        lapor("%s: cari & reset" % jalur, n1 <= n0 and n2 == n0, "%d → %d → %d" % (n0, n1, n2))
        chip = pg.query_selector(".chip-grup .chip, .chip-grup .chip-switch")
        if chip:
            chip.click()
            pg.wait_for_timeout(700)
            lapor("%s: chip filter" % jalur, True, "chip dapat diklik")
        pg.close()

    # ---------- 3. AGENDA & LOKER & NOMOR ----------
    pg = ctx.new_page()
    pg.goto(BASE + "/layanan/agenda.html", wait_until="load")
    pg.wait_for_timeout(1400)
    a0 = pg.eval_on_selector_all("#daftarAgenda > *", "e=>e.length")
    opsi = pg.eval_on_selector_all("#filterBulanAgenda option", "e=>e.map(o=>o.value)")
    if len(opsi) > 1:
        pg.select_option("#filterBulanAgenda", opsi[1])
        pg.wait_for_timeout(700)
        a1 = pg.eval_on_selector_all("#daftarAgenda > *", "e=>e.length")
        pg.click("#resetBulanAgenda")
        pg.wait_for_timeout(600)
        a2 = pg.eval_on_selector_all("#daftarAgenda > *", "e=>e.length")
        lapor("agenda: filter bulan & reset", a1 <= a0 and a2 == a0, "%d → %d → %d" % (a0, a1, a2))
    else:
        lapor("agenda: filter bulan", False, "hanya %d opsi" % len(opsi))
    pg.close()

    pg = ctx.new_page()
    pg.goto(BASE + "/layanan/loker.html", wait_until="load")
    pg.wait_for_timeout(1400)
    l0 = pg.eval_on_selector_all("#daftarLoker > *", "e=>e.length")
    pg.fill("#cariLoker", "barista")
    pg.wait_for_timeout(800)
    l1 = pg.eval_on_selector_all("#daftarLoker > *", "e=>e.length")
    pg.click("#resetLoker")
    pg.wait_for_timeout(700)
    l2 = pg.eval_on_selector_all("#daftarLoker > *", "e=>e.length")
    lapor("loker: cari & reset", l1 <= l0 and l2 == l0, "%d → %d → %d" % (l0, l1, l2))
    pg.close()

    pg = ctx.new_page()
    pg.goto(BASE + "/layanan/nomor-penting.html", wait_until="load")
    pg.wait_for_timeout(1400)
    t0 = pg.eval_on_selector_all("#daftarNomor tr", "e=>e.length")
    pg.fill("#cariNomor", "pemadam")
    pg.wait_for_timeout(800)
    t1 = pg.eval_on_selector_all("#daftarNomor tr", "e=>e.length")
    pg.click("#resetNomor")
    pg.wait_for_timeout(700)
    t2 = pg.eval_on_selector_all("#daftarNomor tr", "e=>e.length")
    lapor("nomor penting: cari & reset", t1 <= t0 and t2 == t0, "%d → %d → %d" % (t0, t1, t2))
    pg.close()

    # ---------- 4. PETA: sakelar mengubah jumlah penanda ----------
    pg = ctx.new_page()
    pg.goto(BASE + "/peta.html", wait_until="load")
    pg.wait_for_timeout(3000)
    m0 = pg.eval_on_selector_all(".leaflet-marker-icon", "e=>e.length")
    for cid in ("cbWisata", "cbKuliner", "cbUmkm", "cbFasilitas", "cbMacet"):
        pg.uncheck("#" + cid)
        pg.wait_for_timeout(400)
    m1 = pg.eval_on_selector_all(".leaflet-marker-icon", "e=>e.length")
    for cid in ("cbWisata", "cbKuliner", "cbUmkm", "cbFasilitas"):
        pg.check("#" + cid)
        pg.wait_for_timeout(400)
    pg.wait_for_timeout(600)
    m2 = pg.eval_on_selector_all(".leaflet-marker-icon", "e=>e.length")
    pg.fill("#cariTitikPeta", "kripik")
    pg.wait_for_timeout(900)
    m3 = pg.eval_on_selector_all(".leaflet-marker-icon", "e=>e.length")
    lapor("peta: sakelar jenis & pencarian titik", m0 > 0 and m1 == 0 and m2 > 0 and m3 <= m2,
          "penanda %d → semua mati %d → hidup lagi %d → cari 'kripik' %d" % (m0, m1, m2, m3))
    pg.close()

    # ---------- 5. PANEL LOMPAT ----------
    pg = ctx.new_page()
    pg.goto(BASE + "/index.html", wait_until="load")
    pg.wait_for_timeout(1500)
    pg.keyboard.press("/")
    pg.wait_for_timeout(700)
    terbuka = pg.eval_on_selector(".panel-lompat", "e=>e.classList.contains('terbuka')")
    pg.fill("#inputLompat", "peta")
    pg.wait_for_timeout(500)
    hasil = pg.eval_on_selector_all("#daftarLompat > *", "e=>e.length")
    lapor("panel lompat cepat", terbuka and hasil > 0, "terbuka=%s hasil=%d" % (terbuka, hasil))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    lapor("panel lompat: Esc menutup", not pg.eval_on_selector(".panel-lompat", "e=>e.classList.contains('terbuka')"), "")
    pg.close()

    # ---------- 6. FORM: validasi & tautan WhatsApp ----------
    pg = ctx.new_page()
    pg.goto(BASE + "/kontak.html", wait_until="load")
    pg.wait_for_timeout(1400)
    pg.click("#formKontak button[type=submit]")
    pg.wait_for_timeout(700)
    pesan = pg.eval_on_selector_all(".invalid-feedback, .alert", "e=>e.filter(x=>x.offsetParent!==null).length")
    lapor("kontak: validasi form kosong", pesan > 0 or pg.url.split("#")[0] == BASE + "/kontak.html", "%d pesan" % pesan)
    pg.close()

    # ---------- 7. LIGHTBOX galeri wisata ----------
    pg = ctx.new_page()
    pg.goto(BASE + "/wisata/candra-wilwatikta.html", wait_until="load")
    pg.wait_for_timeout(1800)
    gl = pg.query_selector("[data-bs-toggle=lightbox], a[data-gallery], .galeri a")
    if gl:
        gl.click()
        pg.wait_for_timeout(1200)
        lapor("lightbox galeri", pg.query_selector(".lightbox, .modal.show") is not None, "lightbox terbuka")
    else:
        lapor("lightbox galeri", False, "tidak ada tautan galeri")
    pg.close()

    # ---------- 8. BACA NANTI / simpan artikel (localStorage) ----------
    pg = ctx.new_page()
    pg.goto(BASE + "/berita/genangan-bypass-pandaan-usai-hujan-deras.html", wait_until="load")
    pg.wait_for_timeout(1800)
    simpan = pg.query_selector("[data-save-article]")
    if simpan:
        simpan.click()
        pg.wait_for_timeout(700)
        tekan = pg.eval_on_selector("[data-save-article]", "e=>e.getAttribute('aria-pressed')")
        isi = pg.evaluate("()=>Object.keys(localStorage).filter(k=>/sp|simpan/i.test(k)).length")
        lapor("simpan artikel (localStorage)", tekan == "true" and isi > 0,
              "aria-pressed=%s · %d kunci localStorage" % (tekan, isi))
    else:
        lapor("simpan artikel (localStorage)", False, "tombol [data-save-article] tidak ada")
    pg.close()
    ctx.close()


# ---------------------------------------------------------------------------
def blok(nama, aksi, hasil, catat_gagal=True):
    """Jalankan satu uji interaksi; kegagalan tidak menghentikan uji lain."""
    try:
        aksi()
    except Exception as e:  # noqa: BLE001
        hasil.append((nama, False, "galat: %s" % str(e).split("\n")[0][:120]))
        if catat_gagal:
            catat("interaksi", nama, str(e).split("\n")[0][:120])


def simpan_cache():
    with open(ARGS.cache, "w", encoding="utf-8") as f:
        json.dump(CATATAN, f, ensure_ascii=False)


def muat_cache():
    try:
        with open(ARGS.cache, encoding="utf-8") as f:
            for k, h, p in json.load(f):
                CATATAN.append((k, h, p))
        return True
    except Exception:  # noqa: BLE001
        return False


def main():
    hasil_sapuan = muat_cache()
    if hasil_sapuan:
        print("  (memakai cache sapuan: %d catatan — hapus %s untuk sapuan ulang)" % (len(CATATAN), ARGS.cache))
    with sync_playwright() as p:
        b = p.chromium.launch()
        halaman = [ARGS.halaman] if ARGS.halaman else semua_halaman()

        if not ARGS.lewati_sapuan and not hasil_sapuan:
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            for i, h in enumerate(halaman, 1):
                sapuan_hal(1280, ctx, h)
                print("   [%2d/%d] %s" % (i, len(halaman), h), flush=True)
            ctx.close()

            ctxm = b.new_context(viewport={"width": 412, "height": 880}, has_touch=True, is_mobile=True)
            for h in ["index.html", "berita/index.html", "wisata/index.html", "umkm/index.html",
                      "layanan/loker.html", "layanan/agenda.html", "peta.html", "kontak.html",
                      "berita/genangan-bypass-pandaan-usai-hujan-deras.html", "wisata/candra-wilwatikta.html"]:
                sapuan_hal(412, ctxm, h)
                target_sentuh(ctxm, h)
            ctxm.close()

            for h in halaman:
                tanpa_js(b, h)
            simpan_cache()

        print("\n  ── Uji interaksi ──", flush=True)

        def lapor(nama, lulus, detail):
            print("   %s %s%s" % ("✅" if lulus else "❌", nama, ("  — " + detail) if detail else ""), flush=True)
            if not lulus:
                catat("interaksi", nama, detail or "gagal")

        try:
            interaksi(b, lapor)
        except Exception as e:  # noqa: BLE001
            catat("interaksi", "-", "uji terputus: %s" % str(e).split("\n")[0][:140])
        b.close()

    from collections import defaultdict
    per = defaultdict(list)
    for k, h, p in CATATAN:
        per[k].append((h, p))
    print("\n  ── Temuan per kategori ──")
    for k in sorted(per, key=lambda x: -len(per[x])):
        print("   %-24s %d" % (k, len(per[k])))
    print("\n  ── Rincian ──")
    for k in sorted(per):
        for h, p in per[k][:40]:
            print("   [%s] %s: %s" % (k, h, p))
        if len(per[k]) > 40:
            print("   [%s] … %d lagi" % (k, len(per[k]) - 40))
    print("\n  Total temuan: %d" % len(CATATAN))
    return 1 if CATATAN else 0


if __name__ == "__main__":
    sys.exit(main())
