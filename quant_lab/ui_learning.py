"""Offline Academy: searchable curriculum, authored lessons and controlled labs."""

import streamlit as st

from quant_lab.courses import (COURSES, COURSE_BY_ID, COURSE_NUMBERS, GROUPS,
                               LEGACY_COURSE_IDS, get_course, run_experiment,
                               search_courses, validated_courses)
from quant_lab.charts import course_chart
from quant_lab.ui_helpers import reset_main_scroll
from quant_lab.ui_knowledge import render_knowledge


def _label(course_id):
    return f"{COURSE_NUMBERS[course_id]:02d} · {COURSE_BY_ID[course_id].title}"


def _clear_return_history():
    st.session_state.pop("_academy_return_stack", None)


def _choose_course(course_id, remember=False):
    if remember and st.session_state.get("academy_course_id") != course_id:
        current = st.session_state["academy_course_id"]
        history = st.session_state.setdefault("_academy_return_stack", [])
        history.append({
            "course_id": current,
            "query": st.session_state.get("academy_search", ""),
            "group": st.session_state.get("academy_group", "全部课程"),
            "parameter": st.session_state.get(f"academy_parameter_{current}"),
        })
        del history[:-32]
    elif not remember:
        _clear_return_history()
    st.session_state["academy_search"] = ""
    st.session_state["academy_group"] = "全部课程"
    st.session_state["academy_course_id"] = course_id


def _return_to_course():
    history = st.session_state.get("_academy_return_stack", [])
    if not history:
        return
    previous = history.pop()
    course_id = previous["course_id"]
    st.session_state["academy_course_id"] = course_id
    st.session_state["academy_search"] = previous["query"]
    st.session_state["academy_group"] = previous["group"]
    if previous["parameter"] is not None:
        st.session_state[f"academy_parameter_{course_id}"] = previous["parameter"]


def _clear_context():
    st.session_state["active_learning_context"] = None
    st.session_state.pop("ai_followup_context", None)
    st.session_state.pop("ai_followup_query", None)
    st.session_state["_current_ai_context"] = {
        "page": "Quant Academy", "data_status": "课程检索，无当前实验。"}


def _migrate_selection():
    # Numeric selections from the original eight lessons must not be interpreted
    # as positions in the new curriculum. New users start at financial variables.
    if "academy_course_id" not in st.session_state:
        legacy = st.session_state.get("academy_lesson")
        st.session_state["academy_course_id"] = (
            LEGACY_COURSE_IDS[legacy] if isinstance(legacy, int) and 0 <= legacy < 8
            else COURSES[0].course_id)
    if st.session_state.get("academy_group") not in ("全部课程", *GROUPS):
        st.session_state["academy_group"] = "全部课程"


@st.fragment
def render_academy() -> None:
    try:
        validated_courses()
    except ValueError as error:
        _clear_context()
        st.error(f"课程内容不可用：{error}")
        return
    _migrate_selection()
    with st.container(key="academy_workspace"):
        catalog, reading = st.columns([1, 3.35], gap="large")
        with catalog, st.container(key="academy_catalog"):
            st.subheader("Quant Academy")
            st.caption("28节 · 从金融数据入门到研究报告")
            query = st.text_input("搜索课程", key="academy_search", placeholder="课程名称、Python或金融关键词",
                                  on_change=_clear_return_history)
            group = st.radio("课程专题", ("全部课程", *GROUPS), key="academy_group", label_visibility="collapsed",
                             on_change=_clear_return_history)
            available = search_courses(query, group)
            if not available:
                st.info("没有匹配的课程，请换一个关键词。")
                _clear_context()
                return
            ids = [course.course_id for course in available]
            if st.session_state["academy_course_id"] not in ids:
                st.session_state["academy_course_id"] = ids[0]
            course_id = st.selectbox("选择课程", ids, key="academy_course_id", format_func=_label,
                                     on_change=_clear_return_history)
            st.caption(f"{len(available)} / {len(COURSES)} 节可用课程 · 固定教学样本")
        with reading, st.container(key="academy_reading"):
            course = get_course(course_id)
            st.caption(course.group)
            st.title(_label(course_id))
            history = st.session_state.get("_academy_return_stack", [])
            if history:
                st.button(f"← 返回 {_label(history[-1]['course_id'])}", key="academy_return",
                          on_click=_return_to_course)
            st.caption("固定教学样本 · 可离线运行 · 不记录学习进度")
            st.markdown(f"**学习目标**：{course.objective}")
            if course.prerequisites:
                st.caption("建议先修（可直接跳转，不限制学习顺序）")
                for prerequisite in course.prerequisites:
                    st.button(_label(prerequisite), key=f"academy_prerequisite_{prerequisite}",
                              on_click=_choose_course, args=(prerequisite, True))
            else:
                st.caption("先修知识：高中四则运算与百分比，无需Python基础。")
            st.write(course.intuition)
            st.markdown(f"**量化场景**：{course.scenario}")
            st.latex(course.formula)
            st.caption(course.units)
            st.markdown(f"**手算例子**：{course.example}")
            _render_experiment(course)
            reset_main_scroll(course_id, key="lesson")


