"""The manual product boots and remains useful without upstream network access."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


ENTRYPOINT = Path(__file__).resolve().parents[1] / "app.py"


def test_offline_startup_opens_manual_and_academy(monkeypatch, tmp_path):
    def blocked(*args, **kwargs):
        raise AssertionError("启动和离线阅读不得访问上游网络")

    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path / "isolated-user-data"))
    monkeypatch.setenv("QUANT_LAB_CREDENTIAL_TARGET", "QuantLabCNHK/Stage5OfflineTest")
    monkeypatch.setattr("requests.sessions.Session.request", blocked)
    monkeypatch.setattr("socket.create_connection", blocked)

    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()

    assert not app.exception
    assert app.session_state["manual_panel_open"] is True
    assert app.radio(key="manual_section").options == ["快速开始", "功能说明", "专业知识库"]
    assert any("快速开始：从资料库到第一份可复现实验" in item.value for item in app.subheader)

    app.sidebar.radio(key="nav_page").set_value("Quant Academy").run()
    assert not app.exception
    assert any("Quant Academy" in item.value for item in app.subheader)
