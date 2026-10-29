"""Session-only manual history, shared by catalog, search, and related links."""

import streamlit as st

SECTIONS = ("快速开始", "功能说明", "专业知识库")
SEARCH_PAGE_SIZE = 12
VIEW_KEYS = ("manual_section", "manual_page_id", "manual_article_id", "manual_search_query",
             "manual_search_limit", "manual_category")


def remember_view():
    view = {key: st.session_state.get(key) for key in VIEW_KEYS}
    view["manual_section"] = view["manual_section"] or "快速开始"
    view["manual_search_query"] = view["manual_search_query"] or ""
    view["manual_search_limit"] = view["manual_search_limit"] or SEARCH_PAGE_SIZE
    st.session_state["_manual_current_view"] = view
    return view


def _push_history():
    current = st.session_state.get("_manual_current_view")
    if current:
        history = st.session_state.setdefault("_manual_history", [])
        if not history or history[-1] != current:
            history.append(dict(current))
            del history[:-64]


def _clear_search():
    st.session_state["manual_search_query"] = ""
    st.session_state["manual_search_last_query"] = ""
    st.session_state["manual_search_limit"] = SEARCH_PAGE_SIZE


def _section_changed():
    _push_history()
    st.session_state.pop("manual_page_id", None)
    st.session_state.pop("manual_article_id", None)
    _clear_search()


def _category_changed():
    _push_history()


def _search_changed():
    query = st.session_state.get("manual_search_query", "").strip()
    if query != st.session_state.get("manual_search_last_query", ""):
        _push_history()
        st.session_state["manual_search_limit"] = SEARCH_PAGE_SIZE
        st.session_state["manual_search_last_query"] = query


def _show_more_results():
    st.session_state["manual_search_limit"] = st.session_state.get("manual_search_limit", SEARCH_PAGE_SIZE) + SEARCH_PAGE_SIZE


def _open(kind, identifier):
    current = st.session_state.get("_manual_current_view", {})
    target = "manual_page_id" if kind == "manual" else "manual_article_id"
    previous_id = current.get(target)
    if kind == "manual" and current.get("manual_section") == "快速开始":
        previous_id = "quick_start"
    if previous_id != identifier or current.get("manual_search_query"):
        _push_history()
    st.session_state["manual_panel_open"] = True
    st.session_state["active_dock_panel"] = "manual"
    st.session_state["_dock_reveal"] = "manual"
    if st.session_state.get("maximized_panel") not in (None, "manual"):
        st.session_state["maximized_panel"] = None
    _clear_search()
    st.session_state["manual_section"] = "专业知识库" if kind == "article" else "快速开始" if identifier == "quick_start" else "功能说明"
    st.session_state[target] = identifier
    st.session_state.pop("manual_article_id" if kind == "manual" else "manual_page_id", None)


def open_manual_page(page_id):
    _open("manual", page_id)


def open_manual_article(article_id):
    _open("article", article_id)


def _open_related_article(article_id):
    open_manual_article(article_id)


def _open_search_manual(page_id):
    open_manual_page(page_id)


def _open_search_article(article_id):
    open_manual_article(article_id)


def _toolbar_back_action():
    history = st.session_state.get("_manual_history", [])
    if not history:
        return
    target = history.pop()
    for key in VIEW_KEYS:
        if target.get(key) is None:
            st.session_state.pop(key, None)
        else:
            st.session_state[key] = target[key]
    st.session_state["manual_search_last_query"] = target.get("manual_search_query", "")
    st.session_state["_manual_restore_scroll"] = True


def _toolbar_back_help():
    history = st.session_state.get("_manual_history", [])
    if not history:
        return None
    target = history[-1]
    if target.get("manual_search_query"):
        return "返回搜索结果"
    if target.get("manual_article_id"):
        return "返回上一词条"
    if target.get("manual_page_id"):
        return "返回上一手册页"
    return {"专业知识库":"返回知识库目录", "功能说明":"返回功能目录", "快速开始":"返回快速开始"}[target["manual_section"]]
