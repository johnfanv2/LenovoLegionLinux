"""Check the per-model temperature register scaffolding flag.

The driver used to read the CPU/GPU/IC temperature from fixed EC addresses
(0xC5E6/0xC5E7/0xC5E8) while also reading per-model EXT_*_TEMP_INPUT offsets
and then discarding them. The scaffolding keeps the fixed addresses as the
default and lets a model opt in per register once that register has been
validated on real hardware.

No module is loaded and no EC is read. The resolver is compiled from the
driver source against a stub, and the model configs are checked textually.
"""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "kernel_module/legion-laptop.c"

# The addresses the driver read before this change, per sensor.
LEGACY_CPU = 0xC5E6
LEGACY_GPU = 0xC5E7
LEGACY_IC = 0xC5E8

HARNESS_C = r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
typedef uint8_t u8;
typedef uint16_t u16;

struct model_config {
	u8 validated_temp_registers;
};

__FUNCTIONS__

int main(void) {
	/* Every model in the tree leaves the mask at zero, so the resolver must
	 * return the legacy address for each sensor. */
	struct model_config off = { .validated_temp_registers = 0 };
	assert(temp_input_register(&off, TEMP_REGISTER_CPU, 0x1234, EC_TEMP_INPUT_CPU) == 0xC5E6);
	assert(temp_input_register(&off, TEMP_REGISTER_GPU, 0x1234, EC_TEMP_INPUT_GPU) == 0xC5E7);
	assert(temp_input_register(&off, TEMP_REGISTER_IC, 0x1234, EC_TEMP_INPUT_IC) == 0xC5E8);

	/* A model register that is not opted in stays unused, even when it holds
	 * a plausible address. */
	assert(temp_input_register(&off, TEMP_REGISTER_CPU, 0xC538, EC_TEMP_INPUT_CPU) == LEGACY_CPU);

	/* Opting in per register: only the flagged sensor switches over. */
	struct model_config cpu_only = { .validated_temp_registers = TEMP_REGISTER_CPU };
	assert(temp_input_register(&cpu_only, TEMP_REGISTER_CPU, 0xC538, EC_TEMP_INPUT_CPU) == 0xC538);
	assert(temp_input_register(&cpu_only, TEMP_REGISTER_GPU, 0xC539, EC_TEMP_INPUT_GPU) == LEGACY_GPU);
	assert(temp_input_register(&cpu_only, TEMP_REGISTER_IC, 0xC5E8, EC_TEMP_INPUT_IC) == LEGACY_IC);

	struct model_config all = {
		.validated_temp_registers = TEMP_REGISTER_CPU | TEMP_REGISTER_GPU | TEMP_REGISTER_IC
	};
	assert(temp_input_register(&all, TEMP_REGISTER_CPU, 0xC538, EC_TEMP_INPUT_CPU) == 0xC538);
	assert(temp_input_register(&all, TEMP_REGISTER_GPU, 0xC539, EC_TEMP_INPUT_GPU) == 0xC539);
	assert(temp_input_register(&all, TEMP_REGISTER_IC, 0xC5A0, EC_TEMP_INPUT_IC) == 0xC5A0);

	/* The placeholder address 0xC5A0 that several configs carry must stay
	 * unused until a model explicitly opts in, so a placeholder can never be
	 * read by accident. */
	assert(temp_input_register(&off, TEMP_REGISTER_GPU, 0xC5A0, EC_TEMP_INPUT_GPU) == LEGACY_GPU);

	printf("ok\n");
	return 0;
}
"""


def function(source, name):
    """Return one top-level C function, brace matched."""
    match = re.search(r"^static\s+[\w\s*]+\b" + name + r"\s*\([^;{}]*\)\s*\{", source, re.M)
    if not match:
        raise AssertionError(f"could not find {name}()")
    depth = 0
    for index in range(source.index("{", match.end() - 1), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : index + 1]
    raise AssertionError(f"unbalanced braces in {name}()")


class TemperatureRegisterFlagTest(unittest.TestCase):
    def test_resolver_defaults_to_the_legacy_addresses(self):
        source = SOURCE.read_text()
        defines = "\n".join(
            match.group(0)
            for match in re.finditer(r"^#define (?:EC_TEMP_INPUT_\w+|TEMP_REGISTER_\w+) .*$", source, re.M)
        )
        body = (
            f"#define LEGACY_CPU 0x{LEGACY_CPU:04X}\n"
            f"#define LEGACY_GPU 0x{LEGACY_GPU:04X}\n"
            f"#define LEGACY_IC 0x{LEGACY_IC:04X}\n"
            + defines
            + "\n"
            + function(source, "temp_input_register")
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "harness.c")
            path.write_text(HARNESS_C.replace("__FUNCTIONS__", body))
            binary = Path(directory, "harness")
            subprocess.run(
                ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", str(path), "-o", str(binary)],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_only_evidenced_models_opt_in(self):
        """A model may opt in only with firmware-evidenced register offsets."""
        source = SOURCE.read_text()
        configs = re.findall(
            r"^static const struct model_config (\w+)\s*=\s*\{(.*?)^\s*};",
            source,
            re.M | re.S,
        )
        opted_in = {}
        for name, body in configs:
            match = re.search(r"\.validated_temp_registers\s*=\s*([^,\n]+)", body)
            if match:
                opted_in[name] = match.group(1)
        self.assertEqual(
            opted_in,
            {
                # Yoga Pro 7 14AHP9 (83E3, issue #630): the NCCN DSDT declares
                # TCPU/TGPU at EC RAM 0x07/0x08 in the ERAM window and the
                # firmware's own thermal (SSDT22) and GPU (SSDT4) code
                # reads/writes them; hardware read-back validation is tracked
                # in the issue.
                "model_nccn": "TEMP_REGISTER_CPU | TEMP_REGISTER_GPU",
            },
            "a model may opt in only with validated register offsets; "
            "add one here only with its evidence documented",
        )

    def test_legacy_addresses_are_named_constants(self):
        """The addresses must not be re-inlined at a call site again."""
        source = SOURCE.read_text()
        defines = dict(re.findall(r"^#define (EC_TEMP_INPUT_\w+)\s+(0[xX][cC]5[eE][678])\s*$", source, re.M))
        self.assertEqual(
            defines,
            {
                "EC_TEMP_INPUT_CPU": "0xC5E6",
                "EC_TEMP_INPUT_GPU": "0xC5E7",
                "EC_TEMP_INPUT_IC": "0xC5E8",
            },
        )
        # No read path may inline an address. The register offset tables are
        # data, not call sites, so lines that initialise a struct field are
        # excluded.
        call_sites = [
            line
            for line in source.splitlines()
            if re.search(r"0[xX][cC]5[eE][678]", line)
            and not line.strip().startswith("#define")
            and not re.match(r"^\s*\.EXT_\w+_TEMP_INPUT\s*=", line)
        ]
        self.assertEqual(
            call_sites,
            [],
            "temperature addresses belong in the EC_TEMP_INPUT_* constants, not inline",
        )

    def test_every_temperature_read_goes_through_the_resolver(self):
        """No read path may bypass the flag and hardcode an address."""
        source = SOURCE.read_text()
        for name in ("ec_read_sensor_values", "ec_read_temperature"):
            body = function(source, name)
            self.assertNotRegex(body, r"0[xX][cC]5[eE][678]", f"{name}() bypasses the flag")
            self.assertIn("temp_input_register(", body, f"{name}() must use the resolver")


if __name__ == "__main__":
    unittest.main()
