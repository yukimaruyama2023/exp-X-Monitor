#!/bin/sh

sudo clang -O2 -g -Wall -target bpf -c xdp_kernel_directcopy.c -o xdp_kernel_directcopy.o
sudo ip link set enp7s0f0np0 xdpdrv off
sudo ip link set enp7s0f0np0 xdpdrv obj xdp_kernel_directcopy.o sec xdp.frags
