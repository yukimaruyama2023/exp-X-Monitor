import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
import datetime

############################################ Configuratin ###############################################
ismemcached = False # default is True. False means collecting Redis metrics
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

remote_host = "hamatora"
# not latency but throughput
if ismemcached:
    remote_mutilate_script_throughput = "/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/numa0/memcached/exp-throughput/"
else:
    remote_mutilate_script_throughput = "/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/numa0/redis/exp-throughput/"

remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
remote_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
stats_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/stats-command"
conf_root = "./conf"
log_script_path = "./scripts/"

# num_instances = [1, 5, 10]
num_instances = list(range(1, 13))
# num_instances = [4, 5, 12]
# num_instances = [12]
intervals = [1, 0.5, 0.001]
# intervals = [0.0002]
metrics = ["user", "kernel"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

if strict_comparison:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/only-go-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/no-plugin.conf"
else:
    user_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
    kernel_plugin_conf = f"{conf_root}/netdata/plugin/only-disable-go-plugin.conf"

if all_runs_in_0_4cores:
    data_dir = ( 
        f"{remote_data_root}/monitoring_throughput/memcached/strict-{strict_comparison}/all_runs_in_0_4cores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}" 
        if ismemcached 
        else f"{remote_data_root}/monitoring_throughput/redis/strict-{strict_comparison}/all_runs_in_0_4cores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
    )
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
        data_dir = ( 
            f"{remote_data_root}/monitoring_throughput/memcached/strict-{strict_comparison}/all_runs_in_allcores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}" 
            if ismemcached 
            else  f"{remote_data_root}/monitoring_throughput/redis/strict-{strict_comparison}/all_runs_in_allcores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
        )
        mcd_cpu_aff_for_no_monitor = "all-core-execute.sh"
        mcd_cpu_aff_for_netdata = "all-core-execute.sh"
        mcd_cpu_aff_for_x_monitor = "all-core-execute.sh"
        netdata_cpu_aff = (
            "let-netdata-allcore-prioritized.conf"
            if prioritized
            else "let-netdata-allcore.conf"
        )
    else:
        data_dir = (
                f"{remote_data_root}/monitoring_throughput/memcached/strict-{strict_comparison}/ntd_mcd_allcores-{mcd_in_allcores_for_x_monitor}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
                if ismemcached
                else f"{remote_data_root}/monitoring_throughput/redis/strict-{strict_comparison}/ntd_mcd_allcores-{mcd_in_allcores_for_x_monitor}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
        )
        if mcd_in_allcores_for_x_monitor:
            mcd_cpu_aff_for_x_monitor = "all-core-execute.sh"
            mcd_cpu_aff_for_no_monitor = "all-core-execute.sh"
        else:
            mcd_cpu_aff_for_x_monitor = "pin-core0-4-execute.sh"
            mcd_cpu_aff_for_no_monitor = "pin-core0-4-execute.sh"

        netdata_cpu_aff = "pin-netdata-core0.conf"
        mcd_cpu_aff_for_netdata = "pin-core1-5-execute.sh"

if ismemcached:
    if xdp_indirectcopy:
        xdp_user_met_program = "xdp_user_indirectcopy.sh"
    else:
        xdp_user_met_program = "xdp_user_directcopy.sh"
else:
    xdp_user_met_program = "xdp_user_indirectcopy_redis.sh"

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

def run_database_for_x_monitor(num_instance):
    print(f"=== [Start] Running Database {num_instance} instances, affinity is {mcd_cpu_aff_for_x_monitor} ===")
    if ismemcached:
        subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff_for_x_monitor} {num_instance}".split())
    else:
        subprocess.Popen(f"./conf/redis/{mcd_cpu_aff_for_x_monitor} {num_instance}".split())
    print(f"=== [End] Running Database {num_instance} instances, affinity is {mcd_cpu_aff_for_x_monitor} ===")

