"""Plotly charts for the terminal interface."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from quant_lab.demo_data import make_layout_preview
from quant_lab.theme import SURFACE, BORDER, TEXT, MUTED, ACCENT, UP, DOWN, AMBER, FONT


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
            line={"color": ACCENT, "width": 2},
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
            marker_color=ACCENT,
            opacity=0.55,
            name="模拟活动量 · 无单位",
            hovertemplate="序号 %{x}<br>模拟活动量 %{y}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        height=360,
        margin={"l": 18, "r": 18, "t": 30, "b": 20},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"color": MUTED, "family": FONT, "size": 11},
        hovermode="x unified",
        showlegend=False,
        bargap=0.42,
        hoverlabel={"bgcolor": "#181B1E", "font_color": TEXT},
        annotations=[
            {
                "text": "SIMULATED · UI PREVIEW",
                "xref": "paper",
                "yref": "paper",
                "x": 0.99,
                "y": 0.99,
                "xanchor": "right",
                "showarrow": False,
                "font": {"color": MUTED, "size": 11},
            }
        ],
    )
    fig.update_xaxes(
        title_text="演示序号（非交易日期）",
        showgrid=True,
        gridcolor=BORDER,
        zeroline=False,
        tickfont={"color": MUTED},
        row=2,
        col=1,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=BORDER,
        zeroline=False,
        tickfont={"color": MUTED},
        row=1,
        col=1,
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        tickfont={"color": MUTED},
        row=2,
        col=1,
    )
    return fig


def _historical_layout(fig: go.Figure, currency: str) -> go.Figure:
    fig.update_layout(
        height=360,
        margin={"l": 86, "r": 22, "t": 24, "b": 35},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"color": MUTED, "family": FONT, "size": 11},
        showlegend=False,
        hovermode="x unified",
        hoverlabel={"bgcolor": "#181B1E", "font_color": TEXT},
    )
    fig.update_xaxes(showgrid=True, gridcolor=BORDER, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=BORDER, zeroline=False)
    unit = {"CNY": "元/股", "HKD": "港元/股", "USD": "美元/股"}.get(currency, currency + "/股")
    fig.update_yaxes(title_text=f"价格（{unit}）", title_standoff=10,
                     tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(title_text="成交量（股）", title_standoff=10,
                     tickformat=",.0f", row=2, col=1)
    fig.update_xaxes(title_text="交易日", row=2, col=1)
    return fig


def _volume_colors(history: pd.DataFrame) -> list[str]:
    # A-share convention: red rises, green falls. First day has no comparison.
    changes = history["close"].diff()
    return [
        ACCENT if pd.isna(change) else UP if change >= 0 else DOWN
        for change in changes
    ]


def history_price_chart(history: pd.DataFrame, currency: str = "CNY") -> go.Figure:
    """Actual unadjusted close and provider volume on two aligned axes."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.055,
        row_heights=[0.75, 0.25],
    )
    unit = {"CNY": "元/股", "HKD": "港元/股", "USD": "美元/股"}.get(currency, currency + "/股")
    fig.add_trace(
        go.Scatter(
            x=history["date"], y=history["close"], mode="lines",
            line={"color": ACCENT, "width": 2},
            name="收盘价",
            hovertemplate=f"%{{x|%Y-%m-%d}}<br>收盘 %{{y:.2f}} {unit}<extra></extra>",
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
    return _historical_layout(fig, currency)


def history_candlestick_chart(history: pd.DataFrame, currency: str = "CNY") -> go.Figure:
    """Actual daily OHLC candles with Chinese-market rise/fall colors."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.055,
        row_heights=[0.75, 0.25],
    )
    fig.add_trace(
        go.Candlestick(
            x=history["date"], open=history["open"], high=history["high"],
            low=history["low"], close=history["close"],
            increasing_line_color=UP, increasing_fillcolor=UP,
            decreasing_line_color=DOWN, decreasing_fillcolor=DOWN,
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
    return _historical_layout(fig, currency)


def course_chart(result, course_id: str) -> go.Figure:
    """Render experiment metadata; curriculum order never selects columns."""
    spec, frame = result.chart, result.table
    figure = go.Figure()
    colors = (ACCENT, AMBER, UP, DOWN)
    for index, name in enumerate(spec.series):
        color = colors[index % len(colors)]
        if spec.kind == "bar":
            figure.add_bar(x=frame[spec.x], y=frame[name], name=name, marker_color=color)
        else:
            figure.add_scatter(x=frame[spec.x], y=frame[name], name=name,
                               mode="markers" if spec.kind == "scatter" else "lines+markers",
                               line={"color": color, "width": 2}, marker={"color": color, "size": 6})
    figure.update_layout(height=300, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                         margin={"l": 45, "r": 20, "t": 25, "b": 40},
                         font={"family": FONT, "color": MUTED, "size": 12},
                         uirevision=f"course-{course_id}", hovermode="x unified",
                         showlegend=len(spec.series) > 1, legend={"orientation": "h", "y": 1.15},
                         xaxis_title=spec.x)
    figure.update_xaxes(showgrid=True, gridcolor=BORDER, zeroline=False)
    figure.update_yaxes(showgrid=True, gridcolor=BORDER, zeroline=False,
                         tickformat=".1%" if spec.percent else None)
    if len(frame) <= 12 and pd.api.types.is_numeric_dtype(frame[spec.x]):
        figure.update_xaxes(dtick=1)
    return figure


def teaching_chart(choice: int, frame: pd.DataFrame) -> go.Figure:
    """Render the exact fixed experiment values; never fetch market data."""
    columns = (("期数", ("本金",)), ("交易日", ("价格", "均线")),
        ("序号", ("样本值",)), ("交易日", ("演示价格",)),
        ("时点", ("演示净值",)), ("交易日", ("演示收益率",)),
        ("X", ("Y",)), ("参数组", ("训练期演示收益", "测试期演示收益")))
    x, series = columns[choice]
    figure = go.Figure()
    for index, name in enumerate(series):
        color = ACCENT if index == 0 else AMBER
        if choice in (2, 5):
            figure.add_bar(x=frame[x], y=frame[name], name=name, marker_color=color)
        else:
            figure.add_scatter(x=frame[x], y=frame[name], name=name, mode="lines+markers",
                               line={"color": color, "width": 2}, marker={"size": 6})
    if choice == 4 and float(frame["回撤"].min()) < 0:
        position = int(frame["回撤"].to_numpy().argmin())
        peak = int(frame["演示净值"].iloc[:position+1].to_numpy().argmax())
        peak_value = float(frame["演示净值"].iloc[peak])
        figure.add_shape(type="line", x0=frame[x].iloc[peak], x1=frame[x].iloc[position],
                         y0=peak_value, y1=peak_value, line={"color": AMBER, "dash": "dash"})
        figure.add_annotation(x=frame[x].iloc[position], y=frame["演示净值"].iloc[position],
            text=f"最大回撤 {frame['回撤'].iloc[position]:.1%}", showarrow=True, arrowhead=2,
            ax=frame[x].iloc[position], ay=peak_value, axref="x", ayref="y",
            font={"color": AMBER}, arrowcolor=AMBER)
    figure.update_layout(height=300, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        margin={"l": 45, "r": 20, "t": 25, "b": 40}, font={"family": FONT, "color": MUTED, "size": 12},
        uirevision=f"teaching-{choice}", hovermode="x unified", showlegend=len(series)>1,
        legend={"orientation": "h", "y": 1.15}, xaxis_title=x)
    figure.update_xaxes(showgrid=True, gridcolor=BORDER, zeroline=False)
    if len(frame) <= 12:
        figure.update_xaxes(dtick=1)
    figure.update_yaxes(showgrid=True, gridcolor=BORDER, zeroline=False,
                       tickformat=".0%" if choice in (5, 7) else None)
    return figure
