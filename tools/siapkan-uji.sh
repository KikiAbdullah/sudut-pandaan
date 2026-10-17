#!/usr/bin/env bash
# ==========================================================================
# Sudut Pandaan — siapkan peralatan uji (Chromium untuk Playwright/Lighthouse)
#
# KENAPA SKRIP INI ADA
#   Situs ini tidak butuh apa pun dari folder /home/user/_libs. Folder itu hanya
#   dipakai oleh uji otomatis (tools/smoke_test.py, tools/cek_tampilan.py) dan
#   audit Lighthouse, yang menjalankan Chromium headless.
#   Chromium memerlukan pustaka sistem (libnss3, libnspr4, libatk, font, dll.)
#   yang tidak ada di image ini, sedangkan kita tidak punya akses root.
#   Solusinya: unduh paket .deb dengan `apt-get download`, ekstrak isinya ke
#   /home/user/_libs/root, lalu arahkan LD_LIBRARY_PATH ke sana.
#
# KAPAN DIJALANKAN
#   - Setelah sandbox/workspace di-reset (folder _libs dan ~/.cache hilang).
#   - Sebelum menjalankan uji tampilan atau Lighthouse.
#
# PAKAI
#   bash tools/siapkan-uji.sh              # unduh + ekstrak + pasang Chromium
#   bash tools/siapkan-uji.sh --cek        # hanya periksa, tidak mengubah apa pun
#   bash tools/siapkan-uji.sh --bersihkan  # hapus /home/user/_libs setelah selesai uji
#
# CATATAN UKURAN: hasil ekstrak penuh 291 MB karena ikut menarik libLLVM/mesa
# (dipakai driver GPU, tidak dipakai Chromium headless). Skrip ini memangkasnya
# ke ± 80 MB; kalau ingin workspace benar-benar ringan, pakai `--bersihkan`
# (uji berikutnya tinggal jalankan skrip ini lagi ± 35 detik).
#
# Setelah selesai, jalankan uji dengan:
#   export LD_LIBRARY_PATH=/home/user/_libs/root/usr/lib/x86_64-linux-gnu:/home/user/_libs/root/lib/x86_64-linux-gnu
#   python3 tools/preview_server.py 8090 &
#   python3 tools/cek_tampilan.py --peta --base http://127.0.0.1:8090
# ==========================================================================
set -euo pipefail

AKAR="/home/user/_libs"
ROOT="$AKAR/root"
UNDUHAN="/tmp/sp-deb"                       # .deb tidak disimpan di workspace (115 MB!)
DAFTAR="$(dirname "$(readlink -f "$0")")/dependensi-uji.txt"
LIB64="$ROOT/usr/lib/x86_64-linux-gnu:$ROOT/lib/x86_64-linux-gnu"

CEK_SAJA=0
BERSIHKAN=0
case "${1:-}" in
  --cek) CEK_SAJA=1 ;;
  --bersihkan) BERSIHKAN=1 ;;
esac

echo "== Sudut Pandaan: peralatan uji =="

# 1. Pustaka sistem untuk Chromium
terpasang=0
[[ -f "$ROOT/usr/lib/x86_64-linux-gnu/libnss3.so" ]] && terpasang=1
if (( CEK_SAJA )); then
  echo "  pustaka sistem : $([[ $terpasang == 1 ]] && echo "OK ($ROOT)" || echo "BELUM ADA — jalankan tanpa --cek")"
else
  if (( terpasang )); then
    echo "  pustaka sistem : sudah ada, dilewati"
  else
    echo "  pustaka sistem : mengunduh $(wc -l < "$DAFTAR") paket…"
    rm -rf "$UNDUHAN" "$ROOT"
    mkdir -p "$UNDUHAN" "$ROOT"
    ( cd "$UNDUHAN" && xargs -a "$DAFTAR" -n 20 apt-get download >/dev/null 2>&1 ) || true
    jumlah=0
    for berkas in "$UNDUHAN"/*.deb; do
      [[ -e "$berkas" ]] || continue
      dpkg-deb -x "$berkas" "$ROOT" 2>/dev/null && jumlah=$((jumlah + 1))
    done
    # Pangkas bagian yang tidak dibutuhkan Chromium headless:
    #   - libLLVM (124 MB) + libgallium (41 MB) + libz3 (27 MB): driver GPU/mesa,
    #     Chromium headless memakai SwiftShader bawaannya sendiri.
    #   - dokumen, manual, locale, data TeX, font tambahan: tidak dipakai rendering.
    # Total: 291 MB → ± 80 MB.
    rm -f "$ROOT/usr/lib/x86_64-linux-gnu/libLLVM.so"* \
          "$ROOT/usr/lib/x86_64-linux-gnu/libgallium-"*.so \
          "$ROOT/usr/lib/x86_64-linux-gnu/libz3.so"* 2>/dev/null || true
    rm -rf "$ROOT/usr/share/doc" "$ROOT/usr/share/man" "$ROOT/usr/share/locale" \
           "$ROOT/usr/share/bug" "$ROOT/usr/share/lintian" "$ROOT/usr/share/info" \
           "$ROOT/usr/share/texmf" "$ROOT/usr/share/gcc" \
           "$ROOT/usr/share/fonts/croscore" "$ROOT/usr/share/fonts/texgyre" \
           "$ROOT/usr/share/fonts/urw-base35" "$ROOT/usr/share/fonts/type1" \
           "$ROOT/usr/share/fonts/truetype/noto"* 2>/dev/null || true
    rm -rf "$UNDUHAN"
    echo "  pustaka sistem : $jumlah paket diekstrak → $ROOT ($(du -sh "$ROOT" | cut -f1))"
  fi
fi

# 2. Peramban Chromium (disimpan di ~/.cache yang TIDAK ikut tersimpan antar sesi)
if [[ -x /home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome ]]; then
  echo "  Chromium       : sudah ada"
elif (( CEK_SAJA )); then
  echo "  Chromium       : BELUM ADA — jalankan tanpa --cek"
else
  echo "  Chromium       : memasang (unduhan ±120 MB, sekali per sesi)…"
  python3 -m playwright install chromium
fi

if (( BERSIHKAN )); then
  echo "  --bersihkan    : menghapus $AKAR (dibuat ulang oleh skrip ini saat dibutuhkan)"
  rm -rf "$AKAR"
fi

echo
echo "Lanjutkan dengan:"
echo "  export LD_LIBRARY_PATH=$LIB64"
echo "  export CHROME_PATH=/home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome"
