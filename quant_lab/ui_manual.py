"""Complete offline reading experience for manuals and knowledge articles."""

from hashlib import sha256

import streamlit as st

from quant_lab.manual_content import (
    CATEGORY_TITLES,
    MANUAL_ORDER,
    ContentValidationError,
    KnowledgeArticle,
    ManualContentLibrary,
    load_manual_content,
)


SECTIONS = ("快速开始", "功能说明", "专业知识库")
FUNCTION_MANUAL_IDS = tuple(page_id for page_id in MANUAL_ORDER if page_id != "quick_start")
STATUS_LABELS = {
    "implemented": "软件已实现",
    "theory_only": "理论扩展 · 当前软件未实现",
    "academy_demo": "仅 Quant Academy 固定样本演示",
    "needs_code_review": "需结合代码边界阅读",
}


@st.cache_resource
def _manual_library() -> ManualContentLibrary:
    return load_manual_content()


def open_manual_page(page_id: str) -> None:
    st.session_state["manual_panel_open"] = True
    st.session_state["manual_section"] = (
        "快速开始" if page_id == "quick_start" else "功能说明"
    )
    st.session_state["manual_page_id"] = page_id
    st.session_state["manual_search_query"] = ""


def open_manual_article(article_id: str) -> None:
    st.session_state["manual_panel_open"] = True
    st.session_state["manual_section"] = "专业知识库"
    st.session_state["manual_article_id"] = article_id
    st.session_state["manual_search_query"] = ""


def _clear_search() -> None:
    st.session_state["manual_search_query"] = ""


def _reset_scroll_for_view(view_key: str) -> None:
    token = sha256(view_key.encode("utf-8")).hexdigest()[:16]
    st.html(
        f'<span class="ql-manual-view-token" data-token="{token}"></span>'
        '<script>(()=>{const body=document.querySelector(".st-key-manual_panel_body");'
        'const markers=document.querySelectorAll(".ql-manual-view-token");'
        'const marker=markers[markers.length-1];if(!body||!marker)return;'
        'const token=marker.dataset.token;if(body.dataset.manualViewToken===token)return;'
        'body.dataset.manualViewToken=token;body.scrollTop=0;})();</script>',
        unsafe_allow_javascript=True,
    )


def _close_manual_page() -> None:
    st.session_state.pop("manual_page_id", None)


def _close_article() -> None:
    st.session_state.pop("manual_article_id", None)


def _render_manual_page(library: ManualContentLibrary, page_id: str) -> None:
    page = library.get_manual(page_id)
    section = "快速开始" if page_id == "quick_start" else "功能说明"
    st.caption(f"使用手册 / {section} / {page.title}")
    if page_id != "quick_start":
        st.button("← 返回功能说明目录", key="manual_back_to_function_index", on_click=_close_manual_page)
    st.subheader(page.title)
    st.markdown(page.body)


def _render_function_index(library: ManualContentLibrary) -> None:
    st.caption("使用手册 / 功能说明")
    st.subheader("功能说明")
    st.write("按软件区域阅读控件、操作顺序、结果口径和已知边界。")
    for page_id in FUNCTION_MANUAL_IDS:
        page = library.get_manual(page_id)
        st.button(
            page.title,
            key=f"manual_index_{page_id}",
            width="stretch",
            on_click=open_manual_page,
            args=(page_id,),
        )


def _render_status(article: KnowledgeArticle) -> None:
    message = f"软件状态：{STATUS_LABELS[article.software_status]}"
    if article.software_status == "implemented":
        st.success(message)
    elif article.software_status == "theory_only":
        st.warning(message)
    else:
        st.info(message)


def _article_button(article: KnowledgeArticle, *, key: str, prefix: str = "") -> None:
    st.button(
        f"{prefix}{article.title} / {article.english_title}",
        key=key,
        width="stretch",
        on_click=open_manual_article,
        args=(article.id,),
    )


def _render_article(library: ManualContentLibrary, article_id: str) -> None:
    article = library.get_article(article_id)
    category_title = CATEGORY_TITLES[article.category]
    st.caption(f"使用手册 / 专业知识库 / {category_title} / {article.title}")
    st.button("← 返回专业知识库目录", key="manual_back_to_article_index", on_click=_close_article)
    _render_status(article)
    with st.expander("词条信息", expanded=False):
        st.write(f"英文名：{article.english_title}")
        st.write("别名：" + "、".join(article.aliases))
        st.write("关联模块：" + "、".join(article.related_modules))
        st.write("来源编号：" + "、".join(article.source_ids))
        st.write(f"最后核对：{article.last_verified.isoformat()}")
    st.markdown(article.body)

    if article.prerequisites:
        st.markdown("#### 前置概念")
        for prerequisite in library.prerequisites_for(article.id):
            _article_button(
                prerequisite,
                key=f"manual_prerequisite_{article.id}_{prerequisite.id}",
            )
    if article.related_articles:
        st.markdown("#### 相关词条")
        for related in library.related_for(article.id):
            _article_button(
                related,
                key=f"manual_related_{article.id}_{related.id}",
            )

    position = next(index for index, item in enumerate(library.articles) if item.id == article.id)
    if position + 1 < len(library.articles):
        next_article = library.articles[position + 1]
        st.markdown("#### 建议下一篇")
        _article_button(
            next_article,
            key=f"manual_next_{article.id}_{next_article.id}",
            prefix="下一篇 · ",
        )


