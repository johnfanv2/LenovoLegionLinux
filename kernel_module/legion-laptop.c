// SPDX-License-Identifier: GPL-2.0-or-later
/*
 *  legion-laptop.c - Extra Lenovo Legion laptop support, in
 *   particular for fan curve control and power mode.
 *
 *  Copyright (C) 2022 johnfan <johnfan (at) example (dot) com>
 *
 *
 *  This driver might work on other Lenovo Legion models. If you
 *  want to try it you can pass force=1 as argument
 *  to the module which will force it to load even when the DMI
 *  data doesn't match the model AND FIRMWARE.
 *
 *  Support for other hardware of this model is already partially
 *  provided by the module ideapd-laptop.
 *
 *  The development page for this driver is located at
 *  https://github.com/johnfanv2/LenovoLegionLinux
 *
 *  This driver exports the files:
 *    - /sys/kernel/debug/legion/fancurve (ro)
 *        The fan curve in the form stored in the firmware in an
 *        human readable table.
 *
 *    - /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/powermode (rw)
 *       0: balanced mode (white)
 *       1: performance mode (red)
 *       2: quiet mode (blue)
 *       ?: custom mode (pink)
 *
 *  NOTE: Writing to this will load the default fan curve from
 *        the firmware for this mode, so the fan curve might
 *        have to be reconfigured if needed.
 *
 *  It implements the usual hwmon interface to monitor fan speed and temmperature
 *  and allows to set the fan curve inside the firware.
 *
 *    - /sys/class/hwmon/X/fan1_input or /sys/class/hwmon/X/fan2_input  (ro)
 *        Current fan speed of fan1/fan2.
 *    - /sys/class/hwmon/X/temp1_input (ro)
 *    - /sys/class/hwmon/X/temp2_input (ro)
 *    - /sys/class/hwmon/X/temp3_input (ro)
 *        Temperature (Celsius) of CPU, GPU, and IC used for fan control.
 *    - /sys/class/hwmon/X/pwmY_auto_pointZ_pwm (rw)
 *          PWM (0-255) of the fan at the Y-level in the fan curve
 *    - /sys/class/hwmon/X/pwmY_auto_pointZ_temp (rw)
 *          upper temperature of tempZ (CPU, GPU, or IC) at the Y-level in the fan curve
 *    - /sys/class/hwmon/X/pwmY_auto_pointZ_temp_hyst (rw)
 *          hysteris (CPU, GPU, or IC) at the Y-level in the fan curve. The lower
 *          temperatue of the level is the upper temperature minus the hysteris
 *
 *
 *  Credits for reverse engineering the firmware to:
 *      - David Woodhouse: heavily inspired by lenovo_laptop.c
 *      - Luke Cama: Windows version "LegionFanControl"
 *      - SmokelessCPU: reverse engineering of custom registers in EC
 *                      and commincation method with EC via ports
 *      - 0x1F9F1: additional reverse engineering for complete fan curve
 */
#define pr_fmt(fmt) KBUILD_MODNAME ": " fmt

#include <linux/acpi.h>
#include <asm/io.h>
#include <linux/debugfs.h>
#include <linux/delay.h>
#include <linux/dmi.h>
#include <linux/leds.h>
#include <linux/hwmon.h>
#include <linux/hwmon-sysfs.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/platform_device.h>
#include <linux/platform_profile.h>
#include <linux/types.h>
#include <linux/wmi.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("johnfan");
MODULE_DESCRIPTION("Lenovo Legion laptop extras");

static bool force;
module_param(force, bool, 0440);
MODULE_PARM_DESC(
	force,
	"Force loading this module even if model or BIOS does not match.");

static bool ec_readonly;
module_param(ec_readonly, bool, 0440);
MODULE_PARM_DESC(
	ec_readonly,
	"Only read from embedded controller but do not write or change settings.");

static bool enable_platformprofile = true;
module_param(enable_platformprofile, bool, 0440);
MODULE_PARM_DESC(
	enable_platformprofile,
	"Enable the platform profile sysfs API to read and write the power mode.");

#define LEGIONFEATURES \
	"fancurve powermode platformprofile platformprofilenotify minifancurve"

//Size of fancurve stored in embedded controller
#define MAXFANCURVESIZE 10

#define LEGION_DRVR_SHORTNAME "legion"
#define LEGION_HWMON_NAME LEGION_DRVR_SHORTNAME "_hwmon"

struct legion_private;

/* =============================== */
/* Embedded Controller Description */
/* =============================== */

/* The configuration and registers to access the embedded controller
 * depending on different the version of the software on the
 * embedded controller or and the BIOS/UEFI firmware.
 *
 * To control fan curve in the embedded controller (EC) one has to
 * write to its "RAM". There are different possibilities:
 *  - EC RAM is memory mapped (write to it with ioremap)
 *  - access EC RAM via ported mapped IO (outb/inb)
 *  - access EC RAM via ACPI methods. It is only possible to write
 *    to part of it (first 0xFF bytes?)
 *
 * In later models the firmware directly exposes ACPI methods to
 * set the fan curve direclty, without writing to EC RAM. This
 * is done inside the ACPI method.
 */

/**
 * Offsets for interseting values inside the EC RAM  (0 = start of
 * EC RAM. These might change depending on the software inside of
 * the EC, which can be updated by a BIOS update from Lenovo.
 */
// TODO: same order as in initialization
struct ec_register_offsets {
	// Super I/O Configuration Registers
	// 7.15 General Control (GCTRL)
	// General Control (GCTRL)
	// (see EC Interface Registers  and 6.2 Plug and Play Configuration (PNPCFG)) in datasheet
	// note: these are in two places saved
	// in EC Interface Registers  and in super io configuraion registers
	// Chip ID
	u16 ECHIPID1;
	u16 ECHIPID2;
	// Chip Version
	u16 ECHIPVER;
	u16 ECDEBUG;

	// Lenovo Custom OEM extension
	// Firmware of ITE can be extended by
	// custom program using its own "variables"
	// These are the offsets to these "variables"
	u16 EXT_FAN_CUR_POINT;
	u16 EXT_FAN_POINTS_SIZE;
	u16 EXT_FAN1_BASE;
	u16 EXT_FAN2_BASE;
	u16 EXT_FAN_ACC_BASE;
	u16 EXT_FAN_DEC_BASE;
	u16 EXT_CPU_TEMP;
	u16 EXT_CPU_TEMP_HYST;
	u16 EXT_GPU_TEMP;
	u16 EXT_GPU_TEMP_HYST;
	u16 EXT_VRM_TEMP;
	u16 EXT_VRM_TEMP_HYST;
	u16 EXT_FAN1_RPM_LSB;
	u16 EXT_FAN1_RPM_MSB;
	u16 EXT_FAN2_RPM_LSB;
	u16 EXT_FAN2_RPM_MSB;
	u16 EXT_FAN1_TARGET_RPM;
	u16 EXT_FAN2_TARGET_RPM;
	u16 EXT_POWERMODE;
	u16 EXT_MINIFANCURVE_ON_COOL;
	// values
	// 0x04: enable mini fan curve if very long on cool level
	//      - this might be due to potential temp failure
	//      - or just because really so cool
	// 0xA0: disable it
	u16 EXT_LOCKFANCONTROLLER;
	u16 EXT_MAXIMUMFANSPEED;
	u16 EXT_WHITE_KEYBOARD_BACKLIGHT;
	u16 EXT_IC_TEMP_INPUT;
	u16 EXT_CPU_TEMP_INPUT;
	u16 EXT_GPU_TEMP_INPUT;
};

enum access_method {
	ACCESS_METHOD_NO_ACCESS = 0,
	ACCESS_METHOD_EC = 1,
	ACCESS_METHOD_ACPI = 2,
	ACCESS_METHOD_WMI = 3,
	ACCESS_METHOD_WMI2 = 4,
	ACCESS_METHOD_WMI3 = 5,
	ACCESS_METHOD_EC2 = 10, // ideapad fancurve method
};

struct model_config {
	const struct ec_register_offsets *registers;
	bool check_embedded_controller_id;
	u16 embedded_controller_id;

	// first addr in EC we access/scan
	phys_addr_t memoryio_physical_ec_start;
	size_t memoryio_size;

	// TODO: maybe use bitfield
	bool has_minifancurve;
	bool has_custom_powermode;
	enum access_method access_method_powermode;

	enum access_method access_method_keyboard;
	enum access_method access_method_temperature;
	enum access_method access_method_fanspeed;
	enum access_method access_method_fancurve;
	enum access_method access_method_fanfullspeed;
	bool three_state_keyboard;

	bool acpi_check_dev;

	phys_addr_t ramio_physical_start;
	size_t ramio_size;
};

/* =================================== */
/* Configuration for different models */
/* =================================== */

// Idea by SmokelesssCPU (modified)
// - all default names and register addresses are supported by datasheet
// - register addresses for custom firmware by SmokelesssCPU
static const struct ec_register_offsets ec_register_offsets_v0 = {
	.ECHIPID1 = 0x2000,
	.ECHIPID2 = 0x2001,
	.ECHIPVER = 0x2002,
	.ECDEBUG = 0x2003,
	.EXT_FAN_CUR_POINT = 0xC534,
	.EXT_FAN_POINTS_SIZE = 0xC535,
	.EXT_FAN1_BASE = 0xC540,
	.EXT_FAN2_BASE = 0xC550,
	.EXT_FAN_ACC_BASE = 0xC560,
	.EXT_FAN_DEC_BASE = 0xC570,
	.EXT_CPU_TEMP = 0xC580,
	.EXT_CPU_TEMP_HYST = 0xC590,
	.EXT_GPU_TEMP = 0xC5A0,
	.EXT_GPU_TEMP_HYST = 0xC5B0,
	.EXT_VRM_TEMP = 0xC5C0,
	.EXT_VRM_TEMP_HYST = 0xC5D0,
	.EXT_FAN1_RPM_LSB = 0xC5E0,
	.EXT_FAN1_RPM_MSB = 0xC5E1,
	.EXT_FAN2_RPM_LSB = 0xC5E2,
	.EXT_FAN2_RPM_MSB = 0xC5E3,
	.EXT_MINIFANCURVE_ON_COOL = 0xC536,
	.EXT_LOCKFANCONTROLLER = 0xc4AB,
	.EXT_CPU_TEMP_INPUT = 0xc538,
	.EXT_GPU_TEMP_INPUT = 0xc539,
	.EXT_IC_TEMP_INPUT = 0xC5E8,
	.EXT_POWERMODE = 0xc420,
	.EXT_FAN1_TARGET_RPM = 0xc600,
	.EXT_FAN2_TARGET_RPM = 0xc601,
	.EXT_MAXIMUMFANSPEED = 0xBD,
	.EXT_WHITE_KEYBOARD_BACKLIGHT = (0x3B + 0xC400)
};

static const struct ec_register_offsets ec_register_offsets_v1 = {
	.ECHIPID1 = 0x2000,
	.ECHIPID2 = 0x2001,
	.ECHIPVER = 0x2002,
	.ECDEBUG = 0x2003,
	.EXT_FAN_CUR_POINT = 0xC534,
	.EXT_FAN_POINTS_SIZE = 0xC535,
	.EXT_FAN1_BASE = 0xC540,
	.EXT_FAN2_BASE = 0xC550,
	.EXT_FAN_ACC_BASE = 0xC560,
	.EXT_FAN_DEC_BASE = 0xC570,
	.EXT_CPU_TEMP = 0xC580,
	.EXT_CPU_TEMP_HYST = 0xC590,
	.EXT_GPU_TEMP = 0xC5A0,
	.EXT_GPU_TEMP_HYST = 0xC5B0,
	.EXT_VRM_TEMP = 0xC5C0,
	.EXT_VRM_TEMP_HYST = 0xC5D0,
	.EXT_FAN1_RPM_LSB = 0xC5E0,
	.EXT_FAN1_RPM_MSB = 0xC5E1,
	.EXT_FAN2_RPM_LSB = 0xC5E2,
	.EXT_FAN2_RPM_MSB = 0xC5E3,
	.EXT_MINIFANCURVE_ON_COOL = 0xC536,
	.EXT_LOCKFANCONTROLLER = 0xc4AB,
	.EXT_CPU_TEMP_INPUT = 0xc538,
	.EXT_GPU_TEMP_INPUT = 0xc539,
	.EXT_IC_TEMP_INPUT = 0xC5E8,
	.EXT_POWERMODE = 0xc41D,
	.EXT_FAN1_TARGET_RPM = 0xc600,
	.EXT_FAN2_TARGET_RPM = 0xc601,
	.EXT_MAXIMUMFANSPEED = 0xBD,
	.EXT_WHITE_KEYBOARD_BACKLIGHT = (0x3B + 0xC400)
};

static const struct ec_register_offsets ec_register_offsets_ideapad_v0 = {
	.ECHIPID1 = 0x2000,
	.ECHIPID2 = 0x2001,
	.ECHIPVER = 0x2002,
	.ECDEBUG = 0x2003,
	.EXT_FAN_CUR_POINT = 0xC5a0, // not found yet
	.EXT_FAN_POINTS_SIZE = 0xC5a0, // constant 0
	.EXT_FAN1_BASE = 0xC5a0,
	.EXT_FAN2_BASE = 0xC5a8,
	.EXT_FAN_ACC_BASE = 0xC5a0, // not found yet
	.EXT_FAN_DEC_BASE = 0xC5a0, // not found yet
	.EXT_CPU_TEMP = 0xC550, // and repeated after 8 bytes
	.EXT_CPU_TEMP_HYST = 0xC590, // and repeated after 8 bytes
	.EXT_GPU_TEMP = 0xC5C0, // and repeated after 8 bytes
	.EXT_GPU_TEMP_HYST = 0xC5D0, // and repeated after 8 bytes
	.EXT_VRM_TEMP = 0xC5a0, // does not exists or not found
	.EXT_VRM_TEMP_HYST = 0xC5a0, // does not exists ot not found yet
	.EXT_FAN1_RPM_LSB = 0xC5a0, // not found yet
	.EXT_FAN1_RPM_MSB = 0xC5a0, // not found yet
	.EXT_FAN2_RPM_LSB = 0xC5a0, // not found yet
	.EXT_FAN2_RPM_MSB = 0xC5a0, // not found yet
	.EXT_MINIFANCURVE_ON_COOL = 0xC5a0, // does not exists or not found
	.EXT_LOCKFANCONTROLLER = 0xC5a0, // does not exists or not found
	.EXT_CPU_TEMP_INPUT = 0xC5a0, // not found yet
	.EXT_GPU_TEMP_INPUT = 0xC5a0, // not found yet
	.EXT_IC_TEMP_INPUT = 0xC5a0, // not found yet
	.EXT_POWERMODE = 0xC5a0, // not found yet
	.EXT_FAN1_TARGET_RPM = 0xC5a0, // not found yet
	.EXT_FAN2_TARGET_RPM = 0xC5a0, // not found yet
	.EXT_MAXIMUMFANSPEED = 0xC5a0, // not found yet
	.EXT_WHITE_KEYBOARD_BACKLIGHT = 0xC5a0 // not found yet
};

static const struct ec_register_offsets ec_register_offsets_ideapad_v1 = {
	.ECHIPID1 = 0x2000,
	.ECHIPID2 = 0x2001,
	.ECHIPVER = 0x2002,
	.ECDEBUG = 0x2003,
	.EXT_FAN_CUR_POINT = 0xC5a0, // not found yet
	.EXT_FAN_POINTS_SIZE = 0xC5a0, // constant 0
	.EXT_FAN1_BASE = 0xC5a0,
	.EXT_FAN2_BASE = 0xC5a8,
	.EXT_FAN_ACC_BASE = 0xC5a0, // not found yet
	.EXT_FAN_DEC_BASE = 0xC5a0, // not found yet
	.EXT_CPU_TEMP = 0xC550, // and repeated after 8 bytes
	.EXT_CPU_TEMP_HYST = 0xC590, // and repeated after 8 bytes
	.EXT_GPU_TEMP = 0xC5C0, // and repeated after 8 bytes
	.EXT_GPU_TEMP_HYST = 0xC5D0, // and repeated after 8 bytes
	.EXT_VRM_TEMP = 0xC5a0, // does not exists or not found
	.EXT_VRM_TEMP_HYST = 0xC5a0, // does not exists ot not found yet
	.EXT_FAN1_RPM_LSB = 0xC5a0, // not found yet
	.EXT_FAN1_RPM_MSB = 0xC5a0, // not found yet
	.EXT_FAN2_RPM_LSB = 0xC5a0, // not found yet
	.EXT_FAN2_RPM_MSB = 0xC5a0, // not found yet
	.EXT_MINIFANCURVE_ON_COOL = 0xC5a0, // does not exists or not found
	.EXT_LOCKFANCONTROLLER = 0xC5a0, // does not exists or not found
	.EXT_CPU_TEMP_INPUT = 0xC5a0, // not found yet
	.EXT_GPU_TEMP_INPUT = 0xC5a0, // not found yet
	.EXT_IC_TEMP_INPUT = 0xC5a0, // not found yet
	.EXT_POWERMODE = 0xC5a0, // not found yet
	.EXT_FAN1_TARGET_RPM = 0xC5a0, // not found yet
	.EXT_FAN2_TARGET_RPM = 0xC5a0, // not found yet
	.EXT_MAXIMUMFANSPEED = 0xC5a0, // not found yet
	.EXT_WHITE_KEYBOARD_BACKLIGHT = 0xC5a0 // not found yet
};

static const struct model_config model_v0 = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_j2cn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_9vcn = {
	.registers = &ec_register_offsets_ideapad_v1,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8226,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI,
	.access_method_temperature = ACCESS_METHOD_WMI,
	.access_method_fancurve = ACCESS_METHOD_EC2,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_v2022 = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_4gcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8226,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_bvcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8226,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI,
	.access_method_temperature = ACCESS_METHOD_WMI,
	.access_method_fancurve = ACCESS_METHOD_NO_ACCESS,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFC7E0800,
	.ramio_size = 0x600
};

static const struct model_config model_bhcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8226,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = false,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_ACPI,
	.access_method_fanspeed = ACCESS_METHOD_WMI,
	.access_method_temperature = ACCESS_METHOD_ACPI,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFF00D400,
	.ramio_size = 0x600
};

static const struct model_config model_kwcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x5507,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI3,
	.access_method_temperature = ACCESS_METHOD_WMI3,
	.access_method_fancurve = ACCESS_METHOD_WMI3,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE0B0400,
	.ramio_size = 0x600
};

static const struct model_config model_m2cn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI3,
	.access_method_temperature = ACCESS_METHOD_WMI3,
	.access_method_fancurve = ACCESS_METHOD_WMI3,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFE0B0400,
	.ramio_size = 0x600
};

static const struct model_config model_k1cn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x5263,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI3,
	.access_method_temperature = ACCESS_METHOD_WMI3,
	.access_method_fancurve = ACCESS_METHOD_WMI3,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE0B0400,
	.ramio_size = 0x600
};

static const struct model_config model_lpcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x5507,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI3,
	.access_method_temperature = ACCESS_METHOD_WMI3,
	.access_method_fancurve = ACCESS_METHOD_WMI3,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE0B0400,
	.ramio_size = 0x600
};

static const struct model_config model_kfcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_hacn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_k9cn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400, // or replace 0xC400 by 0x0400  ?
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_eucn = {
	.registers = &ec_register_offsets_v1,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_fccn = {
	.registers = &ec_register_offsets_ideapad_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI,
	.access_method_temperature = ACCESS_METHOD_ACPI,
	.access_method_fancurve = ACCESS_METHOD_EC2,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_h3cn = {
	//0xFE0B0800
	.registers = &ec_register_offsets_v1,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = false,
	.access_method_powermode = ACCESS_METHOD_WMI,
	// not implemented (properly) in WMI, RGB conrolled by USB
	.access_method_keyboard = ACCESS_METHOD_NO_ACCESS,
	// accessing fan speed is not implemented in ACPI
	// a variable in the operation region (or not found)
	// and not per WMI (methods returns constant 0)
	.access_method_fanspeed = ACCESS_METHOD_NO_ACCESS,
	.access_method_temperature = ACCESS_METHOD_WMI,
	.access_method_fancurve = ACCESS_METHOD_NO_ACCESS,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFE0B0800,
	.ramio_size = 0x600
};

static const struct model_config model_e9cn = {
	//0xFE0B0800
	.registers = &ec_register_offsets_v1,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400, //0xFC7E0800
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = false,
	.access_method_powermode = ACCESS_METHOD_WMI,
	// not implemented (properly) in WMI, RGB conrolled by USB
	.access_method_keyboard = ACCESS_METHOD_NO_ACCESS,
	// accessing fan speed is not implemented in ACPI
	// a variable in the operation region (or not found)
	// and not per WMI (methods returns constant 0)
	.access_method_fanspeed = ACCESS_METHOD_WMI,
	.access_method_temperature = ACCESS_METHOD_WMI,
	.access_method_fancurve = ACCESS_METHOD_NO_ACCESS,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFC7E0800,
	.ramio_size = 0x600
};

static const struct model_config model_8jcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8226,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_WMI,
	.access_method_temperature = ACCESS_METHOD_WMI,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFE00D400,
	.ramio_size = 0x600
};

static const struct model_config model_jncn = {
	.registers = &ec_register_offsets_v1,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false,
	.has_custom_powermode = false,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_NO_ACCESS,
	.access_method_fanspeed = ACCESS_METHOD_WMI,
	.access_method_temperature = ACCESS_METHOD_WMI,
	.access_method_fancurve = ACCESS_METHOD_NO_ACCESS,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFC7E0800,
	.ramio_size = 0x600
};

// Yoga Model!
static const struct model_config model_j1cn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE0B0400,
	.ramio_size = 0x600
};

// Yoga Model!
static const struct model_config model_dmcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_WMI,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = true,
	.ramio_physical_start = 0xFE700D00,
	.ramio_size = 0x600
};

// Yoga Model!
static const struct model_config model_khcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true,
	.has_custom_powermode = true,
	.access_method_powermode = ACCESS_METHOD_EC,
	.access_method_keyboard = ACCESS_METHOD_WMI,
	.access_method_fanspeed = ACCESS_METHOD_EC,
	.access_method_temperature = ACCESS_METHOD_EC,
	.access_method_fancurve = ACCESS_METHOD_EC,
	.access_method_fanfullspeed = ACCESS_METHOD_WMI,
	.acpi_check_dev = false,
	.ramio_physical_start = 0xFE0B0400,
	.ramio_size = 0x600
};


static const struct dmi_system_id denylist[] = { {} };

