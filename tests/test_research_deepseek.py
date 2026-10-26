"""Research shares DeepSeek settings; redraws and local work never send."""

from pathlib import Path
import json

import pytest
from streamlit.testing.v1 import AppTest

from quant_lab.ai_research import HYPOTHESIS_SCHEMA
from quant_lab.deepseek import DeepSeekClient, AIRequestError
from test_deepseek import Response, Session, SECRET
from test_workspaces import sample_bundle


BODY = {"title": "检验双均线", "rationale": "仅为待检验假设",
        "strategy_kind": "dual_ma", "short_window": 3, "long_window": 8,
        "assumptions": ["历史日线"], "statistical_risks": ["过拟合"], "example_code": "# 只展示"}


def test_json_request_uses_selected_deepseek_model_and_redacts():
    session = Session([Response(data={"model": "actual-model", "choices": [{
        "finish_reason": "stop", "message": {"content": json.dumps(BODY)}}]})])
    client = DeepSeekClient(SECRET, session)
    assert client.structured("selected-model", {"question": SECRET}, HYPOTHESIS_SCHEMA, "Research") == BODY
    method, url, request = session.calls[0]
    assert method == "POST" and url == "https://api.deepseek.com/chat/completions"
    assert request["json"]["model"] == "selected-model"
    assert request["json"]["response_format"] == {"type": "json_object"}
    assert SECRET not in json.dumps(request["json"])
    assert client.model_used == "actual-model"


@pytest.mark.parametrize("body,reason", [({**BODY, "short_window": True}, "stop"),
    ({**BODY, "statistical_risks": "invalid"}, "stop"), ({**BODY, "extra": 1}, "stop"), (BODY, "length")])
def test_malformed_or_incomplete_json_is_rejected(body, reason):
    session = Session([Response(data={"choices": [{"finish_reason": reason,
        "message": {"content": json.dumps(body)}}]})])
    with pytest.raises(AIRequestError):
        DeepSeekClient(SECRET, session).structured("selected-model", {}, HYPOTHESIS_SCHEMA, "Research")


def test_research_ui_shares_key_model_and_isolates_current_data(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args: sample_bundle())
    calls = []
    class Client:
        def __init__(self, key):
            assert key == SECRET
            self.model_used = "actual-model"
        def list_models(self):
            return [{"id": "selected-model"}]
        def structured(self, model, payload, schema, instructions, **kwargs):
            calls.append({"model": model, "payload": payload})
            return BODY if "question" in payload else {"summary": "需复核", "observations": ["审计值"],
                "limitations": ["单股票"], "next_tests": ["新时期"]}
    monkeypatch.setattr("quant_lab.ui_ai.DeepSeekClient", Client)
    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", Client)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    app.sidebar.button[0].click().run()
    next(w for w in app.button if w.label == "DeepSeek 助手").click().run()
    next(w for w in app.button if w.label == "研究实验").click().run()
    assert not any("OPENAI" in item.value for item in app.info)
    assert next(w for w in app.button if w.label == "生成 AI 假设").disabled
    next(w for w in app.button if w.label == "⚙").click().run()
    app.text_input(key="deepseek_api_key").input(SECRET).run()
    next(w for w in app.button if w.label == "测试连接").click().run()
    app.button(key="settings_close").click().run()
    assert not next(w for w in app.button if w.label == "生成 AI 假设").disabled
    assert calls == []
    next(w for w in app.button if w.label == "生成 AI 假设").click().run()
    assert not app.exception and len(calls) == 1
    assert calls[0]["model"] == "selected-model"
    assert calls[0]["payload"]["context"]["data_fingerprint"]
    next(w for w in app.button if w.label == "运行受控实验（内置策略）").click().run()
    app.run()
    assert len(calls) == 1
    next(w for w in app.button if w.label == "让 AI 审阅实验").click().run()
    assert not app.exception and len(calls) == 2
    assert calls[-1]["payload"]["context"]["audit_id"]
    assert "raw_history" not in calls[-1]["payload"]["context"]
    assert any("实际模型：actual-model" in w.value for w in app.caption)
    next(w for w in app.button if w.label == "← 返回对话").click().run()
    assert any('"audit_id"' in item.value for item in app.json)
    assert len(calls) == 2
    next(w for w in app.button if w.label == "研究实验").click().run()
    app.sidebar.selectbox(key="symbol_A 股").set_value("000001").run()
    assert len(calls) == 2 and "ai_experiment" in app.session_state
    assert not any(w.label == "让 AI 审阅实验" for w in app.button)
