import os
import glob
from dataclasses import asdict, dataclass
from typing import List
from pathlib import Path

import yaml

DEFAULT_ENCODING = "utf8"
CONFIG_FOLDER = ".config/legion_linux"


@dataclass(order=True)
class FanCurveEntry:
    fan1_speed: int
    fan2_speed: int
    cpu_lower_temp: int
    cpu_upper_temp: int
    gpu_lower_temp: int
    gpu_upper_temp: int
    ic_lower_temp: int
    ic_upper_temp: int
    acceleration: int
    deceleration: int


@dataclass
class FanCurve:
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
        return cls(name, entries)

    def save_to_file(self, filename):
        with open(filename, 'w', encoding=DEFAULT_ENCODING) as filepointer:
            filepointer.write(self.to_yaml())

    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'r', encoding=DEFAULT_ENCODING) as filepointer:
            return cls.from_yaml(filepointer.read())


class FileFeature:
    pattern: str
    filename: str

    def __init__(self, pattern):
        self.pattern = pattern
        self.filename = FileFeature._find_by_file_pattern(pattern)

    @staticmethod
    def _read_file_str(file_path) -> str:
        with open(file_path, "r", encoding=DEFAULT_ENCODING) as filepointer:
            return str(filepointer.read()).strip()

    @staticmethod
    def _read_file_int(file_path) -> int:
        return int(FileFeature._read_file_str(file_path))

    @staticmethod
    def _write_file(file_path, value):
        with open(file_path, "w", encoding=DEFAULT_ENCODING) as filepointer:
            filepointer.write(str(value))

    @staticmethod
    def _find_by_file_pattern(pattern):
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
        return None

    def exists(self):
        return self.filename is not None

    def set(self, value):
        outvalue = 1 if value else 0
        return self._write_file(self.filename, outvalue)

    def get(self):
        invalue = self._read_file_int(self.filename)
        return invalue != 0


class LockFanController(FileFeature):
    def __init__(self):
        super().__init__("/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/lockfancontroller")


class BatteryConservation(FileFeature):
    def __init__(self):
        super().__init__("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/conservation_mode")


class FnLockFeature(FileFeature):
    def __init__(self):
        super().__init__("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/fn_lock")


class TouchpadFeature(FileFeature):
    def __init__(self):
        super().__init__("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/touchpad")


class CameraPowerFeature(FileFeature):
    def __init__(self):
        super().__init__("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/camera_power")


class AlwaysOnUSBChargingFeature(FileFeature):
    '''Always on USB Charging of external devices on while laptop is off'''

    def __init__(self):
        super().__init__("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/usb_charging")


class RapidChargingFeature(FileFeature):
    '''Rapid charging of laptop battery'''

    def __init__(self):
        super().__init__("/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/rapid_charging")


class MaximumFanSpeedFeature(FileFeature):
    def __init__(self):
        super().__init__("/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm1_mode_")

    def set(self, value):
        outvalue = 0 if value else 2
        return self._write_file(self.filename, outvalue)

    def get(self):
        invalue = self._read_file_int(self.filename)
        return invalue == 0


class PlatformProfileFeature(FileFeature):
    def __init__(self):
        super().__init__("/sys/firmware/acpi/platform_profile")

    def set(self, value:str):
        self._write_file(self.filename, value)

    def get(self):
        value = self._read_file_str(self.filename)
        return value


class IsOnPowerSupplyFeature(FileFeature):
    def __init__(self):
        super().__init__("/sys/class/power_supply/ADP0/online")

    def set(self, value: str):
        raise NotImplementedError()