static const struct dmi_system_id optimistic_allowlist[] = {
	{
		// modelyear: 2021
		// generation: 6
		// name: Legion 5, Legion 5 pro, Legion 7
		// Family: Legion 5 15ACH6H, ...
		.ident = "GKCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "GKCN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2020
		.ident = "EUCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "EUCN"),
		},
		.driver_data = (void *)&model_eucn
	},
	{
		// modelyear: 2020
		.ident = "EFCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "EFCN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2020
		.ident = "FSCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "FSCN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2021
		.ident = "HHCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "HHCN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2022
		.ident = "H1CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "H1CN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2022
		.ident = "J2CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "J2CN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2022
		.ident = "JUCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "JUCN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2022
		.ident = "KFCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "KFCN"),
		},
		.driver_data = (void *)&model_kfcn
	},
	{
		// modelyear: 2021
		.ident = "HACN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "HACN"),
		},
		.driver_data = (void *)&model_hacn
	},
	{
		// modelyear: 2021
		.ident = "G9CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "G9CN"),
		},
		.driver_data = (void *)&model_v0
	},
	{
		// modelyear: 2022
		.ident = "K9CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "K9CN"),
		},
		.driver_data = (void *)&model_k9cn
	},
	{
		// e.g. IdeaPad Gaming 3 15ARH05
		.ident = "FCCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "FCCN"),
		},
		.driver_data = (void *)&model_fccn
	},
	{
		// e.g. Ideapad Gaming 3 15ACH6
		.ident = "H3CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "H3CN"),
		},
		.driver_data = (void *)&model_h3cn
	},
	{
		// e.g. IdeaPad Gaming 3 15ARH7 (2022)
		.ident = "JNCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "JNCN"),
		},
		.driver_data = (void *)&model_jncn
	},
	{
		// 2020, seems very different in ACPI dissassembly
		.ident = "E9CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "E9CN"),
		},
		.driver_data = (void *)&model_e9cn
	},
	{
		// e.g. Legion Y7000 (older version)
		.ident = "8JCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "8JCN"),
		},
		.driver_data = (void *)&model_8jcn
	},
	{
		// e.g. Legion 7i Pro 2023
		.ident = "KWCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "KWCN"),
		},
		.driver_data = (void *)&model_kwcn
	},
	{
		// e.g. Legion Pro 5 2023 or R9000P
		.ident = "LPCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "LPCN"),
		},
		.driver_data = (void *)&model_lpcn
	},
	{
		// e.g. Lenovo Legion 5i/Y7000 2019 PG0
		.ident = "BHCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "BHCN"),
		},
		.driver_data = (void *)&model_bhcn
	},
	{
		// e.g. Lenovo 7 16IAX7
		.ident = "K1CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "K1CN"),
		},
		.driver_data = (void *)&model_k1cn
	},
	{
		// e.g. Legion Y720
		.ident = "4GCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "4GCN"),
		},
		.driver_data = (void *)&model_4gcn
	},
	{
		// e.g. Legion Slim 5 16APH8 2023
		.ident = "M3CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "M3CN"),
		},
		.driver_data = (void *)&model_lpcn
	},
	{
		// e.g. Legion Y7000p-1060
		.ident = "9VCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "9VCN"),
		},
		.driver_data = (void *)&model_9vcn
	},
	{
		// e.g. Legion Y9000X
		.ident = "JYCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "JYCN"),
		},
		.driver_data = (void *)&model_v2022
	},
	{
		// e.g. Legion Y740-15IRH, older model e.g. with GTX 1660
		.ident = "BVCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "BVCN"),
		},
		.driver_data = (void *)&model_bvcn
	},
	{
		// e.g. Legion 5 Pro 16IAH7H with a RTX 3070 Ti
		.ident = "J2CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "J2CN"),
		},
		.driver_data = (void *)&model_j2cn
	},
	{
		// e.g. Lenovo Yoga 7 16IAH7 with GPU Intel DG2 Arc A370M
		.ident = "J1CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "J1CN"),
		},
		.driver_data = (void *)&model_j1cn
	},
	{
		// e.g. Legion Slim 5 16IRH8 (2023) with RTX 4070
		.ident = "M2CN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "M2CN"),
		},
		.driver_data = (void *)&model_m2cn
	},
	{
		// e.g. Yoga Slim 7-14ARE05
		.ident = "DMCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "DMCN"),
		},
		.driver_data = (void *)&model_dmcn
	},
	{
		// e.g. Yoga Slim 7 Pro 14ARH7
		.ident = "KHCN",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "KHCN"),
		},
		.driver_data = (void *)&model_khcn
	},
	{}
};

/* ================================= */
/* ACPI and WMI access               */
/* ================================= */

// function from ideapad-laptop.c
static int eval_int(acpi_handle handle, const char *name, unsigned long *res)
{
	unsigned long long result;
	acpi_status status;

	status = acpi_evaluate_integer(handle, (char *)name, NULL, &result);
	if (ACPI_FAILURE(status))
		return -EIO;

	*res = result;

	return 0;
}

// function from ideapad-laptop.c
static int exec_simple_method(acpi_handle handle, const char *name,
			      unsigned long arg)
{
	acpi_status status =
		acpi_execute_simple_method(handle, (char *)name, arg);

	return ACPI_FAILURE(status) ? -EIO : 0;
}

// function from ideapad-laptop.c
static int exec_sbmc(acpi_handle handle, unsigned long arg)
{
	// \_SB.PCI0.LPC0.EC0.VPC0.SBMC
	return exec_simple_method(handle, "VPC0.SBMC", arg);
}

//static int eval_qcho(acpi_handle handle, unsigned long *res)
//{
//	// \_SB.PCI0.LPC0.EC0.QCHO
//	return eval_int(handle, "QCHO", res);
//}

static int eval_gbmd(acpi_handle handle, unsigned long *res)
{
	return eval_int(handle, "VPC0.GBMD", res);
}

static int eval_spmo(acpi_handle handle, unsigned long *res)
{
	// \_SB.PCI0.LPC0.EC0.QCHO
	return eval_int(handle, "VPC0.BTSM", res);
}

static int acpi_process_buffer_to_ints(const char *id_name, int id_nr,
				       acpi_status status,
				       struct acpi_buffer *out_buffer, u8 *res,
				       size_t ressize)
{
	// seto to NULL call kfree on NULL if next function call fails
	union acpi_object *out = NULL;
	size_t i;
	int error = 0;

	if (ACPI_FAILURE(status)) {
		pr_info("ACPI evaluation error for: %s:%d\n", id_name, id_nr);
		error = -EFAULT;
		goto err;
	}

	out = out_buffer->pointer;
	if (!out) {
		pr_info("Unexpected ACPI result for %s:%d\n", id_name, id_nr);
		error = -AE_ERROR;
		goto err;
	}

	if (out->type != ACPI_TYPE_BUFFER || out->buffer.length != ressize) {
		pr_info("Unexpected ACPI result for %s:%d: expected type %d but got %d; expected length %lu but got %u;\n",
			id_name, id_nr, ACPI_TYPE_BUFFER, out->type, ressize,
			out->buffer.length);
		error = -AE_ERROR;
		goto err;
	}
	pr_info("ACPI result for %s:%d: ACPI buffer length: %u\n", id_name,
		id_nr, out->buffer.length);

	for (i = 0; i < ressize; ++i)
		res[i] = out->buffer.pointer[i];
	error = 0;

err:
	kfree(out);
	return error;
}

//static int exec_ints(acpi_handle handle, const char *method_name,
//		     struct acpi_object_list *params, u8 *res, size_t ressize)
//{
//	acpi_status status;
//	struct acpi_buffer out_buffer = { ACPI_ALLOCATE_BUFFER, NULL };

//	status = acpi_evaluate_object(handle, (acpi_string)method_name, params,
//				      &out_buffer);

//	return acpi_process_buffer_to_ints(method_name, 0, status, &out_buffer,
//					   res, ressize);
//}

static int wmi_exec_ints(const char *guid, u8 instance, u32 method_id,
			 const struct acpi_buffer *params, u8 *res,
			 size_t ressize)
{
	acpi_status status;
	struct acpi_buffer out_buffer = { ACPI_ALLOCATE_BUFFER, NULL };

	status = wmi_evaluate_method(guid, instance, method_id, params,
				     &out_buffer);
	return acpi_process_buffer_to_ints(guid, method_id, status, &out_buffer,
					   res, ressize);
}

static int wmi_exec_int(const char *guid, u8 instance, u32 method_id,
			const struct acpi_buffer *params, unsigned long *res)
{
	acpi_status status;
	struct acpi_buffer out_buffer = { ACPI_ALLOCATE_BUFFER, NULL };
	// seto to NULL call kfree on NULL if next function call fails
	union acpi_object *out = NULL;
	int error = 0;

	status = wmi_evaluate_method(guid, instance, method_id, params,
				     &out_buffer);

	if (ACPI_FAILURE(status)) {
		pr_info("WMI evaluation error for: %s:%d\n", guid, method_id);
		error = -EFAULT;
		goto err;
	}

	out = out_buffer.pointer;
	if (!out) {
		pr_info("Unexpected ACPI result for %s:%d", guid, method_id);
		error = -AE_ERROR;
		goto err;
	}

	if (out->type != ACPI_TYPE_INTEGER) {
		pr_info("Unexpected ACPI result for %s:%d: expected type %d but got %d\n",
			guid, method_id, ACPI_TYPE_INTEGER, out->type);
		error = -AE_ERROR;
		goto err;
	}

	*res = out->integer.value;
	error = 0;

err:
	kfree(out);
	return error;
}

static int wmi_exec_noarg_int(const char *guid, u8 instance, u32 method_id,
			      unsigned long *res)
{
	struct acpi_buffer params;

	params.length = 0;
	params.pointer = NULL;
	return wmi_exec_int(guid, instance, method_id, &params, res);
}

static int wmi_exec_noarg_ints(const char *guid, u8 instance, u32 method_id,
			       u8 *res, size_t ressize)
{
	struct acpi_buffer params;

	params.length = 0;
	params.pointer = NULL;
	return wmi_exec_ints(guid, instance, method_id, &params, res, ressize);
}

static int wmi_exec_arg(const char *guid, u8 instance, u32 method_id, void *arg,
			size_t arg_size)
{
	struct acpi_buffer params;
	acpi_status status;

	params.length = arg_size;
	params.pointer = arg;
	status = wmi_evaluate_method(guid, instance, method_id, &params, NULL);

	if (ACPI_FAILURE(status))
		return -EIO;
	return 0;
}

/* ================================= */
/* Lenovo WMI config                 */
/* ================================= */
#define LEGION_WMI_GAMEZONE_GUID "887B54E3-DDDC-4B2C-8B88-68A26A8835D0"
// GPU over clock
#define WMI_METHOD_ID_ISSUPPORTGPUOC 4

//Fan speed
// only completely implemented only for some models here
// often implemted also in other class and other method
// below
#define WMI_METHOD_ID_GETFAN1SPEED 8
#define WMI_METHOD_ID_GETFAN2SPEED 9

// Version of ACPI
#define WMI_METHOD_ID_GETVERSION 11
// Does it support CPU overclock?
#define WMI_METHOD_ID_ISSUPPORTCPUOC 14
// Temperatures
// only completely implemented  only for some models here
// often implemted also in other class and other method
// below
#define WMI_METHOD_ID_GETCPUTEMP 18
#define WMI_METHOD_ID_GETGPUTEMP 19

// two state keyboard light
#define WMI_METHOD_ID_GETKEYBOARDLIGHT 37
#define WMI_METHOD_ID_SETKEYBOARDLIGHT 36
// disable win key
// 0 = win key enabled; 1 = win key disabled
#define WMI_METHOD_ID_ISSUPPORTDISABLEWINKEY 21
#define WMI_METHOD_ID_GETWINKEYSTATUS 23
#define WMI_METHOD_ID_SETWINKEYSTATUS 22
// disable touchpad
//0 = touchpad enabled; 1 = touchpad disabled
#define WMI_METHOD_ID_ISSUPPORTDISABLETP 24
#define WMI_METHOD_ID_GETTPSTATUS 26
#define WMI_METHOD_ID_SETTPSTATUS 25
// gSync
#define WMI_METHOD_ID_ISSUPPORTGSYNC 40
#define WMI_METHOD_ID_GETGSYNCSTATUS 41
#define WMI_METHOD_ID_SETGSYNCSTATUS 42
//smartFanMode = powermode
#define WMI_METHOD_ID_ISSUPPORTSMARTFAN 49
#define WMI_METHOD_ID_GETSMARTFANMODE 45
#define WMI_METHOD_ID_SETSMARTFANMODE 44
// power charge mode
#define WMI_METHOD_ID_GETPOWERCHARGEMODE 47
// overdrive of display to reduce latency
// 0=off, 1=on
#define WMI_METHOD_ID_ISSUPPORTOD 49
#define WMI_METHOD_ID_GETODSTATUS 50
#define WMI_METHOD_ID_SETODSTATUS 51
// thermal mode = power mode used for cooling
#define WMI_METHOD_ID_GETTHERMALMODE 55
// get max frequency of core 0
#define WMI_METHOD_ID_GETCPUMAXFREQUENCY 60
// check if AC adapter has enough power to overclock
#define WMI_METHOD_ID_ISACFITFOROC 62
// set iGPU (GPU packaged with CPU) state
#define WMI_METHOD_ID_ISSUPPORTIGPUMODE 63
#define WMI_METHOD_ID_GETIGPUMODESTATUS 64
#define WMI_METHOD_ID_SETIGPUMODESTATUS 65
#define WMI_METHOD_ID_NOTIFYDGPUSTATUS 66
enum IGPUState {
	IGPUState_default = 0,
	IGPUState_iGPUOnly = 1,
	IGPUState_auto = 2
};

#define WMI_GUID_LENOVO_CPU_METHOD "14afd777-106f-4c9b-b334-d388dc7809be"
#define WMI_METHOD_ID_CPU_GET_SUPPORT_OC_STATUS 15
#define WMI_METHOD_ID_CPU_GET_OC_STATUS 1
#define WMI_METHOD_ID_CPU_SET_OC_STATUS 2

// ppt limit slow
#define WMI_METHOD_ID_CPU_GET_SHORTTERM_POWERLIMIT 3
#define WMI_METHOD_ID_CPU_SET_SHORTTERM_POWERLIMIT 4
// ppt stapm
#define WMI_METHOD_ID_CPU_GET_LONGTERM_POWERLIMIT 5
#define WMI_METHOD_ID_CPU_SET_LONGTERM_POWERLIMIT 6
// default power limit
#define WMI_METHOD_ID_CPU_GET_DEFAULT_POWERLIMIT 7
// peak power limit
#define WMI_METHOD_ID_CPU_GET_PEAK_POWERLIMIT 8
#define WMI_METHOD_ID_CPU_SET_PEAK_POWERLIMIT 9
// apu sppt powerlimit
#define WMI_METHOD_ID_CPU_GET_APU_SPPT_POWERLIMIT 12
#define WMI_METHOD_ID_CPU_SET_APU_SPPT_POWERLIMIT 13
// cross loading powerlimit
#define WMI_METHOD_ID_CPU_GET_CROSS_LOADING_POWERLIMIT 16
#define WMI_METHOD_ID_CPU_SET_CROSS_LOADING_POWERLIMIT 17

#define WMI_GUID_LENOVO_GPU_METHOD "da7547f1-824d-405f-be79-d9903e29ced7"
// overclock GPU possible
#define WMI_METHOD_ID_GPU_GET_OC_STATUS 1
#define WMI_METHOD_ID_GPU_SET_OC_STATUS 2
// dynamic boost power
#define WMI_METHOD_ID_GPU_GET_PPAB_POWERLIMIT 3
#define WMI_METHOD_ID_GPU_SET_PPAB_POWERLIMIT 4
// configurable TGP (power)
#define WMI_METHOD_ID_GPU_GET_CTGP_POWERLIMIT 5
#define WMI_METHOD_ID_GPU_SET_CTGP_POWERLIMIT 6
// ppab/ctgp powerlimit
#define WMI_METHOD_ID_GPU_GET_DEFAULT_PPAB_CTGP_POWERLIMIT 7
// temperature limit
#define WMI_METHOD_ID_GPU_GET_TEMPERATURE_LIMIT 8
#define WMI_METHOD_ID_GPU_SET_TEMPERATURE_LIMIT 9
// boost clock
#define WMI_METHOD_ID_GPU_GET_BOOST_CLOCK 10

#define WMI_GUID_LENOVO_FAN_METHOD "92549549-4bde-4f06-ac04-ce8bf898dbaa"
// set fan to maximal speed; dust cleaning mode
// only works in custom power mode
#define WMI_METHOD_ID_FAN_GET_FULLSPEED 1
#define WMI_METHOD_ID_FAN_SET_FULLSPEED 2
// max speed of fan
#define WMI_METHOD_ID_FAN_GET_MAXSPEED 3
#define WMI_METHOD_ID_FAN_SET_MAXSPEED 4
// fan table in custom mode
#define WMI_METHOD_ID_FAN_GET_TABLE 5
#define WMI_METHOD_ID_FAN_SET_TABLE 6
// get speed of fans
#define WMI_METHOD_ID_FAN_GETCURRENTFANSPEED 7
// get temperatures of CPU and GPU used for controlling cooling
#define WMI_METHOD_ID_FAN_GETCURRENTSENSORTEMPERATURE 8

// do not implement following
// #define WMI_METHOD_ID_Fan_SetCurrentFanSpeed 9

#define LEGION_WMI_KBBACKLIGHT_GUID "8C5B9127-ECD4-4657-980F-851019F99CA5"
// access the keyboard backlight with 3 states
#define WMI_METHOD_ID_KBBACKLIGHTGET 0x1
#define WMI_METHOD_ID_KBBACKLIGHTSET 0x2

// new method in newer methods to get or set most of the values
// with the two methods GetFeatureValue or SetFeatureValue.
// They are called like GetFeatureValue(feature_id) where
// feature_id is a id for the feature
#define LEGION_WMI_LENOVO_OTHER_METHOD_GUID \
	"dc2a8805-3a8c-41ba-a6f7-092e0089cd3b"
#define WMI_METHOD_ID_GET_FEATURE_VALUE 17
#define WMI_METHOD_ID_SET_FEATURE_VALUE 18

enum OtherMethodFeature {
	OtherMethodFeature_U1 = 0x010000, //->PC00.LPCB.EC0.REJF
	OtherMethodFeature_U2 = 0x0F0000, //->C00.PEG1.PXP._STA?
	OtherMethodFeature_U3 = 0x030000, //->PC00.LPCB.EC0.FLBT?
	OtherMethodFeature_CPU_SHORT_TERM_POWER_LIMIT = 0x01010000,
	OtherMethodFeature_CPU_LONG_TERM_POWER_LIMIT = 0x01020000,
	OtherMethodFeature_CPU_PEAK_POWER_LIMIT = 0x01030000,
	OtherMethodFeature_CPU_TEMPERATURE_LIMIT = 0x01040000,

	OtherMethodFeature_APU_PPT_POWER_LIMIT = 0x01050000,

	OtherMethodFeature_CPU_CROSS_LOAD_POWER_LIMIT = 0x01060000,
	OtherMethodFeature_CPU_L1_TAU = 0x01070000,

	OtherMethodFeature_GPU_POWER_BOOST = 0x02010000,
	OtherMethodFeature_GPU_cTGP = 0x02020000,
	OtherMethodFeature_GPU_TEMPERATURE_LIMIT = 0x02030000,
	OtherMethodFeature_GPU_POWER_TARGET_ON_AC_OFFSET_FROM_BASELINE =
		0x02040000,

	OtherMethodFeature_FAN_SPEED_1 = 0x04030001,
	OtherMethodFeature_FAN_SPEED_2 = 0x04030002,

	OtherMethodFeature_C_U1 = 0x05010000,
	OtherMethodFeature_TEMP_CPU = 0x05040000,
	OtherMethodFeature_TEMP_GPU = 0x05050000,
};

static ssize_t wmi_other_method_get_value(enum OtherMethodFeature feature_id,
					  int *value)
{
	struct acpi_buffer params;
	int error;
	unsigned long res;
	u32 param1 = feature_id;

	params.length = sizeof(param1);
	params.pointer = &param1;
	error = wmi_exec_int(LEGION_WMI_LENOVO_OTHER_METHOD_GUID, 0,
			     WMI_METHOD_ID_GET_FEATURE_VALUE, &params, &res);
	if (!error)
		*value = res;
	return error;
}

/* =================================== */
/* EC RAM Access with memory mapped IO */
/* =================================== */

struct ecram_memoryio {
	// TODO: start of remapped memory in EC RAM is assumed to be 0
	// u16 ecram_start;

	// physical address of remapped IO, depends on model and firmware
	phys_addr_t physical_start;
	// start adress of region in ec memory
	phys_addr_t physical_ec_start;
	// virtual address of remapped IO
	u8 *virtual_start;
	// size of remapped access
	size_t size;
};

/**
 * physical_start : corresponds to EC RAM 0 inside EC
 * size: size of remapped region
 *
 * strong exception safety
 */
static ssize_t ecram_memoryio_init(struct ecram_memoryio *ec_memoryio,
				   phys_addr_t physical_start,
				   phys_addr_t physical_ec_start, size_t size)
{
	void *virtual_start = ioremap(physical_start, size);

	if (!IS_ERR_OR_NULL(virtual_start)) {
		ec_memoryio->virtual_start = virtual_start;
		ec_memoryio->physical_start = physical_start;
		ec_memoryio->physical_ec_start = physical_ec_start;
		ec_memoryio->size = size;
		pr_info("Succeffuly mapped embedded controller: 0x%llx (in RAM)/0x%llx (in EC) to virtual 0x%p\n",
			ec_memoryio->physical_start,
			ec_memoryio->physical_ec_start,
			ec_memoryio->virtual_start);
	} else {
		pr_info("Error mapping embedded controller memory at 0x%llx\n",
			physical_start);
		return -ENOMEM;
	}
	return 0;
}

static void ecram_memoryio_exit(struct ecram_memoryio *ec_memoryio)
{
	if (ec_memoryio->virtual_start != NULL) {
		pr_info("Unmapping embedded controller memory at 0x%llx (in RAM)/0x%llx (in EC) at virtual 0x%p\n",
			ec_memoryio->physical_start,
			ec_memoryio->physical_ec_start,
			ec_memoryio->virtual_start);
		iounmap(ec_memoryio->virtual_start);
		ec_memoryio->virtual_start = NULL;
	}
}

/* Read a byte from the EC RAM.
 *
 * Return status because of commong signature for alle
 * methods to access EC RAM.
 */
