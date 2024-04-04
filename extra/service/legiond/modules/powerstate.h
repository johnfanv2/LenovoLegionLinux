#ifndef POWERSTATE_H_
#define POWERSTATE_H_

#define P_AC_Q 0
#define P_BAT_Q 1
#define P_AC_B 2
#define P_BAT_B 3
#define P_AC_BP 4
#define P_BAT_BP 5
#define P_AC_P 6

#define ac_path "/sys/class/power_supply/ADP0/online"
#define profile_path "/sys/firmware/acpi/platform_profile"

extern int get_powerstate();

#endif // POWERSTATE_H_
