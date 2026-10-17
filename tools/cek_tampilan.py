#!/usr/bin/env python3
"""Cek tampilan hasil build dengan peramban sungguhan (Playwright).

Fungsi berkas ini berbeda dari tools/smoke_test.py:
  * smoke_test.py  → status HTTP & berkas yang tidak ketemu.
  * cek_tampilan.py → apa yang benar-benar *terlihat*: ikon Phosphor tidak kosong,
    gambar tidak rusak, atribut alt lengkap, satu <h1> per halaman, tidak ada
    galat konsol, dan peta Leaflet benar-benar terpasang saat digulir.

Jalankan server dulu (mis. `python3 -m http.server 8080` di root situs), lalu:
    python3 tools/cek_tampilan.py                 # semua halaman HTML hasil build
    python3 tools/cek_tampilan.py --base http://127.0.0.1:8080 --peta

Kode keluar 1 bila ada temuan, supaya bisa dipakai di pipeline.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sys.exit("Butuh Playwright: pip install playwright && python3 -m playwright install chromium")

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEWATI = {"404.html"}          # 404 diuji terpisah (memang tidak ada di sitemap)

JS_IKON = """() => {
  let kosong = 0, total = 0, tersembunyi = 0;
  document.querySelectorAll('i[class*="ph-"]').forEach((i) => {
    if (i.offsetParent === null) { tersembunyi++; return; }  // panel non-aktif, toast, tombol belum tampil
    total++;
    const isi = getComputedStyle(i, '::before').content || '';
    const r = i.getBoundingClientRect();
    if (isi === 'none' || isi === '""' || isi === 'normal' || r.width < 3) kosong++;
  });
  return { kosong, total, tersembunyi };
}"""

JS_HALAMAN = """() => ({
  h1: document.querySelectorAll('h1').length,
  img_rusak: Array.from(document.images)
    .filter((i) => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).length,
  img_alt_hilang: Array.from(document.images).filter((i) => !i.hasAttribute('alt')).length,
})"""

JS_PETA = """() => {
  const el = document.getElementById('peta');
  if (!el) return null;
  return { terpasang: el.classList.contains('leaflet-container'),
           ubin: document.querySelectorAll('#peta img.leaflet-tile').length };
}"""


def daftar_halaman() -> list[str]:
    halaman = []
    for berkas in sorted(ROOT.rglob("*.html")):
        rel = berkas.relative_to(ROOT)
        if any(bagian.startswith(".") or bagian in {"assets", "docs", "tools"} for bagian in rel.parts):
            continue
        if str(rel).replace("\\", "/") in LEWATI:
            continue
        halaman.append("/" + str(rel).replace("\\", "/"))
    return halaman


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    ap.add_argument("--peta", action="store_true", help="gulir ke peta & pastikan Leaflet terpasang")
    a = ap.parse_args()

    halaman = daftar_halaman()
    temuan = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 412, "height": 823})
        pg = ctx.new_page()
        galat: list[str] = []
        http_buruk: list[str] = []
        pg.on("console", lambda m: galat.append(m.text) if m.type == "error" else None)
        pg.on("response", lambda r: http_buruk.append(f"{r.status} {r.url}") if r.status >= 400 else None)

        for url in halaman:
            galat.clear()
            http_buruk.clear()
            pg.goto(a.base + url, wait_until="load")
            pg.wait_for_timeout(1200)
            ikon = pg.evaluate(JS_IKON)
            info = pg.evaluate(JS_HALAMAN)
            pesan = []
            if ikon["kosong"]:
                pesan.append(f"{ikon['kosong']} ikon kosong")
            if info["img_rusak"]:
                pesan.append(f"{info['img_rusak']} gambar rusak")
            if info["img_alt_hilang"]:
                pesan.append(f"{info['img_alt_hilang']} gambar tanpa alt")
            if info["h1"] != 1:
                pesan.append(f"{info['h1']} <h1>")
            if galat:
                pesan.append(f"{len(galat)} galat konsol: {galat[0][:60]}")
            if http_buruk:
                pesan.append(f"{len(http_buruk)} permintaan ≥400: {http_buruk[0][:60]}")

            peta = ""
            if a.peta and pg.evaluate("() => !!document.getElementById('peta')"):
                pg.evaluate("() => document.getElementById('peta').scrollIntoView()")
                pg.wait_for_timeout(2500)
                hasil = pg.evaluate(JS_PETA)
                peta = f" | peta={'ok' if hasil['terpasang'] else 'BELUM'} ({hasil['ubin']} ubin)"
                if not hasil["terpasang"]:
                    pesan.append("peta Leaflet tidak terpasang")

            temuan += len(pesan)
            tanda = "!!" if pesan else "OK"
            print(f"  {tanda} {url:46} ikon {ikon['total']:>3}/{ikon['kosong']} kosong "
                  f"({ikon['tersembunyi']} tersembunyi){peta}")
            for x in pesan:
                print(f"        ⚠ {x}")

        browser.close()

    print(f"\n  Halaman diperiksa: {len(halaman)} — temuan: {temuan}")
    return 1 if temuan else 0


if __name__ == "__main__":
    raise SystemExit(main())
