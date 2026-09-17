"""Split the generated Qlib master notebook into two independent Colab lessons."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4


def markdown(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": uuid4().hex[:8],
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": uuid4().hex[:8],
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


def clone(cell: dict, source: str | None = None) -> dict:
    result = deepcopy(cell)
    if source is not None:
        result["source"] = source.strip().splitlines(keepends=True)
    if result["cell_type"] == "code":
        result["execution_count"] = None
        result["outputs"] = []
    return result


def notebook(metadata: dict, cells: list[dict], minor: int, name: str) -> dict:
    notebook_metadata = deepcopy(metadata)
    notebook_metadata.setdefault("colab", {})["name"] = name
    return {
        "nbformat": 4,
        "nbformat_minor": minor,
        "metadata": notebook_metadata,
        "cells": cells,
    }


def write_notebook(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Created {path} | cells={len(payload['cells'])}")


EXPLORATION_CONFIG = r'''
# ==================== 小样本探索配置 ====================
def show_process_memory(stage):
    """显示当前 Python 进程内存，便于观察教学样本的资源占用。"""
    try:
        import psutil
        rss_gb = psutil.Process().memory_info().rss / (1024 ** 3)
        print(f"[内存] {stage}: {rss_gb:.2f} GiB")
    except Exception:
        pass


demo_handler_config = {
    "start_time": "2019-01-01",
    "end_time": "2019-01-31",
    "fit_start_time": "2019-01-01",
    "fit_end_time": "2019-01-31",
    "instruments": market,
}

print("探索区间：2019-01-01 → 2019-01-31")
'''


TRAINING_CONFIG = r'''
# ==================== 独立训练配置 ====================
def show_process_memory(stage):
    """显示当前 Python 进程内存，便于区分内存终止与网络断连。"""
    try:
        import psutil
        rss_gb = psutil.Process().memory_info().rss / (1024 ** 3)
        print(f"[内存] {stage}: {rss_gb:.2f} GiB")
    except Exception:
        pass


TEACHING_SEGMENTS = {
    "train": ("2017-01-01", "2017-12-31"),
    "valid": ("2018-01-01", "2018-12-31"),
    "test": ("2019-01-01", "2020-08-01"),
}
LOW_MEMORY_BACKTEST_END = "2019-12-31"

data_handler_config = {
    "start_time": TEACHING_SEGMENTS["train"][0],
    "end_time": TEACHING_SEGMENTS["test"][1],
    "fit_start_time": TEACHING_SEGMENTS["train"][0],
    "fit_end_time": TEACHING_SEGMENTS["train"][1],
    "instruments": market,
    "drop_raw": True,
}

print("训练、验证与测试区间：", TEACHING_SEGMENTS)
'''


TRAINING_DATASET = r'''
# 只创建这一套正式 Alpha158；本 Notebook 不运行前半程探索。
import gc
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH

handler = Alpha158(**data_handler_config)
dataset = DatasetH(handler=handler, segments=TEACHING_SEGMENTS)
show_process_memory("正式 Alpha158 初始化后（drop_raw=True）")

print("正式训练数据集准备完成：")
for segment_name, segment_range in TEACHING_SEGMENTS.items():
    print(f"  {segment_name:>5}: {segment_range[0]} → {segment_range[1]}")
'''


RECOVERY_CELL = r'''
# 正常顺序运行时无需修改；只有 Colab 已回收运行时且手里有检查点时才改为 True。
RESTORE_ANALYSIS_CHECKPOINT = False  #@param {type:"boolean"}

if RESTORE_ANALYSIS_CHECKPOINT:
    import gzip
    import io
    import pickle
    from qlib.backtest.position import Position
    from google.colab import files

    print("请选择自动下载的 qlib_analysis_checkpoint.pkl.gz")
    uploaded = files.upload()
    if not uploaded:
        raise RuntimeError("没有收到检查点文件，请重新运行本单元格并选择文件。")
    checkpoint_name, checkpoint_bytes = next(iter(uploaded.items()))
    with gzip.GzipFile(fileobj=io.BytesIO(checkpoint_bytes), mode="rb") as checkpoint_file:
        checkpoint = pickle.load(checkpoint_file)
    if checkpoint.get("schema_version") != 1:
        raise ValueError("检查点版本不受支持，请使用同一教程版本重新生成。")

    pred_df = checkpoint["pred_df"]
    label_df = checkpoint["label_df"]
    report_normal_df = checkpoint["report_normal_df"]
    analysis_df = checkpoint["analysis_df"]
    positions = {}
    for date_text, codes in checkpoint["positions"].items():
        weight = 1.0 / len(codes)
        position_dict = {
            stock: {"amount": weight, "price": 1.0, "weight": weight}
            for stock in codes
        }
        positions[pd.Timestamp(date_text)] = Position(cash=0.0, position_dict=position_dict)
    ba_rid = f"checkpoint:{checkpoint_name}"
    print(
        f"检查点恢复完成：交易日={len(report_normal_df)}，"
        f"预测行数={len(pred_df):,}，持仓日数={len(positions)}"
    )
else:
    print("正常顺序运行：继续使用刚刚生成的回测结果。")
'''


RECOVERY_SETUP = r'''
# 本单元格只准备分析依赖，不下载行情数据。
import importlib.util
import subprocess
import sys

if importlib.util.find_spec("qlib") is None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "pyqlib==0.9.7",
            "plotly==6.6.0",
            "statsmodels==0.14.6",
        ],
        check=True,
    )

import numpy as np
import pandas as pd

print("绩效分析依赖准备完成。")
'''


ANALYSIS_READY = r'''
from qlib.contrib.report import analysis_model, analysis_position

required_analysis_objects = [
    "pred_df", "label_df", "report_normal_df", "positions", "analysis_df"
]
missing_analysis_objects = [name for name in required_analysis_objects if name not in globals()]
if missing_analysis_objects:
    raise RuntimeError(
        "当前运行时没有分析数据。请从训练流程重新运行，"
        "或在第 6.3 节上传 qlib_analysis_checkpoint.pkl.gz。"
    )

print("轻量回测结果已在内存中，可直接进行绩效与 IC 分析。")
'''


def build(master_path: Path, exploration_path: Path, training_path: Path) -> None:
    master = json.loads(master_path.read_text(encoding="utf-8-sig"))
    cells = master["cells"]
    metadata = master.get("metadata", {})
    minor = master.get("nbformat_minor", 5)

    slim_imports = r'''
import qlib
import pandas as pd
from qlib.constant import REG_CN
'''

    exploration_cells = [
        markdown("""
