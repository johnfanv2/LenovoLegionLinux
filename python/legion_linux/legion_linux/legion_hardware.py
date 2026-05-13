#!/usr/bin/env python3
"""Legion Linux Toolkit — hardware detection, sysfs helpers, monitoring, fan/display/GPU control.
All sysfs paths are resolved lazily (deferred) — no reads at import time.
"""

import os, sys, subprocess, json, time, threading
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from .legion_utils import (
    CFG_DIR, FAN_CFG, HARDWARE_CFG, FIRST_RUN_FLAG, send_notif, _load_theme_colours
)

_this_dir = Path(__file__).resolve().parent
if str(_this_dir.parent) not in sys.path:
    sys.path.insert(0, str(_this_dir.parent))

# ══════════════════════════════════════════════════════════════════════════════
# LAZY SYSFS PATH RESOLUTION — no reads at import time
# ══════════════════════════════════════════════════════════════════════════════
_POWERMODE_MAP = {1: "quiet", 2: "balanced", 3: "performance", 255: "custom"}
_CLI_FEATURES = {
    "rapidcharge":"rapid-charging","conservation_mode":"batteryconservation",
    "fn_lock":"fnlock","touchpad":"touchpad",
    "usb_charging":"always-on-usb-charging","camera_power":"camera-power",
    "lockfancontroller":"lockfancontroller","maximumfanspeed":"maximumfanspeed",
}

def _find_feature(feature: str):
    bases = []
    for root in [Path("/sys/bus/platform/drivers/ideapad_acpi"),
                 Path("/sys/bus/platform/drivers/legion"),
                 Path("/sys/module/legion_laptop/drivers/platform:legion")]:
        if root.exists():
            try:
                for d in root.iterdir():
                    if d.is_dir() or d.is_symlink():
                        bases.append(d)
            except: pass
    try:
        for pci in Path("/sys/devices").glob("pci*"):
            for dev in pci.glob("*/PNP0C09:*"):
                bases.append(dev)
            for dev in pci.glob("*/VPC2004:*"):
                bases.append(dev)
    except: pass
    try:
        for d in Path("/sys/bus/wmi/devices").iterdir():
            bases.append(d)
    except: pass
    try:
        for d in Path("/sys/bus/platform/devices").iterdir():
            if any(k in d.name.lower() for k in ["vpc","ideapad","legion","lenovo","thinkpad"]):
                bases.append(d)
    except: pass
    for base in bases:
        try:
            p = Path(base) / feature
            if p.exists(): return p
        except: pass
    return None

def _find_ideapad(feature: str):
    root = Path("/sys/bus/platform/drivers/ideapad_acpi")
    if root.exists():
        try:
            for d in root.iterdir():
                p = d / feature
                if p.exists(): return p
        except: pass
    return _find_feature(feature)

def _find_legion_base():
    for p in [Path("/sys/module/legion_laptop/drivers/platform:legion/legion"),
              Path("/sys/bus/platform/drivers/legion")]:
        if p.exists(): return p
    fp = _find_feature("powermode")
    return fp.parent if fp else Path("/sys/module/legion_laptop/drivers/platform:legion/legion")

def _find_legion_path(name):
    base = _find_legion_base()
    p = base / name
    if p.exists(): return p
    return _find_feature(name) or p

def _find_ideapad_named(name):
    p = _find_ideapad(name)
    if p: return p
    root = Path("/sys/bus/platform/drivers/ideapad_acpi")
    if root.exists():
        try:
            for d in root.iterdir():
                return d / name
        except: pass
    return _find_feature(name) or Path("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00") / name

# ══════════════════════════════════════════════════════════════════════════════
# LAZY PATH GETTERS — called on demand, not at import
# ══════════════════════════════════════════════════════════════════════════════
_path_cache = {}
def _lazy(name):
    if name not in _path_cache:
        _path_cache[name] = _find_feature(name)
    return _path_cache[name]

def _read_file(path, default=""):
    try: return Path(path).read_text().strip()
    except: return default

def _which(cmd):
    return Path(cmd).exists() or subprocess.run(["which",cmd],capture_output=True).returncode==0

# ══════════════════════════════════════════════════════════════════════════════
# CLI WRAPPERS
# ══════════════════════════════════════════════════════════════════════════════
def _cli_status(name):
    try:
        r = subprocess.run([sys.executable,"-m","legion_linux.legion_cli",f"{name}-status"],
                           capture_output=True,text=True,timeout=5)
        if r.returncode==0:
            out = r.stdout.strip().lower()
            return "1" if out in ("true","1","enabled","on") else "0"
    except: pass
    return None

def _cli_set(name, enable):
    cmd = f"{name}-enable" if enable else f"{name}-disable"
    try:
        r = subprocess.run([sys.executable,"-m","legion_linux.legion_cli",cmd],
                           capture_output=True,timeout=5)
        return r.returncode==0
    except: return False

def _cli_feature_from_path(path):
    path = str(path).lower()
    for feat_key, cli_name in _CLI_FEATURES.items():
        if feat_key in path:
            return cli_name
    return None

