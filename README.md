# SNSコンテンツ自動化プロジェクト

Note記事作成からマルチプラットフォーム配信までのワークフローを管理・自動化するプロジェクトです。

## 🚀 クイックスタート

```bash
# リポジトリをクローン
git clone https://github.com/instkoni/sns-content-automation.git
cd sns-content-automation

# 記事ネタを追加
python3 scripts/add_idea.py

# 新規記事を作成
python3 scripts/create_article.py 001

# 記事を公開
python3 scripts/publish_article.py 001 https://note.com/...
```

詳しくは [QUICKSTART.md](docs/QUICKSTART.md) をご覧ください。

---

## 📁 ディレクトリ構造

```
sns-content-automation/
├── articles/              # 記事管理
│   ├── drafts/           # 下書き記事
│   └── published/        # 公開済み記事
├── ideas/                # 記事ネタ・アイデア管理
├── research/             # 調査・リサーチ結果
│   ├── topics/          # トピック別調査
│   ├── competitors/     # 競合分析
│   └── trends/          # トレンド調査
├── assets/              # メディアファイル
│   ├── infographics/   # インフォグラフィック
│   ├── images/         # 画像素材
│   └── designs/        # デザインファイル
├── templates/           # テンプレートファイル
├── scripts/             # 自動化スクリプト
├── workflows/           # ワークフロー定義
└── docs/                # ドキュメント
```

---

## 🎯 主な機能

### ✅ 実装済み

- **データ管理基盤**: GitHubでの一元管理
- **テンプレート**: 記事、調査、アイデアリスト
- **自動化スクリプト**: 記事ネタ追加、記事作成、公開処理
- **プロンプト集**: AIエージェント用の再利用可能なプロンプト
- **デザインガイドライン**: 統一されたビジュアルデザイン

### 🔜 今後の実装予定

- AIエージェントAPI連携
- インフォグラフィック自動生成
- マルチプラットフォーム自動投稿
- パフォーマンスレポート生成

---

## 📝 ワークフロー概要

### A) Note記事作成(約3.5時間 → 目標: 2時間)
1. 記事ネタの検索・リスト化
2. ネタの選定
3. 調査・情報収集
4. 記事作成
5. インフォグラフィック作成
6. Note投稿

### B) LinkedIn配信(約30分)
7. LinkedIn向けリライト
8. LinkedIn投稿

### C) X(Twitter)配信(約30分)
9. X向けパーツ分解
10. X投稿

### D) YouTube/Instagram配信(将来実装)
11. AI動画作成
12. 動画投稿

---

## 🛠️ 使用ツール

- **AIエージェント**: Genspark, Manus, Gemini
- **デザイン**: CANVA, Genspark
- **プラットフォーム**: Note, LinkedIn, X
- **バージョン管理**: Git, GitHub

---

## 📚 ドキュメント

- **[QUICKSTART.md](docs/QUICKSTART.md)**: 5分で始めるガイド
- **[USAGE.md](docs/USAGE.md)**: 詳細な使い方
- **[PROMPTS.md](docs/PROMPTS.md)**: AIエージェント用プロンプト集
- **[DESIGN_GUIDE.md](docs/DESIGN_GUIDE.md)**: デザインガイドライン
- **[scripts/README.md](scripts/README.md)**: スクリプト使い方

---

## 🎨 デザイン統一

### カラーパレット
- **プライマリーブルー**: `#3B82F6`
- **オレンジ**: `#F59E0B`
- **ライトグレー**: `#F8FAFC`

### サイズ
- **インフォグラフィック**: 1200x630px
- **Noteトップ画像**: 1280x670px

詳しくは [DESIGN_GUIDE.md](docs/DESIGN_GUIDE.md) をご覧ください。

---

## 🔧 セットアップ

### 必要なもの
- Git
- Python 3.6+
- GitHubアカウント

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/instkoni/sns-content-automation.git
cd sns-content-automation

# スクリプトに実行権限を付与
chmod +x scripts/*.py
```

---

## 💡 効率化のヒント

1. **テンプレートの活用**: 毎回同じ構造で作成
2. **プロンプトの再利用**: 効果的なプロンプトを保存
3. **バッチ処理**: 複数の記事を同時進行
4. **定期的なレビュー**: ワークフローを継続的に改善

---

## 📊 進捗管理

- [記事ネタリスト](ideas/ideas-list.md)
- [制作中の記事](articles/drafts/)
- [公開済み記事](articles/published/)
- [ワークフローチェックリスト](workflows/workflow-checklist.md)

---

## 🆘 サポート

質問や問題がある場合は、以下を参照してください:
- [QUICKSTART.md](docs/QUICKSTART.md)
- [USAGE.md](docs/USAGE.md)
- [scripts/README.md](scripts/README.md)

---

## 📅 更新履歴

- **2026-01-14**: プロジェクト初期化
  - ディレクトリ構造作成
  - テンプレート作成
  - 自動化スクリプト実装(add_idea, create_article, publish_article)
  - プロンプト集作成
  - デザインガイドライン作成

---

## 📄 ライセンス

このプロジェクトは個人利用を目的としています。

---

## 🙏 謝辞

このプロジェクトは、副業でのSNS発信を効率化するために作成されました。
