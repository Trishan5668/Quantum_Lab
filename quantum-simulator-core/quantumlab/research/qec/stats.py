"""Statistical summaries for QEC logical-failure experiments.

The default interval is Wilson's score interval.  Clopper-Pearson is provided
for exact coverage, and a zero-failure helper reports an upper bound instead of
pretending that an observed zero rate proves a zero probability.

For correlated or non-stationary shots (for example drifting calibration or
bursty noise), the independent-Bernoulli interval is not automatically valid.
:func:`block_bootstrap_interval` is provided for that case, but using it
requires a documented block length and a coverage check; it is not a default.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
from scipy.stats import beta


class StatisticsError(ValueError):
    """Raised for invalid counts, probabilities, or configuration."""


@dataclass(frozen=True)
class BinomialSummary:
    trials: int
    failures: int
    probability: float
    confidence_level: float
    interval_low: float
    interval_high: float
    method: str = "wilson"

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "trials": self.trials,
            "failures": self.failures,
            "probability": self.probability,
            "confidence_level": self.confidence_level,
            "interval_low": self.interval_low,
            "interval_high": self.interval_high,
            "method": self.method,
        }


@dataclass(frozen=True)
class McNemarResult:
    """Exact McNemar test for paired binary outcomes."""

    both_success: int
    first_only: int
    second_only: int
    both_failure: int
    discordant: int
    statistic: float
    p_value: float
    method: str = "exact_binomial_two_sided"

    def to_dict(self) -> dict[str, int | float | str]:
        return {
            "both_success": self.both_success,
            "first_only": self.first_only,
            "second_only": self.second_only,
            "both_failure": self.both_failure,
            "discordant": self.discordant,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "method": self.method,
        }


def _validate_counts(failures: int, trials: int) -> None:
    if isinstance(failures, bool) or not isinstance(failures, int):
        raise StatisticsError("failures must be an integer")
    if isinstance(trials, bool) or not isinstance(trials, int):
        raise StatisticsError("trials must be an integer")
    if trials <= 0:
        raise StatisticsError("trials must be positive")
    if failures < 0 or failures > trials:
        raise StatisticsError("failures must be in [0, trials]")


def _validate_confidence(confidence_level: float) -> float:
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise StatisticsError("confidence_level must be a real number")
    value = float(confidence_level)
    if not math.isfinite(value) or not 0.0 < value < 1.0:
        raise StatisticsError("confidence_level must be in (0, 1)")
    return value


def z_value(confidence_level: float = 0.95) -> float:
    """Two-sided standard-normal quantile for a confidence level."""
    value = _validate_confidence(confidence_level)
    return NormalDist().inv_cdf(1.0 - (1.0 - value) / 2.0)


def wilson_interval(
    failures: int, trials: int, confidence_level: float = 0.95
) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    _validate_counts(failures, trials)
    cl = _validate_confidence(confidence_level)
    z = z_value(cl)
    p = failures / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
    return (
        max(0.0, center - margin / denominator),
        min(1.0, center + margin / denominator),
    )


def clopper_pearson_interval(
    failures: int, trials: int, confidence_level: float = 0.95
) -> tuple[float, float]:
    """Exact Clopper-Pearson interval (conservative coverage)."""
    _validate_counts(failures, trials)
    cl = _validate_confidence(confidence_level)
    alpha = 1.0 - cl
    low = 0.0 if failures == 0 else float(beta.ppf(alpha / 2.0, failures, trials - failures + 1))
    high = (
        1.0
        if failures == trials
        else float(beta.ppf(1.0 - alpha / 2.0, failures + 1, trials - failures))
    )
    return low, high


def zero_failure_upper_bound(trials: int, confidence_level: float = 0.95) -> float:
    """One-sided upper bound after observing zero failures in ``trials`` shots.

    This is the Clopper-Pearson upper limit ``1 - (1 - cl)^(1/n)``.  The
    result is a bound, not an estimate, and callers must label it as such.
    """
    if isinstance(trials, bool) or not isinstance(trials, int) or trials <= 0:
        raise StatisticsError("trials must be a positive integer")
    cl = _validate_confidence(confidence_level)
    return float(1.0 - (1.0 - cl) ** (1.0 / trials))


def summarize(
    failures: int, trials: int, confidence_level: float = 0.95
) -> BinomialSummary:
    """Wilson summary (backward-compatible default)."""
    low, high = wilson_interval(failures, trials, confidence_level)
    return BinomialSummary(
        trials=trials,
        failures=failures,
        probability=failures / trials,
        confidence_level=confidence_level,
        interval_low=low,
        interval_high=high,
        method="wilson",
    )


def summarize_with_method(
    failures: int,
    trials: int,
    confidence_level: float = 0.95,
    *,
    method: str = "wilson",
) -> BinomialSummary:
    """Summarize with ``wilson`` or ``clopper_pearson``."""
    if method == "wilson":
        low, high = wilson_interval(failures, trials, confidence_level)
    elif method == "clopper_pearson":
        low, high = clopper_pearson_interval(failures, trials, confidence_level)
    else:
        raise StatisticsError(f"unknown interval method {method!r}")
    return BinomialSummary(
        trials=trials,
        failures=failures,
        probability=failures / trials,
        confidence_level=confidence_level,
        interval_low=low,
        interval_high=high,
        method=method,
    )


def difference_ci_newcombe(
    failures_a: int,
    trials_a: int,
    failures_b: int,
    trials_b: int,
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Newcombe hybrid score interval for ``p_a - p_b`` (independent samples)."""
    _validate_counts(failures_a, trials_a)
    _validate_counts(failures_b, trials_b)
    cl = _validate_confidence(confidence_level)
    pa = failures_a / trials_a
    pb = failures_b / trials_b
    la, ua = wilson_interval(failures_a, trials_a, cl)
    lb, ub = wilson_interval(failures_b, trials_b, cl)
    diff = pa - pb
    lower = diff - math.sqrt((pa - la) ** 2 + (ub - pb) ** 2)
    upper = diff + math.sqrt((ua - pa) ** 2 + (pb - lb) ** 2)
    return max(-1.0, lower), min(1.0, upper)


