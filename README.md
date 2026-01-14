# SNSコンテンツ自動化プロジェクト

Note記事作成からマルチプラットフォーム配信までのワークフローを管理・自動化するプロジェクトです。

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

## 🚀 ワークフロー概要

### A) Note記事作成
1. 記事ネタの検索・リスト化
2. ネタの選定
3. 調査・情報収集
4. 記事作成
5. インフォグラフィック作成
6. Note投稿

### B) LinkedIn配信
7. LinkedIn向けリライト
8. LinkedIn投稿

### C) X(Twitter)配信
9. X向けパーツ分解
10. X投稿

### D) YouTube/Instagram配信(将来実装)
11. AI動画作成
12. 動画投稿

## 📝 使い方

詳細な使い方は [docs/USAGE.md](docs/USAGE.md) を参照してください。

## 🔧 セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/instkoni/sns-content-automation.git
cd sns-content-automation

# テンプレートを使用して新しい記事を開始
cp templates/article-template.md articles/drafts/YYYY-MM-DD-title.md
```

## 📊 進捗管理

- [記事ネタリスト](ideas/ideas-list.md)
- [制作中の記事](articles/drafts/)
- [公開済み記事](articles/published/)

## 🛠️ 使用ツール

- **AIエージェント**: Genspark, Manus, Gemini
- **デザイン**: CANVA
- **プラットフォーム**: Note, LinkedIn, X

## 📅 更新履歴

- 2026-01-14: プロジェクト初期化、ディレクトリ構造作成
