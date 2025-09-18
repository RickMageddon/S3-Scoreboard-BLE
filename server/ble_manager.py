from __future__ import annotations

import asyncio
import logging
import struct
from typing import Dict, Optional

from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

from .config import (
    SERVICE_UUID,
    RX_CHAR_UUID,
    TX_CHAR_UUID,
    DATA_CHAR_UUID,     # Legacy support
    GAME_NAME_CHAR_UUID,  # Legacy support
    SCORE_CHAR_UUID,      # Legacy support
    SCAN_INTERVAL,
    MAX_DEVICES,
    STRICT_SERVICE_FILTER,
    ALLOWED_DEVICE_NAME_PATTERNS,
    DISABLE_AUTHENTICATION,
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
        # Use STRICT_SERVICE_UUID_FILTERING as the primary setting, fallback to STRICT_SERVICE_FILTER for compatibility
        strict_filtering = STRICT_SERVICE_UUID_FILTERING
        logger.info("Starting secure BLE scan loop for service %s (strict filtering: %s)", SERVICE_UUID, strict_filtering)
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self._running:
            try:
                # Use service UUID filter in scanner for more efficient discovery when strict filtering is enabled
                if strict_filtering:
                    found = await BleakScanner.discover(
                        timeout=10.0,
                        service_uuids=[SERVICE_UUID] if SERVICE_UUID else None
                    )
                else:
                    found = await BleakScanner.discover()
                    
                consecutive_errors = 0  # Reset error counter on successful scan
                logger.debug("Found %d BLE devices during scan", len(found))
                
                tasks = []
                matched_devices = 0
                for d in found:
                    if len(self.devices) >= MAX_DEVICES:
                        logger.warning("Maximum device limit (%d) reached", MAX_DEVICES)
                        break
                        
                    # Only process devices that pass our security filter
                    if await self._device_matches(d):
                        matched_devices += 1
                        addr = d.address
                        # Auto-connect to new devices or reconnect to known devices
                        if addr not in self.devices and addr not in self._clients:
                            logger.info("Auto-connecting to authorized device: %s (%s)", d.name or "Unknown", addr)
                            tasks.append(asyncio.create_task(self._connect_device(d)))
                        elif addr in self.devices and addr not in self._clients:
                            # Reconnect to previously known device
                            logger.info("Auto-reconnecting to known device: %s (%s)", d.name or "Unknown", addr)
                            tasks.append(asyncio.create_task(self._connect_device(d)))
                        else:
                            logger.debug("Device %s already known, skipping", addr)
                
                logger.debug("Matched %d devices, connecting to %d new devices", matched_devices, len(tasks))
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    # Log any connection failures
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.debug("Connection task failed: %s", result)
                            
            except Exception as e:
                consecutive_errors += 1
                logger.exception("Scan loop error (%d/%d): %s", consecutive_errors, max_consecutive_errors, e)
                
                # If too many consecutive errors, increase sleep time to avoid spam
                if consecutive_errors >= max_consecutive_errors:
                    logger.warning("Too many scan errors, increasing scan interval temporarily")
                    await asyncio.sleep(SCAN_INTERVAL * 3)
                    consecutive_errors = 0
                    continue
                    
            await asyncio.sleep(SCAN_INTERVAL)

    async def _device_matches(self, d: BLEDevice) -> bool:
        # Check both filtering settings for compatibility  
        strict_filtering = STRICT_SERVICE_UUID_FILTERING
        
        # Primary filter: devices that advertise our service UUID
        uuids = d.details.get("props", {}).get("UUIDs") if hasattr(d.details, "get") else None  # type: ignore
        if uuids and SERVICE_UUID.lower() in [u.lower() for u in uuids]:
            logger.debug("Device %s (%s) matches service UUID in advertisement", d.name, d.address)
            return True
        
        # Check service data and manufacturer data for the service UUID (more reliable on some platforms)
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
            
            # Check advertisement data
            adv_data = d.metadata.get('manufacturer_data', {}) or d.metadata.get('service_data', {})
            if any(SERVICE_UUID.lower() in str(v).lower() for v in adv_data.values()):
                logger.debug("Device %s (%s) matches service UUID in advertisement data", d.name, d.address)
                return True
        
        # If strict filtering is disabled, allow name-based matching for specific devices
        if not strict_filtering:
            device_name = (d.name or "").lower()
            if device_name and any(keyword.strip().lower() in device_name for keyword in ALLOWED_DEVICE_NAME_PATTERNS):
                logger.info("Attempting connection to name-matched device: %s", d.name)
                return True
            logger.debug("Device %s (%s) allowed due to disabled strict filtering", d.name, d.address)
            return True
            
        # SECURITY: No fallback when strict filtering is enabled - reject unknown devices
        logger.debug("Device %s (%s) does not advertise required service UUID %s", d.name or "Unknown", d.address, SERVICE_UUID)
        return False

    async def _connect_device(self, d: BLEDevice):
        addr = d.address
        logger.info("Attempting secure connection to %s (%s)", d.name, addr)
        client = BleakClient(d)
        try:
            # Auto-connect without user intervention
            await client.connect(timeout=15.0)
            
            # SECURITY: Verify service UUID before proceeding
            await client.get_services()
            svcs = getattr(client, "services", [])
            service_uuids = [s.uuid.lower() for s in svcs]
            
            if SERVICE_UUID.lower() not in service_uuids:
                logger.warning("SECURITY: Device %s (%s) connected but missing required service UUID %s. Services found: %s", 
                             d.name or "Unknown", addr, SERVICE_UUID, service_uuids)
                await client.disconnect()
                return

            logger.info("SECURITY: Device %s verified with correct service UUID %s", addr, SERVICE_UUID)

            # RX Setup: Read initial data from ESP32
            game_name = "Unknown Game"
            initial_score = 0
            
            try:
                # Read initial data from RX characteristic (ESP32 -> Pi)
                raw_data = await client.read_gatt_char(RX_CHAR_UUID)
                parsed_data = self._parse_rx_data(raw_data)
                if parsed_data:
                    game_name = parsed_data.get("game_name", game_name)
                    initial_score = parsed_data.get("score", initial_score)
                    logger.debug("Initial RX from %s: game='%s', score=%d", addr, game_name, initial_score)
            except Exception as e:
                logger.debug("Could not read initial RX data from %s: %s", addr, e)
                # Fallback: Try to read game name from TX characteristic (legacy)
                try:
                    raw = await client.read_gatt_char(TX_CHAR_UUID)
                    game_name = raw.decode(errors="ignore").strip() or game_name
                    logger.debug("Read game name from TX char (legacy): %s", game_name)
                except Exception as e2:
                    logger.debug("Legacy TX read failed for %s: %s", addr, e2)

            device_name = d.name or addr
            state = DeviceState(
                id=addr,
                name=device_name,
                game_name=game_name,
                score=initial_score,
                color=deterministic_color(addr),
            )
            async with self._lock:
                self.devices[addr] = state
                self._clients[addr] = client

            await event_bus.publish({"type": "device_added", "device": state.to_dict()})
            logger.info("Device %s (%s) successfully connected and added", device_name, addr)

            # RX Setup: Enable notifications for real-time data from ESP32
            def handle_rx_data(_, data: bytearray):  # RX callback from ESP32
                parsed_data = self._parse_rx_data(data)
                if parsed_data:
                    asyncio.create_task(self._handle_rx_data(addr, parsed_data))

            try:
                await client.start_notify(RX_CHAR_UUID, handle_rx_data)
                logger.debug("RX notifications enabled for %s on %s", addr, RX_CHAR_UUID)
            except Exception as e:
                logger.warning("Could not enable RX notifications for %s: %s", addr, e)
                # Fallback to legacy score characteristic
                try:
                    def handle_legacy_score(_, data: bytearray):
                        score = self._parse_score(data)
                        if score is not None:
                            asyncio.create_task(self._update_score(addr, score))
                    
                    await client.start_notify(SCORE_CHAR_UUID, handle_legacy_score)
                    logger.debug("Legacy score notifications enabled for %s", addr)
                except Exception as e2:
                    logger.warning("Could not enable legacy notifications for %s: %s", addr, e2)

            # Set disconnection callback for automatic cleanup
            client.set_disconnected_callback(lambda _: asyncio.create_task(self._handle_disconnect(addr)))

        except Exception as e:
            logger.warning("Failed to connect to %s (%s): %s", d.name or "Unknown", addr, e)
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _handle_rx_data(self, addr: str, data: Dict[str, any]):
        """Handle incoming data from ESP32 (RX from Pi perspective)"""
        async with self._lock:
            if addr not in self.devices:
                return
                
            device = self.devices[addr]
            updated = False
            
            # Update game name if provided
            if "game_name" in data and data["game_name"] != device.game_name:
                device.game_name = data["game_name"]
                updated = True
                logger.debug("RX game_name update from %s: %s", addr, data["game_name"])
            
            # Update score if provided
            if "score" in data and data["score"] != device.score:
                device.score = data["score"]
                updated = True
                logger.debug("RX score update from %s: %d", addr, data["score"])
            
            if updated:
                payload = {"type": "device_updated", "device": device.to_dict()}
                await event_bus.publish(payload)

    async def send_tx_data(self, addr: str, data: Dict[str, any]) -> bool:
        """Send data to ESP32 via TX characteristic (Pi -> ESP32)"""
        async with self._lock:
            if addr not in self._clients:
                logger.warning("Cannot TX to %s: device not connected", addr)
                return False
                
            client = self._clients[addr]
            
        try:
            # Encode data as JSON for transmission to ESP32
            import json
            json_data = json.dumps(data)
            await client.write_gatt_char(TX_CHAR_UUID, json_data.encode())
            logger.debug("TX to %s via %s: %s", addr, TX_CHAR_UUID, json_data)
            return True
        except Exception as e:
            logger.warning("Failed to TX data to %s: %s", addr, e)
            return False

    @staticmethod
    def _parse_rx_data(data: bytearray) -> Optional[Dict[str, any]]:
        """Parse incoming data from ESP32 via RX characteristic (ESP32 -> Pi)"""
        if not data:
            return None
            
        try:
            # Try JSON format first (recommended)
            import json
            json_str = data.decode('utf-8').strip()
            parsed = json.loads(json_str)
            logger.debug("Parsed JSON data: %s", parsed)
            return parsed
        except Exception:
            pass
            
        try:
            # Fallback: Try simple format "game_name:score" or just "score"
            text = data.decode('utf-8').strip()
            if ':' in text:
                parts = text.split(':', 1)
                return {
                    "game_name": parts[0].strip(),
                    "score": int(parts[1].strip())
                }
            else:
                # Just a score number
                return {"score": int(text)}
        except Exception:
            pass
            
        try:
            # Fallback: Binary score (4-byte little endian)
            if len(data) >= 4:
                import struct
                score = struct.unpack_from("<I", data, 0)[0]
                return {"score": score}
        except Exception:
            pass
            
        logger.debug("Could not parse RX data: %s", data)
        return None

    @staticmethod 
    def _parse_tx_data(data: bytearray) -> Optional[Dict[str, any]]:
        """Legacy method - redirects to _parse_rx_data for backward compatibility"""
        return BLEManager._parse_rx_data(data)

    async def _update_score(self, addr: str, score: int):
        """Legacy score update method"""
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
