#include "output.h"
#include <stdio.h>
#include <string.h>

void pretty(const char *msg)
{
	size_t len = strlen(msg);
	size_t width = len > 30 ? len : 30;

	printf("\033[1m");
	for (size_t i = 0; i < width / 2; i++)
		putchar('-');
	printf("%s", msg);
	for (size_t i = 0; i < width / 2; i++)
		putchar('-');
	printf("\033[m");

	putchar('\n');
}
