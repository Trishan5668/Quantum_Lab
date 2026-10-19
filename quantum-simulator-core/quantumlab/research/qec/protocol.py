"""Machine-validated research protocols (legacy v1 and versioned v2).

Legacy protocols (no ``schema_version``) retain the original strict, narrow
three-qubit repetition-code schema so existing experiments remain loadable.
New experiments must declare ``schema_version: "2.0"`` and pass the strict
v2 validator below.  Unknown keys are rejected so a typo cannot silently
disable a scientific setting.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quantumlab.research.qec.codes import SUPPORTED_CODE_FAMILIES
from quantumlab.research.qec.noise import NoiseModelError, noise_model_from_dict

SUPPORTED_DECODERS: tuple[str, ...] = (
    "exact",
    "majority_vote",
    "mwpm",
    "no_correction",
    "unencoded",
)
PARTITIONS: tuple[str, ...] = ("development", "validation", "heldout", "confirmatory")
STATISTICS_METHODS: tuple[str, ...] = ("wilson", "clopper_pearson")
PRIMARY_METRICS: tuple[str, ...] = (
    "operational_failure_probability",
    "logical_failure_probability",
)


class ProtocolError(ValueError):
    """Raised when a protocol is malformed or scientifically underspecified."""


def _require_mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError(f"{name} must be a mapping")
    return value


def _reject_unknown(mapping: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ProtocolError(f"{name} has unknown keys: {unknown}")


def _require_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ProtocolError(f"{name} must be >= {minimum}")
    return value


def _require_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolError(f"{name} must be a real number")
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise ProtocolError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class CodeSpec:
    family: str
    distance: int | None
    rounds: int
    task: str = "memory"

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "distance": self.distance,
            "rounds": self.rounds,
            "task": self.task,
        }


@dataclass(frozen=True)
class NoiseSpec:
    kind: str
    model: str
    parameters: dict[str, Any]
    measurement_error: float = 0.0
    rounds: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "model": self.model,
            "parameters": dict(self.parameters),
            "measurement_error": self.measurement_error,
            "rounds": self.rounds,
        }

    def build_model(self) -> Any:
        payload = {"model": self.model, **self.parameters}
        if self.model == "phenomenological":
            payload["measurement_error"] = self.measurement_error
            payload["rounds"] = self.rounds
        try:
            return noise_model_from_dict(payload)
        except NoiseModelError as exc:
            raise ProtocolError(str(exc)) from exc


@dataclass(frozen=True)
class DecoderConfig:
    name: str
    mode: str = "min_weight"
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "mode": self.mode, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class ExperimentSettings:
    shots: int
    seed: int
    partition: str
    stopping_rule: str
    max_runtime_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "shots": self.shots,
            "seed": self.seed,
            "partition": self.partition,
            "stopping_rule": self.stopping_rule,
            "max_runtime_seconds": self.max_runtime_seconds,
        }


@dataclass(frozen=True)
class StatisticsSettings:
    method: str
    confidence_level: float
    primary_metric: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "confidence_level": self.confidence_level,
            "primary_metric": self.primary_metric,
        }


@dataclass(frozen=True)
class ExperimentProtocol:
    raw: dict[str, Any]
    name: str
    research_question: str
    hypothesis: str
    code: CodeSpec
    noise: NoiseSpec
    decoders: tuple[DecoderConfig, ...]
    comparisons: tuple[str, ...]
    experiment: ExperimentSettings
    statistics: StatisticsSettings
    resources: dict[str, Any]
    limitations: tuple[str, ...]
    source_path: str | None = None
    source_sha256: str | None = None

    @property
    def config_hash(self) -> str:
        payload = json.dumps(self.raw, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def primary_decoder(self) -> DecoderConfig:
        if not self.decoders:
            raise ProtocolError("protocol has no decoders")
        return self.decoders[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.raw.get("schema_version", "2.0"),
            "name": self.name,
            "research_question": self.research_question,
            "hypothesis": self.hypothesis,
            "code": self.code.to_dict(),
            "noise": self.noise.to_dict(),
            "decoders": [decoder.to_dict() for decoder in self.decoders],
            "comparisons": list(self.comparisons),
            "experiment": self.experiment.to_dict(),
            "statistics": self.statistics.to_dict(),
            "resources": dict(self.resources),
            "limitations": list(self.limitations),
            "config_hash": self.config_hash,
        }


def validate_experiment_protocol(raw: dict[str, Any]) -> ExperimentProtocol:
    allowed = {
        "schema_version",
        "name",
        "research_question",
        "hypothesis",
        "code",
        "noise",
        "decoders",
        "comparisons",
        "experiment",
        "statistics",
        "resources",
        "limitations",
        "metadata",
    }
    _reject_unknown(raw, allowed, "protocol")
    required = {
        "schema_version",
        "name",
        "research_question",
        "hypothesis",
        "code",
        "noise",
        "decoders",
        "experiment",
        "statistics",
    }
    missing = required - raw.keys()
    if missing:
        raise ProtocolError(f"protocol missing required sections: {sorted(missing)}")
    if str(raw["schema_version"]) != "2.0":
        raise ProtocolError("schema_version must be '2.0'")
    for key in ("name", "research_question", "hypothesis"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ProtocolError(f"{key} must be a non-empty string")

    code_raw = _require_mapping(raw["code"], "code")
    _reject_unknown(code_raw, {"family", "distance", "rounds", "task"}, "code")
    family = str(code_raw.get("family", ""))
    stim_families = {"surface_code", "surface_code_stim", "repetition_stim"}
    if family not in SUPPORTED_CODE_FAMILIES and family not in stim_families:
        raise ProtocolError(
            f"code.family {family!r} is not supported; supported: "
            f"{sorted(set(SUPPORTED_CODE_FAMILIES) | stim_families)}"
        )
    distance_raw = code_raw.get("distance")
    distance = (
        None
        if distance_raw is None
        else _require_int(distance_raw, "code.distance", minimum=1)
    )
    rounds = _require_int(code_raw.get("rounds", 1), "code.rounds", minimum=1)
    if family.startswith("surface_code"):
        if distance is None or distance < 3 or distance % 2 == 0:
            raise ProtocolError("surface-code distance must be an odd integer >= 3")
    if family == "repetition" and (distance is None or distance % 2 == 0 or distance < 3):
        raise ProtocolError("repetition code requires an odd distance >= 3")
    if family == "repetition_stim" and (distance is None or distance < 3 or distance % 2 == 0):
        raise ProtocolError("repetition_stim requires an odd distance >= 3")
    if family == "steane" and distance not in {None, 3}:
        raise ProtocolError("the Steane code has distance 3; omit code.distance or set 3")
    if family == "five_qubit" and distance not in {None, 3}:
        raise ProtocolError("the five-qubit code has distance 3; omit code.distance or set 3")
    task = str(code_raw.get("task", "memory"))
    if task not in {"memory", "memory_z", "memory_x", "x", "z"}:
        raise ProtocolError("code.task must be memory_z, memory_x, x, z, or memory")
    code = CodeSpec(family, distance, rounds, task)

    noise_raw = _require_mapping(raw["noise"], "noise")
    _reject_unknown(
        noise_raw,
        {"kind", "model", "parameters", "measurement_error", "rounds"},
        "noise",
    )
    kind = str(noise_raw.get("kind", ""))
    if kind not in {"phenomenological", "circuit_level", "code_capacity"}:
        raise ProtocolError(
            "noise.kind must be 'phenomenological', 'circuit_level', or 'code_capacity'"
        )
    model = str(noise_raw.get("model", ""))
    parameters = _require_mapping(noise_raw.get("parameters", {}), "noise.parameters")
    measurement_error = _require_number(
        noise_raw.get("measurement_error", 0.0), "noise.measurement_error"
    )
    if not 0.0 <= measurement_error <= 1.0:
        raise ProtocolError("noise.measurement_error must be in [0, 1]")
    noise_rounds = _require_int(noise_raw.get("rounds", 1), "noise.rounds", minimum=1)
    noise = NoiseSpec(kind, model, parameters, measurement_error, noise_rounds)
    try:
        noise.build_model()
    except ProtocolError:
        raise
    if kind == "circuit_level" and model != "circuit_level":
        raise ProtocolError("circuit-level noise kind requires model='circuit_level'")
    if kind == "phenomenological" and model != "phenomenological":
        raise ProtocolError("phenomenological kind requires model='phenomenological'")
    if kind == "code_capacity" and model not in {"pauli", "depolarizing", "bit_flip", "phase_flip"}:
        raise ProtocolError("code_capacity kind requires a Pauli model")
    if kind == "circuit_level" and family not in {
        "surface_code",
        "surface_code_stim",
        "repetition_stim",
    }:
        raise ProtocolError("circuit-level noise requires a Stim-backed code family")
    if kind == "phenomenological":
        data_channel = parameters.get("data_channel")
        if not isinstance(data_channel, dict):
            raise ProtocolError("phenomenological noise requires parameters.data_channel")
    if kind == "code_capacity" and measurement_error != 0.0:
        raise ProtocolError(
            "code_capacity noise cannot declare a measurement_error; use "
            "kind='phenomenological' explicitly"
        )
    if kind == "code_capacity" and noise_rounds != 1:
        raise ProtocolError("code_capacity noise is a single-shot model; noise.rounds must be 1")
    if kind == "phenomenological":
        if noise_rounds != rounds:
            raise ProtocolError(
                "noise.rounds must equal code.rounds for the phenomenological model"
            )
        if rounds != 1:
            raise ProtocolError(
                "multi-round phenomenological decoding is not implemented; only "
                "code.rounds=1 is supported (use a Stim circuit-level family for "
                "multiple rounds)"
            )
    if kind == "circuit_level" and family == "repetition_stim" and task in {"memory_x", "x"}:
        raise ProtocolError("Stim repetition_code:memory is a Z-basis memory experiment")

    decoders_raw = raw["decoders"]
    if not isinstance(decoders_raw, list) or not decoders_raw:
        raise ProtocolError("decoders must be a non-empty list")
    decoders: list[DecoderConfig] = []
    for index, item in enumerate(decoders_raw):
        decoder_raw = _require_mapping(item, f"decoders[{index}]")
        _reject_unknown(decoder_raw, {"name", "mode", "parameters"}, f"decoders[{index}]")
        name = str(decoder_raw.get("name", ""))
        if name not in SUPPORTED_DECODERS:
            raise ProtocolError(
                f"decoders[{index}].name {name!r} is not supported; {SUPPORTED_DECODERS}"
            )
        mode = str(decoder_raw.get("mode", "min_weight"))
        if name == "exact" and mode not in {"min_weight", "maximum_likelihood"}:
            raise ProtocolError("exact decoder mode must be min_weight or maximum_likelihood")
        parameters = _require_mapping(
            decoder_raw.get("parameters", {}), f"decoders[{index}].parameters"
        )
        decoders.append(DecoderConfig(name, mode, parameters))
    names = [decoder.name for decoder in decoders]
    if len(names) != len(set(names)):
        raise ProtocolError("decoder names must be unique (they are result keys)")

    comparisons_raw = raw.get("comparisons", [])
    if not isinstance(comparisons_raw, list) or not all(
        isinstance(item, str) for item in comparisons_raw
    ):
        raise ProtocolError("comparisons must be a list of decoder names")
    comparisons = tuple(comparisons_raw)
    for comparison in comparisons:
        if ":" not in comparison:
            raise ProtocolError(
                "each comparison must have the form 'first_decoder:second_decoder'"
            )
        first, second = (part.strip() for part in comparison.split(":", 1))
        if first not in names or second not in names:
            raise ProtocolError(
                f"comparison {comparison!r} references an undeclared decoder"
            )
        if first == second:
            raise ProtocolError(f"comparison {comparison!r} compares a decoder to itself")

    experiment_raw = _require_mapping(raw["experiment"], "experiment")
    _reject_unknown(
        experiment_raw,
        {"shots", "seed", "partition", "stopping_rule", "max_runtime_seconds"},
        "experiment",
    )
    shots = _require_int(experiment_raw.get("shots"), "experiment.shots", minimum=1)
    seed = _require_int(experiment_raw.get("seed"), "experiment.seed", minimum=0)
    partition = str(experiment_raw.get("partition", "confirmatory"))
    if partition not in PARTITIONS:
        raise ProtocolError(f"experiment.partition must be one of {PARTITIONS}")
    stopping_rule = str(experiment_raw.get("stopping_rule", "fixed_shots"))
    if stopping_rule != "fixed_shots":
        raise ProtocolError("only the predeclared fixed_shots stopping rule is implemented")
    max_runtime_raw = experiment_raw.get("max_runtime_seconds")
    max_runtime = (
        None
        if max_runtime_raw is None
        else _require_number(max_runtime_raw, "experiment.max_runtime_seconds")
    )
    if max_runtime is not None and max_runtime <= 0:
        raise ProtocolError("experiment.max_runtime_seconds must be positive or null")
    experiment = ExperimentSettings(shots, seed, partition, stopping_rule, max_runtime)

    statistics_raw = _require_mapping(raw["statistics"], "statistics")
    _reject_unknown(
        statistics_raw,
        {"method", "confidence_level", "primary_metric"},
        "statistics",
    )
    method = str(statistics_raw.get("method", "wilson"))
    if method not in STATISTICS_METHODS:
        raise ProtocolError(f"statistics.method must be one of {STATISTICS_METHODS}")
    confidence = _require_number(
        statistics_raw.get("confidence_level", 0.95), "statistics.confidence_level"
    )
    if not 0.0 < confidence < 1.0:
        raise ProtocolError("statistics.confidence_level must be in (0, 1)")
    primary = str(statistics_raw.get("primary_metric", "operational_failure_probability"))
    if primary not in PRIMARY_METRICS:
        raise ProtocolError(f"statistics.primary_metric must be one of {PRIMARY_METRICS}")

    resources = _require_mapping(raw.get("resources", {}), "resources")
    limitations_raw = raw.get("limitations", [])
    if not isinstance(limitations_raw, list) or not all(
        isinstance(item, str) for item in limitations_raw
    ):
        raise ProtocolError("limitations must be a list of strings")
    return ExperimentProtocol(
        raw=raw,
        name=str(raw["name"]),
        research_question=str(raw["research_question"]),
        hypothesis=str(raw["hypothesis"]),
        code=code,
        noise=noise,
        decoders=tuple(decoders),
        comparisons=comparisons,
        experiment=experiment,
        statistics=StatisticsSettings(method, confidence, primary),
        resources=resources,
        limitations=tuple(limitations_raw),
    )


# ----------------------------------------------------------------------
# Legacy v1 protocol (three-qubit repetition benchmark)
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Protocol:
    raw: dict[str, Any]

    @property
    def trials(self) -> int:
        return int(self.raw["experiment"]["trials"])

    @property
    def seed(self) -> int:
        return int(self.raw["experiment"]["seed"])

    @property
    def physical_error_rate(self) -> float:
        return float(self.raw["noise"]["physical_error_rate"])

    @property
    def confidence_level(self) -> float:
        return float(self.raw["statistics"]["confidence_level"])

    @property
    def code_distance(self) -> int:
        return int(self.raw["code"]["distance"])


def _yaml_load(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load QEC protocols") from exc
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError("protocol root must be a mapping")
    return value


def validate_protocol(raw: dict[str, Any]) -> ExperimentProtocol | Protocol:
    """Validate a protocol, dispatching on the presence of ``schema_version``."""
    if "schema_version" in raw:
        return validate_experiment_protocol(raw)
    required = {"research_question", "hypothesis", "code", "noise", "experiment", "statistics"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"protocol missing required sections: {sorted(missing)}")
    code = raw["code"]
    noise = raw["noise"]
    experiment = raw["experiment"]
    statistics = raw["statistics"]
    if not isinstance(code, dict) or code.get("family") != "repetition":
        raise ValueError("only the repetition code family is supported")
    if code.get("distance") != 3:
        raise ValueError("the supported repetition code has distance 3")
    if not isinstance(noise, dict) or noise.get("model") != "phenomenological_pauli_x":
        raise ValueError("noise.model must be phenomenological_pauli_x")
    p = noise.get("physical_error_rate")
    if (
        isinstance(p, bool)
        or not isinstance(p, (int, float))
        or not 0.0 <= float(p) <= 1.0
    ):
        raise ValueError("noise.physical_error_rate must be in [0, 1]")
    if not isinstance(experiment, dict) or not isinstance(experiment.get("trials"), int):
        raise ValueError("experiment.trials must be an integer")
    if experiment["trials"] <= 0 or not isinstance(experiment.get("seed"), int):
        raise ValueError("experiment.trials must be positive and seed must be an integer")
    if not isinstance(statistics, dict) or statistics.get("confidence_level") != 0.95:
        raise ValueError("statistics.confidence_level must currently be 0.95")
    if statistics.get("method") != "wilson":
        raise ValueError("statistics.method must be wilson")
    return Protocol(raw)


def load_protocol(path: str | Path) -> ExperimentProtocol | Protocol:
    source = Path(path)
    raw = _yaml_load(source)
    protocol = validate_protocol(raw)
    if isinstance(protocol, ExperimentProtocol):
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        return ExperimentProtocol(
            raw=protocol.raw,
            name=protocol.name,
            research_question=protocol.research_question,
            hypothesis=protocol.hypothesis,
            code=protocol.code,
            noise=protocol.noise,
            decoders=protocol.decoders,
            comparisons=protocol.comparisons,
            experiment=protocol.experiment,
            statistics=protocol.statistics,
            resources=protocol.resources,
            limitations=protocol.limitations,
            source_path=str(source),
            source_sha256=digest,
        )
    return protocol


def canonical_protocol_json(protocol: ExperimentProtocol | Protocol) -> str:
    return json.dumps(protocol.raw, sort_keys=True, separators=(",", ":"))
