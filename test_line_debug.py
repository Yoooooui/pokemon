"""LINE接続の詳細デバッグ"""
from dotenv import load_dotenv
import os, requests, json

load_dotenv()

channel_id = os.getenv("LINE_CHANNEL_ID")
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
user_ids = os.getenv("LINE_USER_IDS", "")

print("=== Step 1: トークン取得 ===")
try:
    resp = requests.post(
        "https://api.line.me/v2/oauth/accessToken",
        data={
            "grant_type": "client_credentials",
            "client_id": channel_id,
            "client_secret": channel_secret,
        },
        timeout=15,
    )
    print(f"HTTPステータス: {resp.status_code}")
    token = resp.json().get("access_token", "") if resp.ok else ""
except Exception as e:
    print(f"接続エラー: {e}")
    token = ""

if not token:
    print("❌ トークン取得失敗")
    exit(1)
print(f"✅ トークン取得成功: {token[:20]}...")

print("\n=== Step 2: Botアカウント情報を確認 ===")
try:
    r = requests.get(
        "https://api.line.me/v2/bot/info",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    print(f"HTTPステータス: {r.status_code}")
    print(f"レスポンス: {r.text[:500]}")
except Exception as e:
    print(f"エラー: {e}")

print("\n=== Step 3: メッセージ送信 ===")
user_id = user_ids.split(",")[0].strip()
print(f"送信先: {user_id}")
try:
    r2 = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": "テスト ✅"}]},
        timeout=15,
    )
    print(f"HTTPステータス: {r2.status_code}")
    print(f"レスポンス: {r2.text[:300]}")
    if r2.ok:
        print("✅ 送信成功！")
except Exception as e:
    print(f"エラー: {e}")

