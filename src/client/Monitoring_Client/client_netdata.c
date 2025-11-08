#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define BUF_SIZE 256
#define DEST_ADDR "10.0.0.1" // hamatora
#define DEST_PORT 19999
#define RECV_ADDR "10.0.0.2" // sendai
#define RECV_PORT 22224
#define RES_LEN 60000
// #define NUMMONITORING_BASELINE 60
#define NUMMONITORING_BASELINE 300
#define NUMMONITORING_BASELINE 60

char res[RES_LEN];

const char *request_system =
    "GET /api/v1/allmetrics?format=shell&filter=system.* HTTP/1.1\r\n"
    "Host: " DEST_ADDR ":19999\r\n"
    "\r\n";
const char *request_user =
    "GET /api/v1/allmetrics?format=shell&filter=memcached.* HTTP/1.1\r\n"
    "Host: " DEST_ADDR ":19999\r\n"
    "\r\n";

int main(int argc, char **argv) {
  if (argc == 1) {
    printf("usage: ./manager result_filename\n");
    return 0;
  }
  float INTERVAL;
  int NUMMONITORING;
  printf("Enter interval (unit is second): ");
  scanf("%f", &INTERVAL);
  NUMMONITORING = NUMMONITORING_BASELINE / INTERVAL;

  int metrics;
  printf("Enter 0 or 1 which represent system metrics, user metrics "
         "respectively: ");
  scanf("%d", &metrics);

  const char *request;
  if (metrics == 0) {
    request = request_system;
  } else if (metrics == 1) {
    request = request_user;
  } else {
    puts("Error: specify 0 or 1");
    exit(1);
  }

  struct sockaddr_in send_addr;
  int sd;
  char recv_buf[BUF_SIZE];

  memset(&send_addr, 0, sizeof(send_addr));
  send_addr.sin_family = AF_INET;
  inet_aton(DEST_ADDR, &send_addr.sin_addr);
  send_addr.sin_port = htons(DEST_PORT);

  if ((sd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
    perror("socket");
    exit(1);
  }

  if (connect(sd, (struct sockaddr *)&send_addr, sizeof(send_addr)) < 0) {
    perror("connect");
    exit(1);
  }
  struct timespec send_time, recv_time;
  struct timespec interval;
  if (INTERVAL == 1) {
    interval.tv_sec = INTERVAL;
    interval.tv_nsec = 0;
  } else {
    interval.tv_sec = 0;
    interval.tv_nsec = INTERVAL * 1000000000;
  }
  struct tm *time;
  FILE *fp = fopen(argv[1], "w");
  if (send(sd, request, strlen(request), 0) < 0) {
    perror("send");
    exit(1);
  }

  if (recv(sd, res, RES_LEN, 0) < 0) {
    perror("recv");
    exit(1);
  }
  // printf("%s", res);

  // close(sd);
  for (int i = 0; i < NUMMONITORING; ++i) {
    nanosleep(&interval, NULL);
    // printf("i: %d\n", i);
    if ((sd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
      perror("socket");
      exit(1);
    }

    if (connect(sd, (struct sockaddr *)&send_addr, sizeof(send_addr)) < 0) {
      perror("connect");
      exit(1);
    }
    if (send(sd, request, strlen(request), 0) < 0) {
      perror("send");
      exit(1);
    }
    timespec_get(&send_time, TIME_UTC);

    if (recv(sd, res, RES_LEN, 0) < 0) {
      perror("recv");
      exit(1);
    }
    timespec_get(&recv_time, TIME_UTC);
    time = localtime(&recv_time.tv_sec);
    // printf("%ld.%ld,%09ld: ", send_time.tv_sec, send_time.tv_nsec,
    // (recv_time.tv_sec - send_time.tv_sec) * 1000000000 + recv_time.tv_nsec -
    // send_time.tv_nsec); for (int i = 0; i < NSTATS; ++i) {
    //     printf("%ld ", metric[i]);
    // }
    // printf("\n");

    /*the unit of elapsed time is micro second*/
    long elapsed_time = (recv_time.tv_sec - send_time.tv_sec) * 1000000L +
                        (recv_time.tv_nsec - send_time.tv_nsec) / 1000L;

    fprintf(fp, "%d/%02d/%02d-%02d:%02d:%02d.%ld,%ld.%09ld,%ld\n",
            time->tm_year + 1900, time->tm_mon + 1, time->tm_mday,
            time->tm_hour, time->tm_min, time->tm_sec, recv_time.tv_nsec / 1000,
            send_time.tv_sec, send_time.tv_nsec, elapsed_time);
    // print_metrics(fp, res);
    // printf("%s", res);

    if (i % (int)(10 / INTERVAL) == 0) {
      printf("message[%d] is sent\n", i);
    }
    close(sd);
  }

  close(sd);
  fclose(fp);

  return 0;
}
