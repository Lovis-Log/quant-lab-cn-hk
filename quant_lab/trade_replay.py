"""Read-only explanations of existing single-security price-model results."""

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

from quant_lab.backtest import BacktestResult
from quant_lab.strategy import StrategySpec


class ReplayCosts(Protocol):
    initial_cash: float
    commission_bps: float
    min_commission: float
    buy_tax_bps: float
    sell_tax_bps: float
    slippage_bps: float


@dataclass(frozen=True)
class DrawdownPeriod:
    peak: int
    trough: int
    recovery: int | None
    value: float


@dataclass(frozen=True)
class TradeReplay:
    daily: pd.DataFrame
    events: pd.DataFrame
    drawdown: DrawdownPeriod | None


def locate_drawdown(equity: pd.Series) -> DrawdownPeriod | None:
    """Earliest deepest trough, latest preceding equal peak, first recovery."""
    values = np.asarray(equity, dtype=float)
    if not len(values) or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("回放权益必须为正的有限值。")
    peaks = np.maximum.accumulate(values)
    drawdowns = values / peaks - 1
    trough = int(np.argmin(drawdowns))
    if drawdowns[trough] == 0:
        return None
    peak = int(np.flatnonzero(values[:trough] == peaks[trough])[-1])
    recovered = np.flatnonzero(values[trough + 1:] >= peaks[trough])
    recovery = int(trough + 1 + recovered[0]) if len(recovered) else None
    return DrawdownPeriod(peak, trough, recovery, float(drawdowns[trough]))


def signal_explanation(signals: pd.DataFrame, spec: StrategySpec, index: int) -> str:
    """Explain the saved close signal preceding the selected execution day."""
    if index == 0:
        return "首个交易日没有此前收盘信号，账户从现金开始。"
    row = signals.iloc[index - 1]
    target = "持有" if int(row.signal) else "空仓"
    if pd.isna(row.ma_long):
        detail = "长均线尚未形成"
    elif spec.kind == "single_ma":
        detail = f"信号收盘价 {row.close:.4f} {'>' if row.close > row.ma_long else '≤'} 长均线 {row.ma_long:.4f}"
    elif spec.kind == "dual_ma":
        if pd.isna(row.ma_short):
            detail = "短均线尚未形成"
        else:
            detail = f"短均线 {row.ma_short:.4f} {'>' if row.ma_short > row.ma_long else '≤'} 长均线 {row.ma_long:.4f}"
    else:
        previous = signals.ma_long.iloc[index - 2] if index >= 2 else np.nan
        slope = row.ma_long - previous
        trend = "尚不可比较" if pd.isna(slope) else f"变化 {slope:+.4f}"
        detail = (f"信号收盘价 {row.close:.4f} {'>' if row.close > row.ma_long else '≤'} "
                  f"长均线 {row.ma_long:.4f}；长均线{trend}")
    return f"{row.date:%Y-%m-%d} 收盘：{detail}，目标为{target}；最早下一交易日开盘执行。"


