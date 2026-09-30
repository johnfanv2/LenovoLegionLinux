#include "powerlimit.h"
#include "../public.h"
#include <fcntl.h>
#include <stdio.h>
#include <string.h>

/*
 * Some firmware (Legion Pro 7 16IAX10H, Q7CN) applies the CPU power limits
 * itself only in custom mode and leaves the other modes to OEM software on
 * Windows (the DPTF adaptive policy selects per-mode targets through
 * software-set conditions). On Linux the package limit then stays at the
 * BIOS boot value (30 W on Q7CN) in every other mode. When
 * cpu_powerlimit_sync is enabled, write the firmware's own per-mode
 * defaults, exported by legion-laptop, into the MMIO RAPL limit that the
 * CPU enforces.
 */

/* profile name as used in the defaults files; NULL = leave the limits alone */
static const char *ac_profile(POWER_STATE power_state)
{
	switch (power_state) {
	case P_AC_Q:
		return "low-power";
	case P_AC_B:
		return "balanced";
	case P_AC_P:
		return "performance";
	case P_AC_E:
		return "max-power";
	default:
		/* custom: the firmware applies the user's own limits */
		return NULL;
	}
}

/* index into the powerlimit_double_* tables, -1 for non-AC-mode states */
static int double_index(POWER_STATE power_state)
{
	switch (power_state) {
	case P_AC_Q:
		return POWERLIMIT_Q;
	case P_AC_B:
		return POWERLIMIT_B;
	case P_AC_P:
		return POWERLIMIT_P;
	case P_AC_E:
		return POWERLIMIT_E;
	default:
		return -1;
	}
}

/* temperature in degrees C of the thermal zone of this type, or -1000 */
static int zone_temp(const char *type)
{
	char path[PATH_MAX];

	for (int i = 0; i < 256; i++) {
		char name[32] = "";
		int millideg;

		snprintf(path, sizeof(path), "%s/thermal_zone%d/type",
			 thermal_path, i);
		{
			auto_stream fp = fopen(path, "r");
			if (fp == NULL) {
				if (i > 64)
					break; /* zones are numbered densely */
				continue;
			}
			if (fscanf(fp, "%31s", name) != 1 ||
			    strcmp(name, type) != 0)
				continue;
		}
		snprintf(path, sizeof(path), "%s/thermal_zone%d/temp",
			 thermal_path, i);
		auto_stream fp = fopen(path, "r");
		if (fp == NULL || fscanf(fp, "%d", &millideg) != 1)
			return -1000;
		return millideg / 1000;
	}
	return -1000;
}

/*
 * Firmware DPTF "double" targets: while both sensors are at or above the
 * mode's temperatures, a lower CPU limit leaves power and thermal headroom
 * for the GPU under combined load. Enter when both reach their thresholds
 * (the firmware's AND), leave once either is double_hysteresis below it.
 * The state resets on every power state change.
 */
static bool use_double(POWER_STATE power_state, const LEGIOND_CONFIG *config)
{
	static bool active;
	static POWER_STATE last_state = (POWER_STATE)P_ERROR_PROFILE;
	int idx = double_index(power_state);

	if (power_state != last_state) {
		active = false;
		last_state = power_state;
	}
	if (idx < 0 || config->powerlimit_double_sensor[0][0] == '\0' ||
	    config->powerlimit_double_pl[idx][0] == 0 ||
	    config->powerlimit_double_pl[idx][1] == 0 ||
	    config->powerlimit_double_temp[idx][0] == 0 ||
	    config->powerlimit_double_temp[idx][1] == 0)
		return active = false;

	int t0 = zone_temp(config->powerlimit_double_sensor[0]);
	int t1 = zone_temp(config->powerlimit_double_sensor[1]);
	int lim0 = config->powerlimit_double_temp[idx][0];
	int lim1 = config->powerlimit_double_temp[idx][1];
	int hyst = config->powerlimit_double_hysteresis;

	if (t0 == -1000 || t1 == -1000) {
		printf("cpu_powerlimit: double sensors %s/%s not found\n",
		       config->powerlimit_double_sensor[0],
		       config->powerlimit_double_sensor[1]);
		return active = false;
	}
	if (!active && t0 >= lim0 && t1 >= lim1)
		active = true;
	else if (active && (t0 < lim0 - hyst || t1 < lim1 - hyst))
		active = false;
	printf("cpu_powerlimit: %s %d C (>= %d), %s %d C (>= %d): %s target\n",
	       config->powerlimit_double_sensor[0], t0, lim0,
	       config->powerlimit_double_sensor[1], t1, lim1,
	       active ? "double" : "single");
	return active;
}

