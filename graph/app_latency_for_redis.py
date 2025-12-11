import os
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from packaging import version

####################  configuration #################################

# fontsize = 25  # default is 25
# legend_fontsize = 23  # default is 17
# # figsize = (24, 5)  # default is (10, 7)
# figsize = (33, 4)  # default is (10, 7)

# # 99th latency 用の ylim（必要に応じて調整してください）
# ylim = 10

# line_width = 0.70
# GROUP_SPACING = 7.0
# bbox_to_anchor = (0.5, 1.40)
####################################################################
fontsize = 25  # default is 25
legend_fontsize = 23  # default is 17
# figsize = (24, 5)  # memcached だけの時はこれでちょうど良いサイズだった
figsize = (37, 4)  # default is (10, 7)
ylim = 9
line_width = 0.70
GROUP_SPACING = 7.0
bbox_to_anchor = (0.5, 1.37)
#######################################################
# fontsize = 25  # default is 25
# legend_fontsize = 23  # default is 17
# # figsize = (24, 5)  # memcached だけの時はこれでちょうど良いサイズだった
# figsize = (37, 4)  # default is (10, 7)
# ylim = 1000
# line_width = 0.70
# GROUP_SPACING = 7.0
# bbox_to_anchor = (0.5, 1.40)
##############################################################################

# redisbench 用: 各行は "GET: rps=... p99 X.XXXXXX ..." 形式
P99_RE = re.compile(r"p99\s+([0-9.]+)")



# 7 本構成のラベル（throughput と同じ）
LABELS = [
    "No Monitoring",
    "Netdata (1000ms)",
    "Netdata (500ms)",
    "Netdata (1ms)",
    "X-Monitor (1000ms)",
    "X-Monitor (500ms)",
    "X-Monitor (1ms)",
]

################# Label ↔ interval(sec) / tool 対応 ################
LABEL_META = {
    "No Monitoring": {
        "tool": None,       # interval なし
        "interval": None,
    },
    # Netdata: 1000 / 500 / 1ms
    "Netdata (1000ms)": {
        "tool": "netdata",
        "interval": 1.0,    # 1000ms = 1.0s
    },
    "Netdata (500ms)": {
        "tool": "netdata",
        "interval": 0.5,    # 500ms = 0.5s
    },
    "Netdata (1ms)": {
        "tool": "netdata",
        "interval": 0.001,  # 1ms = 0.001s
    },
    # X-Monitor: 1000 / 500 / 1ms
    "X-Monitor (1000ms)": {
        "tool": "xmonitor",
        "interval": 1.0,
    },
    "X-Monitor (500ms)": {
        "tool": "xmonitor",
        "interval": 0.5,
    },
    "X-Monitor (1ms)": {
        "tool": "xmonitor",
        "interval": 0.001,
    },
}

################# Design Configuration ############

COLORS = {
    "No Monitoring":        "#6E738D",  # Neutral gray (base)

    # Netdata 系
    "Netdata (1000ms)":     "#F5A97F",  # Peach（既存）
    "Netdata (500ms)":      "#F28F79",
    "Netdata (1ms)":        "#E46876",

    # X-Monitor 系
    "X-Monitor (1000ms)":   "#5AB8A8",  # Teal（既存）
    "X-Monitor (500ms)":    "#72A7E3",  # 以前の 100ms の色
    "X-Monitor (1ms)":      "#C7A0E8",  # 以前の 10ms の色
}

HATCHES = {
    "No Monitoring":        "***",
    "Netdata (1000ms)":     "////",
    "Netdata (500ms)":      "----",
    "Netdata (1ms)":        "ooo",

    "X-Monitor (1000ms)":   "\\\\\\\\",
    "X-Monitor (500ms)":    "xxxx",
    "X-Monitor (1ms)":      "....",
}

EDGE_KW = dict(edgecolor="black", linewidth=1.1)
####################################################


