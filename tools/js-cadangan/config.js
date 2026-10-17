/* ==========================================================================
   Sudut Pandaan — config.js
   Konfigurasi situs + utilitas dasar. Dimuat paling awal (sebelum komponen).
   ========================================================================== */
window.SP = (function () {
  'use strict';

  // Tentukan "base path" relatif terhadap root situs, berdasarkan lokasi file ini.
  // Root → '', subfolder → '../' sehingga aset & link tetap benar saat dibuka
  // dari file:// maupun di-hosting pada subdirektori.
  var self = document.querySelector('script[src*="assets/js/config.js"]');
  var base = '';
  if (self) {
    base = (self.getAttribute('src') || '').replace(/assets\/js\/config\.js.*$/, '');
  }

  /** Apakah sebuah path berupa tautan luar (http, protokol-relatif, atau data-URI)? */
  function luar(path) {
    return /^(https?:)?\/\/|^data:/i.test(String(path == null ? '' : path));
  }

  /** URL absolut (luar) dibiarkan apa adanya; path lokal diberi awalan base. */
  function internal(path) {
    return base + String(path).replace(/^\//, '');
  }

  /* ------------------------------- IKON ---------------------------------
     Semua ikon memakai Phosphor Icons (https://phosphoricons.com). Nama lama
     dari Bootstrap Icons dipetakan lewat ALIAS_IKON supaya pemanggil lama
     (mis. SP.ico('search')) tetap jalan tanpa diubah.                     */
  var ALIAS_IKON = {
    // pencarian & navigasi
    search: 'magnifying-glass', 'geo-alt': 'map-pin', geo: 'map-pin', map: 'map-trifold',
    'arrow-right': 'arrow-right', 'arrow-left': 'arrow-left', 'arrow-up': 'arrow-up',
    // status & verifikasi
    'patch-check': 'seal-check', 'patch-check-fill': 'seal-check', 'check-circle': 'check-circle',
    'exclamation-circle': 'warning-circle', 'exclamation-triangle': 'warning',
    'info-circle': 'info', 'shield-check': 'shield-check', 'shield-warning': 'shield-warning',
    // waktu & kalender
    clock: 'clock', 'calendar-event': 'calendar-dots', 'calendar-check': 'calendar-check',
    'calendar-x': 'calendar-x', 'calendar-plus': 'calendar-plus', 'hourglass-split': 'hourglass-medium',
    'clock-counter-clockwise': 'clock-counter-clockwise',
    // orang & tempat
    person: 'user', 'person-circle': 'user-circle', people: 'users', shop: 'storefront',
    // lain-lain
    inbox: 'tray', 'clipboard-check': 'list-checks', 'list-checks': 'list-checks',
    newspaper: 'newspaper', briefcase: 'briefcase', envelope: 'envelope', 'envelope-simple': 'envelope-simple',
    'cash-coin': 'coins', coins: 'coins', 'credit-card': 'credit-card', star: 'star', 'star-fill': 'star',
    bookmark: 'bookmark-simple', 'bookmark-fill': 'bookmark-simple',
    'bookmark-check': 'seal-check', 'bookmark-x': 'tray', fire: 'fire', ticket: 'ticket',
    megaphone: 'megaphone', sparkle: 'sparkle', 'trend-up': 'trend-up', signpost: 'signpost',
    'paper-plane-tilt': 'paper-plane-tilt', 'pencil-simple': 'pencil-simple', bank: 'bank',
    'list-numbers': 'list-numbers', 'calendar-dots': 'calendar-dots', headset: 'headset',
    'link-simple': 'link-simple', 'phone-incoming': 'phone-incoming', users: 'users',
    // telepon
    telephone: 'phone', 'telephone-x': 'phone-slash', phone: 'phone', 'phone-slash': 'phone-slash',
    // media sosial
    whatsapp: 'whatsapp-logo', instagram: 'instagram-logo', threads: 'threads-logo',
    facebook: 'facebook-logo', x: 'x-logo', twitter: 'x-logo', tiktok: 'tiktok-logo',
    youtube: 'youtube-logo', telegram: 'telegram-logo'
  };

  /** Nama kelas ikon Phosphor dari nama lama/baru, mis. 'geo-alt' → 'ph-map-pin'. */
  function ikonKelas(nama, varian) {
    var n = String(nama == null ? '' : nama).trim();
    n = ALIAS_IKON[n] || n;
    return (varian || 'ph') + ' ph-' + n;
  }

  /** Rangkaian <i> siap pakai. Contoh: SP.ico('seal-check', 'ph-fill text-success'). */
  function ico(nama, kelas) {
    return '<i class="' + ikonKelas(nama) + (kelas ? ' ' + kelas : '') + '" aria-hidden="true"></i>';
  }

  /* ------------------------------ GAMBAR -------------------------------- */
  /** URL gambar dari data JSON (boleh URL luar Unsplash atau path lokal). */
  function img(path) { return luar(path) ? String(path) : internal(path); }

  /**
   * Gambar kartu: URL luar diberi ukuran lebih ringan (kartu tidak perlu
   * gambar 1000 px). Hanya menyentuh CDN Unsplash — URL lain dibiarkan utuh.
   */
  function imgKartu(path, skala) {
    var u = img(path);
    if (u.indexOf('images.unsplash.com') < 0) return u;
    var k = skala || 0.7;
    var w = Math.max(400, Math.round(1000 * k));
    var h = Math.max(300, Math.round(625 * k));
    return u.replace(/([?&])w=\d+/, '$1w=' + w)
      .replace(/([?&])h=\d+/, '$1h=' + h)
      .replace(/([?&])q=\d+/, '$1q=60');
  }

  /**
   * srcset/sizes untuk gambar Unsplash: ponsel cukup 480–640 px, desktop 800+.
   * URL non-Unsplash mengembalikan string kosong (tidak ada varian ukuran).
   */
  function imgSrcset(path, lebar) {
    var u = img(path);
    if (u.indexOf('images.unsplash.com') < 0) return { srcset: '', sizes: '' };
    // Rasio tinggi mengikuti imgKartu (625/1000 = 0,625) supaya entri srcset
    // 800w benar-benar sama dengan atribut src → tidak ada unduhan ganda.
    var arr = (lebar || [480, 800]).map(function (w) {
      var h = Math.round(w * 0.625);
      var v = u.replace(/([?&])w=\d+/, '$1w=' + w).replace(/([?&])h=\d+/, '$1h=' + h);
      return v + ' ' + w + 'w';
    });
    return { srcset: arr.join(', '), sizes: '(min-width: 992px) 60vw, 94vw' };
  }

  /** Fallback gambar gagal dimuat → placeholder lokal (tanpa memicu galat baru). */
  function imgGagal(el) {
    if (!el || el.getAttribute('data-gagal') === '1') return;
    el.setAttribute('data-gagal', '1');
    el.src = internal('assets/img/placeholder/placeholder-umum.webp');
  }

  return {
    nama: 'Sudut Pandaan',
    tagline: 'Mata Komunitas Pandaan',
    base: base,
    luar: luar,
    internal: internal,
    /** Bangun URL aset/link internal dari root situs. */
    url: function (path) { return internal(path); },
    img: img,
    imgKartu: imgKartu, imgSrcset: imgSrcset,
    imgGagal: imgGagal,
    ico: ico,
    ikonKelas: ikonKelas,
    ALIAS_IKON: ALIAS_IKON,
    waAdmin: '6281553500855',
    email: 'redaksi@sudutpandaan.id',
    dataDir: 'assets/data/',
    peta: { lat: -7.6527, lng: 112.6871, zoom: 13 },
    key: { simpan: 'sp-simpan', breakingTutup: 'sp-breaking-tutup' },
    // Fasilitas umum pada peta. Koordinat = PERKIRAAN area pusat layanan;
    // verifikasi di lapangan sebelum dipromosikan ke publik.
    fasilitas: [
      { nama: 'Kantor Kecamatan Pandaan', jenis: 'fasilitas', lat: -7.6473, lng: 112.6953, catatan: 'Koordinat perkiraan' },
      { nama: 'Alun-alun / Lapangan Pandaan', jenis: 'fasilitas', lat: -7.6495, lng: 112.6925, catatan: 'Koordinat perkiraan' },
      { nama: 'Puskesmas Pandaan', jenis: 'fasilitas', lat: -7.6497, lng: 112.6896, catatan: 'Koordinat perkiraan' },
      { nama: 'Terminal Tipe A Pandaan', jenis: 'fasilitas', lat: -7.6449, lng: 112.6982, catatan: 'Koordinat perkiraan' },
      { nama: 'Pasar Pandaan', jenis: 'fasilitas', lat: -7.6512, lng: 112.6905, catatan: 'Koordinat perkiraan' },
      { nama: 'Gerbang Tol Pandaan', jenis: 'fasilitas', lat: -7.6341, lng: 112.6795, catatan: 'Koordinat perkiraan' }
    ],
    // Titik rawan kepadatan (hasil observasi redaksi — bukan data resmi)
    titikMacet: [
      { nama: 'Akses gerbang tol Pandaan', jenis: 'macet', lat: -7.6341, lng: 112.6795, catatan: 'Jam rawan 06.00–08.00 & 16.00–19.00' },
      { nama: 'Bypass Pandaan (persimpangan utama)', jenis: 'macet', lat: -7.6413, lng: 112.6871, catatan: 'Jam rawan pagi & sore' },
      { nama: 'Jalur Tretes (menuju kawasan wisata)', jenis: 'macet', lat: -7.6582, lng: 112.6750, catatan: 'Jam rawan pagi akhir pekan' },
      { nama: 'Depan Pasar Pandaan', jenis: 'macet', lat: -7.6512, lng: 112.6905, catatan: 'Jam rawan 05.30–09.00' }
    ]
  };
})();
