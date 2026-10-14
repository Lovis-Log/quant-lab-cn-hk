"""Streamlit terminal shell and market-data workspace."""

from datetime import date, datetime, timedelta
from dataclasses import replace, asdict
import time
import sqlite3
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
    fetch_history_cached as fetch_history,
)
from quant_lab.metrics import summarize_prices
from quant_lab.processing import DataValidationError
from quant_lab.ui_ai import render_ai
from quant_lab.ui_analysis import render_risk, render_statistics
from quant_lab.ui_strategy import render_backtest, render_strategy
from quant_lab.ui_learning import render_academy
from quant_lab.ui_research import render_research_notes
from quant_lab.ui_terminal import render_watchlist
from quant_lab import names
from quant_lab.market_data import normalize_symbol
from quant_lab.storage import list_watchlist
from quant_lab.ui_updates import initialize_settings, persist_setting, toggle_refresh, beijing, show_history_status, INTERVALS
from quant_lab.ui_knowledge import render_knowledge
from quant_lab.ui_deepseek import render_deepseek
from quant_lab.ai_context import bundle_context, experiment_context
from quant_lab.securities import security_directory
from quant_lab.guidance import GUIDES
from quant_lab.ui_guidance import (render_learning_center, render_page_help, render_welcome,
    protect_research_widgets, complete_task, history_evidence)


