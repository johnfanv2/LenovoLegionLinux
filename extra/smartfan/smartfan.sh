#!/bin/bash
# Smart Fan Daemon for Legion 7 Gen 10
# Uses LECR(0xD1) via acpi_call for direct fan control

MODEFILE="/tmp/smartfan_mode"
PIDFILE="/tmp/smartfan.pid"
ACPI_CALL="/proc/acpi/call"
STOPFILE="/tmp/smartfan_stop"
LOG="/tmp/smartfan.log"
#DEBUG=1  # Set to 1 for verbose logging

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" >> "$LOG"
    [ "$DEBUG" = "1" ] && echo "$1"
}

# Check for acpi_call
if [ ! -f "$ACPI_CALL" ]; then
    modprobe acpi_call 2>/dev/null
    sleep 1
    if [ ! -f "$ACPI_CALL" ]; then
        echo "Error: acpi_call module not available"
        echo "Try: sudo modprobe acpi_call"
        exit 1
    fi
fi

# Find correct hwmon path
find_hwmon() {
    for hwmon in /sys/class/hwmon/hwmon*; do
        if [ -f "$hwmon/name" ]; then
            name=$(cat "$hwmon/name")
            if [[ "$name" == *"coretemp"* ]] || [[ "$name" == *"k10temp"* ]] || [[ "$name" == *"zenpower"* ]]; then
                CPU_HWMON="$hwmon"
                log "Found CPU hwmon: $hwmon ($name)"
            fi
            if [[ "$name" == *"amdgpu"* ]] || [[ "$name" == *"nouveau"* ]]; then
                GPU_HWMON="$hwmon"
                log "Found GPU hwmon: $hwmon ($name)"
            fi
        fi
    done
    
    # Fallback to hwmon9 if not found
    [ -z "$CPU_HWMON" ] && CPU_HWMON="/sys/class/hwmon/hwmon9"
    [ -z "$GPU_HWMON" ] && GPU_HWMON="/sys/class/hwmon/hwmon9"
}

get_profile() {
    case "$1" in
        quiet)
            # 10 temperature points for smooth curve
            TEMP_POINTS="40 50 60 65 70 75 80 85 90 95"
            FAN_POINTS="20 20 20 25 30 35 40 50 60 70"
            RAMP_DOWN_DELAY=3
            ;;
        balanced)
            TEMP_POINTS="40 50 60 65 70 75 80 85 90 95"
            FAN_POINTS="25 25 30 35 40 45 50 55 60 70"
            RAMP_DOWN_DELAY=3
            ;;
        performance)
            TEMP_POINTS="40 50 60 65 70 75 80 85 90 95"
            FAN_POINTS="35 40 45 50 55 60 65 75 85 95"
            RAMP_DOWN_DELAY=3
            ;;
        extreme)
            TEMP_POINTS="40 50 60 65 70 75 80 85 90 95"
            FAN_POINTS="50 60 65 70 75 80 85 90 95 100"
            RAMP_DOWN_DELAY=3
            ;;
        *)
            log "Invalid profile: $1, using performance"
            TEMP_POINTS="40 50 60 65 70 75 80 85 90 95"
            FAN_POINTS="35 40 45 50 55 60 65 75 85 95"
            RAMP_DOWN_DELAY=3
            ;;
    esac
}

set_fan_speed() {
    local pct=$1
    # Ensure valid range
    if [ "$pct" -lt 20 ]; then pct=20; fi
    if [ "$pct" -gt 100 ]; then pct=100; fi
    
    local val=$((pct * 100))
    local b0=$(printf '0x%02x' $((val & 0xFF)))
    local b1=$(printf '0x%02x' $(((val >> 8) & 0xFF)))
    local b2=$(printf '0x%02x' $(((val >> 16) & 0xFF)))
    local b3=$(printf '0x%02x' $(((val >> 24) & 0xFF)))
    
    # Try both fan channels
    echo "\_SB_.GZFD.WMAE 0 0x12 {0x01, 0x00, 0x03, 0x04, $b0, $b1, $b2, $b3}" > "$ACPI_CALL" 2>/dev/null
    sleep 0.1
    echo "\_SB_.GZFD.WMAE 0 0x12 {0x02, 0x00, 0x03, 0x04, $b0, $b1, $b2, $b3}" > "$ACPI_CALL" 2>/dev/null
}

