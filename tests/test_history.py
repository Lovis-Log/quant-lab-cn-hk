"""Hand-checkable data and return calculations; no network in test runs."""

from datetime import date

import pandas as pd
import pytest

from quant_lab.data import DataUnavailableError, fetch_a_share_daily
from quant_lab.metrics import simple_price_return, summarize_prices
from quant_lab.processing import DataValidationError, clean_tencent_history


def sample_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date": "2026-10-09", "open": 10.5, "high": 12.0, "low": 10.0,
             "close": 11.0, "volume": 2000, "amount": 22000},
            {"date": "2026-10-08", "open": 9.5, "high": 10.5, "low": 9.0,
             "close": 10.0, "volume": 1000, "amount": 10000},
        ]
    )


def test_history_is_sorted_and_return_matches_hand_calculation() -> None:
    history = clean_tencent_history(
        sample_rows(), date(2026, 10, 1), date(2026, 10, 11)
    )
    summary = summarize_prices(history)

    assert history["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-10-08", "2026-10-09"
    ]
    assert summary.simple_return == pytest.approx(0.10)
    assert summary.period_high == 12.0
    assert summary.period_low == 9.0
    assert summary.trading_days == 2


def test_invalid_or_insufficient_prices_are_not_reported_as_returns() -> None:
    with pytest.raises(ValueError):
        simple_price_return(0, 11)

    one_day = clean_tencent_history(
        sample_rows().iloc[:1], date(2026, 10, 1), date(2026, 10, 11)
    )
    assert summarize_prices(one_day).simple_return is None

    duplicate = pd.concat([sample_rows(), sample_rows().iloc[:1]], ignore_index=True)
    with pytest.raises(DataValidationError, match="重复交易日"):
        clean_tencent_history(duplicate, date(2026, 10, 1), date(2026, 10, 11))


def test_fetch_uses_unadjusted_stock_history(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}

    def fake_history(**kwargs: object) -> pd.DataFrame:
        received.update(kwargs)
        return sample_rows()

    monkeypatch.setattr("quant_lab.data.ak.stock_zh_a_hist_tx", fake_history)
    history = fetch_a_share_daily("600519", date(2026, 10, 1), date(2026, 10, 11))

    assert received == {
        "symbol": "600519", "start_date": "20261001", "end_date": "20261011",
        "adjust": "", "timeout": 15,
    }
    assert len(history) == 2


def test_provider_failure_is_visible_and_logged(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def failing_history(**_: object) -> pd.DataFrame:
        raise ConnectionError("upstream unavailable")

    log_path = tmp_path / "data_errors.log"
    monkeypatch.setattr("quant_lab.data.ak.stock_zh_a_hist_tx", failing_history)
    monkeypatch.setattr("quant_lab.data.LOG_PATH", log_path)

    with pytest.raises(DataUnavailableError, match="暂时无法获取"):
        fetch_a_share_daily("600519", date(2026, 10, 1), date(2026, 10, 11))
    assert "600519" in log_path.read_text(encoding="utf-8")
