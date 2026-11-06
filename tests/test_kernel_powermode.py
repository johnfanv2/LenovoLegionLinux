"""Check the parked custom power mode handling (issue #651).

On J2CN a custom request on battery leaves the EC in balanced with the
"custom pending for AC" flag (CTPA) set, and the GameZone get method then
reports custom. The driver reads the EC flags to report that state as
balanced, and refuses custom on battery so it cannot park a request.

No module is loaded and no EC is read. The decision helpers are compiled from
the driver source against stubs, and the model config is checked textually.
"""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "kernel_module/legion-laptop.c"


def function(source, name):
    match = re.search(r"^static\s+[\w\s*]+\b" + name + r"\s*\([^;{}]*\)\s*\{", source, re.M)
    assert match is not None, name
    end = source.index("\n}", match.end()) + len("\n}")
    return source[match.start() : end]


HARNESS_C = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
typedef uint8_t u8;
#define BIT(n) (1U << (n))

__DEFINES__

enum legion_ec_powermode {
	LEGION_EC_POWERMODE_QUIET = 2,
	LEGION_EC_POWERMODE_BALANCED = 0,
	LEGION_EC_POWERMODE_PERFORMANCE = 1,
};

struct model_config { bool custom_powermode_requires_ac; };
struct legion_private { const struct model_config *conf; };
static int supplied;
static int power_supply_is_system_supplied(void) { return supplied; }

__FUNCTIONS__

int main(void) {
	/* CTPA set, CTMD clear, SPMO balanced: the request is parked. */
	assert(ec_custom_request_parked(0x02, LEGION_EC_POWERMODE_BALANCED));
	/* Other bits in the byte (CTMB is bit 4) do not matter. */
	assert(ec_custom_request_parked(0x12, LEGION_EC_POWERMODE_BALANCED));
	/* Custom active: really custom. */
	assert(!ec_custom_request_parked(0x01, LEGION_EC_POWERMODE_BALANCED));
	assert(!ec_custom_request_parked(0x03, LEGION_EC_POWERMODE_BALANCED));
	/* Nothing pending: leave the firmware's answer alone. */
	assert(!ec_custom_request_parked(0x00, LEGION_EC_POWERMODE_BALANCED));
	/* The get method only maps CTPA to custom when SPMO is balanced. */
	assert(!ec_custom_request_parked(0x02, LEGION_EC_POWERMODE_QUIET));
	assert(!ec_custom_request_parked(0x02, LEGION_EC_POWERMODE_PERFORMANCE));

	struct model_config j2cn = { .custom_powermode_requires_ac = true };
	struct model_config other = { .custom_powermode_requires_ac = false };
	struct legion_private priv = { .conf = &j2cn };

	supplied = 0; /* battery */
	assert(custom_powermode_blocked(&priv));
	supplied = 1; /* AC */
	assert(!custom_powermode_blocked(&priv));
	supplied = -19; /* -ENODEV: no power supply registered */
	assert(!custom_powermode_blocked(&priv));

	priv.conf = &other;
	supplied = 0;
	assert(!custom_powermode_blocked(&priv));
	return 0;
}
"""


class KernelPowermodeTest(unittest.TestCase):
    def test_parked_custom_and_battery_gate(self):
        source = SOURCE.read_text()
        defines = "\n".join(re.findall(r"^#define EC_CUSTOM_MODE_\w+ [^\n]+", source, re.M))
        functions = "\n\n".join(
            function(source, name) for name in ("ec_custom_request_parked", "custom_powermode_blocked")
        )
        code = HARNESS_C.replace("__DEFINES__", defines).replace("__FUNCTIONS__", functions)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "harness.c"
            binary = Path(tmp) / "harness"
            src.write_text(code)
            subprocess.run(["gcc", "-std=gnu11", "-Wall", "-Werror", str(src), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_only_j2cn_opts_in(self):
        source = SOURCE.read_text()
        for field in ("ec_custom_mode_register", "custom_powermode_requires_ac"):
            configs = re.findall(
                r"^static const struct model_config (\w+) = \{(?:(?!^\};).)*?\." + field, source, re.M | re.S
            )
            self.assertEqual(configs, ["model_j2cn"], field)
        j2cn = re.search(r"^static const struct model_config model_j2cn = \{.*?^\};", source, re.M | re.S)
        assert j2cn is not None
        j2cn = j2cn[0]
        self.assertIn(".ec_custom_mode_register = 0xC41D,", j2cn)
        self.assertIn(".custom_powermode_requires_ac = true,", j2cn)

    def test_custom_write_is_gated_and_wmi_read_is_fixed_up(self):
        source = SOURCE.read_text()
        write = function(source, "write_powermode")
        self.assertRegex(write, r"value == LEGION_WMI_POWERMODE_CUSTOM &&\s+custom_powermode_blocked\(priv\)")
        read = function(source, "read_powermode")
        self.assertIn("fixup_parked_custom_powermode(priv, powermode);", read)


if __name__ == "__main__":
    unittest.main()
