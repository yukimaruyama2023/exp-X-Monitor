import os
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from packaging import version


fontsize = 25
legend_fontsize = 17

THROUGHPUT_RE = re.compile(r"Total QPS\s*=\s*([\d.]+)")

LABELS = [
    "No Monitoring",
    "Netdata (1000ms)",
    "X-Monitor (1000ms)",
    "X-Monitor (100ms)",
    "X-Monitor (10ms)",
]

FILE_PATTERNS = {
    "No Monitoring":        "no_monitoring-{num}mcd.txt",
    "Netdata (1000ms)":     "netdata-{metric}metrics-{num}mcd.txt",
    "X-Monitor (1000ms)":   "xmonitor-{metric}metrics-{num}mcd-interval1.txt",
    "X-Monitor (100ms)":    "xmonitor-{metric}metrics-{num}mcd-interval0.1.txt",
    "X-Monitor (10ms)":     "xmonitor-{metric}metrics-{num}mcd-interval0.01.txt",
}


################# Design Configuration ############

COLORS = {
    "No Monitoring":      "#6E738D",  # Neutral gray (base)
    "Netdata (1000ms)":   "#F5A97F",  # Peach (warm)
    "X-Monitor (1000ms)": "#5AB8A8",  # Clear teal（強めに差別化）
    "X-Monitor (100ms)":  "#72A7E3",  # Distinct blue (青方向に大きくずらす)
    "X-Monitor (10ms)":   "#C7A0E8",  # Lavender-purple（明確に他と離す）
}

HATCHES = {
    "No Monitoring":      "***",          # 無地
    "Netdata (1000ms)":   "////",      # 密な斜線
    "X-Monitor (1000ms)": "\\\\\\\\",  # 密な逆斜線
    "X-Monitor (100ms)":  "xxxxx",    # 密なクロス
    "X-Monitor (10ms)":   "....",    # 密なドット
}

# HATCHES = {
#     "No Monitoring": "",
#     "Netdata (1000ms)": "",
#     "X-Monitor (1000ms)": "",
#     "X-Monitor (100ms)": "",
#     "X-Monitor (10ms)": "",
# }

EDGE_KW = dict(edgecolor="black", linewidth=1.1)
####################################################

def collect_throughput(log_dir, metric, n):
    data = {label: [] for label in LABELS}
    for label in LABELS:
        path = os.path.join(log_dir, FILE_PATTERNS[label].format(metric=metric, num=str(n)))
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                m = THROUGHPUT_RE.search(line)
                if m:
                    data[label].append(float(m.group(1)))  # QPS
                    break
    return data

def collect_stats_across_runs(base_dir, metric, nums, run_ids=None):
    if run_ids is None:
        run_ids = [str(i) for i in range(10)]  # "0".."9"

    means = {label: [] for label in LABELS}
    stds  = {label: [] for label in LABELS}

    for n in nums:
        per_label_values = {label: [] for label in LABELS}
        for rid in run_ids:
            run_dir = os.path.join(base_dir, rid, f"{n:03d}mcd")
            d = collect_throughput(run_dir, metric, n)
            for label in LABELS:
                if d[label]:
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
    import matplotlib.pyplot as plt

    x = np.arange(len(nums))
    width = 0.13
    offsets = np.linspace(-width*2, width*2, len(LABELS))

    plt.figure(figsize=(10, 7))

    # ハッチ線を太くして見やすく
    old_hatch_lw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = 1.6

    for i, label in enumerate(LABELS):
        xpos = x + offsets[i]

        # --- 下レイヤ: ハッチ＋色（枠も色） ---
        plt.bar(
            xpos, means[label],
            yerr=stds[label],
            width=width,
            facecolor="white",
            edgecolor=COLORS[label],    # ← ハッチ線は「この色」で描かれる
            hatch=HATCHES[label],       # ← 密ハッチ
            capsize=4,
            ecolor="black",
            error_kw={"elinewidth": 1.2},
            linewidth=1.2,
            zorder=2,
        )

        # --- 上レイヤ: 透明＋黒枠（ハッチなし） ---
        plt.bar(
            xpos, means[label],
            width=width,
            facecolor=(0, 0, 0, 0),     # 完全透明
            edgecolor="black",          # ← 枠だけ黒で上書き
            linewidth=1.4,
            zorder=3,
        )

    # 戻す
    plt.rcParams["hatch.linewidth"] = old_hatch_lw

    # 軸
    plt.xticks(x, [str(n) for n in nums], fontsize=fontsize)
    plt.xlabel("Number of instances", fontsize=fontsize)
    plt.tick_params(axis='y', labelsize=fontsize)
    plt.ylabel("Throughput (K ops/sec)", fontsize=fontsize)
    plt.ylim(0, 1050)
    plt.grid(axis="y", linestyle="--", alpha=0.4)

    #### 凡例：グラフ内に入れるパターン
    # from matplotlib.patches import Patch
    # import matplotlib.patheffects as pe
    # legend_handles = []
    # for label in LABELS:
    #     patch = Patch(
    #         facecolor="white",
    #         edgecolor=COLORS[label],     # ← ハッチ線色（色）
    #         hatch=HATCHES[label],        # ← 密ハッチそのまま
    #         linewidth=1.2,
    #     )
    #     patch.set_path_effects([
    #         pe.Stroke(linewidth=1.4, foreground="black"),
    #         pe.Normal()
    #     ])
    #     legend_handles.append(patch)
    # plt.legend(
    #     handles=legend_handles,
    #     labels=LABELS,
    #     fontsize=15.5,
    #     handlelength=2.0,
    # )

    ### 凡例：グラフ外に出すパターン
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as pe
    legend_handles = []
    for label in LABELS:
        p = mpatches.Patch(
            facecolor="white",
            edgecolor=COLORS[label],   # ハッチと一致する色
            hatch=HATCHES[label],
            linewidth=1.2,
        )
        p.set_path_effects([pe.Stroke(linewidth=1.4, foreground="black"), pe.Normal()])
        legend_handles.append(p)

    plt.legend(
        legend_handles,
        LABELS,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.23),   # ← グラフの上に配置
        ncol=3,                       # 3列に並べる（2なら2列、5なら1行）
        fontsize=legend_fontsize,
        frameon=True                 # 枠線なしで上品に
        # edgecolor="black"
    )

