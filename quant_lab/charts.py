"""Plotly charts for the terminal interface."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from quant_lab.demo_data import make_layout_preview


def demo_chart() -> go.Figure:
    """Render an explicitly simulated, unitless chart preview."""
    sample = make_layout_preview()
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.055,
        row_heights=[0.76, 0.24],
    )
    fig.add_trace(
        go.Scatter(
            x=sample["演示序号"],
            y=sample["模拟指数"],
            mode="lines",
            line={"color": "#24D6A0", "width": 2},
            name="模拟指数 · 无单位",
            hovertemplate="序号 %{x}<br>模拟指数 %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=sample["演示序号"],
            y=sample["模拟活动量"],
            marker_color="#4F8CFF",
            opacity=0.55,
            name="模拟活动量 · 无单位",
            hovertemplate="序号 %{x}<br>模拟活动量 %{y}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        height=520,
        margin={"l": 18, "r": 18, "t": 30, "b": 20},
        paper_bgcolor="#151E2D",
        plot_bgcolor="#151E2D",
        font={"color": "#94A3B8", "family": "Arial, sans-serif", "size": 11},
        hovermode="x unified",
        showlegend=False,
        bargap=0.42,
        hoverlabel={"bgcolor": "#111827", "font_color": "#F1F5F9"},
        annotations=[
            {
                "text": "SIMULATED · UI PREVIEW",
                "xref": "paper",
                "yref": "paper",
                "x": 0.99,
                "y": 0.99,
                "xanchor": "right",
                "showarrow": False,
                "font": {"color": "#718096", "size": 11},
            }
        ],
    )
    fig.update_xaxes(
        title_text="演示序号（非交易日期）",
        showgrid=True,
        gridcolor="#273244",
        zeroline=False,
        tickfont={"color": "#728097"},
        row=2,
        col=1,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#273244",
        zeroline=False,
        tickfont={"color": "#728097"},
        row=1,
        col=1,
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        tickfont={"color": "#728097"},
        row=2,
        col=1,
    )
    return fig
