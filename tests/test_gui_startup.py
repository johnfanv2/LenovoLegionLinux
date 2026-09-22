"""Run with QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p test_gui_startup.py."""

import logging
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python/legion_linux"))

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox
from legion_linux import legion
from legion_linux.legion import FanCurveIO, FileFeature
from legion_linux.legion_gui import LegionController, MainWindow


class GuiStartupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        logging.disable(logging.CRITICAL)

    def check_startup(self, hwmon_path, read_from_hw, supported):
        with patch.object(FanCurveIO, "_find_hwmon_dir", return_value=hwmon_path), patch.object(
            FileFeature,
            "_write_file",
            side_effect=AssertionError("Startup must not write to hardware"),
        ):
            controller = LegionController(
                self.app,
                expect_hwmon=hwmon_path is not None,
                use_legion_cli_to_write=True,
            )
            window = MainWindow(controller, QIcon())
            try:
                with patch.object(controller.model, "read_fancurve_from_hw") as read_curve:
                    controller.init(read_from_hw=read_from_hw)
                    self.assertEqual(read_curve.call_count, int(supported and read_from_hw))
                self.assertEqual(controller.view_fancurve.load_button.isEnabled(), supported)
                self.assertEqual(controller.view_fancurve.write_button.isEnabled(), supported)
                if hwmon_path and not supported:
                    self.assertIn("not supported", controller.view_fancurve.note_label2.text())
            finally:
                window.deleteLater()
                self.app.processEvents()

    def test_sensor_only_hwmon(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "fan1_input").write_text("2300\n")
            self.check_startup(directory + "/", True, False)

    def test_supported_fancurve(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "pwm1_auto_point1_pwm").write_text("64\n")
            self.check_startup(directory + "/", True, True)

    def test_offline_with_supported_hardware(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "pwm1_auto_point1_pwm").write_text("64\n")
            self.check_startup(directory + "/", False, True)

    def test_no_hwmon(self):
        self.check_startup(None, False, False)

    def test_load_from_preset_with_uninitialized_view(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # Default view entries have acceleration = 0, deceleration = 0.
            # Loading a preset must not be blocked by validating the uninitialized view.
            with patch.object(controller.model, "load_fancurve_from_preset") as mock_load, patch.object(
                controller, "update_fancurve_gui"
            ) as mock_update:
                controller.view_fancurve.preset_combobox.addItem("performance-ac")
                controller.view_fancurve.preset_combobox.setCurrentText("performance-ac")
                controller.on_load_from_preset()
                mock_load.assert_called_once_with("performance-ac")
                mock_update.assert_called_once()
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_write_ignores_padding_in_accel_validation(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # Simulate a preset or hardware read whose trailing entries are
            # all-zero EC padding (issue #493): real points 1-8 with valid
            # acceleration, padding points 9-10 with acceleration = 0.
            for entry_view in controller.view_fancurve.entry_edits[:8]:
                entry_view.fan_speed1_edit.setText("2000")
                entry_view.accel_edit.setText("2")
                entry_view.decel_edit.setText("2")
            with patch.object(controller.model, "write_fancurve_to_hw") as mock_write, patch.object(
                controller.model, "read_fancurve_from_hw"
            ), patch.object(controller, "update_fancurve_gui"):
                controller.on_write_fan_curve_to_hw()
                mock_write.assert_called_once()
                # Padding entries stay in the curve (FanCurveIO.write_fan_curve
                # trims them on write); only validation ignores them.
                self.assertEqual(len(controller.model.fan_curve.entries), 10)
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_write_rejects_out_of_range_accel_on_real_point(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # A real (non-padding) point with acceleration outside the
            # controller's 2-5 range must still block the write.
            entry_view = controller.view_fancurve.entry_edits[0]
            entry_view.fan_speed1_edit.setText("2000")
            entry_view.accel_edit.setText("1")
            entry_view.decel_edit.setText("2")
            with patch.object(
                controller.model.fancurve_io, "has_acceleration_curve", return_value=True
            ), patch.object(QMessageBox, "warning"), patch.object(
                controller.model, "write_fancurve_to_hw"
            ) as mock_write:
                controller.on_write_fan_curve_to_hw()
                mock_write.assert_not_called()
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_write_handles_runtime_error(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            with patch.object(
                controller.model, "write_fancurve_to_hw", side_effect=RuntimeError("legion_cli failed")
            ), patch.object(
                controller.model, "read_fancurve_from_hw"
            ) as mock_read, patch.object(
                controller, "update_fancurve_gui"
            ) as mock_update, patch.object(
                QMessageBox, "warning"
            ) as mock_warning:
                controller.on_write_fan_curve_to_hw()
                mock_warning.assert_called_once()
                mock_read.assert_not_called()
                mock_update.assert_not_called()
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_ec3_rpm_and_temperature_edit_roundtrip(self):
        # R3CN uses the EC3 RPM curve, not the shared WMI level table.
        # Its sysfs exposes both fans and temperatures, but no accel/decel.
        with tempfile.TemporaryDirectory() as directory:
            hwmon = Path(directory, "hwmon", "hwmon0")
            hwmon.mkdir(parents=True)
            for name in (FanCurveIO.fan1_max, FanCurveIO.fan2_max):
                (hwmon / name).write_text("10000\n")
            (hwmon / FanCurveIO.auto_points_size).write_text("10\n")
            patterns = (
                FanCurveIO.pwm1_fan_speed,
                FanCurveIO.pwm2_fan_speed,
                FanCurveIO.pwm1_temp_hyst,
                FanCurveIO.pwm1_temp,
                FanCurveIO.pwm2_temp_hyst,
                FanCurveIO.pwm2_temp,
                FanCurveIO.pwm3_temp_hyst,
                FanCurveIO.pwm3_temp,
            )
            for point_id in range(1, 11):
                for pattern in patterns:
                    (hwmon / pattern.format(point_id)).write_text("0\n")

            def write_existing(file_path, value):
                # Unlike normal files, sysfs cannot create unsupported attrs.
                self.assertTrue(Path(file_path).is_file(), file_path)
                self.assertEqual(Path(file_path).parent, hwmon)
                Path(file_path).write_text(str(value))

            with patch.object(legion, "LEGION_SYS_BASEPATH", directory), patch.object(
                FanCurveIO, "hwmon_dir_pattern", str(hwmon)
            ), patch.object(FanCurveIO, "_write_file", side_effect=write_existing), patch.object(
                FileFeature, "_write_file", side_effect=AssertionError("Must not write to real hardware")
            ), patch.object(
                # Direct writes target the fixture, not privileged sysfs.
                legion,
                "is_root_user",
                return_value=True,
            ), patch.object(
                QMessageBox, "warning"
            ) as warning:
                controller = LegionController(self.app, expect_hwmon=True, use_legion_cli_to_write=False)
                window = MainWindow(controller, QIcon())
                try:
                    controller.init(read_from_hw=True)
                    io = controller.model.fancurve_io
                    self.assertFalse(io.uses_fan_levels())
                    self.assertTrue(io.has_fan_2_speed())
                    self.assertTrue(io.has_temperature_curve())
                    self.assertFalse(io.has_acceleration_curve())
                    self.assertFalse(controller.view_fancurve.minfancurve_check.isEnabled())
                    entry = controller.view_fancurve.entry_edits[0]
                    fields = {
                        "fan_speed1_edit": "4500",
                        "fan_speed2_edit": "4600",
                        "cpu_lower_temp_edit": "50",
                        "cpu_upper_temp_edit": "80",
                        "gpu_lower_temp_edit": "45",
                        "gpu_upper_temp_edit": "75",
                        "ic_lower_temp_edit": "40",
                        "ic_upper_temp_edit": "70",
                    }
                    for name, value in fields.items():
                        field = getattr(entry, name)
                        self.assertTrue(field.isEnabled(), name)
                        field.setText(value)
                    self.assertFalse(entry.accel_edit.isEnabled())
                    self.assertFalse(entry.decel_edit.isEnabled())
                    controller.on_write_fan_curve_to_hw()
                    warning.assert_not_called()
                    for name, value in fields.items():
                        self.assertEqual(float(getattr(entry, name).text()), float(value))
                    # Native EC3 must retain zero RPM, unlike the WMI level path.
                    entry.fan_speed1_edit.setText("0")
                    controller.on_write_fan_curve_to_hw()
                    warning.assert_not_called()
                    self.assertEqual(io.get_fan_1_speed_rpm(1), 0)
                    self.assertEqual(io.get_fan_2_speed_rpm(1), 4600)
                    self.assertEqual(io.get_upper_cpu_temperature(1), 80)
                    for pattern in (FanCurveIO.pwm1_accel, FanCurveIO.pwm1_decel):
                        self.assertFalse((hwmon / pattern.format(1)).exists())
                finally:
                    window.deleteLater()
                    self.app.processEvents()

    def test_write_allows_zero_accel_when_acceleration_curve_unsupported(self):
        controller = LegionController(self.app, expect_hwmon=False, use_legion_cli_to_write=True)
        window = MainWindow(controller, QIcon())
        try:
            controller.init(read_from_hw=False)
            # On models without acceleration curves (wmi_fancurve_speed_only),
            # accel/decel are 0 and disabled in the UI. Writing a real point
            # with accel=0 must not be blocked by validation.
            entry_view = controller.view_fancurve.entry_edits[0]
            entry_view.fan_speed1_edit.setText("2000")
            entry_view.accel_edit.setText("0")
            entry_view.decel_edit.setText("0")
            with patch.object(
                controller.model.fancurve_io, "has_acceleration_curve", return_value=False
            ), patch.object(
                controller.model, "write_fancurve_to_hw"
            ) as mock_write, patch.object(
                controller.model, "read_fancurve_from_hw"
            ), patch.object(
                controller, "update_fancurve_gui"
            ):
                controller.on_write_fan_curve_to_hw()
                mock_write.assert_called_once()
        finally:
            window.deleteLater()
            self.app.processEvents()
