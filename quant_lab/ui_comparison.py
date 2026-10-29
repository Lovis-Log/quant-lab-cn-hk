"""Multi-stock research workstation using full data and scoped background jobs."""

from datetime import datetime
import time
import sqlite3
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab import names,theme
from quant_lab.backtest import BacktestConfig,illustrative_config
from quant_lab.comparison import collect_comparison,compare_inputs,normalize_comparison_codes
from quant_lab.history_ranges import history_window
from quant_lab.jobs import JobState
from quant_lab.portfolio_cash import CashPortfolioConfig,prepare_portfolio_execution,run_portfolio_research
from quant_lab.ui_jobs import submit_task,take_result,cancel_task,loading_placeholder
from quant_lab.ui_helpers import style_figure
from quant_lab.ui_data_quality import render_history_quality
from quant_lab.market_data import normalize_symbol
from quant_lab.navigation import comparison_selection


COLORS=("#78A7DB","#C6A56D","#B4BCC5","#73B798","#D7797E","#A39CC7","#86B9C6","#C99F8D","#A8B783","#B887A0")


def _market_change():
    change_comparison_market(st.session_state["compare_market"])


def change_comparison_market(market):
    previous = st.session_state.get("_comparison_draft_market", st.session_state.get("market_selection", "A 股"))
    drafts = st.session_state.setdefault("_comparison_market_drafts", {})
    keys = ("codes", "benchmark", "lots", "commission", "minimum", "buyfee", "sellfee", "slippage", "limit")
    if previous != market:
        drafts[previous] = {"compare_" + key: st.session_state["compare_" + key]
                            for key in keys if "compare_" + key in st.session_state}
    st.session_state["market_selection"] = market
    st.session_state["compare_market"] = market
    st.session_state["_comparison_draft_market"] = market
    if previous == market:
        return
    values = {"compare_codes": "600519,000001,600036" if market == "A 股" else "00700,00941,00005" if market == "港股" else "",
              "compare_benchmark": "", "compare_lots": {}, "compare_limit": "10%"}
    if market != "美股":
        values.update(_default_costs(market))
    values.update(drafts.get(market, {}))
    st.session_state.update(values)


def _default_costs(market):
    defaults=illustrative_config(market)
    return {"compare_" + key: value for key,value in (("commission",defaults.commission_bps),("minimum",defaults.min_commission),
            ("buyfee",defaults.buy_tax_bps),("sellfee",defaults.sell_tax_bps),("slippage",defaults.slippage_bps))}


def _open_us_teaching():
    st.session_state["nav_section"] = "研究工作台"
    st.session_state["us_source_mode"] = "离线教学样本"


def _chart(frame,labels,view,height=330,percentage=False):
    figure=go.Figure()
    trace=go.Scattergl if len(frame)>1000 else go.Scatter
    for index,code in enumerate(frame.columns):
        figure.add_trace(trace(x=frame.index,y=frame[code],name=code if len(frame.columns)>5 else labels.get(code,code),
            meta=labels.get(code,code),hovertemplate="%{meta}<br>%{x}<br>%{y:.3f}<extra></extra>",
            line={"color":COLORS[index%len(COLORS)],"width":1.8}))
    style_figure(figure,height)
    figure.update_layout(uirevision=repr(view),legend={"orientation":"h","y":1.14,"font":{"size":11}})
    if percentage:figure.update_yaxes(tickformat=".0%")
    return figure


