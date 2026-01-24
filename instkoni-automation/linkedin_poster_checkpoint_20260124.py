#!/usr/bin/env python3
"""
LinkedIn自動投稿スクリプト v3
- 最初にインフォグラフィック選択
- 画像プレビュー機能
- スケジュール設定自動化
- クリップボード経由のテキスト入力
"""

import asyncio
import sys
import subprocess
import pyperclip
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# パス設定
SCRIPT_DIR = Path(__file__).parent.resolve()
BROWSER_DATA_DIR = SCRIPT_DIR / "browser-data-sns"
INFOGRAPHIC_DIR = SCRIPT_DIR / "../articles/infographic"
OUTPUT_DIR = SCRIPT_DIR / "outputs"

# 投稿コンテンツ（URLなし）
CONTENT_NO_URL = """🎯 ChatGPT Goは本当に「ビジネス革命」なのか？

※2026年1月、OpenAIが発表した月額8ドルの新プラン「ChatGPT Go」について、マーケティング戦略の視点から分析しました。

📌 「ビジネスパーソンのためのAI」という触れ込みで登場したChatGPT Go。しかし、実際に企業の現場で活用されるシーンを想像するのは難しいかもしれません。

📌 本気でAIを業務に組み込む企業は、すでにPlus以上を導入済み。API利用はプランではなくモデル課金。つまり、このプランの真のターゲットは「ビジネス」ではないのです。

✅ 本質①：月額20ドルのPlusを使わない理由がない企業にとって、Goプランは選択肢にならない

✅ 本質②：OpenAIの狙いは「無料ユーザーの有料化」と「広告収益モデルの確立」

✅ 本質③：2026年2月から広告テスト開始予定。GoogleやMetaと同じプラットフォームビジネスへの転換が始まっている

✅ 真に価値があるのは：AIスキルを身につけたい学生・若手社会人、趣味や副業でAIを活用したい個人層

メディアの「革命」という言葉に踊らされず、裏にあるビジネスロジックを冷静に読み解く視点が、AI時代を生き抜く上で最も重要なスキルではないでしょうか。

🔗 記事はこちら"""

URL_TEXT = "\nhttps://note.com/instkoni/n/nfbf576f13775"


def select_image_folder() -> tuple[list[str], str]:
    """画像フォルダを選択し、画像リストを返す"""
    print("\n" + "=" * 60)
    print("📁 インフォグラフィック選択")
    print("=" * 60)

    # フォルダ一覧を取得（タイムスタンプ付きフォルダのみ）
    folders = []
    for item in INFOGRAPHIC_DIR.iterdir():
        if item.is_dir() and item.name[0].isdigit():
            folders.append(item)

    # タイムスタンプでソート（降順）
    folders.sort(key=lambda x: x.name, reverse=True)

    if not folders:
        print("❌ 画像フォルダが見つかりません")
        return [], ""

    # 一覧表示
    print("\n利用可能なフォルダ:")
    for i, folder in enumerate(folders[:10]):
        # フォルダ内の画像数を数える
        images = list(folder.glob("*.png")) + list(folder.glob("*.jpg"))
        # フォルダ名からタイトルを抽出
        name_parts = folder.name.split("_", 2)
        title = name_parts[2] if len(name_parts) > 2 else folder.name
        print(f"  [{i+1}] {title[:50]}... ({len(images)}枚)")

    print()

    # 選択
    while True:
        try:
            choice = input("番号を入力 (Enterで最新[1]を選択): ").strip()
            if choice == "":
                selected = folders[0]
            else:
                idx = int(choice) - 1
                if 0 <= idx < len(folders):
                    selected = folders[idx]
                else:
                    print("⚠️ 無効な番号です")
                    continue
            break
        except ValueError:
            print("⚠️ 数字を入力してください")

    # 画像ファイルを取得
    images = list(selected.glob("*.png")) + list(selected.glob("*.jpg"))
    images.sort(key=lambda x: x.name)

    # 画像一覧を表示
    print(f"\n✅ 選択フォルダ: {selected.name}")
    print(f"\n📷 添付される画像 ({len(images)}枚):")
    for i, img in enumerate(images[:5]):
        print(f"   [{i+1}] {img.name}")

    if len(images) > 5:
        print(f"   ... 他{len(images) - 5}枚（最初の5枚のみ添付）")

    # 確認
    print()
    confirm = input("これでよろしいですか？ (Enter=OK / n=キャンセル): ").strip().lower()
    if confirm == "n":
        print("キャンセルしました")
        return [], ""

    image_paths = [str(img) for img in images[:5]]
    folder_name = selected.name

    return image_paths, folder_name


