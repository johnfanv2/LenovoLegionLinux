# Lenovo LOQ Essential 15IRX11 (83SC) — Developer Reference

## System Info

- **Model:** Lenovo LOQ Essential 15IRX11 (83SC)
- **BIOS:** SECN22WW
- **EC:** 0x5508 (uses `ec_register_offsets_loq_v1`)
- **CPU:** 13th Gen Intel Core i5-13450HX
- **Kernel module mapping:** `model_r3cn`
- **Power limit access method:** `ACCESS_METHOD_WMI3`

## Prerequisites

```bash
# Load the module (force=1 needed for unlisted models)
sudo modprobe legion_laptop force=1

# Bind the platform device if sysfs doesn't appear
echo "legion" | sudo tee /sys/bus/platform/drivers/legion/bind

# All sysfs paths are under:
/sys/devices/platform/legion/
```

## CPU Power Limits

### Read

```bash
cat /sys/devices/platform/legion/cpu_longterm_powerlimit      # PL1 (W)
cat /sys/devices/platform/legion/cpu_shortterm_powerlimit     # PL2 (W)
cat /sys/devices/platform/legion/cpu_l1_tau                   # TAU (seconds)
cat /sys/devices/platform/legion/cpu_cross_loading_powerlimit # Cross Load (W)
cat /sys/devices/platform/legion/cpu_peak_powerlimit          # Peak (W)
cat /sys/devices/platform/legion/cpu_apu_sppt_powerlimit      # APU SPPT (W)
cat /sys/devices/platform/legion/cpu_default_powerlimit       # Default (read-only)
```

### Write

```bash
echo 55 | sudo tee /sys/devices/platform/legion/cpu_longterm_powerlimit
echo 80 | sudo tee /sys/devices/platform/legion/cpu_shortterm_powerlimit
echo 56 | sudo tee /sys/devices/platform/legion/cpu_l1_tau
echo 30 | sudo tee /sys/devices/platform/legion/cpu_cross_loading_powerlimit
```

### Constraints (enforced by kernel)

- **PL2 must always be ≥ PL1.** Setting PL2 below PL1 automatically drops PL1 to match. Setting PL1 above PL2 automatically raises PL2 to match.
- **Min/Max clamping:** Values outside valid range are silently clamped to the nearest bound.

| Setting | Min | Max | Step |
|---------|-----|-----|------|
| PL1 (Long Term) | 25W | 60W | 1W |
| PL2 (Short Term) | 40W | 85W | 1W |
| TAU | 20s | 160s | 1s |
| Cross Loading | 20W | 30W | 1W |
| CPU Temp Limit | 85°C | 100°C | 1°C |

### MSR 0x610 Verification

PL1/PL2 are also written to MSR 0x610 (RAPL) via `wrmsr_safe`:

```bash
# Read MSR 0x610 (requires root)
sudo rdmsr 0x610

# Decode with Python
python3 -c "
msr = 0x$(sudo rdmsr -f 63:0 0x610)
pl2_raw = (msr >> 32) & 0x7FFF
pl1_raw = msr & 0x7FFF
print(f'PL2={pl2_raw/8:.1f}W, PL1={pl1_raw/8:.1f}W')
"
```

## GPU Power Controls

### Read

```bash
cat /sys/devices/platform/legion/gpu_ctgp_powerlimit           # cTGP (W)
cat /sys/devices/platform/legion/gpu_oc                         # PPAB/Dynamic Boost (W)
cat /sys/devices/platform/legion/gpu_power_target_offset        # Offset (W)
cat /sys/devices/platform/legion/gpu_temperature_limit          # GPU Temp Limit (°C)
cat /sys/devices/platform/legion/gpu_default_ppab_ctrgp_powerlimit # Default (read-only)
cat /sys/devices/platform/legion/gpu_ctgp2_powerlimit           # cTGP2 (read-only)
```

### Write

```bash
echo 50 | sudo tee /sys/devices/platform/legion/gpu_ctgp_powerlimit
echo 15 | sudo tee /sys/devices/platform/legion/gpu_oc
echo 45 | sudo tee /sys/devices/platform/legion/gpu_power_target_offset
echo 87 | sudo tee /sys/devices/platform/legion/gpu_temperature_limit
```

### Constraints

- **Step snapping:** cTGP, PPAB, and Offset snap to nearest valid step (step 5).
- **Min/Max clamping:** Values outside valid range are silently clamped.
- **CRITICAL: GPU WMI writes only take effect in Custom mode (powermode=255).** In other modes, the EC firmware applies its own GPU power budget and ignores WMI writes.

| Setting | Min | Max | Step |
|---------|-----|-----|------|
| GPU cTGP | 35W | 50W | 5W |
| GPU Dynamic Boost (PPAB) | 0W | 15W | 5W |
| GPU Offset | 10W | 45W | 5W |
| GPU Temp Limit | 75°C | 87°C | 1°C |

### WMI3 Feature IDs (OtherMethod, GUID: `dc2a8805-3a8c-41ba-a6f7-092e0089cd3b`)

| Control | Feature ID | Method |
|---------|-----------|--------|
| cTGP | `0x02020000` | Get/Set Feature Value (method 18) |
| PPAB | `0x02010000` | Get/Set Feature Value (method 18) |
| Offset | `0x02040000` | Get/Set Feature Value (method 18) |
| GPU Temp | `0x02030000` | Get/Set Feature Value (method 18) |
| CPU PL1 | `0x01020000` | Get/Set Feature Value (method 18) |
| CPU PL2 | `0x01010000` | Get/Set Feature Value (method 18) |
| CPU TAU | `0x01070000` | Get/Set Feature Value (method 18) |
| CPU Cross Load | `0x01060000` | Get/Set Feature Value (method 18) |
| CPU Temp | `0x01040000` | Get/Set Feature Value (method 18) |

