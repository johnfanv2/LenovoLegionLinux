#!/usr/bin/python3
# pylint: disable=c-extension-no-member
import sys
import os.path
import traceback
import time
from typing import List

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QTabWidget, QWidget, QLabel, \
    QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QComboBox, QGroupBox, \
    QCheckBox, QSystemTrayIcon, QMenu, QAction, QMessageBox
from legion import LegionModelFacade, FanCurve, FanCurveEntry, FileFeature


def mark_error(checkbox: QCheckBox):
    checkbox.setStyleSheet(
        "QCheckBox::indicator {background-color : red;} "
        "QCheckBox:disabled{background-color : red;} "
        "QCheckBox {background-color : red;}")


def log_error(ex: Exception):
    print("Error occured", ex)
    print(traceback.format_exc())


def sync_checkbox_from_feature(checkbox: QCheckBox, feature: FileFeature):
    try:
        if feature.exists():
            hw_value = feature.get()
            checkbox.setChecked(hw_value)
            checkbox.setDisabled(False)
        else:
            checkbox.setDisabled(True)
    # pylint: disable=broad-except
    except Exception as ex:
        mark_error(checkbox)
        log_error(ex)


def sync_checkbox(checkbox: QCheckBox, feature: FileFeature):
    try:
        if feature.exists():
            gui_value = checkbox.isChecked()
            feature.set(gui_value)
            time.sleep(0.100)
            hw_value = feature.get()
            checkbox.setChecked(hw_value)
            checkbox.setDisabled(False)
        else:
            checkbox.setDisabled(True)
    # pylint: disable=broad-except
    except Exception as ex:
        mark_error(checkbox)
        log_error(ex)


class BoolFeatureController:
    checkbox: QCheckBox
    feature: FileFeature
    dependent_controllers: List

    def __init__(self, checkbox: QCheckBox, feature: FileFeature):
        self.checkbox = checkbox
        self.feature = feature
        self.checkbox.clicked.connect(self.sync_feature_to_view)
        self.dependent_controllers = []

    def sync_feature_to_view(self):
        sync_checkbox(
            self.checkbox, self.feature)
        if self.dependent_controllers:
            time.sleep(0.100)
            for c in self.dependent_controllers:
                c.sync_view_to_feature()

    def sync_view_to_feature(self):
        sync_checkbox_from_feature(self.checkbox, self.feature)


