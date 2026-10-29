"""US workspace is offline by default, keeps provenance, and never opens live trades."""

from pathlib import Path

from streamlit.testing.v1 import AppTest
from conftest import navigate

from conftest import finish_background_jobs


APP=Path(__file__).resolve().parents[1]/"app.py"


def test_us_workspace_offline_run_cash_ledger_export_and_parameter_retention(monkeypatch):
    calls=[]
    monkeypatch.setattr("quant_lab.us_sources.inspect_sina_prices",lambda *args:calls.append(args))
    app=AppTest.from_file(APP,default_timeout=30).run()
    navigate(app, "美股研究")
    assert not app.exception and not calls
    assert any("非真实美股行情" in item.value for item in app.info)
    app.number_input(key="us_cash").set_value(5000.)
    app.button(key="FormSubmitter:us_teaching_parameters-运行美元教学研究").click().run()
    finish_background_jobs(app)
    assert not app.exception and not app.error and not calls
    assert any(item.label=="教学策略累计收益" for item in app.metric)
    key,(experiment,portfolio,report)=app.session_state["us_research_result"]
    assert portfolio.equity.settled_cash.ge(0).all() and portfolio.manifest["currency"]=="USD"
    assert report.startswith(b'{')
    assert app.session_state["_current_ai_context"]["data_status"].startswith("离线教学")
    app.radio(key="us_source_mode").set_value("免费来源状态").run()
    assert app.button(key="us_live_backtest").disabled
    assert not any(item.label=="教学策略累计收益" for item in app.metric)
    app.radio(key="us_source_mode").set_value("离线教学样本").run()
    assert app.number_input(key="us_cash").value==5000.
    assert any(item.label=="教学策略累计收益" for item in app.metric)


def test_free_source_failure_stays_visible_and_does_not_become_teaching_data(monkeypatch):
    def fail(*args):
        raise ValueError("测试：来源请求失败")
    monkeypatch.setattr("quant_lab.us_sources.fetch_sina_reference",lambda *args, **kwargs: fail())
    app=AppTest.from_file(APP,default_timeout=30).run()
    navigate(app, "美股研究")
    app.radio(key="us_source_mode").set_value("免费来源状态").run()
    app.button(key="FormSubmitter:us_real_prices-加载真实美股日线").click().run()
    finish_background_jobs(app)
    assert not app.exception
    assert any("来源请求失败" in item.value for item in app.error)
    assert app.button(key="us_live_backtest").disabled
    assert "us_source_observation" not in app.session_state
    assert not app.metric


def test_real_us_prices_refresh_failure_retains_data_and_query_isolates_ai(monkeypatch):
    from datetime import date
    import pandas as pd
    from quant_lab import us_sources
    from quant_lab.refresh import RefreshCache

    calls = []
    def request(symbol):
        calls.append(symbol)
        if len(calls) > 1:
            raise ValueError("offline")
        return pd.DataFrame({"date": pd.to_datetime(["2026-10-27", "2026-10-28"]),
                             "open": [100., 101.], "high": [103., 104.], "low": [99., 100.],
                             "close": [102., 103.], "volume": [1000, 2000]})
    monkeypatch.setattr(us_sources, "_request_sina_daily", request)
    monkeypatch.setattr(us_sources, "_REFERENCE_CACHE", RefreshCache())
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.sidebar.selectbox(key="market_selection").set_value("美股").run()
    assert not app.exception and not calls
    app.date_input(key="us_price_start").set_value(date(2026, 10, 27))
    app.date_input(key="us_price_end").set_value(date(2026, 10, 28))
    app.button(key="FormSubmitter:us_real_prices-加载真实美股日线").click().run()
    finish_background_jobs(app)
    assert not app.exception and not app.error and calls == ["AAPL"]
    assert app.metric[0].value == "103.0000"
    first = app.session_state["us_price_reference"][1].observation
    assert app.session_state["_current_ai_context"]["symbol"] == "AAPL"
    assert app.session_state["_current_ai_context"]["data_status"].startswith("真实美股历史日线")
    app.run()
    app.button(key="FormSubmitter:us_real_prices-加载真实美股日线").click().run()
    finish_background_jobs(app)
    assert calls == ["AAPL"]  # rerender and ordinary load reuse verified memory
    app.button(key="FormSubmitter:us_real_prices-立即更新美股日线").click().run()
    finish_background_jobs(app)
    assert not app.exception and len(calls) == 2 and app.error
    retained = app.session_state["us_price_reference"][1]
    assert retained.observation == first and retained.update_error
    assert app.metric[0].value == "103.0000"
    assert "更新失败" in app.session_state["_current_ai_context"]["data_status"]
    app.text_input(key="us_price_symbol").set_value("MSFT")
    app.button(key="FormSubmitter:us_real_prices-加载真实美股日线").click().run()
    finish_background_jobs(app)
    assert not app.metric
    assert "symbol" not in app.session_state["_current_ai_context"]
    assert app.button(key="us_live_backtest").disabled
