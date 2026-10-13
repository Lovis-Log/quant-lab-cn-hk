"""Native Streamlit sidebar; paid requests occur only on explicit form submit."""

from datetime import datetime, timezone
import sqlite3

import streamlit as st

from quant_lab import credentials
from quant_lab.deepseek import DeepSeekClient, AIRequestError, safe_context
from quant_lab.ai_context import context_scope
from quant_lab.security import redact
from quant_lab.storage import save_learning_note, save_setting


QUICK_QUESTIONS = ("解释当前指标", "分析本次回测", "给一个手算例子", "下一步学什么")


def _clear_key():
    previous = st.session_state.get("deepseek_api_key", "")
    st.session_state["deepseek_prompt"] = redact(st.session_state.get("deepseek_prompt", ""), (previous,))
    st.session_state["deepseek_api_key"] = ""
    st.session_state["deepseek_models"] = []
    st.session_state["deepseek_remember"] = False
    try:
        credentials.clear_key()
        st.session_state["deepseek_notice"] = "会话密钥和记住的凭据已清除。"
    except credentials.SecureStorageUnavailable as exc:
        st.session_state["deepseek_notice"] = str(exc)


def _load_key():
    try:
        st.session_state["deepseek_api_key"] = credentials.load_key() or ""
        st.session_state["deepseek_remember"] = bool(st.session_state["deepseek_api_key"])
        st.session_state["deepseek_notice"] = "已读取系统凭据。" if st.session_state["deepseek_api_key"] else "没有已记住的凭据。"
    except credentials.SecureStorageUnavailable as exc:
        st.session_state["deepseek_notice"] = str(exc)


def _key_changed():
    st.session_state["deepseek_models"] = []
    st.session_state["deepseek_model_error"] = None


def _draft(question):
    st.session_state["deepseek_prompt"] = question
    st.session_state["ai_open"] = True


def _save_model(widget_key):
    value = st.session_state[widget_key]
    st.session_state["deepseek_model"] = value
    try:
        save_setting("deepseek_model", value)
    except (OSError, sqlite3.Error, ValueError):
        st.session_state["deepseek_notice"] = "模型已切换；当前设置仅保留在会话中。"


