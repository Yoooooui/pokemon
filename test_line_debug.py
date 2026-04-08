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
    print(f"レスポンス: {resp.text[:300]}")
    token = resp.json().get("access_token", "") if resp.ok else ""
except Exception as e:
    print(f"接続エラー: {e}")
    token = ""

if not token:
    print("\n❌ トークン取得失敗。Channel ID/Secretを確認してください。")
    exit(1)

print(f"\n✅ トークン取得成功: {token[:20]}...")

print("\n=== Step 2: メッセージ送信 ===")
user_id = user_ids.split(",")[0].strip()
print(f"送信先: {user_id}")

try:
    resp2 = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "to": user_id,
            "messages": [{"type": "text", "text": "テスト送信 ✅"}],
        },
        timeout=15,
    )
    print(f"HTTPステータス: {resp2.status_code}")
    print(f"レスポンス: {resp2.text[:300]}")
    if resp2.ok:
        print("\n✅ 送信成功！LINEを確認してください。")
    else:
        data = resp2.json()
        print(f"\n❌ 送信失敗: {data.get('message', '不明なエラー')}")
        if "Not friend" in resp2.text or "user" in resp2.text.lower():
            print("→ Botを友だち追加してから再試行してください。")
except Exception as e:
    print(f"接続エラー: {e}")
