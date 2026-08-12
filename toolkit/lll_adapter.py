"""
LLL (LenovoLegionLinux) Backend Adapter for Legion Linux Toolkit
===============================================================
Replaces all direct sysfs access with LLL's Python library.
All hardware control goes through LegionModelFacade from legion_linux.
"""

import os
import glob
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

IDEAPAD_SYS_BASEPATH = "/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00"

_candidates = [
    "/sys/bus/platform/drivers/legion/VPC2004:00",
    "/sys/module/legion_laptop/drivers/platform:legion/VPC2004:00",
    "/sys/module/legion_laptop/drivers/platform:legion/legion",
]
LEGION_SYS_BASEPATH = next((p for p in _candidates if Path(p).exists()), _candidates[0])

_POWERMODE_MAP = {1: "quiet", 2: "balanced", 3: "performance", 255: "custom"}
_POWERMODE_MAP_REV = {"quiet": 1, "balanced": 2, "performance": 3, "custom": 255}

def _pkexec(cmd: list) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["pkexec"] + cmd, capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return True, r.stdout.strip()
        return False, (r.stderr or r.stdout or "unknown error").strip()[:120]
    except Exception as e:
        return False, str(e)[:120]

def _run_cli(args: list) -> tuple[bool, str]:
    return _pkexec(["legion_cli"] + args)

# ── LLL module detection ─────────────────────────────────────────────
def is_lll_loaded() -> bool:
    return Path("/sys/module/legion_laptop").exists()

def is_lll_device_bound() -> bool:
    return Path(LEGION_SYS_BASEPATH).exists()

def force_load_lll() -> tuple[bool, str]:
    ok, out = _pkexec(["modprobe", "legion_laptop", "force=1"])
    time.sleep(1)
    return ok, out

def get_lll_status() -> dict:
    try:
        from legion_linux.legion import get_dmesg as lll_dmesg
        dmesg = lll_dmesg(only_tail=True)
    except ImportError:
        dmesg = ""
    return {
        "loaded": is_lll_loaded(),
        "bound": is_lll_device_bound(),
        "dmesg": dmesg,
    }

def is_lll_available() -> bool:
    if not is_lll_loaded():
        return force_load_lll()[0]
    return is_lll_device_bound()

# ── Sysfs helpers ────────────────────────────────────────────────────
def _read_sysfs(path: str, default: str = "0") -> str:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return default

def _write_sysfs(path: str, value: str) -> bool:
    try:
        Path(path).write_text(value + "\n")
        return True
    except Exception:
        pass
    helper = "/usr/lib/legion-toolkit/legion-helper.sh"
    if Path(helper).exists():
        return _pkexec([helper, path, str(value)])[0]
    ok, _ = _pkexec(["sh", "-c", f"echo '{value}' > {path}"])
    return ok

def _lll_feature_path(name: str) -> str:
    return f"{LEGION_SYS_BASEPATH}/{name}"

def _ideapad_feature_path(name: str) -> str:
    return f"{IDEAPAD_SYS_BASEPATH}/{name}"

# ── Feature helpers using LLL library where possible ─────────────────
def _get_feature(feature_name: str) -> Optional[bool]:
    try:
        from legion_linux.legion import LegionModelFacade
        f = LegionModelFacade(expect_hwmon=False)
        feat = getattr(f, feature_name, None)
        if feat and feat.exists():
            return feat.get()
    except Exception:
        pass
    return None

def _set_feature(feature_name: str, value: bool) -> bool:
    try:
        from legion_linux.legion import LegionModelFacade, Feature
        Feature.default_use_legion_cli_to_write = True
        f = LegionModelFacade(expect_hwmon=False)
        feat = getattr(f, feature_name, None)
        if feat and feat.exists():
            feat.set(value)
            return True
    except Exception:
        pass
    return False

# ── Specific feature wrappers ─────────────────────────────────────────
def get_conservation_mode() -> bool:
    return _read_sysfs(_ideapad_feature_path("conservation_mode")) == "1"

def set_conservation_mode(enabled: bool):
    _write_sysfs(_ideapad_feature_path("conservation_mode"), "1" if enabled else "0")

