# ポケモンセンター抽選通知システム

ポケモンセンターオンラインで新しい抽選が開始されたら、LINE・Gmail・Googleカレンダーに自動通知します。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、各値を設定します。

```bash
cp .env.example .env
```

#### LINE Notify トークンの取得
1. [LINE Notify](https://notify-bot.line.me/ja/) にアクセス
2. 「マイページ」→「トークンを発行する」
3. 通知先のトークルームを選択してトークンをコピー
4. `.env` の `LINE_NOTIFY_TOKEN` に貼り付け

#### Gmail アプリパスワードの取得
1. Googleアカウントで2段階認証を有効化
2. [アプリパスワード](https://myaccount.google.com/apppasswords) を生成
3. `.env` の `GMAIL_APP_PASSWORD` に貼り付け

#### Google Calendar の設定
1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. Google Calendar API を有効化
3. OAuth 2.0 クライアントID（デスクトップアプリ）を作成
4. `credentials.json` をダウンロードしてこのディレクトリに配置
5. 以下のコマンドで認証を完了させる:

```bash
python main.py --setup
```

カレンダーIDは「設定と共有」→「カレンダーの統合」→「カレンダーID」で確認できます。  
自分のメインカレンダーの場合は `primary` のままでOKです。

### 3. 動作確認

```bash
# 1回だけチェック
python main.py --once

# 定期監視（デフォルト30分ごと）
python main.py
```

## ファイル構成

```
pokemon/
├── main.py              # エントリーポイント・スケジューラー
├── scraper.py           # ポケモンセンターのスクレイピング
├── notifier.py          # LINE / Gmail / Googleカレンダー通知
├── requirements.txt     # 依存パッケージ
├── .env.example         # 環境変数のサンプル
├── .env                 # 実際の環境変数（要作成、gitignore済み）
├── credentials.json     # Google OAuth認証情報（要配置、gitignore済み）
├── token.pickle         # Google認証トークン（自動生成）
├── seen_lotteries.json  # 通知済み抽選のID記録（自動生成）
└── lottery_monitor.log  # ログファイル（自動生成）
```

## 監視間隔の変更

`.env` の `CHECK_INTERVAL_MINUTES` を変更します（デフォルト: 30分）。

```
CHECK_INTERVAL_MINUTES=15
```
