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
from quant_lab.metrics import summarize_prices, price_risk_metrics
from quant_lab.processing import DataValidationError
from quant_lab.ui_terminal import render_watchlist
from quant_lab import names
from quant_lab.market_data import normalize_symbol
from quant_lab.storage import list_watchlist
from quant_lab.ui_updates import initialize_settings, toggle_refresh, beijing, show_history_status
from quant_lab.ui_knowledge import render_knowledge
from quant_lab.ui_deepseek import initialize_credentials, render_deepseek_panel
from quant_lab.ai_context import bundle_context, experiment_context
from quant_lab.securities import security_directory
from quant_lab.ui_jobs import submit_task, take_result, cancel_task, render_background_tasks, loading_placeholder
from quant_lab.jobs import JobState
from quant_lab.ui_helpers import reset_main_scroll
from quant_lab.history_ranges import HISTORY_PRESETS, history_window
from quant_lab.ui_data_quality import render_history_quality, render_quality_summary
from quant_lab.ui_manual import render_manual_panel
from quant_lab.navigation import SECTIONS, MARKETS, RESEARCH, navigation_values, active_route
from quant_lab.desktop_loading import signal_frontend_ready
from quant_lab.ui_settings import (
    library_configured,
    render_library_setup,
    render_settings_panel,
    rerun_pending_settings,
)


CSS_PATH = Path(__file__).parent / "terminal.css"
PAGES = SECTIONS
ADJUSTMENTS = {"不复权": "", "前复权": "qfq", "后复权": "hfq"}

SIDEBAR_LAYOUT_JS = """
<script>
(() => {
  const root = document.documentElement;
  let observedSidebar = null;
  window.__quantLabSidebarResizeObserver?.disconnect();
  let frame = 0;
  const schedule = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => { frame = 0; sync(); });
  };
  const observer = new ResizeObserver(schedule);
  const sync = () => {
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    if (!sidebar || getComputedStyle(sidebar).display === 'none') return;
    if (sidebar !== observedSidebar) {
      if (sidebar.dataset.qlWidthReady !== '1') {
        sidebar.style.width = '248px';
        sidebar.style.flexBasis = '248px';
        sidebar.dataset.qlWidthReady = '1';
      }
      observer.disconnect();
      observer.observe(sidebar);
      observedSidebar = sidebar;
    }
    const width = sidebar.getBoundingClientRect().width;
    if (width > 0 && root.style.getPropertyValue('--ql-sidebar-width') !== `${width}px`) {
      root.style.setProperty('--ql-sidebar-width', `${width}px`);
    }
  };
  window.__quantLabSidebarResizeObserver = observer;
  window.__quantLabSidebarMutationObserver?.disconnect();
  const mutationObserver = new MutationObserver(schedule);
  const view = document.querySelector('[data-testid="stAppViewContainer"]');
  if (view) mutationObserver.observe(view, {childList:true});
  window.__quantLabSidebarMutationObserver = mutationObserver;
  if (window.__quantLabSidebarWindowResize) {
    window.removeEventListener('resize', window.__quantLabSidebarWindowResize);
  }
  window.__quantLabSidebarWindowResize = schedule;
  window.addEventListener('resize', schedule);
  sync();
  window.setTimeout(sync, 100);
  window.setTimeout(sync, 500);
})();
</script>
"""

DOCK_RESIZE_JS = """
<script>
(() => {
  const root = document.documentElement;
  const newest = selector => [...document.querySelectorAll(selector)].at(-1);
  const setup = (kind, minimum) => {
    const panel = newest(`.st-key-${kind}_side_panel`);
    const handle = panel?.querySelector(`.ql-resize-handle[data-panel="${kind}"]`);
    if (!panel || !handle || handle.dataset.bound === "1") return;
    handle.dataset.bound = "1";
    const property = `--ql-${kind}-width`;
    const storageKey = `quantlab.${kind}.panelWidth`;
    const stored = Number.parseFloat(localStorage.getItem(storageKey));

    const applyWidth = (requested, persist=false) => {
      const otherWidth = ['manual','deepseek','notes'].filter(value => value !== kind)
        .map(value => newest(`.st-key-${value}_side_panel`))
        .reduce((total, other) => total + (other ? other.getBoundingClientRect().width : 0), 0);
      const sidebar = document.querySelector('[data-testid="stSidebar"]');
      const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 0;
      const maximum = Math.max(minimum, window.innerWidth - sidebarWidth);
      const width = Math.round(Math.min(maximum, Math.max(minimum, requested)));
      root.style.setProperty(property, `${width}px`);
      if (persist) localStorage.setItem(storageKey, String(width));
      window.__quantLabApplyPanelOrder?.();
    };
    if (Number.isFinite(stored)) applyWidth(stored);

    handle.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = panel.getBoundingClientRect().width;
      let pendingWidth = startWidth;
      let frame = 0;
      handle.classList.add("is-dragging");
      const move = (next) => {
        pendingWidth = startWidth - (next.clientX - startX);
        if (!frame) frame = requestAnimationFrame(() => { frame = 0; applyWidth(pendingWidth); });
      };
      const stop = () => {
        if (frame) cancelAnimationFrame(frame);
        applyWidth(pendingWidth, true);
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
      applyWidth(panel.getBoundingClientRect().width + delta, true);
    });
  };
  setup("manual", 240);
  setup("deepseek", 240);
  setup("notes", 260);
  window.__quantLabObserveDock?.();
  requestAnimationFrame(() => window.__quantLabApplyPanelOrder?.());
})();
</script>
"""

