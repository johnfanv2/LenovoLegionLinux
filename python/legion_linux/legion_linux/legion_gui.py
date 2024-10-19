#!/usr/bin/python3
# pylint: disable=too-many-lines
# pylint: disable=c-extension-no-member
import sys
import os
import os.path
import traceback
import logging
import random
import time
from typing import List, Optional
from PyQt6 import QtGui, QtCore
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QRunnable, QThreadPool
from PyQt6.QtGui import QAction, QGuiApplication
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QLabel, \
    QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QComboBox, QGroupBox, \
    QCheckBox, QSystemTrayIcon, QMenu, QScrollArea, QMessageBox, QSpinBox, QTextBrowser, QHBoxLayout
# Make it possible to run without installation
# pylint: disable=# pylint: disable=wrong-import-position
sys.path.insert(0, os.path.dirname(__file__) + "/..")
import legion_linux.legion
from legion_linux.legion import LegionModelFacade, FanCurve, FanCurveEntry, FileFeature, \
    IntFileFeature, GsyncFeature, SystemNotificationSender, DiagnosticMsg


def get_color_mode():
    # Try detecting the current color mode (dark/light)
    # As darkdetect is not a system package, make it work if
    # it is not installed
    try:
        # pylint: disable=import-outside-toplevel
        import darkdetect
        if darkdetect.theme() == 'Dark':
            return 'dark'
        if darkdetect.theme() == 'Light':
            return 'light'
    except ImportError as err:
        log.error("Error using darkdetect. Is it installed?")
        log.error(str(err))
    return 'unknown'

# pylint: disable=too-few-public-methods
class QtLogHandler(QtCore.QObject):
    logBuffer = []
    logWritten = QtCore.pyqtSignal(str)

    def emit(self, msg):
        self.logBuffer.append(msg)
        if self.receivers(self.logWritten) > 0:
            while self.logBuffer:
                self.logWritten.emit(self.logBuffer.pop(0))


class QtHandler(logging.Handler):
    logWritten = QtCore.pyqtSignal(str)

    def __init__(self, level=0) -> None:
        super().__init__(level)
        self.qt_obj = QtLogHandler()

    def emit(self, record):
        msg = self.format(record)
        self.qt_obj.emit(msg)


logging.basicConfig()
log = logging.getLogger(legion_linux.legion.__name__)
qt_handler = QtHandler()
qt_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s: %(message)s"))
log.addHandler(qt_handler)
log.setLevel('INFO')



class MonitorWorker(QRunnable):
    def __init__(self, model:LegionModelFacade):
        super().__init__()
        self.model = model
        self.running = False
        self.notification_sender = SystemNotificationSender()


    @pyqtSlot()
    def run(self):
        log.info("Start monitoring thread")

        # The thread itself
        while self.running:
            diag_msgs: List[DiagnosticMsg] = []
            for mon in self.model.monitors:
                try:
                    diag_msgs = diag_msgs + mon.run()
                # pylint: disable=broad-except
                except Exception as err:
                    log.error(str(err))
            for msg in diag_msgs:
                if msg.has_value and msg.filter_do_output:
                    log.info(str(msg.msg))
                    self.notification_sender.notify('Legion', msg.msg)
                elif msg.has_value:
                    log.info("FILTERED: %s", msg.msg)
                else:
                    log.info("FILTERED2: %s", msg.msg)
            time.sleep(10.0)

        log.info("Finishing monitoring thread")

def mark_error(checkbox: QCheckBox):
    checkbox.setStyleSheet(
        "QCheckBox::indicator {background-color : red;} "
        "QCheckBox:disabled{background-color : red;} "
        "QCheckBox {background-color : red;}")


def mark_error_combobox(combobox: QComboBox):
    combobox.setStyleSheet(
        "QComboBox::indicator {background-color : red;} "
        "QComboBox:disabled{background-color : red;} "
        "QComboBox {background-color : red;}")


def log_error(ex: Exception):
    print("Error occured", ex)
    print(traceback.format_exc())



def log_ui_feature_action(widget, feature):
    text = "###"
    if hasattr(widget, 'currentText'):
        text = widget.currentText()
    if hasattr(widget, 'text'):
        text = widget.text()
    name = feature.name() if hasattr(feature, 'name') else "###"
    log.info("Click on UI %s element for %s", text, name)


def open_web_link():
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(
        "https://github.com/johnfanv2/LenovoLegionLinux"))


def open_star_link():
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(
        "https://github.com/johnfanv2/LenovoLegionLinux"))


class EnumFeatureController:
    widget: QComboBox
    feature: FileFeature
    dependent_controllers: List
    check_after_set_time: float

    def __init__(self, widget: QComboBox, feature: FileFeature):
        self.widget = widget
        self.feature = feature
        self.dependent_controllers = []
        self.check_after_set_time = 0.1
        self.widget.currentIndexChanged.connect(self.on_ui_element_click)

    def on_ui_element_click(self):
        log_ui_feature_action(self.widget, self.feature)
        self.update_feature_from_view()

    def update_feature_from_view(self):
        # print("update_feature_from_view", self.widget.currentText())
        try:
            if self.feature.exists():
                gui_value = self.widget.currentText()
                values = self.feature.get_values()
                value = None
                for val in values:
                    if gui_value == val.name:
                        value = val.value

                if value is not None:
                    print(f"Set to value: {value}")
                    self.feature.set(value)
                else:
                    print(f"Value for gui_value {gui_value} not found")
            else:
                self.widget.setDisabled(True)
        # pylint: disable=broad-except
        except Exception as ex:
            mark_error_combobox(self.widget)
            log_error(ex)
        time.sleep(0.200)
        self.update_view_from_feature()

        if self.dependent_controllers:
            time.sleep(self.check_after_set_time)
            for contr in self.dependent_controllers:
                contr.update_view_from_feature()

    def update_view_from_feature(self, k=0, update_items=False):
        log.info("update_view_from_feature: %d", k)
        try:
            if self.feature.exists():
                # possible values -> items
                values = self.feature.get_values()
                self.widget.blockSignals(True)
                if update_items:
                    self.widget.clear()
                    for val in values:
                        self.widget.addItem(val.name)
                self.widget.blockSignals(False)

                # value -> index
                value = self.feature.get()
                self.widget.blockSignals(True)
                for i, val in enumerate(values):
                    if value == val.value:
                        self.widget.setCurrentIndex(i)
                self.widget.blockSignals(False)
                self.widget.setDisabled(False)
            else:
                self.widget.setDisabled(True)
        # pylint: disable=broad-except
        except Exception as ex:
            mark_error_combobox(self.widget)
            log_error(ex)


