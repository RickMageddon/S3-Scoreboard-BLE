#!/bin/bash
# S3 Scoreboard BLE - Eenvoudige installatie voor Raspberry Pi
# Geen virtual environment - directe systeeminstallatie

set -e

echo "╔════════════════════════════════════════════════════╗"
echo "║   S3 Scoreboard BLE - Raspberry Pi Installatie   ║"
echo "║   Pi als BLE Server - ESP32 clients verbinden     ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Draai dit script NIET als root/sudo"
    echo "   Het script vraagt zelf om sudo waar nodig"
    exit 1
fi

echo "📦 Stap 1: Systeem packages installeren..."
sudo apt-get update
sudo apt-get install -y \
    bluetooth \
    bluez \
    python3-pip \
    python3-dev \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    libdbus-1-dev \
    libglib2.0-dev

echo ""
echo "🐍 Stap 2: Python packages installeren (systeem-breed)..."
sudo pip3 install --break-system-packages \
    fastapi==0.111.0 \
    uvicorn[standard]==0.30.1 \
    bleak==0.22.2 \
    orjson==3.10.6 \
    python-dotenv==1.0.1 \
    pydbus==0.6.0

echo ""
echo "🔧 Stap 3: Configuratie aanmaken..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# S3 Scoreboard BLE - Raspberry Pi als BLE Server

# Service UUID
SCOREBOARD_SERVICE_UUID=c9b9a344-a062-4e55-a507-441c7e610e2c

# Characteristic UUIDs
RX_CHAR_UUID=29f80071-9a06-426b-8c26-02ae5df749a4
TX_CHAR_UUID=a43359d2-e50e-43c9-ad86-b77ee5c6524e

# BLE Server mode (Pi als peripheral)
ENABLE_ADVERTISING=1
ENABLE_GATT_SERVER=1
ADVERTISING_NAME=S3-Scoreboard

# Beveiliging
DISABLE_AUTHENTICATION=1
STRICT_SERVICE_FILTER=0

# Web server
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO
EOF
    echo "✅ .env bestand aangemaakt"
else
    echo "ℹ️  .env bestaat al, niet overschreven"
fi

echo ""
echo "👤 Stap 4: Bluetooth rechten instellen..."
sudo usermod -a -G bluetooth $USER

echo ""
echo "📡 Stap 5: Bluetooth inschakelen..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
sudo hciconfig hci0 up

echo ""
echo "🎉 Installatie voltooid!"
echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║              VOLGENDE STAPPEN                      ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  Herstart je Pi (nodig voor Bluetooth groep):"
echo "    sudo reboot"
echo ""
echo "2️⃣  Start de server na herstart:"
echo "    cd ~/S3-Scoreboard-BLE"
echo "    python3 -m server.main"
echo ""
echo "3️⃣  Open dashboard in browser:"
echo "    http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "4️⃣  ESP32's verbinden automatisch via BLE!"
echo ""
echo "💡 Tip: Om als systemd service te draaien, run:"
echo "    sudo ./install_service.sh"
echo ""