def _cash_workspace(inputs,labels):
    st.markdown("#### 现金持仓组合 · 样本外研究")
    st.caption("与旧简化曲线分别核算。权重用不复权价格收益训练，可与比较口径不同；仅研究价格变化与交易成本，不含分红/送转等公司行动或汇兑，不是总回报。")
    defaults=illustrative_config(inputs.market)
    with st.form("cash_portfolio_parameters",border=False):
        columns=st.columns(3)
        fraction=columns[0].slider("权重训练比例",.5,.85,.7,.05,key="compare_fraction")
        frequency=columns[1].selectbox("组合调仓频率",("monthly","daily"),format_func=lambda v:"月末决策、下一开盘" if v=="monthly" else "每日决策、下一开盘",key="compare_frequency")
        cash=columns[2].number_input("组合初始资金",min_value=100.,value=1000000.,key="compare_cash")
        columns=st.columns(3)
        commission=columns[0].number_input("组合佣金（基点）",min_value=0.,value=defaults.commission_bps,key="compare_commission")
        minimum=columns[1].number_input("组合最低佣金",min_value=0.,value=defaults.min_commission,key="compare_minimum")
        slip=columns[2].number_input("组合单边滑点（基点）",min_value=0.,max_value=9999.,value=defaults.slippage_bps,key="compare_slippage")
        columns=st.columns(3)
        buyfee=columns[0].number_input("组合买入附加费用（基点）",min_value=0.,value=defaults.buy_tax_bps,key="compare_buyfee")
        sellfee=columns[1].number_input("组合卖出附加费用（基点）",min_value=0.,value=defaults.sell_tax_bps,key="compare_sellfee")
        limit_choice=columns[2].selectbox("组合简化涨跌停假设",("10%","5%","20%","30%","不模拟"),key="compare_limit") if inputs.market=="A 股" else "不模拟"
        saved_lots=st.session_state.get("compare_lots",{})
        units=st.data_editor(pd.DataFrame({"代码":inputs.codes,"买入单位（股）":[saved_lots.get(code,100) for code in inputs.codes]}),
            disabled=["代码"],hide_index=True,width="stretch",num_rows="fixed",key="cash_lots_editor_"+inputs.fingerprint[:12])
        st.caption("交易单位、费用、卖出资金可用于再投资及简化涨跌停均为研究假设，请逐股核对；不覆盖板块/券商全部规则，不模拟资金取出结算。")
        requested=st.form_submit_button("运行现金持仓组合",type="primary")
    try:
        lots=[]
        for code,lot in units.itertuples(index=False,name=None):
            if isinstance(lot,bool) or pd.isna(lot) or float(lot)!=int(lot) or int(lot)<1:
                raise ValueError("买入单位须为正整数。")
            lots.append((code,int(lot)))
        execution=BacktestConfig(market=inputs.market,initial_cash=cash,lot_size=100,commission_bps=commission,
            min_commission=minimum,buy_tax_bps=buyfee,sell_tax_bps=sellfee,slippage_bps=slip,
            limit_pct=None if limit_choice=="不模拟" else float(limit_choice[:-1])/100)
        config=CashPortfolioConfig(execution,tuple(lots),frequency)
    except (ValueError,TypeError,OverflowError) as error:
        st.warning(str(error));return
    key=(inputs.fingerprint,config,fraction)
    if requested:
        st.session_state["compare_lots"]=dict(lots)
        cancel_task("cash_portfolio")
        submit_task("cash_inputs",key,prepare_portfolio_execution,inputs,job_timeout=300)
    prepared=take_result("cash_inputs",key)
    if prepared and prepared.state==JobState.SUCCEEDED:
        submit_task("cash_portfolio",key,run_portfolio_research,prepared.result,config,fraction,cpu=True,job_timeout=300)
    elif prepared and prepared.state==JobState.FAILED:st.session_state["cash_portfolio_error"]=(key,prepared.error)
    completed=take_result("cash_portfolio",key)
    if completed and completed.state==JobState.SUCCEEDED:
        st.session_state["cash_portfolio_result"]=(key,completed.result)
        st.session_state.pop("cash_portfolio_error",None)
    elif completed and completed.state==JobState.FAILED:st.session_state["cash_portfolio_error"]=(key,completed.error)
    error=st.session_state.get("cash_portfolio_error")
    if error and error[0]==key:st.error(error[1])
    saved=st.session_state.get("cash_portfolio_result")
    if not saved or saved[0]!=key:
        if any(slot in st.session_state.get("_task_tickets",{}) for slot in ("cash_inputs","cash_portfolio")):
            st.caption("正在准备成交价格或计算组合，可切页和取消。");loading_placeholder(160)
        else:st.caption("训练权重固定后，样本外从现金出发；提交参数开始计算。")
        return
    result=saved[1]
    st.caption(f"训练截至 {result.train_last_date:%Y-%m-%d}；样本外首日 {result.test_first_date:%Y-%m-%d}。等权是同成本基准，测试期不参与权重估计。")
    if result.inverse_error:st.warning("逆波动率不可计算："+result.inverse_error+"；没有静默改用其他权重。")
    st.dataframe(result.weights.rename(index=labels).style.format("{:.2%}"),width="stretch")
    curves=pd.DataFrame({method:run.equity.set_index("date").equity/config.execution.initial_cash for method,run in result.runs.items()})
    st.plotly_chart(_chart(curves,{},key,280),width="stretch",theme=None)
    rows=[]
    for method,run in result.runs.items():
        rows.append({"配置":method,"样本外收益":run.stats.cumulative_return,"最大回撤":run.stats.max_drawdown,
            "费用合计":run.equity.cumulative_fees.iloc[-1],"成交金额合计":run.equity.cumulative_traded_notional.iloc[-1],"期末现金":run.equity.cash.iloc[-1]})
    st.dataframe(pd.DataFrame(rows).style.format({"样本外收益":"{:.2%}","最大回撤":"{:.2%}","费用合计":"{:,.2f}","期末现金":"{:,.2f}"}),width="stretch",hide_index=True)
    with st.expander("核对现金、持仓和成交"):
        method=st.selectbox("核对组合配置",tuple(result.runs),key="cash_inspect_method")
        run=result.runs[method]
        renames={"date":"交易日","symbol":"代码","equity":"总权益","cash":"现金","holdings_value":"持仓市值","cumulative_fees":"累计费用",
            "cumulative_traded_notional":"累计成交金额","shares":"股数","value":"持仓市值","close":"原始收盘价","decision_date":"收盘决策日",
            "side":"方向","requested":"目标变动股数","price":"成交价","fees":"费用","status":"状态","reason":"未完全成交原因","cash_after":"成交后现金"}
        st.dataframe(run.equity.rename(columns=renames),width="stretch",hide_index=True)
        st.dataframe(run.positions.rename(columns=renames),width="stretch",hide_index=True)
        st.dataframe(run.orders.rename(columns=renames),width="stretch",hide_index=True)
        st.caption(f"算法 ah-cash-price-v1 · {inputs.currency} · 本次指纹 {run.audit_id[:16]}。当前来源留存许可限制沿用原有规则，没有自动写入行情档案。")


