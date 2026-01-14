# 自動化スクリプト

このディレクトリには、ワークフローを効率化する自動化スクリプトが含まれています。

---

## 📋 利用可能なスクリプト

### 1. add_idea.py - 記事ネタ追加

**機能:**
- 対話形式で記事ネタを入力
- `ideas/ideas-list.md`に自動追加
- 記事IDを自動採番

**使用方法:**
```bash
python3 scripts/add_idea.py
```

**入力項目:**
- タイトル案
- カテゴリ(テクノロジー、ビジネス、マーケティング、副業、AI・自動化、その他)
- 優先度(高、中、低)
- メモ(任意)

---

### 2. create_article.py - 新規記事作成

**機能:**
- `ideas-list.md`から記事情報を取得
- テンプレートから記事ファイルを自動生成
- 調査ファイルも同時に作成
- ステータスを「執筆中」に自動更新

**使用方法:**
```bash
python3 scripts/create_article.py <記事ID>
```

**作成されるファイル:**
- `articles/drafts/YYYY-MM-DD-<記事ID>.md`: 記事本文
- `research/topics/research-<記事ID>.md`: 調査結果

---

### 3. publish_article.py - 記事公開処理

**機能:**
- 記事を`drafts/`から`published/`に移動
- 記事メタ情報を更新(ステータス、公開日、URL)
- `ideas-list.md`のステータスを「完了」に更新

**使用方法:**
```bash
python3 scripts/publish_article.py <記事ID> <Note URL>
```

---

## 🔄 ワークフロー全体

```
1. 記事ネタ追加
   ↓
   python3 scripts/add_idea.py
   ↓
2. 新規記事作成
   ↓
   python3 scripts/create_article.py <ID>
   ↓
3. 調査・執筆(手動)
   ↓
4. インフォグラフィック作成(手動)
   ↓
5. Note投稿(手動)
   ↓
6. 記事公開処理
   ↓
   python3 scripts/publish_article.py <ID> <URL>
   ↓
7. LinkedIn/X投稿(手動)
```

---

## 🛠️ 将来実装予定の機能

以下のスクリプトは将来的に実装予定です:

### 記事生成スクリプト
- `generate_article.py`: AIエージェントAPIを使用した記事自動生成
- `create_infographic.py`: インフォグラフィック自動生成

### リライトスクリプト
- `rewrite_for_linkedin.py`: LinkedIn向け自動リライト
- `create_x_thread.py`: X向けスレッド自動生成

### 投稿スクリプト
- `post_to_note.py`: Note自動投稿
- `post_to_linkedin.py`: LinkedIn自動投稿
- `post_to_x.py`: X自動投稿

### 管理スクリプト
- `update_ideas_list.py`: アイデアリスト自動更新
- `generate_report.py`: パフォーマンスレポート自動生成

---

## 💡 使い方のコツ

### エイリアスを設定(オプション)

Macの`~/.zshrc`または`~/.bash_profile`に追加:

```bash
# SNSコンテンツ自動化エイリアス
alias sns-cd='cd /Volumes/WDBLACK_2TB/Git/sns-content-automation'
alias sns-idea='python3 /Volumes/WDBLACK_2TB/Git/sns-content-automation/scripts/add_idea.py'
alias sns-create='python3 /Volumes/WDBLACK_2TB/Git/sns-content-automation/scripts/create_article.py'
alias sns-publish='python3 /Volumes/WDBLACK_2TB/Git/sns-content-automation/scripts/publish_article.py'
```

---

## 🐛 トラブルシューティング

### エラー: Permission denied
```bash
chmod +x scripts/*.py
```

### エラー: ファイルが見つからない
```bash
pwd
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation
```

---

## 🔗 関連ドキュメント

- [QUICKSTART.md](../docs/QUICKSTART.md): クイックスタートガイド
- [USAGE.md](../docs/USAGE.md): 詳細な使い方
- [PROMPTS.md](../docs/PROMPTS.md): AIエージェント用プロンプト集
