#!/bin/bash

./mutilate \
  -s 10.10.10.1:11211 \
  -s 10.10.10.1:11212 \
  -s 10.10.10.1:11213 \
  -s 10.10.10.1:11214 \
  -s 10.10.10.1:11215 \
  -T 48 -c 1 -q 0 -u 0 -i exponential:1 -t 80 --noload --depth 1 --records 1000000