def _render_article_index(library: ManualContentLibrary) -> None:
    st.caption("使用手册 / 专业知识库")
    st.subheader("专业知识库")
    st.write("按分类浏览 85 篇专业文章；每篇文章都标明当前软件实现边界。")
    category = st.selectbox(
        "专业分类",
        library.category_order,
        key="manual_category",
        format_func=lambda value: CATEGORY_TITLES[value],
    )
    articles = library.articles_in_category(category)
    st.caption(f"{CATEGORY_TITLES[category]} · {len(articles)} 篇")
    if not articles:
        st.warning("当前分类没有可用文章。")
        return
    for article in articles:
        _article_button(article, key=f"manual_article_index_{article.id}")


def _render_search_results(library: ManualContentLibrary, query: str) -> None:
    manuals = library.search_manuals(query)
    articles = library.search_articles(query)
    st.caption(f"本地搜索 / {query}")
    st.button("清除搜索", key="manual_search_clear", on_click=_clear_search)
    if not manuals and not articles:
        st.warning("没有找到匹配内容。请尝试中文标题、英文名、别名或正文关键词。")
        return
    st.write(f"找到 {len(manuals)} 篇手册、{len(articles)} 篇专业文章。")
    if manuals:
        st.markdown("#### 手册")
        for page in manuals:
            st.button(
                f"手册 · {page.title}",
                key=f"manual_search_page_{page.id}",
                width="stretch",
                on_click=open_manual_page,
                args=(page.id,),
            )
    if articles:
        st.markdown("#### 专业文章")
        for article in articles:
            _article_button(
                article,
                key=f"manual_search_article_{article.id}",
                prefix="词条 · ",
            )


def render_manual() -> None:
    st.caption("离线使用手册 · 阅读和搜索不会调用 AI")
    try:
        library = _manual_library()
        section = st.radio("使用手册分区", SECTIONS, key="manual_section")
        query = st.text_input(
            "搜索手册与专业知识",
            key="manual_search_query",
            placeholder="中文标题、英文名、别名或正文关键词",
        ).strip()
        _reset_scroll_for_view("|".join((
            section,
            query,
            str(st.session_state.get("manual_page_id", "")),
            str(st.session_state.get("manual_article_id", "")),
            str(st.session_state.get("manual_category", "")),
        )))
        if query:
            _render_search_results(library, query)
            return
        if section == "快速开始":
            _render_manual_page(library, "quick_start")
        elif section == "功能说明":
            selected = st.session_state.get("manual_page_id")
            if selected in FUNCTION_MANUAL_IDS:
                _render_manual_page(library, selected)
            else:
                _render_function_index(library)
        else:
            selected = st.session_state.get("manual_article_id")
            if selected:
                _render_article(library, selected)
            else:
                _render_article_index(library)
    except (ContentValidationError, KeyError, ValueError) as exc:
        st.error(f"使用手册内容不可用：{exc}")
        st.info("请检查只读内容资源是否完整；程序不会用演示文本替代缺失内容。")


def _close_manual_panel() -> None:
    st.session_state["manual_panel_open"] = False
    if st.session_state.get("maximized_panel") == "manual":
        st.session_state["maximized_panel"] = None


def _toggle_manual_maximize() -> None:
    st.session_state["maximized_panel"] = (
        None if st.session_state.get("maximized_panel") == "manual" else "manual"
    )


def render_manual_panel() -> None:
    with st.container(key="manual_side_panel"):
        st.html(
            '<div class="ql-resize-handle" data-panel="manual" role="separator" '
            'aria-label="调整使用手册宽度" tabindex="0"></div>'
        )
        with st.container(key="manual_panel_header"):
            title, maximize, close = st.columns(
                [5, 1, 1], vertical_alignment="center", gap="small"
            )
            with title:
                st.html(
                    '<div class="ql-ai-panel-title"><strong>使用手册</strong>'
                    '<span>MANUAL</span></div>'
                )
            with maximize:
                st.button(
                    "⛶",
                    key="manual_panel_maximize",
                    width="stretch",
                    on_click=_toggle_manual_maximize,
                    help="最大化或恢复使用手册",
                )
            with close:
                st.button(
                    "×",
                    key="manual_panel_close",
                    width="stretch",
                    on_click=_close_manual_panel,
                    help="关闭使用手册",
                )
        with st.container(key="manual_panel_body"):
            render_manual()
