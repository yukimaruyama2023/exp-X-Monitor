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
metrics = ["user", "kernel"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

cpu_aff = "pin-netdata-core0"

strict_comparison = False
if strict_comparison:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/only-go-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/no-plugin.conf"
else:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/only-disable-go-plugin.conf"

netdata_conf = {
    "cpu_affinity": f"{conf_root}/netdata/cpu-affinity/{cpu_aff}.conf",
    "user_plugin_conf": user_plugin_conf,
    "kernel_plugin_conf": kernel_plugin_conf,
}
data_dir = f"{remote_data_root}/monitoring_latency/strict-{strict_comparison}/{cpu_aff}/{timestamp}"

def run_memcached(num_memcached):
    print(f"=== [Start] Running Memcached {num_memcached} instances ===")
    subprocess.Popen(f"./src/server/memcached/execute.sh {num_memcached}".split())
    print(f"=== [End] Running Memcached {num_memcached} instances ===")

def stop_mutilate():
    subprocess.run(["ssh", remote_host, "pkill", "mutilate"])

def stop_memcached():
    subprocess.run("sudo pkill memcached".split())

def run_netdata(num_memcached, metric):
    print(f"=== [Start] Running Netdata {num_memcached} ===")
    # memcached_conf = f"{conf_root}/{str(num_memcached).zfill(3)}mcd/go.d/memcached.conf"
    memcached_conf = f"{conf_root}/netdata/num_mcd/{str(num_memcached).zfill(3)}-memcached.conf"
    print(f"{memcached_conf}")
    subprocess.run(f"sudo cp {memcached_conf} /etc/netdata/go.d/memcached.conf".split())
    if metric == "user":
        subprocess.run(f"sudo cp {netdata_conf["user_plugin_conf"]} /etc/netdata/netdata.conf".split())
    else:
        subprocess.run(f"sudo cp {netdata_conf["kernel_plugin_conf"]} /etc/netdata/netdata.conf".split())
    subprocess.run(f"sudo systemctl restart netdata".split())
    print(f"=== [End] Running Netdata {num_memcached} ===")

def run_mutilate(num_memcached):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    subprocess.run(f"ssh {remote_host} {remote_mutilate_scripts}/{str(num_memcached).zfill(3)}mcd/load.sh".split())
    subprocess.Popen(f"ssh {remote_host} {remote_mutilate_scripts}/{str(num_memcached).zfill(3)}mcd/run.sh".split())
    print(f"=== [End] Running mutilate {num_memcached} ===")

def run_monitor(num_memcached, metric):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    if metric == "user":
        stdin_input = "1\n1\n"
    else:
        stdin_input = "1\n0\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        f"./client_netdata {data_dir}/netdata-{metric}metrics-{num_memcached}mcd.csv"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split(),
                   input=stdin_input,
                   text=True
    )
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def run_server(num_memcached, metric):
    run_memcached(num_memcached)
    run_netdata(num_memcached, metric)

def run_client(num_memcached, metric):
    run_mutilate(num_memcached)
    run_monitor(num_memcached, metric)

def stop_server():
    stop_mutilate()
    stop_memcached()

def setup():
    print(f"=== [Start] Setup: Create data_dir and set cpu-affinity of netdata === ")
    cmd = (
        f"mkdir -p {data_dir} &&"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    subprocess.run(f"sudo cp {netdata_conf["cpu_affinity"]} /etc/systemd/system/netdata.service.d/override.conf".split())
    print(f"=== [End] Setup: Create data_dir and set cpu-affinity of netdata === ")

def main():
    setup()
    for metric in metrics:
        for num_memcached in num_memcacheds:
            print()
            print(f"############## Running {num_memcached} servers ##########################")
            run_server(num_memcached, metric)
            run_client(num_memcached, metric)
            stop_server()
            # needed to pkill memcached completely
            time.sleep(5)

if __name__ == "__main__":
    main()
