# pylint: disable=missing-docstring,protected-access
"""Tests that writing a fan curve is all-or-nothing.

Fan curve points are independent sysfs attributes, so a failure part way
through used to leave the EC running a mixture of the old and the new curve.
These tests use a real temporary directory as a fake hwmon tree so writes are
observed rather than mocked; no hardware and no loaded module are involved.
"""

import contextlib
import pathlib
import tempfile
import unittest
from unittest import mock

from legion_linux import legion

# The full set of attributes one point of a Legion curve touches.
POINT_FILES = (
    "pwm1_auto_point{}_pwm",
    "pwm2_auto_point{}_pwm",
    "pwm1_auto_point{}_temp",
    "pwm1_auto_point{}_temp_hyst",
    "pwm1_auto_point{}_accel",
    "pwm1_auto_point{}_decel",
)

ORIGINAL = "40"


def entry(point, **overrides):
    """A fan curve entry with every field the plan touches."""
    values = {
        "fan1_speed": 2000,
        "fan2_speed": 2000,
        "cpu_lower_temp": 30,
        "cpu_upper_temp": 40,
        "gpu_lower_temp": 30,
        "gpu_upper_temp": 40,
        "ic_lower_temp": 30,
        "ic_upper_temp": 40,
        "acceleration": 2,
        "deceleration": 2,
    }
    values.update(overrides)
    return legion.FanCurveEntry(**values)


class FancurveAtomicWriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hwmon = pathlib.Path(self.tmp.name)
        for point in range(1, 5):
            for pattern in POINT_FILES:
                (self.hwmon / pattern.format(point)).write_text(ORIGINAL, encoding="UTF-8")

    def fan_curve_io(self):
        io = legion.FanCurveIO(expect_hwmon=False)
        io.hwmon_path = str(self.hwmon) + "/"
        return io

    def plan(self, io, entries):
        speeds = [(entry_.fan1_speed, entry_.fan2_speed) for entry_ in entries]
        return io._fancurve_write_plan(entries, speeds, io.temperature_fields(), True, True)

    def read_all(self):
        return {path.name: path.read_text(encoding="UTF-8") for path in sorted(self.hwmon.iterdir()) if path.is_file()}

    def test_valid_curve_is_written_in_full(self):
        io = self.fan_curve_io()
        entries = [entry(1), entry(2, cpu_upper_temp=55)]
        io._write_fancurve_plan(self.plan(io, entries))
        self.assertEqual((self.hwmon / "pwm1_auto_point2_pwm").read_text(encoding="UTF-8"), "2000")
        self.assertEqual((self.hwmon / "pwm1_auto_point2_temp").read_text(encoding="UTF-8"), "55")
        # Untouched points keep their original value.
        self.assertEqual((self.hwmon / "pwm1_auto_point3_pwm").read_text(encoding="UTF-8"), ORIGINAL)

    def test_out_of_range_temperature_writes_nothing(self):
        io = self.fan_curve_io()
        before = self.read_all()
        # The driver rejects anything outside 0-127; point 2 is the bad one.
        entries = [entry(1), entry(2, cpu_upper_temp=200)]
        with self.assertRaises(ValueError):
            self.plan(io, entries)
        self.assertEqual(self.read_all(), before, "a rejected curve must not touch the hardware")

    def test_out_of_range_acceleration_writes_nothing(self):
        io = self.fan_curve_io()
        before = self.read_all()
        entries = [entry(1), entry(2, acceleration=9)]
        with self.assertRaises(ValueError):
            self.plan(io, entries)
        self.assertEqual(self.read_all(), before, "a rejected curve must not touch the hardware")

    def test_failure_midway_restores_previous_values(self):
        io = self.fan_curve_io()
        entries = [entry(1), entry(2)]
        plan = self.plan(io, entries)
        # Replace the third target with a directory so opening it for writing
        # fails after the first two have already been applied.
        target = pathlib.Path(plan[2][0])
        target.unlink()
        target.mkdir()
        with self.assertRaises(OSError):
            io._write_fancurve_plan(plan)
        self.assertEqual(
            (self.hwmon / "pwm1_auto_point1_pwm").read_text(encoding="UTF-8"),
            ORIGINAL,
            "point 1 must be rolled back after a later write fails",
        )
        self.assertEqual(
            (self.hwmon / "pwm1_auto_point2_pwm").read_text(encoding="UTF-8"),
            ORIGINAL,
            "point 2 must be rolled back after a later write fails",
        )

    def test_restore_failure_still_reports_the_original_error(self):
        io = self.fan_curve_io()
        entries = [entry(1)]
        plan = self.plan(io, entries)
        # Point 1's first file is fine, the second cannot be written, and the
        # restore of the first must not mask why.
        target = pathlib.Path(plan[1][0])
        target.unlink()
        target.mkdir()
        with self.assertRaises(OSError):
            io._write_fancurve_plan(plan)
        with mock.patch.object(legion.FanCurveIO, "_write_file", side_effect=OSError("restore failed")):
            with self.assertRaises(OSError):
                io._write_fancurve_plan(plan)

    def test_write_fan_curve_rolls_back_a_failure_part_way_through(self):
        """Behavioural check through the public API, not just the new helpers.

        The third attribute the driver writes for point 1 cannot be opened, so
        the first two have already been applied. write_fan_curve() must leave
        the tree exactly as it found it; before the fix it kept the new values.
        """
        io = self.fan_curve_io()
        curve = legion.FanCurve("test", [entry(1), entry(2)], False)
        before = self.read_all()
        blocked = self.hwmon / "pwm1_auto_point1_temp_hyst"
        blocked.unlink()
        blocked.mkdir()
        # The test itself destroyed this one, so it is not something the code
        # under test could have restored.
        before.pop(blocked.name, None)
        io.use_legion_cli_to_write = False
        patches = [
            mock.patch.object(io, "_require_hwmon"),
            mock.patch.object(io, "get_point_count", return_value=4),
            mock.patch.object(io, "has_fan_2_speed", return_value=True),
            mock.patch.object(io, "has_acceleration_curve", return_value=True),
            mock.patch.object(io, "temperature_fields", return_value=set(io.temperature_files)),
            mock.patch.object(io, "_rpm_to_pwm", side_effect=lambda _, value, __, ___: value),
            mock.patch.object(io, "set_minifancuve"),
            mock.patch.object(type(io), "level_tables", None),
        ]
        with contextlib.ExitStack() as stack:
            for entered in patches:
                stack.enter_context(entered)
            with self.assertRaises(OSError):
                io.write_fan_curve(curve)
        after = self.read_all()
        self.assertEqual(
            {name: value for name, value in after.items() if name in before},
            before,
            "a failed write must not leave a half-applied curve behind",
        )


if __name__ == "__main__":
    unittest.main()
