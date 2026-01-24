#!/usr/bin/env python3
"""
ManusAI 自動校正・リライトツール

Antigravityで生成されたNote記事の下書きを、ManusAIを活用して
ファクトチェック、内容の肉付け、推敲を自動で行うプログラム。
"""

import asyncio
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, BrowserContext
import aiofiles

# 環境変数の読み込み
load_dotenv()

# --- パス設定（スクリプトの場所を基準） --- #
SCRIPT_DIR = Path(__file__).parent.resolve()
ARTICLES_DIR = SCRIPT_DIR.parent / "articles"

# --- 設定 --- #
INPUT_DIR = Path(os.getenv("INPUT_DIR", ARTICLES_DIR / "drafts"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ARTICLES_DIR / "drafts2"))
ANALYSIS_FILE = Path(os.getenv("ANALYSIS_FILE", SCRIPT_DIR / "config" / "article_analysis.md"))
USER_DATA_DIR = SCRIPT_DIR / "browser-data-manus"  # セッション永続化用

# ManusAI設定
MANUS_URL = "https://manus.im/app"

# デバッグモード
DEBUG_MODE = "--debug" in sys.argv

# --- マスタープロンプト（ファイルアップロード後のダイアログ用） --- #
MASTER_PROMPT_TEMPLATE = """上記のMarkdownファイルを以下の指示に従って処理してください。

【タスク】
1. ファクトチェック: 技術的な記述、製品名、統計データの正確性を検証
2. 参考情報: 信頼性の高い情報源を3〜5個調査してURLリストを作成
3. 加筆: 約4,000字以上に肉付け（冗長にならないよう注意）
4. SNS調査: Xでテーマに関する意見を調査し反映

【成果物】3つのMarkdownファイルを作成してください
1. 推敲・加筆済みのNote記事
2. ファクトチェック結果レポート
3. 参考情報源URLリスト

【著者のスタイル】
{ARTICLE_ANALYSIS}
"""

# 一時ファイル保存用ディレクトリ
TEMP_DIR = SCRIPT_DIR / "temp"


def get_timestamp() -> str:
    """YYYYMMDD形式のタイムスタンプを生成"""
    return datetime.now().strftime("%Y%m%d")


def extract_title_from_filename(filename: str) -> str:
    """ファイル名から記事タイトルを抽出"""
    # 日付部分と拡張子を除去
    name = Path(filename).stem
    # 日付パターンを除去 (YYYY-MM-DD または YYYYMMDD)
    name = re.sub(r'^\d{4}-?\d{2}-?\d{2}-?', '', name)
    return name or "untitled"


async def read_file_async(file_path: Path) -> str:
    """ファイルを非同期で読み込む"""
    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
        return await f.read()


async def write_file_async(file_path: Path, content: str) -> None:
    """ファイルを非同期で書き込む"""
    async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
        await f.write(content)


def list_draft_files() -> list[Path]:
    """下書きファイルの一覧を取得"""
    if not INPUT_DIR.exists():
        return []

    md_files = [f for f in INPUT_DIR.glob("*.md") if f.is_file()]
    # 更新日時でソート（新しい順）
    md_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return md_files


def select_draft_file(md_files: list[Path]) -> Optional[Path]:
    """ユーザーに下書きファイルを選択させる"""
    if not md_files:
        print("📭 下書きファイルが見つかりません")
        return None

    print("\n📄 下書きファイル一覧:")
    print("-" * 60)
    for i, f in enumerate(md_files, 1):
        # ファイルサイズと更新日時を表示
        size_kb = f.stat().st_size / 1024
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  [{i:2d}] {f.name}")
        print(f"       ({size_kb:.1f} KB, 更新: {mtime})")
    print("-" * 60)
    print("  [0] キャンセル")
    print()

    while True:
        try:
            choice = input("📝 処理するファイル番号を入力してください: ").strip()
            if choice == "0":
                print("❌ キャンセルしました")
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(md_files):
                selected = md_files[idx]
                print(f"\n✅ 選択: {selected.name}")
                return selected
            else:
                print(f"⚠️ 1〜{len(md_files)} の範囲で入力してください")
        except ValueError:
            print("⚠️ 数字を入力してください")
        except KeyboardInterrupt:
            print("\n❌ キャンセルしました")
            return None


