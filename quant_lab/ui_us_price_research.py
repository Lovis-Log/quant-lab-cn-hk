"""Real US price/cost workspaces, at the declared AH research fidelity."""

from dataclasses import asdict
import json

import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from quant_lab import names

from quant_lab.jobs import JobState
from quant_lab.metrics import performance_stats
from quant_lab.research_diagnostics import backtest_diagnostics
from quant_lab.research_validation import ValidationRecipe
from quant_lab.statistics import one_sample_return_test, evaluate_linear_model
from quant_lab.strategy import StrategySpec, STRATEGY_NAMES, build_signals
from quant_lab.ui_helpers import style_figure
from quant_lab.ui_jobs import submit_task, take_result, loading_placeholder
from quant_lab.us_price_research import (
    ASSUMPTIONS, PRICE_VERSION, USPriceConfig, validate_price_input,
    run_us_price_experiment, run_us_price_validation, price_report,
)


def open_us_market():
    st.session_state["nav_section"] = "市场数据"


def open_us_price_research():
    st.session_state["nav_section"] = "研究工作台"
    st.session_state["us_research_mode"] = "真实行情价格研究"


def config_controls(prefix):
    cols = st.columns(3)
    cash = cols[0].number_input("初始资金（USD）", min_value=100., max_value=1e10, value=10000., key=prefix+"_cash")
    commission = cols[1].number_input("佣金（基点）", min_value=0., max_value=1000., value=0., key=prefix+"_commission")
    minimum = cols[2].number_input("最低佣金（USD）", min_value=0., max_value=1e6, value=0., key=prefix+"_minimum")
    cols = st.columns(2)
    slip = cols[0].number_input("单边滑点（基点）", min_value=0., max_value=999., value=2., key=prefix+"_slip")
    sell = cols[1].number_input("卖出附加费（基点，研究假设）", min_value=0., max_value=1000., value=0., key=prefix+"_sellfee")
    return USPriceConfig(initial_cash=cash, commission_bps=commission, min_commission=minimum,
                         slippage_bps=slip, sell_tax_bps=sell)


def strategy_controls(prefix):
    cols = st.columns(3)
    kind = cols[0].selectbox("策略", tuple(STRATEGY_NAMES), format_func=STRATEGY_NAMES.get, key=prefix+"_kind")
    short = cols[1].number_input("短周期", min_value=2, max_value=249, value=10, key=prefix+"_short")
    long = cols[2].number_input("长周期", min_value=3, max_value=250, value=30, key=prefix+"_long")
    return kind, int(short), int(long)


def task_result(slot, key, requested, function, *args, cpu=True, timeout=120):
    """Only consume results for the current immutable query/parameters."""
    if requested:
        submit_task(slot, key, function, *args, cpu=cpu, job_timeout=timeout)
    completed = take_result(slot, key)
    if completed and completed.state == JobState.SUCCEEDED:
        st.session_state[slot+"_result"] = (key, completed.result)
        st.session_state.pop(slot+"_error", None)
    elif completed and completed.state == JobState.FAILED:
        st.session_state[slot+"_error"] = (key, completed.error)
    error = st.session_state.get(slot+"_error")
    failed = bool(error and error[0] == key)
    if failed:
        st.error(error[1]+"；已有结果仍对应上次成功计算。")
    saved = st.session_state.get(slot+"_result")
    result = saved[1] if saved and saved[0] == key else None
    if slot in st.session_state.get("_task_tickets", {}):
        st.caption("后台研究进行中，可切页或取消；参数修改后旧任务不会覆盖新查询。")
        if result is None:
            loading_placeholder(180)
    return result, failed


def line_chart(series, key, *, height=340):
    figure = go.Figure()
    for label, (dates, values) in series.items():
        figure.add_trace(go.Scatter(x=dates, y=values, name=label))
    figure = style_figure(figure, height)
    figure.update_layout(uirevision=repr(key))
    st.plotly_chart(figure, width="stretch", theme=None)


