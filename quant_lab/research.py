"""Reproducible, bounded experiments using only built-in strategies."""

from dataclasses import dataclass
import hashlib

import pandas as pd

from quant_lab.backtest import BacktestConfig, BacktestResult, run_backtest, run_buy_and_hold
from quant_lab.metrics import PerformanceStats, performance_stats
from quant_lab.strategy import StrategySpec, build_signals


@dataclass(frozen=True)
class ExperimentResult:
    signals: pd.DataFrame
    strategy: BacktestResult
    benchmark: BacktestResult
    full_stats: PerformanceStats
    benchmark_stats: PerformanceStats
    train_stats: PerformanceStats
    test_stats: PerformanceStats
    split_date: pd.Timestamp
    audit_id: str


def run_experiment(
    raw_history: pd.DataFrame,
    signal_history: pd.DataFrame,
    spec: StrategySpec,
    config: BacktestConfig,
    train_fraction: float = 0.70,
) -> ExperimentResult:
    """Signals may use adjusted prices; all fills and valuation use raw prices."""
    if not 0.5 <= train_fraction <= 0.85:
        raise ValueError("训练比例必须在 50% 到 85% 之间。")
    if len(raw_history) < max(spec.long_window + 5, 30):
        raise ValueError("历史交易日不足以支持所选均线和样本外比较。")
    if not raw_history["date"].reset_index(drop=True).equals(
        signal_history["date"].reset_index(drop=True)
    ):
        raise ValueError("信号价格与原始成交价格的交易日不一致。")
    signals = build_signals(signal_history, spec)
    strategy = run_backtest(raw_history, signals["signal"], config)
    benchmark = run_buy_and_hold(raw_history, config)
    split = int(len(raw_history) * train_fraction)
    if split < 3 or len(raw_history) - split < 2:
        raise ValueError("样本内或样本外区间太短。")
    strategy_equity = strategy.equity["equity"]
    benchmark_equity = benchmark.equity["equity"]
    digest = hashlib.sha256()
    digest.update(raw_history.to_csv(index=False).encode("utf-8"))
    digest.update(signal_history.to_csv(index=False).encode("utf-8"))
    digest.update(repr(spec).encode("utf-8"))
    digest.update(repr(config).encode("utf-8"))
    digest.update(str(train_fraction).encode("utf-8"))
    return ExperimentResult(
        signals=signals, strategy=strategy, benchmark=benchmark,
        full_stats=performance_stats(strategy_equity),
        benchmark_stats=performance_stats(benchmark_equity),
        train_stats=performance_stats(strategy_equity.iloc[:split]),
        test_stats=performance_stats(strategy_equity.iloc[split - 1:]),
        split_date=raw_history["date"].iloc[split],
        audit_id=digest.hexdigest()[:16],
    )


def sensitivity_table(
    raw_history: pd.DataFrame, signal_history: pd.DataFrame,
    kind: str, config: BacktestConfig, short_options: list[int],
    long_options: list[int], train_fraction: float = 0.70,
) -> pd.DataFrame:
    """Score parameter combinations on older observations only."""
    split = int(len(raw_history) * train_fraction)
    raw_train = raw_history.iloc[:split].reset_index(drop=True)
    signal_train = signal_history.iloc[:split].reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for short in short_options:
        for long in long_options:
            if short >= long or long >= len(raw_train):
                continue
            spec = StrategySpec(kind=kind, short_window=short, long_window=long)
            signal = build_signals(signal_train, spec)["signal"]
            result = run_backtest(raw_train, signal, config)
            filled = result.orders[result.orders["status"] == "filled"] if not result.orders.empty else result.orders
            rows.append(
                {"短周期": short, "长周期": long,
                 "样本内累计收益率": performance_stats(result.equity["equity"]).cumulative_return,
                 "成交次数": len(filled)}
            )
    return pd.DataFrame(rows)