static ssize_t ecram_memoryio_read(const struct ecram_memoryio *ec_memoryio,
				   u16 ec_offset, u8 *value)
{
	if (ec_offset < ec_memoryio->physical_ec_start) {
		pr_info("Unexpected read at offset %d into EC RAM\n",
			ec_offset);
		return -1;
	}
	*value = *(ec_memoryio->virtual_start +
		   (ec_offset - ec_memoryio->physical_ec_start));
	return 0;
}

/* Write a byte to the EC RAM.
 *
 * Return status because of commong signature for alle
 * methods to access EC RAM.
 */
ssize_t ecram_memoryio_write(const struct ecram_memoryio *ec_memoryio,
			     u16 ec_offset, u8 value)
{
	if (ec_offset < ec_memoryio->physical_ec_start) {
		pr_info("Unexpected write at offset %d into EC RAM\n",
			ec_offset);
		return -1;
	}
	*(ec_memoryio->virtual_start +
	  (ec_offset - ec_memoryio->physical_ec_start)) = value;
	return 0;
}

/* ================================= */
/* EC RAM Access with port-mapped IO */
/* ================================= */

/*
 * See datasheet of e.g. IT8502E/F/G, e.g.
 * 6.2 Plug and Play Configuration (PNPCFG)
 *
 * Depending on configured BARDSEL register
 * the ports
 *   ECRAM_PORTIO_ADDR_PORT and
 *   ECRAM_PORTIO_DATA_PORT
 * are configured.
 *
 * By performing IO on these ports one can
 * read/write to registers in the EC.
 *
 * "To access a register of PNPCFG, write target index to
 *  address port and access this PNPCFG register via
 *  data port" [datasheet, 6.2 Plug and Play Configuration]
 */

// IO ports used to write to communicate with embedded controller
// Start of used ports
#define ECRAM_PORTIO_START_PORT 0x4E
// Number of used ports
#define ECRAM_PORTIO_PORTS_SIZE 2
// Port used to specify address in EC RAM to read/write
// 0x4E/0x4F is the usual port for IO super controler
// 0x2E/0x2F also common (ITE can also be configure to use these)
#define ECRAM_PORTIO_ADDR_PORT 0x4E
// Port to send/receive the value  to write/read
#define ECRAM_PORTIO_DATA_PORT 0x4F
// Name used to request ports
#define ECRAM_PORTIO_NAME "legion"

struct ecram_portio {
	/* protects read/write to EC RAM performed
	 * as a certain sequence of outb, inb
	 * commands on the IO ports. There can
	 * be at most one.
	 */
	struct mutex io_port_mutex;
};

static ssize_t ecram_portio_init(struct ecram_portio *ec_portio)
{
	if (!request_region(ECRAM_PORTIO_START_PORT, ECRAM_PORTIO_PORTS_SIZE,
			    ECRAM_PORTIO_NAME)) {
		pr_info("Cannot init ecram_portio the %x ports starting at %x\n",
			ECRAM_PORTIO_PORTS_SIZE, ECRAM_PORTIO_START_PORT);
		return -ENODEV;
	}
	//pr_info("Reserved %x ports starting at %x\n", ECRAM_PORTIO_PORTS_SIZE, ECRAM_PORTIO_START_PORT);
	mutex_init(&ec_portio->io_port_mutex);
	return 0;
}

static void ecram_portio_exit(struct ecram_portio *ec_portio)
{
	release_region(ECRAM_PORTIO_START_PORT, ECRAM_PORTIO_PORTS_SIZE);
}

/* Read a byte from the EC RAM.
 *
 * Return status because of commong signature for alle
 * methods to access EC RAM.
 */
static ssize_t ecram_portio_read(struct ecram_portio *ec_portio, u16 offset,
				 u8 *value)
{
	mutex_lock(&ec_portio->io_port_mutex);

	outb(0x2E, ECRAM_PORTIO_ADDR_PORT);
	outb(0x11, ECRAM_PORTIO_DATA_PORT);
	outb(0x2F, ECRAM_PORTIO_ADDR_PORT);
	// TODO: no explicit cast between types seems to be sometimes
	// done and sometimes not
	outb((u8)((offset >> 8) & 0xFF), ECRAM_PORTIO_DATA_PORT);

	outb(0x2E, ECRAM_PORTIO_ADDR_PORT);
	outb(0x10, ECRAM_PORTIO_DATA_PORT);
	outb(0x2F, ECRAM_PORTIO_ADDR_PORT);
	outb((u8)(offset & 0xFF), ECRAM_PORTIO_DATA_PORT);

	outb(0x2E, ECRAM_PORTIO_ADDR_PORT);
	outb(0x12, ECRAM_PORTIO_DATA_PORT);
	outb(0x2F, ECRAM_PORTIO_ADDR_PORT);
	*value = inb(ECRAM_PORTIO_DATA_PORT);

	mutex_unlock(&ec_portio->io_port_mutex);
	return 0;
}

/* Write a byte to the EC RAM.
 *
 * Return status because of commong signature for alle
 * methods to access EC RAM.
 */
static ssize_t ecram_portio_write(struct ecram_portio *ec_portio, u16 offset,
				  u8 value)
{
	mutex_lock(&ec_portio->io_port_mutex);

	outb(0x2E, ECRAM_PORTIO_ADDR_PORT);
	outb(0x11, ECRAM_PORTIO_DATA_PORT);
	outb(0x2F, ECRAM_PORTIO_ADDR_PORT);
	// TODO: no explicit cast between types seems to be sometimes
	// done and sometimes not
	outb((u8)((offset >> 8) & 0xFF), ECRAM_PORTIO_DATA_PORT);

	outb(0x2E, ECRAM_PORTIO_ADDR_PORT);
	outb(0x10, ECRAM_PORTIO_DATA_PORT);
	outb(0x2F, ECRAM_PORTIO_ADDR_PORT);
	outb((u8)(offset & 0xFF), ECRAM_PORTIO_DATA_PORT);

	outb(0x2E, ECRAM_PORTIO_ADDR_PORT);
	outb(0x12, ECRAM_PORTIO_DATA_PORT);
	outb(0x2F, ECRAM_PORTIO_ADDR_PORT);
	outb(value, ECRAM_PORTIO_DATA_PORT);

	mutex_unlock(&ec_portio->io_port_mutex);
	// TODO: remove this
	//pr_info("Writing %d to addr %x\n", value, offset);
	return 0;
}

/* =================================== */
/* EC RAM Access                       */
/* =================================== */

struct ecram {
	struct ecram_portio portio;
};

static ssize_t ecram_init(struct ecram *ecram,
			  phys_addr_t memoryio_ec_physical_start,
			  size_t region_size)
{
	ssize_t err;

	err = ecram_portio_init(&ecram->portio);
	if (err) {
		pr_info("Failed ecram_portio_init\n");
		goto err_ecram_portio_init;
	}

	return 0;

err_ecram_portio_init:
	return err;
}

static void ecram_exit(struct ecram *ecram)
{
	pr_info("Unloading legion ecram\n");
	ecram_portio_exit(&ecram->portio);
	pr_info("Unloading legion ecram done\n");
}

/** Read from EC RAM
 * ecram_offset address on the EC
 */
static u8 ecram_read(struct ecram *ecram, u16 ecram_offset)
{
	u8 value;
	int err;

	err = ecram_portio_read(&ecram->portio, ecram_offset, &value);
	if (err)
		pr_info("Error reading EC RAM at 0x%x\n", ecram_offset);
	return value;
}

static void ecram_write(struct ecram *ecram, u16 ecram_offset, u8 value)
{
	int err;

	if (ec_readonly) {
		pr_info("Skipping writing EC RAM at 0x%x because readonly.\n",
			ecram_offset);
		return;
	}
	err = ecram_portio_write(&ecram->portio, ecram_offset, value);
	if (err)
		pr_info("Error writing EC RAM at 0x%x\n", ecram_offset);
}

/* =============================== */
/* Reads from EC  */
/* ===============================  */

static u16 read_ec_id(struct ecram *ecram, const struct model_config *model)
{
	u8 id1 = ecram_read(ecram, model->registers->ECHIPID1);
	u8 id2 = ecram_read(ecram, model->registers->ECHIPID2);

	return (id1 << 8) + id2;
}

static u16 read_ec_version(struct ecram *ecram,
			   const struct model_config *model)
{
	u8 vers = ecram_read(ecram, model->registers->ECHIPVER);
	u8 debug = ecram_read(ecram, model->registers->ECDEBUG);

	return (vers << 8) + debug;
}

/* ============================= */
/* Data model for sensor values  */
/* ============================= */

struct sensor_values {
	u16 fan1_rpm; // current speed in rpm of fan 1
	u16 fan2_rpm; // current speed in rpm of fan2
	u16 fan1_target_rpm; // target speed in rpm of fan 1
	u16 fan2_target_rpm; // target speed in rpm of fan 2
	u8 cpu_temp_celsius; // cpu temperature in celcius
	u8 gpu_temp_celsius; // gpu temperature in celcius
	u8 ic_temp_celsius; // ic temperature in celcius
};

enum SENSOR_ATTR {
	SENSOR_CPU_TEMP_ID = 1,
	SENSOR_GPU_TEMP_ID = 2,
	SENSOR_IC_TEMP_ID = 3,
	SENSOR_FAN1_RPM_ID = 4,
	SENSOR_FAN2_RPM_ID = 5,
	SENSOR_FAN1_TARGET_RPM_ID = 6,
	SENSOR_FAN2_TARGET_RPM_ID = 7
};

/* ============================= */
/* Data model for fan curve      */
/* ============================= */

struct fancurve_point {
	// rpm1 devided by 100
	u8 rpm1_raw;
	// rpm2 devided by 100
	u8 rpm2_raw;
	// >=2 , <=5 (lower is faster); must be increasing by level
	u8 accel;
	// >=2 , <=5 (lower is faster); must be increasing by level
	u8 decel;

	// min must be lower or equal than max
	// last level max must be 127
	// <=127 cpu max temp for this level; must be increasing by level
	u8 cpu_max_temp_celsius;
	// <=127 cpu min temp for this level; must be increasing by level
	u8 cpu_min_temp_celsius;
	// <=127 gpu min temp for this level; must be increasing by level
	u8 gpu_max_temp_celsius;
	// <=127 gpu max temp for this level; must be increasing by level
	u8 gpu_min_temp_celsius;
	// <=127 ic max temp for this level; must be increasing by level
	u8 ic_max_temp_celsius;
	// <=127 ic max temp for this level; must be increasing by level
	u8 ic_min_temp_celsius;
};

enum FANCURVE_ATTR {
	FANCURVE_ATTR_PWM1 = 1,
	FANCURVE_ATTR_PWM2 = 2,
	FANCURVE_ATTR_CPU_TEMP = 3,
	FANCURVE_ATTR_CPU_HYST = 4,
	FANCURVE_ATTR_GPU_TEMP = 5,
	FANCURVE_ATTR_GPU_HYST = 6,
	FANCURVE_ATTR_IC_TEMP = 7,
	FANCURVE_ATTR_IC_HYST = 8,
	FANCURVE_ATTR_ACCEL = 9,
	FANCURVE_ATTR_DECEL = 10,
	FANCURVE_SIZE = 11,
	FANCURVE_MINIFANCURVE_ON_COOL = 12
};

// used for clearing table entries
static const struct fancurve_point fancurve_point_zero = { 0, 0, 0, 0, 0,
							   0, 0, 0, 0, 0 };

struct fancurve {
	struct fancurve_point points[MAXFANCURVESIZE];
	// number of points used; must be <= MAXFANCURVESIZE
	size_t size;
	// the point that at which fans are run currently
	size_t current_point_i;
};

// validation functions

static bool fancurve_is_valid_min_temp(int min_temp)
{
	return min_temp >= 0 && min_temp <= 127;
}

static bool fancurve_is_valid_max_temp(int max_temp)
{
	return max_temp >= 0 && max_temp <= 127;
}

// setters with validation
// - make hwmon implementation easier
// - keep fancurve valid, otherwise EC will not properly control fan

static bool fancurve_set_rpm1(struct fancurve *fancurve, int point_id, int rpm)
{
	bool valid = point_id == 0 ? rpm == 0 : (rpm >= 0 && rpm <= 4500);

	if (valid)
		fancurve->points[point_id].rpm1_raw = rpm / 100;
	return valid;
}

static bool fancurve_set_rpm2(struct fancurve *fancurve, int point_id, int rpm)
{
	bool valid = point_id == 0 ? rpm == 0 : (rpm >= 0 && rpm <= 4500);

	if (valid)
		fancurve->points[point_id].rpm2_raw = rpm / 100;
	return valid;
}

// TODO: remove { ... } from single line if body

static bool fancurve_set_accel(struct fancurve *fancurve, int point_id,
			       int accel)
{
	bool valid = accel >= 2 && accel <= 5;

	if (valid)
		fancurve->points[point_id].accel = accel;
	return valid;
}

static bool fancurve_set_decel(struct fancurve *fancurve, int point_id,
			       int decel)
{
	bool valid = decel >= 2 && decel <= 5;

	if (valid)
		fancurve->points[point_id].decel = decel;
	return valid;
}

static bool fancurve_set_cpu_temp_max(struct fancurve *fancurve, int point_id,
				      int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].cpu_max_temp_celsius = value;

	return valid;
}

static bool fancurve_set_gpu_temp_max(struct fancurve *fancurve, int point_id,
				      int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].gpu_max_temp_celsius = value;
	return valid;
}

static bool fancurve_set_ic_temp_max(struct fancurve *fancurve, int point_id,
				     int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].ic_max_temp_celsius = value;
	return valid;
}

static bool fancurve_set_cpu_temp_min(struct fancurve *fancurve, int point_id,
				      int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].cpu_min_temp_celsius = value;
	return valid;
}

static bool fancurve_set_gpu_temp_min(struct fancurve *fancurve, int point_id,
				      int value)
{
	bool valid = fancurve_is_valid_min_temp(value);

	if (valid)
		fancurve->points[point_id].gpu_min_temp_celsius = value;
	return valid;
}

static bool fancurve_set_ic_temp_min(struct fancurve *fancurve, int point_id,
				     int value)
{
	bool valid = fancurve_is_valid_min_temp(value);

	if (valid)
		fancurve->points[point_id].ic_min_temp_celsius = value;
	return valid;
}

static bool fancurve_set_size(struct fancurve *fancurve, int size,
			      bool init_values)
{
	bool valid = size >= 1 && size <= MAXFANCURVESIZE;

	if (!valid)
		return false;
	if (init_values && size < fancurve->size) {
		// fancurve size is decreased, but last etnry alwasy needs 127 temperatures
		// Note: size >=1
		fancurve->points[size - 1].cpu_max_temp_celsius = 127;
		fancurve->points[size - 1].ic_max_temp_celsius = 127;
		fancurve->points[size - 1].gpu_max_temp_celsius = 127;
	}
	if (init_values && size > fancurve->size) {
		// fancurve increased, so new entries need valid values
		int i;
		int last = fancurve->size > 0 ? fancurve->size - 1 : 0;

		for (i = fancurve->size; i < size; ++i)
			fancurve->points[i] = fancurve->points[last];
	}
	return true;
}

static ssize_t fancurve_print_seqfile(const struct fancurve *fancurve,
				      struct seq_file *s)
{
	int i;

	seq_printf(
		s,
		"rpm1|rpm2|acceleration|deceleration|cpu_min_temp|cpu_max_temp|gpu_min_temp|gpu_max_temp|ic_min_temp|ic_max_temp\n");
	for (i = 0; i < fancurve->size; ++i) {
		const struct fancurve_point *point = &fancurve->points[i];

		seq_printf(
			s, "%d\t %d\t %d\t %d\t %d\t %d\t %d\t %d\t %d\t %d\n",
			point->rpm1_raw * 100, point->rpm2_raw * 100,
			point->accel, point->decel, point->cpu_min_temp_celsius,
			point->cpu_max_temp_celsius,
			point->gpu_min_temp_celsius,
			point->gpu_max_temp_celsius, point->ic_min_temp_celsius,
			point->ic_max_temp_celsius);
	}
	return 0;
}

struct light {
	bool initialized;
	struct led_classdev led;
	unsigned int last_brightness;
	u8 light_id;
	unsigned int lower_limit;
	unsigned int upper_limit;
};

/* =============================  */
/* Global and shared data between */
/* all calls to this module       */
/* =============================  */
// Implemented like ideapad-laptop.c but currenlty still
// wihtout dynamic memory allocation (instead global _priv)
struct legion_private {
	struct platform_device *platform_device;
	// TODO: remove or keep? init?
	struct acpi_device *adev;

	// Method to access ECRAM
	struct ecram ecram;
	// Configuration with registers an ECRAM access method
	const struct model_config *conf;

	// TODO: maybe refactor an keep only local to each function
	// last known fan curve
	struct fancurve fancurve;
	// configured fan curve from user space
	struct fancurve fancurve_configured;

	// update lock, when partial values of fancurve are changed
	struct mutex fancurve_mutex;

	//interfaces
	struct dentry *debugfs_dir;
	struct device *hwmon_dev;
	struct platform_profile_handler platform_profile_handler;

	struct light kbd_bl;
	struct light ylogo_light;
	struct light iport_light;

	// TODO: remove?
	bool loaded;

	// TODO: remove, only for reverse enginnering
	struct ecram_memoryio ec_memoryio;
};

// shared between different drivers: WMI, platform and proteced by mutex
static struct legion_private *legion_shared;
static struct legion_private _priv;
static DEFINE_MUTEX(legion_shared_mutex);

static int legion_shared_init(struct legion_private *priv)
{
	int ret;

	mutex_lock(&legion_shared_mutex);

	if (!legion_shared) {
		legion_shared = priv;
		mutex_init(&legion_shared->fancurve_mutex);
		ret = 0;
	} else {
		pr_warn("Found multiple platform devices\n");
		ret = -EINVAL;
	}

	priv->loaded = true;
	mutex_unlock(&legion_shared_mutex);

	return ret;
}

static void legion_shared_exit(struct legion_private *priv)
{
	pr_info("Unloading legion shared\n");
	mutex_lock(&legion_shared_mutex);

	if (legion_shared == priv)
		legion_shared = NULL;

	mutex_unlock(&legion_shared_mutex);
	pr_info("Unloading legion shared done\n");
}

static int get_simple_wmi_attribute(struct legion_private *priv,
				    const char *guid, u8 instance,
				    u32 method_id, bool invert,
				    unsigned long scale, unsigned long *value)
{
	unsigned long state = 0;
	int err;

	if (scale == 0) {
		pr_info("Scale cannot be 0\n");
		return -EINVAL;
	}
	err = wmi_exec_noarg_int(guid, instance, method_id, &state);
	if (err)
		return -EINVAL;

	// TODO: remove later
	pr_info("%swith raw value: %ld\n", __func__, state);

	state = state * scale;

	if (invert)
		state = !state;
	*value = state;
	return 0;
}

static int get_simple_wmi_attribute_bool(struct legion_private *priv,
					 const char *guid, u8 instance,
					 u32 method_id, bool invert,
					 unsigned long scale, bool *value)
{
	unsigned long int_val = *value;
	int err = get_simple_wmi_attribute(priv, guid, instance, method_id,
					   invert, scale, &int_val);
	*value = int_val;
	return err;
}

static int set_simple_wmi_attribute(struct legion_private *priv,
				    const char *guid, u8 instance,
				    u32 method_id, bool invert, int scale,
				    int state)
{
	int err;
	u8 in_param;

	if (scale == 0) {
		pr_info("Scale cannot be 0\n");
		return -EINVAL;
	}

	if (invert)
		state = !state;

	in_param = state / scale;

	err = wmi_exec_arg(guid, instance, method_id, &in_param,
			   sizeof(in_param));
	return err;
}

/* ============================= */
/* Sensor values reading/writing */
/* ============================= */

static int ec_read_sensor_values(struct ecram *ecram,
				 const struct model_config *model,
				 struct sensor_values *values)
{
	values->fan1_target_rpm =
		100 * ecram_read(ecram, model->registers->EXT_FAN1_TARGET_RPM);
	values->fan2_target_rpm =
		100 * ecram_read(ecram, model->registers->EXT_FAN2_TARGET_RPM);

	values->fan1_rpm =
		ecram_read(ecram, model->registers->EXT_FAN1_RPM_LSB) +
		(((int)ecram_read(ecram, model->registers->EXT_FAN1_RPM_MSB))
		 << 8);
	values->fan2_rpm =
		ecram_read(ecram, model->registers->EXT_FAN2_RPM_LSB) +
		(((int)ecram_read(ecram, model->registers->EXT_FAN2_RPM_MSB))
		 << 8);

	values->cpu_temp_celsius =
		ecram_read(ecram, model->registers->EXT_CPU_TEMP_INPUT);
	values->gpu_temp_celsius =
		ecram_read(ecram, model->registers->EXT_GPU_TEMP_INPUT);
	values->ic_temp_celsius =
		ecram_read(ecram, model->registers->EXT_IC_TEMP_INPUT);

	values->cpu_temp_celsius = ecram_read(ecram, 0xC5E6);
	values->gpu_temp_celsius = ecram_read(ecram, 0xC5E7);
	values->ic_temp_celsius = ecram_read(ecram, 0xC5E8);

	return 0;
}

static ssize_t ec_read_temperature(struct ecram *ecram,
				   const struct model_config *model,
				   int sensor_id, int *temperature)
{
	int err = 0;
	unsigned long res;

	if (sensor_id == 0) {
		res = ecram_read(ecram, 0xC5E6);
	} else if (sensor_id == 1) {
		res = ecram_read(ecram, 0xC5E7);
	} else {
		// TODO: use all correct error codes
		return -EEXIST;
	}
	if (!err)
		*temperature = res;
	return err;
}

static ssize_t ec_read_fanspeed(struct ecram *ecram,
				const struct model_config *model, int fan_id,
				int *fanspeed_rpm)
{
	int err = 0;
	unsigned long res;

	if (fan_id == 0) {
		res = ecram_read(ecram, model->registers->EXT_FAN1_RPM_LSB) +
		      (((int)ecram_read(ecram,
					model->registers->EXT_FAN1_RPM_MSB))
		       << 8);
	} else if (fan_id == 1) {
		res = ecram_read(ecram, model->registers->EXT_FAN2_RPM_LSB) +
		      (((int)ecram_read(ecram,
					model->registers->EXT_FAN2_RPM_MSB))
		       << 8);
	} else {
		// TODO: use all correct error codes
		return -EEXIST;
	}
	if (!err)
		*fanspeed_rpm = res;
	return err;
}

