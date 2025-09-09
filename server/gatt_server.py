from __future__ import annotations

"""GATT Server voor peripheral mode: Pi adverteert en accepteert verbindingen van centrals (telefoons).

Gebruikt pydbus voor BlueZ D-Bus API om GATT service te registreren.
Wanneer een central (telefoon) verbindt en score schrijft, publish event naar WebSocket clients.

Vereist:
- BlueZ >= 5.50
- pydbus
- Root rechten voor sommige D-Bus calls (of sudo)

Beperkingen:
- Eén central tegelijk (simpel voorbeeld)
- Geen pairing/authenticatie
"""

import asyncio
import logging
from typing import Optional

try:
    import pydbus
except ImportError:
    pydbus = None

from .config import SERVICE_UUID, GAME_NAME_CHAR_UUID, SCORE_CHAR_UUID, ADVERTISING_NAME
from .events import event_bus
from .models import DeviceState
from .ble_manager import deterministic_color

logger = logging.getLogger(__name__)

# GATT Service en Characteristics definities
SCOREBOARD_SERVICE_XML = f"""
<node>
  <interface name="org.bluez.GattService1">
    <property name="UUID" type="s" value="{SERVICE_UUID}"/>
    <property name="Primary" type="b" value="true"/>
  </interface>
</node>
"""

GAME_NAME_CHAR_XML = f"""
<node>
  <interface name="org.bluez.GattCharacteristic1">
    <property name="UUID" type="s" value="{GAME_NAME_CHAR_UUID}"/>
    <property name="Service" type="o" value="/org/bluez/example/service0"/>
    <property name="Value" type="ay" value=""/>
    <property name="Flags" type="as">
      <item>read</item>
    </property>
  </interface>
</node>
"""

SCORE_CHAR_XML = f"""
<node>
  <interface name="org.bluez.GattCharacteristic1">
    <property name="UUID" type="s" value="{SCORE_CHAR_UUID}"/>
    <property name="Service" type="o" value="/org/bluez/example/service0"/>
    <property name="Value" type="ay" value=""/>
    <property name="Flags" type="as">
      <item>read</item>
      <item>write</item>
      <item>notify</item>
    </property>
  </interface>
</node>
"""


class GATTServer:
    def __init__(self):
        self.bus = None
        self.adapter = None
        self.service = None
        self.game_name_char = None
        self.score_char = None
        self.connected_device: Optional[str] = None
        self.game_name = "Scoreboard Game"
        self.score = 0

    async def start(self):
        if pydbus is None:
            logger.warning("pydbus niet geïnstalleerd; GATT server uitgeschakeld")
            return

        try:
            self.bus = pydbus.SystemBus()
            self.adapter = self.bus.get("org.bluez", "/org/bluez/hci0")

            # Set device name
            self.adapter.Alias = ADVERTISING_NAME
            self.adapter.Powered = True
            self.adapter.Discoverable = True
            self.adapter.Pairable = True

            # Register GATT service
            self.service = self.bus.register_object(
                "/org/bluez/example/service0",
                SCOREBOARD_SERVICE_XML,
                self._service_methods()
            )

            # Register characteristics
            self.game_name_char = self.bus.register_object(
                "/org/bluez/example/service0/char0",
                GAME_NAME_CHAR_XML,
                self._game_name_methods()
            )

            self.score_char = self.bus.register_object(
                "/org/bluez/example/service0/char1",
                SCORE_CHAR_XML,
                self._score_methods()
            )

            logger.info("GATT server gestart als '%s'", ADVERTISING_NAME)

            # Publish initial device
            device_state = DeviceState(
                id="PI-SELF",
                name=ADVERTISING_NAME,
                game_name=self.game_name,
                score=self.score,
                color=deterministic_color("PI-SELF")
            )
            await event_bus.publish({"type": "device_added", "device": device_state.to_dict()})

        except Exception as e:
            logger.warning("Kon GATT server niet starten: %s", e)

    async def stop(self):
        if self.connected_device:
            await event_bus.publish({"type": "device_removed", "id": "PI-SELF"})
        # Unregister objects
        if self.bus:
            try:
                self.bus.unregister_object(self.service)
                self.bus.unregister_object(self.game_name_char)
                self.bus.unregister_object(self.score_char)
            except Exception:
                pass
        self.bus = None

    def _service_methods(self):
        return {
            "ReadValue": self._read_value,
            "WriteValue": self._write_value,
            "StartNotify": self._start_notify,
            "StopNotify": self._stop_notify,
        }

    def _game_name_methods(self):
        return {
            "ReadValue": lambda: self.game_name.encode(),
        }

    def _score_methods(self):
        return {
            "ReadValue": lambda: str(self.score).encode(),
            "WriteValue": self._write_score,
            "StartNotify": lambda: None,
            "StopNotify": lambda: None,
        }

    def _read_value(self, options):
        # Generic read
        pass

    def _write_value(self, value, options):
        # Generic write
        pass

    def _write_score(self, value):
        try:
            new_score = int(value.decode().strip())
            if new_score != self.score:
                self.score = new_score
                # Publish update
                device_state = DeviceState(
                    id="PI-SELF",
                    name=ADVERTISING_NAME,
                    game_name=self.game_name,
                    score=self.score,
                    color=deterministic_color("PI-SELF")
                )
                asyncio.create_task(event_bus.publish({"type": "device_updated", "device": device_state.to_dict()}))
                logger.info("Score updated to %d", new_score)
        except Exception as e:
            logger.warning("Invalid score write: %s", e)

    def _start_notify(self):
        pass

    def _stop_notify(self):
        pass


gatt_server = GATTServer()
