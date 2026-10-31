"""Shared update controls and timezone-explicit data provenance rendering."""

from datetime import datetime, timezone, timedelta
import sqlite3
from zoneinfo import ZoneInfo

import streamlit as st

from quant_lab.storage import load_settings, save_setting


INTERVALS = (300, 600, 900)


def initialize_settings():
    if st.session_state.get("settings_initialized"):
        return
    try:
        preferences = load_settings()
    except (OSError, ValueError, sqlite3.Error):
        preferences = {}
        st.session_state["settings_error"] = "无法读取用户设置；使用会话默认值。"
    defaults = {"refresh_enabled": True, "refresh_interval_seconds": 300, "learning_mode": True,
                "deepseek_model": "", "deepseek_answer_mode": "研究解释模式"}
    for key, default in defaults.items():
        value = preferences.get(key, default)
        if key == "refresh_interval_seconds" and value not in INTERVALS:
            value = default
        if key == "deepseek_answer_mode" and value not in {"研究解释模式", "教学辅导模式"}:
            value = default
        st.session_state.setdefault(key, value)
    st.session_state["settings_initialized"] = True


def persist_setting(key):
    if key in {"refresh_enabled", "refresh_interval_seconds"}:
        next_attempt = datetime.now(timezone.utc) + timedelta(seconds=st.session_state.get("refresh_interval_seconds", 300))
        st.session_state["history_next_attempt"] = next_attempt
        if st.session_state.get("_us_next_attempt"):
            st.session_state["_us_next_attempt"] = (st.session_state["_us_next_attempt"][0], next_attempt)
        st.session_state["watch_next_attempts"] = {item: next_attempt for item in st.session_state.get("watch_next_attempts", {})}
    try:
        save_setting(key, st.session_state[key])
    except (OSError, sqlite3.Error, ValueError):
        st.session_state["settings_error"] = "设置保存失败；当前仅在会话中生效。"


def toggle_refresh():
    st.session_state["refresh_enabled"] = not st.session_state["refresh_enabled"]
    persist_setting("refresh_enabled")


def beijing(value) -> str:
    if value is None:
        return "未记录（不能推断为当前时间）"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S UTC+08:00")


def status_rows(value, next_attempt=None, *, session_cache=False) -> dict:
    now = datetime.now(timezone.utc)
    received = value.received_at
    age = max(0, (now - received).total_seconds()) if received and received.tzinfo else None
    observation = getattr(value, "observation_date", None)
    if observation is None and hasattr(value, "frame") and not value.frame.empty:
        observation = value.frame.date.iloc[-1].date()
    demonstration = any(word in value.source.lower()
                        for word in ("模拟", "演示", "教学", "demo", "simulation", "teaching"))
    date_label = "样本日期（模拟/教学）" if demonstration else "行情日期（交易日）"
    return {date_label: str(observation) if observation else "无有效日期",
            "上次成功获取时间": beijing(received), "来源": value.source,
            "缓存状态": "上次有效数据（更新失败）" if value.update_error else
                         "本地缓存/会话快照" if value.cached or session_cache else "本次取得上游响应",
            "缓存年龄": f"{age:.0f} 秒" if age is not None else "未知",
            "自动刷新": "开启" if st.session_state.get("refresh_enabled", True) else "暂停",
            "间隔": f"{st.session_state.get('refresh_interval_seconds', 300)//60} 分钟",
            "下次尝试时间": beijing(next_attempt) if next_attempt and st.session_state.get("refresh_enabled", True) else "暂停／尚未安排",
            "最近更新结果": value.update_result + ("；数据可能过期" if value.update_error else "")}


def show_history_status(bundle, next_attempt=None, *, session_cache=False):
    if bundle is not None:
        demonstration = any(word in bundle.source.lower()
                            for word in ("模拟", "演示", "教学", "demo", "simulation", "teaching"))
        details = status_rows(bundle, next_attempt, session_cache=session_cache)
        observation = "教学样本" if demonstration else "历史日线"
        st.caption(f"{observation} · {bundle.source} · {bundle.currency} · 成功获取于 {beijing(bundle.received_at)}")
        with st.expander("更新与缓存详情"):
            st.table([{"项目": label, "内容": str(value)} for label, value in details.items()])
        if bundle.update_error:
            st.warning(bundle.update_error)
    if bundle is not None and demonstration:
        st.caption("当前为模拟/教学样本，不代表上游真实行情。自动刷新仅在市场页和当前应用会话运行时生效。")
    else:
        st.caption("行情日期是价格对应的交易日；确切延迟未知。自动刷新仅在市场页和当前应用会话运行时生效，关闭软件后不更新。")
