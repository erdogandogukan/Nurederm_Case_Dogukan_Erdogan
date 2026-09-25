"""Konu bazında sayılar ve devir sayısı: terminal çıktısı + tek sayfalık HTML özet."""
from __future__ import annotations

import html
from collections import Counter
from datetime import datetime

from siniflandirici import KONULAR

KONU_ETIKET = {
    "siparis-durumu": "Sipariş durumu",
    "fiyat": "Fiyat",
    "urun-sorusu": "Ürün sorusu",
    "iade-sikayet": "İade / şikâyet",
    "istenmeyen-etki": "İstenmeyen etki",
    "diger": "Diğer",
}
# Özet tablosunda konuların görünme sırası: önce aksiyon gerektirenler.
KONU_SIRASI = ("istenmeyen-etki", "iade-sikayet", "siparis-durumu", "fiyat", "urun-sorusu", "diger")
assert set(KONU_SIRASI) == set(KONULAR)


def sayimlar(talepler) -> tuple[Counter, Counter]:
    konu = Counter(t.konu for t in talepler)
    devir = Counter(t.konu for t in talepler if t.devret)
    return konu, devir


def terminal_ozeti(talepler) -> str:
    konu, devir = sayimlar(talepler)
    cizgi = "─" * 44
    satirlar = [
        f"MÜŞTERİ MESAJLARI — İŞ LİSTESİ ÖZETİ ({len(talepler)} mesaj)",
        cizgi,
        f"{'Konu':<18}{'Adet':>8}{'Devredilen':>14}",
        cizgi,
    ]
    for k in KONU_SIRASI:
        satirlar.append(f"{k:<18}{konu.get(k, 0):>8}{devir.get(k, 0):>14}")
    satirlar += [
        cizgi,
        f"{'TOPLAM':<18}{len(talepler):>8}{sum(devir.values()):>14}",
        "",
        f"İnsana devredilecek: {sum(devir.values())} mesaj → "
        + ", ".join(f"#{t.id} ({t.konu})" for t in talepler if t.devret),
        f"Otomatik taslak hazır (devir yok): {sum(1 for t in talepler if not t.devret and t.cevap_taslagi)}",
        f"Yanıtlanmayacak (spam): {sum(1 for t in talepler if t.cevap_taslagi is None)}",
        "",
        f"{'ID':>3}  {'Kanal':<10}{'Müşt.':>6}  {'Konu':<16}{'Devret':<8}Öncelik",
    ]
    for t in talepler:
        satirlar.append(
            f"{t.id!s:>3}  {t.kanal:<10}{t.musteri_id!s:>6}  {t.konu:<16}{'EVET' if t.devret else '-':<8}{t.oncelik}"
        )
    return "\n".join(satirlar)


def _e(metin) -> str:
    return html.escape("" if metin is None else str(metin))


