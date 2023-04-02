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

#include <linux/acpi.h>
#include <asm/io.h>
#include <linux/debugfs.h>
#include <linux/delay.h>
#include <linux/dmi.h>
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

#define LEGIONFEATURES \
	"fancurve powermode platformprofile platformprofilenotify minifancurve"

//Size of fancurve stored in embedded controller
#define MAXFANCURVESIZE 10

#define LEGION_DRVR_SHORTNAME "legion"
#define LEGION_HWMON_NAME LEGION_DRVR_SHORTNAME "_hwmon"

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

struct model_config {
	const struct ec_register_offsets *registers;
	bool check_embedded_controller_id;
	u16 embedded_controller_id;

	// first addr in EC we access/scan
	phys_addr_t memoryio_physical_ec_start;
	size_t memoryio_size;

	// TODO: maybe use bitfield
	bool has_minifancurve;
};

/* =================================== */
/* Coinfiguration for different models */
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

static const struct model_config model_v0 = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = true
};

static const struct model_config model_kfcn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = true,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false
};

static const struct model_config model_hacn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400,
	.memoryio_size = 0x300,
	.has_minifancurve = false
};


static const struct model_config model_k9cn = {
	.registers = &ec_register_offsets_v0,
	.check_embedded_controller_id = false,
	.embedded_controller_id = 0x8227,
	.memoryio_physical_ec_start = 0xC400, // or replace 0xC400 by 0x0400  ?
	.memoryio_size = 0x300,
	.has_minifancurve = false
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
		.driver_data = (void *)&model_v0
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
	{}
};

/* ================================= */
/* ACPI access                       */
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
	return exec_simple_method(handle, "SBMC", arg);
}

static int eval_qcho(acpi_handle handle, unsigned long *res)
{
	// \_SB.PCI0.LPC0.EC0.QCHO
	return eval_int(handle, "QCHO", res);
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

ssize_t ecram_portio_init(struct ecram_portio *ec_portio)
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

void ecram_portio_exit(struct ecram_portio *ec_portio)
{
	release_region(ECRAM_PORTIO_START_PORT, ECRAM_PORTIO_PORTS_SIZE);
}

/* Read a byte from the EC RAM.
 *
 * Return status because of commong signature for alle
 * methods to access EC RAM.
 */
ssize_t ecram_portio_read(struct ecram_portio *ec_portio, u16 offset, u8 *value)
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
ssize_t ecram_portio_write(struct ecram_portio *ec_portio, u16 offset, u8 value)
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
	return 0;
}

/* =================================== */
/* EC RAM Access                       */
/* =================================== */

struct ecram {
	struct ecram_portio portio;
};

