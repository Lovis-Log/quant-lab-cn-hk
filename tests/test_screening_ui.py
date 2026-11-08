"""Offline batch UI, saved conditions, and explicit research handoffs."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from conftest import finish_background_jobs
from test_screening import fixture


@pytest.mark.parametrize("market,codes",[("A 股",("600519","000001")),("港股",("00700","00941")),("美股",("AAPL","MSFT"))])
def test_batch_preset_launch_return_without_implicit_work(monkeypatch,market,codes):
    from quant_lab import ui_screening
    from quant_lab.screening import collect_screen
    calls=[]
    item=fixture(market,codes[0])
    def worker(recipe,start,end,namespace,**kwargs):
        from dataclasses import replace
        def fetch(market,code,*args,**opts):
            calls.append((code,opts['force']))
            return replace(item,symbol=code)
        return collect_screen(recipe,start,end,namespace,fetcher=fetch,spacing=0,**kwargs)
    monkeypatch.setattr(ui_screening,"collect_screen",worker)
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=25).run()
    app.sidebar.selectbox(key="market_selection").set_value(market).run()
    app.radio(key="market_view").set_value("批量选股").run()
    app.session_state['history_start']=item.frame.date.iloc[0].date()
    app.session_state['history_end']=item.frame.date.iloc[-1].date()
    app.run()
    app.text_area(key=f"screen_{market}_manual").set_value(','.join(codes))
    next(b for b in app.button if b.label=="运行筛选").click().run()
    finish_background_jobs(app)
    assert not app.exception and not app.error
    assert len(calls)==2
    result=app.session_state['_screen_result'][1]
    assert result.table.matched.all()
    app.text_input(key='screen_preset_title').set_value('示例').run()
    app.button(key='screen_save_preset').click().run()
    assert not app.exception
    assert app.selectbox(key='screen_preset').value=='示例'
    selector=next(m for m in app.multiselect if m.label=='选择命中股票进入研究')
    selector.set_value(list(codes)).run()
    app.button(key='screen_go_比较').click().run()
    assert app.session_state['nav_section']=='多股票比较'
    assert len(calls)==2 and not app.exception
    app.button(key='screen_return_button').click().run()
    assert app.radio(key='market_view').value=='批量选股'
    assert len(calls)==2 and not app.exception
    next(b for b in app.button if b.label=='立即更新并筛选').click().run()
    finish_background_jobs(app)
    assert len(calls)==4 and all(force for _,force in calls[-2:])


def test_empty_screen_offline_boot():
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=20).run()
    app.radio(key='market_view').set_value('批量选股').run()
    assert not app.exception
    assert any('1–20' in i.value for i in app.info)


def test_condition_thresholds_and_preset_load(monkeypatch):
    from quant_lab import ui_screening
    from quant_lab.screening import collect_screen
    item=fixture()
    monkeypatch.setattr(ui_screening,'collect_screen',lambda recipe,start,end,namespace,**opts:collect_screen(recipe,start,end,namespace,fetcher=lambda *a,**k:item,spacing=0,**opts))
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=25).run()
    app.radio(key='market_view').set_value('批量选股').run()
    app.session_state['history_start']=item.frame.date.iloc[0].date()
    app.session_state['history_end']=item.frame.date.iloc[-1].date()
    app.run()
    app.text_area(key='screen_A 股_manual').set_value('600519')
    app.multiselect(key='screen_A 股_enabled').set_value(['return20'])
    next(b for b in app.button if b.label=='应用条件').click().run()
    app.number_input(key='screen_A 股_return20_low').set_value(90.)
    next(b for b in app.button if b.label=='运行筛选').click().run()
    finish_background_jobs(app)
    assert not app.session_state['_screen_result'][1].table.matched.any()
    app.text_input(key='screen_preset_title').set_value('条件方案').run()
    app.button(key='screen_save_preset').click().run()
    app.number_input(key='screen_A 股_return20_low').set_value(0.)
    next(b for b in app.button if b.label=='应用条件').click().run()
    app.button(key='screen_load_preset').click().run()
    assert app.number_input(key='screen_A 股_return20_low').value==90.
    assert not app.exception
