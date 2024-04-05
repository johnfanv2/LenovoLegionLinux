#ifndef SETAPPLY_H_
#define SETAPPLY_H_
#include "parseconf.h"
#include "powerstate.h"

extern int set_fancurve(POWER_STATE power_state, LEGIOND_CONFIG *config);
extern int set_cpu(POWER_STATE power_state, LEGIOND_CONFIG *config);
extern int set_gpu(POWER_STATE power_state, LEGIOND_CONFIG *config);
extern int set_all(POWER_STATE power_state, LEGIOND_CONFIG *config);

#endif // SETAPPLY_H_
