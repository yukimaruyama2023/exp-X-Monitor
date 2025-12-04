#include <bits/types.h>
#include <stddef.h>
#include <stdint.h>
#include <time.h>
#define STATS_METRIC_COUNT 7

typedef __off_t off_t;
typedef __sig_atomic_t sig_atomic_t;
typedef uint64_t monotime;

struct redisServer {
  /* metrics */
  /* -----------------------------------------------------------------------------------------------
   */
  /* # Server */
  int arch_bits; /* 32 or 64 depending on sizeof(long) */
  // char runid[CONFIG_RUN_ID_SIZE + 1]; /* ID always different at every exec.
  // */
  int port;     /* TCP listening port */
  int tls_port; /* TLS listening port */
  // ustime_t ustime;                    /* 'unixtime' in microseconds. */
  // redisAtomic time_t unixtime;        /* Unix time sampled every cron cycle.
  // */
  time_t stat_starttime; /* Server start time */
  int hz;                /* serverCron() calls frequency in hertz */
  int config_hz;         /* Configured HZ value. May be different than
                            the actual 'hz' field value if dynamic-hz
                            is enabled. */
  unsigned int lruclock; /* Clock for LRU eviction */
  char *executable;      /* Absolute executable file path. */
  char *configfile;      /* Absolute config file path, or NULL */
  int io_threads_active; /* Is IO threads currently active? */

  /* # Clients */
  // list *clients;                 /* List of active clients */
  // list *slaves, *monitors;       /* List of slaves and MONITORs */
  unsigned int maxclients;       /* Max number of simultaneous clients */
  unsigned int blocked_clients;  /* # of clients executing a blocking cmd.*/
  unsigned int tracking_clients; /* # of clients with tracking enabled.*/
  unsigned int pubsub_clients;   /* # of clients in Pub/Sub mode */
  unsigned int watching_clients; /* # of clients are wathcing keys */
  // rax *clients_timeout_table;    /* Radix tree for blocked clients timeouts.
  // */

  /// memory start
  // zmalloc_used
  size_t stat_peak_memory;      /* Max used memory record */
  time_t stat_peak_memory_time; /* Time when stat_peak_memory was recorded */
  // struct malloc_stats cron_malloc_stats; /* sampled in serverCron(). */

  size_t repl_buffer_mem; /* The memory of replication buffer. */
  // replDataBuf repl_full_sync_buffer; /* Accumulated replication data for rdb
  // channel replication */
  int active_defrag_running; /* Active defragmentation running (holds current
                                scan aggressiveness) */
  /// memory end

  /// persistance start
  volatile sig_atomic_t loading; /* We are loading data from disk if true */
  volatile sig_atomic_t async_loading; /* We are loading data without blocking
                                          the db being served */
  size_t stat_current_cow_peak;        /* Peak size of copy on write bytes. */
  size_t
      stat_current_cow_bytes; /* Copy on write bytes while child is active. */
  monotime
      stat_current_cow_updated; /* Last update time of stat_current_cow_bytes */
  double stat_module_progress;  // for fork_perk
  size_t stat_current_save_keys_processed; // for fork_perk
  size_t stat_current_save_keys_total;     // for fork_perk
  long long dirty;            /* Changes to DB from the last save */
  int child_type;             /* Type of current child */
  time_t lastsave;            /* Unix time of last successful save */
  int lastbgsave_status;      /* C_OK or C_ERR */
  time_t rdb_save_time_last;  /* Time used by last RDB save run. */
  time_t rdb_save_time_start; /* Current RDB save start time. */
  long long stat_rdb_saves;   /* number of rdb saves performed */
  long long stat_rdb_consecutive_failures; /* The number of consecutive failures
                                              of rdb saves */
  size_t stat_rdb_cow_bytes; /* Copy on write bytes during RDB saving. */
  long long
      rdb_last_load_keys_expired; /* number of expired keys when loading RDB */
  long long
      rdb_last_load_keys_loaded; /* number of loaded keys when loading RDB */
  int aof_state;                 /* AOF_(ON|OFF|WAIT_REWRITE) */
  time_t aof_rewrite_time_last;  /* Time used by last AOF rewrite run. */
  time_t aof_rewrite_time_start; /* Current AOF rewrite start time. */
  long long stat_aof_rewrites;   /* number of aof file rewrites performed */
  long long stat_aofrw_consecutive_failures; /* The number of consecutive
                                                failures of aofrw */
  int aof_last_write_status;                 /* C_OK or C_ERR */
  int aof_bio_fsync_status;    /* Status of AOF fsync in bio job. */
  size_t stat_aof_cow_bytes;   /* Copy on write bytes during AOF rewrite. */
  int aof_enabled;             /* AOF configuration */
  off_t aof_current_size;      /* AOF current size (Including BASE + INCRs). */
  off_t aof_rewrite_base_size; /* AOF size on latest startup or rewrite. */
  int aof_rewrite_scheduled;   /* Rewrite once BGSAVE terminates. */
  // sds aof_buf; /* AOF buffer, written before entering the event loop */
  unsigned long aof_delayed_fsync; /* delayed AOF fsync() counter */
  time_t loading_start_time;
  off_t loading_total_bytes;
  off_t loading_rdb_used_mem;
  off_t loading_loaded_bytes;
  /// persistance end

