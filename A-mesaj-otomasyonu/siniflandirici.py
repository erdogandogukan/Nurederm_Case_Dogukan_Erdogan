"""Müşteri mesajlarına konu atayan kural tabanlı sınıflandırıcı.

Neden kural tabanlı (LLM değil)?
- Case anahtarsız çalışmayı istiyor; bir LLM API'si anahtar gerektirirdi.
- Kurallar deterministik ve test edilebilir; her kararın gerekçesi
  (eşleşen ifade) `not` alanına yazılabiliyor, temsilci neden o konunun
  seçildiğini görebiliyor.

Öncelik sırası — bir mesaj birden fazla kurala uyarsa ilk eşleşen kazanır:
    istenmeyen-etki > iade-sikayet > spam (diger) > siparis-durumu > fiyat > urun-sorusu > diger
Sağlık ve şikâyet sinyalleri başka bir konunun altında kaybolmasın diye
hassas konular en başta. Kazanmayan ama eşleşen konular `ikincil_konular`
olarak saklanır (örn. hem fiyat hem sipariş soran mesaj).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

KONULAR = ("urun-sorusu", "fiyat", "siparis-durumu", "iade-sikayet", "istenmeyen-etki", "diger")
HASSAS_KONULAR = ("iade-sikayet", "istenmeyen-etki")

_TR_KATLAMA = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "â": "a", "î": "i", "û": "u", "̇": "",
})


def normalize(metin: str) -> str:
    """Türkçeye uygun küçük harfe çevirir ve Türkçe karakterleri ASCII'ye katlar.

    Müşteriler Türkçe karakter kullanmadan da yazabildiği için ('sikayet',
    'siparisim') kurallar katlanmış metin üzerinde çalışır.
    """
    metin = metin.replace("I", "ı").replace("İ", "i").lower()
    metin = metin.translate(_TR_KATLAMA)
    return re.sub(r"\s+", " ", metin).strip()


def _derle(desenler: list[str]) -> list[re.Pattern]:
    return [re.compile(d) for d in desenler]


# --- Hassas konular -------------------------------------------------------

ISTENMEYEN_ETKI = _derle([
    r"\byan(di|iyor|ma|ik|mis)\b", r"\byak(ti|iyor|ma)\b", r"\bkizar", r"\bkasin",
    r"\balerji", r"\btahris", r"\bdokuntu", r"\bsis(ti|lik|me|kinlik)\b",
    r"\begzama", r"\bekzama", r"\breaksiyon", r"\birritasyon",
    r"\bsivilce (yapti|cikardi|cikti)", r"\bleke (yapti|birakti)", r"\bacidi\b",
    r"\b(burn\w*|rash|itch\w*|allerg\w*|irritat\w*|swell\w*|redness|hives)\b",
    # Değerlendirme setinde kaçan belirtiler (bkz. degerlendirme/):
    r"\bkabar", r"\bpullan", r"\bsoyul", r"\baci(yor|ma|mak)\b", r"\bbatma\b|\bbati(yor|di)\b",
    r"\bkasinti", r"\bkizarik", r"\bsac\w*\s+(\w+\s+)?dokul",
])

# Yapısal kural: "...dan/den sonra" + vücut bölgesi → kullanım sonrası şikâyet. Belirti kelimesi
# listede olmasa da mesaj insana gider. Yanlış pozitifi ("kremi yüzüme sürdükten sonra ne kadar
# beklemeliyim?") de insana gider: hata güvenli tarafta kalır, tersi değil.
KULLANIM_SONRASI = re.compile(r"\w+(dan|den|tan|ten)\s+sonra|\bsonra\b|\bafter (using|applying)\b")
VUCUT = re.compile(r"\b(yuz|cilt|goz|dudak|sac|deri|vucud|boyn|boyun|kafa|elim|ellerim|"
                   r"face|skin|eyes?|lips?|hair)\w*")

IADE_SIKAYET = _derle([
    r"\biade", r"\bsikayet", r"\bgeri (gonder|odeme|iade)", r"\bdegisim\b", r"\bdegistir",
    r"\bezik\b", r"\bkirik\b", r"\bhasarli\b", r"\bbozuk\b", r"\byirtik\b", r"\bakmis\b",
    r"\byanlis urun", r"\beksik (urun|geldi|gonder)", r"\bmemnun degil", r"\brezalet",
    r"\biptal",
    # Değerlendirme setinde kaçan şikâyet kalıpları:
    r"\bparam\w* geri", r"\bgeri istiyorum", r"\bpara iade", r"\bise yaramadi",
    r"\byanlis (urun|renk|beden|numara|siparis|ton)", r"\bkiril(mis|di)", r"\byirtil",
    r"\bmemnun (degil|kalmadi)", r"\bberbat", r"\bcevap (yok|vermiyor|alamiyorum)",
    r"\b(refund\w*|return\w*|complain\w*|damaged|broken|wrong item|cancel\w*)\b",
])

# --- Spam -----------------------------------------------------------------

SPAM = _derle([
    r"\b(bit\.ly|tinyurl\.com|goo\.gl|cutt\.ly|t\.co)/", r"\btakipci", r"\bfollower",
    r"\bbegeni (satin|kas)", r"\bkripto", r"\bbahis\b",
])
# "bedava" spam listesinden çıkarıldı: "2 alana 1 bedava kampanyanız geçerli mi?" gerçek bir müşteri
# sorusu. Spam'i bağlantı ve takipçi kalıpları belirliyor.

# --- Sipariş --------------------------------------------------------------

# Sipariş numarası yalnızca açık bir bağlamla alınır: "12 numaralı sipariş",
# "sipariş no: 12", "order #3". Böylece "Tonik 200 ml" gibi sayılar sipariş
# numarası sanılmaz.
SIPARIS_NO = _derle([
    r"(\d{1,9})\s*(?:numarali|nolu|no'?lu|no\.?)\s*siparis",
    r"siparis\w*\s*(?:(?:no|numarasi|numaram|kodu)\s*[:#.]?|[:#])\s*(\d{1,9})\b",
    r"\border\s*(?:(?:no\.?|number|num)\s*[:#]?|[:#])\s*(\d{1,9})\b",
])
DIYEZ_NO = re.compile(r"#\s*(\d{1,9})\b")

# Kişisel sipariş referansı: "siparişim", "kargom", "my order"...
# Genel soru ("Siparişler hangi kargoyla gidiyor?") sipariş durumu sayılmaz.
SIPARIS_KISISEL = _derle([
    r"\bsiparis(im|imin|imi|ime|imde|imiz|imizin)\b", r"\bkargo(m|mu|mun)\b",
    r"\bpaketim", r"\belime (ulasmadi|gecmedi)", r"\bteslim (alamadim|edilmedi)",
    r"\bgelmedi\b", r"\bverdigim siparis", r"\bsiparis ne zaman", r"\b(siparis|kargo) takip",
    r"\b(my order|where is my|track my|tracking)\b",
])

# --- Fiyat ----------------------------------------------------------------

FIYAT = _derle([
    r"\bfiyat", r"\bne kadar\b(?! (sure|zaman|bekle|gun))", r"\bkac (tl|lira|para)\b", r"\bkac(a|tan)\b",
    r"\bucret", r"\bindirim", r"\bkampanya", r"\bkupon", r"\bpromosyon",
    r"\b(price\w*|how much|cost\w*|discount\w*|coupon\w*)\b",
])

# --- Ürün sorusu ----------------------------------------------------------

# (desen, görünen ad, DummyJSON'da denenecek İngilizce arama terimleri)
# Sıra önemli: "retinol serum" genel "serum"dan önce yakalanmalı.
URUN_TERIMLERI: list[tuple[re.Pattern, str, tuple[str, ...]]] = [
    (re.compile(p), ad, terimler) for p, ad, terimler in [
        (r"gunes krem", "güneş kremi", ("sunscreen", "sunblock")),
        (r"nemlendirici", "nemlendirici krem", ("moisturizer", "lotion")),
        (r"retinol", "retinol serum", ("retinol",)),
        (r"\bc vitamin|vitamin c\b", "C vitamini serumu", ("vitamin c",)),
        (r"\btonik", "tonik", ("toner", "tonic")),
        (r"\bserum", "serum", ("serum",)),
        (r"\bmaske", "maske", ("mask",)),
        (r"\blosyon", "losyon", ("lotion",)),
        (r"\bruj\b", "ruj", ("lipstick",)),
        (r"\bmaskara|\brimel", "maskara", ("mascara",)),
        (r"\bsabun", "sabun", ("soap",)),
        (r"\bkrem", "krem", ("cream",)),
    ]
]

URUN_SORU_BASLIKLARI: list[tuple[re.Pattern, str]] = [
    (re.compile(p), baslik) for p, baslik in [
        # "alkol var mı" stok sorusu değildir; "var mı" yalnızca ürün adıyla birlikteyse stok sayılır.
        (r"\b(serum|krem|tonik|urun|maske|losyon|sabun|ruj)\w* var mi\b|\bstok|\bin stock\b", "stok durumu"),
        (r"cilt tip|kuru cilt|yagli cilt|karma cilt|hassas cilt|ciltte kullan|cilde uygun", "cilt tipine uygunluk"),
        (r"\b\d+\s*ml\b|\bml mi\b|\bgram\b|\bhacim", "hacim"),
        (r"\balkol", "alkol içeriği"),
        (r"\bparaben", "paraben içeriği"),
        (r"icerig|icerik|\bparfum", "içerik"),
        (r"hayvan|test edil|\bvegan\b|cruelty", "hayvan deneyi politikası"),
        (r"nasil kullan|kullanim", "kullanım şekli"),
    ]
]

URUN_GENEL = _derle([r"\burun(ler|un|unuz|leriniz)?\b", r"\bingredient", r"\bskin type"])

# Genel "ürün" kelimesi ancak mesaj bir soruysa ürün sorusu sayılır:
# "Teşekkürler, ürünler çok güzel" bir soru değil.
SORU = re.compile(r"\?|\bm(i|u)(sin|siniz|dir|yim|yiz)?\b|\b(nasil|hangi|neden|nerede|ne zaman|kac)\b|"
                  r"^(is|are|do|does|can|could|what|which|how)\b")

# --- Diğer (genel bilgi) --------------------------------------------------

KARGO_GENEL = re.compile(r"\bkargo\b|\bkargo (firma|sirket)|\bteslimat\b|\bshipping\b")


@dataclass
class Siniflandirma:
    konu: str
    gerekce: list[str] = field(default_factory=list)       # eşleşen ifadeler
    ikincil_konular: list[str] = field(default_factory=list)
    siparis_nolari: list[int] = field(default_factory=list)
    urun: tuple[str, tuple[str, ...]] | None = None         # (görünen ad, arama terimleri)
    urun_basliklari: list[str] = field(default_factory=list)
    spam: bool = False
    genel_kargo: bool = False
    dil: str = "tr"


def _eslesenler(desenler: list[re.Pattern], metin: str) -> list[str]:
    bulunan = []
    for desen in desenler:
        m = desen.search(metin)
        if m:
            bulunan.append(m.group(0).strip())
    return bulunan


def siparis_nolari_bul(normal_metin: str, kisisel: bool = False) -> list[int]:
    """Metinden sipariş numaralarını (tekrarsız, geçiş sırasıyla) çıkarır.

    '#3' gibi yalın diyez yalnızca metinde kişisel sipariş referansı varsa
    sayılır; aksi halde "%100" ya da "#1 ürün" gibi ifadeler yanlış alarm verir.
    """
    nolar: list[int] = []
    desenler = list(SIPARIS_NO) + ([DIYEZ_NO] if kisisel else [])
    for desen in desenler:
        for m in desen.finditer(normal_metin):
            no = int(m.group(1))
            if no not in nolar:
                nolar.append(no)
    return nolar


_EN_KELIMELER = {
    "hi", "hello", "where", "is", "my", "the", "order", "it", "has", "been", "a", "week",
    "please", "how", "much", "what", "when", "can", "you", "i", "your", "do", "does", "not",
    "yet", "still", "thanks", "thank", "have", "of", "to", "and", "for",
}


def dil_tespit(metin: str) -> str:
    """Çok basit dil tespiti: Türkçe karakter varsa 'tr', İngilizce kelime oranı yüksekse 'en'."""
    if re.search(r"[çğıöşüÇĞİÖŞÜ]", metin):
        return "tr"
    kelimeler = re.findall(r"[a-z]+", metin.lower())
    if not kelimeler:
        return "tr"
    oran = sum(k in _EN_KELIMELER for k in kelimeler) / len(kelimeler)
    return "en" if oran >= 0.4 else "tr"


def siniflandir(mesaj: str) -> Siniflandirma:
    metin = normalize(mesaj or "")
    dil = dil_tespit(mesaj or "")

    istenmeyen = _eslesenler(ISTENMEYEN_ETKI, metin)
    if not istenmeyen:
        sonra, vucut = KULLANIM_SONRASI.search(metin), VUCUT.search(metin)
        if sonra and vucut:
            istenmeyen = [f"kullanım sonrası şikâyet: '{sonra.group(0)}' + '{vucut.group(0)}'"]
    iade = _eslesenler(IADE_SIKAYET, metin)
    spam = _eslesenler(SPAM, metin)
    kisisel = _eslesenler(SIPARIS_KISISEL, metin)
    nolar = siparis_nolari_bul(metin, kisisel=bool(kisisel))
    fiyat = _eslesenler(FIYAT, metin)

    urun = None
    for desen, ad, terimler in URUN_TERIMLERI:
        if desen.search(metin):
            urun = (ad, terimler)
            break
    basliklar = [b for d, b in URUN_SORU_BASLIKLARI if d.search(metin)]
    if "içerik" in basliklar and any(b.endswith(" içeriği") for b in basliklar):
        basliklar.remove("içerik")  # "alkol içeriği" varken genel "içerik" tekrar olur
    urun_genel = _eslesenler(URUN_GENEL, metin) if SORU.search(metin) else []
    urun_sinyali = ([urun[0]] if urun else []) + basliklar + urun_genel

    siparis_sinyali = kisisel + [f"sipariş no {n}" for n in nolar]

    # Öncelik sırasıyla aday konular; ilki ana konu olur.
    adaylar: list[tuple[str, list[str]]] = []
    if istenmeyen:
        adaylar.append(("istenmeyen-etki", istenmeyen))
    if iade:
        adaylar.append(("iade-sikayet", iade))
    if spam and not adaylar:
        return Siniflandirma(konu="diger", gerekce=spam, spam=True, dil=dil)
    if siparis_sinyali:
        adaylar.append(("siparis-durumu", siparis_sinyali))
    if fiyat:
        adaylar.append(("fiyat", fiyat))
    if urun_sinyali:
        adaylar.append(("urun-sorusu", urun_sinyali))

    if not adaylar:
        genel_kargo = bool(KARGO_GENEL.search(metin))
        return Siniflandirma(
            konu="diger",
            gerekce=["kargo (genel soru; kişisel sipariş referansı/numarası yok)"] if genel_kargo
            else ["bilinen bir konu kalıbı yok"],
            genel_kargo=genel_kargo,
            dil=dil,
        )

    konu, gerekce = adaylar[0]
    return Siniflandirma(
        konu=konu,
        gerekce=gerekce,
        ikincil_konular=[k for k, _ in adaylar[1:]],
        siparis_nolari=nolar,
        urun=urun,
        urun_basliklari=basliklar,
        dil=dil,
    )
