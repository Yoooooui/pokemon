"""LINEの送信テスト"""
from dotenv import load_dotenv
load_dotenv()

from notifier import notify_line

test_lottery = {
    "title": "テスト送信",
    "period": "2026年4月6日",
    "url": "https://www.pokemoncenter-online.com/",
    "image": "",
}

print("LINE通知テスト中...")
ok = notify_line(test_lottery)
print("成功！" if ok else "失敗。ログを確認してください。")
