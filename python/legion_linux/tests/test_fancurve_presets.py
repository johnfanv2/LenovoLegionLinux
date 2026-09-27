"""Tests for resolving the shipped fan curve preset for the current power mode.

No hardware is touched: the platform profile, the power supply state, the
preset repository and the fancurve write are all stubbed or pointed at a
non-existent directory.
"""

import contextlib
import io
import unittest
from unittest import mock

from legion_linux import legion
from legion_linux import legion_cli
from legion_linux.legion import PlatformProfileFeature

# Of the power modes the driver reports, only these have a matching preset.
PROFILES_WITH_PRESET = ["balanced", "performance"]
PROFILES_WITHOUT_PRESET = ["low-power", "custom", "max-power"]

# Shipped presets that this code path can never select. platform_profile
# reports low-power, while the preset naming (inherited from legiond) uses
# quiet, so only "balanced" and "performance" overlap between the two
# vocabularies. The unreachable presets stay reachable by name from the GUI
# and from legiond.
PRESETS_NOT_REACHABLE_HERE = [
    "balanced-performance-ac",
    "balanced-performance-battery",
    "extreme-ac",
    "extreme-battery",
    "quiet-ac",
    "quiet-battery",
]


def stub_facade(profile, is_on_powersupply, repository):
    """A stand-in for LegionModelFacade exposing only what the method uses."""

    class _Stub:
        pass

    stub = _Stub()
    stub.on_power_supply = mock.Mock()
    stub.on_power_supply.get.return_value = is_on_powersupply
    stub.platform_profile = mock.Mock()
    stub.platform_profile.get.return_value = profile
    stub.fancurve_repo = repository
    stub.fancurve_io = mock.Mock()
    return stub


def real_repository():
    """A FanCurveRepository with the shipped preset names but no files."""
    repository = legion.FanCurveRepository.__new__(legion.FanCurveRepository)
    legion.FanCurveRepository.__init__(repository, "/nonexistent-preset-dir")
    return repository


def repository_with_preset():
    """A repository that resolves a preset and yields a curve."""
    repository = mock.Mock()
    repository.fancurve_presets = {"balanced-ac": None}
    repository.get_names.return_value = ["balanced-ac"]
    repository.does_exists_by_name.return_value = True
    repository.load_by_name.return_value = legion.FanCurve("balanced-ac", [])
    repository.get_preset_name.side_effect = (
        lambda profile, is_on_powersupply: f"{profile}-{'ac' if is_on_powersupply else 'battery'}"
    )
    return repository


class PresetCoverageTest(unittest.TestCase):
    def test_every_platform_profile_resolves_to_a_known_or_unknown_preset_name(self):
        repository = real_repository()
        known = []
        unknown = []
        # constructing the feature only records sysfs paths, it reads nothing
        profiles = [value.value for value in PlatformProfileFeature().all_values]
        for profile in profiles:
            for is_on_powersupply in (True, False):
                name = legion.FanCurveRepository.get_preset_name(profile, is_on_powersupply)
                (known if name in repository.fancurve_presets else unknown).append((profile, name))
        self.assertEqual(
            sorted({profile for profile, _ in unknown}),
            sorted(PROFILES_WITHOUT_PRESET),
            "power modes without a preset changed; update PROFILES_WITHOUT_PRESET",
        )
        self.assertEqual(
            sorted({profile for profile, _ in known}),
            sorted(PROFILES_WITH_PRESET),
            "power modes with a preset changed; update PROFILES_WITH_PRESET",
        )

    def test_shipped_presets_that_this_path_can_never_select(self):
        repository = real_repository()
        profiles = [value.value for value in PlatformProfileFeature().all_values]
        reachable = {
            legion.FanCurveRepository.get_preset_name(profile, is_on_powersupply)
            for profile in profiles
            for is_on_powersupply in (True, False)
        }
        unreachable = sorted(set(repository.fancurve_presets) - reachable)
        self.assertEqual(unreachable, sorted(PRESETS_NOT_REACHABLE_HERE))


class WritePresetForCurrentProfileTest(unittest.TestCase):
    def write(self, profile, is_on_powersupply, repository):
        stub = stub_facade(profile, is_on_powersupply, repository)
        result = legion.LegionModelFacade.fancurve_write_preset_for_current_profile(stub, write_minifancurve=True)
        return result, stub.fancurve_io

    def test_known_power_mode_writes_and_reports_success(self):
        result, fancurve_io = self.write("balanced", True, repository_with_preset())
        self.assertTrue(result)
        fancurve_io.write_fan_curve.assert_called_once()

    def test_power_mode_without_preset_reports_failure_and_writes_nothing(self):
        for profile in PROFILES_WITHOUT_PRESET:
            with self.subTest(profile=profile):
                result, fancurve_io = self.write(profile, True, real_repository())
                self.assertFalse(result)
                fancurve_io.write_fan_curve.assert_not_called()

    def test_missing_battery_preset_falls_back_to_ac_and_still_succeeds(self):
        repository = repository_with_preset()
        repository.fancurve_presets = {"extreme-battery": None}
        repository.does_exists_by_name.return_value = False
        result, fancurve_io = self.write("extreme", False, repository)
        self.assertTrue(result)
        self.assertEqual(repository.load_by_name.call_args[0][0], "extreme-ac")
        fancurve_io.write_fan_curve.assert_called_once()


class CliExitCodeTest(unittest.TestCase):
    def run_cli(self, facade):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = legion_cli.fancurve_write_preset_for_current_profile(facade)
        return code, stderr.getvalue()

    def test_nonzero_and_explanation_when_no_preset_was_written(self):
        facade = mock.Mock()
        facade.fancurve_write_preset_for_current_profile.return_value = False
        code, stderr = self.run_cli(facade)
        self.assertEqual(code, 1)
        self.assertIn("nothing was written", stderr)

    def test_zero_when_a_curve_was_written(self):
        facade = mock.Mock()
        facade.fancurve_write_preset_for_current_profile.return_value = True
        code, stderr = self.run_cli(facade)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
