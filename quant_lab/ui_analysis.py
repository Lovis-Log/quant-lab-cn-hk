"""Risk, multi-asset portfolio, statistics and machine-learning workspaces."""

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab.data import DataUnavailableError, HistoryBundle, fetch_history_cached as fetch_history
from quant_lab.metrics import performance_stats
from quant_lab.portfolio import analyze_portfolio, collect_portfolio_histories
from quant_lab.ui_jobs import submit_task, take_result, loading_placeholder
from quant_lab.jobs import JobState
from quant_lab.processing import DataValidationError
from quant_lab.statistics import evaluate_linear_model, one_sample_return_test
from quant_lab.ui_helpers import bundle_key, percent, require_history, style_figure
from quant_lab.ui_knowledge import KnowledgePoint, render_knowledge, render_knowledge_group
from quant_lab import names


def render_risk(bundle: HistoryBundle | None) -> None:
    st.subheader("风险与投资组合")
    st.caption("同一市场、同一币种的历史描述与样本外配置比较；不包含交易费用或汇率转换。")
    if not require_history(bundle):
        return
    history = bundle.frame
    st.caption(names.cached_security_label(bundle.market, bundle.symbol, bundle.company_name))
    if len(history) >= 3:
        daily = history["close"].pct_change().dropna()
        price_stats = performance_stats(history["close"])
        cols = st.columns(4)
        cols[0].metric("日收益率样本方差", f"{daily.var(ddof=1):.6f}")
        cols[1].metric("日收益率样本标准差", f"{daily.std(ddof=1):.2%}")
        cols[2].metric("年化波动率估计", percent(price_stats.annualized_volatility))
        cols[3].metric("历史最大回撤", percent(price_stats.max_drawdown))
    st.caption("方差与标准差使用样本口径（分母 n−1）；年化波动率约等于日标准差 × √252。历史波动不保证未来风险。")
    if st.session_state.get("learning_mode", True):
        render_knowledge_group(
            (
                KnowledgePoint("variance", float(daily.var(ddof=1)) if len(history) >= 3 else None),
                KnowledgePoint("std", float(daily.std(ddof=1)) if len(history) >= 3 else None),
                KnowledgePoint("volatility", price_stats.annualized_volatility if len(history) >= 3 else None),
                KnowledgePoint("drawdown", price_stats.max_drawdown if len(history) >= 3 else None),
            ),
            key="risk",
        )

    other = "000001" if bundle.market == "A 股" and bundle.symbol != "000001" else (
        "600519" if bundle.market == "A 股" else "00941" if bundle.symbol != "00941" else "00700"
    )
    with st.form("portfolio_parameters", border=False):
        code_text = st.text_input(
            "组合股票代码（逗号分隔，2–4 只）", value=f"{bundle.symbol},{other}",
            help="只允许当前市场股票，不会混合 CNY 与 HKD。",
            key=f"portfolio_codes_{bundle.market}_{bundle.symbol}",
        )
        fraction = st.slider("组合权重训练比例", 0.50, 0.85, 0.70, 0.05, key="portfolio_fraction")
        requested = st.form_submit_button("分析同市场组合")
    codes = [part.strip() for part in code_text.split(",") if part.strip()]
    pattern = r"\d{6}" if bundle.market == "A 股" else r"\d{5}"
    valid = 2 <= len(codes) <= 4 and len(set(codes)) == len(codes) and all(
        re.fullmatch(pattern, code) for code in codes
    )
    if not valid:
        st.warning("请输入 2–4 个不重复的当前市场股票代码。")
        return
    key = (bundle_key(bundle), tuple(codes), fraction)
    if requested:
        submit_task("portfolio_data", key, collect_portfolio_histories, bundle, codes, fetch_history)
    prepared = take_result("portfolio_data", key)
    if prepared:
        if prepared.state == JobState.SUCCEEDED:
            submit_task("portfolio", key, analyze_portfolio, prepared.result, fraction, cpu=True)
        elif prepared.state == JobState.FAILED:
            st.session_state["portfolio_error"] = prepared.error
    completed = take_result("portfolio", key)
    if completed:
        if completed.state == JobState.SUCCEEDED:
            analysis = completed.result
            st.session_state["portfolio_key"] = key
            st.session_state["portfolio_result"] = analysis
            st.session_state["portfolio_error"] = None
        elif completed.state == JobState.FAILED:
            st.session_state["portfolio_error"] = completed.error
    if st.session_state.get("portfolio_error"):
        st.error(st.session_state["portfolio_error"])
    if "portfolio_data" in st.session_state.get("_task_tickets", {}) or "portfolio" in st.session_state.get("_task_tickets", {}):
        st.caption("组合研究进行中，可继续使用其他工作区。")
        if st.session_state.get("portfolio_result") is None:
            loading_placeholder()
    if st.session_state.get("portfolio_key") != key:
        return
    result = st.session_state.get("portfolio_result")
    if result is None:
        return
    st.caption(f"共同交易日 {len(result.closes)} 天；权重只使用截至 {result.train_last_date:%Y-%m-%d} 的训练收益率。")
    st.markdown("#### 组合权重")
    labels = {code: names.cached_security_label(bundle.market, code) for code in codes}
    st.dataframe(result.weights.rename(index=labels).style.format("{:.1%}"), width="stretch")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("#### 相关系数")
        st.dataframe(result.correlation.rename(index=labels, columns=labels).round(3), width="stretch")
    with cols[1]:
        st.markdown("#### 日收益率协方差")
        st.dataframe(result.covariance.rename(index=labels, columns=labels).round(6), width="stretch")
    if st.session_state.get("learning_mode", True):
        st.caption(f"下面解释 {labels[codes[0]]} 与 {labels[codes[1]]} 的共同交易日样本。")
        render_knowledge_group(
            (
                KnowledgePoint("correlation", float(result.correlation.loc[codes[0], codes[1]])),
                KnowledgePoint("covariance", float(result.covariance.loc[codes[0], codes[1]])),
            ),
            key="portfolio",
        )
    figure = go.Figure()
    for name, color in (("等权", "#4F8CFF"), ("逆波动率", "#24D6A0")):
        figure.add_trace(go.Scatter(
            x=result.test_equity.index, y=result.test_equity[name],
            name=name, line={"color": color, "width": 2},
        ))
    st.plotly_chart(style_figure(figure), width="stretch", theme=None)
    stats_rows = []
    for name in ("等权", "逆波动率"):
        stats = performance_stats(result.test_equity[name])
        stats_rows.append({"样本外方法": name, "累计收益率": stats.cumulative_return,
                           "年化波动率": stats.annualized_volatility,
                           "最大回撤": stats.max_drawdown})
    st.dataframe(pd.DataFrame(stats_rows), width="stretch", hide_index=True)
    st.caption("曲线为每日按固定权重再平衡的数学组合，未计调仓成本；逆波动率权重只由更早的训练区间估计。不同市场与币种不可直接相加。")


