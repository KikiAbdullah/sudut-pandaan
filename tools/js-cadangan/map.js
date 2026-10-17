/* ==========================================================================
   Sudut Pandaan — map.js
   Peta Leaflet + OpenStreetMap. Hanya dimuat pada halaman yang memakainya
   (beranda mini-map, detail wisata/kuliner/UMKM, dan halaman Peta Pandaan).
   ========================================================================== */
window.SP_MAP = (function () {
  'use strict';

  var WARNA = { wisata: '#00897B', kuliner: '#8E24AA', umkm: '#E8B400', fasilitas: '#1565C0', macet: '#EF6C00' };
  var LABEL = { wisata: 'Wisata', kuliner: 'Kuliner', umkm: 'UMKM', fasilitas: 'Fasilitas umum', macet: 'Rawan macet' };
  var map = null, cluster = null, markerPerJenis = {};

  // Pin peta: titik 20 px di tengah kotak sentuh 32 px (ramah jari & tetap rapi).
  function ikon(warna) {
    var html = '<span class="sp-pin-wrap"><span class="sp-pin" style="background:' + warna + '"></span></span>';
    return L.divIcon({ html: html, className: '', iconSize: [32, 32], iconAnchor: [16, 16], popupAnchor: [0, -14] });
  }

  function popup(nama, jenis, catatan, href, lat, lng) {
    return '<strong>' + SP_UI.esc(nama) + '</strong><br>' +
      '<span style="color:' + WARNA[jenis] + ';font-weight:600">' + LABEL[jenis] + '</span><br>' +
      (catatan ? '<span style="color:#4B5A52">' + SP_UI.esc(catatan) + '</span><br>' : '') +
      (href ? '<a href="' + href + '">Detail</a> · ' : '') +
      '<a href="https://www.google.com/maps/dir/?api=1&destination=' + lat + ',' + lng +
      '" target="_blank" rel="noopener">Rute</a>';
  }

  function fallback(pesan) {
    var el = document.getElementById('peta');
    if (!el) return;
    el.outerHTML = '<div class="map-fallback"><p class="mb-2 small"><i class="ph ph-warning me-1" aria-hidden="true"></i>' +
      SP_UI.esc(pesan) + '</p><p class="small mb-2">Peta memerlukan berkas Leaflet lokal (<code>assets/vendor/leaflet/</code>) dan koneksi ke server tile OpenStreetMap.</p>' +
      '<a class="btn btn-sm btn-outline-primary" href="' + SP.url('peta.html') + '">Lihat daftar titik &amp; koordinat</a> ' +
      '<a class="btn btn-sm btn-outline-primary" target="_blank" rel="noopener" href="https://www.openstreetmap.org/#map=14/-7.65/112.69">Buka di OpenStreetMap</a></div>';
  }

  function inisialisasi(el, data) {
    if (!window.L) { fallback('Pustaka peta tidak termuat.'); return; }
    var tunggal = el.getAttribute('data-peta') === 'tunggal';
    // Mode "mini" = pratinjau di beranda: hanya ilustrasi (tidak bisa digeser
    // atau di-zoom, penanda tidak menerima fokus/klik). Daftar titik yang bisa
    // diakses keyboard ada di halaman Peta Pandaan.
    var mini = el.getAttribute('data-peta') === 'mini';
    var kotak = tunggal ? el.closest('[data-lat]') : null;
    var lat = tunggal && kotak ? parseFloat(kotak.getAttribute('data-lat')) : SP.peta.lat;
    var lng = tunggal && kotak ? parseFloat(kotak.getAttribute('data-lng')) : SP.peta.lng;
    var zoom = tunggal ? 15 : SP.peta.zoom;

    map = L.map(el, {
      scrollWheelZoom: false,
      zoomControl: !mini,
      dragging: !mini,
      keyboard: !mini,
      doubleClickZoom: !mini,
      touchZoom: !mini,
      boxZoom: !mini
    }).setView([lat, lng], zoom);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    if (tunggal) {
      var nama = kotak && kotak.getAttribute('data-nama') ? kotak.getAttribute('data-nama') : 'Lokasi';
      L.marker([lat, lng], { icon: ikon('#14573F'), title: nama }).addTo(map)
        .bindPopup('<strong>' + SP_UI.esc(nama) + '</strong><br><span style="color:#4B5A52">Koordinat perkiraan — verifikasi di lapangan.</span><br>' +
          '<a href="https://www.google.com/maps/dir/?api=1&destination=' + lat + ',' + lng + '" target="_blank" rel="noopener">Rute ke lokasi</a>')
        .openPopup();
      return;
    }

    // Mode "semua titik" — mendukung filter dari halaman Peta & beranda
    var pakaiCluster = !!window.L.markerClusterGroup;
    cluster = pakaiCluster ? L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 46 }) : L.layerGroup();
    map.addLayer(cluster);

    function tambah(items, jenis, hrefBuilder, catatanBuilder) {
      markerPerJenis[jenis] = L.layerGroup();
      items.forEach(function (it) {
        var lati = parseFloat(it.lat), lngi = parseFloat(it.lng);
        if (isNaN(lati) || isNaN(lngi)) return;
        var m = L.marker([lati, lngi], {
          icon: ikon(WARNA[jenis]), title: it.nama || it.nama_usaha,
          interactive: !mini, keyboard: !mini
        });
        if (!mini) {
          m.bindPopup(popup(it.nama || it.nama_usaha, jenis, catatanBuilder ? catatanBuilder(it) : '', hrefBuilder ? hrefBuilder(it) : '', lati, lngi));
        }
        markerPerJenis[jenis].addLayer(m);
        cluster.addLayer(m);
      });
    }

    tambah(SP_UI.items(data.wisata), 'wisata', function (w) { return SP.url('wisata/' + w.slug + '.html'); }, function (w) { return w.ringkasan; });
    tambah(SP_UI.items(data.kuliner), 'kuliner', function (k) { return SP.url('kuliner/' + k.slug + '.html'); },
      function (k) { return k.jenis_masakan + ' · ' + k.harga_per_orang; });
    tambah(SP_UI.items(data.umkm), 'umkm', function (u) { return SP.url('umkm/' + u.slug + '.html'); },
      function (u) { return u.kategori + ' · ' + u.desa; });
    tambah(SP.fasilitas, 'fasilitas', null, function (f) { return f.catatan; });
    tambah(SP.titikMacet, 'macet', null, function (f) { return f.catatan; });

    // Sinkronkan visibilitas dengan checkbox filter (jika ada)
    document.querySelectorAll('#filterPeta input').forEach(function (cb) {
      cb.addEventListener('change', function () { terapkanFilter(); });
    });
    terapkanFilter();
  }

  function terapkanFilter() {
    if (!map || !cluster) return;
    var aktif = Array.prototype.slice.call(document.querySelectorAll('#filterPeta input')).map(function (cb) { return cb; });
    if (!aktif.length) return;
    aktif.forEach(function (cb) {
      var grup = markerPerJenis[cb.value];
      if (!grup) return;
      if (cb.checked) { grup.eachLayer(function (m) { if (!cluster.hasLayer(m)) cluster.addLayer(m); }); }
      else { grup.eachLayer(function (m) { if (cluster.hasLayer(m)) cluster.removeLayer(m); }); }
    });
  }

  function fokus(lat, lng) {
    if (!map) return;
    map.setView([lat, lng], 16, { animate: true });
    var el = document.getElementById('peta');
    if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function init() {
    var el = document.getElementById('peta');
    if (!el) return;
    // Idempoten: 'sp:rendered' bisa terpicu lebih dari sekali (render ulang data).
    if (map || el.classList.contains('leaflet-container')) return;
    if (!window.SP_UI) { return; }
    SP_UI.loadData().then(function (data) { inisialisasi(el, data); })
      .catch(function () { fallback('Data peta gagal dimuat.'); });
  }

  return { init: init, fokus: fokus, terapkanFilter: terapkanFilter };
})();

document.addEventListener('sp:rendered', function () { window.SP_MAP.init(); });
