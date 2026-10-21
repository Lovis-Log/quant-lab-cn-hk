"""Model switching and UI redraws cannot silently repeat paid completions."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from quant_lab.deepseek import Answer
from quant_lab import storage


def widget(app, kind, label):
    return next(w for w in app.get(kind) if w.label == label)


def test_remembered_key_is_loaded_on_start_and_panel_is_global(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("quant_lab.credentials.load_key", lambda: "sk-restored-from-vault")
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    assert widget(app, "button", "DeepSeek 助手")
    widget(app, "button", "DeepSeek 助手").click().run()
    assert not app.exception
    assert not any(item.label == "DeepSeek API Key" for item in app.text_input)
    widget(app, "button", "⚙").click().run()
    assert widget(app, "text_input", "DeepSeek API Key").value == "sk-restored-from-vault"
    assert widget(app, "checkbox", "记住密钥（Windows 凭据管理器）").value is True
    assert app.session_state["deepseek_panel_open"] is True
    app.button(key="settings_close").click().run()
    app.button(key="deepseek_panel_close").click().run()
    assert app.session_state["deepseek_panel_open"] is False


def test_topbar_panels_open_together_without_swap_button(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    navigation = app.sidebar.radio(key="nav_page")
    assert "AI 研究助手" not in navigation.options
    assert "新手使用指引" not in navigation.options
    assert "研究笔记" not in navigation.options
    widget(app, "button", "新手使用指引").click().run()
    widget(app, "button", "DeepSeek 助手").click().run()
    widget(app, "button", "研究笔记").click().run()
    assert app.session_state["guide_panel_open"] is True
    assert app.session_state["deepseek_panel_open"] is True
    assert app.session_state["notes_panel_open"] is True
    assert not app.exception
    assert not any(button.label == "左右调换" for button in app.button)
    app.button(key="notes_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] == "notes"
    app.button(key="notes_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] is None


def test_models_sending_redraw_context_and_saved_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    calls = []
    class Client:
        def __init__(self, key):
            self.key = key
        def list_models(self):
            return [{"id":"alpha"}, {"id":"beta"}]
        def stream(self, model, prompt, history, context, **kwargs):
            calls.append({"model":model,"history":history,"context":context})
            answer = Answer(model + "-actual")
            def chunks():
                answer.text = "程序事实与模型解释应区分。"
                yield answer.text
                answer.complete = True
            return answer, chunks()
    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", Client)
    monkeypatch.setattr("quant_lab.credentials.clear_key", lambda: None)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    assert not any(w.label == "DeepSeek API Key" for w in app.text_input)
    assert "AI 研究助手" not in app.sidebar.radio(key="nav_page").options
    widget(app,"button","DeepSeek 助手").click().run()
    widget(app,"radio","AI 工作区").set_value("对话与辅导").run()
    widget(app,"button","⚙").click().run()
    widget(app,"text_input","DeepSeek API Key").input("sk-only-ui-mock-secret").run()
    widget(app,"button","测试连接").click().run()
    app.button(key="settings_close").click().run()
    widget(app,"text_area","问题（确认后发送）").input("解释当前指标").run()
    assert calls == []
    widget(app,"button","发送到 DeepSeek").click().run()
    assert not app.exception and len(calls) == 1 and calls[0]["model"] == "alpha"
    app.run()
    app.sidebar.radio[0].set_value("Quant Academy").run()
    assert len(calls) == 1
    widget(app,"button","向 AI 追问").click().run()
    assert app.session_state["deepseek_api_key"] == "sk-only-ui-mock-secret"
    widget(app,"button","⚙").click().run()
    widget(app,"selectbox","DeepSeek 模型").set_value("beta").run()
    app.button(key="settings_close").click().run()
    widget(app,"button","发送到 DeepSeek").click().run()
    assert not app.exception and len(calls) == 2 and calls[-1]["model"] == "beta"
    assert calls[-1]["history"] == []  # New lesson context, old stock messages retained only for display.
    assert "notes" not in calls[-1]["context"]
    widget(app,"selectbox","选择回答保存为学习笔记").set_value(1).run()
    widget(app,"button","保存选定回答到学习笔记").click().run()
    assert storage.list_learning_notes(tmp_path / "research.sqlite3")[0]["model"] == "beta-actual"
    assert "sk-only-ui-mock-secret" not in (tmp_path / "research.sqlite3").read_bytes().decode("utf-8", errors="ignore")
    widget(app,"button","⚙").click().run()
    widget(app,"button","清除密钥").click().run()
    assert widget(app,"text_input","DeepSeek API Key").value == ""
    assert len(calls) == 2


def test_knowledge_followup_only_creates_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    class NeverCalled:
        def __init__(self, *args):
            raise AssertionError("API client created without user send")
    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", NeverCalled)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    widget(app,"button","向 AI 追问").click().run()
    assert not app.exception
    assert "简单收益率" in widget(app,"text_area","问题（确认后发送）").value


def test_history_manual_failure_keeps_previous_data(tmp_path, monkeypatch):
    from test_workspaces import sample_bundle
    from dataclasses import replace
    from datetime import datetime, timezone, timedelta
    from quant_lab.data import DataUnavailableError
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    calls = []
    first = replace(sample_bundle(), received_at=datetime.now(timezone.utc)-timedelta(minutes=5))
    def fetch(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 3:
            raise DataUnavailableError("upstream failure")
        return first
    monkeypatch.setattr("quant_lab.ui.fetch_history", fetch)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    app.sidebar.button[0].click().run()
    widget(app,"button","立即更新历史日线").click().run()
    assert calls[-1] == {"force": True}
    app.session_state["history_manual_at"] = float('-inf')
    app.run()
    widget(app,"button","立即更新历史日线").click().run()
    assert not app.exception
    retained = app.session_state["loaded_bundle"]
    assert retained.received_at == first.received_at and retained.frame.equals(first.frame)
    assert retained.update_error and retained.update_result == "请求失败"
