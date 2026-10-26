"""Model switching and UI redraws cannot silently repeat paid completions."""

from pathlib import Path

from streamlit.testing.v1 import AppTest
from conftest import finish_background_jobs

from quant_lab.deepseek import Answer
from quant_lab import ai_chat, storage


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
    assert not [button for button in app.button if button.label == "新手使用指引"]
    widget(app, "button", "DeepSeek 助手").click().run()
    widget(app, "button", "研究笔记").click().run()
    assert app.session_state["manual_panel_open"] is True
    assert app.session_state["deepseek_panel_open"] is True
    assert app.session_state["notes_panel_open"] is True
    assert not app.exception
    assert not any(button.label == "左右调换" for button in app.button)
    app.button(key="notes_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] == "notes"
    app.button(key="notes_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] is None


def test_deepseek_opens_chat_first_and_research_returns_without_model_call(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    calls = []

    class NeverCalled:
        def __init__(self, *args, **kwargs):
            calls.append("client")

    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", NeverCalled)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    widget(app, "button", "DeepSeek 助手").click().run()

    assert app.session_state["ai_workspace"] == "对话与辅导"
    assert widget(app, "text_area", "问题（确认后发送）")
    assert widget(app, "button", "研究实验")
    assert not [radio for radio in app.radio if radio.label == "AI 工作区"]
    widget(app, "button", "研究实验").click().run()
    assert app.session_state["ai_workspace"] == "研究实验"
    assert widget(app, "button", "← 返回对话")
    widget(app, "button", "← 返回对话").click().run()
    assert app.session_state["ai_workspace"] == "对话与辅导"
    assert calls == []

    app.button(key="deepseek_panel_close").click().run()
    widget(app, "button", "DeepSeek 助手").click().run()
    assert app.session_state["ai_workspace"] == "对话与辅导"


def test_left_sidebar_launcher_does_not_change_open_panels(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    widget(app, "button", "DeepSeek 助手").click().run()
    widget(app, "button", "研究笔记").click().run()
    assert app.session_state["left_sidebar_visible"] is True

    app.button(key="left_sidebar_toggle").click().run()
    assert app.session_state["left_sidebar_visible"] is False
    assert app.session_state["manual_panel_open"] is True
    assert app.session_state["deepseek_panel_open"] is True
    assert app.session_state["notes_panel_open"] is True
    assert app.button(key="deepseek_panel_maximize")
    assert app.button(key="notes_panel_maximize")

    app.button(key="left_sidebar_toggle").click().run()
    assert app.session_state["left_sidebar_visible"] is True
    assert app.button(key="deepseek_panel_maximize")
    assert app.button(key="notes_panel_maximize")

    app.button(key="notes_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] == "notes"
    app.button(key="left_sidebar_toggle").click().run()
    assert app.session_state["left_sidebar_visible"] is False
    assert app.session_state["maximized_panel"] == "notes"
    app.button(key="left_sidebar_toggle").click().run()
    assert app.session_state["left_sidebar_visible"] is True
    assert app.session_state["maximized_panel"] == "notes"
    assert not [button for button in app.button if button.key == "deepseek_panel_maximize"]
    assert app.button(key="notes_panel_maximize")


def test_models_sending_redraw_context_and_saved_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    calls = []
    class Client:
        def __init__(self, key):
            self.key = key
        def list_models(self):
            return [{"id":"alpha"}, {"id":"beta"}]
        def stream_with_recovery(self, model, prompt, history, context, **kwargs):
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
    assert app.session_state["ai_workspace"] == "对话与辅导"
    widget(app,"button","⚙").click().run()
    widget(app,"text_input","DeepSeek API Key").input("sk-only-ui-mock-secret").run()
    widget(app,"button","测试连接").click().run()
    app.button(key="settings_close").click().run()
    widget(app,"text_area","问题（确认后发送）").input("解释当前指标").run()
    assert calls == []
    widget(app,"button","发送到 DeepSeek").click().run()
    assert not app.exception and len(calls) == 1 and calls[0]["model"] == "alpha"
    assert widget(app,"text_area","问题（确认后发送）").value == ""
    app.run()
    assert len(calls) == 1
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
    latest_answer = [message for message in app.session_state["deepseek_chat"] if message["role"] == "assistant"][-1]
    app.button(key=f"deepseek_save_{latest_answer['turn_id']}").click().run()
    saved = storage.list_learning_notes(tmp_path / "research.sqlite3")[0]
    assert saved["model"] == "beta-actual"
    assert saved["title"].startswith("AI 研究问答")
    assert "## 问题" in saved["content"] and "## DeepSeek 回答" in saved["content"]
    assert any("研究笔记 #" in item.value for item in app.success)
    assert app.button(key=f"deepseek_save_{latest_answer['turn_id']}").disabled is True
    assert any("navigator.clipboard" in str(item.value) for item in app.get("html"))
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


def test_history_and_new_chat_switch_without_model_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    conversation = ai_chat.create_conversation("standalone", title="旧收益问答")
    ai_chat.add_message(conversation["id"], turn_id="one", role="user", content="什么是复权")
    ai_chat.add_message(conversation["id"], turn_id="one", role="assistant", content="回答内容",
                        model="deepseek-flash")
    calls = []

    class NeverCalled:
        def __init__(self, *args, **kwargs):
            calls.append("client")

    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", NeverCalled)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    widget(app, "button", "DeepSeek 助手").click().run()
    app.button(key="deepseek_history").click().run()
    assert app.text_input(key="deepseek_history_search")
    app.button(key=f"deepseek_history_open_{conversation['id']}").click().run()
    assert app.session_state["deepseek_conversation_id"] == conversation["id"]
    assert any(message["content"] == "回答内容" for message in app.session_state["deepseek_chat"])

    app.button(key="deepseek_new_chat").click().run()
    assert app.session_state["deepseek_chat"] == []
    app.run()
    assert app.session_state["deepseek_chat"] == []
    assert calls == []


def test_research_note_failure_uses_research_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        "quant_lab.ui_deepseek.save_research_note",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("read only")),
    )
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    widget(app, "button", "DeepSeek 助手").click().run()
    app.session_state["deepseek_chat"] = [{
        "role": "assistant", "content": "待复核回答", "model": "model-x",
        "security": "教学问答", "complete": True, "context": {},
    }]
    app.run()
    widget(app, "button", "保存到研究笔记").click().run()

    assert any("研究笔记保存失败" in item.value for item in app.error)
    assert not any("学习笔记保存失败" in item.value for item in app.error)


def test_multiturn_summary_is_explicit_streamed_and_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    calls = []

    class Client:
        def __init__(self, key):
            self.key = key
        def stream_with_recovery(self, model, prompt, history, context, **kwargs):
            calls.append({"model": model, "prompt": prompt, "history": history,
                          "context": context, **kwargs})
            answer = Answer("summary-model-actual")
            def chunks():
                answer.text = "已确认事实、未决问题和下一步行动。"
                yield answer.text
                answer.complete = True
            return answer, chunks()

    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", Client)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    widget(app, "button", "DeepSeek 助手").click().run()
    app.session_state["deepseek_api_key"] = "sk-summary-mock-secret"
    app.session_state["deepseek_models"] = [{"id": "summary-model"}]
    app.session_state["ds_model_select"] = "summary-model"
    conversation = ai_chat.create_conversation("standalone")
    for turn, question, answer in (("turn-1", "第一问", "第一答"), ("turn-2", "第二问", "第二答")):
        ai_chat.add_message(conversation["id"], turn_id=turn, role="user", content=question)
        ai_chat.add_message(conversation["id"], turn_id=turn, role="assistant", content=answer,
                            model="summary-model")
    app.session_state["deepseek_conversation_id"] = conversation["id"]
    app.session_state["deepseek_history_locked"] = True
    app.session_state["deepseek_attach"] = False
    app.run()

    assert widget(app, "button", "总结并保存本次对话")
    assert calls == []
    widget(app, "button", "总结并保存本次对话").click().run()

    assert len(calls) == 1
    assert calls[0]["purpose"] == "conversation_summary"
    assert calls[0]["history_limit"] == 20
    assert [message["content"] for message in calls[0]["history"]] == ["第一问", "第一答", "第二问", "第二答"]
    saved = storage.list_learning_notes(tmp_path / "research.sqlite3")[0]
    assert saved["title"].startswith("AI 对话总结 · 第一问")
    assert "## 对话主题" in saved["content"] and "## 对话总结" in saved["content"]
    assert saved["model"] == "summary-model-actual"
    assert len(calls) == 1
    app.run()
    assert len(calls) == 1


def test_incomplete_multiturn_summary_is_not_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))

    class Client:
        def __init__(self, key):
            self.key = key
        def stream_with_recovery(self, model, prompt, history, context, **kwargs):
            answer = Answer("summary-model")
            def chunks():
                answer.text = "未完成的总结"
                yield answer.text
                answer.complete = False
            return answer, chunks()

    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", Client)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    widget(app, "button", "DeepSeek 助手").click().run()
    app.session_state["deepseek_api_key"] = "sk-summary-incomplete"
    app.session_state["deepseek_models"] = [{"id": "summary-model"}]
    app.session_state["ds_model_select"] = "summary-model"
    app.session_state["deepseek_attach"] = False
    conversation = ai_chat.create_conversation("standalone")
    for turn, question, answer in (("one", "第一问", "第一答"), ("two", "第二问", "第二答")):
        ai_chat.add_message(conversation["id"], turn_id=turn, role="user", content=question)
        ai_chat.add_message(conversation["id"], turn_id=turn, role="assistant", content=answer,
                            model="summary-model")
    app.session_state["deepseek_conversation_id"] = conversation["id"]
    app.session_state["deepseek_history_locked"] = True
    app.run()
    widget(app, "button", "总结并保存本次对话").click().run()

    summaries = [message for message in app.session_state["deepseek_chat"]
                 if message.get("kind") == "conversation_summary"]
    assert summaries and summaries[-1]["complete"] is False
    assert storage.list_learning_notes(tmp_path / "research.sqlite3") == []


def test_research_workspace_points_to_actual_connection_location(tmp_path, monkeypatch):
    from test_workspaces import sample_bundle

    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args: sample_bundle())
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    app.sidebar.button[0].click().run()
    finish_background_jobs(app)
    widget(app, "button", "DeepSeek 助手").click().run()
    widget(app, "button", "研究实验").click().run()
    text = "\n".join(str(item.value) for item in (*app.caption, *app.info))

    assert "⚙ → DeepSeek" in text
    assert "本页上方" not in text


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
    finish_background_jobs(app)
    widget(app,"button","立即更新历史日线").click().run()
    assert calls[-1] == {"force": True}
    app.session_state["history_manual_at"] = float('-inf')
    app.run()
    widget(app,"button","立即更新历史日线").click().run()
    assert not app.exception
    retained = app.session_state["loaded_bundle"]
    assert retained.received_at == first.received_at and retained.frame.equals(first.frame)
    assert retained.update_error and retained.update_result == "请求失败"
