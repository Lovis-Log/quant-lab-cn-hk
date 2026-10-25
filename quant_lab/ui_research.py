"""Unified categorized notes and immutable research archives."""

from html import escape
from pathlib import Path
import json
import re
import sqlite3
from uuid import uuid4
import zlib

import streamlit as st

from quant_lab import notes
from quant_lab.market_data import display_security
from quant_lab.storage import export_experiment_zip, get_experiment, render_report, replay_experiment


def _category_label(row: dict) -> str:
    return "　" * row.get("depth", 0) + row["name"]


def _autosave_draft(draft_id: str) -> None:
    try:
        notes.save_draft(
            draft_id, title=st.session_state.get("note_editor_title", ""),
            content=st.session_state.get("note_editor_content", ""),
            category_id=st.session_state.get("note_editor_category", notes.UNCATEGORIZED_ID),
            note_id=st.session_state.get("note_editor_note_id"),
            secrets=(st.session_state.get("deepseek_api_key", ""),),
        )
    except (OSError, ValueError, sqlite3.Error) as exc:
        st.session_state["note_editor_error"] = str(exc)


def _load_editor(note_id: int | None = None) -> None:
    st.session_state["note_editor_draft_id"] = uuid4().hex
    st.session_state["note_editor_note_id"] = note_id
    if note_id is None:
        st.session_state["note_editor_title"] = ""
        st.session_state["note_editor_content"] = ""
        st.session_state["note_editor_category"] = notes.UNCATEGORIZED_ID
    else:
        record = notes.get_note(note_id)
        st.session_state["note_editor_title"] = record["title"]
        st.session_state["note_editor_content"] = record["content"]
        st.session_state["note_editor_category"] = record.get("category_id") or notes.UNCATEGORIZED_ID
        st.session_state["note_editor_scroll_pending"] = True
    _autosave_draft(st.session_state["note_editor_draft_id"])


def _restore_editor() -> None:
    """Restore the most recent working copy, then the latest saved note."""
    if "note_editor_draft_id" in st.session_state:
        return
    existing = notes.latest_draft()
    if existing:
        st.session_state["note_editor_draft_id"] = existing["id"]
        st.session_state["note_editor_note_id"] = existing["note_id"]
        st.session_state["note_editor_title"] = existing["title"]
        st.session_state["note_editor_content"] = existing["content"]
        st.session_state["note_editor_category"] = existing["category_id"]
        return
    recent = notes.list_library_items(kind="笔记")
    _load_editor(recent[0]["id"] if recent else None)


def _new_note() -> None:
    draft_id = st.session_state.get("note_editor_draft_id")
    if draft_id:
        _autosave_draft(draft_id)
    _load_editor()
    st.session_state["notes_view"] = "editor"


def _open_note(note_id: int) -> None:
    draft_id = st.session_state.get("note_editor_draft_id")
    if draft_id:
        _autosave_draft(draft_id)
    _load_editor(note_id)
    st.session_state["notes_view"] = "editor"


def _show_history() -> None:
    draft_id = st.session_state.get("note_editor_draft_id")
    if draft_id:
        _autosave_draft(draft_id)
    st.session_state["notes_view"] = "history"


def _show_editor() -> None:
    st.session_state["notes_view"] = "editor"


def _insert_attachment(draft_id: str, attachment_id: str, original_name: str) -> None:
    st.session_state["note_editor_content"] = st.session_state.get("note_editor_content", "") + (
        f"\n\n![{original_name}](attachment://{attachment_id})\n"
    )
    _autosave_draft(draft_id)


def _discard_and_reset(draft_id: str) -> None:
    notes.discard_draft(draft_id)
    _load_editor()


def _render_categories(categories: list[dict]) -> None:
    by_id = {row["id"]: row for row in categories}
    st.markdown("#### 分类管理")
    parent = st.selectbox("父分类", [None] + list(by_id),
                          format_func=lambda value: "根目录" if value is None else _category_label(by_id[value]),
                          key="category_parent")
    name = st.text_input("分类名称", max_chars=80, key="category_name")
    if st.button("新增分类", key="category_add", disabled=not name.strip()):
        try:
            notes.create_category(name, parent)
            st.rerun()
        except (ValueError, OSError, sqlite3.Error) as exc:
            st.warning(str(exc))
    editable = [row for row in categories if not row["is_system"]]
    if editable:
        chosen = st.selectbox("编辑分类", [row["id"] for row in editable],
                              format_func=lambda value: _category_label(by_id[value]), key="category_edit")
        new_name = st.text_input("新名称", value=by_id[chosen]["name"], key="category_new_name")
        move_parent = st.selectbox("移动到", [None] + [row["id"] for row in categories if row["id"] != chosen],
                                   format_func=lambda value: "根目录" if value is None else _category_label(by_id[value]),
                                   key="category_move_parent")
        a, b, c = st.columns(3)
        if a.button("重命名", key="category_rename"):
            notes.rename_category(chosen, new_name); st.rerun()
        if b.button("移动", key="category_move"):
            try:
                notes.move_category(chosen, move_parent); st.rerun()
            except (ValueError, OSError, sqlite3.Error) as exc:
                st.warning(str(exc))
        if c.button("删除", key="category_delete"):
            notes.delete_category(chosen); st.rerun()


