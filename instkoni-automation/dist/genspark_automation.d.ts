interface GenerationConfig {
    model: string;
    imageSize: string;
    aspectRatio: string;
}
interface ImageGenerationParams {
    articleText: string;
    articleTitle: string;
    sourceFileName: string;
    outputDir?: string;
}
interface PodcastGenerationParams {
    articleText: string;
    articleTitle: string;
    outputDir?: string;
}
declare const DEFAULT_CONFIG: GenerationConfig;
declare const ARTICLES_DRAFTS_DIR: string;
declare const ARTICLES_PUBLISHED_DIR: string;
declare const INFOGRAPHIC_DIR = "/Volumes/WDBLACK_2TB/Git/sns-content-automation/articles/infographic";
declare const PROJECTS_DIR: string;
declare function generateTimestamp(): string;
declare function extractArticleName(fileName: string): string;
interface ArticleFile {
    filePath: string;
    fileName: string;
    title: string;
    content: string;
}
declare function listDraftArticles(): string[];
declare function loadArticleFile(filePath: string): ArticleFile;
declare function moveToPublished(filePath: string): void;
declare function withRetry<T>(fn: () => Promise<T>, retries?: number, delay?: number): Promise<T>;
declare function ensureDirectoryExists(dirPath: string): void;
declare function sanitizeFileName(name: string): string;
export declare class GensparkAutomation {
    private context;
    private page;
    private baseUrl;
    private imageAgentUrl;
    launch(): Promise<void>;
    close(): Promise<void>;
    private getPage;
    navigateAndWaitForLogin(skipLoginCheck?: boolean): Promise<void>;
    navigateToImageGeneration(): Promise<void>;
    configureImageSettings(config?: GenerationConfig): Promise<void>;
    private clickModelOption;
    private clickSizeOption;
    private clickAspectRatioOption;
    private openSettingsTabAndWait;
    generateImagesFromArticle(params: ImageGenerationParams): Promise<string[]>;
    private collectAndDownloadAllImages;
    navigateToPodcastGeneration(): Promise<void>;
    generatePodcastFromArticle(params: PodcastGenerationParams): Promise<string>;
    runImageGenerationWorkflow(params: ImageGenerationParams, config?: GenerationConfig, debugMode?: boolean): Promise<string[]>;
    pauseForDebug(): Promise<void>;
    runPodcastGenerationWorkflow(params: PodcastGenerationParams): Promise<string>;
}
export { GenerationConfig, ImageGenerationParams, PodcastGenerationParams, ArticleFile, DEFAULT_CONFIG, ARTICLES_DRAFTS_DIR, ARTICLES_PUBLISHED_DIR, INFOGRAPHIC_DIR, PROJECTS_DIR, generateTimestamp, extractArticleName, withRetry, ensureDirectoryExists, sanitizeFileName, listDraftArticles, loadArticleFile, moveToPublished, };
//# sourceMappingURL=genspark_automation.d.ts.map