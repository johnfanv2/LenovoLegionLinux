#!/usr/bin/env python3
"""
Legion Linux Toolkit — CLI launcher (generated dispatcher, do not edit by hand).

This entry point detects the host laptop model and loads the matching codebase:

  * Lenovo LOQ 83SC  (DMI product_name "83SC", BIOS version "SECN*")
        -> the 83SC-specific custom CLI   (custom/legion-CLI.py)
  * any other model -> the upstream Legion Linux CLI   (embedded as base64)

Upstream source: LenovoLegionLinux (legion_linux.legion_gui / legion_cli)
Regenerate with: tools/build_combined.py
"""
import base64
from pathlib import Path


def _read_dmi(field):
    try:
        return Path(f"/sys/class/dmi/id/{field}").read_text().strip()
    except OSError:
        return ""


def _detect_loq_83sc():
    """True only for the Lenovo LOQ 83SC this custom build targets."""
    vendor = _read_dmi("sys_vendor").upper()
    product = _read_dmi("product_name").strip()
    bios = _read_dmi("bios_version").strip()
    return vendor == "LENOVO" and product == "83SC" and bios.upper().startswith("SECN")


# Model gate: 83SC -> custom build, everything else -> upstream build.
_is_custom = _detect_loq_83sc()

if _is_custom:
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

    from lib.lll_adapter import legion_sysfs_base

    def _read_feature(name):
        try: return int((legion_sysfs_base() / name).read_text().strip())
        except: return None

    def _write_feature(name, val):
        p = legion_sysfs_base() / name
        try:
            p.write_text(str(val))
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

    def gpu_temp_limit_cmd(legion, value=None, **_):
        if value is None:
            print(f"GPU Temp Limit: {_read_feature('gpu_temperature_limit')}°C")
        else:
            _write_feature("gpu_temperature_limit", value)
            print(f"GPU Temp Limit set to: {_read_feature('gpu_temperature_limit')}°C")
        return 0

    def create_argparser()->argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description='Legion CLI')
        parser.add_argument(
            '--donotexpecthwmon', action='store_true', help='Do not check hwmon dir when not needed', default=False)
        parser.add_argument('--loglevel', type=str,
                            help='Level of log output', choices=loglevels, default='ERROR')

        subcommands = parser.add_subparsers(title='Commands', dest='subcommand')

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

        gtemp_cmd_parser = subcommands.add_parser('gpu-temp-limit', help='Get or set GPU temperature limit')
        gtemp_cmd_parser.add_argument('value', type=int, nargs='?', default=None, help='Temperature in °C (75-87)')
        gtemp_cmd_parser.set_defaults(func=gpu_temp_limit_cmd)

        # LOQ 83SC-specific power controls, surfaced as a separate help section so
        # they are clearly distinguished from the generic upstream-style commands.
        _loq83sc_cmds = [
            "tdp", "cpu-tau", "cpu-crossload", "cpu-temp-limit",
            "gpu-dynamic-boost", "gpu-ctgp", "gpu-total-proc", "gpu-temp-limit",
            "custom-conservation-mode-apply",
        ]
        parser.epilog = (
            "LOQ 83SC custom power controls (available on this build only):\n  "
            + ", ".join(_loq83sc_cmds)
        )

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


