import json
import sys
import unittest
from pathlib import Path

KLASOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KLASOR))

from siniflandirici import dil_tespit, normalize, siniflandir, siparis_nolari_bul  # noqa: E402

MESAJLAR = {m["id"]: m for m in json.loads((KLASOR / "mesajlar.json").read_text(encoding="utf-8"))}

# Elle etiketlenmiş beklenen konular (kararların gerekçesi README'de).
BEKLENEN = {
    1: "siparis-durumu", 2: "siparis-durumu", 3: "siparis-durumu", 4: "istenmeyen-etki",
    5: "iade-sikayet", 6: "siparis-durumu", 7: "diger", 8: "siparis-durumu", 9: "urun-sorusu",
    10: "fiyat", 11: "urun-sorusu", 12: "diger", 13: "urun-sorusu", 14: "fiyat", 15: "urun-sorusu",
}


class TumMesajlar(unittest.TestCase):
    def test_her_mesaj_beklenen_konuda(self):
        for mid, beklenen in BEKLENEN.items():
            with self.subTest(id=mid, mesaj=MESAJLAR[mid]["mesaj"]):
                self.assertEqual(siniflandir(MESAJLAR[mid]["mesaj"]).konu, beklenen)

    def test_siparis_numaralari(self):
        beklenen = {1: [12], 2: [5], 3: [9999], 6: [3], 8: [4]}
        for mid, nolar in beklenen.items():
            with self.subTest(id=mid):
                self.assertEqual(siniflandir(MESAJLAR[mid]["mesaj"]).siparis_nolari, nolar)

    def test_coklu_niyet_ikincil_konu_olarak_saklanir(self):
        s = siniflandir(MESAJLAR[8]["mesaj"])  # fiyat + sipariş
        self.assertEqual(s.konu, "siparis-durumu")
        self.assertIn("fiyat", s.ikincil_konular)

    def test_spam(self):
        s = siniflandir(MESAJLAR[7]["mesaj"])
        self.assertTrue(s.spam)
        self.assertEqual(s.konu, "diger")

    def test_genel_kargo_sorusu_siparis_durumu_degil(self):
        s = siniflandir(MESAJLAR[12]["mesaj"])
        self.assertEqual(s.konu, "diger")
        self.assertTrue(s.genel_kargo)
        self.assertEqual(s.siparis_nolari, [])


class Kenarlar(unittest.TestCase):
    def test_hacimdeki_sayi_siparis_numarasi_sanilmaz(self):
        s = siniflandir("Tonik 200 ml mi? İçeriğinde alkol var mı?")
        self.assertEqual(s.konu, "urun-sorusu")
        self.assertEqual(s.siparis_nolari, [])
        self.assertIn("alkol içeriği", s.urun_basliklari)
        self.assertNotIn("stok durumu", s.urun_basliklari)  # "alkol var mı" stok sorusu değil

    def test_siparis_numarasi_kaliplari(self):
        ornekler = {
            "12 numaralı siparişim nerede": [12],
            "sipariş no: 45 ne zaman gelir": [45],
            "siparişim #7 gelmedi": [7],
            "where is my order #3?": [3],
            "siparişim 2 gündür gelmedi": [],  # "2 gün" sipariş numarası değil
            "%100 organik takipçi": [],
        }
        for metin, beklenen in ornekler.items():
            with self.subTest(metin=metin):
                n = normalize(metin)
                self.assertEqual(siparis_nolari_bul(n, kisisel=True), beklenen)

    def test_turkce_karaktersiz_yazim(self):
        self.assertEqual(siniflandir("kutu ezik geldi urunu iade etmek istiyorum").konu, "iade-sikayet")
        self.assertEqual(siniflandir("kremi surdum yuzum yandi").konu, "istenmeyen-etki")
        self.assertEqual(siniflandir("SİPARİŞİM NEREDE? 12 NUMARALI SİPARİŞ").konu, "siparis-durumu")

    def test_saglik_sinyali_her_seyin_onunde(self):
        s = siniflandir("12 numaralı siparişimdeki kremi sürdüm, kaşıntı yaptı, iade etmek istiyorum")
        self.assertEqual(s.konu, "istenmeyen-etki")
        self.assertIn("iade-sikayet", s.ikincil_konular)

    def test_genel_siparis_sorusu_kisisel_degil(self):
        # Kişisel referans yoksa '#1' gibi ifadeler sipariş numarası sayılmaz.
        self.assertEqual(siparis_nolari_bul(normalize("en çok satan #1 serum hangisi"), kisisel=False), [])

    def test_dil_tespiti(self):
        self.assertEqual(dil_tespit(MESAJLAR[6]["mesaj"]), "en")
        self.assertEqual(dil_tespit(MESAJLAR[10]["mesaj"]), "tr")  # Türkçe karakter yok ama Türkçe


class DegerlendirmedenGelenler(unittest.TestCase):
    """degerlendirme/gelistirme_seti.json ilk ölçümünde kaçan mesajlar (bkz. README)."""

    def test_kullanim_sonrasi_sikayet_belirti_listede_olmasa_da_insana_gider(self):
        s = siniflandir("Kremi sürdükten sonra yüzümde küçük kabarcıklar çıktı, normal mi?")
        self.assertEqual(s.konu, "istenmeyen-etki")  # önce: urun-sorusu → otomatik cevap

    def test_sikayet_siparis_numarasindan_once_gelir(self):
        s = siniflandir("Yanlış renk ruj gönderilmiş, siparişim 45 numara")
        self.assertEqual(s.konu, "iade-sikayet")  # önce: siparis-durumu

    def test_para_iadesi_talebi(self):
        self.assertEqual(siniflandir("Paramı geri istiyorum, ürün hiç işe yaramadı").konu, "iade-sikayet")

    def test_bedava_kelimesi_tek_basina_spam_degil(self):
        s = siniflandir("2 alana 1 bedava kampanyanız hâlâ geçerli mi?")
        self.assertFalse(s.spam)
        self.assertEqual(s.konu, "fiyat")

    def test_soru_olmayan_urun_bahsi_urun_sorusu_degil(self):
        self.assertEqual(siniflandir("Teşekkürler, ürünler çok güzel 😊").konu, "diger")

    def test_soru_olmayan_urun_cumlesi_otomatik_cevaplanmaz(self):
        # Ayrı tutulan test setinde kaçan tek hassas mesaj (t08); düzeltme ölçümden SONRA yapıldı.
        s = siniflandir("Şişe kargoda patlamış, her yer krem olmuş")
        self.assertNotIn(s.konu, ("urun-sorusu", "fiyat"))

    def test_gelistirme_setinde_hicbir_hassas_mesaj_otomatik_cevaplanmaz(self):
        from siniflandirici import HASSAS_KONULAR
        yol = KLASOR / "degerlendirme" / "gelistirme_seti.json"
        for o in json.loads(yol.read_text(encoding="utf-8")):
            if o["beklenen"] in HASSAS_KONULAR:
                with self.subTest(id=o["id"], mesaj=o["mesaj"]):
                    self.assertIn(siniflandir(o["mesaj"]).konu, HASSAS_KONULAR)


if __name__ == "__main__":
    unittest.main()
