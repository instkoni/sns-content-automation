#!/usr/bin/env python3
"""
記事ネタをideas-list.mdに追加するスクリプト

使用方法:
    python3 add_idea.py

対話形式で記事ネタの情報を入力し、ideas/ideas-list.mdに自動追加します。
"""

import os
import sys
from datetime import datetime

def get_repo_root():
    """リポジトリのルートディレクトリを取得"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def get_next_id(ideas_file):
    """次の記事IDを取得"""
    if not os.path.exists(ideas_file):
        return "001"
    
    with open(ideas_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 既存のIDを抽出
    import re
    ids = re.findall(r'\| (\d{3}) \|', content)
    
    if not ids:
        return "001"
    
    max_id = max([int(id) for id in ids])
    return f"{max_id + 1:03d}"

def add_idea_to_list(ideas_file, idea_data):
    """アイデアをリストに追加"""
    with open(ideas_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 新規アイデアセクションを探す
    new_idea_section = "### 🆕 新規アイデア"
    
    if new_idea_section not in content:
        print("❌ エラー: ideas-list.mdのフォーマットが正しくありません")
        sys.exit(1)
    
    # テーブルの最後の行を探す
    lines = content.split('\n')
    insert_index = -1
    
    for i, line in enumerate(lines):
        if new_idea_section in line:
            # テーブルヘッダーの次の行を探す
            for j in range(i, len(lines)):
                if lines[j].startswith('| ID |'):
                    # 次の空行またはセクションまでを探す
                    for k in range(j + 2, len(lines)):
                        if lines[k].strip() == '' or lines[k].startswith('###'):
                            insert_index = k
                            break
                    break
            break
    
    if insert_index == -1:
        print("❌ エラー: 挿入位置が見つかりませんでした")
        sys.exit(1)
    
    # 新しい行を挿入
    new_line = f"| {idea_data['id']} | {idea_data['date']} | {idea_data['title']} | {idea_data['category']} | {idea_data['priority']} | {idea_data['memo']} |"
    lines.insert(insert_index, new_line)
    
    # ファイルに書き込み
    with open(ideas_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ 記事ネタを追加しました: {idea_data['title']} (ID: {idea_data['id']})")

def main():
    print("=" * 60)
    print("📝 記事ネタ追加スクリプト")
    print("=" * 60)
    print()
    
    repo_root = get_repo_root()
    ideas_file = os.path.join(repo_root, 'ideas', 'ideas-list.md')
    
    if not os.path.exists(ideas_file):
        print(f"❌ エラー: {ideas_file} が見つかりません")
        sys.exit(1)
    
    # 次のIDを取得
    next_id = get_next_id(ideas_file)
    print(f"📌 記事ID: {next_id}")
    print()
    
    # ユーザー入力
    title = input("タイトル案: ").strip()
    if not title:
        print("❌ タイトルは必須です")
        sys.exit(1)
    
    print("\nカテゴリ選択:")
    print("1. テクノロジー")
    print("2. ビジネス")
    print("3. マーケティング")
    print("4. 副業")
    print("5. AI・自動化")
    print("6. その他")
    
    category_map = {
        "1": "テクノロジー",
        "2": "ビジネス",
        "3": "マーケティング",
        "4": "副業",
        "5": "AI・自動化",
        "6": "その他"
    }
    
    category_choice = input("カテゴリ番号 (1-6): ").strip()
    category = category_map.get(category_choice, "その他")
    
    print("\n優先度選択:")
    print("1. 高")
    print("2. 中")
    print("3. 低")
    
    priority_map = {
        "1": "高",
        "2": "中",
        "3": "低"
    }
    
    priority_choice = input("優先度番号 (1-3): ").strip()
    priority = priority_map.get(priority_choice, "中")
    
    memo = input("\nメモ (任意): ").strip()
    if not memo:
        memo = "-"
    
    # データをまとめる
    idea_data = {
        'id': next_id,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'title': title,
        'category': category,
        'priority': priority,
        'memo': memo
    }
    
    print("\n" + "=" * 60)
    print("📋 入力内容の確認")
    print("=" * 60)
    print(f"ID: {idea_data['id']}")
    print(f"日付: {idea_data['date']}")
    print(f"タイトル: {idea_data['title']}")
    print(f"カテゴリ: {idea_data['category']}")
    print(f"優先度: {idea_data['priority']}")
    print(f"メモ: {idea_data['memo']}")
    print("=" * 60)
    
    confirm = input("\nこの内容で追加しますか? (y/n): ").strip().lower()
    
    if confirm == 'y':
        add_idea_to_list(ideas_file, idea_data)
        print("\n✅ 完了しました!")
        print(f"\n次のステップ:")
        print(f"1. git add ideas/ideas-list.md")
        print(f"2. git commit -m \"記事ネタ追加: {idea_data['title']} (ID: {idea_data['id']})\"")
        print(f"3. git push origin main")
    else:
        print("\n❌ キャンセルしました")

if __name__ == "__main__":
    main()
