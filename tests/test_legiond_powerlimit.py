"""Drive legiond's cpu_powerlimit_sync against a fake sysfs tree.

Unlike tests/test_legiond_command_state.py, nothing in the code under test is
stubbed: the harness includes modules/powerlimit.c itself (so the static
helpers are reachable) and points it at a temporary directory through the
build-time overrides in powerlimit.h (legion_driver_path, rapl_mmio_path,
thermal_path). The "sysfs" files are plain files, so nothing touches hardware.

The harness reads one command per line from stdin and keeps running, so the
logging state carries over between calls exactly as it does in legiond:

  sync 0|1                   cpu_powerlimit_sync
  bat PL1 PL2                [cpu_powerlimit] bat_pl1 / bat_pl2
  double_p PL1 PL2 T0 T1     double_ac_p_pl / double_ac_p_temp, SEN3,SEN4, hyst 3
  write FILE TEXT            replace FILE (relative to the fake root); \\n = newline
  rm FILE                    remove FILE
  mv FROM TO                 rename (e.g. hide the whole MMIO zone)
  call STATE                 set_cpu_powerlimit(STATE), prints "=> result R"
  watts FILE PROFILE         read_default_watts(), prints "=> watts W bad TOKEN"
  find NAME                  find_legion_attr(), prints "=> found PATH" or "=> found -"
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

LEGIOND_DIR = Path(__file__).resolve().parents[1] / "extra/service/legiond"

HARNESS = r"""
#include "modules/powerlimit.c"

#include <stdlib.h>
#include <sys/stat.h>

static void put(const char *rel, const char *text)
{
	char path[PATH_MAX], buf[2048];
	size_t n = 0;

	for (const char *p = text; *p && n < sizeof(buf) - 1; p++) {
		if (p[0] == '\\' && p[1] == 'n') {
			buf[n++] = '\n';
			p++;
		} else {
			buf[n++] = *p;
		}
	}
	snprintf(path, sizeof(path), "%s/%s", FAKE, rel);
	FILE *fp = fopen(path, "w");
	fwrite(buf, 1, n, fp);
	fclose(fp);
}

