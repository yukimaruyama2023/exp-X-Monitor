#include <stddef.h>
#include <stdint.h>

#ifndef bool
typedef _Bool bool;
#endif

#define EXTSTORE
#define SOCK_COOKIE_ID
#define SIZEOF_PTHREAD_MUTEX_T 40
#define MAX_NUMBER_OF_SLAB_CLASSES (63 + 1)
#define POWER_LARGEST 256 /* actual cap is 255 */
typedef unsigned int rel_time_t;
enum protocol {
  ascii_prot = 3, /* arbitrary value. */
  binary_prot,
  negotiating_prot, /* Discovering the protocol */
#ifdef PROXY
  proxy_prot,
#endif
};
typedef int __sig_atomic_t;
typedef __sig_atomic_t sig_atomic_t;

struct timeval_m {
  __time_t tv_sec;       /* Seconds.  */
  __suseconds_t tv_usec; /* Microseconds.  */
};

// // this consists of 224 byte without any padding
// struct stats {
//     uint64_t      total_items; // *
//     uint64_t      total_conns; // *
//     uint64_t      rejected_conns; // *
//     uint64_t      malloc_fails; // *
//     uint64_t      listen_disabled_num; // *
//     uint64_t      slabs_moved; // *
//     uint64_t      slab_reassign_rescues; // *
//     uint64_t      slab_reassign_evictions_nomem; // *
//     uint64_t      slab_reassign_inline_reclaim; // *
//     uint64_t      slab_reassign_chunk_rescues;  // *
//     uint64_t      slab_reassign_busy_items; // *
//     uint64_t      slab_reassign_busy_deletes; // *
//     uint64_t      lru_crawler_starts; // *
//     uint64_t      lru_maintainer_juggles; // *
//     uint64_t      time_in_listen_disabled_us; // *
//     uint64_t      log_worker_dropped; // *
//     uint64_t      log_worker_written; // *
//     uint64_t      log_watcher_skipped; // *
//     uint64_t      log_watcher_sent;  // *
//     uint64_t      extstore_compact_lost;  // *
//     uint64_t      extstore_compact_rescues; // *
//     uint64_t      extstore_compact_skipped; // *
//     uint64_t      extstore_compact_resc_cold; // *
//     uint64_t      extstore_compact_resc_old; // *
//     struct timeval_m maxconns_entered; // 16byte
//     uint64_t      unexpected_napi_ids; // *
//     uint64_t      round_robin_fallback; // *
// };
//
// // this consists of 56 byte: 8(uint64_t)*4 + 4(unsigned int)*4 + 1(bool)*4 +
// 4(padding)
// // every metrics is collected
// struct stats_state {
//     uint64_t      curr_items; // *
//     uint64_t      curr_bytes; // *
//     uint64_t      curr_conns; // *
//     uint64_t      hash_bytes;   // *
//     unsigned int  conn_structs; // *
//     unsigned int  reserved_fds; // *
//     unsigned int  hash_power_level; // *
//     unsigned int  log_watchers; // *
//     bool          hash_is_expanding; // *
//     bool          accepting_conns;  // *
//     bool          slab_reassign_running; // *
//     bool          lru_crawler_running; // *
// };
//
// // this consists of 144: 16*2 + 8*14
// // only struct timeval is collected
// struct rusage
//   {
//     struct timeval_m ru_utime; // *
//     struct timeval_m ru_stime; // *
// 	  // long ru_maxrss;
// 	  // long ru_ixrss;
// 	  // long ru_idrss;
// 	  // long ru_isrss;
// 	  // long ru_minflt;
// 	  // long ru_majflt;
// 	  // long ru_nswap;
// 	  // long ru_inblock;
// 	  // long ru_oublock;
// 	  // long ru_msgsnd;
// 	  // long ru_msgrcv;
// 	  // long ru_nsignals;
// 	  // long ru_nvcsw;
// 	  // long ru_nivcsw;
//   };
//
// struct slab_stats {
//     uint64_t set_cmds; // *
//     uint64_t get_hits; // *
//     uint64_t touch_hits; // *
//     uint64_t delete_hits; // *
//     uint64_t cas_hits; // *
//     uint64_t cas_badval; // *
//     uint64_t incr_hits; // *
//     uint64_t decr_hits; // *
// };
//
// struct settings {
//     size_t maxbytes;
//     int maxconns;
//     int port;
//     int udpport;
//     char *inter;
//     int verbose;
//     rel_time_t oldest_live;
//     int evict_to_free;
//     char *socketpath;
//     char *auth_file;
//     int access;
//     double factor;
//     int chunk_size;
//     int num_threads;
//     int num_threads_per_udp;
//     char prefix_delimiter;
//     int detail_enabled;
//     bool use_cas;
//     enum protocol binding_protocol;
//     int backlog;
//     int item_size_max;
//     int slab_chunk_size_max;
//     int slab_page_size;
//     volatile sig_atomic_t sig_hup;
//     bool sasl;
//     bool maxconns_fast;
//     bool lru_crawler;
//     bool lru_maintainer_thread;
//     bool lru_segmented;
//     bool slab_reassign;
//     bool ssl_enabled;
//     int slab_automove;
//     double slab_automove_ratio;
//     unsigned int slab_automove_window;
//     int hashpower_init;
//     bool shutdown_command;
//     int tail_repair_time;
//     bool flush_enabled;
//     bool dump_enabled;
//     char *hash_algorithm;
//     int lru_crawler_sleep;
//     uint32_t lru_crawler_tocrawl;
//     int hot_lru_pct;
//     int warm_lru_pct;
//     double hot_max_factor;
//     double warm_max_factor;
//     int crawls_persleep;
//     bool temp_lru;
//     uint32_t temporary_ttl;
//     int idle_timeout;
//     unsigned int logger_watcher_buf_size;
//     unsigned int logger_buf_size;
//     unsigned int read_buf_mem_limit;
//     bool drop_privileges;
//     bool watch_enabled;
//     bool relaxed_privileges;
// #ifdef EXTSTORE
//     unsigned int ext_io_threadcount;
//     unsigned int ext_page_size;
//     unsigned int ext_item_size;
//     unsigned int ext_item_age;
//     unsigned int ext_low_ttl;
//     unsigned int ext_recache_rate;
//     unsigned int ext_wbuf_size;
//     unsigned int ext_compact_under;
//     unsigned int ext_drop_under;
//     unsigned int ext_max_sleep;
//     double ext_max_frag;
//     double slab_automove_freeratio;
//     bool ext_drop_unread;
//     unsigned int ext_global_pool_min;
// #endif
// #ifdef TLS
//     void *ssl_ctx;
//     char *ssl_chain_cert;
//     char *ssl_key;
//     int ssl_verify_mode;
//     int ssl_keyformat;
//     char *ssl_ciphers;
//     char *ssl_ca_cert;
//     rel_time_t ssl_last_cert_refresh_time;
//     unsigned int ssl_wbuf_size;
//     bool ssl_session_cache;
//     bool ssl_kernel_tls;
//     int ssl_min_version;
// #endif
//     int num_napi_ids;
//     char *memory_file;
// #ifdef PROXY
//     bool proxy_enabled;
//     bool proxy_uring;
//     bool proxy_memprofile;
//     char *proxy_startfile;
//     char *proxy_startarg;
//     void *proxy_ctx;
// #endif
// #ifdef SOCK_COOKIE_ID
//     uint32_t sock_cookie_id;
// #endif
// };
//
//
// // struct thread and relatives
// struct __pthread_mutex_m
// {
// //   int __lock;
// //   unsigned int __count;
// //   int __owner;
// // #ifdef __x86_64__
// //   unsigned int __nusers;
// // #endif
// //   /* KIND must stay at this position in the structure to maintain
// //      binary compatibility with static initializers.  */
// //   int __kind;
// // #ifdef __x86_64__
// //   short __spins;
// //   __pthread_list_t __list; // it may be 16 bytes, but is ambiguous
// //   short __elision;
// // # define __PTHREAD_MUTEX_HAVE_PREV      1
// // #else
// //   unsigned int __nusers;
// //   __extension__ union
// //   {
// //     struct
// //     {
// //       short __espins;
// //       short __eelision;
// // # define __spins __elision_data.__espins
// // # define __elision __elision_data.__eelision
// //     } __elision_data;
// //     __pthread_slist_t __list;
// //   };
// // # define __PTHREAD_MUTEX_HAVE_PREV      0
// // #endif
//   long a[5];
// };
//
// #define THREAD_STATS_FIELDS \
//     X(get_cmds) \
//     X(get_misses) \
//     X(get_expired) \
//     X(get_flushed) \
//     X(touch_cmds) \
//     X(touch_misses) \
//     X(delete_misses) \
//     X(incr_misses) \
//     X(decr_misses) \
//     X(cas_misses) \
//     X(meta_cmds) \
//     X(bytes_read) \
//     X(bytes_written) \
//     X(flush_cmds) \
//     X(conn_yields)\
//     X(auth_cmds) \
//     X(auth_errors) \
//     X(idle_kicks) \
//     X(response_obj_oom) \
//     X(response_obj_count) \
//     X(response_obj_bytes) \
//     X(read_buf_oom) \
//     X(store_too_large) \
//     X(store_no_memory)
//
// #ifdef EXTSTORE
// #define EXTSTORE_THREAD_STATS_FIELDS \
//     X(get_extstore) \
//     X(get_aborted_extstore) \
//     X(get_oom_extstore) \
//     X(recache_from_extstore) \
//     X(miss_from_extstore) \
//     X(badcrc_from_extstore)
// #endif
//
// typedef union
// {
//   struct __pthread_mutex_m __data;
//   char __size[SIZEOF_PTHREAD_MUTEX_T];
//   long int __align;
// } pthread_mutex_m;
//
// struct thread_stats {
//     pthread_mutex_m   mutex;
// #define X(name) uint64_t    name;
//     THREAD_STATS_FIELDS
// #ifdef EXTSTORE
//     EXTSTORE_THREAD_STATS_FIELDS
// #endif
// #ifdef PROXY
//     PROXY_THREAD_STATS_FIELDS
// #endif
// #undef X
//     struct slab_stats slab_stats[MAX_NUMBER_OF_SLAB_CLASSES];
//     uint64_t lru_hits[POWER_LARGEST];
//     uint64_t read_buf_count;
//     uint64_t read_buf_bytes;
//     uint64_t read_buf_bytes_free;
// };
//
// // itemstats_t
// typedef struct {
//     uint64_t evicted;
//     uint64_t evicted_nonzero;
//     uint64_t reclaimed;
//     uint64_t outofmemory;
//     uint64_t tailrepairs;
//     uint64_t expired_unfetched;
//     uint64_t evicted_unfetched;
//     uint64_t evicted_active;
//     uint64_t crawler_reclaimed;
//     uint64_t crawler_items_checked;
//     uint64_t lrutail_reflocked;
//     uint64_t moves_to_cold;
//     uint64_t moves_to_warm;
//     uint64_t moves_within_lru;
//     uint64_t direct_reclaims;
//     uint64_t hits_to_hot;
//     uint64_t hits_to_warm;
//     uint64_t hits_to_cold;
//     uint64_t hits_to_temp;
//     uint64_t mem_requested;
//     rel_time_t evicted_time;
// } itemstats_t;

