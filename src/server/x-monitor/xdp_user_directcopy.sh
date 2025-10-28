#!/bin/sh

sudo clang -O2 -g -Wall -target bpf -c xdp_user_directcopy.c -o xdp_user_directcopy.o
sudo ip link set enp7s0f0np0 xdpdrv off
sudo ip link set enp7s0f0np0 xdpdrv obj xdp_user_directcopy.o sec xdp.frags
