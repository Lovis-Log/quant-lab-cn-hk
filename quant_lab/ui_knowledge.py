"""Shared knowledge entry used by metrics, Academy and the AI prompt draft."""

from dataclasses import dataclass
from typing import Sequence

import streamlit as st

from quant_lab.knowledge import KNOWLEDGE, interpret


ARTICLE_BY_TOPIC = {
    "simple_return": "simple_return",
    "compound": "compound_return",
    "moving_average": "moving_average",
    "variance": "variance",
    "std": "standard_deviation",
    "volatility": "volatility",
    "drawdown": "maximum_drawdown",
    "sharpe": "sharpe_ratio",
    "correlation": "correlation",
    "costs": "trading_costs",
    "slippage": "slippage_liquidity_market_impact",
    "bias": "lookahead_bias",
}


@dataclass(frozen=True, slots=True)
class KnowledgePoint:
    """One explanation inside a result-local knowledge group."""

    topic: str
    value: object = None
    observations: int | None = None
    period: str = "所选样本区间"
    expanded: bool = False
    current_reading: str | None = None


def render_knowledge(
    topic: str,
    value=None,
    *,
    key="",
    observations=None,
    period="所选样本区间",
    expanded=False,
    current_reading: str | None = None,
):
    if not st.session_state.get("learning_mode", True):
        return
    item = KNOWLEDGE[topic]
    with st.expander(f"知识解释：{item.title}", expanded=expanded):
        for label, content in (("是什么", item.definition), ("刻画什么", item.feature),
                               ("为什么重要", item.importance)):
            st.markdown(f"**{label}**：{content}")
        st.markdown("**怎么计算**")
        st.latex(item.formula)
        st.write(item.symbols)
        st.markdown(f"**手算例子**：{item.example}")
        reading = current_reading or interpret(topic, value, observations=observations, period=period)
        st.markdown(f"**当前结果怎么读**：{reading}")
        st.markdown(f"**局限和常见误读**：{item.limitation}")
        st.markdown(f"**小实验或思考题**：{item.question}")
        if st.button("向 AI 追问", key=f"knowledge_ai_{key}_{topic}"):
            from quant_lab.ui_deepseek import open_ai_followup
            open_ai_followup(f"请进一步解释{item.title}，先讲直觉再给一个手算例子。", item.title)
            st.rerun()
        article_id = ARTICLE_BY_TOPIC.get(topic)
        if article_id:
            from quant_lab.ui_manual import open_manual_article
            st.button(
                "在使用手册中阅读",
                key=f"knowledge_manual_{key}_{topic}",
                on_click=open_manual_article,
                args=(article_id,),
            )


def _toggle_knowledge_group(state_key: str) -> None:
    st.session_state[state_key] = not st.session_state.get(state_key, False)


def render_knowledge_group(
    points: Sequence[KnowledgePoint],
    *,
    key: str,
) -> None:
    """Render at most two explanations until this result block is expanded."""
    if not st.session_state.get("learning_mode", True) or not points:
        return
    state_key = f"knowledge_group_expanded_{key}"
    expanded = st.session_state.get(state_key, False)
    visible = points if expanded else points[:2]
    for point in visible:
        render_knowledge(
            point.topic,
            point.value,
            key=key,
            observations=point.observations,
            period=point.period,
            expanded=point.expanded,
            current_reading=point.current_reading,
        )
    remaining = len(points) - 2
    if remaining > 0:
        st.button(
            "收起详细解释" if expanded else f"显示更多（剩余 {remaining} 项）",
            key=f"knowledge_group_toggle_{key}",
            on_click=_toggle_knowledge_group,
            args=(state_key,),
        )
