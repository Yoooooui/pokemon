"""Instagram投稿 - Graph APIを使った自動投稿"""

import json
import os
import time
import logging
from datetime import datetime

import requests

from instagram.config import (
    INSTAGRAM_ACCOUNT_ID,
    INSTAGRAM_ACCESS_TOKEN,
    POST_LOG_FILE,
    TIMEZONE,
)

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


def _save_post_log(post_data: dict):
    """投稿ログをJSONファイルに保存"""
    logs = []
    if os.path.exists(POST_LOG_FILE):
        with open(POST_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append(post_data)

    with open(POST_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def create_media_container(image_url: str, caption: str) -> str:
    """
    Instagram Graph APIでメディアコンテナを作成する。

    Args:
        image_url: 公開アクセス可能な画像URL
        caption: 投稿キャプション（ハッシュタグ含む）

    Returns:
        str: メディアコンテナID
    """
    url = f"{GRAPH_API_BASE}/{INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }

    response = requests.post(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    container_id = data["id"]
    logger.info(f"メディアコンテナ作成: {container_id}")

    return container_id


def publish_media(container_id: str) -> str:
    """
    メディアコンテナを公開する。

    Args:
        container_id: メディアコンテナID

    Returns:
        str: 公開された投稿のID
    """
    # コンテナの処理完了を待つ
    _wait_for_container(container_id)

    url = f"{GRAPH_API_BASE}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    params = {
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }

    response = requests.post(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    post_id = data["id"]
    logger.info(f"投稿公開完了: {post_id}")

    return post_id


def _wait_for_container(container_id: str, max_wait: int = 60):
    """メディアコンテナの処理が完了するまで待機"""
    url = f"{GRAPH_API_BASE}/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }

    for _ in range(max_wait // 5):
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        status = response.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"メディアコンテナの処理に失敗: {response.json()}")

        logger.debug(f"メディアコンテナ処理中... status={status}")
        time.sleep(5)

    raise TimeoutError("メディアコンテナの処理がタイムアウトしました")


def post_to_instagram(image_url: str, caption: str, hashtags: list[str], category: str) -> dict:
    """
    Instagramに画像付き投稿を行う。

    Args:
        image_url: 公開アクセス可能な画像URL
        caption: キャプション本文
        hashtags: ハッシュタグのリスト
        category: 投稿カテゴリ

    Returns:
        dict: 投稿結果
    """
    # キャプション + ハッシュタグを組み立て
    full_caption = caption + "\n\n" + " ".join(hashtags)

    logger.info(f"Instagram投稿開始: カテゴリ={category}")
    logger.info(f"キャプション: {caption}")

    try:
        # Step 1: メディアコンテナ作成
        container_id = create_media_container(image_url, full_caption)

        # Step 2: 公開
        post_id = publish_media(container_id)

        # 投稿ログ保存
        post_data = {
            "post_id": post_id,
            "category": category,
            "caption": caption,
            "hashtags": hashtags,
            "image_url": image_url,
            "posted_at": datetime.now().isoformat(),
            "status": "success",
        }
        _save_post_log(post_data)

        logger.info(f"投稿成功！ post_id={post_id}")
        return post_data

    except Exception as e:
        logger.error(f"Instagram投稿エラー: {e}")

        error_data = {
            "category": category,
            "caption": caption,
            "error": str(e),
            "posted_at": datetime.now().isoformat(),
            "status": "failed",
        }
        _save_post_log(error_data)

        raise


def check_token_validity() -> bool:
    """アクセストークンの有効性を確認"""
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.error("INSTAGRAM_ACCESS_TOKEN または INSTAGRAM_ACCOUNT_ID が未設定です")
        return False

    url = f"{GRAPH_API_BASE}/{INSTAGRAM_ACCOUNT_ID}"
    params = {
        "fields": "id,username",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.info(f"トークン有効: アカウント={data.get('username', 'unknown')}")
        return True
    except Exception as e:
        logger.error(f"トークン検証エラー: {e}")
        return False
