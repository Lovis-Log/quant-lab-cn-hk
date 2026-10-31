"""Watchlist close references across markets; never a trading provider."""

from datetime import datetime, timedelta

from quant_lab.market_data import MarketSnapshot
from quant_lab.paths import user_data_dir


class WatchlistProvider:
    def __init__(self, ah_provider):
        self.ah_provider = ah_provider

    def snapshot(self, market, symbol):
        if market != "美股":
            return self.ah_provider.snapshot(market, symbol)
        from quant_lab.us_market import NY
        from quant_lab.us_sources import fetch_sina_reference
        end = datetime.now(NY).date()
        reference = fetch_sina_reference(symbol, end - timedelta(days=21), end,
                                         force=True, cache_namespace=str(user_data_dir()))
        if reference.update_error:
            raise ValueError(reference.update_error)
        info = reference.observation
        return MarketSnapshot(market, info.symbol, float(reference.frame.close.iloc[-1]),
            reference.frame.date.iloc[-1].date(), datetime.fromisoformat(info.received_at),
            info.source, "USD", "历史日线收盘参考；非实时，确切延迟未知；来源声明未复权",
            quality_status=f"已结束日线OHLCV校验；参考缺口{len(reference.missing_sessions)}；不认证上市状态")
