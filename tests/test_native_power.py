"""Exercise native power controls using temporary files, without hardware writes."""

import glob
import logging
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python/legion_linux"))

from PyQt6.QtWidgets import QApplication, QSpinBox
from legion_linux.legion import (
    LEGION_SYS_BASEPATH,
    CPULongtermPowerLimit,
    CPUShorttermPowerLimit,
    FileFeature,
    PlatformProfileFeature,
)
from legion_linux.legion_gui import IntFeatureController


class NativePowerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        logging.disable(logging.CRITICAL)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.lookup = patch.object(FileFeature, "_find_by_file_pattern", side_effect=self.find_files)
        self.lookup.start()
        self.addCleanup(self.lookup.stop)

    def find_files(self, patterns):
        for pattern in patterns if isinstance(patterns, list) else [patterns]:
            matches = glob.glob(str(self.root) + pattern)
            if matches:
                return matches[0]
        return None

    def write(self, name, value):
        path = self.root / name.lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(value))
        return path

    def native(self, attribute="ppt_pl1_spl", value=70):
        base = "/sys/class/firmware-attributes/lenovo-wmi-other-0/attributes/" + attribute
        for name, content in (("current_value", value), ("min_value", 50), ("max_value", 95), ("scalar_increment", 5)):
            self.write(base + "/" + name, content)
        return base

    def test_native_preferred_and_both_cpu_mappings(self):
        self.native()
        self.native("ppt_pl2_sppt", 125)
        self.write(LEGION_SYS_BASEPATH + "/cpu_longterm_powerlimit", 0)
        self.assertEqual(CPULongtermPowerLimit().get(), 70)
        self.assertEqual(CPUShorttermPowerLimit().get(), 125)
        self.assertEqual(CPULongtermPowerLimit().get_limits_and_step(), (50, 95, 5))

    def test_legacy_fallback(self):
        path = self.write(LEGION_SYS_BASEPATH + "/cpu_longterm_powerlimit", 60)
        feature = CPULongtermPowerLimit()
        self.assertFalse(feature.uses_native_interface())
        feature.set_str_value("65")
        self.assertEqual(path.read_text(), "65")

    def test_unchanged_value_does_not_write_or_require_profile(self):
        self.native()
        feature = CPULongtermPowerLimit()
        with patch.object(feature, "_write_file") as write:
            feature.set(70)
            feature.set_str_value("70")
            write.assert_not_called()

    def test_gui_and_cli_reject_wrong_mode_range_and_step(self):
        self.native()
        feature = CPULongtermPowerLimit()
        for setter in (feature.set, feature.set_str_value):
            for mode, value in (("performance", 75), ("custom", 100), ("custom", 73)):
                with self.subTest(mode=mode, value=value, setter=setter.__name__):
                    with patch.object(Path, "read_text", return_value=mode), patch.object(
                        feature, "_write_file"
                    ) as write:
                        with self.assertRaises(ValueError):
                            setter(str(value))
                        write.assert_not_called()

    def test_valid_custom_mode_write(self):
        base = self.native()
        feature = CPULongtermPowerLimit()
        with patch.object(Path, "read_text", return_value="custom"):
            feature.set(75)
            feature.set_str_value("80")
        self.assertEqual((self.root / (base + "/current_value").lstrip("/")).read_text(), "80")

    def test_missing_profile_blocks_write(self):
        self.native()
        feature = CPULongtermPowerLimit()
        with patch.object(Path, "read_text", side_effect=FileNotFoundError), patch.object(
            feature, "_write_file"
        ) as write:
            with self.assertRaises(FileNotFoundError):
                feature.set_str_value("75")
            write.assert_not_called()

    def test_profile_fallback_and_legion_precedence(self):
        self.write("/sys/firmware/acpi/platform_profile", "performance")
        self.write("/sys/firmware/acpi/platform_profile_choices", "balanced performance custom")
        native = PlatformProfileFeature()
        self.assertEqual(native.get(), "performance")
        self.assertEqual({item.value for item in native.get_values()}, {"balanced", "performance", "custom"})
        base = LEGION_SYS_BASEPATH + "/platform-profile/platform-profile-12/"
        self.write(base + "profile", "balanced")
        self.write(base + "choices", "balanced performance")
        legion = PlatformProfileFeature()
        self.assertEqual(legion.get(), "balanced")
        self.assertEqual({item.value for item in legion.get_values()}, {"balanced", "performance"})

    def test_reading_outside_custom_bounds_is_not_clamped_or_written(self):
        self.native(value=125)
        feature = CPULongtermPowerLimit()
        widget = QSpinBox()
        with patch.object(feature, "_write_file") as write:
            controller = IntFeatureController(widget, feature)
            controller.update_view_from_feature(update_bounds=True)
            self.assertEqual(widget.value(), 125)
            self.assertEqual(widget.singleStep(), 5)
            controller.update_feature_from_view(wait=False)
            write.assert_not_called()
