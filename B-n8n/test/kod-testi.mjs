// workflow.json içindeki Code düğümlerinin JS'ini n8n'e ihtiyaç duymadan test eder.
// Çalıştırma (B-n8n klasöründe):  node test/kod-testi.mjs
// Not: İlk test canlı siteye (webscraper.io) 21 istek atar; internet gerekir.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const KOK = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const kod = (dosya) => readFileSync(path.join(KOK, 'kod', dosya), 'utf8');

// n8n Code düğümü ortamının küçük bir taklidi: $input ve $('Düğüm Adı')
function calistir(dosya, girdi, dugumler = {}) {
  const ogeler = (liste) => ({ all: () => liste, first: () => liste[0] });
  const fn = new Function('$input', '$', kod(dosya));
  return fn(ogeler(girdi), (ad) => {
    if (!(ad in dugumler)) throw new Error(`Bilinmeyen düğüm referansı: ${ad}`);
    return ogeler(dugumler[ad]);
  });
}

const AYAR = [{ json: {
  taban_url: 'https://webscraper.io/test-sites/e-commerce/static/computers/laptops',
  site_kok: 'https://webscraper.io',
  max_sayfa: 50,
} }];

async function getir(url) {
  const yanit = await fetch(url, { headers: { 'User-Agent': 'n8n-akis-testi/1.0' } });
  if (!yanit.ok) throw new Error(`${url} → HTTP ${yanit.status}`);
  return yanit.text();
}

let gecen = 0;
let kalan = 0;
async function test(ad, fn) {
  try {
    await fn();
    gecen++;
    console.log(`✓ ${ad}`);
  } catch (e) {
    kalan++;
    console.log(`✗ ${ad}\n    ${e.message}`);
  }
}

const kartHtml = (id, ad, fiyat, yorum) => `<div class="card thumbnail"><h4 class="price"><span itemprop="price">${fiyat}</span></h4>
  <a href="/test-sites/e-commerce/static/product/${id}" class="title" title="${ad}" itemprop="name">${ad}</a>
  <p class="review-count"><span itemprop="reviewCount">${yorum}</span> reviews</p></div>`;

// --- 1) Canlı site: tüm sayfalar ---------------------------------------------
let tarama;
await test('canlı site: sayfa sayısı bulunur, tüm sayfalar gezilir, fiyatlar sayıya çevrilir', async () => {
  const sayfa1 = await getir(AYAR[0].json.taban_url);
  const sayfalar = calistir('1-sayfa-listesi.js', [{ json: { html: sayfa1 } }], { Ayarlar: AYAR });
  assert.equal(sayfalar.length, 20, 'sayfa sayısı');
  const ciktilar = [];
  for (const s of sayfalar) {
    ciktilar.push({ json: { html: await getir(s.json.url) } });
    await new Promise((r) => setTimeout(r, 150)); // siteye nazik ol
  }
  const [ozet] = calistir('2-urunleri-ayristir.js', ciktilar, {
    Ayarlar: AYAR, 'Sayfa Listesini Oluştur': sayfalar,
  });
  tarama = ozet.json;
  assert.equal(tarama.saglikli, true, tarama.sorunlar.join('; '));
  assert.equal(tarama.urun_sayisi, 117, 'sitede "117 items" yazıyor');
  for (const u of tarama.urunler) {
    assert.equal(typeof u.fiyat, 'number');
    assert.ok(Number.isFinite(u.fiyat) && u.fiyat > 0, `${u.ad}: ${u.fiyat}`);
    assert.ok(u.link.startsWith('https://webscraper.io/test-sites/e-commerce/static/product/'));
    assert.ok(Number.isInteger(u.yorum_sayisi));
  }
  const fiyatlar = tarama.urunler.map((u) => u.fiyat);
  const adlar = tarama.urunler.map((u) => u.ad);
  console.log(`    ${tarama.taranan_sayfa} sayfa · ${tarama.urun_sayisi} ürün · fiyat aralığı `
    + `$${Math.min(...fiyatlar)}–$${Math.max(...fiyatlar)} · tekrar eden ad: ${adlar.length - new Set(adlar).size}`);
});

