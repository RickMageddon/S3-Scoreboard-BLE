/*
 * ESP32 BLE Client - Simpel voorbeeld voor S3 Scoreboard
 * 
 * Deze client scant naar de Raspberry Pi scoreboard server en verbindt automatisch.
 * Stuurt periodiek score updates naar de Pi via de RX characteristic.
 * 
 * Vereisten:
 * - ESP32 board
 * - ArduinoJson library (via Library Manager)
 * 
 * Installatie:
 * 1. Open dit bestand in Arduino IDE
 * 2. Selecteer Tools > Board > ESP32 Dev Module (of jouw ESP32 board)
 * 3. Installeer ArduinoJson library: Sketch > Include Library > Manage Libraries > zoek "ArduinoJson"
 * 4. Upload naar ESP32
 * 
 * Werking:
 * - ESP32 scant naar BLE server met SERVICE_UUID
 * - Verbindt automatisch wanneer gevonden
 * - Stuurt elke 5 seconden een score update
 * - Herstelt verbinding automatisch bij disconnect
 */

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <BLEClient.h>
#include <ArduinoJson.h>

// UUIDs moeten matchen met server configuratie
#define SERVICE_UUID        "c9b9a344-a062-4e55-a507-441c7e610e2c"
#define RX_CHAR_UUID        "29f80071-9a06-426b-8c26-02ae5df749a4"  // Pi ontvangt (ESP32 -> Pi)
#define TX_CHAR_UUID        "a43359d2-e50e-43c9-ad86-b77ee5c6524e"  // Pi stuurt (Pi -> ESP32)

// Game configuratie
String gameName = "ESP32 Test Game";
int currentScore = 0;
unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 5000; // Update elke 5 seconden

// BLE objecten
BLEScan* pBLEScan = nullptr;
BLEClient* pClient = nullptr;
BLERemoteCharacteristic* pRxChar = nullptr;
BLERemoteCharacteristic* pTxChar = nullptr;
BLEAdvertisedDevice* targetDevice = nullptr;

bool isConnected = false;
bool doConnect = false;
bool doScan = false;

// Callback voor TX characteristic (data van Pi)
static void notifyCallback(BLERemoteCharacteristic* pBLERemoteCharacteristic,
                            uint8_t* pData, size_t length, bool isNotify) {
    String rxValue = String((char*)pData).substring(0, length);
    Serial.println("📩 TX van Pi: " + rxValue);
    
    // Parse JSON commando van Pi
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, rxValue);
    
    if (!error && doc.containsKey("command")) {
        String command = doc["command"];
        
        if (command == "reset") {
            currentScore = 0;
            Serial.println("🔄 Score gereset door Pi");
        }
        else if (command == "set_game") {
            gameName = doc["game_name"].as<String>();
            Serial.println("🎮 Game naam gewijzigd: " + gameName);
        }
    }
}

// Callback voor gevonden BLE devices tijdens scan
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
        Serial.print("🔍 Gevonden BLE device: ");
        Serial.println(advertisedDevice.toString().c_str());

        // Check of dit onze scoreboard server is
        if (advertisedDevice.haveServiceUUID() && 
            advertisedDevice.isAdvertisingService(BLEUUID(SERVICE_UUID))) {
            
            Serial.println("✅ Scoreboard server gevonden!");
            BLEDevice::getScan()->stop();
            targetDevice = new BLEAdvertisedDevice(advertisedDevice);
            doConnect = true;
            doScan = false;
        }
    }
};

// Verbind met de Pi server
bool connectToServer() {
    Serial.println("🔗 Verbinden met Pi server...");
    
    pClient = BLEDevice::createClient();
    Serial.println(" - Client aangemaakt");

    // Verbind met de remote BLE server
    if (!pClient->connect(targetDevice)) {
        Serial.println("❌ Verbinding mislukt");
        return false;
    }
    Serial.println("✅ Verbonden met Pi!");

    // Verkrijg referentie naar de service
    BLERemoteService* pRemoteService = pClient->getService(SERVICE_UUID);
    if (pRemoteService == nullptr) {
        Serial.println("❌ Service niet gevonden");
        pClient->disconnect();
        return false;
    }
    Serial.println("✅ Service gevonden");

    // Verkrijg referentie naar RX characteristic (ESP32 -> Pi)
    pRxChar = pRemoteService->getCharacteristic(RX_CHAR_UUID);
    if (pRxChar == nullptr) {
        Serial.println("❌ RX Characteristic niet gevonden");
        pClient->disconnect();
        return false;
    }
    Serial.println("✅ RX Characteristic gevonden");

    // Verkrijg referentie naar TX characteristic (Pi -> ESP32)
    pTxChar = pRemoteService->getCharacteristic(TX_CHAR_UUID);
    if (pTxChar != nullptr) {
        Serial.println("✅ TX Characteristic gevonden");
        
        // Registreer notify callback voor commando's van Pi
        if (pTxChar->canNotify()) {
            pTxChar->registerForNotify(notifyCallback);
            Serial.println("✅ TX notificaties ingeschakeld");
        }
    }

    isConnected = true;
    Serial.println("🎉 Volledig verbonden en klaar!");
    
    // Stuur initiële game state
    sendGameState();
    
    return true;
}