class LegionController:
    model: LegionModelFacade
    # fan
    lockfancontroller_controller: BoolFeatureController
    maximumfanspeed_controller: BoolFeatureController
    # other
    fnlock_controller: BoolFeatureController
    touchpad_controller: BoolFeatureController
    batteryconservation_controller: BoolFeatureController
    always_on_usb_controller: BoolFeatureController
    rapid_charging_controller: BoolFeatureController

    def __init__(self, expect_hwmon=True):
        self.model = LegionModelFacade(expect_hwmon=expect_hwmon)
        self.view_fancurve = None
        self.view_otheroptions = None
        self.main_window = None

    def init(self, read_from_hw=True):
        # fan
        self.lockfancontroller_controller = BoolFeatureController(
            self.view_fancurve.lockfancontroller_check,
            self.model.lockfancontroller)
        self.maximumfanspeed_controller = BoolFeatureController(
            self.view_fancurve.maximumfanspeed_check,
            self.model.maximum_fanspeed)
        # other
        self.fnlock_controller = BoolFeatureController(
            self.view_otheroptions.fnlock_check,
            self.model.fn_lock)
        self.touchpad_controller = BoolFeatureController(
            self.view_otheroptions.touchpad_check,
            self.model.touchpad)
        self.batteryconservation_controller = BoolFeatureController(
            self.view_otheroptions.batteryconservation_check,
            self.model.battery_conservation)
        self.rapid_charging_controller = BoolFeatureController(
            self.view_otheroptions.rapid_charging_check,
            self.model.rapid_charging)
        self.batteryconservation_controller.dependent_controllers.append(
            self.rapid_charging_controller)
        self.rapid_charging_controller.dependent_controllers.append(
            self.batteryconservation_controller)
        self.always_on_usb_controller = BoolFeatureController(
            self.view_otheroptions.always_on_usb_check,
            self.model.always_on_usb_charging)

        if read_from_hw:
            self.model.read_fancurve_from_hw()
            # fan controller
        # fan
        self.lockfancontroller_controller.sync_view_to_feature()
        self.maximumfanspeed_controller.sync_view_to_feature()
        # other
        self.fnlock_controller.sync_view_to_feature()
        self.touchpad_controller.sync_view_to_feature()
        self.batteryconservation_controller.sync_view_to_feature()
        self.rapid_charging_controller.sync_feature_to_view()
        self.always_on_usb_controller.sync_feature_to_view()
        self.update_fancurve_gui()
        self.view_fancurve.set_presets(self.model.fancurve_repo.get_names())
        self.main_window.show_root_dialog = not self.model.is_root_user()

    def update_fancurve_gui(self):
        self.view_fancurve.set_fancurve(self.model.fan_curve,
                                        self.model.fancurve_io.has_minifancurve(),
                                        self.model.fancurve_io.exists())

    def on_read_fan_curve_from_hw(self):
        self.model.read_fancurve_from_hw()
        self.update_fancurve_gui()

    def on_write_fan_curve_to_hw(self):
        self.model.fan_curve = self.view_fancurve.get_fancurve()
        self.model.write_fancurve_to_hw()
        self.model.read_fancurve_from_hw()
        self.update_fancurve_gui()

    def on_load_from_preset(self):
        name = self.view_fancurve.preset_combobox.currentText()
        self.model.fan_curve = self.view_fancurve.get_fancurve()
        self.model.load_fancurve_from_preset(name)
        self.update_fancurve_gui()

    def on_save_to_preset(self):
        name = self.view_fancurve.preset_combobox.currentText()
        self.model.fan_curve = self.view_fancurve.get_fancurve()
        self.model.save_fancurve_to_preset(name)


