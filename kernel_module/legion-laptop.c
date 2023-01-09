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
 *      - Luke Cama: Windows version "LegionFanControl"
 *      - SmokelessCPU: reverse engineering of custom registers in EC
 *                      and commincation method with EC via ports
 *      - 0x1F9F1: additional reverse engineering for complete fan curve
 *      - heavily inspired by lenovo_laptop.c
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

MODULE_LICENSE("GPL");
MODULE_AUTHOR("johnfan");
MODULE_DESCRIPTION("Lenovo Legion laptop extras");

static bool force;
module_param(force, bool, 0440);
MODULE_PARM_DESC(
	force,
	"Force loading this module even if model or BIOS does not match.");

//TODO: remove this, kernel modules do not have versions
#define MODULEVERSION "0.1"

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
	u16 ECINDAR0;
	u16 ECINDAR1;
	u16 ECINDAR2;
	u16 ECINDAR3;
	u16 ECINDDR;
	u16 GPDRA;
	u16 GPCRA0;
	u16 GPCRA1;
	u16 GPCRA2;
	u16 GPCRA3;
	u16 GPCRA4;
	u16 GPCRA5;
	u16 GPCRA6;
	u16 GPCRA7;
	u16 GPOTA;
	u16 GPDMRA;
	u16 DCR0;
	u16 DCR1;
	u16 DCR2;
	u16 DCR3;
	u16 DCR4;
	u16 DCR5;
	u16 DCR6;
	u16 DCR7;
	u16 CTR2;
	u16 ECHIPID1;
	u16 ECHIPID2;
	u16 ECHIPVER;
	u16 ECDEBUG;
	u16 EADDR;
	u16 EDAT;
	u16 ECNT;
	u16 ESTS;
	u16 FW_VER;
	u16 FAN_CUR_POINT;
	u16 FAN_POINTS_SIZE;
	u16 FAN1_BASE;
	u16 FAN2_BASE;
	u16 FAN_ACC_BASE;
	u16 FAN_DEC_BASE;
	u16 CPU_TEMP;
	u16 CPU_TEMP_HYST;
	u16 GPU_TEMP;
	u16 GPU_TEMP_HYST;
	u16 VRM_TEMP;
	u16 VRM_TEMP_HYST;
	u16 CPU_TEMP_EN;
	u16 GPU_TEMP_EN;
	u16 VRM_TEMP_EN;
	u16 FAN1_ACC_TIMER;
	u16 FAN2_ACC_TIMER;
	u16 FAN1_CUR_ACC;
	u16 FAN1_CUR_DEC;
	u16 FAN2_CUR_ACC;
	u16 FAN2_CUR_DEC;
	u16 FAN1_RPM_LSB;
	u16 FAN1_RPM_MSB;
	u16 FAN2_RPM_LSB;
	u16 FAN2_RPM_MSB;

	u16 F1TLRR;
	u16 F1TMRR;
	u16 F2TLRR;
	u16 F2TMRR;
	u16 CTR1;
	u16 CTR3;
	u16 FAN1CNF;
	u16 FAN2CNF;

	// altnerive regsisters
	// TODO: decide on one version
	u16 ALT_FAN_RPM;
	u16 ALT_CPU_TEMP;
	u16 ALT_GPU_TEMP;
	u16 ALT_POWERMODE;

	u16 ALT_FAN1_RPM;
	u16 ALT_FAN2_RPM;
	u16 ALT_CPU_TEMP2;
	u16 ALT_GPU_TEMP2;
	u16 ALT_IC_TEMP2;
};

enum ECRAM_ACCESS { ECRAM_ACCESS_PORTIO, ECRAM_ACCESS_MEMORYIO };

enum CONTROL_METHOD {
	// control EC by readin/writing to EC memory
	CONTROL_METHOD_ECRAM,
	// control EC only by ACPI calls
	CONTROL_METHOD_ACPI
};

