# pylint: disable=missing-docstring,too-many-public-methods,protected-access
"""Unit tests for the fan level (FAN_SPEED_UNIT_LEVEL) RPM conversion helpers.

The per-fan RPM ladders are read from the kernel module's platform device
sysfs attributes (which derive them from the firmware's LENOVO_FAN_TABLE_DATA
WMI block); these tests mock that sysfs access and cover the conversion and
fallback behaviour of legion.py.
"""

import unittest
from unittest import mock

from legion_linux import legion

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
        raise OSError(f"No such file: {path}")

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

    def test_above_maximum_clamps_to_max(self):
        self.assertEqual(legion.fan_rpm_to_level(9000, 1, FAN1_LADDER), 10)


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
        self.assertEqual(legion.fan_level_to_rpm(11, FAN1_LADDER), 0)


class FanCurveIOLevelTest(unittest.TestCase):
    def make_io(self, files):
        with mock.patch.object(legion, "LEGION_SYS_BASEPATH", "/fake/sys/path"):
            with fake_sysfs(files):
                with mock.patch.object(legion.FanCurveIO, "_find_hwmon_dir", return_value="/fake/hwmon/"):
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

    def test_fan2_ladder_falls_back_to_fan1(self):
        io = self.make_io({"fan1_level_rpm_table": "1700 5400\n"})
        self.assertTrue(io.uses_fan_levels())
        self.assertEqual(io.level_tables[1], [1700, 5400])

    def test_no_attributes_disables_level_mode(self):
        io = self.make_io({})
        self.assertFalse(io.uses_fan_levels())
        self.assertIsNone(io.level_tables)

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


if __name__ == "__main__":
    unittest.main()
