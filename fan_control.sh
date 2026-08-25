#!/bin/bash

# Legion Fan Control Script
# Usage: ./fan_control.sh [enable|disable|status]

LEGION_SYS="/sys/module/legion_laptop/drivers/platform:legion"

find_base() {
	local base
	for base in "$LEGION_SYS/PNP0C09:00" "$LEGION_SYS/legion"; do
		[ -d "$base" ] && printf '%s\n' "$base" && return 0
	done
	return 1
}

set_attr() {
	echo "$2" | sudo tee "$1/$3" > /dev/null
}

read_attr() {
	cat "$1/$2" 2>/dev/null || echo "n/a"
}

show_status() {
	local base=$1
	if command -v sensors > /dev/null 2>&1; then
		sensors -u | grep -A 20 "legion_hwmon" | head -25
	fi
	echo ""
	echo "🎛️ Current Settings:"
	echo "Fan Full Speed: $(read_attr "$base" fan_fullspeed)"
	echo "Fan Max Speed:  $(read_attr "$base" fan_maxspeed)"
	echo "Power Mode:     $(read_attr "$base" powermode)"
}

BASE=$(find_base) || {
	echo "Error: legion-laptop sysfs interface not found (is the module loaded?)"
	exit 1
}

case "$1" in
	"enable")
		echo "🔥 Enabling high-performance fan mode..."
		set_attr "$BASE" 1 fan_fullspeed
		set_attr "$BASE" 1 fan_maxspeed
		echo "✅ High-performance fan mode enabled!"
		show_status "$BASE"
		;;
	"disable")
		echo "🌡️ Disabling high-performance fan mode..."
		set_attr "$BASE" 0 fan_fullspeed
		set_attr "$BASE" 0 fan_maxspeed
		echo "✅ Automatic fan control restored!"
		show_status "$BASE"
		;;
	"status")
		echo "📊 Current Legion Fan Status:"
		echo "================================"
		show_status "$BASE"
		;;
	*)
		echo "Legion Fan Control Script"
		echo "========================"
		echo "Usage: $0 [enable|disable|status]"
		echo ""
		echo "Commands:"
		echo "  enable  - Force maximum fan speed"
		echo "  disable - Return to automatic fan curve control"
		echo "  status  - Show current fan speeds and settings"
		echo ""
		echo "Note: Requires sudo privileges for enable/disable."
		;;
esac
