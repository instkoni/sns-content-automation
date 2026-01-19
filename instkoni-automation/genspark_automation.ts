import { chromium, BrowserContext, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import * as https from 'https';
import * as http from 'http';

// ディレクトリ設定（__dirname基準）
const ARTICLES_DRAFTS_DIR = path.join(__dirname, '..', 'articles', 'drafts');
const ARTICLES_PUBLISHED_DIR = path.join(__dirname, '..', 'articles', 'published');
const INFOGRAPHIC_DIR = path.join(__dirname, '..', 'articles', 'infographic');

// Genspark設定
const GENSPARK_IMAGE_URL = 'https://www.genspark.ai/agents?type=image_generation_agent';
const USER_DATA_DIR = path.join(__dirname, 'browser-data');

// デバッグモード
const DEBUG_MODE = process.argv.includes('--debug');

/**
 * 最新の下書き記事を取得
 */
function getLatestDraftArticle(): { filename: string; content: string } | null {
    if (!fs.existsSync(ARTICLES_DRAFTS_DIR)) {
        console.log(`📁 ディレクトリが存在しません: ${ARTICLES_DRAFTS_DIR}`);
        return null;
    }

    const files = fs.readdirSync(ARTICLES_DRAFTS_DIR)
        .filter(f => f.endsWith('.md'))
        .map(f => ({
            name: f,
            path: path.join(ARTICLES_DRAFTS_DIR, f),
            mtime: fs.statSync(path.join(ARTICLES_DRAFTS_DIR, f)).mtime
        }))
        .sort((a, b) => b.mtime.getTime() - a.mtime.getTime());

    if (files.length === 0) {
        console.log('📭 下書き記事が見つかりません');
        return null;
    }

    const latest = files[0];
    console.log(`📄 最新の下書き: ${latest.name}`);
    return {
        filename: latest.name,
        content: fs.readFileSync(latest.path, 'utf-8')
    };
}

/**
 * 記事名からファイル名用の文字列を生成
 */
function extractArticleName(filename: string): string {
    // 日付部分を除去し、拡張子を除去
    const nameWithoutExt = filename.replace(/\.md$/, '');
    const nameWithoutDate = nameWithoutExt.replace(/^\d{4}-\d{2}-\d{2}-?/, '');
    // ファイル名に使えない文字を置換
    return nameWithoutDate.replace(/[\/\\:*?"<>|]/g, '_').substring(0, 50);
}

/**
 * タイムスタンプを生成（YYYYMMDDHHMMSS形式）
 */
function generateTimestamp(): string {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    const h = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    return `${y}${m}${d}${h}${min}${s}`;
}

/**
 * 画像をダウンロードして保存
 */
async function downloadImage(url: string, filepath: string): Promise<boolean> {
    return new Promise((resolve) => {
        const protocol = url.startsWith('https') ? https : http;
        const file = fs.createWriteStream(filepath);

        protocol.get(url, (response) => {
            if (response.statusCode === 301 || response.statusCode === 302) {
                // リダイレクト処理
                const redirectUrl = response.headers.location;
                if (redirectUrl) {
                    downloadImage(redirectUrl, filepath).then(resolve);
                    return;
                }
            }

            response.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log(`✅ 保存完了: ${filepath}`);
                resolve(true);
            });
        }).on('error', (err) => {
            fs.unlink(filepath, () => {});
            console.error(`❌ ダウンロードエラー: ${err.message}`);
            resolve(false);
        });
    });
}

/**
 * Genspark画像生成の実行
 */
async function generateImages(): Promise<void> {
    console.log('🎨 Genspark画像生成を開始します...\n');

    // 最新の下書き記事を取得
    const article = getLatestDraftArticle();
    if (!article) {
        console.log('❌ 処理する記事がありません');
        return;
    }

    // インフォグラフィック用プロンプト生成（設定はGUIで行うため、プロンプトには含めない）
    const generationPrompt = `このNOTE記事にインフォグラフィックを入れたい。
・記事を分析し、適切な数のインフォグラフィックを作成して欲しい。
・中項目レベルで１つずつ
・グラフィックレコーディング風の手描き図解にしてください。
・重要なキーワードやコンセプトを視覚的に表現し、親しみやすいイラストと手書き風のフォントでまとめてください。

${article.content}`;

    // プロンプトをファイルに保存（確認用）
    const promptFilePath = path.join(INFOGRAPHIC_DIR, 'last_prompt.txt');
    fs.writeFileSync(promptFilePath, generationPrompt, 'utf-8');
    console.log(`📝 プロンプトを保存しました: ${promptFilePath}`);
    console.log(`📝 プロンプト文字数: ${generationPrompt.length}文字`);

    // 保存ディレクトリ作成
    if (!fs.existsSync(INFOGRAPHIC_DIR)) {
        fs.mkdirSync(INFOGRAPHIC_DIR, { recursive: true });
    }

    // ブラウザ起動（ユーザーデータを保持してログイン状態を維持）
    console.log('🌐 ブラウザを起動中...');
    const browser: BrowserContext = await chromium.launchPersistentContext(USER_DATA_DIR, {
        headless: false,
        viewport: { width: 1280, height: 900 },
        args: ['--disable-blink-features=AutomationControlled']
    });

    const page: Page = await browser.newPage();

    try {
        // Gensparkの画像生成ページに移動
        console.log('📍 Genspark画像生成ページに移動中...');
        await page.goto(GENSPARK_IMAGE_URL, { waitUntil: 'networkidle', timeout: 60000 });
        await page.waitForTimeout(3000);

        // デバッグモードでも最初は停止しない（ダウンロード時に停止）

        // ========== GUI設定操作 ==========
        console.log('⚙️ GUI設定を開始します...');
        await page.screenshot({ path: path.join(INFOGRAPHIC_DIR, 'debug_01_initial.png') });

        // ページ内の全てのボタンテキストを確認
        const allButtons = await page.locator('button').allTextContents();
        console.log('📋 検出されたボタン:', allButtons.slice(0, 10));

        // 「設定」ボタンを探してクリック
        console.log('🔍 「設定」ボタンを探しています...');

        // 方法1: getByText
        let settingsClicked = false;
        const settingsLocator = page.getByText('設定');
        const settingsCount = await settingsLocator.count();
        console.log(`📊 「設定」テキスト要素数: ${settingsCount}`);

        if (settingsCount > 0) {
            for (let i = 0; i < settingsCount; i++) {
                const el = settingsLocator.nth(i);
                const isVisible = await el.isVisible();
                console.log(`  [${i}] visible: ${isVisible}`);
                if (isVisible) {
                    await el.click();
                    settingsClicked = true;
                    console.log('✅ 設定ボタンをクリックしました');
                    break;
                }
            }
        }

        // 方法2: CSS セレクタで探す
        if (!settingsClicked) {
            console.log('🔍 CSSセレクタで設定ボタンを探しています...');
            const settingsBtns = page.locator('button:has-text("設定"), div:has-text("設定")');
            const count = await settingsBtns.count();
            console.log(`📊 設定関連要素数: ${count}`);

            for (let i = 0; i < Math.min(count, 5); i++) {
                const el = settingsBtns.nth(i);
                const isVisible = await el.isVisible();
                const text = await el.textContent();
                console.log(`  [${i}] text: "${text?.substring(0, 20)}", visible: ${isVisible}`);
            }
        }

        await page.waitForTimeout(2000);
        await page.screenshot({ path: path.join(INFOGRAPHIC_DIR, 'debug_02_after_settings_click.png') });

        // デバッグモード：一時停止
        if (DEBUG_MODE) {
            console.log('🔍 デバッグ: 現在の状態を確認してください。Resumeで続行。');
            await page.pause();
        }

        // 2K を選択
        console.log('📐 2K を探しています...');
        const size2K = page.getByText('2K', { exact: true });
        const size2KCount = await size2K.count();
        console.log(`📊 「2K」要素数: ${size2KCount}`);

        if (size2KCount > 0) {
            await size2K.first().click();
            console.log('✅ 2K をクリックしました');
        }
        await page.waitForTimeout(500);

        // 16:9 を選択
        console.log('📏 16:9 を探しています...');
        const ratio16_9 = page.getByText('16:9', { exact: true });
        const ratio16_9Count = await ratio16_9.count();
        console.log(`📊 「16:9」要素数: ${ratio16_9Count}`);

        if (ratio16_9Count > 0) {
            await ratio16_9.first().click();
            console.log('✅ 16:9 をクリックしました');
        }
        await page.waitForTimeout(500);

        // 設定パネルを閉じる
        console.log('📋 設定パネルを閉じます...');
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        await page.mouse.click(100, 300);
        await page.waitForTimeout(1000);

        await page.screenshot({ path: path.join(INFOGRAPHIC_DIR, 'debug_03_settings_done.png') });
        console.log('✅ 設定完了');

        // ========== プロンプト入力 ==========
        console.log('✍️ プロンプトを入力中...');

        // テキストエリアまたは入力欄を探す
        const inputSelectors = [
            'textarea[placeholder*="Describe"]',
            'textarea[placeholder*="describe"]',
            'textarea',
            '[contenteditable="true"]',
            'input[type="text"]'
        ];

        let inputElement = null;
        for (const selector of inputSelectors) {
            try {
                inputElement = await page.waitForSelector(selector, { timeout: 5000 });
                if (inputElement) {
                    console.log(`📝 入力欄を発見: ${selector}`);
                    break;
                }
            } catch {
                continue;
            }
        }

        if (!inputElement) {
            console.log('❌ 入力欄が見つかりません');
            await page.screenshot({ path: path.join(INFOGRAPHIC_DIR, 'error_no_input.png') });
            return;
        }

        // プロンプトを入力
        console.log(`📝 プロンプト入力を開始（${generationPrompt.length}文字）...`);
        await inputElement.click();
        await inputElement.focus();
        await page.waitForTimeout(500);

        // 方法1: fill を試す
        try {
            await inputElement.fill(generationPrompt);
            await page.waitForTimeout(500);
            console.log('✅ fill メソッドで入力完了');
        } catch (e) {
            console.log('⚠️ fill が失敗。他の方法を試します...');
        }

        // 入力確認
        let currentText = '';
        try {
            currentText = await inputElement.inputValue();
        } catch {
            try {
                currentText = await inputElement.textContent() || '';
            } catch {
                currentText = '';
            }
        }

        // 方法2: fill が効かない場合、JavaScript で直接設定
        if (currentText.length < 100) {
            console.log('⚠️ 入力が不完全。JavaScript で直接設定を試みます...');
            await page.evaluate((text: string) => {
                const el = document.querySelector('textarea') as any;
                if (el) {
                    el.value = text;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }, generationPrompt);
            await page.waitForTimeout(500);
        }

        // 方法3: それでもダメなら type で少しずつ入力（短縮版）
        try {
            currentText = await inputElement.inputValue();
        } catch {
            currentText = '';
        }

        if (currentText.length < 100) {
            console.log('⚠️ 入力が不完全。type メソッドを試みます（時間がかかります）...');
            await inputElement.click();
            await inputElement.press('Control+a'); // 全選択
            await page.waitForTimeout(100);
            // 最初の1000文字だけ高速入力
            const shortPrompt = generationPrompt.substring(0, 1000) + '\n\n[記事本文省略]';
            await inputElement.type(shortPrompt, { delay: 5 });
        }

        console.log('✅ プロンプト入力完了');
        await page.waitForTimeout(1000);

        // ========== 生成実行 ==========
        console.log('🚀 生成を開始...');
        const submitSelectors = [
            'button[type="submit"]',
            'button:has-text("Generate")',
            'button:has-text("Send")',
            'button:has-text("Create")',
            '[data-testid="send-button"]',
            'button svg[class*="send"]'
        ];

        let submitted = false;
        for (const selector of submitSelectors) {
            try {
                const btn = await page.$(selector);
                if (btn) {
                    await btn.click();
                    submitted = true;
                    console.log(`✅ 送信ボタンをクリック: ${selector}`);
                    break;
                }
            } catch {
                continue;
            }
        }

        if (!submitted) {
            // Enterキーで送信を試みる
            await page.keyboard.press('Enter');
            console.log('⌨️ Enterキーで送信を試みました');
        }

        // ========== 画像生成を自動検出 ==========
        console.log('\n' + '='.repeat(50));
        console.log('⏳ 画像生成を待機中（自動検出）...');
        console.log('='.repeat(50));

        let imageUrls: string[] = [];
        const maxWaitTime = 10 * 60 * 1000; // 最大10分待機
        const checkInterval = 5000; // 5秒ごとにチェック
        const startTime = Date.now();
        let lastImageCount = 0;
        let stableCount = 0; // 画像数が安定している回数

        while (Date.now() - startTime < maxWaitTime) {
            // ページ内の大きな画像を検出
            const allImages = await page.$$('img');
            const largeImages: string[] = [];

            for (const img of allImages) {
                const src = await img.getAttribute('src');
                const boundingBox = await img.boundingBox();

                if (src && boundingBox) {
                    const width = boundingBox.width;
                    const height = boundingBox.height;

                    // 大きな画像（200x200以上）でアイコン等を除外
                    if (width > 200 && height > 200) {
                        const isNotIcon = !src.includes('icon') &&
                                          !src.includes('logo') &&
                                          !src.includes('avatar') &&
                                          !src.includes('emoji') &&
                                          !src.includes('favicon') &&
                                          !src.includes('profile');

                        if (isNotIcon && !largeImages.includes(src)) {
                            largeImages.push(src);
                        }
                    }
                }
            }

            const currentImageCount = largeImages.length;
            const elapsed = Math.floor((Date.now() - startTime) / 1000);

            console.log(`⏳ ${elapsed}秒経過 - 検出画像: ${currentImageCount}枚`);

            // 画像が見つかり、数が安定したら完了とみなす
            if (currentImageCount > 0) {
                if (currentImageCount === lastImageCount) {
                    stableCount++;
                    // 3回連続で同じ画像数なら生成完了とみなす（15秒安定）
                    if (stableCount >= 3) {
                        console.log('✅ 画像生成が完了しました！');
                        imageUrls = largeImages;
                        break;
                    }
                } else {
                    stableCount = 0;
                }
            }

            lastImageCount = currentImageCount;
            await page.waitForTimeout(checkInterval);
        }

        console.log(`\n📊 検出された画像: ${imageUrls.length}枚`);

        // 検出された画像の詳細を表示
        for (let i = 0; i < imageUrls.length; i++) {
            console.log(`  [${i + 1}] ${imageUrls[i].substring(0, 70)}...`);
        }

        // ページ状態をスクリーンショットで保存
        await page.screenshot({ path: path.join(INFOGRAPHIC_DIR, 'debug_page_state.png'), fullPage: true });
        console.log('📸 ページ状態をスクリーンショットで保存しました');

        // 画像を保存
        // 保存ルール:
        // 親パス: /Volumes/WDBLACK_2TB/Git/sns-content-automation/articles/infographic
        // フォルダ名: YYYYMMDDHHMMSS_記事名
        // ファイル名: YYYYMMDDHHMMSS_記事名_連番.png
        if (imageUrls.length > 0) {
            const timestamp = generateTimestamp();
            const articleName = extractArticleName(article.filename);
            const folderName = `${timestamp}_${articleName}`;
            const folderPath = path.join(INFOGRAPHIC_DIR, folderName);

            // フォルダを作成
            if (!fs.existsSync(folderPath)) {
                fs.mkdirSync(folderPath, { recursive: true });
            }

            console.log(`\n📥 キャンバスモードで画像をダウンロードします...`);
            console.log(`📁 保存フォルダ: ${folderPath}`);

            // デバッグモード：ダウンロード前に一時停止
            if (DEBUG_MODE) {
                console.log('\n🔍 デバッグモード: キャンバスモードを確認してください');
                console.log('   手動でダウンロード操作を行い、セレクタを確認できます');
                console.log('   確認後、Resumeボタンをクリックしてください');
                await page.pause();
            }

            // キャンバスモードの右側で画像にチェックを入れる
            console.log('\n🖼️ 画像を選択中...');

            // チェックボックスまたは選択可能な画像を探す
            const checkboxSelectors = [
                '[class*="canvas"] input[type="checkbox"]',
                '[class*="canvas"] [class*="check"]',
                '[class*="select"] input[type="checkbox"]',
                '[class*="image"] input[type="checkbox"]',
                '[class*="thumbnail"] input[type="checkbox"]',
                'input[type="checkbox"]'
            ];

            let checkedCount = 0;
            for (const selector of checkboxSelectors) {
                const checkboxes = await page.$$(selector);
                if (checkboxes.length > 0) {
                    console.log(`   📍 チェックボックス発見: ${selector} (${checkboxes.length}個)`);
                    for (const checkbox of checkboxes) {
                        const isChecked = await checkbox.isChecked().catch(() => false);
                        if (!isChecked) {
                            await checkbox.click();
                            checkedCount++;
                            await page.waitForTimeout(300);
                        }
                    }
                    break;
                }
            }

            // チェックボックスが見つからない場合、画像自体をクリックして選択
            if (checkedCount === 0) {
                console.log('   🔍 画像を直接クリックして選択を試みます...');
                for (const url of imageUrls) {
                    const imgElement = await page.$(`img[src="${url}"]`);
                    if (imgElement) {
                        await imgElement.click();
                        checkedCount++;
                        await page.waitForTimeout(500);
                    }
                }
            }

            console.log(`   ✅ ${checkedCount}枚の画像を選択しました`);
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(INFOGRAPHIC_DIR, 'debug_selected.png') });

            // ダウンロードボタンを探してクリック
            console.log('\n📥 ダウンロードボタンを探しています...');

            const downloadSelectors = [
                'button:has-text("Download")',
                'button:has-text("ダウンロード")',
                '[class*="download"] button',
                'button[class*="download"]',
                'a:has-text("Download")',
                'a:has-text("ダウンロード")',
                '[aria-label*="download"]',
                '[aria-label*="Download"]',
                '[title*="download"]',
                '[title*="Download"]',
                'svg[class*="download"]'
            ];

            // ダウンロードイベントをリッスン
            const downloadPromise = page.waitForEvent('download', { timeout: 30000 }).catch(() => null);

            let downloadClicked = false;
            for (const selector of downloadSelectors) {
                const btn = await page.$(selector);
                if (btn) {
                    const isVisible = await btn.isVisible();
                    if (isVisible) {
                        console.log(`   📍 ダウンロードボタン発見: ${selector}`);
                        await btn.click();
                        downloadClicked = true;
                        break;
                    }
                }
            }

            if (!downloadClicked) {
                console.log('   ⚠️ ダウンロードボタンが見つかりません');
                console.log('   📸 フォールバック: 画像をスクリーンショットで保存します');

                // フォールバック: スクリーンショットで保存
                for (let i = 0; i < imageUrls.length; i++) {
                    const url = imageUrls[i];
                    const filename = `${timestamp}_${articleName}_${String(i + 1).padStart(2, '0')}.png`;
                    const filepath = path.join(folderPath, filename);

                    const imgElement = await page.$(`img[src="${url}"]`);
                    if (imgElement) {
                        await imgElement.screenshot({ path: filepath });
                        const stats = fs.statSync(filepath);
                        console.log(`   ✅ ${filename} (${Math.round(stats.size / 1024)}KB)`);
                    }
                }
            } else {
                // ダウンロードを待機
                console.log('   ⏳ ダウンロードを待機中...');
                const download = await downloadPromise;

                if (download) {
                    // ダウンロードされたファイルを保存
                    const suggestedFilename = download.suggestedFilename();
                    const downloadPath = path.join(folderPath, `${timestamp}_${articleName}_${suggestedFilename}`);
                    await download.saveAs(downloadPath);

                    const stats = fs.statSync(downloadPath);
                    console.log(`   ✅ ダウンロード完了: ${suggestedFilename} (${Math.round(stats.size / 1024)}KB)`);
                } else {
                    console.log('   ⚠️ ダウンロードイベントを検出できませんでした');
                }
            }

            await page.waitForTimeout(2000);

            // 保存されたファイルを一覧表示
            const savedFiles = fs.readdirSync(folderPath).filter(f => f.endsWith('.png') || f.endsWith('.jpg') || f.endsWith('.jpeg') || f.endsWith('.webp'));
            console.log(`\n` + '='.repeat(50));
            console.log(`✨ ダウンロード完了！`);
            console.log(`📁 保存先: ${folderPath}`);
            console.log('='.repeat(50));

            console.log(`\n📋 保存されたファイル (${savedFiles.length}枚):`);
            for (const file of savedFiles) {
                const filePath = path.join(folderPath, file);
                const stats = fs.statSync(filePath);
                const fileSizeKB = Math.round(stats.size / 1024);
                console.log(`   - ${file} (${fileSizeKB}KB)`);
            }
        } else {
            console.log('❌ 画像が見つかりませんでした');
            // スクリーンショットを保存
            await page.screenshot({
                path: path.join(INFOGRAPHIC_DIR, `error_${generateTimestamp()}.png`),
                fullPage: true
            });
        }

    } catch (error) {
        console.error('❌ エラーが発生しました:', error);
        await page.screenshot({
            path: path.join(INFOGRAPHIC_DIR, `error_${generateTimestamp()}.png`),
            fullPage: true
        });
    } finally {
        console.log('\n✅ 処理完了');
        console.log('🔒 ブラウザを閉じます...');
        await browser.close();
    }
}

/**
 * メイン処理
 */
async function main(): Promise<void> {
    const command = process.argv[2];

    console.log('='.repeat(50));
    console.log('🤖 Genspark Automation Tool');
    console.log('='.repeat(50));
    console.log(`📁 下書きディレクトリ: ${ARTICLES_DRAFTS_DIR}`);
    console.log(`📁 インフォグラフィック保存先: ${INFOGRAPHIC_DIR}`);
    console.log(`🔧 デバッグモード: ${DEBUG_MODE ? 'ON' : 'OFF'}`);
    console.log('='.repeat(50) + '\n');

    switch (command) {
        case 'image':
            await generateImages();
            break;
        default:
            console.log('使用方法:');
            console.log('  npx ts-node genspark_automation.ts image          - 画像生成を実行');
            console.log('  npx ts-node genspark_automation.ts image --debug  - デバッグモードで実行');
            break;
    }
}

main().catch(console.error);