def rdsys(path, default="0"):
    cli = _cli_feature_from_path(path)
    if cli:
        val = _cli_status(cli)
        if val is not None: return val
    try: return Path(path).read_text().strip()
    except: return default

def wrsys(path, value):
    import socket as _s
    path = str(path); value = str(value)
    cli = _cli_feature_from_path(path)
    if cli:
        if _cli_set(cli, value=="1"): return
    try:
        c = _s.socket(_s.AF_UNIX, _s.SOCK_STREAM); c.settimeout(2.0)
        c.connect("/run/legion-toolkit.sock")
        c.send(f"write:{path}:{value}\n".encode())
        resp = c.recv(32).decode().strip(); c.close()
        if resp=="ok": return
    except: pass
    try:
        Path(path).write_text(value+"\n"); return
    except: pass
    try:
        v = value.replace("'","").replace(";","").replace("&","")
        subprocess.Popen(["pkexec","sh","-c",f"echo '{v}' > {path}"],
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
# POWER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def get_powermode_path():
    return _lazy("powermode") or _find_legion_path("powermode")

def read_powermode() -> str:
    p = get_powermode_path()
    if p and p.exists():
        try: return _POWERMODE_MAP.get(int(p.read_text().strip()), "balanced")
        except: pass
    # fallback to platform_profile
    try: return Path("/sys/firmware/acpi/platform_profile").read_text().strip()
    except: return "balanced"

def apply_profile(name: str):
    import socket as _s
    try:
        c = _s.socket(_s.AF_UNIX,_s.SOCK_STREAM); c.settimeout(2.0)
        c.connect("/run/legion-toolkit.sock")
        c.send(f"set:{name}\n".encode())
        resp = c.recv(32).decode().strip(); c.close()
        if resp=="ok": return True, f"Profile set to {name}"
    except: pass
    rev = {"quiet":1,"balanced":2,"performance":3,"custom":255}
    p = get_powermode_path()
    if p:
        try:
            p.write_text(f"{rev.get(name,2)}\n")
            return True, f"Profile set to {name}"
        except Exception as e: return False, str(e)
    return False, "No powermode path"

def get_ac_connected():
    try:
        for psu in Path("/sys/class/power_supply").iterdir():
            if rdsys(psu/"type","")=="Mains":
                return rdsys(psu/"online","0")=="1"
    except: pass
    return False

# ══════════════════════════════════════════════════════════════════════════════
# HARDWARE DETECTION (deferred — only runs on first wizard or explicit call)
# ══════════════════════════════════════════════════════════════════════════════
HARDWARE_CACHE_TTL = 3600
LEGION_MODELS = {
    "82ju":"Legion 5 15ACH6H","82gu":"Legion 5 15ACH5","82ms":"Legion 7 16ACHg6",
    "82rh":"Legion 5 Pro 16ARH7","82sr":"Legion 5 Pro 16","82ts":"Legion 7 16","82wm":"Legion Slim 7",
}

def _dmi(field: str) -> str:
    try: return Path(f"/sys/class/dmi/id/{field}").read_text().strip().lower()
    except: return ""

def detect_hardware(force: bool = False) -> dict:
    if not force:
        cached = load_hardware()
        if cached:
            t = cached.get("_detected_at",0)
            if time.time()-t < HARDWARE_CACHE_TTL:
                return cached
    product = _dmi("product_name"); family = _dmi("product_family")
    full = f"{product} {family}".lower()
    if "legion" in full:
        brand = "legion"
        import re
        m = re.search(r'(legion\s+\d+|loq\s+\d+)',full,re.I)
        model_detail = m.group(0).title() if m else product.title()
    elif "loq" in full: brand="loq"; model_detail=product.title() or "LOQ"
    elif "thinkpad" in full: brand="thinkpad"; model_detail=product.title() or "ThinkPad"
    elif "yoga" in full: brand="yoga"; model_detail=product.title() or "Yoga"
    else: brand="lenovo" if "lenovo" in _dmi("sys_vendor") else "unknown"; model_detail=product.title() or "Unknown"
    cpu_vendor="unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if "vendor_id" in line.lower():
                v = line.split(":")[1].strip().lower()
                if "amd" in v: cpu_vendor="amd"
                elif "intel" in v: cpu_vendor="intel"
    except: pass
    cap = {
        "brand":brand,"model":_dmi("product_name"),"cpu_vendor":cpu_vendor,
        "lll_available":Path("/sys/module/legion_laptop").exists(),
        "legionaura":_which("legionaura"),"envycontrol":_which("envycontrol"),
    }
    return cap

def load_hardware() -> dict:
    try:
        if HARDWARE_CFG.exists(): return json.loads(HARDWARE_CFG.read_text())
    except: pass
    return {}

def save_hardware(cap: dict):
    try:
        cap["_detected_at"]=int(time.time())
        HARDWARE_CFG.parent.mkdir(parents=True,exist_ok=True)
        HARDWARE_CFG.write_text(json.dumps(cap,indent=2))
    except: pass

HW: dict = {}

# ══════════════════════════════════════════════════════════════════════════════
# SENSOR READERS
# ══════════════════════════════════════════════════════════════════════════════
def _find_hwmon(name):
    for base in [Path("/sys/class/hwmon"),Path("/sys/devices/virtual/hwmon")]:
        if not base.exists(): continue
        try:
            for p in base.iterdir():
                nf = p/"name"
                if nf.exists() and nf.read_text().strip()==name:
                    return p
        except: pass
    return None

def get_cpu_temp():
    h = _find_hwmon("k10temp")
    if h:
        for f in sorted(h.glob("temp*_input")):
            try: return int(f.read_text())//1000
            except: pass
    return 0

def get_cpu_freq_ghz():
    try:
        return round(int(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq").read_text())/1_000_000,2)
    except: return 0.0

def get_fan_rpm():
    h = _find_hwmon("legion_hwmon"); fans=[]
    if h:
        for f in sorted(h.glob("fan*_input")):
            try: fans.append(int(f.read_text()))
            except: pass
    while len(fans)<2: fans.append(0)
    return fans[0], fans[1]

def get_cpu_hw_max_mhz():
    best=0
    for i in range(16):
        try:
            v=int(Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq").read_text())//1000
            if v>best: best=v
        except: break
    try:
        bl=int(Path("/sys/devices/system/cpu/cpufreq/policy0/bios_limit").read_text())//1000
        if bl>best: best=bl
    except: pass
    return best if best>=3000 else 4400

def _find_rapl_energy_file():
    try:
        for p in sorted(Path("/sys/class/powercap").iterdir()):
            try:
                name=(p/"name").read_text().strip().lower()
                if "package" in name or "psys" in name:
                    ef=p/"energy_uj"
                    if ef.exists(): return ef
            except: pass
    except: pass
    h=_find_hwmon("k10temp")
    if h:
        for f in h.glob("power*_input"):
            return f
    return None

def get_epp():
    try: return Path("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference").read_text().strip()
    except: return "default"

def set_epp(val):
    paths=[f"/sys/devices/system/cpu/cpu{i}/cpufreq/energy_performance_preference"
           for i in range(32) if Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/energy_performance_preference").exists()]
    if paths:
        cmd = " && ".join(f"echo {val} > {p}" for p in paths)
        subprocess.Popen(["pkexec","sh","-c",cmd],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def get_governor():
    try: return Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()
    except: return "\u2014"

def get_battery_pct():
    try:
        n=int(rdsys("/sys/class/power_supply/BAT0/energy_now"))
        f=int(rdsys("/sys/class/power_supply/BAT0/energy_full","1"))
        return min(100,int(n*100/f))
    except: return 0

def get_battery_status(): return rdsys("/sys/class/power_supply/BAT0/status","Unknown")

def get_battery_health():
    try:
        f=int(rdsys("/sys/class/power_supply/BAT0/energy_full","1"))
        d=int(rdsys("/sys/class/power_supply/BAT0/energy_full_design","1"))
        return min(100,int(f*100/d))
    except: return 0

bat_stat_cache = {}
def get_battery_stats():
    s={}
    s["percent"]=get_battery_pct()
    s["status"]=get_battery_status()
    s["health"]=get_battery_health()
    s["cycles"]=rdsys("/sys/class/power_supply/BAT0/cycle_count","\u2014")
    _bat_temp=None
    for bat_path in [Path("/sys/class/power_supply/BAT0"),Path("/sys/class/power_supply/BAT1")]:
        for fn in ["temp","temp_now"]:
            try:
                v=int((bat_path/fn).read_text().strip())
                if v>0: _bat_temp=v//10 if v>1000 else v; break
            except: pass
        if _bat_temp: break
    s["temp"]=f"{_bat_temp} \u00b0C" if _bat_temp else "\u2014"
    try: s["power"]=f"{int(rdsys('/sys/class/power_supply/BAT0/power_now','0'))/1_000_000:.1f} W"
    except: s["power"]="\u2014"
    try: s["voltage"]=f"{int(rdsys('/sys/class/power_supply/BAT0/voltage_now','0'))/1_000_000:.2f} V"
    except: s["voltage"]="\u2014"
    try:
        ef=int(rdsys("/sys/class/power_supply/BAT0/energy_full","0"))
        ed=int(rdsys("/sys/class/power_supply/BAT0/energy_full_design","0"))
        s["capacity"]=f"{ef//1000} mWh / {ed//1000} mWh (design)"
    except: s["capacity"]="\u2014"
    s["manufacturer"]=rdsys("/sys/class/power_supply/BAT0/manufacturer","\u2014")
    s["model_name"]=rdsys("/sys/class/power_supply/BAT0/model_name","\u2014")
    s["technology"]=rdsys("/sys/class/power_supply/BAT0/technology","\u2014")
    return s

def get_ram_info():
    try:
        d={}
        with open("/proc/meminfo") as f:
            for line in f:
                if ":" in line:
                    k,v=line.split(":",1)
                    d[k.strip()]=int(v.strip().split()[0])
        total=d.get("MemTotal",0)
        avail=d.get("MemAvailable",0)
        used=max(0,total-avail)
        pct=int(used*100/max(total,1))
        return used//1024,total//1024,pct
    except: return 0,0,0

def get_igpu_power_w():
    h=_find_hwmon("amdgpu")
    if h:
        for f in h.glob("power*_input"):
            try: return round(int(f.read_text())/1_000_000,1)
            except: pass
    h2=_find_hwmon("k10temp")
    if h2:
        for f in h2.glob("power*_input"):
            try: return round(int(f.read_text())/1_000_000,1)
            except: pass
    return None

_gpu_cache={}; _gpu_last=0.0; _GPU_LOCK=threading.Lock()
def get_gpu_info():
    global _gpu_cache,_gpu_last
    with _GPU_LOCK:
        now=time.time()
        if now-_gpu_last<1.4: return _gpu_cache
        try:
            out=subprocess.check_output(
                ["nvidia-smi","--query-gpu=utilization.gpu,temperature.gpu,clocks.current.graphics,"
                 "memory.used,memory.total,pstate,power.draw,name",
                 "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL,text=True,timeout=2
            ).strip().split(",")
            if len(out)>=8:
                _gpu_cache={"util":int(out[0]),"temp":int(out[1]),"freq":int(out[2]),
                            "mem_used":int(out[3]),"mem_total":int(out[4]),
                            "pstate":out[5],"power":float(out[6]),"name":out[7],"available":True}
                _gpu_last=now
                return _gpu_cache
        except: pass
        _gpu_cache={"available":False}; _gpu_last=now
        return _gpu_cache

def get_ai_engine():
    paths=[Path("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/ai_mode"),
           Path("/sys/bus/platform/devices/VPC2004:00/ai_mode")]
    ai=next((p for p in paths if p.exists()),None)
    if ai: return rdsys(ai,"0")
    return None

def set_ai_engine(enabled: bool):
    paths=[Path("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/ai_mode"),
           Path("/sys/bus/platform/devices/VPC2004:00/ai_mode")]
    ai=next((p for p in paths if p.exists()),None)
    if ai:
        wrsys(ai,"1" if enabled else "0")
        return True
    if enabled: set_epp("balance_performance")
    else: set_epp("default")
    return False

# ══════════════════════════════════════════════════════════════════════════════
# CPU TDP
# ══════════════════════════════════════════════════════════════════════════════
def _rapl_power_paths():
    try:
        for p in sorted(Path("/sys/class/powercap").iterdir()):
            try:
                name=(p/"name").read_text().strip().lower()
                if "package" in name or "psys" in name or name.startswith("amd"):
                    pl1=p/"constraint_0_power_limit_uw"
                    pl2=p/"constraint_1_power_limit_uw"
                    if pl1.exists(): return pl1, pl2 if pl2.exists() else None
            except: pass
    except: pass
    return None,None

def get_cpu_tdp():
    pl1_path,pl2_path=_rapl_power_paths()
    try:
        pl1=int(rdsys(pl1_path,"0"))//1_000_000 if pl1_path else 0
        pl2=int(rdsys(pl2_path,"0"))//1_000_000 if pl2_path else 0
        return pl1,pl2
    except: return 0,0

def set_cpu_tdp(pl1_w:int,pl2_w:int):
    pl1_path,pl2_path=_rapl_power_paths()
    if pl1_path: wrsys(pl1_path,str(pl1_w*1_000_000))
    if pl2_path and pl2_w>0: wrsys(pl2_path,str(pl2_w*1_000_000))
    send_notif("CPU TDP Set",f"PL1: {pl1_w}W  PL2: {pl2_w}W","cpu")

# ══════════════════════════════════════════════════════════════════════════════
# GPU OC
# ══════════════════════════════════════════════════════════════════════════════
def apply_gpu_oc(core_off:int,mem_off:int,power_limit_w:int):
    errors=[]
    if power_limit_w>0:
        try:
            r=subprocess.run(["nvidia-smi","-i","0","-pl",str(power_limit_w)],
                             capture_output=True,text=True,timeout=5)
            if r.returncode!=0: errors.append(f"PL: {r.stderr.strip()[:60]}")
        except Exception as e: errors.append(str(e))
    if core_off!=0:
        try:
            subprocess.Popen(["nvidia-settings","-a",
                             f"[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels={core_off}"],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: errors.append("nvidia-settings not found")
    if mem_off!=0:
        try:
            subprocess.Popen(["nvidia-settings","-a",
                             f"[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels={mem_off}"],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: pass
    msg=f"Core +{core_off} MHz | Mem +{mem_off} MHz | PL {power_limit_w}W"
    if errors: msg+=f" \u26a0 {errors[0]}"
    send_notif("GPU OC Applied",msg,"gpu")

def reset_gpu_oc():
    try:
        subprocess.Popen(["nvidia-smi","--reset-gpu-clocks"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.Popen(["nvidia-smi","--reset-memory-clocks"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except: pass
    try:
        subprocess.Popen(["nvidia-settings","-a","[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels=0",
                         "-a","[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels=0",
                         "-a","[gpu:0]/GPUFanControlState=0"],
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except: pass
    send_notif("GPU OC Reset","All values reset to default","gpu")

# ══════════════════════════════════════════════════════════════════════════════
# FAN CONTROL
# ══════════════════════════════════════════════════════════════════════════════
FAN_PRESETS = {
    "Quiet":(20,20),"Balanced":(50,50),
    "Performance":(75,80),"Turbo":(90,95),"Full Speed":(100,100),
}

def _fan_hwmon():
    return _find_hwmon("legion_hwmon")

def _fan_hwmon_info():
    h=_fan_hwmon()
    if not h: return {"found":False}
    return {"found":True,"path":str(h),"pwm1":(h/"pwm1").exists(),"pwm2":(h/"pwm2").exists(),
            "pwm1_enable":(h/"pwm1_enable").exists(),"pwm2_enable":(h/"pwm2_enable").exists()}

def get_fan_pwm():
    h=_fan_hwmon()
    if not h: return 128,128
    try: c=int((h/"pwm1").read_text())
    except: c=0
    try: g=int((h/"pwm2").read_text())
    except: g=0
    return c,g

def _write_fan_auto():
    cmds=[]
    h=_fan_hwmon()
    if h:
        for f in ["pwm1_enable","pwm2_enable"]:
            p=h/f
            if p.exists(): cmds.append(f"echo 2 > {p}")
    fs=_lazy("fan_fullspeed")
    if fs: cmds.append(f"echo 0 > {fs}")
    if not cmds: return False,"No fan control paths"
    try:
        r=subprocess.run(["pkexec","sh","-c"," && ".join(cmds)],
                         capture_output=True,text=True,timeout=8)
        return r.returncode==0, r.stderr.strip()[:80] if r.returncode!=0 else "Auto"
    except Exception as e: return False,str(e)[:80]

def _write_fan_fullspeed(on:bool):
    fs=_lazy("fan_fullspeed")
    if not fs: return False,"fan_fullspeed not found"
    val="1" if on else "0"
    try:
        r=subprocess.run(["pkexec","sh","-c",f"echo {val} > {fs}"],
                         capture_output=True,text=True,timeout=8)
        return r.returncode==0, r.stderr.strip()[:80] if r.returncode!=0 else ("Full speed ON" if on else "Full speed OFF")
    except Exception as e: return False,str(e)[:80]

def _write_fan_pwm(cpu_pct:int,gpu_pct:int):
    h=_fan_hwmon()
    if not h: return False,"legion_hwmon not found"
    cpu_pwm=int(cpu_pct*255/100); gpu_pwm=int(gpu_pct*255/100)
    cmds=[]
    for en in ["pwm1_enable","pwm2_enable"]:
        p=h/en
        if p.exists(): cmds.append(f"echo 1 > {p}")
    for pwm,val in [("pwm1",cpu_pwm),("pwm2",gpu_pwm)]:
        p=h/pwm
        if p.exists(): cmds.append(f"echo {val} > {p}")
    if not cmds: return False,f"No writable pwm files"
    try:
        r=subprocess.run(["pkexec","sh","-c"," && ".join(cmds)],
                         capture_output=True,text=True,timeout=8)
        if r.returncode==0: return True,f"PWM set: CPU {cpu_pct}%  GPU {gpu_pct}%"
        return False,r.stderr.strip()[:100]
    except Exception as e: return False,str(e)[:100]

def get_fan_lock_status():
    p=_lazy("lockfancontroller")
    if not p: return False
    try: return p.read_text().strip()=="1"
    except: return False

def set_fan_lock(lock:bool):
    p=_lazy("lockfancontroller")
    if not p: return False,"lockfancontroller not found"
    try:
        val="1" if lock else "0"
        r=subprocess.run(["pkexec","sh","-c",f"echo {val} > {p}"],
                         capture_output=True,text=True,timeout=8)
        if r.returncode==0: return True,f"Fan controller {'locked' if lock else 'unlocked'}"
        return False,r.stderr.strip()[:80]
    except Exception as e: return False,str(e)[:80]

def get_minifancurve_status():
    p=_lazy("minifancurve")
    if not p: return False
    try: return p.read_text().strip()=="1"
    except: return False

def set_minifancurve(enable:bool):
    p=_lazy("minifancurve")
    if not p: return False,"minifancurve not found"
    try:
        val="1" if enable else "0"
        r=subprocess.run(["pkexec","sh","-c",f"echo {val} > {p}"],
                         capture_output=True,text=True,timeout=8)
        if r.returncode==0: return True,f"Mini fan curve {'enabled' if enable else 'disabled'}"
        return False,r.stderr.strip()[:80]
    except Exception as e: return False,str(e)[:80]

def get_max_fan_speed_status():
    p=_lazy("maximumfanspeed")
    if not p: return False
    try: return p.read_text().strip()=="1"
    except: return False

def set_max_fan_speed(enable:bool):
    p=_lazy("maximumfanspeed")
    if not p: return False,"maximumfanspeed not found"
    try:
        val="1" if enable else "0"
        r=subprocess.run(["pkexec","sh","-c",f"echo {val} > {p}"],
                         capture_output=True,text=True,timeout=8)
        if r.returncode==0: return True,f"Max fan speed {'enabled' if enable else 'disabled'}"
        return False,r.stderr.strip()[:80]
    except Exception as e: return False,str(e)[:80]

def load_fan_config():
    try:
        if FAN_CFG.exists(): return json.loads(FAN_CFG.read_text())
    except: pass
    return {"mode":"auto","cpu_pct":50,"gpu_pct":50,"preset":"Balanced"}

def save_fan_config(data):
    try:
        FAN_CFG.parent.mkdir(parents=True,exist_ok=True)
        FAN_CFG.write_text(json.dumps(data,indent=2))
    except: pass

# ── CPU boost path ──────────────────────────────────────────────────────────────
AMD_BOOST = Path("/sys/devices/system/cpu/cpufreq/boost")

def get_ic_temp() -> int:
    h = _find_hwmon("legion_hwmon")
    if h:
        for f in [h/"temp3_input", h/"temp4_input"]:
            if f.exists():
                try: return int(f.read_text()) // 1000
                except: pass
    return 0

# ── LLL Fan Curve ──────────────────────────────────────────────────────────────
LLL_FANCURVE_DEBUGFS=Path("/sys/kernel/debug/legion/fancurve")

def is_lll_available():
    return Path("/sys/module/legion_laptop").exists() and _fan_hwmon() is not None

def get_lll_status():
    return {
        "module_loaded":Path("/sys/module/legion_laptop").exists(),
        "device_bound":_fan_hwmon() is not None,
        "debugfs_exists":LLL_FANCURVE_DEBUGFS.exists(),
        "has_fancurve":False,
    }

def read_fancurve_from_hw():
    if LLL_FANCURVE_DEBUGFS.exists():
        try: return LLL_FANCURVE_DEBUGFS.read_text()
        except: pass
    return None

def parse_fancurve(text:str):
    lines=text.strip().split("\n")
    if not lines or "fan curve points size:" not in text: return []
    points=[]
    for line in lines[2:]:
        if not line.strip(): continue
        vals=line.split()
        if len(vals)>=12:
            points.append({
                "speed_unit":int(vals[0]),
                "fan1_rpm":int(vals[1])*100 if vals[0]=="3" else 0,
                "fan2_rpm":int(vals[2])*100 if vals[0]=="3" else 0,
                "fan1_pwm":int(vals[3]),"fan2_pwm":int(vals[4]),
                "accel":int(vals[5]),"decel":int(vals[6]),
                "cpu_min":int(vals[7]),"cpu_max":int(vals[8]),
                "gpu_min":int(vals[9]),"gpu_max":int(vals[10]),
                "ic_min":int(vals[11]),"ic_max":int(vals[12]) if len(vals)>12 else 127,
            })
    return points

def write_fancurve_to_hw(points:list[dict]):
    hwmon=_fan_hwmon()
    if not hwmon: return False,"LLL hwmon not found"
    try:
        for i,pt in enumerate(points,1):
            if i>10: break
            base=f"pwm{1 if i<=3 else 2}_auto_point{i}_"
            if "fan1_pwm" in pt:
                subprocess.run(["pkexec","sh","-c",f"echo {pt['fan1_pwm']} > {hwmon/base}pwm"],
                               capture_output=True,timeout=2)
            if "fan2_pwm" in pt:
                other="pwm2_auto_point" if i<=3 else "pwm1_auto_point"
                idx=i if i<=3 else i-3
                subprocess.run(["pkexec","sh","-c",f"echo {pt['fan2_pwm']} > {hwmon}{other}{idx}_pwm"],
                               capture_output=True,timeout=2)
            if "cpu_temp" in pt:
                subprocess.run(["pkexec","sh","-c",f"echo {pt['cpu_temp']} > {hwmon/base}temp"],
                               capture_output=True,timeout=2)
            if "accel" in pt:
                subprocess.run(["pkexec","sh","-c",f"echo {pt['accel']} > {hwmon/base}accel"],
                               capture_output=True,timeout=2)
            if "decel" in pt:
                subprocess.run(["pkexec","sh","-c",f"echo {pt['decel']} > {hwmon/base}decel"],
                               capture_output=True,timeout=2)
        return True,f"Wrote {len(points)} fan curve points"
    except Exception as e: return False,str(e)[:80]

def save_fancurve_to_file(points:list[dict],filename:str):
    try:
        CFG_DIR.mkdir(parents=True,exist_ok=True)
        (CFG_DIR/f"fancurve_{filename}.json").write_text(json.dumps(points,indent=2))
        return True
    except: return False

def load_fancurve_from_file(filename:str):
    try:
        p=CFG_DIR/f"fancurve_{filename}.json"
        if p.exists(): return json.loads(p.read_text())
    except: pass
    return None

# ── Action config ──────────────────────────────────────────────────────────────
def load_actions():
    try:
        from legion_utils import ACTIONS_CFG
        if ACTIONS_CFG.exists(): return json.loads(ACTIONS_CFG.read_text())
    except: pass
    return {"on_ac":"performance","on_battery":"balanced","auto_switch":False}

def save_actions(data):
    try:
        from legion_utils import ACTIONS_CFG
        ACTIONS_CFG.parent.mkdir(parents=True,exist_ok=True)
        ACTIONS_CFG.write_text(json.dumps(data,indent=2))
    except: pass

def apply_actions_now():
    try:
        cfg=load_actions()
        if not cfg.get("auto_switch"): return
        ac=get_ac_connected()
        target=cfg["on_ac"] if ac else cfg["on_battery"]
        current=read_powermode()
        if target!=current:
            apply_profile(target)
            from legion_utils import PROFILE_LABELS
            send_notif("Auto Profile",
                       f"{'AC connected' if ac else 'On battery'} \u2192 {PROFILE_LABELS.get(target,target)}",
                       "battery-charging" if ac else "battery")
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
# DATASAMPLER
# ══════════════════════════════════════════════════════════════════════════════
class DataSampler(QThread):
    data_ready=pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.cpu_util=0; self._running=True; self._last_idle=0; self._last_total=0; self._last_ac=None
        self._rapl_file=_find_rapl_energy_file()
        self._rapl_is_delta=self._rapl_file and "energy_uj" in str(self._rapl_file)
        self._rapl_last_uj=0; self._rapl_last_t=0.0
        try:
            with open("/proc/stat") as f:
                p=f.readline().split()
            self._last_idle=int(p[4]); self._last_total=sum(int(x) for x in p[1:])
        except: pass
        if self._rapl_is_delta and self._rapl_file:
            try: self._rapl_last_uj=int(self._rapl_file.read_text()); self._rapl_last_t=time.monotonic()
            except: pass
    def stop(self): self._running=False; self.wait()
    def _read_cpu_util(self):
        try:
            with open("/proc/stat") as f:
                p=f.readline().split()
            idle=int(p[4]); total=sum(int(x) for x in p[1:])
            di=idle-self._last_idle; dt=total-self._last_total
            self._last_idle=idle; self._last_total=total
            if dt>0: self.cpu_util=max(0,100-int(di*100/dt))
        except: pass
        return self.cpu_util
    def _read_cpu_power(self):
        if not self._rapl_file: return None
        try:
            now=time.monotonic(); val=int(self._rapl_file.read_text())
            if self._rapl_is_delta:
                dt=now-self._rapl_last_t
                if dt>0.05 and self._rapl_last_uj>0:
                    delta=val-self._rapl_last_uj
                    if delta<0: delta+=2**32
                    w=round(delta/dt/1_000_000,1)
                    self._rapl_last_uj=val; self._rapl_last_t=now
                    return w if 0<w<200 else None
                self._rapl_last_uj=val; self._rapl_last_t=now; return None
            return round(val/1_000_000,1)
        except: return None
    def run(self):
        _tick=0
        while self._running:
            try:
                _tick+=1
                util=self._read_cpu_util()
                ac=get_ac_connected(); profile=read_powermode()
                freq=get_cpu_freq_ghz(); temp=get_cpu_temp()
                fan1,fan2=get_fan_rpm()
                pct=get_battery_pct(); bat_status=get_battery_status()
                try: bat_power=f"{int(Path('/sys/class/power_supply/BAT0/power_now').read_text())/1_000_000:.1f} W"
                except: bat_power="\u2014"
                cpu_power=self._read_cpu_power()
                gpu=get_gpu_info()
                if _tick%2==0 or _tick==1:
                    ru,rt,rpct=get_ram_info()
                    boost=rdsys("/sys/devices/system/cpu/cpufreq/boost","0")
                    gov=get_governor(); epp=get_epp(); igpu=get_igpu_power_w()
                    self._cached={"ram_used":ru,"ram_total":rt,"ram_pct":rpct,
                                  "boost":boost,"gov":gov,"epp":epp,"igpu_power":igpu,"vrr_on":False}
                else:
                    c=getattr(self,'_cached',{})
                    ru=c.get("ram_used","\u2014"); rt=c.get("ram_total","\u2014")
                    rpct=c.get("ram_pct",0); boost=c.get("boost","0")
                    gov=c.get("gov","\u2014"); epp=c.get("epp","\u2014")
                    igpu=c.get("igpu_power",None)
                self.data_ready.emit({
                    "cpu_util":util,"cpu_freq":freq,"cpu_temp":temp,
                    "fan1":fan1,"fan2":fan2,
                    "ram_used":ru,"ram_total":rt,"ram_pct":rpct,
                    "bat_pct":pct,"bat_status":bat_status,"bat_power":bat_power,
                    "boost":boost,"gov":gov,"epp":epp,
                    "ac":ac,"profile":profile,"gpu":gpu,
                    "cpu_power":cpu_power,"igpu_power":igpu,
                })
                if ac!=self._last_ac and self._last_ac is not None:
                    apply_actions_now()
                self._last_ac=ac
            except: pass
            time.sleep(1.0)

# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY HELPER
# ══════════════════════════════════════════════════════════════════════════════
def get_display_outputs():
    try:
        out=subprocess.check_output(["kscreen-doctor","-j"],stderr=subprocess.DEVNULL,text=True,timeout=3)
        data=json.loads(out)
        outputs=[]
        for o in data.get("outputs",[]):
            if not o.get("enabled"): continue
            name=o.get("name",""); cur_id=o.get("currentModeId",""); modes=[]; cur_mode=""
            for m in o.get("modes",[]):
                sz=m.get("size",{}); w,h=sz.get("width",0),sz.get("height",0)
                hz=round(m.get("refreshRate",0))
                if not(w and h and hz): continue
                ms=f"{w}x{h}@{hz}"; is_c=m.get("id","")==cur_id; modes.append((ms,is_c))
                if is_c: cur_mode=ms
            if modes: outputs.append((name,cur_mode,modes))
        return outputs
    except: return []

def set_refresh_rate(output:str,mode:str):
    try:
        out=subprocess.check_output(["kscreen-doctor","-j"],stderr=subprocess.DEVNULL,text=True,timeout=3)
        data=json.loads(out)
        mode_id=None
        for o in data.get("outputs",[]):
            if o.get("name","")==output:
                res_part,hz_part=mode.split("@"); w_str,h_str=res_part.split("x")
                w,h,hz=int(w_str),int(h_str),int(hz_part)
                for m in o.get("modes",[]):
                    sz=m.get("size",{}); mhz=round(m.get("refreshRate",0))
                    if sz.get("width")==w and sz.get("height")==h and mhz==hz:
                        mode_id=m.get("id",""); break
                break
        idx=_kscreen_output_idx(output,data)
        if mode_id:
            subprocess.Popen(["kscreen-doctor",f"output.{idx}.mode.{mode_id}"],
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["kscreen-doctor",f"output.{idx}.mode.{mode}"],
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        send_notif("Refresh Rate Changed",f"{output}: {mode.replace('@',' @ ')} Hz","display")
    except Exception as e: send_notif("Refresh Rate Error",str(e),"dialog-error")

def _kscreen_output_idx(name:str,data=None):
    if data is None:
        try:
            out=subprocess.check_output(["kscreen-doctor","-j"],stderr=subprocess.DEVNULL,text=True,timeout=3)
            data=json.loads(out)
        except: return 1
    for i,o in enumerate(data.get("outputs",[]),1):
        if o.get("name","")==name: return i
    return 1

def get_vrr_status():
    try:
        out=subprocess.check_output(["kscreen-doctor","-j"],stderr=subprocess.DEVNULL,text=True,timeout=3)
        data=json.loads(out)
        for o in data.get("outputs",[]):
            if o.get("enabled"):
                v=o.get("vrrpolicy",0); return v in (1,2), v
        return False,0
    except: return False,-1

def set_vrr(enabled:bool,output_name:str=""):
    policy="automatic" if enabled else "never"; pi=2 if enabled else 0
    try:
        out=subprocess.check_output(["kscreen-doctor","-j"],stderr=subprocess.DEVNULL,text=True,timeout=3)
        data=json.loads(out)
        targets=([o for o in data.get("outputs",[]) if o.get("name","")==output_name]
                 if output_name else [o for o in data.get("outputs",[]) if o.get("enabled")])
        if not targets: targets=data.get("outputs",[])
        for o in targets:
            n=o.get("name",""); idx=_kscreen_output_idx(n,data)
            try: subprocess.run(["kscreen-doctor",f"output.{idx}.vrrpolicy.{policy}"],capture_output=True,timeout=5)
            except: pass
            _persist_vrr(n,pi)
    except: pass

def _persist_vrr(output_name:str,policy:int):
    kd=Path.home()/".local/share/kscreen"
    if not kd.exists(): return
    try:
        for cf in kd.glob("*"):
            if cf.is_dir(): continue
            try:
                d=json.loads(cf.read_text()); changed=False
                for o in d.get("outputs",[]):
                    if o.get("name","")==output_name: o["vrrpolicy"]=policy; changed=True
                if changed: cf.write_text(json.dumps(d,indent=2))
            except: pass
    except: pass
    try:
        subprocess.Popen(["dbus-send","--session","--type=signal","/KWin","org.kde.KWin.reloadConfig"],
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
# KBD BACKLIGHT
# ══════════════════════════════════════════════════════════════════════════════
def get_kbd_path():
    for p in [Path("/sys/class/leds/platform::kbd_backlight/brightness"),
              Path("/sys/class/leds/legion::kbd_backlight/brightness")]:
        if p.exists(): return p
    return None

def get_kbd_max_path():
    p=get_kbd_path()
    return p.parent/"max_brightness" if p else None

def get_kbd_brightness():
    p=get_kbd_path()
    if p:
        try: return int(p.read_text().strip())
        except: pass
    return 0

def set_kbd_brightness(val:int):
    p=get_kbd_path()
    if p:
        try:
            p.write_text(str(val)+"\n"); return
        except: pass
        try:
            subprocess.run(["pkexec","sh","-c",f"echo {val} > {p}"],
                           capture_output=True,timeout=2)
        except: pass

def get_kbd_max_brightness():
    p=get_kbd_max_path()
    if p:
        try: return int(p.read_text().strip())
        except: pass
    return 2
