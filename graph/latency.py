# import matplotlib.pyplot as plt
# import numpy as np
# import sys

# plt.rcParams["font.size"] = 18

# max = int(input("input max value of x axis like 30: "))

# # 入力ファイル数チェック
# if len(sys.argv) != 7:
#     print("Usage: python script.py file1.csv file2.csv file3.csv file4.csv file5.csv file6.csv")
#     sys.exit(1)

# # ファイル読み込みとソート（ミリ秒単位に変換）
# latencies = [np.sort(np.loadtxt(sys.argv[i], delimiter=',',
#                      usecols=2) / 1000) for i in range(1, 7)]

# # CDF 計算
# percentiles = [np.arange(len(lat)) / (len(lat) - 1) for lat in latencies]

# # 暫定ラベル
# labels = [
#     "X-Monitor (10 ms)",
#     "X-Monitor (100 ms)",
#     "X-Monitor (1000 ms)",
#     "Netdata  (1000 ms)",
# ]

# # マーカー一覧（必要に応じて調整）
# markers = ['o', '*', '^', 'x', 's', 'd']

# # 描画
# fig, ax = plt.subplots(figsize=(7, 5))
# for lat, p, label, marker in zip(latencies, percentiles, labels, markers):
#     ax.plot(lat, p, marker=marker, markersize=4, label=label)

# # 水平線（90%, 99%）
# ax.axhline(y=0.9, xmin=-1, xmax=12, color='black',
#            linestyle='--', linewidth=1, dashes=(10, 5))
# ax.axhline(y=0.99, xmin=-1, xmax=12, color='black',
#            linestyle='--', linewidth=1, dashes=(10, 5))

# # 軸範囲とラベル
# ax.set_ylim((0.90, 1))
# ax.set_xlim((-0.1, max))
# ax.set_yticks([0.900, 0.990, 1.000], ["90%", "99%", "100%"])
# ax.set_xlabel("latency [ms]")
# ax.set_ylabel("percentile")
# ax.legend(loc='lower right', labelspacing=0)
# ax.legend(loc='lower right', labelspacing=0, fontsize=17)

# fig.tight_layout()
# plt.show()

#!/usr/bin/env python3
# filename: plot_cdf_dual.py
import argparse
import glob
import os
import re
import sys
from typing import List, Tuple

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.size"] = 18


# ---------- 基本ユーティリティ ----------

def load_latencies_ms(path: str, col: int = 2, skiprows: int = 0) -> np.ndarray:
    """
    CSVから指定列(0-based)を読み、μs→msに変換して昇順で返す。
    ヘッダ行がある場合は skiprows を指定。
    """
    try:
        arr = np.loadtxt(path, delimiter=",", usecols=col, skiprows=skiprows)
    except Exception as e:
        # ヘッダあり・混入データに強い fallback
        arr = np.genfromtxt(path, delimiter=",", usecols=col, skip_header=skiprows)
    arr_ms = arr / 1000.0  # μs → ms
    return np.sort(arr_ms)


def cdf(arr: np.ndarray) -> np.ndarray:
    """昇順配列 arr に対する CDF 値(0..1)を返す。"""
    n = len(arr)
    if n <= 1:
        return np.array([1.0])
    return np.arange(n) / (n - 1)


def find_xmonitor_files(base_dir: str, kind: str, mcd: int) -> List[Tuple[float, str]]:
    """
    kind: 'usermetrics' or 'kernelmetrics'
    戻り値: [(interval_sec, filepath)] を interval 昇順で返す
    """
    pattern = os.path.join(base_dir, f"xmonitor-{kind}-{mcd}mcd-interval*.csv")
    files = glob.glob(pattern)
    found: List[Tuple[float, str]] = []
    for f in files:
        m = re.search(r"interval([0-9.]+)\.csv$", f)
        if m:
            sec = float(m.group(1))
            found.append((sec, f))
    found.sort(key=lambda x: x[0])
    return found


def plot_one(ax, curves, xmax: float):
    """
    curves: iterable of (x_values, y_values, label)
    """
    markers = ['o', '*', '^', 'x', 's', 'd']
    for i, (x, y, label) in enumerate(curves):
        ax.plot(x, y, marker=markers[i % len(markers)], markersize=4, label=label)

    # 90% / 99% 水平線
    ax.axhline(y=0.9, linestyle='--', linewidth=1, dashes=(10, 5), color='black')
    ax.axhline(y=0.99, linestyle='--', linewidth=1, dashes=(10, 5), color='black')

    ax.set_ylim((0.90, 1.0))
    ax.set_xlim((-0.1, xmax))
    ax.set_yticks([0.90, 0.99, 1.00], ["90%", "99%", "100%"])
    ax.set_xlabel("latency [ms]")
    ax.set_ylabel("percentile")
    ax.legend(loc='lower right', labelspacing=0, fontsize=17)


