import os
import re
import numpy as np
import matplotlib.pyplot as plt

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

def _plot_one_metric(means, stds, nums, colors, save_path):
    x = np.arange(len(nums))
    width = 0.13
    offsets = np.linspace(-width*2, width*2, len(LABELS))

    plt.figure(figsize=(10, 7))
    for i, label in enumerate(LABELS):
        plt.bar(
            x + offsets[i],
            means[label],
            yerr=stds[label],
            width=width,
            color=colors[label],
            label=label,
            capsize=4,
            ecolor="black",
            error_kw={"elinewidth": 1},
        )

    # ▼ 以前のスタイルに合わせて "mcd" 表記
    plt.xticks(x, [f"{n} instance" if n == 1 else f"{n} instances" for n in nums], fontsize=30)
    plt.tick_params(axis='y', labelsize=30)
    plt.yticks(fontsize=30)
    plt.ylabel("Throughput (K ops/sec)", fontsize=30)
    plt.ylim(0, 1050)
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.legend(fontsize=15.5)
    plt.tight_layout()

    # ▼ 追加：保存してから表示
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    print(f"Saved: {save_path}")

    plt.show()
    
def plot_grouped_both(base_dir, nums=[1,5,10], run_ids=None):
    colors = {
        "No Monitoring": "#999999",
        "Netdata (1000ms)": "coral",
        "X-Monitor (1000ms)": "#1f77b4",
        "X-Monitor (100ms)": "#4aa3df",
        "X-Monitor (10ms)": "#88c5f2",
    }

    # ▼ 追加：保存ファイル名を base_dir 直下に用意
    kernel_out = os.path.join(base_dir, "throughput_kernel.png")
    user_out   = os.path.join(base_dir, "throughput_user.png")

    # 1枚目: kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    _plot_one_metric(means_k, stds_k, nums, colors, save_path=kernel_out)

    # 2枚目: user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    _plot_one_metric(means_u, stds_u, nums, colors, save_path=user_out)
