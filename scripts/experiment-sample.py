import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
# import numpy as np

remote_host = "hamatora"
remote_mutilate_path = "/home/maruyama/workspace/mutilate"
conf_root = "./conf"

num_memcacheds = [1,5,10]

def run_memcached(num_memcached):
    subprocess.Popen(f"./src/server/memcached/execute.sh {num_memcached}".split())

def stop_memcached():
    subprocess.run("sudo pkill memcached".split())

def run_ssh_ls():
    res = subprocess.run(f"ssh {remote_host} ls".split())
    print(res)

def run_netdata(num_memcached):
    memcached_conf = f"{conf_root}/{str(num_memcached).zfill(3)}mcd/go.d/memcached.conf"
    print(f"{memcached_conf}")
    subprocess.run(f"sudo cp {memcached_conf} /etc/netdata/go.d/memcached.conf".split())
    subprocess.run(f"sudo systemctl restart netdata".split())

def run_client(num_memcached):
    subprocess.run(f"ssh {remote_host} {remote_mutilate_path}".split())

def run_server(num_memcached):
    # run_ssh_ls(num_memcached)
    run_memcached(num_memcached)
    run_netdata(num_memcached)
    # run_client(num_memcached)

def stop_server():
    stop_memcached()

def main():
    for num_memcached in num_memcacheds:
        print()
        print(f"############## Running {num_memcached} servers ##########################")
        run_server(num_memcached)
        # time.sleep(10)
        stop_server()
        # needed to pkill memcached completely
        time.sleep(5)

if __name__ == "__main__":
    main()
