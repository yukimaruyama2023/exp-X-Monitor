import os
import re
import numpy as np
import matplotlib.pyplot as plt

THROUGHPUT_RE = re.compile(r"Total QPS\s*=\s*([\d.]+)")

LABELS = [
    "No-Monitoring",
    "Netdata-1000ms",
    "X-Monitor-1000ms",
    "X-Monitor-100ms",
    "X-Monitor-10ms",
]

FILE_PATTERNS = {
    "No-Monitoring":        "no_monitoring-{num}mcd.txt",
    "Netdata-1000ms":       "netdata-{metric}metrics-{num}mcd.txt",
    "X-Monitor-1000ms":     "xmonitor-{metric}metrics-{num}mcd-interval1.txt",
    "X-Monitor-100ms":      "xmonitor-{metric}metrics-{num}mcd-interval0.1.txt",
    "X-Monitor-10ms":       "xmonitor-{metric}metrics-{num}mcd-interval0.01.txt",
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
                    data[label].append(float(m.group(1)))
                    break
    return data


def collect_means(base_dir, metric, nums):
    means = {label: [] for label in LABELS}
    for n in nums:
        log_dir = os.path.join(base_dir, f"{n:03d}mcd")
        d = collect_throughput(log_dir, metric, n)
        for label in LABELS:
            means[label].append(np.mean(d[label]) / 1000 if d[label] else 0)
    return means


def plot_grouped(base_dir, metric, nums=[1,5,10]):
    means = collect_means(base_dir, metric, nums)

    colors = {
        "No-Monitoring": "#999999",
        "Netdata-1000ms": "coral",
        "X-Monitor-1000ms": "#1f77b4",
        "X-Monitor-100ms": "#4aa3df",
        "X-Monitor-10ms": "#88c5f2",
    }

    x = np.arange(len(nums))
    width = 0.13
    offsets = np.linspace(-width*2, width*2, len(LABELS))

    plt.figure(figsize=(10, 7))
    # plt.figure(figsize=(12, 5))
    for i, label in enumerate(LABELS):
        plt.bar(x + offsets[i], means[label], width=width, color=colors[label], label=label)

    plt.xticks(x, [f"{n} mcd" for n in nums], fontsize=30)
    plt.tick_params(axis='y', labelsize=30)
    plt.yticks(fontsize=30)
    plt.ylabel("Throughput (K ops/sec)", fontsize=30)
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.legend(fontsize=16)
    plt.tight_layout()
    plt.show()

