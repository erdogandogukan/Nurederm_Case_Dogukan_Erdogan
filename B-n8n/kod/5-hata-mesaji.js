// n8n Code düğümü: "Hata Mesajını Hazırla" (Run Once for All Items)
// İki kaynaktan beslenir:
//   1) "Sayfa 1'i Çek" hata çıkışı  → json.error (site açılmadı / zaman aşımı / 5xx)
//   2) "Tarama sağlıklı mı?" false  → "Ürünleri Ayrıştır" özeti (hiç ürün yok, eksik sayfa...)
const girdi = $input.first().json;
const tarih = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Istanbul' }).format(new Date());

let neden;
if (girdi.error) {
  const e = girdi.error;
  neden = `Site açılamadı: ${e.message || e.description || JSON.stringify(e).slice(0, 300)}`;
} else {
  neden = `Tarama sağlıksız (${girdi.urun_sayisi ?? 0} ürün, ${girdi.taranan_sayfa ?? 0}/${girdi.beklenen_sayfa ?? '?'} sayfa): `
    + ((girdi.sorunlar || []).join('; ') || 'bilinmeyen sorun');
}

return [{
  json: {
    hata_mesaji: neden,
    konu: `[HATA] Laptop fiyat takibi ${tarih}: çalışma başarısız`,
    html: `<div style="font-family:Segoe UI,Arial,sans-serif">
      <h2 style="color:#c92a2a;margin:0 0 8px">Laptop fiyat takibi başarısız oldu</h2>
      <p><b>Neden:</b> ${String(neden).replace(/</g, '&lt;')}</p>
      <p>Bu çalışmada tablolar güncellenmedi ve değişiklik karşılaştırması yapılmadı
      (yarım veriyle yanlış "kaldırıldı" alarmı üretmemek için).</p>
      <p>Kaynak: https://webscraper.io/test-sites/e-commerce/static/computers/laptops</p>
    </div>`,
  },
}];
