"""Forced checks bypass only one query and preserve provenance on failure."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timezone, timedelta
from threading import Event

import pandas as pd

from quant_lab.data import HistoryCache, HistoryBundle
from quant_lab.refresh import RefreshCache


def test_history_force_cache_timestamp_and_failure():
    class Provider:
        calls = 0
        fail = False
        def history(self, market, symbol, start, end, adjustment):
            self.calls += 1
            if self.fail:
                raise ConnectionError("upstream")
            return HistoryBundle(pd.DataFrame({"date": pd.to_datetime(["2026-10-08"]), "close": [10.0]}),
                market, symbol, "mock", "CNY", adjustment,
                datetime(2026, 10, 8, tzinfo=timezone.utc) + timedelta(seconds=self.calls))
    provider = Provider()
    cache = HistoryCache(provider)
    args = ("A 股", "600519", date(2026, 10, 1), date(2026, 10, 11))
    first = cache.get(*args)
    cached = cache.get(*args)
    assert cached.cached and cached.received_at == first.received_at and provider.calls == 1
    renewed = cache.get(*args, force=True)
    assert provider.calls == 2 and renewed.received_at > first.received_at
    assert renewed.update_result == "检查成功，数据未变化"
    cache.get("A 股", "000001", args[2], args[3])
    provider.fail = True
    failed = cache.get(*args, force=True)
    assert failed.update_error and failed.received_at == renewed.received_at
    assert failed.frame.equals(renewed.frame)
    other = cache.get("A 股", "000001", args[2], args[3])
    assert not other.update_error  # No global cache invalidation.


def test_duplicate_concurrent_updates_use_one_request(monkeypatch):
    waiting = Event()
    class TrackedEvent(Event):
        def wait(self, timeout=None):
            waiting.set()
            return super().wait(timeout)
    monkeypatch.setattr("quant_lab.refresh.Event", TrackedEvent)
    cache = RefreshCache()
    entered, release = Event(), Event()
    calls = []
    def load():
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return 10
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get, "one-query", load, force=True)
        assert entered.wait(5)
        second = pool.submit(cache.get, "one-query", load, force=True)
        # Wait for the second worker to enter its wait path before releasing.
        assert waiting.wait(5)
        release.set()
        assert first.result().value == second.result().value == 10
    assert len(calls) == 1
