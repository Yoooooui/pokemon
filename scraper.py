import requests
from bs4 import BeautifulSoup
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LOTTERY_URL = "https://www.pokemoncenter-online.com/special/lottery/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
SEEN_FILE = "seen_lotteries.json"


def load_seen_lotteries() -> set:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_seen_lotteries(seen: set) -> None:
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False, indent=2)


def fetch_lotteries() -> list[dict]:
    """ポケモンセンターの抽選一覧を取得する"""
    try:
        resp = requests.get(LOTTERY_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"抽選ページの取得に失敗しました: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    lotteries = []

    # 抽選商品のカード要素を探す（サイト構造に合わせて調整）
    items = soup.select(".lottery-item, .product-item, article.item")
    if not items:
        # フォールバック: より広い検索
        items = soup.select("[class*='lottery'], [class*='raffle']")

    for item in items:
        title_el = item.select_one("h2, h3, .item-name, .product-name, [class*='title']")
        link_el = item.select_one("a[href]")
        date_el = item.select_one("[class*='date'], [class*='period'], time")
        img_el = item.select_one("img")

        title = title_el.get_text(strip=True) if title_el else "タイトル不明"
        link = link_el["href"] if link_el else LOTTERY_URL
        if link and not link.startswith("http"):
            link = "https://www.pokemoncenter-online.com" + link
        period = date_el.get_text(strip=True) if date_el else "期間不明"
        image = img_el.get("src", "") if img_el else ""

        lottery_id = link.rstrip("/").split("/")[-1] or title

        lotteries.append({
            "id": lottery_id,
            "title": title,
            "url": link,
            "period": period,
            "image": image,
            "found_at": datetime.now().isoformat(),
        })

    return lotteries


def get_new_lotteries() -> list[dict]:
    """新着の抽選情報のみ返す"""
    seen = load_seen_lotteries()
    all_lotteries = fetch_lotteries()

    new_ones = [lot for lot in all_lotteries if lot["id"] not in seen]

    if new_ones:
        seen.update(lot["id"] for lot in new_ones)
        save_seen_lotteries(seen)
        logger.info(f"新着抽選 {len(new_ones)} 件を検出しました")
    else:
        logger.info("新着抽選はありません")

    return new_ones
