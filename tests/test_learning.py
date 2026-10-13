"""Academy calculations agree with the examples shown to beginners."""

import pytest

from quant_lab.learning import LESSONS, lesson_experiment


def test_all_eight_lessons_have_required_parts() -> None:
    assert len(LESSONS) == 8
    for lesson in LESSONS:
        assert all((lesson.intuition, lesson.formula, lesson.example,
                    lesson.code, lesson.question, lesson.parameter))


def test_compound_variance_drawdown_and_correlation_examples() -> None:
    compound, _ = lesson_experiment(0, 10)
    assert compound["本金"].iloc[2] == pytest.approx(121)
    variance, _ = lesson_experiment(2, 3)
    assert variance["样本值"].var(ddof=1) == pytest.approx(1)
    drawdown, _ = lesson_experiment(4, 90)
    assert drawdown["回撤"].min() == pytest.approx(-0.25)
    correlation, _ = lesson_experiment(6, 4)
    assert correlation["X"].corr(correlation["Y"]) == pytest.approx(1)
