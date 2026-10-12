"""AI suggestions remain bounded; numerical evidence comes from local code."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from quant_lab.ai_research import AIUnavailableError, audit_snapshot, draft_hypothesis, draft_report
from quant_lab.backtest import BacktestConfig
from quant_lab.research import run_experiment, sensitivity_table
from quant_lab.strategy import StrategySpec


def history() -> pd.DataFrame:
    dates = pd.date_range("2026-01-05", periods=65, freq="B")
    close = 100 + np.arange(65) * 0.2 + np.sin(np.arange(65) * 0.5) * 2
    return pd.DataFrame(
        {"date": dates, "open": close - 0.2, "close": close,
         "volume": np.full(65, 100_000)}
    )


def configuration() -> BacktestConfig:
    return BacktestConfig(
        initial_cash=100_000, commission_bps=0, min_commission=0,
        buy_tax_bps=0, sell_tax_bps=0, slippage_bps=0, limit_pct=None,
    )


class FakeClient:
    def __init__(self, body: dict):
        self.body = body
        self.calls: list[dict] = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(status="completed", output_text=json.dumps(self.body))


def test_experiment_is_reproducible_and_grid_is_training_only() -> None:
    raw = history()
    spec = StrategySpec("dual_ma", 3, 8)
    first = run_experiment(raw, raw, spec, configuration())
    second = run_experiment(raw, raw, spec, configuration())
    grid = sensitivity_table(raw, raw, "dual_ma", configuration(), [3, 5], [8, 12])

    assert first.audit_id == second.audit_id
    assert first.split_date > raw["date"].iloc[0]
    assert len(grid) == 4
    assert audit_snapshot(first)["audit_id"] == first.audit_id
    assert set(first.strategy.orders["status"]).issubset({"filled", "blocked"})


def test_ai_hypothesis_is_validated_before_experiment() -> None:
    body = {
        "title": "Test moving averages", "rationale": "A falsifiable trend idea",
        "strategy_kind": "dual_ma", "short_window": 5, "long_window": 20,
        "assumptions": ["Daily data"], "statistical_risks": ["Overfitting"],
        "example_code": "# Display only",
    }
    fake = FakeClient(body)
    hypothesis = draft_hypothesis("Does a trend filter help?", "A 股", "600519", fake)

    assert hypothesis.strategy == StrategySpec("dual_ma", 5, 20)
    assert fake.calls[0]["text"]["format"]["type"] == "json_schema"
    assert fake.calls[0]["model"]

    invalid = FakeClient({**body, "short_window": 30, "long_window": 5})
    with pytest.raises(AIUnavailableError, match="本地验证"):
        draft_hypothesis("Test", "A 股", "600519", invalid)


def test_ai_report_receives_only_verified_snapshot() -> None:
    experiment = run_experiment(history(), history(), StrategySpec("dual_ma", 3, 8), configuration())
    fake = FakeClient(
        {"summary": "Uncertain result", "observations": ["Audit metrics are visible"],
         "limitations": ["Single asset"], "next_tests": ["Use another period"]}
    )
    report = draft_report(experiment, {"market": "A 股", "symbol": "600519"}, fake)
    request_payload = json.loads(fake.calls[0]["input"])

    assert report.summary == "Uncertain result"
    assert request_payload["verified_metrics"]["audit_id"] == experiment.audit_id
    assert "raw_prices" not in request_payload
