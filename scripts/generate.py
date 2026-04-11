"""
薩摩AI修行日誌 - 自動生成スクリプト
処理フロー:
  1. 記事MarkdownをGemini APIで解析・データ抽出
  2. HTMLテンプレートにデータを注入
  3. PlaywrightでPNGスクリーンショット撮影
  4. Slack / LINE Webhookに画像を送信
"""

import os
import sys
import json
import re
import base64
import shutil
import tempfile
from pathlib import Path

from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
import requests


# ─────────────────────────────────────────
# 設定
# ─────────────────────────────────────────
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
LINE_WEBHOOK_URL  = os.environ.get("LINE_WEBHOOK_URL", "")

ROOT_DIR     = Path(__file__).parent.parent
TEMPLATE_DIR = ROOT_DIR / "template"
OUTPUT_DIR   = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────
# Step 1: Gemini API で記事を解析
# ─────────────────────────────────────────
def extract_data_with_gemini(article_text: str) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
あなたはAIスクールの学習報告アシスタントです。
以下の記事から、報告カード用データをJSON形式で正確に抽出してください。
出力はJSONのみ。説明文・コードブロック記号は不要です。

キャラクター設定:
- はるくん: おっさんだけど楽しみながら学ぶ探究者。さっぱりした男らしさ。たまに鹿児島弁。決め台詞「とりあえずスクワットすっど」
- さくらじまお: 天然ボケで的外れなんだけど可愛げがあって結果的に正しい。おっとり鹿児島弁。決め台詞「とりあえず、冷えたさつまいも食っとけ」

抽出項目:
{{
  "episode": "エピソード番号（数字のみ）",
  "title": "記事のメインタイトル（30文字以内）",
  "date": "記事の日付（例: 2026年4月5日（土））",
  "progress_percent": 進捗パーセント（数値 0-100）,
  "progress_level": レベル（数値）,
  "trigger_title": "トリガーのタイトル（10文字以内）",
  "trigger_desc": "トリガーの説明（20文字以内）",
  "source_title": "ソースのタイトル（10文字以内）",
  "source_desc": "ソースの説明（20文字以内）",
  "process_title": "処理のタイトル（10文字以内）",
  "process_desc": "処理の説明（20文字以内）",
  "output_title": "アウトプットのタイトル（10文字以内）",
  "output_desc": "アウトプットの説明（20文字以内）",
  "tools": [
    {{"name": "ツール名", "icon": "絵文字", "desc": "用途（6文字以内）"}}
  ],
  "haru_message": "はるくんのひと言（さっぱり男らしく、たまに鹿児島弁、60文字以内）",
  "sakura_message": "さくらじまおの天然ボケコメント（おっとり鹿児島弁、結果的に正しい、40文字以内）"
}}

記事:
{article_text}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    raw = response.text.strip()

    # コードブロック除去
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


# ─────────────────────────────────────────
# Step 2: HTMLテンプレートにデータを注入
# ─────────────────────────────────────────
def render_html(data: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("index.html")
    return template.render(**data)


# ─────────────────────────────────────────
# Step 3: PlaywrightでPNG撮影
# ─────────────────────────────────────────
def capture_screenshot(html_content: str, output_path: Path) -> Path:
    # 一時HTMLファイルに書き出し（template/の画像を参照するため同フォルダに置く）
    tmp_html = TEMPLATE_DIR / "_tmp_render.html"
    tmp_html.write_text(html_content, encoding="utf-8")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 750, "height": 900})
            page.goto(f"file:///{tmp_html.as_posix()}", wait_until="networkidle")
            # カード要素だけをクロップ
            card = page.query_selector(".card")
            if card:
                card.screenshot(path=str(output_path))
            else:
                page.screenshot(path=str(output_path), full_page=False)
            browser.close()
    finally:
        tmp_html.unlink(missing_ok=True)

    print(f"[OK] スクリーンショット保存: {output_path}")
    return output_path


