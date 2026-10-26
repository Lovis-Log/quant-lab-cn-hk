"""Native Streamlit assistant workspace; paid requests require explicit actions."""

import json
import re
import sqlite3
import time
from uuid import uuid4

import streamlit as st

from quant_lab import ai_chat, credentials
from quant_lab.deepseek import DeepSeekClient, AIRequestError, CONTINUATION_PROMPT, merge_continuation, safe_context
from quant_lab.ai_context import context_scope
from quant_lab.security import redact
from quant_lab.storage import save_learning_note as save_research_note, save_setting


QUICK_QUESTIONS = ("解释当前指标", "分析本次回测", "给一个手算例子", "下一步学什么")
SUMMARY_PROMPT = (
    "请总结当前对话，保留用户真正关心的问题、已经确认的程序事实、关键解释、"
    "仍待验证的假设和下一步行动。不要添加对话中没有的数据，不要复述完整聊天记录。"
)


def initialize_credentials():
    """Restore a remembered key before any credential widget is created."""
    if st.session_state.get("deepseek_credentials_initialized"):
        return
    try:
        remembered = credentials.load_key() or ""
    except credentials.SecureStorageUnavailable as exc:
        remembered = ""
        st.session_state["deepseek_credential_error"] = str(exc)
    st.session_state.setdefault("deepseek_api_key", remembered)
    st.session_state.setdefault("deepseek_remember", bool(remembered))
    st.session_state["deepseek_credentials_initialized"] = True


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


def _clear_chat() -> None:
    _new_chat()


def _new_chat() -> None:
    st.session_state.pop("deepseek_conversation_id", None)
    st.session_state["deepseek_chat"] = []
    st.session_state["deepseek_prompt"] = ""
    st.session_state["deepseek_view"] = "chat"
    st.session_state["deepseek_history_locked"] = False
    st.session_state["deepseek_new_chat_pending"] = True
    st.session_state["ai_workspace"] = "对话与辅导"


def _show_chat_history() -> None:
    st.session_state["deepseek_view"] = "history"
    st.session_state["ai_workspace"] = "对话与辅导"


def _show_chat() -> None:
    st.session_state["deepseek_view"] = "chat"


def _open_conversation(conversation_id: str) -> None:
    conversation = ai_chat.get_conversation(conversation_id)
    ai_chat.touch_conversation(conversation_id)
    st.session_state["deepseek_conversation_id"] = conversation_id
    st.session_state["deepseek_new_chat_pending"] = False
    st.session_state["deepseek_chat"] = ai_chat.list_messages(conversation_id)
    st.session_state["deepseek_history_locked"] = True
    st.session_state["deepseek_view"] = "chat"


def _retry_incomplete_message(message_id: str) -> None:
    st.session_state["deepseek_retry_message_id"] = message_id


def _save_model(widget_key):
    value = st.session_state[widget_key]
    st.session_state["deepseek_model"] = value
    try:
        save_setting("deepseek_model", value)
    except (OSError, sqlite3.Error, ValueError):
        st.session_state["deepseek_notice"] = "模型已切换；当前设置仅保留在会话中。"


def _save_answer_mode():
    try:
        save_setting("deepseek_answer_mode", st.session_state["deepseek_answer_mode"])
    except (OSError, sqlite3.Error, ValueError):
        st.session_state["deepseek_notice"] = "回答模式仅保留在会话中。"


def open_ai_followup(prompt, topic):
    """Carry only reviewed program facts into the assistant, never send here."""
    context = safe_context(st.session_state.get("_current_ai_context", {}))
    context["knowledge"] = {"topic": topic}
    st.session_state["ai_followup_context"] = context
    st.session_state["ai_followup_query"] = st.session_state.get("_current_query")
    st.session_state["deepseek_prompt"] = prompt
    st.session_state["ai_workspace"] = "对话与辅导"
    st.session_state["deepseek_panel_open"] = True


def _open_research_workspace() -> None:
    st.session_state["ai_workspace"] = "研究实验"


def _return_to_chat() -> None:
    st.session_state["ai_workspace"] = "对话与辅导"


def _note_title(prefix: str, question: str) -> str:
    first_line = next((line.strip() for line in question.splitlines() if line.strip()), "未命名问题")
    first_line = re.sub(r"\s+", " ", first_line)
    return f"{prefix} · {first_line[:48]}"