struct model_config {
	const struct ec_register_offsets *registers;
	u16 embedded_controller_id;
	// how should the EC be acesses?
	enum CONTROL_METHOD access_method;

	// if EC is accessed by RAM, how sould it be access
	enum ECRAM_ACCESS ecram_access_method;

	// if EC is accessed by memory mapped, what is its address
	phys_addr_t memoryio_physical_start;
	size_t memoryio_size;
};

/* =================================== */
/* Coinfiguration for different models */
/* =================================== */

// Idea by SmokelesssCPU (modified)
// - all default names and register addresses are supported by datasheet
// - register addresses for custom firmware by SmokelesssCPU
static const struct ec_register_offsets ec_register_offsets_v0 = {
	// 6.3 Shared Memory Flash Interface Bridge (SMFI)
	// "The SMFI provides an HLPC interface between the host bus a
	// and the M bus. The flash is mapped into the
	// host memory address space for host accesses. The flash is also
	// mapped into the EC memory address space for EC accesses"
	.ECINDAR0 = 0x103B,
	.ECINDAR1 = 0x103C,
	.ECINDAR2 = 0x103D,
	.ECINDAR3 = 0x103E,
	.ECINDDR = 0x103F,

	// 7.5 General Purpose I/O Port (GPIO)
	// I/O pins controlled by registers.
	.GPDRA = 0x1601,
	// port data, i.e. data to output to pins
	// or data read from pins
	.GPCRA0 = 0x1610,
	// control register for each pin,
	// set as input, output, ...
	.GPCRA1 = 0x1611,
	.GPCRA2 = 0x1612,
	.GPCRA3 = 0x1613,
	.GPCRA4 = 0x1614,
	.GPCRA5 = 0x1615,
	.GPCRA6 = 0x1616,
	.GPCRA7 = 0x1617,
	.GPOTA = 0x1671,
	.GPDMRA = 0x1661,

	// Super I/O Configuration Registers
	// 7.15 General Control (GCTRL)
	// General Control (GCTRL)
	// (see EC Interface Registers  and 6.2 Plug and Play Configuration (PNPCFG)) in datasheet
	// note: these are in two places saved
	// in EC Interface Registers  and in super io configuraion registers
	// Chip ID
	.ECHIPID1 = 0x2000, // 0x20
	.ECHIPID2 = 0x2001, // 0x21
	// Chip Version
	.ECHIPVER = 0x2002, // 0x22
	.ECDEBUG = 0x2003, //0x23 SIOCTRL (super io control)

	// External GPIO Controller (EGPC)
	// 7.16 External GPIO Controller (EGPC)
	// Communication with an external GPIO chip
	// (IT8301)
	// Address
	.EADDR = 0x2100,
	// Data
	.EDAT = 0x2101,
	// Control
	.ECNT = 0x2102,
	// Status
	.ESTS = 0x2103,

	// FAN/PWM control by ITE
	// 7.11 PWM
	// - lower powered ITEs just come with PWM
	//   control
	// - higher powered ITEs, e.g. ITE8511, come
	//   from ITE with a fan control software
	//   in ROM with 3 (or 4) fan curve points
	//   called SmartAuto Fan Control
	// - in Lenovo Legion Laptop the SmartAuto
	//   is not used, but the fan is controlled
	//   by a custom program flashed on the ITE
	//   chip

	// duty cycle of each PWM output
	.DCR0 = 0x1802,
	.DCR1 = 0x1803,
	.DCR2 = 0x1804,
	.DCR3 = 0x1805,
	.DCR4 = 0x1806,
	.DCR5 = 0x1807,
	.DCR6 = 0x1808,
	.DCR7 = 0x1809,
	// FAN1 tachometer (least, most signficant byte)
	.F1TLRR = 0x181E,
	.F1TMRR = 0x181F,
	// FAN1 tachometer (least, most signficant byte)
	.F2TLRR = 0x1820,
	.F2TLRR = 0x1821,
	// cycle time, i.e. clock prescaler for PWM signal
	.CTR1 = 0x1842,
	.CTR2 = 0x1842,
	.CTR3 = 0x1842,

	// bits 7-6 (higest bit)
	//  00: SmartAuto mode 0 (temperature controlled)
	//  01: SmartAuto mode 1 (temperaute replaced by a register value)
	//  10: manual mode
	// bits: 4-2
	//  PWM output channel used for ouput (0-7 by 3 bits)
	.FAN1CNF = 0x1810,
	// spin up time (duty cycle = 100% for this time when fan stopped)
	//  00: 0
	//  01: 250ms
	//  10: 500ms
	//  11: 1000ms
	.FAN2CNF = 0x1811,

	// Lenovo Custom OEM extension
	// Firmware of ITE can be extended by
	// custom program using its own "variables"
	// These are the offsets to these "variables"
	.FW_VER = 0xC2C7,
	.FAN_CUR_POINT = 0xC534,
	.FAN_POINTS_SIZE = 0xC535,
	.FAN1_BASE = 0xC540,
	.FAN2_BASE = 0xC550,
	.FAN_ACC_BASE = 0xC560,
	.FAN_DEC_BASE = 0xC570,
	.CPU_TEMP = 0xC580,
	.CPU_TEMP_HYST = 0xC590,
	.GPU_TEMP = 0xC5A0,
	.GPU_TEMP_HYST = 0xC5B0,
	.VRM_TEMP = 0xC5C0,
	.VRM_TEMP_HYST = 0xC5D0,
	.CPU_TEMP_EN = 0xC631,
	.GPU_TEMP_EN = 0xC632,
	.VRM_TEMP_EN = 0xC633,
	.FAN1_ACC_TIMER = 0xC3DA,
	.FAN2_ACC_TIMER = 0xC3DB,
	.FAN1_CUR_ACC = 0xC3DC,
	.FAN1_CUR_DEC = 0xC3DD,
	.FAN2_CUR_ACC = 0xC3DE,
	.FAN2_CUR_DEC = 0xC3DF,
	.FAN1_RPM_LSB = 0xC5E0,
	.FAN1_RPM_MSB = 0xC5E1,
	.FAN2_RPM_LSB = 0xC5E2,
	.FAN2_RPM_MSB = 0xC5E3,

	.ALT_CPU_TEMP = 0xc538,
	.ALT_GPU_TEMP = 0xc539,
	.ALT_POWERMODE = 0xc420,

	.ALT_FAN_RPM = 0xc600,
	.ALT_FAN1_RPM = 0xC406,
	.ALT_FAN2_RPM = 0xC4FE,

	.ALT_CPU_TEMP2 = 0xC5E6,
	.ALT_GPU_TEMP2 = 0xC5E7,
	.ALT_IC_TEMP2 = 0xC5E8
};

