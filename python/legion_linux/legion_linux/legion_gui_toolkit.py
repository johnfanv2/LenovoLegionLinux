#!/usr/bin/env python3
"""Legion Linux Toolkit — Dashboard GUI entry point (thin)"""

import os, sys, json, time, threading
from pathlib import Path

_this_dir = Path(__file__).resolve().parent
if str(_this_dir.parent) not in sys.path:
    sys.path.insert(0, str(_this_dir.parent))

os.environ["QT_QPA_PLATFORM"] = "wayland"
os.environ["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"
os.environ.setdefault("WAYLAND_DISPLAY", "wayland-0")
if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"

_LEGION_ICON = _this_dir / "legion_logo_toolkit.png"

def _legion_icon():
    from PyQt6.QtGui import QIcon as _ic, QPixmap as _px
    pm = _px(str(_LEGION_ICON))
    return _ic(pm) if not pm.isNull() else _ic()

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QSlider, QStackedWidget, QComboBox, QToolTip, QSpinBox,
    QDoubleSpinBox, QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QMetaObject, pyqtSlot
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor

from legion_linux.legion_utils import (
    C_BG, C_SIDEBAR, C_CARD, C_CARD2, C_BORDER, C_TEXT, C_TEXT2, C_TEXT3,
    C_HOVER, C_ACTIVE, C_SHADOW, C_ACCENT, C_GREEN, C_BLUE, C_ORANGE, C_RED, C_PURPLE,
    PROFILES, PROFILE_LABELS, PROFILE_ICONS, PROFILE_DESCS, PROFILE_COLORS,
    send_notif, CFG_DIR, HARDWARE_CFG, FIRST_RUN_FLAG,
    _LANG, _LANG_NAMES, tr, save_language, load_language, _load_theme_colours,
)
from legion_linux.legion_hardware import (
    HW, detect_hardware, load_hardware, save_hardware,
    read_powermode, get_ac_connected, get_cpu_temp, get_cpu_freq_ghz,
    get_fan_rpm, get_battery_pct, get_battery_status, get_ram_info,
    get_gpu_info, get_ic_temp, get_epp, get_governor, is_lll_available,
    get_igpu_power_w, get_vrr_status, get_ai_engine, apply_actions_now,
    AMD_BOOST, _find_rapl_energy_file, rdsys, get_kbd_path,
)
from legion_linux.legion_ui import SidebarBtn
from legion_linux.legion_pages import (
    FirstRunWizard, HomePage, BatteryPage, PerformancePage,
    DisplayPage, SystemPage, PowerOptionsPage, FanPage, ActionsPage,
    AboutPage, LogsPage,
)

# ══════════════════════════════════════════════════════════════════════════════
# DATA SAMPLER
# ══════════════════════════════════════════════════════════════════════════════
class DataSampler(QThread):
    data_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.cpu_util    = 0
        self._running    = True
        self._last_idle  = 0
        self._last_total = 0
        self._last_ac    = None
        self._rapl_file  = _find_rapl_energy_file()
        self._rapl_is_delta = (self._rapl_file and "energy_uj" in str(self._rapl_file))
        self._rapl_last_uj = 0
        self._rapl_last_t  = 0.0
        try:
            with open("/proc/stat") as f:
                p = f.readline().split()
            self._last_idle  = int(p[4])
            self._last_total = sum(int(x) for x in p[1:])
        except: pass
        if self._rapl_is_delta and self._rapl_file:
            try:
                self._rapl_last_uj = int(self._rapl_file.read_text())
                self._rapl_last_t  = time.monotonic()
            except: pass

    def _read_cpu_util(self):
        try:
            with open("/proc/stat") as f:
                p = f.readline().split()
            idle  = int(p[4])
            total = sum(int(x) for x in p[1:])
            di    = idle  - self._last_idle
            dt    = total - self._last_total
            self._last_idle  = idle
            self._last_total = total
            if dt > 0:
                self.cpu_util = max(0, 100 - int(di * 100 / dt))
        except: pass
        return self.cpu_util

    def _read_cpu_power(self):
        if not self._rapl_file:
            return None
        try:
            now = time.monotonic()
            val = int(self._rapl_file.read_text())
            if self._rapl_is_delta:
                dt = now - self._rapl_last_t
                if dt > 0.05 and self._rapl_last_uj > 0:
                    delta_uj = val - self._rapl_last_uj
                    if delta_uj < 0:
                        delta_uj += 2**32
                    watts = round(delta_uj / dt / 1_000_000, 1)
                    self._rapl_last_uj = val
                    self._rapl_last_t  = now
                    return watts if 0 < watts < 200 else None
                self._rapl_last_uj = val
                self._rapl_last_t  = now
                return None
            else:
                return round(val / 1_000_000, 1)
        except: return None

    def run(self):
        _tick = 0
        while self._running:
            try:
                _tick += 1
                util          = self._read_cpu_util()
                ac            = get_ac_connected()
                profile       = read_powermode()
                freq          = get_cpu_freq_ghz()
                temp          = get_cpu_temp()
                fan1, fan2    = get_fan_rpm()
                ic_temp       = get_ic_temp() if is_lll_available() else 0
                pct           = get_battery_pct()
                bat_status    = get_battery_status()
                try:
                    bat_power = f"{int(Path('/sys/class/power_supply/BAT0/power_now').read_text())/1_000_000:.1f} W"
                except: bat_power = "—"
                cpu_power = self._read_cpu_power()
                if _tick % 2 == 0 or _tick == 1:
                    ru, rt, rpct  = get_ram_info()
                    gpu           = get_gpu_info()
                    boost         = rdsys(AMD_BOOST, "0")
                    gov           = get_governor()
                    epp           = get_epp()
                    ai_engine     = get_ai_engine()
                    igpu_power    = get_igpu_power_w()
                    vrr_on, vrr_p = get_vrr_status()
                    self._cached = {
                        "ram_used": ru, "ram_total": rt, "ram_pct": rpct,
                        "gpu": gpu, "boost": boost, "gov": gov, "epp": epp,
                        "ai_engine": ai_engine, "igpu_power": igpu_power,
                        "vrr_on": vrr_on,
                    }
                else:
                    cached = getattr(self, '_cached', {})
                    ru     = cached.get("ram_used",  "—")
                    rt     = cached.get("ram_total",  "—")
                    rpct   = cached.get("ram_pct",    0)
                    gpu    = cached.get("gpu",        {})
                    boost  = cached.get("boost",      "0")
                    gov    = cached.get("gov",        "—")
                    epp    = cached.get("epp",        "—")
                    ai_engine  = cached.get("ai_engine",  False)
                    igpu_power = cached.get("igpu_power", None)
                    vrr_on     = cached.get("vrr_on",     False)

                self.data_ready.emit({
                    "cpu_util":   util,  "cpu_freq":  freq,    "cpu_temp":  temp,
                    "ic_temp":    ic_temp,
                    "fan1":       fan1,  "fan2":      fan2,
                    "ram_used":   ru,    "ram_total": rt,      "ram_pct":   rpct,
                    "bat_pct":    pct,   "bat_status":bat_status,"bat_power":bat_power,
                    "boost":      boost, "gov":       gov,     "epp":       epp,
                    "ac":         ac,    "profile":   profile, "gpu":       gpu,
                    "cpu_power":  cpu_power,  "igpu_power": igpu_power,
                    "ai_engine":  ai_engine,  "vrr_on":     vrr_on,
                })

                if ac != self._last_ac and self._last_ac is not None:
                    apply_actions_now()
                self._last_ac = ac

            except Exception:
                pass
            time.sleep(1.0)

    def stop(self):
        self._running = False
        self.wait()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
_sampler = None

class LegionDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Legion Linux Toolkit")
        self.setWindowIcon(_legion_icon())
        self.setMinimumSize(1060, 680)
        self.resize(1160, 740)
        self._build()
        global _sampler
        _sampler = DataSampler()
        _sampler.data_ready.connect(self._on_data)
        _sampler.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(2000)
        self._start_fnspace_watcher()

    def _build(self):
        self.setStyleSheet(
            f"QMainWindow{{background:{C_BG};}}"
            f"QToolTip{{background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"padding:8px;font-size:12px;border-radius:6px;}}"
            f"QScrollBar:vertical{{background:{C_BG};width:8px;border-radius:4px;}}"
            f"QScrollBar::handle:vertical{{background:{C_TEXT3};border-radius:4px;min-height:40px;}}"
            f"QScrollBar::handle:vertical:hover{{background:{C_TEXT2};}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
            f"QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:transparent;}}"
            f"QSlider::groove:horizontal{{background:{C_BORDER};height:6px;border-radius:3px;}}"
            f"QSlider::sub-page:horizontal{{background:{C_ACCENT};border-radius:3px;}}"
            f"QSlider::handle:horizontal{{background:{C_ACCENT};width:18px;height:18px;"
            f"border-radius:9px;margin:-6px 0;}}"
            f"QSlider::handle:horizontal:hover{{background:{C_TEXT};}}"
            f"QPushButton{{background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:8px;padding:8px 18px;font-size:13px;font-weight:500;}}"
            f"QPushButton:hover{{background:{C_ACCENT};color:#fff;border-color:{C_ACCENT};}}"
            f"QComboBox{{background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:8px;padding:8px 14px;font-size:13px;}}"
            f"QComboBox::drop-down{{border:none;width:24px;}}"
            f"QComboBox QAbstractItemView{{background:{C_CARD2};color:{C_TEXT};"
            f"border:1px solid {C_BORDER};selection-background-color:{C_ACCENT};selection-color:#fff;"
            f"padding:4px;}}"
            f"QSpinBox,QDoubleSpinBox{{background:{C_CARD2};color:{C_TEXT};"
            f"border:1px solid {C_BORDER};border-radius:8px;padding:6px 10px;font-size:13px;}}"
            f"QLineEdit{{background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:8px;padding:8px 12px;font-size:13px;selection-background-color:{C_ACCENT};}}"
        )
        rw = QWidget()
        self.setCentralWidget(rw)
        main = QHBoxLayout(rw)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Sidebar
        sb = QWidget()
        sb.setFixedWidth(220)
        sb.setStyleSheet(f"background:{C_SIDEBAR};")
        sbl = QVBoxLayout(sb)
        sbl.setContentsMargins(0, 0, 0, 0)
        sbl.setSpacing(0)

        # Top logo area
        top_logo = QWidget()
        top_logo.setFixedHeight(64)
        top_logo.setStyleSheet(f"background:{C_SIDEBAR};")
        tl_lay = QHBoxLayout(top_logo)
        tl_lay.setContentsMargins(16, 10, 16, 10)
        tl_lay.setSpacing(10)
        logo_lbl = QLabel()
        from PyQt6.QtGui import QPixmap
        pm = QPixmap(str(_LEGION_ICON))
        if not pm.isNull():
            logo_lbl.setPixmap(pm.scaled(28, 34, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
        logo_lbl.setStyleSheet("background:transparent;")
        logo_lbl.setFixedSize(32, 38)
        title_lbl = QLabel("Legion Toolkit")
        title_lbl.setStyleSheet(f"color:{C_TEXT};font-size:15px;font-weight:700;background:transparent;")
        tl_lay.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        tl_lay.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        tl_lay.addStretch()
        sbl.addWidget(top_logo)

        # Nav buttons
        self.nav_btns = []
        nav = [
            ("🏠", "Home"), ("🔋", "Battery"), ("⚡", "Performance"),
            ("🖥️", "Display"), ("⚙️", "System"),
            ("🚀", "Power Options"), ("🌀", "Fan Control"),
            ("🎯", "Actions"), ("📋", "Logs"), ("ℹ️", "About"),
        ]
        nav_area = QWidget()
        nav_area.setStyleSheet(f"background:{C_SIDEBAR};")
        nav_lay = QVBoxLayout(nav_area)
        nav_lay.setContentsMargins(8, 8, 8, 8)
        nav_lay.setSpacing(4)
        for icon, label in nav:
            btn = SidebarBtn(icon, label)
            btn.clicked.connect(lambda chk, i=len(self.nav_btns): self._switch(i))
            self.nav_btns.append(btn)
            nav_lay.addWidget(btn)
        nav_lay.addStretch()
        sbl.addWidget(nav_area)

        # Bottom spacer
        bottom_area = QWidget()
        bottom_area.setStyleSheet(f"background:{C_SIDEBAR};")
        bottom_lay = QVBoxLayout(bottom_area)
        bottom_lay.setContentsMargins(8, 8, 8, 8)
        bottom_lay.setSpacing(4)
        bottom_lay.addStretch()
        sbl.addWidget(bottom_area)
        main.addWidget(sb)

        # Right side: topbar + stack
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        topbar = QWidget()
        topbar.setFixedHeight(60)
        topbar.setStyleSheet(f"background:{C_BG};")
        tbl = QHBoxLayout(topbar)
        tbl.setContentsMargins(28, 0, 28, 0)
        tbl.setSpacing(12)
        self.page_title = QLabel("Home")
        self.page_title.setStyleSheet(f"color:{C_TEXT};font-size:20px;font-weight:700;letter-spacing:0px;")
        tbl.addWidget(self.page_title)
        tbl.addStretch()
        self.badge = QLabel("")
        self.badge.hide()
        self.ac_ind = QLabel("")
        self.ac_ind.hide()
        self._refresh_badge(read_powermode())
        right.addWidget(topbar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{C_BG};")
        self.home_page = HomePage()
        self.home_page._page_request_cb = self._switch
        self.pages = [
            self.home_page, BatteryPage(), PerformancePage(),
            DisplayPage(), SystemPage(),
            PowerOptionsPage(), FanPage(), ActionsPage(),
            LogsPage(), AboutPage(),
        ]
        self.home_page._sync_battery_cb = self.pages[1].sync_charging
        self.pages[1]._sync_home_cb = self._sync_bat_combo
        for pg in self.pages:
            self.stack.addWidget(pg)
        right.addWidget(self.stack)
        main.addLayout(right)
        self._switch(0)

    def _start_fnspace_watcher(self):
        kbd_path = get_kbd_path()
        if kbd_path is None:
            return

        def _watch():
            last = None
            while True:
                try:
                    val = kbd_path.read_text().strip()
                    if last is not None and val != last:
                        QMetaObject.invokeMethod(
                            self, "_on_fnspace",
                            Qt.ConnectionType.QueuedConnection
                        )
                    last = val
                except: pass
                time.sleep(0.15)

        threading.Thread(target=_watch, daemon=True).start()

    @pyqtSlot()
    def _on_fnspace(self):
        pass

    def _sync_bat_combo(self, idx: int):
        self.home_page.bat_combo.blockSignals(True)
        self.home_page.bat_combo.setCurrentIndex(idx)
        self.home_page.bat_combo.blockSignals(False)

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        titles = [
            "Home", "Battery", "Performance", "Display",
            "System", "Power Options", "Fan", "Actions",
            "Logs", "About",
        ]
        self.page_title.setText(titles[idx])
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == idx)
            btn.update()

    def _refresh_badge(self, profile):
        color = PROFILE_COLORS.get(profile, C_ACCENT)
        label = PROFILE_LABELS.get(profile, profile)
        self.badge.setText(label)
        self.badge.setStyleSheet(
            f"color:{color};font-size:10px;font-weight:600;letter-spacing:1px;"
            f"padding:4px 12px;border:1px solid {color};border-radius:10px;"
        )

    def _on_data(self, d):
        self.home_page.refresh(d)
        self._refresh_badge(d["profile"])
        ac = d["ac"]
        self.ac_ind.setText("⚡ AC" if ac else "🔋 Battery")
        self.ac_ind.setStyleSheet(
            f"color:{C_GREEN if ac else C_ORANGE};font-size:12px;margin-left:12px;"
        )
        idx = self.stack.currentIndex()
        if idx == 2:
            self.pages[2].refresh(d)
        elif idx == 3:
            self.pages[3].refresh(d)
        elif idx == 6:
            self.pages[6].refresh(d)
        elif idx == 7:
            self.pages[7].refresh(d)

    def _tick(self):
        idx = self.stack.currentIndex()
        if idx == 1:
            self.pages[1].refresh()
        elif idx == 7:
            self.pages[7].refresh()

    def closeEvent(self, e):
        global _sampler
        if _sampler:
            _sampler.stop()
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Legion Toolkit")
    app.setQuitOnLastWindowClosed(True)

    load_language()

    global HW
    if FIRST_RUN_FLAG.exists():
        HW = load_hardware()
        if not HW:
            HW = detect_hardware()
            save_hardware(HW)
    else:
        wizard = FirstRunWizard()
        wizard.exec()
        HW = load_hardware()
        if not HW:
            HW = detect_hardware()
            save_hardware(HW)
        FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
        FIRST_RUN_FLAG.touch()

    win = LegionDashboard()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
