import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
import datetime

remote_host = "hamatora"
# TODO: change mutialte mutilate directory
# TODO: mutilate は消しちゃって良い．
remote_mutilate_script_latency = "/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/numa0/exp-cpuusage/"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
local_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
stats_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/stats-command"
conf_root = "./conf"
log_script_path = "./scripts/"

# num_instances = [1, 5, 10]
# num_instances = list(range(1, 13))
# num_instances = [12]
num_instances = [12]
# intervals = [1, 0.5, 0.001]
intervals = [1]
metrics = ["user", "kernel"]
# metrics = ["kernel", "user"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
TRACE_READERS = []

############################################ Configuration ###############################################
ismemcached = False # default is True
enable_mutilate = False # default is False
xdp_indirectcopy = True # default is True, but previous experiments are conducted as false (2025-11-12)
##########################################################################################################

user_plugin_conf  = f"{conf_root}/netdata/plugin/only-go-plugin.conf"
kernel_plugin_conf  = f"{conf_root}/netdata/plugin/no-plugin.conf"
netdata_cpu_aff = "pin-netdata-core0-4.conf"
mcd_cpu_aff = "pin-core0-4-execute.sh"

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

if ismemcached:
    data_dir = f"{local_data_root}/monitoring_cpu_utilization/memcached/enable_mutilate-{enable_mutilate}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}" 
else:
    data_dir = f"{local_data_root}/monitoring_cpu_utilization/redis/enable_mutilate-{enable_mutilate}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}" 


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
    subprocess.run("sudo systemctl daemon-reload".split())
    subprocess.run(f"sudo systemctl restart netdata".split())
    # this sleep is needed for cpu usage calculation by pidstat
    time.sleep(5)
    print(f"=== [End] Running Netdata {num_instance} ===")

def run_netdata_client_monitor(num_instance, metric, interval):
    print(f"=== [Start] Running monitoring client mcd={num_instance} === ")
    if metric == "user":
        stdin_input = f"{interval}\n1\n"
    else:
        stdin_input = f"{interval}\n0\n"
    if ismemcached:
        client_script = "client_netdata"
    else:
        client_script = "client_netdata_redis"
    cmd = (
        f"cd {remote_monitoring_client} && "
        f"numactl --cpunodebind=1 --membind=1 ./{client_script} test.csv"
    )
    proc = subprocess.Popen(
        f"ssh {remote_host} {cmd}".split(),
        stdin=subprocess.PIPE,
        text=True
    )
    proc.stdin.write(stdin_input)
    proc.stdin.close()
    print(f"=== [End] Running monitoring client mcd={num_instance} === ")

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
    time.sleep(5)

def run_x_monitor_client_monitor(num_instance, metric, interval):
    print(f"=== [Start] Running monitoring client mcd={num_instance} === ")
    stdin_input = f"{interval}\n"
    if ismemcached:
        client_script = "client_x-monitor"
    else:
        client_script = "client_x-monitor_redis"

    cmd = (
        f"cd {remote_monitoring_client} && "
        f"numactl --cpunodebind=1 --membind=1 ./{client_script} test.csv"
    )
    # run であっている．run_netdata_client_monitor は，Popen だが，cpu utilizaiton の計測方法が違う
    subprocess.run(
        ["ssh", remote_host, cmd],
        input=stdin_input,
        text=True,
        check=True
    )
    print(f"=== [End] Running monitoring client mcd={num_instance} === ")

def calculate_stats_cpu(num_instance, metric, interval):
    print(f"=== [Start] Calculate stats-loop CPU Utilization, {num_instance} instance, {metric} metrics === ")

    if ismemcached:
        # memcached_stats_loop の CPU 使用率を計測
        out_path = (
            f"{data_dir}/{str(num_instance).zfill(3)}mcd/"
            f"memcached_stats_loop-{metric}metrics-{num_instance}mcd-interval{interval}.csv"
        )
        pattern = "memcached_stats_loop"
    else:
        # redis_info_loop の CPU 使用率を計測
        out_path = (
            f"{data_dir}/{str(num_instance).zfill(3)}redis/"
            f"redis_info_loop-{metric}metrics-{num_instance}redis-interval{interval}.csv"
        )
        pattern = "redis_info_loop"

    # Netdata と同じく 40 秒間 (40 秒ごと 1 回) の CPU 利用率
    cmd = f"pidstat -u -p $(pgrep -d',' -f {pattern}) 40 1"

    with open(out_path, "w") as f:
        subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, check=True)

    print(f"=== [End] Saved stats-loop CPU to {out_path} ===")

