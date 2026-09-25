// n8n Code düğümü: "Ürünleri Ayrıştır" (Run Once for All Items)
// Girdi : "Tüm Sayfaları Çek" çıktısı → sayfa başına bir öğe (json.html ya da json.error)
// Çıktı : TEK özet öğe → { tarih, urun_sayisi, saglikli, urunler: [...], ... }
//
// Neden tek özet öğe? Hiç ürün çıkmazsa n8n 0 öğeyle dalı sessizce bitirir ve
// yürütme "başarılı" görünür. Özet öğe her zaman üretilir; ardından gelen IF
// düğümü `saglikli` alanına bakıp hata dalına yönlendirir.
const ayar = $('Ayarlar').first().json;
const sayfaListesi = $('Sayfa Listesini Oluştur').all();
const sayfaCiktilari = $input.all();

const simdi = new Date();
// İstanbul saatine göre YYYY-MM-DD ("sv-SE" biçimi ISO tarih verir)
const tarih = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Istanbul' }).format(simdi);

const htmlCoz = (s) => String(s)
  .replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&lt;/g, '<')
  .replace(/&gt;/g, '>').replace(/&amp;/g, '&').trim();

// "$1,139.54" → 1139.54 : para simgesi ve binlik ayırıcı virgül temizlenir.
// (Şablondaki parseFloat("$1,139.54".replace("$","")) gibi bir yaklaşım 1 döndürürdü.)
const fiyataCevir = (metin) => Number(String(metin || '').replace(/[^0-9.]/g, '')) || NaN;

const urunler = new Map(); // link → ürün; aynı ürün iki sayfada görünürse tekrar sayılmaz
const hataliSayfalar = [];
const bosSayfalar = [];
let hataliKart = 0;

sayfaCiktilari.forEach((oge, i) => {
  const sayfa = sayfaListesi[i]?.json.sayfa ?? i + 1;
  if (oge.json.error) {
    hataliSayfalar.push(sayfa);
    return;
  }
  const kartlar = String(oge.json.html || '').split('class="card thumbnail"').slice(1);
  if (kartlar.length === 0) {
    bosSayfalar.push(sayfa);
    return;
  }
  for (const kart of kartlar) {
    const link = (kart.match(/href="([^"]*\/product\/(\d+))"/) || [])[1];
    const ad = (kart.match(/class="title"[^>]*title="([^"]*)"/) || [])[1];
    const fiyat = fiyataCevir((kart.match(/itemprop="price"[^>]*>([^<]*)</) || [])[1]);
    const yorum = parseInt((kart.match(/itemprop="reviewCount"[^>]*>([^<]*)</) || [])[1], 10);
    if (!link || !ad || !Number.isFinite(fiyat)) {
      hataliKart++;
      continue;
    }
    const tamLink = link.startsWith('http') ? link : ayar.site_kok.replace(/\/$/, '') + link;
    urunler.set(tamLink, {
      urun_id: Number(link.match(/(\d+)$/)[1]),
      ad: htmlCoz(ad),
      fiyat,
      yorum_sayisi: Number.isFinite(yorum) ? yorum : 0,
      link: tamLink,
      sayfa,
    });
  }
});

const beklenenSayfa = sayfaListesi.length;
const eksikSayfa = beklenenSayfa - sayfaCiktilari.length;
const sorunlar = [];
if (urunler.size === 0) sorunlar.push('hiç ürün bulunamadı');
if (hataliSayfalar.length) sorunlar.push(`açılamayan sayfa(lar): ${hataliSayfalar.join(', ')}`);
if (bosSayfalar.length) sorunlar.push(`ürünsüz sayfa(lar): ${bosSayfalar.join(', ')}`);
if (eksikSayfa > 0) sorunlar.push(`${eksikSayfa} sayfanın yanıtı eksik`);
if (hataliKart > 0) sorunlar.push(`${hataliKart} ürün kartı ayrıştırılamadı`);

// Eksiksizlik kontrolü: site 1. sayfada toplam ürün sayısını yazıyor ("117 items"). Sayfalama
// bağlantıları bir gün bulunamazsa akış yalnızca 1. sayfayı tarar; bu kontrol olmasaydı 6 ürünlük
// tarama "sağlıklı" sayılır ve kalan 111 ürün yanlışlıkla "kaldırıldı" diye bildirilirdi.
const sayfa1Html = String($("Sayfa 1'i Çek").first().json.html || '');
const sitedekiSayi = Number((sayfa1Html.match(/class="item-count"[^>]*>\s*(\d+)\s*items?/) || [])[1]);
if (!Number.isFinite(sitedekiSayi) || sitedekiSayi <= 0) {
  sorunlar.push('sitedeki toplam ürün sayısı okunamadı; taramanın eksiksiz olduğu doğrulanamadı');
} else if (urunler.size !== sitedekiSayi) {
  sorunlar.push(`sitede ${sitedekiSayi} ürün yazıyor, ${urunler.size} ürün ayrıştırıldı`);
}

return [{
  json: {
    tarih,
    calisma_zamani: simdi.toISOString(),
    beklenen_sayfa: beklenenSayfa,
    sitedeki_urun_sayisi: Number.isFinite(sitedekiSayi) ? sitedekiSayi : null,
    taranan_sayfa: sayfaCiktilari.length - hataliSayfalar.length,
    urun_sayisi: urunler.size,
    // Eksik tarama "sağlıklı" sayılmaz: yarım veriyle karşılaştırma yapılırsa
    // taranamayan ürünler yanlışlıkla "kaldırıldı" diye raporlanırdı.
    saglikli: sorunlar.length === 0,
    sorunlar,
    urunler: [...urunler.values()],
  },
}];
