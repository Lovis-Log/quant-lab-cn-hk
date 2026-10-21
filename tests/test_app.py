"""Verify the first milestone boots and keeps simulated content clearly labeled."""

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from quant_lab.data import DataUnavailableError, HistoryBundle


def test_terminal_boots_with_clear_data_status() -> None:
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()

    assert not app.exception
    assert app.sidebar.radio[0].value == "市场数据"
    assert len(app.get("plotly_chart")) == 2
    assert any("固定随机种子" in item.value for item in app.get("caption"))
    assert next(w for w in app.sidebar.selectbox if w.label == "价格口径").value == "不复权"
    assert any("腾讯证券" in item.value for item in app.get("caption"))

    app.sidebar.selectbox[0].select("港股").run()
    assert not app.exception
    assert any("港股" in item.value and "00700" in item.value for item in app.get("html"))
    app.sidebar.radio[0].set_value("策略实验室").run()
    assert not app.exception


def test_loaded_history_replaces_demo_metrics(monkeypatch) -> None:
    history = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-08", "2026-10-09"]),
            "open": [9.5, 10.5], "high": [10.5, 12.0],
            "low": [9.0, 10.0], "close": [10.0, 11.0],
            "volume": [1000, 2000], "amount": [10000, 22000],
        }
    )
    bundle = HistoryBundle(history, "A 股", "600519", "腾讯证券 · AKShare", "CNY", "")
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *_: bundle)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert any("+10.00%" in item.value for item in app.get("html"))
    assert any("已加载真实历史数据" in item.value for item in app.get("html"))
    assert any("来源：腾讯证券" in item.value for item in app.get("caption"))
    assert len(app.get("plotly_chart")) == 2

    app.sidebar.selectbox(key="symbol_A 股").set_value("000001").run()
    assert not app.exception
    assert not any("+10.00%" in item.value for item in app.get("html"))


def test_provider_error_keeps_metrics_empty(monkeypatch) -> None:
    def unavailable(*_: object) -> pd.DataFrame:
        raise DataUnavailableError("历史行情暂时无法获取")

    monkeypatch.setattr("quant_lab.ui.fetch_history", unavailable)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert any("暂时无法获取" in item.value for item in app.get("error"))
    assert any("区间简单价格收益率" in item.value and "--" in item.value
               for item in app.get("html"))


def test_simulated_history_is_never_labeled_real(monkeypatch) -> None:
    history = pd.DataFrame(
        {"date": pd.to_datetime(["2026-10-08", "2026-10-09"]),
         "open": [9.5, 10.5], "high": [10.5, 12.0], "low": [9.0, 10.0],
         "close": [10.0, 11.0], "volume": [1000, 2000], "amount": [10000, 22000]}
    )
    bundle = HistoryBundle(history, "A 股", "600519", "明确模拟教学数据", "CNY", "")
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *_: bundle)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert any("已加载模拟/教学数据" in item.value for item in app.get("html"))
    assert not any("已加载真实历史数据" in item.value for item in app.get("html"))
    assert any("不是上游真实行情" in item.value for item in app.get("caption"))


def test_hk_history_uses_hkd_and_its_own_source(monkeypatch) -> None:
    history = pd.DataFrame(
        {"date": pd.to_datetime(["2026-10-08", "2026-10-09"]),
         "open": [400.0, 410.0], "high": [420.0, 430.0],
         "low": [395.0, 405.0], "close": [415.0, 425.0],
         "volume": [100000, 120000], "amount": [41500000, 51000000]}
    )
    bundle = HistoryBundle(history, "港股", "00700", "新浪财经 · AKShare", "HKD", "")
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *_: bundle)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    app.sidebar.selectbox[0].select("港股").run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert any("HK$" in item.value for item in app.get("html"))
    assert any("新浪财经" in item.value for item in app.get("html"))
