#!/usr/bin/env python3
"""
Note Article Thumbnail Generator - Main Script
Antigravity Agent Skill
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


class NoteThumbnailGenerator:
    """Note記事サムネイル生成のメインクラス"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.template_dir = self.project_root / "templates"
        self.font_path = self.project_root / "fonts" / "NotoSansJP-Bold.ttf"
        self.config_path = self.project_root / ".agent" / "skills" / "note-thumbnail-generator" / "resources" / "template_config.json"
        
        # 設定ファイルを読み込み
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.template_config = json.load(f)
    
    def generate(self, genre, title, illustration_path, output_dir, number=None):
        """
        サムネイルを生成
        
        Args:
            genre (str): ジャンル名
            title (str): 選択されたタイトル
            illustration_path (str): 生成されたイラストのパス
            output_dir (str): 保存先ディレクトリ
            number (int, optional): 記事番号。指定しない場合は自動採番
        
        Returns:
            str: 保存されたファイルのパス
        """
        print(f"サムネイル生成開始...")
        print(f"ジャンル: {genre}")
        print(f"タイトル: {title}")
        
        # 設定を取得
        if genre not in self.template_config:
            raise ValueError(f"未対応のジャンル: {genre}")
        
        config = self.template_config[genre]
        
        # テンプレート画像のパスを取得
        template_path = self.template_dir / config["template_filename"]
        if not template_path.exists():
            raise FileNotFoundError(f"テンプレート画像が見つかりません: {template_path}")
            
        # 出力ディレクトリの準備と番号の決定
        save_dir = Path(output_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        if number is None:
            number = self._determine_next_number(save_dir)
        
        # 画像を合成
        print(f"画像を合成中... (番号: {number})")
        composed_image = self._compose_image(template_path, illustration_path, title, number, config)
        
        # ファイルを保存
        print("ファイルを保存中...")
        saved_filepath = self._save_image(composed_image, save_dir, number)
        
        print(f"✓ サムネイル生成完了: {saved_filepath}")
        return saved_filepath
    
    def _compose_image(self, template_path, illustration_path, title, number, config):
        """画像を合成"""
        # テンプレートを読み込み
        template = Image.open(template_path).convert("RGBA")
        
        # イラストを読み込み、リサイズ
        illustration = Image.open(illustration_path).convert("RGBA")
        illustration_size = (config["illustration_size"]["width"], 
                            config["illustration_size"]["height"])
        illustration = illustration.resize(illustration_size, Image.Resampling.LANCZOS)
        
        # イラストを配置
        illustration_pos = (config["illustration_position"]["x"], 
                           config["illustration_position"]["y"])
        template.paste(illustration, illustration_pos, illustration)
        
        # タイトルを描画
        self._draw_title(template, title, config)
        
        # 番号を描画
        self._draw_number(template, number, config)
        
        return template.convert("RGB")
    
    def _draw_title(self, image, title, config):
        """タイトルテキストを描画（強調色対応）"""
        draw = ImageDraw.Draw(image)
        
        # 色設定
        base_color = config.get("title_color", "#000000")
        highlight_color = config.get("highlight_color", "#D32F2F")
        
        # テキストを解析して色分け (char, color) のリストを作成
        colored_chars = self._parse_colored_text(title, base_color, highlight_color)
        
        # フォントサイズを自動調整
        font, lines = self._auto_adjust_font_colored(
            colored_chars,
            config["title_font_size"],
            config["title_max_width"],
            config["title_max_height"]
        )
        
        # テキストを描画
        y_offset = config["title_position"]["y"]
        line_height = font.size + 10
        start_x = config["title_position"]["x"]
        
        for line in lines:
            current_x = start_x
            for char_data in line:
                char = char_data['char']
                color = char_data['color']
                
                # 文字を描画
                draw.text(
                    (current_x, y_offset),
                    char,
                    font=font,
                    fill=color
                )
                
                # 次の文字位置へ移動（文字幅分進める）
                # 注意: getlengthは浮動小数点を返すことがあるためintにキャスト
                char_width = font.getlength(char)
                current_x += char_width
                
            y_offset += line_height

    def _parse_colored_text(self, text, base_color, highlight_color):
        """テキストを強調表示用の (char, color) リストに変換"""
        result = []
        is_highlight = False
        
        # `*` で囲まれた部分を強調色にする
        # 文字列を一文字ずつ処理
        for char in text:
            if char == "*":
                # フラグを反転させる（*自体は表示しない）
                is_highlight = not is_highlight
                continue
            
            color = highlight_color if is_highlight else base_color
            result.append({'char': char, 'color': color})
                
        return result

    def _draw_number(self, image, number, config):
        """記事番号を描画"""
        if "number_position" not in config:
            return

        draw = ImageDraw.Draw(image)
        
        # フォーマット適用 (例: "#{number}" -> "#1")
        fmt = config.get("number_format", "#{number}")
        text = fmt.format(number=number)
        
        font_size = config.get("number_font_size", 60)
        font = ImageFont.truetype(str(self.font_path), font_size)
        color = config.get("number_color", "#000000")
        
        draw.text(
            (config["number_position"]["x"], config["number_position"]["y"]),
            text,
            font=font,
            fill=color
        )
    
    def _auto_adjust_font_colored(self, colored_chars, initial_size, max_width, max_height):
        """テキストが領域に収まるようにフォントサイズを自動調整"""
        font_size = initial_size
        min_font_size = 20
        
        while font_size >= min_font_size:
            font = ImageFont.truetype(str(self.font_path), font_size)
            lines = self._wrap_colored_text(colored_chars, font, max_width)
            total_height = len(lines) * (font_size + 10)
            
            if total_height <= max_height:
                return font, lines
            
            font_size -= 2
        
        # 最小サイズでも収まらない場合
        font = ImageFont.truetype(str(self.font_path), min_font_size)
        lines = self._wrap_colored_text(colored_chars, font, max_width)
        return font, lines
    
    def _wrap_colored_text(self, colored_chars, font, max_width):
        """色付きテキストを最大幅に収まるように改行"""
        lines = []
        current_line = []
        current_width = 0
        
        for char_data in colored_chars:
            char = char_data['char']
            char_width = font.getlength(char)
            
            if current_width + char_width <= max_width:
                current_line.append(char_data)
                current_width += char_width
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [char_data]
                current_width = char_width
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _save_image(self, image, save_dir, number):
        """画像を指定パスに保存"""
        filename = self._generate_filename(number)
        filepath = save_dir / filename
        image.save(filepath, "PNG")
        return str(filepath)
    
    def _determine_next_number(self, save_dir):
        """次の番号を決定"""
        today = datetime.now().strftime("%Y%m%d")
        existing_files = list(save_dir.glob(f"{today}_Noteサムネイル*.png"))
        
        if not existing_files:
            return 1
            
        numbers = []
        for f in existing_files:
            try:
                num_str = f.stem.split("(")[1].split(")")[0]
                numbers.append(int(num_str))
            except (IndexError, ValueError):
                pass
        
        return max(numbers) + 1 if numbers else 1
    
    def _generate_filename(self, number):
        """年月日_Noteサムネイル(番号).png形式でファイル名を生成"""
        today = datetime.now().strftime("%Y%m%d")
        return f"{today}_Noteサムネイル({number}).png"


def main():
    """メイン関数（エージェントから呼び出される）"""
    parser = argparse.ArgumentParser(description="Note記事サムネイル生成")
    parser.add_argument("--genre", required=True, help="ジャンル名")
    parser.add_argument("--title", required=True, help="タイトル")
    parser.add_argument("--illustration-path", required=True, help="イラストのパス")
    parser.add_argument("--output-dir", default="/Volumes/WDBLACK_2TB/Git/sns-content-automation/articles/Notetitle", help="保存先ディレクトリ")
    parser.add_argument("--project-root", default=".", help="プロジェクトルート")
    parser.add_argument("--number", type=int, help="記事番号（指定しない場合は自動）")
    
    args = parser.parse_args()
    
    try:
        # プロジェクトルートを絶対パスに変換
        project_root_path = Path(args.project_root).resolve()
        generator = NoteThumbnailGenerator(project_root_path)
        saved_path = generator.generate(
            args.genre,
            args.title,
            args.illustration_path,
            args.output_dir,
            args.number
        )
        print(f"SUCCESS: {saved_path}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