  /// start Stats
  long long stat_numcommands;    /* Number of processed commands */
  long long stat_numconnections; /* Number of connections received */
  struct {
    long long last_sample_base;  /* The divisor of last sample window */
    long long last_sample_value; /* The dividend of last sample window */
    // long long samples[STATS_METRIC_SAMPLES];
    int idx;
  } inst_metric[STATS_METRIC_COUNT];   // for getInsttaneousMetric
  long long stat_net_input_bytes;      /* Bytes read from network. */
  long long stat_net_output_bytes;     /* Bytes written to network. */
  long long stat_net_repl_input_bytes; /* Bytes read during replication, added
                                          to stat_net_input_bytes in 'info'. */
  long long
      stat_net_repl_output_bytes; /* Bytes written during replication, added to
                                     stat_net_output_bytes in 'info'. */
  long long
      stat_client_qbuf_limit_disconnections; /* Total number of clients reached
                                                query buf length limit */
  long long stat_rejected_conn;    /* Clients rejected because of maxclients */
  long long stat_sync_full;        /* Number of full resyncs with slaves. */
  long long stat_sync_partial_ok;  /* Number of accepted PSYNC requests. */
  long long stat_sync_partial_err; /* Number of unaccepted PSYNC requests. */
  long long stat_expired_subkeys;  /* Number of expired subkeys (Currently only
                                      hash-fields) */
  long long stat_expiredkeys;      /* Number of expired keys */
  double stat_expired_stale_perc;  /* Percentage of keys probably expired */
  long long stat_expired_time_cap_reached_count; /* Early expire cycle stops.*/
  long long stat_expire_cycle_time_used; /* Cumulative microseconds used. */
  long long stat_evictedkeys;    /* Number of evicted keys (maxmemory) */
  long long stat_evictedclients; /* Number of evicted clients */
  long long stat_evictedscripts; /* Number of evicted lua scripts. */
  long long stat_total_eviction_exceeded_time; /* Total time over the memory
                                                  limit, unit us */
  monotime stat_last_eviction_exceeded_time;   /* Timestamp of current eviction
                                                  start, unit us */
  long long stat_keyspace_hits;   /* Number of successful lookups of keys */
  long long stat_keyspace_misses; /* Number of failed lookups of keys */
  // kvstore *pubsub_channels; /* Map channels to list of subscribed clients */
  // dict *pubsub_patterns;    /* A dict of pubsub_patterns */
  // kvstore *pubsubshard_channels; /* Map shard channels in every slot to list
  // of subscribed clients */
  long long stat_fork_time;   /* Time needed to perform latest fork() */
  long long stat_total_forks; /* Total count of fork. */
  // dict *migrate_cached_sockets;  /* MIGRATE cached sockets */
  long long stat_active_defrag_hits;   /* number of allocations moved */
  long long stat_active_defrag_misses; /* number of allocations scanned but not
                                          moved */
  long long
      stat_active_defrag_key_hits; /* number of keys with moved allocations */
  long long
      stat_active_defrag_key_misses; /* number of keys scanned and not moved */
  long long stat_total_active_defrag_time; /* Total time memory fragmentation
                                              over the limit, unit us */
  monotime stat_last_active_defrag_time;   /* Timestamp of current active defrag
                                              start */
  long long stat_unexpected_error_replies; /* Number of unexpected (aof-loading,
                                              replica to master, etc.) error
                                              replies */
  long long stat_total_error_replies; /* Total number of issued error replies (
                                         command + rejected errors ) */
  long long stat_dump_payload_sanitizations; /* Number deep dump payloads
                                                integrity validations. */
  // long long
  //     stat_io_reads_processed[IO_THREADS_MAX_NUM]; /* Number of read events
  //                                                     processed by IO / Main
  //                                                     threads */
  // long long
  //     stat_io_writes_processed[IO_THREADS_MAX_NUM]; /* Number of write events
  //                                                      processed by IO / Main
  //                                                      threads */
  long long
      stat_total_prefetch_batches; /* Total number of prefetched batches */
  long long
      stat_total_prefetch_entries; /* Total number of prefetched dict entries */
  long long stat_client_outbuf_limit_disconnections; /* Total number of clients
                                                        reached output buf
                                                        length limit */
  long long
      stat_reply_buffer_shrinks; /* Total number of output buffer shrinks */
  long long
      stat_reply_buffer_expands; /* Total number of output buffer expands */
  // durationStats duration_stats[EL_DURATION_TYPE_NUM];
  /// end Stats

