"""Optional model-assisted hypothesis drafting and auditable local experiments."""

from dataclasses import asdict
import json

import pandas as pd
import streamlit as st

from quant_lab.ai_research import (
    AIUnavailableError, audit_snapshot, draft_hypothesis, draft_report,
)
from quant_lab.backtest import illustrative_config
from quant_lab.data import DataUnavailableError, HistoryBundle, fetch_history_cached as fetch_history
from quant_lab.processing import DataValidationError
from quant_lab.research import run_experiment
from quant_lab.strategy import STRATEGY_NAMES, StrategySpec
from quant_lab.ui_helpers import bundle_key, require_history
from quant_lab import names
from quant_lab.security import redact
from quant_lab.deepseek import DeepSeekClient, AIRequestError
from quant_lab.ai_context import bundle_context


def _raw_history(bundle: HistoryBundle) -> pd.DataFrame:
    if bundle.adjustment == "":
        return bundle.frame
    return fetch_history(
        bundle.market, bundle.symbol,
        bundle.frame["date"].iloc[0].date(),
        bundle.frame["date"].iloc[-1].date(), "",
    ).frame


def render_ai(bundle: HistoryBundle | None) -> None:
    st.subheader("DeepSeek 量化研究助手")
    st.caption("模型只草拟可检验假设与文字报告；所有计算在本地内置函数中执行，模型生成的代码永不自动运行。")
    if not require_history(bundle):
        return
    data_key = bundle_key(bundle)
    st.caption(names.security_label(bundle.market, bundle.symbol, bundle.company_name))
    api_key = st.session_state.get("deepseek_api_key", "")
    model = st.session_state.get("ds_model_select") if st.session_state.get("deepseek_models") else st.session_state.get("ds_model_manual", st.session_state.get("deepseek_model", ""))
    metadata = next((m for m in st.session_state.get("deepseek_models", []) if m["id"] == model), {})
    configured = bool(api_key and model)
    st.caption(f"共用侧栏 DeepSeek 连接 · 当前模型：{model or '尚未选择'}。生成假设和审阅按钮会发送付费请求；本地实验免费。")
    if not configured:
        st.info("请在左侧“DeepSeek AI 助手”配置密钥并选择模型。已接入的连接会直接共用；也可先运行本地受控实验。")
    question = st.text_area(
        "研究问题", value="双均线过滤能否改善这只股票的历史回撤？",
        max_chars=600, height=95,
    )
    if st.button("生成 AI 假设", disabled=not configured):
        try:
            client = DeepSeekClient(api_key)
            hypothesis = draft_hypothesis(question, bundle.market, bundle.symbol, client,
                model=model, metadata=metadata, context=bundle_context("AI 研究助手", bundle))
            st.session_state["ai_hypothesis_key"] = data_key
            st.session_state["ai_hypothesis"] = hypothesis
            st.session_state["ai_error"] = None
            st.session_state["ai_hypothesis_model"] = client.model_used
        except (AIUnavailableError, AIRequestError, ValueError) as exc:
            st.session_state["ai_hypothesis_key"] = data_key
            st.session_state["ai_hypothesis"] = None
            st.session_state["ai_error"] = str(exc)
    if st.session_state.get("ai_hypothesis_key") == data_key and st.session_state.get("ai_error"):
        st.error(st.session_state["ai_error"])
    hypothesis = (
        st.session_state.get("ai_hypothesis")
        if st.session_state.get("ai_hypothesis_key") == data_key else None
    )
    spec = hypothesis.strategy if hypothesis is not None else StrategySpec()
    if hypothesis is not None:
        st.caption("假设实际模型：" + st.session_state.get("ai_hypothesis_model", "未记录"))
        st.markdown(f"#### {hypothesis.title}")
        st.write(hypothesis.rationale)
        st.caption(f"通过本地验证的内置策略：{STRATEGY_NAMES[spec.kind]}，短周期 {spec.short_window}，长周期 {spec.long_window}。")
        st.write("假设：", "；".join(hypothesis.assumptions))
        st.write("统计陷阱：", "；".join(hypothesis.statistical_risks))
        with st.expander("AI 草拟的示例代码（只展示，不执行）"):
            st.code(hypothesis.example_code, language="python")
    else:
        st.caption(f"无 AI 假设时使用固定模板：{STRATEGY_NAMES[spec.kind]} {spec.short_window}/{spec.long_window}。")

    experiment_key = (data_key, spec)
    config = illustrative_config(bundle.market)
    if st.button("运行受控实验（内置策略）", type="primary"):
        try:
            with st.spinner("在本地运行并核验实验…"):
                raw = _raw_history(bundle)
                experiment = run_experiment(
                    raw, bundle.frame, spec, config
                )
            st.session_state["ai_experiment_key"] = experiment_key
            st.session_state["ai_experiment"] = experiment
            st.session_state["ai_experiment_error"] = None
            st.session_state["ai_report"] = None
            st.session_state["ai_report_error"] = None
        except (ValueError, DataUnavailableError, DataValidationError) as exc:
            st.session_state["ai_experiment_key"] = experiment_key
            st.session_state["ai_experiment"] = None
            st.session_state["ai_experiment_error"] = str(exc)
    if st.session_state.get("ai_experiment_key") != experiment_key:
        return
    if st.session_state.get("ai_experiment_error"):
        st.error(st.session_state["ai_experiment_error"])
        return
    experiment = st.session_state.get("ai_experiment")
    if experiment is None:
        return
    evidence = audit_snapshot(experiment)
    st.markdown("#### 可独立复核的实验数据")
    st.json(evidence)
    st.caption(f"实验指纹 `{experiment.audit_id}` 由行情、信号、参数和成本假设计算。数值来自本地回测代码，不由 AI 生成。")
    if st.button("让 AI 审阅实验", disabled=not configured):
        try:
            context = bundle_context("AI 研究助手", bundle)
            context.update({"strategy": STRATEGY_NAMES[spec.kind], "audit_id": experiment.audit_id,
                            "costs": asdict(config)})
            client = DeepSeekClient(api_key)
            st.session_state["ai_report"] = draft_report(experiment, context, client, model=model, metadata=metadata)
            st.session_state["ai_report_model"] = client.model_used
            st.session_state["ai_report_error"] = None
        except (AIUnavailableError, AIRequestError) as exc:
            st.session_state["ai_report"] = None
            st.session_state["ai_report_error"] = str(exc)
    if st.session_state.get("ai_report_error"):
        st.error(st.session_state["ai_report_error"])
    report = st.session_state.get("ai_report")
    if report is not None:
        st.caption("审阅实际模型：" + st.session_state.get("ai_report_model", "未记录"))
        st.markdown("#### AI 审阅意见（需要人工核对）")
        st.write(report.summary)
        for heading, items in (
            ("观察", report.observations), ("局限", report.limitations),
            ("下一步检验", report.next_tests),
        ):
            st.markdown(f"**{heading}**")
            for item in items:
                st.write(f"• {item}")
    report_text = (
        f"# Quant Lab CN/HK 研究审计\n\n"
        f"标的：{names.security_label(bundle.market, bundle.symbol, bundle.company_name)}\n\n"
        f"来源：{bundle.source}；价格口径：{bundle.adjustment_label}；币种：{bundle.currency}\n\n"
        f"实际交易日：{bundle.frame['date'].iloc[0]:%Y-%m-%d} 至 "
        f"{bundle.frame['date'].iloc[-1]:%Y-%m-%d}；记录数：{len(bundle.frame)}\n\n"
        f"内置策略：{STRATEGY_NAMES[spec.kind]} {spec.short_window}/{spec.long_window}\n\n"
        f"样本内比例：70%；成交使用不复权价格；信号使用上述选定口径。\n\n"
        f"回测成本与交易单位假设：\n\n```json\n"
        f"{json.dumps(asdict(config), ensure_ascii=False, indent=2)}\n```\n\n"
        f"实验指纹：{experiment.audit_id}\n\n"
        f"## 本地计算证据\n\n```json\n{json.dumps(evidence, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## 局限\n\n日线成交、成本、公司行动、幸存者偏差及参数过拟合会影响解释。"
    )
    if report is not None:
        report_text += f"\n\n## DeepSeek 审阅（未经独立核实）\n\n模型：{st.session_state.get('ai_report_model', '未记录')}\n\n{report.summary}\n"
    st.download_button(
        "下载可复核研究报告", redact(report_text, (api_key,)).encode("utf-8-sig"),
        file_name=f"quant_lab_{bundle.symbol}_{experiment.audit_id}.md",
        mime="text/markdown",
    )