def render_comparison():
    st.subheader("多股票比较")
    st.caption("同市场、同币种 · 历史日线 · 价格收益比较")
    st.session_state["active_comparison_context"]={"page":"多股票比较","data_status":"尚未加载比较输入"}
    market=st.session_state.get("compare_market","A 股")
    if market == "美股":
        st.session_state["active_comparison_context"] = {"page":"多股票比较", "market":"美股", "currency":"USD",
            "data_status":"真实美股多股票比较尚未开放；来源待核验"}
        st.info("真实美股多股票比较尚未开放：免费来源尚未通过完整关卡。")
        st.button("进入美元教学研究", key="comparison_us_teaching", on_click=_open_us_teaching, icon=":material/school:")
        return
    st.session_state.setdefault("_comparison_draft_market", market)
    st.session_state.setdefault("compare_codes", "600519,000001,600036" if market == "A 股" else "00700,00941,00005")
    from quant_lab.ui_security_picker import render_security_picker
    code_text = render_security_picker(market, "compare_codes", multiple=True, label="比较股票（2–10只，代码 / 名称）")
    currency="CNY" if market=="A 股" else "HKD"
    start_default,end_default=history_window(datetime.now(ZoneInfo("Asia/Shanghai")).date(),1)
    with st.form("comparison_parameters",border=False):
        cols=st.columns(3)
        start=cols[0].date_input("比较开始日期",value=start_default,key="compare_start")
        end=cols[1].date_input("比较结束日期",value=end_default,key="compare_end")
        adjustment=cols[2].selectbox("统一价格口径",("","qfq","hfq"),format_func=lambda v:{"":"不复权","qfq":"前复权","hfq":"后复权"}[v],key="compare_adjustment")
        load_col,refresh_col,_=st.columns((1.2,1.6,6),vertical_alignment="bottom")
        requested=load_col.form_submit_button("加载比较",type="primary",width="stretch")
        force=refresh_col.form_submit_button("立即更新比较",width="stretch")
        with st.expander("高级比较设置"):
            cols=st.columns(2)
            baseline=cols[0].text_input("基准代码（留空使用首只）",key="compare_benchmark")
            window=cols[1].number_input("滚动波动窗口（共同记录数）",min_value=2,max_value=252,value=20,key="compare_window")
    try:
        codes=normalize_comparison_codes(market,[part.strip() for part in code_text.replace("，",",").split(",") if part.strip()])
        benchmark=normalize_symbol(market,baseline) if baseline.strip() else codes[0]
        if benchmark not in codes or start>end:raise ValueError("基准须在比较列表内，且起点不能晚于终点。")
    except (ValueError,TypeError) as error:st.warning(str(error));return
    key=(market,codes,start,end,adjustment,benchmark,int(window))
    if requested or force:
        now=time.monotonic()
        if force and now-st.session_state.get("comparison_manual_at",float('-inf'))<5:
            st.info("立即更新刚发起，请等待5秒；本次没有重复请求。")
        else:
            if force:st.session_state["comparison_manual_at"]=now
            cancel_task("comparison_calc")
            submit_task("comparison_data",key,collect_comparison,market,codes,start,end,adjustment,force=force,job_timeout=300)
    prepared=take_result("comparison_data",key)
    if prepared and prepared.state==JobState.SUCCEEDED:
        st.session_state["comparison_pending"]=(key,prepared.result)
        submit_task("comparison_calc",(key,prepared.result.fingerprint),compare_inputs,prepared.result,benchmark,int(window),cpu=True)
    elif prepared and prepared.state==JobState.FAILED:st.session_state["comparison_error"]=(key,prepared.error)
    pending=st.session_state.get("comparison_pending")
    completed=take_result("comparison_calc",(key,pending[1].fingerprint if pending and pending[0]==key else None))
    if completed and completed.state==JobState.SUCCEEDED:
        st.session_state["comparison_result"]=(key,pending[1],completed.result)
        st.session_state.pop("comparison_error",None)
    elif completed and completed.state==JobState.FAILED:st.session_state["comparison_error"]=(key,completed.error)
    error=st.session_state.get("comparison_error")
    if error and error[0]==key:st.error(error[1])
    saved=st.session_state.get("comparison_result")
    active=any(slot in st.session_state.get("_task_tickets",{}) for slot in ("comparison_data","comparison_calc"))
    if active:st.caption("正在更新比较；已有结果仍对应上次成功获取的数据。可切页或取消。")
    if not saved or saved[0]!=key:
        if active:loading_placeholder(280)
        else:st.info("选择2至10只股票并加载。参数编辑不会联网，美股真实比较仍受阶段五来源关卡限制。")
        return
    _,inputs,result=saved
    labels={code:names.cached_security_label(market,code,inputs.bundles[code].company_name) for code in codes}
    synthetic=any(any(token in item.source.lower() for token in ("模拟","教学","demo","teaching","simulation")) for item in inputs.bundles.values())
    st.caption(f"{'教学样本 · 非真实行情' if synthetic else '历史日线'} · {currency} · 共同范围 {result.closes.index[0]:%Y-%m-%d} 至 {result.closes.index[-1]:%Y-%m-%d} · {len(result.closes)}条共同记录 · 基准 {labels[benchmark]}")
    st.html('<style>.st-key-comparison_graphs [data-testid="stHorizontalBlock"]{flex-wrap:wrap}.st-key-comparison_graphs [data-testid="stColumn"]:first-child{min-width:min(480px,100%);flex:2.8 1 480px}.st-key-comparison_graphs [data-testid="stColumn"]:last-child{min-width:min(230px,100%);flex:1 1 230px}</style>')
    with st.container(key="comparison_graphs"):
        left,right=st.columns((3,1.2))
        with left:
            st.markdown("#### 累计价格收益对比 · 起点100")
            st.plotly_chart(_chart(result.normalized,labels,key),width="stretch",theme=None)
            first,second=st.tabs(("回撤对比","滚动波动"),key="comparison_risk_tab",on_change="rerun")
            with first:
                if first.open:st.plotly_chart(_chart(result.drawdowns,labels,key,220,True),width="stretch",theme=None)
            with second:
                if second.open:st.plotly_chart(_chart(result.rolling_volatility,labels,key,220,True),width="stretch",theme=None)
        with right:
            st.markdown("#### 收益率相关性")
            heat=go.Figure(go.Heatmap(z=result.correlation.to_numpy(),x=codes,y=codes,zmin=-1,zmax=1,
                colorscale=[[0,theme.DOWN],[.5,theme.SURFACE],[1,theme.ACCENT]],showscale=False,
                texttemplate="%{z:.2f}" if len(codes)<=5 else None,hovertemplate="%{x} / %{y}<br>%{z:.3f}<extra></extra>"))
            style_figure(heat,max(300,40*len(codes)+100));heat.update_layout(margin={"l":55,"r":10,"t":10,"b":70})
            heat.update_xaxes(type="category",tickangle=-45,tickfont={"size":10})
            heat.update_yaxes(type="category",tickfont={"size":10})
            st.plotly_chart(heat,width="stretch",theme=None)
            st.caption("基于共同观测间隔的价格收益；零波动时相关性留空，不填成0。")
    st.markdown("#### 风险收益对比 · 共同覆盖区间")
    table=result.risk_return.rename(index=labels,columns={"price_return":"区间价格收益","relative_to_benchmark":"相对基准收益","annualized_volatility":"年化波动估计","max_drawdown":"最大回撤","observations":"共同记录数"})
    st.dataframe(table.style.format({col:"{:.2%}" for col in table.columns if col!="共同记录数"},na_rep="—"),width="stretch")
    st.caption("价格收益不等于含分红总回报；共同缺口可能使相邻观测跨多个交易日，年化按252近似。未满滚动窗口的结果留空。")
    if st.toggle("显示观察列表",value=False,key="comparison_watch_open"):
        from quant_lab.ui_terminal import render_watchlist
        interval=st.session_state.get("refresh_interval_seconds",300)
        @st.fragment(run_every=interval if st.session_state.get("refresh_enabled",True) else None)
        def watch():
            render_watchlist(market,codes[0])
        watch()
    with st.expander("覆盖、来源与单股明细"):
        st.dataframe(result.coverage.rename(columns={"code":"代码","requested_start":"请求起点","requested_end":"请求终点","actual_start":"实际起点","actual_end":"实际终点",
            "returned_rows":"返回条数","common_rows":"共同条数","excluded_rows":"排除条数","source":"来源","received_at":"成功获取时间","quality":"覆盖质量","cached":"缓存"}),width="stretch",hide_index=True)
        code=st.selectbox("查看单股完整请求数据",codes,format_func=lambda s:labels[s],key="comparison_detail_symbol")
        st.dataframe(inputs.bundles[code].frame,width="stretch",height=220,hide_index=True)
        render_history_quality(inputs.bundles[code])
    with st.expander("进入现金持仓组合研究"):
        _cash_workspace(inputs,labels)
    st.session_state["active_comparison_context"]={"page":"多股票比较","data_fingerprint":inputs.fingerprint,
        "market":market,"currency":currency,"symbols":list(codes),"benchmark":benchmark,"common_rows":len(result.closes),
        "data_status":"教学样本" if synthetic else "历史日线；非实时"}
