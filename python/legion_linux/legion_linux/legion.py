# pylint: disable=too-many-lines
import os
import glob
from dataclasses import asdict, dataclass
import shutil
import time
from typing import Callable, List, Optional, Tuple, Dict
from pathlib import Path
import logging
import subprocess
import yaml
# import jsonrpyc
# import inotify.adapters


log = logging.getLogger(__name__)


DEFAULT_ENCODING = "utf8"
DEFAULT_CONFIG_DIR = "/etc/legion_linux"
LEGION_SYS_BASEPATH = '/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00'
IDEAPAD_SYS_BASEPATH = '/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00'


def is_root_user():
    return os.geteuid() == 0

def get_dmesg(only_tail=False, filter_log=True):
    try:
        if filter_log:
            cmd = 'dmesg | grep legion | tail -n 20' if only_tail else 'dmesg | grep legion'
        else:
            cmd = 'dmesg | tail -n 20' if only_tail else 'dmesg'
        with subprocess.Popen(['bash', '-c', cmd], stdout=subprocess.PIPE) as process:
            out, _ = process.communicate(timeout=1)
            out_str = out.decode(DEFAULT_ENCODING)
            return out_str
    except OSError as ex:
        log.error(ex)
        return str(ex)


@dataclass(order=True)
class FanCurveEntry:
    fan1_speed: float # fan speed in rpm
    fan2_speed: float # fan speed in rpm
    cpu_lower_temp: int
    cpu_upper_temp: int
    gpu_lower_temp: int
    gpu_upper_temp: int
    ic_lower_temp: int
    ic_upper_temp: int
    acceleration: int
    deceleration: int


class Serializable:
    def __init__(self) -> None:
        pass

    def to_yaml(self):
        raise NotImplementedError()

    @classmethod
    def from_yaml(cls, yaml_str:str):
        raise NotImplementedError()

    def save_to_file(self, filename, create_dir=True):
        name = type(self).__name__
        if create_dir:
            directory = Path(filename).parent.resolve()
            log.info("Create directory %s for presets", directory)
            Path(directory).mkdir(parents=True, exist_ok=True)
        log.info("Trying to save %s to %s", name, filename)
        with open(filename, 'w', encoding=DEFAULT_ENCODING) as filepointer:
            filepointer.write(self.to_yaml())
        log.info("Saved %s to %s", name, filename)

    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'r', encoding=DEFAULT_ENCODING) as filepointer:
            return cls.from_yaml(filepointer.read())


@dataclass
class FanCurve(Serializable):
    name: str
    entries: List[FanCurveEntry]
    enable_minifancurve: bool = True

    def to_yaml(self):
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str):
        data = yaml.load(yaml_str, Loader=yaml.SafeLoader)
        name = data['name']
        entries = [FanCurveEntry(**entry) for entry in data['entries']]
        enable_minifancurve = bool(
            data['enable_minifancurve']) if 'enable_minifancurve' in data else True
        fan_curve = cls(name, entries, enable_minifancurve)
        return fan_curve


# pylint: disable=too-few-public-methods


class NamedValue:
    value: str
    name: str

    def __init__(self, value, name):
        self.value = value
        self.name = name


def write_file_with_legion_cli(name, values):
    cmd_list = ['pkexec', 'legion_cli', 'set-feature', name]
    cmd_list = cmd_list + [str(val) for val in values]
    log.info('FileFeature %s execute "%s"', name, cmd_list)
    out_str = ""
    err_str = ""
    try:
        with subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            stdout, stderr = process.communicate(timeout=None)
            out_str = stdout.decode(DEFAULT_ENCODING)
            err_str = stderr.decode(DEFAULT_ENCODING)
            returncode = process.returncode
            log.info('FileFeature %s executed with code %d: %s; %s',
                     name, returncode, out_str, err_str)
    except IOError as err:
        log.error('FileFeature %s executed with error %s and out %s and err %s', name, str(
            err), out_str, err_str)
        log.error(get_dmesg(only_tail=True, filter_log=False))
        raise err

# def write_file_with_legion_cli_rpc(name, value):


class Feature:
    features: List['FileFeature'] = []
    default_use_legion_cli_to_write: bool = False

    use_legion_cli_to_write: bool

    def __init__(self) -> None:
        Feature.features.append(self)
        self.use_legion_cli_to_write = Feature.default_use_legion_cli_to_write
        self.callbacks = []

    def set_str_value(self, value: str):
        pass

    def set_str_values(self, values: List[str]):
        self.set_str_value(values[0])

    def name(self):
        return type(self).__name__

    def add_callback(self, callback:Callable[[any], None]):
        self.callbacks.append(callback)

    def _notify(self):
        log.info("Notifying subscribers of change")
        for func in self.callbacks:
            func(self)

    def exists(self):
        return True

    def get_values(self) -> List[NamedValue]:
        return []

    @staticmethod
    def set_feature_to_str_value(name: str, values: List[str]):
        for feat in Feature.features:
            if feat.name() == name:
                if len(values) == 1:
                    feat.set_str_value(values[0])
                else:
                    feat.set_str_values(values)
                return True
        return False

    @staticmethod
    def set_feature_to_value(name: str, value):
        for feat in Feature.features:
            if feat.name() == name:
                feat.set(value)
                return True
        return False


class BoolSettingFeature(Feature):

    def __init__(self, name) -> None:
        super().__init__()
        self._name = name
        self.value = True

    def name(self):
        return self._name

    def set(self, value: bool):
        log.info('Setting feature %s to %d', self.name(), value)
        self.value = value
        self._notify()

    def get(self) -> bool:
        return self.value

class EnumSettingFeature(Feature):
    def __init__(self, name, value, all_values:List[NamedValue]) -> None:
        super().__init__()
        self._name = name
        self._all_values = all_values
        self.value = value

    def name(self):
        return self._name

    def get_values(self) -> List[NamedValue]:
        return self._all_values

    def set(self, value: str):
        log.info('Setting feature %s to %s', self.name(), str(value))
        if value in [ nv.value for nv in self._all_values]:
            self.value = value
            self._notify()
        else:
            log.error("Setting invalid value %s", value)
            raise ValueError(f"Invalid value {value}")

    def get(self) -> bool:
        return self.value


