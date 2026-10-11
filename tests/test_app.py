"""Verify the first milestone boots and keeps simulated content clearly labeled."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_terminal_boots_with_clear_data_status() -> None:
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()

    assert not app.exception
    assert app.sidebar.radio[0].value == "市场数据"
    assert len(app.get("plotly_chart")) == 2
    assert any("固定随机种子" in item.value for item in app.get("caption"))
    assert any("尚未连接行情接口" in item.value for item in app.get("caption"))

    app.sidebar.selectbox[0].select("港股").run()
    assert not app.exception
    assert any("港股" in item.value and "00700" in item.value for item in app.get("html"))
