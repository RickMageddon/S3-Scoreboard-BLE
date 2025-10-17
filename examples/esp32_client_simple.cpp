/*
 * ESP32 BLE Client - S3 Scoreboard (Actieve Connectie)
 * 
 * ESP32 werkt als BLE CENTRAL (client) die actief zoekt naar de Raspberry Pi.
 * De Pi (BLE peripheral/server) adverteert en de ESP32 verbindt ermee.
 * 
 * Architectuur:
 * - ESP32 = BLE Client/Central (scant, verbindt, stuurt data)
 * - Raspberry Pi = BLE Server/Peripheral (adverteert, ontvangt data)
 * 
 * Vereisten:
 * - ESP32 board
 * - ArduinoJson library (via Library Manager)
 * - Pi moet GATT server mode gebruiken (ENABLE_GATT_SERVER=1 in .env)
 * 
 * Installatie:
 * 1. Open dit bestand in Arduino IDE
 * 2. Selecteer Tools > Board > ESP32 Dev Module (of jouw ESP32 board)
 * 3. Installeer ArduinoJson library: Sketch > Include Library > Manage Libraries > zoek "ArduinoJson"
 * 4. Upload naar ESP32
 * 
 * Werking:
 * - ESP32 scant naar Pi's BLE service (SERVICE_UUID)
 * - ESP32 verbindt met Pi wanneer gevonden
 * - ESP32 stuurt score updates via write naar RX characteristic
 * - Pi ontvangt en toont op dashboard
 */

#include <BLEDevice.h>
#include <BLEClient.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <ArduinoJson.h>

// UUIDs moeten matchen met Pi configuratie
#define SERVICE_UUID        "c9b9a344-a062-4e55-a507-441c7e610e2c"
#define RX_CHAR_UUID        "29f80071-9a06-426b-8c26-02ae5df749a4"  // ESP32 schrijft naar Pi
#define TX_CHAR_UUID        "a43359d2-e50e-43c9-ad86-b77ee5c6524e"  // Pi stuurt commando's

// Game configuratie
String gameName = "ESP32 Test Game";
int currentScore = 0;
unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 5000; // Update elke 5 seconden

// BLE objecten
BLEClient* pClient = nullptr;
BLERemoteCharacteristic* pRxChar = nullptr;
BLERemoteCharacteristic* pTxChar = nullptr;
BLEScan* pBLEScan = nullptr;

// Status variabelen
bool doConnect = false;
bool isConnected = false;
bool doScan = false;
BLEAdvertisedDevice* targetDevice = nullptr;

// Forward declarations
void sendGameState();
void sendScoreUpdate();
bool connectToServer();

// Scan callback - zoekt naar Pi server
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
        Serial.print("🔍 Gevonden: ");
        Serial.println(advertisedDevice.toString().c_str());
        
        // Check of dit de Pi server is
        if (advertisedDevice.haveServiceUUID() && 
            advertisedDevice.isAdvertisingService(BLEUUID(SERVICE_UUID))) {
            
            Serial.println("✅ Pi server gevonden!");
            BLEDevice::getScan()->stop();
            targetDevice = new BLEAdvertisedDevice(advertisedDevice);
            doConnect = true;
            doScan = false;
        }
    }
};

// TX Characteristic callback (Pi -> ESP32 commando's)
void notifyCallback(BLERemoteCharacteristic* pChar, uint8_t* pData, size_t length, bool isNotify) {
    String rxValue = "";
    for(int i = 0; i < length; i++) {
        rxValue += (char)pData[i];
    }
    
    if (rxValue.length() > 0) {
        Serial.println("📩 TX van Pi: " + rxValue);
        
        // Parse JSON commando van Pi
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, rxValue);
        
        if (!error && doc.containsKey("command")) {
            String command = doc["command"];
            
            if (command == "reset") {
                currentScore = 0;
                Serial.println("🔄 Score gereset door Pi");
                sendGameState(); // Bevestig reset
            }
            else if (command == "set_game") {
                gameName = doc["game_name"].as<String>();
                Serial.println("🎮 Game naam gewijzigd: " + gameName);
                sendGameState(); // Bevestig wijziging
            }
        }
    }
}

// Verbind met Pi server
bool connectToServer() {
    Serial.println("🔗 Verbinden met Pi server...");
    
    pClient = BLEDevice::createClient();
    
    // Verbind met de Pi
    if (!pClient->connect(targetDevice)) {
        Serial.println("❌ Verbinding mislukt!");
        return false;
    }
    Serial.println("✅ Verbonden met Pi!");
    
    // Verkrijg referentie naar de service
    BLERemoteService* pRemoteService = pClient->getService(SERVICE_UUID);
    if (pRemoteService == nullptr) {
        Serial.println("❌ Service niet gevonden!");
        pClient->disconnect();
        return false;
    }
    Serial.println("✅ Service gevonden!");
    
    // Verkrijg RX characteristic (ESP32 -> Pi)
    pRxChar = pRemoteService->getCharacteristic(RX_CHAR_UUID);
    if (pRxChar == nullptr) {
        Serial.println("❌ RX Characteristic niet gevonden!");
        pClient->disconnect();
        return false;
    }
    Serial.println("✅ RX Characteristic gevonden!");
    
    // Verkrijg TX characteristic (Pi -> ESP32)
    pTxChar = pRemoteService->getCharacteristic(TX_CHAR_UUID);
    if (pTxChar != nullptr) {
        Serial.println("✅ TX Characteristic gevonden!");
        
        // Subscribe voor Pi commando's met callback functie
        if(pTxChar->canNotify()) {
            pTxChar->registerForNotify(notifyCallback);
            Serial.println("✅ Subscribed op TX notifications");
        }
    }
    
    isConnected = true;
    Serial.println("🎉 Volledig verbonden en klaar!");
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
            Serial.println("💚 Nu verbonden met Pi!");
            sendGameState(); // Stuur initiële state
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
        BLEScanResults* foundDevices = pBLEScan->start(5, false);
        Serial.print("Scan voltooid, ");
        Serial.print(foundDevices->getCount());
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
 * 1. Zorg dat je Raspberry Pi GATT server draait (ENABLE_GATT_SERVER=1)
 * 2. Upload deze code naar je ESP32
 * 3. Open de Serial Monitor (115200 baud)
 * 4. ESP32 zal automatisch scannen naar de Pi
 * 5. Je ziet de score updates verschijnen op het dashboard
 * 
 * LET OP: Deze setup vereist dat de Pi als GATT server werkt!
 * Check server/config.py: ENABLE_GATT_SERVER moet "1" zijn
 * 
 * ╔════════════════════════════════════════════════════════════╗
 * ║                      AANPASSINGEN                          ║
 * ╚════════════════════════════════════════════════════════════╝
 * 
 * Game naam wijzigen:
 *   Pas de variabele 'gameName' aan
 * 
 * Update interval wijzigen:
 *   Pas 'UPDATE_INTERVAL' aan (in milliseconden)
 * 
 * Start score wijzigen:
 *   Pas 'currentScore' aan
 * 
 * ╔════════════════════════════════════════════════════════════╗
 * ║                      DATA FORMATEN                         ║
 * ╚════════════════════════════════════════════════════════════╝
 * 
 * ESP32 -> Pi (RX via write):
 *   {"game_name": "MijnSpel", "score": 42, "timestamp": 12345}
 *   {"score": 50}  // Alleen score update
 * 
 * Pi -> ESP32 (TX via notify):
 *   {"command": "reset"}
 *   {"command": "set_game", "game_name": "NieuwSpel"}
 */
