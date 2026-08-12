#!/usr/bin/env python3
"""
Legion Linux Toolkit — Dashboard GUI  v0.6.3
New: LLL integration, IC temp, AC/battery auto-switching, kernel 7.x fallback.
KDE Plasma 6 / Wayland compatible.
"""

import os, sys, subprocess, json, time, threading, shutil
from pathlib import Path

_lib = Path(__file__).resolve().parent / "lib"
if not (_lib / "lll_adapter.py").exists():
    _lib = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(_lib))
import lll_adapter as lll

# NOTE: no forced QT_QPA_PLATFORM / WAYLAND_DISPLAY here — Qt auto-selects the
# correct platform plugin (Wayland or X11) at runtime so the toolkit is not tied
# to a specific compositor or display name. The fallback below is standard Linux.
if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"

# ── Legion logo icon (embedded, no external file) ────────────────────────────
_LEGION_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAJXUlEQVR4nOVbfYxU1RX/nXPfzOzMDizsAkpZFhYWQUjVViw2RfshVRpbbJUQY43WrNImSlqbtv9YRWr/qZim1VQrEWsM/QhqFRvURq3SatKI+JHWtd3PWVh32e/Z2Z3ZmXnv3tPcmR3cEsD9mN3Hwm8ymZn73r3nnt8799xzz71DOAH+tHLlt89h3dRNje9sqUMWMxR7V68OVohc2sGRyhs/OPSHE93DJyqcrfXTsyAbzjM1v/3bedUXAiDMLNBLq6s/t0ZSj0SJ1pdnBp456Y04Cd6++OKAHuy/Yx68Hw8QP9WV9B7a2NbWBEBw+oJeWj5/+SIu3RYhfV2vqPu5IfbIWsA9aQWcAtsBZ+OyJZsqHf1EFjrRhdLH3nEGHri9rjt5uhHxcFXV3HUl+P488W4V4tkx4Oau+rbntwD6VPVoDG3TgeoVl1U76SdIsktcDrW2GdnZ5Kk/3hKLxeEznl06Z05lqOzaedq9JyiyOMOhWCcCN3y+oeGtsTwkGqMceq1m0brFkN1BI6uIICkVfLtf1M5h1+z/ciyWxjTjtaVLS8qU/mYZ4wdKzCWONhgKBt5rpcDWq/7T9M5YLZTGI/SFmprlVew+NdfNXqgJpNl4GS55pSOr7++Otf3jk8ytGNgLqIWrai5baNyfBLTZQPAcBiSunHdjUrLl6w0NzeNpj8bbgT01iyov5ZJHQ3poo4FDBAPDGBpCeH+9xvZrm5vrMTWgPy9fvuZ8lruiMny1CEVJNIiUJFXgxUMu197Q0tI57kYxAewpL599cXn0oRDpGxxjlDKAIRHDgXScaFdXBg+9cfhwbAdgMElsB3j9iqqli5i3RbW7FUaHDTEcyRHvDXD4yfd7Wn54Yx8SE2mfJtqxRxcujFxUWvKLhchsNYKAbYtgRIEky077ANHDh131+DUtLV0TnTH+cl7lokXs1JYZfVtQu58yVgQMOUaJ60imS0p+824yfc93OzpSE9WDMAn8srIyfHk0dHuFzvxcGTdowLaHIIgALC5TfY8K/Kq1N/n7Ld3dQ2Ntd+/8+dHVFaWbQ56+Oyi6mkVgKN9XAxIiynRy6K4X6psf3AF4k9FBTabyXxMJb2FP/1vnlC/4aBbxl0h0KGcJFmLAwvOiBhvnRwJXbi6r6FvS399w4BTDwjq4bSuWXbsygl1RD7cx3AplDBm2j55AIgIHiTiFb22ub/7dHUVwuoQiQOw0uXLxpmpjHmGNc4U9gnHA0BCytiAi5CDhBF4/ovGz+Y0Vb67FIXd01Dk40PuF8gB2lHuZ9aKF7MtG6jLSSTYkGYfbmymy9cr6+heLFYhRMRoptPX36upLFjiZpyKaFwvp3HAoIKdIjgg1PKhKnmn1nAd3Nv/3vZ8uW/yZJQ5vCxrvOkebsJd72jiupkhWBeo/ROCmb9S3HCxmFEooMl5eseT8asKTIZ35rAExWXeQk0IjLEDs8PBUoC8t/GYEZj1Ezx25eEx5gdiVmggIwyp4qM2Y669oPGLXIkUFYQrw9IoFy9ZweHfEy14OCFsxVlDBnO0nww5oq+eI3yxcPdYje1WZ4aC8GnNRe1VT+5Gp6Kuaikb39iX7186au2+uctZE4NVYv205KOiW/7Q/8+W5gtxPW56nRQimL8DPHswEb9rccsROpZgxBFjsi8fT62bPea40GJofhncRC1hGkVBAfjCLndzyBUQCVtk4OY89F5i99c6GBrvyxIwjwGJfPO6tcIKvLygtMaVG1glp53gOyEYMIDvP28EiBE4nSe046B3ZcWdDdwZTDDXVAl5OJt21PfE3yyrm9EZEfYWgnby9fww7QhxjbCg93KsC3+ttaN31rfj0pOII0wQ7FxxYtfj6Gs/bYwyxkMkN/sJ8xiDz72B48z8/bNpXjDXEWMHTJcgy3eXKQXckuPl/iLhEXsfA8NvTqfy0EmC1zPanujxWSZCR0T7AwhCnzo20T5m3Px0IQHl5X8aIzkCUHfijIkQSB+ZoVXD684w8ncKqgqslzKqZoG2AlwfZrwKteLAOq3FGE1BXV4eUlw/9jseQFm2vn9EEANAu42huGhwx9kL4o4mPyCTX9qc9AR8AMsh60CZOCprnVwA2l4SOe33Ya+DpFGYVnOdRnbLLwQLykaCEicad0JyJQwCDdgoc7QRy60BCCnpCSc0ZR4DH0pb/9rG123WA4zhTstw97QhIOiUD+UxAXrSNAQRG4mlO0plOAAEShWk0xDqf4czDYzYlSn3kx4YrT7fAxBAknw0t6Co2LDKt2TFnzWc2AeK4Q4rQb9cAI5khBAg9pSF1djjBRCjoalC6kACy0ETJQegpT36cFgRE+9KJINB+LAUGgTLcGx3EhLe3ZhQBnehEOp/tHoGNAUymN9QxrXkA3wh4oxNZ16Cv4ALtyshR6qNbYpj2Qxa+ELALcDU7cZsILUyNw6J9Ud4XAux+fylRI0t+PWAJCCtq2e5DXyx8EepqyS177TAwAPW7+d9nBQH3ApKE7jQj24CWAMNOUU6TzAgCCJBex4vrvP/LGUHCZH2ZAn0bArM8bldkhu0GoCKkykTa4RMcP4R6kLQm6JFcgMQ/3h85Oyygm7MpFpXJ6U0qQSXhbpxNBHhUkdBEKRsOZ8jo9iF90sPMZyQBbalUnyYM2P1BI6ovFov14GzyAQNtba6uqfTs4cKMEXOgiG1/bY/MZhc/EoNrQFieKxQ0EWOfCeCBF2+khO8WUAfYyKefhU0ogNYvFikGuHq3bKAs/iWCu0G4AEBp7k24wJbZa/Ye3wnYm9sLpR57GiQlZqAY+wFWMSG8bHfgTnFblb1n4xNyha8EWISAJhFDEeYWKoLZC2H3WO9ng8dtHfhFgFU4aSgNFvS4o3NDE4Md85/w5I9H1Ugd+GYB/Z7J2JPPGoGWyWaDcw5vvHUEm/wkQDgkzQoOXHiTT4YWvP24quTrMHwCCR9VjOEoqdZjCWIfwD7JJW14yIPI4Wz2hOcFxgXBuI/QCvJ1GD4hZpLJFFEmETBtk/UBNsgZdx3C8776gAGec3SInOE34t6k84E2wgNweBxVWpXBTl8t4NzGxmRIpG53T8+k98RseEuC2rHebxi1z9fSoK8EbAFM+0hitBjYX0uvkOCrn2AJhw1jw0vfoVcLBQyfYAd9D2Nc//EbCwkSxKeJcB+A9wkYsu/cd8J99tpo5eEn7NT364tW3ez3P9P/B3WqLVdxvc4JAAAAAElFTkSuQmCC"

def _legion_icon():
    import base64 as _b64
    from PyQt6.QtGui import QPixmap as _px
    data = _b64.b64decode(_LEGION_ICON_B64)
    pm = _px(); pm.loadFromData(data)
    from PyQt6.QtGui import QIcon as _ic
    return _ic(pm)



from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QSlider, QStackedWidget, QComboBox, QToolTip, QSpinBox,
    QDoubleSpinBox, QLineEdit
)
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                           pyqtProperty, QThread, pyqtSignal, QPoint, QPointF, QRect)
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor, QPolygonF

# ══════════════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════════════
LEGION_SYS_BASEPATH = Path(lll.LEGION_SYS_BASEPATH)
IDEAPAD_SYS_BASEPATH = Path(lll.IDEAPAD_SYS_BASEPATH)
LEGION_POWERMODE    = LEGION_SYS_BASEPATH / "powermode"
AMD_BOOST           = Path("/sys/devices/system/cpu/cpufreq/boost")

CONSERVATION_MODE = IDEAPAD_SYS_BASEPATH / "conservation_mode"
CAMERA_POWER      = IDEAPAD_SYS_BASEPATH / "camera_power"
FN_LOCK           = IDEAPAD_SYS_BASEPATH / "fn_lock"
USB_CHARGING      = IDEAPAD_SYS_BASEPATH / "usb_charging"
RAPID_CHARGE      = LEGION_SYS_BASEPATH / "rapidcharge"
WINKEY            = LEGION_SYS_BASEPATH / "winkey"
OVERDRIVE         = LEGION_SYS_BASEPATH / "overdrive"
GSYNC             = LEGION_SYS_BASEPATH / "gsync"
TOUCHPAD          = LEGION_SYS_BASEPATH / "touchpad"
POWER_CHARGE_MODE = LEGION_SYS_BASEPATH / "powerchargemode"
THERMAL_MODE      = LEGION_SYS_BASEPATH / "thermalmode"
NVIDIA_BACKLIGHT  = Path("/sys/class/backlight/nvidia_wmi_ec_backlight/brightness")

BAT = next(
    (Path(p) for p in [
        "/sys/class/power_supply/BAT0",
        "/sys/class/power_supply/BAT1",
        "/sys/class/power_supply/CMB0",
    ] if Path(p).exists()),
    Path("/sys/class/power_supply/BAT0"),
)

ACTIONS_CFG       = Path.home() / ".config/legion-toolkit/actions.json"
OC_CFG            = Path.home() / ".config/legion-toolkit/overclock.json"
CFG_DIR         = Path.home() / ".config/legion-toolkit"
FAN_CFG           = Path.home() / ".config/legion-toolkit/fan.json"
APP_CFG           = Path.home() / ".config/legion-toolkit/appearance.json"
HARDWARE_CFG      = Path.home() / ".config/legion-toolkit/hardware.json"
LANG_CFG          = Path.home() / ".config/legion-toolkit/language.json"
FIRST_RUN_FLAG    = Path.home() / ".config/legion-toolkit/first_run_done"

# ══════════════════════════════════════════════════════════════════════════════
# TRANSLATIONS
# ══════════════════════════════════════════════════════════════════════════════
_LANG = "en"   # set by first-run wizard or saved config

_TR = {
    "en": {
        "app_name":"Legion Linux Toolkit","home":"Home","battery":"Battery",
        "performance":"Performance","display":"Display","keyboard":"Keyboard",
        "system":"System","overclock":"Overclock","fan":"Fan","actions":"Actions",
        "about":"About","power_mode":"Power Mode","battery_mode":"Battery Mode",
        "gpu_mode":"GPU Working Mode","apply":"Apply","save":"Save",
        "enabled":"Enabled","disabled":"Disabled","on":"ON","off":"OFF",
        "auto":"Auto","full_speed":"Full Speed","detecting":"Detecting hardware…",
        "welcome":"Welcome to Legion Linux Toolkit",
        "choose_lang":"Choose your language to get started.",
        "hw_detect_title":"Hardware Detection",
        "hw_detect_desc":"Scanning your device — this runs once and is saved.",
        "hw_done":"Detection complete!","next":"Next","finish":"Finish",
        "brightness":"Brightness","resolution":"Resolution",
        "refresh_rate":"Refresh Rate","theme":"Theme",
        "conservation":"Conservation (~60%)","rapid_charge":"Rapid Charge",
        "normal":"Normal","quiet":"Quiet","balanced":"Balanced",
        "performance_label":"Performance","custom":"Custom",
    },
    "fr": {
        "app_name":"Legion Linux Toolkit","home":"Accueil","battery":"Batterie",
        "performance":"Performance","display":"Affichage","keyboard":"Clavier",
        "system":"Système","overclock":"Overclocking","fan":"Ventilateur",
        "actions":"Actions","about":"À propos","power_mode":"Mode d'alimentation",
        "battery_mode":"Mode batterie","gpu_mode":"Mode GPU",
        "apply":"Appliquer","save":"Enregistrer",
        "enabled":"Activé","disabled":"Désactivé","on":"OUI","off":"NON",
        "auto":"Auto","full_speed":"Vitesse max","detecting":"Détection…",
        "welcome":"Bienvenue dans Legion Linux Toolkit",
        "choose_lang":"Choisissez votre langue.",
        "hw_detect_title":"Détection matérielle",
        "hw_detect_desc":"Analyse de votre appareil — exécuté une seule fois.",
        "hw_done":"Détection terminée !","next":"Suivant","finish":"Terminer",
        "brightness":"Luminosité","resolution":"Résolution",
        "refresh_rate":"Taux de rafraîchissement","theme":"Thème",
        "conservation":"Conservation (~60%)","rapid_charge":"Charge rapide",
        "normal":"Normal","quiet":"Silencieux","balanced":"Équilibré",
        "performance_label":"Performance","custom":"Personnalisé",
    },
    "de": {
        "app_name":"Legion Linux Toolkit","home":"Start","battery":"Akku",
        "performance":"Leistung","display":"Anzeige","keyboard":"Tastatur",
        "system":"System","overclock":"Übertaktung","fan":"Lüfter",
        "actions":"Aktionen","about":"Über","power_mode":"Energiemodus",
        "battery_mode":"Akkumodus","gpu_mode":"GPU-Modus",
        "apply":"Anwenden","save":"Speichern",
        "enabled":"Aktiviert","disabled":"Deaktiviert","on":"AN","off":"AUS",
        "auto":"Auto","full_speed":"Volle Drehzahl","detecting":"Erkennung…",
        "welcome":"Willkommen bei Legion Linux Toolkit",
        "choose_lang":"Wählen Sie Ihre Sprache.",
        "hw_detect_title":"Hardware-Erkennung",
        "hw_detect_desc":"Gerät wird einmalig gescannt und gespeichert.",
        "hw_done":"Erkennung abgeschlossen!","next":"Weiter","finish":"Fertig",
        "brightness":"Helligkeit","resolution":"Auflösung",
        "refresh_rate":"Bildwiederholrate","theme":"Design",
        "conservation":"Schutz (~60%)","rapid_charge":"Schnellladen",
        "normal":"Normal","quiet":"Leise","balanced":"Ausgewogen",
        "performance_label":"Leistung","custom":"Benutzerdefiniert",
    },
    "es": {
        "app_name":"Legion Linux Toolkit","home":"Inicio","battery":"Batería",
        "performance":"Rendimiento","display":"Pantalla","keyboard":"Teclado",
        "system":"Sistema","overclock":"Overclocking","fan":"Ventilador",
        "actions":"Acciones","about":"Acerca de","power_mode":"Modo energía",
        "battery_mode":"Modo batería","gpu_mode":"Modo GPU",
        "apply":"Aplicar","save":"Guardar",
        "enabled":"Activado","disabled":"Desactivado","on":"ON","off":"OFF",
        "auto":"Auto","full_speed":"Velocidad máx","detecting":"Detectando…",
        "welcome":"Bienvenido a Legion Linux Toolkit",
        "choose_lang":"Elige tu idioma.",
        "hw_detect_title":"Detección de hardware",
        "hw_detect_desc":"Escaneando tu dispositivo — se ejecuta una vez.",
        "hw_done":"¡Detección completa!","next":"Siguiente","finish":"Finalizar",
        "brightness":"Brillo","resolution":"Resolución",
        "refresh_rate":"Tasa de refresco","theme":"Tema",
        "conservation":"Conservación (~60%)","rapid_charge":"Carga rápida",
        "normal":"Normal","quiet":"Silencioso","balanced":"Equilibrado",
        "performance_label":"Rendimiento","custom":"Personalizado",
    },
    "pt": {
        "app_name":"Legion Linux Toolkit","home":"Início","battery":"Bateria",
        "performance":"Desempenho","display":"Ecrã","keyboard":"Teclado",
        "system":"Sistema","overclock":"Overclocking","fan":"Ventoinha",
        "actions":"Ações","about":"Sobre","power_mode":"Modo de energia",
        "battery_mode":"Modo bateria","gpu_mode":"Modo GPU",
        "apply":"Aplicar","save":"Guardar",
        "enabled":"Ativado","disabled":"Desativado","on":"ON","off":"OFF",
        "auto":"Auto","full_speed":"Vel. máxima","detecting":"A detetar…",
        "welcome":"Bem-vindo ao Legion Linux Toolkit",
        "choose_lang":"Escolha o seu idioma.",
        "hw_detect_title":"Deteção de hardware",
        "hw_detect_desc":"A analisar o seu dispositivo — executado uma vez.",
        "hw_done":"Deteção concluída!","next":"Seguinte","finish":"Concluir",
        "brightness":"Brilho","resolution":"Resolução",
        "refresh_rate":"Taxa de atualização","theme":"Tema",
        "conservation":"Conservação (~60%)","rapid_charge":"Carga rápida",
        "normal":"Normal","quiet":"Silencioso","balanced":"Equilibrado",
        "performance_label":"Desempenho","custom":"Personalizado",
    },
    "tr": {
        "app_name":"Legion Linux Toolkit","home":"Ana Sayfa","battery":"Pil",
        "performance":"Performans","display":"Ekran","keyboard":"Klavye",
        "system":"Sistem","overclock":"Hız Aşırtma","fan":"Fan",
        "actions":"Eylemler","about":"Hakkında","power_mode":"Güç modu",
        "battery_mode":"Pil modu","gpu_mode":"GPU modu",
        "apply":"Uygula","save":"Kaydet",
        "enabled":"Etkin","disabled":"Devre dışı","on":"AÇIK","off":"KAPALI",
        "auto":"Otomatik","full_speed":"Tam hız","detecting":"Algılanıyor…",
        "welcome":"Legion Linux Toolkit'e Hoş Geldiniz",
        "choose_lang":"Dilinizi seçin.",
        "hw_detect_title":"Donanım Algılama",
        "hw_detect_desc":"Cihazınız taranıyor — yalnızca bir kez çalışır.",
        "hw_done":"Algılama tamamlandı!","next":"İleri","finish":"Bitir",
        "brightness":"Parlaklık","resolution":"Çözünürlük",
        "refresh_rate":"Yenileme hızı","theme":"Tema",
        "conservation":"Koruma (~%60)","rapid_charge":"Hızlı şarj",
        "normal":"Normal","quiet":"Sessiz","balanced":"Dengeli",
        "performance_label":"Performans","custom":"Özel",
    },
    "ru": {
        "app_name":"Legion Linux Toolkit","home":"Главная","battery":"Батарея",
        "performance":"Производительность","display":"Дисплей","keyboard":"Клавиатура",
        "system":"Система","overclock":"Разгон","fan":"Вентилятор",
        "actions":"Действия","about":"О программе","power_mode":"Режим питания",
        "battery_mode":"Режим батареи","gpu_mode":"Режим GPU",
        "apply":"Применить","save":"Сохранить",
        "enabled":"Включено","disabled":"Выключено","on":"ВКЛ","off":"ВЫКЛ",
        "auto":"Авто","full_speed":"Макс. скорость","detecting":"Определение…",
        "welcome":"Добро пожаловать в Legion Linux Toolkit",
        "choose_lang":"Выберите язык.",
        "hw_detect_title":"Обнаружение оборудования",
        "hw_detect_desc":"Сканирование устройства — выполняется один раз.",
        "hw_done":"Обнаружение завершено!","next":"Далее","finish":"Готово",
        "brightness":"Яркость","resolution":"Разрешение",
        "refresh_rate":"Частота обновления","theme":"Тема",
        "conservation":"Защита (~60%)","rapid_charge":"Быстрая зарядка",
        "normal":"Нормальный","quiet":"Тихий","balanced":"Сбалансированный",
        "performance_label":"Производительность","custom":"Пользовательский",
    },
    "zh": {
        "app_name":"军团 Linux 工具包","home":"主页","battery":"电池",
        "performance":"性能","display":"显示","keyboard":"键盘",
        "system":"系统","overclock":"超频","fan":"风扇",
        "actions":"操作","about":"关于","power_mode":"电源模式",
        "battery_mode":"电池模式","gpu_mode":"GPU 模式",
        "apply":"应用","save":"保存",
        "enabled":"已启用","disabled":"已禁用","on":"开","off":"关",
        "auto":"自动","full_speed":"全速","detecting":"检测中…",
        "welcome":"欢迎使用军团 Linux 工具包",
        "choose_lang":"请选择您的语言。",
        "hw_detect_title":"硬件检测",
        "hw_detect_desc":"正在扫描您的设备 — 仅运行一次。",
        "hw_done":"检测完成！","next":"下一步","finish":"完成",
        "brightness":"亮度","resolution":"分辨率",
        "refresh_rate":"刷新率","theme":"主题",
        "conservation":"保护模式 (~60%)","rapid_charge":"快速充电",
        "normal":"正常","quiet":"安静","balanced":"均衡",
        "performance_label":"性能","custom":"自定义",
    },
    "ja": {
        "app_name":"Legion Linux ツールキット","home":"ホーム","battery":"バッテリー",
        "performance":"パフォーマンス","display":"ディスプレイ","keyboard":"キーボード",
        "system":"システム","overclock":"オーバークロック","fan":"ファン",
        "actions":"アクション","about":"このアプリについて","power_mode":"電源モード",
        "battery_mode":"バッテリーモード","gpu_mode":"GPU モード",
        "apply":"適用","save":"保存",
        "enabled":"有効","disabled":"無効","on":"オン","off":"オフ",
        "auto":"自動","full_speed":"最大速度","detecting":"検出中…",
        "welcome":"Legion Linux ツールキットへようこそ",
        "choose_lang":"言語を選択してください。",
        "hw_detect_title":"ハードウェア検出",
        "hw_detect_desc":"デバイスをスキャン中 — 一度だけ実行されます。",
        "hw_done":"検出完了！","next":"次へ","finish":"完了",
        "brightness":"輝度","resolution":"解像度",
        "refresh_rate":"リフレッシュレート","theme":"テーマ",
        "conservation":"保護モード (~60%)","rapid_charge":"急速充電",
        "normal":"通常","quiet":"静音","balanced":"バランス",
        "performance_label":"パフォーマンス","custom":"カスタム",
    },
    "ko": {
        "app_name":"Legion Linux 툴킷","home":"홈","battery":"배터리",
        "performance":"성능","display":"디스플레이","keyboard":"키보드",
        "system":"시스템","overclock":"오버클럭","fan":"팬",
        "actions":"작업","about":"정보","power_mode":"전원 모드",
        "battery_mode":"배터리 모드","gpu_mode":"GPU 모드",
        "apply":"적용","save":"저장",
        "enabled":"활성화","disabled":"비활성화","on":"켜짐","off":"꺼짐",
        "auto":"자동","full_speed":"최대 속도","detecting":"감지 중…",
        "welcome":"Legion Linux 툴킷에 오신 것을 환영합니다",
        "choose_lang":"언어를 선택하세요.",
        "hw_detect_title":"하드웨어 감지",
        "hw_detect_desc":"장치 스캔 중 — 한 번만 실행됩니다.",
        "hw_done":"감지 완료!","next":"다음","finish":"완료",
        "brightness":"밝기","resolution":"해상도",
        "refresh_rate":"주사율","theme":"테마",
        "conservation":"보호 모드 (~60%)","rapid_charge":"급속 충전",
        "normal":"일반","quiet":"조용함","balanced":"균형",
        "performance_label":"성능","custom":"사용자 지정",
    },
    "ar": {
        "app_name":"Legion Linux Toolkit","home":"الرئيسية","battery":"البطارية",
        "performance":"الأداء","display":"الشاشة","keyboard":"لوحة المفاتيح",
        "system":"النظام","overclock":"رفع التردد","fan":"المروحة",
        "actions":"الإجراءات","about":"حول","power_mode":"وضع الطاقة",
        "battery_mode":"وضع البطارية","gpu_mode":"وضع GPU",
        "apply":"تطبيق","save":"حفظ",
        "enabled":"مُفعَّل","disabled":"معطَّل","on":"تشغيل","off":"إيقاف",
        "auto":"تلقائي","full_speed":"السرعة الكاملة","detecting":"جارٍ الاكتشاف…",
        "welcome":"مرحباً بك في Legion Linux Toolkit",
        "choose_lang":"اختر لغتك للبدء.",
        "hw_detect_title":"اكتشاف الأجهزة",
        "hw_detect_desc":"جارٍ مسح الجهاز — يعمل مرة واحدة فقط.",
        "hw_done":"اكتمل الاكتشاف!","next":"التالي","finish":"إنهاء",
        "brightness":"السطوع","resolution":"الدقة",
        "refresh_rate":"معدل التحديث","theme":"السمة",
        "conservation":"الحماية (~60%)","rapid_charge":"الشحن السريع",
        "normal":"عادي","quiet":"صامت","balanced":"متوازن",
        "performance_label":"أداء","custom":"مخصص",
    },
}

_LANG_NAMES = {
    "en":"English","fr":"Français","de":"Deutsch","es":"Español",
    "pt":"Português","tr":"Türkçe","ru":"Русский","zh":"中文",
    "ja":"日本語","ko":"한국어","ar":"العربية",
}

def tr(key: str) -> str:
    """Translate a key using the current language, fall back to English."""
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

# ══════════════════════════════════════════════════════════════════════════════
# HARDWARE DETECTION (via LLL backend)
# ══════════════════════════════════════════════════════════════════════════════
HARDWARE_CACHE_TTL = 3600

def _dmi(field: str) -> str:
    try: return Path(f"/sys/class/dmi/id/{field}").read_text().strip().lower()
    except: return ""

def _read_file(path: str, default: str = "") -> str:
    try: return Path(path).read_text().strip()
    except: return default

def _which(cmd: str) -> bool:
    return Path(cmd).exists() or subprocess.run(["which", cmd], capture_output=True).returncode == 0

LEGION_MODELS = {
    "82ju": "Legion 5 15ACH6H", "82gu": "Legion 5 15ACH5",
    "82ms": "Legion 7 16ACHg6", "82rh": "Legion 5 Pro 16ARH7",
    "82sr": "Legion 5 Pro 16",  "82ts": "Legion 7 16",
    "82wm": "Legion Slim 7",
}

def detect_hardware(force: bool = False) -> dict:
    if not force:
        cached = load_hardware()
        if cached:
            import time
            if time.time() - cached.get("_detected_at", 0) < HARDWARE_CACHE_TTL:
                return cached
    vendor = _dmi("sys_vendor")
    product = _dmi("product_name")
    family = _dmi("product_family")
    full = f"{product} {family}".lower()
    if "legion" in full:
        brand = "legion"
        product_code = product[:4] if product else ""
        model_detail = LEGION_MODELS.get(product_code, product.title())
    elif "loq" in full:
        brand = "loq"; model_detail = product.title() if product else "LOQ"
    elif "thinkpad" in full:
        brand = "thinkpad"; model_detail = product.title() if product else "ThinkPad"
    else:
        brand = "lenovo" if "lenovo" in vendor else "unknown"
        model_detail = product.title() if product else "Unknown"
    cpu_vendor = "unknown"; cpu_name = "Unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if "vendor_id" in line.lower():
                v = line.split(":")[1].strip().lower()
                if "amd" in v: cpu_vendor = "amd"
                elif "intel" in v: cpu_vendor = "intel"
            if "model name" in line.lower() and cpu_name == "Unknown":
                cpu_name = line.split(":")[1].strip()
    except: pass
    gpu = lll.get_gpu_info()
    hw = lll.detect_hardware()
    def ex(p): return Path(p).exists()
    cap = {
        "brand": brand, "model": product, "vendor": vendor, "family": family,
        "cpu_vendor": cpu_vendor, "cpu_name": cpu_name,
        "has_nvidia": gpu.get("nvidia", False),
        "has_amd_gpu": gpu.get("amd", False),
        "has_intel_gpu": gpu.get("intel", False),
        "lll_loaded": hw.get("lll_loaded", False),
        "lll_bound": hw.get("lll_bound", False),
        "conservation_mode": hw.get("conservation_mode", False),
        "rapidcharge": hw.get("rapidcharge", False),
        "fn_lock": hw.get("fn_lock", False),
        "camera": hw.get("camera", False),
        "touchpad": hw.get("touchpad", False),
        "winkey": hw.get("winkey", False),
        "usb_charging": hw.get("usb_charging", False),
        "overdrive": hw.get("overdrive", False),
        "gsync": hw.get("gsync", False),
        "fan_fullspeed": hw.get("fan_fullspeed", False),
        "kbd_backlight": hw.get("kbd_backlight", False),
        "ylogo": hw.get("ylogo", False),
        "ioport": hw.get("ioport", False),
        "screen_backlight": bool(list(Path("/sys/class/backlight").iterdir())
                                 if Path("/sys/class/backlight").exists() else []),
        "fingerprint": any(Path(d).exists() and list(Path(d).glob("*")) for d in [
            "/sys/bus/usb/drivers/validity-sensor",
            "/sys/bus/usb/drivers/synaptics-usb",
            "/sys/bus/usb/drivers/fpc_fingerprint",
            "/sys/bus/usb/drivers/elan-fingerprint",
            "/sys/bus/platform/drivers/fingerprint",
        ]),
    }
    return cap

def load_hardware() -> dict:
    try:
        if HARDWARE_CFG.exists():
            return json.loads(HARDWARE_CFG.read_text())
    except: return {}
    
def save_hardware(cap: dict):
    try:
        HARDWARE_CFG.parent.mkdir(parents=True, exist_ok=True)
        import time
        cap["_detected_at"] = time.time()
        HARDWARE_CFG.write_text(json.dumps(cap, indent=2))
    except: pass

    # ── GPU detection — Optimized ───────────────────────────────────────────
    has_nvidia = False
    has_amd_gpu = False
    has_intel_gpu = False
    
    # Try lspci first (most reliable)
    try:
        lspci = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3).stdout.lower()
        has_nvidia = "nvidia" in lspci
        has_amd_gpu = any(k in lspci for k in ["amd", "radeon", "amdgpu"])
        has_intel_gpu = any(k in lspci for k in ["intel", "arc", "xe"])
    except:
        # Fallback: check sysfs
        nvidia_sysfs = Path("/sys/bus/pci/drivers/nvidia")
        has_nvidia = nvidia_sysfs.exists()
        
        amd_gpu_sysfs = Path("/sys/class/drm")
        if amd_gpu_sysfs.exists():
            for card in amd_gpu_sysfs.glob("card*/device/vendor"):
                try:
                    vendor = card.read_text().strip().lower()
                    if "1002" in vendor:  # AMD vendor ID
                        has_amd_gpu = True
                    elif "8086" in vendor:  # Intel vendor ID
                        has_intel_gpu = True
                except:
                    pass

    # ── Intel-specific paths ─────────────────────────────────────────────────
    # Intel TurboBoost
    intel_boost_path = Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
    # Intel powercap RAPL
    intel_rapl = any(Path("/sys/class/powercap").glob("intel-rapl:*")) \
                 if Path("/sys/class/powercap").exists() else False
    # Intel GPU sysfs
    intel_gpu_sysfs = bool(list(Path("/sys/class/drm").glob("card*/device/vendor"))
                           if Path("/sys/class/drm").exists() else [])

    # ── Fingerprint — multiple drivers ───────────────────────────────────────
    fp_drivers = [
        "/sys/bus/usb/drivers/validity-sensor",
        "/sys/bus/usb/drivers/synaptics-usb",
        "/sys/bus/usb/drivers/fpc_fingerprint",
        "/sys/bus/usb/drivers/elan-fingerprint",
        "/sys/bus/platform/drivers/fingerprint",
    ]
    has_fingerprint = any(Path(d).exists() and list(Path(d).glob("*"))
                          for d in fp_drivers)

    def ex(p): return Path(p).exists()

    cap = {
        # Identity
        "brand":      brand,
        "model":      _dmi("product_name"),
        "vendor":     _dmi("sys_vendor"),
        "family":     _dmi("product_family"),
        "cpu_vendor": cpu_vendor,
        "cpu_name":   cpu_name,
        "has_nvidia":    has_nvidia,
        "has_amd_gpu":   has_amd_gpu,
        "has_intel_gpu": has_intel_gpu,

        # Power
        "platform_profile":  ex("/sys/firmware/acpi/platform_profile"),
        "conservation_mode": CONSERVATION_MODE.exists(),
        "rapidcharge":       RAPID_CHARGE.exists(),
        "powerchargemode":   POWER_CHARGE_MODE.exists(),

        # CPU boost — AMD or Intel
        "amd_boost":         AMD_BOOST.exists(),
        "intel_boost":       intel_boost_path.exists(),
        "intel_rapl":        intel_rapl,

        # Display
        "overdrive":  OVERDRIVE.exists(),
        "gsync":      GSYNC.exists(),
        "nw_backlight": NVIDIA_BACKLIGHT.exists(),

        # Input
        "fn_lock":      FN_LOCK.exists(),
        "camera":       CAMERA_POWER.exists(),
        "touchpad":     TOUCHPAD.exists(),
        "winkey":       WINKEY.exists(),
        "usb_charging": USB_CHARGING.exists(),

        # Fan
        "fan_fullspeed": FAN_FULLSPEED.exists(),
        "thermalmode":   THERMAL_MODE.exists(),
        "lockfancontroller": ex(LEGION_SYS_BASEPATH / "lockfancontroller"),
        "minifancurve":    ex(LEGION_SYS_BASEPATH / "minifancurve"),

        # Backlight
        "kbd_backlight":    ex("/sys/class/leds/platform::kbd_backlight/brightness"),
        "ylogo":         ex("/sys/class/leds/platform::ylogo/brightness"),
        "ioport":        ex("/sys/class/leds/platform::ioport/brightness"),
        "screen_backlight": bool(list(Path("/sys/class/backlight").iterdir())
                                 if Path("/sys/class/backlight").exists() else []),

        # ThinkPad-specific
        "tp_charge_start": ex("/sys/class/power_supply/BAT0/charge_start_threshold"),
        "tp_charge_stop":  ex("/sys/class/power_supply/BAT0/charge_stop_threshold"),
        "tp_fan_control":  ex("/proc/acpi/ibm/fan"),
        "tp_trackpoint":   bool(list(Path("/sys/bus/serio/devices").glob("*/speed"))
                                if Path("/sys/bus/serio/devices").exists() else []),
        "tp_thinklight":   ex("/sys/class/leds/tpacpi::thinklight/brightness"),
        "tp_micmute_led":  ex("/sys/class/leds/platform::micmute/brightness"),

        # Yoga-specific
        "yoga_hinge": ex("/sys/bus/platform/drivers/lenovo-ymc"),
        "als_sensor": bool(list(Path("/sys/bus/iio/devices").glob("*/in_illuminance_raw"))
                           if Path("/sys/bus/iio/devices").exists() else []),

        # Tools (cached check)
        "legionaura": _which("legionaura"),
        "envycontrol": _which("envycontrol"),

        # Misc
        "fingerprint": has_fingerprint,
        "wwan": bool(list(Path("/sys/class/net").glob("ww*"))
                    if Path("/sys/class/net").exists() else []),
    }
    return cap

def load_hardware() -> dict:
    try:
        if HARDWARE_CFG.exists():
            return json.loads(HARDWARE_CFG.read_text())
    except: pass
    return {}

def save_hardware(cap: dict):
    import time
    try:
        cap["_detected_at"] = int(time.time())
        HARDWARE_CFG.parent.mkdir(parents=True, exist_ok=True)
        HARDWARE_CFG.write_text(json.dumps(cap, indent=2))
    except: pass

