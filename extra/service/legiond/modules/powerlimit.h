#ifndef POWERLIMIT_H_
#define POWERLIMIT_H_
#include "parseconf.h"
#include "powerstate.h"

/*
 * legion-laptop's driver directory. The firmware's per-mode defaults
 * ("profile:watts ...") are in the bound device's directory below it,
 * whose name depends on the kernel version, so it is searched at runtime.
 * The paths can be overridden at build time (e.g. for testing).
 */
#ifndef legion_driver_path
#define legion_driver_path "/sys/bus/platform/drivers/legion"
#endif
#define pl1_defaults_name "cpu_longterm_powerlimit_defaults"
#define pl2_defaults_name "cpu_shortterm_powerlimit_defaults"
/* thermal zones, searched by type for the double-target sensors */
#ifndef thermal_path
#define thermal_path "/sys/class/thermal"
#endif
/* the package limit the CPU enforces (the lower of MSR and MMIO RAPL) */
#ifndef rapl_mmio_path
#define rapl_mmio_path "/sys/class/powercap/intel-rapl-mmio:0"
#endif

[[nodiscard]] int set_cpu_powerlimit(POWER_STATE power_state,
				     LEGIOND_CONFIG *config);

#endif // POWERLIMIT_H_
