from throughput import (
    LABELS, LABEL_META,
    COLORS, HATCHES,
    fontsize, legend_fontsize, figsize, GROUP_SPACING, line_width,bbox_to_anchor, 
    _find_interval_files_txt,
    _select_file_for_interval,
)
ylim = 5

import os
import numpy as np

######################## 99th レイテンシ用ユーティリティ ########################

def _parse_99th_latency(path: str) -> float | None:
    """
    mutilate の結果ファイルから read の 99th レイテンシ (μs) を 1 つ取り出す。
    """
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("read"):
                parts = line.split()
                if len(parts) >= 9:
                    try:
                        return float(parts[8])  # μs
                    except ValueError:
                        return None
    return None


def collect_latency99(log_dir: str, metric: str, n: int):
    """
    1 run_dir (= .../RUN_ID/NNNmcd) から各ラベルの 99th レイテンシ (μs) を集める。
    """
    data = {label: [] for label in LABELS}
    for label in LABELS:
        meta = LABEL_META[label]

        if meta["tool"] is None:
            path = os.path.join(log_dir, f"no_monitoring-{n}mcd.txt")
            if not os.path.exists(path):
                continue
        else:
            tool = meta["tool"]
            interval_sec = meta["interval"]
            path = _select_file_for_interval(
                log_dir, tool=tool, metric=metric, n=n, target_interval=interval_sec
            )
            if path is None or not os.path.exists(path):
                continue

        lat99 = _parse_99th_latency(path)
        if lat99 is not None:
            data[label].append(lat99)  # μs
    return data


def collect_latency99_across_runs(base_dir, metric, nums, run_ids=None):
    """
    user / kernel 両方に対応。
    """
    if run_ids is None:
        run_ids = [str(i) for i in range(5)]

    means = {label: [] for label in LABELS}
    stds  = {label: [] for label in LABELS}

    for n in nums:
        per_label_values = {label: [] for label in LABELS}
        for rid in run_ids:
            run_dir = os.path.join(base_dir, rid, f"{n:03d}mcd")
            d = collect_latency99(run_dir, metric, n)
            for label in LABELS:
                if d[label]:
                    per_label_values[label].extend(d[label])

        for label in LABELS:
            vals = np.array(per_label_values[label], dtype=float) / 1000.0  # μs→ms
            if vals.size == 0:
                means[label].append(0.0)
                stds[label].append(0.0)
            elif vals.size == 1:
                means[label].append(float(vals[0]))
                stds[label].append(0.0)
            else:
                means[label].append(float(np.mean(vals)))
                stds[label].append(float(np.std(vals, ddof=1)))
    return means, stds


def _plot_latency99(means, stds, nums, metric, save_path):
    """
    metric: "kernel" or "user"
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as pe

    x = np.arange(len(nums)) * GROUP_SPACING
    width = line_width
    offsets = np.linspace(-width*3, width*3, len(LABELS))

    plt.figure(figsize=figsize)

    old_hatch_lw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = 1.6

    for i, label in enumerate(LABELS):
        xpos = x + offsets[i]

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

        plt.bar(
            xpos, means[label],
            width=width,
            facecolor=(0, 0, 0, 0),
            edgecolor="black",
            linewidth=1.4,
            zorder=3,
        )

    plt.rcParams["hatch.linewidth"] = old_hatch_lw

    plt.xticks(x, [str(n) for n in nums], fontsize=fontsize)
    plt.xlabel("Number of instances", fontsize=fontsize)
    plt.tick_params(axis='y', labelsize=fontsize)
    plt.ylabel("99th latency (ms)", fontsize=fontsize)
    plt.ylim(0, ylim)

    plt.grid(axis="y", linestyle="--", alpha=0.4)

    # plt.title(f"99th latency ({metric})", fontsize=fontsize)

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
        ncol=4,
        fontsize=legend_fontsize,
        frameon=True
    )

    plt.savefig(save_path, bbox_inches="tight", dpi=300)


def plot_grouped_latency99(base_dir, nums=[1,5,10], run_ids=None):
    """
    kernel と user の２つのグラフを保存
    それぞれ latency99_kernel.pdf, latency99_user.pdf
    """
    for metric in ["kernel", "user"]:
        print(f"\n===== Plotting 99th latency for {metric} metrics =====")
        means, stds = collect_latency99_across_runs(base_dir, metric, nums, run_ids)

        for label in LABELS:
            print(f"[{metric}] {label}: {means[label]} ms")

        out_path = os.path.join(base_dir, f"latency99_{metric}.pdf")
        _plot_latency99(means, stds, nums, metric, save_path=out_path)


# def print_latency99_means(base_dir, nums, run_ids=None):
#     """
#     user / kernel 両方出力
#     """
#     for metric in ["kernel", "user"]:
#         print(f"\n===== 99th latency (ms): Means for {metric} metrics =====")
#         means, stds = collect_latency99_across_runs(base_dir, metric, nums, run_ids)
#         for label in LABELS:
#             print(f"\n[ {metric} | {label} ]")
#             for n, v in zip(nums, means[label]):
#                 print(f"  {n} mcd : {v:.3f} ms")

def print_latency99_means(base_dir, nums, run_ids=None):
    """
    user / kernel 両方出力
    """
    for metric in ["kernel", "user"]:
        print(f"\n===== 99th latency (ms): Means for {metric} metrics =====")
        means, stds = collect_latency99_across_runs(base_dir, metric, nums, run_ids)
        for label in LABELS:
            print(f"\n[ {metric} | {label} ]")
            for n, v in zip(nums, means[label]):
                # 小数点以下 3 桁で固定表示
                print(f"  {n} mcd : {v:.3f} ms")