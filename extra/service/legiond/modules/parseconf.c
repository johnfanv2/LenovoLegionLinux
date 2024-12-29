#include "parseconf.h"
#include <ini.h>
#include <stdlib.h>
#include <string.h>

#define MATCH(s, n) strcmp(section, s) == 0 && strcmp(name, n) == 0

static int handler(void *user, const char *section, const char *name,
		   const char *value)
{
	LEGIOND_CONFIG *pconfig = (LEGIOND_CONFIG *)user;
	command *ptr_cmd = NULL;

	if (MATCH("main", "cpu_control")) {
		if (strcmp(value, "true") == 0)
			pconfig->cpu_control = true;
		else
			pconfig->cpu_control = false;
	} else if (MATCH("main", "gpu_control")) {
		ptr_cmd = &pconfig->gpu_control;
	} else if (MATCH("main", "fan_control")) {
		if (strcmp(value, "true") == 0)
			pconfig->fan_control = true;
		else
			pconfig->fan_control = false;
	} else if (MATCH("gpu_control", "tdp_ac_q")) {
		ptr_cmd = &pconfig->gpu_tdp_ac_q;
	} else if (MATCH("gpu_control", "tdp_bat_q")) {
		ptr_cmd = &pconfig->gpu_tdp_bat_q;
	} else if (MATCH("gpu_control", "tdp_ac_b")) {
		ptr_cmd = &pconfig->gpu_tdp_ac_b;
	} else if (MATCH("gpu_control", "tdp_bat_b")) {
		ptr_cmd = &pconfig->gpu_tdp_bat_b;
	} else if (MATCH("gpu_control", "tdp_ac_bp")) {
		ptr_cmd = &pconfig->gpu_tdp_ac_bp;
	} else if (MATCH("gpu_control", "tdp_bat_bp")) {
		ptr_cmd = &pconfig->gpu_tdp_bat_bp;
	} else if (MATCH("gpu_control", "tdp_ac_p")) {
		ptr_cmd = &pconfig->gpu_tdp_ac_p;
	} else if (MATCH("cpu_control", "bat_q")) {
		ptr_cmd = &pconfig->cpu_bat_q;
	} else if (MATCH("cpu_control", "ac_q")) {
		ptr_cmd = &pconfig->cpu_ac_q;
	} else if (MATCH("cpu_control", "bat_b")) {
		ptr_cmd = &pconfig->cpu_bat_b;
	} else if (MATCH("cpu_control", "ac_b")) {
		ptr_cmd = &pconfig->cpu_ac_b;
	} else if (MATCH("cpu_control", "bat_bp")) {
		ptr_cmd = &pconfig->cpu_bat_bp;
	} else if (MATCH("cpu_control", "ac_bp")) {
		ptr_cmd = &pconfig->cpu_ac_bp;
	} else if (MATCH("cpu_control", "ac_p")) {
		ptr_cmd = &pconfig->cpu_ac_p;
	} else {
		// unknown section
		return 0;
	}

	if (ptr_cmd) {
		strcpy((char *)ptr_cmd, value);
	}
	return 1;
}

static void init_config(LEGIOND_CONFIG *config)
{
	memset((void *)config, 0, sizeof(LEGIOND_CONFIG));

	config->fan_control = false;
	config->cpu_control = false;
}

int parseconf(LEGIOND_CONFIG *config)
{
	init_config(config);
	if (ini_parse(config_path, handler, config)) {
		printf("Unable to parse config\n");
		return 1;
	}
	return 0;
}
