"""Same-currency portfolio research with chronological allocation evaluation."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PortfolioAnalysis:
    closes: pd.DataFrame
    returns: pd.DataFrame
    correlation: pd.DataFrame
    covariance: pd.DataFrame
    weights: pd.DataFrame
    test_equity: pd.DataFrame
    train_last_date: pd.Timestamp


def align_closes(histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not 2 <= len(histories) <= 4:
        raise ValueError("组合分析需要 2 到 4 只同币种股票。")
    series: list[pd.Series] = []
    for symbol, history in histories.items():
        if not {"date", "close"}.issubset(history.columns):
            raise ValueError(f"{symbol} 缺少交易日或收盘价。")
        if history["date"].duplicated().any():
            raise ValueError(f"{symbol} 含重复交易日。")
        values = history.set_index("date")["close"].astype(float).rename(symbol)
        if (values <= 0).any() or values.isna().any():
            raise ValueError(f"{symbol} 含无效收盘价。")
        series.append(values)
    result = pd.concat(series, axis=1, join="inner").dropna().sort_index()
    if len(result) < 8:
        raise ValueError("共同交易日不足 8 天，无法做组合分析。")
    return result


def inverse_volatility_weights(train_returns: pd.DataFrame) -> pd.Series:
    """Use only training observations to estimate allocation weights."""
    vol = train_returns.std(ddof=1)
    if vol.isna().any() or (vol <= 0).any():
        raise ValueError("训练区间有资产波动率为零，不能计算逆波动率权重。")
    inverse = 1.0 / vol
    return inverse / inverse.sum()


def analyze_portfolio(
    histories: dict[str, pd.DataFrame], train_fraction: float = 0.70
) -> PortfolioAnalysis:
    """Compare equal and inverse-volatility allocations on held-out dates."""
    if not 0.5 <= train_fraction <= 0.85:
        raise ValueError("训练比例必须在 50% 到 85% 之间。")
    closes = align_closes(histories)
    returns = closes.pct_change().dropna()
    split = int(len(returns) * train_fraction)
    if split < 3 or len(returns) - split < 2:
        raise ValueError("训练集或样本外区间太短。")
    train = returns.iloc[:split]
    test = returns.iloc[split:]
    equal = pd.Series(1.0 / len(closes.columns), index=closes.columns)
    inverse = inverse_volatility_weights(train)
    weights = pd.DataFrame({"等权": equal, "逆波动率": inverse})
    test_daily = pd.DataFrame(
        {"等权": test @ equal, "逆波动率": test @ inverse}, index=test.index
    )
    test_equity = (1.0 + test_daily).cumprod()
    # Beginning of the held-out period is normalized to 1 before its first return.
    starting_date = closes.index[closes.index.get_loc(test.index[0]) - 1]
    test_equity = pd.concat(
        [pd.DataFrame({"等权": [1.0], "逆波动率": [1.0]}, index=[starting_date]),
         test_equity]
    )
    return PortfolioAnalysis(
        closes=closes, returns=returns,
        correlation=returns.corr(), covariance=returns.cov(),
        weights=weights, test_equity=test_equity,
        train_last_date=train.index[-1],
    )
