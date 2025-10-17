from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import HOST, PORT, ENABLE_TEST_ENDPOINTS, ENABLE_ADVERTISING, ENABLE_GATT_SERVER, LOG_LEVEL
from .ble_manager import ble_manager
from .events import event_bus

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING), format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await ble_manager.start()
    if ENABLE_ADVERTISING:
        try:
            from .advertiser import ble_advertiser
            await ble_advertiser.start()
            if ENABLE_GATT_SERVER:
                # Start GATT server voor peripheral mode
                from .gatt_server import gatt_server
                await gatt_server.start()
        except Exception as e:
            logging.warning("Kon BLE advertiser/GATT server niet starten: %s", e)
    yield
    # Shutdown
    if ENABLE_ADVERTISING:
        try:
            from .advertiser import ble_advertiser
            await ble_advertiser.stop()
            if ENABLE_GATT_SERVER:
                from .gatt_server import gatt_server
                await gatt_server.stop()
        except Exception:
            pass
    await ble_manager.stop()


app = FastAPI(title="S3 Scoreboard BLE", lifespan=lifespan)
# Mount static assets op /static zodat WebSocket /ws niet door StaticFiles wordt gepakt
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root_index():
    return FileResponse("static/index.html")


@app.get("/api/devices")
async def list_devices():
    return {"devices": ble_manager.get_all()}


@app.get("/api/server/info")
async def server_info():
    """Get server information including MAC address and configured characteristics"""
    import subprocess
    import re
    from .config import SERVICE_UUID, RX_CHAR_UUID, TX_CHAR_UUID, ADVERTISING_NAME
    
    # Get Bluetooth MAC address
    mac_address = "Unknown"
    try:
        # Try to get MAC address from hci0 on Linux
        result = subprocess.run(['hciconfig', 'hci0'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            match = re.search(r'BD Address: ([0-9A-F:]{17})', result.stdout, re.IGNORECASE)
            if match:
                mac_address = match.group(1)
    except Exception as e:
        logger.debug("Could not get MAC address: %s", e)
        try:
            # Fallback: try reading from sysfs
            with open('/sys/class/bluetooth/hci0/address', 'r') as f:
                mac_address = f.read().strip()
        except Exception:
            pass
    
    return {
        "mac_address": mac_address,
        "device_name": ADVERTISING_NAME,
        "service_uuid": SERVICE_UUID,
        "characteristics": {
            "rx": {"uuid": RX_CHAR_UUID, "description": "Pi ontvangt data van ESP32 (game naam, score)"},
            "tx": {"uuid": TX_CHAR_UUID, "description": "Pi stuurt commando's naar ESP32"}
        }
    }


@app.post("/api/devices/{device_id}/send")
async def send_data_to_device(device_id: str, data: dict):
    """Send data to a specific ESP32 device via TX"""
    success = await ble_manager.send_tx_data(device_id, data)
    if success:
        return {"ok": True, "message": f"Data sent to {device_id}"}
    else:
        return {"ok": False, "error": f"Failed to send data to {device_id}"}


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