TOPBAR_REORDER_JS = """
<script>
(() => {
  const root = document.documentElement;
  const newest = selector => [...document.querySelectorAll(selector)].at(-1);
  const storageKey = "quantlab.dock.panelOrder";
  const kinds = ['manual', 'deepseek', 'notes'];
  const describeControls = () => {
    const settings = newest('.st-key-settings_toggle button');
    if (settings) {
      const left = Math.max(12, Math.min(settings.getBoundingClientRect().left, window.innerWidth - 564));
      if (root.style.getPropertyValue('--ql-settings-left') !== `${left}px`) root.style.setProperty('--ql-settings-left', `${left}px`);
    }
    const descriptions = {settings_toggle:'打开设置',left_sidebar_toggle:'显示或隐藏左侧导航栏',
      manual_panel_maximize:'最大化或恢复使用手册',manual_panel_close:'关闭使用手册',
      deepseek_panel_maximize:'最大化或恢复DeepSeek助手',deepseek_panel_close:'关闭DeepSeek助手',
      notes_panel_maximize:'最大化或恢复研究笔记',notes_panel_close:'关闭研究笔记'};
    Object.entries(descriptions).forEach(([key, text]) => {
      newest(`.st-key-${key} button`)?.setAttribute('aria-description', text);
    });
  };
  const readOrder = () => {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey));
      return Array.isArray(value) && kinds.every(kind => value.includes(kind)) ? value : [...kinds];
    } catch (_) { return [...kinds]; }
  };
  let order = readOrder();
  let savedOrder = JSON.stringify(order);

  const applyOrder = (animate=true) => {
    describeControls();
    const buttons = Object.fromEntries(kinds.map(kind => [kind,
      newest(`.st-key-${kind}_panel_toggle button`)]));
    const before = animate ? Object.fromEntries(kinds.map(kind => [kind, buttons[kind]?.getBoundingClientRect()])) : {};
    order.forEach((kind, index) => {
      const column = buttons[kind]?.closest('[data-testid="stColumn"]');
      if (column) column.style.order = String(index);
    });
    const present = order.filter(kind => newest(`.st-key-${kind}_side_panel`));
    kinds.forEach(kind => buttons[kind]?.setAttribute('aria-pressed',String(present.includes(kind))));
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    const sidebarWidth = sidebar && getComputedStyle(sidebar).display !== 'none' ? sidebar.getBoundingClientRect().width : 0;
    const mainMinimum = Number.parseFloat(getComputedStyle(root).getPropertyValue('--ql-main-min')) || 560;
    const available = Math.max(240, window.innerWidth - sidebarWidth);
    const maximized = !!newest('.ql-maximized-panel');
    const desired = Object.fromEntries(present.map(kind => [kind,
      Number.parseFloat(getComputedStyle(root).getPropertyValue(`--ql-${kind}-width`)) || 320]));
    const requested = newest('.ql-dock-active')?.dataset.panel;
    const active = present.includes(requested) ? requested : present[0];
    root.dataset.qlDockCompact = 'false';
    root.dataset.qlMaximized = String(maximized);
    let total = 0;
    order.forEach((kind,index) => {
      const copies = [...document.querySelectorAll(`.st-key-${kind}_side_panel`)];
      copies.slice(0, -1).forEach(stale => { stale.style.display='none'; stale.inert=true; });
      const panel = copies.at(-1);
      if (!panel) return;
      panel.style.display = '';
      panel.setAttribute('aria-hidden', 'false');
      panel.inert = false;
      const button = buttons[kind];
      if (button) button.setAttribute('aria-pressed', 'true');
      const width = maximized ? available : Math.min(available,desired[kind]);
      panel.style.width = `${width}px`;
      panel.parentElement.style.order = String(index);
      total += width;
    });
    const mainWidth = maximized ? 0 : Math.max(mainMinimum,available-total);
    root.dataset.qlDockOrder = order.join('-');
    root.style.setProperty('--ql-dock-total-width', `${total}px`);
    root.style.setProperty('--ql-main-width', `${mainWidth}px`);
    root.style.setProperty('--ql-track-width', `${Math.max(available,mainWidth+total)}px`);
    const reveal = newest('.ql-dock-reveal');
    if(reveal?.dataset.panel && root.dataset.qlRevealToken!==reveal.dataset.token) {
      const target=newest(`.st-key-${reveal.dataset.panel}_side_panel`);
      if(target){root.dataset.qlRevealToken=reveal.dataset.token;requestAnimationFrame(()=>target.scrollIntoView({inline:'nearest',block:'nearest',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}));}
    }
    const serializedOrder = JSON.stringify(order);
    if (savedOrder !== serializedOrder) {
      localStorage.setItem(storageKey, serializedOrder);
      savedOrder = serializedOrder;
    }
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
  window.__quantLabObserveDock = () => {
    window.__quantLabDockObserver?.disconnect();
    const dock = document.querySelector('.st-key-right_dock');
    if (!dock) return;
    let scheduled = false;
    window.__quantLabDockObserver = new MutationObserver(() => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => { scheduled = false; applyOrder(false); });
    });
    window.__quantLabDockObserver.observe(dock, {childList:true, subtree:true});
  };
  window.__quantLabObserveDock();

  const bind = (button, kind) => {
    if (button.dataset.reorderBound === '1') return;
    button.dataset.reorderBound = '1';
    button.setAttribute('aria-description', '打开或切换面板；再次点击可收起。按住拖动可调整三个面板顺序');
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
  let pending = false;
  window.__quantLabTopbarObserver = new MutationObserver(() => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; initialize(); });
  });
  const topbar = document.querySelector('.st-key-global_topbar');
  if (topbar) window.__quantLabTopbarObserver.observe(topbar, {childList:true, subtree:true});
  if (window.__quantLabDockWindowResize) window.removeEventListener('resize', window.__quantLabDockWindowResize);
  window.__quantLabDockWindowResize = () => requestAnimationFrame(() => applyOrder(false));
  window.addEventListener('resize', window.__quantLabDockWindowResize);
  if (!window.__quantLabFullscreenEscapeBound) {
    window.__quantLabFullscreenEscapeBound = true;
    window.addEventListener('keydown', event => {
      if (event.key !== 'Escape' || document.querySelector('[role="dialog"]')) return;
      const overlayClose = document.querySelector('.st-key-history_fullscreen_close button') ||
        document.querySelector('.st-key-settings_close button');
      if (overlayClose) { event.preventDefault(); overlayClose.click(); return; }
      if (!document.querySelector('.ql-maximized-panel')) return;
      [...document.querySelectorAll('.st-key-right_dock button')]
        .find(button => button.textContent.includes('⛶'))?.click();
    });
  }
})();
</script>
"""


