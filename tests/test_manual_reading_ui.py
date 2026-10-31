"""The complete manual UI is offline, searchable, and replaces beginner guidance."""

from pathlib import Path

from streamlit.testing.v1 import AppTest
from conftest import navigate

from quant_lab.manual_content import ContentValidationError


ENTRYPOINT = Path(__file__).resolve().parents[1] / "app.py"


def _widget(app, kind, label):
    return next(item for item in app.get(kind) if item.label == label)


def _start_app():
    return AppTest.from_file(ENTRYPOINT, default_timeout=30).run()


def _visible_text(app) -> str:
    values = []
    for kind in (
        "caption", "info", "success", "warning", "error", "header", "subheader", "markdown"
    ):
        values.extend(str(item.value) for item in app.get(kind))
    return "\n".join(values)


def _open_manual(app):
    if not app.session_state.get("manual_panel_open", False):
        _widget(app, "button", "使用手册").click().run()
    return app


def test_manual_replaces_beginner_guidance_and_is_offline(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("手册阅读不得访问网络或模型 API")

    monkeypatch.setattr("quant_lab.ui.fetch_history", no_network)
    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", no_network)
    app = _start_app()

    assert app.session_state["manual_panel_open"] is False
    assert not [button for button in app.button if button.label == "新手使用指引"]
    assert not [button for button in app.button if button.label == "查看本页使用指南"]
    assert not [button for button in app.button if button.label in {"开始入门任务", "跳过首次引导"}]
    _open_manual(app)
    assert not app.exception
    assert app.selectbox(key="manual_section").options == ["快速开始", "功能说明", "专业知识库"]
    assert "离线使用手册 · 阅读和搜索不会调用 AI" in _visible_text(app)
    assert "快速开始：从资料库到第一份可复现实验" in _visible_text(app)


def test_detailed_explanation_setting_uses_product_label_only():
    app = _start_app()
    assert [item for item in app.expander if item.label.startswith("知识解释：")]
    _widget(app, "button", "⚙").click().run()

    setting = app.toggle(key="learning_mode")
    assert setting.label == "显示详细解释提示"
    refresh = app.button(key="learning_mode_refresh")
    assert refresh.label == "刷新整页"
    assert "不会重新请求行情或调用 AI" in refresh.help
    assert not [toggle for toggle in app.toggle if "新手模式" in toggle.label]
    setting.set_value(False).run()
    assert not app.exception
    assert app.session_state["learning_mode"] is False
    assert app.session_state["settings_open"] is True
    assert not [item for item in app.expander if item.label.startswith("知识解释：")]
    app.button(key="settings_close").click().run()
    assert app.session_state["settings_open"] is False
    assert app.session_state["learning_mode"] is False
    assert not [item for item in app.expander if item.label.startswith("知识解释：")]
    app.button(key="settings_toggle").click().run()
    assert app.session_state["settings_open"] is True
    assert app.toggle(key="learning_mode").value is False
    assert not [item for item in app.expander if item.label.startswith("知识解释：")]
    app.toggle(key="learning_mode").set_value(True).run()
    assert [item for item in app.expander if item.label.startswith("知识解释：")]


def test_function_directory_opens_all_registered_manuals_and_returns():
    app = _open_manual(_start_app())
    app.selectbox(key="manual_section").set_value("功能说明").run()

    directory_buttons = [
        button for button in app.button if button.key and button.key.startswith("manual_index_")
    ]
    assert len(directory_buttons) == 9
    _widget(app, "button", "市场数据：代码、名称、区间、复权、来源与缓存").click().run()
    assert "使用手册 / 功能说明 / 市场数据" in _visible_text(app)
    assert "加载真实历史日线" in _visible_text(app)
    back = app.button(key="manual_toolbar_back")
    assert back.label == "← 返回" and back.help == "返回功能目录"
    back.click().run()
    assert len([button for button in app.button if button.key and button.key.startswith("manual_index_")]) == 9


def test_professional_categories_article_status_and_relationship_navigation():
    app = _open_manual(_start_app())
    app.selectbox(key="manual_section").set_value("专业知识库").run()
    category = app.selectbox(key="manual_category")
    assert len(category.options) == 8
    assert "市场与数据 · 10 篇" in _visible_text(app)

    _widget(app, "button", "开高低收与成交量 / OHLCV").click().run()
    text = _visible_text(app)
    assert "使用手册 / 专业知识库 / 市场与数据 / 开高低收与成交量" in text
    assert "软件状态：软件已实现" in text
    assert "#### 前置概念" in text
    assert "#### 相关词条" in text
    assert "#### 建议下一篇" in text
    _widget(app, "button", "证券身份与代码规范化 / Instrument Identity and Symbol Normalization").click().run()
    assert "证券身份" in _visible_text(app)
    back = app.button(key="manual_toolbar_back")
    assert back.label == "← 返回" and back.help == "返回上一词条"
    back.click().run()
    assert app.session_state["manual_article_id"] == "ohlcv"
    app.button(key="manual_toolbar_back").click().run()
    assert app.selectbox(key="manual_category")


def test_local_search_covers_english_alias_body_and_empty_state():
    app = _open_manual(_start_app())
    search = _widget(app, "text_input", "搜索手册与专业知识")

    search.input("Next-Open Execution").run()
    assert _widget(app, "button", "下一交易日开盘成交 / Next-Open Execution")
    app.button(key="manual_toolbar_back").click().run()

    _widget(app, "text_input", "搜索手册与专业知识").input("价量数据").run()
    _widget(app, "button", "开高低收与成交量 / OHLCV").click().run()
    assert "软件状态：软件已实现" in _visible_text(app)

    _widget(app, "text_input", "搜索手册与专业知识").input("绝对不存在的检索词xyz").run()
    assert "没有找到匹配内容" in _visible_text(app)


def test_search_shows_twelve_ranked_cards_then_expands():
    app = _open_manual(_start_app())
    _widget(app, "text_input", "搜索手册与专业知识").input("复权").run()

    result_buttons = [
        button for button in app.button
        if button.key and button.key.startswith(("manual_search_page_", "manual_search_article_"))
    ]
    assert len(result_buttons) == 12
    assert result_buttons[0].label == "价格复权 / Price Adjustment"
    assert "最相关" in _visible_text(app)
    _widget(app, "button", next(button.label for button in app.button if button.key == "manual_search_more")).click().run()
    expanded = [
        button for button in app.button
        if button.key and button.key.startswith(("manual_search_page_", "manual_search_article_"))
    ]
    assert len(expanded) > 12


def test_search_result_back_restores_results_then_origin():
    app = _open_manual(_start_app())
    _widget(app, "text_input", "搜索手册与专业知识").input("OHLCV").run()
    _widget(app, "button", "开高低收与成交量 / OHLCV").click().run()

    back = app.button(key="manual_toolbar_back")
    assert back.label == "← 返回" and back.help == "返回搜索结果"
    back.click().run()
    assert _widget(app, "text_input", "搜索手册与专业知识").value == "OHLCV"
    app.button(key="manual_toolbar_back").click().run()
    assert _widget(app, "text_input", "搜索手册与专业知识").value == ""
    assert "快速开始：从资料库到第一份可复现实验" in _visible_text(app)


def test_manual_related_term_opens_article_directly():
    app = _open_manual(_start_app())
    _widget(
        app, "button",
        "证券身份与代码规范化 / Instrument Identity and Symbol Normalization",
    ).click().run()

    assert app.session_state["manual_article_id"] == "instrument_identity"
    assert "使用手册 / 专业知识库 / 市场与数据 / 证券身份与代码规范化" in _visible_text(app)


def test_related_term_back_restores_manual_then_its_original_catalog():
    app = _open_manual(_start_app())
    app.selectbox(key="manual_section").set_value("功能说明").run()
    app.button(key="manual_index_statistics_ml").click().run()
    original = app.session_state["manual_page_id"]
    related = next(button for button in app.button if button.key and button.key.startswith("manual_term_statistics_ml_"))
    related.click().run()
    assert app.session_state["manual_article_id"]
    app.button(key="manual_toolbar_back").click().run()
    assert app.session_state["manual_section"] == "功能说明"
    assert app.session_state["manual_page_id"] == original
    app.button(key="manual_toolbar_back").click().run()
    assert not app.session_state.get("manual_page_id")
    assert len([button for button in app.button if button.key and button.key.startswith("manual_index_")]) == 9


def test_all_four_software_statuses_render_accurately():
    app = _open_manual(_start_app())
    cases = (
        ("log_return", "理论扩展 · 当前软件未实现"),
        ("overfitting", "仅 Quant Academy 固定样本演示"),
        ("trading_calendar", "需结合代码边界阅读"),
    )
    for article_id, status in cases:
        app.session_state["manual_section"] = "专业知识库"
        app.session_state["manual_article_id"] = article_id
        app.session_state["manual_search_query"] = ""
        app.run()
        assert f"软件状态：{status}" in _visible_text(app)


def test_long_engineering_article_renders_markdown_code_blocks():
    app = _open_manual(_start_app())
    app.session_state["manual_section"] = "专业知识库"
    app.session_state["manual_article_id"] = "python_functions"
    app.session_state["manual_search_query"] = ""
    app.run()

    text = _visible_text(app)
    assert "Python 函数" in text
    assert "```python" in text


def test_manual_deepseek_and_notes_panels_coexist_and_maximize():
    app = _open_manual(_start_app())
    _widget(app, "button", "DeepSeek 助手").click().run()
    _widget(app, "button", "研究笔记").click().run()

    assert not app.exception
    assert app.session_state["manual_panel_open"] is True
    assert app.session_state["deepseek_panel_open"] is True
    assert app.session_state["notes_panel_open"] is True
    app.button(key="manual_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] == "manual"
    assert not [button for button in app.button if button.key == "deepseek_panel_maximize"]
    app.button(key="manual_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] is None


def test_academy_and_knowledge_links_open_manual_not_guidance():
    app = _start_app()
    navigate(app, "Quant Academy")
    _widget(app, "button", "在使用手册中继续阅读").click().run()

    assert app.session_state["manual_panel_open"] is True
    assert app.session_state["manual_article_id"] == "simple_return"
    assert "简单收益率" in _visible_text(app)
    assert not [button for button in app.button if button.label == "新手使用指引"]


def test_manual_shows_content_validation_failure(monkeypatch):
    monkeypatch.setattr(
        "quant_lab.ui_manual._manual_library",
        lambda: (_ for _ in ()).throw(ContentValidationError("测试资源缺失")),
    )
    app = _open_manual(_start_app())

    assert not app.exception
    assert "使用手册内容不可用：测试资源缺失" in _visible_text(app)
    assert "不会用演示文本替代缺失内容" in _visible_text(app)
