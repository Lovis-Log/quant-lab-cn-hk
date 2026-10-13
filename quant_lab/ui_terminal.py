"""Conservative watchlist terminal: periodic daily-close polling, never streaming."""

from datetime import timedelta
from zoneinfo import ZoneInfo
import sqlite3

import pandas as pd
import streamlit as st

from quant_lab.data import DataUnavailableError, SNAPSHOT_CACHE
from quant_lab.processing import DataValidationError
from quant_lab.storage import add_watchlist, list_watchlist, remove_watchlist


@st.fragment(run_every=timedelta(minutes=5))
def _snapshot_panel(items: list[tuple[str, str]], paused: bool, manual: bool) -> None:
    if not items:
        st.info("自选股为空。添加代码后可查看最近历史日线收盘参考。")
        return
    if paused and not manual:
        st.caption("自动刷新已暂停。")
    else:
        rows = []
        errors = []
        for market, symbol in items:
            try:
                quote, cached = SNAPSHOT_CACHE.get(market, symbol, force=manual)
                rows.append({
                    "市场": market, "代码": symbol, "最近日线收盘": quote.last_close,
                    "币种": quote.currency, "行情日期": quote.observation_date.isoformat(),
                    "接收时间（北京时间）": quote.received_at.astimezone(
                        ZoneInfo("Asia/Shanghai")
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "来源": quote.source, "状态": quote.status,
                    "本地缓存": "是" if cached else "否",
                })
            except (DataUnavailableError, DataValidationError, ValueError) as exc:
                errors.append(f"{market} {symbol}：{exc}")
        st.session_state["watch_rows"] = rows
        st.session_state["watch_errors"] = errors
    rows = [row for row in st.session_state.get("watch_rows", [])
            if (row["市场"], row["代码"]) in items]
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    for error in st.session_state.get("watch_errors", []):
        st.warning(error)


def render_watchlist(market: str, symbol: str) -> None:
    st.markdown("#### 自选股 · 历史日线参考")
    st.caption("每 5 分钟检查一次；手动刷新最短间隔 60 秒。行情日期只有交易日，无法从日线推断盘中报价时间或确切延迟。")
    left, right = st.columns(2)
    with left:
        if st.button("加入自选", key="watch_add"):
            try:
                normalized = add_watchlist(market, symbol)
                st.success(f"已加入 {market} {normalized}")
            except (ValueError, OSError, sqlite3.Error) as exc:
                st.error(str(exc))
    try:
        items = list_watchlist()
    except (OSError, sqlite3.Error) as exc:
        st.error(f"读取自选股失败：{exc}")
        return
    with right:
        if items:
            chosen = st.selectbox("移除自选股", items,
                                  format_func=lambda item: f"{item[0]} {item[1]}")
            if st.button("移除所选", key="watch_remove"):
                try:
                    remove_watchlist(*chosen)
                    items = list_watchlist()
                    st.success("已移除。")
                except (OSError, sqlite3.Error) as exc:
                    st.error(f"移除失败：{exc}")
    controls = st.columns(2)
    manual = controls[0].button("手动刷新行情参考", key="watch_refresh")
    paused = st.session_state.get("watch_paused", False)
    if controls[1].button("继续自动刷新" if paused else "暂停自动刷新", key="watch_pause"):
        paused = not paused
        st.session_state["watch_paused"] = paused
    _snapshot_panel(items, paused, manual)
