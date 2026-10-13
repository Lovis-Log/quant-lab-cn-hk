"""Risk, multi-asset portfolio, statistics and machine-learning workspaces."""

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab.data import DataUnavailableError, HistoryBundle, fetch_history_cached as fetch_history
from quant_lab.metrics import performance_stats
from quant_lab.portfolio import analyze_portfolio
from quant_lab.processing import DataValidationError
from quant_lab.statistics import evaluate_linear_model, one_sample_return_test
from quant_lab.ui_helpers import bundle_key, percent, require_history, style_figure


def render_risk(bundle: HistoryBundle | None) -> None:
    st.subheader("风险与投资组合")
    st.caption("同一市场、同一币种的历史描述与样本外配置比较；不包含交易费用或汇率转换。")
    if not require_history(bundle):
        return
    history = bundle.frame
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
        with st.expander("知识解释：方差、波动率与回撤"):
            st.write("样本方差是日收益偏离均值的平方和除以 n−1；标准差是方差的平方根。年化波动率近似日标准差乘 √252。最大回撤则衡量从此前净值峰值跌得最深的一次。")

    other = "000001" if bundle.market == "A 股" and bundle.symbol != "000001" else (
        "600519" if bundle.market == "A 股" else "00941" if bundle.symbol != "00941" else "00700"
    )
    code_text = st.text_input(
        "组合股票代码（逗号分隔，2–4 只）", value=f"{bundle.symbol},{other}",
        help="只允许当前市场的股票；A 股六位，港股五位。不会混合 CNY 与 HKD。",
    )
    fraction = st.slider("组合权重训练比例", 0.50, 0.85, 0.70, 0.05)
    codes = [part.strip() for part in code_text.split(",") if part.strip()]
    pattern = r"\d{6}" if bundle.market == "A 股" else r"\d{5}"
    valid = 2 <= len(codes) <= 4 and len(set(codes)) == len(codes) and all(
        re.fullmatch(pattern, code) for code in codes
    )
    if not valid:
        st.warning("请输入 2–4 个不重复的当前市场股票代码。")
        return
    key = (bundle_key(bundle), tuple(codes), fraction)
    if st.button("分析同市场组合"):
        try:
            histories: dict[str, pd.DataFrame] = {}
            first = bundle.frame["date"].iloc[0].date()
            last = bundle.frame["date"].iloc[-1].date()
            with st.spinner("读取组合股票并对齐共同交易日…"):
                for code in codes:
                    histories[code] = (
                        bundle.frame if code == bundle.symbol
                        else fetch_history(bundle.market, code, first, last, bundle.adjustment).frame
                    )
                analysis = analyze_portfolio(histories, fraction)
            st.session_state["portfolio_key"] = key
            st.session_state["portfolio_result"] = analysis
            st.session_state["portfolio_error"] = None
        except (ValueError, DataUnavailableError, DataValidationError) as exc:
            st.session_state["portfolio_key"] = key
            st.session_state["portfolio_result"] = None
            st.session_state["portfolio_error"] = str(exc)
    if st.session_state.get("portfolio_key") != key:
        return
    if st.session_state.get("portfolio_error"):
        st.error(st.session_state["portfolio_error"])
        return
    result = st.session_state.get("portfolio_result")
    if result is None:
        return
    st.caption(f"共同交易日 {len(result.closes)} 天；权重只使用截至 {result.train_last_date:%Y-%m-%d} 的训练收益率。")
    st.markdown("#### 组合权重")
    st.dataframe(result.weights.style.format("{:.1%}"), width="stretch")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("#### 相关系数")
        st.dataframe(result.correlation.round(3), width="stretch")
    with cols[1]:
        st.markdown("#### 日收益率协方差")
        st.dataframe(result.covariance.round(6), width="stretch")
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
    st.caption("单样本 t 检验的零假设是“平均日收益率为 0”。其 p 值依赖样本近似独立等条件；时间序列自相关、厚尾和反复试参数会削弱解释力。p 值不是策略获利概率。")

    fraction = st.slider("机器学习训练比例", 0.55, 0.85, 0.70, 0.05)
    key = (bundle_key(bundle), fraction)
    if st.button("运行时间序列线性回归"):
        try:
            with st.spinner("按日期训练并评估样本外预测…"):
                evaluation = evaluate_linear_model(bundle.frame, fraction)
            st.session_state["model_key"] = key
            st.session_state["model_result"] = evaluation
            st.session_state["model_error"] = None
        except ValueError as exc:
            st.session_state["model_key"] = key
            st.session_state["model_result"] = None
            st.session_state["model_error"] = str(exc)
    if st.session_state.get("model_key") != key:
        return
    if st.session_state.get("model_error"):
        st.error(st.session_state["model_error"])
        return
    result = st.session_state.get("model_result")
    if result is None:
        return
    cols = st.columns(4)
    cols[0].metric("样本外 MAE", f"{result.mae:.4%}")
    cols[1].metric("零收益基线 MAE", f"{result.baseline_mae:.4%}")
    cols[2].metric("样本外 R²", f"{result.r_squared:.3f}")
    cols[3].metric("方向一致率", f"{result.directional_accuracy:.1%}")
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
