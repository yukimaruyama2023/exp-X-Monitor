#!/bin/bash

BASE_PORT=6379

NUM_INSTANCES=${1:-10}

for i in $(seq 0 $((NUM_INSTANCES - 1))); do
  PORT=$((BASE_PORT + i))
  ./src/server/redis/src/redis-server --port $PORT &
  echo "Started redis on port $PORT"
done
