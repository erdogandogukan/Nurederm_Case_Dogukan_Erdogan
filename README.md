# Uygulama Görevi — AI Otomasyon / Entegrasyon (Nurederm · LabelSkin)

**Doğukan Erdoğan** · 25.09.2026

> **Summary (English).** Take-home case for an AI Automation / Integration role. **Part A** (Python, standard library only) classifies 15 customer messages and hands sensitive ones (returns / complaints, adverse reactions) to a human. It looks up orders via the DummyJSON API and never reveals another customer's order (fail-closed ownership check, identical replies for "not found" and "not yours"). Outputs are `talepler.json` and a one-page summary; 44 unit tests; the classifier was also measured on 74 extra labelled messages. **Part B** is an n8n workflow adapted from template #4640. It crawls every page of the test shop daily and checks the result against the site's own item count. Numeric prices are stored with timestamps in Google Sheets and changes / new / removed products are emailed. On site errors or incomplete crawls it fails loudly (Stop and Error). The workflow was imported and executed on a real n8n 2.40.7 instance. The work was reviewed by a second Claude Code session and by ChatGPT; every finding was verified and fixed. The rest of the documentation is in Turkish.

| | |
|---|---|
| Case e-postası geldi | **11:00** |
| Çalışmaya başladım | **11:06** |
| İlk tam sürüm (iki bölüm, testler, README) | **11:50** |
| İkinci Claude Code oturumunda bağımsız inceleme | **11:54 – 12:13** |
| İlk oturumda ikinci oturumun değişikliklerinin kontrolü | **12:18 – 12:29** |
| Harici inceleme (ChatGPT) bulgularının doğrulanması ve düzeltilmesi | **12:31 – 12:52** |
| Son commit | **12:52** (teslim sınırı 14:00) |
| Kullandığım yapay zekâ aracı | **Claude Code** (Claude Opus 5.5, masaüstü uygulaması) |

Kodun, testlerin ve dokümantasyonun taslağını Claude Code yazdı. Yapay zekâya verdiğim promptlar sırasıyla [`promptlar/`](promptlar/) klasöründe; niyetleri korunarak yeniden ifade edildiler, orijinal metinler git geçmişinde duruyor. Aynı yerde, yapay zekânın yol boyunca karşılaştığı hatalar ve bunları nasıl çözdüğü de var.