def _paired_question(records: list[dict], index: int, message: dict) -> str:
    if message.get("question"):
        return message["question"]
    if message.get("kind") == "conversation_summary":
        return next(
            (item.get("content", "") for item in records[:index]
             if item.get("role") == "user" and item.get("kind", "chat") == "chat"),
            "当前对话",
        )
    turn_id = message.get("turn_id")
    for candidate in reversed(records[:index]):
        if candidate.get("role") != "user":
            continue
        if turn_id and candidate.get("turn_id") != turn_id:
            continue
        return candidate.get("content", "")
    return "未记录原始问题"


def _save_message_as_note(records: list[dict], index: int, key: str) -> None:
    message = records[index]
    question = _paired_question(records, index, message)
    is_summary = message.get("kind") == "conversation_summary"
    title = _note_title("AI 对话总结" if is_summary else "AI 研究问答", question)
    heading = "对话主题" if is_summary else "问题"
    answer_heading = "对话总结" if is_summary else "DeepSeek 回答"
    content = f"## {heading}\n\n{question}\n\n## {answer_heading}\n\n{message['content']}"
    note_context = message.get("context", {})
    note_id = save_research_note(
        title, content, model=message.get("model", ""),
        origin="DeepSeek 对话总结（需复核）" if is_summary else "DeepSeek 模型问答（需复核）",
        market=note_context.get("market"), symbol=note_context.get("symbol"),
        experiment_id=note_context.get("experiment_id"), secrets=(key,),
    )
    message["saved_note_id"] = note_id
    if message.get("id"):
        ai_chat.update_message(message["id"], saved_note_id=note_id)
    st.session_state["deepseek_chat_notice"] = f"研究笔记 #{note_id} 已保存。"


def _render_copy_button(content: str, turn_id: str) -> None:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", turn_id) or uuid4().hex
    button_id = f"ql-copy-{safe_id}"
    encoded = (
        json.dumps(content, ensure_ascii=False)
        .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    )
    st.html(
        f"""
        <div class="ql-copy-action"><button type="button" id="{button_id}" aria-label="复制 DeepSeek 回答">复制回答</button>
        <span id="{button_id}-status" aria-live="polite"></span></div>
        <script>(() => {{
          const button = document.getElementById({json.dumps(button_id)});
          const status = document.getElementById({json.dumps(button_id + '-status')});
          if (!button || button.dataset.bound === '1') return;
          button.dataset.bound = '1';
          const value = {encoded};
          const fallback = () => {{
            const area = document.createElement('textarea');
            area.value = value; area.style.position = 'fixed'; area.style.opacity = '0';
            document.body.appendChild(area); area.select();
            const copied = document.execCommand('copy'); area.remove();
            if (!copied) throw new Error('copy rejected');
          }};
          button.addEventListener('click', async () => {{
            try {{
              if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(value);
              else fallback();
              status.textContent = '已复制';
            }} catch (_) {{
              try {{ fallback(); status.textContent = '已复制'; }}
              catch (_) {{ status.textContent = '复制失败，请手动选择文本'; }}
            }}
            window.setTimeout(() => {{ status.textContent = ''; }}, 2200);
          }});
        }})();</script>
        """,
        unsafe_allow_javascript=True,
    )


def _render_answer_actions(records: list[dict], index: int, key: str) -> None:
    message = records[index]
    turn_id = str(message.setdefault("turn_id", f"legacy-{index}"))
    copy_col, save_col = st.columns(2, gap="small")
    with copy_col:
        _render_copy_button(message["content"], turn_id)
    with save_col:
        saved_id = message.get("saved_note_id")
        clicked = st.button(
            f"已保存 #{saved_id}" if saved_id else "保存到研究笔记",
            key=f"deepseek_save_{turn_id}", width="stretch", disabled=bool(saved_id),
        )
    if clicked:
        try:
            _save_message_as_note(records, index, key)
            st.rerun()
        except (ValueError, OSError, sqlite3.Error):
            st.error("研究笔记保存失败；请检查用户数据目录。")


def connection_state() -> tuple[str, str, dict, str | None]:
    key = st.session_state.get("deepseek_api_key", "")
    models = st.session_state.get("deepseek_models", [])
    model_id = (st.session_state.get("ds_model_select") if models else
                st.session_state.get("ds_model_manual", st.session_state.get("deepseek_model", ""))) or ""
    metadata = next((item for item in models if item.get("id") == model_id), {})
    levels = (metadata.get("effort") or {}).get("supported_levels", [])
    effort = None
    if levels:
        choice = st.session_state.get(f"ds_effort_{model_id}", "模型默认")
        effort = None if choice == "模型默认" else choice
    return key, model_id, metadata, effort


