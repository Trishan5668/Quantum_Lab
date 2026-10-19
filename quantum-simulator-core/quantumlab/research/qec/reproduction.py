"""Pre-declared reproduction of a published QEC threshold.

The target file fixes distances, error probabilities, shot counts, seeds, the
acceptance band, and the decision rule *before* execution.  The analysis code
below implements that rule mechanically; it does not search for a favourable
grid or tolerance.  Results are labeled REPRODUCED, FAILED, or INCONCLUSIVE.
"""

from __future__ import annotations

import hashlib
import importlib.util
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from quantumlab.research.qec.artifacts import (
    ArtifactRun,
    canonical_json,
    git_state,
    sha256_bytes,
    utc_now,
)
from quantumlab.research.qec.decoders.mwpm import DetectorMWPMDecoder
from quantumlab.research.qec.noise import CircuitLevelNoiseModel
from quantumlab.research.qec.stats import (
    BinomialSummary,
    difference_ci_newcombe,
    summarize_with_method,
)


class ReproductionError(RuntimeError):
    """Raised for malformed targets or unavailable dependencies."""


@dataclass(frozen=True)
class ReproductionSpecification:
    raw: dict[str, Any]
    source_path: str
    source_sha256: str


@dataclass(frozen=True)
class ThresholdPoint:
    distance: int
    p: float
    shots: int
    seed: int
    failures: int
    summary: BinomialSummary
    dem_sha256: str
    circuit_sha256: str
    stage: str

    def to_dict(self) -> dict[str, Any]:
        payload = self.summary.to_dict()
        payload.update(
            {
                "distance": self.distance,
                "p": self.p,
                "shots": self.shots,
                "seed": self.seed,
                "dem_sha256": self.dem_sha256,
                "circuit_sha256": self.circuit_sha256,
                "stage": self.stage,
            }
        )
        return payload


def _load_target(path: Path) -> dict[str, Any]:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ReproductionError("reproduction target root must be a mapping")
    required = {
        "name",
        "reference",
        "model",
        "coarse",
        "refinement",
        "acceptance",
        "statistics",
    }
    missing = required - raw.keys()
    if missing:
        raise ReproductionError(f"target missing sections: {sorted(missing)}")
    for section in ("coarse", "refinement"):
        block = raw[section]
        if not isinstance(block, dict):
            raise ReproductionError(f"{section} must be a mapping")
        for key in ("p", "shots", "distances"):
            if key not in block:
                raise ReproductionError(f"{section}.{key} is required")
        if not isinstance(block["p"], list) or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in block["p"]
        ):
            raise ReproductionError(f"{section}.p must be a list of numbers")
        if not isinstance(block["shots"], int) or block["shots"] <= 0:
            raise ReproductionError(f"{section}.shots must be a positive integer")
        if not isinstance(block["distances"], list) or not all(
            isinstance(value, int) and value >= 3 and value % 2 == 1
            for value in block["distances"]
        ):
            raise ReproductionError(f"{section}.distances must be odd integers >= 3")
        if any(not 0.0 < float(value) < 1.0 for value in block["p"]):
            raise ReproductionError(f"{section}.p must lie in (0, 1)")
    acceptance = raw["acceptance"]
    if not isinstance(acceptance, dict):
        raise ReproductionError("acceptance must be a mapping")
    band = acceptance.get("threshold_band")
    if (
        not isinstance(band, list)
        or len(band) != 2
        or not all(isinstance(value, (int, float)) for value in band)
        or not 0.0 < float(band[0]) < float(band[1]) < 1.0
    ):
        raise ReproductionError("acceptance.threshold_band must be [low, high]")
    if not isinstance(acceptance.get("master_seed"), int):
        raise ReproductionError("acceptance.master_seed must be an integer")
    return raw


def _require_tools() -> None:
    for package in ("stim", "pymatching"):
        if importlib.util.find_spec(package) is None:
            raise ReproductionError(
                f"{package} is required for the threshold reproduction; "
                'install the "research" extra'
            )


