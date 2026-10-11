"""Plotly charts for the terminal interface."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

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


def _historical_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        height=520,
        margin={"l": 18, "r": 18, "t": 24, "b": 20},
        paper_bgcolor="#151E2D",
        plot_bgcolor="#151E2D",
        font={"color": "#94A3B8", "family": "Arial, sans-serif", "size": 11},
        showlegend=False,
        hovermode="x unified",
        hoverlabel={"bgcolor": "#111827", "font_color": "#F1F5F9"},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#273244", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#273244", zeroline=False)
    fig.update_yaxes(title_text="价格（元/股）", row=1, col=1)
    fig.update_yaxes(title_text="成交量（股）", row=2, col=1)
    fig.update_xaxes(title_text="交易日", row=2, col=1)
    return fig


def _volume_colors(history: pd.DataFrame) -> list[str]:
    # A-share convention: red rises, green falls. First day has no comparison.
    changes = history["close"].diff()
    return [
        "#4F8CFF" if pd.isna(change) else "#F06A78" if change >= 0 else "#24D6A0"
        for change in changes
    ]


def history_price_chart(history: pd.DataFrame) -> go.Figure:
    """Actual unadjusted close and provider volume on two aligned axes."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.055,
        row_heights=[0.75, 0.25],
    )
    fig.add_trace(
        go.Scatter(
            x=history["date"], y=history["close"], mode="lines",
            line={"color": "#4F8CFF", "width": 2},
            name="收盘价",
            hovertemplate="%{x|%Y-%m-%d}<br>收盘 %{y:.2f} 元/股<extra></extra>",
        ), row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=history["date"], y=history["volume"],
            marker_color=_volume_colors(history), opacity=0.8,
            name="成交量",
            hovertemplate="%{x|%Y-%m-%d}<br>成交量 %{y:,.0f} 股<extra></extra>",
        ), row=2, col=1,
    )
    return _historical_layout(fig)


def history_candlestick_chart(history: pd.DataFrame) -> go.Figure:
    """Actual daily OHLC candles with Chinese-market rise/fall colors."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.055,
        row_heights=[0.75, 0.25],
    )
    fig.add_trace(
        go.Candlestick(
            x=history["date"], open=history["open"], high=history["high"],
            low=history["low"], close=history["close"],
            increasing_line_color="#F06A78", increasing_fillcolor="#F06A78",
            decreasing_line_color="#24D6A0", decreasing_fillcolor="#24D6A0",
            name="日 K",
        ), row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=history["date"], y=history["volume"],
            marker_color=_volume_colors(history), opacity=0.8,
            name="成交量",
        ), row=2, col=1,
    )
    fig.update_layout(xaxis_rangeslider_visible=False)
    return _historical_layout(fig)