async def get_selected_draft() -> Optional[tuple[Path, str]]:
    """ユーザーが選択した下書きファイルを取得"""
    if not INPUT_DIR.exists():
        print(f"📁 入力ディレクトリが存在しません: {INPUT_DIR}")
        return None

    md_files = list_draft_files()
    if not md_files:
        print("📭 下書きファイルが見つかりません")
        return None

    selected = select_draft_file(md_files)
    if not selected:
        return None

    content = await read_file_async(selected)
    return (selected, content)


async def get_article_analysis() -> str:
    """記事分析ファイルを読み込む"""
    if not ANALYSIS_FILE.exists():
        print(f"⚠️ 分析ファイルが存在しません: {ANALYSIS_FILE}")
        return "(分析ファイルなし)"

    return await read_file_async(ANALYSIS_FILE)


def generate_prompt(article_analysis: str) -> str:
    """マスタープロンプトに動的情報を挿入する（記事本文は添付ファイルで送信）"""
    return MASTER_PROMPT_TEMPLATE.format(
        ARTICLE_ANALYSIS=article_analysis
    )


async def prepare_draft_file(draft_path: Path, draft_content: str) -> Path:
    """下書きを一時ファイルとして保存（アップロード用）"""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = TEMP_DIR / draft_path.name
    await write_file_async(temp_file, draft_content)
    return temp_file


async def wait_for_processing_complete(page: Page, timeout_minutes: int = 30) -> bool:
    """ManusAIの処理完了を待機"""
    print(f"⏳ ManusAIの処理を待機中（最大{timeout_minutes}分）...")

    timeout_ms = timeout_minutes * 60 * 1000
    check_interval = 10000  # 10秒ごとにチェック
    min_wait_time = 60  # 最低60秒は待機（早期完了判定を防ぐ）
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout_ms:
        elapsed = int(asyncio.get_event_loop().time() - start_time)

        # ========== ブラウザコネクタ等のダイアログに自動応答 ==========
        try:
            # 「いいえ、デフォルトのブラウザを使用する」ボタンを探す
            decline_selectors = [
                'button:has-text("いいえ")',
                'button:has-text("デフォルトのブラウザを使用する")',
                'button:has-text("No")',
                'button:has-text("Cancel")',
            ]
            for selector in decline_selectors:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    await btn.click()
                    print(f"   🔘 ダイアログ応答: {selector}")
                    await page.wait_for_timeout(1000)
                    break
        except:
            pass

        # ========== コネクタダイアログを閉じる ==========
        try:
            # コネクタダイアログの×ボタンを探して閉じる
            close_btn = page.locator('[class*="dialog"] button:has-text("×"), [class*="modal"] button[aria-label*="close"], button[aria-label*="閉じる"]').first
            if await close_btn.is_visible():
                await close_btn.click()
                print("   ❌ ダイアログを閉じました")
                await page.wait_for_timeout(1000)
        except:
            pass

        # ========== 「ユーザーを待っています」状態を検出して自動返信 ==========
        try:
            # ManusAIがユーザーの返信を待っている場合
            waiting_for_user = page.locator('text=/返信後に作業を続けます|ユーザーを待っています/')
            if await waiting_for_user.count() > 0:
                print("   🔔 ManusAIがユーザーの返信を待っています")

                # 入力欄を探して返信を送信
                textarea = page.locator('textarea[placeholder*="メッセージ"], textarea').first
                if await textarea.is_visible():
                    await textarea.fill("はい、添付ファイルを確認して処理を続けてください。")
                    await page.wait_for_timeout(500)

                    # 送信ボタンをクリック
                    send_btn = page.locator('button[type="submit"], button:has(svg)').last
                    if await send_btn.is_visible():
                        await send_btn.click()
                        print("   ✅ 自動返信を送信しました")
                        await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"   ⚠️ 自動返信エラー: {e}")

        # ========== タスク完了の検出 ==========
        try:
            # 「タスクが完了しました」を検出
            completed = await page.locator('text="タスクが完了しました"').count()
            if completed > 0:
                print(f"✅ タスク完了を検出（{elapsed}秒）")
                await page.screenshot(path=str(OUTPUT_DIR / "debug_task_completed.png"))
                return True

            if elapsed % 30 == 0:  # 30秒ごとに状況を表示
                print(f"   ⏳ タスク完了待機中...（{elapsed}秒経過）")
        except Exception as e:
            if elapsed % 60 == 0:
                print(f"   ⚠️ 検出エラー: {e}")

        print(f"⏳ {elapsed}秒経過...")
        await page.wait_for_timeout(check_interval)

    print("⚠️ タイムアウト")
    return False


