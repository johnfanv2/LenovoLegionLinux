"""PR-3 verification: single-fan fan-curve handling + fan2 rpm-scale typo fix.

LOQ 83SC has ONE fan, so the toolkit must never touch fan2 sysfs nodes and must
mirror fan1 into the in-memory fan2 slot on read. Run with:
    python -m unittest test_fancurve -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "python", "legion_linux"))
from legion_linux.legion import FanCurveIO, FanCurve, FanCurveEntry

FAKE_HWMON = "/fake/hwmon/"


def _make_fio(fan2_present):
    fio = FanCurveIO(expect_hwmon=False)
    fio.hwmon_path = FAKE_HWMON
    fs = {}

    def read_file(fp):
        if fp.endswith("fan1_max") or fp.endswith("fan2_max"):
            return 255
        if "pwm1_auto_point" in fp or "pwm2_auto_point" in fp:
            return 128
        return 0

    def write_file(fp, value):
        fs[fp] = str(value)

    def read_file_or(fp, default):
        return fs.get(fp, default)

    def write_file_or(fp, value):
        fs[fp] = str(value)

    fio._read_file = read_file
    fio._write_file = write_file
    fio._read_file_or = read_file_or
    fio._write_file_or = write_file_or

    def exists(fp):
        if "pwm2_auto_point" in fp:
            return fan2_present
        if "pwm1_auto_point" in fp:
            return True
        if fp.endswith("fan1_max") or fp.endswith("fan2_max"):
            return True
        return False

    return fio, fs, exists


def _entry(i):
    return FanCurveEntry(
        fan1_speed=float(1000 + i * 100),
        fan2_speed=float(2000 + i * 100),
        cpu_lower_temp=0, cpu_upper_temp=0,
        gpu_lower_temp=0, gpu_upper_temp=0,
        ic_lower_temp=0, ic_upper_temp=0,
        acceleration=0, deceleration=0)


class TestFanCurveSingleFan(unittest.TestCase):
    def test_single_fan_write_skips_fan2(self):
        fio, fs, exists = _make_fio(fan2_present=False)
        with mock.patch.object(os.path, "exists", exists):
            curve = FanCurve(
                name="t", entries=[_entry(i) for i in range(10)],
                enable_minifancurve=False)
            fio.write_fan_curve(curve)
            pwm2 = [k for k in fs if "pwm2_auto_point" in k]
            pwm1_speed = [k for k in fs
                          if "pwm1_auto_point" in k and k.endswith("_pwm")]
            self.assertEqual(pwm2, [],
                             "single-fan must NOT write any fan2 sysfs node")
            self.assertEqual(len(pwm1_speed), 10,
                             "all 10 fan1 speed points must be written")

    def test_single_fan_read_mirrors_fan1(self):
        fio, fs, exists = _make_fio(fan2_present=False)
        with mock.patch.object(os.path, "exists", exists):
            curve = fio.read_fan_curve()
            self.assertGreater(len(curve.entries), 0)
            for e in curve.entries:
                self.assertEqual(
                    e.fan2_speed, e.fan1_speed,
                    "single-fan read must mirror fan1 into fan2")

    def test_dual_fan_rpm_scale_consistent(self):
        # regression test for the (100*225) -> (100*255) typo:
        # fan1 and fan2 rpm must use the same scale, so identical pwm/max
        # must yield identical rpm.
        fio, fs, exists = _make_fio(fan2_present=True)
        with mock.patch.object(os.path, "exists", exists):
            self.assertEqual(
                fio.get_fan_1_speed_rpm(1), fio.get_fan_2_speed_rpm(1),
                "fan1 and fan2 rpm scale must match (225->255 fix)")


if __name__ == "__main__":
    unittest.main()
