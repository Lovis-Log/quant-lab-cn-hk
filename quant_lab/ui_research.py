"""Browse saved, data-pinned research runs and export a readable report."""

import streamlit as st
import sqlite3
import zlib

from quant_lab.storage import export_experiment_zip, get_experiment, list_experiments, render_report, replay_experiment


def render_research_notes() -> None:
    st.subheader("研究笔记与实验档案")
    st.caption("回测页可保存标题、假设、笔记、参数、费用和本次行情快照。这里可导出研究报告。")
    try:
        records = list_experiments()
    except (OSError, sqlite3.Error) as exc:
        st.error(f"读取实验列表失败：{exc}")
        return
    if not records:
        st.info("尚无已保存实验。先在历史回测页运行并保存一次实验。")
        return
    chosen = st.selectbox("选择实验", records,
                          format_func=lambda row: f"#{row['id']} {row['title']} · {row['market']} {row['symbol']}")
    try:
        record = get_experiment(chosen["id"])
    except (OSError, ValueError, KeyError, sqlite3.Error, zlib.error) as exc:
        st.error(f"读取实验失败：{exc}")
        return
    st.write(record["hypothesis"])
    st.caption(f"区间 {record['start_date']} 至 {record['end_date']}；来源 {record['source']}；实验指纹 {record['audit_id']}")
    stats = record["metrics"]["strategy"]
    columns = st.columns(3)
    columns[0].metric("累计收益", f"{stats['cumulative_return']:+.2%}")
    columns[1].metric("最大回撤", f"{stats['max_drawdown']:.2%}")
    columns[2].metric("夏普比率", "—" if stats["sharpe"] is None else f"{stats['sharpe']:.2f}")
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
