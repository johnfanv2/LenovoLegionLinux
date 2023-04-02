// Full Address list
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
	u16 FAN1_TARGET_RPM;
	u16 FAN2_TARGET_RPM;
	u16 ALT_CPU_TEMP;
	u16 ALT_GPU_TEMP;
	u16 ALT_POWERMODE;

	u16 ALT_FAN1_RPM;
	u16 ALT_FAN2_RPM;
	u16 ALT_CPU_TEMP2;
	u16 ALT_GPU_TEMP2;
	u16 ALT_IC_TEMP2;

	u16 MINIFANCURVE_ON_COOL;
	u16 LOCKFANCONTROLLER;
	u16 MAXIMUMFANSPEED;

	u16 WHITE_KEYBOARD_BACKLIGHT;
};


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

	// values
	// 0x04: enable mini fan curve if very long on cool level
	//      - this might be due to potential temp failure
	//      - or just because really so cool
	// 0xA0: disable it
	.MINIFANCURVE_ON_COOL = 0xC536,

	.LOCKFANCONTROLLER = 0xc4AB,

	.ALT_CPU_TEMP = 0xc538,
	.ALT_GPU_TEMP = 0xc539,
	.ALT_POWERMODE = 0xc420,

	.FAN1_TARGET_RPM = 0xc600,
	.FAN2_TARGET_RPM = 0xc601,
	.ALT_FAN1_RPM = 0xC406,
	.ALT_FAN2_RPM = 0xC4FE,

	.ALT_CPU_TEMP2 = 0xC5E6,
	.ALT_GPU_TEMP2 = 0xC5E7,
	.ALT_IC_TEMP2 = 0xC5E8,

	//enabled: 0x40
	//disabled: 0x00
	.MAXIMUMFANSPEED = 0xBD,

	.WHITE_KEYBOARD_BACKLIGHT = (0x3B + 0xC400)
};