**Kısaca:**
- **Bölüm A:** 15 mesaj konulara ayrıldı. 11'i insana devredildi: 2'si hassas konu, 2'si doğrulanamayan sipariş, 7'si sistemde olmayan bir bilgi gerektirdiği için. Kalan 3 mesajın taslağı doğrudan gönderilebilir, 1 mesaj spam. Başka müşteriye ait siparişin (#12) hiçbir bilgisi çıktıya sızmıyor; bunu 44 testten 6'sı koruyor. Sınıflandırıcıyı ayrıca **74 yeni etiketli mesajla ölçtüm**. Sonuçları, düzeltilen açıkları ve kalan sınırları aşağıda olduğu gibi yazdım.
- **Bölüm B:** n8n şablonu #4640'tan uyarlanan akış tüm sayfaları geziyor ve fiyatı sayı olarak alıyor. Sonucu Google Sheets'e tarih damgasıyla yazıyor, değişiklik olunca e-posta gönderiyor ve bir hata dalı var. Akış **gerçek bir n8n 2.40.7 kurulumunda** çalıştırıldı (20 sayfa, 117 ürün); iki hata senaryosu da denendi. Ayrıştırılan ürün sayısı sitedeki toplamla karşılaştırılıyor; eksik tarama hata dalına gidiyor.
- **Yöntem:** İlk sürüm bittikten sonra işi ayrı bir Claude Code oturumuna baştan incelettim. Bu inceleme README'deki bir iddianın yanlış olduğunu ortaya çıkardı: sınıflandırıcıyla ilgili "yeni ifadeler güvenli tarafa düşer" cümlesi. Bu açık ölçüldü, düzeltildi ve yeniden ölçüldü ([ayrıntı](#sınıflandırıcıyı-yeni-mesajlarla-ölçtüm)). Sonra bu düzeltmeleri de ilk oturuma kontrol ettirdim. Kontrol, yeni kurallardan birinin masum soruları sağlık şikâyeti saydığını buldu; o da düzeltildi. Son olarak repoyu ChatGPT'ye de incelettim; bulduğu dört sorunun dördü de koda karşı doğrulandı ve düzeltildi.

---

## Brief'teki istekler ve karşılıkları

| İstenen | Nerede / nasıl doğrulandı |
|---|---|
| **A1** Her mesaja tek konu | [`siniflandirici.py`](A-mesaj-otomasyonu/siniflandirici.py), öncelik sıralı kurallar · [`talepler.json`](A-mesaj-otomasyonu/talepler.json) `konu` alanı |
| **A2** iade/istenmeyen etki → `devret: true`, ürün önerisi ya da teşhis yok | Sabit devir metni, bu konularda ürün araması yapılmıyor (testi var) · #4, #5 · sorun anlatan mesajlar ("yüzümde yara çıktı", "şişe patlamış") ürün sorusu sanılmıyor (testi var) |
| **A3** Sipariş sorgusu; `userId ≠ musteri_id` ise bilgi verilmez, devret | `siparis_sorgula()` başkasının siparişini hiç dışarı vermiyor · #1 · sahiplik kontrolü bozulunca **6 test kırmızı** |
| **A3** Sipariş bulunamazsa düzgün uyarı | #3 (9999 → API "not found") |
| **A4** `talepler.json` → `{ id, konu, devret, cevap_taslagi, not }` | [`talepler.json`](A-mesaj-otomasyonu/talepler.json) |
| **A4** Tek sayfalık özet | [`ozet.html`](A-mesaj-otomasyonu/ozet.html) + terminal özeti |
| **A Bonus** `/products/search` ile ürün arama | #10, #14 (kozmetik kategori filtresiyle) |
| **B1** Günde 1 kez zamanlanmış tetikleyici | `Günlük Tetikleyici (09:00)`, Schedule Trigger |
| **B2** Tüm sayfaları gezme; ad, **sayısal** fiyat, yorum, link | Son sayfa sayfalama çubuğundan okunuyor (bugün 20) → 1..N · `$1,139.54` → `1139.54` · ayrıştırılan ürün sayısı sitedeki toplamla ("117 items") karşılaştırılıyor |
| **B3** Tarih damgasıyla tabloya yazma | **Google Sheets** · `fiyat_gecmisi` (append) + `son_durum` (appendOrUpdate) |
| **B4** Değişiklik tespiti + bildirim | Yeni / fiyatı değişen / kalkan ürünler → **e-posta** |
| **B5** Hata dalı, sessiz "başarılı" yok | Site açılmazsa / ürün yoksa / sayfa eksikse: hata e-postası → **Stop and Error** |
| **B** Başlangıç şablonu (ad + link) | [#4640 Competitor Price Monitoring…](https://n8n.io/workflows/4640-competitor-price-monitoring-with-web-scrapinggoogle-sheets-and-telegram/) · [`akis-aciklama.md`](B-n8n/akis-aciklama.md) ve akıştaki not |
| **B Bonus** Ekran görüntüsü | [n8n editöründe akış](B-n8n/ekran-goruntuleri/n8n-editor-akis.png) + [gerçek n8n çalıştırma kaydı](B-n8n/n8n-calistirma-kaydi.md) |
| Promptlar sırasıyla | [`promptlar/A-claude-code.md`](promptlar/A-claude-code.md) · [`promptlar/B-n8n.md`](promptlar/B-n8n.md) · yeniden ifade edildikleri dosyada belirtildi, orijinaller git geçmişinde |
| Depo temiz, küçük commit'ler | Anahtar, `.env` ya da `node_modules` yok · 31 commit |

## Hızlı başlangıç

Gereksinimler: **Python 3.10+** (ek paket yok, sadece standart kütüphane) · B testleri için **Node.js 18+**. API anahtarı, `.env` ya da hesap gerekmiyor. (macOS/Linux'ta `python` yerine `python3`.)

```bash
# Bölüm A — mesajları işle: talepler.json + ozet.html üretir, terminale özet basar
cd A-mesaj-otomasyonu
python main.py
python -m unittest discover -s tests -v                    # 44 test, ağ gerektirmez
python degerlendirme/degerlendir.py                        # sınıflandırıcı: 50 mesajlık geliştirme seti
python degerlendirme/degerlendir.py degerlendirme/test_seti.json   # 24 mesajlık test seti

# Bölüm B — n8n Code düğümlerinin testleri (ilk test canlı siteye bağlanır)
cd ../B-n8n
node test/kod-testi.mjs                       # 10 test
python araclar/workflow_olustur.py            # workflow.json'u kod/*.js'ten üretir ve doğrular
python araclar/sema_olustur.py                # akis-semasi.svg'yi workflow.json'dan üretir
```

`workflow.json`'u n8n'e aktarmak için: *Workflows → Import from File*. Kurulum adımları [`B-n8n/akis-aciklama.md`](B-n8n/akis-aciklama.md) içinde.

## Klasör yapısı

```
├── A-mesaj-otomasyonu/
│   ├── main.py               giriş noktası (CLI)
│   ├── siniflandirici.py     kural tabanlı konu atama (öncelik sıralı)
│   ├── isleyici.py           iş kuralları: devir, sipariş sahipliği kontrolü, cevap taslakları
│   ├── dummyjson_api.py      API istemcisi (zaman aşımı, yeniden deneme, 404)
│   ├── ozet.py               terminal + HTML özet
│   ├── mesajlar.json         girdi (case'ten)
│   ├── talepler.json         ÇIKTI
│   ├── ozet.html             ÇIKTI: tek sayfalık özet
│   ├── tests/                44 birim testi (sahte API ile, ağsız)
│   └── degerlendirme/        etiketli geliştirme (50) + test (24) seti, ölçüm betiği ve sonuçları (güncel: sonuc_guncel.txt)
├── B-n8n/
│   ├── workflow.json         n8n'e import edilecek akış
│   ├── hata-workflow.json    (ek) Error Trigger → e-posta yedek hata bildirimi
│   ├── akis-aciklama.md      adım adım akış · başlangıç şablonu (ad + link) · neyi değiştirdim
│   ├── akis-semasi.svg       akış şeması (workflow.json'dan üretildi)
│   ├── ekran-goruntuleri/    n8n 2.40.7 editöründe akış
│   ├── n8n-calistirma-kaydi.md  gerçek n8n 2.40.7'de CLI ile çalıştırma sonuçları
│   ├── kod/                  Code düğümlerinin JS kaynakları (workflow.json'a gömülür)
│   ├── test/kod-testi.mjs    aynı JS'in Node.js testleri (canlı site dahil)
│   └── araclar/              workflow.json ve şema üreticileri
└── promptlar/
    ├── A-claude-code.md
    └── B-n8n.md
```

---

## Bölüm A — Müşteri mesajı otomasyonu

### Sonuç (15 mesaj)

| # | Mesaj (kısa) | Konu | Devret | Ne oldu |
|---|---|---|:---:|---|
| 1 | "12 numaralı siparişim nerede?" (müşteri 7) | siparis-durumu | **✔** | Sipariş #12'nin sahibi **userId 12**, yazan müşteri 7 → **bilgi verilmedi**, temsilciye devredildi |
| 2 | "5 numaralı siparişimin durumu?" (müşteri 5) | siparis-durumu | – | Sahibi eşleşti → ürünler + toplam tutar (1.467,88 $) |
| 3 | "9999 numaralı siparişim ulaşmadı" | siparis-durumu | **✔** | API "not found" → düzgün uyarı mesajı + temsilci kontrolü |
| 4 | "Serumu kullandım, yüzüm yandı ve kızardı" | istenmeyen-etki | **✔** | Sabit devir metni, **teşhis/öneri yok**, öncelik: yüksek |
| 5 | "Kutu ezik geldi, iade etmek istiyorum" | iade-sikayet | **✔** | Sabit devir metni |
| 6 | "Where is my order #3?" (müşteri 3) | siparis-durumu | – | Eşleşti → **İngilizce** taslak ($1,794.85) |
| 7 | "Takipçi kasmak ister misiniz? bit.ly/…" | diger | – | **Spam**: cevap üretilmedi, linke tıklanmamalı |
| 8 | "Güneş kremi fiyatı? + 4 numaralı siparişim" | siparis-durumu | **✔** | Sipariş bilgisi verildi (sahibi eşleşti). Güneş kremi fiyatı sistemde yok → temsilci tamamlıyor |
| 9 | "Retinol serumunuz var mı? Kuru ciltte…" | urun-sorusu | **✔** | Stok + cilt uygunluğu sistemde yok → ürün uzmanı tamamlıyor |
| 10 | "Nemlendirici krem ne kadar?" | fiyat | – | **Bonus arama**: sistemdeki en yakın ürün "Vaseline Men Body and Face Lotion — 9,99 $" + doğru ürün mü diye soru |
| 11 | "C vitamini serumu hangi cilt tipine?" | urun-sorusu | **✔** | Cilt tipi bilgisi sistemde yok → ürün uzmanı tamamlıyor |
| 12 | "Siparişler hangi kargo firmasıyla?" | diger | **✔** | Genel SSS. `[KARGO FİRMASI]` yer tutucusu → temsilci dolduruyor (bilgi uydurulmadı) |
| 13 | "Tonik 200 ml mi? Alkol var mı?" | urun-sorusu | **✔** | "200" sipariş no sanılmadı. Hacim + alkol içeriği → ürün uzmanı tamamlıyor |
| 14 | "İndirim kodu? Fiyat listesi?" | fiyat | **✔** | **Bonus**: API'den kozmetik fiyat listesi. İndirim kodu uydurulmadı → temsilci ekliyor |
| 15 | "Ürünleriniz hayvanlarda test ediliyor mu?" | urun-sorusu | **✔** | Politika bilgisi sistemde yok → ürün uzmanı tamamlıyor |

**Konu dağılımı:** siparis-durumu 5 · urun-sorusu 4 · fiyat 2 · diger 2 · iade-sikayet 1 · istenmeyen-etki 1 → **11 mesaj insana devredildi.** Nedenleri: hassas konu #4, #5 · sipariş doğrulanamadı #1, #3 · sistemde olmayan bilgi #8, #9, #11–#15. Doğrudan gönderilebilir taslak: #2, #6, #10 · spam: #7. Nedenler [`ozet.html`](A-mesaj-otomasyonu/ozet.html)'de ayrı tabloda. Detaylar [`talepler.json`](A-mesaj-otomasyonu/talepler.json) ve [`ozet.html`](A-mesaj-otomasyonu/ozet.html) içinde.

### Tasarım kararları

**1. Kural tabanlı sınıflandırma (LLM değil).** Case anahtarsız çalışmayı istiyor. Kurallar deterministik ve test edilebilir. Her kararın gerekçesi (eşleşen ifade) `not` alanına yazılıyor, temsilci neden o konunun seçildiğini görebiliyor. Türkçe karakterler katlanıyor (`şikayet` = `sikayet`), böylece Türkçe karakter kullanmadan yazan müşteri de doğru sınıflanıyor. Kuralların bu 15 mesajın dışında ne kadar tuttuğu [aşağıda ölçüldü](#sınıflandırıcıyı-yeni-mesajlarla-ölçtüm).

**2. Öncelik sırası:** `istenmeyen-etki > iade-sikayet > spam > siparis-durumu > fiyat > urun-sorusu > diger`. Sağlık şikâyeti, aynı mesajda sipariş numarası da geçse hiçbir zaman başka bir konunun altında kaybolmaz (testi var). Kazanmayan konular `ikincil_konular` olarak saklanıyor. Örneğin #8'de sipariş yanıtlanıyor, fiyat sorusu da taslakta ele alınıyor.

**3. Sipariş güvenliği (en kritik kısım):**
- `siparis_sorgula()` sipariş **başka müşteriye aitse hiçbir alanını dışarı döndürmüyor**. Ürün, tutar ya da sahip bilgisi programın geri kalanına hiç ulaşmıyor (veri minimizasyonu).
- **Fail-closed:** `userId` ya da `musteri_id` eksik veya sayı değilse eşleşme yok sayılıyor. `musteri_id` yoksa API'ye hiç gidilmiyor.
- **"Bulunamadı" ve "başkasına ait" durumlarında müşteriye aynı metin gidiyor.** Farklı metin gitseydi, biri numara deneyerek hangi sipariş numaralarının var olduğunu öğrenebilirdi. Fark sadece iç notta ve `devret` alanında. Bu yüzden 9999 (bulunamadı) de temsilciye devrediliyor, çünkü temsilci müşterinin gerçek siparişini bulabilir.
- Test: #12'nin ürünleri ("Rolex", "Sportbike") ve tutarı çıktının **hiçbir alanında** geçmiyor. Sahiplik kontrolünü bilerek devre dışı bıraktığımda **5 test kırmızıya döndü** (ikinci oturumda da tekrarlandı; tutarlılık testi eklendikten sonra 6). Yani testler bu açığı gerçekten yakalıyor.

**4. Hassas konular:** `iade-sikayet` ve `istenmeyen-etki` için taslak, **sabit bir devir bildirimi** ("mesajınızı uzman temsilcimize ilettik"). Otomatik ürün önerisi ya da teşhis yok, bu konularda ürün araması da yapılmıyor (testi var). Temsilciye yönelik iç notta istenmeyen etki için *yüksek öncelik* ve kozmetovijilans hatırlatması var: lot no, fotoğraf, gerekirse TİTCK bildirimi.

**5. Bilgi uydurmama.** API'de kargo durumu, ürün içeriği ya da indirim kodu yok. Taslaklar bunları uydurmuyor, ya ilgili uzmana yönlendiriyor ya da `[KARGO FİRMASI]` gibi açık bir yer tutucu bırakıyor. İç not neyin doldurulması gerektiğini söylüyor.

**6. Bonus ürün araması.** DummyJSON genel bir mağaza: `cream` araması **"Ice Cream"** (market ürünü) ve açıklamasında "creamy" geçen **"Red Lipstick"** döndürüyor. Bu yüzden sonuçlar *kozmetik kategorisi (beauty / skin-care / fragrances) + başlıkta terim geçmesi* şartıyla filtreleniyor. Türkçe terimler İngilizce arama terimlerine eşleniyor (nemlendirici → moisturizer, lotion). Kozmetik terimlerinin çoğu (serum, retinol, sunscreen, toner) API'de sonuç vermiyor. Bu durum iç nota yazılıyor, müşteriye "bulunamadı" denmiyor. Bulunan ürün müşteriye "kataloğumuzdaki ürün" diye kesin değil, "sistemimizde bulduğumuz en yakın ürün" diye ve doğru ürün olup olmadığı sorularak sunuluyor.

**7. Diğer detaylar:** İngilizce mesaja İngilizce taslak. Spam'e cevap yok. `Tonik 200 ml` içindeki 200 sipariş numarası sanılmıyor (sipariş numarası sadece "12 numaralı sipariş", "sipariş no:", "order #3" gibi açık bağlamla alınıyor). API'de zaman aşımı, 5xx hatalarında yeniden deneme var; ağ tamamen çökerse program çökmüyor, mesaj temsilciye devrediliyor (testi var). Windows konsolunda Türkçe karakter bozulmasın diye stdout UTF-8'e alınıyor.

**8. `devret` = bu talebi bir insan tamamlamalı.** Brief, hassas konular ve başkasına ait siparişler için devri zorunlu tutuyor. Bunlara ek olarak taslak, sistemde olmayan bir bilgi için "temsilcimiz / uzmanımız iletecek" diyorsa ya da `[KARGO FİRMASI]` gibi bir yer tutucu içeriyorsa talep yine devrediliyor, çünkü verilen sözün bir sahibi olmalı. İlk sürümde bu mesajlar `devret: false` idi; tutarsızlığı harici inceleme buldu. Her devrin nedeni `not` alanında ve özet sayfasında ayrı gösteriliyor. API'de ürün içeriği, cilt uygunluğu, kargo firması ya da indirim kodu bilgisi yok; otomasyon bunları uydurmak yerine doğru kişiye yönlendiriyor. Bu yüzden 15 mesajın 11'i insana gidiyor. Sipariş bulununca hazırlanan taslak da artık "kargo durumunu ayrıca bildireceğiz" gibi tutamayacağı bir söz vermiyor; brief'in istediği gibi ürün adları ve toplam tutarla sınırlı. Bu kuralı bir test sürekli denetliyor.

### Tartışmalı sınıflandırmalar (bilinçli seçimler)
- **#8** hem fiyat hem sipariş soruyor. Brief tek konu istediği için **siparis-durumu** seçildi: güvenlik kontrolü gerektiren ve aksiyon alınması gereken niyet bu. Fiyat sorusu da taslakta ele alınıyor; fiyat sistemde olmadığı için temsilci tamamlıyor.
- **#12** "Siparişler hangi kargo firmasıyla…" belirli bir siparişin durumu değil, genel bir SSS sorusu. Bu yüzden **diger**. `siparis-durumu` seçilseydi müşteriye anlamsız şekilde sipariş numarası sorulurdu.
- **#15** hayvan deneyi, ürün politikasıyla ilgili bir soru. Bu yüzden **urun-sorusu**. `diger` de savunulabilirdi.

### Sınıflandırıcıyı yeni mesajlarla ölçtüm

15 mesajın hepsini doğru sınıflamak, kuralların genellediğini göstermez; kurallar bu 15 mesaja bakılarak yazıldı. Asıl risk, **hassas bir mesajın insana gitmeden otomatik cevaplanması**. Bu yüzden ölçütüm doğruluk değil, bu risk oldu.

| Adım | Set | Doğruluk | Hassas mesaj insana gidiyor | Hassas mesaj otomatik cevaplanıyor |
|---|---|---|---|---|
| 1. İlk ölçüm (kurallara dokunmadan) | geliştirme, 50 mesaj | 37/50 (%74) | 12/18 | **6** |
| 2. Açıklar kapatıldıktan sonra | geliştirme | 50/50 | 18/18 | 0 *(görülmüş set, iyimser)* |
| 3. **Tek seferlik ölçüm** | **test, 24 mesaj** | **18/24 (%75)** | **11/12** | **1** |
| 4. O tek açık kapatıldıktan sonra | test | 18/24 | 12/12 | 0 *(artık görülmüş set)* |
| 5. Harici inceleme (ChatGPT) düzeltmelerinden sonra | geliştirme | 50/50 | 18/18 | 0 *(görülmüş set)* |
| 6. Harici inceleme düzeltmelerinden sonra | test | 20/24 (%83) | 12/12 | 0 *(görülmüş set)* |

- **Adım 1'de bulunan:** "Kremi sürdükten sonra yüzümde kabarcıklar çıktı" gibi 6 hassas mesaj, içlerinde ürün adı geçtiği için *ürün sorusu* sanılıp otomatik cevaplanıyordu. İlk README "kalıplara uymayan ifade güvenli tarafa (diger + devret) düşer" diyordu. **Ölçüm bunun yanlış olduğunu gösterdi.** Mesaj kalıplara uymuyor değildi; *yanlış* kalıba uyuyordu.
- **Düzeltmeler (tek tek ezber yerine genel kurallar):** (a) *"…dan/den sonra" (ya da "sonra") + kişinin kendi vücut bölgesi ("yüzüm", "cildimde", "saçlarım")* → kullanım sonrası şikâyet. Belirti kelimesi listede olmasa da mesaj insana gider. (b) Kaçan şikâyet/belirti kalıpları eklendi ("paramı geri", "yanlış renk", "berbat", "pullanma"…). (c) **Soru olmayan cümle otomatik ürün cevabı almaz** ("Şişe kargoda patlamış, her yer krem olmuş" bir soru değil, şikâyet). (d) "bedava" tek başına spam sayılmıyor ("2 alana 1 bedava kampanyanız geçerli mi?").
- **Test seti düzeltmelerden önce yazılıp commit'lendi** (`2b481da`) ve düzeltmelerden sonra **bir kez** çalıştırıldı (`485fd82` → sonuç [`sonuc_test_seti.txt`](A-mesaj-otomasyonu/degerlendirme/sonuc_test_seti.txt)). Kaçan tek hassas mesaj (t08) için kural (c) ölçümden **sonra** eklendi (`343f6b3`). Bu yüzden adım 4'teki sonuç bağımsız bir ölçüm değildir.
- **Hâlâ yanlış konu verilen 6 test mesajı** (son kullanma tarihi geçmiş, sahte ürün, çift çekim, "order 8 hasn't shipped"…) konusu yanlış olsa da `diger` + devret ile **insana gidiyor**. Bunları bilerek kurala eklemedim; test setine göre kural yazmak ölçümü anlamsız kılardı.
- **Kuralın bedeli de ölçüldü (sonraki kontrol):** İki set sadece "hassas mesaj kaçtı mı?" sorusuna bakıyor, "masum mesaj boşuna alarm verdi mi?" sorusuna bakmıyor. Kural (a)'nın ilk hâli vücut kelimesini herhangi bir biçimde kabul ediyordu. Bu yüzden 10 masum sorunun 6'sını **yüksek öncelikli sağlık şikâyeti** sayıyordu. Örneğin "Sipariş verdikten sonra elime ne zaman ulaşır?" sorusunda "elime" teslimat deyimi. Diğerleri: "kargo yüzünden" (sebep), "yüz kremi" ve "saç maskesi" (ürün adı). Müşteriye de "Yaşadığınız durum için çok üzgünüz" taslağı hazırlanıyordu. Vücut kelimesi birinci şahıs iyelik ekine bağlandı ("yüzüm", "cildimde"): **10 masum sorunun hiçbiri** artık alarm vermiyor. İki setin sonuçları değişmedi; t01 ve t02 hâlâ bu kuralla yakalanıyor. Bu hedefli bir kontroldü, bağımsız bir ölçüm değil. Masum sorular bu açığı bulmak için yazıldı ve [testlere](A-mesaj-otomasyonu/tests/test_siniflandirici.py) eklendi (`YanlisAlarm`). Kalan bilinen yanlış alarm: "Kremi yüzüme sürdükten sonra ne kadar beklemeliyim?". Bu soru insana gider, yani hata güvenli tarafta kalır.
- **Harici inceleme (ChatGPT):** İnceleme, "Kremi sürünce yüzümde yara çıktı, ne yapmalıyım?" ve "Krem şişesi kargoda patlamış, ne yapmalıyım?" mesajlarının hâlâ *ürün sorusu* sayılıp otomatik cevaplandığını gösterdi. İkisi de doğrulandı ve aynı açığın üç varyantı daha bulundu (örn. "cildim kötü oldu, ne yapayım?"). Kök neden aynıydı: ürün adı ve soru varsa otomatik ürün cevabı veriliyordu; hassaslık yalnızca kelime listesiyle anlaşılıyordu. Ezber yerine üç genel kural eklendi:
  - (e) Kişinin kendi vücudu + olay anlatımı → istenmeyen etki. Olay; zarf-fiil ("sürünce"), "…dan sonra" ya da geçmiş zaman fiili olabilir.
  - (f) Hasar fiilleri ("patlamış", "dökülmüş", "sızdırıyor") → iade/şikâyet.
  - (g) "Ne yapmalıyım" gibi yardım isteyen bir ifade içeren mesaj, ürün ya da fiyat sorusu gibi görünse de otomatik cevap almaz, devredilir.

  Masum sorular ("Yüzüm için hangi serum uygun?") hâlâ ürün sorusu. Test seti bu turdan önce zaten kullanıldığı için adım 6 bağımsız bir ölçüm değil. Güncel çıktılar [`sonuc_guncel.txt`](A-mesaj-otomasyonu/degerlendirme/sonuc_guncel.txt) dosyasında; eski sonuç dosyaları "tarihsel kayıt" olarak işaretlendi.
- **Dürüst sınır:** Bu iki seti gerçek müşteriler değil, inceleme oturumundaki Claude Code yazdı. Test seti düzeltmelerden önce yazıldı ama aynı oturumda yazıldığı için tam bağımsız sayılmaz. Gerçek doğruluğu firmanın geçmiş WhatsApp/Instagram mesajlarından etiketlenmiş bir örnek gösterir.

Bütün bunlar birim testlerine de eklendi (29 → 36 → 38 → 44 test). Geliştirme setindeki hiçbir hassas mesajın otomatik cevaplanmadığını bir test sürekli kontrol ediyor.

## Bölüm B — n8n fiyat takibi

Başlangıç şablonu: **[Competitor Price Monitoring with Web Scraping, Google Sheets & Telegram](https://n8n.io/workflows/4640-competitor-price-monitoring-with-web-scrapinggoogle-sheets-and-telegram/)** (#4640). Seçim tablosu ve bildirim kanalı: **Google Sheets + e-posta**.

Akış: günlük 09:00 tetikleyici → 1. sayfadan son sayfa numarasını bul (bugün 20) → tüm sayfaları gez → ad / **sayısal fiyat** / yorum / link → sağlık kontrolü → Google Sheets'teki `son_durum` ile karşılaştır → yeni / fiyatı değişen / kalkan ürünleri e-postayla bildir → `fiyat_gecmisi`ne tarih damgasıyla ekle. **Hata dalı:** site açılmazsa, sayfa eksik kalırsa ya da hiç ürün gelmezse hata e-postası gider ve akış **Stop and Error** ile başarısız biter.

**Gerçek n8n'de denendi:** Akış yerel bir n8n 2.40.7'ye CLI ile içe aktarılıp çalıştırıldı. 20 sayfa gezildi ve 117 ürün sayısal fiyatla ayrıştırıldı; akış credential bağlanmamış Google Sheets adımına kadar hatasız geldi. İki hata senaryosunda (site kapalı / hiç ürün yok) hata dalı çalıştı ve yürütme `error` durumunda bitti ([çalıştırma kaydı](B-n8n/n8n-calistirma-kaydi.md)). Bu test JSON'daki iki eksiği ortaya çıkardı (CLI için workflow `id`, CLI ile çalıştırma için Manual Trigger) ve ikisi de düzeltildi. İkinci oturumdaki değişikliklerden sonra akış yeniden içe aktarılıp çalıştırıldı; sonuç aynıydı.

**Eksiksizlik kontrolü (harici inceleme):** Sayfalama bağlantıları bir gün bulunamazsa akış yalnızca 1. sayfayı tarar. Bu durumda kalan ürünler yanlışlıkla "kaldırıldı" diye bildirilebilirdi. Artık ayrıştırılan ürün sayısı sitenin kendi yazdığı toplamla ("117 items") karşılaştırılıyor. Sayılar tutmazsa ya da toplam okunamazsa tarama sağlıksız sayılıyor ve hata dalına gidiyor. Bunun Node testi var; güncel akış n8n'de yeniden çalıştırıldı ve 117 = 117 sonucu alındı.

Adım adım açıklama, şablondan yapılan değişiklikler (şablondaki `NaN` yanlış-alarm hatası dahil) ve test sonuçları: **[`B-n8n/akis-aciklama.md`](B-n8n/akis-aciklama.md)**.

**n8n editöründe** (yerel n8n 2.40.7; kırmızı üçgenler credential'ı bağlanmamış Sheets/SMTP düğümleri):

![n8n editöründe akış](B-n8n/ekran-goruntuleri/n8n-editor-akis.png)

---

## Yapay zekâ aracını nasıl kullandım

Claude Code'a görevi tek bir başlangıç promptuyla verdim: case'i e-postamdan bulup iki bölümü eksiksiz, birlikte tamamlamak. Case e-postasını ve eklerini Gmail bağlantısı üzerinden kendisi okudu. Karar gerektiren iki noktada bana sordu, ben seçtim: teslim için GitHub reposunu benim açmam ve B'de **Google Sheets + e-posta** kullanılması. Sonra repoyu açıp linkini verdim.

Çalışma sırasında izlenen yöntem:
1. **Önce veriyi doğrulama:** Kod yazılmadan önce DummyJSON'daki ilgili siparişler (#12'nin başka müşteriye ait olduğu, 9999'un 404 döndüğü), ürün araması sonuçları ve test sitesinin HTML'i / sayfalaması elle kontrol edildi.
2. **Parçalama:** A'da sınıflandırıcı → API istemcisi → iş kuralları → özet → testler. B'de şablonu indirip inceleme → eksiklerini listeleme → Code düğümlerini ayrı dosyada yazma → Node.js'te test → `workflow.json` üretimi ve doğrulama.
3. **Çıktıyı sorgulama:** İlk çalıştırmadaki 15 taslak tek tek okundu ve bulunan kusurlar düzeltildi: "alkol var mı" stok sorusu sanılıyordu, kargo SSS taslağında uydurma bir süreç cümlesi vardı, notlarda noktalama eksikti.
4. **Testin kendisini test etme:** Tüm testler ilk seferde geçince, sahiplik kontrolü bilerek bozuldu ve testlerin bunu yakaladığı doğrulandı (5 test kırmızı).
5. **Varsayımları kaynağından doğrulama:** n8n düğüm sürümleri ve parametre adları, n8n-nodes-base 2.15.1 paketinin kendisinden kontrol edildi.
6. **Bağımsız inceleme (ikinci oturum):** İlk sürüm bittikten sonra, önceki konuşmayı bilmeyen yeni bir Claude Code oturumuna repoyu brief'e göre baştan denetlettim. Bu oturum:
   - bütün testleri ve komutları README'deki talimatla yeniden çalıştırdı ve kodu satır satır okudu,
   - sınıflandırıcıyı yeni etiketli mesajlarla ölçtü, hassas mesaj kaçırma açığını buldu ve kapattı ([yukarıda](#sınıflandırıcıyı-yeni-mesajlarla-ölçtüm)),
   - B'de iki küçük sorun buldu: Sheets'in eklediği `row_number` alanı tabloya geri yazılabilirdi; ayrıca arayüzden içe aktarımda Error Workflow bağlantısı kopuyordu. İkisi de düzeltildi ya da belgelendi. Güncel akış gerçek n8n'de yeniden çalıştırıldı,
   - n8n editörünün ekran görüntüsünü ekledi,
   - teslim e-postası taslağında repo linkinin çıplak link yerine bir Google yönlendirme adresi (`google.com/url?q=…`) olarak yazıldığını fark etti ve taslağı düzeltmeye çalıştı.
7. **İnceleme sonrası kontrol (ilk oturum):** İkinci oturumun değişikliklerini ilk oturuma geri verip kontrol ettirdim. Bu kontrolde:
   - Bütün testler ve ölçümler yeniden çalıştırıldı. Raporlanan sayılar aynı çıktı; 15 mesajın `talepler.json` çıktısı değişmemişti.
   - `row_number` düzeltmesi, ekran görüntüsü ve içe aktarım notu yerinde bulundu.
   - Yeni "kullanım sonrası şikâyet" kuralının masum soruları sağlık şikâyeti saydığı bulundu ve düzeltildi ([yukarıda](#sınıflandırıcıyı-yeni-mesajlarla-ölçtüm)).
   - Taslağın ham MIME içeriğine bakıldı: link hâlâ yönlendirme olarak kayıtlıydı. Deneme gösterdi ki Gmail bağlantısı, API ile yazılan her linki kaydederken yönlendirmeye çeviriyor. Bu yüzden link, gönderimden önce Gmail'de elle yapıştırılıyor. E-postayı yapay zekâ değil, ben gönderiyorum.
8. **Harici inceleme (ChatGPT):** Repoyu ayrıca ChatGPT'ye inceletip bulgularını Claude Code'a kontrol ettirdim. Dört bulgunun dördü de koda karşı doğrulandı ve düzeltildi:
   - sorun anlatan iki mesaj otomatik ürün cevabı alıyordu,
   - "uzmanımız iletecek" diyen taslaklar `devret: false` idi,
   - test API ürünleri "kataloğumuz" / "güncel fiyatlarımız" diye kesin sunuluyordu,
   - sayfalama bağlantıları bulunamazsa n8n akışı tek sayfayı tam tarama sayabilirdi.

   Eski ölçüm dosyaları da "tarihsel" olarak işaretlendi. Bu turda aynı tutarsızlığın bir örneği daha bulunup kaldırıldı: sipariş taslağı "kargo durumunu ayrıca bildireceğiz" diye söz veriyordu.

## Nerede takıldım

Ayrıntılar ve çözümleri [`promptlar/`](promptlar/) dosyalarındaki süreç günlüğünde.

- E-posta eklerini diske yazarken ve git'te **Windows 260 karakter yol sınırı** hataları çıktı. Masaüstü uygulamasının çalışma klasörü, arka planda çok uzun bir sanal yola yönlendiriliyordu. Python testleri "dosya bulunamadı" verdi. Proje kısa bir yola taşındı, git'te `core.longpaths` açıldı.
- `npm install n8n` ilk denemede bash ortamında `cmd.exe` başlatılamadığı için başarısız oldu. Önce düğüm tanımları n8n-nodes-base paketinden okundu, sonra n8n PowerShell ile kuruldu.
- Gerçek n8n testinde `workflow.json` iki yerde takıldı: CLI içe aktarımı workflow `id` istedi, CLI ile çalıştırma da Manual Trigger istedi. İkisi de düzeltildi.
- **İkinci oturumda:** n8n ekran görüntüsü ilk denemede boş çıktı. Headless Edge'in `--screenshot` seçeneği, n8n'in kanvası sonradan çizmesini beklemiyordu. DevTools protokolüyle 15 saniye bekleyip çekince düzeldi. Ayrıca kural düzeltmelerini topluca uygulayan ilk betik, Python kaçış karakterlerini (`\w`, `\b`) bozduğu için hiçbir şeyi değiştirmedi; betikteki kontrol bunu yakaladı ve düzeltmeler tek tek yapıldı.

## Neyi bitiremedim / sınırlar

- **n8n'de Google Sheets ve e-posta adımlarını canlı çalıştıramadım.** Credential gerekiyor ve bende firmanın Sheet'i ya da SMTP bilgisi yok. Bu adımların girdisi olan değişiklik tespiti mantığı Node testleriyle doğrulandı; akışın geri kalanı gerçek n8n'de çalıştırıldı. İçe aktarımdan sonra Sheets sütun eşlemesinin bir kez kontrol edilmesi gerekiyor.
- **Ekran görüntüsü n8n'in tasarım görünümü, çalıştırma görünümü değil.** Yerel n8n arayüzü sahip hesabı kurulumu istiyor. Çalıştırmanın kanıtı [CLI çalıştırma kaydı](B-n8n/n8n-calistirma-kaydi.md).
- **Sınıflandırıcı kural tabanlı ve ölçüldü:** İlk görülmemiş ölçümde doğruluk %75'ti ve hassas mesajların 11/12'si insana gidiyordu. Her yeni inceleme (ikinci oturum, ChatGPT) kurallara uymayan yeni bir ifade buldu. Açıklar genel kurallarla kapatıldı, ama yeni ifadeler her zaman çıkacak. Bu yüzden tasarım, emin olunamayan her durumda insana devretmeye göre kurulu. Üretimde bir sonraki adım iki parçalı: (1) firmanın gerçek mesajlarından etiketli bir set; (2) kuralların emin olmadığı mesajlar için yedek bir LLM sınıflandırıcı, aynı "hassas mesaj kaçırma" ölçütüyle ölçülerek. Brief anahtarsız çalışmayı istediği için bu repoya LLM eklemedim.
- DummyJSON'da kargo/teslimat durumu yok. Bu yüzden sipariş taslakları ürünleri ve tutarı veriyor, kargo durumunu temsilciye bırakıyor.
