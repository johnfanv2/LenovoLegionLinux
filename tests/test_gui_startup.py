"""Run with QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p test_gui_startup.py."""

import logging
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python/legion_linux"))

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
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
