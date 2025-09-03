from __future__ import annotations

"""Simple BLE advertising helper for Raspberry Pi using bluetoothctl.

This is a pragmatic approach: instead of implementing a full peripheral GATT
stack (which bleak currently doesn't support for Linux), we shell out to
`bluetoothctl` to create a custom advertisement with the scoreboard service
UUID. This is sufficient for discovery by phones or other centrals.

Limitaties:
 - Vereist BlueZ + bluetoothctl
 - Root of sudo rechten voor sommige acties (alias/advertise primary)
 - Simpele levensduur (start/stop); geen characteristics

Voor echte GATT server functionaliteit zou je kunnen kijken naar:
 - pydbus + BlueZ D-Bus API
 - aiobleserver (ESP32 / MicroPython scenario) (niet van toepassing hier)
 - Of een dedicated C/Go helper die peripheral mode afhandelt.
"""

import asyncio
import logging
import shutil
import subprocess
from typing import Optional

from .config import SERVICE_UUID, ADVERTISING_NAME

logger = logging.getLogger(__name__)


class BLEAdvertiser:
    def __init__(self):
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._running = False

    async def start(self):
        if self._running:
            return
        if not shutil.which("bluetoothctl"):
            logger.warning("bluetoothctl niet gevonden; advertising uitgeschakeld")
            return
        self._running = True
        asyncio.create_task(self._run(), name="ble-advertiser")

    async def stop(self):
        self._running = False
        # Stop advertisement cleanly
        try:
            await self._send_cmd("advertise off")
        except Exception:
            pass
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
            except Exception:
                pass
        self._proc = None

    async def _run(self):
        try:
            # Interactive bluetoothctl session
            self._proc = await asyncio.create_subprocess_exec(
                "bluetoothctl",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            await asyncio.sleep(0.2)
            # Set alias (Device Name)
            await self._send_cmd(f"system-alias {ADVERTISING_NAME}")
            # Maak (her) advertentie met service UUID
            await self._send_cmd("menu advertise")
            await self._send_cmd("clear")
            await self._send_cmd(f"uuid {SERVICE_UUID}")
            await self._send_cmd("back")
            await self._send_cmd("advertise on")
            logger.info("Advertising gestart als '%s' met service %s", ADVERTISING_NAME, SERVICE_UUID)

            # Houd proces in leven terwijl running
            while self._running and self._proc.returncode is None:
                await asyncio.sleep(2)
        except Exception as e:
            logger.warning("Advertiser fout: %s", e)
        finally:
            logger.info("Advertiser gestopt")

    async def _send_cmd(self, line: str):
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("bluetoothctl proces niet actief")
        logger.debug("[advertiser] > %s", line)
        self._proc.stdin.write((line + "\n").encode())
        await self._proc.stdin.drain()
        await asyncio.sleep(0.15)


ble_advertiser = BLEAdvertiser()
