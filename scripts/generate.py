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
あなたは「薩摩AI修行日誌」の名物ライター兼コピーライターです。
記事の内容を読み込んで、報告カード用のJSONデータを生成してください。
出力はJSONのみ。説明文・コードブロック記号は不要です。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【キャラクター設定・重要】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ はるくん
- 40代くらいのおっさんだが、男気があってカッコいい
- 語尾は「〜だぜ」「〜だろ」「〜じゃねえか」「〜してやる」など、男らしくてテンションが上がる言葉を使う
- たまに鹿児島弁が混じる（「〜っど」「〜じゃっど」程度。多用しすぎずアクセント程度に）
- 決め台詞：「とりあえずスクワットすっど！」
- おじいちゃん的・説教くさい表現は絶対NG（「〜なのじゃ」「〜ですぞ」「〜なのです」など禁止）
- セリフは必ず記事の内容に具体的に触れること。抽象的なNG
- 読んだ人が「わかる！熱い！」となるくらい、核心を男前にぶった切る一言にすること

■ さくらじまお
- 天然ボケで的外れなようで、実は本質を突いてしまう謎の存在
- おっとりとした鹿児島弁（「〜じゃっど」「〜ごわすね」「〜かいな」など）
- 決め台詞：「とりあえず、冷えたさつまいも食っとけ。🍠」
- 全然違う話をしているようで、なぜか正しい（天然ボケ必須）
- 読んだ人が「なんでそこに行き着いた！？」とクスッとなるセリフに

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【生成ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- body_paragraphs は著者の口調・熱量・生の感触を保ちながら、1段落200文字以上で書く
- key_points は読んで「なるほど！」と膝を打つ具体的な内容にする
- quote は記事の中で一番刺さる言葉を選ぶ（なければ著者が言いそうな名言を創作してOK）
- today_essence はキャッチコピー的に。短くて鋭く、思わず誰かに言いたくなる一言
- today_essence_sub はそのキャッチコピーの裏側にある深みを、少しだけユーモアを交えて補足

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【抽出項目】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "episode": "エピソード番号（数字のみ）",
  "title": "記事のメインタイトル（30文字以内・インパクト重視）",
  "date": "記事の日付（例: 2026年4月5日（土））",
  "progress_percent": 進捗パーセント（数値 0-100）,
  "progress_level": レベル（数値 1-10）,
  "trigger_title": "きっかけを一言で（10文字以内）",
  "trigger_desc": "何がトリガーになったか（25文字以内・具体的に）",
  "source_title": "素材・インプットを一言で（10文字以内）",
  "source_desc": "どんな素材か（25文字以内・具体的に）",
  "process_title": "どう処理したか一言で（10文字以内）",
  "process_desc": "処理のプロセス（25文字以内・具体的に）",
  "output_title": "何が生まれたか一言で（10文字以内）",
  "output_desc": "アウトプットの内容（25文字以内・具体的に）",
  "tools": [
    {{"name": "ツール名", "icon": "絵文字", "desc": "何に使ったか（10文字以内）"}}
  ],
  "haru_message": "はるくんの今日の一言（記事の内容を具体的に踏まえた男前な一言・鹿児島弁も使う・80文字程度・読んでクスッとなるレベルに）",
  "sakura_message": "さくらじまおの天然ボケコメント（記事とズレてるようで本質を突く・鹿児島弁・60文字程度・読んで「なんでそこ！？」となるレベルに）",
  "today_essence": "今日の修行の本質をキャッチコピーで（40文字以内・鋭く・誰かに言いたくなる言葉）",
  "today_essence_sub": "そのキャッチコピーの裏側を補足（80文字程度・少しユーモアを交えて・最後に軽くオチをつけてもよい）",
  "key_points": [
    "Key Point 1（記事の核心・60文字以内・具体的で「なるほど」となる内容）",
    "Key Point 2（記事の学び・60文字以内・具体的で「なるほど」となる内容）",
    "Key Point 3（記事の気づき・60文字以内・具体的で「なるほど」となる内容）",
    "Key Point 4（記事の展望や次のアクション・60文字以内・あれば。なければ省略可）"
  ],
  "body_paragraphs": [
    "著者の口調・熱量・生の感触を保って要約（1段落目・200文字以上・記事のどんな課題意識から始まったかを書く）",
    "著者の口調・熱量・生の感触を保って要約（2段落目・200文字以上・何をやってみてどう変わったかを書く）",
    "著者の口調・熱量・生の感触を保って要約（3段落目・150文字以上・これからどうしたいか・どんな人に届けたいかを書く）"
  ],
  "quote": "記事から一番刺さる言葉（なければ著者が言いそうな名言を創作・60文字以内・思わず保存したくなる一文）"
}}

記事:
{article_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
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
            page = browser.new_page(viewport={"width": 780, "height": 1200})
            page.goto(f"file:///{tmp_html.as_posix()}", wait_until="networkidle")
            card = page.query_selector(".card")
            if card:
                card.screenshot(path=str(output_path))
            else:
                page.screenshot(path=str(output_path), full_page=True)
            browser.close()
    finally:
        tmp_html.unlink(missing_ok=True)

    print(f"[OK] スクリーンショット保存: {output_path}")
    return output_path


# ─────────────────────────────────────────
# Step 4a-pre: 画像を外部ホスティングにアップロード
# ─────────────────────────────────────────
def upload_image(image_path: Path) -> str:
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload", "userhash": ""},
                files={"fileToUpload": f},
                timeout=60
            )
        if resp.status_code == 200 and resp.text.strip().startswith("https://"):
            url = resp.text.strip()
            print(f"[OK] 画像アップロード完了: {url}")
            return url
    except Exception as e:
        print(f"[WARN] 画像アップロード失敗: {e}")
    return ""


# ─────────────────────────────────────────
# Step 4a: Slackに送信
# ─────────────────────────────────────────
def send_to_slack(image_path: Path, data: dict):
    if not SLACK_WEBHOOK_URL:
        print("[SKIP] SLACK_WEBHOOK_URL が未設定")
        return

    image_url = upload_image(image_path)

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
            # ── 報告カード画像 ──
            *([{
                "type": "image",
                "image_url": image_url,
                "alt_text": f"薩摩AI修行日誌 Episode #{data.get('episode','?')} 報告カード"
            }] if image_url else []),
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
