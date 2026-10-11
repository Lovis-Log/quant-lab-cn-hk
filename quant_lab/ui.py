"""Streamlit presentation layer for historical A-share research."""

from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab.charts import demo_chart, history_candlestick_chart, history_price_chart
from quant_lab.data import (
    ADJUSTMENT_LABEL,
    SOURCE_LABEL,
    DataUnavailableError,
    fetch_a_share_daily,
)
from quant_lab.metrics import summarize_prices
from quant_lab.processing import DataValidationError


CSS_PATH = Path(__file__).parent / "terminal.css"
PAGES = ("市场数据", "策略实验室", "风险分析")


def _metric(label: str, value: str, note: str, accent: str = "") -> None:
    st.html(
        f'<div class="ql-metric {accent}">'
        f'<div class="ql-metric-label">{escape(label)}</div>'
        f'<div class="ql-metric-value">{escape(value)}</div>'
        f'<div class="ql-metric-note">{escape(note)}</div>'
        "</div>"
    )


def _sidebar() -> tuple[str, str, str, tuple[date, date] | None, bool]:
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
            "A 股股票代码（非指数）" if market == "A 股" else "港股代码（待接入）",
            value="600519" if market == "A 股" else "00700",
            key=f"symbol_{market}",
        ).strip()
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        selected_dates = st.date_input(
            "历史区间",
            value=(today - timedelta(days=365), today),
            max_value=today,
        )
        dates = (
            (selected_dates[0], selected_dates[1])
            if isinstance(selected_dates, tuple) and len(selected_dates) == 2
            else None
        )
        valid_symbol = bool(re.fullmatch(r"\d{6}", symbol))
        can_load = (
            page == "市场数据" and market == "A 股" and valid_symbol
            and dates is not None and dates[0] <= dates[1]
        )
        clicked = st.button("加载真实历史日线", disabled=not can_load, width="stretch")
        if market == "港股":
            st.caption("港股数据将在后续里程碑接入。")
        elif not valid_symbol:
            st.caption("请输入 6 位 A 股股票代码。")
        elif dates is None:
            st.caption("请选择完整的开始和结束日期。")
        else:
            st.caption("来源：腾讯证券，经 AKShare 获取；不复权日线。")
        st.html(
            '<div class="ql-side-footer"><span class="ql-live-dot"></span>'
            ' 本地研究环境 <b>·</b> 历史数据按需查询<br>'
            '<small>仅供学习与模拟研究，不执行真实交易</small></div>'
        )
    return page, market, symbol, dates, clicked


