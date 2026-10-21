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
from quant_lab.ui_analysis import render_risk, render_statistics
from quant_lab.ui_strategy import render_backtest, render_strategy
from quant_lab.ui_learning import render_academy
from quant_lab.ui_research import render_research_panel
from quant_lab.ui_terminal import render_watchlist
from quant_lab import names
from quant_lab.market_data import normalize_symbol
from quant_lab.storage import list_watchlist
from quant_lab.ui_updates import initialize_settings, toggle_refresh, beijing, show_history_status
from quant_lab.ui_knowledge import render_knowledge
from quant_lab.ui_deepseek import initialize_credentials, render_deepseek_panel
from quant_lab.ai_context import bundle_context, experiment_context
from quant_lab.securities import security_directory
from quant_lab.guidance import GUIDES
from quant_lab.ui_guidance import (render_learning_panel, render_page_help,
    render_welcome, protect_research_widgets, complete_task, history_evidence)
from quant_lab.ui_settings import library_configured, render_library_setup, render_settings_panel


CSS_PATH = Path(__file__).parent / "terminal.css"
TOPBAR_PAGES = {"AI 研究助手", "新手使用指引", "研究笔记"}
PAGES = tuple(page for page in GUIDES if page not in TOPBAR_PAGES)
ADJUSTMENTS = {"不复权": "", "前复权": "qfq", "后复权": "hfq"}

DOCK_RESIZE_JS = """
<script>
(() => {
  const root = document.documentElement;
  const setup = (kind, minimum) => {
    const panel = document.querySelector(`.st-key-${kind}_side_panel`);
    const handle = panel?.querySelector(`.ql-resize-handle[data-panel="${kind}"]`);
    if (!panel || !handle || handle.dataset.bound === "1") return;
    handle.dataset.bound = "1";
    const property = `--ql-${kind}-width`;
    const storageKey = `quantlab.${kind}.panelWidth`;
    const stored = Number.parseFloat(localStorage.getItem(storageKey));

    const applyWidth = (requested) => {
      const otherWidth = ['guide','deepseek','notes'].filter(value => value !== kind)
        .map(value => document.querySelector(`.st-key-${value}_side_panel`))
        .reduce((total, other) => total + (other ? other.getBoundingClientRect().width : 0), 0);
      const sidebar = document.querySelector('[data-testid="stSidebar"]');
      const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 0;
      const maximum = Math.max(minimum, window.innerWidth - sidebarWidth - otherWidth - 360);
      const width = Math.round(Math.min(maximum, Math.max(minimum, requested)));
      root.style.setProperty(property, `${width}px`);
      localStorage.setItem(storageKey, String(width));
      window.__quantLabApplyPanelOrder?.();
    };
    if (Number.isFinite(stored)) applyWidth(stored);

    handle.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = panel.getBoundingClientRect().width;
      handle.classList.add("is-dragging");
      const move = (next) => applyWidth(startWidth - (next.clientX - startX));
      const stop = () => {
        handle.classList.remove("is-dragging");
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", stop);
        window.removeEventListener("pointercancel", stop);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", stop);
      window.addEventListener("pointercancel", stop);
    });
    handle.addEventListener("keydown", (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const delta = event.key === 'ArrowLeft' ? 24 : -24;
      applyWidth(panel.getBoundingClientRect().width + delta);
    });
  };
  setup("guide", 220);
  setup("deepseek", 240);
  setup("notes", 260);
})();
</script>
"""

