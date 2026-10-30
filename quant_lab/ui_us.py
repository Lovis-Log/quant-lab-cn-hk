"""US daily references and separate teaching research with execution gates."""

from dataclasses import asdict
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab.jobs import JobState
from quant_lab.strategy import StrategySpec,STRATEGY_NAMES
from quant_lab.ui_helpers import style_figure
from quant_lab.ui_jobs import submit_task,take_result,loading_placeholder
from quant_lab.us_market import NY,session_information
from quant_lab.us_teaching import teaching_us_inputs
from quant_lab.us_backtest import USExecutionConfig,run_us_portfolio
from quant_lab.us_research import calculate_us_example
from quant_lab.us_archive import export_us_run


def render_us_source_status():
    _render_us_teaching(source_only=True)


def render_us_research():
    mode=st.radio("美股研究模式",("真实行情价格研究","离线教学样本"),horizontal=True,key="us_research_mode")
    if mode == "真实行情价格研究":
        from quant_lab.ui_us_price_research import render_us_price_research
        render_us_price_research()
    else:
        _render_us_teaching()


def _render_us_teaching(source_only=False):
    st.subheader("美股历史日线" if source_only else "美元教学研究")
    if not source_only:
        st.caption("USD现金账户 · 正常交易时段下一开盘 · 只做多、无杠杆、整数股")
    st.session_state["active_us_context"]={"page":"美股研究","currency":"USD","data_status":"离线教学；真实来源尚未通过回测关卡"}
    source="免费来源状态" if source_only else st.radio("研究输入",("离线教学样本","免费来源状态"),horizontal=True,key="us_source_mode")
    if source=="免费来源状态":
        from quant_lab.ui_us_prices import render_us_prices
        render_us_prices()
        if source_only:
            from quant_lab.ui_comparison import _open_us_teaching
            st.button("进入美元教学研究", key="us_source_teaching", icon=":material/school:", on_click=_open_us_teaching)
        return
    datasets,settlement=teaching_us_inputs()
    st.info("以下为平台生成的固定教学样本，非真实美股行情。它用来核对拆股、分红应收/支付和结算现金。")
    st.caption("固定区间2024-05-20至2024-07-12，包含T+2转T+1、休市、2拆1及现金分红；结算日历是明确的教学假设。")
    with st.expander("现金账户与公司行动假设"):
        st.write("成交使用上一交易日收盘后的目标权重，最早在下一正常交易日开盘执行；卖出款在结算前不能用于买入。")
        st.write("普通股票规则版本：2017-09-05起T+2，2024-05-28起T+1；更早的已覆盖区间采用T+3。交易日与结算日历分别输入。")
        st.write("除息日记应收股息；只有支付时刻核验后才变成可用现金。如果来源只验证了支付日期，保守地等该日结束后才可用。")
        st.write("均线只在发生拆股的当日调整已观察到的历史前缀，不使用未来复权因子；分红不从价格均线中扣除。只显示税前模型，未包含税务或ADR费用。")
    with st.expander("美国交易日与时区参考"):
        day=st.date_input("查询美国交易日",value=datetime.now(NY).date(),key="us_calendar_day")
        info=session_information(day)
        if info["is_session"]:
            st.write(f"纽约开盘：{info['open_new_york']}；收盘：{info['close_new_york']}")
            st.caption(f"UTC：{info['open_utc']} 至 {info['close_utc']}；"+("提前收市" if info["early_close"] else "正常收市"))
        else:
            st.write("参考日历为休市日。")
        st.caption("NYSE/Nasdaq正常时段参考日历；实际结算日期须由独立结算日历核验，不能直接拿交易日代替。")
    with st.form("us_teaching_parameters"):
        symbol=st.selectbox("教学证券",tuple(datasets),key="us_teaching_symbol")
        columns=st.columns(3)
        kind=columns[0].selectbox("美股教学策略",tuple(STRATEGY_NAMES),format_func=lambda s:STRATEGY_NAMES[s],key="us_kind")
        short=columns[1].number_input("美股短周期",min_value=2,max_value=249,value=5,key="us_short")
        long=columns[2].number_input("美股长周期",min_value=3,max_value=250,value=10,key="us_long")
        columns=st.columns(3)
        cash=columns[0].number_input("初始资金（USD）",min_value=100.,value=10000.,key="us_cash")
        commission=columns[1].number_input("佣金（基点，研究假设）",min_value=0.,value=0.,key="us_commission")
        minimum=columns[2].number_input("最低佣金（USD）",min_value=0.,value=0.,key="us_minimum")
        columns=st.columns(2)
        slippage=columns[0].number_input("美股单边滑点（基点）",min_value=0.,max_value=9999.,value=2.,key="us_slippage")
        frequency=columns[1].selectbox("美元组合调仓",("monthly","daily"),format_func=lambda f:"每月首个交易日收盘决策" if f=="monthly" else "每日收盘决策",key="us_rebalance")
        requested=st.form_submit_button("运行美元教学研究",type="primary")
    try:
        spec=StrategySpec(kind,int(short),int(long))
        config=USExecutionConfig(initial_cash=cash,commission_bps=commission,minimum_commission=minimum,slippage_bps=slippage)
    except ValueError as error:
        st.warning(str(error))
        return
    key=(symbol,spec,config,frequency)
    if requested:
        submit_task("us_research",key,calculate_us_example,symbol,spec,config,frequency,cpu=True)
    completed=take_result("us_research",key)
    if completed and completed.state==JobState.SUCCEEDED:
        st.session_state["us_research_result"]=(key,completed.result)
        st.session_state.pop("us_research_error",None)
    elif completed and completed.state==JobState.FAILED:
        st.session_state["us_research_error"]=(key,completed.error)
    error=st.session_state.get("us_research_error")
    if error and error[0]==key:
        st.error(error[1])
    saved=st.session_state.get("us_research_result")
    if "us_research" in st.session_state.get("_task_tickets",{}):
        st.caption("美元教学研究正在计算，可继续切页或取消。")
        if not saved or saved[0]!=key:
            loading_placeholder(160)
    if not saved or saved[0]!=key:
        st.caption("提交参数后运行固定教学数据；参数修改不会自动启动计算。")
        return
    experiment,portfolio,report=saved[1]
    columns=st.columns(3)
    columns[0].metric("教学策略累计收益",f"{experiment.stats['strategy'].cumulative_return:.2%}")
    columns[1].metric("含分红基准",f"{experiment.stats['benchmark_total'].cumulative_return:.2%}")
    columns[2].metric("价格收益基准",f"{experiment.stats['benchmark_price'].cumulative_return:.2%}")
    st.caption("同成本基准；策略与基准均只花已结算现金。含分红基准按支付后的可用现金再投，价格基准排除现金股息。费用为可修改的示例，不代表券商收费或税率。")
    figure=go.Figure()
    for result,label in ((experiment.strategy,"教学策略"),(experiment.benchmark,"含分红基准"),(portfolio,"两证券美元组合")):
        figure.add_trace(go.Scatter(x=result.equity.date,y=result.equity.equity/float(config.initial_cash),name=label))
    st.plotly_chart(style_figure(figure),width="stretch",theme=None)
    with st.expander("核对美元现金、持仓与公司行动",expanded=True):
        names={"date":"交易日","equity":"总权益（USD）","settled_cash":"已结算现金（USD）",
            "unsettled_sale_cash":"待结算卖出款（USD）","dividend_receivable":"应收股息（USD）","holdings_value":"持仓市值（USD）",
            "symbol":"教学代码","shares":"股数","close":"原始收盘价（USD）","kind":"流水类型","amount_usd":"金额（USD）",
            "share_delta":"持股变化","event_id":"事件编号","available_at":"可用时刻","decision_date":"收盘决策日",
            "side":"方向","requested_shares":"目标变动股数","price":"成交价（USD）","fees":"费用（USD）","status":"成交状态",
            "reason":"未完全成交原因","settlement_date":"结算日","rule_version":"规则版本"}
        st.dataframe(portfolio.equity.rename(columns=names),width="stretch",hide_index=True)
        st.dataframe(portfolio.positions.rename(columns=names),width="stretch",hide_index=True)
        st.dataframe(portfolio.cash_ledger.rename(columns=names),width="stretch",hide_index=True)
        st.caption("应收确认、结算转入和买卖现金分别列示；不能直接把不同类型的金额相加当成新增收益。拆股只改变股数，金额为零。")
        st.dataframe(portfolio.orders.rename(columns=names),width="stretch",hide_index=True)
    st.caption("首版不处理税务、ADR、碎股现金替代、并购、分拆或特殊分派；跨不支持或未核验事件会拒绝计算。股息只有已验证支付时刻之后才可花。")
    st.download_button("导出可复算美元教学实验",report,file_name="quantlab_us_teaching_run.json",mime="application/json",key="us_export_run")
    st.session_state["active_us_context"].update({"data_fingerprint":experiment.strategy.audit_id,
        "performance":asdict(experiment.stats["strategy"]),"assumptions":"固定教学、USD现金账户、整数股、无杠杆"})