class FanCurveIO:
    hwmon_dir_pattern = '/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*'
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

    encoding = DEFAULT_ENCODING

    def __init__(self, expect_hwmon=True):
        self.hwmon_path = self._find_hwmon_dir()
        if (not self.hwmon_path) and expect_hwmon:
            raise Exception("hwmon dir not found")

    def exists(self):
        return self.hwmon_path is not None

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

    def set_fan_1_speed(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_fan_speed.format(point_id)
        self._write_file(file_path, value)

    def set_fan_2_speed(self, point_id, value):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_fan_speed.format(point_id)
        self._write_file(file_path, value)

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

    def get_fan_1_speed(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm1_fan_speed.format(point_id)
        return self._read_file(file_path)

    def get_fan_2_speed(self, point_id):
        point_id = self._validate_point_id(point_id)
        file_path = self.hwmon_path + self.pwm2_fan_speed.format(point_id)
        return self._read_file(file_path)

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
        return self.exists() and os.path.exists(self.hwmon_path + self.minifancurve)

    def set_minifancuve(self, value):
        file_path = self.hwmon_path + self.minifancurve
        outvalue = 1 if value else 0
        return self._write_file_or(file_path, outvalue)

    def get_minifancuve(self):
        file_path = self.hwmon_path + self.minifancurve
        invalue = self._read_file_or(file_path, False)
        return invalue != 0

    def write_fan_curve(self, fan_curve: FanCurve):
        """Writes a fan curve object to the file system"""
        try:
            self.set_minifancuve(fan_curve.enable_minifancurve)
        # pylint: disable=broad-except
        except Exception as error:
            print(error)
        for index, entry in enumerate(fan_curve.entries):
            point_id = index + 1
            self.set_fan_1_speed(point_id, entry.fan1_speed)
            self.set_fan_2_speed(point_id, entry.fan2_speed)
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
            fan1_speed = self.get_fan_1_speed(point_id)
            fan2_speed = self.get_fan_2_speed(point_id)
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
            print(error)
        return fancurve


class FanCurveRepository:
    def __init__(self):
        self.fancurve_presets = {
            "quiet-battery": None,
            "balanced-battery": None,
            "performance-battery": None,
            "quiet-ac": None,
            "balanced-ac": None,
            "performance-ac": None
        }

        self.preset_dir = os.path.join(os.getenv("HOME"), CONFIG_FOLDER)

    @staticmethod
    def get_preset_name(profile: str, is_on_powersupply: bool):
        symb = "ac" if is_on_powersupply else "battery"
        preset_name = f"{profile}-{symb}"
        return preset_name

    def create_preset_folder(self):
        print(f"Create path {self.preset_dir}")
        Path(self.preset_dir).mkdir(parents=True, exist_ok=True)

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
        fancurve.save_to_file(self._name_to_filename(name))


class LegionModelFacade:
    def __init__(self, expect_hwmon=True):
        self.fancurve_io = FanCurveIO(expect_hwmon=expect_hwmon)
        self.fancurve_repo = FanCurveRepository()
        self.fan_curve = FanCurve(name='unknown',
                                  entries=[FanCurveEntry(
                                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0) for i in range(10)],
                                  enable_minifancurve=False)
        self.lockfancontroller = LockFanController()
        self.battery_conservation = BatteryConservation()
        self.maximum_fanspeed = MaximumFanSpeedFeature()
        self.fn_lock = FnLockFeature()
        self.touchpad = TouchpadFeature()
        self.platform_profile = PlatformProfileFeature()
        self.on_power_supply = IsOnPowerSupplyFeature()
        self.camera_power = CameraPowerFeature()
        self.always_on_usb_charging = AlwaysOnUSBChargingFeature()
        self.rapid_charging = RapidChargingFeature()

    @staticmethod
    def is_root_user():
        return os.geteuid() == 0

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

    def write_fancurve_to_hw(self):
        self.fancurve_io.write_fan_curve(self.fan_curve)

    def load_fancurve_from_preset(self, name):
        self.fan_curve = self.fancurve_repo.load_by_name(name)

    def save_fancurve_to_preset(self, name):
        self.fancurve_repo.save_by_name(name, self.fan_curve)

    def fancurve_write_preset_to_hw(self, name):
        self.load_fancurve_from_preset(name)
        self.write_fancurve_to_hw()

    def fancurve_write_hw_to_preset(self, name):
        self.read_fancurve_from_hw()
        self.save_fancurve_to_preset(name)

    def fancurve_write_file_to_hw(self, filename: str):
        self.fan_curve = FanCurve.load_from_file(filename)
        self.write_fancurve_to_hw()

    def fancurve_write_hw_to_file(self, filename: str):
        self.read_fancurve_from_hw()
        self.fan_curve.save_to_file(filename)

    def fancurve_write_preset_for_current_profile(self):
        is_on_powersupply = self.on_power_supply.get()
        profile = self.platform_profile.get()
        preset_name = self.fancurve_repo.get_preset_name(
            profile, is_on_powersupply)
        print(
            f"Loading preset={preset_name} for profile={profile} and is_powersupply={is_on_powersupply}")
        if preset_name in self.fancurve_repo.fancurve_presets:
            fancurve = self.fancurve_repo.load_by_name_or_default(preset_name)
            self.fancurve_io.write_fan_curve(fancurve)
            print(fancurve)