class BoolFeatureController:
    checkbox: QCheckBox
    feature: FileFeature
    dependent_controllers: List
    check_after_set_time: float

    def __init__(self, checkbox: QCheckBox, feature: FileFeature):
        self.checkbox = checkbox
        self.feature = feature
        self.checkbox.clicked.connect(self.on_ui_element_click)
        self.dependent_controllers = []
        self.check_after_set_time = 0.1

    def on_ui_element_click(self):
        log_ui_feature_action(self.checkbox, self.feature)
        self.update_feature_from_view()

    def update_feature_from_view(self):
        try:
            if self.feature.exists():
                gui_value = self.checkbox.isChecked()
                self.feature.set(gui_value)
                time.sleep(0.100)
                feature_value = self.feature.get()
                self.checkbox.setChecked(feature_value)
                self.checkbox.setDisabled(False)
            else:
                self.checkbox.setDisabled(True)
        # pylint: disable=broad-except
        except Exception as ex:
            mark_error(self.checkbox)
            log_error(ex)

        if self.dependent_controllers:
            time.sleep(self.check_after_set_time)
            for contr in self.dependent_controllers:
                contr.update_view_from_feature()

    def update_view_from_feature(self):
        try:
            if self.feature.exists():
                feature_value = self.feature.get()
                self.checkbox.setChecked(feature_value)
                self.checkbox.setDisabled(False)
            else:
                self.checkbox.setDisabled(True)
        # pylint: disable=broad-except
        except Exception as ex:
            mark_error(self.checkbox)
            log_error(ex)


class BoolFeatureTrayController:
    action: QAction
    feature: FileFeature
    dependent_controllers: List

    def __init__(self, action: QAction, feature: FileFeature):
        self.action = action
        self.feature = feature
        self.action.setCheckable(True)
        self.action.triggered.connect(self.on_ui_element_click)
        self.dependent_controllers = []

    def on_ui_element_click(self):
        log_ui_feature_action(self.action, self.feature)
        self.update_feature_from_view()

    def update_feature_from_view(self):
        try:
            if self.feature.exists():
                gui_value = self.action.isChecked()
                self.feature.set(gui_value)
                time.sleep(0.100)
                hw_value = self.feature.get()
                self.action.setChecked(hw_value)
                self.action.setDisabled(False)
                self.action.setCheckable(True)
            else:
                self.action.setDisabled(True)
                self.action.setCheckable(False)
        # pylint: disable=broad-except
        except Exception as ex:
            log_error(ex)
        if self.dependent_controllers:
            time.sleep(0.100)
            for contr in self.dependent_controllers:
                contr.update_view_from_feature()

    def update_view_from_feature(self):
        try:
            if self.feature.exists():
                hw_value = self.feature.get()
                self.action.setChecked(hw_value)
                self.action.setDisabled(False)
                self.action.setCheckable(True)
            else:
                self.action.setDisabled(True)
                self.action.setCheckable(False)
        # pylint: disable=broad-except
        except Exception as ex:
            log_error(ex)


class PresetTrayController:
    action: List[QAction]
    model: LegionModelFacade
    dependent_controllers: List

    def __init__(self, model: LegionModelFacade, actions: List[QAction]):
        self.actions = actions
        self.model = model
        self.dependent_controllers = []
        self.update_view_from_feature()

    def update_view_from_feature(self):
        for i, action in enumerate(self.actions):
            name = list(self.model.fancurve_repo.get_names())[i]
            action.setText(f"Apply preset {name}")
            action.setCheckable(False)
            action.setDisabled(not self.model.fancurve_repo.does_exists_by_name(name))

            # Connect function to set respective preset and
            # take current value of name into closure
            def callback(_, pname = name):
                self.on_action_click(pname)
            action.triggered.connect(callback)

    def on_action_click(self, name):
        log.info("Setting preset %s from tray action", name)
        self.model.fancurve_write_preset_to_hw(name)


class EnumFeatureTrayController:
    action: List[QAction]
    feature: FileFeature
    dependent_controllers: List

    def __init__(self, feature: FileFeature, actions: List[QAction]):
        self.actions = actions
        self.feature = feature
        self.dependent_controllers = []
        self.update_view_from_feature(connect=True)

    def update_view_from_feature(self, connect=False):
        log.info("update_view_from_feature in EnumFeatureTrayController ")
        try:
            if self.feature.exists():
                # possible values -> items
                values = self.feature.get_values()
                current_value = self.feature.get()
                # Update each action for each possible value
                for i, action in enumerate(self.actions):
                    if i < len(values):
                        value = values[i].value
                        name = values[i].name
                        action.setVisible(True)
                        action.setText(f"Set {name}")
                        action.setCheckable(True)
                        action.setChecked(value == current_value)

                        if connect:
                            # Connect function to set respective preset and
                            # take current value of name into closure
                            def callback(_, pvalue = value):
                                self.on_action_click(pvalue)
                            action.triggered.connect(callback)
                    else:
                        # there are more actions than values, so hide it
                        action.setVisible(False)
            else:
                for i, action in enumerate(self.actions):
                    if i< len(values):
                        value, name = values[i]
                        action.setText(f"Set {name}")
                        action.setCheckable(True)
                        action.setChecked(False)
                        action.setDisabled(True)
                    else:
                        # there are more actions than values, so hide it
                        action.setVisible(False)
        # pylint: disable=broad-except
        except Exception as ex:
            log_error(ex)

    def on_action_click(self, value):
        log.info("Setting value %s from tray action", value)
        try:
            if self.feature.exists():
                self.feature.set(value)
        # pylint: disable=broad-except
        except Exception as ex:
            log_error(ex)
        time.sleep(0.200)
        log.info("Update view after setting inEnumFeatureTrayController ")
        self.update_view_from_feature()
        if self.dependent_controllers:
            time.sleep(0.100)
            for contr in self.dependent_controllers:
                log.info("Update dependent view %s in EnumFeatureTrayController", str(contr))
                contr.update_view_from_feature()


def set_dependent(controller1, controller2):
    controller1.dependent_controllers.append(controller2)
    controller2.dependent_controllers.append(controller1)


