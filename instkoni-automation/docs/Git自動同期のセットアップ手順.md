# Git自動同期のセットアップ手順

## パート1: シェルスクリプトのセットアップ（5分）

### ステップ1: スクリプトをホームディレクトリにコピー

以下のコマンドをターミナルで実行してください。

```bash
cat > ~/git-sync.sh << 'EOF'
#!/bin/bash

# Git自動同期スクリプト
# 使い方: gitsync [コミットメッセージ]

# リポジトリのパス
REPO_PATH="/Volumes/WDBLACK_2TB/Git/sns-content-automation"

# リポジトリに移動
cd "$REPO_PATH" || exit 1

# 現在のブランチを取得
BRANCH=$(git branch --show-current)

# 変更があるか確認
if git diff-index --quiet HEAD --; then
    echo "✓ 変更がありません。アップロードの必要はありません。"
    exit 0
fi

# コミットメッセージを設定（引数があればそれを使用、なければデフォルト）
if [ -n "$1" ]; then
    COMMIT_MSG="$*"
else
    COMMIT_MSG="Auto sync: $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo "📦 変更をステージングしています..."
git add .

echo "💾 コミットしています: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "🚀 GitHubにプッシュしています..."
git push origin "$BRANCH"

if [ $? -eq 0 ]; then
    echo "✅ GitHubへのアップロードが完了しました！"
else
    echo "❌ エラーが発生しました。"
    exit 1
fi
EOF
```

### ステップ2: スクリプトに実行権限を付与

```bash
chmod +x ~/git-sync.sh
```

### ステップ3: エイリアスを設定

使用しているシェルを確認します。

```bash
echo $SHELL
```

**zshの場合（最近のMacのデフォルト）:**

```bash
echo 'alias gitsync="~/git-sync.sh"' >> ~/.zshrc
source ~/.zshrc
```

**bashの場合:**

```bash
echo 'alias gitsync="~/git-sync.sh"' >> ~/.bash_profile
source ~/.bash_profile
```

### ステップ4: テスト実行

```bash
gitsync
```

成功すると「✅ GitHubへのアップロードが完了しました！」と表示されます。

---

## パート2: 定期自動実行のセットアップ（5分）

### ステップ1: launchd設定ファイルを作成

```bash
cat > ~/Library/LaunchAgents/com.instkoni.gitsync.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.instkoni.gitsync</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/instkoni/git-sync.sh</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>22</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/Users/instkoni/git-sync.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/instkoni/git-sync-error.log</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF
```

### ステップ2: 自動実行を有効化

```bash
launchctl load ~/Library/LaunchAgents/com.instkoni.gitsync.plist
```

### ステップ3: 設定を確認

```bash
launchctl list | grep gitsync
```

`com.instkoni.gitsync`が表示されれば成功です。

---

## 使い方

### 手動でアップロード

```bash
gitsync
```

または、カスタムメッセージを付けて:

```bash
gitsync "新しい記事を追加"
```

### 自動実行

毎日22時に自動的にGitHubにアップロードされます。

---

## 実行時間を変更したい場合

`~/Library/LaunchAgents/com.instkoni.gitsync.plist`を編集します。

例: 毎日18時に変更する場合

```xml
<key>Hour</key>
<integer>18</integer>
```

編集後、再読み込み:

```bash
launchctl unload ~/Library/LaunchAgents/com.instkoni.gitsync.plist
launchctl load ~/Library/LaunchAgents/com.instkoni.gitsync.plist
```

---

## ログを確認

実行履歴を確認:

```bash
cat ~/git-sync.log
```

エラーを確認:

```bash
cat ~/git-sync-error.log
```

---

## 自動実行を停止したい場合

```bash
launchctl unload ~/Library/LaunchAgents/com.instkoni.gitsync.plist
```

再開する場合:

```bash
launchctl load ~/Library/LaunchAgents/com.instkoni.gitsync.plist
```
