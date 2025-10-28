#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <netinet/in.h> // needed for "IPPROTO_UDP"
#include "memcached_metrics.h"

#define NUM_APP 10

struct memcached_metrics {
  struct stats stats;
  struct stats_state stats_state;
  struct settings settings;
  struct rusage rusage;
  struct thread_stats thread_stats;
  struct slab_stats slab_stats;
  itemstats_t totals;
};

enum {
  STATS,
  STATS_STATE,
  SETTINGS,
  RUSAGE,
  THREAD_STATS,
  SLAB_STATS,
  TOTALS,
};

static __always_inline void swap_src_dst_mac(struct ethhdr *eth) {
    __u8 tmp[ETH_ALEN];
    __builtin_memcpy(tmp, eth->h_source, ETH_ALEN);
    __builtin_memcpy(eth->h_source, eth->h_dest, ETH_ALEN);
    __builtin_memcpy(eth->h_dest, tmp, ETH_ALEN);
}

static __always_inline void swap_src_dst_ip(struct iphdr *ip) {
    __be32 tmp = ip->saddr;
    ip->saddr = ip->daddr;
    ip->daddr = tmp;
}

static __always_inline void swap_src_dst_udp(struct udphdr *udp) {
    udp->source = 53078; // 22223
    udp->dest = 52822;  // 22222
}

SEC("xdp.frags")
int xdp_udp_echo(struct xdp_md *ctx) {
    __u64 start, end, elapsed_cycles;
    bpf_rdtsc((long *)&start);
    void *data     = (void *)(unsigned long)ctx->data;
    void *data_end = (void *)(unsigned long)ctx->data_end;

    struct ethhdr eth;
    if (bpf_xdp_load_bytes(ctx, 0, &eth, sizeof(eth)) < 0) {
        return XDP_DROP;
    }

    __u64 offset = sizeof(struct ethhdr);

    struct iphdr ip;
    if (bpf_xdp_load_bytes(ctx, offset, &ip, sizeof(ip)) < 0) {
        return XDP_DROP;
    }

    __u64 ip_header_length = ip.ihl * 4;
    if (ip_header_length < sizeof(struct iphdr)) {
        return XDP_DROP;
    }

    if (ip.protocol != IPPROTO_UDP) {
        return XDP_DROP;
    }

    offset += ip_header_length;

    struct udphdr udp;
    if (bpf_xdp_load_bytes(ctx, offset, &udp, sizeof(udp)) < 0) {
        return XDP_DROP;
    }

    swap_src_dst_mac(&eth);
    swap_src_dst_ip(&ip);
    swap_src_dst_udp(&udp);
    udp.check = 0;

    bpf_xdp_store_bytes(ctx, 0, &eth, sizeof(struct ethhdr));
    bpf_xdp_store_bytes(ctx, sizeof(struct ethhdr), &ip, sizeof(struct iphdr));
    bpf_xdp_store_bytes(ctx, sizeof(struct ethhdr) + sizeof(struct iphdr), &udp, sizeof(struct udphdr));

    /* Header handling is completed. Write monitoring program below! */

    __u64 payload_offset = sizeof(struct ethhdr) + sizeof(struct iphdr) + sizeof(struct udphdr);
    
    int port_array[10] = {11211, 11212, 11213, 11214, 11215,
                          11216, 11217, 11218, 11219, 11220};

    struct memcached_metrics memcached_metrics[NUM_APP];

    for (int i = 0; i < NUM_APP; i++) {
      bpf_get_application_metrics(port_array[i], STATS,
                                  (char *)&memcached_metrics[i].stats,
                                  sizeof(struct stats));
      bpf_get_application_metrics(port_array[i], STATS_STATE,
                                  (char *)&memcached_metrics[i].stats_state,
                                  sizeof(struct stats_state));
      bpf_get_application_metrics(port_array[i], SETTINGS,
                                  (char *)&memcached_metrics[i].settings,
                                  sizeof(struct settings));
      bpf_get_application_metrics(port_array[i], RUSAGE,
                                  (char *)&memcached_metrics[i].rusage,
                                  sizeof(struct rusage));
      bpf_get_application_metrics(port_array[i], THREAD_STATS,
                                  (char *)&memcached_metrics[i].thread_stats,
                                  sizeof(struct thread_stats));
      bpf_get_application_metrics(port_array[i], SLAB_STATS,
                                  (char *)&memcached_metrics[i].slab_stats,
                                  sizeof(struct slab_stats));
      bpf_get_application_metrics(port_array[i], TOTALS,
                                  (char *)&memcached_metrics[i].totals,
                                  sizeof(itemstats_t));
    }
    
    for (int i = 0; i < NUM_APP; i++) {
      if ((void *)payload_offset + sizeof(struct stats) > data_end) {
        return XDP_PASS;
      }
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i].stats, sizeof(struct stats));
      payload_offset += sizeof(struct stats);
      if ((void *)payload_offset + sizeof(struct stats_state) > data_end) {
        return XDP_PASS;
      }
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i].stats_state, sizeof(struct stats_state));
      payload_offset += sizeof(struct stats_state);
      if ((void *)payload_offset + sizeof(struct settings) > data_end) {
        return XDP_PASS;
      }
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i].settings, sizeof(struct settings));
      payload_offset += sizeof(struct settings);
      if ((void *)payload_offset + sizeof(struct rusage) > data_end) {
        return XDP_PASS;
      }
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i].rusage, sizeof(struct rusage));
      payload_offset += sizeof(struct rusage);
      if ((void *)payload_offset + sizeof(struct thread_stats) > data_end) {
        return XDP_PASS;
      }
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i].thread_stats, sizeof(struct thread_stats));
      payload_offset += sizeof(struct thread_stats);
      if ((void *)payload_offset + sizeof(struct slab_stats) > data_end) {
        return XDP_PASS;
      }
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i].slab_stats, sizeof(struct slab_stats));
      payload_offset += sizeof(struct slab_stats);
      if ((void *)payload_offset + sizeof(itemstats_t) > data_end) {
        return XDP_PASS;
      }
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i].totals, sizeof(itemstats_t));
      payload_offset += sizeof(itemstats_t);
    }
    bpf_rdtsc((long *)&end);
    elapsed_cycles = end - start;
    bpf_printk("Elapsed cycles are %ld", elapsed_cycles);

    return XDP_TX;
}

char _license[] SEC("license") = "GPL";