def _protect_session_widgets() -> None:
    """Keep active research and AI controls across Streamlit page redraws."""
    value_keys = {
        "academy_lesson", "deepseek_api_key", "deepseek_remember",
        "deepseek_prompt", "deepseek_answer_mode", "deepseek_attach",
        "ds_model_select", "ds_model_manual", "ai_workspace",
        "learning_mode", "refresh_enabled", "refresh_interval_seconds", "academy_search", "academy_group",
        "history_preset", "history_start", "history_end",
        "us_source_mode", "us_candidate_symbol", "us_teaching_symbol", "us_calendar_day", "us_research_mode",
        "us_kind", "us_short", "us_long", "us_cash", "us_commission", "us_minimum", "us_slippage", "us_rebalance",
        "workspace_name","market_selection","compare_market","compare_codes","compare_benchmark","compare_start","compare_end","compare_adjustment","compare_window",
        "nav_section","research_page","manual_section","manual_category","manual_search_query",
        "compare_fraction","compare_frequency","compare_cash","compare_commission","compare_minimum","compare_buyfee","compare_sellfee","compare_slippage","compare_limit",
        "comparison_watch_open",
        "lab_mode","lab_kind","lab_short","lab_long","lab_shorts","lab_longs","lab_score","lab_fraction","lab_train","lab_test","lab_folds","lab_stress",
    }
    prefixes = (
        "strategy_", "backtest_", "portfolio_", "model_", "research_", "academy_parameter_",
        "ai_question", "cost_", "symbol_", "ds_effort_", "history_adjustment_",
    )
    value_keys.update({"us_price_period","us_price_start","us_price_end","us_price_symbol","us_price_page",
        "us_compare_codes","us_compare_start","us_compare_end","us_compare_baseline","us_compare_window",
        "us_compare_chart","us_compare_detail","us_price_port_frequency","us_price_port_fraction",
        "us_price_bt_fraction","us_price_ml_fraction","us_price_val_fraction","us_price_val_shorts",
        "us_price_val_longs","us_price_val_train","us_price_val_test","us_price_val_folds","us_price_validation_selection"})
    for prefix in ("us_price_signal","us_price_bt","us_price_val"):
        value_keys.update(prefix+"_"+name for name in ("kind","short","long"))
    for prefix in ("us_price_bt","us_price_port","us_price_val"):
        value_keys.update(prefix+"_"+name for name in ("cash","commission","minimum","slip","sellfee"))
    for key in list(st.session_state):
        if key.startswith(prefixes) or key in value_keys:
            st.session_state[key] = st.session_state[key]


def _metric(label: str, value: str, note: str, accent: str = "") -> None:
    st.html(
        f'<div class="ql-metric {accent}">'
        f'<div class="ql-metric-label">{escape(label)}</div>'
        f'<div class="ql-metric-value">{escape(value)}</div>'
        f'<div class="ql-metric-note">{escape(note)}</div>'
        "</div>"
    )


def _select_market_changed():
    from quant_lab.ui_comparison import change_comparison_market
    change_comparison_market(st.session_state["market_selection"])


def _sidebar() -> tuple[str, str, str, tuple[date, date] | None, str, bool]:
    with st.sidebar:
        st.html('<div class="ql-sidebar-heading">工作区</div>')
        section = st.radio("功能导航", PAGES, label_visibility="collapsed", key="nav_section")
        if section == "多股票比较":
            from quant_lab.ui_comparison import _market_change
            market = st.selectbox("比较市场", MARKETS, key="compare_market", on_change=_market_change)
            st.session_state["nav_page"] = section
            return section, market, "", None, "", False
        with st.expander("研究参数", expanded=False):
            market = st.selectbox("市场", MARKETS, key="market_selection", on_change=_select_market_changed)
            page = active_route(section, market, st.session_state["research_page"])
            st.session_state["nav_page"] = page
            market, symbol, dates, adjustment, clicked = _research_controls()
    return page, market, symbol, dates, adjustment, clicked


