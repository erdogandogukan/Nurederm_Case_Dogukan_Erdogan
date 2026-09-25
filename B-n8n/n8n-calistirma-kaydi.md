# n8n'de gerçek çalıştırma kaydı

`workflow.json` yerel bir **n8n 2.40.7** kurulumuna içe aktarılıp **n8n CLI** ile çalıştırıldı (25.09.2026).
Google Sheets ve SMTP credential'ı bağlanmadı; amaç, akış mantığının gerçek n8n motorunda çalıştığını görmekti.
Arayüz ekran görüntüsü yok: yerel n8n arayüzü sahip hesabı kurulumu istiyor.

```powershell
$env:N8N_USER_FOLDER = "C:\...\n8n-yerel\veri"            # mevcut bir n8n kurulumuna dokunmamak için
n8n import:workflow --input=hata-workflow.json
n8n import:workflow --input=workflow.json
n8n execute --id LaptopFiyatTakip --rawOutput
```

## 1) Normal çalışma: canlı site

| Düğüm | Çıkış öğe sayısı | Not |
|---|---|---|
| Günlük Tetikleyici (09:00) | 1 | |
| Ayarlar | 1 | |
| Sayfa 1'i Çek | 1 (başarı) · 0 (hata çıkışı) | |
| Sayfa Listesini Oluştur | **20** | son sayfa sayfalama çubuğundan okundu |
| Tüm Sayfaları Çek | **20** | |
| Ürünleri Ayrıştır | 1 (özet) | `urun_sayisi: 117`, `saglikli: true`, `taranan_sayfa: 20/20` |
| Tarama sağlıklı mı? | 1 (true) · 0 (false) | |
| Son Durumu Oku | – | `Node does not have any credentials set` (**beklenen**: Sheets credential'ı bağlanmadı) |

Örnek ürün (n8n çıktısından): `{"urun_id": 31, "ad": "Packard 255 G2", "fiyat": 416.99, "yorum_sayisi": 2, "link": "https://webscraper.io/test-sites/e-commerce/static/product/31", "sayfa": 1}`. `fiyat` bir sayı (float). En pahalı ürün: Asus ROG Strix SCAR Edition GL503VM-ED115T, 1799.

Sheets adımı hata verince n8n ayarlı Error Workflow'u da çağırdı: `Calling Error Workflow for "LaptopFiyatTakip". Workflow "hataBildirimAkis" is not active`. Yani `errorWorkflow` bağlantısı çalışıyor. **Bu n8n sürümünde hata akışının aktif edilmesi gerekiyor.**

## 2) Hata dalı: site açılmıyor

`taban_url` geçici olarak `https://site-yok.invalid/laptops` yapıldı.

| Düğüm | Sonuç |
|---|---|
| Sayfa 1'i Çek | 0 (başarı) · **1 (hata çıkışı)**: 3 deneme sonrası `getaddrinfo ENOTFOUND` |
| Hata Mesajını Hazırla | `hata_mesaji: "Site açılamadı: getaddrinfo ENOTFOUND site-yok.invalid"` |
| Hata Bildirimi Gönder | SMTP credential'ı yok, hata verdi ama `continueRegularOutput` sayesinde akış devam etti |
| Akışı Hatayla Bitir | **Stop and Error**, yürütme durumu: **`error`** |

(n8n, "ENOTFOUND" içeren hata metinlerini yürütme özetinde kendi açıklamasıyla gösteriyor: "The connection cannot be established…". E-posta gövdesine giden metin yukarıdaki `hata_mesaji`.)

## 3) Hata dalı: hiç ürün gelmiyor

`taban_url` geçici olarak ürün kartı olmayan `https://webscraper.io/test-sites` yapıldı.

| Düğüm | Sonuç |
|---|---|
| Sayfa 1'i Çek → Sayfa Listesini Oluştur → Tüm Sayfaları Çek | 1 → 1 → 1 (site açıldı) |
| Ürünleri Ayrıştır | `urun_sayisi: 0`, `saglikli: false` |
| Tarama sağlıklı mı? | 0 (true) · **1 (false)** |
| Hata Mesajını Hazırla → Hata Bildirimi Gönder → Akışı Hatayla Bitir | yürütme durumu: **`error`**, mesaj: `Tarama sağlıksız (0 ürün, 1/1 sayfa): hiç ürün bulunamadı; ürünsüz sayfa(lar): 1` |

Her iki hata senaryosunda da akış **sessizce "başarılı" bitmedi**.

## Gerçek n8n testinde bulunan ve düzeltilen iki şey

1. `n8n import:workflow` ilk denemede `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id` hatası verdi. CLI içe aktarımı JSON'da workflow `id` alanı istiyor (arayüzden içe aktarım istemiyor). Sabit id eklendi (`LaptopFiyatTakip`, `hataBildirimAkis`). Hata akışının id'si bilindiği için ana akışın `errorWorkflow` ayarı da doğrudan bağlandı.
2. `n8n execute` "Missing node to start execution" hatası verdi: CLI, Schedule Trigger'la başlatamıyor. Arayüzde ve CLI'da test için **"Elle Çalıştır (test)"** Manual Trigger'ı eklendi (zamanlanmış tetikleyici aynen duruyor).

## 4) Harici inceleme sonrası yeniden çalıştırma

Eksiksizlik kontrolü eklendikten sonra (`Ürünleri Ayrıştır`, sitedeki "117 items" ile karşılaştırma) güncel
`workflow.json` yeniden içe aktarılıp çalıştırıldı: `sitedeki_urun_sayisi: 117`, `urun_sayisi: 117`,
`taranan_sayfa: 20`, `saglikli: true`. Akış yine credential bağlanmamış `Son Durumu Oku` adımında durdu.
Sayfalama bağlantılarının bulunamadığı durum (6 ürün / 117) Node testinde `saglikli: false` veriyor.
