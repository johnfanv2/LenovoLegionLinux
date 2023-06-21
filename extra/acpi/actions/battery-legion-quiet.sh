#!/bin/sh

ADP0_connected=$(cat /sys/class/power_supply/ADP0/online)

if [[ $ADP0_connected -eq 1 ]]; then
	/bin/echo balanced > /sys/firmware/acpi/platform_profile
else
	/bin/echo quiet > /sys/firmware/acpi/platform_profile
fi

/bin/systemctl restart legion-linux #systemd restart on profile change

