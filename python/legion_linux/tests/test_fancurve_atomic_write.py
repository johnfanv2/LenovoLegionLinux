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
            # Do not depend on the host's module/BIOS (e.g. an LPCN test machine).
            mock.patch.object(io, "percent_unit_on_level_table", return_value=False),
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


FULL_POINT_FILES = (
    "pwm1_auto_point{}_pwm",
    "pwm2_auto_point{}_pwm",
    "pwm1_auto_point{}_temp",
    "pwm1_auto_point{}_temp_hyst",
    "pwm2_auto_point{}_temp",
    "pwm2_auto_point{}_temp_hyst",
    "pwm3_auto_point{}_temp",
    "pwm3_auto_point{}_temp_hyst",
    "pwm1_auto_point{}_accel",
    "pwm1_auto_point{}_decel",
)

MAX_TEMP_ATTRS = (
    "pwm1_auto_point{}_temp",
    "pwm2_auto_point{}_temp",
    "pwm3_auto_point{}_temp",
)


class FancurveResizeTest(unittest.TestCase):
    """Regression tests for EC auto_points_size resizing vs fixed-size curves (#654)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hwmon = pathlib.Path(self.tmp.name)
        (self.hwmon / "fan1_max").write_text("10000\n", encoding="UTF-8")
        (self.hwmon / "fan2_max").write_text("10000\n", encoding="UTF-8")
        (self.hwmon / "minifancurve").write_text("1", encoding="UTF-8")
        for point in range(1, 11):
            for pattern in FULL_POINT_FILES:
                (self.hwmon / pattern.format(point)).write_text("0", encoding="UTF-8")

    def make_io(self):
        io = legion.FanCurveIO(expect_hwmon=False)
        io.hwmon_path = str(self.hwmon) + "/"
        io.use_legion_cli_to_write = False
        return io

    def write_point(self, point, pwm, *, upper_temp=60, accel=3, decel=3):
        values = {
            "pwm1_auto_point{}_pwm": pwm,
            "pwm2_auto_point{}_pwm": pwm,
            "pwm1_auto_point{}_temp": upper_temp,
            "pwm1_auto_point{}_temp_hyst": 40,
            "pwm2_auto_point{}_temp": upper_temp,
            "pwm2_auto_point{}_temp_hyst": 40,
            "pwm3_auto_point{}_temp": upper_temp,
            "pwm3_auto_point{}_temp_hyst": 35,
            "pwm1_auto_point{}_accel": accel,
            "pwm1_auto_point{}_decel": decel,
        }
        for pattern, val in values.items():
            (self.hwmon / pattern.format(point)).write_text(str(val), encoding="UTF-8")

    def make_kernel_ec_writer(self, fail_on=None):
        """Mirror legion-laptop.c's autopoint_store + ec_write_fancurve_legion behaviour."""

        def kernel_write(file_path, value):
            path = pathlib.Path(file_path)
            if fail_on is not None and path.name == fail_on:
                raise OSError("simulated sysfs write failure")
            if path.name == "auto_points_size":
                old_size = int(path.read_text(encoding="UTF-8"))
                new_size = int(value)
                if not 1 <= new_size <= 10:
                    raise OSError("EINVAL")
                if new_size < old_size:
                    for pattern in MAX_TEMP_ATTRS:
                        (self.hwmon / pattern.format(new_size)).write_text("127", encoding="UTF-8")
                    for cleared in range(new_size + 1, 11):
                        for pattern in FULL_POINT_FILES:
                            (self.hwmon / pattern.format(cleared)).write_text("0", encoding="UTF-8")
                elif new_size > old_size:
                    src = max(1, old_size)
                    for grown in range(old_size + 1, new_size + 1):
                        for pattern in FULL_POINT_FILES:
                            copied = (self.hwmon / pattern.format(src)).read_text(encoding="UTF-8")
                            (self.hwmon / pattern.format(grown)).write_text(copied, encoding="UTF-8")
                path.write_text(str(new_size), encoding="UTF-8")
                return
            for prefix in ("pwm1_auto_point", "pwm2_auto_point"):
                if path.name.startswith(prefix) and path.name.endswith("_pwm"):
                    point_id = int(path.name.removeprefix(prefix).removesuffix("_pwm"))
                    active_size = int((self.hwmon / "auto_points_size").read_text(encoding="UTF-8"))
                    if point_id > active_size:
                        raise OSError(f"point {point_id} exceeds active size {active_size}")
            path.write_text(str(value), encoding="UTF-8")

        return kernel_write

    def snapshot(self):
        return {path.name: path.read_text(encoding="UTF-8") for path in sorted(self.hwmon.iterdir())}

    def test_writable_auto_points_size_reads_active_4_and_resizes_to_10_on_write(self):
        size_file = self.hwmon / "auto_points_size"
        size_file.write_text("4", encoding="UTF-8")
        size_file.chmod(0o644)
        # Active 4-point cool minifancurve on EFCN59WW (including firmware decel=7).
        for point in range(1, 5):
            self.write_point(point, point * 25, upper_temp=110 if point == 4 else 60, accel=5, decel=7)

        io = self.make_io()
        with mock.patch.object(type(io), "speed_unit", "rpm"), mock.patch.object(
            io, "percent_unit_on_level_table", return_value=False
        ):
            self.assertTrue(io.has_writable_auto_points_size())
            self.assertEqual(io.get_active_point_count(), 4)
            self.assertEqual(io.get_point_count(), 10)
            active_curve = io.read_fan_curve()
            self.assertEqual(len(active_curve.entries), 4)
            self.assertEqual(active_curve.entries[0].deceleration, 7)

            ten_point_curve = legion.FanCurve(
                "performance-ac",
                [
                    entry(point, fan1_speed=point * 400, fan2_speed=point * 400, cpu_upper_temp=45 + point * 5)
                    for point in range(1, 11)
                ],
                enable_minifancurve=False,
            )
            with mock.patch.object(io, "_write_file", side_effect=self.make_kernel_ec_writer()):
                io.write_fan_curve(ten_point_curve)

            self.assertEqual(size_file.read_text(encoding="UTF-8"), "10")
            self.assertEqual((self.hwmon / "minifancurve").read_text(encoding="UTF-8"), "0")
            updated_curve = io.read_fan_curve()
            self.assertEqual(len(updated_curve.entries), 10)
            self.assertEqual(updated_curve.entries[9].fan1_speed, 4000)

    def test_readonly_auto_points_size_trims_to_fixed_hardware_limit(self):
        size_file = self.hwmon / "auto_points_size"
        size_file.write_text("8", encoding="UTF-8")
        size_file.chmod(0o444)
        self.addCleanup(size_file.chmod, 0o644)

        io = self.make_io()
        ten_point_curve = legion.FanCurve(
            "custom",
            [entry(point, fan1_speed=point * 300, fan2_speed=point * 300) for point in range(1, 11)],
            enable_minifancurve=False,
        )
        with mock.patch.object(type(io), "speed_unit", "rpm"), mock.patch.object(
            io, "percent_unit_on_level_table", return_value=False
        ):
            self.assertFalse(io.has_writable_auto_points_size())
            self.assertEqual(io.get_active_point_count(), 8)
            self.assertEqual(io.get_point_count(), 8)
            io.write_fan_curve(ten_point_curve)

        self.assertEqual(size_file.read_text(encoding="UTF-8"), "8")
        self.assertNotEqual((self.hwmon / "pwm1_auto_point8_pwm").read_text(encoding="UTF-8"), "0")
        self.assertEqual((self.hwmon / "pwm1_auto_point9_pwm").read_text(encoding="UTF-8"), "0")
        self.assertEqual((self.hwmon / "pwm1_auto_point10_pwm").read_text(encoding="UTF-8"), "0")

    def test_failed_shrink_and_grow_resize_restore_previous_curve_atomically(self):
        size_file = self.hwmon / "auto_points_size"
        size_file.write_text("10", encoding="UTF-8")
        size_file.chmod(0o644)
        io = self.make_io()

        with self.subTest("shrink_10_to_6_rolls_back"):
            size_file.write_text("10", encoding="UTF-8")
            for point in range(1, 11):
                self.write_point(point, point * 20, upper_temp=50 + point * 5, accel=2, decel=3)
            before = self.snapshot()
            six_point_curve = legion.FanCurve(
                "six",
                [entry(point, fan1_speed=2500, fan2_speed=2500) for point in range(1, 7)],
                enable_minifancurve=True,
            )
            with mock.patch.object(type(io), "speed_unit", "rpm"), mock.patch.object(
                io, "percent_unit_on_level_table", return_value=False
            ), mock.patch.object(
                io, "_write_file", side_effect=self.make_kernel_ec_writer(fail_on="pwm1_auto_point2_temp")
            ):
                with self.assertRaises(OSError):
                    io.write_fan_curve(six_point_curve)
            self.assertEqual(self.snapshot(), before)

        with self.subTest("grow_4_to_10_rolls_back"):
            size_file.write_text("4", encoding="UTF-8")
            for point in range(1, 5):
                self.write_point(point, point * 25, upper_temp=110 if point == 4 else 60, accel=5, decel=5)
            for point in range(5, 11):
                for pattern in FULL_POINT_FILES:
                    (self.hwmon / pattern.format(point)).write_text("0", encoding="UTF-8")
            before = self.snapshot()
            ten_point_curve = legion.FanCurve(
                "ten",
                [entry(point, fan1_speed=3000, fan2_speed=3000) for point in range(1, 11)],
                enable_minifancurve=True,
            )
            with mock.patch.object(type(io), "speed_unit", "rpm"), mock.patch.object(
                io, "percent_unit_on_level_table", return_value=False
            ), mock.patch.object(
                io, "_write_file", side_effect=self.make_kernel_ec_writer(fail_on="pwm1_auto_point6_pwm")
            ):
                with self.assertRaises(OSError):
                    io.write_fan_curve(ten_point_curve)
            self.assertEqual(self.snapshot(), before)

    def test_invalid_curve_is_rejected_before_minifancurve_or_size_is_written(self):
        size_file = self.hwmon / "auto_points_size"
        size_file.write_text("4", encoding="UTF-8")
        size_file.chmod(0o644)
        before = self.snapshot()
        io = self.make_io()
        bad_curve = legion.FanCurve(
            "bad",
            [entry(1), entry(2, deceleration=7)],
            enable_minifancurve=False,
        )
        with mock.patch.object(type(io), "speed_unit", "rpm"), mock.patch.object(
            io, "percent_unit_on_level_table", return_value=False
        ):
            with self.assertRaises(ValueError):
                io.write_fan_curve(bad_curve)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
