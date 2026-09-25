// n8n Code düğümü: "Değişiklikleri Bul" (Run Once for All Items)
// Girdi : "Son Durumu Oku" (Google Sheets → son_durum sekmesi; ürün başına bir satır).
//         Sekme boşsa (ilk çalışma) düğümün "Always Output Data" ayarı tek boş öğe verir.
// Çıktı : TEK öğe → yeni / fiyatı değişen / kaldırılan ürünler + tablolara yazılacak satırlar.
//
// Anahtar = ürün linki (/product/{id}). Ürün adı anahtar olamaz: sitede aynı
// ada sahip farklı konfigürasyonlu laptoplar var.
const tarama = $('Ürünleri Ayrıştır').first().json;
const onceki = $input.all().map((o) => o.json).filter((r) => r && r.link);
const ilkCalisma = onceki.length === 0;

// Sheets yerel ayarı Türkçe ise fiyat "1.139,54" gelebilir; iki biçim de sayıya çevrilir.
const sayiyaCevir = (v) => {
  if (typeof v === 'number') return v;
  const s = String(v ?? '').trim().replace(/[^0-9.,-]/g, '');
  if (/^-?\d{1,3}(\.\d{3})*,\d+$/.test(s) || /^-?\d+,\d+$/.test(s)) {
    return Number(s.replace(/\./g, '').replace(',', '.'));
  }
  return Number(s.replace(/,/g, ''));
};

const oncekiHarita = new Map(onceki.map((r) => [String(r.link), r]));
const simdikiHarita = new Map(tarama.urunler.map((u) => [u.link, u]));

const yeni = [];
const degisen = [];
for (const u of tarama.urunler) {
  const o = oncekiHarita.get(u.link);
  if (!o || o.durum === 'kaldirildi') {
    if (!ilkCalisma) yeni.push(u); // ilk çalışmada her şey "yeni" sayılıp alarm yağdırılmaz
    continue;
  }
  const eski = sayiyaCevir(o.fiyat);
  if (Number.isFinite(eski) && Math.abs(eski - u.fiyat) >= 0.005) {
    degisen.push({
      ...u,
      eski_fiyat: eski,
      fark: Number((u.fiyat - eski).toFixed(2)),
      yuzde: eski ? Number((((u.fiyat - eski) / eski) * 100).toFixed(2)) : null,
    });
  }
}
const kaldirilan = onceki.filter((o) => o.durum !== 'kaldirildi' && !simdikiHarita.has(String(o.link)));

const gecmisSatirlari = tarama.urunler.map((u) => ({
  tarih: tarama.tarih,
  calisma_zamani: tarama.calisma_zamani,
  urun_id: u.urun_id,
  ad: u.ad,
  fiyat: u.fiyat,
  yorum_sayisi: u.yorum_sayisi,
  link: u.link,
}));

const sonDurumSatirlari = [
  ...tarama.urunler.map((u) => ({
    link: u.link,
    urun_id: u.urun_id,
    ad: u.ad,
    fiyat: u.fiyat,
    yorum_sayisi: u.yorum_sayisi,
    ilk_gorulme: oncekiHarita.get(u.link)?.ilk_gorulme || tarama.tarih,
    son_gorulme: tarama.tarih,
    durum: 'aktif',
  })),
  // Kaldırılan ürün bir kez raporlanır, sonra "kaldirildi" olarak işaretlenir.
  // Sheets okuması her satıra `row_number` ekliyor; o alan tabloya sütun olarak geri yazılmasın.
  ...kaldirilan.map(({ row_number, ...o }) => ({ ...o, durum: 'kaldirildi' })),
];

return [{
  json: {
    tarih: tarama.tarih,
    urun_sayisi: tarama.urun_sayisi,
    ilk_calisma: ilkCalisma,
    yeni,
    degisen,
    kaldirilan,
    degisiklik_var: yeni.length + degisen.length + kaldirilan.length > 0,
    bildirim_gerekli: ilkCalisma || yeni.length + degisen.length + kaldirilan.length > 0,
    gecmis_satirlari: gecmisSatirlari,
    son_durum_satirlari: sonDurumSatirlari,
  },
}];
