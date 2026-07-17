#!/bin/bash
# SmartFan installer for Lenovo Legion 7 (Gen 10+)
# Requires: acpi_call kernel module

set -e

SCRIPTS="smartfan.sh workmode.sh turboon.sh turbooff.sh"
INSTALL_DIR="/usr/local/bin"
SERVICE_FILE="smartfan.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "=== SmartFan Installer for Legion 7 ==="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo ./install.sh"
    exit 1
fi

# Check for acpi_call
if ! modprobe acpi_call 2>/dev/null; then
    echo "ERROR: acpi_call kernel module not found."
    echo "Install it with: sudo apt install acpi-call-dkms"
    echo "Or build from: https://github.com/nix-community/acpi_call"
    exit 1
fi

# Install scripts
for script in $SCRIPTS; do
    dest="$INSTALL_DIR/${script%.sh}"
    cp "$script" "$dest"
    chmod +x "$dest"
    echo "Installed: $dest"
done

# Install systemd service
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
systemctl daemon-reload
systemctl enable smartfan.service
echo "Installed and enabled: smartfan.service"

# Ensure acpi_call loads on boot
if [ ! -f /etc/modules-load.d/acpi_call.conf ]; then
    echo "acpi_call" > /etc/modules-load.d/acpi_call.conf
    echo "Configured acpi_call to load on boot"
fi

echo ""
echo "=== Installation complete ==="
echo "Usage:"
echo "  workmode          - Interactive mode switcher (quiet/balanced/performance/extreme)"
echo "  smartfan status   - Show current fan status"
echo "  smartfan start quiet|balanced|performance|extreme"
echo "  turboon           - Force max fan speed"
echo "  turbooff          - Restore normal fan control"
echo ""
echo "The smartfan daemon starts automatically on boot in 'quiet' mode."
echo "Use 'workmode' to switch modes at any time."
