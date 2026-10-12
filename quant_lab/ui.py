"""Streamlit terminal shell and market-data workspace."""

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
    DataUnavailableError,
    HistoryBundle,
    fetch_history,
)
from quant_lab.metrics import summarize_prices
from quant_lab.processing import DataValidationError
from quant_lab.ui_ai import render_ai
from quant_lab.ui_analysis import render_risk, render_statistics
from quant_lab.ui_strategy import render_backtest, render_strategy


CSS_PATH = Path(__file__).parent / "terminal.css"
PAGES = ("市场数据", "策略实验室", "历史回测", "风险与组合", "统计与机器学习", "AI 研究助手")
ADJUSTMENTS = {"不复权": "", "前复权": "qfq", "后复权": "hfq"}


def _metric(label: str, value: str, note: str, accent: str = "") -> None:
    st.html(
        f'<div class="ql-metric {accent}">'
        f'<div class="ql-metric-label">{escape(label)}</div>'
        f'<div class="ql-metric-value">{escape(value)}</div>'
        f'<div class="ql-metric-note">{escape(note)}</div>'
        "</div>"
    )


def _sidebar() -> tuple[str, str, str, tuple[date, date] | None, str, bool]:
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
            "A 股股票代码（非指数）" if market == "A 股" else "港股股票代码（非指数）",
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
        adjustment = ADJUSTMENTS[st.selectbox("价格口径", tuple(ADJUSTMENTS))]
        pattern = r"\d{6}" if market == "A 股" else r"\d{5}"
        valid_symbol = bool(re.fullmatch(pattern, symbol))
        can_load = (
            valid_symbol and dates is not None and dates[0] <= dates[1]
        )
        clicked = st.button("加载真实历史日线", disabled=not can_load, width="stretch")
        if not valid_symbol:
            st.caption("A 股请输入 6 位、港股请输入 5 位股票代码。")
        elif dates is None:
            st.caption("请选择完整的开始和结束日期。")
        else:
            source = "腾讯证券" if market == "A 股" else "新浪财经"
            st.caption(f"来源：{source}，经 AKShare 获取；历史日线。")
        st.html(
            '<div class="ql-side-footer"><span class="ql-live-dot"></span>'
            ' 本地研究环境 <b>·</b> 历史数据按需查询<br>'
            '<small>仅供学习与模拟研究，不执行真实交易</small></div>'
        )
    return page, market, symbol, dates, adjustment, clicked