def _research_controls():
    market = st.session_state["market_selection"]
    symbol_key = "us_price_symbol" if market == "美股" else f"symbol_{market}"
    st.session_state.setdefault(symbol_key, {"A 股": "600519", "港股": "00700", "美股": "AAPL"}[market])
    from quant_lab.ui_security_picker import render_security_picker
    symbol = render_security_picker(market, symbol_key).strip()
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    initial_start, initial_end = history_window(today, 1)
    st.session_state.setdefault("history_start", initial_start)
    st.session_state.setdefault("history_end", initial_end)
    st.selectbox("快捷历史区间", tuple(HISTORY_PRESETS), key="history_preset", on_change=_apply_history_preset)
    start = st.date_input("开始日期", value=None, min_value=date(1900, 1, 1), max_value=today,
                          key="history_start", format="YYYY-MM-DD", on_change=_custom_history_dates)
    end = st.date_input("结束日期", value=None, min_value=date(1900, 1, 1), max_value=today,
                        key="history_end", format="YYYY-MM-DD", on_change=_custom_history_dates)
    dates = (start, end) if isinstance(start, date) and isinstance(end, date) else None
    if dates and start > end:
        st.warning("开始日期不能晚于结束日期。")
    adjustment = ADJUSTMENTS[st.selectbox("价格口径", ("不复权",) if market == "美股" else tuple(ADJUSTMENTS),
                                       key="history_adjustment_" + market, disabled=market == "美股")]
    if market == "美股":
        st.caption("USD · 当前来源仅提供不复权历史价格")
    try:
        if market == "美股":
            from quant_lab.us_market import normalize_us_symbol
            symbol = normalize_us_symbol(symbol)
        else:
            symbol = normalize_symbol(market, symbol)
        valid_symbol = True
    except ValueError:
        valid_symbol = False
    can_load = (
        valid_symbol and dates is not None and dates[0] <= dates[1]
    )
    clicked = st.button("加载真实历史日线", disabled=not can_load, width="stretch")
    refresh = st.button("立即更新", key="us_history_refresh" if market == "美股" else "history_sidebar_refresh",
        disabled=not can_load, width="stretch", help="绕过价格与名称查询缓存；相同的进行中请求会合并。")
    st.session_state["_us_force_refresh" if market == "美股" else "_history_force_refresh"] = refresh
    directory_result = take_result("directory", market)
    if directory_result and directory_result.state == JobState.FAILED:
        st.warning(directory_result.error)
    if valid_symbol:
        name_key = (market, symbol)
        name_result = take_result("name", name_key)
        if name_result and name_result.state == JobState.FAILED:
            st.warning(name_result.error)
        seen_names = st.session_state.setdefault("_name_checks", set())
        if (name_key not in seen_names and not names.NAME_CACHE.fresh(market, symbol)) or refresh:
            submit_task("name", name_key, names.security_name, market, symbol, force=refresh)
            seen_names.add(name_key)
        st.caption("当前选择：" + names.cached_security_label(market, symbol))
        st.session_state["_selected_security"] = (market, symbol)
        name_error = names.NAME_CACHE.error(market, symbol)
        if name_error:
            st.warning(name_error)
    try:
        watch_items = list_watchlist()
    except (OSError, ValueError, sqlite3.Error):
        watch_items = []
    if watch_items:
        def choose_watch():
            chosen = st.session_state.get("sidebar_watch")
            if chosen:
                st.session_state["market_selection"] = chosen[0]
                st.session_state["us_price_symbol" if chosen[0] == "美股" else f"symbol_{chosen[0]}"] = chosen[1]
                _select_market_changed()
        st.selectbox("从自选股选择", [None] + watch_items, key="sidebar_watch", on_change=choose_watch,
                     format_func=lambda item: "手动输入" if item is None else names.cached_security_label(*item))
    if st.session_state.get("settings_error"):
        st.warning(st.session_state.pop("settings_error"))
    if not valid_symbol:
        st.caption("美股请输入代码，例如 AAPL、MSFT、BRK.B。" if market == "美股" else
                   "A 股请输入 6 位数字；港股可输入 1–5 位数字，程序会自动补足为 5 位。")
    elif dates is None:
        st.caption("请选择完整的开始和结束日期。")
    st.caption("历史日线 · 本地研究")
    return market, symbol, dates, adjustment, clicked


def _apply_history_preset():
    years = HISTORY_PRESETS.get(st.session_state.get("history_preset", "1 年"))
    if years is not None:
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        start, end = history_window(today, years)
        st.session_state["history_start"], st.session_state["history_end"] = start, end


def _custom_history_dates():
    st.session_state["history_preset"] = "自定义"


def _header(page: str, market: str, symbol: str, latest_date: str | None) -> None:
    page_title = "市场数据实验室" if page == "市场数据" else RESEARCH.get(page, page)
    status = f"历史数据截至 {latest_date}" if latest_date else "尚未加载真实行情"
    status_class = ""
    st.html(
        '<div class="ql-header">'
        '<div>'
        f'<h1>{escape(page_title)}</h1>'
        '<p>历史日线研究与模拟实验</p></div>'
        '<div class="ql-header-context">'
        '<span class="ql-context-label">当前研究标的</span>'
        f'<strong>{escape(names.cached_security_label(market, symbol) if symbol else "未填写")}</strong>'
        f'<span class="ql-context-status {status_class}">{escape(status)}</span>'
        '</div></div>'
    )


