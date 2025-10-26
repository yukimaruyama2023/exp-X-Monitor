#include <stdint.h>
#include <stddef.h>

struct stats {
    uint64_t      total_items;
    uint64_t      total_conns;
    uint64_t      rejected_conns;
    uint64_t      malloc_fails;
    uint64_t      listen_disabled_num;
    uint64_t      slabs_moved;       /* times slabs were moved around */
    uint64_t      slab_reassign_rescues; /* items rescued during slab move */
    uint64_t      slab_reassign_evictions_nomem; /* valid items lost during slab move */
    uint64_t      slab_reassign_inline_reclaim; /* valid items lost during slab move */
    uint64_t      slab_reassign_chunk_rescues; /* chunked-item chunks recovered */
    uint64_t      slab_reassign_busy_items; /* valid temporarily unmovable */
    uint64_t      slab_reassign_busy_deletes; /* refcounted items killed */
    uint64_t      lru_crawler_starts; /* Number of item crawlers kicked off */
    uint64_t      lru_maintainer_juggles; /* number of LRU bg pokes */
    uint64_t      time_in_listen_disabled_us;  /* elapsed time in microseconds while server unable to process new connections */
    uint64_t      log_worker_dropped; /* logs dropped by worker threads */
    uint64_t      log_worker_written; /* logs written by worker threads */
    uint64_t      log_watcher_skipped; /* logs watchers missed */
    uint64_t      log_watcher_sent; /* logs sent to watcher buffers */
    uint64_t      unexpected_napi_ids;  /* see doc/napi_ids.txt */
    uint64_t      round_robin_fallback; /* see doc/napi_ids.txt */
#ifdef TLS // collected only when TLS is defined. usually not defined.
    uint64_t      ssl_proto_errors; /* TLS failures during SSL_read() and SSL_write() calls */
    uint64_t      ssl_handshake_errors; /* TLS failures at accept/handshake time */
    uint64_t      ssl_new_sessions; /* successfully negotiated new (non-reused) TLS sessions */
#endif  // only above is collected
    struct timeval maxconns_entered;  /* last time maxconns entered */
#ifdef EXTSTORE
    uint64_t      extstore_compact_lost; /* items lost because they were locked */
    uint64_t      extstore_compact_rescues; /* items re-written during compaction */
    uint64_t      extstore_compact_skipped; /* unhit items skipped during compaction */
    uint64_t      extstore_compact_resc_cold; /* items re-written during compaction */
    uint64_t      extstore_compact_resc_old; /* items re-written during compaction */
#endif
};

// every metrics is collected
struct stats_state {
    uint64_t      curr_items;
    uint64_t      curr_bytes;
    uint64_t      curr_conns;
    uint64_t      hash_bytes;       /* size used for hash tables */
    unsigned int  conn_structs;
    unsigned int  reserved_fds;
    unsigned int  hash_power_level; /* Better hope it's not over 9000 */
    unsigned int  log_watchers; /* number of currently active watchers */
    bool          hash_is_expanding; /* If the hash table is being expanded */
    bool          accepting_conns;  /* whether we are currently accepting */
    bool          slab_reassign_running; /* slab reassign in progress */
    bool          lru_crawler_running; /* crawl in progress */
};

struct settings {
    size_t maxbytes;
    int maxconns;
    int num_threads;        /* number of worker (without dispatcher) libevent threads to run */
    bool maxconns_fast;     /* Whether or not to early close connections */
#ifdef TLS
    rel_time_t ssl_last_cert_refresh_time; /* time of the last server certificate refresh */
#endif
   // only above is collected

