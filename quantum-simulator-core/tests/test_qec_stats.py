from __future__ import annotations

import math

import numpy as np
import pytest

from quantumlab.research.qec.stats import (
    StatisticsError,
    block_bootstrap_interval,
    bootstrap_interval,
    clopper_pearson_interval,
    difference_ci_newcombe,
    mcnemar_exact,
    mean_statistic,
    summarize,
    summarize_with_method,
    wilson_interval,
    z_value,
    zero_failure_upper_bound,
)


def test_wilson_interval_known_values() -> None:
    assert wilson_interval(84, 10000) == pytest.approx(
        (0.006790405766700768, 0.01038714143134846), rel=1e-12
    )
    low, high = wilson_interval(0, 100)
    assert low == 0.0
    assert high == pytest.approx(0.03699349820698566, rel=1e-12)
    low, high = wilson_interval(100, 100)
    assert high == 1.0
    assert low == pytest.approx(0.9630065017930143, rel=1e-10)


def test_wilson_interval_general_confidence() -> None:
    low95, high95 = wilson_interval(50, 100, 0.95)
    low90, high90 = wilson_interval(50, 100, 0.90)
    assert low90 > low95 and high90 < high95
    assert low95 < 0.5 < high95
    assert z_value(0.95) == pytest.approx(1.959963984540054)


def test_clopper_pearson_interval_exact_boundaries() -> None:
    low, high = clopper_pearson_interval(0, 100)
    assert low == 0.0
    assert high == pytest.approx(0.03621669264517641, rel=1e-12)
    low, high = clopper_pearson_interval(100, 100)
    assert high == 1.0
    assert low == pytest.approx(0.9637833073548235, rel=1e-12)
    cp = clopper_pearson_interval(5, 100)
    w = wilson_interval(5, 100)
    assert cp[0] <= w[0] and cp[1] >= w[1]


def test_zero_failure_upper_bound_is_not_zero() -> None:
    assert zero_failure_upper_bound(1000) == pytest.approx(1.0 - 0.05 ** 0.001, rel=1e-12)
    assert zero_failure_upper_bound(10000) < zero_failure_upper_bound(1000)


def test_interval_rejects_invalid_counts() -> None:
    for failures, trials in [(-1, 10), (11, 10), (0, 0), (True, 10), (0, 1.5)]:
        with pytest.raises(StatisticsError):
            wilson_interval(failures, trials)  # type: ignore[arg-type]
    with pytest.raises(StatisticsError):
        wilson_interval(0, 10, 1.0)
    with pytest.raises(StatisticsError):
        clopper_pearson_interval(0, 10, 0.0)


def test_summarize_and_method_equivalence() -> None:
    summary = summarize(3, 100)
    assert summary.probability == pytest.approx(0.03)
    assert summary.method == "wilson"
    cp = summarize_with_method(3, 100, method="clopper_pearson")
    assert cp.interval_low < summary.interval_low
    assert cp.interval_high > summary.interval_high
    with pytest.raises(StatisticsError):
        summarize_with_method(3, 100, method="normal")


def test_difference_ci_excludes_zero_for_large_separation() -> None:
    low, high = difference_ci_newcombe(0, 1000, 100, 1000)
    assert high < 0.0  # p_a - p_b is negative and the interval excludes zero


def test_difference_ci_contains_zero_for_identical_rates() -> None:
    low, high = difference_ci_newcombe(10, 1000, 10, 1000)
    assert low < 0.0 < high


def test_mcnemar_exact() -> None:
    result = mcnemar_exact(10, 2)
    assert result.discordant == 12
    assert result.p_value == pytest.approx(0.03857421875)
    assert result.statistic == pytest.approx(64 / 12)
    result = mcnemar_exact(0, 0)
    assert result.p_value == 1.0
    assert result.statistic == 0.0
    with pytest.raises(StatisticsError):
        mcnemar_exact(-1, 2)


def test_bootstrap_intervals_are_deterministic_and_bracketed() -> None:
    data = [0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0] * 10
    first = bootstrap_interval(data, mean_statistic, n_bootstrap=300, seed=7)
    second = bootstrap_interval(data, mean_statistic, n_bootstrap=300, seed=7)
    assert first == second
    assert 0.0 <= first[0] <= first[1] <= 1.0
    assert first[0] <= np.mean(data) <= first[1]
    block = block_bootstrap_interval(data, 5, mean_statistic, n_bootstrap=300, seed=7)
    assert 0.0 <= block[0] <= block[1] <= 1.0
    with pytest.raises(StatisticsError):
        bootstrap_interval([], mean_statistic)
    with pytest.raises(StatisticsError):
        block_bootstrap_interval([0, 1], 3, mean_statistic)
    with pytest.raises(StatisticsError):
        block_bootstrap_interval([0, 1], 1, mean_statistic, n_bootstrap=10)


def test_zero_failure_bound_interpretation() -> None:
    bound = zero_failure_upper_bound(10000, 0.95)
    assert 0.0 < bound < 0.001
    assert math.isfinite(bound)
