"""US names, long windows, watchlists and shared market operations."""
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import finish_background_jobs
from quant_lab import names, securities, us_profiles, us_sources
from quant_lab.names import NameCache, NameProvider


def test_us_profile_code_class_and_source_fields_are_verified(monkeypatch):
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def json(self):
            return {"success": True, "result": {"pages": 1, "data": [{
                "SECURITY_CODE": "BRK_B", "SECUCODE": "BRK_B.N",
                "ORG_NAME": "伯克希尔哈撒韦公司", "ORG_EN_ABBR": "Berkshire Hathaway Inc."}]}}
    def request(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    monkeypatch.setattr(us_profiles.requests, "get", request)
    assert NameProvider().lookup("美股", "brk.b") == "伯克希尔哈撒韦公司"
    assert calls[0][1]["params"]["filter"] == '(SECURITY_CODE="BRK_B")'
    assert calls[0][1]["timeout"] == (3, 10)
    assert "ORG_NAME" in calls[0][1]["params"]["columns"]
    with pytest.raises(ValueError, match="不匹配"):
        NameProvider().lookup("美股", "AAPL")
    with pytest.raises(ValueError):
        us_profiles.profile_identity({"SECURITY_CODE": "AAPL", "SECUCODE": "AAPL.F", "ORG_NAME": "wrong venue"})
    assert us_profiles.profile_identity({"SECURITY_CODE": "ABC", "SECUCODE": "ABC.O", "ORG_NAME": None,
        "ORG_EN_ABBR": "ABC Corp."}) == ("ABC", "ABC Corp.")


def test_us_names_cache_force_failure_and_success_clock(monkeypatch):
    from quant_lab import storage
    calls = []
    def lookup(symbol):
        calls.append(symbol)
        return "苹果公司"
    monkeypatch.setattr(us_profiles, "security_name", lookup)
    cache = NameCache()
    assert cache.lookup("美股", "aapl") == "苹果公司"
    assert cache.lookup("美股", "AAPL") == "苹果公司" and calls == ["AAPL"]
    saved = storage.cached_security_name("美股", "AAPL")
    assert saved["source"] == us_profiles.SOURCE
    def fail(symbol): raise ConnectionError("offline")
    monkeypatch.setattr(us_profiles, "security_name", fail)
    assert cache.lookup("美股", "AAPL", force=True) == "苹果公司"
    assert storage.cached_security_name("美股", "AAPL") == saved
    assert cache.error("美股", "AAPL")
    assert NameCache().peek("美股", "aapl") == "苹果公司"


def test_us_directory_is_offline_searchable_and_keeps_original_timestamp(monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail("offline directory attempted a request")
    monkeypatch.setattr(us_profiles.requests, "get", forbidden)
    item = securities.security_directory("美股")
    assert len(item.rows) > 5000
    assert dict(item.rows)["AAPL"] == "苹果公司"
    assert dict(item.rows)["BRK.B"] == "伯克希尔哈撒韦公司"
    def fail(*args, **kwargs): raise ConnectionError("offline")
    monkeypatch.setattr(us_profiles.requests, "get", fail)
    failed = securities.security_directory("美股", force=True)
    assert failed.error and failed.rows == item.rows and failed.received_at == item.received_at


def test_us_custom_history_range_has_no_ten_year_cap():
    assert us_sources._reference_query("msft", date(1986, 3, 13), date(2026, 10, 30)) == (
        "MSFT", date(1986, 3, 13), date(2026, 10, 30))
    with pytest.raises(ValueError):
        us_sources._reference_query("MSFT", date(1899, 1, 1), date(2026, 10, 30))
    with pytest.raises(ValueError):
        us_sources._reference_query("MSFT", date(2026, 10, 30), date(2026, 1, 1))


def test_us_watchlist_uses_usd_close_and_retains_last_success(monkeypatch):
    from quant_lab import storage
    from quant_lab.data import SnapshotCache, DataUnavailableError
    from quant_lab.watchlist_data import WatchlistProvider
    from quant_lab.market_data import normalize_symbol
    from test_us_price_research import reference
    assert storage.add_watchlist("美股", "brk.b", company_name="伯克希尔哈撒韦公司") == "BRK.B"
    assert ("美股", "BRK.B") in storage.list_watchlist()
    with pytest.raises(ValueError): normalize_symbol("美股", "BRK.B")  # AH execution stays unchanged.
    def fetch(symbol, *args, **kwargs):
        assert symbol == "BRK.B" and kwargs["force"]
        return reference(symbol)
    monkeypatch.setattr(us_sources, "fetch_sina_reference", fetch)
    cache = SnapshotCache(WatchlistProvider(None), min_request_gap=0)
    quote, _ = cache.get("美股", "BRK.B", force=True)
    assert quote.currency == "USD" and quote.symbol == "BRK.B"
    def fail(*args, **kwargs): raise ValueError("offline")
    monkeypatch.setattr(us_sources, "fetch_sina_reference", fail)
    old, _ = cache.get("美股", "BRK.B", force=True)
    assert old.update_error and old.received_at == quote.received_at and old.last_close == quote.last_close
    storage.remove_watchlist("美股", "BRK.B")
    assert storage.list_watchlist() == []


def test_market_pages_share_refresh_and_us_table_actions(monkeypatch):
    from quant_lab import storage
    from test_us_price_research import reference
    calls = []
    def fetch(symbol, *args, **kwargs):
        calls.append((symbol, args, kwargs["force"]))
        return reference(symbol)
    monkeypatch.setattr(us_sources, "fetch_sina_reference", fetch)
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=30).run()
    for market in ("A 股", "港股", "美股"):
        app.sidebar.selectbox(key="market_selection").set_value(market).run()
        assert any(item.label == "立即更新" for item in app.sidebar.button)
        assert app.button(key="refresh_pause").label == "暂停自动刷新"
        assert not app.exception
    app.sidebar.date_input(key="history_start").set_value(date(2010, 1, 1)).run()
    assert not calls
    next(item for item in app.sidebar.button if item.label == "加载真实历史日线").click().run()
    finish_background_jobs(app)
    assert calls[0][1][0] == date(2010, 1, 1)
    assert app.button(key="history_fullscreen_open").label == "全屏"
    assert any(item.label == "导出 CSV" for item in app.get("download_button"))
    assert any(item.label == "加入自选" for item in app.button)
    assert not app.exception
    app.button(key="refresh_pause").click().run()
    assert app.button(key="refresh_pause").label == "恢复自动刷新"
    app.button(key="watch_add").click().run()
    assert ("美股", "AAPL") in storage.list_watchlist()
    assert any(item.label == "从自选股选择" for item in app.sidebar.selectbox)
    assert not app.exception


@pytest.mark.parametrize("currency,unit", [("CNY", "元/股"), ("HKD", "港元/股"), ("USD", "美元/股")])
def test_shared_history_charts_keep_market_currency(currency, unit):
    from quant_lab.charts import history_price_chart, history_candlestick_chart
    from test_us_price_research import reference
    frame = reference(n=35).frame
    for builder in (history_price_chart, history_candlestick_chart):
        figure = builder(frame, currency)
        assert figure.layout.yaxis.title.text == f"价格（{unit}）"
    assert unit in history_price_chart(frame, currency).data[0].hovertemplate
