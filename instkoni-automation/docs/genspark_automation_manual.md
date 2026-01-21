# Genspark Automation 運用マニュアル

## 事前準備

### 1. 依存パッケージのインストール

```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/instkoni-automation
npm install
```

### 2. 初回ログイン（必須）

初回実行時はGensparkへのログインが必要です。

```bash
npx ts-node genspark_automation.ts image --debug
```

1. ブラウザが起動したら、手動でGensparkにログイン
2. ログイン完了後、ブラウザを閉じる
3. 以降はログイン状態が `browser-data/` に保存される

---

## 基本的な使い方

### 画像生成を実行

```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/instkoni-automation
npx ts-node genspark_automation.ts image
```

### デバッグモードで実行

途中で一時停止し、手動操作で確認したい場合：

```bash
npx ts-node genspark_automation.ts image --debug
```

---

## 実行の流れ

### Step 1: 記事を配置

`articles/drafts/` に下書き記事（.md）を配置します。

```
articles/drafts/
└── your-article.md   ← 最新のファイルが自動選択される
```

### Step 2: スクリプト実行

```bash
npx ts-node genspark_automation.ts image
```

### Step 3: 出力確認

生成された画像は以下に保存されます：

```
articles/infographic/YYYYMMDDHHMMSS_記事名/
├── YYYYMMDDHHMMSS_記事名_01.png
├── YYYYMMDDHHMMSS_記事名_02.png
└── ...
```

---

## 実行ログの見方

```
==================================================
🤖 Genspark Automation Tool
==================================================
📁 下書きディレクトリ: .../articles/drafts
📁 インフォグラフィック保存先: .../articles/infographic
🔧 デバッグモード: OFF
==================================================

🎨 Genspark画像生成を開始します...

📄 最新の下書き: your-article.md          ← 処理対象の記事
📝 プロンプトを保存しました: .../last_prompt.txt
📝 プロンプト文字数: 3293文字
🌐 ブラウザを起動中...
📍 Genspark画像生成ページに移動中...
⚙️ GUI設定を開始します...
✅ 設定ボタンをクリックしました
✅ 2K をクリックしました
✅ 16:9 をクリックしました
✅ 設定完了
✍️ プロンプトを入力中...
✅ プロンプト入力完了
🚀 生成を開始...

==================================================
⏳ 画像生成を待機中（自動検出）...        ← 画像生成待ち
==================================================
⏳ 0秒経過 - 検出画像: 0枚
⏳ 5秒経過 - 検出画像: 0枚
...
⏳ 85秒経過 - 検出画像: 5枚
✅ 画像生成が完了しました！                ← 生成完了

📥 各画像をクリックしてダウンロードします...
   🖼️ [1/5] 画像をクリック中...
      📍 ダウンロードボタン発見
      ✅ ..._01.png (500KB)                ← ダウンロード成功
   ...

==================================================
✨ ダウンロード完了！
📁 保存先: .../infographic/20260120132501_your-article
==================================================

✅ 処理完了
🔒 ブラウザを閉じます...
```

---

## トラブルシューティング

### 問題: ログイン画面が表示される

**原因**: セッションが切れている

**対処**:
1. `--debug` モードで実行
2. 手動でログイン
3. 再実行

### 問題: 画像が0枚で終了する

**原因**: プロンプト送信に失敗している可能性

**対処**:
1. `--debug` モードで実行し、手動で送信ボタンをクリック
2. `articles/infographic/debug_*.png` でスクリーンショットを確認

### 問題: 画像が途中までしかダウンロードされない

**原因**: Genspark側で生成が遅延またはフリーズ

**対処**:
1. 再実行する
2. それでも発生する場合は手動でダウンロード

### 問題: ダウンロードボタンが見つからない

**原因**: UI変更の可能性

**対処**:
1. `--debug` モードで実行
2. 手動で画像をクリックし、ダウンロードボタンの位置を確認
3. 必要に応じてスクリプトのセレクタを更新

### 問題: ブラウザが起動しない

**原因**: Playwrightの問題

**対処**:
```bash
npx playwright install chromium
```

---

## ファイル構成

| ファイル/フォルダ | 説明 |
|------------------|------|
| `genspark_automation.ts` | メインスクリプト |
| `browser-data/` | ブラウザセッションデータ（削除するとログアウト） |
| `articles/drafts/` | 入力: 下書き記事 |
| `articles/infographic/` | 出力: 生成画像 |
| `articles/infographic/last_prompt.txt` | 最後に使用したプロンプト |
| `articles/infographic/debug_*.png` | デバッグ用スクリーンショット |

---

## 設定のカスタマイズ

### 解像度・アスペクト比の変更

`genspark_automation.ts` の以下の部分を編集：

```typescript
// 2K を選択 → 変更したい場合は '4K' など
const size2K = page.getByText('2K', { exact: true });

// 16:9 を選択 → 変更したい場合は '1:1' など
const ratio16_9 = page.getByText('16:9', { exact: true });
```

### プロンプトの変更

`genspark_automation.ts` の `generationPrompt` を編集：

```typescript
const generationPrompt = `このNOTE記事にインフォグラフィックを入れたい。
・記事を分析し、適切な数のインフォグラフィックを作成して欲しい。
・中項目レベルで１つずつ
・グラフィックレコーディング風の手描き図解にしてください。
...
```

---

## よくある質問

**Q: 一度に複数の記事を処理できますか？**

A: 現在は最新の1記事のみ対応。複数処理は今後の改善予定。

**Q: 生成される画像の枚数は？**

A: 記事の構成により異なる。Gensparkが自動判断（通常3〜6枚程度）。

**Q: 画像の品質は？**

A: 2K解像度（約2048px幅）、16:9アスペクト比で生成。

**Q: ログイン情報はどこに保存される？**

A: `browser-data/` フォルダにブラウザのCookie等が保存される。このフォルダを削除すると再ログインが必要。
