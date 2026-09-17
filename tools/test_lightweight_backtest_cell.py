"""Execute the generated standard Qlib backtest cell against small mocks."""

from __future__ import annotations

import contextlib
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "Qlib模型训练与回测_Colab教学版.ipynb"


def make_predictions() -> pd.DataFrame:
    dates = pd.bdate_range("2019-01-02", "2020-01-10")
    codes = [f"SH{600000 + i:06d}" for i in range(80)]
    index = pd.MultiIndex.from_product(
        [dates, codes], names=["datetime", "instrument"]
    )
    return pd.DataFrame(
        {"score": np.linspace(-1.0, 1.0, len(index), dtype=float)}, index=index
    )


class FakeDataset:
    def __init__(self, predictions: pd.DataFrame):
        self.predictions = predictions

    def prepare(self, segment, col_set=None, data_key=None):
        assert segment == "test" and col_set == "label"
        assert data_key == "infer"
        labels = self.predictions.rename(columns={"score": "LABEL0"}).copy()
        labels.iloc[:, 0] = np.linspace(-0.02, 0.02, len(labels), dtype=float)
        return labels


class FakeRecorder:
    id = "mock-recorder"

    def __init__(self):
        self.objects = {}

    def save_objects(self, artifact_path=None, **objects):
        for name, value in objects.items():
            key = f"{artifact_path}/{name}" if artifact_path else name
            self.objects[key] = value

    def load_object(self, name):
        return self.objects[name]


class FakeWorkflow:
    def __init__(self, recorder):
        self.recorder = recorder

    def start(self, **_kwargs):
        return contextlib.nullcontext()

    def get_recorder(self):
        return self.recorder


class FakeModel:
    def predict(self, dataset):
        return dataset.predictions.copy()


class FakePortAnaRecord:
    def __init__(self, recorder, config, freq):
        assert freq == "day"
        self.recorder = recorder
        self.config = config

    def generate(self):
        codes = self.config["backtest"]["exchange_kwargs"]["codes"]
        assert isinstance(codes, list) and len(codes) == 80
        dates = pd.bdate_range("2019-01-02", "2019-01-31")
        report = pd.DataFrame(
            {
                "return": np.linspace(-0.01, 0.01, len(dates)),
                "cost": 0.001,
                "bench": 0.0,
                "turnover": 0.1,
            },
            index=dates,
        )
        analysis = pd.DataFrame({"risk": [0.1]}, index=["annualized_return"])
        artifacts = {
            "report_normal_1day.pkl": report,
            "positions_normal_1day.pkl": {},
            "port_analysis_1day.pkl": analysis,
        }
        self.recorder.save_objects(
            artifact_path="portfolio_analysis",
            **artifacts,
        )
        return artifacts


def main():
    notebook_text = NOTEBOOK.read_text(encoding="utf-8-sig")
    notebook = json.loads(notebook_text)
    cell_source = next(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and "Qlib 低内存信号与标准组合回测" in "".join(cell.get("source", []))
    )

    recorder = FakeRecorder()
    dataset = FakeDataset(make_predictions())
    port_analysis_config = {
        "backtest": {"exchange_kwargs": {"codes": "csi300"}}
    }
    environment = {
        "pd": pd,
        "gc": gc,
        "R": FakeWorkflow(recorder),
        "PortAnaRecord": FakePortAnaRecord,
        "model": FakeModel(),
        "dataset": dataset,
        "handler": object(),
        "task": {},
        "port_analysis_config": port_analysis_config,
        "LOW_MEMORY_BACKTEST_END": "2019-12-31",
        "show_process_memory": lambda _stage: None,
    }
    exec(compile(cell_source, str(NOTEBOOK), "exec"), environment)

    assert environment["ba_rid"] == recorder.id
    assert environment["label_df"].index.get_level_values("datetime").max() <= pd.Timestamp(
        "2019-12-31"
    )
    assert len(port_analysis_config["backtest"]["exchange_kwargs"]["codes"]) == 80
    assert "pred_df" in environment
    assert "report_normal_df" in environment
    assert "positions" in environment
    assert "analysis_df" in environment
    for variable_name in ("model", "dataset", "handler", "task"):
        assert variable_name not in environment
    for artifact in (
        "pred.pkl",
        "portfolio_analysis/report_normal_1day.pkl",
        "portfolio_analysis/positions_normal_1day.pkl",
        "portfolio_analysis/port_analysis_1day.pkl",
    ):
        assert artifact in recorder.objects

    for forbidden in (
        "qlib_analysis_checkpoint",
        "files.download",
        "RESTORE_ANALYSIS_CHECKPOINT",
        "R.save_objects(trained_model=model)",
        "SignalRecord(",
        "del pred_df",
    ):
        assert forbidden not in notebook_text

    print("standard Qlib workflow mock OK | no custom checkpoint download")


if __name__ == "__main__":
    main()