class FileFeature(Feature):
    pattern: str
    filename: str

    def __init__(self, pattern):
        super().__init__()
        self.pattern = pattern
        self.filename = FileFeature._find_by_file_pattern(pattern)
        log.info('Feature %s with pattern %s and path %s',
                 self.name(), pattern, self.filename)
        if not self.exists():
            log.warning('Feature %s does not exist. exits: %d',
                        self.name(), self.exists())

    def _read_file_str(self, file_path) -> str:
        log.info('Feature %s reading', self.name())
        if not self.exists():
            log.warning('Feature %s reading from non existing', self.name())
        try:
            with open(file_path, "r", encoding=DEFAULT_ENCODING) as filepointer:
                out = str(filepointer.read()).strip()
            log.info('Feature %s reading: %s', self.name(), str(out))
            return out
        except IOError as err:
            log.error('Feature %s reading error %s', self.name(), str(err))
            log.error(get_dmesg(only_tail=True, filter_log=False))
            raise err

    def _read_file_int(self, file_path) -> int:
        return int(self._read_file_str(file_path))

    def set_str_value(self, value: str):
        return self._write_file(self.filename, value)

    def _write_file(self, file_path, value):
        if self.use_legion_cli_to_write:
            write_file_with_legion_cli(self.name(), [value])
            return
        log.info('Feature %s writing: %s', self.name(), str(value))
        if not self.exists():
            log.error('Feature %s writing to non existing', self.name())
        try:
            with open(file_path, "w", encoding=DEFAULT_ENCODING) as filepointer:
                filepointer.write(str(value))
        except IOError as err:
            log.error('Feature %s writing error %s', self.name(), str(err))
            log.error(get_dmesg(only_tail=True, filter_log=False))
            raise err

    @staticmethod
    def _find_by_file_pattern(pattern):
        if isinstance(pattern, list):
            matches_by_pattern = [list(glob.glob(p)) for p in pattern]
            all_matches = sum(matches_by_pattern, [])
            if all_matches:
                return all_matches[0]
        else:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None

    def get_values(self) -> List[NamedValue]:
        return []

    def exists(self):
        return self.filename is not None

    def set(self, value):
        outvalue = 1 if value else 0
        return self._write_file(self.filename, outvalue)

    def get(self):
        invalue = self._read_file_int(self.filename)
        return invalue != 0


class StrFileFeature(FileFeature):

    def set(self, value: str):
        return self._write_file(self.filename, value)

    def get(self):
        return self._read_file_str(self.filename)


class BoolFileFeature(FileFeature):

    def set(self, value: bool):
        value = bool(value)
        outvalue = 1 if value else 0
        return self._write_file(self.filename, outvalue)

    def get(self):
        invalue = self._read_file_int(self.filename)
        return invalue != 0


class LegionGUIAutostart(BoolFileFeature):

    def __init__(self):
        self.autostart_dekstop_folder_path = Path.home() / ".config" / "autostart"
        self.desktop_file_path = Path(
            '/usr/share/applications') / 'legion_gui_user.desktop'
        self.autostart_desktop_file_path = self.autostart_dekstop_folder_path / \
            "legion_gui_user.desktop"
        super().__init__(str(Path.home() / ".config"))

    def exists(self):
        return self.desktop_file_path.exists() and self.autostart_dekstop_folder_path.exists()

    def set(self, value: bool):
        log.info('Feature %s setting to %d', self.name(), value)
        if value:
            src = self.desktop_file_path
            dest = self.autostart_desktop_file_path
            log.info('Feature %s: Copy %s to %s', self.name(), src, dest)
            shutil.copyfile(src, dest)
        else:
            dest = self.autostart_desktop_file_path
            log.info('Feature %s: Delete %s', self.name(), dest)
            dest.unlink(missing_ok=True)
            log.info('Feature %s: Deleted %s', self.name(), dest)

    def get(self) -> bool:
        if not self.autostart_desktop_file_path.exists():
            return False
        return True


class IntFileFeature(FileFeature):
    limit_low_default: int
    limit_up_default: int
    step_default: int

    def __init__(self, pattern, limit_low_default=0, limit_up_default=255, step_default=1):
        super().__init__(pattern)
        self.limit_low_default = limit_low_default
        self.limit_up_default = limit_up_default
        self.step_default = step_default

    def get_limits_and_step(self):
        return (self.limit_low_default, self.limit_up_default, self.step_default)

    def set(self, value: int):
        value = int(value)
        return self._write_file(self.filename, str(value))

    def get(self) -> int:
        return self._read_file_int(self.filename)


class FloatFileFeature(FileFeature):
    limit_low_default: int
    limit_up_default: int
    step_default: int

    def __init__(self, pattern, limit_low_default=0, limit_up_default=255, step_default=1):
        super().__init__(pattern)
        self.limit_low_default = limit_low_default
        self.limit_up_default = limit_up_default
        self.step_default = step_default

    def get_limits_and_step(self):
        return (self.limit_low_default, self.limit_up_default, self.step_default)

    def set(self, value: float):
        value = float(value)
        return self._write_file(self.filename, str(value))

    def get(self):
        value = self._read_file_str(self.filename)
        return float(value)


class LockFanController(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, 'lockfancontroller'))


class BatteryConservation(BoolFileFeature):
    def __init__(self, rapidcharging_feature):
        super().__init__(os.path.join(IDEAPAD_SYS_BASEPATH, 'conservation_mode'))
        self.rapidcharging_feature = rapidcharging_feature

    def set(self, value):
        # disable rapid charging when enabling battery conservation
        if value and (self.rapidcharging_feature is not None) and self.rapidcharging_feature.exists():
            self.rapidcharging_feature.set(False)
        return super().set(value)

    def set_if_not_set(self, value: bool) -> None:
        if value is not self.get():
            self.set(value)
        print(f"Already has value {value} - skip setting again.")


class RapidChargingFeature(BoolFileFeature):
    '''Rapid charging of laptop battery'''

    def __init__(self, batterconservation_feature: BatteryConservation):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, 'rapidcharge'))
        self.batterconservation_feature = batterconservation_feature

    def set(self, value):
        # disable battery conservation when enabling rapid charging
        if value and (self.batterconservation_feature is not None) and self.batterconservation_feature.exists():
            self.batterconservation_feature.set(False)
        return super().set(value)


