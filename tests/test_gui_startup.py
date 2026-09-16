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
            with patch.object(QMessageBox, "warning"), patch.object(
                controller.model, "write_fancurve_to_hw"
            ) as mock_write:
                controller.on_write_fan_curve_to_hw()
                mock_write.assert_not_called()
        finally:
            window.deleteLater()
            self.app.processEvents()
