"""US workspace is offline by default, keeps provenance, and never opens live trades."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from conftest import finish_background_jobs


APP=Path(__file__).resolve().parents[1]/"app.py"


def test_us_workspace_offline_run_cash_ledger_export_and_parameter_retention(monkeypatch):
    calls=[]
    monkeypatch.setattr("quant_lab.us_sources.inspect_sina_prices",lambda *args:calls.append(args))
    app=AppTest.from_file(APP,default_timeout=30).run()
    app.sidebar.radio(key="nav_page").set_value("美股研究").run()
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
    monkeypatch.setattr("quant_lab.us_sources.inspect_sina_prices",fail)
    app=AppTest.from_file(APP,default_timeout=30).run()
    app.sidebar.radio(key="nav_page").set_value("美股研究").run()
    app.radio(key="us_source_mode").set_value("免费来源状态").run()
    app.button(key="FormSubmitter:us_source_check-核验免费日线覆盖").click().run()
    finish_background_jobs(app)
    assert not app.exception
    assert any("来源请求失败" in item.value for item in app.error)
    assert app.button(key="us_live_backtest").disabled
    assert "us_source_observation" not in app.session_state
    assert not app.metric
