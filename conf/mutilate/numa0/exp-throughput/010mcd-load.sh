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
  -s 10.10.10.1:11220 \
  -T 24 --records 1000000 --loadonly