// Canlı test çalışmadıysa (ağ yok) sonraki testler için sentetik veri
if (!tarama) {
  const sayfalar = [{ json: { sayfa: 1 } }];
  tarama = calistir('2-urunleri-ayristir.js', [{ json: { html: kartHtml(1, 'A', '$10.00', 1)
    + kartHtml(2, 'B', '$20.00', 2) + kartHtml(3, 'C', '$30.00', 3) } }],
  { Ayarlar: AYAR, 'Sayfa Listesini Oluştur': sayfalar })[0].json;
}

// --- 2) Ayrıştırma kenar durumları ---------------------------------------------
await test('fiyat: "$1,139.54" → 1139.54 (binlik virgül), HTML varlıkları çözülür', () => {
  const html = kartHtml(7, 'Asus &quot;Pro&quot; 15.6&quot;', '$1,139.54', 12);
  const [o] = calistir('2-urunleri-ayristir.js', [{ json: { html } }], {
    Ayarlar: AYAR, 'Sayfa Listesini Oluştur': [{ json: { sayfa: 1 } }],
  });
  assert.equal(o.json.urunler[0].fiyat, 1139.54);
  assert.equal(o.json.urunler[0].ad, 'Asus "Pro" 15.6"');
  assert.equal(o.json.urunler[0].link, 'https://webscraper.io/test-sites/e-commerce/static/product/7');
});

await test('hata: hiç ürün gelmezse tarama "sağlıksız" olur (sessiz başarı yok)', () => {
  const [o] = calistir('2-urunleri-ayristir.js', [{ json: { html: '<html>bakımdayız</html>' } }], {
    Ayarlar: AYAR, 'Sayfa Listesini Oluştur': [{ json: { sayfa: 1 } }],
  });
  assert.equal(o.json.saglikli, false);
  assert.equal(o.json.urun_sayisi, 0);
  assert.match(o.json.sorunlar.join(), /hiç ürün bulunamadı/);
});

await test('hata: bir sayfa açılamazsa (HTTP hata öğesi) tarama sağlıksız sayılır', () => {
  const [o] = calistir('2-urunleri-ayristir.js', [
    { json: { html: kartHtml(1, 'A', '$10.00', 1) } },
    { json: { error: { message: '503 Service Unavailable' } } },
  ], { Ayarlar: AYAR, 'Sayfa Listesini Oluştur': [{ json: { sayfa: 1 } }, { json: { sayfa: 2 } }] });
  assert.equal(o.json.saglikli, false);
  assert.match(o.json.sorunlar.join(), /açılamayan sayfa\(lar\): 2/);
});

await test('hata mesajı: site hiç açılmazsa ve tarama sağlıksızsa anlaşılır neden üretilir', () => {
  const [a] = calistir('5-hata-mesaji.js', [{ json: { error: { message: 'getaddrinfo ENOTFOUND webscraper.io' } } }]);
  assert.match(a.json.hata_mesaji, /^Site açılamadı: getaddrinfo ENOTFOUND/);
  const [b] = calistir('5-hata-mesaji.js', [{ json: { urun_sayisi: 0, taranan_sayfa: 1, beklenen_sayfa: 1,
    sorunlar: ['hiç ürün bulunamadı'] } }]);
  assert.match(b.json.hata_mesaji, /hiç ürün bulunamadı/);
  assert.match(b.json.konu, /^\[HATA\]/);
});

// --- 3) Değişiklik tespiti ------------------------------------------------------
const oncekiSatir = (u, ek = {}) => ({ json: { link: u.link, urun_id: u.urun_id, ad: u.ad, fiyat: u.fiyat,
  yorum_sayisi: u.yorum_sayisi, ilk_gorulme: '2026-09-24', son_gorulme: '2026-09-24', durum: 'aktif', ...ek } });

