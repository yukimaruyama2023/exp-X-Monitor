#!/bin/bash

numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:6379 \
  -s 10.10.10.1:6380 \
  -s 10.10.10.1:6381 \
  -s 10.10.10.1:6382 \
  -s 10.10.10.1:6383 \
  -s 10.10.10.1:6384 \
  -s 10.10.10.1:6385 \
  -s 10.10.10.1:6386 \
  -T 24 --records 1000000 --loadonly
