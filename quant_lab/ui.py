"""Streamlit presentation layer for the first milestone."""

from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab.charts import demo_chart


CSS_PATH = Path(__file__).parent / "terminal.css"
PAGES = ("市场数据", "策略实验室", "风险分析")


def _metric(label: str, note: str, accent: str = "") -> None:
    st.html(
        f'<div class="ql-metric {accent}">'
        f'<div class="ql-metric-label">{escape(label)}</div>'
        '<div class="ql-metric-value">--</div>'
        f'<div class="ql-metric-note">{escape(note)}</div>'
        "</div>"
    )


def _sidebar() -> tuple[str, str, str]:
    with st.sidebar:
        st.html(
            '<div class="ql-brand"><span class="ql-brand-mark">Q<span>/</span></span>'
            '<span><strong>QUANT LAB</strong><small>CN / HK RESEARCH</small></span></div>'
        )
        st.html('<div class="ql-sidebar-label">WORKSPACE / 导航</div>')
        page = st.radio("功能导航", PAGES, label_visibility="collapsed")
        st.html('<div class="ql-sidebar-label ql-sidebar-gap">RESEARCH SETUP / 研究参数</div>')
        market = st.selectbox("市场", ("A 股", "港股"))
        symbol = st.text_input(
            "股票代码（仅界面演示）",
            value="600519" if market == "A 股" else "00700",
            key=f"symbol_{market}",
        ).strip()
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        st.date_input(
            "历史区间（仅界面演示）",
            value=(today - timedelta(days=365), today),
            max_value=today,
        )
        st.button("加载历史行情 · 待接入", disabled=True, width="stretch")
        st.caption("以上选择仅预览界面，尚未连接行情接口。")
        st.html(
            '<div class="ql-side-footer"><span class="ql-live-dot"></span>'
            ' 本地研究环境 <b>·</b> 数据源未连接<br>'
            '<small>仅供学习与模拟研究，不执行真实交易</small></div>'
        )
    return page, market, symbol


def _header(page: str, market: str, symbol: str) -> None:
    page_title = "市场数据实验室" if page == "市场数据" else page
    st.html(
        '<div class="ql-header">'
        '<div><div class="ql-eyebrow">QUANT LAB / RESEARCH TERMINAL</div>'
        f'<h1>{escape(page_title)}</h1>'
        '<p>中国 A 股与港股量化研究工作台 · 第一里程碑界面骨架</p></div>'
        '<div class="ql-header-context">'
        '<span class="ql-context-label">当前选择 · 仅界面演示</span>'
        f'<strong>{escape(market)} <em>/</em> {escape(symbol or "未填写")}</strong>'
        '<span class="ql-context-status">● 数据源未连接</span>'
        '</div></div>'
    )


def _empty_candlestick() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=520,
        paper_bgcolor="#151E2D",
        plot_bgcolor="#151E2D",
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": "K 线区域预留<br><span style='font-size:13px'>接入真实日线行情后显示</span>",
                "x": 0.5,
                "y": 0.5,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"color": "#94A3B8", "size": 20},
            }
        ],
    )
    return fig


def _main_page() -> None:
    st.html(
        '<div class="ql-section-head"><div><span class="ql-eyebrow">01 / MARKET OVERVIEW</span>'
        '<h2>研究概览</h2></div><span class="ql-tag">演示界面 · 无真实行情</span></div>'
    )
    cols = st.columns(4, gap="small")
    metrics = (
        ("区间简单收益率", "待接入收盘价后计算", "ql-accent-green"),
        ("区间最高价", "待接入日线最高价", ""),
        ("区间最低价", "待接入日线最低价", ""),
        ("样本交易日", "待接入历史行情", ""),
    )
    for col, (label, note, accent) in zip(cols, metrics):
        with col:
            _metric(label, note, accent)

    chart_col, info_col = st.columns([3.35, 1], gap="small")
    with chart_col:
        with st.container(border=True):
            st.html(
                '<div class="ql-panel-header"><div><span class="ql-eyebrow">02 / PRICE & ACTIVITY</span>'
                '<h2>行情图表</h2></div><span class="ql-legend">● 模拟序列 · 无单位</span></div>'
            )
            preview_tab, candle_tab = st.tabs(("走势与活动量 · 演示", "K 线 · 待接入"))
            with preview_tab:
                st.plotly_chart(
                    demo_chart(),
                    width="stretch",
                    theme=None,
                    config={"displaylogo": False, "scrollZoom": False},
                    alt="由随机数生成的无单位模拟走势及活动量，仅用于页面版式演示。",
                )
                st.caption("⚠ 图中数值由固定随机种子生成，非股票价格、成交量或回测结果。")
            with candle_tab:
                st.plotly_chart(
                    _empty_candlestick(),
                    width="stretch",
                    theme=None,
                    config={"displayModeBar": False},
                    alt="空白的 K 线图区域，等待真实日线行情接入。",
                )
    with info_col:
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title"><span class="ql-eyebrow">DATA STATUS</span>'
                '<h2>数据说明</h2></div>'
                '<div class="ql-status-banner"><span>●</span> 尚未连接真实行情</div>'
                '<div class="ql-info-row"><span>数据类型</span><strong>历史日线 · 待接入</strong></div>'
                '<div class="ql-info-row"><span>数据来源</span><strong>待确认</strong></div>'
                '<div class="ql-info-row"><span>复权方式</span><strong>待确认</strong></div>'
                '<div class="ql-info-row"><span>数据日期</span><strong>—</strong></div>'
                '<div class="ql-info-row"><span>实时行情</span><strong>不提供</strong></div>'
            )
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title"><span class="ql-eyebrow">RESEARCH NOTES</span>'
                '<h2>研究提示</h2></div>'
                '<div class="ql-note"><b>01</b><span>区间收益率需要真实的期初与期末收盘价。</span></div>'
                '<div class="ql-note"><b>02</b><span>价格收益率不自动包含现金分红。</span></div>'
                '<div class="ql-note"><b>03</b><span>港股支持将在 A 股数据模块稳定后接入。</span></div>'
            )

    with st.container(border=True):
        st.html(
            '<div class="ql-panel-header"><div><span class="ql-eyebrow">03 / HISTORICAL DATA</span>'
            '<h2>历史数据</h2></div><span class="ql-tag">空表 · 待接入</span></div>'
        )
        st.dataframe(
            pd.DataFrame(columns=["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量"]),
            width="stretch",
            hide_index=True,
            height=160,
        )
        st.caption("数据表和 CSV 导出将在接入并验证真实历史行情后启用。")


def _future_page(page: str) -> None:
    st.html(
        '<div class="ql-future"><span class="ql-eyebrow">PLANNED MODULE</span>'
        f'<h2>{escape(page)} · 规划中</h2>'
        '<p>该模块属于后续里程碑。本阶段只完成导航和市场数据页面骨架。</p>'
        '</div>'
    )


def render_app() -> None:
    st.set_page_config(
        page_title="Quant Lab CN/HK",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.html(CSS_PATH)
    page, market, symbol = _sidebar()
    _header(page, market, symbol)
    if page == "市场数据":
        _main_page()
    else:
        _future_page(page)