def build_trade_replay(
    raw: pd.DataFrame, signals: pd.DataFrame, result: BacktestResult,
    spec: StrategySpec, config: ReplayCosts,
) -> TradeReplay:
    """Reconcile the saved ledger, without fetching data or running a backtest."""
    required = {"date", "open", "high", "low", "close", "volume"}
    signal_columns = {"date", "close", "ma_short", "ma_long", "signal"}
    equity_columns = {"date", "cash", "shares", "equity", "decision_signal", "order_status"}
    if (not required.issubset(raw) or not signal_columns.issubset(signals)
            or not equity_columns.issubset(result.equity) or raw.empty):
        raise ValueError("回放缺少原始行情、保存的信号或账户字段。")
    prices = raw.reset_index(drop=True).copy()
    saved = signals.reset_index(drop=True)
    daily = result.equity.reset_index(drop=True).copy()
    dates = prices.date
    if (dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing
            or not dates.equals(saved.date) or not dates.equals(daily.date)):
        raise ValueError("回放行情、信号和账户交易日不一致。")
    numbers = prices[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
    accounts = daily[["cash", "shares", "equity"]].to_numpy(dtype=float)
    if (not np.isfinite(numbers).all() or (numbers[:, :4] <= 0).any() or (numbers[:, 4] < 0).any()
            or not np.isfinite(accounts).all() or (daily.shares < 0).any()
            or (daily.shares % 1 != 0).any() or (daily.equity <= 0).any()
            or not np.isfinite(saved.close.to_numpy(dtype=float)).all()
            or (saved.close <= 0).any() or saved.signal.isna().any()
            or not set(saved.signal.unique()).issubset({0, 1})):
        raise ValueError("回放行情、信号或账户存在无效数值。")
    if not daily.decision_signal.equals(saved.signal.shift(1, fill_value=0).astype(daily.decision_signal.dtype)):
        raise ValueError("回放决策与前一交易日保存的信号不一致。")
    for column in ("ma_short", "ma_long"):
        if not np.isfinite(saved[column].dropna().to_numpy(dtype=float)).all():
            raise ValueError("回放保存的均线包含无效数值。")
    if spec.kind == "single_ma":
        condition = saved.close > saved.ma_long
    elif spec.kind == "dual_ma":
        condition = saved.ma_short > saved.ma_long
    else:
        condition = (saved.close > saved.ma_long) & (saved.ma_long.diff() > 0)
    if not np.array_equal(condition.fillna(False).astype(int), saved.signal):
        raise ValueError("回放策略与保存的信号条件不一致。")
    if not np.allclose(daily.cash + daily.shares * prices.close, daily.equity, rtol=1e-10, atol=1e-8):
        raise ValueError("回放现金、持仓估值与权益不一致。")

    order_columns = ["decision_date", "date", "side", "status", "reason", "shares", "price", "fees", "cash_after"]
    orders = result.orders.reset_index(drop=True).copy()
    if orders.empty:
        orders = pd.DataFrame(columns=order_columns)
    elif not set(order_columns).issubset(orders):
        raise ValueError("回放订单字段不完整。")
    if (orders.date.duplicated().any() or not orders.date.is_monotonic_increasing
            or not orders.date.isin(dates.iloc[1:]).all()):
        raise ValueError("回放订单日期重复或不在可执行区间。")
    daily["fees"] = 0.0
    daily["slippage"] = 0.0
    share_changes = np.zeros(len(daily))
    cash_changes = np.zeros(len(daily))
    enriched = []
    for order in orders.itertuples(index=False):
        i = int(dates.searchsorted(order.date))
        if (order.decision_date != dates.iloc[i - 1] or order.side not in {"buy", "sell"}
                or order.status not in {"filled", "blocked"} or daily.order_status.iloc[i] != order.status):
            raise ValueError("回放订单的信号日期、方向或状态不一致。")
        previous_shares = float(daily.shares.iloc[i - 1])
        decision = int(daily.decision_signal.iloc[i])
        expected_side = "buy" if decision == 1 and previous_shares == 0 else "sell" if decision == 0 and previous_shares > 0 else None
        if order.side != expected_side:
            raise ValueError("回放订单方向与保存的目标持仓不一致。")
        commission = additional = slip = 0.0
        opening = float(prices.open.iloc[i])
        if order.status == "filled":
            if (not np.isfinite([order.shares, order.price, order.fees]).all()
                    or order.shares <= 0 or order.shares % 1 or order.price <= 0):
                raise ValueError("回放成交数量或价格无效。")
            direction = 1 if order.side == "buy" else -1
            expected_price = opening * (1 + direction * config.slippage_bps / 10000)
            notional = order.shares * order.price
            commission = max(config.min_commission, notional * config.commission_bps / 10000)
            rate = config.buy_tax_bps if order.side == "buy" else config.sell_tax_bps
            additional = notional * rate / 10000
            if (not np.isclose(order.price, expected_price, rtol=1e-10, atol=1e-8)
                    or not np.isclose(order.fees, commission + additional, rtol=1e-10, atol=1e-8)):
                raise ValueError("回放费用或滑点与保存的成交不一致。")
            slip = direction * order.shares * (order.price - opening)
            share_changes[i] = direction * order.shares
            cash_changes[i] = -direction * notional - order.fees
            daily.loc[i, ["fees", "slippage"]] = [order.fees, slip]
        elif order.shares != 0 or order.fees != 0 or not pd.isna(order.price):
            raise ValueError("未成交订单不能产生股数、价格或费用。")
        if not np.isclose(order.cash_after, daily.cash.iloc[i], rtol=1e-10, atol=1e-8):
            raise ValueError("回放订单现金与账户不一致。")
        enriched.append({**dict(zip(order_columns, (getattr(order, key) for key in order_columns))),
                         "day_index": i, "opening_price": opening, "commission": commission,
                         "additional_fees": additional, "slippage": slip})

    previous_cash = daily.cash.shift(1, fill_value=config.initial_cash)
    previous_shares = daily.shares.shift(1, fill_value=0)
    # Account arithmetic can lose a few ULPs when subtracting large balances.
    money_tolerance = max(1e-8, np.finfo(float).eps * max(config.initial_cash, daily.equity.max()) * 16)
    if (not np.allclose(daily.cash - previous_cash, cash_changes, rtol=1e-10, atol=money_tolerance)
            or not np.array_equal(daily.shares - previous_shares, share_changes)):
        raise ValueError("回放订单与每日现金、持仓变化不一致。")
    event_dates = set(orders.date)
    if any((row.date not in event_dates and row.order_status != "none") for row in daily.itertuples()):
        raise ValueError("账户订单状态缺少对应订单。")
    attempts = ((daily.decision_signal == 1) & (previous_shares == 0)) | ((daily.decision_signal == 0) & (previous_shares > 0))
    if not np.array_equal(attempts, daily.date.isin(event_dates)):
        raise ValueError("保存的目标持仓缺少对应订单尝试。")
    daily["overnight_pnl"] = previous_shares * (prices.open - prices.close.shift(1, fill_value=prices.open.iloc[0]))
    daily["intraday_pnl"] = daily.shares * (prices.close - prices.open)
    daily["equity_change"] = daily.equity - daily.equity.shift(1, fill_value=config.initial_cash)
    explained = daily.overnight_pnl + daily.intraday_pnl - daily.slippage - daily.fees
    if not np.allclose(explained, daily.equity_change, rtol=1e-10, atol=money_tolerance):
        raise ValueError("回放盈亏拆解与原始权益变化不一致。")
    daily["drawdown"] = daily.equity / daily.equity.cummax() - 1
    events = pd.DataFrame(enriched, columns=order_columns + ["day_index", "opening_price", "commission", "additional_fees", "slippage"])
    return TradeReplay(daily, events, locate_drawdown(daily.equity))
