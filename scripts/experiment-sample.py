import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
import datetime
# import numpy as np

remote_host = "hamatora"
remote_mutilate_scripts = "/home/maruyama/workspace/exp-X-Monitor/src/client/mutilate/shell-scripts/"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
remote_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
conf_root = "./conf"

num_memcacheds = [1,5,10]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
output_dir = f"{remote_data_root}/monitoring_latency/{timestamp}"

def run_memcached(num_memcached):
    print(f"=== [Start] Running Memcached {num_memcached} instances === ")
    subprocess.Popen(f"./src/server/memcached/execute.sh {num_memcached}".split())
    print(f"=== [End] Running Memcached {num_memcached} instances === ")

def stop_mutilate():
    subprocess.run(["ssh", remote_host, "pkill", "mutilate"])

def stop_memcached():
    subprocess.run("sudo pkill memcached".split())

def run_netdata(num_memcached):
    print(f"=== [Start] Running Netdata {num_memcached} === ")
    memcached_conf = f"{conf_root}/{str(num_memcached).zfill(3)}mcd/go.d/memcached.conf"
    print(f"{memcached_conf}")
    subprocess.run(f"sudo cp {memcached_conf} /etc/netdata/go.d/memcached.conf".split())
    subprocess.run(f"sudo systemctl restart netdata".split())
    print(f"=== [End] Running Netdata {num_memcached} === ")

def run_mutilate(num_memcached):
    print(f"=== [Start] Running mutilate {num_memcached} === ")
    subprocess.run(f"ssh {remote_host} {remote_mutilate_scripts}/{str(num_memcached).zfill(3)}mcd/load.sh".split())
    subprocess.Popen(f"ssh {remote_host} {remote_mutilate_scripts}/{str(num_memcached).zfill(3)}mcd/run.sh".split())
    print(f"=== [End] Running mutilate {num_memcached} === ")

def run_monitor(num_memcached):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    stdin_input = "1\n1\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        f"./client_netdata {output_dir}/netdata-{num_memcached}mcd.csv"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split(),
                   input=stdin_input,
                   text=True
    )
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def run_client(num_memcached):
    run_mutilate(num_memcached)
    run_monitor(num_memcached)

def run_server(num_memcached):
    run_memcached(num_memcached)
    run_netdata(num_memcached)

def stop_server():
    stop_mutilate()
    stop_memcached()

def make_output_dir():
    print(f"=== [Start] Creating output_dir: {output_dir} === ")
    cmd = (
        f"mkdir -p {output_dir} &&"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Creating output_dir: {output_dir} === ")


def main():
    make_output_dir()
    for num_memcached in num_memcacheds:
        print()
        print(f"############## Running {num_memcached} servers ##########################")
        run_server(num_memcached)
        # time.sleep(10)
        run_client(num_memcached)
        stop_server()
        # needed to pkill memcached completely
        time.sleep(5)

if __name__ == "__main__":
    main()