// Stuur volledige game state naar Pi
void sendGameState() {
    if (!isConnected || pRxChar == nullptr) {
        return;
    }

    DynamicJsonDocument doc(1024);
    doc["game_name"] = gameName;
    doc["score"] = currentScore;
    doc["timestamp"] = millis();
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    pRxChar->writeValue(jsonString.c_str(), jsonString.length());
    
    Serial.println("📤 Volledige state verzonden: " + jsonString);
}

// Stuur alleen score update naar Pi
void sendScoreUpdate() {
    if (!isConnected || pRxChar == nullptr) {
        return;
    }

    DynamicJsonDocument doc(512);
    doc["score"] = currentScore;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    pRxChar->writeValue(jsonString.c_str(), jsonString.length());
    
    Serial.println("📤 Score update: " + String(currentScore));
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n\n╔════════════════════════════════════════╗");
    Serial.println("║  ESP32 BLE Client - S3 Scoreboard    ║");
    Serial.println("╚════════════════════════════════════════╝\n");
    
    Serial.println("Game: " + gameName);
    Serial.println("Startwaarde score: " + String(currentScore));
    Serial.println();

    // Initialiseer BLE
    BLEDevice::init("ESP32-Client");
    
    // Scan opzetten
    pBLEScan = BLEDevice::getScan();
    pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
    pBLEScan->setActiveScan(true);
    pBLEScan->setInterval(100);
    pBLEScan->setWindow(99);
    
    Serial.println("🔍 Starten met scannen naar Pi server...");
    Serial.println("Service UUID: " + String(SERVICE_UUID));
    doScan = true;
}

void loop() {
    // Als we moeten verbinden met de gevonden server
    if (doConnect) {
        if (connectToServer()) {
            Serial.println("💚 Nu verbonden met scoreboard!");
        } else {
            Serial.println("❌ Verbinding mislukt, opnieuw scannen...");
            doScan = true;
        }
        doConnect = false;
    }

    // Als we verbonden zijn, stuur periodieke updates
    if (isConnected) {
        // Check of verbinding nog actief is
        if (!pClient->isConnected()) {
            isConnected = false;
            Serial.println("💔 Verbinding verbroken!");
            Serial.println("🔍 Opnieuw scannen...");
            doScan = true;
            return;
        }
        
        // Stuur periodieke score updates
        if (millis() - lastUpdate > UPDATE_INTERVAL) {
            // Simuleer score wijziging
            currentScore += random(1, 11);
            sendScoreUpdate();
            lastUpdate = millis();
        }
    }
    // Anders scannen naar de server
    else if (doScan) {
        Serial.println("🔍 Scannen...");
        BLEScanResults foundDevices = pBLEScan->start(5, false);
        Serial.print("Scan voltooid, ");
        Serial.print(foundDevices.getCount());
        Serial.println(" devices gevonden");
        pBLEScan->clearResults();
        
        if (!doConnect) {
            delay(2000); // Wacht voordat we opnieuw scannen
        }
    }

    delay(100);
}

/*
 * ╔════════════════════════════════════════════════════════════╗
 * ║                      GEBRUIKSINSTRUCTIES                   ║
 * ╚════════════════════════════════════════════════════════════╝
 * 
 * 1. Zorg dat je Raspberry Pi server draait
 * 2. Upload deze code naar je ESP32
 * 3. Open de Serial Monitor (115200 baud)
 * 4. ESP32 zal automatisch scannen en verbinden
 * 5. Je ziet de score updates verschijnen op het scoreboard
 * 
 * ╔════════════════════════════════════════════════════════════╗
 * ║                      AANPASSINGEN                          ║
 * ╚════════════════════════════════════════════════════════════╝
 * 
 * Game naam wijzigen:
 *   Pas de variabele 'gameName' aan in regel 28
 * 
 * Update interval wijzigen:
 *   Pas 'UPDATE_INTERVAL' aan in regel 31 (in milliseconden)
 * 
 * Start score wijzigen:
 *   Pas 'currentScore' aan in regel 29
 * 
 * ╔════════════════════════════════════════════════════════════╗
 * ║                      DATA FORMATEN                         ║
 * ╚════════════════════════════════════════════════════════════╝
 * 
 * ESP32 -> Pi (RX):
 *   {"game_name": "MijnSpel", "score": 42, "timestamp": 12345}
 *   {"score": 50}  // Alleen score update
 * 
 * Pi -> ESP32 (TX):
 *   {"command": "reset"}
 *   {"command": "set_game", "game_name": "NieuwSpel"}
 */