else:
    # ── UPSTREAM CODE (any other model) ──
    _upstream_code = base64.b64decode("IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIFBZVEhPTl9BUkdDT01QTEVURV9PSwojIHB5bGludDogZGlzYWJsZT13cm9uZy1pbXBvcnQtb3JkZXIKaW1wb3J0IGFyZ2NvbXBsZXRlCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgbG9nZ2luZwppbXBvcnQgc3lzCmltcG9ydCBvcwojIE1ha2UgaXQgcG9zc2libGUgdG8gcnVuIHdpdGhvdXQgaW5zdGFsbGF0aW9uaW1wb3J0CiMgcHlsaW50OiBkaXNhYmxlPSMgcHlsaW50OiBkaXNhYmxlPXdyb25nLWltcG9ydC1wb3NpdGlvbgpzeXMucGF0aC5pbnNlcnQoMCwgb3MucGF0aC5kaXJuYW1lKF9fZmlsZV9fKSArICIvLi4iKQppbXBvcnQgbGVnaW9uX2xpbnV4LmxlZ2lvbgpmcm9tIGxlZ2lvbl9saW51eC5sZWdpb24gaW1wb3J0IExlZ2lvbk1vZGVsRmFjYWRlCmxvZ2dpbmcuYmFzaWNDb25maWcoKQpsb2cgPSBsb2dnaW5nLmdldExvZ2dlcihsZWdpb25fbGludXgubGVnaW9uLl9fbmFtZV9fKQpsb2dsZXZlbHMgPSBbJ05PVFNFVCcsICdERUJVRycsICdJTkZPJywgJ1dBUk4nLCAnRVJST1InLCAnQ1JJVElDQUwnXQojIHdpbGwgYmUgc2V0IGluIG1haW4gdG8gdXNlciBkZWZpbmVkIGxldmVsIGFmdGVyIHBhcnNpbmcKbG9nLnNldExldmVsKCdFUlJPUicpCgoKY2xhc3MgQ0xJRmVhdHVyZUNvbW1hbmQ6CiAgICBkZWYgX19pbml0X18oc2VsZiwgbmFtZTogc3RyLCBwYXJzZXJfc3ViY29tbWFuZHMsIGNtZF9ncm91cDogbGlzdCwgd3JpdGVhYmxlOiBib29sID0gVHJ1ZSk6CiAgICAgICAgc2VsZi5uYW1lID0gbmFtZQogICAgICAgIHNlbGYubW9kZWwgPSBOb25lCiAgICAgICAgc3RhdHVzX3BhcnNlciA9IHBhcnNlcl9zdWJjb21tYW5kcy5hZGRfcGFyc2VyKAogICAgICAgICAgICBmIntzZWxmLm5hbWV9LXN0YXR1cyIsIGhlbHA9ZidHZXQgY3VycmVudCB2YWx1ZSBmb3Ige3NlbGYubmFtZX0nKQogICAgICAgIHN0YXR1c19wYXJzZXIuc2V0X2RlZmF1bHRzKAogICAgICAgICAgICBmdW5jPWxhbWJkYSBsLCAqYXJncywgKiprd2FyZ3M6IHNlbGYuY29tbWFuZF9zdGF0dXNfY2xpKCoqa3dhcmdzKSkKCiAgICAgICAgaWYgd3JpdGVhYmxlOgogICAgICAgICAgICBlbmFibGVfcGFyc2VyID0gcGFyc2VyX3N1YmNvbW1hbmRzLmFkZF9wYXJzZXIoCiAgICAgICAgICAgICAgICBmIntzZWxmLm5hbWV9LWVuYWJsZSIsIGhlbHA9ZidFbmFibGUge3NlbGYubmFtZX0nKQogICAgICAgICAgICBlbmFibGVfcGFyc2VyLnNldF9kZWZhdWx0cygKICAgICAgICAgICAgICAgIGZ1bmM9bGFtYmRhIGwsICphcmdzLCAqKmt3YXJnczogc2VsZi5jb21tYW5kX2VuYWJsZV9jbGkoKiprd2FyZ3MpKQoKICAgICAgICAgICAgZGlzYWJsZV9wYXJzZXIgPSBwYXJzZXJfc3ViY29tbWFuZHMuYWRkX3BhcnNlcigKICAgICAgICAgICAgICAgIGYie3NlbGYubmFtZX0tZGlzYWJsZSIsIGhlbHA9ZidEaXNhYmxlIHtzZWxmLm5hbWV9JykKICAgICAgICAgICAgZGlzYWJsZV9wYXJzZXIuc2V0X2RlZmF1bHRzKAogICAgICAgICAgICAgICAgZnVuYz1sYW1iZGEgbCwgKmFyZ3MsICoqa3dhcmdzOiBzZWxmLmNvbW1hbmRfZGlzYWJsZV9jbGkoKiprd2FyZ3MpKQoKICAgICAgICBpZiBjbWRfZ3JvdXAgaXMgbm90IE5vbmU6CiAgICAgICAgICAgIGNtZF9ncm91cC5hcHBlbmQoc2VsZikKCiAgICBkZWYgc2V0X21vZGVsKHNlbGYsIG1vZGVsOiBMZWdpb25Nb2RlbEZhY2FkZSk6CiAgICAgICAgc2VsZi5tb2RlbCA9IG1vZGVsCgogICAgZGVmIGNoZWNrX2lmX2V4aXN0KHNlbGYpOgogICAgICAgIGlmIHNlbGYuZXhpc3RzKCk6CiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgcHJpbnQoCiAgICAgICAgICAgICJDb21tYW5kIG5vdCBhdmFpbGFibGUgYmVjYXVzZSBmZWF0dXJlIGlzIG5vdCBhdmFpbGFibGUgb3Iga2VybmVsIG1vZHVsZSBpcyBub3QgbG9hZGVkLiIpCiAgICAgICAgcmV0dXJuIEZhbHNlCgogICAgZGVmIGNvbW1hbmRfc3RhdHVzX2NsaShzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBpZiBzZWxmLmNoZWNrX2lmX2V4aXN0KCk6CiAgICAgICAgICAgIHJldHVybiBzZWxmLmNvbW1hbmRfc3RhdHVzKCkKICAgICAgICByZXR1cm4gLTEwCgogICAgZGVmIGNvbW1hbmRfZW5hYmxlX2NsaShzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBpZiBzZWxmLmNoZWNrX2lmX2V4aXN0KCk6CiAgICAgICAgICAgIHJldHVybiBzZWxmLmNvbW1hbmRfZW5hYmxlKCkKICAgICAgICByZXR1cm4gLTEwCgogICAgZGVmIGNvbW1hbmRfZGlzYWJsZV9jbGkoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgaWYgc2VsZi5jaGVja19pZl9leGlzdCgpOgogICAgICAgICAgICByZXR1cm4gc2VsZi5jb21tYW5kX2Rpc2FibGUoKQogICAgICAgIHJldHVybiAtMTAKCiAgICBkZWYgZXhpc3RzKHNlbGYpIC0+IGJvb2w6CiAgICAgICAgcmV0dXJuIEZhbHNlCgogICAgZGVmIGNvbW1hbmRfc3RhdHVzKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHJldHVybiAwCgogICAgZGVmIGNvbW1hbmRfZW5hYmxlKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHJldHVybiAtMQoKICAgIGRlZiBjb21tYW5kX2Rpc2FibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgcmV0dXJuIC0xCgoKY2xhc3MgTWluaUZhbmN1cnZlRmVhdHVyZUNvbW1hbmQoQ0xJRmVhdHVyZUNvbW1hbmQpOgogICAgZGVmIF9faW5pdF9fKHNlbGYsIHBhcnNlcl9zdWJjb21tYW5kcywgbW9kZWw6IExlZ2lvbk1vZGVsRmFjYWRlLCBjbWRfZ3JvdXA6IGxpc3QpOgogICAgICAgIHN1cGVyKCkuX19pbml0X18oIm1pbmlmYW5jdXJ2ZSIsIHBhcnNlcl9zdWJjb21tYW5kcywgY21kX2dyb3VwKQogICAgICAgIHNlbGYubW9kZWwgPSBtb2RlbAoKICAgIGRlZiBleGlzdHMoc2VsZikgLT4gYm9vbDoKICAgICAgICByZXR1cm4gc2VsZi5tb2RlbC5mYW5jdXJ2ZV9pby5leGlzdHMoKQoKICAgIGRlZiBjb21tYW5kX3N0YXR1cyhzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBwcmludChzZWxmLm1vZGVsLmZhbmN1cnZlX2lvLmdldF9taW5pZmFuY3V2ZSgpKQogICAgICAgIHJldHVybiAwCgogICAgZGVmIGNvbW1hbmRfZW5hYmxlKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHNlbGYubW9kZWwuZmFuY3VydmVfaW8uc2V0X21pbmlmYW5jdXZlKFRydWUpCiAgICAgICAgcmV0dXJuIDAKCiAgICBkZWYgY29tbWFuZF9kaXNhYmxlKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHNlbGYubW9kZWwuZmFuY3VydmVfaW8uc2V0X21pbmlmYW5jdXZlKEZhbHNlKQogICAgICAgIHJldHVybiAwCgoKY2xhc3MgTG9ja0ZhbkNvbnRyb2xsZXJGZWF0dXJlQ29tbWFuZChDTElGZWF0dXJlQ29tbWFuZCk6CiAgICBkZWYgX19pbml0X18oc2VsZiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBtb2RlbDogTGVnaW9uTW9kZWxGYWNhZGUsIGNtZF9ncm91cDogbGlzdCk6CiAgICAgICAgc3VwZXIoKS5fX2luaXRfXygibG9ja2ZhbmNvbnRyb2xsZXIiLCBwYXJzZXJfc3ViY29tbWFuZHMsIGNtZF9ncm91cCkKICAgICAgICBzZWxmLm1vZGVsID0gbW9kZWwKCiAgICBkZWYgZXhpc3RzKHNlbGYpIC0+IGJvb2w6CiAgICAgICAgcmV0dXJuIHNlbGYubW9kZWwubG9ja2ZhbmNvbnRyb2xsZXIuZXhpc3RzKCkKCiAgICBkZWYgY29tbWFuZF9zdGF0dXMoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgcHJpbnQoc2VsZi5tb2RlbC5sb2NrZmFuY29udHJvbGxlci5nZXQoKSkKICAgICAgICByZXR1cm4gMAoKICAgIGRlZiBjb21tYW5kX2VuYWJsZShzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBzZWxmLm1vZGVsLmxvY2tmYW5jb250cm9sbGVyLnNldChUcnVlKQogICAgICAgIHJldHVybiAwCgogICAgZGVmIGNvbW1hbmRfZGlzYWJsZShzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBzZWxmLm1vZGVsLmxvY2tmYW5jb250cm9sbGVyLnNldChGYWxzZSkKICAgICAgICByZXR1cm4gMAoKCmNsYXNzIE1heGltdW1GYW5TcGVlZEZlYXR1cmVDb21tYW5kKENMSUZlYXR1cmVDb21tYW5kKToKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBwYXJzZXJfc3ViY29tbWFuZHMsIG1vZGVsOiBMZWdpb25Nb2RlbEZhY2FkZSwgY21kX2dyb3VwOiBsaXN0KToKICAgICAgICBzdXBlcigpLl9faW5pdF9fKCJtYXhpbXVtZmFuc3BlZWQiLCBwYXJzZXJfc3ViY29tbWFuZHMsIGNtZF9ncm91cCkKICAgICAgICBzZWxmLm1vZGVsID0gbW9kZWwKCiAgICBkZWYgZXhpc3RzKHNlbGYpIC0+IGJvb2w6CiAgICAgICAgcmV0dXJuIHNlbGYubW9kZWwubWF4aW11bV9mYW5zcGVlZC5leGlzdHMoKQoKICAgIGRlZiBjb21tYW5kX3N0YXR1cyhzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBwcmludChzZWxmLm1vZGVsLm1heGltdW1fZmFuc3BlZWQuZ2V0KCkpCiAgICAgICAgcmV0dXJuIDAKCiAgICBkZWYgY29tbWFuZF9lbmFibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC5tYXhpbXVtX2ZhbnNwZWVkLnNldChUcnVlKQogICAgICAgIHJldHVybiAwCgogICAgZGVmIGNvbW1hbmRfZGlzYWJsZShzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBzZWxmLm1vZGVsLm1heGltdW1fZmFuc3BlZWQuc2V0KEZhbHNlKQogICAgICAgIHJldHVybiAwCgoKY2xhc3MgQmF0dGVyeUNvbnNlcnZhdGlvbkZlYXR1cmVDb21tYW5kKENMSUZlYXR1cmVDb21tYW5kKToKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBwYXJzZXJfc3ViY29tbWFuZHMsIG1vZGVsOiBMZWdpb25Nb2RlbEZhY2FkZSwgY21kX2dyb3VwOiBsaXN0KToKICAgICAgICBzdXBlcigpLl9faW5pdF9fKCJiYXR0ZXJ5Y29uc2VydmF0aW9uIiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBjbWRfZ3JvdXApCiAgICAgICAgc2VsZi5tb2RlbCA9IG1vZGVsCgogICAgZGVmIGV4aXN0cyhzZWxmKSAtPiBib29sOgogICAgICAgIHJldHVybiBzZWxmLm1vZGVsLmJhdHRlcnlfY29uc2VydmF0aW9uLmV4aXN0cygpCgogICAgZGVmIGNvbW1hbmRfc3RhdHVzKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHByaW50KHNlbGYubW9kZWwuYmF0dGVyeV9jb25zZXJ2YXRpb24uZ2V0KCkpCiAgICAgICAgcmV0dXJuIDAKCiAgICBkZWYgY29tbWFuZF9lbmFibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC5iYXR0ZXJ5X2NvbnNlcnZhdGlvbi5zZXQoVHJ1ZSkKICAgICAgICByZXR1cm4gMAoKICAgIGRlZiBjb21tYW5kX2Rpc2FibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC5iYXR0ZXJ5X2NvbnNlcnZhdGlvbi5zZXQoRmFsc2UpCiAgICAgICAgcmV0dXJuIDAKCgpjbGFzcyBGbkxvY2tGZWF0dXJlQ29tbWFuZChDTElGZWF0dXJlQ29tbWFuZCk6CiAgICBkZWYgX19pbml0X18oc2VsZiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBtb2RlbDogTGVnaW9uTW9kZWxGYWNhZGUsIGNtZF9ncm91cDogbGlzdCk6CiAgICAgICAgc3VwZXIoKS5fX2luaXRfXygiZm5sb2NrIiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBjbWRfZ3JvdXApCiAgICAgICAgc2VsZi5tb2RlbCA9IG1vZGVsCgogICAgZGVmIGV4aXN0cyhzZWxmKSAtPiBib29sOgogICAgICAgIHJldHVybiBzZWxmLm1vZGVsLmZuX2xvY2suZXhpc3RzKCkKCiAgICBkZWYgY29tbWFuZF9zdGF0dXMoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgcHJpbnQoc2VsZi5tb2RlbC5mbl9sb2NrLmdldCgpKQogICAgICAgIHJldHVybiAwCgogICAgZGVmIGNvbW1hbmRfZW5hYmxlKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHNlbGYubW9kZWwuZm5fbG9jay5zZXQoVHJ1ZSkKICAgICAgICByZXR1cm4gMAoKICAgIGRlZiBjb21tYW5kX2Rpc2FibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC5mbl9sb2NrLnNldChGYWxzZSkKICAgICAgICByZXR1cm4gMAoKCmNsYXNzIFRvdWNocGFkRmVhdHVyZUNvbW1hbmQoQ0xJRmVhdHVyZUNvbW1hbmQpOgogICAgZGVmIF9faW5pdF9fKHNlbGYsIHBhcnNlcl9zdWJjb21tYW5kcywgbW9kZWw6IExlZ2lvbk1vZGVsRmFjYWRlLCBjbWRfZ3JvdXA6IGxpc3QpOgogICAgICAgIHN1cGVyKCkuX19pbml0X18oInRvdWNocGFkIiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBjbWRfZ3JvdXApCiAgICAgICAgc2VsZi5tb2RlbCA9IG1vZGVsCgogICAgZGVmIGV4aXN0cyhzZWxmKSAtPiBib29sOgogICAgICAgIHJldHVybiBzZWxmLm1vZGVsLnRvdWNocGFkLmV4aXN0cygpCgogICAgZGVmIGNvbW1hbmRfc3RhdHVzKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHByaW50KHNlbGYubW9kZWwudG91Y2hwYWQuZ2V0KCkpCiAgICAgICAgcmV0dXJuIDAKCiAgICBkZWYgY29tbWFuZF9lbmFibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC50b3VjaHBhZC5zZXQoVHJ1ZSkKICAgICAgICByZXR1cm4gMAoKICAgIGRlZiBjb21tYW5kX2Rpc2FibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC50b3VjaHBhZC5zZXQoRmFsc2UpCiAgICAgICAgcmV0dXJuIDAKCgpjbGFzcyBDYW1lcmFQb3dlckZlYXR1cmVDb21tYW5kKENMSUZlYXR1cmVDb21tYW5kKToKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBwYXJzZXJfc3ViY29tbWFuZHMsIG1vZGVsOiBMZWdpb25Nb2RlbEZhY2FkZSwgY21kX2dyb3VwOiBsaXN0KToKICAgICAgICBzdXBlcigpLl9faW5pdF9fKCJjYW1lcmEtcG93ZXIiLCBwYXJzZXJfc3ViY29tbWFuZHMsIGNtZF9ncm91cCwgRmFsc2UpCiAgICAgICAgc2VsZi5tb2RlbCA9IG1vZGVsCgogICAgZGVmIGV4aXN0cyhzZWxmKSAtPiBib29sOgogICAgICAgIHJldHVybiBzZWxmLm1vZGVsLmNhbWVyYV9wb3dlci5leGlzdHMoKQoKICAgIGRlZiBjb21tYW5kX3N0YXR1cyhzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBwcmludChzZWxmLm1vZGVsLmNhbWVyYV9wb3dlci5nZXQoKSkKICAgICAgICByZXR1cm4gMAoKCmNsYXNzIE9uUG93ZXJTdXBwbHlGZWF0dXJlQ29tbWFuZChDTElGZWF0dXJlQ29tbWFuZCk6CiAgICBkZWYgX19pbml0X18oc2VsZiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBtb2RlbDogTGVnaW9uTW9kZWxGYWNhZGUsIGNtZF9ncm91cDogbGlzdCk6CiAgICAgICAgc3VwZXIoKS5fX2luaXRfXygib24tcG93ZXItc3VwcGx5IiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBjbWRfZ3JvdXAsIEZhbHNlKQogICAgICAgIHNlbGYubW9kZWwgPSBtb2RlbAoKICAgIGRlZiBleGlzdHMoc2VsZikgLT4gYm9vbDoKICAgICAgICByZXR1cm4gc2VsZi5tb2RlbC5vbl9wb3dlcl9zdXBwbHkuZXhpc3RzKCkKCiAgICBkZWYgY29tbWFuZF9zdGF0dXMoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgcHJpbnQoc2VsZi5tb2RlbC5vbl9wb3dlcl9zdXBwbHkuZ2V0KCkpCiAgICAgICAgcmV0dXJuIDAKCgpjbGFzcyBBbHdheXNPblVzYkNoYXJnaW5nKENMSUZlYXR1cmVDb21tYW5kKToKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBwYXJzZXJfc3ViY29tbWFuZHMsIG1vZGVsOiBMZWdpb25Nb2RlbEZhY2FkZSwgY21kX2dyb3VwOiBsaXN0KToKICAgICAgICBzdXBlcigpLl9faW5pdF9fKCJhbHdheXMtb24tdXNiLWNoYXJnaW5nIiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBjbWRfZ3JvdXApCiAgICAgICAgc2VsZi5tb2RlbCA9IG1vZGVsCgogICAgZGVmIGV4aXN0cyhzZWxmKSAtPiBib29sOgogICAgICAgIHJldHVybiBzZWxmLm1vZGVsLmFsd2F5c19vbl91c2JfY2hhcmdpbmcuZXhpc3RzKCkKCiAgICBkZWYgY29tbWFuZF9zdGF0dXMoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgcHJpbnQoc2VsZi5tb2RlbC5hbHdheXNfb25fdXNiX2NoYXJnaW5nLmdldCgpKQogICAgICAgIHJldHVybiAwCgogICAgZGVmIGNvbW1hbmRfZW5hYmxlKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHNlbGYubW9kZWwuYWx3YXlzX29uX3VzYl9jaGFyZ2luZy5zZXQoVHJ1ZSkKICAgICAgICByZXR1cm4gMAoKICAgIGRlZiBjb21tYW5kX2Rpc2FibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC5hbHdheXNfb25fdXNiX2NoYXJnaW5nLnNldChGYWxzZSkKICAgICAgICByZXR1cm4gMAoKCmNsYXNzIFJhcGlkQ2hhcmdpbmcoQ0xJRmVhdHVyZUNvbW1hbmQpOgogICAgZGVmIF9faW5pdF9fKHNlbGYsIHBhcnNlcl9zdWJjb21tYW5kcywgbW9kZWw6IExlZ2lvbk1vZGVsRmFjYWRlLCBjbWRfZ3JvdXA6IGxpc3QpOgogICAgICAgIHN1cGVyKCkuX19pbml0X18oInJhcGlkLWNoYXJnaW5nIiwgcGFyc2VyX3N1YmNvbW1hbmRzLCBjbWRfZ3JvdXApCiAgICAgICAgc2VsZi5tb2RlbCA9IG1vZGVsCgogICAgZGVmIGV4aXN0cyhzZWxmKSAtPiBib29sOgogICAgICAgIHJldHVybiBzZWxmLm1vZGVsLnJhcGlkX2NoYXJnaW5nLmV4aXN0cygpCgogICAgZGVmIGNvbW1hbmRfc3RhdHVzKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHByaW50KHNlbGYubW9kZWwucmFwaWRfY2hhcmdpbmcuZ2V0KCkpCiAgICAgICAgcmV0dXJuIDAKCiAgICBkZWYgY29tbWFuZF9lbmFibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC5yYXBpZF9jaGFyZ2luZy5zZXQoVHJ1ZSkKICAgICAgICByZXR1cm4gMAoKICAgIGRlZiBjb21tYW5kX2Rpc2FibGUoc2VsZiwgKipfKSAtPiBpbnQ6CiAgICAgICAgc2VsZi5tb2RlbC5yYXBpZF9jaGFyZ2luZy5zZXQoRmFsc2UpCiAgICAgICAgcmV0dXJuIDAKCgpjbGFzcyBIeWJyaWRNb2RlKENMSUZlYXR1cmVDb21tYW5kKToKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBwYXJzZXJfc3ViY29tbWFuZHMsIG1vZGVsOiBMZWdpb25Nb2RlbEZhY2FkZSwgY21kX2dyb3VwOiBsaXN0KToKICAgICAgICBzdXBlcigpLl9faW5pdF9fKCJoeWJyaWQtbW9kZSIsIHBhcnNlcl9zdWJjb21tYW5kcywgY21kX2dyb3VwKQogICAgICAgIHNlbGYubW9kZWwgPSBtb2RlbAoKICAgIGRlZiBleGlzdHMoc2VsZikgLT4gYm9vbDoKICAgICAgICByZXR1cm4gc2VsZi5tb2RlbC5nc3luYy5leGlzdHMoKQoKICAgIGRlZiBjb21tYW5kX3N0YXR1cyhzZWxmLCAqKl8pIC0+IGludDoKICAgICAgICBwcmludCgiVGhpcyBpcyB0aGUgY3VycmVudCBzdGF0ZS4gQ2hhbmdpbmcgaXQgYnkgc2V0dGluZyBpdCB3aWxsIGFwcGx5IG9ubHkgYWZ0ZXIgYSByZWJvb3QuIikKICAgICAgICBwcmludChzZWxmLm1vZGVsLmdzeW5jLmdldCgpKQogICAgICAgIHJldHVybiAwCgogICAgZGVmIGNvbW1hbmRfZW5hYmxlKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHByaW50KCJDaGFuZ2VzIHdpbGwgb25seSBhcHBseSBhZnRlciBhIHJlYm9vdC4iKQogICAgICAgIHNlbGYubW9kZWwuZ3N5bmMuc2V0KFRydWUpCiAgICAgICAgcmV0dXJuIDAKCiAgICBkZWYgY29tbWFuZF9kaXNhYmxlKHNlbGYsICoqXykgLT4gaW50OgogICAgICAgIHByaW50KCJDaGFuZ2VzIHdpbGwgb25seSBhcHBseSBhZnRlciBhIHJlYm9vdC4iKQogICAgICAgIHNlbGYubW9kZWwuZ3N5bmMuc2V0KEZhbHNlKQogICAgICAgIHJldHVybiAwCgoKZGVmIGF1dG9jb21wbGV0ZV9pbnN0YWxsKF8sICoqX18pIC0+IGludDoKICAgIGNtZCA9IGYiZXZhbCBcIiQocmVnaXN0ZXItcHl0aG9uLWFyZ2NvbXBsZXRlIHtfX2ZpbGVfX30pXCIiCiAgICBwcmludCgiUExFQVNFIFJVTiBUSEUgQ09NTUFORDoiKQogICAgcHJpbnQoY21kKQoKCmRlZiBmYW5jdXJ2ZV93cml0ZV9wcmVzZXRfdG9faHcobGVnaW9uOiBMZWdpb25Nb2RlbEZhY2FkZSwgcHJlc2V0bmFtZTogc3RyLCAqKl8pIC0+IGludDoKICAgICMgcHlsaW50OiBkaXNhYmxlPXVudXNlZC1hcmd1bWVudAogICAgbGVnaW9uLmZhbmN1cnZlX3dyaXRlX3ByZXNldF90b19odyhwcmVzZXRuYW1lLCB3cml0ZV9taW5pZmFuY3VydmU9VHJ1ZSkKICAgIHByaW50KGYnU3VjY2Vzc2Z1bGx5IHdyb3RlIHByZXNldCB7cHJlc2V0bmFtZX0gdG8gaGFyZHdhcmUnKQogICAgcmV0dXJuIDAKCgpkZWYgZmFuY3VydmVfd3JpdGVfaHdfdG9fcHJlc2V0KGxlZ2lvbjogTGVnaW9uTW9kZWxGYWNhZGUsIHByZXNldG5hbWU6IHN0ciwgKipfKSAtPiBpbnQ6CiAgICAjIHB5bGludDogZGlzYWJsZT11bnVzZWQtYXJndW1lbnQKICAgIGxlZ2lvbi5mYW5jdXJ2ZV93cml0ZV9od190b19wcmVzZXQocHJlc2V0bmFtZSkKICAgIHByaW50KGYnU3VjY2Vzc2Z1bGx5IHdyb3RlIGhhcmR3YXJlIHRvIHByZXNldCB7cHJlc2V0bmFtZX0nKQogICAgcmV0dXJuIDAKCgpkZWYgZmFuY3VydmVfd3JpdGVfZmlsZV90b19odyhsZWdpb246IExlZ2lvbk1vZGVsRmFjYWRlLCBmaWxlbmFtZTogc3RyLCAqKl8pIC0+IGludDoKICAgICMgcHlsaW50OiBkaXNhYmxlPXVudXNlZC1hcmd1bWVudAogICAgbGVnaW9uLmZhbmN1cnZlX3dyaXRlX2ZpbGVfdG9faHcoZmlsZW5hbWUsIHdyaXRlX21pbmlmYW5jdXJ2ZT1UcnVlKQogICAgcHJpbnQoZidTdWNjZXNzZnVsbHkgd3JvdGUgZmFuIGN1cnZlIGZyb20gZmlsZSB7ZmlsZW5hbWV9IHRvIGhhcmR3YXJlJykKICAgIHJldHVybiAwCgoKZGVmIGZhbmN1cnZlX3dyaXRlX2h3X3RvX2ZpbGUobGVnaW9uOiBMZWdpb25Nb2RlbEZhY2FkZSwgZmlsZW5hbWU6IHN0ciwgKipfKSAtPiBpbnQ6CiAgICAjIHB5bGludDogZGlzYWJsZT11bnVzZWQtYXJndW1lbnQKICAgIGxlZ2lvbi5mYW5jdXJ2ZV93cml0ZV9od190b19maWxlKGZpbGVuYW1lKQogICAgcHJpbnQoZidTdWNjZXNzZnVsbHkgd3JvdGUgZmFuIGN1cnZlIGZyb20gaGFyZHdhcmUgdG8gZmlsZSB7ZmlsZW5hbWV9JykKICAgIHJldHVybiAwCgoKZGVmIGZhbmN1cnZlX3dyaXRlX3ByZXNldF9mb3JfY3VycmVudF9wcm9maWxlKGxlZ2lvbjogTGVnaW9uTW9kZWxGYWNhZGUsICoqXykgLT4gaW50OgogICAgIyBweWxpbnQ6IGRpc2FibGU9dW51c2VkLWFyZ3VtZW50CiAgICBsZWdpb24uZmFuY3VydmVfd3JpdGVfcHJlc2V0X2Zvcl9jdXJyZW50X3Byb2ZpbGUod3JpdGVfbWluaWZhbmN1cnZlPVRydWUpCiAgICByZXR1cm4gMAoKCmRlZiBjb25zZXJ2YXRpb25fYXBwbHlfbW9kZV9mb3JfY3VycmVudF9iYXR0ZXJ5X2NhcGFjaXR5KGxlZ2lvbjogTGVnaW9uTW9kZWxGYWNhZGUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGxvd2VybGltaXQ9NTAsIHVwcGVybGltaXQ9NjAsICoqXykgLT4gaW50OgogICAgcHJpbnQobGVnaW9uLmNvbnNlcnZhdGlvbl9hcHBseV9tb2RlX2Zvcl9jdXJyZW50X2JhdHRlcnlfY2FwYWNpdHkoCiAgICAgICAgbG93ZXJsaW1pdCwgdXBwZXJsaW1pdCkpCiAgICByZXR1cm4gMAoKCmRlZiBtb25pdG9yKGxlZ2lvbjogTGVnaW9uTW9kZWxGYWNhZGUsIHBlcmlvZD1Ob25lLCAqKl8pIC0+IGludDoKICAgIHByaW50KCJTdGFydGluZyBtb25pdG9yaW5nOiIpCiAgICBsZWdpb24ucnVuX21vbml0b3JzKHBlcmlvZF9zPXBlcmlvZCkKICAgIHJldHVybiAwCgoKZGVmIHNldF9mZWF0dXJlKGxlZ2lvbjogTGVnaW9uTW9kZWxGYWNhZGUsIG5hbWUsIHZhbHVlcywgKipfKSAtPiBpbnQ6CiAgICBsb2cuc2V0TGV2ZWwoJ0lORk8nKQogICAgaWYgbGVnaW9uLnNldF9mZWF0dXJlX3RvX3N0cl92YWx1ZShuYW1lLCB2YWx1ZXMpOgogICAgICAgIHJldHVybiAwCiAgICBwcmludCgiRmVhdHVyZSBub3QgZm91bmQuIikKICAgIGZvciBmZWF0IGluIGxlZ2lvbi5nZXRfYWxsX2ZlYXR1cmVzKCk6CiAgICAgICAgcHJpbnQoZmVhdCkKICAgIHJldHVybiAtMgoKZGVmIGNyZWF0ZV9hcmdwYXJzZXIoKS0+YXJncGFyc2UuQXJndW1lbnRQYXJzZXI6CiAgICBwYXJzZXIgPSBhcmdwYXJzZS5Bcmd1bWVudFBhcnNlcihkZXNjcmlwdGlvbj0nTGVnaW9uIENMSScpCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KAogICAgICAgICctLWRvbm90ZXhwZWN0aHdtb24nLCBhY3Rpb249J3N0b3JlX3RydWUnLCBoZWxwPSdEbyBub3QgY2hlY2sgaHdtb24gZGlyIHdoZW4gbm90IG5lZWRlZCcsIGRlZmF1bHQ9RmFsc2UpCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCctLWxvZ2xldmVsJywgdHlwZT1zdHIsCiAgICAgICAgICAgICAgICAgICAgICAgIGhlbHA9J0xldmVsIG9mIGxvZyBvdXRwdXQnLCBjaG9pY2VzPWxvZ2xldmVscywgZGVmYXVsdD0nRVJST1InKQoKICAgIHN1YmNvbW1hbmRzID0gcGFyc2VyLmFkZF9zdWJwYXJzZXJzKHRpdGxlPSdzdWJjb21tYW5kcycsIGRlc3Q9J3N1YmNvbW1hbmQnKQoKICAgIGF1dG9jb21wbGV0ZV9pbnN0YWxsX3BhcnNlciA9IHN1YmNvbW1hbmRzLmFkZF9wYXJzZXIoCiAgICAgICAgJ2F1dG9jb21wbGV0ZS1pbnN0YWxsJywgaGVscD0nSW5zdGFsbCBhdXRvY29tcGxldGlvbiBpbiBzaGVsbCBmb3IgdGhpcyB0b29sJykKICAgIGF1dG9jb21wbGV0ZV9pbnN0YWxsX3BhcnNlci5zZXRfZGVmYXVsdHMoZnVuYz1hdXRvY29tcGxldGVfaW5zdGFsbCkKCiAgICBwcmVzZXRfdG9faHdfcGFyc2VyID0gc3ViY29tbWFuZHMuYWRkX3BhcnNlcigKICAgICAgICAnZmFuY3VydmUtd3JpdGUtcHJlc2V0LXRvLWh3JywgaGVscD0nV3JpdGUgZmFuIGN1cnZlIGZyb20gcHJlc2V0IHRvIGhhcmR3YXJlJykKICAgIHByZXNldF90b19od19wYXJzZXIuYWRkX2FyZ3VtZW50KAogICAgICAgICdwcmVzZXRuYW1lJywgdHlwZT1zdHIsIGhlbHA9J05hbWUgb2YgdGhlIHByZXNldCcpCiAgICBwcmVzZXRfdG9faHdfcGFyc2VyLmFkZF9hcmd1bWVudCgKICAgICAgICAnLS1wcmVzZXQtZGlyJywgdHlwZT1zdHIsIGhlbHA9J1BhdGggb2YgdGhlIGRpcmVjdG9yeSB3aXRoIHByZXNldHMnKQogICAgcHJlc2V0X3RvX2h3X3BhcnNlci5zZXRfZGVmYXVsdHMoZnVuYz1mYW5jdXJ2ZV93cml0ZV9wcmVzZXRfdG9faHcpCgogICAgaHdfdG9fcHJlc2V0X3BhcnNlciA9IHN1YmNvbW1hbmRzLmFkZF9wYXJzZXIoCiAgICAgICAgJ2ZhbmN1cnZlLXdyaXRlLWh3LXRvLXByZXNldCcsIGhlbHA9J1dyaXRlIGZhbiBjdXJ2ZSBmcm9tIGhhcmR3YXJlIHRvIHByZXNldCcpCiAgICBod190b19wcmVzZXRfcGFyc2VyLmFkZF9hcmd1bWVudCgKICAgICAgICAncHJlc2V0bmFtZScsIHR5cGU9c3RyLCBoZWxwPSdOYW1lIG9mIHRoZSBwcmVzZXQnKQogICAgaHdfdG9fcHJlc2V0X3BhcnNlci5hZGRfYXJndW1lbnQoCiAgICAgICAgJy0tcHJlc2V0LWRpcicsIHR5cGU9c3RyLCBoZWxwPSdQYXRoIG9mIHRoZSBkaXJlY3Rvcnkgd2l0aCBwcmVzZXRzJykKICAgIGh3X3RvX3ByZXNldF9wYXJzZXIuc2V0X2RlZmF1bHRzKGZ1bmM9ZmFuY3VydmVfd3JpdGVfaHdfdG9fcHJlc2V0KQoKICAgIGZpbGVfdG9faHdfcGFyc2VyID0gc3ViY29tbWFuZHMuYWRkX3BhcnNlcigKICAgICAgICAnZmFuY3VydmUtd3JpdGUtZmlsZS10by1odycsIGhlbHA9J1dyaXRlIGZhbiBjdXJ2ZSBmcm9tIGZpbGUgdG8gaGFyZHdhcmUnKQogICAgZmlsZV90b19od19wYXJzZXIuYWRkX2FyZ3VtZW50KAogICAgICAgICdmaWxlbmFtZScsIHR5cGU9c3RyLCBoZWxwPSdOYW1lIG9mIHRoZSBmaWxlJykKICAgIGZpbGVfdG9faHdfcGFyc2VyLnNldF9kZWZhdWx0cyhmdW5jPWZhbmN1cnZlX3dyaXRlX2ZpbGVfdG9faHcpCgogICAgaHdfdG9fZmlsZV9wYXJzZXIgPSBzdWJjb21tYW5kcy5hZGRfcGFyc2VyKAogICAgICAgICdmYW5jdXJ2ZS13cml0ZS1ody10by1maWxlJywgaGVscD0nV3JpdGUgZmFuIGN1cnZlIGZyb20gaGFyZHdhcmUgdG8gZmlsZScpCiAgICBod190b19maWxlX3BhcnNlci5hZGRfYXJndW1lbnQoCiAgICAgICAgJ2ZpbGVuYW1lJywgdHlwZT1zdHIsIGhlbHA9J05hbWUgb2YgdGhlIGZpbGUnKQogICAgaHdfdG9fZmlsZV9wYXJzZXIuc2V0X2RlZmF1bHRzKGZ1bmM9ZmFuY3VydmVfd3JpdGVfaHdfdG9fZmlsZSkKCiAgICBod190b19maWxlX3BhcnNlciA9IHN1YmNvbW1hbmRzLmFkZF9wYXJzZXIoCiAgICAgICAgJ2ZhbmN1cnZlLXdyaXRlLWN1cnJlbnQtcHJlc2V0LXRvLWh3JywKICAgICAgICBoZWxwPSdXcml0ZSBmYW4gY3VydmUgZm9yIHRoZSBjdXJyZW50IHByb2ZpbGUgKHBvd2VyIG1vZGUsIHBvd2VyIHN1cHBseSBzdGF0dXMpIHRvIGhhcmR3YXJlJykKICAgIGh3X3RvX2ZpbGVfcGFyc2VyLnNldF9kZWZhdWx0cygKICAgICAgICBmdW5jPWZhbmN1cnZlX3dyaXRlX3ByZXNldF9mb3JfY3VycmVudF9wcm9maWxlKQoKICAgIGN1c3RvbV9jb25zZXJ2YXRpb25fbW9kZSA9IHN1YmNvbW1hbmRzLmFkZF9wYXJzZXIoCiAgICAgICAgJ2N1c3RvbS1jb25zZXJ2YXRpb24tbW9kZS1hcHBseScsIGhlbHA9J1R1cm4gY29uc2VydmF0aW9uIG1vZGUgb24gb3Igb2ZmIGRlcGVuZGluZyBvbiBiYXR0ZXJ5IGxldmVsJykKICAgIGN1c3RvbV9jb25zZXJ2YXRpb25fbW9kZS5hZGRfYXJndW1lbnQoCiAgICAgICAgJ2xvd2VybGltaXQnLCB0eXBlPWludCwgaGVscD0nTGltaXQgd2hlbiBjb25zZXJ2YXRpb24gbW9kZSBzaG91bGQgYmUgdHVybmVkIG9mZiwgZS5nLiA2MCcsIGRlZmF1bHQ9NjEpCiAgICBjdXN0b21fY29uc2VydmF0aW9uX21vZGUuYWRkX2FyZ3VtZW50KAogICAgICAgICd1cHBlcmxpbWl0JywgdHlwZT1pbnQsIGhlbHA9J0xpbWl0IHdoZW4gY29uc2VydmF0aW9uIG1vZGUgc2hvdWxkIGJlIHR1cm5lZCBvbiwgZS5nLiA4MCcsIGRlZmF1bHQ9ODEpCiAgICBjdXN0b21fY29uc2VydmF0aW9uX21vZGUuc2V0X2RlZmF1bHRzKAogICAgICAgIGZ1bmM9Y29uc2VydmF0aW9uX2FwcGx5X21vZGVfZm9yX2N1cnJlbnRfYmF0dGVyeV9jYXBhY2l0eSkKCiAgICBtb25pdG9yX2NtZCA9IHN1YmNvbW1hbmRzLmFkZF9wYXJzZXIoCiAgICAgICAgJ21vbml0b3InLCBoZWxwPSdSdW4gbW9uaXRvcnMgd2l0aCBub3RpZmljYXRpb25zJykKICAgIG1vbml0b3JfY21kLmFkZF9hcmd1bWVudCgKICAgICAgICAncGVyaW9kJywgdHlwZT1pbnQsIGhlbHA9J01vbml0b3JpbmcgcGVyaW9kIGluIHNlY29uZHMnLCBkZWZhdWx0PTYwKQogICAgbW9uaXRvcl9jbWQuc2V0X2RlZmF1bHRzKAogICAgICAgIGZ1bmM9bW9uaXRvcikKCiAgICBzZXRfZmVhdHVyZV9jbWQgPSBzdWJjb21tYW5kcy5hZGRfcGFyc2VyKAogICAgICAgICdzZXQtZmVhdHVyZScsIGhlbHA9J1NldCBmZWF0dXJlJykKICAgIHNldF9mZWF0dXJlX2NtZC5hZGRfYXJndW1lbnQoCiAgICAgICAgJ25hbWUnLCB0eXBlPXN0ciwgaGVscD0nTmFtZSBvZiBmZWF0dXJlJykKICAgIHNldF9mZWF0dXJlX2NtZC5hZGRfYXJndW1lbnQoCiAgICAgICAgJ3ZhbHVlcycsIHR5cGU9c3RyLCBoZWxwPSdWYWx1ZSBvZiBmZWF0dXJlJywgbmFyZ3M9JysnKQogICAgc2V0X2ZlYXR1cmVfY21kLnNldF9kZWZhdWx0cygKICAgICAgICBmdW5jPXNldF9mZWF0dXJlKQoKICAgIGJvb3Rsb2dvX3BhcnNlciA9IHN1YmNvbW1hbmRzLmFkZF9wYXJzZXIoJ2Jvb3QtbG9nbycsIGhlbHA9IkN1c3RvbSBCb290IExvZ28iKQogICAgYm9vdGxvZ29fc3ViID0gYm9vdGxvZ29fcGFyc2VyLmFkZF9zdWJwYXJzZXJzKGRlc3Q9J2Jvb3Rsb2dvX2NtZCcpCiAgICBlbmFibGVfcGFyc2VyID0gYm9vdGxvZ29fc3ViLmFkZF9wYXJzZXIoJ2VuYWJsZScsIGhlbHA9J1NldCBCb290IExvZ28nKQogICAgZW5hYmxlX3BhcnNlci5hZGRfYXJndW1lbnQoJ2ltYWdlX3BhdGgnLCB0eXBlPXN0ciwgaGVscD0nUGF0aCB0byB0aGUgaW1hZ2UgdG8gYmUgdXNlZCcpCiAgICBlbmFibGVfcGFyc2VyLnNldF9kZWZhdWx0cyhmdW5jPWJvb3RfbG9nb19lbmFibGUpCiAgICByZXN0b3JlX3BhcnNlciA9IGJvb3Rsb2dvX3N1Yi5hZGRfcGFyc2VyKCdyZXN0b3JlJywgaGVscD0nUmVzdG9yZSBtb2RpZmllZCBib290IGxvZ28nKQogICAgcmVzdG9yZV9wYXJzZXIuc2V0X2RlZmF1bHRzKGZ1bmM9Ym9vdF9sb2dvX3Jlc3RvcmUpCiAgICBzdGF0dXNfcGFyc2VyID0gYm9vdGxvZ29fc3ViLmFkZF9wYXJzZXIoJ3N0YXR1cycsIGhlbHA9J1ZpZXcgc3RhdHVzJykKICAgIHN0YXR1c19wYXJzZXIuc2V0X2RlZmF1bHRzKGZ1bmM9Ym9vdF9sb2dvX3N0YXR1cykKCiAgICByZXR1cm4gcGFyc2VyLCBzdWJjb21tYW5kcwoKZGVmIGJvb3RfbG9nb19lbmFibGUobGVnaW9uOiBMZWdpb25Nb2RlbEZhY2FkZSwgaW1hZ2VfcGF0aDogc3RyLCAqKmt3YXJncykgLT4gaW50OiAgIyBweWxpbnQ6IGRpc2FibGU9dW51c2VkLWFyZ3VtZW50CiAgICB0cnk6CiAgICAgICAgbGVnaW9uLmVuYWJsZV9ib290X2xvZ28oaW1hZ2VfcGF0aCkKICAgICAgICBwcmludCgiQm9vdCBMb2dvIGVuYWJsZWQuIikKICAgICAgICByZXR1cm4gMAogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOiAgIyBweWxpbnQ6IGRpc2FibGU9YnJvYWQtZXhjZXB0aW9uLWNhdWdodAogICAgICAgIHByaW50KGYiRXJyb3IgZW5hYmxpbmcgQm9vdCBMb2dvOiB7ZX0iKQogICAgICAgIHJldHVybiAxCgpkZWYgYm9vdF9sb2dvX3Jlc3RvcmUobGVnaW9uOiBMZWdpb25Nb2RlbEZhY2FkZSwgKiprd2FyZ3MpIC0+IGludDogICMgcHlsaW50OiBkaXNhYmxlPXVudXNlZC1hcmd1bWVudAogICAgdHJ5OgogICAgICAgIGxlZ2lvbi5yZXN0b3JlX2Jvb3RfbG9nbygpCiAgICAgICAgcHJpbnQoIkJvb3QgTG9nbyByZXN0b3JlZC4iKQogICAgICAgIHJldHVybiAwCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6ICAjIHB5bGludDogZGlzYWJsZT1icm9hZC1leGNlcHRpb24tY2F1Z2h0CiAgICAgICAgcHJpbnQoZiJFcnJvciByZXN0b3JpbmcgYm9vdCBsb2dvOiB7ZX0iKQogICAgICAgIHJldHVybiAxCgpkZWYgYm9vdF9sb2dvX3N0YXR1cyhsZWdpb246IExlZ2lvbk1vZGVsRmFjYWRlLCAqKmt3YXJncykgLT4gaW50OiAgIyBweWxpbnQ6IGRpc2FibGU9dW51c2VkLWFyZ3VtZW50CiAgICBpc19vbiwgdywgaCA9IGxlZ2lvbi5nZXRfYm9vdF9sb2dvX3N0YXR1cygpCiAgICBwcmludChmIkN1cnJlbnQgQm9vdCBMb2dvIHN0YXR1czogeydPTicgaWYgaXNfb24gZWxzZSAnT0ZGJ307IFJlcXVpcmVkIGltYWdlIGRpbWVuc2lvbnM6IHt3fSB4IHtofSIpCiAgICByZXR1cm4gMAoKZGVmIG1haW4oKToKICAgIHBhcnNlciwgc3ViY29tbWFuZHMgPSBjcmVhdGVfYXJncGFyc2VyKCkKCiAgICBjbWRfZ3JvdXAgPSBbXQogICAgTWluaUZhbmN1cnZlRmVhdHVyZUNvbW1hbmQoc3ViY29tbWFuZHMsIE5vbmUsIGNtZF9ncm91cCkKICAgIExvY2tGYW5Db250cm9sbGVyRmVhdHVyZUNvbW1hbmQoc3ViY29tbWFuZHMsIE5vbmUsIGNtZF9ncm91cCkKICAgIE1heGltdW1GYW5TcGVlZEZlYXR1cmVDb21tYW5kKHN1YmNvbW1hbmRzLCBOb25lLCBjbWRfZ3JvdXApCiAgICBCYXR0ZXJ5Q29uc2VydmF0aW9uRmVhdHVyZUNvbW1hbmQoc3ViY29tbWFuZHMsIE5vbmUsIGNtZF9ncm91cCkKICAgIEZuTG9ja0ZlYXR1cmVDb21tYW5kKHN1YmNvbW1hbmRzLCBOb25lLCBjbWRfZ3JvdXApCiAgICBUb3VjaHBhZEZlYXR1cmVDb21tYW5kKHN1YmNvbW1hbmRzLCBOb25lLCBjbWRfZ3JvdXApCiAgICBDYW1lcmFQb3dlckZlYXR1cmVDb21tYW5kKHN1YmNvbW1hbmRzLCBOb25lLCBjbWRfZ3JvdXApCiAgICBPblBvd2VyU3VwcGx5RmVhdHVyZUNvbW1hbmQoc3ViY29tbWFuZHMsIE5vbmUsIGNtZF9ncm91cCkKICAgIEFsd2F5c09uVXNiQ2hhcmdpbmcoc3ViY29tbWFuZHMsIE5vbmUsIGNtZF9ncm91cCkKICAgIFJhcGlkQ2hhcmdpbmcoc3ViY29tbWFuZHMsIE5vbmUsIGNtZF9ncm91cCkKICAgIEh5YnJpZE1vZGUoc3ViY29tbWFuZHMsIE5vbmUsIGNtZF9ncm91cCkKCiAgICAjIG9ubHkgYWRkIGF1dG9jb21wbGV0aW9uIGlmIHBhY2thZ2UgaXMgaW5zdGFsbGVkCiAgICBhcmdjb21wbGV0ZS5hdXRvY29tcGxldGUocGFyc2VyKQoKICAgIGFyZ3MgPSBwYXJzZXIucGFyc2VfYXJncygpCiAgICBsb2cuc2V0TGV2ZWwoYXJncy5sb2dsZXZlbCkKCiAgICBpZiBhcmdzLnN1YmNvbW1hbmQgaXMgTm9uZToKICAgICAgICBwYXJzZXIucHJpbnRfaGVscCgpCiAgICBlbHNlOgogICAgICAgIGxlZ2lvbiA9IExlZ2lvbk1vZGVsRmFjYWRlKGV4cGVjdF9od21vbj1ub3QgYXJncy5kb25vdGV4cGVjdGh3bW9uKQogICAgICAgIGZvciBjbWQgaW4gY21kX2dyb3VwOgogICAgICAgICAgICBjbWQuc2V0X21vZGVsKGxlZ2lvbikKICAgICAgICAjIHNldCBnbG9iYWwgb3B0aW9ucwogICAgICAgIGlmICJwcmVzZXRfZGlyIiBpbiBhcmdzIGFuZCBhcmdzLnByZXNldF9kaXIgaXMgbm90IE5vbmU6CiAgICAgICAgICAgIGxlZ2lvbi5zZXRfcHJlc2V0X2ZvbGRlcihhcmdzLnByZXNldF9kaXIpCgogICAgICAgIGFyZ3MuZnVuYyhsZWdpb24sICoqdmFycyhhcmdzKSkKCgppZiBfX25hbWVfXyA9PSAnX19tYWluX18nOgogICAgbWFpbigpCg==")
    exec(compile(_upstream_code, __file__, "exec"))