ssize_t ecram_init(struct ecram *ecram, phys_addr_t memoryio_ec_physical_start,
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

void ecram_exit(struct ecram *ecram)
{
	pr_info("Unloading legion ecram\n");
	ecram_portio_exit(&ecram->portio);
	pr_info("Unloading legion ecram done\n");
}

/**
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

u16 read_ec_id(struct ecram *ecram, const struct model_config *model)
{
	u8 id1 = ecram_read(ecram, model->registers->ECHIPID1);
	u8 id2 = ecram_read(ecram, model->registers->ECHIPID2);

	return (id1 << 8) + id2;
}

u16 read_ec_version(struct ecram *ecram, const struct model_config *model)
{
	u8 vers = ecram_read(ecram, model->registers->ECHIPVER);
	u8 debug = ecram_read(ecram, model->registers->ECDEBUG);

	return (vers << 8) + debug;
}

/* ============================= */
/* Data model for sensor values  */
/* ============================  */

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

static int read_sensor_values(struct ecram *ecram,
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

/* =============================== */
/* Behaviour changing functions    */
/* =============================== */

int read_powermode(struct ecram *ecram, const struct model_config *model)
{
	return ecram_read(ecram, model->registers->EXT_POWERMODE);
}

ssize_t write_powermode(struct ecram *ecram, const struct model_config *model,
			u8 value)
{
	if (!(value >= 0 && value <= 2)) {
		pr_info("Unexpected power mode value ignored: %d\n", value);
		return -ENOMEM;
	}
	ecram_write(ecram, model->registers->EXT_POWERMODE, value);
	return 0;
}

/**
 * Shortly toggle powermode to a different mode
 * and switch back, e.g. to reset fan curve.
 */
void toggle_powermode(struct ecram *ecram, const struct model_config *model)
{
	int old_powermode = read_powermode(ecram, model);
	int next_powermode = old_powermode == 0 ? 1 : 0;

	write_powermode(ecram, model, next_powermode);
	mdelay(1500);
	write_powermode(ecram, model, old_powermode);
}

#define lockfancontroller_ON 8
#define lockfancontroller_OFF 0

ssize_t write_lockfancontroller(struct ecram *ecram,
				const struct model_config *model, bool state)
{
	u8 val = state ? lockfancontroller_ON : lockfancontroller_OFF;

	ecram_write(ecram, model->registers->EXT_LOCKFANCONTROLLER, val);
	return 0;
}

int read_lockfancontroller(struct ecram *ecram,
			   const struct model_config *model, bool *state)
{
	int value = ecram_read(ecram, model->registers->EXT_LOCKFANCONTROLLER);

	switch (value) {
	case lockfancontroller_ON:
		*state = true;
		break;
	case lockfancontroller_OFF:
		*state = false;
		break;
	default:
		pr_info("Unexpected value in lockfanspeed register:%d\n",
			value);
		return -1;
	}
	return 0;
}

#define MAXIMUMFANSPEED_ON 0x40
#define MAXIMUMFANSPEED_OFF 0x00

int read_maximumfanspeed(struct ecram *ecram, const struct model_config *model,
			 bool *state)
{
	int value = ecram_read(ecram, model->registers->EXT_MAXIMUMFANSPEED);

	switch (value) {
	case MAXIMUMFANSPEED_ON:
		*state = true;
		break;
	case MAXIMUMFANSPEED_OFF:
		*state = false;
		break;
	default:
		pr_info("Unexpected value in maximumfanspeed register:%d\n",
			value);
		return -1;
	}
	return 0;
}

ssize_t write_maximumfanspeed(struct ecram *ecram,
			      const struct model_config *model, bool state)
{
	u8 val = state ? MAXIMUMFANSPEED_ON : MAXIMUMFANSPEED_OFF;

	ecram_write(ecram, model->registers->EXT_MAXIMUMFANSPEED, val);
	return 0;
}

#define MINIFANCUVE_ON_COOL_ON 0x04
#define MINIFANCUVE_ON_COOL_OFF 0xA0

int read_minifancurve(struct ecram *ecram, const struct model_config *model,
		      bool *state)
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

ssize_t write_minifancurve(struct ecram *ecram,
			   const struct model_config *model, bool state)
{
	u8 val = state ? MINIFANCUVE_ON_COOL_ON : MINIFANCUVE_ON_COOL_OFF;

	ecram_write(ecram, model->registers->EXT_MINIFANCURVE_ON_COOL, val);
	return 0;
}

#define KEYBOARD_BACKLIGHT_OFF 18
#define KEYBOARD_BACKLIGHT_ON1 21
#define KEYBOARD_BACKLIGHT_ON2 23

int read_keyboard_backlight(struct ecram *ecram,
			    const struct model_config *model, int *state)
{
	int value = ecram_read(ecram,
			       model->registers->EXT_WHITE_KEYBOARD_BACKLIGHT);

	//switch (value) {
	//case MINIFANCUVE_ON_COOL_ON:
	//	*state = true;
	//	break;
	//case MINIFANCUVE_ON_COOL_OFF:
	//	*state = false;
	//	break;
	//default:
	//	pr_info("Unexpected value in MINIFANCURVE register:%d\n",
	//		value);
	//	return -1;
	//}
	*state = value;
	return 0;
}

int write_keyboard_backlight(struct ecram *ecram,
			     const struct model_config *model, int state)
{
	u8 val = state > 0 ? KEYBOARD_BACKLIGHT_ON1 : KEYBOARD_BACKLIGHT_OFF;

	ecram_write(ecram, model->registers->EXT_WHITE_KEYBOARD_BACKLIGHT, val);
	return 0;
}

#define FCT_RAPID_CHARGE_ON 0x07
#define FCT_RAPID_CHARGE_OFF 0x08
#define RAPID_CHARGE_ON 0x0
#define RAPID_CHARGE_OFF 0x1

int read_rapidcharge(acpi_handle acpihandle, int *state)
{
	unsigned long result;
	int err;

	err = eval_qcho(acpihandle, &result);
	if (err)
		return err;

	*state = result;
	return 0;
}

int write_rapidcharge(acpi_handle acpihandle, bool state)
{
	unsigned long fct_nr = state > 0 ? FCT_RAPID_CHARGE_ON :
					   FCT_RAPID_CHARGE_OFF;
	return exec_sbmc(acpihandle, fct_nr);
}

/* ============================= */
/* Data model for fan curve      */
/* ============================  */

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

// calculate derived values

int fancurve_get_cpu_deltahyst(struct fancurve_point *point)
{
	return ((int)point->cpu_max_temp_celsius) -
	       ((int)point->cpu_min_temp_celsius);
}

int fancurve_get_gpu_deltahyst(struct fancurve_point *point)
{
	return ((int)point->gpu_max_temp_celsius) -
	       ((int)point->gpu_min_temp_celsius);
}

int fancurve_get_ic_deltahyst(struct fancurve_point *point)
{
	return ((int)point->ic_max_temp_celsius) -
	       ((int)point->ic_min_temp_celsius);
}

// validation functions

bool fancurve_is_valid_min_temp(int min_temp)
{
	return min_temp >= 0 && min_temp <= 127;
}

bool fancurve_is_valid_max_temp(int max_temp)
{
	return max_temp >= 0 && max_temp <= 127;
}

// setters with validation
// - make hwmon implementation easier
// - keep fancurve valid, otherwise EC will not properly control fan

bool fancurve_set_rpm1(struct fancurve *fancurve, int point_id, int rpm)
{
	bool valid = point_id == 0 ? rpm == 0 : (rpm >= 0 && rpm <= 4500);

	if (valid)
		fancurve->points[point_id].rpm1_raw = rpm / 100;
	return valid;
}

bool fancurve_set_rpm2(struct fancurve *fancurve, int point_id, int rpm)
{
	bool valid = point_id == 0 ? rpm == 0 : (rpm >= 0 && rpm <= 4500);

	if (valid)
		fancurve->points[point_id].rpm2_raw = rpm / 100;
	return valid;
}

// TODO: remove { ... } from single line if body

bool fancurve_set_accel(struct fancurve *fancurve, int point_id, int accel)
{
	bool valid = accel >= 2 && accel <= 5;

	if (valid)
		fancurve->points[point_id].accel = accel;
	return valid;
}

bool fancurve_set_decel(struct fancurve *fancurve, int point_id, int decel)
{
	bool valid = decel >= 2 && decel <= 5;

	if (valid)
		fancurve->points[point_id].decel = decel;
	return valid;
}

bool fancurve_set_cpu_temp_max(struct fancurve *fancurve, int point_id,
			       int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].cpu_max_temp_celsius = value;

	return valid;
}

bool fancurve_set_gpu_temp_max(struct fancurve *fancurve, int point_id,
			       int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].gpu_max_temp_celsius = value;
	return valid;
}

