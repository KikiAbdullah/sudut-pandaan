/* ==========================================================================
   Sudut Pandaan — main.js
   Inisialisasi global: slider hero, counter, back-to-top, notifikasi info
   (breaking bar), lightbox, tahun footer, dan pemuatan peta tertunda.
   Catatan: situs selalu terang — tidak ada toggle tema, dan animasi AOS sudah
   dibuang karena tidak ada markup yang memakainya.
   ========================================================================== */
(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------ breaking ------------------------------ */
  function initBreaking() {
    var bar = document.getElementById('breakingBar');
    if (!bar) return;
    var kedaluwarsa = bar.getAttribute('data-expires');
    if (kedaluwarsa && new Date(kedaluwarsa) < new Date()) { bar.remove(); return; }
    var kunci = SP.key.breakingTutup;
    try { if (sessionStorage.getItem(kunci) === '1') { bar.remove(); return; } } catch (e) { }
    var tutup = bar.querySelector('[data-dismiss-breaking]');
    if (tutup) tutup.addEventListener('click', function () {
      bar.remove();
      try { sessionStorage.setItem(kunci, '1'); } catch (e) { }
    });
  }

  /* ------------------------------- counter ------------------------------ */
  function initCounter() {
    var counters = document.querySelectorAll('[data-counter]');
    if (!counters.length) return;
    if (reduced || !('IntersectionObserver' in window)) {
      counters.forEach(function (c) { c.textContent = Number(c.dataset.counter).toLocaleString('id-ID'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target, akhir = +el.dataset.counter, durasi = 1100, t0 = performance.now();
        (function tick(t) {
          var p = Math.min((t - t0) / durasi, 1);
          var nilai = Math.floor(akhir * (1 - Math.pow(1 - p, 3)));   // ease-out
          el.textContent = nilai.toLocaleString('id-ID');
          if (p < 1) requestAnimationFrame(tick);
        })(t0);
        io.unobserve(el);
      });
    }, { threshold: 0.4 });
    counters.forEach(function (c) { io.observe(c); });
  }

  /* -------------------------------- swiper ------------------------------ */
  // Pustaka Swiper dimuat SETELAH halaman tenang (idle). Alasannya: evaluasi
  // swiper-bundle.min.js memakan ±750 ms CPU (terukur Lighthouse) dan itu
  // menambah Total Blocking Time beranda. Tanpa Swiper pun tata letak sudah
  // benar: CSS Swiper membuat tiap slide selebar kontainer (slide 1 terlihat),
  // dan korsel destinasi bisa digeser dengan gesekan native (scroll-snap).
  var swiperSedangDimuat = null;
  function muatSwiper(cb) {
    if (window.Swiper) { cb(); return; }
    if (swiperSedangDimuat) { swiperSedangDimuat.push(cb); return; }
    swiperSedangDimuat = [cb];
    var sc = document.createElement('script');
    sc.src = SP.url('assets/vendor/swiper-bundle.min.js');
    sc.onload = function () {
      var daftar = swiperSedangDimuat || [];
      swiperSedangDimuat = null;
      daftar.forEach(function (f) { try { f(); } catch (e) { /* biarkan halaman tetap jalan */ } });
    };
    sc.onerror = function () { swiperSedangDimuat = null; };   // tanpa Swiper: tetap geser manual
    document.head.appendChild(sc);
  }

  function initKorsel() {
    if (!document.querySelector('.hero-swiper') && !document.querySelector('.destinasi-swiper')) return;
    muatSwiper(function () {
      initHero();
      initDestinasi();
    });
  }

  function initDestinasi() {
    var el = document.querySelector('.destinasi-swiper');
    if (!window.Swiper || !el || el.swiper) return;
    new Swiper(el, {
      slidesPerView: 1.1, spaceBetween: 16, watchOverflow: true, loop: false, speed: 500,
      breakpoints: { 576: { slidesPerView: 2 }, 992: { slidesPerView: 3 } },
      pagination: { el: '.destinasi-pagination', clickable: true },
      a11y: { enabled: true }
    });
  }

  function initHero() {
    if (!window.Swiper || !document.querySelector('.hero-swiper')) return;
    if (document.querySelector('.hero-swiper').swiper) return;      // idempoten
    new Swiper('.hero-swiper', {
      // loop: false — mode loop menggandakan slide (DOM & gambar bertambah),
      // menaikkan TBT dan membuat gambar slide kedua ikut terunduh.
      loop: false,
      speed: 650,
      autoplay: reduced ? false : { delay: 7000, pauseOnMouseEnter: true, disableOnInteraction: false },
      pagination: { el: '.hero-swiper .swiper-pagination', clickable: true },
      navigation: { nextEl: '.hero-swiper .swiper-button-next', prevEl: '.hero-swiper .swiper-button-prev' },
      a11y: { enabled: true, prevSlideMessage: 'Slide sebelumnya', nextSlideMessage: 'Slide berikutnya' },
      keyboard: { enabled: true }
    });
  }

  /* --------------------- peta: pemuatan tertunda ------------------------- */
  // Halaman detail & beranda tidak memuat Leaflet di jalur kritis: pustaka peta
  // diunduh saat kotak peta mendekati viewport (rootMargin 400px).
  function saatIdle(fn) {
    if ('requestIdleCallback' in window) requestIdleCallback(fn, { timeout: 1500 });
    else setTimeout(fn, 1);
  }

  function initPetaTertunda() {
    var el = document.getElementById('peta');
    if (!el || window.L) return;

    function muat() {
      if (window.__spPetaDimuat) return;
      window.__spPetaDimuat = true;
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = SP.url('assets/vendor/leaflet/leaflet.css');
      document.head.appendChild(css);
      var js = document.createElement('script');
      js.src = SP.url('assets/vendor/leaflet/leaflet.js');
      js.onload = function () {
        var mjs = document.createElement('script');
        mjs.src = SP.url('assets/js/map.js');
        mjs.onload = function () { if (window.SP_MAP) window.SP_MAP.init(); };
        document.body.appendChild(mjs);
      };
      document.body.appendChild(js);
    }

    if (!('IntersectionObserver' in window)) { saatIdle(muat); return; }
    var io = new IntersectionObserver(function (entri) {
      entri.forEach(function (e) { if (e.isIntersecting) { io.disconnect(); saatIdle(muat); } });
    }, { rootMargin: '400px 0px' });
    io.observe(el);
  }

  /* ------------------------------ back to top --------------------------- */
  function initBackToTop() {
    var btn = document.getElementById('backToTop');
    if (!btn) return;
    window.addEventListener('scroll', function () {
      btn.classList.toggle('show', window.scrollY > 600);
    }, { passive: true });
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
    });
  }

  /* -------------------------------- lightbox ---------------------------- */
  function initLightbox() {
    if (!window.Lightbox || !window.Lightbox.initialize) return;
    document.querySelectorAll('[data-toggle="lightbox"]').forEach(function (el) {
      if (el.getAttribute('data-lb-ready') === '1') return;
      el.setAttribute('data-lb-ready', '1');
      el.addEventListener('click', window.Lightbox.initialize);
    });
  }

  /* ------------------------------ tahun footer -------------------------- */
  function initTahun() {
    var el = document.getElementById('tahun');
    if (el) el.textContent = new Date().getFullYear();
  }

  /* ------------------------------- navbar ------------------------------- */
  function initNavbar() {
    var nav = document.querySelector('.sp-navbar');
    if (!nav) return;
    window.addEventListener('scroll', function () {
      nav.classList.toggle('shadow-sm', window.scrollY > 8);
    }, { passive: true });
  }

  /* --------------------------------- init ------------------------------- */
  var sudahInit = false;

  function initSemua() {
    if (sudahInit) return;          // cegah inisialisasi ganda (Swiper/AOS)
    sudahInit = true;
    initBreaking();
    initCounter();
    initHero();
    initBackToTop();
    initNavbar();
    initLightbox();
    initTahun();
    initPetaTertunda();
    saatIdle(initKorsel);
  }

  document.addEventListener('sp:rendered', function () {
    if (sudahInit) {           // konten baru dirender → segarkan lightbox & korsel
      initLightbox();
      saatIdle(initKorsel);
      return;
    }
    initSemua();
  });

  document.addEventListener('DOMContentLoaded', function () {
    // Fallback: bila pages.js tidak memicu 'sp:rendered' (mis. data gagal dimuat),
    // UI dasar tetap berjalan setelah jeda singkat.
    setTimeout(initSemua, 1200);
  });
})();
