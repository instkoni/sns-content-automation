# Note Thumbnail Generator - 実装内容と設計書（最新版）

**最終更新日**: 2026年1月26日  
**バージョン**: 2.0.0  
**実装状況**: フェーズ1完了、フェーズ2未着手

---

## プロジェクト概要

**目的**: Note記事のトップ画像（サムネイル）作成を半自動化するシステム

**アプローチ**: Antigravity IDE環境でAgent Skillsを構築し、ジャンル選択→記事ネタ入力→AIO/SEO対策済みタイトル生成→イラスト生成→Canvaテンプレートと合成→指定パスに保存、という一連のワークフローを自動化

**開発環境**: Antigravity IDE（デスクトップアプリ）+ Canva Apps SDK

---

## システムアーキテクチャ

### 全体構成

```
┌─────────────────────────────────────────────────────────────┐
│                    Antigravity IDE                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Agent Skills: Note Thumbnail Generator       │  │
│  │                                                       │  │
│  │  1. 記事選択 (select_article.py)                     │  │
│  │     ↓                                                 │  │
│  │  2. タイトル生成 (Antigravityエージェント + Gemini)  │  │
│  │     ↓                                                 │  │
│  │  3. ローカルサーバー起動 (server.py + ngrok)         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ngrok公開URL
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Canva Apps SDK                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      Noteサムネイルアシスタント (app.tsx)            │  │
│  │                                                       │  │
│  │  1. タイトル・キーワード取得                         │  │
│  │  2. 素材検索/生成                                    │  │
│  │  3. 自動レイアウト実行                               │  │
│  │  4. PNG形式でエクスポート                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
              保存先: articles/Notetitle/
              形式: YYYYMMDD_Noteサムネイル(N).png
```

### 技術スタック

| 項目 | 技術 | 用途 | 実装状況 |
|------|------|------|---------|
| 開発環境 | Antigravity IDE | Agent Skills開発プラットフォーム | ✅ 完了 |
| AIモデル（タイトル生成） | Gemini 2.0 Flash Exp | AIO/SEO対策済みタイトル生成 | ✅ 完了 |
| AIモデル（イラスト生成） | Nanobananapro | サムネイル用イラスト生成 | 🔲 未実装 |
| プログラミング言語（サーバー） | Python 3.11 | スクリプト実装 | ✅ 完了 |
| プログラミング言語（Canva） | TypeScript/React | Canvaアプリ実装 | 🔲 未実装 |
| Webフレームワーク | FastAPI + Uvicorn | ローカルサーバー | ✅ 完了 |
| トンネリング | ngrok | ローカルサーバーの公開 | ✅ 完了 |
| デザインツール | Canva Apps SDK | サムネイルレイアウト | 🔲 未実装 |

---

## ディレクトリ構造

```
/Volumes/WDBLACK_2TB/Git/sns-content-automation/
├── .agent/
│   └── skills/
│       └── note-thumbnail-generator/
│           ├── SKILL.md                    # エージェント向けドキュメント ✅
│           ├── select_article.py           # 記事選択スクリプト ✅
│           ├── server.py                   # FastAPI + ngrokサーバー ✅
│           ├── requirements.txt            # Python依存関係 ✅
│           └── config/
│               ├── genres.json             # ジャンル設定（7種類） ✅
│               └── prompts.json            # プロンプトテンプレート ✅
│
├── articles/
│   ├── drafts2/                            # 記事ソースフォルダ
│   │   ├── 20260124__AI_Copyright_Update/
│   │   ├── 20260124__ChatGPT_Go_vs_Gemini/
│   │   └── ...（16フォルダ）
│   │
│   └── Notetitle/                          # サムネイル保存先（未実装）
│       ├── 20260126_Noteサムネイル(051).png
│       └── ...
│
└── canva-app/                              # Canva Apps SDK（未実装）
    ├── src/
    │   └── app.tsx                         # メインコンポーネント 🔲
    ├── manifest.json                       # アプリマニフェスト 🔲
    └── package.json                        # npm依存関係 🔲
```

---

## 実装済みファイル詳細

### 1. SKILL.md ✅

**役割**: Antigravityエージェント向けのスキル説明書

**主要内容**:
- スキルの概要とアーキテクチャ
- ワークフロー（ステップ1〜6）
- エージェント向け実装ガイド（Pythonコード例）
- 利用可能なジャンル一覧
- トラブルシューティング

**重要な設計方針**:
- エージェントが設定ファイル（genres.json, prompts.json）を自動読み込み
- ユーザーはプロンプトを入力不要
- エージェントが直接Geminiを呼び出してタイトル生成

