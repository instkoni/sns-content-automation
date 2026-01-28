#!/usr/bin/env python3
"""
Note記事サムネイル生成用ローカルサーバー
FastAPI + ngrokでCanvaアプリにデータを提供します
（ngrokコマンドを直接使用するバージョン）
"""

import argparse
import asyncio
import base64
import json
import os
import re
import signal
import subprocess
import sys
import time
import webbrowser
import requests
from contextlib import asynccontextmanager
from datetime import datetime

try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print("エラー: 必要なパッケージがインストールされていません")
    print("以下のコマンドでインストールしてください:")
    print("pip install fastapi uvicorn")
    sys.exit(1)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("警告: google-generativeai がインストールされていません。画像生成機能は無効です。")

from pathlib import Path

# 設定ファイルのパス
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR / "config"
GENRES_FILE = CONFIG_DIR / "genres.json"
TEMPLATE_ELEMENTS_FILE = CONFIG_DIR / "template_elements.json"

# 出力ディレクトリ（サムネイル保存先）
OUTPUT_DIR = SCRIPT_DIR.parent.parent.parent / "articles" / "Notetitle"


def copy_to_clipboard(text: str) -> bool:
    """テキストをクリップボードにコピー（macOS用）"""
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        return True
    except Exception as e:
        print(f"クリップボードへのコピーに失敗: {e}")
        return False

def load_genres():
    """ジャンル設定を読み込む"""
    try:
        if GENRES_FILE.exists():
            with open(GENRES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"ジャンル設定読み込みエラー: {e}")
        return {}


def load_template_elements():
    """テンプレート要素設定を読み込む"""
    try:
        if TEMPLATE_ELEMENTS_FILE.exists():
            with open(TEMPLATE_ELEMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"テンプレート要素設定読み込みエラー: {e}")
        return {}


# ジャンル設定をロード
genres_config = load_genres()
template_elements_config = load_template_elements()


# グローバル変数
server_data = {}
ngrok_process = None
shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時の処理
    yield
    # 終了時の処理
    cleanup()


app = FastAPI(lifespan=lifespan)

# CORSの設定（Canvaアプリからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """ルートでもデータを返す（Canvaアプリ用）"""
    print("📥 アクセス: / (ルート) - データを返します")
    print(f"   返すデータ: {server_data}")
    return server_data


@app.get("/data")
async def get_data():
    """タイトルとキーワードのデータを返す"""
    print("📥 アクセス: /data - データを返します")
    print(f"   返すデータ: {server_data}")
    print(f"   返すデータ: {server_data}")
    return server_data


@app.get("/api/get-genre-config")
async def get_genre_config():
    """ジャンル設定を返す"""
    print("📥 アクセス: /api/get-genre-config")
    return genres_config


@app.get("/api/get-template-elements")
async def get_template_elements():
    """テンプレート要素設定を返す"""
    print("📥 アクセス: /api/get-template-elements")
    return template_elements_config


@app.get("/api/get-latest-number")
async def get_latest_number():
    """出力ディレクトリをスキャンし次の番号を返す"""
    print("📥 アクセス: /api/get-latest-number")

    today = datetime.now().strftime("%Y%m%d")
    max_number = 0

    try:
        if OUTPUT_DIR.exists():
            # YYYYMMDD_Noteサムネイル(N).png パターンを検索
            pattern = re.compile(r"^\d{8}_Noteサムネイル\((\d+)\)\.png$")

            for file in OUTPUT_DIR.iterdir():
                if file.is_file():
                    match = pattern.match(file.name)
                    if match:
                        num = int(match.group(1))
                        if num > max_number:
                            max_number = num
    except Exception as e:
        print(f"ディレクトリスキャンエラー: {e}")

    next_number = max_number + 1
    suggested_filename = f"{today}_Noteサムネイル({next_number}).png"

    result = {
        "currentMax": max_number,
        "nextNumber": next_number,
        "suggestedFilename": suggested_filename
    }
    print(f"   結果: {result}")
    return result


