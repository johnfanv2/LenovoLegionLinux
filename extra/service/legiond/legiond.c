#include "public.h"

int delayed = 0;

void timer_handler()
{
	int result = system("/usr/bin/fancurve-set");
	if (result == -1) {
		printf("failed to start fancurve-set\n");
	} else {
		printf("fancurve-set started\n");
	}
	if (delayed)
		delayed = 0;
}

void set_timer(struct itimerspec *its, long delay_s, long delay_ns,
	       timer_t timerid)
{
	its->it_value.tv_sec = delay_s;
	its->it_value.tv_nsec = delay_ns;
	its->it_interval.tv_sec = 0;
	its->it_interval.tv_nsec = 0;
	timer_settime(timerid, 0, its, NULL);
}

int main()
{
	// remove socket before create it
	if (access(socket_path, F_OK) != -1) {
		remove(socket_path);
	}

	// calculate delay
	long delay_s = (int)delay;
	long delay_ns = (int)((delay - (int)delay) * 1000000000);

	// not blocking output
	setbuf(stdout, NULL);

	// init timer
	timer_t timerid;
	struct itimerspec its;

	struct sigevent sev;
	sev.sigev_notify = SIGEV_THREAD;
	sev.sigev_notify_function = timer_handler;
	sev.sigev_value.sival_ptr = &timerid;
	sev.sigev_notify_attributes = NULL;

	timer_create(CLOCK_REALTIME, &sev, &timerid);

	// init socket
	int fd = socket(AF_UNIX, SOCK_STREAM, 0);
	struct sockaddr_un addr;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, socket_path);
	int ret = bind(fd, (struct sockaddr *)&addr, sizeof(addr));

	if (ret == -1) {
		exit(1);
	}

	listen(fd, 5);

	// run fancurve-set on startup
	set_timer(&its, delay, 0, timerid);

	// listen
	while (1) {
		int clientfd = accept(fd, NULL, NULL);
		char ret[20];
		memset(ret, 0, sizeof(ret));
		recv(clientfd, ret, sizeof(ret), 0);
		printf("cmd: \"%s\" received\n", ret);
		if (ret[0] == 'A') {
			// delayed means user use legiond-cli fanset with a parameter
			if (delayed) {
				printf("extend delay\n");
				set_timer(&its, delayed, 0, timerid);
			} else if (ret[1] == '0') {
				printf("reset timer\n");
				set_timer(&its, delay_s, delay_ns, timerid);
			} else {
				printf("reset timer with delay\n");
				int delay;
				sscanf(ret, "A%d", &delay);
				set_timer(&its, delay, 0, timerid);
				delayed = delay;
			}
		} else {
			printf("do nothing\n");
		}
		close(clientfd);
	}

	close(fd);
	exit(0);
}
