"""UI tests use offline securities names; no upstream API is needed."""

import pytest


@pytest.fixture(autouse=True)
def offline_ui_names(monkeypatch, tmp_path):
    # Tests must never migrate or modify the real user's research archive.
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path / "isolated-user-data"))
    from quant_lab import names
    from quant_lab import credentials
    monkeypatch.setattr(names, "security_name", lambda market, symbol, **kwargs: "测试证券")
    # Ordinary tests must not inspect the developer's real Windows vault.
    monkeypatch.setattr(credentials, "load_key", lambda: None)
