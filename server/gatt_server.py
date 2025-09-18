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

from .config import SERVICE_UUID, RX_CHAR_UUID, TX_CHAR_UUID, DATA_CHAR_UUID, GAME_NAME_CHAR_UUID, SCORE_CHAR_UUID, ADVERTISING_NAME, DISABLE_AUTHENTICATION
from .events import event_bus
from .models import DeviceState
from .ble_manager import deterministic_color

logger = logging.getLogger(__name__)

# GATT Service en RX/TX Characteristic definities
SCOREBOARD_SERVICE_XML = f"""
<node>
  <interface name="org.bluez.GattService1">
    <property name="UUID" type="s" value="{SERVICE_UUID}"/>
    <property name="Primary" type="b" value="true"/>
  </interface>
</node>
"""

# RX Characteristic: Pi ontvangt data van ESP32 (game naam, scores)
RX_CHAR_XML = f"""
<node>
  <interface name="org.bluez.GattCharacteristic1">
    <property name="UUID" type="s" value="{RX_CHAR_UUID}"/>
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

# TX Characteristic: Pi stuurt data naar ESP32 (commando's)
TX_CHAR_XML = f"""
<node>
  <interface name="org.bluez.GattCharacteristic1">
    <property name="UUID" type="s" value="{TX_CHAR_UUID}"/>
    <property name="Service" type="o" value="/org/bluez/example/service0"/>
    <property name="Value" type="ay" value=""/>
    <property name="Flags" type="as">
      <item>read</item>
      <item>write</item>
    </property>
  </interface>
</node>
"""

# Legacy characteristics (for backward compatibility)
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

            # Configure adapter for automatic, no-auth connections
            self.adapter.Alias = ADVERTISING_NAME
            self.adapter.Powered = True
            self.adapter.Discoverable = True
            
            if DISABLE_AUTHENTICATION:
                self.adapter.Pairable = False  # Disable pairing requirement
                
                # Disable authentication requirements for automatic connections
                try:
                    # Set adapter to not require authentication
                    self.adapter.Set("org.bluez.Adapter1", "PairableTimeout", 0)
                    logger.info("Disabled pairing timeout for automatic connections")
                except Exception as e:
                    logger.debug("Could not disable pairing timeout: %s", e)
            else:
                self.adapter.Pairable = True

            # Register GATT service
            self.service = self.bus.register_object(
                "/org/bluez/example/service0",
                SCOREBOARD_SERVICE_XML,
                self._service_methods()
            )

            # Register RX characteristic (ESP32 -> Pi)
            self.rx_char = self.bus.register_object(
                "/org/bluez/example/service0/char0",
                RX_CHAR_XML,
                self._rx_methods()
            )

            # Register TX characteristic (Pi -> ESP32)
            self.tx_char = self.bus.register_object(
                "/org/bluez/example/service0/char1",
                TX_CHAR_XML,
                self._tx_methods()
            )

            logger.info("GATT server gestart als '%s'%s", ADVERTISING_NAME, 
                       " (no-auth mode)" if DISABLE_AUTHENTICATION else "")

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
                self.bus.unregister_object(self.rx_char)
                self.bus.unregister_object(self.tx_char)
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

    def _rx_methods(self):
        """RX Characteristic: Pi ontvangt data van ESP32"""
        return {
            "ReadValue": lambda: self._get_current_state().encode(),
            "WriteValue": self._handle_rx_write,
            "StartNotify": lambda: None,
            "StopNotify": lambda: None,
        }

    def _tx_methods(self):
        """TX Characteristic: Pi stuurt data naar ESP32"""
        return {
            "ReadValue": lambda: "".encode(),  # Empty for TX
            "WriteValue": self._handle_tx_write,
        }

    def _get_current_state(self):
        """Get current game state as JSON for RX reads"""
        import json
        return json.dumps({
            "game_name": self.game_name,
            "score": self.score,
            "device": "PI-SELF"
        })

    def _handle_rx_write(self, value):
        """Handle data written to RX characteristic (from ESP32)"""
        try:
            import json
            data_str = value.decode('utf-8').strip()
            data = json.loads(data_str)
            
            updated = False
            if "game_name" in data and data["game_name"] != self.game_name:
                self.game_name = data["game_name"]
                updated = True
                
            if "score" in data and data["score"] != self.score:
                self.score = data["score"]
                updated = True
                
            if updated:
                # Publish update
                device_state = DeviceState(
                    id="PI-SELF",
                    name=ADVERTISING_NAME,
                    game_name=self.game_name,
                    score=self.score,
                    color=deterministic_color("PI-SELF")
                )
                asyncio.create_task(event_bus.publish({"type": "device_updated", "device": device_state.to_dict()}))
                logger.info("RX update: game='%s', score=%d", self.game_name, self.score)
                
        except Exception as e:
            logger.warning("Invalid RX data: %s", e)

    def _handle_tx_write(self, value):
        """Handle data written to TX characteristic (commands to ESP32)"""
        try:
            data_str = value.decode('utf-8').strip()
            logger.info("TX command received: %s", data_str)
            # Commands to ESP32 would be handled here
        except Exception as e:
            logger.warning("Invalid TX command: %s", e)

    def _read_value(self, options):
        # Generic read
        pass

    def _write_value(self, value, options):
        # Generic write
        pass

    def _start_notify(self):
        pass

    def _stop_notify(self):
        pass


gatt_server = GATTServer()