def _render_markdown(content: str, attachments: list[dict]) -> None:
    safe_content = re.sub(
        r"!\[[^\]]*\]\(attachment://[a-f0-9]{32}\)", "", content or "（空笔记）"
    )
    st.markdown(safe_content)
    images = {item["id"]: item for item in attachments
              if Path(item["original_name"]).suffix.lower() in notes.IMAGE_EXTENSIONS}
    for token in notes.attachment_tokens(content):
        item = images.get(token)
        if item:
            try:
                st.image(notes.attachment_bytes(item), caption=item["original_name"])
            except (OSError, ValueError) as exc:
                st.warning(str(exc))


def _render_editor(categories: list[dict]) -> None:
    by_id = {row["id"]: row for row in categories}
    _restore_editor()
    draft_id = st.session_state["note_editor_draft_id"]
    note_id = st.session_state.get("note_editor_note_id")
    if st.session_state.pop("note_editor_scroll_pending", False):
        st.html(
            '<script>(()=>{const body=document.querySelector(".st-key-notes_panel_body");'
            'if(body)requestAnimationFrame(()=>body.scrollTo({top:0,behavior:"smooth"}));})();</script>',
            unsafe_allow_javascript=True,
        )
    st.text_input("笔记标题", key="note_editor_title", on_change=_autosave_draft, args=(draft_id,))
    st.text_area("Markdown 正文", key="note_editor_content", height=360,
                 on_change=_autosave_draft, args=(draft_id,),
                 help="字段变化时自动保存草稿；点击保存后写入正式笔记。")
    draft_key = json.dumps(f"quantlab.noteDraft.{draft_id}")
    st.html(f"""
    <script>
    (() => {{
      const key = {draft_key};
      const bind = () => {{
        const title = document.querySelector('input[aria-label="笔记标题"]');
        const content = document.querySelector('textarea[aria-label="Markdown 正文"]');
        if (!title || !content || content.dataset.localDraftBound === '1') return;
        content.dataset.localDraftBound = '1';
        const saved = localStorage.getItem(key);
        if (saved) {{
          try {{
            const value = JSON.parse(saved);
            const setInput = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            const setArea = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
            if (value.title !== undefined && value.title !== title.value) {{
              setInput.call(title, value.title); title.dispatchEvent(new Event('input', {{bubbles:true}}));
            }}
            if (value.content !== undefined && value.content !== content.value) {{
              setArea.call(content, value.content); content.dispatchEvent(new Event('input', {{bubbles:true}}));
            }}
          }} catch (_) {{ localStorage.removeItem(key); }}
        }}
        const save = () => localStorage.setItem(key, JSON.stringify({{
          title:title.value, content:content.value, updatedAt:new Date().toISOString()
        }}));
        title.addEventListener('input', save);
        content.addEventListener('input', save);
      }};
      bind();
      const observer = new MutationObserver(bind);
      observer.observe(document.body, {{childList:true,subtree:true}});
      window.setTimeout(() => observer.disconnect(), 5000);
    }})();
    </script>
    """, unsafe_allow_javascript=True)
    save_col, new_col = st.columns(2)
    if save_col.button("保存笔记", key="note_save", width="stretch"):
        try:
            saved = notes.save_note(
                title=st.session_state.get("note_editor_title", ""),
                content=st.session_state.get("note_editor_content", ""),
                category_id=st.session_state.get("note_editor_category", notes.UNCATEGORIZED_ID),
                note_id=note_id, draft_id=draft_id,
                secrets=(st.session_state.get("deepseek_api_key", ""),),
            )
            st.session_state["note_editor_notice"] = f"笔记 #{saved} 已保存。"
            resume_draft_id = uuid4().hex
            st.session_state["note_editor_note_id"] = saved
            st.session_state["note_editor_draft_id"] = resume_draft_id
            notes.save_draft(
                resume_draft_id,
                title=st.session_state.get("note_editor_title", ""),
                content=st.session_state.get("note_editor_content", ""),
                category_id=st.session_state.get("note_editor_category", notes.UNCATEGORIZED_ID),
                note_id=saved,
                secrets=(st.session_state.get("deepseek_api_key", ""),),
            )
            st.rerun()
        except (OSError, ValueError, sqlite3.Error, KeyError) as exc:
            st.error(str(exc))
    new_col.button("新建笔记", key="note_new", width="stretch", on_click=_new_note)
    if st.session_state.get("note_editor_notice"):
        st.success(st.session_state.pop("note_editor_notice"))
    if st.session_state.get("note_editor_error"):
        st.warning(st.session_state.pop("note_editor_error"))
    with st.expander("更多选项（分类与附件）", expanded=False):
        st.selectbox("笔记分类", list(by_id), key="note_editor_category",
                     format_func=lambda value: _category_label(by_id[value]),
                     on_change=_autosave_draft, args=(draft_id,))
        uploads = st.file_uploader("添加附件", accept_multiple_files=True,
            type=[ext[1:] for ext in sorted(notes.ALLOWED_EXTENSIONS)], key="note_attachment_upload")
        if st.button("保存所选附件到草稿", disabled=not uploads, key="note_attachment_save"):
            try:
                _autosave_draft(draft_id)
                for uploaded in uploads:
                    notes.save_attachment(uploaded.getvalue(), uploaded.name, draft_id=draft_id)
                st.success("附件已复制到托管资料目录。")
                st.rerun()
            except (OSError, ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
        attachments = notes.list_attachments(draft_id=draft_id)
        if note_id:
            attachments = notes.list_attachments(note_id=note_id) + attachments
        for item in attachments:
            row = st.columns([3, 1, 1])
            row[0].caption(f"📎 {item['original_name']} · {item['size_bytes']/1024:.1f} KB")
            if Path(item["original_name"]).suffix.lower() in notes.IMAGE_EXTENSIONS:
                row[1].button("插入", key=f"insert_attachment_{item['id']}",
                              on_click=_insert_attachment,
                              args=(draft_id, item["id"], item["original_name"]))
            row[2].download_button(
                "下载", notes.attachment_bytes(item), file_name=item["original_name"],
                mime=item["mime_type"], key=f"download_attachment_{item['id']}",
            )
        st.markdown("#### Markdown 预览")
        _render_markdown(st.session_state.get("note_editor_content", ""), attachments)
        if note_id:
            st.download_button(
                "导出笔记与附件 ZIP", notes.export_note_zip(note_id),
                file_name=f"note-{note_id}.zip", mime="application/zip",
            )
        st.button("放弃草稿", key="note_discard", width="stretch",
                  on_click=_discard_and_reset, args=(draft_id,))
        if note_id:
            if st.button("移到回收站", key="note_trash_current", width="stretch"):
                try:
                    notes.trash_item("笔记", note_id)
                    notes.discard_draft(draft_id)
                    for key in (
                        "note_editor_draft_id", "note_editor_note_id", "note_editor_title",
                        "note_editor_content", "note_editor_category",
                    ):
                        st.session_state.pop(key, None)
                    st.session_state["note_editor_notice"] = "笔记已移到回收站。"
                    st.rerun()
                except (OSError, ValueError, sqlite3.Error) as exc:
                    st.error(str(exc))


def _render_history() -> None:
    st.button("← 返回编辑", key="notes_history_back", on_click=_show_editor)
    query = st.text_input(
        "搜索历史笔记", key="notes_history_search", label_visibility="collapsed",
        placeholder="搜索标题或正文…",
    )
    items = notes.list_library_items(query=query, kind="笔记")
    if not items:
        st.info("没有找到历史笔记。" if query.strip() else "还没有已保存的研究笔记。")
        return
    st.caption(f"找到 {len(items)} 条笔记，按最近编辑排序。")
    for item in items[:50]:
        content = " ".join((item.get("content") or "").split())
        snippet = content[:72] + ("…" if len(content) > 72 else "")
        updated = str(item["updated_at"] or item["created_at"]).replace("T", " ")[:16]
        with st.container(border=True, key=f"note_history_card_{item['id']}"):
            st.button(
                item["title"], key=f"note_history_open_{item['id']}", width="stretch",
                on_click=_open_note, args=(item["id"],), help="打开并继续编辑这篇笔记",
            )
            st.caption(f"更新于 {updated}")
            if snippet:
                st.html(f'<p class="ql-note-history-snippet">{escape(snippet)}</p>')


def _render_experiment_archive(categories: list[dict]) -> dict | None:
    query = st.text_input("搜索实验标题或假设", key="experiment_archive_search")
    items = notes.list_library_items(query=query, kind="实验")
    if not items:
        st.info("没有符合条件的实验档案。")
        return None
    chosen = st.selectbox(
        "选择实验", range(len(items)), key="experiment_archive_item",
        format_func=lambda index: items[index]["title"],
    )
    item = items[chosen]
    category_map = {row["id"]: row for row in categories}
    category_ids = list(category_map)
    current_category = item["category_id"] or notes.UNCATEGORIZED_ID
    target_category = st.selectbox(
        "实验分类", category_ids, index=category_ids.index(current_category),
        format_func=lambda value: _category_label(category_map[value]),
        key=f"experiment_category_{item['id']}",
    )
    if target_category != current_category:
        notes.set_item_category("实验", item["id"], target_category)
        st.rerun()
    if st.button("将实验移到回收站", key="experiment_trash"):
        notes.trash_item("实验", item["id"])
        st.rerun()
    try:
        record = get_experiment(item["id"])
    except (OSError, ValueError, KeyError, sqlite3.Error, zlib.error) as exc:
        st.error(f"读取实验失败：{exc}")
        return None
    st.write(record["hypothesis"])
    st.write(display_security(record["market"], record["symbol"], record.get("company_name")))
    st.caption(f"区间 {record['start_date']} 至 {record['end_date']} · {record['audit_id']}")
    st.download_button("导出 Markdown 研究报告", render_report(record).encode("utf-8-sig"),
                       file_name=f"quant_lab_{record['id']}_{record['audit_id']}.md", mime="text/markdown")
    st.download_button("导出可复现研究包 ZIP", export_experiment_zip(record),
                       file_name=f"quant_lab_{record['id']}_{record['audit_id']}.zip", mime="application/zip")
    if st.button("从存档数据重新计算", key="replay_archived_experiment"):
        try:
            st.success(f"复算成功：指纹 {replay_experiment(record).audit_id}。")
        except ValueError as exc:
            st.error(f"复算失败：{exc}")
    return record


def _render_recycle_bin() -> None:
    query = st.text_input("搜索回收站", key="recycle_search")
    items = notes.list_library_items(query=query, kind="全部", trashed=True)
    if not items:
        st.info("回收站为空。")
        return
    chosen = st.selectbox(
        "选择已删除内容", range(len(items)), key="recycle_item",
        format_func=lambda index: f"{items[index]['kind']} · {items[index]['title']}",
    )
    item = items[chosen]
    restore, confirm_col, delete = st.columns([1, 1.5, 1])
    if restore.button("恢复", key="recycle_restore", width="stretch"):
        notes.restore_item(item["kind"], item["id"])
        st.rerun()
    confirm = confirm_col.checkbox("确认永久删除", key="recycle_delete_confirm")
    if delete.button("永久删除", key="recycle_delete", disabled=not confirm, width="stretch"):
        notes.permanent_delete_item(item["kind"], item["id"])
        st.rerun()


def _render_management(categories: list[dict]) -> dict | None:
    selected = None
    with st.expander("更多管理（实验 / 分类 / 回收站）", expanded=False):
        mode = st.selectbox(
            "管理内容", ("实验档案", "分类管理", "回收站"), key="notes_management_mode",
        )
        if mode == "实验档案":
            selected = _render_experiment_archive(categories)
        elif mode == "分类管理":
            _render_categories(categories)
        else:
            _render_recycle_bin()
    return selected


def render_research_notes() -> dict | None:
    categories = notes.list_categories()
    st.session_state.setdefault("notes_view", "editor")
    if st.session_state["notes_view"] == "history":
        _render_history()
        return None
    _render_editor(categories)
    return _render_management(categories)


def _close_panel() -> None:
    st.session_state["notes_panel_open"] = False
    if st.session_state.get("maximized_panel") == "notes":
        st.session_state["maximized_panel"] = None


def _toggle_maximize() -> None:
    st.session_state["maximized_panel"] = None if st.session_state.get("maximized_panel") == "notes" else "notes"


def render_research_panel() -> dict | None:
    with st.container(key="notes_side_panel"):
        st.html('<div class="ql-resize-handle" data-panel="notes" role="separator" aria-label="调整研究笔记宽度" tabindex="0"></div>')
        with st.container(key="notes_panel_header"):
            title, history, maximize, close = st.columns([4.6, 1, 1, 1], vertical_alignment="center", gap="small")
            with title:
                st.html('<div class="ql-ai-panel-title"><strong>研究笔记</strong><span>RESEARCH NOTES</span></div>')
            with history:
                st.button(
                    "⌕", key="notes_panel_history", on_click=_show_history, width="stretch",
                    help="搜索历史笔记",
                )
            with maximize:
                st.button("⛶", key="notes_panel_maximize", on_click=_toggle_maximize, width="stretch")
            with close:
                st.button("×", key="notes_panel_close", on_click=_close_panel, width="stretch")
            st.html(
                '<script>(()=>{const button=document.querySelector(".st-key-notes_panel_history button");'
                'if(button){button.setAttribute("aria-label","历史笔记");button.title="搜索历史笔记";}})();</script>',
                unsafe_allow_javascript=True,
            )
        with st.container(key="notes_panel_body"):
            return render_research_notes()
