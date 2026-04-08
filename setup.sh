#!/bin/bash
cat > .env << 'EOF'
LINE_CHANNEL_ID=2009698948
LINE_CHANNEL_SECRET=5b2308a6fba3ca7945c19447e462c476
LINE_USER_IDS=Uee667eef4735df44dc626ce338e0d8fc
GMAIL_ADDRESS=qitengyangyi93@gmail.com
GMAIL_APP_PASSWORD=
NOTIFY_EMAIL_TO=qitengyangyi93@gmail.com
GOOGLE_CALENDAR_ID=qitengyangyi93@gmail.com
CHECK_INTERVAL_MINUTES=30
EOF
echo ".env を作成しました"
pip3 install -r requirements.txt -q
echo "パッケージインストール完了"
python3 test_line_debug.py
