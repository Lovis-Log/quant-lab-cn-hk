"""Clearly labeled, deterministic visual samples; never market observations."""

import numpy as np
import pandas as pd


def make_layout_preview() -> pd.DataFrame:
    """Return unitless data used only to preview chart layout."""
    rng = np.random.default_rng(42)
    count = 144
    steps = rng.normal(loc=0.06, scale=0.38, size=count)
    level = 100 + np.cumsum(steps)
    activity = rng.integers(15, 85, size=count)
    activity[31] = 130
    activity[94] = 118
    return pd.DataFrame(
        {"演示序号": np.arange(1, count + 1), "模拟指数": level, "模拟活动量": activity}
    )
