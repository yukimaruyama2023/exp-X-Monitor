import argparse
import glob
import os
import re
import sys
from typing import List, Tuple

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.size"] = 22

############### Color Configuration #############
## catppuccin
# COLORS = {
#     "Netdata (1000ms)":   "#F5A97F",  # Peach
#     "X-Monitor (1000ms)": "#5AB8A8",  # Teal
#     "X-Monitor (100ms)":  "#72A7E3",  # Blue
#     "X-Monitor (10ms)":   "#C7A0E8",  # Lavender
# }

## default matplotlib
COLORS = {
    "Netdata (1000ms)":   "#d62728",
    "X-Monitor (1000ms)": "#ff7f0e",
    "X-Monitor (100ms)":  "#2ca02c",
    "X-Monitor (10ms)":   "#1f77b4",
}


# ---------- 基本ユーティリティ ----------

def load_latencies_ms(path: str, col: int = 2, skiprows: int = 0) -> np.ndarray:
    """
    CSVから指定列(0-based)を読み、μs→msに変換して返す。
    ※ここではソートしない（ソートは CDF 計算前に行う）。
    """
    try:
        arr = np.loadtxt(path, delimiter=",", usecols=col, skiprows=skiprows)
    except Exception:
        # ヘッダあり・混入データに強い fallback
        arr = np.genfromtxt(path, delimiter=",", usecols=col, skip_header=skiprows)
    arr_ms = arr / 1000.0  # μs → ms
    return arr_ms  # ← ここではソートしない


def cdf(arr: np.ndarray) -> np.ndarray:
    """昇順配列 arr に対する CDF 値(0..1)を返す。"""
    n = len(arr)
    if n <= 1:
        return np.array([1.0])
    return np.arange(n) / (n - 1)


def resolve_mcd_dir(base_dir: str, mcd: int) -> str:
    """
    base_dir がタイムスタンプ階層を指している前提で、
    その直下の {mcd:03d}mcd ディレクトリを返す。
    もし base_dir が既に .../NNNmcd を含んでいたら、そのまま返す。
    """
    # 末尾  /123mcd[/]  に既に一致していればそのまま
    if re.search(rf"[\\/]{mcd:03d}mcd[\\/]?$", base_dir):
        return base_dir
    # 末尾が任意の NNNmcd なら、そのまま（ユーザーが明示指定したケース）
    if re.search(r"[\\/]\d{3}mcd[\\/]?$", base_dir):
        return base_dir
    # それ以外は mcd を付ける
    return os.path.join(base_dir, f"{mcd:03d}mcd")


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
        color = COLORS.get(label, None)  # ← マップから色取得
        ax.plot(
            x, y,
            marker=markers[i % len(markers)],
            markersize=4,
            label=label,
            color=color,
            linewidth=2,
        )

    # 90% / 99% 水平線
    ax.axhline(y=0.9, linestyle='--', linewidth=1, dashes=(10, 5), color='black')
    ax.axhline(y=0.99, linestyle='--', linewidth=1, dashes=(10, 5), color='black')

    ax.set_ylim((0.90, 1.0))
    ax.set_xlim((-0.1, xmax))
    ax.set_yticks([0.90, 0.99, 1.00], ["90%", "99%", "100%"])
    ax.set_xlabel("latency [ms]")
    ax.set_ylabel("percentile")
    ax.legend(loc='lower right', labelspacing=0, fontsize=14)


# ---------- 引数とエントリーポイント分離（Jupyter/CLI両対応） ----------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot CDFs for user/kernel metrics (X-Monitor vs Netdata)."
    )
    parser.add_argument("--dir", default=".", help="directory containing CSV files")
    parser.add_argument(
        "--mcd", type=int, default=1,
        help="mcd count used in filenames (e.g., 1 for *-1mcd-*)"
    )
    parser.add_argument(
        "--xmax", type=float, default=30.0,
        help="x-axis max (ms)"
    )
    parser.add_argument(
        "--col", type=int, default=2,
        help="latency column index (0-based)"
    )
    parser.add_argument(
        "--skiprows", type=int, default=0,
        help="header rows to skip"
    )
    parser.add_argument(
        "--save", action="store_true",
        help="save figures as PNG instead of showing"
    )
    # ウォームアップ 10 秒分を除外するフラグ
    parser.add_argument(
        "--exclude-warmup", action="store_true",
        help="exclude first 10 seconds of samples (Netdata/X-Monitor) from CDF"
    )
    return parser.parse_args(argv)


