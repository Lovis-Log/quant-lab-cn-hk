"""Stable legacy routes behind the compact desktop navigation."""

SECTIONS = ("市场数据", "研究工作台", "多股票比较", "Quant Academy")
MARKETS = ("A 股", "港股", "美股")
RESEARCH = {
    "策略实验室": "策略信号",
    "历史回测": "历史回测",
    "风险与组合": "风险与组合",
    "统计与机器学习": "统计分析",
    "研究实验台": "专业验证",
}


def navigation_values(values):
    """Read old saved leaf routes without changing any research contracts."""
    route = values.get("nav_page", "市场数据")
    section = values.get("nav_section")
    if section not in SECTIONS:
        section = "研究工作台" if route in RESEARCH or route == "美股研究" else route
    if section not in SECTIONS:
        section = "市场数据"
    research = values.get("research_page", route if route in RESEARCH else "策略实验室")
    if research not in RESEARCH:
        research = "策略实验室"
    market = values.get("market_selection", values.get("compare_market", "A 股"))
    if route == "美股研究":
        market = "美股"
    elif section == "多股票比较" and "nav_section" not in values:
        market = values.get("compare_market", market)
    if market not in MARKETS:
        market = "A 股"
    return {"nav_section": section, "research_page": research,
            "market_selection": market, "compare_market": market}


def active_route(section, market, research):
    if market == "美股" and section in ("市场数据", "研究工作台"):
        return "美股数据" if section == "市场数据" else "美股研究"
    return research if section == "研究工作台" else section


def comparison_selection(market, text, additions=()):
    """Normalize an editable candidate list, allowing drafts with 0 or 1 item."""
    from quant_lab.market_data import normalize_symbol
    if market not in ("A 股", "港股"):
        raise ValueError("真实美股比较尚未开放。")
    result = []
    for code in [*text.replace("，", ",").split(","), *additions]:
        if not code.strip():
            continue
        code = normalize_symbol(market, code.strip())
        if code not in result:
            result.append(code)
    if len(result) > 10:
        raise ValueError("最多选择10只同市场股票，请先移除部分股票。")
    return tuple(result)