def calculate_netdata_cpu(num_instance, metric, interval):
    print(f"=== [Start] Calculate Netdata CPU Utilization, {num_instance} instance, {metric} metrics === ")
    if ismemcached:
        out_path = f"{data_dir}/{str(num_instance).zfill(3)}mcd/netdata-{metric}metrics-{num_instance}mcd-interval{interval}.csv"
    else:
        out_path = f"{data_dir}/{str(num_instance).zfill(3)}redis/netdata-{metric}metrics-{num_instance}redis-interval{interval}.csv"
    # cmd = f"pidstat -u -p $(pgrep -d',' -f netdata) 1 10"
    cmd = f"pidstat -u -p $(pgrep -d',' -f netdata) 40 1"
    with open(out_path, "w") as f:
        subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, check=True)
    print(f"=== [End] Saved to {out_path} ===")

def clear_trace_buffer():
    base = "/sys/kernel/debug/tracing"
    if not os.path.isdir(base):
        base = "/sys/kernel/tracing"
    subprocess.run(["sudo", "sh", "-c", f"echo 0 > {base}/tracing_on"])
    subprocess.run(["sudo", "sh", "-c", f": > {base}/trace"])
    subprocess.run(["sudo", "sh", "-c", f"echo 1 > {base}/tracing_on"])

def calculate_x_monitor_cpu(num_instance, metric, interval):
    clear_trace_buffer()
    print(f"=== [Start] Calculate X-Monitor CPU Utilization, {num_instance} instance, {metric} metrics === ")
    if ismemcached:
        out_path = f"{data_dir}/{str(num_instance).zfill(3)}mcd/xmonitor-{metric}metrics-{num_instance}mcd-interval{interval}.csv"
    else:
        out_path = f"{data_dir}/{str(num_instance).zfill(3)}redis/xmonitor-{metric}metrics-{num_instance}redis-interval{interval}.csv"

    trace_pipe = "/sys/kernel/debug/tracing/trace_pipe"
    if not os.path.exists(trace_pipe):
        alt = "/sys/kernel/tracing/trace_pipe"
        if os.path.exists(alt):
            trace_pipe = alt

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    f = open(out_path, "w")
    # ▼ proc を受け取って登録
    proc = subprocess.Popen(["sudo", "cat", trace_pipe], stdout=f)
    TRACE_READERS.append((proc, f, out_path))
    time.sleep(5)
    print(f"=== [Trace reader started in background -> {out_path}] ===")

def stop_mutilate():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "mutilate"])

# def run_mutilate(num_instance):
#     print(f"=== [Start] Running mutilate {num_instance} ===")
#     subprocess.run(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_instance).zfill(3)}mcd-load.sh".split())
#     subprocess.Popen(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_instance).zfill(3)}mcd-run.sh".split())
#     print(f"=== [End] Running mutilate {num_instance} ===")

def run_mutilate(num_instance):
    print(f"=== [Start] Running mutilate {num_instance} ===")
    load_script = f"{remote_mutilate_script_latency}/{str(num_instance).zfill(3)}mcd-load.sh"
    run_script  = f"{remote_mutilate_script_latency}/{str(num_instance).zfill(3)}mcd-run.sh"
    # -------- load (blocking) --------
    # ssh の先で ulimit → script を実行
    # TODO:  ここいらないので直す．なんなら mutilate 自体消す．
    subprocess.run([
        "ssh", remote_host,
        f'bash -c "ulimit -n 100000; {load_script}"'
    ])
    # -------- run (non-blocking) --------
    # 同様に ulimit を設定してから run.sh を実行
    subprocess.Popen([
        "ssh", remote_host,
        f'bash -c "ulimit -n 100000; {run_script}"'
    ])
    print(f"=== [End] Running mutilate {num_instance} ===")

