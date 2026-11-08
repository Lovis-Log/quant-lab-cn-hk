"""Explicit course-to-research handoffs; no implicit data or compute requests."""
from copy import deepcopy
import streamlit as st
from quant_lab.course_research import SUPPORTED, build_research_launch
from quant_lab.courses import get_course
from quant_lab.ui_security_picker import render_security_picker
from quant_lab.strategy import STRATEGY_NAMES


def queue_launch(launch):
    keys = ("academy_course_id", "academy_group", "academy_search", "_academy_return_stack")
    snapshot = {key: deepcopy(st.session_state[key]) for key in st.session_state
                if key in keys or key.startswith("academy_parameter_")}
    st.session_state["_course_origin"] = (launch, snapshot)
    st.session_state["_course_pending"] = launch


def queue_return():
    st.session_state["_course_return_pending"] = True


def apply_pending_course_navigation():
    if st.session_state.pop("_course_return_pending", False):
        origin = st.session_state.pop("_course_origin", None)
        if origin:
            st.session_state.update(origin[1])
            st.session_state["nav_section"] = "Quant Academy"
    launch = st.session_state.pop("_course_pending", None)
    if launch is None:
        return
    from quant_lab.ui_comparison import change_comparison_market
    change_comparison_market(launch.market)
    st.session_state["nav_section"] = "多股票比较" if launch.route == "多股票比较" else "研究工作台"
    if launch.route == "多股票比较":
        key = "us_compare_codes" if launch.market == "美股" else "compare_codes"
        st.session_state[key] = ",".join(launch.codes)
        st.session_state["us_compare_baseline" if launch.market == "美股" else "compare_benchmark"] = launch.codes[0]
        st.session_state["_course_comparison_focus"] = launch.course_id
    else:
        st.session_state["research_page"] = launch.route
        st.session_state["us_price_symbol" if launch.market == "美股" else "symbol_"+launch.market] = launch.codes[0]
        st.session_state["us_research_mode"] = "真实行情价格研究"
        if launch.route == "研究实验台":
            st.session_state["lab_mode"] = "当前行情验证"
    st.session_state.update(launch.overrides)


def render_course_origin():
    origin = st.session_state.get("_course_origin")
    if origin and st.session_state.get("nav_section") != "Quant Academy":
        launch = origin[0]
        st.caption(f"来自课程：{get_course(launch.course_id).title}。{launch.note}")
        st.button("返回来源课程", key="course_return", on_click=queue_return)


def render_course_launch(course, value):
    if course.course_id not in SUPPORTED:
        return
    with st.expander("用真实数据研究"):
        market = st.selectbox("研究市场", ("A 股", "港股", "美股"), key="course_launch_market")
        multiple = course.course_id in SUPPORTED[8:]
        key = "course_launch_codes_"+market if multiple else "course_launch_symbol_"+market
        defaults = {"A 股": ("600519", "000001"), "港股": ("00700", "00941"), "美股": ("AAPL", "MSFT")}
        st.session_state.setdefault(key, ",".join(defaults[market]) if multiple else defaults[market][0])
        text = render_security_picker(market, key, multiple=multiple,
                                      label="研究股票（2–10只）" if multiple else "研究股票")
        try:
            launch = build_research_launch(course.course_id, value, market,
                                           tuple(v.strip() for v in text.replace("，", ",").split(",") if v.strip()))
        except ValueError as error:
            st.warning(str(error))
            return
        route_label = {"策略实验室": "策略信号", "研究实验台": "专业验证"}.get(launch.route, launch.route)
        st.write(f"目标：{launch.market}，{', '.join(launch.codes)} → {route_label}")
        st.write(launch.note)
        if launch.overrides:
            labels = {"kind": "策略", "short": "短周期", "long": "长周期", "slip": "滑点（基点）",
                      "slippage": "滑点（基点）", "fraction": "训练比例"}
            st.write({labels.get(k.rsplit('_', 1)[-1], k): STRATEGY_NAMES.get(v, v) if k.endswith("_kind") else v
                      for k, v in launch.overrides.items()})
        st.caption("沿用研究区已有日期范围与价格口径；进入后手动加载行情并运行。")
        if st.button("进入真实研究", key="course_launch", on_click=queue_launch, args=(launch,)):
            st.rerun(scope="app")
