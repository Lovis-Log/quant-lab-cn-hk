"""Global settings surface and mandatory managed-library setup."""

from pathlib import Path
import sqlite3

import streamlit as st

from quant_lab.paths import library_configured, stage_library, user_data_dir
from quant_lab.ui_deepseek import render_connection_settings
from quant_lab.ui_updates import INTERVALS, persist_setting


def _folder_picker_component() -> None:
    st.html("""
    <button id="pick" style="width:100%;height:36px;border:1px solid #34435A;border-radius:6px;
      background:#172133;color:#DCE6F3;font:600 13px sans-serif;cursor:pointer">浏览 Windows 文件夹…</button>
    <script>
    document.getElementById('pick').onclick = async () => {
      const api = window.pywebview?.api;
      if (!api?.choose_data_folder) {
        document.getElementById('pick').textContent = '浏览器模式：请在上方手动填写路径';
        return;
      }
      const value = await api.choose_data_folder();
      if (!value) return;
      const url = new URL(window.location.href);
      url.searchParams.set('ql_parent', value);
      window.location.href = url.toString();
    };
    </script>
    """, unsafe_allow_javascript=True)


def _chosen_parent(default: str) -> str:
    selected = st.query_params.get("ql_parent")
    return str(selected or default)


def _configure_library(prefix: str) -> None:
    default = str(Path.home() / "Documents")
    parent = st.text_input("资料库父目录", value=_chosen_parent(default), key=f"{prefix}_library_parent",
                           help="应用会在所选位置创建 QuantLabCNHK 子目录。")
    _folder_picker_component()
    if st.button("创建资料库并迁移现有数据", key=f"{prefix}_activate_library", width="stretch"):
        try:
            target = stage_library(Path(parent))
            st.session_state["library_restart_required"] = str(target)
        except (OSError, ValueError, sqlite3.Error) as exc:
            st.error(str(exc))
    if st.session_state.get("library_restart_required"):
        st.success("资料库已复制并验证。请关闭并重新启动软件后继续。")
        st.code(st.session_state["library_restart_required"], language=None)


def render_library_setup() -> None:
    st.html('<div class="ql-setup"><h1>创建 Quant Lab 专用资料库</h1>'
            '<p>首次使用前必须选择一个本地父目录。应用会创建独立的 QuantLabCNHK 文件夹，'
            '保存数据库、笔记附件、备份、日志和缓存；DeepSeek Key 不会写入该目录。</p></div>')
    _configure_library("setup")
    st.info("现有资料会复制并校验；原目录保留，不会自动删除。")


def _close_settings() -> None:
    st.session_state["settings_open"] = False


def _learning_mode_changed() -> None:
    persist_setting("learning_mode")
    for key in tuple(st.session_state):
        if str(key).startswith("knowledge_group_expanded_"):
            st.session_state.pop(key, None)
    st.session_state["learning_mode_app_rerun_pending"] = True


def render_settings_panel() -> None:
    with st.container(key="settings_panel"):
        title, close = st.columns([5, 1], vertical_alignment="center")
        with title:
            st.html('<div class="ql-ai-panel-title"><strong>设置</strong><span>SETTINGS</span></div>')
        with close:
            st.button("×", key="settings_close", on_click=_close_settings, width="stretch")
        storage_tab, ai_tab, preference_tab = st.tabs(("资料文件夹", "DeepSeek", "偏好设置"))
        with storage_tab:
            st.caption("当前资料根目录")
            st.code(str(user_data_dir()), language=None)
            _configure_library("settings")
        with ai_tab:
            render_connection_settings()
        with preference_tab:
            st.toggle("显示详细解释提示", key="learning_mode",
                      on_change=_learning_mode_changed)
            st.caption("只调整页面解释密度，不改变行情、策略、回测、统计或组合计算。")
            st.toggle("自动刷新行情（仅市场页）", key="refresh_enabled",
                      on_change=persist_setting, args=("refresh_enabled",))
            st.selectbox("自动刷新间隔", INTERVALS, key="refresh_interval_seconds",
                         format_func=lambda seconds: f"{seconds//60} 分钟",
                         on_change=persist_setting, args=("refresh_interval_seconds",))
            st.caption("自动刷新只在软件和市场页会话运行时生效；关闭软件后不更新。")
            if st.session_state.get("settings_error"):
                st.warning(st.session_state.pop("settings_error"))
        if st.session_state.pop("learning_mode_app_rerun_pending", False):
            st.rerun(scope="app")


__all__ = ["library_configured", "render_library_setup", "render_settings_panel"]