def run_database_for_netdata(num_instance):
    print(f"=== [Start] Running Database {num_instance} instances, affinity is {mcd_cpu_aff_for_netdata} ===")
    if ismemcached:
        subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff_for_netdata} {num_instance}".split())
    else:
        subprocess.Popen(f"./conf/redis/{mcd_cpu_aff_for_netdata} {num_instance}".split())
    print(f"=== [End] Running Database {num_instance} instances, affinity is {mcd_cpu_aff_for_netdata} ===")

def run_database_for_no_monitor(num_instance):
    print(f"=== [Start] Running Database {num_instance} instances, affinity is {mcd_cpu_aff_for_no_monitor} ===")
    if ismemcached:
        subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff_for_no_monitor} {num_instance}".split())
    else:
        subprocess.Popen(f"./conf/redis/{mcd_cpu_aff_for_no_monitor} {num_instance}".split())
    print(f"=== [End] Running Database {num_instance} instances, affinity is {mcd_cpu_aff_for_no_monitor} ===")

# kill x_monitor not mutilate
def stop_monitoring_client_for_netdata():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "client_netdata"])

def stop_monitoring_client_for_x_monitor():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "client_x-monitor"])

def stop_database():
    if ismemcached:
        subprocess.run("sudo pkill memcached".split())
    else:
        subprocess.run("sudo pkill redis".split())

def run_netdata(num_instance, metric):
    print(f"=== [Start] Running Netdata {num_instance} ===")
    # memcached_conf = f"{conf_root}/{str(num_instance).zfill(3)}mcd/go.d/memcached.conf"
    if ismemcached:
        memcached_conf = f"{conf_root}/netdata/go.d/num_mcd/{str(num_instance).zfill(3)}-memcached.conf"
        subprocess.run(f"sudo cp {memcached_conf} /etc/netdata/go.d/memcached.conf".split())
    else:
        memcached_conf = f"{conf_root}/netdata/go.d/num_redis/{str(num_instance).zfill(3)}-redis.conf"
        subprocess.run(f"sudo cp {memcached_conf} /etc/netdata/go.d/redis.conf".split())

    if metric == "user":
        subprocess.run(f"sudo cp {netdata_conf["user_plugin_conf"]} /etc/netdata/netdata.conf".split())
    else:
        subprocess.run(f"sudo cp {netdata_conf["kernel_plugin_conf"]} /etc/netdata/netdata.conf".split())
    subprocess.run(f"sudo systemctl daemon-reload".split())
    subprocess.run(f"sudo systemctl restart netdata".split())
    print(f"=== [End] Running Netdata {num_instance} ===")


def run_netdata_client_monitor(num_instance, metric, interval):
    print(f"=== [Start] Running monitoring client instance={num_instance} === ")
    if metric == "user":
        stdin_input = f"{interval}\n1\n"
    else:
        stdin_input = f"{interval}\n0\n"

    if ismemcached:
        client_script = "client_netdata"
    else:
        client_script = "client_netdata_redis"
    cmd = (
        f"cd {remote_monitoring_client} &&"
        # output file is test.csv
        f"numactl --cpunodebind=1 --membind=1 ./{client_script} test.csv"
    )
    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
    proc.stdin.write(stdin_input)
    proc.stdin.close()
    print(f"=== [End] Running monitoring client instance={num_instance} === ")


def load_xdp(metric, num_instance):
    if metric == "user":
        if ismemcached:
            if xdp_indirectcopy:
                c_name = "xdp_user_indirectcopy.c"
            else:
                c_name = "xdp_user_directcopy.c"
        else:
            c_name = "xdp_user_indirectcopy_redis.c"
        # c_name = "xdp_user_indirectcopy.c" if xdp_indirectcopy else "xdp_user_directcopy.c"
        c_file = os.path.join(x_monitor_root, c_name)
        with open(c_file, "r") as f:
            lines = f.readlines()
        with open(c_file, "w") as f:
            for line in lines:
                if line.startswith("#define NUM_APP"):
                    f.write(f"#define NUM_APP {num_instance}\n")
                else:
                    f.write(line)

    exe_script = xdp_user_met_program if metric == "user" else "xdp_kernel_directcopy.sh"
    script_path = os.path.join(x_monitor_root, exe_script)
    subprocess.run([script_path], cwd=x_monitor_root, check=True)
    time.sleep(5)

