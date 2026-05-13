#!/usr/bin/env python3
"""Legion Linux Toolkit — all page classes (Home, Battery, Performance, Display, System, PowerOptions, Fan, Actions, About)"""

import os, sys, subprocess, json, time, threading, base64
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy, QSlider, QStackedWidget, QComboBox,
    QSpinBox, QLineEdit, QDialog, QProgressBar, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QTimer, QMetaObject, Q_ARG, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap, QColor

from .legion_utils import (
    C_BG, C_SIDEBAR, C_CARD, C_CARD2, C_BORDER, C_TEXT, C_TEXT2, C_TEXT3,
    C_HOVER, C_ACTIVE, C_SHADOW, C_ACCENT, C_GREEN, C_BLUE, C_ORANGE, C_RED, C_PURPLE,
    send_notif, CFG_DIR, APP_CFG, HARDWARE_CFG, FIRST_RUN_FLAG,
    PROFILES, PROFILE_LABELS, PROFILE_ICONS, PROFILE_DESCS, PROFILE_COLORS,
    EPP_VALUES, EPP_LABELS, _LANG, _LANG_NAMES, tr, save_language, legion_icon,
    get_icon_path, _load_theme_colours, load_language,
)
from .legion_ui import (
    BarFill, StatRow, InfoRow, ToggleSwitch, NotifyToggle,
    StatusBadge, AIBadge, ProfileBtn, SidebarBtn, FanWidget,
    _mk_lbl, _mk_lineedit, make_div, make_card, combo_style, scrollable,
)
from .legion_hardware import (
    HW, detect_hardware, load_hardware, save_hardware,
    read_powermode, apply_profile, get_ac_connected,
    rdsys, wrsys, _find_feature, _find_ideapad,
    get_cpu_temp, get_cpu_freq_ghz, get_fan_rpm, get_ram_info,
    get_battery_pct, get_battery_status, get_battery_health, get_battery_stats,
    get_gpu_info, get_igpu_power_w, get_epp, set_epp, get_governor,
    get_cpu_hw_max_mhz, get_cpu_tdp, set_cpu_tdp,
    get_ai_engine, set_ai_engine,
    apply_gpu_oc, reset_gpu_oc,
    FAN_PRESETS, load_fan_config, save_fan_config, get_fan_lock_status, get_fan_pwm,
    set_fan_lock, get_minifancurve_status, set_minifancurve, set_max_fan_speed,
    _write_fan_auto, _write_fan_fullspeed, _write_fan_pwm,
    _fan_hwmon_info, _fan_hwmon,
    is_lll_available, get_lll_status,
    read_fancurve_from_hw, parse_fancurve, write_fancurve_to_hw,
    save_fancurve_to_file, load_fancurve_from_file,
    load_actions, save_actions, apply_actions_now,
    get_display_outputs, set_refresh_rate, get_vrr_status, set_vrr,
    get_kbd_brightness, get_kbd_max_brightness, set_kbd_brightness,
    _dmi,
)

_ICON_DIR = Path(__file__).resolve().parent
_LEGION_ICON_PATH = _ICON_DIR / "legion_logo_toolkit.png"