def render_us_price_research(section=None):
    st.subheader("美股价格研究")
    st.caption(ASSUMPTIONS)
    st.session_state["active_us_context"] = {"page": "美股价格研究", "market": "美股", "currency": "USD",
                                             "data_status": "尚未加载真实美股日线"}
    source_error = st.session_state.get("us_price_error")
    if source_error and source_error[0] == st.session_state.get("_us_price_query"):
        st.error("当前查询最近一次更新失败，请先更新行情："+source_error[1])
        st.session_state["active_us_context"]["data_status"] = "当前查询最近更新失败；未运行新研究"
        return
    saved = st.session_state.get("us_price_reference")
    if not saved or saved[0] != st.session_state.get("_us_price_query"):
        st.info("请在左侧选择股票与日期，点击“加载真实历史日线”。")
        return
    query, reference = saved
    info = reference.observation
    st.write(f"当前已加载：{names.cached_security_label('美股', info.symbol)} · USD · {info.actual_start} 至 {info.actual_end} · {info.observations}条")
    st.caption(f"{info.source} · {reference.price_basis} · 成功接收 {info.received_at}")
    st.session_state["active_us_context"].update({"symbol": info.symbol, "source": info.source,
        "company_name": names.cached_security_name("美股", info.symbol),
        "data_period": [info.actual_start, info.actual_end], "received_at": info.received_at,
        "data_fingerprint": info.content_sha256, "adjustment": reference.price_basis,
        "data_status": "真实美股历史日线；价格与成本研究；公司行动和结算未模拟"})
    try:
        raw = validate_price_input(reference, execution=False)
    except ValueError as error:
        st.error(str(error))
        st.session_state["active_us_context"]["data_status"] = "当前美股日线不可用于新研究："+str(error)
        return
    if (raw.close.pct_change(fill_method=None).abs() >= .4).any():
        st.warning("区间有至少40%的原始价格跳变；价格统计可能受公司行动影响，成交回测与验证需缩短区间。")
    if section is None:
        section = st.radio("研究内容", ("策略信号", "历史回测", "风险与组合", "统计分析", "专业验证"),
                           horizontal=True, key="us_price_page")
    fingerprint = (info.symbol, info.content_sha256, info.received_at, PRICE_VERSION)
    if section == "策略信号":
        values = strategy_controls("us_price_signal")
        try:
            spec = StrategySpec(*values)
            signals = build_signals(raw, spec)
        except ValueError as error:
            st.warning(str(error)); return
        line_chart({"收盘（USD）": (signals.date, signals.close), "短均线": (signals.date, signals.ma_short),
                    "长均线": (signals.date, signals.ma_long)}, fingerprint)
        st.dataframe(signals, width="stretch", hide_index=True)
        st.caption("信号只使用当日及更早的原始收盘价；0/1目标最早在下一交易日开盘执行。")
    elif section == "历史回测":
        _backtest(reference, fingerprint)
    elif section == "风险与组合":
        if len(raw) < 2:
            st.info("风险统计至少需要两个有效收盘价，请扩大区间。")
            return
        stats = performance_stats(raw.close)
        cols = st.columns(3)
        cols[0].metric("区间价格收益", f"{stats.cumulative_return:.2%}")
        cols[1].metric("年化波动率估计", "—" if stats.annualized_volatility is None else f"{stats.annualized_volatility:.2%}")
        cols[2].metric("价格最大回撤", f"{stats.max_drawdown:.2%}")
        st.caption("价格统计不包含分红。美元持仓、费用和样本外等权/逆波动率组合在多股票比较中运行。")
        st.button("进入美股比较与组合", key="us_price_go_compare", on_click=_open_comparison)
    elif section == "统计分析":
        _statistics(raw, fingerprint)
    else:
        _validation(reference, fingerprint)


def _open_comparison():
    st.session_state["nav_section"] = "多股票比较"


