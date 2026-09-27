"""Drive legiond's command state machine with stubbed hardware.

`legiond` writes to the EC and to ACPI methods, so this never calls into the
real modules: `set_all`, `set_cpu`, `set_fancurve`, `set_gpu`, `get_powerstate`
and `reload_config` are all replaced, and only `handle_command()` - the code that
decides *whether* those would be called - is the code under test.

The same approach as tests/test_kernel_fancurve.py: compile the real source
with fixtures, so the assertions cover the shipped file rather than a copy of it.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

LEGIOND_DIR = Path(__file__).resolve().parents[1] / "extra/service/legiond"

# The harness includes legiond.c directly so it can reach the static
# handle_command(), with main() and the config loader renamed out of the way.
HARNESS = r"""
#define main legiond_unused_main
#define reload_config legiond_unused_reload_config
#include "legiond.c"
#undef main
#undef reload_config

#include <stdio.h>

/* every path that would reach the hardware is replaced */
int set_all_calls;
int set_cpu_calls;

int set_all(POWER_STATE s, LEGIOND_CONFIG *c) { (void)s; (void)c; set_all_calls++; return 0; }
int set_cpu(POWER_STATE s, LEGIOND_CONFIG *c) { (void)s; (void)c; set_cpu_calls++; return 0; }
int set_fancurve(POWER_STATE s, LEGIOND_CONFIG *c) { (void)s; (void)c; return 0; }
int set_gpu(POWER_STATE s, LEGIOND_CONFIG *c) { (void)s; (void)c; return 0; }
POWER_STATE get_powerstate(void) { return P_AC_B; }
void pretty(const char *msg) { (void)msg; }
static void reload_config(void) { }
int parseconf(LEGIOND_CONFIG *conf) { (void)conf; return 0; }

static void dispatch(const char *label, LEGIOND_REQUEST *req)
{
	handle_command(req);
	printf("triggered_%s=%s\n", label, triggered ? "true" : "false");
}

int main(void)
{
	LEGIOND_REQUEST req;
	memset(&req, 0, sizeof(req));
	req.cmd = CMD_FANSET;
	req.delay_s = 60;

	/* A fanset with a delay means "apply later": cpuset must wait. */
	dispatch("after_fanset", &req);
	set_cpu_calls = 0;
	req.cmd = CMD_CPUSET;
	handle_command(&req);
	printf("cpuset_after_fanset=%d\n", set_cpu_calls);

	/* A reload applies everything right now, so cpuset must not be
	 * suppressed afterwards: set_all has run since the last fanset. */
	req.cmd = CMD_RELOAD;
	dispatch("after_reload", &req);
	set_cpu_calls = 0;
	req.cmd = CMD_CPUSET;
	handle_command(&req);
	printf("cpuset_after_reload=%d\n", set_cpu_calls);

	/* And the flag must not become sticky: a later fanset has to be able
	 * to suppress cpuset again. */
	req.cmd = CMD_FANSET;
	dispatch("after_second_fanset", &req);
	set_cpu_calls = 0;
	req.cmd = CMD_CPUSET;
	handle_command(&req);
	printf("cpuset_after_second_fanset=%d\n", set_cpu_calls);
	return 0;
}
"""


def read_fields(output):
    """Parse the harness output into a dict of int/bool values."""
    fields = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if value in ("true", "false"):
            fields[key] = value == "true"
        elif value.lstrip("-").isdigit():
            fields[key] = int(value)
    return fields


@unittest.skipIf(shutil.which("gcc") is None, "gcc is required to build the harness")
class CommandStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields = read_fields(cls.run_harness())

    @staticmethod
    def run_harness():
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "harness.c"
            source.write_text(HARNESS, encoding="utf-8")
            binary = Path(tmp) / "harness"
            build = subprocess.run(
                ["gcc", "-std=gnu2x", f"-I{LEGIOND_DIR}", "-o", str(binary), str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            if build.returncode != 0:
                # gcc is present, so a harness that does not compile is a real
                # problem with the file under test - do not let it hide as a skip
                raise AssertionError(f"harness did not build:\n{build.stderr}")
            run = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
            return run.stdout

    def test_fanset_suppresses_cpuset_until_the_timer_fires(self):
        # documented intent: a delayed fanset means the config is not current yet
        self.assertFalse(self.fields["triggered_after_fanset"])
        self.assertEqual(self.fields["cpuset_after_fanset"], 0)

    def test_reload_marks_the_config_as_applied(self):
        # CMD_RELOAD runs set_all, so triggered must be true afterwards
        self.assertTrue(
            self.fields["triggered_after_reload"],
            "CMD_RELOAD ran set_all but left triggered false, so a following "
            "CMD_CPUSET is suppressed even though the reload already applied it",
        )

    def test_cpuset_is_applied_after_a_reload(self):
        self.assertEqual(
            self.fields["cpuset_after_reload"],
            1,
            "legiond-ctl cpuset printed 'do nothing' after legiond-ctl reload",
        )

    def test_a_later_fanset_can_suppress_cpuset_again(self):
        # guards against 'fixing' the reload by making triggered permanently true
        self.assertFalse(self.fields["triggered_after_second_fanset"])
        self.assertEqual(self.fields["cpuset_after_second_fanset"], 0)


if __name__ == "__main__":
    unittest.main()
