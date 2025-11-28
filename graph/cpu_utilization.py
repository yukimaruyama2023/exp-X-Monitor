from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

HATCH_LINEWIDTH = 1.6  
fontsize = 25
labelsize = 25
figsize = (12, 6.5) # default is (9, 6.5)

# ========== Color / Hatch (あなた指定のスキームに合わせて修正) ==========

COLORS = {
    # --- Netdata 系 (interval ごとに色分け) ---
    "Netdata (1000ms)":     "#F5A97F",
    "Netdata (500ms)":      "#F28F79",
    "Netdata (1ms)":        "#E46876",

    # go.d.plugin は Netdata と区別するために別キーのまま
    # （色をそろえたければここを変えればよい）
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

    # go.d.plugin は常に同じ見た目
    "go.d.plugin":          "****",

    # --- X-Monitor 系 ---
    "X-Monitor (1000ms)":   "\\\\\\\\",
    "X-Monitor (500ms)":    "xxxx",
    "X-Monitor (1ms)":      "....",
}

# ---- 正規表現 ----
CYCLES_RE = re.compile(r"Elapsed cycles are (\d+)")
TS_RE = re.compile(r"\s(\d+\.\d+):\s+bpf_trace_printk")

# xmonitor- or x-monitor の両方対応 + interval は任意の浮動小数
FNAME_RE = re.compile(
    r"x-?monitor-(user|kernel)metrics-(\d+)mcd-interval([0-9.]+)\.csv$"
)

# netdata CSV（interval 付き）
NETDATA_FNAME_RE = re.compile(
    r"netdata-(user|kernel)metrics-(\d+)mcd-interval([0-9.]+)\.csv$"
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
    mcd_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    metric: 'user' or 'kernel'
    mcd_nums: [1,5,10,...]
    戻り値: {mcd_num: {interval_str: Path, ...}, ...}
    """
    assert metric in ("user", "kernel")
    if mcd_nums is None:
        mcd_nums = [1, 5, 10]

    intervals = ["1", "0.5", "0.001"]
    result: Dict[int, Dict[str, Path]] = {}

    for mcd_num in mcd_nums:
        sub = base_dir / f"{mcd_num:03d}mcd"
        if not sub.is_dir():
            continue

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

# ---- ファイル探索（Netdata）----
def _collect_netdata_files(
    base_dir: Path,
    metric: str,
    mcd_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    metric: 'user' or 'kernel'
    mcd_nums: [1,5,10,...]
    戻り値: {mcd_num: {interval_str: Path, ...}}
    """
    assert metric in ("user", "kernel")
    if mcd_nums is None:
        mcd_nums = [1, 5, 10]

    intervals = ["1", "0.5", "0.001"]
    result: Dict[int, Dict[str, Path]] = {}

    for mcd_num in mcd_nums:
        sub = base_dir / f"{mcd_num:03d}mcd"
        if not sub.is_dir():
            continue

        available: Dict[str, Path] = {}
        for p in sub.iterdir():
            if not p.is_file():
                continue
            m = NETDATA_FNAME_RE.match(p.name)
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
        facecolor=(0,0,0,0),
        edgecolor="black",
        linewidth=1.3,
        zorder=3,
    )