// '\_SB.PCI0.LPC0.EC0.FANS
#define ACPI_PATH_FAN_SPEED1 "FANS"
// '\_SB.PCI0.LPC0.EC0.FA2S
#define ACPI_PATH_FAN_SPEED2 "FA2S"

static ssize_t acpi_read_fanspeed(struct legion_private *priv, int fan_id,
				  int *value)
{
	int err;
	unsigned long acpi_value;
	const char *acpi_path;

	if (fan_id == 0) {
		acpi_path = ACPI_PATH_FAN_SPEED1;
	} else if (fan_id == 1) {
		acpi_path = ACPI_PATH_FAN_SPEED2;
	} else {
		// TODO: use all correct error codes
		return -EEXIST;
	}
	err = eval_int(priv->adev->handle, acpi_path, &acpi_value);
	if (!err)
		*value = (int)acpi_value * 100;
	return err;
}

// '\_SB.PCI0.LPC0.EC0.CPUT
#define ACPI_PATH_CPU_TEMP "CPUT"
// '\_SB.PCI0.LPC0.EC0.GPUT
#define ACPI_PATH_GPU_TEMP "GPUT"

static ssize_t acpi_read_temperature(struct legion_private *priv, int fan_id,
				     int *value)
{
	int err;
	unsigned long acpi_value;
	const char *acpi_path;

	if (fan_id == 0) {
		acpi_path = ACPI_PATH_CPU_TEMP;
	} else if (fan_id == 1) {
		acpi_path = ACPI_PATH_GPU_TEMP;
	} else {
		// TODO: use all correct error codes
		return -EEXIST;
	}
	err = eval_int(priv->adev->handle, acpi_path, &acpi_value);
	if (!err)
		*value = (int)acpi_value;
	return err;
}

// fan_id: 0 or 1
static ssize_t wmi_read_fanspeed(int fan_id, int *fanspeed_rpm)
{
	int err;
	unsigned long res;
	struct acpi_buffer params;

	params.length = 1;
	params.pointer = &fan_id;

	err = wmi_exec_int(WMI_GUID_LENOVO_FAN_METHOD, 0,
			   WMI_METHOD_ID_FAN_GETCURRENTFANSPEED, &params, &res);

	if (!err)
		*fanspeed_rpm = res;
	return err;
}

//sensor_id: cpu = 0, gpu = 1
static ssize_t wmi_read_temperature(int sensor_id, int *temperature)
{
	int err;
	unsigned long res;
	struct acpi_buffer params;

	if (sensor_id == 0)
		sensor_id = 0x03;
	else if (sensor_id == 1)
		sensor_id = 0x04;
	else {
		// TODO: use all correct error codes
		return -EEXIST;
	}

	params.length = 1;
	params.pointer = &sensor_id;

	err = wmi_exec_int(WMI_GUID_LENOVO_FAN_METHOD, 0,
			   WMI_METHOD_ID_FAN_GETCURRENTSENSORTEMPERATURE,
			   &params, &res);

	if (!err)
		*temperature = res;
	return err;
}

// fan_id: 0 or 1
static ssize_t wmi_read_fanspeed_gz(int fan_id, int *fanspeed_rpm)
{
	int err;
	u32 method_id;
	unsigned long res;

	if (fan_id == 0)
		method_id = WMI_METHOD_ID_GETFAN1SPEED;
	else if (fan_id == 1)
		method_id = WMI_METHOD_ID_GETFAN2SPEED;
	else {
		// TODO: use all correct error codes
		return -EEXIST;
	}
	err = wmi_exec_noarg_int(LEGION_WMI_GAMEZONE_GUID, 0, method_id, &res);

	if (!err)
		*fanspeed_rpm = res;
	return err;
}

//sensor_id: cpu = 0, gpu = 1
static ssize_t wmi_read_temperature_gz(int sensor_id, int *temperature)
{
	int err;
	u32 method_id;
	unsigned long res;

	if (sensor_id == 0)
		method_id = WMI_METHOD_ID_GETCPUTEMP;
	else if (sensor_id == 1)
		method_id = WMI_METHOD_ID_GETGPUTEMP;
	else {
		// TODO: use all correct error codes
		return -EEXIST;
	}

	err = wmi_exec_noarg_int(LEGION_WMI_GAMEZONE_GUID, 0, method_id, &res);

	if (!err)
		*temperature = res;
	return err;
}

// fan_id: 0 or 1
static ssize_t wmi_read_fanspeed_other(int fan_id, int *fanspeed_rpm)
{
	int err;
	enum OtherMethodFeature featured_id;
	int res;

	if (fan_id == 0)
		featured_id = OtherMethodFeature_FAN_SPEED_1;
	else if (fan_id == 1)
		featured_id = OtherMethodFeature_FAN_SPEED_2;
	else {
		// TODO: use all correct error codes
		return -EEXIST;
	}

	err = wmi_other_method_get_value(featured_id, &res);

	if (!err)
		*fanspeed_rpm = res;
	return err;
}

//sensor_id: cpu = 0, gpu = 1
static ssize_t wmi_read_temperature_other(int sensor_id, int *temperature)
{
	int err;
	enum OtherMethodFeature featured_id;
	int res;

	if (sensor_id == 0)
		featured_id = OtherMethodFeature_TEMP_CPU;
	else if (sensor_id == 1)
		featured_id = OtherMethodFeature_TEMP_GPU;
	else {
		// TODO: use all correct error codes
		return -EEXIST;
	}

	err = wmi_other_method_get_value(featured_id, &res);
	if (!err)
		*temperature = res;
	return err;
}

static ssize_t read_fanspeed(struct legion_private *priv, int fan_id,
			     int *speed_rpm)
{
	// TODO: use enums or function pointers?
	switch (priv->conf->access_method_fanspeed) {
	case ACCESS_METHOD_EC:
		return ec_read_fanspeed(&priv->ecram, priv->conf, fan_id,
					speed_rpm);
	case ACCESS_METHOD_ACPI:
		return acpi_read_fanspeed(priv, fan_id, speed_rpm);
	case ACCESS_METHOD_WMI:
		return wmi_read_fanspeed_gz(fan_id, speed_rpm);
	case ACCESS_METHOD_WMI2:
		return wmi_read_fanspeed(fan_id, speed_rpm);
	case ACCESS_METHOD_WMI3:
		return wmi_read_fanspeed_other(fan_id, speed_rpm);
	default:
		pr_info("No access method for fanspeed: %d\n",
			priv->conf->access_method_fanspeed);
		return -EINVAL;
	}
}

static ssize_t read_temperature(struct legion_private *priv, int sensor_id,
				int *temperature)
{
	// TODO: use enums or function pointers?
	switch (priv->conf->access_method_temperature) {
	case ACCESS_METHOD_EC:
		return ec_read_temperature(&priv->ecram, priv->conf, sensor_id,
					   temperature);
	case ACCESS_METHOD_ACPI:
		return acpi_read_temperature(priv, sensor_id, temperature);
	case ACCESS_METHOD_WMI:
		return wmi_read_temperature_gz(sensor_id, temperature);
	case ACCESS_METHOD_WMI2:
		return wmi_read_temperature(sensor_id, temperature);
	case ACCESS_METHOD_WMI3:
		return wmi_read_temperature_other(sensor_id, temperature);
	default:
		pr_info("No access method for temperature: %d\n",
			priv->conf->access_method_temperature);
		return -EINVAL;
	}
}

/* ============================= */
/* Fancurve reading/writing      */
/* ============================= */

/* Fancurve from WMI
 * This allows changing fewer parameters.
 * It is only available on newer models.
 */

struct WMIFanTable {
	u8 FSTM; //FSMD
	u8 FSID;
	u32 FSTL; //FSST
	u16 FSS0;
	u16 FSS1;
	u16 FSS2;
	u16 FSS3;
	u16 FSS4;
	u16 FSS5;
	u16 FSS6;
	u16 FSS7;
	u16 FSS8;
	u16 FSS9;
} __packed;

struct WMIFanTableRead {
	u32 FSFL;
	u32 FSS0;
	u32 FSS1;
	u32 FSS2;
	u32 FSS3;
	u32 FSS4;
	u32 FSS5;
	u32 FSS6;
	u32 FSS7;
	u32 FSS8;
	u32 FSS9;
	u32 FSSA;
} __packed;

static ssize_t wmi_read_fancurve_custom(const struct model_config *model,
					struct fancurve *fancurve)
{
	u8 buffer[88];
	int err;

	// The output buffer from the ACPI call is 88 bytes and larger
	// than the returned object
	pr_info("Size of object: %lu\n", sizeof(struct WMIFanTableRead));
	err = wmi_exec_noarg_ints(WMI_GUID_LENOVO_FAN_METHOD, 0,
				  WMI_METHOD_ID_FAN_GET_TABLE, buffer,
				  sizeof(buffer));
	print_hex_dump(KERN_INFO, "legion_laptop fan table wmi buffer",
		       DUMP_PREFIX_ADDRESS, 16, 1, buffer, sizeof(buffer),
		       true);
	if (!err) {
		struct WMIFanTableRead *fantable =
			(struct WMIFanTableRead *)&buffer[0];
		fancurve->current_point_i = 0;
		fancurve->size = 10;
		fancurve->points[0].rpm1_raw = fantable->FSS0;
		fancurve->points[1].rpm1_raw = fantable->FSS1;
		fancurve->points[2].rpm1_raw = fantable->FSS2;
		fancurve->points[3].rpm1_raw = fantable->FSS3;
		fancurve->points[4].rpm1_raw = fantable->FSS4;
		fancurve->points[5].rpm1_raw = fantable->FSS5;
		fancurve->points[6].rpm1_raw = fantable->FSS6;
		fancurve->points[7].rpm1_raw = fantable->FSS7;
		fancurve->points[8].rpm1_raw = fantable->FSS8;
		fancurve->points[9].rpm1_raw = fantable->FSS9;
		//fancurve->points[10].rpm1_raw = fantable->FSSA;
	}
	return err;
}

static ssize_t wmi_write_fancurve_custom(const struct model_config *model,
					 const struct fancurve *fancurve)
{
	u8 buffer[0x20];
	int err;

	// The buffer is read like this in ACPI firmware
	//
	// CreateByteField (Arg2, Zero, FSTM)
	// CreateByteField (Arg2, One, FSID)
	// CreateDWordField (Arg2, 0x02, FSTL)
	// CreateByteField (Arg2, 0x06, FSS0)
	// CreateByteField (Arg2, 0x08, FSS1)
	// CreateByteField (Arg2, 0x0A, FSS2)
	// CreateByteField (Arg2, 0x0C, FSS3)
	// CreateByteField (Arg2, 0x0E, FSS4)
	// CreateByteField (Arg2, 0x10, FSS5)
	// CreateByteField (Arg2, 0x12, FSS6)
	// CreateByteField (Arg2, 0x14, FSS7)
	// CreateByteField (Arg2, 0x16, FSS8)
	// CreateByteField (Arg2, 0x18, FSS9)

	memset(buffer, 0, sizeof(buffer));
	buffer[0x06] = fancurve->points[0].rpm1_raw;
	buffer[0x08] = fancurve->points[1].rpm1_raw;
	buffer[0x0A] = fancurve->points[2].rpm1_raw;
	buffer[0x0C] = fancurve->points[3].rpm1_raw;
	buffer[0x0E] = fancurve->points[4].rpm1_raw;
	buffer[0x10] = fancurve->points[5].rpm1_raw;
	buffer[0x12] = fancurve->points[6].rpm1_raw;
	buffer[0x14] = fancurve->points[7].rpm1_raw;
	buffer[0x16] = fancurve->points[8].rpm1_raw;
	buffer[0x18] = fancurve->points[9].rpm1_raw;

	print_hex_dump(KERN_INFO, "legion_laptop fan table wmi write buffer",
		       DUMP_PREFIX_ADDRESS, 16, 1, buffer, sizeof(buffer),
		       true);
	err = wmi_exec_arg(WMI_GUID_LENOVO_FAN_METHOD, 0,
			   WMI_METHOD_ID_FAN_SET_TABLE, buffer, sizeof(buffer));
	return err;
}

/* Read the fan curve from the EC.
 *
 * In newer models (>=2022) there is an ACPI/WMI to read fan curve as
 * a whole. So read/write fan table as a whole to use
 * same interface for both cases.
 *
 * It reads all points from EC memory, even if stored fancurve is smaller, so
 * it can contain 0 entries.
 */
static int ec_read_fancurve_legion(struct ecram *ecram,
				   const struct model_config *model,
				   struct fancurve *fancurve)
{
	size_t i = 0;

	for (i = 0; i < MAXFANCURVESIZE; ++i) {
		struct fancurve_point *point = &fancurve->points[i];

		point->rpm1_raw =
			ecram_read(ecram, model->registers->EXT_FAN1_BASE + i);
		point->rpm2_raw =
			ecram_read(ecram, model->registers->EXT_FAN2_BASE + i);

		point->accel = ecram_read(
			ecram, model->registers->EXT_FAN_ACC_BASE + i);
		point->decel = ecram_read(
			ecram, model->registers->EXT_FAN_DEC_BASE + i);
		point->cpu_max_temp_celsius =
			ecram_read(ecram, model->registers->EXT_CPU_TEMP + i);
		point->cpu_min_temp_celsius = ecram_read(
			ecram, model->registers->EXT_CPU_TEMP_HYST + i);
		point->gpu_max_temp_celsius =
			ecram_read(ecram, model->registers->EXT_GPU_TEMP + i);
		point->gpu_min_temp_celsius = ecram_read(
			ecram, model->registers->EXT_GPU_TEMP_HYST + i);
		point->ic_max_temp_celsius =
			ecram_read(ecram, model->registers->EXT_VRM_TEMP + i);
		point->ic_min_temp_celsius = ecram_read(
			ecram, model->registers->EXT_VRM_TEMP_HYST + i);
	}

	// Do not trust that hardware; It might suddendly report
	// a larger size, so clamp it.
	fancurve->size =
		ecram_read(ecram, model->registers->EXT_FAN_POINTS_SIZE);
	fancurve->size =
		min(fancurve->size, (typeof(fancurve->size))(MAXFANCURVESIZE));
	fancurve->current_point_i =
		ecram_read(ecram, model->registers->EXT_FAN_CUR_POINT);
	fancurve->current_point_i =
		min(fancurve->current_point_i, fancurve->size);
	return 0;
}

static int ec_write_fancurve_legion(struct ecram *ecram,
				    const struct model_config *model,
				    const struct fancurve *fancurve,
				    bool write_size)
{
	size_t i;

	//TODO: remove again
	pr_info("Set fancurve\n");

	// Reset fan update counters (try to avoid any race conditions)
	ecram_write(ecram, 0xC5FE, 0);
	ecram_write(ecram, 0xC5FF, 0);
	for (i = 0; i < MAXFANCURVESIZE; ++i) {
		// Entries for points larger than fancurve size should be cleared
		// to 0
		const struct fancurve_point *point =
			i < fancurve->size ? &fancurve->points[i] :
					     &fancurve_point_zero;

		ecram_write(ecram, model->registers->EXT_FAN1_BASE + i,
			    point->rpm1_raw);
		ecram_write(ecram, model->registers->EXT_FAN2_BASE + i,
			    point->rpm2_raw);

		ecram_write(ecram, model->registers->EXT_FAN_ACC_BASE + i,
			    point->accel);
		ecram_write(ecram, model->registers->EXT_FAN_DEC_BASE + i,
			    point->decel);

		ecram_write(ecram, model->registers->EXT_CPU_TEMP + i,
			    point->cpu_max_temp_celsius);
		ecram_write(ecram, model->registers->EXT_CPU_TEMP_HYST + i,
			    point->cpu_min_temp_celsius);
		ecram_write(ecram, model->registers->EXT_GPU_TEMP + i,
			    point->gpu_max_temp_celsius);
		ecram_write(ecram, model->registers->EXT_GPU_TEMP_HYST + i,
			    point->gpu_min_temp_celsius);
		ecram_write(ecram, model->registers->EXT_VRM_TEMP + i,
			    point->ic_max_temp_celsius);
		ecram_write(ecram, model->registers->EXT_VRM_TEMP_HYST + i,
			    point->ic_min_temp_celsius);
	}

	if (write_size) {
		ecram_write(ecram, model->registers->EXT_FAN_POINTS_SIZE,
			    fancurve->size);
	}

	// Reset current fan level to 0, so algorithm in EC
	// selects fan curve point again and resetting hysterisis
	// effects
	ecram_write(ecram, model->registers->EXT_FAN_CUR_POINT, 0);

	// Reset internal fan levels
	ecram_write(ecram, 0xC634, 0); // CPU
	ecram_write(ecram, 0xC635, 0); // GPU
	ecram_write(ecram, 0xC636, 0); // SENSOR

	return 0;
}

#define FANCURVESIZE_IDEAPDAD 8

static int ec_read_fancurve_ideapad(struct ecram *ecram,
				    const struct model_config *model,
				    struct fancurve *fancurve)
{
	size_t i = 0;

	for (i = 0; i < FANCURVESIZE_IDEAPDAD; ++i) {
		struct fancurve_point *point = &fancurve->points[i];

		point->rpm1_raw =
			ecram_read(ecram, model->registers->EXT_FAN1_BASE + i);
		point->rpm2_raw =
			ecram_read(ecram, model->registers->EXT_FAN2_BASE + i);

		point->accel = 0;
		point->decel = 0;
		point->cpu_max_temp_celsius =
			ecram_read(ecram, model->registers->EXT_CPU_TEMP + i);
		point->cpu_min_temp_celsius = ecram_read(
			ecram, model->registers->EXT_CPU_TEMP_HYST + i);
		point->gpu_max_temp_celsius =
			ecram_read(ecram, model->registers->EXT_GPU_TEMP + i);
		point->gpu_min_temp_celsius = ecram_read(
			ecram, model->registers->EXT_GPU_TEMP_HYST + i);
		point->ic_max_temp_celsius = 0;
		point->ic_min_temp_celsius = 0;
	}

	// Do not trust that hardware; It might suddendly report
	// a larger size, so clamp it.
	fancurve->size = FANCURVESIZE_IDEAPDAD;
	fancurve->current_point_i =
		ecram_read(ecram, model->registers->EXT_FAN_CUR_POINT);
	fancurve->current_point_i =
		min(fancurve->current_point_i, fancurve->size);
	return 0;
}

static int ec_write_fancurve_ideapad(struct ecram *ecram,
				     const struct model_config *model,
				     const struct fancurve *fancurve)
{
	size_t i;
	int valr1;
	int valr2;

	// add this later: maybe other addresses needed
	// therefore, fan curve might not be effective immediatley but
	// only after temp change
	// Reset fan update counters (try to avoid any race conditions)
	ecram_write(ecram, 0xC5FE, 0);
	ecram_write(ecram, 0xC5FF, 0);
	for (i = 0; i < FANCURVESIZE_IDEAPDAD; ++i) {
		const struct fancurve_point *point = &fancurve->points[i];

		ecram_write(ecram, model->registers->EXT_FAN1_BASE + i,
			    point->rpm1_raw);
		valr1 = ecram_read(ecram, model->registers->EXT_FAN1_BASE + i);
		ecram_write(ecram, model->registers->EXT_FAN2_BASE + i,
			    point->rpm2_raw);
		valr2 = ecram_read(ecram, model->registers->EXT_FAN2_BASE + i);
		pr_info("Writing fan1: %d; reading fan1: %d\n", point->rpm1_raw,
			valr1);
		pr_info("Writing fan2: %d; reading fan2: %d\n", point->rpm2_raw,
			valr2);

		// write to memory and repeat 8 bytes later again
		ecram_write(ecram, model->registers->EXT_CPU_TEMP + i,
			    point->cpu_max_temp_celsius);
		ecram_write(ecram, model->registers->EXT_CPU_TEMP + 8 + i,
			    point->cpu_max_temp_celsius);
		// write to memory and repeat 8 bytes later again
		ecram_write(ecram, model->registers->EXT_CPU_TEMP_HYST + i,
			    point->cpu_min_temp_celsius);
		ecram_write(ecram, model->registers->EXT_CPU_TEMP_HYST + 8 + i,
			    point->cpu_min_temp_celsius);
		// write to memory and repeat 8 bytes later again
		ecram_write(ecram, model->registers->EXT_GPU_TEMP + i,
			    point->gpu_max_temp_celsius);
		ecram_write(ecram, model->registers->EXT_GPU_TEMP + 8 + i,
			    point->gpu_max_temp_celsius);
		// write to memory and repeat 8 bytes later again
		ecram_write(ecram, model->registers->EXT_GPU_TEMP_HYST + i,
			    point->gpu_min_temp_celsius);
		ecram_write(ecram, model->registers->EXT_GPU_TEMP_HYST + 8 + i,
			    point->gpu_min_temp_celsius);
	}

	// add this later: maybe other addresses needed
	// therefore, fan curve might not be effective immediatley but
	// only after temp change
	// // Reset current fan level to 0, so algorithm in EC
	// // selects fan curve point again and resetting hysterisis
	// // effects
	// ecram_write(ecram, model->registers->EXT_FAN_CUR_POINT, 0);

	// // Reset internal fan levels
	// ecram_write(ecram, 0xC634, 0); // CPU
	// ecram_write(ecram, 0xC635, 0); // GPU
	// ecram_write(ecram, 0xC636, 0); // SENSOR

	return 0;
}

static int read_fancurve(struct legion_private *priv, struct fancurve *fancurve)
{
	// TODO: use enums or function pointers?
	switch (priv->conf->access_method_fancurve) {
	case ACCESS_METHOD_EC:
		return ec_read_fancurve_legion(&priv->ecram, priv->conf,
					       fancurve);
	case ACCESS_METHOD_EC2:
		return ec_read_fancurve_ideapad(&priv->ecram, priv->conf,
						fancurve);
	case ACCESS_METHOD_WMI3:
		return wmi_read_fancurve_custom(priv->conf, fancurve);
	default:
		pr_info("No access method for fancurve:%d\n",
			priv->conf->access_method_fancurve);
		return -EINVAL;
	}
}

static int write_fancurve(struct legion_private *priv,
			  const struct fancurve *fancurve, bool write_size)
{
	// TODO: use enums or function pointers?
	switch (priv->conf->access_method_fancurve) {
	case ACCESS_METHOD_EC:
		return ec_write_fancurve_legion(&priv->ecram, priv->conf,
						fancurve, write_size);
	case ACCESS_METHOD_EC2:
		return ec_write_fancurve_ideapad(&priv->ecram, priv->conf,
						 fancurve);
	case ACCESS_METHOD_WMI3:
		return wmi_write_fancurve_custom(priv->conf, fancurve);
	default:
		pr_info("No access method for fancurve:%d\n",
			priv->conf->access_method_fancurve);
		return -EINVAL;
	}
}