def _find_interval_files_txt(log_dir: str, tool: str, metric: str, n: int):
    """
    {tool}-{metric}metrics-{n}redis-interval*.txt を全部拾って
    [(interval_sec, path), ...] を interval 昇順で返す。
    """
    import glob

    pattern = os.path.join(
        log_dir, f"{tool}-{metric}metrics-{n}redis-interval*.txt"
    )
    files = glob.glob(pattern)
    found = []
    for f in files:
        m = re.search(r"interval([0-9.]+)\.txt$", f)
        if not m:
            continue
        sec = float(m.group(1))
        found.append((sec, f))
    found.sort(key=lambda x: x[0])
    return found


def _select_file_for_interval(
    log_dir: str, tool: str, metric: str, n: int, target_interval: float
):
    """
    指定された tool/metric/n に対して、
    interval*.txt の中から target_interval(s) に一致するファイルを 1 つ選ぶ。
    見つからなければ None を返す。
    """
    candidates = _find_interval_files_txt(log_dir, tool, metric, n)
    for sec, path in candidates:
        if abs(sec - target_interval) < 1e-9:
            return path
    return None


def _median_p99_from_file(path: str):
    """
    redisbench の結果ファイルから
    `p99` の値を全行分集め、その中央値を返す。
    （1 ファイル = 1 実験 = 1 つの 99th latency 値）
    """
    vals = []
    with open(path) as f:
        for line in f:
            m = P99_RE.search(line)
            if m:
                vals.append(float(m.group(1)))
    if not vals:
        return None
    arr = np.array(vals, dtype=float)
    return float(np.median(arr))


def collect_latency99(log_dir, metric, n):
    """
    1 run_dir (= .../RUN_ID/NNNredis) から各ラベルの 99th latency を集める。

    各ファイルについて:
      - 各行の p99 値を集めて中央値を計算
      - その中央値を「このファイルの 99th latency」とする
    """
    data = {label: [] for label in LABELS}
    for label in LABELS:
        meta = LABEL_META[label]

        # No Monitoring: interval なし、固定ファイル名
        if meta["tool"] is None:
            path = os.path.join(log_dir, f"no_monitoring-{n}redis.txt")
            if not os.path.exists(path):
                continue
        else:
            tool = meta["tool"]
            interval_sec = meta["interval"]

            path = _select_file_for_interval(
                log_dir, tool=tool, metric=metric, n=n, target_interval=interval_sec
            )
            if path is None or not os.path.exists(path):
                # その interval のファイルが存在しない場合はスキップ
                continue

        # ファイルから p99 を行ごとに拾い、その中央値を 1 値として使う
        med_p99 = _median_p99_from_file(path)
        if med_p99 is not None:
            data[label].append(med_p99)
    return data


def collect_stats_across_runs(base_dir, metric, nums, run_ids=None):
    """
    base_dir/0..4/NNNredis 以下を見て、
    各ラベルの 99th latency (ms) の平均と標準偏差を計算する。

    1 つの run (例: run_id=0) では:
      - 各ラベルごとに 1 つの「ファイル中央値の p99」が得られる
      - run_ids 0〜4 の 5 個から平均＆不偏標準偏差を計算
    """
    if run_ids is None:
        # redisbench 実験は 0〜4 の 5 回試行
        # run_ids = [str(i) for i in range(5)]
        run_ids = [str(i) for i in range(3)]

    means = {label: [] for label in LABELS}
    stds  = {label: [] for label in LABELS}

    for n in nums:
        per_label_values = {label: [] for label in LABELS}
        for rid in run_ids:
            run_dir = os.path.join(base_dir, rid, f"{n:03d}redis")
            if not os.path.isdir(run_dir):
                continue
            d = collect_latency99(run_dir, metric, n)
            for label in LABELS:
                if d[label]:
                    # 1 run あたり 1 個の「ファイル中央値 p99」を追加
                    per_label_values[label].extend(d[label])

        for label in LABELS:
            vals = np.array(per_label_values[label], dtype=float)  # ms
            if vals.size == 0:
                means[label].append(0.0)
                stds[label].append(0.0)
            elif vals.size == 1:
                means[label].append(float(vals[0]))
                stds[label].append(0.0)
            else:
                means[label].append(float(np.mean(vals)))
                stds[label].append(float(np.std(vals, ddof=1)))  # 不偏標準偏差
    return means, stds


