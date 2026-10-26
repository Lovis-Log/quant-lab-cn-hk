"""Provider boundary, provenance and throttling without network calls."""

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from quant_lab.data import AKShareProvider, DataUnavailableError, HistoryCache, SnapshotCache
from quant_lab.market_data import MarketSnapshot, normalize_symbol
from quant_lab.processing import DataValidationError


def rows() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2026-10-09", "2026-10-08"],
        "open": [11, 10], "high": [12, 11], "low": [10, 9],
        "close": [11, 10], "volume": [100, 100], "amount": [1100, 1000],
    })


def test_symbol_normalization_is_market_specific() -> None:
    assert normalize_symbol("A 股", "sh.600519") == "600519"
    assert normalize_symbol("港股", "HK:700") == "00700"
    assert normalize_symbol("港股", "00700.HK") == "00700"
    with pytest.raises(ValueError):
        normalize_symbol("A 股", "700")


def test_provider_keeps_source_adjustment_and_receive_time(monkeypatch) -> None:
    called = {}

    def fake_hk(**kwargs):
        called.update(kwargs)
        return rows().rename(columns={
            "date": "日期", "open": "开盘", "high": "最高", "low": "最低",
            "close": "收盘", "volume": "成交量", "amount": "成交额",
        })

    monkeypatch.setattr("quant_lab.data.ak.stock_hk_hist", fake_hk)
    bundle = AKShareProvider().history("港股", "700", date(2026, 10, 1), date(2026, 10, 11), "qfq")
    assert called == {"symbol": "00700", "period": "daily", "start_date": "20261001",
                      "end_date": "20261011", "adjust": "qfq"}
    assert bundle.symbol == "00700" and bundle.currency == "HKD"
    assert bundle.source == "东方财富 · AKShare" and bundle.adjustment == "qfq"
    assert bundle.received_at is not None and bundle.received_at.tzinfo is not None
    assert bundle.frame["close"].tolist() == [10, 11]


def test_hk_provider_marks_sina_fallback(monkeypatch) -> None:
    def primary_failure(**_):
        raise ConnectionError("primary unavailable")

    monkeypatch.setattr("quant_lab.data.ak.stock_hk_hist", primary_failure)
    monkeypatch.setattr("quant_lab.data.ak.stock_hk_daily", lambda **_: rows())
    bundle = AKShareProvider().history(
        "港股", "00700", date(2026, 10, 1), date(2026, 10, 11)
    )
    assert bundle.source == "新浪财经 · AKShare（东方财富请求失败后回退）"
    assert bundle.frame["close"].tolist() == [10, 11]


def test_bad_provider_rows_are_rejected(monkeypatch) -> None:
    broken = rows().drop(columns="volume")
    monkeypatch.setattr("quant_lab.data.ak.stock_zh_a_hist_tx", lambda **_: broken)
    with pytest.raises(DataValidationError, match="volume"):
        AKShareProvider().history("A 股", "600519", date(2026, 10, 1), date(2026, 10, 11))


def test_snapshot_cache_throttles_and_preserves_failure(monkeypatch) -> None:
    class FakeProvider:
        calls = 0

        def snapshot(self, market, symbol):
            self.calls += 1
            if self.calls == 2:
                raise DataUnavailableError("upstream failed")
            return MarketSnapshot(market, symbol, 11, date(2026, 10, 9),
                                  datetime(2026, 10, 9, tzinfo=timezone.utc),
                                  "mock historical source", "CNY")

    provider = FakeProvider()
    clock = {"now": 100.0}
    monkeypatch.setattr("quant_lab.data.time.monotonic", lambda: clock["now"])
    cache = SnapshotCache(provider, ttl_seconds=300, min_request_gap=0)
    first, cached = cache.get("A 股", "600519")
    assert not cached and first.status.startswith("历史日线")
    clock["now"] = 130
    failed, cached = cache.get("A 股", "600519", force=True)
    assert cached and failed.update_error and failed.update_result == "请求失败"
    assert failed.last_close == first.last_close and failed.received_at == first.received_at
    assert provider.calls == 2
    clock["now"] = 200
    renewed, cached = cache.get("A 股", "600519", force=True)
    assert not cached and renewed.update_result == "检查成功，数据未变化"
    clock["now"] = 201
    assert cache.get("A 股", "600519")[1] is True
    assert provider.calls == 3


def test_history_cache_returns_defensive_copies(monkeypatch) -> None:
    class FakeProvider:
        calls = 0

        def history(self, market, symbol, start, end, adjustment=""):
            from quant_lab.data import HistoryBundle
            self.calls += 1
            return HistoryBundle(rows(), market, symbol, "mock", "CNY", adjustment,
                                 datetime.now(timezone.utc))

    provider = FakeProvider()
    cache = HistoryCache(provider)
    first = cache.get("A 股", "600519", date(2026, 10, 1), date(2026, 10, 11))
    first.frame.loc[0, "close"] = 999
    second = cache.get("A 股", "600519", date(2026, 10, 1), date(2026, 10, 11))
    assert second.cached and second.frame.loc[0, "close"] == 11
    assert provider.calls == 1
