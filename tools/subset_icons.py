#!/usr/bin/env python3
"""
Sudut Pandaan — pembuat subset ikon Phosphor.

Masalah: paket resmi @phosphor-icons/web berisi ribuan ikon (±150 KB per varian
font + ±78 KB CSS per varian). Situs hanya memakai puluhan ikon, sehingga
§10 blueprint (hemat byte, mobile-first) menuntut subsetting.

Skrip ini:
  1. Memindai seluruh *.html + assets/js/*.js untuk menemukan nama ikon yang dipakai
     (`ph ph-nama` = regular, `ph-fill ph-nama` = fill, `ph-bold ph-nama` = bold).
  2. Mengambil peta nama → codepoint dari style.css resmi Phosphor.
  3. Men-subset file .woff2 (fontTools) sehingga hanya glyph yang dipakai tersisa.
  4. Menulis satu berkas CSS ringkas: assets/vendor/phosphor/phosphor.css

Hasil: pengganti 3 berkas style.css (≈234 KB) + 3 font (≈440 KB) menjadi
1 berkas CSS kecil + 1–3 berkas font kecil. Jalan tanpa npm pada runtime.

Pakai:
    python3 tools/subset_icons.py --src /path/ke/phosphor-paket/src
Sumber paket: `npm pack @phosphor-icons/web` lalu ekstrak (folder `src/`).
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "vendor", "phosphor")

VARIAN = {  # nama kelas -> (folder sumber, nama font-face, weight CSS)
    "": ("regular", "Phosphor", "normal"),
    "-bold": ("bold", "Phosphor-Bold", "bold"),
    "-fill": ("fill", "Phosphor-Fill", "normal"),
}


def nama_ikon_dipakai() -> dict[str, set[str]]:
    """Kumpulkan ikon yang benar-benar dipakai, dikelompokkan per varian."""
    pakai: dict[str, set[str]] = {k: set() for k in VARIAN}
    berkas = [p for p in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)
              if f"{os.sep}dist{os.sep}" not in p]
    berkas += glob.glob(os.path.join(ROOT, "assets", "js", "*.js"))
    pola = re.compile(r'class="((?:[^"]*\bph(?:-bold|-fill)?\b[^"]*))"|'
                      r"'((?:[^']*\bph(?:-bold|-fill)?\b[^']*))'")
    for p in berkas:
        if os.path.basename(p) == "subset_icons.py":
            continue
        teks = open(p, encoding="utf-8", errors="ignore").read()
        for m in pola.finditer(teks):
            potongan = m.group(1) or m.group(2) or ""
            kelas = potongan.split()
            varian = ""
            if "ph-fill" in kelas:
                varian = "-fill"
            elif "ph-bold" in kelas:
                varian = "-bold"
            for k in kelas:
                if k.startswith("ph-") and k[3:] not in ("bold", "fill", "regular"):
                    pakai[varian].add(k[3:])
    # Nama ikon dari pemanggilan SP.ico('…') / SP.ikonKelas('…') dan dari tabel
    # alias di config.js (semuanya memakai varian regular).
    for p in glob.glob(os.path.join(ROOT, "assets", "js", "*.js")):
        teks = open(p, encoding="utf-8", errors="ignore").read()
        for nama in re.findall(r"SP\.i(?:co|konKelas)\(\s*'([a-z0-9-]+)'", teks):
            pakai[""].add(nama)
        for blok in re.findall(r"ALIAS_IKON\s*=\s*\{(.*?)\};", teks, re.S):
            for nama in re.findall(r"'([a-z0-9-]+)'\s*:\s*'([a-z0-9-]+)'", blok):
                pakai[""].add(nama[1])
        # Ikon yang ditulis apa adanya di dalam string JS (mis. komponen kartu):
        # '<i class="ph ph-user">' → harus ikut disubset, kalau tidak glyph-nya kosong.
        for varian, pola in (("", r"ph ph-([a-z0-9-]+)"),
                             ("-fill", r"ph-fill ph-([a-z0-9-]+)"),
                             ("-bold", r"ph-bold ph-([a-z0-9-]+)")):
            for nama in re.findall(pola, teks):
                pakai[varian].add(nama)
    return pakai

    return pakai



def peta_codepoint(style_css: str) -> dict[str, str]:
    """Baca peta nama ikon -> codepoint dari style.css resmi Phosphor."""
    teks = open(style_css, encoding="utf-8", errors="ignore").read()
    peta: dict[str, str] = {}
    for blok in teks.split("}"):
        if ":before" not in blok or "content" not in blok:
            continue
        nama = blok.split(".ph-", 1)[1].split(":before", 1)[0].strip()
        if "." in nama:          # varian fill/bold: ".ph-fill.ph-nama"
            nama = nama.split(".")[-1]
        if nama.startswith("ph-"):   # sisa awalan setelah pemisahan di atas
            nama = nama[3:]
        sesudah = blok.split("content:", 1)[1]
        heks = "".join(c for c in sesudah if c in "0123456789abcdefABCDEF")
        if nama and heks:
            peta[nama] = heks
    return peta


def subset_font(peta: dict[str, str], nama: list[str], src_woff2: str, tujuan: str) -> int:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    unicodes = sorted({peta[n] for n in nama if n in peta})
    opsi = subset.Options()
    opsi.layout_features = ["*"]
    opsi.drop_tables += ["DSIG", "SVG ", "EBDT", "EBLC", "CBDT", "CBLC", "sbix"]
    opsi.notdef_outline = True
    opsi.recalc_bounds = True
    font = TTFont(src_woff2)
    sb = subset.Subsetter(options=opsi)
    sb.populate(unicodes=[int(u, 16) for u in unicodes])
    sb.subset(font)
    font.flavor = "woff2"
    font.save(tujuan)
    return len(unicodes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder src/ dari paket @phosphor-icons/web")
    args = ap.parse_args()

    pakai = nama_ikon_dipakai()
    total = sum(len(v) for v in pakai.values())
    if not total:
        print("Tidak ada ikon yang terdeteksi dipakai.", file=sys.stderr)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)

    blok_face: list[str] = []
    blok_kelas: list[str] = []
    ringkas: list[str] = []

    for sufiks, (folder, keluarga, berat) in VARIAN.items():
        nama = sorted(pakai[sufiks])
        if not nama:
            continue
        src = os.path.join(args.src, folder)
        peta = peta_codepoint(os.path.join(src, "style.css"))
        hilang = [n for n in nama if n not in peta]
        if hilang:
            print(f"  ! {folder}: ikon tidak ditemukan di font → dilewati: {', '.join(hilang)}")
            nama = [n for n in nama if n in peta]
        tujuan_font = os.path.join(OUT_DIR, f"{keluarga}.woff2")
        jml = subset_font(peta, nama, os.path.join(src, f"{keluarga}.woff2"), tujuan_font)
        kb = os.path.getsize(tujuan_font) / 1024
        ringkas.append(f"  {folder:8} {jml:3} glyph → {keluarga}.woff2 ({kb:.1f} KB)")
        blok_face.append(
            "@font-face{font-family:'%s';src:url('%s.woff2') format('woff2');"
            "font-weight:%s;font-style:normal;font-display:block}" % (keluarga, keluarga, berat))
        selektor = ".ph" + sufiks
        blok_kelas.append(
            "%s{font-family:'%s' !important;font-style:normal;font-weight:normal;"
            "font-variant:normal;line-height:1;text-transform:none;speak:never;"
            "-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}"
            % (selektor, keluarga))
        aturan = "".join('%s.ph-%s:before{content:"\\%s"}' % (selektor, n, peta[n]) for n in nama)
        blok_kelas.append(aturan)

    css = ("/* Sudut Pandaan — Phosphor Icons (subset otomatis)\n"
           "   Sumber: @phosphor-icons/web (MIT). Dibuat oleh tools/subset_icons.py\n"
           "   Var. resmi: https://phosphoricons.com  •  jangan sunting manual */\n"
           + "\n".join(blok_face) + "\n"
           + ".ph,.ph-bold,.ph-fill{display:inline-block;vertical-align:-.125em}\n"
           + "\n".join(blok_kelas) + "\n")
    tujuan_css = os.path.join(OUT_DIR, "phosphor.css")
    with open(tujuan_css, "w", encoding="utf-8") as f:
        f.write(css)

    print("Subset ikon Phosphor:")
    print("\n".join(ringkas))
    print(f"  CSS      → phosphor.css ({os.path.getsize(tujuan_css)/1024:.1f} KB, "
          f"{sum(len(v) for v in pakai.values())} aturan ikon)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
