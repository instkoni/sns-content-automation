#!/usr/bin/env python3
"""
Note記事サムネイル生成用ローカルサーバー
FastAPI + ngrokでCanvaアプリにデータを提供します
"""

import argparse
import asyncio
import json
import os
import signal
import sys
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    from pyngrok import ngrok
except ImportError:
    print("エラー: 必要なパッケージがインストールされていません")
    print("以下のコマンドでインストールしてください:")
    print("pip install fastapi uvicorn pyngrok")
    sys.exit(1)


# グローバル変数
server_data = {}
ngrok_tunnel = None
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


@app.get("/data")
async def get_data():
    """タイトルとキーワードのデータを返す"""
    return server_data


@app.post("/shutdown")
async def shutdown():
    """サーバーを終了する"""
    print("\n終了信号を受信しました。サーバーを停止します...")
    shutdown_event.set()
    return {"status": "shutting down"}


def cleanup():
    """クリーンアップ処理"""
    global ngrok_tunnel
    print("クリーンアップ中...")
    if ngrok_tunnel:
        try:
            print("ngrokを停止中...")
            ngrok.disconnect(ngrok_tunnel.public_url)
            print("✓ ngrokを停止しました")
        except Exception as e:
            print(f"ngrok停止時のエラー: {e}")
    ngrok.kill()


def signal_handler(sig, frame):
    """Ctrl+Cのハンドラー"""
    print("\n\n割り込みを受信しました。終了します...")
    cleanup()
    sys.exit(0)


def start_server(title, keywords, genre, port=5002):
    """サーバーを起動する"""
    global server_data, ngrok_tunnel
    
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
    try:
        print(f"ngrokを起動中（ポート {port}）...")
        ngrok_tunnel = ngrok.connect(port, "http" )
        public_url = ngrok_tunnel.public_url
        print(f"✓ ngrokが起動しました: {public_url}")
    except Exception as e:
        print(f"エラー: ngrokの起動に失敗しました - {e}")
        print("\nngrokがインストールされていることを確認してください:")
        print("https://ngrok.com/download" )
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🚀 サーバーが起動しました！")
    print("=" * 60)
    print(f"公開URL: {public_url}")
    print(f"データエンドポイント: {public_url}/data")
    print(f"終了エンドポイント: {public_url}/shutdown")
    print("=" * 60)
    print("\nCanvaでの作業を開始してください。")
    print("1. Canvaでサムネイルのテンプレートを開いてください。")
    print("2. 左パネルから「Noteサムネイルアシスタント」アプリを起動してください。")
    print("3. アプリが自動的にタイトルとキーワードを取得します。")
    print("4. 記事番号を入力し、素材を選択して、レイアウトを実行してください。")
    print("\n作業が完了すると、サーバーは自動的に終了します。")
    print("=" * 60)
    
    # サーバーを起動
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="error"
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
