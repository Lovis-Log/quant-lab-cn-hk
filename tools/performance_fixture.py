"""Offline fixture injected by benchmark_desktop into its isolated copy only."""

from datetime import datetime, timezone
import os
import time
import numpy as np
import pandas as pd

from quant_lab import credentials, names, ui
from quant_lab.data import HistoryBundle

credentials.load_key = lambda **kwargs: None
names.security_name = lambda *args, **kwargs: "离线性能样本"


def history(market, symbol, start, end, adjustment="", **kwargs):
    time.sleep(float(os.environ.get("QUANT_LAB_TEST_IO_DELAY", "0")))
    dates = pd.bdate_range(end=pd.Timestamp(end), periods=2520)
    close = 100 + np.arange(len(dates)) * .02 + np.sin(np.arange(len(dates)))
    frame = pd.DataFrame({"date": dates, "open": close - .1, "high": close + 1,
        "low": close - 1, "close": close, "volume": np.full(len(dates), 100000),
        "amount": close * 100000})
    return HistoryBundle(frame, market, symbol, "离线模拟性能样本（非真实行情）",
        "CNY" if market == "A 股" else "HKD", adjustment,
        received_at=datetime.now(timezone.utc))


ui.fetch_history = history
