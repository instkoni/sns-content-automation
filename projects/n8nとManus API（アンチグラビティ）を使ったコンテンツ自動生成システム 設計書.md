# n8nとManus API（アンチグラビティ）を使ったコンテンツ自動生成システム 設計書

**作成日**: 2026年1月17日  
**プロジェクト**: Note記事・SNS投稿の自動化ワークフロー  
**ユーザー**: instkoni  
**リポジトリ**: https://github.com/instkoni/sns-content-automation

---

## 1. プロジェクト概要

### 1.1 目的

生成AIとワークフロー自動化ツールを活用し、以下のコンテンツ制作プロセスを自動化・効率化する：

1. **Note記事タイトル提案**（最新AIトレンドに基づく）
2. **AIニュースアーカイブ**（週次・月次での情報収集）
3. **LinkedIn投稿の自動リライト**（Note記事からの転用）
4. **X（Twitter）投稿の自動生成**
5. **Suno音楽生成プロンプト作成**
6. **MV企画・絵コンテ・イラスト/動画プロンプト生成**

### 1.2 技術スタック

| 項目 | 技術 | 用途 |
|------|------|------|
| ワークフロー自動化 | **n8n** (Cloud版) | ノードベースの自動化プラットフォーム |
| AI API | **Manus API** (Super Agent manus-1.6) | 高度な推論・検索機能を持つAIエージェント |
| AI API | **Google Gemini 3 Pro Preview** | Google Search統合、マルチモーダル対応 |
| データ保存 | **GitHub API** | 生成結果の自動コミット・バージョン管理 |
| 過去記事管理 | **GitHub** (Markdown) | 過去のタイトル一覧を手動更新・自動読み込み |

### 1.3 ユーザーのコンテンツスタイル

**テーマ**: 生成AI、AIツール活用、クリエイター向け情報  
**トーン**: カジュアル、フレンドリー、初心者〜中級者向け  
**タイトルパターン**: 【】括弧、絵文字、数字、疑問形/感嘆形  
**ターゲット読者**: AI興味層のクリエイター、初心者〜中級者

---

## 2. 現在の実装状況

### 2.1 ワークフロー1: Note記事タイトル提案 + AIニュースアーカイブ

#### 2.1.1 ノード構成（全8ノード）

```
[1] Manual Trigger
  ↓
[2] GitHub List files (過去記事タイトル一覧を取得)
  ↓
[3] Code: Extract Titles (タイトルを抽出)
  ↓
[4] Google Gemini (タイトル提案生成 + Google Search)
  ↓
[5] Code: Parse Response (Gemini出力をJSON解析)
  ↓
  ├→ [6] Code: Format Title Suggestions (タイトル提案をMarkdown整形) ※未実装
  │    ↓
  │   [7] GitHub Create File (タイトル提案をGitHubに保存)
  │
  └→ [8] Code: Format AI News (AIニュースをMarkdown整形)
       ↓
      [9] GitHub Create File (AIニュースをGitHubに保存)
```

#### 2.1.2 各ノードの詳細

##### ノード1: Manual Trigger
- **機能**: 手動実行トリガー
- **設定**: なし

##### ノード2: GitHub List files
- **機能**: 過去記事タイトル一覧ファイルを取得
- **設定**:
  - Repository: `instkoni/sns-content-automation`
  - File Path: `note_articles/past_titles.md`
  - Branch: `main`

##### ノード3: Code: Extract Titles
- **機能**: Markdownファイルから過去のタイトルを抽出
- **入力**: ノード2のファイル内容
- **出力**: タイトルの配列

##### ノード4: Google Gemini
- **機能**: 最新AIトレンドに基づいたタイトル提案を生成
- **設定**:
  - Model: `Gemini 3 Pro Preview`
  - Temperature: `0.9`
  - Max Output Tokens: `8192`
  - Google Search: **有効**
  - Search Period: 過去1週間
- **プロンプト**: instkoniのnote記事スタイルに基づいたカスタムプロンプト
- **出力形式**: JSON（15件のタイトル提案 + 検索サマリー）

##### ノード5: Code: Parse Response
- **機能**: Geminiの出力をJSON解析し、構造化データに変換
- **課題**: 
  - Geminiの出力に余分な`}`が含まれる場合がある
  - `\n`のエスケープ処理が必要
