# import re

# def compute_cpu_utilization(filename):
#     print(f"{filename}")
#     total_elapsed_seconds = 0.0
#     cpu_freq_hz = 2_000_000_000  # 2000 MHz

#     cycles_pattern = re.compile(r'Elapsed cycles are (\d+)')
#     timestamp_pattern = re.compile(r'\s(\d+\.\d+):\s+bpf_trace_printk')

#     timestamps = []

#     with open(filename, 'r') as f:
#         for line in f:
#             # タイムスタンプを収集
#             ts_match = timestamp_pattern.search(line)
#             if ts_match:
#                 timestamps.append(float(ts_match.group(1)))

#             # Elapsed cycles を加算
#             cycle_match = cycles_pattern.search(line)
#             if cycle_match:
#                 cycles = int(cycle_match.group(1))
#                 total_elapsed_seconds += cycles / cpu_freq_hz

#     # タイムスタンプ差分から duration を求める
#     if len(timestamps) >= 2:
#         start_time = timestamps[0]
#         end_time = timestamps[-1]
#         duration = end_time - start_time
#         cpu_util = total_elapsed_seconds / duration if duration > 0 else 0
#         print(f"Total elapsed time: {total_elapsed_seconds:.6f} s")
#         print(f"Total duration     : {duration:.6f} s")
#         print(f"CPU utilization    : {cpu_util * 100:.9f} %")
#     else:
#         print("Not enough timestamp data to compute utilization.")
#     print();

# # 実行
# compute_cpu_utilization("xdp_output_interval/xdp_1_interval")
# compute_cpu_utilization("xdp_output_interval/xdp_0_1_interval")
# compute_cpu_utilization("xdp_output_interval/xdp_0_01_interval")

# -------------------------------------------------------------------------------------------------------------------------------------

from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

# ---- 正規表現 ----
CYCLES_RE = re.compile(r"Elapsed cycles are (\d+)")
TS_RE = re.compile(r"\s(\d+\.\d+):\s+bpf_trace_printk")
# xmonitor- or x-monitor の両方対応
FNAME_RE = re.compile(r"x-?monitor-(user|kernel)metrics-(\d+)mcd-interval(0\.01|0\.1|1)\.csv$")
# netdata CSV
NETDATA_FNAME_RE = re.compile(r"netdata-(user|kernel)metrics-(\d+)mcd\.csv$")

# ---- X-Monitor: CPU 使用率計算 ----
def compute_cpu_utilization(filepath: Path, cpu_freq_hz: float = 2_000_000_000) -> Optional[float]:
    total_elapsed_seconds = 0.0
    timestamps: List[float] = []
    with filepath.open("r") as f:
        for line in f:
            ts_match = TS_RE.search(line)
            if ts_match:
                timestamps.append(float(ts_match.group(1)))
            cyc = CYCLES_RE.search(line)
            if cyc:
                total_elapsed_seconds += int(cyc.group(1)) / cpu_freq_hz
    if len(timestamps) < 2:
        return None
    duration = timestamps[-1] - timestamps[0]
    if duration <= 0:
        return None
    return total_elapsed_seconds / duration   # fraction (0~1)

# ---- Netdata: CSV から %CPU を抽出 ----
def parse_netdata_csv(fp: Path) -> Dict[str, float]:
    """
    'Average:' 行からコマンド別の %CPU を拾う。
    返り値: {'netdata': float, 'go.d.plugin': float, ...}（存在するものだけ）
    """
    usage: Dict[str, float] = {}
    with fp.open("r", errors="ignore") as f:
        for line in f:
            if not line.startswith("Average:"):
                continue
            # 例: Average:  111 396500 1.12 1.20 0.00 0.00 2.33 - netdata
            parts = line.strip().split()
            if len(parts) < 10:
                continue
            # parts[0]='Average:', [1]=UID, [2]=PID, [3]=%usr, [4]=%system, [5]=%guest, [6]=%wait, [7]=%CPU, [8]=CPU, [9:]=Command(スペース無し想定)
            try:
                cpu_pct = float(parts[7])
            except ValueError:
                continue
            cmd = parts[9]
            usage[cmd] = cpu_pct
    return usage

# ---- ファイル探索 ----
def _collect_xmon_files(base_dir: Path, metric: str) -> Dict[int, Dict[str, Path]]:
    assert metric in ("user", "kernel")
    mcd_dirs = ["001mcd", "005mcd", "010mcd"]
    intervals = ["1", "0.1", "0.01"]
    result: Dict[int, Dict[str, Path]] = {}
    for d in mcd_dirs:
        sub = base_dir / d
        if not sub.is_dir():
            continue
        mcd_num = {1: 1, 5: 5, 10: 10}[int(d[:3])]
        available: Dict[str, Path] = {}
        for p in sub.iterdir():
            if not p.is_file():
                continue
            m = FNAME_RE.match(p.name)
            if not m:
                continue
            f_metric, f_mcd, f_interval = m.group(1), m.group(2), m.group(3)
            if f_metric != metric or int(f_mcd) != mcd_num:
                continue
            if f_interval in intervals:
                available[f_interval] = p
        if available:
            result[mcd_num] = available
    return result

