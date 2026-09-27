"""Tests for the exit codes legion_cli reports to the shell.

A process exit status is a single unsigned byte, so a negative return value is
truncated by the kernel and reaches the shell as an unrelated number. The
source scan here is what keeps that from coming back; the behavioural tests
pin the codes that callers may want to distinguish.

No hardware is touched: the feature commands are exercised with their
`exists()` overridden.
"""

import re
import unittest
from pathlib import Path

from legion_linux import legion_cli

SOURCE = Path(legion_cli.__file__).resolve()

ALL_EXIT_CODES = [
    legion_cli.EXIT_OK,
    legion_cli.EXIT_NOT_IMPLEMENTED,
    legion_cli.EXIT_FEATURE_UNAVAILABLE,
    legion_cli.EXIT_FEATURE_NOT_FOUND,
]


class ExitCodeRangeTest(unittest.TestCase):
    def test_every_exit_constant_fits_in_a_process_status(self):
        for name in [n for n in dir(legion_cli) if n.startswith("EXIT_")]:
            with self.subTest(name=name):
                value = getattr(legion_cli, name)
                self.assertIsInstance(value, int)
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 255)

    def test_exit_codes_are_distinct(self):
        # two meanings sharing a code would make one of them undetectable
        self.assertEqual(len(ALL_EXIT_CODES), len(set(ALL_EXIT_CODES)))

    def test_no_function_returns_a_negative_value(self):
        # A "return -1" anywhere in this module silently becomes 255 (or any
        # other value) for every caller in a shell script, a systemd unit or
        # legiond. Catch it at the source rather than at the call site.
        negative_returns = []
        for number, line in enumerate(SOURCE.read_text(encoding="utf-8").splitlines(), start=1):
            if re.search(r"\breturn\s+-\d", line):
                negative_returns.append(f"{number}: {line.strip()}")
        self.assertEqual(negative_returns, [], "use the EXIT_* constants instead")


class FeatureCommandExitCodeTest(unittest.TestCase):
    def test_unavailable_feature_reports_its_own_code(self):
        command = legion_cli.CLIFeatureCommand.__new__(legion_cli.CLIFeatureCommand)
        command.exists = lambda: False
        for method in ("command_status_cli", "command_enable_cli", "command_disable_cli"):
            with self.subTest(method=method):
                self.assertEqual(getattr(command, method)(), legion_cli.EXIT_FEATURE_UNAVAILABLE)

    def test_unimplemented_action_reports_its_own_code(self):
        command = legion_cli.CLIFeatureCommand.__new__(legion_cli.CLIFeatureCommand)
        self.assertEqual(command.command_status(), legion_cli.EXIT_OK)
        self.assertEqual(command.command_enable(), legion_cli.EXIT_NOT_IMPLEMENTED)
        self.assertEqual(command.command_disable(), legion_cli.EXIT_NOT_IMPLEMENTED)

    def test_unavailable_code_differs_from_unimplemented_code(self):
        # the base class reports both conditions, so a caller that checks for
        # one must not accidentally match the other
        self.assertNotEqual(legion_cli.EXIT_FEATURE_UNAVAILABLE, legion_cli.EXIT_NOT_IMPLEMENTED)


if __name__ == "__main__":
    unittest.main()
