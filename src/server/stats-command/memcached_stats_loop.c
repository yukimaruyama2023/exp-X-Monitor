// stats_sender.c
// Send "stats" to memcached ports 11211–11222 with adjustable interval.

#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <math.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define IP_ADDR "127.0.0.1"
#define BASE_PORT 11211
#define LAST_PORT 11222
#define NUM_PORTS (LAST_PORT - BASE_PORT + 1)

static volatile sig_atomic_t g_stop = 0;

static void on_sigint(int sig) {
  (void)sig;
  g_stop = 1;
}

static int connect_port(int port) {
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0)
    return -1;

  struct sockaddr_in addr = {.sin_family = AF_INET,
                             .sin_port = htons((uint16_t)port)};
  inet_pton(AF_INET, IP_ADDR, &addr.sin_addr);

  if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
    close(fd);
    return -1;
  }
  return fd;
}

// read until END\r\n
static int drain_until_end(int fd) {
  char buf[4096];
  char window[8] = {0};
  size_t wlen = 0;

  for (;;) {
    ssize_t n = recv(fd, buf, sizeof(buf), 0);
    if (n == 0)
      return -1; // peer closed
    if (n < 0) {
      if (errno == EINTR)
        continue;
      return -1;
    }
    for (ssize_t i = 0; i < n; i++) {
      if (wlen < sizeof(window))
        window[wlen++] = buf[i];
      else {
        memmove(window, window + 1, sizeof(window) - 1);
        window[sizeof(window) - 1] = buf[i];
      }
      if (wlen >= 5 && window[wlen - 5] == 'E' && window[wlen - 4] == 'N' &&
          window[wlen - 3] == 'D' && window[wlen - 2] == '\r' &&
          window[wlen - 1] == '\n')
        return 0;
    }
  }
}

static int send_all(int fd, const char *msg, size_t len) {
  size_t off = 0;
  while (off < len) {
    ssize_t n = send(fd, msg + off, len - off, 0);
    if (n < 0) {
      if (errno == EINTR)
        continue;
      return -1;
    }
    off += n;
  }
  return 0;
}

static void add_interval(struct timespec *ts, double interval) {
  ts->tv_sec += (time_t)interval;
  double frac = interval - floor(interval);
  long nsec = (long)(frac * 1e9);
  ts->tv_nsec += nsec;

  if (ts->tv_nsec >= 1000000000L) {
    ts->tv_sec += 1;
    ts->tv_nsec -= 1000000000L;
  }
}

int main(int argc, char *argv[]) {
  if (argc != 3) {
    fprintf(stderr, "Usage: %s <num_memcached> <interval_sec>\n", argv[0]);
    exit(1);
  }

  // --- 1. num_memcached を取得 ---
  int num_ports = atoi(argv[1]);
  if (num_ports <= 0 || num_ports > NUM_PORTS) {
    fprintf(stderr, "num_memcached must be in the range 1..%d (got %d)\n",
            NUM_PORTS, num_ports);
    exit(1);
  }

  // --- 2. interval を取得 ---
  double interval = atof(argv[2]);
  if (interval <= 0) {
    fprintf(stderr, "interval must be > 0\n");
    exit(1);
  }

  signal(SIGINT, on_sigint);
  signal(SIGTERM, on_sigint);

  int fds[NUM_PORTS];
  memset(fds, -1, sizeof(fds));

  const char *req = "stats\r\n";
  size_t req_len = strlen(req);

  struct timespec next;
  clock_gettime(CLOCK_MONOTONIC, &next);
  add_interval(&next, interval);

  while (!g_stop) {
    // --- 1. send to all ports (0 .. num_ports-1) ---
    for (int i = 0; i < num_ports; i++) {
      int port = BASE_PORT + i;

      if (fds[i] < 0) {
        fds[i] = connect_port(port);
        if (fds[i] < 0) {
          printf("failed to connect to port %d\n", port);
          continue; // connect 失敗時はスキップ
        }
      }

      if (send_all(fds[i], req, req_len) < 0) {
        close(fds[i]);
        fds[i] = -1;
        continue;
      }
    }

    // --- 2. recv from all ports until END\r\n ---
    for (int i = 0; i < num_ports; i++) {
      if (fds[i] < 0)
        continue;

      if (drain_until_end(fds[i]) < 0) {
        close(fds[i]);
        fds[i] = -1;
        continue;
      }
    }

    // --- 3. wait until interval ---
    int rc;
    do {
      rc = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);
    } while (rc == EINTR && !g_stop);

    add_interval(&next, interval);
  }

  for (int i = 0; i < num_ports; i++) {
    if (fds[i] >= 0)
      close(fds[i]);
  }
  return 0;
}
