"""A real background comparison/cash path with isolated preferences and errors."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from conftest import finish_background_jobs
from test_comparison_cash import frame,fetcher
from quant_lab.workspaces import WorkspaceStore


APP=Path(__file__).resolve().parents[1]/"app.py"


def test_comparison_and_cash_run_offline_then_failed_refresh_keeps_old_result(monkeypatch):
    import numpy as np
    calls=[]
    data={code:frame(100+i*5+np.arange(60)*.1+np.sin(np.arange(60)+i)) for i,code in enumerate(("600519","000001","600036"))}
    monkeypatch.setattr("quant_lab.comparison.fetch_history_cached",fetcher(data,calls))
    app=AppTest.from_file(APP,default_timeout=30).run()
    app.sidebar.radio(key="nav_page").set_value("多股票比较").run()
    assert not app.exception and not calls
    app.button(key="FormSubmitter:comparison_parameters-加载比较").click().run()
    finish_background_jobs(app,timeout=25)
    assert not app.exception and not app.error
    saved=app.session_state["comparison_result"]
    assert saved[2].closes.shape==(60,3) and len(calls)==3
    app.button(key="FormSubmitter:cash_portfolio_parameters-运行现金持仓组合").click().run()
    finish_background_jobs(app,timeout=25)
    assert not app.exception and not app.error
    research=app.session_state["cash_portfolio_result"][1]
    assert len(research.runs)==2 and all(run.equity.cash.ge(0).all() for run in research.runs.values())
    assert app.session_state["_current_ai_context"]["data_fingerprint"]==saved[1].fingerprint
    def fail(*args,**kwargs):raise ValueError("测试：上游限频")
    monkeypatch.setattr("quant_lab.comparison.fetch_history_cached",fail)
    app.button(key="FormSubmitter:comparison_parameters-立即更新比较").click().run()
    finish_background_jobs(app)
    assert not app.exception and any("上游限频" in item.value for item in app.error)
    assert app.session_state["comparison_result"][1].fingerprint==saved[1].fingerprint


def test_preset_apply_save_restore_in_new_session_without_network(monkeypatch):
    calls=[]
    monkeypatch.setattr("quant_lab.comparison.fetch_history_cached",lambda *args,**kwargs:calls.append(args))
    app=AppTest.from_file(APP,default_timeout=30).run()
    app.sidebar.selectbox(key="workspace_name").set_value("多股票比较").run()
    app.sidebar.button(key="workspace_apply").click().run()
    assert app.session_state["nav_page"]=="多股票比较"
    assert app.session_state["manual_panel_open"] is False and not calls and not app.exception
    app.sidebar.button(key="workspace_save").click().run()
    assert WorkspaceStore().load()["active"]=="多股票比较"
    restarted=AppTest.from_file(APP,default_timeout=30).run()
    assert restarted.session_state["nav_page"]=="多股票比较"
    assert not restarted.exception and not calls


def test_watch_quality_and_failed_refresh_retain_original_success_clock(monkeypatch):
    from datetime import datetime,date,timezone
    from dataclasses import replace
    from quant_lab.market_data import MarketSnapshot
    from quant_lab.storage import add_watchlist
    add_watchlist("A 股","600519")
    quote=MarketSnapshot("A 股","600519",10.,date(2026,1,5),datetime(2026,1,5,8,tzinfo=timezone.utc),
                         "教学来源","CNY",quality_status="测试质量：已校验")
    def failed(items):return {item:replace(quote,cached=True,update_error="测试更新失败",update_result="请求失败") for item in items},{}
    monkeypatch.setattr("quant_lab.ui_terminal.snapshot_batch",failed)
    app=AppTest.from_string('''
import streamlit as st
from quant_lab.ui_terminal import render_watchlist
st.session_state.setdefault("refresh_enabled",False)
render_watchlist("A 股","600519")
''',default_timeout=10).run()
    app.button(key="watch_refresh").click().run()
    finish_background_jobs(app)
    assert not app.exception
    table=app.dataframe[0].value
    assert table.loc[0,"数据质量"]=="测试质量：已校验"
    assert "2026-01-05" in table.loc[0,"上次成功获取时间"]
    assert table.loc[0,"更新状态"]=="上次更新失败"
