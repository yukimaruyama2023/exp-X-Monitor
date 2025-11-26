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
remote_mutilate_script_throughput = "/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/numa0/exp-throughput/"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
remote_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
stats_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/stats-command"
conf_root = "./conf"
log_script_path = "./scripts/"

# num_memcacheds = [1, 5, 10]
# num_memcacheds = list(range(1, 13))
# num_memcacheds = list(range(1, 12))
num_memcacheds = [4, 5, 12]
intervals = [1, 0.5, 0.001]
metrics = ["user", "kernel"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


############################################ Configuratin ###############################################
strict_comparison = True # default is False, which means almost all plugin runs
prioritized = False # default is False. This is enabled when all_runs_in_allcores is True
xdp_indirectcopy = True # default is True, but previous experiments are conducted as false (2025-11-12)
all_runs_in_0_4cores = True #  (2025-11-25)
cnts = 5
#########################################################################################################
# fixed configuration
all_runs_in_allcores = True # default is False; this is additonal configuration. 
mcd_in_allcores_for_x_monitor = True # default is False; mcd for x_monitor runs in core 1-5, NOTE: you cannot configure mcd and netdata cpu affinity unlike latency experiment except for the case all_runs_in_allcores is True
#########################################################################################################


if strict_comparison:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/only-go-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/no-plugin.conf"
else:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/only-disable-go-plugin.conf"

if all_runs_in_0_4cores:
    data_dir = f"{remote_data_root}/monitoring_throughput/strict-{strict_comparison}/all_runs_in_0_4cores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
    mcd_cpu_aff_for_no_monitor = "pin-core0-4-execute.sh"
    mcd_cpu_aff_for_netdata = "pin-core0-4-execute.sh"
    mcd_cpu_aff_for_x_monitor = "pin-core0-4-execute.sh"
    netdata_cpu_aff = (
        "pin-netdata-core0-4-prioritized.conf"
        if prioritized
        else "pin-netdata-core0-4.conf"
    )

else:
    if all_runs_in_allcores:
        data_dir = f"{remote_data_root}/monitoring_throughput/strict-{strict_comparison}/all_runs_in_allcores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
        mcd_cpu_aff_for_no_monitor = "all-core-execute.sh"
        mcd_cpu_aff_for_netdata = "all-core-execute.sh"
        mcd_cpu_aff_for_x_monitor = "all-core-execute.sh"
        netdata_cpu_aff = (
            "let-netdata-allcore-prioritized.conf"
            if prioritized
            else "let-netdata-allcore.conf"
        )
    else:
        data_dir = f"{remote_data_root}/monitoring_throughput/strict-{strict_comparison}/ntd_mcd_allcores-{mcd_in_allcores_for_x_monitor}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
        if mcd_in_allcores_for_x_monitor:
            mcd_cpu_aff_for_x_monitor = "all-core-execute.sh"
            mcd_cpu_aff_for_no_monitor = "all-core-execute.sh"
        else:
            mcd_cpu_aff_for_x_monitor = "pin-core0-4-execute.sh"
            mcd_cpu_aff_for_no_monitor = "pin-core0-4-execute.sh"

        netdata_cpu_aff = "pin-netdata-core0.conf"
        mcd_cpu_aff_for_netdata = "pin-core1-5-execute.sh"

if xdp_indirectcopy:
    xdp_user_met_program = "xdp_user_indirectcopy.sh"
else:
    xdp_user_met_program = "xdp_user_directcopy.sh"

netdata_conf = {
    "cpu_affinity": f"{conf_root}/netdata/cpu-affinity/{netdata_cpu_aff}",
    "user_plugin_conf": user_plugin_conf,
    "kernel_plugin_conf": kernel_plugin_conf,
}


def log_to_slack(message):
    try:
        subprocess.run(
            [f"{log_script_path}/log.sh", message],
            check=True
        )
    except Exception as e:
        print(f"[WARN] Failed to send message to slack {e}", file=sys.stderr)

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
    subprocess.run(f"sudo systemctl daemon-reload".split())
    subprocess.run(f"sudo systemctl restart netdata".split())
    print(f"=== [End] Running Netdata {num_memcached} ===")


def run_netdata_client_monitor(num_memcached, metric, interval):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    if metric == "user":
        stdin_input = f"{interval}\n1\n"
    else:
        stdin_input = f"{interval}\n0\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        # output file is test.csv
        f"numactl --cpunodebind=1 --membind=1 ./client_netdata test.csv"
    )
    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
    proc.stdin.write(stdin_input)
    proc.stdin.close()
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

def run_x_monitor_client_monitor(num_memcached, metric, interval):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    stdin_input = f"{interval}\n"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        # output file is test.csv
        f"numactl --cpunodebind=1 --membind=1 ./client_x-monitor test.csv")
    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
    proc.stdin.write(stdin_input)
    proc.stdin.close()
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")