# ══════════════════════════════════════════════════════════════════════════════
# FIRST-RUN WIZARD
# ══════════════════════════════════════════════════════════════════════════════
class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Legion Linux Toolkit \u2014 Setup")
        self.setFixedSize(560, 440)
        self.setWindowIcon(legion_icon())
        self.setStyleSheet(f"QDialog{{background:{C_BG};}}QLabel{{color:{C_TEXT};background:transparent;}}"
            f"QPushButton{{background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:8px;padding:10px 24px;font-size:13px;}}"
            f"QPushButton:hover{{background:{C_ACCENT};color:#fff;border-color:{C_ACCENT};}}"
            f"QListWidget{{background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;color:{C_TEXT};font-size:13px;}}"
            f"QListWidget::item:selected{{background:{C_ACCENT};color:#fff;border-radius:6px;}}"
            f"QListWidget::item:hover{{background:{C_CARD2};}}")
        self._build()

    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(32,28,32,24); root.setSpacing(0)
        logo_row=QHBoxLayout()
        pm=QPixmap(str(_LEGION_ICON_PATH))
        logo=QLabel(); logo.setPixmap(pm.scaled(44,52,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        logo_row.addWidget(logo); logo_row.addSpacing(14)
        an=QLabel("Legion Linux Toolkit"); an.setStyleSheet(f"color:{C_TEXT};font-size:20px;font-weight:600;")
        logo_row.addWidget(an); logo_row.addStretch(); root.addLayout(logo_row); root.addSpacing(20)
        self._stack=QStackedWidget()
        self._stack.addWidget(self._pg_lang()); self._stack.addWidget(self._pg_detect()); self._stack.addWidget(self._pg_done())
        root.addWidget(self._stack,1); root.addSpacing(16)
        br=QHBoxLayout(); br.addStretch()
        self._back=QPushButton("\u2190 Back"); self._back.setVisible(False); self._back.clicked.connect(self._gb)
        self._next=QPushButton("Next \u2192"); self._next.clicked.connect(self._gn)
        self._next.setStyleSheet(f"QPushButton{{background:{C_ACCENT};color:#fff;border:none;border-radius:6px;padding:8px 24px;font-size:13px;font-weight:600;}}QPushButton:hover{{background:#aa2222;}}")
        br.addWidget(self._back); br.addWidget(self._next); root.addLayout(br)
        self._hw_result={}

    def _pg_lang(self):
        w=QWidget(); w.setStyleSheet("background:transparent;")
        lay=QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        t=QLabel("Choose Your Language"); t.setStyleSheet(f"color:{C_TEXT};font-size:16px;font-weight:600;")
        d=QLabel("Select the language for the interface."); d.setStyleSheet(f"color:{C_TEXT2};font-size:12px;")
        lay.addWidget(t); lay.addWidget(d); lay.addSpacing(8)
        self._ll=QListWidget(); self._ll.setFixedHeight(220)
        saved=_LANG; sr=0
        for i,(code,name) in enumerate(_LANG_NAMES.items()):
            item=QListWidgetItem(f"  {name}"); item.setData(Qt.ItemDataRole.UserRole,code); self._ll.addItem(item)
            if code==saved: sr=i
        self._ll.setCurrentRow(sr); self._ll.itemClicked.connect(self._on_lang)
        lay.addWidget(self._ll); return w

    def _pg_detect(self):
        w=QWidget(); w.setStyleSheet("background:transparent;")
        lay=QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        self._dt=QLabel("Hardware Detection"); self._dt.setStyleSheet(f"color:{C_TEXT};font-size:16px;font-weight:600;")
        self._dd=QLabel("Scanning your device for supported features.\nThis runs once and the result is saved.")
        self._dd.setStyleSheet(f"color:{C_TEXT2};font-size:12px;"); self._dd.setWordWrap(True)
        lay.addWidget(self._dt); lay.addWidget(self._dd); lay.addSpacing(12)
        self._pr=QProgressBar(); self._pr.setRange(0,0); self._pr.setFixedHeight(6); self._pr.hide()
        self._pr.setStyleSheet(f"QProgressBar{{background:{C_BORDER};border-radius:3px;border:none;}}QProgressBar::chunk{{background:{C_ACCENT};border-radius:3px;}}")
        lay.addWidget(self._pr)
        self._ds=QLabel(""); self._ds.setStyleSheet(f"color:{C_TEXT3};font-size:12px;font-family:monospace;"); self._ds.setWordWrap(True)
        lay.addWidget(self._ds); lay.addStretch(); return w

    def _pg_done(self):
        w=QWidget(); w.setStyleSheet("background:transparent;")
        lay=QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        t=QLabel("\u2713  Setup Complete"); t.setStyleSheet(f"color:{C_GREEN};font-size:18px;font-weight:600;")
        d=QLabel("The dashboard is ready to use."); d.setStyleSheet(f"color:{C_TEXT2};font-size:12px;"); d.setWordWrap(True)
        lay.addWidget(t); lay.addWidget(d); lay.addSpacing(8)
        self._sl=QLabel(""); self._sl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-family:monospace;background:{C_CARD};border-radius:8px;padding:12px;")
        self._sl.setWordWrap(True); lay.addWidget(self._sl); lay.addStretch(); return w

    def _on_lang(self,item):
        save_language(item.data(Qt.ItemDataRole.UserRole))

    def _gn(self):
        cur=self._stack.currentIndex()
        if cur==0:
            item=self._ll.currentItem()
            if item: save_language(item.data(Qt.ItemDataRole.UserRole))
            self._stack.setCurrentIndex(1); self._back.setVisible(True)
            self._next.setEnabled(False); self._next.setText("Detecting\u2026")
            threading.Thread(target=self._run_detection,daemon=True).start()
        elif cur==1:
            self._stack.setCurrentIndex(2); self._next.setText("Finish")
        elif cur==2: self.accept()

    def _gb(self):
        cur=self._stack.currentIndex()
        if cur>0:
            self._stack.setCurrentIndex(cur-1)
            if cur-1==0: self._back.setVisible(False)
            self._next.setText("Next \u2192"); self._next.setEnabled(True)

    def _run_detection(self):
        def upd(msg):
            QMetaObject.invokeMethod(self._ds,"setText",Qt.ConnectionType.QueuedConnection,Q_ARG(str,msg))
        QMetaObject.invokeMethod(self._pr,"show",Qt.ConnectionType.QueuedConnection)
        steps = [
            ("Reading DMI info\u2026",lambda: _dmi("product_name")),
            ("Checking LLL module\u2026",lambda: Path("/sys/module/legion_laptop").exists()),
            ("Building capability map\u2026",lambda: detect_hardware()),
        ]
        cap={}
        for msg,fn in steps:
            upd(msg); time.sleep(0.15)
            try:
                r=fn()
                if isinstance(r,dict): cap=r
            except: pass
        if not cap: cap=detect_hardware()
        save_hardware(cap); FIRST_RUN_FLAG.parent.mkdir(parents=True,exist_ok=True); FIRST_RUN_FLAG.touch()
        global HW
        HW=cap
        def fin():
            self._pr.hide(); self._next.setEnabled(True); self._next.setText("Finish")
            self._stack.setCurrentIndex(2)
            brand=cap.get("brand","unknown").upper(); model=cap.get("model","Unknown")
            self._sl.setText(f"Brand: {brand}\nModel: {model}")
        QMetaObject.invokeMethod(self,"_finish_detection",Qt.ConnectionType.QueuedConnection)

    @pyqtSlot()
    def _finish_detection(self):
        global HW; cap=HW
        self._pr.hide(); self._next.setEnabled(True); self._next.setText("Finish")
        self._stack.setCurrentIndex(2)
        brand=cap.get("brand","unknown").upper() if cap else "UNKNOWN"
        model=cap.get("model","Unknown") if cap else "Unknown"
        self._sl.setText(f"Brand:  {brand}\nModel:  {model}")

# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._last_profile=None; self._page_request_cb=None; self._sync_battery_cb=None
        self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # Hardware Monitor Card
        hw=QWidget(); hw.setStyleSheet(f"background:{C_CARD};border-radius:12px;")
        hw.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum)
        hw_outer=QHBoxLayout(hw); hw_outer.setContentsMargins(0,0,0,0); hw_outer.setSpacing(0)

        def hw_col(stretch=1):
            w=QWidget(); w.setStyleSheet("background:transparent;")
            w.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Maximum)
            l=QVBoxLayout(w); l.setContentsMargins(16,14,16,14); l.setSpacing(2); l.setAlignment(Qt.AlignmentFlag.AlignTop)
            return w,l

        def col_hdr(text,badge=None):
            row=QHBoxLayout(); row.setSpacing(8); row.setContentsMargins(0,0,0,8)
            lbl=QLabel(text); lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
            row.addWidget(lbl)
            if badge: row.addWidget(badge)
            row.addStretch()
            hw=QWidget(); hw.setStyleSheet("background:transparent;")
            hl=QVBoxLayout(hw); hl.setContentsMargins(0,0,0,4); hl.setSpacing(3); hl.addLayout(row)
            return hw

        def vdiv():
            f=QWidget(); f.setFixedWidth(12); f.setStyleSheet("background:transparent;")
            f.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Expanding); return f

        cpu_w,cpu_l=hw_col(3)
        cpu_l.addWidget(col_hdr("CPU"))
        self.r_util=StatRow("Utilization","0%",0)
        self.r_freq=StatRow("Core Clock","0.0 GHz",0,val_w=80)
        self.r_temp=StatRow("Temperature","0 \u00b0C",0,val_w=80)
        self.r_fan1=StatRow("Fan 1","0 RPM",0,val_w=80)
        self.r_fan2=StatRow("Fan 2","0 RPM",0,val_w=80)
        for r in [self.r_util,self.r_freq,self.r_temp,self.r_fan1,self.r_fan2]:
            cpu_l.addWidget(r)

        gpu_w,gpu_l=hw_col(3)
        self.gpu_pstate=QLabel("P-State: \u2014")
        self.gpu_pstate.setStyleSheet(f"color:{C_BLUE};font-size:12px;background:transparent;border:none;border-radius:4px;padding:2px 6px;")
        gpu_l.addWidget(col_hdr("GPU",self.gpu_pstate))
        self.r_g_util=StatRow("Utilization","\u2014",0,val_w=90,color=C_BLUE)
        self.r_g_freq=StatRow("Core Clock","\u2014",0,val_w=90,color=C_BLUE)
        self.r_g_temp=StatRow("Temperature","\u2014",0,val_w=90)
        self.r_g_mem=StatRow("VRAM Used","\u2014",0,val_w=90,color=C_BLUE)
        self.r_g_pow=StatRow("Power Draw","\u2014",0,val_w=90,color=C_ORANGE)
        for r in [self.r_g_util,self.r_g_freq,self.r_g_temp,self.r_g_mem,self.r_g_pow]:
            gpu_l.addWidget(r)
        self.gpu_na=QLabel("nvidia-smi not found"); self.gpu_na.setStyleSheet(f"color:{C_TEXT3};font-size:10px;background:transparent;")
        self.gpu_na.hide(); gpu_l.addWidget(self.gpu_na)

        mem_w,mem_l=hw_col(2)
        mem_l.addWidget(col_hdr("Memory & Battery"))
        self.r_ram=StatRow("RAM Used","0 MB",0,val_w=120)
        self.r_bat=StatRow("Battery","0%",0,val_w=120,color=C_GREEN)
        self.r_bstat=StatRow("Status","\u2014",0,val_w=120)
        self.r_bpow=StatRow("Draw","\u2014 W",0,val_w=120)
        for r in [self.r_ram,self.r_bat,self.r_bstat,self.r_bpow]:
            mem_l.addWidget(r)

        hw_outer.addWidget(cpu_w,3); hw_outer.addWidget(vdiv())
        hw_outer.addWidget(gpu_w,3); hw_outer.addWidget(vdiv())
        hw_outer.addWidget(mem_w,2)
        root.addWidget(hw)

        # Power + Graphics 2-column
        two_col=QHBoxLayout(); two_col.setSpacing(10)

        pw,pl=make_card("Power")
        def _srow(icon,title,desc,ctrl):
            rw=QWidget(); rw.setStyleSheet("background:transparent;"); rw.setMinimumHeight(60)
            rl=QHBoxLayout(rw); rl.setContentsMargins(0,6,0,6); rl.setSpacing(14)
            ic=QLabel(icon); ic.setFixedWidth(32); ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic.setStyleSheet("font-size:18px;background:transparent;")
            tx=QVBoxLayout(); tx.setSpacing(3)
            t=QLabel(title); t.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
            d=QLabel(desc); d.setWordWrap(True); d.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
            tx.addWidget(t); tx.addWidget(d)
            rl.addWidget(ic); rl.addLayout(tx,1); rl.addWidget(ctrl,0,Qt.AlignmentFlag.AlignVCenter)
            return rw

        def _combo(opts,cur_idx=0):
            c=QComboBox(); c.setStyleSheet(combo_style()); c.setFixedWidth(170); c.setFixedHeight(34)
            for o in opts:
                if isinstance(o,tuple): c.addItem(o[0]); c.setItemData(c.count()-1,o[1])
                else: c.addItem(o)
            c.setCurrentIndex(cur_idx); return c

        cur_p=read_powermode()
        profile_opts=[(PROFILE_LABELS.get(p,p),p) for p in PROFILES]
        cur_idx=next((i for i,(_,p) in enumerate(profile_opts) if p==cur_p),0)
        self.power_combo=_combo(profile_opts,cur_idx)
        self.power_combo.currentIndexChanged.connect(self._on_power)
        pl.addWidget(_srow("\u26a1","Power Mode","Change performance profile. Also: Fn+Q",self.power_combo))
        pl.addWidget(make_div())

        cons=rdsys(str(_find_ideapad("conservation_mode") or ""),"0")
        rapid=rdsys(str(_find_feature("rapidcharge") or ""),"0")
        bat_mode=1 if cons=="1" else 2 if rapid=="1" else 0
        self.bat_combo=_combo(["Normal","Conservation (~60%)","Rapid Charge"],bat_mode)
        self.bat_combo.currentIndexChanged.connect(self._on_bat)
        pl.addWidget(_srow("\U0001f50b","Battery Mode","Choose how the battery is charged.",self.bat_combo))
        pl.addWidget(make_div())

        usb_tog=ToggleSwitch(path=_find_ideapad("usb_charging"))
        pl.addWidget(_srow("\U0001f50c","Always on USB","Charge USB devices when laptop is off.",usb_tog))
        pl.addWidget(make_div())

        fn_tog=ToggleSwitch(path=_find_ideapad("fn_lock"))
        pl.addWidget(_srow("\u2328","Fn Lock","Swap Fn and media keys.",fn_tog))
        two_col.addWidget(pw,1)

        gw,gl=make_card("Graphics")
        gpu_opts=[("Hybrid (iGPU+dGPU)","hybrid"),("NVIDIA (Discrete)","nvidia"),("Integrated (iGPU)","integrated")]
        self.gpu_mode=QComboBox(); self.gpu_mode.setStyleSheet(combo_style()); self.gpu_mode.setFixedHeight(34)
        for l,_ in gpu_opts: self.gpu_mode.addItem(l)
        self.gpu_mode.currentIndexChanged.connect(self._on_gpu)
        gl.addWidget(_srow("\U0001f3ae","GPU Working Mode","Switches GPU mode via envycontrol.",self.gpu_mode))
        gl.addWidget(make_div())

        gs_tog=ToggleSwitch(path=_find_feature("gsync"))
        gl.addWidget(_srow("\U0001f504","G-Sync","NVIDIA G-Sync variable refresh rate.",gs_tog))
        gl.addWidget(make_div())

        od_tog=ToggleSwitch(path=_find_feature("overdrive"))
        gl.addWidget(_srow("\U0001f5a5","Display Overdrive","Reduce display response time.",od_tog))
        two_col.addWidget(gw,1)
        root.addLayout(two_col)

        # System Status badges
        ss=QWidget(); ss.setStyleSheet(f"background:{C_CARD};border-radius:8px;")
        ss.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum)
        ssl=QVBoxLayout(ss); ssl.setContentsMargins(16,12,16,12); ssl.setSpacing(8)
        sst=QLabel("System Status"); sst.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
        ssl.addWidget(sst)
        badge_row=QHBoxLayout(); badge_row.setSpacing(6)
        self.b_boost=StatusBadge("CPU Boost","\u2014",C_TEXT3)
        self.b_gov=StatusBadge("Governor","\u2014",C_BLUE)
        self.b_epp=StatusBadge("EPP","\u2014",C_ORANGE)
        self.b_ac=StatusBadge("Power","\u2014",C_GREEN)
        for b in [self.b_boost,self.b_gov,self.b_epp,self.b_ac]:
            badge_row.addWidget(b)
        ssl.addLayout(badge_row)
        root.addWidget(ss)
        root.addStretch()

    def _on_power(self,idx):
        p=self.power_combo.currentData()
        if not p: p=PROFILES[idx] if idx<len(PROFILES) else PROFILES[0]
        ok,msg=apply_profile(p)
        send_notif(f"Power Mode: {PROFILE_LABELS.get(p,p)}",msg if not ok else PROFILE_DESCS.get(p,""),"battery" if ok else "dialog-error")

    def _on_bat(self,idx):
        if idx==0:
            wrsys(str(_find_ideapad("conservation_mode")),"0"); wrsys(str(_find_feature("rapidcharge")),"0")
            send_notif("Battery Mode","Normal charging","battery")
        elif idx==1:
            wrsys(str(_find_ideapad("conservation_mode")),"1"); wrsys(str(_find_feature("rapidcharge")),"0")
            send_notif("Battery Mode","Conservation ~60%","battery")
        elif idx==2:
            wrsys(str(_find_feature("rapidcharge")),"1"); wrsys(str(_find_ideapad("conservation_mode")),"0")
            send_notif("Battery Mode","Rapid Charge ON","battery")

    def _on_gpu(self,idx):
        modes=["hybrid","nvidia","integrated"]; labels=["Hybrid","NVIDIA","Integrated"]
        mode=modes[idx]
        def _do():
            try:
                import socket as _sk
                c=_sk.socket(_sk.AF_UNIX,_sk.SOCK_STREAM); c.settimeout(35)
                c.connect("/run/legion-toolkit.sock")
                c.send(f"envycontrol:{mode}\n".encode())
                resp=c.recv(256).decode().strip(); c.close()
                if resp=="ok": send_notif(f"GPU Mode \u2192 {labels[idx]}","\u26a0  Reboot to apply.","display")
                elif "not found" in resp: send_notif("envycontrol not found","Install: yay -S envycontrol","dialog-error")
                else: send_notif("GPU Mode Error",resp.replace("err:","").strip() or "failed","dialog-error")
            except ConnectionRefusedError:
                import shutil
                env=shutil.which("envycontrol")
                if env:
                    r=subprocess.run(["pkexec",env,"--switch",mode],capture_output=True,text=True,timeout=30)
                    if r.returncode==0: send_notif(f"GPU Mode \u2192 {labels[idx]}","\u26a0  Reboot to apply.","display")
                    else: send_notif("GPU Mode Error",(r.stderr or "failed").strip()[:120],"dialog-error")
                else: send_notif("Daemon not running","Start: sudo systemctl start legion-toolkit","dialog-error")
            except Exception as e: send_notif("GPU Mode Error",str(e)[:100],"dialog-error")
        threading.Thread(target=_do,daemon=True).start()

    def refresh(self,d=None):
        if d is None: return
        self.r_util.update_value(f"{d['cpu_util']}%",d["cpu_util"])
        self.r_freq.update_value(f"{d['cpu_freq']} GHz",int(d["cpu_freq"]/4.4*100))
        self.r_temp.update_value(f"{d['cpu_temp']} \u00b0C",d["cpu_temp"])
        self.r_fan1.update_value(f"{d['fan1']} RPM",int(d["fan1"]/5000*100))
        self.r_fan2.update_value(f"{d['fan2']} RPM",int(d["fan2"]/5000*100))
        gpu=d["gpu"]
        if gpu.get("available"):
            self.gpu_na.hide()
            gmem_pct=int(gpu["mem_used"]*100/max(gpu["mem_total"],1))
            self.r_g_util.update_value(f"{gpu['util']}%",gpu["util"],C_BLUE)
            self.r_g_freq.update_value(f"{gpu['freq']} MHz",int(gpu["freq"]/2000*100),C_BLUE)
            self.r_g_temp.update_value(f"{gpu['temp']} \u00b0C",gpu["temp"])
            self.r_g_mem.update_value(f"{gpu['mem_used']}/{gpu['mem_total']} MB",gmem_pct,C_BLUE)
            self.r_g_pow.update_value(f"{gpu['power']:.0f} W",int(gpu["power"]/150*100),C_ORANGE)
            pst=gpu.get("pstate","\u2014")
            col=C_GREEN if pst=="P0" else C_BLUE if pst in ["P1","P2"] else C_TEXT3
            self.gpu_pstate.setText(f"P-State: {pst}")
            self.gpu_pstate.setStyleSheet(f"color:{col};font-size:12px;background:transparent;border:1px solid {col};border-radius:4px;padding:2px 8px;")
        else:
            self.gpu_na.show()
            for r in [self.r_g_util,self.r_g_freq,self.r_g_temp,self.r_g_mem,self.r_g_pow]:
                r.update_value("\u2014",0)
            self.gpu_pstate.setText("P-State: N/A")
        ru=d["ram_used"]; rt=d["ram_total"]; rpct=d["ram_pct"]
        pct=d["bat_pct"]; status=d["bat_status"]
        self.r_ram.update_value(f"{ru} MB / {rt} MB",rpct)
        bc=C_GREEN if pct>50 else C_ORANGE if pct>20 else C_RED
        self.r_bat.update_value(f"{pct}%",pct,bc)
        self.r_bstat.update_value(status,0)
        self.r_bpow.update_value(d["bat_power"],0)
        cur=d["profile"]
        self.power_combo.blockSignals(True)
        for i in range(self.power_combo.count()):
            if self.power_combo.itemData(i,Qt.ItemDataRole.UserRole)==cur:
                self.power_combo.setCurrentIndex(i); break
        self.power_combo.blockSignals(False)
        boost=d["boost"]
        self.b_boost.set_value("ON" if boost=="1" else "OFF",C_GREEN if boost=="1" else C_TEXT3)
        self.b_gov.set_value(d["gov"].capitalize(),C_BLUE)
        epp_raw=d["epp"]; EPP_SHORT={"default":"Default","performance":"Perf","balance_performance":"Bal.Perf","balance_power":"Bal.Power","power":"PowerSave"}
        self.b_epp.set_value(EPP_SHORT.get(epp_raw,epp_raw[:10]),C_ORANGE)
        self.b_ac.set_value("AC" if d["ac"] else "Battery",C_GREEN if d["ac"] else C_ORANGE)