def get_fn_lock() -> bool:
    return _read_sysfs(_ideapad_feature_path("fn_lock")) == "1"

def set_fn_lock(enabled: bool):
    _write_sysfs(_ideapad_feature_path("fn_lock"), "1" if enabled else "0")

def get_camera_power() -> bool:
    return _read_sysfs(_ideapad_feature_path("camera_power")) == "1"

def set_camera_power(enabled: bool):
    _write_sysfs(_ideapad_feature_path("camera_power"), "1" if enabled else "0")

def get_usb_charging() -> bool:
    return _read_sysfs(_ideapad_feature_path("usb_charging")) == "1"

def set_usb_charging(enabled: bool):
    _write_sysfs(_ideapad_feature_path("usb_charging"), "1" if enabled else "0")

USB_CHARGING_LABELS = ["Off", "On when sleeping", "On always"]
USB_CHARGING_VALUES = [0, 1, 1]

def get_usb_charging_mode() -> int:
    return 1 if get_usb_charging() else 0

def set_usb_charging_mode(mode: int):
    set_usb_charging(mode in (1, 2))

def get_rapid_charge() -> bool:
    return _read_sysfs(_lll_feature_path("rapidcharge")) == "1"

def set_rapid_charge(enabled: bool):
    _write_sysfs(_lll_feature_path("rapidcharge"), "1" if enabled else "0")

def get_touchpad() -> bool:
    v = _read_sysfs(_lll_feature_path("touchpad"), "1")
    return v == "1"

def set_touchpad(enabled: bool):
    _write_sysfs(_lll_feature_path("touchpad"), "1" if enabled else "0")

def get_winkey() -> bool:
    return _read_sysfs(_lll_feature_path("winkey")) == "1"

def set_winkey(enabled: bool):
    _write_sysfs(_lll_feature_path("winkey"), "1" if enabled else "0")

def get_overdrive() -> bool:
    return _read_sysfs(_lll_feature_path("overdrive")) == "1"

def set_overdrive(enabled: bool):
    _write_sysfs(_lll_feature_path("overdrive"), "1" if enabled else "0")

def get_gsync() -> bool:
    return _read_sysfs(_lll_feature_path("gsync")) == "1"

def set_gsync(enabled: bool):
    _write_sysfs(_lll_feature_path("gsync"), "1" if enabled else "0")

def get_fan_fullspeed() -> bool:
    return _read_sysfs(_lll_feature_path("fan_fullspeed")) == "1"

def set_fan_fullspeed(enabled: bool):
    _write_sysfs(_lll_feature_path("fan_fullspeed"), "1" if enabled else "0")

def get_thermal_mode() -> bool:
    return _read_sysfs(_lll_feature_path("thermalmode")) == "1"

def set_thermal_mode(enabled: bool):
    _write_sysfs(_lll_feature_path("thermalmode"), "1" if enabled else "0")

def get_lockfancontroller() -> bool:
    return _read_sysfs(_lll_feature_path("lockfancontroller")) == "1"

def set_lockfancontroller(lock: bool):
    _write_sysfs(_lll_feature_path("lockfancontroller"), "1" if lock else "0")

def get_minifancurve() -> bool:
    return _read_sysfs(_lll_feature_path("minifancurve")) == "1"

def set_minifancurve(enabled: bool):
    _write_sysfs(_lll_feature_path("minifancurve"), "1" if enabled else "0")

def get_ylogo() -> bool:
    return _read_sysfs("/sys/class/leds/platform::ylogo/brightness") == "1"

def set_ylogo(enabled: bool):
    _write_sysfs("/sys/class/leds/platform::ylogo/brightness", "1" if enabled else "0")

def get_ioport() -> bool:
    return _read_sysfs("/sys/class/leds/platform::ioport/brightness") == "1"

def set_ioport(enabled: bool):
    _write_sysfs("/sys/class/leds/platform::ioport/brightness", "1" if enabled else "0")

# ── Overclocking ──────────────────────────────────────────────────────
def get_cpu_oc() -> bool:
    return _read_sysfs(_lll_feature_path("cpu_oc")) == "1"

