"""İş kuralları: sınıflandırılmış mesajı temsilci için bir talebe dönüştürür.

Kurallar (case brief'inden):
1. Her mesaja tek konu.
2. iade-sikayet ve istenmeyen-etki → devret=True; ürün önerisi/teşhis içeren cevap YOK,
   yalnızca sabit bir devir bildirimi.
3. siparis-durumu → /carts/{id}; userId ≠ musteri_id ise sipariş bilgisi VERİLMEZ, devret=True.
   Sipariş yoksa düzgün bir uyarı mesajı.

Ek kararlar (README'de gerekçeleriyle):
- Sipariş sahipliği "fail-closed": userId ya da musteri_id eksik/bozuksa eşleşme yok sayılır.
- Başka müşteriye ait siparişin hiçbir alanı `siparis_sorgula` fonksiyonundan dışarı çıkmaz.
- "Bulunamadı" ve "başkasına ait" durumlarında müşteriye giden metin aynıdır; böylece numara
  deneyerek başkasının siparişinin var olup olmadığı anlaşılamaz (fark yalnızca iç notta).
- Otomasyonun bilmediği işletme bilgisi (kargo firması vb.) uydurulmaz: [YER TUTUCU] bırakılır.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dummyjson_api import KOZMETIK_KATEGORILER, ApiHatasi
from siniflandirici import HASSAS_KONULAR, Siniflandirma, normalize, siniflandir


@dataclass
class Talep:
    id: object
    konu: str
    devret: bool
    cevap_taslagi: str | None
    not_: str
    # Aşağıdakiler talepler.json'a yazılmaz; özet sayfası için tutulur.
    kanal: str = ""
    musteri_id: object = None
    mesaj: str = ""
    oncelik: str = "normal"
    devir_nedeni: str = ""   # özet sayfasında devirleri nedenine göre gruplamak için

    def json_ciktisi(self) -> dict:
        return {
            "id": self.id,
            "konu": self.konu,
            "devret": self.devret,
            "cevap_taslagi": self.cevap_taslagi,
            "not": self.not_,
        }


@dataclass
class SiparisSonucu:
    no: int
    durum: str                     # "bulundu" | "yetkisiz" | "bulunamadi" | "hata"
    urunler: list[tuple[str, int]] = field(default_factory=list)
    toplam: float | None = None
    hata: str = ""


# --- Metin şablonları -----------------------------------------------------

SELAM = {"tr": "Merhaba,", "en": "Hi,"}
KAPANIS = {"tr": "İyi günler dileriz.", "en": "Have a nice day!"}

DEVIR_METNI = {
    "istenmeyen-etki": {
        "tr": "Yaşadığınız durum için çok üzgünüz. Mesajınızı uzman müşteri temsilcimize ilettik; "
              "en kısa sürede sizinle iletişime geçecek.",
        "en": "We are very sorry to hear this. We have forwarded your message to a specialist customer "
              "representative, who will contact you as soon as possible.",
    },
    "iade-sikayet": {
        "tr": "Yaşadığınız sorun için üzgünüz. Talebinizi müşteri temsilcimize ilettik; "
              "en kısa sürede sizinle iletişime geçecek.",
        "en": "We are sorry for the trouble. We have forwarded your request to a customer representative, "
              "who will contact you as soon as possible.",
    },
}

TEMSILCI_NOTU = {
    "istenmeyen-etki": "ÖNCELİK: YÜKSEK (sağlık şikâyeti). Temsilci için: ürün adı, seri/lot no ve fotoğraf "
                       "istenmeli; ciddi istenmeyen etki şüphesinde kozmetovijilans (TİTCK bildirimi) süreci "
                       "değerlendirilmeli.",
    "iade-sikayet": "Temsilci için: sipariş numarası ve hasar fotoğrafı istenip iade/değişim süreci başlatılmalı.",
}


def para(tutar: float | None, dil: str) -> str:
    if tutar is None:
        return "?"
    if dil == "en":
        return f"${tutar:,.2f}"
    metin = f"{tutar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{metin} $"


def _urun_listesi(urunler: list[tuple[str, int]], dil: str) -> str:
    if dil == "en":
        return ", ".join(f"{ad} (x{adet})" for ad, adet in urunler)
    return ", ".join(f"{ad} ({adet} adet)" for ad, adet in urunler)


def _taslak(dil: str, cumleler: list[str]) -> str:
    return "\n".join([SELAM[dil], " ".join(cumleler), KAPANIS[dil]])


# --- Sipariş sorgusu (güvenlik kritik kısım) ------------------------------

def ayni_musteri(sahip, musteri_id) -> bool:
    """Fail-closed karşılaştırma: herhangi bir değer eksik ya da sayı değilse eşleşme yok."""
    if sahip is None or musteri_id is None or isinstance(sahip, bool) or isinstance(musteri_id, bool):
        return False
    try:
        return int(sahip) == int(musteri_id)
    except (TypeError, ValueError):
        return False


def siparis_sorgula(api, siparis_no: int, musteri_id) -> SiparisSonucu:
    """Siparişi çeker; yalnızca mesajı yazan müşteriye aitse içeriğini döndürür."""
    try:
        sepet = api.sepet_getir(siparis_no)
    except ApiHatasi as e:
        return SiparisSonucu(siparis_no, "hata", hata=str(e))
    if sepet is None:
        return SiparisSonucu(siparis_no, "bulunamadi")
    if not ayni_musteri(sepet.get("userId"), musteri_id):
        # Başka müşterinin siparişi: ürün, tutar ya da sahip bilgisi dışarı taşınmaz.
        return SiparisSonucu(siparis_no, "yetkisiz")
    urunler = [(str(p.get("title", "?")), int(p.get("quantity", 0))) for p in sepet.get("products", [])]
    return SiparisSonucu(siparis_no, "bulundu", urunler=urunler, toplam=sepet.get("total"))


def _siparis_cumlesi(r: SiparisSonucu, dil: str) -> str:
    if r.durum == "bulundu":
        if dil == "en":
            return (f"We checked your order #{r.no}. Items: {_urun_listesi(r.urunler, dil)}. "
                    f"Order total: {para(r.toplam, dil)}.")
        # Kargo durumu API'de yok; taslak tutamayacağı bir söz ("ayrıca bildireceğiz") vermez.
        return (f"{r.no} numaralı siparişinizi kontrol ettik. Siparişinizdeki ürünler: "
                f"{_urun_listesi(r.urunler, dil)}. Toplam tutar: {para(r.toplam, dil)}.")
    if r.durum in ("yetkisiz", "bulunamadi"):
        # Bilerek aynı metin: sipariş numarası tahminiyle bilgi sızmasın.
        if dil == "en":
            return (f"We couldn't find a record matching your account for order #{r.no}. Please double-check "
                    f"the order number and write to us again; we have also forwarded your request to a "
                    f"customer representative, who will contact you if needed.")
        return (f"{r.no} numaralı sipariş için hesabınızla eşleşen bir kayıt bulamadık. Sipariş numaranızı "
                f"kontrol edip tekrar yazabilirsiniz; talebinizi ayrıca müşteri temsilcimize ilettik, "
                f"gerekirse sizinle iletişime geçecek.")
    if dil == "en":
        return ("We are unable to check your order right now. We have forwarded your request to a customer "
                "representative, who will get back to you shortly.")
    return ("Sipariş bilginizi şu anda kontrol edemiyoruz. Talebinizi müşteri temsilcimize ilettik; "
            "en kısa sürede size dönüş yapılacak.")


def _siparis_notu(r: SiparisSonucu) -> str:
    return {
        "bulundu": f"Sipariş #{r.no}: bulundu, sahibi mesajı yazan müşteri (userId = musteri_id) → "
                   f"{len(r.urunler)} ürün ve toplam tutar paylaşıldı. API'de kargo/teslimat durumu alanı yok; "
                   f"temsilci kargo bilgisini ekleyebilir.",
        "yetkisiz": f"GÜVENLİK: Sipariş #{r.no} başka bir müşteriye ait (userId ≠ musteri_id) → sipariş "
                    f"bilgisi paylaşılmadı, temsilciye devredildi.",
        "bulunamadi": f"Sipariş #{r.no}: API 'not found' döndü. Müşteriden numarayı teyit etmesi istendi; "
                      f"temsilci müşterinin kayıtlı siparişlerini kontrol etmeli.",
        "hata": f"Sipariş #{r.no}: API'ye ulaşılamadı ({r.hata}) → temsilciye devredildi.",
    }[r.durum]


# --- Ürün / fiyat (bonus: /products/search) ------------------------------

def katalogda_ara(api, terimler: tuple[str, ...]) -> tuple[list[dict], str]:
    """İngilizce terimlerle arar; yalnızca kozmetik kategorisinde ve başlığında terim geçenleri alır.

    Test API'si genel bir mağaza: 'cream' araması 'Ice Cream' (groceries) ve açıklamasında
    'creamy' geçen 'Red Lipstick' döndürüyor. Bu yüzden kategori + başlık filtresi var.
    """
    denenenler = []
    for terim in terimler:
        try:
            sonuclar = api.urun_ara(terim)
        except ApiHatasi as e:
            return [], f"ürün araması yapılamadı ({e})"
        uygun = [
            p for p in sonuclar
            if p.get("category") in KOZMETIK_KATEGORILER and terim.lower() in str(p.get("title", "")).lower()
        ]
        denenenler.append(f"'{terim}' → {len(sonuclar)} sonuç, {len(uygun)} uygun")
        if uygun:
            return uygun[:3], "; ".join(denenenler)
    return [], "; ".join(denenenler)


def _katalog_listesi(urunler: list[dict], dil: str) -> str:
    return "; ".join(f"{p.get('title')} — {para(p.get('price'), dil)}" for p in urunler)


def _fiyat_listesi(api) -> tuple[list[dict], str]:
    urunler: list[dict] = []
    try:
        for kategori in ("skin-care", "beauty"):
            urunler += api.kategori_urunleri(kategori)
    except ApiHatasi as e:
        return [], f"fiyat listesi alınamadı ({e})"
    return urunler, f"fiyat listesi: skin-care + beauty kategorilerinden {len(urunler)} ürün"


def _buyuk_harf(metin: str) -> str:
    return metin[:1].upper() + metin[1:]


NEDEN_HASSAS = "hassas konu"
NEDEN_GUVENLIK = "sipariş doğrulanamadı"
NEDEN_EKSIK_BILGI = "sistemde olmayan bilgi — temsilci tamamlamalı"
NEDEN_BELIRSIZ = "sorun anlatımı / konu belirsiz"


def urun_cumleleri(api, s: Siniflandirma, konu: str, metin: str, dil: str,
                   urun_arama: bool = True) -> tuple[list[str], list[str], bool]:
    """fiyat / urun-sorusu için cevap cümleleri, iç notlar ve "temsilci tamamlamalı mı?" bilgisi.

    Taslak sistemde olmayan bir bilgi için temsilci/uzman dönüşü vaat ediyorsa üçüncü değer True olur
    ve talep devredilir: verilen sözün bir sahibi olmalı (harici incelemede bulunan tutarsızlık).
    """
    cumleler: list[str] = []
    notlar: list[str] = []
    takip = False
    urun_ad = s.urun[0] if s.urun else None
    katalog: list[dict] = []
    if urun_arama and s.urun:
        katalog, iz = katalogda_ara(api, s.urun[1])
        notlar.append(f"Ürün araması ({urun_ad}): {iz}.")

    if dil == "en":
        # Veri setinde İngilizce ürün/fiyat sorusu yok; kısa bir genel karşılık yeterli.
        cumleler.append("Thanks for your question. A customer representative will share the details shortly.")
        if katalog:
            cumleler.append(f"The closest match we found in our system: {_katalog_listesi(katalog, dil)}.")
        return cumleler, notlar, True

    normal = normalize(metin)
    if konu == "fiyat":
        if "liste" in normal or (not urun_ad and urun_arama):
            liste, iz = _fiyat_listesi(api) if urun_arama else ([], "")
            if iz:
                notlar.append(iz.capitalize() + ".")
            if liste:
                cumleler.append("Sistemimizdeki cilt bakımı ve makyaj ürünlerinin fiyatları: "
                                f"{_katalog_listesi(liste, dil)}.")
        if katalog:
            # Test API'si genel bir mağaza: sonuç "en yakın ürün" olarak sunulur ve müşteriye doğru
            # ürün olup olmadığı sorulur; "kataloğumuzdaki ürün" diye kesin konuşulmaz.
            cumleler.append(f"{_buyuk_harf(urun_ad)} için sistemimizde bulduğumuz en yakın ürün: "
                            f"{_katalog_listesi(katalog, dil)}. Aradığınız ürün bu değilse ürün adını "
                            f"paylaşırsanız hemen kontrol edelim.")
        elif urun_ad:
            cumleler.append(f"{_buyuk_harf(urun_ad)} fiyatıyla ilgili güncel bilgiyi müşteri temsilcimiz "
                            f"kısa süre içinde iletecek.")
            takip = True
        if any(k in normal for k in ("indirim", "kampanya", "kupon", "kod")):
            cumleler.append("İndirim kodu ve güncel kampanyalar hakkındaki bilgiyi müşteri temsilcimiz "
                            "ayrıca paylaşacak.")
            notlar.append("İndirim kodu sistemde yok; uydurulmadı, temsilci eklemeli.")
            takip = True
        if not cumleler:
            cumleler.append("Fiyat bilgisini müşteri temsilcimiz kısa süre içinde iletecek.")
            takip = True
        return cumleler, notlar, takip

    # urun-sorusu: içerik / cilt uygunluğu / politika bilgisi sistemde yok → her zaman uzman tamamlar.
    basliklar = " ve ".join(s.urun_basliklari) if s.urun_basliklari else "ürün"
    if urun_ad:
        cumleler.append(f"{_buyuk_harf(urun_ad)} ile ilgili {basliklar} konusundaki detaylı bilgiyi ürün "
                        f"uzmanımız kısa süre içinde iletecek.")
    else:
        cumleler.append(f"{_buyuk_harf(basliklar)} konusundaki detaylı bilgiyi ürün uzmanımız kısa süre "
                        f"içinde iletecek.")
    if katalog:
        cumleler.append(f"Sistemimizde bulduğumuz ilgili ürün(ler): {_katalog_listesi(katalog, dil)}.")
    notlar.append("Ürün içeriği/cilt uygunluğu doğrulanmış kaynaktan (ürün uzmanı) yanıtlanmalı; "
                  "otomasyon ürün bilgisi uydurmaz.")
    return cumleler, notlar, True


# --- Ana akış -------------------------------------------------------------

def mesaj_isle(mesaj: dict, api, urun_arama: bool = True) -> Talep:
    mid = mesaj.get("id")
    kanal = mesaj.get("kanal", "?")
    musteri = mesaj.get("musteri_id")
    metin = mesaj.get("mesaj") or ""

    s = siniflandir(metin)
    dil = s.dil
    notlar = [f"Kanal: {kanal} · Müşteri: {musteri} · Gerekçe: " + ", ".join(f"'{g}'" for g in s.gerekce) + "."]
    if s.ikincil_konular:
        notlar.append("İkincil konu(lar): " + ", ".join(s.ikincil_konular) + ".")
    if dil == "en":
        notlar.append("Mesaj İngilizce → taslak İngilizce.")

    def talep(devret: bool, taslak: str | None, oncelik: str = "normal", neden: str = "") -> Talep:
        if devret:
            notlar.append(f"Devir nedeni: {neden}.")
        return Talep(mid, s.konu, devret, taslak, " ".join(notlar), kanal=kanal, musteri_id=musteri,
                     mesaj=metin, oncelik=oncelik, devir_nedeni=neden if devret else "")

    # 1) Hassas konular: yalnızca devir.
    if s.konu in HASSAS_KONULAR:
        notlar.append(TEMSILCI_NOTU[s.konu])
        notlar.append("Otomatik cevapta ürün önerisi/teşhis yok; yalnızca sabit devir bildirimi.")
        oncelik = "yüksek" if s.konu == "istenmeyen-etki" else "normal"
        return talep(True, _taslak(dil, [DEVIR_METNI[s.konu][dil]]), oncelik, NEDEN_HASSAS)

    # 2) Sipariş durumu: sahiplik kontrolü.
    if s.konu == "siparis-durumu":
        if not s.siparis_nolari:
            notlar.append("Mesajda sipariş numarası yok → numara istendi.")
            soru = ("Could you share your order number so we can check your order?" if dil == "en" else
                    "Siparişinizi kontrol edebilmemiz için sipariş numaranızı paylaşır mısınız?")
            return talep(False, _taslak(dil, [soru]))
        if musteri is None:
            notlar.append("Mesajda musteri_id yok → sipariş sahipliği doğrulanamaz, API'ye gidilmedi.")
            return talep(True, _taslak(dil, [_siparis_cumlesi(SiparisSonucu(s.siparis_nolari[0], "hata"), dil)]),
                         neden=NEDEN_GUVENLIK)

        sonuclar = [siparis_sorgula(api, no, musteri) for no in s.siparis_nolari]
        devret = any(r.durum != "bulundu" for r in sonuclar)
        neden = NEDEN_GUVENLIK if devret else ""
        cumleler = [_siparis_cumlesi(r, dil) for r in sonuclar]
        notlar += [_siparis_notu(r) for r in sonuclar]

        # İkincil fiyat/ürün sorusu varsa ve devir gerekmiyorsa onu da yanıtla.
        ikincil = next((k for k in s.ikincil_konular if k in ("fiyat", "urun-sorusu")), None)
        if ikincil and not devret:
            ek, ek_not, takip = urun_cumleleri(api, s, ikincil, metin, dil)
            cumleler += ek
            notlar += ek_not
            if takip:
                devret, neden = True, NEDEN_EKSIK_BILGI
        elif ikincil:
            notlar.append(f"İkincil {ikincil} sorusu devir nedeniyle otomatik yanıtlanmadı.")
        if s.yardim_istegi and not devret:
            devret, neden = True, NEDEN_BELIRSIZ
        return talep(devret, _taslak(dil, cumleler), neden=neden)

    # 3) Fiyat / ürün sorusu (+ bonus katalog araması).
    if s.konu in ("fiyat", "urun-sorusu"):
        if s.yardim_istegi:
            # "…ne yapmalıyım?" bir sorun anlatımıdır: ürün bilgisi ya da öneri verilmez.
            notlar.append("Yardım isteyen ifade ('ne yapmalıyım' vb.) → olası sorun; otomatik ürün/fiyat "
                          "cevabı verilmedi.")
            return talep(True, _taslak(dil, [DEVIR_METNI["iade-sikayet"][dil]]), neden=NEDEN_BELIRSIZ)
        cumleler, ek_not, takip = urun_cumleleri(api, s, s.konu, metin, dil)
        notlar += ek_not
        return talep(takip, _taslak(dil, cumleler), neden=NEDEN_EKSIK_BILGI)

    # 4) Diğer.
    if s.spam:
        notlar.append("SPAM: kısaltılmış/şüpheli bağlantı içeriyor → yanıtlanmamalı, bağlantıya tıklanmamalı; "
                      "hesap engellenip raporlanabilir.")
        return talep(False, None, "düşük")
    if s.genel_kargo:
        notlar.append("Belirli bir siparişle ilgili değil, genel kargo sorusu (SSS). Kargo firması bilgisi "
                      "sistemde yok → göndermeden önce [KARGO FİRMASI] alanını doldurun.")
        return talep(True, _taslak(dil, [
            "Siparişlerimiz [KARGO FİRMASI] ile gönderilmektedir. Başka bir sorunuz olursa yardımcı olmaktan "
            "memnuniyet duyarız."]), neden=NEDEN_EKSIK_BILGI)
    notlar.append("Otomatik konu bulunamadı → temsilci değerlendirmeli.")
    return talep(True, _taslak(dil, [
        "Mesajınız için teşekkürler. Talebinizi müşteri temsilcimize ilettik; en kısa sürede dönüş yapılacak."]),
        neden=NEDEN_BELIRSIZ)


def mesajlari_isle(mesajlar: list[dict], api, urun_arama: bool = True) -> list[Talep]:
    return [mesaj_isle(m, api, urun_arama=urun_arama) for m in mesajlar]
