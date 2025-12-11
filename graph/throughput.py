# import os
# import re
# import numpy as np
# import matplotlib.pyplot as plt
# import matplotlib
# from packaging import version


# fontsize = 25  # default is 25
# legend_fontsize = 23  # default is 17
# # figsize = (24, 5)  # default is (10, 7)
# figsize = (37, 4)  # default is (10, 7)
# ylim = 1000
# line_width = 0.70
# GROUP_SPACING = 7.0
# bbox_to_anchor = (0.5, 1.37)
# ########################################
# # fontsize = 25  # default is 25
# # legend_fontsize = 23  # default is 17
# # # figsize = (24, 5)  # default is (10, 7)
# # figsize = (33, 4)  # default is (10, 7)
# # ylim = 1000
# # line_width = 0.70
# # GROUP_SPACING = 7.0
# # bbox_to_anchor = (0.5, 1.40)
# ##########################################

# THROUGHPUT_RE = re.compile(r"Total QPS\s*=\s*([\d.]+)")

# # ここを 7 本構成に拡張
# LABELS = [
#     "No Monitoring",
#     "Netdata (1000ms)",
#     "Netdata (500ms)",
#     "Netdata (1ms)",
#     "X-Monitor (1000ms)",
#     "X-Monitor (500ms)",
#     "X-Monitor (1ms)",
# ]

# ################# Label ↔ interval(sec) / tool 対応 ################
# # throughput のラベルはそのまま維持しつつ、
# # 内部的に「どのツールの、どの interval を読むか」をここで定義。
# LABEL_META = {
#     "No Monitoring": {
#         "tool": None,       # interval なし
#         "interval": None,
#     },
#     # Netdata: 1000 / 500 / 1ms
#     "Netdata (1000ms)": {
#         "tool": "netdata",
#         "interval": 1.0,    # 1000ms = 1.0s
#     },
#     "Netdata (500ms)": {
#         "tool": "netdata",
#         "interval": 0.5,    # 500ms = 0.5s
#     },
#     "Netdata (1ms)": {
#         "tool": "netdata",
#         "interval": 0.001,  # 1ms = 0.001s
#     },
#     # X-Monitor: 1000 / 500 / 1ms
#     "X-Monitor (1000ms)": {
#         "tool": "xmonitor",
#         "interval": 1.0,
#     },
#     "X-Monitor (500ms)": {
#         "tool": "xmonitor",
#         "interval": 0.5,
#     },
#     "X-Monitor (1ms)": {
#         "tool": "xmonitor",
#         "interval": 0.001,
#     },
# }

# ################# Design Configuration ############
# # すでに存在していたラベルの色はそのまま維持。
# # 新規ラベルにだけ新しい色を足している。

# COLORS = {
#     "No Monitoring":        "#6E738D",  # Neutral gray (base)

#     # Netdata 系
#     "Netdata (1000ms)":     "#F5A97F",  # Peach (既存)
#     "Netdata (500ms)":      "#F28F79",  # 少し淡いトーンの追加色
#     "Netdata (1ms)":        "#E46876",  # 少し濃いトーンの追加色

#     # X-Monitor 系
#     "X-Monitor (1000ms)":   "#5AB8A8",  # Teal（既存）
#     "X-Monitor (500ms)":    "#72A7E3",  # 以前の 100ms の色を流用
#     "X-Monitor (1ms)":      "#C7A0E8",  # 以前の 10ms の色を流用
# }

# HATCHES = {
#     "No Monitoring":        "***",
#     "Netdata (1000ms)":     "////",
#     "Netdata (500ms)":      "----",   # Netdata 系は同じでもよいなら共通
#     "Netdata (1ms)":        "ooo",

#     "X-Monitor (1000ms)":   "\\\\\\\\",
#     "X-Monitor (500ms)":    "xxxx",
#     "X-Monitor (1ms)":      "....",
# }

# EDGE_KW = dict(edgecolor="black", linewidth=1.1)
# ####################################################


# def _find_interval_files_txt(log_dir: str, tool: str, metric: str, n: int):
#     """
#     CDF スクリプトの find_interval_files と同じノリで、
#     {tool}-{metric}metrics-{n}mcd-interval*.txt を全部拾って
#     [(interval_sec, path), ...] を interval 昇順で返す。
#     """
#     import glob

