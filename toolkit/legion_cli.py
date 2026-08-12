#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# pylint: disable=wrong-import-order
import argcomplete
import argparse
import logging
import sys
import os
# Make it possible to run without installationimport
# pylint: disable=# pylint: disable=wrong-import-position
sys.path.insert(0, os.path.dirname(__file__) + "/..")
import legion_linux.legion
from legion_linux.legion import LegionModelFacade
from pathlib import Path
import subprocess
logging.basicConfig()
log = logging.getLogger(legion_linux.legion.__name__)
loglevels = ['NOTSET', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']
# will be set in main to user defined level after parsing
log.setLevel('ERROR')


class CLIFeatureCommand:
    def __init__(self, name: str, parser_subcommands, cmd_group: list, writeable: bool = True):
        self.name = name
        self.model = None
        status_parser = parser_subcommands.add_parser(
            f"{self.name}-status", help=f'Get current value for {self.name}')
        status_parser.set_defaults(
            func=lambda l, *args, **kwargs: self.command_status_cli(**kwargs))

        if writeable:
            enable_parser = parser_subcommands.add_parser(
                f"{self.name}-enable", help=f'Enable {self.name}')
            enable_parser.set_defaults(
                func=lambda l, *args, **kwargs: self.command_enable_cli(**kwargs))

            disable_parser = parser_subcommands.add_parser(
                f"{self.name}-disable", help=f'Disable {self.name}')
            disable_parser.set_defaults(
                func=lambda l, *args, **kwargs: self.command_disable_cli(**kwargs))

        if cmd_group is not None:
            cmd_group.append(self)

    def set_model(self, model: LegionModelFacade):
        self.model = model

    def check_if_exist(self):
        if self.exists():
            return True
        print(
            "Command not available because feature is not available or kernel module is not loaded.")
        return False

    def command_status_cli(self, **_) -> int:
        if self.check_if_exist():
            return self.command_status()
        return -10

    def command_enable_cli(self, **_) -> int:
        if self.check_if_exist():
            return self.command_enable()
        return -10

    def command_disable_cli(self, **_) -> int:
        if self.check_if_exist():
            return self.command_disable()
        return -10

    # pylint: disable=no-self-use
    def exists(self) -> bool:
        return False

    # pylint: disable=no-self-use
    def command_status(self, **_) -> int:
        return 0

    # pylint: disable=no-self-use
    def command_enable(self, **_) -> int:
        return -1

    # pylint: disable=no-self-use
    def command_disable(self, **_) -> int:
        return -1


class MiniFancurveFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("minifancurve", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.fancurve_io.exists()

    def command_status(self, **_) -> int:
        print(self.model.fancurve_io.get_minifancuve())
        return 0

    def command_enable(self, **_) -> int:
        self.model.fancurve_io.set_minifancuve(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.fancurve_io.set_minifancuve(False)
        return 0


class LockFanControllerFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("lockfancontroller", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.lockfancontroller.exists()

    def command_status(self, **_) -> int:
        print(self.model.lockfancontroller.get())
        return 0

    def command_enable(self, **_) -> int:
        self.model.lockfancontroller.set(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.lockfancontroller.set(False)
        return 0


class MaximumFanSpeedFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("maximumfanspeed", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.maximum_fanspeed.exists()

    def command_status(self, **_) -> int:
        print(self.model.maximum_fanspeed.get())
        return 0

    def command_enable(self, **_) -> int:
        self.model.maximum_fanspeed.set(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.maximum_fanspeed.set(False)
        return 0


class BatteryConservationFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("batteryconservation", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.battery_conservation.exists()

    def command_status(self, **_) -> int:
        print(self.model.battery_conservation.get())
        return 0

    def command_enable(self, **_) -> int:
        self.model.battery_conservation.set(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.battery_conservation.set(False)
        return 0


class FnLockFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("fnlock", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.fn_lock.exists()

    def command_status(self, **_) -> int:
        print(self.model.fn_lock.get())
        return 0

    def command_enable(self, **_) -> int:
        self.model.fn_lock.set(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.fn_lock.set(False)
        return 0


class TouchpadFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("touchpad", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.touchpad.exists()

    def command_status(self, **_) -> int:
        print(self.model.touchpad.get())
        return 0

    def command_enable(self, **_) -> int:
        self.model.touchpad.set(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.touchpad.set(False)
        return 0


class CameraPowerFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("camera-power", parser_subcommands, cmd_group, False)
        self.model = model

    def exists(self) -> bool:
        return self.model.camera_power.exists()

    def command_status(self, **_) -> int:
        print(self.model.camera_power.get())
        return 0


class OnPowerSupplyFeatureCommand(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("on-power-supply", parser_subcommands, cmd_group, False)
        self.model = model

    def exists(self) -> bool:
        return self.model.on_power_supply.exists()

    def command_status(self, **_) -> int:
        print(self.model.on_power_supply.get())
        return 0


class AlwaysOnUsbCharging(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("always-on-usb-charging", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.always_on_usb_charging.exists()

    def command_status(self, **_) -> int:
        print(self.model.always_on_usb_charging.get())
        return 0

    def command_enable(self, **_) -> int:
        self.model.always_on_usb_charging.set(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.always_on_usb_charging.set(False)
        return 0


class RapidCharging(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("rapid-charging", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.rapid_charging.exists()

    def command_status(self, **_) -> int:
        print(self.model.rapid_charging.get())
        return 0

    def command_enable(self, **_) -> int:
        self.model.rapid_charging.set(True)
        return 0

    def command_disable(self, **_) -> int:
        self.model.rapid_charging.set(False)
        return 0


class HybridMode(CLIFeatureCommand):
    def __init__(self, parser_subcommands, model: LegionModelFacade, cmd_group: list):
        super().__init__("hybrid-mode", parser_subcommands, cmd_group)
        self.model = model

    def exists(self) -> bool:
        return self.model.gsync.exists()

    def command_status(self, **_) -> int:
        print("This is the current state. Changing it by setting it will apply only after a reboot.")
        print(self.model.gsync.get())
        return 0

    def command_enable(self, **_) -> int:
        print("Changes will only apply after a reboot.")
        self.model.gsync.set(True)
        return 0

    def command_disable(self, **_) -> int:
        print("Changes will only apply after a reboot.")
        self.model.gsync.set(False)
        return 0


def autocomplete_install(_, **__) -> int:
    cmd = f"eval \"$(register-python-argcomplete {__file__})\""
    print("PLEASE RUN THE COMMAND:")
    print(cmd)


def fancurve_write_preset_to_hw(legion: LegionModelFacade, presetname: str, **_) -> int:
    # pylint: disable=unused-argument
    legion.fancurve_write_preset_to_hw(presetname, write_minifancurve=True)
    print(f'Successfully wrote preset {presetname} to hardware')
    return 0


def fancurve_write_hw_to_preset(legion: LegionModelFacade, presetname: str, **_) -> int:
    # pylint: disable=unused-argument
    legion.fancurve_write_hw_to_preset(presetname)
    print(f'Successfully wrote hardware to preset {presetname}')
    return 0


def fancurve_write_file_to_hw(legion: LegionModelFacade, filename: str, **_) -> int:
    # pylint: disable=unused-argument
    legion.fancurve_write_file_to_hw(filename, write_minifancurve=True)
    print(f'Successfully wrote fan curve from file {filename} to hardware')
    return 0


def fancurve_write_hw_to_file(legion: LegionModelFacade, filename: str, **_) -> int:
    # pylint: disable=unused-argument
    legion.fancurve_write_hw_to_file(filename)
    print(f'Successfully wrote fan curve from hardware to file {filename}')
    return 0


def fancurve_write_preset_for_current_profile(legion: LegionModelFacade, **_) -> int:
    # pylint: disable=unused-argument
    legion.fancurve_write_preset_for_current_profile(write_minifancurve=True)
    return 0


def conservation_apply_mode_for_current_battery_capacity(legion: LegionModelFacade,
                                                         lowerlimit=50, upperlimit=60, **_) -> int:
    print(legion.conservation_apply_mode_for_current_battery_capacity(
        lowerlimit, upperlimit))
    return 0


def monitor(legion: LegionModelFacade, period=None, **_) -> int:
    print("Starting monitoring:")
    legion.run_monitors(period_s=period)
    return 0


def set_feature(legion: LegionModelFacade, name, values, **_) -> int:
    log.setLevel('INFO')
    if legion.set_feature_to_str_value(name, values):
        return 0
    print("Feature not found.")
    for feat in legion.get_all_features():
        print(feat)
    return -2


_PCORES = [i for i in range(16) if Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq").exists()
           and int(Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq").read_text()) >= 4500000]
_ECORES = [i for i in range(16) if Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq").exists()
           and int(Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_max_freq").read_text()) < 4500000]

def cpu_pcore_freq(legion: LegionModelFacade, freq: int = None, **_) -> int:
    if freq is None:
        # status: show current
        for i in _PCORES[:1]:
            p = Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq")
            if p.exists():
                print(f"P-core max: {int(p.read_text())//1000} MHz")
        return 0
    khz = freq * 1000
    for i in _PCORES:
        p = Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq")
        if p.exists():
            p.write_text(str(khz) + "\n")
    print(f"P-core max set to {freq} MHz")
    return 0

def cpu_ecore_freq(legion: LegionModelFacade, freq: int = None, **_) -> int:
    if freq is None:
        for i in _ECORES[:1]:
            p = Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq")
            if p.exists():
                print(f"E-core max: {int(p.read_text())//1000} MHz")
        return 0
    khz = freq * 1000
    for i in _ECORES:
        p = Path(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq")
        if p.exists():
            p.write_text(str(khz) + "\n")
    print(f"E-core max set to {freq} MHz")
    return 0

# ── LOQ 83SC power limit controls ────────────────────────────────────────────

LEGION_BASE = "/sys/devices/platform/legion"

def _read_feature(name):
    try: return int(Path(f"{LEGION_BASE}/{name}").read_text().strip())
    except: return None

def _write_feature(name, val):
    p = f"{LEGION_BASE}/{name}"
    try:
        Path(p).write_text(str(val))
    except PermissionError:
        subprocess.run(["pkexec", "sh", "-c", f"echo {val} > {p}"],
                       capture_output=True, timeout=5)

def tdp_cmd(legion, pl1=None, pl2=None, **_):
    """Get or set PL1/PL2 with constraint: PL2 >= PL1."""
    if pl1 is None and pl2 is None:
        cur_pl1 = _read_feature("cpu_longterm_powerlimit")
        cur_pl2 = _read_feature("cpu_shortterm_powerlimit")
        print(f"PL1: {cur_pl1}W  PL2: {cur_pl2}W")
        return 0
    cur_pl1 = _read_feature("cpu_longterm_powerlimit") or 55
    cur_pl2 = _read_feature("cpu_shortterm_powerlimit") or 80
    if pl1 is not None:
        if pl2 is None:
            pl2 = cur_pl2
        if pl1 > pl2:
            pl2 = pl1
    elif pl2 is not None:
        if pl2 < cur_pl1:
            pl1 = pl2
        else:
            pl1 = cur_pl1
    _write_feature("cpu_longterm_powerlimit", pl1)
    _write_feature("cpu_shortterm_powerlimit", pl2)
    actual_pl1 = _read_feature("cpu_longterm_powerlimit")
    actual_pl2 = _read_feature("cpu_shortterm_powerlimit")
    print(f"PL1: {actual_pl1}W  PL2: {actual_pl2}W")
    return 0

def cpu_tau_cmd(legion, value=None, **_):
    if value is None:
        print(f"TAU: {_read_feature('cpu_l1_tau')}s")
    else:
        _write_feature("cpu_l1_tau", value)
        print(f"TAU set to: {_read_feature('cpu_l1_tau')}s")
    return 0

def cpu_crossload_cmd(legion, value=None, **_):
    if value is None:
        print(f"Cross Loading: {_read_feature('cpu_cross_loading_powerlimit')}W")
    else:
        _write_feature("cpu_cross_loading_powerlimit", value)
        print(f"Cross Loading set to: {_read_feature('cpu_cross_loading_powerlimit')}W")
    return 0

def cpu_temp_limit_cmd(legion, value=None, **_):
    if value is None:
        print(f"CPU Temp Limit: {_read_feature('cpu_temperature_limit')}°C")
    else:
        _write_feature("cpu_temperature_limit", value)
        print(f"CPU Temp Limit set to: {_read_feature('cpu_temperature_limit')}°C")
    return 0

def gpu_dynamic_boost_cmd(legion, value=None, **_):
    if value is None:
        print(f"Dynamic Boost (PPAB): {_read_feature('gpu_oc')}W")
    else:
        _write_feature("gpu_oc", value)
        print(f"Dynamic Boost (PPAB) set to: {_read_feature('gpu_oc')}W")
    return 0

def gpu_ctgp_cmd(legion, value=None, **_):
    if value is None:
        print(f"cTGP: {_read_feature('gpu_ctgp_powerlimit')}W")
    else:
        _write_feature("gpu_ctgp_powerlimit", value)
        print(f"cTGP set to: {_read_feature('gpu_ctgp_powerlimit')}W")
    return 0

def gpu_total_proc_cmd(legion, value=None, **_):
    if value is None:
        print(f"Total Proc Power (Offset): {_read_feature('gpu_power_target_offset')}W")
    else:
        _write_feature("gpu_power_target_offset", value)
        print(f"Total Proc Power (Offset) set to: {_read_feature('gpu_power_target_offset')}W")
    return 0

def create_argparser()->argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Legion CLI')
    parser.add_argument(
        '--donotexpecthwmon', action='store_true', help='Do not check hwmon dir when not needed', default=False)
    parser.add_argument('--loglevel', type=str,
                        help='Level of log output', choices=loglevels, default='ERROR')

    subcommands = parser.add_subparsers(title='subcommands', dest='subcommand')

    autocomplete_install_parser = subcommands.add_parser(
        'autocomplete-install', help='Install autocompletion in shell for this tool')
    autocomplete_install_parser.set_defaults(func=autocomplete_install)

    preset_to_hw_parser = subcommands.add_parser(
        'fancurve-write-preset-to-hw', help='Write fan curve from preset to hardware')
    preset_to_hw_parser.add_argument(
        'presetname', type=str, help='Name of the preset')
    preset_to_hw_parser.add_argument(
        '--preset-dir', type=str, help='Path of the directory with presets')
    preset_to_hw_parser.set_defaults(func=fancurve_write_preset_to_hw)

    hw_to_preset_parser = subcommands.add_parser(
        'fancurve-write-hw-to-preset', help='Write fan curve from hardware to preset')
    hw_to_preset_parser.add_argument(
        'presetname', type=str, help='Name of the preset')
    hw_to_preset_parser.add_argument(
        '--preset-dir', type=str, help='Path of the directory with presets')
    hw_to_preset_parser.set_defaults(func=fancurve_write_hw_to_preset)

    file_to_hw_parser = subcommands.add_parser(
        'fancurve-write-file-to-hw', help='Write fan curve from file to hardware')
    file_to_hw_parser.add_argument(
        'filename', type=str, help='Name of the file')
    file_to_hw_parser.set_defaults(func=fancurve_write_file_to_hw)

    hw_to_file_parser = subcommands.add_parser(
        'fancurve-write-hw-to-file', help='Write fan curve from hardware to file')
    hw_to_file_parser.add_argument(
        'filename', type=str, help='Name of the file')
    hw_to_file_parser.set_defaults(func=fancurve_write_hw_to_file)

    hw_to_file_parser = subcommands.add_parser(
        'fancurve-write-current-preset-to-hw',
        help='Write fan curve for the current profile (power mode, power supply status) to hardware')
    hw_to_file_parser.set_defaults(
        func=fancurve_write_preset_for_current_profile)

    custom_conservation_mode = subcommands.add_parser(
        'custom-conservation-mode-apply', help='Turn conservation mode on or off depending on battery level')
    custom_conservation_mode.add_argument(
        'lowerlimit', type=int, help='Limit when conservation mode should be turned off, e.g. 60', default=61)
    custom_conservation_mode.add_argument(
        'upperlimit', type=int, help='Limit when conservation mode should be turned on, e.g. 80', default=81)
    custom_conservation_mode.set_defaults(
        func=conservation_apply_mode_for_current_battery_capacity)

    monitor_cmd = subcommands.add_parser(
        'monitor', help='Run monitors with notifications')
    monitor_cmd.add_argument(
        'period', type=int, help='Monitoring period in seconds', default=60)
    monitor_cmd.set_defaults(
        func=monitor)

    set_feature_cmd = subcommands.add_parser(
        'set-feature', help='Set feature')
    set_feature_cmd.add_argument(
        'name', type=str, help='Name of feature')
    set_feature_cmd.add_argument(
        'values', type=str, help='Value of feature', nargs='+')
    set_feature_cmd.set_defaults(
        func=set_feature)

    pcore_freq_cmd = subcommands.add_parser(
        'cpu-pcore-freq', help='Get or set P-core max frequency (MHz)')
    pcore_freq_cmd.add_argument(
        'freq', type=int, nargs='?', default=None,
        help='Frequency in MHz (omit to read current)')
    pcore_freq_cmd.set_defaults(func=cpu_pcore_freq)

    ecore_freq_cmd = subcommands.add_parser(
        'cpu-ecore-freq', help='Get or set E-core max frequency (MHz)')
    ecore_freq_cmd.add_argument(
        'freq', type=int, nargs='?', default=None,
        help='Frequency in MHz (omit to read current)')
    ecore_freq_cmd.set_defaults(func=cpu_ecore_freq)

    tdp_cmd_parser = subcommands.add_parser('tdp', help='Get or set PL1/PL2 (enforces PL2 >= PL1)')
    tdp_cmd_parser.add_argument('--pl1', type=int, default=None, help='PL1 in watts')
    tdp_cmd_parser.add_argument('--pl2', type=int, default=None, help='PL2 in watts')
    tdp_cmd_parser.set_defaults(func=tdp_cmd)

    tau_cmd_parser = subcommands.add_parser('cpu-tau', help='Get or set TAU (PL1 duration)')
    tau_cmd_parser.add_argument('value', type=int, nargs='?', default=None, help='Duration in seconds')
    tau_cmd_parser.set_defaults(func=cpu_tau_cmd)

    cl_cmd_parser = subcommands.add_parser('cpu-crossload', help='Get or set cross loading limit')
    cl_cmd_parser.add_argument('value', type=int, nargs='?', default=None, help='Power in watts')
    cl_cmd_parser.set_defaults(func=cpu_crossload_cmd)

    ct_cmd_parser = subcommands.add_parser('cpu-temp-limit', help='Get or set CPU temperature limit')
    ct_cmd_parser.add_argument('value', type=int, nargs='?', default=None, help='Temperature in °C')
    ct_cmd_parser.set_defaults(func=cpu_temp_limit_cmd)

    db_cmd_parser = subcommands.add_parser('gpu-dynamic-boost', help='Get or set GPU dynamic boost / PPAB (via gpu_oc)')
    db_cmd_parser.add_argument('value', type=int, nargs='?', default=None, help='Power in watts (0-15, step 5)')
    db_cmd_parser.set_defaults(func=gpu_dynamic_boost_cmd)

    ctgp_cmd_parser = subcommands.add_parser('gpu-ctgp', help='Get or set cTGP limit')
    ctgp_cmd_parser.add_argument('value', type=int, nargs='?', default=None, help='Power in watts (35-50, step 5)')
    ctgp_cmd_parser.set_defaults(func=gpu_ctgp_cmd)

    poff_cmd_parser = subcommands.add_parser('gpu-total-proc', help='Get or set total processing power target (offset)')
    poff_cmd_parser.add_argument('value', type=int, nargs='?', default=None, help='Power in watts (10-45, step 5)')
    poff_cmd_parser.set_defaults(func=gpu_total_proc_cmd)

    return parser, subcommands

def main():
    parser, subcommands = create_argparser()

    cmd_group = []
    MiniFancurveFeatureCommand(subcommands, None, cmd_group)
    LockFanControllerFeatureCommand(subcommands, None, cmd_group)
    MaximumFanSpeedFeatureCommand(subcommands, None, cmd_group)
    BatteryConservationFeatureCommand(subcommands, None, cmd_group)
    FnLockFeatureCommand(subcommands, None, cmd_group)
    TouchpadFeatureCommand(subcommands, None, cmd_group)
    CameraPowerFeatureCommand(subcommands, None, cmd_group)
    OnPowerSupplyFeatureCommand(subcommands, None, cmd_group)
    AlwaysOnUsbCharging(subcommands, None, cmd_group)
    RapidCharging(subcommands, None, cmd_group)
    HybridMode(subcommands, None, cmd_group)

    # only add autocompletion if package is installed
    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    log.setLevel(args.loglevel)

    if args.subcommand is None:
        parser.print_help()
    else:
        legion = LegionModelFacade(expect_hwmon=not args.donotexpecthwmon)
        for cmd in cmd_group:
            cmd.set_model(legion)
        # set global options
        if "preset_dir" in args and args.preset_dir is not None:
            legion.set_preset_folder(args.preset_dir)

        args.func(legion, **vars(args))


if __name__ == '__main__':
    main()