def _run_point(
    distance: int,
    probability: float,
    shots: int,
    master_seed: int,
    stage_code: int,
    stage: str,
) -> tuple[ThresholdPoint, np.ndarray]:
    sequence = np.random.SeedSequence(
        [master_seed, distance, int(round(probability * 1_000_000)), stage_code]
    )
    seed = int(sequence.generate_state(1, dtype=np.uint32)[0])
    model = CircuitLevelNoiseModel.uniform(probability)
    circuit = model.stim_circuit(
        distance, distance, task="surface_code:rotated_memory_z"
    )
    error_model = circuit.detector_error_model(decompose_errors=True)
    decoder = DetectorMWPMDecoder(error_model)
    sampler = circuit.compile_detector_sampler(seed=seed)
    detectors, observables = sampler.sample(
        shots=shots, separate_observables=True, append_observables=False
    )
    predictions = decoder.decode_batch(detectors)
    observed = np.asarray(observables).reshape(shots, -1)
    predicted = np.asarray(predictions).reshape(shots, -1)
    failure_vector = np.any(predicted != observed, axis=1)
    failures = int(np.count_nonzero(failure_vector))
    summary = summarize_with_method(
        failures, shots, confidence_level=0.95, method="wilson"
    )
    point = ThresholdPoint(
        distance=distance,
        p=float(probability),
        shots=shots,
        seed=seed,
        failures=failures,
        summary=summary,
        dem_sha256=hashlib.sha256(str(error_model).encode("utf-8")).hexdigest(),
        circuit_sha256=hashlib.sha256(str(circuit).encode("utf-8")).hexdigest(),
        stage=stage,
    )
    return point, failure_vector


def _find(
    points: list[ThresholdPoint], *, stage: str, distance: int, probability: float
) -> ThresholdPoint:
    matches = [
        point
        for point in points
        if point.stage == stage
        and point.distance == distance
        and abs(point.p - probability) < 1e-15
    ]
    if len(matches) != 1:
        raise ReproductionError(
            f"expected one {stage} point for d={distance}, p={probability}; "
            f"found {len(matches)}"
        )
    return matches[0]


