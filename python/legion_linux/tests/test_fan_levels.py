# pylint: disable=missing-docstring,too-many-public-methods,protected-access
"""Unit tests for the fan level (FAN_SPEED_UNIT_LEVEL) RPM conversion helpers.

The per-fan RPM ladders are read from the kernel module's platform device
sysfs attributes (which derive them from the firmware's LENOVO_FAN_TABLE_DATA
WMI block); these tests mock that sysfs access and cover the conversion and
fallback behaviour of legion.py.
"""

import argparse
import unittest
from unittest import mock

from legion_linux import legion
from legion_linux.legion_cli import MiniFancurveFeatureCommand

FAN1_LADDER = [1700, 1900, 2100, 2300, 2500, 2900, 3400, 3700, 4400, 5400]
FAN2_LADDER = [1700, 1900, 2100, 2200, 2700, 2900, 3500, 3700, 4600, 5400]


def fake_sysfs(files):
    """Build an open() mock serving the given {filename: content} mapping."""

    def fake_open(path, *args, **kwargs):
        for name, content in files.items():
            if str(path).endswith(name):
                file_object = mock.MagicMock()
                file_object.__enter__.return_value.read.return_value = content
                return file_object
        raise FileNotFoundError(f"No such file: {path}")

    return mock.patch("builtins.open", side_effect=fake_open)


class ReadFanLevelRpmTablesTest(unittest.TestCase):
    def read_with_files(self, files):
        with mock.patch.object(legion, "LEGION_SYS_BASEPATH", "/fake/sys/path"):
            with fake_sysfs(files):
                return legion.read_fan_level_rpm_tables()

    def test_both_fans(self):
        fan1, fan2 = self.read_with_files(
            {
                "fan1_level_rpm_table": "1700 1900 2100 2300 2500 2900 3400 3700 4400 5400\n",
                "fan2_level_rpm_table": "1700 1900 2100 2200 2700 2900 3500 3700 4600 5400\n",
            }
        )
        self.assertEqual(fan1, FAN1_LADDER)
        self.assertEqual(fan2, FAN2_LADDER)

    def test_fan2_missing_falls_back_to_none_entry(self):
        fan1, fan2 = self.read_with_files({"fan1_level_rpm_table": "1700 5400\n"})
        self.assertEqual(fan1, [1700, 5400])
        self.assertIsNone(fan2)

    def test_attributes_absent(self):
        self.assertEqual(self.read_with_files({}), (None, None))

    def test_invalid_ladder_is_rejected(self):
        for content in ("0 0", "2000 1000", "-1 1000", "", " ".join(map(str, range(1, 12)))):
            with self.subTest(content=content):
                self.assertEqual(self.read_with_files({legion.FAN_LEVEL_RPM_TABLE_FILES[0]: content}), (None, None))

    def test_zero_and_repeated_rpm_levels_preserve_their_indices(self):
        ladder = [0, 1300, 1700, 2100, 2500, 3100, 3400, 3800, 4200, 4600]
        fan1, _ = self.read_with_files({legion.FAN_LEVEL_RPM_TABLE_FILES[0]: " ".join(map(str, ladder))})
        self.assertEqual(fan1, ladder)
        self.assertEqual(legion.fan_level_to_rpm(1, fan1), 0)
        self.assertEqual(legion.fan_level_to_rpm(10, fan1), 4600)
        self.assertEqual(legion.fan_rpm_to_level(1300, 1, fan1), 2)
        self.assertEqual(legion.fan_rpm_to_level(0, 10, fan1), legion.LEVEL_POINT_MIN[-1])
        repeated, _ = self.read_with_files({legion.FAN_LEVEL_RPM_TABLE_FILES[0]: "0 1000 1000 2000"})
        self.assertEqual(repeated, [0, 1000, 1000, 2000])

    def test_malformed_content_is_ignored(self):
        fan1, fan2 = self.read_with_files(
            {
                "fan1_level_rpm_table": "17oo 1900\n",
                "fan2_level_rpm_table": "1700 5400\n",
            }
        )
        self.assertIsNone(fan1)
        self.assertEqual(fan2, [1700, 5400])


