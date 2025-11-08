#pragma once

#include <stdint.h>

typedef struct {
    uint64_t write_nsec;
} DiskStat;

typedef struct {
} CpuStat;

/* typedef struct { */
/* } MemStat; */
/* typedef struct { */
/* } NetStat; */

typedef struct {
    /* DiskStat disk_stat; */
    CpuStat cpu_stat;
    /* MemStat mem_stat; */
    /* NetStat net_stat; */
} Statistics;

#define BUF_SIZE 256

enum stat_id {
    /* DISK_WRITE_NSEC, */
    CPUTIME_USER,
    CPUTIME_NICE,
    CPUTIME_SYSTEM,
    CPUTIME_IDLE,
    CPUTIME_IOWAIT,
    CPUTIME_IRQ,
    CPUTIME_SOFTIRQ,
    CPUTIME_STEAL,
    CPUTIME_GUEST,
    CPUTIME_GUEST_NICE,
    /* MEM_FREE_PAGE, */
    /* NET_IP_IN_RECV, */
    /* NET_IP_IN_HDR_ERRORS, */
    /* NET_IP_ADDR_ERRORS, */
    NSTATS
};
