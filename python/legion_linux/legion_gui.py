#!/usr/bin/python3
import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QTabWidget, QWidget, QLabel, \
     QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QComboBox, QGroupBox, \
     QCheckBox
from legion import LegionModelFacade, FanCurve, FanCurveEntry

class LegionController:
    model:LegionModelFacade

    def __init__(self, expect_hwmon=True):
        self.model = LegionModelFacade(expect_hwmon=expect_hwmon)
        self.view_fancurve = None

    def init(self, read_from_hw=True):
        self.model.read_fancurve_from_hw()
        self.view_fancurve.set_fancurve(self.model.fan_curve)
        self.view_fancurve.set_fancurve(self.model.fan_curve)
        self.view_fancurve.set_presets(self.model.fancurve_repo.get_names())

    def on_read_fan_curve_from_hw(self):
        self.model.read_fancurve_from_hw()
        self.view_fancurve.set_fancurve(self.model.fan_curve)

    def on_write_fan_curve_to_hw(self):
        self.model.fan_curve = self.view_fancurve.get_fancurve()
        self.model.write_fancurve_to_hw()
        self.model.read_fancurve_from_hw()
        self.view_fancurve.set_fancurve(self.model.fan_curve)

    def on_load_from_preset(self):
        name = self.view_fancurve.preset_combobox.currentText()
        self.model.fan_curve = self.view_fancurve.get_fancurve()
        self.model.load_fancurve_from_preset(name)
        self.view_fancurve.set_fancurve(self.model.fan_curve)

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

    def set(self, entry:FanCurveEntry):
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

    def get(self) -> FanCurveEntry:
        fan1_speed =        int(self.fan_speed1_edit.text())
        fan2_speed =        int(self.fan_speed2_edit.text())
        cpu_lower_temp =    int(self.cpu_lower_temp_edit.text())
        cpu_upper_temp =    int(self.cpu_upper_temp_edit.text())
        gpu_lower_temp =    int(self.gpu_lower_temp_edit.text())
        gpu_upper_temp =    int(self.gpu_upper_temp_edit.text())
        ic_lower_temp =     int(self.ic_lower_temp_edit.text())
        ic_upper_temp =     int(self.ic_upper_temp_edit.text())
        acceleration =      int(self.accel_edit.text())
        deceleration =      int(self.decel_edit.text())
        entry = FanCurveEntry(fan1_speed=fan1_speed, fan2_speed=fan2_speed,
                                  cpu_lower_temp=cpu_lower_temp, cpu_upper_temp=cpu_upper_temp,
                                  gpu_lower_temp=gpu_lower_temp, gpu_upper_temp= gpu_upper_temp,
                                  ic_lower_temp=ic_lower_temp, ic_upper_temp=ic_upper_temp,
                                  acceleration=acceleration, deceleration=deceleration)
        return entry


class FanCurveTab(QWidget):
    def __init__(self, controller:LegionController):
        super().__init__()
        self.controller = controller
        self.entry_edits = []
        self.init_ui()

        self.controller.view_fancurve = self


    def set_fancurve(self, fancurve:FanCurve):
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
        self.fan_speed2_label = QLabel("Fan 1 Speed [rpm]")
        self.cpu_lower_temp_label = QLabel("CPU Lower Temp. [°C.]")
        self.cpu_upper_temp_label = QLabel("CPU Upper Temp. [°C.]")
        self.gpu_lower_temp_label = QLabel("GPU Lower Temp. [°C.]")
        self.gpu_upper_temp_label = QLabel("GPU Upper Temp. [°C.]")
        self.ic_lower_temp_label = QLabel("IC Lower Temp. [°C.]")
        self.ic_upper_temp_label = QLabel("IC Upper Temp. [°C.]")
        self.accel_label = QLabel("Acceleration [s]")
        self.decel_label = QLabel("Deceleration [s]")
        self.minfancurve_check = QCheckBox("Minifancurve if too cold")
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
        for i in range(1,11):
            self.create_fancurve_entry_view(self.layout, i)
        self.fancurve_group.setLayout(self.layout)

        self.button1_group = QGroupBox("Fancurve Hardware")
        self.button1_layout = QGridLayout()

        self.load_button = QPushButton("Read from HW")
        self.write_button = QPushButton("Apply to HW")
        self.note_label = QLabel("Fan curve is reset to default if you toggle power mode (Fn + Q)")
        self.load_button.clicked.connect(self.controller.on_read_fan_curve_from_hw)
        self.write_button.clicked.connect(self.controller.on_write_fan_curve_to_hw)
        self.button1_group.setLayout(self.button1_layout)
        self.button1_layout.addWidget(self.load_button, 0, 0)
        self.button1_layout.addWidget(self.write_button, 0, 1)
        self.button1_layout.addWidget(self.note_label, 1, 0)

        self.button2_group = QGroupBox("Fancurve Preset")
        self.button2_layout = QGridLayout()
        self.save_to_preset_button = QPushButton("Save to Preset")
        self.load_from_preset_button = QPushButton("Load from Preset")
        self.save_to_preset_button.clicked.connect(self.controller.on_save_to_preset)
        self.load_from_preset_button.clicked.connect(self.controller.on_load_from_preset)
        self.preset_combobox =  QComboBox(self)
        self.button2_group.setLayout(self.button2_layout)
        self.button2_layout.addWidget(self.preset_combobox, 0, 0)
        self.button2_layout.addWidget(self.save_to_preset_button, 1, 0)
        self.button2_layout.addWidget(self.load_from_preset_button, 1, 1)


        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.button1_group, 1, 0)
        self.main_layout.addWidget(self.button2_group, 2, 0)
        self.main_layout.addWidget(self.fancurve_group, 0, 0)

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
        self.fan_curve_tab = FanCurveTab(controller)
        self.about_tab = AboutTab()
        self.close_timer = QTimer()
        self.addTab(self.fan_curve_tab, "Fan Curve")
        self.addTab(self.about_tab, "About")

    def close_after(self, milliseconds:int):
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(milliseconds)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    AUTOMATIC_CLOSE = '--automaticclose' in sys.argv
    DO_NOT_EXPECT_HWMON = '--donotexpecthwmon' in sys.argv

    contr = LegionController(expect_hwmon=not DO_NOT_EXPECT_HWMON)
    main_window = MainWindow(contr)
    main_window.setWindowTitle("LenovoLegionLinux")
    contr.init(read_from_hw= not DO_NOT_EXPECT_HWMON)
    contr.model.fancurve_repo.create_preset_folder()
    if AUTOMATIC_CLOSE:
        main_window.close_after(3000)
    main_window.show()
    sys.exit(app.exec_())