class IntFeatureController:
    widget: QSpinBox
    feature: IntFileFeature

    def __init__(self, widget: QComboBox, feature: FileFeature, update_on_change=False):
        self.widget = widget
        self.feature = feature
        if update_on_change:
            self.widget.valueChanged.connect(self.on_ui_element_click)

    def on_ui_element_click(self):
        log_ui_feature_action(self.widget, self.feature)
        self.update_feature_from_view()

    def update_feature_from_view(self, wait=True):
        # print("update_feature_from_view", self.widget.currentText())
        try:
            if self.feature.exists():
                gui_value = self.widget.value()
                low, upper, _ = self.feature.get_limits_and_step()
                if low <= gui_value <= upper:
                    print(f"Set to value: {gui_value}")
                    self.feature.set(gui_value)
                else:
                    print(
                        f"Value for gui_value {gui_value} not ignored with limits {low} and {upper}")
            else:
                self.widget.setDisabled(True)
        # pylint: disable=broad-except
        except Exception as ex:
            mark_error_combobox(self.widget)
            log_error(ex)
        if wait:
            time.sleep(0.200)
        self.update_view_from_feature()

    def update_view_from_feature(self, k=0, update_bounds=False):
        print("update_view_from_feature", k)
        try:
            if self.feature.exists():
                # possible values
                low, upper, _ = self.feature.get_limits_and_step()
                if update_bounds:
                    self.widget.blockSignals(True)
                    self.widget.setMinimum(low)
                    self.widget.setMaximum(upper)
                    self.widget.blockSignals(False)

                # value -> index
                value = self.feature.get()
                self.widget.blockSignals(True)
                self.widget.setValue(value)
                self.widget.blockSignals(False)
                self.widget.setDisabled(False)
            else:
                self.widget.setDisabled(True)
        # pylint: disable=broad-except
        except Exception as ex:
            mark_error_combobox(self.widget)
            log_error(ex)

class HybridGsyncController:
    gsynchybrid_feature: GsyncFeature
    target_value: Optional[dict]

    def __init__(self, gsynchybrid_feature: GsyncFeature,
                 current_state_label: QLabel,
                 activate_button: QPushButton,
                 deactivate_button: QPushButton):
        self.current_state_label = current_state_label
        self.gsynchybrid_feature = gsynchybrid_feature
        self.target_value = None
        self.activate_button = activate_button
        self.deactivate_button = deactivate_button
        self.activate_button.clicked.connect(self.activate)
        self.deactivate_button.clicked.connect(self.deactivate)

    def activate(self):
        log_ui_feature_action(self.activate_button, self.gsynchybrid_feature)
        self.gsynchybrid_feature.set(True)
        self.target_value = True
        self.update_view_from_feature()

    def deactivate(self):
        log_ui_feature_action(self.deactivate_button, self.gsynchybrid_feature)
        self.gsynchybrid_feature.set(False)
        self.target_value = False
        self.update_view_from_feature()

    def update_feature_from_view(self, _):
        pass

    def update_view_from_feature(self):
        try:
            if not self.gsynchybrid_feature.exists():
                current_val_str = 'not found'
            else:
                value = self.gsynchybrid_feature.get()
                if value:
                    current_val_str = 'current: active'
                else:
                    current_val_str = 'current: inactive'
        # pylint: disable=broad-except
        except Exception as ex:
            current_val_str = 'error'
            log_error(ex)

        if self.target_value is None:
            target_val_str = ''
        elif self.target_value:
            target_val_str = '- target: active (restart required)'
        else:
            target_val_str = '- target: inactive (restart required)'
        self.current_state_label.setText(
            current_val_str + ' ' + target_val_str)


