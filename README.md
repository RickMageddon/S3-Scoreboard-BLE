# S3 Scoreboard BLE

Een webinterface die in real-time scoreboards toont van BLE-apparaten die verbonden zijn met een Raspberry Pi 4. De interface toont maximaal 54 apparaten in een 9x6 grid layout.

## 🚀 Quick Start

```bash
# Op Raspberry Pi:
git clone https://github.com/RickMageddon/S3-Scoreboard-BLE.git
cd S3-Scoreboard-BLE
chmod +x install.sh
./install.sh
sudo reboot

# Na herstart:
python3 -m server.main
```

Open browser: `http://[PI-IP]:8000` 🎉

## 🏗️ Architectuur

**Raspberry Pi** = BLE Server (peripheral)
- Adverteert als `S3-Scoreboard`
- Ontvangt scores van ESP32 clients
- Toont alles op web dashboard

**ESP32's** = BLE Clients (central)
- Scannen naar Pi server
- Verbinden automatisch
- Sturen game data (JSON)
- Geen WiFi nodig!

## Hoe het werkt

De Raspberry Pi draait een Python backend die:
- Scant naar BLE-apparaten met een specifieke Service UUID
- Automatisch verbindt met gevonden apparaten
- Ontvangt game naam en score updates via BLE notificaties
- Stuurt wijzigingen via WebSockets naar de webinterface

De webinterface toont voor elk apparaat:
- Device naam
- Game naam
- Live score updates
- Unieke kleur (automatisch toegekend)

## Project structuur

```
server/
├── main.py          # FastAPI server + WebSocket endpoints
├── ble_manager.py   # BLE scanning en verbindingsbeheer
├── config.py        # Configuratie instellingen
├── gatt_server.py   # BLE peripheral mode (Pi als GATT server)
├── models.py        # Data models
└── events.py        # Event system voor UI updates

static/
├── index.html       # Webinterface
├── app.js           # WebSocket client logica
└── styles.css       # CSS Grid styling

examples/
└── esp32_txrx_example.cpp  # ESP32 voorbeeld code
```

## BLE Communicatie

### Service en Characteristics
```
Service UUID:     c9b9a344-a062-4e55-a507-441c7e610e2c
RX Characteristic: 29f80071-9a06-426b-8c26-02ae5df749a4  (ESP32 → Pi)
TX Characteristic: a43359d2-e50e-43c9-ad86-b77ee5c6524e  (Pi → ESP32)
```

### Data formaten
ESP32 naar Pi (RX characteristic, JSON):
```json
{"game_name": "MijnSpel", "score": 42}
{"score": 50}
```

