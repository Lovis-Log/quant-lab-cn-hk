"""Complete offline reading experience for manuals and knowledge articles."""

from hashlib import sha256

import streamlit as st

from quant_lab.manual_content import (
    CATEGORY_TITLES,
    MANUAL_ORDER,
    ContentSearchResult,
    ContentValidationError,
    KnowledgeArticle,
    ManualContentLibrary,
    load_manual_content,
)


SECTIONS = ("快速开始", "功能说明", "专业知识库")
FUNCTION_MANUAL_IDS = tuple(page_id for page_id in MANUAL_ORDER if page_id != "quick_start")
SEARCH_PAGE_SIZE = 12
STATUS_LABELS = {
    "implemented": "软件已实现",
    "theory_only": "理论扩展 · 当前软件未实现",
    "academy_demo": "仅 Quant Academy 固定样本演示",
    "needs_code_review": "需结合代码边界阅读",
}


@st.cache_resource
def _manual_library() -> ManualContentLibrary:
    return load_manual_content()


from quant_lab.ui_manual_navigation import (
    _section_changed, _category_changed, _search_changed, _show_more_results,
    open_manual_page, open_manual_article, _open_related_article,
    _open_search_manual, _open_search_article, _toolbar_back_action, _toolbar_back_help,
    remember_view,
)


def _reset_scroll_for_view(view_key: str) -> None:
    token = sha256(view_key.encode("utf-8")).hexdigest()[:16]
    restore = st.session_state.pop("_manual_restore_scroll", False)
    st.html(f'<span class="ql-manual-view-token" data-token="{token}" data-restore="{str(restore).lower()}"></span>'
            + MANUAL_SCROLL_JS, unsafe_allow_javascript=True)


MANUAL_SCROLL_JS = """
<script>(()=>{
  const body=[...document.querySelectorAll('.st-key-manual_panel_body')].at(-1);
  const marker=[...document.querySelectorAll('.ql-manual-view-token')].at(-1);
  if(!body||!marker)return;
  const positions=window.__qlManualScrollPositions ||= {};
  if(!body.dataset.qlHistoryBound){
    body.dataset.qlHistoryBound='1';
    body.addEventListener('scroll',()=>{if(!body.dataset.qlNavigating&&body.dataset.manualViewToken)positions[body.dataset.manualViewToken]=body.scrollTop;},{passive:true});
    body.addEventListener('click',event=>{if(event.target.closest('button')){positions[body.dataset.manualViewToken]=body.scrollTop;body.dataset.qlNavigating='1';}},true);
  }
  const token=marker.dataset.token;
  if(body.dataset.manualViewToken===token){if(!body.__qlRestoreCancel)body.dataset.qlNavigating='';return;}
  body.__qlRestoreCancel?.();
  body.dataset.manualViewToken=token;
  body.dataset.qlNavigating='1';
  const desired=marker.dataset.restore==='true'?(positions[token]||0):0;
  let frame=0,timer=0,done=false;
  const stop=()=>{
    if(done)return;done=true;cancelAnimationFrame(frame);clearTimeout(timer);
    mutation.disconnect();resize.disconnect();body.__qlRestoreCancel=null;body.dataset.qlNavigating='';
  };
  const finish=()=>{body.scrollTop=desired;positions[token]=body.scrollTop;stop();};
  const schedule=()=>{
    if(done)return;cancelAnimationFrame(frame);
    frame=requestAnimationFrame(()=>{
      if(body.dataset.manualViewToken!==token){stop();return;}
      const height=body.scrollHeight;body.scrollTop=desired;
      frame=requestAnimationFrame(()=>{
        if(body.scrollHeight===height&&body.scrollHeight-body.clientHeight>=desired-1&&
           document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning')finish();
      });
    });
  };
  const mutation=new MutationObserver(schedule),resize=new ResizeObserver(schedule);
  mutation.observe(body,{childList:true,subtree:true,characterData:true});
  const app=document.querySelector('[data-testid=stApp]');
  if(app)mutation.observe(app,{attributes:true,attributeFilter:['data-test-script-state']});
  resize.observe(body.firstElementChild||body);
  body.__qlRestoreCancel=stop;
  timer=setTimeout(finish,1500);
  schedule();
})();</script>
"""


def _render_sticky_toolbar() -> tuple[str, str]:
    with st.container(key="manual_sticky_toolbar"):
        back_help = _toolbar_back_help()
        columns = st.columns([32, 44, 24] if back_help else [28, 72], gap="small")
        section_column, search_column = columns[:2]
        with section_column:
            section = st.selectbox(
                "当前分区",
                SECTIONS,
                key="manual_section",
                label_visibility="collapsed",
                on_change=_section_changed,
            )
        with search_column:
            query = st.text_input(
                "搜索手册与专业知识",
                key="manual_search_query",
                placeholder="搜索标题、别名或正文",
                label_visibility="collapsed",
                on_change=_search_changed,
            ).strip()
        if back_help:
            with columns[2]:
                st.button(
                    "← 返回",
                    key="manual_toolbar_back",
                    width="stretch",
                    on_click=_toolbar_back_action,
                    help=back_help,
                )
    return section, query


