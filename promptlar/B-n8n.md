# Bölüm B — n8n akışı için yapay zekâ aracına yazdığım promptlar

**Araç:** Claude Code masaüstü uygulaması, model Claude Opus 5.5. İlk sürümü Bölüm A ile **aynı oturumda** yaptım (Oturum 1). İlk prompt iki bölümü birlikte kapsıyordu. Teslimden önce ikinci bir oturumda iki bölümü birlikte inceledim ([Oturum 2](#oturum-2--bağımsız-inceleme-iki-bölüm-için-ortak)). Promptlar silinmeden, düzeltilmeden ve sırasıyla aşağıda (bkz. [A-claude-code.md](A-claude-code.md)).

---

## Prompt 1 · ≈11:06 (iki bölüm için ortak)

```
ise girmek icin bir case geldi cok onemli mail adresimde var case icerigi beraber tum ayrintilariyla eksiksiz yapalim
```

## Prompt 2 · ≈11:10 · Claude Code'un sorusuna verdiğim cevap (seçenekli soru)

> **Soru:** Bölüm B (n8n fiyat takibi) için hangi tablo ve bildirim kanalı kullanılsın? Brief ikisini de bize bırakıyor.
> Seçenekler: *Google Sheets + E-posta (Önerilen)* · *n8n Data Table + Telegram* · *CSV dosyası + E-posta*
> **Cevabım:** `Google Sheets + E-posta (Önerilen)`

---

## Claude Code'un Bölüm B'de yaptıkları (özet süreç günlüğü)

1. **Kaynağı tanıma:** Test sitesinin HTML'i incelendi.
   - 117 ürün var, sayfa başına 6 ürün.
   - Sayfalama çubuğu `1 … 10 … 19 20` şeklinde, yani son sayfa linki görünüyor.
   - `?page=99` HTTP 200 dönüyor ama ürün yok. Bu yüzden "sayfa boşsa dur" mantığı tek başına hata tespiti için yeterli değil.
   - Fiyatlar `<span itemprop="price">$416.99</span>` içinde.
2. **Şablon seçimi:** n8n şablon API'sinde `price monitoring`, `price tracker`, `competitor price`, `price change alert` aramaları yapıldı.
   - **#4640** seçildi: ücretli scraper kullanmıyor (HTTP + HTML + Code + Sheets) ve en çok görüntülenen sonuç.
   - Şablonun JSON'u indirildi ve düğüm düğüm incelendi.
   - **Eksikleri listelendi:** sayfa gezme yok (hazır URL listesi kullanıyor), yeni ürün tespiti yok, hata dalı yok. Fiyat okunamazsa `NaN !== eski_fiyat` true döndüğü için **yanlış alarm** üretiyor. Ürün başına 20 sn + 1 dk bekleme var. Saat dilimi IST'ye sabit. Sheet'te `timestamp\t` gibi sekmeli sütun adları var.
3. **Düğüm şemalarını kaynaktan doğrulama:** `npm install n8n` ilk denemede bash ortamında başarısız oldu (`spawn cmd.exe ENOENT`). Bunun üzerine **n8n-nodes-base 2.15.1** paketi (tarball) indirildi. Kullanılacak düğümlerin sürümleri ve parametre adları buradan kontrol edildi (HTTP Request `response.responseFormat`, `batching.batch`, Send Email v2 alanları, Schedule `triggerAtHour`, Stop and Error `errorMessage`).
4. **Code düğümlerini test edilebilir yazma:** Code düğümlerinin JS'i `kod/*.js` dosyalarına ayrıldı. `test/kod-testi.mjs`, n8n'in `$input` / `$('Düğüm')` ortamını taklit ederek aynı kodu Node.js'te çalıştırıyor.
   - **Canlı test:** 20 sayfa, 117 ürün, tüm fiyatlar sayı. 9 testin hepsi geçti.
   - **Önemli bulgu:** 29 ürünün adı başka bir ürünle aynı. Bu yüzden karşılaştırma anahtarı ürün adı değil, **ürün linki** oldu.
5. **`workflow.json` üretimi:** `araclar/workflow_olustur.py` JS dosyalarını akışa gömüyor ve yapıyı doğruluyor (benzersiz ad/id, var olmayan düğüme bağlantı ya da `$('…')` referansı yok, kopuk düğüm yok).
6. **Gerçek n8n'de test:** n8n PowerShell ile kurulunca (2.40.7) akış CLI ile içe aktarılıp çalıştırıldı. Bu test iki hata ortaya çıkardı:
   - **Hata:** `import:workflow` → `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id`. **Çözüm:** Workflow `id` eklendi. Hata akışının id'si bilindiği için `errorWorkflow` ayarı da doğrudan bağlandı.
   - **Hata:** `execute` → `Missing node to start execution` (CLI, Schedule Trigger ile başlatamıyor). **Çözüm:** "Elle Çalıştır (test)" Manual Trigger'ı eklendi.
   - **Sonuç:** 20 sayfa, 117 ürün, `saglikli: true`. Akış credential bağlanmamış Google Sheets adımına kadar hatasız geldi (beklenen durum).
   - İki hata senaryosu (site kapalı / hiç ürün yok) da gerçek n8n'de çalıştırıldı. Hata dalı çalıştı ve yürütme `error` durumunda bitti. Ayrıntılar: [../B-n8n/n8n-calistirma-kaydi.md](../B-n8n/n8n-calistirma-kaydi.md)
7. **Akış şeması:** `araclar/sema_olustur.py` ile `workflow.json`'dan SVG üretildi ve tarayıcıda kontrol edildi. IF'in normal "false" çıkışı da hata dalı gibi kırmızı çizilmişti, bu düzeltildi.

---

## Oturum 2 — bağımsız inceleme (iki bölüm için ortak)

## Prompt 3 · ≈11:54 (Oturum 2'nin ilk promptu; [A-claude-code.md](A-claude-code.md)'de Prompt 5)

```
erdinc beyden case geldi ben de baska bir sohbette sana yaptirdim suan ama emin degilim nasil olcak diye suan case repomda githubda https://github.com/erdogandogukan/Nurederm_Case_Dogukan_Erdogan  . Mangolabdaki gibi case imin cok iyi olmasini istiyorum ilk 5 te olmam lazim anlayacagin.
Eger eksik veya fazlalik bir sey goruyorsan duzeltelim cok profosyonel olmasi lazim. Buyuk ihtimal caseleri elleriyle kontrol etmeyebilirler yapay zekaya case i mi atip puanlatirlar gibi. Cok profosyonel olmasi istiyorum anlayacagin. Bir de mesela neyi bitiremedin diye bolum acmis onlari yapabiliyorsak yapalim readme yi de duzenleyelim eger turkce olmasini uygun goruyorsan turkce kalsin ama dedigim gibi en iyi olsun
```

## Claude Code'un Oturum 2'de Bölüm B için yaptıkları (özet süreç günlüğü)

1. **Şablon linki doğrulandı:** Link HTTP 200 döndürüyor. n8n şablon API'sindeki ad da README'dekiyle aynı ("Competitor price monitoring with web scraping, Google Sheets & Telegram", #4640).
2. **İki küçük sorun bulundu:**
   - Google Sheets okuması her satıra `row_number` ekliyor. "Kaldırıldı" diye işaretlenen satırlar bu alanla birlikte `son_durum`'a geri yazılıyordu, bu da tabloda fazladan bir sütun açabilirdi. Alan çıkarıldı ve Node testine bununla ilgili bir kontrol eklendi.
   - Arayüzden (*Import from File*) içe aktarımda n8n akışa yeni bir id veriyor. Bu durumda `errorWorkflow: hataBildirimAkis` bağlantısı kopuyor. `akis-aciklama.md`'ye tek adımlık bir düzeltme notu eklendi. CLI ile içe aktarımda bu sorun yok.
3. **Gerçek n8n'de yeniden çalıştırma:** Güncel `workflow.json` yerel n8n 2.40.7'ye yeniden içe aktarılıp CLI ile çalıştırıldı. Sonuç öncekiyle aynı: 20 sayfa, 117 ürün, `saglikli: true`. Akış, credential'ı bağlanmamış Google Sheets adımında beklendiği gibi durdu.
4. **Ekran görüntüsü (bonus):** Yerel n8n arayüzü sahip hesabı istiyor. Bu yüzden n8n ayrı bir veri klasörüyle **önizleme modunda** (`N8N_PREVIEW_MODE=true`) başlatıldı. `workflow.json`, editörün `/workflows/demo` görünümüne n8n'in kendi gömme bileşeninin kullandığı `openWorkflow` mesajıyla yüklendi.
   - **Hata:** Headless Edge'in `--screenshot --virtual-time-budget` seçeneği boş bir sayfa kaydetti; n8n kanvası sonradan çiziyor. **Çözüm:** Küçük bir Node betiğiyle DevTools protokolü üzerinden sayfa açıldı, 15 saniye beklendi ve `Page.captureScreenshot` alındı.
   - Görüntü tasarım görünümü; README'de böyle etiketlendi.
5. `araclar/workflow_olustur.py` Windows konsolunda Türkçe karakterleri bozuk basıyordu. stdout UTF-8'e alındı.
