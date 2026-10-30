"""Real USD comparison and price/cost portfolios, separated from AH state."""

from datetime import datetime

import streamlit as st

from quant_lab.history_ranges import history_window
from quant_lab.paths import user_data_dir
from quant_lab.us_market import NY, normalize_us_symbol
from quant_lab.us_price_research import ASSUMPTIONS, normalize_us_codes, calculate_us_price_comparison, run_us_price_portfolio
from quant_lab.ui_us_price_research import config_controls, task_result, line_chart


def render_us_price_comparison():
    st.caption(ASSUMPTIONS)
    st.session_state["active_comparison_context"] = {"page": "多股票比较", "market": "美股", "currency": "USD",
                                                     "data_status": "尚未加载美股比较输入"}
    today = datetime.now(NY).date()
    first, last = history_window(today, 1)
    with st.form("us_price_comparison"):
        text = st.text_input("美股比较代码（逗号分隔，2–10只）", value="AAPL,MSFT", key="us_compare_codes")
        cols = st.columns(2)
        start = cols[0].date_input("美股比较开始日期", value=first, key="us_compare_start", max_value=today)
        end = cols[1].date_input("美股比较结束日期", value=last, key="us_compare_end", max_value=today)
        cols = st.columns(2)
        baseline = cols[0].text_input("美股基准代码（留空使用首只）", key="us_compare_baseline")
        window = cols[1].number_input("美股滚动波动窗口", min_value=2, max_value=252, value=20, key="us_compare_window")
        cols = st.columns(2)
        load = cols[0].form_submit_button("加载美股比较", type="primary")
        force = cols[1].form_submit_button("立即更新美股比较")
    try:
        codes = normalize_us_codes([v.strip() for v in text.replace("，", ",").split(",") if v.strip()])
        benchmark = normalize_us_symbol(baseline) if baseline.strip() else codes[0]
        if benchmark not in codes or start > end:
            raise ValueError("基准须属于比较列表，开始日期不能晚于结束日期。")
    except ValueError as error:
        st.warning(str(error)); return
    key = (str(user_data_dir()), codes, start, end, benchmark, int(window))
    saved, failed = task_result("us_price_comparison", key, load or force, calculate_us_price_comparison,
                                codes, start, end, benchmark, int(window), force, key[0], cpu=False, timeout=300)
    if saved is None:
        st.info("显式加载后比较真实美股日线；同查询合并，立即更新绕过缓存，失败不会换成教学数据。")
        return
    inputs, result = saved
    st.caption(f"USD · 共同范围 {result.closes.index[0]:%Y-%m-%d} 至 {result.closes.index[-1]:%Y-%m-%d} · {len(result.closes)}条 · 基准 {benchmark} · 来源声明未复权")
    if any((item.frame.close.pct_change(fill_method=None).abs() >= .4).any() for item in inputs.bundles.values()):
        st.warning("存在至少40%的原始价格跳变，价格收益/相关性可能受公司行动影响；现金组合需缩短区间。")
    selected = st.radio("美股比较图表", ("标准化价格", "回撤", "滚动波动率"), horizontal=True, key="us_compare_chart")
    values = {"标准化价格": result.normalized, "回撤": result.drawdowns, "滚动波动率": result.rolling_volatility}[selected]
    line_chart({code: (values.index, values[code]) for code in codes}, (inputs.fingerprint, selected))
    st.dataframe(result.risk_return.rename(columns={"price_return": "价格收益", "relative_to_benchmark": "相对基准收益",
                 "annualized_volatility": "年化波动估计", "max_drawdown": "最大回撤", "observations": "共同记录数"}), width="stretch")
    with st.expander("相关性、覆盖和完整单股数据", expanded=True):
        st.dataframe(result.correlation, width="stretch")
        st.caption("相关系数使用共同观测间隔的价格收益；年化按252近似，零波动相关性留空。共同缺口不填价格。")
        st.dataframe(result.coverage, width="stretch", hide_index=True)
        if st.session_state.get("us_compare_detail") not in codes:
            st.session_state["us_compare_detail"] = codes[0]
        code = st.selectbox("查看美股完整日线", codes, key="us_compare_detail")
        st.dataframe(inputs.bundles[code].frame, width="stretch", hide_index=True)
    with st.expander("美元现金持仓组合", expanded=False):
        with st.form("us_price_portfolio"):
            config = config_controls("us_price_port")
            fraction = st.slider("组合权重训练比例", .5, .85, .7, .05, key="us_price_port_fraction")
            frequency = st.selectbox("调仓频率", ("monthly", "daily"),
                format_func=lambda value: "月末收盘决策，次日开盘执行" if value == "monthly" else "每个收盘决策，次日开盘执行",
                key="us_price_port_frequency")
            requested = st.form_submit_button("运行真实美元价格组合")
        outcome, portfolio_failed = task_result("us_price_portfolio", (inputs.fingerprint, config, fraction, frequency),
            requested, run_us_price_portfolio, inputs, config, fraction, frequency, timeout=300)
        if outcome is not None:
            st.caption(f"权重训练截止 {outcome.train_last_date:%Y-%m-%d}；样本外交易起点 {outcome.test_first_date:%Y-%m-%d}。卖出现金按成交记账，非结算现金模拟。")
            st.dataframe(outcome.weights, width="stretch")
            if outcome.inverse_error:
                st.warning("逆波动率未运行："+outcome.inverse_error)
            line_chart({name: (run.equity.date, run.equity.equity) for name, run in outcome.runs.items()},
                       (inputs.fingerprint, config, fraction, frequency))
            for name, run in outcome.runs.items():
                st.markdown("**"+name+"**")
                st.write({"价格与成本收益": run.stats.cumulative_return, "最大回撤": run.stats.max_drawdown,
                          "最终权益（USD）": run.stats.ending_equity, "指纹": run.audit_id})
                st.dataframe(run.equity, width="stretch", hide_index=True)
                st.dataframe(run.positions, width="stretch", hide_index=True)
                st.dataframe(run.orders, width="stretch", hide_index=True)
    st.caption("与A/H同为价格研究，不计公司行动或股息；完整行情档案的留存条件仍沿用现有规则。")
    st.session_state["active_comparison_context"] = {"page": "多股票比较", "market": "美股", "currency": "USD",
        "symbol": ",".join(codes), "data_fingerprint": inputs.fingerprint,
        "data_period": [str(result.closes.index[0].date()), str(result.closes.index[-1].date())],
        "data_status": ("本次更新失败，显示上次结果；" if failed else "")+"真实美股共同区间价格研究；非实时；公司行动未模拟"}
