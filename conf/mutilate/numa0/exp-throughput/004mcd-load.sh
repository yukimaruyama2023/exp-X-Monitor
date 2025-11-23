#!/bin/bash

numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:11211 \
  -s 10.10.10.1:11212 \
  -s 10.10.10.1:11213 \
  -s 10.10.10.1:11214 \
  -T 24 --records 50000000 --loadonly
