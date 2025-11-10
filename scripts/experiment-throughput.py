import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
import datetime

remote_host = "hamatora"
# not latency but throughput
remote_mutilate_script_throughput = "/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/exp-throughput/"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
remote_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
conf_root = "./conf"

num_memcacheds = [1, 5, 10]
x_monitor_intervals = [1, 0.1, 0.01]
metrics = ["user", "kernel"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


############################################ Configuratin ###############################################
strict_comparison = True # default is False, which means almost all plugin runs
mcd_in_allcores_for_x_monitor = True # default is False; mcd for x_monitor runs in core 1-5, NOTE: you cannot configure mcd and netdata cpu affinity unlike latency experiment
cnts = 10
#########################################################################################################

if strict_comparison:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/only-go-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/no-plugin.conf"
else:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/only-disable-go-plugin.conf"

if mcd_in_allcores_for_x_monitor:
    mcd_cpu_aff_for_x_monitor = "all-core-execute.sh"
    mcd_cpu_aff_for_no_monitor = "all-core-execute.sh"
else:
    mcd_cpu_aff_for_x_monitor = "pin-core1-5-execute.sh"
    mcd_cpu_aff_for_no_monitor = "pin-core1-5-execute.sh"

netdata_cpu_aff = "pin-netdata-core0.conf"
mcd_cpu_aff_for_netdata = "pin-core1-5-execute.sh"

netdata_conf = {
    "cpu_affinity": f"{conf_root}/netdata/cpu-affinity/{netdata_cpu_aff}",
    "user_plugin_conf": user_plugin_conf,
    "kernel_plugin_conf": kernel_plugin_conf,
}

# change output data_dir
data_dir = f"{remote_data_root}/monitoring_throughput/strict-{strict_comparison}/ntd_mcd_allcores-{mcd_in_allcores_for_x_monitor}/{timestamp}"


def run_memcached_for_x_monitor(num_memcached):
    print(f"=== [Start] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff_for_x_monitor} ===")
    subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff_for_x_monitor} {num_memcached}".split())
    print(f"=== [End] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff_for_x_monitor} ===")

def run_memcached_for_netdata(num_memcached):
    print(f"=== [Start] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff_for_netdata} ===")
    subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff_for_netdata} {num_memcached}".split())
    print(f"=== [End] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff_for_netdata} ===")

def run_memcached_for_no_monitor(num_memcached):
    print(f"=== [Start] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff_for_no_monitor} ===")
    subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff_for_no_monitor} {num_memcached}".split())
    print(f"=== [End] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff_for_no_monitor} ===")

# kill x_monitor not mutilate
def stop_monitoring_client_for_netdata():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "client_netdata"])

def stop_monitoring_client_for_x_monitor():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "client_x-monitor"])

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


def run_netdata_client_monitor(num_memcached, metric):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    if metric == "user":
        stdin_input = "1\n1\n"
    else:
        stdin_input = "1\n0\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        # output file is test.csv
        f"./client_netdata test.csv"
    )
    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
    proc.stdin.write(stdin_input)
    proc.stdin.close()
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def load_xdp(metric, num_memcached):
    if metric == "user":
        c_file = os.path.join(x_monitor_root, "xdp_user_directcopy.c")
        with open(c_file, "r") as f:
            lines = f.readlines()
        with open(c_file, "w") as f:
            for line in lines:
                if line.startswith("#define NUM_APP"):
                    f.write(f"#define NUM_APP {num_memcached}\n")
                else:
                    f.write(line)

    exe_script = "xdp_user_directcopy.sh" if metric == "user" else "xdp_cpu_indirectcopy.sh"
    script_path = os.path.join(x_monitor_root, exe_script)
    subprocess.run([script_path], cwd=x_monitor_root, check=True)
    time.sleep(5)

def detach_xdp():
    script_path = os.path.join(x_monitor_root, "off.sh")
    subprocess.run([script_path], cwd=x_monitor_root, check=True)

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
        # output file is test.csv
        f"./client_x-monitor test.csv"
    )
    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
    proc.stdin.write(stdin_input)
    proc.stdin.close()
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def run_mutilate_for_netdata(cnt, num_memcached, metric):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    cmd = (
        f"{remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_memcached).zfill(3)}mcd/netdata-{metric}metrics-{num_memcached}mcd.txt"
    )
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-load.sh".split())
    run_netdata_client_monitor(num_memcached, metric)
    subprocess.run(f"ssh {remote_host} {cmd}".split())

    print(f"=== [End] Running mutilate {num_memcached} ===")