class FanCurveEntryView():
    def __init__(self, point_id, layout):
        self.point_id_label = QLabel(f'{point_id}')
        self.point_id_label.setAlignment(Qt.AlignCenter)
        self.fan_speed1_edit = QLineEdit()
        self.fan_speed2_edit = QLineEdit()
        self.cpu_lower_temp_edit = QLineEdit()
        self.cpu_upper_temp_edit = QLineEdit()
        self.gpu_lower_temp_edit = QLineEdit()
        self.gpu_upper_temp_edit = QLineEdit()
        self.ic_lower_temp_edit = QLineEdit()
        self.ic_upper_temp_edit = QLineEdit()
        self.accel_edit = QLineEdit()
        self.decel_edit = QLineEdit()

        layout.addWidget(self.point_id_label, 0, point_id)
        layout.addWidget(self.fan_speed1_edit, 1, point_id)
        layout.addWidget(self.fan_speed2_edit, 2, point_id)
        layout.addWidget(self.cpu_lower_temp_edit, 3, point_id)
        layout.addWidget(self.cpu_upper_temp_edit, 4, point_id)
        layout.addWidget(self.gpu_lower_temp_edit, 5, point_id)
        layout.addWidget(self.gpu_upper_temp_edit, 6, point_id)
        layout.addWidget(self.ic_lower_temp_edit, 7, point_id)
        layout.addWidget(self.ic_upper_temp_edit, 8, point_id)
        layout.addWidget(self.accel_edit, 9, point_id)
        layout.addWidget(self.decel_edit, 10, point_id)

    def set(self, entry: FanCurveEntry):
        self.fan_speed1_edit.setText(str(entry.fan1_speed))
        self.fan_speed2_edit.setText(str(entry.fan2_speed))
        self.cpu_lower_temp_edit.setText(str(entry.cpu_lower_temp))
        self.cpu_upper_temp_edit.setText(str(entry.cpu_upper_temp))
        self.gpu_lower_temp_edit.setText(str(entry.gpu_lower_temp))
        self.gpu_upper_temp_edit.setText(str(entry.gpu_upper_temp))
        self.ic_lower_temp_edit.setText(str(entry.ic_lower_temp))
        self.ic_upper_temp_edit.setText(str(entry.ic_upper_temp))
        self.accel_edit.setText(str(entry.acceleration))
        self.decel_edit.setText(str(entry.deceleration))

    def set_disabled(self, value: bool):
        self.fan_speed1_edit.setDisabled(value)
        self.fan_speed2_edit.setDisabled(value)
        self.cpu_lower_temp_edit.setDisabled(value)
        self.cpu_upper_temp_edit.setDisabled(value)
        self.gpu_lower_temp_edit.setDisabled(value)
        self.gpu_upper_temp_edit.setDisabled(value)
        self.ic_lower_temp_edit.setDisabled(value)
        self.ic_upper_temp_edit.setDisabled(value)
        self.accel_edit.setDisabled(value)
        self.decel_edit.setDisabled(value)

    def get(self) -> FanCurveEntry:
        fan1_speed = int(self.fan_speed1_edit.text())
        fan2_speed = int(self.fan_speed2_edit.text())
        cpu_lower_temp = int(self.cpu_lower_temp_edit.text())
        cpu_upper_temp = int(self.cpu_upper_temp_edit.text())
        gpu_lower_temp = int(self.gpu_lower_temp_edit.text())
        gpu_upper_temp = int(self.gpu_upper_temp_edit.text())
        ic_lower_temp = int(self.ic_lower_temp_edit.text())
        ic_upper_temp = int(self.ic_upper_temp_edit.text())
        acceleration = int(self.accel_edit.text())
        deceleration = int(self.decel_edit.text())
        entry = FanCurveEntry(fan1_speed=fan1_speed, fan2_speed=fan2_speed,
                              cpu_lower_temp=cpu_lower_temp, cpu_upper_temp=cpu_upper_temp,
                              gpu_lower_temp=gpu_lower_temp, gpu_upper_temp=gpu_upper_temp,
                              ic_lower_temp=ic_lower_temp, ic_upper_temp=ic_upper_temp,
                              acceleration=acceleration, deceleration=deceleration)
        return entry


