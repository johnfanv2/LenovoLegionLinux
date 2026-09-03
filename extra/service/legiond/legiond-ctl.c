#include "public.h"

static const struct {
	const char *name;
	LEGIOND_CMD cmd;
	bool takes_delay;
} commands[] = {
	{ "fanset", CMD_FANSET, true },
	{ "cpuset", CMD_CPUSET, false },
	{ "reload", CMD_RELOAD, false },
};

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))

int main(int argc, char *argv[])
{
	if (getuid() != 0) {
		printf("require root privileges\n");
		return 3;
	}

	if (access(socket_path, F_OK) == -1) {
		printf("socket not found\n");
		return 1;
	}

	LEGIOND_REQUEST request = {
		.magic = protocol_magic,
		.cmd = 0,
		.delay_s = 0,
	};

	if (argc > 1) {
		const typeof(commands[0]) *command = NULL;
		for (size_t i = 0; i < ARRAY_SIZE(commands); i++) {
			if (strcmp(argv[1], commands[i].name) == 0) {
				command = &commands[i];
				break;
			}
		}

		if (command == NULL) {
			printf("unknown arguments\n");
			return 1;
		}

		request.cmd = command->cmd;
		if (command->takes_delay && argc > 2) {
			// for example "legiond-ctl fanset 3" means 3 seconds delay
			if (sscanf(argv[2], "%d", &request.delay_s) != 1)
				request.delay_s = 0;
		}
	}

	// init socket
	auto_fd fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (fd == -1)
		return 2;

	struct sockaddr_un addr = {
		.sun_family = AF_UNIX,
	};
	if (snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", socket_path) >=
	    (int)sizeof(addr.sun_path))
		return 2;

	if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) == -1)
		return 2;

	if (send(fd, &request, sizeof(request), 0) != -1)
		printf("successfully sent cmd\n");

	return 0;
}
