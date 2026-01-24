#!/usr/bin/env python3
"""
SNS Content Generator

note.comの最新記事を取得し、Genspark AIでLinkedInとX向けにリライトして
下書きを生成するプログラム。
"""

import asyncio
import configparser
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, BrowserContext
import aiofiles


# --- パス設定 --- #
SCRIPT_DIR = Path(__file__).parent.resolve()


@dataclass
class Config:
    """設定管理クラス"""
    # NOTE設定
    note_username: str
    note_base_url: str

    # Genspark設定
    genspark_chat_url: str
    response_timeout_minutes: int
    stability_threshold: int
    check_interval_seconds: int

    # パス設定
    browser_data_dir: Path
    output_dir: Path
    infographic_dir: Path
    prompt_file: Path

    # SNS設定
    linkedin_url: str
    x_url: str
    linkedin_delay_days: int
    x_first_post_delay_days: int
    x_interval_hours: int

    # デバッグ
    debug_mode: bool

    @classmethod
    def load(cls, config_path: Path) -> 'Config':
        """設定ファイルを読み込む"""
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding='utf-8')

        return cls(
            note_username=parser.get('NOTE', 'username'),
            note_base_url=parser.get('NOTE', 'base_url'),
            genspark_chat_url=parser.get('GENSPARK', 'chat_url'),
            response_timeout_minutes=parser.getint('GENSPARK', 'response_timeout_minutes'),
            stability_threshold=parser.getint('GENSPARK', 'stability_threshold'),
            check_interval_seconds=parser.getint('GENSPARK', 'check_interval_seconds'),
            browser_data_dir=SCRIPT_DIR / parser.get('PATHS', 'browser_data_dir'),
            output_dir=SCRIPT_DIR / parser.get('PATHS', 'output_dir'),
            infographic_dir=SCRIPT_DIR / parser.get('PATHS', 'infographic_dir'),
            prompt_file=SCRIPT_DIR / parser.get('PATHS', 'prompt_file'),
            linkedin_url=parser.get('SNS', 'linkedin_url'),
            x_url=parser.get('SNS', 'x_url'),
            linkedin_delay_days=parser.getint('SNS', 'linkedin_delay_days'),
            x_first_post_delay_days=parser.getint('SNS', 'x_first_post_delay_days'),
            x_interval_hours=parser.getint('SNS', 'x_interval_hours'),
            debug_mode=parser.getboolean('DEBUG', 'debug_mode'),
        )


@dataclass
class Article:
    """記事データクラス"""
    title: str
    url: str
    content: str
    published_at: Optional[str] = None


