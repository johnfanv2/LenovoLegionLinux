#ifndef SETAPPLY_H_
#define SETAPPLY_H_
#include "parseconf.h"
#include "powerstate.h"

int set_fancurve(POWER_STATE power_state, LEGIOND_CONFIG *config);
int set_cpu(POWER_STATE power_state, LEGIOND_CONFIG *config);
int set_gpu(POWER_STATE power_state, LEGIOND_CONFIG *config);
int set_all(POWER_STATE power_state, LEGIOND_CONFIG *config);

#endif // SETAPPLY_H_