bool fancurve_set_ic_temp_max(struct fancurve *fancurve, int point_id,
			      int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].ic_max_temp_celsius = value;
	return valid;
}

bool fancurve_set_cpu_temp_min(struct fancurve *fancurve, int point_id,
			       int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].cpu_min_temp_celsius = value;
	return valid;
}

bool fancurve_set_gpu_temp_min(struct fancurve *fancurve, int point_id,
			       int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].gpu_min_temp_celsius = value;
	return valid;
}

bool fancurve_set_ic_temp_min(struct fancurve *fancurve, int point_id,
			      int value)
{
	bool valid = fancurve_is_valid_max_temp(value);

	if (valid)
		fancurve->points[point_id].ic_min_temp_celsius = value;
	return valid;
}

bool fancurve_set_size(struct fancurve *fancurve, int size, bool init_values)
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

/* Read the fan curve from the EC.
 *
 * In newer models (>=2022) there is an ACPI/WMI to read fan curve as
 * a whole. So read/write fan table as a whole to use
 * same interface for both cases.
 *
 * It reads all points from EC memory, even if stored fancurve is smaller, so
 * it can contain 0 entries.
 */
static int read_fancurve(struct ecram *ecram, const struct model_config *model,
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

static int write_fancurve(struct ecram *ecram, const struct model_config *model,
			  const struct fancurve *fancurve, bool write_size)
{
	size_t i;
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

/* =============================  */
/* Global and shared data between */
/* all calls to this module       */
/* ============================   */
// Implemented like ideapad-laptop.c but currenlty still
// wihtout dynamic memory allocation (instaed global _priv)

struct legion_private {
	struct platform_device *platform_device;
	// TODO: remove or keep? init?
	// struct acpi_device *adev;

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

	// TODO: remove?
	bool loaded;
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

static int debugfs_fancurve_show(struct seq_file *s, void *unused)
{
	struct legion_private *priv = s->private;
	bool is_minifancurve;
	bool is_lockfancontroller;
	bool is_maximumfanspeed;
	int err;

	seq_printf(s, "EC Chip ID: %x\n", read_ec_id(&priv->ecram, priv->conf));
	seq_printf(s, "EC Chip Version: %x\n",
		   read_ec_version(&priv->ecram, priv->conf));
	seq_printf(s, "legion_laptop features: %s\n", LEGIONFEATURES);
	seq_printf(s, "legion_laptop ec_readonly: %d\n", ec_readonly);
	read_fancurve(&priv->ecram, priv->conf, &priv->fancurve);

	seq_printf(s, "minifancurve feature enabled: %d\n",
		   priv->conf->has_minifancurve);
	err = read_minifancurve(&priv->ecram, priv->conf, &is_minifancurve);
	seq_printf(s, "minifancurve on cool: %s\n",
		   err ? "error" : (is_minifancurve ? "true" : "false"));
	err = read_lockfancontroller(&priv->ecram, priv->conf,
				     &is_lockfancontroller);
	seq_printf(s, "lock fan controller: %s\n",
		   err ? "error" : (is_lockfancontroller ? "true" : "false"));
	err = read_maximumfanspeed(&priv->ecram, priv->conf,
				   &is_maximumfanspeed);
	seq_printf(s, "enable maximumfanspeed: %s\n",
		   err ? "error" : (is_maximumfanspeed ? "true" : "false"));
	seq_printf(s, "enable maximumfanspeed status: %d\n", err);

	seq_printf(s, "fan curve current point id: %ld\n",
		   priv->fancurve.current_point_i);
	seq_printf(s, "fan curve points size: %ld\n", priv->fancurve.size);

	seq_puts(s, "Current fan curve in hardware (embedded controller):\n");
	fancurve_print_seqfile(&priv->fancurve, s);
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

static ssize_t powermode_show(struct device *dev, struct device_attribute *attr,
			      char *buf)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	int power_mode = read_powermode(&priv->ecram, priv->conf);

	return sysfs_emit(buf, "%d\n", power_mode);
}

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

	err = write_powermode(&priv->ecram, priv->conf, powermode);
	if (err)
		return -EINVAL;

	// TODO: better?
	// we have to wait a bit before change is done in hardware and
	// readback done after notifying returns correct value, otherwise
	// the notified reader will read old value
	msleep(500);
	platform_profile_notify();

	return count;
}

static DEVICE_ATTR_RW(powermode);

static ssize_t lockfancontroller_show(struct device *dev,
				      struct device_attribute *attr, char *buf)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	bool is_lockfancontroller;
	int err;

	mutex_lock(&priv->fancurve_mutex);
	err = read_lockfancontroller(&priv->ecram, priv->conf,
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
	err = write_lockfancontroller(&priv->ecram, priv->conf,
				      is_lockfancontroller);
	mutex_unlock(&priv->fancurve_mutex);
	if (err)
		return -EINVAL;

	return count;
}

static DEVICE_ATTR_RW(lockfancontroller);

static ssize_t keyboard_backlight_show(struct device *dev,
				       struct device_attribute *attr, char *buf)
{
	int state;
	struct legion_private *priv = dev_get_drvdata(dev);

	read_keyboard_backlight(&priv->ecram, priv->conf, &state);
	return sysfs_emit(buf, "%d\n", state);
}

static ssize_t keyboard_backlight_store(struct device *dev,
					struct device_attribute *attr,
					const char *buf, size_t count)
{
	struct legion_private *priv = dev_get_drvdata(dev);
	int state;
	int err;

	err = kstrtouint(buf, 0, &state);
	if (err)
		return err;

	err = write_keyboard_backlight(&priv->ecram, priv->conf, state);
	if (err)
		return -EINVAL;

	return count;
}

static DEVICE_ATTR_RW(keyboard_backlight);

static struct attribute *legion_sysfs_attributes[] = {
	&dev_attr_powermode.attr, &dev_attr_lockfancontroller.attr,
	&dev_attr_keyboard_backlight.attr, NULL
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
		//platform_profile_notify();
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
	platform_profile_notify();
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

// check if really a method
#define LEGION_WMI_GAMEZONE_GUID "887B54E3-DDDC-4B2C-8B88-68A26A8835D0"

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

enum LEGION_POWERMODE {
	LEGION_POWERMODE_BALANCED = 0,
	LEGION_POWERMODE_PERFORMANCE = 1,
	LEGION_POWERMODE_QUIET = 2,
};

static int legion_platform_profile_get(struct platform_profile_handler *pprof,
				       enum platform_profile_option *profile)
{
	int powermode;
	struct legion_private *priv;

	priv = container_of(pprof, struct legion_private,
			    platform_profile_handler);
	powermode = read_powermode(&priv->ecram, priv->conf);

	switch (powermode) {
	case LEGION_POWERMODE_BALANCED:
		*profile = PLATFORM_PROFILE_BALANCED;
		break;
	case LEGION_POWERMODE_PERFORMANCE:
		*profile = PLATFORM_PROFILE_PERFORMANCE;
		break;
	case LEGION_POWERMODE_QUIET:
		*profile = PLATFORM_PROFILE_QUIET;
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
		powermode = LEGION_POWERMODE_BALANCED;
		break;
	case PLATFORM_PROFILE_PERFORMANCE:
		powermode = LEGION_POWERMODE_PERFORMANCE;
		break;
	case PLATFORM_PROFILE_QUIET:
		powermode = LEGION_POWERMODE_QUIET;
		break;
	default:
		return -EOPNOTSUPP;
	}

	return write_powermode(&priv->ecram, priv->conf, powermode);
}

static int legion_platform_profile_init(struct legion_private *priv)
{
	int err;

	priv->platform_profile_handler.profile_get =
		legion_platform_profile_get;
	priv->platform_profile_handler.profile_set =
		legion_platform_profile_set;

	set_bit(PLATFORM_PROFILE_QUIET, priv->platform_profile_handler.choices);
	set_bit(PLATFORM_PROFILE_BALANCED,
		priv->platform_profile_handler.choices);
	set_bit(PLATFORM_PROFILE_PERFORMANCE,
		priv->platform_profile_handler.choices);

	err = platform_profile_register(&priv->platform_profile_handler);
	if (err)
		return err;

	return 0;
}

static void legion_platform_profile_exit(struct legion_private *priv)
{
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

	read_sensor_values(&priv->ecram, priv->conf, &values);

	switch (sensor_id) {
	case SENSOR_CPU_TEMP_ID:
		outval = 1000 * values.cpu_temp_celsius;
		break;
	case SENSOR_GPU_TEMP_ID:
		outval = 1000 * values.gpu_temp_celsius;
		break;
	case SENSOR_IC_TEMP_ID:
		outval = 1000 * values.ic_temp_celsius;
		break;
	case SENSOR_FAN1_RPM_ID:
		outval = values.fan1_rpm;
		break;
	case SENSOR_FAN2_RPM_ID:
		outval = values.fan2_rpm;
		break;
	case SENSOR_FAN1_TARGET_RPM_ID:
		outval = values.fan1_target_rpm;
		break;
	case SENSOR_FAN2_TARGET_RPM_ID:
		outval = values.fan2_target_rpm;
		break;
	default:
		pr_info("Error reading sensor value with id %d\n", sensor_id);
		return -EOPNOTSUPP;
	}

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
	err = read_fancurve(&priv->ecram, priv->conf, &fancurve);
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
	err = read_fancurve(&priv->ecram, priv->conf, &fancurve);

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

	err = write_fancurve(&priv->ecram, priv->conf, &fancurve, false);
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
	err = read_minifancurve(&priv->ecram, priv->conf, &value);
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
	err = write_minifancurve(&priv->ecram, priv->conf, value);
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
	err = read_maximumfanspeed(&priv->ecram, priv->conf, &value);
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
	err = write_maximumfanspeed(&priv->ecram, priv->conf,
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

static umode_t legion_is_visible(struct kobject *kobj, struct attribute *attr,
				 int idx)
{
	bool supported = true;
	struct device *dev = kobj_to_dev(kobj);
	struct legion_private *priv = dev_get_drvdata(dev);

	if (attr == &sensor_dev_attr_minifancurve.dev_attr.attr)
		supported = priv->conf->has_minifancurve;

	return supported ? attr->mode : 0;
}

static const struct attribute_group legion_hwmon_sensor_group = {
	.attrs = sensor_hwmon_attributes,
	.is_visible = NULL
};

static const struct attribute_group legion_hwmon_fancurve_group = {
	.attrs = fancurve_hwmon_attributes,
	.is_visible = legion_is_visible,
};

static const struct attribute_group *legion_hwmon_groups[] = {
	&legion_hwmon_sensor_group, &legion_hwmon_fancurve_group, NULL
};

ssize_t legion_hwmon_init(struct legion_private *priv)
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

void legion_hwmon_exit(struct legion_private *priv)
{
	pr_info("Unloading legion hwon\n");
	if (priv->hwmon_dev) {
		hwmon_device_unregister(priv->hwmon_dev);
		priv->hwmon_dev = NULL;
	}
	pr_info("Unloading legion hwon done\n");
}

/* =============================  */
/* Platform driver                */
/* ============================   */

int legion_add(struct platform_device *pdev)
{
	struct legion_private *priv;
	const struct dmi_system_id *dmi_sys;
	int err;
	u16 ec_read_id;
	bool is_denied = true;
	bool is_allowed = false;
	bool do_load_by_list = false;
	bool do_load = false;
	//struct legion_private *priv = dev_get_drvdata(&pdev->dev);
	dev_info(&pdev->dev, "legion_laptop platform driver probing\n");

	dev_info(&pdev->dev, "Read identifying information: DMI_SYS_VENDOR: %s; DMI_PRODUCT_NAME: %s; DMI_BIOS_VERSION:%s\n",
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

	err = ecram_init(&priv->ecram, priv->conf->memoryio_physical_ec_start,
			 priv->conf->memoryio_size);
	if (err) {
		dev_info(&pdev->dev,
			 "Could not init access to embedded controller\n");
		goto err_ecram_init;
	}

	ec_read_id = read_ec_id(&priv->ecram, priv->conf);
	dev_info(&pdev->dev, "Read embedded controller ID 0x%x\n", ec_read_id);
	if (priv->conf->check_embedded_controller_id &&
	    !(ec_read_id == priv->conf->embedded_controller_id)) {
		err = -ENOMEM;
		dev_info(&pdev->dev, "Expected EC chip id 0x%x but read 0x%x\n",
			 priv->conf->embedded_controller_id, ec_read_id);
		goto err_ecram_id;
	}
	if (!priv->conf->check_embedded_controller_id) {
		dev_info(&pdev->dev,
			 "Skipped checking embedded controller id\n");
	}

	dev_info(&pdev->dev, "Creating debugfs inteface\n");
	legion_debugfs_init(priv);

	pr_info("Creating sysfs inteface\n");
	err = legion_sysfs_init(priv);
	if (err) {
		dev_info(&pdev->dev, "Creating sysfs interface failed\n");
		goto err_sysfs_init;
	}

	pr_info("Creating hwmon interface");
	err = legion_hwmon_init(priv);
	if (err)
		goto err_hwmon_init;

	pr_info("Creating platform profile support\n");
	err = legion_platform_profile_init(priv);
	if (err) {
		dev_info(&pdev->dev, "Creating platform profile failed\n");
		goto err_platform_profile;
	}

	pr_info("Init WMI driver support\n");
	err = legion_wmi_init();
	if (err) {
		dev_info(&pdev->dev, "Init WMI driver failed\n");
		goto err_wmi;
	}

	dev_info(&pdev->dev, "legion_laptop loaded for this device\n");
	return 0;

	// TODO: remove eventually
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
	legion_shared_exit(priv);
err_legion_shared_init:
err_model_mismtach:
	dev_info(&pdev->dev, "legion_laptop not loaded for this device\n");
	return err;
}

int legion_remove(struct platform_device *pdev)
{
	struct legion_private *priv = dev_get_drvdata(&pdev->dev);

	mutex_lock(&legion_shared_mutex);
	priv->loaded = false;
	mutex_unlock(&legion_shared_mutex);

	// first unregister wmi, so toggling powermode does not
	// generate events anymore that even might be delayed
	legion_wmi_exit();
	legion_platform_profile_exit(priv);

	// toggle power mode to load default setting from embedded controller
	// again
	toggle_powermode(&priv->ecram, priv->conf);

	legion_hwmon_exit(priv);
	legion_sysfs_exit(priv);
	legion_debugfs_exit(priv);
	ecram_exit(&priv->ecram);
	legion_shared_exit(priv);

	pr_info("Legion platform unloaded\n");
	return 0;
}

int legion_resume(struct platform_device *pdev)
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
	{ "PNP0C09", 0 }, // todo: change to "VPC2004"
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

int __init legion_init(void)
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

void __exit legion_exit(void)
{
	platform_driver_unregister(&legion_driver);
	pr_info("legion_laptop exit\n");
}

module_exit(legion_exit);