class NoteArticleFetcher:
    """note.com記事取得クラス"""

    def __init__(self, config: Config):
        self.config = config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def get_latest_article_url(self) -> Optional[str]:
        """最新記事のURLを取得"""
        profile_url = f"{self.config.note_base_url}/{self.config.note_username}"
        print(f"📡 プロフィールページを取得中: {profile_url}")

        try:
            response = requests.get(profile_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 記事リンクを探す（note.comの構造に基づく）
            # パターン1: data-note-url属性
            article_links = soup.select('a[data-note-url]')
            if article_links:
                url = article_links[0].get('data-note-url')
                if url:
                    return url if url.startswith('http') else f"{self.config.note_base_url}{url}"

            # パターン2: href属性で /n/ を含むリンク
            article_links = soup.select('a[href*="/n/"]')
            for link in article_links:
                href = link.get('href', '')
                if '/n/' in href and self.config.note_username in href:
                    return href if href.startswith('http') else f"{self.config.note_base_url}{href}"

            # パターン3: API経由で取得（公開日でソート）
            api_url = f"{self.config.note_base_url}/api/v2/creators/{self.config.note_username}/contents?kind=note&page=1"
            api_response = requests.get(api_url, headers=self.headers, timeout=30)
            if api_response.status_code == 200:
                data = api_response.json()
                contents = data.get('data', {}).get('contents', [])
                if contents:
                    # publishAtで降順ソートして最新記事を取得
                    sorted_contents = sorted(
                        contents,
                        key=lambda x: x.get('publishAt', ''),
                        reverse=True
                    )
                    latest_note = sorted_contents[0]
                    note_key = latest_note.get('key')
                    note_title = latest_note.get('name', '')[:50]
                    publish_at = latest_note.get('publishAt', 'N/A')
                    print(f"   📝 最新記事: {note_title}...")
                    print(f"   📅 公開日: {publish_at}")
                    if note_key:
                        return f"{self.config.note_base_url}/{self.config.note_username}/n/{note_key}"

            print("⚠️ 記事URLが見つかりませんでした")
            return None

        except Exception as e:
            print(f"❌ プロフィールページ取得エラー: {e}")
            return None

    def fetch_article(self, url: str) -> Optional[Article]:
        """記事本文を取得"""
        print(f"📄 記事を取得中: {url}")

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # タイトル取得
            title = ""
            title_elem = soup.select_one('h1.o-noteContentHeader__title, h1[class*="title"], article h1')
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                og_title = soup.select_one('meta[property="og:title"]')
                if og_title:
                    title = og_title.get('content', '')

            # 本文取得
            content = ""
            content_selectors = [
                '.note-common-styles__textnote-body',
                '.o-noteContentText',
                'article .p-article__content',
                '.note-body',
                'article'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 不要な要素を削除
                    for unwanted in content_elem.select('script, style, nav, footer, .ads'):
                        unwanted.decompose()
                    content = content_elem.get_text(separator='\n', strip=True)
                    if len(content) > 100:
                        break

            if not content:
                print("⚠️ 本文が取得できませんでした")
                return None

            print(f"   ✅ タイトル: {title[:50]}...")
            print(f"   ✅ 本文: {len(content)}文字")

            return Article(
                title=title,
                url=url,
                content=content
            )

        except Exception as e:
            print(f"❌ 記事取得エラー: {e}")
            return None


class InfographicFinder:
    """最新インフォグラフィック検索クラス"""

    def __init__(self, config: Config):
        self.config = config

    def find_latest_images(self) -> list[Path]:
        """最新のインフォグラフィック画像を特定"""
        infographic_dir = self.config.infographic_dir

        if not infographic_dir.exists():
            print(f"⚠️ インフォグラフィックディレクトリが存在しません: {infographic_dir}")
            return []

        # タイムスタンプ付きフォルダを探す (YYYYMMDDHHMMSS_*)
        folders = []
        for item in infographic_dir.iterdir():
            if item.is_dir() and re.match(r'^\d{14}_', item.name):
                folders.append(item)

        if not folders:
            # フォルダがない場合、直接画像を探す
            images = list(infographic_dir.glob('*.png')) + list(infographic_dir.glob('*.jpg'))
            if images:
                # 更新日時でソート
                images.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                print(f"   📸 直接配置の画像: {len(images)}枚")
                return images[:5]
            return []

        # 最新フォルダを取得
        folders.sort(key=lambda x: x.name, reverse=True)
        latest_folder = folders[0]
        print(f"   📁 最新フォルダ: {latest_folder.name}")

        # フォルダ内の画像を取得
        images = list(latest_folder.glob('*.png')) + list(latest_folder.glob('*.jpg'))
        images.sort(key=lambda x: x.name)

        print(f"   📸 画像: {len(images)}枚")
        return images


class GensparkRewriter:
    """Genspark AIリライタークラス"""

    def __init__(self, config: Config):
        self.config = config

    async def rewrite(self, context: BrowserContext, article: Article, infographic_images: list[Path]) -> Optional[str]:
        """Genspark AIで記事をリライト"""
        page = await context.new_page()
        output_dir = self._get_output_dir()

        try:
            # プロンプトを準備
            prompt = await self._prepare_prompt(article, infographic_images)

            # プロンプトを保存（デバッグ用）
            async with aiofiles.open(output_dir / "prompt.txt", 'w', encoding='utf-8') as f:
                await f.write(prompt)
            print(f"   📝 プロンプト保存: {output_dir / 'prompt.txt'}")
            print(f"   📝 プロンプト文字数: {len(prompt)}文字")

            print("📍 Genspark AIにアクセス中...")
            await page.goto(self.config.genspark_chat_url, wait_until="domcontentloaded", timeout=120000)

            # ページが完全にロードされるまで待機
            print("   ⏳ ページ読み込み待機中...")
            await page.wait_for_timeout(5000)

            # スクリーンショット保存
            await page.screenshot(path=str(output_dir / "debug_01_initial.png"))

            # デバッグモード
            if self.config.debug_mode:
                print("\n🔍 デバッグモード: ページを確認してください")
                print("   Playwright Inspectorで Resume をクリックして続行")
                await page.pause()

            # 入力欄が表示されるまで待機
            print("   ⏳ 入力欄を待機中...")
            try:
                await page.wait_for_selector('textarea', timeout=30000)
            except:
                print("   ⚠️ textarea が見つかりません、続行します")

            # Claude Opus 4.5モデルを選択
            await self._select_model(page)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(output_dir / "debug_02_model_selected.png"))

            # プロンプトを入力
            print("✍️ プロンプトを入力中...")
            await self._input_prompt(page, prompt)
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(output_dir / "debug_03_prompt_entered.png"))

            # 送信
            print("🚀 送信中...")
            await self._submit(page)
            await page.wait_for_timeout(5000)
            await page.screenshot(path=str(output_dir / "debug_04_submitted.png"))

            # レスポンス待機
            response = await self._wait_for_response(page)

            if response:
                await page.screenshot(path=str(output_dir / "debug_05_response.png"))
                # レスポンスを保存
                async with aiofiles.open(output_dir / "raw_response.txt", 'w', encoding='utf-8') as f:
                    await f.write(response)
                return response
            else:
                await page.screenshot(path=str(output_dir / "error_no_response.png"))
                return None

        except Exception as e:
            print(f"❌ Genspark処理エラー: {e}")
            try:
                await page.screenshot(path=str(output_dir / "error_exception.png"))
            except:
                pass
            return None
        finally:
            await page.close()

    def _get_output_dir(self) -> Path:
        """出力ディレクトリを取得"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = self.config.output_dir / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    async def _prepare_prompt(self, article: Article, infographic_images: list[Path]) -> str:
        """プロンプトを準備"""
        # テンプレート読み込み
        async with aiofiles.open(self.config.prompt_file, 'r', encoding='utf-8') as f:
            template = await f.read()

        # 画像リスト作成
        image_list = "\n".join([f"- 画像{i+1}: {img.name}" for i, img in enumerate(infographic_images)])
        if not image_list:
            image_list = "(インフォグラフィック画像なし)"

        # テンプレート置換
        prompt = template.format(
            title=article.title,
            url=article.url,
            content=article.content,
            infographic_images=image_list
        )

        return prompt

    async def _select_model(self, page: Page) -> None:
        """Claude Opus 4.5モデルを選択"""
        print("🔧 Claude Opus 4.5を選択中...")

        try:
            # モデル選択ボタンを探す
            model_selectors = [
                'button:has-text("Claude")',
                'button:has-text("Model")',
                'button:has-text("モデル")',
                '[class*="model-select"]',
                '[class*="dropdown"]',
            ]

            for selector in model_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue

            # Claude Opus 4.5を選択
            opus_selectors = [
                'text="Claude Opus 4.5"',
                'text="claude-opus-4-5"',
                'text="Opus 4.5"',
                '[data-model*="opus"]',
            ]

            for selector in opus_selectors:
                try:
                    option = page.locator(selector).first
                    if await option.is_visible():
                        await option.click()
                        print("   ✅ Claude Opus 4.5を選択")
                        return
                except:
                    continue

            print("   ⚠️ モデル選択できず、デフォルトモデルを使用")

        except Exception as e:
            print(f"   ⚠️ モデル選択エラー: {e}")

    async def _input_prompt(self, page: Page, prompt: str) -> None:
        """プロンプトを入力"""
        input_selectors = [
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="Message"]',
            'textarea[placeholder*="Ask"]',
            'textarea[placeholder*="Type"]',
            'textarea[placeholder*="Enter"]',
            'textarea',
            '[contenteditable="true"]',
            'input[type="text"]',
        ]

        for selector in input_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                for i in range(count):
                    element = elements.nth(i)
                    if await element.is_visible():
                        await element.click()
                        await page.wait_for_timeout(500)
                        await element.fill(prompt)
                        print(f"   📝 プロンプト入力完了（{len(prompt)}文字）")
                        print(f"   📝 使用セレクタ: {selector}")
                        return
            except Exception as e:
                continue

        # フォールバック: JavaScriptで入力
        print("   ⚠️ 通常入力失敗、JavaScript経由で入力を試みます...")
        try:
            await page.evaluate('''
                (text) => {
                    const textareas = document.querySelectorAll('textarea');
                    for (const ta of textareas) {
                        if (ta.offsetParent !== null) {
                            ta.focus();
                            ta.value = text;
                            ta.dispatchEvent(new Event('input', { bubbles: true }));
                            ta.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }
            ''', prompt)
            print(f"   📝 JavaScript経由で入力完了（{len(prompt)}文字）")
            return
        except:
            pass

        raise Exception("入力欄が見つかりません")

    async def _submit(self, page: Page) -> None:
        """送信"""
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Send")',
            'button:has-text("送信")',
            'button[aria-label*="send"]',
            'button[aria-label*="Send"]',
            'button[aria-label*="submit"]',
            '[class*="send-button"]',
            '[class*="submit-button"]',
            'button svg[class*="send"]',
            # SVGアイコンを含むボタン（送信アイコン）
            'button:has(svg)',
        ]

        for selector in submit_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                for i in range(count):
                    btn = elements.nth(i)
                    if await btn.is_visible():
                        # テキストエリアの近くにあるボタンを優先
                        box = await btn.bounding_box()
                        if box and box['y'] > 200:  # 下部にあるボタン
                            await btn.click()
                            print(f"   ✅ 送信完了（セレクタ: {selector}）")
                            return
            except:
                continue

        # フォールバック: 可視の最後のボタンをクリック
        try:
            buttons = page.locator('button')
            count = await buttons.count()
            for i in range(count - 1, -1, -1):
                btn = buttons.nth(i)
                if await btn.is_visible():
                    box = await btn.bounding_box()
                    if box and box['y'] > 400:  # 画面下部
                        await btn.click()
                        print("   ✅ 送信完了（最後のボタン）")
                        return
        except:
            pass

        # 最終フォールバック: Enterキーで送信
        await page.keyboard.press("Enter")
        print("   ⌨️ Enterキーで送信")

    async def _wait_for_response(self, page: Page) -> Optional[str]:
        """レスポンスを待機（stability-based）"""
        print(f"⏳ レスポンスを待機中（最大{self.config.response_timeout_minutes}分）...")

        timeout_ms = self.config.response_timeout_minutes * 60 * 1000
        check_interval = self.config.check_interval_seconds * 1000
        stability_threshold = self.config.stability_threshold

        start_time = asyncio.get_event_loop().time()
        last_content = ""
        stable_count = 0

        # レスポンス要素のセレクタ候補
        response_selectors = [
            '[class*="message"][class*="assistant"]',
            '[class*="ai-message"]',
            '[class*="bot-message"]',
            '[class*="response"]',
            '[class*="answer"]',
            '[class*="chat-message"]:last-child',
            '[class*="prose"]',
            '.markdown-body',
            '[data-role="assistant"]',
            # より汎用的なセレクタ
            'article',
            '[class*="content"]',
        ]

        while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout_ms:
            elapsed = int(asyncio.get_event_loop().time() - start_time)

            try:
                current_content = ""

                # 各セレクタで要素を探す
                for selector in response_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            # 全要素のテキストを結合
                            for i in range(count):
                                elem = elements.nth(i)
                                if await elem.is_visible():
                                    text = await elem.inner_text()
                                    # 長いテキストを持つ要素を採用
                                    if len(text) > len(current_content) and len(text) > 100:
                                        current_content = text
                    except:
                        continue

                # ページ全体からテキストを取得（フォールバック）
                if not current_content or len(current_content) < 100:
                    try:
                        body_text = await page.locator('body').inner_text()
                        # 入力プロンプト以降のテキストを抽出
                        if '=== LINKEDIN ===' in body_text:
                            # レスポンスが含まれている
                            current_content = body_text
                    except:
                        pass

                if current_content and current_content == last_content and len(current_content) > 100:
                    stable_count += 1
                    print(f"⏳ {elapsed}秒経過... (安定: {stable_count}/{stability_threshold}, {len(current_content)}文字)")

                    if stable_count >= stability_threshold:
                        print(f"✅ レスポンス完了（{elapsed}秒、{len(current_content)}文字）")
                        return current_content
                else:
                    stable_count = 0
                    last_content = current_content
                    content_len = len(current_content) if current_content else 0
                    print(f"⏳ {elapsed}秒経過... (生成中: {content_len}文字)")

            except Exception as e:
                print(f"   ⚠️ チェックエラー: {e}")

            await page.wait_for_timeout(check_interval)

        print("⚠️ タイムアウト")
        return last_content if last_content else None


class OutputManager:
    """出力管理クラス"""

    def __init__(self, config: Config):
        self.config = config

    def get_output_dir(self) -> Path:
        """タイムスタンプ付き出力ディレクトリを作成"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = self.config.output_dir / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    async def save_all(self, output_dir: Path, article: Article, response: str, infographic_images: list[Path]) -> None:
        """全ての出力を保存"""
        # 元記事を保存
        await self._save_original_article(output_dir, article)

        # レスポンスをパース
        linkedin_content, x_format, x_posts = self._parse_response(response)

        # LinkedIn下書きを保存
        await self._save_linkedin_draft(output_dir, article, linkedin_content, infographic_images)

        # X下書きを保存
        await self._save_x_draft(output_dir, article, x_format, x_posts, infographic_images)

        print(f"   📁 出力ディレクトリ: {output_dir}")

    async def _save_original_article(self, output_dir: Path, article: Article) -> None:
        """元記事を保存"""
        filepath = output_dir / "original_article.md"
        content = f"""# {article.title}

URL: {article.url}
取得日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

{article.content}
"""
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(content)
        print(f"   ✅ original_article.md")

    def _parse_response(self, response: str) -> tuple[str, str, list[str]]:
        """レスポンスをLinkedInとXに分割

        Returns:
            tuple: (linkedin_content, x_format, x_posts)
            - linkedin_content: LinkedIn投稿文
            - x_format: "single" または "thread"
            - x_posts: X投稿のリスト（単一の場合は1要素、スレッドの場合は複数）
        """
        linkedin_content = ""
        x_format = "single"
        x_posts = []

        # === LinkedIn部分を抽出 ===
        linkedin_matches = list(re.finditer(
            r'--LINKEDIN_START--\s*(.*?)\s*--LINKEDIN_END--',
            response,
            re.DOTALL
        ))
        if linkedin_matches:
            linkedin_content = linkedin_matches[-1].group(1).strip()
            if '(ここにLinkedIn投稿文を生成)' in linkedin_content:
                linkedin_content = ""

        # フォールバック: 旧形式のマーカー
        if not linkedin_content:
            linkedin_matches = list(re.finditer(
                r'=== LINKEDIN ===\s*(.*?)(?:=== X_THREAD ===|--X_START--|$)',
                response,
                re.DOTALL
            ))
            if linkedin_matches:
                linkedin_content = linkedin_matches[-1].group(1).strip()

        # フォールバック: 絵文字で始まる構造化コンテンツを探す
        if not linkedin_content or len(linkedin_content) < 100:
            linkedin_match = re.search(
                r'([🚀📌✅🔗💡🎯][^\n]*\n[\s\S]{200,}?)(?:--|===|$)',
                response,
                re.DOTALL
            )
            if linkedin_match:
                linkedin_content = linkedin_match.group(1).strip()

        # === X形式を判定 ===
        format_matches = list(re.finditer(
            r'--X_FORMAT--\s*(.*?)\s*--X_FORMAT_END--',
            response,
            re.DOTALL
        ))
        if format_matches:
            format_str = format_matches[-1].group(1).strip().lower()
            if 'thread' in format_str:
                x_format = "thread"
            else:
                x_format = "single"

        # === X投稿を抽出 ===
        x_matches = list(re.finditer(
            r'--X_START--\s*(.*?)\s*--X_END--',
            response,
            re.DOTALL
        ))
        if x_matches:
            x_content = x_matches[-1].group(1).strip()
            # テンプレートのプレースホルダーを除外
            if '(単一ポストの場合' in x_content or '(ここにX投稿文を生成)' in x_content:
                x_content = ""

            if x_content:
                # スレッド形式: --- で分割
                if '---' in x_content:
                    posts = [p.strip() for p in x_content.split('---') if p.strip()]
                    # 例文や説明を除外
                    x_posts = [p for p in posts if not p.startswith('例（') and len(p) > 20]
                elif x_format == "thread":
                    # ---区切りがないが、thread形式が指定されている場合
                    # ハッシュタグで終わる行で分割（各ツイートはハッシュタグで終わる）
                    # パターン: テキスト + ハッシュタグ + 改行
                    hashtag_pattern = r'(.*?#\w+(?:\s+#\w+)*)\s*\n'
                    hashtag_matches = re.findall(hashtag_pattern, x_content + '\n', re.DOTALL)
                    if hashtag_matches and len(hashtag_matches) > 1:
                        x_posts = [p.strip() for p in hashtag_matches if p.strip() and len(p.strip()) > 20]
                    else:
                        # ハッシュタグ分割できない場合、段落で分割
                        paragraphs = re.split(r'\n\s*\n', x_content)
                        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
                        if len(paragraphs) > 1:
                            x_posts = paragraphs
                        else:
                            x_posts = [x_content]
                            x_format = "single"
                else:
                    # 単一ポスト
                    x_posts = [x_content]

                # 形式を自動判定（フォーマットマーカーがない場合）
                if len(x_posts) > 1:
                    x_format = "thread"

        # フォールバック: 旧形式のマーカー（JSON形式）
        if not x_posts:
            x_thread_matches = list(re.finditer(
                r'=== X_THREAD ===\s*([\s\S]*?)(?:Notionに保存|Claude|$)',
                response,
                re.DOTALL
            ))
            if x_thread_matches:
                x_json = x_thread_matches[-1].group(1).strip()
                try:
                    json_match = re.search(r'\{[\s\S]*?"thread"[\s\S]*?\}', x_json)
                    if json_match:
                        data = json.loads(json_match.group())
                        threads = data.get('thread', [])
                        x_posts = [t.get('text', '') for t in threads if t.get('text')]
                        if len(x_posts) > 1:
                            x_format = "thread"
                except:
                    pass

        return linkedin_content, x_format, x_posts

    async def _save_linkedin_draft(self, output_dir: Path, article: Article, content: str, images: list[Path]) -> None:
        """LinkedIn下書きを保存"""
        filepath = output_dir / "linkedin_draft.md"

        # 画像パス一覧
        image_list = "\n".join([f"- {img}" for img in images]) if images else "(なし)"

        draft = f"""# LinkedIn Draft
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source: {article.url}
Character Count: {len(content)}

---

{content}

---

## Images
{image_list}
"""
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(draft)
        print(f"   ✅ linkedin_draft.md ({len(content)}文字)")

    async def _save_x_draft(self, output_dir: Path, article: Article, x_format: str, posts: list[str], images: list[Path]) -> None:
        """X下書きを保存（単一/スレッド形式対応）"""
        filepath = output_dir / "x_draft.md"

        # 画像パス一覧
        image_list = "\n".join([f"- {img}" for img in images]) if images else "(なし)"

        # 投稿内容を整形
        if x_format == "thread" and len(posts) > 1:
            # スレッド形式
            posts_content = ""
            total_chars = 0
            for i, post in enumerate(posts, 1):
                char_count = len(post)
                total_chars += char_count
                posts_content += f"### ツイート {i} ({char_count}文字)\n\n{post}\n\n"

            draft = f"""# X Draft (スレッド形式: {len(posts)}ツイート)
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source: {article.url}
Format: thread
Total Posts: {len(posts)}
Total Characters: {total_chars}

---

{posts_content}
---

## Images
{image_list}
"""
            print(f"   ✅ x_draft.md (スレッド: {len(posts)}ツイート, 計{total_chars}文字)")
        else:
            # 単一ポスト形式
            content = posts[0] if posts else ""
            draft = f"""# X Draft (単一ポスト)
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source: {article.url}
Format: single
Character Count: {len(content)}

---

{content}

---

## Images
{image_list}
"""
            print(f"   ✅ x_draft.md (単一: {len(content)}文字)")

        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(draft)


