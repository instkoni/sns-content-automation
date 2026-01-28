#!/usr/bin/env python3
"""
LinkedIn自動投稿スクリプト v4
- outputsフォルダからlinkedin_draft.mdを選択
- linkedin_draft.mdから投稿内容と画像パスを読み込み
- スケジュール設定自動化
- クリップボード経由のテキスト入力
"""

import asyncio
import sys
import subprocess
import pyperclip
import re
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# パス設定
SCRIPT_DIR = Path(__file__).parent.resolve()
BROWSER_DATA_DIR = SCRIPT_DIR / "browser-data-sns"
OUTPUT_DIR = SCRIPT_DIR / "outputs"


def parse_linkedin_draft(draft_path: Path) -> tuple[str, str, list[str]]:
    """
    linkedin_draft.mdを解析して、本文・URL・画像パスを抽出する

    Returns:
        tuple[str, str, list[str]]: (本文, URL, 画像パスリスト)
    """
    content = draft_path.read_text(encoding='utf-8')

    # メタ情報からSource URLを抽出
    source_match = re.search(r'^Source:\s*(.+)$', content, re.MULTILINE)
    source_url = source_match.group(1).strip() if source_match else ""

    # 本文を抽出（最初の---と次の---の間）
    parts = content.split('---')
    if len(parts) >= 2:
        body_text = parts[1].strip()
    else:
        body_text = ""

    # 本文の最後に「🔗 記事はこちら」があれば、URLは別途追加
    # 本文からURLを分離（本文自体はURLを含まない形で保持）
    content_no_url = body_text
    url_text = f"\n{source_url}" if source_url else ""

    # 画像パスを抽出（## Imagesセクション）
    images = []
    images_match = re.search(r'## Images\n((?:- .+\n?)+)', content)
    if images_match:
        image_lines = images_match.group(1).strip().split('\n')
        for line in image_lines:
            if line.startswith('- '):
                img_path = line[2:].strip()
                # パスを正規化
                img_path_obj = Path(img_path)
                if img_path_obj.exists():
                    images.append(str(img_path_obj.resolve()))
                else:
                    # 相対パスの場合、draft_pathからの相対パスとして解決
                    resolved = (draft_path.parent / img_path).resolve()
                    if resolved.exists():
                        images.append(str(resolved))

    return content_no_url, url_text, images


def select_draft_folder() -> tuple[str, str, list[str], str]:
    """
    outputsフォルダからlinkedin_draft.mdを含むフォルダを選択し、
    本文・URL・画像パスを返す

    Returns:
        tuple[str, str, list[str], str]: (本文, URL, 画像パスリスト, フォルダ名)
    """
    print("\n" + "=" * 60)
    print("📁 LinkedIn投稿フォルダ選択")
    print("=" * 60)

    # linkedin_draft.mdを含むフォルダ一覧を取得
    folders = []
    for item in OUTPUT_DIR.iterdir():
        if item.is_dir():
            draft_file = item / "linkedin_draft.md"
            if draft_file.exists():
                folders.append(item)

    # タイムスタンプでソート（降順）
    folders.sort(key=lambda x: x.name, reverse=True)

    if not folders:
        print("❌ linkedin_draft.mdを含むフォルダが見つかりません")
        return "", "", [], ""

    # 一覧表示
    print("\n利用可能なフォルダ:")
    for i, folder in enumerate(folders[:10]):
        draft_file = folder / "linkedin_draft.md"
        # draft_fileから最初の行（タイトル相当）を取得
        try:
            content = draft_file.read_text(encoding='utf-8')
            # 本文の最初の行を取得（---の後の最初の行）
            parts = content.split('---')
            if len(parts) >= 2:
                body_lines = parts[1].strip().split('\n')
                title = body_lines[0][:60] if body_lines else folder.name
            else:
                title = folder.name
        except:
            title = folder.name
        print(f"  [{i+1}] {folder.name}")
        print(f"       {title}...")

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

    # linkedin_draft.mdを解析
    draft_file = selected / "linkedin_draft.md"
    content_no_url, url_text, images = parse_linkedin_draft(draft_file)

    # 内容を表示
    print(f"\n✅ 選択フォルダ: {selected.name}")
    print("\n📝 投稿内容プレビュー:")
    print("-" * 40)
    preview = content_no_url[:300] + "..." if len(content_no_url) > 300 else content_no_url
    print(preview)
    print("-" * 40)
    print(f"\n🔗 URL: {url_text.strip()}")
    print(f"\n📷 添付される画像 ({len(images)}枚):")
    for i, img in enumerate(images):
        print(f"   [{i+1}] {Path(img).name}")

    # 確認
    print()
    confirm = input("これでよろしいですか？ (Enter=OK / n=キャンセル): ").strip().lower()
    if confirm == "n":
        print("キャンセルしました")
        return "", "", [], ""

    folder_name = selected.name

    return content_no_url, url_text, images, folder_name


