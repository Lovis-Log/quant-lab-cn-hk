"""Session-only real US daily references; no execution/archival bypass."""

from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import json
import time

import streamlit as st

from quant_lab import us_sources, names
from quant_lab.charts import history_candlestick_chart, history_price_chart
from quant_lab.jobs import JobState
from quant_lab.paths import user_data_dir
from quant_lab.ui_jobs import loading_placeholder, submit_task, take_result
from quant_lab.us_market import NY, normalize_us_symbol


def sync_us_prices(ticker, dates, load=False, refresh=False):
    """Consume the shared sidebar query on market and research pages alike."""
    st.session_state["_us_price_query"] = None
    if dates is None:
        return None
    try:
        ticker = normalize_us_symbol(ticker)
        start, end = dates
        if start > end:
            return None
    except ValueError:
        return None
    key = (str(user_data_dir()), ticker, start, end)
    if load or refresh:
        submit_task("us_prices", key, us_sources.fetch_sina_reference, ticker, start, end,
                    force=refresh, cache_namespace=key[0], job_timeout=60)
        st.session_state["_us_next_attempt"] = (key, datetime.now(timezone.utc) +
            timedelta(seconds=st.session_state.get("refresh_interval_seconds", 300)))
    completed = take_result("us_prices", key)
    if completed and completed.state == JobState.SUCCEEDED:
        if isinstance(completed.result, us_sources.USPriceReference):
            st.session_state["us_price_reference"] = (key, completed.result)
            st.session_state.pop("us_price_error", None)
        else:
            st.session_state["us_price_error"] = (key, "来源返回类型无效；没有使用教学数据。")
    elif completed and completed.state == JobState.FAILED:
        st.session_state["us_price_error"] = (key, completed.error)
    st.session_state["_us_price_query"] = key
    return key


def render_us_prices():
    interval = st.session_state.get("refresh_interval_seconds", 300)
    @st.fragment(run_every=interval if st.session_state.get("refresh_enabled", True) else None)
    def body():
        _render_us_prices()
    body()


def _render_us_prices():
    st.subheader("市场数据实验室")
    st.session_state["active_us_context"] = {
        "page": "美股数据", "market": "美股", "currency": "USD",
        "data_status": "尚未加载当前查询的真实美股历史日线；可用于独立价格研究模型",
    }
    st.caption("免费公开历史日线 · USD · 仅会话保留 · 非实时，确切延迟未知")
    key = st.session_state.get("_us_price_query")
    saved = st.session_state.get("us_price_reference")
    reference = saved[1] if saved and saved[0] == key else None
    error = st.session_state.get("us_price_error")
    failure = error[1] if error and error[0] == key else None
    first, second, _ = st.columns([1.25, 1.25, 4.5])
    requested = first.button("立即更新历史日线", disabled=key is None, key="history_refresh")
    from quant_lab.ui_updates import toggle_refresh
    auto = st.session_state.get("refresh_enabled", True)
    if second.button("暂停自动刷新" if auto else "恢复自动刷新", on_click=toggle_refresh, key="refresh_pause"):
        st.rerun(scope="app")
    wait = st.session_state.get("_us_manual_at", float('-inf')) + 5 - time.monotonic()
    if requested and wait > 0:
        st.info(f"请等待 {wait:.0f} 秒后再点击；本次没有重复请求。")
    scheduled = st.session_state.get("_us_next_attempt")
    due = bool(auto and reference is not None and scheduled and scheduled[0] == key and
               datetime.now(timezone.utc) >= scheduled[1])
    if key and ((requested and wait <= 0) or due):
        if requested:
            st.session_state["_us_manual_at"] = time.monotonic()
        sync_us_prices(key[1], key[2:4], refresh=True)
        st.rerun(scope="app")
    if failure:
        st.error(failure)
    if "us_prices" in st.session_state.get("_task_tickets", {}):
        st.caption("美股日线正在更新，可切页或取消；已有日线保留显示。")
        if reference is None:
            loading_placeholder(220)
    if reference is not None:
        _render_reference(reference, key, failure)
    else:
        st.info("请在左侧选择股票与日期，点击“加载真实历史日线”。请求失败会显示错误，不会换成教学行情。")
    from quant_lab.ui_us_price_research import open_us_price_research
    st.button("进入真实美股研究", key="us_live_backtest", on_click=open_us_price_research)
    st.caption("采用与现有A/H同级的价格与成本模型，不包含公司行动或结算现金；完整现金账户模拟留待后续。")
    with st.expander("免费来源资格与限制"):
        st.table([
            {"来源": "新浪 / AKShare日线接口", "状态": "真实日线价格参考可用；执行价、完整事件、身份及留存未认证"},
            {"来源": "东方财富 / AKShare", "状态": "此前请求失败；不静默切换来源或价格口径"},
            {"来源": "Alpha Vantage免费Daily", "状态": "官方full历史需付费，免费compact不足十年"},
            {"来源": "Twelve Data Basic", "状态": "免费账户权限、显示/留存及完整支付事件未核验"},
            {"来源": "Massive Stocks Basic", "状态": "官方列日线、拆股、分红支付日期，两年免费历史；非显示使用/策略与留存仍待许可核验"},
        ])
        st.caption("来源仅声明未复权，未独立认证为可成交价格；拆股、分红会影响跨日价格。此页不计算策略收益、总回报或风险排名。不自动写磁盘行情或保存实验。")
    from quant_lab.ui_terminal import render_watchlist
    render_watchlist("美股", st.session_state.get("us_price_symbol", ""))


