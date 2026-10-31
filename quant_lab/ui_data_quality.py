"""Compact, explicit data provenance without rerunning calendar computations."""

import json

import streamlit as st


def render_quality_summary(bundle):
    if bundle is None:
        return
    report = getattr(bundle, "quality", None)
    if report is None:
        return
    actual = f"{report.actual_start} 至 {report.actual_end}" if report.actual_start else "没有返回记录"
    st.caption(f"请求：{report.requested_start} 至 {report.requested_end} · 实际：{actual} · {report.observations} 条")
    if report.unfinished_sessions:
        st.warning("含尚未收市的日线；请使用已结束交易日进行回测。")


def render_history_quality(bundle):
    if bundle is None:
        return
    report = getattr(bundle, "quality", None)
    if report is None:
        with st.expander("数据质量与覆盖"):
            st.caption("此旧数据包未记录质量报告，可明确更新后生成；不改写旧实验或推断其完整性。")
        return
    actual = f"{report.actual_start} 至 {report.actual_end}" if report.actual_start else "没有返回记录"
    with st.expander("数据质量与覆盖"):
        st.write(report.coverage_label)
        st.caption(bundle.retention.note)
        if bundle.snapshot_id:
            st.caption(f"快照版本：{bundle.snapshot_id[:16]} · 获取批次：{bundle.batch_id or '旧数据未记录'}")
        if bundle.segments:
            st.caption(f"本次分 {len(bundle.segments)} 段获取原始价格，重叠记录已核对；没有拼接复权历史。")
        if bundle.persistence_note:
            st.warning(bundle.persistence_note)
        st.table([
            {"项目": "市场 / 规范代码", "内容": f"{bundle.market} / {bundle.symbol}"},
            {"项目": "请求区间", "内容": f"{report.requested_start} 至 {report.requested_end}"},
            {"项目": "实际返回", "内容": actual},
            {"项目": "来源 / 币种 / 请求复权", "内容": f"{report.source} / {report.currency} / {report.adjustment or '不复权'}"},
            {"项目": "参考日历", "内容": f"{report.calendar_name or '未核验'} / {report.calendar_version or '版本未记录'}"},
            {"项目": "日历范围内已结束日期数", "内容": str(report.expected_completed_sessions) if report.expected_completed_sessions is not None else "无法核验"},
            {"项目": "缺少参考日期记录数", "内容": str(len(report.missing_sessions)) if report.calendar_available else "无法核验"},
            {"项目": "与日历不一致日期数", "内容": str(len(report.off_calendar_sessions)) if report.calendar_available else "无法核验"},
            {"项目": "零成交量 / 大幅变动日期数", "内容": f"{len(report.zero_volume_sessions)} / {len(report.large_move_sessions)}"},
        ])
        st.caption(report.calendar_note)
        for error in report.errors:
            st.error(error)
        for note in report.notes:
            st.caption(note)
        for label, dates in (("缺少的参考日期（原因未核验）", report.missing_sessions),
                             ("日历不一致日期", report.off_calendar_sessions),
                             ("尚未收市日期", report.unfinished_sessions),
                             ("零成交量日期", report.zero_volume_sessions), ("大幅变化日期", report.large_move_sessions)):
            if dates:
                st.write(f"{label}：" + "、".join(str(day) for day in dates[:20]) + (" ……" if len(dates)>20 else ""))
        payload = {**report.to_dict(), "market": bundle.market, "symbol": bundle.symbol,
            "company_name": bundle.company_name,
            "received_at": bundle.received_at.isoformat() if bundle.received_at else None,
            "batch_id": bundle.batch_id, "snapshot_id": bundle.snapshot_id,
            "retention": bundle.retention.to_dict(), "segments": bundle.segments}
        st.download_button("导出质量报告", json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8-sig"),
            file_name=f"{bundle.market}_{bundle.symbol}_quality.json", mime="application/json", key="download_history_quality")
