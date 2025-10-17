# S3 Scoreboard BLE Architecture

## 🎯 Correcte BLE Architectuur

### Rolverdeling
- **ESP32** = BLE Peripheral/Server (adverteert, heeft GATT service met characteristics)
- **Raspberry Pi** = BLE Central/Client (scant, verbindt, leest data)

### Waarom Deze Architectuur?
Dit is de standaard IoT pattern:
- ESP32 is een sensor device dat data genereert (score updates)
- Raspberry Pi is de hub die data verzamelt van meerdere ESP32's
- ESP32 adverteert zijn aanwezigheid
- Pi scant actief naar beschikbare ESP32's en verbindt

---

## 📡 BLE Service Structuur

### Service UUID
```
c9b9a344-a062-4e55-a507-441c7e610e2c
```

### Characteristics

#### RX Characteristic (ESP32 → Pi)
```
UUID: 29f80071-9a06-426b-8c26-02ae5df749a4
Properties: READ, WRITE, NOTIFY
Doel: ESP32 stuurt score data naar Pi
```

**Data Format (JSON):**
```json
{
  "game_name": "My Game",
  "score": 42,
  "timestamp": 12345
}
```
Of alleen score update:
```json
{
  "score": 50
}
```

#### TX Characteristic (Pi → ESP32)
```
UUID: a43359d2-e50e-43c9-ad86-b77ee5c6524e
Properties: READ, WRITE
Doel: Pi stuurt commando's naar ESP32
```

**Commando Format (JSON):**
```json
{
  "command": "reset"
}
```
```json
{
  "command": "set_game",
  "game_name": "Nieuwe Game"
}
```

---

## 🔄 Data Flow

```
┌─────────────┐                      ┌──────────────────┐
│   ESP32     │                      │  Raspberry Pi    │
│  (Server)   │                      │   (Client)       │
└─────────────┘                      └──────────────────┘
      │                                       │
      │  1. Advertise Service UUID            │
      │──────────────────────────────────────>│
      │                                       │
      │           2. Scan & Discover          │
      │<──────────────────────────────────────│
      │                                       │
      │              3. Connect               │
      │<──────────────────────────────────────│
      │                                       │
      │  4. Subscribe to RX notifications     │
      │<──────────────────────────────────────│
      │                                       │
      │  5. Send score via RX (notify)        │
      │──────────────────────────────────────>│
      │                                       │
      │  6. Pi command via TX (write)         │
      │<──────────────────────────────────────│
      │                                       │
```

---

## 🔧 Component Status

### ESP32 (examples/esp32_client_simple.cpp)
✅ **COMPLEET** - Volledig herschreven als BLE server
- ✅ BLEServer initialisatie
- ✅ Service met beide characteristics
- ✅ Advertising
- ✅ Connection callbacks
- ✅ RX notifications (ESP32 → Pi)
- ✅ TX write callbacks (Pi → ESP32)
- ✅ JSON data format
- ✅ Auto-reconnect

### Raspberry Pi (server/ble_manager.py)
✅ **COMPLEET** - Werkt al als BLE client
- ✅ BleakScanner voor device discovery
- ✅ BleakClient voor connecties
- ✅ Service UUID filtering
- ✅ RX notification subscriptions
- ✅ TX write functionaliteit
- ✅ JSON parsing
- ✅ Auto-reconnect bij disconnect

### Web Dashboard
✅ **COMPLEET** - Toont real-time data
- ✅ WebSocket verbinding met backend
- ✅ Real-time score updates
- ✅ Server info display (MAC, UUIDs)
- ✅ Multi-device support

---

## 🚀 Gebruik

### 1. Raspberry Pi Setup
```bash
cd /pad/naar/S3-Scoreboard-BLE-1
./install.sh              # Installeer dependencies
./install_service.sh       # Start als systemd service
```

Of handmatig:
```bash
python3 -m server.main
```

Dashboard beschikbaar op: http://[pi-ip]:8000

### 2. ESP32 Setup
1. Open `examples/esp32_client_simple.cpp` in Arduino IDE
2. Installeer ESP32 board support (via Board Manager)
3. Installeer ArduinoJson library (via Library Manager)
4. Selecteer je ESP32 board (Tools > Board)
5. Upload code naar ESP32
6. Open Serial Monitor (115200 baud)

### 3. Verbinding
De ESP32 en Pi vinden elkaar automatisch:
1. ESP32 start advertising met Service UUID
2. Pi scant en vindt ESP32
3. Pi verbindt automatisch
4. ESP32 stuurt initiële game state
5. ESP32 stuurt elke 5 seconden score updates
6. Dashboard toont real-time updates

---

## 🔍 Troubleshooting

### ESP32 adverteert niet
- Check Serial Monitor voor "BLE Server gestart"
- Verifieer dat UUIDs matchen met Pi config
- Herstart ESP32

### Pi vindt ESP32 niet
- Check dat bluetooth enabled is: `systemctl status bluetooth`
- Verifieer scan met: `sudo bluetoothctl scan on`
- Check logs: `journalctl -u s3-scoreboard -f`
- Zorg dat STRICT_SERVICE_UUID_FILTERING=true in .env

### Geen data op dashboard
- Check WebSocket verbinding in browser console (F12)
- Verifieer dat ESP32 verbonden is (Serial Monitor)
- Check backend logs voor errors
- Controleer firewall (port 8000)

### Compile errors ESP32
- Installeer ESP32 board support: https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html
- Installeer ArduinoJson via Library Manager
- Selecteer correct board (ESP32 Dev Module)

---

## 📝 Aanpassingen

### ESP32 Game Naam Wijzigen
In `esp32_client_simple.cpp`:
```cpp
String gameName = "Mijn Nieuwe Game";  // Regel 40
```

### Update Interval Wijzigen
In `esp32_client_simple.cpp`:
```cpp
const unsigned long UPDATE_INTERVAL = 5000;  // Regel 43 (milliseconden)
```

### Score Simulatie Uitschakelen
Verwijder deze regel uit `loop()`:
```cpp
currentScore += random(1, 11);  // Verwijder voor handmatige updates
```

Voeg je eigen score logic toe:
```cpp
if (digitalRead(BUTTON_PIN) == LOW) {
    currentScore += 10;
    sendScoreUpdate();
}
```

---

## 🎓 BLE Terminologie

| Term | Betekenis | In dit project |
|------|-----------|----------------|
| **Central** | Scant en verbindt | Raspberry Pi |
| **Peripheral** | Adverteert | ESP32 |
| **Server** | Heeft GATT services | ESP32 |
| **Client** | Leest GATT data | Raspberry Pi |
| **Service** | Groep characteristics | c9b9a344... |
| **Characteristic** | Data endpoint | RX/TX |
| **Notify** | Push notificatie | ESP32 → Pi |
| **Write** | Data schrijven | Pi → ESP32 |

**Belangrijk:** Een device kan tegelijk Server én Peripheral zijn (ESP32), of Client én Central (Pi).

---

## 📚 Zie Ook

- `examples/README.md` - Gedetailleerde ESP32 voorbeelden
- `START.md` - Quick start guide
- `README.md` - Project overzicht
- `.env.example` - Configuratie opties