def _collect_netdata_files(base_dir: Path, metric: str) -> Dict[int, Path]:
    assert metric in ("user", "kernel")
    mcd_dirs = ["001mcd", "005mcd", "010mcd"]
    result: Dict[int, Path] = {}
    for d in mcd_dirs:
        sub = base_dir / d
        if not sub.is_dir():
            continue
        mcd_num = {1: 1, 5: 5, 10: 10}[int(d[:3])]
        for p in sub.iterdir():
            if not p.is_file():
                continue
            m = NETDATA_FNAME_RE.match(p.name)
            if not m:
                continue
            f_metric, f_mcd = m.group(1), m.group(2)
            if f_metric != metric or int(f_mcd) != mcd_num:
                continue
            result[mcd_num] = p
    return result

# ---- グラフ描画 ----
def _plot_grouped(ax, util_xmon: Dict[int, Dict[str, float]],
                  util_netdata: Dict[int, Tuple[float, float]],
                  metric: str):
    """
    util_xmon[g][interval] = fraction(0~1)
    util_netdata[g] = (netdata_daemon_pct, go_d_pct)  # go_d_pct は kernel のとき 0 にする
    """
    groups = sorted(set(util_xmon.keys()) | set(util_netdata.keys()))  # [1,5,10]
    # 表示順: netdata, 1s, 100ms, 10ms
    series = ["netdata", "1", "0.1", "0.01"]

    # データ整形（%に変換）
    xmon_pct = {s: [util_xmon.get(g, {}).get(s, float('nan')) * 100 for g in groups] for s in ["1", "0.1", "0.01"]}
    netdata_daemon = [util_netdata.get(g, (np.nan, np.nan))[0] for g in groups]
    netdata_god    = [util_netdata.get(g, (np.nan, np.nan))[1] for g in groups]

    # 等間隔配置
    x = np.arange(len(groups))  # 0,1,2...
    width = 0.18
    offsets = np.linspace(-1.5*width, 1.5*width, 4)  # 4系列ぶん

    # --- Netdata: ユーザは stacked, カーネルは netdata のみ ---
    # ベース
    # ax.bar(x + offsets[0], netdata_daemon, width=width, label="Netdata (daemon)")
    # go.d.plugin をユーザメトリクスのときだけ重ねる
    # if metric == "user":
    #     ax.bar(x + offsets[0], netdata_god, width=width, bottom=netdata_daemon, label="go.d.plugin")
    # --- Netdata: ユーザは stacked（go.d.plugin → 下 / daemon → 上） ---
    if metric == "user":
        ax.bar(x + offsets[0], netdata_god, width=width, label="go.d.plugin")  # 下
        ax.bar(x + offsets[0], netdata_daemon, width=width, bottom=netdata_god, label="Netdata")  # 上
    else:
        # kernel: daemon のみ
        ax.bar(x + offsets[0], netdata_daemon, width=width, label="Netdata")

    # --- X-Monitor ---
    ax.bar(x + offsets[1], xmon_pct["1"],   width=width, label="X-Monitor-1s")
    ax.bar(x + offsets[2], xmon_pct["0.1"], width=width, label="X-Monitor-100ms")
    ax.bar(x + offsets[3], xmon_pct["0.01"],width=width, label="X-Monitor-10ms")

    # 軸・体裁
    ax.set_xticks(x)
    ax.set_xticklabels([str(g) for g in groups], fontsize=20)
    ax.set_xlabel("Number of instance", fontsize=22)
    ax.set_ylabel("CPU Utilization (%)", fontsize=22)

    ax.tick_params(axis='x', labelsize=20)
    ax.tick_params(axis='y', labelsize=20)

    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-4)

    fig = ax.figure
    fig.text(0.08, 0.89, "log scale", fontsize=18, ha='left', va='bottom')

    ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.18))
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

# ---- メイン ----
def make_plots(base_dir: str, cpu_freq_hz: float = 2_000_000_000):
    base = Path(base_dir)

    for metric in ("user", "kernel"):
        # X-Monitor 側
        files_xmon = _collect_xmon_files(base, metric)
        if not files_xmon:
            print(f"[warn] No X-Monitor files for metric={metric}")
        util_xmon: Dict[int, Dict[str, float]] = {}
        for mcd, by_interval in files_xmon.items():
            util_xmon[mcd] = {}
            for interval, path in by_interval.items():
                u = compute_cpu_utilization(path, cpu_freq_hz)
                if u is not None:
                    util_xmon[mcd][interval] = u

        # Netdata 側（%CPU）
        files_net = _collect_netdata_files(base, metric)
        if not files_net:
            print(f"[warn] No Netdata files for metric={metric}")
        util_netdata: Dict[int, Tuple[float, float]] = {}
        for mcd, fp in files_net.items():
            usage = parse_netdata_csv(fp)
            daemon = usage.get("netdata", np.nan)
            god = usage.get("go.d.plugin", 0.0 if metric=="kernel" else np.nan)  # kernel は無視（積み上げ無し）
            if metric == "kernel":
                god = 0.0  # 明示
            util_netdata[mcd] = (daemon, god)

        # プロット
        fig, ax = plt.subplots(figsize=(9, 6.5))
        _plot_grouped(ax, util_xmon, util_netdata, metric)
        ax.set_title(f"X-Monitor vs Netdata ({metric})")
        fig.tight_layout()
        plt.show()