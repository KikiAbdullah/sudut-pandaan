/* ==========================================================================
   NAVIGASI MODEL indonesia.travel
   - navbar bening di atas hero → memutih setelah digulir (.nav-scrolled)
   - panel pencarian overlay (buka/tutup, Esc, fokus terjaga)
   - bilah pencarian di bawah navbar (beranda) ikut memutih saat digulir
   - tanpa dark mode, tanpa animasi yang melanggar prefers-reduced-motion
   ========================================================================== */
(function () {
  'use strict';

  var navbar = document.getElementById('navbarUtama');
  var panel = document.getElementById('panelCari');
  var tombol = document.getElementById('tombolCari');
  var tutup = document.getElementById('tutupCari');
  var input = document.getElementById('inputCari');
  var barisCari = document.querySelector('.sp-cari-baris');
  var fokusSebelum = null;

  /* ---------- 1. Status gulir ---------- */
  function saatGulir() {
    var y = window.scrollY || window.pageYOffset || 0;
    var ambang = 60;
    if (navbar) navbar.classList.toggle('nav-scrolled', y > ambang);
    if (barisCari) barisCari.classList.toggle('memutih', y > ambang);
  }
  var menunggu = false;
  window.addEventListener('scroll', function () {
    if (menunggu) return;
    menunggu = true;
    requestAnimationFrame(function () { menunggu = false; saatGulir(); });
  }, { passive: true });
  saatGulir();

  /* ---------- 2. Panel pencarian ---------- */
  function buka() {
    if (!panel) return;
    fokusSebelum = document.activeElement;
    panel.classList.add('terbuka');
    if (tombol) tombol.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    if (input) setTimeout(function () { input.focus(); }, 30);
  }
  function tutupPanel() {
    if (!panel || !panel.classList.contains('terbuka')) return;
    panel.classList.remove('terbuka');
    if (tombol) tombol.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    if (fokusSebelum && fokusSebelum.focus) fokusSebelum.focus();
  }
  if (tombol) tombol.addEventListener('click', buka);
  if (tutup) tutup.addEventListener('click', tutupPanel);
  if (panel) {
    panel.addEventListener('click', function (e) { if (e.target === panel) tutupPanel(); });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') tutupPanel();
    // Pintasan "/" kini milik panel lompat cepat (assets/js/majalah.js) supaya
    // tidak ada dua panel yang terbuka bersamaan. Pencarian situs tetap bisa
    // dibuka lewat ikon kaca pembesar di navbar.
  });

  /* ---------- 3. Bilah pencarian di bawah navbar (beranda) ---------- */
  if (barisCari) {
    var formBilah = barisCari.querySelector('form');
    if (formBilah) {
      formBilah.addEventListener('submit', function (e) {
        var q = (formBilah.querySelector('input[name="q"]') || {}).value || '';
        if (!q.trim()) { e.preventDefault(); buka(); }
      });
    }
  }

  /* ---------- 4. Dropdown navigasi: bisa dioperasikan keyboard ---------- */
  if (navbar) {
    navbar.querySelectorAll('.dropdown').forEach(function (dd) {
      dd.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
          var t = dd.querySelector('.dropdown-toggle');
          if (t) { t.blur(); }
        }
      });
    });
  }

  /* ---------- 5. Tautan jangkar aktif otomatis pada nav ---------- */
  var tautan = Array.prototype.slice.call(document.querySelectorAll('.sp-navbar .nav-link'));
  if (tautan.length) {
    tautan.forEach(function (a) {
      var url = a.getAttribute('href') || '';
      if (url.replace(/\.html$/, '').replace(/^.*\//, '') === location.pathname.replace(/\.html$/, '').replace(/\/$/, '').replace(/^.*\//, '')) {
        // hanya tandai bila belum ada penanda dari generator
        if (!document.querySelector('.sp-navbar .nav-link.active')) a.classList.add('active');
      }
    });
  }
})();
