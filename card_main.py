"""
ポケカ価格分析の実行スクリプト

使い方:
    python card_main.py                    # 分析してHTMLレポートを開く
    python card_main.py --min-price 50     # $50以上のカードのみ
    python card_main.py --limit 30         # 30件まで
    python card_main.py --no-open          # ブラウザを開かない
"""

import argparse
import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from card_analyzer import analyze, get_alert_cards, ALERT_SURGE, ALERT_HIGH
from card_report import generate_report
from notifier import notify_card_surge_discord, notify_card_surge_gmail


def main():
    parser = argparse.ArgumentParser(description="ポケカ価格分析")
    parser.add_argument("--min-price", type=float, default=20.0,
                        help="海外最低価格フィルタ（USD、デフォルト: 20）")
    parser.add_argument("--limit", type=int, default=50,
                        help="取得件数上限（デフォルト: 50）")
    parser.add_argument("--output", default="card_report.html",
                        help="出力ファイル名（デフォルト: card_report.html）")
    parser.add_argument("--no-open", action="store_true",
                        help="ブラウザを自動で開かない")
    parser.add_argument("--no-notify", action="store_true",
                        help="LINE/Gmail通知を送らない")
    args = parser.parse_args()

    print(f"分析開始（海外価格${args.min_price}以上 / 最大{args.limit}件）...")

    cards = analyze(min_price_usd=args.min_price, limit=args.limit)
    if not cards:
        print("カードが見つかりませんでした。")
        return

    output = generate_report(cards, args.output)
    abs_path = os.path.abspath(output)

    alert_cards = get_alert_cards(cards)
    surge_count = sum(1 for c in alert_cards if c.alert_level == ALERT_SURGE)
    high_count  = sum(1 for c in alert_cards if c.alert_level == ALERT_HIGH)

    print(f"\nレポート生成完了: {abs_path}")
    print(f"カード数: {len(cards)}件  🚨 急騰: {surge_count}件  ⚠️ 予兆: {high_count}件")

    # 予兆カードがあれば通知
    if alert_cards and not args.no_notify:
        print("通知送信中...")
        notify_card_surge_discord(alert_cards)
        notify_card_surge_gmail(alert_cards)

    if not args.no_open:
        if sys.platform == "darwin":
            subprocess.run(["open", abs_path])
        elif sys.platform == "win32":
            os.startfile(abs_path)
        else:
            subprocess.run(["xdg-open", abs_path])


if __name__ == "__main__":
    main()