def render_connection_settings() -> None:
    st.caption("Key 只写入 Windows 凭据管理器；普通资料文件夹、SQLite、日志和导出均不保存 Key。")
    key = st.text_input("DeepSeek API Key", type="password", key="deepseek_api_key",
                        on_change=_key_changed, help="请不要把 Key 粘贴到笔记或聊天问题。")
    remember = st.checkbox("记住密钥（Windows 凭据管理器）", key="deepseek_remember")
    apply_col, load_col, clear_col = st.columns(3)
    with apply_col:
        apply_clicked = st.button("应用密钥", key="deepseek_apply_key", width="stretch")
    with load_col:
        st.button("读取密钥", on_click=_load_key, key="deepseek_load_key", width="stretch")
    with clear_col:
        st.button("清除密钥", on_click=_clear_key, key="deepseek_clear_key", width="stretch")
    if apply_clicked:
        try:
            if remember and key.strip():
                credentials.remember_key(key)
                st.success("已写入 Windows 凭据管理器。")
            elif remember:
                st.warning("请先填写 API Key。")
            else:
                credentials.clear_key()
                st.info("仅在当前会话保留密钥。")
        except credentials.SecureStorageUnavailable as exc:
            st.warning(str(exc))
    test_col, refresh_col = st.columns(2)
    test = test_col.button("测试连接", key="deepseek_test", disabled=not key, width="stretch")
    refresh = refresh_col.button("刷新模型", key="deepseek_models_refresh", disabled=not key, width="stretch")
    if test or refresh:
        try:
            available = DeepSeekClient(key).list_models()
            st.session_state["deepseek_models"] = available
            ids = [item["id"] for item in available]
            preference = st.session_state.get("deepseek_model", "")
            if st.session_state.get("ds_model_select") not in ids:
                st.session_state["ds_model_select"] = preference if preference in ids else ids[0]
            st.session_state["deepseek_model_error"] = None
            st.session_state["deepseek_connection_notice"] = "连接成功；已取得官方可用模型列表。"
            st.rerun()
        except AIRequestError as exc:
            st.session_state["deepseek_models"] = []
            st.session_state["deepseek_model_error"] = str(exc)
    models = st.session_state.get("deepseek_models", [])
    if models:
        ids = [item["id"] for item in models]
        preference = st.session_state.get("deepseek_model", "")
        if st.session_state.get("ds_model_select") not in ids:
            st.session_state["ds_model_select"] = preference if preference in ids else ids[0]
        model_id = st.selectbox("DeepSeek 模型", ids, key="ds_model_select",
            format_func=lambda value: next((m.get("name", value) + f" · {value}" for m in models if m["id"] == value), value),
            on_change=_save_model, args=("ds_model_select",))
        metadata = next(item for item in models if item["id"] == model_id)
    else:
        st.caption("尚未取得模型列表；可测试连接，或手动填写官方模型 ID。")
        model_id = st.text_input("手动模型 ID", value=st.session_state.get("deepseek_model", ""),
                                 key="ds_model_manual", on_change=_save_model, args=("ds_model_manual",))
        metadata = {}
    levels = (metadata.get("effort") or {}).get("supported_levels", [])
    if levels:
        effort_key = f"ds_effort_{model_id}"
        st.session_state.setdefault(effort_key, "模型默认")
        st.selectbox("思考强度（按模型声明）", ["模型默认"] + levels, key=effort_key)
    if st.session_state.get("deepseek_notice"):
        st.info(st.session_state.pop("deepseek_notice"))
    if st.session_state.get("deepseek_connection_notice"):
        st.success(st.session_state.pop("deepseek_connection_notice"))
    if st.session_state.get("deepseek_model_error"):
        st.warning(st.session_state["deepseek_model_error"])
    if st.session_state.get("deepseek_credential_error"):
        st.warning(st.session_state.pop("deepseek_credential_error"))


