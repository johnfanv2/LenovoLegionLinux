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

	int ac_state;
	if (fscanf(fp, "%d", &ac_state) != 1) {
		printf("failed to get AC status\n");
		return P_ERROR_AC;
	}
	fclose(fp);

	fp = fopen(profile_path, "r");
	char profile[30];
	if (fscanf(fp, "%s", profile) != 1) {
		printf("failed to get power_profile\n");
		return P_ERROR_PROFILE;
	}
	fclose(fp);
	
	if (MATCH(profile, "quiet")) {
		power_state = P_AC_Q;
	} else if (MATCH(profile, "balanced")) {
		power_state = P_AC_B;
	} else if (MATCH(profile, "performance")) {
		power_state = P_AC_P;
	} else if (MATCH(profile, "balanced-performance")) {
		// Custom Mode
		power_state = P_AC_BP;
	}

	if (!ac_state && power_state != -1) {
		power_state++;
	}

	return power_state;
}
