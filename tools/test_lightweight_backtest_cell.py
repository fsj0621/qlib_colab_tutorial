"""Execute the generated lightweight backtest cell against small deterministic mocks."""

from __future__ import annotations

import contextlib
import gc
import json
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "Qlib模型训练与回测_Colab教学版.ipynb"


class FakePosition:
    def __init__(self, cash=0.0, position_dict=None):
        self.cash = cash
        self.position = dict(position_dict or {})

    def get_stock_list(self):
        return list(self.position)

    def get_stock_weight(self, code):
        return self.position[code]["weight"]


class FakeDataAPI:
    @staticmethod
    def features(instruments, fields, start_time, end_time, **_kwargs):
        dates = pd.bdate_range(start_time, min(end_time, "2019-01-31"))
        index = pd.MultiIndex.from_product(
            [instruments, dates], names=["instrument", "datetime"]
        )
        values = np.linspace(-0.02, 0.02, len(index), dtype=float)
        return pd.DataFrame({fields[0]: values}, index=index)


class FakeModel:
    @staticmethod
    def predict(_dataset):
        dates = pd.bdate_range("2019-01-02", "2019-01-31")
        codes = [f"SH{600000 + i:06d}" for i in range(80)]
        index = pd.MultiIndex.from_product(
            [dates, codes], names=["datetime", "instrument"]
        )
        return pd.Series(np.linspace(-1.0, 1.0, len(index)), index=index, name="score")


class FakeRecorder:
    id = "mock-recorder"

    def __init__(self):
        self.objects = {}

    def save_objects(self, artifact_path=None, **objects):
        for name, value in objects.items():
            key = f"{artifact_path}/{name}" if artifact_path else name
            self.objects[key] = value


class FakeWorkflow:
    def __init__(self, recorder):
        self.recorder = recorder

    def start(self, **_kwargs):
        return contextlib.nullcontext()

    def get_recorder(self):
        return self.recorder


def fake_risk_analysis(values, freq="1day"):
    del freq
    values = pd.Series(values).dropna()
    std = float(values.std())
    mean = float(values.mean())
    cumulative = values.cumsum()
    drawdown = cumulative - cumulative.cummax()
    return pd.DataFrame(
        {
            "risk": [
                mean,
                std,
                mean * 252,
                mean / std * np.sqrt(252) if std else np.nan,
                float(drawdown.min()),
            ]
        },
        index=["mean", "std", "annualized_return", "information_ratio", "max_drawdown"],
    )


def install_fake_qlib_modules():
    qlib_module = types.ModuleType("qlib")
    data_module = types.ModuleType("qlib.data")
    data_module.D = FakeDataAPI
    backtest_module = types.ModuleType("qlib.backtest")
    position_module = types.ModuleType("qlib.backtest.position")
    position_module.Position = FakePosition
    contrib_module = types.ModuleType("qlib.contrib")
    evaluate_module = types.ModuleType("qlib.contrib.evaluate")
    evaluate_module.risk_analysis = fake_risk_analysis
    sys.modules.update(
        {
            "qlib": qlib_module,
            "qlib.data": data_module,
            "qlib.backtest": backtest_module,
            "qlib.backtest.position": position_module,
            "qlib.contrib": contrib_module,
            "qlib.contrib.evaluate": evaluate_module,
        }
    )


def main():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8-sig"))
    cell_source = next(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if "免费 Colab 轻量 TopK 回测" in "".join(cell.get("source", []))
        and cell.get("cell_type") == "code"
    )

    install_fake_qlib_modules()
    recorder = FakeRecorder()
    environment = {
        "pd": pd,
        "np": np,
        "gc": gc,
        "R": FakeWorkflow(recorder),
        "model": FakeModel(),
        "dataset": object(),
        "handler": object(),
        "task": {},
        "benchmark": "SH000300",
        "TEACHING_SEGMENTS": {"test": ("2019-01-01", "2020-08-01")},
        "LOW_MEMORY_BACKTEST_END": "2019-12-31",
        "IN_COLAB": False,
        "Path": Path,
        "show_process_memory": lambda _stage: None,
    }
    exec(compile(cell_source, str(NOTEBOOK), "exec"), environment)

    report = environment["report_normal_df"]
    positions = environment["positions"]
    analysis = environment["analysis_df"]
    assert list(report.columns) == ["return", "cost", "bench", "turnover"]
    assert len(report) == len(positions) >= 20
    assert report.index.is_monotonic_increasing
    assert report["turnover"].between(0.0, 1.0).all()
    assert max(len(position.get_stock_list()) for position in positions.values()) == 50
    assert analysis.index.nlevels == 2
    for artifact in (
        "pred.pkl",
        "portfolio_analysis/report_normal_1day.pkl",
        "portfolio_analysis/positions_normal_1day.pkl",
        "portfolio_analysis/port_analysis_1day.pkl",
    ):
        assert artifact in recorder.objects
    checkpoint_path = environment["checkpoint_path"]
    assert checkpoint_path.exists() and checkpoint_path.stat().st_size > 0

    recovery_notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8-sig"))
    recovery_loader = next(
        "".join(cell.get("source", []))
        for cell in recovery_notebook["cells"]
        if cell.get("cell_type") == "code" and "checkpoint = pickle.load" in "".join(cell.get("source", []))
    )
    recovery_loader = recovery_loader.replace(
        "RESTORE_ANALYSIS_CHECKPOINT = False",
        "RESTORE_ANALYSIS_CHECKPOINT = True",
    )
    google_module = types.ModuleType("google")
    colab_module = types.ModuleType("google.colab")
    colab_module.files = types.SimpleNamespace(
        upload=lambda: {checkpoint_path.name: checkpoint_path.read_bytes()}
    )
    sys.modules.update({"google": google_module, "google.colab": colab_module})
    recovery_environment = {"pd": pd}
    exec(compile(recovery_loader, str(NOTEBOOK), "exec"), recovery_environment)
    assert recovery_environment["report_normal_df"].equals(report)
    assert len(recovery_environment["positions"]) == len(positions)
    assert recovery_environment["pred_df"].equals(environment["pred_df"])

    checkpoint_path.unlink()
    print(
        f"lightweight backtest + recovery mock OK | "
        f"days={len(report)} | positions={len(positions)}"
    )


if __name__ == "__main__":
    main()