#define MINIFANCUVE_ON_COOL_ON 0x04
#define MINIFANCUVE_ON_COOL_OFF 0xA0

static int ec_read_minifancurve(struct ecram *ecram,
				const struct model_config *model, bool *state)
{
	int value =
		ecram_read(ecram, model->registers->EXT_MINIFANCURVE_ON_COOL);

	switch (value) {
	case MINIFANCUVE_ON_COOL_ON:
		*state = true;
		break;
	case MINIFANCUVE_ON_COOL_OFF:
		*state = false;
		break;
	default:
		pr_info("Unexpected value in MINIFANCURVE register:%d\n",
			value);
		return -1;
	}
	return 0;
}

static ssize_t ec_write_minifancurve(struct ecram *ecram,
				     const struct model_config *model,
				     bool state)
{
	u8 val = state ? MINIFANCUVE_ON_COOL_ON : MINIFANCUVE_ON_COOL_OFF;

	ecram_write(ecram, model->registers->EXT_MINIFANCURVE_ON_COOL, val);
	return 0;
}

#define EC_LOCKFANCONTROLLER_ON 8
#define EC_LOCKFANCONTROLLER_OFF 0

static ssize_t ec_write_lockfancontroller(struct ecram *ecram,
					  const struct model_config *model,
					  bool state)
{
	u8 val = state ? EC_LOCKFANCONTROLLER_ON : EC_LOCKFANCONTROLLER_OFF;

	ecram_write(ecram, model->registers->EXT_LOCKFANCONTROLLER, val);
	return 0;
}

static int ec_read_lockfancontroller(struct ecram *ecram,
				     const struct model_config *model,
				     bool *state)
{
	int value = ecram_read(ecram, model->registers->EXT_LOCKFANCONTROLLER);

	switch (value) {
	case EC_LOCKFANCONTROLLER_ON:
		*state = true;
		break;
	case EC_LOCKFANCONTROLLER_OFF:
		*state = false;
		break;
	default:
		pr_info("Unexpected value in lockfanspeed register:%d\n",
			value);
		return -1;
	}
	return 0;
}

#define EC_FANFULLSPEED_ON 0x40
#define EC_FANFULLSPEED_OFF 0x00

static int ec_read_fanfullspeed(struct ecram *ecram,
				const struct model_config *model, bool *state)
{
	int value = ecram_read(ecram, model->registers->EXT_MAXIMUMFANSPEED);

	switch (value) {
	case EC_FANFULLSPEED_ON:
		*state = true;
		break;
	case EC_FANFULLSPEED_OFF:
		*state = false;
		break;
	default:
		pr_info("Unexpected value in maximumfanspeed register:%d\n",
			value);
		return -1;
	}
	return 0;
}

static ssize_t ec_write_fanfullspeed(struct ecram *ecram,
				     const struct model_config *model,
				     bool state)
{
	u8 val = state ? EC_FANFULLSPEED_ON : EC_FANFULLSPEED_OFF;

	ecram_write(ecram, model->registers->EXT_MAXIMUMFANSPEED, val);
	return 0;
}

static ssize_t wmi_read_fanfullspeed(struct legion_private *priv, bool *state)
{
	return get_simple_wmi_attribute_bool(priv, WMI_GUID_LENOVO_FAN_METHOD,
					     0, WMI_METHOD_ID_FAN_GET_FULLSPEED,
					     false, 1, state);
}

static ssize_t wmi_write_fanfullspeed(struct legion_private *priv, bool state)
{
	return set_simple_wmi_attribute(priv, WMI_GUID_LENOVO_FAN_METHOD, 0,
					WMI_METHOD_ID_FAN_SET_FULLSPEED, false,
					1, state);
}

static ssize_t read_fanfullspeed(struct legion_private *priv, bool *state)
{
	// TODO: use enums or function pointers?
	switch (priv->conf->access_method_fanfullspeed) {
	case ACCESS_METHOD_EC:
		return ec_read_fanfullspeed(&priv->ecram, priv->conf, state);
	case ACCESS_METHOD_WMI:
		return wmi_read_fanfullspeed(priv, state);
	default:
		pr_info("No access method for fan full speed: %d\n",
			priv->conf->access_method_fanfullspeed);
		return -EINVAL;
	}
}

static ssize_t write_fanfullspeed(struct legion_private *priv, bool state)
{
	ssize_t res;

	switch (priv->conf->access_method_fanfullspeed) {
	case ACCESS_METHOD_EC:
		res = ec_write_fanfullspeed(&priv->ecram, priv->conf, state);
		return res;
	case ACCESS_METHOD_WMI:
		return wmi_write_fanfullspeed(priv, state);
	default:
		pr_info("No access method for fan full speed:%d\n",
			priv->conf->access_method_fanfullspeed);
		return -EINVAL;
	}
}

/* ============================= */
/* Power mode reading/writing    */
/* ============================= */

enum legion_ec_powermode {
	LEGION_EC_POWERMODE_QUIET = 2,
	LEGION_EC_POWERMODE_BALANCED = 0,
	LEGION_EC_POWERMODE_PERFORMANCE = 1,
	LEGION_EC_POWERMODE_CUSTOM = 3
};

enum legion_wmi_powermode {
	LEGION_WMI_POWERMODE_QUIET = 1,
	LEGION_WMI_POWERMODE_BALANCED = 2,
	LEGION_WMI_POWERMODE_PERFORMANCE = 3,
	LEGION_WMI_POWERMODE_CUSTOM = 255
};

enum legion_wmi_powermode ec_to_wmi_powermode(int ec_mode)
{
	switch (ec_mode) {
	case LEGION_EC_POWERMODE_QUIET:
		return LEGION_WMI_POWERMODE_QUIET;
	case LEGION_EC_POWERMODE_BALANCED:
		return LEGION_WMI_POWERMODE_BALANCED;
	case LEGION_EC_POWERMODE_PERFORMANCE:
		return LEGION_WMI_POWERMODE_PERFORMANCE;
	case LEGION_EC_POWERMODE_CUSTOM:
		return LEGION_WMI_POWERMODE_CUSTOM;
	default:
		return LEGION_WMI_POWERMODE_BALANCED;
	}
}

enum legion_ec_powermode wmi_to_ec_powermode(enum legion_wmi_powermode wmi_mode)
{
	switch (wmi_mode) {
	case LEGION_WMI_POWERMODE_QUIET:
		return LEGION_EC_POWERMODE_QUIET;
	case LEGION_WMI_POWERMODE_BALANCED:
		return LEGION_EC_POWERMODE_BALANCED;
	case LEGION_WMI_POWERMODE_PERFORMANCE:
		return LEGION_EC_POWERMODE_PERFORMANCE;
	case LEGION_WMI_POWERMODE_CUSTOM:
		return LEGION_EC_POWERMODE_CUSTOM;
	default:
		return LEGION_EC_POWERMODE_BALANCED;
	}
}

static ssize_t ec_read_powermode(struct legion_private *priv, int *powermode)
{
	*powermode =
		ecram_read(&priv->ecram, priv->conf->registers->EXT_POWERMODE);
	return 0;
}

static ssize_t ec_write_powermode(struct legion_private *priv, u8 value)
{
	if (!((value >= 0 && value <= 2) || value == 255)) {
		pr_info("Unexpected power mode value ignored: %d\n", value);
		return -ENOMEM;
	}
	ecram_write(&priv->ecram, priv->conf->registers->EXT_POWERMODE, value);
	return 0;
}

static ssize_t acpi_read_powermode(struct legion_private *priv, int *powermode)
{
	unsigned long acpi_powermode;
	int err;

	// spmo method not alwasy available
	// \_SB.PCI0.LPC0.EC0.SPMO
	err = eval_spmo(priv->adev->handle, &acpi_powermode);
	*powermode = (int)acpi_powermode;
	return err;
}

static ssize_t wmi_read_powermode(int *powermode)
{
	int err;
	unsigned long res;

	err = wmi_exec_noarg_int(LEGION_WMI_GAMEZONE_GUID, 0,
				 WMI_METHOD_ID_GETSMARTFANMODE, &res);

	if (!err)
		*powermode = res;
	return err;
}

static ssize_t wmi_write_powermode(u8 value)
{
	if (!((value >= LEGION_WMI_POWERMODE_QUIET &&
	       value <= LEGION_WMI_POWERMODE_PERFORMANCE) ||
	      value == LEGION_WMI_POWERMODE_CUSTOM)) {
		pr_info("Unexpected power mode value ignored: %d\n", value);
		return -ENOMEM;
	}
	return wmi_exec_arg(LEGION_WMI_GAMEZONE_GUID, 0,
			    WMI_METHOD_ID_SETSMARTFANMODE, &value,
			    sizeof(value));
}

static ssize_t read_powermode(struct legion_private *priv, int *powermode)
{
	ssize_t res;

	switch (priv->conf->access_method_powermode) {
	case ACCESS_METHOD_EC:
		res = ec_read_powermode(priv, powermode);
		*powermode = ec_to_wmi_powermode(*powermode);
		return res;
	case ACCESS_METHOD_ACPI:
		return acpi_read_powermode(priv, powermode);
	case ACCESS_METHOD_WMI:
		return wmi_read_powermode(powermode);
	default:
		pr_info("No access method for powermode:%d\n",
			priv->conf->access_method_powermode);
		return -EINVAL;
	}
}

static ssize_t write_powermode(struct legion_private *priv,
			       enum legion_wmi_powermode value)
{
	ssize_t res;

	//TODO: remove again
	pr_info("Set powermode\n");

	switch (priv->conf->access_method_powermode) {
	case ACCESS_METHOD_EC:
		res = ec_write_powermode(priv, wmi_to_ec_powermode(value));
		return res;
	case ACCESS_METHOD_WMI:
		return wmi_write_powermode(value);
	default:
		pr_info("No access method for powermode:%d\n",
			priv->conf->access_method_powermode);
		return -EINVAL;
	}
}

/**
 * Shortly toggle powermode to a different mode
 * and switch back, e.g. to reset fan curve.
 */
static void toggle_powermode(struct legion_private *priv)
{
	int old_powermode;
	int next_powermode;

	read_powermode(priv, &old_powermode);
	next_powermode = old_powermode == 0 ? 1 : 0;

	write_powermode(priv, next_powermode);
	mdelay(1500);
	write_powermode(priv, old_powermode);
}

/* ============================= */
/* Charging mode reading/writing */
/* ============================- */

#define FCT_RAPID_CHARGE_ON 0x07
#define FCT_RAPID_CHARGE_OFF 0x08
#define RAPID_CHARGE_ON 0x0
#define RAPID_CHARGE_OFF 0x1

static int acpi_read_rapidcharge(struct acpi_device *adev, bool *state)
{
	unsigned long result;
	int err;

	//also works? what is better?
	/*
	 * err = eval_qcho(adev->handle, &result);
	 * if (err)
	 *  return err;
	 * state = result;
	 * return 0;
	 */

	err = eval_gbmd(adev->handle, &result);
	if (err)
		return err;

	*state = result & 0x04;
	return 0;
}

static int acpi_write_rapidcharge(struct acpi_device *adev, bool state)
{
	int err;
	unsigned long fct_nr = state > 0 ? FCT_RAPID_CHARGE_ON :
					   FCT_RAPID_CHARGE_OFF;

	err = exec_sbmc(adev->handle, fct_nr);
	pr_info("Set rapidcharge to %d by calling %lu: result: %d\n", state,
		fct_nr, err);
	return err;
}

/* ============================= */
/* Keyboard backlight read/write */
/* ============================= */

static ssize_t legion_kbd_bl2_brightness_get(struct legion_private *priv)
{
	unsigned long state = 0;
	int err;

	err = wmi_exec_noarg_int(LEGION_WMI_GAMEZONE_GUID, 0,
				 WMI_METHOD_ID_GETKEYBOARDLIGHT, &state);
	if (err)
		return -EINVAL;

	return state;
}

//static int legion_kbd_bl2_brightness_set(struct legion_private *priv,
//					 unsigned int brightness)
//{
//	u8 in_param = brightness;

//	return wmi_exec_arg(LEGION_WMI_GAMEZONE_GUID, 0,
//			    WMI_METHOD_ID_SETKEYBOARDLIGHT, &in_param,
//			    sizeof(in_param));
//}

//min: 1, max: 3
#define LIGHT_ID_KEYBOARD 0x00
//min: 0, max: 1
#define LIGHT_ID_YLOGO 0x03
//min: 1, max: 2
#define LIGHT_ID_IOPORT 0x05

static int legion_wmi_light_get(struct legion_private *priv, u8 light_id,
				unsigned int min_value, unsigned int max_value)
{
	struct acpi_buffer params;
	u8 in;
	u8 result[2];
	u8 value;
	int err;

	params.length = 1;
	params.pointer = &in;
	in = light_id;
	err = wmi_exec_ints(LEGION_WMI_KBBACKLIGHT_GUID, 0,
			    WMI_METHOD_ID_KBBACKLIGHTGET, &params, result,
			    ARRAY_SIZE(result));
	if (err) {
		pr_info("Error for WMI method call to get brightness\n");
		return -EIO;
	}

	value = result[1];
	if (!(value >= min_value && value <= max_value)) {
		pr_info("Error WMI call for reading brightness: expected a value between %u and %u, but got %d\n",
			min_value, max_value, value);
		return -EFAULT;
	}

	return value - min_value;
}

static int legion_wmi_light_set(struct legion_private *priv, u8 light_id,
				unsigned int min_value, unsigned int max_value,
				unsigned int brightness)
{
	struct acpi_buffer buffer;
	u8 in_buffer_param[8];
	unsigned long result;
	int err;

	buffer.length = 3;
	buffer.pointer = &in_buffer_param[0];
	in_buffer_param[0] = light_id;
	in_buffer_param[1] = 0x01;
	in_buffer_param[2] =
		clamp(brightness + min_value, min_value, max_value);

	err = wmi_exec_int(LEGION_WMI_KBBACKLIGHT_GUID, 0,
			   WMI_METHOD_ID_KBBACKLIGHTSET, &buffer, &result);
	if (err) {
		pr_info("Error for WMI method call to set brightness on light: %d\n",
			light_id);
		return -EIO;
	}

	return 0;
}

static int legion_kbd_bl_brightness_get(struct legion_private *priv)
{
	return legion_wmi_light_get(priv, LIGHT_ID_KEYBOARD, 1, 3);
}

static int legion_kbd_bl_brightness_set(struct legion_private *priv,
					unsigned int brightness)
{
	return legion_wmi_light_set(priv, LIGHT_ID_KEYBOARD, 1, 3, brightness);
}

/* =============================  */
/* debugfs interface              */
/* ============================   */

static int debugfs_ecmemory_show(struct seq_file *s, void *unused)
{
	struct legion_private *priv = s->private;
	size_t offset;

	for (offset = 0; offset < priv->conf->memoryio_size; ++offset) {
		char value = ecram_read(&priv->ecram,
					priv->conf->memoryio_physical_ec_start +
						offset);

		seq_write(s, &value, 1);
	}
	return 0;
}

DEFINE_SHOW_ATTRIBUTE(debugfs_ecmemory);

static int debugfs_ecmemoryram_show(struct seq_file *s, void *unused)
{
	struct legion_private *priv = s->private;
	size_t offset;
	ssize_t err;
	u8 value;

	for (offset = 0; offset < priv->conf->ramio_size; ++offset) {
		err = ecram_memoryio_read(&priv->ec_memoryio, offset, &value);
		if (!err)
			seq_write(s, &value, 1);
		else
			return -EACCES;
	}
	return 0;
}

DEFINE_SHOW_ATTRIBUTE(debugfs_ecmemoryram);

//TODO: make (almost) all methods static

static void seq_file_print_with_error(struct seq_file *s, const char *name,
				      ssize_t err, int value)
{
	seq_printf(s, "%s error: %ld\n", name, err);
	seq_printf(s, "%s: %d\n", name, value);
}

static int debugfs_fancurve_show(struct seq_file *s, void *unused)
{
	struct legion_private *priv = s->private;
	bool is_minifancurve;
	bool is_lockfancontroller;
	bool is_maximumfanspeed;
	bool is_rapidcharge = false;
	int powermode;
	int temperature;
	int fanspeed;
	int err;
	unsigned long cfg;
	struct fancurve wmi_fancurve;
	//int kb_backlight;

	mutex_lock(&priv->fancurve_mutex);

	seq_printf(s, "EC Chip ID: %x\n", read_ec_id(&priv->ecram, priv->conf));
	seq_printf(s, "EC Chip Version: %x\n",
		   read_ec_version(&priv->ecram, priv->conf));
	seq_printf(s, "legion_laptop features: %s\n", LEGIONFEATURES);
	seq_printf(s, "legion_laptop ec_readonly: %d\n", ec_readonly);

	err = eval_int(priv->adev->handle, "VPC0._CFG", &cfg);
	seq_printf(s, "ACPI CFG error: %d\n", err);
	seq_printf(s, "ACPI CFG: %lu\n", cfg);

	seq_printf(s, "temperature access method: %d\n",
		   priv->conf->access_method_temperature);
	err = read_temperature(priv, 0, &temperature);
	seq_file_print_with_error(s, "CPU temperature", err, temperature);
	err = ec_read_temperature(&priv->ecram, priv->conf, 0, &temperature);
	seq_file_print_with_error(s, "CPU temperature EC", err, temperature);
	err = acpi_read_temperature(priv, 0, &temperature);
	seq_file_print_with_error(s, "CPU temperature ACPI", err, temperature);
	err = wmi_read_temperature_gz(0, &temperature);
	seq_file_print_with_error(s, "CPU temperature WMI", err, temperature);
	err = wmi_read_temperature(0, &temperature);
	seq_file_print_with_error(s, "CPU temperature WMI2", err, temperature);
	err = wmi_read_temperature_other(0, &temperature);
	seq_file_print_with_error(s, "CPU temperature WMI3", err, temperature);

	err = read_temperature(priv, 1, &temperature);
	seq_file_print_with_error(s, "GPU temperature", err, temperature);
	err = ec_read_temperature(&priv->ecram, priv->conf, 1, &temperature);
	seq_file_print_with_error(s, "GPU temperature EC", err, temperature);
	err = acpi_read_temperature(priv, 1, &temperature);
	seq_file_print_with_error(s, "GPU temperature ACPI", err, temperature);
	err = wmi_read_temperature_gz(1, &temperature);
	seq_file_print_with_error(s, "GPU temperature WMI", err, temperature);
	err = wmi_read_temperature(1, &temperature);
	seq_file_print_with_error(s, "GPU temperature WMI2", err, temperature);
	err = wmi_read_temperature_other(1, &temperature);
	seq_file_print_with_error(s, "GPU temperature WMI3", err, temperature);

	seq_printf(s, "fan speed access method: %d\n",
		   priv->conf->access_method_fanspeed);
	err = read_fanspeed(priv, 0, &fanspeed);
	seq_file_print_with_error(s, "1 fanspeed", err, fanspeed);
	err = ec_read_fanspeed(&priv->ecram, priv->conf, 0, &fanspeed);
	seq_file_print_with_error(s, "1 fanspeed EC", err, fanspeed);
	err = acpi_read_fanspeed(priv, 0, &fanspeed);
	seq_file_print_with_error(s, "1 fanspeed ACPI", err, fanspeed);
	err = wmi_read_fanspeed_gz(0, &fanspeed);
	seq_file_print_with_error(s, "1 fanspeed WMI", err, fanspeed);
	err = wmi_read_fanspeed(0, &fanspeed);
	seq_file_print_with_error(s, "1 fanspeed WMI2", err, fanspeed);
	err = wmi_read_fanspeed_other(0, &fanspeed);
	seq_file_print_with_error(s, "1 fanspeed WMI3", err, fanspeed);

	err = read_fanspeed(priv, 1, &fanspeed);
	seq_file_print_with_error(s, "2 fanspeed", err, fanspeed);
	err = ec_read_fanspeed(&priv->ecram, priv->conf, 1, &fanspeed);
	seq_file_print_with_error(s, "2 fanspeed EC", err, fanspeed);
	err = acpi_read_fanspeed(priv, 1, &fanspeed);
	seq_file_print_with_error(s, "2 fanspeed ACPI", err, fanspeed);
	err = wmi_read_fanspeed_gz(1, &fanspeed);
	seq_file_print_with_error(s, "2 fanspeed WMI", err, fanspeed);
	err = wmi_read_fanspeed(1, &fanspeed);
	seq_file_print_with_error(s, "2 fanspeed WMI2", err, fanspeed);
	err = wmi_read_fanspeed_other(1, &fanspeed);
	seq_file_print_with_error(s, "2 fanspeed WMI3", err, fanspeed);

	seq_printf(s, "powermode access method: %d\n",
		   priv->conf->access_method_powermode);
	err = read_powermode(priv, &powermode);
	seq_file_print_with_error(s, "powermode", err, powermode);
	err = ec_read_powermode(priv, &powermode);
	seq_file_print_with_error(s, "powermode EC", err, powermode);
	err = acpi_read_powermode(priv, &powermode);
	seq_file_print_with_error(s, "powermode ACPI", err, powermode);
	err = wmi_read_powermode(&powermode);
	seq_file_print_with_error(s, "powermode WMI", err, powermode);
	seq_printf(s, "has custom powermode: %d\n",
		   priv->conf->has_custom_powermode);

	err = acpi_read_rapidcharge(priv->adev, &is_rapidcharge);
	seq_printf(s, "ACPI rapidcharge error: %d\n", err);
	seq_printf(s, "ACPI rapidcharge: %d\n", is_rapidcharge);

	seq_printf(s, "WMI backlight 2 state: %ld\n",
		   legion_kbd_bl2_brightness_get(priv));
	seq_printf(s, "WMI backlight 3 state: %d\n",
		   legion_kbd_bl_brightness_get(priv));

	seq_printf(s, "WMI light IO port: %d\n",
		   legion_wmi_light_get(priv, LIGHT_ID_IOPORT, 0, 4));

	seq_printf(s, "WMI light y logo/lid: %d\n",
		   legion_wmi_light_get(priv, LIGHT_ID_YLOGO, 0, 4));

	seq_printf(s, "EC minifancurve feature enabled: %d\n",
		   priv->conf->has_minifancurve);
	err = ec_read_minifancurve(&priv->ecram, priv->conf, &is_minifancurve);
	seq_printf(s, "EC minifancurve on cool: %s\n",
		   err ? "error" : (is_minifancurve ? "true" : "false"));

	err = ec_read_lockfancontroller(&priv->ecram, priv->conf,
					&is_lockfancontroller);
	seq_printf(s, "EC lockfancontroller error: %d\n", err);
	seq_printf(s, "EC lockfancontroller: %s\n",
		   err ? "error" : (is_lockfancontroller ? "true" : "false"));

	err = read_fanfullspeed(priv, &is_maximumfanspeed);
	seq_file_print_with_error(s, "fanfullspeed", err, is_maximumfanspeed);

	err = ec_read_fanfullspeed(&priv->ecram, priv->conf,
				   &is_maximumfanspeed);
	seq_file_print_with_error(s, "fanfullspeed EC", err,
				  is_maximumfanspeed);

	read_fancurve(priv, &priv->fancurve);
	seq_printf(s, "EC fan curve current point id: %ld\n",
		   priv->fancurve.current_point_i);
	seq_printf(s, "EC fan curve points size: %ld\n", priv->fancurve.size);

	seq_puts(s, "Current fan curve in hardware:\n");
	fancurve_print_seqfile(&priv->fancurve, s);
	seq_puts(s, "=====================\n");
	mutex_unlock(&priv->fancurve_mutex);

	seq_puts(s, "Current fan curve in hardware (WMI; might be empty)\n");
	wmi_fancurve.size = 0;
	err = wmi_read_fancurve_custom(priv->conf, &wmi_fancurve);
	fancurve_print_seqfile(&wmi_fancurve, s);
	seq_puts(s, "=====================\n");
	return 0;
}

