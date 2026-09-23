#include "powerstate.h"
#include "../public.h"
#include <stdio.h>
#include <string.h>

#define MATCH(a, b) (strcmp(a, b) == 0)
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))

POWER_STATE get_powerstate(void)
{
	int ac_state;

	{
		auto_stream fp = fopen(ac_path, "r");
		if (fp == NULL)
			fp = fopen(ac_path_alt, "r");

		if (fp == NULL) {
			printf("failed to open AC power status file\n");
			return P_ERROR_AC;
		}

		if (fscanf(fp, "%d", &ac_state) != 1) {
			printf("failed to get AC status\n");
			return P_ERROR_AC;
		}
	}

	char profile[30];

	{
		auto_stream fp = fopen(profile_path, "r");
		if (fp == NULL) {
			printf("failed to open power profile file\n");
			return P_ERROR_PROFILE;
		}

		if (fscanf(fp, "%29s", profile) != 1) {
			printf("failed to get power_profile\n");
			return P_ERROR_PROFILE;
		}
	}

	static const struct {
		const char *name;
		POWER_STATE state;
	} profile_map[] = {
		{ "quiet", P_AC_Q },
		{ "low-power", P_AC_Q },
		{ "balanced", P_AC_B },
		{ "performance", P_AC_P },
		{ "balanced-performance", P_AC_BP }, // Custom Mode
		{ "custom", P_AC_BP },
		{ "extreme", P_AC_E }, // Extreme Mode
		{ "max-power", P_AC_E },
	};

	POWER_STATE power_state = P_ERROR_PROFILE;
	for (size_t i = 0; i < ARRAY_SIZE(profile_map); i++) {
		if (MATCH(profile, profile_map[i].name)) {
			power_state = profile_map[i].state;
			break;
		}
	}

	/*
	 * The enum interleaves AC (even) and battery (odd) states, so the
	 * battery variant of any valid AC state is the next enumerator.
	 */
	_Static_assert(P_BAT_Q == P_AC_Q + 1, "enum layout");
	_Static_assert(P_BAT_B == P_AC_B + 1, "enum layout");
	_Static_assert(P_BAT_BP == P_AC_BP + 1, "enum layout");
	_Static_assert(P_BAT_P == P_AC_P + 1, "enum layout");
	_Static_assert(P_BAT_E == P_AC_E + 1, "enum layout");

	if (!ac_state && power_state != (POWER_STATE)P_ERROR_PROFILE)
		power_state = (POWER_STATE)(power_state + 1);

	return power_state;
}
