#!/usr/bin/env python3
"""Legion Linux Toolkit — pure utilities (translations, theme, icon, config paths)"""

import os, sys, subprocess, json
from pathlib import Path

_this_dir = Path(__file__).resolve().parent
_src_root = _this_dir.parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

# ── Config paths ──────────────────────────────────────────────────────────────
CFG_DIR = Path.home() / ".config/legion-toolkit"
OC_CFG = CFG_DIR / "overclock.json"
FAN_CFG = CFG_DIR / "fan.json"
APP_CFG = CFG_DIR / "appearance.json"
HARDWARE_CFG = CFG_DIR / "hardware.json"
LANG_CFG = CFG_DIR / "language.json"
ACTIONS_CFG = CFG_DIR / "actions.json"
FIRST_RUN_FLAG = CFG_DIR / "first_run_done"

# ── Translations ──────────────────────────────────────────────────────────────
_LANG = "en"
_TR = {
    "en": {
        "app_name":"Legion Linux Toolkit","home":"Home","battery":"Battery",
        "performance":"Performance","display":"Display",
        "system":"System","overclock":"Power Options","fan":"Fan","actions":"Actions",
        "about":"About","logs":"Logs",
        "power_mode":"Power Mode","battery_mode":"Battery Mode",
        "gpu_mode":"GPU Working Mode","apply":"Apply","save":"Save",
        "enabled":"Enabled","disabled":"Disabled","on":"ON","off":"OFF",
        "auto":"Auto","full_speed":"Full Speed",
        "brightness":"Brightness","theme":"Theme",
        "conservation":"Conservation (~60%)","rapid_charge":"Rapid Charge",
        "normal":"Normal","quiet":"Quiet","balanced":"Balanced",
        "performance_label":"Performance","custom":"Custom",
    },
}
_LANG_NAMES = {"en":"English"}

def tr(key: str) -> str:
    return _TR.get(_LANG, _TR["en"]).get(key, _TR["en"].get(key, key))

def load_language():
    global _LANG
    try:
        if LANG_CFG.exists():
            _LANG = json.loads(LANG_CFG.read_text()).get("lang","en")
    except: _LANG = "en"

def save_language(lang: str):
    global _LANG
    _LANG = lang
    try:
        LANG_CFG.parent.mkdir(parents=True, exist_ok=True)
        LANG_CFG.write_text(json.dumps({"lang": lang}))
    except: pass

# ── Theme ──────────────────────────────────────────────────────────────────────
_THEMES = {
    "dark": {
        "C_BG":"#0d0d0d","C_SIDEBAR":"#111111","C_CARD":"#181818",
        "C_CARD2":"#222222","C_BORDER":"#2a2a2a","C_TEXT":"#e5e5e5",
        "C_TEXT2":"#999999","C_TEXT3":"#666666","C_HOVER":"#1a1a1a",
        "C_ACTIVE":"#252525","C_SHADOW":"#000000",
    },
    "dark_dimmed": {
        "C_BG":"#151515","C_SIDEBAR":"#1a1a1a","C_CARD":"#1e1e1e",
        "C_CARD2":"#262626","C_BORDER":"#333333","C_TEXT":"#e0e0e0",
        "C_TEXT2":"#999999","C_TEXT3":"#666666","C_HOVER":"#222222",
        "C_ACTIVE":"#2d2d2d","C_SHADOW":"#000000",
    },
    "oled_black": {
        "C_BG":"#000000","C_SIDEBAR":"#050505","C_CARD":"#0a0a0a",
        "C_CARD2":"#111111","C_BORDER":"#1a1a1a","C_TEXT":"#e0e0e0",
        "C_TEXT2":"#888888","C_TEXT3":"#555555","C_HOVER":"#0f0f0f",
        "C_ACTIVE":"#151515","C_SHADOW":"#000000",
    },
    "light": {
        "C_BG":"#f5f5f5","C_SIDEBAR":"#eaeaea","C_CARD":"#ffffff",
        "C_CARD2":"#f0f0f0","C_BORDER":"#e0e0e0","C_TEXT":"#1a1a1a",
        "C_TEXT2":"#666666","C_TEXT3":"#999999","C_HOVER":"#eeeeee",
        "C_ACTIVE":"#e5e5e5","C_SHADOW":"#cccccc",
    },
}
C_BG = "#0d0d0d"; C_SIDEBAR = "#111111"; C_CARD = "#181818"
C_CARD2 = "#222222"; C_BORDER = "#2a2a2a"; C_TEXT = "#e5e5e5"
C_TEXT2 = "#999999"; C_TEXT3 = "#666666"; C_HOVER = "#1a1a1a"
C_ACTIVE = "#252525"; C_SHADOW = "#000000"
C_ACCENT = "#cc3333"; C_GREEN = "#4ecb71"; C_BLUE = "#4a9eff"
C_ORANGE = "#ffa724"; C_RED = "#ff4757"; C_PURPLE = "#a855f7"

