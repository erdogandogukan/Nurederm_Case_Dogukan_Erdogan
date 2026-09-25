"""Sınıflandırıcıyı etiketli mesajlarla ölçer (API'ye gitmez).

Kullanım (A-mesaj-otomasyonu klasöründen):
    python degerlendirme/degerlendir.py                              # geliştirme seti
    python degerlendirme/degerlendir.py degerlendirme/test_seti.json # ayrı tutulan test seti

Asıl ölçüt doğruluk değil, **hassas mesaj kaçırma**: iade/şikâyet ya da istenmeyen etki
içeren bir mesajın insana gitmeden otomatik cevaplanması. Sınıflandırıcı bir mesajı hiçbir
kurala uyduramazsa `diger` + devret'e düşer; bu yanlış konu olsa da güvenli taraftır.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from siniflandirici import HASSAS_KONULAR, KONULAR, siniflandir  # noqa: E402


def insana_gider_mi(s) -> bool:
    """isleyici.py ile aynı mantık: hassas konu ya da hiçbir kurala uymayan mesaj devredilir."""
    if s.konu in HASSAS_KONULAR:
        return True
    return s.konu == "diger" and not s.spam and not s.genel_kargo


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    yol = Path(argv[0]) if argv else Path(__file__).resolve().parent / "gelistirme_seti.json"
    ornekler = json.loads(yol.read_text(encoding="utf-8"))

    dogru = 0
    sinif_toplam: Counter = Counter()
    sinif_dogru: Counter = Counter()
    hatalar = []
    hassas_toplam = hassas_yakalanan = hassas_insana = 0
    tehlikeli = []

    for o in ornekler:
        s = siniflandir(o["mesaj"])
        beklenen = o["beklenen"]
        sinif_toplam[beklenen] += 1
        if s.konu == beklenen:
            dogru += 1
            sinif_dogru[beklenen] += 1
        else:
            hatalar.append((o["id"], beklenen, s.konu, o["mesaj"]))
        if beklenen in HASSAS_KONULAR:
            hassas_toplam += 1
            hassas_yakalanan += s.konu in HASSAS_KONULAR
            if insana_gider_mi(s):
                hassas_insana += 1
            else:
                tehlikeli.append((o["id"], s.konu, o["mesaj"]))

    n = len(ornekler)
    print(f"Set: {yol.name} · {n} mesaj")
    print(f"Doğruluk: {dogru}/{n} = %{100 * dogru / n:.0f}")
    print(f"Hassas mesaj → hassas konu: {hassas_yakalanan}/{hassas_toplam}")
    print(f"Hassas mesaj → insana gidiyor (hassas konu ya da 'diger'+devret): {hassas_insana}/{hassas_toplam}")
    print(f"TEHLİKELİ (hassas mesaj otomatik cevaplanıyor): {len(tehlikeli)}")
    for i, konu, mesaj in tehlikeli:
        print(f"   {i}: → {konu:15} {mesaj}")
    print("\nKonu bazında:")
    for k in KONULAR:
        if sinif_toplam[k]:
            print(f"   {k:16} {sinif_dogru[k]}/{sinif_toplam[k]}")
    print(f"\nYanlış sınıflananlar ({len(hatalar)}):")
    for i, beklenen, bulunan, mesaj in hatalar:
        print(f"   {i}: beklenen {beklenen:15} bulunan {bulunan:15} {mesaj}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
