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
remote_mutilate_script_latency = "/home/maruyama/workspace/exp-X-Monitor/conf/mutilate/exp-cpuusage/"
remote_monitoring_client = "/home/maruyama/workspace/exp-X-Monitor/src/client/Monitoring_Client/"
local_data_root = "/home/maruyama/workspace/exp-X-Monitor/data/"
x_monitor_root = "/home/maruyama/workspace/exp-X-Monitor/src/server/x-monitor"
conf_root = "./conf"
log_script_path = "./scripts/"

# num_memcacheds = [1, 5, 10]
num_memcacheds = list(range(1, 13))
intervals = [1, 0.5, 0.001]
# metrics = ["user", "kernel"]
metrics = ["kernel", "user"]
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
TRACE_READERS = []

############################################ Configuration ###############################################
enable_mutilate = False # default is False
xdp_indirectcopy = True # default is True, but previous experiments are conducted as false (2025-11-12)
##########################################################################################################

user_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
kernel_plugin_conf  = f"{conf_root}/netdata/plugin/all-plugin.conf"
netdata_cpu_aff = "pin-netdata-core0.conf"
mcd_cpu_aff = "pin-core1-5-execute.sh"

if xdp_indirectcopy:
    xdp_user_met_program = "xdp_user_indirectcopy.sh"
else:
    xdp_user_met_program = "xdp_user_directcopy.sh"


netdata_conf = {
    "cpu_affinity": f"{conf_root}/netdata/cpu-affinity/{netdata_cpu_aff}",
    "user_plugin_conf": user_plugin_conf,
    "kernel_plugin_conf": kernel_plugin_conf,
}

data_dir = f"{local_data_root}/monitoring_cpu_utilization/enable_mutilate-{enable_mutilate}/xdp_indirectcopy-{xdp_indirectcopy}/{timestamp}"



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
    # this sleep is needed for cpu usage calculation by pidstat
    time.sleep(5)
    print(f"=== [End] Running Netdata {num_memcached} ===")

def run_netdata_client_monitor(num_memcached, metric):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    if metric == "user":
        stdin_input = "1\n1\n"
    else:
        stdin_input = "1\n0\n"
    cmd = (
        f"cd {remote_monitoring_client} && "
        f"numactl --cpunodebind=1 --membind=1 ./client_netdata test.csv"
    )
    proc = subprocess.Popen(f"ssh {remote_host} {cmd}".split(),
                        stdin=subprocess.PIPE,
                        text=True)
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
    time.sleep(5)

def run_x_monitor_client_monitor(num_memcached, metric, interval):
    print(f"=== [Start] Running monitoring client mcd={num_memcached} === ")
    stdin_input = f"{interval}\n"
    cmd = ( 
        f"cd {remote_monitoring_client} && "
        f"numactl --cpunodebind=1 --membind=1 ./client_x-monitor test.csv"
    )
    subprocess.run(
        ["ssh", remote_host, cmd],
        input=stdin_input,
        text=True,
        check=True
    )
    print(f"=== [End] Running monitoring client mcd={num_memcached} === ")

def calculate_netdata_cpu(num_memcached, metric):
    print(f"=== [Start] Calculate Netdata CPU Utilization, {num_memcached} instance, {metric} metrics === ")
    out_path = f"{data_dir}/{str(num_memcached).zfill(3)}mcd/netdata-{metric}metrics-{num_memcached}mcd.csv"
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

def calculate_x_monitor_cpu(num_memcached, metric, interval):
    clear_trace_buffer()
    print(f"=== [Start] Calculate X-Monitor CPU Utilization, {num_memcached} instance, {metric} metrics === ")
    out_path = f"{data_dir}/{str(num_memcached).zfill(3)}mcd/xmonitor-{metric}metrics-{num_memcached}mcd-interval{interval}.csv"

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

def run_mutilate(num_memcached):
    print(f"=== [Start] Running mutilate {num_memcached} ===")
    subprocess.run(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_memcached).zfill(3)}mcd-load.sh".split())
    subprocess.Popen(f"ssh {remote_host} {remote_mutilate_script_latency}/{str(num_memcached).zfill(3)}mcd-run.sh".split())
    print(f"=== [End] Running mutilate {num_memcached} ===")

def stop_monitoring_client_for_netdata():
    subprocess.run(["ssh", remote_host, "pkill", "-f", "client_netdata"])

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

def stop_memcached():
    subprocess.run("sudo pkill -f memcached".split())

def run_netdata_server(num_memcached, metric):
    run_memcached(num_memcached)
    run_netdata(num_memcached, metric)

def run_netdata_client(num_memcached, metric):
    if enable_mutilate:
        run_mutilate(num_memcached)
    run_netdata_client_monitor(num_memcached, metric)

def run_x_monitor_server(num_memcached, metric):
    run_memcached(num_memcached)
    load_xdp(metric, num_memcached)

def run_x_monitor_client(num_memcached, metric, interval):
    if enable_mutilate:
        run_mutilate(num_memcached)
    run_x_monitor_client_monitor(num_memcached, metric, interval)

def stop_for_netdata():
    stop_monitoring_client_for_netdata()
    if enable_mutilate:
        stop_mutilate()
    stop_memcached()

def stop_for_x_monitor():
    stop_bpf_tracepipe()
    if enable_mutilate:
        stop_mutilate()
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
    subprocess.run(f"{cmd}".split())
    print(f"=== [End] Making output_dir {data_dir}/{str(num_memcached).zfill(3)}mcd ===")

def netdata_monitoring():
    for metric in metrics:
        print()
        print(f"############################################################################")
        print(f"##################### Netdata: Monitoring {metric} metrics ##########################")
        print(f"############################################################################")
        log_to_slack(f"============================ Netdcata: Monitoring {metric} metrics ===================")
        for num_memcached in num_memcacheds:
            print()
            print(f"############## Running {num_memcached} servers ##########################")
            log_to_slack(f"------------------Runnign {num_memcached} servers----------------")
            make_output_dir(num_memcached)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
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
        log_to_slack(f"============================ X-Monitor: Monitoring {metric} metrics ===================")
        for num_memcached in num_memcacheds:
            print()
            print(f"############## Running {num_memcached} servers ##########################")
            log_to_slack(f"------------------Runnign {num_memcached} servers----------------")
            make_output_dir(num_memcached)
            for interval in intervals:
                print(f"############## Interval {interval} ##########################")
                log_to_slack(f"Interval {interval}")
                run_x_monitor_server(num_memcached, metric)
                calculate_x_monitor_cpu(num_memcached, metric, interval)
                run_x_monitor_client(num_memcached, metric, interval)
                stop_for_x_monitor()
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
