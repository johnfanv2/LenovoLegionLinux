#!/bin/bash
# Smart Fan Daemon for Legion 7 Gen 10
# Uses LECR(0xD1) via acpi_call for direct fan control

MODEFILE="/tmp/smartfan_mode"
PIDFILE="/tmp/smartfan.pid"
ACPI_CALL="/proc/acpi/call"
STOPFILE="/tmp/smartfan_stop"

if [ ! -f "$ACPI_CALL" ]; then
    modprobe acpi_call 2>/dev/null
    if [ ! -f "$ACPI_CALL" ]; then
        echo "Error: acpi_call module not available"
        exit 1
    fi
fi

get_profile() {
    case "$1" in
        quiet)
            TEMP_LOW=75; TEMP_MED=85; TEMP_HIGH=92
            FAN_LOW=20; FAN_MED=35; FAN_HIGH=50; FAN_MAX=70
            RAMP_DOWN_DELAY=3
            ;;
        balanced)
            TEMP_LOW=70; TEMP_MED=80; TEMP_HIGH=90
            FAN_LOW=30; FAN_MED=45; FAN_HIGH=55; FAN_MAX=60
            RAMP_DOWN_DELAY=3
            ;;
        performance)
            TEMP_LOW=60; TEMP_MED=70; TEMP_HIGH=80
            FAN_LOW=45; FAN_MED=60; FAN_HIGH=75; FAN_MAX=85
            RAMP_DOWN_DELAY=3
            ;;
        extreme)
            TEMP_LOW=50; TEMP_MED=60; TEMP_HIGH=70
            FAN_LOW=60; FAN_MED=75; FAN_HIGH=90; FAN_MAX=100
            RAMP_DOWN_DELAY=3
            ;;
    esac
}

set_fan_speed() {
    local pct=$1
    if [ "$pct" -le 0 ]; then
        pct=20
    fi
    local val=$((pct * 100))
    local b0=$(printf '0x%02x' $((val & 0xFF)))
    local b1=$(printf '0x%02x' $(( (val >> 8) & 0xFF)))
    local b2=$(printf '0x%02x' $(( (val >> 16) & 0xFF)))
    local b3=$(printf '0x%02x' $(( (val >> 24) & 0xFF)))
    echo "\_SB_.GZFD.WMAE 0 0x12 {0x01, 0x00, 0x03, 0x04, $b0, $b1, $b2, $b3}" > "$ACPI_CALL"
    cat "$ACPI_CALL" > /dev/null 2>&1
    echo "\_SB_.GZFD.WMAE 0 0x12 {0x02, 0x00, 0x03, 0x04, $b0, $b1, $b2, $b3}" > "$ACPI_CALL"
    cat "$ACPI_CALL" > /dev/null 2>&1
}

TEMP_HISTORY=""
TEMP_SAMPLES=8
RAMP_UP_COUNT=0
RAMP_UP_NEEDED=3

get_max_temp() {
    local cpu_temp=$(cat /sys/class/hwmon/hwmon9/temp1_input 2>/dev/null)
    local gpu_temp=$(cat /sys/class/hwmon/hwmon9/temp2_input 2>/dev/null)
    cpu_temp=$((cpu_temp / 1000))
    gpu_temp=$((gpu_temp / 1000))
    local raw
    if [ "$cpu_temp" -gt "$gpu_temp" ]; then
        raw=$cpu_temp
    else
        raw=$gpu_temp
    fi
    if [ "$raw" -gt 90 ]; then
        raw=90
    fi
    TEMP_HISTORY="$TEMP_HISTORY $raw"
    local count=$(echo $TEMP_HISTORY | wc -w)
    if [ "$count" -gt "$TEMP_SAMPLES" ]; then
        TEMP_HISTORY=$(echo $TEMP_HISTORY | cut -d' ' -f2-)
    fi
    local sum=0
    for t in $TEMP_HISTORY; do
        sum=$((sum + t))
    done
    count=$(echo $TEMP_HISTORY | wc -w)
    echo $((sum / count))
}

get_target_pct() {
    local temp=$1
    if [ "$temp" -le "$TEMP_LOW" ]; then
        echo "$FAN_LOW"
    elif [ "$temp" -le "$TEMP_MED" ]; then
        local range=$((TEMP_MED - TEMP_LOW))
        local offset=$((temp - TEMP_LOW))
        echo $(( FAN_LOW + (FAN_MED - FAN_LOW) * offset / range ))
    elif [ "$temp" -le "$TEMP_HIGH" ]; then
        local range=$((TEMP_HIGH - TEMP_MED))
        local offset=$((temp - TEMP_MED))
        echo $(( FAN_MED + (FAN_HIGH - FAN_MED) * offset / range ))
    else
        echo "$FAN_MAX"
    fi
}

stop_daemon() {
    # Signal any running daemon to stop via stop file
    touch "$STOPFILE"
    # Also kill by PID file as backup
    if [ -f "$PIDFILE" ]; then
        local oldpid=$(cat "$PIDFILE")
        kill "$oldpid" 2>/dev/null
        sleep 1
        kill -9 "$oldpid" 2>/dev/null
    fi
    # Wait for it to actually die
    sleep 1
    rm -f "$PIDFILE" "$STOPFILE"
    # Restore EC auto
    set_fan_speed 0
}