def _analyse(target: dict[str, Any], points: list[ThresholdPoint]) -> dict[str, Any]:
    coarse = target["coarse"]
    refinement = target["refinement"]
    acceptance = target["acceptance"]
    band_low, band_high = (float(value) for value in acceptance["threshold_band"])
    refine_ps = sorted(float(value) for value in refinement["p"])

    scores = {}
    differences = {}
    for probability in refine_ps:
        d3 = _find(points, stage="refinement", distance=3, probability=probability)
        d5 = _find(points, stage="refinement", distance=5, probability=probability)
        low, high = difference_ci_newcombe(
            d3.failures, d3.shots, d5.failures, d5.shots, 0.95
        )
        scores[probability] = d3.summary.probability - d5.summary.probability
        differences[probability] = {
            "difference": scores[probability],
            "interval_low": low,
            "interval_high": high,
            "interval_excludes_zero": bool(low > 0.0 or high < 0.0),
            "d3_estimate": d3.summary.probability,
            "d5_estimate": d5.summary.probability,
        }

    bracket: list[float] | None = None
    for left, right in zip(refine_ps, refine_ps[1:], strict=False):
        if scores[left] > 0.0 and scores[right] < 0.0:
            bracket = [left, right]
            break

    within_band = (
        bracket is not None and bracket[0] <= band_high and bracket[1] >= band_low
    )

    below = _coarse_ordering(points, coarse, 0.004)
    above = _coarse_ordering(points, coarse, 0.010)
    below_evaluable = below is not None and len(below) == 3
    above_evaluable = above is not None and len(above) == 3
    below_pass = bool(
        below_evaluable and below is not None and below[0] > below[1] > below[2]
    )
    above_pass = bool(
        above_evaluable and above is not None and above[0] < above[1] < above[2]
    )

    significant = False
    if bracket is not None:
        selected_left = differences[bracket[0]]
        selected_right = differences[bracket[1]]
        significant = bool(
            selected_left["interval_excludes_zero"]
            and selected_right["interval_excludes_zero"]
            and selected_left["difference"] > 0.0
            and selected_right["difference"] < 0.0
        )

    criteria = [
        {
            "id": "bracket_exists",
            "passed": bracket is not None,
            "detail": f"bracket={bracket}",
        },
        {
            "id": "bracket_in_predeclared_band",
            "passed": within_band,
            "detail": f"band=[{band_low}, {band_high}]",
        },
        {
            "id": "refinement_significant",
            "passed": significant,
            "detail": "Newcombe 95% intervals exclude zero with opposite signs",
        },
        {
            "id": "ordering_below_threshold",
            "passed": below_pass,
            "evaluable": below_evaluable,
            "detail": f"LER(d3,d5,d7) at p=0.004 = {below}",
        },
        {
            "id": "ordering_above_threshold",
            "passed": above_pass,
            "evaluable": above_evaluable,
            "detail": f"LER(d3,d5,d7) at p=0.010 = {above}",
        },
    ]

    if bracket is None:
        status = "INCONCLUSIVE"
        rationale = "No sign change was observed between adjacent refinement points."
    elif not (below_evaluable and above_evaluable):
        status = "INCONCLUSIVE"
        rationale = (
            "The distance-ordering criteria could not be evaluated because the "
            "coarse grid does not contain d=3, 5, and 7 at the declared points."
        )
    elif not within_band or not below_pass or not above_pass:
        status = "FAILED"
        rationale = (
            "The measured bracket or distance ordering contradicts the "
            "pre-declared acceptance criteria."
        )
    elif not significant:
        status = "INCONCLUSIVE"
        rationale = (
            "The point-estimate bracket lies in the declared band, but the "
            "uncertainty intervals do not establish the crossing with the "
            "pre-declared confidence."
        )
    else:
        status = "REPRODUCED"
        rationale = (
            "The measured crossing is inside the pre-declared literature band, "
            "is statistically resolved at the refinement points, and both "
            "distance-ordering checks pass for the declared model."
        )
    return {
        "status": status,
        "rationale": rationale,
        "bracket": bracket,
        "within_predeclared_band": within_band,
        "scores": scores,
        "differences": differences,
        "criteria": criteria,
        "predeclared_band": [band_low, band_high],
        "claim_label": {
            "REPRODUCED": "REPRODUCED_WITHIN_DECLARED_MODEL",
            "FAILED": "FAILED",
            "INCONCLUSIVE": "INCONCLUSIVE",
        }[status],
        "scope": (
            "Stim circuit-level depolarizing model with PyMatching MWPM; "
            "not a hardware result and not Fowler et al.'s exact gate model."
        ),
    }


def _coarse_ordering(
    points: list[ThresholdPoint], coarse: dict[str, Any], probability: float
) -> tuple[float, ...] | None:
    distances = sorted(int(value) for value in coarse["distances"])
    if probability not in [float(value) for value in coarse["p"]]:
        return None
    values = []
    for distance in distances:
        point = _find(
            points, stage="coarse", distance=distance, probability=probability
        )
        values.append(point.summary.probability)
    return tuple(values)