def _render_experiment(course):
    parameter = course.parameter
    pkey = f"academy_parameter_{course.course_id}"
    if pkey not in st.session_state and course.legacy_index is not None:
        old_value = st.session_state.get(f"academy_parameter_{course.legacy_index}")
        if isinstance(old_value, (int, float)) and parameter.minimum <= old_value <= parameter.maximum:
            st.session_state[pkey] = old_value
    number = float if parameter.step < 1 else int
    chart_area = st.empty()
    with st.container(key="academy_experiment"):
        controls, table = st.columns([1, 1.2], gap="medium")
        with controls:
            st.markdown("#### 参数实验")
            options = dict(min_value=number(parameter.minimum), max_value=number(parameter.maximum),
                           step=number(parameter.step), key=pkey)
            if pkey not in st.session_state:
                options["value"] = number(parameter.default)
            value = st.slider(parameter.label, **options)
            try:
                result = run_experiment(course.course_id, {"value": value})
            except ValueError as error:
                _clear_context()
                st.error(f"教学实验未完成：{error}")
                return
            st.info(result.conclusion)
        with table:
            st.markdown("#### 教学数据与结果")
            st.dataframe(result.table, width="stretch", hide_index=True,
                         height=min(280, 38 + 35 * len(result.table)),
                         column_config={name: st.column_config.NumberColumn(name, format="percent")
                                        for name in result.percent_columns})
    with chart_area.container():
        st.plotly_chart(course_chart(result, course.course_id), width="stretch", theme=None,
                        key=f"academy_chart_{course.course_id}",
                        config={"displaylogo": False, "scrollZoom": False})
    st.markdown(f"**结果解释**：{course.interpretation}")
    st.markdown(f"**常见错误**：{course.mistakes}")
    context = {"course_id": course.course_id, "topic": course.title, "parameter": value,
               "experiment_conclusion": result.conclusion, "status": "固定教学样本，不是股票行情"}
    followup = st.session_state.get("ai_followup_context")
    if followup and followup.get("learning_context") != context:
        st.session_state.pop("ai_followup_context", None)
        st.session_state.pop("ai_followup_query", None)
    st.session_state["active_learning_context"] = context
    st.session_state["_current_ai_context"] = {
        "page": "Quant Academy", "lesson": course.course_id,
        "data_status": "离线教学实验，不是股票行情。", "learning_context": context}
    with st.expander("Python 实现 · 逐行解释"):
        st.code(f"parameter = {value!r}  # 当前滑块值\n" + course.code, language="python")
        for note in course.code_notes:
            st.write(note)
    for topic in course.knowledge:
        render_knowledge(topic, result.knowledge_values.get(topic), key="academy", lazy=True,
                         rerun_on_manual=True,
                         period="当前固定教学样本（不是行情）",
                         current_reading=result.knowledge_readings.get(topic))
    if result.report:
        with st.expander("核对原表与教学报告"):
            st.code(result.report, language="json" if course.course_id == "research_archive" else None)
    with st.expander("思考题与参考答案"):
        st.write(course.question)
        st.write(course.answer)
    position = COURSE_NUMBERS[course.course_id] - 1
    previous, following = st.columns(2)
    previous.button("上一课", key="academy_previous", disabled=position == 0,
                    on_click=_choose_course, args=(COURSES[max(0, position-1)].course_id,))
    following.button("下一课", key="academy_next", disabled=position == len(COURSES)-1,
                     on_click=_choose_course, args=(COURSES[min(len(COURSES)-1, position+1)].course_id,))
    from quant_lab.ui_manual import open_manual_article
    if st.button("在使用手册中继续阅读", key="academy_to_manual", on_click=open_manual_article,
                 args=(course.articles[0],)):
        st.rerun(scope="app")
    if len(course.articles) > 1:
        with st.expander("更多深入阅读"):
            from quant_lab.manual_content import load_manual_content
            library = load_manual_content()
            titles = {article.id: article.title for article in library.articles}
            for article_id in course.articles[1:]:
                if st.button(titles[article_id], key=f"academy_article_{article_id}",
                             on_click=open_manual_article, args=(article_id,)):
                    st.rerun(scope="app")