get_max_temp() {
    local cpu_temp=0
    local gpu_temp=0
    local cpu_file="$CPU_HWMON/temp1_input"
    local gpu_file="$GPU_HWMON/temp1_input"
    
    # Try different temp files
    [ -f "$cpu_file" ] && cpu_temp=$(cat "$cpu_file" 2>/dev/null)
    [ -z "$cpu_temp" ] && [ -f "$GPU_HWMON/temp2_input" ] && cpu_temp=$(cat "$GPU_HWMON/temp2_input" 2>/dev/null)
    
    [ -f "$gpu_file" ] && gpu_temp=$(cat "$gpu_file" 2>/dev/null)
    [ -z "$gpu_temp" ] && [ -f "$CPU_HWMON/temp2_input" ] && gpu_temp=$(cat "$CPU_HWMON/temp2_input" 2>/dev/null)
    
    # Convert to Celsius
    cpu_temp=$((cpu_temp / 1000))
    gpu_temp=$((gpu_temp / 1000))
    
    # Clamp to reasonable range
    [ "$cpu_temp" -gt 100 ] && cpu_temp=100
    [ "$gpu_temp" -gt 100 ] && gpu_temp=100
    [ "$cpu_temp" -lt 0 ] && cpu_temp=0
    [ "$gpu_temp" -lt 0 ] && gpu_temp=0
    
    local raw=$cpu_temp
    [ "$gpu_temp" -gt "$raw" ] && raw=$gpu_temp
    
    echo "$raw"
}

