"""Watchlist polling with explicit upstream checks and retained valid prices."""

from datetime import datetime, timezone, timedelta
import sqlite3
import time

import pandas as pd
import streamlit as st

from quant_lab.data import DataUnavailableError, SNAPSHOT_CACHE, snapshot_batch
from quant_lab.ui_jobs import submit_task, take_result
from quant_lab.jobs import JobState
from quant_lab import names
from quant_lab.storage import add_watchlist, list_watchlist, remove_watchlist
from quant_lab.ui_updates import status_rows


def render_watchlist(market: str, symbol: str) -> None:
    st.markdown("#### 自选股 · 最近历史日线收盘参考")
    st.caption("立即更新会绕过所选自选股的缓存。最多 10 只，上游请求至少间隔 1 秒；连续点击需等 5 秒。")
    if st.session_state.get("watch_message"):
        st.success(st.session_state.pop("watch_message"))
    left, right = st.columns(2)
    with left:
        if st.button("加入自选", key="watch_add"):
            try:
                name = names.cached_security_name(market, symbol)
                normalized = add_watchlist(market, symbol, company_name=name)
                st.session_state["watch_message"] = f"已加入 {names.cached_security_label(market, normalized, name)}"
                st.rerun(scope="app")
            except (ValueError, OSError, sqlite3.Error) as exc:
                st.error(str(exc))
    try:
        items = list_watchlist()
    except (OSError, ValueError, sqlite3.Error):
        st.error("读取自选股失败；请检查用户数据目录。")
        return
    with right:
        if items:
            chosen = st.selectbox("移除自选股", items, format_func=lambda item: names.cached_security_label(*item))
            if st.button("移除所选", key="watch_remove"):
                try:
                    remove_watchlist(*chosen)
                    items = list_watchlist()
                    st.session_state["watch_message"] = "已移除。"
                    st.rerun(scope="app")
                except (OSError, sqlite3.Error):
                    st.error("移除失败，请稍后重试。")
    now = datetime.now(timezone.utc)
    interval = st.session_state.get("refresh_interval_seconds", 300)
    auto = st.session_state.get("refresh_enabled", True)
    wait = max(0, st.session_state.get("watch_manual_at", float('-inf')) + 5 - time.monotonic())
    requested = st.button("立即更新自选股", key="watch_refresh", disabled=not items)
    manual = requested and wait <= 0
    if requested and wait > 0:
        st.info(f"请等待 {wait:.0f} 秒后再点击；本次没有重复请求。")
    if manual:
        st.session_state["watch_manual_at"] = time.monotonic()
    snapshots = st.session_state.setdefault("watch_snapshots", {})
    attempts = st.session_state.setdefault("watch_next_attempts", {})
    errors = st.session_state.setdefault("watch_errors_by_symbol", {})
    outcome = take_result("watch", tuple(items))
    updated_items = set()
    if outcome:
        if outcome.state == JobState.SUCCEEDED:
            quotes, failures = outcome.result
            updated_items = set(quotes)
            for item, quote in quotes.items():
                snapshots[item] = quote
                errors.pop(item, None)
                if quote.update_error:
                    errors[item] = quote.update_error
            errors.update(failures)
        elif outcome.state == JobState.FAILED:
            for item in items:
                errors[item] = outcome.error
    due = any(item not in attempts or now >= attempts[item] for item in items)
    if items and (manual or (auto and due)) and "watch" not in st.session_state.get("_task_tickets", {}):
        submit_task("watch", tuple(items), snapshot_batch, tuple(items))
        for item in items:
            attempts[item] = now + timedelta(seconds=interval)
        st.rerun(scope="app")
    rows = []
    for item in items:
        updated = item in updated_items
        if item in snapshots:
            quote = snapshots[item]
            rows.append({"股票": names.cached_security_label(*item), "最近日线收盘": quote.last_close,
                         "币种": quote.currency, "行情日期": quote.observation_date.isoformat(),
                         **status_rows(quote, attempts.get(item), session_cache=not updated),
                         "延迟状态": quote.status,"数据质量":quote.quality_status,
                         "更新状态":"进行中" if "watch" in st.session_state.get("_task_tickets",{}) else "上次更新失败" if item in errors or quote.update_error else "最近检查完成"})
            if item in errors:
                rows[-1]["最近更新结果"] = "请求失败；保留上次有效数据，可能过期"
            if quote.update_error:
                st.warning(f"{names.cached_security_label(*item)}：{quote.update_error}")
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    if not items:
        st.info("自选股为空。添加代码后可查看最近历史日线收盘参考。")
    elif not rows:
        st.info("尚无有效参考价格。可点击立即更新；自动刷新已暂停时不会发起请求。")
    for item in items:
        if item in errors:
            st.warning(errors[item])