CSS_PATH = Path(__file__).parent / "terminal.css"
PAGES = tuple(GUIDES)
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
        page = st.radio("功能导航", PAGES, label_visibility="collapsed", key="nav_page")
        st.html('<div class="ql-sidebar-label ql-sidebar-gap">RESEARCH SETUP / 研究参数</div>')
        market = st.selectbox("市场", ("A 股", "港股"), key="market_selection")
        st.session_state.setdefault(f"symbol_{market}", "600519" if market == "A 股" else "00700")
        def code_changed():
            st.session_state["_security_selection_event"] = {"market": market, "symbol": st.session_state[f"symbol_{market}"]}
        symbol = st.text_input(
            "A 股股票代码（非指数）" if market == "A 股" else "港股股票代码（非指数）",
            key=f"symbol_{market}",
            on_change=code_changed,
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
        try:
            symbol = normalize_symbol(market, symbol)
            valid_symbol = True
        except ValueError:
            valid_symbol = False
        can_load = (
            valid_symbol and dates is not None and dates[0] <= dates[1]
        )
        clicked = st.button("加载真实历史日线", disabled=not can_load, width="stretch")
        def choose_candidate():
            chosen = st.session_state.get(f"candidate_{market}")
            if chosen:
                st.session_state[f"symbol_{market}"] = normalize_symbol(market, chosen)
                st.session_state["_security_selection_event"] = {"market": market, "symbol": chosen}
        labels = {}
        try:
            directory = security_directory(market)
            labels = dict(directory.rows)
            st.selectbox("搜索股票候选（代码 / 名称）", list(labels), index=None,
                key=f"candidate_{market}", placeholder="输入代码或名称搜索；选中后填入上方代码",
                format_func=lambda code: f"{code} · {labels[code]}",
                on_change=choose_candidate,
                help="常见大盘股票优先展示；这是证券目录，不是买入推荐。仍可手动输入未收录代码。")
            st.caption(f"目录快照：{len(labels)} 只 · {directory.source} · 获取于 {beijing(directory.received_at)}；不含行情，不验证当前上市状态。")
            if directory.error:
                st.warning(directory.error)
            if st.button("更新股票候选目录", key="refresh_security_directory"):
                directory = security_directory(market, force=True)
                if directory.error:
                    st.warning(directory.error)
                else:
                    st.rerun()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            st.warning(str(exc))
        st.toggle("新手模式（关闭为专业模式）", key="learning_mode", on_change=persist_setting,
                  args=("learning_mode",), help="只改变教学提示和知识入口，不改变金融计算。")
        st.caption("当前使用：" + ("新手模式" if st.session_state["learning_mode"] else "专业模式"))
        if valid_symbol:
            if st.button("重新获取证券名称", key="refresh_security_name"):
                names.security_name(market, symbol, force=True)
            st.caption("当前选择：" + names.security_label(market, symbol))
            try:
                name_record = names.storage.cached_security_name(market, symbol)
                if name_record:
                    st.caption(f"名称资料缓存：{name_record['source']} · 成功获取于 {beijing(name_record['fetched_at'])}")
            except (OSError, ValueError, sqlite3.Error):
                pass
            name_error = names.NAME_CACHE.error(market, symbol)
            if name_error:
                st.warning(name_error)
            selection = st.session_state.pop("_security_selection_event", None)
            if selection and selection["market"] == market and normalize_symbol(market, selection["symbol"]) == symbol:
                complete_task("select_security", {"selected": True, "identity_known": bool(labels.get(symbol) or names.security_name(market, symbol)),
                    "market": market, "symbol": symbol, "identity_basis": "基础资料目录快照或个股资料；不证明当前可交易"})
        try:
            watch_items = list_watchlist()
        except (OSError, ValueError, sqlite3.Error):
            watch_items = []
        if watch_items:
            def choose_watch():
                chosen = st.session_state.get("sidebar_watch")
                if chosen:
                    st.session_state["market_selection"] = chosen[0]
                    st.session_state[f"symbol_{chosen[0]}"] = chosen[1]
            st.selectbox("从自选股选择", [None] + watch_items, key="sidebar_watch", on_change=choose_watch,
                         format_func=lambda item: "手动输入" if item is None else names.security_label(*item))
        st.toggle("自动刷新行情（仅市场页）", key="refresh_enabled", on_change=persist_setting, args=("refresh_enabled",))
        st.selectbox("自动刷新间隔", INTERVALS, key="refresh_interval_seconds",
                     format_func=lambda seconds: f"{seconds//60} 分钟", on_change=persist_setting, args=("refresh_interval_seconds",))
        st.caption("自动刷新仅在软件和市场页会话运行时生效；关闭软件后不更新。")
        if st.session_state.get("settings_error"):
            st.warning(st.session_state.pop("settings_error"))
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
    status_class = ""
    st.html(
        '<div class="ql-header">'
        '<div><div class="ql-eyebrow">QUANT LAB / RESEARCH TERMINAL</div>'
        f'<h1>{escape(page_title)}</h1>'
        '<p>中国 A 股与港股量化研究 · 历史数据与模拟实验</p></div>'
        '<div class="ql-header-context">'
        '<span class="ql-context-label">当前研究标的</span>'
        f'<strong>{escape(names.security_label(market, symbol) if symbol else "未填写")}</strong>'
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
    if st.session_state.get("learning_mode", True):
        render_knowledge("simple_return", summary.simple_return if has_data else None,
                         key="market", observations=len(history) if has_data else None)

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
                        history_price_chart(history, currency).update_layout(title_text=names.security_label(market, symbol, bundle.company_name)), width="stretch", theme=None,
                        config={"displaylogo": False, "scrollZoom": False},
                        alt=f"{source}真实历史日线的收盘价（{unit}每股）和成交量（股）。",
                    )
                with candle_tab:
                    st.plotly_chart(
                        history_candlestick_chart(history, currency).update_layout(title_text=names.security_label(market, symbol, bundle.company_name)), width="stretch", theme=None,
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
        received = (
            beijing(bundle.received_at)
            if bundle is not None and bundle.received_at is not None else "—"
        )
        status_class = "ql-status-ok" if has_data else ""
        status_text = "已加载真实历史数据" if has_data else "尚未加载真实行情"
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title"><span class="ql-eyebrow">DATA STATUS</span>'
                '<h2>数据说明</h2></div>'
                f'<div class="ql-status-banner {status_class}"><span>●</span> {status_text}</div>'
                f'<div class="ql-info-row"><span>数据类型</span><strong>{market}股票 · 历史日线</strong></div>'
                f'<div class="ql-info-row"><span>数据来源</span><strong>{source}</strong></div>'
                f'<div class="ql-info-row"><span>本地缓存</span><strong>{"是" if bundle is not None and bundle.cached else "否"}</strong></div>'
                f'<div class="ql-info-row"><span>价格口径</span><strong>{adjustment_label}</strong></div>'
                f'<div class="ql-info-row"><span>价格币种</span><strong>{currency}</strong></div>'
                f'<div class="ql-info-row"><span>最新交易日</span><strong>{latest}</strong></div>'
                f'<div class="ql-info-row"><span>接收时间（北京时间）</span><strong>{received}</strong></div>'
                '<div class="ql-info-row"><span>延迟状态</span><strong>历史日线；确切延迟未知</strong></div>'
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
            table.insert(0, "股票", names.security_label(market, symbol, bundle.company_name))
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
    render_watchlist(market, symbol)


def _market_workspace(query, market, symbol, adjustment):
    interval = st.session_state.get("refresh_interval_seconds", 300)
    auto = st.session_state.get("refresh_enabled", True)

    @st.fragment(run_every=interval if auto else None)
    def body():
        current = st.session_state.get("loaded_query") == query
        bundle = st.session_state.get("loaded_bundle") if current else None
        error = st.session_state.get("load_error") if current else None
        wait = st.session_state.get("history_manual_at", float('-inf')) + 5 - time.monotonic()
        first, second = st.columns(2)
        requested = first.button("立即更新历史日线", disabled=query is None, key="history_refresh")
        manual = requested and wait <= 0
        if requested and wait > 0:
            st.info(f"上一次立即更新刚发起，请等待 {wait:.0f} 秒后再点击；本次没有重复请求。")
        pause = second.button("暂停自动刷新" if auto else "恢复自动刷新", on_click=toggle_refresh, key="refresh_pause")
        if pause:
            st.rerun()
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        next_attempt = st.session_state.get("history_next_attempt") if current else None
        updated = st.session_state.pop("_history_loaded_this_run", False)
        if manual or (auto and bundle is not None and next_attempt and now >= next_attempt):
            if manual:
                st.session_state["history_manual_at"] = time.monotonic()
            previous = bundle
            try:
                new_bundle = fetch_history(*query, force=True)
                bundle = replace(new_bundle, company_name=names.security_name(market, symbol))
                error = bundle.update_error
                updated = True
            except (DataUnavailableError, DataValidationError, ValueError):
                error = "历史日线更新失败；保留上次有效数据，数据可能过期。"
                if previous is not None:
                    bundle = replace(previous, update_result="请求失败", update_error=error,
                                     last_attempt_at=now, cached=True)
            st.session_state["loaded_bundle"] = bundle
            st.session_state["loaded_query"] = query
            st.session_state["load_error"] = error
            next_attempt = now + timedelta(seconds=interval)
            st.session_state["history_next_attempt"] = next_attempt
        latest = str(bundle.frame.date.iloc[-1].date()) if bundle is not None and not bundle.frame.empty else None
        _header("市场数据", market, symbol, latest)
        show_history_status(bundle, next_attempt, session_cache=not updated)
        _main_page(bundle, error, market, symbol, adjustment)
    body()


def render_app() -> None:
    st.set_page_config(
        page_title="Quant Lab CN/HK",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.html(CSS_PATH)
    initialize_settings()
    protect_research_widgets()
    page, market, symbol, dates, adjustment, clicked = _sidebar()
    bundle: HistoryBundle | None = None
    error: str | None = None
    query = None
    st.session_state["active_backtest_context"] = None
    st.session_state["active_analysis_context"] = None
    st.session_state["active_learning_context"] = None
    record = None
    if dates is not None:
        query = (market, symbol, dates[0], dates[1], adjustment)
        if clicked:
            try:
                with st.spinner("正在获取并验证真实历史日线…"):
                    fetched = fetch_history(
                        market, symbol, *dates, adjustment
                    )
                    st.session_state["loaded_bundle"] = replace(fetched, company_name=names.security_name(market, symbol))
                    evidence = history_evidence(st.session_state["loaded_bundle"])
                    complete_task("select_security", {"selected": True, "identity_known": bool(evidence.get("company_name")),
                        "market": market, "symbol": symbol})
                    complete_task("load_history", evidence)
                    st.session_state["_history_loaded_this_run"] = True
                st.session_state["load_error"] = fetched.update_error
            except (DataUnavailableError, DataValidationError, ValueError) as exc:
                if st.session_state.get("loaded_query") != query:
                    st.session_state["loaded_bundle"] = None
                st.session_state["load_error"] = str(exc)
            st.session_state["loaded_query"] = query
            st.session_state["history_next_attempt"] = datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(seconds=st.session_state["refresh_interval_seconds"])
        if st.session_state.get("loaded_query") == query:
            bundle = st.session_state.get("loaded_bundle")
            error = st.session_state.get("load_error")
            if bundle is not None:
                current_name = names.security_name(market, symbol)
                if current_name and current_name != bundle.company_name:
                    bundle = replace(bundle, company_name=current_name)
                    st.session_state["loaded_bundle"] = bundle

    latest_date = (
        bundle.frame["date"].iloc[-1].strftime("%Y-%m-%d")
        if bundle is not None and not bundle.frame.empty else None
    )
    st.session_state["active_data_fingerprint"] = None if page in {"Quant Academy", "新手使用指引"} else bundle_context(page, bundle).get("data_fingerprint")
    render_welcome()
    render_page_help(page)
    if page == "市场数据":
        _market_workspace(query, market, symbol, adjustment)
        bundle = st.session_state.get("loaded_bundle") if st.session_state.get("loaded_query") == query else None
    elif page == "Quant Academy":
        _header(page, market, symbol, latest_date)
        render_academy()
    elif page == "新手使用指引":
        _header(page, market, symbol, latest_date)
        render_learning_center()
    elif page == "研究笔记":
        _header(page, market, symbol, latest_date)
        record = render_research_notes()
    else:
        _header(page, market, symbol, latest_date)
        if error:
            st.warning(error)
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
    context = experiment_context(record) if record else bundle_context(page, bundle)
    context["page"] = page
    if st.session_state.get("active_backtest_context"):
        context.update(st.session_state["active_backtest_context"])
    if st.session_state.get("active_analysis_context"):
        context["statistics"] = st.session_state["active_analysis_context"]
    if page == "Quant Academy":
        context = {"page": page, "lesson": st.session_state.get("academy_lesson", 0),
                   "data_status": "离线教学实验，不是股票行情。"}
    if page == "新手使用指引":
        context = {"page": page, "data_status": "学习指南与固定教学样本，不是股票行情。"}
    if st.session_state.get("active_learning_context"):
        context["learning_context"] = st.session_state["active_learning_context"]
    render_deepseek(context)
