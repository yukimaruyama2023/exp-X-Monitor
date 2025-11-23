#!/bin/bash

numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:11211 \
  -s 10.10.10.1:11212 \
  -s 10.10.10.1:11213 \
  -s 10.10.10.1:11214 \
  -s 10.10.10.1:11215 \
  -s 10.10.10.1:11216 \
  -s 10.10.10.1:11217 \
  -s 10.10.10.1:11218 \
  -s 10.10.10.1:11219 \
  -T 24 -c 80 -q 0 -u 0 -i exponential:1 -t 40 --noload --depth 1 --records 1000000
