#!/bin/bash

taskset -c 0-46 /home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/mutilate \
  -s 10.10.10.1:11211 \
  -T 47 --records 1000000 --loadonly
