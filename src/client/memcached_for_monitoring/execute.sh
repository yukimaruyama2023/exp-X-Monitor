#!/bin/bash

BASE_PORT=11211

NUM_INSTANCES=${1:-10}

for i in $(seq 0 $((NUM_INSTANCES - 1))); do
  PORT=$((BASE_PORT + i))
  taskset --cpu-list 1,2,3,4,5 ./memcached -p $PORT -t 1 &
  # ./memcached -p $PORT -t 1 &
  echo "Started memcached on port $PORT"
done

wait
