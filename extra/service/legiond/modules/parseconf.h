#ifndef PARSECONF_H_
#define PARSECONF_H_
#include <ini.h>
#include <stdbool.h>

#define config_path "/etc/legion_linux/legiond.ini"
#define MAX_CMD_LEN 100
typedef char command[MAX_CMD_LEN];

typedef struct _LEGIOND_CONFIG {
	bool fan_control;
	bool cpu_control;
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
