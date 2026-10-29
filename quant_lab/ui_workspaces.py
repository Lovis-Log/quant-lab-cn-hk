"""Explicit preset save/apply actions, before any market request is submitted."""

import streamlit as st

from quant_lab.workspaces import WorkspaceStore,NAMES,DEFAULTS,restore_values


def initialize_workspaces():
    if st.session_state.get("_workspaces_initialized"):return
    try:
        payload=WorkspaceStore().load()
        name=payload["active"]
        if name:
            values={**DEFAULTS[name],**payload["profiles"].get(name,{})}
            st.session_state.update(restore_values(values))
            st.session_state["workspace_name"]=name
    except (OSError,ValueError,TypeError,KeyError):
        st.session_state["workspace_message"]="工作区设置读取失败，原文件保留；当前使用会话设置。"
    st.session_state["_workspaces_initialized"]=True


def _apply():
    try:
        values=WorkspaceStore().activate(st.session_state["workspace_name"])
        st.session_state.update(restore_values(values))
        st.session_state["_comparison_draft_market"] = st.session_state["market_selection"]
        st.session_state["settings_app_rerun_pending"] = True
        st.session_state["workspace_message"]="已应用预设；比较仍需明确加载，观察列表沿用已有刷新设置。"
    except (OSError,ValueError,TypeError):
        st.session_state["workspace_message"]="应用预设失败，原文件与当前研究结果保留。"


def _save():
    try:
        WorkspaceStore().save(st.session_state["workspace_name"],dict(st.session_state))
        st.session_state["workspace_message"]="已保存已提交参数及面板开关；不含行情、笔记、AI内容或密钥。"
    except (OSError,ValueError,TypeError):
        st.session_state["workspace_message"]="工作区保存失败，请检查代码和参数；原文件不变。"


def render_workspace_presets():
    with st.expander("工作区方案"):
        st.selectbox("选择工作区方案",NAMES,key="workspace_name")
        st.button("应用预设",key="workspace_apply",on_click=_apply,width="stretch")
        st.button("保存当前",key="workspace_save",on_click=_save,width="stretch")
        st.caption("保存参数、导航与面板开关。")
        if st.session_state.get("workspace_message"):st.caption(st.session_state["workspace_message"])
