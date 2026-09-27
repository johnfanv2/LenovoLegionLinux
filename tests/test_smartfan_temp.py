"""Drive smartfan's temperature handling against a fake sysfs.

``smartfan.sh`` cannot be sourced: it runs a top-level ``modprobe acpi_call``
and writes to ``/proc/acpi/call``. So the functions under test are extracted
verbatim and run in a subshell with a stub ``log()`` and a temporary hwmon
tree. No acpi_call, no module load, no hardware, no EC writes.

The behaviour being pinned down: when no temperature can be read, the daemon
used to fall back to ``last_temp``, which is 0 until the first successful
read. A failure at startup therefore resolved to 0 degrees, the coldest point
of the curve, and ``set_fan_speed`` clamped that to 20% - the fans at their
minimum while the daemon had no idea it was blind.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

SMARTFAN = Path(__file__).resolve().parents[1] / "extra/smartfan/smartfan.sh"
FUNCTIONS = ("find_hwmon", "get_profile", "get_max_temp", "profile_max_temp", "resolve_temp")


def extract(source, name):
    """Return one top-level bash function, brace-matched."""
    start = source.index(f"\n{name}() {{")
    depth = 0
    for index in range(source.index("{", start), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1 : index + 1]
    raise AssertionError(f"unbalanced braces in {name}()")


class SmartFanTempTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = SMARTFAN.read_text()
        cls.harness = "log() { :; }\n" + "\n".join(extract(source, name) for name in FUNCTIONS)

    def run_bash(self, script, env=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "harness.sh")
            path.write_text("set -u\n" + self.harness + "\n" + script)
            result = subprocess.run(
                ["bash", str(path)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            return result.stdout.strip()

    def hwmon(self, directory, name, cpu_temp=None, gpu_temp=None):
        """Build a fake hwmon dir and return its path."""
        path = Path(directory, name)
        path.mkdir()
        (path / "name").write_text(name)
        if cpu_temp is not None:
            (path / "temp1_input").write_text(str(cpu_temp))
        if gpu_temp is not None:
            (path / "temp2_input").write_text(str(gpu_temp))
        return path

    def test_reads_the_hottest_of_cpu_and_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            cpu = self.hwmon(directory, "hwmon2", cpu_temp=45000)
            gpu = self.hwmon(directory, "hwmon3", cpu_temp=71000)
            script = f'CPU_HWMON="{cpu}"\nGPU_HWMON="{gpu}"\nget_max_temp\n'
            self.assertEqual(self.run_bash(script), "71")

    def test_missing_sensors_report_failure_instead_of_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            cpu = self.hwmon(directory, "hwmon2")
            script = f'CPU_HWMON="{cpu}"\nGPU_HWMON="{cpu}"\nget_max_temp\n'
            # Empty, not "0": a 0 would be indistinguishable from a real reading.
            self.assertEqual(self.run_bash(script), "")

    def test_no_hwmon_path_at_all_reports_failure(self):
        script = 'CPU_HWMON=""\nGPU_HWMON=""\nget_max_temp\n'
        self.assertEqual(self.run_bash(script), "")

    def test_cold_start_with_no_reading_uses_the_profile_maximum(self):
        script = 'get_profile quiet\necho "$(resolve_temp "" 0)"\n'
        # quiet is "40 ... 95", so 95 resolves to the top of the curve (70%),
        # not the bottom (20%).
        self.assertEqual(self.run_bash(script), "95")

    def test_later_failure_keeps_the_last_known_reading(self):
        script = 'get_profile quiet\necho "$(resolve_temp "" 62)"\n'
        self.assertEqual(self.run_bash(script), "62")

    def test_a_real_reading_always_wins(self):
        script = 'get_profile quiet\necho "$(resolve_temp 58 62)"\n'
        self.assertEqual(self.run_bash(script), "58")

    def test_profile_maximum_tracks_each_profile(self):
        for mode, expected in (("quiet", "95"), ("balanced", "95"), ("performance", "95"), ("extreme", "95")):
            with self.subTest(mode=mode):
                script = f'get_profile {mode}\nprofile_max_temp\n'
                self.assertEqual(self.run_bash(script), expected)

    def test_cold_start_failure_does_not_choose_the_coldest_point(self):
        """The regression this fixes, stated as a property of the curve data."""
        script = """
get_profile quiet
worst=$(resolve_temp "" 0)
best=$(echo "$TEMP_POINTS" | awk '{print $1}')
[ "$worst" -gt "$best" ] || exit 1
echo ok
"""
        self.assertEqual(self.run_bash(script), "ok")

    def test_find_hwmon_does_not_invent_a_sensor_path(self):
        """The old fallback pointed at hwmon9 whatever the machine looked like."""
        with tempfile.TemporaryDirectory() as directory:
            unrelated = self.hwmon(directory, "hwmon9", cpu_temp=99000)
            script = (
                f'HWMON_ROOT="{directory}"\nCPU_HWMON=""\nGPU_HWMON=""\n'
                'find_hwmon\necho "[$CPU_HWMON][$GPU_HWMON]"\n'
            )
            self.assertEqual(self.run_bash(script), "[][]")
            self.assertTrue(unrelated.exists(), "the fake hwmon9 must not be adopted")

    def test_find_hwmon_still_finds_real_sensors(self):
        with tempfile.TemporaryDirectory() as directory:
            cpu = self.hwmon(directory, "hwmon2")
            gpu = self.hwmon(directory, "hwmon3")
            (cpu / "name").write_text("coretemp")
            (gpu / "name").write_text("amdgpu")
            script = (
                f'HWMON_ROOT="{directory}"\nCPU_HWMON=""\nGPU_HWMON=""\n'
                'find_hwmon\necho "$CPU_HWMON|$GPU_HWMON"\n'
            )
            self.assertEqual(self.run_bash(script), f"{cpu}|{gpu}")


if __name__ == "__main__":
    unittest.main()
