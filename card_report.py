"""HTMLレポートを生成する"""

import os
from datetime import datetime
from card_analyzer import CardPrice

TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ポケカ価格分析レポート</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #f0f4f8; color: #333; padding: 20px; }
    h1 { font-size: 1.6em; margin-bottom: 4px; color: #1a1a2e; }
    .meta { font-size: 0.85em; color: #666; margin-bottom: 24px; }
    .filter-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
    .filter-bar input, .filter-bar select {
      padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px;
      font-size: 0.9em; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
    .card {
      background: #fff; border-radius: 12px; overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s;
    }
    .card:hover { transform: translateY(-3px); }
    .card-header { display: flex; align-items: center; gap: 12px; padding: 12px; }
    .card-img { width: 60px; height: 84px; object-fit: contain; border-radius: 4px;
                background: #eee; flex-shrink: 0; }
    .card-img-placeholder { width: 60px; height: 84px; background: #e0e0e0;
                             border-radius: 4px; flex-shrink: 0; display:flex;
                             align-items:center; justify-content:center;
                             font-size:1.8em; }
    .card-title { flex: 1; }
    .card-title h2 { font-size: 1em; color: #1a1a2e; }
    .card-title .name-ja { font-size: 0.85em; color: #666; }
    .card-title .set { font-size: 0.75em; color: #999; margin-top: 2px; }
    .rarity { display: inline-block; font-size: 0.7em; padding: 2px 6px;
              background: #eee; border-radius: 10px; margin-top: 4px; }
    .card-body { padding: 0 12px 12px; }
    .price-row { display: flex; justify-content: space-between;
                 align-items: center; padding: 6px 0;
                 border-bottom: 1px solid #f0f0f0; font-size: 0.9em; }
    .price-row:last-child { border-bottom: none; }
    .label { color: #888; }
    .price-en { font-weight: bold; color: #e63946; font-size: 1.05em; }
    .price-ja { font-weight: bold; color: #457b9d; }
    .ratio { font-weight: bold; }
    .ratio.high { color: #e63946; }
    .ratio.mid  { color: #f4a261; }
    .ratio.low  { color: #2a9d8f; }
    .no-japan { color: #bbb; font-style: italic; }
    .btn { display: inline-block; margin-top: 8px; padding: 6px 12px;
           background: #1a1a2e; color: #fff; border-radius: 6px;
           text-decoration: none; font-size: 0.8em; }
    .btn:hover { background: #e63946; }
    .summary { background:#fff; border-radius:12px; padding:16px;
               margin-bottom:20px; display:flex; gap:24px; flex-wrap:wrap;
               box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .stat { text-align:center; }
    .stat .num { font-size:1.8em; font-weight:bold; color:#e63946; }
    .stat .lbl { font-size:0.8em; color:#888; }
  </style>
</head>
<body>
  <h1>🎴 ポケカ価格分析レポート</h1>
  <p class="meta">生成日時: {generated_at} | 為替レート: 1USD ≈ {rate}円 | {total}件</p>

  <div class="summary">
    <div class="stat"><div class="num">{total}</div><div class="lbl">分析カード数</div></div>
    <div class="stat"><div class="num">{max_usd}</div><div class="lbl">最高海外価格</div></div>
    <div class="stat"><div class="num">{arbitrage_count}</div><div class="lbl">日本より1.5倍↑</div></div>
  </div>

  <div class="filter-bar">
    <input type="text" id="search" placeholder="カード名で絞り込み..." oninput="filterCards()">
    <select id="sort" onchange="sortCards()">
      <option value="price_desc">海外価格 高い順</option>
      <option value="price_asc">海外価格 安い順</option>
      <option value="ratio_desc">倍率 高い順</option>
    </select>
  </div>

  <div class="cards" id="cards">
    {cards_html}
  </div>

  <script>
    const allCards = document.querySelectorAll('.card');
    function filterCards() {
      const q = document.getElementById('search').value.toLowerCase();
      allCards.forEach(c => {
        c.style.display = c.dataset.name.includes(q) ? '' : 'none';
      });
    }
    function sortCards() {
      const val = document.getElementById('sort').value;
      const container = document.getElementById('cards');
      const cards = [...allCards].sort((a, b) => {
        if (val === 'price_desc') return b.dataset.usd - a.dataset.usd;
        if (val === 'price_asc')  return a.dataset.usd - b.dataset.usd;
        if (val === 'ratio_desc') return b.dataset.ratio - a.dataset.ratio;
        return 0;
      });
      cards.forEach(c => container.appendChild(c));
    }
  </script>
</body>
</html>"""

CARD_TEMPLATE = """
<div class="card"
     data-name="{name_lower}"
     data-usd="{usd}"
     data-ratio="{ratio}">
  <div class="card-header">
    {img_html}
    <div class="card-title">
      <h2>{name_en}</h2>
      <div class="name-ja">{name_ja}</div>
      <div class="set">{set_name}</div>
      <span class="rarity">{rarity}</span>
    </div>
  </div>
  <div class="card-body">
    <div class="price-row">
      <span class="label">🌍 海外価格（TCGPlayer）</span>
      <span class="price-en">${usd} <small>≈ ¥{jpy_en:,}</small></span>
    </div>
    <div class="price-row">
      <span class="label">🇯🇵 日本価格</span>
      {japan_price_html}
    </div>
    <div class="price-row">
      <span class="label">📈 海外/日本 倍率</span>
      <span class="ratio {ratio_class}">{ratio_str}</span>
    </div>
    <a href="{tcg_url}" target="_blank" class="btn">TCGPlayerで見る →</a>
  </div>
</div>
"""


def _ratio_class(ratio: float) -> str:
    if ratio >= 2.0:
        return "high"
    if ratio >= 1.5:
        return "mid"
    return "low"


def generate_report(cards: list[CardPrice], output_path: str = "card_report.html") -> str:
    from card_analyzer import get_usd_to_jpy
    rate = get_usd_to_jpy()

    cards_html_parts = []
    for c in cards:
        if c.card_image:
            img_html = f'<img class="card-img" src="{c.card_image}" alt="{c.name_en}" loading="lazy">'
        else:
            img_html = '<div class="card-img-placeholder">🎴</div>'

        if c.japan_price_jpy > 0:
            japan_price_html = f'<span class="price-ja">¥{c.japan_price_jpy:,}</span>'
            ratio_str = f"× {c.arbitrage_ratio:.1f}"
            rc = _ratio_class(c.arbitrage_ratio)
        else:
            japan_price_html = '<span class="no-japan">日本価格データなし</span>'
            ratio_str = "-"
            rc = "low"

        cards_html_parts.append(CARD_TEMPLATE.format(
            name_lower=(c.name_en + " " + c.name_ja).lower(),
            usd=c.tcg_market_usd,
            ratio=round(c.arbitrage_ratio, 2),
            name_en=c.name_en,
            name_ja=c.name_ja,
            set_name=c.set_name,
            rarity=c.rarity,
            img_html=img_html,
            jpy_en=c.tcg_market_jpy,
            japan_price_html=japan_price_html,
            ratio_str=ratio_str,
            ratio_class=rc,
            tcg_url=c.tcg_url,
        ))

    arbitrage_count = sum(1 for c in cards if c.arbitrage_ratio >= 1.5)
    max_usd = f"${max((c.tcg_market_usd for c in cards), default=0):.0f}"

    html = TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y/%m/%d %H:%M"),
        rate=int(rate),
        total=len(cards),
        max_usd=max_usd,
        arbitrage_count=arbitrage_count,
        cards_html="\n".join(cards_html_parts),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
