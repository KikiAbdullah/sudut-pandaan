/* ==========================================================================
   Sudut Pandaan — share.js
   Tombol bagikan (WhatsApp, Facebook, X, Telegram), salin tautan, dan simpan
   artikel. Format URL mengikuti blueprint bagian 9.
   ========================================================================== */
(function () {
  'use strict';

  function judulDari(container) {
    var t = container.getAttribute('data-share-title');
    return t || document.title.replace(/\s*—\s*Sudut Pandaan\s*$/, '');
  }

  function urlSekarang() {
    return location.href.split('#')[0];
  }

  function tautan(jenis, judul, url) {
    var u = encodeURIComponent(url), t = encodeURIComponent(judul);
    switch (jenis) {
      case 'wa': return 'https://wa.me/?text=' + encodeURIComponent(judul + ' ' + url);
      case 'fb': return 'https://www.facebook.com/sharer/sharer.php?u=' + u;
      case 'x': return 'https://twitter.com/intent/tweet?text=' + t + '&url=' + u;
      case 'tg': return 'https://t.me/share/url?url=' + u + '&text=' + t;
      default: return url;
    }
  }

  function init() {
    document.querySelectorAll('.sp-share').forEach(function (container) {
      var aktif = container.getAttribute('data-share-init') === '1';
      if (aktif) return;
      container.setAttribute('data-share-init', '1');

      container.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-share], [data-copy-link], [data-save-article]');
        if (!btn) return;
        e.preventDefault();
        var judul = judulDari(container);
        var url = urlSekarang();

        if (btn.hasAttribute('data-copy-link')) {
          window.SP_UI.salin(url, 'Tautan artikel disalin');
          return;
        }

        if (btn.hasAttribute('data-save-article')) {
          var disimpan = window.SP_UI.toggleSimpan({
            judul: judul, url: url, waktu: new Date().toISOString()
          });
          btn.classList.toggle('is-saved', disimpan);
          btn.setAttribute('aria-pressed', disimpan ? 'true' : 'false');
          btn.querySelector('i').className = SP.ikonKelas('bookmark' + (disimpan ? '-fill' : ''));
          window.SP_UI.toast(disimpan ? 'Artikel disimpan di peramban Anda' : 'Artikel dihapus dari simpanan',
            disimpan ? 'bookmark-check' : 'bookmark-x');
          return;
        }

        var jenis = btn.getAttribute('data-share');
        var lebar = 640, tinggi = 560;
        var kiri = (window.screen.width - lebar) / 2, atas = (window.screen.height - tinggi) / 2;
        window.open(tautan(jenis, judul, url), 'bagikan',
          'width=' + lebar + ',height=' + tinggi + ',left=' + kiri + ',top=' + atas + ',noopener,noreferrer');
      });

      // Tandai tombol simpan bila artikel sudah tersimpan
      var simpan = container.querySelector('[data-save-article]');
      if (simpan && window.SP_UI.sudahDisimpan(urlSekarang())) {
        simpan.classList.add('is-saved');
        simpan.setAttribute('aria-pressed', 'true');
        var i = simpan.querySelector('i');
        if (i) i.className = SP.ikonKelas('bookmark-fill');
      }
    });
  }

  document.addEventListener('sp:rendered', init);
  document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 0); });
})();
