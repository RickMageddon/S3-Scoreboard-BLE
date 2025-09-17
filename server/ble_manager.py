from __future__ import annotations

import asyncio
import logging
import struct
from typing import Dict, Optional

from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

from .config import (
    SERVICE_UUID,
    GAME_NAME_CHAR_UUID,
    SCORE_CHAR_UUID,
    SCAN_INTERVAL,
    MAX_DEVICES,
    STRICT_SERVICE_UUID_FILTERING,
)
from .models import DeviceState
from .events import event_bus

logger = logging.getLogger(__name__)

COLOR_PALETTE = [
    "#FF6B6B",
    "#4ECDC4",
    "#1A535C",
    "#FF9F1C",
    "#2EC4B6",
    "#E71D36",
    "#6A4C93",
    "#1982C4",
    "#8AC926",
    "#FF595E",
    "#FFCA3A",
    "#6A994E",
    "#386641",
    "#8338EC",
    "#3A86FF",
    "#FB5607",
]


def deterministic_color(key: str) -> str:
    h = 0
    for c in key:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return COLOR_PALETTE[h % len(COLOR_PALETTE)]


class BLEManager:
    def __init__(self):
        self.devices: Dict[str, DeviceState] = {}
        self._clients: Dict[str, BleakClient] = {}
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._scan_loop(), name="ble-scan-loop")

    async def stop(self):
        self._running = False
        async with self._lock:
            for addr, client in list(self._clients.items()):
                try:
                    await client.disconnect()
                except Exception:
                    pass
            self._clients.clear()

    async def _scan_loop(self):
        logger.info("Starting BLE scan loop for service %s (strict filtering: %s)", SERVICE_UUID, STRICT_SERVICE_UUID_FILTERING)
        while self._running:
            try:
                found = await BleakScanner.discover()
                logger.debug("Found %d BLE devices during scan", len(found))
                tasks = []
                matched_devices = 0
                for d in found:
                    if len(self.devices) >= MAX_DEVICES:
                        logger.debug("Maximum device limit reached (%d)", MAX_DEVICES)
                        break
                    if await self._device_matches(d):
                        matched_devices += 1
                        addr = d.address
                        if addr not in self.devices and addr not in self._clients:
                            logger.info("Attempting to connect to matching device %s (%s)", d.name, addr)
                            tasks.append(asyncio.create_task(self._connect_device(d)))
                        else:
                            logger.debug("Device %s already known, skipping", addr)
                
                logger.debug("Matched %d devices, connecting to %d new devices", matched_devices, len(tasks))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.exception("Scan loop error: %s", e)
            await asyncio.sleep(SCAN_INTERVAL)

    async def _device_matches(self, d: BLEDevice) -> bool:
        # Filter: only allow devices that advertise the required service UUID when strict filtering is enabled
        # Check in advertisement data if available (platform dependent)
        uuids = d.details.get("props", {}).get("UUIDs") if hasattr(d.details, "get") else None  # type: ignore
        if uuids and SERVICE_UUID.lower() in [u.lower() for u in uuids]:
            logger.debug("Device %s (%s) matches service UUID in advertisement", d.name, d.address)
            return True
        
        # Check service data and manufacturer data for the service UUID
        if hasattr(d, 'metadata') and d.metadata:
            # Check service data
            service_data = d.metadata.get('service_data', {})
            if SERVICE_UUID.lower() in [uuid.lower() for uuid in service_data.keys()]:
                logger.debug("Device %s (%s) matches service UUID in service data", d.name, d.address)
                return True
                
            # Check service UUIDs list
            service_uuids = d.metadata.get('service_uuids', [])
            if SERVICE_UUID.lower() in [uuid.lower() for uuid in service_uuids]:
                logger.debug("Device %s (%s) matches service UUID in metadata", d.name, d.address)
                return True
        
        # If strict filtering is disabled, allow fallback to connecting and verifying later
        if not STRICT_SERVICE_UUID_FILTERING:
            logger.debug("Device %s (%s) allowed due to disabled strict filtering", d.name, d.address)
            return True
            
        # No fallback when strict filtering is enabled - only connect to devices that explicitly advertise our service UUID
        logger.debug("Device %s (%s) does not advertise required service UUID %s", d.name, d.address, SERVICE_UUID)
        return False

    async def _connect_device(self, d: BLEDevice):
        addr = d.address
        logger.info("Connecting to %s (%s)", d.name, addr)
        client = BleakClient(d)
        try:
            await client.connect(timeout=10.0)
            # Verify service (nieuwe manier: services property na fetch)
            await client.get_services()
            svcs = getattr(client, "services", [])
            if SERVICE_UUID.lower() not in [s.uuid.lower() for s in svcs]:
                logger.info("Device %s missing service UUID; disconnecting", addr)
                await client.disconnect()
                return

            game_name = "Unknown Game"
            try:
                if GAME_NAME_CHAR_UUID:
                    raw = await client.read_gatt_char(GAME_NAME_CHAR_UUID)
                    game_name = raw.decode(errors="ignore").strip() or game_name
            except Exception:
                pass

            device_name = d.name or addr
            state = DeviceState(
                id=addr,
                name=device_name,
                game_name=game_name,
                score=0,
                color=deterministic_color(addr),
            )
            async with self._lock:
                self.devices[addr] = state
                self._clients[addr] = client

            await event_bus.publish({"type": "device_added", "device": state.to_dict()})

            def handle_score(_, data: bytearray):  # notification callback
                score = self._parse_score(data)
                if score is not None:
                    asyncio.create_task(self._update_score(addr, score))

            try:
                await client.start_notify(SCORE_CHAR_UUID, handle_score)
            except Exception as e:
                logger.warning("Could not start score notifications for %s: %s", addr, e)

            # Set disconnection callback
            client.set_disconnected_callback(lambda _: asyncio.create_task(self._handle_disconnect(addr)))

        except Exception as e:
            logger.warning("Failed to connect %s: %s", addr, e)
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _update_score(self, addr: str, score: int):
        async with self._lock:
            if addr in self.devices:
                if self.devices[addr].score == score:
                    return
                self.devices[addr].score = score
                payload = {"type": "device_updated", "device": self.devices[addr].to_dict()}
        await event_bus.publish(payload)

    async def _handle_disconnect(self, addr: str):
        logger.info("Device disconnected: %s", addr)
        async with self._lock:
            self._clients.pop(addr, None)
            state = self.devices.pop(addr, None)
        if state:
            await event_bus.publish({"type": "device_removed", "id": addr})

    @staticmethod
    def _parse_score(data: bytearray) -> Optional[int]:
        if not data:
            return None
        # Try ascii int
        try:
            return int(data.decode().strip())
        except Exception:
            pass
        # Try 4-byte little endian
        try:
            if len(data) >= 4:
                return struct.unpack_from("<I", data, 0)[0]
        except Exception:
            pass
        return None

    def get_all(self):
        return [d.to_dict() for d in self.devices.values()]


ble_manager = BLEManager()
