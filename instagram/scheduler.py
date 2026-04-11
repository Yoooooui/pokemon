"""スケジューラー - 最適な時間帯に自動投稿をスケジューリング"""

import random
import logging
from datetime import datetime

import pytz
import schedule

from instagram.config import POST_SCHEDULE, WEEKEND_CATEGORIES, TIMEZONE
from instagram.content_generator import generate_caption_with_fallback
from instagram.image_generator import generate_and_upload
from instagram.poster import post_to_instagram, check_token_validity

logger = logging.getLogger(__name__)


def _get_current_time_jst() -> datetime:
    """日本時間を取得"""
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)


def _is_weekend() -> bool:
    """今日が週末かどうか"""
    return _get_current_time_jst().weekday() >= 5


def _select_category() -> str:
    """現在の時間帯と曜日に合わせたカテゴリを選択"""
    now = _get_current_time_jst()
    hour = now.hour

    # 週末は特別カテゴリも候補に入れる
    extra_categories = WEEKEND_CATEGORIES if _is_weekend() else []

    # 時間帯に合ったカテゴリを取得
    for slot_name, slot_config in POST_SCHEDULE.items():
        if hour in slot_config["hours"]:
            categories = slot_config["categories"] + extra_categories
            return random.choice(categories)

    # どの時間帯にも当てはまらない場合（基本的には起きないが安全策）
    all_categories = []
    for slot_config in POST_SCHEDULE.values():
        all_categories.extend(slot_config["categories"])
    return random.choice(all_categories)


def execute_post():
    """1回分の投稿を実行する"""
    logger.info("=" * 50)
    logger.info("投稿プロセス開始")

    try:
        # 1. カテゴリ選択
        category = _select_category()
        logger.info(f"選択カテゴリ: {category}")

        # 2. キャプション生成
        content = generate_caption_with_fallback(category)
        logger.info(f"キャプション生成完了: {content['caption'][:50]}...")

        # 3. 画像生成 & アップロード
        image = generate_and_upload(content["image_prompt"])
        logger.info(f"画像準備完了: {image['public_url']}")

        # 4. Instagram投稿
        result = post_to_instagram(
            image_url=image["public_url"],
            caption=content["caption"],
            hashtags=content["hashtags"],
            category=content["category"],
        )

        logger.info(f"投稿完了！ post_id={result['post_id']}")
        return result

    except Exception as e:
        logger.error(f"投稿プロセスでエラーが発生: {e}", exc_info=True)
        return None


def _random_minute() -> str:
    """ランダムな分を生成（毎回同じ時間に投稿しないように）"""
    return f"{random.randint(0, 59):02d}"


def setup_schedule():
    """
    毎日の投稿スケジュールを設定する。

    投稿タイミング（JST）:
    - 朝: 7:00〜8:59（日本の朝 + 北米の夜）
    - 昼: 12:00〜13:59（日本の昼 + 欧州の朝）
    - 夜: 19:00〜21:59（日本の夜 + 北米の朝 + 欧州の昼）

    最低1日1投稿を保証し、ランダムに2〜3投稿にする。
    """
    schedule.clear()

    # 必ず1つは夜の投稿（最もエンゲージメントが高い時間帯）
    evening_hour = random.choice(POST_SCHEDULE["evening"]["hours"])
    evening_time = f"{evening_hour}:{_random_minute()}"
    schedule.every().day.at(evening_time).do(execute_post)
    logger.info(f"夜の投稿スケジュール: {evening_time} JST")

    # 60%の確率で朝も投稿
    if random.random() < 0.6:
        morning_hour = random.choice(POST_SCHEDULE["morning"]["hours"])
        morning_time = f"{morning_hour:02d}:{_random_minute()}"
        schedule.every().day.at(morning_time).do(execute_post)
        logger.info(f"朝の投稿スケジュール: {morning_time} JST")

    # 50%の確率で昼も投稿
    if random.random() < 0.5:
        lunch_hour = random.choice(POST_SCHEDULE["lunch"]["hours"])
        lunch_time = f"{lunch_hour}:{_random_minute()}"
        schedule.every().day.at(lunch_time).do(execute_post)
        logger.info(f"昼の投稿スケジュール: {lunch_time} JST")

    # 日替わりでスケジュールを更新（同じパターンを繰り返さないように）
    schedule.every().day.at("00:01").do(setup_schedule)
    logger.info("翌日のスケジュール再生成: 00:01 JST")


def run_scheduler():
    """スケジューラーを起動する"""
    logger.info("Instagram自動投稿スケジューラーを起動します")

    # トークンの有効性を確認
    if not check_token_validity():
        logger.error("Instagramトークンが無効です。設定を確認してください。")
        return

    # スケジュール設定
    setup_schedule()

    logger.info("スケジューラー稼働中... Ctrl+C で停止")

    import time
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("スケジューラーを停止しました")
