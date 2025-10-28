#!/bin/sh

sudo clang -O2 -g -Wall -target bpf -c xdp_cpu_indirectcopy.c -o xdp_cpu_indirectcopy.o
sudo ip link set enp7s0f0np0 xdpdrv off
sudo ip link set enp7s0f0np0 xdpdrv obj xdp_cpu_indirectcopy.o sec xdp.frags
