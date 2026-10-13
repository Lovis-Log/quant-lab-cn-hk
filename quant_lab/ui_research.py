"""Browse saved, data-pinned research runs and export a readable report."""

import streamlit as st
import sqlite3
import zlib

from quant_lab.storage import export_experiment_zip, get_experiment, list_experiments, render_report, replay_experiment
from quant_lab.storage import list_learning_notes, save_learning_note
from quant_lab.market_data import display_security
from quant_lab.ui_knowledge import render_knowledge
from quant_lab.ui_updates import beijing


def render_research_notes() -> None:
    st.subheader("研究笔记与实验档案")
    st.caption("回测页可保存标题、假设、笔记、参数、费用和本次行情快照。这里可导出研究报告。")
    try:
        notes = list_learning_notes()
        with st.expander("学习笔记（私人内容默认不附带给 AI）", expanded=bool(notes)):
            for note in notes[:30]:
                st.markdown(f"**#{note['id']} {note['title']}**")
                st.caption(f"{note['origin']} · 模型：{note['model'] or '无'} · {beijing(note['created_at'])}")
                st.write(note["content"])
            with st.form("manual_learning_note"):
                note_title = st.text_input("学习笔记标题")
                note_content = st.text_area("学习笔记内容")
                if st.form_submit_button("保存手写学习笔记"):
                    save_learning_note(note_title, note_content)
                    st.success("学习笔记已保存；重绘后可查看。")
    except (ValueError, OSError, sqlite3.Error):
        st.error("读取或保存学习笔记失败，请检查用户数据目录。")
    try:
        records = list_experiments()
    except (OSError, sqlite3.Error) as exc:
        st.error(f"读取实验列表失败：{exc}")
        return
    if not records:
        st.info("尚无已保存实验。先在历史回测页运行并保存一次实验。")
        return
    chosen = st.selectbox("选择实验", records,
                          format_func=lambda row: f"#{row['id']} {row['title']} · {display_security(row['market'], row['symbol'], row.get('company_name'))}")
    try:
        record = get_experiment(chosen["id"])
    except (OSError, ValueError, KeyError, sqlite3.Error, zlib.error) as exc:
        st.error(f"读取实验失败：{exc}")
        return
    st.write(record["hypothesis"])
    st.write(display_security(record["market"], record["symbol"], record.get("company_name")))
    st.caption(f"区间 {record['start_date']} 至 {record['end_date']}；来源 {record['source']}；实验指纹 {record['audit_id']}")
    stats = record["metrics"]["strategy"]
    columns = st.columns(3)
    columns[0].metric("累计收益", f"{stats['cumulative_return']:+.2%}")
    columns[1].metric("最大回撤", f"{stats['max_drawdown']:.2%}")
    columns[2].metric("夏普比率", "—" if stats["sharpe"] is None else f"{stats['sharpe']:.2f}")
    if st.session_state.get("learning_mode", True):
        render_knowledge("drawdown", stats["max_drawdown"], key="archive", period="该实验保存的历史区间")
        render_knowledge("sharpe", stats["sharpe"], key="archive", period="该实验保存的历史区间")
    st.markdown("#### 学习笔记")
    st.write(record["notes"] or "（无）")
    st.download_button("导出 Markdown 研究报告", render_report(record).encode("utf-8-sig"),
                       file_name=f"quant_lab_{record['id']}_{record['audit_id']}.md", mime="text/markdown")
    st.download_button("导出可复现研究包 ZIP", export_experiment_zip(record),
                       file_name=f"quant_lab_{record['id']}_{record['audit_id']}.zip", mime="application/zip")
    if st.button("从存档数据重新计算"):
        try:
            replay = replay_experiment(record)
            st.success(f"复算成功：指纹 {replay.audit_id}，策略累计收益 {replay.full_stats.cumulative_return:+.2%}。")
        except ValueError as exc:
            st.error(f"复算失败：{exc}")
    return record
