"""Representative offline explanations and drawdown recovery arithmetic."""

import pytest

from quant_lab.knowledge import KNOWLEDGE, interpret, recovery_return


def test_drawdown_recovery_and_unavailable_values():
    assert recovery_return(-.2) == pytest.approx(.25)
    assert recovery_return(-.5) == pytest.approx(1)
    assert "25.00%" in interpret("drawdown", -.2)
    assert "不说明恢复时间" in interpret("drawdown", -.2)
    assert "没有足够" in interpret("sharpe", None)
    with pytest.raises(ValueError):
        recovery_return(-1)


def test_all_terms_have_research_meaning_and_limits():
    assert {"simple_return","compound","moving_average","variance","std","volatility",
            "drawdown","sharpe","correlation","costs","slippage","bias"}.issubset(KNOWLEDGE)
    for item in KNOWLEDGE.values():
        assert all((item.definition,item.feature,item.importance,item.formula,
                    item.symbols,item.example,item.limitation,item.question))
