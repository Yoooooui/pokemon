"""
Instagram自動投稿システム - メインエントリーポイント

20代日本人女性の日常を切り取ったInstagram投稿を自動生成・投稿する。
AI感をなくし、リアルな人間の投稿に見えるように設計。

使い方:
    # 自動スケジュール投稿（毎日1〜3回、最適時間帯）
    python instagram_main.py

    # 今すぐ1回だけ投稿（テスト用）
    python instagram_main.py --once

    # 指定カテゴリで投稿
    python instagram_main.py --once --category ランチ

    # ドライラン（画像生成まで実行、Instagram投稿はしない）
    python instagram_main.py --dry-run

    # トークンの有効性チェック
    python instagram_main.py --check
"""

import argparse
import logging
import sys
import os
import json
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from instagram.config import POST_LOG_FILE
from instagram.content_generator import generate_caption_with_fallback
from instagram.image_generator import generate_and_upload, generate_image
from instagram.poster import post_to_instagram, check_token_validity
from instagram.scheduler import execute_post, run_scheduler

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("instagram_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def do_single_post(category: str = None):
    """1回だけ投稿を実行"""
    if category:
        logger.info(f"指定カテゴリで投稿: {category}")
        content = generate_caption_with_fallback(category)
        image = generate_and_upload(content["image_prompt"])
        result = post_to_instagram(
            image_url=image["public_url"],
            caption=content["caption"],
            hashtags=content["hashtags"],
            category=content["category"],
        )
        print(f"\n投稿完了！ post_id={result['post_id']}")
    else:
        result = execute_post()
        if result:
            print(f"\n投稿完了！ post_id={result['post_id']}")
        else:
            print("\n投稿に失敗しました。ログを確認してください。")


def do_dry_run(category: str = None):
    """ドライラン - 画像生成まで実行して投稿はしない"""
    category = category or "カフェ"
    logger.info(f"ドライラン開始: カテゴリ={category}")

    content = generate_caption_with_fallback(category)

    print("\n" + "=" * 50)
    print("【生成されたキャプション】")
    print(content["caption"])
    print("\n【ハッシュタグ】")
    print(" ".join(content["hashtags"]))
    print("\n【画像プロンプト】")
    print(content["image_prompt"])

    print("\n画像を生成中...")
    local_path = generate_image(content["image_prompt"])
    print(f"画像保存先: {local_path}")
    print("=" * 50)
    print("\n※ドライランのためInstagramへの投稿はスキップしました。")


def show_post_history():
    """過去の投稿履歴を表示"""
    if not os.path.exists(POST_LOG_FILE):
        print("投稿履歴がありません。")
        return

    with open(POST_LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)

    print(f"\n投稿履歴（{len(logs)}件）:")
    print("-" * 50)
    for log in logs[-10:]:  # 直近10件
        status = "OK" if log.get("status") == "success" else "NG"
        print(f"  [{status}] {log.get('posted_at', '?')} | {log.get('category', '?')}")
        print(f"       {log.get('caption', '')[:60]}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Instagram自動投稿システム")
    parser.add_argument("--once", action="store_true", help="1回だけ投稿して終了")
    parser.add_argument("--category", type=str, help="投稿カテゴリを指定（--onceと併用）")
    parser.add_argument("--dry-run", action="store_true", help="投稿せずにプレビューだけ表示")
    parser.add_argument("--check", action="store_true", help="トークンの有効性チェック")
    parser.add_argument("--history", action="store_true", help="投稿履歴を表示")

    args = parser.parse_args()

    print("=" * 50)
    print("  Instagram自動投稿システム")
    print("  ペルソナ: 20代日本人女性の日常")
    print("=" * 50)

    if args.check:
        print("\nトークンを確認中...")
        if check_token_validity():
            print("トークンは有効です。")
        else:
            print("トークンが無効です。設定を確認してください。")
        return

    if args.history:
        show_post_history()
        return

    if args.dry_run:
        do_dry_run(args.category)
        return

    if args.once:
        do_single_post(args.category)
        return

    # デフォルト: スケジューラー起動
    print("\n自動投稿スケジューラーを起動します...")
    print("投稿タイミング（JST）:")
    print("  朝  7:00〜8:59  (日本の朝 / 北米の夕方〜夜)")
    print("  昼 12:00〜13:59 (日本の昼 / 欧州の朝)")
    print("  夜 19:00〜21:59 (日本の夜 / 北米の朝 / 欧州の昼)")
    print("\nCtrl+C で停止\n")

    run_scheduler()


if __name__ == "__main__":
    main()