**ファイルパス**: `/Volumes/WDBLACK_2TB/Git/sns-content-automation/.agent/skills/note-thumbnail-generator/SKILL.md`

---

### 2. select_article.py ✅

**役割**: 記事フォルダから記事を選択し、内容を出力

**主要機能**:
- `articles/drafts2`配下のフォルダを自動検出
- 記事ファイル（.md, .txt）の有無をチェック（✓/✗表示）
- インタラクティブな記事選択（番号入力）
- JSON形式での出力（`--output-json`オプション）

**使用例**:
```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/.agent/skills/note-thumbnail-generator
python3 select_article.py --output-json
```

**出力形式**:
```json
{
  "folder_name": "20260124__AI_Copyright_Update",
  "file_path": "/Volumes/.../AI著作権に関する参考情報源URLリスト.md",
  "content": "記事の全文...",
  "content_length": 2844
}
```

**テスト結果**: ✅ 正常動作確認済み（16フォルダ検出、記事選択・読み込み成功）

---

### 3. server.py ✅

**役割**: FastAPI + ngrokでCanvaアプリにデータを提供

**主要機能**:
- FastAPIでローカルサーバーを起動（ポート5002）
- ngrokコマンドを直接実行してインターネット公開
- `/data`エンドポイント: タイトルとキーワードを返す
- `/shutdown`エンドポイント: サーバーを終了
- CORS設定: Canvaアプリからのアクセスを許可
- 自動終了機能: Canvaアプリがデータ取得後に終了

**使用例**:
```bash
python3 server.py \
  --title "【2026年最新】AI著作権の全貌とクリエイターが知るべき3つの自衛策" \
  --keywords "AI著作権,フェアユース,クリエイター保護,法規制,2026年" \
  --genre "AI"
```

**エンドポイント**:
- `GET /data`: タイトル、キーワード、ジャンルを返す
- `POST /shutdown`: サーバーを終了

**重要な実装変更**:
- **変更前**: `pyngrok`パッケージを使用（SSL証明書エラーで失敗）
- **変更後**: `subprocess`でngrokコマンドを直接実行（成功）

**テスト結果**: ✅ 正常動作確認済み（ngrok起動成功、公開URL取得成功）

**テスト時の公開URL**: `https://pattie-rufous-viola.ngrok-free.dev`

---

### 4. config/genres.json ✅

**役割**: 7つのジャンルの設定を管理

**ジャンル一覧**:

| ジャンル | トーン | ターゲット読者 | キーワードヒント |
|---------|--------|---------------|-----------------|
| 人生 | 共感的で温かみのある | 人生の転機を迎えている人 | 人生、経験、学び、成長、気づき |
| 副業 | 実践的で具体的な | 副業を始めたい人 | 副業、収入、スキル、実践、ノウハウ |
| AI | 最新トレンドを押さえた専門的な | AI技術に関心がある人 | AI、ChatGPT、生成AI、活用、最新 |
| 有料 | 価値を強調する説得力のある | 深い知識を求めている人 | 限定、独自、ノウハウ、実践、成果 |
| 雑記 | 親しみやすくカジュアルな | 日常の気づきを楽しみたい人 | 日常、気づき、発見、体験、考察 |
| 資格 | 励ましと具体的アドバイスを含む | 資格取得を目指している人 | 資格、勉強法、合格、対策、実践 |
| 本業 | プロフェッショナルで実践的な | キャリアアップを目指す人 | 仕事、キャリア、スキル、実践、成果 |

**ファイル構造**:
```json
{
  "AI": {
    "name": "AI",
    "tone": "最新トレンドを押さえた専門的な",
    "target_audience": "AI技術に関心がある人、ビジネスでAIを活用したい人",
    "keywords_hint": "AI、ChatGPT、生成AI、活用、最新"
  },
  ...
}
```

---

### 5. config/prompts.json ✅

**役割**: Geminiに送信するプロンプトテンプレートを管理

**システムプロンプト**:
```
あなたはNote記事のタイトル作成の専門家です。AIO（AI Optimization）とSEO対策を考慮した、クリック率の高い魅力的なタイトルを生成します。

重要なポイント:
1. 数字を使って具体性を出す（例：「5つの方法」「3倍になった」）
2. ターゲット読者を明確にする（例：「初心者向け」「経営者必見」）
3. ベネフィットを明示する（例：「収入アップ」「時間短縮」）
4. 緊急性や希少性を演出する（例：「2026年最新」「知らないと損する」）
5. 感情を刺激する言葉を使う（例：「驚愕」「必見」「秘密」）
6. 記号を効果的に使う（【】『』！？など）
```