def _toggle_deepseek_panel() -> None:
    opening = _toggle_dock("deepseek")
    if opening:
        st.session_state["ai_workspace"] = "对话与辅导"


def _toggle_manual_panel() -> None:
    _toggle_dock("manual")


def _toggle_notes_panel() -> None:
    opening = _toggle_dock("notes")
    if opening:
        st.session_state["notes_view"] = "editor"


def _toggle_dock(kind):
    current = st.session_state.get("maximized_panel") or st.session_state.get("active_dock_panel", "manual")
    opening = not (st.session_state.get(f"{kind}_panel_open", False) and current == kind)
    st.session_state[f"{kind}_panel_open"] = opening
    if opening:
        st.session_state["active_dock_panel"] = kind
        if st.session_state.get("maximized_panel") and st.session_state["maximized_panel"] != kind:
            st.session_state["maximized_panel"] = None
        st.session_state["_dock_reveal"] = kind
    elif st.session_state.get("maximized_panel") == kind:
        st.session_state["maximized_panel"] = None
    return opening


def _toggle_left_sidebar() -> None:
    st.session_state["left_sidebar_visible"] = not st.session_state.get(
        "left_sidebar_visible", True
    )


def _toggle_settings() -> None:
    st.session_state["settings_open"] = not st.session_state.get("settings_open", False)


def _global_topbar() -> None:
    st.session_state.setdefault("deepseek_panel_open", False)
    st.session_state.setdefault("manual_panel_open", True)
    st.session_state.setdefault("notes_panel_open", False)
    st.session_state.setdefault("left_sidebar_visible", True)
    st.session_state.setdefault("settings_open", False)
    st.session_state.setdefault("maximized_panel", None)
    active = st.session_state.setdefault("active_dock_panel", "manual")
    if not st.session_state.get(f"{active}_panel_open", False):
        st.session_state["active_dock_panel"] = next((kind for kind in ("manual", "deepseek", "notes")
            if st.session_state.get(f"{kind}_panel_open", False)), "manual")
    with st.container(key="global_topbar"):
        left, workspace, right = st.columns([3, 2, 4], vertical_alignment="center", gap="small")
        with left, st.container(key="topbar_left"):
            brand, sidebar_toggle, settings = st.columns([3, .65, .65], vertical_alignment="center", gap="small")
            with brand:
                import base64
                logo = base64.b64encode((Path(__file__).resolve().parents[1] / "assets" / "quantlab.png").read_bytes()).decode()
                st.html(f'<div class="ql-topbar-brand"><img src="data:image/png;base64,{logo}" alt="Quant Lab"><strong>QUANT LAB</strong></div>')
            with sidebar_toggle:
                st.button("▥", key="left_sidebar_toggle", width="stretch", on_click=_toggle_left_sidebar)
            with settings:
                st.button("⚙", key="settings_toggle", width="stretch", on_click=_toggle_settings)
        with workspace:
            st.html('<div class="ql-topbar-workspace">研究工作台</div>')
        with right, st.container(key="topbar_tools"):
            manual, assistant, research = st.columns([1, 1.2, 1], vertical_alignment="center", gap="small")
            with manual:
                st.button("使用手册", icon=":material/menu_book:", key="manual_panel_toggle", width="stretch", on_click=_toggle_manual_panel)
            with assistant:
                st.button("DeepSeek 助手", icon=":material/smart_toy:", key="deepseek_panel_toggle", width="stretch", on_click=_toggle_deepseek_panel)
            with research:
                st.button("研究笔记", icon=":material/edit_note:", key="notes_panel_toggle", width="stretch", on_click=_toggle_notes_panel)
        sidebar_state = "visible" if st.session_state["left_sidebar_visible"] else "hidden"
        st.html(f'<span class="ql-left-sidebar-state ql-left-sidebar-{sidebar_state}"></span>')
        st.html(f'<span class="ql-dock-active" data-panel="{st.session_state["active_dock_panel"]}"></span>')
        reveal = st.session_state.pop("_dock_reveal", "")
        st.html(f'<span class="ql-dock-reveal" data-panel="{reveal}" data-token="{time.monotonic_ns() if reveal else 0}"></span>')
        st.html(SIDEBAR_LAYOUT_JS, unsafe_allow_javascript=True)
        st.html(TOPBAR_REORDER_JS, unsafe_allow_javascript=True)


def _render_right_dock(context: dict, bundle) -> None:
    manual_open = st.session_state.get("manual_panel_open", False)
    deepseek_open = st.session_state.get("deepseek_panel_open", False)
    notes_open = st.session_state.get("notes_panel_open", False)
    maximized = st.session_state.get("maximized_panel")
    if maximized:
        manual_open = maximized == "manual"
        deepseek_open = maximized == "deepseek"
        notes_open = maximized == "notes"
    if not (manual_open or deepseek_open or notes_open):
        st.html('<script>requestAnimationFrame(() => window.__quantLabApplyPanelOrder?.());</script>', unsafe_allow_javascript=True)
        return
    with st.container(key="right_dock"):
        if maximized:
            st.html('<span class="ql-maximized-panel"></span>')
        if manual_open:
            render_manual_panel()
        if deepseek_open:
            render_deepseek_panel(context, bundle)
        if notes_open:
            from quant_lab.ui_research import render_research_panel
            render_research_panel()
        st.html(DOCK_RESIZE_JS, unsafe_allow_javascript=True)


