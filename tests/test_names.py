"""Market-specific security identity, profile mapping and graceful failures."""

from datetime import datetime, timezone

import pandas as pd

from quant_lab.names import NameProvider, NameCache
from quant_lab.market_data import display_security, normalize_symbol


def test_a_profile_mapping_preserves_leading_zero(monkeypatch):
    monkeypatch.setattr("quant_lab.names.ak.stock_individual_info_em", lambda **_: pd.DataFrame(
        {"item": ["股票代码", "股票简称"], "value": ["000001", "平安银行"]}))
    assert NameProvider().lookup("A 股", "SZ000001") == "平安银行"
    assert display_security("港股", "1", "测试港股") == "港股 00001（测试港股）"


def test_hk_profile_and_market_cache_are_distinct(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"result": {"data": [{"SECUCODE": "00001.HK", "SECURITY_NAME_ABBR": "长和"}]}}
    calls = []
    def get(url, **kwargs):
        calls.append(kwargs)
        return Response()
    monkeypatch.setattr("quant_lab.names.requests.get", get)
    monkeypatch.setattr("quant_lab.names.ak.stock_individual_info_em", lambda **_: pd.DataFrame(
        {"item": ["股票代码", "股票简称"], "value": ["000001", "平安银行"]}))
    cache = NameCache()
    assert cache.lookup("A 股", "000001") == "平安银行"
    assert cache.lookup("港股", "1") == "长和"
    assert cache.lookup("港股", "00001.HK") == "长和"
    assert len(calls) == 1 and calls[0]["timeout"] == (3, 8)
    # Another process/cache instance reuses persisted identity without a call.
    assert NameCache().lookup("港股", "1") == "长和" and len(calls) == 1


def test_name_failure_does_not_assert_nonexistence(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    class Provider:
        source = "test profile"
        calls = 0
        def lookup(self, *args):
            self.calls += 1
            raise ConnectionError("offline")
    provider = Provider()
    cache = NameCache(provider)
    assert cache.lookup("港股", "700") == ""
    assert cache.lookup("港股", "700") == "" and provider.calls == 1
    assert display_security("港股", "700") == "港股 00700（名称暂不可用）"


def test_mismatched_profile_is_not_a_name_mapping(monkeypatch):
    monkeypatch.setattr("quant_lab.names.ak.stock_individual_info_em", lambda **_: pd.DataFrame(
        {"item": ["股票代码", "股票简称"], "value": ["000002", "错误映射"]}))
    try:
        NameProvider().lookup("A 股", "000001")
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched code was accepted")