- **現在の対策**: 
  - 余分な閉じ括弧を自動削除
  - `\n`を改行に変換
- **出力**:
  ```json
  {
    "raw_response": {...},
    "titles": [...],
    "search_date": "...",
    "search_summary": "...",
    "generated_at": "..."
  }
  ```

##### ノード6: Code: Format Title Suggestions ※未実装
- **機能**: タイトル提案をMarkdown形式に整形
- **入力**: ノード5の出力
- **出力**: 
  ```json
  {
    "markdown": "# Note記事タイトル提案\n\n...",
    "title_count": 15,
    "generated_at": "..."
  }
  ```
- **状態**: **未実装** - 現在ノード5の生データがそのまま保存されている

##### ノード7: GitHub Create File (タイトル提案)
- **機能**: タイトル提案をGitHubに保存
- **設定**:
  - Repository: `instkoni/sns-content-automation`
  - File Path: `note_articles/title_suggestions/{{ $now.toFormat('yyyy-MM-dd_HHmmss') }}.md`
  - File Content: `{{ $json.markdown }}`
  - Commit Message: `Add note title suggestions generated on {{ $now.toFormat('yyyy-MM-dd HH:mm:ss') }}`
  - Branch: `main`
- **課題**: 
  - ファイル名フォーマットが`YYYY-MM-DD`（間違い）になっている → `yyyy-MM-dd`に修正必要
  - ノード6未実装のため、生データが保存されている

##### ノード8: Code: Format AI News
- **機能**: AIニュースをMarkdown形式に整形
- **入力**: ノード5の出力
- **出力**:
  ```json
  {
    "filename": "2026-01-17_130856--AI-news.md",
    "markdown": "# 2026-01-17 AI News Archive\n\n...",
    "date": "2026-01-17",
    "title_count": 15
  }
  ```
- **状態**: **実装済み・動作確認済み**

##### ノード9: GitHub Create File (AIニュース)
- **機能**: AIニュースアーカイブをGitHubに保存
- **設定**:
  - Repository: `instkoni/sns-content-automation`
  - File Path: `note_articles/ai_news_archive/{{ $json.date }}_{{ $now.toFormat('HHmmss') }}--AI-news.md`
  - File Content: `{{ $json.markdown }}`
  - Commit Message: `Add AI news archive for {{ $json.date }}`
  - Branch: `main`
- **課題**: 
  - 初回実行時にフォルダが存在しないためエラーが発生する可能性
  - `sha`エラーが発生（既存ファイルとの競合）

#### 2.1.3 現在の課題

| 課題 | 影響 | 優先度 | 対策 |
|------|------|--------|------|
| ノード6未実装 | タイトル提案ファイルが生データのまま | **高** | ノード6のコード実装 |
| ノード7のファイル名フォーマット | `YYYY-MM-DD`形式で保存される | 中 | `toFormat('yyyy-MM-dd')`に修正 |
| ノード9のフォルダ作成エラー | 初回実行時にエラー | 中 | 時刻付きファイル名で回避済み |
| Gemini出力の不安定性 | JSON解析エラーが発生する | 中 | ノード5でエラーハンドリング実装済み |

---

## 3. 今後の拡張計画

### 3.1 ワークフロー2: Note記事本文自動生成 ⭐最重要

**目的**: タイトル提案を元に、完全なNote記事（本文）を自動生成

#### ノード構成（案）

```
[1] Manual Trigger (または選択したタイトルを入力)
  ↓
[2] Input: 選択したタイトル + 追加指示（任意）
  ↓
[3] Manus API: Google Search + 情報収集
  ↓
[4] Manus API: 記事本文生成（3000〜5000文字）
  ↓
[5] Code: Markdown整形 + メタ情報追加
  ↓
[6] GitHub: 記事下書きを保存
  ↓
[7] （オプション）Manus API: アイキャッチ画像プロンプト生成
  ↓
[8] （オプション）GitHub: 画像プロンプトを保存
```

#### プロンプト設計

**ステップ1: 情報収集プロンプト**

