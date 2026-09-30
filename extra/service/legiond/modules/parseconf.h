#ifndef PARSECONF_H_
#define PARSECONF_H_
#include <ini.h>
#include <stdbool.h>

#ifndef config_path /* overridable at build time, e.g. for testing */
#define config_path "/etc/legion_linux/legiond.ini"
#endif
#define MAX_CMD_LEN 100

/* index of the AC modes in the powerlimit_double_* tables */
enum { POWERLIMIT_Q, POWERLIMIT_B, POWERLIMIT_P, POWERLIMIT_E };
typedef char command[MAX_CMD_LEN];

typedef struct _LEGIOND_CONFIG {
	bool fan_control;
	bool cpu_control;
	/* write the firmware's per-mode CPU power limits to MMIO RAPL */
	bool cpu_powerlimit_sync;
	/* battery PL1/PL2 in watts for cpu_powerlimit_sync; 0 = leave alone */
	unsigned int powerlimit_bat_pl1;
	unsigned int powerlimit_bat_pl2;
	/*
	 * Combined-load ("double") limits for cpu_powerlimit_sync, per AC
	 * mode (index POWERLIMIT_Q/B/P/E): used while both double_sensors
	 * (thermal zone types) are at or above the mode's temperatures, as
	 * the firmware's DPTF *_Double targets do on Windows. 0 = unset.
	 */
	char powerlimit_double_sensor[2][32];
	unsigned int powerlimit_double_hysteresis; /* degrees C */
	unsigned int powerlimit_double_pl[4][2]; /* PL1, PL2 in watts */
	unsigned int powerlimit_double_temp[4][2]; /* degrees C per sensor */
	command gpu_control;
	command nvidia_smi_path;
	command rocm_smi_path;
	command cpu_ac_q;
	command cpu_bat_q;
	command cpu_ac_b;
	command cpu_bat_b;
	command cpu_ac_bp;
	command cpu_bat_bp;
	command cpu_ac_p;
	command cpu_bat_p;
	command cpu_ac_e;
	command cpu_bat_e;
	command gpu_tdp_ac_q;
	command gpu_tdp_bat_q;
	command gpu_tdp_ac_b;
	command gpu_tdp_bat_b;
	command gpu_tdp_ac_bp;
	command gpu_tdp_bat_bp;
	command gpu_tdp_ac_p;
	command gpu_tdp_bat_p;
	command gpu_tdp_ac_e;
	command gpu_tdp_bat_e;
} LEGIOND_CONFIG;

int parseconf(LEGIOND_CONFIG *config);

#endif // PARSECONF_H_
