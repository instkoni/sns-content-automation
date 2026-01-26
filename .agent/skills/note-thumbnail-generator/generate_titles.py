#!/usr/bin/env python3
"""
Note記事タイトル生成スクリプト（記事ファイル選択版）
Gemini 3 Proを使用してAIO/SEO対策済みのタイトルを3案生成します
"""

import google.generativeai as genai
import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("エラー: google-generativeaiパッケージがインストールされていません")
    print("以下のコマンドでインストールしてください:")
    print("pip install google-generativeai")
    sys.exit(1)


from select_article import select_article, read_article_content

# 設定ファイルのパス
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR / "config"
GENRES_FILE = CONFIG_DIR / "genres.json"
PROMPTS_FILE = CONFIG_DIR / "prompts.json"


def load_config():
    """設定ファイルを読み込む"""
    try:
        with open(GENRES_FILE, "r", encoding="utf-8") as f:
            genres = json.load(f)
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            prompts = json.load(f)
        return genres, prompts
    except FileNotFoundError as e:
        print(f"エラー: 設定ファイルが見つかりません - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"エラー: 設定ファイルの形式が正しくありません - {e}")
        sys.exit(1)


def generate_titles(article_content, genre_name, genres, prompts):
    """Gemini 3 Proを使用してタイトルを生成"""
    # ジャンル情報を取得
    genre_info = genres.get(genre_name)
    if not genre_info:
        print(f"エラー: ジャンル '{genre_name}' が見つかりません")
        print(f"利用可能なジャンル: {', '.join(genres.keys())}")
        sys.exit(1)
    
    # プロンプトを構築
    system_prompt = prompts["system_prompt"]
    user_prompt_template = prompts["user_prompt_template"]
    
    # 記事内容の要約（最初の1000文字程度）
    article_summary = article_content[:1000] if len(article_content) > 1000 else article_content
    
    user_prompt = user_prompt_template.format(
        topic=article_summary,
        genre=genre_info["name"],
        tone=genre_info["tone"],
        target_audience=genre_info["target_audience"],
        keywords_hint=genre_info["keywords_hint"]
    )
    
    # Gemini 3 Proを初期化（APIキー不要）
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        print("\nタイトルを生成中...")
        print(f"ジャンル: {genre_info['name']}")
        print(f"トーン: {genre_info['tone']}")
        print(f"ターゲット: {genre_info['target_audience']}")
        print("-" * 60)
        
        # タイトルを生成
        response = model.generate_content([
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["承知しました。記事ネタからAIO/SEO対策済みのタイトルを3案生成します。"]},
            {"role": "user", "parts": [user_prompt]}
        ])
        
        return response.text
    
    except Exception as e:
        print(f"エラー: タイトル生成に失敗しました - {e}")
        sys.exit(1)


def parse_generated_output(output_text):
    """生成された出力からタイトルとキーワードを抽出"""
    lines = output_text.strip().split("\n")
    titles = []
    keywords = ""
    
    for line in lines:
        line = line.strip()
        # タイトル行を抽出（数字で始まる行）
        if line and (line[0].isdigit() or line.startswith("**")):
            # マークダウンの太字を除去
            clean_line = line.replace("**", "").strip()
            # 番号とピリオドを除去
            if ". " in clean_line:
                title = clean_line.split(". ", 1)[1].strip()
                titles.append(title)
        # キーワード行を抽出
        elif "キーワード" in line or "keywords" in line.lower():
            if ":" in line:
                keywords = line.split(":", 1)[1].strip()
    
    return titles, keywords


def main():
    parser = argparse.ArgumentParser(description="Note記事タイトル生成（記事ファイル選択版）")
    parser.add_argument("--genre", required=True, help="ジャンル（人生、副業、AI、有料、雑記、資格、本業）")
    parser.add_argument("--article-path", help="記事ファイルのパス（指定がある場合は対話モードをスキップ）")
    
    args = parser.parse_args()
    
    # 設定を読み込む
    genres, prompts = load_config()
    
    # 記事を選択
    if args.article_path:
        article_file = Path(args.article_path)
        if not article_file.exists():
            print(f"エラー: 指定された記事ファイルが見つかりません: {article_file}")
            sys.exit(1)
        # selected_folderはこの後の処理で使われないためNoneでOK
        selected_folder = None
    else:
        selected_folder, article_file = select_article()
    
    print(f"\n選択された記事: {article_file}")
    print("記事を読み込み中...")
    
    # 記事内容を読み込む
    article_content = read_article_content(article_file)
    if not article_content:
        sys.exit(1)
    
    print(f"✓ 記事を読み込みました（{len(article_content)}文字）")
    
    # タイトルを生成
    output = generate_titles(article_content, args.genre, genres, prompts)
    
    # 結果を解析
    titles, keywords = parse_generated_output(output)
    
    # 結果を表示
    print("\n" + "=" * 60)
    print("生成されたタイトル:")
    print("=" * 60)
    
    if titles:
        for i, title in enumerate(titles, 1):
            print(f"{i}. {title}")
    else:
        # タイトルが抽出できなかった場合は生の出力を表示
        print(output)
    
    if keywords:
        print("\n" + "=" * 60)
        print(f"キーワード: {keywords}")
        print("=" * 60)
    
    print("\n次のステップ:")
    print("1. 上記のタイトルから1つを選択してください")
    print("2. 以下のコマンドでローカルサーバーを起動してください:")
    print(f'\npython3 server.py \\')
    print(f'  --title "選択したタイトル" \\')
    print(f'  --keywords "{keywords}" \\')
    print(f'  --genre "{args.genre}"')


if __name__ == "__main__":
    main()
