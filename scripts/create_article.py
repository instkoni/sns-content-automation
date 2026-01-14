#!/usr/bin/env python3
"""
新規記事を作成するスクリプト

使用方法:
    python3 create_article.py <記事ID>

指定された記事IDに基づいて、テンプレートから新規記事ファイルを作成します。
"""

import os
import sys
import shutil
from datetime import datetime

def get_repo_root():
    """リポジトリのルートディレクトリを取得"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def get_idea_info(ideas_file, article_id):
    """ideas-list.mdから記事情報を取得"""
    if not os.path.exists(ideas_file):
        return None
    
    with open(ideas_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 記事IDの行を探す
    import re
    pattern = rf'\| {article_id} \| ([^\|]+) \| ([^\|]+) \| ([^\|]+) \| ([^\|]+) \| ([^\|]+) \|'
    match = re.search(pattern, content)
    
    if match:
        return {
            'id': article_id,
            'date': match.group(1).strip(),
            'title': match.group(2).strip(),
            'category': match.group(3).strip(),
            'priority': match.group(4).strip(),
            'memo': match.group(5).strip()
        }
    
    return None

def create_article_from_template(template_file, output_file, article_info):
    """テンプレートから記事ファイルを作成"""
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # プレースホルダーを置換
    content = content.replace('[記事タイトル]', article_info['title'])
    content = content.replace('XXX', article_info['id'])
    content = content.replace('YYYY-MM-DD', datetime.now().strftime('%Y-%m-%d'))
    content = content.replace('[カテゴリ名]', article_info['category'])
    
    # ファイルに書き込み
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 記事ファイルを作成しました: {output_file}")

def create_research_file(template_file, output_file, article_info):
    """調査ファイルを作成"""
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # プレースホルダーを置換
    content = content.replace('[トピック名]', article_info['title'])
    content = content.replace('XXX', article_info['id'])
    content = content.replace('YYYY-MM-DD', datetime.now().strftime('%Y-%m-%d'))
    
    # ファイルに書き込み
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 調査ファイルを作成しました: {output_file}")

def update_ideas_status(ideas_file, article_id):
    """ideas-list.mdのステータスを更新"""
    with open(ideas_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 該当行を探して、新規アイデアから執筆中に移動
    import re
    pattern = rf'\| {article_id} \| ([^\|]+) \| ([^\|]+) \| ([^\|]+) \| ([^\|]+) \| ([^\|]+) \|'
    match = re.search(pattern, content)
    
    if match:
        old_line = match.group(0)
        # 該当行を削除
        content = content.replace(old_line + '\n', '')
        
        # 執筆中セクションに追加
        new_line = f"| {article_id} | {match.group(1).strip()} | {match.group(2).strip()} | {match.group(3).strip()} | articles/drafts/{datetime.now().strftime('%Y-%m-%d')}-{article_id}.md | 0% |"
        
        # 執筆中セクションを探す
        writing_section = "### ✍️ 執筆中"
        if writing_section in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if writing_section in line:
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
        
        # ファイルに書き込み
        with open(ideas_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ ideas-list.mdのステータスを更新しました")

def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 create_article.py <記事ID>")
        print("例: python3 create_article.py 001")
        sys.exit(1)
    
    article_id = sys.argv[1]
    
    print("=" * 60)
    print("📝 新規記事作成スクリプト")
    print("=" * 60)
    print(f"記事ID: {article_id}")
    print()
    
    repo_root = get_repo_root()
    ideas_file = os.path.join(repo_root, 'ideas', 'ideas-list.md')
    template_file = os.path.join(repo_root, 'templates', 'article-template.md')
    research_template_file = os.path.join(repo_root, 'templates', 'research-template.md')
    
    # 記事情報を取得
    article_info = get_idea_info(ideas_file, article_id)
    
    if not article_info:
        print(f"❌ エラー: 記事ID {article_id} が ideas-list.md に見つかりません")
        sys.exit(1)
    
    print(f"タイトル: {article_info['title']}")
    print(f"カテゴリ: {article_info['category']}")
    print()
    
    # ファイル名を生成
    date_str = datetime.now().strftime('%Y-%m-%d')
    article_filename = f"{date_str}-{article_id}.md"
    research_filename = f"research-{article_id}.md"
    
    article_file = os.path.join(repo_root, 'articles', 'drafts', article_filename)
    research_file = os.path.join(repo_root, 'research', 'topics', research_filename)
    
    # ファイルが既に存在するかチェック
    if os.path.exists(article_file):
        print(f"⚠️  警告: {article_file} は既に存在します")
        overwrite = input("上書きしますか? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("❌ キャンセルしました")
            sys.exit(0)
    
    # 記事ファイルを作成
    create_article_from_template(template_file, article_file, article_info)
    
    # 調査ファイルを作成
    create_research_file(research_template_file, research_file, article_info)
    
    # ステータスを更新
    update_ideas_status(ideas_file, article_id)
    
    print("\n" + "=" * 60)
    print("✅ 完了しました!")
    print("=" * 60)
    print(f"\n作成されたファイル:")
    print(f"1. 記事: {article_file}")
    print(f"2. 調査: {research_file}")
    print(f"\n次のステップ:")
    print(f"1. {research_file} で調査を実施")
    print(f"2. {article_file} で記事を執筆")
    print(f"3. git add . && git commit -m \"記事{article_id}: 執筆開始\" && git push")

if __name__ == "__main__":
    main()