def _backtest(reference, fingerprint):
    with st.form("us_price_backtest"):
        values = strategy_controls("us_price_bt")
        config = config_controls("us_price_bt")
        fraction = st.slider("训练比例", .5, .85, .7, .05, key="us_price_bt_fraction")
        requested = st.form_submit_button("运行真实美股价格回测", type="primary")
    try:
        spec = StrategySpec(*values)
    except ValueError as error:
        st.warning(str(error)); return
    key = (fingerprint, spec, config, fraction)
    result, failed = task_result("us_price_backtest", key, requested, run_us_price_experiment, reference, spec, config, fraction)
    if result is None:
        return
    cols = st.columns(4)
    cols[0].metric("策略价格收益", f"{result.full_stats.cumulative_return:.2%}")
    cols[1].metric("同成本基准", f"{result.benchmark_stats.cumulative_return:.2%}")
    cols[2].metric("样本外收益", f"{result.test_stats.cumulative_return:.2%}")
    cols[3].metric("策略最大回撤", f"{result.full_stats.max_drawdown:.2%}")
    line_chart({"策略": (result.strategy.equity.date, result.strategy.equity.equity),
                "买入持有价格基准": (result.benchmark.equity.date, result.benchmark.equity.equity)}, key)
    with st.expander("成交、现金、持仓与成本诊断", expanded=True):
        st.dataframe(result.strategy.orders, width="stretch", hide_index=True)
        st.dataframe(result.strategy.equity, width="stretch", hide_index=True)
        diagnostics = backtest_diagnostics(reference.frame, result.strategy, config)
        st.write(diagnostics.summary)
        st.dataframe(diagnostics.costs, width="stretch", hide_index=True)
    st.caption(f"{result.audit_id} · 样本外起点 {result.split_date:%Y-%m-%d}；按原A/H模型连续持仓切分，并非在测试起点重置账户。费用为研究假设。")
    st.download_button("导出美股价格回测摘要", price_report(reference, result, spec, config, fraction,
        company_name=names.cached_security_name("美股", reference.observation.symbol)),
                       file_name="us_price_research_summary.json", mime="application/json", key="us_price_bt_export")
    st.caption("来源留存条件与A/H一致：当前可会话研究、导出摘要；暂不新增含完整行情的实验档案或可复算快照。")
    st.session_state["active_us_context"].update({"data_fingerprint": result.audit_id,
        "strategy": asdict(spec), "costs": asdict(config), "performance": asdict(result.full_stats),
        "data_status": ("本次计算失败，以下为旧结果；" if failed else "")+"真实美股价格与成本回测；公司行动/结算未模拟"})


def _statistics(raw, fingerprint):
    try:
        stats = one_sample_return_test(raw)
    except ValueError as error:
        st.warning(str(error)); return
    cols = st.columns(3)
    cols[0].metric("日收益样本均值", f"{stats.mean_daily:.4%}")
    cols[1].metric("日收益样本标准差", f"{stats.sample_std:.2%}")
    cols[2].metric("均值为零检验p值", "—" if stats.p_value is None else f"{stats.p_value:.4f}")
    st.caption("复用A/H单样本t检验；p值依赖近似独立等假设，不是盈利概率。")
    fraction = st.slider("回归训练比例", .55, .85, .7, .05, key="us_price_ml_fraction")
    requested = st.button("运行美股时间序列回归", key="us_price_ml_run")
    result, failed = task_result("us_price_statistics", (fingerprint, fraction), requested, evaluate_linear_model, raw, fraction)
    if result is not None:
        st.write({"样本外MAE": result.mae, "零收益基线MAE": result.baseline_mae, "样本外R²": result.r_squared,
                  "方向一致率": result.directional_accuracy, "训练期交叉验证MAE": result.cv_mae})
        st.dataframe(result.predictions, width="stretch", hide_index=True)
        st.caption(f"训练标签截止 {result.train_end:%Y-%m-%d}；测试特征起点 {result.test_start:%Y-%m-%d}。预测误差不等于可交易收益。")
    st.session_state["active_us_context"]["statistics"] = asdict(stats)


