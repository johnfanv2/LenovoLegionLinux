#include "public.h"
#include "modules/output.h"
#include "modules/parseconf.h"
#include "modules/powerstate.h"
#include "modules/setapply.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>

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

/*
 * Serializes access to config/delayed/triggered between the SIGEV_THREAD
 * timer thread and the main loop (socket commands).  It also serializes
 * hardware writes (set_all/set_cpu), which must never run concurrently.
 */
static pthread_mutex_t state_lock = PTHREAD_MUTEX_INITIALIZER;

static volatile sig_atomic_t terminate_requested;
static int signal_pipe[2] = { -1, -1 };

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
 * Async-signal-safe.  Only writes to the self-pipe and sets a flag; real
 * cleanup happens when the main loop observes the pipe and returns.
 */
static void term_handler([[maybe_unused]] int signum)
{
	int saved_errno = errno;
	ssize_t ignored = write(signal_pipe[1], "", 1);
	(void)ignored;
	errno = saved_errno;
	terminate_requested = 1;
}

static void timer_handler([[maybe_unused]] union sigval sigev_value)
{
	pretty("config reload start");
	pthread_mutex_lock(&state_lock);
	parseconf(&config);
	pretty("config reload end");
	pretty("set_all start");
	set_all(get_powerstate(), &config);

	if (delayed)
		delayed = 0;

	triggered = true;
	pretty("set_all end");
	pthread_mutex_unlock(&state_lock);
}

static void set_timer(long delay_s, long delay_ns)
{
	struct itimerspec its = {
		.it_value = { .tv_sec = delay_s, .tv_nsec = delay_ns },
		.it_interval = { 0 },
	};
	timer_settime(timerid, 0, &its, NULL);
}

/*
 * Reads one fixed-size request without blocking forever when a client
 * connects but stalls mid-transfer.  Caps the wait at a total of 5 s.
 */
static int recv_request(int fd, LEGIOND_REQUEST *request)
{
	size_t received = 0;
	struct timespec deadline;
	if (clock_gettime(CLOCK_MONOTONIC, &deadline) != -1)
		deadline.tv_sec += 5;

	while (received < sizeof(*request)) {
		struct timespec now;
		if (clock_gettime(CLOCK_MONOTONIC, &now) != -1 &&
		    (now.tv_sec > deadline.tv_sec ||
		     (now.tv_sec == deadline.tv_sec && now.tv_nsec > deadline.tv_nsec)))
			return -1;

		struct pollfd pfd = { .fd = fd, .events = POLLIN };
		int ready = poll(&pfd, 1, 2000);
		if (ready == -1 && errno == EINTR)
			continue;
		if (ready <= 0)
			return -1;

		ssize_t n = recv(fd, (char *)request + received,
				 sizeof(*request) - received, 0);
		if (n <= 0)
			return -1;
		received += (size_t)n;
	}
	return 0;
}

static void handle_command(const LEGIOND_REQUEST *request)
{
	pthread_mutex_lock(&state_lock);
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
	pthread_mutex_unlock(&state_lock);
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

	// self-pipe to wake the select loop from the signal handler
	if (pipe(signal_pipe) == -1) {
		perror("pipe");
		return 1;
	}
	for (int i = 0; i < 2; i++) {
		int flags = fcntl(signal_pipe[i], F_GETFL, 0);
		if (flags == -1 || fcntl(signal_pipe[i], F_SETFL, flags | O_NONBLOCK) == -1) {
			perror("fcntl");
			return 1;
		}
	}

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
	while (!terminate_requested) {
		fd_set readfds;
		FD_ZERO(&readfds);
		FD_SET(server_fd, &readfds);
		FD_SET(inotify_fd, &readfds);
		FD_SET(signal_pipe[0], &readfds);

		int maxfd = max_fd(server_fd, inotify_fd);
		maxfd = max_fd(maxfd, signal_pipe[0]);

		if (select(maxfd + 1, &readfds, NULL, NULL, NULL) == -1) {
			if (terminate_requested || errno == EINTR)
				continue;
			perror("select");
			break;
		}

		if (FD_ISSET(signal_pipe[0], &readfds)) {
			char discard[64];
			while (read(signal_pipe[0], discard, sizeof(discard)) > 0) {
			}
			break;
		}

		if (FD_ISSET(server_fd, &readfds)) {
			auto_fd client_fd = accept(server_fd, NULL, NULL);
			if (client_fd == -1)
				continue;

			LEGIOND_REQUEST request = { 0 };
			if (recv_request(client_fd, &request) != 0) {
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
