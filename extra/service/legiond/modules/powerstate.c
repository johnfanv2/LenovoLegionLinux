#include "powerstate.h"
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>

#define MATCH(a, b) strcmp(a, b) == 0

POWER_STATE get_powerstate()
{
	POWER_STATE power_state = -1;
	FILE *fp;

	fp = fopen(ac_path, "r");
	if (fp == NULL)
		fp = fopen(ac_path_alt, "r");
	
	if (fp == NULL) {
		printf("failed to open AC power status file\n");
		return P_ERROR_AC;
	}

	int ac_state;
	if (fscanf(fp, "%d", &ac_state) != 1) {
		printf("failed to get AC status\n");
		fclose(fp);
		return P_ERROR_AC;
	}
	fclose(fp);

	fp = fopen(profile_path, "r");
	if (fp == NULL) {
		printf("failed to open power profile file\n");
		return P_ERROR_PROFILE;
	}
	
	char profile[30];
	if (fscanf(fp, "%29s", profile) != 1) {
		printf("failed to get power_profile\n");
		fclose(fp);
		return P_ERROR_PROFILE;
	}
	fclose(fp);
	
	if (MATCH(profile, "quiet") || MATCH(profile, "low-power")) {
		power_state = P_AC_Q;
	} else if (MATCH(profile, "balanced")) {
		power_state = P_AC_B;
	} else if (MATCH(profile, "performance")) {
		power_state = P_AC_P;
	} else if (MATCH(profile, "balanced-performance") || MATCH(profile, "custom")) {
		// Custom Mode
		power_state = P_AC_BP;
	} else if (MATCH(profile, "extreme") || MATCH(profile, "max-power")) {
		// Extreme Mode
		power_state = P_AC_E;
	}


	if (!ac_state && power_state != -1) {
		switch (power_state) {
		case P_AC_Q:
			power_state = P_BAT_Q;
			break;
		case P_AC_B:
			power_state = P_BAT_B;
			break;
		case P_AC_BP:
			power_state = P_BAT_BP;
			break;
		case P_AC_P:
			power_state = P_BAT_P;
			break;
		case P_AC_E:
			power_state = P_BAT_E;
			break;
		default:
			break;
		}
	}

	return power_state;
}
