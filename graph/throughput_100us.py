from throughput import (
    COLORS,
    HATCHES,
    THROUGHPUT_RE,
)

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe

###################### 描画設定 ######################
fontsize = 25
legend_fontsize = 18
figsize = (9, 5)
ylim = 1000
line_width = 0.40
GROUP_SPACING = 2.0
bbox_to_anchor = (0.5, 1.27)

DEFAULT_COLOR = "#AAAAAA"
DEFAULT_HATCH = ""

# 今回描画したいラベル（凡例の順番）
PLOT_LABELS = [
    "No Monitoring",
    "Netdata (100μs)",
    "X-Monitor (100μs)",
]

# throughput.py の色・ハッチを流用しつつ 100μs ラベルに割り当て
COLOR_MAP = {
    "No Monitoring": COLORS.get("No Monitoring", DEFAULT_COLOR),
    "Netdata (100μs)": COLORS.get(
        "Netdata (1ms)",
        COLORS.get("Netdata (1000ms)", DEFAULT_COLOR),
    ),
    "X-Monitor (100μs)": COLORS.get(
        "X-Monitor (1ms)",
        COLORS.get("X-Monitor (1000ms)", DEFAULT_COLOR),
    ),
}

HATCH_MAP = {
    "No Monitoring": HATCHES.get("No Monitoring", DEFAULT_HATCH),
    "Netdata (100μs)": HATCHES.get(
        "Netdata (1ms)",
        HATCHES.get("Netdata (1000ms)", DEFAULT_HATCH),
    ),
    "X-Monitor (100μs)": HATCHES.get(
        "X-Monitor (1ms)",
        HATCHES.get("X-Monitor (1000ms)", DEFAULT_HATCH),
    ),
}

######################## スループット用ユーティリティ ########################

def _parse_throughput(path: str) -> float | None:
    """
    ファイルから Total QPS を 1 つ取り出す。
    返り値は QPS (ops/sec)。
    """
    with open(path) as f:
        for line in f:
            m = THROUGHPUT_RE.search(line)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    return None
    return None


def collect_throughput_12mcd(base_dir: str, metric: str, run_ids=None):
    """
    base_dir/0/012mcd, ..., base_dir/4/012mcd の 5 run から，
    12 mcd の Total QPS を集める。

    metric: "kernel" or "user"
    戻り値:
        means, stds （単位は K ops/sec）
    """
    if run_ids is None:
        run_ids = [str(i) for i in range(5)]  # "0".."4"

    # 各ラベルごとの生データ（QPS）
    per_label_values = {label: [] for label in PLOT_LABELS}

    for rid in run_ids:
        run_dir = os.path.join(base_dir, rid, "012mcd")

        # --- No Monitoring ---
        path_no = os.path.join(run_dir, "no_monitoring-12mcd.txt")
        if os.path.exists(path_no):
            qps = _parse_throughput(path_no)
            if qps is not None:
                per_label_values["No Monitoring"].append(qps)

        # --- Netdata (100μs) ---
        net_path = os.path.join(
            run_dir,
            f"netdata-{metric}metrics-12mcd-interval0.0001.txt",
        )
        if os.path.exists(net_path):
            qps = _parse_throughput(net_path)
            if qps is not None:
                per_label_values["Netdata (100μs)"].append(qps)

        # --- X-Monitor (100μs) ---
        xmon_path = os.path.join(
            run_dir,
            f"xmonitor-{metric}metrics-12mcd-interval0.0001.txt",
        )
        if os.path.exists(xmon_path):
            qps = _parse_throughput(xmon_path)
            if qps is not None:
                per_label_values["X-Monitor (100μs)"].append(qps)

    # QPS -> K ops/sec に変換しつつ平均と標準偏差を計算
    means = {}
    stds = {}
    for label in PLOT_LABELS:
        vals = np.array(per_label_values[label], dtype=float) / 1000.0  # -> K ops/sec
        if vals.size == 0:
            means[label] = 0.0
            stds[label] = 0.0
        elif vals.size == 1:
            means[label] = float(vals[0])
            stds[label] = 0.0
        else:
            means[label] = float(np.mean(vals))
            stds[label] = float(np.std(vals, ddof=1))
    return means, stds


