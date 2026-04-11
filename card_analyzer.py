from __future__ import annotations
"""
ポケカ価格分析
海外（TCGPlayer）と日本（カードラッシュ）の価格を比較し、
高騰カード・割安カードを抽出する。

海外価格が先行して上がる → 日本価格が後追いで上がる傾向を利用し、
「日本価格高騰予兆カード」を早期検出して通知する。
"""

import json
import logging
import os
import time
import re
from dataclasses import dataclass, field
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PRICE_HISTORY_FILE = "card_price_history.json"

POKEMON_TCG_API = "https://api.pokemontcg.io/v2/cards"
CARDRUSH_SEARCH_URL = "https://www.cardrush-pokemon.jp/product-list?name={}"
TOREKA_SEARCH_URL = "https://torecamarket.com/pokekas/?keyword={}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# 円/ドル レート（.envで上書き可）
DEFAULT_USD_TO_JPY = 150.0


ALERT_NONE = "none"
ALERT_WATCH = "watch"    # 海外が日本の1.5〜2倍（要注目）
ALERT_HIGH  = "high"     # 海外が日本の2倍以上（高騰予兆）
ALERT_SURGE = "surge"    # 前回比で海外価格が急騰（緊急）


@dataclass
class CardPrice:
    name_en: str
    name_ja: str
    set_name: str
    rarity: str
    tcg_market_usd: float       # TCGPlayer市場価格（USD）
    tcg_market_jpy: float       # 円換算
    japan_price_jpy: int        # 日本市場価格（円）
    japan_source: str           # 価格出典
    card_image: str             # カード画像URL
    tcg_url: str                # TCGPlayerページ
    prev_tcg_usd: float = 0.0   # 前回の海外価格（履歴から）
    arbitrage_ratio: float = field(init=False)
    price_change_pct: float = field(init=False)   # 海外価格の前回比変化率（%）
    alert_level: str = field(init=False)          # 予兆レベル

    def __post_init__(self):
        self.arbitrage_ratio = (
            self.tcg_market_jpy / self.japan_price_jpy
            if self.japan_price_jpy > 0 else 0.0
        )
        self.price_change_pct = (
            (self.tcg_market_usd - self.prev_tcg_usd) / self.prev_tcg_usd * 100
            if self.prev_tcg_usd > 0 else 0.0
        )
        # 予兆レベルを判定
        if self.price_change_pct >= 20:
            self.alert_level = ALERT_SURGE   # 海外が急騰（緊急通知）
        elif self.arbitrage_ratio >= 2.0:
            self.alert_level = ALERT_HIGH    # 海外が日本の2倍以上
        elif self.arbitrage_ratio >= 1.5:
            self.alert_level = ALERT_WATCH   # 要注目
        else:
            self.alert_level = ALERT_NONE


def get_usd_to_jpy() -> float:
    """為替レートを取得（失敗時はデフォルト値）"""
    rate = os.getenv("USD_TO_JPY")
    if rate:
        return float(rate)
    try:
        resp = requests.get(
            "https://open.er-api.com/v6/latest/USD", timeout=5
        )
        return resp.json()["rates"]["JPY"]
    except Exception:
        return DEFAULT_USD_TO_JPY


