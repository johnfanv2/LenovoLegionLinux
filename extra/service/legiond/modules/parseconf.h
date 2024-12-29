#ifndef PARSECONF_H_
#define PARSECONF_H_
#include <ini.h>
#include <stdbool.h>

#define config_path "/etc/legion_linux/legiond.ini"
typedef char command[100];

typedef struct _LEGIOND_CONFIG {
	bool fan_control;
	bool cpu_control;
	command gpu_control;
	command cpu_ac_q;
	command cpu_bat_q;
	command cpu_ac_b;
	command cpu_bat_b;
	command cpu_ac_bp;
	command cpu_bat_bp;
	command cpu_ac_p;
	command gpu_tdp_ac_q;
	command gpu_tdp_bat_q;
	command gpu_tdp_ac_b;
	command gpu_tdp_bat_b;
	command gpu_tdp_ac_bp;
	command gpu_tdp_bat_bp;
	command gpu_tdp_ac_p;
} LEGIOND_CONFIG;

int parseconf(LEGIOND_CONFIG *config);

#endif // PARSECONF_H_
