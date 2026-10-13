"""Interactive Academy page with deliberate separation from market observations."""

import streamlit as st

from quant_lab.learning import LESSONS, lesson_experiment


def render_academy() -> None:
    st.subheader("Quant Academy · 金融数学实验室")
    st.caption("先用可手算的例子理解公式，再回到真实行情检验。下方实验全是固定教学数据。")
    choice = st.selectbox("选择课程", range(len(LESSONS)), format_func=lambda i: f"{i+1}. {LESSONS[i].title}")
    lesson = LESSONS[choice]
    st.markdown("#### 直觉")
    st.write(lesson.intuition)
    st.markdown("#### 公式")
    st.latex(lesson.formula)
    st.markdown("#### 手算例子")
    st.write(lesson.example)
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
    st.dataframe(frame, width="stretch", hide_index=True)
    st.info(conclusion)
    st.markdown("#### 思考问题")
    st.write(lesson.question)