def _header(page: str, market: str, symbol: str, latest_date: str | None) -> None:
    page_title = "市场数据实验室" if page == "市场数据" else page
    status = f"● 历史数据截至 {latest_date}" if latest_date else "● 尚未加载真实行情"
    status_class = "ql-context-live" if latest_date else ""
    st.html(
        '<div class="ql-header">'
        '<div><div class="ql-eyebrow">QUANT LAB / RESEARCH TERMINAL</div>'
        f'<h1>{escape(page_title)}</h1>'
        '<p>中国 A 股历史日线研究 · 港股模块规划中</p></div>'
        '<div class="ql-header-context">'
        '<span class="ql-context-label">当前研究标的</span>'
        f'<strong>{escape(market)} <em>/</em> {escape(symbol or "未填写")}</strong>'
        f'<span class="ql-context-status {status_class}">{escape(status)}</span>'
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
                "text": "K 线区域预留<br><span style='font-size:13px'>加载真实日线行情后显示</span>",
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


def _display_history(history: pd.DataFrame) -> pd.DataFrame:
    table = history.rename(
        columns={
            "date": "日期", "open": "开盘价（元/股）", "high": "最高价（元/股）",
            "low": "最低价（元/股）", "close": "收盘价（元/股）",
            "volume": "成交量（股）", "amount": "成交额（元）",
        }
    ).copy()
    table["日期"] = table["日期"].dt.strftime("%Y-%m-%d")
    return table


def _main_page(history: pd.DataFrame | None, error: str | None, symbol: str) -> None:
    has_data = history is not None and not history.empty
    if error:
        st.error(error)
    elif history is not None and history.empty:
        st.info("该股票在所选日期内没有历史交易记录。请调整日期范围后重试。")

    overview_tag = "真实历史数据 · 不复权" if has_data else "未加载真实行情"
    st.html(
        '<div class="ql-section-head"><div><span class="ql-eyebrow">01 / MARKET OVERVIEW</span>'
        f'<h2>研究概览</h2></div><span class="ql-tag">{overview_tag}</span></div>'
    )
    if has_data:
        summary = summarize_prices(history)
        return_value = (
            f"{summary.simple_return:+.2%}" if summary.simple_return is not None else "--"
        )
        return_note = (
            f"{summary.first_close:.2f} → {summary.last_close:.2f} 元/股"
            if summary.simple_return is not None else "至少需要两个交易日"
        )
        accent = (
            "ql-accent-up" if summary.simple_return is not None and summary.simple_return > 0
            else "ql-accent-down" if summary.simple_return is not None and summary.simple_return < 0
            else "ql-accent-neutral"
        )
        metrics = (
            ("区间简单价格收益率", return_value, return_note, accent),
            ("区间最高价", f"¥{summary.period_high:,.2f}", "日线最高价 · 元/股", ""),
            ("区间最低价", f"¥{summary.period_low:,.2f}", "日线最低价 · 元/股", ""),
            ("样本交易日", str(summary.trading_days), "仅统计返回的交易日", ""),
        )
    else:
        metrics = (
            ("区间简单价格收益率", "--", "加载日线后计算", "ql-accent-neutral"),
            ("区间最高价", "--", "等待真实行情", ""),
            ("区间最低价", "--", "等待真实行情", ""),
            ("样本交易日", "--", "等待真实行情", ""),
        )
    for col, (label, value, note, accent) in zip(st.columns(4, gap="small"), metrics):
        with col:
            _metric(label, value, note, accent)

    chart_col, info_col = st.columns([3.35, 1], gap="small")
    with chart_col:
        with st.container(border=True):
            legend = "● 腾讯证券历史日线" if has_data else "● 模拟序列 · 无单位"
            st.html(
                '<div class="ql-panel-header"><div><span class="ql-eyebrow">02 / PRICE & VOLUME</span>'
                f'<h2>行情图表</h2></div><span class="ql-legend">{legend}</span></div>'
            )
            if has_data:
                price_tab, candle_tab = st.tabs(("收盘价与成交量", "日 K 线"))
                with price_tab:
                    st.plotly_chart(
                        history_price_chart(history), width="stretch", theme=None,
                        config={"displaylogo": False, "scrollZoom": False},
                        alt="腾讯证券真实历史日线的收盘价（元每股）和成交量（股）。",
                    )
                with candle_tab:
                    st.plotly_chart(
                        history_candlestick_chart(history), width="stretch", theme=None,
                        config={"displaylogo": False, "scrollZoom": False},
                        alt="腾讯证券真实历史日线的开高低收 K 线及成交量。红色上涨，绿色下跌。",
                    )
                st.caption("来源：腾讯证券，经 AKShare 获取。不复权价格；红涨绿跌。图表不是实时行情。")
            else:
                preview_tab, candle_tab = st.tabs(("走势与活动量 · 演示", "K 线 · 等待数据"))
                with preview_tab:
                    st.plotly_chart(
                        demo_chart(), width="stretch", theme=None,
                        config={"displaylogo": False, "scrollZoom": False},
                        alt="由随机数生成的无单位模拟走势及活动量，仅用于页面版式演示。",
                    )
                    st.caption("⚠ 图中数值由固定随机种子生成，非股票价格、成交量或回测结果。")
                with candle_tab:
                    st.plotly_chart(
                        _empty_candlestick(), width="stretch", theme=None,
                        config={"displayModeBar": False},
                        alt="空白的 K 线图区域，等待真实日线行情加载。",
                    )

    with info_col:
        latest = history["date"].iloc[-1].strftime("%Y-%m-%d") if has_data else "—"
        status_class = "ql-status-ok" if has_data else ""
        status_text = "已加载真实历史数据" if has_data else "尚未加载真实行情"
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title"><span class="ql-eyebrow">DATA STATUS</span>'
                '<h2>数据说明</h2></div>'
                f'<div class="ql-status-banner {status_class}"><span>●</span> {status_text}</div>'
                '<div class="ql-info-row"><span>数据类型</span><strong>A 股股票 · 历史日线</strong></div>'
                f'<div class="ql-info-row"><span>数据来源</span><strong>{SOURCE_LABEL}</strong></div>'
                f'<div class="ql-info-row"><span>价格口径</span><strong>{ADJUSTMENT_LABEL}</strong></div>'
                f'<div class="ql-info-row"><span>最新交易日</span><strong>{latest}</strong></div>'
                '<div class="ql-info-row"><span>成交量单位</span><strong>股</strong></div>'
                '<div class="ql-info-row"><span>实时行情</span><strong>不提供</strong></div>'
            )
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title"><span class="ql-eyebrow">RESEARCH NOTES</span>'
                '<h2>研究提示</h2></div>'
                '<div class="ql-note"><b>01</b><span>收益率使用首尾两个实际交易日的收盘价。</span></div>'
                '<div class="ql-note"><b>02</b><span>该价格收益率不含现金分红和交易成本。</span></div>'
                '<div class="ql-note"><b>03</b><span>不复权价格可能受到除权除息影响。</span></div>'
            )

    with st.container(border=True):
        table_tag = f"{len(history)} 条真实记录" if has_data else "空表 · 等待数据"
        st.html(
            '<div class="ql-panel-header"><div><span class="ql-eyebrow">03 / HISTORICAL DATA</span>'
            f'<h2>历史数据</h2></div><span class="ql-tag">{table_tag}</span></div>'
        )
        if has_data:
            table = _display_history(history)
            st.dataframe(table, width="stretch", hide_index=True, height=280)
            first = table["日期"].iloc[0].replace("-", "")
            last = table["日期"].iloc[-1].replace("-", "")
            st.download_button(
                "导出 CSV", table.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{symbol}_{first}_{last}_raw.csv", mime="text/csv",
            )
            st.caption("日期以实际交易日为准。价格单位：元/股；成交量：股；成交额：元。")
        else:
            st.dataframe(
                pd.DataFrame(columns=["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量"]),
                width="stretch", hide_index=True, height=160,
            )
            st.caption("加载并验证真实历史行情后可查看和导出 CSV。")