  /// start Replication
  time_t repl_down_since; /* Unix time at which link with master went down */
  // char replid[CONFIG_RUN_ID_SIZE + 1];  /* My current replication ID. */
  // char replid2[CONFIG_RUN_ID_SIZE + 1]; /* replid inherited from master*/
  long long master_repl_offset;   /* My current replication offset */
  long long second_replid_offset; /* Accept offsets up to this for replid2. */
  long long repl_backlog_size;    /* Backlog circular buffer size */
  /// end Replication

  /// start CPU
  /// end CPU
  /* -----------------------------------------------------------------------------------------------
   */
};

struct rusage {
  /* Total amount of user time used.  */
  struct timeval ru_utime;
  /* Total amount of system time used.  */
  struct timeval ru_stime;
  /* Maximum resident set size (in kilobytes).  */
  __extension__ union {
    long int ru_maxrss;
    __syscall_slong_t __ru_maxrss_word;
  };
  /* Amount of sharing of text segment memory
     with other processes (kilobyte-seconds).  */
  __extension__ union {
    long int ru_ixrss;
    __syscall_slong_t __ru_ixrss_word;
  };
  /* Amount of data segment memory used (kilobyte-seconds).  */
  __extension__ union {
    long int ru_idrss;
    __syscall_slong_t __ru_idrss_word;
  };
  /* Amount of stack memory used (kilobyte-seconds).  */
  __extension__ union {
    long int ru_isrss;
    __syscall_slong_t __ru_isrss_word;
  };
  /* Number of soft page faults (i.e. those serviced by reclaiming
     a page from the list of pages awaiting reallocation.  */
  __extension__ union {
    long int ru_minflt;
    __syscall_slong_t __ru_minflt_word;
  };
  /* Number of hard page faults (i.e. those that required I/O).  */
  __extension__ union {
    long int ru_majflt;
    __syscall_slong_t __ru_majflt_word;
  };
  /* Number of times a process was swapped out of physical memory.  */
  __extension__ union {
    long int ru_nswap;
    __syscall_slong_t __ru_nswap_word;
  };
  /* Number of input operations via the file system.  Note: This
     and `ru_oublock' do not include operations with the cache.  */
  __extension__ union {
    long int ru_inblock;
    __syscall_slong_t __ru_inblock_word;
  };
  /* Number of output operations via the file system.  */
  __extension__ union {
    long int ru_oublock;
    __syscall_slong_t __ru_oublock_word;
  };
  /* Number of IPC messages sent.  */
  __extension__ union {
    long int ru_msgsnd;
    __syscall_slong_t __ru_msgsnd_word;
  };
  /* Number of IPC messages received.  */
  __extension__ union {
    long int ru_msgrcv;
    __syscall_slong_t __ru_msgrcv_word;
  };
  /* Number of signals delivered.  */
  __extension__ union {
    long int ru_nsignals;
    __syscall_slong_t __ru_nsignals_word;
  };
  /* Number of voluntary context switches, i.e. because the process
     gave up the process before it had to (usually to wait for some
     resource to be available).  */
  __extension__ union {
    long int ru_nvcsw;
    __syscall_slong_t __ru_nvcsw_word;
  };
  /* Number of involuntary context switches, i.e. a higher priority process
     became runnable or the current process used up its time slice.  */
  __extension__ union {
    long int ru_nivcsw;
    __syscall_slong_t __ru_nivcsw_word;
  };
};
