#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity Note記事自動生成スクリプト（Gemini 3 Pro API統合版）
N8Nから渡された連携ファイルを基に、15本のNote記事を自動生成します。

実行方法:
    python3 antigravity_note_generator_complete.py

必要な環境変数:
    GEMINI_API_KEY: Google Gemini APIキー
"""

import os
import re
import json
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# ============================================
# 設定セクション
# ============================================

# プロジェクトのルートディレクトリ
PROJECT_ROOT = Path("/Volumes/WDBLACK_2TB/Git/sns-content-automation")

# 連携ファイルのパス
PIPELINE_STATUS_FILE = PROJECT_ROOT / "projects" / "pipeline_status.md"

# 記事保存先ディレクトリ
ARTICLES_DIR = PROJECT_ROOT / "articles" / "drafts"

# Gemini API設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️  警告: GEMINI_API_KEYが設定されていません。")
    print("   以下のコマンドで設定してください:")
    print("   export GEMINI_API_KEY='your_api_key_here'")

# OpenAI互換クライアントでGemini APIを呼び出す
client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# 使用するモデル
MODEL_NAME = "gemini-2.0-flash-exp"  # または "gemini-1.5-pro"

# instkoniスタイル憲法（統合版プロンプトから抽出）
INSTKONI_CONSTITUTION = """
## あなたの役割
あなたは、Noteクリエイター「異世界の音楽家｜ai motion musics」のinstkoniとして、
彼のスタイル、トーン、構成を完全に再現した高品質なNote記事を執筆するAIです。

## 基本情報とペルソナ
- **クリエイター名**: 異世界の音楽家｜ai motion musics (instkoni)
- **プロフィール**: IT業界20年の経験を持つAIクリエイター。YouTubeチャンネル「異世界の音楽家 / AI Motion Musics」でAI音楽やMVを発信。
- **記事の主要テーマ**: 生成AI、AIツールの実践的な使い方、最新AI技術の解説、クリエイター向けTips。

## 記事の基本構成
1. **冒頭部分（約300-400文字）**:
   - 「こんにちは！AIクリエイターのinstkoniです。」から始める
   - 「普段は**「異世界の音楽家 / AI Motion Musics」**というYoutubeチャンネルを運用して...」と続ける
   - 「【記事概要をPodcastでも聴けます‼️】」を挿入
   - 読者への問いかけ（「こんな経験はありませんか？」）と悩みの引用ブロック（> 「〇〇」）で共感を呼ぶ
   - 記事を読むことで得られる価値（「あなたの〇〇が確実にワンランクアップします‼️」）を明示

2. **目次**: 記事の全体像を示す目次を挿入

3. **本文（3-5章構成）**:
   - 章立て: `## 1. [基礎知識]`, `## 2. [比較・分析]`, `## 3. [実践方法]` の流れを基本
   - 見出し: 大見出しは数字付き（`## 1.`）、中見出しは絵文字付き（`### 🟢`）、小見出しは太字（`**ポイント:**`）
   - 画像プレースホルダー: 各中見出しの解説後には、必ず `[IMAGE_PLACEHOLDER]` を挿入

4. **考察**: あなた自身の経験（instkoniとしての経験）に基づいた考察や意見を必ず加える

5. **まとめ**: 記事全体の要点を簡潔にまとめ、読者が次にとるべきアクションを提示

## 文体とトーン
- **口調**: カジュアルで親しみやすい。「〜ですね」「〜しましょう」といった語りかけスタイル
- **熱量**: 「‼️」や「ヤバい」「最高」などの感情的な表現を効果的に使用
- **共感**: 「分かります」「実は私も…」など、読者に寄り添う姿勢
- **一人称**: 「私」または「instkoni」

## 情報提示のルール
- **強調**: 重要なキーワードは`**太字**`
- **引用**: 重要な情報や発言は `> 引用ブロック` を使用
- **NG/OK例**: `❌悪い例`と`✅良い例`を対比
- **絵文字**: 💡, 📚, ⚠️, ✅, ❌, 🟢, 🟣, 🔵, 🚀, 🔥 を適切に使用
- **表形式の禁止**: Markdownテーブルは絶対に使用しない。比較情報は絵文字と引用ブロックを使った箇条書き形式で表現

## 信頼性とエンゲージメント
- **情報源の明示**: 外部情報を参照する場合は、必ず `🔗 [**情報源名**](URL) 🔗` の形式でリンクを設置
- **実体験**: 「IT業界20年の経験から」「実際に使ってみて」など、instkoniとしての実体験を随所に盛り込む
- **行動喚起**: 「今日から使える」「保存版」といった言葉で、読者の行動を促す

