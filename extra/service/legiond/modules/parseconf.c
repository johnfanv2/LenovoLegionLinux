#include "parseconf.h"
#include <ini.h>
#include <stdio.h>
#include <string.h>

#define MATCH(s, n) (strcmp(section, s) == 0 && strcmp(name, n) == 0)

static int handler(void *user, const char *section, const char *name,
		   const char *value)
{
	LEGIOND_CONFIG *pconfig = (LEGIOND_CONFIG *)user;
	command *ptr_cmd = NULL;

	if (MATCH("main", "cpu_control")) {
		pconfig->cpu_control = strcmp(value, "true") == 0;
	} else if (MATCH("main", "gpu_control")) {
		ptr_cmd = &pconfig->gpu_control;
	} else if (MATCH("main", "fan_control")) {
		pconfig->fan_control = strcmp(value, "true") == 0;
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
	} else if (MATCH("gpu_control", "tdp_bat_p")) {
		ptr_cmd = &pconfig->gpu_tdp_bat_p;
	} else if (MATCH("gpu_control", "tdp_ac_e")) {
		ptr_cmd = &pconfig->gpu_tdp_ac_e;
	} else if (MATCH("gpu_control", "tdp_bat_e")) {
		ptr_cmd = &pconfig->gpu_tdp_bat_e;
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
	} else if (MATCH("cpu_control", "bat_p")) {
		ptr_cmd = &pconfig->cpu_bat_p;
	} else if (MATCH("cpu_control", "ac_e")) {
		ptr_cmd = &pconfig->cpu_ac_e;
	} else if (MATCH("cpu_control", "bat_e")) {
		ptr_cmd = &pconfig->cpu_bat_e;
	} else {
		// unknown section
		return 0;
	}

	if (ptr_cmd)
		snprintf(*ptr_cmd, sizeof(*ptr_cmd), "%s", value);

	return 1;
}

int parseconf(LEGIOND_CONFIG *config)
{
	*config = (LEGIOND_CONFIG){ 0 };

	if (ini_parse(config_path, handler, config)) {
		printf("Unable to parse config\n");
		return 1;
	}
	return 0;
}
