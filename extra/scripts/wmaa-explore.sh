#!/bin/bash
# WMAA sub-command explorer for Lenovo Legion firmwares.
# Iterates GameZone WMI WMAA(0, mid, val) sub-commands, captures fan response,
# and produces a compatibility report. Use this on un-tested firmwares to find
# fan-unlock-equivalent commands.
#
# DISCOVERED SO FAR (see issue #429 / PR #443):
#   KWCN54WW (Legion Pro 7 16IRX8H):
#     WMAA(0, 0x0D, 1) → fans 4400 → 7100 RPM (unlock — exposed as fan_unlock)
#     WMAA(0, 0x16, 1) → fans 4400 → 6700 RPM (decays to ~6000)
#     WMAA(0, 0x19, 1) → fans 4400 → 5600 RPM (decays to ~4900)
#
# Goal: build a per-firmware compat matrix to cover all Legion 2022/2023
# models in the upstream driver.
#
# Safety:
#   - Skips known-destructive sub-commands (0xE0, 0xFF — see README in PR #443
#     comments for context).
#   - Each test reverses with WMAA(0, mid, 0) before the next.
#   - Aborts immediately if fans drop below baseline (anti-tamper triggered).

set -u

GAMEZONE=/sys/devices/pci0000:00/0000:00:1f.0/PNP0C09:00/gamezone_method
HWMON=
for d in /sys/class/hwmon/hwmon*/; do
    [ "$(cat "${d}name" 2>/dev/null)" = "legion_hwmon" ] && HWMON="${d%/}" && break
done

if [ -z "$HWMON" ] || [ ! -w "$GAMEZONE" ]; then
    echo "ERROR: legion-laptop driver not loaded or not patched. Need gamezone_method sysfs."
    echo "Apply patches from https://github.com/johnfanv2/LenovoLegionLinux issue #429"
    exit 1
fi

readonly REPORT=/tmp/wmaa-compat-report.txt
> "$REPORT"

echo "=== WMAA explorer for $(cat /sys/class/dmi/id/product_name) BIOS=$(cat /sys/class/dmi/id/bios_version) ==="
echo "Logging to $REPORT"
echo

read_fans() { echo "$(cat $HWMON/fan1_input)/$(cat $HWMON/fan2_input)"; }
read_cpu() { awk '/^Package id 0:/{gsub(/[+°C]/,"",$4);print int($4);exit}' < <(sensors coretemp-isa-0000 2>/dev/null); }

baseline_fans=$(read_fans)
echo "Baseline (idle): fans=$baseline_fans cpu=$(read_cpu)°C" | tee -a "$REPORT"
echo

# Generate light load so EC actually wants to spin fans
stress-ng --cpu 16 --timeout 240s > /dev/null 2>&1 &
STRESS=$!
trap "kill $STRESS 2>/dev/null; echo 0x0D:0x00 > $GAMEZONE 2>/dev/null" EXIT INT TERM
sleep 8
load_fans=$(read_fans)
echo "Under light load (16 CPUs): fans=$load_fans cpu=$(read_cpu)°C" | tee -a "$REPORT"
echo

# DANGEROUS sub-commands to skip — known to either crash, drop fans, or
# require a multi-step protocol that we shouldn't trigger blind.
DANGER_LIST="0xE0 0xFF 0x8C 0xCD"
is_dangerous() {
    local v=$1
    for d in $DANGER_LIST; do [ "$v" = "$d" ] && return 0; done
    return 1
}

echo "Testing WMAA(0, mid, 1) for mid in 0x00..0x40, then back to 0..." | tee -a "$REPORT"
echo "(skipping known-destructive: $DANGER_LIST)" | tee -a "$REPORT"
echo

for n in $(seq 0 64); do hex=$(printf "0x%02X" $n)
    if is_dangerous "$hex"; then
        printf "  %s  SKIPPED (destructive)\n" "$hex" | tee -a "$REPORT"
        continue
    fi
    echo "$hex:0x01" > "$GAMEZONE" 2>/dev/null
    sleep 3
    fans=$(read_fans)
    cpu=$(read_cpu)
    f1=${fans%/*}
    base1=${load_fans%/*}
    delta=$((f1 - base1))
    flag=""
    [ $delta -gt 500 ] && flag="🚀 RAISES FANS"
    [ $delta -lt -500 ] && { flag="⚠ DROPS FANS"; }
    printf "  %s  fans=%s  cpu=%s°C  delta=%+d  %s\n" "$hex" "$fans" "$cpu" "$delta" "$flag" | tee -a "$REPORT"
    # Always disable before next to avoid stacking effects
    echo "$hex:0x00" > "$GAMEZONE" 2>/dev/null
    sleep 1
    # Abort if anti-tamper triggered (fans below baseline despite load)
    cur_f1=$(cut -d/ -f1 <<< "$(read_fans)")
    if [ "$cur_f1" -lt "$((${baseline_fans%/*} - 200))" ]; then
        echo "ABORT: fans below baseline ($cur_f1 < ${baseline_fans%/*}). Possible anti-tamper, stopping." | tee -a "$REPORT"
        break
    fi
done

kill $STRESS 2>/dev/null
echo "$REPORT"
echo
echo "=== Report saved to $REPORT ==="
echo "If you found new sub-commands that raise fans, please post the report"
echo "to https://github.com/johnfanv2/LenovoLegionLinux/pull/443"
