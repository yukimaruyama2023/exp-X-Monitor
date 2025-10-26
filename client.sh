#!/bin/bash

# mutilate
sudo apt-get install scons libevent-dev gengetopt libzmq3-dev
cd ./src/client/mutilate/ && scons
