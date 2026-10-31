"""Curriculum contracts and hand-checkable independent financial examples."""

from dataclasses import replace
import hashlib
import json
import math

import numpy as np
import pandas as pd
import pytest

from quant_lab.courses import (COURSES, GROUPS, LEGACY_COURSE_IDS, get_course,
                               run_experiment, search_courses, validate_catalog, validated_courses)
from quant_lab.courses.experiments import (inverse_weights, regression_scores, replay_teaching_manifest,
                                          safe_correlation, sample_sharpe, sample_std)
from quant_lab.charts import course_chart
from quant_lab.learning import LESSONS, lesson_experiment


def test_complete_catalog_links_and_legacy_mapping():
    assert len(validated_courses()) == 28
    assert all(sum(c.group == group for c in COURSES) == 4 for group in GROUPS)
    assert len(LESSONS) == 8
    assert tuple(get_course(cid).legacy_index for cid in LEGACY_COURSE_IDS) == tuple(range(8))
    assert search_courses("回撤")[0].course_id == "drawdown"
    assert len(search_courses("", GROUPS[0])) == 4
    assert not search_courses("没有这个课程xyz")


@pytest.mark.parametrize("course", COURSES, ids=lambda c: c.course_id)
def test_each_experiment_boundary_and_display_contract(course):
    for value in dict.fromkeys((course.parameter.minimum, course.parameter.default, course.parameter.maximum)):
        result = run_experiment(course.course_id, {"value": value})
        assert not result.table.empty and result.conclusion
        assert set((result.chart.x, *result.chart.series, *result.percent_columns)) <= set(result.table.columns)
        assert all(v is None or math.isfinite(v) for v in result.metrics.values())
        assert not np.isinf(result.table.select_dtypes(include="number").to_numpy()).any()
        # The chart must show the actual result columns, including intentional gaps.
        chart = course_chart(result, course.course_id)
        assert len(chart.data) == len(result.chart.series)
        for trace, name in zip(chart.data, result.chart.series):
            np.testing.assert_equal(np.asarray(trace.y), result.table[name].to_numpy())
        if course.legacy_index is not None:
            old_frame, old_conclusion = lesson_experiment(course.legacy_index, value)
            pd.testing.assert_frame_equal(result.table, old_frame)
            assert result.conclusion == old_conclusion


def test_registry_rejects_duplicate_missing_cyclic_and_broken_article_references():
    with pytest.raises(ValueError, match="重复"):
        validate_catalog((*COURSES, COURSES[0]))
    with pytest.raises(ValueError, match="先修"):
        validate_catalog((replace(COURSES[0], prerequisites=("missing",)), *COURSES[1:]))
    with pytest.raises(ValueError, match="环"):
        validate_catalog((replace(COURSES[0], prerequisites=(COURSES[1].course_id,)), *COURSES[1:]))
    with pytest.raises(ValueError, match="文章"):
        validate_catalog(COURSES, set())


@pytest.mark.parametrize("parameters", [{"value": np.nan}, {"value": float("inf")}, {"value": True},
                                         {"value": "3"}, {"value": -1}, {"value": 3.5},
                                         {"unknown": 1}, [], {"value": 101}])
def test_experiment_rejects_unsafe_or_out_of_contract_parameters(parameters):
    with pytest.raises(ValueError):
        run_experiment("financial_variables", parameters)
    with pytest.raises(ValueError):
        run_experiment("missing")