# Qlib 数据与因子探索

**第一部分 · 课堂讲解版**

本 Notebook 只负责环境、Qlib 初始化、A 股数据查询、表达式特征以及一个月的 Alpha158 小样本探索。它不会创建正式训练集，也不会训练模型。完成后请断开并删除运行时，再打开第二部分，让训练与回测从干净内存开始。
"""),
        clone(cells[1]),
        clone(cells[2]),
        clone(cells[4]),
        clone(cells[5], slim_imports),
        *[clone(cell) for cell in cells[6:43]],
        clone(cells[43], EXPLORATION_CONFIG),
        *[clone(cell) for cell in cells[44:59]],
        markdown("""
### 4.2 正式训练数据集放在第二部分

这里不创建覆盖多年数据的正式 `DatasetH`，避免讲解阶段的缓存进入训练阶段。请先完成上面的探索与练习，然后选择 **“运行时 → 断开连接并删除运行时”**，再打开《Qlib 模型训练、回测与绩效分析》。
"""),
        markdown("""
## 下一步

第一部分到此结束。第二部分会在全新的 Colab 运行时中只创建一套 Alpha158，并完成模型训练、TopK 回测和绩效分析。
"""),
    ]

    setup_source = "".join(cells[2]["source"])
    training_cells = [
        markdown("""
# Qlib 模型训练、回测与绩效分析

**第二部分 · 独立运行版**

本 Notebook 不依赖第一部分的任何变量。请在新的 Colab 运行时中从头运行，它会独立准备环境，只创建一套正式 Alpha158，然后完成 LightGBM 训练、轻量 TopK 回测与第 7 节绩效分析。
"""),
        markdown("""
## 运行方式

正常学习请选择 **“运行时 → 全部运行”**。完成回测后浏览器会下载 `qlib_analysis_checkpoint.pkl.gz`。如果后续分析阶段发生断线，可重新打开本 Notebook，直接到 6.3 依次运行三个恢复单元格，再从第 7 节继续，无需下载行情或重新训练。
"""),
        clone(cells[1], "## 第二部分运行环境"),
        clone(cells[2], setup_source),
        clone(cells[4]),
        clone(cells[5]),
        *[clone(cell) for cell in cells[6:13]],
        markdown("""
## 4.2 配置正式训练数据集

第一部分的探索数据不会带入这里。本节直接创建启用 `drop_raw=True` 的正式处理器与唯一一套 `DatasetH`。
"""),
        code(TRAINING_CONFIG),
        code(TRAINING_DATASET),
        *[clone(cell) for cell in cells[65:77]],
        markdown("""
### 6.3 断线后的可选恢复

正常顺序运行时继续执行即可。若 Colab 在回测完成后回收了运行时，请重新打开本 Notebook，只运行下面三个单元格：轻量分析环境、辅助函数、检查点恢复。把恢复开关改为 `True` 并上传检查点后，从第 7 节继续。
"""),
        code(RECOVERY_SETUP),
        clone(cells[3]),
        code(RECOVERY_CELL),
        *[clone(cell) for cell in cells[77:]],
    ]

    for cell in training_cells:
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        source = source.replace(
            "复用第 4 节已创建的 DatasetH，避免重复加载 Alpha158。",
            "复用本 Notebook 启动阶段创建的 DatasetH，避免重复加载 Alpha158。",
        )
        source = source.replace(
            "请在“绩效分析恢复版”中上传它。",
            "可在本 Notebook 的 6.3 节上传它。",
        )
        source = source.replace(
            "请打开网页中的“绩效分析恢复版”，上传 qlib_analysis_checkpoint.pkl.gz 后继续。",
            "请从训练流程重新运行，或在第 6.3 节上传 qlib_analysis_checkpoint.pkl.gz。",
        )
        if "missing_analysis_objects" in source:
            source = ANALYSIS_READY.strip()
        cell["source"] = source.splitlines(keepends=True)

    write_notebook(
        exploration_path,
        notebook(metadata, exploration_cells, minor, exploration_path.name),
    )
    write_notebook(
        training_path,
        notebook(metadata, training_cells, minor, training_path.name),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--exploration-output", required=True, type=Path)
    parser.add_argument("--training-output", required=True, type=Path)
    args = parser.parse_args()
    build(args.input, args.exploration_output, args.training_output)


if __name__ == "__main__":
    main()