class LegionController:
    model: LegionModelFacade
    # fan
    lockfancontroller_controller: BoolFeatureController
    maximumfanspeed_controller: BoolFeatureController
    # other
    fnlock_controller: BoolFeatureController
    winkey_controller: BoolFeatureController
    touchpad_controller: BoolFeatureController
    camera_power_controller: BoolFeatureController
    overdrive_controller: BoolFeatureController
    hybrid_gsync_controller: HybridGsyncController
    batteryconservation_controller: BoolFeatureController
    always_on_usb_controller: BoolFeatureController
    rapid_charging_controller: BoolFeatureController
    power_mode_controller: EnumFeatureController
    # OC/Power
    cpu_overclock: BoolFeatureController
    gpu_overclock: BoolFeatureController
    cpu_longterm_power_limit_controller: IntFeatureController
    cpu_shortterm_power_limit_controller: IntFeatureController
    cpu_peak_power_limit_controller: IntFeatureController
    cpu_cross_loading_power_limit_controller: IntFeatureController
    cpu_apu_sppt_power_limit_controller: IntFeatureController
    gpu_ctgp_power_limit_controller: IntFeatureController
    gpu_ppab_power_limit_controller: IntFeatureController
    gpu_temperature_limit_controller: IntFeatureController
    # light
    ylogo_light_controller: BoolFeatureController
    ioport_light_controller: BoolFeatureController
    # deamon and automation
    power_profiles_deamon_service_controller: BoolFeatureController
    lenovo_legion_laptop_support_service_controller: BoolFeatureController
    legion_gui_autstart_controller: BoolFeatureController

    close_to_tray_controller:BoolFeatureController
    open_closed_to_tray:BoolFeatureController
    enable_gui_monitoring_controller:BoolFeatureController
    icon_color_mode_controller:EnumFeatureController

    # tray
    batteryconservation_tray_controller: BoolFeatureTrayController
    rapid_charging_tray_controller: BoolFeatureTrayController
    fnlock_tray_controller: BoolFeatureTrayController
    touchpad_tray_controller: BoolFeatureTrayController
    always_on_usb_tray_controller: BoolFeatureTrayController
    power_mode_tray_controller: EnumFeatureTrayController
    preset_tray_controller: PresetTrayController

    def __init__(self, app:QApplication, expect_hwmon=True, use_legion_cli_to_write=False):
        self.model = LegionModelFacade(
            expect_hwmon=expect_hwmon, use_legion_cli_to_write=use_legion_cli_to_write)
        self.app = app
        self.view_fancurve = None
        self.view_otheroptions = None
        self.main_window = None
        self.log_view = None
        self.tray = None
        self.view_automation = None
        self.show_root_dialog = (not self.model.is_root_user()) and (
            not use_legion_cli_to_write)
        self.monitoring_threadpool = QThreadPool()
        self.monitoring_worker = MonitorWorker(None)

    def init(self, read_from_hw=True):
        # connect logger output to GUI
        qt_handler.qt_obj.logWritten.connect(self.on_new_log_msg)

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
        self.winkey_controller = BoolFeatureController(
            self.view_otheroptions.winkey_check,
            self.model.winkey)
        self.touchpad_controller = BoolFeatureController(
            self.view_otheroptions.touchpad_check,
            self.model.touchpad)
        self.camera_power_controller = BoolFeatureController(
            self.view_otheroptions.camera_power_check,
            self.model.camera_power)
        self.overdrive_controller = BoolFeatureController(
            self.view_otheroptions.overdrive_check,
            self.model.overdrive)
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
        self.power_mode_controller = EnumFeatureController(
            self.view_otheroptions.power_mode_combo,
            self.model.platform_profile
        )
        self.hybrid_gsync_controller = HybridGsyncController(
            gsynchybrid_feature=self.model.gsync,
            current_state_label=self.view_otheroptions.hybrid_state_label,
            activate_button=self.view_otheroptions.hybrid_activate_button,
            deactivate_button=self.view_otheroptions.hybrid_deactivate_button)

        # power limits
        self.cpu_overclock = BoolFeatureController(
            self.view_otheroptions.cpu_overclock_ckeck,
            self.model.cpu_overclock)
        self.gpu_overclock = BoolFeatureController(
            self.view_otheroptions.gpu_overclock_check,
            self.model.gpu_overclock)
        self.cpu_longterm_power_limit_controller = IntFeatureController(
            self.view_otheroptions.cpu_longterm_power_limit_spinbox,
            self.model.cpu_longterm_power_limit)
        self.cpu_shortterm_power_limit_controller = IntFeatureController(
            self.view_otheroptions.cpu_shortterm_power_limit_spinbox,
            self.model.cpu_shortterm_power_limit)
        self.cpu_peak_power_limit_controller = IntFeatureController(
            self.view_otheroptions.cpu_peak_power_limit_spinbox,
            self.model.cpu_peak_power_limit)
        self.cpu_cross_loading_power_limit_controller = IntFeatureController(
            self.view_otheroptions.cpu_cross_loading_power_limit_spinbox,
            self.model.cpu_cross_loading_power_limit)
        self.cpu_apu_sppt_power_limit_controller = IntFeatureController(
            self.view_otheroptions.cpu_apu_sppt_power_limit_spinbox,
            self.model.cpu_apu_sppt_power_limit)
        self.gpu_ctgp_power_limit_controller = IntFeatureController(
            self.view_otheroptions.gpu_ctgp_power_limit_spinbox,
            self.model.gpu_ctgp_power_limit)
        self.gpu_ppab_power_limit_controller = IntFeatureController(
            self.view_otheroptions.gpu_ppab_power_limit_spinbox,
            self.model.gpu_ppab_power_limit)
        self.gpu_temperature_limit_controller = IntFeatureController(
            self.view_otheroptions.gpu_temperature_limit_spinbox,
            self.model.gpu_temperature_limit)

        # light
        self.ylogo_light_controller = BoolFeatureController(
            self.view_otheroptions.ylogo_light_check,
            self.model.ylogo_light)
        self.ioport_light_controller = BoolFeatureController(
            self.view_otheroptions.ioport_light_check,
            self.model.ioport_light)

        # services and automation
        self.power_profiles_deamon_service_controller = BoolFeatureController(
            self.view_automation.power_profiles_deamon_service_check,
            self.model.power_profiles_deamon_service
        )
        self.lenovo_legion_laptop_support_service_controller = BoolFeatureController(
            self.view_automation.lenovo_legion_laptop_support_service_check,
            self.model.lenovo_legion_laptop_support_service
        )
        self.legion_gui_autstart_controller = BoolFeatureController(
            self.view_automation.legion_gui_autostart_check,
            self.model.legion_gui_autostart
        )
        self.close_to_tray_controller = BoolFeatureController(
            self.view_automation.close_to_tray_check,
            self.model.app_model.close_to_tray
        )
        self.open_closed_to_tray = BoolFeatureController(
            self.view_automation.open_closed_to_tray_check,
            self.model.app_model.open_closed_to_tray
        )
        self.enable_gui_monitoring_controller = BoolFeatureController(
            self.view_automation.enable_gui_monitoring_check,
            self.model.app_model.enable_gui_monitoring
        )
        self.model.app_model.enable_gui_monitoring.add_callback(self.on_enable_monitoring_change)
        self.icon_color_mode_controller = EnumFeatureController(
            self.view_automation.icon_color_mode_combobox,
            self.model.app_model.icon_color_mode
        )
        self.icon_color_mode_controller.update_view_from_feature(0, True)

        if read_from_hw:
            self.model.read_fancurve_from_hw()
            # fan controller
        # fan
        self.update_fancurve_gui()
        self.update_fan_additional_gui()
        self.update_other_gui()
        self.update_power_gui(True)
        self.update_automation()
        self.view_fancurve.set_presets(self.model.fancurve_repo.get_names())
        self.main_window.show_root_dialog = self.show_root_dialog

    def init_tray(self):
        # tray/other
        self.batteryconservation_tray_controller = BoolFeatureTrayController(
            self.tray.batteryconservation_action, self.model.battery_conservation)
        set_dependent(self.batteryconservation_controller,
                      self.batteryconservation_tray_controller)
        set_dependent(self.rapid_charging_controller,
                      self.batteryconservation_tray_controller)
        self.batteryconservation_tray_controller.update_view_from_feature()

        self.rapid_charging_tray_controller = BoolFeatureTrayController(
            self.tray.rapid_charging_action, self.model.rapid_charging)
        set_dependent(self.batteryconservation_controller,
                      self.rapid_charging_tray_controller)
        set_dependent(self.rapid_charging_controller,
                      self.rapid_charging_tray_controller)
        set_dependent(self.batteryconservation_tray_controller,
                      self.rapid_charging_tray_controller)
        self.rapid_charging_tray_controller.update_view_from_feature()


        self.fnlock_tray_controller = BoolFeatureTrayController(
            self.tray.fnlock_action, self.model.fn_lock)
        set_dependent(self.fnlock_tray_controller, self.fnlock_controller)
        self.fnlock_tray_controller.update_view_from_feature()

        self.touchpad_tray_controller = BoolFeatureTrayController(
            self.tray.touchpad_action, self.model.touchpad)
        set_dependent(self.touchpad_tray_controller, self.touchpad_controller)
        self.touchpad_tray_controller.update_view_from_feature()

        self.always_on_usb_tray_controller = BoolFeatureTrayController(
            self.tray.always_on_usb_charging_action, self.model.always_on_usb_charging)
        set_dependent(self.always_on_usb_tray_controller, self.always_on_usb_controller)
        self.always_on_usb_tray_controller.update_view_from_feature()

        self.power_mode_tray_controller = EnumFeatureTrayController(self.model.platform_profile,
            [self.tray.powermode1_action,
             self.tray.powermode2_action,
             self.tray.powermode3_action,
             self.tray.powermode4_action])
        set_dependent(self.power_mode_tray_controller, self.power_mode_controller)
        self.power_mode_tray_controller.update_view_from_feature()

        self.preset_tray_controller = PresetTrayController(self.model,
            [self.tray.preset1_action,
             self.tray.preset2_action,
             self.tray.preset3_action,
             self.tray.preset4_action,
             self.tray.preset5_action,
             self.tray.preset6_action,
             self.tray.preset7_action,
             self.tray.preset8_action])

    def update_fan_additional_gui(self):
        self.lockfancontroller_controller.update_view_from_feature()
        self.maximumfanspeed_controller.update_view_from_feature()

    def update_other_gui(self):
        self.fnlock_controller.update_view_from_feature()
        self.winkey_controller.update_view_from_feature()
        self.touchpad_controller.update_view_from_feature()
        self.camera_power_controller.update_view_from_feature()
        self.batteryconservation_controller.update_view_from_feature()
        self.rapid_charging_controller.update_view_from_feature()
        self.always_on_usb_controller.update_view_from_feature()
        self.cpu_overclock.update_view_from_feature()
        self.gpu_overclock.update_view_from_feature()
        self.overdrive_controller.update_view_from_feature()
        self.hybrid_gsync_controller.update_view_from_feature()

    def update_power_gui(self, update_bounds=False):
        self.power_mode_controller.update_view_from_feature(
            0, update_items=update_bounds)
        self.cpu_longterm_power_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)
        self.cpu_shortterm_power_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)
        self.cpu_peak_power_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)
        self.cpu_cross_loading_power_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)
        self.cpu_apu_sppt_power_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)
        self.gpu_ctgp_power_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)
        self.gpu_ppab_power_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)
        self.gpu_temperature_limit_controller.update_view_from_feature(
            update_bounds=update_bounds)

    def power_gui_write_to_hw(self):
        self.cpu_longterm_power_limit_controller.update_feature_from_view(
            False)
        self.cpu_shortterm_power_limit_controller.update_feature_from_view(
            False)
        self.cpu_peak_power_limit_controller.update_feature_from_view(False)
        self.cpu_cross_loading_power_limit_controller.update_feature_from_view(
            False)
        self.cpu_apu_sppt_power_limit_controller.update_feature_from_view(
            False)
        self.gpu_ctgp_power_limit_controller.update_feature_from_view(False)
        self.gpu_ppab_power_limit_controller.update_feature_from_view(False)
        self.gpu_temperature_limit_controller.update_feature_from_view(False)
        self.update_power_gui()

    def update_fancurve_gui(self):
        self.view_fancurve.set_fancurve(self.model.fan_curve,
                                        self.model.fancurve_io.has_minifancurve(),
                                        self.model.fancurve_io.exists())

    def update_automation(self):
        self.power_profiles_deamon_service_controller.update_view_from_feature()
        self.lenovo_legion_laptop_support_service_controller.update_view_from_feature()
        self.close_to_tray_controller.update_view_from_feature()
        self.open_closed_to_tray.update_view_from_feature()
        self.legion_gui_autstart_controller.update_view_from_feature()
        self.enable_gui_monitoring_controller.update_view_from_feature()
        self.icon_color_mode_controller.update_view_from_feature()

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

    def on_new_log_msg(self, msg):
        self.log_view.log_out.insertPlainText(msg+'\n')

    def save_settings(self):
        try:
            self.model.save_settings()
        except PermissionError as err:
            log_error(err)

    def app_close_and_save(self):
        self.stop_monitoring()
        self.save_settings()
        self.app.quit()

    def app_close(self):
        self.stop_monitoring()
        self.app.quit()

    def app_show(self):
        self.main_window.bring_to_foreground()

    def start_monitoring(self):
        log.info("Starting monitoring")
        if not self.monitoring_worker.running:
            self.monitoring_worker = MonitorWorker(self.model)
            self.monitoring_worker.running = True
            self.monitoring_threadpool.start(self.monitoring_worker)

    def stop_monitoring(self):
        log.info("Stopping monitoring")
        self.monitoring_worker.running = False

    def on_enable_monitoring_change(self, _):
        if self.model.app_model.enable_gui_monitoring.get():
            self.start_monitoring()
        else:
            self.stop_monitoring()


