import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
import datetime

############################################ Configuratin ###############################################
ismemcached = True # default is True. False means collecting Redis metrics
strict_comparison = True # default is False, which means almost all plugin runs. now true 2025-11-20
prioritized = False # default is False. In true case, ntd_mcd_in_allcores set to be True
xdp_indirectcopy = True # default is True, but previous experiments are conducted as false (2025-11-12)
all_runs_in_0_4cores = True #  (2025-11-25)
##############################################################################################################
# fixed configuratin. 2025-11-20
ntd_mcd_in_allcores = True # default is False, which means 1 netdata run on core 0 and mcd run on core 1-5, now fixed to True
# mutilate_num_thread = 35 # default is True, but previous experiments are conducted as false (2025-11-12) # NOTE: artifact configuration
###############################################################################################################


remote_host = "hamatora"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
remote_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
stats_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/stats-command"
conf_root = "./conf"
# remote_mutilate_script_latency = f"/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/{mutilate_num_thread}thread/exp-latency/" # NOTE: artifact configuration
remote_mutilate_script_latency = f"/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/numa0/exp-latency/"
remote_redisbench_script_latency = "/home/maruyama/workspace/exp-X-Monitor/conf/redisbench/exp-latency/"
log_script_path = "./scripts/"

# num_instances = [1, 5, 10]
num_instances = [12]
# num_instances = list(range(1, 13))
# intervals = [1, 0.1, 0.01]
# intervals = [0.001, 0.0005, 0.0001]
intervals = [0.001]
# intervals = [0.0001]
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

if all_runs_in_0_4cores:
    data_dir = ( f"{remote_data_root}/monitoring_latency/memcached/strict-{strict_comparison}/all_runs_in_0_4cores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
        if ismemcached
        else f"{remote_data_root}/monitoring_latency/redis/strict-{strict_comparison}/all_runs_in_0_4cores/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"
    )

    mcd_cpu_aff = "pin-core0-4-execute.sh"
    netdata_cpu_aff = (
    "pin-netdata-core0-4-prioritized.conf"
        if prioritized
        else "pin-netdata-core0-4.conf"
    )

else:
    # prioritized のときは「必ず all-core」で実験する
    data_dir = ( f"{remote_data_root}/monitoring_latency/memcached/strict-{strict_comparison}/ntd_mcd_allcores-{ntd_mcd_in_allcores}/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/numa0/{timestamp}"
        if ismemcached
        else f"{remote_data_root}/monitoring_latency/redis/strict-{strict_comparison}/ntd_mcd_allcores-{ntd_mcd_in_allcores}/prioritized-{prioritized}/xdp_indirectcopy-{xdp_indirectcopy}/numa0/{timestamp}"

    )
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

if ismemcached:
    if xdp_indirectcopy:
        xdp_user_met_program = "xdp_user_indirectcopy.sh"
    else:
        xdp_user_met_program = "xdp_user_directcopy.sh"
else:
    xdp_user_met_program = "xdp_user_indirectcopy_redis.sh"

# data_dir = f"{remote_data_root}/monitoring_latency/strict-{strict_comparison}/prioritized-{prioritized}/ntd_mcd_allcores-{ntd_mcd_in_allcores}/xdp_indirectcopy-{xdp_indirectcopy}/mutilate-{mutilate_num_thread}thread/{timestamp}"  # NOTE: artifact configuration

def log_to_slack(message):
    try:
        subprocess.run(
            [f"{log_script_path}/log.sh", message],
            check=True
        )
    except Exception as e:
        print(f"[WARN] Failed to send message to slack {e}", file=sys.stderr)


def run_database(num_instance):
    print(f"=== [Start] Running Database {num_instance} instances, affinity is {mcd_cpu_aff} ===")
    if ismemcached:
        subprocess.Popen(f"./conf/memcached/{mcd_cpu_aff} {num_instance}".split())
    else:
        subprocess.Popen(f"./conf/redis/{mcd_cpu_aff} {num_instance}".split())

    print(f"=== [End] Running Database {num_instance} instances, affinity is {mcd_cpu_aff} ===")

def stop_mutilate():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "mutilate"])

def stop_redisbench():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "redis-benchmark"])

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

def run_mutilate(num_instance):
    print(f"=== [Start] Running mutilate {num_instance} ===")
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_instance).zfill(3)}mcd-load.sh".split())
    subprocess.Popen(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_instance).zfill(3)}mcd-run.sh".split())
    print(f"=== [End] Running mutilate {num_instance} ===")

def run_redisbench(num_instance):
    print(f"=== [Start] Running redisbench {num_instance} ===")
    subprocess.run(f"ssh {remote_host} {remote_redisbench_script_latency}/{str(num_instance).zfill(3)}redis-load.sh".split())
    subprocess.Popen(f"ssh {remote_host} {remote_redisbench_script_latency}/{str(num_instance).zfill(3)}redis-run.sh".split())
    print(f"=== [End] Running redisbench {num_instance} ===")


