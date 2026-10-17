/* ==========================================================================
   Sudut Pandaan — pages.js
   Router sederhana: setiap "halaman" dikenali dari elemen penanda di DOM,
   lalu dirender dari data JSON. Tidak ada framework, hanya JS vanilla.
   ========================================================================== */
(function () {
  'use strict';
  var UI = window.SP_UI;

  /* ----------------------------- util lokal ----------------------------- */
  function qs(s, r) { return (r || document).querySelector(s); }
  function qsa(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function param(nama) { return new URLSearchParams(location.search).get(nama); }

  function urutkanTanggal(arr, key, naik) {
    return arr.slice().sort(function (a, b) {
      var da = new Date(a[key] || 0), db = new Date(b[key] || 0);
      return naik ? da - db : db - da;
    });
  }

  function kategoriNama(slug) {
    var kat = (UI._data && UI._data.kategori) || [];
    var found = kat.filter(function (k) { return k.slug === slug; })[0];
    return found ? found.nama : slug;
  }

  /* ============================== BERANDA ===============================
     Tata letak "Majalah + Bento": masthead statis dari build, sisanya
     diisi dari data JSON. Petak besar (.b-8) = berita utama, petak kecil
     (.b-3/.b-4/.b-6) = destinasi, kuliner, angka, dan UMKM. */
  function home(d) {
    var berita = urutkanTanggal(UI.items(d.berita), 'tanggal');
    var wisata = UI.items(d.wisata);
    var kuliner = UI.items(d.kuliner);
    var umkm = UI.items(d.umkm);

    /* --- Bento 1: berita utama + 2 kartu sisi --- */
    var utama = qs('[data-bento-utama]');
    if (utama) {
      utama.innerHTML = berita.length
        ? UI.kartuBeritaLead(berita[0], { prioritas: true })
        : UI.pesanKosong('Belum ada berita.', 'newspaper');
    }
    var sisi = qs('[data-bento-sisi]');
    if (sisi) {
      sisi.innerHTML = berita.slice(1, 3).map(function (b) {
        return UI.tileFoto({
          href: SP.url('berita/' + b.slug + '.html'),
          gambar: SP.imgKartu(b.gambar, 0.5),
          alt: b.judul,
          judul: b.judul,
          judulKelas: 'h6',
          kicker: kategoriNama(b.kategori_slug),
          kelas: 'tile-pendek',
          meta: UI.waktuRelatif ? UI.waktuRelatif(b.tanggal) : ''
        });
      }).join('') || UI.pesanKosong('Belum ada berita lain.', 'newspaper');
    }

    /* --- Bento 1: satu destinasi + satu kuliner sebagai petak foto --- */
    var bd = qs('[data-bento-destinasi]');
    if (bd) {
      var w0 = (wisata.filter(function (w) { return w.is_featured; })[0] || wisata[0]);
      bd.innerHTML = w0 ? UI.tileFoto({
        href: SP.url('wisata/' + w0.slug + '.html'),
        gambar: SP.imgKartu(w0.gambar, 0.6),
        alt: w0.nama,
        judul: w0.nama,
        judulKelas: 'h5',
        kicker: 'Wisata · ' + (w0.kategori || w0.desa || 'Pandaan'),
        teks: w0.ringkasan || w0.deskripsi_singkat || ''
      }) : UI.pesanKosong('Belum ada data wisata.', 'mountains');
    }
    var bk = qs('[data-bento-kuliner]');
    if (bk) {
      var k0 = (kuliner.filter(function (k) { return k.is_featured; })[0] || kuliner[0]);
      bk.innerHTML = k0 ? UI.tileFoto({
        href: SP.url('kuliner/' + k0.slug + '.html'),
        gambar: SP.imgKartu(k0.gambar, 0.6),
        alt: k0.nama,
        judul: k0.nama,
        judulKelas: 'h5',
        kicker: 'Kuliner · ' + (k0.jenis || k0.desa || 'Pandaan'),
        teks: k0.harga_per_orang ? 'Kisaran ' + k0.harga_per_orang + ' (cek ulang)' : ''
      }) : UI.pesanKosong('Belum ada data kuliner.', 'bowl-food');
    }

    /* --- 01 Destinasi: rail geser --- */
    var railW = qs('[data-list="wisata-sorotan"]');
    if (railW) {
      var unggulan = wisata.filter(function (w) { return w.is_featured; });
      if (unggulan.length < 3) unggulan = unggulan.concat(wisata).slice(0, 6);
      railW.innerHTML = (unggulan.length ? unggulan : wisata).slice(0, 8).map(function (w) {
        return '<div class="rail-item">' + UI.tileFoto({
          href: SP.url('wisata/' + w.slug + '.html'),
          gambar: SP.imgKartu(w.gambar, 0.6),
          alt: w.nama,
          judul: w.nama,
          judulKelas: 'h5',
          kicker: (w.kategori || 'Wisata'),
          teks: w.ringkasan || '',
          meta: (w.harga_tiket ? w.harga_tiket + ' (cek ulang)' : '')
        }) + '</div>';
      }).join('') || UI.pesanKosong('Belum ada destinasi.', 'mountains');
    }

    /* --- 02 Kuliner: 4 petak foto + daftar harga bernomor --- */
    var kf = qs('[data-list="kuliner-foto"]');
    if (kf) {
      var limK = +kf.getAttribute('data-limit') || 4;
      var kp = kuliner.filter(function (k) { return k.is_featured; });
      if (kp.length < limK) kp = kp.concat(kuliner.filter(function (k) { return !k.is_featured; }));
      kf.innerHTML = kp.slice(0, limK).map(function (k) {
        return '<div class="b-6">' + UI.tileFoto({
          href: SP.url('kuliner/' + k.slug + '.html'),
          gambar: SP.imgKartu(k.gambar, 0.5),
          alt: k.nama,
          judul: k.nama,
          judulKelas: 'h6',
          kicker: (k.jenis || 'Kuliner') + (k.desa ? ' · ' + k.desa : ''),
          kelas: 'tile-pendek'
        }) + '</div>';
      }).join('') || UI.pesanKosong('Belum ada data kuliner.', 'bowl-food');
    }
    var kd = qs('[data-list="kuliner-daftar"]');
    if (kd) {
      var limD = +kd.getAttribute('data-limit') || 6;
      var kdItems = urutkanTanggal(kuliner, 'nama', true).slice(0, limD);
      kd.innerHTML = kdItems.map(function (k, i) { return UI.barisKuliner(k, i + 1); }).join('') ||
        UI.pesanKosong('Belum ada daftar harga.', 'list-magnifying-glass');
    }

    /* --- 03 UMKM: petak kecil (b-3) --- */
    var um = qs('[data-list="umkm-pilihan"]');
    if (um) {
      var limU = +um.getAttribute('data-limit') || 4;
      var up = umkm.slice().sort(function (a, b) {
        var pa = (b.paket === 'premium') - (a.paket === 'premium');
        return pa || ((b.is_verified === true) - (a.is_verified === true));
      }).slice(0, limU);
      um.innerHTML = up.map(function (u) { return '<div class="b-3">' + UI.tileUmkm(u) + '</div>'; }).join('') ||
        UI.pesanKosong('Belum ada UMKM.', 'storefront');
    }

    /* --- 04 Berita: rail + tab kategori --- */
    var railB = qs('[data-list="berita-lead"]');
    if (railB) {
      var limB = +railB.getAttribute('data-limit') || 8;
      // Berita teratas sudah tampil di bento pembuka → rail mulai dari nomor 4
      railB.innerHTML = berita.slice(3, 3 + limB).map(function (b) {
        return '<div class="rail-item">' + UI.tileFoto({
          href: SP.url('berita/' + b.slug + '.html'),
          gambar: SP.imgKartu(b.gambar, 0.5),
          alt: b.judul,
          judul: b.judul,
          judulKelas: 'h6',
          kicker: kategoriNama(b.kategori_slug),
          meta: (UI.waktuRelatif ? UI.waktuRelatif(b.tanggal) : '') +
                (b.lokasi ? ' · ' + b.lokasi : '')
        }) + '</div>';
      }).join('') || UI.pesanKosong('Belum ada berita.', 'newspaper');
    }

    qsa('[data-list="kategori-berita"]').forEach(function (el) {
      var slug = el.getAttribute('data-kategori');
      var limitK = +el.getAttribute('data-limit') || 3;
      var items = berita.filter(function (b) { return b.kategori_slug === slug; }).slice(0, limitK);
      el.innerHTML = items.map(function (b) {
        return UI.kartuBerita(b, { col: 'col-12 col-sm-6 col-lg-4', skalaGambar: 0.5 });
      }).join('') || UI.pesanKosong('Belum ada berita pada kategori ini.', 'newspaper');
    });

    /* --- 08 Sosial media --- */
    var sos = qs('[data-list="sosmed"]');
    if (sos) {
      var limS = +sos.getAttribute('data-limit') || 6;
      sos.innerHTML = UI.items(d.sosmed).slice(0, limS).map(function (s) {
        return '<div class="rail-item">' + UI.tileFoto({
          href: s.url, luar: true,
          gambar: SP.imgKartu(s.gambar, 0.5),
          alt: s.alt || ('Ilustrasi postingan ' + s.platform),
          judul: s.caption,
          judulKelas: 'h6',
          kicker: s.platform + ' · ' + s.jenis,
          meta: UI.waktuRelatif(s.tanggal)
        }) + '</div>';
      }).join('') || UI.pesanKosong('Belum ada konten sosial media.', 'instagram-logo');
    }
  }

  /* ============================ DAFTAR BERITA =========================== */
  function beritaIndex(d) {
    var wrap = qs('[data-page="berita-index"]');
    if (!wrap) return;
    var state = {
      q: param('q') || '',
      kategori: param('kategori') || '',
      urut: param('urut') || 'baru',
      halaman: parseInt(param('halaman') || '1', 10) || 1,
      perHalaman: 12
    };

    var inputQ = qs('#qBerita'), selUrut = qs('#urutBerita'), info = qs('#hasilInfo');
    var pag = qs('#paginasiBerita'), resetBtn = qs('#resetFilterBerita');
    var blokLain = qs('#blokHasilLain'), kotakLain = qs('#hasilLain');

    /* --- URL: setiap perubahan filter ditulis ke address bar, sehingga tautan
       hasil filter bisa dibagikan, di-bookmark, dan tetap sama saat di-refresh.
       (tanpa memuat ulang halaman) --- */
    function urlUntuk(ubah) {
      var v = {};
      for (var k in state) { if (k !== 'perHalaman') v[k] = state[k]; }
      for (var k2 in (ubah || {})) v[k2] = ubah[k2];
      var p = [];
      if (v.q) p.push('q=' + encodeURIComponent(v.q));
      if (v.kategori) p.push('kategori=' + encodeURIComponent(v.kategori));
      if (v.urut && v.urut !== 'baru') p.push('urut=' + encodeURIComponent(v.urut));
      if (v.halaman && v.halaman > 1) p.push('halaman=' + v.halaman);
      // Nama berkas relatif (bukan location.pathname yang absolut) supaya tetap
      // benar saat di-hosting di subfolder maupun dibuka lewat file://.
      return p.length ? '?' + p.join('&') : (location.pathname.split('/').pop() || 'index.html');
    }

    function sinkronUrl() {
      try { history.replaceState(null, '', urlUntuk()); } catch (e) { /* file:// */ }
      // Tautan chip & paginasi ikut disesuaikan agar tetap benar saat dibuka
      // di tab baru / dibagikan.
      qsa('#filterKategori .chip').forEach(function (a) {
        var slug = kategoriDariChip(a);
        a.setAttribute('href', urlUntuk({ kategori: slug, halaman: 1 }));
        a.classList.toggle('active', slug === state.kategori);
      });
    }

    function kategoriDariChip(a) {
      var href = a.getAttribute('href') || '';
      var m = href.match(/kategori=([^&]*)/);
      return m ? decodeURIComponent(m[1]) : '';
    }

    if (inputQ) inputQ.value = state.q;
    if (selUrut) selUrut.value = state.urut;

    function pilih() {
      var q = state.q.toLowerCase().trim();
      return UI.items(d.berita).filter(function (b) {
        if (state.kategori && b.kategori_slug !== state.kategori) return false;
        if (!q) return true;
        var teks = [b.judul, b.ringkasan, b.kategori, b.penulis, (b.tags || []).join(' '),
          String(b.isi || '').replace(/<[^>]+>/g, ' ')].join(' ').toLowerCase();
        return teks.indexOf(q) >= 0;
      });
    }

    /* --- Pencarian lintas jenis: kotak pencarian di navbar menjanjikan cakupan
       berita + wisata + kuliner + UMKM, jadi hasil non-berita ditampilkan di
       blok terpisah (bukan diklaim tanpa bukti). --- */
    function hasilLain(q) {
      if (!blokLain || !kotakLain) return;
      if (!q) { blokLain.classList.add('d-none'); kotakLain.innerHTML = ''; return; }
      var kata = q.toLowerCase();
      var sumber = [
        ['Wisata', UI.items(d.wisata), function (x) { return SP.url('wisata/' + x.slug + '.html'); }, 'kategori'],
        ['Kuliner', UI.items(d.kuliner), function (x) { return SP.url('kuliner/' + x.slug + '.html'); }, 'jenis_masakan'],
        ['UMKM', UI.items(d.umkm), function (x) { return SP.url('umkm/' + x.slug + '.html'); }, 'kategori']
      ];
      var kartu = [];
      sumber.forEach(function (grup) {
        grup[1].forEach(function (x) {
          var nama = x.nama || x.nama_usaha || '';
          var teks = [nama, x.ringkasan, x.desa, grup[3] ? x[grup[3]] : '', (x.fasilitas || []).join(' ')]
            .join(' ').toLowerCase();
          if (teks.indexOf(kata) < 0) return;
          kartu.push('<div class="col-12 col-md-6"><div class="info-box h-100 py-2">' +
            '<div class="small text-muted-2">' + UI.esc(grup[0]) + (x.desa ? ' · ' + UI.esc(x.desa) : '') + '</div>' +
            '<a class="fw-semibold text-decoration-none" href="' + grup[2](x) + '">' + UI.esc(nama) + '</a>' +
            '</div></div>');
        });
      });
      kotakLain.innerHTML = kartu.join('');
      blokLain.classList.toggle('d-none', kartu.length === 0);
    }

    function render(pindahHalaman) {
      var hasil = pilih();
      if (state.urut === 'populer') hasil = hasil.slice().sort(function (a, b) { return (b.views || 0) - (a.views || 0); });
      else if (state.urut === 'judul') hasil = hasil.slice().sort(function (a, b) { return a.judul.localeCompare(b.judul, 'id'); });
      else hasil = urutkanTanggal(hasil, 'tanggal');

      var total = hasil.length;
      var maxHal = Math.max(1, Math.ceil(total / state.perHalaman));
      if (state.halaman > maxHal) state.halaman = maxHal;
      if (state.halaman < 1) state.halaman = 1;
      var mulai = (state.halaman - 1) * state.perHalaman;
      var halIni = hasil.slice(mulai, mulai + state.perHalaman);

      UI.isi('#daftarBerita', halIni.map(function (b) { return UI.kartuBerita(b); }).join('') ||
        UI.pesanKosong('Tidak ada berita yang cocok. Coba kata kunci lain atau tekan tombol Reset.', 'search'));

      if (info) {
        var labelKat = state.kategori ? ' kategori “' + kategoriNama(state.kategori) + '”' : '';
        var labelQ = state.q ? ' untuk pencarian “' + state.q + '”' : '';
        info.textContent = total
          ? 'Menampilkan ' + (mulai + 1) + '–' + Math.min(mulai + state.perHalaman, total) + ' dari ' + total +
            ' berita' + labelKat + labelQ + '.'
          : 'Tidak ada berita' + labelKat + labelQ + '.';
      }

      hasilLain(state.q);

      // Paginasi: tautan href nyata (bisa dibuka di tab baru / oleh crawler),
      // klik biasa ditangani tanpa memuat ulang halaman.
      if (pag) {
        var html = '';
        function li(label, hal, aktif, nonaktif, sr) {
          var isi = sr ? '<span class="visually-hidden">' + sr + '</span>' + label : label;
          if (nonaktif) {
            return '<li class="page-item disabled"><span class="page-link" aria-disabled="true">' + isi + '</span></li>';
          }
          return '<li class="page-item' + (aktif ? ' active' : '') + '">' +
            '<a class="page-link" href="' + urlUntuk({ halaman: hal }) + '" data-hal="' + hal + '"' +
            (aktif ? ' aria-current="page"' : '') + '>' + isi + '</a></li>';
        }
        if (maxHal > 1) {
          html += li('&laquo;', state.halaman - 1, false, state.halaman === 1, 'Halaman sebelumnya');
          for (var i = 1; i <= maxHal; i++) html += li(i, i, i === state.halaman, false);
          html += li('&raquo;', state.halaman + 1, false, state.halaman === maxHal, 'Halaman berikutnya');
        }
        pag.innerHTML = html;
      }

      sinkronUrl();
      if (pindahHalaman && info && info.offsetTop) {
        window.scrollTo({ top: info.offsetTop - 120, behavior: prefersReduced() ? 'auto' : 'smooth' });
      }
    }

    function prefersReduced() {
      return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    var form = qs('form[role="search"][aria-label="Pencarian berita"]');
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault();
      state.q = (inputQ && inputQ.value) || '';
      state.halaman = 1;
      render();
    });
    if (inputQ) {
      inputQ.addEventListener('input', debounce(function () {
        state.q = inputQ.value; state.halaman = 1; render();
      }, 300));
      // Esc = kosongkan pencarian (kebiasaan umum pada kolom pencarian).
      inputQ.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        inputQ.value = ''; state.q = ''; state.halaman = 1; render();
      });
    }
    if (selUrut) selUrut.addEventListener('change', function () {
      state.urut = selUrut.value; state.halaman = 1; render();
    });

    // Chip kategori: tanpa muat ulang, tetapi href-nya tetap URL yang benar.
    qsa('#filterKategori .chip').forEach(function (a) {
      a.addEventListener('click', function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;   // biarkan tab baru
        e.preventDefault();
        state.kategori = kategoriDariChip(a);
        state.halaman = 1;
        render();
      });
    });

    if (resetBtn) resetBtn.addEventListener('click', function () {
      state.q = ''; state.kategori = ''; state.urut = 'baru'; state.halaman = 1;
      if (inputQ) inputQ.value = '';
      if (selUrut) selUrut.value = 'baru';
      render();
    });

    if (pag) pag.addEventListener('click', function (e) {
      var a = e.target.closest('a[data-hal]');
      if (!a) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
      e.preventDefault();
      state.halaman = parseInt(a.getAttribute('data-hal'), 10) || 1;
      render(true);
    });

    render();
    sidebar(d);
  }

  function direktori(d) {
    var wrap = qs('[data-page="direktori"]');
    if (!wrap) return;
    var jenis = wrap.getAttribute('data-jenis');             // wisata | kuliner | umkm
    var sumber = jenis === 'wisata' ? d.wisata : (jenis === 'kuliner' ? d.kuliner : d.umkm);
    var list = UI.items(sumber);
    var state = { q: '', kategori: 'semua', fasilitas: 'semua', harga: 'semua', desa: 'semua', verified: false, premium: false };

    var inputQ = qs('#qDirektori');
    var info = qs('#hasilInfoDirektori');

    function cocok(item) {
      if (state.q) {
        var teks = [item.nama, item.nama_usaha, item.ringkasan, item.deskripsi, item.jenis_masakan,
          item.kategori, (item.fasilitas || []).join(' '), (item.menu_andalan || []).join(' '),
          (item.produk || []).map(function (p) { return p.nama; }).join(' ')]
          .join(' ').toLowerCase();
        if (teks.indexOf(state.q.toLowerCase()) < 0) return false;
      }
      if (jenis === 'umkm') {
        if (state.kategori !== 'semua' && item.kategori !== state.kategori) return false;
        if (state.desa !== 'semua' && item.desa !== state.desa) return false;
        if (state.verified && !item.is_verified) return false;
        if (state.premium && item.paket !== 'premium') return false;
        return true;
      }
      if (state.kategori !== 'semua' && (item.kategori_filter || []).indexOf(state.kategori) < 0) return false;
      if (state.fasilitas !== 'semua' && (item.fasilitas || []).indexOf(state.fasilitas) < 0) return false;
      if (state.harga !== 'semua' && UI.bucketHarga(item) !== state.harga) return false;
      return true;
    }

    function render() {
      var hasil = list.filter(cocok);
      var kartu = jenis === 'wisata' ? UI.kartuWisata : (jenis === 'kuliner' ? UI.kartuKuliner : UI.kartuUmkm);
      var col = jenis === 'umkm' ? 'col-6 col-lg-4 col-xl-3' : 'col-12 col-md-6 col-lg-4';
      UI.isi('#daftarDirektori', hasil.map(function (i) { return kartu(i, { col: col }); }).join('') ||
        UI.pesanKosong('Tidak ada entri yang cocok dengan filter. Coba perluas filter atau reset.', 'search'));
      if (info) {
        info.textContent = 'Menampilkan ' + hasil.length + ' dari ' + list.length + ' entri' +
          (state.kategori !== 'semua' ? ' · kategori: ' + state.kategori : '') +
          (state.desa && state.desa !== 'semua' ? ' · desa: ' + state.desa : '') +
          (state.verified ? ' · terverifikasi saja' : '') + '.';
      }
    }

    if (inputQ) inputQ.addEventListener('input', debounce(function () { state.q = inputQ.value; render(); }, 250));

    qsa('[data-filter]', wrap).forEach(function (el) {
      var kind = el.getAttribute('data-filter');
      if (el.type === 'checkbox') {
        el.addEventListener('change', function () {
          if (kind === 'verified') state.verified = el.checked;
          if (kind === 'premium') state.premium = el.checked;
          render();
        });
      } else {
        el.addEventListener('click', function () {
          state[kind] = el.getAttribute('data-value');
          // chip sejenis jadi "semua", chip yang dipilih jadi aktif
          qsa('[data-filter="' + kind + '"]', wrap).forEach(function (c) {
            if (c.type === 'checkbox') return;
            var aktif = c === el;
            c.classList.toggle('active', aktif);
            c.setAttribute('aria-pressed', aktif ? 'true' : 'false');
          });
          render();
        });
      }
    });

    var reset = qs('#resetFilter');
    if (reset) reset.addEventListener('click', function () {
      state = { q: '', kategori: 'semua', fasilitas: 'semua', harga: 'semua', desa: 'semua', verified: false, premium: false };
      if (inputQ) inputQ.value = '';
      qsa('[data-filter]', wrap).forEach(function (el) {
        if (el.type === 'checkbox') { el.checked = false; return; }
        var aktif = el.getAttribute('data-value') === 'semua';
        el.classList.toggle('active', aktif);
        el.setAttribute('aria-pressed', aktif ? 'true' : 'false');
      });
      render();
    });

    render();
  }

  /* =============================== AGENDA ============================== */
  function agenda(d) {
    var wrap = qs('[data-page="agenda"]');
    if (!wrap) return;
    var list = UI.items(d.agenda).slice().sort(function (a, b) { return new Date(a.mulai) - new Date(b.mulai); });
    var sel = qs('#filterBulanAgenda'), info = qs('#hasilInfoAgenda');
    var bulan = list.map(function (a) {
      var dt = new Date(a.mulai);
      return { key: dt.getFullYear() + '-' + (dt.getMonth() + 1), label: UI.tglPanjang(a.mulai, false).replace(/^\w+, /, '').replace(/\s\d{4}$/, ' ' + dt.getFullYear()) };
    }).filter(function (b, i, arr) { return arr.findIndex(function (x) { return x.key === b.key; }) === i; });

    if (sel) {
      sel.innerHTML = '<option value="semua">Semua bulan</option>' + bulan.map(function (b) {
        return '<option value="' + b.key + '">' + UI.esc(b.label) + '</option>';
      }).join('');
    }

    function render() {
      var pilih = sel ? sel.value : 'semua';
      var hasil = list.filter(function (a) {
        if (pilih === 'semua') return true;
        var dt = new Date(a.mulai);
        return (dt.getFullYear() + '-' + (dt.getMonth() + 1)) === pilih;
      });
      UI.isi('#daftarAgenda', hasil.map(UI.kartuAgenda).join('') ||
        UI.pesanKosong('Belum ada agenda pada bulan ini.', 'calendar-x'));
      if (info) info.textContent = hasil.length + ' agenda ditampilkan' + (pilih !== 'semua' ? ' (hasil filter bulan).' : ' dari total ' + list.length + '.');
    }
    if (sel) sel.addEventListener('change', render);

    // Tombol "Semua bulan" pada bilah filter
    var resetBulan = qs('#resetBulanAgenda');
    if (resetBulan) resetBulan.addEventListener('click', function () {
      if (sel) sel.value = 'semua';
      render();
    });

    // Linimasa agenda terdekat (penanda tanggal + lokasi, gaya majalah)
    var lini = qs('#linimasaAgenda');
    if (lini) {
      var kini = new Date();
      var dekat = list.filter(function (a) { return new Date(a.mulai) >= kini; });
      if (!dekat.length) dekat = list.slice(0, 5);
      // Semua entri linimasa adalah agenda mendatang → penanda emas
      lini.innerHTML = dekat.slice(0, 5).map(function (a) {
        return '<li class="mendatang">' +
          '<span class="linimasa-tanggal">' + UI.tglPendek(a.mulai) + '</span><br>' +
          '<span class="linimasa-judul">' + UI.esc(a.judul) + '</span><br>' +
          '<span class="small text-muted-2"><i class="ph ph-map-pin me-1" aria-hidden="true"></i>' + UI.esc(a.lokasi) + '</span>' +
          '</li>';
      }).join('');
    }

    var eks = qs('#eksporIcs');
    if (eks) eks.addEventListener('click', function () {
      var pilih = sel ? sel.value : 'semua';
      var hasil = list.filter(function (a) {
        if (pilih === 'semua') return true;
        var dt = new Date(a.mulai);
        return (dt.getFullYear() + '-' + (dt.getMonth() + 1)) === pilih;
      });
      if (!hasil.length) { UI.toast('Tidak ada agenda untuk diekspor', 'exclamation-circle'); return; }
      hasil.forEach(function (a, i) { setTimeout(function () { UI.unduhIcs(a); }, i * 300); });
    });

    wrap.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-ics]');
      if (!btn) return;
      var slug = btn.getAttribute('data-ics');
      var a = list.filter(function (x) { return x.slug === slug; })[0];
      if (a) UI.unduhIcs(a);
    });

    render();
  }

  /* =============================== LOKER =============================== */
  function loker(d) {
    var wrap = qs('[data-page="loker"]');
    if (!wrap) return;
    var payload = d.loker || {};
    var list = UI.items(payload);
    var sel = qs('#filterJenisLoker'), car = qs('#cariLoker'), info = qs('#hasilInfoLoker');

    function render() {
      var jenis = sel ? sel.value : 'semua';
      var q = car ? car.value.toLowerCase() : '';
      var hasil = list.filter(function (l) {
        if (jenis !== 'semua') {
          if (jenis === 'Paruh waktu' && l.jenis.indexOf('Paruh waktu') < 0) return false;
          if (jenis !== 'Paruh waktu' && l.jenis.indexOf(jenis) < 0) return false;
        }
        if (q && (l.posisi + ' ' + l.perusahaan + ' ' + l.lokasi).toLowerCase().indexOf(q) < 0) return false;
        return true;
      }).sort(function (a, b) { return new Date(b.tanggal_posting) - new Date(a.tanggal_posting); });

      UI.isi('#daftarLoker', hasil.map(UI.kartuLoker).join('') ||
        UI.pesanKosong('Belum ada lowongan yang cocok.', 'briefcase'));
      if (info) info.textContent = hasil.length + ' lowongan ditampilkan dari ' + list.length + ' entri.';
    }
    if (sel) sel.addEventListener('change', render);
    if (car) car.addEventListener('input', debounce(render, 250));
    var resetLoker = qs('#resetLoker');
    if (resetLoker) resetLoker.addEventListener('click', function () {
      if (car) car.value = '';
      if (sel) sel.value = 'semua';
      render();
    });

    wrap.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-loker-detail]');
      if (!btn) return;
      var l = list.filter(function (x) { return x.slug === btn.getAttribute('data-loker-detail'); })[0];
      if (!l) return;
      modalInfo('Cara Melamar — ' + l.posisi,
        '<p class="small mb-2"><strong>' + UI.esc(l.perusahaan) + '</strong> · ' + UI.esc(l.lokasi) + '</p>' +
        '<p class="small mb-2">' + UI.esc(l.deskripsi) + '</p>' +
        '<p class="small mb-2"><strong>Kualifikasi:</strong> ' + UI.esc((l.kualifikasi || []).join(', ')) + '</p>' +
        '<p class="small mb-2"><strong>Gaji:</strong> ' + UI.esc(l.gaji) + ' · <strong>Batas lamaran:</strong> ' + UI.tglPendek(l.batas_waktu) + '</p>' +
        '<div class="alert alert-warning small mb-2">' + UI.esc(l.cara_melamar) + '</div>' +
        '<p class="small text-muted-2 mb-0">Periksa ulang kanal resmi perusahaan. Jangan membayar biaya apa pun.</p>');
    });

    render();
  }

  /* =========================== NOMOR PENTING =========================== */
  function nomorPenting(d) {
    var wrap = qs('[data-page="nomor-penting"]');
    if (!wrap) return;
    var list = UI.items(d['nomor-penting']);
    var input = qs('#cariNomor');
    function render() {
      var q = input ? input.value.toLowerCase() : '';
      var hasil = list.filter(function (n) {
        return !q || (n.instansi + ' ' + n.kategori + ' ' + n.keterangan).toLowerCase().indexOf(q) >= 0;
      });
      UI.isi('#daftarNomor', hasil.length ? hasil.map(UI.barisNomor).join('')
        : '<tr><td colspan="4"><div class="empty-state">' + UI.ico('telephone-x') + '<p class="mb-0">Tidak ada nomor yang cocok.</p></div></td></tr>');
    }
    if (input) input.addEventListener('input', debounce(render, 200));
    var resetNomor = qs('#resetNomor');
    if (resetNomor) resetNomor.addEventListener('click', function () {
      if (input) { input.value = ''; input.focus(); }
      render();
    });
    render();
  }

  /* ============================ LALU LINTAS ============================ */
  function laluLintas(d) {
    if (!qs('[data-page="lalu-lintas"]')) return;
    var payload = d['lalu-lintas'] || {};
    var list = UI.items(payload).slice().sort(function (a, b) { return new Date(b.waktu) - new Date(a.waktu); });
    UI.isi('#daftarLalin', list.map(UI.itemLalin).join('') ||
      '<div class="list-group-item px-0 text-muted-2">Belum ada laporan.</div>');
    var upd = qs('#updateTerakhir');
    if (upd && list[0]) upd.textContent = 'Pembaruan terakhir: ' + UI.tglPanjang(list[0].waktu, true);
  }

  /* ======================== SIDEBAR & BLOK TERKAIT ====================== */
  function sidebar(d) {
    var pop = qs('#sidebarPopuler');
    if (pop) {
      var top = UI.items(d.berita).slice().sort(function (a, b) { return (b.views || 0) - (a.views || 0); }).slice(0, 5);
      pop.innerHTML = top.map(function (b) {
        return '<li><a href="' + SP.url('berita/' + b.slug + '.html') + '">' + UI.esc(b.judul) + '</a></li>';
      }).join('');
    }
    var ag = qs('#sidebarAgenda');
    if (ag) {
      var dekat = UI.items(d.agenda).slice().sort(function (a, b) { return new Date(a.mulai) - new Date(b.mulai); }).slice(0, 3);
      ag.innerHTML = dekat.map(function (a) {
        return '<div class="mb-2 pb-2 border-bottom"><strong class="d-block">' + UI.esc(a.judul) + '</strong>' +
          '<span>' + UI.tglPanjang(a.mulai, false) + '</span><br><span>' + UI.esc(a.lokasi) + '</span></div>';
      }).join('') + '<a class="small" href="' + SP.url('layanan/agenda.html') + '">Lihat semua agenda ' + UI.ico('arrow-right') + '</a>';
    }
  }

  function blokTerkait(d) {
    qsa('[data-list="terkait-berita"]').forEach(function (el) {
      var kat = el.getAttribute('data-kategori');
      var kecuali = el.getAttribute('data-exclude');
      var limit = +el.getAttribute('data-limit') || 4;
      var list = urutkanTanggal(UI.items(d.berita), 'tanggal')
        .filter(function (b) { return b.slug !== kecuali; })
        .sort(function (a, b) {
          var sa = (a.kategori_slug === kat ? 0 : 1), sb = (b.kategori_slug === kat ? 0 : 1);
          if (sa !== sb) return sa - sb;
          return new Date(b.tanggal) - new Date(a.tanggal);
        }).slice(0, limit);
      el.innerHTML = list.map(function (b) {
        return UI.kartuBerita(b, { col: 'col-12 col-md-6' });
      }).join('');
    });

    qsa('[data-list="sekitar"]').forEach(function (el) {
      var desa = el.getAttribute('data-desa');
      var limit = +el.getAttribute('data-limit') || 3;
      var kulin = UI.items(d.kuliner).filter(function (k) { return k.desa === desa; });
      if (kulin.length < limit) {
        kulin = kulin.concat(UI.items(d.kuliner).filter(function (k) {
          return k.desa !== desa && kulin.indexOf(k) < 0;
        }));
      }
      var umk = UI.items(d.umkm).filter(function (u) { return u.desa === desa; });
      var gabung = kulin.slice(0, limit).map(function (k) { return { tipe: 'kuliner', o: k }; })
        .concat(umk.slice(0, Math.max(1, limit - 2)).map(function (u) { return { tipe: 'umkm', o: u }; }));
      el.innerHTML = gabung.map(function (x) {
        return x.tipe === 'kuliner'
          ? UI.kartuKuliner(x.o, { col: 'col-12 col-md-6 col-lg-4' })
          : UI.kartuUmkm(x.o, { col: 'col-12 col-md-6 col-lg-4' });
      }).join('') || UI.pesanKosong('Belum ada data sekitar.', 'geo');
    });

    qsa('[data-list="panduan-lain"]').forEach(function (el) {
      var kecuali = el.getAttribute('data-exclude');
      var limit = +el.getAttribute('data-limit') || 3;
      var list = UI.items(d.panduan).filter(function (p) { return p.slug !== kecuali; }).slice(0, limit);
      el.innerHTML = list.map(function (p) {
        return '<div class="col-12 col-md-6 col-lg-4"><article class="card card-news h-100">' +
          '<div class="card-img-wrap"><a href="' + SP.url('panduan/' + p.slug + '.html') + '" tabindex="-1" aria-hidden="true">' +
          '<img src="' + SP.img(p.gambar) + '" alt="' + UI.esc(p.judul) + '" loading="lazy" width="800" height="500"></a></div>' +
          '<div class="card-body"><h3 class="card-title h6 mb-2"><a class="stretched-link text-decoration-none" href="' +
          SP.url('panduan/' + p.slug + '.html') + '">' + UI.esc(p.judul) + '</a></h3>' +
          '<p class="small text-muted-2 clamp-3 mb-0">' + UI.esc(p.ringkasan) + '</p></div></article></div>';
      }).join('');
    });
  }

  /* ========================== DAFTAR TITIK PETA ======================== */
  function daftarTitik(d) {
    var el = qs('#daftarTitik');
    if (!el) return;
    var titik = [];
    UI.items(d.wisata).forEach(function (w) {
      titik.push({ jenis: 'wisata', label: 'Wisata', nama: w.nama, lat: w.lat, lng: w.lng, catatan: w.ringkasan, href: SP.url('wisata/' + w.slug + '.html') });
    });
    UI.items(d.kuliner).forEach(function (k) {
      titik.push({ jenis: 'kuliner', label: 'Kuliner', nama: k.nama, lat: k.lat, lng: k.lng, catatan: k.jenis_masakan + ' · ' + k.harga_per_orang, href: SP.url('kuliner/' + k.slug + '.html') });
    });
    UI.items(d.umkm).forEach(function (u) {
      titik.push({ jenis: 'umkm', label: 'UMKM', nama: u.nama_usaha, lat: u.lat, lng: u.lng, catatan: u.kategori + ' · ' + u.desa, href: SP.url('umkm/' + u.slug + '.html') });
    });
    SP.fasilitas.forEach(function (f) {
      titik.push({ jenis: 'fasilitas', label: 'Fasilitas umum', nama: f.nama, lat: f.lat, lng: f.lng, catatan: f.catatan });
    });
    SP.titikMacet.forEach(function (f) {
      titik.push({ jenis: 'macet', label: 'Rawan macet', nama: f.nama, lat: f.lat, lng: f.lng, catatan: f.catatan });
    });

    var cari = qs('#cariTitikPeta');
    function render() {
      var q = cari ? cari.value.toLowerCase() : '';
      var aktif = qsa('#filterPeta input:checked').map(function (c) { return c.value; });
      var hasil = titik.filter(function (t) {
        if (aktif.indexOf(t.jenis) < 0) return false;
        return !q || (t.nama + ' ' + (t.catatan || '')).toLowerCase().indexOf(q) >= 0;
      });
      el.innerHTML = hasil.map(UI.kartuTitikPeta).join('') ||
        UI.pesanKosong('Tidak ada titik yang cocok.', 'geo-alt');
      el.setAttribute('data-jumlah', hasil.length);
    }
    if (cari) cari.addEventListener('input', debounce(render, 200));
    qsa('#filterPeta input').forEach(function (c) { c.addEventListener('change', render); });

    el.addEventListener('click', function (e) {
      var b = e.target.closest('[data-fokus-peta]');
      if (!b) return;
      var p = b.getAttribute('data-fokus-peta').split(',');
      if (window.SP_MAP && SP_MAP.fokus) SP_MAP.fokus(parseFloat(p[0]), parseFloat(p[1]));
    });

    render();
  }

  /* ================================ FORM =============================== */
  function forms(d) {
    // 1) Lapor / kirim info
    var fLapor = qs('#formLapor');
    if (fLapor) {
      fLapor.addEventListener('submit', function (e) {
        e.preventDefault();
        if (fLapor.querySelector('.sp-hp').value) return;             // honeypot
        if (!validasi(fLapor)) return;
        var t = [
          '*LAPORAN WARGA — SUDUT PANDAAN*',
          'Nama: ' + (fLapor.nama.value || 'anonim'),
          'Kontak: ' + fLapor.kontak.value,
          'Jenis: ' + fLapor.jenis.value,
          'Desa/Kelurahan: ' + fLapor.desa.value,
          'Lokasi: ' + fLapor.lokasi.value,
          'Waktu: ' + fLapor.waktu.value.replace('T', ' ') + ' WIB',
          'Media: ' + (fLapor.media.value || '-'),
          'Isi: ' + fLapor.isi.value,
          'Izin publikasi: ya'
        ].join('\n');
        window.open('https://wa.me/' + SP.waAdmin + '?text=' + encodeURIComponent(t), '_blank', 'noopener');
        UI.toast('Laporan disiapkan di WhatsApp. Tekan kirim untuk mengirimkan.', 'whatsapp');
      });
      var btnEmail = qs('#kirimEmail');
      if (btnEmail) btnEmail.addEventListener('click', function () {
        if (!validasi(fLapor)) return;
        var isi = 'Lokasi: ' + fLapor.lokasi.value + '\nWaktu: ' + fLapor.waktu.value.replace('T', ' ') +
          '\nJenis: ' + fLapor.jenis.value + '\nDesa: ' + fLapor.desa.value +
          '\nKontak: ' + fLapor.kontak.value + '\nMedia: ' + (fLapor.media.value || '-') +
          '\n\n' + fLapor.isi.value;
        location.href = 'mailto:' + SP.email + '?subject=' +
          encodeURIComponent('Laporan warga: ' + fLapor.jenis.value) + '&body=' + encodeURIComponent(isi);
      });
    }

    // 2) Pendaftaran UMKM
    var fUmkm = qs('#formUmkm');
    if (fUmkm) {
      var desk = qs('#deskripsiUsaha'), sisa = qs('#sisaKarakter');
      if (desk && sisa) desk.addEventListener('input', function () { sisa.textContent = 500 - desk.value.length; });
      var wa = qs('#waUsaha');
      if (wa) wa.addEventListener('blur', function () {
        var v = wa.value.replace(/\D/g, '');
        if (v.indexOf('0') === 0) wa.value = '62' + v.slice(1);
      });
      fUmkm.addEventListener('submit', function (e) {
        e.preventDefault();
        if (fUmkm.querySelector('.sp-hp').value) return;
        if (!validasi(fUmkm)) return;
        var t = [
          '*PENDAFTARAN UMKM — SUDUT PANDAAN*',
          'Nama usaha: ' + fUmkm.nama_usaha.value,
          'Pemilik: ' + fUmkm.pemilik.value,
          'Kategori: ' + fUmkm.kategori.value,
          'Desa/Kelurahan: ' + fUmkm.desa.value,
          'Alamat: ' + fUmkm.alamat.value,
          'WhatsApp: ' + fUmkm.whatsapp.value,
          'Instagram/marketplace: ' + (fUmkm.instagram.value || '-'),
          'Jam operasional: ' + (fUmkm.jam.value || '-'),
          'Google Maps: ' + (fUmkm.maps.value || '-'),
          'Tautan foto: ' + (fUmkm.foto.value || '-'),
          'Deskripsi: ' + fUmkm.deskripsi.value,
          'Persetujuan data: ya (UU PDP)'
        ].join('\n');
        window.open('https://wa.me/' + SP.waAdmin + '?text=' + encodeURIComponent(t), '_blank', 'noopener');
        UI.toast('Pendaftaran disiapkan di WhatsApp. Tekan kirim untuk mengirimkan.', 'whatsapp');
      });
    }

    // 3) Kontak
    var fKontak = qs('#formKontak');
    if (fKontak) fKontak.addEventListener('submit', function (e) {
      e.preventDefault();
      if (fKontak.querySelector('.sp-hp').value) return;
      if (!validasi(fKontak)) return;
      var isi = 'Nama: ' + fKontak.nama.value + '\nEmail: ' + fKontak.email.value + '\n\n' + fKontak.pesan.value;
      location.href = 'mailto:' + SP.email + '?subject=' + encodeURIComponent('[' + fKontak.subjek.value + '] Pesan dari situs') +
        '&body=' + encodeURIComponent(isi);
      UI.toast('Membuka aplikasi email…', 'envelope');
    });

    // 4) Newsletter (belum tersambung ke layanan email)
    var fLang = qs('#formLangganan');
    if (fLang) fLang.addEventListener('submit', function (e) {
      e.preventDefault();
      var em = qs('#emailLangganan');
      if (!em.checkValidity()) { em.classList.add('is-invalid'); return; }
      em.classList.remove('is-invalid');
      UI.toast('Terima kasih! Form ini belum tersambung ke layanan email (lihat catatan).', 'info-circle');
    });
  }

  function validasi(form) {
    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      var pertama = form.querySelector(':invalid');
      if (pertama) { pertama.focus(); pertama.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
      return false;
    }
    form.classList.remove('was-validated');
    return true;
  }

  /* ------------------------ modal info generik ------------------------- */
  function modalInfo(judul, isiHtml) {
    var el = document.getElementById('spModalInfo');
    if (!el) {
      el = document.createElement('div');
      el.id = 'spModalInfo';
      el.className = 'modal fade';
      el.tabIndex = -1;
      el.setAttribute('aria-hidden', 'true');
      el.innerHTML = '<div class="modal-dialog modal-dialog-centered"><div class="modal-content rounded-card">' +
        '<div class="modal-header"><h2 class="h6 mb-0" id="spModalInfoJudul"></h2>' +
        '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Tutup"></button></div>' +
        '<div class="modal-body" id="spModalInfoIsi"></div></div></div>';
      document.body.appendChild(el);
    }
    qs('#spModalInfoJudul', el).textContent = judul;
    qs('#spModalInfoIsi', el).innerHTML = isiHtml;
    if (window.bootstrap) bootstrap.Modal.getOrCreateInstance(el).show();
  }

  function debounce(fn, ms) {
    var t; return function () { var a = arguments, s = this; clearTimeout(t); t = setTimeout(function () { fn.apply(s, a); }, ms || 250); };
  }

  /* ============================== ROUTER ============================== */
  function renderAll() {
    return UI.loadData().then(function (d) {
      var tugas = [];
      if (qs('[data-list="berita-lead"]') || qs('[data-list="berita-terbaru"]')) tugas.push(home(d));
      if (qs('[data-page="berita-index"]')) tugas.push(beritaIndex(d));
      if (qs('[data-page="direktori"]')) tugas.push(direktori(d));
      if (qs('[data-page="agenda"]')) tugas.push(agenda(d));
      if (qs('[data-page="loker"]')) tugas.push(loker(d));
      if (qs('[data-page="nomor-penting"]')) tugas.push(nomorPenting(d));
      if (qs('[data-page="lalu-lintas"]')) tugas.push(laluLintas(d));
      if (qs('#daftarTitik')) tugas.push(daftarTitik(d));
      blokTerkait(d);
      if (!qs('[data-list="berita-lead"]') && !qs('[data-list="berita-terbaru"]')) sidebar(d);
      forms(d);
      return tugas;
    }).catch(function (err) {
      // Jaring pengaman: tampilkan pesan ramah daripada halaman kosong
      if (window.console) console.error('[Sudut Pandaan] Gagal memuat data:', err);
      var pesan = UI.pesanKosong('Data belum dapat dimuat. Jika Anda membuka berkas langsung (file://), jalankan pratinjau dengan server lokal: python3 -m http.server 8080', 'exclamation-triangle');
      qsa('[data-list], #daftarBerita, #daftarDirektori, #daftarAgenda, #daftarLoker, #daftarLalin, #daftarNomor').forEach(function (el) {
        el.innerHTML = pesan;
      });
    });
  }

  window.SP_PAGES = { renderAll: renderAll };

  // Render SEKARANG (bukan menunggu DOMContentLoaded): data sudah tersedia dari
  // sematan hasil build, sehingga kartu tampil pada paint pertama dan tata letak
  // tidak bergeser setelahnya (CLS kecil).
  function mulai() {
    renderAll().then(function () {
      document.dispatchEvent(new Event('sp:rendered'));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mulai);
  } else {
    mulai();
  }

  // JSON di assets/data/ berbeda dengan data sematan (redaksi baru menyunting)
  // → gambar ulang daftar dengan data terbaru.
  document.addEventListener('sp:data-baru', function () { mulai(); });
})();