DEFINE_SHOW_ATTRIBUTE(debugfs_fancurve);

static void legion_debugfs_init(struct legion_private *priv)
{
	struct dentry *dir;

	// TODO: remove this note
	// Note: as other kernel modules, do not catch errors here
	// because if kernel is build without debugfs this
	// will return an error but module still has to
	// work, just without debugfs
	// TODO: what permissions; some modules do 400
	// other do 444
	dir = debugfs_create_dir(LEGION_DRVR_SHORTNAME, NULL);
	debugfs_create_file("fancurve", 0444, dir, priv,
			    &debugfs_fancurve_fops);
	debugfs_create_file("ecmemory", 0444, dir, priv,
			    &debugfs_ecmemory_fops);
	debugfs_create_file("ecmemoryram", 0444, dir, priv,
			    &debugfs_ecmemoryram_fops);

	priv->debugfs_dir = dir;
}

static void legion_debugfs_exit(struct legion_private *priv)
{
	pr_info("Unloading legion dubugfs\n");
	// The following is does nothing if pointer is NULL
	debugfs_remove_recursive(priv->debugfs_dir);
	priv->debugfs_dir = NULL;
	pr_info("Unloading legion dubugfs done\n");
}

/* =============================  */
/* sysfs interface                */
/* ============================   */

static int show_simple_wmi_attribute(struct device *dev,
				     struct device_attribute *attr, char *buf,
				     const char *guid, u8 instance,
				     u32 method_id, bool invert,
				     unsigned long scale)
{
	unsigned long state = 0;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	mutex_lock(&priv->fancurve_mutex);
	err = get_simple_wmi_attribute(priv, guid, instance, method_id, invert,
				       scale, &state);
	mutex_unlock(&priv->fancurve_mutex);

	if (err)
		return -EINVAL;

	return sysfs_emit(buf, "%lu\n", state);
}

static int show_simple_wmi_attribute_from_buffer(struct device *dev,
						 struct device_attribute *attr,
						 char *buf, const char *guid,
						 u8 instance, u32 method_id,
						 size_t ressize, size_t i,
						 int scale)
{
	u8 res[16];
	int err;
	int out;
	struct legion_private *priv = dev_get_drvdata(dev);

	if (ressize > ARRAY_SIZE(res)) {
		pr_info("Buffer to small for WMI result\n");
		return -EINVAL;
	}
	if (i >= ressize) {
		pr_info("Index not within buffer size\n");
		return -EINVAL;
	}

	mutex_lock(&priv->fancurve_mutex);
	err = wmi_exec_noarg_ints(guid, instance, method_id, res, ressize);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	out = scale * res[i];
	return sysfs_emit(buf, "%d\n", out);
}

static int store_simple_wmi_attribute(struct device *dev,
				      struct device_attribute *attr,
				      const char *buf, size_t count,
				      const char *guid, u8 instance,
				      u32 method_id, bool invert, int scale)
{
	int state;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	err = kstrtouint(buf, 0, &state);
	if (err)
		return err;
	err = set_simple_wmi_attribute(priv, guid, instance, method_id, invert,
				       scale, state);
	if (err)
		return err;
	return count;
}

static ssize_t lockfancontroller_show(struct device *dev,
				      struct device_attribute *attr, char *buf)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	bool is_lockfancontroller;
	int err;

	mutex_lock(&priv->fancurve_mutex);
	err = ec_read_lockfancontroller(&priv->ecram, priv->conf,
					&is_lockfancontroller);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	return sysfs_emit(buf, "%d\n", is_lockfancontroller);
}

static ssize_t lockfancontroller_store(struct device *dev,
				       struct device_attribute *attr,
				       const char *buf, size_t count)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	bool is_lockfancontroller;
	int err;

	err = kstrtobool(buf, &is_lockfancontroller);
	if (err)
		return err;

	mutex_lock(&priv->fancurve_mutex);
	err = ec_write_lockfancontroller(&priv->ecram, priv->conf,
					 is_lockfancontroller);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	return count;
}

static DEVICE_ATTR_RW(lockfancontroller);

static ssize_t rapidcharge_show(struct device *dev,
				struct device_attribute *attr, char *buf)
{
	bool state = false;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	mutex_lock(&priv->fancurve_mutex);
	err = acpi_read_rapidcharge(priv->adev, &state);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	return sysfs_emit(buf, "%d\n", state);
}

static ssize_t rapidcharge_store(struct device *dev,
				 struct device_attribute *attr, const char *buf,
				 size_t count)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	int state;
	int err;

	err = kstrtouint(buf, 0, &state);
	if (err)
		return err;

	mutex_lock(&priv->fancurve_mutex);
	err = acpi_write_rapidcharge(priv->adev, state);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	return count;
}

static DEVICE_ATTR_RW(rapidcharge);

static ssize_t issupportgpuoc_show(struct device *dev,
				   struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_ISSUPPORTGPUOC, false,
					 1);
}

static DEVICE_ATTR_RO(issupportgpuoc);

static ssize_t aslcodeversion_show(struct device *dev,
				   struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETVERSION, false, 1);
}

static DEVICE_ATTR_RO(aslcodeversion);

static ssize_t issupportcpuoc_show(struct device *dev,
				   struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_ISSUPPORTCPUOC, false,
					 1);
}

static DEVICE_ATTR_RO(issupportcpuoc);

static ssize_t winkey_show(struct device *dev, struct device_attribute *attr,
			   char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETWINKEYSTATUS, true,
					 1);
}

static ssize_t winkey_store(struct device *dev, struct device_attribute *attr,
			    const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  LEGION_WMI_GAMEZONE_GUID, 0,
					  WMI_METHOD_ID_SETWINKEYSTATUS, true,
					  1);
}

static DEVICE_ATTR_RW(winkey);

// on newer models the touchpad feature in ideapad does not work anymore, so
// we need this
static ssize_t touchpad_show(struct device *dev, struct device_attribute *attr,
			     char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETTPSTATUS, true, 1);
}

static ssize_t touchpad_store(struct device *dev, struct device_attribute *attr,
			      const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  LEGION_WMI_GAMEZONE_GUID, 0,
					  WMI_METHOD_ID_SETTPSTATUS, true, 1);
}

static DEVICE_ATTR_RW(touchpad);

static ssize_t gsync_show(struct device *dev, struct device_attribute *attr,
			  char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETGSYNCSTATUS, true, 1);
}

static ssize_t gsync_store(struct device *dev, struct device_attribute *attr,
			   const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  LEGION_WMI_GAMEZONE_GUID, 0,
					  WMI_METHOD_ID_SETGSYNCSTATUS, true,
					  1);
}

static DEVICE_ATTR_RW(gsync);

static ssize_t powerchargemode_show(struct device *dev,
				    struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETPOWERCHARGEMODE,
					 false, 1);
}
static DEVICE_ATTR_RO(powerchargemode);

static ssize_t overdrive_show(struct device *dev, struct device_attribute *attr,
			      char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETODSTATUS, false, 1);
}

static ssize_t overdrive_store(struct device *dev,
			       struct device_attribute *attr, const char *buf,
			       size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  LEGION_WMI_GAMEZONE_GUID, 0,
					  WMI_METHOD_ID_SETODSTATUS, false, 1);
}

static DEVICE_ATTR_RW(overdrive);

static ssize_t thermalmode_show(struct device *dev,
				struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETTHERMALMODE, false,
					 1);
}
static DEVICE_ATTR_RO(thermalmode);

// TOOD: probably remove again because provided by other means; only useful for overclocking
static ssize_t cpumaxfrequency_show(struct device *dev,
				    struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETCPUMAXFREQUENCY,
					 false, 1);
}
static DEVICE_ATTR_RO(cpumaxfrequency);

static ssize_t isacfitforoc_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_ISACFITFOROC, false, 1);
}
static DEVICE_ATTR_RO(isacfitforoc);

static ssize_t igpumode_show(struct device *dev, struct device_attribute *attr,
			     char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 LEGION_WMI_GAMEZONE_GUID, 0,
					 WMI_METHOD_ID_GETIGPUMODESTATUS, false,
					 1);
}

static ssize_t igpumode_store(struct device *dev, struct device_attribute *attr,
			      const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  LEGION_WMI_GAMEZONE_GUID, 0,
					  WMI_METHOD_ID_SETIGPUMODESTATUS,
					  false, 1);
}

static DEVICE_ATTR_RW(igpumode);

static ssize_t cpu_oc_show(struct device *dev, struct device_attribute *attr,
			   char *buf)
{
	return show_simple_wmi_attribute_from_buffer(
		dev, attr, buf, WMI_GUID_LENOVO_CPU_METHOD, 0,
		WMI_METHOD_ID_CPU_GET_OC_STATUS, 16, 0, 1);
}

static ssize_t cpu_oc_store(struct device *dev, struct device_attribute *attr,
			    const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  WMI_GUID_LENOVO_CPU_METHOD, 0,
					  WMI_METHOD_ID_CPU_SET_OC_STATUS,
					  false, 1);
}

static DEVICE_ATTR_RW(cpu_oc);

static ssize_t cpu_shortterm_powerlimit_show(struct device *dev,
					     struct device_attribute *attr,
					     char *buf)
{
	return show_simple_wmi_attribute_from_buffer(
		dev, attr, buf, WMI_GUID_LENOVO_CPU_METHOD, 0,
		WMI_METHOD_ID_CPU_GET_SHORTTERM_POWERLIMIT, 16, 0, 1);
}

static ssize_t cpu_shortterm_powerlimit_store(struct device *dev,
					      struct device_attribute *attr,
					      const char *buf, size_t count)
{
	return store_simple_wmi_attribute(
		dev, attr, buf, count, WMI_GUID_LENOVO_CPU_METHOD, 0,
		WMI_METHOD_ID_CPU_SET_SHORTTERM_POWERLIMIT, false, 1);
}

static DEVICE_ATTR_RW(cpu_shortterm_powerlimit);

static ssize_t cpu_longterm_powerlimit_show(struct device *dev,
					    struct device_attribute *attr,
					    char *buf)
{
	return show_simple_wmi_attribute_from_buffer(
		dev, attr, buf, WMI_GUID_LENOVO_CPU_METHOD, 0,
		WMI_METHOD_ID_CPU_GET_LONGTERM_POWERLIMIT, 16, 0, 1);
}

static ssize_t cpu_longterm_powerlimit_store(struct device *dev,
					     struct device_attribute *attr,
					     const char *buf, size_t count)
{
	return store_simple_wmi_attribute(
		dev, attr, buf, count, WMI_GUID_LENOVO_CPU_METHOD, 0,
		WMI_METHOD_ID_CPU_SET_LONGTERM_POWERLIMIT, false, 1);
}

static DEVICE_ATTR_RW(cpu_longterm_powerlimit);

static ssize_t cpu_default_powerlimit_show(struct device *dev,
					   struct device_attribute *attr,
					   char *buf)
{
	return show_simple_wmi_attribute(
		dev, attr, buf, WMI_GUID_LENOVO_CPU_METHOD, 0,
		WMI_METHOD_ID_CPU_GET_DEFAULT_POWERLIMIT, false, 1);
}

static DEVICE_ATTR_RO(cpu_default_powerlimit);

static ssize_t cpu_peak_powerlimit_show(struct device *dev,
					struct device_attribute *attr,
					char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 WMI_GUID_LENOVO_GPU_METHOD, 0,
					 WMI_METHOD_ID_CPU_GET_PEAK_POWERLIMIT,
					 false, 1);
}

static ssize_t cpu_peak_powerlimit_store(struct device *dev,
					 struct device_attribute *attr,
					 const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  WMI_GUID_LENOVO_GPU_METHOD, 0,
					  WMI_METHOD_ID_CPU_SET_PEAK_POWERLIMIT,
					  false, 1);
}

static DEVICE_ATTR_RW(cpu_peak_powerlimit);

static ssize_t cpu_apu_sppt_powerlimit_show(struct device *dev,
					    struct device_attribute *attr,
					    char *buf)
{
	return show_simple_wmi_attribute(
		dev, attr, buf, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_CPU_GET_APU_SPPT_POWERLIMIT, false, 1);
}

static ssize_t cpu_apu_sppt_powerlimit_store(struct device *dev,
					     struct device_attribute *attr,
					     const char *buf, size_t count)
{
	return store_simple_wmi_attribute(
		dev, attr, buf, count, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_CPU_SET_APU_SPPT_POWERLIMIT, false, 1);
}

static DEVICE_ATTR_RW(cpu_apu_sppt_powerlimit);

static ssize_t cpu_cross_loading_powerlimit_show(struct device *dev,
						 struct device_attribute *attr,
						 char *buf)
{
	return show_simple_wmi_attribute(
		dev, attr, buf, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_CPU_GET_CROSS_LOADING_POWERLIMIT, false, 1);
}

static ssize_t cpu_cross_loading_powerlimit_store(struct device *dev,
						  struct device_attribute *attr,
						  const char *buf, size_t count)
{
	return store_simple_wmi_attribute(
		dev, attr, buf, count, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_CPU_SET_CROSS_LOADING_POWERLIMIT, false, 1);
}

static DEVICE_ATTR_RW(cpu_cross_loading_powerlimit);

static ssize_t gpu_oc_show(struct device *dev, struct device_attribute *attr,
			   char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 WMI_GUID_LENOVO_GPU_METHOD, 0,
					 WMI_METHOD_ID_GPU_GET_OC_STATUS, false,
					 1);
}

static ssize_t gpu_oc_store(struct device *dev, struct device_attribute *attr,
			    const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  WMI_GUID_LENOVO_GPU_METHOD, 0,
					  WMI_METHOD_ID_GPU_SET_OC_STATUS,
					  false, 1);
}

static DEVICE_ATTR_RW(gpu_oc);

static ssize_t gpu_ppab_powerlimit_show(struct device *dev,
					struct device_attribute *attr,
					char *buf)
{
	return show_simple_wmi_attribute_from_buffer(
		dev, attr, buf, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_GPU_GET_PPAB_POWERLIMIT, 16, 0, 1);
}

static ssize_t gpu_ppab_powerlimit_store(struct device *dev,
					 struct device_attribute *attr,
					 const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  WMI_GUID_LENOVO_GPU_METHOD, 0,
					  WMI_METHOD_ID_GPU_SET_PPAB_POWERLIMIT,
					  false, 1);
}

static DEVICE_ATTR_RW(gpu_ppab_powerlimit);

static ssize_t gpu_ctgp_powerlimit_show(struct device *dev,
					struct device_attribute *attr,
					char *buf)
{
	return show_simple_wmi_attribute_from_buffer(
		dev, attr, buf, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_GPU_GET_CTGP_POWERLIMIT, 16, 0, 1);
}

static ssize_t gpu_ctgp_powerlimit_store(struct device *dev,
					 struct device_attribute *attr,
					 const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  WMI_GUID_LENOVO_GPU_METHOD, 0,
					  WMI_METHOD_ID_GPU_SET_CTGP_POWERLIMIT,
					  false, 1);
}

static DEVICE_ATTR_RW(gpu_ctgp_powerlimit);

static ssize_t gpu_ctgp2_powerlimit_show(struct device *dev,
					 struct device_attribute *attr,
					 char *buf)
{
	return show_simple_wmi_attribute_from_buffer(
		dev, attr, buf, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_GPU_GET_CTGP_POWERLIMIT, 16, 0x0C, 1);
}

static DEVICE_ATTR_RO(gpu_ctgp2_powerlimit);

// TOOD: probably remove again because provided by other means; only useful for overclocking
static ssize_t
gpu_default_ppab_ctrgp_powerlimit_show(struct device *dev,
				       struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(
		dev, attr, buf, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_GPU_GET_DEFAULT_PPAB_CTGP_POWERLIMIT, false, 1);
}
static DEVICE_ATTR_RO(gpu_default_ppab_ctrgp_powerlimit);

static ssize_t gpu_temperature_limit_show(struct device *dev,
					  struct device_attribute *attr,
					  char *buf)
{
	return show_simple_wmi_attribute(
		dev, attr, buf, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_GPU_GET_TEMPERATURE_LIMIT, false, 1);
}

static ssize_t gpu_temperature_limit_store(struct device *dev,
					   struct device_attribute *attr,
					   const char *buf, size_t count)
{
	return store_simple_wmi_attribute(
		dev, attr, buf, count, WMI_GUID_LENOVO_GPU_METHOD, 0,
		WMI_METHOD_ID_GPU_SET_TEMPERATURE_LIMIT, false, 1);
}

static DEVICE_ATTR_RW(gpu_temperature_limit);

// TOOD: probably remove again because provided by other means; only useful for overclocking
static ssize_t gpu_boost_clock_show(struct device *dev,
				    struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 WMI_GUID_LENOVO_GPU_METHOD, 0,
					 WMI_METHOD_ID_GPU_GET_BOOST_CLOCK,
					 false, 1);
}
static DEVICE_ATTR_RO(gpu_boost_clock);

static ssize_t fan_fullspeed_show(struct device *dev,
				  struct device_attribute *attr, char *buf)
{
	bool state = false;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	mutex_lock(&priv->fancurve_mutex);
	err = read_fanfullspeed(priv, &state);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	return sysfs_emit(buf, "%d\n", state);
}

static ssize_t fan_fullspeed_store(struct device *dev,
				   struct device_attribute *attr,
				   const char *buf, size_t count)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	int state;
	int err;

	err = kstrtouint(buf, 0, &state);
	if (err)
		return err;

	mutex_lock(&priv->fancurve_mutex);
	err = write_fanfullspeed(priv, state);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	return count;
}

static DEVICE_ATTR_RW(fan_fullspeed);

static ssize_t fan_maxspeed_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	return show_simple_wmi_attribute(dev, attr, buf,
					 WMI_GUID_LENOVO_FAN_METHOD, 0,
					 WMI_METHOD_ID_FAN_GET_MAXSPEED, false,
					 1);
}

static ssize_t fan_maxspeed_store(struct device *dev,
				  struct device_attribute *attr,
				  const char *buf, size_t count)
{
	return store_simple_wmi_attribute(dev, attr, buf, count,
					  WMI_GUID_LENOVO_FAN_METHOD, 0,
					  WMI_METHOD_ID_FAN_SET_MAXSPEED, false,
					  1);
}

static DEVICE_ATTR_RW(fan_maxspeed);

static ssize_t powermode_show(struct device *dev, struct device_attribute *attr,
			      char *buf)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	int power_mode;

	mutex_lock(&priv->fancurve_mutex);
	read_powermode(priv, &power_mode);
	mutex_unlock(&priv->fancurve_mutex);
	return sysfs_emit(buf, "%d\n", power_mode);
}

static void legion_platform_profile_notify(void);

static ssize_t powermode_store(struct device *dev,
			       struct device_attribute *attr, const char *buf,
			       size_t count)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	int powermode;
	int err;

	err = kstrtouint(buf, 0, &powermode);
	if (err)
		return err;

	mutex_lock(&priv->fancurve_mutex);
	err = write_powermode(priv, powermode);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	// TODO: better?
	// we have to wait a bit before change is done in hardware and
	// readback done after notifying returns correct value, otherwise
	// the notified reader will read old value
	msleep(500);
	legion_platform_profile_notify();

	return count;
}

static DEVICE_ATTR_RW(powermode);

static struct attribute *legion_sysfs_attributes[] = {
	&dev_attr_powermode.attr,
	&dev_attr_lockfancontroller.attr,
	&dev_attr_rapidcharge.attr,
	&dev_attr_winkey.attr,
	&dev_attr_touchpad.attr,
	&dev_attr_gsync.attr,
	&dev_attr_powerchargemode.attr,
	&dev_attr_overdrive.attr,
	&dev_attr_cpumaxfrequency.attr,
	&dev_attr_isacfitforoc.attr,
	&dev_attr_cpu_oc.attr,
	&dev_attr_cpu_shortterm_powerlimit.attr,
	&dev_attr_cpu_longterm_powerlimit.attr,
	&dev_attr_cpu_apu_sppt_powerlimit.attr,
	&dev_attr_cpu_default_powerlimit.attr,
	&dev_attr_cpu_peak_powerlimit.attr,
	&dev_attr_cpu_cross_loading_powerlimit.attr,
	&dev_attr_gpu_oc.attr,
	&dev_attr_gpu_ppab_powerlimit.attr,
	&dev_attr_gpu_ctgp_powerlimit.attr,
	&dev_attr_gpu_ctgp2_powerlimit.attr,
	&dev_attr_gpu_default_ppab_ctrgp_powerlimit.attr,
	&dev_attr_gpu_temperature_limit.attr,
	&dev_attr_gpu_boost_clock.attr,
	&dev_attr_fan_fullspeed.attr,
	&dev_attr_fan_maxspeed.attr,
	&dev_attr_thermalmode.attr,
	&dev_attr_issupportcpuoc.attr,
	&dev_attr_issupportgpuoc.attr,
	&dev_attr_aslcodeversion.attr,
	&dev_attr_igpumode.attr,
	NULL
};

static const struct attribute_group legion_attribute_group = {
	.attrs = legion_sysfs_attributes
};

static int legion_sysfs_init(struct legion_private *priv)
{
	return device_add_group(&priv->platform_device->dev,
				&legion_attribute_group);
}

