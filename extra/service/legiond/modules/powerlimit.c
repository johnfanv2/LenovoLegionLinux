#include "powerlimit.h"
#include "../public.h"
#include <fcntl.h>
#include <glob.h>
#include <stdarg.h>
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

/*
 * set_cpu_powerlimit() runs on every legiond-cpuset.timer tick (30 s), and
 * with cpu_powerlimit_sync off too. Every outcome, written or skipped, goes
 * through report(), which logs it only when it differs from the previous
 * call's outcome. A steady state is logged once, and any change (e.g. back to
 * a written limit after a skip) is logged again.
 */
static char last_report[384];

[[gnu::format(printf, 1, 2)]] static void report(const char *fmt, ...)
{
	char msg[sizeof(last_report)];
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(msg, sizeof(msg), fmt, ap);
	va_end(ap);
	if (strcmp(msg, last_report) == 0)
		return;
	snprintf(last_report, sizeof(last_report), "%s", msg);
	printf("%s\n", msg);
}

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

	/* runs on every legiond-cpuset.timer tick: log transitions only */
	static bool sensors_missing;

	if (t0 == -1000 || t1 == -1000) {
		if (!sensors_missing)
			printf("cpu_powerlimit: double sensors %s/%s not found\n",
			       config->powerlimit_double_sensor[0],
			       config->powerlimit_double_sensor[1]);
		sensors_missing = true;
		return active = false;
	}
	sensors_missing = false;

	bool was_active = active;

	if (!active && t0 >= lim0 && t1 >= lim1)
		active = true;
	else if (active && (t0 < lim0 - hyst || t1 < lim1 - hyst))
		active = false;
	if (active != was_active)
		printf("cpu_powerlimit: %s %d C (>= %d), %s %d C (>= %d): "
		       "%s the double target\n",
		       config->powerlimit_double_sensor[0], t0, lim0,
		       config->powerlimit_double_sensor[1], t1, lim1,
		       active ? "entering" : "leaving");
	return active;
}

/*
 * Find a legion-laptop attribute file. The driver binds a platform device
 * named "legion" on kernel >= 7.0 and the ACPI device (e.g. "PNP0C09:00")
 * before, so the device directory's name differs; take the first match.
 */
static bool find_legion_attr(const char *name, char *path, size_t size)
{
	char pattern[PATH_MAX];
	glob_t matches;
	bool found = false;

	snprintf(pattern, sizeof(pattern), "%s/*/%s", legion_driver_path, name);
	/* globfree() only after a successful glob(), as POSIX requires */
	if (glob(pattern, 0, NULL, &matches) == 0) {
		if (matches.gl_pathc > 0)
			found = snprintf(path, size, "%s",
					 matches.gl_pathv[0]) < (int)size;
		globfree(&matches);
	}
	return found;
}

/*
 * Upper bound for a default the driver reports. The defaults come from the
 * firmware's capability data, so this only catches a garbled read; it is
 * not a hardware limit. MMIO constraint_0_max_power_uw cannot be used for
 * this: it reports the CPU's base power (55 W on the 16IAX10H), well below
 * the firmware's own performance defaults (145 W).
 */
#define POWERLIMIT_MAX_WATTS 500

/*
 * Look up "profile:watts" in a defaults file. Every whitespace-separated
 * token in the file is checked, not just the first line. Returns 0 when
 * the profile is absent or its value is implausible; in the latter case the
 * offending token is copied to bad (for the caller's log line).
 */