    int port;
    int udpport;
    char *inter;
    int verbose;
    rel_time_t oldest_live; /* ignore existing items older than this */
    int evict_to_free;
    char *socketpath;   /* path to unix socket if using local socket */
    char *auth_file;    /* path to user authentication file */
    int access;  /* access mask (a la chmod) for unix domain socket */
    double factor;          /* chunk size growth factor */
    int chunk_size;
    int num_threads_per_udp; /* number of worker threads serving each udp socket */
    char prefix_delimiter;  /* character that marks a key prefix (for stats) */
    int detail_enabled;     /* nonzero if we're collecting detailed stats */
    int reqs_per_event;     /* Maximum number of io to process on each
                               io-event. */
    bool use_cas;
    enum protocol binding_protocol;
    int backlog;
    int item_size_max;        /* Maximum item size */
    int slab_chunk_size_max;  /* Upper end for chunks within slab pages. */
    int slab_page_size;     /* Slab's page units. */
    volatile sig_atomic_t sig_hup;  /* a HUP signal was received but not yet handled */
    bool sasl;              /* SASL on/off */
    bool lru_crawler;        /* Whether or not to enable the autocrawler thread */
    bool lru_maintainer_thread; /* LRU maintainer background thread */
    bool lru_segmented;     /* Use split or flat LRU's */
    bool slab_reassign;     /* Whether or not slab reassignment is allowed */
    bool ssl_enabled; /* indicates whether SSL is enabled */
    int slab_automove;     /* Whether or not to automatically move slabs */
    double slab_automove_ratio; /* youngest must be within pct of oldest */
    unsigned int slab_automove_window; /* window mover for algorithm */
    int hashpower_init;     /* Starting hash power level */
    bool shutdown_command; /* allow shutdown command */
    int tail_repair_time;   /* LRU tail refcount leak repair time */
    bool flush_enabled;     /* flush_all enabled */
    bool dump_enabled;      /* whether cachedump/metadump commands work */
    char *hash_algorithm;     /* Hash algorithm in use */
    int lru_crawler_sleep;  /* Microsecond sleep between items */
    uint32_t lru_crawler_tocrawl; /* Number of items to crawl per run */
    int hot_lru_pct; /* percentage of slab space for HOT_LRU */
    int warm_lru_pct; /* percentage of slab space for WARM_LRU */
    double hot_max_factor; /* HOT tail age relative to COLD tail */
    double warm_max_factor; /* WARM tail age relative to COLD tail */
    int crawls_persleep; /* Number of LRU crawls to run before sleeping */
    bool temp_lru; /* TTL < temporary_ttl uses TEMP_LRU */
    uint32_t temporary_ttl; /* temporary LRU threshold */
    int idle_timeout;       /* Number of seconds to let connections idle */
    unsigned int logger_watcher_buf_size; /* size of logger's per-watcher buffer */
    unsigned int logger_buf_size; /* size of per-thread logger buffer */
    unsigned int read_buf_mem_limit; /* total megabytes allowable for net buffers */
    bool drop_privileges;   /* Whether or not to drop unnecessary process privileges */
    bool watch_enabled; /* allows watch commands to be dropped */
    bool relaxed_privileges;   /* Relax process restrictions when running testapp */
#ifdef EXTSTORE
    unsigned int ext_io_threadcount; /* number of IO threads to run. */
    unsigned int ext_page_size; /* size in megabytes of storage pages. */
    unsigned int ext_item_size; /* minimum size of items to store externally */
    unsigned int ext_item_age; /* max age of tail item before storing ext. */
    unsigned int ext_low_ttl; /* remaining TTL below this uses own pages */
    unsigned int ext_recache_rate; /* counter++ % recache_rate == 0 > recache */
    unsigned int ext_wbuf_size; /* read only note for the engine */
    unsigned int ext_compact_under; /* when fewer than this many pages, compact */
    unsigned int ext_drop_under; /* when fewer than this many pages, drop COLD items */
    unsigned int ext_max_sleep; /* maximum sleep time for extstore bg threads, in us */
    double ext_max_frag; /* ideal maximum page fragmentation */
    double slab_automove_freeratio; /* % of memory to hold free as buffer */
    bool ext_drop_unread; /* skip unread items during compaction */
    /* start flushing to extstore after memory below this */
    unsigned int ext_global_pool_min;
#endif
#ifdef TLS
    void *ssl_ctx; /* holds the SSL server context which has the server certificate */
    char *ssl_chain_cert; /* path to the server SSL chain certificate */
    char *ssl_key; /* path to the server key */
    int ssl_verify_mode; /* client certificate verify mode */
    int ssl_keyformat; /* key format , default is PEM */
    char *ssl_ciphers; /* list of SSL ciphers */
    char *ssl_ca_cert; /* certificate with CAs. */
    unsigned int ssl_wbuf_size; /* size of the write buffer used by ssl_sendmsg method */
    bool ssl_session_cache; /* enable SSL server session caching */
    bool ssl_kernel_tls; /* enable server kTLS */
    int ssl_min_version; /* minimum SSL protocol version to accept */
#endif
    int num_napi_ids;   /* maximum number of NAPI IDs */
    char *memory_file;  /* warm restart memory file path */
#ifdef PROXY
    bool proxy_enabled;
    bool proxy_uring; /* if the proxy should use io_uring */
    bool proxy_memprofile; /* output detail of lua allocations */
    char *proxy_startfile; /* lua file to run when workers start */
    char *proxy_startarg; /* string argument to pass to proxy */
    void *proxy_ctx; /* proxy's state context */
#endif
#ifdef SOCK_COOKIE_ID
    uint32_t sock_cookie_id;
#endif
};