def select_image_folder_auto(folder_num: int) -> tuple[list[str], str]:
    """フォルダ番号を指定して自動選択"""
    print("\n" + "=" * 60)
    print("📁 インフォグラフィック自動選択")
    print("=" * 60)

    # フォルダ一覧を取得
    folders = []
    for item in INFOGRAPHIC_DIR.iterdir():
        if item.is_dir() and item.name[0].isdigit():
            folders.append(item)

    folders.sort(key=lambda x: x.name, reverse=True)

    if not folders:
        print("❌ 画像フォルダが見つかりません")
        return [], ""

    # 指定番号で選択
    idx = folder_num - 1
    if idx < 0 or idx >= len(folders):
        print(f"⚠️ 無効なフォルダ番号: {folder_num}")
        return [], ""

    selected = folders[idx]

    # 画像ファイルを取得
    images = list(selected.glob("*.png")) + list(selected.glob("*.jpg"))
    images.sort(key=lambda x: x.name)

    # 画像一覧を表示
    print(f"\n✅ 選択フォルダ: {selected.name}")
    print(f"\n📷 添付される画像 ({len(images)}枚):")
    for i, img in enumerate(images[:5]):
        print(f"   [{i+1}] {img.name}")

    if len(images) > 5:
        print(f"   ... 他{len(images) - 5}枚（最初の5枚のみ添付）")

    image_paths = [str(img) for img in images[:5]]
    folder_name = selected.name

    return image_paths, folder_name


def get_schedule_settings() -> int:
    """スケジュール設定を取得"""
    print("\n" + "=" * 60)
    print("📅 スケジュール設定")
    print("=" * 60)

    while True:
        try:
            days_input = input("何日後に投稿予約？ (デフォルト: 7): ").strip()
            if days_input == "":
                return 7
            days = int(days_input)
            if days < 1:
                print("⚠️ 1日以上を指定してください")
                continue
            return days
        except ValueError:
            print("⚠️ 数字を入力してください")


