"""Every research workspace renders from one validated history bundle."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from quant_lab.data import HistoryBundle
from quant_lab.storage import list_experiments
from conftest import finish_background_jobs
from dataclasses import replace
from quant_lab.source_rights import TEACHING_RETENTION


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
        finish_background_jobs(app)
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
        finish_background_jobs(app)
        for page, button_label in (
            ("历史回测", "运行历史回测"),
            ("风险与组合", "分析同市场组合"),
            ("统计与机器学习", "运行时间序列线性回归"),
        ):
            app.sidebar.radio[0].set_value(page).run()
            button = next(item for item in app.get("button") if item.label == button_label)
            button.click().run()
            finish_background_jobs(app)
            assert not app.exception, page
            assert not app.get("error"), page
            result_key = {"历史回测": "backtest_result", "风险与组合": "portfolio_result",
                          "统计与机器学习": "model_result"}[page]
            assert app.session_state[result_key] is not None
        next(item for item in app.get("button") if item.label == "DeepSeek 助手").click().run()
        next(item for item in app.get("button") if item.label == "研究实验").click().run()
        next(item for item in app.get("button") if item.label == "运行受控实验（内置策略）").click().run()
        assert not app.exception
        assert not app.get("error")


def test_backtest_can_be_saved_and_opened_as_research_note(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    bundle = replace(sample_bundle(), source="平台生成的教学样本", retention=TEACHING_RETENTION)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    with patch("quant_lab.ui.fetch_history", return_value=bundle):
        app = AppTest.from_file(entrypoint, default_timeout=30).run()
        app.sidebar.button[0].click().run()
        finish_background_jobs(app)
        app.sidebar.radio[0].set_value("历史回测").run()
        next(item for item in app.get("button") if item.label == "运行历史回测").click().run()
        finish_background_jobs(app)
        next(item for item in app.get("button") if item.label == "保存实验").click().run()
        assert not app.exception
        assert len(list_experiments(tmp_path / "research.sqlite3")) == 1
        next(item for item in app.get("button") if item.label == "研究笔记").click().run()
        assert not app.exception
        app.button(key="notes_open_management").click().run()
        app.button(key="notes_manage_experiments").click().run()
        assert any(item.label == "选择实验" for item in app.selectbox)
        assert any("从存档数据重新计算" == item.label for item in app.button)


def test_unverified_source_cannot_create_new_archive():
    bundle = sample_bundle()
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    with patch("quant_lab.ui.fetch_history", return_value=bundle):
        app = AppTest.from_file(entrypoint, default_timeout=30).run()
        app.sidebar.button[0].click().run()
        finish_background_jobs(app)
        app.sidebar.radio[0].set_value("历史回测").run()
        app.button(key="FormSubmitter:backtest_parameters-运行历史回测").click().run()
        finish_background_jobs(app)
        assert app.button(key="save_experiment").disabled
        assert any("本地留存许可未核实" in caption.value for caption in app.caption)
        assert not list_experiments()


def test_backtest_knowledge_group_expands_collapses_and_resets(monkeypatch) -> None:
    bundle = sample_bundle()
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    with patch("quant_lab.ui.fetch_history", return_value=bundle):
        app = AppTest.from_file(entrypoint, default_timeout=30).run()
        app.sidebar.button[0].click().run()
        finish_background_jobs(app)
        app.sidebar.radio(key="nav_page").set_value("历史回测").run()
        next(item for item in app.button if item.label == "运行历史回测").click().run()
        finish_background_jobs(app)

        explanations = [item for item in app.expander if item.label.startswith("知识解释：")]
        assert len(explanations) == 2
        next(item for item in app.button if item.label == "显示更多（剩余 6 项）").click().run()
        explanations = [item for item in app.expander if item.label.startswith("知识解释：")]
        assert len(explanations) == 8
        next(item for item in app.button if item.label == "收起详细解释").click().run()
        assert len([item for item in app.expander if item.label.startswith("知识解释：")]) == 2

        next(item for item in app.button if item.label == "显示更多（剩余 6 项）").click().run()
        app.button(key="settings_toggle").click().run()
        app.toggle(key="learning_mode").set_value(False).run()
        assert not [item for item in app.expander if item.label.startswith("知识解释：")]
        app.toggle(key="learning_mode").set_value(True).run()
        assert len([item for item in app.expander if item.label.startswith("知识解释：")]) == 2
        next(item for item in app.button if item.label == "显示更多（剩余 6 项）").click().run()
        assert len([item for item in app.expander if item.label.startswith("知识解释：")]) == 8
        app.button(key="learning_mode_refresh").click().run()
        assert app.session_state["settings_open"] is True
        assert "learning_mode_app_rerun_pending" not in app.session_state
        assert len([item for item in app.expander if item.label.startswith("知识解释：")]) == 2
