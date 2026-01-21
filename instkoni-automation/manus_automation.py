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

# --- マスタープロンプト（添付ファイル用：記事本文は別途アップロード） --- #
MASTER_PROMPT_TEMPLATE = """添付したMarkdownファイルはNote記事の下書きです。以下の指示に従って、記事の品質を向上させてください。

## 制約条件

1. **ファクトチェック**: 記事内の技術的な記述、製品名、統計データの正確性を検証し、誤りがあれば修正案を提示
2. **参考情報の付与**: 信頼性の高い情報源を3〜5個調査してURLリストを作成
3. **文字数の肉付け**: 約4,000字以上を目安に加筆（冗長にならないよう注意）
4. **SNS調査**: X等でテーマに関する意見を調査し、記事に反映

## 成果物（3つ明確に分けて提示）

1. 推敲・加筆済みのNote記事（Markdown形式）
2. ファクトチェック結果レポート（修正箇所、理由、参考情報源）
3. 参考情報源のURLリスト

## 記事の特徴分析（著者のスタイル）

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


async def get_latest_draft() -> Optional[tuple[Path, str]]:
    """最新の下書きファイルを取得"""
    if not INPUT_DIR.exists():
        print(f"📁 入力ディレクトリが存在しません: {INPUT_DIR}")
        return None

    md_files = list(INPUT_DIR.glob("*.md"))
    if not md_files:
        print("📭 下書きファイルが見つかりません")
        return None

    # 更新日時でソートして最新を取得
    latest = max(md_files, key=lambda f: f.stat().st_mtime)
    print(f"📄 最新の下書き: {latest.name}")

    content = await read_file_async(latest)
    return (latest, content)


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

        # ========== 処理完了の判定（最低待機時間経過後） ==========
        if elapsed >= min_wait_time:
            # 処理中のインジケーターをチェック
            is_processing = False
            try:
                # 「ユーザーを待っています」などの表示がないか確認
                waiting_text = await page.locator('text=/待っています|実行中|処理中/').count()
                loading_indicators = await page.locator('[class*="loading"], [class*="spinner"]').count()
                is_processing = waiting_text > 0 or loading_indicators > 0
            except:
                pass

            # チャット内に添付ファイルが表示されているか確認
            try:
                # 生成されたファイルを示す要素を探す（チャット内の添付ファイル）
                # より具体的なセレクタ：ファイル名を含む要素
                file_elements = page.locator('[class*="message"] [class*="file"], [class*="attachment"], [class*="artifact"]')
                file_count = await file_elements.count()

                if file_count >= 3 and not is_processing:
                    print(f"✅ 処理完了（{elapsed}秒）- {file_count}個のファイルを検出")
                    return True
            except:
                pass

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

    try:
        # ========== ファイルカードを探す ==========
        # ManusAIのファイルは「Markdown · X.XX KB」形式で表示される
        # ファクトチェック結果レポート、参考情報源URLリストなどのテキストを含む

        # ファイルカードを識別するためのテキストパターン
        file_patterns = [
            ("fact_check", ["ファクトチェック結果レポート", "ファクトチェック"]),
            ("references", ["参考情報源URLリスト", "参考情報源", "参考URL"]),
            ("revised_article", ["推敲", "加筆", "Sora", "衝撃"]),  # メイン記事（タイトルに含まれる可能性）
        ]

        # 「Markdown · 」を含む要素を探す（ファイルサイズ表示）
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

                # ========== ダウンロードボタンを探す ==========
                # 右上に表示されるダウンロードアイコンを探す
                download_selectors = [
                    'button[aria-label*="download"]',
                    'button[aria-label*="Download"]',
                    'button[aria-label*="ダウンロード"]',
                    '[class*="download"]',
                    'button:has(svg[class*="download"])',
                    'a[download]',
                    # アイコンボタン（SVG内のpathで判定）
                    'button:has(svg)',
                ]

                # ダウンロードイベントをリッスン
                async with page.expect_download(timeout=30000) as download_info:
                    download_clicked = False

                    # ダウンロードボタンを探してクリック
                    for dl_selector in download_selectors:
                        try:
                            dl_btns = page.locator(dl_selector)
                            dl_count = await dl_btns.count()

                            for j in range(dl_count):
                                dl_btn = dl_btns.nth(j)
                                if await dl_btn.is_visible():
                                    # ボタンの位置を確認（右上にあるか）
                                    box = await dl_btn.bounding_box()
                                    if box and box['x'] > 800:  # 画面右側にある
                                        await dl_btn.click()
                                        download_clicked = True
                                        print(f"      📥 ダウンロードボタンクリック: {dl_selector}")
                                        break
                            if download_clicked:
                                break
                        except:
                            continue

                    # フォールバック: 右上領域の全てのボタンを試す
                    if not download_clicked:
                        try:
                            all_buttons = page.locator('button')
                            btn_count = await all_buttons.count()
                            for j in range(btn_count):
                                btn = all_buttons.nth(j)
                                if await btn.is_visible():
                                    box = await btn.bounding_box()
                                    # 右上にあり、小さいボタン（アイコンボタン）を探す
                                    if box and box['x'] > 900 and box['width'] < 60 and box['height'] < 60:
                                        await btn.click()
                                        download_clicked = True
                                        print(f"      📥 右上のボタンをクリック")
                                        break
                        except:
                            pass

                    if not download_clicked:
                        print(f"      ⚠️ ダウンロードボタンが見つかりません")
                        await page.keyboard.press('Escape')
                        await page.wait_for_timeout(1000)
                        continue

                # ダウンロード完了を待つ
                try:
                    download = await download_info.value
                    suggested_name = download.suggested_filename
                    filename = f"{timestamp}_{title}_{suffix}.md"
                    filepath = OUTPUT_DIR / filename

                    await download.save_as(str(filepath))
                    downloaded_files.append(filepath)
                    outputs[key] = f"(ダウンロード済み: {filepath})"
                    print(f"      ✅ {filename}")
                except Exception as e:
                    print(f"      ⚠️ ダウンロード保存エラー: {e}")

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

        # デバッグモード: 一時停止
        if DEBUG_MODE:
            print("\n🔍 デバッグモード: ページを確認してください")
            print("   手動でログインやUI確認を行えます")
            print("   確認後、ブラウザのPlaywright Inspectorで Resume をクリック")
            await page.pause()

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

        # ========== ファイルアップロード（ドラッグ&ドロップ） ==========
        print("📎 ファイルをドラッグ&ドロップでアップロード中...")

        file_uploaded = False

        # 入力欄を見つける
        input_selectors = [
            'textarea',
            '[contenteditable="true"]',
            '[class*="input"]',
            '[class*="prompt"]'
        ]

        drop_target = None
        for selector in input_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible():
                    drop_target = element
                    print(f"   📍 ドロップ先を発見: {selector}")
                    break
            except:
                continue

        if drop_target:
            try:
                # ファイルの内容を読み込む
                with open(draft_file, 'rb') as f:
                    file_content = f.read()

                # DataTransferイベントをシミュレートしてドラッグ&ドロップ
                # Playwrightではset_input_filesの代わりにJavaScriptでdropイベントを発火
                await page.evaluate('''
                    async (args) => {
                        const { targetSelector, fileName, fileContent } = args;
                        const target = document.querySelector(targetSelector);
                        if (!target) return false;

                        // Base64をArrayBufferに変換
                        const binaryString = atob(fileContent);
                        const bytes = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }

                        // Fileオブジェクトを作成
                        const file = new File([bytes], fileName, { type: 'text/markdown' });

                        // DataTransferオブジェクトを作成
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);

                        // dropイベントを発火
                        const dropEvent = new DragEvent('drop', {
                            bubbles: true,
                            cancelable: true,
                            dataTransfer: dataTransfer
                        });
                        target.dispatchEvent(dropEvent);

                        return true;
                    }
                ''', {
                    'targetSelector': 'textarea',
                    'fileName': draft_file.name,
                    'fileContent': __import__('base64').b64encode(file_content).decode('utf-8')
                })

                await page.wait_for_timeout(2000)
                print(f"   📎 ドラッグ&ドロップでファイルを添付: {draft_file.name}")
                file_uploaded = True

            except Exception as e:
                print(f"   ⚠️ ドラッグ&ドロップエラー: {e}")

        # フォールバック: 非表示のinput[type="file"]を探す
        if not file_uploaded:
            try:
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(str(draft_file))
                file_uploaded = True
                print(f"   📎 input[type=file]でアップロード: {draft_file.name}")
            except:
                pass

        if not file_uploaded:
            print("   ⚠️ ファイルアップロードできませんでした（プロンプトのみで続行）")

        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUTPUT_DIR / "debug_02_file_uploaded.png"))

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

    # 最新の下書きを取得
    draft = await get_latest_draft()
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
