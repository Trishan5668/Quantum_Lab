"""Machine-validated research protocol loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


def validate_protocol(raw: dict[str, Any]) -> Protocol:
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
    if not isinstance(p, (int, float)) or not 0.0 <= p <= 1.0:
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


def load_protocol(path: str | Path) -> Protocol:
    return validate_protocol(_yaml_load(Path(path)))
