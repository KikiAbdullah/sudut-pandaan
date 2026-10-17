#!/usr/bin/env bash
# ==========================================================================
# Sudut Pandaan — pulihkan berkas JavaScript dari cadangan
#
# KENAPA: penyimpanan workspace pernah memutar balik assets/js/* ke versi lama
# (masih memakai Bootstrap Icons `bi bi-*`, toggle mode gelap, AOS, dan pemuatan
# data via fetch). Akibatnya ikon tampil kosong dan gambar hotlink Unsplash
# diminta ke server lokal (404). Skrip ini mengembalikan versi yang benar.
#
# PAKAI:  bash tools/pulihkan-js.sh          # pulihkan hanya bila perlu
#         bash tools/pulihkan-js.sh --paksa  # timpa tanpa memeriksa dulu
#
# Setelah memulihkan: jalankan ulang uji
#   python3 tools/cek_tampilan.py --base http://127.0.0.1:8090
# ==========================================================================
set -euo pipefail
DIR="$(dirname "$(readlink -f "$0")")"
JS="$DIR/../assets/js"
PAKSA=0
[[ "${1:-}" == "--paksa" ]] && PAKSA=1

cek() { grep -q "ikonKelas" "$JS/$1"; }

if (( ! PAKSA )) && cek config.js && cek components.js && ! grep -q 'bi bi-' "$JS/components.js"; then
  echo "  Berkas JS sudah versi benar — tidak ada yang diubah."
  exit 0
fi

for f in config.js components.js pages.js main.js map.js share.js; do
  cp "$DIR/js-cadangan/$f" "$JS/$f"
  printf "  ✓ %s\n" "$f"
done
echo "  Selesai. Jalankan: python3 tools/build.py (bila HTML juga perlu disegarkan)"