**ユーザープロンプトテンプレート**:
```
以下の記事内容から、{genre}ジャンルのNote記事タイトルを3案作成してください。

記事内容:
{topic}

ジャンル: {genre}
トーン: {tone}
ターゲット読者: {target_audience}
キーワードヒント: {keywords_hint}

要件:
1. タイトルは30〜40文字程度
2. {genre}ジャンルのトーンに合わせる
3. AIO/SEO対策を考慮する
4. クリック率が高くなるような魅力的な表現を使う
5. 3案すべて異なるアプローチで作成する

出力形式:
1. [タイトル1]
2. [タイトル2]
3. [タイトル3]

キーワード: [カンマ区切りで5〜7個]
```

---

### 6. requirements.txt ✅

**依存関係**:
```
fastapi==0.115.6
uvicorn==0.34.0
requests
```

**重要な変更**:
- **削除**: `pyngrok==7.2.2`（SSL証明書エラーのため）
- **追加**: `requests`（ngrok APIからURL取得のため）

**注意**: `google-generativeai`はAntigravity環境では不要（エージェントが直接Geminiを使用）

---

## ワークフロー詳細

### フェーズ1: Antigravity側（✅ 実装完了）

#### ステップ1: 記事選択
1. ユーザーがAntigravity IDEのAIチャットで指示
   ```
   Note Thumbnail Generatorスキルを使って、AIジャンルの記事のサムネイルタイトルを生成してください。
   ```
2. エージェントが`select_article.py --output-json`を実行
3. ユーザーが記事を選択（番号入力）
4. 記事内容がJSON形式で出力される

**テスト結果**: ✅ 成功（16フォルダ検出、記事選択・読み込み成功）

---

#### ステップ2: タイトル生成
1. エージェントが`config/genres.json`からジャンル情報を読み込む
2. エージェントが`config/prompts.json`からプロンプトを読み込む
3. エージェントが記事内容とジャンル情報を使ってプロンプトを構築
4. エージェントがGeminiを呼び出してタイトルを生成（3案）
5. エージェントがユーザーにタイトル案を提示

**テスト結果**: ✅ 成功（タイトル3案生成、キーワード抽出成功）

**生成例**:
```
1. 2026年最新！*AI著作権*の全貌とクリエイターが知るべき3つの*自衛策*
2. 【保存版】*AI法規制*はどう変わる？日米英の最新動向と*生存戦略*
3. 弁護士も注目！「AIは*道具*」と認められた著作権法の新たな*転換点*
```

---

#### ステップ3: タイトル選択
1. ユーザーが3案から1つを選択
2. エージェントが選択されたタイトルとキーワードを記録

**テスト結果**: ✅ 成功

---

#### ステップ4: ローカルサーバー起動
1. エージェントが`server.py`を実行
   ```bash
   python3 server.py \
     --title "選択したタイトル" \
     --keywords "キーワード1,キーワード2,キーワード3" \
     --genre "AI"
   ```
2. サーバーがngrokで公開される
3. 公開URLが表示される

**テスト結果**: ✅ 成功（ngrok起動成功、公開URL取得成功）

**テスト時の出力**:
```
============================================================
Note Thumbnail Generator - ローカルサーバー
============================================================
タイトル: テストタイトル
キーワード: キーワード1, キーワード2, キーワード3
ジャンル: AI
============================================================
ngrokを起動中（ポート 5002）...
✓ ngrokが起動しました: https://pattie-rufous-viola.ngrok-free.dev

============================================================
🚀 サーバーが起動しました！
============================================================
公開URL: https://pattie-rufous-viola.ngrok-free.dev
データエンドポイント: https://pattie-rufous-viola.ngrok-free.dev/data
終了エンドポイント: https://pattie-rufous-viola.ngrok-free.dev/shutdown
============================================================
```

---

### フェーズ2: Canva Apps SDK側（🔲 未実装）

#### ステップ5: Canvaでサムネイル作成
1. ユーザーがCanvaにログイン
2. サムネイルのテンプレートを開く
3. 「Noteサムネイルアシスタント」アプリを起動
4. アプリが自動的にngrokサーバーからタイトルとキーワードを取得
5. ユーザーが記事番号を入力（例：051）
6. 「素材を検索/生成」ボタンをクリック
7. 使用したい素材を選択
8. 「レイアウト実行」ボタンをクリック
9. 最終調整を行い、PNG形式でエクスポート

**実装状況**: 🔲 未実装

---

#### ステップ6: 自動終了
1. Canvaアプリがデータ取得完了を通知
2. サーバーが自動的に終了

**実装状況**: 🔲 未実装

---

## 設計上の重要な決定事項