def _load_theme_colours():
    global C_BG, C_SIDEBAR, C_CARD, C_CARD2, C_BORDER, C_TEXT, C_TEXT2, C_TEXT3
    global C_HOVER, C_ACTIVE, C_SHADOW
    try:
        cfg = json.loads(APP_CFG.read_text()) if APP_CFG.exists() else {}
        t = _THEMES.get(cfg.get("theme","dark"), _THEMES["dark"])
    except:
        t = _THEMES["dark"]
    C_BG=t["C_BG"]; C_SIDEBAR=t["C_SIDEBAR"]; C_CARD=t["C_CARD"]; C_CARD2=t["C_CARD2"]
    C_BORDER=t["C_BORDER"]; C_TEXT=t["C_TEXT"]; C_TEXT2=t["C_TEXT2"]; C_TEXT3=t["C_TEXT3"]
    C_HOVER=t["C_HOVER"]; C_ACTIVE=t["C_ACTIVE"]; C_SHADOW=t["C_SHADOW"]

_load_theme_colours()

# ── Profile constants ──────────────────────────────────────────────────────────
PROFILES = ["quiet","balanced","performance","custom"]
PROFILE_LABELS = {"quiet":"Quiet","balanced":"Balanced","performance":"Performance","custom":"Custom"}
PROFILE_ICONS = {"quiet":"\U0001f535","balanced":"\u26aa","performance":"\U0001f534","custom":"\U0001fa77"}
PROFILE_DESCS = {"quiet":"15W \u00b7 Boost OFF","balanced":"35W \u00b7 Boost ON",
                 "performance":"54W \u00b7 Boost ON","custom":"54W \u00b7 Custom Config"}
PROFILE_COLORS = {"quiet":"#4a9eff","balanced":"#d0d0d0","performance":"#ff4757","custom":"#ff69b4"}
EPP_VALUES = ["default","performance","balance_performance","balance_power","power"]
EPP_LABELS = {"default":"Default","performance":"Performance",
              "balance_performance":"Balance Performance",
              "balance_power":"Balance Power","power":"Power Save"}

# ── Icon (file-based) ─────────────────────────────────────────────────────────
_ICON_DIR = _this_dir
_LEGION_ICON_PATH = _ICON_DIR / "legion_logo_toolkit.png"

def get_icon_path():
    return str(_LEGION_ICON_PATH)

def legion_icon():
    from PyQt6.QtGui import QIcon as _ic, QPixmap as _px
    pm = _px(str(_LEGION_ICON_PATH))
    return _ic(pm) if not pm.isNull() else _ic()

# ── Notification ──────────────────────────────────────────────────────────────
def send_notif(title: str, body: str = "", icon: str = "computer"):
    try:
        subprocess.Popen(
            ["notify-send","-a","Legion Toolkit","-i",icon,"-t","3000",title,body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except: pass
