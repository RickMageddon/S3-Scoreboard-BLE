# S3 Scoreboard BLE

Moderne webinterface (9 x 6 raster) die dynamisch tegels toevoegt/verwijdert op basis van BLE verbindingen met de Raspberry Pi 4 (Raspberry Pi OS 64-bit).

## Architectuur

- Raspberry Pi draait een Python backend (FastAPI) die:
  - BLE scant naar apparaten die een specifieke Service UUID adverteren.
  - Verbindt als central (client) met elk gevonden device.
  - Leest kenmerken (naam van de game, score) en luistert naar score-updates via notificaties.
  - Houdt real-time state bij en pusht wijzigingen via WebSockets naar de frontend.
- Frontend (static web app) toont een 9 kolommen x 6 rijen grid (max 54 tegels) met:
  - Apparaatnaam
  - Gamenaam
  - Score (live updates)
  - Unieke kleur per apparaat (deterministisch gegenereerd)

## Bestanden

| Pad | Omschrijving |
|-----|--------------|
| `server/main.py` | Start FastAPI + WebSocket endpoints |
| `server/ble_manager.py` | BLE scanning & verbindingen beheren |
| `server/models.py` | Dataclasses / pydantic modellen |
| `server/events.py` | Eenvoudige async pub/sub voor UI updates |
| `server/config.py` | Configuratie (service UUID, characteristics) |
| `static/index.html` | Frontend HTML |
| `static/app.js` | WebSocket client + DOM logica |
| `static/styles.css` | Styling (CSS Grid) |

## Security & Connection Control

The app implements strict security controls to prevent unauthorized connections:

### Service UUID Filtering
- **Default behavior**: Only connects to BLE devices advertising the exact service UUID (`c9b9a344-a062-4e55-a507-441c7e610e2c`)
- **Automatic connection**: Devices with matching service UUID connect automatically without user intervention
- **No authentication**: Connections require no PIN codes or pairing confirmation

### Configuration Options

Copy `.env.example` to `.env` and adjust settings:

```bash
# Strict filtering (recommended for security)
STRICT_SERVICE_FILTER=1

# Disable authentication for automatic connections
DISABLE_AUTHENTICATION=1

# Custom allowed device name patterns (only when STRICT_SERVICE_FILTER=0)
ALLOWED_DEVICE_NAME_PATTERNS=scoreboard,game,ble
```

### Security Features
- ✅ **Service UUID verification**: Only devices with matching service UUID can connect
- ✅ **Automatic connection**: No manual pairing or confirmation required
- ✅ **Authentication disabled**: No PIN codes or user interaction needed
- ✅ **Connection filtering**: Rejects unauthorized devices immediately
- ✅ **Reconnection support**: Automatically reconnects to known devices

## Installatie (Raspberry Pi)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m server.main
```

Server draait standaard op `http://0.0.0.0:8000` -> open in browser op de Pi (`http://localhost:8000`).

### Verbinden met mobiel (Pi als peripheral)
De Pi kan ook als BLE peripheral adverteren, zodat je telefoon kan verbinden en scores sturen.

1. Installeer pydbus: `pip install pydbus`
2. Zet in `.env`:
   ```bash
   ENABLE_ADVERTISING=1
   ENABLE_GATT_SERVER=1
   ADVERTISING_NAME=scoreboard-PI
   ```
3. Start server: `python -m server.main`
4. Op je telefoon: gebruik BLE app (nRF Connect, LightBlue) om te verbinden met "scoreboard-PI"
5. Schrijf naar characteristic `29f80071-9a06-426b-8c26-02ae5df749a4` (score) met integer waarde (ASCII of 4-byte little-endian)
6. Score verschijnt live op de website.

De Pi toont zichzelf als device op de website; score updates van telefoon worden direct weergegeven.

## WebSocket Events

Voorbeeld bericht (JSON):

```json
{
  "type": "device_added",
  "device": {"id": "AA:BB:CC:DD:EE:FF", "name": "MyDevice", "game_name": "Space Run", "score": 42, "color": "#FF6B6B"}
}
```

## Kleurtoewijzing
Deterministisch op basis van MAC adres hash, uit vaste palet. Consistent tijdens runtime.

## Flutter (Optioneel)
Wil je later Flutter Web gebruiken, dan kun je de WebSocket API (`/ws`) hergebruiken. De backend hoeft niet te veranderen.

## Beperkingen / TODO
* Device discovery & connect retry strategie is basaal.
* Geen authenticatie (niet nodig voor lokaal gebruik).
* Score notificatie parser is simpel (verwacht integer ASCII of little-endian 4 byte int).

## Stoppen
Ctrl+C in terminal.

## Licentie
MIT (pas aan indien gewenst).
