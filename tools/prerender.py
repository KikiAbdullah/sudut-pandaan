# -*- coding: utf-8 -*-
"""
Sudut Pandaan — tools/prerender.py
Mengisi kontainer yang sebelumnya HANYA diisi JavaScript dengan HTML jadi
(SEO + pengguna tanpa JS). Caranya: buka tiap halaman di Chromium sungguhan
lewat server lokal sementara, ambil hasil render, lalu tuliskan kembali ke
berkas .html — sehingga hasil statis PASTI identik dengan hasil JS.

Pemakaian:
    cd sudutpandaan && python3 tools/prerender.py            # semua halaman
    python3 tools/prerender.py --halaman index.html berita/index.html
    python3 tools/prerender.py --kering                      # hanya laporkan

Tanpa Playwright/Chromium, skrip ini berhenti dengan pesan (situs tetap
berfungsi: kontainer kembali diisi JS seperti semula).
"""

import argparse
import http.server
import os
import re
import socketserver
import sys
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 0   # 0 = biarkan sistem memilih port kosong

# Kontainer yang diisi JS -> innerHTML  (id / data-list / atribut lain)
KONTAINER = [
    '#daftarBerita', '#blokHasilLain', '#hasilLain', '#paginasiBerita',
    '#daftarDirektori', '#daftarLoker', '#daftarNomor', '#daftarTitik',
    '#linimasaAgenda', '#sidebarPopuler', '#sidebarAgenda',
    '[data-bento-utama]', '[data-bento-sisi]', '[data-bento-destinasi]', '[data-bento-kuliner]',
    '[data-list="berita-lead"]', '[data-list="berita-terbaru"]', '[data-list="kategori-berita"]',
    '[data-list="wisata-sorotan"]', '[data-list="kuliner-foto"]', '[data-list="kuliner-daftar"]',
    '[data-list="umkm-pilihan"]', '[data-list="sosmed"]', '[data-list="terkait-berita"]',
    '[data-list="sekitar"]', '[data-list="panduan-lain"]',
]
# Elemen yang isinya teks biasa -> textContent
TEKS = ['#hasilInfo', '#hasilInfoAgenda', '#hasilInfoDirektori', '#hasilInfoLoker', '#updateTerakhir']


# ---------------------------------------------------------------------------
# Alat tulis-ulang HTML tanpa parser pihak ketiga (aman: cari tag penyeimbang)
# ---------------------------------------------------------------------------
def posisi_isi(html, penanda, ke=0):
    """Temukan (awal_isi, akhir_isi, tag) untuk penanda dari KONTAINER."""
    if penanda.startswith("["):
        atribut = penanda[1:-1]
        pola = re.compile(r"<([a-zA-Z0-9]+)([^>]*\b%s(?:=(?:\"[^\"]*\"|'[^']*'))?[^>]*)>" % re.escape(atribut), re.I)
    else:
        pola = re.compile(r"<([a-zA-Z0-9]+)([^>]*\bid=\"%s\"[^>]*)>" % re.escape(penanda.lstrip("#")), re.I)
    m = None
    for i, kandidat in enumerate(pola.finditer(html)):
        if i == ke:
            m = kandidat
            break
    if not m:
        return None
    tag = m.group(1)
    awal = m.end()
    if m.group(2).rstrip().endswith("/"):
        return None
    tingkat, pos = 0, awal
    pola_tag = re.compile(r"<%s\b|</%s\s*>" % (tag, tag), re.I)
    while True:
        t = pola_tag.search(html, pos)
        if not t:
            return None
        if html[t.start():t.start() + 2] == "</":
            if tingkat == 0:
                return (awal, t.start(), tag)
            tingkat -= 1
        else:
            tingkat += 1
        pos = t.end()


def ganti(html, penanda, isi_baru, tipe="html", ke=0):
    pos = posisi_isi(html, penanda, ke)
    if not pos:
        return html, False
    awal, akhir, _ = pos
    return html[:awal] + isi_baru + html[akhir:], True


def ganti_teks(html, penanda, teks):
    pos = posisi_isi(html, penanda)
    if not pos:
        return html, False
    awal, akhir, _ = pos
    aman = (teks.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return html[:awal] + aman + html[akhir:], True


# ---------------------------------------------------------------------------
def halaman_semua():
    keluar = []
    for r, d, f in os.walk(BASE_DIR):
        d[:] = [x for x in d if x not in ("assets", "tools", "docs", ".git", "uploads", "__pycache__")]
        for n in f:
            if n.endswith(".html"):
                keluar.append(os.path.relpath(os.path.join(r, n), BASE_DIR).replace(os.sep, "/"))
    return sorted(keluar)


class Server(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=BASE_DIR, **k)

    def log_message(self, *a):  # senyap
        pass


class ServerTCP(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--halaman", nargs="*", default=[])
    ap.add_argument("--kering", action="store_true", help="hanya laporkan, tanpa menulis")
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        print("  Playwright tidak tersedia (%s) — prerender dilewati." % str(e)[:60])
        return 2

    httpd = ServerTCP(("127.0.0.1", PORT), Server)   # PORT 0 = pilih port kosong
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    halaman = a.halaman or halaman_semua()
    total_kontainer = 0
    gagal = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1366, "height": 900})
        for h in halaman:
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            try:
                pg.goto("http://127.0.0.1:%d/%s" % (port, h), wait_until="load", timeout=45000)
                pg.wait_for_timeout(2600)           # beri waktu data JSON & render
                isi_kontainer, isi_teks = {}, {}
                for sel in KONTAINER:
                    daftar = pg.evaluate("s=>Array.from(document.querySelectorAll(s)).map(e=>e.innerHTML)", sel)
                    for i, v in enumerate(daftar or []):
                        if v:
                            isi_kontainer.setdefault(sel, []).append(v)
                for sel in TEKS:
                    v = pg.evaluate("s=>{const el=document.querySelector(s);return el?el.textContent.trim():null;}", sel)
                    if v:
                        isi_teks[sel] = v
            except Exception as e:  # noqa: BLE001
                gagal.append((h, str(e)[:80]))
                pg.close()
                continue
            pg.close()

            berkas = os.path.join(BASE_DIR, h)
            with open(berkas, encoding="utf-8") as f:
                html = f.read()
            html_baru, jumlah = html, 0
            for sel, daftar in isi_kontainer.items():
                for i, v in enumerate(daftar):
                    hasil, ok = ganti(html_baru, sel, v, ke=i)
                    # setelah penggantian pertama, dokumen berubah → cari ulang dari awal
                    html_baru = hasil
                    jumlah += 1 if ok else 0
            for sel, v in isi_teks.items():
                html_baru, ok = ganti_teks(html_baru, sel, v)
                jumlah += 1 if ok else 0
            if jumlah and not a.kering:
                with open(berkas, "w", encoding="utf-8") as f:
                    f.write(html_baru)
            total_kontainer += jumlah
            tanda = "  " if not errs else "! "
            print("%s%-46s %2d kontainer  %s" % (tanda, h, jumlah, ("galat: " + errs[0][:60]) if errs else ""))
        b.close()
    httpd.shutdown()
    print("\n  Kontainer terisi: %d pada %d halaman%s" %
          (total_kontainer, len(halaman), " (mode kering)" if a.kering else ""))
    for h, e in gagal:
        print("   gagal: %s — %s" % (h, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
