"""Course mappings never reinterpret teaching prices or weights as market facts."""
import pytest
from streamlit.testing.v1 import AppTest
from quant_lab.course_research import SUPPORTED, build_research_launch
from quant_lab.courses import get_course


@pytest.mark.parametrize("market,codes", [("A 股", ("600519", "000001")), ("港股", ("00700", "00941")), ("美股", ("AAPL", "MSFT"))])
@pytest.mark.parametrize("course_id", SUPPORTED)
def test_all_course_market_mappings(course_id, market, codes):
    course = get_course(course_id)
    launch = build_research_launch(course_id, course.parameter.default, market,
                                   codes if course_id in SUPPORTED[8:] else codes[:1])
    assert launch.market == market and launch.note
    assert (launch.route == "多股票比较") == (course_id in SUPPORTED[8:])
    if course_id in {"next_open", "bias", "walk_forward", "resampling_stress", *SUPPORTED[8:]}:
        assert not launch.overrides


def test_mapping_boundaries_and_semantics():
    args = ("A 股", ("600519",))
    assert not build_research_launch("moving_average", 2, *args).overrides
    assert build_research_launch("moving_average", 6, *args).overrides["strategy_long"] == 6
    assert not build_research_launch("temporal_split", 3, *args).overrides
    assert build_research_launch("temporal_split", 7, *args).overrides["lab_fraction"] == .7
    assert build_research_launch("execution_costs", 25, *args).overrides["cost_A 股_slippage"] == 25
    with pytest.raises(ValueError):
        build_research_launch("moving_average", 100, *args)
    with pytest.raises(ValueError):
        build_research_launch("correlation", 4, "美股", ("AAPL", "AAPL"))


def test_launch_return_preserves_course_state_and_is_consumed_once():
    app = AppTest.from_string('''
import streamlit as st
from quant_lab.ui_course_research import apply_pending_course_navigation, queue_launch, queue_return
from quant_lab.course_research import build_research_launch
apply_pending_course_navigation()
st.session_state.setdefault("academy_course_id", "dual_trend")
st.session_state.setdefault("academy_group", "专题原值")
st.session_state.setdefault("academy_search", "均线")
st.session_state.setdefault("academy_parameter_dual_trend", 4)
st.session_state.setdefault("_academy_return_stack", [{"course_id":"moving_average"}])
st.button("go", on_click=queue_launch, args=(build_research_launch("dual_trend",4,"美股",("AAPL",)),))
st.button("back", on_click=queue_return)
''').run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["us_price_signal_short"] == 4
    app.session_state["us_price_signal_short"] = 3
    app.run()
    assert app.session_state["us_price_signal_short"] == 3
    app.button[1].click().run()
    assert app.session_state["nav_section"] == "Quant Academy"
    assert app.session_state["academy_search"] == "均线"
    assert app.session_state["academy_parameter_dual_trend"] == 4
    assert app.session_state["_academy_return_stack"] == [{"course_id":"moving_average"}]


def test_real_academy_launch_and_return_without_jobs():
    from pathlib import Path
    from conftest import navigate
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=25).run()
    navigate(app, "Quant Academy")
    app.selectbox(key="academy_course_id").set_value("dual_trend").run()
    app.slider(key="academy_parameter_dual_trend").set_value(4).run()
    app.button(key="course_launch").click().run()
    assert not app.exception
    assert app.session_state["research_page"] == "策略实验室"
    assert app.selectbox(key="strategy_kind").value == "dual_ma" if any(v.key=="strategy_kind" for v in app.selectbox) else True
    assert not any(k in app.session_state["_task_tickets"] for k in ("history", "backtest", "comparison_data"))
    app.button(key="course_return").click().run()
    assert app.selectbox(key="academy_course_id").value == "dual_trend"
    assert app.slider(key="academy_parameter_dual_trend").value == 4
