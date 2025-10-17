# 🚀 START HIER - S3 Scoreboard BLE

## Voor de Raspberry Pi (BLE Server)

### 1. Installeer alles in één keer:
```bash
cd ~
git clone https://github.com/RickMageddon/S3-Scoreboard-BLE.git
cd S3-Scoreboard-BLE
chmod +x install.sh
./install.sh
```

### 2. Herstart je Pi:
```bash
sudo reboot
```

### 3. Start de server:
```bash
cd ~/S3-Scoreboard-BLE
python3 -m server.main
```

### 4. Open dashboard:
Ga naar: `http://[PI-IP-ADRES]:8000`

Vind je IP: `hostname -I`

---

## Voor ESP32 (BLE Clients)

### 1. Open Arduino IDE

### 2. Installeer library:
- Ga naar **Sketch** → **Include Library** → **Manage Libraries**
- Zoek: **ArduinoJson**
- Klik **Install**

### 3. Open voorbeeld:
- Open: `examples/esp32_client_simple.cpp`
- Kopieer de code naar een nieuwe sketch

### 4. Pas aan (optioneel):
```cpp
String gameName = "MijnSpel";    // Jouw spel naam
int currentScore = 0;             // Start score
```

### 5. Upload naar ESP32:
- Selecteer je ESP32 board
- Klik **Upload**

### 6. Open Serial Monitor (115200 baud):
Je ziet:
```
🔍 Scannen naar Pi server...
✅ Scoreboard server gevonden!
🎉 Volledig verbonden en klaar!
📤 Score update: 5
```

---

## ✅ Checklist

**Raspberry Pi:**
- [x] `install.sh` gedraaid
- [x] Pi herstart
- [x] Server draait (`python3 -m server.main`)
- [x] Dashboard open in browser

**ESP32:**
- [x] ArduinoJson library geïnstalleerd
- [x] Code geüpload
- [x] Serial Monitor open
- [x] Ziet "Verbonden" melding

**Beide werken:**
- [x] ESP32 verschijnt op dashboard
- [x] Score updates zijn zichtbaar
- [x] Elk apparaat heeft unieke kleur

---

## 🆘 Hulp nodig?

### Pi vindt geen Bluetooth:
```bash
sudo hciconfig hci0 up
sudo systemctl start bluetooth
```

### ESP32 vindt Pi niet:
- Check of Pi server draait
- Check Serial Monitor voor errors
- Probeer ESP32 opnieuw op te starten

### Dashboard laadt niet:
- Check Pi IP adres: `hostname -I`
- Check of server draait
- Probeer: `http://[PI-IP]:8000`

### Logs bekijken:
```bash
# Als je service installeert:
sudo journalctl -u s3-scoreboard -f
```

---

## 🎯 Volgende stappen

### Automatisch opstarten:
```bash
cd ~/S3-Scoreboard-BLE
chmod +x install_service.sh
sudo ./install_service.sh
```

Nu start de server automatisch bij elke boot!

### Meerdere ESP32's:
Upload dezelfde code naar meerdere ESP32's.
Elk apparaat verschijnt automatisch op het dashboard!

### Eigen game logica:
Pas de `loop()` functie aan in je ESP32 code:
```cpp
void loop() {
    // Jouw game logica hier
    currentScore = readSensorValue();
    sendScoreUpdate();
    delay(1000);
}
```

---

## 📚 Meer informatie

- Volledige README: `README.md`
- ESP32 voorbeelden: `examples/README.md`
- Troubleshooting: `README.md` → Troubleshooting sectie

---

**Veel succes! 🎉**
