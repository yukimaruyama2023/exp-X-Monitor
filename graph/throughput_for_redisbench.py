import os
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from packaging import version



fontsize = 25  # default is 25
legend_fontsize = 23  # default is 17
# figsize = (24, 5)  # memcached だけの時はこれでちょうど良いサイズだった
figsize = (37, 4)  # default is (10, 7)
ylim = 1000
line_width = 0.70
GROUP_SPACING = 7.0
bbox_to_anchor = (0.5, 1.40)

##############################################
# fontsize = 25  # default is 25
# legend_fontsize = 23  # default is 17
# # figsize = (24, 5)  # memcached だけの時はこれでちょうど良いサイズだった
# figsize = (33, 4)  # default is (10, 7)
# ylim = 1000
# line_width = 0.70
# GROUP_SPACING = 7.0
# bbox_to_anchor = (0.5, 1.40)
###########################################

# redisbench 用: 各行は "GET: rps=XXXX ..." 形式
RPS_RE = re.compile(r"GET:\s*rps=([\d.]+)")

# 7 本構成のラベル
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


def _sum_rps_from_file(path: str) -> float:
    """
    redisbench の結果ファイルから
    `GET: rps=...` の値を全行分合計して返す。
    （平均ではなく **合計** なので注意）
    """
    total = 0.0
    with open(path) as f:
        for line in f:
            m = RPS_RE.search(line)
            if m:
                total += float(m.group(1))
    return total


def collect_throughput(log_dir, metric, n):
    """
    1 run_dir (= .../RUN_ID/NNNredis) から各ラベルの throughput を集める。
    各ファイル内の全行の rps を合計した値を throughput として扱う。
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

        # ファイルから GET: rps=... を合計する
        total_rps = _sum_rps_from_file(path)
        data[label].append(total_rps)
    return data


def collect_stats_across_runs(base_dir, metric, nums, run_ids=None):
    """
    base_dir/0..4/NNNredis 以下を見て、
    各ラベルの平均 throughput と標準偏差を計算する。

    throughput = 各ファイル内の rps 合計値 [ops/sec]
    表示単位は K ops/sec とするため 1000 で割る。
    """
    if run_ids is None:
        # redisbench 実験は 0〜4 の 5 回試行
        # run_ids = [str(i) for i in range(5)]
        run_ids = [str(i) for i in range(5)]

    means = {label: [] for label in LABELS}
    stds  = {label: [] for label in LABELS}

    for n in nums:
        per_label_values = {label: [] for label in LABELS}
        for rid in run_ids:
            run_dir = os.path.join(base_dir, rid, f"{n:03d}redis")
            if not os.path.isdir(run_dir):
                continue
            d = collect_throughput(run_dir, metric, n)
            for label in LABELS:
                if d[label]:
                    # 1 run あたり 1 個の throughput を追加
                    per_label_values[label].extend(d[label])

        for label in LABELS:
            vals = np.array(per_label_values[label], dtype=float) / 1000.0  # K ops/sec
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
    offsets = np.linspace(-width * 3, width * 3, len(LABELS))

    # ここだけ fig / ax を明示的に使う
    fig, ax = plt.subplots(figsize=figsize)

    # ハッチ線を太くして見やすく
    old_hatch_lw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = 1.6

    for i, label in enumerate(LABELS):
        xpos = x + offsets[i]

        # --- 下レイヤ: ハッチ＋色（枠も色） ---
        ax.bar(
            xpos,
            means[label],
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

        # --- 上レイヤ: 透明＋黒枠（ハッチなし） ---
        ax.bar(
            xpos,
            means[label],
            width=width,
            facecolor=(0, 0, 0, 0),
            edgecolor="black",
            linewidth=1.4,
            zorder=3,
        )

    # 戻す
    plt.rcParams["hatch.linewidth"] = old_hatch_lw

    # 軸
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in nums], fontsize=fontsize)
    ax.set_xlabel("Number of instances", fontsize=fontsize)
    ax.tick_params(axis="y", labelsize=fontsize)
    ax.set_ylabel("Throughput (K ops/sec)", fontsize=fontsize)
    ax.set_ylim(0, ylim)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # 凡例（グラフ外）
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
        p.set_path_effects(
            [pe.Stroke(linewidth=1.4, foreground="black"), pe.Normal()]
        )
        legend_handles.append(p)

    # legend オブジェクトを取得するのがポイント
    leg = ax.legend(
        legend_handles,
        LABELS,
        loc="upper center",
        bbox_to_anchor=bbox_to_anchor,
        ncol=7,
        fontsize=legend_fontsize,
        frameon=True,
    )

    # --- PDF + PNG 保存（凡例を bbox_extra_artists に明示） ---
    pdf_path = save_path
    png_path = save_path.replace(".pdf", ".png")

    for path in (pdf_path, png_path):
        fig.savefig(
            path,
            bbox_inches="tight",
            bbox_extra_artists=(leg,),
            pad_inches=0.3,
            dpi=300,
        )

    plt.show()
    plt.close(fig)

def plot_grouped_both(base_dir, nums=[1, 5, 10], run_ids=None):
    """
    base_dir は timestamp 直下（0〜4/NNNredis ...）を想定。

    nums は instance 数のリスト。
    例: [1, 4, 8, 12] などに変えて使ってください。
    """
    kernel_out = os.path.join(base_dir, "redis_throughput_kernel.pdf")
    user_out   = os.path.join(base_dir, "redis_throughput_user.pdf")

    # 1枚目: kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    _plot_one_metric(means_k, stds_k, nums, save_path=kernel_out)

    # 2枚目: user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    _plot_one_metric(means_u, stds_u, nums, save_path=user_out)


def print_throughput_means(base_dir, nums, run_ids=None):
    # kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    print("===== Kernel metrics: Throughput Means (K ops/sec) =====")
    for label in LABELS:
        print(f"\n[ {label} ]")
        for n, v in zip(nums, means_k[label]):
            print(f"  {n} redis : {v:.3f} K ops/sec")

    # user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    print("\n===== User metrics: Throughput Means (K ops/sec) =====")
    for label in LABELS:
        print(f"\n[ {label} ]")
        for n, v in zip(nums, means_u[label]):
            print(f"  {n} redis : {v:.3f} K ops/sec")