# Global hardware profile — loaded at startup
HW: dict = {}

# L1 AI Engine — try multiple known paths from LenovoLegionLinux driver
_AI_ENGINE_PATHS = [
    Path("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/ai_mode"),
    Path("/sys/bus/platform/devices/VPC2004:00/ai_mode"),
    Path("/sys/bus/wmi/drivers/lenovo-wmi-gamezone/ai_mode"),
]
AI_ENGINE = next((p for p in _AI_ENGINE_PATHS if p.exists()), None)

# RGB keyboard — LenovoLegionLinux driver paths
_KBD_BACKLIGHT_PATHS = [
    Path("/sys/class/leds/platform::kbd_backlight/brightness"),
    Path("/sys/class/leds/legion::kbd_backlight/brightness"),
]
KBD_BACKLIGHT_PATH = next((p for p in _KBD_BACKLIGHT_PATHS if p.exists()), None)
KBD_BACKLIGHT_MAX_PATH = None
if KBD_BACKLIGHT_PATH:
    KBD_BACKLIGHT_MAX_PATH = KBD_BACKLIGHT_PATH.parent / "max_brightness"

RGB_PRESETS = {
    # ── Static colours ───────────────────────────────────────────────────────
    "Static Red":      ("ff0000","ff0000","ff0000","ff0000"),
    "Static Blue":     ("0044ff","0044ff","0044ff","0044ff"),
    "Static Green":    ("00ff44","00ff44","00ff44","00ff44"),
    "Static White":    ("ffffff","ffffff","ffffff","ffffff"),
    "Static Purple":   ("aa00ff","aa00ff","aa00ff","aa00ff"),
    "Static Cyan":     ("00ffff","00ffff","00ffff","00ffff"),
    "Static Orange":   ("ff6600","ff6600","ff6600","ff6600"),
    "Static Pink":     ("ff69b4","ff69b4","ff69b4","ff69b4"),
    # ── Legion themed ────────────────────────────────────────────────────────
    "Legion Red":      ("cc0000","dd1111","ff0000","cc0000"),
    "Legion Blue":     ("001aff","0033ff","004cff","0033ff"),
    "Legion Storm":    ("0033ff","00aaff","00ffcc","00ff88"),
    # ── Gradients ────────────────────────────────────────────────────────────
    "Ocean":           ("001aff","0066ff","00aaff","00ffff"),
    "Sunset":          ("ff2200","ff6600","ffaa00","ffff00"),
    "Aurora":          ("00ff44","00ccff","aa00ff","ff00aa"),
    "Fire":            ("ff0000","ff4400","ff8800","ffaa00"),
    "Galaxy":          ("1a0033","4400aa","8800ff","cc44ff"),
    "Neon":            ("ff00ff","aa00ff","0044ff","00ffff"),
    # ── Profile-matched ──────────────────────────────────────────────────────
    "Quiet (Blue)":    ("001aff","0033ff","004cff","0033ff"),
    "Performance (Red)":("ff0000","ff0000","ff0000","ff0000"),
    "Custom (Pink)":   ("ff69b4","ff69b4","ff69b4","ff69b4"),
    # ── Special ──────────────────────────────────────────────────────────────
    "Rainbow":         ("ff0000","ff8800","0044ff","aa00ff"),
    "Stealth":         ("111111","111111","111111","111111"),
    "Off":             ("000000","000000","000000","000000"),
}

# Detect actual profile names from the kernel (low-power vs quiet)
def _detect_profiles():
    return ["quiet", "balanced", "performance", "custom"]

PROFILES       = _detect_profiles()

# UI labels — "low-power" is the sysfs name but user always sees "Quiet"
PROFILE_LABELS = {
    "quiet":       "Quiet",
    "balanced":    "Balanced",
    "performance": "Performance",
    "custom":      "Custom",
}
PROFILE_ICONS = {
    "quiet":       "🔵",
    "balanced":    "⚪",
    "performance": "🔴",
    "custom":      "🩷",
}
PROFILE_DESCS = {
    "quiet":       "15W · Boost OFF",
    "balanced":    "35W · Boost ON",
    "performance": "54W · Boost ON",
    "custom":      "54W · Custom Config",
}
PROFILE_COLORS = {
    "quiet":       "#4a9eff",
    "balanced":    "#d0d0d0",
    "performance": "#ff4757",
    "custom":      "#ff69b4",
}

# ── Power Mode Preset Values ──────────────────────────────────────────────────
# Applied when switching FROM Custom TO a standard power mode.
# These match the firmware defaults per WMI capability data.
POWERMODE_QUIET = {"pl1": 30, "pl2": 45, "tau": 56, "crossload": 25, "cpu_temp": 94,
                   "ctgp": 45, "ppab": 10, "total_proc": 25, "gpu_temp": 87}
POWERMODE_BALANCED = {"pl1": 45, "pl2": 65, "tau": 56, "crossload": 30, "cpu_temp": 94,
                      "ctgp": 45, "ppab": 15, "total_proc": 30, "gpu_temp": 87}
POWERMODE_PERFORMANCE = {"pl1": 55, "pl2": 80, "tau": 56, "crossload": 30, "cpu_temp": 94,
                         "ctgp": 50, "ppab": 15, "total_proc": 30, "gpu_temp": 87}

POWERMODE_PRESETS = {
    "quiet": POWERMODE_QUIET,
    "balanced": POWERMODE_BALANCED,
    "performance": POWERMODE_PERFORMANCE,
}

# "Reset CPU OC" button targets — P-core / E-core default max clocks
PCORE_RESET_MHZ = 4600
ECORE_RESET_MHZ = 4100

# Flat grey style applied to sliders when locked (no colored handle / no box)
DISABLED_SLIDER_STYLE = (
    "QSlider::groove:horizontal{background:#242424;height:6px;border-radius:3px;}"
    "QSlider::handle:horizontal{background:#5a5a5a;width:16px;height:16px;border-radius:8px;margin:-5px 0;}"
    "QSlider::sub-page:horizontal{background:#333333;border-radius:3px;}"
)

# How often (seconds) the background watcher polls the powermode sysfs.
# Only fires on an actual mode change, so it never fights user edits.
POWERMODE_POLL_INTERVAL = 0.25

# Keyboard brightness poll interval (seconds) — detects Fn+Space quickly without lag.
KEYBOARD_POLL_INTERVAL = 0.25

# ── Hardware bounds (mirror the LOQ_* #defines in legion-laptop.c) ────────────
# Source of truth is the kernel module; GUI ranges must track these so a kernel
# clamp (e.g. TAU 19→20) and the UI never disagree.
CPU_PL1_MIN_WATTS        = 25
CPU_PL1_MAX_WATTS        = 60
CPU_PL2_MIN_WATTS        = 40
CPU_PL2_MAX_WATTS        = 85
CPU_TAU_MIN_SECS         = 20
CPU_TAU_MAX_SECS         = 160
CPU_CROSSLOAD_MIN_WATTS  = 20
CPU_CROSSLOAD_MAX_WATTS  = 30
CPU_TEMP_MIN_CELSIUS     = 85
CPU_TEMP_MAX_CELSIUS     = 100
GPU_PPAB_MIN_WATTS       = 0
GPU_PPAB_MAX_WATTS       = 15
GPU_PPAB_STEP_WATTS      = 5
GPU_CTGP_MIN_WATTS       = 35
GPU_CTGP_MAX_WATTS       = 50
GPU_CTGP_STEP_WATTS      = 5
GPU_TOTAL_PROC_MIN_WATTS = 10
GPU_TOTAL_PROC_MAX_WATTS = 45
GPU_TOTAL_PROC_STEP_WATTS = 5
GPU_TEMP_MIN_CELSIUS     = 75
GPU_TEMP_MAX_CELSIUS     = 87
# CPU frequency bounds (silicon datasheet range)
CPU_FREQ_MIN_MHZ  = 800
CPU_FREQ_MAX_MHZ  = 5000
ECORE_FREQ_MIN_MHZ = 400
ECORE_FREQ_MAX_MHZ = 5000
# nvidia-settings clock-offset bounds (controls are locked/non-functional on this model)
GPU_CORE_OFFSET_MIN_MHZ = -500
GPU_CORE_OFFSET_MAX_MHZ = 500
GPU_MEM_OFFSET_MIN_MHZ  = -1000
GPU_MEM_OFFSET_MAX_MHZ  = 2000
GPU_OFFSET_STEP_MHZ      = 50
# Fan-curve editor bounds (hwmon/legion_hwmon conventions)
FAN_TEMP_MIN_C = 30
FAN_TEMP_MAX_C = 95
PWM_MIN        = 0
PWM_MAX        = 255
FAN_RAMP_MIN   = 1
FAN_RAMP_MAX   = 10

# Qt's stylesheet engine (and its `url()`) does not reliably draw QSpinBox arrow
# glyphs on every theme/WM (caelestia + Hyprland + CachyOS included), and it
# silently suppresses the native arrow once a stylesheet targets the spinbox.
# PyQt6's QStyle.SubControl enum also omits SC_SpinBoxUp/Down, so subControlRect
# can't locate the buttons. We subclass QSpinBox and paint the triangles directly
# with QPainter from the widget geometry — theme/WM/version independent.
SPIN_BTN_W = 24  # must match the ::up-button/::down-button width in _spin()

