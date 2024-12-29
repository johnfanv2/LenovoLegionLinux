#include "public.h"
#include "modules/parseconf.h"
#include "modules/setapply.h"
#include "modules/powerstate.h"
#include "modules/output.h"

#define BUF_LEN (10 * (sizeof(struct inotify_event) + NAME_MAX + 1))

LEGIOND_CONFIG config;

int delayed = 0;
bool triggered = false;
int fd, client_fd, inotify_fd, maxfd;
fd_set readfds;
char buffer[BUF_LEN], ret[20];
struct inotify_event *event = NULL;

void clear_socket()
{
	if (access(socket_path, F_OK) != -1) {
		remove(socket_path);
	}
}

void term_handler(int signum)
{
	close(fd);
	clear_socket();
	exit(0);
}

void timer_handler()
{
	pretty("config reload start");
	parseconf(&config);
	pretty("config reload end");
	pretty("set_all start");
	set_all(get_powerstate(), &config);

	if (delayed)
		delayed = 0;

	triggered = true;
	pretty("set_all end");
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
	clear_socket();

	parseconf(&config);

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
	fd = socket(AF_UNIX, SOCK_STREAM, 0);
	struct sockaddr_un addr;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, socket_path);

	if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
		exit(1);
	}

	listen(fd, 5);

	// run fancurve-set on startup
	set_timer(&its, delay, 0, timerid);

	// setup SIGTERM handler
	struct sigaction action;
	memset(&action, 0, sizeof(action));
	action.sa_handler = term_handler;
	sigaction(SIGTERM, &action, NULL);

	// inotify power-state/power-profile watcher
	inotify_fd = inotify_init();
	inotify_add_watch(inotify_fd, profile_path, IN_MODIFY);
	inotify_add_watch(inotify_fd, ac_path, IN_MODIFY);

	// listen
	while (1) {
		FD_ZERO(&readfds);
		FD_SET(fd, &readfds);
		FD_SET(inotify_fd, &readfds);

		maxfd = (fd > inotify_fd) ? fd : inotify_fd;

		select(maxfd + 1, &readfds, NULL, NULL, NULL);

		if (FD_ISSET(fd, &readfds)) {
			client_fd = accept(fd, NULL, NULL);
			memset(ret, 0, sizeof(ret));
			recv(client_fd, ret, sizeof(ret), 0);
			printf("cmd: \"%s\" received\n", ret);
			close(client_fd);

			if (ret[0] == 'A') {
				// delayed means user use legiond-ctl fanset with a parameter
				triggered = false;
				if (delayed) {
					printf("extend delay\n");
					set_timer(&its, delayed, 0, timerid);
				} else if (ret[1] == '0') {
					printf("reset timer\n");
					set_timer(&its, delay_s, delay_ns,
						  timerid);
				} else {
					printf("reset timer with delay\n");
					int delay;
					sscanf(ret, "A%d", &delay);
					set_timer(&its, delay, 0, timerid);
					delayed = delay;
				}
			} else if (ret[0] == 'B' && triggered == true) {
				pretty("set_cpu start");
				set_cpu(get_powerstate(), &config);
				pretty("set_cpu end");
			} else if (ret[0] == 'R') {
				pretty("config reload start");
				parseconf(&config);
				set_all(get_powerstate(), &config);
				pretty("config reload end");
			} else {
				printf("do nothing\n");
			}
		}

		if (FD_ISSET(inotify_fd, &readfds)) {
			int lengh = read(inotify_fd, buffer, BUF_LEN);
			char *p = buffer;
			while (p < buffer + lengh) {
				event = (struct inotify_event *)p;
				if (event->mask & IN_MODIFY) {
					pretty("power-state/power-profile change");
					// as we used to use A3 in acpid cfg
					set_timer(&its, 3, 0, timerid);
				}
				p += sizeof(struct inotify_event) + event->len;
			}
		}
	}
}
