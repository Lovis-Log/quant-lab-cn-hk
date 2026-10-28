"""Serialize AKShare's embedded Sina JS runtime initialization in this process."""

from threading import RLock


SINA_RUNTIME_LOCK=RLock()
