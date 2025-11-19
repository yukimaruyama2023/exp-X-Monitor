import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
import datetime

############################################ Configuratin ###############################################
strict_comparison = True # default is False, which means almost all plugin runs
prioritized = False # default is False. In true case, ntd_mcd_in_allcores set to be True
ntd_mcd_in_allcores = True # default is False, which means 1 netdata run on core 0 and mcd run on core 1-5
xdp_indirectcopy = True # default is True, but previous experiments are conducted as false (2025-11-12)
##############################################################################################################
# mutilate_num_thread = 35 # default is True, but previous experiments are conducted as false (2025-11-12) # NOTE: artifact configuration
###############################################################################################################


remote_host = "hamatora"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
remote_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
conf_root = "./conf"
# remote_mutilate_script_latency = f"/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/{mutilate_num_thread}thread/exp-latency/" # NOTE: artifact configuration
# remote_mutilate_script_latency = f"/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/numa0/exp-latency/"
remote_mutilate_script_latency = f"/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/mut0-46/exp-latency/"
log_script_path = "./scripts/"

num_memcacheds = [10]
# num_memcacheds = list(range(1, 13))
# x_monitor_intervals = [1, 0.1, 0.01]
# x_monitor_intervals = [0.001, 0.0005, 0.0001]
x_monitor_intervals = [1, 0.001, 0.0002]
# x_monitor_intervals = [0.0001]
# metrics = ["user", "kernel"]
metrics = ["kernel", "user"]
# metrics = ["kernel"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")



if strict_comparison:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/only-go-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/no-plugin.conf"
else:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/only-disable-go-plugin.conf"

# prioritized のときは「必ず all-core」で実験する
if prioritized:
    ntd_mcd_in_allcores = True

if ntd_mcd_in_allcores:
    mcd_cpu_aff = "all-core-execute.sh"
    netdata_cpu_aff = (
        "let-netdata-allcore-prioritized.conf"
        if prioritized
        else "let-netdata-allcore.conf"
    )
else:
    mcd_cpu_aff = "pin-core1-5-execute.sh"
    netdata_cpu_aff = "pin-netdata-core0.conf"

netdata_conf = {
    "cpu_affinity": f"{conf_root}/netdata/cpu-affinity/{netdata_cpu_aff}",
    "user_plugin_conf": user_plugin_conf,
    "kernel_plugin_conf": kernel_plugin_conf,
}

if xdp_indirectcopy:
    xdp_user_met_program = "xdp_user_indirectcopy.sh"
else:
    xdp_user_met_program = "xdp_user_directcopy.sh"

# data_dir = f"{remote_data_root}/monitoring_latency/strict-{strict_comparison}/prioritized-{prioritized}/ntd_mcd_allcores-{ntd_mcd_in_allcores}/xdp_indirectcopy-{xdp_indirectcopy}/mutilate-{mutilate_num_thread}thread/{timestamp}"  # NOTE: artifact configuration
data_dir = f"{remote_data_root}/monitoring_latency/strict-{strict_comparison}/prioritized-{prioritized}/ntd_mcd_allcores-{ntd_mcd_in_allcores}/xdp_indirectcopy-{xdp_indirectcopy}/numa0/{timestamp}"

def log_to_slack(message):
    try:
        subprocess.run(
            [f"{log_script_path}/log.sh", message],
            check=True
        )
    except Exception as e:
        print(f"[WARN] Failed to send message to slack {e}", file=sys.stderr)


def run_memcached(num_memcached):
    print(f"=== [Start] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff} ===")
    subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff} {num_memcached}".split())
    print(f"=== [End] Running Memcached {num_memcached} instances, affinity is {mcd_cpu_aff} ===")

def stop_mutilate():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "mutilate"])

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
    subprocess.run(f"sudo systemctl daemon-reload".split())
    subprocess.run(f"sudo systemctl restart netdata".split())
    print(f"=== [End] Running Netdata {num_memcached} ===")

def run_mutilate(num_memcached):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_memcached).zfill(3)}mcd-load.sh".split())
    subprocess.Popen(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_memcached).zfill(3)}mcd-run.sh".split())
    print(f"=== [End] Running mutilate {num_memcached} ===")

