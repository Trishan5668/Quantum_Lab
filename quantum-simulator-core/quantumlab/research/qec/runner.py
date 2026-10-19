"""Deterministic runner and evidence artifact writer for the initial QEC slice."""

from __future__ import annotations

import hashlib
import json
import platform
import random
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from quantumlab.research.qec.code import RepetitionCode
from quantumlab.research.qec.protocol import Protocol
from quantumlab.research.qec.stats import summarize


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def run_experiment(protocol: Protocol, output_root: str | Path) -> Path:
    code = RepetitionCode(protocol.code_distance)
    code.validate()
    experiment_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    artifact_dir = Path(output_root) / experiment_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    rng = random.Random(protocol.seed)
    failures = 0
    baseline_failures = 0
    trials_path = artifact_dir / "raw_trials.jsonl"
    with trials_path.open("w", encoding="utf-8") as handle:
        for trial in range(protocol.trials):
            flips = (
                rng.random() < protocol.physical_error_rate,
                rng.random() < protocol.physical_error_rate,
                rng.random() < protocol.physical_error_rate,
            )
            syndrome = code.syndrome(flips)
            correction = code.correction_for_syndrome(syndrome)
            failed = code.logical_failure(flips, correction)
            baseline_failed = flips[0]
            failures += int(failed)
            baseline_failures += int(baseline_failed)
            handle.write(json.dumps({
                "trial": trial, "flips": flips, "syndrome": syndrome,
                "correction": correction, "logical_failure": failed,
                "baseline_logical_failure": baseline_failed,
            }, sort_keys=True) + "\n")
    result = summarize(failures, protocol.trials, protocol.confidence_level)
    baseline = summarize(baseline_failures, protocol.trials, protocol.confidence_level)
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to write QEC artifacts") from exc
    (artifact_dir / "config.yaml").write_text(
        yaml.safe_dump(protocol.raw, sort_keys=True), encoding="utf-8"
    )
    (artifact_dir / "environment.json").write_text(json.dumps({
        "python": sys.version, "platform": platform.platform(), "git_revision": _git_revision(),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (artifact_dir / "provenance.json").write_text(json.dumps({
        "experiment_id": experiment_id, "seed": protocol.seed,
        "input_protocol_sha256": hashlib.sha256(
            json.dumps(protocol.raw, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "source_revision": _git_revision(),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (artifact_dir / "summary.json").write_text(json.dumps({
        "experiment_id": experiment_id, "trials": result.trials, "failures": result.failures,
        "logical_failure_probability": result.probability,
        "confidence_level": result.confidence_level,
        "confidence_interval": [result.interval_low, result.interval_high],
        "baseline": {
            "decoder": "unencoded_single_qubit",
            "failures": baseline.failures,
            "logical_failure_probability": baseline.probability,
            "confidence_interval": [baseline.interval_low, baseline.interval_high],
        },
        "paired_absolute_difference": baseline.probability - result.probability,
        "decoder": "majority_vote",
        "resource_cost": {"data_qubits": 3, "syndrome_bits": 2, "rounds": 1},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (artifact_dir / "report.md").write_text(
        f"# QEC experiment {experiment_id}\n\n"
        f"This bounded phenomenological repetition-code run recorded "
        f"{result.failures} candidate failures in {result.trials} trials "
        f"({result.probability:.8g}; Wilson 95% CI "
        f"[{result.interval_low:.8g}, {result.interval_high:.8g}]).\n\n"
        "This is simulator evidence under ideal syndrome extraction, not a "
        "hardware result or a surface-code threshold claim.\n",
        encoding="utf-8",
    )
    names = (
        "config.yaml",
        "environment.json",
        "provenance.json",
        "raw_trials.jsonl",
        "summary.json",
        "report.md",
    )
    files = [artifact_dir / name for name in names]
    checksums = "\n".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in files
    ) + "\n"
    (artifact_dir / "checksums.sha256").write_text(checksums, encoding="utf-8")
    return artifact_dir
