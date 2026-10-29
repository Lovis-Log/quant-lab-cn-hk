"""Small shared helpers for the research workspaces."""

import hashlib

import plotly.graph_objects as go
import streamlit as st

from quant_lab.data import HistoryBundle
from quant_lab import theme


def reset_main_scroll(view, *, key):
    """New pages/lessons begin at their heading; parameter edits keep position."""
    state_key = "_scroll_view_" + key
    if st.session_state.get(state_key) != view:
        st.session_state[state_key] = view
        st.html('<script>requestAnimationFrame(() => requestAnimationFrame(() => {'
                'document.querySelector(".st-key-main_workspace")?.scrollTo({top:0,behavior:"instant"});'
                'document.querySelector(".st-key-workbench_scroller")?.scrollTo({left:0,behavior:"instant"});'
                '}));</script>',
                unsafe_allow_javascript=True)


def bundle_key(bundle: HistoryBundle) -> str:
    digest = hashlib.sha256()
    digest.update(f"{bundle.market}|{bundle.symbol}|{bundle.adjustment}".encode())
    digest.update(bundle.frame.to_csv(index=False).encode("utf-8"))
    return digest.hexdigest()[:16]


def require_history(bundle: HistoryBundle | None) -> bool:
    if bundle is None or bundle.frame.empty:
        st.info("请先在左侧选择股票与日期，并点击“加载真实历史日线”。")
        return False
    return True


def style_figure(fig: go.Figure, height: int = 410) -> go.Figure:
    fig.update_layout(
        uirevision=repr(st.session_state.get("_current_query")),
        height=height, paper_bgcolor=theme.SURFACE, plot_bgcolor=theme.SURFACE,
        font={"color": theme.MUTED, "size": 12, "family": theme.FONT},
        margin={"l": 25, "r": 20, "t": 25, "b": 30},
        hovermode="x unified", legend={"orientation": "h", "y": 1.12},
    )
    fig.update_xaxes(showgrid=True, gridcolor=theme.BORDER, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=theme.BORDER, zeroline=False)
    return fig


def percent(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2%}"
