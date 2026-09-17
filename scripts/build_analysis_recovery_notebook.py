"""Build a standalone Colab notebook that resumes Qlib analysis from a checkpoint."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

def markdown(source: str):
    return {
        "cell_type": "markdown",
        "id": uuid4().hex[:8],
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def code(source: str):
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": uuid4().hex[:8],
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


def build(input_path: Path, output_path: Path):
    notebook = json.loads(input_path.read_text(encoding="utf-8-sig"))
    support_cell = next(
        cell
        for cell in notebook["cells"]
        if cell["cell_type"] == "code" and "def load_backtest_data" in "".join(cell["source"])
    )
    module7_index = next(
        index
        for index, cell in enumerate(notebook["cells"])
        if cell["cell_type"] == "markdown" and "".join(cell["source"]).lstrip().startswith("## 7.")
    )
    analysis_cells = deepcopy(notebook["cells"][module7_index:])

    setup = r'''
import subprocess
import sys

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
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

import gzip
import io
import pickle

import numpy as np
import pandas as pd

print(f"Python: {sys.version.split()[0]}")
print("分析环境准备完成 [OK]")
'''

    upload = r'''
from qlib.backtest.position import Position

if IN_COLAB:
    from google.colab import files

    print("请选择主 Notebook 下载的 qlib_analysis_checkpoint.pkl.gz")
    uploaded = files.upload()
    if not uploaded:
        raise RuntimeError("没有收到检查点文件，请重新运行本单元格并选择文件。")
    checkpoint_name, checkpoint_bytes = next(iter(uploaded.items()))
else:
    from pathlib import Path

    checkpoint_path = Path("qlib_analysis_checkpoint.pkl.gz")
    checkpoint_name = checkpoint_path.name
    checkpoint_bytes = checkpoint_path.read_bytes()

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
        code: {"amount": weight, "price": 1.0, "weight": weight}
        for code in codes
    }
    positions[pd.Timestamp(date_text)] = Position(cash=0.0, position_dict=position_dict)

ba_rid = f"checkpoint:{checkpoint_name}"
print(
    f"检查点恢复完成 [OK] 交易日={len(report_normal_df)}，"
    f"预测行数={len(pred_df):,}，持仓日数={len(positions)}"
)
'''

    recovery = {
        "nbformat": 4,
        "nbformat_minor": notebook.get("nbformat_minor", 5),
        "metadata": deepcopy(notebook.get("metadata", {})),
        "cells": [
            markdown(
                """
# Qlib 绩效分析恢复版

免费 Colab 可能在模型与回测已经完成后回收整个虚拟机。本 Notebook 不重新训练，也不下载行情数据；上传主 Notebook 自动下载的 `qlib_analysis_checkpoint.pkl.gz`，即可继续绩效、风险与 IC 分析。
"""
            ),
            markdown(
                """
## 使用顺序

1. 运行“准备分析环境”；
2. 上传 `qlib_analysis_checkpoint.pkl.gz`；
3. 从第 7 节开始顺序运行。

检查点包含预测、原始未来收益、轻量回测报告、持仓代码与风险指标，不包含模型、完整 Alpha158 特征或原始行情。
"""
            ),
            markdown("## 准备分析环境"),
            code(setup),
            deepcopy(support_cell),
            markdown("## 上传并恢复检查点"),
            code(upload),
            *analysis_cells,
        ],
    }
    for cell in recovery["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(recovery, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Created {output_path} | cells={len(recovery['cells'])}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.input, args.output)


if __name__ == "__main__":
    main()
