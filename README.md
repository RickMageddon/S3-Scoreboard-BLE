# S3 Scoreboard BLE

Een webinterface die in real-time scoreboards toont van BLE-apparaten die verbonden zijn met een Raspberry Pi 4. De interface toont maximaal 54 apparaten in een 9x6 grid layout.

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

### Raspberry Pi setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuratie
Kopieer `.env.example` naar `.env` en pas aan indien nodig:
```bash
SCOREBOARD_SERVICE_UUID=c9b9a344-a062-4e55-a507-441c7e610e2c
RX_CHAR_UUID=29f80071-9a06-426b-8c26-02ae5df749a4
TX_CHAR_UUID=a43359d2-e50e-43c9-ad86-b77ee5c6524e
STRICT_SERVICE_FILTER=1
```

### Server starten
```bash
python -m server.main
```

De webinterface is bereikbaar op `http://localhost:8000`

## ESP32 implementatie

Gebruik de voorbeeldcode in `examples/esp32_txrx_example.cpp`. Belangrijke punten:

1. Adverteer de juiste Service UUID
2. Maak twee characteristics aan:
   - RX (Pi ontvangt): 29f80071-9a06-426b-8c26-02ae5df749a4
   - TX (Pi stuurt):   a43359d2-e50e-43c9-ad86-b77ee5c6524e
3. Stuur data in JSON formaat
4. Device naam maakt niet uit voor beveiliging

### Vereiste libraries
- ArduinoJson (via Library Manager)
- ESP32 BLE Arduino (ingebouwd)

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

```bash
# In .env:
ENABLE_ADVERTISING=1
ENABLE_GATT_SERVER=1

# Vereist: sudo rechten en pydbus
pip install pydbus
```

## Beperkingen

- Maximaal 54 apparaten (grid grootte)
- Eenvoudige retry logica voor verbindingen
- Geen authenticatie (geschikt voor lokaal netwerk)
- Linux/BlueZ vereist voor peripheral mode

## Licentie

MIT
