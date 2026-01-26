#!/usr/bin/env python3
"""
Note記事選択スクリプト
記事フォルダから記事を選択し、内容を出力します
タイトル生成はAntigravityエージェントが担当します
"""

import argparse
import json
import sys
from pathlib import Path

# 記事フォルダのパス
ARTICLES_BASE_DIR = Path("/Volumes/WDBLACK_2TB/Git/sns-content-automation/articles/drafts2")


def list_contents():
    """記事フォルダとファイルの一覧を取得"""
    if not ARTICLES_BASE_DIR.exists():
        print(f"エラー: 記事フォルダが見つかりません - {ARTICLES_BASE_DIR}")
        sys.exit(1)
    
    items = []
    for item in ARTICLES_BASE_DIR.iterdir():
        if item.name.startswith('.'):
            continue
        if item.is_dir():
            items.append(item)
        elif item.is_file() and item.suffix in ['.md', '.txt']:
            items.append(item)
    
    items.sort(key=lambda x: x.name)
    return items


def find_article_file(folder):
    """フォルダ内の記事ファイルを探す（.md, .txt）"""
    for ext in [".md", ".txt"]:
        for file in folder.glob(f"*{ext}"):
            return file
    return None


def read_article_content(file_path):
    """記事ファイルの内容を読み込む"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"エラー: 記事ファイルの読み込みに失敗しました - {e}")
        return None


def select_article():
    """ユーザーに記事を選択させる"""
    items = list_contents()
    
    if not items:
        print(f"エラー: {ARTICLES_BASE_DIR} に記事フォルダまたはファイルが見つかりません")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("記事を選択してください:")
    print("=" * 60)
    
    for i, item in enumerate(items, 1):
        if item.is_dir():
            article_file = find_article_file(item)
            status = "✓" if article_file else "✗"
            print(f"{i:3d}. [Dir ] {status} {item.name}")
        else:
            print(f"{i:3d}. [File] ✓ {item.name}")
    
    print("=" * 60)
    
    while True:
        try:
            choice = input("\n番号を入力してください（0で終了）: ").strip()
            if choice == "0":
                print("終了します")
                sys.exit(0)
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(items):
                selected_item = items[choice_num - 1]
                
                if selected_item.is_dir():
                    article_file = find_article_file(selected_item)
                    
                    if not article_file:
                        print(f"エラー: {selected_item.name} に記事ファイル（.md, .txt）が見つかりません")
                        continue
                    
                    return selected_item, article_file
                else:
                    return None, selected_item
            else:
                print(f"エラー: 1〜{len(items)}の番号を入力してください")
        except ValueError:
            print("エラー: 数字を入力してください")
        except KeyboardInterrupt:
            print("\n\n終了します")
            sys.exit(0)


def list_articles_only():
    """記事一覧を表示するだけ（選択なし）"""
    items = list_contents()

    if not items:
        print(f"エラー: {ARTICLES_BASE_DIR} に記事フォルダまたはファイルが見つかりません")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("記事一覧:")
    print("=" * 60)

    articles_info = []
    for i, item in enumerate(items, 1):
        if item.is_dir():
            article_file = find_article_file(item)
            status = "✓" if article_file else "✗"
            print(f"{i:3d}. [Dir ] {status} {item.name}")
            folder_name = item.name
        else:
            article_file = item
            status = "✓"
            print(f"{i:3d}. [File] {status} {item.name}")
            folder_name = "(Root)"
            
        articles_info.append({
            "number": i,
            "folder_name": folder_name,
            "has_article": article_file is not None,
            "file_path": str(article_file) if article_file else None
        })

    print("=" * 60)
    print(f"\n合計: {len(items)} アイテム")
    return articles_info


def select_by_number(number):
    """番号で記事を選択"""
    items = list_contents()

    if not items:
        print(f"エラー: {ARTICLES_BASE_DIR} に記事フォルダまたはファイルが見つかりません")
        sys.exit(1)

    if number < 1 or number > len(items):
        print(f"エラー: 番号は1〜{len(items)}の範囲で指定してください")
        sys.exit(1)

    selected_item = items[number - 1]
    
    if selected_item.is_dir():
        article_file = find_article_file(selected_item)
        if not article_file:
            print(f"エラー: {selected_item.name} に記事ファイル（.md, .txt）が見つかりません")
            sys.exit(1)
        return selected_item, article_file
    else:
        return None, selected_item


def main():
    parser = argparse.ArgumentParser(description="Note記事選択スクリプト")
    parser.add_argument("--output-json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--list", action="store_true", help="記事一覧を表示するだけ（選択なし）")
    parser.add_argument("--number", "-n", type=int, help="記事番号を直接指定（インタラクティブ選択をスキップ）")

    args = parser.parse_args()

    # 一覧表示のみの場合
    if args.list:
        articles_info = list_articles_only()
        if args.output_json:
            print("\nJSON形式:")
            print(json.dumps(articles_info, ensure_ascii=False, indent=2))
        return

    # 番号指定の場合
    if args.number:
        selected_folder, article_file = select_by_number(args.number)
    else:
        # インタラクティブ選択
        selected_folder, article_file = select_article()
    
    print(f"\n選択された記事: {article_file}")
    print("記事を読み込み中...")
    
    # 記事内容を読み込む
    article_content = read_article_content(article_file)
    if not article_content:
        sys.exit(1)
    
    print(f"✓ 記事を読み込みました（{len(article_content)}文字）")
    
    # 結果を出力
    if args.output_json:
        # JSON形式で出力（エージェントが解析しやすい）
        result = {
            "folder_name": selected_folder.name if selected_folder else "(Root)",
            "file_path": str(article_file),
            "content": article_content,
            "content_length": len(article_content)
        }
        print("\n" + "=" * 60)
        print("JSON出力:")
        print("=" * 60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # テキスト形式で出力
        print("\n" + "=" * 60)
        print("記事内容:")
        print("=" * 60)
        print(article_content)
        print("\n" + "=" * 60)
        print(f"フォルダ名: {selected_folder.name if selected_folder else '(Root)'}")
        print(f"ファイルパス: {article_file}")
        print("=" * 60)


if __name__ == "__main__":
    main()
