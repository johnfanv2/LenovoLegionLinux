#!/bin/bash
# Turbo fan OFF - return fans to firmware/daemon control
if [ ! -f /proc/acpi/call ]; then
    sudo modprobe acpi_call 2>/dev/null
fi
# smartfan restore re-asserts the current power mode (not the hardcoded
# quiet value this script used to write) and leaves a 30% baseline while
# the EC re-takes the fans.
/usr/local/bin/smartfan restore
echo "Turbo fans OFF - EC auto control restored"