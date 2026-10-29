"""Research UI stays local, binds inputs and versions, and compares real archives."""

from pathlib import Path
from dataclasses import replace

from streamlit.testing.v1 import AppTest
from conftest import navigate

from conftest import finish_background_jobs
from test_research_validation import prepared
from quant_lab.data import HistoryBundle
from quant_lab.source_rights import TEACHING_RETENTION
from quant_lab.storage import list_experiments
from quant_lab.deepseek import safe_context


APP=Path(__file__).resolve().parents[1]/"app.py"


def loaded_lab(monkeypatch,retained=True):
    inputs=prepared()
    from datetime import datetime,timezone
    bundle=HistoryBundle(inputs.raw,"A 股","600519","固定教学样本","CNY","",datetime(2026,1,1,tzinfo=timezone.utc),
        retention=TEACHING_RETENTION if retained else replace(TEACHING_RETENTION,allowed=False))
    monkeypatch.setattr("quant_lab.ui.fetch_history",lambda *args,**kwargs:bundle)
    app=AppTest.from_file(APP,default_timeout=30).run()
    app.sidebar.button[0].click().run()
    finish_background_jobs(app)
    navigate(app, "研究实验台")
    return app


def run_lab(app):
    app.button(key="FormSubmitter:lab_validation_parameters-运行研究验证").click().run()
    finish_background_jobs(app,timeout=30)
    assert not app.exception and not app.error
    return app


def test_lab_run_save_two_versions_and_compare_archives(monkeypatch):
    app=run_lab(loaded_lab(monkeypatch))
    assert any(item.label=="滚动样本外收益" for item in app.metric)
    assert app.session_state["lab_result"][3] is not None
    context=safe_context(app.session_state["_current_ai_context"])
    assert "research_validation" in context["statistics"] and "raw_history" not in str(context)
    app.button(key="lab_save").click().run()
    app.number_input(key="lab_long").set_value(20)
    run_lab(app)
    app.button(key="lab_save").click().run()
    assert len(list_experiments())==2
    shelf=tuple(app.session_state["lab_shelf"])
    assert len(shelf)==2
    app.multiselect(key="lab_session_selection").set_value(list(shelf)).run()
    assert not app.exception
    app.session_state["lab_shelf"].pop(shelf[0])
    app.run()
    assert not app.exception and app.multiselect(key="lab_session_selection").value==[shelf[1]]
    app.radio(key="lab_mode").set_value("存档实验比较").run()
    app.multiselect(key="lab_saved_selection").set_value([1,2]).run()
    app.button(key="lab_compare_saved").click().run()
    finish_background_jobs(app,timeout=30)
    assert not app.exception and not app.error
    assert app.session_state["lab_saved_comparison"][1].directly_comparable
    assert "私人笔记" in app.session_state["_current_ai_context"]["data_status"]
    app.button(key="lab_replay_validation").click().run()
    finish_background_jobs(app,timeout=30)
    assert not app.exception and not app.error
    assert len(app.session_state["lab_archive_replay_result"][1].folds)>0


def test_unlicensed_lab_remains_session_only(monkeypatch):
    app=run_lab(loaded_lab(monkeypatch,retained=False))
    assert app.session_state["lab_result"][3] is None
    assert not any(item.key=="lab_save" for item in app.button)
    assert any("来源留存许可未通过" in item.value for item in app.caption)
    assert not list_experiments()
