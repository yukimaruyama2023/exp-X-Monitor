#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <netinet/in.h> // needed for "IPPROTO_UDP"
#include "redis_metrics.h"

#define NUM_APP 12
// #define RETURN_METRIC_SIZE 512

// struct buf_700{
//   char buf[700];
// };

struct redis_metrics {
  char buf[740];
};

// struct redis_metrics {
//   struct redisServer redisServer;
//   struct rusage rusage;
// };

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
int xdp_user_indirectcopy_redis(struct xdp_md *ctx) {
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
      6379,  6380,  6381,  6382,  6383,
      6384,  6385,  6386,  6387,  6388,
      6389,  6390,  6391,  6392,  6393,
      6394,  6395,  6396,  6397,  6398,
      6399,  6400,  6401,  6402,  6403,
      6404,  6405,  6406,  6407,  6408,
      6409,  6410,  6411,  6412,  6413,
      6414,  6415,  6416,  6417,  6418,
      6419,  6420,  6421,  6422,  6423,
      6424,  6425,  6426,  6427,  6428,
      6429,  6430,  6431,  6432,  6433,
      6434,  6435,  6436,  6437,  6438,
      6439,  6440,  6441,  6442,  6443,
      6444,  6445,  6446,  6447,  6448,
      6449,  6450,  6451,  6452,  6453,
      6454,  6455,  6456,  6457,  6458,
      6459,  6460,  6461,  6462,  6463,
      6464,  6465,  6466,  6467,  6468,
      6469,  6470,  6471,  6472,  6473,
      6474,  6475,  6476,  6477,  6478,
    };

    struct redis_metrics redis_metrics[NUM_APP];
    
    for (int i = 0; i < NUM_APP; i++) {
      int metrics_size = 0;
      if ((metrics_size = bpf_user_met_indirect_copy((uint64_t)&redis_metrics[i], sizeof(struct redis_metrics), port_array[i])) < 0) {
        bpf_printk("[ABORTED] port: %d, total_metrics_size is %d \n", port_array[i], metrics_size);
        return XDP_ABORTED;
      }
    }
    
    for (int i = 0; i < NUM_APP; i++) {
      if ((void *)payload_offset + sizeof(struct redis_metrics) > data_end) return XDP_PASS;
      bpf_xdp_store_bytes(ctx, payload_offset, &redis_metrics[i], sizeof(struct redis_metrics));
      payload_offset += sizeof(struct redis_metrics);
    }
    
    // for (int i = 0; i < NUM_APP; i++) {
    //   if ((void *)payload_offset + RETURN_METRIC_SIZE > data_end) return XDP_PASS;
    //   bpf_xdp_store_bytes(ctx, payload_offset, &redis_metrics[i], RETURN_METRIC_SIZE);
    //   payload_offset += RETURN_METRIC_SIZE;
    // }

    // for (int i = 0; i < NUM_APP; i++) {
    //     void *write_end = data + payload_offset + RETURN_METRIC_SIZE;
    //     if (write_end > data_end)
    //         return XDP_PASS;
    //     bpf_xdp_store_bytes(ctx, payload_offset,
    //                         &redis_metrics[i],
    //                         RETURN_METRIC_SIZE);
    //
    //     payload_offset += RETURN_METRIC_SIZE;
    // }

    bpf_rdtsc((long *)&end);
    elapsed_cycles = end - start;
    bpf_printk("Elapsed cycles are %ld", elapsed_cycles);

    return XDP_TX;
}

char _license[] SEC("license") = "GPL";
