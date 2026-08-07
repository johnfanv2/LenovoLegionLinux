#!/bin/bash
# Turbo fan ON - set both fans to maximum speed
if [ ! -f /proc/acpi/call ]; then
    sudo modprobe acpi_call 2>/dev/null
fi
echo '\_SB_.GZFD.WMAE 0 0x12 {0x01, 0x00, 0x03, 0x04, 0x10, 0x27, 0x00, 0x00}' | sudo tee /proc/acpi/call > /dev/null
cat /proc/acpi/call > /dev/null
echo '\_SB_.GZFD.WMAE 0 0x12 {0x02, 0x00, 0x03, 0x04, 0x10, 0x27, 0x00, 0x00}' | sudo tee /proc/acpi/call > /dev/null
cat /proc/acpi/call > /dev/null
echo "Turbo fans ON - full speed"
