"""画像生成 - DALL-E 3で自然な日常スナップ風の画像を生成し、Imgurにアップロード"""

import os
import logging
import time
import base64
from pathlib import Path

import openai
import requests

from instagram.config import OPENAI_API_KEY, IMGUR_CLIENT_ID, IMAGE_OUTPUT_DIR

logger = logging.getLogger(__name__)

openai.api_key = OPENAI_API_KEY


def _build_image_prompt(base_prompt: str) -> str:
    """画像生成プロンプトを構築する（AI感を排除する指示を追加）"""
    return (
        f"{base_prompt}. "
        "Style: casual iPhone photo, slightly imperfect composition, "
        "natural warm lighting, shallow depth of field, "
        "taken by a young Japanese woman sharing her daily life on Instagram. "
        "No face visible - show hands, food, scenery, outfit details, or accessories. "
        "The photo should look completely real and authentic, "
        "like a genuine social media post. No text or watermarks. "
        "Soft natural tones, not overly saturated. "
        "Shot from first-person perspective or close-up detail shot."
    )


def generate_image(image_prompt: str) -> str:
    """
    DALL-E 3で画像を生成し、ローカルに保存してファイルパスを返す。

    Args:
        image_prompt: 画像の説明（英語）

    Returns:
        str: 保存された画像のローカルファイルパス
    """
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

    full_prompt = _build_image_prompt(image_prompt)
    logger.info(f"画像生成中... プロンプト: {full_prompt[:100]}...")

    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        # 画像をダウンロードして保存
        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()

        timestamp = int(time.time())
        filename = f"post_{timestamp}.png"
        filepath = os.path.join(IMAGE_OUTPUT_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(image_response.content)

        logger.info(f"画像保存完了: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
        raise


def upload_to_imgur(image_path: str) -> str:
    """
    画像をImgurにアップロードし、公開URLを返す。
    Instagram Graph APIは公開URLが必要なため。

    Args:
        image_path: ローカル画像ファイルのパス

    Returns:
        str: Imgur上の画像URL
    """
    if not IMGUR_CLIENT_ID:
        raise ValueError("IMGUR_CLIENT_IDが設定されていません。.envファイルを確認してください。")

    logger.info(f"Imgurにアップロード中: {image_path}")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
    payload = {"image": image_data, "type": "base64"}

    response = requests.post(
        "https://api.imgur.com/3/image",
        headers=headers,
        data=payload,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    image_url = data["data"]["link"]

    logger.info(f"Imgurアップロード完了: {image_url}")
    return image_url


def generate_and_upload(image_prompt: str) -> dict:
    """
    画像を生成してImgurにアップロードする一連の処理。

    Returns:
        dict: {"local_path": str, "public_url": str}
    """
    local_path = generate_image(image_prompt)
    public_url = upload_to_imgur(local_path)

    return {
        "local_path": local_path,
        "public_url": public_url,
    }
