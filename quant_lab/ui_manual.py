"""Stage-2 preview shell for the offline reading manual."""

import streamlit as st

from quant_lab.manual_content import (
    CATEGORY_TITLES,
    ContentValidationError,
    ManualContentLibrary,
    load_manual_content,
)


PREVIEW_SECTIONS = ("快速开始", "功能说明", "专业知识库")


@st.cache_resource
def _manual_library() -> ManualContentLibrary:
    return load_manual_content()


def _render_manual(manual_id: str) -> None:
    page = _manual_library().get_manual(manual_id)
    st.subheader(page.title)
    st.markdown(page.body)


def _render_article(article_id: str) -> None:
    article = _manual_library().get_article(article_id)
    st.caption(
        f"{CATEGORY_TITLES[article.category]} · {article.software_status} · "
        f"核对日期 {article.last_verified.isoformat()}"
    )
    st.markdown(article.body)


def render_manual_preview() -> None:
    st.caption("阶段 2 预览 · 内容完全离线读取")
    st.info("当前只展示 3 个代表页面，用于验证阅读布局。完整目录、搜索和文章跳转将在后续阶段接入。")
    section = st.radio(
        "使用手册预览分区",
        PREVIEW_SECTIONS,
        key="manual_preview_section",
    )
    try:
        if section == "快速开始":
            _render_manual("quick_start")
        elif section == "功能说明":
            _render_manual("market_data")
        else:
            _render_article("ohlcv")
    except (ContentValidationError, KeyError) as exc:
        st.error(f"使用手册内容不可用：{exc}")


def _close_manual_panel() -> None:
    st.session_state["manual_panel_open"] = False
    if st.session_state.get("maximized_panel") == "manual":
        st.session_state["maximized_panel"] = None


def _toggle_manual_maximize() -> None:
    st.session_state["maximized_panel"] = (
        None if st.session_state.get("maximized_panel") == "manual" else "manual"
    )


def render_manual_preview_panel() -> None:
    with st.container(key="manual_side_panel"):
        st.html(
            '<div class="ql-resize-handle" data-panel="manual" role="separator" '
            'aria-label="调整使用手册预览宽度" tabindex="0"></div>'
        )
        with st.container(key="manual_panel_header"):
            title, maximize, close = st.columns(
                [5, 1, 1], vertical_alignment="center", gap="small"
            )
            with title:
                st.html(
                    '<div class="ql-ai-panel-title"><strong>使用手册（预览）</strong>'
                    '<span>MANUAL PREVIEW</span></div>'
                )
            with maximize:
                st.button(
                    "⛶",
                    key="manual_panel_maximize",
                    width="stretch",
                    on_click=_toggle_manual_maximize,
                    help="最大化或恢复使用手册预览",
                )
            with close:
                st.button(
                    "×",
                    key="manual_panel_close",
                    width="stretch",
                    on_click=_close_manual_panel,
                    help="关闭使用手册预览",
                )
        with st.container(key="manual_panel_body"):
            render_manual_preview()
