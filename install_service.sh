#!/bin/bash
# Installeer S3 Scoreboard als systemd service
# Draait automatisch bij opstarten

set -e

echo "🔧 Installeren van systemd service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Dit script moet als root draaien"
    echo "   Gebruik: sudo ./install_service.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "📁 Installatie directory: $SCRIPT_DIR"
echo "👤 Gebruiker: $ACTUAL_USER"

# Create systemd service file
cat > /etc/systemd/system/s3-scoreboard.service << EOF
[Unit]
Description=S3 Scoreboard BLE Server
After=network.target bluetooth.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 -m server.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Bluetooth capabilities
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service bestand aangemaakt: /etc/systemd/system/s3-scoreboard.service"

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo "🚀 Service inschakelen en starten..."
systemctl enable s3-scoreboard
systemctl start s3-scoreboard

echo ""
echo "✅ Service geïnstalleerd en gestart!"
echo ""
echo "📋 Handige commando's:"
echo "  Status bekijken:  sudo systemctl status s3-scoreboard"
echo "  Logs bekijken:    sudo journalctl -u s3-scoreboard -f"
echo "  Herstarten:       sudo systemctl restart s3-scoreboard"
echo "  Stoppen:          sudo systemctl stop s3-scoreboard"
echo "  Uitschakelen:     sudo systemctl disable s3-scoreboard"
echo ""
