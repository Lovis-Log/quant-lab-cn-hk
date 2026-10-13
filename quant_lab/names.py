"""Company short names from securities profiles, keyed by market and code."""

from datetime import datetime, timezone, timedelta
from threading import RLock

import akshare as ak
import pandas as pd
import requests
import sqlite3

from quant_lab.market_data import normalize_symbol, display_security
from quant_lab import storage


class NameProvider:
    source = "东方财富证券资料 · AKShare 字段口径"

    def lookup(self, market: str, symbol: str) -> str:
        symbol = normalize_symbol(market, symbol)
        if market == "A 股":
            raw = ak.stock_individual_info_em(symbol=symbol, timeout=5)
            values = dict(zip(raw["item"], raw["value"]))
            returned = str(values.get("股票代码", "")).zfill(6)
            name = values.get("股票简称")
        else:
            # Same securities-profile endpoint/fields as AKShare 1.19.1, but
            # with a bounded timeout (the installed HK helper has no timeout).
            response = requests.get(
                "https://datacenter.eastmoney.com/securities/api/data/v1/get",
                params={"reportName": "RPT_HKF10_INFO_SECURITYINFO",
                        "columns": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR",
                        "filter": f'(SECUCODE="{symbol}.HK")', "pageNumber": "1",
                        "pageSize": "1", "source": "F10", "client": "PC"},
                timeout=(3, 8),
            )
            response.raise_for_status()
            row = response.json()["result"]["data"][0]
            returned = normalize_symbol(market, str(row["SECUCODE"]))
            name = row["SECURITY_NAME_ABBR"]
        if returned != symbol or not isinstance(name, str) or not name.strip() or pd.isna(name):
            raise ValueError("证券资料字段或代码不匹配。")
        return name.strip()


class NameCache:
    def __init__(self, provider=None, ttl=timedelta(hours=24), retry=timedelta(minutes=5)):
        self.provider = provider or NameProvider()
        self.ttl, self.retry = ttl, retry
        self._values = {}
        self._attempts = {}
        self._lock = RLock()

    def lookup(self, market: str, symbol: str) -> str:
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
            if previous and now - previous[1] < self.ttl:
                return previous[0]
            if key in self._attempts and now - self._attempts[key] < self.retry:
                return previous[0] if previous else ""
            self._attempts[key] = now
            try:
                name = self.provider.lookup(market, symbol)
                successful_at = datetime.now(timezone.utc)
                self._values[key] = (name, successful_at)
                try:
                    storage.save_security_name(market, symbol, name, self.provider.source, successful_at)
                except (OSError, sqlite3.Error):
                    pass
                return name
            except Exception:
                # Name failures never assert delisting or block prices/backtests.
                return previous[0] if previous else ""


NAME_CACHE = NameCache()


def security_name(market: str, symbol: str) -> str:
    try:
        return NAME_CACHE.lookup(market, symbol)
    except ValueError:
        return ""


def security_label(market: str, symbol: str, name: str | None = None) -> str:
    try:
        return display_security(market, symbol, name if name is not None else security_name(market, symbol))
    except ValueError:
        return f"{market} {symbol}（名称暂不可用）"
