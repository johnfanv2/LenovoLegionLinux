
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


