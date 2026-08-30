# SmartFan — Lightweight Fan Control for Lenovo Legion 7

A shell-based smart fan control daemon for Lenovo Legion 7 (Gen 10+) laptops using `acpi_call` for direct ACPI/WMI fan speed control. Works without the full LLL kernel module stack — just needs `acpi_call`.

## Features

- **4 power modes** with distinct fan curves: quiet, balanced, performance, extreme
- **Smooth ramping** — gradual speed increases/decreases to avoid fan oscillation
- **Temperature averaging** — 8-sample rolling average prevents spike-triggered fan blasts
- **LED color sync** — keyboard LED color matches power mode (blue=quiet, white=balanced, red=performance)
- **TUI mode switcher** — interactive menu with real-time RPM/temp display
- **Turbo override** — instant max speed for sustained heavy loads
- **Systemd integration** — starts on boot, survives sleep/resume
- **Zero dependencies** beyond `acpi_call` — pure bash, no Python, no GUI toolkit

## Supported Hardware

- Lenovo Legion 7 16IRX9 (Gen 9/10) — tested and confirmed
- Should work on other Legion 7/Pro models with `\_SB_.GZFD.WMAE` fan control method

## Fan Speed Ranges by Mode

Quiet, balanced, performance and extreme
Default is balanced, if you need more agressive fan curves run sudo smartfan performance
You can tweak it in your bath, which is in /usr/local/bin/smartfan | just look for the string with the fan speeds and cpu temps
The daemon starts in balanced, adjust on the fly and they do not persist, so just edit the .service file and reinstall, it's much easier.
  NOTE IF YOU'RE HAVING ISSUES:
    This entire repo is a mess honestly, this worked for my 83KY while the GUI didn't, so if you're having trouble i recommend using this smartfan and ignore all the rest.
## Installation

```bash
cd extra/smartfan
sudo ./install.sh
```

This installs:
- `/usr/local/bin/smartfan` — fan control daemon
- `/usr/local/bin/workmode` — interactive mode switcher TUI
- `/usr/local/bin/turboon` — force max fan speed
- `/usr/local/bin/turbooff` — restore normal fan operation
- `smartfan.service` — systemd unit (enabled on boot)

### Prerequisites

```bash
# Debian/Ubuntu/Parrot
sudo apt install acpi-call-dkms

# Arch
sudo pacman -S acpi_call-dkms

# Fedora
sudo dnf install acpi_call
```

## Usage

### Interactive Mode Switcher
```bash
workmode
```
Shows a TUI menu with current temps, fan speeds, and mode selection.

### Direct Commands
```bash
# Start daemon in a specific mode
sudo smartfan start quiet

# Switch mode on the fly (no restart needed)
smartfan mode performance

# Check status
smartfan status

# Stop daemon (returns fans to EC auto control)
sudo smartfan stop

# Turbo mode (bypass daemon, max fans)
sudo turboon

# Back to normal
sudo turbooff
```

## How It Works

The daemon uses `\_SB_.GZFD.WMAE` ACPI method to write fan speed targets directly to the EC (Embedded Controller), bypassing the firmware's built-in fan curve. Each mode defines:

- **Temperature thresholds** (TEMP_LOW, TEMP_MED, TEMP_HIGH) — where fan speed steps up
- **Fan speed percentages** (FAN_LOW through FAN_MAX) — target speed at each threshold
- **Ramp delays** — how many 2-second cycles before stepping up/down

The daemon reads CPU and GPU temps from hwmon, averages them over 8 samples, and smoothly adjusts fan speed using linear interpolation between thresholds.

## Uninstall

```bash
sudo systemctl disable --now smartfan.service
sudo rm /usr/local/bin/{smartfan,workmode,turboon,turbooff}
sudo rm /etc/systemd/system/smartfan.service
```

## License

Same as LenovoLegionLinux — GPLv2.
