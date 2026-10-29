"""New learning and research pages boot without fetching market data."""

from pathlib import Path

from streamlit.testing.v1 import AppTest
from conftest import navigate


def test_academy_and_empty_notes_render(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    navigate(app, "Quant Academy")
    # AppTest doesn't expose a setter for expander state; the desktop harness
    # checks real disclosure clicks. Seed the same public session-state input.
    app.session_state["knowledge_lazy_academy_simple_return"] = True
    app.run()
    assert not app.exception
    assert any("Quant Academy" in item.value for item in app.get("subheader"))
    assert any("10→11" in item.value for item in app.get("markdown"))
    assert any("刻画什么" in item.value for item in app.get("markdown"))
    assert any("局限和常见误读" in item.value for item in app.get("markdown"))
    for lesson in range(8):
        next(item for item in app.get("selectbox") if item.label == "选择课程").set_value(lesson).run()
        assert not app.exception, lesson
    app.session_state["knowledge_lazy_academy_bias"] = True
    app.run()
    academy_text = "\n".join(str(item.value) for item in app.get("markdown"))
    assert "本课没有单一的‘偏差值’" in academy_text
    assert "当前没有足够的有效计算值" not in academy_text
    app.text_input(key="academy_search").set_value("回撤").run()
    assert app.session_state["academy_lesson"] == 4
    app.text_input(key="academy_search").set_value("").run()
    app.button(key="academy_next").click().run()
    assert app.session_state["academy_lesson"] == 5
    app.button(key="academy_previous").click().run()
    assert app.session_state["academy_lesson"] == 4
    assert not app.exception
    assert not [button for button in app.button if button.label in {"保存交互实验记录", "提交课程测验"}]
    next(item for item in app.get("button") if item.label == "研究笔记").click().run()
    assert not app.exception
    assert app.text_input(key="note_editor_title")
    assert app.button(key="notes_panel_history")
