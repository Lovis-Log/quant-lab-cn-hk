"""Company short names from securities profiles, keyed by market and code."""

from datetime import datetime, timezone, timedelta
from threading import RLock, Event

import pandas as pd
import requests
import sqlite3

from quant_lab.security_identity import normalize_security as normalize_symbol
from quant_lab import storage
from quant_lab.securities import PROFILE_URL


class NameProvider:
    source = "东方财富证券基础资料 · AKShare 港股字段口径"

    def lookup(self, market: str, symbol: str) -> str:
        symbol = normalize_symbol(market, symbol)
        if market == "美股":
            from quant_lab.us_profiles import security_name
            return security_name(symbol)
        # The old A-share push2 endpoint can disconnect while the basic
        # company directory remains available. No quote values are used here.
        response = requests.get(
            PROFILE_URL,
            params={"reportName": "RPT_F10_BASIC_ORGINFO" if market == "A 股" else "RPT_HKF10_INFO_SECURITYINFO",
                    "columns": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR",
                    "filter": f'(SECURITY_CODE="{symbol}")' if market == "A 股" else f'(SECUCODE="{symbol}.HK")',
                    "pageNumber": "1", "pageSize": "1", "source": "F10", "client": "PC"},
            timeout=(3, 8),
        )
        try:
            response.raise_for_status()
            row = response.json()["result"]["data"][0]
            returned = normalize_symbol(market, str(row["SECUCODE"]))
            name = row["SECURITY_NAME_ABBR"]
        finally:
            response.close()
        if returned != symbol or not isinstance(name, str) or not name.strip() or pd.isna(name):
            raise ValueError("证券资料字段或代码不匹配。")
        return name.strip()

    def source_for(self, market):
        if market == "美股":
            from quant_lab.us_profiles import SOURCE
            return SOURCE
        return self.source


class NameCache:
    def __init__(self, provider=None, ttl=timedelta(hours=24), retry=timedelta(minutes=5)):
        self.provider = provider or NameProvider()
        self.ttl, self.retry = ttl, retry
        self._values = {}
        self._attempts = {}
        self._lock = RLock()
        self._flight = {}
        self.errors = {}

    def fresh(self, market, symbol):
        key = (str(storage.database_path()), market, normalize_symbol(market, symbol))
        with self._lock:
            value = self._values.get(key)
            return bool(value and datetime.now(timezone.utc) - value[1] < self.ttl)

    def lookup(self, market: str, symbol: str, *, force: bool = False) -> str:
        symbol = normalize_symbol(market, symbol)
        key = (str(storage.database_path()), market, symbol)
        now = datetime.now(timezone.utc)
        with self._lock:
            previous = self._values.get(key)
            if previous is None:
                try:
                    row = storage.cached_security_name(market, symbol)
                    if row:
                        previous = (row["name"], datetime.fromisoformat(row["fetched_at"]))
                        self._values[key] = previous
                except (OSError, ValueError, sqlite3.Error):
                    pass
            waiter = self._flight.get(key)
            if not force and waiter is None and previous and now - previous[1] < self.ttl:
                return previous[0]
            if not force and waiter is None and key in self._attempts and now - self._attempts[key] < self.retry:
                return previous[0] if previous else ""
            owner = waiter is None
            if owner:
                waiter = Event()
                self._flight[key] = waiter
        if not owner:
            waiter.wait(30)
            with self._lock:
                return self._values.get(key, ("", None))[0]
        with self._lock:
            self._attempts[key] = now
        try:
            name = self.provider.lookup(market, symbol)
            successful_at = datetime.now(timezone.utc)
            with self._lock:
                self._values[key] = (name, successful_at)
                self.errors.pop(key, None)
            try:
                source = self.provider.source_for(market) if hasattr(self.provider, "source_for") else self.provider.source
                storage.save_security_name(market, symbol, name, source, successful_at)
            except (OSError, sqlite3.Error):
                pass
            return name
        except Exception:
            # Name failures never assert delisting or block prices/backtests.
            with self._lock:
                self.errors[key] = "证券名称更新失败；保留上次有效名称。无缓存时显示名称暂不可用。"
            return previous[0] if previous else ""
        finally:
            with self._lock:
                self._flight.pop(key).set()

    def error(self, market, symbol):
        key = (str(storage.database_path()), market, normalize_symbol(market, symbol))
        with self._lock:
            return self.errors.get(key)

    def peek(self, market: str, symbol: str) -> str:
        """Read known names without ever asking the upstream service."""
        symbol = normalize_symbol(market, symbol)
        key = (str(storage.database_path()), market, symbol)
        with self._lock:
            previous = self._values.get(key)
            if previous is not None:
                return previous[0]
        try:
            row = storage.cached_security_name(market, symbol)
        except (OSError, ValueError, sqlite3.Error):
            row = None
        if row:
            with self._lock:
                self._values[key] = (row["name"], datetime.fromisoformat(row["fetched_at"]))
            return row["name"]
        if market != "美股":
            return ""
        # Directory snapshots are local identity data with their original clock.
        from quant_lab.securities import security_directory
        try:
            directory = security_directory(market)
            name = dict(directory.rows).get(symbol, "")
            if name:
                with self._lock:
                    self._values[key] = (name, datetime.fromisoformat(directory.received_at))
            return name
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return ""


NAME_CACHE = NameCache()


def cached_security_name(market: str, symbol: str) -> str:
    try:
        return NAME_CACHE.peek(market, symbol)
    except ValueError:
        return ""


def cached_security_label(market: str, symbol: str, name: str | None = None) -> str:
    try:
        return display_security(market, symbol, name if name is not None else cached_security_name(market, symbol))
    except ValueError:
        return f"{market} {symbol}（名称暂不可用）"


def display_security(market, symbol, name=None):
    return f"{market} {normalize_symbol(market, symbol)}（{name or '名称暂不可用'}）"


def security_name(market: str, symbol: str, *, force: bool = False) -> str:
    try:
        return NAME_CACHE.lookup(market, symbol, force=force)
    except ValueError:
        return ""


def security_label(market: str, symbol: str, name: str | None = None) -> str:
    try:
        return display_security(market, symbol, name if name is not None else security_name(market, symbol))
    except ValueError:
        return f"{market} {symbol}（名称暂不可用）"
