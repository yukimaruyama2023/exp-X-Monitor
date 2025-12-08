#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define DEST_ADDR "10.0.0.1" // hamatora
#define DEST_PORT 22222
#define RECV_ADDR "10.0.0.2" // sendai
#define RECV_PORT 22222
// #define NUMMONITORING_BASELINE 120
// #define NUMMONITORING_BASELINE 300
// #define BUFFER_SIZE 6900
#define NUMMONITORING 1000
#define BUFFER_SIZE 6570
// #define BUFFER_SIZE 1500

int main(int argc, char **argv) {
  struct sockaddr_in send_addr, recv_addr;
  int send_sd, recv_sd;
  if (argc == 1) {
    printf("usage: ./manager result_filename");
    return 0;
  }

  float INTERVAL;
  printf("Enter interval (unit is second): ");
  scanf("%f", &INTERVAL);

  memset(&send_addr, 0, sizeof(send_addr));
  send_addr.sin_family = AF_INET;
  inet_aton(DEST_ADDR, &send_addr.sin_addr);
  send_addr.sin_port = htons(DEST_PORT);

  memset(&recv_addr, 0, sizeof(recv_addr));
  recv_addr.sin_family = AF_INET;
  inet_aton(RECV_ADDR, &recv_addr.sin_addr);
  recv_addr.sin_port = htons(RECV_PORT);

  if ((send_sd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
    perror("socket send");
    exit(1);
  }

  if ((recv_sd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
    perror("socket recv");
    exit(1);
  }

  if (bind(recv_sd, (struct sockaddr *)&recv_addr, sizeof(recv_addr)) < 0) {
    perror("bind");
    exit(1);
  }

  if (connect(send_sd, (struct sockaddr *)&send_addr, sizeof(send_addr)) < 0) {
    perror("connect");
    exit(1);
  }

  if (argc != 2)
    puts("Enter result file name");
  FILE *fp = fopen(argv[1], "w");
  char metrics[BUFFER_SIZE];

  // store first data into old_metrics[]
  if (send(send_sd, &metrics, sizeof(metrics), 0) < 0) {
    perror("send");
    exit(1);
  }
  if ((recv(recv_sd, &metrics, sizeof(metrics), 0) < 0)) {
    perror("recv");
    exit(1);
  }

  // declare variables relavant to time
  struct timespec send_time, recv_time;
  struct tm *time;

  // start monitoring for NUMMONITORING times
  for (int i = 0; i < NUMMONITORING; i++) {
    memset(metrics, 0, BUFFER_SIZE);
    // nanosleep(&interval, NULL);
    if (send(send_sd, metrics, BUFFER_SIZE, 0) < 0) {
      perror("send");
      exit(1);
    }

    // timespec_get(&send_time, TIME_UTC);
    clock_gettime(CLOCK_MONOTONIC, &send_time);

    if (recv(recv_sd, metrics, BUFFER_SIZE, 0) < 0) {
      perror("recv");
      exit(1);
    }

    // timespec_get(&recv_time, TIME_UTC);
    clock_gettime(CLOCK_MONOTONIC, &recv_time);

    // time = localtime(&recv_time.tv_sec);
    struct timespec wall_time;
    clock_gettime(CLOCK_REALTIME, &wall_time);
    time = localtime(&wall_time.tv_sec);

    long sec_diff = recv_time.tv_sec - send_time.tv_sec;
    long nsec_diff = recv_time.tv_nsec - send_time.tv_nsec;

    if (nsec_diff < 0) {
      sec_diff -= 1;
      nsec_diff += 1000000000L; // 1s to nano second
    }
    // double elapsed_time = sec_diff * 1000000.0 + nsec_diff / 1000.0;

    long elapsed_us = (recv_time.tv_sec - send_time.tv_sec) * 1000000L +
                        (recv_time.tv_nsec - send_time.tv_nsec) / 1000L;

    double elapsed_time = (double)elapsed_us;

    long target_us = (long)(INTERVAL * 1000000L);
    long remaining_us = target_us - elapsed_us;

    if (remaining_us > 0) {
        struct timespec req;
        req.tv_sec  = remaining_us / 1000000L;
        req.tv_nsec = (remaining_us % 1000000L) * 1000L;

        nanosleep(&req, NULL);
    }

    fprintf(fp, "%d/%02d/%02d-%02d:%02d:%02d.%06ld,", time->tm_year + 1900,
            time->tm_mon + 1, time->tm_mday, time->tm_hour, time->tm_min,
            time->tm_sec, wall_time.tv_nsec / 1000);

    fprintf(fp, "%ld.%09ld,%.2f\n", send_time.tv_sec, send_time.tv_nsec,
            elapsed_time);

    if (i % (int)(10 / INTERVAL) == 0) {
      printf("message[%d] is sent\n", i);
    }
  }

  close(send_sd);
  close(recv_sd);
  fclose(fp);

  return 0;
}
