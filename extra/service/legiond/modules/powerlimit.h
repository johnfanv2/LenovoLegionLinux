#ifndef POWERLIMIT_H_
#define POWERLIMIT_H_
#include "parseconf.h"
#include "powerstate.h"

/*
 * Firmware per-mode defaults exported by legion-laptop, "profile:watts ...".
 * The paths can be overridden at build time (e.g. for testing).
 */
#ifndef pl1_defaults_path
#define pl1_defaults_path \
	"/sys/bus/platform/drivers/legion/legion/cpu_longterm_powerlimit_defaults"
#endif
#ifndef pl2_defaults_path
#define pl2_defaults_path \
	"/sys/bus/platform/drivers/legion/legion/cpu_shortterm_powerlimit_defaults"
#endif
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
