"""Session-only real US daily references; no execution/archival bypass."""

from dataclasses import asdict
from datetime import datetime
import json

import plotly.graph_objects as go
import streamlit as st

from quant_lab import us_sources
from quant_lab.history_ranges import history_window
from quant_lab.jobs import JobState
from quant_lab.paths import user_data_dir
from quant_lab.ui_helpers import style_figure
from quant_lab.ui_jobs import loading_placeholder, submit_task, take_result
from quant_lab.us_market import NY, normalize_us_symbol


def render_us_prices():
    today = datetime.now(NY).date()
    st.session_state["active_us_context"] = {
        "page": "美股数据", "market": "美股", "currency": "USD",
        "data_status": "尚未加载真实美股历史日线；真实回测来源关卡未通过",
    }
    st.caption("免费公开历史日线 · USD · 仅会话保留 · 非实时，确切延迟未知")
    period = st.selectbox("美股历史区间", (1, 3, 5, 10, "自定义"),
                          format_func=lambda value: f"{value}年" if isinstance(value, int) else value,
                          key="us_price_period")
    if st.session_state.get("_us_price_period") != period:
        if isinstance(period, int):
            start, end = history_window(today, period)
            st.session_state["us_price_start"] = start
            st.session_state["us_price_end"] = end
        st.session_state["_us_price_period"] = period
    with st.form("us_real_prices"):
        ticker = st.text_input("美股代码", value="AAPL", key="us_price_symbol",
                               help="例如AAPL、MSFT、NVDA；类别股使用点号。输入代码不代表证券身份已核验。")
        columns = st.columns(2)
        start = columns[0].date_input("开始日期", key="us_price_start", min_value=history_window(today, 10)[0], max_value=today)
        end = columns[1].date_input("结束日期", key="us_price_end", max_value=today)
        columns = st.columns(2)
        load = columns[0].form_submit_button("加载真实美股日线", type="primary")
        refresh = columns[1].form_submit_button("立即更新美股日线", help="绕过五分钟查询缓存；相同的进行中请求会合并。")
    try:
        ticker = normalize_us_symbol(ticker)
        if start > end:
            raise ValueError("开始日期不能晚于结束日期。")
    except ValueError as error:
        st.warning(str(error))
        return
    key = (str(user_data_dir()), ticker, start, end)
    if load or refresh:
        submit_task("us_prices", key, us_sources.fetch_sina_reference, ticker, start, end,
                    force=refresh, cache_namespace=key[0], job_timeout=60)
    completed = take_result("us_prices", key)
    if completed and completed.state == JobState.SUCCEEDED:
        if isinstance(completed.result, us_sources.USPriceReference):
            st.session_state["us_price_reference"] = (key, completed.result)
            st.session_state.pop("us_price_error", None)
        else:
            st.session_state["us_price_error"] = (key, "来源返回类型无效；没有使用教学数据。")
    elif completed and completed.state == JobState.FAILED:
        st.session_state["us_price_error"] = (key, completed.error)
    saved = st.session_state.get("us_price_reference")
    reference = saved[1] if saved and saved[0] == key else None
    error = st.session_state.get("us_price_error")
    failure = error[1] if error and error[0] == key else None
    if failure:
        st.error(failure)
    if "us_prices" in st.session_state.get("_task_tickets", {}):
        st.caption("美股日线正在更新，可切页或取消；已有日线保留显示。")
        if reference is None:
            loading_placeholder(220)
    if reference is not None:
        _render_reference(reference, key, failure)
    else:
        st.info("输入代码并加载真实历史日线。请求失败会显示错误，不会换成教学行情。")
    st.button("运行真实美股回测", disabled=True, key="us_live_backtest")
    st.caption("真实回测与美元组合仍需核验证券身份、原始执行价、完整公司行动、结算日历和快照留存权限。")
    with st.expander("免费来源资格与限制"):
        st.table([
            {"来源": "新浪 / AKShare日线接口", "状态": "真实日线价格参考可用；执行价、完整事件、身份及留存未认证"},
            {"来源": "东方财富 / AKShare", "状态": "此前请求失败；不静默切换来源或价格口径"},
            {"来源": "Alpha Vantage免费Daily", "状态": "官方full历史需付费，免费compact不足十年"},
            {"来源": "Twelve Data Basic", "状态": "免费账户权限、显示/留存及完整支付事件未核验"},
            {"来源": "Massive Stocks Basic", "状态": "官方列日线、拆股、分红支付日期，两年免费历史；非显示使用/策略与留存仍待许可核验"},
        ])
        st.caption("来源仅声明未复权，未独立认证为可成交价格；拆股、分红会影响跨日价格。此页不计算策略收益、总回报或风险排名。不自动写磁盘行情或保存实验。")


