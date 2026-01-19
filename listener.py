import os
import time
import subprocess
from flask import Flask

app = Flask(__name__)

# --- 設定項目 ---
REPO_PATH = "/Volumes/WDBLACK_2TB/Git/sns-content-automation"
TARGET_FILE = "pipeline_status.md"
APP_NAME = "Antigravity"
BRANCH_NAME = "main" 

# --- 執筆憲法（マスタープロンプト） ---
MASTER_PROMPT = """
# @agent: 以下の「執筆憲法」に従い、直ちに任務を開始してください。

【あなたの役割】
あなたは「instkoni」の魂を継承したプロのnoteライターです。
単なるAIのまとめではなく、読者の心に刺さる体験談と鋭い考察を交えた4,000文字以上の大作を執筆してください。

【実行プロセス】
1. pipeline_status.md を読み取り、[ ] 執筆待ち であることを確認する。
2. 記載されている「最新アイデアファイル」と「参照ニュースアーカイブ」の内容を完全に把握する。
3. 「ユーザー（instkoni）のnote記事スタイル分析.md」を読み、トーンを完全に同期する。

【執筆の掟】
- 文字数: 4,000文字以上（必須）
- 構成: 導入、目次、詳細解説（3〜5章）、本音の考察、まとめ
- 挿入: 適切な位置に [IMAGE_PLACEHOLDER: 〇〇のシーンの画像] を挿入
- トーン: カジュアル、親しみやすい、実体験ベース、鋭い本音。

【完了後の処理】
# @agent: 以下の「執筆憲法」に従い、直ちに任務を開始してください。

【あなたの役割】
あなたは「instkoni」の魂を継承したプロのnoteライターです。
単なるAIのまとめではなく、読者の心に刺さる体験談と鋭い考察を交えた4,000文字以上の大作を執筆してください。

【実行プロセス】
1. pipeline_status.md を読み取り、[ ] 執筆待ち であることを確認する。
2. 記載されている「最新アイデアファイル」と「参照ニュースアーカイブ」の内容を完全に把握する。
3. 「ユーザー（instkoni）のnote記事スタイル分析.md」を読み、トーンを完全に同期する。

【執筆の掟】
- 文字数: 4,000文字以上（必須）
- 構成: 導入、目次、詳細解説（3〜5章）、本音の考察、まとめ
- 挿入: 適切な位置に [IMAGE_PLACEHOLDER: 〇〇のシーンの画像] を挿入
- トーン: カジュアル、親しみやすい、実体験ベース、鋭い本音。

【完了後の処理】
1. 成果物を /articles/drafts/ 内に保存。
2. pipeline_status.md のステータスを [x] に変更。
3. git add . / git commit -m "feat: 新規記事執筆完了" / git push を実行。

準備ができたら、思考（Planning）を開始し、記事を書き上げてください。


1. 成果物を /articles/drafts/ 内に保存。
2. pipeline_status.md のステータスを [x] に変更。
3. git add . / git commit -m "feat: 新規記事執筆完了" / git push を実行。

準備ができたら、思考（Planning）を開始し、記事を書き上げてください。
"""

def run_applescript_with_clipboard(prompt):
    """
    クリップボードを使用してプロンプトを確実にペーストし、実行する
    """
    # 1. プロンプトをMacのクリップボードにコピー (IME対策)
    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    process.communicate(prompt.encode('utf-8'))

    # 2. AppleScriptでAntigravityを操作
    script = f'''
    tell application "{APP_NAME}"
        activate
    end tell
    delay 4 -- アプリ起動待ち
    
    tell application "System Events"
        tell process "{APP_NAME}"
            -- エージェントパネルを開く (Cmd + L)
            keystroke "l" using {{command down}}
            delay 2 -- パネルが開くのを少し長めに待機
            
            -- クリップボードから貼り付け (Cmd + V)
            keystroke "v" using {{command down}}
            delay 1
            
            -- 実行 (Enter)
            keystroke return
        end tell
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=True)
        print(f"✅ {APP_NAME} エージェントに憲法を注入し、実行を開始しました")
    except Exception as e:
        print(f"❌ AppleScript実行エラー: {e}")

@app.route('/trigger-write', methods=['POST', 'GET'])
def trigger_write():
    print(f"🔔 {APP_NAME} 連携信号を受信")
    try:
        # 1. パスの存在確認
        if not os.path.exists(REPO_PATH):
            return f"❌ エラー: パスが見つかりません: {REPO_PATH}", 500
            
        os.chdir(REPO_PATH)
        
        # 2. GitHubから最新情報を強制同期 (Divergent branches エラー対策)
        print("🔄 GitHubから最新情報を取得中...")
        subprocess.run(["git", "fetch", "origin"], check=True)
        subprocess.run(["git", "reset", "--hard", f"origin/{BRANCH_NAME}"], check=True)
        print("✅ Git強制同期完了")
        
        # 3. Antigravityでファイルを開く
        subprocess.run(["open", "-a", APP_NAME, TARGET_FILE], check=True)
        print(f"🚀 {APP_NAME} で指示書を開きました")

        # 4. AppleScriptで自律動作を開始させる
        run_applescript_with_clipboard(MASTER_PROMPT)

        # 5. 通知
        subprocess.run(["osascript", "-e", 'display notification "Git同期とエージェントの始動に成功しました。" with title "n8n automation"'])
        
        return "Success: Agent Started with Forced Git Sync", 200

    except Exception as e:
        error_msg = f"❌ エラー詳細: {str(e)}"
        print(error_msg)
        return error_msg, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)