def _activate_chat(scope: str, context: dict) -> dict | None:
    st.session_state.setdefault("deepseek_view", "chat")
    if st.session_state.get("deepseek_new_chat_pending", False):
        st.session_state["deepseek_current_scope"] = scope
        st.session_state["deepseek_chat"] = []
        return None
    locked = st.session_state.get("deepseek_history_locked", False)
    previous_scope = st.session_state.get("deepseek_current_scope")
    scope_changed = bool(previous_scope and previous_scope != scope and not locked)
    if scope_changed:
        st.session_state.pop("deepseek_conversation_id", None)
        st.session_state["deepseek_chat"] = []
    st.session_state["deepseek_current_scope"] = scope
    conversation_id = st.session_state.get("deepseek_conversation_id")
    if conversation_id:
        try:
            conversation = ai_chat.get_conversation(conversation_id)
        except (KeyError, OSError, sqlite3.Error, ValueError):
            st.session_state.pop("deepseek_conversation_id", None)
            st.session_state["deepseek_chat"] = []
        else:
            if locked or conversation["scope"] == scope:
                st.session_state["deepseek_chat"] = ai_chat.list_messages(conversation_id)
                return conversation
            st.session_state.pop("deepseek_conversation_id", None)
            st.session_state["deepseek_chat"] = []
    if scope_changed:
        return None
    try:
        conversation = ai_chat.latest_conversation(scope)
    except (OSError, sqlite3.Error, ValueError):
        conversation = None
    if conversation:
        st.session_state["deepseek_conversation_id"] = conversation["id"]
        st.session_state["deepseek_chat"] = ai_chat.list_messages(conversation["id"])
    else:
        st.session_state.setdefault("deepseek_chat", [])
    return conversation


def _render_chat_history() -> None:
    st.button("← 返回对话", key="deepseek_history_back", on_click=_show_chat)
    query = st.text_input(
        "搜索历史会话", key="deepseek_history_search", label_visibility="collapsed",
        placeholder="搜索标题或消息…",
    )
    try:
        conversations = ai_chat.list_conversations(query)
    except (OSError, sqlite3.Error, ValueError) as exc:
        st.error(f"读取历史会话失败：{exc}")
        return
    if not conversations:
        st.info("没有找到历史会话。" if query.strip() else "还没有历史会话。")
        return
    st.caption(f"{len(conversations)} 个本地会话，按最近更新排序。")
    for item in conversations[:50]:
        updated = str(item["updated_at"]).replace("T", " ")[:16]
        with st.container(border=True, key=f"deepseek_history_card_{item['id']}"):
            st.button(
                item["title"], key=f"deepseek_history_open_{item['id']}", width="stretch",
                on_click=_open_conversation, args=(item["id"],),
            )
            st.caption(f"{item['message_count']} 条消息 · 更新于 {updated}")
    with st.expander("整理历史会话", expanded=False):
        ids = [item["id"] for item in conversations]
        by_id = {item["id"]: item for item in conversations}
        selected = st.selectbox(
            "选择会话", ids, key="deepseek_history_manage",
            format_func=lambda value: by_id[value]["title"],
        )
        title = st.text_input(
            "会话标题", value=by_id[selected]["title"],
            key=f"deepseek_history_title_{selected}", max_chars=80,
        )
        rename, delete = st.columns(2)
        if rename.button("重命名", key="deepseek_history_rename", width="stretch"):
            try:
                ai_chat.rename_conversation(selected, title)
                st.rerun()
            except (KeyError, ValueError, OSError, sqlite3.Error) as exc:
                st.error(str(exc))
        confirm = st.checkbox("确认删除所选会话", key="deepseek_history_delete_confirm")
        if delete.button(
            "删除", key="deepseek_history_delete", width="stretch", disabled=not confirm,
        ):
            try:
                ai_chat.delete_conversation(selected)
                if st.session_state.get("deepseek_conversation_id") == selected:
                    _new_chat()
                    st.session_state["deepseek_view"] = "history"
                st.rerun()
            except (KeyError, OSError, sqlite3.Error) as exc:
                st.error(str(exc))


