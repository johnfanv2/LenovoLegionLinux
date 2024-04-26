#ifndef PARSECONF_H_
#define PARSECONF_H_
#include <ini.h>
#include <stdbool.h>

#define config_path "/etc/legion_linux/legiond.ini"

typedef struct _LEGIOND_CONFIG {
	bool fan_control;
	bool cpu_control;
	const char *gpu_control;
	const char *cpu_ac_q;
	const char *cpu_bat_q;
	const char *cpu_ac_b;
	const char *cpu_bat_b;
	const char *cpu_ac_bp;
	const char *cpu_bat_bp;
	const char *cpu_ac_p;
	const char *gpu_tdp_ac_q;
	const char *gpu_tdp_bat_q;
	const char *gpu_tdp_ac_b;
	const char *gpu_tdp_bat_b;
	const char *gpu_tdp_ac_bp;
	const char *gpu_tdp_bat_bp;
	const char *gpu_tdp_ac_p;
} LEGIOND_CONFIG;

int parseconf(LEGIOND_CONFIG *config);

#endif // PARSECONF_H_
