#!/bin/bash

# ./mutilate \
#   -s 10.10.10.1:11211 \
#   -T 48 --records 1000000 --loadonly

/home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:11211 \
  -T 48 --records 1000000 --loadonly
