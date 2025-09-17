from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

# Service UUID waar de Pi naar zoekt om te beslissen of hij moet verbinden.
SERVICE_UUID = os.getenv("SCOREBOARD_SERVICE_UUID", "c9b9a344-a062-4e55-a507-441c7e610e2c")

# Characteristic UUIDs voor game name en score.
GAME_NAME_CHAR_UUID = os.getenv("GAME_NAME_CHAR_UUID", "a43359d2-e50e-43c9-ad86-b77ee5c6524e")
SCORE_CHAR_UUID = os.getenv("SCORE_CHAR_UUID", "29f80071-9a06-426b-8c26-02ae5df749a4")

# Scan interval (seconden) tussen discovery rondes.
SCAN_INTERVAL = float(os.getenv("SCAN_INTERVAL", "8"))

# Max tiles (9 x 6)
MAX_DEVICES = 54

# Web server host / port
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Test endpoints (simulatie zonder echte BLE). Zet ENABLE_TEST_ENDPOINTS=1 om /api/test/* routes te activeren.
ENABLE_TEST_ENDPOINTS = os.getenv("ENABLE_TEST_ENDPOINTS", "0") in ("1", "true", "True")

# BLE advertising (Pi als peripheral) – experimenteel: Linux + BlueZ vereist.
ENABLE_ADVERTISING = os.getenv("ENABLE_ADVERTISING", "0") in ("1", "true", "True")
ADVERTISING_NAME = os.getenv("ADVERTISING_NAME", "scoreboard-PI")

# GATT server voor peripheral mode (vereist ENABLE_ADVERTISING=1 en pydbus)
ENABLE_GATT_SERVER = os.getenv("ENABLE_GATT_SERVER", "0") in ("1", "true", "True")

# BLE connection restrictions - only connect to devices with matching service UUID
STRICT_SERVICE_UUID_FILTERING = os.getenv("STRICT_SERVICE_UUID_FILTERING", "1") in ("1", "true", "True")

# Logging level
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