def _plot_one_metric(means, stds, nums, save_path):
    x = np.arange(len(nums)) * GROUP_SPACING
    width = line_width
    offsets = np.linspace(-width*3, width*3, len(LABELS))

    plt.figure(figsize=figsize)

    # ハッチ線を太くして見やすく
    old_hatch_lw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = 1.6

    for i, label in enumerate(LABELS):
        xpos = x + offsets[i]

        # --- 下レイヤ ---
        plt.bar(
            xpos, means[label],
            yerr=stds[label],
            width=width,
            facecolor="white",
            edgecolor=COLORS[label],
            hatch=HATCHES[label],
            capsize=4,
            ecolor="black",
            error_kw={"elinewidth": 1.2},
            linewidth=1.2,
            zorder=2,
        )

        # --- 上レイヤ ---
        plt.bar(
            xpos, means[label],
            width=width,
            facecolor=(0, 0, 0, 0),
            edgecolor="black",
            linewidth=1.4,
            zorder=3,
        )

    plt.rcParams["hatch.linewidth"] = old_hatch_lw

    # 軸設定
    plt.xticks(x, [str(n) for n in nums], fontsize=fontsize)
    plt.xlabel("Number of instances", fontsize=fontsize)
    plt.tick_params(axis='y', labelsize=fontsize)
    plt.ylabel("99th latency (ms)", fontsize=fontsize)
    plt.ylim(0, ylim)
    plt.grid(axis="y", linestyle="--", alpha=0.4)

    # 凡例
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as pe
    legend_handles = []
    for label in LABELS:
        p = mpatches.Patch(
            facecolor="white",
            edgecolor=COLORS[label],
            hatch=HATCHES[label],
            linewidth=1.2,
        )
        p.set_path_effects([pe.Stroke(linewidth=1.4, foreground="black"), pe.Normal()])
        legend_handles.append(p)

    plt.legend(
        legend_handles,
        LABELS,
        loc="upper center",
        bbox_to_anchor=bbox_to_anchor,
        ncol=7,
        fontsize=legend_fontsize,
        frameon=True
    )

    # --- ここだけ追加・修正 ---
    plt.savefig(save_path, bbox_inches="tight", dpi=300)               # PDF
    # plt.savefig(save_path.replace(".pdf", ".png"), dpi=300)           # PNG
    plt.savefig(
        save_path.replace(".pdf", ".png"),
        bbox_inches="tight",
        pad_inches=0.2,
        dpi=300
    )



    plt.show()
    plt.close()

def plot_grouped_both(base_dir, nums=[1, 5, 10], run_ids=None):
    """
    base_dir は timestamp 直下（0〜4/NNNredis ...）を想定。

    nums は instance 数のリスト。
    例: [1, 4, 8, 12] などに変えて使ってください。
    """
    kernel_out = os.path.join(base_dir, "redis_latency99_kernel.pdf")
    user_out   = os.path.join(base_dir, "redis_latency99_user.pdf")

    # 1枚目: kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    _plot_one_metric(means_k, stds_k, nums, save_path=kernel_out)

    # 2枚目: user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    _plot_one_metric(means_u, stds_u, nums, save_path=user_out)


def print_latency99_means(base_dir, nums, run_ids=None):
    # kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    print("===== Kernel metrics: 99th latency (ms) =====")
    for label in LABELS:
        print(f"\n[ {label} ]")
        for n, v in zip(nums, means_k[label]):
            print(f"  {n} redis : {v:.3f} ms")

    # user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    print("\n===== User metrics: 99th latency (ms) =====")
    for label in LABELS:
        print(f"\n[ {label} ]")
        for n, v in zip(nums, means_u[label]):
            print(f"  {n} redis : {v:.3f} ms")