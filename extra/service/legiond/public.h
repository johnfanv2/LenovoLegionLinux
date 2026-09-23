#ifndef PUBLIC_H_
#define PUBLIC_H_

#include <limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/inotify.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

/*
 * The whole daemon is built around GCC's/Clang's cleanup attribute for
 * automatic resource management.  Both compilers implement it; guard the
 * spelling so an unsupported compiler fails loudly instead of silently
 * leaking resources.
 */
#ifdef __clang__
#define legiond_cleanup(fn) __attribute__((cleanup(fn)))
#elifdef __GNUC__
#define legiond_cleanup(fn) __attribute__((cleanup(fn)))
#else
#error "legiond requires GCC or Clang with __attribute__((cleanup)) support"
#endif

/* close(2) a file descriptor held by an auto_fd variable. */
static inline void close_fd(int *fd)
{
	if (*fd >= 0)
		close(*fd);
	*fd = -1;
}

/* fclose(3) a stream held by an auto_stream variable. */
static inline void close_stream(FILE **stream)
{
	if (*stream)
		fclose(*stream);
	*stream = NULL;
}

/* free(3) a heap buffer held by an auto_free variable. */
static inline void free_buffer(void *buffer)
{
	free(*(void **)buffer);
}

#define auto_fd legiond_cleanup(close_fd) int
#define auto_stream legiond_cleanup(close_stream) FILE *
#define auto_free legiond_cleanup(free_buffer)

#define socket_path "/run/legiond.socket"
#define default_delay 1.5

/*
 * Wire protocol between legiond-ctl and legiond: exactly one fixed-size
 * binary legiond_request per connection over the unix socket.
 *
 * Defined once here so both sides can never drift apart.  The magic
 * doubles as a protocol version marker: peers speaking another protocol
 * (e.g. the old single-byte text protocol) are rejected instead of
 * being misinterpreted.
 */
#define protocol_magic 0x4C47'4E31 /* "LGN1" */

typedef enum _LEGIOND_CMD {
	CMD_FANSET = 0,
	CMD_CPUSET,
	CMD_RELOAD,
} LEGIOND_CMD;

typedef struct _LEGIOND_REQUEST {
	uint32_t magic; /* protocol_magic */
	uint32_t cmd; /* LEGIOND_CMD */
	int32_t delay_s; /* CMD_FANSET only: 0 resets the timer */
} LEGIOND_REQUEST;

/* human-readable name for a protocol command */
static inline const char *cmd_name(uint32_t cmd)
{
	switch (cmd) {
	case CMD_FANSET:
		return "fanset";
	case CMD_CPUSET:
		return "cpuset";
	case CMD_RELOAD:
		return "reload";
	default:
		return "unknown";
	}
}

#endif // PUBLIC_H_
