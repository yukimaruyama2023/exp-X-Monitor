import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe

# ここはあなたのファイルと同じ前提
from throughput import COLORS, HATCHES, THROUGHPUT_RE
from app_latency_100us import collect_latency99_12mcd
from throughput_100us import collect_throughput_12mcd

################### config ######################
fontsize = 27
legend_fontsize = 24 
figsize_combined = (14, 5)
ylim_latency = 6
ylim_throughput = 1000
wspace = 1.0 # space between left and right graph
line_width = 0.20
GROUP_SPACING = 1.0
###################### 共通設定 ######################
# fontsize = 25
# legend_fontsize = 18
# figsize_combined = (16, 5)  # 左右 2 枚なので少し横長に
# ylim_latency = 6
# ylim_throughput = 1000
# line_width = 0.50
# GROUP_SPACING = 2.0
##########################################################

DEFAULT_COLOR = "#AAAAAA"
DEFAULT_HATCH = ""

PLOT_LABELS = [
    "No Monitoring",
    "Netdata (100μs)",
    "X-Monitor (100μs)",
]

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

###################### ここは既存の collect_* を使う前提 ######################
# - collect_latency99_12mcd(base_dir, metric, run_ids)
# - collect_throughput_12mcd(base_dir, metric, run_ids)
# はあなたのコードのままで OK とします


def _plot_bar_user_kernel_on_axes(ax, means_user, stds_user,
                                  means_kernel, stds_kernel,
                                  ylabel: str, ylim: float):
    """
    1つの Axes 上に
      x 軸: [user metrics, kernel metrics]
      各グループ内: PLOT_LABELS の 3 本バー
    を描画するユーティリティ。
    """
    group_centers = np.array(
        [-GROUP_SPACING / 2.0, GROUP_SPACING / 2.0]
    )
    width = line_width
    offsets = np.linspace(-width, width, len(PLOT_LABELS))

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
            ax.bar(
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
            ax.bar(
                xpos,
                means[label],
                width=width,
                facecolor=(0, 0, 0, 0),
                edgecolor="black",
                linewidth=1.4,
                zorder=3,
            )

    plt.rcParams["hatch.linewidth"] = old_hatch_lw

    ax.set_xticks(group_centers)
    ax.set_xticklabels(["user metrics", "kernel metrics"], fontsize=fontsize)
    ax.tick_params(axis="y", labelsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.set_ylim(0, ylim)
    ax.grid(axis="y", linestyle="--", alpha=0.4)


def _build_common_legend_handles():
    """
    共通の凡例ハンドルを作成して返す。
    fig.legend に渡して使う想定。
    """
    handles = []
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
        handles.append(p)
    return handles


def plot_latency_and_throughput_12mcd(base_dir: str, run_ids=None):
    """
    左に 99th latency, 右に throughput,
    上部に共通の凡例を持つ 1 枚の図を出力する。
    """
    # --- データ集計 ---
    # latency (ms)
    means_lat_user, stds_lat_user = collect_latency99_12mcd(base_dir, "user", run_ids)
    means_lat_kernel, stds_lat_kernel = collect_latency99_12mcd(base_dir, "kernel", run_ids)

    # throughput (K ops/sec)
    means_thr_user, stds_thr_user = collect_throughput_12mcd(base_dir, "user", run_ids)
    means_thr_kernel, stds_thr_kernel = collect_throughput_12mcd(base_dir, "kernel", run_ids)

    # --- Figure / Axes 作成 ---
    fig, (ax_left, ax_right) = plt.subplots(
        1, 2, figsize=figsize_combined, sharex=True
    )
    fig.subplots_adjust(wspace=wspace)

    # 左: latency
    _plot_bar_user_kernel_on_axes(
        ax_left,
        means_lat_user,
        stds_lat_user,
        means_lat_kernel,
        stds_lat_kernel,
        ylabel="99th latency (ms)",
        ylim=ylim_latency,
    )
    ax_left.set_xlabel("99th latency", fontsize=fontsize)
    ax_left.xaxis.labelpad = 10  # 余白が要らなければこの行は削ってOK

    # 右: throughput
    _plot_bar_user_kernel_on_axes(
        ax_right,
        means_thr_user,
        stds_thr_user,
        means_thr_kernel,
        stds_thr_kernel,
        ylabel="Throughput (K ops/sec)",
        ylim=ylim_throughput,
    )
    ax_right.set_xlabel("throughput", fontsize=fontsize)
    ax_right.xaxis.labelpad = 10  # 同上

    # --- 共通凡例 ---
    legend_handles = _build_common_legend_handles()
    fig.legend(
        legend_handles,
        PLOT_LABELS,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.15),
        ncol=len(PLOT_LABELS),
        fontsize=legend_fontsize,
        frameon=True,
    )

    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.95])  # 上に凡例を置くので少し縮める

    out_path = os.path.join(
        base_dir,
        "memcached_latency99_throughput_user_kernel_100μs.pdf",
    )
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.show()
    plt.close(fig)