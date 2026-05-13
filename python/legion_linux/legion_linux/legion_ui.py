#!/usr/bin/env python3
"""Legion Linux Toolkit — UI widget primitives and page scaffolding."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy, QSlider, QStackedWidget, QComboBox,
    QSpinBox, QDoubleSpinBox, QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor

from .legion_utils import (
    C_BG, C_SIDEBAR, C_CARD, C_CARD2, C_BORDER, C_TEXT, C_TEXT2, C_TEXT3,
    C_HOVER, C_ACTIVE, C_SHADOW, C_ACCENT, C_GREEN, C_BLUE, C_ORANGE, C_RED, C_PURPLE,
    send_notif,
)

# ── BarFill ────────────────────────────────────────────────────────────────────
class BarFill(QWidget):
    def __init__(self, pct=0, color=None, parent=None):
        super().__init__(parent)
        self._pct = float(max(0, min(100, pct)))
        self._color = color or C_ACCENT
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._anim = QPropertyAnimation(self, b"pct_prop", self)
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    @pyqtProperty(float)
    def pct_prop(self): return self._pct
    @pct_prop.setter
    def pct_prop(self, v): self._pct = v; self.update()
    def set_pct(self, pct, color=None):
        t = float(max(0, min(100, pct)))
        if color: self._color = color
        if abs(t-self._pct)<0.3: self._pct=t; self.update(); return
        self._anim.stop(); self._anim.setStartValue(self._pct); self._anim.setEndValue(t); self._anim.start()
    def _bar_color(self, pct):
        if self._color != C_ACCENT: return QColor(self._color)
        if pct>85: return QColor(C_RED)
        if pct>65: return QColor(C_ORANGE)
        return QColor(C_ACCENT)
    def paintEvent(self, e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        p.setBrush(QBrush(QColor(C_BORDER))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0,0,w,h,3,3)
        fill=int(w*self._pct/100)
        if fill>0:
            p.setBrush(QBrush(self._bar_color(self._pct)))
            p.drawRoundedRect(0,0,fill,h,3,3)
        p.end()

# ── StatRow ────────────────────────────────────────────────────────────────────
class StatRow(QWidget):
    def __init__(self, label, value_str="\u2014", pct=0, lbl_w=110, val_w=110, color=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26); self.setStyleSheet("background:transparent;")
        lay=QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        self._lbl=QLabel(label); self._lbl.setFixedWidth(lbl_w)
        self._lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;")
        lay.addWidget(self._lbl)
        self._bar=BarFill(pct,color); lay.addWidget(self._bar)
        self._val=QLabel(value_str); self._val.setFixedWidth(val_w)
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        self._val.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:600;")
        lay.addWidget(self._val)
    def update_value(self, value_str, pct, color=None):
        self._val.setText(value_str); self._bar.set_pct(pct,color)
    def set_value(self, value_str, pct=0, color=None, visible=True):
        self._val.setText(value_str); self._bar.set_pct(pct,color); self.setVisible(visible)

# ── InfoRow ────────────────────────────────────────────────────────────────────
class InfoRow(QWidget):
    def __init__(self, label, value="\u2014", lbl_w=180, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40); self.setStyleSheet("background:transparent;")
        lay=QHBoxLayout(self); lay.setContentsMargins(0,4,0,4)
        lbl=QLabel(label); lbl.setFixedWidth(lbl_w)
        lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;")
        self._val=QLabel(value); self._val.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:500;")
        lay.addWidget(lbl); lay.addWidget(self._val); lay.addStretch()
    def set_value(self, v): self._val.setText(v)

# ── ToggleSwitch ───────────────────────────────────────────────────────────────
class ToggleSwitch(QWidget):
    def __init__(self, path=None, on_change=None, parent=None, read_val=None):
        super().__init__(parent)
        self.path=path; self.on_change=on_change
        val=read_val if read_val else ("0")
        self._checked=val=="1"; self._cx=26.0 if self._checked else 6.0
        self.setFixedSize(56,32); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim=QPropertyAnimation(self,b"cx",self); self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    @pyqtProperty(float)
    def cx(self): return self._cx
    @cx.setter
    def cx(self,v): self._cx=v; self.update()
    def isChecked(self): return self._checked
    def setChecked(self,val,write=True,silent=False):
        self._checked=val
        self._anim.stop(); self._anim.setStartValue(self._cx); self._anim.setEndValue(26.0 if val else 6.0)
        self._anim.start(); self.update()
        if write and self.path:
            from legion_hardware import wrsys
            wrsys(self.path,"1" if val else "0")
        if self.on_change and not silent: self.on_change(val)
    def mousePressEvent(self,e):
        self.setChecked(not self._checked)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg=C_ACCENT if self._checked else C_TEXT3
        p.setBrush(QBrush(QColor(bg))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0,0,56,32,16,16)
        p.setBrush(QBrush(QColor("#ffffff"))); p.drawEllipse(int(self._cx),6,20,20); p.end()

# ── NotifyToggle ───────────────────────────────────────────────────────────────
class NotifyToggle(QWidget):
    def __init__(self,title,desc,path,notif_title=None,notif_on="Enabled",notif_off="Disabled",
                 on_change=None,read_val=None,parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;"); self.setFixedHeight(56)
        self._nt=notif_title or title; self._non=notif_on; self._noff=notif_off
        lay=QHBoxLayout(self); lay.setContentsMargins(0,4,0,4)
        col=QVBoxLayout(); col.setSpacing(3)
        t=QLabel(title); t.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;border:none;")
        d=QLabel(desc); d.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;border:none;")
        d.setWordWrap(True); col.addWidget(t); col.addWidget(d)
        lay.addLayout(col); lay.addStretch()
        self.toggle=ToggleSwitch(path,self._on_toggle,parent=self,read_val=read_val)
        lay.addWidget(self.toggle,alignment=Qt.AlignmentFlag.AlignVCenter)
        self._oc=on_change
    def _on_toggle(self,val):
        send_notif(self._nt,self._non if val else self._noff)
        if self._oc: self._oc(val)

# ── StatusBadge ────────────────────────────────────────────────────────────────
class StatusBadge(QWidget):
    def __init__(self,title,value="\u2014",color=C_TEXT3,tooltip="",parent=None):
        super().__init__(parent)
        self.setMinimumWidth(90); self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"QWidget{{background:{C_CARD2};border-radius:10px;}}")
        lay=QVBoxLayout(self); lay.setContentsMargins(10,8,10,8); lay.setSpacing(2)
        self._t=QLabel(title); self._t.setStyleSheet(f"color:{C_TEXT2};font-size:10px;background:transparent;border:none;font-weight:500;")
        self._v=QLabel(value); self._v.setStyleSheet(f"color:{color};font-size:13px;font-weight:700;background:transparent;border:none;")
        self._v.setWordWrap(False); self._v.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        lay.addWidget(self._t); lay.addWidget(self._v)
        if tooltip: self.setToolTip(tooltip)
    def set_value(self,v,color=None):
        self._v.setText(v)
        if color: self._v.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;background:transparent;border:none;")

# ── AIBadge ────────────────────────────────────────────────────────────────────
class AIBadge(StatusBadge):
    def __init__(self,on_change=None,parent=None):
        super().__init__("L1 AI Engine","OFF",C_TEXT3,
                         "Lenovo L1 AI Engine\nOn Linux: adjusts EPP for performance.",parent)
        self.toggled=on_change
        lay=self.layout(); lay.removeWidget(self._v); self._v.setParent(None)
        row=QHBoxLayout(); row.setContentsMargins(0,0,0,0); row.setSpacing(4)
        self._v=QLabel("OFF"); self._v.setStyleSheet(f"color:{C_TEXT3};font-size:12px;font-weight:600;background:transparent;border:none;")
        self._v.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self._tog=ToggleSwitch(path=None,on_change=self._handle_toggle,read_val="0")
        self._tog.setFixedSize(36,20)
        row.addWidget(self._v); row.addWidget(self._tog); lay.addLayout(row)
    def _handle_toggle(self,val):
        col=C_GREEN if val else C_TEXT3
        self._v.setText("ON" if val else "OFF")
        self._v.setStyleSheet(f"color:{col};font-size:12px;font-weight:600;background:transparent;border:none;")
        if self.toggled: self.toggled(val)
    def set_state(self,is_on:bool,silent:bool=False):
        col=C_GREEN if is_on else C_TEXT3
        self._v.setText("ON" if is_on else "OFF")
        self._v.setStyleSheet(f"color:{col};font-size:12px;font-weight:600;background:transparent;border:none;")
        self._tog._checked=is_on; self._tog._cx=22.0 if is_on else 4.0; self._tog.update()

# ── ProfileBtn ─────────────────────────────────────────────────────────────────
class ProfileBtn(QPushButton):
    def __init__(self,profile,parent=None):
        super().__init__(parent)
        self.profile=profile; self.setCheckable(True); self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        from legion_utils import PROFILE_COLORS,PROFILE_ICONS,PROFILE_LABELS
        color=PROFILE_COLORS[profile]; icon=PROFILE_ICONS[profile]; label=PROFILE_LABELS[profile]
        self.setStyleSheet(
            f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};border:none;border-radius:10px;font-size:12px;text-align:center;padding:4px 2px;}}"
            f"QPushButton:checked{{background:rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},30);color:{color};}}"
            f"QPushButton:hover:!checked{{background:{C_HOVER};color:{C_TEXT};}}")
        lay=QVBoxLayout(self); lay.setContentsMargins(4,6,4,6); lay.setSpacing(1); lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        li=QLabel(icon); li.setAlignment(Qt.AlignmentFlag.AlignCenter); li.setStyleSheet("background:transparent;font-size:16px;")
        ln=QLabel(label); ln.setAlignment(Qt.AlignmentFlag.AlignCenter); ln.setStyleSheet(f"background:transparent;font-size:12px;font-weight:600;color:{color};")
        ld=QLabel(""); ld.setAlignment(Qt.AlignmentFlag.AlignCenter); ld.setStyleSheet(f"background:transparent;font-size:12px;color:{C_TEXT3};")
        lay.addWidget(li); lay.addWidget(ln); lay.addWidget(ld)

# ── SidebarBtn ─────────────────────────────────────────────────────────────────
class SidebarBtn(QPushButton):
    def __init__(self,icon_char,label,parent=None):
        super().__init__(parent); self.setCheckable(True); self.setFixedSize(204,44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setLayout(QHBoxLayout()); self.layout().setContentsMargins(16,0,16,0); self.layout().setSpacing(12)
        self.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._icon=QLabel(icon_char); self._icon.setStyleSheet("font-size:18px;background:transparent;")
        self._icon.setFixedSize(20,20); self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text=QLabel(label); self._text.setStyleSheet("font-size:13px;background:transparent;font-weight:500;")
        self.layout().addWidget(self._icon); self.layout().addWidget(self._text); self.layout().addStretch()
        self.toggled.connect(self._upd); self._upd(self.isChecked())
    def _upd(self,chk):
        if chk: bg=C_ACTIVE; fg=C_ACCENT; il=C_ACCENT; tl=C_ACCENT
        else: bg="transparent"; fg=C_TEXT2; il=C_TEXT3; tl=C_TEXT2
        self.setStyleSheet(f"QPushButton{{background:{bg};border:none;color:{fg};border-radius:8px;}}QPushButton:hover{{background:{C_HOVER};}}")
        self._icon.setStyleSheet(f"color:{il};font-size:18px;background:transparent;")
        self._text.setStyleSheet(f"color:{tl};font-size:13px;background:transparent;font-weight:500;")

# ── FanWidget (animated fan) ───────────────────────────────────────────────────
class FanWidget(QWidget):
    def __init__(self,color:str,size:int=64,parent=None):
        super().__init__(parent)
        self._color=QColor(color); self._dim=QColor(color); self._dim.setAlphaF(0.25)
        self._angle=0.0; self._speed=0.0; self._rpm=0
        self.setFixedSize(size,size); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._timer=QTimer(self); self._timer.timeout.connect(self._tick); self._timer.start(16)
    def set_rpm(self,rpm:int):
        self._rpm=rpm; self._speed=min(rpm/5000*12.0,14.0)
    def _tick(self):
        if self._speed>0: self._angle=(self._angle+self._speed)%360; self.update()
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s=self.width(); cx,cy,r=s/2,s/2,s*0.44
        p.translate(cx,cy); p.rotate(self._angle)
        for i in range(3):
            p.save(); p.rotate(i*120)
            bw, bh = r*0.52, r*0.78
            grad=__import__('PyQt6.QtGui',fromlist=['QRadialGradient']).QRadialGradient(0,-r*0.35,r*0.55)
            grad.setColorAt(0.0,self._color); grad.setColorAt(1.0,self._dim)
            p.setBrush(grad); p.setPen(Qt.PenStyle.NoPen)
            p.translate(r*0.28,-r*0.38)
            p.drawEllipse(int(-bw/2),int(-bh/2),int(bw),int(bh))
            p.restore()
        hr=int(r*0.22); p.setBrush(self._color); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(-hr,-hr,hr*2,hr*2)
        inner=max(2,int(r*0.08)); p.setBrush(QColor(C_BG)); p.drawEllipse(-inner,-inner,inner*2,inner*2)
        p.end()

# ── Helper factories ───────────────────────────────────────────────────────────
def _mk_lbl(text:str,color:str=None,size:int=12,bold:bool=False):
    lbl=QLabel(text); c=color or C_TEXT2; w="600" if bold else "400"
    lbl.setStyleSheet(f"color:{c};font-size:{size}px;font-weight:{w};background:transparent;"); lbl.setWordWrap(True); return lbl

def _mk_lineedit(text:str="",width:int=100,placeholder:str=""):
    le=QLineEdit(text); le.setPlaceholderText(placeholder); le.setFixedWidth(width)
    le.setStyleSheet(f"QLineEdit{{background:{C_CARD2};color:{C_TEXT};border:none;border-radius:8px;padding:8px 12px;font-size:13px;selection-background-color:{C_ACCENT};}}")
    return le

def make_div():
    f=QWidget(); f.setFixedHeight(6); f.setStyleSheet("background:transparent;"); return f

def make_card(title=""):
    card=QWidget(); card.setStyleSheet(f"background:{C_CARD};border-radius:12px;")
    card.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum)
    lay=QVBoxLayout(card); lay.setContentsMargins(20,16,20,16); lay.setSpacing(12)
    if title:
        t=QLabel(title); t.setStyleSheet(f"color:{C_TEXT};font-size:14px;font-weight:600;background:transparent;border:none;")
        lay.addWidget(t)
    return card, lay

def sec_title(text):
    l=QLabel(text); l.setStyleSheet(f"color:{C_TEXT};font-size:14px;font-weight:600;background:transparent;border:none;"); return l

def combo_style():
    return (f"QComboBox{{background:{C_CARD2};color:{C_TEXT};border:none;border-radius:8px;padding:8px 14px;font-size:13px;min-width:180px;}}"
            f"QComboBox::drop-down{{border:none;width:24px;}}"
            f"QComboBox QAbstractItemView{{background:{C_CARD2};color:{C_TEXT};border:none;selection-background-color:{C_ACCENT};selection-color:#fff;padding:4px;}}")

def scrollable(widget_factory):
    outer=QWidget(); outer.setStyleSheet(f"background:{C_BG};")
    scroll=QScrollArea(outer); scroll.setWidgetResizable(True); scroll.setStyleSheet("border:none;background:transparent;")
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    inner=QWidget(); inner.setStyleSheet(f"background:{C_BG};")
    root=QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
    lay=QVBoxLayout(outer); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
    scroll.setWidget(inner); widget_factory(root); root.addStretch()
    return outer
