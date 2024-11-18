#ifndef POWERSTATE_H_
#define POWERSTATE_H_

typedef enum _POWER_STATE {
	P_AC_Q = 0,
	P_BAT_Q = 1,
	P_AC_B = 2,
	P_BAT_B = 3,
	P_AC_BP = 4,
	P_BAT_BP = 5,
	P_AC_P = 6
} POWER_STATE;

#define P_ERROR_PROFILE -1
#define P_ERROR_AC -2

#define ac_path "/sys/class/power_supply/ADP0/online"
#define ac_path_alt "/sys/class/power_supply/ACAD/online"
#define profile_path "/sys/firmware/acpi/platform_profile"

POWER_STATE get_powerstate();

#endif // POWERSTATE_H_
