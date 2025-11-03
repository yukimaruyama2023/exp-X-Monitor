#!/bin/bash

/home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:11211 \
  -T 48 -c 1 -q 0 -u 0 -i exponential:1 -t 300 --noload --depth 1 --records 1000000
