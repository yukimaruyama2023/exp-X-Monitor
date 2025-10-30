# import numpy as np
# import matplotlib.pyplot as plt
# import sys

# micron_unicode = '\u03BC'
# METRIC_NAME = "system"
# METRICS_UNIT = "ms"

# max = int(input("input max value of vertical axis: "))

# # データの読み込み
# data = np.loadtxt(sys.argv[1], delimiter=",", skiprows=0, usecols=(1, 2))
# data = np.transpose(data)

# TIMESEC_COL = 0
# LATENCY_COL = 1

# plt.rcParams["font.size"] = 23

# fig, ax1 = plt.subplots()

# # パーセンタイルの計算
# latency = data[LATENCY_COL]
# percentiles = np.percentile(latency, [50, 90, 99])
# print(f"50th percentile latency: {percentiles[0]} us")
# print(f"90th percentile latency: {percentiles[1]} us")
# print(f"99th percentile latency: {percentiles[2]} us")

# # 経過時間と遅延時間の準備
# elapsed = data[TIMESEC_COL] - data[TIMESEC_COL][0]
# latency = data[LATENCY_COL] / 1000  # msに変換

# # グラフの描画
# ax1.plot(elapsed, latency, label="latency of monitoring\nmessage",
#          color="orange", marker="^")

# # 軸ラベルと範囲の設定
# ax1.set_xlabel("elapsed time [s]")
# ax1.set_ylabel("latency [ms]")
# ax1.set_ylim(0, max)

# # グリッドのカスタマイズ（横線だけ表示）
# ax1.grid(axis='y')  # y軸方向のグリッドを表示

# # 凡例の設定
# handler, label = ax1.get_legend_handles_labels()
# ax1.legend(handler, label, loc="upper right", fontsize="small")

# # グラフの表示
# plt.show()


import numpy as np
import matplotlib.pyplot as plt

micron_unicode = '\u03BC'
METRIC_NAME = "system"
METRICS_UNIT = "ms"


def plot_latency(csv_path: str, y_max: int, skiprows: int = 0) -> None:
    """
    Plot latency over elapsed time from a CSV file.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.
    y_max : int
        Upper limit for Y-axis in milliseconds.
    skiprows : int, optional
        Number of header rows to skip when loading CSV, by default 0.

    Notes
    -----
    - Expects the CSV to have time in seconds at column index 1,
      and latency in microseconds at column index 2.
    """
    # データの読み込み（time[s]=col1, latency[us]=col2）
    data = np.loadtxt(csv_path, delimiter=",", skiprows=skiprows, usecols=(1, 2))
    data = np.transpose(data)

    TIMESEC_COL = 0
    LATENCY_COL = 1

    plt.rcParams["font.size"] = 23

    fig, ax1 = plt.subplots()

    # パーセンタイル計算（μsのまま）
    latency_us = data[LATENCY_COL]
    percentiles = np.percentile(latency_us, [50, 90, 99])
    print(f"50th percentile latency: {percentiles[0]} us")
    print(f"90th percentile latency: {percentiles[1]} us")
    print(f"99th percentile latency: {percentiles[2]} us")

    # 経過時間と遅延時間
    elapsed = data[TIMESEC_COL] - data[TIMESEC_COL][0]
    latency_ms = latency_us / 1000.0  # ms に変換

    # プロット
    ax1.plot(
        elapsed,
        latency_ms,
        label="latency of monitoring\nmessage",
        color="orange",
        marker="^",
    )

    ax1.set_xlabel("elapsed time [s]")
    ax1.set_ylabel("latency [ms]")
    ax1.set_ylim(0, y_max)

    ax1.grid(axis="y")  # 横線だけ
    handler, label = ax1.get_legend_handles_labels()
    ax1.legend(handler, label, loc="upper right", fontsize="small")

    plt.show()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Plot latency from CSV.")
    parser.add_argument("csv_path", help="Path to CSV file")
    parser.add_argument("--ymax", type=int, required=True, help="Max value for Y-axis (ms)")
    parser.add_argument("--skiprows", type=int, default=0, help="Header rows to skip")
    args = parser.parse_args()
    plot_latency(args.csv_path, args.ymax, args.skiprows)


if __name__ == "__main__":
    main()