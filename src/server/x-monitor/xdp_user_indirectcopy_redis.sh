#!/bin/sh

sudo clang -O2 -g -Wall -target bpf -c xdp_user_indirectcopy_redis.c -o xdp_user_indirectcopy_redis.o
sudo ip link set enp7s0f0np0 xdpdrv off
sudo ip link set enp7s0f0np0 xdpdrv obj xdp_user_indirectcopy_redis.o sec xdp.frags
