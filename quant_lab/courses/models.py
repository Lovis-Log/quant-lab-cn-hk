"""Offline Academy contracts. No UI, storage or network dependencies."""

from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class Parameter:
    label: str
    minimum: float
    maximum: float
    default: float
    step: float = 1


@dataclass(frozen=True)
class Course:
    course_id: str
    title: str
    group: str
    prerequisites: tuple[str, ...]
    objective: str
    intuition: str
    scenario: str
    formula: str
    units: str
    example: str
    interpretation: str
    mistakes: str
    code: str
    code_notes: tuple[str, ...]
    question: str
    answer: str
    parameter: Parameter
    articles: tuple[str, ...]
    knowledge: tuple[str, ...] = ()
    legacy_index: int | None = None


@dataclass(frozen=True)
class ChartSpec:
    x: str
    series: tuple[str, ...]
    kind: str = "line"
    percent: bool = False


@dataclass
class TeachingResult:
    table: pd.DataFrame
    chart: ChartSpec
    conclusion: str
    metrics: Mapping[str, float | None] = field(default_factory=dict)
    percent_columns: tuple[str, ...] = ()
    knowledge_values: Mapping[str, float | None] = field(default_factory=dict)
    knowledge_readings: Mapping[str, str] = field(default_factory=dict)
    report: str = ""