def run_netdata_client_monitor(num_instance, metric, interval):
    print(f"=== [Start] Running monitoring client instance={num_instance} === ")
    if metric == "user":
        stdin_input = f"{interval}\n1\n"
    else:
        stdin_input = f"{interval}\n0\n"
    if ismemcached:
        client_script = "client_netdata_for_latency"
        cmd = (
            f"cd {remote_monitoring_client} &&"
            f"numactl --cpunodebind=1 --membind=1 ./{client_script} {data_dir}/{str(num_instance).zfill(3)}mcd/"
            f"netdata-{metric}metrics-{num_instance}mcd-interval{interval}.csv"
        )
    else:
        client_script = "client_netdata_redis_for_latency"
        cmd = (
            f"cd {remote_monitoring_client} &&"
            f"numactl --cpunodebind=1 --membind=1 ./{client_script} {data_dir}/{str(num_instance).zfill(3)}redis/"
            f"netdata-{metric}metrics-{num_instance}redis-interval{interval}.csv"
        )

    subprocess.run(f"ssh {remote_host} {cmd}".split(),
                   input=stdin_input,
                   text=True
    )
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
        client_script = "client_x-monitor_for_latency"
        cmd = (
            f"cd {remote_monitoring_client} &&"
            f"numactl --cpunodebind=1 --membind=1 ./{client_script} {data_dir}/{str(num_instance).zfill(3)}mcd/"
            f"xmonitor-{metric}metrics-{num_instance}mcd-interval{interval}.csv"
        )
    else:
        client_script = "client_x-monitor_redis_for_latency"
        cmd = (
            f"cd {remote_monitoring_client} &&"
            f"numactl --cpunodebind=1 --membind=1 ./{client_script} {data_dir}/{str(num_instance).zfill(3)}redis/"
            f"xmonitor-{metric}metrics-{num_instance}redis-interval{interval}.csv"
        )

    subprocess.run(
        f"ssh {remote_host} {cmd}".split(),
        input=stdin_input,
        text=True,
    )
    print(f"=== [End] Running monitoring client instance={num_instance} === ")

def run_stats(num_instance, interval):
    print(f"=== [Start] Running memcached_stats_loop interval={interval} on core 5 ===")
    cmd = [
        "taskset", "-c", "5",
        f"{stats_root}/memcached_stats_loop",
        str(num_instance),
        str(interval),
    ]
    subprocess.Popen(cmd)

def run_INFO(num_instance, interval):
    print(f"=== [Start] Running redis_info_loop interval={interval} on core 5 ===")
    cmd = [
        "taskset", "-c", "5",
        f"{stats_root}/redis_info_loop",
        str(num_instance),
        str(interval),
    ]
    subprocess.Popen(cmd)

def stop_stats():
    print("=== [Stop] memcached_stats_loop ===")
    subprocess.run(["pkill", "-f", "memcached_stats_loop"])

def stop_INFO():
    print("=== [Stop] redis_info_loop ===")
    subprocess.run(["pkill", "-f", "redis_info_loop"])

########################

def run_netdata_server(num_instance, metric):
    run_database(num_instance)
    run_netdata(num_instance, metric)

def run_netdata_client(num_instance, metric, interval):
    if ismemcached:
        run_mutilate(num_instance)
    else:
        run_redisbench(num_instance)
    run_netdata_client_monitor(num_instance, metric, interval)

def run_x_monitor_server(num_instance, metric):
    run_database(num_instance)

def run_x_monitor_client(num_instance, metric, interval):
    load_xdp(metric, num_instance)
    if ismemcached:
        run_mutilate(num_instance)
    else:
        run_redisbench(num_instance)
    run_x_monitor_client_monitor(num_instance, metric, interval)
    detach_xdp()

def stop_server():
    if ismemcached:
        stop_mutilate()
    else:
        stop_redisbench()
    if (all_runs_in_0_4cores):
        # this might not be needed. stop_database() have already killed memcached_stats
        if ismemcached:
            stop_stats()
        else:
            stop_INFO()
    stop_database()

########################

def setup():
    print(f"=== [Start] Setup: cpu-affinity of netdata ===")
    subprocess.run(f"sudo cp {netdata_conf["cpu_affinity"]} /etc/systemd/system/netdata.service.d/override.conf".split())
    print(f"=== [End] Setup: cpu-affinity of netdata ===")

def make_output_dir(num_instance):
    if ismemcached:
        subdir = f"{str(num_instance).zfill(3)}mcd"
    else:
        subdir = f"{str(num_instance).zfill(3)}redis"

    print(f"=== [Start] Making output_dir {data_dir}/{subdir} ===")
    cmd = f"mkdir -p {data_dir}/{subdir}"
    subprocess.run(f"ssh {remote_host} {cmd}".split())
    print(f"=== [End] Making output_dir {data_dir}/{subdir} ===")

def netdata_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### Netdata: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        log_to_slack(f"===================== Netdata: Monitoring {metric} metrics =======================")
        for num_instance in num_instances:
            print()
            print(f"############## Running {num_instance} servers ##########################")
            log_to_slack(f"-------------------Running {num_instance} metrics--------------")
            make_output_dir(num_instance)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_netdata_server(num_instance, metric)
                if all_runs_in_0_4cores and metric == "user":
                    if ismemcached:
                        run_stats(num_instance, interval)
                    else:
                        run_INFO(num_instance, interval)
                run_netdata_client(num_instance, metric, interval)
                stop_server()
                # needed to pkill memcached completely
                time.sleep(5)

def x_monitor_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### X-Monitor: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        log_to_slack(f"============================ X-Monitor: Monitoring {metric} metrics ===================")
        for num_instance in num_instances:
            print(f"############## Running {num_instance} servers ##########################")
            log_to_slack(f"------------------Runnign {num_instance} servers----------------")
            make_output_dir(num_instance)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_x_monitor_server(num_instance, metric)
                run_x_monitor_client(num_instance, metric, interval)
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