class SNSPoster:
    """SNS予約下書き投稿クラス（LinkedIn & X）"""

    def __init__(self, config: Config):
        self.config = config

    async def post_to_sns(
        self,
        context: BrowserContext,
        linkedin_content: str,
        x_posts: list[str],
        article_url: str,
        infographic_images: list[Path]
    ) -> dict:
        """LinkedInとXに予約下書きを投稿"""
        results = {
            "linkedin": {"success": False, "message": ""},
            "x": {"success": False, "message": "", "posts": []}
        }

        # LinkedIn投稿
        print("\n📘 LinkedInに予約下書きを投稿中...")
        try:
            linkedin_result = await self._post_to_linkedin(context, linkedin_content, article_url, infographic_images)
            results["linkedin"] = linkedin_result
        except Exception as e:
            results["linkedin"]["message"] = f"エラー: {e}"
            print(f"   ❌ LinkedIn投稿エラー: {e}")

        # X投稿
        print("\n📱 Xに予約下書きを投稿中...")
        try:
            x_result = await self._post_to_x(context, x_posts, article_url, infographic_images)
            results["x"] = x_result
        except Exception as e:
            results["x"]["message"] = f"エラー: {e}"
            print(f"   ❌ X投稿エラー: {e}")

        return results

    async def _post_to_linkedin(
        self,
        context: BrowserContext,
        content: str,
        article_url: str,
        images: list[Path]
    ) -> dict:
        """LinkedInに予約下書きを投稿"""
        page = await context.new_page()
        result = {"success": False, "message": ""}

        try:
            # 投稿内容にURLを追加
            full_content = f"{content}\n\n🔗 {article_url}"

            # 予約日時を計算（1日後の同じ時刻）
            schedule_time = datetime.now() + timedelta(days=self.config.linkedin_delay_days)
            print(f"   📅 予約日時: {schedule_time.strftime('%Y-%m-%d %H:%M')}")

            # LinkedInにアクセス
            print(f"   🌐 LinkedInにアクセス中...")
            await page.goto(self.config.linkedin_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # ログイン確認
            if "login" in page.url.lower() or "signin" in page.url.lower():
                print("   ⚠️ LinkedInにログインしていません。手動でログインしてください。")
                result["message"] = "ログインが必要です"
                return result

            # 投稿作成ボタンをクリック
            print("   ✍️ 投稿作成画面を開く...")
            create_post_selectors = [
                'button:has-text("Start a post")',
                'button:has-text("投稿を開始")',
                '[class*="share-box-feed-entry__trigger"]',
                '[aria-label*="Start a post"]',
                '[aria-label*="投稿を作成"]',
                '.share-box-feed-entry__top-bar',
            ]

            clicked = False
            for selector in create_post_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        clicked = True
                        print(f"   ✅ 投稿ボタンクリック（{selector}）")
                        break
                except:
                    continue

            if not clicked:
                print("   ⚠️ 投稿ボタンが見つかりません")
                result["message"] = "投稿ボタンが見つかりません"
                return result

            await page.wait_for_timeout(2000)

            # 投稿エディタに入力
            print("   📝 投稿内容を入力中...")
            editor_selectors = [
                '[role="textbox"][aria-label*="post"]',
                '[role="textbox"][aria-label*="投稿"]',
                '[contenteditable="true"][class*="ql-editor"]',
                '.ql-editor[data-placeholder]',
                '[contenteditable="true"]',
            ]

            input_success = False
            for selector in editor_selectors:
                try:
                    editor = page.locator(selector).first
                    if await editor.is_visible(timeout=5000):
                        await editor.click()
                        await page.wait_for_timeout(500)
                        await editor.fill(full_content)
                        input_success = True
                        print(f"   ✅ 内容入力完了（{len(full_content)}文字）")
                        break
                except:
                    continue

            if not input_success:
                # JavaScript fallback
                try:
                    await page.evaluate('''
                        (text) => {
                            const editors = document.querySelectorAll('[contenteditable="true"]');
                            for (const editor of editors) {
                                if (editor.offsetParent !== null) {
                                    editor.focus();
                                    editor.innerHTML = text.replace(/\\n/g, '<br>');
                                    return true;
                                }
                            }
                            return false;
                        }
                    ''', full_content)
                    input_success = True
                    print(f"   ✅ JS経由で入力完了（{len(full_content)}文字）")
                except:
                    pass

            if not input_success:
                result["message"] = "投稿エディタが見つかりません"
                return result

            await page.wait_for_timeout(1000)

            # 画像を添付（最初の1枚のみ）
            if images:
                await self._attach_image_linkedin(page, images[0])

            # 予約設定を開く
            print("   ⏰ 予約設定を開く...")
            await self._set_linkedin_schedule(page, schedule_time)

            # 下書き保存
            print("   💾 下書きとして保存...")
            await self._save_linkedin_draft(page)

            result["success"] = True
            result["message"] = f"予約下書き保存完了（{schedule_time.strftime('%Y-%m-%d %H:%M')}）"
            print(f"   ✅ {result['message']}")

        except Exception as e:
            result["message"] = f"エラー: {e}"
            print(f"   ❌ エラー: {e}")
        finally:
            await page.close()

        return result

    async def _attach_image_linkedin(self, page: Page, image_path: Path) -> None:
        """LinkedInに画像を添付"""
        try:
            print(f"   📷 画像を添付中: {image_path.name}")
            # 画像添付ボタンを探す
            media_selectors = [
                'button[aria-label*="Add media"]',
                'button[aria-label*="メディアを追加"]',
                'button:has-text("Add media")',
                '[class*="image-sharing"]',
                '[class*="media-upload"]',
            ]

            for selector in media_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_timeout(1000)

                        # ファイル入力
                        file_input = page.locator('input[type="file"]').first
                        await file_input.set_input_files(str(image_path))
                        await page.wait_for_timeout(2000)
                        print(f"   ✅ 画像添付完了")
                        return
                except:
                    continue

            print("   ⚠️ 画像添付ボタンが見つかりません")
        except Exception as e:
            print(f"   ⚠️ 画像添付エラー: {e}")

    async def _set_linkedin_schedule(self, page: Page, schedule_time: datetime) -> None:
        """LinkedIn予約時刻を設定"""
        try:
            # 時計/カレンダーアイコンを探す
            schedule_selectors = [
                'button[aria-label*="Schedule"]',
                'button[aria-label*="予約"]',
                'button:has-text("Schedule")',
                '[class*="schedule"]',
                '[class*="clock"]',
            ]

            for selector in schedule_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue

            # 日時を設定（LinkedInのUIに依存）
            # 日付入力
            date_input = page.locator('input[type="date"], input[name*="date"]').first
            if await date_input.is_visible(timeout=2000):
                await date_input.fill(schedule_time.strftime("%Y-%m-%d"))

            # 時間入力
            time_input = page.locator('input[type="time"], input[name*="time"]').first
            if await time_input.is_visible(timeout=2000):
                await time_input.fill(schedule_time.strftime("%H:%M"))

            print(f"   ✅ 予約時刻設定: {schedule_time.strftime('%Y-%m-%d %H:%M')}")

        except Exception as e:
            print(f"   ⚠️ 予約設定エラー（手動設定が必要かもしれません）: {e}")

    async def _save_linkedin_draft(self, page: Page) -> None:
        """LinkedInの下書きを保存"""
        try:
            # 保存ボタンを探す
            save_selectors = [
                'button:has-text("Save as draft")',
                'button:has-text("下書きとして保存")',
                'button:has-text("Save")',
                'button:has-text("保存")',
                '[class*="draft"]',
            ]

            for selector in save_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        print("   ✅ 下書き保存完了")
                        return
                except:
                    continue

            # 閉じるボタンを押して下書き保存を促す
            close_selectors = [
                'button[aria-label*="Close"]',
                'button[aria-label*="閉じる"]',
                'button:has-text("Close")',
            ]

            for selector in close_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_timeout(1000)
                        # 下書き保存確認ダイアログ
                        save_btn = page.locator('button:has-text("Save"), button:has-text("保存")').first
                        if await save_btn.is_visible(timeout=2000):
                            await save_btn.click()
                        print("   ✅ 下書き保存完了（閉じるボタン経由）")
                        return
                except:
                    continue

            print("   ⚠️ 保存ボタンが見つかりません（手動保存が必要）")

        except Exception as e:
            print(f"   ⚠️ 保存エラー: {e}")

    async def _post_to_x(
        self,
        context: BrowserContext,
        posts: list[str],
        article_url: str,
        images: list[Path]
    ) -> dict:
        """Xに予約下書きを投稿（スレッド形式）"""
        page = await context.new_page()
        result = {"success": False, "message": "", "posts": []}

        try:
            # Xにアクセス
            print(f"   🌐 Xにアクセス中...")
            await page.goto(self.config.x_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # ログイン確認
            if "login" in page.url.lower():
                print("   ⚠️ Xにログインしていません。手動でログインしてください。")
                result["message"] = "ログインが必要です"
                return result

            # 各ポストの予約時刻を計算
            base_time = datetime.now() + timedelta(days=self.config.x_first_post_delay_days)
            schedule_times = []
            for i in range(len(posts)):
                post_time = base_time + timedelta(hours=i * self.config.x_interval_hours)
                schedule_times.append(post_time)
                print(f"   📅 ツイート{i+1} 予約: {post_time.strftime('%Y-%m-%d %H:%M')}")

            # 最後のポストにURLを追加
            posts_with_url = posts.copy()
            if posts_with_url:
                posts_with_url[-1] = f"{posts_with_url[-1]}\n{article_url}"

            # 各ツイートを投稿（下書き保存）
            for i, (post_text, schedule_time) in enumerate(zip(posts_with_url, schedule_times)):
                print(f"\n   📝 ツイート {i+1}/{len(posts_with_url)} を作成中...")
                post_result = await self._create_x_post(page, post_text, schedule_time, images[0] if i == 0 and images else None)
                result["posts"].append(post_result)

                if not post_result["success"]:
                    print(f"   ⚠️ ツイート{i+1}の投稿に失敗")
                else:
                    print(f"   ✅ ツイート{i+1}の下書き保存完了")

                await page.wait_for_timeout(2000)

            # 全ポスト成功したかチェック
            success_count = sum(1 for p in result["posts"] if p["success"])
            result["success"] = success_count == len(posts)
            result["message"] = f"{success_count}/{len(posts)}件の下書き保存完了"
            print(f"\n   📊 結果: {result['message']}")

        except Exception as e:
            result["message"] = f"エラー: {e}"
            print(f"   ❌ エラー: {e}")
        finally:
            await page.close()

        return result

    async def _create_x_post(
        self,
        page: Page,
        text: str,
        schedule_time: datetime,
        image: Optional[Path]
    ) -> dict:
        """X（Twitter）の予約下書きを作成"""
        result = {"success": False, "message": "", "scheduled_time": schedule_time.strftime("%Y-%m-%d %H:%M")}

        try:
            # 投稿ボタンをクリック
            compose_selectors = [
                '[data-testid="SideNav_NewTweet_Button"]',
                'a[href="/compose/tweet"]',
                'button[aria-label*="ポスト"]',
                'button[aria-label*="Post"]',
                'button[aria-label*="Tweet"]',
            ]

            clicked = False
            for selector in compose_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                # フォールバック: 直接URLへ
                await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")

            await page.wait_for_timeout(2000)

            # テキスト入力
            editor_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[role="textbox"][data-testid*="tweet"]',
                '[contenteditable="true"][class*="DraftEditor"]',
                '[contenteditable="true"]',
            ]

            input_success = False
            for selector in editor_selectors:
                try:
                    editor = page.locator(selector).first
                    if await editor.is_visible(timeout=5000):
                        await editor.click()
                        await page.wait_for_timeout(500)
                        # 1文字ずつタイプ（日本語対応）
                        await editor.fill(text)
                        input_success = True
                        break
                except:
                    continue

            if not input_success:
                result["message"] = "テキストエリアが見つかりません"
                return result

            await page.wait_for_timeout(1000)

            # 画像添付
            if image:
                await self._attach_image_x(page, image)

            # 予約設定
            await self._set_x_schedule(page, schedule_time)

            # 下書きとして保存（予約確定）
            await self._save_x_draft(page)

            result["success"] = True
            result["message"] = f"予約完了: {schedule_time.strftime('%Y-%m-%d %H:%M')}"

        except Exception as e:
            result["message"] = f"エラー: {e}"

        return result

    async def _attach_image_x(self, page: Page, image_path: Path) -> None:
        """Xに画像を添付"""
        try:
            print(f"      📷 画像添付中: {image_path.name}")
            # 画像ボタン or ファイル入力
            file_input = page.locator('input[type="file"][accept*="image"]').first
            if await file_input.count() > 0:
                await file_input.set_input_files(str(image_path))
                await page.wait_for_timeout(2000)
                print("      ✅ 画像添付完了")
            else:
                # 画像ボタンをクリック
                media_btn = page.locator('[data-testid="fileInput"], [aria-label*="メディア"], [aria-label*="Media"]').first
                if await media_btn.is_visible(timeout=2000):
                    await media_btn.click()
                    await page.wait_for_timeout(1000)
                    file_input = page.locator('input[type="file"]').first
                    await file_input.set_input_files(str(image_path))
                    await page.wait_for_timeout(2000)
                    print("      ✅ 画像添付完了")
        except Exception as e:
            print(f"      ⚠️ 画像添付スキップ: {e}")

    async def _set_x_schedule(self, page: Page, schedule_time: datetime) -> None:
        """X予約時刻を設定"""
        try:
            # 予約ボタンを探す（カレンダーアイコン）
            schedule_selectors = [
                '[data-testid="scheduleOption"]',
                '[aria-label*="スケジュール"]',
                '[aria-label*="Schedule"]',
                'button:has(svg[viewBox*="calendar"])',
            ]

            for selector in schedule_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue

            # 日付選択
            # 年
            year_input = page.locator('select[name*="year"], [data-testid*="year"]').first
            if await year_input.is_visible(timeout=2000):
                await year_input.select_option(str(schedule_time.year))

            # 月
            month_input = page.locator('select[name*="month"], [data-testid*="month"]').first
            if await month_input.is_visible(timeout=2000):
                await month_input.select_option(str(schedule_time.month))

            # 日
            day_input = page.locator('select[name*="day"], [data-testid*="day"]').first
            if await day_input.is_visible(timeout=2000):
                await day_input.select_option(str(schedule_time.day))

            # 時間
            hour_input = page.locator('select[name*="hour"], [data-testid*="hour"]').first
            if await hour_input.is_visible(timeout=2000):
                await hour_input.select_option(str(schedule_time.hour))

            # 分
            minute_input = page.locator('select[name*="minute"], [data-testid*="minute"]').first
            if await minute_input.is_visible(timeout=2000):
                # 最も近い分を選択（0, 5, 10, 15, ...）
                rounded_minute = (schedule_time.minute // 5) * 5
                await minute_input.select_option(str(rounded_minute))

            # 確定ボタン
            confirm_btn = page.locator('button:has-text("Confirm"), button:has-text("確認")').first
            if await confirm_btn.is_visible(timeout=2000):
                await confirm_btn.click()

            print(f"      ✅ 予約時刻設定: {schedule_time.strftime('%Y-%m-%d %H:%M')}")

        except Exception as e:
            print(f"      ⚠️ 予約設定エラー: {e}")

    async def _save_x_draft(self, page: Page) -> None:
        """Xの予約投稿を確定（下書き保存）"""
        try:
            # 予約確定ボタン
            schedule_btn_selectors = [
                '[data-testid="schedulePostButton"]',
                'button:has-text("Schedule")',
                'button:has-text("予約設定")',
                '[data-testid="scheduledConfirmationPrimaryAction"]',
            ]

            for selector in schedule_btn_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        print("      ✅ 予約投稿確定")
                        return
                except:
                    continue

            # フォールバック: 閉じて下書き保存
            close_btn = page.locator('button[aria-label*="Close"], button[aria-label*="閉じる"]').first
            if await close_btn.is_visible(timeout=2000):
                await close_btn.click()
                await page.wait_for_timeout(1000)

                # 下書き保存確認
                save_btn = page.locator('button:has-text("Save"), button:has-text("保存")').first
                if await save_btn.is_visible(timeout=2000):
                    await save_btn.click()
                    print("      ✅ 下書き保存完了")

        except Exception as e:
            print(f"      ⚠️ 保存エラー: {e}")


class SNSContentGenerator:
    """メインオーケストレーションクラス"""

    def __init__(self, config: Config):
        self.config = config
        self.fetcher = NoteArticleFetcher(config)
        self.infographic_finder = InfographicFinder(config)
        self.rewriter = GensparkRewriter(config)
        self.output_manager = OutputManager(config)
        self.sns_poster = SNSPoster(config)

    async def run(self, post_to_sns: bool = False) -> None:
        """メイン処理を実行

        Args:
            post_to_sns: True の場合、LinkedIn/Xに予約下書きを投稿
        """
        print("=" * 50)
        print("🚀 SNS Content Generator")
        print("=" * 50)
        print(f"📌 note.comユーザー: {self.config.note_username}")
        print(f"📁 出力先: {self.config.output_dir}")
        print(f"🔧 デバッグモード: {'ON' if self.config.debug_mode else 'OFF'}")
        print(f"📤 SNS投稿: {'ON' if post_to_sns else 'OFF'}")
        print("=" * 50 + "\n")

        # 1. 最新記事URLを取得
        print("📡 Step 1: 最新記事を取得")
        article_url = self.fetcher.get_latest_article_url()
        if not article_url:
            print("❌ 記事URLが取得できませんでした")
            return

        # 2. 記事本文を取得
        article = self.fetcher.fetch_article(article_url)
        if not article:
            print("❌ 記事本文が取得できませんでした")
            return

        # 3. インフォグラフィック画像を検索
        print("\n📸 Step 2: インフォグラフィック画像を検索")
        infographic_images = self.infographic_finder.find_latest_images()

        # 4. Genspark AIでリライト
        print("\n🤖 Step 3: Genspark AIでリライト")
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                str(self.config.browser_data_dir),
                headless=False,
                viewport={"width": 1280, "height": 900},
                args=['--disable-blink-features=AutomationControlled']
            )

            try:
                response = await self.rewriter.rewrite(context, article, infographic_images)

                if not response:
                    print("❌ リライトレスポンスが取得できませんでした")
                    return

                # 5. 出力を保存
                print("\n💾 Step 4: 出力を保存")
                output_dir = self.output_manager.get_output_dir()
                await self.output_manager.save_all(output_dir, article, response, infographic_images)

                # 6. SNSに予約下書きを投稿（オプション）
                if post_to_sns:
                    print("\n📤 Step 5: SNSに予約下書きを投稿")

                    # レスポンスをパースしてLinkedIn/Xコンテンツを取得
                    linkedin_content, x_format, x_posts = self.output_manager._parse_response(response)

                    if linkedin_content or x_posts:
                        sns_results = await self.sns_poster.post_to_sns(
                            context=context,
                            linkedin_content=linkedin_content,
                            x_posts=x_posts,
                            article_url=article.url,
                            infographic_images=infographic_images
                        )

                        # 結果を保存
                        await self._save_sns_results(output_dir, sns_results)
                    else:
                        print("   ⚠️ 投稿するコンテンツがありません")

            finally:
                await context.close()

        print("\n" + "=" * 50)
        print("✅ 処理完了")
        print("=" * 50)

    async def _save_sns_results(self, output_dir: Path, results: dict) -> None:
        """SNS投稿結果を保存"""
        filepath = output_dir / "sns_posting_results.json"
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"   📄 投稿結果保存: {filepath.name}")


