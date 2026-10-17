"""Uji menyeluruh bagian B (Berita) — indeks, filter, paginasi, jembatan, navigasi.

Jalankan setelah `bash tools/siapkan-uji.sh` dan server pratinjau hidup:

    export LD_LIBRARY_PATH=/home/user/_libs/root/usr/lib/x86_64-linux-gnu:/home/user/_libs/root/lib/x86_64-linux-gnu
    python3 tools/uji_berita.py [BASE]        # default http://127.0.0.1:8090

Seluruh kasus harus "lulus". Uji ini tidak mengubah berkas apa pun.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"
LEBAR, TINGGI = 412, 900
lulus, gagal = [], []


def cek(nama, syarat, catatan=""):
    (lulus if syarat else gagal).append(nama)
    print(f"    {'✅' if syarat else '❌'} {nama}" + (f" — {catatan}" if catatan else ""))


def kartu(pg, sel="#daftarBerita .card"):
    return pg.evaluate(f"()=>document.querySelectorAll('{sel}').length")


def jalankan():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": LEBAR, "height": TINGGI})
        pg = ctx.new_page()
        errs, http_buruk = [], []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("response", lambda r: http_buruk.append(f"{r.status} {r.url}") if r.status >= 400 else None)

        # --- 1. Indeks: penyaringan lewat URL langsung ------------------------
        print("\n  1) Indeks berita — 7 kasus URL langsung")
        for nama, url, harap in [
            ("indeks polos", "/berita/index.html", 12),
            ("kategori=peristiwa", "/berita/index.html?kategori=peristiwa", 2),
            ("kategori=lalu-lintas", "/berita/index.html?kategori=lalu-lintas", 3),
            ("q=hujan", "/berita/index.html?q=hujan", 5),
            ("kategori tak dikenal", "/berita/index.html?kategori=tidak-ada", 0),
        ]:
            pg.goto(BASE + url, wait_until="load"); pg.wait_for_timeout(1400)
            n = kartu(pg)
            info = pg.evaluate("()=>{const e=document.getElementById('hasilInfo');return e?e.textContent.trim():'';}")
            cek(nama, n == harap and len(errs) == 0, f"{n} kartu (harap {harap}) · info: {info[:58]}")
        for urut, judul_awal in [("populer", "Rute Alternatif"), ("judul", "")]:
            pg.goto(f"{BASE}/berita/index.html?urut={urut}", wait_until="load"); pg.wait_for_timeout(1200)
            atas = pg.evaluate("()=>{const e=document.querySelector('#daftarBerita .card-title');return e?e.textContent.trim():'';}")
            cek(f"urut={urut}", kartu(pg) == 12 and (judul_awal in atas), f"teratas: {atas[:44]}")

        # --- 2. Indeks: interaksi tanpa muat ulang ---------------------------
        print("\n  2) Indeks berita — interaksi (tanpa reload)")
        pg.goto(f"{BASE}/berita/index.html", wait_until="load"); pg.wait_for_timeout(1400)
        chip_href = pg.evaluate("()=>document.querySelector('#filterKategori .chip:nth-child(3)').getAttribute('href')")
        # Bentuk yang benar: query relatif (mis. "?kategori=lalu-lintas") supaya URL
        # bersih /berita/ tetap utuh saat tautan dibuka di tab baru atau disalin.
        cek("chip punya href nyata & bisa dibuka di tab baru",
            (chip_href or "").startswith("?") and "kategori=" in (chip_href or ""), f"href={chip_href}")
        pg.click("#filterKategori .chip:nth-child(3)"); pg.wait_for_timeout(600)
        cek("klik chip menyaring + URL tersinkron",
            kartu(pg) == 3 and "kategori=lalu-lintas" in pg.url, pg.url.split("8090")[-1])
        pg.fill("#qBerita", "truk"); pg.wait_for_timeout(700)
        cek("kata kunci menyempitkan hasil + URL tersinkron",
            kartu(pg) == 1 and "q=truk" in pg.url, pg.url.split("8090")[-1])
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        cek("Esc mengosongkan kata kunci", "q=" not in pg.url and kartu(pg) == 3, pg.url.split("8090")[-1])
        pg.goto(f"{BASE}/berita/index.html?q=hujan&kategori=kesehatan", wait_until="load"); pg.wait_for_timeout(1300)
        pg.click("#resetFilterBerita"); pg.wait_for_timeout(600)
        cek("tombol Reset mengembalikan tanpa filter", kartu(pg) == 12 and "?" not in pg.url, pg.url.split("8090")[-1])

        # --- 3. Paginasi -----------------------------------------------------
        print("\n  3) Paginasi")
        pg.goto(f"{BASE}/berita/index.html", wait_until="load"); pg.wait_for_timeout(1400)
        href2 = pg.evaluate("()=>document.querySelector('#paginasiBerita a[data-hal=\"2\"]').getAttribute('href')")
        cek("tautan halaman 2 punya href nyata", "halaman=2" in (href2 or ""), f"href={href2}")
        pg.click('#paginasiBerita a[data-hal="2"]'); pg.wait_for_timeout(700)
        aktif = pg.evaluate("()=>{const e=document.querySelector('#paginasiBerita .page-item.active');return e?e.textContent.trim():'';}")
        cek("halaman 2 menampilkan sisa artikel", kartu(pg) == 1 and aktif == "2" and "halaman=2" in pg.url,
            f"{kartu(pg)} kartu · aktif={aktif}")
        cek("halaman 2 bukan duplikat kanonik halaman 1",
            pg.evaluate("()=>{const l=document.querySelector('link[rel=canonical]');return !!l && !/halaman=2/.test(l.href);}"),
            pg.evaluate("()=>document.querySelector('link[rel=canonical]')?.href || '-'"))

        # --- 4. Hasil lintas jenis -------------------------------------------
        print("\n  4) Hasil lain (wisata/kuliner/UMKM) saat kata kunci cocok")
        pg.goto(f"{BASE}/berita/index.html?q=tempe", wait_until="load"); pg.wait_for_timeout(1300)
        tampil = pg.evaluate("()=>{const e=document.getElementById('blokHasilLain');return !!e && !e.classList.contains('d-none');}")
        cek("blok hasil lain muncul & terisi", tampil and kartu(pg, "#hasilLain .info-box") >= 1,
            f"{kartu(pg,'#hasilLain .info-box')} kartu")
        pg.goto(f"{BASE}/berita/index.html?q=zzz-tidak-ada", wait_until="load"); pg.wait_for_timeout(1200)
        kosong = pg.evaluate("()=>{const e=document.getElementById('blokHasilLain');return !e || e.classList.contains('d-none') || e.querySelectorAll('.info-box').length===0;}")
        cek("blok hasil lain disembunyikan saat tak ada padanan", kosong)

        # --- 5. Jembatan /berita/detail.html?slug=… ---------------------------
        print("\n  5) Jembatan URL lama (3 jalur)")
        pg.goto(f"{BASE}/berita/detail.html?slug=bmkg-pasuruan-hujan-sore-sepekan", wait_until="load"); pg.wait_for_timeout(1500)
        cek("slug valid → berpindah ke artikel", "/berita/bmkg-pasuruan-hujan-sore-sepekan" in pg.url and "detail.html" not in pg.url,
            pg.url.split("8090")[-1])
        pg.goto(f"{BASE}/berita/detail.html?slug=artikel-yang-tidak-ada", wait_until="load"); pg.wait_for_timeout(1200)
        teks = pg.evaluate("()=>(document.querySelector('#jembatan')?.innerText||'').replace(/\\s+/g,' ')")
        cek("slug tak dikenal → pesan ramah (bukan 404/buntu)",
            "tidak ditemukan" in teks.lower() and kartu(pg, ".jembatan-daftar a") >= 4, teks[:64])
        pg.goto(f"{BASE}/berita/detail.html", wait_until="load"); pg.wait_for_timeout(1400)
        cek("tanpa slug → diarahkan ke indeks berita", "/berita/index.html" in pg.url, pg.url.split("8090")[-1])
        pg.goto(f"{BASE}/berita/detail.html?slug=artikel-yang-tidak-ada", wait_until="load"); pg.wait_for_timeout(900)
        cek("jembatan tetap noindex (tidak jadi halaman duplikat)",
            pg.evaluate("()=>(document.querySelector('meta[name=robots]')?.content||'').includes('noindex')"))

        # --- 6. Navigasi antar-artikel + aksesibilitas ------------------------
        print("\n  6) Detail: navigasi antar-artikel, target sentuh, kontras")
        pg.goto(f"{BASE}/berita/jadwal-posyandu-pandaan-november-2026.html", wait_until="load"); pg.wait_for_timeout(1300)
        arah = pg.evaluate("()=>Array.from(document.querySelectorAll('.nav-berita-arah')).map(e=>e.textContent.trim())")
        cek("artikel tengah punya prev + next", len(arah) == 2, str(arah))
        pg.goto(f"{BASE}/berita/bmkg-pasuruan-hujan-sore-sepekan.html", wait_until="load"); pg.wait_for_timeout(1200)
        cek("artikel terbaru hanya punya satu tetangga",
            pg.evaluate("()=>document.querySelectorAll('.nav-berita-item').length") == 1)
        ukuran = pg.evaluate("""()=>Array.from(document.querySelectorAll('.nav-berita-item'))
            .map(e=>Math.round(e.getBoundingClientRect().height))""")
        cek("target sentuh navigasi ≥ 44 px", all(h >= 44 for h in ukuran) if ukuran else True, f"tinggi={ukuran}")
        kontras = pg.evaluate("""()=>{
            const el=document.querySelector('.nav-berita-arah'); if(!el) return null;
            const rgb=s=>{const m=s.match(/\\d+/g).map(Number);const f=c=>{c/=255;return c<=.03928?c/12.92:Math.pow((c+.055)/1.055,2.4)};
              return .2126*f(m[0])+.7152*f(m[1])+.0722*f(m[2])};
            const L1=rgb(getComputedStyle(el).color), L2=rgb(getComputedStyle(document.body).backgroundColor||'rgb(255,255,255)');
            const a=Math.max(L1,L2), b=Math.min(L1,L2); return +( (a+.05)/(b+.05) ).toFixed(2);}""")
        cek("teks label navigasi kontras ≥ 4,5:1", kontras is None or kontras >= 4.5, f"rasio={kontras}")

        # Daftar isi + bar progres baca (tata letak artikel majalah)
        toc = pg.evaluate("()=>document.querySelectorAll('[data-toc-link]').length")
        cek("artikel punya daftar isi + tautan jangkar", toc >= 1, f"{toc} tautan")
        pg.evaluate("()=>window.scrollTo(0, document.body.scrollHeight * 0.6)")
        pg.wait_for_timeout(500)
        lebar = pg.evaluate("()=>{const b=document.querySelector('[data-progress-baca]');return b?parseFloat(b.style.width||'0'):null;}")
        cek("bar progres baca bertambah saat digulir", lebar is not None and lebar > 5, f"lebar={lebar}%")
        aktif = pg.evaluate("()=>Array.from(document.querySelectorAll('[data-toc-link].aktif')).length")
        cek("scrollspy daftar isi menandai bagian aktif", aktif >= 1, f"{aktif} aktif")

        # --- 7. SEO/struktur halaman berita ----------------------------------
        print("\n  7) SEO halaman berita")
        pg.goto(f"{BASE}/berita/index.html", wait_until="load"); pg.wait_for_timeout(1200)
        ld = pg.evaluate("""()=>Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
            .map(s=>{try{return JSON.parse(s.textContent)}catch(e){return null}}).filter(Boolean)""")
        halaman = next((d for d in ld if d.get("@type") == "CollectionPage"), {})
        itemlist = (halaman.get("mainEntity") or {})
        n_item = len(itemlist.get("itemListElement") or [])
        cek("indeks: JSON-LD CollectionPage + ItemList(13 berita) + BreadcrumbList",
            itemlist.get("@type") == "ItemList" and n_item == 13 and any(d.get("@type") == "BreadcrumbList" for d in ld),
            f"ItemList bersarang di mainEntity: {n_item} butir · BreadcrumbList: {any(d.get('@type')=='BreadcrumbList' for d in ld)}")
        cek("indeks: setiap butir ItemList punya URL absolut",
            all(str(i.get("url", "")).startswith("https://") for i in (itemlist.get("itemListElement") or [])),
            (itemlist.get("itemListElement") or [{}])[0].get("url", "-"))
        cek("indeks: tepat satu H1",
            pg.evaluate("()=>document.querySelectorAll('h1').length") == 1)
        pg.goto(f"{BASE}/berita/kripik-tempe-pandaan-tembus-pasar-malaysia", wait_until="load"); pg.wait_for_timeout(1200)
        cek("URL bersih dimuat sebagai artikel (mesin pencari/tautan luar)",
            pg.evaluate("()=>document.querySelectorAll('h1').length") == 1,
            pg.evaluate("()=>(document.querySelector('h1')?.textContent||'').trim().slice(0,48)"))
        cek("tidak ada sisa animasi AOS (perpustakaan sudah dihapus)",
            pg.evaluate("()=>document.querySelectorAll('[data-aos]').length") == 0)

        sisa_err = [e for e in errs if "404" not in e or "assets" not in e]
        print("\n  ── Ringkasan ──")
        print(f"  lulus {len(lulus)} · gagal {len(gagal)} · galat konsol {len(errs)} · respons ≥400 {len(http_buruk)}")
        for x in errs[:4]:
            print("   ⚠ konsol:", x[:120])
        for x in http_buruk[:4]:
            print("   ⚠ http:", x[:120])
        b.close()
    return len(gagal)


if __name__ == "__main__":
    sys.exit(1 if jalankan() else 0)
