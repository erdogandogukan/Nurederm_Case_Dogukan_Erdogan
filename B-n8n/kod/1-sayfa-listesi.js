// n8n Code düğümü: "Sayfa Listesini Oluştur" (Run Once for All Items)
// Girdi : "Sayfa 1'i Çek" düğümünün çıktısı → json.html (1. sayfanın HTML'i)
// Çıktı : taranacak her sayfa için bir öğe → { sayfa, url }
//
// Site ?page=N ile sayfalanıyor ve sayfalama çubuğu son sayfayı da gösteriyor
// (1 … 10 … 19 20). Sayfa linklerindeki en büyük N = son sayfa. Sayfa sayısı
// değişirse akış kendiliğinden uyum sağlar; sabit "20" yazılmadı.
const ayar = $('Ayarlar').first().json;
const html = String($input.first().json.html || '');

const sayfaNolari = [...html.matchAll(/[?&]page=(\d+)/g)].map((m) => Number(m[1]));
const sonSayfa = Math.min(Math.max(1, ...sayfaNolari), Number(ayar.max_sayfa) || 50);

const sayfalar = [];
for (let sayfa = 1; sayfa <= sonSayfa; sayfa++) {
  sayfalar.push({ json: { sayfa, url: `${ayar.taban_url}?page=${sayfa}` } });
}
return sayfalar;