def _future_page(page: str) -> None:
    st.html(
        '<div class="ql-future"><span class="ql-eyebrow">PLANNED MODULE</span>'
        f'<h2>{escape(page)} · 规划中</h2>'
        '<p>该模块属于后续里程碑。当前可使用 A 股历史日线研究页面。</p>'
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
    page, market, symbol, dates, clicked = _sidebar()
    history: pd.DataFrame | None = None
    error: str | None = None
    if page == "市场数据" and market == "A 股" and dates is not None:
        query = (symbol, dates[0], dates[1])
        if clicked:
            try:
                with st.spinner("正在获取并验证真实历史日线…"):
                    st.session_state["loaded_history"] = fetch_a_share_daily(symbol, *dates)
                st.session_state["load_error"] = None
            except (DataUnavailableError, DataValidationError, ValueError) as exc:
                st.session_state["loaded_history"] = None
                st.session_state["load_error"] = str(exc)
            st.session_state["loaded_query"] = query
        if st.session_state.get("loaded_query") == query:
            history = st.session_state.get("loaded_history")
            error = st.session_state.get("load_error")

    latest_date = (
        history["date"].iloc[-1].strftime("%Y-%m-%d")
        if history is not None and not history.empty else None
    )
    _header(page, market, symbol, latest_date)
    if page == "市场数据":
        _main_page(history, error, symbol)
    else:
        _future_page(page)