def fetch_english_cards(min_price_usd: float = 20.0, page_size: int = 100) -> list[dict]:
    """TCGPlayerで一定額以上の英語カードを取得"""
    tcg_api_key = os.getenv("POKEMON_TCG_API_KEY", "")
    headers = {"X-Api-Key": tcg_api_key} if tcg_api_key else {}

    all_cards = []
    page = 1

    while True:
        try:
            params = {
                "q": f"tcgplayer.prices.holofoil.market:[{min_price_usd} TO *] OR "
                     f"tcgplayer.prices.normal.market:[{min_price_usd} TO *] OR "
                     f"tcgplayer.prices.reverseHolofoil.market:[{min_price_usd} TO *]",
                "orderBy": "-tcgplayer.prices.holofoil.market",
                "pageSize": page_size,
                "page": page,
                "select": "id,name,set,rarity,tcgplayer,images,nationalPokedexNumbers",
            }
            resp = requests.get(POKEMON_TCG_API, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            cards = data.get("data", [])
            if not cards:
                break
            all_cards.extend(cards)
            if len(all_cards) >= data.get("totalCount", 0) or page >= 5:
                break
            page += 1
            time.sleep(0.3)
        except requests.RequestException as e:
            logger.error(f"Pokemon TCG API エラー: {e}")
            break

    logger.info(f"英語カード {len(all_cards)} 件取得")
    return all_cards


def get_best_tcg_price(tcgplayer: dict) -> float:
    """TCGプレイヤーデータから最高市場価格を返す"""
    prices = tcgplayer.get("prices", {})
    best = 0.0
    for variant in prices.values():
        market = variant.get("market") or 0
        best = max(best, market)
    return best


def get_tcg_url(tcgplayer: dict) -> str:
    return tcgplayer.get("url", "https://www.tcgplayer.com/")


def search_japan_price_cardrush(name_ja: str) -> tuple[int, str]:
    """カードラッシュで日本語カード価格を検索"""
    if not name_ja:
        return 0, ""
    try:
        url = CARDRUSH_SEARCH_URL.format(requests.utils.quote(name_ja))
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # 価格要素を探す
        price_el = soup.select_one(".price, .sell-price, [class*='price']")
        if price_el:
            text = re.sub(r"[^\d]", "", price_el.get_text())
            if text:
                return int(text), url
    except Exception as e:
        logger.debug(f"カードラッシュ検索失敗 ({name_ja}): {e}")
    return 0, ""


# 英語名→日本語名の簡易マッピング（主要レアカード）
EN_TO_JA: dict[str, str] = {
    "Charizard": "リザードン",
    "Pikachu": "ピカチュウ",
    "Mewtwo": "ミュウツー",
    "Mew": "ミュウ",
    "Umbreon": "ブラッキー",
    "Espeon": "エーフィ",
    "Rayquaza": "レックウザ",
    "Lugia": "ルギア",
    "Ho-Oh": "ホウオウ",
    "Gengar": "ゲンガー",
    "Blastoise": "カメックス",
    "Venusaur": "フシギバナ",
    "Snorlax": "カビゴン",
    "Eevee": "イーブイ",
    "Alakazam": "フーディン",
    "Gyarados": "ギャラドス",
    "Dragonite": "カイリュー",
    "Gardevoir": "サーナイト",
    "Garchomp": "ガブリアス",
    "Sylveon": "ニンフィア",
    "Glaceon": "グレイシア",
    "Leafeon": "リーフィア",
    "Flareon": "ブースター",
    "Vaporeon": "シャワーズ",
    "Jolteon": "サンダース",
}


def translate_name(name_en: str) -> str:
    """英語名→日本語名に変換（部分一致）"""
    for en, ja in EN_TO_JA.items():
        if en.lower() in name_en.lower():
            return ja
    return ""


# ---------------------------------------------------------------------------
# 価格履歴（前回比較用）
# ---------------------------------------------------------------------------

def load_price_history() -> dict:
    if not os.path.exists(PRICE_HISTORY_FILE):
        return {}
    with open(PRICE_HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_price_history(history: dict) -> None:
    with open(PRICE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def update_history(history: dict, card_key: str, usd_price: float) -> float:
    """履歴を更新し、前回価格を返す"""
    prev = history.get(card_key, {}).get("usd", 0.0)
    history[card_key] = {
        "usd": usd_price,
        "updated_at": datetime.now().isoformat(),
    }
    return prev


def analyze(
    min_price_usd: float = 20.0,
    min_arbitrage: float = 1.5,
    limit: int = 50,
) -> list[CardPrice]:
    """
    海外高騰カードを分析して返す

    Args:
        min_price_usd: 海外最低価格フィルタ（USD）
        min_arbitrage: 海外/日本 最低倍率フィルタ
        limit: 最大取得件数
    """
    rate = get_usd_to_jpy()
    logger.info(f"為替レート: 1USD = {rate}円")

    raw_cards = fetch_english_cards(min_price_usd=min_price_usd)
    history = load_price_history()
    results: list[CardPrice] = []

    for raw in raw_cards[:limit]:
        tcgplayer = raw.get("tcgplayer", {})
        if not tcgplayer:
            continue

        usd_price = get_best_tcg_price(tcgplayer)
        if usd_price < min_price_usd:
            continue

        jpy_price = usd_price * rate
        name_en = raw.get("name", "")
        name_ja = translate_name(name_en)
        card_key = f"{raw.get('id', name_en)}"

        # 前回価格と比較
        prev_usd = update_history(history, card_key, usd_price)

        japan_price, japan_src = 0, ""
        if name_ja:
            japan_price, japan_src = search_japan_price_cardrush(name_ja)
            time.sleep(0.5)

        card = CardPrice(
            name_en=name_en,
            name_ja=name_ja or name_en,
            set_name=raw.get("set", {}).get("name", ""),
            rarity=raw.get("rarity", ""),
            tcg_market_usd=usd_price,
            tcg_market_jpy=round(jpy_price),
            japan_price_jpy=japan_price,
            japan_source=japan_src,
            card_image=raw.get("images", {}).get("large", ""),
            tcg_url=get_tcg_url(tcgplayer),
            prev_tcg_usd=prev_usd,
        )
        results.append(card)

    save_price_history(history)

    # 予兆レベル優先、同レベル内は海外価格の高い順
    level_order = {ALERT_SURGE: 0, ALERT_HIGH: 1, ALERT_WATCH: 2, ALERT_NONE: 3}
    results.sort(key=lambda c: (level_order[c.alert_level], -c.tcg_market_usd))
    logger.info(f"分析完了: {len(results)} 件 "
                f"(緊急:{sum(1 for c in results if c.alert_level==ALERT_SURGE)} / "
                f"予兆:{sum(1 for c in results if c.alert_level==ALERT_HIGH)})")
    return results


def get_alert_cards(cards: list[CardPrice]) -> list[CardPrice]:
    """通知が必要な予兆カードのみ返す"""
    return [c for c in cards if c.alert_level in (ALERT_SURGE, ALERT_HIGH)]
