#!/bin/bash

# ./mutilate \
#   -s 10.10.10.1:11211 \
#   -s 10.10.10.1:11212 \
#   -s 10.10.10.1:11213 \
#   -s 10.10.10.1:11214 \
#   -s 10.10.10.1:11215 \
#   -T 48 --records 1000000 --loadonly

/home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:11211 \
  -s 10.10.10.1:11212 \
  -s 10.10.10.1:11213 \
  -s 10.10.10.1:11214 \
  -s 10.10.10.1:11215 \
  -T 48 --records 1000000 --loadonly