def test_hand_calculations_for_new_financial_experiments():
    assert run_experiment("financial_variables").metrics["cash"] == 700
    assert run_experiment("price_sequences").metrics["latest"] == 11
    assert run_experiment("frames_missing").metrics == {"missing": 1, "duplicates": 1}
    shifted = run_experiment("returns_shift").table
    assert pd.isna(shifted.loc[2, "次日可用信号"])
    assert shifted.loc[3, "次日可用信号"] == 1
    assert run_experiment("log_annual").metrics["total_return"] == pytest.approx(.08)
    assert run_experiment("ohlcv_time", {"value": 13}).metrics["valid_ohlc"] == 0
    basis = run_experiment("price_basis", {"value": 2}).metrics
    assert basis["price_only_return"] == -.5 and basis["wealth"] == 102
    execution = run_experiment("next_open").table
    assert list(execution["开盘买入执行"]) == [False, False, True, False]
    assert run_experiment("next_open").metrics["close_pnl"] == -1
    assert run_experiment("execution_costs").metrics["shares"] == 100
    assert run_experiment("execution_costs", {"value": 5}).metrics["shares"] == 0
    assert run_experiment("temporal_split").metrics["test_return"] == pytest.approx(.97 * 1.04 * 1.01 * .98 - 1)
    rolling = run_experiment("walk_forward").table
    assert (rolling["训练终点"] < rolling["测试观察"]).all()
    assert rolling.iloc[0]["选择"] == "A" and rolling.iloc[0]["测试收益"] == -.02
    weights = run_experiment("portfolio_weights").metrics
    assert weights["weight_a"] == pytest.approx(2/3)
    assert weights["test_return"] == pytest.approx(.01/3)
    balance = run_experiment("rebalance_cash").metrics
    assert balance["shares_a"] == 45 and balance["shares_b"] == 68
    assert balance["fees"] == pytest.approx(.204)
    assert balance["cash"] == pytest.approx(15.796)
    assert balance["final_equity"] + balance["fees"] == pytest.approx(1100)
    assert (run_experiment("rebalance_cash").table["现金余额"] >= 0).all()
    assert run_experiment("concentration", {"value": 100}).metrics["volatility"] == pytest.approx(.2)
    assert run_experiment("hypothesis_quality", {"value": 0}).metrics["issue_count"] == 0
    assert run_experiment("hypothesis_quality", {"value": 3}).metrics["issue_count"] == 1
    scores = run_experiment("benchmark_regression").metrics
    assert scores["mae"] == pytest.approx(1) and scores["r_squared"] == pytest.approx(.625)
    comparison = run_experiment("compare_experiments").metrics
    assert comparison["net_a"] == pytest.approx(.02) and comparison["net_b"] == pytest.approx(.0225)


def test_empty_invalid_and_zero_variation_are_not_invented_values():
    assert sample_std([]) is None and sample_std([1]) is None
    assert sample_std([1, np.nan]) is None
    assert sample_std([1, 1]) == 0
    assert sample_sharpe([.01, .01]) is None
    assert safe_correlation([1, 1], [1, 2]) is None
    assert safe_correlation([], []) is None
    for values in ([], [0, 1], [np.nan, 1], [-1, 2]):
        with pytest.raises(ValueError):
            inverse_weights(values)
    assert regression_scores([], []) == {"mae": None, "r_squared": None}
    assert regression_scores([1, 1], [2, 2])["r_squared"] is None
    assert regression_scores([1, np.inf], [1, 2])["mae"] is None
    assert regression_scores([1, 2], [4, 5])["r_squared"] < 0


def test_resampling_is_reproducible_and_higher_cost_is_a_stress():
    low = run_experiment("resampling_stress", {"value": 0})
    repeated = run_experiment("resampling_stress", {"value": 0})
    high = run_experiment("resampling_stress", {"value": 50})
    pd.testing.assert_frame_equal(low.table, repeated.table)
    assert (high.table["净累计收益"] < low.table["净累计收益"]).all()


def test_complete_teaching_report_round_trip_and_version_guard():
    result = run_experiment("research_archive")
    report = json.loads(result.report)
    encoded = json.dumps(report["input"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert report["input_sha256"] == hashlib.sha256(encoded.encode()).hexdigest()
    assert report["replay_matches"] is True
    assert replay_teaching_manifest(report["input"]) == report["result"]
    assert result.metrics["fee"] == pytest.approx(.01)
    assert result.metrics["cash"] == pytest.approx(989.99)
    assert result.metrics["wealth"] == pytest.approx(1002.99)
    with pytest.raises(ValueError, match="版本"):
        replay_teaching_manifest({**report["input"], "version": "unknown"})
    with pytest.raises(ValueError, match="输入"):
        replay_teaching_manifest({**report["input"], "buy_open": 11})


def test_authored_python_examples_run_and_agree_with_hand_examples():
    # Only trusted, repository-authored examples are executed during verification.
    # The application never exposes eval/exec or accepts user-provided programs.
    outputs = {}
    for course in COURSES:
        scope = {"parameter": course.parameter.default}
        exec(compile(course.code, f"<authored-course:{course.course_id}>", "exec"), scope)
        outputs[course.course_id] = scope
    assert outputs["financial_variables"]["remaining"] == 700
    assert outputs["returns_shift"]["next_open_signal"].iloc[3] == 1
    assert outputs["next_open"]["pnl_at_close"] == -1
    assert outputs["rebalance_cash"]["wealth"] == pytest.approx(1099.796)
    assert outputs["hypothesis_quality"]["missing"] == 1
    assert outputs["benchmark_regression"]["r2"] == pytest.approx(.625)
    archive = outputs["research_archive"]
    report = json.loads(run_experiment("research_archive").report)
    assert archive["fingerprint"] == report["input_sha256"]
    assert archive["original"] == report["result"] and archive["matches"]