#     pattern = os.path.join(
#         log_dir, f"{tool}-{metric}metrics-{n}mcd-interval*.txt"
#     )
#     files = glob.glob(pattern)
#     found = []
#     for f in files:
#         m = re.search(r"interval([0-9.]+)\.txt$", f)
#         if not m:
#             continue
#         sec = float(m.group(1))
#         found.append((sec, f))
#     found.sort(key=lambda x: x[0])
#     return found


# def _select_file_for_interval(
#     log_dir: str, tool: str, metric: str, n: int, target_interval: float
# ):
#     """
#     指定された tool/metric/mcd に対して、
#     interval*.txt の中から target_interval(s) に一致するファイルを 1 つ選ぶ。
#     見つからなければ None を返す。
#     """
#     candidates = _find_interval_files_txt(log_dir, tool, metric, n)
#     for sec, path in candidates:
#         if abs(sec - target_interval) < 1e-9:
#             return path
#     return None


# def collect_throughput(log_dir, metric, n):
#     """
#     1 run_dir (= .../RUN_ID/NNNmcd) から各ラベルの QPS を集める。
#     """
#     data = {label: [] for label in LABELS}
#     for label in LABELS:
#         meta = LABEL_META[label]

#         # No Monitoring: interval なし、固定ファイル名
#         if meta["tool"] is None:
#             path = os.path.join(log_dir, f"no_monitoring-{n}mcd.txt")
#             if not os.path.exists(path):
#                 continue
#         else:
#             tool = meta["tool"]
#             interval_sec = meta["interval"]

#             path = _select_file_for_interval(
#                 log_dir, tool=tool, metric=metric, n=n, target_interval=interval_sec
#             )
#             if path is None or not os.path.exists(path):
#                 # その interval のファイルが存在しない場合はスキップ
#                 continue

#         # 実際にファイルから Total QPS を拾う
#         with open(path) as f:
#             for line in f:
#                 m = THROUGHPUT_RE.search(line)
#                 if m:
#                     data[label].append(float(m.group(1)))  # QPS
#                     break
#     return data


# def collect_stats_across_runs(base_dir, metric, nums, run_ids=None):
#     if run_ids is None:
#         run_ids = [str(i) for i in range(10)]  # "0".."9"

#     means = {label: [] for label in LABELS}
#     stds  = {label: [] for label in LABELS}

#     for n in nums:
#         per_label_values = {label: [] for label in LABELS}
#         for rid in run_ids:
#             run_dir = os.path.join(base_dir, rid, f"{n:03d}mcd")
#             d = collect_throughput(run_dir, metric, n)
#             for label in LABELS:
#                 if d[label]:
#                     per_label_values[label].extend(d[label])

#         for label in LABELS:
#             vals = np.array(per_label_values[label], dtype=float) / 1000.0  # K ops/sec
#             if vals.size == 0:
#                 means[label].append(0.0)
#                 stds[label].append(0.0)
#             elif vals.size == 1:
#                 means[label].append(float(vals[0]))
#                 stds[label].append(0.0)
#             else:
#                 means[label].append(float(np.mean(vals)))
#                 stds[label].append(float(np.std(vals, ddof=1)))  # 不偏標準偏差
#     return means, stds


# def _plot_one_metric(means, stds, nums, save_path):
#     import matplotlib.pyplot as plt

#     x = np.arange(len(nums)) * GROUP_SPACING
#     width = line_width  # 7 本になるので少し細く（元は 0.13）
#     offsets = np.linspace(-width*3, width*3, len(LABELS))

#     plt.figure(figsize=figsize)

#     # ハッチ線を太くして見やすく
#     old_hatch_lw = plt.rcParams.get("hatch.linewidth", 1.0)
#     plt.rcParams["hatch.linewidth"] = 1.6

#     for i, label in enumerate(LABELS):
#         xpos = x + offsets[i]

#         # --- 下レイヤ: ハッチ＋色（枠も色） ---
#         plt.bar(
#             xpos, means[label],
#             yerr=stds[label],
#             width=width,
#             facecolor="white",
#             edgecolor=COLORS[label],    # ← ハッチ線は「この色」で描かれる
#             hatch=HATCHES[label],       # ← 密ハッチ
#             capsize=4,
#             ecolor="black",
#             error_kw={"elinewidth": 1.2},
#             linewidth=1.2,
#             zorder=2,
#         )

