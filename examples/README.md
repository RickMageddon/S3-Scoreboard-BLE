# ESP32 Voorbeelden voor S3 Scoreboard

Deze folder bevat voorbeeldcode voor ESP32 devices die communiceren met de Raspberry Pi scoreboard server.

## Beschikbare Voorbeelden

### 1. `esp32_client_simple.cpp` - Simpele BLE Client ⭐ AANBEVOLEN
**Gebruik dit voor nieuwe projecten!**

Een eenvoudige, complete client die:
- ✅ Automatisch scant naar de Pi server
- ✅ Automatisch verbindt bij het vinden van de server
- ✅ Periodiek score updates stuurt
- ✅ Automatisch opnieuw verbindt bij disconnect
- ✅ Ondersteunt commando's van de Pi (reset, game naam wijzigen)
- ✅ Goed gedocumenteerde code met emoji's voor duidelijkheid
- ✅ Simpel aan te passen (game naam, update interval, etc.)

**Installatie:**
1. Open `esp32_client_simple.cpp` in Arduino IDE
2. Installeer de ArduinoJson library (via Library Manager)
3. Selecteer je ESP32 board
4. Upload naar ESP32
5. Open Serial Monitor (115200 baud) om de status te zien

**Aanpassen:**
```cpp
// Wijzig game naam
String gameName = "Mijn Coole Game";

// Wijzig update interval (in milliseconden)
const unsigned long UPDATE_INTERVAL = 3000; // Elke 3 seconden

// Wijzig start score
int currentScore = 100;
```

### 2. `esp32_txrx_example.cpp` - TX/RX Voorbeeld
**Legacy voorbeeld met TX/RX characteristics**

Dit voorbeeld toont de bi-directionele communicatie tussen ESP32 en Pi:
- TX: ESP32 → Pi (game data, scores)
- RX: ESP32 ← Pi (commando's)

Gebruikt `BLEServer` in plaats van `BLEClient`, wat betekent dat de ESP32 als peripheral werkt (de Pi verbindt naar de ESP32).

## Service en Characteristic UUIDs

**Belangrijk:** Zorg dat deze UUIDs matchen met je server configuratie!

```cpp
#define SERVICE_UUID    "c9b9a344-a062-4e55-a507-441c7e610e2c"
#define RX_CHAR_UUID    "29f80071-9a06-426b-8c26-02ae5df749a4"  // Pi ontvangt
#define TX_CHAR_UUID    "a43359d2-e50e-43c9-ad86-b77ee5c6524e"  // Pi stuurt
```

Deze kun je aanpassen in je `.env` bestand op de Pi:
```bash
SCOREBOARD_SERVICE_UUID=c9b9a344-a062-4e55-a507-441c7e610e2c
RX_CHAR_UUID=29f80071-9a06-426b-8c26-02ae5df749a4
TX_CHAR_UUID=a43359d2-e50e-43c9-ad86-b77ee5c6524e
```

## Data Formaten

### ESP32 → Pi (JSON)
```json
// Volledige game state
{
  "game_name": "MijnSpel",
  "score": 42,
  "timestamp": 12345
}

// Alleen score update (efficiënter)
{
  "score": 50
}
```

### Pi → ESP32 (JSON Commando's)
```json
// Reset score
{
  "command": "reset"
}

// Wijzig game naam
{
  "command": "set_game",
  "game_name": "NieuwSpel"
}
```

## Vereisten

### Hardware
- ESP32 development board (alle varianten)
- USB kabel voor programmeren
- Raspberry Pi met Bluetooth (Pi 3/4/5)

### Software
- Arduino IDE (1.8.x of 2.x)
- ESP32 Board Support (via Boards Manager)
- ArduinoJson library (via Library Manager)

### Arduino IDE Setup
1. **ESP32 Board Support installeren:**
   - File → Preferences
   - Bij "Additional Boards Manager URLs" toevoegen:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Tools → Board → Boards Manager → zoek "esp32" → Install

2. **ArduinoJson library installeren:**
   - Sketch → Include Library → Manage Libraries
   - Zoek "ArduinoJson"
   - Installeer versie 6.x of nieuwer

3. **Board selecteren:**
   - Tools → Board → ESP32 Arduino → ESP32 Dev Module
   - (of selecteer je specifieke ESP32 board)

## Troubleshooting

### ESP32 vindt de Pi niet
- ✅ Check of de Pi server draait
- ✅ Check of Bluetooth aan staat op de Pi (`sudo hciconfig hci0 up`)
- ✅ Check of de SERVICE_UUID overeenkomt
- ✅ Kijk in de Serial Monitor voor foutmeldingen

### Verbinding valt steeds weg
- ✅ Check de afstand tussen ESP32 en Pi (max ~10 meter)
- ✅ Check of er geen obstakels tussen zitten
- ✅ Probeer de Pi en ESP32 opnieuw op te starten

### Score updates komen niet aan
- ✅ Check of RX_CHAR_UUID correct is
- ✅ Kijk in de Pi logs: `journalctl -u scoreboard -f`
- ✅ Controleer het JSON formaat in Serial Monitor

### Upload naar ESP32 lukt niet
- ✅ Check of de juiste COM/Serial poort geselecteerd is
- ✅ Houd BOOT knop ingedrukt tijdens uploaden (sommige boards)
- ✅ Probeer een andere USB kabel
- ✅ Check of de driver geïnstalleerd is (CP2102 of CH340)

## Tips voor Productie

### Batterijverbruik verlagen
```cpp
// Gebruik deep sleep tussen updates
esp_sleep_enable_timer_wakeup(5000000); // 5 seconden
esp_deep_sleep_start();
```

### WiFi uitschakelen (als niet nodig)
```cpp
WiFi.mode(WIFI_OFF);
btStop(); // Stop classic Bluetooth
```

### Meer robuuste verbinding
```cpp
// Verhoog connection interval
pClient->setConnectionParams(80, 100, 0, 400);
```

## Eigen Project Maken

1. **Kopieer** `esp32_client_simple.cpp`
2. **Hernoem** naar je project naam
3. **Pas aan**:
   - Game naam
   - Update logica (ipv random scores)
   - Commando handlers (wat te doen bij Pi commando's)
4. **Test** met Serial Monitor
5. **Deploy** naar je devices

## Licentie

Deze voorbeelden zijn vrij te gebruiken en aan te passen voor eigen projecten.