def select_draft_folder_auto(folder_num: int) -> tuple[str, str, list[str], str]:
    """
    フォルダ番号を指定して自動選択

    Returns:
        tuple[str, str, list[str], str]: (本文, URL, 画像パスリスト, フォルダ名)
    """
    print("\n" + "=" * 60)
    print("📁 LinkedIn投稿フォルダ自動選択")
    print("=" * 60)

    # linkedin_draft.mdを含むフォルダ一覧を取得
    folders = []
    for item in OUTPUT_DIR.iterdir():
        if item.is_dir():
            draft_file = item / "linkedin_draft.md"
            if draft_file.exists():
                folders.append(item)

    folders.sort(key=lambda x: x.name, reverse=True)

    if not folders:
        print("❌ linkedin_draft.mdを含むフォルダが見つかりません")
        return "", "", [], ""

    # 指定番号で選択
    idx = folder_num - 1
    if idx < 0 or idx >= len(folders):
        print(f"⚠️ 無効なフォルダ番号: {folder_num}")
        return "", "", [], ""

    selected = folders[idx]

    # linkedin_draft.mdを解析
    draft_file = selected / "linkedin_draft.md"
    content_no_url, url_text, images = parse_linkedin_draft(draft_file)

    # 内容を表示
    print(f"\n✅ 選択フォルダ: {selected.name}")
    print(f"\n📷 添付される画像 ({len(images)}枚):")
    for i, img in enumerate(images):
        print(f"   [{i+1}] {Path(img).name}")

    folder_name = selected.name

    return content_no_url, url_text, images, folder_name


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


async def post_to_linkedin(content_no_url: str, url_text: str, images: list[str], schedule_days: int = 7):
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
            pyperclip.copy(content_no_url)
            await page.keyboard.press("Meta+v")  # macOSはMeta+v
            await page.wait_for_timeout(2000)
            print("   ✅ 完了", flush=True)

            # Step 6: URL追記
            print("🔗 Step 6/11: URL追記...", flush=True)
            # 末尾に移動
            await page.keyboard.press("Meta+End")
            await page.wait_for_timeout(300)
            pyperclip.copy(url_text)
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
    print("📘 LinkedIn自動投稿スクリプト v4")
    print("=" * 60)
    print("このスクリプトは以下を自動で行います:")
    print("  1. outputsフォルダからlinkedin_draft.mdを選択")
    print("  2. 投稿コンテンツと画像を自動読み込み")
    print("  3. スケジュール予約の設定")
    print("=" * 60)

    # Step 1: 投稿フォルダを選択
    if args.folder is not None:
        content_no_url, url_text, images, folder_name = select_draft_folder_auto(args.folder)
    else:
        content_no_url, url_text, images, folder_name = select_draft_folder()

    if not content_no_url:
        print("\n❌ 投稿内容が選択されませんでした")
        return

    if not images:
        print("\n⚠️ 画像が見つかりませんでした。テキストのみで投稿しますか？")
        confirm = input("(Enter=続行 / n=キャンセル): ").strip().lower()
        if confirm == "n":
            print("キャンセルしました")
            return

    # Step 2: スケジュール設定
    schedule_days = args.days if args.auto else get_schedule_settings()

    # 最終確認
    schedule_time = datetime.now() + timedelta(days=schedule_days)
    print("\n" + "=" * 60)
    print("📋 設定確認")
    print("=" * 60)
    print(f"📝 投稿内容: {len(content_no_url)}文字")
    print(f"🔗 URL: {url_text.strip()}")
    print(f"📷 画像: {len(images)}枚")
    print(f"📅 予約: {schedule_time.strftime('%Y年%m月%d日 %H:%M')}")
    print("=" * 60)

    if not args.auto:
        confirm = input("\nこの設定で開始しますか？ (Enter=開始 / n=キャンセル): ").strip().lower()
        if confirm == "n":
            print("キャンセルしました")
            return

    # 実行
    asyncio.run(post_to_linkedin(content_no_url, url_text, images, schedule_days))


if __name__ == "__main__":
    main()
