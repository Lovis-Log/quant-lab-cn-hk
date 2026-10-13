"""Mocked models, streaming, request bounds and secret-safe errors."""

import json

import pytest
import requests

from quant_lab.deepseek import AIRequestError, DeepSeekClient, safe_context
from quant_lab.security import StreamRedactor
from quant_lab.ai_context import context_scope


SECRET = "sk-only-for-mocked-tests-123456"


class Response:
    def __init__(self, status=200, data=None, lines=None):
        self.status_code, self.data, self.lines = status, data, lines or []
    def json(self):
        return self.data
    def close(self):
        pass
    def iter_lines(self, **kwargs):
        return iter(self.lines)


class Session:
    def __init__(self, responses):
        self.responses, self.calls = iter(responses), []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return next(self.responses)


def streamed(model, content="程序事实应核对，缺少数据不能猜测。"):
    return Response(lines=["data: " + json.dumps({"model": model,
        "choices": [{"delta": {"content": content}, "finish_reason": "stop"}]}, ensure_ascii=False), "data: [DONE]"])


def test_dynamic_models_switch_and_supported_parameters():
    models = [{"id": "alpha", "max_output_tokens": 512, "effort": {"supported_levels": ["low"]}},
              {"id": "beta", "max_output_tokens": 2048}]
    session = Session([Response(data={"data": models}), streamed("alpha-resolved"), streamed("beta")])
    client = DeepSeekClient(SECRET, session)
    discovered = client.list_models()
    answer, chunks = client.stream("alpha", "解释收益率", [], metadata=discovered[0], effort="low")
    assert "程序事实" in "".join(chunks) and answer.model_used == "alpha-resolved" and answer.complete
    _, chunks = client.stream("beta", "再解释", [], metadata=discovered[1], effort="low")
    list(chunks)
    payloads = [kwargs["json"] for method, _, kwargs in session.calls if method == "POST"]
    assert payloads[0]["model"] == "alpha" and payloads[0]["max_tokens"] == 512
    assert payloads[0]["reasoning_effort"] == "low"
    assert payloads[1]["model"] == "beta" and "reasoning_effort" not in payloads[1]
    assert not ({"temperature", "top_p", "thinking"} & payloads[1].keys())


@pytest.mark.parametrize("status,word", [(401,"鉴权"),(402,"余额"),(429,"频繁"),(404,"模型"),(503,"繁忙")])
def test_http_failures_do_not_expose_body_or_key(status, word, caplog):
    client = DeepSeekClient(SECRET, Session([Response(status=status, data={"error": SECRET})]))
    with pytest.raises(AIRequestError, match=word) as exc:
        client.list_models()
    assert SECRET not in str(exc.value) and SECRET not in caplog.text


def test_stream_secret_redaction_and_private_context_limits():
    session = Session([streamed("model", "输出错误密钥 " + SECRET)])
    client = DeepSeekClient(SECRET, session)
    answer, chunks = client.stream("model", "请解释 " + SECRET, [],
                                  {"market": "港股", "symbol": "00700", "notes": SECRET, "raw_history": [SECRET]})
    output = "".join(chunks)
    assert SECRET not in output and SECRET not in answer.text
    payload = session.calls[0][2]["json"]
    assert SECRET not in json.dumps(payload) and "raw_history" not in json.dumps(payload)
    assert "notes" not in safe_context({"notes": "private"})
    assert safe_context({"performance": {"notes":"private", "return": .1}}) == {"performance":{"return":.1}}
    redactor = StreamRedactor((SECRET,))
    out = redactor.feed("x" * 500 + SECRET[:8]) + redactor.feed(SECRET[8:]) + redactor.feed("", final=True)
    assert SECRET not in out


def test_context_identity_changes_with_stock_or_experiment():
    assert context_scope({"market":"A 股","symbol":"000001"}) != context_scope({"market":"港股","symbol":"00001"})
    assert context_scope({"experiment_id":1,"audit_id":"one"}) != context_scope({"experiment_id":2,"audit_id":"two"})


def test_timeout_and_malformed_models_are_safe(caplog):
    class TimeoutSession:
        def request(self, *args, **kwargs):
            raise requests.Timeout("raw transport diagnostic " + SECRET)
    with pytest.raises(AIRequestError, match="超时") as exc:
        DeepSeekClient(SECRET, TimeoutSession()).list_models()
    assert SECRET not in str(exc.value) and SECRET not in caplog.text
    with pytest.raises(AIRequestError, match="无法识别"):
        DeepSeekClient(SECRET, Session([Response(data={"data": "broken"})])).list_models()
