#include "powerstate.h"
#include <stdio.h>
#include <string.h>

#define MATCH(a, b) strcmp(a, b) == 0

extern int get_powerstate()
{
	FILE *fp;
	fp = fopen(ac_path, "r");
	int state;
	fscanf(fp, "%d", &state);
	fclose(fp);

	fp = fopen(profile_path, "r");
	char profile[30];
	fscanf(fp, "%s", profile);
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