class FanCurveEntryView():
    def __init__(self, point_id, layout):
        self.point_id_label = QLabel(f'{point_id}')
        self.point_id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        fan1_speed = float(self.fan_speed1_edit.text())
        fan2_speed = float(self.fan_speed2_edit.text())
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
        self.cpu_lower_temp_label = QLabel("CPU Lower Temp. [°C]")
        self.cpu_upper_temp_label = QLabel("CPU Upper Temp. [°C]")
        self.gpu_lower_temp_label = QLabel("GPU Lower Temp. [°C]")
        self.gpu_upper_temp_label = QLabel("GPU Upper Temp. [°C]")
        self.ic_lower_temp_label = QLabel("IC Lower Temp. [°C]")
        self.ic_upper_temp_label = QLabel("IC Upper Temp. [°C]")
        self.accel_label = QLabel("Acceleration  Time [s]")
        self.decel_label = QLabel("Deceleration Time [s]")
        self.minfancurve_check = QCheckBox("Minifancurve if too cold")
        self.lockfancontroller_check = QCheckBox(
            "Lock fan controller, lock temperature sensors, and lock current fan speed")
        self.maximumfanspeed_check = QCheckBox(
            "Set speed to maximum fan speed (often only in custom power mode possible)")
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
        self.layout.addWidget(self.minfancurve_check, 11, 0, 1, 10)
        self.layout.addWidget(self.lockfancontroller_check, 12, 0, 1, 10)
        self.layout.addWidget(self.maximumfanspeed_check, 13, 0, 1, 10)
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
            "the driver is not loaded properly or hwmon directory not found.\nIf features are marked "
            "red, an unexpected error has occured while accessing the hardware and you should notify the maintainer.")
        self.note_label2.setStyleSheet("color: red;")
        self.note_label2.setWordWrap(True)
        self.main_layout.addWidget(self.note_label2, 3)

        self.setLayout(self.main_layout)


