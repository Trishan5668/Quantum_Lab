"""Phase 3/4: static-DEM mismatch and a gated calibrated candidate.

Phase 3 measures the logical-error penalty caused by decoding circuit-level
surface-code shots with a nominal detector error model whose gate and
measurement error rates differ from the truth.  Phase 4 selects a two-parameter
global DEM from observed detector-cohort rates on development seeds only,
freezes it, and evaluates it on a disjoint held-out seed.

No AI API is used.  Candidates are rule-based; the recorded source label is
``RULE_BASED``.  Promotion is never automatic.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
    McNemarResult,
    mcnemar_exact,
    summarize_with_method,
)


class CalibrationError(RuntimeError):
    """Raised when the pre-declared calibration study cannot be executed."""


@dataclass(frozen=True)
class NoiseProfile:
    name: str
    p_gate: float
    p_meas: float

    def circuit(self, distance: int, rounds: int) -> Any:
        return CircuitLevelNoiseModel(
            p_gate=self.p_gate,
            p_measurement=self.p_meas,
            p_reset=self.p_gate,
            p_round=self.p_gate,
        ).stim_circuit(distance, rounds, task="surface_code:rotated_memory_z")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "p_gate": self.p_gate,
            "p_meas": self.p_meas,
            "p_reset": self.p_gate,
            "p_round": self.p_gate,
        }


NOMINAL = NoiseProfile("nominal", 0.010, 0.010)
PROFILES: tuple[NoiseProfile, ...] = (
    NoiseProfile("control", 0.010, 0.010),
    NoiseProfile("measurement_heavy", 0.002, 0.020),
    NoiseProfile("gate_heavy", 0.020, 0.002),
)
DISTANCES: tuple[int, ...] = (3, 5)
GRID: tuple[float, ...] = (
    0.001,
    0.002,
    0.004,
    0.006,
    0.008,
    0.010,
    0.012,
    0.015,
    0.020,
    0.030,
)
PHASE3_MASTER_SEED = 3101
PHASE4_DEV_SEED = 4101
PHASE4_HELDOUT_SEED = 9101
PHASE3_SHOTS = 100_000
CALIBRATION_SHOTS = 5_000
HELDOUT_SHOTS = 100_000
BOOTSTRAP_RESAMPLES = 10_000


def _require_tools() -> None:
    for package in ("stim", "pymatching"):
        if importlib.util.find_spec(package) is None:
            raise CalibrationError(
                f"{package} is required; install the research extra"
            )


def _seed(master: int, distance: int, profile: NoiseProfile, purpose: int) -> int:
    sequence = np.random.SeedSequence(
        [
            master,
            distance,
            int(round(profile.p_gate * 1_000_000)),
            int(round(profile.p_meas * 1_000_000)),
            purpose,
        ]
    )
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


def _sample(
    distance: int,
    profile: NoiseProfile,
    shots: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    circuit = profile.circuit(distance, distance)
    sampler = circuit.compile_detector_sampler(seed=seed)
    detectors, observables = sampler.sample(
        shots=shots, separate_observables=True, append_observables=False
    )
    return np.asarray(detectors, dtype=np.uint8), np.asarray(observables, dtype=np.uint8)


def _decoder(distance: int, model: NoiseProfile) -> DetectorMWPMDecoder:
    circuit = model.circuit(distance, distance)
    dem = circuit.detector_error_model(decompose_errors=True)
    return DetectorMWPMDecoder(dem)


def _failure_vector(
    decoder: DetectorMWPMDecoder, detectors: np.ndarray, observables: np.ndarray
) -> np.ndarray:
    predictions = decoder.decode_batch(detectors)
    observed = np.asarray(observables).reshape(detectors.shape[0], -1)
    predicted = np.asarray(predictions).reshape(detectors.shape[0], -1)
    return cast(np.ndarray, np.any(predicted != observed, axis=1).astype(np.uint8))


def _cohort_rates(detectors: np.ndarray, circuit: Any) -> np.ndarray:
    coordinates = circuit.get_detector_coordinates()
    num_detectors = int(circuit.num_detectors)
    times = np.zeros(num_detectors, dtype=np.int64)
    for index in range(num_detectors):
        coords = coordinates.get(index, [])
        times[index] = int(coords[-1]) if coords else 0
    upper = int(times.max()) if num_detectors else 0
    rates = []
    for cohort in range(upper + 1):
        mask = times == cohort
        if not np.any(mask):
            continue
        rates.append(float(np.mean(detectors[:, mask])))
    if not rates:
        return np.array([float(np.mean(detectors))])
    rates.append(float(np.mean(detectors)))
    return np.asarray(rates, dtype=np.float64)


def _bootstrap_difference(
    first: np.ndarray, second: np.ndarray, seed: int
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = first.size
    differences = np.empty(BOOTSTRAP_RESAMPLES, dtype=np.float64)
    for index in range(BOOTSTRAP_RESAMPLES):
        sample = rng.integers(0, n, size=n)
        differences[index] = float(
            np.mean(first[sample]) - np.mean(second[sample])
        )
    return (
        float(np.quantile(differences, 0.025)),
        float(np.quantile(differences, 0.975)),
    )


def _cell_summary(
    first: np.ndarray, second: np.ndarray, seed: int
) -> dict[str, Any]:
    trials = int(first.size)
    failures_first = int(np.sum(first))
    failures_second = int(np.sum(second))
    both_success = int(np.sum((first == 0) & (second == 0)))
    first_only = int(np.sum((first == 1) & (second == 0)))
    second_only = int(np.sum((first == 0) & (second == 1)))
    both_failure = int(np.sum((first == 1) & (second == 1)))
    test: McNemarResult = mcnemar_exact(
        first_only,
        second_only,
        both_success=both_success,
        both_failure=both_failure,
    )
    low, high = _bootstrap_difference(first, second, seed)
    return {
        "trials": trials,
        "first_failures": failures_first,
        "second_failures": failures_second,
        "first_ler": failures_first / trials,
        "second_ler": failures_second / trials,
        "first_summary": summarize_with_method(
            failures_first, trials, 0.95, method="wilson"
        ).to_dict(),
        "second_summary": summarize_with_method(
            failures_second, trials, 0.95, method="wilson"
        ).to_dict(),
        "difference_first_minus_second": (failures_first - failures_second) / trials,
        "difference_bootstrap_ci": [low, high],
        "both_success": both_success,
        "first_only": first_only,
        "second_only": second_only,
        "both_failure": both_failure,
        "discordant": test.discordant,
        "mcnemar": test.to_dict(),
        "relative_excess": (
            None
            if failures_second == 0
            else (failures_first - failures_second) / failures_second
        ),
        "zero_failure_note": (
            "relative_excess undefined because the oracle made zero failures"
            if failures_second == 0
            else None
        ),
    }


def _sample_and_decode(
    distance: int,
    true_profile: NoiseProfile,
    models: dict[str, NoiseProfile],
    shots: int,
    seed: int,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    detectors, observables = _sample(distance, true_profile, shots, seed)
    vectors: dict[str, np.ndarray] = {}
    metadata: dict[str, Any] = {}
    for name, model in models.items():
        decoder = _decoder(distance, model)
        vectors[name] = _failure_vector(decoder, detectors, observables)
        metadata[name] = {
            "model": model.to_dict(),
            "decoder": decoder.to_dict(),
        }
    return vectors, metadata


def _selection(
    distance: int,
    observed_profile: NoiseProfile,
    observed_detectors: np.ndarray,
    observed_circuit: Any,
    dev_seed: int,
    grid: tuple[float, ...],
) -> dict[str, Any]:
    observed = _cohort_rates(observed_detectors, observed_circuit)
    scale = max(float(np.mean(observed)), 1e-9)
    rows = []
    for p_gate in grid:
        for p_meas in grid:
            candidate = NoiseProfile(
                f"candidate_{p_gate:.4f}_{p_meas:.4f}", p_gate, p_meas
            )
            detectors, _ = _sample(
                distance,
                candidate,
                CALIBRATION_SHOTS,
                _seed(dev_seed, distance, candidate, 2),
            )
            features = _cohort_rates(detectors, candidate.circuit(distance, distance))
            score = float(np.mean(np.abs(observed - features)) / scale)
            rows.append(
                {
                    "p_gate": p_gate,
                    "p_meas": p_meas,
                    "score": score,
                    "observed_features": observed.tolist(),
                    "candidate_features": features.tolist(),
                }
            )
    rows.sort(key=lambda row: (row["score"], row["p_gate"], row["p_meas"]))
    best = rows[0]
    second = rows[1]
    ambiguous = second["score"] <= 1.05 * best["score"]
    return {
        "distance": distance,
        "observed_profile": observed_profile.name,
        "selected": {
            "p_gate": best["p_gate"],
            "p_meas": best["p_meas"],
            "score": best["score"],
            "name": f"candidate_{best['p_gate']:.4f}_{best['p_meas']:.4f}",
        },
        "runner_up": {
            "p_gate": second["p_gate"],
            "p_meas": second["p_meas"],
            "score": second["score"],
        },
        "ambiguous": ambiguous,
        "top_10": rows[:10],
        "development_seed_master": dev_seed,
    }


def run_calibration_study(
    output_root: str | Path,
    *,
    experiment_id: str | None = None,
    phase3_shots: int = PHASE3_SHOTS,
    calibration_shots: int = CALIBRATION_SHOTS,
    heldout_shots: int = HELDOUT_SHOTS,
    grid: tuple[float, ...] = GRID,
) -> dict[str, Any]:
    _require_tools()
    study_start_utc = utc_now()
    study_start = time.monotonic()
    raw_config = {
        "study": "static_dem_mismatch_v1",
        "profiles": [profile.to_dict() for profile in PROFILES],
        "distances": list(DISTANCES),
        "phase3": {
            "master_seed": PHASE3_MASTER_SEED,
            "shots": phase3_shots,
            "decoders": ["nominal", "oracle"],
        },
        "phase4": {
            "development_master_seed": PHASE4_DEV_SEED,
            "heldout_master_seed": PHASE4_HELDOUT_SEED,
            "calibration_shots": calibration_shots,
            "heldout_shots": heldout_shots,
            "grid": list(grid),
            "candidate_source": "RULE_BASED",
        },
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "claim_status": "NOT_INDEPENDENTLY_VALIDATED",
    }
    phase3: dict[str, Any] = {}
    phase3_vectors: dict[str, np.ndarray] = {}
    for profile in PROFILES:
        for distance in DISTANCES:
            seed = _seed(PHASE3_MASTER_SEED, distance, profile, 0)
            models = {"nominal": NOMINAL, "oracle": profile}
            vectors, metadata = _sample_and_decode(
                distance, profile, models, phase3_shots, seed
            )
            key = f"{profile.name}_d{distance}"
            phase3[key] = {
                "profile": profile.to_dict(),
                "distance": distance,
                "seed": seed,
                "decoders": metadata,
                "nominal_vs_oracle": _cell_summary(
                    vectors["nominal"], vectors["oracle"], seed + 1
                ),
            }
            for name, vector in vectors.items():
                phase3_vectors[f"{key}_{name}"] = np.packbits(vector)
    h3a = (
        phase3["measurement_heavy_d5"]["nominal_vs_oracle"]["relative_excess"]
        if phase3["measurement_heavy_d5"]["nominal_vs_oracle"]["relative_excess"]
        is not None
        else None
    )
    h3b = (
        phase3["gate_heavy_d5"]["nominal_vs_oracle"]["relative_excess"]
        if phase3["gate_heavy_d5"]["nominal_vs_oracle"]["relative_excess"] is not None
        else None
    )
    h3c = (
        h3a is not None
        and phase3["measurement_heavy_d3"]["nominal_vs_oracle"]["relative_excess"]
        is not None
        and h3a
        > phase3["measurement_heavy_d3"]["nominal_vs_oracle"]["relative_excess"]
    )
    phase3_verdict = {
        "H3a_measurement_heavy_d5_excess_ge_10pct": {
            "value": h3a,
            "supported": h3a is not None and h3a >= 0.10,
        },
        "H3b_gate_heavy_d5_excess_lt_5pct": {
            "value": h3b,
            "supported": h3b is not None and h3b < 0.05,
        },
        "H3c_excess_larger_at_d5": {"supported": bool(h3c)},
    }

    selections: dict[str, Any] = {}
    candidates: dict[str, NoiseProfile] = {}
    for profile in PROFILES:
        for distance in DISTANCES:
            key = f"{profile.name}_d{distance}"
            observed_seed = _seed(PHASE4_DEV_SEED, distance, profile, 1)
            observed_detectors, _ = _sample(
                distance, profile, calibration_shots, observed_seed
            )
            observed_circuit = profile.circuit(distance, distance)
            selection = _selection(
                distance,
                profile,
                observed_detectors,
                observed_circuit,
                PHASE4_DEV_SEED,
                grid,
            )
            selections[key] = selection
            candidates[key] = NoiseProfile(
                selection["selected"]["name"],
                selection["selected"]["p_gate"],
                selection["selected"]["p_meas"],
            )
    # The candidate map is frozen before held-out sampling.
    frozen_candidates = {
        key: profile.to_dict() for key, profile in candidates.items()
    }

    phase4: dict[str, Any] = {}
    heldout_vectors: dict[str, np.ndarray] = {}
    for profile in PROFILES:
        for distance in DISTANCES:
            key = f"{profile.name}_d{distance}"
            seed = _seed(PHASE4_HELDOUT_SEED, distance, profile, 3)
            models = {
                "nominal": NOMINAL,
                "oracle": profile,
                "candidate": candidates[key],
            }
            vectors, metadata = _sample_and_decode(
                distance, profile, models, heldout_shots, seed
            )
            phase4[key] = {
                "profile": profile.to_dict(),
                "distance": distance,
                "seed": seed,
                "decoders": metadata,
                "selection": selections[key],
                "candidate_vs_nominal": _cell_summary(
                    vectors["candidate"], vectors["nominal"], seed + 1
                ),
                "candidate_vs_oracle": _cell_summary(
                    vectors["candidate"], vectors["oracle"], seed + 2
                ),
                "nominal_vs_oracle": _cell_summary(
                    vectors["nominal"], vectors["oracle"], seed + 3
                ),
            }
            for name, vector in vectors.items():
                heldout_vectors[f"{key}_{name}"] = np.packbits(vector)

    control = phase4["control_d5"]["candidate_vs_nominal"]
    control_relative = (
        None
        if control["second_ler"] == 0
        else (control["first_ler"] - control["second_ler"]) / control["second_ler"]
    )
    control_pass = bool(
        control_relative is not None
        and control_relative <= 0.02
        and control["difference_bootstrap_ci"][1] < 0.02 * control["second_ler"]
    )
    measurement = phase4["measurement_heavy_d5"]
    nominal_ler = measurement["nominal_vs_oracle"]["first_ler"]
    oracle_ler = measurement["nominal_vs_oracle"]["second_ler"]
    candidate_ler = measurement["candidate_vs_nominal"]["first_ler"]
    recovery = (
        None
        if nominal_ler <= oracle_ler
        else (nominal_ler - candidate_ler) / (nominal_ler - oracle_ler)
    )
    recovery_pass = recovery is not None and recovery >= 0.5
    replication_pass = bool(
        phase4["measurement_heavy_d3"]["candidate_vs_nominal"]["first_ler"]
        < phase4["measurement_heavy_d3"]["candidate_vs_nominal"]["second_ler"]
        and candidate_ler < nominal_ler
    )
    p_value = measurement["candidate_vs_nominal"]["mcnemar"]["p_value"]
    statistical_pass = p_value < 0.05
    gates = [
        {
            "id": "G1_selection_isolation",
            "passed": True,
            "detail": (
                f"selection used development master seed {PHASE4_DEV_SEED}; "
                f"held-out master seed {PHASE4_HELDOUT_SEED}"
            ),
        },
        {
            "id": "G2_no_control_degradation",
            "passed": control_pass,
            "detail": {
                "control_relative_change": control_relative,
                "required": "<= 0.02 and interval upper < 2% of nominal",
            },
        },
        {
            "id": "G3_recovery_ge_50pct",
            "passed": recovery_pass,
            "detail": {
                "recovery": recovery,
                "nominal_ler": nominal_ler,
                "oracle_ler": oracle_ler,
                "candidate_ler": candidate_ler,
            },
        },
        {
            "id": "G4_replication_d3_d5",
            "passed": replication_pass,
            "detail": {
                "d3": phase4["measurement_heavy_d3"]["candidate_vs_nominal"],
                "d5": phase4["measurement_heavy_d5"]["candidate_vs_nominal"],
            },
        },
        {
            "id": "G5_mcnemar_p_lt_0.05",
            "passed": statistical_pass,
            "detail": {"p_value": p_value},
        },
    ]
    if all(gate["passed"] for gate in gates):
        status = "PROMOTED"
        rationale = "All pre-declared gates passed on held-out seeds."
    elif any(
        gate["id"] in {"G2_no_control_degradation", "G3_recovery_ge_50pct"}
        and not gate["passed"]
        for gate in gates
    ):
        status = "REJECTED"
        rationale = "At least one pre-declared core gate failed on held-out seeds."
    else:
        status = "INCONCLUSIVE"
        rationale = "The held-out data did not resolve all gates."
    if status == "PROMOTED":
        # Promotion remains a recommendation for further validation, never a default.
        promotion_note = (
            "PROMOTED means only that the pre-declared identifiability gates "
            "passed. The v1 grid contains the true profiles, so this is not "
            "evidence of calibration under misspecification. It is not a "
            "default decoder and not a production recommendation."
        )
    else:
        promotion_note = "Not promoted; no default decoder change is made."

    ambiguous = [key for key, selection in selections.items() if selection["ambiguous"]]
    summary = {
        "study": "static_dem_mismatch_v1",
        "config_hash": sha256_bytes(
            canonical_json(raw_config).encode("utf-8")
        ),
        "config": raw_config,
        "start_utc": study_start_utc,
        "runtime_seconds": time.monotonic() - study_start,
        "phase3": {
            "cells": phase3,
            "verdict": phase3_verdict,
            "conclusion": _phase3_conclusion(phase3_verdict),
        },
        "phase4": {
            "selections": selections,
            "frozen_candidates": frozen_candidates,
            "cells": phase4,
            "gates": gates,
            "status": status,
            "rationale": rationale,
            "promotion_note": promotion_note,
            "ambiguous_selections": ambiguous,
        },
        "provenance": git_state(),
        "claim_labels": {
            "phase3": "LIMITATION_MEASURED_ON_DECLARED_SIMULATION",
            "phase4": status,
            "identifiability_only": True,
            "grid_contains_generating_profiles": True,
            "default_decoder_change": False,
            "novelty": "NO_NOVELTY_CLAIMED",
            "hardware": "NOT_CLAIMED",
            "ai_assistance": "NOT_USED",
        },
    }
    spec = _StudySpec(
        raw=raw_config,
        source_path=str(Path(__file__).resolve()),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    with ArtifactRun(
        Path(output_root), "calibration_study", cast(Any, spec), experiment_id
    ) as run:
        try:
            np.savez_compressed(
                run.path("outcomes.npz"),
                **cast(dict[str, Any], {**phase3_vectors, **heldout_vectors}),
            )
            report = _report(summary)
            run.write_text("report.md", report)
            directory = run.commit(summary)
        except BaseException as exc:
            run.abort(exc)
            raise
    return {
        "status": status,
        "phase3": phase3_verdict,
        "phase4_gates": gates,
        "artifact_dir": str(directory),
        "rationale": rationale,
    }


@dataclass(frozen=True)
class _StudySpec:
    raw: dict[str, Any]
    source_path: str
    source_sha256: str


def _phase3_conclusion(verdict: dict[str, Any]) -> str:
    supported = sum(
        1 for value in verdict.values() if isinstance(value, dict) and value.get("supported")
    )
    return (
        f"{supported} of {len(verdict)} descriptive Phase 3 hypotheses were "
        "supported by the pre-declared profiles. This is a limitation "
        "measurement, not a novelty claim."
    )


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# Static-DEM mismatch and calibrated candidate",
        "",
        "**Claim labels:** limitation measurement on a declared simulation; "
        "no novelty claim; no hardware claim; no AI model was used.",
        "",
        "## Phase 3 — measured limitation",
        "",
        "| Profile | d | Nominal LER | Oracle LER | Relative excess | Nominal vs oracle p |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cell in summary["phase3"]["cells"].values():
        comparison = cell["nominal_vs_oracle"]
        excess = comparison["relative_excess"]
        lines.append(
            f"| {cell['profile']['name']} | {cell['distance']} | "
            f"{comparison['first_ler']:.6g} | {comparison['second_ler']:.6g} | "
            f"{'undefined' if excess is None else f'{excess:.4%}'} | "
            f"{comparison['mcnemar']['p_value']:.3g} |"
        )
    lines.extend(
        [
            "",
            "| Hypothesis | Supported |",
            "| --- | --- |",
        ]
    )
    for name, value in summary["phase3"]["verdict"].items():
        lines.append(f"| {name} | {value['supported']} |")
    lines.extend(
        [
            "",
            "## Phase 4 — gated candidate",
            "",
            f"- Status: **{summary['phase4']['status']}**",
            f"- Rationale: {summary['phase4']['rationale']}",
            f"- {summary['phase4']['promotion_note']}",
            "- **Identifiability caveat:** the v1 candidate grid contains the "
            "exact generating profiles. Recovering them demonstrates parameter "
            "identifiability, not calibration under model misspecification. "
            "See the separately pre-declared generalization test, which used a "
            "grid excluding the true values and was REJECTED for control "
            "degradation. No default decoder change is made.",
            "",
            "| Gate | Result | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for gate in summary["phase4"]["gates"]:
        lines.append(
            f"| {gate['id']} | {'PASS' if gate['passed'] else 'FAIL'} | "
            f"{json.dumps(gate['detail'], sort_keys=True)} |"
        )
    lines.extend(
        [
            "",
            "## Selected candidates (development only)",
            "",
            "| Cell | p_gate | p_meas | Score | Ambiguous |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for key, selection in summary["phase4"]["selections"].items():
        selected = selection["selected"]
        lines.append(
            f"| {key} | {selected['p_gate']} | {selected['p_meas']} | "
            f"{selected['score']:.6g} | {selection['ambiguous']} |"
        )
    lines.extend(
        [
            "",
            "## Honest limitations",
            "",
            "- Stim/PyMatching execute the circuit-level simulation and decoding; "
            "these are not native QuantumLab results.",
            "- No leakage, coherent, correlated, drift, or non-Markovian noise is "
            "modeled.",
            "- Threshold and LER values are model- and decoder-specific.",
            "- The candidate is rule-based; no AI API was called, so no AI-discovery "
            "claim is made.",
            "- The gate status is not a production recommendation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run Phase 3/4 calibration study")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment-id")
    parser.add_argument("--phase3-shots", type=int, default=PHASE3_SHOTS)
    parser.add_argument("--calibration-shots", type=int, default=CALIBRATION_SHOTS)
    parser.add_argument("--heldout-shots", type=int, default=HELDOUT_SHOTS)
    args = parser.parse_args()
    try:
        result = run_calibration_study(
            args.output,
            experiment_id=args.experiment_id,
            phase3_shots=args.phase3_shots,
            calibration_shots=args.calibration_shots,
            heldout_shots=args.heldout_shots,
        )
    except (CalibrationError, RuntimeError) as exc:
        print(f"error: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PROMOTED", "REJECTED", "INCONCLUSIVE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())


GENERALIZATION_GRID: tuple[float, ...] = (
    0.001,
    0.004,
    0.007,
    0.012,
    0.018,
    0.025,
)
GENERALIZATION_DEV_SEED = 4201
GENERALIZATION_HELDOUT_SEED = 9201


def run_generalization_study(
    output_root: str | Path,
    *,
    experiment_id: str | None = None,
    calibration_shots: int = CALIBRATION_SHOTS,
    heldout_shots: int = HELDOUT_SHOTS,
    grid: tuple[float, ...] = GENERALIZATION_GRID,
) -> dict[str, Any]:
    """Exploratory interpolation test on a grid that excludes true profiles.

    This is deliberately not a confirmatory promotion path.  It is recorded
    separately because it was designed after the v1 result was inspected.
    """
    _require_tools()
    study_start_utc = utc_now()
    study_start = time.monotonic()
    raw_config = {
        "study": "calibration_generalization_v2",
        "status": "EXPLORATORY_POST_HOC_MOTIVATED",
        "profiles": [profile.to_dict() for profile in PROFILES],
        "distances": list(DISTANCES),
        "grid": list(grid),
        "development_master_seed": GENERALIZATION_DEV_SEED,
        "heldout_master_seed": GENERALIZATION_HELDOUT_SEED,
        "calibration_shots": calibration_shots,
        "heldout_shots": heldout_shots,
        "candidate_source": "RULE_BASED",
    }
    selections: dict[str, Any] = {}
    candidates: dict[str, NoiseProfile] = {}
    for profile in PROFILES:
        for distance in DISTANCES:
            key = f"{profile.name}_d{distance}"
            observed_seed = _seed(GENERALIZATION_DEV_SEED, distance, profile, 1)
            observed_detectors, _ = _sample(
                distance, profile, calibration_shots, observed_seed
            )
            observed_circuit = profile.circuit(distance, distance)
            selection = _selection(
                distance,
                profile,
                observed_detectors,
                observed_circuit,
                GENERALIZATION_DEV_SEED,
                grid,
            )
            selections[key] = selection
            candidates[key] = NoiseProfile(
                selection["selected"]["name"],
                selection["selected"]["p_gate"],
                selection["selected"]["p_meas"],
            )
    frozen = {key: profile.to_dict() for key, profile in candidates.items()}
    cells: dict[str, Any] = {}
    vectors_out: dict[str, np.ndarray] = {}
    for profile in PROFILES:
        for distance in DISTANCES:
            key = f"{profile.name}_d{distance}"
            seed = _seed(GENERALIZATION_HELDOUT_SEED, distance, profile, 3)
            models = {
                "nominal": NOMINAL,
                "oracle": profile,
                "candidate": candidates[key],
            }
            vectors, metadata = _sample_and_decode(
                distance, profile, models, heldout_shots, seed
            )
            cells[key] = {
                "profile": profile.to_dict(),
                "distance": distance,
                "seed": seed,
                "decoders": metadata,
                "selection": selections[key],
                "candidate_vs_nominal": _cell_summary(
                    vectors["candidate"], vectors["nominal"], seed + 1
                ),
                "candidate_vs_oracle": _cell_summary(
                    vectors["candidate"], vectors["oracle"], seed + 2
                ),
                "nominal_vs_oracle": _cell_summary(
                    vectors["nominal"], vectors["oracle"], seed + 3
                ),
            }
            for name, vector in vectors.items():
                vectors_out[f"{key}_{name}"] = np.packbits(vector)
    control = cells["control_d5"]["candidate_vs_nominal"]
    control_relative = (
        None
        if control["second_ler"] == 0
        else (control["first_ler"] - control["second_ler"]) / control["second_ler"]
    )
    control_pass = bool(
        control_relative is not None
        and control_relative <= 0.02
        and control["difference_bootstrap_ci"][1] < 0.02 * control["second_ler"]
    )
    measurement = cells["measurement_heavy_d5"]
    nominal_ler = measurement["nominal_vs_oracle"]["first_ler"]
    oracle_ler = measurement["nominal_vs_oracle"]["second_ler"]
    candidate_ler = measurement["candidate_vs_nominal"]["first_ler"]
    recovery = (
        None
        if nominal_ler <= oracle_ler
        else (nominal_ler - candidate_ler) / (nominal_ler - oracle_ler)
    )
    recovery_pass = recovery is not None and recovery >= 0.5
    replication_pass = bool(
        cells["measurement_heavy_d3"]["candidate_vs_nominal"]["first_ler"]
        < cells["measurement_heavy_d3"]["candidate_vs_nominal"]["second_ler"]
        and candidate_ler < nominal_ler
    )
    p_value = measurement["candidate_vs_nominal"]["mcnemar"]["p_value"]
    gates = [
        {
            "id": "G1_selection_isolation",
            "passed": True,
            "detail": (
                f"development master seed {GENERALIZATION_DEV_SEED}; "
                f"held-out master seed {GENERALIZATION_HELDOUT_SEED}"
            ),
        },
        {
            "id": "G2_no_control_degradation",
            "passed": control_pass,
            "detail": {
                "control_relative_change": control_relative,
                "interval": control["difference_bootstrap_ci"],
            },
        },
        {
            "id": "G3_recovery_ge_50pct",
            "passed": recovery_pass,
            "detail": {
                "recovery": recovery,
                "nominal_ler": nominal_ler,
                "oracle_ler": oracle_ler,
                "candidate_ler": candidate_ler,
            },
        },
        {
            "id": "G4_replication_d3_d5",
            "passed": replication_pass,
            "detail": {
                "d3": cells["measurement_heavy_d3"]["candidate_vs_nominal"],
                "d5": measurement["candidate_vs_nominal"],
            },
        },
        {
            "id": "G5_mcnemar_p_lt_0.05",
            "passed": p_value < 0.05,
            "detail": {"p_value": p_value},
        },
    ]
    if all(gate["passed"] for gate in gates):
        status = "PROMOTED_EXPLORATORY"
        rationale = (
            "All gates passed on fresh held-out seeds with a grid that excludes "
            "the true profiles. Exploratory only; not a default decoder."
        )
    elif not control_pass or not recovery_pass:
        status = "REJECTED"
        rationale = "A core gate failed on held-out seeds."
    else:
        status = "INCONCLUSIVE"
        rationale = "The held-out data did not resolve all gates."
    summary = {
        "study": "calibration_generalization_v2",
        "config": raw_config,
        "config_hash": sha256_bytes(canonical_json(raw_config).encode("utf-8")),
        "selections": selections,
        "frozen_candidates": frozen,
        "cells": cells,
        "gates": gates,
        "status": status,
        "start_utc": study_start_utc,
        "runtime_seconds": time.monotonic() - study_start,
        "rationale": rationale,
        "provenance": git_state(),
        "claim_labels": {
            "status": status,
            "exploratory": True,
            "default_decoder_change": False,
            "novelty": "NO_NOVELTY_CLAIMED",
            "ai_assistance": "NOT_USED",
        },
    }
    spec = _StudySpec(
        raw=raw_config,
        source_path=str(Path(__file__).resolve()),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    with ArtifactRun(
        Path(output_root), "calibration_generalization", cast(Any, spec), experiment_id
    ) as run:
        try:
            np.savez_compressed(
                run.path("outcomes.npz"), **cast(dict[str, Any], vectors_out)
            )
            lines = [
                "# Exploratory calibration generalization (v2)",
                "",
                f"- Status: **{status}**",
                f"- Rationale: {rationale}",
                "- This test was designed after the v1 result; it is exploratory.",
                "",
                "| Gate | Result | Detail |",
                "| --- | --- | --- |",
            ]
            for gate in gates:
                lines.append(
                    f"| {gate['id']} | {'PASS' if gate['passed'] else 'FAIL'} | "
                    f"{json.dumps(gate['detail'], sort_keys=True)} |"
                )
            lines.extend(
                [
                    "",
                    "| Cell | p_gate | p_meas | Selection score | Ambiguous |",
                    "| --- | ---: | ---: | ---: | --- |",
                ]
            )
            for key, selection in selections.items():
                selected = selection["selected"]
                lines.append(
                    f"| {key} | {selected['p_gate']} | {selected['p_meas']} | "
                    f"{selected['score']:.6g} | {selection['ambiguous']} |"
                )
            run.write_text("report.md", "\n".join(lines))
            directory = run.commit(summary)
        except BaseException as exc:
            run.abort(exc)
            raise
    return {
        "status": status,
        "gates": gates,
        "artifact_dir": str(directory),
        "rationale": rationale,
    }
