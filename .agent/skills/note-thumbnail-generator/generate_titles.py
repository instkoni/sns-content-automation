#!/usr/bin/env python3
"""
Note記事のタイトル生成スクリプト
Gemini 3 Proを使用してAIO/SEO対策済みのタイトルを生成します
"""

import argparse
import json
import os
import sys

try:
    import google.generativeai as genai
except ImportError:
    print("エラー: google-generativeai パッケージがインストールされていません")
    print("以下のコマンドでインストールしてください:")
    print("pip install google-generativeai")
    sys.exit(1)


def load_config(config_dir="config"):
    """設定ファイルを読み込む"""
    genres_path = os.path.join(config_dir, "genres.json")
    prompts_path = os.path.join(config_dir, "prompts.json")
    
    with open(genres_path, "r", encoding="utf-8") as f:
        genres = json.load(f)
    
    with open(prompts_path, "r", encoding="utf-8") as f:
        prompts = json.load(f)
    
    return genres, prompts


def generate_titles(topic, genre, api_key=None):
    """タイトルを生成する"""
    # 設定ファイルを読み込む
    genres_config, prompts_config = load_config()
    
    # ジャンル情報を取得
    if genre not in genres_config["genres"]:
        print(f"エラー: ジャンル '{genre}' が見つかりません")
        print(f"利用可能なジャンル: {', '.join(genres_config['genres'].keys())}")
        sys.exit(1)
    
    genre_info = genres_config["genres"][genre]
    
    # Gemini APIの設定
    if api_key:
        genai.configure(api_key=api_key)
    elif os.getenv("GOOGLE_API_KEY"):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    else:
        print("警告: GOOGLE_API_KEY環境変数が設定されていません")
        print("Antigravity環境では自動的に設定されます")
    
    # プロンプトを構築
    system_prompt = prompts_config["title_generation"]["system_prompt"]
    user_prompt_template = prompts_config["title_generation"]["user_prompt_template"]
    
    user_prompt = user_prompt_template.format(
        topic=topic,
        genre_name=genre_info["name"],
        genre_description=genre_info["description"],
        genre_keywords=", ".join(genre_info["keywords"]),
        genre_tone=genre_info["tone"]
    )
    
    # Gemini 3 Proモデルを使用
    model = genai.GenerativeModel("gemini-pro")
    
    print(f"\n記事ネタ: {topic}")
    print(f"ジャンル: {genre}")
    print("タイトルを生成中...\n")
    
    try:
        response = model.generate_content(user_prompt)
        result_text = response.text
        
        # JSONを抽出
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            result_text = result_text[json_start:json_end].strip()
        
        result = json.loads(result_text)
        
        # 結果を表示
        print("生成されたタイトル:")
        for i, title in enumerate(result["titles"], 1):
            print(f"{i}. {title}")
        
        print(f"\nキーワード: {', '.join(result['keywords'])}")
        
        # 結果をファイルに保存
        output = {
            "topic": topic,
            "genre": genre,
            "titles": result["titles"],
            "keywords": result["keywords"]
        }
        
        with open("generated_titles.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print("\n結果を generated_titles.json に保存しました。")
        
        return result
        
    except Exception as e:
        print(f"エラー: タイトル生成に失敗しました - {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Note記事のタイトルを生成します")
    parser.add_argument("--topic", required=True, help="記事ネタ")
    parser.add_argument("--genre", required=True, help="ジャンル（人生、副業、AI、有料、雑記、資格、本業）")
    parser.add_argument("--api-key", help="Google API Key（省略可）")
    
    args = parser.parse_args()
    
    generate_titles(args.topic, args.genre, args.api_key)


if __name__ == "__main__":
    main()