def mcnemar_exact(
    first_only: int,
    second_only: int,
    *,
    both_success: int = 0,
    both_failure: int = 0,
) -> McNemarResult:
    """Exact two-sided McNemar test on paired binary outcomes.

    ``first_only`` counts pairs where only the first method failed;
    ``second_only`` counts the converse.  Under the null hypothesis the
    discordant failures are Binomial(n, 1/2).
    """
    for name, value in (
        ("first_only", first_only),
        ("second_only", second_only),
        ("both_success", both_success),
        ("both_failure", both_failure),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StatisticsError(f"{name} must be a non-negative integer")
    discordant = first_only + second_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, k) for k in range(0, min(first_only, second_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2.0 * tail)
    statistic = 0.0 if discordant == 0 else (first_only - second_only) ** 2 / discordant
    return McNemarResult(
        both_success=both_success,
        first_only=first_only,
        second_only=second_only,
        both_failure=both_failure,
        discordant=discordant,
        statistic=float(statistic),
        p_value=float(p_value),
    )


def bootstrap_interval(
    data: Sequence[float],
    statistic: Callable[[np.ndarray], float],
    *,
    n_bootstrap: int = 2000,
    confidence_level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap interval for an i.i.d. statistic."""
    values = np.asarray(data, dtype=np.float64)
    if values.ndim != 1 or values.size == 0:
        raise StatisticsError("data must be a non-empty one-dimensional sequence")
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap < 100:
        raise StatisticsError("n_bootstrap must be an integer >= 100")
    cl = _validate_confidence(confidence_level)
    rng = np.random.default_rng(seed)
    estimates = np.empty(n_bootstrap, dtype=np.float64)
    n = values.size
    for index in range(n_bootstrap):
        sample = values[rng.integers(0, n, size=n)]
        estimates[index] = statistic(sample)
    alpha = (1.0 - cl) / 2.0
    return (
        float(np.quantile(estimates, alpha)),
        float(np.quantile(estimates, 1.0 - alpha)),
    )


def block_bootstrap_interval(
    data: Sequence[float],
    block_size: int,
    statistic: Callable[[np.ndarray], float],
    *,
    n_bootstrap: int = 2000,
    confidence_level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Circular block-bootstrap interval for serially correlated shots.

    ``block_size`` must be chosen from domain knowledge or a pilot study and
    recorded with the result.  This routine does not prove that the chosen
    block length captures the dependence; that requires a coverage study.
    """
    values = np.asarray(data, dtype=np.float64)
    if values.ndim != 1 or values.size == 0:
        raise StatisticsError("data must be a non-empty one-dimensional sequence")
    if isinstance(block_size, bool) or not isinstance(block_size, int) or block_size < 1:
        raise StatisticsError("block_size must be a positive integer")
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap < 100:
        raise StatisticsError("n_bootstrap must be an integer >= 100")
    if block_size > values.size:
        raise StatisticsError("block_size must not exceed the number of observations")
    cl = _validate_confidence(confidence_level)
    n = values.size
    n_blocks = int(math.ceil(n / block_size))
    starts = np.arange(n)
    rng = np.random.default_rng(seed)
    estimates = np.empty(n_bootstrap, dtype=np.float64)
    for index in range(n_bootstrap):
        chosen = rng.choice(starts, size=n_blocks, replace=True)
        pieces = [np.roll(values, -int(start))[:block_size] for start in chosen]
        sample = np.concatenate(pieces)[:n]
        estimates[index] = statistic(sample)
    alpha = (1.0 - cl) / 2.0
    return (
        float(np.quantile(estimates, alpha)),
        float(np.quantile(estimates, 1.0 - alpha)),
    )


def mean_statistic(sample: np.ndarray) -> float:
    return float(np.mean(sample))
