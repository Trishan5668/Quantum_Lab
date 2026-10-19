"""Run the pre-declared independent-validation checks.

The checks are analytic identities, exhaustive enumerations, and a
Stim/PyMatching versus native-QuantumLab comparison.  They are not external
replication.  Blocked checks remain visible in the report.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from quantumlab.research.qec.artifacts import (
    environment_snapshot,
    git_state,
    sha256_file,
    utc_now,
)
from quantumlab.research.qec.codes import five_qubit_code, repetition_code, steane_code
from quantumlab.research.qec.decoders.exact import ExactDecoder
from quantumlab.research.qec.decoders.mwpm import PauliMWPMDecoder
from quantumlab.research.qec.experiment import _sample_pauli_errors, run_protocol
from quantumlab.research.qec.noise import bit_flip, depolarizing
from quantumlab.research.qec.pauli import Pauli, enumerate_paulis
from quantumlab.research.qec.protocol import load_protocol
from quantumlab.research.qec.stabilizer import ResidualClass
from quantumlab.research.qec.stats import (
    clopper_pearson_interval,
    difference_ci_newcombe,
    wilson_interval,
    zero_failure_upper_bound,
)


class ValidationError(RuntimeError):
    """Raised when a validation check cannot be executed."""


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    description: str
    status: str
    independence: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "description": self.description,
            "status": self.status,
            "independence": self.independence,
            "details": self.details,
        }


def _check_pauli_products() -> CheckResult:
    n = 5
    rng = np.random.default_rng(7001)
    max_error = 0.0
    labels = ["I", "X", "Y", "Z"]
    for _ in range(50):
        first = Pauli.from_string("".join(rng.choice(labels, size=n)))
        second = Pauli.from_string("".join(rng.choice(labels, size=n)))
        product = first * second
        direct = first.matrix() @ second.matrix()
        max_error = max(max_error, float(np.max(np.abs(product.matrix() - direct))))
    return CheckResult(
        "V1_pauli_matrix_product",
        "Pauli matrix product equals product of matrices",
        "PASS" if max_error <= 1e-10 else "FAIL",
        "L1",
        {"max_abs_error": max_error, "tolerance": 1e-10, "samples": 50},
    )


def _check_code_parameters() -> CheckResult:
    expected = {
        "repetition_d3": (1, 3, 1, True),
        "repetition_d5": (1, 5, 1, True),
        "steane_7_1_3": (3, 3, 3, True),
        "five_qubit_5_1_3": (3, 3, 3, True),
    }
    observed = {}
    all_ok = True
    for code in (
        repetition_code(3),
        repetition_code(5),
        steane_code(),
        five_qubit_code(),
    ):
        validation = code.validate()
        full = code.distance(kind="full")
        x_distance = code.distance(kind="x")
        z_distance = code.distance(kind="z")
        encoder = code.validate_encoder()
        observed[code.name] = {
            "full": full,
            "x": x_distance,
            "z": z_distance,
            "validated": validation.ok,
            "encoder": encoder,
        }
        all_ok = all_ok and (
            (full, x_distance, z_distance, validation.ok) == expected[code.name]
        )
    return CheckResult(
        "V2_code_parameters",
        "Declared code parameters and algebraic validation",
        "PASS" if all_ok else "FAIL",
        "L1",
        {"expected": expected, "observed": observed},
    )


def _check_exact_decoder_all_syndromes() -> CheckResult:
    code = repetition_code(5)
    decoder = ExactDecoder(code, bit_flip(0.1))
    failures = []
    for index in range(2 ** code.num_stabilizers):
        syndrome = tuple(
            (index >> (code.num_stabilizers - 1 - bit)) & 1
            for bit in range(code.num_stabilizers)
        )
        result = decoder.decode(syndrome)
        if result.status != "ok" or result.correction is None:
            failures.append(syndrome)
        elif code.syndrome(result.correction) != syndrome:
            failures.append(syndrome)
    return CheckResult(
        "V3_exact_decoder_all_syndromes",
        "Exact decoder returns a syndrome-consistent correction for every syndrome",
        "PASS" if not failures else "FAIL",
        "L1",
        {"syndromes_checked": 2 ** code.num_stabilizers, "failures": failures},
    )


def _check_exact_vs_mwpm() -> CheckResult:
    if importlib.util.find_spec("pymatching") is None:
        return CheckResult(
            "V4_exact_vs_mwpm",
            "Exact and MWPM corrections are logically equivalent",
            "BLOCKED",
            "L2",
            {"reason": "pymatching not installed"},
        )
    code = repetition_code(5)
    exact = ExactDecoder(code, bit_flip(0.1))
    mwpm = PauliMWPMDecoder(code, error_probability=0.1)
    mismatches = []
    for index in range(2 ** code.num_stabilizers):
        syndrome = tuple(
            (index >> (code.num_stabilizers - 1 - bit)) & 1
            for bit in range(code.num_stabilizers)
        )
        first = exact.decode(syndrome)
        second = mwpm.decode(syndrome)
        if first.correction is None or second.correction is None:
            mismatches.append({"syndrome": syndrome, "reason": "missing correction"})
            continue
        residual = first.correction * second.correction
        if not code.in_stabilizer_group(residual):
            mismatches.append(
                {
                    "syndrome": syndrome,
                    "first": first.correction.label(),
                    "second": second.correction.label(),
                }
            )
    return CheckResult(
        "V4_exact_vs_mwpm",
        "Exact and MWPM corrections differ only by a stabilizer",
        "PASS" if not mismatches else "FAIL",
        "L2",
        {"syndromes_checked": 2 ** code.num_stabilizers, "mismatches": mismatches},
    )


def _check_analytic_repetition() -> CheckResult:
    code = repetition_code(3)
    channel = bit_flip(0.1)
    decoder = ExactDecoder(code, channel)
    total = 0.0
    for error in enumerate_paulis(3):
        probability = math.exp(channel.log_probability(error))
        if probability == 0.0:
            continue
        result = decoder.decode(code.syndrome(error))
        if result.status != "ok" or result.correction is None:
            total += probability
            continue
        residual = error * result.correction
        if code.classify_residual(residual, basis="z") is not ResidualClass.TRIVIAL:
            total += probability
    p = 0.1
    formula = 3.0 * p * p * (1.0 - p) + p**3
    return CheckResult(
        "V5_analytic_repetition_d3",
        "Exact enumeration matches the closed-form d=3 bit-flip failure probability",
        "PASS" if abs(total - formula) <= 1e-12 else "FAIL",
        "L1",
        {"enumerated": total, "formula": formula, "difference": total - formula},
    )


def _stim_repetition_failures(distance: int, p: float, shots: int, seed: int) -> int:
    import stim

    circuit = stim.Circuit.generated(
        "repetition_code:memory",
        distance=distance,
        rounds=1,
        before_round_data_depolarization=p,
    )
    dem = circuit.detector_error_model(decompose_errors=True)
    import pymatching

    matching = pymatching.Matching.from_detector_error_model(dem)
    sampler = circuit.compile_detector_sampler(seed=seed)
    detectors, observables = sampler.sample(
        shots=shots, separate_observables=True, append_observables=False
    )
    predictions = np.asarray(matching.decode_batch(detectors))
    if predictions.ndim == 1:
        predictions = predictions.reshape(-1, 1)
    return int(np.sum(np.any(predictions != np.asarray(observables), axis=1)))


def _native_repetition_failures(distance: int, p: float, shots: int, seed: int) -> int:
    code = repetition_code(distance)
    channel = depolarizing(p)
    decoder = ExactDecoder(code, channel)
    rng = np.random.default_rng(seed)
    errors = _sample_pauli_errors(channel, shots, distance, rng)
    failures = 0
    for error in errors:
        result = decoder.decode(code.syndrome(error))
        if result.status != "ok" or result.correction is None:
            failures += 1
            continue
        residual = error * result.correction
        if code.classify_residual(residual, basis="z") is not ResidualClass.TRIVIAL:
            failures += 1
    return failures


def _check_stim_vs_native() -> CheckResult:
    if importlib.util.find_spec("stim") is None or importlib.util.find_spec("pymatching") is None:
        return CheckResult(
            "V6_stim_vs_native_repetition",
            "Stim/PyMatching and native reproduction agree",
            "BLOCKED",
            "L2",
            {"reason": "stim or pymatching not installed"},
        )
    shots = 50_000
    p = 0.1
    rows = []
    passed = True
    for distance in (3, 5, 7):
        seed = 7001 + distance
        stim_failures = _stim_repetition_failures(distance, p, shots, seed)
        native_failures = _native_repetition_failures(distance, p, shots, seed + 100)
        low, high = difference_ci_newcombe(
            native_failures, shots, stim_failures, shots, 0.95
        )
        interval_contains_zero = low <= 0.0 <= high
        passed = passed and interval_contains_zero
        rows.append(
            {
                "distance": distance,
                "stim_failures": stim_failures,
                "native_failures": native_failures,
                "stim_rate": stim_failures / shots,
                "native_rate": native_failures / shots,
                "difference_ci": [low, high],
                "contains_zero": interval_contains_zero,
            }
        )
    return CheckResult(
        "V6_stim_vs_native_repetition",
        "Stim/PyMatching and native exact decoding agree on depolarizing repetition memory",
        "PASS" if passed else "FAIL",
        "L2",
        {"shots": shots, "p": p, "rows": rows, "criterion": "Newcombe 95% interval contains 0"},
    )


def _check_intervals() -> CheckResult:
    wilson_84 = wilson_interval(84, 10000)
    wilson_zero = wilson_interval(0, 100)
    cp_zero = clopper_pearson_interval(0, 100)
    zero_bound = zero_failure_upper_bound(1000)
    expected = {
        "wilson_84": (0.006790405766700768, 0.01038714143134846),
        "wilson_zero": (0.0, 0.03699349820698566),
        "cp_zero": (0.0, 0.03621669264517641),
        "zero_bound": 1.0 - 0.05 ** 0.001,
    }
    observed: dict[str, Any] = {
        "wilson_84": wilson_84,
        "wilson_zero": wilson_zero,
        "cp_zero": cp_zero,
        "zero_bound": zero_bound,
    }
    errors = []
    for key, value in expected.items():
        if isinstance(value, tuple):
            low, high = value
            obs_low, obs_high = observed[key]
            if abs(obs_low - low) > 1e-12 or abs(obs_high - high) > 1e-12:
                errors.append(key)
        else:
            if abs(float(observed[key]) - value) > 1e-15:
                errors.append(key)
    return CheckResult(
        "V7_interval_identities",
        "Wilson/Clopper-Pearson/zero-failure identities",
        "PASS" if not errors else "FAIL",
        "L1",
        {"errors": errors, "observed": observed},
    )


def _check_artifact_reproducibility() -> CheckResult:
    import yaml

    raw = {
        "schema_version": "2.0",
        "name": "validation_reproducibility",
        "research_question": "Are records byte-identical for the same seed?",
        "hypothesis": "Yes.",
        "code": {"family": "repetition", "distance": 3, "rounds": 1, "task": "memory_z"},
        "noise": {
            "kind": "code_capacity",
            "model": "bit_flip",
            "parameters": {"p": 0.1},
        },
        "decoders": [{"name": "exact"}],
        "comparisons": [],
        "experiment": {
            "shots": 200,
            "seed": 77,
            "partition": "development",
            "stopping_rule": "fixed_shots",
        },
        "statistics": {
            "method": "wilson",
            "confidence_level": 0.95,
            "primary_metric": "operational_failure_probability",
        },
        "limitations": ["Validation-only protocol."],
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        protocol_path = root / "protocol.yaml"
        protocol_path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        protocol = load_protocol(protocol_path)
        if not hasattr(protocol, "experiment"):
            raise ValidationError("validation protocol did not load as v2")
        first = run_protocol(protocol, root / "runs")  # type: ignore[arg-type]
        second = run_protocol(protocol, root / "runs")  # type: ignore[arg-type]
        same = sha256_file(first / "records.jsonl") == sha256_file(
            second / "records.jsonl"
        )
        return CheckResult(
            "V8_artifact_reproducibility",
            "Same protocol and seed reproduce byte-identical records",
            "PASS" if same else "FAIL",
            "L1",
            {
                "first_records_sha256": sha256_file(first / "records.jsonl"),
                "second_records_sha256": sha256_file(second / "records.jsonl"),
            },
        )


def run_validation(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    checks = [
        _check_pauli_products(),
        _check_code_parameters(),
        _check_exact_decoder_all_syndromes(),
        _check_exact_vs_mwpm(),
        _check_analytic_repetition(),
        _check_stim_vs_native(),
        _check_intervals(),
        _check_artifact_reproducibility(),
    ]
    blocked = [check for check in checks if check.status == "BLOCKED"]
    failed = [check for check in checks if check.status == "FAIL"]
    if failed:
        overall = "FAIL"
    elif blocked:
        overall = "PASS_WITH_BLOCKED"
    else:
        overall = "PASS_L1_L2_EXTERNAL_REPLICATION_BLOCKED"
    payload = {
        "schema_version": "1.0",
        "generated_utc": utc_now(),
        "overall_status": overall,
        "checks": [check.to_dict() for check in checks],
        "blocked_checks": [
            "V9 external replication (no external group)",
            "V10 hardware logical error rate (no hardware)",
            "V11 leakage/coherent-noise validation (not modeled)",
            "V12 surface-code distance >7 exact validation (cost)",
        ],
        "independence_level": (
            "L1 analytic + L2 independent implementation; L3 external replication BLOCKED"
        ),
        "environment": environment_snapshot(),
        "git": git_state(),
        "notice": (
            "Passing these checks supports implementation correctness. It is not "
            "external replication, a hardware result, or a novelty claim."
        ),
    }
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temp_json = root / ".independent_validation.json.tmp"
    temp_json.write_text(json_text, encoding="utf-8")
    os.replace(temp_json, root / "independent_validation.json")
    digest = hashlib.sha256(json_text.encode("utf-8")).hexdigest()
    (root / "independent_validation.sha256").write_text(
        f"{digest}  independent_validation.json\n", encoding="utf-8"
    )
    (root / "independent_validation.md").write_text(
        _markdown(payload), encoding="utf-8"
    )
    return payload


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Independent validation report",
        "",
        f"- Generated: {payload['generated_utc']}",
        f"- Overall status: **{payload['overall_status']}**",
        f"- Independence: {payload['independence_level']}",
        "",
        "| Check | Status | Independence | Description |",
        "| --- | --- | --- | --- |",
    ]
    for check in payload["checks"]:
        lines.append(
            f"| {check['check_id']} | {check['status']} | "
            f"{check['independence']} | {check['description']} |"
        )
    lines.extend(
        [
            "",
            "## Blocked",
            "",
        ]
    )
    for item in payload["blocked_checks"]:
        lines.append(f"- BLOCKED: {item}")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            payload["notice"],
            "",
        ]
    )
    return "\n".join(lines)