class FanCurveTab(QWidget):
    def __init__(self, controller: LegionController):
        super().__init__()
        self.controller = controller
        self.entry_edits = []
        self.init_ui()

        self.controller.view_fancurve = self

    def set_fancurve(self, fancurve: FanCurve, has_minifancurve: bool, enabled: bool):
        self.minfancurve_check.setDisabled(not has_minifancurve)
        for i, entry in enumerate(fancurve.entries):
            self.entry_edits[i].set(entry)
            self.entry_edits[i].set_disabled(not enabled)
        self.load_button.setDisabled(not enabled)
        self.write_button.setDisabled(not enabled)

        for i, entry in enumerate(fancurve.entries):
            self.entry_edits[i].set(entry)
        self.minfancurve_check.setChecked(fancurve.enable_minifancurve)

    def get_fancurve(self) -> FanCurve:
        entries = []
        for i in range(10):
            entry = self.entry_edits[i].get()
            entries.append(entry)
        return FanCurve(name='unknown', entries=entries,
                        enable_minifancurve=self.minfancurve_check.isChecked())

    def create_fancurve_entry_view(self, layout, point_id):
        self.entry_edits.append(FanCurveEntryView(point_id, layout))

    def set_presets(self, presets):
        self.preset_combobox.clear()
        for preset in presets:
            self.preset_combobox.addItem(preset)

    def init_ui(self):
        # pylint: disable=too-many-statements
        self.fancurve_group = QGroupBox("Fan Curve")
        self.layout = QGridLayout()
        self.point_id_label = QLabel("Point ID")
        self.fan_speed1_label = QLabel("Fan 1 Speed [rpm]")
        self.fan_speed2_label = QLabel("Fan 2 Speed [rpm]")
        self.cpu_lower_temp_label = QLabel("CPU Lower Temp. [°C.]")
        self.cpu_upper_temp_label = QLabel("CPU Upper Temp. [°C.]")
        self.gpu_lower_temp_label = QLabel("GPU Lower Temp. [°C.]")
        self.gpu_upper_temp_label = QLabel("GPU Upper Temp. [°C.]")
        self.ic_lower_temp_label = QLabel("IC Lower Temp. [°C.]")
        self.ic_upper_temp_label = QLabel("IC Upper Temp. [°C.]")
        self.accel_label = QLabel("Acceleration [s]")
        self.decel_label = QLabel("Deceleration [s]")
        self.minfancurve_check = QCheckBox("Minifancurve if too cold")
        self.lockfancontroller_check = QCheckBox(
            "Lock fan controller, lock temperature sensors, and lock current fan speed")
        self.maximumfanspeed_check = QCheckBox(
            "Set speed to maximum fan speed")
        self.layout.addWidget(self.point_id_label, 0, 0)
        self.layout.addWidget(self.fan_speed1_label, 1, 0)
        self.layout.addWidget(self.fan_speed2_label, 2, 0)
        self.layout.addWidget(self.cpu_lower_temp_label, 3, 0)
        self.layout.addWidget(self.cpu_upper_temp_label, 4, 0)
        self.layout.addWidget(self.gpu_lower_temp_label, 5, 0)
        self.layout.addWidget(self.gpu_upper_temp_label, 6, 0)
        self.layout.addWidget(self.ic_lower_temp_label, 7, 0)
        self.layout.addWidget(self.ic_upper_temp_label, 8, 0)
        self.layout.addWidget(self.accel_label, 9, 0)
        self.layout.addWidget(self.decel_label, 10, 0)
        self.layout.addWidget(self.minfancurve_check, 11, 0)
        self.layout.addWidget(self.lockfancontroller_check, 12, 0)
        self.layout.addWidget(self.maximumfanspeed_check, 13, 0)
        for i in range(1, 11):
            self.create_fancurve_entry_view(self.layout, i)
        self.fancurve_group.setLayout(self.layout)

        self.button1_group = QGroupBox("Fancurve Hardware")
        self.button1_layout = QGridLayout()

        self.load_button = QPushButton("Read from HW")
        self.write_button = QPushButton("Apply to HW")
        self.note_label = QLabel(
            "Fan curve is reset to default if you toggle power mode (Fn + Q).")
        self.load_button.clicked.connect(
            self.controller.on_read_fan_curve_from_hw)
        self.write_button.clicked.connect(
            self.controller.on_write_fan_curve_to_hw)
        self.button1_group.setLayout(self.button1_layout)
        self.button1_layout.addWidget(self.load_button, 0, 0)
        self.button1_layout.addWidget(self.write_button, 0, 1)
        self.button1_layout.addWidget(self.note_label, 1, 0)

        self.button2_group = QGroupBox("Fancurve Preset")
        self.button2_layout = QGridLayout()
        self.save_to_preset_button = QPushButton("Save to Preset")
        self.load_from_preset_button = QPushButton("Load from Preset")
        self.save_to_preset_button.clicked.connect(
            self.controller.on_save_to_preset)
        self.load_from_preset_button.clicked.connect(
            self.controller.on_load_from_preset)
        self.preset_combobox = QComboBox(self)
        self.button2_group.setLayout(self.button2_layout)
        self.button2_layout.addWidget(self.preset_combobox, 0, 0)
        self.button2_layout.addWidget(self.save_to_preset_button, 1, 0)
        self.button2_layout.addWidget(self.load_from_preset_button, 1, 1)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.fancurve_group, 0)
        self.main_layout.addWidget(self.button1_group, 1)
        self.main_layout.addWidget(self.button2_group, 2)

        self.note_label2 = QLabel(
            "Greyed out features are not available. If most features are greyed out, "
            "the driver is not loaded properly or hwmon directoy not found.\nIf features are marked "
            "red, an unepxected error accessing the hardware and you should notify the maintainer.")
        self.note_label2.setStyleSheet("color: red;")
        self.main_layout.addWidget(self.note_label2, 3)

        self.setLayout(self.main_layout)

