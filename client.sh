#!/bin/bash

# mutilate
sudo apt-get install scons libevent-dev gengetopt libzmq3-dev
cd ./src/client/mutilate/ && scons

# monitoring client
cd -
gcc -o ./src/client/Monitoring_Client/client_netdata ./src/client/Monitoring_Client/client_netdata.c
gcc -o ./src/client/Monitoring_Client/client_x-monitor ./src/client/Monitoring_Client/client_x-monitor.c