def render_deepseek(context: dict, bundle=None, *, chat_only: bool = False,
                    connection_expanded: bool = True, compact: bool = False):
    from quant_lab.ui_ai import render_ai, current_experiment_context
    key, model_id, metadata, effort = connection_state()
    status = f"已连接 · {model_id}" if key and model_id else "尚未完成 DeepSeek 连接设置"
    workspace = st.session_state.setdefault("ai_workspace", "对话与辅导")
    if not chat_only and workspace == "研究实验":
        st.button("← 返回对话", key="deepseek_return_chat", on_click=_return_to_chat)
        render_ai(bundle)
        if st.session_state.get("active_backtest_context"):
            context.update(st.session_state["active_backtest_context"])
            st.session_state["_current_ai_context"] = context
        return
    followup = st.session_state.get("ai_followup_context")
    context.update(current_experiment_context(bundle))
    context = safe_context(followup or context)
    st.session_state.setdefault("deepseek_attach", True)
    st.session_state.setdefault("deepseek_chat", [])
    if st.session_state.pop("deepseek_clear_prompt_pending", False):
        st.session_state["deepseek_prompt"] = ""
    st.html('<span class="ql-deepseek-chat-mode" aria-hidden="true"></span>')
    with st.container(key="deepseek_chat_toolbar"):
        st.caption(status)
        new_column, history_column = st.columns(2, gap="small")
        with new_column:
            st.button("新对话", key="deepseek_new_chat", width="stretch", on_click=_new_chat)
        with history_column:
            st.button("历史会话", key="deepseek_history", width="stretch", on_click=_show_chat_history)
        settings_column, experiment_column = st.columns(2, gap="small", vertical_alignment="center")
        with settings_column:
            with st.popover("⚙ 设置", use_container_width=True):
                st.caption("连接与模型设置位于左上角 `⚙ → DeepSeek`。")
                if st.button("前往 DeepSeek 设置", key="deepseek_open_settings", width="stretch"):
                    st.session_state["settings_open"] = True
                    st.rerun()
                st.radio(
                    "回答模式",
                    ("研究解释模式", "教学辅导模式"),
                    key="deepseek_answer_mode",
                    on_change=_save_answer_mode,
                )
                st.checkbox("附带当前程序事实摘要", key="deepseek_attach")
                if followup:
                    st.caption(
                        "追问来源：" + followup.get("page", "知识解释")
                        + " · 使用点击追问时的事实摘要"
                    )
                    if st.button("改用当前研究摘要", key="deepseek_use_current_context"):
                        st.session_state.pop("ai_followup_context", None)
                        st.rerun()
                with st.expander("发送前查看上下文摘要"):
                    attach_preview = st.session_state.get("deepseek_attach", True)
                    st.json(context if attach_preview else {"说明": "本次不附带当前研究摘要。"})
                    st.caption("不附带私人笔记、完整历史行情或数据库；发送前请核对标的与实验。")
                st.markdown("##### 快捷问题")
                quick_columns = st.columns(2, gap="small")
                for index, question in enumerate(QUICK_QUESTIONS):
                    with quick_columns[index % 2]:
                        st.button(
                            question,
                            key=f"ds_quick_{question}",
                            width="stretch",
                            on_click=_draft,
                            args=(question,),
                        )
                st.button("清空当前对话", key="ds_clear_chat", width="stretch",
                          on_click=_clear_chat)
        with experiment_column:
            if not chat_only:
                st.button(
                    "研究实验",
                    key="deepseek_open_research",
                    width="stretch",
                    on_click=_open_research_workspace,
                )
    context["answer_mode"] = st.session_state["deepseek_answer_mode"]
    attach = st.session_state.get("deepseek_attach", True)
    scope = context_scope(context)
    outgoing_scope = scope if attach else "standalone"
    conversation = _activate_chat(outgoing_scope, context if attach else {})
    records = st.session_state.setdefault("deepseek_chat", [])
    selected_context = context if attach else {}
    if conversation and st.session_state.get("deepseek_history_locked"):
        outgoing_scope = conversation["scope"]
        selected_context = conversation["context"]
    if st.session_state.get("deepseek_view") == "history":
        with st.container(key="deepseek_chat_surface"):
            with st.container(key="deepseek_messages"):
                _render_chat_history()
        return
    active_answers = [
        message for message in records
        if message.get("role") == "assistant"
        and message.get("scope", outgoing_scope) == outgoing_scope
        and message.get("kind", "chat") == "chat"
        and message.get("complete", True)
    ]
    with st.container(key="deepseek_chat_surface"):
        with st.container(key="deepseek_composer"):
            prompt = st.text_area(
                "问题（确认后发送）", key="deepseek_prompt", max_chars=3000,
                placeholder="输入你的研究问题…", height=92,
            )
            submitted = st.button(
                "发送到 DeepSeek", key="deepseek_send", disabled=not key or not model_id,
                help="此操作使用你的 API 账户；其他页面重绘不会自动发送。",
                width="stretch",
            )
            summarize = False
            if len(active_answers) >= 2:
                summarize = st.button(
                    "总结并保存本次对话", key="deepseek_summarize_save", width="stretch",
                    disabled=not key or not model_id,
                    help="会额外调用一次 DeepSeek，并在完整生成后保存到研究笔记。",
                )
                st.caption("总结只使用当前研究作用域内最近保留的对话；此操作会产生一次额外请求。")
            if st.session_state.get("deepseek_chat_notice"):
                st.success(st.session_state.pop("deepseek_chat_notice"))
            if st.session_state.get("deepseek_chat_error"):
                st.error(st.session_state.pop("deepseek_chat_error"))
            st.html(
                """
                <script>(() => {
                  const bind = () => {
                    const area = document.querySelector('textarea[aria-label="问题（确认后发送）"]');
                    const send = document.querySelector('.st-key-deepseek_send button');
                    if (!area || !send || area.dataset.enterSendBound === '1') return;
                    area.dataset.enterSendBound = '1';
                    area.addEventListener('keydown', event => {
                      if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
                      event.preventDefault();
                      if (!send.disabled && area.value.trim()) {
                        area.blur();
                        window.setTimeout(() => {
                          const current = document.querySelector('.st-key-deepseek_send button');
                          if (current && !current.disabled) current.click();
                        }, 250);
                      }
                    });
                  };
                  bind();
                  requestAnimationFrame(bind);
                })();</script>
                """,
                unsafe_allow_javascript=True,
            )
        if submitted:
            if prompt.strip():
                st.session_state["deepseek_pending_request"] = {
                    "id": uuid4().hex, "kind": "chat", "prompt": redact(prompt, (key,)),
                    "scope": outgoing_scope, "context": selected_context,
                    "security": selected_context.get("security", "教学问答") if selected_context else "教学问答（未附带行情）",
                }
                st.session_state["deepseek_clear_prompt_pending"] = True
            else:
                st.warning("请先输入问题。")
        if summarize:
            summary_history = [
                message for message in records
                if message.get("scope", outgoing_scope) == outgoing_scope
                and message.get("role") in {"user", "assistant"}
                and message.get("kind", "chat") == "chat"
                and (message.get("role") == "user" or message.get("complete", True))
            ][-20:]
            first_question = next(
                (message.get("content", "") for message in summary_history if message.get("role") == "user"),
                "当前对话",
            )
            st.session_state["deepseek_pending_request"] = {
                "id": uuid4().hex, "kind": "conversation_summary", "prompt": SUMMARY_PROMPT,
                "scope": outgoing_scope, "context": selected_context,
                "security": selected_context.get("security", "教学问答") if selected_context else "教学问答（未附带行情）",
                "question": first_question,
            }
        retry_message_id = st.session_state.pop("deepseek_retry_message_id", None)
        if retry_message_id:
            target = next((message for message in records if message.get("id") == retry_message_id), None)
            if target:
                st.session_state["deepseek_pending_request"] = {
                    "id": uuid4().hex, "kind": "manual_continuation",
                    "prompt": CONTINUATION_PROMPT, "target_message_id": retry_message_id,
                    "scope": target.get("scope", outgoing_scope),
                    "context": target.get("context", selected_context),
                    "security": target.get("security", "教学问答"),
                    "question": _paired_question(records, records.index(target), target),
                }
        with st.container(key="deepseek_messages"):
            st.html(
                """
                <script>(() => {
                  const panel = document.querySelector('.st-key-deepseek_messages');
                  if (!panel || panel.dataset.autoScrollBound === '1') return;
                  panel.dataset.autoScrollBound = '1';
                  let follow = true;
                  const nearBottom = () => panel.scrollHeight - panel.scrollTop - panel.clientHeight < 80;
                  panel.addEventListener('scroll', () => { follow = nearBottom(); }, {passive:true});
                  const observer = new MutationObserver(() => {
                    if (follow) requestAnimationFrame(() => { panel.scrollTop = panel.scrollHeight; });
                  });
                  observer.observe(panel, {childList:true, subtree:true, characterData:true});
                  requestAnimationFrame(() => { panel.scrollTop = panel.scrollHeight; });
                })();</script>
                """,
                unsafe_allow_javascript=True,
            )
            if not records and "deepseek_pending_request" not in st.session_state:
                st.caption("开始新的对话。没有 Key 时仍可使用离线手册和 Academy。")
            start = max(0, len(records) - 20)
            for index in range(start, len(records)):
                message = records[index]
                with st.chat_message(message["role"]):
                    if message.get("kind") == "conversation_summary":
                        st.caption("对话总结")
                    st.markdown(message["content"])
                    if message["role"] == "assistant":
                        st.caption(
                            f"模型：{message.get('model', '未知')} · {message.get('security', '教学问答')}"
                            + (" · 回答不完整" if not message.get("complete", True) else "")
                        )
                        if not message.get("complete", True) and message.get("error"):
                            st.warning(message["error"])
                        if message.get("complete", True) and message.get("content"):
                            _render_answer_actions(records, index, key)
                        elif message.get("content"):
                            copy_col, retry_col = st.columns(2, gap="small")
                            with copy_col:
                                _render_copy_button(message["content"], str(message.get("turn_id", index)))
                            with retry_col:
                                st.button(
                                    "重新继续", key=f"deepseek_retry_{message.get('id', index)}",
                                    width="stretch", on_click=_retry_incomplete_message,
                                    args=(message.get("id", ""),),
                                    help="从已保留的回答末尾继续生成。",
                                )
            pending = st.session_state.pop("deepseek_pending_request", None)
            if pending:
                if st.session_state.get("deepseek_busy"):
                    st.info("上一条回答仍在生成；本次请求未发送，请稍后重新点击。")
                else:
                    st.session_state["deepseek_busy"] = True
                    answer = None
                    kind = pending["kind"]
                    request_context = pending["context"]
                    history = [
                        message for message in records
                        if message.get("scope", pending["scope"]) == pending["scope"]
                        and (kind == "chat" or message.get("kind", "chat") == "chat")
                        and (kind == "chat" or message.get("role") == "user" or message.get("complete", True))
                    ]
                    if kind == "conversation_summary":
                        history = history[-20:]
                    elif kind == "chat":
                        turn_id = pending["id"]
                    conversation_id = st.session_state.get("deepseek_conversation_id")
                    partial_message_id = None
                    last_persisted_at = 0.0
                    try:
                        if not conversation_id:
                            created = ai_chat.create_conversation(
                                pending["scope"], request_context, title=pending.get("question", pending["prompt"]),
                            )
                            conversation_id = created["id"]
                            st.session_state["deepseek_conversation_id"] = conversation_id
                            st.session_state["deepseek_new_chat_pending"] = False
                        if kind == "chat":
                            user_message = ai_chat.add_message(
                                conversation_id, turn_id=turn_id, role="user",
                                content=pending["prompt"], kind="chat", security=pending["security"],
                                context=request_context, secrets=(key,),
                            )
                            records.append(user_message)
                            with st.chat_message("user"):
                                st.markdown(user_message["content"])
                        request_purpose = "continuation" if kind == "manual_continuation" else kind
                        answer, chunks = DeepSeekClient(key).stream_with_recovery(
                            model_id, pending["prompt"], history, request_context,
                            metadata=metadata, effort=effort,
                            purpose=request_purpose,
                            history_limit=20 if kind == "conversation_summary" else 12,
                        )
                        def persisted_chunks():
                            nonlocal partial_message_id, last_persisted_at
                            for piece in chunks:
                                now = time.monotonic()
                                if answer.text and (partial_message_id is None or now - last_persisted_at >= 0.4):
                                    try:
                                        if kind == "manual_continuation":
                                            target = next(
                                                (item for item in records
                                                 if item.get("id") == pending.get("target_message_id")), None
                                            )
                                            if target:
                                                ai_chat.update_message(
                                                    target["id"],
                                                    content=merge_continuation(target["content"], answer.text),
                                                    complete=False, secrets=(key,),
                                                )
                                        elif partial_message_id is None:
                                            partial = ai_chat.add_message(
                                                conversation_id, turn_id=pending["id"], role="assistant",
                                                content=answer.text, model=answer.model_used,
                                                requested_model=model_id, kind=kind,
                                                security=pending["security"], complete=False,
                                                context=request_context, secrets=(key,),
                                            )
                                            partial_message_id = partial["id"]
                                        else:
                                            ai_chat.update_message(
                                                partial_message_id, content=answer.text,
                                                complete=False, secrets=(key,),
                                            )
                                        last_persisted_at = now
                                    except (KeyError, ValueError, OSError, sqlite3.Error):
                                        st.session_state["deepseek_chat_error"] = "流式回答暂时无法保存到资料库。"
                                yield piece
                        with st.chat_message("assistant"):
                            if kind == "conversation_summary":
                                st.caption("正在总结当前对话…")
                            elif kind == "manual_continuation":
                                st.caption("正在从上次中断处继续…")
                            else:
                                st.caption("DeepSeek 正在思考并生成最终回答…")
                            st.write_stream(persisted_chunks())
                            st.caption(f"实际模型：{answer.model_used}")
                    except (AIRequestError, KeyError, ValueError, OSError, sqlite3.Error) as exc:
                        st.session_state["deepseek_chat_error"] = str(exc)
                    finally:
                        if answer and answer.text:
                            try:
                                if kind == "manual_continuation":
                                    target = next(
                                        (item for item in records
                                         if item.get("id") == pending.get("target_message_id")), None
                                    )
                                    if target:
                                        combined = merge_continuation(target["content"], answer.text)
                                        ai_chat.update_message(
                                            target["id"], content=combined, complete=answer.complete,
                                            finish_reason=answer.finish_reason or "stop",
                                            error=answer.error or "", secrets=(key,),
                                        )
                                else:
                                    if partial_message_id:
                                        ai_chat.update_message(
                                            partial_message_id, content=answer.text,
                                            complete=answer.complete,
                                            finish_reason=answer.finish_reason or ("stop" if answer.complete else "aborted"),
                                            error=answer.error or "", secrets=(key,),
                                        )
                                        message = ai_chat.get_message(partial_message_id)
                                    else:
                                        message = ai_chat.add_message(
                                            conversation_id, turn_id=pending["id"], role="assistant",
                                            content=answer.text, model=answer.model_used,
                                            requested_model=model_id, kind=kind, security=pending["security"],
                                            complete=answer.complete, finish_reason=answer.finish_reason,
                                            error=answer.error, context=request_context, secrets=(key,),
                                        )
                                    message["question"] = pending.get("question", pending["prompt"])
                                    records.append(message)
                                    if kind == "conversation_summary" and answer.complete:
                                        try:
                                            _save_message_as_note(records, len(records) - 1, key)
                                        except (ValueError, OSError, sqlite3.Error):
                                            st.session_state["deepseek_chat_error"] = (
                                                "对话总结已生成，但研究笔记保存失败；可在回答下方手动保存。"
                                            )
                            except (KeyError, ValueError, OSError, sqlite3.Error) as exc:
                                st.session_state["deepseek_chat_error"] = f"对话保存失败：{exc}"
                        if conversation_id:
                            try:
                                st.session_state["deepseek_chat"] = ai_chat.list_messages(conversation_id)
                            except (OSError, sqlite3.Error, ValueError):
                                st.session_state["deepseek_chat"] = records
                        st.session_state["deepseek_busy"] = False
                    st.rerun()


