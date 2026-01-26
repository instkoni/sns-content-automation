---
name: note-thumbnail-generator
description: "Note記事のサムネイルタイトルを生成し、Canvaでサムネイルを作成するためのスキル。記事を選択し、AIがタイトル案を生成、ngrokサーバー経由でCanvaアプリにデータを連携します。"
---

# Note Thumbnail Generator Skill

Note記事のサムネイル作成を半自動化するスキルです。

## 実行手順

以下の手順を順番に実行してください。

---

## STEP 1: 記事一覧を表示

以下のコマンドを実行して、記事一覧を表示してください：

```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/.agent/skills/note-thumbnail-generator && python3 select_article.py --list
```

記事一覧が表示されたら、ユーザーに「どの記事のサムネイルを作成しますか？番号を入力してください」と質問してください。

---

## STEP 2: 記事を選択

ユーザーが番号（例: 1, 3, 5など）を入力したら、その番号を使って以下のコマンドを実行してください：

```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/.agent/skills/note-thumbnail-generator && python3 select_article.py --number [ユーザーが入力した番号] --output-json
```

**注意**: `[ユーザーが入力した番号]` は実際の数字に置き換えてください。例えばユーザーが「3」と入力したら `--number 3` となります。

---

## STEP 3: 設定ファイルを読み込む

以下の2つのファイルを読み込んでください：

1. `/Volumes/WDBLACK_2TB/Git/sns-content-automation/.agent/skills/note-thumbnail-generator/config/genres.json`
2. `/Volumes/WDBLACK_2TB/Git/sns-content-automation/.agent/skills/note-thumbnail-generator/config/prompts.json`

---

## STEP 4: タイトルを生成

ユーザーが指定したジャンル（AI、人生、副業、有料、雑記、資格、本業のいずれか）に基づいて、以下の情報でタイトルを3案生成してください：

- `genres.json` から該当ジャンルの `tone`、`target_audience`、`keywords_hint` を取得
- `prompts.json` の `system_prompt` と `user_prompt_template` を使用
- 記事内容（STEP 2で取得した `content`）を使用

生成したタイトル3案をユーザーに提示し、どれを使うか選択してもらってください。

---

## STEP 5: サーバーを起動

ユーザーがタイトルを選択したら、以下のコマンドを**バックグラウンドで**実行してください：

```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation/.agent/skills/note-thumbnail-generator && nohup python3 server.py --title "[選択されたタイトル]" --keywords "[キーワード1,キーワード2,キーワード3]" --genre "[ジャンル]" > /tmp/thumbnail_server.log 2>&1 &
```

**注意**:
- 角括弧の部分は実際の値に置き換えてください
- タイトルに特殊文字（`!`、`?`、`【】`など）が含まれる場合は、シングルクォートで囲んでください

サーバーが起動したら、ログを確認してngrok URLを取得：

```bash
sleep 5 && cat /tmp/thumbnail_server.log | grep -A1 "Canvaアプリに以下のURL"
```

サーバーが起動すると：
- ngrok公開URLがログに表示されます
- Canvaテンプレートが自動で開きます

---

## STEP 6: ユーザーへの案内

以下の手順をユーザーに案内してください：

1. Canvaテンプレートが自動で開きます
2. 左パネルから「アプリ」→「Note Thumbnail Generator」を起動
3. 表示されたngrok URLをアプリに入力
4. 「接続」をクリック
5. タイトルとキーワードが表示されたら、デザインに追加
6. 完成したらPNG形式でエクスポート

---

## 利用可能なジャンル

| ジャンル | トーン |
|---------|--------|
| 人生 | 共感的で温かみのある |
| 副業 | 実践的で具体的な |
| AI | 最新トレンドを押さえた専門的な |
| 有料 | 価値を強調する説得力のある |
| 雑記 | 親しみやすくカジュアルな |
| 資格 | 励ましと具体的アドバイスを含む |
| 本業 | プロフェッショナルで実践的な |

---

## STEP 7: 完了後のクリーンアップ

ユーザーがCanvaでの作業を完了したら、サーバーを停止します：

```bash
lsof -ti:5002 | xargs kill -9 2>/dev/null; pkill -f "python3 server.py" 2>/dev/null; echo "サーバーを停止しました"
```

---

## トラブルシューティング

### ポート5002が使用中の場合

```bash
lsof -ti:5002 | xargs kill -9
```

### ngrokが起動しない場合

ngrokがインストールされているか確認：
```bash
which ngrok
```

### サーバーのログを確認する場合

```bash
cat /tmp/thumbnail_server.log
```