struct stats {
  uint64_t total_items;
  uint64_t total_conns;
  uint64_t rejected_conns;
  uint64_t malloc_fails;
  uint64_t listen_disabled_num;
  uint64_t slabs_moved;
  uint64_t slab_reassign_rescues;
  uint64_t slab_reassign_evictions_nomem;
  uint64_t slab_reassign_inline_reclaim;
  uint64_t slab_reassign_chunk_rescues;
  uint64_t slab_reassign_busy_items;
  uint64_t slab_reassign_busy_deletes;
  uint64_t lru_crawler_starts;
  uint64_t lru_maintainer_juggles;
  uint64_t time_in_listen_disabled_us;
  uint64_t log_worker_dropped;
  uint64_t log_worker_written;
  uint64_t log_watcher_skipped;
  uint64_t log_watcher_sent;
  uint64_t unexpected_napi_ids;
  uint64_t round_robin_fallback;
#ifdef TLS // collected only when TLS is defined. usually not defined.
  uint64_t ssl_proto_errors;
  uint64_t ssl_handshake_errors;
  uint64_t ssl_new_sessions;
#endif // only above is collected
};

// every metrics is collected
struct stats_state {
  uint64_t curr_items;
  uint64_t curr_bytes;
  uint64_t curr_conns;
  uint64_t hash_bytes;
  unsigned int conn_structs;
  unsigned int reserved_fds;
  unsigned int hash_power_level;
  unsigned int log_watchers;
  bool hash_is_expanding;
  bool accepting_conns;
  bool slab_reassign_running;
  bool lru_crawler_running;
};