Pi naar ESP32 (TX characteristic, JSON commando's):
```json
{"command": "reset"}
{"command": "set_game", "game_name": "NieuwSpel"}
```

Voor eenvoudige apparaten zijn ook tekst formaten ondersteund:
- `"MijnSpel:42"` (game:score)
- `"42"` (alleen score)

## Beveiliging

De Pi verbindt alleen met apparaten die de juiste Service UUID adverteren. Dit voorkomt verbindingen met willekeurige BLE-apparaten in de buurt.

Standaard instellingen:
- Strict filtering: aan
- Automatische verbinding: aan
- Geen pincode/pairing vereist

## Installatie

### 🚀 Snelle installatie (Raspberry Pi als BLE Server)

De Raspberry Pi fungeert als BLE server waar ESP32 clients automatisch mee verbinden.

#### Stap 1: Clone repository
```bash
cd ~
git clone https://github.com/RickMageddon/S3-Scoreboard-BLE.git
cd S3-Scoreboard-BLE
```

#### Stap 2: Run installatiescript
```bash
chmod +x install.sh
./install.sh
```

Dit installeert alles wat nodig is:
- Bluetooth packages (bluez, etc.)
- Python dependencies (systeem-breed, geen venv)
- GATT server dependencies (pydbus)
- Maakt `.env` configuratie aan
- Stelt Bluetooth rechten in

#### Stap 3: Herstart Pi
```bash
sudo reboot
```

#### Stap 4: Start server
```bash
cd ~/S3-Scoreboard-BLE
python3 -m server.main
```

De server draait nu op: `http://[PI-IP]:8000`

### 🔄 Als systemd service (automatisch opstarten)

Om de server automatisch te starten bij elke boot:

```bash
cd ~/S3-Scoreboard-BLE
chmod +x install_service.sh
sudo ./install_service.sh
```

Dan hoef je niet meer handmatig te starten!

**Handige commando's:**
```bash
# Status bekijken
sudo systemctl status s3-scoreboard

# Live logs
sudo journalctl -u s3-scoreboard -f

# Herstarten
sudo systemctl restart s3-scoreboard
```

### Configuratie

Het installatiescript maakt automatisch een `.env` bestand aan met de juiste instellingen:

```bash
# Pi als BLE Server
ENABLE_ADVERTISING=1
ENABLE_GATT_SERVER=1
ADVERTISING_NAME=S3-Scoreboard

# Service en Characteristics
SCOREBOARD_SERVICE_UUID=c9b9a344-a062-4e55-a507-441c7e610e2c
RX_CHAR_UUID=29f80071-9a06-426b-8c26-02ae5df749a4
TX_CHAR_UUID=a43359d2-e50e-43c9-ad86-b77ee5c6524e

# Automatisch verbinden zonder pairing
DISABLE_AUTHENTICATION=1
```

Je kunt deze aanpassen in het `.env` bestand indien nodig.

### Dashboard openen

Na het starten is de webinterface bereikbaar op:
- Op de Pi zelf: `http://localhost:8000`
- Vanaf ander apparaat: `http://[PI-IP-ADRES]:8000`

Vind je Pi IP-adres met: `hostname -I`

## ESP32 Client Implementatie

De ESP32's werken als **BLE clients** die verbinden met de Raspberry Pi **BLE server**.

### 🎯 Twee opties:

#### Optie 1: Simpele Client (AANBEVOLEN) ⭐
Gebruik `examples/esp32_client_simple.cpp` - ESP32 scant naar Pi en verbindt automatisch:

```cpp
// ESP32 zoekt Pi server en verbindt
BLEClient* pClient = BLEDevice::createClient();
pClient->connect(piServerAddress);
```

**Voordelen:**
- ✅ Zeer eenvoudig
- ✅ Automatische verbinding
- ✅ Automatisch herverbinden bij disconnect
- ✅ Kant-en-klaar JSON communicatie

#### Optie 2: Server Mode (voor geavanceerden)
Gebruik `examples/esp32_txrx_example.cpp` - ESP32 als server, Pi verbindt ernaar:

```cpp
// ESP32 adverteert, Pi verbindt
BLEServer *pServer = BLEDevice::createServer();
```

**Let op:** Vereist `STRICT_SERVICE_FILTER=0` in Pi `.env`

### 📚 Vereiste Arduino libraries
- ArduinoJson (via Library Manager)
- ESP32 BLE Arduino (ingebouwd)

Zie `examples/README.md` voor volledige instructies!

## ESP32 BLE Instellingen en Communicatie

Om goed te verbinden met de Raspberry Pi scoreboard-app, moet je ESP32 de volgende instellingen en BLE-structuur gebruiken:

### Service en Characteristic UUIDs

Gebruik exact deze UUIDs in je ESP32-code:

- **Service UUID**  
  `c9b9a344-a062-4e55-a507-441c7e610e2c`

- **RX Characteristic UUID** (ESP32 → Pi, Pi ontvangt)  
  `29f80071-9a06-426b-8c26-02ae5df749a4`

- **TX Characteristic UUID** (Pi → ESP32, Pi zendt)  
  `a43359d2-e50e-43c9-ad86-b77ee5c6524e`

### Vereiste BLE-structuur op de ESP32

- Maak een BLE-service aan met de Service UUID hierboven.
- Voeg twee characteristics toe:
  - **RX Characteristic**:  
    - UUID: `29f80071-9a06-426b-8c26-02ae5df749a4`  
    - Eigenschappen: `PROPERTY_WRITE`, `PROPERTY_NOTIFY`  
    - ESP32 stuurt hier data naar de Pi (bijvoorbeeld scores, status, etc.)
  - **TX Characteristic**:  
    - UUID: `a43359d2-e50e-43c9-ad86-b77ee5c6524e`  
    - Eigenschappen: `PROPERTY_READ`, `PROPERTY_WRITE`, `PROPERTY_NOTIFY`  
    - Pi kan via deze characteristic commando’s of instellingen naar de ESP32 sturen.

### Dataformaat

- **Aanbevolen:** Gebruik JSON als dataformaat voor communicatie.
  - Voorbeeld van ESP32 naar Pi (RX):
    ```json
    {"game_name": "Tafeltennis", "score": 7}
    ```
  - Voorbeeld van Pi naar ESP32 (TX):
    ```json
    {"command": "reset"}
    ```

### Overige vereisten

- De ESP32 moet de juiste Service UUID adverteren.
- Er is geen pincode of pairing vereist; de verbinding moet automatisch tot stand komen.
- De naam van het ESP32-apparaat maakt niet uit, zolang de Service UUID klopt.
- Zorg dat de characteristics correct zijn aangemaakt en geadverteerd.

### Voorbeeld ESP32-code (Arduino)

```cpp
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#define SERVICE_UUID        "c9b9a344-a062-4e55-a507-441c7e610e2c"
#define RX_CHAR_UUID       "29f80071-9a06-426b-8c26-02ae5df749a4"
#define TX_CHAR_UUID       "a43359d2-e50e-43c9-ad86-b77ee5c6524e"

BLECharacteristic *rxCharacteristic;
BLECharacteristic *txCharacteristic;

void setup() {
  BLEDevice::init("Scoreboard-ESP32");
  BLEServer *pServer = BLEDevice::createServer();
  BLEService *pService = pServer->createService(SERVICE_UUID);

  rxCharacteristic = pService->createCharacteristic(
    RX_CHAR_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY
  );
  rxCharacteristic->addDescriptor(new BLE2902());

  txCharacteristic = pService->createCharacteristic(
    TX_CHAR_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY
  );
  txCharacteristic->addDescriptor(new BLE2902());

  pService->start();
  BLEDevice::startAdvertising();
}

void loop() {
  // Voorbeeld: stuur score update naar Pi
  String scoreJson = "{\"game_name\": \"Tafeltennis\", \"score\": 7}";
  rxCharacteristic->setValue(scoreJson.c_str());
  rxCharacteristic->notify();
  delay(5000);
}
```

### Samenvatting

- Gebruik altijd de juiste UUIDs voor service en characteristics.
- RX = ESP32 stuurt naar Pi, TX = Pi stuurt naar ESP32.
- Gebruik JSON voor data-uitwisseling.
- Geen pairing of pincode nodig.
- De naam van het apparaat is niet belangrijk.

Met deze instellingen werkt de communicatie tussen de ESP32 en de Pi direct en veilig.

## API

### REST endpoints
```
GET  /api/devices           # Lijst van verbonden apparaten
POST /api/devices/{id}/send # Stuur commando naar apparaat
```

### WebSocket
```
ws://localhost:8000/ws      # Real-time updates
```

## Peripheral mode (experimenteel)

De Pi kan ook als BLE peripheral fungeren voor verbindingen met telefoons:

### Vereisten
```bash
# Installeer pydbus dependencies
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 libdbus-1-dev libglib2.0-dev

# Installeer pydbus in venv
source .venv/bin/activate
pip install pydbus
```

### Configuratie
In `.env`:
```bash
ENABLE_ADVERTISING=1
ENABLE_GATT_SERVER=1
```

**Let op:** Vereist sudo rechten voor sommige D-Bus operaties. Als pydbus installatie problemen geeft, zet `ENABLE_GATT_SERVER=0`.

## Troubleshooting

### pydbus installeert niet
**Error:** `WARNING server.gatt_server: pydbus niet geïnstalleerd`

**Oplossing:**
```bash
# Installeer systeem dependencies
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 libdbus-1-dev libglib2.0-dev

# Herinstalleer pydbus
source .venv/bin/activate
pip uninstall pydbus
pip install pydbus --no-cache-dir
```

Of schakel GATT server uit in `.env`:
```bash
ENABLE_GATT_SERVER=0
```

### BLE scanning werkt niet
**Symptoom:** Geen apparaten gevonden

**Oplossingen:**
- Check of Bluetooth aan staat: `sudo hciconfig hci0 up`
- Check of ESP32 de juiste service UUID adverteert
- Verhoog log level in `.env`: `LOG_LEVEL=DEBUG`
- Check logs: `journalctl -u scoreboard -f`

### Server start niet op Windows
**Symptoom:** BLE errors op Windows

**Oplossing:** Dit is normaal! BLE scanning werkt alleen op Linux. Voor development op Windows:
```bash
# In .env:
ENABLE_TEST_ENDPOINTS=1
```

Dan kun je test apparaten toevoegen via: `POST http://localhost:8000/api/test/add`

## Beperkingen

- Maximaal 54 apparaten (grid grootte)
- Eenvoudige retry logica voor verbindingen
- Geen authenticatie (geschikt voor lokaal netwerk)
- Linux/BlueZ vereist voor peripheral mode

## Licentie

MIT
