/* ==========================================================================
   Sudut Pandaan — components.js
   Pemuatan data + komponen kartu & daftar (dirender dari JSON).
   Semua keluaran di-escape (esc) untuk mencegah XSS dari data yang diedit.
   ========================================================================== */
window.SP_UI = (function () {
  'use strict';

  var _data = null, _siap = false;

  /* ------------------------------ utilitas ------------------------------ */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  var BULAN = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
    'Agustus', 'September', 'Oktober', 'November', 'Desember'];
  var BULAN_SINGKAT = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
  var HARI = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'];

  function toDate(v) { return v ? new Date(v) : null; }

  function waktuRelatif(v) {
    var d = toDate(v); if (!d || isNaN(d)) return '';
    var detik = (Date.now() - d.getTime()) / 1000;
    if (detik < 60) return 'baru saja';
    if (detik < 3600) return Math.max(1, Math.floor(detik / 60)) + ' menit lalu';
    if (detik < 86400) return Math.floor(detik / 3600) + ' jam lalu';
    if (detik < 604800) return Math.floor(detik / 86400) + ' hari lalu';
    return d.getDate() + ' ' + BULAN[d.getMonth()] + ' ' + d.getFullYear();
  }

  function tglPanjang(v, denganJam) {
    var d = toDate(v); if (!d || isNaN(d)) return '—';
    var s = d.getDate() + ' ' + BULAN[d.getMonth()] + ' ' + d.getFullYear();
    if (denganJam) s += ', ' + pad(d.getHours()) + '.' + pad(d.getMinutes()) + ' WIB';
    return s;
  }

  function tglPendek(v) {
    var d = toDate(v); if (!d || isNaN(d)) return '—';
    return d.getDate() + ' ' + BULAN_SINGKAT[d.getMonth()] + ' ' + d.getFullYear();
  }

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function rupiah(n) { return 'Rp' + Number(n || 0).toLocaleString('id-ID'); }

  function menitBaca(html) {
    var t = String(html || '').replace(/<[^>]+>/g, ' ');
    var kata = t.split(/\s+/).filter(Boolean).length;
    return Math.max(2, Math.round(kata / 200));
  }

  /* ------------------------- pemuatan data JSON ------------------------- */
  var FILES = ['situs', 'kategori', 'berita', 'wisata', 'kuliner', 'umkm', 'agenda',
    'loker', 'lalu-lintas', 'nomor-penting', 'sosmed', 'panduan', 'desa', 'penulis'];

  function teksNilai(v) { try { return JSON.stringify(v || null); } catch (e) { return '' + v; } }

  // Ambil ulang JSON dari assets/data/ di latar belakang. Bila isinya berbeda
  // dengan data sematan (mis. redaksi baru menyunting JSON), beri tahu halaman
  // lewat peristiwa 'sp:data-baru' agar daftar digambar ulang.
  function segarkan() {
    var tasks = FILES.map(function (name) {
      return fetch(SP.url(SP.dataDir + name + '.json'), { cache: 'no-cache' })
        .then(function (r) { if (!r.ok) throw new Error('gagal'); return r.json(); })
        .then(function (json) { return [name, json]; })
        .catch(function () { return null; });
    });
    return Promise.all(tasks).then(function (pairs) {
      var berubah = false;
      pairs.forEach(function (p) {
        if (!p || p[1] == null) return;
        if (teksNilai(_data[p[0]]) !== teksNilai(p[1])) { _data[p[0]] = p[1]; berubah = true; }
      });
      if (berubah) document.dispatchEvent(new Event('sp:data-baru'));
      return _data;
    });
  }

  function loadData() {
    if (_siap) return Promise.resolve(_data);
    _siap = true;
    var embedded = window.SP_DATA || {};   // salinan hasil build (agar file:// tetap jalan)
    var adaSematan = Object.keys(embedded).length > 1;
    _data = {};
    FILES.forEach(function (name) { _data[name] = embedded[name] || null; });

    // Sentuhan pertama memakai data sematan → kartu langsung tampil tanpa
    // menunggu 14 permintaan JSON. Tanpa sematan (mis. HTML lama), tunggu fetch.
    if (adaSematan) { segarkan(); return Promise.resolve(_data); }
    return segarkan().then(function () { return _data; });
  }

  function items(payload) {
    if (!payload) return [];
    return Array.isArray(payload) ? payload : (payload.items || []);
  }

  /* --------------------------- jam buka (status) ------------------------- */
  // Waktu WIB (UTC+7), bukan waktu lokal peramban: pengunjung dari luar
  // Indonesia tetap melihat status "Buka sekarang/Tutup" yang benar.
  function sekarangWIB() {
    var now = new Date();
    return new Date(now.getTime() + now.getTimezoneOffset() * 60000 + 7 * 3600000);
  }

  function menitDari(teks) {
    var m = String(teks).match(/(\d{1,2})[.:](\d{2})/);
    return m ? parseInt(m[1], 10) * 60 + parseInt(m[2], 10) : null;
  }

  function cekBuka(jam) {
    if (!jam) return null;
    var hari = sekarangWIB().getDay();     // 0 = Minggu
    var kunci = null;
    if (hari === 0 || hari === 6) kunci = jam['sab-min'] || jam['sen-min'] || jam['sen-jum'] || null;
    else kunci = jam['sen-jum'] || jam['sen-min'] || jam['sab-min'] || null;
    if (!kunci) return null;
    var pisah = String(kunci).split(/[–—-]/);
    if (pisah.length < 2) return null;
    var mulai = menitDari(pisah[0]), selesai = menitDari(pisah[1]);
    if (mulai === null || selesai === null) return null;
    var wib = sekarangWIB();
    var sekarang = wib.getHours() * 60 + wib.getMinutes();
    var buka = mulai <= selesai
      ? (sekarang >= mulai && sekarang <= selesai)    // tutup di hari yang sama
      : (sekarang >= mulai || sekarang <= selesai);   // tutup lewat tengah malam
    return { buka: buka, label: buka ? 'Buka sekarang' : 'Tutup', jam: kunci };
  }

  /* ------------------------------- kartu -------------------------------- */
  function kartuBerita(b, opsi) {
    opsi = opsi || {};
    var href = SP.url('berita/' + b.slug + '.html');
    return '' +
      '<div class="' + (opsi.col || 'col-12 col-md-6 col-lg-4') + '">' +
      '<article class="card card-news">' +
      '<div class="card-img-wrap">' +
      '<a href="' + href + '" tabindex="-1" aria-hidden="true">' +
      '<img src="' + SP.imgKartu(b.gambar, opsi.skalaGambar) + '" alt="' + esc(b.alt || b.judul) + '" loading="lazy" decoding="async" width="800" height="500" onerror="SP.imgGagal(this)">' +
      '</a>' +
      '<span class="card-badge-float badge-cat cat-' + esc(b.kategori_slug) + '">' + esc(b.kategori) + '</span>' +
      (b.breaking ? '<span class="card-flag"><i class="ph ph-broadcast"></i>Terkini</span>' : '') +
      '</div>' +
      '<div class="card-body d-flex flex-column">' +
      '<h3 class="card-title clamp-3 mb-2"><a class="stretched-link text-decoration-none" href="' + href + '">' + esc(b.judul) + '</a></h3>' +
      '<p class="small text-muted-2 clamp-2 mb-3">' + esc(b.ringkasan) + '</p>' +
      '<div class="meta mt-auto">' +
      '<span><i class="ph ph-clock" aria-hidden="true"></i> ' + waktuRelatif(b.tanggal) + '</span>' +
      '<span><i class="ph ph-user" aria-hidden="true"></i> ' + esc(b.penulis) + '</span>' +
      '<span><i class="ph ph-hourglass-medium" aria-hidden="true"></i> ' + menitBaca(b.isi) + ' mnt</span>' +
      '</div></div></article></div>';
  }

  function kartuWisata(w, opsi) {
    opsi = opsi || {};
    var href = SP.url('wisata/' + w.slug + '.html');
    var status = cekBuka(w.jam_buka);
    return '' +
      '<div class="' + (opsi.col || 'col-12 col-md-6 col-lg-4') + '">' +
      '<article class="card card-place">' +
      '<div class="card-img-wrap">' +
      '<a href="' + href + '" tabindex="-1" aria-hidden="true"><img src="' + SP.imgKartu(w.gambar) + '" alt="' + esc(w.nama) + '" loading="lazy" decoding="async" width="800" height="500" onerror="SP.imgGagal(this)"></a>' +
      '<span class="card-badge-float badge-cat cat-wisata">' + esc(w.kategori) + '</span>' +
      (status ? '<span class="card-flag ' + (status.buka ? 'status-buka' : 'status-tutup') + '" title="Jam buka hari ini: ' + esc(status.jam) + ' WIB">' + status.label + '</span>' : '') +
      '</div>' +
      '<div class="card-body d-flex flex-column">' +
      '<h3 class="card-title h6 mb-1"><a class="stretched-link text-decoration-none" href="' + href + '">' + esc(w.nama) + '</a></h3>' +
      '<p class="small text-muted-2 clamp-2 mb-2">' + esc(w.ringkasan) + '</p>' +
      '<p class="card-price mb-2">' + esc(w.harga_label || '—') + '</p>' +
      '<div class="meta mt-auto">' +
      '<span><i class="ph ph-map-pin" aria-hidden="true"></i> ' + esc(w.desa) + '</span>' +
      '<span><i class="ph ph-seal-check" aria-hidden="true"></i> Cek ' + tglPendek(w.terakhir_diverifikasi) + '</span>' +
      '</div></div></article></div>';
  }

  function kartuKuliner(k, opsi) {
    opsi = opsi || {};
    var href = SP.url('kuliner/' + k.slug + '.html');
    return '' +
      '<div class="' + (opsi.col || 'col-12 col-md-6 col-lg-4') + '">' +
      '<article class="card card-place">' +
      '<div class="card-img-wrap">' +
      '<a href="' + href + '" tabindex="-1" aria-hidden="true"><img src="' + SP.imgKartu(k.gambar) + '" alt="' + esc(k.nama) + '" loading="lazy" decoding="async" width="800" height="500" onerror="SP.imgGagal(this)"></a>' +
      '<span class="card-badge-float badge-cat cat-kuliner">' + esc(k.jenis_masakan) + '</span>' +
      (k.is_legendaris ? '<span class="card-flag">Legendaris</span>' : '') +
      '</div>' +
      '<div class="card-body d-flex flex-column">' +
      '<h3 class="card-title h6 mb-1"><a class="stretched-link text-decoration-none" href="' + href + '">' + esc(k.nama) + '</a></h3>' +
      '<p class="small text-muted-2 clamp-2 mb-2">' + esc(k.ringkasan) + '</p>' +
      '<p class="card-price mb-2">' + esc(k.harga_per_orang) + '</p>' +
      '<div class="meta mt-auto">' +
      '<span><i class="ph ph-clock" aria-hidden="true"></i> ' + esc(k.jam_buka_str) + '</span>' +
      '<span><i class="ph ph-map-pin" aria-hidden="true"></i> ' + esc(k.desa) + '</span>' +
      '</div></div></article></div>';
  }

  function kartuUmkm(u, opsi) {
    opsi = opsi || {};
    var href = SP.url('umkm/' + u.slug + '.html');
    var pesan = encodeURIComponent('Halo, saya menemukan profil ' + u.nama_usaha + ' di Sudut Pandaan. Saya ingin bertanya.');
    return '' +
      '<div class="' + (opsi.col || 'col-6 col-lg-3') + '">' +
      '<article class="card card-place card-umkm">' +
      '<div class="card-img-wrap">' +
      '<a href="' + href + '" tabindex="-1" aria-hidden="true"><img src="' + SP.imgKartu(u.gambar, 0.4) + '" alt="' + esc(u.nama_usaha) + '" loading="lazy" decoding="async" width="400" height="400" onerror="SP.imgGagal(this)"></a>' +
      (u.paket === 'premium' ? '<span class="card-flag"><i class="ph-fill ph-star me-1" aria-hidden="true"></i>Premium</span>' : '') +
      '</div>' +
      '<div class="card-body d-flex flex-column">' +
      '<h3 class="card-title h6 mb-1"><a class="stretched-link text-decoration-none" href="' + href + '">' + esc(u.nama_usaha) + '</a></h3>' +
      '<p class="small text-muted-2 mb-2">' + esc(u.kategori) + ' · ' + esc(u.desa) + '</p>' +
      '<div class="d-flex flex-wrap gap-1 mb-2">' +
      (u.is_verified ? '<span class="badge-verify"><i class="ph-fill ph-seal-check"></i> Terverifikasi</span>' : '<span class="badge-soft">Belum diverifikasi</span>') +
      '</div>' +
      '<a class="btn btn-wa btn-sm mt-auto position-relative" style="z-index:2" target="_blank" rel="noopener noreferrer" ' +
      'href="https://wa.me/' + esc(u.whatsapp) + '?text=' + pesan + '"><i class="ph ph-whatsapp-logo"></i> WhatsApp</a>' +
      '</div></article></div>';
  }

  /* Kartu berita utama: gambar besar dengan judul serif di atas tirai gelap */
  function kartuBeritaLead(b, opsi) {
    opsi = opsi || {};
    var href = SP.url('berita/' + b.slug + '.html');
    // Mode prioritas: gambar utama di atas lipatan → eager + fetchpriority high
    // dan srcset agar ponsel tidak mengunduh versi desktop (mempercepat LCP).
    var ss = opsi.prioritas ? SP.imgSrcset(b.gambar, [480, 800, 1000]) : { srcset: '', sizes: '' };
    var atrGambar = opsi.prioritas
      ? ' loading="eager" fetchpriority="high"' + (ss.srcset ? ' srcset="' + ss.srcset + '" sizes="' + ss.sizes + '"' : '')
      : ' loading="lazy"';
    return '' +
      // Wadah memakai <div>: <span> tidak boleh berisi <h3>/<p> (HTML tidak sah →
      // peramban memecah elemennya dan teks keluar dari kartu).
      // Tautan ditempatkan DI DALAM judul (bukan <a> kosong) agar pembaca layar
      // dan audit aksesibilitas menemukan nama tautan yang bermakna.
      '<article class="card-lead h-100">' +
      '<img src="' + SP.imgKartu(b.gambar, opsi.prioritas ? 0.8 : 0.8) + '" alt="' + esc(b.alt || b.judul) + '"' + atrGambar + ' decoding="async" width="960" height="660" onerror="SP.imgGagal(this)">' +
      '<div class="card-lead-isi">' +
      '<span class="badge-cat cat-' + esc(b.kategori_slug) + ' mb-2 d-inline-block">' + esc(b.kategori) + '</span>' +
      '<h3 class="card-lead-judul mb-2"><a class="stretched-link" href="' + href + '">' + esc(b.judul) + '</a></h3>' +
      '<p class="card-lead-ringkas clamp-2 mb-2">' + esc(b.ringkasan) + '</p>' +
      '<span class="meta"><i class="ph ph-clock" aria-hidden="true"></i> ' + waktuRelatif(b.tanggal) + '</span>' +
      '</div></article>';
  }

  /* ==================== PETAK BENTO (tata letak majalah) ====================
     Semua petak memakai kelas dari CSS: .tile + varian (foto/navy/teal/emas)
     dan penempatan kolom via .b-12/.b-8/.b-6/.b-4/.b-3 pada pembungkusnya. */

  function tileFoto(o) {
    return '' +
      '<a class="tile tile-foto ' + (o.kelas || '') + '" href="' + o.href + '"' +
        (o.luar ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' +
      '<img src="' + (o.gambar || '') + '" alt="' + esc(o.alt || o.judul) + '" loading="lazy" decoding="async" width="800" height="500" onerror="SP.imgGagal(this)">' +
      '<span class="tile-isi">' +
      (o.kicker ? '<span class="tile-kicker">' + esc(o.kicker) + '</span>' : '') +
      '<span class="tile-judul ' + (o.judulKelas || 'h4') + '">' + esc(o.judul) + '</span>' +
      (o.teks ? '<span class="tile-teks clamp-2">' + esc(o.teks) + '</span>' : '') +
      (o.meta ? '<span class="meta">' + o.meta + '</span>' : '') +
      (o.badge || '') +
      '</span></a>';
  }

  function tileTeks(o) {
    var tag = o.href ? 'a' : 'div';
    return '<' + tag + ' class="tile ' + (o.kelas || '') + '"' + (o.href ? ' href="' + o.href + '"' : '') + '>' +
      '<span class="tile-isi">' +
      (o.kicker ? '<span class="tile-kicker">' + esc(o.kicker) + '</span>' : '') +
      (o.ikon ? '<i class="ph ' + o.ikon + ' fs-3" aria-hidden="true"></i>' : '') +
      '<span class="tile-judul ' + (o.judulKelas || 'h5') + '">' + esc(o.judul) + '</span>' +
      (o.teks ? '<span class="tile-teks">' + esc(o.teks) + '</span>' : '') +
      (o.isiHtml || '') +
      (o.tautan ? '<span class="tile-tautan">' + esc(o.tautan) + ' <i class="ph ph-arrow-right" aria-hidden="true"></i></span>' : '') +
      '</span></' + tag + '>';
  }

  /* Baris daftar harga kuliner (pola daftar editorial bernomor) */
  function barisKuliner(k, nomor) {
    var angka = (nomor < 10 ? '0' : '') + nomor;
    return '<li><span class="daftar-nomor" aria-hidden="true">' + angka + '</span>' +
      '<span><a class="fw-bold text-decoration-none" href="' + SP.url('kuliner/' + k.slug + '.html') + '">' + esc(k.nama) + '</a>' +
      '<br><span class="tile-teks small">' + esc(k.harga_per_orang || '—') + ' · ' + esc(k.desa) + '</span></span></li>';
  }

  /* Petak UMKM kecil (gambar + nama + kategori desa) */
  function tileUmkm(u) {
    return tileFoto({
      href: SP.url('umkm/' + u.slug + '.html'),
      gambar: SP.imgKartu(u.gambar, 0.4),
      alt: u.nama_usaha,
      judul: u.nama_usaha,
      judulKelas: 'h6',
      kicker: u.kategori + (u.desa ? ' · ' + u.desa : ''),
      kelas: 'tile-pendek',
      badge: (u.is_verified ? '<span class="badge-verify mt-1 align-self-start"><i class="ph-fill ph-seal-check" aria-hidden="true"></i> Terverifikasi</span>' : '')
    });
  }

  /* Kartu destinasi ala indonesia.travel: gambar penuh, tirai gelap di bawah,
     judul serif putih, dan satu tautan utuh (seluruh kartu bisa diklik). */
  function kartuDestinasi(o) {
    // o = { href, gambar, alt, judul, label, kategori(kelas badge), meta, col, harga }
    return '' +
      '<div class="' + (o.col === undefined ? 'col-12 col-sm-6 col-lg-4' : o.col) + '">' +
      '<a class="card-dest' + (o.lebar ? ' card-dest-lebar' : '') + '" href="' + o.href + '">' +
      '<img src="' + o.gambar + '" alt="' + esc(o.alt) + '" loading="lazy" decoding="async" width="600" height="750" onerror="SP.imgGagal(this)">' +
      (o.kategori ? '<span class="badge-cat ' + o.kategori + '">' + esc(o.label) + '</span>' : '') +
      '<span class="card-dest-isi">' +
      '<span class="card-dest-judul d-block">' + esc(o.judul) + '</span>' +
      (o.meta ? '<span class="d-block small mt-1" style="color:rgba(255,255,255,.85)">' + esc(o.meta) + '</span>' : '') +
      '<span class="card-dest-link mt-2">Lihat detail <i class="ph ph-arrow-right" aria-hidden="true"></i></span>' +
      '</span></a></div>';
  }

  function destinasiWisata(w, opsi) {
    opsi = opsi || {};
    var status = cekBuka(w.jam_buka);
    return kartuDestinasi({
      href: SP.url('wisata/' + w.slug + '.html'),
      gambar: SP.imgKartu(w.gambar, 0.6),
      alt: w.nama,
      judul: w.nama,
      label: w.kategori,
      kategori: 'cat-wisata',
      meta: w.desa + (status ? ' · ' + status.label : ''),
      col: opsi.col, lebar: opsi.lebar
    });
  }

  function destinasiKuliner(k, opsi) {
    opsi = opsi || {};
    return kartuDestinasi({
      href: SP.url('kuliner/' + k.slug + '.html'),
      gambar: SP.imgKartu(k.gambar, 0.55),
      alt: k.nama,
      judul: k.nama,
      label: k.jenis_masakan,
      kategori: 'cat-kuliner',
      meta: (k.harga_per_orang || '') + (k.desa ? ' · ' + k.desa : ''),
      col: opsi.col, lebar: opsi.lebar
    });
  }

  function kartuAgenda(a) {
    var d = toDate(a.mulai) || new Date();
    var statusBadge = a.status === 'belum_final'
      ? '<span class="badge text-bg-warning">Belum final</span>'
      : (a.status === 'berulang' ? '<span class="badge text-bg-info">Rutin</span>' : '<span class="badge text-bg-success">Terjadwal</span>');
    return '' +
      '<div class="col-12 col-md-6 col-lg-4">' +
      '<article class="card card-news h-100" data-agenda-slug="' + esc(a.slug) + '">' +
      '<div class="card-img-wrap"><img src="' + SP.imgKartu(a.gambar) + '" alt="' + esc(a.judul) + '" loading="lazy" decoding="async" width="800" height="500" onerror="SP.imgGagal(this)"></div>' +
      '<div class="card-body d-flex flex-column">' +
      '<div class="d-flex gap-2 align-items-center mb-2">' + statusBadge + '<span class="badge-soft">' + esc(a.biaya) + '</span></div>' +
      '<h3 class="card-title h6 mb-2">' + esc(a.judul) + '</h3>' +
      '<p class="small text-muted-2 clamp-2 mb-3">' + esc(a.deskripsi) + '</p>' +
      '<ul class="list-unstyled small mb-3">' +
      '<li><i class="ph ph-calendar-dots me-1" aria-hidden="true"></i>' + tglPanjang(a.mulai, true) + '</li>' +
      '<li><i class="ph ph-map-pin me-1" aria-hidden="true"></i>' + esc(a.lokasi) + '</li>' +
      '<li><i class="ph ph-users me-1" aria-hidden="true"></i>' + esc(a.penyelenggara) + '</li>' +
      '</ul>' +
      '<button class="btn btn-sm btn-outline-primary mt-auto position-relative" style="z-index:2" type="button" ' +
      'data-ics="' + esc(a.slug) + '"><i class="ph ph-calendar-plus me-1" aria-hidden="true"></i>Tambahkan ke kalender</button>' +
      '</div></article></div>';
  }

  function kartuLoker(l) {
    var kadaluarsa = l.status !== 'aktif';
    return '' +
      '<div class="col-12 col-lg-6">' +
      '<article class="card card-news h-100"><div class="card-body d-flex flex-column">' +
      '<div class="d-flex flex-wrap gap-2 mb-2">' +
      '<span class="badge-cat cat-agenda">' + esc(l.jenis) + '</span>' +
      (kadaluarsa ? '<span class="badge text-bg-secondary">Contoh / kedaluwarsa</span>' : '<span class="badge text-bg-success">Aktif</span>') +
      '</div>' +
      '<h3 class="card-title h6 mb-1">' + esc(l.posisi) + '</h3>' +
      '<p class="small text-muted-2 mb-2">' + esc(l.perusahaan) + '</p>' +
      '<ul class="list-unstyled small mb-3">' +
      '<li><i class="ph ph-map-pin me-1" aria-hidden="true"></i>' + esc(l.lokasi) + '</li>' +
      '<li><i class="ph ph-coins me-1" aria-hidden="true"></i>' + esc(l.gaji) + '</li>' +
      '<li><i class="ph ph-calendar-x me-1" aria-hidden="true"></i>Batas lamaran: ' + tglPendek(l.batas_waktu) + '</li>' +
      '</ul>' +
      '<p class="small mb-2"><strong>Kualifikasi:</strong> ' + esc((l.kualifikasi || []).join(' · ')) + '</p>' +
      '<button class="btn btn-sm btn-outline-primary mt-auto position-relative" style="z-index:2" type="button" ' +
      'data-loker-detail="' + esc(l.slug) + '"><i class="ph ph-info me-1" aria-hidden="true"></i>Cara melamar</button>' +
      '</div></article></div>';
  }

  function itemLalin(l) {
    var warna = l.kondisi === 'Lancar' ? 'kesehatan'
      : (l.kondisi === 'Padat' ? 'lalu-lintas' : (l.kondisi === 'Belum terverifikasi' ? 'pembangunan' : 'peristiwa'));
    // Kartu status: garis kiri berwarna (lancar/ramai/padat) seperti papan lalu lintas
    var status = l.kondisi === 'Lancar' ? 'lancar'
      : (l.kondisi === 'Padat' ? 'padat' : 'ramai');
    return '' +
      '<div class="list-group-item px-0 border-0"><div class="status-kartu ' + status + '">' +
      '<div class="d-flex flex-wrap align-items-center gap-2 mb-1">' +
      '<span class="badge-cat cat-' + warna + '">' + esc(l.kondisi) + '</span>' +
      '<strong class="small">' + esc(l.ruas) + '</strong>' +
      '<span class="small text-muted-2">· ' + esc(l.lokasi) + '</span>' +
      (l.terverifikasi ? '<span class="badge-verify ms-auto"><i class="ph-fill ph-seal-check"></i> Terverifikasi</span>'
        : '<span class="badge-soft ms-auto">Belum terverifikasi</span>') +
      '</div>' +
      '<p class="small mb-1">' + esc(l.penyebab) + '</p>' +
      '<p class="small text-muted-2 mb-0">' +
      '<i class="ph ph-clock me-1" aria-hidden="true"></i>' + tglPanjang(l.waktu, true) +
      ' · <i class="ph ph-broadcast me-1" aria-hidden="true"></i>Sumber: ' + esc(l.sumber) +
      '</p></div></div>';
  }

  function kartuSosmed(s, opsi) {
    opsi = opsi || {};
    return '' +
      '<div class="' + (opsi.col || 'col-12 col-md-6 col-lg-4') + '">' +
      '<article class="card card-place h-100">' +
      '<div class="card-img-wrap"><img src="' + SP.imgKartu(s.gambar) + '" alt="Pratinjau konten ' + esc(s.platform) + '" loading="lazy" decoding="async" width="800" height="500" onerror="SP.imgGagal(this)">' +
      '<span class="card-flag position-static d-none"></span>' +
      '<span class="badge-cat cat-' + (s.ikon === 'threads' ? 'pembangunan' : 'kuliner') + ' card-badge-float">' + esc(s.jenis) + '</span>' +
      '</div>' +
      '<div class="card-body d-flex flex-column">' +
      '<p class="small mb-2 clamp-3">' + esc(s.caption) + '</p>' +
      '<div class="meta mt-auto">' +
      '<span>' + SP.ico(s.ikon) + ' ' + esc(s.platform) + '</span>' +
      '<span>' + waktuRelatif(s.tanggal) + '</span>' +
      '</div>' +
      '<a class="btn btn-sm btn-outline-primary mt-3 position-relative" style="z-index:2" href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">Lihat postingan</a>' +
      '</div></article></div>';
  }

  function barisNomor(n) {
    var ada = n.nomor && n.nomor !== '—';
    var badge = n.verifikasi === 'kosong'
      ? '<span class="badge-soft">Belum tersedia</span>'
      : '<span class="badge-verify">Perlu dicek ulang</span>';
    return '<tr>' +
      '<td><strong>' + esc(n.instansi) + '</strong><div class="small text-muted-2">' + esc(n.keterangan) + '</div></td>' +
      '<td>' + (ada ? '<span class="fw-semibold">' + esc(n.nomor) + '</span>' : '<span class="text-muted-2">—</span>') + '</td>' +
      '<td>' + badge + '</td>' +
      '<td>' + (ada ? '<a class="btn btn-sm btn-outline-primary" href="tel:' + esc(String(n.nomor).replace(/[^\d+]/g, '')) + '"><i class="ph ph-phone"></i><span class="visually-hidden">Telepon</span></a>' : '<span class="small text-muted-2">Menunggu verifikasi</span>') + '</td>' +
      '</tr>';
  }

  function kartuTitikPeta(t) {
    var warna = { wisata: 'cat-wisata', kuliner: 'cat-kuliner', umkm: 'cat-umkm', fasilitas: 'cat-agenda', macet: 'cat-lalu-lintas' }[t.jenis] || 'cat-umum';
    return '<div class="col-12 col-md-6">' +
      '<div class="info-box h-100 d-flex flex-column">' +
      '<div class="d-flex gap-2 align-items-center mb-1"><span class="badge-cat ' + warna + '">' + esc(t.label) + '</span></div>' +
      '<h3 class="h6 mb-1">' + esc(t.nama) + '</h3>' +
      '<p class="small text-muted-2 mb-2">' + esc(t.catatan || '') + '</p>' +
      '<div class="d-flex gap-2 mt-auto position-relative" style="z-index:2">' +
      (t.href ? '<a class="btn btn-sm btn-outline-primary" href="' + t.href + '">Detail</a>' : '') +
      '<a class="btn btn-sm btn-outline-primary" target="_blank" rel="noopener noreferrer" ' +
      'href="https://www.google.com/maps/dir/?api=1&destination=' + t.lat + ',' + t.lng + '">Rute</a>' +
      '<button class="btn btn-sm btn-outline-primary" type="button" data-fokus-peta="' + t.lat + ',' + t.lng + '">Lihat di peta</button>' +
      '</div></div></div>';
  }

  /* ------------------------------- util UI ------------------------------ */
  function isi(selector, html) {
    var el = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (el) el.innerHTML = html;
    return el;
  }

  function pesanKosong(teks, ikon) {
    return '<div class="col-12"><div class="empty-state">' + SP.ico(ikon || 'inbox') +
      '<p class="mb-0">' + esc(teks) + '</p></div></div>';
  }

  function toast(teks, ikon) {
    var el = document.getElementById('spToast');
    var txt = document.getElementById('spToastText');
    if (txt) txt.textContent = teks;
    var i = el ? el.querySelector('i') : null;
    if (i && ikon) i.className = SP.ikonKelas(ikon);
    if (el && window.bootstrap) bootstrap.Toast.getOrCreateInstance(el, { delay: 2600 }).show();
  }

  function salin(teks, pesanSukses) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(teks).then(function () { toast(pesanSukses || 'Tersalin ke papan klip', 'clipboard-check'); },
        function () { window.prompt('Salin tautan berikut:', teks); });
    } else {
      window.prompt('Salin tautan berikut:', teks);
    }
  }

  /* Simpan artikel (bookmark lokal) */
  function daftarSimpan() {
    try { return JSON.parse(localStorage.getItem(SP.key.simpan) || '[]'); } catch (e) { return []; }
  }
  function toggleSimpan(data) {
    var list = daftarSimpan();
    var idx = list.findIndex(function (x) { return x.url === data.url; });
    if (idx >= 0) { list.splice(idx, 1); } else { list.push(data); }
    try { localStorage.setItem(SP.key.simpan, JSON.stringify(list)); } catch (e) { }
    return idx < 0; // true = baru disimpan
  }
  function sudahDisimpan(url) {
    return daftarSimpan().some(function (x) { return x.url === url; });
  }

  /* Rentang harga untuk filter */
  function bucketHarga(item) {
    var max = item.harga_max || 0;
    var min = item.harga_min || 0;
    if (!max && !min) return 'gratis';
    if (max <= 20000) return 'murah';
    if (max <= 50000) return 'sedang';
    return 'mahal';
  }

  /* Ekspor .ics */
  function buatIcs(agenda) {
    function fmt(d) {
      return d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate()) + 'T' +
        pad(d.getUTCHours()) + pad(d.getUTCMinutes()) + '00Z';
    }
    var mulai = new Date(agenda.mulai), selesai = new Date(agenda.selesai || agenda.mulai);
    var isi = [
      'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Sudut Pandaan//ID', 'CALSCALE:GREGORIAN',
      'BEGIN:VEVENT',
      'UID:' + agenda.slug + '@sudutpandaan.id',
      'DTSTAMP:' + fmt(new Date()),
      'DTSTART:' + fmt(mulai),
      'DTEND:' + fmt(selesai),
      'SUMMARY:' + agenda.judul.replace(/[,;]/g, ' '),
      'LOCATION:' + String(agenda.lokasi).replace(/[,;]/g, ' '),
      'DESCRIPTION:' + String(agenda.deskripsi || '').replace(/[,;]/g, ' ').slice(0, 300),
      'END:VEVENT', 'END:VCALENDAR'
    ].join('\r\n');
    return isi;
  }

  function unduhIcs(agenda) {
    var blob = new Blob([buatIcs(agenda)], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (agenda.slug || 'agenda') + '.ics';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    toast('Berkas .ics diunduh', 'calendar-check');
  }

  return {
    esc: esc, loadData: loadData, items: items,
    // Ikon & utilitas gaya: memakai ulang helper dari config.js
    ico: function (nama, kelas) { return SP.ico(nama, kelas); },
    ikonKelas: function (nama, varian) { return SP.ikonKelas(nama, varian); },
    imgKartu: function (p, skala) { return SP.imgKartu(p, skala); },
    waktuRelatif: waktuRelatif, tglPanjang: tglPanjang, tglPendek: tglPendek,
    rupiah: rupiah, menitBaca: menitBaca, cekBuka: cekBuka,
    kartuBerita: kartuBerita, kartuWisata: kartuWisata, kartuKuliner: kartuKuliner,
    kartuDestinasi: kartuDestinasi, destinasiWisata: destinasiWisata, destinasiKuliner: destinasiKuliner,
    kartuBeritaLead: kartuBeritaLead, tileFoto: tileFoto, tileTeks: tileTeks,
    barisKuliner: barisKuliner, tileUmkm: tileUmkm,
    kartuUmkm: kartuUmkm, kartuAgenda: kartuAgenda, kartuLoker: kartuLoker,
    itemLalin: itemLalin, kartuSosmed: kartuSosmed, barisNomor: barisNomor,
    kartuTitikPeta: kartuTitikPeta,
    isi: isi, pesanKosong: pesanKosong, toast: toast, salin: salin,
    toggleSimpan: toggleSimpan, sudahDisimpan: sudahDisimpan, daftarSimpan: daftarSimpan,
    bucketHarga: bucketHarga, unduhIcs: unduhIcs, buatIcs: buatIcs
  };
})();
