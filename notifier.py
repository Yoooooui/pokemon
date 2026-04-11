import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Discord Webhook
# ---------------------------------------------------------------------------

def notify_discord(lottery: dict) -> bool:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL が設定されていません")
        return False

    content = (
        f"🎰 **ポケモンセンター 抽選開始！**\n"
        f"**{lottery['title']}**\n"
        f"期間: {lottery['period']}\n"
        f"{lottery['url']}"
    )

    try:
        resp = requests.post(
            webhook_url,
            json={"content": content},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Discord通知送信完了: {lottery['title']}")
        return True
    except requests.RequestException as e:
        logger.error(f"Discord通知の送信に失敗しました: {e}")
        return False
# Gmail
# ---------------------------------------------------------------------------

def notify_gmail(lottery: dict) -> bool:
    gmail_address = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    to_address = os.getenv("NOTIFY_EMAIL_TO", gmail_address)

    if not gmail_address or not app_password:
        logger.warning("GMAIL_ADDRESS または GMAIL_APP_PASSWORD が設定されていません")
        return False

    subject = f"【ポケモンセンター】抽選開始: {lottery['title']}"
    body = f"""\
ポケモンセンターで新しい抽選が始まりました！

タイトル: {lottery['title']}
期間:     {lottery['period']}
URL:      {lottery['url']}

検出日時: {lottery['found_at']}
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain", "utf-8"))

    html_body = f"""\
<html><body>
<h2>🎰 ポケモンセンター 抽選開始！</h2>
<table>
  <tr><td><b>タイトル</b></td><td>{lottery['title']}</td></tr>
  <tr><td><b>期間</b></td><td>{lottery['period']}</td></tr>
  <tr><td><b>URL</b></td><td><a href="{lottery['url']}">{lottery['url']}</a></td></tr>
  <tr><td><b>検出日時</b></td><td>{lottery['found_at']}</td></tr>
</table>
</body></html>
"""
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_address, app_password)
            smtp.sendmail(gmail_address, to_address, msg.as_bytes())
        logger.info(f"Gmail通知送信完了: {lottery['title']}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"Gmail通知の送信に失敗しました: {e}")
        return False


# ---------------------------------------------------------------------------
# Google Calendar
# ---------------------------------------------------------------------------

def _get_calendar_service():
    """Google Calendar APIサービスを取得する"""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_FILE = "token.pickle"
    CREDENTIALS_FILE = "credentials.json"

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                logger.error(
                    f"{CREDENTIALS_FILE} が見つかりません。"
                    "Google Cloud ConsoleからOAuth2認証情報をダウンロードしてください。"
                )
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            import pickle as _pickle
            _pickle.dump(creds, f)

    return build("calendar", "v3", credentials=creds)


def notify_calendar(lottery: dict) -> bool:
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "qitengyangyi93@gmail.com")

    service = _get_calendar_service()
    if not service:
        return False

    # 抽選期間をパースできない場合は当日終日イベントを登録（Asia/Tokyo固定）
    import zoneinfo
    tz = zoneinfo.ZoneInfo("Asia/Tokyo")
    now = datetime.now(tz)
    event = {
        "summary": f"🎰 ポケモン抽選: {lottery['title']}",
        "description": (
            f"ポケモンセンターで抽選が始まりました！\n\n"
            f"期間: {lottery['period']}\n"
            f"URL: {lottery['url']}\n\n"
            f"検出日時: {now.strftime('%Y/%m/%d %H:%M')} (JST)"
        ),
        "start": {"date": now.strftime("%Y-%m-%d"), "timeZone": "Asia/Tokyo"},
        "end": {"date": (now + timedelta(days=1)).strftime("%Y-%m-%d"), "timeZone": "Asia/Tokyo"},
        "source": {"title": "ポケモンセンター抽選通知", "url": lottery["url"]},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},
                {"method": "email", "minutes": 60},
            ],
        },
    }

    try:
        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        logger.info(
            f"Googleカレンダー登録完了: {lottery['title']} -> {created.get('htmlLink')}"
        )
        return True
    except Exception as e:
        logger.error(f"Googleカレンダーへの登録に失敗しました: {e}")
        return False


# ---------------------------------------------------------------------------
# 全通知をまとめて実行
# ---------------------------------------------------------------------------

def notify_all(lottery: dict) -> None:
    logger.info(f"通知送信開始: {lottery['title']}")
    results = {
        "Discord": notify_discord(lottery),
        "Gmail": notify_gmail(lottery),
        "Calendar": notify_calendar(lottery),
    }
    for channel, ok in results.items():
        status = "OK" if ok else "FAILED"
        logger.info(f"  {channel}: {status}")


# ---------------------------------------------------------------------------
# ポケカ高騰予兆通知
# ---------------------------------------------------------------------------

def notify_card_surge_discord(cards: list) -> bool:
    """高騰予兆カードをDiscordに通知"""
    from card_analyzer import ALERT_SURGE, ALERT_HIGH
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return False

    surge = [c for c in cards if c.alert_level == ALERT_SURGE]
    high  = [c for c in cards if c.alert_level == ALERT_HIGH]
    if not surge and not high:
        return True

    lines = ["🎴 **ポケカ価格速報**"]
    if surge:
        lines.append("🚨 **海外価格が急騰！日本価格も近く上昇予測**")
        for c in surge[:3]:
            lines.append(
                f"▶ **{c.name_ja}**（{c.name_en}）\n"
                f"　海外: ${c.tcg_market_usd} (+{c.price_change_pct:.0f}%) "
                f"/ 日本: {'¥'+f'{c.japan_price_jpy:,}' if c.japan_price_jpy else 'データなし'}"
            )
    if high:
        lines.append("⚠️ **海外が日本の2倍以上のカード**")
        for c in high[:3]:
            lines.append(f"▶ **{c.name_ja}** — 海外 ${c.tcg_market_usd} / ×{c.arbitrage_ratio:.1f}")

    try:
        resp = requests.post(
            webhook_url,
            json={"content": "\n".join(lines)},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"ポケカ高騰予兆Discord通知完了 ({len(surge)}件急騰/{len(high)}件予兆)")
        return True
    except requests.RequestException as e:
        logger.error(f"ポケカ高騰予兆Discord通知失敗: {e}")
        return False


def notify_card_surge_gmail(cards: list) -> bool:
    """高騰予兆カードをGmailに通知"""
    from card_analyzer import ALERT_SURGE, ALERT_HIGH
    gmail_address = os.getenv("GMAIL_ADDRESS")
    app_password  = os.getenv("GMAIL_APP_PASSWORD")
    to_address    = os.getenv("NOTIFY_EMAIL_TO", gmail_address)
    if not gmail_address or not app_password:
        return False

    surge = [c for c in cards if c.alert_level == ALERT_SURGE]
    high  = [c for c in cards if c.alert_level == ALERT_HIGH]
    if not surge and not high:
        return True

    subject = f"【ポケカ価格速報】急騰{len(surge)}件 / 予兆{len(high)}件"

    rows = ""
    for c in surge + high:
        badge = "🚨 急騰" if c.alert_level == ALERT_SURGE else "⚠️ 予兆"
        jp = f"¥{c.japan_price_jpy:,}" if c.japan_price_jpy else "-"
        chg = f"+{c.price_change_pct:.0f}%" if c.prev_tcg_usd > 0 else "初回"
        rows += (
            f"<tr><td>{badge}</td><td>{c.name_ja}<br><small>{c.name_en}</small></td>"
            f"<td>${c.tcg_market_usd} ({chg})</td><td>{jp}</td>"
            f"<td>×{c.arbitrage_ratio:.1f}</td>"
            f"<td><a href='{c.tcg_url}'>見る</a></td></tr>"
        )

    html = f"""<html><body>
<h2>🎴 ポケカ海外価格 高騰予兆レポート</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr style="background:#f0f0f0">
    <th>状態</th><th>カード名</th><th>海外価格</th><th>日本価格</th><th>倍率</th><th>リンク</th>
  </tr>
  {rows}
</table>
<p style="color:#888;font-size:0.85em">
海外価格が先行上昇すると、数週間〜数ヶ月後に日本価格も追随する傾向があります。
</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = to_address
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_address, app_password)
            smtp.sendmail(gmail_address, to_address, msg.as_bytes())
        logger.info("ポケカ高騰予兆Gmail通知完了")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"ポケカ高騰予兆Gmail通知失敗: {e}")
        return False
