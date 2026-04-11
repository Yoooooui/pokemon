#!/bin/bash
cat > .env << 'EOF'
DISCORD_WEBHOOK_URL=YOUR_WEBHOOK_URL_HERE
GMAIL_ADDRESS=qitengyangyi93@gmail.com
GMAIL_APP_PASSWORD=
NOTIFY_EMAIL_TO=qitengyangyi93@gmail.com
GOOGLE_CALENDAR_ID=qitengyangyi93@gmail.com
CHECK_INTERVAL_MINUTES=30
EOF
echo ".env を作成しました"
pip3 install -r requirements.txt -q
echo "パッケージインストール完了"
echo ""
echo "次のステップ:"
echo "1. .env の DISCORD_WEBHOOK_URL を設定してください"
echo "2. python3 test_discord.py でテスト"