run_daemon() {
    local mode="$1"
    echo "$$" > "$PIDFILE"
    echo "$mode" > "$MODEFILE"
    chmod 666 "$MODEFILE"
    rm -f "$STOPFILE"

    get_profile "$mode"

    local current_pct=$FAN_LOW
    local down_count=0
    local LOG="/tmp/smartfan.log"
    echo "$(date): daemon started, mode=$mode pid=$$" > "$LOG"
    set_fan_speed "$current_pct"

    trap 'set_fan_speed 0; rm -f "$PIDFILE"; echo "$(date): stopped" >> "$LOG"; exit 0' TERM INT

    while true; do
        # Check if we should stop
        if [ -f "$STOPFILE" ]; then
            set_fan_speed 0
            rm -f "$PIDFILE"
            echo "$(date): stopped by signal" >> "$LOG"
            exit 0
        fi

        # Re-read mode in case it was changed
        if [ -f "$MODEFILE" ]; then
            local new_mode=$(cat "$MODEFILE")
            if [ "$new_mode" != "$mode" ]; then
                mode="$new_mode"
                get_profile "$mode"
                # Pre-fill history with current temp to avoid spike reaction
                TEMP_HISTORY=""
                local fill_temp=$(cat /sys/class/hwmon/hwmon9/temp1_input 2>/dev/null)
                fill_temp=$((fill_temp / 1000))
                if [ "$fill_temp" -gt 90 ]; then fill_temp=90; fi
                for i in $(seq 1 $TEMP_SAMPLES); do
                    TEMP_HISTORY="$TEMP_HISTORY $fill_temp"
                done
                current_pct=$FAN_LOW
                down_count=0
                RAMP_UP_COUNT=0
                set_fan_speed "$current_pct"
                echo "$(date): mode changed to $mode, reset fans" >> "$LOG"
            fi
        fi

        local temp=$(get_max_temp)
        local target_pct=$(get_target_pct "$temp")

        if [ "$target_pct" -gt "$current_pct" ]; then
            RAMP_UP_COUNT=$((RAMP_UP_COUNT + 1))
            if [ "$RAMP_UP_COUNT" -ge "$RAMP_UP_NEEDED" ]; then
                current_pct=$target_pct
                set_fan_speed "$current_pct"
                echo "$(date): temp=${temp}C -> ${current_pct}%" >> "$LOG"
                RAMP_UP_COUNT=0
            fi
            down_count=0
        elif [ "$target_pct" -lt "$current_pct" ]; then
            RAMP_UP_COUNT=0
            down_count=$((down_count + 1))
            if [ "$temp" -le "$((TEMP_LOW - 5))" ] && [ "$down_count" -ge 3 ]; then
                current_pct=$target_pct
                set_fan_speed "$current_pct"
                echo "$(date): temp=${temp}C snap to ${current_pct}%" >> "$LOG"
                down_count=0
            elif [ "$down_count" -ge "$RAMP_DOWN_DELAY" ]; then
                current_pct=$((current_pct - 10))
                if [ "$current_pct" -lt "$target_pct" ]; then
                    current_pct=$target_pct
                fi
                set_fan_speed "$current_pct"
                echo "$(date): temp=${temp}C ramp DOWN to ${current_pct}%" >> "$LOG"
                down_count=$((RAMP_DOWN_DELAY - 2))
            fi
        else
            down_count=0
            RAMP_UP_COUNT=0
        fi

        sleep 2
    done
}

case "$1" in
    start)
        mode="${2:-performance}"
        stop_daemon
        echo "Starting smart fan daemon in '$mode' mode..."
        run_daemon "$mode" &
        disown
        echo "Smart fan running (PID: $!)"
        ;;
    stop)
        echo "Stopping smart fan daemon..."
        stop_daemon
        echo "Fans restored to EC auto control"
        ;;
    mode)
        if [ -z "$2" ]; then
            echo "Current mode: $(cat $MODEFILE 2>/dev/null || echo 'not running')"
        else
            echo "$2" > "$MODEFILE"
            echo "Mode changed to: $2 (takes effect within 2s)"
        fi
        ;;
    status)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
            echo "Smart fan: RUNNING (PID $(cat $PIDFILE))"
            echo "Mode: $(cat $MODEFILE 2>/dev/null)"
            echo "CPU: $(($(cat /sys/class/hwmon/hwmon9/temp1_input) / 1000))°C"
            echo "GPU: $(($(cat /sys/class/hwmon/hwmon9/temp2_input) / 1000))°C"
            echo "Fan1: $(cat /sys/class/hwmon/hwmon9/fan1_input) RPM"
            echo "Fan2: $(cat /sys/class/hwmon/hwmon9/fan2_input) RPM"
        else
            echo "Smart fan: NOT RUNNING"
        fi
        ;;
    *)
        echo "Usage: smartfan {start [mode]|stop|mode [name]|status}"
        echo "Modes: quiet, balanced, performance, extreme"
        ;;
esac