```
あなたはAI専門のリサーチャーです。
以下のタイトルに関する最新情報をGoogle Searchで調査し、記事執筆に必要な情報を収集してください。

【タイトル】
{{selected_title}}

【調査項目】
1. 発表日・発表元
2. 主要な機能・特徴（5つ以上）
3. 競合製品との比較
4. ユーザーの反応・評判
5. 実際の使用例・ユースケース
6. 価格・料金プラン
7. 今後の展開・ロードマップ

【出力形式】
JSON形式で構造化して出力してください。
```

**ステップ2: 記事本文生成プロンプト**

```
あなたはinstkoniのnote記事を執筆するライターです。
以下の調査結果を元に、instkoniのスタイルでnote記事を執筆してください。

【タイトル】
{{selected_title}}

【調査結果】
{{research_data}}

【instkoniのnote記事スタイル】
- 文字数: 3000〜5000文字
- トーン: カジュアル、フレンドリー、初心者にも分かりやすい
- 構成:
  1. 導入（フック）: 読者の関心を引く驚き・疑問（200文字）
  2. 背景・文脈: なぜ今これが重要なのか（300文字）
  3. 本題: 詳細な説明・機能紹介（2000文字）
  4. 実用例: 具体的な使い方・活用法（800文字）
  5. 考察: 今後の展望・読者へのメッセージ（500文字）
  6. まとめ: 要点の再確認（200文字）
- 見出し: ##、###を適切に使用
- 箇条書き: 重要なポイントは箇条書きで整理
- 強調: **太字**で重要な用語を強調
- 絵文字: 適度に使用（見出しやポイントで）
- 引用: 公式情報は引用形式で明示
- 画像挿入位置: [画像1: ○○のスクリーンショット]のように指示

【注意事項】
- 専門用語は初心者向けに解説を加える
- 「ですます調」で統一
- 読者に語りかけるような文体
- 具体例を豊富に盛り込む
- 最後に「あなたはどう思いますか？」など読者への問いかけを入れる

【出力形式】
Markdown形式で出力してください。
```

#### 生成される記事の構成例

```markdown
# 【速報】月額8ドル！？OpenAIの新プラン「ChatGPT Go」と「広告導入」がついに開始…！💸🤖

## はじめに

ついに来ましたね…！OpenAIが2026年1月16日、衝撃の発表をしました。月額たったの8ドルで使える新プラン「ChatGPT Go」と、無料版への広告導入です。「え、広告？」「8ドルって安すぎない？」と思ったあなた、正解です。この発表、実はAI業界の大きな転換点なんです。

## なぜ今、この発表なのか？

...(300文字)

## ChatGPT Goとは？

### 料金プラン比較

| プラン | 月額 | 機能 |
|--------|------|------|
| 無料版 | $0 | 広告あり、GPT-4o mini |
| **ChatGPT Go** | **$8** | 広告なし、GPT-4o、画像生成 |
| Plus | $20 | 全機能、優先アクセス |

...(2000文字)

## 実際に使ってみた

...(800文字)

## 今後の展望

...(500文字)

## まとめ

...(200文字)

あなたはChatGPT Go、使ってみたいですか？コメントで教えてください！

---

**参考リンク**
- [OpenAI公式ブログ](https://openai.com/blog/...)
- [料金プラン詳細](https://openai.com/pricing)

**関連記事**
- [過去の記事タイトル1]
- [過去の記事タイトル2]
```

#### 追加機能: アイキャッチ画像プロンプト生成

```
以下のnote記事に最適なアイキャッチ画像を、Midjourney V8で生成するためのプロンプトを作成してください。

【記事タイトル】
{{article_title}}

【記事内容（要約）】
{{article_summary}}

【画像要件】
- サイズ: 16:9（横長）
- スタイル: モダン、テック系、親しみやすい
- 色調: 明るめ、ポップ
- 要素: タイトルに関連するビジュアルメタファー
- テキスト: なし（画像のみ）

【出力】
Midjourney V8用のプロンプト（英語、200文字以内）を出力してください。
```

---

### 3.3 ワークフロー4: LinkedIn投稿自動リライト

**目的**: Note記事を元にLinkedIn用の投稿を自動生成

#### ノード構成（案）

