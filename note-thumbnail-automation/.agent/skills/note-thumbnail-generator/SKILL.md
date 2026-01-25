---
name: note-thumbnail-generator
description: Generates Note article thumbnails by orchestrating Gemini 3 Pro for title generation and Nano Banana Pro for illustration generation. Combines them with Canva templates and saves to specified path with automatic naming (YYYYMMDD_Noteサムネイル(N).png).
---

# Note Article Thumbnail Generator

このSkillは、Note記事のトップ画像（サムネイル）を自動生成する全体的なワークフローを管理します。

## 処理フロー

1. **ユーザー入力の取得**
   - ジャンルを選択（人生、副業、AI、有料、雑記、資格、本業）
   - 記事ネタを入力（テーマやキーワード）

2. **タイトル生成**
   - `gemini-title-generator` Skillを呼び出し
   - Gemini 3 Proで3つのタイトル案を生成
   - ユーザーに選択させる

3. **イラスト生成**
   - `nanobananapro-illustrator` Skillを呼び出し
   - 選択されたタイトルとジャンルに基づいてイラストを生成
   - Nano Banana Proが自動的に使用される

4. **画像合成**
   - `scripts/generate_thumbnail.py`を実行
   - Canvaテンプレートを読み込み
   - イラストをリサイズして配置
   - タイトルテキストをオーバーレイ
   - フォントサイズを自動調整

5. **ファイル保存**
   - 形式: `年月日_Noteサムネイル(番号).png`
   - 保存先: `/Volumes/WDBLACK_2TB/Git/sns-content-automation/articles/Notetitle/`
   - ディレクトリが存在しない場合は自動作成
   - 同日に複数ファイルがある場合は番号を自動インクリメント

## 使用方法

エージェントに以下のように指示してください：

Note記事のサムネイルを作成してください。
ジャンル: [ジャンル名]
記事ネタ: [テーマやキーワード]

エージェントは自動的にこのSkillを検出し、ワークフローを実行します。

## スクリプトの実行

画像合成は、Pythonスクリプト `scripts/generate_thumbnail.py` を使用します。

実行コマンド:
```bash
python3 scripts/generate_thumbnail.py --genre "AI" --title "選択されたタイトル" --illustration-path "/path/to/illustration.png"
```

設定ファイル

•
resources/template_config.json: 各ジャンルのテンプレート設定（配置位置、フォントサイズなど）

エラーハンドリング

•
テンプレート画像が見つからない場合: エラーメッセージを表示し、テンプレートの配置を確認

•
保存先パスへの書き込み権限がない場合: エラーメッセージを表示し、権限を確認

•
タイトルが長すぎる場合: 自動的にフォントサイズを縮小し、改行処理を実行