async def extract_outputs(page: Page, original_path: Path) -> dict[str, str]:
    """ManusAIの出力から成果物をダウンロード"""
    print("📥 成果物をダウンロード中...")

    outputs = {
        "revised_article": "",
        "fact_check": "",
        "references": ""
    }

    # スクリーンショットを保存
    await page.screenshot(path=str(OUTPUT_DIR / "debug_05_before_download.png"))

    timestamp = get_timestamp()
    title = extract_title_from_filename(original_path.name)
    downloaded_files = []

    # 日付_記事名フォルダを作成
    folder_name = f"{timestamp}_{title}"
    output_folder = OUTPUT_DIR / folder_name
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"   📁 出力フォルダ作成: {output_folder}")

    # ========== 手動ダウンロード方式 ==========
    import time
    downloads_dir = Path.home() / "Downloads"

    # ダウンロード前の.mdファイル一覧を取得
    before_download = set(downloads_dir.glob("*.md"))

    print("\n" + "=" * 60)
    print("📥 手動でファイルをダウンロードしてください")
    print("=" * 60)
    print(f"   1. 各ファイルカードをクリックして拡大")
    print(f"   2. 右上のダウンロードボタン（↓）をクリック")
    print(f"   3. 「Markdown」を選択してダウンロード")
    print(f"   4. 3ファイル全てダウンロードしてください：")
    print(f"      - メイン記事")
    print(f"      - ファクトチェック結果レポート")
    print(f"      - 参考情報源URLリスト")
    print("=" * 60)
    print("   完了したら、Playwright Inspectorで Resume をクリック")
    print("=" * 60 + "\n")

    await page.pause()

    # ダウンロード後の.mdファイル一覧を取得
    after_download = set(downloads_dir.glob("*.md"))

    # 新しくダウンロードされたファイルを特定
    new_files = after_download - before_download
    print(f"   🔍 新しくダウンロードされたファイル: {len(new_files)}個")

    # ファイルを出力フォルダに移動
    for md_file in new_files:
        try:
            dest = output_folder / md_file.name
            md_file.rename(dest)
            downloaded_files.append(dest)
            print(f"   ✅ 移動: {md_file.name}")
        except Exception as e:
            print(f"   ⚠️ 移動エラー: {md_file.name} - {e}")

    print(f"   📊 移動完了: {len(downloaded_files)}ファイル -> {output_folder.name}/")

    outputs["output_folder"] = str(output_folder)
    outputs["downloaded_files"] = [str(f) for f in downloaded_files]
    return outputs

    try:
        # ========== ファイルカードを探す ==========
        # ManusAIのファイルは「Markdown · X.XX KB」形式で表示される
        # ファクトチェック結果レポート、参考情報源URLリストなどのテキストを含む

        # ファイルカードを識別するためのテキストパターン
        file_patterns = [
            ("fact_check", ["ファクトチェック結果レポート", "ファクトチェック"]),
            ("references", ["参考情報源URLリスト", "参考情報源", "参考URL"]),
            ("revised_article", ["【2026", "【2025", "指示待ちAI", "自律型"]),  # メイン記事
        ]

        print("   🔍 ファイルカードを検索中...")

        # 方法1: テキストでファイルカードを検索
        file_cards = []

        # 「Markdown · 」テキストを含む親要素を探す
        markdown_indicators = page.locator('text=/Markdown · \\d+\\.?\\d* KB/')
        md_count = await markdown_indicators.count()
        print(f"   📊 Markdown表示要素: {md_count}個")

        for i in range(md_count):
            try:
                indicator = markdown_indicators.nth(i)
                # 親要素（ファイルカード全体）を取得
                # 3階層上の親要素を探す
                card = indicator.locator('xpath=ancestor::div[contains(@class, "cursor-pointer") or contains(@class, "hover:")]').first
                if not await card.count():
                    # フォールバック: クリック可能な親要素を探す
                    card = indicator.locator('xpath=..').first
                    for _ in range(3):
                        parent = card.locator('xpath=..')
                        if await parent.count():
                            card = parent.first
                if await card.is_visible():
                    full_text = await card.inner_text()
                    file_cards.append({
                        'element': card,
                        'text': full_text
                    })
                    print(f"   📄 ファイルカード発見: {full_text[:60]}...")
            except Exception as e:
                print(f"   ⚠️ カード取得エラー: {e}")

        # 方法2: 特定のテキストを含む要素を直接検索
        if len(file_cards) < 3:
            for key, patterns in file_patterns:
                for pattern in patterns:
                    try:
                        elements = page.locator(f'text="{pattern}"')
                        count = await elements.count()
                        for i in range(count):
                            el = elements.nth(i)
                            if await el.is_visible():
                                # 親要素を探す（クリック可能な領域）
                                card = el.locator('xpath=ancestor::div[1]')
                                if await card.count() and await card.first.is_visible():
                                    full_text = await card.first.inner_text()
                                    # 重複チェック
                                    if not any(fc['text'] == full_text for fc in file_cards):
                                        file_cards.append({
                                            'element': card.first,
                                            'text': full_text,
                                            'key': key
                                        })
                                        print(f"   📄 パターンマッチ: {pattern} -> {full_text[:40]}...")
                    except:
                        continue

        print(f"   📊 発見したファイルカード: {len(file_cards)}個")

        # ========== 各ファイルをダウンロード ==========
        for i, card_info in enumerate(file_cards[:3]):
            try:
                card_text = card_info['text']
                card = card_info['element']

                # ファイルの種類を判定
                if 'ファクトチェック' in card_text:
                    key = "fact_check"
                    suffix = "ファクトチェック"
                elif '参考情報源' in card_text or '参考URL' in card_text:
                    key = "references"
                    suffix = "参考情報"
                else:
                    key = "revised_article"
                    suffix = "推敲版"

                print(f"   🖱️ [{i+1}] {suffix}をクリック...")

                # ファイルカードをクリックして展開
                await card.click()
                await page.wait_for_timeout(3000)

                # スクリーンショット保存
                await page.screenshot(path=str(OUTPUT_DIR / f"debug_06_file_expanded_{i+1}.png"))

                # ========== ダウンロードボタンを探す（右上のアイコン） ==========
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(OUTPUT_DIR / f"debug_07_file_opened_{i+1}.png"))

                # 右上のボタン群: 共有(↗), ダウンロード(↓), ..., □, ×
                # ダウンロードボタンは x=1050-1080 付近にある
                download_btn = None

                # 方法1: aria-label で探す
                download_selectors = [
                    'button[aria-label*="ダウンロード"]',
                    'button[aria-label*="download"]',
                    'button[aria-label*="Download"]',
                ]
                for sel in download_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible():
                            download_btn = btn
                            print(f"      📍 ダウンロードボタン発見（{sel}）")
                            break
                    except:
                        continue

                # 方法2: x座標でダウンロードボタンを特定（共有の右隣）
                if not download_btn:
                    print("      🔍 右上のボタンを座標で検索...")
                    all_buttons = page.locator('button')
                    btn_count = await all_buttons.count()

                    for j in range(btn_count):
                        try:
                            btn = all_buttons.nth(j)
                            if await btn.is_visible():
                                box = await btn.bounding_box()
                                # ダウンロードボタン: y < 100, x が 1040-1090 の範囲
                                if box and box['y'] < 100 and 1040 < box['x'] < 1090:
                                    download_btn = btn
                                    print(f"      📍 ダウンロードボタン発見: x={box['x']:.0f}, y={box['y']:.0f}")
                                    break
                        except:
                            continue

                # 方法3: ヘッダーボタンの3番目（0: 共有, 1: ダウンロード ではなく実際の順序で）
                if not download_btn:
                    header_buttons = []
                    all_buttons = page.locator('button')
                    btn_count = await all_buttons.count()

                    for j in range(btn_count):
                        try:
                            btn = all_buttons.nth(j)
                            if await btn.is_visible():
                                box = await btn.bounding_box()
                                if box and box['y'] < 100 and box['x'] > 1000:
                                    header_buttons.append((btn, box))
                        except:
                            continue

                    header_buttons.sort(key=lambda x: x[1]['x'])
                    print(f"      📊 ヘッダーボタン: {len(header_buttons)}個")
                    for idx, (btn, box) in enumerate(header_buttons):
                        print(f"         [{idx}] x={box['x']:.0f}")

                    # インデックス1がダウンロード（0が共有）
                    if len(header_buttons) >= 2:
                        download_btn = header_buttons[1][0]
                        print(f"      📍 インデックス1のボタンを使用")

                if not download_btn:
                    print(f"      ⚠️ ダウンロードボタンが見つかりません")
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(1000)
                    continue

                # ダウンロードボタンをクリック → メニュー表示
                await download_btn.click()
                print(f"      📥 ダウンロードボタンをクリック")
                await page.wait_for_timeout(1500)
                await page.screenshot(path=str(OUTPUT_DIR / f"debug_08_download_menu_{i+1}.png"))

                # 「Markdown」オプションが表示されているか確認
                markdown_option = page.locator('text="Markdown"').first
                if not await markdown_option.is_visible():
                    print(f"      ⚠️ Markdownオプションが見つかりません（別のメニューが開いた可能性）")
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(500)
                    continue

                # 「Markdown」を選択してダウンロード
                try:
                    async with page.expect_download(timeout=60000) as download_info:
                        await markdown_option.click()
                        print(f"      📄 Markdownを選択")

                    download = await download_info.value
                    suggested_name = download.suggested_filename
                    filename = f"{suffix}.md"
                    filepath = output_folder / filename

                    await download.save_as(str(filepath))
                    downloaded_files.append(filepath)
                    outputs[key] = str(filepath)
                    print(f"      ✅ 保存: {filepath}")

                except Exception as e:
                    print(f"      ⚠️ ダウンロードエラー: {e}")
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(500)

                # ファイルプレビューを閉じる
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(1500)

            except Exception as e:
                print(f"   ⚠️ ファイル{i+1}の処理エラー: {e}")
                # エラー時もEscで閉じる
                try:
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(1000)
                except:
                    pass

        print(f"   📊 ダウンロード完了: {len(downloaded_files)}ファイル")

        # ========== ダウンロードできなかった場合、テキスト抽出を試みる ==========
        if len(downloaded_files) == 0:
            print("   ⚠️ ファイルダウンロードできず、テキスト抽出を試みます...")
            try:
                # チャット内のメッセージからテキストを抽出
                messages = page.locator('[class*="message"], [class*="content"]')
                msg_count = await messages.count()
                for i in range(msg_count):
                    try:
                        msg = messages.nth(i)
                        text = await msg.inner_text()
                        if len(text) > 500:  # 長いテキストを探す
                            if 'ファクトチェック' in text:
                                outputs["fact_check"] = text
                            elif '参考情報源' in text or 'http' in text:
                                outputs["references"] = text
                            elif '##' in text or '###' in text:  # Markdown見出しを含む
                                outputs["revised_article"] = text
                    except:
                        continue
            except:
                pass

    except Exception as e:
        print(f"⚠️ 出力抽出エラー: {e}")
        await page.screenshot(path=str(OUTPUT_DIR / "error_extraction.png"))

    return outputs