int main(void)
{
	LEGIOND_CONFIG config = { 0 };
	char line[4096];

	config.powerlimit_double_hysteresis = 3;
	setvbuf(stdout, NULL, _IOLBF, 0);
	while (fgets(line, sizeof(line), stdin)) {
		char cmd[16] = "", a[PATH_MAX] = "", b[2048] = "";
		int n = sscanf(line, "%15s %4095s %2047[^\n]", cmd, a, b);

		if (n < 1)
			continue;
		if (strcmp(cmd, "sync") == 0) {
			config.cpu_powerlimit_sync = atoi(a);
		} else if (strcmp(cmd, "bat") == 0) {
			config.powerlimit_bat_pl1 = atoi(a);
			config.powerlimit_bat_pl2 = atoi(b);
		} else if (strcmp(cmd, "double_p") == 0) {
			strcpy(config.powerlimit_double_sensor[0], "SEN3");
			strcpy(config.powerlimit_double_sensor[1], "SEN4");
			config.powerlimit_double_pl[POWERLIMIT_P][0] = atoi(a);
			sscanf(b, "%u %u %u",
			       &config.powerlimit_double_pl[POWERLIMIT_P][1],
			       &config.powerlimit_double_temp[POWERLIMIT_P][0],
			       &config.powerlimit_double_temp[POWERLIMIT_P][1]);
		} else if (strcmp(cmd, "write") == 0) {
			put(a, b);
		} else if (strcmp(cmd, "rm") == 0) {
			char path[PATH_MAX];

			snprintf(path, sizeof(path), "%s/%s", FAKE, a);
			remove(path);
		} else if (strcmp(cmd, "mv") == 0) {
			char from[PATH_MAX], to[PATH_MAX];

			snprintf(from, sizeof(from), "%s/%s", FAKE, a);
			snprintf(to, sizeof(to), "%s/%s", FAKE, b);
			rename(from, to);
		} else if (strcmp(cmd, "call") == 0) {
			printf("=> result %d\n",
			       set_cpu_powerlimit((POWER_STATE)atoi(a), &config));
		} else if (strcmp(cmd, "watts") == 0) {
			char path[PATH_MAX], bad[64];

			snprintf(path, sizeof(path), "%s/%s", FAKE, a);
			unsigned int w = read_default_watts(path, b, bad, sizeof(bad));
			printf("=> watts %u bad %s\n", w, bad[0] ? bad : "-");
		} else if (strcmp(cmd, "find") == 0) {
			char path[PATH_MAX];

			if (find_legion_attr(a, path, sizeof(path)))
				printf("=> found %s\n", path + strlen(FAKE) + 1);
			else
				printf("=> found -\n");
		}
	}
	return 0;
}
"""

DEFAULTS_PL1 = "low-power:55 balanced:90 performance:145 max-power:160 custom:90\n"
DEFAULTS_PL2 = "low-power:65 balanced:125 performance:190 max-power:205 custom:125\n"

# POWER_STATE values (modules/powerstate.h)
AC_Q, BAT_Q, AC_B, BAT_B, AC_BP, BAT_BP, AC_P, BAT_P, AC_E = 0, 1, 2, 3, 4, 5, 6, 7, 8
UNKNOWN = -1


@unittest.skipIf(shutil.which("gcc") is None, "gcc is required to build the harness")
class PowerLimitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        build_dir = Path(cls.tmp.name)
        cls.root = build_dir / "root"
        source = build_dir / "harness.c"
        source.write_text(HARNESS, encoding="utf-8")
        cls.binary = build_dir / "harness"
        build = subprocess.run(
            [
                "gcc",
                "-std=gnu2x",
                "-Wall",
                "-Wextra",
                f"-I{LEGIOND_DIR}",
                f'-DFAKE="{cls.root}"',
                f'-Dlegion_driver_path="{cls.root}/drv"',
                f'-Drapl_mmio_path="{cls.root}/mmio"',
                f'-Dthermal_path="{cls.root}/thermal"',
                "-o",
                str(cls.binary),
                str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if build.returncode != 0:
            raise AssertionError(f"harness did not build:\n{build.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        shutil.rmtree(self.root, ignore_errors=True)
        (self.root / "mmio").mkdir(parents=True)
        for index, name in ((0, "long_term"), (1, "short_term")):
            (self.root / "mmio" / f"constraint_{index}_name").write_text(name + "\n")
            (self.root / "mmio" / f"constraint_{index}_power_limit_uw").write_text("30000000\n")
        for zone, kind in ((3, "SEN3"), (4, "SEN4")):
            zone_dir = self.root / "thermal" / f"thermal_zone{zone}"
            zone_dir.mkdir(parents=True)
            (zone_dir / "type").write_text(kind + "\n")
            (zone_dir / "temp").write_text("40000\n")
        self.device("legion")

    def device(self, name, pl1=DEFAULTS_PL1, pl2=DEFAULTS_PL2):
        """(Re)create the driver directory as kernel >= 7.0 ("legion") or < 7.0 does."""
        shutil.rmtree(self.root / "drv", ignore_errors=True)
        device_dir = self.root / "drv" / name
        device_dir.mkdir(parents=True)
        (self.root / "drv" / "bind").write_text("")
        if pl1 is not None:
            (device_dir / "cpu_longterm_powerlimit_defaults").write_text(pl1)
        if pl2 is not None:
            (device_dir / "cpu_shortterm_powerlimit_defaults").write_text(pl2)

    def run_script(self, *commands):
        run = subprocess.run(
            [str(self.binary)],
            input="\n".join(commands) + "\n",
            capture_output=True,
            text=True,
            check=True,
        )
        return run.stdout.splitlines()

    def limits(self):
        return tuple(
            int((self.root / "mmio" / f"constraint_{i}_power_limit_uw").read_text()) // 1_000_000 for i in (0, 1)
        )

    @staticmethod
    def logs(lines):
        """The log lines legiond would print (everything but the harness markers)."""
        return [line for line in lines if not line.startswith("=>")]

    # find_legion_attr(): the device directory differs by kernel version

    def test_finds_the_defaults_under_either_device_directory(self):
        for name in ("legion", "PNP0C09:00"):
            with self.subTest(device=name):
                self.device(name)
                out = self.run_script("find cpu_longterm_powerlimit_defaults", "sync 1", f"call {AC_P}")
                self.assertIn(f"=> found drv/{name}/cpu_longterm_powerlimit_defaults", out)
                self.assertEqual(self.limits(), (145, 190))

    def test_missing_defaults_name_the_missing_file_once(self):
        self.device("legion", pl2=None)
        out = self.run_script("sync 1", f"call {AC_P}", f"call {AC_P}")
        self.assertEqual(self.limits(), (30, 30))
        self.assertEqual(len(self.logs(out)), 1, out)
        self.assertIn("cpu_shortterm_powerlimit_defaults", self.logs(out)[0])

    # read_default_watts(): parsing and plausibility

    def test_read_default_watts(self):
        cases = {
            "multi-line": ("low-power:55\\nperformance:145\\n", 145, "-"),
            "tab-separated": ("low-power:55\tperformance:145\\n", 145, "-"),
            "prefix decoy first": ("performancex:1 performance:145\\n", 145, "-"),
            "upper bound": ("performance:500\\n", 500, "-"),
            "above bound": ("performance:501\\n", 0, "performance:501"),
            "zero": ("performance:0\\n", 0, "performance:0"),
            "unit suffix": ("performance:145W\\n", 0, "performance:145W"),
            "negative": ("performance:-5\\n", 0, "performance:-5"),
            "empty value": ("performance:\\n", 0, "performance:"),
            "absent": ("balanced:90\\n", 0, "-"),
            # a token cut at the 1023-byte read limit must not be misread
            "cut at the buffer end": ("x" * 1009 + " performance:145", 0, "-"),
            "complete at the buffer end": ("x" * 1006 + " performance:145", 145, "-"),
        }
        for name, (text, watts, bad) in cases.items():
            with self.subTest(case=name):
                out = self.run_script(f"write file {text}", "watts file performance")
                self.assertIn(f"=> watts {watts} bad {bad}", out)

    # logging: one line per change of outcome, on every path

    def test_steady_state_logs_once(self):
        out = self.run_script("sync 1", *[f"call {AC_P}"] * 5)
        self.assertEqual(self.logs(out), ["cpu_powerlimit set to PL1 145 W, PL2 190 W"])

    def test_sync_off_logs_once(self):
        # the shipped default, reached on every legiond-cpuset.timer tick
        out = self.run_script("sync 0", *[f"call {AC_P}"] * 5)
        self.assertEqual(len(self.logs(out)), 1, out)
        self.assertEqual(self.limits(), (30, 30))

    def test_unknown_power_state_logs_once(self):
        out = self.run_script("sync 1", *[f"call {UNKNOWN}"] * 3)
        self.assertEqual(len(self.logs(out)), 1, out)

    def test_a_write_after_any_skip_is_logged_again(self):
        # every path that returns without writing must make the next write visible
        skips = {
            "profile absent from the defaults": [f"call {AC_E}"],
            "custom mode": [f"call {AC_BP}"],
            "battery without bat_pl1/bat_pl2": [f"call {BAT_P}"],
            "power state unknown": [f"call {UNKNOWN}"],
            "constraint name unreadable": [
                "rm mmio/constraint_0_name",
                f"call {AC_P}",
                "write mmio/constraint_0_name long_term",
            ],
            "no MMIO zone": ["mv mmio mmio.gone", f"call {AC_P}", "mv mmio.gone mmio"],
        }
        for name, steps in skips.items():
            with self.subTest(skip=name):
                self.setUp()
                self.device("legion", pl1=DEFAULTS_PL1.replace(" max-power:160", ""))
                out = self.run_script("sync 1", f"call {AC_P}", *steps, f"call {AC_P}")
                writes = [line for line in self.logs(out) if line.startswith("cpu_powerlimit set to")]
                self.assertEqual(len(writes), 2, out)

    def test_implausible_default_skips_and_logs_once(self):
        self.device("legion", pl1="performance:9999\n")
        out = self.run_script("sync 1", *[f"call {AC_P}"] * 3)
        self.assertEqual(self.limits(), (30, 30))
        self.assertEqual(len(self.logs(out)), 1, out)
        self.assertIn("performance:9999", self.logs(out)[0])

    def test_wrong_constraint_name_writes_nothing_and_logs_once(self):
        (self.root / "mmio" / "constraint_1_name").write_text("peak_power\n")
        out = self.run_script("sync 1", *[f"call {AC_P}"] * 3)
        self.assertEqual(self.limits(), (30, 30))
        self.assertEqual(len(self.logs(out)), 1, out)

    # behaviour per power state

    def test_ac_modes_write_the_firmware_defaults(self):
        for state, expected in ((AC_Q, (55, 65)), (AC_B, (90, 125)), (AC_P, (145, 190)), (AC_E, (160, 205))):
            with self.subTest(state=state):
                self.run_script("sync 1", f"call {state}")
                self.assertEqual(self.limits(), expected)

    def test_ac_custom_mode_is_left_to_the_firmware(self):
        self.run_script("sync 1", f"call {AC_BP}")
        self.assertEqual(self.limits(), (30, 30))

    def test_battery_writes_the_configured_limits_in_every_mode_including_custom(self):
        # deliberate: on battery the configured DC limits win, custom mode included
        for state in (BAT_Q, BAT_B, BAT_BP, BAT_P):
            with self.subTest(state=state):
                self.setUp()
                self.run_script("sync 1", "bat 45 65", f"call {state}")
                self.assertEqual(self.limits(), (45, 65))

    def test_double_target_enters_and_leaves_with_hysteresis(self):
        out = self.run_script(
            "sync 1",
            "double_p 75 190 54 74",
            f"call {AC_P}",
            "write thermal/thermal_zone3/temp 55000",
            "write thermal/thermal_zone4/temp 75000",
            f"call {AC_P}",
            f"call {AC_P}",
            "write thermal/thermal_zone3/temp 52000",
            f"call {AC_P}",
            "write thermal/thermal_zone3/temp 50000",
            f"call {AC_P}",
        )
        self.assertEqual(
            [line for line in self.logs(out) if line.startswith("cpu_powerlimit set to")],
            [
                "cpu_powerlimit set to PL1 145 W, PL2 190 W",
                "cpu_powerlimit set to PL1 75 W, PL2 190 W",
                "cpu_powerlimit set to PL1 145 W, PL2 190 W",
            ],
        )
        self.assertEqual(sum("the double target" in line for line in out), 2, out)
        self.assertEqual(self.limits(), (145, 190))


if __name__ == "__main__":
    unittest.main()