```
[1] Manual Trigger (または Schedule Trigger)
  ↓
[2] GitHub: 最新のNote記事を取得
  ↓
[3] Manus API: LinkedIn用にリライト
  ↓
[4] Code: フォーマット整形
  ↓
[5] GitHub: LinkedIn投稿案を保存
```

#### プロンプト設計

```
あなたはプロフェッショナルなLinkedInコンテンツライターです。
以下のNote記事を、LinkedIn投稿用に最適化してください。

【変換ルール】
- 文字数: 1500〜2000文字
- トーン: カジュアルからビジネスカジュアルに調整
- 構成: フック（1-2行）→ 本文 → CTA（行動喚起）
- ハッシュタグ: 5〜10個（#生成AI #AIツール など）
- 絵文字: 控えめに使用（Note記事より減らす）

【Note記事】
{{note_content}}
```

### 3.4 ワークフロー5: X（Twitter）投稿自動生成

**目的**: Note記事やAIニュースを元に、X投稿を自動生成

#### ノード構成（案）

```
[1] Schedule Trigger (毎日9:00, 12:00, 18:00)
  ↓
[2] GitHub: AIニュースアーカイブから最新ニュースを取得
  ↓
[3] Manus API: X投稿用に要約（280文字以内）
  ↓
[4] Code: フォーマット整形
  ↓
[5] GitHub: X投稿案を保存（または直接投稿API連携）
```

#### プロンプト設計

```
以下のAIニュースを、X（Twitter）投稿用に280文字以内で要約してください。

【要件】
- 文字数: 280文字以内
- トーン: キャッチー、興味を引く
- 構成: フック（驚き・疑問）→ 要点 → ハッシュタグ
- ハッシュタグ: 2〜3個
- 絵文字: 1〜2個

【AIニュース】
{{news_content}}
```

### 3.5 ワークフロー6: Suno音楽生成プロンプト作成

**目的**: MV制作のための音楽生成プロンプトを自動生成

#### ノード構成（案）

```
[1] Manual Trigger
  ↓
[2] Input: MVコンセプト・テーマを入力
  ↓
[3] Manus API: Suno用プロンプト生成
  ↓
[4] Code: フォーマット整形
  ↓
[5] GitHub: プロンプトを保存
```

#### プロンプト設計

```
あなたは音楽プロデューサーです。
以下のMVコンセプトに基づいて、Suno AI用の音楽生成プロンプトを作成してください。

【MVコンセプト】
{{mv_concept}}

【出力形式】
- ジャンル: (例: Electronic, Ambient, Cinematic)
- BPM: (例: 120)
- キー: (例: C major)
- ムード: (例: Dreamy, Energetic, Melancholic)
- 楽器構成: (例: Synth, Piano, Strings)
- Sunoプロンプト: (英語、200文字以内)
```

### 3.6 ワークフロー7: MV企画・絵コンテ自動生成

**目的**: 音楽に合わせたMVの企画書と絵コンテを自動生成

#### ノード構成（案）

```
[1] Manual Trigger
  ↓
[2] Input: 楽曲情報・コンセプト
  ↓
[3] Manus API: MV企画書生成
  ↓
[4] Manus API: シーン分割・絵コンテ生成
  ↓
[5] Code: Markdown整形
  ↓
[6] GitHub: 企画書・絵コンテを保存
```

### 3.7 ワークフロー8: イラスト/動画プロンプト生成

**目的**: Midjourney、Runway、Soraなどの生成AI用プロンプトを自動生成

#### ノード構成（案）

```
[1] Manual Trigger
  ↓
[2] GitHub: 絵コンテを取得
  ↓
[3] Manus API: 各シーンのプロンプト生成
  ↓
[4] Code: プロンプト整形（Midjourney/Runway/Sora別）
  ↓
[5] GitHub: プロンプト集を保存
```

---

## 4. Manus API（アンチグラビティ）活用戦略

### 4.1 Manus APIの特徴

| 特徴 | 説明 | 活用シーン |
|------|------|-----------|
| Super Agent | 高度な推論・計画能力 | 複雑なコンテンツ生成、企画立案 |
| Google Search統合 | リアルタイム情報取得 | 最新AIトレンド調査 |
| マルチモーダル | テキスト・画像・音声対応 | MV企画、絵コンテ生成 |
| 長文対応 | 8192トークン以上の出力 | 詳細な企画書、記事生成 |