async def save_outputs(original_path: Path, outputs: dict[str, str]) -> None:
    """成果物をファイルに保存"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = get_timestamp()
    title = extract_title_from_filename(original_path.name)

    files_to_save = [
        (f"{timestamp}_{title}_推敲版.md", outputs.get("revised_article", "")),
        (f"{timestamp}_{title}_ファクトチェック.md", outputs.get("fact_check", "")),
        (f"{timestamp}_{title}_参考情報.md", outputs.get("references", "")),
    ]

    for filename, content in files_to_save:
        if content:
            filepath = OUTPUT_DIR / filename
            await write_file_async(filepath, content)
            print(f"   ✅ {filename}")
        else:
            print(f"   ⚠️ {filename} (内容なし)")


async def process_with_manus(context: BrowserContext, prompt: str, draft_file: Path) -> dict[str, str]:
    """ManusAIで記事を処理（ファイルアップロード対応）"""
    page = await context.new_page()

    try:
        print("📍 ManusAIにアクセス中...")
        await page.goto(MANUS_URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        # スクリーンショット保存（デバッグ用）
        await page.screenshot(path=str(OUTPUT_DIR / "debug_01_initial.png"))

        # ログイン状態を確認（必要に応じてログインフローを追加）
        # 注意: セッション永続化により、2回目以降はログイン不要の想定

        # ========== 新しいタスクを開始（前回の入力をクリア） ==========
        print("🆕 新しいタスクを開始...")

        # 左サイドバーの「新しいタスク」ボタンを正確に探す
        # 注意: コネクタやその他の要素をクリックしないよう、セレクタを厳密にする
        new_task_clicked = False
        try:
            # 左サイドバー内の「新しいタスク」を探す（アイコン付きのボタン）
            sidebar = page.locator('nav, [class*="sidebar"], [class*="menu"]').first
            new_task_btn = sidebar.locator('text="新しいタスク"').first
            if await new_task_btn.is_visible():
                await new_task_btn.click()
                new_task_clicked = True
                print("   ✅ サイドバーの「新しいタスク」をクリック")
        except:
            pass

        # フォールバック: ページ上部の「新しいタスク」リンクを探す
        if not new_task_clicked:
            try:
                # より限定的なセレクタを使用（divは除外）
                new_task_selectors = [
                    'a:has-text("新しいタスク")',
                    'button:has-text("新しいタスク")',
                ]
                for selector in new_task_selectors:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        # コネクタ関連でないことを確認
                        parent_text = await btn.locator('..').inner_text()
                        if 'コネクタ' not in parent_text and 'connector' not in parent_text.lower():
                            await btn.click()
                            new_task_clicked = True
                            print(f"   ✅ 新しいタスクをクリック: {selector}")
                            break
            except:
                pass

        if not new_task_clicked:
            print("   ⚠️ 新しいタスクボタンが見つかりません（続行）")

        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUTPUT_DIR / "debug_01b_new_task.png"))

        # ========== ファイルアップロード ==========
        print("📎 ファイルをアップロード...")
        print(f"   📄 アップロードするファイル: {draft_file}")

        file_uploaded = False

        if DEBUG_MODE:
            # 手動アップロードモード（デバッグ時）
            print("\n" + "=" * 50)
            print("📎 手動でファイルをアップロードしてください")
            print("=" * 50)
            print(f"   1. 入力欄の左下にある「+」ボタンをクリック")
            print(f"   2. ファイルを選択: {draft_file}")
            print(f"   3. または、上記ファイルをドラッグ&ドロップ")
            print("=" * 50)
            print("   完了したら、Playwright Inspectorで Resume をクリック")
            print("=" * 50 + "\n")

            await page.pause()  # 手動操作のため一時停止

            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(OUTPUT_DIR / "debug_02_file_uploaded.png"))
            print("   ✅ 手動アップロード完了を確認")
            file_uploaded = True
        else:
            # 自動アップロード試行
            try:
                # input[type="file"]を探して使用
                file_inputs = page.locator('input[type="file"]')
                input_count = await file_inputs.count()
                if input_count > 0:
                    await file_inputs.first.set_input_files(str(draft_file))
                    await page.wait_for_timeout(2000)
                    file_uploaded = True
                    print(f"   ✅ ファイルアップロード成功: {draft_file.name}")
            except Exception as e:
                print(f"   ⚠️ 自動アップロードエラー: {e}")

            if not file_uploaded:
                print("   ⚠️ ファイルアップロードできませんでした（プロンプトのみで続行）")

        # ========== プロンプト入力 ==========
        print("✍️ プロンプトを入力中...")

        # ダイアログが表示されている場合、ダイアログ内のtextareaを探す
        await page.wait_for_timeout(2000)

        # ダイアログ内またはメインページのtextareaを探す
        input_selectors = [
            'textarea[placeholder*="処理"]',  # ファイルアップロード後のダイアログ
            'textarea[placeholder*="Manus"]',
            '[class*="dialog"] textarea',
            '[class*="modal"] textarea',
            'textarea',
            '[contenteditable="true"]',
            'input[type="text"]',
        ]

        input_element = None
        for selector in input_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                for i in range(count):
                    element = elements.nth(i)
                    if await element.is_visible():
                        input_element = element
                        placeholder = await element.get_attribute('placeholder') or ''
                        print(f"   📝 入力欄を発見: {selector} (placeholder: {placeholder[:30]}...)")
                        break
                if input_element:
                    break
            except:
                continue

        if not input_element:
            print("❌ 入力欄が見つかりません")
            await page.screenshot(path=str(OUTPUT_DIR / "error_no_input.png"))
            return {}

        # プロンプトを入力（force=Trueでダイアログ上の要素もクリック可能に）
        try:
            await input_element.click(force=True)
            await input_element.fill(prompt)
        except Exception as e:
            print(f"   ⚠️ 通常入力失敗、JavaScript経由で入力: {e}")
            # JavaScriptで直接入力
            await page.evaluate('''
                (text) => {
                    const textareas = document.querySelectorAll('textarea');
                    for (const ta of textareas) {
                        if (ta.offsetParent !== null) {  // visible
                            ta.value = text;
                            ta.dispatchEvent(new Event('input', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }
            ''', prompt)

        await page.wait_for_timeout(1000)

        print(f"   📝 プロンプト入力完了（{len(prompt)}文字）")
        await page.screenshot(path=str(OUTPUT_DIR / "debug_03_prompt_entered.png"))

        # 送信ボタンを探してクリック
        print("🚀 送信中...")
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Send")',
            'button:has-text("送信")',
            'button:has-text("Submit")',
            '[class*="send"]',
            '[class*="submit"]'
        ]

        submitted = False
        for selector in submit_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    await btn.click()
                    submitted = True
                    print(f"   ✅ 送信ボタンをクリック: {selector}")
                    break
            except:
                continue

        if not submitted:
            # Enterキーで送信を試みる
            await page.keyboard.press("Enter")
            print("   ⌨️ Enterキーで送信")

        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(OUTPUT_DIR / "debug_04_submitted.png"))

        # 処理完了を待機
        success = await wait_for_processing_complete(page)

        if not success:
            print("⚠️ 処理がタイムアウトしました")
            await page.screenshot(path=str(OUTPUT_DIR / "error_timeout.png"))

        # 成果物を抽出（ファイルをダウンロード）
        await page.screenshot(path=str(OUTPUT_DIR / "debug_04_completed.png"))
        outputs = await extract_outputs(page, draft_file)

        return outputs

    except Exception as e:
        print(f"❌ エラー: {e}")
        await page.screenshot(path=str(OUTPUT_DIR / "error_exception.png"))
        return {}
    finally:
        await page.close()


async def main():
    """メイン処理"""
    print("=" * 50)
    print("🤖 ManusAI 自動校正・リライトツール")
    print("=" * 50)
    print(f"📁 入力ディレクトリ: {INPUT_DIR}")
    print(f"📁 出力ディレクトリ: {OUTPUT_DIR}")
    print(f"📄 分析ファイル: {ANALYSIS_FILE}")
    print(f"🔧 デバッグモード: {'ON' if DEBUG_MODE else 'OFF'}")
    print("=" * 50 + "\n")

    # 出力ディレクトリを作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ユーザーに下書きを選択させる
    draft = await get_selected_draft()
    if not draft:
        print("❌ 処理する記事がありません")
        return

    draft_path, draft_content = draft

    # 記事分析を取得
    article_analysis = await get_article_analysis()

    # プロンプトを生成（記事本文は添付ファイルで送信するため含めない）
    prompt = generate_prompt(article_analysis)

    # 下書きを一時ファイルとして保存（アップロード用）
    draft_file = await prepare_draft_file(draft_path, draft_content)
    print(f"📎 アップロード用ファイル: {draft_file}")

    # プロンプトを保存（確認用）
    prompt_file = OUTPUT_DIR / "last_prompt.txt"
    await write_file_async(prompt_file, prompt)
    print(f"📝 プロンプトを保存: {prompt_file}")
    print(f"📝 プロンプト文字数: {len(prompt)}文字\n")

    # ブラウザを起動（セッション永続化）
    print("🌐 ブラウザを起動中...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=['--disable-blink-features=AutomationControlled']
        )

        try:
            print(f"--- {draft_path.name} の処理を開始 ---\n")

            outputs = await process_with_manus(context, prompt, draft_file)

            if outputs:
                print("\n📥 成果物を保存中...")
                await save_outputs(draft_path, outputs)
                print(f"\n--- {draft_path.name} の処理が完了 ---")
            else:
                print("⚠️ 成果物を取得できませんでした")

        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
        finally:
            print("\n🔒 ブラウザを閉じます...")
            await context.close()

    print("\n✅ 処理完了")


if __name__ == "__main__":
    asyncio.run(main())