class FnLockFeature(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(IDEAPAD_SYS_BASEPATH, 'fn_lock'))


class WinkeyFeature(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, 'winkey'))


class TouchpadFeature(BoolFileFeature):
    def __init__(self):
        super().__init__([os.path.join(IDEAPAD_SYS_BASEPATH, 'touchpad'), os.path.join(
            LEGION_SYS_BASEPATH, 'touchpad')])


class CameraPowerFeature(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(IDEAPAD_SYS_BASEPATH, 'camera_power'))


class OverdriveFeature(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, 'overdrive'))


class GsyncFeature(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, 'gsync'))


class AlwaysOnUSBChargingFeature(BoolFileFeature):
    '''Always on USB Charging of external devices while laptop is off'''

    def __init__(self):
        super().__init__(os.path.join(IDEAPAD_SYS_BASEPATH, 'usb_charging'))

    def set(self, value: str):
        raise NotImplementedError()


class MaximumFanSpeedFeature(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, 'fan_fullspeed'))


class PlatformProfileFeature(FileFeature):
    def __init__(self):
        super().__init__("/sys/firmware/acpi/platform_profile")
        self.choices = StrFileFeature(
            "/sys/firmware/acpi/platform_profile_choices")
        self.all_values = [
            NamedValue("quiet", "Quiet Mode"),
            NamedValue("balanced", "Balanced Mode"),
            NamedValue("performance", "Performance Mode"),
            NamedValue("balanced-performance", "Custom Mode")
        ]

    def get_values(self) -> List[NamedValue]:
        try:
            available_choices_str = self.choices.get()
        except IOError as error:
            print(error)
            available_choices_str = ""
        available_choices = available_choices_str.split(" ")
        return [p for p in self.all_values if p.value in available_choices]

    def set(self, value: str):
        self._write_file(self.filename, value)

    def get(self):
        value = self._read_file_str(self.filename)
        return value


class IsOnPowerSupplyFeature(BoolFileFeature):
    def __init__(self):
        super().__init__("/sys/class/power_supply/ADP0/online")

    def set(self, value: str):
        raise NotImplementedError()


class BatteryIsCharging(BoolFileFeature):
    def __init__(self):
        super().__init__("/sys/class/power_supply/BAT0/status")

    def set(self, _: str):
        raise NotImplementedError()

    def get(self):
        value = self._read_file_str(self.filename)
        return value == "Charging"


class BatteryCurrentCapacityPercentage(FloatFileFeature):
    def __init__(self):
        super().__init__("/sys/class/power_supply/BAT0/capacity")

    def set(self, _: str):
        raise NotImplementedError()


class CPUOverclock(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "cpu_oc"))


class GPUOverclock(BoolFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "gpu_oc"))


class CPUShorttermPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "cpu_shortterm_powerlimit"), 5, 200, 1)


class CPULongtermPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "cpu_longterm_powerlimit"), 5, 200, 1)


class CPUPeakPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "cpu_peak_powerlimit"), 0, 200, 1)


class CPUAPUSPPTPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "cpu_apu_sppt_powerlimit"), 0, 100, 1)


class CPUDefaultPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "cpu_default_powerlimit"), 0, 100, 1)


class CPUCrossLoadingPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH,
                                      "cpu_cross_loading_powerlimit"), 0, 100, 1)


class GPUBoostClock(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "gpu_boost_clock"), 0, 10000, 1)


class GPUCTGPPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "gpu_ctgp_powerlimit"), 0, 200, 1)


class GPUPPABPowerLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "gpu_ppab_powerlimit"), 0, 200, 1)


class GPUTemperatureLimit(IntFileFeature):
    def __init__(self):
        super().__init__(os.path.join(LEGION_SYS_BASEPATH, "gpu_temperature_limit"), 0, 120, 1)


class YLogoLight(BoolFileFeature):
    def __init__(self):
        super().__init__("/sys/class/leds/platform::ylogo/brightness")


class IOPortLight(BoolFileFeature):
    def __init__(self):
        super().__init__("/sys/class/leds/platform::ioport/brightness")


class NVIDIAGPUIsRunning(BoolFileFeature):
    def __init__(self):
        super().__init__('/sys/bus/pci/devices/0000:01:00.0/power/runtime_status')

    def set(self, _: bool):
        raise NotImplementedError()

    def get(self):
        if self.exists():
            value = self._read_file_str(self.filename)
            return value != "suspended"
        return False


