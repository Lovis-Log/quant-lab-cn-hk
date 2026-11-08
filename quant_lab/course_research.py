"""Explicit, offline mappings from teaching parameters to research drafts."""
from dataclasses import dataclass
from quant_lab.courses import get_course, run_experiment
from quant_lab.security_identity import normalize_security

SUPPORTED = ("moving_average", "dual_trend", "next_open", "execution_costs", "bias",
             "temporal_split", "walk_forward", "resampling_stress", "correlation",
             "portfolio_weights", "rebalance_cash", "concentration")


@dataclass(frozen=True)
class ResearchLaunch:
    course_id: str
    market: str
    codes: tuple[str, ...]
    route: str
    overrides: dict
    note: str


def build_research_launch(course_id, value, market, codes):
    if course_id not in SUPPORTED:
        raise ValueError("本课尚未提供真实研究入口。")
    run_experiment(course_id, {"value": value})  # Enforce the actual teaching contract.
    normalized = tuple(normalize_security(market, code) for code in codes)
    multiple = course_id in SUPPORTED[8:]
    if len(set(normalized)) != len(normalized) or not (2 <= len(normalized) <= 10 if multiple else len(normalized) == 1):
        raise ValueError("请选择2–10只不重复的同市场股票。" if multiple else "请选择一只股票。")
    route = "多股票比较" if multiple else "策略实验室" if course_id in SUPPORTED[:2] else "历史回测" if course_id in SUPPORTED[2:4] else "研究实验台"
    prefix = ("us_price_signal" if route == "策略实验室" else "us_price_bt" if route == "历史回测" else "us_price_val") if market == "美股" else ("strategy" if route == "策略实验室" else "backtest" if route == "历史回测" else "lab")
    overrides = {}
    note = "教学数值不带入；保留目标页已有合法设置，真实结果须手动加载并计算。"
    if course_id == "moving_average" and value >= 3:
        overrides = {prefix+"_kind": "single_ma", prefix+"_short": 2, prefix+"_long": int(value)}
        note = "带入单均线窗口；短周期2仅用于满足现有参数约束。"
    elif course_id == "moving_average":
        note = "当前模型长周期至少3日；2日教学窗口未带入，保留已有策略设置。"
    elif course_id == "dual_trend":
        overrides = {prefix+"_kind": "dual_ma", prefix+"_short": int(value), prefix+"_long": 5}
        note = "带入短周期及课程固定长周期5。"
    elif course_id == "execution_costs":
        key = "us_price_bt_slip" if market == "美股" else f"cost_{market}_slippage"
        overrides = {key: float(value)}
        note = "带入滑点基点；真实研究模型对买卖双边使用同一滑点参数，课程仅演示买入。"
    elif course_id == "temporal_split":
        if .5 <= value / 10 <= .85:
            overrides = {("us_price_val_fraction" if market == "美股" else "lab_fraction"): value / 10}
            note = "训练比例按课程训练观察数÷10带入；其余设置保持。"
        else:
            note = "教学训练比例低于真实研究50%下限，未带入；保留已有比例。"
    if multiple:
        note = "教学相关系数、波动和目标权重不带入；真实组合仍用训练数据计算等权和逆波动率。"
    return ResearchLaunch(course_id, market, normalized, route, overrides, note)