## Power Mode / Platform Profile

### Read

```bash
cat /sys/devices/platform/legion/powermode          # Raw power mode value
cat /sys/devices/platform/legion/platform-profile   # Platform profile name
```

### Write

```bash
# Via platform-profile (recommended)
echo performance | sudo tee /sys/devices/platform/legion/platform-profile
echo balanced | sudo tee /sys/devices/platform/legion/platform-profile
echo low-power | sudo tee /sys/devices/platform/legion/platform-profile

# Via raw powermode (WMI SetSmartFanMode, method 44)
# Values: 1=Quiet, 2=Balanced, 3=Performance, 224=Extreme, 255=Custom
echo 255 | sudo tee /sys/devices/platform/legion/powermode
```

### Power Mode Values

| Mode | WMI Value | Platform Profile |
|------|-----------|-----------------|
| Quiet | 1 | `low-power` |
| Balanced | 2 | `balanced` |
| Performance | 3 | `performance` |
| Extreme | 224 | `max-performance` |
| Custom | 255 | `custom` |

### Per-Mode Defaults

| Metric | Quiet | Balanced | Performance | Extreme | Custom |
|--------|-------|----------|-------------|---------|--------|
| PL1 | 30W | 45W | 55W | 55W | user-set |
| PL2 | 45W | 65W | 80W | 80W | user-set |
| TAU | 56s | 56s | 56s | 56s | user-set |
| cTGP | 45W | 45W | 50W | 50W | user-set |
| PPAB | 10W | 15W | 15W | 15W | user-set |
| Offset | 25W | 30W | 30W | 30W | user-set |
| GPU Temp | 87°C | 87°C | 87°C | 87°C | user-set |

## Fan Control

### Read

```bash
cat /sys/devices/platform/legion/hwmon/hwmon*/fan1_input    # Fan speed (RPM)
cat /sys/devices/platform/legion/fancurve_defaults_powermode # Fan curve power mode
```

### Fan Curve (Custom mode only)

Fan curves require Custom mode (powermode=255) and GZ44==0x07 in the EC.

```bash
# Fan curve addresses (read from EC RAM)
# See /sys/kernel/debug/legion/ecmemory for raw EC RAM dump
```

## Keyboard Backlight

```bash
cat /sys/devices/platform/legion/leds/platform::kbd_backlight/brightness
echo 2 | sudo tee /sys/devices/platform/legion/leds/platform::kbd_backlight/brightness
# Values: 0=Off, 1=Low, 2=High
```

## Other LED Controls

```bash
# Y-logo LED
cat /sys/devices/platform/legion/leds/platform::ylogo/brightness

# IO port LED
cat /sys/devices/platform/legion/leds/platform::ioport/brightness
```

## Battery / Conservation Mode

> **Note:** On LOQ 83SC, `ideapad-laptop` is blacklisted (no DYTC), and the
> legion module does **not** expose `conservation_mode`. The usual `ideapad_acpi`
> path (`/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/conservation_mode`)
> is therefore unavailable on this machine. Use the OEM tool or a different
> driver if you need conservation mode.

## Debug / EC RAM

```bash
# Full EC RAM dump
sudo cat /sys/kernel/debug/legion/ecmemory

# EC RAM via MMIO
sudo cat /sys/kernel/debug/legion/ecmemoryram
```

## nvidia-smi Integration

```bash
# Read GPU power draw
nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits

# Note: nvidia-smi -pl is blocked on mobile ("not supported in current scope")
# Power limits are controlled via the kernel module sysfs, not nvidia-smi
```

## Blacklisted Modules

`ideapad-laptop` is blacklisted in `/etc/modprobe.d/blacklist-ideapad.conf` because the LOQ 83SC BIOS SECN22WW has no DYTC ACPI method.

## Rebuild the Module

```bash
cd /tmp/LenovoLegionLinux/kernel_module
make KERNELRELEASE=$(uname -r) LLVM=1

# Reload
sudo rmmod legion_laptop
sudo insmod legion-laptop.ko force=1
echo "legion" | sudo tee /sys/bus/platform/drivers/legion/bind
```

## Auto-Apply on Boot

```bash
# systemd service for PL2 limit
sudo cat /etc/systemd/system/cpu-pl2-limit.service

# Pacman hook to reapply patch after kernel updates
sudo cat /etc/pacman.d/hooks/99-reapply-legion-loq-patch.hook
```

## Key Differences from Legion EC 0x8227

1. **EC register offsets** use `ec_register_offsets_loq_v1` (different addresses)
2. **Power mode** uses `LEGION_WMI_GAMEZONE_GUID` (`887B54E3-DDDC-4B2C-8B88-68A26A8835D0`)
3. **Power limits** use WMI3 OtherMethod (`dc2a8805-3a8c-41ba-a6f7-092e0089cd3b`)
4. **GPU temp limit** is writable; valid range 75–87°C (reads 87°C in standard power modes)
5. **Custom mode** is required for GPU WMI writes to take effect
6. **Total power budget** is 135W (PL2 maxes at 85W on Windows)
7. **No DYTC** — ideapad-laptop cannot load
