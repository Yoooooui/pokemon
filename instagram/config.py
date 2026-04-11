"""Instagram自動投稿の設定"""

import os
from dotenv import load_dotenv

load_dotenv()

# Instagram Graph API
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

# OpenAI API（キャプション生成 + 画像生成）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# 画像をホストするURL（Instagram APIは公開URLが必要）
IMAGE_HOST_BASE_URL = os.getenv("IMAGE_HOST_BASE_URL", "")

# Imgur API（画像ホスティング用）
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID", "")

# ペルソナ設定
PERSONA = {
    "name": "ゆい",
    "age": 25,
    "location": "東京",
    "occupation": "会社員",
    "personality": "明るくてポジティブ、おしゃれが好き、カフェ巡りが趣味",
    "tone": "カジュアルで親しみやすい、絵文字を自然に使う、長すぎない",
}

# 投稿カテゴリと時間帯マッピング（JST）
# グローバルリーチを考慮した最適時間帯
POST_SCHEDULE = {
    "morning": {
        "hours": [7, 8],
        "categories": ["朝の支度", "モーニング", "通勤風景", "朝カフェ"],
        "description": "朝の日常（日本の朝 + 北米の夕方〜夜）",
    },
    "lunch": {
        "hours": [12, 13],
        "categories": ["ランチ", "カフェ", "オフィス周辺", "お弁当"],
        "description": "ランチタイム（日本の昼 + 欧州の朝）",
    },
    "evening": {
        "hours": [19, 20, 21],
        "categories": ["ディナー", "夜カフェ", "夜景", "おうち時間", "スキンケア"],
        "description": "夜の投稿（日本の夜 + 北米の朝 + 欧州の昼）",
    },
}

# 週末限定カテゴリ
WEEKEND_CATEGORIES = [
    "お出かけ",
    "ショッピング",
    "友達とランチ",
    "美術館",
    "公園散歩",
    "旅行",
    "ブランチ",
    "ネイル",
    "ヨガ",
]

# ハッシュタグ戦略
HASHTAGS = {
    "base": [
        "#日常",
        "#暮らし",
        "#日々の暮らし",
        "#丁寧な暮らし",
        "#シンプルライフ",
    ],
    "food": [
        "#おうちごはん",
        "#カフェ巡り",
        "#ランチ",
        "#カフェ好き",
        "#foodstagram",
        "#japanesefood",
        "#tokyocafe",
        "#lunchtime",
    ],
    "fashion": [
        "#今日のコーデ",
        "#ootd",
        "#コーデ",
        "#プチプラコーデ",
        "#fashion",
        "#japanfashion",
        "#tokyofashion",
    ],
    "lifestyle": [
        "#東京ライフ",
        "#tokyolife",
        "#japanlife",
        "#livinginjapan",
        "#lifeinJapan",
        "#aesthetic",
        "#vibes",
    ],
    "beauty": [
        "#スキンケア",
        "#美容",
        "#コスメ",
        "#skincare",
        "#beauty",
        "#japanesebeauty",
        "#jbeauty",
    ],
    "travel": [
        "#旅行",
        "#お出かけ",
        "#週末旅行",
        "#travel",
        "#japantravel",
        "#explorejapan",
    ],
}

# 投稿画像の保存先
IMAGE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")

# 投稿ログ
POST_LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "instagram_post_log.json"
)

# タイムゾーン
TIMEZONE = "Asia/Tokyo"