def _empty_candlestick() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=520,
        paper_bgcolor="#1C1F22",
        plot_bgcolor="#1C1F22",
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
                "font": {"color": "#929AA3", "size": 20},
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


def _render_history_chart(bundle, *, candlestick=False):
    builder = history_candlestick_chart if candlestick else history_price_chart
    figure = builder(bundle.frame, bundle.currency)
    figure.update_layout(title_text=names.cached_security_label(bundle.market, bundle.symbol, bundle.company_name),
                         uirevision=repr(st.session_state.get("_current_query")))
    st.plotly_chart(figure, width="stretch", theme=None,
        key="market_candle" if candlestick else "market_price",
        config={"displaylogo": False, "scrollZoom": False},
        alt="当前选中区间的历史日线 K 线与成交量。" if candlestick else "当前选中区间的历史收盘价与成交量。")


def _main_page(
    bundle: HistoryBundle | None, error: str | None,
    market: str, symbol: str, adjustment: str, *, session_cache=True,
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
    demonstration = bool(
        has_data
        and any(
            word in bundle.source.lower()
            for word in ("模拟", "演示", "教学", "demo", "simulation", "teaching")
        )
    )
    real_data = has_data and not demonstration
    if error:
        st.error(error)
    elif history is not None and history.empty:
        st.info("该股票在所选日期内没有历史交易记录。请调整日期范围后重试。")

    overview_tag = (
        f"已加载真实历史数据 · {adjustment_label}" if real_data else
        f"已加载模拟/教学数据 · {adjustment_label}" if demonstration else
        "未加载真实行情"
    )
    render_quality_summary(bundle)
    st.html(
        '<div class="ql-section-head"><div>'
        f'<h2>研究概览</h2></div><span class="ql-tag">{overview_tag}</span></div>'
    )
    if has_data:
        summary = summarize_prices(history)
        try:
            volatility, drawdown = price_risk_metrics(history["close"])
        except ValueError as exc:
            st.warning(f"风险指标暂不可计算：{exc}")
            volatility, drawdown = None, None
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
            ("年化波动率估计", "—" if volatility is None else f"{volatility:.2%}", "样本标准差 · √252 近似", ""),
            ("历史最大回撤", "—" if drawdown is None else f"{drawdown:.2%}", "当前价格口径 · 历史样本", ""),
            ("样本交易日", str(summary.trading_days), "仅统计返回的交易日", ""),
        )
    else:
        metrics = (
            ("区间简单价格收益率", "--", "加载日线后计算", "ql-accent-neutral"),
            ("年化波动率估计", "--", "等待真实行情", ""),
            ("历史最大回撤", "--", "等待真实行情", ""),
            ("样本交易日", "--", "等待真实行情", ""),
        )
    with st.container(key="market_metrics"):
        for col, (label, value, note, accent) in zip(st.columns(4, gap="small"), metrics):
            with col:
                _metric(label, value, note, accent)
    chart_col = st.container()
    info_col = st.expander("数据来源、价格口径与区间信息")
    with chart_col:
        with st.container(border=True):
            legend = (
                f"{source} · 真实历史日线" if real_data else
                f"{source} · 模拟/教学数据" if demonstration else
                "模拟序列 · 无单位"
            )
            st.html(
                '<div class="ql-panel-header"><div>'
                f'<h2>行情图表</h2></div><span class="ql-legend">{legend}</span></div>'
            )
            if has_data:
                price_tab, candle_tab = st.tabs(("收盘价与成交量", "日 K 线"), default="日 K 线", key="market_chart_tabs", on_change="rerun")
                with price_tab:
                    if price_tab.open:
                        _render_history_chart(bundle)
                with candle_tab:
                    if candle_tab.open:
                        _render_history_chart(bundle, candlestick=True)
                provenance_note = "模拟/教学数据，不是上游真实行情。" if demonstration else "图表不是实时行情。"
                st.caption(f"来源：{source}；{adjustment_label}价格；红涨绿跌。{provenance_note}")
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
        status_class = "ql-status-ok" if real_data else ""
        status_text = (
            "已加载真实历史数据" if real_data else
            "已加载模拟/教学数据" if demonstration else
            "尚未加载真实行情"
        )
        data_type = f"{market}股票 · {'模拟/教学日线' if demonstration else '历史日线'}"
        latest_label = "最新样本日期" if demonstration else "最新交易日"
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title">'
                '<h2>数据说明</h2></div>'
                f'<div class="ql-status-banner {status_class}"><span>●</span> {status_text}</div>'
                f'<div class="ql-info-row"><span>数据类型</span><strong>{data_type}</strong></div>'
                f'<div class="ql-info-row"><span>数据来源</span><strong>{source}</strong></div>'
                f'<div class="ql-info-row"><span>本地缓存</span><strong>{"是" if bundle is not None and bundle.cached else "否"}</strong></div>'
                f'<div class="ql-info-row"><span>价格口径</span><strong>{adjustment_label}</strong></div>'
                f'<div class="ql-info-row"><span>价格币种</span><strong>{currency} · {money}/股</strong></div>'
                f'<div class="ql-info-row"><span>{latest_label}</span><strong>{latest}</strong></div>'
                f'<div class="ql-info-row"><span>接收时间（北京时间）</span><strong>{received}</strong></div>'
                '<div class="ql-info-row"><span>延迟状态</span><strong>历史日线；确切延迟未知</strong></div>'
                '<div class="ql-info-row"><span>成交量单位</span><strong>股</strong></div>'
                '<div class="ql-info-row"><span>实时行情</span><strong>不提供</strong></div>'
            )
            if has_data:
                st.html(f'<div class="ql-info-row"><span>区间最高 / 最低</span><strong>{money}{summary.period_high:,.2f} / {money}{summary.period_low:,.2f}</strong></div>')
        with st.container(border=True):
            st.html(
                '<div class="ql-info-title">'
                '<h2>研究提示</h2></div>'
                '<div class="ql-note"><b>01</b><span>收益率使用首尾两个实际交易日的收盘价。</span></div>'
                '<div class="ql-note"><b>02</b><span>页面收益率不等同含分红的总回报或可实现收益。</span></div>'
                '<div class="ql-note"><b>03</b><span>不同复权口径不可直接混用；回测成交始终用原始价格。</span></div>'
            )

    with st.container(border=True):
        table_tag = f"{len(history)} 条教学记录" if demonstration else f"{len(history)} 条真实记录" if has_data else "空表 · 等待数据"
        st.html(
            '<div class="ql-panel-header"><div>'
            f'<h2>历史数据</h2></div><span class="ql-tag">{table_tag}</span></div>'
        )
        if has_data:
            table = _display_history(history, currency)
            table.insert(0, "股票", names.cached_security_label(market, symbol, bundle.company_name))
            first = table["日期"].iloc[0].replace("-", "")
            last = table["日期"].iloc[-1].replace("-", "")
            from quant_lab.ui_history_table import render_history_table
            render_history_table(table, f"{market}_{symbol}_{first}_{last}_{adjustment or 'raw'}.csv")
            date_note = "日期为模拟/教学样本日期" if demonstration else "日期以实际交易日为准"
            st.caption(f"{date_note}。价格单位：{unit}/股；成交量：股；成交额：{unit}。")
        else:
            st.dataframe(
                pd.DataFrame(columns=["日期", "开盘价", "最高价", "最低价", "收盘价", "成交量"]),
                width="stretch", hide_index=True, height=160,
            )
            st.caption("加载并验证真实历史行情后可查看和导出 CSV。")
    show_history_status(bundle, st.session_state.get("history_next_attempt"), session_cache=session_cache)
    render_history_quality(bundle)
    render_watchlist(market, symbol)
    if st.session_state.get("learning_mode", True):
        render_knowledge("simple_return", summary.simple_return if has_data else None,
                         key="market", observations=len(history) if has_data else None)


