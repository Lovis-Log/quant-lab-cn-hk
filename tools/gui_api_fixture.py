"""Injected only into an isolated GUI test copy, never the shipped app."""

import json
import time

from quant_lab import names, credentials
from quant_lab.deepseek import DeepSeekClient

names.security_name = lambda *args: "界面验证样本"
credentials.remember_key = lambda *args, **kwargs: None
credentials.load_key = lambda **kwargs: None
credentials.clear_key = lambda **kwargs: None


class Response:
    status_code = 200
    def __init__(self, model=None):
        self.model = model
    def json(self):
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
    return Response(kwargs.get("json", {}).get("model"))

DeepSeekClient._request = request
