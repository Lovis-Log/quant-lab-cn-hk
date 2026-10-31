"""One complete history table with an app-sized, locally updated fullscreen view."""

import streamlit as st


def _toggle_fullscreen():
    st.session_state["history_table_fullscreen"] = not st.session_state.get("history_table_fullscreen", False)


@st.fragment
def render_history_table(table, filename):
    full = st.session_state.get("history_table_fullscreen", False)
    key = "history_table_fullscreen" if full else "history_table_inline"
    with st.container(key=key, height="stretch" if full else "content"):
        title, export, action = st.columns((7, 1.4, 1.4), vertical_alignment="center")
        title.caption(f"历史数据 · {len(table)}条" + (" · Esc 返回" if full else ""))
        export.download_button("导出 CSV", table.to_csv(index=False).encode("utf-8-sig"),
            file_name=filename, mime="text/csv", key="history_csv", on_click="ignore")
        action.button("恢复" if full else "全屏", icon=":material/fullscreen_exit:" if full else ":material/fullscreen:",
                      key="history_fullscreen_close" if full else "history_fullscreen_open", width="stretch", on_click=_toggle_fullscreen)
        st.dataframe(table, width="stretch", hide_index=True, height="stretch" if full else 280, key="history_data_grid")
    st.html('''<script>(() => {
      const root = document.querySelector('.st-key-history_table_fullscreen') || document.querySelector('.st-key-history_table_inline');
      if (!root) return;
      root.querySelectorAll('button').forEach(button => {
        if ((button.getAttribute('aria-label') || '').toLowerCase().includes('fullscreen') ||
            button.getAttribute('title') === 'Fullscreen') button.style.display = 'none';
      });
    })();</script>''', unsafe_allow_javascript=True)
