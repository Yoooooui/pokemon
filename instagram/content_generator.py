"""キャプション生成 - 20代日本人女性の自然な日常投稿を生成"""

import json
import random
import logging
from datetime import datetime

import openai

from instagram.config import OPENAI_API_KEY, PERSONA, HASHTAGS

logger = logging.getLogger(__name__)

openai.api_key = OPENAI_API_KEY


def _get_season(month: int) -> str:
    if month in (3, 4, 5):
        return "春"
    elif month in (6, 7, 8):
        return "夏"
    elif month in (9, 10, 11):
        return "秋"
    else:
        return "冬"


def _get_seasonal_topics(season: str) -> list[str]:
    topics = {
        "春": ["桜", "お花見", "新生活", "春コーデ", "いちごスイーツ", "花粉症つらい"],
        "夏": ["かき氷", "海", "花火", "夏祭り", "アイスコーヒー", "日焼け止め", "冷やし中華"],
        "秋": ["紅葉", "秋コーデ", "さんま", "かぼちゃスイーツ", "読書の秋", "栗スイーツ"],
        "冬": ["イルミネーション", "鍋", "クリスマス", "冬コーデ", "ホットチョコレート", "温泉"],
    }
    return topics.get(season, [])


def _select_hashtags(category: str, count: int = 15) -> list[str]:
    """カテゴリに合わせたハッシュタグを選択"""
    selected = list(HASHTAGS["base"])

    category_lower = category.lower()
    if any(w in category_lower for w in ["ランチ", "ディナー", "カフェ", "ごはん", "弁当", "モーニング", "ブランチ"]):
        selected.extend(HASHTAGS["food"])
    if any(w in category_lower for w in ["コーデ", "ファッション", "ショッピング"]):
        selected.extend(HASHTAGS["fashion"])
    if any(w in category_lower for w in ["スキンケア", "コスメ", "ネイル", "美容"]):
        selected.extend(HASHTAGS["beauty"])
    if any(w in category_lower for w in ["旅行", "お出かけ", "散歩"]):
        selected.extend(HASHTAGS["travel"])

    selected.extend(HASHTAGS["lifestyle"])

    random.shuffle(selected)
    return selected[:count]


def generate_caption(category: str, extra_context: str = "") -> dict:
    """
    自然なInstagramキャプションを生成する。

    Returns:
        dict: {"caption": str, "hashtags": list[str], "image_prompt": str}
    """
    now = datetime.now()
    season = _get_season(now.month)
    seasonal_topics = _get_seasonal_topics(season)
    day_of_week = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"][now.weekday()]

    system_prompt = f"""あなたは{PERSONA['age']}歳の{PERSONA['location']}在住の{PERSONA['occupation']}、{PERSONA['name']}です。
性格: {PERSONA['personality']}

Instagramの投稿キャプションを書いてください。

【絶対ルール】
- AIが書いたとバレないように、完全に人間の20代女性として書く
- 完璧すぎる文章にしない。少しだけ崩した自然な口語体で
- 絵文字は1〜3個程度、使いすぎない
- 長すぎない（2〜4文程度）
- 宣伝っぽくしない
- 「〜だよ」「〜した！」「〜かも」など自然な語尾を使う
- たまに「笑」や「w」を使ってもいい
- 英語のフレーズを時々混ぜてもいい（グローバル意識）
- 今の季節は{season}、今日は{day_of_week}

【季節のトピック候補】
{', '.join(seasonal_topics)}

JSONで返してください:
{{"caption": "キャプション本文", "image_prompt": "この投稿に合う写真の英語での説明（後述のルール参照）"}}

【image_promptのルール】
- 英語で書く
- 「Japanese woman in her 20s」の一人称視点の写真を想定
- 顔は映さない（手元、料理、風景、足元、服のコーデなど）
- 自然光で撮った雰囲気
- iPhoneで撮ったような自然なスナップ写真風
- 具体的な場面を描写する"""

    user_prompt = f"カテゴリ: {category}"
    if extra_context:
        user_prompt += f"\n追加コンテキスト: {extra_context}"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        hashtags = _select_hashtags(category)

        return {
            "caption": result["caption"],
            "hashtags": hashtags,
            "image_prompt": result.get("image_prompt", ""),
            "category": category,
        }

    except Exception as e:
        logger.error(f"キャプション生成エラー: {e}")
        raise


def generate_caption_with_fallback(category: str) -> dict:
    """API失敗時のフォールバック付きキャプション生成"""
    try:
        return generate_caption(category)
    except Exception:
        logger.warning("OpenAI APIエラー。フォールバックキャプションを使用します。")
        fallback_captions = {
            "ランチ": "今日のランチ🍽 美味しかった〜！",
            "カフェ": "カフェでほっと一息 ☕",
            "朝カフェ": "朝活してきた！早起きって気持ちいい ☀",
            "モーニング": "おはよう〜 今日も一日がんばろ！",
            "朝の支度": "今日のメイク、なかなかいい感じかも 💄",
            "ディナー": "今日のごはん、大成功だった 🙌",
            "夜カフェ": "夜カフェでまったり中 ☕",
            "おうち時間": "おうちでのんびりな夜 🌙",
            "スキンケア": "今日もスキンケアがんばる 🧴",
            "お出かけ": "お出かけ日和だった！",
            "ショッピング": "かわいいの見つけちゃった 🛍",
        }
        caption = fallback_captions.get(category, f"今日の一枚 📸")
        hashtags = _select_hashtags(category)

        return {
            "caption": caption,
            "hashtags": hashtags,
            "image_prompt": "A casual iPhone snapshot of a daily life scene in Tokyo, natural lighting, first person perspective, no face visible",
            "category": category,
        }