#         # --- 上レイヤ: 透明＋黒枠（ハッチなし） ---
#         plt.bar(
#             xpos, means[label],
#             width=width,
#             facecolor=(0, 0, 0, 0),     # 完全透明
#             edgecolor="black",          # ← 枠だけ黒で上書き
#             linewidth=1.4,
#             zorder=3,
#         )

#     # 戻す
#     plt.rcParams["hatch.linewidth"] = old_hatch_lw

#     # 軸
#     plt.xticks(x, [str(n) for n in nums], fontsize=fontsize)
#     plt.xlabel("Number of instances", fontsize=fontsize)
#     plt.tick_params(axis='y', labelsize=fontsize)
#     plt.ylabel("Throughput (K ops/sec)", fontsize=fontsize)
#     # plt.ylim(0, 1050)
#     plt.ylim(0, ylim)
#     plt.grid(axis="y", linestyle="--", alpha=0.4)

#     # 凡例（グラフ外）
#     import matplotlib.patches as mpatches
#     import matplotlib.patheffects as pe
#     legend_handles = []
#     for label in LABELS:
#         p = mpatches.Patch(
#             facecolor="white",
#             edgecolor=COLORS[label],   # ハッチと一致する色
#             hatch=HATCHES[label],
#             linewidth=1.2,
#         )
#         p.set_path_effects([pe.Stroke(linewidth=1.4, foreground="black"), pe.Normal()])
#         legend_handles.append(p)

#     plt.legend(
#         legend_handles,
#         LABELS,
#         loc="upper center",
#         bbox_to_anchor=bbox_to_anchor,   # ← グラフの上に配置
#         ncol=7,                       # 7 本なので 4 + 3 などに
#         fontsize=legend_fontsize,
#         frameon=True
#     )
#     plt.savefig(save_path, bbox_inches="tight", dpi=300)


# def plot_grouped_both(base_dir, nums=[1,5,10], run_ids=None):
#     # base_dir はタイムスタンプ直下（0〜9/001mcd ...）を想定（従来通り）

#     kernel_out = os.path.join(base_dir, "memcached_throughput_kernel.pdf")
#     user_out   = os.path.join(base_dir, "memcached_throughput_user.pdf")

#     # 1枚目: kernel
#     means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
#     _plot_one_metric(means_k, stds_k, nums, save_path=kernel_out)

#     # 2枚目: user
#     means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
#     _plot_one_metric(means_u, stds_u, nums, save_path=user_out)


# def print_throughput_means(base_dir, nums, run_ids=None):
#     # kernel
#     means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
#     print("===== Kernel metrics: Throughput Means (K ops/sec) =====")
#     for label in LABELS:
#         print(f"\n[ {label} ]")
#         for n, v in zip(nums, means_k[label]):
#             print(f"  {n} mcd : {v:.3f}")

#     # user
#     means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
#     print("\n===== User metrics: Throughput Means (K ops/sec) =====")
#     for label in LABELS:
#         print(f"\n[ {label} ]")
#         for n, v in zip(nums, means_u[label]):
#             print(f"  {n} mcd : {v:.3f} ops/sec")



import os
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from packaging import version


fontsize = 25  # default is 25
legend_fontsize = 23  # default is 17
# figsize = (24, 5)  # default is (10, 7)
figsize = (37, 4)  # default is (10, 7)
ylim = 1000
line_width = 0.70
GROUP_SPACING = 7.0
bbox_to_anchor = (0.5, 1.37)

THROUGHPUT_RE = re.compile(r"Total QPS\s*=\s*([\d.]+)")

# -------------------------------------------------------
# Interval 関連設定
# -------------------------------------------------------

NO_MONITORING_LABEL = "No Monitoring"

# ツールごとの interval [sec] をここで定義しておけば OK
# 例: 1.0 = 1000ms, 0.5 = 500ms, 0.001 = 1ms, 0.0001 = 100us など
TOOL_INTERVALS = {
    "netdata":  [1.0, 0.5, 0.001],   # 必要に応じて 0.1, 0.01, 0.0001 など追加
    "xmonitor": [1.0, 0.5, 0.001],
}