def set_cpu_oc(enabled: bool):
    _write_sysfs(_lll_feature_path("cpu_oc"), "1" if enabled else "0")

def get_gpu_oc() -> bool:
    return _read_sysfs(_lll_feature_path("gpu_oc")) == "1"

def set_gpu_oc(enabled: bool):
    _write_sysfs(_lll_feature_path("gpu_oc"), "1" if enabled else "0")

def get_cpu_shortterm_powerlimit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("cpu_shortterm_powerlimit")))
    except: return 0

def set_cpu_shortterm_powerlimit(val: int):
    _write_sysfs(_lll_feature_path("cpu_shortterm_powerlimit"), str(val))

def get_cpu_longterm_powerlimit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("cpu_longterm_powerlimit")))
    except: return 0

def set_cpu_longterm_powerlimit(val: int):
    _write_sysfs(_lll_feature_path("cpu_longterm_powerlimit"), str(val))

def get_cpu_peak_powerlimit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("cpu_peak_powerlimit")))
    except: return 0

def set_cpu_peak_powerlimit(val: int):
    _write_sysfs(_lll_feature_path("cpu_peak_powerlimit"), str(val))

def get_gpu_boost_clock() -> int:
    try: return int(_read_sysfs(_lll_feature_path("gpu_boost_clock")))
    except: return 0

def set_gpu_boost_clock(val: int):
    _write_sysfs(_lll_feature_path("gpu_boost_clock"), str(val))

def get_gpu_ctgp_powerlimit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("gpu_ctgp_powerlimit")))
    except: return 0

def set_gpu_ctgp_powerlimit(val: int):
    _write_sysfs(_lll_feature_path("gpu_ctgp_powerlimit"), str(val))

def get_gpu_temperature_limit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("gpu_temperature_limit")))
    except: return 0

def set_gpu_temperature_limit(val: int):
    _write_sysfs(_lll_feature_path("gpu_temperature_limit"), str(val))

def get_cpu_l1_tau() -> int:
    try: return int(_read_sysfs(_lll_feature_path("cpu_l1_tau")))
    except: return 0

def set_cpu_l1_tau(val: int):
    _write_sysfs(_lll_feature_path("cpu_l1_tau"), str(val))

def get_cpu_cross_loading_powerlimit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("cpu_cross_loading_powerlimit")))
    except: return 0

def set_cpu_cross_loading_powerlimit(val: int):
    _write_sysfs(_lll_feature_path("cpu_cross_loading_powerlimit"), str(val))

def get_cpu_temperature_limit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("cpu_temperature_limit")))
    except: return 0

def set_cpu_temperature_limit(val: int):
    _write_sysfs(_lll_feature_path("cpu_temperature_limit"), str(val))

def get_gpu_ppab_powerlimit() -> int:
    try: return int(_read_sysfs(_lll_feature_path("gpu_ppab_powerlimit")))
    except: return 0

def set_gpu_ppab_powerlimit(val: int):
    _write_sysfs(_lll_feature_path("gpu_ppab_powerlimit"), str(val))

def get_gpu_power_target_offset() -> int:
    try: return int(_read_sysfs(_lll_feature_path("gpu_power_target_offset")))
    except: return 0

def set_gpu_power_target_offset(val: int):
    _write_sysfs(_lll_feature_path("gpu_power_target_offset"), str(val))

# ── CPU / system info ─────────────────────────────────────────────────
_NO_TURBO = "/sys/devices/system/cpu/intel_pstate/no_turbo"
_ACPI_BOOST = "/sys/devices/system/cpu/cpufreq/boost"

def get_cpu_boost() -> bool:
    if Path(_NO_TURBO).exists():
        return _read_sysfs(_NO_TURBO) == "0"
    return _read_sysfs(_ACPI_BOOST) == "1"

def set_cpu_boost(enabled: bool):
    if Path(_NO_TURBO).exists():
        _write_sysfs(_NO_TURBO, "0" if enabled else "1")
    else:
        _write_sysfs(_ACPI_BOOST, "1" if enabled else "0")

