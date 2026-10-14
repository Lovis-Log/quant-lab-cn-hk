"""Optional DeepSeek drafting around auditable, locally executed experiments.

Generated Python is displayed as text only. The model can suggest parameters,
but it never receives a tool for file writes, shell commands, or code execution.
"""

from dataclasses import dataclass
from typing import Any

from quant_lab.deepseek import AIRequestError, safe_context

from quant_lab.research import ExperimentResult
from quant_lab.strategy import StrategySpec


class AIUnavailableError(RuntimeError):
    """The optional model service is absent or returned an unusable response."""


@dataclass(frozen=True)
class ResearchHypothesis:
    title: str
    rationale: str
    strategy: StrategySpec
    assumptions: list[str]
    statistical_risks: list[str]
    example_code: str


@dataclass(frozen=True)
class ResearchReport:
    summary: str
    observations: list[str]
    limitations: list[str]
    next_tests: list[str]


HYPOTHESIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "rationale": {"type": "string"},
        "strategy_kind": {"type": "string", "enum": ["single_ma", "dual_ma", "trend"]},
        "short_window": {"type": "integer"},
        "long_window": {"type": "integer"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "statistical_risks": {"type": "array", "items": {"type": "string"}},
        "example_code": {"type": "string"},
    },
    "required": ["title", "rationale", "strategy_kind", "short_window", "long_window",
                 "assumptions", "statistical_risks", "example_code"],
    "additionalProperties": False,
}

REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "observations": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "next_tests": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "observations", "limitations", "next_tests"],
    "additionalProperties": False,
}


def _structured_response(
    payload: dict[str, Any], schema: dict[str, Any],
    instructions: str, client: Any | None = None, *, model: str = "", metadata=None,
) -> dict[str, Any]:
    if client is None:
        raise AIUnavailableError("请在 DeepSeek 侧栏配置密钥并选择模型。")
    try:
        result = client.structured(model, payload, schema, instructions, metadata=metadata)
        if not isinstance(result, dict):
            raise AIUnavailableError("模型没有返回结构化对象。")
        return result
    except AIUnavailableError:
        raise
    except AIRequestError as exc:
        raise AIUnavailableError(str(exc)) from None
    except Exception as exc:
        raise AIUnavailableError(f"AI 服务调用失败：{type(exc).__name__}") from exc


def draft_hypothesis(
    question: str, market: str, symbol: str, client: Any | None = None,
    *, model: str = "", metadata=None, context=None,
) -> ResearchHypothesis:
    """Turn a question into bounded built-in strategy parameters, plus text code."""
    if not question.strip() or len(question) > 600:
        raise ValueError("研究问题须为 1 到 600 个字符。")
    payload = {"question": question.strip(), "market": market, "symbol": symbol,
               "allowed_strategies": ["single_ma", "dual_ma", "trend"],
               "bounds": "2 <= short_window < long_window <= 250", "context": safe_context(context)}
    result = _structured_response(
        payload, HYPOTHESIS_SCHEMA,
        "You are a cautious quant research assistant. Propose one testable hypothesis "
        "using only the listed built-in strategies and valid periods. State assumptions "
        "and statistical pitfalls. example_code is illustrative pandas code only; "
        "it will never be executed. Do not claim future profits or real tradeability.",
        client, model=model, metadata=metadata,
    )
    try:
        spec = StrategySpec(
            kind=result["strategy_kind"], short_window=int(result["short_window"]),
            long_window=int(result["long_window"]),
        )
        return ResearchHypothesis(
            title=str(result["title"]), rationale=str(result["rationale"]),
            strategy=spec, assumptions=[str(x) for x in result["assumptions"]],
            statistical_risks=[str(x) for x in result["statistical_risks"]],
            example_code=str(result["example_code"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AIUnavailableError("模型给出的参数未通过本地验证。") from exc


def audit_snapshot(experiment: ExperimentResult) -> dict[str, Any]:
    """Deterministic evidence shown beside any AI interpretation."""
    return {
        "audit_id": experiment.audit_id,
        "full_cumulative_return": experiment.full_stats.cumulative_return,
        "benchmark_cumulative_return": experiment.benchmark_stats.cumulative_return,
        "full_max_drawdown": experiment.full_stats.max_drawdown,
        "full_sharpe": experiment.full_stats.sharpe,
        "train_cumulative_return": experiment.train_stats.cumulative_return,
        "test_cumulative_return": experiment.test_stats.cumulative_return,
        "split_date": str(experiment.split_date.date()),
        "filled_orders": int((experiment.strategy.orders.get("status") == "filled").sum())
        if not experiment.strategy.orders.empty else 0,
    }


def draft_report(
    experiment: ExperimentResult, context: dict[str, str], client: Any | None = None,
    *, model: str = "", metadata=None,
) -> ResearchReport:
    """Interpret a fixed evidence snapshot without granting execution tools."""
    payload = {"context": safe_context(context), "verified_metrics": audit_snapshot(experiment)}
    result = _structured_response(
        payload, REPORT_SCHEMA,
        "You are a cautious quantitative research reviewer. Interpret only the "
        "provided verified_metrics. Discuss sample size, costs, slippage, price "
        "adjustment, survivorship bias, parameter sensitivity and out-of-sample "
        "uncertainty where relevant. Never invent numerical results, promise returns, "
        "or present this backtest as live trading evidence.",
        client, model=model, metadata=metadata,
    )
    try:
        return ResearchReport(
            summary=str(result["summary"]),
            observations=[str(x) for x in result["observations"]],
            limitations=[str(x) for x in result["limitations"]],
            next_tests=[str(x) for x in result["next_tests"]],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AIUnavailableError("模型研究报告未通过本地格式验证。") from exc
