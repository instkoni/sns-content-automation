# Git自動同期のセットアップ手順（バックアップ機能付き）

このスクリプトは、Git同期の前に以下のフォルダを自動的にバックアップします。

## バックアップ対象

- `instkoni-automation`
- `scripts`
- `.agent/skills/note-article-generator`

バックアップ先: `/Volumes/WDBLACK_2TB/Program_backup/YYYYMMDD/`

---

## パート1: シェルスクリプトのセットアップ（5分）

### ステップ1: スクリプトを作成

以下のコマンドをターミナルにコピー＆ペーストして実行してください。

```bash
cat > ~/git-sync.sh << 'EOFSCRIPT'
#!/bin/bash

# Git自動同期スクリプト（バックアップ機能付き）

# ===== 設定 =====
REPO_PATH="/Volumes/WDBLACK_2TB/Git/sns-content-automation"
BACKUP_BASE="/Volumes/WDBLACK_2TB/Program_backup"

# バックアップ対象のフォルダ
BACKUP_TARGETS=(
    "instkoni-automation"
    "scripts"
    ".agent/skills/note-article-generator"
)

# ===== バックアップ処理 =====
backup_folders() {
    DATE_FOLDER=$(date '+%Y%m%d')
    BACKUP_DIR="$BACKUP_BASE/$DATE_FOLDER"
    
    echo "📁 バックアップ先: $BACKUP_DIR"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        echo "✓ バックアップフォルダを作成しました: $DATE_FOLDER"
    else
        echo "✓ バックアップフォルダは既に存在します: $DATE_FOLDER"
    fi
    
    for target in "${BACKUP_TARGETS[@]}"; do
        SOURCE="$REPO_PATH/$target"
        
        if [ -e "$SOURCE" ]; then
            echo "📦 バックアップ中: $target"
            
            SAFE_NAME=$(echo "$target" | tr '/' '_')
            DEST="$BACKUP_DIR/$SAFE_NAME"
            
            rsync -a --delete "$SOURCE/" "$DEST/"
            
            if [ $? -eq 0 ]; then
                echo "  ✅ 完了: $SAFE_NAME"
            else
                echo "  ⚠️  警告: $target のバックアップに失敗しました"
            fi
        else
            echo "  ⚠️  警告: $target が見つかりません（スキップ）"
        fi
    done
    
    echo ""
}

# ===== Git同期処理 =====
git_sync() {
    cd "$REPO_PATH" || exit 1
    
    BRANCH=$(git branch --show-current)
    
    if git diff-index --quiet HEAD --; then
        echo "✓ 変更がありません。アップロードの必要はありません。"
        return 0
    fi
    
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
        return 0
    else
        echo "❌ エラーが発生しました。"
        return 1
    fi
}

# ===== メイン処理 =====
echo "=========================================="
echo "  Git同期スクリプト（バックアップ付き）"
echo "=========================================="
echo ""

echo "【ステップ1】 ローカルバックアップを実行"
backup_folders

echo "【ステップ2】 GitHubに同期"
git_sync "$@"

echo ""
echo "=========================================="
echo "  処理が完了しました"
echo "=========================================="
EOFSCRIPT
```

### ステップ2: 実行権限を付与

```bash
chmod +x ~/git-sync.sh
```

### ステップ3: エイリアスを設定

```bash
echo 'alias gitsync="~/git-sync.sh"' >> ~/.zshrc
source ~/.zshrc
```

### ステップ4: テスト実行

```bash
gitsync
```

実行すると以下の処理が行われます:

1. **バックアップ**: 指定フォルダを `/Volumes/WDBLACK_2TB/Program_backup/YYYYMMDD/` にコピー
2. **Git同期**: 変更をGitHubにプッシュ

---

## パート2: 定期自動実行のセットアップ（5分）

### ステップ1: 自動実行設定ファイルを作成

```bash
cat > ~/Library/LaunchAgents/com.instkoni.gitsync.plist << 'EOFPLIST'
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
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOFPLIST
```

### ステップ2: 自動実行を有効化

```bash
launchctl load ~/Library/LaunchAgents/com.instkoni.gitsync.plist
```

### ステップ3: 設定を確認

```bash
launchctl list | grep gitsync
```

`com.instkoni.gitsync`が表示されればOKです。

---

## 使い方

### 手動でバックアップ＆同期

```bash
gitsync
```

実行すると:
1. 指定フォルダを `/Volumes/WDBLACK_2TB/Program_backup/20260121/` にバックアップ
2. GitHubに変更をプッシュ

### カスタムメッセージを付ける

```bash
gitsync "新しい記事を追加"
```

### 自動実行

**毎日22時**に自動的にバックアップ＆GitHubアップロードが実行されます。

---

## バックアップの仕組み

### バックアップ先の構造

```
/Volumes/WDBLACK_2TB/Program_backup/
├── 20260121/
│   ├── instkoni-automation/
│   ├── scripts/
│   └── .agent_skills_note-article-generator/
├── 20260122/
│   ├── instkoni-automation/
│   ├── scripts/
│   └── .agent_skills_note-article-generator/
...
```

- 毎日新しい日付フォルダが作成されます
- 同じ日に複数回実行しても、同じフォルダに上書きされます
- `rsync`を使用しているため、差分のみがコピーされ高速です

### バックアップ対象を変更したい場合

`~/git-sync.sh`を編集します。

```bash
nano ~/git-sync.sh
```

以下の部分を編集:

```bash
BACKUP_TARGETS=(
    "instkoni-automation"
    "scripts"
    ".agent/skills/note-article-generator"
    "追加したいフォルダ名"
)
```

保存: `Control + O` → `Enter` → `Control + X`

---

## 実行時間を変更したい場合

設定ファイルを編集:

```bash
nano ~/Library/LaunchAgents/com.instkoni.gitsync.plist
```

`<integer>22</integer>`の数字を変更（例: 18時なら18）

保存後、再読み込み:

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

最新の10行を表示:

```bash
tail -10 ~/git-sync.log
```

---

## トラブルシューティング

### バックアップが失敗する場合

1. バックアップ先のディスクがマウントされているか確認:
```bash
ls /Volumes/WDBLACK_2TB/Program_backup/
```

2. ディスクの空き容量を確認:
```bash
df -h /Volumes/WDBLACK_2TB/
```

### Git同期が失敗する場合

1. SSH接続を確認:
```bash
ssh -T git@github.com
```

2. リモートURLを確認:
```bash
cd /Volumes/WDBLACK_2TB/Git/sns-content-automation
git remote -v
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
