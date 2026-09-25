"""Müşteri mesajlarını işleyip temsilci için iş listesi üretir.

Kullanım:
    python main.py                       # mesajlar.json → talepler.json + ozet.html
    python main.py --urun-arama-kapali   # bonus ürün aramasını kapatır
    python main.py --girdi baska.json --cikti cikti.json --ozet ozet.html
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dummyjson_api import DummyJsonApi
from isleyici import mesajlari_isle
from ozet import html_ozeti, terminal_ozeti

KLASOR = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    # Windows konsolunda Türkçe karakterler bozulmasın.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Müşteri mesajı otomasyonu (Bölüm A)")
    parser.add_argument("--girdi", default=KLASOR / "mesajlar.json", type=Path)
    parser.add_argument("--cikti", default=KLASOR / "talepler.json", type=Path)
    parser.add_argument("--ozet", default=KLASOR / "ozet.html", type=Path)
    parser.add_argument("--urun-arama-kapali", action="store_true",
                        help="Bonus /products/search aramasını kapatır")
    args = parser.parse_args(argv)

    try:
        mesajlar = json.loads(args.girdi.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"HATA: girdi okunamadı ({args.girdi}): {e}", file=sys.stderr)
        return 1
    if not isinstance(mesajlar, list):
        print("HATA: girdi bir mesaj listesi olmalı.", file=sys.stderr)
        return 1

    talepler = mesajlari_isle(mesajlar, DummyJsonApi(), urun_arama=not args.urun_arama_kapali)

    args.cikti.write_text(
        json.dumps([t.json_ciktisi() for t in talepler], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.ozet.write_text(html_ozeti(talepler, datetime.now()), encoding="utf-8")

    print(terminal_ozeti(talepler))
    print(f"\nÇıktılar:\n  {args.cikti}\n  {args.ozet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