static const struct model_config model_v0 = {
	.registers = &ec_register_offsets_v0,
	.embedded_controller_id = 0x8227,
	.access_method = CONTROL_METHOD_ECRAM,
	.ecram_access_method = ECRAM_ACCESS_PORTIO,
	.memoryio_physical_start = 0xFE00D400,
	.memoryio_size = 0x300
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
	{}
};

static const struct dmi_system_id explicit_allowlist[] = {
	{
		.ident = "GKCN58WW",
		.matches = {
			DMI_MATCH(DMI_SYS_VENDOR, "LENOVO"),
			DMI_MATCH(DMI_BIOS_VERSION, "GKCN58WW"),
		},
		.driver_data = (void *)&model_v0
	},
	{}
};

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
/* EC RAM Access with memory mapped IO */
/* =================================== */

#define ECRAM_OFFSET 0xC400

struct ecram_memoryio {
	// TODO: start of remapped memory in EC RAM is assumed to be 0
	// u16 ecram_start;

	// physical address of remapped IO, depends on model and firmware
	phys_addr_t physical_start;
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
ssize_t ecram_memoryio_init(struct ecram_memoryio *ec_memoryio,
			    phys_addr_t physical_start, size_t size)
{
	void *virtual_start = ioremap(physical_start, size);

	if (!IS_ERR_OR_NULL(virtual_start)) {
		ec_memoryio->virtual_start = virtual_start;
		ec_memoryio->physical_start = physical_start;
		ec_memoryio->size = size;
		pr_info("Succeffuly mapped embedded controller: 0x%llx to virtual 0x%p\n",
			ec_memoryio->physical_start,
			ec_memoryio->virtual_start);
	} else {
		pr_info("Error mapping embedded controller memory at 0x%llx\n",
			physical_start);
		return -ENOMEM;
	}
	return 0;
}

void ecram_memoryio_exit(struct ecram_memoryio *ec_memoryio)
{
	if (ec_memoryio->virtual_start != NULL) {
		pr_info("Unmapping embedded controller memory at 0x%llx at virtual 0x%p\n",
			ec_memoryio->physical_start,
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
ssize_t ecram_memoryio_read(const struct ecram_memoryio *ec_memoryio,
			    u16 ec_offset, u8 *value)
{
	if (ec_offset < ECRAM_OFFSET) {
		pr_info("Unexpected read at offset %d into EC RAM\n",
			ec_offset);
		return -1;
	}
	*value = *(ec_memoryio->virtual_start + (ec_offset - ECRAM_OFFSET));
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
	if (ec_offset < ECRAM_OFFSET) {
		pr_info("Unexpected write at offset %d into EC RAM\n",
			ec_offset);
		return -1;
	}
	*(ec_memoryio->virtual_start + (ec_offset - ECRAM_OFFSET)) = value;
	return 0;
}

/* =================================== */
/* EC RAM Access                       */
/* =================================== */

struct ecram {
	struct ecram_memoryio memoryio;
	struct ecram_portio portio;
	enum ECRAM_ACCESS access_method;
};

ssize_t ecram_init(struct ecram *ecram, enum ECRAM_ACCESS access_method,
		   phys_addr_t memoryio_physical_start, size_t region_size)
{
	ssize_t err;

	err = ecram_memoryio_init(&ecram->memoryio, memoryio_physical_start,
				  region_size);
	if (err) {
		pr_info("Failed ecram_memoryio_init\n");
		goto err_ecram_memoryio_init;
	}
	err = ecram_portio_init(&ecram->portio);
	if (err) {
		pr_info("Failed ecram_portio_init\n");
		goto err_ecram_portio_init;
	}

	ecram->access_method = access_method;

	return 0;

err_ecram_portio_init:
	ecram_memoryio_exit(&ecram->memoryio);
err_ecram_memoryio_init:

	return err;
}

void ecram_exit(struct ecram *ecram)
{
	ecram_portio_exit(&ecram->portio);
	ecram_memoryio_exit(&ecram->memoryio);
}

/**
 * ecram_offset address on the EC
 */
static u8 ecram_read(struct ecram *ecram, u16 ecram_offset)
{
	u8 value;
	int err;

	switch (ecram->access_method) {
	case ECRAM_ACCESS_MEMORYIO:
		err = ecram_memoryio_read(&ecram->memoryio, ecram_offset,
					  &value);
		break;
	case ECRAM_ACCESS_PORTIO:
		err = ecram_portio_read(&ecram->portio, ecram_offset, &value);
		break;
	default:
		break;
	}
	if (err)
		pr_info("Error reading EC RAM at 0x%x\n", ecram_offset);
	return value;
}

static void ecram_write(struct ecram *ecram, u16 ecram_offset, u8 value)
{
	int err;

	switch (ecram->access_method) {
	case ECRAM_ACCESS_MEMORYIO:
		err = ecram_memoryio_write(&ecram->memoryio, ecram_offset,
					   value);
		break;
	case ECRAM_ACCESS_PORTIO:
		err = ecram_portio_write(&ecram->portio, ecram_offset, value);
		break;
	default:
		break;
	}
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
	u16 fan1_rpm; // rpm1
	u16 fan2_rpm; // rpm2
	// TODO: remove this later, lets just see what is more accurate
	u16 fan_rpm; // rpm1
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
	// TODO: remove this later, lets just see what is more accurate
	SENSOR_FAN_RPM_ID = 6
};

static int read_sensor_values(struct ecram *ecram,
			      const struct model_config *model,
			      struct sensor_values *values)
{
	values->fan_rpm =
		100 * ecram_read(ecram, model->registers->ALT_FAN_RPM);
	// TODO: what source toc choose?
	// values->fan1_rpm = 100*ecram_read(ecram, model->registers->ALT_FAN1_RPM);
	// values->fan2_rpm = 100*ecram_read(ecram, model->registers->ALT_FAN2_RPM);

	values->fan1_rpm =
		ecram_read(ecram, model->registers->FAN1_RPM_LSB) +
		(((int)ecram_read(ecram, model->registers->FAN1_RPM_MSB)) << 8);
	values->fan2_rpm =
		ecram_read(ecram, model->registers->FAN2_RPM_LSB) +
		(((int)ecram_read(ecram, model->registers->FAN2_RPM_MSB)) << 8);

	values->cpu_temp_celsius =
		ecram_read(ecram, model->registers->ALT_CPU_TEMP);
	values->gpu_temp_celsius =
		ecram_read(ecram, model->registers->ALT_GPU_TEMP);
	values->ic_temp_celsius =
		ecram_read(ecram, model->registers->ALT_IC_TEMP2);

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
	return ecram_read(ecram, model->registers->ALT_POWERMODE);
}

ssize_t write_powermode(struct ecram *ecram, const struct model_config *model,
			u8 value)
{
	if (!(value >= 0 && value <= 2)) {
		pr_info("Unexpected power mode value ignored: %d\n", value);
		return -ENOMEM;
	}
	ecram_write(ecram, model->registers->ALT_POWERMODE, value);
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

//TODO: remove this if meaning of hyst in fan curve is clear!
//
//bool fancurve_set_cpu_deltahyst(struct fancurve* fancurve, int point_id, int hyst_value)
//{
//	int max_temp = fancurve->points[point_id].cpu_max_temp_celsius;
//	bool valid = hyst_value < max_temp;
//	if(valid){
//		fancurve->points[point_id].cpu_min_temp_celsius = max_temp - hyst_value;
//	}
//	return valid;
//}

//bool fancurve_set_gpu_deltahyst(struct fancurve* fancurve, int point_id, int hyst_value)
//{
//	int max_temp = fancurve->points[point_id].gpu_max_temp_celsius;
//	bool valid = hyst_value < max_temp;
//	if(valid){
//		fancurve->points[point_id].gpu_min_temp_celsius = max_temp - hyst_value;
//	}
//	return valid;
//}

//bool fancurve_set_ic_deltahyst(struct fancurve* fancurve, int point_id, int hyst_value)
//{
//	int max_temp = fancurve->points[point_id].ic_max_temp_celsius;
//	bool valid = hyst_value < max_temp;
//	if(valid){
//		fancurve->points[point_id].ic_min_temp_celsius = max_temp - hyst_value;
//	}
//	return valid;
//}

bool fancurve_set_size(struct fancurve *fancurve, int size, bool init_values)
{
	bool valid = size >= 1 && size <= MAXFANCURVESIZE;

	if (!valid)
		return false;
	if (init_values && size < fancurve->size) {
		// fancurve size is decreased, but last etnry alwasy needs 127 temperatures
		// Note: size >=1
		// TODO: remove this comment
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
			ecram_read(ecram, model->registers->FAN1_BASE + i);
		point->rpm2_raw =
			ecram_read(ecram, model->registers->FAN2_BASE + i);

		point->accel =
			ecram_read(ecram, model->registers->FAN_ACC_BASE + i);
		point->decel =
			ecram_read(ecram, model->registers->FAN_DEC_BASE + i);
		point->cpu_max_temp_celsius =
			ecram_read(ecram, model->registers->CPU_TEMP + i);
		point->cpu_min_temp_celsius =
			ecram_read(ecram, model->registers->CPU_TEMP_HYST + i);
		point->gpu_max_temp_celsius =
			ecram_read(ecram, model->registers->GPU_TEMP + i);
		point->gpu_min_temp_celsius =
			ecram_read(ecram, model->registers->GPU_TEMP_HYST + i);
		point->ic_max_temp_celsius =
			ecram_read(ecram, model->registers->VRM_TEMP + i);
		point->ic_min_temp_celsius =
			ecram_read(ecram, model->registers->VRM_TEMP_HYST + i);
	}

	// Do not trust that hardware; It might suddendly report
	// a larger size, so clamp it.
	fancurve->size = ecram_read(ecram, model->registers->FAN_POINTS_SIZE);
	fancurve->size =
		min(fancurve->size, (typeof(fancurve->size))(MAXFANCURVESIZE));
	fancurve->current_point_i =
		ecram_read(ecram, model->registers->FAN_CUR_POINT);
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

		ecram_write(ecram, model->registers->FAN1_BASE + i,
			    point->rpm1_raw);
		ecram_write(ecram, model->registers->FAN2_BASE + i,
			    point->rpm2_raw);

		ecram_write(ecram, model->registers->FAN_ACC_BASE + i,
			    point->accel);
		ecram_write(ecram, model->registers->FAN_DEC_BASE + i,
			    point->decel);

		ecram_write(ecram, model->registers->CPU_TEMP + i,
			    point->cpu_max_temp_celsius);
		ecram_write(ecram, model->registers->CPU_TEMP_HYST + i,
			    point->cpu_min_temp_celsius);
		ecram_write(ecram, model->registers->GPU_TEMP + i,
			    point->gpu_max_temp_celsius);
		ecram_write(ecram, model->registers->GPU_TEMP_HYST + i,
			    point->gpu_min_temp_celsius);
		ecram_write(ecram, model->registers->VRM_TEMP + i,
			    point->ic_max_temp_celsius);
		ecram_write(ecram, model->registers->VRM_TEMP_HYST + i,
			    point->ic_min_temp_celsius);
	}

	if (write_size) {
		ecram_write(ecram, model->registers->FAN_POINTS_SIZE,
			    fancurve->size);
	}

	// Reset current fan level to 0, so algorithm in EC
	// selects fan curve point again and resetting hysterisis
	// effects
	ecram_write(ecram, model->registers->FAN_CUR_POINT, 0);

	// Reset internal fan levels
	ecram_write(ecram, 0xC634, 0); // CPU
	ecram_write(ecram, 0xC635, 0); // GPU
	ecram_write(ecram, 0xC636, 0); // SENSOR

	return 0;
}

//TODO: still needed?
//static ssize_t fancurve_print(const struct fancurve* fancurve, char *buf)
//{
//	ssize_t output_char_count = 0;
//	size_t i;
//	for (i = 0; i < fancurve->size; ++i) {
//		const struct fancurve_point * point = &fancurve->points[i];
//		int res = sprintf(buf, "%d %d %d %d %d %d %d %d %d %d\n",
//				  point->rpm1_raw*100, point->rpm2_raw*100,
//				  point->accel, point->decel,
//				  point->cpu_min_temp_celsius,
//				  point->cpu_max_temp_celsius,
//				  point->gpu_min_temp_celsius,
//				  point->gpu_max_temp_celsius,
//				  point->ic_min_temp_celsius,
//				  point->ic_max_temp_celsius);
//		if (res > 0) {
//			output_char_count += res;
//		} else {
//			pr_debug(
//				"Error writing to buffer for output of fanCurveStructure\n");
//			return 0;
//		}
//		// go forward in buffer to append next print output
//		buf += res;
//	}
//	return output_char_count;
//}

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

	mutex_unlock(&legion_shared_mutex);

	return ret;
}

static void legion_shared_exit(struct legion_private *priv)
{
	mutex_lock(&legion_shared_mutex);

	if (legion_shared == priv)
		legion_shared = NULL;

	mutex_unlock(&legion_shared_mutex);
}

/* =============================  */
/* debugfs interface              */
/* ============================   */

static int debugfs_ecmemory_show(struct seq_file *s, void *unused)
{
	struct legion_private *priv = s->private;
	size_t offset;

	for (offset = 0; offset < priv->conf->memoryio_size; ++offset) {
		char value = ecram_read(&priv->ecram, offset);

		seq_write(s, &value, 1);
	}
	return 0;
}

DEFINE_SHOW_ATTRIBUTE(debugfs_ecmemory);

static int debugfs_fancurve_show(struct seq_file *s, void *unused)
{
	struct legion_private *priv = s->private;

	seq_printf(s, "EC Chip ID: %x\n", read_ec_id(&priv->ecram, priv->conf));
	seq_printf(s, "EC Chip Version: %x\n",
		   read_ec_version(&priv->ecram, priv->conf));

	read_fancurve(&priv->ecram, priv->conf, &priv->fancurve);

	seq_printf(s, "fan curve current point id: %ld\n",
		   priv->fancurve.current_point_i);
	seq_printf(s, "fan curve points size: %ld\n", priv->fancurve.size);

	seq_puts(s, "Current fan curve in UEFI\n");
	fancurve_print_seqfile(&priv->fancurve, s);
	seq_puts(s, "=====================\n");

	// TODO: decide what to do with it, still needed?
	// seq_puts(s, "Configured fan curve.\n");
	// fancurve_print_seqfile(&priv->fancurve_configured, s);
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
	// TODO: remove this note
	// Note: does nothing if null
	debugfs_remove_recursive(priv->debugfs_dir);
	priv->debugfs_dir = NULL;
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

	platform_profile_notify();

	return count;
}

static DEVICE_ATTR_RW(powermode);

static struct attribute *legion_sysfs_attributes[] = { &dev_attr_powermode.attr,
						       NULL };

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
	device_remove_group(&priv->platform_device->dev,
			    &legion_attribute_group);
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
	platform_profile_remove();
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
	case SENSOR_FAN_RPM_ID:
		label = "Fan\n";
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
	case SENSOR_FAN_RPM_ID:
		outval = values.fan_rpm;
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
static SENSOR_DEVICE_ATTR_RO(fan3_input, sensor, SENSOR_FAN_RPM_ID);
static SENSOR_DEVICE_ATTR_RO(fan3_label, sensor_label, SENSOR_FAN_RPM_ID);

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
	&sensor_dev_attr_fan3_input.dev_attr.attr,
	&sensor_dev_attr_fan3_label.dev_attr.attr,
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
		// TODO: remove
		//valid = valid && fancurve_set_rpm2(&fancurve, point_id, value);
		break;
	case FANCURVE_ATTR_PWM2:
		valid = fancurve_set_rpm2(&fancurve, point_id, value);
		// TODO: remove
		//valid = valid && fancurve_set_rpm2(&fancurve, point_id, value);
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
	&sensor_dev_attr_auto_points_size.dev_attr.attr,
	NULL
};

static const struct attribute_group legion_hwmon_sensor_group = {
	.attrs = sensor_hwmon_attributes,
	.is_visible = NULL // use modes from attributes
};

static const struct attribute_group legion_hwmon_fancurve_group = {
	.attrs = fancurve_hwmon_attributes,
	.is_visible = NULL // use modes from attributes
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
		&priv->platform_device->dev, "legion_hwmon", NULL,
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
	if (priv->hwmon_dev) {
		hwmon_device_unregister(priv->hwmon_dev);
		priv->hwmon_dev = NULL;
	}
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
	dev_info(&pdev->dev, "legion_laptop platform driver %s probing\n",
		 MODULEVERSION);

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

	is_denied = dmi_check_system(denylist);
	//is_allowed = dmi_check_system(explicit_allowlist);
	is_allowed = dmi_check_system(optimistic_allowlist);

	dev_info(&pdev->dev, "is_denied: %d; is_allowed: %d\n", is_denied,
		 is_allowed);

	do_load_by_list = is_allowed && !is_denied;
	do_load = do_load_by_list || force;

	if (force)
		dev_info(&pdev->dev, "legion_laptop is forced to load.\n");
	if (!do_load_by_list && do_load) {
		dev_info(
			&pdev->dev,
			"legion_laptop is forced to load and would otherwise be not loaded\n");
	}

	if (!(do_load)) {
		dev_info(
			&pdev->dev,
			"Module not useable for this laptop because it is not in allowlist. Notify maintainer if you want to add your device or force load with param force.\n");
		err = -ENOMEM;
		goto err_model_mismtach;
	}

	dmi_sys = dmi_first_match(optimistic_allowlist);
	if (!dmi_sys) {
		dev_info(&pdev->dev, "No matching configuration found\n");
		err = -ENOMEM;
		goto err_model_mismtach;
	}
	priv->conf = dmi_sys->driver_data;
	priv->conf = &model_v0;

	err = ecram_init(&priv->ecram, priv->conf->ecram_access_method,
			 priv->conf->memoryio_physical_start,
			 priv->conf->memoryio_size);
	if (err) {
		dev_info(&pdev->dev,
			 "Could not init access to embedded controller\n");
		goto err_ecram_init;
	}

	ec_read_id = read_ec_id(&priv->ecram, priv->conf);
	if (!(ec_read_id == priv->conf->embedded_controller_id)) {
		err = -ENOMEM;
		dev_info(&pdev->dev, "Expected EC chip id 0x%x but read 0x%x\n",
			 priv->conf->embedded_controller_id, ec_read_id);
		goto err_ecram_id;
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
	if (err)
		goto err_platform_profile;

	dev_info(&pdev->dev, "legion_laptop loaded for this device\n");
	return 0;

// TODO: remove eventually
// legion_platform_profile_exit();
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
	// TODO: remove this
	pr_info("Unloading legion platform\n");

	// toggle power mode to load default setting from embedded controller
	// again
	toggle_powermode(&priv->ecram, priv->conf);

	legion_platform_profile_exit(priv);
	legion_hwmon_exit(priv);
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
	// TODO: remove version
	pr_info("legion_laptop %s starts loading\n", MODULEVERSION);

	// TODO: remove this, make a comment
	if (!(MAXFANCURVESIZE <= 10)) {
		pr_debug("Fan curve size too large\n");
		err = -ENOMEM;
		goto error_assert;
	}

	// TODO: remove this
	pr_info("Read identifying information: DMI_SYS_VENDOR: %s; DMI_PRODUCT_NAME: %s; DMI_BIOS_VERSION:%s\n",
		dmi_get_system_info(DMI_SYS_VENDOR),
		dmi_get_system_info(DMI_PRODUCT_NAME),
		dmi_get_system_info(DMI_BIOS_VERSION));

	err = platform_driver_register(&legion_driver);
	if (err) {
		pr_info("legion_laptop: platform_driver_register failed\n");
		goto error_platform_driver;
	}

	// TODO: remove version
	// pr_info("legion_laptop %s loading done\n", MODULEVERSION);

	return 0;

error_platform_driver:
error_assert:
	return err;
}

module_init(legion_init);

void __exit legion_exit(void)
{
	// TODO: remove this
	pr_info("legion_laptop %s starts unloading\n", MODULEVERSION);
	platform_driver_unregister(&legion_driver);
	// TODO: remove this
	pr_info("legion_laptop %s unloaded\n", MODULEVERSION);
}

module_exit(legion_exit);