def _render_article_link_grid(
    articles: tuple[KnowledgeArticle, ...], *, key_prefix: str
) -> None:
    for start in range(0, len(articles), 2):
        columns = st.columns(2, gap="small")
        for offset, article in enumerate(articles[start:start + 2]):
            with columns[offset]:
                st.button(
                    f"{article.title} / {article.english_title}",
                    key=f"{key_prefix}_{article.id}",
                    width="stretch",
                    type="tertiary",
                    on_click=_open_related_article,
                    args=(article.id,),
                )


def _render_manual_page(library: ManualContentLibrary, page_id: str) -> None:
    page = library.get_manual(page_id)
    section = "快速开始" if page_id == "quick_start" else "功能说明"
    st.caption(f"使用手册 / {section} / {page.title}")
    st.subheader(page.title)
    st.markdown(page.body)
    if page.related_articles:
        st.markdown("#### 相关术语")
        _render_article_link_grid(
            tuple(library.get_article(article_id) for article_id in page.related_articles),
            key_prefix=f"manual_term_{page.id}",
        )
    if page.footer:
        st.markdown(page.footer)


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


def _render_article(library: ManualContentLibrary, article_id: str) -> None:
    article = library.get_article(article_id)
    category_title = CATEGORY_TITLES[article.category]
    st.caption(f"使用手册 / 专业知识库 / {category_title} / {article.title}")
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
        _render_article_link_grid(
            library.prerequisites_for(article.id),
            key_prefix=f"manual_prerequisite_{article.id}",
        )
    if article.related_articles:
        st.markdown("#### 相关词条")
        _render_article_link_grid(
            library.related_for(article.id),
            key_prefix=f"manual_related_{article.id}",
        )
    position = next(index for index, item in enumerate(library.articles) if item.id == article.id)
    if position + 1 < len(library.articles):
        st.markdown("#### 建议下一篇")
        _render_article_link_grid(
            (library.articles[position + 1],),
            key_prefix=f"manual_next_{article.id}",
        )


def _render_article_index(library: ManualContentLibrary) -> None:
    st.caption("使用手册 / 专业知识库")
    st.subheader("专业知识库")
    st.write("按分类浏览 85 篇专业文章；每篇文章都标明当前软件实现边界。")
    category = st.selectbox(
        "专业分类",
        library.category_order,
        key="manual_category",
        on_change=_category_changed,
        format_func=lambda value: CATEGORY_TITLES[value],
    )
    articles = library.articles_in_category(category)
    st.caption(f"{CATEGORY_TITLES[category]} · {len(articles)} 篇")
    if not articles:
        st.warning("当前分类没有可用文章。")
        return
    for article in articles:
        st.button(
            f"{article.title} / {article.english_title}",
            key=f"manual_article_index_{article.id}",
            width="stretch",
            on_click=open_manual_article,
            args=(article.id,),
        )


def _search_result_meta(result: ContentSearchResult) -> str:
    if result.kind == "manual":
        return "使用手册"
    return f"{CATEGORY_TITLES[result.category]} · {STATUS_LABELS[result.software_status]}"


def _render_search_card(result: ContentSearchResult, *, rank: int) -> None:
    with st.container(key=f"manual_search_card_{result.kind}_{result.item_id}", border=True):
        badge = "最相关 · " if rank == 0 else ""
        st.caption(f"{badge}{_search_result_meta(result)} · {result.match_reason}")
        title = result.title + (f" / {result.english_title}" if result.english_title else "")
        if result.kind == "manual":
            st.button(
                title,
                key=f"manual_search_page_{result.item_id}",
                width="stretch",
                type="tertiary",
                on_click=_open_search_manual,
                args=(result.item_id,),
            )
        else:
            st.button(
                title,
                key=f"manual_search_article_{result.item_id}",
                width="stretch",
                type="tertiary",
                on_click=_open_search_article,
                args=(result.item_id,),
            )
        st.write(result.excerpt)


def _render_search_results(library: ManualContentLibrary, query: str) -> None:
    results = library.search(query)
    st.caption(f"本地搜索 / {query}")
    if not results:
        st.warning("没有找到匹配内容。请尝试中文标题、英文名、别名或正文关键词。")
        return
    visible_count = min(
        st.session_state.get("manual_search_limit", SEARCH_PAGE_SIZE), len(results)
    )
    st.write(f"找到 {len(results)} 项，按相关度排序；当前显示 {visible_count} 项。")
    visible_results = results[:visible_count]
    for start in range(0, len(visible_results), 2):
        columns = st.columns(2, gap="small")
        for offset, result in enumerate(visible_results[start:start + 2]):
            with columns[offset]:
                _render_search_card(result, rank=start + offset)
    if visible_count < len(results):
        st.button(
            f"显示更多（剩余 {len(results) - visible_count} 项）",
            key="manual_search_more",
            width="stretch",
            on_click=_show_more_results,
        )


@st.fragment
def render_manual() -> None:
    st.caption("离线使用手册 · 阅读和搜索不会调用 AI")
    try:
        library = _manual_library()
        section, query = _render_sticky_toolbar()
        _reset_scroll_for_view("|".join((
            section,
            query,
            str(st.session_state.get("manual_page_id", "")),
            str(st.session_state.get("manual_article_id", "")),
            str(st.session_state.get("manual_category", "")),
            str(st.session_state.get("manual_search_limit", SEARCH_PAGE_SIZE)),
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
    finally:
        remember_view()


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

                )
            with close:
                st.button(
                    "×",
                    key="manual_panel_close",
                    width="stretch",
                    on_click=_close_manual_panel,

                )
        with st.container(key="manual_panel_body"):
            render_manual()
