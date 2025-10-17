/*
 * ESP32 BLE Server - S3 Scoreboard
 * 
 * ESP32 werkt als BLE PERIPHERAL (server) waar de Raspberry Pi mee verbindt.
 * De Pi (BLE central/client) scant naar ESP32's en ontvangt de score data.
 * 
 * Architectuur:
 * - ESP32 = BLE Server/Peripheral (adverteert, heeft characteristics)
 * - Raspberry Pi = BLE Client/Central (scant, verbindt, ontvangt data)
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
 * - ESP32 adverteert als BLE server met SERVICE_UUID
 * - Raspberry Pi vindt en verbindt met ESP32
 * - ESP32 stuurt score updates via notify
 * - Pi ontvangt en toont op dashboard
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <ArduinoJson.h>

// UUIDs moeten matchen met Pi configuratie
#define SERVICE_UUID        "c9b9a344-a062-4e55-a507-441c7e610e2c"
#define RX_CHAR_UUID        "29f80071-9a06-426b-8c26-02ae5df749a4"  // Pi ontvangt (ESP32 -> Pi)
#define TX_CHAR_UUID        "a43359d2-e50e-43c9-ad86-b77ee5c6524e"  // Pi stuurt (Pi -> ESP32)

// Game configuratie
String gameName = "ESP32 Test Game";
int currentScore = 0;
unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 5000; // Update elke 5 seconden

// BLE objecten
BLEServer* pServer = nullptr;
BLECharacteristic* pRxChar = nullptr;
BLECharacteristic* pTxChar = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// Server callbacks voor verbindingsstatus
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("� Pi verbonden!");
    };

    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("� Pi losgekoppeld!");
    }
};

// TX Characteristic callback (Pi -> ESP32)
class MyTxCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        String rxValue = pCharacteristic->getValue().c_str();
        
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
};

// Stuur volledige game state naar Pi
void sendGameState() {
    if (!deviceConnected || pRxChar == nullptr) {
        return;
    }

    DynamicJsonDocument doc(1024);
    doc["game_name"] = gameName;
    doc["score"] = currentScore;
    doc["timestamp"] = millis();
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    pRxChar->setValue(jsonString.c_str());
    pRxChar->notify();
    
    Serial.println("📤 Volledige state verzonden: " + jsonString);
}

// Stuur alleen score update naar Pi
void sendScoreUpdate() {
    if (!deviceConnected || pRxChar == nullptr) {
        return;
    }

    DynamicJsonDocument doc(512);
    doc["score"] = currentScore;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    pRxChar->setValue(jsonString.c_str());
    pRxChar->notify();
    
    Serial.println("📤 Score update: " + String(currentScore));
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n\n╔════════════════════════════════════════╗");
    Serial.println("║  ESP32 BLE Server - S3 Scoreboard    ║");
    Serial.println("╚════════════════════════════════════════╝\n");
    
    Serial.println("Game: " + gameName);
    Serial.println("Startwaarde score: " + String(currentScore));
    Serial.println();

    // Initialiseer BLE Device
    BLEDevice::init("ESP32-Scoreboard");
    
    // Maak BLE Server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    // Maak BLE Service
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // RX Characteristic: ESP32 stuurt data naar Pi (notify)
    pRxChar = pService->createCharacteristic(
                        RX_CHAR_UUID,
                        BLECharacteristic::PROPERTY_READ   |
                        BLECharacteristic::PROPERTY_WRITE  |
                        BLECharacteristic::PROPERTY_NOTIFY
                      );
    pRxChar->addDescriptor(new BLE2902());

    // TX Characteristic: Pi stuurt commando's naar ESP32 (write)
    pTxChar = pService->createCharacteristic(
                        TX_CHAR_UUID,
                        BLECharacteristic::PROPERTY_READ   |
                        BLECharacteristic::PROPERTY_WRITE
                      );
    pTxChar->setCallbacks(new MyTxCallbacks());
    pTxChar->addDescriptor(new BLE2902());

    // Start service
    pService->start();

    // Start advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(false);
    pAdvertising->setMinPreferred(0x0);  // iOS connection fix
    BLEDevice::startAdvertising();
    
    Serial.println("� BLE Server gestart - wacht op Pi verbinding...");
    Serial.println("Service UUID: " + String(SERVICE_UUID));
    Serial.println("RX Char UUID: " + String(RX_CHAR_UUID) + " (ESP32 -> Pi)");
    Serial.println("TX Char UUID: " + String(TX_CHAR_UUID) + " (Pi -> ESP32)");
    Serial.println();
    
    // Stuur initiële game state
    sendGameState();
}

void loop() {
    // Als disconnected, herstart advertising
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); // Geef BLE stack tijd om op te schonen
        pServer->startAdvertising();
        Serial.println("📡 Herstart advertising - wacht op verbinding...");
        oldDeviceConnected = deviceConnected;
    }
    
    // Als nieuwe verbinding
    if (deviceConnected && !oldDeviceConnected) {
        Serial.println("✅ Pi verbonden!");
        oldDeviceConnected = deviceConnected;
    }
    
    // Periodiek score updates sturen wanneer verbonden
    if (deviceConnected) {
        // Stuur periodieke score updates
        if (millis() - lastUpdate > UPDATE_INTERVAL) {
            // Simuleer score wijziging
            currentScore += random(1, 11);
            sendScoreUpdate();
            lastUpdate = millis();
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