def main_impl(args) -> None:
    base_ts = args.dir        # タイムスタンプ階層（ユーザー指定）
    mcd = args.mcd
    col = args.col
    skiprows = args.skiprows
    exclude_warmup = args.exclude_warmup

    # ← ここで実際に探索するルートに変換（.../NNNmcd）
    search_root = resolve_mcd_dir(base_ts, mcd)

    # 必須ファイル（Netdata）: すべて search_root を基準に探す
    net_user = os.path.join(search_root, f"netdata-usermetrics-{mcd}mcd.csv")
    net_kernel = os.path.join(search_root, f"netdata-kernelmetrics-{mcd}mcd.csv")

    missing = [p for p in [net_user, net_kernel] if not os.path.exists(p)]
    if missing:
        print("Missing required file(s) under:", search_root)
        for m in missing:
            print("  -", m)
        sys.exit(1)

    # X-Monitor 側（interval* を自動検出）
    xmon_user = find_xmonitor_files(search_root, "usermetrics", mcd)
    xmon_kernel = find_xmonitor_files(search_root, "kernelmetrics", mcd)
    if len(xmon_user) == 0 or len(xmon_kernel) == 0:
        print("No xmonitor files found under:", search_root)
        print("Expected patterns like:")
        print(f"  {os.path.join(search_root, f'xmonitor-usermetrics-{mcd}mcd-interval*.csv')}")
        print(f"  {os.path.join(search_root, f'xmonitor-kernelmetrics-{mcd}mcd-interval*.csv')}")
        sys.exit(1)

    # ---- helper: ウォームアップ行を削る ----
    def cut_warmup(latencies: np.ndarray, interval_sec: float) -> np.ndarray:
        """
        interval_sec ごとのサンプリングの場合に、
        先頭 10 秒分 (10 / interval_sec サンプル) を削る。
        """
        if not exclude_warmup:
            return latencies
        if interval_sec <= 0:
            return latencies
        warmup_rows = int(15.0 / interval_sec)  # 15秒 / interval
        if warmup_rows <= 0 or warmup_rows >= len(latencies):
            # 行数が少なすぎるなどの場合は、そのまま返す
            return latencies
        return latencies[warmup_rows:]

    # 読み込み（User metrics）
    curves_user = []
    for sec, path in xmon_user:
        lat = load_latencies_ms(path, col, skiprows)   # 未ソート
        lat = cut_warmup(lat, sec)                     # 先頭 N 行を削る
        lat = np.sort(lat)                             # ここでソート
        p = cdf(lat)
        label = f"X-Monitor ({int(sec*1000)}ms)"
        curves_user.append((lat, p, label))

    # Netdata (固定 1000ms → 1.0秒とみなす)
    lat_net_user = load_latencies_ms(net_user, col, skiprows)
    lat_net_user = cut_warmup(lat_net_user, 1.0)
    lat_net_user = np.sort(lat_net_user)
    p_net_user = cdf(lat_net_user)
    curves_user.append((lat_net_user, p_net_user, "Netdata (1000ms)"))

    # 読み込み（Kernel metrics）
    curves_kernel = []
    for sec, path in xmon_kernel:
        lat = load_latencies_ms(path, col, skiprows)
        lat = cut_warmup(lat, sec)
        lat = np.sort(lat)
        p = cdf(lat)
        label = f"X-Monitor ({int(sec*1000)}ms)"
        curves_kernel.append((lat, p, label))

    lat_net_kernel = load_latencies_ms(net_kernel, col, skiprows)
    lat_net_kernel = cut_warmup(lat_net_kernel, 1.0)
    lat_net_kernel = np.sort(lat_net_kernel)
    p_net_kernel = cdf(lat_net_kernel)
    curves_kernel.append((lat_net_kernel, p_net_kernel, "Netdata (1000ms)"))

    # 描画（2 図）
    print("User metrics CDF")
    fig1, ax1 = plt.subplots(figsize=(7, 5))
    plot_one(ax1, curves_user, xmax=args.xmax)

    print("Kernel metrics CDF")
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    plot_one(ax2, curves_kernel, xmax=args.xmax)

    fig1.tight_layout()
    fig2.tight_layout()

    print("\n[Output directory (base)]")
    print(f"  {args.dir}")
    print(f"  (mcd = {mcd})\n")

    # ここから保存先ディレクトリの切り分け
    mode_dir = "warmup-cut-enable" if exclude_warmup else "warmup-cut-disable"
    out_root = os.path.join(args.dir, "output-png", mode_dir)

    if args.save:
        os.makedirs(out_root, exist_ok=True)
        out1 = os.path.join(out_root, f"cdf-usermetrics-{mcd}mcd.png")
        out2 = os.path.join(out_root, f"cdf-kernelmetrics-{mcd}mcd.png")
        fig1.savefig(out1, dpi=200)
        fig2.savefig(out2, dpi=200)

        print("[Saved PNG files]")
        print(f"  {out1}")
        print(f"  {out2}")
    else:
        out1 = os.path.join(out_root, f"cdf-usermetrics-{mcd}mcd.png")
        out2 = os.path.join(out_root, f"cdf-kernelmetrics-{mcd}mcd.png")
        print("[Not saving files] (use --save to generate PNG)")
        print("  Would save as:")
        print(f"    {out1}")
        print(f"    {out2}\n")

        plt.show()


def main_cli(argv=None) -> None:
    """コマンドライン用エントリーポイント"""
    args = parse_args(argv)
    main_impl(args)


def run_plot(
    dir=".",
    mcd=1,
    xmax=30.0,
    col=2,
    skiprows=0,
    save=False,
    exclude_warmup: bool = False,
) -> None:
    """
    Notebook / 他コードからの呼び出し用API。
    例:
        run_plot(dir=".", mcd=1, xmax=30, save=True, exclude_warmup=True)
    """
    argv = [
        "--dir", str(dir),
        "--mcd", str(mcd),
        "--xmax", str(xmax),
        "--col", str(col),
        "--skiprows", str(skiprows),
    ]
    if save:
        argv.append("--save")
    if exclude_warmup:
        argv.append("--exclude-warmup")

    main_cli(argv)


if __name__ == "__main__":
    main_cli()