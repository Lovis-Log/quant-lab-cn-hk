"""Shared knowledge entry used by metrics, Academy and the AI prompt draft."""

import streamlit as st

from quant_lab.knowledge import KNOWLEDGE, interpret


def render_knowledge(topic: str, value=None, *, key="", observations=None, period="所选样本区间", expanded=False):
    item = KNOWLEDGE[topic]
    with st.expander(f"知识解释：{item.title}", expanded=expanded):
        for label, content in (("是什么", item.definition), ("刻画什么", item.feature),
                               ("为什么重要", item.importance)):
            st.markdown(f"**{label}**：{content}")
        st.markdown("**怎么计算**")
        st.latex(item.formula)
        st.write(item.symbols)
        st.markdown(f"**手算例子**：{item.example}")
        reading = interpret(topic, value, observations=observations, period=period)
        st.markdown(f"**当前结果怎么读**：{reading}")
        st.markdown(f"**局限和常见误读**：{item.limitation}")
        st.markdown(f"**小实验或思考题**：{item.question}")
        if st.button("向 AI 追问", key=f"knowledge_ai_{key}_{topic}"):
            from quant_lab.ui_deepseek import open_ai_followup
            open_ai_followup(f"请进一步解释{item.title}，先讲直觉再给一个手算例子。", item.title)
            st.rerun()
        from quant_lab.guidance import COURSES
        if topic in COURSES:
            from quant_lab.ui_guidance import navigate
            st.button("进入对应课程", key=f"knowledge_course_{key}_{topic}", on_click=navigate,
                args=("新手使用指引",), kwargs={"section": "课程与练习", "course": topic})