def render_deepseek(context: dict):
    context = safe_context(context)
    if st.session_state.get("ai_knowledge"):
        context["knowledge"] = st.session_state["ai_knowledge"]
    scope = context_scope(context)
    with st.sidebar:
        with st.expander("DeepSeek AI 助手", expanded=st.session_state.get("ai_open", False)):
            st.caption("使用你自己的 DeepSeek API 账户。只有点击发送才产生模型请求；模型解释需核对程序事实。")
            st.caption("官方地址：https://api.deepseek.com")
            key = st.text_input("DeepSeek API Key", type="password", key="deepseek_api_key",
                                on_change=_key_changed,
                                help="默认仅当前会话保存；请不要把 Key 粘贴到聊天问题或笔记。")
            remember = st.checkbox("记住密钥（Windows 凭据管理器）", key="deepseek_remember")
            if st.button("应用密钥设置", key="deepseek_apply_key"):
                try:
                    if remember:
                        credentials.remember_key(key)
                        st.success("已写入 Windows 凭据管理器。")
                    else:
                        credentials.clear_key()
                        st.info("仅在当前会话保留密钥。")
                except credentials.SecureStorageUnavailable as exc:
                    st.warning(str(exc))
            st.button("读取已记住密钥", on_click=_load_key, key="deepseek_load_key")
            st.button("清除密钥", on_click=_clear_key, key="deepseek_clear_key")
            if st.session_state.get("deepseek_notice"):
                st.info(st.session_state.pop("deepseek_notice"))
            test = st.button("测试连接", key="deepseek_test", disabled=not key)
            refresh = st.button("刷新模型列表", key="deepseek_models_refresh", disabled=not key)
            if test or refresh:
                try:
                    st.session_state["deepseek_models"] = DeepSeekClient(key).list_models()
                    st.session_state["deepseek_model_error"] = None
                    st.success("连接成功；已取得官方可用模型列表。")
                except AIRequestError as exc:
                    st.session_state["deepseek_models"] = []
                    st.session_state["deepseek_model_error"] = str(exc)
            if st.session_state.get("deepseek_model_error"):
                st.warning(st.session_state["deepseek_model_error"])
            models = st.session_state.get("deepseek_models", [])
            metadata = {}
            if models:
                ids = [model["id"] for model in models]
                preference = st.session_state.get("deepseek_model", "")
                if st.session_state.get("ds_model_select") not in ids:
                    st.session_state["ds_model_select"] = preference if preference in ids else ids[0]
                model_id = st.selectbox("DeepSeek 模型", ids, key="ds_model_select",
                    format_func=lambda value: next((m.get("name", value) + f" · {value}" for m in models if m["id"] == value), value),
                    on_change=_save_model, args=("ds_model_select",))
                metadata = next(m for m in models if m["id"] == model_id)
            else:
                st.caption("尚未取得模型列表；可测试连接，或手动填写官方模型 ID。")
                model_id = st.text_input("手动模型 ID", value=st.session_state.get("deepseek_model", ""),
                                        key="ds_model_manual", on_change=_save_model, args=("ds_model_manual",))
            levels = (metadata.get("effort") or {}).get("supported_levels", [])
            effort = None
            if levels:
                effort_key = f"ds_effort_{model_id}"
                if st.session_state.get(effort_key) not in ["模型默认"] + levels:
                    st.session_state[effort_key] = "模型默认"
                choice = st.selectbox("思考强度（按模型声明）", ["模型默认"] + levels, key=effort_key)
                effort = None if choice == "模型默认" else choice
            st.caption("请求使用模型默认采样与思考设置；只对模型列表声明支持的参数提供选项。")
            attach = st.checkbox("附带当前程序事实摘要", value=True, key="deepseek_attach")
            with st.expander("发送前查看上下文摘要"):
                st.json(context if attach else {"说明": "本次不附带当前研究摘要。"})
                st.caption("不附带私人笔记、完整历史行情或数据库；发送前请核对标的与实验。")
            for question in QUICK_QUESTIONS:
                st.button(question, key=f"ds_quick_{question}", on_click=_draft, args=(question,))
            records = st.session_state.setdefault("deepseek_chat", [])
            if st.button("清空当前对话", key="ds_clear_chat"):
                st.session_state["deepseek_chat"] = []
                records = []
            with st.container(height=320, border=True):
                if not records:
                    st.caption("没有 Key 时仍可使用离线课程和知识解释。")
                for message in records[-20:]:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                        if message["role"] == "assistant":
                            st.caption(f"模型：{message['model']} · {message.get('security', '教学问答')}" +
                                       (" · 回答不完整" if not message.get("complete", True) else ""))
            with st.form("deepseek_send_form", clear_on_submit=False):
                prompt = st.text_area("问题（确认后发送）", key="deepseek_prompt", max_chars=3000)
                submitted = st.form_submit_button("发送到 DeepSeek", disabled=not key or not model_id,
                                                  help="此操作使用你的 API 账户；其他页面重绘不会自动发送。")
            if submitted:
                selected_context = context if attach else {}
                outgoing_scope = scope if attach else "standalone"
                history = [m for m in records if m.get("scope") == outgoing_scope]
                security = context.get("security", "教学问答") if attach else "教学问答（未附带行情）"
                if st.session_state.get("deepseek_busy"):
                    st.info("上一条回答仍在生成，请等待完成。")
                else:
                    st.session_state["deepseek_busy"] = True
                    answer = None
                    try:
                        answer, chunks = DeepSeekClient(key).stream(model_id, prompt, history, selected_context,
                                                                  metadata=metadata, effort=effort)
                        records.append({"role": "user", "content": redact(prompt, (key,)),
                                        "scope": outgoing_scope, "security": security})
                        with st.chat_message("assistant"):
                            st.write_stream(chunks)
                        st.caption(f"实际模型：{answer.model_used}")
                    except AIRequestError as exc:
                        st.warning(str(exc))
                    finally:
                        if answer and answer.text:
                            records.append({"role": "assistant", "content": redact(answer.text, (key,)),
                                            "model": answer.model_used, "requested_model": model_id,
                                            "scope": outgoing_scope, "security": security,
                                            "complete": answer.complete, "context": selected_context})
                        st.session_state["deepseek_chat"] = records[-40:]
                        st.session_state["deepseek_busy"] = False
            answers = [m for m in st.session_state.get("deepseek_chat", []) if m["role"] == "assistant"]
            if answers:
                selected = st.selectbox("选择回答保存为学习笔记", range(len(answers)),
                    format_func=lambda i: f"{i+1}. {answers[i]['model']} · {answers[i]['content'][:25]}")
                if st.button("保存选定回答到学习笔记", key="ds_save_note"):
                    message = answers[selected]
                    note_context = message.get("context", {})
                    try:
                        note_id = save_learning_note(
                            "AI 学习回答 · " + message["security"], message["content"],
                            model=message["model"], origin="DeepSeek 模型解释（需复核）",
                            market=note_context.get("market"), symbol=note_context.get("symbol"),
                            experiment_id=note_context.get("experiment_id"), secrets=(key,),
                        )
                        st.success(f"学习笔记 #{note_id} 已保存。")
                    except (ValueError, OSError, sqlite3.Error):
                        st.error("学习笔记保存失败；请检查用户数据目录。")
