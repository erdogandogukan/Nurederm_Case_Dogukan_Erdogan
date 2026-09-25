# Bölüm A — Claude Code'a yazdığım promptlar

**Araç:** Claude Code masaüstü uygulaması, model Claude Opus 5.5. İki oturum kullandım:
- **Oturum 1 (11:06–11:50):** Case'in iki bölümünün ilk tam sürümü. İki bölüm aynı oturumda yapıldı, bu yüzden ilk prompt iki dosyada da var.
- **Oturum 2 (11:54–12:13):** Teslimden önce, önceki konuşmayı bilmeyen yeni bir oturumda bağımsız inceleme ve düzeltmeler ([aşağıda](#oturum-2--bağımsız-inceleme)).

**Kural:** Promptlar silinmeden, düzeltilmeden (yazım hataları dahil) ve sırasıyla aşağıda. Saatler yaklaşıktır.

**Neden `/export` çıktısı yok?** Oturum dökümlerinde case ile ilgisi olmayan kişisel veriler de var: Gmail aramasının ham sonuçları, başka e-postalarımın konu ve özetleri. Bu yüzden ham dökümleri herkese açık depoya koymadım. Promptlarımı buraya birebir kopyaladım. Yapay zekânın yaptığı işleri ve karşılaştığı hataları da aşağıya özet olarak ekledim.

---

## Prompt 1 · ≈11:06

```
ise girmek icin bir case geldi cok onemli mail adresimde var case icerigi beraber tum ayrintilariyla eksiksiz yapalim
```

## Prompt 2 · ≈11:10 · Claude Code'un sorduğu iki soruya verdiğim cevaplar (seçenekli soru)

> **Soru:** Teslim için GitHub reposu gerekiyor ama bilgisayarında `gh` (GitHub CLI) yok. Repoyu nasıl oluşturalım?
> **Cevabım:** `Ben açıp link veririm (Önerilen)`

> **Soru:** Bölüm B (n8n fiyat takibi) için hangi tablo ve bildirim kanalı kullanılsın? Brief ikisini de bize bırakıyor.
> **Cevabım:** `Google Sheets + E-posta (Önerilen)` *(bkz. B-n8n.md)*

## Prompt 3 · ≈11:25

```
https://github.com/erdogandogukan/Nurederm_Case_Dogukan_Erdogan olusturdum
```

## Prompt 4 · ≈11:50 · Claude Code'un sorusuna verdiğim cevap (seçenekli soru)

> **Soru:** Teslim e-postası nasıl gitsin? (Son teslim 14:00, şu an ~11:50.)
> Seçenekler: *İnceledim, gönder* · *Gmail'de taslak oluştur* · *Önce değişiklik isteyeceğim*
> **Cevabım:** `Gmail'de taslak oluştur` (Claude Code taslağı hazırladı; e-postayı kontrol edip kendim gönderiyorum)

---

## Claude Code'un Bölüm A'da yaptıkları (özet süreç günlüğü)

Bu bölüm prompt değil. Yapay zekânın işi nasıl parçaladığını ve hata çıkınca ne yaptığını gösteren özet bir günlük.

1. **Case'i bulma:** Gmail'de "case / görev / mülakat" gibi kelimelerle arama yapıldı ve Nurederm yazışması bulundu (11:00'de gelen e-posta, ekleri `case-brief.md` ve `mesajlar.json`). Gmail aracında ek indirme fonksiyonu yok. Bu yüzden e-posta ham MIME olarak çekildi ve ekler Python ile çıkarıldı.
   - **Hata:** İlk denemede `FileNotFoundError` alındı. Sebep: aracın çıktı dosyasının yolu Windows'un 260 karakter sınırını aşıyordu. **Çözüm:** `\\?\` uzun yol önekiyle okundu.
2. **Koddan önce veriyi doğrulama:** `curl` ile `/carts/12` → `userId: 12`, yani mesajı yazan müşteri 7 değil. Bu **tuzak**. `/carts/5`, `/carts/3`, `/carts/4` sahipleriyle eşleşiyor. `/carts/9999` → HTTP 404. Ürün araması: `serum`, `retinol`, `sunscreen`, `toner` → 0 sonuç. `cream` → **"Ice Cream"** (market ürünü) + "Red Lipstick". Buradan "kozmetik kategorisi + başlık eşleşmesi" filtresi kararı çıktı.
3. **Karar gerektiren iki soru bana soruldu** (Prompt 2).
4. **Repo iskeleti:** `git add` sırasında `Filename too long` hatası alındı. **Çözüm:** `git config core.longpaths true`.
5. **Parçalama:** `siniflandirici.py` → `dummyjson_api.py` → `isleyici.py` → `ozet.py` / `main.py` → testler.
   - Sınıflandırıcı yazılırken fark edildi: "İçeriğinde **alkol var mı**" cümlesindeki "var mı" stok sorusu sanılacaktı. Kalıp ürün adına bağlandı ve testi eklendi.
   - Tasarım kararı: "sipariş yok" ile "sipariş başkasına ait" durumlarında müşteriye **aynı metin** gidiyor. Farklı metin gitseydi, biri numara deneyerek hangi siparişlerin var olduğunu öğrenebilirdi.
6. **İlk çalıştırma (canlı API) → 15 taslak tek tek okundu.** Bulunan kusurlar düzeltildi:
   - Notlarda cümle arası nokta eksikti.
   - #12'nin gerekçesi yanlış yazıyordu ("bilinen kalıp yok").
   - #13'teki "alkol" sorusu genel "içerik" olarak geçiyordu.
   - Kargo SSS taslağında sistemin bilmediği bir süreç **uydurulmuştu** ("takip bilgisi iletilir"). Cümle kaldırıldı.
7. **Testler:** `python -m unittest discover` önce "NO TESTS RAN", sonra "No such file" verdi.
   - **Kök neden:** Masaüstü uygulamasının geçici çalışma klasörü arka planda çok daha uzun bir sanal yola (`…\Packages\Claude_…\LocalCache\…`) yönlendiriliyordu ve test dosyalarının yolu 260 karakteri aşıyordu.
   - **Çözüm:** Proje `C:\Users\erdog\Nurederm_Case_Dogukan_Erdogan` klasörüne taşındı. **29 testin hepsi geçti.**
8. **Testin kendisini test etme:** Hepsi ilk seferde geçince sipariş sahipliği kontrolü bilerek devre dışı bırakıldı (`ayni_musteri` her zaman True döndü). **5 test kırmızıya döndü.** Yani sızıntı testleri gerçekten koruma sağlıyor.
9. Küçük commit'lerle GitHub'a gönderildi.

---

## Oturum 2 — bağımsız inceleme

İlk sürüm 11:50'de bitti. Teslimden önce, önceki konuşmayı bilmeyen **yeni bir Claude Code oturumu** açıp işi baştan inceletip eksiklerini tamamlattım. İnceleme iki bölümü birlikte kapsadığı için bu prompt [B-n8n.md](B-n8n.md) dosyasında da var.

## Prompt 5 · ≈11:54 (Oturum 2'nin ilk promptu)

```
erdinc beyden case geldi ben de baska bir sohbette sana yaptirdim suan ama emin degilim nasil olcak diye suan case repomda githubda https://github.com/erdogandogukan/Nurederm_Case_Dogukan_Erdogan  . Mangolabdaki gibi case imin cok iyi olmasini istiyorum ilk 5 te olmam lazim anlayacagin.
Eger eksik veya fazlalik bir sey goruyorsan duzeltelim cok profosyonel olmasi lazim. Buyuk ihtimal caseleri elleriyle kontrol etmeyebilirler yapay zekaya case i mi atip puanlatirlar gibi. Cok profosyonel olmasi istiyorum anlayacagin. Bir de mesela neyi bitiremedin diye bolum acmis onlari yapabiliyorsak yapalim readme yi de duzenleyelim eger turkce olmasini uygun goruyorsan turkce kalsin ama dedigim gibi en iyi olsun
```

## Claude Code'un Oturum 2'de Bölüm A için yaptıkları (özet süreç günlüğü)

1. **Brief'e göre baştan denetim:** Case e-postası ve `case-brief.md` yeniden okundu. README'deki komutlar olduğu gibi çalıştırıldı: `main.py`, 29 birim testi, B'nin 9 Node testi ve `workflow.json` doğrulayıcısı. Hepsi geçti. Kod satır satır okundu.
2. **Denetlenmemiş bir iddia bulundu:** README, "kalıplara uymayan yeni bir ifade `diger` + devret'e düşer (güvenli taraf)" diyordu, ama bu hiç ölçülmemişti. Farklı yazımlarla (Türkçe karaktersiz, İngilizce, çok niyetli, belirti adı geçmeyen) **50 mesajlık etiketli bir geliştirme seti** yazıldı ve kurallara dokunmadan ölçüldü.
   - **Sonuç: 37/50 (%74) ve 18 hassas mesajın 6'sı otomatik cevaplanıyordu.** Örnek: "Kremi sürdükten sonra yüzümde kabarcıklar çıktı" → *urun-sorusu*. Mesajlar kalıplara uymuyor değildi, *yanlış* kalıba uyuyordu (ürün adı geçiyordu). Yani README'deki cümle yanlıştı.
   - Bu ilk ölçüm, **kurallar değişmeden önce** commit'lendi (`2b481da`). Aynı commit'e 24 mesajlık, henüz çalıştırılmamış bir **test seti** de kondu.
3. **Hata:** Kural değişikliklerini topluca uygulayan ilk Python betiği, düz (raw olmayan) string kullandığı için `\w` ve `\b` kaçış karakterlerini bozdu. Betikteki `assert` eşleşmenin bulunamadığını yakaladı ve dosyaya hiçbir şey yazılmadı. Değişiklikler tek tek yapıldı.
4. **Düzeltmeler, tek tek ezber yerine genel kurallar olarak yapıldı** (`485fd82`): *"…dan/den sonra" + vücut bölgesi* → kullanım sonrası şikâyet; kaçan şikâyet/belirti kalıpları; "bedava" tek başına spam değil; soru olmayan genel "ürün" bahsi ürün sorusu değil. Geliştirme seti 50/50 oldu (görülmüş set, iyimser). **Orijinal 15 mesajın `talepler.json` çıktısı değişmedi** (diff boş). 6 yeni test eklendi.
5. **Test seti bir kez çalıştırıldı:** 18/24 (%75). 12 hassas mesajın 11'i insana gidiyor, 1'i otomatik cevaplanıyor ("Şişe kargoda patlamış, her yer krem olmuş" → *urun-sorusu*). Bu tek açık için genel bir kural, ölçümden **sonra** eklendi (`343f6b3`): soru olmayan cümle otomatik ürün cevabı almaz. Bunun ölçümden sonra yapıldığı README'de açıkça yazıyor. Kalan 6 yanlış konunun hepsi `diger` + devret ile insana gidiyor; test setine göre kural yazılmadı.
6. **Mutasyon testi tekrarlandı:** `ayni_musteri` her zaman `True` döndürecek şekilde bozuldu → 5 test kırmızı. Dosya geri alındı.
7. **Teslim e-postası taslağı:** Repo linkinin çıplak link yerine `google.com/url?q=…` yönlendirmesi olarak yazıldığı görüldü. Taslak düzeltildi. E-postayı kontrol edip kendim gönderiyorum.

---

## Oturum 1'e dönüş — ikinci oturumun değişikliklerinin kontrolü

İkinci oturumun commit'lerini, ilk sürümü yapan oturuma geri verip kontrol ettirdim. İstek iki bölümü birlikte kapsıyor. Bu yüzden promptlar [B-n8n.md](B-n8n.md) dosyasında da var.

## Prompt 6 · ≈12:18

```
senin yaptigin repoyu baska bir claude oturumuna verdim bazi eksikliklerini buldu ve duzeltti repoyu tekrar kontrol eder misin sence yerinde duzeltmeler mi veya senin de eksik gordugun seyler var mi
```

## Prompt 7 · ≈12:27 (çalışma sürerken yazdım)

```
sakin gonderme maili
```

## Claude Code'un bu kontrolde yaptıkları (özet süreç günlüğü)

1. **Değişiklikleri tek tek okudu ve yeniden çalıştırdı:** 38 test (önce 36), geliştirme ve test seti ölçümleri, 15 mesajın çıktısı. Raporlanan sayılar aynı çıktı ve `talepler.json` değişmemişti.
2. **Yeni kuralın bedelini denedi:** "kullanım sonrası şikâyet" kuralı (`sonra` + vücut kelimesi) 10 masum sorunun **6'sını** yüksek öncelikli sağlık şikâyeti sayıyordu.
   - Örnek: "Sipariş verdikten sonra elime ne zaman ulaşır?" (teslimat deyimi). Diğerleri: "kargo yüzünden" (sebep), "yüz kremi" ve "saç maskesi" (ürün adı).
   - Ölçüm setlerinde bu tür masum cümle yoktu. Geliştirme setindeki %100, kuralların o sete göre ayarlanmasının sonucuydu.
3. **Düzeltme:** Vücut kelimesi birinci şahıs iyelik ekine bağlandı ("yüzüm", "cildimde", "saçlarım"). Bu kurala bağlı iki test seti mesajı (t01, t02) hâlâ yakalanıyor. Masum 6 sorunun hiçbiri alarm vermiyor. İki setin sonuçları ve 15 mesajın çıktısı değişmedi. `YanlisAlarm` testleri eklendi (36 → 38).
   - Kendi test beklentilerimden biri yanlıştı: "Sipariş verdikten sonra elime ne zaman ulaşır?" sipariş sorusu olarak değil `diger` + devret olarak sınıflanıyor. Bu güvenli taraf olduğu için beklenti "sağlık şikâyeti değil" olarak düzeltildi.
   - Mutasyon testi tekrarlandı: sahiplik kontrolü kapatılınca yine 5 test kırmızı.
4. **Teslim e-postası:** Gmail'de iki taslak bulundu. Biri case konuşmasının içinde; diğeri benim ilk taslağım, güncellenirken konuşmadan kopmuştu. Ham MIME'da ikisinde de link **hâlâ** `google.com/url?q=…` yönlendirmesiydi; yani önceki "düzeltildi" notu tutmuyordu.
   - Deneme için fazla taslağa temiz bir link yazıldı. Gmail bağlantısı hem HTML'deki linki hem düz metindeki çıplak URL'yi yine yönlendirmeye çevirdi. Yani bu araçla temiz link yazılamıyor.
   - Fazla taslağın konusu "[SİLİN - GÖNDERMEYİN]" yapıldı (taslak silmek kalıcı olduğu için yapay zekâ yapmadı). Linki gönderimden önce Gmail'de elle yapıştırıyorum.
   - E-posta yapay zekâ tarafından gönderilmedi.
