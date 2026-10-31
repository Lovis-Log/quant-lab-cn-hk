"""Three-market identity normalization for names and watchlists, not execution."""

from quant_lab.market_data import normalize_symbol


def normalize_security(market, symbol):
    if market == "美股":
        from quant_lab.us_market import normalize_us_symbol
        return normalize_us_symbol(symbol)
    return normalize_symbol(market, symbol)