def run_netdata_client_monitor(num_memcached, metric):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    if metric == "user":
        stdin_input = "1\n1\n"
    else:
        stdin_input = "1\n0\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        f"taskset -c 47 ./client_netdata {data_dir}/{str(num_memcached).zfill(3)}mcd/netdata-{metric}metrics-{num_memcached}mcd.csv"
    )
    subprocess.run(f"ssh {remote_host} {cmd}".split(),
                   input=stdin_input,
                   text=True
    )
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def load_xdp(metric, num_memcached):
    if metric == "user":
        c_name = "xdp_user_indirectcopy.c" if xdp_indirectcopy else "xdp_user_directcopy.c"
        c_file = os.path.join(x_monitor_root, c_name)
        with open(c_file, "r") as f:
            lines = f.readlines()
        with open(c_file, "w") as f:
            for line in lines:
                if line.startswith("#define NUM_APP"):
                    f.write(f"#define NUM_APP {num_memcached}\n")
                else:
                    f.write(line)

    exe_script = xdp_user_met_program if metric == "user" else "xdp_kernel_directcopy.sh"
    script_path = os.path.join(x_monitor_root, exe_script)
    subprocess.run([script_path], cwd=x_monitor_root, check=True)
    time.sleep(5)

def detach_xdp():
    script_path = os.path.join(x_monitor_root, "off.sh")
    subprocess.run([script_path], cwd=x_monitor_root, check=True)
#
# def run_x_monitor_client_monitor(num_memcached, metric, x_monitor_interval):
#     print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
#     if x_monitor_interval == 1:
#         stdin_input = "1\n"
#     elif x_monitor_interval == 0.1:
#         stdin_input = "0.1\n"
#     else:
#         stdin_input = "0.01\n"
#     cmd = (
#         f"cd {remote_monitoring_client} &&"
#         f"./client_x-monitor {data_dir}/{str(num_memcached).zfill(3)}mcd/xmonitor-{metric}metrics-{num_memcached}mcd-interval{x_monitor_interval}.csv"
#     )
#     subprocess.run(f"ssh {remote_host} {cmd}".split(),
#                    input=stdin_input,
#                    text=True
#     )
#     print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def run_x_monitor_client_monitor(num_memcached, metric, x_monitor_interval):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    stdin_input = f"{x_monitor_interval}\n"

    cmd = (
        f"cd {remote_monitoring_client} &&"
        f"taskset -c 47 ./client_x-monitor {data_dir}/{str(num_memcached).zfill(3)}mcd/"
        f"xmonitor-{metric}metrics-{num_memcached}mcd-interval{x_monitor_interval}.csv"
    )
    subprocess.run(
        f"ssh {remote_host} {cmd}".split(),
        input=stdin_input,
        text=True,
    )
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def run_netdata_server(num_memcached, metric):
    run_memcached(num_memcached)
    run_netdata(num_memcached, metric)

def run_netdata_client(num_memcached, metric):
    run_mutilate(num_memcached)
    run_netdata_client_monitor(num_memcached, metric)

def run_x_monitor_server(num_memcached, metric):
    run_memcached(num_memcached)

def run_x_monitor_client(num_memcached, metric, x_monitor_interval):
    load_xdp(metric, num_memcached)
    run_mutilate(num_memcached)
    run_x_monitor_client_monitor(num_memcached, metric, x_monitor_interval)
    detach_xdp()

def stop_server():
    stop_mutilate()
    stop_memcached()

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
        log_to_slack(f"=====================Netdata: Monitoring {metric} metrics=======================")
        for num_memcached in num_memcacheds:
            print()
            print(f"############## Running {num_memcached} servers ##########################")
            log_to_slack(f"Running {num_memcached} metrics")
            make_output_dir(num_memcached)
            run_netdata_server(num_memcached, metric)
            run_netdata_client(num_memcached, metric)
            stop_server()
            # needed to pkill memcached completely
            time.sleep(5)

def x_monitor_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### X-Monitor: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        log_to_slack(f"============================X-Monitor: Monitoring {metric} metrics===================")
        for num_memcached in num_memcacheds:
            print(f"############## Running {num_memcached} servers ##########################")
            log_to_slack(f"Runnign {num_memcached} servers")
            make_output_dir(num_memcached)
            for x_monitor_interval in x_monitor_intervals:
                print(f"############## Interval {x_monitor_interval} ##########################")
                log_to_slack(f"Interval {x_monitor_interval}")
                run_x_monitor_server(num_memcached, metric)
                run_x_monitor_client(num_memcached, metric, x_monitor_interval)
                stop_server()
                # needed to pkill memcached completely
                time.sleep(5)

def main():
    log_to_slack("============================ Experiment Starts!!!! =======================================")
    log_to_slack(f"============================ data_dir is {data_dir} =======================================")
    setup()
    netdata_monitoring()
    x_monitor_monitoring()
    log_to_slack("============================All experiment finished!!!!=======================================")

if __name__ == "__main__":
    main()