def _close_deepseek_panel() -> None:
    st.session_state["deepseek_panel_open"] = False
    if st.session_state.get("maximized_panel") == "deepseek":
        st.session_state["maximized_panel"] = None


def _toggle_deepseek_maximize() -> None:
    st.session_state["maximized_panel"] = (
        None if st.session_state.get("maximized_panel") == "deepseek" else "deepseek"
    )


def render_deepseek_panel(context: dict, bundle=None):
    with st.container(key="deepseek_side_panel"):
        st.html(
            '<div class="ql-resize-handle" data-panel="deepseek" role="separator" '
            'aria-label="调整 DeepSeek 助手宽度" tabindex="0"></div>'
        )
        with st.container(key="deepseek_panel_header"):
            title, maximize, close = st.columns([5, 1, 1], vertical_alignment="center", gap="small")
            with title:
                st.html(
                    '<div class="ql-ai-panel-title"><strong>DeepSeek 助手</strong>'
                    '<span>AI RESEARCH ASSISTANT</span></div>'
                )
            with maximize:
                st.button("⛶", key="deepseek_panel_maximize", width="stretch",
                          on_click=_toggle_deepseek_maximize, help="最大化或恢复 DeepSeek 助手")
            with close:
                st.button("×", key="deepseek_panel_close", width="stretch",
                          on_click=_close_deepseek_panel, help="关闭 DeepSeek 侧栏")
        with st.container(key="deepseek_panel_body"):
            render_deepseek(
                context, bundle, chat_only=False, connection_expanded=False, compact=True
            )
