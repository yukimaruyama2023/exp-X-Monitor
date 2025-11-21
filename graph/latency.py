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
# interval ごとに色を固定（Netdata / X-Monitor で同じ interval は同じ色）
COLORS = {
    "1s": "tab:red",
    "500ms": "tab:orange",
    "1ms": "tab:blue",
    # もし今後 200μs などを追加したければここに足す
    "200μs": "tab:green",
}
############### Color Configuration #############
# interval ごとに色を固定（Netdata / X-Monitor で同じ interval は同じ色）
# COLORS = {
#     "1000ms": "tab:red",    # 1s
#     "500ms":  "tab:orange", # 0.5s
#     "1ms":    "tab:blue",   # 0.001s
#     # もし今後 0.2ms (0.0002s) などを追加したければここに足す
#     # "0.2ms": "tab:green",
# }

############### Color Configuration (6 colors) #############

COLORS = {
    "X-Monitor (1000ms)": "tab:blue",
    "X-Monitor (500ms)":  "tab:orange",
    "X-Monitor (1ms)":    "tab:green",

    "Netdata (1000ms)":   "tab:red",
    "Netdata (500ms)":    "tab:purple",
    "Netdata (1ms)":      "tab:brown",
}

# ---------- 基本ユーティリティ ----------
# def interval_label(sec: float) -> str:
#     """
#     interval(sec) を 1s / 500ms / 1ms / 200μs の形式で返す。
#       1       → "1s"
#       0.5     → "500ms"
#       0.001   → "1ms"
#       0.0002  → "200μs"
#     """
#     # s 表記
#     if sec >= 1.0 - 1e-9:
#         return f"{sec:g}s"  # 1 → "1s", 2 → "2s" など

#     # ms 表記
#     ms = sec * 1000.0
#     if ms >= 1.0 - 1e-9:
#         # 0.5 → 500ms, 0.001 → 1ms
#         # 小数が出ないように g フォーマット
#         return f"{ms:g}ms"

#     # それ以外は μs
#     us = sec * 1_000_000.0
#     return f"{us:g}μs"

def interval_label(sec: float) -> str:
    """
    interval(sec) を常に ms 表記で返す。
      1       → "1000ms"
      0.5     → "500ms"
      0.001   → "1ms"
      0.0002  → "0.2ms"
    """
    ms = sec * 1000.0
    # ほぼ整数なら整数で表示
    if abs(ms - round(ms)) < 1e-6:
        return f"{int(round(ms))}ms"
    # 小数が必要な場合
    # （必要に応じて桁数は調整してください）
    return f"{ms:g}ms"

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


def find_interval_files(
    base_dir: str, tool: str, kind: str, mcd: int
) -> List[Tuple[float, str]]:
    """
    tool: 'xmonitor' or 'netdata'
    kind: 'usermetrics' or 'kernelmetrics'
    戻り値: [(interval_sec, filepath)] を interval 昇順で返す

    例:
      xmonitor-usermetrics-1mcd-interval0.001.csv
      netdata-kernelmetrics-1mcd-interval0.5.csv
      ...
    """
    pattern = os.path.join(
        base_dir, f"{tool}-{kind}-{mcd}mcd-interval*.csv"
    )
    files = glob.glob(pattern)
    found: List[Tuple[float, str]] = []
    for f in files:
        m = re.search(r"interval([0-9.]+)\.csv$", f)
        if m:
            sec = float(m.group(1))
            found.append((sec, f))
    found.sort(key=lambda x: x[0])
    return found


def get_color_from_label(label: str):
    """
    ラベル "X-Monitor (1s)" / "Netdata (500ms)" から interval 部分だけを抜き出して
    COLORS で色を引く。
    """
    m = re.search(r"\((.+)\)$", label)
    if not m:
        return None
    interval_str = m.group(1)  # 1s / 500ms / 1ms / 200μs ...
    return COLORS.get(interval_str, None)