def stop_monitoring_client_for_netdata():
    if ismemcached:
        subprocess.run(["ssh", remote_host, "pkill", "-f", "client_netdata"])
    else:
        subprocess.run(["ssh", remote_host, "pkill", "-f", "client_netdata_redis"])

def stop_bpf_tracepipe():
    subprocess.run("sudo pkill -f trace_pipe".split())
    for proc, f, path in TRACE_READERS:
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        try:
            f.flush()
            os.fsync(f.fileno())
        except Exception:
            pass
        try:
            f.close()
        except Exception:
            pass
    TRACE_READERS.clear()

def stop_database():
    if ismemcached:
        subprocess.run("sudo pkill -f memcached".split())
    else:
        subprocess.run("sudo pkill -f redis".split())



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

#############################################################################

def run_netdata_server(num_instance, metric):
    run_database(num_instance)
    run_netdata(num_instance, metric)

def run_netdata_client(num_instance, metric, interval):
    if enable_mutilate:
        run_mutilate(num_instance)
    run_netdata_client_monitor(num_instance, metric, interval)

def run_x_monitor_server(num_instance, metric):
    run_database(num_instance)
    load_xdp(metric, num_instance)

def run_x_monitor_client(num_instance, metric, interval):
    if enable_mutilate:
        run_mutilate(num_instance)
    run_x_monitor_client_monitor(num_instance, metric, interval)

def stop_for_netdata():
    stop_monitoring_client_for_netdata()
    if enable_mutilate:
        stop_mutilate()
    if ismemcached:
        stop_stats()
    else:
        stop_INFO()
    stop_database()

def stop_for_x_monitor():
    stop_bpf_tracepipe()
    if enable_mutilate:
        stop_mutilate()
    stop_database()
    detach_xdp()

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
    subprocess.run(cmd.split())
    print(f"=== [End] Making output_dir {data_dir}/{subdir} ===")

def netdata_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### Netdata: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        log_to_slack(f"============================ Netdcata: Monitoring {metric} metrics ===================")
        for num_instance in num_instances:
            print()
            print(f"############## Running {num_instance} servers ##########################")
            log_to_slack(f"------------------Runnign {num_instance} servers----------------")
            make_output_dir(num_instance)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_netdata_server(num_instance, metric)
                time.sleep(5)
                if metric == "user":
                    if ismemcached:
                        run_stats(num_instance, interval)
                    else:
                        run_INFO(num_instance, interval)
                run_netdata_client(num_instance, metric, interval)
                if metric == "user":
                    calculate_stats_cpu(num_instance, metric, interval)
                calculate_netdata_cpu(num_instance, metric, interval)
                stop_for_netdata()
                time.sleep(5)

def x_monitor_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### X-Monitor: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        log_to_slack(f"============================ X-Monitor: Monitoring {metric} metrics ===================")
        for num_instance in num_instances:
            print()
            print(f"############## Running {num_instance} servers ##########################")
            log_to_slack(f"------------------Runnign {num_instance} servers----------------")
            make_output_dir(num_instance)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_x_monitor_server(num_instance, metric)
                calculate_x_monitor_cpu(num_instance, metric, interval)
                run_x_monitor_client(num_instance, metric, interval)
                stop_for_x_monitor()
                time.sleep(5)

def main():
    log_to_slack("============================ Experiment Starts!!!! =======================================")
    log_to_slack(f"============================ data_dir is {data_dir} =======================================")
    setup()
    # netdata_monitoring()
    x_monitor_monitoring()
    log_to_slack("============================All experiment finished!!!!=======================================")
    log_to_slack(f"============================ data_dir is {data_dir} =======================================")

if __name__ == "__main__":
    main()
