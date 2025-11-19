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
int xdp_user_indirectcopy(struct xdp_md *ctx) {
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

    // bpf_xdp_adjust_tail(ctx, 7000);

    bpf_xdp_store_bytes(ctx, 0, &eth, sizeof(struct ethhdr));
    bpf_xdp_store_bytes(ctx, sizeof(struct ethhdr), &ip, sizeof(struct iphdr));
    bpf_xdp_store_bytes(ctx, sizeof(struct ethhdr) + sizeof(struct iphdr), &udp, sizeof(struct udphdr));

    /* Header handling is completed. Write monitoring program below! */
  
    __u64 payload_offset = sizeof(struct ethhdr) + sizeof(struct iphdr) + sizeof(struct udphdr);
    
    int port_array[100] = {
      11211, 11212, 11213, 11214, 11215,
      11216, 11217, 11218, 11219, 11220,
      11221, 11222, 11223, 11224, 11225,
      11226, 11227, 11228, 11229, 11230,
      11231, 11232, 11233, 11234, 11235,
      11236, 11237, 11238, 11239, 11240,
      11241, 11242, 11243, 11244, 11245,
      11246, 11247, 11248, 11249, 11250,
      11251, 11252, 11253, 11254, 11255,
      11256, 11257, 11258, 11259, 11260,
      11261, 11262, 11263, 11264, 11265,
      11266, 11267, 11268, 11269, 11270,
      11271, 11272, 11273, 11274, 11275,
      11276, 11277, 11278, 11279, 11280,
      11281, 11282, 11283, 11284, 11285,
      11286, 11287, 11288, 11289, 11290,
      11291, 11292, 11293, 11294, 11295,
      11296, 11297, 11298, 11299, 11300,
      11301, 11302, 11303, 11304, 11305,
      11306, 11307, 11308, 11309, 11310
    };

    struct memcached_metrics memcached_metrics[NUM_APP];
    
    for (int i = 0; i < NUM_APP; i++) {
      int metrics_size = 0;
      if ((metrics_size = bpf_user_met_indirect_copy((uint64_t)&memcached_metrics[i], sizeof(struct memcached_metrics), port_array[i])) < 0) {
        bpf_printk("[ABORTED] port: %d, total_metrics_size is %d \n", port_array[i], metrics_size);
        return XDP_ABORTED;
      }
    }
    
    for (int i = 0; i < NUM_APP; i++) {
      if ((void *)payload_offset + sizeof(struct memcached_metrics) > data_end) return XDP_PASS;
      bpf_xdp_store_bytes(ctx, payload_offset, &memcached_metrics[i], sizeof(struct memcached_metrics));
      payload_offset += sizeof(struct memcached_metrics);
    }

    bpf_rdtsc((long *)&end);
    elapsed_cycles = end - start;
    bpf_printk("Elapsed cycles are %ld", elapsed_cycles);

    return XDP_TX;
}

char _license[] SEC("license") = "GPL";