# ══════════════════════════════════════════════════════════════════════════════
# BATTERY PAGE
# ══════════════════════════════════════════════════════════════════════════════
class BatteryPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._sync_home_cb=None; self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        sc,sl=make_card()
        top=QHBoxLayout(); top.setSpacing(24)
        left=QVBoxLayout(); left.setSpacing(4)
        self.pct=QLabel("\u2014%"); self.pct.setStyleSheet(f"color:{C_TEXT};font-size:42px;font-weight:700;background:transparent;")
        self.stat=QLabel("Status: \u2014"); self.stat.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;")
        self.health_lbl=QLabel("Health: \u2014"); self.health_lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;")
        left.addWidget(self.pct); left.addWidget(self.stat); left.addWidget(self.health_lbl); left.addStretch()
        top.addLayout(left); top.addWidget(QWidget()); top.addWidget(QWidget()) # spacers
        right=QVBoxLayout(); right.setSpacing(4)
        self.b_charge=StatRow("Charge","\u2014",0,130,110,C_GREEN)
        self.b_health=StatRow("Health","\u2014",0,130)
        self.b_temp=StatRow("Temp","\u2014",0,130)
        self.b_power=StatRow("Draw","\u2014",0,130)
        for b in [self.b_charge,self.b_health,self.b_temp,self.b_power]: right.addWidget(b)
        right.addStretch(); top.addLayout(right)
        sl.addLayout(top); root.addWidget(sc)

        ds,dl=make_card("Battery Details")
        self.info_rows={}
        for key,label in [("capacity","Capacity"),("voltage","Voltage"),("cycles","Charge Cycles"),
                          ("power","Power Draw"),("temp","Temperature"),("manufacturer","Manufacturer"),
                          ("model_name","Model"),("technology","Technology")]:
            r=InfoRow(label,"\u2014"); self.info_rows[key]=r; dl.addWidget(r)
        root.addWidget(ds)
        root.addStretch()

    def refresh(self,d=None):
        s=get_battery_stats()
        pct=s["percent"]; health=s["health"]
        bc=C_GREEN if pct>50 else C_ORANGE if pct>20 else C_RED
        hc=C_GREEN if health>80 else C_ORANGE if health>60 else C_RED
        self.pct.setText(f"{pct}%"); self.pct.setStyleSheet(f"color:{bc};font-size:40px;font-weight:600;background:transparent;")
        self.stat.setText(f"Status: {s['status']}"); self.health_lbl.setText(f"Health: {health}%")
        self.b_charge.update_value(f"{pct}%",pct,bc); self.b_health.update_value(f"{health}%",health,hc)
        self.b_temp.update_value(s["temp"],0); self.b_power.update_value(s["power"],0)
        for k in self.info_rows: self.info_rows[k].set_value(str(s.get(k,"\u2014")))

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE PAGE
# ══════════════════════════════════════════════════════════════════════════════
class PerformancePage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};"); self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        bc,bl=make_card("CPU Boost")
        boost_path="/sys/devices/system/cpu/cpufreq/boost"
        bl.addWidget(_mk_lbl("Allows CPU to exceed base clock for short bursts.","",size=12))
        br=QHBoxLayout()
        bt=QLabel("AMD CPU Boost"); bt.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
        br.addWidget(bt); br.addStretch()
        self.boost_tog=ToggleSwitch(path=boost_path)
        br.addWidget(self.boost_tog,alignment=Qt.AlignmentFlag.AlignVCenter)
        bl.addLayout(br); root.addWidget(bc)

        ec,el=make_card("Energy Performance Preference")
        ed=QLabel("Controls CPU energy/performance tradeoff."); ed.setWordWrap(True)
        ed.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        el.addWidget(ed)
        er=QHBoxLayout(); er.setSpacing(12)
        lbl=QLabel("EPP Level"); lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
        er.addWidget(lbl)
        self.epp=QComboBox(); self.epp.setStyleSheet(combo_style()); self.epp.setFixedHeight(36)
        cur_epp=get_epp()
        for v in EPP_VALUES: self.epp.addItem(EPP_LABELS[v],v)
        if cur_epp in EPP_VALUES: self.epp.setCurrentIndex(EPP_VALUES.index(cur_epp))
        self.epp.currentIndexChanged.connect(self._on_epp)
        er.addWidget(self.epp); er.addStretch(); el.addLayout(er)
        root.addWidget(ec)

        fc,fl=make_card("Fan & Thermal")
        fl.addWidget(NotifyToggle("Fan Full Speed","Lock both fans to maximum speed.",str(_find_feature("fan_fullspeed") or "")))
        fl.addWidget(make_div())
        fl.addWidget(NotifyToggle("Thermal Mode","Enhanced thermal performance.",str(_find_feature("thermalmode") or "")))
        root.addWidget(fc)

        li,ll=make_card("Live CPU Info")
        self.gov=InfoRow("Governor","\u2014"); ll.addWidget(self.gov)
        self.freq=InfoRow("Frequency","\u2014"); ll.addWidget(self.freq)
        self.temp=InfoRow("Temperature","\u2014"); ll.addWidget(self.temp)
        root.addWidget(li); root.addStretch()

    def _on_epp(self,idx):
        val=EPP_VALUES[idx]; set_epp(val); send_notif("EPP Changed",EPP_LABELS[val])

    def refresh(self,d=None):
        if d:
            self.gov.set_value(d.get("gov","\u2014"))
            self.freq.set_value(f"{d.get('cpu_freq',0)} GHz")
            self.temp.set_value(f"{d.get('cpu_temp',0)} \u00b0C")
        else:
            self.gov.set_value(get_governor())
            self.freq.set_value(f"{get_cpu_freq_ghz()} GHz")
            self.temp.set_value(f"{get_cpu_temp()} \u00b0C")

# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY PAGE
# ══════════════════════════════════════════════════════════════════════════════
class DisplayPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._outputs=[]; self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        bc,bl=make_card("Screen Brightness")
        _bl_paths=[Path("/sys/class/backlight/nvidia_wmi_ec_backlight"),Path("/sys/class/backlight/amdgpu_bl0")]
        self._bl_path=next((p for p in _bl_paths if (p/"brightness").exists()),None)
        if self._bl_path:
            try: _mb=int((self._bl_path/"max_brightness").read_text().strip()); _cb=int((self._bl_path/"brightness").read_text().strip())
            except: _mb=255; _cb=128
            bri_row=QHBoxLayout(); bri_row.setSpacing(12)
            dim=QLabel("0%"); dim.setFixedWidth(32); dim.setStyleSheet(f"color:{C_TEXT3};font-size:12px;background:transparent;")
            bri_row.addWidget(dim)
            self._sl=QSlider(Qt.Orientation.Horizontal); self._sl.setRange(0,_mb); self._sl.setValue(_cb)
            self._sl.setStyleSheet(f"QSlider::groove:horizontal{{background:{C_BORDER};height:8px;border-radius:4px;}}"
                f"QSlider::handle:horizontal{{background:{C_BLUE};width:20px;height:20px;border-radius:10px;margin:-6px 0;}}"
                f"QSlider::sub-page:horizontal{{background:{C_BLUE};border-radius:4px;}}")
            bri_row.addWidget(self._sl)
            mx=QLabel("100%"); mx.setFixedWidth(36); mx.setStyleSheet(f"color:{C_TEXT3};font-size:12px;background:transparent;")
            bri_row.addWidget(mx)
            self._bp=QLabel(f"{int(_cb/_mb*100)}%"); self._bp.setFixedWidth(42)
            self._bp.setStyleSheet(f"color:{C_BLUE};font-size:13px;font-weight:600;background:transparent;")
            bri_row.addWidget(self._bp); bl.addLayout(bri_row)
            self._bl_max=_mb
            self._sl.valueChanged.connect(lambda v: self._bp.setText(f"{int(v/self._bl_max*100)}%"))
            self._sl.sliderReleased.connect(self._write_brightness)
        else:
            bl.addWidget(_mk_lbl("\u26a0  No backlight device found.",C_ORANGE,size=11))
        root.addWidget(bc)

        dc,dl=make_card("Display Settings")
        dl.addWidget(NotifyToggle("Display Overdrive","Reduce display response time.",str(_find_feature("overdrive") or "")))
        dl.addWidget(make_div())
        dl.addWidget(NotifyToggle("G-Sync","NVIDIA G-Sync variable refresh rate.",str(_find_feature("gsync") or "")))
        root.addWidget(dc)
        root.addStretch()

    def _write_brightness(self):
        if not self._bl_path: return
        val=self._sl.value()
        try: (self._bl_path/"brightness").write_text(str(val)+"\n")
        except:
            subprocess.Popen(["pkexec","sh","-c",f"echo {val} > {self._bl_path/'brightness'}"],
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PAGE
# ══════════════════════════════════════════════════════════════════════════════
class SystemPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};"); self._app_cfg=json.loads(APP_CFG.read_text()) if APP_CFG.exists() else {}
        self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        ic,il=make_card("Input Devices")
        for i,(t,d,p) in enumerate([("Fn Lock","Swap Fn and media keys.",_find_ideapad("fn_lock")),
                                     ("Super Key","Enable/disable Windows key.",_find_feature("winkey")),
                                     ("Touchpad","Enable/disable touchpad.",_find_feature("touchpad")),
                                     ("Camera","Hardware kill switch for webcam.",_find_ideapad("camera_power"))]):
            il.addWidget(NotifyToggle(t,d,str(p) if p else ""))
            if i<3: il.addWidget(make_div())
        root.addWidget(ic)

        ac,al=make_card("Appearance")
        th_row=QHBoxLayout(); th_row.setSpacing(12)
        th_lbl=QLabel("Theme"); th_lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
        th_row.addWidget(th_lbl)
        self.theme=QComboBox(); self.theme.setStyleSheet(combo_style()); self.theme.setFixedHeight(36)
        self.theme.addItems(["Dark","Dark Dimmed","OLED Black","Light"])
        saved_theme=self._app_cfg.get("theme","dark")
        theme_idx={"dark":0,"dark_dimmed":1,"oled_black":2,"light":3}.get(saved_theme,0)
        self.theme.setCurrentIndex(theme_idx); self.theme.currentIndexChanged.connect(self._on_theme)
        th_row.addWidget(self.theme); th_row.addStretch(); al.addLayout(th_row)
        root.addWidget(ac); root.addStretch()

    def _on_theme(self,idx):
        names=["dark","dark_dimmed","oled_black","light"]; name=names[idx] if idx<len(names) else "dark"
        self._app_cfg["theme"]=name
        try:
            APP_CFG.parent.mkdir(parents=True,exist_ok=True); APP_CFG.write_text(json.dumps(self._app_cfg))
        except: pass
        _load_theme_colours()
        win=self.window()
        if win: win.close()
        os.execv(sys.executable,[sys.executable]+sys.argv)

