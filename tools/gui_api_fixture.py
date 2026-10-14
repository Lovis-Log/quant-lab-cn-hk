"""Injected only into an isolated GUI test copy, never the shipped app."""

import json
import time

from quant_lab import names, credentials, ui
from quant_lab.deepseek import DeepSeekClient
from quant_lab.data import HistoryBundle
import numpy as np
import pandas as pd

names.security_name = lambda *args, **kwargs: "界面验证样本"
credentials.remember_key = lambda *args, **kwargs: None
credentials.load_key = lambda **kwargs: None
credentials.clear_key = lambda **kwargs: None


def sample_history(market, symbol, *args, **kwargs):
    dates = pd.date_range("2026-01-02", periods=100, freq="B")
    close = 100 + np.arange(100) * .2 + np.sin(np.arange(100))
    frame = pd.DataFrame({"date": dates, "open": close - .5, "high": close + 1,
        "low": close - 1, "close": close, "volume": np.full(100, 100000), "amount": close * 100000})
    return HistoryBundle(frame, market, symbol, "模拟API验收日线（非真实行情）",
                         "CNY" if market == "A 股" else "HKD", "")


ui.fetch_history = sample_history


class Response:
    status_code = 200
    def __init__(self, payload=None):
        self.payload = payload or {}
        self.model = self.payload.get("model")
    def json(self):
        if self.payload.get("response_format"):
            incoming = json.loads(self.payload["messages"][-1]["content"])
            if "question" in incoming:
                body = {"title": "界面验收假设", "rationale": "模拟 API 返回，仅验证控件",
                    "strategy_kind": "dual_ma", "short_window": 3, "long_window": 8,
                    "assumptions": ["模拟日线"], "statistical_risks": ["非投资依据"], "example_code": "# 不执行"}
            else:
                body = {"summary": "界面验收审阅", "observations": ["本地证据待核对"],
                    "limitations": ["模拟 API"], "next_tests": ["用真实数据复核"]}
            return {"model": self.model + "-actual", "choices": [{"finish_reason": "stop",
                "message": {"content": json.dumps(body, ensure_ascii=False)}}]}
        return {"data": [{"id": "mock-a", "name": "模拟模型 A", "max_output_tokens": 4096},
                         {"id": "mock-b", "name": "模拟模型 B", "max_output_tokens": 4096}]}
    def close(self):
        pass
    def iter_lines(self, **kwargs):
        for text in ("[模拟 API，仅用于界面验收] STREAM_ONE " + "程序事实要核对。"*45,
                     " STREAM_TWO " + "直觉、公式和手算示例帮助理解。"*35,
                     " STREAM_DONE。模型解释不能代替程序计算。"):
            yield "data: " + json.dumps({"model": self.model + "-actual",
                "choices": [{"delta": {"content": text}}]}, ensure_ascii=False)
            time.sleep(.7)
        yield "data: [DONE]"


def request(self, method, endpoint, **kwargs):
    return Response(kwargs.get("json", {}))

DeepSeekClient._request = request
