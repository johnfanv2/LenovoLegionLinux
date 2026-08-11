#!/usr/bin/env python3
"""
Legion Linux Toolkit — System Tray
Hardware: Lenovo Legion via LLL (LenovoLegionLinux)
Left-click   → open dashboard
Middle-click → cycle power profile
Right-click  → full menu
"""
import os, sys, subprocess, socket
from pathlib import Path

os.environ["QT_QPA_PLATFORM"]                 = "xcb"
os.environ["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"
os.environ.setdefault("WAYLAND_DISPLAY", "wayland-0")
if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"


try:
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import (QIcon, QPixmap, QColor, QPainter,
                              QBrush, QFont, QAction, QActionGroup)
    from PyQt6.QtCore import Qt, QTimer
except ImportError:
    sys.exit("PyQt6 not found — sudo pacman -S python-pyqt6")

# ── Use LLL backend ──────────────────────────────────────────────────────
_lib = Path(__file__).resolve().parent / "lib"
if not (_lib / "lll_adapter.py").exists():
    _lib = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(_lib))
import lll_adapter as lll

GUI_BIN = Path(__file__).parent / "legion-gui.py"

def _send_notif(title, body, icon="dialog-information"):
    """Send a desktop notification via notify-send."""
    uid = os.getuid()
    dbus_addr = f"unix:path=/run/user/{uid}/bus"
    display = os.environ.get("DISPLAY", ":1")
    if icon.startswith("/"):
        hint = ["-h", f"string:image-path:{icon}"]
    else:
        hint = ["-i", icon]
    subprocess.Popen(["env", f"DBUS_SESSION_BUS_ADDRESS={dbus_addr}",
                       f"DISPLAY={display}", "notify-send", "-a", "Legion Toolkit",
                        *hint, "-t", "3000", title, body])

_PROFILE_INFO = {
    "quiet":       {"label": "Quiet",       "icon": "🔵", "color": "#4a9eff", "letter": "Q", "desc": "15W · Silent"},
    "balanced":    {"label": "Balanced",    "icon": "⚪", "color": "#e0e0e0", "letter": "B", "desc": "35W · Everyday"},
    "performance": {"label": "Performance", "icon": "🔴", "color": "#ff4757", "letter": "P", "desc": "54W · Gaming"},
    "custom":      {"label": "Custom",      "icon": "🩷", "color": "#ff69b4", "letter": "C", "desc": "54W · Custom"},
}

def _get_profiles() -> list[str]:
    return ["quiet", "balanced", "performance", "custom"]

def _label(name: str) -> str:
    return _PROFILE_INFO.get(name, {}).get("label", name.title())

def _color(name: str) -> str:
    return _PROFILE_INFO.get(name, {}).get("color", "#888888")

def _make_legion_tray_icon(profile: str) -> QIcon:
    """Colored circle tray icon — no custom branding."""
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(_color(profile))
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, size - 4, size - 4)
    from PyQt6.QtGui import QPen, QFont
    p.setPen(QPen(QColor("#ffffff")))
    f = QFont()
    f.setPixelSize(28)
    f.setBold(True)
    p.setFont(f)
    letter = {"quiet": "Q", "balanced": "B", "performance": "P", "custom": "C"}.get(profile, "?")
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    p.end()
    return QIcon(px)

