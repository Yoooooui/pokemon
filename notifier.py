import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

LINE_NOTIFY_API = "https://notify-api.line.me/api/notify"


# ---------------------------------------------------------------------------
# LINE Notify
# ---------------------------------------------------------------------------

def notify_line(lottery: dict) -> bool:
    token = os.getenv("LINE_NOTIFY_TOKEN")
    if not token:
        logger.warning("LINE_NOTIFY_TOKEN が設定されていません")
        return False

    message = (
        f"\n🎰 ポケモンセンター 抽選開始!\n"
        f"【{lottery['title']}】\n"
        f"期間: {lottery['period']}\n"
        f"URL: {lottery['url']}"
    )

    payload = {"message": message}
    if lottery.get("image"):
        payload["imageThumbnail"] = lottery["image"]
        payload["imageFullsize"] = lottery["image"]

    try:
        resp = requests.post(
            LINE_NOTIFY_API,
            headers={"Authorization": f"Bearer {token}"},
            data=payload,
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"LINE通知送信完了: {lottery['title']}")
        return True
    except requests.RequestException as e:
        logger.error(f"LINE通知の送信に失敗しました: {e}")
        return False


# ---------------------------------------------------------------------------
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
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    service = _get_calendar_service()
    if not service:
        return False

    # 抽選期間をパースできない場合は当日終日イベントを登録
    now = datetime.now()
    event = {
        "summary": f"🎰 ポケモン抽選: {lottery['title']}",
        "description": (
            f"ポケモンセンターで抽選が始まりました。\n\n"
            f"期間: {lottery['period']}\n"
            f"URL: {lottery['url']}"
        ),
        "start": {"date": now.strftime("%Y-%m-%d")},
        "end": {"date": (now + timedelta(days=1)).strftime("%Y-%m-%d")},
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
        "LINE": notify_line(lottery),
        "Gmail": notify_gmail(lottery),
        "Calendar": notify_calendar(lottery),
    }
    for channel, ok in results.items():
        status = "OK" if ok else "FAILED"
        logger.info(f"  {channel}: {status}")