class OtherOptionsTab(QWidget):
    def __init__(self, controller: LegionController):
        super().__init__()
        self.controller = controller
        self.init_power_ui()
        self.init_ui()
        self.controller.view_otheroptions = self

    def init_ui(self):
        self.options_group = QGroupBox("Options")
        self.options_layout = QVBoxLayout()
        self.options_group.setLayout(self.options_layout)

        self.fnlock_check = QCheckBox(
            "Fn Lock (Use special function of F1-F12 keys without pressing Fn; same as Fn + Esc)")
        self.options_layout.addWidget(self.fnlock_check, 0)

        self.winkey_check = QCheckBox(
            "Win Key Enabled")
        self.options_layout.addWidget(self.winkey_check, 0)

        self.touchpad_check = QCheckBox(
            "Touchpad Enabled (Lock or unlock touchpad; same as Fn + F10)")
        self.options_layout.addWidget(self.touchpad_check, 1)

        self.camera_power_check = QCheckBox(
            "Camera Power Enabled")
        self.options_layout.addWidget(self.camera_power_check, 0)

        self.batteryconservation_check = QCheckBox(
            "Battery Conservation (keep battery at about 50 percent and do not charge on AC to extend battery life)")
        self.options_layout.addWidget(self.batteryconservation_check, 2)

        self.rapid_charging_check = QCheckBox(
            "Rapid Charging")
        self.options_layout.addWidget(self.rapid_charging_check, 3)

        self.always_on_usb_check = QCheckBox(
            "Charge Output from USB always on")
        self.options_layout.addWidget(self.always_on_usb_check, 4)

        self.overdrive_check = QCheckBox(
            "Display Overdrive Enabled")
        self.options_layout.addWidget(self.overdrive_check, 5)

        self.ylogo_light_check = QCheckBox(
            "Y-Logo/Lid LED light")
        self.options_layout.addWidget(self.ylogo_light_check, 5)

        self.ioport_light_check = QCheckBox(
            "IO-Port/Rear LEDs light")
        self.options_layout.addWidget(self.ioport_light_check, 5)

        self.hybrid_label = QLabel('Hybrid Mode (sometimes also GSync):')
        self.hybrid_state_label = QLabel('')
        self.hybrid_activate_button = QPushButton('Activate')
        self.hybrid_deactivate_button = QPushButton('Deactivate')
        self.hybrid_layout = QHBoxLayout()
        self.hybrid_layout.addWidget(self.hybrid_label)
        self.hybrid_layout.addWidget(self.hybrid_activate_button)
        self.hybrid_layout.addWidget(self.hybrid_deactivate_button)
        self.hybrid_layout.addWidget(self.hybrid_state_label)

        self.options_layout.addLayout(self.hybrid_layout, 6)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.options_group, 0)
        self.main_layout.addWidget(self.power_group, 1)
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)

    def init_power_ui(self):
        # pylint: disable=too-many-statements
        self.power_group = QGroupBox("Power Options")
        self.power_all_layout = QVBoxLayout()
        self.power_group.setLayout(self.power_all_layout)

        self.power_layout = QGridLayout()
        self.power_all_layout.addLayout(self.power_layout, 0)

        self.power_mode_label = QLabel(
            'Power mode/platform profile:')
        self.power_mode_combo = QComboBox()
        self.power_layout.addWidget(self.power_mode_label, 0, 0)
        self.power_layout.addWidget(self.power_mode_combo, 0, 1)

        self.cpu_overclock_ckeck = QCheckBox(
            "CPU Overclock")
        self.power_layout.addWidget(self.cpu_overclock_ckeck, 1, 0)

        self.gpu_overclock_check = QCheckBox(
            "GPU Overclock")
        self.power_layout.addWidget(self.gpu_overclock_check, 1, 1)

        self.cpu_longterm_power_limit_spinbox_label = QLabel(
            "CPU Long Term Power Limit [W]")
        self.cpu_longterm_power_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.cpu_longterm_power_limit_spinbox_label, 3, 0)
        self.power_layout.addWidget(
            self.cpu_longterm_power_limit_spinbox, 3, 1)

        self.cpu_shortterm_power_limit_spinbox_label = QLabel(
            "CPU Short Term Power Limit [W]")
        self.cpu_shortterm_power_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.cpu_shortterm_power_limit_spinbox_label, 4, 0)
        self.power_layout.addWidget(
            self.cpu_shortterm_power_limit_spinbox, 4, 1)

        self.cpu_peak_power_limit_spinbox_label = QLabel(
            "CPU Peak Power Limit [W]")
        self.cpu_peak_power_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.cpu_peak_power_limit_spinbox_label, 5, 0)
        self.power_layout.addWidget(self.cpu_peak_power_limit_spinbox, 5, 1)

        self.cpu_cross_loading_power_limit_spinbox_label = QLabel(
            "CPU Cross Loading Power Limit [W]")
        self.cpu_cross_loading_power_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.cpu_cross_loading_power_limit_spinbox_label, 6, 0)
        self.power_layout.addWidget(
            self.cpu_cross_loading_power_limit_spinbox, 6, 1)

        self.cpu_apu_sppt_power_limit_spinbox_label = QLabel(
            "CPU APU SPPT Power Limit [W]")
        self.cpu_apu_sppt_power_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.cpu_apu_sppt_power_limit_spinbox_label, 7, 0)
        self.power_layout.addWidget(
            self.cpu_apu_sppt_power_limit_spinbox, 7, 1)

        self.gpu_ctgp_power_limit_spinbox_label = QLabel(
            "GPU cTGP Power Limit [W]")
        self.gpu_ctgp_power_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.gpu_ctgp_power_limit_spinbox_label, 8, 0)
        self.power_layout.addWidget(
            self.gpu_ctgp_power_limit_spinbox, 8, 1)

        self.gpu_ppab_power_limit_spinbox_label = QLabel(
            "GPU PPAB Power Limit [W]")
        self.gpu_ppab_power_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.gpu_ppab_power_limit_spinbox_label, 9, 0)
        self.power_layout.addWidget(
            self.gpu_ppab_power_limit_spinbox, 9, 1)

        self.gpu_temperature_limit_spinbox_label = QLabel(
            "GPU Temperature Limit [°C]")
        self.gpu_temperature_limit_spinbox = QSpinBox()
        self.power_layout.addWidget(
            self.gpu_temperature_limit_spinbox_label, 10, 0)
        self.power_layout.addWidget(
            self.gpu_temperature_limit_spinbox, 10, 1)

        self.power_load_button = QPushButton("Read from HW")
        self.power_write_button = QPushButton("Apply to HW")
        self.power_load_button.clicked.connect(
            self.controller.update_power_gui)
        self.power_write_button.clicked.connect(
            self.controller.power_gui_write_to_hw)
        self.power_layout.addWidget(self.power_load_button, 11, 0)
        self.power_layout.addWidget(self.power_write_button, 11, 1)

        self.power_note_label = QLabel(
            "It is recommended to customize the power settings only in custom mode. Although "
            "it is possible to change them in any mode.")
        self.power_note_label.setStyleSheet("color: red;")
        self.power_note_label.setWordWrap(True)
        self.power_all_layout.addWidget(self.power_note_label)