class LegionTray:
    def __init__(self, app: QApplication):
        self.app      = app
        self._profiles = _get_profiles()
        self._profile  = lll.read_powermode()
        self._suppress_poll = False

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(_make_legion_tray_icon(self._profile))
        self.tray.activated.connect(self._on_click)

        self.menu = QMenu()
        self._build_menu()
        self.tray.setContextMenu(self.menu)
        self._update_tooltip()

        self._timer = QTimer()
        self._timer.timeout.connect(self._poll)
        self._timer.start(500)
        self.tray.show()

    def _build_menu(self):
        self.menu.clear()
        m = self.menu

        h = QAction("⚡  Legion Toolkit", m); h.setEnabled(False)
        m.addAction(h)

        pct = lll.get_battery_pct()
        ac  = lll.get_ac_connected()
        bat_icon = "🔌" if ac else "🔋"
        bat_str = f"{bat_icon}  Battery: {pct}%" if pct >= 0 else f"{bat_icon}  Battery"
        ba = QAction(bat_str, m); ba.setEnabled(False)
        m.addAction(ba)
        m.addSeparator()

        prof_title = QAction("  Power Mode", m); prof_title.setEnabled(False)
        m.addAction(prof_title)

        self._profile_group   = QActionGroup(m)
        self._profile_actions = {}
        self._profile_group.setExclusive(True)

        for p in self._profiles:
            info  = _PROFILE_INFO.get(p, {})
            icon  = info.get("icon", "")
            label = info.get("label", p.title())
            desc  = info.get("desc", "")
            a = QAction(f"  {icon}  {label}  —  {desc}", m)
            a.setCheckable(True)
            a.setChecked(p == self._profile)
            a.triggered.connect(lambda chk, prof=p: self._set_profile(prof))
            self._profile_group.addAction(a)
            m.addAction(a)
            self._profile_actions[p] = a

        m.addSeparator()

        bat_title = QAction("  Battery", m); bat_title.setEnabled(False)
        m.addAction(bat_title)

        has_conservation = lll.find_feature_path("conservation_mode") is not None
        has_rapid = lll.find_feature_path("rapidcharge") is not None
        has_usb = lll.find_feature_path("usb_charging") is not None

        if has_conservation:
            cons = lll.get_conservation_mode()
            self._cons_action = QAction(
                ("🔋  Conservation Mode  ●" if cons else "🔋  Conservation Mode  ○"), m)
            self._cons_action.triggered.connect(self._toggle_conservation)
            m.addAction(self._cons_action)
        if has_rapid:
            rapid = lll.get_rapid_charge()
            self._rapid_action = QAction(
                ("⚡  Rapid Charge  ●" if rapid else "🐢  Rapid Charge  ○"), m)
            self._rapid_action.triggered.connect(self._toggle_rapid)
            m.addAction(self._rapid_action)
        if has_usb:
            self._usb_menu = QMenu("🔌  USB Charging")
            usb_mode = lll.get_usb_charging_mode()
            self._usb_actions = []
            for i, label in enumerate(lll.USB_CHARGING_LABELS):
                a = QAction(label, m)
                a.setCheckable(True)
                a.setChecked(i == usb_mode)
                a.triggered.connect(lambda checked, idx=i: self._set_usb_mode(idx))
                self._usb_actions.append(a)
                self._usb_menu.addAction(a)
            m.addAction(self._usb_menu.menuAction())
        m.addSeparator()

        disp_title = QAction("  Display", m); disp_title.setEnabled(False)
        m.addAction(disp_title)
        od_val = lll.get_overdrive()
        self._od_action = QAction(
            ("🖥️   Display Overdrive  ●" if od_val else "🖥️   Display Overdrive  ○"), m)
        self._od_action.triggered.connect(self._toggle_overdrive)
        m.addAction(self._od_action)

        gsync_val = lll.get_gsync()
        self._gsync_action = QAction(
            ("🔄  G-Sync  ●" if gsync_val else "🔄  G-Sync  ○"), m)
        self._gsync_action.triggered.connect(self._toggle_gsync)
        m.addAction(self._gsync_action)
        m.addSeparator()

        sys_title = QAction("  System", m); sys_title.setEnabled(False)
        m.addAction(sys_title)
        has_fn = lll.find_feature_path("fn_lock") is not None
        has_cam = lll.find_feature_path("camera_power") is not None
        wk = lll.get_winkey()
        if has_fn:
            fn = lll.get_fn_lock()
            self._fn_action = QAction(("⌨️   Fn Lock  ●" if fn else "⌨️   Fn Lock  ○"), m)
            self._fn_action.triggered.connect(self._toggle_fn)
            m.addAction(self._fn_action)
        if has_cam:
            cam = lll.get_camera_power()
            self._cam_action = QAction(("📷  Camera  ●" if cam else "📷  Camera  ○"), m)
            self._cam_action.triggered.connect(self._toggle_cam)
            m.addAction(self._cam_action)
        self._winkey_action = QAction(("🪟  Super Key  ●" if wk else "🪟  Super Key  ○"), m)
        self._winkey_action.triggered.connect(self._toggle_winkey)
        m.addAction(self._winkey_action)
        m.addSeparator()
        m.addSeparator()

        fan_title = QAction("  Fan", m); fan_title.setEnabled(False)
        m.addAction(fan_title)
        fan_val = lll.get_fan_fullspeed()
        self._fan_action = QAction(
            ("🌀  Fan Full Speed  ●" if fan_val else "🌀  Fan Full Speed  ○"), m)
        self._fan_action.triggered.connect(self._toggle_fan)
        m.addAction(self._fan_action)
        m.addSeparator()

        boost = lll.get_cpu_boost()
        s = QAction(f"  CPU Boost: {'ON' if boost else 'OFF'}", m)
        s.setEnabled(False)
        m.addAction(s)
        m.addSeparator()

        dash = QAction("📊  Open Dashboard", m)
        dash.triggered.connect(self._open_dashboard)
        m.addAction(dash)
        m.addSeparator()

        quit_a = QAction("✕  Quit", m)
        quit_a.triggered.connect(self.app.quit)
        m.addAction(quit_a)

    def _update_tooltip(self):
        lbl = _label(self._profile)
        pct = lll.get_battery_pct()
        bat = f" · 🔋 {pct}%" if pct >= 0 else ""
        self.tray.setToolTip(f"Legion Toolkit — {lbl}{bat}")

    def _on_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._open_dashboard()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self._cycle()

    def _open_dashboard(self):
        try:
            subprocess.run(["pkill", "-f", "legion-gui.py"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        import time as _t; _t.sleep(0.15)
        try:
            subprocess.Popen(
                ["python3", str(GUI_BIN)],
                stdout=open("/tmp/legion-gui.log","w"),
                stderr=open("/tmp/legion-gui.log","w")
            )
        except Exception as e:
            self.tray.showMessage("Legion Toolkit",
                                  f"Could not launch dashboard: {e}",
                                  QSystemTrayIcon.MessageIcon.Critical, 4000)

    def _cycle(self):
        profiles = self._profiles
        idx = profiles.index(self._profile) if self._profile in profiles else 0
        self._set_profile(profiles[(idx + 1) % len(profiles)])

    def _set_profile(self, name: str):
        self._suppress_poll = True
        lll.apply_profile(name)
        self._update_ui(name)
        QTimer.singleShot(1500, lambda: setattr(self, "_suppress_poll", False))

    def _tog(self, get_fn, set_fn, action, on_lbl, off_lbl,
             notif_on="", notif_off=""):
        cur = get_fn()
        new = not cur
        set_fn(new)
        action.setText(on_lbl if new else off_lbl)
        msg = notif_on if new else notif_off
        if msg:
            self.tray.showMessage("Legion Toolkit", msg,
                                  QSystemTrayIcon.MessageIcon.Information, 2000)

    def _toggle_conservation(self):
        self._tog(lll.get_conservation_mode, lll.set_conservation_mode,
                  self._cons_action,
                  "🔋  Conservation Mode  ●", "🔋  Conservation Mode  ○",
                  "Conservation ON — charging capped at ~60%",
                  "Conservation OFF — normal charging")

    def _toggle_rapid(self):
        self._tog(lll.get_rapid_charge, lll.set_rapid_charge,
                  self._rapid_action,
                  "⚡  Rapid Charge  ●", "🐢  Rapid Charge  ○",
                  "Rapid charge ON", "Rapid charge OFF")

    def _set_usb_mode(self, idx):
        lll.set_usb_charging_mode(idx)
        for i, a in enumerate(self._usb_actions):
            a.setChecked(i == idx)
        self._usb_menu.setTitle(f"🔌  {lll.USB_CHARGING_LABELS[idx]}")
        self._usb_menu.menuAction().setText(f"🔌  {lll.USB_CHARGING_LABELS[idx]}")

    def _toggle_overdrive(self):
        self._tog(lll.get_overdrive, lll.set_overdrive,
                  self._od_action,
                  "🖥️   Display Overdrive  ●", "🖥️   Display Overdrive  ○",
                  "Display overdrive ON", "Display overdrive OFF")

    def _toggle_gsync(self):
        self._tog(lll.get_gsync, lll.set_gsync,
                  self._gsync_action,
                  "🔄  G-Sync  ●", "🔄  G-Sync  ○",
                  "G-Sync ON", "G-Sync OFF")

    def _toggle_fn(self):
        self._tog(lll.get_fn_lock, lll.set_fn_lock,
                  self._fn_action,
                  "⌨️   Fn Lock  ●", "⌨️   Fn Lock  ○",
                  "Fn Lock ON", "Fn Lock OFF")

    def _toggle_cam(self):
        self._tog(lll.get_camera_power, lll.set_camera_power,
                  self._cam_action,
                  "📷  Camera  ●", "📷  Camera  ○",
                  "Camera ON", "Camera OFF")

    def _toggle_winkey(self):
        self._tog(lll.get_winkey, lll.set_winkey,
                  self._winkey_action,
                  "🪟  Super Key  ●", "🪟  Super Key  ○",
                  "Super key enabled", "Super key disabled")

    def _toggle_fan(self):
        self._tog(lll.get_fan_fullspeed, lll.set_fan_fullspeed,
                  self._fan_action,
                  "🌀  Fan Full Speed  ●", "🌀  Fan Full Speed  ○",
                  "Fan → full speed", "Fan → auto")

    def _update_ui(self, profile: str):
        self._profile = profile
        self.tray.setIcon(_make_legion_tray_icon(profile))
        self._update_tooltip()
        if profile in self._profile_actions:
            self._profile_actions[profile].setChecked(True)

    def _poll(self):
        if self._suppress_poll:
            return
        current = lll.read_powermode()
        if current != self._profile:
            lll.set_cpu_boost(current in ("balanced", "performance"))
            icon_map = {
                "quiet": "power-profile-balanced",
                "balanced": "power-profile-balanced",
                "performance": "power-profile-performance",
                "custom": "power-profile-custom",
            }
            icon = icon_map.get(current, "dialog-information")
            label = _PROFILE_INFO.get(current, {}).get("label", current.title())
            _send_notif("Power Mode", f"Switched to {label}", icon)
            self._update_ui(current)
            self._build_menu()
            self.tray.setContextMenu(self.menu)
        else:
            self._update_tooltip()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Legion Toolkit")
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        _send_notif("Legion Toolkit", "System tray not available — running silently", "dialog-warning")
        # Don't exit — keep running so notifications still work
    LegionTray(app)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