def detach_xdp():
    script_path = os.path.join(x_monitor_root, "off.sh")
    subprocess.run([script_path], cwd=x_monitor_root, check=True)

def run_x_monitor_client_monitor(num_instance, metric, interval):
    print(f"=== [Start] Running monitoring client instance={num_instance} === ")
    stdin_input = f"{interval}\n"
    if ismemcached:
        client_script = "client_x-monitor"
    else:
        client_script = "client_x-monitor_redis"

    cmd = (
        f"cd {remote_monitoring_client} &&"
        # output file is test.csv
        f"numactl --cpunodebind=1 --membind=1 ./{client_script} test.csv"
    )

    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
    proc.stdin.write(stdin_input)
    proc.stdin.close()
    print(f"=== [End] Running monitoring client instance={num_instance} === ")


def run_mutilate_for_netdata(cnt, num_instance, metric, interval):
    print(f"=== [Start] Running mutilate {num_instance} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    if ismemcached:
        cmd = (
            f"{remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_instance).zfill(3)}mcd/netdata-{metric}metrics-{num_instance}mcd-interval{interval}.txt"
        )
        subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}mcd-load.sh".split())
    else:
        cmd = (
            f"{remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}redis-run.sh > {data_dir}/{cnt}/{str(num_instance).zfill(3)}redis/netdata-{metric}metrics-{num_instance}redis-interval{interval}.txt"
        )
        subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}redis-load.sh".split())
    run_netdata_client_monitor(num_instance, metric, interval)
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Running mutilate {num_instance} ===")

def run_mutilate_for_x_monitor(cnt, num_instance, metric, interval):
    print(f"=== [Start] Running mutilate {num_instance} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    if ismemcached:
        cmd = (
            f"{remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_instance).zfill(3)}mcd/xmonitor-{metric}metrics-{num_instance}mcd-interval{interval}.txt"
        )
        subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}mcd-load.sh".split())
    else:
        cmd = (
            f"{remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}redis-run.sh > {data_dir}/{cnt}/{str(num_instance).zfill(3)}redis/xmonitor-{metric}metrics-{num_instance}redis-interval{interval}.txt"
        )
        subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}redis-load.sh".split())
    run_x_monitor_client_monitor(num_instance, metric, interval)
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Running mutilate {num_instance} ===")


def run_mutilate_for_no_monitoring(cnt, num_instance):
    print(f"=== [Start] Running mutilate {num_instance} ===")
    # 1. execute path is remote_mutilate_script_throughput not ..latency
    # 2. specify output file
    if ismemcached:
        cmd = (
            f"{remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}mcd-run.sh > {data_dir}/{cnt}/{str(num_instance).zfill(3)}mcd/no_monitoring-{num_instance}mcd.txt"
        )
        subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}mcd-load.sh".split())
    else:
        cmd = (
            f"{remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}redis-run.sh > {data_dir}/{cnt}/{str(num_instance).zfill(3)}redis/no_monitoring-{num_instance}redis.txt"
        )
        subprocess.run(f"ssh {remote_host} {remote_mutilate_script_throughput}/{str(num_instance).zfill(3)}redis-load.sh".split())

    subprocess.run(f"ssh {remote_host} {cmd}".split())

    print(f"=== [End] Running mutilate {num_instance} ===")

def run_stats(num_instance, interval):
    print(f"=== [Start] Running memcached_stats_loop interval={interval} on core 5 ===")
    cmd = [
        "taskset", "-c", "5",
        f"{stats_root}/memcached_stats_loop",
        str(num_instance),
        str(interval),
    ]
    subprocess.Popen(cmd)

def stop_stats():
    print("=== [Stop] memcached_stats_loop ===")
    subprocess.run(["pkill", "-f", "memcached_stats_loop"])

def run_INFO(num_instance, interval):
    print(f"=== [Start] Running redis_info_loop interval={interval} on core 5 ===")
    cmd = [
        "taskset", "-c", "5",
        f"{stats_root}/redis_info_loop",
        str(num_instance),
        str(interval),
    ]
    subprocess.Popen(cmd)