await test('değişiklik: fiyatı değişen, yeni çıkan ve kaldırılan ürünler ayrılır', () => {
  const [u0, u1] = tarama.urunler;
  const onceki = tarama.urunler.slice(1).map((u) => oncekiSatir(u,
    // u1'in önceki fiyatı 10$ fazla ve Türkçe yerel ayarlı Sheets'ten gelmiş gibi string
    u === u1 ? { fiyat: (u.fiyat + 10).toFixed(2).replace('.', ',') } : {}));
  onceki.push({ json: { link: 'https://webscraper.io/test-sites/e-commerce/static/product/99999',
    ad: 'Eski Laptop', fiyat: 999, durum: 'aktif', row_number: 118 } }); // Sheets okuması row_number ekler

  const [s] = calistir('3-degisiklikleri-bul.js', onceki, { 'Ürünleri Ayrıştır': [{ json: tarama }] });
  const d = s.json;
  assert.deepEqual(d.yeni.map((u) => u.link), [u0.link]);
  assert.equal(d.degisen.length, 1);
  assert.equal(d.degisen[0].link, u1.link);
  assert.equal(d.degisen[0].fark, -10);
  assert.deepEqual(d.kaldirilan.map((u) => u.ad), ['Eski Laptop']);
  assert.equal(d.degisiklik_var, true);
  assert.equal(d.gecmis_satirlari.length, tarama.urun_sayisi);
  assert.ok(d.gecmis_satirlari.every((r) => r.tarih === tarama.tarih && typeof r.fiyat === 'number'));
  assert.equal(d.son_durum_satirlari.length, tarama.urun_sayisi + 1);
  assert.equal(d.son_durum_satirlari.at(-1).durum, 'kaldirildi');
  assert.ok(!('row_number' in d.son_durum_satirlari.at(-1)), 'row_number tabloya geri yazılmamalı');
  assert.equal(d.son_durum_satirlari.find((r) => r.link === u1.link).ilk_gorulme, '2026-09-24');

  const [e] = calistir('4-bildirim-epostasi.js', [s]);
  assert.match(e.json.konu, /1 fiyat değişikliği, 1 yeni, 1 kaldırılan/);
  assert.ok(e.json.html.includes('Eski Laptop'));
});

await test('değişiklik yoksa bildirim gönderilmez', () => {
  const onceki = tarama.urunler.map((u) => oncekiSatir(u));
  const [s] = calistir('3-degisiklikleri-bul.js', onceki, { 'Ürünleri Ayrıştır': [{ json: tarama }] });
  assert.equal(s.json.degisiklik_var, false);
  assert.equal(s.json.bildirim_gerekli, false);
});

await test('ilk çalışma (boş tablo): her ürün "yeni" sayılmaz, referans bildirimi gider', () => {
  const [s] = calistir('3-degisiklikleri-bul.js', [{ json: {} }], { 'Ürünleri Ayrıştır': [{ json: tarama }] });
  assert.equal(s.json.ilk_calisma, true);
  assert.equal(s.json.yeni.length, 0);
  assert.equal(s.json.bildirim_gerekli, true);
  const [e] = calistir('4-bildirim-epostasi.js', [s]);
  assert.match(e.json.konu, /ilk çalışma/);
});

await test('kaldırılmış ürün tekrar raporlanmaz; geri gelirse "yeni" sayılır', () => {
  const [u0] = tarama.urunler;
  const onceki = tarama.urunler.map((u) => oncekiSatir(u, u === u0 ? { durum: 'kaldirildi' } : {}));
  onceki.push({ json: { link: 'x/product/5', ad: 'Zaten kaldırıldı', fiyat: 5, durum: 'kaldirildi' } });
  const [s] = calistir('3-degisiklikleri-bul.js', onceki, { 'Ürünleri Ayrıştır': [{ json: tarama }] });
  assert.deepEqual(s.json.yeni.map((u) => u.link), [u0.link]);
  assert.equal(s.json.kaldirilan.length, 0);
});

console.log(`\n${gecen} test geçti, ${kalan} test başarısız.`);
process.exitCode = kalan ? 1 : 0;
