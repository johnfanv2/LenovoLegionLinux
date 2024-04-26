#include "output.h"
#include <string.h>
#include <stdio.h>

void pretty(char *msg)
{
	int len = strlen(msg);
	len = len > 30 ? len : 30;
	printf("\033[1m");
	for (int i = 0; i < len / 2; i++) {
		putchar('-');
	}
	printf("%s", msg);
	for (int i = 0; i < len / 2; i++) {
		putchar('-');
	}
	printf("\033[m");

	putchar('\n');
}