def _header(page: str, market: str, symbol: str, latest_date: str | None) -> None:
    page_title = "市场数据实验室" if page == "市场数据" else page
    status = f"● 历史数据截至 {latest_date}" if latest_date else "● 尚未加载真实行情"
    status_class = "ql-context-live" if latest_date else ""
    st.html(
        '<div class="ql-header">'
        '<div><div class="ql-eyebrow">QUANT LAB / RESEARCH TERMINAL</div>'
        f'<h1>{escape(page_title)}</h1>'
        '<p>中国 A 股与港股量化研究 · 历史数据与模拟实验</p></div>'
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


def _display_history(history: pd.DataFrame, currency: str) -> pd.DataFrame:
    unit = "元" if currency == "CNY" else "港元"
    table = history.rename(
        columns={
            "date": "日期", "open": f"开盘价（{unit}/股）", "high": f"最高价（{unit}/股）",
            "low": f"最低价（{unit}/股）", "close": f"收盘价（{unit}/股）",
            "volume": "成交量（股）", "amount": f"成交额（{unit}）",
        }
    ).copy()
    table["日期"] = table["日期"].dt.strftime("%Y-%m-%d")
    return table


def _main_page(
    bundle: HistoryBundle | None, error: str | None,
    market: str, symbol: str, adjustment: str,
) -> None:
    history = bundle.frame if bundle is not None else None
    currency = bundle.currency if bundle is not None else "CNY" if market == "A 股" else "HKD"
    money = "¥" if currency == "CNY" else "HK$"
    unit = "元" if currency == "CNY" else "港元"
    source = bundle.source if bundle is not None else (
        "腾讯证券 · AKShare" if market == "A 股" else "新浪财经 · AKShare"
    )
    adjustment_label = bundle.adjustment_label if bundle is not None else {
        "": "不复权", "qfq": "前复权", "hfq": "后复权"
    }[adjustment]
    has_data = history is not None and not history.empty
    if error:
        st.error(error)
    elif history is not None and history.empty:
        st.info("该股票在所选日期内没有历史交易记录。请调整日期范围后重试。")

    overview_tag = f"真实历史数据 · {adjustment_label}" if has_data else "未加载真实行情"
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
            f"{summary.first_close:.2f} → {summary.last_close:.2f} {unit}/股"
            if summary.simple_return is not None else "至少需要两个交易日"
        )
        accent = (
            "ql-accent-up" if summary.simple_return is not None and summary.simple_return > 0
            else "ql-accent-down" if summary.simple_return is not None and summary.simple_return < 0
            else "ql-accent-neutral"
        )
        metrics = (
            ("区间简单价格收益率", return_value, return_note, accent),
            ("区间最高价", f"{money}{summary.period_high:,.2f}", f"日线最高价 · {unit}/股", ""),
            ("区间最低价", f"{money}{summary.period_low:,.2f}", f"日线最低价 · {unit}/股", ""),
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
            legend = f"● {source}历史日线" if has_data else "● 模拟序列 · 无单位"
            st.html(
                '<div class="ql-panel-header"><div><span class="ql-eyebrow">02 / PRICE & VOLUME</span>'
                f'<h2>行情图表</h2></div><span class="ql-legend">{legend}</span></div>'
            )
            if has_data:
                price_tab, candle_tab = st.tabs(("收盘价与成交量", "日 K 线"))
                with price_tab:
                    st.plotly_chart(
                        history_price_chart(history, currency), width="stretch", theme=None,
                        config={"displaylogo": False, "scrollZoom": False},
                        alt=f"{source}真实历史日线的收盘价（{unit}每股）和成交量（股）。",
                    )
                with candle_tab:
                    st.plotly_chart(
                        history_candlestick_chart(history, currency), width="stretch", theme=None,
                        config={"displaylogo": False, "scrollZoom": False},
                        alt=f"{source}真实历史日线的开高低收 K 线及成交量。红色上涨，绿色下跌。",
                    )
                st.caption(f"来源：{source}；{adjustment_label}价格；红涨绿跌。图表不是实时行情。")
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
                f'<div class="ql-info-row"><span>数据类型</span><strong>{market}股票 · 历史日线</strong></div>'
                f'<div class="ql-info-row"><span>数据来源</span><strong>{source}</strong></div>'
                f'<div class="ql-info-row"><span>价格口径</span><strong>{adjustment_label}</strong></div>'
                f'<div class="ql-info-row"><span>价格币种</span><strong>{currency}</strong></div>'
                f'<div class="ql-info-row"><span>最新交易日</span><strong>{latest}</strong></div>'
                '<div class="ql-info-row"><span>成交量单位</span><strong>股</strong></div>'
                '<div class="ql-info-row"><span>实时行情</span><strong>不提供</strong></div>'
            )
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title"><span class="ql-eyebrow">RESEARCH NOTES</span>'
                '<h2>研究提示</h2></div>'
                '<div class="ql-note"><b>01</b><span>收益率使用首尾两个实际交易日的收盘价。</span></div>'
                '<div class="ql-note"><b>02</b><span>页面收益率不等同含分红的总回报或可实现收益。</span></div>'
                '<div class="ql-note"><b>03</b><span>不同复权口径不可直接混用；回测成交始终用原始价格。</span></div>'
            )

    with st.container(border=True):
        table_tag = f"{len(history)} 条真实记录" if has_data else "空表 · 等待数据"
        st.html(
            '<div class="ql-panel-header"><div><span class="ql-eyebrow">03 / HISTORICAL DATA</span>'
            f'<h2>历史数据</h2></div><span class="ql-tag">{table_tag}</span></div>'
        )
        if has_data:
            table = _display_history(history, currency)
            st.dataframe(table, width="stretch", hide_index=True, height=280)
            first = table["日期"].iloc[0].replace("-", "")
            last = table["日期"].iloc[-1].replace("-", "")
            st.download_button(
                "导出 CSV", table.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{market}_{symbol}_{first}_{last}_{adjustment or 'raw'}.csv", mime="text/csv",
            )
            st.caption(f"日期以实际交易日为准。价格单位：{unit}/股；成交量：股；成交额：{unit}。")
        else:
            st.dataframe(
                pd.DataFrame(columns=["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量"]),
                width="stretch", hide_index=True, height=160,
            )
            st.caption("加载并验证真实历史行情后可查看和导出 CSV。")


def render_app() -> None:
    st.set_page_config(
        page_title="Quant Lab CN/HK",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.html(CSS_PATH)
    page, market, symbol, dates, adjustment, clicked = _sidebar()
    bundle: HistoryBundle | None = None
    error: str | None = None
    if dates is not None:
        query = (market, symbol, dates[0], dates[1], adjustment)
        if clicked:
            try:
                with st.spinner("正在获取并验证真实历史日线…"):
                    st.session_state["loaded_bundle"] = fetch_history(
                        market, symbol, *dates, adjustment
                    )
                st.session_state["load_error"] = None
            except (DataUnavailableError, DataValidationError, ValueError) as exc:
                st.session_state["loaded_bundle"] = None
                st.session_state["load_error"] = str(exc)
            st.session_state["loaded_query"] = query
        if st.session_state.get("loaded_query") == query:
            bundle = st.session_state.get("loaded_bundle")
            error = st.session_state.get("load_error")

    latest_date = (
        bundle.frame["date"].iloc[-1].strftime("%Y-%m-%d")
        if bundle is not None and not bundle.frame.empty else None
    )
    _header(page, market, symbol, latest_date)
    if page == "市场数据":
        _main_page(bundle, error, market, symbol, adjustment)
        return
    if error:
        st.error(error)
    if page == "策略实验室":
        render_strategy(bundle)
    elif page == "历史回测":
        render_backtest(bundle)
    elif page == "风险与组合":
        render_risk(bundle)
    elif page == "统计与机器学习":
        render_statistics(bundle)
    else:
        render_ai(bundle)