### 1. アーキテクチャの分離

**決定**: Antigravityエージェント主導、Pythonスクリプトは補助的役割

**理由**:
- Antigravity IDEはGeminiを同梱しているため、APIキー不要
- エージェントが直接Geminiを使用できる
- Pythonスクリプトは記事選択とサーバー起動のみを担当

**当初の設計（変更前）**:
```
Pythonスクリプト → google-generativeai API → Gemini
```

**最終設計（変更後）**:
```
Antigravityエージェント → Gemini（直接）
Pythonスクリプト → 記事選択、サーバー起動のみ
```

---

### 2. 設定ファイルの自動読み込み

**決定**: ユーザーはプロンプトを入力不要、エージェントが自動読み込み

**理由**:
- ユーザーが毎回プロンプトを入力するのは非効率
- 設定ファイルに集約することで、メンテナンス性向上
- エージェントが自動的に設定を読み込んで使用

**実装方法**:
```python
# エージェントが実行するコード
import json
from pathlib import Path

config_dir = Path("/Volumes/.../config")

with open(config_dir / "genres.json", "r", encoding="utf-8") as f:
    genres = json.load(f)

with open(config_dir / "prompts.json", "r", encoding="utf-8") as f:
    prompts = json.load(f)

genre_info = genres["AI"]
system_prompt = prompts["system_prompt"]
user_prompt = prompts["user_prompt_template"].format(
    topic=article_content[:1000],
    genre=genre_info["name"],
    tone=genre_info["tone"],
    target_audience=genre_info["target_audience"],
    keywords_hint=genre_info["keywords_hint"]
)
```

---

### 3. 記事選択の自動化

**決定**: 手動入力ではなく、既存の記事ファイルから選択

**理由**:
- ユーザーが記事ネタを手動入力するのは非効率
- 既存の記事フォルダ（`articles/drafts2`）を活用
- 記事ファイル（.md, .txt）を自動検出

**実装方法**:
- `select_article.py`がフォルダを一覧表示
- ユーザーが番号を入力して選択
- 記事内容を自動的に読み込み

---

### 4. ngrokの実装方法変更

**当初の実装**: `pyngrok`パッケージを使用

**問題**: SSL証明書の検証エラーで失敗
```
An error occurred while downloading ngrok from https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip: 
<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:992)>
```

**最終実装**: `subprocess`でngrokコマンドを直接実行

**理由**:
- ngrokコマンドは既にインストール済み（`ngrok http 5002`で動作確認済み）
- `pyngrok`のSSL証明書問題を回避
- ngrok APIから公開URLを取得（`http://127.0.0.1:4040/api/tunnels`）

**実装コード**:
```python
import subprocess
import requests

# ngrokプロセスを起動
ngrok_process = subprocess.Popen(
    ["ngrok", "http", str(port)],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# ngrokが起動するまで待機
time.sleep(3)

# 公開URLを取得
response = requests.get("http://127.0.0.1:4040/api/tunnels")
tunnels = response.json()["tunnels"]
public_url = tunnels[0]["public_url"]
```

---

## テスト結果

### ✅ 成功したテスト

#### 1. Antigravity IDEのAIチャットでのテスト
- **テスト内容**: 「Note Thumbnail Generatorスキルを使って、AIジャンルの記事のサムネイルタイトルを生成してください。」
- **結果**: ✅ 成功（タイトル3案生成）
- **生成されたタイトル**:
  1. 2026年最新！*AI著作権*の全貌とクリエイターが知るべき3つの*自衛策*
  2. 【保存版】*AI法規制*はどう変わる？日米英の最新動向と*生存戦略*
  3. 弁護士も注目！「AIは*道具*」と認められた著作権法の新たな*転換点*

#### 2. select_article.pyの個別テスト
- **テスト内容**: `python3 select_article.py`
- **結果**: ✅ 成功
- **確認項目**:
  - ✅ 記事フォルダの一覧表示（16フォルダ検出）
  - ✅ 記事ファイルの有無チェック（✓/✗表示）
  - ✅ ユーザーによる記事選択（番号入力）
  - ✅ 記事ファイルの読み込み（2844文字）
  - ✅ 記事内容の表示

#### 3. server.pyの個別テスト
- **テスト内容**: `python3 server.py --title "テストタイトル" --keywords "キーワード1,キーワード2,キーワード3" --genre "AI"`
- **結果**: ✅ 成功
- **確認項目**:
  - ✅ FastAPIサーバー起動（ポート5002）
  - ✅ ngrokプロセス起動
  - ✅ 公開URL取得（`https://pattie-rufous-viola.ngrok-free.dev`）
  - ✅ `/data`エンドポイント動作確認

