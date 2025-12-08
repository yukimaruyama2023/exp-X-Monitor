from pathlib import Path
import re
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

HATCH_LINEWIDTH = 1.6
fontsize = 35
labelsize = 35 
legend_fontsize = 30
# figsize = (12, 6.5)  # default is (9, 6.5)
# figsize = (24, 7)  # default is (9, 6.5)
# figsize = (33, 6.9)  # default is (9, 6.5)
# figsize = (33, 6.8)  # default is (9, 6.5)
figsize = (38, 6.8)  # default is (9, 6.5)
logsize = 30
bbox_to_anchor = (0.5, 1.32)

# ========== Color / Hatch ==========

COLORS = {
    # --- Netdata 系 (interval ごとに色分け) ---
    "Netdata (1000ms)":     "#F5A97F",
    "Netdata (500ms)":      "#F28F79",
    "Netdata (1ms)":        "#E46876",

    # go.d.plugin は合計値にだけ使うので描画には使わない（定義だけ残す）
    "go.d.plugin":          "#F5A97F",

    # --- X-Monitor 系 ---
    "X-Monitor (1000ms)":   "#5AB8A8",
    "X-Monitor (500ms)":    "#72A7E3",
    "X-Monitor (1ms)":      "#C7A0E8",
}

HATCHES = {
    # --- Netdata 系 ---
    "Netdata (1000ms)":     "////",
    "Netdata (500ms)":      "----",
    "Netdata (1ms)":        "ooo",

    # go.d.plugin は合計値にだけ使うので描画には使わない（定義だけ残す）
    "go.d.plugin":          "****",

    # --- X-Monitor 系 ---
    "X-Monitor (1000ms)":   "\\\\\\\\",
    "X-Monitor (500ms)":    "xxxx",
    "X-Monitor (1ms)":      "....",
}

# ---- 正規表現 ----
CYCLES_RE = re.compile(r"Elapsed cycles are (\d+)")
TS_RE     = re.compile(r"\s(\d+\.\d+):\s+bpf_trace_printk")

# xmonitor- or x-monitor の両方対応 + interval は任意の浮動小数
# 例: x-monitor-usermetrics-12redis-interval1.csv
FNAME_RE = re.compile(
    r"x-?monitor-(user|kernel)metrics-(\d+)redis-interval([0-9.]+)\.csv$"
)

# netdata CSV（interval 付き）
# 例: netdata-usermetrics-12redis-interval1.csv
NETDATA_FNAME_RE = re.compile(
    r"netdata-(user|kernel)metrics-(\d+)redis-interval([0-9.]+)\.csv$"
)

# redis_info_loop (user metrics 用, Netdata 実験時)
# 例: redis_info_loop-usermetrics-12redis-interval1.csv
REDIS_INFO_LOOP_FNAME_RE = re.compile(
    r"redis_info_loop-usermetrics-(\d+)redis-interval([0-9.]+)\.csv$"
)

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
            parts = line.strip().split()
            if len(parts) < 10:
                continue
            try:
                cpu_pct = float(parts[7])
            except ValueError:
                continue
            cmd = parts[9]
            usage[cmd] = cpu_pct
    return usage