TOPBAR_REORDER_JS = """
<script>
(() => {
  const root = document.documentElement;
  const storageKey = "quantlab.dock.panelOrder";
  const kinds = ['guide', 'deepseek', 'notes'];
  const readOrder = () => {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey));
      return Array.isArray(value) && kinds.every(kind => value.includes(kind)) ? value : [...kinds];
    } catch (_) { return [...kinds]; }
  };
  let order = readOrder();

  const applyOrder = (animate=true) => {
    const buttons = Object.fromEntries(kinds.map(kind => [kind,
      document.querySelector(`.st-key-${kind}_panel_toggle button`)]));
    const before = Object.fromEntries(kinds.map(kind => [kind, buttons[kind]?.getBoundingClientRect()]));
    order.forEach((kind, index) => {
      const column = buttons[kind]?.closest('[data-testid="stColumn"]');
      if (column) column.style.order = String(index + 3);
    });
    let right = 0;
    [...order].reverse().forEach(kind => {
      const panel = document.querySelector(`.st-key-${kind}_side_panel`);
      if (!panel) return;
      panel.style.right = `${right}px`;
      right += panel.getBoundingClientRect().width;
    });
    root.dataset.qlDockOrder = order.join('-');
    localStorage.setItem(storageKey, JSON.stringify(order));
    if (animate && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      requestAnimationFrame(() => kinds.forEach(kind => {
        const button = buttons[kind];
        const first = before[kind];
        const last = button?.getBoundingClientRect();
        if (!button || !first || !last) return;
        const delta = first.left - last.left;
        if (!delta) return;
        button.animate([{transform:`translateX(${delta}px)`},{transform:'translateX(0)'}],
          {duration:180,easing:'cubic-bezier(.2,.8,.2,1)'});
      }));
    }
  };
  window.__quantLabApplyPanelOrder = () => applyOrder(false);

  const bind = (button, kind) => {
    if (button.dataset.reorderBound === '1') return;
    button.dataset.reorderBound = '1';
    button.setAttribute('aria-description', '按住并左右拖动可调整三个面板的顺序');
    button.addEventListener('click', (event) => {
      if (button.dataset.suppressClick !== '1') return;
      event.preventDefault();
      event.stopImmediatePropagation();
      button.dataset.suppressClick = '';
    }, true);
    button.addEventListener('pointerdown', (event) => {
      if (event.button !== 0) return;
      const startX = event.clientX;
      let dragged = false;
      const move = (next) => {
        if (Math.abs(next.clientX - startX) < 8 && !dragged) return;
        dragged = true;
        button.classList.add('is-reordering');
        const others = order.filter(value => value !== kind);
        let target = others.length;
        for (let index = 0; index < others.length; index++) {
          const other = document.querySelector(`.st-key-${others[index]}_panel_toggle button`);
          if (other && next.clientX < other.getBoundingClientRect().left + other.getBoundingClientRect().width/2) {
            target = index; break;
          }
        }
        const updated = [...others];
        updated.splice(target, 0, kind);
        if (updated.join('|') !== order.join('|')) { order = updated; applyOrder(true); }
      };
      const stop = () => {
        button.classList.remove('is-reordering');
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', stop);
        window.removeEventListener('pointercancel', stop);
        if (dragged) {
          button.dataset.suppressClick = '1';
          window.setTimeout(() => { button.dataset.suppressClick = ''; }, 250);
        }
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', stop);
      window.addEventListener('pointercancel', stop);
    });
  };
  const initialize = () => {
    kinds.forEach(kind => {
      const button = document.querySelector(`.st-key-${kind}_panel_toggle button`);
      if (button) bind(button, kind);
    });
    applyOrder(false);
  };
  initialize();
  window.__quantLabTopbarObserver?.disconnect();
  window.__quantLabTopbarObserver = new MutationObserver(initialize);
  window.__quantLabTopbarObserver.observe(document.body, {childList:true, subtree:true});
  if (!window.__quantLabFullscreenEscapeBound) {
    window.__quantLabFullscreenEscapeBound = true;
    window.addEventListener('keydown', event => {
      if (event.key !== 'Escape' || !document.querySelector('.ql-maximized-panel')) return;
      [...document.querySelectorAll('.st-key-right_dock button')]
        .find(button => button.textContent.includes('⛶'))?.click();
    });
  }
})();
</script>
"""


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
        if st.session_state.get("nav_page") not in PAGES:
            st.session_state["nav_page"] = PAGES[0]
        page = st.radio("功能导航", PAGES, label_visibility="collapsed", key="nav_page")
        st.html('<div class="ql-sidebar-label ql-sidebar-gap">RESEARCH SETUP / 研究参数</div>')
        market = st.selectbox("市场", ("A 股", "港股"), key="market_selection")
        st.session_state.setdefault(f"symbol_{market}", "600519" if market == "A 股" else "00700")
        labels = {}
        directory = None
        try:
            directory = security_directory(market)
            labels = dict(directory.rows)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            st.warning(str(exc))
        def code_changed():
            st.session_state["_security_selection_event"] = {"market": market, "symbol": st.session_state[f"symbol_{market}"]}
        current = st.session_state[f"symbol_{market}"]
        options = list(labels)
        if current and current not in options:
            options.append(current)
        symbol = (st.selectbox(
            "股票（代码 / 名称）", options, key=f"symbol_{market}",
            accept_new_options=True, on_change=code_changed,
            format_func=lambda code: f"{code} · {labels[code]}" if code in labels else code,
            placeholder="输入代码或名称搜索，也可直接输入新代码",
            help="常见大盘股票优先展示；候选是证券目录，不是买入推荐。未收录的代码可输入后选择新增项确认。",
        ) or "").strip()
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
        if directory is not None:
            st.caption(f"目录快照：{len(labels)} 只 · {directory.source} · 获取于 {beijing(directory.received_at)}；不含行情，不验证当前上市状态。")
            if directory.error:
                st.warning(directory.error)
        if st.button("更新股票候选目录", key="refresh_security_directory"):
            try:
                refreshed = security_directory(market, force=True)
                if refreshed.error:
                    st.warning(refreshed.error)
                else:
                    st.rerun()
            except (OSError, ValueError, KeyError, TypeError) as exc:
                st.warning(str(exc))
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
        if st.session_state.get("settings_error"):
            st.warning(st.session_state.pop("settings_error"))
        if not valid_symbol:
            st.caption("A 股请输入 6 位、港股请输入 5 位股票代码。")
        elif dates is None:
            st.caption("请选择完整的开始和结束日期。")
        else:
            source = "腾讯证券" if market == "A 股" else "东方财富"
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


