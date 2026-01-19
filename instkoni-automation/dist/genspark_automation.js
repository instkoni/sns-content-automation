"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.PROJECTS_DIR = exports.INFOGRAPHIC_DIR = exports.ARTICLES_PUBLISHED_DIR = exports.ARTICLES_DRAFTS_DIR = exports.DEFAULT_CONFIG = exports.GensparkAutomation = void 0;
exports.generateTimestamp = generateTimestamp;
exports.extractArticleName = extractArticleName;
exports.withRetry = withRetry;
exports.ensureDirectoryExists = ensureDirectoryExists;
exports.sanitizeFileName = sanitizeFileName;
exports.listDraftArticles = listDraftArticles;
exports.loadArticleFile = loadArticleFile;
exports.moveToPublished = moveToPublished;
const playwright_1 = require("playwright");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
// デフォルト設定（必須パラメータ）
const DEFAULT_CONFIG = {
    model: 'Nano Banana Pro',
    imageSize: '2K',
    aspectRatio: '16:9',
};
exports.DEFAULT_CONFIG = DEFAULT_CONFIG;
// リトライ設定
const RETRY_COUNT = 3;
const RETRY_DELAY = 2000;
// ユーザーデータディレクトリ（セッション永続化用）
const USER_DATA_DIR = path.join(__dirname, '.browser-data');
// 記事フォルダ（リポジトリ直下の articles/ を参照）
const ARTICLES_DRAFTS_DIR = path.join(__dirname, '..', 'articles', 'drafts');
exports.ARTICLES_DRAFTS_DIR = ARTICLES_DRAFTS_DIR;
const ARTICLES_PUBLISHED_DIR = path.join(__dirname, '..', 'articles', 'published');
exports.ARTICLES_PUBLISHED_DIR = ARTICLES_PUBLISHED_DIR;
// インフォグラフィック保存フォルダ（固定パス）
const INFOGRAPHIC_DIR = '/Volumes/WDBLACK_2TB/Git/sns-content-automation/articles/infographic';
exports.INFOGRAPHIC_DIR = INFOGRAPHIC_DIR;
// 出力フォルダ（リポジトリ直下の projects/ を参照）
const PROJECTS_DIR = path.join(__dirname, '..', 'projects');
exports.PROJECTS_DIR = PROJECTS_DIR;
// タイムスタンプ生成（YYYYMMDDHHMMSS形式）
function generateTimestamp() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    return `${year}${month}${day}${hours}${minutes}${seconds}`;
}
// 記事名を抽出（ファイル名から拡張子を除去）
function extractArticleName(fileName) {
    return fileName.replace(/\.(txt|md)$/i, '');
}
// ユーティリティ: draftsフォルダから記事ファイル一覧を取得
function listDraftArticles() {
    if (!fs.existsSync(ARTICLES_DRAFTS_DIR)) {
        return [];
    }
    return fs.readdirSync(ARTICLES_DRAFTS_DIR)
        .filter(file => file.endsWith('.txt') || file.endsWith('.md'))
        .map(file => path.join(ARTICLES_DRAFTS_DIR, file));
}
// ユーティリティ: 記事ファイルを読み込む
function loadArticleFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf-8').trim();
    const fileName = path.basename(filePath);
    // タイトルを抽出（最初の行、または # で始まる行、またはファイル名から）
    let title = '';
    const lines = content.split('\n');
    // Markdown形式のタイトル（# で始まる行）
    const mdTitleLine = lines.find(line => line.startsWith('# '));
    if (mdTitleLine) {
        title = mdTitleLine.replace(/^#\s*/, '').trim();
    }
    else if (lines[0] && lines[0].length < 100) {
        // 最初の行が短ければタイトルとして使用
        title = lines[0].trim();
    }
    else {
        // ファイル名からタイトルを生成
        title = fileName.replace(/\.(txt|md)$/, '');
    }
    return {
        filePath,
        fileName,
        title,
        content,
    };
}
// ユーティリティ: 処理済みファイルをpublishedに移動
function moveToPublished(filePath) {
    const fileName = path.basename(filePath);
    const destPath = path.join(ARTICLES_PUBLISHED_DIR, fileName);
    ensureDirectoryExists(ARTICLES_PUBLISHED_DIR);
    fs.renameSync(filePath, destPath);
    console.log(`記事を移動しました: ${fileName} → articles/published/`);
}
// ユーティリティ: リトライ付き実行
async function withRetry(fn, retries = RETRY_COUNT, delay = RETRY_DELAY) {
    let lastError;
    for (let i = 0; i < retries; i++) {
        try {
            return await fn();
        }
        catch (error) {
            lastError = error;
            console.log(`リトライ ${i + 1}/${retries}: ${lastError.message}`);
            if (i < retries - 1) {
                await new Promise((resolve) => setTimeout(resolve, delay));
            }
        }
    }
    throw lastError;
}
// ユーティリティ: ディレクトリ作成
function ensureDirectoryExists(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
        console.log(`ディレクトリを作成しました: ${dirPath}`);
    }
}
// ユーティリティ: ファイル名をサニタイズ
function sanitizeFileName(name) {
    return name.replace(/[<>:"/\\|?*]/g, '_').trim();
}
// Genspark自動操作クラス
class GensparkAutomation {
    constructor() {
        this.context = null;
        this.page = null;
        this.baseUrl = 'https://www.genspark.ai/';
        // 画像生成エージェントの直接URL
        this.imageAgentUrl = 'https://www.genspark.ai/agents?type=image_generation_agent';
    }
    // ブラウザを起動（永続的コンテキスト使用）
    async launch() {
        console.log('ブラウザを起動しています...');
        console.log(`セッションデータ: ${USER_DATA_DIR}`);
        this.context = await playwright_1.chromium.launchPersistentContext(USER_DATA_DIR, {
            headless: false,
            slowMo: 100,
            viewport: { width: 1920, height: 1080 },
            acceptDownloads: true,
            args: [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
            ],
            ignoreDefaultArgs: ['--enable-automation'],
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        });
        const pages = this.context.pages();
        this.page = pages.length > 0 ? pages[0] : await this.context.newPage();
        await this.page.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        });
        console.log('ブラウザを起動しました');
    }
    // ブラウザを終了
    async close() {
        if (this.context) {
            await this.context.close();
            this.context = null;
            this.page = null;
            console.log('ブラウザを終了しました');
        }
    }
    // ページ取得（内部用）
    getPage() {
        if (!this.page) {
            throw new Error('ブラウザが起動していません。launch()を先に呼び出してください。');
        }
        return this.page;
    }
    // Gensparkにアクセスしてログイン待機
    async navigateAndWaitForLogin(skipLoginCheck = false) {
        const page = this.getPage();
        console.log('Gensparkにアクセスしています...');
        await page.goto(this.baseUrl);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(3000);
        // ログインチェックをスキップする場合
        if (skipLoginCheck) {
            console.log('ログインチェックをスキップしました');
            return;
        }
        // URLでログイン状態を判定
        const currentUrl = page.url();
        console.log(`現在のURL: ${currentUrl}`);
        // ログインページにリダイレクトされていないかチェック
        if (currentUrl.includes('login') || currentUrl.includes('auth') || currentUrl.includes('signin')) {
            console.log('ログインが必要です。ブラウザで手動でログインしてください...');
            console.log('ログイン完了後、Gensparkのメインページに戻るまで待機します。');
            // メインページに戻るまで待機（URLベース）
            await page.waitForFunction((baseUrl) => {
                const url = window.location.href;
                return url.startsWith(baseUrl) && !url.includes('login') && !url.includes('auth') && !url.includes('signin');
            }, this.baseUrl, { timeout: 300000 });
            await page.waitForTimeout(3000);
            console.log('ログインが完了しました');
        }
        else {
            console.log('既にログイン済みです');
        }
    }
    // 画像生成画面に移動（直接URL遷移 + リトライ付き）
    async navigateToImageGeneration() {
        const page = this.getPage();
        const targetUrl = this.imageAgentUrl;
        const errorScreenshotPath = path.join(__dirname, 'error.png');
        console.log('=== 画像生成エージェント画面へ遷移 ===');
        console.log(`遷移先URL: ${targetUrl}`);
        let navigationSuccess = false;
        let retryCount = 0;
        const maxRetries = 1;
        while (!navigationSuccess && retryCount <= maxRetries) {
            try {
                if (retryCount > 0) {
                    console.log(`リトライ ${retryCount}/${maxRetries}: ページをリロードしています...`);
                    await page.reload({ waitUntil: 'networkidle' });
                    await page.waitForTimeout(2000);
                }
                // 直接URLへジャンプ
                console.log('画像生成エージェントページへ直接アクセス中...');
                await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
                // URLが正しいか確認（waitForURL使用）
                console.log('URL確認中...');
                await page.waitForURL((url) => {
                    const urlStr = url.toString();
                    return urlStr.includes('agents') && urlStr.includes('image_generation');
                }, { timeout: 15000 });
                // ネットワーク安定を待機
                await page.waitForLoadState('networkidle', { timeout: 30000 });
                await page.waitForTimeout(2000);
                // 現在のURLを確認
                const currentUrl = page.url();
                console.log(`現在のURL: ${currentUrl}`);
                // 正しいページかどうか検証
                if (currentUrl.includes('image_generation')) {
                    console.log('✓ 画像生成エージェント画面に正常に遷移しました');
                    navigationSuccess = true;
                }
                else {
                    throw new Error(`想定外のページに遷移: ${currentUrl}`);
                }
            }
            catch (error) {
                const errorMessage = error.message;
                console.error(`遷移エラー: ${errorMessage}`);
                // エラー時のスクリーンショットを保存
                try {
                    await page.screenshot({ path: errorScreenshotPath, fullPage: true });
                    console.log(`デバッグ用スクリーンショットを保存: ${errorScreenshotPath}`);
                }
                catch (screenshotError) {
                    console.log('スクリーンショットの保存に失敗しました');
                }
                // 現在のページ情報をログ出力
                const currentUrl = page.url();
                const pageTitle = await page.title();
                console.log(`現在のURL: ${currentUrl}`);
                console.log(`ページタイトル: ${pageTitle}`);
                retryCount++;
                if (retryCount > maxRetries) {
                    throw new Error(`画像生成エージェント画面への遷移に失敗しました。エラー詳細: ${errorMessage}`);
                }
            }
        }
        // 最終確認：入力フィールドが存在するか
        try {
            console.log('ページ要素の存在確認中...');
            await page.waitForSelector('textarea, [class*="input"], [class*="Input"]', { timeout: 10000 });
            console.log('✓ 入力フィールドを検出しました');
        }
        catch {
            console.log('警告: 入力フィールドがまだ読み込まれていない可能性があります');
            await page.waitForTimeout(3000);
        }
        console.log('=== 遷移完了 ===\n');
    }
    // 【重要】パラメータを事前設定（モデル、サイズ、アスペクト比）
    // 処理順序: 設定タブ→モデル→サイズ→アスペクト比→待機→プロンプト
    // ※ Playwright Inspector で確認した正確なセレクタを使用
    async configureImageSettings(config = DEFAULT_CONFIG) {
        const page = this.getPage();
        const settingsScreenshotPath = path.join(__dirname, 'settings_debug.png');
        console.log('=== 画像生成パラメータを事前設定 ===');
        console.log(`目標: モデル=${config.model}, サイズ=${config.imageSize}, アスペクト比=${config.aspectRatio}`);
        // ============================================
        // STEP 1: 設定タブを開く（getByText('設定')）
        // ============================================
        console.log('\n[STEP 1] 設定タブを開く...');
        await this.openSettingsTabAndWait(page);
        // ============================================
        // STEP 2: Nano Banana Pro を選択
        // ============================================
        console.log(`\n[STEP 2] モデルを選択: ${config.model}`);
        const modelSelected = await this.clickModelOption(page, config.model);
        console.log(modelSelected ? `   ✓ ${config.model} 選択完了` : `   ✗ ${config.model} 選択失敗`);
        // ============================================
        // STEP 3: 2K を選択（locator('div').filter({ hasText: /^2K$/ })）
        // ============================================
        console.log(`\n[STEP 3] 解像度を選択: ${config.imageSize}`);
        const sizeSelected = await this.clickSizeOption(page, config.imageSize);
        console.log(sizeSelected ? `   ✓ ${config.imageSize} 選択完了` : `   ✗ ${config.imageSize} 選択失敗`);
        // ============================================
        // STEP 4: 16:9 を選択（div:nth-child(4) > .ratio-icon > svg）
        // ============================================
        console.log(`\n[STEP 4] アスペクト比を選択: ${config.aspectRatio}`);
        const aspectSelected = await this.clickAspectRatioOption(page, config.aspectRatio);
        console.log(aspectSelected ? `   ✓ ${config.aspectRatio} 選択完了` : `   ✗ ${config.aspectRatio} 選択失敗`);
        // ============================================
        // STEP 5: 設定反映を待機
        // ============================================
        console.log('\n[STEP 5] 設定反映を待機...');
        await page.waitForTimeout(2000);
        // デバッグ用スクリーンショット
        try {
            await page.screenshot({ path: settingsScreenshotPath, fullPage: false });
            console.log(`設定確認スクリーンショット: ${settingsScreenshotPath}`);
        }
        catch {
            // スキップ
        }
        const allSuccess = modelSelected && sizeSelected && aspectSelected;
        console.log(allSuccess ? '\n=== 全設定完了 ===' : '\n=== 一部設定が未確認ですが続行 ===');
    }
    // モデル選択（Nano Banana Pro）
    async clickModelOption(page, modelName) {
        const MAX_RETRIES = 3;
        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                console.log(`   試行 ${attempt}/${MAX_RETRIES}...`);
                // モデル名でテキスト検索（TODO: 正確なセレクタに置き換え）
                const modelElement = page.getByText(modelName, { exact: true });
                if (await modelElement.isVisible({ timeout: 3000 })) {
                    await modelElement.click();
                    console.log(`   クリック実行: ${modelName}`);
                    await page.waitForTimeout(800);
                    return true;
                }
            }
            catch (error) {
                console.log(`   エラー: ${error.message}`);
            }
            await page.waitForTimeout(500);
        }
        return false;
    }
    // サイズ選択（2K）- 確認済みセレクタ使用
    async clickSizeOption(page, size) {
        const MAX_RETRIES = 3;
        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                console.log(`   試行 ${attempt}/${MAX_RETRIES}...`);
                // Playwright Inspector で確認したセレクタ
                const sizePattern = new RegExp(`^${size}$`);
                const sizeElement = page.locator('div').filter({ hasText: sizePattern }).first();
                if (await sizeElement.isVisible({ timeout: 3000 })) {
                    await sizeElement.click();
                    console.log(`   クリック実行: div.filter({ hasText: /^${size}$/ })`);
                    await page.waitForTimeout(800);
                    return true;
                }
            }
            catch (error) {
                console.log(`   エラー: ${error.message}`);
            }
            await page.waitForTimeout(500);
        }
        return false;
    }
    // アスペクト比選択（16:9）- 確認済みセレクタ使用
    async clickAspectRatioOption(page, ratio) {
        const MAX_RETRIES = 3;
        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                console.log(`   試行 ${attempt}/${MAX_RETRIES}...`);
                // Playwright Inspector で確認したセレクタ: div:nth-child(4) > .ratio-icon > svg
                // 16:9 は 4番目の子要素
                const ratioElement = page.locator('div:nth-child(4) > .ratio-icon').first();
                if (await ratioElement.isVisible({ timeout: 3000 })) {
                    await ratioElement.click();
                    console.log(`   クリック実行: div:nth-child(4) > .ratio-icon`);
                    await page.waitForTimeout(800);
                    return true;
                }
                else {
                    // フォールバック: テキストで検索
                    const fallbackElement = page.getByText(ratio, { exact: true });
                    if (await fallbackElement.isVisible({ timeout: 2000 })) {
                        await fallbackElement.click();
                        console.log(`   クリック実行（フォールバック）: getByText('${ratio}')`);
                        await page.waitForTimeout(800);
                        return true;
                    }
                }
            }
            catch (error) {
                console.log(`   エラー: ${error.message}`);
            }
            await page.waitForTimeout(500);
        }
        return false;
    }
    // 設定タブを開き、設定項目が表示されるまで待機
    async openSettingsTabAndWait(page) {
        console.log('   「設定」ボタンをクリック...');
        try {
            // Playwright Inspector で確認したセレクタを使用
            const settingsButton = page.getByText('設定');
            if (await settingsButton.isVisible({ timeout: 3000 })) {
                await settingsButton.click();
                console.log('   ✓ 「設定」ボタンをクリックしました');
                await page.waitForTimeout(1500);
            }
            else {
                console.log('   ⚠ 「設定」ボタンが見つかりません');
            }
        }
        catch (error) {
            console.log(`   ⚠ 設定ボタンのクリックに失敗: ${error.message}`);
        }
        // 設定項目（2K など）が表示されるまで待機
        console.log('   設定項目の表示を待機中...');
        try {
            await page.locator('div').filter({ hasText: /^2K$/ }).first().waitFor({ state: 'visible', timeout: 5000 });
            console.log('   ✓ 設定項目が表示されました');
        }
        catch {
            console.log('   ⚠ 設定項目の表示を確認できませんでした（続行）');
        }
        await page.waitForTimeout(500);
    }
    // 記事全文から画像を一括生成
    async generateImagesFromArticle(params) {
        const { articleText, articleTitle, sourceFileName } = params;
        const page = this.getPage();
        // タイムスタンプと記事名を生成
        const timestamp = generateTimestamp();
        const articleName = extractArticleName(sourceFileName);
        const sanitizedArticleName = sanitizeFileName(articleName);
        // フォルダ名: YYYYMMDDHHMMSS_記事名
        const folderName = `${timestamp}_${sanitizedArticleName}`;
        const outputPath = path.join(INFOGRAPHIC_DIR, folderName);
        // フォルダを作成（親ディレクトリも含めて）
        fs.mkdirSync(outputPath, { recursive: true });
        console.log(`\n=== インフォグラフィック保存先 ===`);
        console.log(`フォルダ: ${outputPath}`);
        // 分析・生成依頼プロンプトを構築（インフォグラフィック用）
        const generationPrompt = `このNOTE記事にインフォグラフィックを入れたい。
・記事を分析し、適切な数のインフォグラフィックを作成して欲しい。
・中項目レベルで１つずつ
・グラフィックレコーディング風の手描き図解にしてください。
・重要なキーワードやコンセプトを視覚的に表現し、親しみやすいイラストと手書き風のフォントでまとめてください。
・画質：2K、比率：16:9

${articleText}`;
        console.log('分析・生成依頼プロンプトを送信しています...');
        console.log(`記事タイトル: ${articleTitle}`);
        console.log(`記事文字数: ${articleText.length}文字`);
        // プロンプトを入力
        await withRetry(async () => {
            // 入力フィールドのセレクター（複数パターン）
            const inputSelectors = [
                'textarea[placeholder*="prompt"]',
                'textarea[placeholder*="Enter"]',
                'textarea[placeholder*="Describe"]',
                'textarea[placeholder*="Type"]',
                'textarea[placeholder*="Ask"]',
                '[data-testid="prompt-input"]',
                '[class*="PromptInput"] textarea',
                '[class*="chat-input"] textarea',
                '[class*="ChatInput"] textarea',
                '[class*="input"] textarea',
                '[class*="Input"] textarea',
                'textarea',
            ];
            let inputField = null;
            for (const selector of inputSelectors) {
                try {
                    const element = page.locator(selector).first();
                    if (await element.isVisible({ timeout: 1000 })) {
                        inputField = element;
                        console.log(`入力フィールドを検出: ${selector}`);
                        break;
                    }
                }
                catch {
                    continue;
                }
            }
            if (!inputField) {
                throw new Error('入力フィールドが見つかりません');
            }
            await inputField.fill(generationPrompt);
            await page.waitForTimeout(500);
        });
        // 送信ボタンをクリック
        await withRetry(async () => {
            const submitSelectors = [
                'button:has-text("Generate")',
                'button:has-text("Send")',
                'button:has-text("送信")',
                'button:has-text("生成")',
                'button[type="submit"]',
                '[data-testid="submit-button"]',
                '[class*="SendButton"]',
                '[class*="send-button"]',
                '[class*="submit"]',
                '[class*="Submit"]',
                'button[aria-label*="send"]',
                'button[aria-label*="Send"]',
                'button svg[class*="send"]',
            ];
            let submitButton = null;
            for (const selector of submitSelectors) {
                try {
                    const element = page.locator(selector).first();
                    if (await element.isVisible({ timeout: 1000 })) {
                        submitButton = element;
                        console.log(`送信ボタンを検出: ${selector}`);
                        break;
                    }
                }
                catch {
                    continue;
                }
            }
            if (!submitButton) {
                // 最後の手段：Enterキーで送信
                console.log('送信ボタンが見つかりません。Enterキーで送信を試みます...');
                await page.keyboard.press('Enter');
                return;
            }
            await submitButton.click();
        });
        console.log('画像生成を待機しています（複数枚生成される場合があります）...');
        // 生成完了を待機（生成中インジケーターが消えるまで）
        await page.waitForTimeout(5000); // 初期待機
        await withRetry(async () => {
            // 生成中のインジケーターがなくなるまで待機
            await page.waitForFunction(() => {
                const loadingElements = document.querySelectorAll('[class*="loading"], [class*="generating"], [class*="spinner"], [class*="progress"]');
                return loadingElements.length === 0 ||
                    Array.from(loadingElements).every(el => {
                        const style = window.getComputedStyle(el);
                        return style.display === 'none' || style.visibility === 'hidden';
                    });
            }, { timeout: 300000 } // 5分待機
            );
        }, RETRY_COUNT, 10000);
        // 追加の待機（全画像がレンダリングされるのを待つ）
        await page.waitForTimeout(5000);
        console.log('生成完了。画像を収集しています...');
        // チャット内のすべての画像を収集（タイムスタンプと記事名を渡す）
        const savedPaths = await this.collectAndDownloadAllImages(page, outputPath, timestamp, sanitizedArticleName);
        console.log(`\n=== 画像収集完了 ===`);
        console.log(`保存枚数: ${savedPaths.length}枚`);
        savedPaths.forEach((p, i) => console.log(`  ${i + 1}. ${path.basename(p)}`));
        return savedPaths;
    }
    // チャット内のすべての画像を収集してダウンロード
    async collectAndDownloadAllImages(page, outputPath, timestamp, articleName) {
        const savedPaths = [];
        let imageIndex = 1;
        // ファイル名生成ヘルパー: YYYYMMDDHHMMSS_記事名_連番.png
        const generateFileName = (index) => {
            const paddedIndex = String(index).padStart(2, '0');
            return `${timestamp}_${articleName}_${paddedIndex}.png`;
        };
        // 方法1: ダウンロードボタン経由でダウンロード
        const downloadButtons = page.locator('[data-testid="download-button"], button:has-text("Download"), button[aria-label*="download"], [class*="download-btn"], a[download]');
        const downloadCount = await downloadButtons.count();
        console.log(`ダウンロードボタン検出数: ${downloadCount}`);
        for (let i = 0; i < downloadCount; i++) {
            try {
                const button = downloadButtons.nth(i);
                const fileName = generateFileName(imageIndex);
                const filePath = path.join(outputPath, fileName);
                const [download] = await Promise.all([
                    page.waitForEvent('download', { timeout: 30000 }),
                    button.click(),
                ]);
                await download.saveAs(filePath);
                savedPaths.push(filePath);
                console.log(`  ダウンロード完了: ${fileName}`);
                imageIndex++;
                await page.waitForTimeout(1000);
            }
            catch (error) {
                console.log(`  ダウンロードボタン ${i + 1} でエラー: ${error.message}`);
            }
        }
        // 方法2: 画像要素から直接URLを取得してダウンロード（ボタンがない場合のフォールバック）
        if (savedPaths.length === 0) {
            console.log('画像URLから直接ダウンロードを試みます...');
            const imageUrls = await page.evaluate(() => {
                const images = document.querySelectorAll('img[src*="generated"], img[src*="image"], [class*="generated-image"] img, [class*="result"] img');
                return Array.from(images)
                    .map(img => img.src)
                    .filter(src => src && !src.includes('avatar') && !src.includes('icon') && !src.includes('logo'));
            });
            console.log(`画像URL検出数: ${imageUrls.length}`);
            for (let i = 0; i < imageUrls.length; i++) {
                try {
                    const url = imageUrls[i];
                    const fileName = generateFileName(imageIndex);
                    const filePath = path.join(outputPath, fileName);
                    // 画像をfetchしてダウンロード
                    const response = await page.request.get(url);
                    const buffer = await response.body();
                    fs.writeFileSync(filePath, buffer);
                    savedPaths.push(filePath);
                    console.log(`  保存完了: ${fileName}`);
                    imageIndex++;
                }
                catch (error) {
                    console.log(`  画像 ${i + 1} の保存でエラー: ${error.message}`);
                }
            }
        }
        return savedPaths;
    }
    // ポッドキャスト生成画面に移動
    async navigateToPodcastGeneration() {
        const page = this.getPage();
        console.log('AIポッドキャスト画面に移動しています...');
        await withRetry(async () => {
            await page.goto(`${this.baseUrl}podcast`);
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(2000);
        });
        console.log('AIポッドキャスト画面に移動しました');
    }
    // 記事全文からポッドキャストを一括生成
    async generatePodcastFromArticle(params) {
        const { articleText, articleTitle, outputDir } = params;
        const page = this.getPage();
        const sanitizedTitle = sanitizeFileName(articleTitle);
        const outputPath = outputDir || path.join(PROJECTS_DIR, sanitizedTitle, 'podcast');
        ensureDirectoryExists(outputPath);
        console.log('=== ポッドキャスト一括生成 ===');
        console.log(`記事タイトル: ${articleTitle}`);
        console.log(`記事文字数: ${articleText.length}文字`);
        // 記事全文を入力
        await withRetry(async () => {
            const textArea = page.locator('textarea[placeholder*="text"], textarea[placeholder*="content"], textarea[placeholder*="Enter"], [data-testid="podcast-input"], [class*="PodcastInput"] textarea, [class*="input"] textarea').first();
            await textArea.fill(articleText);
            await page.waitForTimeout(500);
        });
        // 生成ボタンをクリック
        await withRetry(async () => {
            const generateButton = page.locator('button:has-text("Generate"), button:has-text("Create"), button:has-text("生成"), [data-testid="generate-podcast"], [class*="GenerateButton"], [class*="submit"]').first();
            await generateButton.click();
        });
        console.log('ポッドキャスト生成を待機しています（数分かかる場合があります）...');
        // 生成完了を待機
        await page.waitForTimeout(5000);
        await withRetry(async () => {
            await page.waitForFunction(() => {
                const loadingElements = document.querySelectorAll('[class*="loading"], [class*="generating"], [class*="processing"], [class*="spinner"]');
                return loadingElements.length === 0 ||
                    Array.from(loadingElements).every(el => {
                        const style = window.getComputedStyle(el);
                        return style.display === 'none' || style.visibility === 'hidden';
                    });
            }, { timeout: 600000 } // 10分待機
            );
            // 音声プレイヤーまたはダウンロードボタンが表示されるまで待機
            await page.waitForSelector('[data-testid="podcast-ready"], [class*="podcast-player"], audio, [class*="AudioPlayer"], button:has-text("Download"), a[download]', {
                state: 'visible',
                timeout: 60000,
            });
        }, RETRY_COUNT, 10000);
        console.log('ポッドキャスト生成完了。ダウンロードしています...');
        // 音声をダウンロード
        const fileName = `podcast_${sanitizedTitle}_${Date.now()}.mp3`;
        const filePath = path.join(outputPath, fileName);
        await withRetry(async () => {
            const downloadButton = page.locator('[data-testid="podcast-download"], button:has-text("Download"), a[download][href*="audio"], a[download], [class*="download"]').first();
            const [download] = await Promise.all([
                page.waitForEvent('download', { timeout: 60000 }),
                downloadButton.click(),
            ]);
            await download.saveAs(filePath);
        });
        console.log(`\n=== ポッドキャスト保存完了 ===`);
        console.log(`保存先: ${filePath}`);
        return filePath;
    }
    // 画像生成のフルワークフロー（事前設定→一括生成→一括保存）
    async runImageGenerationWorkflow(params, config, debugMode = false) {
        // 1. 画像生成画面に移動
        await this.navigateToImageGeneration();
        // デバッグモード: ここで一時停止（Playwright Inspector でセレクタを確認）
        if (debugMode) {
            await this.pauseForDebug();
        }
        // 2. 【重要】事前にパラメータを設定
        await this.configureImageSettings(config || DEFAULT_CONFIG);
        // 3. 記事全文を送信して一括生成・一括保存
        return await this.generateImagesFromArticle(params);
    }
    // デバッグ用一時停止
    async pauseForDebug() {
        const page = this.getPage();
        console.log('\n========================================');
        console.log('🔧 デバッグモード: Playwright Inspector で一時停止');
        console.log('========================================');
        console.log('以下の操作を行い、セレクタを記録してください:');
        console.log('  1. 「設定（Settings）」タブを開くボタン');
        console.log('  2. 「Nano Banana Pro」の選択');
        console.log('  3. 「2K」の選択');
        console.log('  4. 「16:9」の選択');
        console.log('');
        console.log('操作が完了したら、Inspector の「Resume」ボタンを押してください。');
        console.log('========================================\n');
        await page.pause();
        console.log('デバッグモード終了。処理を続行します...\n');
    }
    // ポッドキャスト生成のフルワークフロー
    async runPodcastGenerationWorkflow(params) {
        await this.navigateToPodcastGeneration();
        return await this.generatePodcastFromArticle(params);
    }
}
exports.GensparkAutomation = GensparkAutomation;
// メイン実行関数
async function main() {
    const automation = new GensparkAutomation();
    const rawArgs = process.argv.slice(2);
    // フラグをチェック
    const skipLogin = rawArgs.includes('--skip-login');
    const noMove = rawArgs.includes('--no-move'); // 処理後にpublishedに移動しない
    const debugMode = rawArgs.includes('--debug'); // デバッグモード（page.pause()で一時停止）
    const args = rawArgs.filter(arg => !arg.startsWith('--'));
    if (debugMode) {
        console.log('🔧 デバッグモードが有効です（Playwright Inspector で一時停止します）');
    }
    const mode = args[0] || 'image';
    // listモードはブラウザ不要
    if (mode === 'list') {
        const draftFiles = listDraftArticles();
        console.log(`\n=== articles/drafts/ 内の記事一覧 ===`);
        if (draftFiles.length === 0) {
            console.log('記事ファイルがありません。');
        }
        else {
            draftFiles.forEach((f, i) => {
                const article = loadArticleFile(f);
                console.log(`${i + 1}. ${article.fileName}`);
                console.log(`   タイトル: ${article.title}`);
                console.log(`   文字数: ${article.content.length}文字\n`);
            });
        }
        return;
    }
    try {
        await automation.launch();
        // ログイン専用モード
        if (mode === 'login') {
            console.log('\n=== ログインモード ===');
            console.log('ブラウザでログインしてください。');
            console.log('ログイン完了後、セッションが保存されます。');
            await automation.navigateAndWaitForLogin();
            console.log('\nログインセッションが保存されました。');
            console.log('次回以降は自動でログイン状態が維持されます。');
            return;
        }
        // ログイン待機（--skip-loginで省略可能）
        await automation.navigateAndWaitForLogin(skipLogin);
        if (mode === 'image') {
            // 引数がない場合はdraftsフォルダから読み込み
            let articleTitle;
            let articleText;
            let sourceFileName;
            let sourceFilePath = null;
            if (args.length <= 1) {
                // draftsフォルダから記事を読み込み
                const draftFiles = listDraftArticles();
                if (draftFiles.length === 0) {
                    console.log('articles/drafts/ に記事ファイルがありません。');
                    console.log('記事ファイル（.txt または .md）を配置してください。');
                    console.log('\n使用法:');
                    console.log('  1. articles/drafts/ にテキストファイルを配置して実行');
                    console.log('  2. npx ts-node genspark_automation.ts image "タイトル" "記事内容"');
                    return;
                }
                console.log(`\n=== articles/drafts/ から記事を読み込み ===`);
                console.log(`見つかった記事: ${draftFiles.length}件`);
                draftFiles.forEach((f, i) => console.log(`  ${i + 1}. ${path.basename(f)}`));
                // 最初の記事を処理
                const article = loadArticleFile(draftFiles[0]);
                articleTitle = article.title;
                articleText = article.content;
                sourceFileName = article.fileName;
                sourceFilePath = article.filePath;
                console.log(`\n処理対象: ${article.fileName}`);
            }
            else {
                // 引数から記事情報を取得
                articleTitle = args[1] || 'default_article';
                articleText = args.slice(2).join(' ') || 'これはテスト記事です。美しい風景と未来的な都市の画像を生成してください。';
                sourceFileName = `${articleTitle}.txt`;
            }
            console.log(`\n=== 画像一括生成モード ===`);
            console.log(`記事タイトル: ${articleTitle}`);
            console.log(`記事文字数: ${articleText.length}文字\n`);
            const savedImages = await automation.runImageGenerationWorkflow({
                articleText,
                articleTitle,
                sourceFileName,
            }, undefined, // デフォルト設定を使用
            debugMode // デバッグモード
            );
            console.log('\n=== 最終結果 ===');
            console.log(`生成・保存された画像: ${savedImages.length}枚`);
            savedImages.forEach((p, i) => console.log(`  ${i + 1}. ${p}`));
            // 処理完了後、publishedに移動
            if (sourceFilePath && !noMove && savedImages.length > 0) {
                moveToPublished(sourceFilePath);
            }
        }
        else if (mode === 'podcast') {
            // 引数がない場合はdraftsフォルダから読み込み
            let articleTitle;
            let articleText;
            let sourceFilePath = null;
            if (args.length <= 1) {
                const draftFiles = listDraftArticles();
                if (draftFiles.length === 0) {
                    console.log('articles/drafts/ に記事ファイルがありません。');
                    return;
                }
                const article = loadArticleFile(draftFiles[0]);
                articleTitle = article.title;
                articleText = article.content;
                sourceFilePath = article.filePath;
                console.log(`\n処理対象: ${article.fileName}`);
            }
            else {
                articleTitle = args[1] || 'default_article';
                articleText = args.slice(2).join(' ') || 'これはテスト記事です。AIポッドキャストの生成テストを行います。';
            }
            console.log(`\n=== ポッドキャスト一括生成モード ===`);
            console.log(`記事タイトル: ${articleTitle}`);
            console.log(`記事文字数: ${articleText.length}文字\n`);
            const savedPodcast = await automation.runPodcastGenerationWorkflow({
                articleText,
                articleTitle,
            });
            console.log('\n=== 最終結果 ===');
            console.log(`保存されたポッドキャスト: ${savedPodcast}`);
            // 処理完了後、publishedに移動
            if (sourceFilePath && !noMove) {
                moveToPublished(sourceFilePath);
            }
        }
        else {
            console.error('不明なモード:', mode);
            console.log('使用法:');
            console.log('  npx ts-node genspark_automation.ts login                              # 初回ログイン');
            console.log('  npx ts-node genspark_automation.ts list                               # drafts内の記事一覧');
            console.log('  npx ts-node genspark_automation.ts image                              # draftsから自動読み込みで画像生成');
            console.log('  npx ts-node genspark_automation.ts image [title] [記事全文]           # 引数指定で画像生成');
            console.log('  npx ts-node genspark_automation.ts image --no-move                    # 処理後にpublishedに移動しない');
            console.log('  npx ts-node genspark_automation.ts podcast                            # draftsから自動読み込みでポッドキャスト生成');
        }
    }
    catch (error) {
        console.error('エラーが発生しました:', error);
        throw error;
    }
    finally {
        console.log('\n10秒後にブラウザを閉じます...');
        await new Promise((resolve) => setTimeout(resolve, 10000));
        await automation.close();
    }
}
// 直接実行された場合
if (require.main === module) {
    main().catch((error) => {
        console.error('致命的なエラー:', error);
        process.exit(1);
    });
}
//# sourceMappingURL=genspark_automation.js.map