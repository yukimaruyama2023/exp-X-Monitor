#!/bin/bash

./mutilate \
  -s 10.10.10.1:11211 \
  -T 48 --records 1000000 --loadonly