def _toggle_deepseek_panel() -> None:
    opening = not st.session_state.get("deepseek_panel_open", False)
    st.session_state["deepseek_panel_open"] = opening
    if opening:
        st.session_state.setdefault("ai_workspace", "对话与辅导")


def _toggle_guide_panel() -> None:
    st.session_state["guide_panel_open"] = not st.session_state.get(
        "guide_panel_open", False
    )


def _toggle_notes_panel() -> None:
    st.session_state["notes_panel_open"] = not st.session_state.get("notes_panel_open", False)


def _toggle_settings() -> None:
    st.session_state["settings_open"] = not st.session_state.get("settings_open", False)


def _global_topbar() -> None:
    st.session_state.setdefault("deepseek_panel_open", False)
    st.session_state.setdefault("guide_panel_open", False)
    st.session_state.setdefault("notes_panel_open", False)
    st.session_state.setdefault("settings_open", False)
    st.session_state.setdefault("maximized_panel", None)
    with st.container(key="global_topbar"):
        settings, brand, workspace, guide, assistant, research = st.columns(
            [.48, 1.9, 3.1, 1.35, 1.3, 1.25], vertical_alignment="center", gap="small"
        )
        with settings:
            st.button("⚙", key="settings_toggle", width="stretch", on_click=_toggle_settings,
                      help="打开设置")
        with brand:
            st.html(
                '<div class="ql-topbar-brand"><span>Q/</span>'
                '<strong>Quant Lab CN/HK</strong></div>'
            )
        with workspace:
            st.html('<div class="ql-topbar-workspace">研究工作台</div>')
        with guide:
            st.button(
                "新手使用指引", key="guide_panel_toggle", width="stretch",
                on_click=_toggle_guide_panel,
                help="打开或关闭右侧新手使用指引；按住并左右拖动可与 DeepSeek 调换顺序。",
            )
        with assistant:
            st.button(
                "DeepSeek 助手", key="deepseek_panel_toggle", width="stretch",
                on_click=_toggle_deepseek_panel,
                help="打开或关闭右侧 DeepSeek 助手；按住并左右拖动可与使用指引调换顺序。只有点击发送才调用付费 API。",
            )
        with research:
            st.button("研究笔记", key="notes_panel_toggle", width="stretch",
                      on_click=_toggle_notes_panel,
                      help="打开或关闭研究笔记；按住并左右拖动可调整顺序。")
        st.html(TOPBAR_REORDER_JS, unsafe_allow_javascript=True)


