"""Execution engine for versioned QEC experiments.

Two physically distinct backends are supported and never mixed silently:

``pauli``
    A stabilizer code from :mod:`quantumlab.research.qec.codes` with an
    explicitly sampled independent Pauli channel, ideal one-round syndrome
    extraction, and optional classical measurement bit flips.  All decoders
    see the *same* error and syndrome (paired design).

``stim``
    Stim-generated surface/repetition code circuits with circuit-level
    depolarizing noise, sampled and decoded by Stim and PyMatching.  The
    circuit, detector error model, seeds, and package versions are recorded.

Anything else is rejected.  The engine does not silently promote a
phenomenological model to a circuit-level claim, and decoder failures are
counted as operational failures rather than discarded.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TextIO

import numpy as np

from quantumlab.research.qec.artifacts import (
    ArtifactRun,
    canonical_json,
    git_state,
    sha256_bytes,
)
from quantumlab.research.qec.codes import UnsupportedCodeFamilyError, make_code
from quantumlab.research.qec.decoders import (
    DecoderInputError,
    ExactDecoder,
    PauliMWPMDecoder,
    RepetitionMajorityDecoder,
)
from quantumlab.research.qec.decoders.base import PauliDecodeResult
from quantumlab.research.qec.decoders.mwpm import DetectorMWPMDecoder
from quantumlab.research.qec.noise import (
    CircuitLevelNoiseModel,
    PauliChannel,
    PhenomenologicalNoiseModel,
)
from quantumlab.research.qec.pauli import Pauli
from quantumlab.research.qec.protocol import ExperimentProtocol, ProtocolError
from quantumlab.research.qec.stabilizer import ResidualClass, StabilizerCode
from quantumlab.research.qec.stats import (
    StatisticsError,
    mcnemar_exact,
    summarize_with_method,
    zero_failure_upper_bound,
)

Backend = Literal["pauli", "stim"]

PAULI_CODE_FAMILIES = {"repetition", "steane", "five_qubit"}
STIM_CODE_FAMILIES = {"surface_code", "repetition_stim", "surface_code_stim"}


class ExperimentError(RuntimeError):
    """Raised when a protocol cannot be executed as specified."""


@dataclass(frozen=True)
class DecoderOutcome:
    """Per-shot result of one decoder."""

    correction: str | None
    status: str
    failure: bool


def _resolve_task(protocol: ExperimentProtocol) -> tuple[str, str]:
    task = protocol.code.task
    if task in {"memory", "memory_z", "z"}:
        return "memory_z", "z"
    if task in {"memory_x", "x"}:
        return "memory_x", "x"
    raise ExperimentError(f"unsupported code.task {task!r}; use memory_z or memory_x")


def _build_pauli_code(protocol: ExperimentProtocol) -> StabilizerCode:
    try:
        return make_code(protocol.code.family, protocol.code.distance)
    except UnsupportedCodeFamilyError as exc:
        raise ExperimentError(str(exc)) from exc


def _check_backend(protocol: ExperimentProtocol) -> Backend:
    family = protocol.code.family
    kind = protocol.noise.kind
    if family in STIM_CODE_FAMILIES:
        if protocol.code.distance is None:
            raise ExperimentError("Stim-backed codes require an explicit distance")
        if kind != "circuit_level":
            raise ExperimentError(
                f"{family} is executed by Stim and requires noise.kind='circuit_level'; "
                f"got {kind!r}"
            )
        return "stim"
    if family in PAULI_CODE_FAMILIES:
        if kind == "circuit_level":
            raise ExperimentError(
                "circuit-level noise on a Pauli-algebra code is not implemented; "
                "use a Stim-backed code family"
            )
        return "pauli"
    raise ExperimentError(f"unsupported code family {family!r}")


def _build_decoders(protocol: ExperimentProtocol, code: StabilizerCode) -> dict[str, Any]:
    model = protocol.noise.build_model()
    if isinstance(model, PhenomenologicalNoiseModel):
        data_channel = model.data_channel
    elif isinstance(model, PauliChannel):
        data_channel = model
    else:
        raise ExperimentError("Pauli backend requires a Pauli-level noise model")
    decoders: dict[str, Any] = {}
    for config in protocol.decoders:
        name = config.name
        if name == "exact":
            try:
                decoders[name] = ExactDecoder(
                    code,
                    data_channel,
                    mode=config.mode,  # type: ignore[arg-type]
                    max_enumeration=int(config.parameters.get("max_enumeration", 1_000_000)),
                )
            except DecoderInputError as exc:
                raise ExperimentError(f"decoder {name!r}: {exc}") from exc
        elif name == "majority_vote":
            if not code.name.startswith("repetition_"):
                raise ExperimentError("majority_vote is only defined for the repetition code")
            decoders[name] = RepetitionMajorityDecoder(code)
        elif name == "mwpm":
            if not code.stabilizers or any(generator.x != 0 for generator in code.stabilizers):
                raise ExperimentError(
                    "the Pauli MWPM adapter requires a CSS code with Z-type stabilizers; "
                    "use the Stim backend for the surface code"
                )
            probability = float(config.parameters.get("error_probability", 0.01))
            try:
                decoders[name] = PauliMWPMDecoder(code, error_probability=probability)
            except DecoderInputError as exc:
                raise ExperimentError(f"decoder {name!r}: {exc}") from exc
        elif name == "no_correction":
            decoders[name] = None
        elif name == "unencoded":
            raise ExperimentError(
                "the unencoded reference is not a decoder; run a separate "
                "single-qubit protocol and label it as a reference baseline"
            )
        else:  # pragma: no cover - validator already restricts names
            raise ExperimentError(f"unsupported decoder {name!r}")
    return decoders


def _sample_pauli_errors(
    channel: PauliChannel, shots: int, num_qubits: int, rng: np.random.Generator
) -> list[Pauli]:
    labels = channel.sample_labels(rng, (shots, num_qubits))
    x_bits = np.zeros((num_qubits, 4), dtype=np.int64)
    z_bits = np.zeros((num_qubits, 4), dtype=np.int64)
    phases = np.zeros((num_qubits, 4), dtype=np.int64)
    for qubit in range(num_qubits):
        bit = 1 << (num_qubits - 1 - qubit)
        x_bits[qubit, 1] = bit
        z_bits[qubit, 2] = bit
        x_bits[qubit, 3] = bit
        z_bits[qubit, 3] = bit
        phases[qubit, 3] = 1
    x_masks = x_bits[np.arange(num_qubits), labels].sum(axis=1)
    z_masks = z_bits[np.arange(num_qubits), labels].sum(axis=1)
    phase_counts = phases[np.arange(num_qubits), labels].sum(axis=1)
    return [
        Pauli(
            int(x_masks[index]),
            int(z_masks[index]),
            int(phase_counts[index]) % 4,
            num_qubits,
        )
        for index in range(shots)
    ]


def _flip_bits(
    bits: tuple[int, ...], probability: float, rng: np.random.Generator
) -> tuple[int, ...]:
    if probability == 0.0:
        return bits
    flips = rng.random(len(bits)) < probability
    return tuple(
        int(bit) ^ int(flip) for bit, flip in zip(bits, flips, strict=True)
    )


def _classify(
    code: StabilizerCode, error: Pauli, result: PauliDecodeResult, basis: str
) -> tuple[ResidualClass | None, bool]:
    if result.status != "ok" or result.correction is None:
        return None, True  # operational failure: no valid correction
    residual = error * result.correction
    residual_class = code.classify_residual(residual, basis=basis)
    return residual_class, residual_class is not ResidualClass.TRIVIAL


def _write_records(handle: TextIO, records: list[dict[str, Any]]) -> None:
    for record in records:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _run_pauli(protocol: ExperimentProtocol, run: ArtifactRun) -> dict[str, Any]:
    code = _build_pauli_code(protocol)
    model = protocol.noise.build_model()
    if isinstance(model, PhenomenologicalNoiseModel):
        if model.rounds != 1:
            raise ExperimentError(
                "the Pauli backend implements exactly one syndrome round; "
                f"noise.rounds={model.rounds} is not supported"
            )
        data_channel = model.data_channel
        measurement_error = model.measurement_error
        noise_kind = "phenomenological"
    elif isinstance(model, PauliChannel):
        data_channel = model
        measurement_error = 0.0
        noise_kind = "code_capacity"
    else:
        raise ExperimentError("Pauli backend requires a Pauli-level noise model")
    decoders = _build_decoders(protocol, code)
    _, basis = _resolve_task(protocol)
    shots = protocol.experiment.shots
    seed = protocol.experiment.seed
    data_rng = np.random.default_rng(np.random.SeedSequence([seed, 0]))
    measurement_rng = np.random.default_rng(np.random.SeedSequence([seed, 1]))
    errors = _sample_pauli_errors(data_channel, shots, code.num_qubits, data_rng)
    failures: dict[str, list[bool]] = {name: [] for name in decoders}
    decoder_failures: dict[str, int] = {name: 0 for name in decoders}
    logical_failures: dict[str, int] = {name: 0 for name in decoders}
    invalid_residuals: dict[str, int] = {name: 0 for name in decoders}
    status_counts: dict[str, dict[str, int]] = {name: {} for name in decoders}
    deadline = (
        None
        if protocol.experiment.max_runtime_seconds is None
        else time.monotonic() + protocol.experiment.max_runtime_seconds
    )
    with run.open_jsonl("records.jsonl") as handle:
        for index, error in enumerate(errors):
            if deadline is not None and index % 1000 == 0 and time.monotonic() > deadline:
                raise TimeoutError(
                    "max_runtime_seconds="
                    f"{protocol.experiment.max_runtime_seconds} exceeded after "
                    f"{index} of {shots} shots"
                )
            syndrome = _flip_bits(
                code.syndrome(error), measurement_error, measurement_rng
            )
            record: dict[str, Any] = {
                "i": index,
                "e": error.label(),
                "s": "".join(str(bit) for bit in syndrome),
                "d": {},
            }
            for name, decoder in decoders.items():
                result: PauliDecodeResult
                if decoder is None:
                    result = PauliDecodeResult(
                        correction=Pauli.identity(code.num_qubits),
                        status="ok",
                        runtime_seconds=0.0,
                        syndrome_valid=True,
                        message="no_correction",
                    )
                else:
                    result = decoder.decode(syndrome)
                residual_class, failed = _classify(code, error, result, basis)
                failures[name].append(failed)
                if result.status != "ok":
                    decoder_failures[name] += 1
                elif residual_class is ResidualClass.LOGICAL_FAILURE:
                    logical_failures[name] += 1
                elif residual_class is ResidualClass.INVALID:
                    invalid_residuals[name] += 1
                status_counts[name][result.status] = (
                    status_counts[name].get(result.status, 0) + 1
                )
                record["d"][name] = {
                    "c": None if result.correction is None else result.correction.label(),
                    "s": result.status,
                    "f": int(failed),
                }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    summaries, comparisons = _summarize(
        protocol,
        failures,
        logical_failures,
        decoder_failures,
        invalid_residuals,
        status_counts,
    )
    return {
        "backend": "pauli",
        "code": code.to_dict(),
        "task": basis,
        "noise": {
            "kind": noise_kind,
            "data_channel": data_channel.to_dict(),
            "measurement_error": measurement_error,
            "rounds": 1,
            "note": (
                "Ideal one-round syndrome extraction with classical bit-flip "
                "measurement error; not a circuit-level model."
            ),
        },
        "seed_streams": {"data": [seed, 0], "measurement": [seed, 1]},
        "decoders": summaries,
        "comparisons": comparisons,
        "record_encoding": {
            "e": "Pauli label of the sampled data error",
            "s": "observed syndrome bits (after measurement error)",
            "d": "per-decoder correction label, status, and failure flag",
        },
        "shots": shots,
        "decoder_limits": (
            "Exact decoding assumes independent Pauli errors. With "
            "measurement_error > 0 the likelihood ignores measurement faults, "
            "so the decoder is a documented mismatch baseline, not an oracle."
        ),
    }


def _summarize(
    protocol: ExperimentProtocol,
    failures: dict[str, list[bool]],
    logical_failures: dict[str, int],
    decoder_failures: dict[str, int],
    invalid_residuals: dict[str, int],
    status_counts: dict[str, dict[str, int]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    shots = protocol.experiment.shots
    confidence = protocol.statistics.confidence_level
    method = protocol.statistics.method
    summaries: dict[str, Any] = {}
    for name, vector in failures.items():
        count = int(sum(vector))
        payload: dict[str, Any] = summarize_with_method(
            count, shots, confidence, method=method
        ).to_dict()
        payload.update(
            {
                "operational_failures": count,
                "logical_failures": logical_failures[name],
                "decoder_failures": decoder_failures[name],
                "invalid_residuals": invalid_residuals[name],
                "status_counts": status_counts[name],
                "zero_failure_upper_bound": (
                    zero_failure_upper_bound(shots, confidence) if count == 0 else None
                ),
                "interpretation": (
                    "operational failure includes wrong logical outcome, invalid "
                    "residual, and any decoder invalid/timeout/error; zero events "
                    "do not prove p=0"
                ),
            }
        )
        summaries[name] = payload
    return summaries, _paired_comparisons(protocol, failures)


def _paired_comparisons(
    protocol: ExperimentProtocol, failures: dict[str, list[bool]]
) -> list[dict[str, Any]]:
    shots = protocol.experiment.shots
    comparisons: list[dict[str, Any]] = []
    for label in protocol.comparisons:
        if ":" not in label:
            raise ExperimentError(
                f"comparison {label!r} must have the form 'first_decoder:second_decoder'"
            )
        first, second = (part.strip() for part in label.split(":", 1))
        if first not in failures or second not in failures:
            raise ExperimentError(f"comparison references unknown decoder: {label!r}")
        a, b = failures[first], failures[second]
        both_success = sum(1 for x, y in zip(a, b, strict=True) if not x and not y)
        first_only = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
        second_only = sum(1 for x, y in zip(a, b, strict=True) if not x and y)
        both_failure = sum(1 for x, y in zip(a, b, strict=True) if x and y)
        try:
            mcnemar = mcnemar_exact(
                first_only,
                second_only,
                both_success=both_success,
                both_failure=both_failure,
            )
        except StatisticsError as exc:
            raise ExperimentError(str(exc)) from exc
        comparisons.append(
            {
                "first": first,
                "second": second,
                "paired": True,
                "difference_first_minus_second": (sum(a) - sum(b)) / shots,
                "both_success": both_success,
                "first_only": first_only,
                "second_only": second_only,
                "both_failure": both_failure,
                "mcnemar": mcnemar.to_dict(),
                "multiple_comparisons_note": (
                    "No multiplicity correction is applied; report all planned "
                    "comparisons and treat exploratory p-values accordingly."
                ),
            }
        )
    return comparisons


def _run_stim(protocol: ExperimentProtocol, run: ArtifactRun) -> dict[str, Any]:
    if importlib.util.find_spec("stim") is None:  # pragma: no cover - optional dependency
        raise ExperimentError("Stim is required for circuit-level execution")
    model = protocol.noise.build_model()
    if not isinstance(model, CircuitLevelNoiseModel):
        raise ExperimentError("Stim backend requires CircuitLevelNoiseModel")
    task, basis = _resolve_task(protocol)
    family = protocol.code.family
    if family in {"surface_code", "surface_code_stim"}:
        stim_task = f"surface_code:rotated_{task}"
    elif family == "repetition_stim":
        stim_task = "repetition_code:memory"
    else:
        raise ExperimentError(f"unsupported Stim family {family!r}")
    distance = protocol.code.distance
    if distance is None:
        raise ExperimentError("Stim execution requires an explicit distance")
    rounds = protocol.code.rounds
    circuit = model.stim_circuit(distance, rounds, task=stim_task)
    error_model = circuit.detector_error_model(decompose_errors=True)
    run.write_text("circuit.stim", str(circuit))
    run.write_text("detector_error_model.dem", str(error_model))
    decoder_names = {config.name for config in protocol.decoders}
    unknown = decoder_names - {"mwpm", "no_correction"}
    if unknown:
        raise ExperimentError(
            f"Stim backend supports only mwpm/no_correction, got {sorted(unknown)}"
        )
    decoder = DetectorMWPMDecoder(error_model)
    shots = protocol.experiment.shots
    seed = protocol.experiment.seed
    deadline = (
        None
        if protocol.experiment.max_runtime_seconds is None
        else time.monotonic() + protocol.experiment.max_runtime_seconds
    )
    sampler = circuit.compile_detector_sampler(seed=seed)
    detectors, observables = sampler.sample(
        shots=shots, separate_observables=True, append_observables=False
    )
    if deadline is not None and time.monotonic() > deadline:
        raise TimeoutError("max_runtime_seconds exceeded during Stim sampling")
    predictions, decode_seconds = decoder.decode_batch_timed(detectors)
    failures: dict[str, list[bool]] = {name: [] for name in decoder_names}
    status_counts: dict[str, dict[str, int]] = {
        name: {"ok": shots} for name in decoder_names
    }
    with run.open_jsonl("records.jsonl") as handle:
        for index in range(shots):
            observed = np.asarray(observables[index]).reshape(-1)
            record: dict[str, Any] = {
                "i": index,
                "obs": "".join(str(int(bit)) for bit in observed),
                "pred": {},
                "f": {},
            }
            for name in decoder_names:
                predicted = (
                    np.zeros_like(observed)
                    if name == "no_correction"
                    else predictions[index]
                )
                failed = bool(np.any(predicted != observed))
                failures[name].append(failed)
                record["pred"][name] = "".join(str(int(bit)) for bit in predicted)
                record["f"][name] = int(failed)
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    summaries: dict[str, Any] = {}
    for name, vector in failures.items():
        count = int(sum(vector))
        payload: dict[str, Any] = summarize_with_method(
            count,
            shots,
            protocol.statistics.confidence_level,
            method=protocol.statistics.method,
        ).to_dict()
        payload.update(
            {
                "operational_failures": count,
                "logical_failures": count,
                "decoder_failures": 0,
                "invalid_residuals": 0,
                "status_counts": status_counts[name],
                "zero_failure_upper_bound": (
                    zero_failure_upper_bound(
                        shots, protocol.statistics.confidence_level
                    )
                    if count == 0
                    else None
                ),
                "interpretation": (
                    "any mismatch between predicted and observed logical frame is "
                    "a failure; zero events do not prove p=0"
                ),
            }
        )
        summaries[name] = payload
    return {
        "backend": "stim+pymatching",
        "code": protocol.code.to_dict(),
        "task": basis,
        "stim_task": stim_task,
        "distance": distance,
        "rounds": rounds,
        "noise": model.to_dict(),
        "stim_version": _version("stim"),
        "pymatching_version": _version("pymatching"),
        "dem_sha256": decoder.spec.config["dem_sha256"],
        "circuit_sha256": hashlib.sha256(str(circuit).encode("utf-8")).hexdigest(),
        "seed": seed,
        "decoder": decoder.to_dict(),
        "decode_runtime_seconds": decode_seconds,
        "decoders": summaries,
        "comparisons": _paired_comparisons(protocol, failures),
        "shots": shots,
        "record_encoding": {
            "obs": "observed logical frame",
            "pred": "predicted logical frame per decoder",
            "f": "logical failure flag",
            "note": "detector bits are not stored; Stim regenerates them from the seed",
        },
        "assumptions": [
            "circuit-level depolarizing model exactly as recorded in circuit.stim",
            "decoder operates on Stim's decomposed detector error model",
            "no leakage, coherent error, drift, or correlated noise is modeled",
        ],
    }


def _version(package: str) -> str | None:
    try:
        import importlib.metadata as metadata

        return metadata.version(package)
    except Exception:
        return None


def _write_report(
    run: ArtifactRun, protocol: ExperimentProtocol, summary: dict[str, Any]
) -> None:
    result = summary["result"]
    lines = [
        f"# QEC experiment: {protocol.name}",
        "",
        f"- Experiment ID: `{run.experiment_id}`",
        f"- Config hash: `{summary['config_hash']}`",
        f"- Backend: `{result['backend']}`",
        f"- Shots: {result['shots']}",
        f"- Partition: `{protocol.experiment.partition}`",
        "",
        "## Pre-declared question",
        "",
        protocol.research_question,
        "",
        "## Pre-declared hypothesis",
        "",
        protocol.hypothesis,
        "",
        "## Results (operational failure = wrong logical outcome or decoder failure)",
        "",
        "| Decoder | Failures | Shots | Estimate | Interval | Method |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for name, payload in result["decoders"].items():
        lines.append(
            f"| `{name}` | {payload['operational_failures']} | {payload['trials']} | "
            f"{payload['probability']:.6g} | "
            f"[{payload['interval_low']:.6g}, {payload['interval_high']:.6g}] | "
            f"{payload['method']} |"
        )
        if payload["operational_failures"] == 0:
            lines.append(
                "| "
                f"_{name} zero-event bound_ | 0 | "
                f"{payload['trials']} | one-sided "
                f"{payload['confidence_level']:.0%} upper bound "
                f"{payload['zero_failure_upper_bound']:.6g} | | |"
            )
    lines.extend(
        [
            "",
            "## Claim labels",
            "",
            "| Claim | Label |",
            "| --- | --- |",
            "| Simulation executed and artifacts checksummed | VERIFIED (integrity only) |",
            "| Reproduction of a published threshold | NOT_CLAIMED_IN_THIS_RUN |",
            "| Hardware behavior | NOT_CLAIMED |",
            "| Leakage/coherent/correlated noise | NOT_MODELED |",
            "",
            "## Assumptions and limitations",
            "",
        ]
    )
    for item in protocol.limitations:
        lines.append(f"- {item}")
    lines.extend(
        [
            "- Intervals assume independent identically distributed shots; that "
            "assumption must be checked against the sampler (Stim shots are independent).",
            "- Zero observed failures are reported with an upper bound, never as p=0.",
            "",
            "## Provenance",
            "",
            f"- Source revision: `{summary['provenance']['source_revision']}`",
            f"- Dirty tree at run: `{summary['provenance']['dirty']}`",
            "- See `provenance.json`, `environment.json`, `manifest.json`, and "
            "`checksums.sha256`.",
            "",
        ]
    )
    run.write_text("report.md", "\n".join(lines))


def run_protocol(
    protocol: ExperimentProtocol,
    output_root: str | Path,
    *,
    experiment_id: str | None = None,
) -> Path:
    """Execute one versioned protocol and return the immutable artifact path."""
    backend = _check_backend(protocol)
    if protocol.code.rounds != 1 and backend == "pauli":
        raise ExperimentError(
            "multi-round syndrome extraction requires a Stim circuit-level code; "
            "the Pauli backend implements exactly one ideal syndrome round"
        )
    if any(":" not in label for label in protocol.comparisons):
        raise ProtocolError("comparisons must use 'first:second' decoder names")
    decoder_names = {config.name for config in protocol.decoders}
    for label in protocol.comparisons:
        first, second = (part.strip() for part in label.split(":", 1))
        if first not in decoder_names or second not in decoder_names:
            raise ProtocolError(f"comparison references an undeclared decoder: {label!r}")
    provenance = git_state()
    with ArtifactRun(Path(output_root), "qec_experiment", protocol, experiment_id) as run:
        try:
            if backend == "pauli":
                result = _run_pauli(protocol, run)
            else:
                result = _run_stim(protocol, run)
            summary = {
                "protocol": protocol.to_dict(),
                "config_hash": sha256_bytes(
                    canonical_json(protocol.raw).encode("utf-8")
                ),
                "result": result,
                "status": "COMPLETED",
                "scientific_status": (
                    "NOT_INDEPENDENTLY_VALIDATED"
                    if protocol.experiment.partition != "confirmatory"
                    else "PENDING_VALIDATION"
                ),
                "provenance": {
                    "source_revision": provenance["source_revision"],
                    "dirty": provenance["dirty"],
                    "dirty_status_sha256": provenance["dirty_status_sha256"],
                },
            }
            _write_report(run, protocol, summary)
            directory = run.commit(summary)
        except BaseException as exc:
            run.abort(exc)
            raise
    return directory