def run_mutilate_for_x_monitor(cnt, num_memcached, metric, x_monitor_interval):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    cmd = (
        f"{remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_memcached).zfill(3)}mcd/xmonitor-{metric}metrics-{num_memcached}mcd-interval{x_monitor_interval}.txt"
    )
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-load.sh".split())
    run_x_monitor_client_monitor(num_memcached, metric, x_monitor_interval)
    subprocess.run(f"ssh {remote_host} {cmd}".split())

    print(f"=== [End] Running mutilate {num_memcached} ===")

def run_mutilate_for_no_monitoring(cnt, num_memcached):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    cmd = (
        f"{remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_memcached).zfill(3)}mcd/no_monitoring-{num_memcached}mcd.txt"
    )
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-load.sh".split())
    subprocess.run(f"ssh {remote_host} {cmd}".split())

    print(f"=== [End] Running mutilate {num_memcached} ===")


def run_netdata_server(num_memcached, metric):
    run_memcached_for_netdata(num_memcached)
    run_netdata(num_memcached, metric)

def run_netdata_client(cnt, num_memcached, metric):
    # monitoring client is called inside run_mutilate_for_netdata
    run_mutilate_for_netdata(cnt, num_memcached, metric)

def run_x_monitor_server(num_memcached, metric):
    run_memcached_for_x_monitor(num_memcached)

def run_x_monitor_client(cnt, num_memcached, metric, x_monitor_interval):
    load_xdp(metric, num_memcached)
    # monitoring client is called inside run_mutilate_for_x_monitor
    run_mutilate_for_x_monitor(cnt, num_memcached, metric, x_monitor_interval)
    detach_xdp()

def stop_server_for_netdata():
    stop_monitoring_client_for_netdata()
    stop_memcached()

def stop_server_for_x_monitor():
    stop_monitoring_client_for_x_monitor()
    stop_memcached()

def setup():
    print(f"=== [Start] Setup: cpu-affinity of netdata ===")
    subprocess.run(f"sudo cp {netdata_conf["cpu_affinity"]} /etc/systemd/system/netdata.service.d/override.conf".split())
    print(f"=== [End] Setup: cpu-affinity of netdata ===")

def make_output_dir(cnt, num_memcached):
    print(f"=== [Start] Making output_dir {data_dir}/{str(num_memcached).zfill(3)}mcd ===")
    cmd = (
        f"mkdir -p {data_dir}/{cnt}/{str(num_memcached).zfill(3)}mcd"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Making output_dir {data_dir}/{str(num_memcached).zfill(3)}mcd ===")

def netdata_monitoring(cnt):
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### Netdata: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        for num_memcached in num_memcacheds:
            print()
            print(f"############## Running {num_memcached} servers ##########################")
            make_output_dir(cnt, num_memcached)
            run_netdata_server(num_memcached, metric)
            run_netdata_client(cnt, num_memcached, metric)
            stop_server_for_netdata()
            # needed to pkill memcached completely
            time.sleep(5)

def x_monitor_monitoring(cnt):
    for metric in metrics:
        print()
        print(f"#######################################################################################")
        print(f"##################### X-Monitor: Monitoring {metric} metrics ##########################")
        print(f"#######################################################################################")
        for num_memcached in num_memcacheds:
            print(f"############## Running {num_memcached} servers ##########################")
            make_output_dir(cnt, num_memcached)
            for x_monitor_interval in x_monitor_intervals:
                print(f"############## Interval {x_monitor_interval} ##########################")
                run_x_monitor_server(num_memcached, metric)
                run_x_monitor_client(cnt, num_memcached, metric, x_monitor_interval)
                stop_server_for_x_monitor()
                # needed to pkill memcached completely
                time.sleep(5)

def no_monitoring(cnt):
    print()
    print(f"############################################################################")
    print(f"############################# No-Monitoring ################################")
    print(f"############################################################################")
    for num_memcached in num_memcacheds:
        make_output_dir(cnt, num_memcached)
        run_memcached_for_no_monitor(num_memcached)
        run_mutilate_for_no_monitoring(cnt, num_memcached)
        stop_memcached()
        time.sleep(5)

def main():
    setup()
    for cnt in range(cnts):
        print(f"############################################################################")
        print(f"############################################################################")
        print(f"############################# Count: {cnt} #################################")
        print(f"############################################################################")
        print(f"############################################################################")
        no_monitoring(cnt)
        netdata_monitoring(cnt)
        x_monitor_monitoring(cnt)

if __name__ == "__main__":
    main()