def _validation(reference, fingerprint):
    with st.form("us_price_validation"):
        values = strategy_controls("us_price_val")
        config = config_controls("us_price_val")
        cols = st.columns(2)
        short_text = cols[0].text_input("扫描短周期", value="5,10", key="us_price_val_shorts")
        long_text = cols[1].text_input("扫描长周期", value="20,30", key="us_price_val_longs")
        cols = st.columns(3)
        train = cols[0].number_input("滚动训练条数", min_value=35, max_value=5000, value=126, key="us_price_val_train")
        test = cols[1].number_input("滚动测试条数", min_value=5, max_value=1000, value=42, key="us_price_val_test")
        folds = cols[2].number_input("最大折数", min_value=1, max_value=8, value=3, key="us_price_val_folds")
        fraction = st.slider("验证训练比例", .5, .85, .7, .05, key="us_price_val_fraction")
        requested = st.form_submit_button("运行美股专业验证")
    try:
        shorts = tuple(int(v.strip()) for v in short_text.replace("，", ",").split(",") if v.strip())
        longs = tuple(int(v.strip()) for v in long_text.replace("，", ",").split(",") if v.strip())
        recipe = ValidationRecipe(StrategySpec(*values), config, shorts, longs, fraction, int(train), int(test), int(folds))
        recipe.validate(len(reference.frame))
    except ValueError as error:
        st.warning(str(error)); return
    result, failed = task_result("us_price_validation", (fingerprint, recipe), requested, run_us_price_validation,
                                 reference, recipe, timeout=300)
    if result is None:
        return
    st.success("美股价格研究验证已完成")
    for title, table in (("训练参数扫描", result.scan), ("连续滚动样本外", result.folds),
                          ("成本压力", result.stress), ("费用拆解", result.diagnostics.costs)):
        with st.expander(title, expanded=title == "训练参数扫描"):
            st.dataframe(table, width="stretch", hide_index=True)
    st.caption(f"{result.audit_id}；测试区间不参与对应折选参，跨折账户连续；成本压力使用固定基础策略。")
    shelf = st.session_state.setdefault("us_price_validation_shelf", {})
    shelf[result.audit_id] = {"audit_id": result.audit_id, "symbol": reference.observation.symbol,
        "company_name": names.cached_security_name("美股", reference.observation.symbol),
        "data_sha256": reference.observation.content_sha256, "period": [reference.observation.actual_start, reference.observation.actual_end],
        "recipe": asdict(recipe), "return": result.base.full_stats.cumulative_return,
        "rolling_return": float(result.rolling.equity.equity.iloc[-1]/config.initial_cash-1)}
    while len(shelf) > 6:
        shelf.pop(next(iter(shelf)))
    with st.expander("比较会话验证（最近6个）"):
        previous = st.session_state.get("us_price_validation_selection", [])
        if any(value not in shelf for value in previous):
            st.session_state["us_price_validation_selection"] = [value for value in previous if value in shelf]
        selected = st.multiselect("选择2–6个美股验证", tuple(shelf), key="us_price_validation_selection")
        if 2 <= len(selected) <= 6:
            records = [shelf[value] for value in selected]
            comparable = len({(v["symbol"], v["data_sha256"], json.dumps(v["recipe"]["costs"], sort_keys=True)) for v in records}) == 1
            st.caption("相同数据与资金/费用假设；仍需核对参数和训练比例差异。" if comparable else "数据、证券或资金/费用不同，不能直接归因比较。")
            st.dataframe(pd.DataFrame(records), width="stretch", hide_index=True)
    st.download_button("导出美股验证摘要", json.dumps({"format": "us-price-validation-summary-v1",
        "company_name": names.cached_security_name("美股", reference.observation.symbol),
        "manifest": result.manifest, "audit_id": result.audit_id, "scan": result.scan.to_json(orient="table"),
        "folds": result.folds.to_json(orient="table"), "stress": result.stress.to_json(orient="table"),
        "raw_prices_included": False, "offline_replay_available": False}, ensure_ascii=False, default=str).encode(),
        file_name="us_price_validation_summary.json", mime="application/json")
    st.session_state["active_us_context"].update({"data_fingerprint": result.audit_id,
        "data_status": ("本次失败、沿用旧结果；" if failed else "")+"真实美股价格研究验证；公司行动未模拟",
        "statistics": {"base_return": result.base.full_stats.cumulative_return, "folds": len(result.folds)}})
