#!/usr/bin/env python3
"""
記事を公開済みに移動するスクリプト

使用方法:
    python3 publish_article.py <記事ID> <Note URL>

記事をdraftsからpublishedに移動し、ideas-list.mdのステータスを更新します。
"""

import os
import sys
import shutil
from datetime import datetime

def get_repo_root():
    """リポジトリのルートディレクトリを取得"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def find_draft_file(drafts_dir, article_id):
    """下書きファイルを検索"""
    for filename in os.listdir(drafts_dir):
        if article_id in filename and filename.endswith('.md'):
            return os.path.join(drafts_dir, filename)
    return None

def move_to_published(draft_file, published_dir):
    """ファイルをpublishedに移動"""
    filename = os.path.basename(draft_file)
    published_file = os.path.join(published_dir, filename)
    
    shutil.move(draft_file, published_file)
    print(f"✅ ファイルを移動しました: {published_file}")
    
    return published_file

def update_article_metadata(article_file, note_url):
    """記事ファイルのメタ情報を更新"""
    with open(article_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # ステータスを更新
    content = content.replace('**ステータス**: 下書き / レビュー中 / 公開済み', '**ステータス**: 公開済み')
    
    # Note URLを追加
    content = content.replace('**URL**: ', f'**URL**: {note_url}')
    
    # 公開日を更新
    today = datetime.now().strftime('%Y-%m-%d')
    if '**公開日**: YYYY-MM-DD' in content:
        content = content.replace('**公開日**: YYYY-MM-DD', f'**公開日**: {today}')
    
    with open(article_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 記事メタ情報を更新しました")

def update_ideas_status_to_completed(ideas_file, article_id, article_info):
    """ideas-list.mdのステータスを完了に更新"""
    with open(ideas_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 執筆中セクションから該当行を削除
    import re
    pattern = rf'\| {article_id} \|[^\n]+\n'
    content = re.sub(pattern, '', content)
    
    # 完了セクションに追加
    today = datetime.now().strftime('%Y-%m-%d')
    new_line = f"| {article_id} | {article_info['date']} | {article_info['title']} | {article_info['category']} | {today} | {article_info['url']} |"
    
    completed_section = "### ✅ 完了"
    if completed_section in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if completed_section in line:
                # テーブルヘッダーの次の行を探す
                for j in range(i, len(lines)):
                    if lines[j].startswith('| ID |'):
                        # 次の空行またはセクションまでを探す
                        for k in range(j + 2, len(lines)):
                            if lines[k].strip() == '' or lines[k].startswith('###'):
                                lines.insert(k, new_line)
                                break
                        break
                break
        
        content = '\n'.join(lines)
    
    with open(ideas_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ ideas-list.mdのステータスを「完了」に更新しました")

def main():
    if len(sys.argv) < 3:
        print("使用方法: python3 publish_article.py <記事ID> <Note URL>")
        print("例: python3 publish_article.py 001 https://note.com/username/n/xxxxx")
        sys.exit(1)
    
    article_id = sys.argv[1]
    note_url = sys.argv[2]
    
    print("=" * 60)
    print("📢 記事公開スクリプト")
    print("=" * 60)
    print(f"記事ID: {article_id}")
    print(f"Note URL: {note_url}")
    print()
    
    repo_root = get_repo_root()
    drafts_dir = os.path.join(repo_root, 'articles', 'drafts')
    published_dir = os.path.join(repo_root, 'articles', 'published')
    ideas_file = os.path.join(repo_root, 'ideas', 'ideas-list.md')
    
    # 下書きファイルを検索
    draft_file = find_draft_file(drafts_dir, article_id)
    
    if not draft_file:
        print(f"❌ エラー: 記事ID {article_id} の下書きファイルが見つかりません")
        sys.exit(1)
    
    print(f"下書きファイル: {draft_file}")
    
    # 確認
    confirm = input("\nこの記事を公開済みに移動しますか? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ キャンセルしました")
        sys.exit(0)
    
    # ファイルを移動
    published_file = move_to_published(draft_file, published_dir)
    
    # メタ情報を更新
    update_article_metadata(published_file, note_url)
    
    # ideas-list.mdを更新
    # 記事情報を取得
    with open(ideas_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    pattern = rf'\| {article_id} \| ([^\|]+) \| ([^\|]+) \| ([^\|]+) \|'
    match = re.search(pattern, content)
    
    if match:
        article_info = {
            'date': match.group(1).strip(),
            'title': match.group(2).strip(),
            'category': match.group(3).strip(),
            'url': note_url
        }
        
        update_ideas_status_to_completed(ideas_file, article_id, article_info)
    
    print("\n" + "=" * 60)
    print("✅ 完了しました!")
    print("=" * 60)
    print(f"\n次のステップ:")
    print(f"1. LinkedIn向けリライトを作成")
    print(f"2. Xスレッドを作成")
    print(f"3. git add . && git commit -m \"記事{article_id}: Note公開完了\" && git push")

if __name__ == "__main__":
    main()
