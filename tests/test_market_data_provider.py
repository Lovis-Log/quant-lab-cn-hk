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
    assert second.cached and second.frame.loc[0, "close"] == 10
    assert second.frame.date.is_monotonic_increasing
    assert provider.calls == 1


def test_cache_never_reuses_invalid_rows_and_keeps_validation_reason():
    class Provider:
        broken = False
        def history(self, market, symbol, start, end, adjustment):
            from quant_lab.data import HistoryBundle
            data = rows().drop(columns="volume") if self.broken else rows()
            return HistoryBundle(data, market, symbol, "test", "CNY", adjustment, datetime.now(timezone.utc))
    provider = Provider()
    cache = HistoryCache(provider)
    args = ("A 股", "600519", date(2026,10,1), date(2026,10,11))
    good = cache.get(*args)
    provider.broken = True
    failed = cache.get(*args, force=True)
    assert failed.frame.equals(good.frame) and failed.received_at == good.received_at
    assert "volume" in failed.update_error
    with pytest.raises(DataUnavailableError, match="volume"):
        HistoryCache(provider).get(*args)


def test_snapshot_uses_last_completed_close_not_intraday_last_bar(monkeypatch):
    from quant_lab.data import HistoryBundle
    from quant_lab.data_quality import CalendarReference
    reference = CalendarReference("TEST", "1", tuple((date(2026,10,day),datetime(2026,10,day,8,tzinfo=timezone.utc)) for day in (8,9)), True, "test")
    monkeypatch.setattr("quant_lab.data_quality.calendar_reference", lambda *args: reference)
    raw = rows().sort_values("date").reset_index(drop=True)
    raw["date"] = pd.to_datetime(raw.date)
    provider = AKShareProvider()
    bundle = HistoryBundle(raw,"港股","00700","test","HKD","",datetime(2026,10,9,3,tzinfo=timezone.utc))
    monkeypatch.setattr(provider, "history", lambda *args: bundle)
    quote = provider.snapshot("港股","00700")
    assert quote.observation_date == date(2026,10,8)
    assert quote.last_close == 10
    assert "未结束日线不纳入" in quote.status


def test_invalid_snapshot_cannot_replace_last_success():
    class Provider:
        broken = False
        def snapshot(self, market, symbol):
            return MarketSnapshot(market,symbol,float('nan') if self.broken else 10.,date(2026,10,8),
                datetime(2026,10,8,9,tzinfo=timezone.utc),"test","CNY")
    provider = Provider()
    cache = SnapshotCache(provider,min_request_gap=0)
    good,_ = cache.get("A 股","600519")
    provider.broken = True
    failed,_ = cache.get("A 股","600519",force=True)
    assert failed.last_close == good.last_close and failed.received_at == good.received_at
    assert "有限值" in failed.update_error
    with pytest.raises(DataUnavailableError,match="有限值"):
        SnapshotCache(provider,min_request_gap=0).get("A 股","600519")


def test_provider_error_log_tracks_active_isolated_library(tmp_path, monkeypatch):
    from quant_lab import data
    monkeypatch.setattr(data,"LOG_PATH",None)
    first,second = tmp_path/"one",tmp_path/"two"
    monkeypatch.setenv("QUANT_LAB_DATA_DIR",str(first))
    data._record_failure("600519",DataUnavailableError("first isolated failure"))
    first_path = first/"logs/data_errors.log"
    original = first_path.read_bytes()
    monkeypatch.setenv("QUANT_LAB_DATA_DIR",str(second))
    data._record_failure("00700",DataUnavailableError("second isolated failure"))
    assert first_path.read_bytes()==original
    assert "second isolated failure" in (second/"logs/data_errors.log").read_text(encoding="utf-8")
