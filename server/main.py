from __future__ import annotations

import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import HOST, PORT
from .ble_manager import ble_manager
from .events import event_bus

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="S3 Scoreboard BLE")
app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.on_event("startup")
async def startup():
    await ble_manager.start()


@app.on_event("shutdown")
async def shutdown():
    await ble_manager.stop()


@app.get("/api/devices")
async def list_devices():
    return {"devices": ble_manager.get_all()}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    queue = await event_bus.subscribe()
    # Stuur init state
    await ws.send_json({"type": "init", "devices": ble_manager.get_all()})
    try:
        while True:
            # race tussen inkomende events en client messages (we verwachten geen client msgs nu)
            done, pending = await asyncio.wait(
                [asyncio.create_task(queue.get()), asyncio.create_task(ws.receive_text())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                try:
                    data = task.result()
                except Exception:
                    continue
                if isinstance(data, str):
                    # Ignored client message
                    continue
                await ws.send_json(data)
            for task in pending:
                task.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        await event_bus.unsubscribe(queue)


def run():
    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    run()
