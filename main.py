"""
ポケモンセンター抽選監視・通知スクリプト

使い方:
    python main.py              # 定期監視モード（.envのCHECK_INTERVAL_MINUTES分ごと）
    python main.py --once       # 1回だけチェックして終了
    python main.py --setup      # Google Calendar認証のセットアップ
"""

import argparse
import logging
import os
import sys
import time

import schedule
from dotenv import load_dotenv

from scraper import get_new_lotteries
from notifier import notify_all

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("lottery_monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def check_and_notify() -> None:
    logger.info("=== 抽選チェック開始 ===")
    new_lotteries = get_new_lotteries()

    if not new_lotteries:
        logger.info("新着抽選なし")
        return

    for lottery in new_lotteries:
        notify_all(lottery)

    logger.info(f"=== チェック完了: {len(new_lotteries)} 件通知 ===")


def setup_google_calendar() -> None:
    """Google Calendar OAuth認証を対話的に実行する"""
    from notifier import _get_calendar_service
    logger.info("Google Calendar認証を開始します...")
    service = _get_calendar_service()
    if service:
        logger.info("Google Calendar認証が完了しました。token.pickle を保存しました。")
    else:
        logger.error("認証に失敗しました。credentials.json を確認してください。")


def main() -> None:
    parser = argparse.ArgumentParser(description="ポケモンセンター抽選監視")
    parser.add_argument("--once", action="store_true", help="1回だけチェックして終了")
    parser.add_argument("--setup", action="store_true", help="Google Calendar認証セットアップ")
    args = parser.parse_args()

    if args.setup:
        setup_google_calendar()
        return

    if args.once:
        check_and_notify()
        return

    interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
    logger.info(f"定期監視モード開始: {interval}分ごとにチェックします")

    # 起動直後に1回チェック
    check_and_notify()

    schedule.every(interval).minutes.do(check_and_notify)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
