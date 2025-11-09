import os
import re
import argparse
import numpy as np
import matplotlib.pyplot as plt

# THROUGHPUT_RE = re.compile(r"Total QPS\s*=\s*([\d.]+)")

# LABELS = [
#     "No-Monitoring",
#     "Netdata-1000ms",
#     "X-Monitor-1000ms",
#     "X-Monitor-100ms",
#     "X-Monitor-10ms",
# ]

# # 実ファイル名に合わせたパターン（mcd は 0 埋めなし、-interval の前に mcd）
# FILE_PATTERNS = {
#     "No-Monitoring":        "no_monitoring-{num}mcd.txt",
#     "Netdata-1000ms":       "netdata-{metric}metrics-{num}mcd.txt",
#     "X-Monitor-1000ms":     "xmonitor-{metric}metrics-{num}mcd-interval1.txt",
#     "X-Monitor-100ms":      "xmonitor-{metric}metrics-{num}mcd-interval0.1.txt",
#     "X-Monitor-10ms":       "xmonitor-{metric}metrics-{num}mcd-interval0.01.txt",
# }


# def collect_throughput(log_dir: str, metric: str, num_memcached: int):
#     data = {label: [] for label in LABELS}

#     for label in LABELS:
#         fname = FILE_PATTERNS[label].format(metric=metric, num=str(num_memcached))
#         path = os.path.join(log_dir, fname)

#         if not os.path.exists(path):
#             print(f"[SKIP] {path} not found")
#             continue

#         with open(path) as f:
#             for line in f:
#                 m = THROUGHPUT_RE.search(line)
#                 if m:
#                     v = float(m.group(1))
#                     data[label].append(v)
#                     print(f"[OK] {label}: {v}")
#                     break

#     return data


def plot_one(base_dir, metric, num_memcached):
    # ディレクトリ名は 0 埋め（001mcd / 005mcd / 010mcd）
    subdir = f"{num_memcached:03d}mcd"
    log_dir = os.path.join(base_dir, subdir)

    data = collect_throughput(log_dir, metric, num_memcached)
    means = [(np.mean(v) / 1000) if v else 0 for v in data.values()]

    colors = [
        "#999999",   # No-Monitoring
        "coral",     # Netdata
        "#1f77b4",   # Proposal 1000ms
        "#1f77b4",   # Proposal 100ms
        "#1f77b4",   # Proposal 10ms
    ]

    x = np.arange(len(LABELS))
    plt.figure(figsize=(10, 5))
    plt.bar(x, means, color=colors)
    plt.xticks(x, LABELS, rotation=20, fontsize=18)
    plt.yticks(fontsize=18)
    plt.ylabel("Throughput (K ops/sec)", fontsize=18)
    plt.title(f"{metric.upper()}   {num_memcached} memcached", fontsize=20)
    plt.grid(axis='y')
    plt.tight_layout()

    save_path = os.path.join(base_dir, f"throughput-{metric}-{num_memcached}.png")
    plt.savefig(save_path, bbox_inches="tight")
    print(f"[SAVED] {save_path}")

    plt.show()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-dir", required=True)
    p.add_argument("--num-memcached", required=True, type=int)
    args = p.parse_args()

    # metric は固定で両方描画
    for metric in ["kernel", "user"]:
        plot_one(args.base_dir, metric, args.num_memcached)


if __name__ == "__main__":
    main()