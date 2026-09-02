#include "public.h"
#include "modules/output.h"
#include "modules/parseconf.h"
#include "modules/powerstate.h"
#include "modules/setapply.h"

#define events_max 10
#define BUF_LEN (events_max * (sizeof(struct inotify_event) + NAME_MAX + 1))

/* type-safe maximum for the select(2) fd set */
#define max_fd(a, b)                \
	({                          \
		typeof(a) _a = (a); \
		typeof(b) _b = (b); \
		_a > _b ? _a : _b;  \
	})

static LEGIOND_CONFIG config;
static int delayed; /* user supplied fanset delay in seconds, 0 = none */
static bool triggered; /* set_all has run since the last fanset command */
static int server_fd = -1;
static timer_t timerid;
static long delay_s_default;
static long delay_ns_default;

static void clear_socket(void)
{
	if (access(socket_path, F_OK) != -1)
		remove(socket_path);
}

/* registered via atexit(): unlinks the socket on SIGTERM and normal exit */
static void cleanup_socket(void)
{
	if (server_fd >= 0)
		close(server_fd);
	clear_socket();
}

/*
 * GCC 12's C frontend parses plain [[noreturn]] but warns that it is
 * ignored, so use the GNU-namespaced spelling which both compilers honor.
 */
[[gnu::noreturn]] static void term_handler([[maybe_unused]] int signum)
{
	/* cleanup_socket() runs through atexit() */
	exit(0);
}

static void timer_handler([[maybe_unused]] union sigval sigev_value)
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

static void set_timer(long delay_s, long delay_ns)
{
	struct itimerspec its = {
		.it_value = { .tv_sec = delay_s, .tv_nsec = delay_ns },
		.it_interval = { 0 },
	};
	timer_settime(timerid, 0, &its, NULL);
}

static void handle_command(const LEGIOND_REQUEST *request)
{
	switch (request->cmd) {
	case CMD_FANSET:
		// delayed means user use legiond-ctl fanset with a parameter
		triggered = false;
		if (delayed) {
			printf("extend delay\n");
			set_timer(delayed, 0);
		} else if (request->delay_s == 0) {
			printf("reset timer\n");
			set_timer(delay_s_default, delay_ns_default);
		} else {
			printf("reset timer with delay %d s\n",
			       request->delay_s);
			set_timer(request->delay_s, 0);
			delayed = request->delay_s;
		}
		break;
	case CMD_CPUSET:
		if (triggered == true) {
			pretty("set_cpu start");
			int result = set_cpu(get_powerstate(), &config);
			if (result != 0)
				printf("set_cpu failed: %d\n", result);
			pretty("set_cpu end");
		} else {
			printf("do nothing\n");
		}
		break;
	case CMD_RELOAD:
		pretty("config reload start");
		parseconf(&config);
		set_all(get_powerstate(), &config);
		pretty("config reload end");
		break;
	default:
		printf("do nothing\n");
		break;
	}
}

int main(void)
{
	// remove socket before create it
	clear_socket();

	parseconf(&config);

	// calculate delay
	delay_s_default = (long)default_delay;
	delay_ns_default =
		(long)((default_delay - delay_s_default) * 1'000'000'000);

	// not blocking output
	setbuf(stdout, NULL);

	// init timer
	struct sigevent sev = {
		.sigev_notify = SIGEV_THREAD,
		.sigev_notify_function = timer_handler,
		.sigev_value = { .sival_ptr = &timerid },
		.sigev_notify_attributes = NULL,
	};

	if (timer_create(CLOCK_REALTIME, &sev, &timerid) == -1) {
		perror("timer_create");
		return 1;
	}

	if (atexit(cleanup_socket) != 0) {
		fprintf(stderr, "failed to register socket cleanup\n");
		return 1;
	}

	// init socket
	server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (server_fd == -1) {
		perror("socket");
		return 1;
	}

	struct sockaddr_un addr = {
		.sun_family = AF_UNIX,
	};
	if (snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", socket_path) >=
	    (int)sizeof(addr.sun_path)) {
		fprintf(stderr, "socket path too long\n");
		return 1;
	}

	if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
		return 1;
	}

	if (listen(server_fd, 5) == -1) {
		perror("listen");
		return 1;
	}

	// run fancurve-set on startup
	set_timer(delay_s_default, delay_ns_default);

	// setup SIGTERM handler
	struct sigaction action = {
		.sa_handler = term_handler,
	};
	sigaction(SIGTERM, &action, NULL);

	// inotify power-state/power-profile watcher
	auto_fd inotify_fd = inotify_init();
	if (inotify_fd == -1) {
		perror("inotify_init");
		return 1;
	}
	inotify_add_watch(inotify_fd, profile_path, IN_MODIFY);
	inotify_add_watch(inotify_fd, ac_path, IN_MODIFY);

	auto_free char *buffer = malloc(BUF_LEN);
	if (buffer == NULL) {
		perror("malloc");
		return 1;
	}

	// listen
	while (true) {
		fd_set readfds;
		FD_ZERO(&readfds);
		FD_SET(server_fd, &readfds);
		FD_SET(inotify_fd, &readfds);

		int maxfd = max_fd(server_fd, inotify_fd);

		if (select(maxfd + 1, &readfds, NULL, NULL, NULL) == -1)
			continue;

		if (FD_ISSET(server_fd, &readfds)) {
			auto_fd client_fd = accept(server_fd, NULL, NULL);
			if (client_fd == -1)
				continue;

			LEGIOND_REQUEST request = { 0 };
			ssize_t received = recv(client_fd, &request,
						sizeof(request), MSG_WAITALL);
			if (received != (ssize_t)sizeof(request)) {
				printf("ignoring malformed request\n");
				continue;
			}
			if (request.magic != protocol_magic) {
				printf("ignoring request with bad magic\n");
				continue;
			}

			printf("cmd: %s received\n", cmd_name(request.cmd));
			handle_command(&request);
		}

		if (FD_ISSET(inotify_fd, &readfds)) {
			ssize_t length = read(inotify_fd, buffer, BUF_LEN);
			if (length <= 0)
				continue;

			char *p = buffer;
			while (p < buffer + length) {
				struct inotify_event *event =
					(struct inotify_event *)p;
				if (event->mask & IN_MODIFY) {
					pretty("power-state/power-profile change");
					// as we used to use A3 in acpid cfg
					set_timer(3, 0);
				}
				p += sizeof(struct inotify_event) + event->len;
			}
		}
	}
}