# ══════════════════════════════════════════════════════════════════════════════
# POWER OPTIONS PAGE (redesigned LLL-style)
# ══════════════════════════════════════════════════════════════════════════════
class PowerOptionsPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};"); self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        note=QLabel("Power options. Unsupported options silently fail with legion_cli.")
        note.setWordWrap(True); note.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        root.addWidget(note)

        # CPU Power Limits
        cc,cl=make_card("CPU Power Limits")
        cl.addWidget(_mk_lbl("Set PL1 (sustained) and PL2 (boost peak) via RAPL.",C_TEXT2,size=12))
        cl.addWidget(make_div())
        cur_pl1,cur_pl2=get_cpu_tdp()
        def _spin(lo,hi,val,suffix):
            sp=QSpinBox(); sp.setRange(lo,hi); sp.setSuffix(suffix); sp.setValue(val); sp.setSingleStep(1)
            sp.setStyleSheet(f"QSpinBox{{background:{C_CARD2};color:{C_ORANGE};border:1px solid {C_BORDER};border-radius:6px;padding:6px;font-size:13px;min-width:100px;}}"
                f"QSpinBox::up-button,QSpinBox::down-button{{width:22px;background:{C_CARD2};}}")
            return sp
        self.pl1=_spin(5,150,cur_pl1 or 35," W")
        self.pl2=_spin(5,150,cur_pl2 or 54," W")
        def _row(lbl,sp):
            r=QHBoxLayout(); r.setSpacing(12); lb=QLabel(lbl); lb.setFixedWidth(160)
            lb.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
            r.addWidget(lb); r.addWidget(sp); r.addStretch(); return r
        cl.addLayout(_row("PL1 (sustained W):",self.pl1))
        cl.addLayout(_row("PL2 (boost peak W):",self.pl2))
        ap=QPushButton("Apply Power Limits"); ap.setFixedHeight(32)
        ap.setStyleSheet(f"background:{C_ACCENT};color:#fff;border:none;border-radius:6px;font-size:12px;padding:0 16px;")
        ap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pl_stat=QLabel(""); self.pl_stat.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        pr=QHBoxLayout(); pr.addWidget(ap); pr.addWidget(self.pl_stat); pr.addStretch()
        cl.addLayout(pr); ap.clicked.connect(self._apply_pl)
        root.addWidget(cc)

        # GPU OC
        gc,gl=make_card("GPU Overclocking")
        gl.addWidget(_mk_lbl("Apply core/memory offsets and power limit via nvidia-settings.",C_TEXT2,size=12))
        gl.addWidget(make_div())
        self.gc_off=_spin(-500,500,0," MHz"); self.gm_off=_spin(-500,500,0," MHz")
        self.gp_lim=_spin(15,200,0," W")
        gl.addLayout(_row("Core Offset:",self.gc_off))
        gl.addLayout(_row("Memory Offset:",self.gm_off))
        gl.addLayout(_row("Power Limit:",self.gp_lim))
        agr=QHBoxLayout()
        ag=QPushButton("Apply GPU OC"); ag.setFixedHeight(32)
        ag.setStyleSheet(f"background:{C_ACCENT};color:#fff;border:none;border-radius:6px;font-size:12px;padding:0 16px;")
        ag.setCursor(Qt.CursorShape.PointingHandCursor); ag.clicked.connect(self._apply_gpu)
        rg=QPushButton("Reset GPU OC"); rg.setFixedHeight(32)
        rg.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;font-size:12px;padding:0 16px;")
        rg.setCursor(Qt.CursorShape.PointingHandCursor); rg.clicked.connect(self._reset_gpu)
        agr.addWidget(ag); agr.addWidget(rg); agr.addStretch()
        gl.addLayout(agr)
        self.gpu_stat=QLabel(""); self.gpu_stat.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        gl.addWidget(self.gpu_stat)
        root.addWidget(gc)
        root.addStretch()

    def _apply_pl(self):
        set_cpu_tdp(self.pl1.value(),self.pl2.value())
        self.pl_stat.setText(f"OK  PL1={self.pl1.value()}W  PL2={self.pl2.value()}W")
        self.pl_stat.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")

    def _apply_gpu(self):
        apply_gpu_oc(self.gc_off.value(),self.gm_off.value(),self.gp_lim.value())
        self.gpu_stat.setText(f"Core {self.gc_off.value()} Mem {self.gm_off.value()} PL {self.gp_lim.value()}W")
        self.gpu_stat.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")

    def _reset_gpu(self):
        reset_gpu_oc(); self.gpu_stat.setText("GPU OC reset to defaults")
        self.gpu_stat.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")

