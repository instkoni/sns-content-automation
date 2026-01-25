---
name: nanobananapro-illustrator
description: Uses Nano Banana Pro (Gemini 3 Pro Image) to generate genre-specific, style-consistent illustrations for Note article thumbnails. Applies flat design, minimalist aesthetics, and genre-appropriate color palettes. The agent automatically decides when to use Nano Banana Pro.
---

# Nano Banana Pro Illustrator

Nano Banana Pro（Gemini 3 Pro Image）を使用して、タイトルに合わせたイラストを生成します。ジャンルごとのスタイルプリセットを適用し、デザインの一貫性を確保します。

## 重要な注意事項

Antigravityのエージェントは、**自動的にNano Banana Proを使用するタイミングを判断**します。このSkillは、エージェントがイラスト生成が必要と判断した際に、適切なプロンプトを構築するためのガイドラインを提供します。

## ジャンル別スタイルプリセット

スタイルプリセットは `resources/style_presets.json` に定義されています。

### 人生
- **スタイル**: warm and inspiring, life-coaching style
- **カラー**: pastel colors, soft tones
- **テーマ**: personal growth, happiness, mindfulness

### 副業
- **スタイル**: modern and professional, business-oriented
- **カラー**: clean design, blue and green tones
- **テーマ**: entrepreneurship, side hustle, financial growth

### AI
- **スタイル**: futuristic and tech-savvy, digital aesthetic
- **カラー**: vibrant colors, neon accents
- **テーマ**: technology, innovation, artificial intelligence

### 有料
- **スタイル**: premium and exclusive, high-quality feel
- **カラー**: elegant, gold and dark tones
- **テーマ**: luxury, exclusivity, premium content

### 雑記
- **スタイル**: casual and friendly, everyday life style
- **カラー**: soft tones, warm colors
- **テーマ**: daily life, random thoughts, personal stories

### 資格
- **スタイル**: academic and trustworthy, educational theme
- **カラー**: structured, blue and white
- **テーマ**: learning, certification, professional development

### 本業
- **スタイル**: corporate and serious, professional workplace
- **カラー**: formal, navy and gray
- **テーマ**: career, workplace, professional skills

## 共通デザイン要件

すべてのイラストは以下の要件を満たす必要があります。

- **フラットデザイン**: 立体感を排除したシンプルなデザイン
- **ミニマリスト**: 要素を最小限に抑えた洗練されたデザイン
- **テキスト禁止**: イラスト内にテキストや文字を含めない
- **正方形フォーマット**: 1024x1024px推奨
- **プロフェッショナル**: 清潔感があり、プロフェッショナルな印象

## プロンプトテンプレート

エージェントがNano Banana Proを呼び出す際、以下のテンプレートを使用してプロンプトを構築してください。

Create a {style} illustration for a blog article thumbnail about "{title}".

Genre: {genre}
Style: {genre_style_preset}

Design requirements:

•
Flat design

•
Minimalist aesthetic

•
{genre_color_palette}

•
No text or letters in the image

•
Professional and clean

•
Square format (1024x1024)

•
Suitable for {genre} genre content

Theme: {genre_theme}

The illustration should be simple, visually appealing, and directly relevant to the topic.

## 使用方法

エージェントは、選択されたタイトルとジャンルに基づいて、適切なスタイルプリセットを `resources/style_presets.json` から読み込み、Nano Banana Proにプロンプトを送信します。生成されたイラストは一時ファイルとして保存され、メインSkillに渡されます。

## エージェントによる自動判断

エージェントは、タスクの文脈から画像生成が必要と判断した場合、自動的にNano Banana Proを呼び出します。ユーザーが明示的に「イラストを生成して」と指示しなくても、エージェントが適切なタイミングで実行します。

## 出力

生成されたイラストのファイルパス（例: `/tmp/illustration_20260124_123456.png`）を返します。