# ---- ファイル探索（X-Monitor）----
def _collect_xmon_files(
    base_dir: Path,
    metric: str,
    redis_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    metric: 'user' or 'kernel'
    redis_nums: [1,5,10,...]
    戻り値: {num_instances: {interval_str: Path, ...}, ...}
    """
    assert metric in ("user", "kernel")
    if redis_nums is None:
        redis_nums = [1, 5, 10]

    intervals = ["1", "0.5", "0.001"]
    result: Dict[int, Dict[str, Path]] = {}

    for num in redis_nums:
        sub = base_dir / f"{num:03d}redis"
        if not sub.is_dir():
            continue

        available: Dict[str, Path] = {}
        for p in sub.iterdir():
            if not p.is_file():
                continue
            m = FNAME_RE.match(p.name)
            if not m:
                continue
            f_metric, f_num, f_interval = m.group(1), m.group(2), m.group(3)
            if f_metric != metric or int(f_num) != num:
                continue
            if f_interval in intervals:
                available[f_interval] = p
        if available:
            result[num] = available
    return result

# ---- ファイル探索（Netdata）----
def _collect_netdata_files(
    base_dir: Path,
    metric: str,
    redis_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    metric: 'user' or 'kernel'
    redis_nums: [1,5,10,...]
    戻り値: {num_instances: {interval_str: Path, ...}}
    """
    assert metric in ("user", "kernel")
    if redis_nums is None:
        redis_nums = [1, 5, 10]

    intervals = ["1", "0.5", "0.001"]
    result: Dict[int, Dict[str, Path]] = {}

    for num in redis_nums:
        sub = base_dir / f"{num:03d}redis"
        if not sub.is_dir():
            continue

        available: Dict[str, Path] = {}
        for p in sub.iterdir():
            if not p.is_file():
                continue
            m = NETDATA_FNAME_RE.match(p.name)
            if not m:
                continue
            f_metric, f_num, f_interval = m.group(1), m.group(2), m.group(3)
            if f_metric != metric or int(f_num) != num:
                continue
            if f_interval in intervals:
                available[f_interval] = p
        if available:
            result[num] = available
    return result

# ---- ファイル探索（redis_info_loop, user metrics, Netdata 実験時）----
def _collect_redis_info_loop_files(
    base_dir: Path,
    redis_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    戻り値: {num_instances: {interval_str: Path, ...}}
    例: {12: {"1": Path(".../redis_info_loop-usermetrics-12redis-interval1.csv"), ...}}
    """
    if redis_nums is None:
        redis_nums = [1, 5, 10]

    intervals = ["1", "0.5", "0.001"]
    result: Dict[int, Dict[str, Path]] = {}

    for num in redis_nums:
        sub = base_dir / f"{num:03d}redis"
        if not sub.is_dir():
            continue

        available: Dict[str, Path] = {}
        for p in sub.iterdir():
            if not p.is_file():
                continue
            m = REDIS_INFO_LOOP_FNAME_RE.match(p.name)
            if not m:
                continue
            f_num, f_interval = m.group(1), m.group(2)
            if int(f_num) != num:
                continue
            if f_interval in intervals:
                available[f_interval] = p
        if available:
            result[num] = available
    return result

def draw_bar(ax, xpos, height, label, width, bottom=None):
    ax.bar(
        xpos, height,
        width=width,
        bottom=bottom,
        facecolor="white",
        edgecolor=COLORS[label],
        hatch=HATCHES[label],
        linewidth=1.1,
        zorder=2,
    )
    ax.bar(
        xpos, height,
        width=width,
        bottom=bottom,
        facecolor=(0, 0, 0, 0),
        edgecolor="black",
        linewidth=1.3,
        zorder=3,
    )

# ---- グラフ描画 ----
def _plot_grouped(
    ax,
    util_xmon: Dict[int, Dict[str, float]],
    util_netdata: Dict[int, Dict[str, float]],
    metric: str,
    ymax,
):
    old_hlw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = HATCH_LINEWIDTH
    try:
        groups = sorted(set(util_xmon.keys()) | set(util_netdata.keys()))
        x = np.arange(len(groups))
        width = 0.12  # 6本分

        # interval の順序（左から右へ）
        intervals = ["1", "0.5", "0.001"]

        # 6 本の棒: [N(1s), X(1s), N(0.5s), X(0.5s), N(1ms), X(1ms)]
        offsets = np.linspace(-2.5 * width, 2.5 * width, 6)

        # X-Monitor (% へ変換)
        xmon_pct: Dict[str, List[float]] = {
            s: [util_xmon.get(g, {}).get(s, float("nan")) * 100 for g in groups]
            for s in intervals
        }

        # Netdata (%CPU) も「合計値のみ」を持つ
        netdata_total: Dict[str, List[float]] = {
            s: [util_netdata.get(g, {}).get(s, float("nan")) for g in groups]
            for s in intervals
        }

        # interval → ラベル
        net_label_map = {
            "1":    "Netdata (1000ms)",
            "0.5":  "Netdata (500ms)",
            "0.001":"Netdata (1ms)",
        }
        xmon_label_map = {
            "1":    "X-Monitor (1000ms)",
            "0.5":  "X-Monitor (500ms)",
            "0.001":"X-Monitor (1ms)",
        }

        # --- 描画 ---
        for i, s in enumerate(intervals):
            # Netdata 側（user のときは netdata+go.d, kernel のときは netdata のみを事前に合計済み）
            xpos_net = x + offsets[2 * i]
            net_label = net_label_map[s]
            draw_bar(ax, xpos_net, netdata_total[s], net_label, width)

            # X-Monitor 側
            xpos_xmon = x + offsets[2 * i + 1]
            xmon_label = xmon_label_map[s]
            draw_bar(ax, xpos_xmon, xmon_pct[s], xmon_label, width)

        # 体裁
        ax.set_xticks(x)
        ax.set_xticklabels([str(g) for g in groups], fontsize=fontsize)
        ax.set_xlabel("Number of instances", fontsize=fontsize)
        ax.set_ylabel("CPU Utilization (%)", fontsize=fontsize)
        ax.tick_params(axis='x', labelsize=labelsize)
        ax.tick_params(axis='y', labelsize=labelsize)

        ax.set_yscale("log")
        ax.set_ylim(bottom=1e-5, top=ymax)

        fig = ax.figure
        fig.text(0.023, 0.76, "log scale", fontsize=logsize, ha='left', va='bottom')

        ax.yaxis.grid(True, linestyle="--", linewidth=1.3, alpha=0.55)
        ax.set_axisbelow(True)

        # Legend: Netdata(3) + X-Monitor(3)
        order = [
            "Netdata (1000ms)",
            "Netdata (500ms)",
            "Netdata (1ms)",
            "X-Monitor (1000ms)",
            "X-Monitor (500ms)",
            "X-Monitor (1ms)",
        ]
        order = [lab for lab in order if (lab in COLORS and lab in HATCHES)]

        legend_items = [
            Patch(
                facecolor="white",
                edgecolor=COLORS[lab],
                hatch=HATCHES[lab],
                linewidth=1.6,
                label=lab,
            )
            for lab in order
        ]

        ax.legend(
            handles=legend_items,
            loc="upper center",
            # ncol=3,
            ncol=6,
            bbox_to_anchor=bbox_to_anchor,
            fontsize=legend_fontsize,
            frameon=True,
            framealpha=1.0,
        )
    finally:
        plt.rcParams["hatch.linewidth"] = old_hlw

def make_plots(
    base_dir: str,
    cpu_freq_hz: float = 3_800_000_000,
    redis_nums: Optional[List[int]] = None,
    save: bool = True,
    out_prefix: str = "cpu_utilization_redis",
):
    """
    Redis 版:
      ディレクトリ: 001redis, 002redis, ...
      ファイル:
        X-Monitor: x-monitor-<metric>metrics-<N>redis-intervalX.csv
        Netdata  : netdata-<metric>metrics-<N>redis-intervalX.csv
        stats    : redis_info_loop-usermetrics-<N>redis-intervalX.csv
    """
    base = Path(base_dir)
    if redis_nums is None:
        redis_nums = [1, 5, 10]

    max_cpu_pct = 0.0
    results: Dict[str, tuple] = {}

    # --- 1パス目: データ読み込み & 最大 CPU 利用率の計算 ---
    for metric in ("user", "kernel"):
        # X-Monitor 側
        files_xmon = _collect_xmon_files(base, metric, redis_nums)
        if not files_xmon:
            print(f"[warn] No X-Monitor files for metric={metric}")
        util_xmon: Dict[int, Dict[str, float]] = {}
        for num, by_interval in files_xmon.items():
            util_xmon[num] = {}
            for interval, path in by_interval.items():
                u = compute_cpu_utilization(path, cpu_freq_hz)
                if u is not None:
                    util_xmon[num][interval] = u
                    # u は 0〜1 の比率なので % に変換
                    max_cpu_pct = max(max_cpu_pct, u * 100.0)

        # Netdata 側
        files_net = _collect_netdata_files(base, metric, redis_nums)
        if not files_net:
            print(f"[warn] No Netdata files for metric={metric}")

        # redis_info_loop は user metrics の Netdata 実験のときだけ
        redis_info_files: Dict[int, Dict[str, Path]] = {}
        if metric == "user":
            redis_info_files = _collect_redis_info_loop_files(base, redis_nums)

        util_netdata: Dict[int, Dict[str, float]] = {}
        util_netdata_god: Dict[int, Dict[str, float]] = {}
        util_netdata_info: Dict[int, Dict[str, float]] = {}

        for num, by_interval in files_net.items():
            util_netdata[num] = {}
            if metric == "user":
                util_netdata_god[num] = {}
                util_netdata_info[num] = {}
            for interval, fp in by_interval.items():
                usage = parse_netdata_csv(fp)
                daemon = usage.get("netdata", np.nan)
                god = usage.get("go.d.plugin", 0.0)

                info_cpu = 0.0
                if metric == "user":
                    info_fp = redis_info_files.get(num, {}).get(interval)
                    if info_fp is not None:
                        info_usage = parse_netdata_csv(info_fp)
                        info_cpu = info_usage.get("redis_info_loop", 0.0)

                if metric == "user":
                    total = daemon + god + info_cpu
                else:
                    total = daemon

                util_netdata[num][interval] = total
                # Netdata は既に %CPU 単位
                max_cpu_pct = max(max_cpu_pct, total)

                if metric == "user":
                    util_netdata_god[num][interval] = god
                    util_netdata_info[num][interval] = info_cpu

        # 結果を保存（描画はまだしない）
        if metric == "user":
            results[metric] = (util_xmon, util_netdata, util_netdata_god, util_netdata_info)
        else:
            results[metric] = (util_xmon, util_netdata, None, None)

    # max_cpu_pct が 0 だった場合の保険
    if max_cpu_pct <= 0:
        ymax = 1.0
    else:
        ymax = max_cpu_pct * 2.0  # 100% のマージン

    # --- 2パス目: 共通 ymax で user / kernel を描画 ---
    for metric in ("user", "kernel"):
        util_xmon, util_netdata, util_netdata_god, util_netdata_info = results[metric]

        fig, ax = plt.subplots(figsize=figsize)
        _plot_grouped(ax, util_xmon, util_netdata, metric, ymax=ymax)
        fig.tight_layout()

        if save:
            # PDF 保存
            pdf_path = base / f"{out_prefix}-redis-{metric}.pdf"
            fig.savefig(pdf_path, bbox_inches="tight")
            print(f"[info] Saved: {pdf_path}")

            # PNG 保存（高解像度）
            png_path = base / f"{out_prefix}-redis-{metric}.png"
            fig.savefig(png_path, dpi=300, bbox_inches="tight")
            print(f"[info] Saved: {png_path}")

        plt.show()

    return results

def print_cpu_utilization_table(results):
    """
    results: make_plots() の返り値
      {
        "user":   (util_xmon, util_net_total, util_net_god, util_net_info),
        "kernel": (util_xmon, util_net_total, None, None)
      }
    """

    intervals = ["1", "0.5", "0.001"]

    for metric in ("user", "kernel"):
        util_xmon, util_netdata, util_net_god, util_net_info = results[metric]
        print(f"\n===== CPU Utilization (Redis, metric={metric}) =====")
        # 全 instance 数
        nums = sorted(set(util_xmon.keys()) | set(util_netdata.keys()))
        for s in intervals:
            print(f"\n--- interval = {s} ---")
            for num in nums:
                # X-Monitor: 0〜1 の比率 → % に変換（小数点以下6桁）
                xmon_v = util_xmon.get(num, {}).get(s, float("nan"))
                if np.isnan(xmon_v):
                    xmon_str = "nan"
                else:
                    xmon_str = f"{xmon_v * 100:.6f}"

                # Netdata: 合計 %CPU
                net_v = util_netdata.get(num, {}).get(s, float("nan"))
                if np.isnan(net_v):
                    net_str = "nan"
                else:
                    net_str = f"{net_v:.4f}"

                # user metrics 内訳（go.d, redis_info_loop）
                detail = ""
                if metric == "user" and util_net_god is not None and util_net_info is not None:
                    god_v = util_net_god.get(num, {}).get(s, float("nan"))
                    info_v = util_net_info.get(num, {}).get(s, float("nan"))
                    parts = []
                    if not np.isnan(god_v):
                        parts.append(f"go.d={god_v:.4f} %")
                    if not np.isnan(info_v):
                        parts.append(f"redis_info_loop={info_v:.4f} %")
                    if parts:
                        detail = " (" + ", ".join(parts) + ")"

                print(f"  {num} redis : X-Monitor={xmon_str} % , Netdata={net_str} %{detail}")