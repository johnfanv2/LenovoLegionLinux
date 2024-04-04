#ifndef SETAPPLY_H_
#define SETAPPLY_H_
#include "parseconf.h"

extern int set_fancurve(int power_state, LEGIOND_CONFIG *config);
extern int set_cpu(int power_state, LEGIOND_CONFIG *config);
extern int set_gpu(int power_state, LEGIOND_CONFIG *config);
extern int set_all(int power_state, LEGIOND_CONFIG *config);

#endif // SETAPPLY_H_