class ArrowSpinBox(QSpinBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        r = self.rect()
        inset = 2  # border + small gap so the glyph clears the rounded corner
        x = r.right() - inset - SPIN_BTN_W
        half = (r.height() - 2 * inset) // 2
        up = QRect(x, r.top() + inset, SPIN_BTN_W, half)
        dn = QRect(x, r.top() + inset + half, SPIN_BTN_W, r.height() - 2 * inset - half)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_TEXT if self.isEnabled() else "#555555"))
        ArrowSpinBox._tri(p, up, True)
        ArrowSpinBox._tri(p, dn, False)
        p.end()

    @staticmethod
    def _tri(p, r, up):
        m = max(3, r.width() // 6)
        if up:
            pts = [QPointF(r.left()+m,   r.bottom()-m),
                   QPointF(r.right()-m,  r.bottom()-m),
                   QPointF(r.center().x(), r.top()+m)]
        else:
            pts = [QPointF(r.left()+m,   r.top()+m),
                   QPointF(r.right()-m,  r.top()+m),
                   QPointF(r.center().x(), r.bottom()-m)]
        p.drawPolygon(QPolygonF(pts))

EPP_VALUES = ["default","performance","balance_performance","balance_power","power"]
EPP_LABELS = {"default":"Default","performance":"Performance",
              "balance_performance":"Balance Performance",
              "balance_power":"Balance Power","power":"Power Save"}

_THEMES = {
    "dark": {
        "C_BG":      "#0d0d0d",
        "C_SIDEBAR": "#111111",
        "C_CARD":    "#181818",
        "C_CARD2":   "#222222",
        "C_BORDER":  "#2a2a2a",
        "C_TEXT":    "#e5e5e5",
        "C_TEXT2":   "#999999",
        "C_TEXT3":   "#666666",
        "C_HOVER":   "#1a1a1a",
        "C_ACTIVE":  "#252525",
        "C_SHADOW":  "#000000",
    },
    "dark_dimmed": {
        "C_BG":      "#151515",
        "C_SIDEBAR": "#1a1a1a",
        "C_CARD":    "#1e1e1e",
        "C_CARD2":   "#262626",
        "C_BORDER":  "#333333",
        "C_TEXT":    "#e0e0e0",
        "C_TEXT2":   "#999999",
        "C_TEXT3":   "#666666",
        "C_HOVER":   "#222222",
        "C_ACTIVE":  "#2d2d2d",
        "C_SHADOW":  "#000000",
    },
    "oled_black": {
        "C_BG":      "#000000",
        "C_SIDEBAR": "#050505",
        "C_CARD":    "#0a0a0a",
        "C_CARD2":   "#111111",
        "C_BORDER":  "#1a1a1a",
        "C_TEXT":    "#e0e0e0",
        "C_TEXT2":   "#888888",
        "C_TEXT3":   "#555555",
        "C_HOVER":   "#0f0f0f",
        "C_ACTIVE":  "#151515",
        "C_SHADOW":  "#000000",
    },
    "light": {
        "C_BG":      "#f5f5f5",
        "C_SIDEBAR": "#eaeaea",
        "C_CARD":    "#ffffff",
        "C_CARD2":   "#f0f0f0",
        "C_BORDER":  "#e0e0e0",
        "C_TEXT":    "#1a1a1a",
        "C_TEXT2":   "#666666",
        "C_TEXT3":   "#999999",
        "C_HOVER":   "#eeeeee",
        "C_ACTIVE":  "#e5e5e5",
        "C_SHADOW":  "#cccccc",
    },
}

def _load_theme_colours():
    global C_BG, C_SIDEBAR, C_CARD, C_CARD2, C_BORDER, C_TEXT, C_TEXT2, C_TEXT3
    global C_HOVER, C_ACTIVE, C_SHADOW
    try:
        cfg = json.loads(APP_CFG.read_text()) if APP_CFG.exists() else {}
        t = _THEMES.get(cfg.get("theme","dark"), _THEMES["dark"])
    except:
        t = _THEMES["dark"]
    C_BG     = t["C_BG"]
    C_SIDEBAR= t["C_SIDEBAR"]
    C_CARD   = t["C_CARD"]
    C_CARD2  = t["C_CARD2"]
    C_BORDER = t["C_BORDER"]
    C_TEXT   = t["C_TEXT"]
    C_TEXT2  = t["C_TEXT2"]
    C_TEXT3  = t["C_TEXT3"]
    C_HOVER  = t["C_HOVER"]
    C_ACTIVE = t["C_ACTIVE"]
    C_SHADOW = t["C_SHADOW"]

_load_theme_colours()

C_ACCENT = "#cc3333"
C_GREEN  = "#4ecb71"
C_BLUE   = "#4a9eff"
C_ORANGE = "#ffa724"
C_RED    = "#ff4757"
C_PURPLE = "#a855f7"
C_YELLOW = "#facc15"

# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════
def send_notif(title: str, body: str = "", icon: str = "computer"):
    try:
        subprocess.Popen(
            ["notify-send", "-a", "Legion Toolkit", "-i", icon,
             "-t", "3000", title, body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# DATA HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def rdsys(path, default="0"):
    try: return Path(path).read_text().strip()
    except: return default

def wrsys(path, value):
    """Write to sysfs — tries direct write, then pkexec fallback."""
    path = str(path)
    value = str(value)
    try:
        Path(path).write_text(value + "\n")
        return
    except Exception:
        pass
    try:
        v = value.replace("'","").replace(";","").replace("&","")
        subprocess.Popen(
            ["pkexec","sh","-c", f"echo '{v}' > {path}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

def apply_profile(name: str):
    """Apply power profile via LLL backend."""
    try:
        lll.apply_profile(name)
        return True, f"Profile set to {name}"
    except Exception as e:
        return False, str(e)[:80]

def find_hwmon(name):
    for base in [Path("/sys/class/hwmon"),Path("/sys/devices/virtual/hwmon")]:
        if not base.exists(): continue
        try:
            for p in base.iterdir():
                nf = p/"name"
                if nf.exists() and nf.read_text().strip() == name:
                    return p
        except: pass
    return None

# ── LLL (LenovoLegionLinux) Integration ───────────────────────────────────────────────
LLL_FANCURVE_DEBUGFS = Path("/sys/kernel/debug/legion/fancurve")
FAN_FULLSPEED = LEGION_SYS_BASEPATH / "fan_fullspeed"

def is_lll_module_loaded() -> bool:
    """Check if LLL kernel module is loaded."""
    return Path("/sys/module/legion_laptop").exists()

def is_lll_device_bound() -> bool:
    """Check if LLL device is bound (hwmon exposed)."""
    return find_hwmon("legion_hwmon") is not None

def get_lll_status() -> dict:
    """Get detailed LLL status for UI display."""
    status = {
        "module_loaded": is_lll_module_loaded(),
        "device_bound": is_lll_device_bound(),
        "debugfs_exists": LLL_FANCURVE_DEBUGFS.exists(),
        "has_fancurve": False,
    }
    if status["debugfs_exists"]:
        try:
            curve = LLL_FANCURVE_DEBUGFS.read_text()
            status["has_fancurve"] = "fan curve points size:" in curve
        except: pass
    return status

def is_lll_available() -> bool:
    """Full check: module loaded AND device bound."""
    return is_lll_module_loaded() and is_lll_device_bound()

def force_load_lll() -> tuple[bool, str]:
    """Try to force-load LLL module with force=1."""
    if not is_lll_module_loaded():
        try:
            r = subprocess.run(
                ["pkexec", "modprobe", "legion_laptop", "force=1"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                return True, "Module loaded with force=1"
            return False, r.stderr.strip()[:80]
        except Exception as e:
            return False, str(e)[:80]
    return is_lll_device_bound(), "Module already loaded, trying force..."

def get_ic_temp() -> int:
    """Get IC temperature from LLL hwmon (returns 0 if not available)."""
    h = find_hwmon("legion_hwmon")
    if h:
        for f in [h/"temp3_input", h/"temp4_input"]:
            if f.exists():
                try: return int(f.read_text())//1000
                except: pass
    return 0

def get_fan_status_message() -> str:
    if FAN_FULLSPEED.exists():
        return "✓  LLL fan control ready"
    return "⚠  fan_fullspeed not found"

def read_fancurve_from_hw() -> str | None:
    """Read current fan curve from LLL debugfs. Returns None if not available."""
    if LLL_FANCURVE_DEBUGFS.exists():
        try: return LLL_FANCURVE_DEBUGFS.read_text()
        except: pass
    return None

def write_fancurve_to_hw(points: list[dict]) -> tuple[bool, str]:
    """Write fan curve points to LLL hwmon. Each point: {fan1_pwm, fan2_pwm, cpu_temp, gpu_temp, ic_temp, accel, decel}"""
    hwmon = _fan_hwmon()
    if not hwmon:
        return False, "LLL hwmon not found"
    
    try:
        for i, pt in enumerate(points, 1):
            if i > 10:
                break
            base = f"pwm{1 if i <= 3 else 2}_auto_point{i}_"
            
            # Write PWM values (fan speed)
            if "fan1_pwm" in pt:
                subprocess.run(["pkexec", "sh", "-c", f"echo {pt['fan1_pwm']} > {hwmon/base}pwm"],
                             capture_output=True, timeout=2)
            if "fan2_pwm" in pt:
                other = "pwm2_auto_point" if i <= 3 else "pwm1_auto_point"
                idx = i if i <= 3 else i - 3
                subprocess.run(["pkexec", "sh", "-c", f"echo {pt['fan2_pwm']} > {hwmon}{other}{idx}_pwm"],
                             capture_output=True, timeout=2)
            
            # Write temperature thresholds
            if "cpu_temp" in pt:
                subprocess.run(["pkexec", "sh", "-c", f"echo {pt['cpu_temp']} > {hwmon/base}temp"],
                             capture_output=True, timeout=2)
            
            # Write acceleration/deceleration
            if "accel" in pt:
                subprocess.run(["pkexec", "sh", "-c", f"echo {pt['accel']} > {hwmon/base}accel"],
                             capture_output=True, timeout=2)
            if "decel" in pt:
                subprocess.run(["pkexec", "sh", "-c", f"echo {pt['decel']} > {hwmon/base}decel"],
                             capture_output=True, timeout=2)
        
        return True, f"Wrote {len(points)} fan curve points"
    except Exception as e:
        return False, str(e)[:80]

def save_fancurve_to_file(points: list[dict], filename: str) -> bool:
    """Save fan curve to JSON file."""
    try:
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        path = CFG_DIR / f"fancurve_{filename}.json"
        path.write_text(json.dumps(points, indent=2))
        return True
    except:
        return False

def load_fancurve_from_file(filename: str) -> list[dict] | None:
    """Load fan curve from JSON file."""
    try:
        path = CFG_DIR / f"fancurve_{filename}.json"
        if path.exists():
            return json.loads(path.read_text())
    except:
        pass
    return None

def parse_fancurve(curve_text: str) -> list[dict]:
    """Parse fancurve debugfs output into list of point dicts."""
    lines = curve_text.strip().split("\n")
    if not lines or "fan curve points size:" not in curve_text:
        return []
    points = []
    header = lines[0].split("|")
    for line in lines[2:]:
        if not line.strip(): continue
        vals = line.split()
        if len(vals) >= 12:
            points.append({
                "speed_unit": int(vals[0]),
                "fan1_rpm": int(vals[1]) * 100 if vals[0] == "3" else 0,
                "fan2_rpm": int(vals[2]) * 100 if vals[0] == "3" else 0,
                "fan1_pwm": int(vals[3]),
                "fan2_pwm": int(vals[4]),
                "accel": int(vals[5]),
                "decel": int(vals[6]),
                "cpu_min": int(vals[7]),
                "cpu_max": int(vals[8]),
                "gpu_min": int(vals[9]),
                "gpu_max": int(vals[10]),
                "ic_min": int(vals[11]),
                "ic_max": int(vals[12]) if len(vals) > 12 else 127,
            })
    return points

def get_fan_lock_status() -> bool:
    """Check if fan controller is locked (read-only, firmware level)."""
    lock_path = LEGION_SYS_BASEPATH / "lockfancontroller"
    if not lock_path.exists():
        return False
    try:
        return lock_path.read_text().strip() == "1"
    except:
        return False

def set_fan_lock(lock: bool) -> tuple[bool, str]:
    """Lock/unlock fan controller. Requires LLL."""
    lock_path = LEGION_SYS_BASEPATH / "lockfancontroller"
    if not lock_path.exists():
        if not is_lll_available():
            return False, "LLL not loaded"
        return False, "lockfancontroller not found"
    try:
        val = "1" if lock else "0"
        r = subprocess.run(
            ["pkexec", "sh", "-c", f"echo {val} > {lock_path}"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            return True, f"Fan controller {'locked' if lock else 'unlocked'}"
        return False, r.stderr.strip()[:80]
    except Exception as e:
        return False, str(e)[:80]

def get_minifancurve_status() -> bool:
    """Check if mini fan curve (cold) is enabled."""
    mini_path = LEGION_SYS_BASEPATH / "minifancurve"
    if not mini_path.exists():
        return False
    try:
        return mini_path.read_text().strip() == "1"
    except:
        return False

def set_minifancurve(enable: bool) -> tuple[bool, str]:
    """Enable/disable mini fan curve when cold. Requires LLL."""
    mini_path = LEGION_SYS_BASEPATH / "minifancurve"
    if not mini_path.exists():
        if not is_lll_available():
            return False, "LLL not loaded"
        return False, "minifancurve not found"
    try:
        val = "1" if enable else "0"
        r = subprocess.run(
            ["pkexec", "sh", "-c", f"echo {val} > {mini_path}"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            return True, f"Mini fan curve {'enabled' if enable else 'disabled'}"
        return False, r.stderr.strip()[:80]
    except Exception as e:
        return False, str(e)[:80]

def set_max_fan_speed(enable: bool) -> tuple[bool, str]:
    """Set maximum fan speed (extreme cooling mode)."""
    if not FAN_FULLSPEED.exists():
        if not is_lll_available():
            return False, "LLL not loaded"
        return False, "fan_fullspeed path not found"
    try:
        val = "1" if enable else "0"
        r = subprocess.run(
            ["pkexec", "sh", "-c", f"echo {val} > {FAN_FULLSPEED}"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            return True, f"Max fan {'ON' if enable else 'OFF'}"
        return False, r.stderr.strip()[:80]
    except Exception as e:
        return False, str(e)[:80]

def get_cpu_temp():
    h = find_hwmon("k10temp")
    if h:
        for f in sorted(h.glob("temp*_input")):
            try: return int(f.read_text())//1000
            except: pass
    return 0

def get_fan_rpm():
    h = find_hwmon("legion_hwmon"); fans = []
    if h:
        for f in sorted(h.glob("fan*_input")):
            try: fans.append(int(f.read_text()))
            except: pass
    while len(fans) < 2: fans.append(0)
    return fans[0], fans[1]

def get_cpu_freq_ghz():
    try:
        return round(int(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
                         .read_text()) / 1_000_000, 2)
    except: return 0.0

def get_cpu_max_freq_mhz():
    """Max allowed frequency in MHz (scaling_max_freq)."""
    try:
        return int(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq")
                   .read_text()) // 1000
    except: return 0

def get_cpu_hw_max_mhz():
    """Hardware max frequency in MHz — P-core turbo ceiling."""
    return get_pcore_hw_max_mhz()

def get_cpu_power_w():
    """
    NOT called directly — use DataSampler which tracks RAPL energy delta.
    This is kept as a helper for finding the energy file.
    """
    return None   # handled by _read_cpu_power_delta in DataSampler

def _find_rapl_energy_file():
    """Find AMD RAPL package energy file. Returns Path or None."""
    try:
        pc = Path("/sys/class/powercap")
        if pc.exists():
            for p in sorted(pc.iterdir()):
                try:
                    name = (p/"name").read_text().strip().lower()
                    if "package" in name or "psys" in name:
                        ef = p/"energy_uj"
                        if ef.exists(): return ef
                except: pass
    except: pass
    # AMD hwmon fallback
    h = find_hwmon("k10temp")
    if h:
        for f in h.glob("power*_input"):
            return f   # already in µW, not cumulative
    return None

def get_igpu_power_w():
    """AMD iGPU power via amdgpu hwmon or apu_power in k10temp."""
    # Try amdgpu hwmon
    h = find_hwmon("amdgpu")
    if h:
        for f in h.glob("power*_input"):
            try: return round(int(f.read_text()) / 1_000_000, 1)
            except: pass
    # Try k10temp APU power (some AMD mobile CPUs expose this)
    h2 = find_hwmon("k10temp")
    if h2:
        for f in h2.glob("power*_input"):
            try: return round(int(f.read_text()) / 1_000_000, 1)
            except: pass
    return None

def get_ram_info():
    """
    Returns (used_mb, total_mb, pct).
    Uses MemTotal - MemAvailable — the kernel's own best estimate of
    used memory, matching what htop/free shows as 'used'.
    """
    try:
        d = {}
        with open("/proc/meminfo") as f:
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    d[k.strip()] = int(v.strip().split()[0])
        total     = d.get("MemTotal", 0)
        available = d.get("MemAvailable", 0)
        used      = max(0, total - available)
        pct       = int(used * 100 / max(total, 1))
        return used // 1024, total // 1024, pct
    except: return 0, 0, 0

def get_battery_pct():
    try:
        n = int(rdsys(BAT/"energy_now"))
        f = int(rdsys(BAT/"energy_full", "1"))
        return min(100, int(n * 100 / f))
    except: return 0

def get_battery_status(): return rdsys(BAT/"status", "Unknown")

def get_battery_health():
    try:
        f = int(rdsys(BAT/"energy_full","1"))
        d = int(rdsys(BAT/"energy_full_design","1"))
        return min(100, int(f*100/d))
    except: return 0

def get_battery_stats():
    s = {}
    s["percent"] = get_battery_pct()
    s["status"]  = get_battery_status()
    s["health"]  = get_battery_health()
    s["cycles"]  = rdsys(BAT/"cycle_count","—")

    # ── Battery temperature — exhaustive scan ────────────────────────────────
    _bat_temp = None

    # 1. Direct BAT sysfs (some kernels expose this)
    for bat_path in [BAT, Path("/sys/class/power_supply/BAT1"),
                     Path("/sys/class/power_supply/CMB0")]:
        for fname in ["temp", "temp_now"]:
            try:
                v = int((bat_path/fname).read_text().strip())
                if v > 0:
                    # Values can be in tenths of °C (273→27) or milli-°C
                    _bat_temp = v // 10 if v > 1000 else v
                    break
            except: pass
        if _bat_temp is not None: break

    # 2. power_supply device symlink — real device path often has temp
    if _bat_temp is None:
        try:
            real = Path("/sys/class/power_supply/BAT0").resolve()
            for fname in ["temp", "temp_now", "uevent"]:
                p = real / fname
                if fname == "uevent" and p.exists():
                    # parse POWER_SUPPLY_TEMP= from uevent
                    for line in p.read_text().splitlines():
                        if "TEMP=" in line:
                            try:
                                v = int(line.split("=")[1].strip())
                                if v > 0:
                                    _bat_temp = v // 10 if v > 1000 else v
                            except: pass
                elif p.exists():
                    try:
                        v = int(p.read_text().strip())
                        if v > 0:
                            _bat_temp = v // 10 if v > 1000 else v
                            break
                    except: pass
        except: pass

    # 3. hwmon scan — look for battery/acpi named hwmon devices
    if _bat_temp is None:
        try:
            for hwmon in sorted(Path("/sys/class/hwmon").iterdir()):
                try:
                    name = (hwmon/"name").read_text().strip().lower()
                except: name = ""
                if not any(k in name for k in
                           ("bat","acpi","power","bq","max","lenovo","smbus")):
                    continue
                for f in sorted(hwmon.glob("temp*_input")):
                    try:
                        v = int(f.read_text().strip()) // 1000
                        if 10 < v < 80:
                            _bat_temp = v; break
                    except: pass
                if _bat_temp is not None: break
        except: pass

    # 4. Scan ALL hwmon for a temp in battery range (20–55°C realistic)
    if _bat_temp is None:
        try:
            for hwmon in sorted(Path("/sys/class/hwmon").iterdir()):
                try: name = (hwmon/"name").read_text().strip().lower()
                except: name = ""
                # Skip CPU/GPU hwmon — not battery temps
                if any(k in name for k in ("k10temp","coretemp","nct","asus",
                                           "it8","gpu","nouveau","radeon","amdgpu")):
                    continue
                for f in sorted(hwmon.glob("temp*_input")):
                    try:
                        v = int(f.read_text().strip()) // 1000
                        if 20 < v < 55:  # realistic battery temp range
                            _bat_temp = v; break
                    except: pass
                if _bat_temp is not None: break
        except: pass

    # 5. ACPI thermal zone — last resort
    if _bat_temp is None:
        try:
            for tz in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
                try:
                    ttype = (tz/"type").read_text().strip().lower()
                    if any(k in ttype for k in ("bat","acpi","charger")):
                        v = int((tz/"temp").read_text().strip()) // 1000
                        if 10 < v < 80:
                            _bat_temp = v; break
                except: pass
        except: pass

    s["temp"] = f"{_bat_temp} °C" if _bat_temp is not None else "—"

    try: s["power"] = f"{int(rdsys(BAT/'power_now','0'))/1_000_000:.1f} W"
    except: s["power"] = "—"
    try: s["voltage"] = f"{int(rdsys(BAT/'voltage_now','0'))/1_000_000:.2f} V"
    except: s["voltage"] = "—"
    try:
        ef = int(rdsys(BAT/"energy_full","0"))
        ed = int(rdsys(BAT/"energy_full_design","0"))
        s["capacity"] = f"{ef//1000} mWh / {ed//1000} mWh (design)"
    except: s["capacity"] = "—"
    s["manufacturer"] = rdsys(BAT/"manufacturer","—")
    s["model"]        = rdsys(BAT/"model_name","—")
    s["technology"]   = rdsys(BAT/"technology","—")
    return s

def get_epp():
    try:
        return Path("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference") \
               .read_text().strip()
    except: return "default"

def set_epp(val):
    paths = [
        f"/sys/devices/system/cpu/cpu{i}/cpufreq/energy_performance_preference"
        for i in range(32)
        if Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/energy_performance_preference").exists()
    ]
    if paths:
        cmd = " && ".join(f"echo {val} > {p}" for p in paths)
        subprocess.Popen(["pkexec","sh","-c",cmd],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_governor():
    try:
        return Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()
    except: return "—"

def get_ac_connected():
    return lll.get_ac_connected()

def get_ai_engine():
    """Return '1'/'0' for AI Engine state, or None if unavailable."""
    if AI_ENGINE:
        return rdsys(AI_ENGINE, "0")
    return None

def set_ai_engine(enabled: bool):
    if AI_ENGINE:
        wrsys(AI_ENGINE, "1" if enabled else "0")
        return True
    # Fallback: use EPP balance_performance
    if enabled:
        set_epp("balance_performance")
    else:
        set_epp("default")
    return False   # not native, EPP fallback

# ── GPU via nvidia-smi ────────────────────────────────────────────────────────
_gpu_cache  = {}
_gpu_last   = 0.0
_GPU_LOCK   = threading.Lock()

def get_gpu_info():
    global _gpu_cache, _gpu_last
    with _GPU_LOCK:
        now = time.time()
        if now - _gpu_last < 1.4:
            return _gpu_cache
        try:
            out = subprocess.check_output(
                ["nvidia-smi",
                 "--query-gpu=utilization.gpu,temperature.gpu,clocks.current.graphics,"
                 "memory.used,memory.total,pstate,power.draw,name",
                 "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL, text=True, timeout=2
            ).strip().split(",")
            if len(out) >= 8:
                _gpu_cache = {
                    "util":      int(out[0].strip()),
                    "temp":      int(out[1].strip()),
                    "freq":      int(out[2].strip()),
                    "mem_used":  int(out[3].strip()),
                    "mem_total": int(out[4].strip()),
                    "pstate":    out[5].strip(),
                    "power":     float(out[6].strip()),
                    "name":      out[7].strip(),
                    "available": True,
                }
                _gpu_last = now
                return _gpu_cache
        except: pass
        _gpu_cache = {"available": False}
        _gpu_last  = now
        return _gpu_cache

# ── Display / VRR / Refresh Rate (compositor-aware) ──────────────────────────
#
# VRR and refresh-rate control differ per compositor, so this block detects the
# running compositor and dispatches to the right tool:
#   * KDE Plasma 6 (Wayland/X11)  → kscreen-doctor + kwriteconfig6 (KWin)
#   * Hyprland (wlroots/Wayland)  → hyprctl
#   * GNOME (Wayland)             → gsettings org.gnome.mutter experimental-features
#   * other                       → unsupported (callers degrade gracefully)
# This keeps the toolkit usable on any DE instead of being hard-wired to KDE.

def _detect_compositor():
    """Return 'kde' | 'hyprland' | 'gnome' | 'x11-other' | 'other'."""
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()
    on_wayland = "WAYLAND_DISPLAY" in os.environ
    if "kde" in desktop or "plasma" in desktop:
        return "kde"
    if "hyprland" in desktop:
        return "hyprland"
    if "gnome" in desktop:
        return "gnome"
    if not on_wayland and ("xfce" in desktop or "x-cinnamon" in desktop or "mate" in desktop):
        return "x11-other"
    return "other"


def vrr_supported():
    """True if a VRR control path exists for the current compositor."""
    c = _detect_compositor()
    if c in ("kde", "hyprland", "gnome"):
        return True
    # last-resort: a known tool is installed even if DE wasn't recognised
    return bool(shutil.which("kscreen-doctor") or shutil.which("hyprctl"))


# ── KDE (kscreen-doctor / KWin) ──────────────────────────────────────────────
def _kscreen_json():
    """Return parsed kscreen-doctor JSON, or {}."""
    try:
        out = subprocess.check_output(
            ["kscreen-doctor", "-j"], stderr=subprocess.DEVNULL, text=True, timeout=3
        )
        return json.loads(out)
    except Exception:
        return {}


def _kscreen_output_idx(name: str) -> int:
    """Return 1-based output index for kscreen-doctor output.N commands."""
    try:
        data = _kscreen_json()
        for i, o in enumerate(data.get("outputs", []), 1):
            if o.get("name", "") == name:
                return i
    except Exception:
        pass
    return 1


def _persist_vrr(output_name: str, policy: int):
    """Persist VRR policy into kscreen config files so it survives reboot (KDE)."""
    kscreen_dir = Path.home() / ".local/share/kscreen"
    if not kscreen_dir.exists():
        return
    try:
        for cfg_file in kscreen_dir.glob("*"):
            if cfg_file.is_dir():
                continue
            try:
                data = json.loads(cfg_file.read_text())
                for o in data.get("outputs", []):
                    if o.get("name", "") == output_name:
                        o["vrrpolicy"] = policy
                cfg_file.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
    except Exception:
        pass


def _configure_kwin_vrr(enabled: bool):
    """Set KWin compositor VRR policy via kwriteconfig6 (KDE)."""
    try:
        policy = "1" if enabled else "0"
        subprocess.run(
            ["kwriteconfig6", "--file", "kwinrc", "--group", "Compositing",
             "--key", "VRRPolicy", policy],
            timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(
            ["qdbus6", "org.kde.KWin", "/Compositor",
             "org.kde.kwin.Compositing.resume"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(
            ["dbus-send", "--session", "--dest=org.kde.KWin", "--type=method_call",
             "/KWin", "org.kde.KWin.reconfigure"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


# ── Hyprland (hyprctl) ───────────────────────────────────────────────────────
def _hypr_monitors_json():
    try:
        out = subprocess.check_output(
            ["hyprctl", "-j", "monitors"], stderr=subprocess.DEVNULL, text=True, timeout=3
        )
        return json.loads(out)
    except Exception:
        return []


def _hyprctl(args):
    try:
        subprocess.run(["hyprctl", *args], timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ── GNOME (gsettings) ────────────────────────────────────────────────────────
def _gnome_vrr_enabled():
    try:
        out = subprocess.check_output(
            ["gsettings", "get", "org.gnome.mutter", "experimental-features"],
            stderr=subprocess.DEVNULL, text=True, timeout=3)
        return "variable-refresh-rate" in out
    except Exception:
        return False


def _gnome_set_vrr(enabled: bool):
    try:
        cur = subprocess.check_output(
            ["gsettings", "get", "org.gnome.mutter", "experimental-features"],
            stderr=subprocess.DEVNULL, text=True, timeout=3).strip()
        feats = []
        try:
            if cur.startswith("@as"):
                feats = json.loads(cur.split(None, 1)[1])
            elif cur.startswith("["):
                feats = json.loads(cur)
        except Exception:
            feats = []
        feats = [f for f in feats if f != "variable-refresh-rate"]
        if enabled:
            feats.append("variable-refresh-rate")
        arg = "[" + ", ".join(f"'{f}'" for f in feats) + "]" if feats else "[]"
        subprocess.run(
            ["gsettings", "set", "org.gnome.mutter", "experimental-features", arg],
            timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ── Unified public API ───────────────────────────────────────────────────────
def get_display_outputs():
    """
    Return list of (output_name, current_mode_str, modes_list).
    modes_list = [(mode_str, is_current), ...]  mode_str = 'WxH@HZ'
    """
    comp = _detect_compositor()
    outputs = []
    try:
        if comp == "kde":
            data = _kscreen_json()
            for o in data.get("outputs", []):
                if not o.get("enabled"):
                    continue
                name = o.get("name", "")
                cur_id = o.get("currentModeId", "")
                modes, cur_mode = [], ""
                for m in o.get("modes", []):
                    sz = m.get("size", {})
                    w, h = sz.get("width", 0), sz.get("height", 0)
                    hz = round(m.get("refreshRate", 0))
                    if not (w and h and hz):
                        continue
                    ms = f"{w}x{h}@{hz}"
                    if m.get("id") == cur_id:
                        cur_mode = ms
                    modes.append((ms, m.get("id") == cur_id))
                if modes:
                    outputs.append((name, cur_mode, modes))
        elif comp == "hyprland":
            for m in _hypr_monitors_json():
                name = m.get("name", "")
                cw, ch = m.get("width", 0), m.get("height", 0)
                chz = round(m.get("refreshRate", 0))
                cur = f"{cw}x{ch}@{chz}" if chz else ""
                seen, modes = set(), []
                for md in m.get("modes", []):
                    w, h = md.get("width", 0), md.get("height", 0)
                    hz = round(md.get("refreshRate", 0))
                    if not (w and h and hz):
                        continue
                    ms = f"{w}x{h}@{hz}"
                    if ms not in seen:
                        seen.add(ms)
                        modes.append((ms, ms == cur))
                if modes:
                    outputs.append((name, cur, modes))
        # gnome / other: no reliable output enumeration from Python here
    except Exception:
        pass
    return outputs


def get_vrr_status():
    """
    Return (is_on, policy_int) for the first enabled output.
    policy: 0=never 1=automatic 2=always
    """
    comp = _detect_compositor()
    try:
        if comp == "kde":
            data = _kscreen_json()
            for o in data.get("outputs", []):
                if o.get("enabled"):
                    vrr = o.get("vrrpolicy", 0)
                    return vrr in (1, 2), vrr
            return False, 0
        if comp == "hyprland":
            out = subprocess.check_output(
                ["hyprctl", "-j", "getoption", "misc:vrr"],
                stderr=subprocess.DEVNULL, text=True, timeout=3)
            val = int(json.loads(out).get("int", 0))
            return val in (1, 2), val
        if comp == "gnome":
            on = _gnome_vrr_enabled()
            return on, (2 if on else 0)
    except Exception:
        pass
    return False, 0


def set_vrr(enabled: bool, output_name: str = ""):
    """
    Enable/disable VRR/FreeSync on the current compositor.
    KDE: kscreen-doctor + kwriteconfig6 + kscreen config persist.
    Hyprland: hyprctl keyword misc:vrr (0=off 1=automatic 2=always).
    GNOME: gsettings org.gnome.mutter experimental-features.
    """
    comp = _detect_compositor()
    label = "Automatic" if enabled else "Never"
    try:
        if comp == "kde":
            data = _kscreen_json()
            targets = ([o for o in data.get("outputs", [])
                        if o.get("name", "") == output_name] if output_name
                       else [o for o in data.get("outputs", []) if o.get("enabled")])
            if not targets:
                targets = data.get("outputs", [])
            for o in targets:
                name = o.get("name", "")
                idx = _kscreen_output_idx(name)
                subprocess.run(["kscreen-doctor", f"output.{idx}.vrrpolicy.{'automatic' if enabled else 'never'}"],
                                capture_output=True, text=True, timeout=5)
                _persist_vrr(name, 2 if enabled else 0)
            _configure_kwin_vrr(enabled)
        elif comp == "hyprland":
            _hyprctl(["keyword", "misc:vrr", "1" if enabled else "0"])
        elif comp == "gnome":
            _gnome_set_vrr(enabled)
        else:
            send_notif("VRR not supported on this compositor",
                       "VRR is supported on: KDE Plasma, Hyprland, GNOME.",
                       "dialog-error")
            return
        if enabled:
            _ensure_nvidia_modeset()
        send_notif("VRR / FreeSync", f"Adaptive sync → {label}", "display")
    except Exception as e:
        send_notif("VRR Error", str(e), "dialog-error")


def set_refresh_rate(output: str, mode: str):
    """
    Set display mode. mode = 'WxH@HZ'.
    KDE: kscreen-doctor. Hyprland: hyprctl keyword monitor.
    """
    comp = _detect_compositor()
    try:
        if comp == "kde":
            data = _kscreen_json()
            mode_id = None
            for o in data.get("outputs", []):
                if o.get("name", "") == output:
                    res_part, hz_part = mode.split("@")
                    w, h, hz = (int(x) for x in (res_part.split("x") + [hz_part]))
                    for m in o.get("modes", []):
                        sz = m.get("size", {})
                        if sz.get("width") == w and sz.get("height") == h \
                                and round(m.get("refreshRate", 0)) == hz:
                            mode_id = m.get("id", "")
                            break
                    break
            idx = _kscreen_output_idx(output)
            subprocess.Popen(
                ["kscreen-doctor",
                 f"output.{idx}.mode.{mode_id}" if mode_id else f"output.{idx}.mode.{mode}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif comp == "hyprland":
            _hyprctl(["keyword", "monitor", f"{output},{mode},auto"])
        else:
            send_notif("Refresh rate not supported on this compositor",
                       "Refresh-rate control is supported on: KDE Plasma, Hyprland.",
                       "dialog-error")
            return
        send_notif("Refresh Rate Changed", f"{output}: {mode.replace('@', ' @ ')} Hz", "display")
    except Exception as e:
        send_notif("Refresh Rate Error", str(e), "dialog-error")

# ── RGB Keyboard — via legionaura CLI ─────────────────────────────────────────
# legionaura (AUR: legionaura) wraps the USB HID protocol for Legion keyboards.
# Install: yay -S legionaura
# CLI: legionaura static|breath|wave|hue|off [colors] [--speed 1-4] [--brightness 1-2]

_KBD_BRI_PATH = Path("/sys/class/leds/platform::kbd_backlight/brightness")
_KBD_BRI_MAX  = Path("/sys/class/leds/platform::kbd_backlight/max_brightness")

def _has_legionaura() -> bool:
    try:
        r = subprocess.run(["which","legionaura"], capture_output=True, timeout=2)
        return r.returncode == 0
    except Exception: return False

def _legionaura_version() -> str:
    try:
        r = subprocess.run(["legionaura","--version"], capture_output=True, text=True, timeout=2)
        return (r.stdout or r.stderr).strip().split("\n")[0][:40]
    except Exception: return "unknown"

def _write_sysfs(path: Path, value: str) -> bool:
    try:
        path.write_text(value + "\n"); return True
    except PermissionError: pass
    except Exception: return False
    try:
        import socket as _s
        c = _s.socket(_s.AF_UNIX, _s.SOCK_STREAM); c.settimeout(2.0)
        c.connect("/run/legion-toolkit.sock")
        c.send(f"write:{path}:{value}\n".encode())
        r = c.recv(32).decode().strip(); c.close()
        if r == "ok": return True
    except Exception: pass
    try:
        v = value.replace("'","").replace(";","").replace("&","")
        subprocess.run(["pkexec","sh","-c",f"printf '%s\\n' '{v}' > {path}"],
                       check=False, timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception: return False

def set_kbd_brightness(val: int):
    p = _KBD_BRI_PATH if _KBD_BRI_PATH.exists() else KBD_BACKLIGHT_PATH
    if p: _write_sysfs(p, str(val))

def get_kbd_brightness() -> int:
    p = _KBD_BRI_PATH if _KBD_BRI_PATH.exists() else KBD_BACKLIGHT_PATH
    try: return int(p.read_text().strip()) if p else 0
    except: return 0

def get_kbd_max_brightness() -> int:
    try: return int(_KBD_BRI_MAX.read_text().strip()) if _KBD_BRI_MAX.exists() else 2
    except: return 2

# ── Y-Logo and IO-Port LED (via LLL) ─────────────────────────────────────────
_YLOGO_PATH = Path("/sys/class/leds/platform::ylogo/brightness")
_IOPORT_PATH = Path("/sys/class/leds/platform::ioport/brightness")

def set_ylogo_brightness(brightness: int) -> tuple[bool, str]:
    """Set Y-logo LED brightness (0-2 or 0-100 depending on model). Requires LLL."""
    if not _YLOGO_PATH.exists():
        return False, "Y-logo LED not found"
    try:
        _YLOGO_PATH.write_text(str(brightness) + "\n")
        return True, f"Y-logo brightness: {brightness}"
    except PermissionError:
        try:
            subprocess.run(["pkexec", "sh", "-c", f"echo {brightness} > {_YLOGO_PATH}"],
                         capture_output=True, timeout=5)
            return True, f"Y-logo brightness: {brightness}"
        except Exception as e:
            return False, str(e)[:80]
    except Exception as e:
        return False, str(e)[:80]

def get_ylogo_brightness() -> int:
    """Get current Y-logo LED brightness."""
    if not _YLOGO_PATH.exists():
        return 0
    try:
        return int(_YLOGO_PATH.read_text().strip())
    except:
        return 0

def set_ioport_brightness(brightness: int) -> tuple[bool, str]:
    """Set IO-Port LED brightness. Requires LLL."""
    if not _IOPORT_PATH.exists():
        return False, "IO-Port LED not found"
    try:
        _IOPORT_PATH.write_text(str(brightness) + "\n")
        return True, f"IO-Port brightness: {brightness}"
    except PermissionError:
        try:
            subprocess.run(["pkexec", "sh", "-c", f"echo {brightness} > {_IOPORT_PATH}"],
                         capture_output=True, timeout=5)
            return True, f"IO-Port brightness: {brightness}"
        except Exception as e:
            return False, str(e)[:80]
    except Exception as e:
        return False, str(e)[:80]

def get_ioport_brightness() -> int:
    """Get current IO-Port LED brightness."""
    if not _IOPORT_PATH.exists():
        return 0
    try:
        return int(_IOPORT_PATH.read_text().strip())
    except:
        return 0

def run_legionaura(args: list, callback=None):
    """Run legionaura CLI in a background thread. callback(ok, msg) when done."""
    def _do():
        try:
            r = subprocess.run(
                ["legionaura"] + args,
                capture_output=True, text=True, timeout=8
            )
            ok  = r.returncode == 0
            msg = (r.stdout or r.stderr or "").strip()[:120]
            if not msg: msg = "OK" if ok else "failed (no output)"
        except FileNotFoundError:
            ok, msg = False, "legionaura not found — install: yay -S legionaura"
        except Exception as e:
            ok, msg = False, str(e)[:120]
        if callback: callback(ok, msg)
    threading.Thread(target=_do, daemon=True).start()

# ── Overclock helpers ─────────────────────────────────────────────────────────
def load_oc_config():
    try:
        if OC_CFG.exists():
            return json.loads(OC_CFG.read_text())
    except: pass
    hw_max = get_cpu_hw_max_mhz()
    ecore_max = get_ecore_hw_max_mhz()
    return {
        "cpu_max_freq_mhz": hw_max,
        "ecore_max_freq_mhz": ecore_max,
        "gpu_core_offset":  0,
        "gpu_mem_offset":   0,
        "gpu_power_limit":  0,
    }

def save_oc_config(data):
    try:
        OC_CFG.parent.mkdir(parents=True, exist_ok=True)
        OC_CFG.write_text(json.dumps(data, indent=2))
    except: pass

def _detect_cpu_clusters():
    """Detect P-core and E-core CPU indices and their hardware max frequencies.
    Returns (pcore_cpus, ecore_cpus, pcore_hw_max_mhz, ecore_hw_max_mhz)."""
    pcore_cpus, ecore_cpus = [], []
    pcore_hw_max, ecore_hw_max = 0, 0
    for i in range(32):
        path = Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq")
        if not path.exists():
            break
        try:
            max_freq = int(path.read_text()) // 1000
        except:
            continue
        if max_freq > pcore_hw_max:
            pcore_hw_max = max_freq
    for i in range(32):
        path = Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq")
        if not path.exists():
            break
        try:
            max_freq = int(path.read_text()) // 1000
        except:
            continue
        if max_freq >= pcore_hw_max:
            pcore_cpus.append(i)
        else:
            ecore_cpus.append(i)
            ecore_hw_max = max(ecore_hw_max, max_freq)
    return pcore_cpus, ecore_cpus, pcore_hw_max, ecore_hw_max

_PCORES, _ECORES, _PCORE_HW_MAX, _ECORE_HW_MAX = _detect_cpu_clusters()

def get_ecore_hw_max_mhz():
    return _ECORE_HW_MAX if _ECORE_HW_MAX > 0 else 3400

def get_pcore_hw_max_mhz():
    return _PCORE_HW_MAX if _PCORE_HW_MAX > 0 else 4600

def apply_cpu_freq(mhz: int):
    """Set scaling_max_freq for P-core CPUs only."""
    khz = mhz * 1000
    paths = [
        f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq"
        for i in _PCORES
        if Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq").exists()
    ]
    if paths:
        cmd = " && ".join(f"echo {khz} > {p}" for p in paths)
        subprocess.Popen(["pkexec","sh","-c",cmd],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        send_notif("P-Core Frequency Set", f"Max frequency: {mhz} MHz", "cpu")

def apply_ecore_freq(mhz: int):
    """Set scaling_max_freq for E-core CPUs only."""
    khz = mhz * 1000
    paths = [
        f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq"
        for i in _ECORES
        if Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq").exists()
    ]
    if paths:
        cmd = " && ".join(f"echo {khz} > {p}" for p in paths)
        subprocess.Popen(["pkexec","sh","-c",cmd],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        send_notif("E-Core Frequency Set", f"Max frequency: {mhz} MHz", "cpu")

def apply_gpu_oc(core_off: int, mem_off: int, power_limit: int):
    """Apply GPU overclock via nvidia-smi. Requires coolbits=28 in xorg."""
    cmds = []
    if core_off != 0:
        cmds.append(f"nvidia-smi --lock-gpu-clocks={core_off},{core_off}")
    if mem_off != 0:
        cmds.append(f"nvidia-smi --lock-memory-clocks={mem_off},{mem_off}")
    if power_limit > 0:
        cmds.append(f"nvidia-smi -pl {power_limit}")
    if cmds:
        for cmd in cmds:
            try:
                subprocess.Popen(cmd.split(),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
        send_notif("GPU Overclock Applied",
                   f"Core +{core_off} MHz | Mem +{mem_off} MHz | PL {power_limit}W",
                   "gpu")

def reset_gpu_oc():
    try:
        subprocess.Popen(["nvidia-smi","--reset-gpu-clocks"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(["nvidia-smi","--reset-memory-clocks"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        send_notif("GPU OC Reset", "Clock offsets cleared", "gpu")
    except: pass

# ── GPU overclock via nvidia-settings (offset mode, needs coolbits=28) ────────
def apply_gpu_oc_full(core_off: int, mem_off: int, power_limit_w: int,
                      temp_target: int = 0, fan_pct: int = 0):
    errors = []
    # 1. Power limit via nvidia-smi
    if power_limit_w > 0:
        try:
            r = subprocess.run(["nvidia-smi","-i","0","-pl",str(power_limit_w)],
                               capture_output=True, text=True, timeout=5)
            if r.returncode != 0: errors.append(f"PL: {r.stderr.strip()[:60]}")
        except Exception as e: errors.append(str(e))
    # 2. Clock offsets via nvidia-settings
    if core_off != 0:
        try:
            subprocess.Popen(
                ["nvidia-settings","-a",
                 f"[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels={core_off}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: errors.append("nvidia-settings not found")
    if mem_off != 0:
        try:
            subprocess.Popen(
                ["nvidia-settings","-a",
                 f"[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels={mem_off}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
    # 3. Temperature target
    if temp_target > 0:
        try:
            subprocess.Popen(["nvidia-smi","-i","0",
                               f"--gom={temp_target}"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
    # 4. Manual fan speed
    if fan_pct > 0:
        try:
            subprocess.Popen(
                ["nvidia-settings","-a","[gpu:0]/GPUFanControlState=1",
                 "-a",f"[fan:0]/GPUTargetFanSpeed={fan_pct}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
    msg = f"Core +{core_off} MHz | Mem +{mem_off} MHz | PL {power_limit_w}W"
    if errors: msg += f" ⚠ {errors[0]}"
    send_notif("GPU OC Applied", msg, "gpu")

def reset_gpu_oc_full():
    try:
        subprocess.Popen(["nvidia-smi","--reset-gpu-clocks"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(["nvidia-smi","--reset-memory-clocks"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try:
        subprocess.Popen(
            ["nvidia-settings","-a","[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels=0",
             "-a","[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels=0",
             "-a","[gpu:0]/GPUFanControlState=0"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    send_notif("GPU OC Reset", "All values reset to default", "gpu")

# ── CPU TDP via RAPL (writable PL1/PL2) ──────────────────────────────────────
def _rapl_power_paths():
    """Return (pl1_path, pl2_path) or (None, None)."""
    try:
        pc = Path("/sys/class/powercap")
        for p in sorted(pc.iterdir()):
            try:
                name = (p/"name").read_text().strip().lower()
                if "package" in name or "psys" in name or name.startswith("amd"):
                    pl1 = p/"constraint_0_power_limit_uw"
                    pl2 = p/"constraint_1_power_limit_uw"
                    if pl1.exists(): return pl1, pl2 if pl2.exists() else None
            except: pass
    except: pass
    return None, None

def set_cpu_tdp(pl1_w: int, pl2_w: int):
    """Set CPU TDP via legion sysfs or RAPL.
    Enforces: PL2 >= PL1 (firmware constraint).
    If PL1 > current PL2, both are set to PL1.
    If PL2 < current PL1, both are set to PL2.
    """
    from lib.lll_adapter import (get_cpu_longterm_powerlimit, get_cpu_shortterm_powerlimit,
                                  set_cpu_longterm_powerlimit, set_cpu_shortterm_powerlimit)
    cur_pl1 = get_cpu_longterm_powerlimit()
    cur_pl2 = get_cpu_shortterm_powerlimit()
    # Enforce PL2 >= PL1
    if pl1_w > pl2_w:
        pl2_w = pl1_w
    # If new PL1 > current PL2, raise PL2
    if cur_pl2 > 0 and pl1_w > cur_pl2:
        pl2_w = pl1_w
    # If new PL2 < current PL1, lower PL1
    if cur_pl1 > 0 and pl2_w < cur_pl1:
        pl1_w = pl2_w
    # Try legion sysfs first
    try:
        set_cpu_longterm_powerlimit(pl1_w)
        if pl2_w > 0:
            set_cpu_shortterm_powerlimit(pl2_w)
        send_notif("CPU TDP Set", f"PL1: {pl1_w}W  PL2: {pl2_w}W", "cpu")
        return
    except: pass
    # Fall back to RAPL
    pl1_path, pl2_path = _rapl_power_paths()
    if pl1_path:
        wrsys(pl1_path, str(pl1_w * 1_000_000))
    if pl2_path and pl2_w > 0:
        wrsys(pl2_path, str(pl2_w * 1_000_000))
    send_notif("CPU TDP Set", f"PL1: {pl1_w}W  PL2: {pl2_w}W", "cpu")

def get_cpu_tdp():
    """Return (pl1_w, pl2_w) or (0, 0)."""
    # Try legion sysfs first (cached values from EC)
    try:
        from lib.lll_adapter import get_cpu_longterm_powerlimit, get_cpu_shortterm_powerlimit
        pl1 = get_cpu_longterm_powerlimit()
        pl2 = get_cpu_shortterm_powerlimit()
        if pl1 > 0 or pl2 > 0:
            return pl1, pl2
    except: pass
    # Fall back to RAPL
    pl1_path, pl2_path = _rapl_power_paths()
    try:
        pl1 = int(rdsys(pl1_path, "0")) // 1_000_000 if pl1_path else 0
        pl2 = int(rdsys(pl2_path, "0")) // 1_000_000 if pl2_path else 0
        return pl1, pl2
    except: return 0, 0

def get_cpu_min_freq_mhz():
    try:
        return int(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq")
                   .read_text()) // 1000
    except: return 400

def apply_cpu_min_freq(mhz: int):
    khz = mhz * 1000
    paths = [f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_min_freq"
             for i in range(32)
             if Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_min_freq").exists()]
    if paths:
        cmd = " && ".join(f"echo {khz} > {p}" for p in paths)
        subprocess.Popen(["pkexec","sh","-c",cmd],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ── Fan control via legion_hwmon + FAN_FULLSPEED sysfs ────────────────────────
#
# Legion 5 15ACH6H fan control reality:
#   fan_fullspeed  → /sys/devices/.../PNP0C09:00/fan_fullspeed  (0/1) — always works
#   pwm1/pwm2      → legion_hwmon pwm files — may be writable on some driver versions
#   fan1_input/fan2_input → RPM read-only — always works
#
# Strategy:
#   Auto       → fan_fullspeed=0  (firmware controls fans via thermal curve)
#   Full Speed → fan_fullspeed=1  (locks both fans to 100%)
#   Manual     → try pwm via pkexec; if hwmon missing fall back to fan_fullspeed
#   Presets    → map to platform_profile + fan_fullspeed combinations

def _fan_hwmon():
    return find_hwmon("legion_hwmon")

def _fan_hwmon_info() -> dict:
    """Return dict of what the hwmon actually exposes."""
    h = _fan_hwmon()
    if not h:
        return {"found": False, "path": None,
                "pwm1": False, "pwm2": False,
                "pwm1_enable": False, "pwm2_enable": False}
    return {
        "found": True,
        "path": str(h),
        "pwm1":        (h/"pwm1").exists(),
        "pwm2":        (h/"pwm2").exists(),
        "pwm1_enable": (h/"pwm1_enable").exists(),
        "pwm2_enable": (h/"pwm2_enable").exists(),
    }

def get_fan_rpm():
    h = _fan_hwmon(); fans = []
    if h:
        for f in sorted(h.glob("fan*_input")):
            try: fans.append(int(f.read_text()))
            except: pass
    while len(fans) < 2: fans.append(0)
    return fans[0], fans[1]

def get_fan_pwm():
    h = _fan_hwmon()
    if not h: return 128, 128
    try: c = int((h/"pwm1").read_text())
    except: c = 0
    try: g = int((h/"pwm2").read_text())
    except: g = 0
    return c, g

def _write_fan_pwm(cpu_pct: int, gpu_pct: int) -> tuple:
    """
    Write PWM values as root via subprocess (avoids daemon socket path issues).
    Returns (ok: bool, msg: str).
    """
    h = _fan_hwmon()
    if not h:
        return False, "legion_hwmon not found"

    cpu_pwm = int(cpu_pct * 255 / 100)
    gpu_pwm = int(gpu_pct * 255 / 100)
    cmds = []

    pwm1_en = h / "pwm1_enable"
    pwm2_en = h / "pwm2_enable"
    pwm1    = h / "pwm1"
    pwm2    = h / "pwm2"

    if pwm1_en.exists(): cmds.append(f"echo 1 > {pwm1_en}")
    if pwm2_en.exists(): cmds.append(f"echo 1 > {pwm2_en}")
    if pwm1.exists():    cmds.append(f"echo {cpu_pwm} > {pwm1}")
    if pwm2.exists():    cmds.append(f"echo {gpu_pwm} > {pwm2}")

    if not cmds:
        return False, f"No writable pwm files in {h}"

    try:
        r = subprocess.run(
            ["pkexec", "sh", "-c", " && ".join(cmds)],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            return True, f"PWM set: CPU {cpu_pct}%  GPU {gpu_pct}%"
        else:
            return False, r.stderr.strip()[:100]
    except Exception as e:
        return False, str(e)[:100]

def _write_fan_auto() -> tuple:
    """Set fans back to automatic (pwm_enable=2) + clear fan_fullspeed."""
    cmds = []
    h = _fan_hwmon()
    if h:
        for f in ["pwm1_enable", "pwm2_enable"]:
            p = h / f
            if p.exists(): cmds.append(f"echo 2 > {p}")

    if FAN_FULLSPEED.exists():
        cmds.append(f"echo 0 > {FAN_FULLSPEED}")

    if not cmds:
        return False, "No fan control paths found"

    try:
        r = subprocess.run(
            ["pkexec", "sh", "-c", " && ".join(cmds)],
            capture_output=True, text=True, timeout=8
        )
        return r.returncode == 0, r.stderr.strip()[:80] if r.returncode != 0 else "Auto"
    except Exception as e:
        return False, str(e)[:80]

def _write_fan_fullspeed(on: bool) -> tuple:
    """Set fan_fullspeed 0 or 1 via pkexec."""
    if not FAN_FULLSPEED.exists():
        return False, f"fan_fullspeed not found at {FAN_FULLSPEED}"
    val = "1" if on else "0"
    try:
        r = subprocess.run(
            ["pkexec", "sh", "-c", f"echo {val} > {FAN_FULLSPEED}"],
            capture_output=True, text=True, timeout=8
        )
        return r.returncode == 0, r.stderr.strip()[:80] if r.returncode != 0 else ("Full speed ON" if on else "Full speed OFF")
    except Exception as e:
        return False, str(e)[:80]

# Keep these as sync wrappers for backwards compat (used elsewhere)
def set_fan_mode_auto():
    _write_fan_auto()

def set_fan_mode_manual(cpu_pct: int, gpu_pct: int):
    _write_fan_pwm(cpu_pct, gpu_pct)

def set_fan_fullspeed(on: bool):
    _write_fan_fullspeed(on)
    if on: _write_fan_pwm(100, 100)

# Fan presets
FAN_PRESETS = {
    "Quiet":       (20, 20),
    "Balanced":    (50, 50),
    "Performance": (75, 80),
    "Turbo":       (90, 95),
    "Full Speed":  (100, 100),
}

def load_fan_config():
    try:
        if FAN_CFG.exists():
            return json.loads(FAN_CFG.read_text())
    except: pass
    return {"mode": "auto", "cpu_pct": 50, "gpu_pct": 50, "preset": "Balanced"}

def save_fan_config(data):
    try:
        FAN_CFG.parent.mkdir(parents=True, exist_ok=True)
        FAN_CFG.write_text(json.dumps(data, indent=2))
    except: pass

# ── Appearance config ─────────────────────────────────────────────────────────
_ACCENT_OPTIONS = {
    "Legion Red":    "#cc3333",
    "Electric Blue": "#2979ff",
    "Neon Green":    "#00e676",
    "Amber":         "#ffa724",
    "Purple":        "#a855f7",
    "Pink":          "#ff69b4",
    "Cyan":          "#00bcd4",
}

def load_app_config():
    try:
        if APP_CFG.exists():
            return json.loads(APP_CFG.read_text())
    except: pass
    return {"accent": "#cc3333", "font_size": 12}

def save_app_config(data):
    try:
        APP_CFG.parent.mkdir(parents=True, exist_ok=True)
        APP_CFG.write_text(json.dumps(data, indent=2))
    except: pass

def load_actions():
    try:
        if ACTIONS_CFG.exists():
            return json.loads(ACTIONS_CFG.read_text())
    except: pass
    return {"on_ac":"performance","on_battery":"balanced","auto_switch":False,
            "_last_ac": None}

def save_actions(data):
    try:
        ACTIONS_CFG.parent.mkdir(parents=True, exist_ok=True)
        ACTIONS_CFG.write_text(json.dumps(data, indent=2))
    except: pass

def apply_actions_now():
    """Read actions config and apply profile if auto_switch is on."""
    try:
        cfg = load_actions()
        if not cfg.get("auto_switch"): return
        ac = get_ac_connected()
        target = cfg["on_ac"] if ac else cfg["on_battery"]
        current = lll.read_powermode()
        if target != current:
            apply_profile(target)
            send_notif("Auto Profile",
                       f"{'AC connected' if ac else 'On battery'} → {PROFILE_LABELS.get(target,target)}",
                       "battery-charging" if ac else "battery")
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND SAMPLER THREAD
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
        self._last_profile = None
        # RAPL delta tracking for CPU power
        self._rapl_file  = _find_rapl_energy_file()
        self._rapl_is_delta = (self._rapl_file and
                               "energy_uj" in str(self._rapl_file))
        self._rapl_last_uj = 0
        self._rapl_last_t  = 0.0
        # seed CPU stat
        try:
            with open("/proc/stat") as f:
                p = f.readline().split()
            self._last_idle  = int(p[4])
            self._last_total = sum(int(x) for x in p[1:])
        except: pass
        # seed RAPL
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
        """Return CPU package power in watts using RAPL energy delta."""
        if not self._rapl_file:
            return None
        try:
            now = time.monotonic()
            val = int(self._rapl_file.read_text())
            if self._rapl_is_delta:
                dt = now - self._rapl_last_t
                if dt > 0.05 and self._rapl_last_uj > 0:
                    delta_uj = val - self._rapl_last_uj
                    if delta_uj < 0:   # counter wraparound
                        delta_uj += 2**32
                    watts = round(delta_uj / dt / 1_000_000, 1)
                    self._rapl_last_uj = val
                    self._rapl_last_t  = now
                    return watts if 0 < watts < 200 else None
                self._rapl_last_uj = val
                self._rapl_last_t  = now
                return None
            else:
                # hwmon power*_input is already instantaneous µW
                return round(val / 1_000_000, 1)
        except: return None

    def run(self):
        _tick = 0
        while self._running:
            try:
                _tick += 1
                # Always sample — these are cheap reads
                util          = self._read_cpu_util()
                ac            = get_ac_connected()
                profile       = lll.read_powermode()
                if profile != self._last_profile and self._last_profile is not None:
                    lll.set_cpu_boost(profile in ("balanced", "performance"))
                self._last_profile = profile

                # Medium cost — every tick
                freq          = get_cpu_freq_ghz()
                temp          = get_cpu_temp()
                fan1, fan2    = get_fan_rpm()
                ic_temp      = get_ic_temp() if is_lll_available() else 0
                pct           = get_battery_pct()
                bat_status    = get_battery_status()

                # Slightly heavier — battery power
                try:
                    bat_power = f"{int(rdsys(BAT/'power_now','0'))/1_000_000:.1f} W"
                except: bat_power = "—"

                # CPU power via RAPL delta
                cpu_power = self._read_cpu_power()

                # Every 2 ticks — RAM, GPU, governor, EPP (slower changing)
                if _tick % 2 == 0 or _tick == 1:
                    ru, rt, rpct  = get_ram_info()
                    gpu           = get_gpu_info()
                    boost         = "1" if lll.get_cpu_boost() else "0"
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
                    # Use cached values
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

                # auto profile switch on AC change
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
# WIDGET PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════

class BarFill(QWidget):
    """Smooth animated progress bar."""
    def __init__(self, pct=0, color=None, parent=None):
        super().__init__(parent)
        self._pct   = float(max(0, min(100, pct)))
        self._color = color or C_ACCENT
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._anim = QPropertyAnimation(self, b"pct_prop", self)
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._user_toggled = False

    @pyqtProperty(float)
    def pct_prop(self): return self._pct
    @pct_prop.setter
    def pct_prop(self, v): self._pct = v; self.update()

    def set_pct(self, pct, color=None):
        target = float(max(0, min(100, pct)))
        if color: self._color = color
        if abs(target - self._pct) < 0.3:
            self._pct = target; self.update(); return
        self._anim.stop()
        self._anim.setStartValue(self._pct)
        self._anim.setEndValue(target)
        self._anim.start()

    def _bar_color(self, pct):
        if self._color != C_ACCENT: return QColor(self._color)
        if pct > 85: return QColor(C_RED)
        if pct > 65: return QColor(C_ORANGE)
        return QColor(C_ACCENT)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QBrush(QColor(C_BORDER))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 3, 3)
        fill = int(w * self._pct / 100)
        if fill > 0:
            p.setBrush(QBrush(self._bar_color(self._pct)))
            p.drawRoundedRect(0, 0, fill, h, 3, 3)
        p.end()


class StatRow(QWidget):
    def __init__(self, label, value_str="—", pct=0,
                 lbl_w=110, val_w=110, color=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        self._lbl = QLabel(label)
        self._lbl.setFixedWidth(lbl_w)
        self._lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;")
        lay.addWidget(self._lbl)
        self._bar = BarFill(pct, color)
        lay.addWidget(self._bar)
        self._val = QLabel(value_str)
        self._val.setFixedWidth(val_w)
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._val.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:600;")
        lay.addWidget(self._val)

    def update_value(self, value_str, pct, color=None):
        self._val.setText(value_str)
        self._bar.set_pct(pct, color)

    def set_value(self, value_str, pct=0, color=None, visible=True):
        self._val.setText(value_str)
        self._bar.set_pct(pct, color)
        self.setVisible(visible)


class InfoRow(QWidget):
    def __init__(self, label, value="—", lbl_w=180, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self); lay.setContentsMargins(0,4,0,4)
        lbl = QLabel(label); lbl.setFixedWidth(lbl_w)
        lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;")
        self._val = QLabel(value)
        self._val.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:500;")
        lay.addWidget(lbl); lay.addWidget(self._val); lay.addStretch()
    def set_value(self, v): self._val.setText(v)


# ══════════════════════════════════════════════════════════════════════════════
# FIRST-RUN WIZARD  (language selector + hardware detection)
# ══════════════════════════════════════════════════════════════════════════════
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QProgressBar, QListWidget, QListWidgetItem

class FirstRunWizard(QDialog):
    """
    Shown once on first launch.
    Page 0 → Language selection
    Page 1 → Hardware detection with progress
    Page 2 → Summary / done
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Legion Linux Toolkit — Setup")
        self.setFixedSize(560, 440)
        self.setWindowIcon(_legion_icon())
        self.setStyleSheet(f"""
            QDialog {{ background:{C_BG}; }}
            QLabel  {{ color:{C_TEXT}; background:transparent; }}
            QPushButton {{
                background:{C_CARD2}; color:{C_TEXT}; border:1px solid {C_BORDER};
                border-radius:8px; padding:10px 24px; font-size:13px;
            }}
            QPushButton:hover {{ background:{C_ACCENT}; color:#fff; border-color:{C_ACCENT}; }}
            QListWidget {{
                background:{C_CARD}; border:1px solid {C_BORDER};
                border-radius:10px; color:{C_TEXT}; font-size:13px;
            }}
            QListWidget::item:selected {{
                background:{C_ACCENT}; color:#fff; border-radius:6px;
            }}
            QListWidget::item:hover {{ background:{C_CARD2}; }}
        """)
        self._hw_result = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(32,28,32,24); root.setSpacing(0)

        # ── Logo + App name ───────────────────────────────────────────────────
        logo_row = QHBoxLayout()
        logo_lbl = QLabel()
        import base64 as _b64
        from PyQt6.QtGui import QPixmap as _QPixmap
        pm = _QPixmap(); pm.loadFromData(_b64.b64decode(_LEGION_ICON_B64))
        logo_lbl.setPixmap(pm.scaled(44, 52, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        logo_row.addWidget(logo_lbl)
        logo_row.addSpacing(14)
        app_name = QLabel("Legion Linux Toolkit")
        app_name.setStyleSheet(f"color:{C_TEXT};font-size:20px;font-weight:600;")
        logo_row.addWidget(app_name); logo_row.addStretch()
        root.addLayout(logo_row)
        root.addSpacing(20)

        # ── Stacked pages ─────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_lang())
        self._stack.addWidget(self._page_detect())
        self._stack.addWidget(self._page_done())
        root.addWidget(self._stack, 1)

        root.addSpacing(16)

        # ── Navigation buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._back_btn = QPushButton("← Back")
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn = QPushButton("Next →")
        self._next_btn.clicked.connect(self._go_next)
        self._next_btn.setStyleSheet(
            f"QPushButton{{background:{C_ACCENT};color:#fff;border:none;"
            f"border-radius:6px;padding:8px 24px;font-size:13px;font-weight:600;}}"
            f"QPushButton:hover{{background:#aa2222;}}"
        )
        btn_row.addWidget(self._back_btn); btn_row.addWidget(self._next_btn)
        root.addLayout(btn_row)

        # Page indicator dots
        self._dots = QHBoxLayout(); self._dots.setSpacing(6)
        self._dot_lbls = []
        for _ in range(3):
            d = QLabel("●"); d.setStyleSheet(f"color:{C_TEXT3};font-size:10px;")
            self._dot_lbls.append(d); self._dots.addWidget(d)
        self._dots.addStretch()
        root.addLayout(self._dots)
        self._update_dots(0)

    def _page_lang(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        title = QLabel("Choose Your Language")
        title.setStyleSheet(f"color:{C_TEXT};font-size:16px;font-weight:600;")
        desc = QLabel("Select the language for the interface.")
        desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;")
        lay.addWidget(title); lay.addWidget(desc); lay.addSpacing(8)

        self._lang_list = QListWidget()
        self._lang_list.setFixedHeight(220)
        # Pre-select saved or system language
        saved = _LANG
        sel_row = 0
        for i, (code, name) in enumerate(_LANG_NAMES.items()):
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            self._lang_list.addItem(item)
            if code == saved: sel_row = i
        self._lang_list.setCurrentRow(sel_row)
        self._lang_list.itemClicked.connect(self._on_lang_select)
        lay.addWidget(self._lang_list)
        return w

    def _page_detect(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        self._detect_title = QLabel("Hardware Detection")
        self._detect_title.setStyleSheet(f"color:{C_TEXT};font-size:16px;font-weight:600;")
        self._detect_desc = QLabel("Scanning your device for supported features.\nThis runs once and the result is saved.")
        self._detect_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;")
        self._detect_desc.setWordWrap(True)
        lay.addWidget(self._detect_title); lay.addWidget(self._detect_desc)
        lay.addSpacing(12)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(
            f"QProgressBar{{background:{C_BORDER};border-radius:3px;border:none;}}"
            f"QProgressBar::chunk{{background:{C_ACCENT};border-radius:3px;}}"
        )
        self._progress.hide()
        lay.addWidget(self._progress)

        self._detect_status = QLabel("")
        self._detect_status.setStyleSheet(f"color:{C_TEXT3};font-size:12px;font-family:monospace;")
        self._detect_status.setWordWrap(True)
        lay.addWidget(self._detect_status)
        lay.addStretch()
        return w

    def _page_done(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)
        done_title = QLabel("✓  Setup Complete")
        done_title.setStyleSheet(f"color:{C_GREEN};font-size:18px;font-weight:600;")
        done_desc = QLabel("Your hardware profile has been saved.\nThe dashboard is ready to use.")
        done_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;")
        done_desc.setWordWrap(True)
        lay.addWidget(done_title); lay.addWidget(done_desc); lay.addSpacing(8)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet(
            f"color:{C_TEXT2};font-size:12px;font-family:monospace;"
            f"background:{C_CARD};border-radius:8px;padding:12px;")
        self._summary_lbl.setWordWrap(True)
        lay.addWidget(self._summary_lbl)
        lay.addStretch()
        return w

    def _on_lang_select(self, item):
        code = item.data(Qt.ItemDataRole.UserRole)
        save_language(code)

    def _update_dots(self, page: int):
        for i, d in enumerate(self._dot_lbls):
            d.setStyleSheet(
                f"color:{C_ACCENT};font-size:10px;" if i == page
                else f"color:{C_TEXT3};font-size:10px;"
            )

    def _go_next(self):
        cur = self._stack.currentIndex()
        if cur == 0:
            # Save language from list
            item = self._lang_list.currentItem()
            if item:
                save_language(item.data(Qt.ItemDataRole.UserRole))
            self._stack.setCurrentIndex(1)
            self._back_btn.setVisible(True)
            self._update_dots(1)
            self._next_btn.setEnabled(False)
            self._next_btn.setText("Detecting…")
            # Run detection in background
            threading.Thread(target=self._run_detection, daemon=True).start()

        elif cur == 1:
            self._stack.setCurrentIndex(2)
            self._update_dots(2)
            self._next_btn.setText("Finish")

        elif cur == 2:
            self.accept()

    def _go_back(self):
        cur = self._stack.currentIndex()
        if cur > 0:
            self._stack.setCurrentIndex(cur - 1)
            self._update_dots(cur - 1)
            if cur - 1 == 0:
                self._back_btn.setVisible(False)
            self._next_btn.setText("Next →")
            self._next_btn.setEnabled(True)

    def _run_detection(self):
        """Called from worker thread."""
        from PyQt6.QtCore import QMetaObject, Q_ARG
        def upd(msg):
            QMetaObject.invokeMethod(self._detect_status, "setText",
                Qt.ConnectionType.QueuedConnection, Q_ARG(str, msg))

        QMetaObject.invokeMethod(self._progress, "show",
            Qt.ConnectionType.QueuedConnection)

        steps = [
            ("Reading DMI info…",           lambda: _dmi("product_name")),
            ("Checking power profiles…",    lambda: Path("/sys/firmware/acpi/platform_profile").exists()),
            ("Checking fan control…",       lambda: FAN_FULLSPEED.exists()),
            ("Checking battery paths…",     lambda: BAT.exists()),
            ("Checking backlight…",         lambda: any(Path("/sys/class/backlight").iterdir()) if Path("/sys/class/backlight").exists() else False),
            ("Checking ThinkPad features…", lambda: Path("/proc/acpi/ibm/fan").exists()),
            ("Checking Yoga hinge…",        lambda: Path("/sys/bus/platform/drivers/lenovo-ymc").exists()),
            ("Checking envycontrol…",       lambda: subprocess.run(["which","envycontrol"],capture_output=True).returncode==0),
            ("Checking legionaura…",        lambda: subprocess.run(["which","legionaura"],capture_output=True).returncode==0),
            ("Building capability map…",    lambda: detect_hardware()),
        ]

        lines = []
        cap = {}
        for msg, fn in steps:
            upd(msg)
            time.sleep(0.15)
            try:
                result = fn()
                if isinstance(result, dict):
                    cap = result
                status = "✓" if result else "—"
                lines.append(f"{status}  {msg.rstrip('…')}")
            except Exception as e:
                lines.append(f"✗  {msg.rstrip('…')}: {e}")

        if not cap:
            cap = detect_hardware()

        save_hardware(cap)
        FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
        FIRST_RUN_FLAG.touch()

        global HW
        HW = cap

        # Build summary
        brand = cap.get("brand","unknown").upper()
        model = cap.get("model","Unknown")
        feats = []
        if cap.get("platform_profile"): feats.append("Power Profiles")
        if cap.get("fan_fullspeed"):    feats.append("Fan Control")
        if cap.get("tp_charge_start"):  feats.append("ThinkPad Charge Thresholds")
        if cap.get("tp_fan_control"):   feats.append("ThinkPad Fan Levels")
        if cap.get("yoga_hinge"):       feats.append("Yoga Hinge Mode")
        if cap.get("legionaura"):       feats.append("RGB Keyboard (LegionAura)")
        if cap.get("envycontrol"):      feats.append("GPU Mode Switching")
        if cap.get("overdrive"):        feats.append("Display Overdrive")
        if cap.get("gsync"):            feats.append("G-Sync")
        if cap.get("nw_backlight"):    feats.append("Brightness Backlight")

        summary = f"Brand: {brand}\nModel: {model}\n\nDetected features:\n"
        summary += "\n".join(f"  ✓  {f}" for f in feats) if feats else "  — No special features detected"

        def finish_up():
            self._progress.hide()
            self._detect_status.setText("\n".join(lines[-4:]))
            self._summary_lbl.setText(summary)
            self._next_btn.setEnabled(True)
            self._next_btn.setText("Next →")
            self._stack.setCurrentIndex(2)
            self._update_dots(2)
            self._next_btn.setText("Finish")

        QMetaObject.invokeMethod(self, "_finish_detection",
            Qt.ConnectionType.QueuedConnection)

    from PyQt6.QtCore import pyqtSlot

    @pyqtSlot()
    def _finish_detection(self):
        cap = HW
        brand = cap.get("brand","unknown").upper()
        model = cap.get("model","Unknown")
        feats = []
        if cap.get("platform_profile"): feats.append("Power Profiles")
        if cap.get("fan_fullspeed"):    feats.append("Fan Control")
        if cap.get("tp_charge_start"):  feats.append("ThinkPad Charge Thresholds")
        if cap.get("tp_fan_control"):   feats.append("ThinkPad Fan Levels (0–7)")
        if cap.get("yoga_hinge"):       feats.append("Yoga Hinge Mode")
        if cap.get("legionaura"):       feats.append("RGB Keyboard")
        if cap.get("envycontrol"):      feats.append("GPU Mode Switching")
        if cap.get("overdrive"):        feats.append("Display Overdrive")
        if cap.get("gsync"):            feats.append("G-Sync")
        if cap.get("nw_backlight"):    feats.append("Brightness Backlight")
        if cap.get("tp_thinklight"):    feats.append("ThinkLight")
        if cap.get("tp_micmute_led"):   feats.append("Mic Mute LED")
        if cap.get("als_sensor"):       feats.append("Ambient Light Sensor")

        summary = f"Brand:  {brand}\nModel:  {model}\n\nAvailable features:\n"
        summary += "\n".join(f"  ✓  {f}" for f in feats) if feats else "  — Standard features only"
        self._summary_lbl.setText(summary)
        self._progress.hide()
        self._next_btn.setEnabled(True)
        self._next_btn.setText("Finish")
        self._update_dots(2)
        self._stack.setCurrentIndex(2)


class ToggleSwitch(QWidget):
    def __init__(self, path=None, getter=None, setter=None, on_change=None, parent=None, read_val=None):
        super().__init__(parent)
        self.path = path
        self.getter = getter
        self.setter = setter
        self.on_change = on_change
        if read_val is not None:
            val = read_val
        elif getter:
            val = "1" if getter() else "0"
        elif path:
            val = rdsys(path, "0")
        else:
            val = "0"
        self._checked = val == "1"
        self._cx = 26.0 if self._checked else 6.0
        self.setFixedSize(56, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"cx", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def cx(self): return self._cx
    @cx.setter
    def cx(self, v): self._cx = v; self.update()

    def isChecked(self): return self._checked

    def setChecked(self, val, write=True, notify_title=None, notify_on=None, notify_off=None, silent=False):
        self._checked = val
        self._anim.stop()
        self._anim.setStartValue(self._cx)
        self._anim.setEndValue(26.0 if val else 6.0)
        self._anim.start(); self.update()
        if write:
            if self.setter:
                self.setter(val)
            elif self.path:
                wrsys(self.path, "1" if val else "0")
        if notify_title and not silent:
            body = notify_on if val else notify_off or ""
            send_notif(notify_title, body, "dialog-information")
        if self.on_change and not silent:
            self.on_change(val)

    def mousePressEvent(self, e):
        self._user_toggled = True
        if self.getter:
            actual = self.getter()
            self.setChecked(not actual)
        elif self.path and Path(self.path).exists():
            actual = rdsys(self.path, "0") == "1"
            self.setChecked(not actual)
        else:
            self.setChecked(not self._checked)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg_color = C_ACCENT if self._checked else C_TEXT3
        p.setBrush(QBrush(QColor(bg_color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 56, 32, 16, 16)
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(int(self._cx), 6, 20, 20); p.end()


class NotifyToggle(QWidget):
    """ToggleRow that sends a desktop notification on change."""
    def __init__(self, title, desc, path=None,
                 notif_title=None, notif_on="Enabled", notif_off="Disabled",
                 on_change=None, read_val=None, parent=None,
                 getter=None, setter=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;"); self.setFixedHeight(56)
        self._notif_title = notif_title or title
        self._notif_on    = notif_on
        self._notif_off   = notif_off
        lay = QHBoxLayout(self); lay.setContentsMargins(0,4,0,4)
        col = QVBoxLayout(); col.setSpacing(3)
        t = QLabel(title)
        t.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;border:none;")
        d = QLabel(desc)
        d.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;border:none;")
        d.setWordWrap(True)
        col.addWidget(t); col.addWidget(d)
        lay.addLayout(col); lay.addStretch()
        self.toggle = ToggleSwitch(path=path, getter=getter, setter=setter,
                                   on_change=self._on_toggle, parent=self, read_val=read_val)
        lay.addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        self._on_change = on_change

    def _on_toggle(self, val):
        send_notif(self._notif_title,
                   self._notif_on if val else self._notif_off)
        if self._on_change: self._on_change(val)


def _mk_lbl(text: str, color: str = None, size: int = 12, bold: bool = False) -> QLabel:
    """Quick styled QLabel factory."""
    lbl = QLabel(text)
    c = color or C_TEXT2
    w = "600" if bold else "400"
    lbl.setStyleSheet(f"color:{c};font-size:{size}px;font-weight:{w};background:transparent;")
    lbl.setWordWrap(True)
    return lbl

def _mk_lineedit(text: str = "", width: int = 100, placeholder: str = "") -> "QLineEdit":
    from PyQt6.QtWidgets import QLineEdit
    le = QLineEdit(text)
    le.setPlaceholderText(placeholder)
    le.setFixedWidth(width)
    le.setStyleSheet(
        f"QLineEdit{{background:{C_CARD2};color:{C_TEXT};border:none;"
        f"border-radius:8px;padding:8px 12px;font-size:13px;selection-background-color:{C_ACCENT};}}"
    )
    return le

def make_div():
    f = QWidget(); f.setFixedHeight(6); f.setStyleSheet("background:transparent;")
    return f

def make_card(title=""):
    card = QWidget()
    card.setStyleSheet(f"background:{C_CARD};border-radius:12px;")
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    lay = QVBoxLayout(card); lay.setContentsMargins(20,16,20,16); lay.setSpacing(12)
    if title:
        t = QLabel(title)
        t.setStyleSheet(f"color:{C_TEXT};font-size:14px;font-weight:600;background:transparent;border:none;")
        lay.addWidget(t)
    return card, lay

def sec_title(text):
    l = QLabel(text)
    l.setStyleSheet(f"color:{C_TEXT};font-size:14px;font-weight:600;background:transparent;border:none;")
    return l

def combo_style():
    return (f"QComboBox{{background:{C_CARD2};color:{C_TEXT};border:none;"
            f"border-radius:8px;padding:8px 14px;font-size:13px;min-width:180px;}}"
            f"QComboBox::drop-down{{border:none;width:24px;}}"
            f"QComboBox QAbstractItemView{{background:{C_CARD2};color:{C_TEXT};"
            f"border:none;selection-background-color:{C_ACCENT};selection-color:#fff;"
            f"padding:4px;}}")


class StatusBadge(QWidget):
    def __init__(self, title, value="—", color=C_TEXT3, tooltip="", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(90)
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QWidget{{background:{C_CARD2};border-radius:10px;}}"
        )
        lay = QVBoxLayout(self); lay.setContentsMargins(10,8,10,8); lay.setSpacing(2)
        self._t = QLabel(title)
        self._t.setStyleSheet(f"color:{C_TEXT2};font-size:10px;background:transparent;border:none;font-weight:500;")
        self._v = QLabel(value)
        self._v.setStyleSheet(f"color:{color};font-size:13px;font-weight:700;background:transparent;border:none;")
        self._v.setWordWrap(False)
        self._v.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay.addWidget(self._t); lay.addWidget(self._v)
        if tooltip: self.setToolTip(tooltip)

    def set_value(self, v, color=None):
        self._v.setText(v)
        if color:
            self._v.setStyleSheet(
                f"color:{color};font-size:12px;font-weight:600;background:transparent;border:none;"
            )


class AIBadge(StatusBadge):
    """StatusBadge with an inline toggle switch — identical size/style to peers."""
    toggled = None  # callback(bool)

    def __init__(self, on_change=None, parent=None):
        super().__init__("L1 AI Engine", "OFF", C_TEXT3,
                         "Lenovo L1 AI Engine\nOn Linux: adjusts EPP for performance.\nToggle is manual — never auto-changed by profile switching.",
                         parent)
        self.toggled = on_change
        # Replace the value label row with value + toggle side by side
        lay = self.layout()
        # Remove old value label
        lay.removeWidget(self._v)
        self._v.setParent(None)
        # New row: value text + toggle
        row = QHBoxLayout(); row.setContentsMargins(0,0,0,0); row.setSpacing(4)
        self._v = QLabel("OFF")
        self._v.setStyleSheet(f"color:{C_TEXT3};font-size:12px;font-weight:600;background:transparent;border:none;")
        self._v.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._tog = ToggleSwitch(path=None, on_change=self._handle_toggle, read_val="0")
        self._tog.setFixedSize(36, 20)
        row.addWidget(self._v); row.addWidget(self._tog)
        lay.addLayout(row)

    def _handle_toggle(self, val):
        col = C_GREEN if val else C_TEXT3
        self._v.setText("ON" if val else "OFF")
        self._v.setStyleSheet(f"color:{col};font-size:12px;font-weight:600;background:transparent;border:none;")
        if self.toggled:
            self.toggled(val)

    def set_state(self, is_on: bool, silent: bool = False):
        """Update visual state WITHOUT triggering the callback."""
        col = C_GREEN if is_on else C_TEXT3
        self._v.setText("ON" if is_on else "OFF")
        self._v.setStyleSheet(f"color:{col};font-size:12px;font-weight:600;background:transparent;border:none;")
        self._tog._checked = is_on
        self._tog._cx = 22.0 if is_on else 4.0
        self._tog.update()


class ProfileBtn(QPushButton):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setCheckable(True)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        color  = PROFILE_COLORS[profile]
        icon   = PROFILE_ICONS[profile]
        label  = PROFILE_LABELS[profile]
        desc   = PROFILE_DESCS[profile].split(" · ")[0]   # first part only e.g. "15W"
        # Unchecked: dark card
        # Checked: colored border + subtle color background
        import re as _re
        r = int(_re.search(r'#(..)', color).group(1), 16) if '#' in color else 255
        self.setStyleSheet(
            f"QPushButton{{"
            f"  background:{C_CARD2};color:{C_TEXT2};"
            f"  border:none;border-radius:10px;"
            f"  font-size:12px;text-align:center;padding:4px 2px;"
            f"}}"
            f"QPushButton:checked{{"
            f"  background:rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},30);"
            f"  color:{color};border:none;border-radius:10px;"
            f"}}"
            f"QPushButton:hover:!checked{{"
            f"  background:{C_HOVER};color:{C_TEXT};"
            f"}}"
        )
        # Layout inside button: icon on top, label below, watt hint at bottom
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 6)
        lay.setSpacing(1)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon = QLabel(icon)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("background:transparent;font-size:16px;")
        lbl_name = QLabel(label)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setStyleSheet(f"background:transparent;font-size:12px;font-weight:600;color:{color};")
        lbl_desc = QLabel(desc)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet(f"background:transparent;font-size:12px;color:{C_TEXT3};")
        lay.addWidget(lbl_icon)
        lay.addWidget(lbl_name)
        lay.addWidget(lbl_desc)


class SidebarBtn(QPushButton):
    def __init__(self, icon_char, label, parent=None):
        super().__init__(parent); self.setCheckable(True)
        self.setFixedSize(204, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_char = icon_char; self.label = label

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(16, 0, 16, 0)
        self.layout().setSpacing(12)
        self.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._icon_lbl = QLabel(icon_char)
        self._icon_lbl.setStyleSheet(f"font-size:18px;background:transparent;")
        self._icon_lbl.setFixedSize(20, 20)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._text_lbl = QLabel(label)
        self._text_lbl.setStyleSheet(f"font-size:13px;background:transparent;font-weight:500;")

        self.layout().addWidget(self._icon_lbl)
        self.layout().addWidget(self._text_lbl)
        self.layout().addStretch()

        self.toggled.connect(self._update_style)
        self._update_style(self.isChecked())

    def _update_style(self, checked):
        if checked:
            bg = C_ACTIVE; fg = C_ACCENT; tw = 600
            il_color = C_ACCENT; tl_color = C_ACCENT
        else:
            bg = "transparent"; fg = C_TEXT2; tw = 500
            il_color = C_TEXT3; tl_color = C_TEXT2
        self.setStyleSheet(
            f"QPushButton{{background:{bg};border:none;color:{fg};"
            f"border-radius:8px;}}"
            f"QPushButton:hover{{background:{C_HOVER};}}"
        )
        self._icon_lbl.setStyleSheet(f"color:{il_color};font-size:18px;background:transparent;")
        self._text_lbl.setStyleSheet(f"color:{tl_color};font-size:13px;background:transparent;font-weight:{tw};")


def scrollable(widget_factory):
    """Wrap a QVBoxLayout-based page in a scroll area."""
    outer = QWidget()
    outer.setStyleSheet(f"background:{C_BG};")
    scroll = QScrollArea(outer)
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("border:none;background:transparent;")
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
    root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
    lay = QVBoxLayout(outer); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
    scroll.setWidget(inner)
    widget_factory(root)
    root.addStretch()
    return outer

# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._last_profile = None
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # ── Hardware Monitor Card ─────────────────────────────────────────
        hw = QWidget(); hw.setStyleSheet(f"background:{C_CARD};border-radius:12px;")
        hw.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        hw_outer = QHBoxLayout(hw); hw_outer.setContentsMargins(0,0,0,0); hw_outer.setSpacing(0)

        def hw_col(stretch=1):
            w = QWidget(); w.setStyleSheet("background:transparent;")
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            l = QVBoxLayout(w); l.setContentsMargins(16,14,16,14); l.setSpacing(2)
            l.setAlignment(Qt.AlignmentFlag.AlignTop)
            return w, l

        def col_hdr(text, badge_widget=None):
            row = QHBoxLayout(); row.setSpacing(8); row.setContentsMargins(0,0,0,8)
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
            row.addWidget(lbl)
            if badge_widget: row.addWidget(badge_widget)
            row.addStretch()
            hdr_w = QWidget(); hdr_w.setStyleSheet("background:transparent;")
            hdr_l = QVBoxLayout(hdr_w); hdr_l.setContentsMargins(0,0,0,4); hdr_l.setSpacing(3)
            hdr_l.addLayout(row)
            return hdr_w

        def vdiv():
            f = QWidget(); f.setFixedWidth(12); f.setStyleSheet("background:transparent;")
            f.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
            return f

        # CPU column
        cpu_w, cpu_l = hw_col(3)
        cpu_l.addWidget(col_hdr("CPU"))
        self.r_util  = StatRow("Utilization",  "0%",      0)
        self.r_freq  = StatRow("Core Clock",   "0.0 GHz", 0, val_w=80)
        self.r_temp  = StatRow("Temperature",  "0 °C",    0, val_w=80)
        self.r_ic_temp = StatRow("IC Temp",    "—",     0, val_w=80)
        self.r_ic_temp.setToolTip("Integrated Controller temperature (requires LLL)")
        self.r_fan1  = StatRow("Fan 1",        "0 RPM",   0, val_w=80)
        self.r_fan2  = StatRow("Fan 2",        "0 RPM",   0, val_w=80)
        for r in [self.r_util,self.r_freq,self.r_temp,
                  self.r_ic_temp,self.r_fan1,self.r_fan2]:
            cpu_l.addWidget(r)

        # GPU column
        gpu_w, gpu_l = hw_col(3)
        self.gpu_pstate_lbl = QLabel("P-State: —")
        self.gpu_pstate_lbl.setStyleSheet(
            f"color:{C_BLUE};font-size:12px;background:transparent;"
            f"border:none;border-radius:4px;padding:2px 6px;"
        )
        self.gpu_pstate_lbl.setToolTip("GPU Performance State\nP0=Max  P2=Mid  P8=Idle")
        gpu_l.addWidget(col_hdr("GPU", self.gpu_pstate_lbl))
        self.r_g_util = StatRow("Utilization",  "—", 0, val_w=90, color=C_BLUE)
        self.r_g_freq = StatRow("Core Clock",   "—", 0, val_w=90, color=C_BLUE)
        self.r_g_temp = StatRow("Temperature",  "—", 0, val_w=90)
        self.r_g_mem  = StatRow("VRAM Used",    "—", 0, val_w=90, color=C_BLUE)
        self.r_g_pow  = StatRow("Power Draw",   "—", 0, val_w=90, color=C_ORANGE)
        for r in [self.r_g_util,self.r_g_freq,self.r_g_temp,self.r_g_mem,self.r_g_pow]:
            gpu_l.addWidget(r)
        self.gpu_na = QLabel("nvidia-smi not found — yay -S nvidia-utils")
        self.gpu_na.setStyleSheet(f"color:{C_TEXT3};font-size:10px;background:transparent;")
        self.gpu_na.hide(); gpu_l.addWidget(self.gpu_na)

        # Memory & Battery column
        mem_w, mem_l = hw_col(2)
        mem_l.addWidget(col_hdr("Memory & Battery"))
        self.r_ram   = StatRow("RAM Used",  "0 MB",  0, val_w=120)
        self.r_bat   = StatRow("Battery",   "0%",    0, val_w=120, color=C_GREEN)
        self.r_bstat = StatRow("Status",    "—",     0, val_w=120)
        self.r_bpow  = StatRow("Draw",      "— W",   0, val_w=120)
        for r in [self.r_ram,self.r_bat,self.r_bstat,self.r_bpow]:
            mem_l.addWidget(r)

        hw_outer.addWidget(cpu_w, 3); hw_outer.addWidget(vdiv())
        hw_outer.addWidget(gpu_w, 3); hw_outer.addWidget(vdiv())
        hw_outer.addWidget(mem_w, 2)
        root.addWidget(hw)

        # ── Power  +  Graphics  (2-column, LLT-style) ───────────────────────
        two_col = QHBoxLayout(); two_col.setSpacing(10)

        # ── LEFT: Power card ─────────────────────────────────────────────────
        pw, pl = make_card("Power")

        def _setting_row(icon_text, title, desc, control_widget):
            """LLT-style row: icon | title+desc | control"""
            row_w = QWidget(); row_w.setStyleSheet("background:transparent;")
            row_w.setMinimumHeight(60)
            rl = QHBoxLayout(row_w); rl.setContentsMargins(0,6,0,6); rl.setSpacing(14)
            icon = QLabel(icon_text)
            icon.setFixedWidth(32)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet("font-size:18px;background:transparent;")
            txt = QVBoxLayout(); txt.setSpacing(3)
            t = QLabel(title)
            t.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
            d = QLabel(desc); d.setWordWrap(True)
            d.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
            txt.addWidget(t); txt.addWidget(d)
            rl.addWidget(icon)
            rl.addLayout(txt, 1)
            rl.addWidget(control_widget, 0, Qt.AlignmentFlag.AlignVCenter)
            return row_w

        def _combo(options, current_idx=0):
            c = QComboBox(); c.setStyleSheet(combo_style())
            c.setFixedWidth(170); c.setFixedHeight(34)
            for o in options:
                if isinstance(o, tuple):
                    c.addItem(o[0])                        # display text
                    c.setItemData(c.count()-1, o[1])       # sysfs name as UserRole data
                else:
                    c.addItem(o)
            c.setCurrentIndex(current_idx)
            return c

        # Power Mode dropdown
        cur_profile  = lll.read_powermode()
        profile_opts = [(PROFILE_LABELS.get(p,p), p) for p in PROFILES]
        cur_idx      = next((i for i,(_,p) in enumerate(profile_opts) if p == cur_profile), 0)
        self.power_combo = _combo(profile_opts, cur_idx)
        self.power_combo.currentIndexChanged.connect(self._on_power_combo)
        pl.addWidget(_setting_row("⚡", "Power Mode",
            "Change performance profile.  Also: Fn+Q",
            self.power_combo))
        pl.addWidget(make_div())

        # Battery Mode dropdown
        bat_mode_now = 1 if lll.get_conservation_mode() else 2 if lll.get_rapid_charge() else 0
        self.bat_combo = _combo(["Normal", "Conservation (~60%)", "Rapid Charge"], bat_mode_now)
        self.bat_combo.currentIndexChanged.connect(self._on_bat_combo)
        pl.addWidget(_setting_row("🔋", "Battery Mode",
            "Choose how the battery is charged.", self.bat_combo))
        pl.addWidget(make_div())

        # Always on USB dropdown
        usb_mode = lll.get_usb_charging_mode()
        self.usb_combo = _combo(lll.USB_CHARGING_LABELS, usb_mode)
        self.usb_combo.currentIndexChanged.connect(self._on_usb_combo)
        pl.addWidget(_setting_row("🔌", "Always on USB",
            "Control USB charging behavior.", self.usb_combo))
        pl.addWidget(make_div())

        # Fn Lock toggle
        fn_tog = ToggleSwitch(getter=lll.get_fn_lock, setter=lll.set_fn_lock)
        pl.addWidget(_setting_row("⌨️", "Fn Lock",
            "Swap Fn and media keys so F1–F12 work as function keys.", fn_tog))

        two_col.addWidget(pw, 1)

        # ── RIGHT: Graphics card ──────────────────────────────────────────────
        gw, gl = make_card("Graphics")

        # GPU Working Mode via envycontrol
        # Read current mode from envycontrol at build time
        def _envycontrol_current() -> int:
            try:
                r = subprocess.run(["envycontrol", "--query"],
                                   capture_output=True, text=True, timeout=4)
                out = r.stdout.strip().lower()
                if "integrated" in out:   return 2
                if "nvidia" in out:       return 1
                return 0   # hybrid
            except Exception: return 0

        gpu_mode_opts = [
            ("Hybrid  (iGPU + dGPU)", "hybrid"),
            ("NVIDIA  (Discrete only)", "nvidia"),
            ("Integrated  (iGPU only)", "integrated"),
        ]
        _cur_gpu_idx = _envycontrol_current()
        self.gpu_mode_combo = QComboBox()
        self.gpu_mode_combo.setStyleSheet(combo_style())
        self.gpu_mode_combo.setFixedHeight(34)
        for label, _ in gpu_mode_opts:
            self.gpu_mode_combo.addItem(label)
        self.gpu_mode_combo.setCurrentIndex(_cur_gpu_idx)
        self.gpu_mode_combo.currentIndexChanged.connect(self._on_gpu_mode_combo)
        gl.addWidget(_setting_row("🎮", "GPU Working Mode",
            "Switches GPU mode via envycontrol. Requires reboot to take effect.", self.gpu_mode_combo))
        gl.addWidget(make_div())

        # G-Sync Toggle — via ToggleSwitch
        _gsync_tog = ToggleSwitch(getter=lll.get_gsync, setter=lll.set_gsync)
        gl.addWidget(_setting_row("🔄", "G-Sync",
            "NVIDIA G-Sync variable refresh rate. Enable for smoother gaming.", _gsync_tog))
        gl.addWidget(make_div())

        # Display Overdrive toggle
        od_tog = ToggleSwitch(getter=lll.get_overdrive, setter=lll.set_overdrive)
        gl.addWidget(_setting_row("🖥️", "Display Overdrive",
            "Reduce display response time latency.", od_tog))
        gl.addWidget(make_div())

        # Overclock GPU row — button to navigate to OC page
        oc_btn = QPushButton("Open OC →")
        oc_btn.setFixedSize(110, 34)
        oc_btn.setStyleSheet(
            f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:6px;font-size:12px;")
        oc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        oc_btn.clicked.connect(lambda: self._request_page(6))
        gl.addWidget(_setting_row("🚀", "Overclock GPU",
            "Increase performance by overclocking the discrete GPU.", oc_btn))

        two_col.addWidget(gw, 1)
        root.addLayout(two_col)

        # ── System Status badges ──────────────────────────────────────────────
        ss = QWidget(); ss.setStyleSheet(f"background:{C_CARD};border-radius:8px;")
        ss.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        ssl = QVBoxLayout(ss); ssl.setContentsMargins(16,12,16,12); ssl.setSpacing(8)
        ss_title = QLabel("System Status")
        ss_title.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
        ssl.addWidget(ss_title)
        badge_row = QHBoxLayout(); badge_row.setSpacing(6)
        self.b_boost  = StatusBadge("CPU Boost","—",C_TEXT3,"AMD Boost: allows CPU to burst above base clock")
        self.b_gov    = StatusBadge("Governor","—",C_BLUE,"CPU frequency scaling governor")
        self.b_epp    = StatusBadge("EPP","—",C_ORANGE,"Energy Performance Preference")
        self.b_ac     = StatusBadge("Power","—",C_GREEN,"Current power source")
        self.b_pstate = StatusBadge("GPU P-State","—",C_BLUE,"P0=Max Performance  P2=Mid  P8=Idle")
        for b in [self.b_boost,self.b_gov,self.b_epp,self.b_ac,self.b_pstate]:
            badge_row.addWidget(b)
        ssl.addLayout(badge_row)
        root.addWidget(ss)
        root.addStretch()
        self._page_request_cb = None
        self._sync_battery_cb = None   # set by LegionDashboard to sync Battery page
        self._oc_sync_cb = None         # set by LegionDashboard to sync OverclockPage

    def _request_page(self, idx):
        if self._page_request_cb:
            self._page_request_cb(idx)

    def _on_power_combo(self, idx):
        """Power Mode dropdown changed — read sysfs name from item UserRole data."""
        p = self.power_combo.currentData()
        if not p:  # fallback by position
            p = PROFILES[idx] if idx < len(PROFILES) else PROFILES[0]
        ok, msg = apply_profile(p)
        send_notif(f"Power Mode: {PROFILE_LABELS.get(p,p)}",
                   msg if not ok else PROFILE_DESCS.get(p,""), "battery" if ok else "dialog-error")
        # Notify OverclockPage to check power mode + apply presets / greyout
        oc_page = getattr(self, '_oc_sync_cb', None)
        if oc_page:
            oc_page()

    def _on_bat_combo(self, idx):
        """Battery Mode: 0=Normal 1=Conservation 2=Rapid"""
        if idx == 0:
            lll.set_conservation_mode(False); lll.set_rapid_charge(False)
            send_notif("Battery Mode", "Normal charging", "battery")
            mode = "normal"
        elif idx == 1:
            lll.set_conservation_mode(True); lll.set_rapid_charge(False)
            send_notif("Battery Mode", "Conservation — capped at ~60%", "battery")
            mode = "conservation"
        elif idx == 2:
            lll.set_rapid_charge(True); lll.set_conservation_mode(False)
            send_notif("Battery Mode", "Rapid Charge ON", "battery")
            mode = "rapid"
        else:
            return
        # Sync Battery page toggles if callback is set
        if self._sync_battery_cb:
            self._sync_battery_cb(mode)

    def _on_usb_combo(self, idx):
        """Always on USB: 0=Off 1=On when sleeping 2=On always"""
        lll.set_usb_charging_mode(idx)
        if idx < len(lll.USB_CHARGING_LABELS):
            send_notif("USB Charging", lll.USB_CHARGING_LABELS[idx], "usb")
        # Sync Charging page combo
        if hasattr(self, '_charge_usb_combo'):
            self._charge_usb_combo.blockSignals(True)
            self._charge_usb_combo.setCurrentIndex(idx)
            self._charge_usb_combo.blockSignals(False)

    def _on_gpu_mode_combo(self, idx):
        """Apply GPU mode via envycontrol then notify user to reboot."""
        modes  = ["hybrid", "nvidia", "integrated"]
        labels = ["Hybrid (iGPU + dGPU)", "NVIDIA (Discrete only)", "Integrated (iGPU only)"]
        descs  = [
            "AMD iGPU renders, NVIDIA handles 3D workloads.",
            "NVIDIA GPU drives everything — reboot required.",
            "AMD iGPU only, NVIDIA powered off — reboot required.",
        ]
        mode = modes[idx]

        def _do():
            try:
                import socket as _sk
                c = _sk.socket(_sk.AF_UNIX, _sk.SOCK_STREAM)
                c.settimeout(35)
                c.connect("/run/legion-toolkit.sock")
                c.send(f"envycontrol:{mode}\n".encode())
                resp = c.recv(256).decode().strip()
                c.close()
                if resp == "ok":
                    send_notif(
                        f"GPU Mode → {labels[idx]}",
                        f"{descs[idx]}\n\n⚠  Reboot to apply.",
                        "display"
                    )
                elif "not found" in resp:
                    send_notif("envycontrol not found",
                        "Install it: yay -S envycontrol\nthen run: sudo bash update.sh",
                        "dialog-error")
                else:
                    send_notif("GPU Mode — Error",
                        resp.replace("err:","").strip() or "envycontrol failed",
                        "dialog-error")
            except ConnectionRefusedError:
                # Daemon not running — try envycontrol directly via pkexec
                try:
                    import shutil
                    env_bin = shutil.which("envycontrol")
                    if env_bin:
                        r = subprocess.run(
                            ["pkexec", env_bin, "--switch", mode],
                            capture_output=True, text=True, timeout=30
                        )
                        if r.returncode == 0:
                            send_notif(f"GPU Mode → {labels[idx]}",
                                f"{descs[idx]}\n\n⚠  Reboot to apply.", "display")
                        else:
                            send_notif("GPU Mode — Error",
                                (r.stderr or r.stdout or "failed").strip()[:120],
                                "dialog-error")
                    else:
                        send_notif("Daemon not running",
                            "Start it: sudo systemctl start legion-toolkit",
                            "dialog-error")
                except Exception as e2:
                    send_notif("GPU Mode — Error", str(e2)[:100], "dialog-error")
            except Exception as e:
                send_notif("GPU Mode — Error", str(e)[:100], "dialog-error")

        threading.Thread(target=_do, daemon=True).start()

    def _on_profile(self, profile):
        """Kept for compat — not used in new layout."""
        apply_profile(profile)

    def refresh(self, d=None):
        if d is None: return
        # CPU
        self.r_util.update_value(f"{d['cpu_util']}%",  d["cpu_util"])
        self.r_freq.update_value(f"{d['cpu_freq']} GHz", int(d["cpu_freq"]/4.4*100))
        self.r_temp.update_value(f"{d['cpu_temp']} °C",  d["cpu_temp"])
        ic = d.get("ic_temp", 0)
        if ic > 0:
            self.r_ic_temp.set_value(f"{ic} °C", ic, visible=True)
            self.r_ic_temp.setToolTip("Integrated Controller temperature (LLL)")
        else:
            self.r_ic_temp.set_value("—", 0, visible=False)
            self.r_ic_temp.setToolTip("IC temperature requires LLL driver")
        self.r_fan1.update_value(f"{d['fan1']} RPM",  int(d["fan1"]/5000*100))
        self.r_fan2.update_value(f"{d['fan2']} RPM",  int(d["fan2"]/5000*100))
        # GPU
        gpu = d["gpu"]
        if gpu.get("available"):
            self.gpu_na.hide()
            gmem_pct = int(gpu["mem_used"]*100/max(gpu["mem_total"],1))
            self.r_g_util.update_value(f"{gpu['util']}%",  gpu["util"], C_BLUE)
            self.r_g_freq.update_value(f"{gpu['freq']} MHz",int(gpu["freq"]/2000*100),C_BLUE)
            self.r_g_temp.update_value(f"{gpu['temp']} °C", gpu["temp"])
            self.r_g_mem.update_value( f"{gpu['mem_used']}/{gpu['mem_total']} MB",gmem_pct,C_BLUE)
            self.r_g_pow.update_value( f"{gpu['power']:.0f} W",int(gpu["power"]/150*100),C_ORANGE)
            pst = gpu.get("pstate","—")
            col = C_GREEN if pst=="P0" else C_BLUE if pst in ["P1","P2"] else C_TEXT3
            self.gpu_pstate_lbl.setText(f"P-State: {pst}")
            self.gpu_pstate_lbl.setStyleSheet(
                f"color:{col};font-size:12px;background:transparent;"
                f"border:1px solid {col};border-radius:4px;padding:2px 8px;"
            )
        else:
            self.gpu_na.show()
            for r in [self.r_g_util,self.r_g_freq,self.r_g_temp,self.r_g_mem,self.r_g_pow]:
                r.update_value("—", 0)
            self.gpu_pstate_lbl.setText("P-State: N/A")
        # RAM & Battery
        ru=d["ram_used"]; rt=d["ram_total"]; rpct=d["ram_pct"]
        pct=d["bat_pct"]; status=d["bat_status"]
        self.r_ram.update_value(f"{ru} MB / {rt} MB", rpct)
        bat_col = C_GREEN if pct>50 else C_ORANGE if pct>20 else C_RED
        self.r_bat.update_value(f"{pct}%", pct, bat_col)
        self.r_bstat.update_value(status, 0)
        self.r_bpow.update_value(d["bat_power"], 0)
        # Profile — sync dropdown by matching stored UserRole data (sysfs name)
        cur = d["profile"]
        self.power_combo.blockSignals(True)
        for i in range(self.power_combo.count()):
            if self.power_combo.itemData(i, Qt.ItemDataRole.UserRole) == cur:
                self.power_combo.setCurrentIndex(i)
                break
        self.power_combo.blockSignals(False)
        # Badges
        boost = d["boost"]
        self.b_boost.set_value("ON" if boost=="1" else "OFF",
                               C_GREEN if boost=="1" else C_TEXT3)
        self.b_gov.set_value(d["gov"].capitalize(), C_BLUE)
        # EPP: shorten for display, full name in tooltip
        epp_raw = d["epp"]
        EPP_SHORT = {"default":"Default","performance":"Perf","balance_performance":"Bal.Perf",
                     "balance_power":"Bal.Power","power":"PowerSave"}
        self.b_epp.set_value(EPP_SHORT.get(epp_raw, epp_raw[:10]), C_ORANGE)
        self.b_epp.setToolTip(f"EPP: {epp_raw.replace('_',' ').title()}")
        self.b_ac.set_value("AC" if d["ac"] else "Battery",
                            C_GREEN if d["ac"] else C_ORANGE)
        pst2 = gpu.get("pstate","—") if gpu.get("available") else "—"
        self.b_pstate.set_value(pst2,
                                C_GREEN if pst2=="P0" else C_BLUE if pst2 in ["P1","P2"] else C_TEXT3)

# ══════════════════════════════════════════════════════════════════════════════
# BATTERY PAGE
# ══════════════════════════════════════════════════════════════════════════════
class BatteryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._sync_home_cb = None   # set by LegionDashboard to sync Home combo
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        sc, sl = make_card()
        top = QHBoxLayout(); top.setSpacing(24)
        left = QVBoxLayout(); left.setSpacing(4)
        self.pct_lbl    = QLabel("—%")
        self.pct_lbl.setStyleSheet(f"color:{C_TEXT};font-size:42px;font-weight:700;background:transparent;")
        self.status_lbl = QLabel("Status: —")
        self.status_lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;")
        self.health_lbl = QLabel("Health: —")
        self.health_lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;")
        left.addWidget(self.pct_lbl); left.addWidget(self.status_lbl)
        left.addWidget(self.health_lbl); left.addStretch()
        top.addLayout(left)
        vd = QWidget(); vd.setFixedWidth(12); vd.setStyleSheet("background:transparent;"); top.addWidget(vd)
        right = QVBoxLayout(); right.setSpacing(4)
        self.b_charge = StatRow("Charge",  "—", 0, 130, 110, C_GREEN)
        self.b_health = StatRow("Health",  "—", 0, 130)
        self.b_temp   = StatRow("Temp",    "—", 0, 130)
        self.b_power  = StatRow("Draw",    "—", 0, 130)
        for b in [self.b_charge,self.b_health,self.b_temp,self.b_power]:
            right.addWidget(b)
        right.addStretch(); top.addLayout(right)
        sl.addLayout(top); root.addWidget(sc)

        ds, dl = make_card("Battery Details")
        self.info_rows = {}
        for key, label in [("capacity","Capacity"),("voltage","Voltage"),
                            ("cycles","Charge Cycles"),("power","Power Draw"),
                            ("temp","Temperature"),("manufacturer","Manufacturer"),
                            ("model","Model"),("technology","Technology")]:
            r = InfoRow(label,"—"); self.info_rows[key] = r; dl.addWidget(r)
        root.addWidget(ds)

        cc, cl = make_card("Charging Settings")
        # Normal charging toggle — ON = conservation OFF AND rapid OFF
        _is_normal = (not lll.get_conservation_mode() and
                      not lll.get_rapid_charge())
        self._normal_toggle = ToggleSwitch(
            path=None,
            on_change=self._on_normal_toggle,
            read_val="1" if _is_normal else "0"
        )
        norm_row = QWidget(); norm_row.setStyleSheet("background:transparent;"); norm_row.setFixedHeight(56)
        nrl = QHBoxLayout(norm_row); nrl.setContentsMargins(0,0,0,0); nrl.setSpacing(0)
        ncol = QVBoxLayout(); ncol.setSpacing(2)
        nt_lbl = QLabel("Normal Charging"); nt_lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
        nd_lbl = QLabel("Standard mode — both conservation and rapid charge OFF.")
        nd_lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        ncol.addWidget(nt_lbl); ncol.addWidget(nd_lbl)
        nrl.addLayout(ncol); nrl.addStretch()
        nrl.addWidget(self._normal_toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(norm_row)
        cl.addWidget(make_div())

        rows = [
            ("Conservation Mode",
             "Limits charge to ~60% to extend battery lifespan.",
             lll.get_conservation_mode, lll.set_conservation_mode, "conservation"),
            ("Rapid Charging",
             "Charges faster, generates more heat.",
             lll.get_rapid_charge, lll.set_rapid_charge, "rapid"),
            ("Power Charge Mode",
             "Optimised charging curve for battery longevity.",
             lambda: rdsys(POWER_CHARGE_MODE,"0") == "1",
             lambda v: wrsys(POWER_CHARGE_MODE, "1" if v else "0"),
             "pcm"),
        ]
        self.charge_toggles = {}
        for i, (title, desc, getter, setter, key) in enumerate(rows):
            def _make_cb(k):
                def _cb(val):
                    if k == "conservation" and val:
                        lll.set_rapid_charge(False)
                        if "rapid" in self.charge_toggles:
                            self.charge_toggles["rapid"].setChecked(False, write=False, silent=True)
                        self._normal_toggle.setChecked(False, write=False, silent=True)
                        if self._sync_home_cb: self._sync_home_cb(1)
                    elif k == "rapid" and val:
                        lll.set_conservation_mode(False)
                        if "conservation" in self.charge_toggles:
                            self.charge_toggles["conservation"].setChecked(False, write=False, silent=True)
                        self._normal_toggle.setChecked(False, write=False, silent=True)
                        if self._sync_home_cb: self._sync_home_cb(2)
                    elif k == "conservation" and not val and (not lll.get_rapid_charge()):
                        self._normal_toggle.setChecked(True, write=False, silent=True)
                        if self._sync_home_cb: self._sync_home_cb(0)
                    elif k == "rapid" and not val and (not lll.get_conservation_mode()):
                        self._normal_toggle.setChecked(True, write=False, silent=True)
                        if self._sync_home_cb: self._sync_home_cb(0)
                    self._update_dashboard()
                return _cb

            nt = NotifyToggle(title, desc,
                              getter=getter, setter=setter,
                              notif_title=title,
                              notif_on="Enabled",
                              notif_off="Disabled",
                              on_change=_make_cb(key) if key in ("conservation","rapid") else None)
            self.charge_toggles[key] = nt.toggle
            cl.addWidget(nt)
            if i < len(rows)-1: cl.addWidget(make_div())
        root.addWidget(cc)

        # ── USB Charging dropdown ──────────────────────────────────────────
        uc, ul = make_card("🔌  USB Charging")
        usb_desc = QLabel(
            "Choose when USB ports remain powered.")
        usb_desc.setWordWrap(True)
        usb_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        ul.addWidget(usb_desc)
        ul.addWidget(make_div())
        usb_mode = lll.get_usb_charging_mode()
        self._charge_usb_combo = QComboBox()
        self._charge_usb_combo.setStyleSheet(combo_style())
        self._charge_usb_combo.setFixedWidth(170); self._charge_usb_combo.setFixedHeight(34)
        for opt in lll.USB_CHARGING_LABELS:
            self._charge_usb_combo.addItem(opt)
        self._charge_usb_combo.setCurrentIndex(usb_mode)
        self._charge_usb_combo.currentIndexChanged.connect(self._on_charge_usb_combo)
        usb_row = QHBoxLayout()
        usb_row.addWidget(self._charge_usb_combo); usb_row.addStretch()
        ul.addLayout(usb_row)
        root.addWidget(uc)

        # ── ThinkPad charge thresholds (only shown on ThinkPads) ──────────────
        if HW.get("tp_charge_start") and HW.get("tp_charge_stop"):
            tc, tl = make_card("⚡  ThinkPad Charge Thresholds")
            tp_desc = QLabel(
                "Set custom start/stop charge levels to preserve long-term battery health.\n"
                "Example: Start=40%, Stop=80% avoids full cycles.")
            tp_desc.setWordWrap(True)
            tp_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
            tl.addWidget(tp_desc)
            tl.addWidget(make_div())

            def _tp_spin(lo, hi, val, label_text):
                row = QHBoxLayout(); row.setSpacing(12)
                lbl = QLabel(label_text); lbl.setFixedWidth(130)
                lbl.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
                sp = QSpinBox(); sp.setRange(lo, hi); sp.setValue(val); sp.setSuffix(" %")
                sp.setStyleSheet(
                    f"QSpinBox{{background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
                    f"border-radius:6px;padding:6px;font-size:12px;min-width:90px;}}"
                    f"QSpinBox::up-button,QSpinBox::down-button{{width:20px;background:{C_CARD2};}}"
                )
                row.addWidget(lbl); row.addWidget(sp); row.addStretch()
                return row, sp

            try:
                cur_start = int(Path("/sys/class/power_supply/BAT0/charge_start_threshold").read_text().strip())
                cur_stop  = int(Path("/sys/class/power_supply/BAT0/charge_stop_threshold").read_text().strip())
            except:
                cur_start, cur_stop = 40, 80

            start_row, self._tp_start = _tp_spin(0, 99, cur_start, "Start charging at:")
            stop_row,  self._tp_stop  = _tp_spin(1, 100, cur_stop,  "Stop charging at:")
            tl.addLayout(start_row); tl.addLayout(stop_row)

            tp_apply = QPushButton("Apply Thresholds")
            tp_apply.setFixedHeight(32)
            tp_apply.setStyleSheet(
                f"background:{C_ACCENT};color:#fff;border:none;"
                f"border-radius:6px;font-size:12px;padding:0 16px;")
            tp_apply.setCursor(Qt.CursorShape.PointingHandCursor)
            tp_apply.clicked.connect(self._apply_tp_thresholds)
            self._tp_status = QLabel("")
            self._tp_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
            tp_btn_row = QHBoxLayout()
            tp_btn_row.addWidget(tp_apply); tp_btn_row.addWidget(self._tp_status); tp_btn_row.addStretch()
            tl.addLayout(tp_btn_row)
            root.addWidget(tc)

        root.addStretch()

    def sync_charging(self, mode: str):
        """Called from HomePage combo — updates toggles silently (no callbacks, no sysfs writes)."""
        self._normal_toggle.setChecked(mode == "normal",       write=False, silent=True)
        if "conservation" in self.charge_toggles:
            self.charge_toggles["conservation"].setChecked(mode == "conservation", write=False, silent=True)
        if "rapid" in self.charge_toggles:
            self.charge_toggles["rapid"].setChecked(mode == "rapid",        write=False, silent=True)

    def _on_charge_usb_combo(self, idx):
        """USB mode from Charging page: 0=Off 1=On when sleeping 2=On always"""
        lll.set_usb_charging_mode(idx)
        # Sync Features page combo
        if hasattr(self, 'usb_combo'):
            self.usb_combo.blockSignals(True)
            self.usb_combo.setCurrentIndex(idx)
            self.usb_combo.blockSignals(False)

    def _apply_tp_thresholds(self):
        start = self._tp_start.value()
        stop  = self._tp_stop.value()
        if start >= stop:
            self._tp_status.setStyleSheet(f"color:{C_ORANGE};font-size:12px;background:transparent;")
            self._tp_status.setText("✗  Start must be less than Stop")
            return
        def _do():
            cmds = (
                f"echo {start} > /sys/class/power_supply/BAT0/charge_start_threshold && "
                f"echo {stop}  > /sys/class/power_supply/BAT0/charge_stop_threshold"
            )
            r = subprocess.run(["pkexec","sh","-c",cmds],
                               capture_output=True, text=True, timeout=8)
            if r.returncode == 0:
                self._tp_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
                self._tp_status.setText(f"✓  Start {start}%  Stop {stop}%")
                send_notif("Charge Thresholds", f"Start {start}%  →  Stop {stop}%", "battery")
            else:
                self._tp_status.setStyleSheet(f"color:{C_ORANGE};font-size:12px;background:transparent;")
                self._tp_status.setText(f"✗  {r.stderr.strip()[:80]}")
        threading.Thread(target=_do, daemon=True).start()

    def _on_normal_toggle(self, val):
        if val:
            lll.set_conservation_mode(False)
            lll.set_rapid_charge(False)
            if "conservation" in self.charge_toggles:
                self.charge_toggles["conservation"].setChecked(False, write=False, silent=True)
            if "rapid" in self.charge_toggles:
                self.charge_toggles["rapid"].setChecked(False, write=False, silent=True)
            send_notif("Charging Mode", "Normal charging — no limits", "battery")
            if self._sync_home_cb: self._sync_home_cb(0)

    def refresh(self, d=None):
        s = get_battery_stats()
        pct    = s["percent"]
        health = s["health"]
        bat_col    = C_GREEN if pct > 50 else C_ORANGE if pct > 20 else C_RED
        health_col = C_GREEN if health > 80 else C_ORANGE if health > 60 else C_RED
        self.pct_lbl.setText(f"{pct}%")
        self.pct_lbl.setStyleSheet(f"color:{bat_col};font-size:40px;font-weight:600;background:transparent;")
        self.status_lbl.setText(f"Status: {s['status']}")
        self.health_lbl.setText(f"Health: {health}%")
        self.b_charge.update_value(f"{pct}%",    pct,    bat_col)
        self.b_health.update_value(f"{health}%", health, health_col)
        self.b_temp.update_value(s["temp"],  0)
        self.b_power.update_value(s["power"], 0)
        for k in self.info_rows:
            self.info_rows[k].set_value(str(s.get(k, "—")))

# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE PAGE
# ══════════════════════════════════════════════════════════════════════════════
class PerformancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # Boost — detect AMD or Intel
        bc, bl = make_card("CPU Boost")
        br = QHBoxLayout()
        bt_col = QVBoxLayout(); bt_col.setSpacing(3)
        _intel_boost = Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
        _is_intel    = HW.get("cpu_vendor","amd") == "intel" if HW else False
        _boost_path  = _intel_boost if _is_intel and _intel_boost.exists() else AMD_BOOST
        _boost_label = "Intel Turbo Boost" if _is_intel else "AMD CPU Boost"
        _boost_desc  = ("Allows CPU to exceed base clock. Intel Turbo Boost (no_turbo=0 = enabled)."
                        if _is_intel else
                        "Allows CPU to exceed base clock for short bursts. Auto-managed by power profile daemon.")
        bt = QLabel(_boost_label)
        bt.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
        bd = QLabel(_boost_desc)
        bd.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;"); bd.setWordWrap(True)
        bt_col.addWidget(bt); bt_col.addWidget(bd)
        br.addLayout(bt_col); br.addStretch()
        if _is_intel:
            _boost_read = "1" if rdsys(_boost_path,"1") == "0" else rdsys(_boost_path,"0")
            self.boost_toggle = ToggleSwitch(path=_boost_path, read_val=_boost_read)
        else:
            self.boost_toggle = ToggleSwitch(getter=lll.get_cpu_boost, setter=lll.set_cpu_boost,
                                             read_val="1" if lll.get_cpu_boost() else "0")
        br.addWidget(self.boost_toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        bl.addLayout(br); root.addWidget(bc)

        # EPP
        ec, el = make_card("Energy Performance Preference")
        edesc = QLabel("Controls CPU energy/performance tradeoff. Daemon sets this per profile automatically.")
        edesc.setWordWrap(True)
        edesc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        el.addWidget(edesc)
        er = QHBoxLayout(); er.setSpacing(12)
        lbl = QLabel("EPP Level"); lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
        er.addWidget(lbl)
        self.epp_combo = QComboBox(); self.epp_combo.setStyleSheet(combo_style())
        self.epp_combo.setFixedHeight(36)
        cur_epp = get_epp()
        for v in EPP_VALUES: self.epp_combo.addItem(EPP_LABELS[v], v)
        if cur_epp in EPP_VALUES: self.epp_combo.setCurrentIndex(EPP_VALUES.index(cur_epp))
        self.epp_combo.currentIndexChanged.connect(self._on_epp)
        er.addWidget(self.epp_combo); er.addStretch()
        el.addLayout(er)
        self.epp_status = QLabel("")
        self.epp_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;font-weight:500;background:transparent;")
        el.addWidget(self.epp_status); root.addWidget(ec)

        # Fan & Thermal
        fc, fl = make_card("Fan & Thermal")
        for i, (t, d, getter, setter) in enumerate([
            ("Fan Full Speed","Lock both fans to maximum speed immediately.",
             lll.get_fan_fullspeed, lll.set_fan_fullspeed),
            ("Thermal Mode","Enhanced thermal performance for sustained workloads.",
             lll.get_thermal_mode, lll.set_thermal_mode),
        ]):
            fl.addWidget(NotifyToggle(t, d, getter=getter, setter=setter, notif_title=t))
            if i == 0: fl.addWidget(make_div())
        root.addWidget(fc)

        # Live info
        li, ll = make_card("Live CPU Info")
        self.gov_row   = InfoRow("Governor","—"); ll.addWidget(self.gov_row)
        self.freq_row  = InfoRow("Frequency","—"); ll.addWidget(self.freq_row)
        self.temp_row  = InfoRow("Temperature","—"); ll.addWidget(self.temp_row)
        self.boost_row = InfoRow("Boost State","—"); ll.addWidget(self.boost_row)
        root.addWidget(li)
        root.addStretch()

    def _on_epp(self, idx):
        val = EPP_VALUES[idx]; set_epp(val)
        send_notif("EPP Changed", EPP_LABELS[val])
        self.epp_status.setText(f"✓ Set to '{EPP_LABELS[val]}'")
        QTimer.singleShot(2000, lambda: self.epp_status.setText(""))

    def refresh(self, d=None):
        # Accept data from sampler (no blocking reads)
        if d:
            boost = d.get("boost","0")
            self.gov_row.set_value(d.get("gov","—"))
            self.freq_row.set_value(f"{d.get('cpu_freq',0)} GHz")
            self.temp_row.set_value(f"{d.get('cpu_temp',0)} °C")
            epp = d.get("epp","default")
        else:
            boost = "1" if lll.get_cpu_boost() else "0"
            self.gov_row.set_value(get_governor())
            self.freq_row.set_value(f"{get_cpu_freq_ghz()} GHz")
            self.temp_row.set_value(f"{get_cpu_temp()} °C")
            epp = get_epp()
        if not getattr(self.boost_toggle, '_user_toggled', False):
            self.boost_toggle.setChecked(boost == "1", write=False)
        else:
            QTimer.singleShot(2000, lambda: setattr(self.boost_toggle, '_user_toggled', False))
        self.boost_row.set_value("ON ✓" if boost=="1" else "OFF ✗")
        if epp in EPP_VALUES:
            self.epp_combo.blockSignals(True)
            self.epp_combo.setCurrentIndex(EPP_VALUES.index(epp))
            self.epp_combo.blockSignals(False)

# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY PAGE
# ══════════════════════════════════════════════════════════════════════════════
class DisplayPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._outputs = []
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # ── Screen Brightness ─────────────────────────────────────────────────
        bc, bl = make_card("Screen Brightness")
        bl.addWidget(_mk_lbl(
            "Display backlight brightness via sysfs.", C_TEXT2, size=12))

        # Detect backlight path — scan known paths + all available
        _bl_paths = [
            Path("/sys/class/backlight/nvidia_wmi_ec_backlight"),
            Path("/sys/class/backlight/amdgpu_bl0"),
            Path("/sys/class/backlight/amdgpu_bl1"),
            Path("/sys/class/backlight/acpi_video0"),
        ]
        # Also scan dynamically
        try:
            for p in Path("/sys/class/backlight").iterdir():
                if p not in _bl_paths: _bl_paths.append(p)
        except Exception: pass
        self._bl_path = next((p for p in _bl_paths if (p/"brightness").exists()), None)

        if self._bl_path:
            try:
                _max_bl = int((self._bl_path/"max_brightness").read_text().strip())
                _cur_bl = int((self._bl_path/"brightness").read_text().strip())
            except Exception:
                _max_bl = 255; _cur_bl = 128

            # Read actual hardware minimum — nvidia_wmi_ec_backlight supports 0
            try:
                _min_bl = int((self._bl_path/"min_brightness").read_text().strip())
            except:
                _min_bl = 0   # default to 0, allow full dim

            bl.addWidget(_mk_lbl(
                f"Path: {self._bl_path}/brightness  ·  Max: {_max_bl}", C_TEXT3, size=11))

            bri_row = QHBoxLayout(); bri_row.setSpacing(12)
            dim_lbl = QLabel("0%")
            dim_lbl.setFixedWidth(32)
            dim_lbl.setStyleSheet(f"color:{C_TEXT3};font-size:12px;background:transparent;")
            bri_row.addWidget(dim_lbl)

            self._screen_sl = QSlider(Qt.Orientation.Horizontal)
            self._screen_sl.setRange(_min_bl, _max_bl)  # use hardware min — allows 0
            self._screen_sl.setValue(_cur_bl)
            self._screen_sl.setStyleSheet(
                f"QSlider::groove:horizontal{{background:{C_BORDER};height:8px;border-radius:4px;}}"
                f"QSlider::handle:horizontal{{background:{C_BLUE};width:20px;height:20px;"
                f"border-radius:10px;margin:-6px 0;}}"
                f"QSlider::sub-page:horizontal{{background:{C_BLUE};border-radius:4px;}}"
            )
            bri_row.addWidget(self._screen_sl)

            max_lbl = QLabel("100%")
            max_lbl.setFixedWidth(36)
            max_lbl.setStyleSheet(f"color:{C_TEXT3};font-size:12px;background:transparent;")
            bri_row.addWidget(max_lbl)

            # Percentage label
            self._bri_pct_lbl = QLabel(f"{int(_cur_bl/_max_bl*100)}%")
            self._bri_pct_lbl.setFixedWidth(42)
            self._bri_pct_lbl.setStyleSheet(
                f"color:{C_BLUE};font-size:13px;font-weight:600;background:transparent;")
            bri_row.addWidget(self._bri_pct_lbl)
            bl.addLayout(bri_row)

            # Connect: live update on drag, write on release
            self._bl_max = _max_bl
            self._screen_sl.valueChanged.connect(self._on_bri_change)
            self._screen_sl.sliderReleased.connect(self._write_brightness)
        else:
            bl.addWidget(_mk_lbl(
                "⚠  No backlight device found.\n"
                "Is the amdgpu driver loaded? Try: sudo modprobe amdgpu", C_ORANGE, size=11))
        root.addWidget(bc)

        # ── Display toggles ───────────────────────────────────────────────────
        dc, dl = make_card("Display Settings")
        dl.addWidget(NotifyToggle("Display Overdrive",
                                  "Reduce display response time. May introduce minor artefacts.",
                                  getter=lll.get_overdrive, setter=lll.set_overdrive,
                                  notif_title="Display Overdrive"))
        dl.addWidget(make_div())

        # G-Sync — via Legion sysfs node
        _gsync_nt = NotifyToggle(
            "G-Sync",
            "NVIDIA G-Sync variable refresh rate. Enable for smoother gaming.",
            getter=lll.get_gsync, setter=lll.set_gsync,
            notif_title="G-Sync")
        dl.addWidget(_gsync_nt)

        # Brightness Backlight
        if NVIDIA_BACKLIGHT.exists():
            def _is_bl_on():
                try: return int(NVIDIA_BACKLIGHT.read_text().strip()) > 0
                except: return False
            _bl_nt = NotifyToggle(
                "Brightness Backlight",
                "Control display backlight via nvidia_wmi_ec_backlight.",
                NVIDIA_BACKLIGHT,
                notif_title="Brightness Backlight",
                read_val=lambda: "1" if _is_bl_on() else "0")
            dl.addWidget(_bl_nt)
        root.addWidget(dc)

        # ── Resolution ────────────────────────────────────────────────────────
        resc, resl = make_card("Resolution")
        res_desc = QLabel("Change the display resolution. Takes effect immediately.")
        res_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        resl.addWidget(res_desc)

        out_row = QHBoxLayout(); out_row.setSpacing(12)
        out_lbl = QLabel("Output:")
        out_lbl.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
        self.out_combo = QComboBox(); self.out_combo.setStyleSheet(combo_style())
        self.out_combo.currentIndexChanged.connect(self._on_output_change)
        out_row.addWidget(out_lbl); out_row.addWidget(self.out_combo); out_row.addStretch()
        resl.addLayout(out_row)

        res_row = QHBoxLayout(); res_row.setSpacing(12)
        res_lbl = QLabel("Resolution:")
        res_lbl.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
        self.res_combo = QComboBox(); self.res_combo.setStyleSheet(combo_style())
        self.res_combo.currentIndexChanged.connect(self._on_res_change)
        res_row.addWidget(res_lbl); res_row.addWidget(self.res_combo); res_row.addStretch()
        resl.addLayout(res_row)

        self.res_current = InfoRow("Current", "—"); resl.addWidget(self.res_current)

        apply_res_btn = QPushButton("Apply Resolution")
        apply_res_btn.setFixedHeight(32)
        apply_res_btn.setStyleSheet(
            f"background:{C_ACCENT};color:#fff;border-radius:6px;"
            f"font-size:12px;border:none;padding:0 16px;")
        apply_res_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_res_btn.clicked.connect(self._apply_resolution)
        res_btn_row = QHBoxLayout()
        res_btn_row.addWidget(apply_res_btn); res_btn_row.addStretch()
        resl.addLayout(res_btn_row)

        self.res_note = QLabel("No display tool found (kscreen-doctor / hyprctl).")
        self.res_note.setStyleSheet(f"color:{C_ORANGE};font-size:12px;background:transparent;")
        resl.addWidget(self.res_note)
        root.addWidget(resc)

        # ── Refresh Rate ──────────────────────────────────────────────────────
        rrc, rrl = make_card("Refresh Rate")
        rr_desc = QLabel("Set the display refresh rate for the current resolution.")
        rr_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        rrl.addWidget(rr_desc)

        hz_row = QHBoxLayout(); hz_row.setSpacing(12)
        hz_lbl = QLabel("Refresh Rate:")
        hz_lbl.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
        self.hz_combo = QComboBox(); self.hz_combo.setStyleSheet(combo_style())
        hz_row.addWidget(hz_lbl); hz_row.addWidget(self.hz_combo); hz_row.addStretch()
        rrl.addLayout(hz_row)

        self.hz_current = InfoRow("Current", "—"); rrl.addWidget(self.hz_current)

        apply_hz_btn = QPushButton("Apply Refresh Rate")
        apply_hz_btn.setFixedHeight(32)
        apply_hz_btn.setStyleSheet(
            f"background:{C_ACCENT};color:#fff;border-radius:6px;"
            f"font-size:12px;border:none;padding:0 16px;")
        apply_hz_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_hz_btn.clicked.connect(self._apply_rate)
        hz_btn_row = QHBoxLayout()
        hz_btn_row.addWidget(apply_hz_btn); hz_btn_row.addStretch()
        rrl.addLayout(hz_btn_row)
        root.addWidget(rrc)

        root.addStretch()
        self._refresh_outputs()

    def _on_bri_change(self, val: int):
        """Live label update while dragging — no sysfs write yet."""
        pct = int(val / self._bl_max * 100)
        self._bri_pct_lbl.setText(f"{pct}%")

    def _write_brightness(self):
        """Write brightness on slider release — via sysfs direct or pkexec."""
        if not self._bl_path: return
        val = self._screen_sl.value()
        bri_file = self._bl_path / "brightness"
        try:
            bri_file.write_text(str(val) + "\n")
        except PermissionError:
            subprocess.Popen(
                ["pkexec","sh","-c",f"echo {val} > {bri_file}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception: pass

    def _refresh_outputs(self):
        self._outputs = get_display_outputs()
        self.out_combo.blockSignals(True)
        self.out_combo.clear()
        if self._outputs:
            self.res_note.hide()
            self.out_combo.show()
            for name, cur_mode, modes in self._outputs:
                self.out_combo.addItem(name)
        else:
            self.res_note.show()
        self.out_combo.blockSignals(False)
        self._on_output_change(0)

    def _on_output_change(self, idx):
        """Populate resolution combo from unique WxH values for selected output."""
        self.res_combo.blockSignals(True)
        self.res_combo.clear()
        self._cur_output_modes = []   # list of (mode_str, is_cur)

        if 0 <= idx < len(self._outputs):
            name, cur_mode, modes = self._outputs[idx]
            self._cur_output_modes = modes

            # Collect unique resolutions preserving order
            seen_res = {}
            for mode_str, is_cur in modes:
                res = mode_str.split("@")[0]   # "1920x1080"
                if res not in seen_res:
                    seen_res[res] = is_cur
                elif is_cur:
                    seen_res[res] = True

            for res, is_cur in seen_res.items():
                label = ("● " if is_cur else "  ") + res
                self.res_combo.addItem(label, res)
                if is_cur:
                    self.res_combo.setCurrentIndex(self.res_combo.count()-1)

            if cur_mode:
                res_part = cur_mode.split("@")[0]
                hz_part  = cur_mode.split("@")[1] if "@" in cur_mode else "?"
                self.res_current.set_value(f"{res_part}  ({hz_part} Hz active)")
                self.hz_current.set_value(f"{hz_part} Hz")

        self.res_combo.blockSignals(False)
        self._on_res_change(self.res_combo.currentIndex())

    def _on_res_change(self, idx):
        """Populate refresh rate combo for selected resolution."""
        self.hz_combo.blockSignals(True)
        self.hz_combo.clear()
        selected_res = self.res_combo.itemData(idx) if idx >= 0 else None
        if selected_res and self._cur_output_modes:
            for mode_str, is_cur in self._cur_output_modes:
                res = mode_str.split("@")[0]
                if res == selected_res:
                    hz = mode_str.split("@")[1] if "@" in mode_str else "?"
                    label = ("● " if is_cur else "  ") + hz + " Hz"
                    self.hz_combo.addItem(label, mode_str)
                    if is_cur:
                        self.hz_combo.setCurrentIndex(self.hz_combo.count()-1)
        self.hz_combo.blockSignals(False)

    def _apply_resolution(self):
        """Apply selected resolution at its highest available refresh rate."""
        out_idx = self.out_combo.currentIndex()
        res_data = self.res_combo.currentData()
        if out_idx < 0 or not res_data or not self._outputs: return
        out_name = self._outputs[out_idx][0]
        # Find highest Hz mode for this resolution
        best_mode = None
        best_hz = 0
        for mode_str, _ in self._cur_output_modes:
            if mode_str.split("@")[0] == res_data:
                try:
                    hz = int(mode_str.split("@")[1])
                    if hz > best_hz:
                        best_hz = hz; best_mode = mode_str
                except: pass
        if best_mode:
            set_refresh_rate(out_name, best_mode)
            QTimer.singleShot(1500, self._refresh_outputs)

    def _apply_rate(self):
        """Apply selected refresh rate."""
        out_idx  = self.out_combo.currentIndex()
        mode_str = self.hz_combo.currentData()
        if out_idx < 0 or not mode_str or not self._outputs: return
        out_name = self._outputs[out_idx][0]
        set_refresh_rate(out_name, mode_str)
        QTimer.singleShot(1500, self._refresh_outputs)

    def _apply_vrr(self):
        """Apply VRR/FreeSync policy via kscreen-doctor + persist to kscreen config."""
        # combo: 0=Never 1=Automatic 2=Always → kscreen: 0=never 1=automatic 2=always
        _idx_to_ks    = {0: 0, 1: 1, 2: 2}
        _idx_to_str   = {0: "never", 1: "automatic", 2: "always"}
        _idx_to_label = {0: "Never", 1: "Automatic", 2: "Always"}
        idx    = self._vrr_combo.currentIndex()
        policy = _idx_to_ks.get(idx, 0)
        policy_str = _idx_to_str.get(idx, "never")
        label  = _idx_to_label.get(idx, "Never")

        self._vrr_status.setStyleSheet(f"color:{C_ORANGE};font-size:12px;background:transparent;")
        self._vrr_status.setText("⏳  Applying…")

        def _do():
            errors = []
            try:
                data = _kscreen_json()
                for o in data.get("outputs", []):
                    if not o.get("enabled"): continue
                    name    = o.get("name","")
                    out_idx = _kscreen_output_idx(name)
                    r = subprocess.run(
                        ["kscreen-doctor", f"output.{out_idx}.vrrpolicy.{policy_str}"],
                        capture_output=True, text=True, timeout=5
                    )
                    if r.returncode != 0 and r.stderr:
                        errors.append(r.stderr.strip()[:60])
                    _persist_vrr(name, policy)
            except Exception as e:
                errors.append(str(e)[:60])

            from PyQt6.QtCore import QMetaObject, Q_ARG
            if errors:
                QMetaObject.invokeMethod(self._vrr_status, "setText",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, f"✗  {errors[0]}"))
                self._vrr_status.setStyleSheet(
                    f"color:{C_ORANGE};font-size:12px;background:transparent;")
            else:
                QMetaObject.invokeMethod(self._vrr_status, "setText",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, f"✓  VRR set to {label}"))
                self._vrr_status.setStyleSheet(
                    f"color:{C_GREEN};font-size:12px;background:transparent;")
                send_notif("VRR / FreeSync", f"Adaptive sync → {label}", "display")

        threading.Thread(target=_do, daemon=True).start()

    def refresh(self, d=None):
        pass
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARD PAGE — brightness only
# ══════════════════════════════════════════════════════════════════════════════
class KeyboardPage(QWidget):
    _rgb_result = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        bc, bl = make_card("Keyboard Brightness")

        bri_max = get_kbd_max_brightness()
        cur_bri = get_kbd_brightness()

        self._bri_sl = QSlider(Qt.Orientation.Horizontal)
        self._bri_sl.setRange(0, bri_max)
        self._bri_sl.setValue(cur_bri)
        self._bri_sl.setTickInterval(1)
        self._bri_sl.setStyleSheet(
            f"QSlider::groove:horizontal{{background:{C_BORDER};height:8px;border-radius:4px;}}"
            f"QSlider::handle:horizontal{{background:{C_ACCENT};width:20px;height:20px;"
            f"border-radius:10px;margin:-6px 0;}}"
            f"QSlider::sub-page:horizontal{{background:{C_ACCENT};border-radius:4px;}}"
        )
        self._bri_sl.valueChanged.connect(self._on_brightness)
        bl.addWidget(self._bri_sl)

        self._bri_val = QLabel(f"Level {cur_bri} / {bri_max}")
        self._bri_val.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        bl.addWidget(self._bri_val)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        bl.addWidget(self._status_lbl)

        root.addWidget(bc)
        root.addStretch()

        # Poll brightness to detect Fn+Space changes
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self.refresh)
        self._poll_timer.start(int(KEYBOARD_POLL_INTERVAL * 1000))

    def _on_brightness(self, val):
        set_kbd_brightness(val)
        bri_max = get_kbd_max_brightness()
        self._bri_val.setText(f"Level {val} / {bri_max}")

    def cycle_effect(self):
        pass

    def refresh(self, d=None):
        """Read actual keyboard brightness from sysfs and update slider."""
        cur = get_kbd_brightness()
        bri_max = get_kbd_max_brightness()
        if self._bri_sl.value() != cur:
            self._bri_sl.blockSignals(True)
            self._bri_sl.setValue(cur)
            self._bri_sl.blockSignals(False)
            self._bri_val.setText(f"Level {cur} / {bri_max}")

class SystemPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._app_cfg = load_app_config()
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # Input devices
        ic, il = make_card("Input Devices")
        input_rows = [
            ("Fn Lock",   "Swap Fn and media keys so F1–F12 work as standard keys.",
             lll.get_fn_lock, lll.set_fn_lock,
             "Fn Lock ON — F1-F12 as function keys",  "Fn Lock OFF — media keys"),
            ("Super Key", "Enable or disable the Windows/Super key.",
             lll.get_winkey, lll.set_winkey,
             "Super Key Enabled",  "Super Key Disabled"),
            ("Touchpad",  "Enable or disable the built-in touchpad.",
             lll.get_touchpad, lll.set_touchpad,
             "Touchpad Enabled",   "Touchpad Disabled"),
            ("Camera",    "Hardware kill switch for the built-in webcam.",
             lll.get_camera_power, lll.set_camera_power,
             "Camera Enabled",  "Camera Disabled 🔒"),
        ]
        for i, (title, desc, getter, setter, notif_on, notif_off) in enumerate(input_rows):
            il.addWidget(NotifyToggle(title, desc, getter=getter, setter=setter,
                                      notif_title=title,
                                      notif_on=notif_on, notif_off=notif_off))
            if i < len(input_rows)-1: il.addWidget(make_div())
        root.addWidget(ic)

        # ── TrackPoint (ThinkPad only) ────────────────────────────────────────
        if HW.get("tp_trackpoint"):
            tp_c, tp_l = make_card("🔴  TrackPoint")
            tp_l.addWidget(_mk_lbl(
                "Adjust the red TrackPoint pointing stick sensitivity and speed.",
                C_TEXT2, size=12))
            tp_l.addWidget(make_div())

            def _tp_serio_path(attr: str) -> "Path | None":
                try:
                    for d in Path("/sys/bus/serio/devices").iterdir():
                        p = d / attr
                        if p.exists(): return p
                except: pass
                return None

            def _tp_slider(label, attr, lo, hi, color):
                path = _tp_serio_path(attr)
                row = QHBoxLayout(); row.setSpacing(12)
                lb = QLabel(label); lb.setFixedWidth(100)
                lb.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
                sl = QSlider(Qt.Orientation.Horizontal)
                sl.setRange(lo, hi)
                try: sl.setValue(int(path.read_text().strip())) if path else sl.setValue((lo+hi)//2)
                except: sl.setValue((lo+hi)//2)
                sl.setStyleSheet(
                    f"QSlider::groove:horizontal{{background:{C_BORDER};height:6px;border-radius:3px;}}"
                    f"QSlider::handle:horizontal{{background:{color};width:16px;height:16px;border-radius:8px;margin:-5px 0;}}"
                    f"QSlider::sub-page:horizontal{{background:{color};border-radius:3px;}}"
                )
                vl = QLabel(str(sl.value())); vl.setFixedWidth(30)
                vl.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;background:transparent;")
                sl.valueChanged.connect(lambda v, l=vl, p=path: (l.setText(str(v)),
                    _tp_serio_path(attr) and _tp_serio_path(attr).write_text(str(v))))
                row.addWidget(lb); row.addWidget(sl); row.addWidget(vl)
                return row

            tp_l.addLayout(_tp_slider("Sensitivity", "sensitivity", 1, 255, C_RED))
            tp_l.addLayout(_tp_slider("Speed",       "speed",       1, 255, C_ORANGE))
            root.addWidget(tp_c)

        # ── Yoga auto-rotate ──────────────────────────────────────────────────
        if HW.get("yoga_hinge") or HW.get("als_sensor"):
            yr_c, yr_l = make_card("🔄  Yoga — Auto Rotate")
            yr_l.addWidget(_mk_lbl(
                "Lock or unlock automatic screen rotation based on hinge/accelerometer.",
                C_TEXT2, size=11))
            yr_l.addWidget(make_div())

            rot_row = QHBoxLayout(); rot_row.setSpacing(16)
            rot_text = QVBoxLayout(); rot_text.setSpacing(2)
            rot_t = QLabel("Orientation Lock")
            rot_t.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
            rot_d = QLabel("When ON, rotation is locked to current orientation.")
            rot_d.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
            rot_text.addWidget(rot_t); rot_text.addWidget(rot_d)
            rot_row.addLayout(rot_text, 1)

            self._rot_lock_tog = ToggleSwitch(path=None, on_change=self._on_rot_lock, read_val="0")
            rot_row.addWidget(self._rot_lock_tog, 0, Qt.AlignmentFlag.AlignVCenter)
            yr_l.addLayout(rot_row)
            self._rot_status = QLabel("")
            self._rot_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
            yr_l.addWidget(self._rot_status)
            root.addWidget(yr_c)

        # Appearance — Theme
        ac, al = make_card("Appearance")
        th_row = QHBoxLayout(); th_row.setSpacing(12)
        th_lbl = QLabel("Theme")
        th_lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:500;background:transparent;")
        th_row.addWidget(th_lbl)
        self.theme_combo = QComboBox()
        self.theme_combo.setStyleSheet(combo_style())
        self.theme_combo.setFixedHeight(36)
        self.theme_combo.addItems(["Dark", "Dark Dimmed", "OLED Black", "Light"])
        saved_theme = self._app_cfg.get("theme", "dark")
        theme_idx = {"dark": 0, "dark_dimmed": 1, "oled_black": 2, "light": 3}.get(saved_theme, 0)
        self.theme_combo.setCurrentIndex(theme_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme)
        th_row.addWidget(self.theme_combo); th_row.addStretch()
        al.addLayout(th_row)
        th_desc = QLabel("Changes the application theme. Applied immediately.")
        th_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        al.addWidget(th_desc)
        self._app_status = QLabel("")
        self._app_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        al.addWidget(self._app_status)
        root.addWidget(ac)

        # ── Yoga hinge mode (only on Yoga devices) ────────────────────────────
        if HW.get("yoga_hinge"):
            yc, yl = make_card("🔄  Yoga Mode")
            yl.addWidget(_mk_lbl(
                "Your device supports automatic mode switching based on hinge angle.",
                C_TEXT2, size=11))
            yl.addWidget(make_div())
            def _get_yoga_mode() -> str:
                try:
                    p = next(Path("/sys/bus/platform/drivers/lenovo-ymc").glob("*/yoga_mode"), None)
                    if p: return p.read_text().strip()
                except: pass
                return "—"
            self._yoga_mode_lbl = QLabel(f"Current mode: {_get_yoga_mode()}")
            self._yoga_mode_lbl.setStyleSheet(f"color:{C_BLUE};font-size:13px;font-weight:600;background:transparent;")
            yl.addWidget(self._yoga_mode_lbl)
            yoga_ref = QPushButton("🔄  Refresh Mode")
            yoga_ref.setFixedHeight(30)
            yoga_ref.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;font-size:12px;")
            yoga_ref.clicked.connect(lambda: self._yoga_mode_lbl.setText(f"Current mode: {_get_yoga_mode()}"))
            yl.addWidget(yoga_ref)
            root.addWidget(yc)

        # ── ThinkPad keyboard extras ──────────────────────────────────────────
        if HW.get("tp_thinklight") or HW.get("tp_micmute_led"):
            tpk_c, tpk_l = make_card("⌨️  ThinkPad Extras")
            if HW.get("tp_thinklight"):
                tpk_l.addWidget(NotifyToggle(
                    "ThinkLight", "Keyboard light above the screen.",
                    Path("/sys/class/leds/tpacpi::thinklight/brightness"),
                    notif_title="ThinkLight"))
                tpk_l.addWidget(make_div())
            if HW.get("tp_micmute_led"):
                tpk_l.addWidget(NotifyToggle(
                    "Mic Mute LED", "Sync the mic mute LED with system mute state.",
                    Path("/sys/class/leds/platform::micmute/brightness"),
                    notif_title="Mic Mute LED"))
            root.addWidget(tpk_c)

        root.addStretch()

    def _on_rot_lock(self, locked: bool):
        """Toggle screen orientation lock via iio-sensor-proxy / monitor-sensor."""
        def _do():
            try:
                if locked:
                    subprocess.Popen(["gdbus", "call", "--session",
                        "--dest", "net.hadess.SensorProxy",
                        "--object-path", "/net/hadess/SensorProxy",
                        "--method", "net.hadess.SensorProxy.ClaimAccelerometer"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self._rot_status.setText("✓  Rotation locked")
                else:
                    subprocess.Popen(["gdbus", "call", "--session",
                        "--dest", "net.hadess.SensorProxy",
                        "--object-path", "/net/hadess/SensorProxy",
                        "--method", "net.hadess.SensorProxy.ReleaseAccelerometer"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self._rot_status.setText("✓  Auto-rotate enabled")
            except Exception as e:
                self._rot_status.setText(f"✗  {e}")
        threading.Thread(target=_do, daemon=True).start()

    def _on_theme(self, idx):
        """Save theme and restart dashboard so all colours rebuild correctly."""
        names = ["dark", "dark_dimmed", "oled_black", "light"]
        name = names[idx] if idx < len(names) else "dark"
        self._app_cfg["theme"] = name
        save_app_config(self._app_cfg)
        self._app_status.setText("✓ Restarting to apply theme…")
        QTimer.singleShot(500, self._restart)

    def _restart(self):
        """Restart the GUI so all colours rebuild from the saved theme."""
        import os
        win = self.window()
        if win: win.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def refresh(self, d=None): pass

# ══════════════════════════════════════════════════════════════════════════════
# OVERCLOCK PAGE
# ══════════════════════════════════════════════════════════════════════════════
class OverclockPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._cfg    = load_oc_config()
        self._hw_max = get_cpu_hw_max_mhz()
        self._last_powermode = None  # track to detect transitions
        self._oc_spinboxes = []  # filled in _build
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # Warning banner
        warn_card = QWidget(); warn_card.setObjectName("oc_warn")
        warn_card.setStyleSheet(
            f"QWidget#oc_warn{{background:#1a0a00;border-radius:8px;border:1px solid {C_ORANGE};}}"
            f"QWidget#oc_warn QLabel{{background:transparent;border:none;}}"
        )
        wl = QVBoxLayout(warn_card); wl.setContentsMargins(16,12,16,12); wl.setSpacing(4)
        wt = QLabel("⚠️  Overclock / TDP Warning")
        wt.setStyleSheet(f"color:{C_ORANGE};font-size:14px;font-weight:600;")
        wd = QLabel(
            "Changes apply immediately. Instability or data loss can occur. "
            "GPU clock offsets require nvidia-settings with Coolbits=28. "
            "TDP changes via RAPL are reset on reboot unless saved to profile."
        )
        wd.setWordWrap(True); wd.setStyleSheet(f"color:{C_TEXT2};font-size:12px;")
        wl.addWidget(wt); wl.addWidget(wd); root.addWidget(warn_card)

        # ── OC Master Toggle ───────────────────────────────────────────────────
        tc, tl = make_card("Overclock")
        tog_row = QHBoxLayout(); tog_row.setSpacing(16)
        tog_text = QVBoxLayout(); tog_text.setSpacing(2)
        tog_title = QLabel("Enable Overclock")
        tog_title.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
        tog_desc = QLabel(
            "When OFF, CPU runs at stock max frequency and GPU OC is reset. "
            "Toggle ON to apply saved OC settings immediately."
        )
        tog_desc.setWordWrap(True)
        tog_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        tog_text.addWidget(tog_title); tog_text.addWidget(tog_desc)
        tog_row.addLayout(tog_text, 1)
        oc_enabled = self._cfg.get("oc_enabled", False)
        self._oc_toggle = ToggleSwitch(
            path=None,
            on_change=self._on_oc_toggle,
            read_val="1" if oc_enabled else "0"
        )
        tog_row.addWidget(self._oc_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        tl.addLayout(tog_row)
        self._oc_status = QLabel("")
        self._oc_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        tl.addWidget(self._oc_status)
        root.addWidget(tc)

        # Container for all OC controls — hidden when toggle is OFF
        self._oc_controls = QWidget(); self._oc_controls.setStyleSheet("background:transparent;")
        oc_root = QVBoxLayout(self._oc_controls)
        oc_root.setContentsMargins(0,0,0,0); oc_root.setSpacing(10)
        self._oc_controls.setVisible(oc_enabled)

        def _spin(lo, hi, val, suffix=" MHz", step=100, color=C_TEXT):
            sp = ArrowSpinBox()
            sp.setRange(lo, hi); sp.setSuffix(suffix)
            sp.setValue(val); sp.setSingleStep(step)
            # Arrows are painted by ArrowSpinBox.paintEvent (QPainter), so no
            # ::up-arrow/::down-arrow stylesheet rule is needed (and data: URIs
            # don't render in Qt stylesheets anyway).
            sp.setStyleSheet(
                f"QSpinBox{{background:{C_CARD2};color:{color};border:1px solid {C_BORDER};"
                f"border-radius:6px;"
                f"padding:2px {SPIN_BTN_W + 2}px 2px 8px;"  # clears the buttons + gap
                f"font-size:13px;min-width:120px;min-height:34px;}}"
                f"QSpinBox::up-button{{subcontrol-origin:border;subcontrol-position:top right;"
                f"width:{SPIN_BTN_W}px;background:{C_CARD2};border:none;"
                f"border-left:1px solid {C_BORDER};border-top-right-radius:6px;}}"
                f"QSpinBox::up-button:hover{{background:{C_BORDER};}}"
                f"QSpinBox::down-button{{subcontrol-origin:border;subcontrol-position:bottom right;"
                f"width:{SPIN_BTN_W}px;background:{C_CARD2};border:none;"
                f"border-left:1px solid {C_BORDER};border-top:1px solid {C_BORDER};"
                f"border-bottom-right-radius:6px;}}"
                f"QSpinBox::down-button:hover{{background:{C_BORDER};}}"
                f"QSpinBox:disabled{{background:#161616;color:#555555;border-color:#262626;}}"
                f"QSpinBox::up-button:disabled,QSpinBox::down-button:disabled{{background:#161616;}}"
            )
            return sp

        # ── OC control lockdown registry ────────────────────────────────────────
        self._oc_pairs = []          # (label, widget) gated by power mode
        self._oc_always_locked = []  # (label, widget) always disabled (clock/mem offsets)

        def _row(label, widget, color=C_TEXT, always_locked=False):
            r = QHBoxLayout(); r.setSpacing(12)
            lb = QLabel(label); lb.setFixedWidth(200)
            lb.setStyleSheet(f"color:{color};font-size:12px;background:transparent;")
            lb.setProperty("base", color)
            r.addWidget(lb); r.addWidget(widget); r.addStretch()
            if always_locked:
                self._oc_always_locked.append((lb, widget))
            else:
                self._oc_pairs.append((lb, widget))
            return r

        # ── CPU section ────────────────────────────────────────────────────────
        _cpu_label = "CPU"
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if "model name" in line.lower():
                    _cpu_label = "CPU — " + line.split(":")[1].strip()[:40]
                    break
        except: pass
        cc, cl = make_card(_cpu_label)
        cur_pl1, cur_pl2 = get_cpu_tdp()

        self.cpu_freq_spin = _spin(CPU_FREQ_MIN_MHZ, CPU_FREQ_MAX_MHZ,
                                   self._cfg.get("cpu_max_freq_mhz", self._hw_max))
        cl.addLayout(_row("P-Core Max Freq:", self.cpu_freq_spin, C_RED))
        self.cpu_freq_sl = QSlider(Qt.Orientation.Horizontal)
        self.cpu_freq_sl.setRange(CPU_FREQ_MIN_MHZ, CPU_FREQ_MAX_MHZ)
        self.cpu_freq_sl.setValue(self.cpu_freq_spin.value()); self.cpu_freq_sl.setSingleStep(100)
        self.cpu_freq_sl.setStyleSheet(
            f"QSlider::groove:horizontal{{background:{C_BORDER};height:6px;border-radius:3px;}}"
            f"QSlider::handle:horizontal{{background:{C_RED};width:16px;height:16px;border-radius:8px;margin:-5px 0;}}"
            f"QSlider::sub-page:horizontal{{background:{C_RED};border-radius:3px;}}"
        )
        self.cpu_freq_sl.valueChanged.connect(self.cpu_freq_spin.setValue)
        self._oc_pairs.append((None, self.cpu_freq_sl))
        self.cpu_freq_sl.setProperty("orig_slider_style", self.cpu_freq_sl.styleSheet())
        self.cpu_freq_spin.valueChanged.connect(self.cpu_freq_sl.setValue)
        cl.addWidget(self.cpu_freq_sl)

        # E-Core Max Frequency
        self.ecore_freq_spin = _spin(ECORE_FREQ_MIN_MHZ, ECORE_FREQ_MAX_MHZ,
                                     self._cfg.get("ecore_max_freq_mhz", get_ecore_hw_max_mhz()),
                                     color=C_PURPLE)
        cl.addLayout(_row("E-Core Max Freq:", self.ecore_freq_spin, C_PURPLE))
        self.ecore_freq_sl = QSlider(Qt.Orientation.Horizontal)
        self.ecore_freq_sl.setRange(ECORE_FREQ_MIN_MHZ, ECORE_FREQ_MAX_MHZ)
        self.ecore_freq_sl.setValue(self.ecore_freq_spin.value())
        self.ecore_freq_sl.setSingleStep(100)
        self.ecore_freq_sl.setStyleSheet(
            f"QSlider::groove:horizontal{{background:{C_BORDER};height:6px;border-radius:3px;}}"
            f"QSlider::handle:horizontal{{background:{C_PURPLE};width:16px;height:16px;border-radius:8px;margin:-5px 0;}}"
            f"QSlider::sub-page:horizontal{{background:{C_PURPLE};border-radius:3px;}}"
        )
        self.ecore_freq_sl.valueChanged.connect(self.ecore_freq_spin.setValue)
        self._oc_pairs.append((None, self.ecore_freq_sl))
        self.ecore_freq_sl.setProperty("orig_slider_style", self.ecore_freq_sl.styleSheet())
        self.ecore_freq_spin.valueChanged.connect(self.ecore_freq_sl.setValue)
        cl.addWidget(self.ecore_freq_sl)



        # TDP PL1
        self.pl1_spin = _spin(CPU_PL1_MIN_WATTS, CPU_PL1_MAX_WATTS, self._cfg.get("pl1_w", cur_pl1 or 55),
                              suffix=" W", step=1, color=C_ORANGE)
        cl.addLayout(_row("TDP — PL1 (sustained):", self.pl1_spin, C_ORANGE))
        self.pl1_sl = QSlider(Qt.Orientation.Horizontal)
        self.pl1_sl.setRange(CPU_PL1_MIN_WATTS, CPU_PL1_MAX_WATTS); self.pl1_sl.setValue(self.pl1_spin.value())
        self.pl1_sl.setStyleSheet(
            f"QSlider::groove:horizontal{{background:{C_BORDER};height:6px;border-radius:3px;}}"
            f"QSlider::handle:horizontal{{background:{C_ORANGE};width:16px;height:16px;border-radius:8px;margin:-5px 0;}}"
            f"QSlider::sub-page:horizontal{{background:{C_ORANGE};border-radius:3px;}}"
        )
        self.pl1_sl.valueChanged.connect(self.pl1_spin.setValue)
        self._oc_pairs.append((None, self.pl1_sl))
        self.pl1_sl.setProperty("orig_slider_style", self.pl1_sl.styleSheet())
        self.pl1_spin.valueChanged.connect(self.pl1_sl.setValue)
        # PL1/PL2 constraint: PL2 >= PL1
        self.pl1_spin.valueChanged.connect(self._pl1_changed)
        cl.addWidget(self.pl1_sl)

        # TDP PL2
        self.pl2_spin = _spin(CPU_PL2_MIN_WATTS, CPU_PL2_MAX_WATTS, self._cfg.get("pl2_w", cur_pl2 or 80),
                              suffix=" W", step=1, color=C_ORANGE)
        cl.addLayout(_row("TDP — PL2 (boost peak):", self.pl2_spin, C_ORANGE))
        self.pl2_sl = QSlider(Qt.Orientation.Horizontal)
        self.pl2_sl.setRange(CPU_PL2_MIN_WATTS, CPU_PL2_MAX_WATTS); self.pl2_sl.setValue(self.pl2_spin.value())
        self.pl2_sl.setStyleSheet(
            f"QSlider::groove:horizontal{{background:{C_BORDER};height:6px;border-radius:3px;}}"
            f"QSlider::handle:horizontal{{background:{C_ORANGE};width:16px;height:16px;border-radius:8px;margin:-5px 0;}}"
            f"QSlider::sub-page:horizontal{{background:{C_ORANGE};border-radius:3px;}}"
        )
        self.pl2_sl.valueChanged.connect(self.pl2_spin.setValue)
        self._oc_pairs.append((None, self.pl2_sl))
        self.pl2_sl.setProperty("orig_slider_style", self.pl2_sl.styleSheet())
        self.pl2_spin.valueChanged.connect(self.pl2_sl.setValue)
        # PL1/PL2 constraint: PL2 >= PL1
        self.pl2_spin.valueChanged.connect(self._pl2_changed)
        cl.addWidget(self.pl2_sl)

        # TAU (PL1 Tau Duration)
        self.tau_spin = _spin(CPU_TAU_MIN_SECS, CPU_TAU_MAX_SECS,
                              min(CPU_TAU_MAX_SECS, max(CPU_TAU_MIN_SECS, self._cfg.get("cpu_tau", 56))),
                              suffix=" s", step=1, color=C_YELLOW)
        cl.addLayout(_row("Tau Duration (PL1):", self.tau_spin, C_YELLOW))

        # Cross Loading
        self.crossload_spin = _spin(CPU_CROSSLOAD_MIN_WATTS, CPU_CROSSLOAD_MAX_WATTS, self._cfg.get("cpu_crossload", 30),
                                    suffix=" W", step=1, color=C_YELLOW)
        cl.addLayout(_row("Cross Loading Limit:", self.crossload_spin, C_YELLOW))

        # CPU Temperature Limit
        self.cpu_temp_lim_spin = _spin(CPU_TEMP_MIN_CELSIUS, CPU_TEMP_MAX_CELSIUS, self._cfg.get("cpu_temp_lim", 94),
                                      suffix=" °C", step=1, color=C_RED)
        cl.addLayout(_row("CPU Temp Limit:", self.cpu_temp_lim_spin, C_RED))

        cpu_tdp_hint = QLabel("PL1 = sustained TDP  ·  PL2 = short boost ceiling  ·  Reset on reboot")
        cpu_tdp_hint.setStyleSheet(f"color:{C_TEXT3};font-size:10px;background:transparent;")
        cl.addWidget(cpu_tdp_hint)

        cpu_btn_row = QHBoxLayout(); cpu_btn_row.setSpacing(8)
        for label, slot, bg in [
            ("Apply CPU", self._apply_cpu, C_ACCENT),
            ("Reset CPU OC", self._reset_cpu, C_CARD2),
        ]:
            b = QPushButton(label); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{bg};color:{'#fff' if bg!=C_CARD2 else C_TEXT};"
                f"border:{'none' if bg!=C_CARD2 else f'1px solid {C_BORDER}'};"
                f"border-radius:6px;font-size:12px;padding:8px 14px;}}"
                f"QPushButton:disabled{{background:#222222;color:#555555;border:1px solid #2a2a2a;}}"
            )
            b.clicked.connect(slot); cpu_btn_row.addWidget(b)
            self._oc_pairs.append((None, b))
        cpu_btn_row.addStretch()
        cl.addLayout(cpu_btn_row)
        self.cpu_status = QLabel("")
        self.cpu_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        cl.addWidget(self.cpu_status)
        oc_root.addWidget(cc)
        _gpu_label = "GPU"
        _nvidia_label = None
        try:
            r = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                if "VGA" in line or "3D" in line:
                    name = line.split(":",2)[-1].strip()[:45]
                    if "NVIDIA" in line.upper():
                        _nvidia_label = "GPU — " + name
                        break
                    elif not _nvidia_label:
                        _gpu_label = "GPU — " + name
            if _nvidia_label:
                _gpu_label = _nvidia_label
        except: pass
        gc, gl = make_card(_gpu_label)

        # Requirements note
        req_lbl = QLabel(
            "Clock offsets require nvidia-settings (AUR: nvidia-settings) + "
            "Option \"Coolbits\" \"28\" in /etc/X11/xorg.conf.d/10-nvidia.conf"
        )
        req_lbl.setWordWrap(True)
        req_lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        gl.addWidget(req_lbl)

        # Live GPU stats row
        self.gpu_live = QLabel("Querying…")
        self.gpu_live.setStyleSheet(f"color:{C_TEXT3};font-size:12px;background:transparent;")
        gl.addWidget(self.gpu_live)
        gl.addWidget(make_div())

        for attr, label, lo, hi, default, suffix, color in [
            ("gpu_core_spin",  "Core Clock Offset",   GPU_CORE_OFFSET_MIN_MHZ,  GPU_CORE_OFFSET_MAX_MHZ,
             self._cfg.get("gpu_core_offset", 0),  " MHz", C_BLUE),
            ("gpu_mem_spin",   "Mem Transfer Offset", GPU_MEM_OFFSET_MIN_MHZ,  GPU_MEM_OFFSET_MAX_MHZ,
             self._cfg.get("gpu_mem_offset",  0),  " MHz", C_PURPLE),
        ]:
            sp = _spin(lo, hi, default, suffix, step=GPU_OFFSET_STEP_MHZ, color=color)
            setattr(self, attr, sp)
            gl.addLayout(_row(label + ":", sp, color, always_locked=True))

        # GPU WMI power controls
        gl.addWidget(make_div())

        self.gpu_dynboost_ppab_spin = _spin(GPU_PPAB_MIN_WATTS, GPU_PPAB_MAX_WATTS, self._cfg.get("gpu_dynboost_ppab", 15),
                                      suffix=" W", step=GPU_PPAB_STEP_WATTS, color=C_ORANGE)
        gl.addLayout(_row("Dynamic Boost (PPAB):", self.gpu_dynboost_ppab_spin, C_ORANGE))

        self.gpu_ctgp_spin = _spin(GPU_CTGP_MIN_WATTS, GPU_CTGP_MAX_WATTS, self._cfg.get("gpu_ctgp", 45),
                                  suffix=" W", step=GPU_CTGP_STEP_WATTS, color=C_ORANGE)
        gl.addLayout(_row("cTGP Limit:", self.gpu_ctgp_spin, C_ORANGE))

        self.gpu_total_proc_spin = _spin(GPU_TOTAL_PROC_MIN_WATTS, GPU_TOTAL_PROC_MAX_WATTS, self._cfg.get("gpu_total_proc", 30),
                                           suffix=" W", step=GPU_TOTAL_PROC_STEP_WATTS, color=C_ORANGE)
        gl.addLayout(_row("Total Proc Power (Offset):", self.gpu_total_proc_spin, C_ORANGE))

        self.gpu_temp_spin = _spin(GPU_TEMP_MIN_CELSIUS, GPU_TEMP_MAX_CELSIUS, self._cfg.get("gpu_temp_limit", 87),
                                   suffix=" °C", step=1, color=C_RED)
        gl.addLayout(_row("GPU Temp Limit:", self.gpu_temp_spin, C_RED))

        gpu_btn_row = QHBoxLayout(); gpu_btn_row.setSpacing(8)
        for label, slot, bg in [
            ("Apply GPU OC", self._apply_gpu, C_BLUE),
            ("Reset GPU OC", self._reset_gpu_oc, C_CARD2),
        ]:
            b = QPushButton(label); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{bg};color:{'#fff' if bg!=C_CARD2 else C_TEXT};"
                f"border:{'none' if bg!=C_CARD2 else f'1px solid {C_BORDER}'};"
                f"border-radius:6px;font-size:12px;padding:8px 14px;}}"
                f"QPushButton:disabled{{background:#222222;color:#555555;border:1px solid #2a2a2a;}}"
            )
            b.clicked.connect(slot); gpu_btn_row.addWidget(b)
            self._oc_pairs.append((None, b))
        gpu_btn_row.addStretch()
        gl.addLayout(gpu_btn_row)
        self.gpu_status = QLabel("")
        self.gpu_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        gl.addWidget(self.gpu_status)
        oc_root.addWidget(gc)

        # ── Live GPU timer ─────────────────────────────────────────────────────
        self._gpu_timer = QTimer(self)
        self._gpu_timer.timeout.connect(self._refresh_gpu_live)
        self._gpu_timer.start(2000)
        self._refresh_gpu_live()

        # Clock/mem offsets are non-functional on this model — always locked
        for w, lb in self._oc_always_locked:
            w.setEnabled(False)
            lb.setStyleSheet(
                f"color:#555555;font-size:12px;background:transparent;text-decoration:line-through;")

        root.addWidget(self._oc_controls)
        root.addStretch()

    def _on_oc_toggle(self, enabled: bool):
        self._oc_controls.setVisible(enabled)
        self._cfg["oc_enabled"] = enabled
        save_oc_config(self._cfg)
        if enabled:
            # Re-apply saved OC settings
            self._apply_cpu()
            self._apply_gpu()
            self._oc_status.setText("✓ Overclock enabled — settings applied")
        else:
            # Reset everything to stock
            self._reset_cpu()
            self._reset_gpu_oc()
            self._oc_status.setText("✓ Overclock disabled — stock settings restored")
        QTimer.singleShot(4000, lambda: self._oc_status.setText(""))

    def _pl1_changed(self, val):
        """Enforce PL2 >= PL1: if PL1 > PL2, raise PL2."""
        if val > self.pl2_spin.value():
            self.pl2_spin.blockSignals(True)
            self.pl2_spin.setValue(val)
            self.pl2_sl.setValue(val)
            self.pl2_spin.blockSignals(False)

    def _pl2_changed(self, val):
        """Enforce PL2 >= PL1: if PL2 < PL1, lower PL1."""
        if val < self.pl1_spin.value():
            self.pl1_spin.blockSignals(True)
            self.pl1_spin.setValue(val)
            self.pl1_sl.setValue(val)
            self.pl1_spin.blockSignals(False)

    def _label_style(self, lb, enabled: bool) -> str:
        base = lb.property("base") or C_TEXT
        col = base if enabled else "#555555"
        return f"color:{col};font-size:12px;background:transparent;"

    def _locked_label_style(self, lb) -> str:
        return (f"color:#555555;font-size:12px;background:transparent;"
                f"text-decoration:line-through;")

    def _set_oc_enabled(self, enabled: bool):
        """Enable/disable all power-mode-gated OC controls and dim their labels.
        Clock/mem offset controls stay locked regardless of mode."""
        for lb, w in self._oc_pairs:
            w.setEnabled(enabled)
            if lb is not None:
                lb.setStyleSheet(self._label_style(lb, enabled))
            if isinstance(w, QSlider):
                if enabled:
                    w.setStyleSheet(w.property("orig_slider_style") or "")
                else:
                    w.setStyleSheet(DISABLED_SLIDER_STYLE)
        for lb, w in self._oc_always_locked:
            w.setEnabled(False)
            if lb is not None:
                lb.setStyleSheet(self._locked_label_style(lb))

    def _apply_preset(self, profile: str):
        """Apply firmware preset values for the given power mode."""
        presets = {
            "quiet": POWERMODE_QUIET,
            "balanced": POWERMODE_BALANCED,
            "performance": POWERMODE_PERFORMANCE,
        }
        p = presets.get(profile)
        if not p:
            return
        from lib.lll_adapter import (set_cpu_longterm_powerlimit, set_cpu_shortterm_powerlimit,
                                      set_cpu_l1_tau, set_cpu_cross_loading_powerlimit,
                                      set_cpu_temperature_limit, set_gpu_oc_powerlimit,
                                      set_gpu_ctgp_powerlimit, set_gpu_power_target_offset,
                                      set_gpu_temperature_limit)
        set_cpu_longterm_powerlimit(p["pl1"])
        set_cpu_shortterm_powerlimit(p["pl2"])
        set_cpu_l1_tau(p["tau"])
        set_cpu_cross_loading_powerlimit(p["crossload"])
        set_cpu_temperature_limit(p["cpu_temp"])
        set_gpu_oc_powerlimit(p["ppab"])
        set_gpu_ctgp_powerlimit(p["ctgp"])
        set_gpu_power_target_offset(p["total_proc"])
        set_gpu_temperature_limit(p["gpu_temp"])
        # Update spinbox display
        self.pl1_spin.blockSignals(True); self.pl1_spin.setValue(p["pl1"])
        self.pl1_sl.setValue(p["pl1"]); self.pl1_spin.blockSignals(False)
        self.pl2_spin.blockSignals(True); self.pl2_spin.setValue(p["pl2"])
        self.pl2_sl.setValue(p["pl2"]); self.pl2_spin.blockSignals(False)
        self.tau_spin.setValue(p["tau"])
        self.crossload_spin.setValue(p["crossload"])
        self.cpu_temp_lim_spin.setValue(p["cpu_temp"])
        self.gpu_dynboost_ppab_spin.setValue(p["ppab"])
        self.gpu_ctgp_spin.setValue(p["ctgp"])
        self.gpu_total_proc_spin.setValue(p["total_proc"])
        self.gpu_temp_spin.blockSignals(True)
        self.gpu_temp_spin.setValue(p["gpu_temp"])
        self.gpu_temp_spin.blockSignals(False)
        self._cfg.update({
            "pl1_w": p["pl1"], "pl2_w": p["pl2"], "cpu_tau": p["tau"],
            "cpu_crossload": p["crossload"], "cpu_temp_lim": p["cpu_temp"],
            "gpu_dynboost_ppab": p["ppab"], "gpu_ctgp": p["ctgp"],
            "gpu_total_proc": p["total_proc"], "gpu_temp_limit": p["gpu_temp"],
        })
        save_oc_config(self._cfg)
        self.cpu_status.setText(f"✓ Preset: {profile.title()} — PL1 {p['pl1']}W · PL2 {p['pl2']}W")
        QTimer.singleShot(4000, lambda: self.cpu_status.setText(""))

    def check_powermode(self):
        """Check current power mode: enable OC controls only in Custom mode,
        otherwise grey them out and apply the reference preset for that mode."""
        from lib.lll_adapter import read_powermode, POWERMODE_CUSTOM_STR
        try:
            mode = read_powermode()
        except Exception:
            return
        is_custom = (mode == POWERMODE_CUSTOM_STR)
        prev = self._last_powermode
        if is_custom:
            # Returning to Custom → restore the user's last custom OC values
            if prev is not None and prev != POWERMODE_CUSTOM_STR:
                self._restore_custom_oc()
            self._set_oc_enabled(True)
        else:
            # Leaving Custom → snapshot current values before applying the preset
            if prev == POWERMODE_CUSTOM_STR:
                self._save_custom_oc()
            self._set_oc_enabled(False)
            # Apply reference values whenever the standard mode changes
            if mode != prev:
                self._apply_preset(mode)
        self._last_powermode = mode

    def _save_custom_oc(self):
        """Snapshot current OC spinbox values while in Custom mode."""
        self._custom_backup = {
            "pl1": self.pl1_spin.value(), "pl2": self.pl2_spin.value(),
            "tau": self.tau_spin.value(), "crossload": self.crossload_spin.value(),
            "cpu_temp": self.cpu_temp_lim_spin.value(),
            "gpu_ppab": self.gpu_dynboost_ppab_spin.value(),
            "gpu_ctgp": self.gpu_ctgp_spin.value(),
            "gpu_total": self.gpu_total_proc_spin.value(),
            "gpu_temp": self.gpu_temp_spin.value(),
        }

    def _restore_custom_oc(self):
        """Write the last saved custom OC values back to the kernel + UI."""
        b = getattr(self, "_custom_backup", None)
        if not b:
            return
        from lib.lll_adapter import (set_cpu_longterm_powerlimit, set_cpu_shortterm_powerlimit,
                                     set_cpu_l1_tau, set_cpu_cross_loading_powerlimit,
                                     set_cpu_temperature_limit, set_gpu_oc_powerlimit,
                                     set_gpu_ctgp_powerlimit, set_gpu_power_target_offset,
                                     set_gpu_temperature_limit)
        set_cpu_longterm_powerlimit(b["pl1"])
        set_cpu_shortterm_powerlimit(b["pl2"])
        set_cpu_l1_tau(b["tau"])
        set_cpu_cross_loading_powerlimit(b["crossload"])
        set_cpu_temperature_limit(b["cpu_temp"])
        set_gpu_oc_powerlimit(b["gpu_ppab"])
        set_gpu_ctgp_powerlimit(b["gpu_ctgp"])
        set_gpu_power_target_offset(b["gpu_total"])
        set_gpu_temperature_limit(b["gpu_temp"])
        self.pl1_spin.blockSignals(True); self.pl1_spin.setValue(b["pl1"]); self.pl1_sl.setValue(b["pl1"]); self.pl1_spin.blockSignals(False)
        self.pl2_spin.blockSignals(True); self.pl2_spin.setValue(b["pl2"]); self.pl2_sl.setValue(b["pl2"]); self.pl2_spin.blockSignals(False)
        self.tau_spin.setValue(b["tau"])
        self.crossload_spin.setValue(b["crossload"])
        self.cpu_temp_lim_spin.setValue(b["cpu_temp"])
        self.gpu_dynboost_ppab_spin.setValue(b["gpu_ppab"])
        self.gpu_ctgp_spin.setValue(b["gpu_ctgp"])
        self.gpu_total_proc_spin.setValue(b["gpu_total"])
        self.gpu_temp_spin.blockSignals(True); self.gpu_temp_spin.setValue(b["gpu_temp"]); self.gpu_temp_spin.blockSignals(False)
        self._cfg.update({"pl1_w": b["pl1"], "pl2_w": b["pl2"], "cpu_tau": b["tau"],
                         "cpu_crossload": b["crossload"], "cpu_temp_lim": b["cpu_temp"],
                         "gpu_dynboost_ppab": b["gpu_ppab"], "gpu_ctgp": b["gpu_ctgp"],
                         "gpu_total_proc": b["gpu_total"], "gpu_temp_limit": b["gpu_temp"]})
        save_oc_config(self._cfg)

    def _refresh_gpu_live(self):
        g = get_gpu_info()
        if g.get("available"):
            self.gpu_live.setText(
                f"Util {g['util']}%  ·  {g['temp']}°C  ·  "
                f"{g['freq']} MHz  ·  {g['mem_used']}/{g['mem_total']} MB  ·  "
                f"{g['power']:.0f}W  ·  {g['pstate']}"
            )
            self.gpu_live.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        else:
            self.gpu_live.setText("nvidia-smi not available")
            self.gpu_live.setStyleSheet(f"color:{C_TEXT3};font-size:12px;background:transparent;")

    def _apply_cpu(self):
        from lib.lll_adapter import (set_cpu_l1_tau, set_cpu_cross_loading_powerlimit,
                                      set_cpu_temperature_limit, get_cpu_longterm_powerlimit,
                                      get_cpu_shortterm_powerlimit, get_cpu_l1_tau,
                                      get_cpu_cross_loading_powerlimit, get_cpu_temperature_limit)
        pcore_mhz  = self.cpu_freq_spin.value()
        ecore_mhz  = self.ecore_freq_spin.value()
        pl1        = self.pl1_spin.value()
        pl2        = self.pl2_spin.value()
        tau        = self.tau_spin.value()
        crossload  = self.crossload_spin.value()
        cpu_temp   = self.cpu_temp_lim_spin.value()
        apply_cpu_freq(pcore_mhz)
        apply_ecore_freq(ecore_mhz)
        set_cpu_tdp(pl1, pl2)
        set_cpu_l1_tau(tau)
        set_cpu_cross_loading_powerlimit(crossload)
        set_cpu_temperature_limit(cpu_temp)
        # Read back actual values from kernel — it clamps to its own bounds
        # (e.g. TAU 19 -> 20), so the UI must reflect the real written value.
        actual_pl1 = get_cpu_longterm_powerlimit()
        actual_pl2 = get_cpu_shortterm_powerlimit()
        actual_tau = get_cpu_l1_tau()
        actual_cl  = get_cpu_cross_loading_powerlimit()
        actual_ct  = get_cpu_temperature_limit()
        self.pl1_spin.blockSignals(True); self.pl1_spin.setValue(actual_pl1 or pl1)
        self.pl1_sl.setValue(actual_pl1 or pl1); self.pl1_spin.blockSignals(False)
        self.pl2_spin.blockSignals(True); self.pl2_spin.setValue(actual_pl2 or pl2)
        self.pl2_sl.setValue(actual_pl2 or pl2); self.pl2_spin.blockSignals(False)
        if actual_tau: self.tau_spin.setValue(actual_tau)
        if actual_cl:  self.crossload_spin.setValue(actual_cl)
        if actual_ct:  self.cpu_temp_lim_spin.setValue(actual_ct)
        self._cfg.update({"cpu_max_freq_mhz": pcore_mhz,
                          "ecore_max_freq_mhz": ecore_mhz,
                          "pl1_w": actual_pl1 or pl1, "pl2_w": actual_pl2 or pl2,
                          "cpu_tau": actual_tau or tau, "cpu_crossload": actual_cl or crossload,
                          "cpu_temp_lim": actual_ct or cpu_temp})
        save_oc_config(self._cfg)
        self.cpu_status.setText(
            f"✓ P {pcore_mhz} MHz · E {ecore_mhz} MHz · PL1 {actual_pl1 or pl1}W · PL2 {actual_pl2 or pl2}W · TAU {actual_tau or tau}s")
        QTimer.singleShot(4000, lambda: self.cpu_status.setText(""))

    def _reset_cpu(self):
        from lib.lll_adapter import set_cpu_l1_tau, set_cpu_cross_loading_powerlimit, set_cpu_temperature_limit
        self.cpu_freq_spin.setValue(PCORE_RESET_MHZ)
        self.ecore_freq_spin.setValue(ECORE_RESET_MHZ)
        self.pl1_spin.setValue(55); self.pl2_spin.setValue(80)
        self.tau_spin.setValue(56); self.crossload_spin.setValue(30)
        self.cpu_temp_lim_spin.setValue(94)
        apply_cpu_freq(PCORE_RESET_MHZ)
        apply_ecore_freq(ECORE_RESET_MHZ)
        set_cpu_tdp(55, 80)
        set_cpu_l1_tau(56)
        set_cpu_cross_loading_powerlimit(30)
        set_cpu_temperature_limit(94)
        self._cfg.update({"cpu_max_freq_mhz": PCORE_RESET_MHZ,
                          "ecore_max_freq_mhz": ECORE_RESET_MHZ,
                          "pl1_w": 55, "pl2_w": 80,
                          "cpu_tau": 56, "cpu_crossload": 30,
                          "cpu_temp_lim": 94})
        save_oc_config(self._cfg)
        self.cpu_status.setText(
            f"✓ CPU reset — P {PCORE_RESET_MHZ} MHz · E {ECORE_RESET_MHZ} MHz · PL1 55W · PL2 80W")
        QTimer.singleShot(4000, lambda: self.cpu_status.setText(""))

    def _apply_gpu(self):
        from lib.lll_adapter import (set_gpu_oc_powerlimit, set_gpu_power_target_offset,
                                      set_gpu_ctgp_powerlimit, set_gpu_temperature_limit,
                                      get_gpu_oc_powerlimit, get_gpu_power_target_offset,
                                      get_gpu_ctgp_powerlimit, get_gpu_temperature_limit)
        # Clock offsets commented out — not reliable on this model
        # core = self.gpu_core_spin.value()
        # mem  = self.gpu_mem_spin.value()
        # apply_gpu_oc_full(core, mem, 0, 0, 0)
        dynboost_ppab = self.gpu_dynboost_ppab_spin.value()
        ctgp     = self.gpu_ctgp_spin.value()
        total_proc = self.gpu_total_proc_spin.value()
        gpu_temp = self.gpu_temp_spin.value()
        set_gpu_oc_powerlimit(dynboost_ppab)
        set_gpu_power_target_offset(total_proc)
        set_gpu_ctgp_powerlimit(ctgp)
        set_gpu_temperature_limit(gpu_temp)
        # Read back actual values from kernel
        actual_ppab = get_gpu_oc_powerlimit()
        actual_poff = get_gpu_power_target_offset()
        actual_ctgp = get_gpu_ctgp_powerlimit()
        actual_temp = get_gpu_temperature_limit()
        self.gpu_dynboost_ppab_spin.setValue(actual_ppab or dynboost_ppab)
        self.gpu_total_proc_spin.setValue(actual_poff or total_proc)
        self.gpu_ctgp_spin.setValue(actual_ctgp or ctgp)
        self.gpu_temp_spin.blockSignals(True)
        self.gpu_temp_spin.setValue(actual_temp or gpu_temp)
        self.gpu_temp_spin.blockSignals(False)
        core = self.gpu_core_spin.value()
        mem  = self.gpu_mem_spin.value()
        self._cfg.update({"gpu_core_offset": core, "gpu_mem_offset": mem,
                          "gpu_dynboost_ppab": actual_ppab or dynboost_ppab,
                          "gpu_ctgp": actual_ctgp or ctgp,
                          "gpu_total_proc": actual_poff or total_proc,
                          "gpu_temp_limit": actual_temp or gpu_temp})
        save_oc_config(self._cfg)
        self.gpu_status.setText(f"✓ PPAB {actual_ppab or dynboost_ppab}W  cTGP {actual_ctgp or ctgp}W  Temp {actual_temp or gpu_temp}°C")
        QTimer.singleShot(4000, lambda: self.gpu_status.setText(""))

    def _reset_gpu_oc(self):
        from lib.lll_adapter import set_gpu_oc_powerlimit, set_gpu_power_target_offset, set_gpu_ctgp_powerlimit, set_gpu_temperature_limit
        # Clock offsets commented out
        # for sp, val in [(self.gpu_core_spin, 0), (self.gpu_mem_spin, 0),
        #                 (self.gpu_pl_spin, 115), (self.gpu_temp_spin, 83),
        #                 (self.gpu_fan_spin, 0),
        for sp, val in [(self.gpu_core_spin, 0), (self.gpu_mem_spin, 0),
                        (self.gpu_dynboost_ppab_spin, 15), (self.gpu_ctgp_spin, 45),
                        (self.gpu_total_proc_spin, 30), (self.gpu_temp_spin, 87)]:
            sp.setValue(val)
        set_gpu_oc_powerlimit(15)
        set_gpu_power_target_offset(30)
        set_gpu_ctgp_powerlimit(45)
        set_gpu_temperature_limit(87)
        self._cfg.update({"gpu_core_offset": 0, "gpu_mem_offset": 0,
                          "gpu_dynboost_ppab": 15, "gpu_ctgp": 45,
                          "gpu_total_proc": 30, "gpu_temp_limit": 87})
        save_oc_config(self._cfg)
        self.gpu_status.setText("✓ GPU OC reset to defaults")
        QTimer.singleShot(3000, lambda: self.gpu_status.setText(""))

    def refresh(self, d=None):
        """Check power mode for grey-out + presets, read actual values from kernel."""
        self.check_powermode()
        try:
            from lib.lll_adapter import (get_cpu_longterm_powerlimit, get_cpu_shortterm_powerlimit,
                                          get_cpu_l1_tau, get_cpu_cross_loading_powerlimit,
                                          get_cpu_temperature_limit, get_gpu_oc_powerlimit,
                                          get_gpu_power_target_offset, get_gpu_ctgp_powerlimit,
                                          read_powermode)
            cur_pl1 = get_cpu_longterm_powerlimit()
            cur_pl2 = get_cpu_shortterm_powerlimit()
            if cur_pl1 > 0:
                self.pl1_spin.blockSignals(True); self.pl1_spin.setValue(cur_pl1)
                self.pl1_sl.setValue(cur_pl1); self.pl1_spin.blockSignals(False)
            if cur_pl2 > 0:
                self.pl2_spin.blockSignals(True); self.pl2_spin.setValue(cur_pl2)
                self.pl2_sl.setValue(cur_pl2); self.pl2_spin.blockSignals(False)
            cur_tau = get_cpu_l1_tau()
            if cur_tau > 0:
                self.tau_spin.setValue(cur_tau)
            cur_cl = get_cpu_cross_loading_powerlimit()
            if cur_cl > 0:
                self.crossload_spin.setValue(cur_cl)
            cur_ct = get_cpu_temperature_limit()
            if cur_ct > 0:
                self.cpu_temp_lim_spin.setValue(cur_ct)
            cur_ppab = get_gpu_oc_powerlimit()
            if cur_ppab > 0:
                self.gpu_dynboost_ppab_spin.setValue(cur_ppab)
            cur_poff = get_gpu_power_target_offset()
            if cur_poff > 0:
                self.gpu_total_proc_spin.setValue(cur_poff)
            cur_ctgp = get_gpu_ctgp_powerlimit()
            if cur_ctgp > 0:
                self.gpu_ctgp_spin.setValue(cur_ctgp)
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════════════════════
# FAN CURVE PAGE
# ══════════════════════════════════════════════════════════════════════════════
class FanWidget(QWidget):
    """Animated fan icon — spins faster as RPM increases."""
    def __init__(self, color: str, size: int = 64, parent=None):
        super().__init__(parent)
        self._color  = QColor(color)
        self._dim    = QColor(color)
        self._dim.setAlphaF(0.25)
        self._angle  = 0.0
        self._speed  = 0.0   # degrees per timer tick (60fps)
        self._rpm    = 0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)   # ~60 fps

    def set_rpm(self, rpm: int):
        self._rpm = rpm
        # Map RPM → degrees per frame
        # 0 RPM = 0 deg/frame,  5000 RPM = 12 deg/frame (2 full rotations/sec)
        self._speed = min(rpm / 5000 * 12.0, 14.0)

    def _tick(self):
        if self._speed > 0:
            self._angle = (self._angle + self._speed) % 360
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        cx, cy, r = s / 2, s / 2, s * 0.44

        p.translate(cx, cy)
        p.rotate(self._angle)

        # Draw 3 blades, each 120° apart
        BLADES = 3
        for i in range(BLADES):
            p.save()
            p.rotate(i * (360 / BLADES))
            # Blade: a rounded ellipse offset from center
            blade_w = r * 0.52
            blade_h = r * 0.78
            grad = __import__('PyQt6.QtGui', fromlist=['QRadialGradient']).QRadialGradient(
                0, -r * 0.35, r * 0.55)
            grad.setColorAt(0.0, self._color)
            grad.setColorAt(1.0, self._dim)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            # Offset blade away from center
            p.translate(r * 0.28, -r * 0.38)
            p.drawEllipse(
                int(-blade_w / 2), int(-blade_h / 2),
                int(blade_w), int(blade_h)
            )
            p.restore()

        # Hub circle
        hub_r = int(r * 0.22)
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(-hub_r, -hub_r, hub_r * 2, hub_r * 2)

        # Inner hub dot
        inner = max(2, int(r * 0.08))
        bg = QColor(C_BG)
        p.setBrush(bg)
        p.drawEllipse(-inner, -inner, inner * 2, inner * 2)

        p.end()


class FanPage(QWidget):
    _fan_result = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._fan_result.connect(self._on_fan_result)
        self._mode = "auto"   # "auto" or "full"
        self._build()
        self._fan_timer = QTimer(self)
        self._fan_timer.timeout.connect(self._refresh_rpm)
        self._fan_timer.start(1500)

    def _on_fan_result(self, ok: bool, msg: str):
        color = C_GREEN if ok else C_ORANGE
        self._status.setStyleSheet(
            f"color:{color};font-size:12px;font-weight:600;background:transparent;")
        self._status.setText(msg)

    def _emit(self, ok: bool, msg: str):
        self._fan_result.emit(ok, msg)

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # ── Live RPM ──────────────────────────────────────────────────────────
        rc, rl = make_card("Live Fan Speed")
        rpm_row = QHBoxLayout(); rpm_row.setSpacing(48)
        rpm_row.addStretch()
        for attr, fan_attr, label, color in [
            ("cpu_rpm_lbl", "cpu_fan_widget", "CPU Fan", C_BLUE),
            ("gpu_rpm_lbl", "gpu_fan_widget", "GPU Fan", C_RED),
        ]:
            col = QVBoxLayout(); col.setSpacing(6)
            col.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            fan_w = FanWidget(color, size=64)
            setattr(self, fan_attr, fan_w)
            fan_w_wrap = QHBoxLayout()
            fan_w_wrap.addStretch(); fan_w_wrap.addWidget(fan_w); fan_w_wrap.addStretch()

            lbl = QLabel("— RPM")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color:{color};font-size:22px;font-weight:600;background:transparent;")
            name = QLabel(label)
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
            setattr(self, attr, lbl)
            col.addLayout(fan_w_wrap); col.addWidget(lbl); col.addWidget(name)
            rpm_row.addLayout(col)
        rpm_row.addStretch()
        rl.addLayout(rpm_row)
        self.fan_mode_badge = QLabel("Mode: Auto")
        self.fan_mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fan_mode_badge.setStyleSheet(
            f"color:{C_TEXT3};font-size:12px;background:transparent;")
        rl.addWidget(self.fan_mode_badge)
        root.addWidget(rc)

        # ── Fan Control ───────────────────────────────────────────────────────
        cc, cl = make_card("Fan Control")

        # Info note - enhanced LLL status
        lll_status = get_lll_status()
        lll_available = is_lll_available()
        info = _fan_hwmon_info()
        fs_ok = FAN_FULLSPEED.exists()
        curve_text = ""
        if lll_available:
            curve_text = read_fancurve_from_hw()
        has_curve = curve_text and "fan curve points size:" in curve_text
        
        note_lines = []
        if lll_available:
            note_lines.append(get_fan_status_message())
            note_lines.append(f"✓  fan_fullspeed: {FAN_FULLSPEED}")
            if has_curve:
                note_lines.append(f"✓  Custom fan curve: available")
            note_lines.append("")
            note_lines.append("Use Power Mode (Quiet / Balanced / Performance)")
            note_lines.append("or custom fan curve (LLL required).")
        elif lll_status["module_loaded"]:
            note_lines.append("⚠  LLL module loaded but device NOT bound")
            note_lines.append(f"  Kernel: {Path('/proc/sys/kernel/osrelease').read_text().split()[0]}")
            note_lines.append("")
            note_lines.append("The module loaded but no hwmon device was created.")
            note_lines.append("This usually means kernel 7.x is not supported yet.")
            note_lines.append("")
            note_lines.append("Try force loading:")
            note_lines.append("  sudo modprobe -r legion_laptop")
            note_lines.append("  sudo modprobe legion_laptop force=1")
            note_lines.append("")
            note_lines.append("OR downgrade to kernel 6.x:")
            note_lines.append("  sudo pacman -S linux-cachyos#6.19.2")
        else:
            note_lines.append("⚠  LLL not loaded — limited fan control")
            note_lines.append("")
            note_lines.append("For full fan control, install lenovolegionlinux:")
            note_lines.append("  sudo pacman -S cachyos/lenovolegionlinux")
            note_lines.append("  sudo modprobe legion_laptop")
            note_lines.append("")
            note_lines.append("OR if module loads but no device:")
            note_lines.append("  sudo modprobe legion_laptop force=1")
        
        note = QLabel("\n".join(note_lines))
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        cl.addWidget(note)
        cl.addWidget(make_div())

        # Two big buttons: Auto and Full Speed
        btn_row = QHBoxLayout(); btn_row.setSpacing(12)

        self._auto_btn = QPushButton("🌡️  Auto / Dynamic")
        self._auto_btn.setCheckable(True); self._auto_btn.setChecked(True)
        self._auto_btn.setFixedHeight(48)
        self._auto_btn.setStyleSheet(
            f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};"
            f"border:1px solid {C_BORDER};border-radius:8px;"
            f"font-size:13px;font-weight:600;}}"
            f"QPushButton:checked{{background:transparent;color:{C_GREEN};"
            f"border:2px solid {C_GREEN};}}"
            f"QPushButton:hover:!checked{{border:1px solid #555;color:{C_TEXT};}}"
        )
        self._auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_btn.clicked.connect(lambda: self._set_mode("auto"))

        self._full_btn = QPushButton("🌀  Full Speed")
        self._full_btn.setCheckable(True); self._full_btn.setChecked(False)
        self._full_btn.setFixedHeight(48)
        self._full_btn.setStyleSheet(
            f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};"
            f"border:1px solid {C_BORDER};border-radius:8px;"
            f"font-size:13px;font-weight:600;}}"
            f"QPushButton:checked{{background:transparent;color:{C_RED};"
            f"border:2px solid {C_RED};}}"
            f"QPushButton:hover:!checked{{border:1px solid #555;color:{C_TEXT};}}"
        )
        self._full_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._full_btn.clicked.connect(lambda: self._set_mode("full"))

        # Lock Fan Controller button
        lock_enabled = get_fan_lock_status()
        self._lockfan_btn = QPushButton("🔒  Lock")
        self._lockfan_btn.setCheckable(True)
        self._lockfan_btn.setChecked(lock_enabled)
        self._lockfan_btn.setFixedHeight(48)
        self._lockfan_btn.setStyleSheet(
            f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};"
            f"border:1px solid {C_BORDER};border-radius:8px;"
            f"font-size:13px;font-weight:600;}}"
            f"QPushButton:checked{{background:{C_RED};color:{C_BG};}}"
            f"QPushButton:hover:!checked{{border:1px solid {C_RED};}}"
        )
        self._lockfan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lockfan_btn.clicked.connect(lambda: self._apply_lockfan(self._lockfan_btn.isChecked()))

        # Mini Fan Curve button
        mini_enabled = get_minifancurve_status()
        self._minifan_btn = QPushButton("🌡️  Mini")
        self._minifan_btn.setCheckable(True)
        self._minifan_btn.setChecked(mini_enabled)
        self._minifan_btn.setFixedHeight(48)
        self._minifan_btn.setStyleSheet(
            f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};"
            f"border:1px solid {C_BORDER};border-radius:8px;"
            f"font-size:13px;font-weight:600;}}"
            f"QPushButton:checked{{background:{C_GREEN};color:{C_BG};}}"
            f"QPushButton:hover:!checked{{border:1px solid {C_GREEN};}}"
        )
        self._minifan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minifan_btn.clicked.connect(lambda: self._apply_minifan(self._minifan_btn.isChecked()))

        btn_row.addWidget(self._auto_btn); btn_row.addWidget(self._full_btn)
        btn_row.addWidget(self._lockfan_btn); btn_row.addWidget(self._minifan_btn)
        cl.addLayout(btn_row)

        self._mode_desc = QLabel(
            "Firmware controls fans based on CPU/GPU temperature. Recommended.")
        self._mode_desc.setStyleSheet(
            f"color:{C_TEXT2};font-size:12px;background:transparent;")
        self._mode_desc.setWordWrap(True)
        cl.addWidget(self._mode_desc)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet(
            f"color:{C_GREEN};font-size:12px;background:transparent;")
        cl.addWidget(self._status)
        
        # ── 10-Point Fan Curve Editor ──────────────────────────────────────────────────
        if has_curve and lll_available:
            fce, fcel = make_card("🎛️  Custom Fan Curve Editor")
            
            # Instructions
            fcel.addWidget(_mk_lbl(
                "Edit each point: temperature (°C) where fan speed changes.\n"
                "PWM = fan speed (0-255), Accel/Decel = speed change rate.",
                C_TEXT2, size=11))
            
            # Create table for 10 points
            curve_scroll = QScrollArea()
            curve_scroll.setWidgetResizable(True)
            curve_scroll.setFixedHeight(280)
            
            curve_widget = QWidget()
            curve_layout = QVBoxLayout()
            
            # Headers
            header = QLabel("Pt | CPU Temp | Fan1 PWM | Fan2 PWM | Accel | Decel")
            header.setStyleSheet(f"color:{C_ACCENT};font-weight:600;font-size:12px;")
            curve_layout.addWidget(header)
            
            # Parse current curve
            current_points = parse_fancurve(curve_text) if curve_text else []
            
            # Create 10 input rows
            self._curve_points = []
            for i in range(10):
                row = QHBoxLayout()
                
                # Point label
                lbl = QLabel(f"{i+1}")
                lbl.setFixedWidth(25)
                row.addWidget(lbl)
                
                # CPU Temp (threshold to switch to this fan speed)
                temp_spin = QSpinBox()
                temp_spin.setRange(FAN_TEMP_MIN_C, FAN_TEMP_MAX_C)
                temp_spin.setValue(current_points[i].get("cpu_max", 50) if i < len(current_points) else 40 + i*5)
                temp_spin.setFixedWidth(60)
                row.addWidget(QLabel("°C")); row.addWidget(temp_spin)
                row.addStretch()
                
                # Fan1 PWM
                pwm1_spin = QSpinBox()
                pwm1_spin.setRange(PWM_MIN, PWM_MAX)
                pwm1_spin.setValue(current_points[i].get("fan1_pwm", 50 + i*20) if i < len(current_points) else min(255, 50 + i*20))
                pwm1_spin.setFixedWidth(60)
                row.addWidget(QLabel("F1")); row.addWidget(pwm1_spin)
                row.addStretch()
                
                # Fan2 PWM  
                pwm2_spin = QSpinBox()
                pwm2_spin.setRange(PWM_MIN, PWM_MAX)
                pwm2_spin.setValue(current_points[i].get("fan2_pwm", 50 + i*20) if i < len(current_points) else min(255, 50 + i*20))
                pwm2_spin.setFixedWidth(60)
                row.addWidget(QLabel("F2")); row.addWidget(pwm2_spin)
                row.addStretch()
                
                # Accel
                accel_spin = QSpinBox()
                accel_spin.setRange(FAN_RAMP_MIN, FAN_RAMP_MAX)
                accel_spin.setValue(current_points[i].get("accel", 5) if i < len(current_points) else 5)
                accel_spin.setFixedWidth(45)
                row.addWidget(QLabel("Acc")); row.addWidget(accel_spin)
                
                # Decel
                decel_spin = QSpinBox()
                decel_spin.setRange(FAN_RAMP_MIN, FAN_RAMP_MAX)
                decel_spin.setValue(current_points[i].get("decel", 5) if i < len(current_points) else 5)
                decel_spin.setFixedWidth(45)
                row.addWidget(QLabel("Dec")); row.addWidget(decel_spin)
                
                self._curve_points.append({
                    "temp": temp_spin,
                    "pwm1": pwm1_spin,
                    "pwm2": pwm2_spin,
                    "accel": accel_spin,
                    "decel": decel_spin,
                })
                curve_layout.addLayout(row)
            
            # Buttons for save/load/apply
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)
            
            apply_btn = QPushButton("💾  Apply to Hardware")
            apply_btn.setStyleSheet(f"background:{C_ACCENT};color:{C_BG};border-radius:6px;padding:8px;")
            apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            apply_btn.clicked.connect(self._apply_fan_curve_editor)
            btn_row.addWidget(apply_btn)
            
            save_preset_btn = QPushButton("💾  Save Preset")
            save_preset_btn.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;padding:8px;")
            save_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_preset_btn.clicked.connect(lambda: self._save_fan_preset("custom"))
            btn_row.addWidget(save_preset_btn)
            
            load_preset_btn = QPushButton("📂  Load Preset")
            load_preset_btn.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;padding:8px;")
            load_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            load_preset_btn.clicked.connect(lambda: self._load_fan_preset("custom"))
            btn_row.addWidget(load_preset_btn)
            
            curve_layout.addLayout(btn_row)
            curve_widget.setLayout(curve_layout)
            curve_scroll.setWidget(curve_widget)
            fcel.addWidget(curve_scroll)
            
            # Store reference to hide/show based on fan mode
            self._fancurve_editor = fce
            self._fancurve_editor.setVisible(False)  # Hidden by default (use Auto mode)
            
            root.addWidget(fce)
            root.addWidget(make_div())

        root.addWidget(cc)

        # ── Info card ─────────────────────────────────────────────────────────
        ic, il = make_card("ℹ️  Fan Curve Control")
        info_text = QLabel(
            "To adjust fan aggressiveness, change your Power Mode:\n\n"
            "🔵  Quiet          —  Minimal fan noise, lower temps acceptable\n"
            "⚪  Balanced      —  Balanced fan curve for everyday use\n"
            "🔴  Performance  —  Aggressive cooling for sustained loads\n"
            "🩷  Custom        —  Maximum fan speed, loudest\n\n"
            "Each profile has its own firmware-defined fan curve baked in."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        il.addWidget(info_text)
        root.addWidget(ic)

        # ── ThinkPad fan levels (only on ThinkPad) ────────────────────────────
        if HW.get("tp_fan_control"):
            tfc, tfl = make_card("🌀  ThinkPad Fan Control")
            tfl.addWidget(_mk_lbl(
                "ThinkPad fan levels via /proc/acpi/ibm/fan.\n"
                "Level 0 = off  ·  1–7 = increasing speed  ·  Auto = firmware control",
                C_TEXT2, size=11))
            tfl.addWidget(make_div())

            # Read current level
            def _get_tp_fan() -> str:
                try:
                    txt = Path("/proc/acpi/ibm/fan").read_text()
                    for line in txt.splitlines():
                        if line.startswith("level:"): return line.split(":")[1].strip()
                except: pass
                return "auto"

            level_row = QHBoxLayout(); level_row.setSpacing(12)
            lv_lbl = QLabel("Fan Level:")
            lv_lbl.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
            self._tp_fan_combo = QComboBox()
            self._tp_fan_combo.setStyleSheet(combo_style())
            self._tp_fan_combo.setFixedHeight(34)
            levels = ["auto", "0", "1", "2", "3", "4", "5", "6", "7", "disengaged"]
            level_labels = {
                "auto": "Auto (firmware)", "0": "0 — Off",
                "1": "1 — Very quiet", "2": "2 — Quiet",
                "3": "3 — Low", "4": "4 — Medium",
                "5": "5 — High", "6": "6 — Very high",
                "7": "7 — Maximum", "disengaged": "Disengaged (max RPM)"
            }
            cur_lv = _get_tp_fan()
            for lv in levels:
                self._tp_fan_combo.addItem(level_labels.get(lv, lv), lv)
            cur_idx = levels.index(cur_lv) if cur_lv in levels else 0
            self._tp_fan_combo.setCurrentIndex(cur_idx)
            level_row.addWidget(lv_lbl); level_row.addWidget(self._tp_fan_combo); level_row.addStretch()
            tfl.addLayout(level_row)

            tp_fan_apply = QPushButton("Apply Fan Level")
            tp_fan_apply.setFixedHeight(32)
            tp_fan_apply.setStyleSheet(
                f"background:{C_ACCENT};color:#fff;border:none;"
                f"border-radius:6px;font-size:12px;padding:0 16px;")
            tp_fan_apply.setCursor(Qt.CursorShape.PointingHandCursor)
            tp_fan_apply.clicked.connect(self._apply_tp_fan)
            self._tp_fan_status = QLabel("")
            self._tp_fan_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
            tp_btn_row = QHBoxLayout()
            tp_btn_row.addWidget(tp_fan_apply); tp_btn_row.addWidget(self._tp_fan_status); tp_btn_row.addStretch()
            tfl.addLayout(tp_btn_row)
            root.addWidget(tfc)

        root.addStretch()
        self._refresh_rpm()

    def _apply_gsync(self, enable: bool):
        """Apply G-Sync/Hybrid mode toggle."""
        ok, msg = set_gsync(enable)
        if ok:
            self._gsync_btn.setText("🔄  G-Sync  ✓" if enable else "🔄  G-Sync  ○")
            send_notif("G-Sync", msg, "display")
        else:
            send_notif("G-Sync Error", msg, "dialog-error")

    def _apply_lockfan(self, lock: bool):
        """Apply fan lock toggle."""
        ok, msg = set_fan_lock(lock)
        if ok:
            send_notif("Fan Controller", msg, "computer")
        else:
            send_notif("Fan Lock Error", msg, "dialog-error")

    def _apply_minifan(self, enable: bool):
        """Apply mini fan curve toggle."""
        ok, msg = set_minifancurve(enable)
        if ok:
            send_notif("Mini Fan Curve", msg, "computer")
        else:
            send_notif("Mini Fan Error", msg, "dialog-error")

    def _apply_fan_curve_editor(self):
        """Apply the custom fan curve from the editor."""
        points = []
        for pt in self._curve_points:
            points.append({
                "fan1_pwm": pt["pwm1"].value(),
                "fan2_pwm": pt["pwm2"].value(),
                "cpu_temp": pt["temp"].value(),
                "accel": pt["accel"].value(),
                "decel": pt["decel"].value(),
            })
        
        ok, msg = write_fancurve_to_hw(points)
        if ok:
            self._status.setText(f"✓  {msg}")
            send_notif("Fan Curve", msg, "computer")
        else:
            self._status.setText(f"✗  {msg}")
            send_notif("Fan Curve Error", msg, "dialog-error")

    def _save_fan_preset(self, name: str):
        """Save current fan curve to a preset file."""
        points = []
        for pt in self._curve_points:
            points.append({
                "fan1_pwm": pt["pwm1"].value(),
                "fan2_pwm": pt["pwm2"].value(),
                "cpu_temp": pt["temp"].value(),
                "accel": pt["accel"].value(),
                "decel": pt["decel"].value(),
            })
        
        if save_fancurve_to_file(points, name):
            send_notif("Fan Curve", f"Saved preset: {name}", "computer")
        else:
            send_notif("Save Error", "Failed to save preset", "dialog-error")

    def _load_fan_preset(self, name: str):
        """Load a fan curve preset into the editor."""
        points = load_fancurve_from_file(name)
        if not points:
            send_notif("Load Error", f"No preset found: {name}", "dialog-error")
            return
        
        # Update the UI
        for i, pt in enumerate(points[:10]):
            if i < len(self._curve_points):
                self._curve_points[i]["temp"].setValue(pt.get("cpu_temp", 50))
                self._curve_points[i]["pwm1"].setValue(pt.get("fan1_pwm", 100))
                self._curve_points[i]["pwm2"].setValue(pt.get("fan2_pwm", 100))
                self._curve_points[i]["accel"].setValue(pt.get("accel", 5))
                self._curve_points[i]["decel"].setValue(pt.get("decel", 5))
        
        send_notif("Fan Curve", f"Loaded preset: {name}", "computer")

    def _apply_tp_fan(self):
        level = self._tp_fan_combo.currentData()
        def _do():
            try:
                r = subprocess.run(
                    ["pkexec", "sh", "-c",
                     f"echo 'level {level}' > /proc/acpi/ibm/fan"],
                    capture_output=True, text=True, timeout=8
                )
                if r.returncode == 0:
                    self._tp_fan_status.setText(f"✓  Fan level → {level}")
                    send_notif("ThinkPad Fan", f"Fan level set to {level}", "computer")
                else:
                    self._tp_fan_status.setText(f"✗  {r.stderr.strip()[:80]}")
            except Exception as e:
                self._tp_fan_status.setText(f"✗  {e}")
        threading.Thread(target=_do, daemon=True).start()

    def _set_mode(self, mode: str):
        self._mode = mode
        self._auto_btn.setChecked(mode == "auto")
        self._full_btn.setChecked(mode == "full")
        self._mode_desc.setText(
            "Firmware controls fans based on CPU/GPU temperature. Recommended."
            if mode == "auto" else
            "Both fans locked to 100% — maximum cooling, louder."
        )
        
        # Show/hide fan curve editor based on mode
        if hasattr(self, '_fancurve_editor'):
            self._fancurve_editor.setVisible(mode != "auto")
        
        self._on_fan_result(False, f"⏳  Applying…")

        def _do():
            if mode == "auto":
                ok, msg = _write_fan_auto()
                self._emit(ok, "✓  Auto fan control active" if ok else f"✗  {msg}")
            else:
                ok, msg = _write_fan_fullspeed(True)
                self._emit(ok, "✓  Full speed active" if ok else f"✗  {msg}")
        threading.Thread(target=_do, daemon=True).start()

    def _refresh_rpm(self):
        rpm1, rpm2 = get_fan_rpm()
        # Update animated fan widgets
        self.cpu_fan_widget.set_rpm(rpm1)
        self.gpu_fan_widget.set_rpm(rpm2)
        # Update labels
        self.cpu_rpm_lbl.setText(f"{rpm1:,}" if rpm1 > 0 else "—")
        self.gpu_rpm_lbl.setText(f"{rpm2:,}" if rpm2 > 0 else "—")
        mode_label = "Full Speed" if self._mode == "full" else "Auto"
        self.fan_mode_badge.setText(f"Mode: {mode_label}")
        for lbl, rpm, base_col in [
            (self.cpu_rpm_lbl, rpm1, C_BLUE),
            (self.gpu_rpm_lbl, rpm2, C_RED),
        ]:
            c = C_RED if rpm > 5000 else C_ORANGE if rpm > 2500 else base_col
            lbl.setStyleSheet(
                f"color:{c};font-size:22px;font-weight:600;background:transparent;")

    def refresh(self, d=None):
        self._refresh_rpm()

# ══════════════════════════════════════════════════════════════════════════════
class ActionsPage(QWidget):

    def refresh(self, d=None):
        self._refresh_rpm()

# ══════════════════════════════════════════════════════════════════════════════
        color = C_GREEN if ok else C_ORANGE
        self._status.setStyleSheet(
            f"color:{color};font-size:12px;font-weight:600;background:transparent;")
        self._status.setText(msg)

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        # ── Driver status banner ──────────────────────────────────────────────
        info = _fan_hwmon_info()
        fc, fl = make_card("Fan Control")
        if info["found"]:
            has_pwm = info["pwm1"] or info["pwm2"]
            has_en  = info["pwm1_enable"] or info["pwm2_enable"]
            fs_ok   = FAN_FULLSPEED.exists()
            lines = [
                f"✓  legion_hwmon found: {info['path']}",
                f"   PWM files: {'pwm1 pwm2' if has_pwm else '— not available (read-only RPM only)'}",
                f"   PWM enable: {'pwm1_enable pwm2_enable' if has_en else '— not available'}",
                f"   fan_fullspeed: {'✓' if fs_ok else '✗  not found'} {FAN_FULLSPEED}",
            ]
            if not has_pwm:
                lines.append("")
                lines.append("⚠  Manual speed via PWM not available on this driver version.")
                lines.append("   Auto / Full Speed still work. Presets use Full Speed toggle.")
            status_lbl = QLabel("\n".join(lines))
            status_lbl.setStyleSheet(
                f"color:{C_TEXT2};font-size:10px;font-family:monospace;background:transparent;")
        else:
            status_lbl = QLabel(
                "⚠  legion_hwmon not found.\n"
                "Make sure lenovo_legion_laptop module is loaded:\n"
                "sudo modprobe lenovo_legion_laptop")
            status_lbl.setStyleSheet(f"color:{C_ORANGE};font-size:12px;background:transparent;")
        status_lbl.setWordWrap(True)
        fl.addWidget(status_lbl)
        root.addWidget(fc)

        # ── Live RPM ──────────────────────────────────────────────────────────
        rc, rl = make_card("Live Fan Speed")
        rpm_row = QHBoxLayout(); rpm_row.setSpacing(32)
        for attr, label, color in [
            ("cpu_rpm_lbl","CPU Fan",C_BLUE),
            ("gpu_rpm_lbl","GPU Fan",C_RED),
        ]:
            col = QVBoxLayout(); col.setSpacing(4)
            icon = QLabel("🌀"); icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet("font-size:22px;background:transparent;")
            lbl = QLabel("— RPM"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{color};font-size:20px;font-weight:600;background:transparent;")
            name = QLabel(label); name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
            setattr(self, attr, lbl)
            col.addWidget(icon); col.addWidget(lbl); col.addWidget(name)
            rpm_row.addLayout(col)
        rl.addLayout(rpm_row)
        self.fan_mode_badge = QLabel("Mode: Auto")
        self.fan_mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fan_mode_badge.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        rl.addWidget(self.fan_mode_badge)
        root.addWidget(rc)

        # ── Mode selector ─────────────────────────────────────────────────────
        mc, ml = make_card("Fan Control Mode")
        mode_row = QHBoxLayout(); mode_row.setSpacing(8)
        self._mode_btns = {}
        for mode_name, mode_key, color in [
            ("Auto / Dynamic", "auto",   C_GREEN),
            ("Manual Speed",   "manual", C_ORANGE),
            ("Full Speed",     "full",   C_RED),
        ]:
            btn = QPushButton(mode_name)
            btn.setCheckable(True); btn.setFixedHeight(36)
            btn.setChecked(self._cfg.get("mode","auto") == mode_key)
            btn.setStyleSheet(
                f"QPushButton{{background:{C_CARD2};color:{C_TEXT2};"
                f"border:1px solid {C_BORDER};border-radius:6px;"
                f"font-size:12px;font-weight:600;padding:0 8px;}}"
                f"QPushButton:checked{{background:transparent;color:{color};"
                f"border:2px solid {color};}}"
                f"QPushButton:hover:!checked{{border:1px solid #555;color:{C_TEXT};}}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda chk, k=mode_key: self._set_mode(k))
            self._mode_btns[mode_key] = btn; mode_row.addWidget(btn)
        ml.addLayout(mode_row)
        self._mode_desc = QLabel(self._mode_hint(self._cfg.get("mode","auto")))
        self._mode_desc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        self._mode_desc.setWordWrap(True)
        ml.addWidget(self._mode_desc)
        root.addWidget(mc)

        # ── Presets ───────────────────────────────────────────────────────────
        pc, pl = make_card("Fan Presets")
        pl.addWidget(_mk_lbl(
            "Quick presets. If manual PWM is available, sets exact speed.\n"
            "Otherwise maps to Auto or Full Speed.", C_TEXT2, size=12))
        preset_wrap = QWidget()
        preset_wrap.setStyleSheet("background:transparent;")
        preset_lay = QVBoxLayout(preset_wrap)
        preset_lay.setContentsMargins(0, 8, 0, 0)
        preset_lay.setSpacing(8)
        preset_list = list(FAN_PRESETS.items())
        for row_i in range(0, len(preset_list), 3):
            row = QHBoxLayout()
            row.setSpacing(8)
            for col_i in range(3):
                idx = row_i + col_i
                if idx >= len(preset_list):
                    row.addStretch()
                    continue
                pname, (cpu_pct, gpu_pct) = preset_list[idx]
                color = [C_BLUE, C_GREEN, C_ORANGE, C_RED, "#ff0000"][idx % 5]
                btn = QPushButton(f"{pname}  —  {cpu_pct}% CPU / {gpu_pct}% GPU")
                btn.setFixedHeight(42)
                btn.setStyleSheet(
                    f"QPushButton{{background:{C_CARD2};color:{C_TEXT};"
                    f"border:1px solid {C_BORDER};border-radius:8px;font-size:12px;font-weight:500;"
                    f"border-left:3px solid {color};padding-left:12px;}}"
                    f"QPushButton:hover{{background:{color}22;border-color:{color};}}"
                    f"QPushButton:pressed{{background:{color}44;}}"
                )
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda chk, pn=pname, cp=cpu_pct, gp=gpu_pct:
                                    self._apply_preset(pn, cp, gp))
                row.addWidget(btn, 1)
            preset_lay.addLayout(row)
        pl.addWidget(preset_wrap)
        root.addWidget(pc)

        # ── Manual sliders ────────────────────────────────────────────────────
        self._manual_card, ml2 = make_card("Manual Fan Speed")
        ml2.addWidget(_mk_lbl(
            "Set exact fan speed. Requires writable PWM files in legion_hwmon.", C_TEXT2, size=11))

        def _slider_row(label, color, default):
            row = QHBoxLayout(); row.setSpacing(12)
            lb = QLabel(label); lb.setFixedWidth(70)
            lb.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;background:transparent;")
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(0,100); sl.setValue(default)
            sl.setStyleSheet(
                f"QSlider::groove:horizontal{{background:{C_BORDER};height:8px;border-radius:4px;}}"
                f"QSlider::handle:horizontal{{background:{color};width:18px;height:18px;"
                f"border-radius:9px;margin:-5px 0;}}"
                f"QSlider::sub-page:horizontal{{background:{color};border-radius:4px;}}"
            )
            vl = QLabel(f"{default}%"); vl.setFixedWidth(40)
            vl.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;background:transparent;")
            sl.valueChanged.connect(lambda v, l=vl: l.setText(f"{v}%"))
            row.addWidget(lb); row.addWidget(sl); row.addWidget(vl)
            return row, sl

        cpu_row, self.cpu_fan_sl = _slider_row("CPU Fan", C_BLUE,  self._cfg.get("cpu_pct",50))
        gpu_row, self.gpu_fan_sl = _slider_row("GPU Fan", C_RED,   self._cfg.get("gpu_pct",50))
        ml2.addLayout(cpu_row); ml2.addLayout(gpu_row)

        apply_btn = QPushButton("Apply Manual Speed")
        apply_btn.setFixedHeight(34)
        apply_btn.setStyleSheet(
            f"background:{C_ORANGE};color:#000;font-weight:600;"
            f"border:none;border-radius:6px;font-size:12px;padding:0 16px;")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_manual)
        btn_rl = QHBoxLayout(); btn_rl.addWidget(apply_btn); btn_rl.addStretch()
        ml2.addLayout(btn_rl)
        root.addWidget(self._manual_card)

        # Status label
        self._fan_status = QLabel("")
        self._fan_status.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        root.addWidget(self._fan_status)
        root.addStretch()

        self._update_manual_visibility(self._cfg.get("mode","auto"))
        self._refresh_rpm()

    def _mode_hint(self, mode: str) -> str:
        return {
            "auto":   "Firmware controls fans via thermal curves. Recommended for daily use.",
            "manual": "Set exact fan speed. Uses PWM files in legion_hwmon.",
            "full":   "Both fans locked to 100% — loudest, maximum cooling.",
        }.get(mode, "")

    def _set_mode(self, mode: str):
        for k, b in self._mode_btns.items():
            b.setChecked(k == mode)
        self._mode_desc.setText(self._mode_hint(mode))
        
        # Show/hide fan curve editor based on mode
        # Editor visible for manual or full mode (NOT auto)
        if hasattr(self, '_fancurve_editor'):
            self._fancurve_editor.setVisible(mode in ("manual", "full"))
        
        self._cfg["mode"] = mode
        save_fan_config(self._cfg)
        self._update_manual_visibility(mode)
        self._on_fan_result(False, f"⏳  Applying {mode} mode…")
        def _do():
            if mode == "auto":
                ok, msg = _write_fan_auto()
                self._emit(ok, "✓  Auto fan control active" if ok else f"✗  {msg}")
            elif mode == "full":
                ok, msg = _write_fan_fullspeed(True)
                self._emit(ok, "✓  Full speed active" if ok else f"✗  {msg}")
            elif mode == "manual":
                self._emit(True, "↑  Set speed with sliders above → Apply")
        threading.Thread(target=_do, daemon=True).start()

    def _update_manual_visibility(self, mode: str):
        self._manual_card.setVisible(mode == "manual")

    def _apply_preset(self, name: str, cpu_pct: int, gpu_pct: int):
        self.cpu_fan_sl.setValue(cpu_pct)
        self.gpu_fan_sl.setValue(gpu_pct)
        for k, b in self._mode_btns.items():
            b.setChecked(k == "manual")
        self._update_manual_visibility("manual")
        self._cfg.update({"mode":"manual","cpu_pct":cpu_pct,"gpu_pct":gpu_pct,"preset":name})
        save_fan_config(self._cfg)
        self._on_fan_result(False, f"⏳  Applying {name}…")
        def _do():
            ok, msg = _write_fan_pwm(cpu_pct, gpu_pct)
            if ok:
                self._emit(True, f"✓  {name} — CPU {cpu_pct}%  GPU {gpu_pct}%")
            else:
                if cpu_pct >= 90:
                    ok2, msg2 = _write_fan_fullspeed(True)
                    self._emit(ok2, f"✓  {name} (full speed)" if ok2 else f"✗  {msg2}")
                else:
                    ok2, msg2 = _write_fan_auto()
                    self._emit(ok2,
                        f"✓  {name} (auto — PWM not available)" if ok2 else f"✗  {msg2}")
        threading.Thread(target=_do, daemon=True).start()

    def _apply_manual(self):
        cpu_pct = self.cpu_fan_sl.value()
        gpu_pct = self.gpu_fan_sl.value()
        self._cfg.update({"mode":"manual","cpu_pct":cpu_pct,"gpu_pct":gpu_pct})
        save_fan_config(self._cfg)
        self._on_fan_result(False, f"⏳  Applying CPU {cpu_pct}%  GPU {gpu_pct}%…")
        def _do():
            ok, msg = _write_fan_pwm(cpu_pct, gpu_pct)
            self._emit(ok, f"✓  CPU {cpu_pct}%  GPU {gpu_pct}%" if ok else f"✗  {msg}")
        threading.Thread(target=_do, daemon=True).start()

    def _refresh_rpm(self):
        rpm1, rpm2 = get_fan_rpm()
        self.cpu_rpm_lbl.setText(f"{rpm1:,}" if rpm1 > 0 else "—")
        self.gpu_rpm_lbl.setText(f"{rpm2:,}" if rpm2 > 0 else "—")
        mode = self._cfg.get("mode","auto")
        mode_labels = {"auto":"Auto","manual":"Manual","full":"Full Speed"}
        self.fan_mode_badge.setText(f"Mode: {mode_labels.get(mode, mode)}")
        for lbl, rpm, col in [(self.cpu_rpm_lbl,rpm1,C_BLUE),(self.gpu_rpm_lbl,rpm2,C_RED)]:
            c = C_RED if rpm>5000 else C_ORANGE if rpm>2500 else col
            lbl.setStyleSheet(
                f"color:{c};font-size:20px;font-weight:600;background:transparent;")

    def refresh(self, d=None):
        self._refresh_rpm()
# ══════════════════════════════════════════════════════════════════════════════
class ActionsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._actions = load_actions()
        self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setStyleSheet(f"background:{C_BG};")
        root = QVBoxLayout(inner); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)
        scroll.setWidget(inner)

        ac, al = make_card("Automatic Power Mode Switching")
        adesc = QLabel(
            "Automatically switch power profile when AC adapter is plugged or unplugged. "
            "The background sampler applies changes immediately — no separate daemon needed."
        )
        adesc.setWordWrap(True)
        adesc.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        al.addWidget(adesc); al.addWidget(make_div())

        sw = QHBoxLayout()
        swc = QVBoxLayout(); swc.setSpacing(2)
        st = QLabel("Enable Auto Switching")
        st.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;background:transparent;")
        sd = QLabel("Automatically change profile when charger is plugged/unplugged.")
        sd.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        swc.addWidget(st); swc.addWidget(sd)
        sw.addLayout(swc); sw.addStretch()
        self.auto_toggle = ToggleSwitch(
            path=None, on_change=self._on_auto,
            read_val="1" if self._actions.get("auto_switch") else "0"
        )
        sw.addWidget(self.auto_toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        al.addLayout(sw); al.addWidget(make_div())

        for attr, label, key in [
            ("ac_combo",  "On AC Connect  →", "on_ac"),
            ("bat_combo", "On Battery      →", "on_battery"),
        ]:
            row = QHBoxLayout(); row.setSpacing(16)
            lbl = QLabel(label); lbl.setFixedWidth(180)
            lbl.setStyleSheet(f"color:{C_TEXT};font-size:13px;background:transparent;")
            row.addWidget(lbl)
            combo = QComboBox(); combo.setStyleSheet(combo_style())
            cur = self._actions.get(key,"balanced")
            for p in PROFILES: combo.addItem(PROFILE_LABELS[p], p)
            if cur in PROFILES: combo.setCurrentIndex(PROFILES.index(cur))
            combo.currentIndexChanged.connect(self._save)
            setattr(self, attr, combo); row.addWidget(combo); row.addStretch()
            al.addLayout(row)

        test_row = QHBoxLayout()
        test_btn = QPushButton("Test Now — Apply correct profile")
        test_btn.setStyleSheet(f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
                               f"border-radius:6px;padding:8px 16px;font-size:12px;")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(self._test_now)
        test_row.addWidget(test_btn); test_row.addStretch()
        al.addLayout(test_row)

        self.save_lbl = QLabel("")
        self.save_lbl.setStyleSheet(f"color:{C_GREEN};font-size:12px;background:transparent;")
        al.addWidget(self.save_lbl); root.addWidget(ac)

        cs, csl = make_card("Current Status")
        self.ac_status   = InfoRow("Power Source","—"); csl.addWidget(self.ac_status)
        self.prof_status = InfoRow("Active Profile","—"); csl.addWidget(self.prof_status)
        self.auto_status = InfoRow("Auto Switch","—"); csl.addWidget(self.auto_status)
        root.addWidget(cs)

        nc, nl = make_card("ℹ️  How It Works")
        note = QLabel(
            "The background thread checks AC state every second. "
            "When power source changes and Auto Switch is ON, the profile is applied immediately "
            "and a desktop notification is shown.\n\n"
            "Config: ~/.config/legion-toolkit/actions.json"
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{C_TEXT2};font-size:12px;background:transparent;")
        nl.addWidget(note); root.addWidget(nc)
        root.addStretch()

    def _on_auto(self, val):
        self._actions["auto_switch"] = val; self._save_data()

    def _save(self):
        self._actions["on_ac"]       = self.ac_combo.currentData()
        self._actions["on_battery"]  = self.bat_combo.currentData()
        self._actions["auto_switch"] = self.auto_toggle.isChecked()
        self._save_data()

    def _save_data(self):
        save_actions(self._actions)
        self.save_lbl.setText("✓ Saved")
        QTimer.singleShot(2000, lambda: self.save_lbl.setText(""))

    def _test_now(self):
        apply_actions_now()
        self.save_lbl.setText("✓ Profile applied")
        QTimer.singleShot(2000, lambda: self.save_lbl.setText(""))

    def refresh(self, d=None):
        if d:
            ac      = d.get("ac", False)
            profile = d.get("profile", "balanced")
        else:
            ac      = get_ac_connected()
            profile = lll.read_powermode()
        self.ac_status.set_value("AC Adapter" if ac else "Battery")
        self.prof_status.set_value(PROFILE_LABELS.get(profile, "—"))
        self.auto_status.set_value(
            "✓ Active" if self._actions.get("auto_switch") else "✗ Disabled"
        )

# ══════════════════════════════════════════════════════════════════════════════
# ABOUT PAGE
# ══════════════════════════════════════════════════════════════════════════════
class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(12)
        card, lay = make_card()

        # Header section with logo and title
        header_w = QWidget()
        header_w.setStyleSheet("background:transparent;")
        header_l = QVBoxLayout(header_w)
        header_l.setContentsMargins(0,0,0,8)
        header_l.setSpacing(8)
        header_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        from PyQt6.QtGui import QPixmap as _QP
        import base64 as _b64
        pm = _QP(); pm.loadFromData(_b64.b64decode(_LEGION_ICON_B64))
        logo = QLabel(); logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(pm.scaled(64, 78, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation))
        logo.setStyleSheet("background:transparent;")
        header_l.addWidget(logo)

        title = QLabel("Legion Linux Toolkit")
        title.setStyleSheet(f"color:{C_TEXT};font-size:22px;font-weight:700;background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_l.addWidget(title)

        ver = QLabel("v0.6.3 · BETA 20260504")
        ver.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_l.addWidget(ver)

        lay.addWidget(header_w)

        # Read system info dynamically
        brand = HW.get("brand", "unknown").upper() if HW else _dmi("product_family").upper() or "LENOVO"
        model = HW.get("model", _dmi("product_name")) if HW else _dmi("product_name") or "Unknown"

        cpu_name = "Unknown"
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if "model name" in line.lower():
                    cpu_name = line.split(":")[1].strip()
                    break
        except: pass

        gpu_name = "Unknown"
        try:
            r = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
            gpus = []
            for line in r.stdout.splitlines():
                if any(k in line for k in ["VGA","3D","Display"]):
                    g = line.split(":",2)[-1].strip()
                    if len(g) > 55: g = g[:55] + "…"
                    gpus.append(g)
            gpu_name = " + ".join(gpus) if gpus else "Unknown"
        except: pass

        os_name = "Linux"
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    os_name = line.split("=",1)[1].strip().strip('"')
                    break
        except: pass

        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "") or \
                  os.environ.get("DESKTOP_SESSION", "Unknown")
        wayland = "Wayland" if os.environ.get("WAYLAND_DISPLAY") else "X11"
        desktop_str = f"{desktop} ({wayland})" if desktop else wayland

        drivers = []
        try:
            mods = subprocess.run(["lsmod"], capture_output=True, text=True, timeout=3).stdout
            if "ideapad_acpi" in mods:  drivers.append("ideapad_acpi")
            if "legion_laptop" in mods: drivers.append("legion_laptop")
            if "thinkpad_acpi" in mods: drivers.append("thinkpad_acpi")
        except: pass
        driver_str = " + ".join(drivers) if drivers else "ideapad_acpi"

        info_rows = [
            ("Brand",   brand),
            ("Model",   model),
            ("CPU",     cpu_name),
            ("GPU",     gpu_name),
            ("OS",      os_name),
            ("Desktop", desktop_str),
            ("Driver",  driver_str),
            ("Config",  "~/.config/legion-toolkit/"),
            ("GitHub",  "github.com/VVAT3R/legion-linux-toolkit"),
        ]
        for label, value in info_rows:
            row = QWidget()
            row.setStyleSheet("background:transparent;")
            row.setFixedHeight(32)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.setSpacing(16)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{C_TEXT2};font-size:12px;font-weight:500;background:transparent;")
            lbl.setFixedWidth(80)
            val = QLabel(value)
            val.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:500;background:transparent;")
            val.setWordWrap(True)
            rl.addWidget(lbl)
            rl.addWidget(val, 1)
            lay.addWidget(row)

        root.addWidget(card); root.addStretch()

    def refresh(self, d=None): pass

# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
_sampler = None   # created in main() after QApplication exists

class LegionDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Legion Linux Toolkit")
        self.setWindowIcon(_legion_icon())
        self.setMinimumSize(1060, 680); self.resize(1160, 740)
        self._build()
        global _sampler
        _sampler = DataSampler()
        _sampler.data_ready.connect(self._on_data)
        _sampler.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(2000)
        # Start Fn+Space watcher + power-mode watcher (event-driven, no rigid refresh)
        self._start_fnspace_watcher()
        self._start_powermode_watcher()

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
        rw = QWidget(); self.setCentralWidget(rw)
        main = QHBoxLayout(rw); main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        # Sidebar — wider, LLT-style
        sb = QWidget(); sb.setFixedWidth(220)
        sb.setStyleSheet(f"background:{C_SIDEBAR};")
        sbl = QVBoxLayout(sb); sbl.setContentsMargins(0,0,0,0); sbl.setSpacing(0)

        # Top bar with logo and title
        top_logo = QWidget()
        top_logo.setFixedHeight(64)
        top_logo.setStyleSheet(f"background:{C_SIDEBAR};")
        top_logo_lay = QHBoxLayout(top_logo)
        top_logo_lay.setContentsMargins(16,10,16,10)
        top_logo_lay.setSpacing(10)

        import base64 as _b64
        from PyQt6.QtGui import QPixmap as _QP2
        _pm2 = _QP2(); _pm2.loadFromData(_b64.b64decode(_LEGION_ICON_B64))
        logo_lbl = QLabel()
        logo_lbl.setPixmap(_pm2.scaled(28, 34, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation))
        logo_lbl.setStyleSheet("background:transparent;")
        logo_lbl.setFixedSize(32, 38)

        title_lbl = QLabel("Legion Toolkit")
        title_lbl.setStyleSheet(f"color:{C_TEXT};font-size:15px;font-weight:700;background:transparent;")

        top_logo_lay.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        top_logo_lay.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        top_logo_lay.addStretch()
        sbl.addWidget(top_logo)

        # Nav buttons
        self.nav_btns = []
        nav = [("🏠","Home"),("🔋","Battery"),("⚡","Performance"),
               ("🖥️","Display"),("⌨️","Keyboard"),("⚙️","System"),
               ("🚀","Overclock"),("🌀","Fan Control"),("🎯","Actions"),("ℹ️","About")]
        nav_area = QWidget()
        nav_area.setStyleSheet(f"background:{C_SIDEBAR};")
        nav_area_lay = QVBoxLayout(nav_area)
        nav_area_lay.setContentsMargins(8,8,8,8)
        nav_area_lay.setSpacing(4)

        for icon, label in nav:
            btn = SidebarBtn(icon, label)
            btn.clicked.connect(lambda chk, i=len(self.nav_btns): self._switch(i))
            self.nav_btns.append(btn)
            nav_area_lay.addWidget(btn)
        nav_area_lay.addStretch()
        sbl.addWidget(nav_area)

        # Bottom section with theme toggle
        bottom_area = QWidget()
        bottom_area.setStyleSheet(f"background:{C_SIDEBAR};")
        bottom_lay = QVBoxLayout(bottom_area)
        bottom_lay.setContentsMargins(8,8,8,8)
        bottom_lay.setSpacing(4)
        bottom_lay.addStretch()
        sbl.addWidget(bottom_area)
        main.addWidget(sb)

        # Right side
        right = QVBoxLayout(); right.setContentsMargins(0,0,0,0); right.setSpacing(0)
        topbar = QWidget(); topbar.setFixedHeight(60)
        topbar.setStyleSheet(
            f"background:{C_BG};"
        )
        tbl = QHBoxLayout(topbar); tbl.setContentsMargins(28,0,28,0); tbl.setSpacing(12)

        # Page title
        self.page_title = QLabel("Home")
        self.page_title.setStyleSheet(
            f"color:{C_TEXT};font-size:20px;font-weight:700;letter-spacing:0px;")
        tbl.addWidget(self.page_title)
        tbl.addStretch()

        # Hidden badge kept for _refresh_badge compat — not shown
        self.badge = QLabel(""); self.badge.hide()
        self.ac_ind = QLabel(""); self.ac_ind.hide()
        self._refresh_badge(lll.read_powermode())
        right.addWidget(topbar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{C_BG};")
        self.home_page = HomePage()
        self.home_page._page_request_cb = self._switch
        self.pages = [
            self.home_page, BatteryPage(), PerformancePage(),
            DisplayPage(), KeyboardPage(), SystemPage(),
            OverclockPage(), FanPage(), ActionsPage(), AboutPage()
        ]
        self.home_page._sync_battery_cb = self.pages[1].sync_charging
        self.pages[1]._sync_home_cb = self._sync_bat_combo
        self.pages[2]._oc_sync_cb = self.pages[6].check_powermode
        for pg in self.pages: self.stack.addWidget(pg)
        right.addWidget(self.stack); main.addLayout(right)
        self._switch(0)

    def _start_fnspace_watcher(self):
        """
        Watch kbd_backlight brightness for changes — fires when Fn+Space is pressed.
        Fn+Space cycles brightness 0→1→2→0, we intercept and also cycle RGB effect.
        """
        from PyQt6.QtCore import QMetaObject
        self._fnspace_signal = pyqtSignal()

        kbd_path = KBD_BACKLIGHT_PATH
        if kbd_path is None or not Path(str(kbd_path)).exists():
            return  # No backlight path — skip

        def _watch():
            last = None
            while True:
                try:
                    val = Path(str(kbd_path)).read_text().strip()
                    if last is not None and val != last:
                        # Brightness changed — Fn+Space was pressed
                        QMetaObject.invokeMethod(
                            self, "_on_fnspace",
                            Qt.ConnectionType.QueuedConnection
                        )
                    last = val
                except: pass
                time.sleep(0.15)

        threading.Thread(target=_watch, daemon=True).start()

    from PyQt6.QtCore import pyqtSlot

    @pyqtSlot()
    def _on_fnspace(self):
        """Called on main thread when Fn+Space is detected."""
        # Cycle the keyboard effect
        kb_page = self.pages[4]   # KeyboardPage is index 4
        if hasattr(kb_page, "cycle_effect"):
            kb_page.cycle_effect()
        # If keyboard page is not visible, show a brief notification
        if self.stack.currentIndex() != 4:
            cur = getattr(kb_page, "_current_effect", "Static")
            send_notif("Keyboard RGB", f"Effect → {cur}", "input-keyboard")

    def _start_powermode_watcher(self):
        """Background thread polling the powermode sysfs; fires only on actual
        change so Fn+Q / external switches reflect in ~POWERMODE_POLL_INTERVAL
        without a rigid timer resetting the user's in-progress edits."""
        from PyQt6.QtCore import QMetaObject
        pm_path = LEGION_POWERMODE
        if pm_path is None or not Path(str(pm_path)).exists():
            return

        def _watch():
            last = None
            while True:
                try:
                    val = Path(str(pm_path)).read_text().strip()
                    if last is not None and val != last:
                        QMetaObject.invokeMethod(
                            self, "_on_powermode_change",
                            Qt.ConnectionType.QueuedConnection
                        )
                    last = val
                except Exception:
                    pass
                time.sleep(POWERMODE_POLL_INTERVAL)

        threading.Thread(target=_watch, daemon=True).start()

    @pyqtSlot()
    def _on_powermode_change(self):
        """Main-thread handler invoked only when the power mode actually changes."""
        try:
            mode = lll.read_powermode()
        except Exception:
            return
        perf_page = self.pages[2]
        if hasattr(perf_page, 'power_combo'):
            perf_page.power_combo.blockSignals(True)
            for i in range(perf_page.power_combo.count()):
                if perf_page.power_combo.itemData(i, Qt.ItemDataRole.UserRole) == mode:
                    perf_page.power_combo.setCurrentIndex(i)
                    break
            perf_page.power_combo.blockSignals(False)
        self._refresh_badge(mode)
        # Keep Overclock page grey-out / preset in sync with the new mode
        self.pages[6].check_powermode()

    def _sync_bat_combo(self, idx: int):
        """Sync Home page battery combo when Battery page toggle changes."""
        self.home_page.bat_combo.blockSignals(True)
        self.home_page.bat_combo.setCurrentIndex(idx)
        self.home_page.bat_combo.blockSignals(False)

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        titles = ["Home","Battery","Performance","Display","Keyboard",
                  "System","Overclock","Fan","Actions","About"]
        self.page_title.setText(titles[idx])
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == idx); btn.update()
        # Refresh pages that don't get sampler data (read-once on switch)
        if idx == 4:    # KeyboardPage
            self.pages[4].refresh()
        elif idx == 6:  # OverclockPage
            self.pages[6].refresh()

    def _refresh_badge(self, profile):
        color = PROFILE_COLORS.get(profile, C_ACCENT)
        label = PROFILE_LABELS.get(profile, profile)
        self.badge.setText(label)
        self.badge.setStyleSheet(
            f"color:{color};font-size:10px;font-weight:600;letter-spacing:1px;"
            f"padding:4px 12px;border:1px solid {color};border-radius:10px;"
        )

    def _on_data(self, d):
        """Main-thread signal handler — safe to update UI. Called every 1s."""
        # Always update home (visible or not — keeps badges/OC bar in sync)
        self.home_page.refresh(d)
        self._refresh_badge(d["profile"])
        ac = d["ac"]
        self.ac_ind.setText("⚡ AC" if ac else "🔋 Battery")
        self.ac_ind.setStyleSheet(
            f"color:{C_GREEN if ac else C_ORANGE};font-size:12px;margin-left:12px;"
        )
        # Always sync power combo (Fn+Space may change it from any page)
        cur_profile = d["profile"]
        perf_page = self.pages[2]
        if hasattr(perf_page, 'power_combo'):
            perf_page.power_combo.blockSignals(True)
            for i in range(perf_page.power_combo.count()):
                if perf_page.power_combo.itemData(i, Qt.ItemDataRole.UserRole) == cur_profile:
                    perf_page.power_combo.setCurrentIndex(i)
                    break
            perf_page.power_combo.blockSignals(False)
        # Feed currently visible page if it can accept sampler data
        idx = self.stack.currentIndex()
        if idx == 2:    # PerformancePage
            self.pages[2].refresh(d)
        elif idx == 3:  # DisplayPage — VRR status
            self.pages[3].refresh(d)
        elif idx == 7:  # FanPage — live RPM
            self.pages[7].refresh(d)
        elif idx == 8:  # ActionsPage — power source status
            self.pages[8].refresh(d)
        elif idx == 6:  # OverclockPage — keep grey-out/preset in sync with power mode
            self.pages[6].check_powermode()
        # NOTE: KeyboardPage (4) is NOT refreshed here
        # to avoid overwriting user edits. It refreshes on page switch + 30s timer.

    def _tick(self):
        """Light 2s timer for pages that need periodic refresh but not sampler data."""
        idx = self.stack.currentIndex()
        # Battery page — detailed stats not in sampler
        if idx == 1:
            self.pages[1].refresh()
        # Actions page — AC poll
        elif idx == 8:
            self.pages[8].refresh()

    def closeEvent(self, e):
        global _sampler
        if _sampler:
            _sampler.stop()
        super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Legion Toolkit")
    app.setQuitOnLastWindowClosed(True)

    # Load saved language
    load_language()

    # Load or run hardware detection
    global HW
    if FIRST_RUN_FLAG.exists():
        # Returning user — load saved hardware profile silently
        HW = load_hardware()
        if not HW:
            HW = detect_hardware()
            save_hardware(HW)
    else:
        # First run — show wizard
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