# def _plot_one_metric(means, stds, nums, save_path):
#     import matplotlib.pyplot as plt

#     x = np.arange(len(nums))
#     width = 0.13
#     offsets = np.linspace(-width*2, width*2, len(LABELS))

#     plt.figure(figsize=(10, 7))

#     # ハッチ線を少し太めに（必要に応じて 1.4〜1.8）
#     old_hlw = plt.rcParams.get("hatch.linewidth", 1.0)
#     plt.rcParams["hatch.linewidth"] = 


#     for i, label in enumerate(LABELS):
#         plt.bar(
#             x + offsets[i], means[label],
#             yerr=stds[label], width=width,
#             facecolor="white",            # 塗りは白
#             edgecolor="black",            # 枠は黒
#             hatch=HATCHES[label],         # 密ハッチ
#             hatch_color=COLORS[label],    # ← 各系列の色をここで指定（3.7+）
#             linewidth=1.3,
#             capsize=4, ecolor="black",
#             error_kw={"elinewidth": 1.2},
#         )

#     # 軸など
#     plt.rcParams["hatch.linewidth"] = old_hlw
#     plt.xticks(x, [str(n) for n in nums], fontsize=fontsize)
#     plt.xlabel("Number of instances", fontsize=fontsize)
#     plt.tick_params(axis='y', labelsize=fontsize)
#     plt.ylabel("Throughput (K ops/sec)", fontsize=fontsize)
#     plt.ylim(0, 1050)
#     plt.grid(axis="y", linestyle="--", alpha=0.4)

#     # 凡例（1レイヤ用：hatch_color をそのまま使う）
#     from matplotlib.patches import Patch
#     legend_handles = [
#         Patch(facecolor="white", edgecolor="black",
#               hatch=HATCHES[label], hatch_color=COLORS[label],
#               linewidth=1.3, label=label)
#         for label in LABELS
#     ]
#     plt.legend(handles=legend_handles, fontsize=15.5, handlelength=2.0)

#     plt.tight_layout()
#     plt.savefig(save_path, dpi=300, bbox_inches="tight")
#     print(f"Saved: {save_path}")
#     plt.show()

    
def plot_grouped_both(base_dir, nums=[1,5,10], run_ids=None):

    # ▼ 追加：保存ファイル名を base_dir 直下に用意
    kernel_out = os.path.join(base_dir, "throughput_kernel.png")
    user_out   = os.path.join(base_dir, "throughput_user.png")

    # 1枚目: kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    _plot_one_metric(means_k, stds_k, nums, save_path=kernel_out)

    # 2枚目: user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    _plot_one_metric(means_u, stds_u, nums, save_path=user_out)