# ══════════════════════════════════════════════════════════════════════════════
# FAN PAGE
# ══════════════════════════════════════════════════════════════════════════════
class FanPage(QWidget):
    _fan_result=pyqtSignal(bool,str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._fan_result.connect(self._on_fan_result)
        self._mode="auto"; self._build()
        self._ft=QTimer(self); self._ft.timeout.connect(self._refresh_rpm); self._ft.start(1500)

    def _on_fan_result(self,ok,msg):
        col=C_GREEN if ok else C_ORANGE
        self._status.setStyleSheet(f"color:{col};font-size:12px;font-weight:600;background:transparent;")
        self._status.setText(msg)

    def _emit(self,ok,msg): self._fan_result.emit(ok,msg)

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        hw=_fan_hwmon_info()
        lll_avail=is_lll_available()
        has_curve=bool(lll_avail and read_fancurve_from_hw())

        # Live RPM
        rc,rl=make_card("Live Fan Speed")
        rpm_row=QHBoxLayout(); rpm_row.setSpacing(48); rpm_row.addStretch()
        for attr,fattr,label,color in [("cpu_rpm","cpu_fan","CPU Fan",C_BLUE),("gpu_rpm","gpu_fan","GPU Fan",C_RED)]:
            col=QVBoxLayout(); col.setSpacing(6); col.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            fw=FanWidget(color,size=64); setattr(self,fattr,fw)
            fww=QHBoxLayout(); fww.addStretch(); fww.addWidget(fw); fww.addStretch()
            lbl=QLabel("\u2014 RPM"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{color};font-size:22px;font-weight:600;background:transparent;")
            nm=QLabel(label); nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
            setattr(self,attr,lbl)
            col.addLayout(fww); col.addWidget(lbl); col.addWidget(nm); rpm_row.addLayout(col)
        rpm_row.addStretch(); rl.addLayout(rpm_row)
        self.fan_badge=QLabel("Mode: Auto"); self.fan_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fan_badge.setStyleSheet(f"color:{C_TEXT3};font-size:12px;background:transparent;")
        rl.addWidget(self.fan_badge); root.addWidget(rc)

        # Fan Control card
        cc,cl=make_card("Fan Control")
        note="Full speed only available in Custom power mode.\nUse Auto/Dynamic for daily use."
        cl.addWidget(_mk_lbl(note,C_TEXT2,size=12)); cl.addWidget(make_div())

        # Mode buttons
        btn_row=QHBoxLayout(); btn_row.setSpacing(12)
        self._auto_btn=QPushButton("\U0001f5a5  Auto / Dynamic"); self._auto_btn.setCheckable(True); self._auto_btn.setChecked(True)
        self._auto_btn.setFixedHeight(48)
        self._auto_btn.setStyleSheet(f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};border:1px solid {C_BORDER};border-radius:8px;font-size:13px;font-weight:600;}}"
            f"QPushButton:checked{{background:transparent;color:{C_GREEN};border:2px solid {C_GREEN};}}"
            f"QPushButton:hover:!checked{{border:1px solid #555;color:{C_TEXT};}}")
        self._auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_btn.clicked.connect(lambda: self._set_mode("auto"))

        self._full_btn=QPushButton("\U0001f300  Full Speed"); self._full_btn.setCheckable(True)
        self._full_btn.setFixedHeight(48)
        self._full_btn.setStyleSheet(f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};border:1px solid {C_BORDER};border-radius:8px;font-size:13px;font-weight:600;}}"
            f"QPushButton:checked{{background:transparent;color:{C_RED};border:2px solid {C_RED};}}"
            f"QPushButton:hover:!checked{{border:1px solid #555;color:{C_TEXT};}}")
        self._full_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._full_btn.clicked.connect(lambda: self._set_mode("full"))

        # Hide fullspeed unless power mode is Custom
        self._full_btn.setVisible(False)

        btn_row.addWidget(self._auto_btn); btn_row.addWidget(self._full_btn)
        cl.addLayout(btn_row)

        self._mode_desc=QLabel("Firmware controls fans. Recommended.")
        self._mode_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;"); self._mode_desc.setWordWrap(True)
        cl.addWidget(self._mode_desc)
        self._status=QLabel(""); self._status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        cl.addWidget(self._status)
        root.addWidget(cc)

        # Fan Presets
        pc,pl=make_card("Fan Presets")
        presets=list(FAN_PRESETS.items())
        for row_i in range(0,len(presets),3):
            row=QHBoxLayout(); row.setSpacing(8)
            for ci in range(3):
                idx=row_i+ci
                if idx>=len(presets): row.addStretch(); continue
                pname,(cpu_pct,gpu_pct)=presets[idx]
                colors=[C_BLUE,C_GREEN,C_ORANGE,C_RED,"#ff0000"]
                btn=QPushButton(f"{pname}  \u2014  {cpu_pct}% / {gpu_pct}%")
                btn.setFixedHeight(42)
                btn.setStyleSheet(f"QPushButton{{background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
                    f"border-radius:8px;font-size:12px;font-weight:500;border-left:3px solid {colors[idx%5]};padding-left:12px;}}"
                    f"QPushButton:hover{{background:{colors[idx%5]}22;border-color:{colors[idx%5]};}}")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda chk,pn=pname,cp=cpu_pct,gp=gpu_pct: self._apply_preset(pn,cp,gp))
                row.addWidget(btn,1)
            pl.addLayout(row)
        root.addWidget(pc)

        # Custom Fan Curve Editor (LLL required)
        if has_curve:
            fce,fcel=make_card("\U0001f39b  Custom Fan Curve")
            fcel.addWidget(_mk_lbl("Edit 10-point fan curve. PWM=0-255, Temp thresholds in \u00b0C.",C_TEXT2,size=11))
            curve_text=read_fancurve_from_hw() or ""
            current=parse_fancurve(curve_text) if curve_text else []
            self._curve_pts=[]
            for i in range(10):
                row=QHBoxLayout()
                row.addWidget(QLabel(f"{i+1}"))
                ts=QSpinBox(); ts.setRange(30,95); ts.setValue(current[i].get("cpu_max",40+i*5) if i<len(current) else 40+i*5)
                ts.setFixedWidth(60); row.addWidget(QLabel("\u00b0C")); row.addWidget(ts)
                p1=QSpinBox(); p1.setRange(0,255); p1.setValue(current[i].get("fan1_pwm",50+i*20) if i<len(current) else min(255,50+i*20))
                p1.setFixedWidth(60); row.addWidget(QLabel("F1")); row.addWidget(p1)
                p2=QSpinBox(); p2.setRange(0,255); p2.setValue(current[i].get("fan2_pwm",50+i*20) if i<len(current) else min(255,50+i*20))
                p2.setFixedWidth(60); row.addWidget(QLabel("F2")); row.addWidget(p2)
                self._curve_pts.append({"temp":ts,"pwm1":p1,"pwm2":p2})
                fcel.addLayout(row)

            apply_btn=QPushButton("\u2728  Apply Curve")
            apply_btn.setStyleSheet(f"background:{C_ACCENT};color:{C_BG};border-radius:6px;padding:8px;")
            apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            apply_btn.clicked.connect(self._apply_curve)
            save_btn=QPushButton("\U0001f4be  Save Preset")
            save_btn.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;padding:8px;")
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(lambda: save_fancurve_to_file(
                [{"fan1_pwm":p["pwm1"].value(),"fan2_pwm":p["pwm2"].value(),"cpu_temp":p["temp"].value()} for p in self._curve_pts],"custom"))
            load_btn=QPushButton("\U0001f4c2  Load Preset")
            load_btn.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;padding:8px;")
            load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            load_btn.clicked.connect(self._load_preset)
            br=QHBoxLayout(); br.addWidget(apply_btn); br.addWidget(save_btn); br.addWidget(load_btn); fcel.addLayout(br)
            root.addWidget(fce)

        # Lock/Minifan buttons
        lc,ll=make_card("Advanced")
        lr=QHBoxLayout()
        lock_btn=QPushButton("\U0001f512  Lock Controller"); lock_btn.setCheckable(True); lock_btn.setChecked(get_fan_lock_status())
        lock_btn.setStyleSheet(f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};border:1px solid {C_BORDER};border-radius:6px;font-size:12px;}}"
            f"QPushButton:checked{{background:{C_RED};color:{C_BG};}}")
        lock_btn.clicked.connect(lambda: set_fan_lock(lock_btn.isChecked()))
        lr.addWidget(lock_btn)
        mini_btn=QPushButton("\U0001f327  Mini Curve"); mini_btn.setCheckable(True); mini_btn.setChecked(get_minifancurve_status())
        mini_btn.setStyleSheet(f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};border:1px solid {C_BORDER};border-radius:6px;font-size:12px;}}"
            f"QPushButton:checked{{background:{C_GREEN};color:{C_BG};}}")
        mini_btn.clicked.connect(lambda: set_minifancurve(mini_btn.isChecked()))
        lr.addWidget(mini_btn); lr.addStretch(); ll.addLayout(lr)
        root.addWidget(lc)

        root.addStretch()
        self._refresh_rpm()

    def _set_mode(self,mode):
        self._mode=mode
        self._auto_btn.setChecked(mode=="auto"); self._full_btn.setChecked(mode=="full")
        self._mode_desc.setText("Firmware controls fans." if mode=="auto" else "Both fans locked to 100%.")
        self._emit(False,"\u23f3  Applying\u2026")
        def _do():
            if mode=="auto": ok,msg=_write_fan_auto(); self._emit(ok,"\u2713  Auto active" if ok else f"\u2717  {msg}")
            else: ok,msg=_write_fan_fullspeed(True); self._emit(ok,"\u2713  Full speed" if ok else f"\u2717  {msg}")
        threading.Thread(target=_do,daemon=True).start()

    def _apply_preset(self,name,cpu_pct,gpu_pct):
        self._emit(False,"\u23f3  Applying {name}\u2026")
        def _do():
            ok,msg=_write_fan_pwm(cpu_pct,gpu_pct)
            if ok: self._emit(True,f"\u2713  {name} \u2014 CPU {cpu_pct}%  GPU {gpu_pct}%")
            else:
                if cpu_pct>=90:
                    ok2,_=_write_fan_fullspeed(True)
                    self._emit(ok2,f"\u2713  {name} (full speed)")
                else:
                    ok2,_=_write_fan_auto()
                    self._emit(ok2,f"\u2713  {name} (auto)")
        threading.Thread(target=_do,daemon=True).start()

    def _apply_curve(self):
        pts=[]
        for p in self._curve_pts:
            pts.append({"fan1_pwm":p["pwm1"].value(),"fan2_pwm":p["pwm2"].value(),"cpu_temp":p["temp"].value(),"accel":5,"decel":5})
        ok,msg=write_fancurve_to_hw(pts)
        self._status.setText(f"\u2713  {msg}" if ok else f"\u2717  {msg}")
        send_notif("Fan Curve",msg,"computer")

    def _load_preset(self):
        pts=load_fancurve_from_file("custom")
        if not pts: send_notif("Load Error","No preset found: custom","dialog-error"); return
        for i,p in enumerate(pts[:10]):
            if i<len(self._curve_pts):
                self._curve_pts[i]["temp"].setValue(p.get("cpu_temp",50))
                self._curve_pts[i]["pwm1"].setValue(p.get("fan1_pwm",100))
                self._curve_pts[i]["pwm2"].setValue(p.get("fan2_pwm",100))
        send_notif("Fan Curve","Loaded preset: custom","computer")

    def _refresh_rpm(self):
        r1,r2=get_fan_rpm()
        self.cpu_fan.set_rpm(r1); self.gpu_fan.set_rpm(r2)
        self.cpu_rpm.setText(f"{r1:,}" if r1>0 else "\u2014")
        self.gpu_rpm.setText(f"{r2:,}" if r2>0 else "\u2014")
        mode_lbl="Full Speed" if self._mode=="full" else "Auto"
        self.fan_badge.setText(f"Mode: {mode_lbl}")
        for lbl,rpm,col in [(self.cpu_rpm,r1,C_BLUE),(self.gpu_rpm,r2,C_RED)]:
            c=C_RED if rpm>5000 else C_ORANGE if rpm>2500 else col
            lbl.setStyleSheet(f"color:{c};font-size:22px;font-weight:600;background:transparent;")

    def refresh(self,d=None):
        self._refresh_rpm()
        if d:
            profile=d.get("profile","")
            self._full_btn.setVisible(profile=="custom")