def _render_reference(reference, key, failure):
    info, frame = reference.observation, reference.frame
    if reference.update_error:
        st.error(reference.update_error)
    columns = st.columns(3)
    columns[0].metric("最近历史收盘（USD）", f"{frame.close.iloc[-1]:,.4f}")
    columns[1].metric("日线条数", str(len(frame)))
    columns[2].metric("最近交易日", info.actual_end)
    st.write(f"{names.cached_security_label('美股', info.symbol)} · 请求 {info.requested_start} 至 {info.requested_end}；实际 {info.actual_start} 至 {info.actual_end}")
    received = datetime.fromisoformat(info.received_at).astimezone(NY).isoformat(sep=" ")
    st.caption(f"{info.source} · {reference.price_basis}；成功接收（纽约）：{received}")
    st.caption(("会话缓存 · " if reference.cached else "上游请求 · ") + reference.update_result)
    if failure:
        st.warning("本次更新失败，继续显示上次有效日线；成功接收时间未变。")
    price_tab, candle_tab = st.tabs(("收盘价与成交量", "日 K 线"), default="日 K 线", key="market_chart_tabs", on_change="rerun")
    for tab, builder, chart_key in ((price_tab, history_price_chart, "us_close_price_chart"),
                                     (candle_tab, history_candlestick_chart, "us_real_price_chart")):
        with tab:
            if tab.open:
                figure = builder(frame, "USD")
                figure.update_layout(uirevision=repr(key), title_text=names.cached_security_label("美股", info.symbol))
                st.plotly_chart(figure, width="stretch", theme=None, key=chart_key)
    with st.expander("日线明细与数据质量", expanded=True):
        st.caption(f"OHLCV基础校验通过；参考日历已结束交易日 {reference.expected_sessions}个，缺口 {len(reference.missing_sessions)}个，非参考交易日 {len(reference.non_session_dates)}个，排除未结束日线 {reference.excluded_unfinished_rows}条。")
        if reference.missing_sessions or reference.non_session_dates:
            st.warning("覆盖不完整或与参考日历不同。上市不足、源端截断、停牌与异常缺失尚不能区分；不补价格，不认证完整区间。")
            st.write({"缺口日期": list(reference.missing_sessions), "非参考交易日": list(reference.non_session_dates)})
        table = frame.rename(columns={"date": "交易日", "open": "开盘（USD）", "high": "最高（USD）",
                     "low": "最低（USD）", "close": "收盘（USD）", "volume": "成交量（股，来源口径）"})
        table.insert(0, "股票", names.cached_security_label("美股", info.symbol))
        from quant_lab.ui_history_table import render_history_table
        render_history_table(table, f"美股_{info.symbol}_{info.actual_start}_{info.actual_end}_raw.csv")
        summary = {**asdict(info), "currency": reference.currency, "price_basis": reference.price_basis,
                   "company_name": names.cached_security_name("美股", info.symbol),
                   "expected_sessions": reference.expected_sessions, "missing_sessions": reference.missing_sessions,
                   "non_session_dates": reference.non_session_dates,
                   "excluded_unfinished_rows": reference.excluded_unfinished_rows,
                   "cached": reference.cached, "update_error": reference.update_error or failure,
                   "raw_prices_saved": False, "backtest_eligible": False, "eligibility_model": "us-cash-v1",
                   "price_research": "us-price-cost-v1；按价格模型另行校验，不适用完整现金账户资格"}
        st.download_button("导出来源核验摘要", json.dumps(summary, ensure_ascii=False, indent=2).encode(),
                           file_name=f"{info.symbol}_us_source_observation.json", mime="application/json")
    st.session_state["active_us_context"].update({
        "symbol": info.symbol, "source": info.source, "received_at": info.received_at,
        "company_name": names.cached_security_name("美股", info.symbol),
        "data_period": [info.actual_start, info.actual_end], "data_fingerprint": info.content_sha256,
        "adjustment": reference.price_basis,
        "data_status": "真实美股历史日线价格参考；非实时；可进行价格与成本研究，公司行动未模拟" +
                       ("；最近更新失败，数据可能过期" if reference.update_error or failure else ""),
        "price_metrics": {"latest_close": float(frame.close.iloc[-1]), "observations": len(frame)},
    })
