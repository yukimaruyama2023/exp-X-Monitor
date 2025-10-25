import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
# import numpy as np

num_memcacheds = [1,5,10]

conf_root = "./conf"

def run_memcached(num_memcached):
    print("hello")

def run_netdata(num_memcached):
    memcached_conf = f"{conf_root}/{str(num_memcached).zfill(3)}mcd/go.d/memcached.conf"
    print(f"{memcached_conf}")
    subprocess.run(f"sudo cp {memcached_conf} /etc/netdata/go.d/memcached.conf".split())
    subprocess.run(f"sudo systemctl restart netdata".split())

def run_client():
    print("hello")

def main():
    for num_memcached in num_memcacheds:
        run_memcached(num_memcached)
        run_netdata(num_memcached)
        run_client()
        time.sleep(10)

if __name__ == "__main__":
    main()