def plot_one(ax, curves, xmax: float):
    """
    curves: iterable of (x_values, y_values, label)
    """
    markers = ['o', '*', '^', 'x', 's', 'd']
    for i, (x, y, label) in enumerate(curves):
        color = get_color_from_label(label)
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
        description="Plot CDFs for user/kernel metrics (X-Monitor vs Netdata) with multiple intervals."
    )
    parser.add_argument("--dir", default=".", help="directory containing CSV files (timestamp dir or .../NNNmcd)")
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
    # ウォームアップ 15 秒分を除外するフラグ
    parser.add_argument(
        "--exclude-warmup", action="store_true",
        help="exclude first 15 seconds of samples (Netdata/X-Monitor) from CDF"
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

    # X-Monitor / Netdata の interval* ファイルを自動検出
    xmon_user   = find_interval_files(search_root, "xmonitor", "usermetrics", mcd)
    xmon_kernel = find_interval_files(search_root, "xmonitor", "kernelmetrics", mcd)
    net_user    = find_interval_files(search_root, "netdata", "usermetrics", mcd)
    net_kernel  = find_interval_files(search_root, "netdata", "kernelmetrics", mcd)

    # 必須チェック
    if not xmon_user or not xmon_kernel or not net_user or not net_kernel:
        print("Missing required interval files under:", search_root)
        print("Found status:")
        print(f"  xmonitor-usermetrics : {len(xmon_user)} file(s)")
        print(f"  xmonitor-kernelmetrics: {len(xmon_kernel)} file(s)")
        print(f"  netdata-usermetrics  : {len(net_user)} file(s)")
        print(f"  netdata-kernelmetrics: {len(net_kernel)} file(s)")
        print("\nExpected patterns like:")
        print(f"  {os.path.join(search_root, f'xmonitor-usermetrics-{mcd}mcd-interval*.csv')}")
        print(f"  {os.path.join(search_root, f'xmonitor-kernelmetrics-{mcd}mcd-interval*.csv')}")
        print(f"  {os.path.join(search_root, f'netdata-usermetrics-{mcd}mcd-interval*.csv')}")
        print(f"  {os.path.join(search_root, f'netdata-kernelmetrics-{mcd}mcd-interval*.csv')}")
        sys.exit(1)

    # ---- helper: ウォームアップ行を削る ----
    def cut_warmup(latencies: np.ndarray, interval_sec: float) -> np.ndarray:
        """
        interval_sec ごとのサンプリングの場合に、
        先頭 15 秒分 (15 / interval_sec サンプル) を削る。
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

    # X-Monitor (usermetrics) 全 interval
    for sec, path in xmon_user:
        lat = load_latencies_ms(path, col, skiprows)   # 未ソート
        lat = cut_warmup(lat, sec)                     # 先頭 N 行を削る
        lat = np.sort(lat)                             # ここでソート
        p = cdf(lat)
        label = f"X-Monitor ({interval_label(sec)})"
        curves_user.append((lat, p, label))

    # Netdata (usermetrics) 全 interval
    for sec, path in net_user:
        lat = load_latencies_ms(path, col, skiprows)
        lat = cut_warmup(lat, sec)
        lat = np.sort(lat)
        p = cdf(lat)
        label = f"Netdata ({interval_label(sec)})"
        curves_user.append((lat, p, label))

    # 読み込み（Kernel metrics）
    curves_kernel = []

    # X-Monitor (kernelmetrics)
    for sec, path in xmon_kernel:
        lat = load_latencies_ms(path, col, skiprows)
        lat = cut_warmup(lat, sec)
        lat = np.sort(lat)
        p = cdf(lat)
        label = f"X-Monitor ({interval_label(sec)})"
        curves_kernel.append((lat, p, label))

    # Netdata (kernelmetrics)
    for sec, path in net_kernel:
        lat = load_latencies_ms(path, col, skiprows)
        lat = cut_warmup(lat, sec)
        lat = np.sort(lat)
        p = cdf(lat)
        label = f"Netdata ({interval_label(sec)})"
        curves_kernel.append((lat, p, label))

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