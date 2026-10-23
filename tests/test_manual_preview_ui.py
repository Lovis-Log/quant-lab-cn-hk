"""Stage-2 manual preview stays parallel to the original learning center."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from quant_lab.manual_content import ContentValidationError


ENTRYPOINT = Path(__file__).resolve().parents[1] / "app.py"


def _widget(app, kind, label):
    return next(item for item in app.get(kind) if item.label == label)


def _start_app():
    return AppTest.from_file(ENTRYPOINT, default_timeout=30).run()


def _visible_text(app) -> str:
    values = []
    for kind in ("caption", "info", "error", "header", "subheader", "markdown"):
        values.extend(str(item.value) for item in app.get(kind))
    return "\n".join(values)


def test_preview_entry_and_three_representative_pages_are_offline(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("手册预览不得访问网络或模型 API")

    monkeypatch.setattr("quant_lab.ui.fetch_history", no_network)
    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", no_network)
    app = _start_app()

    assert _widget(app, "button", "新手使用指引")
    _widget(app, "button", "使用手册（预览）").click().run()
    assert not app.exception
    assert app.session_state["manual_panel_open"] is True
    navigation = app.radio(key="manual_preview_section")
    assert navigation.options == ["快速开始", "功能说明", "专业知识库"]
    assert "快速开始：从资料库到第一份可复现实验" in _visible_text(app)
    assert "完整目录、搜索和文章跳转将在后续阶段接入" in _visible_text(app)

    navigation.set_value("功能说明").run()
    assert "市场数据：代码、名称、区间、复权、来源与缓存" in _visible_text(app)

    app.radio(key="manual_preview_section").set_value("专业知识库").run()
    text = _visible_text(app)
    assert "开高低收与成交量（OHLCV）" in text
    assert "市场与数据 · implemented" in text


def test_preview_and_original_panels_coexist_and_maximize_independently():
    app = _start_app()
    _widget(app, "button", "新手使用指引").click().run()
    _widget(app, "button", "使用手册（预览）").click().run()
    _widget(app, "button", "DeepSeek 助手").click().run()
    _widget(app, "button", "研究笔记").click().run()

    assert not app.exception
    assert app.session_state["guide_panel_open"] is True
    assert app.session_state["manual_panel_open"] is True
    assert app.session_state["deepseek_panel_open"] is True
    assert app.session_state["notes_panel_open"] is True
    assert app.button(key="guide_panel_maximize")
    assert app.button(key="manual_panel_maximize")
    assert app.button(key="deepseek_panel_maximize")
    assert app.button(key="notes_panel_maximize")

    app.button(key="manual_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] == "manual"
    assert app.button(key="manual_panel_maximize")
    assert not [button for button in app.button if button.key == "guide_panel_maximize"]
    app.button(key="manual_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] is None
    assert app.button(key="guide_panel_maximize")

    app.button(key="manual_panel_close").click().run()
    assert app.session_state["manual_panel_open"] is False
    assert app.session_state["guide_panel_open"] is True
    assert app.session_state["deepseek_panel_open"] is True
    assert app.session_state["notes_panel_open"] is True


def test_preview_shows_content_validation_failure(monkeypatch):
    monkeypatch.setattr(
        "quant_lab.ui_manual._manual_library",
        lambda: (_ for _ in ()).throw(ContentValidationError("测试资源缺失")),
    )
    app = _start_app()
    _widget(app, "button", "使用手册（预览）").click().run()

    assert not app.exception
    assert "使用手册内容不可用：测试资源缺失" in _visible_text(app)
