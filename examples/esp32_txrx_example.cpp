/*
 * ESP32 TX/RX BLE Scoreboard Example
 * 
 * Vereenvoudigde communicatie met Raspberry Pi via één characteristic:
 * - TX: ESP32 stuurt data naar Pi (game naam, score updates)
 * - RX: ESP32 ontvangt commando's van Pi (reset, configuratie)
 * 
 * Data formaat: JSON voor bi-directionele communicatie
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <ArduinoJson.h>

// Service en Characteristic UUIDs (moeten matchen met Pi configuratie)
#define SERVICE_UUID        "c9b9a344-a062-4e55-a507-441c7e610e2c"
#define DATA_CHAR_UUID      "29f80071-9a06-426b-8c26-02ae5df749a4"

BLEServer* pServer = nullptr;
BLECharacteristic* pDataChar = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// Game state
String gameName = "MijnSpel";
int currentScore = 0;
unsigned long lastScoreUpdate = 0;

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("Pi verbonden!");
    };

    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("Pi losgekoppeld!");
    }
};

class MyDataCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        // RX: Data ontvangen van Pi
        String rxValue = pCharacteristic->getValue().c_str();
        
        if (rxValue.length() > 0) {
            Serial.println("RX van Pi: " + rxValue);
            
            // Parse JSON commando van Pi
            DynamicJsonDocument doc(1024);
            DeserializationError error = deserializeJson(doc, rxValue);
            
            if (!error) {
                // Handle commando's van Pi
                if (doc.containsKey("command")) {
                    String command = doc["command"];
                    
                    if (command == "reset") {
                        currentScore = 0;
                        Serial.println("Score gereset door Pi");
                        sendGameState(); // Bevestig reset
                    }
                    else if (command == "set_game") {
                        gameName = doc["game_name"].as<String>();
                        Serial.println("Game naam gewijzigd naar: " + gameName);
                        sendGameState(); // Bevestig wijziging
                    }
                }
            }
        }
    }
};

void setup() {
    Serial.begin(115200);
    Serial.println("ESP32 TX/RX BLE Scoreboard gestart");

    // BLE Device initialiseren
    BLEDevice::init("ESP32-Game-Device"); // Naam maakt niet uit voor beveiliging
    
    // BLE Server maken
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    // Service maken
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // TX/RX Data Characteristic maken
    pDataChar = pService->createCharacteristic(
                        DATA_CHAR_UUID,
                        BLECharacteristic::PROPERTY_READ   |
                        BLECharacteristic::PROPERTY_WRITE  |
                        BLECharacteristic::PROPERTY_NOTIFY
                      );

    pDataChar->setCallbacks(new MyDataCallbacks());
    pDataChar->addDescriptor(new BLE2902());

    // Service starten
    pService->start();

    // Advertising starten
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(false);
    pAdvertising->setMinPreferred(0x0);
    BLEDevice::startAdvertising();
    
    Serial.println("BLE Advertising gestart - wacht op Pi verbinding...");
    Serial.println("Service UUID: " + String(SERVICE_UUID));
    Serial.println("Data Char UUID: " + String(DATA_CHAR_UUID));
    
    // Stuur initiële game state
    sendGameState();
}

void sendGameState() {
    if (deviceConnected && pDataChar) {
        // TX: Stuur game state naar Pi (JSON formaat)
        DynamicJsonDocument doc(1024);
        doc["game_name"] = gameName;
        doc["score"] = currentScore;
        doc["timestamp"] = millis();
        
        String jsonString;
        serializeJson(doc, jsonString);
        
        pDataChar->setValue(jsonString.c_str());
        pDataChar->notify();
        
        Serial.println("TX naar Pi: " + jsonString);
    }
}

void sendScoreUpdate() {
    if (deviceConnected && pDataChar) {
        // TX: Stuur alleen score update (compact)
        DynamicJsonDocument doc(512);
        doc["score"] = currentScore;
        
        String jsonString;
        serializeJson(doc, jsonString);
        
        pDataChar->setValue(jsonString.c_str());
        pDataChar->notify();
        
        Serial.println("Score TX: " + String(currentScore));
    }
}

void loop() {
    // Simuleer score wijzigingen
    if (millis() - lastScoreUpdate > 5000) { // Elke 5 seconden
        currentScore += random(1, 10);
        sendScoreUpdate();
        lastScoreUpdate = millis();
    }
    
    // Handle verbinding wijzigingen
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); // Geef bluetooth stack tijd
        pServer->startAdvertising();
        Serial.println("Herstart advertising...");
        oldDeviceConnected = deviceConnected;
    }
    
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected;
        sendGameState(); // Stuur volledige state bij nieuwe verbinding
    }
    
    delay(100);
}

/*
 * Data formaten:
 * 
 * ESP32 -> Pi (TX):
 * {"game_name": "MijnSpel", "score": 42, "timestamp": 12345}
 * {"score": 50}  // Alleen score update
 * 
 * Pi -> ESP32 (RX):
 * {"command": "reset"}
 * {"command": "set_game", "game_name": "NieuwSpel"}
 * 
 * Libraries vereist:
 * - ArduinoJson (installeer via Library Manager)
 * - ESP32 BLE Arduino (ingebouwd)
 */