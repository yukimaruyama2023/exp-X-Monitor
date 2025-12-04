#!/bin/bash

timeout 43 numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/redis/src/redis-benchmark -h 10.10.10.1 -p 6379 --threads 24 -c 24 -P 1 -d 1000000 -t get -n 1000000000 >tmp0.txt &
timeout 43 numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/redis/src/redis-benchmark -h 10.10.10.1 -p 6380 --threads 24 -c 24 -P 1 -d 1000000 -t get -n 1000000000 >tmp1.txt &
timeout 43 numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/redis/src/redis-benchmark -h 10.10.10.1 -p 6381 --threads 24 -c 24 -P 1 -d 1000000 -t get -n 1000000000 >tmp2.txt &
timeout 43 numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/redis/src/redis-benchmark -h 10.10.10.1 -p 6382 --threads 24 -c 24 -P 1 -d 1000000 -t get -n 1000000000 >tmp3.txt &
timeout 43 numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/redis/src/redis-benchmark -h 10.10.10.1 -p 6383 --threads 24 -c 24 -P 1 -d 1000000 -t get -n 1000000000 >tmp4.txt &
timeout 43 numactl --cpunodebind=0 --membind=0 /home/maruyama/workspace/exp-X-Monitor/src/client/redis/src/redis-benchmark -h 10.10.10.1 -p 6384 --threads 24 -c 24 -P 1 -d 1000000 -t get -n 1000000000 >tmp5.txt &