struct settings {
  size_t maxbytes;
  int maxconns;
  int num_threads;
  bool maxconns_fast;
#ifdef TLS
  rel_time_t ssl_last_cert_refresh_time;
#endif
  // only above is collected
};

struct rusage {
  struct timeval_m ru_utime; // *
  struct timeval_m ru_stime; // *
};

#define THREAD_STATS_FIELDS\
  X(get_cmds)  \
  X(get_misses)\
  X(get_expired)\
  X(get_flushed)\
  X(touch_cmds)\
  X(touch_misses)\
  X(delete_misses)\
  X(incr_misses)\
  X(decr_misses)\
  X(cas_misses)\
  X(meta_cmds)\
  X(bytes_read)\
  X(bytes_written)\
  X(flush_cmds) \
  X(conn_yields) \
  X(auth_cmds) \
  X(auth_errors) \
  X(idle_kicks)\
  X(response_obj_oom)\
  X(response_obj_count)\
  X(response_obj_bytes)\
  X(read_buf_oom)\
  X(store_too_large)\
  X(store_no_memory)

/**
 * Stats stored per-thread.
 */
struct thread_stats {
#define X(name) uint64_t name;
  THREAD_STATS_FIELDS                   //*
  uint64_t read_buf_count;              //*
  uint64_t read_buf_bytes;              //*
  uint64_t read_buf_bytes_free;         //*
                                        // only above is collected
};

#define SLAB_STATS_FIELDS                                                      \
  X(set_cmds)                                                                  \
  X(get_hits)                                                                  \
  X(touch_hits)                                                                \
  X(delete_hits)                                                               \
  X(cas_hits)                                                                  \
  X(cas_badval)                                                                \
  X(incr_hits)                                                                 \
  X(decr_hits)

/** Stats stored per slab (and per thread). */
// every metrics is collected
struct slab_stats {
#define X(name) uint64_t name;
  SLAB_STATS_FIELDS
#undef X
};

typedef struct {
  uint64_t evicted;               // *
  uint64_t reclaimed;             // *
  uint64_t expired_unfetched;     // *
  uint64_t evicted_unfetched;     // *
  uint64_t evicted_active;        // *
  uint64_t crawler_reclaimed;     // *
  uint64_t crawler_items_checked; // *
  uint64_t lrutail_reflocked;     // *
  uint64_t moves_to_cold;         // *
  uint64_t moves_to_warm;         // *
  uint64_t moves_within_lru;      // *
  uint64_t direct_reclaims;       // *
  // only above is collected
} itemstats_t;
