"""New learning and research pages boot without fetching market data."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_academy_and_empty_notes_render(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    entrypoint = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=20).run()
    app.sidebar.radio[0].set_value("Quant Academy").run()
    assert not app.exception
    assert any("Quant Academy" in item.value for item in app.get("subheader"))
    assert any("10→11" in item.value for item in app.get("markdown"))
    assert any("刻画什么" in item.value for item in app.get("markdown"))
    assert any("局限和常见误读" in item.value for item in app.get("markdown"))
    for lesson in range(8):
        next(item for item in app.get("selectbox") if item.label == "选择课程").set_value(lesson).run()
        assert not app.exception, lesson
    app.sidebar.radio[0].set_value("研究笔记").run()
    assert not app.exception
    assert any("尚无已保存实验" in item.value for item in app.get("info"))
