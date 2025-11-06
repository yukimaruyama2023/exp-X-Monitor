import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
import datetime

remote_host = "hamatora"
remote_mutilate_script_latency = "/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/exp-latency/"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
local_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
conf_root = "./conf"

num_memcacheds = [1, 5, 10]
x_monitor_intervals = [1, 0.1, 0.01]
metrics = ["user", "kernel"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

############################################ Configuration ###############################################

#########################################################################################################

user_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
kernel_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
netdata_cpu_aff = "pin-netdata-core0.conf"
mcd_cpu_aff = "pin-core1-5-execute.sh"

netdata_conf = {
    "cpu_affinity": f"{conf_root}/netdata/cpu-affinity/{netdata_cpu_aff}",
    "user_plugin_conf": user_plugin_conf,
    "kernel_plugin_conf": kernel_plugin_conf,
}

data_dir = f"{local_data_root}/monitoring_cpu_utilization/{timestamp}"


def run_memcached(num_memcached):
    print(f"=== [Start] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff} ===")
    subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff} {num_memcached}".split())
    print(f"=== [End] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff} ===")

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

def run_netdata_client_monitor(num_memcached, metric):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    if metric == "user":
        stdin_input = "1\n1\n"
    else:
        stdin_input = "1\n0\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        f"./client_netdata test.csv"
    )
    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def load_xdp(metric):
    exe_script = "xdp_user_directcopy.sh" if metric == "user" else "xdp_cpu_indirectcopy.sh"
    script_path = os.path.join(x_monitor_root, exe_script)
    subprocess.run([script_path], cwd=x_monitor_root, check=True)
    time.sleep(5)

def detach_xdp():
    script_path = os.path.join(x_monitor_root, "off.sh")
    subprocess.run([script_path], cwd=x_monitor_root, check=True)
    time.sleep(5)

def run_x_monitor_client_monitor(num_memcached, metric, x_monitor_interval):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    if x_monitor_interval == 1:
        stdin_input = "1\n"
    elif x_monitor_interval == 0.1:
        stdin_input = "0.1\n"
    else:
        stdin_input = "0.01\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        f"./client_x-monitor test.csv"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split(),
                   input=stdin_input,
                   text=True
    )
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def calculate_netdata_cpu(num_memcached, metric):
    print(f"=== [Start] Calculate Netdata CPU Utilization, {num_memcached} instance, {metric} metrics === ")
    subprocess.run(f"pidstat -u -p $(pgrep -d',' -f netdata) 40 1 > {data_dir}/{str(num_memcached).zfill(3)}mcd/netdata-{metric}metrics-{num_memcached}mcd.csv".split())
    print(f"=== [End] Calculate Netdata CPU Utilization, {num_memcached} instance, {metric} metrics === ")

def calculate_x_monitor_cpu(num_memcached, metric):
    print(f"=== [Start] Calculate X-Monitor CPU Utilization, {num_memcached} instance, {metric} metrics === ")
    subprocess.run(f"sudo cat /sys/kernel/debug/tracing/trace_pipe > {data_dir}/{str(num_memcached).zfill(3)}mcd/xmonitor-{metric}metrics-{num_memcached}mcd.csv".split())
    print(f"=== [End] Calculate X-Monitor CPU Utilization, {num_memcached} instance, {metric} metrics === ")

def stop_monitoring_client_for_netdata():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "client_netdata"])

def stop_bpf_tracepipe():
    subprocess.run("sudo pkill -f trace_pipe".split())

def stop_memcached():
    subprocess.run("sudo pkill -f memcached".split())

def run_netdata_server(num_memcached, metric):
    run_memcached(num_memcached)
    run_netdata(num_memcached, metric)

def run_netdata_client(num_memcached, metric):
    run_netdata_client_monitor(num_memcached, metric)

def run_x_monitor_server(num_memcached, metric):
    run_memcached(num_memcached)
    load_xdp(metric)

def run_x_monitor_client(num_memcached, metric, x_monitor_interval):
    run_x_monitor_client_monitor(num_memcached, metric, x_monitor_interval)


def stop_for_netdata():
    stop_monitoring_client_for_netdata()
    stop_memcached()

def stop_for_x_monitor():
    stop_bpf_tracepipe()
    stop_memcached()
    detach_xdp()

def setup():
    print(f"=== [Start] Setup: cpu-affinity of netdata ===")
    subprocess.run(f"sudo cp {netdata_conf["cpu_affinity"]} /etc/systemd/system/netdata.service.d/override.conf".split())
    print(f"=== [End] Setup: cpu-affinity of netdata ===")

def make_output_dir(num_memcached):
    print(f"=== [Start] Making output_dir {data_dir}/{str(num_memcached).zfill(3)}mcd ===")
    cmd = (
        f"mkdir -p {data_dir}/{str(num_memcached).zfill(3)}mcd"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Making output_dir {data_dir}/{str(num_memcached).zfill(3)}mcd ===")

def netdata_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### Netdata: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        for num_memcached in num_memcacheds:
            print()
            print(f"############## Running {num_memcached} servers ##########################")
            make_output_dir(num_memcached)
            run_netdata_server(num_memcached, metric)
            run_netdata_client(num_memcached, metric)
            calculate_netdata_cpu(num_memcached, metric)
            stop_for_netdata()
            time.sleep(5)

def x_monitor_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### X-Monitor: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        for num_memcached in num_memcacheds:
            print(f"############## Running {num_memcached} servers ##########################")
            make_output_dir(num_memcached)
            for x_monitor_interval in x_monitor_intervals:
                print(f"############## Interval {x_monitor_interval} ##########################")
                run_x_monitor_server(num_memcached, metric)
                run_x_monitor_client(num_memcached, metric, x_monitor_interval)
                calculate_x_monitor_cpu(num_memcached, metric)
                stop_for_x_monitor()
                time.sleep(5)

def main():
    setup()
    x_monitor_monitoring()
    netdata_monitoring()

if __name__ == "__main__":
    main()
