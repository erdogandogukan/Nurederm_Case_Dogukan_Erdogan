"""workflow.json'dan akis-semasi.svg üretir (düğüm konumları ve bağlantılar n8n'dekiyle aynı).

Çalıştırma (B-n8n klasöründe):  python araclar/sema_olustur.py
"""
from __future__ import annotations

import json
import textwrap
from html import escape
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
OLCEK, GEN, YUK, KENAR = 0.8, 160, 50, 40

RENK = {
    "scheduleTrigger": "#2b8a3e", "manualTrigger": "#2b8a3e", "set": "#495057",
    "httpRequest": "#1c7ed6", "code": "#7048e8", "if": "#e67700", "googleSheets": "#0b8043",
    "emailSend": "#d9480f", "splitOut": "#495057", "noOp": "#868e96", "stopAndError": "#c92a2a",
}
TUR_ADI = {
    "scheduleTrigger": "Schedule Trigger", "manualTrigger": "Manual Trigger", "set": "Set",
    "httpRequest": "HTTP Request", "code": "Code", "if": "IF", "googleSheets": "Google Sheets",
    "emailSend": "Send Email", "splitOut": "Split Out", "noOp": "No Op", "stopAndError": "Stop and Error",
}


def main() -> None:
    akis = json.loads((KOK / "workflow.json").read_text(encoding="utf-8"))
    dugumler = {n["name"]: n for n in akis["nodes"] if n["type"] != "n8n-nodes-base.stickyNote"}
    xs = [n["position"][0] for n in dugumler.values()]
    ys = [n["position"][1] for n in dugumler.values()]
    x0, y0 = min(xs), min(ys)

    def kutu(ad: str) -> tuple[float, float]:
        x, y = dugumler[ad]["position"]
        return KENAR + (x - x0) * OLCEK, KENAR + 50 + (y - y0) * OLCEK

    genislik = KENAR * 2 + (max(xs) - x0) * OLCEK + GEN
    yukseklik = KENAR * 2 + 50 + (max(ys) - y0) * OLCEK + YUK + 40

    parca = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {genislik:.0f} {yukseklik:.0f}" '
        f'font-family="Segoe UI, Arial, sans-serif">',
        f'<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{KENAR}" y="{KENAR + 4}" font-size="20" font-weight="700" fill="#1c2330">'
        f'{escape(akis["name"])}</text>',
        '<defs><marker id="ok" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#868e96"/></marker>'
        '<marker id="okk" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#c92a2a"/></marker></defs>',
    ]

    for kaynak, cikislar in akis["connections"].items():
        for cikis_no, hedefler in enumerate(cikislar["main"]):
            for h in hedefler:
                (x1, y1), (x2, y2) = kutu(kaynak), kutu(h["node"])
                x1, y1, y2 = x1 + GEN, y1 + YUK / 2 + (8 if cikis_no else 0), y2 + YUK / 2
                # Kırmızı yalnızca hata dalı; IF'in normal "false" çıkışı gri kesikli.
                hata = h["node"].startswith(("Hata", "Akışı"))
                kesikli = hata or cikis_no == 1
                renk, isaret = ("#c92a2a", "okk") if hata else ("#868e96", "ok")
                dx = max(40, (x2 - x1) / 2)
                parca.append(
                    f'<path d="M{x1:.0f},{y1:.0f} C{x1 + dx:.0f},{y1:.0f} {x2 - dx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}" '
                    f'fill="none" stroke="{renk}" stroke-width="1.6"{" stroke-dasharray=\"5 4\"" if kesikli else ""} '
                    f'marker-end="url(#{isaret})"/>')
                if cikis_no == 1:
                    etiket = "false" if dugumler[kaynak]["type"].endswith(".if") else "hata çıkışı"
                    parca.append(f'<text x="{x1 + 6:.0f}" y="{y1 + 14:.0f}" font-size="10" fill="{renk}">'
                                 f'{etiket}</text>')

    for ad, n in dugumler.items():
        x, y = kutu(ad)
        tur = n["type"].split(".")[-1]
        renk = RENK.get(tur, "#495057")
        satirlar = textwrap.wrap(ad, 24)[:2]
        parca.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{GEN}" height="{YUK}" rx="8" fill="#ffffff" '
                     f'stroke="{renk}" stroke-width="2"/>')
        parca.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="6" height="{YUK}" rx="3" fill="{renk}"/>')
        for i, satir in enumerate(satirlar):
            parca.append(f'<text x="{x + 14:.0f}" y="{y + 18 + i * 14:.0f}" font-size="12" font-weight="600" '
                         f'fill="#1c2330">{escape(satir)}</text>')
        parca.append(f'<text x="{x + 14:.0f}" y="{y + YUK + 13:.0f}" font-size="10" fill="{renk}">'
                     f'{TUR_ADI.get(tur, tur)}</text>')

    parca.append(f'<text x="{KENAR}" y="{yukseklik - 14:.0f}" font-size="11" fill="#868e96">'
                 'Kesikli kırmızı: hata dalı · düğüm konumları workflow.json ile aynı · '
                 'araclar/sema_olustur.py ile üretildi</text>')
    parca.append("</svg>")
    (KOK / "akis-semasi.svg").write_text("\n".join(parca) + "\n", encoding="utf-8")
    print(f"akis-semasi.svg: {len(dugumler)} düğüm")


if __name__ == "__main__":
    main()