async def main():
    """エントリポイント

    Usage:
        python sns_content_generator.py              # 基本実行（下書き生成のみ）
        python sns_content_generator.py --post-sns   # 下書き生成 + SNS予約投稿
        python sns_content_generator.py --debug      # デバッグモード
    """
    # コマンドライン引数
    debug_mode = "--debug" in sys.argv
    post_to_sns = "--post-sns" in sys.argv

    # ヘルプ表示
    if "--help" in sys.argv or "-h" in sys.argv:
        print("SNS Content Generator")
        print("=" * 40)
        print("Usage: python sns_content_generator.py [OPTIONS]")
        print()
        print("Options:")
        print("  --post-sns    LinkedIn/Xに予約下書きを投稿")
        print("  --debug       デバッグモード（Playwright Inspector使用）")
        print("  --help, -h    このヘルプを表示")
        print()
        print("Note:")
        print("  --post-sns を使用する前に、LinkedIn/Xに")
        print("  ブラウザで事前ログインしておく必要があります。")
        return

    # 設定読み込み
    config_path = SCRIPT_DIR / "config.ini"
    if not config_path.exists():
        print(f"❌ 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)

    config = Config.load(config_path)

    # デバッグモードをコマンドラインで上書き
    if debug_mode:
        config.debug_mode = True

    # 実行
    generator = SNSContentGenerator(config)
    await generator.run(post_to_sns=post_to_sns)


if __name__ == "__main__":
    asyncio.run(main())
