# 薩摩AI修行日誌 - Cursor引き継ぎメモ

## プロジェクト概要

記事（Markdown）をGitHubにpushすると、自動でビジュアル報告カードを生成してSlackに送るツール。

## フォルダ構成

```
satsuma-ai-diary/
├── articles/          ← ここに記事を書く（Markdown）
│   └── 001_report.md  ← サンプル記事
├── template/
│   └── index.html     ← 報告カードのデザイン（ダークグリーン×エメラルド）
├── scripts/
│   └── generate.py    ← メインスクリプト（Gemini API → Jinja2 → Playwright → Slack）
├── output/            ← 生成された画像の保存先
├── .github/workflows/
│   └── report.yml     ← GitHub Actions自動トリガー
└── requirements.txt   ← 必要なPythonパッケージ
```

## 自動化の流れ

1. 記事を書く（articles/*.md）
2. GitHubにpush
3. GitHub Actionsが起動
4. generate.py が Gemini API に記事を送って情報を抽出
5. HTMLテンプレート（template/index.html）に流し込む（Jinja2）
6. Playwrightが画像として撮影
7. Slackに自動送信

## 4つのパーツ（システムの核心）

| パーツ | 意味 |
|--------|------|
| Trigger（きっかけ） | 記事を書いてpushしたら自動で動く |
| Source（素材） | 書いた文章がそのままデータになる |
| Process（処理） | AIが要約・デザインを代わりにやる |
| Output（届け先） | Slackに自動で届く＝発信ハードルゼロ |

## 次にやること（優先順）

1. **GitHub SecretsにGEMINI_API_KEYを登録**
   - 取得先: https://aistudio.google.com/app/apikey
   - 登録先: GitHubリポジトリ → Settings → Secrets and variables → Actions

2. **GitHub SecretsにSLACK_WEBHOOK_URLを登録**
   - 取得先: https://api.slack.com/apps でIncoming Webhook作成
   - 登録先: 同上

3. **動作確認**
   - articles/001_report.md を少し編集してGitHubにpush
   - GitHub Actionsのログを確認
   - Slackに通知が届けば成功

## GitHubリポジトリ

https://github.com/shosuke8631139/satsuma-ai-diary-

## 公開URL（Surge）

https://satsuma-ai-diary.surge.sh

## 環境変数（GitHub Secretsに登録するもの）

| 変数名 | 用途 |
|--------|------|
| GEMINI_API_KEY | 記事の解析・データ抽出 |
| SLACK_WEBHOOK_URL | Slackへの通知送信 |
| LINE_WEBHOOK_URL | （任意）LINEへの通知送信 |
