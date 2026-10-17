# Uji otomatis (opsional) — butuh Playwright: pip install playwright && playwright install chromium
"""Smoke test Sudut Pandaan: cek console error, 404, dan konten dinamis."""
import asyncio
import tempfile, sys
from playwright.async_api import async_playwright

import os
# Port bisa diganti: jalankan server (mis. `python3 tools/preview_server.py 8090`) lalu
#   SP_BASE=http://127.0.0.1:8090 python3 tools/smoke_test.py
BASE = os.environ.get("SP_BASE", "http://127.0.0.1:8080")
PAGES = [
    # Beranda tata letak MAJALAH + BENTO: masthead, petak berita utama, rail
    # destinasi/berita, kartu layanan, dan daftar harga kuliner.
    ("/index.html", [".masthead .masthead-nama", "[data-bento-utama] .card-lead",
                    "[data-list=\"wisata-sorotan\"] .tile", "[data-list=\"berita-lead\"] .tile",
                    ".kartu-layanan", "[data-list=\"kuliner-daftar\"] li"]),
    ("/berita/index.html", ["#daftarBerita .card-news"]),
    ("/berita/truk-terguling-tol-pandaan-arah-malang.html", [".artikel-body p", "[data-toc-link]", "[data-artikel]"]),
    ("/wisata/index.html", ["#daftarDirektori .card-place"]),
    ("/wisata/candra-wilwatikta.html", ["#peta.leaflet-container"]),
    ("/kuliner/index.html", ["#daftarDirektori .card-place"]),
    ("/umkm/index.html", ["#daftarDirektori .card-place"]),
    ("/umkm/kripik-tempe-bu-tini.html", ["#peta.leaflet-container"]),
    ("/layanan/lalu-lintas.html", ["#daftarLalin .list-group-item"]),
    ("/layanan/agenda.html", ["#daftarAgenda .card"]),
    ("/layanan/loker.html", ["#daftarLoker .card"]),
    ("/layanan/nomor-penting.html", ["#daftarNomor tr"]),
    ("/peta.html", ["#peta.leaflet-container", "#daftarTitik .info-box"]),
    ("/panduan/index.html", [".card-place"]),
    ("/panduan/panduan-wisata-pandaan-sehari.html", [".article-body table"]),
    ("/tentang.html", ["main h1"]),
    ("/redaksi.html", ["main h1"]),
    ("/pasang-iklan.html", ["table tbody tr"]),
    ("/kontak.html", ["#formKontak"]),
    ("/layanan/lapor.html", ["#formLapor"]),
    ("/umkm/daftar.html", ["#formUmkm"]),
    ("/privasi.html", ["main h1"]),
    ("/404.html", [".display-1"]),
    ("/link/index.html", ["a.btn"]),
]


async def main():
    hasil = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1366, "height": 900}, locale="id-ID")
        page = await ctx.new_page()
        errors, failed = [], []
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type in ("error",) else None)
        page.on("requestfailed", lambda r: failed.append(f"{r.url} :: {r.failure}"))
        page.on("response", lambda r: failed.append(f"HTTP {r.status} {r.url}") if r.status >= 400 else None)

        for path, checks in PAGES:
            errors.clear(); failed.clear()
            await page.goto(BASE + path, wait_until="networkidle", timeout=45000)
            await page.wait_for_timeout(700)
            status = []
            for sel in checks:
                try:
                    if "leaflet-container" in sel:
                        # Leaflet baru dimuat saat peta mendekati layar (main.js saatIdle/
                        # initPetaTertunda) → gulirkan dulu, baru tunggu lebih lama.
                        await page.eval_on_selector("#peta", "el => el.scrollIntoView({block:'center'})")
                    await page.wait_for_selector(sel, timeout=15000 if "leaflet" in sel else 6000)
                    status.append(f"ok:{sel}")
                except Exception:
                    status.append(f"GAGAL:{sel}")
            # hitung kontainer kosong
            kosong = await page.evaluate("""() => {
                const ids = ['#beritaTerbaru','#daftarBerita','#daftarDirektori','#daftarAgenda','#daftarLoker','#daftarLalin','#daftarNomor','#daftarTitik','#sidebarPopuler','[data-list="berita-terbaru"]'];
                const out = [];
                for (const id of ids) {
                  const el = document.querySelector(id);
                  if (el && el.textContent.trim().length < 3) out.push(id + ' kosong');
                }
                return out;
            }""")
            hasil.append({"path": path, "checks": status, "kosong": kosong,
                          "errors": list(errors), "failed": list(failed)[:6]})

        # screenshot desktop
        await page.set_viewport_size({"width": 1366, "height": 900})
        # Tangkapan layar ditulis ke direktori sementara OS, bukan ke workspace —
        # supaya berkas hasil uji tidak menumpuk di folder kerja (dan tidak ikut
        # tersimpan ke snapshot workspace).
        tmp = tempfile.gettempdir()
        os.makedirs(tmp + "/sp-shots", exist_ok=True)
        for path, out in [("/index.html", tmp + "/sp-shots/home-desktop.png"),
                          ("/berita/index.html", tmp + "/sp-shots/berita-desktop.png"),
                          ("/berita/truk-terguling-tol-pandaan-arah-malang.html", tmp + "/sp-shots/detail-desktop.png"),
                          ("/wisata/candra-wilwatikta.html", tmp + "/sp-shots/wisata-detail-desktop.png"),
                          ("/peta.html", tmp + "/sp-shots/peta-desktop.png"),
                          ("/umkm/kripik-tempe-bu-tini.html", tmp + "/sp-shots/umkm-desktop.png")]:
            await page.goto(BASE + path, wait_until="networkidle")
            await page.wait_for_timeout(1200)
            await page.evaluate("window.scrollTo(0,0)")
            await page.screenshot(path=out, full_page=False)
        # mobile
        m = await ctx.new_page()
        await m.set_viewport_size({"width": 390, "height": 844})
        await m.goto(BASE + "/index.html", wait_until="networkidle")
        await m.wait_for_timeout(1200)
        await m.screenshot(path=tmp + "/sp-shots/home-mobile.png")
        await m.goto(BASE + "/wisata/index.html", wait_until="networkidle")
        await m.wait_for_timeout(900)
        await m.screenshot(path=tmp + "/sp-shots/wisata-mobile.png")
        await browser.close()

    for h in hasil:
        tanda = "OK " if all(c.startswith("ok:") for c in h["checks"]) and not h["kosong"] and not h["errors"] and not h["failed"] else "XX "
        print(f"{tanda}{h['path']}")
        for c in h["checks"]:
            if c.startswith("GAGAL"): print("      ", c)
        for k in h["kosong"]: print("       kosong:", k)
        for e in h["errors"][:4]: print("       console:", e[:160])
        for f in h["failed"][:4]: print("       failed:", f[:160])

asyncio.run(main())
