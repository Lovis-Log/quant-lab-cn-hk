"""Every research workspace renders from one validated history bundle."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from quant_lab.data import HistoryBundle


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
        for page in ("策略实验室", "历史回测", "风险与组合", "统计与机器学习", "AI 研究助手"):
            app.sidebar.radio[0].set_value(page).run()
            assert not app.exception, page


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
            ("AI 研究助手", "运行受控实验（内置策略）"),
        ):
            app.sidebar.radio[0].set_value(page).run()
            button = next(item for item in app.get("button") if item.label == button_label)
            button.click().run()
            assert not app.exception, page
            assert not app.get("error"), page