static unsigned int read_default_watts(const char *path, const char *profile,
				       char *bad, size_t bad_size)
{
	/*
	 * The kernel prints about 70 bytes ("low-power:55 balanced:90 ...").
	 * A file that fills the buffer is cut at its last whitespace below, so a
	 * token split at the buffer end (e.g. "performance:14" of "...:145") is
	 * dropped rather than misread.
	 */
	char text[1024];
	size_t len;

	bad[0] = '\0';
	{
		auto_stream fp = fopen(path, "r");
		if (fp == NULL)
			return 0;
		len = fread(text, 1, sizeof(text) - 1, fp);
	}
	text[len] = '\0';
	if (len == sizeof(text) - 1) {
		while (len > 0 && !strchr(" \t\n", text[len - 1]))
			len--;
		text[len] = '\0';
	}

	size_t plen = strlen(profile);
	char *save;
	for (char *tok = strtok_r(text, " \t\n", &save); tok;
	     tok = strtok_r(NULL, " \t\n", &save)) {
		unsigned int watts;
		char extra;

		if (strncmp(tok, profile, plen) != 0 || tok[plen] != ':')
			continue;
		if (sscanf(tok + plen + 1, "%u%c", &watts, &extra) != 1 ||
		    watts == 0 || watts > POWERLIMIT_MAX_WATTS) {
			snprintf(bad, bad_size, "%s", tok);
			return 0;
		}
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
		report("cpu_powerlimit: %s not readable, skip", path);
		return false;
	}
	if (strcmp(name, expected_name) != 0) {
		report("cpu_powerlimit: constraint %d is %s, expected %s, skip",
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
		report("cpu_powerlimit: failed to write %u W to %s", watts,
		       path);
		return 1;
	}
	return 0;
}

int set_cpu_powerlimit(POWER_STATE power_state, LEGIOND_CONFIG *config)
{
	if (!config->cpu_powerlimit_sync) {
		report("cpu_powerlimit_sync is set to false, skip cpu_powerlimit");
		return 0;
	}

	if ((int)power_state < 0) {
		report("skip cpu_powerlimit (power state unknown)");
		return 0;
	}

	unsigned int pl1, pl2;
	char bad[64] = "";

	if (power_state % 2) {
		/* battery: capdata has no DC defaults, use the configured ones */
		pl1 = config->powerlimit_bat_pl1;
		pl2 = config->powerlimit_bat_pl2;
	} else {
		const char *profile = ac_profile(power_state);

		if (profile == NULL) {
			/* the firmware sets the limit in custom mode */
			report("skip cpu_powerlimit (custom mode or unknown state)");
			return 0;
		}
		char pl1_path[PATH_MAX], pl2_path[PATH_MAX];

		const char *missing = NULL;

		if (!find_legion_attr(pl1_defaults_name, pl1_path,
				      sizeof(pl1_path)))
			missing = pl1_defaults_name;
		else if (!find_legion_attr(pl2_defaults_name, pl2_path,
					   sizeof(pl2_path)))
			missing = pl2_defaults_name;
		if (missing) {
			report("cpu_powerlimit: no %s/*/%s, "
			       "power limit defaults unavailable",
			       legion_driver_path, missing);
			return 0;
		}
		pl1 = read_default_watts(pl1_path, profile, bad, sizeof(bad));
		if (pl1)
			pl2 = read_default_watts(pl2_path, profile, bad,
						 sizeof(bad));
		else
			pl2 = 0;
		if (bad[0] != '\0') {
			report("cpu_powerlimit: ignoring implausible %s in the "
			       "defaults, skip cpu_powerlimit",
			       bad);
			return 0;
		}
		if (pl1 && pl2 && use_double(power_state, config)) {
			int idx = double_index(power_state);

			pl1 = config->powerlimit_double_pl[idx][0];
			pl2 = config->powerlimit_double_pl[idx][1];
		}
	}

	if (pl1 == 0 || pl2 == 0) {
		report("no cpu power limits for this state, skip cpu_powerlimit");
		return 0;
	}

	if (access(rapl_mmio_path, F_OK) != 0) {
		report("no MMIO RAPL zone (%s), skip cpu_powerlimit",
		       rapl_mmio_path);
		return 0;
	}

	/* validate both before writing either, so a surprise never half-applies */
	if (!constraint_is(0, "long_term") || !constraint_is(1, "short_term"))
		return 1;

	/* stop at the first failure: one log line, and no PL2 without PL1 */
	int result = write_constraint(0, pl1);
	if (result == 0)
		result = write_constraint(1, pl2);
	if (result == 0)
		report("cpu_powerlimit set to PL1 %u W, PL2 %u W", pl1, pl2);

	return result;
}
