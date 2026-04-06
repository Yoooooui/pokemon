"""HTMLレポートを生成する"""

import os
from datetime import datetime
from card_analyzer import CardPrice, ALERT_SURGE, ALERT_HIGH, ALERT_WATCH, ALERT_NONE, get_usd_to_jpy

TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ポケカ価格分析レポート</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f0f4f8; color: #333; padding: 20px; }}
    h1 {{ font-size: 1.6em; margin-bottom: 4px; color: #1a1a2e; }}
    .meta {{ font-size: 0.85em; color: #666; margin-bottom: 16px; }}

    /* 緊急アラートバナー */
    .surge-banner {{ background: linear-gradient(135deg, #e63946, #c1121f);
                     color: #fff; border-radius: 12px; padding: 16px 20px;
                     margin-bottom: 20px; }}
    .surge-banner h2 {{ font-size: 1.1em; margin-bottom: 8px; }}
    .surge-item {{ background: rgba(255,255,255,0.15); border-radius: 8px;
                   padding: 8px 12px; margin: 6px 0; font-size: 0.9em; }}
    .surge-item strong {{ font-size: 1.05em; }}

    .summary {{ background:#fff; border-radius:12px; padding:16px;
                margin-bottom:20px; display:flex; gap:24px; flex-wrap:wrap;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .stat {{ text-align:center; }}
    .stat .num {{ font-size:1.8em; font-weight:bold; color:#e63946; }}
    .stat .lbl {{ font-size:0.8em; color:#888; }}

    .filter-bar {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
    .filter-bar input, .filter-bar select {{
      padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 0.9em; }}

    .section-title {{ font-size: 1em; font-weight: bold; color: #555;
                      margin: 20px 0 10px; border-left: 4px solid #e63946;
                      padding-left: 8px; }}

    .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
    .card {{ background: #fff; border-radius: 12px; overflow: hidden;
             box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s;
             border-top: 4px solid transparent; }}
    .card:hover {{ transform: translateY(-3px); }}
    .card.alert-surge {{ border-top-color: #e63946; }}
    .card.alert-high  {{ border-top-color: #f4a261; }}
    .card.alert-watch {{ border-top-color: #a8dadc; }}

    .alert-badge {{ display: inline-block; font-size: 0.7em; font-weight: bold;
                    padding: 2px 8px; border-radius: 10px; margin-left: 6px;
                    vertical-align: middle; }}
    .badge-surge {{ background: #e63946; color: #fff; }}
    .badge-high  {{ background: #f4a261; color: #fff; }}
    .badge-watch {{ background: #a8dadc; color: #1d3557; }}

    .card-header {{ display: flex; align-items: center; gap: 12px; padding: 12px; }}
    .card-img {{ width: 60px; height: 84px; object-fit: contain; border-radius: 4px;
                 background: #eee; flex-shrink: 0; }}
    .card-img-placeholder {{ width: 60px; height: 84px; background: #e0e0e0;
                              border-radius: 4px; flex-shrink: 0; display:flex;
                              align-items:center; justify-content:center; font-size:1.8em; }}
    .card-title {{ flex: 1; }}
    .card-title h2 {{ font-size: 1em; color: #1a1a2e; }}
    .card-title .name-ja {{ font-size: 0.85em; color: #666; }}
    .card-title .set {{ font-size: 0.75em; color: #999; margin-top: 2px; }}
    .rarity {{ display: inline-block; font-size: 0.7em; padding: 2px 6px;
               background: #eee; border-radius: 10px; margin-top: 4px; }}
    .card-body {{ padding: 0 12px 12px; }}
    .price-row {{ display: flex; justify-content: space-between; align-items: center;
                  padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9em; }}
    .price-row:last-child {{ border-bottom: none; }}
    .label {{ color: #888; }}
    .price-en {{ font-weight: bold; color: #e63946; font-size: 1.05em; }}
    .price-ja {{ font-weight: bold; color: #457b9d; }}
    .ratio {{ font-weight: bold; }}
    .ratio.high {{ color: #e63946; }}
    .ratio.mid  {{ color: #f4a261; }}
    .ratio.low  {{ color: #2a9d8f; }}
    .change-up   {{ color: #e63946; font-weight: bold; }}
    .change-down {{ color: #2a9d8f; font-weight: bold; }}
    .change-flat {{ color: #999; }}
    .no-japan {{ color: #bbb; font-style: italic; }}
    .btn {{ display: inline-block; margin-top: 8px; padding: 6px 12px;
            background: #1a1a2e; color: #fff; border-radius: 6px;
            text-decoration: none; font-size: 0.8em; }}
    .btn:hover {{ background: #e63946; }}
  </style>
</head>
<body>
  <h1>🎴 ポケカ価格分析レポート</h1>
  <p class="meta">生成日時: {generated_at} | 為替レート: 1USD ≈ {rate}円 | {total}件</p>

  {surge_banner}

  <div class="summary">
    <div class="stat"><div class="num">{total}</div><div class="lbl">分析カード数</div></div>
    <div class="stat"><div class="num">{max_usd}</div><div class="lbl">最高海外価格</div></div>
    <div class="stat"><div class="num" style="color:#e63946">{surge_count}</div><div class="lbl">🚨 急騰検知</div></div>
    <div class="stat"><div class="num" style="color:#f4a261">{high_count}</div><div class="lbl">⚠️ 高騰予兆</div></div>
  </div>

  <div class="filter-bar">
    <input type="text" id="search" placeholder="カード名で絞り込み..." oninput="filterCards()">
    <select id="sort" onchange="sortCards()">
      <option value="alert">予兆レベル順</option>
      <option value="price_desc">海外価格 高い順</option>
      <option value="ratio_desc">倍率 高い順</option>
      <option value="change_desc">価格変化 大きい順</option>
    </select>
    <select id="filter_alert" onchange="filterCards()">
      <option value="">すべて表示</option>
      <option value="surge">🚨 急騰のみ</option>
      <option value="high">⚠️ 予兆以上</option>
    </select>
  </div>

  <div class="cards" id="cards">
    {cards_html}
  </div>

  <script>
    const allCards = [...document.querySelectorAll('.card')];
    function filterCards() {{
      const q = document.getElementById('search').value.toLowerCase();
      const fa = document.getElementById('filter_alert').value;
      allCards.forEach(c => {{
        const nameOk = c.dataset.name.includes(q);
        const alertOk = !fa || c.dataset.alert === fa ||
                        (fa === 'high' && ['surge','high'].includes(c.dataset.alert));
        c.style.display = (nameOk && alertOk) ? '' : 'none';
      }});
    }}
    function sortCards() {{
      const val = document.getElementById('sort').value;
      const container = document.getElementById('cards');
      const order = {{surge:0, high:1, watch:2, none:3}};
      const sorted = allCards.slice().sort((a, b) => {{
        if (val === 'alert')      return (order[a.dataset.alert]||3) - (order[b.dataset.alert]||3);
        if (val === 'price_desc') return b.dataset.usd - a.dataset.usd;
        if (val === 'ratio_desc') return b.dataset.ratio - a.dataset.ratio;
        if (val === 'change_desc')return b.dataset.change - a.dataset.change;
        return 0;
      }});
      sorted.forEach(c => container.appendChild(c));
    }}
  </script>
</body>
</html>"""

CARD_TEMPLATE = """
<div class="card alert-{alert_level}"
     data-name="{name_lower}"
     data-usd="{usd}"
     data-ratio="{ratio}"
     data-change="{change_pct}"
     data-alert="{alert_level}">
  <div class="card-header">
    {img_html}
    <div class="card-title">
      <h2>{name_en}{alert_badge}</h2>
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
      <span class="label">📊 前回比</span>
      <span class="{change_class}">{change_str}</span>
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


def _alert_badge(alert_level: str) -> str:
    if alert_level == ALERT_SURGE:
        return '<span class="alert-badge badge-surge">🚨 急騰</span>'
    if alert_level == ALERT_HIGH:
        return '<span class="alert-badge badge-high">⚠️ 予兆</span>'
    if alert_level == ALERT_WATCH:
        return '<span class="alert-badge badge-watch">👀 注目</span>'
    return ""


def _change_str_and_class(pct: float, prev: float) -> tuple[str, str]:
    if prev <= 0:
        return "初回データ", "change-flat"
    if pct >= 1:
        return f"▲ +{pct:.1f}%", "change-up"
    if pct <= -1:
        return f"▼ {pct:.1f}%", "change-down"
    return f"→ {pct:+.1f}%", "change-flat"


def _build_surge_banner(surge_cards: list[CardPrice]) -> str:
    if not surge_cards:
        return ""
    items = ""
    for c in surge_cards[:5]:
        items += (
            f'<div class="surge-item">'
            f'<strong>{c.name_ja}（{c.name_en}）</strong> — '
            f'海外 ${c.tcg_market_usd} '
            f'<small>(前回比 +{c.price_change_pct:.0f}%)</small> / '
            f'日本 {"¥"+f"{c.japan_price_jpy:,}" if c.japan_price_jpy else "データなし"}'
            f'</div>'
        )
    return f"""
<div class="surge-banner">
  <h2>🚨 海外価格急騰カード — 日本価格も近く上昇する可能性があります</h2>
  {items}
</div>"""


def generate_report(cards: list[CardPrice], output_path: str = "card_report.html") -> str:
    rate = get_usd_to_jpy()

    surge_cards = [c for c in cards if c.alert_level == ALERT_SURGE]
    high_cards  = [c for c in cards if c.alert_level == ALERT_HIGH]

    cards_html_parts = []
    for c in cards:
        img_html = (
            f'<img class="card-img" src="{c.card_image}" alt="{c.name_en}" loading="lazy">'
            if c.card_image else
            '<div class="card-img-placeholder">🎴</div>'
        )
        japan_price_html = (
            f'<span class="price-ja">¥{c.japan_price_jpy:,}</span>'
            if c.japan_price_jpy > 0 else
            '<span class="no-japan">データなし</span>'
        )
        ratio_str = f"× {c.arbitrage_ratio:.1f}" if c.japan_price_jpy > 0 else "-"
        change_str, change_class = _change_str_and_class(c.price_change_pct, c.prev_tcg_usd)

        cards_html_parts.append(CARD_TEMPLATE.format(
            alert_level=c.alert_level,
            name_lower=(c.name_en + " " + c.name_ja).lower(),
            usd=c.tcg_market_usd,
            ratio=round(c.arbitrage_ratio, 2),
            change_pct=round(c.price_change_pct, 1),
            name_en=c.name_en,
            name_ja=c.name_ja,
            set_name=c.set_name,
            rarity=c.rarity,
            img_html=img_html,
            alert_badge=_alert_badge(c.alert_level),
            jpy_en=c.tcg_market_jpy,
            japan_price_html=japan_price_html,
            ratio_str=ratio_str,
            ratio_class=_ratio_class(c.arbitrage_ratio),
            change_str=change_str,
            change_class=change_class,
            tcg_url=c.tcg_url,
        ))

    html = TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y/%m/%d %H:%M"),
        rate=int(rate),
        total=len(cards),
        max_usd=f"${max((c.tcg_market_usd for c in cards), default=0):.0f}",
        surge_count=len(surge_cards),
        high_count=len(high_cards),
        surge_banner=_build_surge_banner(surge_cards),
        cards_html="\n".join(cards_html_parts),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
