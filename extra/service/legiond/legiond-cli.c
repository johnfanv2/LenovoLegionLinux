#include "public.h"

int main(int argc, char *argv[])
{
  // init socket
	int fd = socket(AF_UNIX, SOCK_STREAM, 0);
	struct sockaddr_un addr;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, socket_path);
	int ret = connect(fd, (struct sockaddr *)&addr, sizeof(addr));
	if (ret == -1) {
		exit(-1);
	}
	char request[20] = "";

	if (argc > 1)
		if (strcmp(argv[1], "fanset") == 0) {
			sprintf(request, "A0"); // A means fanset
			// 0 means reset
			if (argc > 2) {
				int delay;
				sscanf(argv[2], "%d", &delay);
        // for example "A3" means 3 seconds delay
				sprintf(request, "A%d", delay);
			}
		};
	send(fd, request, strlen(request), 0);
	close(fd);
}