@app.post("/api/generate-image")
async def generate_image(request: Request):
    """Gemini Imagenで画像を生成"""
    print("📥 アクセス: /api/generate-image")

    if not GENAI_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"error": "google-generativeai がインストールされていません"}
        )

    try:
        data = await request.json()
        prompt = data.get("prompt", "")

        if not prompt:
            return JSONResponse(
                status_code=400,
                content={"error": "プロンプトが指定されていません"}
            )

        print(f"   プロンプト: {prompt}")

        # Gemini API キーの確認
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return JSONResponse(
                status_code=500,
                content={"error": "GOOGLE_API_KEY または GEMINI_API_KEY が設定されていません"}
            )

        genai.configure(api_key=api_key)

        # Imagen 3 を使用して画像生成
        imagen_model = genai.ImageGenerationModel("imagen-3.0-generate-002")

        result = imagen_model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9",
            safety_filter_level="block_only_high",
            person_generation="allow_adult",
        )

        if result.images:
            # 画像をBase64エンコード
            image = result.images[0]
            image_bytes = image._pil_image.tobytes() if hasattr(image, '_pil_image') else None

            # PIL Imageから直接バイトを取得
            import io
            buffer = io.BytesIO()
            image._pil_image.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            print("   ✅ 画像生成成功")
            return {
                "success": True,
                "image": f"data:image/png;base64,{image_base64}"
            }
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "画像の生成に失敗しました"}
            )

    except Exception as e:
        print(f"   ❌ 画像生成エラー: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"画像生成エラー: {str(e)}"}
        )


@app.post("/shutdown")
async def shutdown():
    """サーバーを終了する"""
    print("\n終了信号を受信しました。サーバーを停止します...")
    shutdown_event.set()
    return {"status": "shutting down"}


def get_ngrok_public_url():
    """ngrokのローカルAPIから公開URLを取得"""
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels" )
        tunnels = response.json()["tunnels"]
        for tunnel in tunnels:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
        # httpsが見つからない場合はhttpを返す
        for tunnel in tunnels:
            if tunnel["proto"] == "http":
                return tunnel["public_url"]
        return None
    except Exception as e:
        print(f"ngrok URLの取得に失敗しました: {e}" )
        return None


