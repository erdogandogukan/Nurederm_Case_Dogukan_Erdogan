"""DummyJSON için küçük, bağımlılıksız (yalnızca standart kütüphane) API istemcisi.

- Zaman aşımı ve ağ / 5xx hatalarında sınırlı yeniden deneme var.
- "Bulunamadı" durumu hem HTTP 404'ten hem de gövdedeki
  `{"message": "... not found"}` kalıbından anlaşılır (case brief'i bu gövdeyi tarif ediyor).
- Ağ tamamen çökerse `ApiHatasi` fırlatılır; çağıran taraf mesajı temsilciye devreder.
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

KOZMETIK_KATEGORILER = {"beauty", "skin-care", "fragrances"}


class ApiHatasi(Exception):
    """API'ye ulaşılamadı ya da beklenmeyen bir yanıt döndü."""


class DummyJsonApi:
    def __init__(self, taban_url: str = "https://dummyjson.com", zaman_asimi: float = 10.0,
                 yeniden_deneme: int = 2, bekleme: float = 0.8):
        self.taban_url = taban_url.rstrip("/")
        self.zaman_asimi = zaman_asimi
        self.yeniden_deneme = yeniden_deneme
        self.bekleme = bekleme

    def _get(self, yol: str, parametreler: dict | None = None) -> tuple[int, dict]:
        url = self.taban_url + yol
        if parametreler:
            url += "?" + urllib.parse.urlencode(parametreler)
        istek = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "mesaj-otomasyonu/1.0 (case calismasi)",
        })
        son_hata: Exception | None = None
        for deneme in range(self.yeniden_deneme + 1):
            try:
                with urllib.request.urlopen(istek, timeout=self.zaman_asimi) as yanit:
                    return yanit.status, json.loads(yanit.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                govde = e.read().decode("utf-8", errors="replace")
                try:
                    veri = json.loads(govde)
                except ValueError:
                    veri = {"message": govde[:200]}
                if 500 <= e.code < 600 and deneme < self.yeniden_deneme:
                    son_hata = e
                    time.sleep(self.bekleme * (deneme + 1))
                    continue
                return e.code, veri
            except (urllib.error.URLError, socket.timeout, TimeoutError, ValueError) as e:
                son_hata = e
                if deneme < self.yeniden_deneme:
                    time.sleep(self.bekleme * (deneme + 1))
                    continue
        raise ApiHatasi(f"{url} isteği başarısız: {son_hata}")

    def sepet_getir(self, sepet_id: int) -> dict | None:
        """/carts/{id}. Sipariş yoksa None döner; diğer hatalarda ApiHatasi fırlatır."""
        durum, veri = self._get(f"/carts/{int(sepet_id)}")
        mesaj = str(veri.get("message", "")).lower() if isinstance(veri, dict) else ""
        if durum == 404 or "not found" in mesaj:
            return None
        if durum != 200 or not isinstance(veri, dict) or "products" not in veri:
            raise ApiHatasi(f"/carts/{sepet_id} beklenmeyen yanıt (HTTP {durum}): {str(veri)[:120]}")
        return veri

    def urun_ara(self, sorgu: str, limit: int = 10) -> list[dict]:
        """/products/search?q=... → [{id, title, price, category}, ...]"""
        durum, veri = self._get("/products/search", {
            "q": sorgu, "limit": limit, "select": "title,price,category",
        })
        if durum != 200 or not isinstance(veri, dict):
            raise ApiHatasi(f"/products/search?q={sorgu} beklenmeyen yanıt (HTTP {durum})")
        return veri.get("products", [])

    def kategori_urunleri(self, kategori: str, limit: int = 10) -> list[dict]:
        """/products/category/{kategori} → fiyat listesi talepleri için."""
        durum, veri = self._get(f"/products/category/{urllib.parse.quote(kategori)}", {
            "limit": limit, "select": "title,price,category",
        })
        if durum != 200 or not isinstance(veri, dict):
            raise ApiHatasi(f"/products/category/{kategori} beklenmeyen yanıt (HTTP {durum})")
        return veri.get("products", [])