TOOL_PREFIX = {
    "netdata":  "Netdata",
    "xmonitor": "X-Monitor",
}


def format_interval_label(interval_sec: float) -> str:
    """interval(sec) を '1000ms' や '100us' のようなラベルに変換"""
    ms = interval_sec * 1000.0
    if ms >= 1.0:
        # ms 表記
        if abs(ms - round(ms)) < 1e-9:
            return f"{int(round(ms))}ms"
        else:
            return f"{ms:.3g}ms"
    else:
        # us 表記
        us = interval_sec * 1e6
        if abs(us - round(us)) < 1e-9:
            return f"{int(round(us))}us"
        else:
            return f"{us:.3g}us"


def build_labels_and_meta():
    """
    TOOL_INTERVALS から LABELS と LABEL_META を自動生成。
    LABELS: プロット順
    LABEL_META[label] = {"tool": ..., "interval": ...}
    """
    labels = [NO_MONITORING_LABEL]
    meta = {
        NO_MONITORING_LABEL: {"tool": None, "interval": None},
    }

    for tool, intervals in TOOL_INTERVALS.items():
        prefix = TOOL_PREFIX[tool]
        for sec in intervals:
            iv_label = format_interval_label(sec)
            label = f"{prefix} ({iv_label})"
            labels.append(label)
            meta[label] = {"tool": tool, "interval": sec}

    return labels, meta


# ここで実際に LABELS / LABEL_META を構築
LABELS, LABEL_META = build_labels_and_meta()

# -------------------------------------------------------
# グラフデザイン (色・ハッチ)
# 既知ラベルは個別指定、それ以外は後でフォールバック
# -------------------------------------------------------

COLORS = {
    "No Monitoring":        "#6E738D",  # Neutral gray (base)

    # ここから下は「既知のラベル」だけ指定しておく (任意)
    # 例: 1000ms, 500ms, 1ms の場合
    "Netdata (1000ms)":     "#F5A97F",  # Peach
    "Netdata (500ms)":      "#F28F79",
    "Netdata (1ms)":        "#E46876",

    "X-Monitor (1000ms)":   "#5AB8A8",  # Teal
    "X-Monitor (500ms)":    "#72A7E3",
    "X-Monitor (1ms)":      "#C7A0E8",
}

HATCHES = {
    "No Monitoring":        "***",
    "Netdata (1000ms)":     "////",
    "Netdata (500ms)":      "----",
    "Netdata (1ms)":        "ooo",

    "X-Monitor (1000ms)":   "\\\\\\\\",
    "X-Monitor (500ms)":    "xxxx",
    "X-Monitor (1ms)":      "....",
}

DEFAULT_COLOR = "#AAAAAA"
DEFAULT_HATCH = ""

EDGE_KW = dict(edgecolor="black", linewidth=1.1)

# -------------------------------------------------------
# ファイル探索まわり
# -------------------------------------------------------

def _find_interval_files_txt(log_dir: str, tool: str, metric: str, n: int):
    """
    {tool}-{metric}metrics-{n}mcd-interval*.txt を全部拾って
    [(interval_sec, path), ...] を interval 昇順で返す。
    """
    import glob

    pattern = os.path.join(
        log_dir, f"{tool}-{metric}metrics-{n}mcd-interval*.txt"
    )
    files = glob.glob(pattern)
    found = []
    for f in files:
        m = re.search(r"interval([0-9.]+)\.txt$", f)
        if not m:
            continue
        sec = float(m.group(1))
        found.append((sec, f))
    found.sort(key=lambda x: x[0])
    return found


def _select_file_for_interval(
    log_dir: str, tool: str, metric: str, n: int, target_interval: float
):
    """
    指定された tool/metric/n に対して、
    interval*.txt の中から target_interval(s) に一致するファイルを 1 つ選ぶ。
    見つからなければ None を返す。
    """
    candidates = _find_interval_files_txt(log_dir, tool, metric, n)
    for sec, path in candidates:
        if abs(sec - target_interval) < 1e-9:
            return path
    return None

# -------------------------------------------------------
# データ集約
# -------------------------------------------------------

