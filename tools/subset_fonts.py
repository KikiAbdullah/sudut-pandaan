#!/usr/bin/env python3
"""Subset font webfont lokal (Inter & Poppins) ke karakter yang benar-benar
dipakai situs berbahasa Indonesia, lalu cetak `unicode-range` hasilnya.

Kenapa: berkas latin Inter dari Google Fonts berukuran ±48 KB. Karena font body
di-preload (agar pertukaran webfont tidak menggeser tata letak / CLS), ukuran itu
ikut masuk jalur kritis dan menunda LCP. Setelah disubset: ±17 KB.

Pemakaian:
    python3 tools/subset_fonts.py                     # semua target
    python3 tools/subset_fonts.py --cek               # hanya laporkan ukuran

Setelah dijalankan, salin nilai `unicode-range` yang dicetak ke
assets/css/fonts.css pada blok @font-face berkas terkait — kalau tidak,
peramban akan mengira berkas memuat karakter yang sudah dibuang.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from fontTools import subset
    from fontTools.ttLib import TTFont
except ImportError:  # pragma: no cover
    sys.exit("Butuh fontTools: pip install fonttools brotli")

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"

# Karakter minimum yang harus tetap ada (aman untuk teks Indonesia + tanda baca
# tipografis yang dipakai redaksi): ASCII, Latin-1, simbol mata uang, tanda
# hubung/elipsis/kutip melengkung, panah, ≤ ≥, dan tanda hubung tak terputus.
UNICODES = (
    "U+0020-007E,"          # ASCII
    "U+00A0-00FF,"          # Latin-1 Supplement (é, ñ, ×, ·, °, dll.)
    "U+0131,U+0152-0153,"   # dotless i, OE/oe
    "U+2000-206F,"          # tanda baca umum (– — ‘ ’ “ ” … ‰)
    "U+20AC,U+2122,"        # euro, trademark
    "U+2190-2193,"          # panah
    "U+2212,U+2264-2265,"   # minus, ≤, ≥
    "U+FEFF,U+FFFD"
)

# Target: hanya Inter latin. Font Poppins hanya ±7,6 KB/berkas sehingga tidak
# sepadan risikonya (karakter di luar subset akan jatuh ke font sistem).
# Font situs sekarang: Manrope (badan) & Playfair Display (judul) — dua-duanya
# variable font. Berkas keluaran di assets/fonts/ sudah disubset ke rentang
# karakter Indonesia; skrip ini dipakai lagi bila ingin mempersempit/memperluas
# rentang itu, lalu `unicode-range` di assets/css/fonts.css disalin dari hasil.
TARGET = {
    "manrope-latin.woff2": "Manrope 200–800 latin (font badan)",
    "playfair-latin.woff2": "Playfair Display 400–900 latin (font judul)",
}

# Fitur OpenType yang dipertahankan. "*" menambah ±4,7 KB tanpa manfaat nyata
# untuk teks Indonesia (ss01–ss03, cv… hanya varian gaya opsional).
LAYOUT_FEATURES = "kern,liga,clig,calt,ccmp"


def range_dari_cmap(path: Path) -> str:
    """Ubah cmap font menjadi rangkaian unicode-range yang rapat."""
    font = TTFont(path, lazy=True)
    kode = sorted({c for t in font["cmap"].tables for c in t.cmap.keys() if c > 31})
    font.close()
    bagian: list[str] = []
    awal = akhir = kode[0]
    for c in kode[1:]:
        if c == akhir + 1:
            akhir = c
            continue
        bagian.append(hex(awal) if awal == akhir else f"{hex(awal)}-{hex(akhir)[2:]}")
        awal = akhir = c
    bagian.append(hex(awal) if awal == akhir else f"{hex(awal)}-{hex(akhir)[2:]}")
    return ", ".join(b.upper().replace("0X", "U+") for b in bagian)


def subset_satu(nama: str, cek: bool) -> None:
    asal = FONT_DIR / nama
    if asal.exists() is False:
        print(f"  ! lewat  {nama} (tidak ada)")
        return
    ukuran_awal = asal.stat().st_size
    if cek:
        print(f"  · {nama}: {ukuran_awal/1024:.1f} KB — {TARGET.get(nama, '')}")
        return

    tmp = asal.with_suffix(".tmp.woff2")
    subset.main([
        str(asal),
        f"--unicodes={UNICODES}",
        "--flavor=woff2",
        f"--layout-features={LAYOUT_FEATURES}",
        "--ignore-missing-unicodes",
        "--drop-tables+=DSIG",
        f"--output-file={tmp}",
    ])
    if not tmp.exists() or tmp.stat().st_size == 0:
        sys.exit(f"  ! subset {nama} gagal (berkas kosong) — berkas asli tidak diubah")

    # Jangan pernah memperbesar berkas; kalau hasil subset lebih besar, pakai aslinya.
    if tmp.stat().st_size >= ukuran_awal:
        print(f"  = {nama}: subset {tmp.stat().st_size/1024:.1f} KB ≥ asal, dilewati")
        tmp.unlink()
        return

    ukuran_akhir = tmp.stat().st_size
    tmp.replace(asal)
    print(f"  ✓ {nama}: {ukuran_awal/1024:.1f} KB → {ukuran_akhir/1024:.1f} KB")
    print(f"      unicode-range: {range_dari_cmap(asal)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Subset webfont lokal.")
    ap.add_argument("--cek", action="store_true", help="hanya laporkan ukuran")
    a = ap.parse_args()
    print("Subset webfont lokal:")
    for nama in TARGET:
        subset_satu(nama, a.cek)


if __name__ == "__main__":
    main()
