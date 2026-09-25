import json
import re
import sys
import unittest
from pathlib import Path

KLASOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KLASOR))

from dummyjson_api import ApiHatasi  # noqa: E402
from isleyici import DEVIR_METNI, ayni_musteri, mesaj_isle, mesajlari_isle  # noqa: E402
from siniflandirici import KONULAR  # noqa: E402

MESAJLAR = json.loads((KLASOR / "mesajlar.json").read_text(encoding="utf-8"))


def sepet(user_id, urunler, toplam):
    return {"id": 0, "userId": user_id, "total": toplam,
            "products": [{"title": t, "quantity": q} for t, q in urunler]}


# Gerçek DummyJSON verisinin (25.09.2026'da kontrol edildi) ağ gerektirmeyen kopyası.
GERCEK_SEPETLER = {
    12: sepet(12, [("Sportbike Motorcycle", 1), ("Rolex Submariner Watch", 2)], 37767.32),
    5: sepet(5, [("Samsung Galaxy Tab White", 4), ("Soft Drinks", 4), ("Powder Canister", 4)], 1467.88),
    3: sepet(3, [("iPhone 13 Pro", 1), ("Dior J'adore", 2)], 1794.85),
    4: sepet(4, [("Sports Sneakers Off White Red", 3), ("Dior J'adore", 4)], 689.93),
}


class SahteApi:
    """Ağa çıkmayan API; yapılan çağrıları kaydeder."""

    def __init__(self, sepetler=None, hata=False, arama=None):
        self.sepetler = sepetler or {}
        self.hata = hata
        self.arama = arama or {}
        self.cagrilar = []

    def sepet_getir(self, sepet_id):
        self.cagrilar.append(("sepet", sepet_id))
        if self.hata:
            raise ApiHatasi("bağlantı zaman aşımı")
        return self.sepetler.get(sepet_id)

    def urun_ara(self, sorgu, limit=10):
        self.cagrilar.append(("ara", sorgu))
        return self.arama.get(sorgu, [])

    def kategori_urunleri(self, kategori, limit=10):
        self.cagrilar.append(("kategori", kategori))
        return []


def mesaj(metin, musteri_id=7, mid=1):
    return {"id": mid, "kanal": "whatsapp", "musteri_id": musteri_id, "mesaj": metin}


def tum_cikti(talep) -> str:
    return json.dumps(talep.json_ciktisi(), ensure_ascii=False)


class SiparisGuvenligi(unittest.TestCase):
    def test_baska_musterinin_siparisi_hicbir_alana_sizmaz(self):
        api = SahteApi(GERCEK_SEPETLER)
        t = mesaj_isle(mesaj("Merhaba, 12 numaralı siparişim nerede?", musteri_id=7), api)
        self.assertTrue(t.devret)
        cikti = tum_cikti(t)
        for sizinti in ("Sportbike", "Rolex", "37767", "37.767", "userId 12", "müşteri 12"):
            self.assertNotIn(sizinti, cikti)
        self.assertIn("GÜVENLİK", t.not_)

    def test_kendi_siparisi_urun_ve_toplamla_yanitlanir(self):
        t = mesaj_isle(mesaj("5 numaralı siparişimin durumu nedir?", musteri_id=5), SahteApi(GERCEK_SEPETLER))
        self.assertFalse(t.devret)
        for beklenen in ("Samsung Galaxy Tab White (4 adet)", "Powder Canister", "1.467,88 $"):
            self.assertIn(beklenen, t.cevap_taslagi)

    def test_bulunamayan_siparis_duzgun_uyari_uretir(self):
        t = mesaj_isle(mesaj("9999 numaralı siparişim gelmedi", musteri_id=22), SahteApi(GERCEK_SEPETLER))
        self.assertIn("bulamadık", t.cevap_taslagi)
        self.assertIn("not found", t.not_)

    def test_bulunamadi_ile_baskasina_ait_ayni_metni_alir(self):
        # Numara deneyerek hangi siparişin var olduğu anlaşılamamalı.
        api = SahteApi(GERCEK_SEPETLER)
        yok = mesaj_isle(mesaj("9999 numaralı siparişim nerede?", musteri_id=7), api).cevap_taslagi
        baskasi = mesaj_isle(mesaj("12 numaralı siparişim nerede?", musteri_id=7), api).cevap_taslagi
        self.assertEqual(re.sub(r"\d+", "N", yok), re.sub(r"\d+", "N", baskasi))

    def test_api_hatasinda_cokmez_devreder(self):
        t = mesaj_isle(mesaj("12 numaralı siparişim nerede?"), SahteApi(hata=True))
        self.assertTrue(t.devret)
        self.assertIn("API'ye ulaşılamadı", t.not_)

    def test_userid_eksikse_fail_closed(self):
        api = SahteApi({8: {"products": [{"title": "Gizli Ürün", "quantity": 1}], "total": 10}})
        t = mesaj_isle(mesaj("8 numaralı siparişim nerede?", musteri_id=8), api)
        self.assertTrue(t.devret)
        self.assertNotIn("Gizli Ürün", tum_cikti(t))

    def test_musteri_id_yoksa_apiye_gidilmez(self):
        api = SahteApi(GERCEK_SEPETLER)
        t = mesaj_isle({"id": 1, "kanal": "whatsapp", "mesaj": "5 numaralı siparişim nerede?"}, api)
        self.assertTrue(t.devret)
        self.assertEqual(api.cagrilar, [])

    def test_sahiplik_karsilastirmasi(self):
        self.assertTrue(ayni_musteri(5, 5))
        self.assertTrue(ayni_musteri("5", 5))      # API string döndürse de doğru çalışır
        self.assertFalse(ayni_musteri(12, 7))
        self.assertFalse(ayni_musteri(None, 7))
        self.assertFalse(ayni_musteri(True, 1))    # bool, 1 sayılmaz
        self.assertFalse(ayni_musteri("abc", 7))

    def test_numarasiz_siparis_sorusunda_numara_istenir(self):
        api = SahteApi(GERCEK_SEPETLER)
        t = mesaj_isle(mesaj("Siparişim nerede?"), api)
        self.assertIn("sipariş numaranızı", t.cevap_taslagi)
        self.assertEqual(api.cagrilar, [])


