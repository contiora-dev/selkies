import asyncio
import json
import os
import webbrowser
from pathlib import Path

from aiohttp import web, WSMsgType
import websockets

PORT = 8080
WS_PORT = 8081
WEB_ROOT = Path(__file__).parent / "addons" / "selkies-web-core" / "dist"


async def ws_proxy(request):
    ws_server = web.WebSocketResponse()
    await ws_server.prepare(request)

    try:
        async with websockets.connect(f"ws://localhost:{WS_PORT}") as backend:
            async def to_backend():
                async for msg in ws_server:
                    if msg.type == WSMsgType.TEXT:
                        await backend.send(msg.data)
                    elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                        break

            async def to_client():
                async for msg in backend:
                    await ws_server.send_str(msg)

            await asyncio.gather(to_backend(), to_client())
    except Exception as e:
        print(f"WS proxy error: {e}")

    return ws_server


async def health(request):
    return web.json_response({"status": "ok"})


async def static_handler(request):
    rel_path = request.path.lstrip("/")
    file_path = WEB_ROOT / rel_path

    if file_path.is_file():
        return web.FileResponse(file_path)
    return web.FileResponse(WEB_ROOT / "index.html")


app = web.Application()
app.router.add_get("/health", health)
app.router.add_get("/websockets", ws_proxy)
app.router.add_get("/{path:.*}", static_handler)

if __name__ == "__main__":
    print(f"Serving {WEB_ROOT} on http://localhost:{PORT}")
    print(f"WS proxy /websockets -> ws://localhost:{WS_PORT}")
    webbrowser.open(f"http://localhost:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
