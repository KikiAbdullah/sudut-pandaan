#!/usr/bin/env python3
"""
Sudut Pandaan — server pratinjau lokal (gzip + MIME lengkap).

`python3 -m http.server` tidak mengompres berkas, sehingga rasio byte/kecepatan
yang terlihat di lokal lebih buruk daripada hosting asli (Netlify/Cloudflare
sudah otomatis gzip/brotli). Skrip ini menambahkan kompresi + header cache
supaya hasil uji Lighthouse mendekati kondisi produksi.

Pakai:  python3 tools/preview_server.py [port]   (default 8090)
"""
import http.server
import os
import re
import urllib.parse
import socketserver
import sys
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOMPRES = {".html", ".css", ".js", ".json", ".svg", ".txt", ".xml", ".webmanifest", ".md"}
MIME = {
    ".webmanifest": "application/manifest+json", ".webp": "image/webp", ".avif": "image/avif",
    ".woff2": "font/woff2", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".md": "text/markdown; charset=utf-8",
}

# False (default) = pratinjau: tanpa cache. True = `--produksi`: meniru header
# cache hosting asli (aset immutable 1 tahun) untuk pengukuran Lighthouse.
PRODUKSI = False


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME.get(ext) or super().guess_type(path)

    def end_headers(self):
        """Header cache.

        Penting untuk pratinjau: CSS/JS TIDAK boleh di-cache lama. Sebelumnya
        berkas aset dikirim dengan `immutable, max-age=1 tahun`, sehingga setelah
        tampilan dirombak, browser/pane pratinjau masih memakai CSS & JS lama
        (halaman tampak "tidak berubah"). Sekarang defaultnya tanpa cache.
        Mode `--produksi` (untuk mengukur Lighthouse sedekat hosting) tetap
        memakai cache panjang seperti hosting asli.
        """
        if PRODUKSI:
            ext = os.path.splitext(self.path)[1].lower()
            if ext in (".html", ".json", ".webmanifest"):
                self.send_header("Cache-Control", "no-cache")
            else:
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            # Tanpa cache sama sekali: setiap muat ulang/preview selalu segar.
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        """URL bersih + kompatibilitas pola lama, meniru aturan .htaccess.

        1. /berita/detail.html?slug=<slug>  → 301 ke /berita/<slug>.html
        2. /tentang                         → dilayani dari /tentang.html (200)
        Tanpa ini, URL kanonik & sitemap (yang memakai bentuk tanpa .html) akan
        404 saat pratinjau lokal, padahal di hosting sudah benar.
        """
        dari_url = urllib.parse.urlsplit(self.path)
        jalur = urllib.parse.unquote(dari_url.path)

        # 1) pola lama ?slug= → URL statis (sama seperti .htaccess)
        if jalur.rstrip("/").endswith("berita/detail.html"):
            q = urllib.parse.parse_qs(dari_url.query)
            slug = re.sub(r"[^a-z0-9-]", "", (q.get("slug", [""])[0] or "").lower())
            tujuan = jalur.rsplit("/", 1)[0] + "/" + slug + ".html"
            # 301 hanya bila artikelnya benar-benar ada; kalau tidak, jembatan
            # tetap tampil dan menampilkan pesan ramah (seperti di Apache).
            if slug and os.path.isfile(self.translate_path(tujuan)):
                self.send_response(301)
                self.send_header("Location", tujuan)
                self.end_headers()
                return

        # 2) URL bersih tanpa ekstensi → berkas .html yang sepadan
        if jalur.endswith("/") is False and not os.path.splitext(jalur)[1]:
            kandidat = self.translate_path(jalur + ".html")
            if os.path.isfile(kandidat):
                self.path = jalur + ".html" + (("?" + dari_url.query) if dari_url.query else "")
        super().do_GET()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        ext = os.path.splitext(path)[1].lower()
        if ext in KOMPRES and os.path.isfile(path) and "gzip" in self.headers.get("Accept-Encoding", ""):
            with open(path, "rb") as f:
                data = f.read()
            import gzip
            body = gzip.compress(data, 6)
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            import io
            return io.BytesIO(body)
        return super().send_head()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    arg = [a for a in sys.argv[1:] if not a.startswith("--")]
    PRODUKSI = "--produksi" in sys.argv
    port = int(arg[0]) if arg else 8090
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", port), Handler) as httpd:
        print(f"Pratinjau Sudut Pandaan (gzip) → http://0.0.0.0:{port}/")
        print("  mode cache:", "PRODUKSI — aset immutable 1 tahun (untuk Lighthouse)"
              if PRODUKSI else "PRATINJAU — tanpa cache, perubahan selalu terlihat")
        httpd.serve_forever()
        httpd.serve_forever()