def _plot_throughput_12mcd_combined(
    means_user, stds_user, means_kernel, stds_kernel, save_path: str
):
    """
    12 instance 固定で、
    左に user metrics、右に kernel metrics を並べて描画する。
    各グループの中に
      No Monitoring / Netdata (100μs) / X-Monitor (100μs)
    を描く。
    """
    # グループ中心位置: 左(user), 右(kernel)
    group_centers = np.array(
        [-GROUP_SPACING / 2.0, GROUP_SPACING / 2.0]
    )

    width = line_width
    # グループ内でラベルを左右に振るオフセット
    offsets = np.linspace(-width, width, len(PLOT_LABELS))

    plt.figure(figsize=figsize)

    old_hatch_lw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = 1.6

    # 0: user, 1: kernel
    for g_idx, (group_label, means, stds) in enumerate(
        [
            ("user metrics", means_user, stds_user),
            ("kernel metrics", means_kernel, stds_kernel),
        ]
    ):
        center = group_centers[g_idx]

        for i, label in enumerate(PLOT_LABELS):
            xpos = center + offsets[i]
            color = COLOR_MAP.get(label, DEFAULT_COLOR)
            hatch = HATCH_MAP.get(label, DEFAULT_HATCH)

            # 下レイヤ: 色＋ハッチ
            plt.bar(
                xpos,
                means[label],
                yerr=stds[label],
                width=width,
                facecolor="white",
                edgecolor=color,
                hatch=hatch,
                capsize=4,
                ecolor="black",
                error_kw={"elinewidth": 1.2},
                linewidth=1.2,
                zorder=2,
            )

            # 上レイヤ: 黒枠
            plt.bar(
                xpos,
                means[label],
                width=width,
                facecolor=(0, 0, 0, 0),
                edgecolor="black",
                linewidth=1.4,
                zorder=3,
            )

    plt.rcParams["hatch.linewidth"] = old_hatch_lw

    # x 軸は「user metrics」「Kernel metrics」の 2 つだけ
    plt.xticks(
        group_centers,
        ["user metrics", "kernel metrics"],
        fontsize=fontsize,
    )

    plt.tick_params(axis="y", labelsize=fontsize)
    plt.ylabel("Throughput (K ops/sec)", fontsize=fontsize)
    plt.ylim(0, ylim)
    plt.grid(axis="y", linestyle="--", alpha=0.4)

    # 凡例
    legend_handles = []
    for label in PLOT_LABELS:
        color = COLOR_MAP.get(label, DEFAULT_COLOR)
        hatch = HATCH_MAP.get(label, DEFAULT_HATCH)
        p = mpatches.Patch(
            facecolor="white",
            edgecolor=color,
            hatch=hatch,
            linewidth=1.2,
        )
        p.set_path_effects(
            [pe.Stroke(linewidth=1.4, foreground="black"), pe.Normal()]
        )
        legend_handles.append(p)

    plt.legend(
        legend_handles,
        PLOT_LABELS,
        loc="upper center",
        bbox_to_anchor=bbox_to_anchor,
        ncol=len(PLOT_LABELS),
        fontsize=legend_fontsize,
        frameon=True,
    )

    plt.savefig(save_path, bbox_inches="tight", dpi=300)
    plt.show()
    plt.close()


def plot_throughput_12mcd(base_dir: str, run_ids=None):
    """
    user / kernel のスループットを 1 枚のグラフにまとめて出力する。

    出力:
        base_dir/memcached_throughput_user_kernel_100μs.pdf
    """
    # まず user と kernel それぞれの平均・標準偏差を取得
    means_user, stds_user = collect_throughput_12mcd(base_dir, "user", run_ids)
    means_kernel, stds_kernel = collect_throughput_12mcd(base_dir, "kernel", run_ids)

    # コンソール用に数値も出しておく
    print(
        "\n===== Throughput (K ops/sec): Means for user metrics "
        "(12 mcd, 100μs) ====="
    )
    for label in PLOT_LABELS:
        print(
            f"[ user   | {label} ] mean={means_user[label]:.3f} K ops/sec "
            f"(std={stds_user[label]:.3f})"
        )

    print(
        "\n===== Throughput (K ops/sec): Means for kernel metrics "
        "(12 mcd, 100μs) ====="
    )
    for label in PLOT_LABELS:
        print(
            f"[ kernel | {label} ] mean={means_kernel[label]:.3f} K ops/sec "
            f"(std={stds_kernel[label]:.3f})"
        )

    out_path = os.path.join(
        base_dir,
        "memcached_throughput_user_kernel_100μs.pdf",
    )
    _plot_throughput_12mcd_combined(
        means_user,
        stds_user,
        means_kernel,
        stds_kernel,
        save_path=out_path,
    )


def print_throughput_12mcd_means(base_dir: str, run_ids=None):
    """
    グラフは描画せず，user / kernel の平均値だけを表示したい場合のユーティリティ。
    """
    means_user, stds_user = collect_throughput_12mcd(base_dir, "user", run_ids)
    means_kernel, stds_kernel = collect_throughput_12mcd(base_dir, "kernel", run_ids)

    print(
        "\n===== Throughput (K ops/sec): Means for user metrics "
        "(12 mcd, 100μs) ====="
    )
    for label in PLOT_LABELS:
        print(
            f"[ user   | {label} ] mean={means_user[label]:.3f} K ops/sec "
            f"(std={stds_user[label]:.3f})"
        )

    print(
        "\n===== Throughput (K ops/sec): Means for kernel metrics "
        "(12 mcd, 100μs) ====="
    )
    for label in PLOT_LABELS:
        print(
            f"[ kernel | {label} ] mean={means_kernel[label]:.3f} K ops/sec "
            f"(std={stds_kernel[label]:.3f})"
        )