static void legion_sysfs_exit(struct legion_private *priv)
{
	pr_info("Unloading legion sysfs\n");
	device_remove_group(&priv->platform_device->dev,
			    &legion_attribute_group);
	pr_info("Unloading legion sysfs done\n");
}

/* =============================  */
/* WMI + ACPI                     */
/* ============================   */
// heavily based on ideapad_laptop.c

// TODO: proper names if meaning of all events is clear
enum LEGION_WMI_EVENT {
	LEGION_WMI_EVENT_GAMEZONE = 1,
	LEGION_EVENT_A,
	LEGION_EVENT_B,
	LEGION_EVENT_C,
	LEGION_EVENT_D,
	LEGION_EVENT_E,
	LEGION_EVENT_F,
	LEGION_EVENT_G
};

struct legion_wmi_private {
	enum LEGION_WMI_EVENT event;
};

//static void legion_wmi_notify2(u32 value, void *context)
//    {
//	pr_info("WMI notify\n" );
//    }

static void legion_wmi_notify(struct wmi_device *wdev, union acpi_object *data)
{
	struct legion_wmi_private *wpriv;
	struct legion_private *priv;

	mutex_lock(&legion_shared_mutex);
	priv = legion_shared;
	if ((!priv) && (priv->loaded)) {
		pr_info("Received WMI event while not initialized!\n");
		goto unlock;
	}

	wpriv = dev_get_drvdata(&wdev->dev);
	switch (wpriv->event) {
	case LEGION_EVENT_A:
		pr_info("Fan event: legion type: %d;  acpi type: %d (%d=integer)",
			wpriv->event, data->type, ACPI_TYPE_INTEGER);
		// TODO: here it is too early (first unlock mutext, then wait a bit)
		//legion_platform_profile_notify();
		break;
	default:
		pr_info("Event: legion type: %d;  acpi type: %d (%d=integer)",
			wpriv->event, data->type, ACPI_TYPE_INTEGER);
		break;
	}

unlock:
	mutex_unlock(&legion_shared_mutex);
	// todo; fix that!
	// problem: we get a event just before the powermode change (from the key?),
	// so if we notify to early, it will read the old power mode/platform profile
	msleep(500);
	legion_platform_profile_notify();
}

static int legion_wmi_probe(struct wmi_device *wdev, const void *context)
{
	struct legion_wmi_private *wpriv;

	wpriv = devm_kzalloc(&wdev->dev, sizeof(*wpriv), GFP_KERNEL);
	if (!wpriv)
		return -ENOMEM;

	*wpriv = *(const struct legion_wmi_private *)context;

	dev_set_drvdata(&wdev->dev, wpriv);
	dev_info(&wdev->dev, "Register after probing for WMI.\n");
	return 0;
}

static const struct legion_wmi_private legion_wmi_context_gamezone = {
	.event = LEGION_WMI_EVENT_GAMEZONE
};
static const struct legion_wmi_private legion_wmi_context_a = {
	.event = LEGION_EVENT_A
};
static const struct legion_wmi_private legion_wmi_context_b = {
	.event = LEGION_EVENT_B
};
static const struct legion_wmi_private legion_wmi_context_c = {
	.event = LEGION_EVENT_C
};
static const struct legion_wmi_private legion_wmi_context_d = {
	.event = LEGION_EVENT_D
};
static const struct legion_wmi_private legion_wmi_context_e = {
	.event = LEGION_EVENT_E
};
static const struct legion_wmi_private legion_wmi_context_f = {
	.event = LEGION_EVENT_F
};

#define LEGION_WMI_GUID_FAN_EVENT "D320289E-8FEA-41E0-86F9-611D83151B5F"
#define LEGION_WMI_GUID_FAN2_EVENT "bc72a435-e8c1-4275-b3e2-d8b8074aba59"
#define LEGION_WMI_GUID_GAMEZONE_KEY_EVENT \
	"10afc6d9-ea8b-4590-a2e7-1cd3c84bb4b1"
#define LEGION_WMI_GUID_GAMEZONE_GPU_EVENT \
	"bfd42481-aee3-4502-a107-afb68425c5f8"
#define LEGION_WMI_GUID_GAMEZONE_OC_EVENT "d062906b-12d4-4510-999d-4831ee80e985"
#define LEGION_WMI_GUID_GAMEZONE_TEMP_EVENT \
	"bfd42481-aee3-4501-a107-afb68425c5f8"
//#define LEGION_WMI_GUID_GAMEZONE_DATA_EVENT  "887b54e3-dddc-4b2c-8b88-68a26a8835d0"

static const struct wmi_device_id legion_wmi_ids[] = {
	{ LEGION_WMI_GAMEZONE_GUID, &legion_wmi_context_gamezone },
	{ LEGION_WMI_GUID_FAN_EVENT, &legion_wmi_context_a },
	{ LEGION_WMI_GUID_FAN2_EVENT, &legion_wmi_context_b },
	{ LEGION_WMI_GUID_GAMEZONE_KEY_EVENT, &legion_wmi_context_c },
	{ LEGION_WMI_GUID_GAMEZONE_GPU_EVENT, &legion_wmi_context_d },
	{ LEGION_WMI_GUID_GAMEZONE_OC_EVENT, &legion_wmi_context_e },
	{ LEGION_WMI_GUID_GAMEZONE_TEMP_EVENT, &legion_wmi_context_f },
	{ "8FC0DE0C-B4E4-43FD-B0F3-8871711C1294",
	  &legion_wmi_context_gamezone }, /* Legion 5 */
	{},
};
MODULE_DEVICE_TABLE(wmi, legion_wmi_ids);

static struct wmi_driver legion_wmi_driver = {
	.driver = {
		.name = "legion_wmi",
	},
	.id_table = legion_wmi_ids,
	.probe = legion_wmi_probe,
	.notify = legion_wmi_notify,
};

//acpi_status status = wmi_install_notify_handler(LEGION_WMI_GAMEZONE_GUID,
//				legion_wmi_notify2, NULL);
//if (ACPI_FAILURE(status)) {
//    return -ENODEV;
//}
//return 0;

static int legion_wmi_init(void)
{
	return wmi_driver_register(&legion_wmi_driver);
}

static void legion_wmi_exit(void)
{
	// TODO: remove this
	pr_info("Unloading legion WMI\n");

	//wmi_remove_notify_handler(LEGION_WMI_GAMEZONE_GUID);
	wmi_driver_unregister(&legion_wmi_driver);
	pr_info("Unloading legion WMI done\n");
}

/* =============================  */
/* Platform profile               */
/* ============================   */

static void legion_platform_profile_notify(void)
{
	if (!enable_platformprofile)
		pr_info("Skipping platform_profile_notify because enable_platformprofile is false\n");

	platform_profile_notify();
}

static int legion_platform_profile_get(struct platform_profile_handler *pprof,
				       enum platform_profile_option *profile)
{
	int powermode;
	struct legion_private *priv;

	priv = container_of(pprof, struct legion_private,
			    platform_profile_handler);
	read_powermode(priv, &powermode);

	switch (powermode) {
	case LEGION_WMI_POWERMODE_BALANCED:
		*profile = PLATFORM_PROFILE_BALANCED;
		break;
	case LEGION_WMI_POWERMODE_PERFORMANCE:
		*profile = PLATFORM_PROFILE_PERFORMANCE;
		break;
	case LEGION_WMI_POWERMODE_QUIET:
		*profile = PLATFORM_PROFILE_QUIET;
		break;
	case LEGION_WMI_POWERMODE_CUSTOM:
		*profile = PLATFORM_PROFILE_BALANCED_PERFORMANCE;
		break;
	default:
		return -EINVAL;
	}
	return 0;
}

static int legion_platform_profile_set(struct platform_profile_handler *pprof,
				       enum platform_profile_option profile)
{
	int powermode;
	struct legion_private *priv;

	priv = container_of(pprof, struct legion_private,
			    platform_profile_handler);

	switch (profile) {
	case PLATFORM_PROFILE_BALANCED:
		powermode = LEGION_WMI_POWERMODE_BALANCED;
		break;
	case PLATFORM_PROFILE_PERFORMANCE:
		powermode = LEGION_WMI_POWERMODE_PERFORMANCE;
		break;
	case PLATFORM_PROFILE_QUIET:
		powermode = LEGION_WMI_POWERMODE_QUIET;
		break;
	case PLATFORM_PROFILE_BALANCED_PERFORMANCE:
		powermode = LEGION_WMI_POWERMODE_CUSTOM;
		break;
	default:
		return -EOPNOTSUPP;
	}

	return write_powermode(priv, powermode);
}

static int legion_platform_profile_init(struct legion_private *priv)
{
	int err;

	if (!enable_platformprofile) {
		pr_info("Skipping creating platform profile support because enable_platformprofile is false\n");
		return 0;
	}

	priv->platform_profile_handler.profile_get =
		legion_platform_profile_get;
	priv->platform_profile_handler.profile_set =
		legion_platform_profile_set;

	set_bit(PLATFORM_PROFILE_QUIET, priv->platform_profile_handler.choices);
	set_bit(PLATFORM_PROFILE_BALANCED,
		priv->platform_profile_handler.choices);
	set_bit(PLATFORM_PROFILE_PERFORMANCE,
		priv->platform_profile_handler.choices);
	if (priv->conf->has_custom_powermode &&
	    priv->conf->access_method_powermode == ACCESS_METHOD_WMI) {
		set_bit(PLATFORM_PROFILE_BALANCED_PERFORMANCE,
			priv->platform_profile_handler.choices);
	}

	err = platform_profile_register(&priv->platform_profile_handler);
	if (err)
		return err;

	return 0;
}

static void legion_platform_profile_exit(struct legion_private *priv)
{
	if (!enable_platformprofile) {
		pr_info("Skipping unloading platform profile support because enable_platformprofile is false\n");
		return;
	}
	pr_info("Unloading legion platform profile\n");
	platform_profile_remove();
	pr_info("Unloading legion platform profile done\n");
}

/* =============================  */
/* hwom interface              */
/* ============================   */

// hw-mon interface

// todo: register_group or register_info?

// TODO: use one common function (like here) or one function per attribute?
static ssize_t sensor_label_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	int sensor_id = (to_sensor_dev_attr(attr))->index;
	const char *label;

	switch (sensor_id) {
	case SENSOR_CPU_TEMP_ID:
		label = "CPU Temperature\n";
		break;
	case SENSOR_GPU_TEMP_ID:
		label = "GPU Temperature\n";
		break;
	case SENSOR_IC_TEMP_ID:
		label = "IC Temperature\n";
		break;
	case SENSOR_FAN1_RPM_ID:
		label = "Fan 1\n";
		break;
	case SENSOR_FAN2_RPM_ID:
		label = "Fan 2\n";
		break;
	case SENSOR_FAN1_TARGET_RPM_ID:
		label = "Fan 1 Target\n";
		break;
	case SENSOR_FAN2_TARGET_RPM_ID:
		label = "Fan 2 Target\n";
		break;
	default:
		return -EOPNOTSUPP;
	}

	return sprintf(buf, label);
}

// TODO: use one common function (like here) or one function per attribute?
static ssize_t sensor_show(struct device *dev, struct device_attribute *devattr,
			   char *buf)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	int sensor_id = (to_sensor_dev_attr(devattr))->index;
	struct sensor_values values;
	int outval;
	int err = -EIO;

	switch (sensor_id) {
	case SENSOR_CPU_TEMP_ID:
		err = read_temperature(priv, 0, &outval);
		outval *= 1000;
		break;
	case SENSOR_GPU_TEMP_ID:
		err = read_temperature(priv, 1, &outval);
		outval *= 1000;
		break;
	case SENSOR_IC_TEMP_ID:
		ec_read_sensor_values(&priv->ecram, priv->conf, &values);
		outval = 1000 * values.ic_temp_celsius;
		err = 0;
		break;
	case SENSOR_FAN1_RPM_ID:
		err = read_fanspeed(priv, 0, &outval);
		break;
	case SENSOR_FAN2_RPM_ID:
		err = read_fanspeed(priv, 1, &outval);
		break;
	case SENSOR_FAN1_TARGET_RPM_ID:
		ec_read_sensor_values(&priv->ecram, priv->conf, &values);
		outval = values.fan1_target_rpm;
		err = 0;
		break;
	case SENSOR_FAN2_TARGET_RPM_ID:
		ec_read_sensor_values(&priv->ecram, priv->conf, &values);
		outval = values.fan2_target_rpm;
		err = 0;
		break;
	default:
		pr_info("Error reading sensor value with id %d\n", sensor_id);
		return -EOPNOTSUPP;
	}
	if (err)
		return err;

	return sprintf(buf, "%d\n", outval);
}

static SENSOR_DEVICE_ATTR_RO(temp1_input, sensor, SENSOR_CPU_TEMP_ID);
static SENSOR_DEVICE_ATTR_RO(temp1_label, sensor_label, SENSOR_CPU_TEMP_ID);
static SENSOR_DEVICE_ATTR_RO(temp2_input, sensor, SENSOR_GPU_TEMP_ID);
static SENSOR_DEVICE_ATTR_RO(temp2_label, sensor_label, SENSOR_GPU_TEMP_ID);
static SENSOR_DEVICE_ATTR_RO(temp3_input, sensor, SENSOR_IC_TEMP_ID);
static SENSOR_DEVICE_ATTR_RO(temp3_label, sensor_label, SENSOR_IC_TEMP_ID);
static SENSOR_DEVICE_ATTR_RO(fan1_input, sensor, SENSOR_FAN1_RPM_ID);
static SENSOR_DEVICE_ATTR_RO(fan1_label, sensor_label, SENSOR_FAN1_RPM_ID);
static SENSOR_DEVICE_ATTR_RO(fan2_input, sensor, SENSOR_FAN2_RPM_ID);
static SENSOR_DEVICE_ATTR_RO(fan2_label, sensor_label, SENSOR_FAN2_RPM_ID);
static SENSOR_DEVICE_ATTR_RO(fan1_target, sensor, SENSOR_FAN1_TARGET_RPM_ID);
static SENSOR_DEVICE_ATTR_RO(fan2_target, sensor, SENSOR_FAN2_TARGET_RPM_ID);

static struct attribute *sensor_hwmon_attributes[] = {
	&sensor_dev_attr_temp1_input.dev_attr.attr,
	&sensor_dev_attr_temp1_label.dev_attr.attr,
	&sensor_dev_attr_temp2_input.dev_attr.attr,
	&sensor_dev_attr_temp2_label.dev_attr.attr,
	&sensor_dev_attr_temp3_input.dev_attr.attr,
	&sensor_dev_attr_temp3_label.dev_attr.attr,
	&sensor_dev_attr_fan1_input.dev_attr.attr,
	&sensor_dev_attr_fan1_label.dev_attr.attr,
	&sensor_dev_attr_fan2_input.dev_attr.attr,
	&sensor_dev_attr_fan2_label.dev_attr.attr,
	&sensor_dev_attr_fan1_target.dev_attr.attr,
	&sensor_dev_attr_fan2_target.dev_attr.attr,
	NULL
};

static ssize_t autopoint_show(struct device *dev,
			      struct device_attribute *devattr, char *buf)
{
	struct fancurve fancurve;
	int err;
	int value;
	struct legion_private *priv = dev_get_drvdata(dev);
	int fancurve_attr_id = to_sensor_dev_attr_2(devattr)->nr;
	int point_id = to_sensor_dev_attr_2(devattr)->index;

	mutex_lock(&priv->fancurve_mutex);
	err = read_fancurve(priv, &fancurve);
	mutex_unlock(&priv->fancurve_mutex);

	if (err) {
		pr_info("Reading fancurve failed\n");
		return -EOPNOTSUPP;
	}
	if (!(point_id >= 0 && point_id < MAXFANCURVESIZE)) {
		pr_info("Reading fancurve failed due to wrong point id: %d\n",
			point_id);
		return -EOPNOTSUPP;
	}

	switch (fancurve_attr_id) {
	case FANCURVE_ATTR_PWM1:
		value = fancurve.points[point_id].rpm1_raw * 100;
		break;
	case FANCURVE_ATTR_PWM2:
		value = fancurve.points[point_id].rpm2_raw * 100;
		break;
	case FANCURVE_ATTR_CPU_TEMP:
		value = fancurve.points[point_id].cpu_max_temp_celsius;
		break;
	case FANCURVE_ATTR_CPU_HYST:
		value = fancurve.points[point_id].cpu_min_temp_celsius;
		break;
	case FANCURVE_ATTR_GPU_TEMP:
		value = fancurve.points[point_id].gpu_max_temp_celsius;
		break;
	case FANCURVE_ATTR_GPU_HYST:
		value = fancurve.points[point_id].gpu_min_temp_celsius;
		break;
	case FANCURVE_ATTR_IC_TEMP:
		value = fancurve.points[point_id].ic_max_temp_celsius;
		break;
	case FANCURVE_ATTR_IC_HYST:
		value = fancurve.points[point_id].ic_min_temp_celsius;
		break;
	case FANCURVE_ATTR_ACCEL:
		value = fancurve.points[point_id].accel;
		break;
	case FANCURVE_ATTR_DECEL:
		value = fancurve.points[point_id].decel;
		break;
	case FANCURVE_SIZE:
		value = fancurve.size;
		break;
	default:
		pr_info("Reading fancurve failed due to wrong attribute id: %d\n",
			fancurve_attr_id);
		return -EOPNOTSUPP;
	}

	return sprintf(buf, "%d\n", value);
}

static ssize_t autopoint_store(struct device *dev,
			       struct device_attribute *devattr,
			       const char *buf, size_t count)
{
	struct fancurve fancurve;
	int err;
	int value;
	bool valid;
	struct legion_private *priv = dev_get_drvdata(dev);
	int fancurve_attr_id = to_sensor_dev_attr_2(devattr)->nr;
	int point_id = to_sensor_dev_attr_2(devattr)->index;
	bool write_fancurve_size = false;

	if (!(point_id >= 0 && point_id < MAXFANCURVESIZE)) {
		pr_info("Reading fancurve failed due to wrong point id: %d\n",
			point_id);
		err = -EOPNOTSUPP;
		goto error;
	}

	err = kstrtoint(buf, 0, &value);
	if (err) {
		pr_info("Parse for hwmon store is not succesful: error:%d; point_id: %d; fancurve_attr_id: %d\\n",
			err, point_id, fancurve_attr_id);
		goto error;
	}

	mutex_lock(&priv->fancurve_mutex);
	err = read_fancurve(priv, &fancurve);

	if (err) {
		pr_info("Reading fancurve failed\n");
		err = -EOPNOTSUPP;
		goto error_mutex;
	}

	switch (fancurve_attr_id) {
	case FANCURVE_ATTR_PWM1:
		valid = fancurve_set_rpm1(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_PWM2:
		valid = fancurve_set_rpm2(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_CPU_TEMP:
		valid = fancurve_set_cpu_temp_max(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_CPU_HYST:
		valid = fancurve_set_cpu_temp_min(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_GPU_TEMP:
		valid = fancurve_set_gpu_temp_max(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_GPU_HYST:
		valid = fancurve_set_gpu_temp_min(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_IC_TEMP:
		valid = fancurve_set_ic_temp_max(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_IC_HYST:
		valid = fancurve_set_ic_temp_min(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_ACCEL:
		valid = fancurve_set_accel(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_DECEL:
		valid = fancurve_set_decel(&fancurve, point_id, value);
		break;
	case FANCURVE_SIZE:
		valid = fancurve_set_size(&fancurve, value, true);
		write_fancurve_size = true;
		break;
	default:
		pr_info("Writing fancurve failed due to wrong attribute id: %d\n",
			fancurve_attr_id);
		err = -EOPNOTSUPP;
		goto error_mutex;
	}

	if (!valid) {
		pr_info("Ignoring invalid fancurve value %d for attribute %d at point %d\n",
			value, fancurve_attr_id, point_id);
		err = -EOPNOTSUPP;
		goto error_mutex;
	}

	err = write_fancurve(priv, &fancurve, write_fancurve_size);
	if (err) {
		pr_info("Writing fancurve failed for accessing hwmon at point_id: %d\n",
			point_id);
		err = -EOPNOTSUPP;
		goto error_mutex;
	}

	mutex_unlock(&priv->fancurve_mutex);
	return count;

error_mutex:
	mutex_unlock(&priv->fancurve_mutex);
error:
	return count;
}

// rpm1
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point1_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point2_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point3_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point4_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point5_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point6_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point7_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point8_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point9_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point10_pwm, autopoint,
			       FANCURVE_ATTR_PWM1, 9);
// rpm2
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point1_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point2_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point3_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point4_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point5_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point6_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point7_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point8_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point9_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point10_pwm, autopoint,
			       FANCURVE_ATTR_PWM2, 9);
// CPU temp
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point1_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point2_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point3_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point4_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point5_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point6_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point7_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point8_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point9_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point10_temp, autopoint,
			       FANCURVE_ATTR_CPU_TEMP, 9);
// CPU temp hyst
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point1_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point2_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point3_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point4_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point5_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point6_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point7_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point8_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point9_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point10_temp_hyst, autopoint,
			       FANCURVE_ATTR_CPU_HYST, 9);
// GPU temp
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point1_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point2_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point3_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point4_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point5_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point6_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point7_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point8_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point9_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point10_temp, autopoint,
			       FANCURVE_ATTR_GPU_TEMP, 9);
// GPU temp hyst
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point1_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point2_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point3_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point4_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point5_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point6_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point7_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point8_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point9_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm2_auto_point10_temp_hyst, autopoint,
			       FANCURVE_ATTR_GPU_HYST, 9);
// IC temp
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point1_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point2_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point3_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point4_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point5_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point6_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point7_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point8_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point9_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point10_temp, autopoint,
			       FANCURVE_ATTR_IC_TEMP, 9);
// IC temp hyst
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point1_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point2_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point3_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point4_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point5_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point6_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point7_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point8_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point9_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm3_auto_point10_temp_hyst, autopoint,
			       FANCURVE_ATTR_IC_HYST, 9);
// accel
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point1_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point2_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point3_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point4_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point5_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point6_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point7_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point8_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point9_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point10_accel, autopoint,
			       FANCURVE_ATTR_ACCEL, 9);
// decel
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point1_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 0);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point2_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 1);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point3_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 2);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point4_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 3);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point5_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 4);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point6_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 5);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point7_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 6);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point8_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 7);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point9_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 8);
static SENSOR_DEVICE_ATTR_2_RW(pwm1_auto_point10_decel, autopoint,
			       FANCURVE_ATTR_DECEL, 9);
//size
static SENSOR_DEVICE_ATTR_2_RW(auto_points_size, autopoint, FANCURVE_SIZE, 0);

