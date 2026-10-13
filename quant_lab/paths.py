"""Writable per-user application paths for web and packaged desktop runs."""

import os
from pathlib import Path


def user_data_dir() -> Path:
    override = os.environ.get("QUANT_LAB_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "QuantLabCNHK"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "quant-lab-cnhk"