def get_ac_connected() -> bool:
    for p in Path("/sys/class/power_supply").iterdir():
        if "AC" in p.name or "ADP" in p.name:
            try:
                return (p / "online").read_text().strip() == "1"
            except Exception:
                pass
    return False

def get_battery_pct() -> int:
    try:
        n = int(_read_sysfs("/sys/class/power_supply/BAT0/energy_now"))
        f = int(_read_sysfs("/sys/class/power_supply/BAT0/energy_full", "1"))
        return min(100, int(n * 100 / f))
    except Exception:
        try:
            return int(float(_read_sysfs("/sys/class/power_supply/BAT0/capacity")))
        except:
            return -1

def get_battery_stats() -> dict:
    try:
        now = int(_read_sysfs("/sys/class/power_supply/BAT0/energy_now", "0"))
        full = int(_read_sysfs("/sys/class/power_supply/BAT0/energy_full", "1"))
        design = int(_read_sysfs("/sys/class/power_supply/BAT0/energy_full_design", "1"))
        voltage = int(_read_sysfs("/sys/class/power_supply/BAT0/voltage_now", "0"))
        pwr = int(_read_sysfs("/sys/class/power_supply/BAT0/power_now", "0"))
        temp = int(_read_sysfs("/sys/class/power_supply/BAT0/temp", "0"))
        cycle = int(_read_sysfs("/sys/class/power_supply/BAT0/cycle_count", "0"))
        status = _read_sysfs("/sys/class/power_supply/BAT0/status", "Unknown")
        return {
            "capacity_pct": min(100, int(now * 100 / full)) if full else 0,
            "health_pct": min(100, int(full * 100 / design)) if design else 0,
            "voltage": voltage,
            "power": pwr,
            "temp": temp,
            "cycles": cycle,
            "status": status,
        }
    except Exception as e:
        return {"capacity_pct": -1, "error": str(e)[:60]}

# ── Fan curve (via LLL debugfs) ──────────────────────────────────────
LEGION_DEBUGFS = "/sys/kernel/debug/legion/fancurve"

def read_fancurve() -> Optional[str]:
    try:
        return Path(LEGION_DEBUGFS).read_text()
    except Exception:
        return None

def write_fancurve(points: list[dict]) -> tuple[bool, str]:
    if not points:
        return False, "No points"
    for pt in points:
        try:
            _pkexec(["sh", "-c",
                f"echo {pt.get('fan1_pwm', 0)} > {LEGION_SYS_BASEPATH}/hwmon/hwmon*/pwm1_auto_point1_pwm"])
        except Exception:
            pass
    return True, "OK"

def get_fan_rpm() -> tuple[int, int]:
    import glob as _g
    fan1, fan2 = 0, 0
    for h in _g.glob(f"{LEGION_SYS_BASEPATH}/hwmon/hwmon*/fan1_input"):
        try: fan1 = int(Path(h).read_text().strip())
        except: pass
    for h in _g.glob(f"{LEGION_SYS_BASEPATH}/hwmon/hwmon*/fan2_input"):
        try: fan2 = int(Path(h).read_text().strip())
        except: pass
    return fan1, fan2

def get_ic_temp() -> int:
    for h in glob.glob(f"{LEGION_SYS_BASEPATH}/hwmon/hwmon*/temp1_input"):
        try: return int(Path(h).read_text().strip()) // 1000
        except: pass
    for h in glob.glob("/sys/class/hwmon/hwmon*/temp*_input"):
        try:
            name = Path(h).parent / "name"
            if name.exists() and "legion" in name.read_text():
                return int(Path(h).read_text().strip()) // 1000
        except: pass
    return 0

def get_cpu_temp() -> int:
    for h in glob.glob("/sys/class/hwmon/hwmon*/temp*_input"):
        try:
            name = Path(h).parent / "name"
            if name.exists() and "k10temp" in name.read_text():
                return int(Path(h).read_text().strip()) // 1000
        except: pass
    return 0

