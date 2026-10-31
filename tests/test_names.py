"""Market-specific security identity, profile mapping and graceful failures."""

from datetime import datetime, timezone

import pytest

from quant_lab.names import NameProvider, NameCache
from quant_lab.market_data import display_security, normalize_symbol


def test_cached_name_read_never_fetches_upstream(monkeypatch):
    from quant_lab import storage
    class Provider:
        def lookup(self, *args):
            pytest.fail("cache-only display attempted a network lookup")
    cache = NameCache(Provider())
    assert cache.peek("港股", "700") == ""
    fetched = datetime(2026, 10, 1, tzinfo=timezone.utc)
    storage.save_security_name("港股", "00700", "腾讯控股", "测试来源", fetched)
    assert cache.peek("港股", "700") == "腾讯控股"
    assert storage.cached_security_name("港股", "00700")["fetched_at"] == fetched.isoformat()


def test_a_profile_mapping_preserves_leading_zero(monkeypatch):
    profile(monkeypatch, "000001.SZ", "平安银行")
    assert NameProvider().lookup("A 股", "SZ000001") == "平安银行"
    assert display_security("港股", "1", "测试港股") == "港股 00001（测试港股）"


def test_hk_profile_and_market_cache_are_distinct(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"result": {"data": [{"SECUCODE": "00001.HK", "SECURITY_NAME_ABBR": "长和"}]}}
        def close(self):
            pass
    calls = []
    def get(url, **kwargs):
        calls.append(kwargs)
        return Response()
    monkeypatch.setattr("quant_lab.names.requests.get", get)
    cache = NameCache()
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
    profile(monkeypatch, "000002.SZ", "错误映射")
    try:
        NameProvider().lookup("A 股", "000001")
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched code was accepted")


def profile(monkeypatch, code, name):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"result": {"data": [{"SECUCODE": code, "SECURITY_NAME_ABBR": name}]}}
        def close(self):
            pass
    def get(url, **kwargs):
        assert kwargs["params"]["reportName"] == "RPT_F10_BASIC_ORGINFO"
        assert kwargs["timeout"] == (3, 8)
        return Response()
    monkeypatch.setattr("quant_lab.names.requests.get", get)


def test_force_retries_failure_and_retains_success_time(monkeypatch, tmp_path):
    from quant_lab import storage
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    class Provider:
        source = "test profile"
        calls = 0
        fail = True
        def lookup(self, *args):
            self.calls += 1
            if self.fail:
                raise ConnectionError("offline")
            return "腾讯控股"
    provider = Provider()
    cache = NameCache(provider)
    assert cache.lookup("港股", "700") == ""
    assert cache.lookup("港股", "700") == "" and provider.calls == 1
    provider.fail = False
    assert cache.lookup("港股", "700", force=True) == "腾讯控股"
    previous = storage.cached_security_name("港股", "00700")
    provider.fail = True
    assert cache.lookup("港股", "700", force=True) == "腾讯控股"
    assert storage.cached_security_name("港股", "00700") == previous
    assert cache.error("港股", "700")


def test_same_name_force_requests_are_merged(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from quant_lab import names
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    started, release, joined = Event(), Event(), Event()
    class Flight(Event):
        def wait(self, timeout=None):
            joined.set()
            return super().wait(timeout)
    monkeypatch.setattr(names, "Event", Flight)
    class Provider:
        source = "test profile"
        calls = 0
        def lookup(self, *args):
            self.calls += 1
            started.set()
            assert release.wait(5)
            return "贵州茅台"
    provider = Provider()
    cache = NameCache(provider)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(cache.lookup, "A 股", "600519", force=True)
        assert started.wait(5)
        second = pool.submit(cache.lookup, "A 股", "600519", force=True)
        try:
            assert joined.wait(5)
        finally:
            release.set()
        assert first.result() == second.result() == "贵州茅台"
    assert provider.calls == 1
