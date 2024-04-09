#include "public.h"

int main(int argc, char *argv[])
{
	if (getuid() != 0){
		printf("require root privileges\n");
		exit(3);
	}

	if (access(socket_path, F_OK) == -1) {
		printf("socket not found\n");
		exit(1);
	}

	char request[20] = "";

	if (argc > 1) {
		if (strcmp(argv[1], "fanset") == 0) {
			sprintf(request, "A0"); // A means fanset
			// 0 means reset
			if (argc > 2) {
				int delay;
				sscanf(argv[2], "%d", &delay);
				// for example "A3" means 3 seconds delay
				sprintf(request, "A%d", delay);
			}
		} else if (strcmp(argv[1], "cpuset") == 0) {
			sprintf(request, "B"); // B means cpuset
		} else if (strcmp(argv[1], "reload") == 0) {
			sprintf(request, "R"); // R means reload config
		} else {
			printf("unknown arguments\n");
			exit(1);
		}
	}

	// init socket
	int fd = socket(AF_UNIX, SOCK_STREAM, 0);
	struct sockaddr_un addr;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, socket_path);

	if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
		exit(2);
	}

	if (send(fd, request, strlen(request), 0) != -1) {
		printf("successfully sent cmd\n");
	}

	close(fd);
}