# ---- グラフ描画 ----
def _plot_grouped(
    ax,
    util_xmon: Dict[int, Dict[str, float]],
    util_netdata: Dict[int, Dict[str, Tuple[float, float]]],
    metric: str
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

        # Netdata (%CPU)
        netdata_daemon: Dict[str, List[float]] = {}
        netdata_god: Dict[str, List[float]] = {}
        for s in intervals:
            netdata_daemon[s] = []
            netdata_god[s] = []
            for g in groups:
                daemon, god = util_netdata.get(g, {}).get(s, (np.nan, np.nan))
                netdata_daemon[s].append(daemon)
                netdata_god[s].append(god)

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
            # Netdata 側
            xpos_net = x + offsets[2 * i]
            net_label = net_label_map[s]

            if metric == "user":
                # go.d.plugin（下段、interval によらず同じ見た目）
                draw_bar(ax, xpos_net, netdata_god[s], "go.d.plugin", width, bottom=None)
                # Netdata daemon（上段、interval ごとに色分け）
                draw_bar(
                    ax,
                    xpos_net,
                    netdata_daemon[s],
                    net_label,
                    width,
                    bottom=np.array(netdata_god[s]),
                )
            else:
                # kernel のときは go.d.plugin=0 なので全て daemon 側
                draw_bar(ax, xpos_net, netdata_daemon[s], net_label, width)

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
        ax.set_ylim(bottom=1e-4)

        fig = ax.figure
        fig.text(0.055, 0.83, "log scale", fontsize=18, ha='left', va='bottom')

        ax.yaxis.grid(True, linestyle="--", linewidth=1.3, alpha=0.55)
        ax.set_axisbelow(True)

        from matplotlib.patches import Patch

        # Legend: Netdata(3) + go.d.plugin + X-Monitor(3)
        order = [
            "Netdata (1000ms)",
            "Netdata (500ms)",
            "Netdata (1ms)",
            "go.d.plugin",
            "X-Monitor (1000ms)",
            "X-Monitor (500ms)",
            "X-Monitor (1ms)",
        ]
        if metric == "kernel":
            # kernel では go.d.plugin は実質 0 だが、凡例から消すならここで remove
            order.remove("go.d.plugin")

        order = [lab for lab in order if (lab in COLORS and lab in HATCHES)]

        legend_items = [
            Patch(
                facecolor="white",
                edgecolor=COLORS[lab],
                hatch=HATCHES[lab],
                linewidth=1.6,
                label=lab
            )
            for lab in order
        ]

        ax.legend(
            handles=legend_items,
            loc="upper center",
            ncol=3,
            bbox_to_anchor=(0.5, 1.25),
            fontsize=14,
            frameon=True,
            framealpha=1.0,
        )
    finally:
        plt.rcParams["hatch.linewidth"] = old_hlw


# ---- メイン ----
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

HATCH_LINEWIDTH = 1.6  
fontsize = 25
labelsize = 25
figsize = (12, 6.5) # default is (9, 6.5)

# ========== Color / Hatch (あなた指定のスキームに合わせて修正) ==========

COLORS = {
    # --- Netdata 系 (interval ごとに色分け) ---
    "Netdata (1000ms)":     "#F5A97F",
    "Netdata (500ms)":      "#F28F79",
    "Netdata (1ms)":        "#E46876",

    # go.d.plugin は Netdata と区別するために別キーのまま
    # （色をそろえたければここを変えればよい）
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

    # go.d.plugin は常に同じ見た目
    "go.d.plugin":          "****",

    # --- X-Monitor 系 ---
    "X-Monitor (1000ms)":   "\\\\\\\\",
    "X-Monitor (500ms)":    "xxxx",
    "X-Monitor (1ms)":      "....",
}

# ---- 正規表現 ----
CYCLES_RE = re.compile(r"Elapsed cycles are (\d+)")
TS_RE = re.compile(r"\s(\d+\.\d+):\s+bpf_trace_printk")

# xmonitor- or x-monitor の両方対応 + interval は任意の浮動小数
FNAME_RE = re.compile(
    r"x-?monitor-(user|kernel)metrics-(\d+)mcd-interval([0-9.]+)\.csv$"
)

# netdata CSV（interval 付き）
NETDATA_FNAME_RE = re.compile(
    r"netdata-(user|kernel)metrics-(\d+)mcd-interval([0-9.]+)\.csv$"
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
    mcd_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    metric: 'user' or 'kernel'
    mcd_nums: [1,5,10,...]
    戻り値: {mcd_num: {interval_str: Path, ...}, ...}
    """
    assert metric in ("user", "kernel")
    if mcd_nums is None:
        mcd_nums = [1, 5, 10]

    intervals = ["1", "0.5", "0.001"]
    result: Dict[int, Dict[str, Path]] = {}

    for mcd_num in mcd_nums:
        sub = base_dir / f"{mcd_num:03d}mcd"
        if not sub.is_dir():
            continue

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

# ---- ファイル探索（Netdata）----
def _collect_netdata_files(
    base_dir: Path,
    metric: str,
    mcd_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    metric: 'user' or 'kernel'
    mcd_nums: [1,5,10,...]
    戻り値: {mcd_num: {interval_str: Path, ...}}
    """
    assert metric in ("user", "kernel")
    if mcd_nums is None:
        mcd_nums = [1, 5, 10]

    intervals = ["1", "0.5", "0.001"]
    result: Dict[int, Dict[str, Path]] = {}

    for mcd_num in mcd_nums:
        sub = base_dir / f"{mcd_num:03d}mcd"
        if not sub.is_dir():
            continue

        available: Dict[str, Path] = {}
        for p in sub.iterdir():
            if not p.is_file():
                continue
            m = NETDATA_FNAME_RE.match(p.name)
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
        facecolor=(0,0,0,0),
        edgecolor="black",
        linewidth=1.3,
        zorder=3,
    )

# ---- グラフ描画 ----
def _plot_grouped(
    ax,
    util_xmon: Dict[int, Dict[str, float]],
    util_netdata: Dict[int, Dict[str, Tuple[float, float]]],
    metric: str
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

        # Netdata (%CPU)
        netdata_daemon: Dict[str, List[float]] = {}
        netdata_god: Dict[str, List[float]] = {}
        for s in intervals:
            netdata_daemon[s] = []
            netdata_god[s] = []
            for g in groups:
                daemon, god = util_netdata.get(g, {}).get(s, (np.nan, np.nan))
                netdata_daemon[s].append(daemon)
                netdata_god[s].append(god)

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
            # Netdata 側
            xpos_net = x + offsets[2 * i]
            net_label = net_label_map[s]

            if metric == "user":
                # go.d.plugin（下段、interval によらず同じ見た目）
                draw_bar(ax, xpos_net, netdata_god[s], "go.d.plugin", width, bottom=None)
                # Netdata daemon（上段、interval ごとに色分け）
                draw_bar(
                    ax,
                    xpos_net,
                    netdata_daemon[s],
                    net_label,
                    width,
                    bottom=np.array(netdata_god[s]),
                )
            else:
                # kernel のときは go.d.plugin=0 なので全て daemon 側
                draw_bar(ax, xpos_net, netdata_daemon[s], net_label, width)

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
        ax.set_ylim(bottom=1e-4)

        fig = ax.figure
        fig.text(0.055, 0.83, "log scale", fontsize=18, ha='left', va='bottom')

        ax.yaxis.grid(True, linestyle="--", linewidth=1.3, alpha=0.55)
        ax.set_axisbelow(True)

        from matplotlib.patches import Patch

        # Legend: Netdata(3) + go.d.plugin + X-Monitor(3)
        order = [
            "Netdata (1000ms)",
            "Netdata (500ms)",
            "Netdata (1ms)",
            "go.d.plugin",
            "X-Monitor (1000ms)",
            "X-Monitor (500ms)",
            "X-Monitor (1ms)",
        ]
        if metric == "kernel":
            # kernel では go.d.plugin は実質 0 だが、凡例から消すならここで remove
            order.remove("go.d.plugin")

        order = [lab for lab in order if (lab in COLORS and lab in HATCHES)]

        legend_items = [
            Patch(
                facecolor="white",
                edgecolor=COLORS[lab],
                hatch=HATCHES[lab],
                linewidth=1.6,
                label=lab
            )
            for lab in order
        ]

        ax.legend(
            handles=legend_items,
            loc="upper center",
            ncol=3,
            bbox_to_anchor=(0.5, 1.25),
            fontsize=14,
            frameon=True,
            framealpha=1.0,
        )
    finally:
        plt.rcParams["hatch.linewidth"] = old_hlw


# ---- メイン ----
def make_plots(
    base_dir: str,
    cpu_freq_hz: float = 3_800_000_000,
    mcd_nums: Optional[List[int]] = None,
    save: bool = True,
    out_prefix: str = "cpu_utilization",
):
    base = Path(base_dir)
    if mcd_nums is None:
        mcd_nums = [1, 5, 10]

    for metric in ("user", "kernel"):
        # X-Monitor 側
        files_xmon = _collect_xmon_files(base, metric, mcd_nums)
        if not files_xmon:
            print(f"[warn] No X-Monitor files for metric={metric}")
        util_xmon: Dict[int, Dict[str, float]] = {}
        for mcd, by_interval in files_xmon.items():
            util_xmon[mcd] = {}
            for interval, path in by_interval.items():
                u = compute_cpu_utilization(path, cpu_freq_hz)
                if u is not None:
                    util_xmon[mcd][interval] = u

        # Netdata 側
        files_net = _collect_netdata_files(base, metric, mcd_nums)
        if not files_net:
            print(f"[warn] No Netdata files for metric={metric}")
        util_netdata: Dict[int, Dict[str, Tuple[float, float]]] = {}
        for mcd, by_interval in files_net.items():
            util_netdata[mcd] = {}
            for interval, fp in by_interval.items():
                usage = parse_netdata_csv(fp)
                daemon = usage.get("netdata", np.nan)
                god = usage.get("go.d.plugin", 0.0 if metric=="kernel" else np.nan)
                if metric == "kernel":
                    god = 0.0
                util_netdata[mcd][interval] = (daemon, god)

        fig, ax = plt.subplots(figsize=figsize)
        _plot_grouped(ax, util_xmon, util_netdata, metric)
        fig.tight_layout()

        if save:
            pdf_path = base / f"{out_prefix}-{metric}.pdf"
            fig.savefig(pdf_path, bbox_inches="tight")
            print(f"[info] Saved: {pdf_path}")

        plt.show()