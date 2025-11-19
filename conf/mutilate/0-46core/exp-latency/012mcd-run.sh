#!/bin/bash

taskset -c 0-46 /home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:11211 \
  -s 10.10.10.1:11212 \
  -s 10.10.10.1:11213 \
  -s 10.10.10.1:11214 \
  -s 10.10.10.1:11215 \
  -s 10.10.10.1:11216 \
  -s 10.10.10.1:11217 \
  -s 10.10.10.1:11218 \
  -s 10.10.10.1:11219 \
  -s 10.10.10.1:11220 \
  -s 10.10.10.1:11221 \
  -s 10.10.10.1:11222 \
  -T 47 -c 1 -q 0 -u 0 -i exponential:1 -t 30000 --noload --depth 1 --records 1000000
