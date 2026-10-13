"""Saved experiments must replay from pinned data and export independently."""

from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from quant_lab.backtest import BacktestConfig
from quant_lab.research import run_experiment
from quant_lab.storage import (add_watchlist, export_experiment_zip, get_experiment,
                               list_experiments, list_watchlist, remove_watchlist,
                               replay_experiment, save_experiment)
from quant_lab.strategy import StrategySpec


def history() -> pd.DataFrame:
    closes = [10 + i * 0.12 + (i % 3) * 0.07 for i in range(40)]
    return pd.DataFrame({
        "date": pd.date_range("2026-01-05", periods=40, freq="B"),
        "open": [x - 0.05 for x in closes], "close": closes,
        "volume": [10000] * 40,
    })


def test_watchlist_is_normalized_and_persistent(tmp_path: Path) -> None:
    path = tmp_path / "lab.sqlite3"
    add_watchlist("港股", "700", path)
    add_watchlist("港股", "00700", path)
    assert list_watchlist(path) == [("港股", "00700")]
    remove_watchlist("港股", "00700", path)
    assert list_watchlist(path) == []


def test_saved_run_replays_and_zip_contains_inputs(tmp_path: Path) -> None:
    path = tmp_path / "lab.sqlite3"
    raw = history()
    spec = StrategySpec("dual_ma", 2, 3)
    config = BacktestConfig(initial_cash=10000, lot_size=100, commission_bps=0,
                            min_commission=0, sell_tax_bps=0, slippage_bps=0,
                            limit_pct=None)
    result = run_experiment(raw, raw, spec, config)
    saved_id = save_experiment(
        title="手算实验", hypothesis="均线规则在未来仍有效", notes="先检查成交日期",
        market="A 股", symbol="600519", raw_history=raw, signal_history=raw,
        spec=spec, config=config, train_fraction=0.70, result=result,
        source="测试历史源", adjustment="", received_at=datetime.now(timezone.utc),
        path=path,
    )
    assert list_experiments(path)[0]["id"] == saved_id
    record = get_experiment(saved_id, path)
    replay = replay_experiment(record)
    assert replay.audit_id == result.audit_id
    assert replay.full_stats.cumulative_return == pytest.approx(result.full_stats.cumulative_return)
    with ZipFile(BytesIO(export_experiment_zip(record))) as archive:
        assert set(archive.namelist()) == {"report.md", "raw_history.csv", "signal_history.csv", "assumptions.json"}
        assert json.loads(archive.read("assumptions.json"))["audit_id"] == result.audit_id
        assert hashlib.sha256(archive.read("raw_history.csv")).hexdigest() == record["raw_sha256"]
        assert b"600519" in archive.read("report.md")
