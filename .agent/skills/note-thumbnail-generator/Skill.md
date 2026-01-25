# Note Thumbnail Generator Skill

このスキルは、Note記事のサムネイル作成を半自動化します。記事ネタからAIO/SEO対策済みのタイトルを生成し、Canvaアプリと連携してサムネイルを作成します。

## 機能

- Gemini 3 Proを使用したタイトル自動生成（3案）
- ジャンル別（人生、副業、AI、有料、雑記、資格、本業）のトーン調整
- キーワード自動抽出
- FastAPIローカルサーバー（ポート5002）の起動
- ngrokによるインターネット公開
- Canvaアプリとの自動データ連携

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
