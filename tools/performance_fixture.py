"""Offline fixture injected by benchmark_desktop into its isolated copy only."""

from datetime import datetime, timezone
import os
import time
import json
from pathlib import Path
import numpy as np
import pandas as pd

from quant_lab import credentials, names, ui
from quant_lab.data import HistoryBundle

credentials.load_key = lambda **kwargs: None
names.security_name = lambda *args, **kwargs: "离线性能样本"
names.cached_security_name = lambda *args, **kwargs: "离线性能样本"


if os.environ.get("QUANT_LAB_TEST_EVENTS") == "1" and not getattr(ui._toggle_dock, "_validation_trace", False):
    _original_toggle = ui._toggle_dock
    def _traced_toggle(kind):
        import streamlit as st
        fields = ("active_dock_panel", "maximized_panel", "manual_panel_open", "deepseek_panel_open", "notes_panel_open")
        before = {key: st.session_state.get(key) for key in fields}
        result = _original_toggle(kind)
        after = {key: st.session_state.get(key) for key in fields}
        target = Path(os.environ["QUANT_LAB_DATA_DIR"]) / "dock-events.jsonl"
        with target.open("a", encoding="utf-8") as output:
            output.write(json.dumps({"kind": kind, "before": before, "after": after}, ensure_ascii=False)+"\n")
        return result
    _traced_toggle._validation_trace = True
    ui._toggle_dock = _traced_toggle


def history(market, symbol, start, end, adjustment="", **kwargs):
    time.sleep(float(os.environ.get("QUANT_LAB_TEST_IO_DELAY", "0")))
    count = int(os.environ.get("QUANT_LAB_TEST_ROWS", "2520"))
    dates = pd.bdate_range(end=pd.Timestamp(end), periods=count)
    rng = np.random.default_rng(20261027)
    close = 100 * np.exp(np.cumsum(rng.normal(.0002, .012, count)))
    opening = np.r_[100., close[:-1]] * (1 + rng.normal(0, .0015, count))
    volume = rng.integers(80000, 250000, count)
    frame = pd.DataFrame({"date": dates, "open": opening,
        "high": np.maximum(opening, close) * (1 + rng.uniform(.001, .008, count)),
        "low": np.minimum(opening, close) * (1 - rng.uniform(.001, .008, count)),
        "close": close, "volume": volume, "amount": close * volume})
    return HistoryBundle(frame, market, symbol, "离线模拟性能样本（非真实行情）",
        "CNY" if market == "A 股" else "HKD", adjustment,
        received_at=datetime.now(timezone.utc))


ui.fetch_history = history
