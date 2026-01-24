#!/usr/bin/env python3
"""
SNSログインスクリプト

LinkedInとXにログインしてセッションを保存します。
ブラウザが開いたら手動でログインし、完了後にブラウザを閉じてください。
"""

from playwright.sync_api import sync_playwright
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
BROWSER_DATA_DIR = SCRIPT_DIR / "browser-data-sns"

def main():
    print("=" * 50)
    print("🔐 SNS ログインスクリプト")
    print("=" * 50)
    print()
    print("ブラウザが開きます。以下の手順でログインしてください：")
    print("1. LinkedInにログイン")
    print("2. Xにログイン")
    print("3. 両方完了したらブラウザを閉じてください")
    print()
    print("=" * 50)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900}
        )

        # LinkedInタブ
        page1 = ctx.new_page()
        print("🌐 LinkedInを開いています...")
        page1.goto("https://www.linkedin.com")

        # Xタブ
        page2 = ctx.new_page()
        print("🌐 Xを開いています...")
        page2.goto("https://x.com")

        print()
        print("✅ 両方のタブでログインしてください")
        print("✅ 完了したらブラウザを閉じてください")
        print()

        # ブラウザが閉じられるまで待機
        try:
            while len(ctx.pages) > 0:
                ctx.pages[0].wait_for_timeout(1000)
        except:
            pass

        ctx.close()

    print("=" * 50)
    print("✅ セッション保存完了！")
    print("以下のコマンドでSNS投稿を実行できます：")
    print()
    print("  python sns_content_generator.py --post-sns")
    print()
    print("=" * 50)

if __name__ == "__main__":
    main()
