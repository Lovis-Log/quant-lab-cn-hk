"""Shared, locally updated trade replay for AH and US price backtests."""

import hashlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab.trade_replay import build_trade_replay, signal_explanation
from quant_lab.ui_helpers import plotly_chart, style_figure


EVENT_LABELS = {
    "decision_date": "信号日期", "date": "执行日期", "side": "方向", "status": "状态",
    "reason": "未成交原因", "shares": "成交股数", "price": "成交价", "fees": "实际费用",
    "cash_after": "成交后现金", "opening_price": "原始开盘", "commission": "佣金",
    "additional_fees": "附加费", "slippage": "滑点价差",
}
DAILY_LABELS = {"date": "交易日", "equity": "收盘权益", "cash": "现金", "shares": "持仓股数",
                "overnight_pnl": "隔夜持仓盈亏", "intraday_pnl": "日内持仓盈亏",
                "slippage": "滑点价差", "fees": "实际费用", "equity_change": "权益变化"}


def _event_table(events):
    display = events.drop(columns="day_index").copy()
    display["side"] = display.side.map({"buy": "买入", "sell": "卖出"})
    display["status"] = display.status.map({"filled": "成交", "blocked": "未成交"})
    return display.rename(columns=EVENT_LABELS)


def _select_order(date_key, selection_key, events, table_key):
    rows = st.session_state[table_key]["selection"]["rows"]
    if rows:
        _set_date(date_key, selection_key, events.date.iloc[rows[0]].date())


def _set_date(date_key, selection_key, value):
    st.session_state[date_key] = value
    st.session_state[selection_key] = value


def _remember_date(date_key, selection_key):
    st.session_state[selection_key] = st.session_state[date_key]


def _locate_drawdown(date_key, selection_key, view_key, value):
    _set_date(date_key, selection_key, value)
    st.session_state[view_key] = True


def render_trade_replay(raw, result, spec, config, *, market, symbol, currency,
                        adjustment, query, slot, stale=False):
    identity = (market, symbol, repr(query), result.audit_id)
    cache_key = "_trade_replay_" + slot
    cached = st.session_state.get(cache_key)
    if cached is None or cached[0] != identity or cached[1] is not result:
        try:
            replay = build_trade_replay(raw, result.signals, result.strategy, spec, config)
        except (ValueError, KeyError, TypeError) as exc:
            st.error(f"交易回放不可用：{exc}")
            return
        st.session_state[cache_key] = (identity, result, replay)
    else:
        replay = cached[2]
    token = hashlib.sha256(repr(identity).encode()).hexdigest()[:16]
    prefix = "replay_" + slot + "_" + token
    date_key = prefix + "_date"
    view_key = prefix + "_drawdown"
    active_key = "_trade_replay_active_" + slot
    selection_key = "_trade_replay_date_" + slot
    if st.session_state.get(active_key) != identity:
        st.session_state[active_key] = identity
        initial = replay.events.date.iloc[0] if not replay.events.empty else replay.daily.date.iloc[0]
        st.session_state[selection_key] = initial.date()
        st.session_state[view_key] = False
    if date_key not in st.session_state or st.session_state[date_key] not in tuple(replay.daily.date.dt.date):
        st.session_state[date_key] = st.session_state[selection_key]
    _replay_fragment(raw, result.signals, replay, spec, currency, adjustment, prefix, date_key, selection_key, view_key, stale)


