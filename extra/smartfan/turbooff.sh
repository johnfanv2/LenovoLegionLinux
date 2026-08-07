#!/bin/bash
# Turbo fan OFF - restore EC automatic control (30% baseline)
if [ ! -f /proc/acpi/call ]; then
    sudo modprobe acpi_call 2>/dev/null
fi
# Set fan1 to 30% (0x1E = 30, * 100 = 3000 = 0x0BB8)
echo '\_SB_.GZFD.WMAE 0 0x12 {0x01, 0x00, 0x03, 0x04, 0xB8, 0x0B, 0x00, 0x00}' | sudo tee /proc/acpi/call > /dev/null
cat /proc/acpi/call > /dev/null
# Set fan2 to 30%
echo '\_SB_.GZFD.WMAE 0 0x12 {0x02, 0x00, 0x03, 0x04, 0xB8, 0x0B, 0x00, 0x00}' | sudo tee /proc/acpi/call > /dev/null
cat /proc/acpi/call > /dev/null
# Re-set thermal mode to performance to hand control back to EC
echo '\_SB_.GZFD.WMAA 0 0x2C {0x01, 0x00, 0x00, 0x00}' | sudo tee /proc/acpi/call > /dev/null
cat /proc/acpi/call > /dev/null
echo "Turbo fans OFF - EC auto control restored"