def _render_reference(reference, key, failure):
    info, frame = reference.observation, reference.frame
    if reference.update_error:
        st.error(reference.update_error)
    columns = st.columns(3)
    columns[0].metric("最近历史收盘（USD）", f"{frame.close.iloc[-1]:,.4f}")
    columns[1].metric("日线条数", str(len(frame)))
    columns[2].metric("最近交易日", info.actual_end)
    st.write(f"{info.symbol}（名称暂不可用） · 请求 {info.requested_start} 至 {info.requested_end}；实际 {info.actual_start} 至 {info.actual_end}")
    received = datetime.fromisoformat(info.received_at).astimezone(NY).isoformat(sep=" ")
    st.caption(f"{info.source} · {reference.price_basis}；成功接收（纽约）：{received}")
    st.caption(("会话缓存 · " if reference.cached else "上游请求 · ") + reference.update_result)
    if failure:
        st.warning("本次更新失败，继续显示上次有效日线；成功接收时间未变。")
    figure = go.Figure(go.Candlestick(x=frame.date, open=frame.open, high=frame.high,
                                      low=frame.low, close=frame.close, name="历史日线（USD）"))
    figure.update_xaxes(rangeslider_visible=False)
    figure.update_yaxes(title_text="USD／股")
    figure = style_figure(figure)
    figure.update_layout(uirevision=repr(key))
    st.plotly_chart(figure, width="stretch", theme=None, key="us_real_price_chart")
    with st.expander("日线明细与数据质量", expanded=True):
        st.caption(f"OHLCV基础校验通过；参考日历已结束交易日 {reference.expected_sessions}个，缺口 {len(reference.missing_sessions)}个，非参考交易日 {len(reference.non_session_dates)}个，排除未结束日线 {reference.excluded_unfinished_rows}条。")
        if reference.missing_sessions or reference.non_session_dates:
            st.warning("覆盖不完整或与参考日历不同。上市不足、源端截断、停牌与异常缺失尚不能区分；不补价格，不认证完整区间。")
            st.write({"缺口日期": list(reference.missing_sessions), "非参考交易日": list(reference.non_session_dates)})
        st.dataframe(frame.rename(columns={"date": "交易日", "open": "开盘（USD）", "high": "最高（USD）",
                     "low": "最低（USD）", "close": "收盘（USD）", "volume": "成交量（股，来源口径）"}),
                     width="stretch", hide_index=True)
        summary = {**asdict(info), "currency": reference.currency, "price_basis": reference.price_basis,
                   "expected_sessions": reference.expected_sessions, "missing_sessions": reference.missing_sessions,
                   "non_session_dates": reference.non_session_dates,
                   "excluded_unfinished_rows": reference.excluded_unfinished_rows,
                   "cached": reference.cached, "update_error": reference.update_error or failure,
                   "raw_prices_saved": False, "backtest_eligible": False}
        st.download_button("导出来源核验摘要", json.dumps(summary, ensure_ascii=False, indent=2).encode(),
                           file_name=f"{info.symbol}_us_source_observation.json", mime="application/json")
    st.session_state["active_us_context"].update({
        "symbol": info.symbol, "source": info.source, "received_at": info.received_at,
        "data_period": [info.actual_start, info.actual_end], "data_fingerprint": info.content_sha256,
        "adjustment": reference.price_basis,
        "data_status": "真实美股历史日线价格参考；非实时；真实回测未开放" +
                       ("；最近更新失败，数据可能过期" if reference.update_error or failure else ""),
        "price_metrics": {"latest_close": float(frame.close.iloc[-1]), "observations": len(frame)},
    })
