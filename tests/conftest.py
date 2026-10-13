"""UI tests use offline securities names; no upstream API is needed."""

import pytest


@pytest.fixture(autouse=True)
def offline_ui_names(monkeypatch):
    from quant_lab import names
    monkeypatch.setattr(names, "security_name", lambda market, symbol: "测试证券")
