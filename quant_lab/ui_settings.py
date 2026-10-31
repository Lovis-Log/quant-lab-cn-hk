"""Global settings surface and mandatory managed-library setup."""

from pathlib import Path
import sqlite3

import streamlit as st

from quant_lab.paths import library_configured, stage_library, user_data_dir
from quant_lab.ui_deepseek import render_connection_settings
from quant_lab.ui_updates import INTERVALS, persist_setting


def _folder_picker_component() -> None:
    st.html("""
    <button id="pick" style="width:100%;height:36px;border:1px solid #303438;border-radius:6px;
      background:#22262A;color:#E8EBEE;font:600 13px sans-serif;cursor:pointer">浏览 Windows 文件夹…</button>
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
    parent = st.text_input(
        "选择新的存放文件夹",
        value=_chosen_parent(default),
        key=f"{prefix}_library_parent",
        help="软件会在所选文件夹内创建 QuantLabCNHK 子文件夹。",
    )
    _folder_picker_component()
    target_preview = st.session_state.get("library_restart_required") or str(
        Path(parent).expanduser() / "QuantLabCNHK"
    )
    st.caption("迁移后的资料库位置")
    st.code(target_preview, language=None)
    if st.button("创建资料库并迁移现有数据", key=f"{prefix}_activate_library", width="stretch"):
        try:
            target = stage_library(Path(parent))
            st.session_state["library_restart_required"] = str(target)
        except (OSError, ValueError, sqlite3.Error) as exc:
            st.error(str(exc))
    if st.session_state.get("library_restart_required"):
        st.success("资料库已复制并验证。请关闭并重新启动软件后继续。")


def render_library_setup() -> None:
    st.html('<div class="ql-setup"><h1>创建 Quant Lab 专用资料库</h1>'
            '<p>首次使用前必须选择一个本地父目录。应用会创建独立的 QuantLabCNHK 文件夹，'
            '保存数据库、笔记附件、备份、日志和缓存；DeepSeek Key 不会写入该目录。</p></div>')
    _configure_library("setup")
    st.info("现有资料会复制并校验；原目录保留，不会自动删除。")


def _close_settings() -> None:
    st.session_state["settings_open"] = False
    st.session_state["settings_app_rerun_pending"] = True


def _queue_learning_mode_refresh() -> None:
    for key in tuple(st.session_state):
        if str(key).startswith("knowledge_group_expanded_"):
            st.session_state.pop(key, None)
    st.session_state["learning_mode_app_rerun_pending"] = True


def _learning_mode_changed() -> None:
    persist_setting("learning_mode")
    _queue_learning_mode_refresh()


def _refresh_learning_mode_page() -> None:
    persist_setting("learning_mode")
    _queue_learning_mode_refresh()


def _refresh_schedule_changed(key):
    persist_setting(key)
    # Fragment intervals/closures must be registered again after a schedule edit.
    st.session_state["settings_app_rerun_pending"] = True


def rerun_pending_settings() -> None:
    """Consume settings-triggered app reruns before any fragment is rendered."""
    pending = st.session_state.pop("learning_mode_app_rerun_pending", False)
    pending = st.session_state.pop("settings_app_rerun_pending", False) or pending
    if pending:
        st.rerun(scope="app")


@st.fragment
def render_settings_panel() -> None:
    with st.container(key="settings_panel"):
        title, close = st.columns([5, 1], vertical_alignment="center")
        with title:
            st.html('<div class="ql-ai-panel-title"><strong>设置</strong><span>SETTINGS</span></div>')
        with close:
            st.button("×", key="settings_close", on_click=_close_settings, width="stretch")
        preference_tab, storage_tab, ai_tab, declaration_tab = st.tabs(("偏好设置", "资料文件夹", "DeepSeek", "声明与数据来源"))
        with storage_tab:
            st.caption("当前资料库位置")
            st.code(str(user_data_dir()), language=None)
            _configure_library("settings")
        with ai_tab:
            render_connection_settings()
        with preference_tab:
            from quant_lab.ui_workspaces import render_workspace_presets
            render_workspace_presets()
            learning_toggle, refresh = st.columns(
                [3, 1], vertical_alignment="bottom", gap="small"
            )
            with learning_toggle:
                st.toggle("显示详细解释提示", key="learning_mode",
                          on_change=_learning_mode_changed)
            with refresh:
                st.button(
                    "刷新整页",
                    key="learning_mode_refresh",
                    width="stretch",
                    on_click=_refresh_learning_mode_page,
                    help="强制重绘全部工作区；不会重新请求行情或调用 AI。",
                )
            st.caption("只调整页面解释密度，不改变行情、策略、回测、统计或组合计算。")
            st.toggle("自动刷新行情（仅市场页）", key="refresh_enabled",
                      on_change=_refresh_schedule_changed, args=("refresh_enabled",))
            st.selectbox("自动刷新间隔", INTERVALS, key="refresh_interval_seconds",
                         format_func=lambda seconds: f"{seconds//60} 分钟",
                         on_change=_refresh_schedule_changed, args=("refresh_interval_seconds",))
            st.caption("自动刷新只在软件和市场页会话运行时生效；关闭软件后不更新。")
            if st.session_state.get("settings_error"):
                st.warning(st.session_state.pop("settings_error"))
        with declaration_tab:
            _render_declarations()
    if st.session_state.pop("settings_app_rerun_pending", False):
        st.rerun(scope="app")
    rerun_pending_settings()


def _render_declarations():
    from quant_lab import names
    from quant_lab.securities import security_directory
    from quant_lab.ui_jobs import submit_task, take_result, cancel_task
    from quant_lab.jobs import JobState
    from quant_lab.ui_updates import beijing

    st.markdown("仅供学习与模拟研究，不提供实盘下单。历史日线及缓存均不是实时行情；确切延迟未知。")
    st.caption("证券目录只提供代码与名称候选，不是投资推荐，也不验证当前上市状态。")
    market = st.session_state.get("market_selection", "A 股")
    if market == "美股":
        st.info("美股以USD进行价格研究；完整公司行动/结算资格另行核验。证券目录不授予行情或留存资格。")
    completed = take_result("directory", market)
    if completed and completed.state == JobState.FAILED:
        st.warning(completed.error)
    try:
        directory = security_directory(market)
        st.write(f"{market}证券目录 · {len(directory.rows)}只")
        st.caption(f"{directory.source} · 获取于 {beijing(directory.received_at)}")
        if directory.error:
            st.warning(directory.error)
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.warning(str(error))
    if st.button("更新股票候选目录", key="refresh_security_directory"):
        submit_task("directory", market, security_directory, market, force=True, job_timeout=300)
        st.session_state["settings_app_rerun_pending"] = True
    selected = st.session_state.get("_selected_security")
    if selected and selected[0] == market:
        st.write(names.cached_security_label(*selected))
        try:
            record = names.storage.cached_security_name(*selected)
            if record:
                st.caption(f"名称资料：{record['source']} · 成功获取于 {beijing(record['fetched_at'])}")
        except (OSError, ValueError, sqlite3.Error):
            st.caption("名称资料暂不可用。")
        if st.button("重新获取证券名称", key="refresh_security_name"):
            cancel_task("name")
            submit_task("name", selected, names.security_name, *selected, force=True)
            st.session_state["settings_app_rerun_pending"] = True
    bundle = st.session_state.get("loaded_bundle")
    if (bundle is not None and bundle.market == market
            and st.session_state.get("loaded_query") == st.session_state.get("_current_query")):
        st.caption(f"当前行情：{bundle.source} · {bundle.currency} · {bundle.adjustment_label} · 成功获取于 {beijing(bundle.received_at)}")


__all__ = [
    "library_configured",
    "render_library_setup",
    "render_settings_panel",
    "rerun_pending_settings",
]