def run_mutilate_for_netdata(cnt, num_memcached, metric, interval):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    cmd = (
        f"{remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_memcached).zfill(3)}mcd/netdata-{metric}metrics-{num_memcached}mcd-interval{interval}.txt"
    )
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-load.sh".split())
    run_netdata_client_monitor(num_memcached, metric, interval)
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Running mutilate {num_memcached} ===")

def run_mutilate_for_x_monitor(cnt, num_memcached, metric, interval):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    cmd = (
        f"{remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_memcached).zfill(3)}mcd/xmonitor-{metric}metrics-{num_memcached}mcd-interval{interval}.txt"
    )
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_memcached).zfill(3)}mcd-load.sh".split())
    run_x_monitor_client_monitor(num_memcached, metric, interval)
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

def run_stats(num_memcached, interval):
    print(f"=== [Start] Running memcached_stats_loop interval={interval} on core 5 ===")
    cmd = [
        "taskset", "-c", "5",
        f"{stats_root}/memcached_stats_loop",
        str(num_memcached),
        str(interval),
    ]
    subprocess.Popen(cmd)

def stop_stats():
    print("=== [Stop] memcached_stats_loop ===")
    subprocess.run(["pkill", "-f", "memcached_stats_loop"])

###############################

def run_netdata_server(num_memcached, metric):
    run_memcached_for_netdata(num_memcached)
    run_netdata(num_memcached, metric)

def run_netdata_client(cnt, num_memcached, metric, interval):
    # monitoring client is called inside run_mutilate_for_netdata
    run_mutilate_for_netdata(cnt, num_memcached, metric, interval)

def run_x_monitor_server(num_memcached, metric):
    run_memcached_for_x_monitor(num_memcached)

def run_x_monitor_client(cnt, num_memcached, metric, interval):
    load_xdp(metric, num_memcached)
    # monitoring client is called inside run_mutilate_for_x_monitor
    run_mutilate_for_x_monitor(cnt, num_memcached, metric, interval)
    detach_xdp()

def stop_server_for_netdata():
    stop_monitoring_client_for_netdata()
    if (all_runs_in_0_4cores):
        # this might not be needed. stop_memcached() have already killed memcached_stats
        stop_stats()
    stop_memcached()


def stop_server_for_x_monitor():
    stop_monitoring_client_for_x_monitor()
    stop_memcached()

#################################

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
        log_to_slack(f"============================ Netdcata: Monitoring {metric} metrics ===================")
        for num_memcached in num_memcacheds:
            log_to_slack(f"------- Running {num_memcached} servers ----------")
            print()
            print(f"############## Running {num_memcached} servers ##########################")
            make_output_dir(cnt, num_memcached)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_netdata_server(num_memcached, metric)
                if all_runs_in_0_4cores and metric == "user":
                    run_stats(num_memcached, interval)
                run_netdata_client(cnt, num_memcached, metric, interval)
                stop_server_for_netdata()
                # needed to pkill memcached completely
                time.sleep(5)

def x_monitor_monitoring(cnt):
    for metric in metrics:
        print()
        print(f"#######################################################################################")
        print(f"##################### X-Monitor: Monitoring {metric} metrics ##########################")
        print(f"#######################################################################################")
        log_to_slack(f"============================ X-Monitor: Monitoring {metric} metrics ===================")
        for num_memcached in num_memcacheds:
            log_to_slack(f"------- Running {num_memcached} metrics ----------")
            print(f"############## Running {num_memcached} servers ##########################")
            make_output_dir(cnt, num_memcached)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_x_monitor_server(num_memcached, metric)
                run_x_monitor_client(cnt, num_memcached, metric, interval)
                stop_server_for_x_monitor()
                # needed to pkill memcached completely
                time.sleep(5)

def no_monitoring(cnt):
    print()
    print(f"############################################################################")
    print(f"############################# No-Monitoring ################################")
    print(f"############################################################################")
    log_to_slack(f"============================ No-Monitoring ===================")
    for num_memcached in num_memcacheds:
        log_to_slack(f"------- Running {num_memcached} servers ----------")
        print(f"############## Running {num_memcached} servers ##########################")
        make_output_dir(cnt, num_memcached)
        run_memcached_for_no_monitor(num_memcached)
        run_mutilate_for_no_monitoring(cnt, num_memcached)
        stop_memcached()
        time.sleep(5)

def main():
    log_to_slack("============================ Experiment Starts!!!! =======================================")
    log_to_slack(f"============================ data_dir is {data_dir} =======================================")
    setup()
    for cnt in range(cnts):
        print(f"############################################################################")
        print(f"############################################################################")
        print(f"############################# Count: {cnt} #################################")
        print(f"############################################################################")
        print(f"############################################################################")
        log_to_slack(f"####################### Count {cnt} ######################")

        no_monitoring(cnt)
        netdata_monitoring(cnt)
        x_monitor_monitoring(cnt)

    log_to_slack("============================All experiment finished!!!!=======================================")

if __name__ == "__main__":
    main()