---

## トラブルシューティング

### 問題1: `google-generativeai`パッケージのAPIキーエラー

**症状**:
```
No API_KEY or ADC found. Please either:
  - Set the `GOOGLE_API_KEY` environment variable.
  - Manually pass the key with `genai.configure(api_key=my_api_key)`.
```

**原因**: ローカル環境（macOS）で実行していたため、APIキーが必要だった

**解決策**: Antigravity IDE内で実行することで、APIキー不要になる

---

### 問題2: `config/genres.json`の読み込みエラー

**症状**:
```
エラー: ジャンル 'AI' が見つかりません
利用可能なジャンル: genres
```

**原因**: JSONの構造が正しくなかった

**解決策**: 正しいJSON形式で再作成

---

### 問題3: 複数のPython環境の混在

**症状**: `pip install`でインストールしたパッケージが`python3`で認識されない

**原因**: Anaconda環境とPython 3.11環境が混在していた

**解決策**: `python3 -m pip install`で明示的にPython 3.11環境にインストール

---

### 問題4: `pyngrok`のSSL証明書エラー ⭐ 重要

**症状**:
```
エラー: ngrokの起動に失敗しました - An error occurred while downloading ngrok from https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip: 
<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:992)>
```

**原因**: `pyngrok`パッケージがngrokバイナリを自動ダウンロードしようとして、SSL証明書の検証に失敗

**解決策**: 
1. `pyngrok`パッケージを削除
2. `subprocess`でngrokコマンドを直接実行
3. ngrok APIから公開URLを取得

**実装変更**:
- `requirements.txt`から`pyngrok==7.2.2`を削除
- `requests`パッケージを追加
- `server.py`を修正（ngrokコマンドを直接実行）

---

### 問題5: server.pyの上書き失敗

**症状**: 修正版の`server.py`を上書きしたはずなのに、古いバージョンが実行される

**原因**: ファイルが正しく上書きされていなかった

**解決策**: ファイルの内容を再確認し、正しく上書き

---

## 未実装項目

### フェーズ2: Canva Apps SDK側（🔲 未実装）

#### 必要なファイル
1. `app.tsx` - Canvaアプリのメインコンポーネント
2. `manifest.json` - Canvaアプリのマニフェスト
3. `package.json` - npm依存関係

#### 必要な機能
1. ngrokサーバーからタイトル・キーワードを取得
2. 記事番号の入力
3. 素材検索/生成（Nanobananapro連携）
4. 自動レイアウト実行
5. サーバー終了通知

---

### フェーズ3: 統合テスト（🔲 未実装）

#### テスト項目
1. エンドツーエンドのワークフローテスト
2. エラーハンドリングの確認
3. 自動終了機能の確認
4. 保存先の確認（`articles/Notetitle/`）
5. ファイル名形式の確認（`YYYYMMDD_Noteサムネイル(N).png`）

---

## 次のステップ

### 短期（フェーズ2）
1. Canva Apps SDKの環境構築
2. `app.tsx`の実装
3. Nanobananapro連携の実装
4. 自動レイアウト機能の実装

### 中期（フェーズ3）
1. 統合テスト
2. エラーハンドリングの改善
3. ドキュメントの充実

### 長期（改善案）
1. 記事番号の自動採番
2. 複数のCanvaテンプレート対応
3. 保存先の柔軟な設定
4. ログ機能の追加
5. UIの改善（記事プレビュー、タイトル編集など）

---

## 参考資料

### Antigravity IDE
- 公式サイト: （2025年11月リリース）
- Agent Skills: `.agent/skills/`配下に配置
- 実行環境: デスクトップアプリ（macOS）

### Canva Apps SDK
- 公式ドキュメント: https://www.canva.dev/docs/apps/
- 開発者ポータル: https://www.canva.com/developers/

### ngrok
- 公式サイト: https://ngrok.com/
- ダウンロード: https://ngrok.com/download
- API: http://127.0.0.1:4040/api/tunnels

### Gemini
- 公式サイト: https://ai.google.dev/
- モデル: Gemini 2.0 Flash Exp

---

## ライセンス

MIT

---

## 更新履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-01-26 | 1.0.0 | 初版作成（フェーズ1完了時点） |
| 2026-01-26 | 2.0.0 | 最新の実装内容を反映（ngrok実装変更、テスト結果追加） |

---

## 作成者

- プロジェクト: Note Thumbnail Generator
- 開発環境: Antigravity IDE + Canva Apps SDK
- 実装フェーズ: フェーズ1完了（✅）、フェーズ2未着手（🔲）
- 最終テスト日: 2026年1月26日