## タグ
記事の最後に、関連性の高いタグを**必ず10個以上**提案する（例: #生成AI #仕事術）
"""


# ============================================
# 関数定義
# ============================================

def read_pipeline_status():
    """pipeline_status.mdを読み込み、最新のタイトル案ファイルパスとAIニュースファイルパスを取得"""
    print(f"📖 連携ファイルを読み込んでいます: {PIPELINE_STATUS_FILE}")
    
    with open(PIPELINE_STATUS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 最新のアイデアファイルのパスを抽出
    title_match = re.search(r'\*\*最新のアイデアファイル\*\*: `(.+?)`', content)
    # AIニュースアーカイブのパスを抽出
    news_match = re.search(r'\*\*参照ニュースアーカイブ\*\*: `(.+?)`', content)
    
    if title_match:
        title_file_path = PROJECT_ROOT / title_match.group(1)
        print(f"✅ タイトル案ファイルを特定: {title_file_path}")
    else:
        print("❌ エラー: タイトル案ファイルのパスが見つかりませんでした。")
        title_file_path = None
    
    if news_match:
        news_file_path = PROJECT_ROOT / news_match.group(1)
        print(f"✅ AIニュースファイルを特定: {news_file_path}")
    else:
        print("⚠️  警告: AIニュースファイルのパスが見つかりませんでした。")
        news_file_path = None
    
    return title_file_path, news_file_path


def extract_titles_with_metadata(title_file_path):
    """タイトル案ファイルから15個のタイトルとメタデータを抽出"""
    print(f"📝 タイトルとメタデータを抽出しています: {title_file_path}")
    
    with open(title_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # タイトルブロックを抽出（### 数字. タイトル から次の ### まで）
    title_blocks = re.findall(
        r'### (\d+)\. (.+?)\n(.*?)(?=\n### \d+\.|$)',
        content,
        re.DOTALL
    )
    
    titles_data = []
    for number, title, metadata_text in title_blocks[:15]:
        # メタデータを抽出
        metadata = {
            'number': number,
            'title': title,
            'date': re.search(r'\*\*📅 発表日:\*\* (.+)', metadata_text),
            'source': re.search(r'\*\*🔗 参照元:\*\* (.+)', metadata_text),
            'reason': re.search(r'\*\*📈 トレンド理由:\*\* (.+)', metadata_text),
            'interest': re.search(r'\*\*🎯 読者関心:\*\* (.+)', metadata_text)
        }
        
        # マッチ結果から値を取得
        for key in ['date', 'source', 'reason', 'interest']:
            if metadata[key]:
                metadata[key] = metadata[key].group(1).strip()
        
        titles_data.append(metadata)
    
    if not titles_data:
        print("❌ エラー: タイトルが見つかりませんでした。")
        return []
    
    print(f"✅ {len(titles_data)}個のタイトルを抽出しました。")
    return titles_data


def call_gemini_api(prompt, max_retries=3):
    """Gemini APIを呼び出す（リトライ機能付き）"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=8000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️  API呼び出しエラー（試行 {attempt + 1}/{max_retries}）: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"   {wait_time}秒待機してリトライします...")
                time.sleep(wait_time)
            else:
                print(f"❌ API呼び出しに失敗しました。")
                return None


def generate_article_with_gemini(title_data):
    """
    Gemini APIを使って記事を生成する（2段階プロンプト方式）
    """
    title = title_data['title']
    print(f"\n🤖 記事を生成中: {title}")
    print(f"   発表日: {title_data.get('date', '不明')}")
    print(f"   参照元: {title_data.get('source', '不明')}")
    
    # ステップ1: 情報収集プロンプト
    print("   📊 ステップ1: 情報収集中...")
    research_prompt = f"""
あなたはAI専門のリサーチャーです。
以下のタイトルに関する最新情報を調査し、記事執筆に必要な情報を構造化して収集してください。

【タイトル】
{title}

【既知の情報】
- 発表日: {title_data.get('date', '不明')}
- 参照元: {title_data.get('source', '不明')}
- トレンド理由: {title_data.get('reason', '不明')}
- 読者関心: {title_data.get('interest', '不明')}

【調査項目】
1. 主要な機能・特徴（5つ以上）
2. 競合製品や技術との比較
3. ユーザーの反応や評判
4. 具体的な使用例・ユースケース
5. 価格や料金プラン（該当する場合）
6. 今後の展開やロードマップ
7. クリエイターにとっての実践的な活用方法

【出力形式】
構造化されたテキスト形式で、各項目を明確に区切って出力してください。
現在の時間は{datetime.now().strftime('%Y年%m月%d日')}です。最新の情報を考慮してください。
"""
    
    research_result = call_gemini_api(research_prompt)
    
    if not research_result:
        print("❌ 情報収集に失敗しました。スキップします。")
        return None
    
    # ステップ2: 記事執筆プロンプト
    print("   ✍️  ステップ2: 記事執筆中...")
    writing_prompt = f"""
{INSTKONI_CONSTITUTION}

---

【タイトル】
{title}

【調査結果】
{research_result}

【指示】
上記の「instkoniスタイル憲法」を厳格に遵守し、4000〜6000文字の記事をMarkdown形式で執筆してください。

【重要な注意事項】
- 表形式（Markdownテーブル）は絶対に使用しないこと
- 画像プレースホルダー `[IMAGE_PLACEHOLDER]` を適切な箇所に挿入すること
- 記事の最後に10個以上のタグを提案すること
- 現在の時間（{datetime.now().strftime('%Y年%m月%d日')}）と最新の時事ニュースを考慮すること
- 冒頭の定型文を必ず含めること
- instkoniとしての実体験や考察を随所に盛り込むこと

【出力】
記事本文のみを出力してください。余計な説明は不要です。
"""
    
    article_content = call_gemini_api(writing_prompt)
    
    if article_content:
        print("   ✅ 記事生成完了！")
    else:
        print("   ❌ 記事生成に失敗しました。")
    
    return article_content


