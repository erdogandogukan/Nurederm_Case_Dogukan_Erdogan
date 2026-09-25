"""workflow.json ve hata-workflow.json dosyalarını üretir ve yapısal olarak doğrular.

Code düğümlerinin JavaScript'i kod/*.js dosyalarından okunur. Böylece n8n'e giden kod
ile test/kod-testi.mjs'de Node.js üzerinde test edilen kod birebir aynıdır.

Çalıştırma (B-n8n klasöründe):  python araclar/workflow_olustur.py
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
# n8n CLI içe aktarımı (import:workflow) workflow id'si olmadan başarısız oluyor
# ("NOT NULL constraint failed: workflow_entity.id"); arayüzden içe aktarmada da zararı yok.
ANA_AKIS_ID = "LaptopFiyatTakip"
HATA_AKISI_ID = "hataBildirimAkis"
SABLON_ADI = "Competitor Price Monitoring with Web Scraping, Google Sheets & Telegram"
SABLON_LINKI = ("https://n8n.io/workflows/4640-competitor-price-monitoring-with-web-scrapinggoogle-sheets"
                "-and-telegram/")


def kod(dosya: str) -> str:
    return (KOK / "kod" / dosya).read_text(encoding="utf-8")


def dugum_id(ad: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nurederm-case/{ad}"))


def dugum(ad: str, tur: str, surum: float, konum: tuple[int, int], parametreler: dict, **ayarlar) -> dict:
    return {"parameters": parametreler, "id": dugum_id(ad), "name": ad, "type": tur,
            "typeVersion": surum, "position": list(konum), **ayarlar}


def not_kagidi(ad: str, konum: tuple[int, int], genislik: int, yukseklik: int, icerik: str, renk: int = 7) -> dict:
    return dugum(ad, "n8n-nodes-base.stickyNote", 1, konum,
                 {"content": icerik, "width": genislik, "height": yukseklik, "color": renk})


def kosul(ad_ifadesi: str) -> dict:
    """IF v2.2: boolean alan true mu?"""
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
            "conditions": [{
                "id": dugum_id(ad_ifadesi),
                "leftValue": ad_ifadesi,
                "rightValue": "",
                "operator": {"type": "boolean", "operation": "true", "singleValue": True},
            }],
            "combinator": "and",
        },
        "options": {},
    }


def sheets(islem: str, sekme: str, **ek) -> dict:
    parametreler = {
        "operation": islem,
        "documentId": {"__rl": True, "value": "={{ $('Ayarlar').first().json.sheet_id }}", "mode": "id"},
        "sheetName": {"__rl": True, "value": sekme, "mode": "name"},
    }
    parametreler.update(ek)
    parametreler.setdefault("options", {})
    return parametreler


def eposta(konu: str, html: str) -> dict:
    return {
        "fromEmail": "={{ $('Ayarlar').first().json.gonderen_eposta }}",
        "toEmail": "={{ $('Ayarlar').first().json.bildirim_eposta }}",
        "subject": konu,
        "emailFormat": "html",
        "html": html,
        "options": {"appendAttribution": False},
    }


HTTP_BASLIK = {"parameters": [{"name": "User-Agent", "value": "n8n-fiyat-takip/1.0"}]}
TEKRAR_DENE = {"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000}


def ana_akis() -> dict:
    d = [
        dugum("Günlük Tetikleyici (09:00)", "n8n-nodes-base.scheduleTrigger", 1.2, (0, 300),
              {"rule": {"interval": [{"triggerAtHour": 9}]}}),
        # Test için: arayüzde "Execute workflow" ve CLI'da `n8n execute` bu tetikleyiciyle çalışır.
        dugum("Elle Çalıştır (test)", "n8n-nodes-base.manualTrigger", 1, (0, 480), {}),
        dugum("Ayarlar", "n8n-nodes-base.set", 3.4, (220, 300), {
            "assignments": {"assignments": [
                {"id": dugum_id("a1"), "name": "taban_url", "type": "string",
                 "value": "https://webscraper.io/test-sites/e-commerce/static/computers/laptops"},
                {"id": dugum_id("a2"), "name": "site_kok", "type": "string", "value": "https://webscraper.io"},
                {"id": dugum_id("a3"), "name": "max_sayfa", "type": "number", "value": 50},
                {"id": dugum_id("a4"), "name": "sheet_id", "type": "string", "value": "GOOGLE_SHEET_ID_BURAYA"},
                {"id": dugum_id("a5"), "name": "bildirim_eposta", "type": "string", "value": "ekip@ornek.com"},
                {"id": dugum_id("a6"), "name": "gonderen_eposta", "type": "string", "value": "n8n@ornek.com"},
            ]},
            "options": {},
        }),
        # Site hiç açılmazsa hata çıkışı (ikinci çıkış) hata dalına gider.
        dugum("Sayfa 1'i Çek", "n8n-nodes-base.httpRequest", 4.2, (440, 300), {
            "url": "={{ $json.taban_url }}",
            "sendHeaders": True,
            "headerParameters": HTTP_BASLIK,
            "options": {"response": {"response": {"responseFormat": "text", "outputPropertyName": "html"}},
                        "timeout": 20000},
        }, onError="continueErrorOutput", **TEKRAR_DENE),
        dugum("Sayfa Listesini Oluştur", "n8n-nodes-base.code", 2, (660, 300),
              {"jsCode": kod("1-sayfa-listesi.js")}),
        # Her sayfa için bir istek; 500 ms arayla (siteye nazik ol). Hatalı sayfa akışı
        # durdurmaz, hata öğesi olarak "Ürünleri Ayrıştır"a gelir ve orada sayılır.
        dugum("Tüm Sayfaları Çek", "n8n-nodes-base.httpRequest", 4.2, (880, 300), {
            "url": "={{ $json.url }}",
            "sendHeaders": True,
            "headerParameters": HTTP_BASLIK,
            "options": {"batching": {"batch": {"batchSize": 1, "batchInterval": 500}},
                        "response": {"response": {"responseFormat": "text", "outputPropertyName": "html"}},
                        "timeout": 20000},
        }, onError="continueRegularOutput", **TEKRAR_DENE),
        dugum("Ürünleri Ayrıştır", "n8n-nodes-base.code", 2, (1100, 300),
              {"jsCode": kod("2-urunleri-ayristir.js")}),
        dugum("Tarama sağlıklı mı?", "n8n-nodes-base.if", 2.2, (1320, 300), kosul("={{ $json.saglikli }}")),
        # İlk çalışmada sekme boştur: "Always Output Data" olmadan 0 satır dönünce akış sessizce biterdi.
        dugum("Son Durumu Oku", "n8n-nodes-base.googleSheets", 4.5, (1540, 200),
              sheets("read", "son_durum"), alwaysOutputData=True, **TEKRAR_DENE),
        dugum("Değişiklikleri Bul", "n8n-nodes-base.code", 2, (1760, 200),
              {"jsCode": kod("3-degisiklikleri-bul.js")}),
        # Dallar yukarıdan aşağıya çalışır (executionOrder v1): önce bildirim, sonra tablolar.
        # E-posta başarısız olursa tablolar güncellenmez → ertesi gün değişiklik yeniden yakalanır.
        dugum("Bildirim gerekli mi?", "n8n-nodes-base.if", 2.2, (1980, 0), kosul("={{ $json.bildirim_gerekli }}")),
        dugum("Bildirim E-postasını Hazırla", "n8n-nodes-base.code", 2, (2200, -100),
              {"jsCode": kod("4-bildirim-epostasi.js")}),
        dugum("Değişiklik Bildirimi Gönder", "n8n-nodes-base.emailSend", 2.1, (2420, -100),
              eposta("={{ $json.konu }}", "={{ $json.html }}")),
        dugum("Değişiklik Yok", "n8n-nodes-base.noOp", 1, (2200, 100), {}),
        dugum("Geçmiş Satırlarını Ayır", "n8n-nodes-base.splitOut", 1, (1980, 260),
              {"fieldToSplitOut": "gecmis_satirlari", "options": {}}),
        dugum("Fiyat Geçmişine Ekle", "n8n-nodes-base.googleSheets", 4.5, (2200, 260),
              sheets("append", "fiyat_gecmisi", columns={
                  "mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []}),
              **TEKRAR_DENE),
        dugum("Son Durum Satırlarını Ayır", "n8n-nodes-base.splitOut", 1, (1980, 460),
              {"fieldToSplitOut": "son_durum_satirlari", "options": {}}),
        dugum("Son Durumu Güncelle", "n8n-nodes-base.googleSheets", 4.5, (2200, 460),
              sheets("appendOrUpdate", "son_durum", columns={
                  "mappingMode": "autoMapInputData", "value": {}, "matchingColumns": ["link"], "schema": []}),
              **TEKRAR_DENE),
        # --- Hata dalı ---
        dugum("Hata Mesajını Hazırla", "n8n-nodes-base.code", 2, (1540, 700),
              {"jsCode": kod("5-hata-mesaji.js")}),
        # E-posta da başarısız olsa akış yine "Stop and Error" ile hatalı bitsin.
        dugum("Hata Bildirimi Gönder", "n8n-nodes-base.emailSend", 2.1, (1760, 700),
              eposta("={{ $json.konu }}", "={{ $json.html }}"), onError="continueRegularOutput"),
        dugum("Akışı Hatayla Bitir", "n8n-nodes-base.stopAndError", 1, (1980, 700),
              {"errorMessage": "={{ $('Hata Mesajını Hazırla').first().json.hata_mesaji }}"}),
        # --- Açıklama notları ---
        not_kagidi("Not: Başlangıç şablonu", (-40, -240), 640, 260,
                   f"## Laptop fiyat takibi\nBaşlangıç şablonu: **{SABLON_ADI}** (#4640)\n{SABLON_LINKI}\n\n"
                   "Şablondan farklar: ürün URL listesi yerine kategori sayfalarını **?page=N ile tümüyle gezme**, "
                   "yeni/kaldırılan ürün tespiti, **hata dalı**, Telegram yerine e-posta, fiyat geçmişi + son durum "
                   "sekmeleri.\n\nKurulum: `Ayarlar` düğümünde sheet_id ve e-postaları doldurun; Google Sheets ve "
                   "SMTP kimlik bilgilerini bağlayın. Ayrıntı: akis-aciklama.md", 5),
        not_kagidi("Not: Tüm sayfalar", (400, 460), 700, 200,
                   "### 1–3 · Tüm sayfaları gez\nSayfa 1 çekilir → sayfalama çubuğundaki en büyük `page=N` son "
                   "sayfadır (bugün 20) → 1..N için istek (500 ms arayla, 3 deneme) → her ürün kartından ad, "
                   "**sayısal fiyat** (`$1,139.54` → 1139.54), yorum sayısı ve link çıkarılır."),
        not_kagidi("Not: Karşılaştırma", (1500, -240), 640, 200,
                   "### 4–5 · Tablo + değişiklik tespiti\n`son_durum` sekmesiyle karşılaştır (anahtar: ürün linki; "
                   "sitede 29 ürünün adı başka ürünle aynı). Yeni / fiyatı değişen / kaldırılan ürünler → e-posta. "
                   "Tüm ürünler tarih damgasıyla `fiyat_gecmisi`ne eklenir, `son_durum` güncellenir."),
        not_kagidi("Not: Hata dalı", (1500, 860), 700, 180,
                   "### Hata dalı\nSite açılmaz, bir sayfa alınamaz ya da hiç ürün çıkmazsa: hata e-postası → "
                   "**Stop and Error** ile yürütme *başarısız* biter. Yarım veriyle karşılaştırma yapılmaz "
                   "(yanlış 'kaldırıldı' alarmı olmasın).", 3),
    ]

    def b(hedef: str) -> dict:
        return {"node": hedef, "type": "main", "index": 0}

    baglantilar = {
        "Günlük Tetikleyici (09:00)": {"main": [[b("Ayarlar")]]},
        "Elle Çalıştır (test)": {"main": [[b("Ayarlar")]]},
        "Ayarlar": {"main": [[b("Sayfa 1'i Çek")]]},
        "Sayfa 1'i Çek": {"main": [[b("Sayfa Listesini Oluştur")], [b("Hata Mesajını Hazırla")]]},
        "Sayfa Listesini Oluştur": {"main": [[b("Tüm Sayfaları Çek")]]},
        "Tüm Sayfaları Çek": {"main": [[b("Ürünleri Ayrıştır")]]},
        "Ürünleri Ayrıştır": {"main": [[b("Tarama sağlıklı mı?")]]},
        "Tarama sağlıklı mı?": {"main": [[b("Son Durumu Oku")], [b("Hata Mesajını Hazırla")]]},
        "Son Durumu Oku": {"main": [[b("Değişiklikleri Bul")]]},
        "Değişiklikleri Bul": {"main": [[b("Bildirim gerekli mi?"), b("Geçmiş Satırlarını Ayır"),
                                         b("Son Durum Satırlarını Ayır")]]},
        "Bildirim gerekli mi?": {"main": [[b("Bildirim E-postasını Hazırla")], [b("Değişiklik Yok")]]},
        "Bildirim E-postasını Hazırla": {"main": [[b("Değişiklik Bildirimi Gönder")]]},
        "Geçmiş Satırlarını Ayır": {"main": [[b("Fiyat Geçmişine Ekle")]]},
        "Son Durum Satırlarını Ayır": {"main": [[b("Son Durumu Güncelle")]]},
        "Hata Mesajını Hazırla": {"main": [[b("Hata Bildirimi Gönder")]]},
        "Hata Bildirimi Gönder": {"main": [[b("Akışı Hatayla Bitir")]]},
    }
    return {
        "id": ANA_AKIS_ID,
        "name": "Laptop Fiyat Takibi — webscraper.io → Google Sheets + E-posta",
        "nodes": d,
        "connections": baglantilar,
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "timezone": "Europe/Istanbul",
            "saveDataErrorExecution": "all",
            "saveDataSuccessExecution": "all",
            # Beklenmeyen hatalarda hata-workflow.json çalışır (o da içe aktarılmış olmalı).
            "errorWorkflow": HATA_AKISI_ID,
        },
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": False},
    }


def hata_akisi() -> dict:
    """Beklenmeyen her hata (örn. Sheets kimlik bilgisi süresi doldu) için yedek bildirim akışı."""
    d = [
        dugum("Error Trigger", "n8n-nodes-base.errorTrigger", 1, (0, 0), {}),
        dugum("Hata E-postası", "n8n-nodes-base.emailSend", 2.1, (240, 0), {
            "fromEmail": "n8n@ornek.com",
            "toEmail": "ekip@ornek.com",
            "subject": "=[n8n HATA] {{ $json.workflow.name }}",
            "emailFormat": "html",
            "html": "=<p><b>Akış:</b> {{ $json.workflow.name }}</p><p><b>Düğüm:</b> "
                    "{{ $json.execution.lastNodeExecuted }}</p><p><b>Hata:</b> {{ $json.execution.error.message }}"
                    "</p><p><a href=\"{{ $json.execution.url }}\">Yürütmeyi aç</a></p>",
            "options": {"appendAttribution": False},
        }),
    ]
    return {
        "id": HATA_AKISI_ID,
        "name": "Hata Bildirimi (Error Workflow)",
        "nodes": d,
        "connections": {"Error Trigger": {"main": [[{"node": "Hata E-postası", "type": "main", "index": 0}]]}},
        "active": False,
        "settings": {"executionOrder": "v1", "timezone": "Europe/Istanbul"},
        "pinData": {},
    }


def dogrula(akis: dict) -> None:
    adlar = [n["name"] for n in akis["nodes"]]
    assert len(adlar) == len(set(adlar)), "düğüm adları benzersiz olmalı"
    idler = [n["id"] for n in akis["nodes"]]
    assert len(idler) == len(set(idler)), "düğüm id'leri benzersiz olmalı"
    for kaynak, cikislar in akis["connections"].items():
        assert kaynak in adlar, f"bağlantı kaynağı yok: {kaynak}"
        for cikis in cikislar["main"]:
            for hedef in cikis:
                assert hedef["node"] in adlar, f"bağlantı hedefi yok: {hedef['node']}"
    # $('Düğüm Adı') / $("Düğüm Adı") referansları gerçekten var olan düğümlere mi işaret ediyor?
    # (Adında kesme işareti olan düğüm, örn. "Sayfa 1'i Çek", çift tırnakla çağrılıyor.)
    import re

    def metinler(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for v in o.values():
                yield from metinler(v)
        elif isinstance(o, list):
            for v in o:
                yield from metinler(v)

    ham = "\n".join(metinler(akis["nodes"]))
    refler = re.findall(r"\$\('([^']+)'\)", ham) + re.findall(r'\$\("([^"]+)"\)', ham)
    if "$(" in ham:
        assert refler, "düğüm referansları okunamadı (doğrulayıcı bozuk olabilir)"
    for ref in set(refler):
        assert ref in adlar, f"var olmayan düğüme referans: {ref}"
    # Tetikleyici dışındaki her işlem düğümüne bir bağlantı girmeli (kopuk düğüm olmasın).
    hedefler = {h["node"] for c in akis["connections"].values() for cikis in c["main"] for h in cikis}
    for n in akis["nodes"]:
        if n["type"] in ("n8n-nodes-base.stickyNote", "n8n-nodes-base.scheduleTrigger",
                         "n8n-nodes-base.manualTrigger", "n8n-nodes-base.errorTrigger"):
            continue
        assert n["name"] in hedefler, f"kopuk düğüm: {n['name']}"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows konsolunda Türkçe karakterler bozulmasın
    for dosya, akis in (("workflow.json", ana_akis()), ("hata-workflow.json", hata_akisi())):
        dogrula(akis)
        (KOK / dosya).write_text(json.dumps(akis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        islem = [n for n in akis["nodes"] if n["type"] != "n8n-nodes-base.stickyNote"]
        print(f"{dosya}: {len(islem)} düğüm, {len(akis['connections'])} bağlantı kaynağı — doğrulandı")
