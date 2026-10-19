"""Statistical summaries for Bernoulli logical-failure experiments."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BinomialSummary:
    trials: int
    failures: int
    probability: float
    confidence_level: float
    interval_low: float
    interval_high: float


def wilson_interval(failures: int, trials: int, confidence_level: float = 0.95) -> tuple[float, float]:
    if trials <= 0 or not 0 <= failures <= trials:
        raise ValueError("failures must be between zero and positive trials")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")
    z = 1.959963984540054
    if confidence_level != 0.95:
        raise ValueError("only the 0.95 Wilson interval is currently supported")
    p = failures / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
    return (max(0.0, center - margin / denominator), min(1.0, center + margin / denominator))


def summarize(failures: int, trials: int, confidence_level: float = 0.95) -> BinomialSummary:
    low, high = wilson_interval(failures, trials, confidence_level)
    return BinomialSummary(trials, failures, failures / trials, confidence_level, low, high)
