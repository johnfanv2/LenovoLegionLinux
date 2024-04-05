#ifndef POWERSTATE_H_
#define POWERSTATE_H_

typedef enum _POWER_STATE {
	P_AC_Q,
	P_BAT_Q,
	P_AC_B,
	P_BAT_B,
	P_AC_BP,
	P_BAT_BP,
	P_AC_P
} POWER_STATE;

#define P_ERROR_PROFILE -1
#define P_ERROR_AC -2

#define ac_path "/sys/class/power_supply/ADP0/online"
#define profile_path "/sys/firmware/acpi/platform_profile"

extern POWER_STATE get_powerstate();

#endif // POWERSTATE_H_