//ssize_t ecram_portio_read_low(struct ecram_portio *ec_portio, u8 offset, u8 *value){
//	mutex_lock(&ec_portio->io_port_mutex);
//	outb(0x66, 0x80);
//	outb(offset, ECRAM_PORTIO_DATA_PORT);
//	*value = inb(ECRAM_PORTIO_DATA_PORT);
//	mutex_unlock(&ec_portio->io_port_mutex);
//}
//ssize_t ecram_portio_write_low(struct ecram_portio *ec_portio, u8 offset, u8 value){
//	mutex_lock(&ec_portio->io_port_mutex);
//	outb(0x66, ECRAM_PORTIO_ADDR_PORT);
//	outb(offset, ECRAM_PORTIO_DATA_PORT);
//	outb(value, ECRAM_PORTIO_DATA_PORT);
//	mutex_unlock(&ec_portio->io_port_mutex);
//}

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
ssize_t ecram_memoryio_init(struct ecram_memoryio *ec_memoryio,
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

void ecram_memoryio_exit(struct ecram_memoryio *ec_memoryio)
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
ssize_t ecram_memoryio_read(const struct ecram_memoryio *ec_memoryio,
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


/* =================================== */
/* EC RAM Access with ACPI             */
/* =================================== */
// experimental and currently not used!

/*
 * ACPI Helpers from ideapad-laptop.c in Linux Kernel
 */
#define IDEAPAD_EC_TIMEOUT 200 /* in ms */

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

static int eval_int_with_arg(acpi_handle handle, const char *name,
			     unsigned long arg, unsigned long *res)
{
	struct acpi_object_list params;
	unsigned long long result;
	union acpi_object in_obj;
	acpi_status status;

	params.count = 1;
	params.pointer = &in_obj;
	in_obj.type = ACPI_TYPE_INTEGER;
	in_obj.integer.value = arg;

	status = acpi_evaluate_integer(handle, (char *)name, &params, &result);
	if (ACPI_FAILURE(status))
		return -EIO;

	if (res)
		*res = result;

	return 0;
}

static int eval_vpcr(acpi_handle handle, unsigned long cmd, unsigned long *res)
{
	return eval_int_with_arg(handle, "VPCR", cmd, res);
}

static int eval_vpcw(acpi_handle handle, unsigned long cmd, unsigned long data)
{
	struct acpi_object_list params;
	union acpi_object in_obj[2];
	acpi_status status;

	params.count = 2;
	params.pointer = in_obj;
	in_obj[0].type = ACPI_TYPE_INTEGER;
	in_obj[0].integer.value = cmd;
	in_obj[1].type = ACPI_TYPE_INTEGER;
	in_obj[1].integer.value = data;

	status = acpi_evaluate_object(handle, "VPCW", &params, NULL);
	if (ACPI_FAILURE(status))
		return -EIO;

	return 0;
}

static int read_ec_data(acpi_handle handle, unsigned long cmd,
			unsigned long *data)
{
	unsigned long end_jiffies, val;
	int err;

	err = eval_vpcw(handle, 1, cmd);
	if (err)
		return err;

	end_jiffies = jiffies + msecs_to_jiffies(IDEAPAD_EC_TIMEOUT) + 1;

	while (time_before(jiffies, end_jiffies)) {
		schedule();

		err = eval_vpcr(handle, 1, &val);
		if (err)
			return err;

		if (val == 0)
			return eval_vpcr(handle, 0, data);
	}

	acpi_handle_err(handle, "timeout in %s\n", __func__);

	return -ETIMEDOUT;
}

static int write_ec_cmd(acpi_handle handle, unsigned long cmd,
			unsigned long data)
{
	unsigned long end_jiffies, val;
	int err;

	err = eval_vpcw(handle, 0, data);
	if (err)
		return err;

	err = eval_vpcw(handle, 1, cmd);
	if (err)
		return err;

	end_jiffies = jiffies + msecs_to_jiffies(IDEAPAD_EC_TIMEOUT) + 1;

	while (time_before(jiffies, end_jiffies)) {
		schedule();

		err = eval_vpcr(handle, 1, &val);
		if (err)
			return err;

		if (val == 0)
			return 0;
	}

	acpi_handle_err(handle, "timeout in %s\n", __func__);

	return -ETIMEDOUT;
}



/* ================================================ */
/* Trying to find memory region experiements        */
/* ================================================ */
// experimental and currently not used!



void acpi_erax_dh(acpi_handle object, void *data){
	pr_info("sdfsdf\n");
}

acpi_status acpi_walk_ec_cb(struct acpi_resource * resource, void *context){
	pr_info("xxddd\n");
	return AE_OK;
};


acpi_status acpi_walk_callback_erax (acpi_handle object,
				   u32 nesting_level,
				   void *context, void **return_value){
	struct acpi_device_info *info;
	acpi_object_type acpi_type;
	acpi_status status;

	status = acpi_get_type(object, &acpi_type);
	if (ACPI_FAILURE(status)) {
		pr_info("type not found.\n");
	} else {
		pr_info("type found: %d\n", acpi_type);
	}

	status = acpi_get_object_info(object, &info);
	if (ACPI_FAILURE(status)) {
		pr_info("info not found.\n");
	} else {
		pr_info("info found\n");
	}
	pr_info("xxddd\n");
	return AE_OK;
}

/**
 * Get the memory mapped start adress of the memory of the embedded controller .
*/
static int legion_acpi_get_ec_start(struct acpi_device *adev, phys_addr_t * mm_start_addr){
	struct acpi_buffer buffer = { ACPI_ALLOCATE_BUFFER, NULL };
	struct acpi_resource *resource;
	//struct acpi_resource_address64 address;

	acpi_status status;
	int err;
	unsigned long long erax_addr;
	struct acpi_device_info *info;
	// ERAX is a OperationRegion in SystemMemory. It is the start
	// of the memory mapped region to access the RAM of the embedded
	// controller

	acpi_handle erax_handle;
	status = acpi_get_handle(NULL, "\\_SB_.PCI0.LPC0.EC0_.ERAX", &erax_handle);
	if (ACPI_FAILURE(status)) {
		pr_info("ERAX in ACPI not found.\n");
	} else {
		pr_info("ERAX in ACPI found.\n");
	}

	status = acpi_get_object_info(erax_handle, &info);
	if (ACPI_FAILURE(status)) {
		pr_info("ERAX in ACPI not found.\n");
	} else {
		pr_info("acpi_get_object_info success.\n");
	}

	status = acpi_walk_namespace(ACPI_TYPE_ANY , erax_handle,
				     ACPI_UINT32_MAX,
				     acpi_walk_callback_erax,
				     NULL, NULL, NULL);
	if (ACPI_FAILURE(status)) {
		pr_info("acpi_walk_namespace faile.\n");
	} else {
		pr_info("acpi_walk_namespace succes\n");
	}

	status = acpi_walk_resources(adev->handle,
		    "_CRS", acpi_walk_ec_cb , NULL);
	if (ACPI_FAILURE(status)) {
		pr_info("acpi_walk_resources failed: %d \n", status);
	} else {
		pr_info("acpi_walk_resources was succesful\n");
	}

	struct acpi_gpio_chip *acpi_gpio;
	status = acpi_get_data(erax_handle, acpi_erax_dh, (void **)&acpi_gpio);
	if (ACPI_FAILURE(status)) {
		pr_info("acpi_get_data failed.\n");
	} else {
		pr_info("acpi_get_data was succesful\n");
	}

	status = acpi_evaluate_integer(erax_handle, "_REG", NULL, &erax_addr);
	if (ACPI_FAILURE(status)) {
		pr_info("ERAX _ADR not found.\n");
	} else {
		pr_info("ERAX _ADR not found.\n");
	}

	status = acpi_evaluate_object(NULL, "\\_SB_.PCI0.LPC0.EC0_.ERAX", NULL, &buffer);
	if (ACPI_FAILURE(status)){
		pr_info("getting EC start address: acpi_evaluate_object to get ERAX failed.\n");
		err = -EINVAL;
		goto error_acpi_evaluate_object;
	}

	// u8  a;
	// ec_read(0, &a);

	// resource = buffer.pointer;
	// if (resource->type != ACPI_RESOURCE_TYPE_ADDRESS16 &&
	// 	resource->type != ACPI_RESOURCE_TYPE_ADDRESS32 &&
	// 	resource->type != ACPI_RESOURCE_TYPE_ADDRESS64) {
	// 	err = -EINVAL;
	// 	pr_info("getting EC start address: acpi_evaluate_object to get ERAX failed.\n");
	// 	goto error_ressource_type;
	// }

	// if(resource->type == ACPI_RESOURCE_TYPE_ADDRESS32){
	// 	pr_info("Got 32 bit ACPI Address.\n");
	// }

	// acpi_resource_to_address64(resource, &address);
	// address = resource->data.address;
	// phys_addr_t phy_addr = address;
	// pr_info("Start address at %p \n", (void*) phy_addr);
		
	return 0;

error_ressource_type:
	kfree(resource);
error_acpi_evaluate_object:
	return err;
}



////////////




/*
 * Platform driver from ideapad_acpi.c in linux kernel (modified)
 * Use either that or ACPI driver.
 */
static int ideapad_acpi_add(struct acpi_device *adev)
{
	struct legion_private *priv = &_legion_priv;
	int err;
	phys_addr_t start_addr_ec;
	pr_info("Loading platform/ACPI driver.\n");

	if (!adev || eval_int(adev->handle, "_CFG", &cfg)){
		err = -ENODEV;
		return err;
	}

	pr_info("acpi device and _CFG succesful\n");
	
	err = legion_acpi_get_ec_start(adev, &start_addr_ec);
	if(err){
		pr_info("legion_acpi_get_ec_start failed!\n");
		return err;
	}

	priv->adev = adev;
	priv->ec_start_addr = start_addr_ec;
	//priv->platform_device = pdev;
	priv->loaded = true;

	return 0;
}

static int ideapad_acpi_remove(struct acpi_device *pdev)
{
	//struct legion_private *priv = dev_get_drvdata(&pdev->dev);
	return 0;
}

// static int ideapad_acpi_add_platform(struct platform_device *pdev)
// {
// 	struct acpi_device *adev = ACPI_COMPANION(&pdev->dev);	
// 	return ideapad_acpi_add(adev);
// }

// static int ideapad_acpi_remove_platform(struct platform_device *pdev)
// {
// 	//struct legion_private *priv = dev_get_drvdata(&pdev->dev);
// 	return 0;
// }

// static int ideapad_acpi_resume(struct device *dev)
// {
// 	return 0;
// }
// static SIMPLE_DEV_PM_OPS(ideapad_pm, NULL, ideapad_acpi_resume);

static const struct acpi_device_id ideapad_device_ids[] = {
	{ "VPC2004", 0 },
	{ "", 0 },
};
MODULE_DEVICE_TABLE(acpi, ideapad_device_ids);

// static struct platform_driver ideapad_acpi_driver = {
// 	.probe = ideapad_acpi_add,
// 	.remove = ideapad_acpi_remove,
// 	.driver = {
// 		.name   = "legion_acpi",
// 		.pm     = &ideapad_pm,
// 		.acpi_match_table = ACPI_PTR(ideapad_device_ids),
// 	},
// };

// static const struct acpi_device_id legion_device_ids[] = {
// 	{ "PNP0C09", 0 },
// 	{ "", 0 },
// };
// MODULE_DEVICE_TABLE(acpi, legion_device_ids);



static struct acpi_driver ideapad_extra_acpi_driver = {
	.name = "legion_additional6",
	.class = "Legion2",
	.ids =  ideapad_device_ids,
	.ops =  {
				.add =  ideapad_acpi_add,
				.remove = ideapad_acpi_remove,
			},
	.owner = THIS_MODULE,
};

static int acpi_driver_init(void){
	int err;

	// via platform driver
	// err = platform_driver_register(&ideapad_acpi_driver);
	// if (err) {
	// 	pr_info("Error laoding platform driver\n");
	// 	goto error_platform_driver_register;
	// }

	// err = platform_driver_probe(&ideapad_acpi_driver, ideapad_acpi_add);
	// if (err) {
	// 	pr_info("Error probing platform driver\n");
	// 	goto error_platform_driver_probe;
	// }

	// via acpi driver
	pr_info("Register ACPI driver.\n");
	err = acpi_bus_register_driver(&ideapad_extra_acpi_driver);
	if (err) {
		pr_info("Error loading acpi driver\n");
		goto error_register;
	}

	// err = acpi_bus_register_driver(&ideapad_acpi_driver, ideapad_acpi_add);
	// if (err) {#define MAXFANCURVESIZE 10
	// 	pr_info("Error probing platform driver\n");
	// 	goto error_platform_driver_probe;
	// }
	return 0;

	error_register:
		return err;
}

static void acpi_driver_exit(void){
	pr_info("Exit acpi driver\n");
	//platform_driver_unregister(&ideapad_acpi_driver);
	acpi_bus_unregister_driver(&ideapad_extra_acpi_driver);
}

///


