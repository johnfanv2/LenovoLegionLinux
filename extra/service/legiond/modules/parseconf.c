#include "parseconf.h"
#include <ini.h>
#include <stdlib.h>
#include <string.h>

#define MATCH(s, n) strcmp(section, s) == 0 && strcmp(name, n) == 0

static bool reload = false;

static int handler(void *user, const char *section, const char *name,
		   const char *value)
{
	LEGIOND_CONFIG *pconfig = (LEGIOND_CONFIG *)user;
	if (MATCH("main", "cpu_control")) {
		if (strcmp(value, "true") == 0)
			pconfig->cpu_control = true;
		else
			pconfig->cpu_control = false;
	} else if (MATCH("main", "gpu_control")) {
		pconfig->gpu_control = strdup(value);
	} else if (MATCH("main", "fan_control")) {
		if (strcmp(value, "true") == 0)
			pconfig->fan_control = true;
		else
			pconfig->fan_control = false;
	} else if (MATCH("gpu_control", "tdp_ac_q")) {
		pconfig->gpu_tdp_ac_q = strdup(value);
	} else if (MATCH("gpu_control", "tdp_bat_q")) {
		pconfig->gpu_tdp_bat_q = strdup(value);
	} else if (MATCH("gpu_control", "tdp_ac_b")) {
		pconfig->gpu_tdp_ac_b = strdup(value);
	} else if (MATCH("gpu_control", "tdp_bat_b")) {
		pconfig->gpu_tdp_bat_b = strdup(value);
	} else if (MATCH("gpu_control", "tdp_ac_bp")) {
		pconfig->gpu_tdp_ac_bp = strdup(value);
	} else if (MATCH("gpu_control", "tdp_bat_bp")) {
		pconfig->gpu_tdp_bat_bp = strdup(value);
	} else if (MATCH("gpu_control", "tdp_ac_p")) {
		pconfig->gpu_tdp_ac_p = strdup(value);
	} else if (MATCH("cpu_control", "bat_q")) {
		pconfig->cpu_bat_q = strdup(value);
	} else if (MATCH("cpu_control", "ac_q")) {
		pconfig->cpu_ac_q = strdup(value);
	} else if (MATCH("cpu_control", "bat_b")) {
		pconfig->cpu_bat_b = strdup(value);
	} else if (MATCH("cpu_control", "ac_b")) {
		pconfig->cpu_ac_b = strdup(value);
	} else if (MATCH("cpu_control", "bat_bp")) {
		pconfig->cpu_bat_bp = strdup(value);
	} else if (MATCH("cpu_control", "ac_bp")) {
		pconfig->cpu_ac_bp = strdup(value);
	} else if (MATCH("cpu_control", "ac_p")) {
		pconfig->cpu_ac_p = strdup(value);
	} else {
		// unknown section
		return 0;
	}
	return 1;
}

static void reset(const char *p)
{
	if (p && reload) {
		free((char *)p);
	}
	p = NULL;
}

static void init_config(LEGIOND_CONFIG *config)
{
	config->fan_control = false;
	config->cpu_control = false;
	reset(config->gpu_control);
	reset(config->cpu_ac_q);
	reset(config->cpu_bat_q);
	reset(config->cpu_ac_b);
	reset(config->cpu_bat_b);
	reset(config->cpu_ac_bp);
	reset(config->cpu_bat_bp);
	reset(config->cpu_ac_p);
	reset(config->gpu_tdp_ac_q);
	reset(config->gpu_tdp_bat_q);
	reset(config->gpu_tdp_ac_b);
	reset(config->gpu_tdp_bat_b);
	reset(config->gpu_tdp_ac_bp);
	reset(config->gpu_tdp_bat_bp);
	reset(config->gpu_tdp_ac_p);

	if (!reload)
		reload = true;
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