class AutomationTab(QWidget):
    def __init__(self, controller: LegionController):
        super().__init__()
        self.controller = controller
        self.init_ui()
        self.controller.view_automation = self

    def init_ui(self):
        self.options_group = QGroupBox("Systemd Services")
        self.options_layout = QVBoxLayout()
        self.options_group.setLayout(self.options_layout)

        self.power_profiles_deamon_service_check = QCheckBox(
            "Power Profiles Daemon Enabled")
        self.options_layout.addWidget(
            self.power_profiles_deamon_service_check, 0)

        self.lenovo_legion_laptop_support_service_check = QCheckBox(
            "Lenovo Legion Laptop Support Daemon Enabled")
        self.options_layout.addWidget(
            self.lenovo_legion_laptop_support_service_check, 1)

        self.legion_gui_autostart_check = QCheckBox(
            "Autostart Legion GUI on Session Startup")
        self.options_layout.addWidget(
            self.legion_gui_autostart_check, 1)


        self.close_to_tray_check = QCheckBox(
            "Close Legion GUI to Tray")
        self.options_layout.addWidget(
            self.close_to_tray_check, 2)

        self.open_closed_to_tray_check = QCheckBox(
            "Open Legion GUI Closed to Tray")
        self.options_layout.addWidget(
            self.open_closed_to_tray_check, 3)

        self.icon_color_mode_label = QLabel(
            'Icon Color Mode (requires reopening the app)')
        self.options_layout.addWidget(
            self.icon_color_mode_label, 3)
        self.icon_color_mode_combobox = QComboBox()
        self.options_layout.addWidget(
            self.icon_color_mode_combobox, 3)

        self.enable_gui_monitoring_check = QCheckBox(
            "Enable Monitoring while GUI is Running")
        self.options_layout.addWidget(
            self.enable_gui_monitoring_check, 3)

        self.note_label = QLabel(
            'These are Experimental Features.\n To apply and save the Settings Press "Save" or "Save and Quit"')
        self.options_layout.addWidget(self.note_label, 4)

        self.note_openrc_label = QLabel(
            "OpenRC service are available but need to be enable manually!\n"
            "They are install automatically on gentoo base distro!\n"
            "To get the files go to extra/service in the repo.\n"
        )
        self.options_layout.addWidget(self.note_openrc_label, 4)

        self.note_label2 = QLabel("")

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.options_group, 0)
        self.main_layout.addWidget(self.note_label2, 4)
        self.setLayout(self.main_layout)

# pylint: disable=too-few-public-methods


class LogTab(QWidget):
    def __init__(self, controller):
        super().__init__()
        controller.log_view = self
        self.init_ui()

    def init_ui(self):
        self.log_out = QTextBrowser(self)

        layout = QVBoxLayout()
        layout.addWidget(self.log_out)
        self.setLayout(layout)

# pylint: disable=too-few-public-methods
class AboutTab(QWidget):
    def __init__(self, _):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # pylint: disable=line-too-long
        about_label = QLabel(
            'Help by giving a star to the github repo <a href="https://github.com/johnfanv2/LenovoLegionLinux" >https://github.com/johnfanv2/LenovoLegionLinux</a>')
        about_label.setOpenExternalLinks(True)
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(about_label)
        self.setLayout(layout)

# pylint: disable=too-few-public-methods
class Tabs(QTabWidget):
    def __init__(self, controller):
        super().__init__()
        # setup controller
        self.controller = controller
        self.controller.tabs = self

        # setup tabs
        self.tabs = (
            ("Fan Curve", FanCurveTab(controller)),
            ("Other Options", OtherOptionsTab(controller)),
            ("Automation", AutomationTab(controller)),
            ("Log", LogTab(controller)),
            ("About", AboutTab(controller))
        )

        for tab_name, tab in self.tabs:
            area = QScrollArea()
            area.setWidget(tab)
            area.setWidgetResizable(True)
            self.addTab(area, tab_name)


class QClickLabel(QLabel):
    clicked = QtCore.pyqtSignal()

    # pylint: disable=invalid-name
    def mousePressEvent(self, _):
        self.clicked.emit()

# pylint: disable=too-few-public-methods


class MainWindow(QMainWindow):
    controller:LegionController

    def __init__(self, controller:LegionController, icon:QtGui.QIcon):
        super().__init__()
        # setup controller
        self.controller = controller
        self.controller.main_window = self

        # Set a minium width to the window
        self.setMinimumSize(1250, 725)

        # window layout
        self.setWindowTitle("LenovoLegionLinux")
        self.icon = icon
        self.setWindowIcon(self.icon)

        # header message
        self.header_msg = QClickLabel()
        # self.header_msg.clicked.connect(open_star_link)
        self.set_random_header_msg()

        # tabs
        self.tabs = Tabs(controller)

        # bottom buttons
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(controller.app_close)
        self.ok_button = QPushButton("Save")
        self.ok_button.clicked.connect(controller.save_settings)
        self.ok_quit_button = QPushButton("Save and Quit")
        self.ok_quit_button.clicked.connect(controller.app_close_and_save)
        self.button_layout = QHBoxLayout()
        # Push to the right with strecht
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.quit_button)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.ok_quit_button)

        # main layout
        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.header_msg)
        self.main_layout.addWidget(self.tabs, 1)
        self.main_layout.addLayout(self.button_layout)

        # use main layout for main window
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)

        # set main widget
        self.setCentralWidget(self.main_widget)

        # display of root warning message
        self.show_root_dialog = False
        self.onstart_timer = QtCore.QTimer()
        self.onstart_timer.singleShot(0, self.on_start)

        # timer to automatically close window during testing in CI
        self.close_timer = QTimer()

    def set_header_msg(self, text: str):
        self.header_msg.setText(text)
        self.header_msg.setOpenExternalLinks(True)
        self.header_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_random_header_msg(self):
        # pylint: disable=line-too-long
        msgs = [
            'Show your appreciation for this tool by giving a star on github <a href="https://github.com/johnfanv2/LenovoLegionLinux" >https://github.com/johnfanv2/LenovoLegionLinux</a>',
            'Help by giving a star to the github repository <a href="https://github.com/johnfanv2/LenovoLegionLinux" >https://github.com/johnfanv2/LenovoLegionLinux</a>',
            'Please give a star on github to support. My goal is to merge the driver into the main Linux kernel,<br> so no recompilation is required after a Linux update <a href="https://github.com/johnfanv2/LenovoLegionLinux" >https://github.com/johnfanv2/LenovoLegionLinux</a'
            'Please give star on github the repository if this is useful or might be useful in the future <a href="https://github.com/johnfanv2/LenovoLegionLinux" >https://github.com/johnfanv2/LenovoLegionLinux</a>',
            'Please give a star on github to show that this it useful to me and the Linux community,<br> so hopefully the driver can be merged to the Linux kernel <a href="https://github.com/johnfanv2/LenovoLegionLinux" >https://github.com/johnfanv2/LenovoLegionLinux</a>'
        ]
        self.set_header_msg(random.choice(msgs))

    def on_start(self):
        if self.show_root_dialog:
            QMessageBox.critical(
                self, "Error", "The program must be run as root!")

        if self.controller.model.app_model.open_closed_to_tray.get():
            self.hide_to_tray()

    # pylint: disable=invalid-name
    def closeEvent(self, event):
        # Overide the close event of pyqt
        log.info("Received close event")
        if self.controller.model.app_model.close_to_tray.get():
            log.info("Ignore close event and hide to tray instead.")
            event.ignore()
            self.hide_to_tray()
        else:
            log.info("Accept close event and close.")
            self.controller.app_close()
            event.accept()

    def close_after(self, milliseconds: int):
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(milliseconds)

    def bring_to_foreground(self):
        self.setWindowFlag(QtCore.Qt.WindowType.Window)
        self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowType.Tool))
        self.setWindowState(self.windowState(
        ) & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
        self.activateWindow()
        self.show()

    def hide_to_tray(self):
        if not self.controller.model.is_root_user():
            # do not hide to tray when running as root because
            # a program run as root cannot usually
            # show a tray icon
            self.setWindowFlag(QtCore.Qt.WindowType.Tool)
            self.hide()


class LegionTray:
    def __init__(self, icon, main_window:QMainWindow, controller:LegionController):
        self.tray = QSystemTrayIcon(icon, main_window)
        self.tray.setIcon(icon)
        self.tray.setVisible(True)
        self.controller = controller

        self.menu = QMenu()
        def add_action(text):
            act = QAction(text)
            self.menu.addAction(act)
            return act

        # title
        self.title = QAction("Legion")
        self.title.setEnabled(False)
        self.menu.addAction(self.title)
        # ---
        self.menu.addSeparator()
        # open
        self.open_action = QAction("Show")
        self.open_action.triggered.connect(self.controller.app_show)
        self.menu.addAction(self.open_action)
        # quit
        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.controller.app_close)
        self.menu.addAction(self.quit_action)
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        # ---
        self.menu.addSeparator()
        self.batteryconservation_action = QAction("Conservation Mode")
        self.menu.addAction(self.batteryconservation_action)
        self.rapid_charging_action = QAction("Rapid Charging")
        self.menu.addAction(self.rapid_charging_action)
        self.fnlock_action = QAction("Fn Lock")
        self.menu.addAction(self.fnlock_action)
        self.touchpad_action = QAction("Touchpad Enabled")
        self.menu.addAction(self.touchpad_action)
        self.always_on_usb_charging_action = QAction("Always On USB Charging")
        self.menu.addAction(self.always_on_usb_charging_action)
        # ---
        self.menu.addSeparator()
        self.preset1_action = add_action("preset")
        self.preset2_action = add_action("preset")
        self.preset3_action = add_action("preset")
        self.preset4_action = add_action("preset")
        self.preset5_action = add_action("preset")
        self.preset6_action = add_action("preset")
        self.preset7_action = add_action("preset")
        self.preset8_action = add_action("preset")
        # ---
        self.menu.addSeparator()
        self.powermode1_action = add_action("powermode")
        self.powermode2_action = add_action("powermode")
        self.powermode3_action = add_action("powermode")
        self.powermode4_action = add_action("powermode")
        # ---
        self.menu.addSeparator()
        self.star_action = QAction(
            "Help giving a star to the github repo (click here)")
        self.star_action.triggered.connect(open_star_link)
        self.menu.addAction(self.star_action)

    def show_message(self, title):
        self.tray.setToolTip(title)
        self.tray.showMessage(title, title)

    def show(self):
        self.tray.show()


