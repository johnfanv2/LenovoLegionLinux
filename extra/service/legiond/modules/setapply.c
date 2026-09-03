#include "setapply.h"
#include "powerstate.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int set_cpu(POWER_STATE power_state, LEGIOND_CONFIG *config)
{
	if (!config->cpu_control) {
		printf("cpu_control is set to false\n");
		printf("skip cpu_control\n");
		return 0;
	}

	const char *cmd = NULL;

	/*
	 * Battery states fall through to their AC counterpart when no
	 * battery-specific command is configured.
	 */
	switch (power_state) {
	case P_BAT_Q:
		cmd = config->cpu_bat_q;
		if (cmd[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_Q:
		cmd = config->cpu_ac_q;
		break;
	case P_BAT_B:
		cmd = config->cpu_bat_b;
		if (cmd[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_B:
		cmd = config->cpu_ac_b;
		break;
	case P_BAT_BP:
		cmd = config->cpu_bat_bp;
		if (cmd[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_BP:
		cmd = config->cpu_ac_bp;
		break;
	case P_BAT_P:
		cmd = config->cpu_bat_p;
		if (cmd[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_P:
		cmd = config->cpu_ac_p;
		break;
	case P_BAT_E:
		cmd = config->cpu_bat_e;
		if (cmd[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_E:
		cmd = config->cpu_ac_e;
		break;
	default:
		break;
	}

	int result = 0;

	if (cmd != NULL && cmd[0] != '\0') {
		result = system(cmd);
	} else {
		printf("no cpu_control cmd configured\n");
		printf("skip cpu_control\n");
		return 0;
	}

	if (result != 0) {
		printf("cpu_control cmd failed\n");
	} else {
		printf("cpu_control cmd started\n");
	}

	return result;
}

int set_fancurve(POWER_STATE power_state, LEGIOND_CONFIG *config)
{
	if (!config->fan_control) {
		printf("fan_control is set to false\n");
		printf("skip fan_control\n");
		return 0;
	}

	const char *preset = NULL;

	switch (power_state) {
	case P_AC_Q:
		preset = "quiet-ac";
		break;
	case P_BAT_Q:
		preset = "quiet-battery";
		break;
	case P_AC_B:
		preset = "balanced-ac";
		break;
	case P_BAT_B:
		preset = "balanced-battery";
		break;
	case P_AC_BP:
		preset = "balanced-performance-ac";
		break;
	case P_BAT_BP:
		preset = "balanced-performance-battery";
		break;
	case P_AC_P:
		preset = "performance-ac";
		break;
	case P_BAT_P:
		preset = "performance-battery";
		break;
	case P_BAT_E:
		/* no extreme-battery preset exists yet; keep max cooling */
		[[fallthrough]];
	case P_AC_E:
		preset = "extreme-ac";
		break;
	default:
		break;
	}

	int result = 0;

	if (preset != NULL) {
		char cmd[MAX_CMD_LEN + 64];
		snprintf(cmd, sizeof(cmd),
			 "legion_cli fancurve-write-preset-to-hw %s", preset);
		result = system(cmd);
	}

	if (result != 0) {
		printf("fancurve_control cmd failed\n");
	} else {
		printf("fancurve_control cmd started\n");
	}

	return result;
}

int set_gpu(POWER_STATE power_state, LEGIOND_CONFIG *config)
{
	if (strcmp(config->gpu_control, "false") == 0) {
		printf("gpu_control is set to false\n");
		printf("skip gpu_control\n");
		return 0;
	}

	const char *tool;

	if (strcmp(config->gpu_control, "nvidia") == 0) {
		tool = config->nvidia_smi_path;
	} else if (strcmp(config->gpu_control, "radeon") == 0) {
		tool = config->rocm_smi_path;
	} else {
		printf("unknown gpu_control value: %s\n", config->gpu_control);
		printf("skip gpu_control\n");
		return 0;
	}

	const char *tdp = NULL;

	/*
	 * Battery states fall through to their AC counterpart when no
	 * battery-specific tdp is configured.
	 */
	switch (power_state) {
	case P_BAT_Q:
		tdp = config->gpu_tdp_bat_q;
		if (tdp[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_Q:
		tdp = config->gpu_tdp_ac_q;
		break;
	case P_BAT_B:
		tdp = config->gpu_tdp_bat_b;
		if (tdp[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_B:
		tdp = config->gpu_tdp_ac_b;
		break;
	case P_BAT_BP:
		tdp = config->gpu_tdp_bat_bp;
		if (tdp[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_BP:
		tdp = config->gpu_tdp_ac_bp;
		break;
	case P_BAT_P:
		tdp = config->gpu_tdp_bat_p;
		if (tdp[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_P:
		tdp = config->gpu_tdp_ac_p;
		break;
	case P_BAT_E:
		tdp = config->gpu_tdp_bat_e;
		if (tdp[0] != '\0')
			break;
		[[fallthrough]];
	case P_AC_E:
		tdp = config->gpu_tdp_ac_e;
		break;
	default:
		break;
	}

	int result = 0;

	if (tdp != NULL && tdp[0] != '\0') {
		const char *mode = strcmp(config->gpu_control, "nvidia") == 0
					   ? "-pl "
					   : "--setpoweroverdrive ";
		char cmd[MAX_CMD_LEN + 64];
		int written = snprintf(cmd, sizeof(cmd), "%s %s%s", tool, mode, tdp);
		if (written < 0 || written >= (int)sizeof(cmd)) {
			printf("gpu_control cmd too long, skipping\n");
		} else {
			result = system(cmd);
		}
	} else {
		printf("no gpu_control tdp configured\n");
		printf("skip gpu_control\n");
		return 0;
	}

	if (result != 0) {
		printf("gpu_control cmd failed\n");
	} else {
		printf("gpu_control cmd started\n");
	}

	return result;
}

int set_all(POWER_STATE power_state, LEGIOND_CONFIG *config)
{
	int result = 0;

	result |= set_fancurve(power_state, config);
	result |= set_cpu(power_state, config);
	result |= set_gpu(power_state, config);

	return result;
}
