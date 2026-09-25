# Bölüm A — Claude Code'a yazdığım promptlar

**Araç:** Claude Code masaüstü uygulaması, model Claude Opus 5.5. Case'in iki bölümünü de **tek bir oturumda** yaptım. Bu yüzden ilk prompt iki dosyada da var.

**Kural:** Promptlar silinmeden, düzeltilmeden (yazım hataları dahil) ve sırasıyla aşağıda. Saatler yaklaşıktır.

**Neden `/export` çıktısı yok?** Oturum dökümünde Gmail aramasının ham sonuçları da var: case ile ilgisi olmayan başka e-postalarımın konu ve özetleri. Bu yüzden ham dökümü herkese açık depoya koymadım. Promptlarımı buraya birebir kopyaladım. Yapay zekânın yaptığı işleri ve karşılaştığı hataları da aşağıya özet olarak ekledim.

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
> **Cevabım:** `Gmail'de taslak oluştur` (teslim e-postasını kontrol edip kendim gönderdim)

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