def collect_throughput(log_dir, metric, n):
    """
    1 run_dir (= .../RUN_ID/NNNmcd) から各ラベルの QPS を集める。
    """
    data = {label: [] for label in LABELS}
    for label in LABELS:
        meta = LABEL_META[label]

        # No Monitoring: interval なし、固定ファイル名
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
                # その interval のファイルが存在しない場合はスキップ
                continue

        # 実際にファイルから Total QPS を拾う
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

# -------------------------------------------------------
# 描画
# -------------------------------------------------------

def _plot_one_metric(means, stds, nums, save_path):
    x = np.arange(len(nums)) * GROUP_SPACING
    width = line_width
    offsets = np.linspace(-width * (len(LABELS) - 1) / 2,
                          width * (len(LABELS) - 1) / 2,
                          len(LABELS))

    plt.figure(figsize=figsize)

    # ハッチ線を太くして見やすく
    old_hatch_lw = plt.rcParams.get("hatch.linewidth", 1.0)
    plt.rcParams["hatch.linewidth"] = 1.6

    for i, label in enumerate(LABELS):
        xpos = x + offsets[i]

        color = COLORS.get(label, DEFAULT_COLOR)
        hatch = HATCHES.get(label, DEFAULT_HATCH)

        # --- 下レイヤ: ハッチ＋色（枠も色） ---
        plt.bar(
            xpos, means[label],
            yerr=stds[label],
            width=width,
            facecolor="white",
            edgecolor=color,          # ハッチ線は「この色」で描かれる
            hatch=hatch,              # 密ハッチ
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
            facecolor=(0, 0, 0, 0),   # 完全透明
            edgecolor="black",        # 枠だけ黒で上書き
            linewidth=1.4,
            zorder=3,
        )

    # 戻す
    plt.rcParams["hatch.linewidth"] = old_hatch_lw

    # 軸
    plt.xticks(x, [str(n) for n in nums], fontsize=fontsize)
    plt.xlabel("Number of instances", fontsize=fontsize)
    plt.tick_params(axis="y", labelsize=fontsize)
    plt.ylabel("Throughput (K ops/sec)", fontsize=fontsize)
    plt.ylim(0, ylim)
    plt.grid(axis="y", linestyle="--", alpha=0.4)

    # 凡例（グラフ外）
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as pe
    legend_handles = []
    for label in LABELS:
        color = COLORS.get(label, DEFAULT_COLOR)
        hatch = HATCHES.get(label, DEFAULT_HATCH)
        p = mpatches.Patch(
            facecolor="white",
            edgecolor=color,
            hatch=hatch,
            linewidth=1.2,
        )
        p.set_path_effects([pe.Stroke(linewidth=1.4, foreground="black"), pe.Normal()])
        legend_handles.append(p)

    plt.legend(
        legend_handles,
        LABELS,
        loc="upper center",
        bbox_to_anchor=bbox_to_anchor,
        ncol=len(LABELS),
        fontsize=legend_fontsize,
        frameon=True
    )
    plt.savefig(save_path, bbox_inches="tight", dpi=300)


def plot_grouped_both(base_dir, nums=[1, 5, 10], run_ids=None):
    # base_dir はタイムスタンプ直下（0〜9/001mcd ...）を想定

    kernel_out = os.path.join(base_dir, "memcached_throughput_kernel.pdf")
    user_out   = os.path.join(base_dir, "memcached_throughput_user.pdf")

    # 1枚目: kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    _plot_one_metric(means_k, stds_k, nums, save_path=kernel_out)

    # 2枚目: user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    _plot_one_metric(means_u, stds_u, nums, save_path=user_out)


def print_throughput_means(base_dir, nums, run_ids=None):
    # kernel
    means_k, stds_k = collect_stats_across_runs(base_dir, "kernel", nums, run_ids)
    print("===== Kernel metrics: Throughput Means (K ops/sec) =====")
    for label in LABELS:
        print(f"\n[ {label} ]")
        for n, v in zip(nums, means_k[label]):
            print(f"  {n} mcd : {v:.3f}")

    # user
    means_u, stds_u = collect_stats_across_runs(base_dir, "user", nums, run_ids)
    print("\n===== User metrics: Throughput Means (K ops/sec) =====")
    for label in LABELS:
        print(f"\n[ {label} ]")
        for n, v in zip(nums, means_u[label]):
            print(f"  {n} mcd : {v:.3f} ops/sec")