get_target_pct() {
    local temp=$1
    local temps=($TEMP_POINTS)
    local fans=($FAN_POINTS)
    local target=${fans[0]}
    
    # If below first point, use first fan speed
    if [ "$temp" -le "${temps[0]}" ]; then
        echo "${fans[0]}"
        return
    fi
    
    # If above last point, use last fan speed
    local last_idx=$((${#temps[@]} - 1))
    if [ "$temp" -ge "${temps[$last_idx]}" ]; then
        echo "${fans[$last_idx]}"
        return
    fi
    
    # Find which two points we're between and interpolate
    for ((i=0; i<last_idx; i++)); do
        local t1=${temps[$i]}
        local t2=${temps[$((i+1))]}
        local f1=${fans[$i]}
        local f2=${fans[$((i+1))]}
        
        if [ "$temp" -ge "$t1" ] && [ "$temp" -le "$t2" ]; then
            # Linear interpolation between points
            local temp_range=$((t2 - t1))
            local temp_offset=$((temp - t1))
            local fan_range=$((f2 - f1))
            
            if [ "$temp_range" -gt 0 ]; then
                target=$((f1 + (fan_range * temp_offset) / temp_range))
            else
                target=$f1
            fi
            break
        fi
    done
    
    echo "$target"
}

run_daemon() {
    local mode="$1"
    echo "$$" > "$PIDFILE"
    echo "$mode" > "$MODEFILE"
    rm -f "$STOPFILE"
    
    find_hwmon
    get_profile "$mode"
    
    local current_pct=$(echo $FAN_POINTS | awk '{print $1}')
    local down_count=0
    local ramp_up_count=0
    local temp_history=""
    local temp_samples=5
    local last_temp=0
    
    log "Daemon started: mode=$mode, PID=$$, CPU_HWMON=$CPU_HWMON, GPU_HWMON=$GPU_HWMON"
    set_fan_speed "$current_pct"
    
    trap 'log "Stopping daemon"; set_fan_speed 0; rm -f "$PIDFILE"; exit 0' TERM INT
    
    local iteration=0
    while true; do
        # Check stop file
        if [ -f "$STOPFILE" ]; then
            log "Stop file detected"
            set_fan_speed 0
            rm -f "$PIDFILE" "$STOPFILE"
            exit 0
        fi
        
        # Check mode changes
        local new_mode=$(cat "$MODEFILE" 2>/dev/null)
        if [ -n "$new_mode" ] && [ "$new_mode" != "$mode" ]; then
            mode="$new_mode"
            get_profile "$mode"
            current_pct=$(echo $FAN_POINTS | awk '{print $1}')
            down_count=0
            ramp_up_count=0
            temp_history=""
            set_fan_speed "$current_pct"
            log "Mode changed to $mode"
        fi
        
        # Get temperature
        local temp=$(get_max_temp)
        if [ -z "$temp" ] || [ "$temp" -eq 0 ]; then
            temp=$last_temp
            log "Warning: Could not read temperature, using last known: $temp"
        fi
        last_temp=$temp
        
        # Apply smoothing
        temp_history="$temp_history $temp"
        local count=$(echo "$temp_history" | wc -w)
        if [ "$count" -gt "$temp_samples" ]; then
            temp_history=$(echo "$temp_history" | cut -d' ' -f2-)
        fi
        
        # Calculate average
        local sum=0
        for t in $temp_history; do
            sum=$((sum + t))
        done
        count=$(echo "$temp_history" | wc -w)
        temp=$((sum / count))
        
        # Get target speed
        local target_pct=$(get_target_pct "$temp")
        
        # Fan control logic with smooth transitions
        if [ "$target_pct" -gt "$current_pct" ]; then
            # Temperature increased - ramp up faster
            ramp_up_count=$((ramp_up_count + 1))
            if [ "$ramp_up_count" -ge 2 ]; then
                # Increase by up to 5% at a time for smoothness
                local diff=$((target_pct - current_pct))
                if [ "$diff" -gt 5 ]; then
                    current_pct=$((current_pct + 5))
                else
                    current_pct=$target_pct
                fi
                set_fan_speed "$current_pct"
                log "Temp: ${temp}C, increasing fan to ${current_pct}%"
                ramp_up_count=0
            fi
            down_count=0
        elif [ "$target_pct" -lt "$current_pct" ]; then
            # Temperature decreased - ramp down slower
            ramp_up_count=0
            down_count=$((down_count + 1))
            
            if [ "$temp" -le 45 ] && [ "$down_count" -ge 3 ]; then
                # Snap to low if very cool
                current_pct=$target_pct
                set_fan_speed "$current_pct"
                log "Temp: ${temp}C, dropping fan to ${current_pct}%"
                down_count=0
            elif [ "$down_count" -ge "$RAMP_DOWN_DELAY" ]; then
                # Decrease by 3% at a time for smoothness
                local diff=$((current_pct - target_pct))
                if [ "$diff" -gt 3 ]; then
                    current_pct=$((current_pct - 3))
                else
                    current_pct=$target_pct
                fi
                set_fan_speed "$current_pct"
                log "Temp: ${temp}C, ramping down to ${current_pct}%"
                down_count=0
            fi
        else
            # Temperature stable
            down_count=0
            ramp_up_count=0
        fi
        
        # Debug info every 10 iterations
        iteration=$((iteration + 1))
        if [ $((iteration % 10)) -eq 0 ]; then
            log "Status: temp=${temp}C, fan=${current_pct}%, mode=$mode"
        fi
        
        sleep 2
    done
}

stop_daemon() {
    log "Stopping daemon..."
    
    # Create stop file
    touch "$STOPFILE"
    
    # Kill by PID
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null
            # Wait for graceful shutdown
            for i in {1..5}; do
                kill -0 "$pid" 2>/dev/null || break
                sleep 1
            done
            # Force kill if still running
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
        fi
    fi
    
    # Cleanup
    rm -f "$PIDFILE" "$STOPFILE" "$MODEFILE"
    set_fan_speed 0
    log "Daemon stopped"
}

case "$1" in
    start)
        mode="${2:-performance}"
        stop_daemon
        sleep 1
        echo "Starting smart fan daemon in '$mode' mode..."
        nohup "$0" daemon "$mode" > /dev/null 2>&1 &
        sleep 2
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "Smart fan running (PID: $(cat "$PIDFILE"))"
        else
            echo "Failed to start daemon. Check $LOG for details"
        fi
        ;;
    daemon)
        # Internal command for running as daemon
        run_daemon "$2"
        ;;
    stop)
        stop_daemon
        ;;
    mode)
        if [ -z "$2" ]; then
            if [ -f "$MODEFILE" ]; then
                echo "Current mode: $(cat "$MODEFILE")"
            else
                echo "Not running"
            fi
        else
            case "$2" in
                quiet|balanced|performance|extreme)
                    echo "$2" > "$MODEFILE"
                    echo "Mode changed to: $2"
                    ;;
                *)
                    echo "Invalid mode. Use: quiet, balanced, performance, extreme"
                    ;;
            esac
        fi
        ;;
    status)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "Smart fan: RUNNING (PID $(cat "$PIDFILE"))"
            echo "Mode: $(cat "$MODEFILE" 2>/dev/null)"
            
            find_hwmon
            cpu_temp=$(cat "$CPU_HWMON/temp1_input" 2>/dev/null)
            gpu_temp=$(cat "$GPU_HWMON/temp1_input" 2>/dev/null)
            
            [ -n "$cpu_temp" ] && echo "CPU: $((cpu_temp / 1000))°C"
            [ -n "$gpu_temp" ] && echo "GPU: $((gpu_temp / 1000))°C"
            
            fan1=$(cat /sys/class/hwmon/hwmon*/fan1_input 2>/dev/null | head -1)
            fan2=$(cat /sys/class/hwmon/hwmon*/fan2_input 2>/dev/null | head -1)
            
            [ -n "$fan1" ] && echo "Fan1: $fan1 RPM"
            [ -n "$fan2" ] && echo "Fan2: $fan2 RPM"
            
            echo "Log: $LOG"
        else
            echo "Smart fan: NOT RUNNING"
        fi
        ;;
    debug)
        echo "Debug information:"
        echo "ACPI call file: $ACPI_CALL"
        find_hwmon
        echo "CPU HWMON: $CPU_HWMON"
        echo "GPU HWMON: $GPU_HWMON"
        echo "Available hwmon devices:"
        for hwmon in /sys/class/hwmon/hwmon*; do
            echo "  $hwmon: $(cat "$hwmon/name" 2>/dev/null)"
        done
        ;;
    *)
        echo "Usage: $0 {start [mode]|stop|mode [name]|status|debug}"
        echo "Modes: quiet, balanced, performance, extreme"
        ;;
esac
