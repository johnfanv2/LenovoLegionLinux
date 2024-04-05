#include "powerstate.h"
#include <stdio.h>
#include <string.h>

#define MATCH(a, b) strcmp(a, b) == 0

extern POWER_STATE get_powerstate()
{
	FILE *fp;
	fp = fopen(ac_path, "r");
	int state;
	if (fscanf(fp, "%d", &state) != 1) {
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
		if (state) {
			return P_AC_Q;
		} else {
			return P_BAT_Q;
		}
	} else if (MATCH(profile, "balanced")) {
		if (state) {
			return P_AC_B;
		} else {
			return P_BAT_B;
		}
	} else if (MATCH(profile, "balanced-performance")) {
		if (state) {
			return P_AC_BP;
		} else {
			return P_BAT_BP;
		}
	} else if (MATCH(profile, "performance")) {
		return P_AC_P;
	}
	return -1;
}
