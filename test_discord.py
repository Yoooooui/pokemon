"""Discord Webhook テスト"""
from dotenv import load_dotenv
import os, requests

load_dotenv()

webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
if not webhook_url:
    print("❌ DISCORD_WEBHOOK_URL が .env に設定されていません")
    exit(1)

print("Discord通知テスト中...")
resp = requests.post(
    webhook_url,
    json={"content": "🎰 **テスト送信** ✅\nポケモンセンター抽選通知システムが正常に動作しています！"},
    timeout=15,
)
if resp.ok:
    print("✅ 成功！Discordを確認してください。")
else:
    print(f"❌ 失敗: {resp.status_code} {resp.text}")