def get_ressource_path(name):
    path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), name)
    return path

# Disable linter error since this is simplier than refactored into lookup table
# with less branches
# pylint: disable=too-many-branches
def get_icon_path(controller):
    icon_color = 'color'
    if controller.model.app_model.icon_color_mode.get() == 'always-color':
        icon_color = 'color'
    elif controller.model.app_model.icon_color_mode.get() == 'always-light':
        icon_color = 'light'
    elif controller.model.app_model.icon_color_mode.get() == 'always-dark':
        icon_color = 'dark'
    elif controller.model.app_model.icon_color_mode.get() == 'automatic':
        color_mode = get_color_mode()
        log.info("Using color mode: %s", color_mode)
        if color_mode == 'dark':
            icon_color = 'dark'
        elif color_mode == 'light':
            icon_color = 'light'
        else:
            icon_color = 'color'
    elif controller.model.app_model.icon_color_mode.get() == 'automatic-inverted':
        color_mode = get_color_mode()
        log.info("Using color mode: %s", color_mode)
        if color_mode == 'dark':
            icon_color = 'light'
        elif color_mode == 'light':
            icon_color = 'dark'
        else:
            icon_color = 'color'

    log.info("Using icon_color %s", icon_color)
    if icon_color == 'dark':
        log.info("Using icon legion_logo_dark")
        icon_path = get_ressource_path('legion_logo_dark.png')
    elif icon_color == 'light':
        log.info("Using icon legion_logo_light")
        icon_path = get_ressource_path('legion_logo_light.png')
    else:
        log.info("Using icon legion_logo")
        icon_path = get_ressource_path('legion_logo.png')
    return icon_path

def main():
    # Set the desktop file name
    # This make the window icon appear on wayland
    QGuiApplication.setDesktopFileName("legion_gui.desktop")

    app = QApplication(sys.argv)

    use_legion_cli_to_write = '--use_legion_cli_to_write' in sys.argv
    do_not_excpect_hwmon = True
    controller = LegionController(app, expect_hwmon=not do_not_excpect_hwmon,
                             use_legion_cli_to_write=use_legion_cli_to_write)

    # Load savable settings from file if exists
    controller.model.load_settings()

    # Overwrite settings from commandline args
    if '--automaticclose' in sys.argv:
        controller.model.app_model.automatic_close.set(True)
    if '--close_to_tray' in sys.argv:
        controller.model.app_model.close_to_tray.set(True)
    if '--open_closed_to_tray' in sys.argv:
        controller.model.app_model.open_closed_to_tray.set(True)

    # Overwrite settings by rules
    if controller.model.is_root_user():
        # When GUI is run as root it usually cannot display
        # a icon in the tray due to security of XServer,
        # so disable opening or closing minimized in tray,
        # otherwise there is no way to close the program
        # except sending a kill signal
        #
        # https://forum.qt.io/topic/78464/system-tray-icon-missing-when-running-as-root/5
        controller.model.app_model.open_closed_to_tray.set(False)
        controller.model.app_model.close_to_tray.set(False)

    # Resources
    icon_path = get_icon_path(controller)
    icon = QtGui.QIcon(icon_path)
    # Set tray icon to the window icon
    # Can't be use since tray icon is a svg
    # Only support png and ico
    # (maybe if PyQT6 introduce svg support)
    #QGuiApplication.setWindowIcon(icon)

    # Main Windows
    main_window = MainWindow(controller, icon)
    controller.init(read_from_hw=not do_not_excpect_hwmon)

    # Tray
    tray = LegionTray(icon, main_window, controller)
    tray.show()
    controller.tray = tray
    controller.init_tray()

    # Start Windows
    if controller.model.app_model.automatic_close.get():
        main_window.close_after(3000)
    main_window.show()

    # Run
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
