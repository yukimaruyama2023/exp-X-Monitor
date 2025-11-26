from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

HATCH_LINEWIDTH = 1.6  
fontsize = 25
labelsize = 25
figsize = (12, 6.5) # default is (9, 6.5)
# --- 追加：グローバルで統一色を定義 ---

# 統一パレット（任意）
COLORS = {
    "Netdata":             "#F5A97F",   # Peach
    # "go.d.plugin":         "#EBA0AC", 
    "go.d.plugin":         "#E28C8C", 
    "X-Monitor (1000ms)":  "#5AB8A8",   # Teal
    "X-Monitor (100ms)":   "#72A7E3",   # Blue
    "X-Monitor (10ms)":    "#C7A0E8",   # Lavender
}

HATCHES = {
    "Netdata":        "////",
    "go.d.plugin":    "***",
    "X-Monitor (1000ms)":  "\\\\\\\\",
    "X-Monitor (100ms)":   "xxxxx",
    "X-Monitor (10ms)":    "....",
}

# 縁取り（CPU 図の棒で使用）
EDGE_KW = dict(edgecolor="black", linewidth=0.6)

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
            # parts[0]='Average:', [1]=UID, [2]=PID, [3]=%usr, [4]=%system,
            # [5]=%guest, [6]=%wait, [7]=%CPU, [8]=CPU, [9:]=Command
            try:
                cpu_pct = float(parts[7])
            except ValueError:
                continue
            cmd = parts[9]
            usage[cmd] = cpu_pct
    return usage

# ---- ファイル探索 ----
def _collect_xmon_files(
    base_dir: Path,
    metric: str,
    mcd_nums: Optional[List[int]] = None,
) -> Dict[int, Dict[str, Path]]:
    """
    metric: 'user' or 'kernel'
    mcd_nums: [1,5,10,...] のような memcached instance 数のリスト
    戻り値: {mcd_num: {interval_str: Path, ...}, ...}
    """
    assert metric in ("user", "kernel")
    if mcd_nums is None:
        mcd_nums = [1, 5, 10]  # 従来のデフォルト

    intervals = ["1", "0.1", "0.01"]
    result: Dict[int, Dict[str, Path]] = {}

    for mcd_num in mcd_nums:
        d = f"{mcd_num:03d}mcd"
        sub = base_dir / d
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


def _collect_netdata_files(
    base_dir: Path,
    metric: str,
    mcd_nums: Optional[List[int]] = None,
) -> Dict[int, Path]:
    """
    metric: 'user' or 'kernel'
    mcd_nums: [1,5,10,...]
    戻り値: {mcd_num: Path}
    """
    assert metric in ("user", "kernel")
    if mcd_nums is None:
        mcd_nums = [1, 5, 10]  # 従来のデフォルト

    result: Dict[int, Path] = {}
    for mcd_num in mcd_nums:
        d = f"{mcd_num:03d}mcd"
        sub = base_dir / d
        if not sub.is_dir():
            continue

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


def draw_bar(ax, xpos, height, label, width, bottom=None):
    # 下レイヤ：色ハッチ + 色枠
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
    # 上レイヤ：透明 + 黒枠
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
def _plot_grouped(ax, util_xmon: Dict[int, Dict[str, float]],
                  util_netdata: Dict[int, Tuple[float, float]],
                  metric: str):

    # --- ここを追加：ハッチ線の太さを一時的に 1.6 に ---
    old_hlw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = HATCH_LINEWIDTH
    try:
        groups = sorted(set(util_xmon.keys()) | set(util_netdata.keys()))  # [1,5,10,...]
        x = np.arange(len(groups))
        width = 0.18
        offsets = np.linspace(-1.5*width, 1.5*width, 4)

        # % へ変換
        xmon_pct = {
            s: [util_xmon.get(g, {}).get(s, float('nan')) * 100 for g in groups]
            for s in ["1", "0.1", "0.01"]
        }
        netdata_daemon = [util_netdata.get(g, (np.nan, np.nan))[0] for g in groups]
        netdata_god    = [util_netdata.get(g, (np.nan, np.nan))[1] for g in groups]

        # --- Netdata（stacked）---
        if metric == "user":
            # go.d.plugin（下段）
            draw_bar(ax, x + offsets[0], netdata_god, "go.d.plugin", width, bottom=None)
            # Netdata（上段, bottom=go.d）
            draw_bar(ax, x + offsets[0], netdata_daemon, "Netdata", width,
                     bottom=np.array(netdata_god))
        else:
            draw_bar(ax, x + offsets[0], netdata_daemon, "Netdata", width)

        # --- X-Monitor ---
        draw_bar(ax, x + offsets[1], xmon_pct["1"],    "X-Monitor (1000ms)", width)
        draw_bar(ax, x + offsets[2], xmon_pct["0.1"],  "X-Monitor (100ms)",  width)
        draw_bar(ax, x + offsets[3], xmon_pct["0.01"], "X-Monitor (10ms)",   width)

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
        ax.set_axisbelow(True)  # 棒の下にグリッドを敷く

        from matplotlib.patches import Patch

        # ---- Legend（色付きハッチ + 黒枠）----
        order = ["Netdata", "go.d.plugin", "X-Monitor (1000ms)",
                 "X-Monitor (100ms)", "X-Monitor (10ms)"]
        if metric == "kernel":
            order.remove("go.d.plugin")  # kernel では go.d.plugin を出さない

        # 実在キーだけ残す
        order = [lab for lab in order if (lab in COLORS and lab in HATCHES)]

        legend_items = [
            Patch(
                facecolor="white",           # 塗りは白
                edgecolor=COLORS[lab],       # ハッチ色と同系で縁取り
                hatch=HATCHES[lab],          # 模様
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
        # --- 忘れずに元へ戻す（他の図へ副作用を残さない）---
        plt.rcParams["hatch.linewidth"] = old_hlw


# ---- メイン ----
def make_plots(
    base_dir: str,
    cpu_freq_hz: float = 3_800_000_000,
    mcd_nums: Optional[List[int]] = None,
    save: bool = True,
    out_prefix: str = "cpu_utilization",
):
    """
    base_dir: タイムスタンプ直下のディレクトリ
    mcd_nums: [1,5,10,...]
    save:    True のとき PNG を保存
    out_prefix: 出力 PNG の接頭辞
    """
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
        util_netdata: Dict[int, Tuple[float, float]] = {}
        for mcd, fp in files_net.items():
            usage = parse_netdata_csv(fp)
            daemon = usage.get("netdata", np.nan)
            god = usage.get("go.d.plugin", 0.0 if metric=="kernel" else np.nan)
            if metric == "kernel":
                god = 0.0
            util_netdata[mcd] = (daemon, god)

        # プロット
        fig, ax = plt.subplots(figsize=figsize)
        _plot_grouped(ax, util_xmon, util_netdata, metric)
        fig.tight_layout()

        # ---- PNG 保存のみ ----
        if save:
            png_path = base / f"{out_prefix}-{metric}.png"
            fig.savefig(png_path, bbox_inches="tight")
            print(f"[info] Saved: {png_path}")

        plt.show()