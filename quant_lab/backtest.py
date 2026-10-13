"""Long-only daily research backtest with next-open execution assumptions.

This is a controlled approximation. It cannot reconstruct order-book liquidity,
actual limit queues, corporate-action cash flows, or exchange-specific fees.
"""

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    market: str = "A 股"
    initial_cash: float = 1_000_000.0
    lot_size: int = 100
    commission_bps: float = 3.0
    min_commission: float = 5.0
    buy_tax_bps: float = 0.0
    sell_tax_bps: float = 5.0
    slippage_bps: float = 2.0
    limit_pct: float | None = 0.10

    def __post_init__(self) -> None:
        if self.market not in {"A 股", "港股"}:
            raise ValueError("回测市场必须是 A 股或港股。")
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0 or self.lot_size < 1:
            raise ValueError("初始资金和交易单位必须大于零。")
        costs = (self.commission_bps, self.min_commission, self.buy_tax_bps,
                 self.sell_tax_bps, self.slippage_bps)
        if not all(math.isfinite(value) and value >= 0 for value in costs):
            raise ValueError("交易成本参数不能为负。")
        if self.slippage_bps >= 10_000:
            raise ValueError("滑点必须小于 100%。")
        if self.limit_pct is not None and not 0 < self.limit_pct < 1:
            raise ValueError("涨跌停比例必须在 0 到 1 之间。")


def illustrative_config(market: str, initial_cash: float = 1_000_000.0,
                        lot_size: int = 100) -> BacktestConfig:
    """Editable research assumptions, not a current legal fee schedule."""
    if market == "A 股":
        return BacktestConfig(market=market, initial_cash=initial_cash, lot_size=lot_size)
    if market == "港股":
        return BacktestConfig(
            market=market, initial_cash=initial_cash, lot_size=lot_size,
            commission_bps=10.0, min_commission=0.0,
            buy_tax_bps=10.0, sell_tax_bps=10.0,
            slippage_bps=3.0, limit_pct=None,
        )
    raise ValueError("回测市场必须是 A 股或港股。")


@dataclass(frozen=True)
class BacktestResult:
    equity: pd.DataFrame
    orders: pd.DataFrame


def _fee(notional: float, side: str, config: BacktestConfig) -> float:
    commission = max(config.min_commission, notional * config.commission_bps / 10_000)
    tax_bps = config.buy_tax_bps if side == "buy" else config.sell_tax_bps
    return commission + notional * tax_bps / 10_000


def run_backtest(
    raw_history: pd.DataFrame, close_signals: pd.Series, config: BacktestConfig
) -> BacktestResult:
    """Use signal from close t-1 to trade at open t; never same-close fills."""
    required = {"date", "open", "close", "volume"}
    if not required.issubset(raw_history.columns) or len(raw_history) < 2:
        raise ValueError("回测至少需要两个交易日的原始开盘、收盘与成交量。")
    if len(close_signals) != len(raw_history):
        raise ValueError("信号与原始成交价格的交易日数量不一致。")
    if not raw_history["date"].is_monotonic_increasing or raw_history["date"].duplicated().any():
        raise ValueError("原始行情必须按唯一交易日升序排列。")
    if close_signals.isna().any() or not set(close_signals.unique()).issubset({0, 1}):
        raise ValueError("信号只能是 0 或 1。")
    if not np.isfinite(raw_history[["open", "close", "volume"]].to_numpy(dtype=float)).all():
        raise ValueError("成交价格和成交量必须为有限数值。")
    if raw_history[["open", "close"]].isna().any().any() or (
        raw_history[["open", "close"]] <= 0
    ).any().any():
        raise ValueError("成交价格必须为正的有效数值。")
    if raw_history["volume"].isna().any() or (raw_history["volume"] < 0).any():
        raise ValueError("成交量必须为非负有效数值。")

    cash = float(config.initial_cash)
    shares = 0
    last_buy_index = -1
    equity_rows: list[dict[str, object]] = []
    order_rows: list[dict[str, object]] = []

    for i in range(len(raw_history)):
        row = raw_history.iloc[i]
        decision = int(close_signals.iloc[i - 1]) if i > 0 else 0
        side = "buy" if decision == 1 and shares == 0 else "sell" if decision == 0 and shares > 0 else None
        status = "none"
        if side is not None:
            reason = ""
            traded_shares = 0
            execution_price = 0.0
            fees = 0.0
            opening_price = float(row["open"])
            if float(row["volume"]) <= 0:
                reason = "零成交量，视为无法成交"
            elif side == "sell" and config.market == "A 股" and i <= last_buy_index:
                reason = "T+1：当日买入股份不可卖出"
            elif config.market == "A 股" and config.limit_pct is not None and i > 0:
                previous_close = float(raw_history["close"].iloc[i - 1])
                if side == "buy" and opening_price >= previous_close * (1 + config.limit_pct):
                    reason = "开盘触及假设涨停，买入不成交"
                elif side == "sell" and opening_price <= previous_close * (1 - config.limit_pct):
                    reason = "开盘触及假设跌停，卖出不成交"

            if not reason and side == "buy":
                execution_price = opening_price * (1 + config.slippage_bps / 10_000)
                lots = int(cash // (execution_price * config.lot_size))
                while lots > 0:
                    candidate = lots * config.lot_size
                    notional = candidate * execution_price
                    fees = _fee(notional, side, config)
                    if notional + fees <= cash:
                        traded_shares = candidate
                        break
                    lots -= 1
                if traded_shares:
                    cash -= traded_shares * execution_price + fees
                    shares += traded_shares
                    last_buy_index = i
                else:
                    reason = "资金不足以买入一个交易单位"
            elif not reason and side == "sell":
                execution_price = opening_price * (1 - config.slippage_bps / 10_000)
                traded_shares = shares
                notional = traded_shares * execution_price
                fees = _fee(notional, side, config)
                cash += notional - fees
                shares = 0

            status = "filled" if traded_shares else "blocked"
            order_rows.append(
                {
                    "decision_date": raw_history["date"].iloc[i - 1],
                    "date": row["date"], "side": side, "status": status,
                    "reason": reason, "shares": traded_shares,
                    "price": execution_price if traded_shares else None,
                    "fees": fees if traded_shares else 0.0,
                    "cash_after": cash,
                }
            )
        equity_rows.append(
            {
                "date": row["date"], "equity": cash + shares * float(row["close"]),
                "cash": cash, "shares": shares, "decision_signal": decision,
                "order_status": status,
            }
        )

    return BacktestResult(pd.DataFrame(equity_rows), pd.DataFrame(order_rows))


def run_buy_and_hold(raw_history: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
    """Benchmark enters at the next open and uses the same costs and rules."""
    return run_backtest(
        raw_history, pd.Series(1, index=raw_history.index, dtype=int), config
    )