class CommandFeature:
    _exists: bool

    def __init__(self, cmds):
        self.cmds = cmds
        self._exists = False
        log.info('CommandFeature %s: %s', self.name(), self.cmds)
        if not self.exists():
            log.warning('Feature %s does not exist. exits: %d',
                        self.name(), self.exists())

    def _exec_cmd(self, cmd, timeout=None) -> Tuple[str, int]:
        log.info('CommandFeature %s execute "%s"', self.name(), cmd)
        try:
            with subprocess.Popen(['bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                stdout, _ = process.communicate(timeout=timeout)
                out_str = stdout.decode(DEFAULT_ENCODING)
                returncode = process.returncode
                log.info('CommandFeature %s reading with code %d: %s',
                         self.name(), returncode, out_str)
                return out_str, returncode
        except IOError as err:
            log.error('CommandFeature %s reading error %s',
                      self.name(), str(err))
            log.error(get_dmesg(only_tail=True, filter_log=False))
            raise err

    def name(self):
        return type(self).__name__

    def get_values(self) -> List[NamedValue]:
        return []

    def exists(self):
        return self._exists

    def set(self, value):
        raise NotImplementedError()

    def get(self):
        raise NotImplementedError()


class BoolCommandFeature(CommandFeature):

    def set(self, value):
        raise NotImplementedError()

    def get(self) -> bool:
        raise NotImplementedError()


class SystemDServiceFeature(BoolCommandFeature):
    def __init__(self, servicename):
        super().__init__([])
        self.status_cmd = f'systemctl status {servicename}'
        self.stop_cmd = f'systemctl stop {servicename}'
        self.start_cmd = f'systemctl start {servicename}'
        self.enable_cmd = f'systemctl enable {servicename}'
        self.disable_cmd = f'systemctl disable {servicename}'
        self.read_cmd = f'systemctl is-active {servicename}'
        self._exists = self._does_service_exists()

    def _does_service_exists(self):
        _, returncode = self._exec_cmd(self.status_cmd)
        return returncode != 4

    def set(self, value: bool):
        if value:
            self._exec_cmd(self.start_cmd)
            self._exec_cmd(self.enable_cmd)
        else:
            self._exec_cmd(self.stop_cmd)
            self._exec_cmd(self.disable_cmd)

    def get(self) -> bool:
        if self.exists():
            _, returncode = self._exec_cmd(self.read_cmd)
            return returncode == 0
        return False


class PowerProfilesDeamonService(SystemDServiceFeature):
    def __init__(self):
        super().__init__('power-profiles-daemon')


class LenovoLegionLaptopSupportService(SystemDServiceFeature):
    def __init__(self):
        super().__init__('legiond.service legiond-onresume.service legiond-cpuset.service legiond-cpuset.timer')


class FanCurveIO(Feature):
    hwmon_dir_pattern = os.path.join(LEGION_SYS_BASEPATH, 'hwmon/hwmon*')
    pwm1_fan_speed = "pwm1_auto_point{}_pwm"
    pwm2_fan_speed = "pwm2_auto_point{}_pwm"
    pwm1_temp_hyst = "pwm1_auto_point{}_temp_hyst"
    pwm1_temp = "pwm1_auto_point{}_temp"
    pwm2_temp_hyst = "pwm2_auto_point{}_temp_hyst"
    pwm2_temp = "pwm2_auto_point{}_temp"
    pwm3_temp_hyst = "pwm3_auto_point{}_temp_hyst"
    pwm3_temp = "pwm3_auto_point{}_temp"
    pwm1_accel = "pwm1_auto_point{}_accel"
    pwm1_decel = "pwm1_auto_point{}_decel"
    minifancurve = "minifancurve"
    fan1_max = "fan1_max"
    fan2_max = "fan2_max"

    encoding = DEFAULT_ENCODING

    def __init__(self, expect_hwmon=True):
        super().__init__()
        self.hwmon_path = self._find_hwmon_dir()
        if (not self.hwmon_path) and expect_hwmon:
            raise FileNotFoundError("hwmon dir not found")

    def exists(self):
        if self.hwmon_path is not None:
            file_path = self.hwmon_path + self.pwm1_fan_speed.format(1)
            has_point1 = os.path.exists(file_path)
            return has_point1
        return False

    def _find_hwmon_dir(self):
        matches = glob.glob(self.hwmon_dir_pattern)
        if matches:
            return matches[0]+'/'
        return None

    @staticmethod
    def _validate_point_id(point_id):
        if point_id < 1 or point_id > 10:
            raise ValueError("Invalid point_id. Must be between 1 and 10.")
        return point_id

    @staticmethod
    def _read_file(file_path):
        with open(file_path, "r", encoding=DEFAULT_ENCODING) as filepointer:
            return int(filepointer.read())

    @staticmethod
    def _read_file_or(file_path, default):
        if os.path.exists(file_path):
            return FanCurveIO._read_file(file_path)
        return default

    @staticmethod
    def _write_file(file_path, value):
        with open(file_path, "w", encoding=DEFAULT_ENCODING) as filepointer:
            filepointer.write(str(value))

    @staticmethod
    def _write_file_or(file_path, value):
        if os.path.exists(file_path):
            FanCurveIO._write_file(file_path, value)

    def get_fan_1_max_rpm(self):
        file_path = self.hwmon_path + self.fan1_max
        return int(self._read_file(file_path))

    def get_fan_2_max_rpm(self):
        file_path = self.hwmon_path + self.fan2_max
        return int(self._read_file(file_path))

    def set_fan_1_speed_pwm(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_fan_speed.format(point_id)
        self._write_file(file_path, value)

    def set_fan_2_speed_pwm(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_fan_speed.format(point_id)
        self._write_file(file_path, value)

    def set_fan_1_speed_rpm(self, point_id, value):
        return self.set_fan_1_speed_pwm(point_id, round(value/self.get_fan_1_max_rpm()*255.0))

    def set_fan_2_speed_rpm(self, point_id, value):
        return self.set_fan_2_speed_pwm(point_id, round(value/self.get_fan_2_max_rpm()*255.0))

    def set_lower_cpu_temperature(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_temp_hyst.format(point_id)
        self._write_file(file_path, value)

    def set_upper_cpu_temperature(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_temp.format(point_id)
        self._write_file(file_path, value)

    def set_lower_gpu_temperature(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_temp_hyst.format(point_id)
        self._write_file(file_path, value)

    def set_upper_gpu_temperature(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_temp.format(point_id)
        self._write_file(file_path, value)

    def set_lower_ic_temperature(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm3_temp_hyst.format(point_id)
        self._write_file(file_path, value)

    def set_upper_ic_temperature(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm3_temp.format(point_id)
        self._write_file(file_path, value)

    def set_acceleration(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_accel.format(point_id)
        self._write_file(file_path, value)

    def set_deceleration(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_decel.format(point_id)
        self._write_file(file_path, value)

    def get_fan_1_speed_pwm(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_fan_speed.format(point_id)
        return self._read_file(file_path)

    def get_fan_2_speed_pwm(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_fan_speed.format(point_id)
        return self._read_file(file_path)

    def get_fan_1_speed_rpm(self, point_id):
        return round(self.get_fan_1_speed_pwm(point_id)/255.0*self.get_fan_1_max_rpm(), ndigits=2)

    def get_fan_2_speed_rpm(self, point_id):
        return round(self.get_fan_2_speed_pwm(point_id)/255.0*self.get_fan_2_max_rpm(), ndigits=2)

    def get_lower_cpu_temperature(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_temp_hyst.format(point_id)
        return self._read_file(file_path)

    def get_upper_cpu_temperature(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_temp.format(point_id)
        return self._read_file(file_path)

    def get_lower_gpu_temperature(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_temp_hyst.format(point_id)
        return self._read_file(file_path)

    def get_upper_gpu_temperature(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_temp.format(point_id)
        return self._read_file(file_path)

    def get_lower_ic_temperature(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm3_temp_hyst.format(point_id)
        return self._read_file(file_path)

    def get_upper_ic_temperature(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm3_temp.format(point_id)
        return self._read_file(file_path)

    def get_acceleration(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_accel.format(point_id)
        return self._read_file(file_path)

    def get_deceleration(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_decel.format(point_id)
        return self._read_file(file_path)

    def has_minifancurve(self):
        return self.exists() and self.hwmon_path is not None and os.path.exists(self.hwmon_path + self.minifancurve)

    def set_minifancuve(self, value):
        log.info("Setting minifancurve to: %s", str(value))
        file_path = self.hwmon_path + self.minifancurve
        outvalue = 1 if value else 0
        return self._write_file_or(file_path, outvalue)

    def get_minifancuve(self):
        file_path = self.hwmon_path + self.minifancurve
        invalue = self._read_file_or(file_path, False)
        return invalue != 0

    def set_str_value(self, value: str):
        fancurve = FanCurve.from_yaml(value)
        self.write_fan_curve(fancurve)

    def write_fan_curve(self, fan_curve: FanCurve, _=False):
        """Writes a fan curve object to the file system and sets minifancurve if enabled"""
        if self.use_legion_cli_to_write:
            write_file_with_legion_cli(self.name(), [str(fan_curve.to_yaml())])
            return
        try:
            log.info(
                "Trying to set minifancurve using fancurve profile to: %s", str(fan_curve.enable_minifancurve))
            self.set_minifancuve(fan_curve.enable_minifancurve)
        # pylint: disable=broad-except
        except BaseException as error:
            log.error(str(error))
        for index, entry in enumerate(fan_curve.entries):
            point_id = index + 1
            self.set_fan_1_speed_rpm(point_id, entry.fan1_speed)
            self.set_fan_2_speed_rpm(point_id, entry.fan2_speed)
            self.set_lower_cpu_temperature(point_id, entry.cpu_lower_temp)
            self.set_upper_cpu_temperature(point_id, entry.cpu_upper_temp)
            self.set_lower_gpu_temperature(point_id, entry.gpu_lower_temp)
            self.set_upper_gpu_temperature(point_id, entry.gpu_upper_temp)
            self.set_lower_ic_temperature(point_id, entry.ic_lower_temp)
            self.set_upper_ic_temperature(point_id, entry.ic_upper_temp)
            self.set_acceleration(point_id, entry.acceleration)
            self.set_deceleration(point_id, entry.deceleration)

    def read_fan_curve(self) -> FanCurve:
        """Reads a fan curve object from the file system"""
        entries = []
        for point_id in range(1, 11):
            fan1_speed = self.get_fan_1_speed_rpm(point_id)
            fan2_speed = self.get_fan_2_speed_rpm(point_id)
            cpu_lower_temp = self.get_lower_cpu_temperature(point_id)
            cpu_upper_temp = self.get_upper_cpu_temperature(point_id)
            gpu_lower_temp = self.get_lower_gpu_temperature(point_id)
            gpu_upper_temp = self.get_upper_gpu_temperature(point_id)
            ic_lower_temp = self.get_lower_ic_temperature(point_id)
            ic_upper_temp = self.get_upper_ic_temperature(point_id)
            acceleration = self.get_acceleration(point_id)
            deceleration = self.get_deceleration(point_id)
            entry = FanCurveEntry(fan1_speed=fan1_speed, fan2_speed=fan2_speed,
                                  cpu_lower_temp=cpu_lower_temp, cpu_upper_temp=cpu_upper_temp,
                                  gpu_lower_temp=gpu_lower_temp, gpu_upper_temp=gpu_upper_temp,
                                  ic_lower_temp=ic_lower_temp, ic_upper_temp=ic_upper_temp,
                                  acceleration=acceleration, deceleration=deceleration)
            entries.append(entry)
        fancurve = FanCurve(name='unknown', entries=entries)
        try:
            fancurve.enable_minifancurve = self.get_minifancuve()
        # pylint: disable=broad-except
        except BaseException as error:
            log.error(str(error))
        return fancurve


class ApplicationModel:
    automatic_close: BoolSettingFeature
    close_to_tray: BoolSettingFeature
    open_closed_to_tray: BoolSettingFeature
    enable_gui_monitoring: BoolSettingFeature
    icon_color_mode: EnumSettingFeature

    def __init__(self):
        self.automatic_close = BoolSettingFeature('automatic_close')
        self.automatic_close.set(False)

        self.close_to_tray = BoolSettingFeature('close_to_tray')
        self.close_to_tray.set(False)

        self.open_closed_to_tray = BoolSettingFeature('open_closed_to_tray')
        self.open_closed_to_tray.set(False)

        self.enable_gui_monitoring = BoolSettingFeature('enable_gui_monitoring')
        self.enable_gui_monitoring.set(False)

        icon_color_modes = [
            NamedValue("always-color", "Always use colorful color scheme"),
            NamedValue("always-light", "Always use light color scheme"),
            NamedValue("always-dark", "Always use dark color scheme"),
            NamedValue("automatic", "Use system color scheme"),
            NamedValue("automatic-inverted", "Use inverted system color scheme")
        ]
        self.icon_color_mode = EnumSettingFeature("icon_color_mode", icon_color_modes[0].value, icon_color_modes)
        self.icon_color_mode.set(icon_color_modes[0].value)


@dataclass
class Settings(Serializable):
    setting_entries: Dict

    def to_yaml(self):
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str):
        data = yaml.load(yaml_str, Loader=yaml.SafeLoader)['setting_entries']
        return Settings(data)


class SettingsManager(Feature):
    features: List[Feature]

    def __init__(self, preset_dir) -> None:
        super().__init__()
        self.preset_dir = preset_dir
        self.features = []

    def add_feature(self, feature: Feature):
        self.features.append(feature)

    def get_settings(self) -> Settings:
        settings = Settings({})
        for feat in self.features:
            name = feat.name()
            value = feat.get()
            log.info("Add to setting: %s, %s", name, value)
            settings.setting_entries[name] = value
        return settings

    def apply_settings(self, preset: Settings):
        for name, value in preset.setting_entries.items():
            log.error("Try seting %s from preset to %s", name, value)
            has_set = Feature.set_feature_to_value(name, value)
            if not has_set:
                log.error("Cannot set %s from preset to %s", name, value)

    def _name_to_filename(self, name):
        return os.path.join(self.preset_dir, name+".yaml")

    def does_exists_by_name(self, name):
        return os.path.exists(self._name_to_filename(name))

    def load_by_name(self, name):
        return Settings.load_from_file(self._name_to_filename(name))

    def save_by_name(self, name, settings: Settings):
        if self.use_legion_cli_to_write:
            write_file_with_legion_cli(
                self.name(), [name, str(settings.to_yaml())])
            return
        settings.save_to_file(self._name_to_filename(name))

    def set_str_values(self, values: List[str]):
        name = values[0]
        fancurve = Settings.from_yaml(values[1])
        self.save_by_name(name, fancurve)


class FanCurveRepository(Feature):
    def __init__(self, preset_dir):
        super().__init__()
        self.fancurve_presets = {
            "quiet-battery": None,
            "balanced-battery": None,
            "performance-battery": None,
            "balanced-performance-battery": None,
            "quiet-ac": None,
            "balanced-ac": None,
            "performance-ac": None,
            "balanced-performance-ac": None
        }

        self.preset_dir = preset_dir

    @staticmethod
    def get_preset_name(profile: str, is_on_powersupply: bool):
        symb = "ac" if is_on_powersupply else "battery"
        preset_name = f"{profile}-{symb}"
        return preset_name

    def _name_to_filename(self, name):
        return os.path.join(self.preset_dir, name+".yaml")

    def get_names(self):
        return self.fancurve_presets.keys()

    def does_exists_by_name(self, name):
        return os.path.exists(self._name_to_filename(name))

    def load_by_name(self, name):
        return FanCurve.load_from_file(self._name_to_filename(name))

    def load_by_name_or_default(self, name):
        if self.does_exists_by_name(name):
            return self.load_by_name(name)
        return FanCurve(name='unknown', entries=[])

    def save_by_name(self, name, fancurve: FanCurve):
        if self.use_legion_cli_to_write:
            write_file_with_legion_cli(
                self.name(), [name, str(fancurve.to_yaml())])
            return
        fancurve.save_to_file(self._name_to_filename(name))

    def set_str_values(self, values: List[str]):
        name = values[0]
        fancurve = FanCurve.from_yaml(values[1])
        self.save_by_name(name, fancurve)


class CustomConservationController:
    def __init__(self, battery_conservation: BatteryConservation,
                 battery_capacity_perc: BatteryCurrentCapacityPercentage):
        self.battery_conservation = battery_conservation
        self.battery_capacity_perc = battery_capacity_perc
        self.lower_limit = 60
        self.upper_limit = 80

    def run(self):
        battery_cap = self.battery_capacity_perc.get()
        if battery_cap > self.upper_limit:
            print(
                "Enabling conservation mode because battery" +
                f" {battery_cap} is greater than upper limit {self.upper_limit}")
            self.battery_conservation.set_if_not_set(True)
            return self.battery_conservation.get()
        if battery_cap < self.lower_limit:
            print(
                "Disabling conservation mode because battery" +
                f" {battery_cap} is lower than lower limit {self.lower_limit}")
            self.battery_conservation.set_if_not_set(False)
            return self.battery_conservation.get()
        print(
            "Keeping conservation mode because battery" +
            f" {battery_cap} is within bounds of {self.lower_limit} and {self.upper_limit}")
        return self.battery_conservation.get()


@dataclass
class DiagnosticMsg:
    value: bool = None
    has_value: bool = True
    msg: str = ''
    # filter by setting attribute so current message could still be displayed
    filter_do_output: bool = True


class DiagFilter:

    def predicate(self, diag_msg: DiagnosticMsg):
        raise NotImplementedError()

    def apply_filter(self, diag_msg: DiagnosticMsg) -> DiagnosticMsg:
        if diag_msg.has_value and diag_msg.filter_do_output:
            diag_msg.filter_do_output = diag_msg.filter_do_output and self.predicate(
                diag_msg)
        return diag_msg


class FilterNotChanged(DiagFilter):
    last_value: Optional[bool]

    def __init__(self) -> None:
        super().__init__()
        self.last_value = None

    def predicate(self, diag_msg: DiagnosticMsg) -> bool:
        out = diag_msg.value != self.last_value
        self.last_value = diag_msg.value
        return out


class FilterAtMostEvery(DiagFilter):
    last_output_time: Optional[float]
    period_s: float

    def __init__(self, period_s: float):
        self.period_s = period_s
        self.last_output_time = None

    def predicate(self, diag_msg: DiagnosticMsg) -> bool:
        cur_time = time.time()
        if self.last_output_time is None:
            do_output = True
        else:
            do_output = cur_time > self.last_output_time + self.period_s
        if do_output:
            self.last_output_time = cur_time
        return do_output


class Monitor:
    inputs: List[FileFeature]
    period_s: float

    def __init__(self, inputs: List[FileFeature] = None) -> None:
        if inputs is None:
            inputs = []
        self.inputs = list(inputs)  # copy list
        self.period_s = 1.0

    def run(self) -> List[DiagnosticMsg]:
        raise NotImplementedError()

    def get_inputs(self) -> List[FileFeature]:
        return self.inputs

    def add_input(self, new_input: FileFeature):
        self.inputs.append(new_input)


class NVIDIAGPUMonitor(Monitor):
    gpu_is_running: NVIDIAGPUIsRunning
    filter: DiagFilter

    def __init__(self, gpu_is_running: NVIDIAGPUIsRunning) -> None:
        super().__init__([gpu_is_running])
        self.gpu_is_running = gpu_is_running
        self.filter = FilterNotChanged()

    def run(self) -> List[DiagnosticMsg]:
        is_gpu_running = self.gpu_is_running.get()
        gpu_running_diag = DiagnosticMsg()
        if is_gpu_running:
            gpu_running_diag.value = True
            gpu_running_diag.msg = 'GPU wakeup'
        else:
            gpu_running_diag.value = False
            gpu_running_diag.msg = 'GPU suspended'
        gpu_running_diag = self.filter.apply_filter(gpu_running_diag)

        return [gpu_running_diag]


class NVIDIAGPUOnBatteryMonitor(Monitor):
    gpu_is_running: NVIDIAGPUIsRunning
    gpu_is_on_power_supply: IsOnPowerSupplyFeature
    filter: DiagFilter

    def __init__(self, gpu_is_running: NVIDIAGPUIsRunning, is_on_power_supply: IsOnPowerSupplyFeature) -> None:
        super().__init__([gpu_is_running, is_on_power_supply])
        self.gpu_is_running = gpu_is_running
        self.is_on_power_supply = is_on_power_supply
        self.filter = FilterAtMostEvery(period_s=10)

    def run(self) -> List[DiagnosticMsg]:
        is_gpu_running = self.gpu_is_running.get()
        is_on_battery = not self.is_on_power_supply.get()
        diag = DiagnosticMsg()
        if is_gpu_running and is_on_battery:
            diag.value = True
            diag.msg = 'Running on battery with dGPU on.'
            diag = self.filter.apply_filter(diag)
        else:
            diag.value = False
            diag.msg = 'Running on battery with dGPU off.'
            diag.has_value = False
            diag = self.filter.apply_filter(diag)

        return [diag]


class NVIDIAGPUOnQuietMode(Monitor):
    gpu_is_running: NVIDIAGPUIsRunning
    platform_profile: PlatformProfileFeature
    filter: DiagFilter

    def __init__(self, gpu_is_running: NVIDIAGPUIsRunning, platform_profile: PlatformProfileFeature) -> None:
        super().__init__([gpu_is_running, platform_profile])
        self.gpu_is_running = gpu_is_running
        self.platform_profile = platform_profile
        self.filter = FilterAtMostEvery(period_s=60*10)

    def run(self) -> List[DiagnosticMsg]:
        is_gpu_running = self.gpu_is_running.get()
        is_quiet_mode = self.platform_profile.get() == "quiet"
        diag = DiagnosticMsg()
        if is_gpu_running and is_quiet_mode:
            diag.value = True
            diag.msg = 'Running on quiet mode with dGPU on.'
            diag = self.filter.apply_filter(diag)
        else:
            diag.value = False
            diag.msg = 'Not running on quiet mode with dGPU on.'
            diag.has_value = False
            diag = self.filter.apply_filter(diag)

        return [diag]

# class INotifyMonitor:

#     def __init__(self):
#         self.monitors = []
#         self.monitors_by_featurefilename = {}
#         self.inot = inotify.adapters.Inotify()


#     def add_monitor(self, monitor:Monitor):
#         for file_feature in monitor.get_inputs():
#             filename = file_feature.filename
#             if filename:
#                 self.inot.add_watch(filename.encode())
#                 if filename in self.monitors_by_featurefilename:
#                     self.monitors_by_featurefilename[filename].append(monitor)
#                 else:
#                     self.monitors_by_featurefilename[filename] = [monitor]
#                 self.monitors.append(monitor)

#     def get_monitors_for_filename(self, filename):
#         return self.monitors_by_featurefilename.get(filename, [])

#     def run(self):
#         monitors_to_notify : List[Monitor] = []
#         for event in self.inot.event_gen(yield_nones=True):
#             # collect all monitors that should be notified
#             if event:
#                 header, type_names, path, filename = event
#                 print(event)
#                 for m in self.get_monitors_for_filename():
#                     if m not in monitors_to_notify:
#                         monitors_to_notify.append(m)
#             # call each monitor that should be notified once
#             # for this timestep
#             if event is None:
#                 for m in monitors_to_notify:
#                     m.run()
#                 monitors_to_notify = []


class NotifcationSender:
    disable_notifications: bool

    def __init__(self):
        self.disable_notifications = False

    def notify(self, title, msg):
        return self._send_notification(title, msg)

    def _send_notification(self, title, msg):
        raise NotImplementedError()


class SystemNotificationSender(NotifcationSender):

    def _send_notification(self, _, msg):
        if is_root_user():
            # Drop root privileges so we can send notifications
            # TODOs: find a better way
            # Code by user dvilela on stackoverflow
            # https://stackoverflow.com/a/54718205
            user_id = subprocess.run(['id', '-u', os.environ['SUDO_USER']],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True).stdout.decode("utf-8").replace('\n', '')
            subprocess.run(['sudo', '-u', os.environ['SUDO_USER'],
                            f'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{user_id}/bus',
                            'notify-send', '-i', 'utilities-terminal', msg, msg],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True)
        else:
            with subprocess.Popen(['notify-send', msg]) as _:
                pass


class LegionModelFacade:
    monitors: List[Monitor]

    # pylint: disable=too-many-statements
    def __init__(self, expect_hwmon=True, use_legion_cli_to_write=False, config_dir=DEFAULT_CONFIG_DIR):
        Feature.default_use_legion_cli_to_write = use_legion_cli_to_write
        log.info(get_dmesg())
        self.fancurve_io = FanCurveIO(expect_hwmon=expect_hwmon)
        self.fancurve_repo = FanCurveRepository(preset_dir=config_dir)
        self.fan_curve = FanCurve(name='unknown',
                                  entries=[FanCurveEntry(
                                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0) for i in range(10)],
                                  enable_minifancurve=False)
        self.lockfancontroller = LockFanController()
        self.rapid_charging = RapidChargingFeature(None)
        self.battery_conservation = BatteryConservation(None)
        # fix this by resolving circular dependency by facade or similar
        self.rapid_charging.batterconservation_feature = self.battery_conservation
        self.battery_conservation.rapidcharging_feature = self.rapid_charging
        self.maximum_fanspeed = MaximumFanSpeedFeature()
        self.fn_lock = FnLockFeature()
        self.winkey = WinkeyFeature()
        self.touchpad = TouchpadFeature()
        self.camera_power = CameraPowerFeature()
        self.overdrive = OverdriveFeature()
        self.gsync = GsyncFeature()
        self.platform_profile = PlatformProfileFeature()
        self.on_power_supply = IsOnPowerSupplyFeature()
        self.always_on_usb_charging = AlwaysOnUSBChargingFeature()
        self.battery_capacity_perc = BatteryCurrentCapacityPercentage()
        self.battery_custom_conservation_controller = CustomConservationController(
            self.battery_conservation, self.battery_capacity_perc)

        # OC and Power
        self.cpu_overclock = CPUOverclock()
        self.cpu_longterm_power_limit = CPULongtermPowerLimit()
        self.cpu_shortterm_power_limit = CPUShorttermPowerLimit()
        self.cpu_peak_power_limit = CPUPeakPowerLimit()
        self.cpu_default_power_limit = CPUDefaultPowerLimit()
        self.cpu_cross_loading_power_limit = CPUCrossLoadingPowerLimit()
        self.cpu_apu_sppt_power_limit = CPUAPUSPPTPowerLimit()
        self.gpu_overclock = GPUOverclock()
        self.gpu_boost_clock = GPUBoostClock()
        self.gpu_ctgp_power_limit = GPUCTGPPowerLimit()
        self.gpu_ppab_power_limit = GPUPPABPowerLimit()
        self.gpu_temperature_limit = GPUTemperatureLimit()

        # light
        self.ylogo_light = YLogoLight()
        self.ioport_light = IOPortLight()

        # services
        self.power_profiles_deamon_service = PowerProfilesDeamonService()
        self.lenovo_legion_laptop_support_service = LenovoLegionLaptopSupportService()
        self.legion_gui_autostart = LegionGUIAutostart()

        # monitors
        self.nvidia_gpu_running = NVIDIAGPUIsRunning()
        self.nvidia_gpu_monitor = NVIDIAGPUMonitor(self.nvidia_gpu_running)
        self.nvidia_battery_monitor = NVIDIAGPUOnBatteryMonitor(
            self.nvidia_gpu_running, self.on_power_supply)
        self.dgpu_on_quiet_monitior = NVIDIAGPUOnQuietMode(
            self.nvidia_gpu_running, self.platform_profile)
        self.monitors = [self.nvidia_gpu_monitor,
                         self.nvidia_battery_monitor, self.dgpu_on_quiet_monitior]

        # Other settings mainly for app
        self.app_model = ApplicationModel()

        # Savable Settings
        self.settings_manager = SettingsManager(preset_dir=config_dir)
        self.settings_manager.add_feature(self.app_model.close_to_tray)
        self.settings_manager.add_feature(self.app_model.open_closed_to_tray)
        self.settings_manager.add_feature(self.app_model.enable_gui_monitoring)
        self.settings_manager.add_feature(self.app_model.icon_color_mode)

    @staticmethod
    def is_root_user():
        return is_root_user()

    @staticmethod
    def set_feature_to_str_value(name: str, values: List[str]) -> bool:
        return Feature.set_feature_to_str_value(name, values)

    @staticmethod
    def get_all_features():
        return [feat.name() for feat in Feature.features]

    def set_lockfancontroller(self, value):
        self.lockfancontroller.set(value)

    def get_lockfancontroller(self):
        return self.lockfancontroller.get()

    def get_preset_folder(self):
        return self.fancurve_repo.preset_dir

    def set_preset_folder(self, preset_dir: str):
        self.fancurve_repo.preset_dir = preset_dir

    def read_fancurve_from_hw(self):
        self.fan_curve = self.fancurve_io.read_fan_curve()

    def write_fancurve_to_hw(self, write_minifancurve=False):
        self.fancurve_io.write_fan_curve(self.fan_curve, write_minifancurve)

    def load_fancurve_from_preset(self, name):
        self.fan_curve = self.fancurve_repo.load_by_name(name)

    def save_fancurve_to_preset(self, name):
        self.fancurve_repo.save_by_name(name, self.fan_curve)

    def fancurve_write_preset_to_hw(self, name, write_minifancurve=False):
        self.load_fancurve_from_preset(name)
        self.write_fancurve_to_hw(write_minifancurve)

    def fancurve_write_hw_to_preset(self, name):
        self.read_fancurve_from_hw()
        self.save_fancurve_to_preset(name)

    def fancurve_write_file_to_hw(self, filename: str, write_minifancurve=False):
        self.fan_curve = FanCurve.load_from_file(filename)
        self.write_fancurve_to_hw(write_minifancurve)

    def fancurve_write_hw_to_file(self, filename: str):
        self.read_fancurve_from_hw()
        self.fan_curve.save_to_file(filename)

    def fancurve_write_preset_for_current_profile(self, write_minifancurve=False):
        is_on_powersupply = self.on_power_supply.get()
        profile = self.platform_profile.get()
        preset_name = self.fancurve_repo.get_preset_name(
            profile, is_on_powersupply)
        print(
            f"Loading preset={preset_name} for profile={profile} and is_powersupply={is_on_powersupply}")
        if preset_name in self.fancurve_repo.fancurve_presets:
            fancurve = self.fancurve_repo.load_by_name_or_default(preset_name)
            self.fancurve_io.write_fan_curve(fancurve, write_minifancurve)
            print(fancurve)

    def conservation_apply_mode_for_current_battery_capacity(self, lower_limit=None, upper_limit=None):
        if lower_limit is not None:
            self.battery_custom_conservation_controller.lower_limit = lower_limit
        if upper_limit is not None:
            self.battery_custom_conservation_controller.upper_limit = upper_limit
        return self.battery_custom_conservation_controller.run()

    def load_settings(self):
        if self.settings_manager.does_exists_by_name('settings'):
            log.info("Settings file exists and will be loaded.")
            settings = self.settings_manager.load_by_name('settings')
            log.info("Loaded settings:\n %s", settings.to_yaml())
            self.settings_manager.apply_settings(settings)
        else:
            log.info("Settings file does not exist.")

    def save_settings(self):
        log.info("Saving settings...")
        settings = self.settings_manager.get_settings()
        log.info("Settings:\n %s", settings.to_yaml())
        self.settings_manager.save_by_name('settings', settings)
        log.info("Saving settings done")

    def run_monitors(self, period_s):
        notification_sender = SystemNotificationSender()
        period_s = period_s or self.nvidia_gpu_monitor.period_s
        try:
            while True:
                print(".", flush=True, end='')
                diag_msgs: List[DiagnosticMsg] = []
                for mon in self.monitors:
                    try:
                        diag_msgs = diag_msgs + mon.run()
                    # pylint: disable=broad-except
                    except Exception as err:
                        log.error(str(err))
                for msg in diag_msgs:
                    if msg.has_value and msg.filter_do_output:
                        print('')
                        print(msg.msg)
                        notification_sender.notify('Legion', msg.msg)
                    elif msg.has_value:
                        print(f"FILTERED: {msg.msg}")
                    else:
                        print(f"FILTERED2: {msg.msg}")
                time.sleep(period_s)
        except KeyboardInterrupt:
            print('Monitor Interrupted!')
