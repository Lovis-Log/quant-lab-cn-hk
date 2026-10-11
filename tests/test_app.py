"""Verify the first milestone boots and keeps simulated content clearly labeled."""

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from quant_lab.data import DataUnavailableError


def test_terminal_boots_with_clear_data_status() -> None:
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()

    assert not app.exception
    assert app.sidebar.radio[0].value == "市场数据"
    assert len(app.get("plotly_chart")) == 2
    assert any("固定随机种子" in item.value for item in app.get("caption"))
    assert any("腾讯证券" in item.value and "不复权" in item.value for item in app.get("caption"))

    app.sidebar.selectbox[0].select("港股").run()
    assert not app.exception
    assert any("港股" in item.value and "00700" in item.value for item in app.get("html"))


def test_loaded_history_replaces_demo_metrics(monkeypatch) -> None:
    history = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-08", "2026-10-09"]),
            "open": [9.5, 10.5], "high": [10.5, 12.0],
            "low": [9.0, 10.0], "close": [10.0, 11.0],
            "volume": [1000, 2000], "amount": [10000, 22000],
        }
    )
    monkeypatch.setattr("quant_lab.ui.fetch_a_share_daily", lambda *_: history)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert any("+10.00%" in item.value for item in app.get("html"))
    assert any("已加载真实历史数据" in item.value for item in app.get("html"))
    assert any("来源：腾讯证券" in item.value for item in app.get("caption"))
    assert len(app.get("plotly_chart")) == 2

    app.sidebar.text_input[0].input("000001").run()
    assert not app.exception
    assert not any("+10.00%" in item.value for item in app.get("html"))


def test_provider_error_keeps_metrics_empty(monkeypatch) -> None:
    def unavailable(*_: object) -> pd.DataFrame:
        raise DataUnavailableError("历史行情暂时无法获取")

    monkeypatch.setattr("quant_lab.ui.fetch_a_share_daily", unavailable)
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert any("暂时无法获取" in item.value for item in app.get("error"))
    assert any("区间简单价格收益率" in item.value and "--" in item.value
               for item in app.get("html"))
