"""New learning and research pages boot without fetching market data."""

from pathlib import Path

from streamlit.testing.v1 import AppTest
from conftest import navigate


def test_academy_and_empty_notes_render(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    navigate(app, "Quant Academy")
    app.selectbox(key="academy_course_id").set_value("simple_return").run()
    # AppTest doesn't expose a setter for expander state; the desktop harness
    # checks real disclosure clicks. Seed the same public session-state input.
    app.session_state["knowledge_lazy_academy_simple_return"] = True
    app.run()
    assert not app.exception
    assert any("Quant Academy" in item.value for item in app.get("subheader"))
    assert any("10→11" in item.value for item in app.get("markdown"))
    assert any("刻画什么" in item.value for item in app.get("markdown"))
    assert any("局限和常见误读" in item.value for item in app.get("markdown"))
    app.selectbox(key="academy_course_id").set_value("bias").run()
    app.session_state["knowledge_lazy_academy_bias"] = True
    app.run()
    academy_text = "\n".join(str(item.value) for item in app.get("markdown"))
    assert "本课没有单一的‘偏差值’" in academy_text
    assert "当前没有足够的有效计算值" not in academy_text
    app.text_input(key="academy_search").set_value("回撤").run()
    assert app.session_state["academy_course_id"] == "drawdown"
    app.text_input(key="academy_search").set_value("").run()
    app.button(key="academy_next").click().run()
    assert app.session_state["academy_course_id"] == "sharpe"
    app.button(key="academy_previous").click().run()
    assert app.session_state["academy_course_id"] == "drawdown"
    assert not app.exception
    assert not [button for button in app.button if button.label in {"保存交互实验记录", "提交课程测验"}]
    next(item for item in app.get("button") if item.label == "研究笔记").click().run()
    assert not app.exception
    assert app.text_input(key="note_editor_title")
    assert app.button(key="notes_panel_history")


def test_all_28_courses_render_offline_with_current_ai_context(monkeypatch):
    from quant_lab.courses import COURSES
    import requests
    monkeypatch.setattr(requests.sessions.Session, "request",
                        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("Academy must be offline")))
    app = AppTest.from_string("from quant_lab.ui_learning import render_academy\nrender_academy()", default_timeout=15).run()
    assert app.session_state["academy_course_id"] == "financial_variables"
    assert app.button(key="academy_previous").disabled
    for course in COURSES:
        app.selectbox(key="academy_course_id").set_value(course.course_id).run()
        assert not app.exception, course.course_id
        assert len(app.get("plotly_chart")) == 1
        assert app.session_state["_current_ai_context"]["learning_context"]["course_id"] == course.course_id
        assert app.session_state["active_learning_context"]["parameter"] == course.parameter.default
        assert not app.error
    assert app.button(key="academy_next").disabled
    app.session_state["ai_followup_context"] = dict(app.session_state["_current_ai_context"])
    app.slider(key="academy_parameter_research_archive").set_value(25).run()
    assert app.session_state["_current_ai_context"]["learning_context"]["parameter"] == 25
    assert "ai_followup_context" not in app.session_state
    app.button(key="academy_prerequisite_hypothesis_quality").click().run()
    assert app.session_state["academy_course_id"] == "hypothesis_quality"
    app.radio(key="academy_group").set_value("风险与统计").run()
    assert len(app.selectbox(key="academy_course_id").options) == 4
    app.text_input(key="academy_search").set_value("没有这个课程xyz").run()
    assert app.session_state["active_learning_context"] is None
    assert "learning_context" not in app.session_state["_current_ai_context"]
    app.text_input(key="academy_search").set_value("").run()
    assert not app.exception


def test_original_numeric_selection_and_parameter_migrate_by_identity():
    app = AppTest.from_string("from quant_lab.ui_learning import render_academy\nrender_academy()")
    app.session_state["academy_lesson"] = 6
    app.session_state["academy_parameter_6"] = 7
    app.session_state["academy_group"] = "收益与数据"  # Original category name.
    app.run()
    assert not app.exception
    assert app.session_state["academy_course_id"] == "correlation"
    assert app.slider(key="academy_parameter_correlation").value == 7
    assert app.session_state["academy_lesson"] == 6  # Old index is never rewritten.


def test_prerequisite_return_restores_chained_course_filters_and_parameter():
    app = AppTest.from_string("from quant_lab.ui_learning import render_academy\nrender_academy()")
    app.session_state["academy_group"] = "风险与统计"
    app.session_state["academy_search"] = "方差"
    app.session_state["academy_course_id"] = "variance"
    app.run()
    app.slider(key="academy_parameter_variance").set_value(5).run()
    app.button(key="academy_prerequisite_simple_return").click().run()
    assert app.session_state["academy_course_id"] == "simple_return"
    assert "09 · 方差与标准差" in app.button(key="academy_return").label
    app.button(key="academy_prerequisite_financial_variables").click().run()
    assert app.session_state["academy_course_id"] == "financial_variables"
    assert "05 · 简单收益率与复利" in app.button(key="academy_return").label
    app.button(key="academy_return").click().run()
    assert app.session_state["academy_course_id"] == "simple_return"
    app.button(key="academy_return").click().run()
    assert not app.exception
    assert app.session_state["academy_course_id"] == "variance"
    assert app.text_input(key="academy_search").value == "方差"
    assert app.radio(key="academy_group").value == "风险与统计"
    assert app.slider(key="academy_parameter_variance").value == 5
    assert app.session_state["active_learning_context"]["parameter"] == 5
    assert not any(button.key == "academy_return" for button in app.button)
    app.button(key="academy_prerequisite_simple_return").click().run()
    app.selectbox(key="academy_course_id").set_value("drawdown").run()
    assert not app.session_state.get("_academy_return_stack")