### 4.2 Manus API vs Google Gemini 使い分け

| 用途 | 推奨API | 理由 |
|------|---------|------|
| タイトル提案 | **Google Gemini** | Google Search統合、コスト効率 |
| AIニュース収集 | **Google Gemini** | リアルタイム検索、高速 |
| **Note記事本文生成** | **Manus API** | 長文生成、高度な構成力、情報収集 |
| LinkedIn リライト | **Manus API** | 高度な文章調整、トーン変換 |
| X投稿生成 | **Google Gemini** | 短文生成、高速 |
| Suno プロンプト | **Manus API** | 音楽知識、クリエイティブ |
| MV企画書 | **Manus API** | 複雑な企画立案、構造化 |
| 絵コンテ生成 | **Manus API** | ビジュアル理解、シーン分割 |
| プロンプト生成 | **Manus API** | 生成AI専門知識 |

### 4.3 コスト管理

**Manus API料金**:
- 入力: $3 / 1M tokens
- 出力: $15 / 1M tokens

**推定コスト（月間）**:
- タイトル提案（週1回）: 約$0.50
- **Note記事本文生成（週2回）**: 約$3.00
- LinkedIn リライト（週2回）: 約$1.00
- X投稿（毎日3回）: 約$2.00
- MV企画（月2回）: 約$1.50
- **合計**: 約$8.00/月

---

## 5. GitHubリポジトリ構成

```
sns-content-automation/
├── note_articles/
│   ├── past_titles.md              # 過去記事タイトル一覧（手動更新）
│   ├── title_suggestions/          # タイトル提案（自動生成）
│   │   └── 2026-01-17_130856.md
│   ├── ai_news_archive/            # AIニュースアーカイブ（自動生成）
│   │   └── 2026-01-17_130856--AI-news.md
│   └── drafts/                     # 記事下書き（手動作成）
│
├── linkedin_posts/                 # LinkedIn投稿案（自動生成）
│   └── 2026-01-17_post.md
│
├── x_posts/                        # X投稿案（自動生成）
│   └── 2026-01-17_posts.md
│
├── mv_projects/                    # MV企画・制作関連
│   ├── concepts/                   # MVコンセプト
│   ├── music_prompts/              # Suno プロンプト
│   ├── storyboards/                # 絵コンテ
│   └── generation_prompts/         # イラスト/動画プロンプト
│
└── README.md                       # リポジトリ説明
```

---

## 6. 次のアクションアイテム

### 6.1 即座に修正が必要な項目

1. **ノード6の実装** - タイトル提案のMarkdown整形
2. **ノード7のファイル名修正** - `toFormat('yyyy-MM-dd')`に変更
3. **ワークフロー全体のテスト** - すべてのノードが正常動作するか確認

### 6.2 短期（1週間以内）

1. **ワークフロー2の実装** - Note記事本文自動生成（最優先）
2. **過去記事一覧の更新** - `past_titles.md`に最新記事を追加
3. **スケジュール実行の設定** - 週次でタイトル提案を自動実行

### 6.3 中期（1ヶ月以内）

1. **ワークフロー3の実装** - LinkedIn投稿自動リライト
2. **ワークフロー4の実装** - X投稿自動生成
3. **ワークフロー5の実装** - Suno プロンプト生成
3. **Manus API統合テスト** - 各ワークフローでの動作確認

### 6.4 長期（3ヶ月以内）

1. **ワークフロー6の実装** - MV企画・絵コンテ自動生成
2. **ワークフロー7の実装** - イラスト/動画プロンプト生成
3. **全体最適化** - コスト削減、速度改善、エラーハンドリング強化

---

## 7. 参考資料

- **n8n公式ドキュメント**: https://docs.n8n.io/
- **Manus API仕様**: https://help.manus.im
- **Google Gemini API**: https://ai.google.dev/
- **GitHub API**: https://docs.github.com/rest
- **ユーザーnote記事スタイル分析**: `/home/ubuntu/upload/ユーザー（instkoni）のnote記事スタイル分析.pdf`

---

**作成者**: Manus AI Agent  
**最終更新**: 2026年1月17日 13:20
