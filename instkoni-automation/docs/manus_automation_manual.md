# ManusAI 自動校正・リライトツール 運用マニュアル

## 事前準備

### 1. Python依存パッケージのインストール

```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/instkoni-automation
pip install -r requirements-manus.txt
```

### 2. Playwrightブラウザのインストール

```bash
playwright install chromium
```

### 3. 環境変数の設定

```bash
cp .env.example .env
```

必要に応じて `.env` を編集：
```
INPUT_DIR=articles/drafts
OUTPUT_DIR=articles/drafts2
ANALYSIS_FILE=config/article_analysis.md
```

### 4. 記事分析ファイルの編集

`config/article_analysis.md` を開き、あなたの執筆スタイルを記入してください。

### 5. 初回ログイン（必須）

初回はManusAIへの手動ログインが必要です：

```bash
python manus_automation.py --debug
```

1. ブラウザが起動したら、ManusAIに手動でログイン
2. ログイン完了後、Playwright Inspectorの「Resume」をクリック
3. 以降はログイン状態が `browser-data-manus/` に保存される

---

## 基本的な使い方

### 記事を処理する

```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/instkoni-automation
python manus_automation.py
```

### デバッグモードで実行

途中で一時停止し、手動操作で確認したい場合：

```bash
python manus_automation.py --debug
```

---

## 実行の流れ

### Step 1: 下書き記事を配置

`articles/drafts/` に下書き記事（.md）を配置します。

```
articles/drafts/
└── your-article.md   ← 最新のファイルが自動選択される
```

### Step 2: スクリプト実行

```bash
python manus_automation.py
```

### Step 3: 出力確認

処理済みファイルは以下に保存されます：

```
articles/drafts2/
├── 20260120_your-article_推敲版.md
├── 20260120_your-article_ファクトチェック.md
└── 20260120_your-article_参考情報.md
```

---

## 実行ログの見方

```
==================================================
🤖 ManusAI 自動校正・リライトツール
==================================================
📁 入力ディレクトリ: .../articles/drafts
📁 出力ディレクトリ: .../articles/drafts2
📄 分析ファイル: .../config/article_analysis.md
🔧 デバッグモード: OFF
==================================================

📄 最新の下書き: your-article.md          ← 処理対象
📝 プロンプトを保存: .../last_prompt.txt
📝 プロンプト文字数: 5000文字

🌐 ブラウザを起動中...
--- your-article.md の処理を開始 ---

📍 ManusAIにアクセス中...
✍️ プロンプトを入力中...
   📝 入力欄を発見: textarea
   📝 プロンプト入力完了（5000文字）
🚀 送信中...
   ✅ 送信ボタンをクリック

⏳ ManusAIの処理を待機中（最大30分）...
⏳ 10秒経過...
⏳ 20秒経過...
...
✅ 処理完了（180秒）

📥 成果物を抽出中...
📥 成果物を保存中...
   ✅ 20260120_your-article_推敲版.md
   ✅ 20260120_your-article_ファクトチェック.md
   ✅ 20260120_your-article_参考情報.md

--- your-article.md の処理が完了 ---

🔒 ブラウザを閉じます...

✅ 処理完了
```

---

## トラブルシューティング

### 問題: ログイン画面が表示される

**原因**: セッションが切れている

**対処**:
1. `--debug` モードで実行
2. 手動でログイン
3. 再実行

### 問題: 入力欄が見つからない

**原因**: ManusAIのUI変更、またはページ読み込み未完了

**対処**:
1. `--debug` モードで実行し、ページを確認
2. `articles/drafts2/debug_*.png` のスクリーンショットを確認
3. 必要に応じてスクリプトのセレクタを修正

### 問題: 処理がタイムアウトする

**原因**: ManusAIの処理が長い、またはフリーズ

**対処**:
1. 記事が長すぎる場合は分割を検討
2. ManusAIの状態を手動で確認
3. 再実行

### 問題: 成果物が正しく分割されない

**原因**: ManusAIの出力形式が想定と異なる

**対処**:
1. `articles/drafts2/debug_04_completed.png` を確認
2. 出力形式に合わせて `extract_outputs()` 関数を調整

### 問題: ブラウザが起動しない

**原因**: Playwrightの問題

**対処**:
```bash
playwright install chromium
```

---

## ファイル構成

| ファイル/フォルダ | 説明 |
|------------------|------|
| `manus_automation.py` | メインスクリプト |
| `browser-data-manus/` | ブラウザセッション（削除するとログアウト） |
| `config/article_analysis.md` | 執筆スタイル分析 |
| `.env` | 環境変数設定 |
| `requirements-manus.txt` | Python依存パッケージ |
| `articles/drafts/` | 入力: 下書き記事 |
| `articles/drafts2/` | 出力: 処理済み記事 |
| `articles/drafts2/last_prompt.txt` | 最後に使用したプロンプト |
| `articles/drafts2/debug_*.png` | デバッグ用スクリーンショット |

---

## カスタマイズ

### プロンプトの変更

`manus_automation.py` の `MASTER_PROMPT_TEMPLATE` を編集：

```python
MASTER_PROMPT_TEMPLATE = """
# 指示: Note記事の品質向上

あなたはプロの編集者です...
"""
```

### 待機時間の変更

`wait_for_processing_complete()` 関数のパラメータを調整：

```python
async def wait_for_processing_complete(page: Page, timeout_minutes: int = 30):
    # timeout_minutes を変更（デフォルト30分）
```

### 出力ファイル名の変更

`save_outputs()` 関数の `files_to_save` を編集：

```python
files_to_save = [
    (f"{timestamp}_{title}_推敲版.md", outputs.get("revised_article", "")),
    # 他のファイル名を変更
]
```

---

## よくある質問

**Q: 一度に複数の記事を処理できますか？**

A: 現在は最新の1記事のみ対応。複数処理は今後の改善予定。

**Q: 処理にどのくらい時間がかかりますか？**

A: 記事の長さとManusAIの負荷により異なる。通常3〜10分程度。

**Q: ログイン情報はどこに保存される？**

A: `browser-data-manus/` フォルダにブラウザのCookie等が保存される。このフォルダを削除すると再ログインが必要。

**Q: Gensparkツールと併用できますか？**

A: 可能。それぞれ別のセッションディレクトリを使用しているため、干渉しない。