class RpmToLevelTest(unittest.TestCase):
    def test_exact_levels(self):
        for level, rpm in enumerate(FAN1_LADDER, start=1):
            self.assertEqual(legion.fan_rpm_to_level(rpm, 1, FAN1_LADDER), level)

    def test_tie_resolves_to_lower_level(self):
        # 1800 rpm is exactly between level 1 and 2
        self.assertEqual(legion.fan_rpm_to_level(1800, 1, FAN1_LADDER), 1)

    def test_between_levels_rounds_to_nearest(self):
        self.assertEqual(legion.fan_rpm_to_level(2000, 1, FAN1_LADDER), 2)

    def test_zero_resolves_to_point_minimum(self):
        self.assertEqual(legion.fan_rpm_to_level(0, 1, FAN1_LADDER), 1)
        self.assertEqual(legion.fan_rpm_to_level(0, 10, FAN1_LADDER), 5)

    def test_nonpositive_rpm_respects_each_point_minimum(self):
        for point_id, minimum in enumerate(legion.LEVEL_POINT_MIN, start=1):
            for rpm in (0, -1, -1000):
                with self.subTest(point_id=point_id, rpm=rpm):
                    self.assertEqual(legion.fan_rpm_to_level(rpm, point_id, FAN1_LADDER), minimum)

    def test_point_minimum_clamps_low_levels(self):
        # level 1 would be the nearest for 1800 rpm, but point 9 needs >= 3
        self.assertEqual(legion.fan_rpm_to_level(1800, 9, FAN1_LADDER), 3)
        self.assertEqual(legion.fan_rpm_to_level(1800, 10, FAN1_LADDER), 5)

    def test_short_ladder_cannot_reach_point_minimum(self):
        with self.assertRaises(ValueError):
            legion.fan_rpm_to_level(0, 10, FAN1_LADDER[:2])

    def test_nonfinite_speed_is_rejected(self):
        for rpm in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(rpm=rpm), self.assertRaises(ValueError):
                legion.fan_rpm_to_level(rpm, 1, FAN1_LADDER)

    def test_above_maximum_clamps_to_max(self):
        self.assertEqual(legion.fan_rpm_to_level(9000, 1, FAN1_LADDER), 10)
        self.assertEqual(legion.fan_rpm_to_level(1e308, 1, FAN1_LADDER), legion.MAX_FAN_LEVEL)


class LevelConversionTest(unittest.TestCase):
    def test_pwm_level_roundtrip(self):
        for level in range(0, legion.MAX_FAN_LEVEL + 1):
            pwm = legion.fan_level_to_pwm(level)
            self.assertEqual(legion.fan_pwm_to_level(pwm), level)

    def test_pwm_to_level_midpoints(self):
        # kernel: DIV_ROUND_CLOSEST(pwm * 10, 255)
        self.assertEqual(legion.fan_pwm_to_level(26), 1)
        self.assertEqual(legion.fan_pwm_to_level(12), 0)
        self.assertEqual(legion.fan_pwm_to_level(13), 1)

    def test_level_to_rpm(self):
        self.assertEqual(legion.fan_level_to_rpm(1, FAN1_LADDER), 1700)
        self.assertEqual(legion.fan_level_to_rpm(10, FAN1_LADDER), 5400)
        self.assertEqual(legion.fan_level_to_rpm(0, FAN1_LADDER), 0)
        with self.assertRaises(ValueError):
            legion.fan_level_to_rpm(11, FAN1_LADDER)
        with self.assertRaises(ValueError):
            legion.fan_level_to_rpm(1, None)