# ══════════════════════════════════════════════════════════════════════════════
# ACTIONS PAGE
# ══════════════════════════════════════════════════════════════════════════════
class ActionsPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._actions=load_actions(); self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        ac,al=make_card("Automatic Power Mode Switching")
        ad=QLabel("Automatically switch power profile when AC is plugged/unplugged.")
        ad.setWordWrap(True); ad.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        al.addWidget(ad); al.addWidget(make_div())

        sw=QHBoxLayout()
        swc=QVBoxLayout(); swc.setSpacing(2)
        st=QLabel("Enable Auto Switching"); st.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
        sd=QLabel("Change profile when charger is plugged/unplugged.")
        sd.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        swc.addWidget(st); swc.addWidget(sd)
        sw.addLayout(swc); sw.addStretch()
        self.auto_tog=ToggleSwitch(path=None,on_change=lambda v: (self._actions.update({"auto_switch":v}),save_actions(self._actions)),
                                    read_val="1" if self._actions.get("auto_switch") else "0")
        sw.addWidget(self.auto_tog,alignment=Qt.AlignmentFlag.AlignVCenter)
        al.addLayout(sw); al.addWidget(make_div())

        for attr,label,key in [("ac_combo","On AC Connect \u2192","on_ac"),("bat_combo","On Battery \u2192","on_battery")]:
            row=QHBoxLayout(); row.setSpacing(16)
            lbl=QLabel(label); lbl.setFixedWidth(180); lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;background:transparent;")
            row.addWidget(lbl)
            combo=QComboBox(); combo.setStyleSheet(combo_style())
            cur=self._actions.get(key,"balanced")
            for p in PROFILES: combo.addItem(PROFILE_LABELS[p],p)
            if cur in PROFILES: combo.setCurrentIndex(PROFILES.index(cur))
            combo.currentIndexChanged.connect(lambda _,a=attr,lk=key: self._save())
            setattr(self,attr,combo); row.addWidget(combo); row.addStretch()
            al.addLayout(row)

        test=QPushButton("Test Now")
        test.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;padding:8px 16px;font-size:12px;")
        test.setCursor(Qt.CursorShape.PointingHandCursor)
        test.clicked.connect(lambda: (apply_actions_now(),self._sl.setText("\u2713 Tested")))
        tr=QHBoxLayout(); tr.addWidget(test); tr.addStretch(); al.addLayout(tr)
        self._sl=QLabel(""); self._sl.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        al.addWidget(self._sl); root.addWidget(ac)

        cs,csl=make_card("Current Status")
        self.ac_stat=InfoRow("Power Source","\u2014"); csl.addWidget(self.ac_stat)
        self.pr_stat=InfoRow("Active Profile","\u2014"); csl.addWidget(self.pr_stat)
        root.addWidget(cs); root.addStretch()

    def _save(self):
        self._actions["on_ac"]=self.ac_combo.currentData()
        self._actions["on_battery"]=self.bat_combo.currentData()
        save_actions(self._actions)
        self._sl.setText("\u2713 Saved")

    def refresh(self,d=None):
        ac=get_ac_connected(); profile=read_powermode()
        self.ac_stat.set_value("AC Adapter" if ac else "Battery")
        self.pr_stat.set_value(PROFILE_LABELS.get(profile,"\u2014"))