def stop_INFO():
    print("=== [Stop] redis_info_loop ===")
    subprocess.run(["pkill", "-f", "redis_info_loop"])

###############################

def run_netdata_server(num_instance, metric):
    run_database_for_netdata(num_instance)
    run_netdata(num_instance, metric)

def run_netdata_client(cnt, num_instance, metric, interval):
    # monitoring client is called inside run_mutilate_for_netdata
    run_mutilate_for_netdata(cnt, num_instance, metric, interval)

def run_x_monitor_server(num_instance, metric):
    run_database_for_x_monitor(num_instance)

def run_x_monitor_client(cnt, num_instance, metric, interval):
    load_xdp(metric, num_instance)
    # monitoring client is called inside run_mutilate_for_x_monitor
    run_mutilate_for_x_monitor(cnt, num_instance, metric, interval)
    detach_xdp()

def stop_server_for_netdata():
    stop_monitoring_client_for_netdata()
    if (all_runs_in_0_4cores):
        # this might not be needed. stop_database() have already killed memcached_stats
        if ismemcached:
            stop_stats()
        else:
            stop_INFO();
    stop_database()


def stop_server_for_x_monitor():
    stop_monitoring_client_for_x_monitor()
    stop_database()

#################################

def setup():
    print(f"=== [Start] Setup: cpu-affinity of netdata ===")
    subprocess.run(f"sudo cp {netdata_conf["cpu_affinity"]} /etc/systemd/system/netdata.service.d/override.conf".split())
    print(f"=== [End] Setup: cpu-affinity of netdata ===")

# def make_output_dir(cnt, num_instance):
#     print(f"=== [Start] Making output_dir {data_dir}/{str(num_instance).zfill(3)}mcd ===")
#     cmd = (
#         f"mkdir -p {data_dir}/{cnt}/{str(num_instance).zfill(3)}mcd"
#     )
#     subprocess.run(f"ssh {remote_host} {cmd}".split())
#     print(f"=== [End] Making output_dir {data_dir}/{str(num_instance).zfill(3)}mcd ===")

def make_output_dir(cnt, num_instance):
    if ismemcached:
        subdir = f"{str(num_instance).zfill(3)}mcd"
    else:
        subdir = f"{str(num_instance).zfill(3)}redis"

    print(f"=== [Start] Making output_dir {data_dir}/{cnt}/{subdir} ===")
    cmd = f"mkdir -p {data_dir}/{cnt}/{subdir}"
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Making output_dir {data_dir}/{cnt}/{subdir} ===")

def netdata_monitoring(cnt):
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### Netdata: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        log_to_slack(f"============================ Netdcata: Monitoring {metric} metrics ===================")
        for num_instance in num_instances:
            log_to_slack(f"------- Running {num_instance} servers ----------")
            print()
            print(f"############## Running {num_instance} servers ##########################")
            make_output_dir(cnt, num_instance)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_netdata_server(num_instance, metric)
                if all_runs_in_0_4cores and metric == "user":
                    if ismemcached:
                        run_stats(num_instance, interval)
                    else:
                        run_INFO(num_instance, interval)
                run_netdata_client(cnt, num_instance, metric, interval)
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
        for num_instance in num_instances:
            log_to_slack(f"------- Running {num_instance} metrics ----------")
            print(f"############## Running {num_instance} servers ##########################")
            make_output_dir(cnt, num_instance)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_x_monitor_server(num_instance, metric)
                run_x_monitor_client(cnt, num_instance, metric, interval)
                stop_server_for_x_monitor()
                # needed to pkill memcached completely
                time.sleep(5)

def no_monitoring(cnt):
    print()
    print(f"############################################################################")
    print(f"############################# No-Monitoring ################################")
    print(f"############################################################################")
    log_to_slack(f"============================ No-Monitoring ===================")
    for num_instance in num_instances:
        log_to_slack(f"------- Running {num_instance} servers ----------")
        print(f"############## Running {num_instance} servers ##########################")
        make_output_dir(cnt, num_instance)
        run_database_for_no_monitor(num_instance)
        run_mutilate_for_no_monitoring(cnt, num_instance)
        stop_database()
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
