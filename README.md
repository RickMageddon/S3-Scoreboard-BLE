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

## Aanpassen BLE UUIDs
Pas in `server/config.py` de UUIDs aan zodat ze overeenkomen met je devices.

## Installatie (Raspberry Pi)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m server.main
```

Server draait standaard op `http://0.0.0.0:8000` -> open in Chromium/Firefox op de Pi (`http://localhost:8000`).

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
