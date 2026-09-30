#include "parseconf.h"
#include <ini.h>
#include <stdio.h>
#include <string.h>

#define MATCH(s, n) (strcmp(section, s) == 0 && strcmp(name, n) == 0)

/* double_ac_{q,b,p,e}_{pl,temp} = two comma-separated numbers */
static bool parse_double_key(LEGIOND_CONFIG *pconfig, const char *name,
			     const char *value)
{
	static const char modes[] = { 'q', 'b', 'p', 'e' };
	char mode, kind[8];
	unsigned int a, b;

	if (sscanf(name, "double_ac_%c_%7s", &mode, kind) != 2)
		return false;
	for (size_t i = 0; i < sizeof(modes); i++) {
		if (modes[i] != mode)
			continue;
		unsigned int *dst = NULL;

		if (strcmp(kind, "pl") == 0)
			dst = pconfig->powerlimit_double_pl[i];
		else if (strcmp(kind, "temp") == 0)
			dst = pconfig->powerlimit_double_temp[i];
		if (dst == NULL)
			return false;
		if (sscanf(value, "%u,%u", &a, &b) != 2) {
			fprintf(stderr,
				"[cpu_powerlimit] %s needs two numbers\n",
				name);
			return true;
		}
		dst[0] = a;
		dst[1] = b;
		return true;
	}
	return false;
}

static int handler(void *user, const char *section, const char *name,
		   const char *value)
{
	LEGIOND_CONFIG *pconfig = (LEGIOND_CONFIG *)user;
	command *ptr_cmd = NULL;

	if (MATCH("main", "cpu_control")) {
		pconfig->cpu_control = strcmp(value, "true") == 0;
	} else if (MATCH("main", "gpu_control")) {
		ptr_cmd = &pconfig->gpu_control;
	} else if (MATCH("main", "nvidia_smi_path")) {
		ptr_cmd = &pconfig->nvidia_smi_path;
	} else if (MATCH("main", "rocm_smi_path")) {
		ptr_cmd = &pconfig->rocm_smi_path;
	} else if (MATCH("main", "fan_control")) {
		pconfig->fan_control = strcmp(value, "true") == 0;
	} else if (MATCH("main", "cpu_powerlimit_sync")) {
		pconfig->cpu_powerlimit_sync = strcmp(value, "true") == 0;
	} else if (MATCH("cpu_powerlimit", "bat_pl1")) {
		if (sscanf(value, "%u", &pconfig->powerlimit_bat_pl1) != 1)
			pconfig->powerlimit_bat_pl1 = 0;
	} else if (MATCH("cpu_powerlimit", "bat_pl2")) {
		if (sscanf(value, "%u", &pconfig->powerlimit_bat_pl2) != 1)
			pconfig->powerlimit_bat_pl2 = 0;
	} else if (MATCH("cpu_powerlimit", "double_sensors")) {
		if (sscanf(value, "%31[^,],%31s",
			   pconfig->powerlimit_double_sensor[0],
			   pconfig->powerlimit_double_sensor[1]) != 2) {
			fprintf(stderr,
				"[cpu_powerlimit] double_sensors needs two "
				"thermal zone types, e.g. SEN3,SEN4\n");
			pconfig->powerlimit_double_sensor[0][0] = '\0';
		}
	} else if (MATCH("cpu_powerlimit", "double_hysteresis")) {
		if (sscanf(value, "%u",
			   &pconfig->powerlimit_double_hysteresis) != 1)
			pconfig->powerlimit_double_hysteresis = 3;
	} else if (strcmp(section, "cpu_powerlimit") == 0 &&
		   parse_double_key(pconfig, name, value)) {
		/* double_ac_{q,b,p,e}_{pl,temp} */
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
		/*
		 * Returning 0 aborts the whole parse, so a single typo
		 * would silently drop every later key.  Warn and continue.
		 */
		fprintf(stderr, "unknown config key [%s] %s, ignoring\n", section, name);
		return 1;
	}

	if (ptr_cmd) {
		int written = snprintf(*ptr_cmd, sizeof(*ptr_cmd), "%s", value);
		if (written < 0 || (size_t)written >= sizeof(*ptr_cmd)) {
			fprintf(stderr, "config value for [%s] %s too long, ignoring\n",
				section, name);
			(*ptr_cmd)[0] = '\0';
		}
	}

	return 1;
}

int parseconf(LEGIOND_CONFIG *config)
{
	LEGIOND_CONFIG parsed = { 0 };

	parsed.powerlimit_double_hysteresis = 3;

	/* default GPU tool paths, overridable via config */
	snprintf(parsed.nvidia_smi_path, sizeof(parsed.nvidia_smi_path),
		 "%s", "/opt/bin/nvidia-smi");
	snprintf(parsed.rocm_smi_path, sizeof(parsed.rocm_smi_path),
		 "%s", "/opt/bin/rocm-smi");

	/*
	 * Parse into a scratch copy and publish it only on success.
	 * libinih keeps going after the first bad line, and the caller
	 * re-parses on every timer tick, so writing straight into *config
	 * would let a half-written legiond.ini zero fan_control and
	 * cpu_control and silently switch fan curve control off.
	 */
	if (ini_parse(config_path, handler, &parsed)) {
		fprintf(stderr, "Unable to parse config\n");
		return 1;
	}

	*config = parsed;
	return 0;
}