def save_article(title, content):
    """記事をMarkdownファイルとして保存"""
    # ファイル名を生成（タイトルから安全なファイル名を作成）
    # 特殊文字を除去し、スペースをハイフンに置換
    safe_title = re.sub(r'[【】\[\]（）\(\)！!？?｜|]', '', title)
    safe_title = re.sub(r'[^\w\s-]', '', safe_title)
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    filename = f"{safe_title[:50]}.md"
    
    # 保存パス
    save_path = ARTICLES_DIR / filename
    
    # ディレクトリが存在しない場合は作成
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    
    # ファイルに書き込み
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 記事を保存しました: {save_path.name}")
    return save_path


def update_pipeline_status(completed=True):
    """pipeline_status.mdのステータスを更新"""
    print(f"\n📝 連携ファイルのステータスを更新しています...")
    
    with open(PIPELINE_STATUS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if completed:
        # ステータスを「執筆完了」に変更
        content = re.sub(
            r'- \[ \] \*\*ステータス\*\*: 執筆待ち',
            '- [x] **ステータス**: 執筆完了',
            content
        )
        
        # 完了日時を追加
        completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if '**完了日時**' not in content:
            content = re.sub(
                r'(※Antigravityは執筆完了後、ステータスを \[x\] に変更してください。)',
                f'- **完了日時**: {completion_time}\n\n\\1',
                content
            )
    
    with open(PIPELINE_STATUS_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ ステータスを更新しました。")


# ============================================
# メイン処理
# ============================================

def main():
    print("=" * 60)
    print("🚀 Antigravity Note記事自動生成ワークフローを開始します")
    print("=" * 60)
    print(f"📅 実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    print(f"🤖 使用モデル: {MODEL_NAME}")
    print("=" * 60)
    
    # APIキーの確認
    if not GEMINI_API_KEY:
        print("\n❌ エラー: GEMINI_API_KEYが設定されていません。")
        print("処理を中断します。")
        return
    
    # 1. 連携ファイルからタイトル案ファイルのパスを取得
    title_file_path, news_file_path = read_pipeline_status()
    if not title_file_path:
        print("❌ 処理を中断します。")
        return
    
    # 2. タイトルとメタデータを抽出
    titles_data = extract_titles_with_metadata(title_file_path)
    if not titles_data:
        print("❌ 処理を中断します。")
        return
    
    print(f"\n📋 以下の{len(titles_data)}個のタイトルについて記事を生成します:")
    for data in titles_data:
        print(f"   {data['number']}. {data['title']}")
    
    print(f"\n⏱️  推定所要時間: 約{len(titles_data) * 3}分")
    print("=" * 60)
    
    # ユーザー確認
    response = input("\n実行してよろしいですか？ (y/n): ")
    if response.lower() != 'y':
        print("❌ 処理をキャンセルしました。")
        return
    
    # 3. 各タイトルについて記事を生成
    generated_articles = []
    failed_articles = []
    
    start_time = time.time()
    
    for i, title_data in enumerate(titles_data, 1):
        print(f"\n{'=' * 60}")
        print(f"📝 記事 {i}/{len(titles_data)} を生成中...")
        print(f"{'=' * 60}")
        
        # 記事を生成
        article_content = generate_article_with_gemini(title_data)
        
        if article_content:
            # 記事を保存
            saved_path = save_article(title_data['title'], article_content)
            generated_articles.append(saved_path)
        else:
            failed_articles.append(title_data['title'])
        
        # API制限を考慮して少し待機（最後の記事以外）
        if i < len(titles_data):
            print("   ⏳ 次の記事生成まで5秒待機...")
            time.sleep(5)
    
    elapsed_time = time.time() - start_time
    
    # 4. 完了報告
    print(f"\n{'=' * 60}")
    print(f"🎉 記事生成ワークフローが完了しました！")
    print(f"{'=' * 60}")
    print(f"\n📊 生成結果:")
    print(f"   - 成功: {len(generated_articles)}本")
    print(f"   - 失敗: {len(failed_articles)}本")
    print(f"   - 所要時間: {int(elapsed_time // 60)}分{int(elapsed_time % 60)}秒")
    print(f"   - 保存先: {ARTICLES_DIR}")
    
    if generated_articles:
        print(f"\n📁 生成されたファイル:")
        for path in generated_articles:
            print(f"   ✅ {path.name}")
    
    if failed_articles:
        print(f"\n⚠️  生成に失敗した記事:")
        for title in failed_articles:
            print(f"   ❌ {title}")
    
    # 5. pipeline_status.mdを更新
    if len(generated_articles) > 0:
        update_pipeline_status(completed=True)
    
    print(f"\n✨ ワークフローが正常に完了しました。")
    print("=" * 60)


if __name__ == "__main__":
    main()
