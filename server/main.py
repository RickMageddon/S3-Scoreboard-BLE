from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import HOST, PORT, LAUNCH_BROWSER, BROWSER_CMD, ENABLE_TEST_ENDPOINTS
from .ble_manager import ble_manager
from .events import event_bus

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="S3 Scoreboard BLE")
app.mount("/", StaticFiles(directory="static", html=True), name="static")


browser_process: Optional[subprocess.Popen] = None


@app.on_event("startup")
async def startup():
    global browser_process
    await ble_manager.start()
    if LAUNCH_BROWSER and browser_process is None:
        # Wacht heel even tot uvicorn luistert
        async def _delayed_launch():
            await asyncio.sleep(0.8)
            url = f"http://localhost:{PORT}"
            try:
                # Gebruik kiosk/fullscreen flags indien chromium; anders gewoon openen
                cmd = [BROWSER_CMD]
                lower_cmd = BROWSER_CMD.lower()
                if "chromium" in lower_cmd or "chrome" in lower_cmd:
                    cmd += ["--noerrdialogs", "--disable-session-crashed-bubble", "--disable-infobars", "--kiosk", url]
                elif "firefox" in lower_cmd:
                    cmd += ["--kiosk", url]
                else:
                    cmd.append(url)
                logging.info("Launching browser: %s", " ".join(cmd))
                # Start in aparte process group zodat we hem later kunnen killen
                browser_env = os.environ.copy()
                browser_env.setdefault("DISPLAY", ":0")  # typical RPi
                try:
                    browser_proc = subprocess.Popen(cmd, env=browser_env, preexec_fn=os.setsid)  # type: ignore[arg-type]
                except Exception:
                    # Fallback zonder setsid (bv. op Windows ontwikkeling)
                    browser_proc = subprocess.Popen(cmd, env=browser_env)
                globals()["browser_process"] = browser_proc
            except FileNotFoundError:
                logging.warning("Browser command niet gevonden: %s", BROWSER_CMD)
            except Exception as e:
                logging.warning("Kon browser niet starten: %s", e)

        asyncio.create_task(_delayed_launch())


@app.on_event("shutdown")
async def shutdown():
    global browser_process
    await ble_manager.stop()
    if browser_process and browser_process.poll() is None:
        try:
            logging.info("Terminating browser (pid=%s)", browser_process.pid)
            # Stuur SIGTERM naar process group indien mogelijk
            try:
                os.killpg(os.getpgid(browser_process.pid), signal.SIGTERM)  # type: ignore[arg-type]
            except Exception:
                browser_process.terminate()
            try:
                await asyncio.wait_for(asyncio.to_thread(browser_process.wait), timeout=3)
            except asyncio.TimeoutError:
                logging.info("Force killing browser")
                try:
                    os.killpg(os.getpgid(browser_process.pid), signal.SIGKILL)  # type: ignore[arg-type]
                except Exception:
                    browser_process.kill()
        except Exception:
            pass
    browser_process = None


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


# ---------------------- Test / Simulatie Endpoints ----------------------
if ENABLE_TEST_ENDPOINTS:
    from fastapi import Body
    import random, string

    @app.post("/api/test/add")
    async def test_add(
        name: str = Body("SimDevice"),
        game_name: str = Body("Test Game"),
        score: int = Body(0),
        id: str | None = Body(None),
    ):
        # Simuleer alsof BLE een nieuw device vond
        if not id:
            id = "TEST-" + "".join(random.choices(string.hexdigits[:16], k=12))
        from .ble_manager import deterministic_color
        from .models import DeviceState
        async with ble_manager._lock:  # type: ignore
            state = DeviceState(id=id, name=name, game_name=game_name, score=score, color=deterministic_color(id))
            ble_manager.devices[id] = state
        await event_bus.publish({"type": "device_added", "device": state.to_dict()})
        return {"ok": True, "device": state.to_dict()}

    @app.post("/api/test/score")
    async def test_score(id: str = Body(...), score: int = Body(...)):
        async with ble_manager._lock:  # type: ignore
            if id not in ble_manager.devices:
                return {"ok": False, "error": "unknown id"}
            ble_manager.devices[id].score = score
            payload = {"type": "device_updated", "device": ble_manager.devices[id].to_dict()}
        await event_bus.publish(payload)
        return {"ok": True}

    @app.post("/api/test/remove")
    async def test_remove(id: str = Body(...)):
        async with ble_manager._lock:  # type: ignore
            if id in ble_manager.devices:
                ble_manager.devices.pop(id)
        await event_bus.publish({"type": "device_removed", "id": id})
        return {"ok": True}


if __name__ == "__main__":
    run()
