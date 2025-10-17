# 🚀 Quick Start - ESP32 Zoekt Naar Pi

## ✅ Setup Checklist

### 1. Raspberry Pi Opstarten

**SSH naar je Pi:**
```bash
ssh pi@[PI-IP-ADRES]
```

**Clone/Update Repository:**
```bash
cd ~
git clone https://github.com/RickMageddon/S3-Scoreboard-BLE.git
cd S3-Scoreboard-BLE
git pull  # als je het al hebt
```

**Installeer Dependencies:**
```bash
chmod +x install.sh
./install.sh
```

**Start de Server:**
```bash
python3 -m server.main
```

Je ziet:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting secure BLE scan loop
```

**Dashboard Openen:**
- Zoek Pi IP: `hostname -I`
- Open browser: `http://[PI-IP]:8000`

---

### 2. ESP32 Uploaden

**In Arduino IDE:**

1. **Installeer ArduinoJson Library:**
   - Sketch → Include Library → Manage Libraries
   - Zoek: `ArduinoJson`
   - Installeer versie van Benoit Blanchon

2. **Open Code:**
   - Open: `examples/esp32_client_simple.cpp`
   - Selecteer alles (Ctrl+A)
   - Kopieer (Ctrl+C)
   - Nieuwe sketch in Arduino IDE (File → New)
   - Plak (Ctrl+V)
   - Save As: `esp32_scoreboard_client.ino`

3. **Configureer Board:**
   - Tools → Board → ESP32 Arduino → **ESP32 Dev Module**
   - Tools → Port → [Selecteer jouw ESP32 port]

4. **Upload:**
   - Klik Upload (→ knop)
   - Wacht tot "Done uploading"

5. **Open Serial Monitor:**
   - Tools → Serial Monitor
   - Baud rate: **115200**

---

### 3. Verwachte Output

**ESP32 Serial Monitor:**
```
╔════════════════════════════════════════╗
║  ESP32 BLE Client - S3 Scoreboard    ║
╚════════════════════════════════════════╝

Game: ESP32 Test Game
Startwaarde score: 0

🔍 Starten met scannen naar Pi server...
Service UUID: c9b9a344-a062-4e55-a507-441c7e610e2c

🔍 Scannen...
🔍 Gevonden: [Device info]
✅ Pi server gevonden!
🔗 Verbinden met Pi server...
✅ Verbonden met Pi!
✅ Service gevonden!
✅ RX Characteristic gevonden!
✅ TX Characteristic gevonden!
✅ Subscribed op TX notifications
🎉 Volledig verbonden en klaar!
💚 Nu verbonden met Pi!
📤 Volledige state verzonden: {"game_name":"ESP32 Test Game","score":0,"timestamp":1234}
📤 Score update: {"score":7}
📤 Score update: {"score":15}
```

**Pi Terminal:**
```
INFO: Auto-connecting to authorized device: ESP32-Client
INFO: Device ESP32-Client successfully connected and added
DEBUG: RX notifications enabled
DEBUG: RX score update from AA:BB:CC:DD:EE:FF: 7
```

**Dashboard (Browser):**
- Kaartje verschijnt met "ESP32-Client" of "ESP32 Test Game"
- Score telt automatisch op (elke 5 seconden)
- Kleur toegewezen aan device

---

## 🔧 Troubleshooting

### ESP32 Vindt Pi Niet

**Controleer Pi Advertising:**
```bash
# Op de Pi:
sudo hciconfig hci0 up
sudo hciconfig hci0 leadv
```

**Check Pi Config:**
```bash
cd ~/S3-Scoreboard-BLE
cat .env
```

Zorg dat deze regels staan:
```
ENABLE_ADVERTISING=1
ENABLE_GATT_SERVER=1
```

**Herstart Pi Server:**
```bash
# Stop met Ctrl+C
python3 -m server.main
```

### ESP32 Vindt Service Niet

**Op Pi, check GATT server logs:**
```bash
journalctl -u bluetooth -f
```

**Op ESP32:**
- Check dat UUIDs exact matchen
- Herstart ESP32 (reset knop)

### Verbinding Valt Weg

**ESP32 Serial Monitor:**
```
💔 Verbinding verbroken!
🔍 Opnieuw scannen...
```

Dit is normaal - ESP32 zal automatisch reconnecten.

**Als het blijft gebeuren:**
- Check Pi Bluetooth: `sudo systemctl status bluetooth`
- Herstart bluetooth: `sudo systemctl restart bluetooth`

### Geen Data op Dashboard

**Check WebSocket:**
- Open browser console (F12)
- Moet zien: "WebSocket connected"

**Check Backend Logs:**
- Kijk naar Pi terminal output
- Moet zien: "RX score update from..."

---

## 🎯 Volgende Stappen

### Automatisch Opstarten (Pi)

```bash
cd ~/S3-Scoreboard-BLE
chmod +x install_service.sh
sudo ./install_service.sh
```

Nu start de server automatisch bij elke boot!

**Check status:**
```bash
sudo systemctl status s3-scoreboard
sudo journalctl -u s3-scoreboard -f
```

### Meerdere ESP32's

Upload dezelfde code naar meerdere ESP32's.
Ze verschijnen allemaal automatisch op het dashboard!

### Eigen Score Logic

Vervang in ESP32 code:
```cpp
void loop() {
    if (isConnected) {
        if (millis() - lastUpdate > UPDATE_INTERVAL) {
            // VERVANG DIT:
            // currentScore += random(1, 11);
            
            // MET JOUW LOGIC:
            currentScore = readYourSensor();
            sendScoreUpdate();
            lastUpdate = millis();
        }
    }
    delay(100);
}
```

---

## 📊 Data Flow Diagram

```
┌─────────────┐                      ┌──────────────────┐
│   ESP32     │                      │  Raspberry Pi    │
│  (Client)   │                      │   (Server)       │
└─────────────┘                      └──────────────────┘
      │                                       │
      │  1. Scan naar SERVICE_UUID            │
      │<──────────────────────────────────────│ Adverteert
      │                                       │
      │           2. Pi gevonden!             │
      │──────────────────────────────────────>│
      │                                       │
      │              3. Connect               │
      │──────────────────────────────────────>│
      │                                       │
      │  4. Get Service & Characteristics     │
      │──────────────────────────────────────>│
      │                                       │
      │  5. Subscribe op TX notifications     │
      │──────────────────────────────────────>│
      │                                       │
      │  6. Write score via RX                │
      │──────────────────────────────────────>│
      │           {"score": 42}               │
      │                                       │
      │  7. Pi command via TX (notify)        │
      │<──────────────────────────────────────│
      │         {"command": "reset"}          │
      │                                       │
```

---

## 📝 Configuratie Aanpassen

### ESP32 Game Naam:
```cpp
String gameName = "Jouw Game Naam";  // Regel 40
```

### ESP32 Update Interval:
```cpp
const unsigned long UPDATE_INTERVAL = 3000;  // Regel 43 (3 seconden)
```

### Pi Scan Interval:
Edit `.env` op Pi:
```
SCAN_INTERVAL=5
```

---

**Succes met je BLE scoreboard! 🎉**

Voor meer info: zie `README.md` en `ARCHITECTURE.md`