def _write_report(
    run: ArtifactRun, target: dict[str, Any], summary: dict[str, Any]
) -> None:
    analysis = summary["analysis"]
    lines = [
        f"# Reproduction: {target['name']}",
        "",
        f"- Experiment ID: `{run.experiment_id}`",
        f"- Status: **{analysis['status']}** (`{analysis['claim_label']}`)",
        f"- Rationale: {analysis['rationale']}",
        f"- Pre-declared band: {analysis['predeclared_band']}",
        f"- Measured bracket: {analysis['bracket']}",
        "",
        "## Reference result",
        "",
        target["reference"]["description"],
        "",
        "## Model under test",
        "",
        target["model"]["description"],
        "",
        "## Results",
        "",
        "| Stage | d | p | Shots | Failures | LER | Wilson 95% CI |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for point in summary["results"]:
        lines.append(
            f"| {point['stage']} | {point['distance']} | {point['p']:.4f} | "
            f"{point['shots']} | {point['failures']} | "
            f"{point['probability']:.6g} | "
            f"[{point['interval_low']:.6g}, {point['interval_high']:.6g}] |"
        )
    lines.extend(
        [
            "",
            "## Pre-declared criteria",
            "",
            "| Criterion | Result | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for criterion in analysis["criteria"]:
        lines.append(
            f"| {criterion['id']} | {'PASS' if criterion['passed'] else 'FAIL'} | "
            f"{criterion['detail']} |"
        )
    lines.extend(
        [
            "",
            "## Claim labels",
            "",
            "| Claim | Label |",
            "| --- | --- |",
            "| Declared model reproduces the published threshold band | "
            f"{analysis['claim_label']} |",
            "| Native QuantumLab circuit-level sampler | NOT_CLAIMED (Stim used) |",
            "| Hardware behavior | NOT_CLAIMED |",
            "| Novelty or superiority | NOT_CLAIMED |",
            "",
            "## Limitations and disclosures",
            "",
            "- The model is Stim's standard circuit-level depolarizing model, not "
            "Fowler et al.'s exact gate-level error placement.",
            "- Threshold values are decoder- and model-dependent; the quoted band "
            "is a literature band, not a universal constant.",
            "- The exploratory pilot disclosed in the target is not evidence.",
            "- Raw per-shot logical outcomes are stored compressed in "
            "`outcomes.npz`; circuits and detector error models are identified by "
            "SHA-256 in the summary.",
            "",
        ]
    )
    run.write_text("report.md", "\n".join(lines))


def run_reproduction_target(
    target_path: str | Path,
    output_root: str | Path,
    *,
    experiment_id: str | None = None,
) -> dict[str, Any]:
    _require_tools()
    study_start_utc = utc_now()
    study_start = time.monotonic()
    path = Path(target_path)
    try:
        raw = _load_target(path)
    except Exception as exc:
        if isinstance(exc, ReproductionError):
            raise
        raise ReproductionError(f"could not parse target: {exc}") from exc
    master_seed = int(raw["acceptance"]["master_seed"])
    points: list[ThresholdPoint] = []
    outcomes: dict[str, np.ndarray] = {}
    stages = [
        ("coarse", raw["coarse"], 0),
        ("refinement", raw["refinement"], 1),
    ]
    for stage_name, block, stage_code in stages:
        for distance in sorted(int(value) for value in block["distances"]):
            for probability in sorted(float(value) for value in block["p"]):
                point, vector = _run_point(
                    distance,
                    probability,
                    int(block["shots"]),
                    master_seed,
                    stage_code,
                    stage_name,
                )
                points.append(point)
                outcomes[f"{stage_name}_d{distance}_p{int(round(probability * 1e6))}"] = (
                    np.packbits(vector.astype(np.uint8))
                )
    analysis = _analyse(raw, points)
    results = [point.to_dict() for point in points]
    spec = ReproductionSpecification(
        raw=raw,
        source_path=str(path),
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    provenance = git_state()
    with ArtifactRun(
        Path(output_root),
        "reproduction",
        cast(Any, spec),
        experiment_id,
    ) as run:
        try:
            np.savez_compressed(
                run.path("outcomes.npz"),
                **cast(dict[str, Any], outcomes),
            )
            summary = {
                "target": raw,
                "config_hash": sha256_bytes(canonical_json(raw).encode("utf-8")),
                "results": results,
                "analysis": analysis,
                "status": "COMPLETED",
                "start_utc": study_start_utc,
                "runtime_seconds": time.monotonic() - study_start,
                "provenance": {
                    "source_revision": provenance["source_revision"],
                    "dirty": provenance["dirty"],
                    "dirty_status_sha256": provenance["dirty_status_sha256"],
                },
                "notices": [
                    "Integrity verification does not establish scientific validity.",
                    "Reproduction is limited to the declared model class.",
                    "The exploratory pilot is not evidence.",
                ],
            }
            _write_report(run, raw, summary)
            directory = run.commit(summary)
        except BaseException as exc:
            run.abort(exc)
            raise
    return {
        "status": analysis["status"],
        "claim_label": analysis["claim_label"],
        "bracket": analysis["bracket"],
        "artifact_dir": str(directory),
        "analysis": analysis,
    }


def summarize_existing_target(path: str | Path) -> dict[str, Any]:
    """Read a targets file without running (used by tests and docs checks)."""
    return _load_target(Path(path))
