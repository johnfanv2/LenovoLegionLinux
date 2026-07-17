#!/bin/bash

ACPI_CALL="/proc/acpi/call"
if [ ! -f "$ACPI_CALL" ]; then
    modprobe acpi_call 2>/dev/null
fi

HWMON=""
for h in /sys/class/hwmon/hwmon*/name; do
    if [ "$(cat "$h" 2>/dev/null)" = "legion_hwmon" ]; then
        HWMON="${h%/name}"
        break
    fi
done

current=$(cat /sys/firmware/acpi/platform_profile)

sf_status="OFF"
if [ -f /tmp/smartfan.pid ] && kill -0 "$(cat /tmp/smartfan.pid 2>/dev/null)" 2>/dev/null; then
    sf_status="$(cat /tmp/smartfan_mode 2>/dev/null || echo 'unknown')"
fi

echo "╔══════════════════════════════════════╗"
echo "║     Legion Power Mode Switcher       ║"
echo "╠══════════════════════════════════════╣"
echo "║  Current mode: $current"
echo "║  Smart fan: $sf_status"
echo "╠══════════════════════════════════════╣"
echo "║  1) quiet        (silent, battery)   ║"
echo "║  2) balanced     (daily use)         ║"
echo "║  3) performance  (gaming/AI)         ║"
echo "║  4) extreme      (max cooling)       ║"
echo "║  5) turbo        (fans 100% NOW)     ║"
echo "║  6) fans off     (stop smart fan)    ║"
echo "╚══════════════════════════════════════╝"
echo ""
read -p "Select mode [1-6]: " choice

case $choice in
    1) wmi_arg="0x01"; fanmode="quiet"; label="quiet" ;;
    2) wmi_arg="0x02"; fanmode="balanced"; label="balanced" ;;
    3) wmi_arg="0x03"; fanmode="performance"; label="performance" ;;
    4) wmi_arg="0xE0"; fanmode="extreme"; label="extreme" ;;
    5)
        turboon
        exit 0
        ;;
    6)
        turbooff
        /usr/local/bin/smartfan stop
        exit 0
        ;;
    *) echo "Invalid choice"; exit 1 ;;
esac

# Set mode via WMI — changes EC mode and triggers LED
echo "\_SB_.GZFD.WMAA 0 0x2C {$wmi_arg, 0x00, 0x00, 0x00}" > "$ACPI_CALL"
cat "$ACPI_CALL" > /dev/null 2>&1
echo "Switched to: $label"

# If daemon already running, just update mode file — don't spawn another
if [ -f /tmp/smartfan.pid ] && kill -0 "$(cat /tmp/smartfan.pid)" 2>/dev/null; then
    echo "$fanmode" > /tmp/smartfan_mode
    echo "Smart fan mode updated to: $fanmode"
else
    /usr/local/bin/smartfan start "$fanmode"
fi

echo ""
echo "Temps:"
if [ -n "$HWMON" ]; then
    echo "  CPU: $(($(cat $HWMON/temp1_input) / 1000))°C"
    echo "  GPU: $(($(cat $HWMON/temp2_input) / 1000))°C"
    echo "  Fan1: $(cat $HWMON/fan1_input) RPM"
    echo "  Fan2: $(cat $HWMON/fan2_input) RPM"
fi
