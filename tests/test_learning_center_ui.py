"""The full learning workflow works offline and returns to preserved research."""

from pathlib import Path
from dataclasses import replace

from streamlit.testing.v1 import AppTest

from quant_lab import learning_store, storage
from test_workspaces import sample_bundle


def widget(app, kind, label):
    return next(w for w in app.get(kind) if w.label == label)


def app_start():
    return AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()


def test_welcome_skip_restart_help_maps_every_page_without_api(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("implicit network call")
    monkeypatch.setattr("quant_lab.ui.fetch_history", no_network)
    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", no_network)
    app = app_start()
    assert not app.exception
    assert not learning_store.load_progress()
    widget(app,"button","跳过首次引导").click().run()
    assert learning_store.load_progress()[("onboarding","welcome")]["status"] == "skipped"
    from quant_lab.guidance import GUIDES
    for page in GUIDES:
        if page == "新手使用指引":
            continue
        app.sidebar.radio(key="nav_page").set_value(page).run()
        widget(app,"button","查看本页使用指南").click().run()
        assert not app.exception and app.sidebar.radio(key="nav_page").value == "新手使用指引"
        assert widget(app,"selectbox","选择页面指南").value == page
        widget(app,"button","返回研究任务 · " + page).click().run()
        assert not app.exception and app.sidebar.radio(key="nav_page").value == page
    app.sidebar.radio(key="nav_page").set_value("新手使用指引").run()
    widget(app,"radio","学习中心分区").set_value("学习进度").run()
    widget(app,"button","重新启动首次引导").click().run()
    assert widget(app,"button","开始入门任务")


def test_course_experiment_quiz_goal_notes_restore_after_restart(monkeypatch):
    app = app_start()
    widget(app,"button","开始入门任务").click().run()
    widget(app,"radio","学习中心分区").set_value("课程与练习").run()
    widget(app,"selectbox","选择交互课程").set_value("drawdown").run()
    assert not learning_store.quiz_attempts()
    widget(app,"slider","低点净值").set_value(80).run()
    widget(app,"button","保存交互实验记录").click().run()
    assert ("course","drawdown") not in learning_store.load_progress()
    widget(app,"number_input","你的数值答案").set_value(-20)
    widget(app,"button","提交课程测验").click().run()
    assert not app.exception
    assert ("course","drawdown") in learning_store.load_progress()
    widget(app,"radio","学习中心分区").set_value("学习进度").run()
    widget(app,"text_input","当前学习目标").input("先掌握回撤再看夏普")
    widget(app,"button","保存学习目标").click().run()
    widget(app,"text_input","学习笔记标题").input("手算回撤")
    widget(app,"text_area","学习笔记内容").input("峰值必须只看过去。")
    widget(app,"button","保存学习笔记").click().run()
    second = app_start()
    second.sidebar.radio(key="nav_page").set_value("新手使用指引").run()
    widget(second,"radio","学习中心分区").set_value("学习进度").run()
    assert not second.exception
    assert widget(second,"text_input","当前学习目标").value == "先掌握回撤再看夏普"
    assert len(learning_store.quiz_attempts()) == 1
    assert storage.list_learning_notes()[0]["content"] == "峰值必须只看过去。"
    widget(second,"button","重置学习进度").click().run()
    assert ("course","drawdown") in learning_store.load_progress()  # No confirmation, no reset.
    widget(second,"checkbox","确认只重置学习进度与测验；保留研究、行情、笔记和密钥").set_value(True)
    widget(second,"button","重置学习进度").click().run()
    assert not second.exception and ("course","drawdown") not in learning_store.load_progress()
    assert learning_store.quiz_attempts() == []
    assert storage.list_learning_notes()[0]["content"] == "峰值必须只看过去。"


def test_offline_candidate_can_complete_selection_but_not_history(monkeypatch):
    monkeypatch.setattr("quant_lab.names.security_name", lambda *args, **kwargs: "")
    app = app_start()
    assert ("task","select_security") not in learning_store.load_progress()
    app.sidebar.selectbox(key="symbol_A 股").set_value("000001").run()
    assert not app.exception
    assert learning_store.load_progress()[("task","select_security")]["details"]["identity_known"]
    assert ("task","load_history") not in learning_store.load_progress()


def test_tasks_use_actual_success_and_help_preserves_parameters(monkeypatch):
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args: sample_bundle())
    app = app_start()
    assert not any(kind == "task" for kind, _ in learning_store.load_progress())
    app.sidebar.button[0].click().run()
    assert learning_store.load_progress()[("task","load_history")]
    app.sidebar.radio(key="nav_page").set_value("策略实验室").run()
    assert learning_store.load_progress()[("task","choose_strategy")]
    app.sidebar.radio(key="nav_page").set_value("历史回测").run()
    app.number_input(key="backtest_short").set_value(5).run()
    app.number_input(key="backtest_long").set_value(20).run()
    widget(app,"number_input","佣金（基点）").set_value(12).run()
    widget(app,"slider","样本内比例").set_value(.65).run()
    widget(app,"button","运行历史回测").click().run()
    audit = app.session_state["backtest_result"].audit_id
    widget(app,"text_area","学习笔记").input("成本提高后仍需新样本验证。").run()
    widget(app,"button","查看本页使用指南").click().run()
    widget(app,"button","返回研究任务 · 历史回测").click().run()
    assert not app.exception
    assert app.number_input(key="backtest_short").value == 5
    assert widget(app,"number_input","佣金（基点）").value == 12
    assert widget(app,"slider","样本内比例").value == .65
    assert app.session_state["backtest_result"].audit_id == audit
    assert widget(app,"text_area","学习笔记").value == "成本提高后仍需新样本验证。"
    widget(app,"button","保存实验").click().run()
    assert learning_store.load_progress()[("task","save_research")]["details"]["has_judgment"]


def test_professional_mode_and_teaching_draft_never_send_or_change_math(monkeypatch):
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args: sample_bundle())
    def no_client(*args, **kwargs):
        raise AssertionError("paid client instantiated without send")
    monkeypatch.setattr("quant_lab.ui_deepseek.DeepSeekClient", no_client)
    app = app_start()
    app.sidebar.button[0].click().run()
    app.sidebar.radio(key="nav_page").set_value("统计与机器学习").run()
    widget(app,"button","运行时间序列线性回归").click().run()
    result = app.session_state["model_result"]
    app.toggle(key="learning_mode").set_value(False).run()
    assert not app.exception and app.session_state["model_result"].mae == result.mae
    assert app.session_state["active_analysis_context"]["linear_model"]["mae"] == result.mae
    app.sidebar.radio(key="nav_page").set_value("新手使用指引").run()
    widget(app,"radio","学习中心分区").set_value("课程与练习").run()
    widget(app,"button","使用 DeepSeek 辅导这节课").click().run()
    assert not app.exception
    assert widget(app,"radio","回答模式").value == "教学辅导模式"
    assert "不要直接给出" in widget(app,"text_area","问题（确认后发送）").value


def test_demo_and_failed_data_do_not_complete_real_history_task(monkeypatch):
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args: replace(sample_bundle(), source="明确模拟教学数据"))
    app = app_start()
    app.sidebar.button[0].click().run()
    assert ("task","load_history") not in learning_store.load_progress()