@st.fragment
def _replay_fragment(raw, signals, replay, spec, currency, adjustment, prefix, date_key, selection_key, view_key, stale):
    st.markdown("#### 交易回放")
    if stale:
        st.warning("本次计算失败，回放仍对应上次成功计算。")
    days = tuple(replay.daily.date.dt.date)
    selected = st.session_state[date_key]
    i = days.index(selected)
    event_days = tuple(day.date() for day in replay.events.date)
    previous = [day for day in event_days if day < selected]
    following = [day for day in event_days if day > selected]
    controls = st.columns([1, 1, 2])
    controls[0].button("上一笔", key=prefix+"_previous", disabled=not previous,
                       on_click=_set_date, args=(date_key, selection_key, previous[-1] if previous else selected), width="stretch")
    controls[1].button("下一笔", key=prefix+"_next", disabled=not following,
                       on_click=_set_date, args=(date_key, selection_key, following[0] if following else selected), width="stretch")
    controls[2].selectbox("交易日", days, key=date_key, format_func=lambda day: day.isoformat(),
                          on_change=_remember_date, args=(date_key, selection_key))
    period = replay.drawdown
    st.button("定位最大回撤", key=prefix+"_locate_drawdown", disabled=period is None,
              on_click=_locate_drawdown, args=(date_key, selection_key, view_key, days[period.trough] if period else selected))
    if replay.events.empty:
        st.info("此区间没有订单，仍可按交易日查看信号和账户。")
    else:
        with st.expander("选择订单", expanded=False):
            table_key = prefix+f"_orders_{i}"
            st.dataframe(_event_table(replay.events), key=table_key, hide_index=True, width="stretch", height=240,
                         on_select=lambda: _select_order(date_key, selection_key, replay.events, table_key), selection_mode="single-row")
    account = replay.daily.iloc[i]
    metrics = st.columns(4)
    metrics[0].metric(f"现金（{currency}）", f"{account.cash:,.2f}")
    metrics[1].metric("持仓股数", f"{account.shares:,.0f}")
    metrics[2].metric(f"收盘权益（{currency}）", f"{account.equity:,.2f}")
    metrics[3].metric(f"当日盈亏（{currency}）", f"{account.equity_change:+,.2f}")

    left, right = max(0, i - 20), min(len(raw), i + 21)
    prices = raw.iloc[left:right]
    figure = go.Figure(go.Candlestick(x=prices.date, open=prices.open, high=prices.high,
                                     low=prices.low, close=prices.close, name="不复权K线"))
    for side, status, label, color, marker in (
        ("buy", "filled", "买入成交", "#D7797E", "triangle-up"),
        ("sell", "filled", "卖出成交", "#73B798", "triangle-down"),
        ("buy", "blocked", "买入未成交", "#C6A56D", "x"),
        ("sell", "blocked", "卖出未成交", "#78A7DB", "x"),
    ):
        events = replay.events
        subset = events.loc[(events.side == side) & (events.status == status)
                            & events.day_index.between(left, right - 1)]
        figure.add_trace(go.Scatter(x=subset.date, y=subset.price if status == "filled" else subset.opening_price,
                                    mode="markers", name=label, text=subset.reason,
                                    marker={"color": color, "symbol": marker, "size": 11}))
    figure.add_vline(x=pd.Timestamp(selected), line_dash="dot", line_color="#C6A56D")
    figure = style_figure(figure, 360)
    figure.update_layout(uirevision=prefix+str(i), xaxis_rangeslider_visible=False)
    plotly_chart(figure, key=prefix+"_candles", width="stretch", theme=None)
    st.caption(f"{selected:%Y-%m-%d}；K线与成交价均为不复权价格（{currency}）。未成交标记位于原始开盘价。")

    st.markdown("**信号与执行**")
    st.write(signal_explanation(signals, spec, i))
    basis = {"qfq": "前复权", "hfq": "后复权"}.get(adjustment, adjustment or "不复权")
    st.caption(f"信号价格口径：{basis}（{currency}）。均线仅在下方信号图展示。")
    if i:
        snapshot = signals.iloc[[i - 1]][["date", "close", "ma_short", "ma_long", "signal"]].copy()
        snapshot["signal"] = snapshot.signal.map({0: "空仓", 1: "持有"})
        st.dataframe(snapshot.rename(columns={"date": "信号日期", "close": "信号收盘价", "ma_short": "短均线",
                                              "ma_long": "长均线", "signal": "目标持仓"}), hide_index=True, width="stretch")
    signal_prices = signals.iloc[left:right]
    signal_chart = go.Figure()
    for column, label in (("close", "信号收盘价"), ("ma_short", f"MA {spec.short_window}"),
                          ("ma_long", f"MA {spec.long_window}")):
        signal_chart.add_trace(go.Scatter(x=signal_prices.date, y=signal_prices[column], name=label))
    if i:
        signal_chart.add_vline(x=signals.date.iloc[i - 1], line_dash="dot", line_color="#C6A56D")
    signal_chart = style_figure(signal_chart, 240)
    signal_chart.update_layout(uirevision=prefix+str(i))
    plotly_chart(signal_chart, key=prefix+"_signals", width="stretch", theme=None)
    today = replay.events.loc[replay.events.day_index == i]
    if today.empty:
        st.info("当日没有订单：目标持仓无需调整。" if i else "首日没有可执行的此前收盘信号。")
    else:
        order = today.iloc[0]
        if order.status == "blocked":
            st.warning(f"当日未成交：{order.reason}")
        st.dataframe(_event_table(today), hide_index=True, width="stretch")
    explanation = pd.DataFrame({"项目": ["隔夜持仓价格变化", "日内持仓价格变化", "滑点价差（减项）", "实际费用（减项）", "权益变化"],
                                f"金额（{currency}）": [account.overnight_pnl, account.intraday_pnl,
                                                       account.slippage, account.fees, account.equity_change]})
    st.dataframe(explanation, hide_index=True, width="stretch")
    st.caption("权益变化＝隔夜持仓盈亏＋日内持仓盈亏－滑点价差－实际费用。滑点已包含在成交价中，此处仅拆解，不重复扣费。")

    if period is None:
        st.caption("无回撤区间。")
    elif st.session_state[view_key]:
        st.markdown("**最大回撤区间**")
        recovery = "尚未恢复" if period.recovery is None else days[period.recovery].isoformat()
        st.write(f"峰值 {days[period.peak]}，谷值 {days[period.trough]}，最大回撤 {period.value:.2%}；恢复：{recovery}。")
        equity = replay.daily
        curve = go.Figure(go.Scatter(x=equity.date, y=equity.equity, name=f"收盘权益（{currency}）"))
        curve.add_vrect(x0=equity.date.iloc[period.peak], x1=equity.date.iloc[period.trough],
                        fillcolor="#D7797E", opacity=.15, line_width=0)
        curve.add_vline(x=pd.Timestamp(selected), line_dash="dot", line_color="#C6A56D")
        curve = style_figure(curve, 260)
        curve.update_layout(uirevision=prefix+"_drawdown")
        plotly_chart(curve, key=prefix+"_equity", width="stretch", theme=None)
        # Peak is the closing account; the loss interval begins on its following day.
        interval = replay.events.loc[replay.events.day_index.between(period.peak + 1, period.trough)]
        st.caption("峰值收盘后至谷值收盘的订单与主要亏损日；按每日账户变化解释，不作市场因果推断。")
        if interval.empty:
            st.info("回撤下跌区间没有订单，损益来自既有持仓估值。")
        else:
            st.dataframe(_event_table(interval), hide_index=True, width="stretch")
        losses = equity.iloc[period.peak + 1:period.trough + 1]
        losses = losses.loc[losses.equity_change < 0].nsmallest(5, "equity_change")
        st.dataframe(losses[list(DAILY_LABELS)].rename(columns=DAILY_LABELS), hide_index=True, width="stretch")