class HassasKonular(unittest.TestCase):
    def test_hassas_konular_yalnizca_sabit_devir_metni_alir(self):
        for metin, konu in (("Serumu kullandım, yüzüm yandı ve kızardı. Ne yapmalıyım?", "istenmeyen-etki"),
                            ("Kutu ezik geldi, ürünü iade etmek istiyorum.", "iade-sikayet")):
            with self.subTest(konu=konu):
                api = SahteApi(GERCEK_SEPETLER)
                t = mesaj_isle(mesaj(metin), api)
                self.assertEqual(t.konu, konu)
                self.assertTrue(t.devret)
                self.assertIn(DEVIR_METNI[konu]["tr"], t.cevap_taslagi)
                self.assertEqual(api.cagrilar, [])  # ürün araması / öneri yok

    def test_istenmeyen_etki_yuksek_oncelikli(self):
        t = mesaj_isle(mesaj("Kremi sürdükten sonra kaşıntı ve kızarıklık oldu"), SahteApi())
        self.assertEqual(t.oncelik, "yüksek")


class UrunAramasi(unittest.TestCase):
    def test_urun_sorusunda_siparis_apisi_cagrilmaz(self):
        api = SahteApi(GERCEK_SEPETLER)
        mesaj_isle(mesaj("Tonik 200 ml mi? İçeriğinde alkol var mı?"), api)
        self.assertFalse([c for c in api.cagrilar if c[0] == "sepet"])

    def test_alakasiz_arama_sonuclari_elenir(self):
        # Gerçek API'de 'cream' → 'Ice Cream' (groceries) ve 'Red Lipstick' döndürüyor.
        api = SahteApi(arama={"cream": [
            {"title": "Ice Cream", "price": 5.49, "category": "groceries"},
            {"title": "Red Lipstick", "price": 12.99, "category": "beauty"},
        ]})
        t = mesaj_isle(mesaj("Krem ne kadar?"), api)
        self.assertNotIn("Ice Cream", t.cevap_taslagi)
        self.assertNotIn("Red Lipstick", t.cevap_taslagi)

    def test_uygun_arama_sonucu_taslaga_eklenir(self):
        api = SahteApi(arama={"lotion": [
            {"title": "Vaseline Men Body and Face Lotion", "price": 9.99, "category": "skin-care"}]})
        t = mesaj_isle(mesaj("Nemlendirici krem ne kadar?"), api)
        self.assertIn("Vaseline Men Body and Face Lotion — 9,99 $", t.cevap_taslagi)


class UctanUca(unittest.TestCase):
    def setUp(self):
        self.talepler = mesajlari_isle(MESAJLAR, SahteApi(GERCEK_SEPETLER))

    def test_cikti_semasi(self):
        for t in self.talepler:
            cikti = t.json_ciktisi()
            self.assertEqual(set(cikti), {"id", "konu", "devret", "cevap_taslagi", "not"})
            self.assertIn(cikti["konu"], KONULAR)
            self.assertIsInstance(cikti["devret"], bool)

    def test_devredilenler(self):
        self.assertEqual({t.id for t in self.talepler if t.devret}, {1, 3, 4, 5})

    def test_spam_yanitlanmaz(self):
        spam = next(t for t in self.talepler if t.id == 7)
        self.assertIsNone(spam.cevap_taslagi)

    def test_ingilizce_mesaja_ingilizce_taslak(self):
        t = next(t for t in self.talepler if t.id == 6)
        self.assertTrue(t.cevap_taslagi.startswith("Hi,"))
        self.assertIn("$1,794.85", t.cevap_taslagi)


if __name__ == "__main__":
    unittest.main()
