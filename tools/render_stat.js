#!/usr/bin/env node
/* ==========================================================================
   Sudut Pandaan — render_stat.js
   Merender potongan HTML statis (untuk SEO & pengguna tanpa JavaScript) dengan
   MEMAKAI ULANG fungsi komponen yang sama dipakai peramban
   (assets/js/config.js + assets/js/components.js), dijalankan lewat Node.

   Tujuannya: HTML di berkas .html identik dengan hasil render JS, sehingga
   tidak ada "lompatan" saat halaman dibuka dan mesin pencari tetap membaca
   konten tanpa menjalankan JavaScript.

   Dipanggil oleh tools/build.py (bukan bagian dari situs):
     node tools/render_stat.js <root-situs> <berkas-data> <fungsi> <opsi-json>

   opsi: { "base": "../", "urutKunci": "mulai", "arah": "naik", "batas": 4 }
   ========================================================================== */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const [rootArg, dataRel, fnNama, opsiArg] = process.argv.slice(2);
if (!rootArg || !dataRel || !fnNama) {
  process.stderr.write('pakai: node tools/render_stat.js <root> <berkas-data> <fungsi> [opsi-json]\n');
  process.exit(2);
}
const root = path.resolve(rootArg);
const opsi = opsiArg ? JSON.parse(opsiArg) : {};
const base = opsi.base || '';

/* --- tiru lingkungan peramban seperlunya (config.js mencari <script> dirinya) - */
global.window = global;
global.document = {
  querySelector: function (sel) {
    if (String(sel).indexOf('config.js') >= 0) {
      return { getAttribute: function () { return base + 'assets/js/config.js'; } };
    }
    return null;
  },
  querySelectorAll: function () { return []; },
  addEventListener: function () {},
  createElement: function () { return { style: {}, setAttribute: function () {}, appendChild: function () {} }; },
  documentElement: { classList: { add: function () {}, remove: function () {}, contains: function () { return false; } } }
};

['assets/js/config.js', 'assets/js/components.js'].forEach(function (f) {
  vm.runInThisContext(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f });
});

const UI = global.SP_UI;
if (!UI || typeof UI[fnNama] !== 'function') {
  process.stderr.write('fungsi komponen tidak ditemukan: ' + fnNama + '\n');
  process.exit(3);
}

const mentah = JSON.parse(fs.readFileSync(path.join(root, dataRel), 'utf8'));
let item = Array.isArray(mentah) ? mentah : (mentah.items || []);

if (opsi.urutKunci) {
  const arah = opsi.arah === 'turun' ? -1 : 1;
  item = item.slice().sort(function (a, b) {
    return (new Date(a[opsi.urutKunci]) - new Date(b[opsi.urutKunci])) * arah;
  });
}
if (opsi.batas) item = item.slice(0, opsi.batas);

process.stdout.write(item.map(function (it) { return UI[fnNama](it); }).join(''));
