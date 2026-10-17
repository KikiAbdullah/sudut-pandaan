/* ==========================================================================
   MAJALAH — perilaku khas tata letak "Majalah + Bento"
   1) Rail        : mengaktifkan tombol geser pada .rail (tanpa pustaka)
   2) Lompat cepat: panel pencarian halaman + pintasan "/" atau Ctrl+K
   3) Daftar isi  : TOC otomatis dari h2 ber-id + scrollspy + bilah progres baca
   4) Tahun       : mengisi [data-tahun] di footer
   Semua progresif: tanpa JS situs tetap terbaca dan bisa digeser dengan jari.
   ========================================================================== */
(function () {
  'use strict';

  var kurangiGerak = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ================= 1. RAIL (bilah geser horizontal) ================= */
  function siapkanRail() {
    var rails = document.querySelectorAll('[data-rail]');
    if (!rails.length) return;

    Array.prototype.forEach.call(rails, function (rail) {
      var track = rail.querySelector('.rail-track');
      var mundur = rail.querySelector('[data-rail-mundur]');
      var maju = rail.querySelector('[data-rail-maju]');
      if (!track) return;

      function langkah() {
        // Geser sebanyak lebar satu kartu + jarak antar kartu, bukan satu layar
        var item = track.querySelector('.rail-item, .tile, > *');
        var lebar = item ? item.getBoundingClientRect().width : track.clientWidth * 0.8;
        return Math.max(160, lebar + 16);
      }

      function perbarui() {
        var bisaGeser = track.scrollWidth - track.clientWidth > 8;
        if (!bisaGeser) { rail.setAttribute('data-tanpa-nav', ''); return; }
        rail.removeAttribute('data-tanpa-nav');
        var kiri = track.scrollLeft > 4;
        var kanan = track.scrollLeft < track.scrollWidth - track.clientWidth - 4;
        if (mundur) { mundur.disabled = !kiri; }
        if (maju) { maju.disabled = !kanan; }
      }

      function geser(arah) {
        track.scrollBy({
          left: arah * langkah(),
          behavior: kurangiGerak ? 'auto' : 'smooth'
        });
      }

      if (mundur) mundur.addEventListener('click', function () { geser(-1); });
      if (maju) maju.addEventListener('click', function () { geser(1); });

      track.addEventListener('scroll', function () { window.requestAnimationFrame(perbarui); }, { passive: true });
      window.addEventListener('resize', perbarui);
      // Setelah data JSON selesai dirender (SP_PAGES memicu event ini)
      document.addEventListener('sp:rendered', function () { setTimeout(perbarui, 60); });
      setTimeout(perbarui, 120);
    });
  }

  /* ================= 2. PANEL LOMPAT CEPAT ================= */
  var HALAMAN = [
    ['Beranda', 'index.html', 'ph-house', 'Halaman utama'],
    ['Berita', 'berita/index.html', 'ph-newspaper', 'Indeks berita + filter'],
    ['Wisata', 'wisata/index.html', 'ph-mountains', 'Destinasi Pandaan'],
    ['Kuliner', 'kuliner/index.html', 'ph-bowl-food', 'Warung & oleh-oleh'],
    ['UMKM', 'umkm/index.html', 'ph-storefront', 'Direktori usaha warga'],
    ['Daftarkan UMKM', 'umkm/daftar.html', 'ph-pencil-simple', 'Formulir gratis'],
    ['Info Lalu Lintas', 'layanan/lalu-lintas.html', 'ph-traffic-signal', 'Status jalan'],
    ['Agenda', 'layanan/agenda.html', 'ph-calendar-dots', 'Acara mendatang'],
    ['Lowongan Kerja', 'layanan/loker.html', 'ph-briefcase', 'Loker sekitar'],
    ['Nomor Penting', 'layanan/nomor-penting.html', 'ph-phone-call', 'Kontak darurat'],
    ['Lapor / Kirim Info', 'layanan/lapor.html', 'ph-paper-plane-tilt', 'Kirim ke redaksi'],
    ['Panduan Warga', 'panduan/index.html', 'ph-book-open-text', 'Panduan praktis'],
    ['Peta Pandaan', 'peta.html', 'ph-map-trifold', 'Titik penting'],
    ['Tentang Kami', 'tentang.html', 'ph-info', 'Redaksi & sumber data'],
    ['Kontak', 'kontak.html', 'ph-envelope-simple', 'Hubungi kami'],
    ['Pasang Iklan', 'iklan.html', 'ph-megaphone', 'Media kit'],
    ['Kebijakan Privasi', 'privacy.html', 'ph-shield-check', 'Data & privasi'],
    ['Semua Tautan', 'link/index.html', 'ph-link-simple', 'Link bio'],
    ['Instagram', 'https://www.instagram.com/sudutpandaan', 'ph-instagram-logo', 'Eksternal'],
    ['Threads', 'https://www.threads.net/@sudutpandaan', 'ph-threads-logo', 'Eksternal'],
    ['WhatsApp Redaksi', 'https://wa.me/6281553500855', 'ph-whatsapp-logo', 'Eksternal']
  ];

  function panelLompat() {
    if (document.querySelector('.panel-lompat')) return;

    var dasar = (window.SP && SP.url) ? '' : '';
    var kotak = document.createElement('div');
    kotak.className = 'panel-lompat';
    kotak.setAttribute('role', 'dialog');
    kotak.setAttribute('aria-modal', 'true');
    kotak.setAttribute('aria-label', 'Lompat cepat antar halaman');
    kotak.innerHTML =
      '<div class="panel-lompat-kotak">' +
      '  <form role="search" onsubmit="return false">' +
      '    <i class="ph ph-magnifying-glass fs-4" aria-hidden="true"></i>' +
      '    <label class="visually-hidden" for="inputLompat">Cari halaman</label>' +
      '    <input id="inputLompat" type="search" placeholder="Cari halaman, layanan, atau destinasi…" autocomplete="off">' +
      '    <button type="button" class="btn btn-sm btn-outline-navy" data-lompat-tutup aria-label="Tutup panel">Esc</button>' +
      '  </form>' +
      '  <div class="panel-lompat-daftar" id="daftarLompat" role="listbox" aria-label="Daftar halaman"></div>' +
      '  <div class="panel-lompat-kaki"><span><kbd>/</kbd> atau <kbd>Ctrl</kbd>+<kbd>K</kbd> untuk membuka</span>' +
      '    <span><kbd>&uarr;</kbd><kbd>&darr;</kbd> pilih, <kbd>Enter</kbd> buka, <kbd>Esc</kbd> tutup</span></div>' +
      '</div>';
    document.body.appendChild(kotak);

    var input = kotak.querySelector('#inputLompat');
    var daftar = kotak.querySelector('#daftarLompat');
    var hasil = HALAMAN.slice();
    var pilih = 0;
    var fokusSebelum = null;

    function tautan(h) {
      var luar = /^https?:/.test(h[1]);
      return {
        url: luar ? h[1] : (window.SP && SP.url ? SP.url(h[1]) : h[1]),
        luar: luar, nama: h[0], ikon: h[2], ket: h[3]
      };
    }

    // Peta konten (berita/wisata/kuliner/umkm) dimuat sekali, dari sematan build
    var konten = null;
    function muatKonten() {
      if (konten || !(window.SP_UI && SP_UI.loadData)) return;
      SP_UI.loadData().then(function (d) {
        konten = [];
        var kelompok = [['berita', 'berita/', 'ph-newspaper', 'Berita'],
                        ['wisata', 'wisata/', 'ph-mountains', 'Wisata'],
                        ['kuliner', 'kuliner/', 'ph-bowl-food', 'Kuliner'],
                        ['umkm', 'umkm/', 'ph-storefront', 'UMKM']];
        kelompok.forEach(function (g) {
          (SP_UI.items(d[g[0]]) || []).forEach(function (it) {
            var nama = it.nama || it.judul || it.nama_usaha || '';
            if (!nama) return;
            konten.push({
              nama: nama, url: (SP.url ? SP.url(g[1] + it.slug + '.html') : g[1] + it.slug + '.html'),
              ikon: g[2], ket: g[3] + (it.desa ? ' · ' + it.desa : (it.kategori ? ' · ' + it.kategori : (it.kategori_slug ? ' · ' + it.kategori_slug : ''))),
              isi: (nama + ' ' + (it.ringkasan || '') + ' ' + (it.desa || '') + ' ' + (it.kategori || '') + ' ' + (it.nama_usaha || '')).toLowerCase()
            });
          });
        });
      });
    }

    function gambarLagi(q) {
      var kata = (q || '').toLowerCase().trim();
      hasil = HALAMAN.filter(function (h) {
        return !kata || (h[0] + ' ' + h[3] + ' ' + h[1]).toLowerCase().indexOf(kata) > -1;
      });
      var hasilKonten = [];
      if (kata.length > 2 && konten) {
        hasilKonten = konten.filter(function (k) { return k.isi.indexOf(kata) > -1; }).slice(0, 6);
      }
      pilih = 0;
      var html = '';
      if (hasil.length) {
        html += hasil.map(function (h, i) {
          var t = tautan(h);
          return '<a href="' + t.url + '" role="option" aria-selected="' + (i === 0) + '" data-i="' + i + '"' +
            (t.luar ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' +
            '<i class="ph ' + t.ikon + '" aria-hidden="true"></i>' +
            '<span>' + SP_UI.esc(h[0]) + ' <small class="d-block">' + SP_UI.esc(h[3]) + '</small></span></a>';
        }).join('');
      }
      if (hasilKonten.length) {
        html += '<p class="tile-kicker px-3 pt-3 pb-1 mb-0">Dari isi situs</p>' +
          hasilKonten.map(function (k, i) {
            var idx = hasil.length + i;
            return '<a href="' + k.url + '" role="option" aria-selected="false" data-i="' + idx + '">' +
              '<i class="ph ' + k.ikon + '" aria-hidden="true"></i>' +
              '<span>' + SP_UI.esc(k.nama) + ' <small class="d-block">' + SP_UI.esc(k.ket) + '</small></span></a>';
          }).join('');
      }
      if (!html) {
        html = '<p class="tile-teks p-3 mb-0">Tidak ada hasil untuk “' + SP_UI.esc(kata) +
          '”. Coba kata lain, misalnya “candra”, “loker”, atau “peta”.</p>';
      }
      daftar.innerHTML = html;
      semua = hasil.concat(hasilKonten);
    }

    // Daftar gabungan (halaman + konten) untuk navigasi tombol panah
    var semua = [];

    function tandai() {
      Array.prototype.forEach.call(daftar.querySelectorAll('a'), function (a, i) {
        var aktif = i === pilih;
        a.setAttribute('aria-selected', aktif ? 'true' : 'false');
        a.classList.toggle('aktif', aktif);
        if (aktif) a.style.background = 'var(--sp-krem-2)';
        else a.style.background = '';
      });
    }

    function buka() {
      if (kotak.classList.contains('terbuka')) return;
      fokusSebelum = document.activeElement;
      kotak.classList.add('terbuka');
      document.body.style.overflow = 'hidden';
      muatKonten();
      gambarLagi('');
      input.value = '';
      input.focus();
      tandai();
      // Bila dibuka dari menu offcanvas, Bootstrap mengembalikan fokus setelah
      // animasi tutup (±300 ms) → tegaskan fokus ke kolom pencarian lagi.
      setTimeout(function () { if (kotak.classList.contains('terbuka')) input.focus(); }, 360);
    }

    function tutup() {
      kotak.classList.remove('terbuka');
      document.body.style.overflow = '';
      if (fokusSebelum && fokusSebelum.focus) fokusSebelum.focus();
    }

    input.addEventListener('input', function () { gambarLagi(input.value); tandai(); });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); pilih = Math.min(pilih + 1, semua.length - 1); tandai(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); pilih = Math.max(pilih - 1, 0); tandai(); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        var target = semua[pilih];
        if (target) window.location.href = target.url || tautan(target).url;
      }
    });

    kotak.addEventListener('click', function (e) {
      if (e.target === kotak || e.target.closest('[data-lompat-tutup]')) tutup();
    });

    document.addEventListener('keydown', function (e) {
      var diForm = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || '');
      if (e.key === 'Escape' && kotak.classList.contains('terbuka')) { tutup(); return; }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); buka(); return; }
      if (e.key === '/' && !diForm && !kotak.classList.contains('terbuka')) { e.preventDefault(); buka(); }
    });

    // Tombol pemicu opsional di navbar/footer
    Array.prototype.forEach.call(document.querySelectorAll('[data-lompat-buka]'), function (b) {
      b.addEventListener('click', function (e) { e.preventDefault(); buka(); });
    });
  }

  /* ================= 3. DAFTAR ISI + PROGRES BACA ================= */
  function daftarIsi() {
    var artikel = document.querySelector('[data-artikel], .sp-artikel, article.sp-isi');
    var bar = document.querySelector('[data-progress-baca]');
    var kotakToc = document.querySelector('[data-toc]');
    var judul = artikel ? artikel.querySelectorAll('h2[id]') : [];

    function updateBar() {
      if (!bar) return;
      var h = document.documentElement.scrollHeight - window.innerHeight;
      var p = h > 0 ? (window.scrollY / h) * 100 : 0;
      bar.style.width = Math.max(0, Math.min(100, p)).toFixed(2) + '%';
      if (bar.parentNode && bar.parentNode.hasAttribute && bar.parentNode.hasAttribute('aria-valuenow')) {
        bar.parentNode.setAttribute('aria-valuenow', Math.round(p));
      }
    }

    if (bar) {
      var menunggu = false;
      window.addEventListener('scroll', function () {
        if (menunggu) return;
        menunggu = true;
        window.requestAnimationFrame(function () { menunggu = false; updateBar(); });
      }, { passive: true });
      window.addEventListener('resize', updateBar);
      updateBar();
    }

    if (kotakToc && judul.length) {
      kotakToc.innerHTML = '<h2>Isi Artikel</h2><ol>' +
        Array.prototype.map.call(judul, function (h, i) {
          if (!h.id) h.id = 'bagian-' + (i + 1);
          var teks = (h.textContent || '').replace(/\s+/g, ' ').trim();
          return '<li><a href="#' + h.id + '" data-toc-link="' + h.id + '">' + teks + '</a></li>';
        }).join('') + '</ol>';
    }

    var tautanToc = document.querySelectorAll('[data-toc-link]');
    if (!tautanToc.length) return;

    function sorot() {
      var posisi = window.scrollY + 140;
      var aktif = judul[0];
      Array.prototype.forEach.call(judul, function (h) {
        if (h.offsetTop <= posisi) aktif = h;
      });
      Array.prototype.forEach.call(tautanToc, function (a) {
        var nyala = aktif && a.getAttribute('data-toc-link') === aktif.id;
        a.classList.toggle('aktif', nyala);
        if (nyala) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
      });
    }

    var tunggu = false;
    window.addEventListener('scroll', function () {
      if (tunggu) return;
      tunggu = true;
      window.requestAnimationFrame(function () { tunggu = false; sorot(); });
    }, { passive: true });
    sorot();
  }

  /* ================= 4. TAHUN DI FOOTER ================= */
  function tahun() {
    var kini = new Date().getFullYear();
    Array.prototype.forEach.call(document.querySelectorAll('[data-tahun]'), function (el) {
      el.textContent = String(kini);
    });
  }

  function mulai() {
    siapkanRail();
    panelLompat();
    daftarIsi();
    tahun();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(mulai, 0); });
  } else {
    setTimeout(mulai, 0);
  }
  document.addEventListener('sp:rendered', function () {
    // Data JSON selesai dirender → perbarui status rail
    siapkanRail();
  });
})();
