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
from quant_lab.data_quality import assess_history
from quant_lab.source_rights import TEACHING_RETENTION

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
    rng = np.random.default_rng(20261027+sum((index+1)*ord(letter) for index,letter in enumerate(symbol)))
    close = 100 * np.exp(np.cumsum(rng.normal(.0002, .012, count)))
    opening = np.r_[100., close[:-1]] * (1 + rng.normal(0, .0015, count))
    volume = rng.integers(80000, 250000, count)
    frame = pd.DataFrame({"date": dates, "open": opening,
        "high": np.maximum(opening, close) * (1 + rng.uniform(.001, .008, count)),
        "low": np.minimum(opening, close) * (1 - rng.uniform(.001, .008, count)),
        "close": close, "volume": volume, "amount": close * volume})
    source = "离线模拟性能样本（非真实行情）"
    currency = "CNY" if market == "A 股" else "HKD"
    received = datetime.now(timezone.utc)
    quality = assess_history(frame, market, start, end, source=source, currency=currency,
                             adjustment=adjustment, received_at=received)
    return HistoryBundle(frame, market, symbol, source, currency, adjustment,
                         received_at=received, quality=quality, retention=TEACHING_RETENTION)


ui.fetch_history = history

from quant_lab import comparison,portfolio_cash
comparison.fetch_history_cached=history
portfolio_cash.fetch_history_cached=history

if os.environ.get("QUANT_LAB_TEST_COMPARISON")=="1":
    from datetime import date
    from quant_lab import ui_terminal,storage
    from quant_lab.market_data import MarketSnapshot
    if not storage.list_watchlist():storage.add_watchlist("A 股","600519")
    def _comparison_watch(items):
        now=datetime.now(timezone.utc)
        return {item:MarketSnapshot(item[0],item[1],100.,now.date(),now,"固定教学快照，非真实行情","CNY" if item[0]=="A 股" else "HKD",
            quality_status="固定教学快照，非真实行情") for item in items},{}
    ui_terminal.snapshot_batch=_comparison_watch


if os.environ.get("QUANT_LAB_TEST_US_SOURCE")=="1":
    from quant_lab import us_sources
    def _us_validation_failure(*args,**kwargs):
        raise ValueError("隔离验收模拟上游超时；没有有效真实数据，未替换为教学行情。")
    us_sources.inspect_sina_prices=_us_validation_failure