def _market_workspace(query, market, symbol, adjustment):
    interval = st.session_state.get("refresh_interval_seconds", 300)
    auto = st.session_state.get("refresh_enabled", True)

    @st.fragment(run_every=interval if auto else None)
    def body():
        with st.container(key="market_workspace"):
            current = st.session_state.get("loaded_query") == query
            bundle = st.session_state.get("loaded_bundle") if current else None
            error = st.session_state.get("load_error") if current else None
            latest = str(bundle.frame.date.iloc[-1].date()) if bundle is not None and not bundle.frame.empty else None
            _header("市场数据", market, symbol, latest)
            wait = st.session_state.get("history_manual_at", float('-inf')) + 5 - time.monotonic()
            first, second, _ = st.columns([1.25, 1.25, 4.5])
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
                _submit_history(query, force=True)
                st.rerun(scope="app")
            if "history" in st.session_state.get("_task_tickets", {}) and bundle is None:
                loading_placeholder(350)
            _main_page(bundle, error, market, symbol, adjustment, session_cache=not updated)
    body()


def _submit_history(query, *, force=False):
    if force:
        submit_task("history", query, fetch_history, *query, force=True)
    else:
        submit_task("history", query, fetch_history, *query)
    st.session_state["_history_task_query"] = query
    st.session_state["history_next_attempt"] = datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(seconds=st.session_state["refresh_interval_seconds"])


def _consume_history(query):
    outcome = take_result("history", query)
    if outcome is None:
        return
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    if outcome.state == JobState.SUCCEEDED:
        fetched = outcome.result
        st.session_state["loaded_bundle"] = replace(fetched, company_name=names.cached_security_name(fetched.market, fetched.symbol))
        st.session_state["loaded_query"] = query
        st.session_state["load_error"] = fetched.update_error
        st.session_state["_history_loaded_this_run"] = True
    elif outcome.state == JobState.FAILED:
        error = outcome.error
        previous = st.session_state.get("loaded_bundle") if st.session_state.get("loaded_query") == query else None
        if previous is not None:
            previous = replace(previous, update_result="请求失败", update_error=error, last_attempt_at=now, cached=True)
        st.session_state["loaded_bundle"] = previous
        st.session_state["loaded_query"] = query
        st.session_state["load_error"] = error


