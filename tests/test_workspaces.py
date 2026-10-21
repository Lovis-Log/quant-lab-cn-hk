"""Every research workspace renders from one validated history bundle."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from quant_lab.data import HistoryBundle
from quant_lab.storage import list_experiments


def sample_bundle() -> HistoryBundle:
    dates = pd.date_range("2026-01-02", periods=100, freq="B")
    close = 100 + np.arange(100) * 0.2 + np.sin(np.arange(100))
    history = pd.DataFrame(
        {"date": dates, "open": close - 0.5, "high": close + 1,
         "low": close - 1, "close": close,
         "volume": np.full(100, 100_000), "amount": close * 100_000}
    )
    return HistoryBundle(history, "A 股", "600519", "腾讯证券 · AKShare", "CNY", "")


def test_all_workspaces_boot_without_extra_network_calls() -> None:
    bundle = sample_bundle()
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    with patch("quant_lab.ui.fetch_history", return_value=bundle):
        app = AppTest.from_file(entrypoint, default_timeout=30).run()
        app.sidebar.button[0].click().run()
        assert not app.exception
        for page in ("策略实验室", "历史回测", "风险与组合", "统计与机器学习"):
            app.sidebar.radio[0].set_value(page).run()
            assert not app.exception, page
        next(item for item in app.get("button") if item.label == "DeepSeek 助手").click().run()
        assert not app.exception


def test_research_actions_run_from_loaded_history() -> None:
    bundle = sample_bundle()
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    with patch("quant_lab.ui.fetch_history", return_value=bundle), patch(
        "quant_lab.ui_analysis.fetch_history", return_value=bundle
    ):
        app = AppTest.from_file(entrypoint, default_timeout=30).run()
        app.sidebar.button[0].click().run()
        for page, button_label in (
            ("历史回测", "运行历史回测"),
            ("风险与组合", "分析同市场组合"),
            ("统计与机器学习", "运行时间序列线性回归"),
        ):
            app.sidebar.radio[0].set_value(page).run()
            button = next(item for item in app.get("button") if item.label == button_label)
            button.click().run()
            assert not app.exception, page
            assert not app.get("error"), page
        next(item for item in app.get("button") if item.label == "DeepSeek 助手").click().run()
        next(item for item in app.get("radio") if item.label == "AI 工作区").set_value("研究实验").run()
        next(item for item in app.get("button") if item.label == "运行受控实验（内置策略）").click().run()
        assert not app.exception
        assert not app.get("error")


def test_backtest_can_be_saved_and_opened_as_research_note(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    bundle = sample_bundle()
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    with patch("quant_lab.ui.fetch_history", return_value=bundle):
        app = AppTest.from_file(entrypoint, default_timeout=30).run()
        app.sidebar.button[0].click().run()
        app.sidebar.radio[0].set_value("历史回测").run()
        next(item for item in app.get("button") if item.label == "运行历史回测").click().run()
        next(item for item in app.get("button") if item.label == "保存实验").click().run()
        assert not app.exception
        assert len(list_experiments(tmp_path / "research.sqlite3")) == 1
        next(item for item in app.get("button") if item.label == "研究笔记").click().run()
        assert not app.exception
        assert any(item.label == "选择内容" for item in app.selectbox)