struct rusage
  {
    struct timeval ru_utime; // * 
    struct timeval ru_stime; // * 
	  long ru_maxrss; 
	  long ru_ixrss; 
	  long ru_idrss;
	  long ru_isrss;
	  long ru_minflt;
	  long ru_majflt;
	  long ru_nswap;
	  long ru_inblock;
	  long ru_oublock;
	  long ru_msgsnd;
	  long ru_msgrcv;
	  long ru_nsignals;
	  long ru_nvcsw;
	  long ru_nivcsw;
  };

#define THREAD_STATS_FIELDS \
    X(get_cmds) \
    X(get_misses) \
    X(get_expired) \
    X(get_flushed) \
    X(touch_cmds) \
    X(touch_misses) \
    X(delete_misses) \
    X(incr_misses) \
    X(decr_misses) \
    X(cas_misses) \
    X(meta_cmds) \
    X(bytes_read) \
    X(bytes_written) \
    X(flush_cmds) \
    X(conn_yields) /* # of yields for connections (-R option)*/ \
    X(auth_cmds) \
    X(auth_errors) \
    X(idle_kicks) /* idle connections killed */ \
    X(response_obj_oom) \
    X(response_obj_count) \
    X(response_obj_bytes) \
    X(read_buf_oom) \
    X(store_too_large) \
    X(store_no_memory)

#ifdef EXTSTORE
#define EXTSTORE_THREAD_STATS_FIELDS \
    X(get_extstore) \
    X(get_aborted_extstore) \
    X(get_oom_extstore) \
    X(recache_from_extstore) \
    X(miss_from_extstore) \
    X(badcrc_from_extstore)
#endif

#ifdef PROXY
#define PROXY_THREAD_STATS_FIELDS \
    X(proxy_conn_requests) \
    X(proxy_conn_errors) \
    X(proxy_conn_oom) \
    X(proxy_req_active)
#endif

/**
 * Stats stored per-thread.
 */
struct thread_stats {
#define X(name) uint64_t    name;
    THREAD_STATS_FIELDS //*
    uint64_t lru_hits[POWER_LARGEST]; //*
    uint64_t read_buf_count; //*
    uint64_t read_buf_bytes; //*
    uint64_t read_buf_bytes_free; //*
// only above is collected
    struct slab_stats slab_stats[MAX_NUMBER_OF_SLAB_CLASSES];
#ifdef EXTSTORE
    EXTSTORE_THREAD_STATS_FIELDS
#endif
    pthread_mutex_t   mutex;
#ifdef PROXY
    PROXY_THREAD_STATS_FIELDS
#endif
#undef X
};




#define SLAB_STATS_FIELDS \
    X(set_cmds) \
    X(get_hits) \
    X(touch_hits) \
    X(delete_hits) \
    X(cas_hits) \
    X(cas_badval) \
    X(incr_hits) \
    X(decr_hits)

/** Stats stored per slab (and per thread). */
// every metrics is collected
struct slab_stats {
#define X(name) uint64_t    name;
    SLAB_STATS_FIELDS
#undef X
};



typedef struct {
  uint64_t evicted; // *
  uint64_t reclaimed; // *
  uint64_t expired_unfetched; // *
  uint64_t evicted_unfetched; // *
  uint64_t evicted_active;    // *
  uint64_t crawler_reclaimed; // *
  uint64_t crawler_items_checked; // *
  uint64_t lrutail_reflocked; // *
  uint64_t moves_to_cold; // *
  uint64_t moves_to_warm; // *
  uint64_t moves_within_lru; // *
  uint64_t direct_reclaims; // *
  // only above is collected
  uint64_t evicted_nonzero;
  uint64_t tailrepairs;
  uint64_t outofmemory;
  uint64_t hits_to_hot;
  uint64_t hits_to_warm;
  uint64_t hits_to_cold;
  uint64_t hits_to_temp;
  uint64_t mem_requested;
  rel_time_t evicted_time;
} itemstats_t;
extern itemstats_t totals;
