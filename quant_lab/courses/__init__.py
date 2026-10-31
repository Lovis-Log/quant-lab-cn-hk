"""Validated course registry and bounded offline experiment interface."""

from functools import lru_cache
import math
from types import MappingProxyType
from typing import Mapping

from .content import COURSES, GROUPS
from .experiments import EXPERIMENTS, execute
from .models import ChartSpec, Course, Parameter, TeachingResult


LEGACY_COURSE_IDS = (
    "simple_return", "moving_average", "variance", "volatility",
    "drawdown", "sharpe", "correlation", "bias",
)


def validate_catalog(courses, article_ids=None):
    """Fail visibly on broken content rather than silently omitting a lesson."""
    ids = [c.course_id for c in courses]
    if len(ids) != len(set(ids)):
        raise ValueError("课程ID重复。")
    by_id = {c.course_id: c for c in courses}
    for course in courses:
        if not all((course.course_id, course.title, course.objective, course.intuition,
                    course.scenario, course.formula, course.units, course.example,
                    course.interpretation, course.mistakes, course.code, course.code_notes,
                    course.question, course.answer, course.articles)):
            raise ValueError(f"课程内容不完整：{course.course_id}")
        if course.group not in GROUPS or any(p not in by_id for p in course.prerequisites):
            raise ValueError(f"专题或先修引用无效：{course.course_id}")
        if article_ids is not None and any(a not in article_ids for a in course.articles):
            raise ValueError(f"课程文章引用无效：{course.course_id}")
        p = course.parameter
        if not (all(math.isfinite(v) for v in (p.minimum, p.maximum, p.default, p.step))
                and p.minimum <= p.default <= p.maximum and p.minimum < p.maximum and p.step > 0):
            raise ValueError(f"课程参数定义无效：{course.course_id}")
        if course.legacy_index is None and course.course_id not in EXPERIMENTS:
            raise ValueError(f"缺少实验入口：{course.course_id}")
        if course.legacy_index is not None and (
                not 0 <= course.legacy_index < len(LEGACY_COURSE_IDS)
                or LEGACY_COURSE_IDS[course.legacy_index] != course.course_id):
            raise ValueError(f"旧课程映射无效：{course.course_id}")
    visited, pending = set(), set()

    def visit(course_id):
        if course_id in pending:
            raise ValueError("课程先修关系存在环。")
        if course_id in visited:
            return
        pending.add(course_id)
        for prerequisite in by_id[course_id].prerequisites:
            visit(prerequisite)
        pending.remove(course_id)
        visited.add(course_id)

    for course_id in ids:
        visit(course_id)


validate_catalog(COURSES)
COURSE_BY_ID = MappingProxyType({c.course_id: c for c in COURSES})
COURSE_NUMBERS = MappingProxyType({c.course_id: i + 1 for i, c in enumerate(COURSES)})


@lru_cache(maxsize=1)
def validated_courses():
    """Validate bundled article references once on entering Academy, offline."""
    from quant_lab.manual_content import load_manual_content
    from quant_lab.knowledge import KNOWLEDGE
    articles = load_manual_content().articles
    validate_catalog(COURSES, {article.id for article in articles})
    if any(topic not in KNOWLEDGE for c in COURSES for topic in c.knowledge):
        raise ValueError("课程知识解释引用无效。")
    return COURSES


def get_course(course_id: str) -> Course:
    try:
        return COURSE_BY_ID[course_id]
    except (KeyError, TypeError) as error:
        raise ValueError("未知课程。") from error


def search_courses(query="", group="全部课程"):
    """Titles rank ahead of body matches; curriculum order breaks ties."""
    terms = query.strip().casefold().split()
    results = []
    for course in COURSES:
        if group != "全部课程" and course.group != group:
            continue
        title = f"{COURSE_NUMBERS[course.course_id]:02d} {course.title}".casefold()
        text = " ".join((title, course.course_id, course.group, course.objective,
                         course.intuition, course.scenario, course.mistakes, course.code)).casefold()
        if all(term in text for term in terms):
            rank = 0 if all(term in title for term in terms) else 1
            results.append((rank, COURSE_NUMBERS[course.course_id], course))
    return tuple(item[2] for item in sorted(results, key=lambda item: item[:2]))


def run_experiment(course_id: str, parameters: Mapping | None = None) -> TeachingResult:
    course = get_course(course_id)
    parameters = {} if parameters is None else parameters
    if not isinstance(parameters, Mapping) or set(parameters) - {"value"}:
        raise ValueError("课程参数只接受value。")
    value = parameters.get("value", course.parameter.default)
    p = course.parameter
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("课程参数必须为有限数值。")
    if not p.minimum <= value <= p.maximum:
        raise ValueError("课程参数超出范围。")
    steps = (value - p.minimum) / p.step
    if not math.isclose(steps, round(steps), abs_tol=1e-7):
        raise ValueError("课程参数不符合步长。")
    return execute(course, float(value))