# ─────────────────────────────────────────
# Step 4a: Slackに送信
# ─────────────────────────────────────────
def send_to_slack(image_path: Path, data: dict):
    if not SLACK_WEBHOOK_URL:
        print("[SKIP] SLACK_WEBHOOK_URL が未設定")
        return

    tools_text = "　".join(
        [f"{t.get('icon','')} {t.get('name','')}" for t in data.get("tools", [])]
    )

    payload = {
        "username": "サツマ日記ロボ",
        "icon_emoji": ":volcano:",
        "blocks": [
            # ── ヘッダー ──
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🌋 薩摩AI修行日誌 Episode #{data.get('episode','?')}",
                    "emoji": True
                }
            },
            # ── タイトル＆日付 ──
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{data.get('title', '')}*\n"
                        f"📅 {data.get('date', '')}\n"
                        f"📈 進捗: *{data.get('progress_percent', '?')}%*　Lv. {data.get('progress_level', '?')}"
                    )
                }
            },
            {"type": "divider"},
            # ── 4つのサイクル ──
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*🔥 {data.get('trigger_title','')}*\n"
                            f"{data.get('trigger_desc','')}"
                        )
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*📥 {data.get('source_title','')}*\n"
                            f"{data.get('source_desc','')}"
                        )
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*⚙️ {data.get('process_title','')}*\n"
                            f"{data.get('process_desc','')}"
                        )
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*📤 {data.get('output_title','')}*\n"
                            f"{data.get('output_desc','')}"
                        )
                    }
                ]
            },
            {"type": "divider"},
            # ── 使ったツール ──
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🛠️ *今日の武器庫*\n{tools_text}" if tools_text else "🛠️ *今日の武器庫*\n（データなし）"
                }
            },
            {"type": "divider"},
            # ── はるくんのセリフ ──
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"💬 *はるくん*\n>{data.get('haru_message', '')}"
                }
            },
            # ── さくらじまおのセリフ ──
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🌋 *さくらじまお*\n>{data.get('sakura_message', 'とりあえず、冷えたさつまいも食っとけ。🍠')}"
                }
            },
            # ── フッター ──
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "サツマ日記ロボ 🤖 powered by Gemini × GitHub Actions"
                    }
                ]
            }
        ]
    }

    resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    print(f"[Slack] ステータス: {resp.status_code}")
    if resp.status_code != 200:
        print(f"[Slack] レスポンス: {resp.text}")


# ─────────────────────────────────────────
# Step 4b: LINEに送信
# ─────────────────────────────────────────
def send_to_line(image_path: Path, data: dict):
    if not LINE_WEBHOOK_URL:
        print("[SKIP] LINE_WEBHOOK_URL が未設定")
        return

    # LINE Notify の場合
    headers = {"Authorization": f"Bearer {LINE_WEBHOOK_URL}"}
    with open(image_path, "rb") as f:
        files = {"imageFile": f}
        params = {"message": f"\n薩摩AI修行日誌 Episode #{data['episode']}\n{data['title']}\n{data['date']}"}
        resp = requests.post(
            "https://notify-api.line.me/api/notify",
            headers=headers,
            params=params,
            files=files,
            timeout=30
        )
    print(f"[LINE] ステータス: {resp.status_code}")


# ─────────────────────────────────────────
# メイン
# ─────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("使い方: python generate.py <記事ファイルのパス>")
        sys.exit(1)

    article_path = Path(sys.argv[1])
    if not article_path.exists():
        print(f"エラー: ファイルが見つかりません: {article_path}")
        sys.exit(1)

    article_text = article_path.read_text(encoding="utf-8")
    article_stem  = article_path.stem
    output_path   = OUTPUT_DIR / f"{article_stem}.png"

    print(f"[1/4] Gemini APIで記事を解析中...")
    data = extract_data_with_gemini(article_text)
    print(f"      → Episode #{data.get('episode')} / {data.get('title')}")

    print(f"[2/4] HTMLテンプレートにデータを注入中...")
    html = render_html(data)

    print(f"[3/4] Playwrightでスクリーンショット撮影中...")
    capture_screenshot(html, output_path)

    print(f"[4/4] 通知送信中...")
    send_to_slack(output_path, data)
    send_to_line(output_path, data)

    print(f"\n完了！ → {output_path}")


if __name__ == "__main__":
    main()
