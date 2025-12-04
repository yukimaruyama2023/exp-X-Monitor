// redis_info_sender.c
// Send "INFO" to Redis ports 6379–6390 with adjustable interval.

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
#define BASE_PORT 6379
#define LAST_PORT 6390
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

/*
 * Redis INFO reply (通常の INFO コマンド) は RESP Bulk String:
 *   $<len>\r\n
 *   <payload (len bytes)>\r\n
 * という形式なので、
 * 1. 先頭行 "$<len>\r\n" を読み取って長さをパース
 * 2. payload (<len> byte) + 最後の "\r\n" を捨てる
 */
static int drain_info_reply(int fd) {
  char line[64];
  size_t line_len = 0;
  char c;
  ssize_t n;

  // 1) "$<len>\r\n" の行を読む
  for (;;) {
    n = recv(fd, &c, 1, 0);
    if (n == 0)
      return -1; // peer closed
    if (n < 0) {
      if (errno == EINTR)
        continue;
      return -1;
    }

    if (c == '\n') {
      // 行終端
      if (line_len >= sizeof(line))
        return -1;
      line[line_len] = '\0';
      break;
    }

    if (line_len < sizeof(line) - 1) {
      line[line_len++] = c;
    } else {
      // 行が長すぎる
      return -1;
    }
  }

  // line は "$<len>\r" のはず
  if (line_len < 2 || line[0] != '$')
    return -1;

  char *endptr = NULL;
  long payload_len = strtol(line + 1, &endptr, 10);
  if (endptr == line + 1 || payload_len < 0)
    return -1;

  // 2) payload_len bytes + 終端の "\r\n" を読み捨てる
  long to_read = payload_len + 2;
  char buf[4096];

  while (to_read > 0) {
    size_t chunk =
        (to_read < (long)sizeof(buf)) ? (size_t)to_read : sizeof(buf);
    n = recv(fd, buf, chunk, 0);
    if (n == 0)
      return -1;
    if (n < 0) {
      if (errno == EINTR)
        continue;
      return -1;
    }
    to_read -= n;
  }

  return 0;
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
    fprintf(stderr, "Usage: %s <num_redis> <interval_sec>\n", argv[0]);
    exit(1);
  }

  // --- 1. num_redis を取得 ---
  int num_ports = atoi(argv[1]);
  if (num_ports <= 0 || num_ports > NUM_PORTS) {
    fprintf(stderr, "num_redis must be in the range 1..%d (got %d)\n",
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
  for (int i = 0; i < NUM_PORTS; i++)
    fds[i] = -1;

  const char *req = "INFO\r\n";
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

    // --- 2. recv from all ports (INFO 応答を取り切る) ---
    for (int i = 0; i < num_ports; i++) {
      if (fds[i] < 0)
        continue;

      if (drain_info_reply(fds[i]) < 0) {
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