static ssize_t minifancurve_show(struct device *dev,
				 struct device_attribute *devattr, char *buf)
{
	bool value;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	mutex_lock(&priv->fancurve_mutex);
	err = ec_read_minifancurve(&priv->ecram, priv->conf, &value);
	if (err) {
		err = -1;
		pr_info("Reading minifancurve not succesful\n");
		goto error_unlock;
	}
	mutex_unlock(&priv->fancurve_mutex);
	return sprintf(buf, "%d\n", value);

error_unlock:
	mutex_unlock(&priv->fancurve_mutex);
	return -1;
}

static ssize_t minifancurve_store(struct device *dev,
				  struct device_attribute *devattr,
				  const char *buf, size_t count)
{
	int value;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	err = kstrtoint(buf, 0, &value);
	if (err) {
		err = -1;
		pr_info("Parse for hwmon store is not succesful: error:%d\n",
			err);
		goto error;
	}

	mutex_lock(&priv->fancurve_mutex);
	err = ec_write_minifancurve(&priv->ecram, priv->conf, value);
	if (err) {
		err = -1;
		pr_info("Writing minifancurve not succesful\n");
		goto error_unlock;
	}
	mutex_unlock(&priv->fancurve_mutex);
	return count;

error_unlock:
	mutex_unlock(&priv->fancurve_mutex);
error:
	return err;
}

static SENSOR_DEVICE_ATTR_RW(minifancurve, minifancurve, 0);

static ssize_t pwm1_mode_show(struct device *dev,
			      struct device_attribute *devattr, char *buf)
{
	bool value;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	mutex_lock(&priv->fancurve_mutex);
	err = ec_read_fanfullspeed(&priv->ecram, priv->conf, &value);
	if (err) {
		err = -1;
		pr_info("Reading pwm1_mode/maximumfanspeed not succesful\n");
		goto error_unlock;
	}
	mutex_unlock(&priv->fancurve_mutex);
	return sprintf(buf, "%d\n", value ? 0 : 2);

error_unlock:
	mutex_unlock(&priv->fancurve_mutex);
	return -1;
}

// TODO: remove? or use WMI method?
static ssize_t pwm1_mode_store(struct device *dev,
			       struct device_attribute *devattr,
			       const char *buf, size_t count)
{
	int value;
	int is_maximumfanspeed;
	int err;
	struct legion_private *priv = dev_get_drvdata(dev);

	err = kstrtoint(buf, 0, &value);
	if (err) {
		err = -1;
		pr_info("Parse for hwmon store is not succesful: error:%d\n",
			err);
		goto error;
	}
	is_maximumfanspeed = value == 0;

	mutex_lock(&priv->fancurve_mutex);
	err = ec_write_fanfullspeed(&priv->ecram, priv->conf,
				    is_maximumfanspeed);
	if (err) {
		err = -1;
		pr_info("Writing pwm1_mode/maximumfanspeed not succesful\n");
		goto error_unlock;
	}
	mutex_unlock(&priv->fancurve_mutex);
	return count;

error_unlock:
	mutex_unlock(&priv->fancurve_mutex);
error:
	return err;
}

static SENSOR_DEVICE_ATTR_RW(pwm1_mode, pwm1_mode, 0);

static struct attribute *fancurve_hwmon_attributes[] = {
	&sensor_dev_attr_pwm1_auto_point1_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point2_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point3_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point4_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point5_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point6_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point7_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point8_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point9_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point10_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point1_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point2_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point3_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point4_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point5_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point6_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point7_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point8_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point9_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point10_pwm.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point1_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point2_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point3_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point4_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point5_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point6_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point7_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point8_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point9_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point10_temp.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point1_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point2_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point3_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point4_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point5_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point6_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point7_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point8_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point9_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point10_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point1_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point2_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point3_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point4_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point5_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point6_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point7_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point8_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point9_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point10_temp.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point1_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point2_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point3_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point4_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point5_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point6_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point7_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point8_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point9_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm2_auto_point10_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point1_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point2_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point3_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point4_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point5_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point6_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point7_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point8_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point9_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point10_temp.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point1_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point2_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point3_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point4_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point5_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point6_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point7_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point8_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point9_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm3_auto_point10_temp_hyst.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point1_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point2_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point3_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point4_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point5_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point6_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point7_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point8_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point9_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point10_accel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point1_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point2_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point3_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point4_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point5_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point6_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point7_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point8_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point9_decel.dev_attr.attr,
	&sensor_dev_attr_pwm1_auto_point10_decel.dev_attr.attr,
	//
	&sensor_dev_attr_auto_points_size.dev_attr.attr,
	&sensor_dev_attr_minifancurve.dev_attr.attr,
	&sensor_dev_attr_pwm1_mode.dev_attr.attr, NULL
};

static umode_t legion_hwmon_is_visible(struct kobject *kobj,
				       struct attribute *attr, int idx)
{
	bool supported = true;
	struct device *dev = kobj_to_dev(kobj);
	struct legion_private *priv = dev_get_drvdata(dev);

	if (attr == &sensor_dev_attr_minifancurve.dev_attr.attr)
		supported = priv->conf->has_minifancurve;

	supported = supported && (priv->conf->access_method_fancurve !=
				  ACCESS_METHOD_NO_ACCESS);

	return supported ? attr->mode : 0;
}

static const struct attribute_group legion_hwmon_sensor_group = {
	.attrs = sensor_hwmon_attributes,
	.is_visible = NULL
};

static const struct attribute_group legion_hwmon_fancurve_group = {
	.attrs = fancurve_hwmon_attributes,
	.is_visible = legion_hwmon_is_visible,
};

static const struct attribute_group *legion_hwmon_groups[] = {
	&legion_hwmon_sensor_group, &legion_hwmon_fancurve_group, NULL
};

static ssize_t legion_hwmon_init(struct legion_private *priv)
{
	//TODO: use hwmon_device_register_with_groups or
	// hwmon_device_register_with_info (latter means all hwmon functions have to be
	// changed)
	// some laptop driver do it in one way, some in the other
	// TODO: Use devm_hwmon_device_register_with_groups ?
	// some laptop drivers use this, some
	struct device *hwmon_dev = hwmon_device_register_with_groups(
		&priv->platform_device->dev, "legion_hwmon", priv,
		legion_hwmon_groups);
	if (IS_ERR_OR_NULL(hwmon_dev)) {
		pr_err("hwmon_device_register failed!\n");
		return PTR_ERR(hwmon_dev);
	}
	dev_set_drvdata(hwmon_dev, priv);
	priv->hwmon_dev = hwmon_dev;
	return 0;
}

static void legion_hwmon_exit(struct legion_private *priv)
{
	pr_info("Unloading legion hwon\n");
	if (priv->hwmon_dev) {
		hwmon_device_unregister(priv->hwmon_dev);
		priv->hwmon_dev = NULL;
	}
	pr_info("Unloading legion hwon done\n");
}

/* ACPI*/

static int acpi_init(struct legion_private *priv, struct acpi_device *adev)
{
	int err;
	unsigned long cfg;
	bool skip_acpi_sta_check;
	struct device *dev = &priv->platform_device->dev;

	priv->adev = adev;
	if (!priv->adev) {
		dev_info(dev, "Could not get ACPI handle\n");
		goto err_acpi_init;
	}

	skip_acpi_sta_check = force || (!priv->conf->acpi_check_dev);
	if (!skip_acpi_sta_check) {
		err = eval_int(priv->adev->handle, "_STA", &cfg);
		if (err) {
			dev_info(dev, "Could not evaluate ACPI _STA\n");
			goto err_acpi_init;
		}

		err = eval_int(priv->adev->handle, "VPC0._CFG", &cfg);
		if (err) {
			dev_info(dev, "Could not evaluate ACPI _CFG\n");
			goto err_acpi_init;
		}
		dev_info(dev, "ACPI CFG: %lu\n", cfg);
	} else {
		dev_info(dev, "Skipping ACPI _STA check");
	}

	return 0;

err_acpi_init:
	return err;
}

/* =============================  */
/* White Keyboard Backlight       */
/* ============================   */
// In style of ideapad-driver and with code modified from ideapad-driver.

static enum led_brightness
legion_kbd_bl_led_cdev_brightness_get(struct led_classdev *led_cdev)
{
	struct legion_private *priv =
		container_of(led_cdev, struct legion_private, kbd_bl.led);

	return legion_kbd_bl_brightness_get(priv);
}

static int legion_kbd_bl_led_cdev_brightness_set(struct led_classdev *led_cdev,
						 enum led_brightness brightness)
{
	struct legion_private *priv =
		container_of(led_cdev, struct legion_private, kbd_bl.led);

	return legion_kbd_bl_brightness_set(priv, brightness);
}

static int legion_kbd_bl_init(struct legion_private *priv)
{
	int brightness, err;

	if (WARN_ON(priv->kbd_bl.initialized)) {
		pr_info("Keyboard backlight already initialized\n");
		return -EEXIST;
	}

	if (priv->conf->access_method_keyboard == ACCESS_METHOD_NO_ACCESS) {
		pr_info("Keyboard backlight handling disabled by this driver\n");
		return -ENODEV;
	}

	brightness = legion_kbd_bl_brightness_get(priv);
	if (brightness < 0) {
		pr_info("Error reading keyboard brighntess\n");
		return brightness;
	}

	priv->kbd_bl.last_brightness = brightness;

	// will be renamed to "platform::kbd_backlight_1" if it exists already
	priv->kbd_bl.led.name = "platform::" LED_FUNCTION_KBD_BACKLIGHT;
	priv->kbd_bl.led.max_brightness = 2;
	priv->kbd_bl.led.brightness_get = legion_kbd_bl_led_cdev_brightness_get;
	priv->kbd_bl.led.brightness_set_blocking =
		legion_kbd_bl_led_cdev_brightness_set;
	priv->kbd_bl.led.flags = LED_BRIGHT_HW_CHANGED;

	err = led_classdev_register(&priv->platform_device->dev,
				    &priv->kbd_bl.led);
	if (err)
		return err;

	priv->kbd_bl.initialized = true;

	return 0;
}

/**
 * Deinit keyboard backlight.
 *
 * Can also be called if init was not successful.
 *
 */
static void legion_kbd_bl_exit(struct legion_private *priv)
{
	if (!priv->kbd_bl.initialized)
		return;

	priv->kbd_bl.initialized = false;

	led_classdev_unregister(&priv->kbd_bl.led);
}

/* =============================  */
/* Additional light driver        */
/* ============================   */

static enum led_brightness
legion_wmi_cdev_brightness_get(struct led_classdev *led_cdev)
{
	struct legion_private *priv =
		container_of(led_cdev, struct legion_private, kbd_bl.led);
	struct light *light_ins = container_of(led_cdev, struct light, led);

	return legion_wmi_light_get(priv, light_ins->light_id,
				    light_ins->lower_limit,
				    light_ins->upper_limit);
}

static int legion_wmi_cdev_brightness_set(struct led_classdev *led_cdev,
					  enum led_brightness brightness)
{
	struct legion_private *priv =
		container_of(led_cdev, struct legion_private, kbd_bl.led);
	struct light *light_ins = container_of(led_cdev, struct light, led);

	return legion_wmi_light_set(priv, light_ins->light_id,
				    light_ins->lower_limit,
				    light_ins->upper_limit, brightness);
}

static int legion_light_init(struct legion_private *priv,
			     struct light *light_ins, u8 light_id,
			     u8 lower_limit, u8 upper_limit, const char *name)
{
	int brightness, err;

	if (WARN_ON(light_ins->initialized)) {
		pr_info("Light already initialized for light: %u\n",
			light_ins->light_id);
		return -EEXIST;
	}

	light_ins->light_id = light_id;
	light_ins->lower_limit = lower_limit;
	light_ins->upper_limit = upper_limit;

	brightness = legion_wmi_light_get(priv, light_ins->light_id,
					  light_ins->lower_limit,
					  light_ins->upper_limit);
	if (brightness < 0) {
		pr_info("Error reading brighntess for light: %u\n",
			light_ins->light_id);
		return brightness;
	}

	light_ins->led.name = name;
	light_ins->led.max_brightness =
		light_ins->upper_limit - light_ins->lower_limit;
	light_ins->led.brightness_get = legion_wmi_cdev_brightness_get;
	light_ins->led.brightness_set_blocking = legion_wmi_cdev_brightness_set;
	light_ins->led.flags = LED_BRIGHT_HW_CHANGED;

	err = led_classdev_register(&priv->platform_device->dev,
				    &light_ins->led);
	if (err)
		return err;

	light_ins->initialized = true;

	return 0;
}

/**
 * Deinit light.
 *
 * Can also be called if init was not successful.
 *
 */
static void legion_light_exit(struct legion_private *priv,
			      struct light *light_ins)
{
	if (!light_ins->initialized)
		return;

	light_ins->initialized = false;

	led_classdev_unregister(&light_ins->led);
}

/* =============================  */
/* Platform driver                */
/* ============================   */

static int legion_add(struct platform_device *pdev)
{
	struct legion_private *priv;
	const struct dmi_system_id *dmi_sys;
	int err;
	u16 ec_read_id;
	bool skip_ec_id_check;
	bool is_ec_id_valid;
	bool is_denied = true;
	bool is_allowed = false;
	bool do_load_by_list = false;
	bool do_load = false;
	//struct legion_private *priv = dev_get_drvdata(&pdev->dev);
	dev_info(&pdev->dev, "legion_laptop platform driver probing\n");

	dev_info(
		&pdev->dev,
		"Read identifying information: DMI_SYS_VENDOR: %s; DMI_PRODUCT_NAME: %s; DMI_BIOS_VERSION:%s\n",
		dmi_get_system_info(DMI_SYS_VENDOR),
		dmi_get_system_info(DMI_PRODUCT_NAME),
		dmi_get_system_info(DMI_BIOS_VERSION));

	// TODO: allocate?
	priv = &_priv;
	priv->platform_device = pdev;
	err = legion_shared_init(priv);
	if (err) {
		dev_info(&pdev->dev, "legion_laptop is forced to load.\n");
		goto err_legion_shared_init;
	}
	dev_set_drvdata(&pdev->dev, priv);

	// TODO: remove
	pr_info("Read identifying information: DMI_SYS_VENDOR: %s; DMI_PRODUCT_NAME: %s; DMI_BIOS_VERSION:%s\n",
		dmi_get_system_info(DMI_SYS_VENDOR),
		dmi_get_system_info(DMI_PRODUCT_NAME),
		dmi_get_system_info(DMI_BIOS_VERSION));

	dmi_sys = dmi_first_match(optimistic_allowlist);
	is_allowed = dmi_sys != NULL;
	is_denied = dmi_check_system(denylist);
	do_load_by_list = is_allowed && !is_denied;
	do_load = do_load_by_list || force;

	dev_info(
		&pdev->dev,
		"is_denied: %d; is_allowed: %d; do_load_by_list: %d; do_load: %d\n",
		is_denied, is_allowed, do_load_by_list, do_load);

	if (!(do_load)) {
		dev_info(
			&pdev->dev,
			"Module not useable for this laptop because it is not in allowlist. Notify maintainer if you want to add your device or force load with param force.\n");
		err = -ENOMEM;
		goto err_model_mismtach;
	}

	if (force)
		dev_info(&pdev->dev, "legion_laptop is forced to load.\n");

	if (!do_load_by_list && do_load) {
		dev_info(
			&pdev->dev,
			"legion_laptop is forced to load and would otherwise be not loaded\n");
	}

	// if forced and no module found, use config for first model
	if (dmi_sys == NULL)
		dmi_sys = &optimistic_allowlist[0];
	dev_info(&pdev->dev, "Using configuration for system: %s\n",
		 dmi_sys->ident);

	priv->conf = dmi_sys->driver_data;

	err = acpi_init(priv, ACPI_COMPANION(&pdev->dev));
	if (err) {
		dev_info(&pdev->dev, "Could not init ACPI access: %d\n", err);
		goto err_acpi_init;
	}

	// TODO: remove; only used for reverse engineering
	pr_info("Creating RAM access to embedded controller\n");
	err = ecram_memoryio_init(&priv->ec_memoryio,
				  priv->conf->ramio_physical_start, 0,
				  priv->conf->ramio_size);
	if (err) {
		dev_info(
			&pdev->dev,
			"Could not init RAM access to embedded controller: %d\n",
			err);
		goto err_ecram_memoryio_init;
	}

	err = ecram_init(&priv->ecram, priv->conf->memoryio_physical_ec_start,
			 priv->conf->memoryio_size);
	if (err) {
		dev_info(&pdev->dev,
			 "Could not init access to embedded controller: %d\n",
			 err);
		goto err_ecram_init;
	}

	ec_read_id = read_ec_id(&priv->ecram, priv->conf);
	dev_info(&pdev->dev, "Read embedded controller ID 0x%x\n", ec_read_id);
	skip_ec_id_check = force || (!priv->conf->check_embedded_controller_id);
	is_ec_id_valid = skip_ec_id_check ||
			 (ec_read_id == priv->conf->embedded_controller_id);
	if (!is_ec_id_valid) {
		err = -ENOMEM;
		dev_info(&pdev->dev, "Expected EC chip id 0x%x but read 0x%x\n",
			 priv->conf->embedded_controller_id, ec_read_id);
		goto err_ecram_id;
	}
	if (skip_ec_id_check) {
		dev_info(&pdev->dev,
			 "Skipped checking embedded controller id\n");
	}

	dev_info(&pdev->dev, "Creating debugfs inteface\n");
	legion_debugfs_init(priv);

	pr_info("Creating sysfs inteface\n");
	err = legion_sysfs_init(priv);
	if (err) {
		dev_info(&pdev->dev, "Creating sysfs interface failed: %d\n",
			 err);
		goto err_sysfs_init;
	}

	pr_info("Creating hwmon interface");
	err = legion_hwmon_init(priv);
	if (err) {
		dev_info(&pdev->dev, "Creating hwmon interface failed: %d\n",
			 err);
		goto err_hwmon_init;
	}

	pr_info("Creating platform profile support\n");
	err = legion_platform_profile_init(priv);
	if (err) {
		dev_info(&pdev->dev, "Creating platform profile failed: %d\n",
			 err);
		goto err_platform_profile;
	}

	pr_info("Init WMI driver support\n");
	err = legion_wmi_init();
	if (err) {
		dev_info(&pdev->dev, "Init WMI driver failed: %d\n", err);
		goto err_wmi;
	}

	pr_info("Init keyboard backlight LED driver\n");
	err = legion_kbd_bl_init(priv);
	if (err) {
		dev_info(
			&pdev->dev,
			"Init keyboard backlight LED driver failed. Skipping ...\n");
	}

	pr_info("Init Y-Logo LED driver\n");
	err = legion_light_init(priv, &priv->ylogo_light, LIGHT_ID_YLOGO, 0, 1,
				"platform::ylogo");
	if (err) {
		dev_info(&pdev->dev,
			 "Init Y-Logo LED driver failed. Skipping ...\n");
	}

	pr_info("Init IO-Port LED driver\n");
	err = legion_light_init(priv, &priv->iport_light, LIGHT_ID_IOPORT, 1, 2,
				"platform::ioport");
	if (err) {
		dev_info(&pdev->dev,
			 "Init IO-Port LED driver failed. Skipping ...\n");
	}

	dev_info(&pdev->dev, "legion_laptop loaded for this device\n");
	return 0;

	// TODO: remove eventually
	legion_light_exit(priv, &priv->iport_light);
	legion_light_exit(priv, &priv->ylogo_light);
	legion_kbd_bl_exit(priv);
	legion_wmi_exit();
err_wmi:
	legion_platform_profile_exit(priv);
err_platform_profile:
	legion_hwmon_exit(priv);
err_hwmon_init:
	legion_sysfs_exit(priv);
err_sysfs_init:
	legion_debugfs_exit(priv);
err_ecram_id:
	ecram_exit(&priv->ecram);
err_ecram_init:
	ecram_memoryio_exit(&priv->ec_memoryio);
err_ecram_memoryio_init:
err_acpi_init:
	legion_shared_exit(priv);
err_legion_shared_init:
err_model_mismtach:
	dev_info(&pdev->dev, "legion_laptop not loaded for this device\n");
	return err;
}

static int legion_remove(struct platform_device *pdev)
{
	struct legion_private *priv = dev_get_drvdata(&pdev->dev);

	mutex_lock(&legion_shared_mutex);
	priv->loaded = false;
	mutex_unlock(&legion_shared_mutex);

	legion_light_exit(priv, &priv->iport_light);
	legion_light_exit(priv, &priv->ylogo_light);
	legion_kbd_bl_exit(priv);
	// first unregister wmi, so toggling powermode does not
	// generate events anymore that even might be delayed
	legion_wmi_exit();
	legion_platform_profile_exit(priv);

	// toggle power mode to load default setting from embedded controller
	// again
	toggle_powermode(priv);

	legion_hwmon_exit(priv);
	legion_sysfs_exit(priv);
	legion_debugfs_exit(priv);
	ecram_exit(&priv->ecram);
	ecram_memoryio_exit(&priv->ec_memoryio);
	legion_shared_exit(priv);

	pr_info("Legion platform unloaded\n");
	return 0;
}

static int legion_resume(struct platform_device *pdev)
{
	//struct legion_private *priv = dev_get_drvdata(&pdev->dev);
	dev_info(&pdev->dev, "Resumed in legion-laptop\n");

	return 0;
}

#ifdef CONFIG_PM_SLEEP
static int legion_pm_resume(struct device *dev)
{
	//struct legion_private *priv = dev_get_drvdata(dev);
	dev_info(dev, "Resumed PM in legion-laptop\n");

	return 0;
}
#endif
static SIMPLE_DEV_PM_OPS(legion_pm, NULL, legion_pm_resume);

// same as ideapad
static const struct acpi_device_id legion_device_ids[] = {
	// todo: change to "VPC2004", and also ACPI paths
	{ "PNP0C09", 0 },
	{ "", 0 },
};
MODULE_DEVICE_TABLE(acpi, legion_device_ids);

static struct platform_driver legion_driver = {
	.probe = legion_add,
	.remove = legion_remove,
	.resume = legion_resume,
	.driver = {
		.name   = "legion",
		.pm     = &legion_pm,
		.acpi_match_table = ACPI_PTR(legion_device_ids),
	},
};

static int __init legion_init(void)
{
	int err;

	pr_info("legion_laptop starts loading\n");
	err = platform_driver_register(&legion_driver);
	if (err) {
		pr_info("legion_laptop: platform_driver_register failed\n");
		return err;
	}

	return 0;
}

module_init(legion_init);

static void __exit legion_exit(void)
{
	platform_driver_unregister(&legion_driver);
	pr_info("legion_laptop exit\n");
}

module_exit(legion_exit);