def html_ozeti(talepler, olusturma: datetime) -> str:
    konu, devir = sayimlar(talepler)
    toplam = len(talepler) or 1
    devir_toplam = sum(devir.values())
    taslak_hazir = sum(1 for t in talepler if not t.devret and t.cevap_taslagi)
    spam = sum(1 for t in talepler if t.cevap_taslagi is None)

    konu_satirlari = []
    for k in KONU_SIRASI:
        adet = konu.get(k, 0)
        konu_satirlari.append(
            f'<tr><td><span class="etiket k-{k}">{_e(KONU_ETIKET[k])}</span></td>'
            f'<td class="sayi">{adet}</td>'
            f'<td class="cubuk"><span style="width:{adet / toplam * 100:.1f}%"></span></td>'
            f'<td class="sayi">{devir.get(k, 0)}</td></tr>'
        )

    kartlar = []
    for t in talepler:
        rozet = '<span class="rozet devret">Temsilciye devret</span>' if t.devret else \
                '<span class="rozet otomatik">Taslak hazır</span>' if t.cevap_taslagi else \
                '<span class="rozet yok">Yanıtlanmayacak</span>'
        if t.oncelik == "yüksek":
            rozet += ' <span class="rozet acil">Öncelik: yüksek</span>'
        taslak = (f'<div class="taslak">{_e(t.cevap_taslagi)}</div>' if t.cevap_taslagi
                  else '<div class="taslak bos">— cevap üretilmedi —</div>')
        kartlar.append(f"""
      <article class="talep{' devir' if t.devret else ''}">
        <header>
          <span class="no">#{_e(t.id)}</span>
          <span class="etiket k-{_e(t.konu)}">{_e(KONU_ETIKET.get(t.konu, t.konu))}</span>
          {rozet}
          <span class="meta">{_e(t.kanal)} · müşteri {_e(t.musteri_id)}</span>
        </header>
        <p class="mesaj">“{_e(t.mesaj)}”</p>
        {taslak}
        <p class="not"><b>Not:</b> {_e(t.not_)}</p>
      </article>""")

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mesaj İş Listesi Özeti</title>
<style>
  :root {{
    --bg: #f6f7f9; --kart: #ffffff; --metin: #1c2330; --soluk: #5b6576; --cizgi: #e3e6eb;
    --vurgu: #3b5bdb; --devir: #c92a2a; --devir-bg: #fff0f0; --ok: #2b8a3e; --ok-bg: #ebfbee;
    --uyari: #e8590c; --taslak-bg: #f1f3f5;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #12151b; --kart: #1b2029; --metin: #e6e9ef; --soluk: #9aa3b2; --cizgi: #2c3340;
      --vurgu: #748ffc; --devir: #ff8787; --devir-bg: #2a1b1e; --ok: #69db7c; --ok-bg: #16261b;
      --uyari: #ffa94d; --taslak-bg: #232a35;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--metin);
         font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 1000px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 17px; margin: 32px 0 12px; }}
  .alt {{ color: var(--soluk); margin: 0 0 20px; }}
  .kpi {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
  .kpi div {{ background: var(--kart); border: 1px solid var(--cizgi); border-radius: 10px; padding: 14px 16px; }}
  .kpi b {{ display: block; font-size: 28px; }}
  .kpi span {{ color: var(--soluk); font-size: 13px; }}
  .kpi .kirmizi b {{ color: var(--devir); }} .kpi .yesil b {{ color: var(--ok); }}
  table {{ width: 100%; border-collapse: collapse; background: var(--kart); border: 1px solid var(--cizgi);
          border-radius: 10px; overflow: hidden; }}
  th, td {{ padding: 9px 12px; border-bottom: 1px solid var(--cizgi); text-align: left; }}
  th {{ font-size: 13px; color: var(--soluk); font-weight: 600; }}
  td.sayi {{ text-align: right; font-variant-numeric: tabular-nums; width: 90px; }}
  td.cubuk span {{ display: block; height: 10px; border-radius: 5px; background: var(--vurgu); min-width: 2px; }}
  tfoot td {{ font-weight: 700; border-bottom: 0; }}
  .etiket {{ display: inline-block; font-size: 12.5px; font-weight: 600; padding: 2px 9px; border-radius: 999px;
            background: var(--taslak-bg); }}
  .k-istenmeyen-etki {{ color: var(--devir); }} .k-iade-sikayet {{ color: var(--uyari); }}
  .k-siparis-durumu {{ color: var(--vurgu); }}
  .talep {{ background: var(--kart); border: 1px solid var(--cizgi); border-left: 4px solid var(--ok);
           border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; }}
  .talep.devir {{ border-left-color: var(--devir); }}
  .talep header {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
  .no {{ font-weight: 700; }}
  .meta {{ margin-left: auto; color: var(--soluk); font-size: 13px; }}
  .rozet {{ font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }}
  .rozet.devret {{ background: var(--devir-bg); color: var(--devir); }}
  .rozet.otomatik {{ background: var(--ok-bg); color: var(--ok); }}
  .rozet.yok {{ background: var(--taslak-bg); color: var(--soluk); }}
  .rozet.acil {{ background: var(--devir); color: #fff; }}
  .mesaj {{ margin: 10px 0 8px; font-style: italic; }}
  .taslak {{ white-space: pre-line; background: var(--taslak-bg); border-radius: 8px; padding: 10px 12px; }}
  .taslak.bos {{ color: var(--soluk); }}
  .not {{ color: var(--soluk); font-size: 13px; margin: 8px 0 0; }}
</style>
</head>
<body>
<main>
  <h1>Müşteri Mesajları — İş Listesi Özeti</h1>
  <p class="alt">{len(talepler)} mesaj işlendi · oluşturulma: {olusturma:%d.%m.%Y %H:%M} · kaynak: mesajlar.json + DummyJSON API</p>

  <section class="kpi">
    <div><b>{len(talepler)}</b><span>Toplam mesaj</span></div>
    <div class="kirmizi"><b>{devir_toplam}</b><span>İnsana devredilecek</span></div>
    <div class="yesil"><b>{taslak_hazir}</b><span>Otomatik taslak hazır</span></div>
    <div><b>{spam}</b><span>Yanıtlanmayacak (spam)</span></div>
  </section>

  <h2>Konu bazında</h2>
  <table>
    <thead><tr><th>Konu</th><th class="sayi">Adet</th><th>Dağılım</th><th class="sayi">Devredilen</th></tr></thead>
    <tbody>{''.join(konu_satirlari)}</tbody>
    <tfoot><tr><td>Toplam</td><td class="sayi">{len(talepler)}</td><td></td><td class="sayi">{devir_toplam}</td></tr></tfoot>
  </table>

  <h2>Talepler</h2>
  {''.join(kartlar)}
</main>
</body>
</html>
"""