/* look up "profile:watts" in a defaults file; 0 when absent */
static unsigned int read_default_watts(const char *path, const char *profile)
{
	char line[256];

	{
		auto_stream fp = fopen(path, "r");
		if (fp == NULL || fgets(line, sizeof(line), fp) == NULL)
			return 0;
	}

	size_t len = strlen(profile);
	for (char *tok = strtok(line, " \n"); tok; tok = strtok(NULL, " \n")) {
		unsigned int watts;

		if (strncmp(tok, profile, len) == 0 && tok[len] == ':' &&
		    sscanf(tok + len + 1, "%u", &watts) == 1)
			return watts;
	}
	return 0;
}

/* check that an MMIO RAPL constraint is the one we expect it to be */
static bool constraint_is(int index, const char *expected_name)
{
	char path[PATH_MAX];
	char name[32] = "";

	snprintf(path, sizeof(path), "%s/constraint_%d_name", rapl_mmio_path,
		 index);
	auto_stream fp = fopen(path, "r");
	if (fp == NULL || fscanf(fp, "%31s", name) != 1) {
		printf("cpu_powerlimit: %s not readable\n", path);
		return false;
	}
	if (strcmp(name, expected_name) != 0) {
		printf("cpu_powerlimit: constraint %d is %s, expected %s\n",
		       index, name, expected_name);
		return false;
	}
	return true;
}

static int write_constraint(int index, unsigned int watts)
{
	char path[PATH_MAX];
	char value[32];

	snprintf(path, sizeof(path), "%s/constraint_%d_power_limit_uw",
		 rapl_mmio_path, index);
	/* unbuffered, so a rejected value is reported here, not lost in fclose */
	int len = snprintf(value, sizeof(value), "%u000000\n", watts);
	auto_fd fd = open(path, O_WRONLY);
	if (fd < 0 || write(fd, value, len) != len) {
		printf("cpu_powerlimit: failed to write %s\n", path);
		return 1;
	}
	return 0;
}

int set_cpu_powerlimit(POWER_STATE power_state, LEGIOND_CONFIG *config)
{
	if (!config->cpu_powerlimit_sync) {
		printf("cpu_powerlimit_sync is set to false\n");
		printf("skip cpu_powerlimit\n");
		return 0;
	}

	if ((int)power_state < 0) {
		printf("skip cpu_powerlimit (power state unknown)\n");
		return 0;
	}

	unsigned int pl1, pl2;

	if (power_state % 2) {
		/* battery: capdata has no DC defaults, use the configured ones */
		pl1 = config->powerlimit_bat_pl1;
		pl2 = config->powerlimit_bat_pl2;
	} else {
		const char *profile = ac_profile(power_state);

		if (profile == NULL) {
			printf("skip cpu_powerlimit (custom mode or unknown state)\n");
			return 0;
		}
		pl1 = read_default_watts(pl1_defaults_path, profile);
		pl2 = read_default_watts(pl2_defaults_path, profile);
		if (pl1 && pl2 && use_double(power_state, config)) {
			int idx = double_index(power_state);

			pl1 = config->powerlimit_double_pl[idx][0];
			pl2 = config->powerlimit_double_pl[idx][1];
		}
	}

	if (pl1 == 0 || pl2 == 0) {
		printf("no cpu power limits for this state\n");
		printf("skip cpu_powerlimit\n");
		return 0;
	}

	if (access(rapl_mmio_path, F_OK) != 0) {
		printf("no MMIO RAPL zone (%s)\n", rapl_mmio_path);
		printf("skip cpu_powerlimit\n");
		return 0;
	}

	/* validate both before writing either, so a surprise never half-applies */
	if (!constraint_is(0, "long_term") || !constraint_is(1, "short_term"))
		return 1;

	int result = write_constraint(0, pl1);
	result |= write_constraint(1, pl2);
	if (result == 0)
		printf("cpu_powerlimit set to PL1 %u W, PL2 %u W\n", pl1, pl2);

	return result;
}