# ---------- 引数とエントリーポイント分離（Jupyter/CLI両対応） ----------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot CDFs for user/kernel metrics (X-Monitor vs Netdata)."
    )
    parser.add_argument("--dir", default=".", help="directory containing CSV files")
    parser.add_argument("--mcd", type=int, default=1,
                        help="mcd count used in filenames (e.g., 1 for *-1mcd-*)")
    parser.add_argument("--xmax", type=float, default=30.0, help="x-axis max (ms)")
    parser.add_argument("--col", type=int, default=2, help="latency column index (0-based)")
    parser.add_argument("--skiprows", type=int, default=0, help="header rows to skip")
    parser.add_argument("--save", action="store_true", help="save figures as PNG instead of showing")
    return parser.parse_args(argv)


def main_impl(args) -> None:
    base = args.dir
    mcd = args.mcd
    col = args.col
    skiprows = args.skiprows

    # 必須ファイル（Netdata）
    net_user = os.path.join(base, f"netdata-usermetrics-{mcd}mcd.csv")
    net_kernel = os.path.join(base, f"netdata-kernelmetrics-{mcd}mcd.csv")

    missing = [p for p in [net_user, net_kernel] if not os.path.exists(p)]
    if missing:
        print("Missing required file(s):")
        for m in missing:
            print("  -", m)
        sys.exit(1)

    # X-Monitor 側（interval* を自動検出）
    xmon_user = find_xmonitor_files(base, "usermetrics", mcd)
    xmon_kernel = find_xmonitor_files(base, "kernelmetrics", mcd)
    if len(xmon_user) == 0 or len(xmon_kernel) == 0:
        print("No xmonitor files found. Expected patterns like:")
        print(f"  {os.path.join(base, f'xmonitor-usermetrics-{mcd}mcd-interval*.csv')}")
        print(f"  {os.path.join(base, f'xmonitor-kernelmetrics-{mcd}mcd-interval*.csv')}")
        sys.exit(1)

    # 読み込み（User metrics）
    curves_user = []
    for sec, path in xmon_user:
        lat = load_latencies_ms(path, col, skiprows)
        p = cdf(lat)
        label = f"X-Monitor ({int(sec*1000)} ms)"
        curves_user.append((lat, p, label))
    # Netdata (固定 1000ms として扱う)
    lat_net_user = load_latencies_ms(net_user, col, skiprows)
    p_net_user = cdf(lat_net_user)
    curves_user.append((lat_net_user, p_net_user, "Netdata  (1000 ms)"))

    # 読み込み（Kernel metrics）
    curves_kernel = []
    for sec, path in xmon_kernel:
        lat = load_latencies_ms(path, col, skiprows)
        p = cdf(lat)
        label = f"X-Monitor ({int(sec*1000)} ms)"
        curves_kernel.append((lat, p, label))
    lat_net_kernel = load_latencies_ms(net_kernel, col, skiprows)
    p_net_kernel = cdf(lat_net_kernel)
    curves_kernel.append((lat_net_kernel, p_net_kernel, "Netdata  (1000 ms)"))

    # 描画（2 図）
    fig1, ax1 = plt.subplots(figsize=(7, 5))
    plot_one(ax1, curves_user, xmax=args.xmax)
    ax1.set_title("User metrics CDF")

    fig2, ax2 = plt.subplots(figsize=(7, 5))
    plot_one(ax2, curves_kernel, xmax=args.xmax)
    ax2.set_title("Kernel metrics CDF")

    fig1.tight_layout()
    fig2.tight_layout()

    if args.save:
        out1 = os.path.join(base, f"cdf-usermetrics-{mcd}mcd.png")
        out2 = os.path.join(base, f"cdf-kernelmetrics-{mcd}mcd.png")
        fig1.savefig(out1, dpi=200)
        fig2.savefig(out2, dpi=200)
        print(f"Saved: {out1}")
        print(f"Saved: {out2}")
    else:
        plt.show()


def main_cli(argv=None) -> None:
    """コマンドライン用エントリーポイント"""
    args = parse_args(argv)
    main_impl(args)


def run_plot(dir=".", mcd=1, xmax=30.0, col=2, skiprows=0, save=False) -> None:
    """
    Notebook / 他コードからの呼び出し用API。
    例: run_plot(dir=".", mcd=1, xmax=30, save=True)
    """
    argv = ["--dir", str(dir), "--mcd", str(mcd), "--xmax", str(xmax), "--col", str(col), "--skiprows", str(skiprows)]
    if save:
        argv.append("--save")
    main_cli(argv)


if __name__ == "__main__":
    main_cli()