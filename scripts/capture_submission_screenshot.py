"""
提出用: ルート index.html の報告カード UI を PNG で docs/ に保存する。
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "docs" / "submission-screenshot.png"


def main():
    if not INDEX.exists():
        raise SystemExit(f"見つかりません: {INDEX}")

    url = INDEX.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.goto(url, wait_until="networkidle", timeout=60_000)
        card = page.locator(".main-card").first
        card.wait_for(state="visible", timeout=30_000)
        card.screenshot(path=str(OUT))
        browser.close()

    print(f"[OK] {OUT}")


if __name__ == "__main__":
    main()
