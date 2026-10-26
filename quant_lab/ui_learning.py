"""Interactive Academy page with deliberate separation from market observations."""

import streamlit as st

from quant_lab.learning import LESSONS, lesson_experiment
from quant_lab.knowledge import LESSON_TOPICS
from quant_lab.ui_knowledge import ARTICLE_BY_TOPIC, render_knowledge
import math


@st.fragment
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
    # A fragment rerun does not re-enter render_app: refresh the AI whitelist
    # explicitly so a follow-up never receives the previous lesson's numbers.
    st.session_state["_current_ai_context"] = {
        "page": "Quant Academy", "lesson": choice,
        "data_status": "离线教学实验，不是股票行情。",
        "learning_context": st.session_state["active_learning_context"],
    }
    st.dataframe(frame, width="stretch", hide_index=True)
    st.info(conclusion)
    readings = {}
    current_readings = {}
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
    elif choice == 7:
        current_readings["bias"] = (
            f"当前固定教学样本比较 {int(value)} 组参数。{conclusion}"
            "本课没有单一的‘偏差值’；应比较训练期选出的参数在测试期是否仍成立。"
        )
    for topic in LESSON_TOPICS[choice]:
        render_knowledge(
            topic,
            readings.get(topic),
            key="academy",
            period="当前固定教学样本（不是行情）",
            expanded=True,
            current_reading=current_readings.get(topic),
        )
    st.markdown("#### 思考问题")
    st.write(lesson.question)
    from quant_lab.ui_manual import open_manual_article
    st.button(
        "在使用手册中继续阅读",
        key="academy_to_manual",
        on_click=open_manual_article,
        args=(ARTICLE_BY_TOPIC[LESSON_TOPICS[choice][0]],),
    )
