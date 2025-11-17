#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <netinet/in.h> // needed for "IPPROTO_UDP"
#include "memcached_metrics.h"

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
int xdp_kernel_monitoring(struct xdp_md *ctx) {
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

    
    int metrics_size;
    if ((metrics_size = bpf_get_cpu_metrics_direct_copy(ctx, payload_offset)) < 0) {
      bpf_printk("disk cpu fail: metrics size is %d\n", metrics_size);
      return XDP_ABORTED;
    }
    payload_offset += metrics_size;
    if ((metrics_size = bpf_get_disk_metrics_direct_copy(ctx, payload_offset)) < 0) {
      bpf_printk("disk metrics fail: metrics size is %d\n", metrics_size);
      return XDP_ABORTED;
    }
    payload_offset += metrics_size;
    if ((metrics_size = bpf_get_memory_metrics_direct_copy(ctx, payload_offset)) < 0) {
      bpf_printk("memory metrics fail: metrics size is %d\n", metrics_size);
      return XDP_ABORTED;
    }
    payload_offset += metrics_size;
    if ((metrics_size = bpf_get_ipv4_metrics_direct_copy(ctx, payload_offset)) < 0) {
      bpf_printk("ipv4 metrics fail: metrics size is %d\n", metrics_size);
      return XDP_ABORTED;
    }
    payload_offset += metrics_size;
    if ((metrics_size = bpf_get_ipv4_tcp_udp_metrics_direct_copy(ctx, payload_offset)) < 0) {
      bpf_printk("ipv4 metrics fail: metrics size is %d\n", metrics_size);
      return XDP_ABORTED;
    }

    bpf_rdtsc((long *)&end);
    elapsed_cycles = end - start;
    bpf_printk("Elapsed cycles are %ld", elapsed_cycles);

    return XDP_TX;
}

char _license[] SEC("license") = "GPL";
