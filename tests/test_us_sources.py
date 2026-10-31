"""Reference prices cannot silently become executable or archived US inputs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Event

import pandas as pd
import pytest

from quant_lab import us_sources
from quant_lab.refresh import RefreshCache


def prices(dates=("2024-05-23", "2024-05-24", "2024-05-28")):
    return pd.DataFrame({"date": pd.to_datetime(dates), "open": 100., "high": 102.,
                         "low": 99., "close": 101., "volume": 1000})


def test_reference_calendar_gaps_finished_sessions_and_qualification(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 5, 29, 15, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(us_sources, "datetime", Clock)
    monkeypatch.setattr(us_sources, "_request_sina_daily", lambda symbol: prices(("2024-05-23", "2024-05-28", "2024-05-29")))
    result = us_sources._load_sina_reference("AAPL", date(2024, 5, 23), date(2024, 5, 29))
    assert result.excluded_unfinished_rows == 1 and result.expected_sessions == 3
    assert result.missing_sessions == ("2024-05-24",) and not result.non_session_dates
    assert result.observation.actual_end == "2024-05-28"
    assert not result.observation.raw_execution_verified
    assert not result.observation.retention_verified and not result.observation.actions_complete
    assert not result.observation.identity_verified and not result.observation.settlement_calendar_verified


def test_reference_invalid_data_rejected_and_old_success_survives_force(monkeypatch):
    cache = RefreshCache()
    monkeypatch.setattr(us_sources, "_REFERENCE_CACHE", cache)
    monkeypatch.setattr(us_sources, "_request_sina_daily", lambda symbol: prices())
    args = ("AAPL", date(2024, 5, 23), date(2024, 5, 28))
    original = us_sources.fetch_sina_reference(*args, cache_namespace="one")
    original.frame.loc[0, "close"] = 999.  # callers cannot corrupt the cache
    assert us_sources.fetch_sina_reference(*args, cache_namespace="one").frame.close.iloc[0] == 101.
    monkeypatch.setattr(us_sources, "_request_sina_daily", lambda symbol: prices(("2024-05-23", "2024-05-23")))
    stale = us_sources.fetch_sina_reference(*args, force=True, cache_namespace="one")
    assert stale.update_error and stale.cached
    assert stale.observation == original.observation
    with pytest.raises(ValueError, match="失败"):
        us_sources.fetch_sina_reference(*args, cache_namespace="another-library")


def test_reference_validates_requested_interval_and_reports_bad_ohlc(monkeypatch):
    frame = prices(("2020-01-02", "2024-05-23", "2024-05-24", "2024-05-28"))
    frame.loc[0, "high"] = 90.
    monkeypatch.setattr(us_sources, "_request_sina_daily", lambda symbol: frame)
    monkeypatch.setattr(us_sources, "_REFERENCE_CACHE", RefreshCache())
    current = us_sources.fetch_sina_reference("BRK.B", date(2024, 5, 23), date(2024, 5, 28))
    assert len(current.frame) == 3
    with pytest.raises(ValueError, match="OHLC高低价关系无效"):
        us_sources.fetch_sina_reference("BRK.B", date(2020, 1, 2), date(2024, 5, 28))


def test_reference_single_flight_and_symbol_validation(monkeypatch):
    entered, release = Event(), Event()
    calls = []
    def load(symbol):
        calls.append(symbol)
        entered.set()
        assert release.wait(5)
        return prices()
    monkeypatch.setattr(us_sources, "_REFERENCE_CACHE", RefreshCache())
    monkeypatch.setattr(us_sources, "_request_sina_daily", load)
    args = ("aapl", date(2024, 5, 23), date(2024, 5, 28))
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(us_sources.fetch_sina_reference, *args)
        assert entered.wait(5)
        two = pool.submit(us_sources.fetch_sina_reference, *args)
        release.set()
        assert one.result().observation == two.result().observation
    assert calls == ["AAPL"]
    with pytest.raises(ValueError):
        us_sources.fetch_sina_reference("../AAPL", args[1], args[2])
    assert calls == ["AAPL"]


def test_sina_decoder_uses_date_labels_bounded_http_and_rejects_scripts(monkeypatch):
    import py_mini_racer
    seen = []
    class Response:
        text = 'var KLC_K2_BRK$B="encoded";'
        def raise_for_status(self):
            pass
    class Decoder:
        def eval(self, code):
            assert "encoded" not in code
        def call(self, function, encoded):
            assert (function, encoded) == ("d", "encoded")
            return [{"date": "2024-05-28T00:00:00.000Z", "open": 100., "close": 101.,
                     "high": 102., "low": 99., "volume": 10}]
        def close(self):
            pass
    def get(url, **kwargs):
        seen.append((url, kwargs))
        return Response()
    monkeypatch.setattr(us_sources.requests, "get", get)
    monkeypatch.setattr(py_mini_racer, "MiniRacer", Decoder)
    frame = us_sources._request_sina_daily("BRK.B")
    assert frame.date.iloc[0] == pd.Timestamp("2024-05-28") and frame.date.dt.tz is None
    assert seen == [("https://finance.sina.com.cn/staticdata/us/BRK.B", {"timeout": (5, 20)})]
    Response.text = 'var KLC_KL_AAPL="encoded"; malicious();'
    with pytest.raises(ValueError, match="格式"):
        us_sources._request_sina_daily("AAPL")
