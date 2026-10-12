"""Small shared helpers for the research workspaces."""

import hashlib

import plotly.graph_objects as go
import streamlit as st

from quant_lab.data import HistoryBundle


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
        height=height, paper_bgcolor="#151E2D", plot_bgcolor="#151E2D",
        font={"color": "#94A3B8", "size": 11},
        margin={"l": 25, "r": 20, "t": 25, "b": 30},
        hovermode="x unified", legend={"orientation": "h", "y": 1.12},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#273244", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#273244", zeroline=False)
    return fig


def percent(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2%}"