async def post_to_linkedin(images: list[str], schedule_days: int = 7):
    """LinkedInに投稿"""
    schedule_time = datetime.now() + timedelta(days=schedule_days)

    print("\n" + "=" * 60)
    print("📘 LinkedIn自動投稿開始")
    print("=" * 60)
    print(f"📅 予約日時: {schedule_time.strftime('%Y年%m月%d日 %H:%M')}")
    print(f"📷 画像数: {len(images)}枚")
    print("=" * 60)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900}
        )

        page = await context.new_page()

        try:
            print("\n🌐 LinkedInにアクセス中...", flush=True)
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            # Step 1: 投稿モーダルを開く
            print("\n📝 Step 1/11: 投稿モーダルを開く...", flush=True)
            await page.locator('button:has-text("投稿を開始")').first.click()
            await page.wait_for_timeout(3000)
            print("   ✅ 完了", flush=True)

            # Step 2: メディア追加ボタンをクリック
            print("📷 Step 2/11: メディア追加画面を開く...", flush=True)
            await page.locator('button[aria-label="メディアを追加"]').first.click()
            await page.wait_for_timeout(3000)
            print("   ✅ 完了", flush=True)

            # Step 3: 画像をアップロード（ファイルダイアログが開いた状態で）
            print(f"📷 Step 3/11: 画像をアップロード（{len(images)}枚）...", flush=True)
            # file inputを探す（複数の可能なセレクタを試す）
            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(images)
            print("   ⏳ アップロード待機中（25秒）...", flush=True)
            await page.wait_for_timeout(25000)
            print("   ✅ 完了", flush=True)

            # Step 3.5: macOSネイティブファイルダイアログを閉じる
            print("🔄 Step 3.5/11: ネイティブダイアログを閉じる...", flush=True)
            await page.wait_for_timeout(2000)
            # Cmd+. (macOS標準のキャンセルショートカット) を送信
            subprocess.run([
                'osascript', '-e',
                'tell application "System Events" to keystroke "." using command down'
            ], capture_output=True)
            await page.wait_for_timeout(1500)
            # Escapeも送信
            subprocess.run([
                'osascript', '-e',
                'tell application "System Events" to key code 53'
            ], capture_output=True)
            await page.wait_for_timeout(1000)
            print("   ✅ 完了", flush=True)

            # Step 3.6: 「変更を破棄」確認メッセージが出たらキャンセルをクリック
            print("🔄 Step 3.6/11: 確認メッセージを閉じる...", flush=True)
            await page.wait_for_timeout(1000)
            try:
                # 「変更を破棄」テキストが表示されているか確認
                discard_text = page.locator('text=変更を破棄してもよろしいですか')
                if await discard_text.is_visible(timeout=3000):
                    # キャンセルボタンをクリック
                    cancel_btn = page.locator('button:has-text("キャンセル")').first
                    await cancel_btn.click()
                    await page.wait_for_timeout(1000)
                    print("   ✅ キャンセルをクリック", flush=True)
                else:
                    print("   ⚠️ 確認メッセージなし（スキップ）", flush=True)
            except:
                print("   ⚠️ 確認メッセージなし（スキップ）", flush=True)
            await page.wait_for_timeout(500)

            # Step 4: 「次へ」をクリック（画像選択完了）
            print("➡️ Step 4/11: 画像選択完了「次へ」...", flush=True)
            next_btn = page.locator('button:has-text("次へ")').first
            await next_btn.click()
            await page.wait_for_timeout(3000)
            print("   ✅ 完了", flush=True)

            # Step 5: コンテンツ入力（クリップボード経由）
            print("📝 Step 5/11: コンテンツ入力...", flush=True)
            editor = page.locator('.ql-editor').first
            await editor.click()
            await page.wait_for_timeout(500)
            # クリップボード経由で貼り付け
            pyperclip.copy(CONTENT_NO_URL)
            await page.keyboard.press("Meta+v")  # macOSはMeta+v
            await page.wait_for_timeout(2000)
            print("   ✅ 完了", flush=True)

            # Step 6: URL追記
            print("🔗 Step 6/11: URL追記...", flush=True)
            # 末尾に移動
            await page.keyboard.press("Meta+End")
            await page.wait_for_timeout(300)
            pyperclip.copy(URL_TEXT)
            await page.keyboard.press("Meta+v")
            await page.wait_for_timeout(2000)
            print("   ✅ 完了", flush=True)

            # Step 7: スケジュール設定画面を開く（時計アイコン）
            print("⏰ Step 7/11: スケジュール設定画面を開く...", flush=True)
            # 時計アイコンボタンを探す
            schedule_btn = page.locator('button[aria-label="投稿のスケジュールを設定"]').first
            await schedule_btn.click()
            await page.wait_for_timeout(2000)
            print("   ✅ 完了", flush=True)

            # Step 8: 日付を設定（入力フィールドに直接入力）
            print(f"📅 Step 8/11: 日付を設定 ({schedule_time.strftime('%Y/%m/%d')})...", flush=True)

            # 日付入力フィールドをクリックして選択
            date_input = page.locator('input[type="text"]').first
            await date_input.click()
            await page.wait_for_timeout(500)

            # トリプルクリックで全選択
            await date_input.click(click_count=3)
            await page.wait_for_timeout(300)

            # 日付を入力 (YYYY/M/D形式)
            date_str = f"{schedule_time.year}/{schedule_time.month}/{schedule_time.day}"
            await page.keyboard.type(date_str)
            await page.wait_for_timeout(500)

            # Tabキーで時間フィールドへ移動
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(1000)
            print("   ✅ 完了", flush=True)

            # Step 9: 時間を設定
            print(f"⏰ Step 9/11: 時間を設定 ({schedule_time.strftime('%H:%M')})...", flush=True)
            # 時間フィールドはTabで移動済み

            # 24時間形式で入力 (HH:MM)
            time_str = schedule_time.strftime("%H:%M")

            # 全選択して上書き
            await page.keyboard.press("Meta+a")
            await page.keyboard.type(time_str)
            await page.wait_for_timeout(500)
            print("   ✅ 完了", flush=True)

            # Step 10: スケジュールダイアログの「次へ」をクリック
            print("✅ Step 10/12: スケジュールを確定...", flush=True)
            next_btn_schedule = page.locator('button:has-text("次へ")').last
            await next_btn_schedule.click()
            await page.wait_for_timeout(3000)
            print("   ✅ 完了", flush=True)

            # Step 11: 「スケジュール」ボタンをクリック（最終確定）
            print("✅ Step 11/12: 「スケジュール」ボタンをクリック...", flush=True)
            schedule_final_btn = page.locator('button:has-text("スケジュール")').first
            await schedule_final_btn.click()
            await page.wait_for_timeout(3000)
            print("   ✅ 完了", flush=True)

            # Step 12: 最終確認のスクリーンショット
            print("📷 Step 12/12: スクリーンショット保存...", flush=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = OUTPUT_DIR / f"linkedin_scheduled_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path))
            print("   ✅ 完了", flush=True)

            print("\n" + "=" * 60)
            print("🎉 投稿予約完了！")
            print("=" * 60)
            print(f"📅 予約日時: {schedule_time.strftime('%Y年%m月%d日 %H:%M')}")
            print(f"📷 スクリーンショット: {screenshot_path.name}")
            print("=" * 60)
            print("\n✅ 内容を確認してください")
            print("   確認後、ブラウザを閉じてください...")

            # ブラウザが閉じられるまで待機
            try:
                while len(context.pages) > 0:
                    await asyncio.sleep(1)
            except:
                pass

        except Exception as e:
            print(f"\n❌ エラー発生: {e}", flush=True)
            error_screenshot = OUTPUT_DIR / f"linkedin_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=str(error_screenshot))
            print(f"📷 エラースクリーンショット: {error_screenshot.name}", flush=True)
            print("\n手動で操作を続けてください...")
            print("完了後、ブラウザを閉じてください...")
            try:
                while len(context.pages) > 0:
                    await asyncio.sleep(1)
            except:
                pass
        finally:
            await context.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LinkedIn自動投稿スクリプト")
    parser.add_argument("--folder", "-f", type=int, default=None, help="フォルダ番号（1から始まる）")
    parser.add_argument("--days", "-d", type=int, default=7, help="何日後に投稿予約（デフォルト: 7）")
    parser.add_argument("--auto", "-a", action="store_true", help="確認なしで自動実行")
    args = parser.parse_args()

    print("=" * 60)
    print("📘 LinkedIn自動投稿スクリプト v3")
    print("=" * 60)
    print("このスクリプトは以下を自動で行います:")
    print("  1. インフォグラフィック画像の添付")
    print("  2. 投稿コンテンツの入力")
    print("  3. スケジュール予約の設定")
    print("=" * 60)

    # Step 1: 画像フォルダを選択
    if args.folder is not None:
        images, folder_name = select_image_folder_auto(args.folder)
    else:
        images, folder_name = select_image_folder()

    if not images:
        print("\n❌ 画像が選択されませんでした")
        return

    # Step 2: スケジュール設定
    schedule_days = args.days if args.auto else get_schedule_settings()

    # 最終確認
    schedule_time = datetime.now() + timedelta(days=schedule_days)
    print("\n" + "=" * 60)
    print("📋 設定確認")
    print("=" * 60)
    print(f"📷 画像: {len(images)}枚")
    print(f"📅 予約: {schedule_time.strftime('%Y年%m月%d日 %H:%M')}")
    print("=" * 60)

    if not args.auto:
        confirm = input("\nこの設定で開始しますか？ (Enter=開始 / n=キャンセル): ").strip().lower()
        if confirm == "n":
            print("キャンセルしました")
            return

    # 実行
    asyncio.run(post_to_linkedin(images, schedule_days))


if __name__ == "__main__":
    main()
