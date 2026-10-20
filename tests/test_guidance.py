"""Every real page and learning reference is valid; teaching answers are checked."""

import math
import pytest

from quant_lab.guidance import GUIDES, COURSES, PATHS, TASKS, validate_catalog, check_answer, course_experiment, task_evidence_valid
from quant_lab.ui import PAGES, TOPBAR_PAGES


def test_catalog_maps_all_pages_and_prerequisites_without_cycles():
    validate_catalog()
    assert set(GUIDES) == set(PAGES) | TOPBAR_PAGES and len(PATHS) == 4
    for guide in GUIDES.values():
        assert all((guide.purpose, guide.controls, guide.steps, guide.example, guide.errors, guide.topics))
    def walk(node, stack):
        assert node not in stack
        for prerequisite in COURSES[node].prerequisites:
            walk(prerequisite, stack + [node])
    for node in COURSES:
        walk(node, [])
    assert any(course is None for path in PATHS.values() for _, course in path)


def test_statistics_guide_describes_actual_regression_and_leakage():
    guide = GUIDES["统计与机器学习"]
    text = " ".join(guide.steps + guide.errors + tuple(meaning for _, meaning in guide.controls))
    assert all(word in text for word in ("零收益", "标准化", "特征", "标签", "时间", "回归", "分类"))
    assert "3 折" in text and "60 行" in text


@pytest.mark.parametrize("course_id,answer", [("simple_return",198),("moving_average",14),
    ("variance",4),("volatility",2*math.sqrt(252)),("drawdown",-20),("sharpe",0),("correlation",-1),("bias",0)])
def test_course_quizzes_have_hand_checkable_answers(course_id, answer):
    assert check_answer(course_id, answer)
    assert not check_answer(course_id, answer + 2)
    assert not check_answer(course_id, float("nan"))
    from quant_lab.learning import LESSONS
    frame, conclusion = course_experiment(course_id, LESSONS[COURSES[course_id].lesson].default)
    assert not frame.empty and conclusion


def test_invalid_or_demonstration_task_evidence_cannot_complete():
    assert not task_evidence_valid("select_security", {"symbol":"600519"})
    assert not task_evidence_valid("load_history", {"history_valid":False,"company_name":"贵州茅台"})
    assert not task_evidence_valid("run_backtest", {"audit_id":"abc","backtest_success":True,"demonstration":True})
    assert not task_evidence_valid("save_research", {"experiment_id":1,"audit_id":"abc","has_judgment":False})
    assert task_evidence_valid("select_security", {"selected":True,"identity_known":True,"symbol":"600519"})
    assert len(TASKS) == 8
