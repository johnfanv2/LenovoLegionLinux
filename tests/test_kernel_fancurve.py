"""Compile the driver's actual capability functions with hardware-free fixtures.

These tests check configuration/dispatch, not firmware behavior. No kernel module
is loaded and no EC/WMI I/O occurs. Keep expected schemas independent of the
implementation so accidentally exposing a discarded field fails CI.
"""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "kernel_module/legion-laptop.c"


def declaration(source, start):
    return re.search(r"^" + re.escape(start) + r".*?^}(?: __packed)?;", source, re.M | re.S)[0]


def function(source, name):
    match = re.search(r"^static\s+[\w\s*]+\b" + name + r"\s*\([^;{}]*\)\s*\{", source, re.M)
    end = source.index("\n}", match.end()) + len("\n}")
    return source[match.start() : end]


class KernelFanCurveTest(unittest.TestCase):
    def test_capabilities_and_units(self):
        source = SOURCE.read_text()
        code = [
            r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t phys_addr_t;
typedef unsigned short umode_t;
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define pr_info(...) ((void)0)
#define dev_info(...) ((void)0)
#define sysfs_emit sprintf
#define min(a, b) ((a) < (b) ? (a) : (b))
#define clamp_t(type, value, low, high) ((type)((value) < (low) ? (low) : ((value) > (high) ? (high) : (value))))
#define __packed __attribute__((packed))
#define U8_MAX UINT8_MAX
#define print_hex_dump(...) ((void)0)
"""
        ]
        for name, value in re.findall(r"^#define (\w+)\s+([^\n]+)", source, re.M):
            if name.startswith(
                (
                    "WMI_GUID_",
                    "MINIFANCUVE_ON_COOL_",
                    "EC_LOCKFANCONTROLLER_",
                    "MAXFANCURVESIZE",
                    "FANCURVESIZE_",
                    "EC4_",
                    "FANTABLE_MAX_LEVELS",
                    "FANTABLE_SENSOR_",
                    "MAX_FAN_LEVEL",
                    "WMI_METHOD_ID_FAN_SET_TABLE",
                    "WMI_METHOD_ID_GETTHERMALMODE",
                    "LEGION_WMI_GAMEZONE_GUID",
                )
            ):
                code.append(f"#define {name} {value}")
        for start in (
            "struct ec_register_offsets {",
            "enum access_method {",
            "enum acpi_paths_inventory_ids {",
            "struct model_config {",
            "enum fan_speed_unit {",
            "enum FANCURVE_ATTR {",
            "struct fancurve_point {",
            "struct fancurve {",
            "enum legion_wmi_powermode {",
            "struct fantable_ladder {",
            "struct wmi_fantable_row {",
        ):
            code.append(declaration(source, start))
        code.append(re.search(r"static const u8 fancurve_level_min\[.*?;", source, re.S)[0])
        for kind in ("ec_register_offsets", "model_config"):
            code.extend(re.findall(r"^static const struct " + kind + r" \w+\s*=\s*\{.*?^\s*};", source, re.M | re.S))
        code.append(
            r"""
struct attribute { umode_t mode; };
struct device;
struct device_attribute {
    struct attribute attr;
    ssize_t (*show)(struct device *, struct device_attribute *, char *);
};
struct sensor_device_attribute_2 { struct device_attribute dev_attr; int nr; int index; };
#define to_sensor_dev_attr_2(attr) container_of(attr, struct sensor_device_attribute_2, dev_attr)
struct ecram { int unused; };
struct legion_private {
    const struct model_config *conf;
    struct ecram ecram;
    struct fancurve fancurve;
    bool fancurve_valid;
    int current_powermode, fantable_powermode;
    bool fantable_fan1_valid, fantable_fan2_valid;
    struct fantable_ladder fantable_fan1, fantable_fan2;
};
struct device { struct legion_private *priv; };
struct kobject { struct device *dev; };
static struct device *kobj_to_dev(struct kobject *kobj) { return kobj->dev; }
static struct legion_private *dev_get_drvdata(struct device *dev) { return dev->priv; }
static ssize_t autopoint_show(struct device *dev, struct device_attribute *attr, char *buf) { return 0; }
static bool have_guid = true;
static bool wmi_has_guid(const char *guid) { return have_guid; }
static bool legion_rapidcharge_is_supported(struct legion_private *priv) { return true; }
static bool legion_attribute_uses_cpu_wmi(const struct attribute *attr) { return false; }
static bool legion_attribute_uses_gpu_wmi(const struct attribute *attr) { return false; }
static ssize_t wmi_read_fancurve_custom(const struct model_config *model, struct fancurve *curve) { return -EIO; }
static int power_mode, power_error, power_reads, thermal_reads, wmi_calls;
static unsigned long thermal_mode;
static u8 last_payload[0x40];
static struct wmi_fantable_row firmware_rows[4];
static int failed_row = -1;
static int wmi_instance_count(const char *guid) { return 4; }
static int wmi_query_fantable_row(u8 index, struct wmi_fantable_row *row) {
    if (index == failed_row) return -EIO;
    *row = firmware_rows[index];
    return 0;
}
static ssize_t read_powermode(struct legion_private *priv, int *mode) {
    power_reads++;
    *mode = power_mode;
    return power_error;
}
static int wmi_exec_noarg_int(const char *guid, int instance, int method, unsigned long *mode) {
    assert(method == WMI_METHOD_ID_GETTHERMALMODE);
    thermal_reads++;
    *mode = thermal_mode;
    return power_error;
}
static int wmi_exec_arg(const char *guid, int instance, int method, u8 *data, size_t size) {
    assert(size <= sizeof(last_payload));
    memcpy(last_payload, data, size);
    wmi_calls++;
    return 0;
}
static int io_count;
static int ecram_read(struct ecram *ram, u16 offset) { io_count++; return 0; }
static void ecram_write(struct ecram *ram, u16 offset, u8 value) { io_count++; }
"""
        )
        names = (
            "fancurve_init",
            "fancurve_attr_supported",
            "ec_read_fancurve_legion",
            "ec_read_fancurve_ideapad",
            "ec_read_fancurve_loq",
            "ec_read_fancurve_legion2024",
            "read_fancurve",
            "wmi_fancurve_speed_unit",
            "fantable_row_to_ladder",
            "fancurve_level_table_sanitize",
            "read_fan_control_mode",
            "wmi_fancurve_mode",
            "fanfullspeed_write_allowed",
            "fantable_row_matches_mode",
            "fantable_refresh",
            "sync_powermode_locked",
            "fantable_ensure",
            "wmi_write_fancurve_custom",
            "wmi_write_fancurve_defaults",
            "minifancurve_supported",
            "lockfancontroller_supported",
            "ec_read_minifancurve",
            "ec_write_minifancurve",
            "ec_read_lockfancontroller",
            "ec_write_lockfancontroller",
            "legion_hwmon_fancurve_is_visible",
            "legion_sysfs_is_visible",
            "fancurve_speed_unit_show",
        )
        functions = "\n".join(function(source, name) for name in names)
        point_attrs = re.findall(r"SENSOR_DEVICE_ATTR_2_RW\((\w+),\s*autopoint,\s*(\w+),\s*(\d+)\)", source)
        for name, field, index in point_attrs:
            code.append(
                f"static struct sensor_device_attribute_2 sensor_dev_attr_{name} = "
                f"{{{{{{0644}}, autopoint_show}}, {field}, {index}}};"
            )
        declared = {f"sensor_dev_attr_{name}" for name, _, _ in point_attrs}
        for name in sorted(set(re.findall(r"\bsensor_dev_attr_\w+", functions)) - declared):
            code.append(f"static struct sensor_device_attribute_2 {name} = {{{{{{0644}}, NULL}}, 0, 0}};")
        for name in sorted(set(re.findall(r"\bdev_attr_\w+", functions))):
            code.append(f"static struct device_attribute {name} = {{{{0644}}, NULL}};")
        code.append(functions)
        code.append("static struct sensor_device_attribute_2 *points[] = {")
        code.extend(f"&sensor_dev_attr_{name}," for name, _, _ in point_attrs)
        code.append("};")
        code.append(
            r"""
int main(void) {
    struct model_config conf = model_v0;
    struct legion_private priv = { .conf = &conf };
    struct device dev = { &priv };
    struct kobject kobj = { &dev };
    const enum access_method methods[] = {
        ACCESS_METHOD_EC, ACCESS_METHOD_EC2, ACCESS_METHOD_EC3,
        ACCESS_METHOD_EC4, ACCESS_METHOD_WMI3, ACCESS_METHOD_NO_ACCESS
    };
    size_t cases = 0;
    for (size_t m = 0; m < sizeof(methods) / sizeof(methods[0]); m++) {
        conf.access_method_fancurve = methods[m];
        for (size_t p = 0; p < sizeof(points) / sizeof(points[0]); p++) {
            int id = points[p]->nr;
            bool expected = false;
            switch (methods[m]) {
            case ACCESS_METHOD_EC: expected = true; break;
            case ACCESS_METHOD_EC2:
                expected = id == FANCURVE_ATTR_PWM1 || id == FANCURVE_ATTR_PWM2 ||
                    id == FANCURVE_ATTR_CPU_TEMP || id == FANCURVE_ATTR_CPU_HYST ||
                    id == FANCURVE_ATTR_GPU_TEMP || id == FANCURVE_ATTR_GPU_HYST;
                break;
            case ACCESS_METHOD_EC3:
                expected = id != FANCURVE_ATTR_ACCEL && id != FANCURVE_ATTR_DECEL; break;
            case ACCESS_METHOD_EC4:
                expected = id == FANCURVE_ATTR_PWM1 || id == FANCURVE_ATTR_PWM2 ||
                    id == FANCURVE_ATTR_CPU_TEMP || id == FANCURVE_ATTR_GPU_TEMP; break;
            case ACCESS_METHOD_WMI3: expected = id == FANCURVE_ATTR_PWM1; break;
            default: break;
            }
            if (id == FANCURVE_SIZE) expected = methods[m] != ACCESS_METHOD_NO_ACCESS;
            umode_t mode = expected ? points[p]->dev_attr.attr.mode : 0;
            if (id == FANCURVE_SIZE && methods[m] != ACCESS_METHOD_EC) mode &= ~0222;
            assert(legion_hwmon_fancurve_is_visible(&kobj, &points[p]->dev_attr.attr, 0) == mode);
            cases++;
        }
    }
    /* Poisoned stack memory must not leak into native curve PWM scaling. */
    for (size_t m = 0; m < 4; m++) {
        conf.access_method_fancurve = methods[m];
        const u16 maxima[] = {0, 5100};
        for (size_t r = 0; r < sizeof(maxima) / sizeof(maxima[0]); r++) {
            struct fancurve curve;
            memset(&curve, 0xff, sizeof(curve));
            conf.fan_max_rpm = maxima[r];
            assert(read_fancurve(&priv, &curve) == 0);
            assert(curve.max_rpm == maxima[r]);
            assert(curve.fan_speed_unit == FAN_SPEED_UNIT_RPM_HUNDRED);
            if (methods[m] == ACCESS_METHOD_EC2)
                assert(curve.points[MAXFANCURVESIZE - 1].speed1 == 0);
        }
    }
    io_count = 0;
    char unit[32];
    conf = model_r3cn;
    priv.conf = &model_r3cn;
    assert(conf.access_method_fancurve == ACCESS_METHOD_EC3);
    assert(conf.access_method_temperature == ACCESS_METHOD_WMI3);
    assert(conf.fanfullspeed_requires_custom_powermode);
    fancurve_speed_unit_show(&dev, NULL, unit);
    assert(strcmp(unit, "rpm\n") == 0);
    assert(!legion_sysfs_is_visible(&kobj, &dev_attr_fan1_level_rpm_table.attr, 0));
    conf = model_lpcn; /* Defaults support must not turn percentages into levels. */
    conf.has_fancurve_defaults = true;
    priv.conf = &conf;
    fancurve_speed_unit_show(&dev, NULL, unit);
    assert(strcmp(unit, "percent\n") == 0);
    assert(!legion_sysfs_is_visible(&kobj, &dev_attr_fan1_level_rpm_table.attr, 0));
    priv.conf = &model_t2cn;
    assert(strcmp(priv.conf->acpi_paths[ACPI_PATH_CFG], "\\_SB.PCI0.LPC0.EC0.VPC0._CFG") == 0);
    fancurve_speed_unit_show(&dev, NULL, unit);
    assert(strcmp(unit, "level\n") == 0);
    assert(legion_sysfs_is_visible(&kobj, &dev_attr_fan1_level_rpm_table.attr, 0));
    priv.conf = &model_m3cn_8227; /* Level calibration does not require default-reset support. */
    fancurve_speed_unit_show(&dev, NULL, unit);
    assert(strcmp(unit, "level\n") == 0);
    assert(legion_sysfs_is_visible(&kobj, &dev_attr_fan1_level_rpm_table.attr, 0));
    assert(legion_hwmon_fancurve_is_visible(&kobj, &sensor_dev_attr_auto_points_size.dev_attr.attr, 0) == 0444);
    have_guid = false;
    assert(!legion_sysfs_is_visible(&kobj, &dev_attr_fan1_level_rpm_table.attr, 0));
    assert(legion_sysfs_is_visible(&kobj, &dev_attr_fancurve_speed_unit.attr, 0));

    /* Calibration must preserve level 1's zero RPM and all subsequent indices. */
    struct wmi_fantable_row row = {
        .fan_table_len = FANTABLE_MAX_LEVELS,
        .fan_speed = {0, 1300, 1700, 2100, 2500, 3100, 3400, 3800, 4200, 4600},
    };
    struct fantable_ladder ladder;
    const struct wmi_fantable_row valid_row = row;
    assert(fantable_row_to_ladder(&row, &ladder));
    assert(ladder.level_count == FANTABLE_MAX_LEVELS);
    assert(ladder.rpms[0] == 0 && ladder.rpms[1] == 1300 && ladder.rpms[9] == 4600);
    row.fan_speed[2] = row.fan_speed[1];
    assert(fantable_row_to_ladder(&row, &ladder));
    row.fan_speed[2] = row.fan_speed[1] - 1;
    assert(!fantable_row_to_ladder(&row, &ladder));
    row.fan_table_len = FANTABLE_MAX_LEVELS + 1;
    assert(!fantable_row_to_ladder(&row, &ladder));

    struct fancurve requested = { .fan_speed_unit = FAN_SPEED_UNIT_LEVEL };
    for (size_t p = 0; p < MAXFANCURVESIZE; p++) requested.points[p].speed1 = 2;
    priv.conf = &model_t2cn;
    power_mode = LEGION_WMI_POWERMODE_CUSTOM;
    thermal_mode = LEGION_WMI_POWERMODE_CUSTOM;
    assert(wmi_write_fancurve_custom(&priv, &requested) == 0);
    assert(wmi_calls == 1 && last_payload[0] == LEGION_WMI_POWERMODE_CUSTOM);
    assert(last_payload[6] == 2 && last_payload[0x18] == fancurve_level_min[9]);
    /* Saved SmartFanMode may still say custom while GZ44 is extreme. */
    thermal_mode = LEGION_WMI_POWERMODE_MAX_POWER;
    assert(power_mode == LEGION_WMI_POWERMODE_CUSTOM);
    assert(wmi_write_fancurve_custom(&priv, &requested) == -EOPNOTSUPP);
    assert(wmi_write_fancurve_defaults(&priv, LEGION_WMI_POWERMODE_CUSTOM) == -EOPNOTSUPP);
    assert(wmi_calls == 1);
    power_error = -EIO;
    assert(wmi_write_fancurve_custom(&priv, &requested) == -EIO);
    assert(wmi_calls == 1);
    priv.conf = &model_m3cn_8227;
    assert(wmi_write_fancurve_custom(&priv, &requested) == -EIO);
    power_error = 0;
    power_mode = LEGION_WMI_POWERMODE_BALANCED;
    assert(wmi_write_fancurve_custom(&priv, &requested) == 0);
    assert(wmi_calls == 2 && last_payload[0] == LEGION_WMI_POWERMODE_BALANCED);
    priv.conf = &model_r3cn;
    power_mode = LEGION_WMI_POWERMODE_CUSTOM;
    thermal_mode = LEGION_WMI_POWERMODE_MAX_POWER;
    assert(fanfullspeed_write_allowed(&priv, true) == -EBUSY);
    assert(fanfullspeed_write_allowed(&priv, false) == 0);
    assert(wmi_write_fancurve_defaults(&priv, LEGION_WMI_POWERMODE_CUSTOM) == -EOPNOTSUPP);
    assert(wmi_calls == 2);
    thermal_mode = (unsigned long)U8_MAX + LEGION_WMI_POWERMODE_CUSTOM + 1;
    assert(fanfullspeed_write_allowed(&priv, true) == -ERANGE);
    thermal_mode = LEGION_WMI_POWERMODE_CUSTOM;
    power_error = -EIO;
    assert(fanfullspeed_write_allowed(&priv, true) == -EIO);
    assert(fanfullspeed_write_allowed(&priv, false) == 0);
    power_error = 0;
    assert(fanfullspeed_write_allowed(&priv, true) == 0);
    assert(wmi_write_fancurve_defaults(&priv, LEGION_WMI_POWERMODE_CUSTOM) == 0);
    assert(wmi_calls == 3 && last_payload[0] == LEGION_WMI_POWERMODE_CUSTOM);
    priv.conf = &model_kwcn;
    power_reads = thermal_reads = 0;
    assert(wmi_fancurve_mode(&priv) == 0 && power_reads == 0 && thermal_reads == 0);

    /* T2CN calibration must use the same live mode as its SFAN payload. */
    firmware_rows[0] = valid_row;
    firmware_rows[0].mode = 0x100;
    firmware_rows[0].fan_id = 1;
    firmware_rows[0].sensor_id = FANTABLE_SENSOR_CPU;
    firmware_rows[1] = firmware_rows[0];
    firmware_rows[1].mode = LEGION_WMI_POWERMODE_BALANCED;
    for (size_t i = 1; i < FANTABLE_MAX_LEVELS; i++) firmware_rows[1].fan_speed[i] += 100;
    firmware_rows[2] = firmware_rows[0];
    firmware_rows[3] = firmware_rows[1];
    for (size_t i = 2; i < 4; i++) {
        firmware_rows[i].fan_id = 2;
        firmware_rows[i].sensor_id = FANTABLE_SENSOR_GPU;
    }
    priv.conf = &model_t2cn;
    power_mode = LEGION_WMI_POWERMODE_CUSTOM;
    thermal_mode = LEGION_WMI_POWERMODE_BALANCED;
    assert(fantable_ensure(&priv) == 0);
    assert(priv.fantable_powermode == LEGION_WMI_POWERMODE_BALANCED);
    assert(priv.fantable_fan1.rpms[1] == valid_row.fan_speed[1] + 100);
    thermal_mode = LEGION_WMI_POWERMODE_CUSTOM;
    failed_row = 0;
    assert(fantable_ensure(&priv) == 0);
    assert(!priv.fantable_fan1_valid && priv.fantable_fan2_valid);
    failed_row = -1;
    assert(fantable_ensure(&priv) == 0); /* Retry a partial refresh, even in the same mode. */
    assert(priv.fantable_fan1_valid && priv.fantable_fan2_valid);
    assert(priv.fantable_fan1.rpms[1] == valid_row.fan_speed[1]);
    thermal_mode = LEGION_WMI_POWERMODE_LOW_POWER;
    assert(fantable_ensure(&priv) == -ENODATA); /* Never use another mode's ladder. */
    thermal_mode = LEGION_WMI_POWERMODE_MAX_POWER;
    assert(fantable_ensure(&priv) == -EOPNOTSUPP);
    priv.conf = &model_m3cn_8227;
    priv.fantable_fan1_valid = priv.fantable_fan2_valid = true;
    priv.current_powermode = priv.fantable_powermode = LEGION_WMI_POWERMODE_CUSTOM;
    power_error = -EIO;
    assert(fantable_ensure(&priv) == -EIO); /* Do not trust a cache after a failed mode read. */
    power_error = 0;

    /* A stale model flag must never cause reads/writes to a placeholder offset. */
    const struct ec_register_offsets *unmapped[] = {
        &ec_register_offsets_ideapad_v0, &ec_register_offsets_ideapad_v1,
        &ec_register_offsets_loq_v0, &ec_register_offsets_loq_v1
    };
    struct ecram ram = {0};
    bool state;
    conf = model_v0;
    priv.conf = &conf;
    for (size_t i = 0; i < sizeof(unmapped) / sizeof(unmapped[0]); i++) {
        conf.registers = unmapped[i];
        assert(!minifancurve_supported(&conf));
        assert(!lockfancontroller_supported(&conf));
        assert(ec_read_minifancurve(&ram, &conf, &state) == -EOPNOTSUPP);
        assert(ec_write_minifancurve(&ram, &conf, true) == -EOPNOTSUPP);
        assert(ec_read_lockfancontroller(&ram, &conf, &state) == -EOPNOTSUPP);
        assert(ec_write_lockfancontroller(&ram, &conf, true) == -EOPNOTSUPP);
        assert(io_count == 0);
        assert(!legion_hwmon_fancurve_is_visible(&kobj, &sensor_dev_attr_minifancurve.dev_attr.attr, 0));
        assert(!legion_sysfs_is_visible(&kobj, &dev_attr_lockfancontroller.attr, 0));
    }
    conf = model_v0;
    assert(minifancurve_supported(&conf) && lockfancontroller_supported(&conf));
    assert(ec_write_minifancurve(&ram, &conf, true) == 0);
    assert(ec_write_lockfancontroller(&ram, &conf, true) == 0);
    assert(io_count == 2);
    printf("PASS: %zu point-attribute cases, unit gates and guarded EC controls\n", cases);
    return 0;
}
"""
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "fancurve.c")
            binary = Path(directory, "fancurve")
            path.write_text("\n".join(code))
            subprocess.run(
                [
                    os.environ.get("CC", "gcc"),
                    "-std=gnu11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wno-unused-parameter",
                    "-Wno-unused-const-variable",
                    str(path),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            subprocess.run([str(binary)], check=True)
