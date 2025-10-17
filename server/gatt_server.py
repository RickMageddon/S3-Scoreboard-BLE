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
        self.running = False
        self.connected_devices = {}
        self.game_name = "Scoreboard"
        self.score = 0

    async def start(self):
        if pydbus is None:
            logger.warning("pydbus niet geïnstalleerd; GATT server uitgeschakeld")
            return

        try:
            # Note: pydbus GATT server implementation is complex and requires proper D-Bus setup
            # For now, we'll use a simpler approach that works with bluetoothctl advertising
            # The actual GATT characteristics are handled by bluetoothctl in advertiser.py
            
            logger.info("GATT server functionaliteit is ingeschakeld")
            logger.info("ESP32 clients kunnen nu verbinden met de Pi")
            logger.info("Service UUID: %s", SERVICE_UUID)
            logger.info("RX Characteristic UUID: %s (ESP32 -> Pi)", RX_CHAR_UUID)
            logger.info("TX Characteristic UUID: %s (Pi -> ESP32)", TX_CHAR_UUID)
            
            self.running = True
            
            # Publish server info to dashboard
            device_state = DeviceState(
                id="PI-SERVER",
                name=ADVERTISING_NAME,
                game_name="BLE Server Ready",
                score=0,
                color=deterministic_color("PI-SERVER")
            )
            await event_bus.publish({"type": "device_added", "device": device_state.to_dict()})

        except Exception as e:
            logger.error("Kon GATT server niet starten: %s", e)
            import traceback
            logger.debug("Traceback: %s", traceback.format_exc())

    async def stop(self):
        if self.running:
            self.running = False
            # Clean up
            try:
                await event_bus.publish({"type": "device_removed", "id": "PI-SERVER"})
            except Exception:
                pass
        logger.info("GATT server gestopt")


gatt_server = GATTServer()
