// n8n Code düğümü: "Bildirim E-postasını Hazırla" (Run Once for All Items)
// Girdi : "Değişiklikleri Bul" özeti. Çıktı: { konu, html } → "Send Email" düğümü.
const d = $input.first().json;
const para = (n) => `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const kacis = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const link = (u) => `<a href="${kacis(u.link)}">${kacis(u.ad)}</a>`;

const tablo = (baslik, satirlar, basliklar) => (satirlar.length === 0 ? '' : `
  <h3>${baslik} (${satirlar.length})</h3>
  <table cellpadding="6" style="border-collapse:collapse;font-size:14px">
    <tr style="background:#f1f3f5">${basliklar.map((b) => `<th align="left">${b}</th>`).join('')}</tr>
    ${satirlar.join('\n')}
  </table>`);

// Önce en büyük değişimler
const degisen = [...d.degisen].sort((a, b) => Math.abs(b.yuzde) - Math.abs(a.yuzde));

const govde = d.ilk_calisma
  ? `<p>İlk çalışma: <b>${d.urun_sayisi}</b> ürün referans olarak kaydedildi. Bundan sonraki
     çalışmalarda yalnızca fiyatı değişen, yeni çıkan ve kaldırılan ürünler bildirilecek.</p>`
  : [
    tablo('Fiyatı değişen ürünler', degisen.map((u) => `<tr><td>${link(u)}</td><td>${para(u.eski_fiyat)}</td>
      <td>${para(u.fiyat)}</td><td style="color:${u.fark < 0 ? '#2b8a3e' : '#c92a2a'}">${u.fark < 0 ? '▼' : '▲'}
      ${u.yuzde}%</td></tr>`), ['Ürün', 'Eski fiyat', 'Yeni fiyat', 'Değişim']),
    tablo('Yeni çıkan ürünler', d.yeni.map((u) => `<tr><td>${link(u)}</td><td>${para(u.fiyat)}</td>
      <td>${u.yorum_sayisi}</td></tr>`), ['Ürün', 'Fiyat', 'Yorum']),
    tablo('Listeden kalkan ürünler', d.kaldirilan.map((u) => `<tr><td>${link(u)}</td>
      <td>${para(u.fiyat)}</td></tr>`), ['Ürün', 'Son bilinen fiyat']),
  ].join('');

const ozet = d.ilk_calisma
  ? 'ilk çalışma, referans kaydedildi'
  : `${d.degisen.length} fiyat değişikliği, ${d.yeni.length} yeni, ${d.kaldirilan.length} kaldırılan`;

return [{
  json: {
    konu: `Laptop fiyat takibi ${d.tarih}: ${ozet}`,
    html: `<div style="font-family:Segoe UI,Arial,sans-serif">
      <h2 style="margin:0 0 8px">Laptop fiyat takibi — ${d.tarih}</h2>
      <p style="color:#555">Taranan ürün: ${d.urun_sayisi} · Kaynak: webscraper.io test sitesi (tüm sayfalar)</p>
      ${govde}
    </div>`,
  },
}];