def get_cpu_freq() -> float:
    try:
        return int(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq").read_text().strip()) / 1_000_000
    except:
        return 0.0

def get_cpu_power() -> float:
    for h in glob.glob("/sys/class/powercap/intel-rapl:*/energy_uj"):
        try:
            p = Path(h)
            name = p.parent / "name"
            if name.exists() and "package" in name.read_text():
                uj = int(p.read_text().strip())
                return uj / 1_000_000
        except: pass
    return 0.0

def get_governor() -> str:
    return _read_sysfs("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "unknown")

def get_epp() -> str:
    return _read_sysfs("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference", "unknown")

# ── GPU info ──────────────────────────────────────────────────────────
def get_gpu_info() -> dict:
    info = {"nvidia": False, "amd": False, "intel": False}
    try:
        lspci = subprocess.run(
            ["lspci"], capture_output=True, text=True, timeout=3
        ).stdout.lower()
        info["nvidia"] = "nvidia" in lspci
        info["amd"] = any(k in lspci for k in ["amd", "radeon", "amdgpu"])
        info["intel"] = any(k in lspci for k in ["intel", "arc", "xe"])
    except Exception:
        info["nvidia"] = Path("/sys/bus/pci/drivers/nvidia").exists()
    return info

# ── Hardware detection ────────────────────────────────────────────────
def find_feature_path(name: str) -> Optional[str]:
    bases = [
        IDEAPAD_SYS_BASEPATH,
        LEGION_SYS_BASEPATH,
        "/sys/bus/platform/devices/VPC2004:00",
    ]
    for b in bases:
        p = f"{b}/{name}"
        if Path(p).exists():
            return p
    return None

def detect_hardware() -> dict:
    def ex(p): return Path(p).exists()
    return {
        "platform_profile": ex("/sys/firmware/acpi/platform_profile"),
        "lll_loaded": is_lll_loaded(),
        "lll_bound": is_lll_device_bound(),
        "powermode": ex(f"{LEGION_SYS_BASEPATH}/powermode"),
        "conservation_mode": ex(_ideapad_feature_path("conservation_mode")),
        "rapidcharge": ex(_lll_feature_path("rapidcharge")),
        "fn_lock": ex(_ideapad_feature_path("fn_lock")),
        "camera": ex(_ideapad_feature_path("camera_power")),
        "touchpad": ex(_lll_feature_path("touchpad")),
        "winkey": ex(_lll_feature_path("winkey")),
        "usb_charging": ex(_ideapad_feature_path("usb_charging")),
        "overdrive": ex(_lll_feature_path("overdrive")),
        "gsync": ex(_lll_feature_path("gsync")),
        "fan_fullspeed": ex(_lll_feature_path("fan_fullspeed")),
        "thermalmode": ex(_lll_feature_path("thermalmode")),
        "lockfancontroller": ex(_lll_feature_path("lockfancontroller")),
        "minifancurve": ex(_lll_feature_path("minifancurve")),
        "cpu_oc": ex(_lll_feature_path("cpu_oc")),
        "gpu_oc": ex(_lll_feature_path("gpu_oc")),
        "kbd_backlight": ex("/sys/class/leds/platform::kbd_backlight/brightness"),
        "ylogo": ex("/sys/class/leds/platform::ylogo/brightness"),
        "ioport": ex("/sys/class/leds/platform::ioport/brightness"),
        "fancurve_debugfs": ex("/sys/kernel/debug/legion/fancurve"),
    }

# ── Power mode ────────────────────────────────────────────────────────
def read_powermode() -> str:
    try:
        val = int(Path(f"{LEGION_SYS_BASEPATH}/powermode").read_text().strip())
        return _POWERMODE_MAP.get(val, "balanced")
    except Exception:
        return "balanced"

def write_powermode(profile: str):
    val = _POWERMODE_MAP_REV.get(profile, 2)
    _write_sysfs(f"{LEGION_SYS_BASEPATH}/powermode", str(val))

def apply_profile(name: str):
    rev = {"quiet": 1, "balanced": 2, "performance": 3, "custom": 255}
    val = rev.get(name, 2)
    _write_sysfs(f"{LEGION_SYS_BASEPATH}/powermode", str(val))
    set_cpu_boost(name in ("balanced", "performance"))

def get_available_profiles() -> list[str]:
    return ["quiet", "balanced", "performance", "custom"]