def _render_right_dock(context: dict, bundle) -> None:
    guide_open = st.session_state.get("guide_panel_open", False)
    deepseek_open = st.session_state.get("deepseek_panel_open", False)
    notes_open = st.session_state.get("notes_panel_open", False)
    maximized = st.session_state.get("maximized_panel")
    if maximized:
        guide_open = maximized == "guide"
        deepseek_open = maximized == "deepseek"
        notes_open = maximized == "notes"
    if not (guide_open or deepseek_open or notes_open):
        return
    with st.container(key="right_dock"):
        if maximized:
            st.html('<span class="ql-maximized-panel"></span>')
        if guide_open:
            render_learning_panel()
            if st.session_state.get("active_learning_context"):
                context["learning_context"] = st.session_state["active_learning_context"]
        if deepseek_open:
            render_deepseek_panel(context, bundle)
        if notes_open:
            render_research_panel()
        st.html(DOCK_RESIZE_JS, unsafe_allow_javascript=True)


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
        "腾讯证券 · AKShare" if market == "A 股" else "东方财富 · AKShare"
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
    if not library_configured():
        render_library_setup()
        return
    initialize_settings()
    initialize_credentials()
    protect_research_widgets()
    _global_topbar()
    st.session_state.pop("_open_ai_page", None)
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

    st.session_state["_current_query"] = query
    if st.session_state.get("ai_followup_context") and st.session_state.get("ai_followup_query") != query:
        st.session_state.pop("ai_followup_context", None)

    latest_date = (
        bundle.frame["date"].iloc[-1].strftime("%Y-%m-%d")
        if bundle is not None and not bundle.frame.empty else None
    )
    st.session_state["active_data_fingerprint"] = None if page == "Quant Academy" else bundle_context(page, bundle).get("data_fingerprint")
    render_welcome()
    render_page_help(page)
    if page == "市场数据":
        _market_workspace(query, market, symbol, adjustment)
        bundle = st.session_state.get("loaded_bundle") if st.session_state.get("loaded_query") == query else None
    elif page == "Quant Academy":
        _header(page, market, symbol, latest_date)
        render_academy()
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
    context = experiment_context(record) if record else bundle_context(page, bundle)
    context["page"] = page
    if st.session_state.get("active_backtest_context"):
        context.update(st.session_state["active_backtest_context"])
    if st.session_state.get("active_analysis_context"):
        context["statistics"] = st.session_state["active_analysis_context"]
    if page == "Quant Academy":
        context = {"page": page, "lesson": st.session_state.get("academy_lesson", 0),
                   "data_status": "离线教学实验，不是股票行情。"}
    if st.session_state.get("active_learning_context"):
        context["learning_context"] = st.session_state["active_learning_context"]
    st.session_state["_current_ai_context"] = context
    _render_right_dock(context, bundle)
    if st.session_state.get("settings_open"):
        render_settings_panel()
