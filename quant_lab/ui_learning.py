"""Interactive Academy page with deliberate separation from market observations."""

import streamlit as st

from quant_lab.learning import LESSONS, lesson_experiment
from quant_lab.knowledge import LESSON_TOPICS
from quant_lab.ui_knowledge import render_knowledge
import math


def render_academy() -> None:
    st.subheader("Quant Academy · 金融数学实验室")
    st.caption("先用可手算的例子理解公式，再回到真实行情检验。下方实验全是固定教学数据。")
    choice = st.selectbox("选择课程", range(len(LESSONS)), key="academy_lesson", format_func=lambda i: f"{i+1}. {LESSONS[i].title}")
    lesson = LESSONS[choice]
    st.markdown("#### Python 实现")
    st.code(lesson.code, language="python")
    st.markdown("#### 调参数试一试")
    if lesson.step < 1:
        bounds = (float(lesson.minimum), float(lesson.maximum),
                  float(lesson.default), float(lesson.step))
    else:
        bounds = (int(lesson.minimum), int(lesson.maximum),
                  int(lesson.default), int(lesson.step))
    value = st.slider(lesson.parameter, *bounds)
    frame, conclusion = lesson_experiment(choice, value)
    st.session_state["active_learning_context"] = {"course_id": LESSON_TOPICS[choice][0],
        "topic": lesson.title, "parameter": value, "experiment_conclusion": conclusion,
        "status": "固定教学样本，不是股票行情"}
    st.dataframe(frame, width="stretch", hide_index=True)
    st.info(conclusion)
    readings = {}
    if choice == 0:
        readings = {"simple_return": float(frame["本金"].iloc[-1]/100-1), "compound": float(frame["本金"].iloc[-1]/100-1)}
    elif choice == 1:
        readings["moving_average"] = float(frame["均线"].iloc[-1])
    elif choice == 2:
        readings = {"variance": float(frame["样本值"].var(ddof=1)), "std": float(frame["样本值"].std(ddof=1))}
    elif choice == 3:
        readings["volatility"] = float(frame["演示价格"].pct_change().dropna().std(ddof=1)*math.sqrt(252))
    elif choice == 4:
        readings["drawdown"] = float(frame["回撤"].min())
    elif choice == 5:
        daily = frame["演示收益率"]
        readings["sharpe"] = float((daily.mean()-value/100)/daily.std(ddof=1)*math.sqrt(252))
    elif choice == 6:
        readings["correlation"] = float(frame["X"].corr(frame["Y"]))
    for topic in LESSON_TOPICS[choice]:
        render_knowledge(topic, readings.get(topic), key="academy", period="当前固定教学样本（不是行情）", expanded=True)
    st.markdown("#### 思考问题")
    st.write(lesson.question)
    from quant_lab.ui_guidance import navigate
    st.button("到学习中心保存实验与测验", key="academy_to_center", on_click=navigate,
        args=("新手使用指引",), kwargs={"section": "课程与练习", "course": LESSON_TOPICS[choice][0]})