def render_statistics(bundle: HistoryBundle | None) -> None:
    st.subheader("统计学与机器学习")
    st.caption("先描述样本，再做假设检验与时间序列预测；这些结果不构成投资建议。")
    with st.expander("这个页面怎么用", expanded=bundle is None):
        st.markdown(
            "1. 左侧选股票，历史区间建议至少一年，再点“加载真实历史日线”。所有统计使用当前价格口径；跨除权时先核对复权影响。\n"
            "2. 先看日收益率样本量、日均收益、年化波动和 p 值。p < 0.05 只表示在检验假设下对零均值的反证较强，不能理解成未来上涨概率。\n"
            "3. 训练比例先保留 70%，点击“运行时间序列线性回归”：较早 70% 用来学习，较晚样本用来检验，中间留一日间隔。至少需要 60 行有效特征，通常要 80 个以上交易日。\n"
            "4. 比较模型 MAE 和零收益基线 MAE：越小越好，模型必须先胜过每天预测 0 的简单方法。再看 R²、方向一致率与两条曲线，别只看命中方向。\n"
            "5. 系数对应标准化后的特征，表示训练期关联。换股票或区间后需要重新运行；反复根据测试结果调参会过拟合。"
        )
        st.caption("输入特征：1 日收益、5 日收益、5/20 日均线比值减 1、成交量变化率、10 日收益波动。预测目标：下一交易日收盘相对当日收盘的收益率。")
    if not require_history(bundle):
        return
    try:
        test = one_sample_return_test(bundle.frame)
    except ValueError as exc:
        st.info(str(exc))
        return
    cols = st.columns(4)
    cols[0].metric("日收益率样本量", str(test.observations))
    cols[1].metric("日均收益率", percent(test.mean_daily))
    cols[2].metric("年化波动率估计", percent(test.annualized_volatility))
    cols[3].metric("均值为零检验 p 值", "—" if test.p_value is None else f"{test.p_value:.3f}")
    st.session_state["active_analysis_context"] = {
        "observations": test.observations, "mean_daily": test.mean_daily,
        "annualized_volatility": test.annualized_volatility, "p_value": test.p_value,
        "test_definition": "单样本 t 检验：平均日收益为 0；非盈利概率"}
    st.caption("单样本 t 检验的零假设是“平均日收益率为 0”。其 p 值依赖样本近似独立等条件；时间序列自相关、厚尾和反复试参数会削弱解释力。p 值不是策略获利概率。")
    if st.session_state.get("learning_mode", True):
        render_knowledge("p_value", test.p_value, key="statistics", observations=test.observations)

    fraction = st.slider("机器学习训练比例", 0.55, 0.85, 0.70, 0.05, key="model_fraction")
    key = (bundle_key(bundle), fraction)
    if st.button("运行时间序列线性回归"):
        submit_task("statistics", key, evaluate_linear_model, bundle.frame, fraction, cpu=True)
    completed = take_result("statistics", key)
    if completed:
        if completed.state == JobState.SUCCEEDED:
            evaluation = completed.result
            st.session_state["model_key"] = key
            st.session_state["model_result"] = evaluation
            st.session_state["model_error"] = None
        elif completed.state == JobState.FAILED:
            st.session_state["model_error"] = completed.error
    if st.session_state.get("model_error"):
        st.error(st.session_state["model_error"])
    if "statistics" in st.session_state.get("_task_tickets", {}):
        st.caption("模型在后台计算，可继续阅读或切换工作区。")
        if st.session_state.get("model_result") is None:
            loading_placeholder()
    if st.session_state.get("model_key") != key:
        return
    result = st.session_state.get("model_result")
    if result is None:
        return
    st.session_state["active_analysis_context"]["linear_model"] = {
        "train_fraction": fraction, "train_rows": result.train_rows, "test_rows": result.test_rows,
        "train_label_end": str(result.train_end.date()), "test_feature_start": str(result.test_start.date()),
        "mae": result.mae, "zero_return_baseline_mae": result.baseline_mae, "r_squared": result.r_squared,
        "directional_accuracy": result.directional_accuracy, "cv_mae": result.cv_mae,
        "features": ["1/5 日收益", "5/20 均线比值-1", "成交量变化", "10 日收益标准差"],
        "target": "下一交易日收盘相对当日收盘的收益率；不是交易收益"}
    cols = st.columns(4)
    cols[0].metric("样本外 MAE", f"{result.mae:.4%}")
    cols[1].metric("零收益基线 MAE", f"{result.baseline_mae:.4%}")
    cols[2].metric("样本外 R²", f"{result.r_squared:.3f}")
    cols[3].metric("方向一致率", f"{result.directional_accuracy:.1%}")
    if result.mae < result.baseline_mae:
        st.info("本次样本外 MAE 小于零收益基线，说明该历史测试区间的平均误差更低；仍需在其他未使用区间复核。")
    else:
        st.warning("本次模型 MAE 未低于零收益基线，预测误差尚未优于每天预测 0。")
    st.caption("例如 MAE 1% 表示预测与实际日收益平均相差 1 个百分点。R² 为负时，模型误差比测试样本均值参考更大；方向一致率不计涨跌幅、费用或可成交性。")
    if st.session_state.get("learning_mode", True):
        render_knowledge_group(
            (
                KnowledgePoint("mae", result.mae, observations=result.test_rows),
                KnowledgePoint("r_squared", result.r_squared, observations=result.test_rows),
            ),
            key="statistics_model",
        )
    st.caption(
        f"训练 {result.train_rows} 行（标签至 {result.train_end:%Y-%m-%d}）；"
        f"测试 {result.test_rows} 行（特征始于 {result.test_start:%Y-%m-%d}）；"
        f"训练期 3 折时间序列交叉验证 MAE {result.cv_mae:.4%}。"
    )
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=result.predictions["target_date"], y=result.predictions["actual"],
        name="实际次日收盘收益率", line={"color": "#4F8CFF"},
    ))
    figure.add_trace(go.Scatter(
        x=result.predictions["target_date"], y=result.predictions["predicted"],
        name="模型预测", line={"color": "#F5B942"},
    ))
    st.plotly_chart(style_figure(figure), width="stretch", theme=None)
    st.dataframe(result.coefficients.to_frame(), width="stretch")
    st.caption("特征仅使用当日收盘后可知的价格和成交量；目标是下一日收盘相对当日收盘的收益率。这个目标不能按当日收盘价成交。标准化只在训练集拟合，并在训练/测试边界留出一日间隔。")