# pylint: disable=too-few-public-methods


class OtherOptionsTab(QWidget):
    def __init__(self, controller: LegionController):
        super().__init__()
        self.controller = controller
        self.init_ui()
        self.controller.view_otheroptions = self

    def init_ui(self):
        self.options_group = QGroupBox("Options")
        self.options_layout = QVBoxLayout()
        self.options_group.setLayout(self.options_layout)

        self.fnlock_check = QCheckBox(
            "Fn Lock (Use special function of F1-F12 keys without pressing Fn; same as Fn + Esc)")
        self.options_layout.addWidget(self.fnlock_check, 0)

        self.touchpad_check = QCheckBox(
            "Touchpad Enabled (Lock or unlock touchpad; same as Fn + F10)")
        self.options_layout.addWidget(self.touchpad_check, 1)

        self.batteryconservation_check = QCheckBox(
            "Battery Conservation (keep battery at about 50 percent and do not charge on AC to extend battery life)")
        self.options_layout.addWidget(self.batteryconservation_check, 2)

        self.rapid_charging_check = QCheckBox(
            "Rapid Charging")
        self.options_layout.addWidget(self.rapid_charging_check, 3)

        self.always_on_usb_check = QCheckBox(
            "AlwaysOnUsbCharging")
        self.options_layout.addWidget(self.always_on_usb_check, 4)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.options_group, 0)
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)


# pylint: disable=too-few-public-methods
class AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        about_label = QLabel("https://github.com/johnfanv2/LenovoLegionLinux")
        about_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(about_label)
        self.setLayout(layout)

# pylint: disable=too-few-public-methods


class MainWindow(QTabWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.controller.main_window = self
        self.fan_curve_tab = FanCurveTab(controller)
        self.other_options_tab = OtherOptionsTab(controller)
        self.about_tab = AboutTab()
        self.close_timer = QTimer()
        self.addTab(self.fan_curve_tab, "Fan Curve")
        self.addTab(self.other_options_tab, "Other Options")
        self.addTab(self.about_tab, "About")
        self.show_root_dialog = False
        self.onstart_timer = QtCore.QTimer()
        self.onstart_timer.singleShot(0, self.on_start)

    def on_start(self):
        if self.show_root_dialog:
            QMessageBox.critical(
                self, "Error", "Program must be run as root user!")

    def close_after(self, milliseconds: int):
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(milliseconds)

    def bring_to_foreground(self):
        self.setWindowState(self.windowState(
        ) & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.activateWindow()


class LegionTray:
    def __init__(self, icon, app, main_window):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(icon)
        self.tray.setVisible(True)

        self.menu = QMenu()
        # title
        self.title = QAction("Legion")
        self.title.setEnabled(False)
        self.menu.addAction(self.title)
        # ---
        self.menu.addSeparator()
        # open
        self.open_action = QAction("Show")
        self.open_action.triggered.connect(main_window.bring_to_foreground)
        self.menu.addAction(self.open_action)
        # quit
        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(app.quit)
        self.menu.addAction(self.quit_action)
        self.tray.setContextMenu(self.menu)

    def show(self):
        self.tray.show()


def main():
    app = QApplication(sys.argv)
    automatic_close = '--automaticclose' in sys.argv
    do_not_excpect_hwmon = True

    icon = QtGui.QIcon(os.path.join(
        os.path.realpath(__file__), 'legion_logo.png'))

    contr = LegionController(expect_hwmon=not do_not_excpect_hwmon)
    main_window = MainWindow(contr)
    main_window.setWindowTitle("LenovoLegionLinux")
    main_window.setWindowIcon(icon)
    contr.init(read_from_hw=not do_not_excpect_hwmon)
    contr.model.fancurve_repo.create_preset_folder()
    if automatic_close:
        main_window.close_after(3000)
    main_window.show()

    tray = LegionTray(icon, app, main_window)
    tray.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
