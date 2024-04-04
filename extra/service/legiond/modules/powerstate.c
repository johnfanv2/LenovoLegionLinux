#include "powerstate.h"
#include <stdio.h>
#include <string.h>

extern int get_powerstate()
{
	FILE *fp;
	fp = fopen(ac_path, "r");
	fclose(fp);
	int state;
	fscanf(fp, "%d", &state);
	fclose(fp);

	fp = fopen(profile_path, "r");
	char profile[30];
	fscanf(fp, "%s", profile);
	if (strcmp(profile, "quiet") == 0) {
		if (state) {
			return P_AC_Q;
		} else {
			return P_BAT_Q;
		}
	} else if (strcmp(profile, "balanced") == 0) {
		if (state) {
			return P_AC_B;
		} else {
			return P_BAT_B;
		}
	} else if (strcmp(profile, "balanced-performance") == 0) {
		if (state) {
			return P_AC_BP;
		} else {
			return P_BAT_BP;
		}
	} else if (strcmp(profile, "performance") == 0) {
		return P_AC_P;
	}
	return -1;
}
