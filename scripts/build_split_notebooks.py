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

本 Notebook 不依赖第一部分的任何变量。请在新的 Colab 运行时中从头运行，它会独立准备环境，只创建一套正式 Alpha158，然后使用 Qlib 标准工作流完成 LightGBM、TopK 回测与第 7 节绩效分析。
"""),
        markdown("""
## 运行方式

请选择 **“运行时 → 全部运行”**。预测、回测和第 7 节分析在同一个干净运行时内连续完成；本教程不再生成或下载额外检查点文件。
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
        clone(cells[3]),
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