class FanCurveIOLevelTest(unittest.TestCase):
    def make_io(self, files):
        # Keep the filesystem live for the whole test: calibration is refreshed
        # for each operation instead of being cached at construction.
        for patcher in (
            mock.patch.object(legion, "LEGION_SYS_BASEPATH", "/fake/sys/path"),
            fake_sysfs(files),
            mock.patch.object(legion.FanCurveIO, "_find_hwmon_dir", return_value="/fake/hwmon/"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        return legion.FanCurveIO(expect_hwmon=False)

    def test_uses_fan_levels_when_attributes_exist(self):
        io = self.make_io(
            {
                "fan1_level_rpm_table": "1700 1900 2100 2300 2500 2900 3400 3700 4400 5400\n",
                "fan2_level_rpm_table": "1700 1900 2100 2200 2700 2900 3500 3700 4600 5400\n",
            }
        )
        self.assertTrue(io.uses_fan_levels())
        self.assertEqual(io.level_tables[0], FAN1_LADDER)
        self.assertEqual(io.level_tables[1], FAN2_LADDER)

    def test_missing_fan2_ladder_does_not_invent_rpm(self):
        io = self.make_io({"fan1_level_rpm_table": "1700 5400\n"})
        self.assertTrue(io.uses_fan_levels())
        self.assertIsNone(io.level_tables[1])
        with mock.patch.object(io, "get_fan_1_speed_pwm", return_value=26), self.assertRaises(ValueError):
            io.get_fan_2_speed_rpm(1)

    def test_no_attributes_disables_level_mode(self):
        io = self.make_io({})
        self.assertFalse(io.uses_fan_levels())
        self.assertIsNone(io.level_tables)

    def test_calibration_refreshes_after_power_mode_change(self):
        name = legion.FAN_LEVEL_RPM_TABLE_FILES[0]
        files = {name: " ".join(map(str, FAN1_LADDER))}
        io = self.make_io(files)
        with mock.patch.object(io, "get_fan_1_speed_pwm", return_value=26):
            self.assertEqual(io.get_fan_1_speed_rpm(1), FAN1_LADDER[0])
            files[name] = " ".join(str(rpm + 1000) for rpm in FAN1_LADDER)
            self.assertEqual(io.get_fan_1_speed_rpm(1), FAN1_LADDER[0] + 1000)
        with mock.patch.object(io, "_write_file") as write:
            io.set_fan_1_speed_rpm(1, FAN1_LADDER[0] + 1000)
            write.assert_called_once_with(mock.ANY, legion.fan_level_to_pwm(1))

    def test_known_level_curve_never_falls_back_to_linear_pwm(self):
        io = self.make_io({legion.FANCURVE_SPEED_UNIT_FILE: "level\n"})
        with mock.patch.object(io, "_write_file") as write, self.assertRaises(ValueError):
            io.set_fan_1_speed_rpm(1, 3000)
        write.assert_not_called()

    def test_legacy_unreadable_ladder_never_falls_back_to_linear_pwm(self):
        io = self.make_io({})
        with mock.patch("os.path.exists", return_value=True), mock.patch.object(io, "_write_file") as write:
            with self.assertRaises(ValueError):
                io.set_fan_1_speed_rpm(1, 3000)
            write.assert_not_called()

    def test_nonlevel_unit_does_not_consume_firmware_ladder(self):
        io = self.make_io(
            {
                legion.FANCURVE_SPEED_UNIT_FILE: "percent\n",
                legion.FAN_LEVEL_RPM_TABLE_FILES[0]: " ".join(map(str, FAN1_LADDER)),
            }
        )
        self.assertIsNone(io.level_tables)

    def test_percentage_rpm_roundtrip_does_not_lose_a_percentage_point(self):
        io = self.make_io({legion.FANCURVE_SPEED_UNIT_FILE: "percent\n"})
        for maximum in (10000, 5400, 5555):
            with mock.patch.object(io, "get_fan_1_max_rpm", return_value=maximum):
                for percent in range(101):
                    with self.subTest(maximum=maximum, percent=percent), mock.patch.object(io, "_write_file") as write:
                        rpm = percent * maximum / 100
                        io.set_fan_1_speed_rpm(1, rpm)
                        pwm = write.call_args[0][1]
                        # Both kernel percentage setters must select exactly this step.
                        self.assertEqual(pwm * 100 // 255, percent)
                        self.assertEqual((pwm * 100 + 127) // 255, percent)
                        with mock.patch.object(io, "get_fan_1_speed_pwm", return_value=percent * 255 // 100):
                            self.assertAlmostEqual(io.get_fan_1_speed_rpm(1), rpm)

    def test_native_conversion_clamps_before_arithmetic_overflows(self):
        io = self.make_io({legion.FANCURVE_SPEED_UNIT_FILE: "rpm\n"})
        with mock.patch.object(io, "get_fan_1_max_rpm", return_value=10000), mock.patch.object(
            io, "_write_file"
        ) as write:
            io.set_fan_1_speed_rpm(1, 1e308)
            write.assert_called_once_with(mock.ANY, 255)
        with mock.patch.object(io, "get_fan_1_max_rpm", return_value=0), mock.patch.object(io, "_write_file") as write:
            with self.assertRaises(ValueError):
                io.set_fan_1_speed_rpm(1, 1000)
            write.assert_not_called()

    def test_no_writable_points_is_an_error_not_silent_success(self):
        io = self.make_io({})
        curve = legion.FanCurve("unsupported", [legion.FanCurveEntry(2000, 2000, 0, 0, 0, 0, 0, 0, 0, 0)])
        with mock.patch.object(io, "get_point_count", return_value=0), mock.patch.object(io, "_write_file") as write:
            with self.assertRaises(RuntimeError):
                io.write_fan_curve(curve)
            write.assert_not_called()

    def test_whole_curve_validates_speeds_before_writing(self):
        io = self.make_io({legion.FAN_LEVEL_RPM_TABLE_FILES[0]: " ".join(map(str, FAN1_LADDER))})
        curve = legion.FanCurve(
            "invalid", [legion.FanCurveEntry(rpm, rpm, 0, 0, 0, 0, 0, 0, 0, 0) for rpm in (2000, float("nan"))]
        )
        with mock.patch.object(io, "get_point_count", return_value=2), mock.patch.object(
            io, "set_minifancuve"
        ) as mini, mock.patch.object(io, "_write_file") as write:
            with self.assertRaises(ValueError):
                io.write_fan_curve(curve)
            write.assert_not_called()
            mini.assert_not_called()

    def test_set_fan_speed_rpm_writes_level_pwm(self):
        io = self.make_io(
            {
                "fan1_level_rpm_table": "1700 1900 2100 2300 2500 2900 3400 3700 4400 5400\n",
                "fan2_level_rpm_table": "1700 1900 2100 2200 2700 2900 3500 3700 4600 5400\n",
            }
        )
        with mock.patch.object(io, "_write_file") as write_file:
            io.set_fan_1_speed_rpm(1, 4400)
            write_file.assert_called_once_with(mock.ANY, 230)  # level 9
        with mock.patch.object(io, "_write_file") as write_file:
            io.set_fan_2_speed_rpm(10, 0)
            write_file.assert_called_once_with(mock.ANY, 128)  # level 5 (point minimum)

    def test_get_fan_speed_rpm_reports_nominal_rpm(self):
        io = self.make_io(
            {
                "fan1_level_rpm_table": "1700 1900 2100 2300 2500 2900 3400 3700 4400 5400\n",
                "fan2_level_rpm_table": "1700 1900 2100 2200 2700 2900 3500 3700 4600 5400\n",
            }
        )
        with mock.patch.object(io, "get_fan_1_speed_pwm", return_value=230):
            self.assertEqual(io.get_fan_1_speed_rpm(1), 4400)
            # fan 2 has no own pwm attribute on this firmware; one level
            # drives both fans, so fan 1's pwm selects fan 2's level
            self.assertEqual(io.get_fan_2_speed_rpm(1), 4600)


class MiniFancurveCommandTest(unittest.TestCase):
    def test_curve_support_does_not_imply_minifancurve_support(self):
        model = mock.Mock()
        model.fancurve_io.exists.return_value = True
        model.fancurve_io.has_minifancurve.return_value = False
        parser = argparse.ArgumentParser()
        command = MiniFancurveFeatureCommand(parser.add_subparsers(), model, [])
        with mock.patch("builtins.print"):
            self.assertNotEqual(command.command_enable_cli(), 0)
        model.fancurve_io.set_minifancuve.assert_not_called()
        model.fancurve_io.has_minifancurve.return_value = True
        self.assertEqual(command.command_enable_cli(), 0)
        model.fancurve_io.set_minifancuve.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
