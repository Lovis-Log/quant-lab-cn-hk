"""Per-query refresh state with single-flight fetching and retained good data."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import Event, Lock
import time


@dataclass(frozen=True)
class RefreshView:
    value: object | None
    cached: bool
    age_seconds: float
    result: str
    attempted_at: datetime | None
    error: str | None = None


class RefreshCache:
    def __init__(self, ttl=300, max_entries=64):
        self.ttl, self.max_entries = ttl, max_entries
        self._entries = {}
        self._flight = {}
        self._lock = Lock()

    def get(self, key, loader, *, force=False, same=lambda a, b: a == b,
            failure_message="请求失败；保留上次有效数据，数据可能过期。") -> RefreshView:
        with self._lock:
            old = self._entries.get(key)
            if not force and old and time.monotonic() - old[0] < self.ttl:
                return replace(old[1], cached=True, age_seconds=time.monotonic()-old[0])
            waiter = self._flight.get(key)
            if waiter is None:
                waiter = Event()
                self._flight[key] = waiter
                owner = True
            else:
                owner = False
        if not owner:
            if not waiter.wait(60):
                return RefreshView(old[1].value if old else None, True,
                                   time.monotonic()-old[0] if old else 0,
                                   "更新请求仍在进行", old[1].attempted_at if old else None)
            with self._lock:
                entry = self._entries[key]
                return replace(entry[1], age_seconds=max(0, time.monotonic()-entry[0]))
        attempted = datetime.now(timezone.utc)
        try:
            value = loader()
            unchanged = old and old[1].value is not None and same(old[1].value, value)
            view = RefreshView(value, False, 0,
                               "检查成功，数据未变化" if unchanged else "取得新数据", attempted)
            successful_at = time.monotonic()
        except Exception:
            value = old[1].value if old else None
            successful_at = old[0] if old else time.monotonic() - self.ttl
            view = RefreshView(value, bool(old), max(0, time.monotonic()-successful_at),
                               "请求失败", attempted, failure_message)
        finally:
            with self._lock:
                self._entries[key] = (successful_at, view)
                if len(self._entries) > self.max_entries:
                    candidates = [k for k in self._entries if k not in self._flight]
                    if candidates:
                        del self._entries[min(candidates, key=lambda k: self._entries[k][0])]
                self._flight.pop(key).set()
        return view