# ══════════════════════════════════════════════════════════════════════════════
# ABOUT PAGE
# ══════════════════════════════════════════════════════════════════════════════
class AboutPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};"); self._build()

    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        card,lay=make_card()
        hw=QWidget(); hw.setStyleSheet("background:transparent;")
        hl=QVBoxLayout(hw); hl.setContentsMargins(0,0,0,8); hl.setSpacing(8); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm=QPixmap(str(_LEGION_ICON_PATH))
        logo=QLabel(); logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(pm.scaled(64,78,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        logo.setStyleSheet("background:transparent;")
        hl.addWidget(logo)
        title=QLabel("Legion Linux Toolkit"); title.setStyleSheet(f"color:{C_TEXT};font-size:22px;font-weight:700;background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter); hl.addWidget(title)
        ver=QLabel("v0.7.0"); ver.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter); hl.addWidget(ver)
        lay.addWidget(hw)

        brand=HW.get("brand","unknown").upper() if HW else "LENOVO"
        model=HW.get("model",_dmi("product_name")) if HW else _dmi("product_name") or "Unknown"
        cpu_name="Unknown"
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if "model name" in line.lower(): cpu_name=line.split(":")[1].strip(); break
        except: pass
        gpu_name="Unknown"
        try:
            r=subprocess.run(["lspci"],capture_output=True,text=True,timeout=3)
            gpus=[line.split(":",2)[-1].strip() for line in r.stdout.splitlines() if any(k in line for k in ["VGA","3D","Display"])]
            gpu_name=" + ".join(gpus) if gpus else "Unknown"
        except: pass
        os_name="Linux"
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="): os_name=line.split("=",1)[1].strip().strip('"'); break
        except: pass
        desktop=os.environ.get("XDG_CURRENT_DESKTOP","") or os.environ.get("DESKTOP_SESSION","Unknown")
        wayland="Wayland" if os.environ.get("WAYLAND_DISPLAY") else "X11"
        desktop_str=f"{desktop} ({wayland})" if desktop else wayland
        info=[("Brand",brand),("Model",model),("CPU",cpu_name),("GPU",gpu_name),
              ("OS",os_name),("Desktop",desktop_str),("Config","~/.config/legion-toolkit/")]
        for label,value in info:
            row=QWidget(); row.setStyleSheet("background:transparent;"); row.setFixedHeight(32)
            rl=QHBoxLayout(row); rl.setContentsMargins(0,2,0,2); rl.setSpacing(16)
            lbl=QLabel(label); lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;"); lbl.setFixedWidth(80)
            val=QLabel(value); val.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:500;background:transparent;"); val.setWordWrap(True)
            rl.addWidget(lbl); rl.addWidget(val,1); lay.addWidget(row)
        root.addWidget(card); root.addStretch()

# ══════════════════════════════════════════════════════════════════════════════
# LOGS PAGE
# ══════════════════════════════════════════════════════════════════════════════
class LogsPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._entries=[]; self._build()

    def _build(self):
        scroll=QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        cc,cl=make_card("Application Logs")
        cl.addWidget(_mk_lbl("Recent operations and legion_cli command output.",C_TEXT2,size=12))
        cl.addWidget(make_div())

        self._log_area=QWidget(); self._log_area.setStyleSheet(f"background:{C_BG};")
        self._log_layout=QVBoxLayout(self._log_area); self._log_layout.setContentsMargins(0,0,0,0); self._log_layout.setSpacing(2)
        log_scroll=QScrollArea(); log_scroll.setWidgetResizable(True); log_scroll.setFixedHeight(300)
        log_scroll.setStyleSheet(f"border:1px solid {C_BORDER};border-radius:8px;background:{C_CARD};")
        log_scroll.setWidget(self._log_area)
        cl.addWidget(log_scroll)

        clear_btn=QPushButton("Clear Logs")
        clear_btn.setFixedHeight(32)
        clear_btn.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;font-size:12px;padding:0 16px;")
        clear_btn.clicked.connect(self._clear)
        br=QHBoxLayout(); br.addWidget(clear_btn); br.addStretch(); cl.addLayout(br)
        root.addWidget(cc)
        root.addStretch()

    def log(self,msg:str):
        ts=time.strftime("%H:%M:%S")
        lbl=QLabel(f"[{ts}] {msg}")
        lbl.setStyleSheet(f"color:{C_TEXT2};font-size:11px;font-family:monospace;background:transparent;padding:2px 4px;")
        lbl.setWordWrap(True)
        self._entries.append(lbl)
        self._log_layout.addWidget(lbl)
        # Keep last 100 entries
        if len(self._entries)>100:
            old=self._entries.pop(0)
            old.setParent(None); old.deleteLater()

    def _clear(self):
        for lbl in self._entries:
            lbl.setParent(None); lbl.deleteLater()
        self._entries.clear()