def start_ngrok(port):
    """ngrokプロセスを起動"""
    global ngrok_process
    
    try:
        print(f"ngrokを起動中（ポート {port}）...")
        # ngrokコマンドを実行
        ngrok_process = subprocess.Popen(
            ["ngrok", "http", str(port )],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # ngrokが起動するまで待機
        time.sleep(3)
        
        # 公開URLを取得
        public_url = get_ngrok_public_url()

        if public_url:
            print(f"✓ ngrokが起動しました: {public_url}")
            # クリップボードにコピー
            if copy_to_clipboard(public_url):
                print(f"✅ URLがクリップボードにコピーされました: {public_url}")
            return public_url
        else:
            print("エラー: ngrokの公開URLを取得できませんでした")
            return None
            
    except FileNotFoundError:
        print("エラー: ngrokコマンドが見つかりません")
        print("\nngrokがインストールされていることを確認してください:")
        print("https://ngrok.com/download" )
        print("\nまたは、Homebrewでインストールできます:")
        print("brew install ngrok/ngrok/ngrok")
        return None
    except Exception as e:
        print(f"エラー: ngrokの起動に失敗しました - {e}")
        return None


def cleanup():
    """クリーンアップ処理"""
    global ngrok_process
    print("クリーンアップ中...")
    if ngrok_process:
        try:
            print("ngrokを停止中...")
            ngrok_process.terminate()
            ngrok_process.wait(timeout=5)
            print("✓ ngrokを停止しました")
        except Exception as e:
            print(f"ngrok停止時のエラー: {e}")
            try:
                ngrok_process.kill()
            except:
                pass


def signal_handler(sig, frame):
    """Ctrl+Cのハンドラー"""
    print("\n\n割り込みを受信しました。終了します...")
    cleanup()
    sys.exit(0)


def start_server(title, keywords, genre, port=5002):
    """サーバーを起動する"""
    global server_data
    
    # データを設定
    server_data = {
        "title": title,
        "keywords": keywords.split(",") if isinstance(keywords, str) else keywords,
        "genre": genre
    }
    
    print("=" * 60)
    print("Note Thumbnail Generator - ローカルサーバー")
    print("=" * 60)
    print(f"タイトル: {title}")
    print(f"キーワード: {', '.join(server_data['keywords'])}")
    print(f"ジャンル: {genre}")
    print("=" * 60)
    
    # シグナルハンドラーを設定
    signal.signal(signal.SIGINT, signal_handler)
    
    # ngrokを起動
    public_url = start_ngrok(port)
    
    if not public_url:
        print("\nngrokの起動に失敗しました。終了します。")
        sys.exit(1)

    # CanvaテンプレートURL
    canva_template_url = "https://www.canva.com/design/DAG_VDDB5a8/LY89bXNuNx8IAooDQXFQNg/edit"

    # 見やすい表示
    print("\n" + "=" * 70)
    print("✅ サーバーが起動しました！")
    print("=" * 70)
    print("=" * 70)
    print("\n🌐 Canvaアプリに以下のURLを入力してください:\n")
    print(f"    {public_url}")
    print(f"\n    (上記のURLをコピーして、Canvaアプリの「サーバーアドレス」欄に入力してください)")
    print("\n" + "=" * 70)
    print("\n📝 手順:")
    print("   1. Canvaテンプレートが自動で開きます")
    print("   2. 左パネルから「Note Thumbnail Generator」アプリを起動")
    print("   3. 「サーバーアドレス」欄に上記URLを入力")
    print("   4. 「接続」ボタンをクリック")
    print("=" * 70)
    print(f"\n📊 サーバー情報:")
    print(f"   データエンドポイント: {public_url}/data")
    print(f"   終了エンドポイント: {public_url}/shutdown")
    print("=" * 70)

    # Canvaテンプレートを自動で開く
    print("\n🎨 Canvaテンプレートを開いています...")
    try:
        webbrowser.open(canva_template_url)
        print("✓ Canvaテンプレートを開きました")
    except Exception as e:
        print(f"⚠️  ブラウザの起動に失敗しました: {e}")
        print(f"   手動で以下のURLを開いてください: {canva_template_url}")

    print("\n⏳ Canvaでの作業が完了すると、サーバーは自動的に終了します。")
    print("   (Ctrl+Cで手動終了も可能です)")
    print("=" * 70 + "\n")
    
    # サーバーを起動（ログレベルをinfoに設定してリクエストを確認）
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    async def serve():
        """サーバーを実行"""
        await server.serve()
    
    async def wait_for_shutdown():
        """終了イベントを待つ"""
        await shutdown_event.wait()
        await server.shutdown()
    
    async def run():
        """サーバーと終了待機を並行実行"""
        await asyncio.gather(
            serve(),
            wait_for_shutdown()
        )
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
        print("✓ サーバーが正常に終了しました")


def main():
    parser = argparse.ArgumentParser(description="Note記事サムネイル生成用ローカルサーバー")
    parser.add_argument("--title", required=True, help="記事タイトル")
    parser.add_argument("--keywords", required=True, help="キーワード（カンマ区切り）")
    parser.add_argument("--genre", required=True, help="ジャンル")
    parser.add_argument("--port", type=int, default=5002, help="ポート番号（デフォルト: 5002）")
    
    args = parser.parse_args()
    
    start_server(args.title, args.keywords, args.genre, args.port)


if __name__ == "__main__":
    main()