def render_app() -> None:
    st.set_page_config(
        page_title="Quant Lab",
        page_icon=str(Path(__file__).resolve().parents[1] / "assets" / "quantlab.png"),
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.html(CSS_PATH)
    if not library_configured():
        render_library_setup()
        signal_frontend_ready("library_setup")
        return
    initialize_settings()
    from quant_lab.ui_workspaces import initialize_workspaces
    initialize_workspaces()
    if not st.session_state.get("_navigation_initialized"):
        st.session_state.update(navigation_values(dict(st.session_state)))
        st.session_state["_comparison_draft_market"] = st.session_state["market_selection"]
        st.session_state["_navigation_initialized"] = True
    rerun_pending_settings()
    initialize_credentials()
    _protect_session_widgets()
    _global_topbar()
    st.session_state.pop("_open_ai_page", None)
    page, market, symbol, dates, adjustment, clicked = _sidebar()
    with st.container(key="workbench_scroller"):
        with st.container(key="workbench_track"):
            with st.container(key="main_workspace"):
                if st.session_state["nav_section"] == "研究工作台":
                    research_page = st.radio("研究内容", tuple(RESEARCH), key="research_page", horizontal=True,
                                    format_func=RESEARCH.get, label_visibility="collapsed")
                    page = active_route("研究工作台", market, research_page)
                    st.session_state["nav_page"] = page
                bundle: HistoryBundle | None = None
                error: str | None = None
                query = None
                st.session_state["active_backtest_context"] = None
                st.session_state["active_analysis_context"] = None
                st.session_state["active_learning_context"] = None
                record = None
                if market == "美股" and page != "多股票比较":
                    from quant_lab.ui_us_prices import sync_us_prices
                    query = sync_us_prices(symbol, dates, clicked, st.session_state.pop("_us_force_refresh", False))
                elif dates is not None and market != "美股":
                    query = (market, symbol, dates[0], dates[1], adjustment)
                    force = st.session_state.pop("_history_force_refresh", False)
                    if clicked or force:
                        _submit_history(query, force=force)
                    _consume_history(query)
                    if st.session_state.get("loaded_query") == query:
                        bundle = st.session_state.get("loaded_bundle")
                        error = st.session_state.get("load_error")
                        if bundle is not None:
                            current_name = names.cached_security_name(market, symbol)
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
                base_context = bundle_context(page, bundle)
                context_bundle = bundle
                st.session_state["active_data_fingerprint"] = None if page == "Quant Academy" else base_context.get("data_fingerprint")
                if page == "市场数据":
                    _market_workspace(query, market, symbol, adjustment)
                    bundle = st.session_state.get("loaded_bundle") if st.session_state.get("loaded_query") == query else None
                elif page == "Quant Academy":
                    from quant_lab.ui_learning import render_academy
                    render_academy()
                elif page == "美股数据":
                    from quant_lab.ui_us_prices import render_us_prices
                    render_us_prices()
                elif page == "美股研究":
                    from quant_lab.ui_us import render_us_research
                    render_us_research(RESEARCH[st.session_state["research_page"]])
                elif page == "多股票比较":
                    from quant_lab.ui_comparison import render_comparison
                    render_comparison()
                else:
                    _header(page, market, symbol, latest_date)
                    if error:
                        st.warning(error)
                    if page == "策略实验室":
                        from quant_lab.ui_strategy import render_strategy
                        render_strategy(bundle)
                    elif page == "历史回测":
                        from quant_lab.ui_strategy import render_backtest
                        render_backtest(bundle)
                    elif page == "风险与组合":
                        from quant_lab.ui_analysis import render_risk
                        render_risk(bundle)
                    elif page == "统计与机器学习":
                        from quant_lab.ui_analysis import render_statistics
                        render_statistics(bundle)
                    elif page == "研究实验台":
                        from quant_lab.ui_experiments import render_experiment_lab
                        render_experiment_lab(bundle)
                context = experiment_context(record) if record else base_context if bundle is context_bundle else bundle_context(page, bundle)
                context["page"] = page
                if st.session_state.get("active_backtest_context"):
                    context.update(st.session_state["active_backtest_context"])
                if st.session_state.get("active_analysis_context"):
                    context["statistics"] = st.session_state["active_analysis_context"]
                if page == "Quant Academy":
                    context = {"page": page, "lesson": st.session_state.get("academy_lesson", 0),
                               "data_status": "离线教学实验，不是股票行情。"}
                if page in ("美股研究", "美股数据"):
                    context=st.session_state.get("active_us_context",{"page":page,"data_status":"尚未加载合格真实美股数据"})
                    st.session_state["active_data_fingerprint"]=context.get("data_fingerprint")
                if page == "多股票比较":
                    context=st.session_state.get("active_comparison_context",{"page":page,"data_status":"尚未加载比较输入"})
                    st.session_state["active_data_fingerprint"]=context.get("data_fingerprint")
                if page == "研究实验台":
                    context=st.session_state.get("active_lab_context",{"page":page,"data_status":"尚未完成研究验证"})
                    st.session_state["active_data_fingerprint"]=context.get("data_fingerprint")
                if st.session_state.get("active_learning_context"):
                    context["learning_context"] = st.session_state["active_learning_context"]
                st.session_state["_current_ai_context"] = context
                render_background_tasks()
            _render_right_dock(context, bundle)
    if st.session_state.get("settings_open"):
        render_settings_panel()
    reset_main_scroll(page, key="page")
    signal_frontend_ready()
