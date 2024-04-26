#include "powerstate.h"
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>

#define MATCH(a, b) strcmp(a, b) == 0

static POWER_STATE get_ppdstate()
{
	char *cmd = "powerprofilesctl get";
	char result[50] = { 0 };
	FILE *fp = NULL;
	fp = popen(cmd, "r");
	if (fp == NULL) {
		printf("failed to run powerprofilesctl\n");
	}

	if (!fread(result, sizeof(char), sizeof(result), fp)) {
		printf("failed to parse powerprofile\n");
		return -2;
	}
	pclose(fp);

	result[strlen(result) - 1] = 0;

	if (MATCH(result, "performance")) {
		return P_AC_P;
	} else if (MATCH(result, "balanced")) {
		return P_AC_B;
	} else if (MATCH(result, "power-saver")) {
		return P_AC_Q;
	}

	return -1;
}

POWER_STATE get_powerstate()
{
	static bool use_ppd = false;
	static bool initialize = false;
	POWER_STATE power_state = -1;
	FILE *fp;

	if (!initialize) {
		initialize = true;
		if (access(profile_path, F_OK)) {
			use_ppd = true;
		}
	}

	fp = fopen(ac_path, "r");
	int ac_state;
	if (fscanf(fp, "%d", &ac_state) != 1) {
		printf("failed to get AC status\n");
		return P_ERROR_AC;
	}
	fclose(fp);

	if (use_ppd) {
		power_state = get_ppdstate();
	} else {
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
		} else if (MATCH(profile, "balanced-performance")) {
			power_state = P_AC_BP;
		} else if (MATCH(profile, "performance")) {
			power_state = P_AC_P;
		}
	}

	if (!ac_state && power_state != -1) {
		power_state++;
	}

	return power_state;
}
