"""
提出用: template/index.html（ダークグリーン・レベル連動 UI）をサンプルデータでレンダリングし、
.card を PNG で docs/submission-screenshot.png に保存する。
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "template"


def render_html(data: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("index.html")
    return template.render(**data)

OUT = ROOT / "docs" / "submission-screenshot.png"
TMP_HTML = TEMPLATE_DIR / "_tmp_submission_preview.html"

# Episode・レベル・ツールタグが増える「遊び心」が伝わるデモデータ
SAMPLE = {
    "episode": 7,
    "title": "エメラルドの進捗バーが「記憶」になる日🌿",
    "date": "2026年5月9日（土）",
    "progress_percent": 68,
    "progress_level": 7,
    "trigger_title": "きっかけ",
    "trigger_desc": "記事を push したら自動で動く仕組みにした",
    "source_title": "素材",
    "source_desc": "自分語りの Markdown をそのままソースにした",
    "process_title": "処理",
    "process_desc": "Gemini→HTML→Playwright でカード画像化",
    "output_title": "届け先",
    "output_desc": "Slack へ Webhook。画像は公開 URL 経由で添付",
    "tools": [
        {"name": "Cursor", "icon": "⌨️", "desc": "実装"},
        {"name": "Claude", "icon": "🧠", "desc": "推敲"},
        {"name": "Gemini", "icon": "✨", "desc": "抽出"},
        {"name": "GitHub Actions", "icon": "⚙️", "desc": "自動化"},
        {"name": "Playwright", "icon": "📸", "desc": "撮影"},
        {"name": "Slack", "icon": "💬", "desc": "共有"},
        {"name": "Netlify", "icon": "🌐", "desc": "図解公開"},
        {"name": "Jinja2", "icon": "📐", "desc": "テンプレ"},
    ],
    "haru_message": "Episode が上がるたびにタグとスライダーの色が変わるって、ただの日報が RPG みてえだろ。記録が増えるほど装備欄が賑やかになるのが気に入ってるんだぜ。",
    "sakura_message": "AI ツールが増えていくのは、さつまいもが袋から増えていくみたいじゃっど。袋は同じでも中身がじわじわパワーアップしていく感じごわすね。",
    "today_essence": "「記録」がそのままビジュアルと装備リストになる",
    "today_essence_sub": "書いた文章はストックされ、カードのタグとレベルメーターに変換される。見せ場が増えるほど続けたくなるから、遊び心が続きの燃料になる。",
    "key_points": [
        "エピソード番号とツールタグで「今週のロードアウト」が一目でわかる",
        "LV スライダーで Glow 色がエメラルド→ゴールドへグラデーションする",
        "フル／ライト／1 行のモード切替で忙しい日も投稿できる設計",
        "Slack 用 PNG と提出用 URL で、仲間向けとスクール向けを分けられる",
    ],
    "body_paragraphs": [
        "ランディングのクリーム色カードから、ダークグリーン基調に振り切ってグリッドとノイズを敷いた。夜に書いても目が疲れにくく、「テックな修行ログ」感が出るようにしたんだぜ。",
        "レベルに応じてはるくん周りの発光色が変わるので、同じテンプレでも「今日はどの区間にいるか」が直感的に伝わる。装備タグは記事を書くたびに AI が整理して、コンテンツが育つほど見た目も賑やかになる。",
        "Slack の画像添付は公開 URL が要るので、アップロード先を挟んだ。提出用の図解は Netlify でホストして、講師にも URL 一発で見せられるようにしておいた。",
    ],
    "quote": "書いた回数が、そのままステータス画面になる。",
}


def main():
    html = render_html(SAMPLE)
    TMP_HTML.write_text(html, encoding="utf-8")
    url = TMP_HTML.as_uri()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 980, "height": 900})
            page.goto(url, wait_until="networkidle", timeout=90_000)
            page.wait_for_timeout(1500)
            card = page.locator(".card").first
            card.wait_for(state="visible", timeout=30_000)
            card.screenshot(path=str(OUT))
            browser.close()
    finally:
        TMP_HTML.unlink(missing_ok=True)

    print(f"[OK] {OUT}")


if __name__ == "__main__":
    main()
