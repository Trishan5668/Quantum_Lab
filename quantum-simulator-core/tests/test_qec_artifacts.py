from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest
import yaml

from quantumlab.research.qec.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactError,
    ArtifactRun,
    package_artifact,
    read_summary,
    sha256_file,
    verify_artifact,
)
from quantumlab.research.qec.experiment import run_protocol
from quantumlab.research.qec.protocol import ExperimentProtocol, load_protocol


@pytest.fixture()
def protocol_path(tmp_path: Path) -> Path:
    path = tmp_path / "protocol.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.0",
                "name": "artifact_test",
                "research_question": "Does the artifact engine detect tampering?",
                "hypothesis": "Tampering is detected by checksum verification.",
                "code": {
                    "family": "repetition",
                    "distance": 3,
                    "rounds": 1,
                    "task": "memory_z",
                },
                "noise": {
                    "kind": "code_capacity",
                    "model": "bit_flip",
                    "parameters": {"p": 0.1},
                },
                "decoders": [{"name": "exact"}, {"name": "no_correction"}],
                "comparisons": ["exact:no_correction"],
                "experiment": {
                    "shots": 200,
                    "seed": 17,
                    "partition": "development",
                    "stopping_rule": "fixed_shots",
                },
                "statistics": {
                    "method": "wilson",
                    "confidence_level": 0.95,
                    "primary_metric": "operational_failure_probability",
                },
                "limitations": ["Synthetic artifact test."],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _run(protocol_path: Path, output: Path) -> tuple[Path, ExperimentProtocol]:
    protocol = load_protocol(protocol_path)
    assert isinstance(protocol, ExperimentProtocol)
    return run_protocol(protocol, output), protocol


def test_artifact_is_complete_and_verifies(protocol_path: Path, tmp_path: Path) -> None:
    artifact, protocol = _run(protocol_path, tmp_path / "runs")
    expected = {
        "config.json",
        "environment.json",
        "manifest.json",
        "provenance.json",
        "records.jsonl",
        "report.md",
        "summary.json",
        "checksums.sha256",
    }
    assert expected == {path.name for path in artifact.iterdir()}
    report = verify_artifact(artifact)
    assert report.ok, report.errors
    assert report.checked_files == len(expected) - 1
    summary = read_summary(artifact)
    assert summary["experiment_id"] == artifact.name
    assert summary["config_hash"] == protocol.config_hash
    assert summary["status"] == "COMPLETED"
    rows = (artifact / "records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 200
    first = json.loads(rows[0])
    assert set(first) == {"d", "e", "i", "s"}
    provenance = json.loads((artifact / "provenance.json").read_text(encoding="utf-8"))
    assert "source_revision" in provenance["git"]
    assert provenance["git"]["dirty"] in {True, False}
    environment = json.loads((artifact / "environment.json").read_text(encoding="utf-8"))
    assert environment["packages"]["numpy"]


def test_identical_seed_reproduces_records(protocol_path: Path, tmp_path: Path) -> None:
    first, _ = _run(protocol_path, tmp_path / "a")
    second, _ = _run(protocol_path, tmp_path / "b")
    assert sha256_file(first / "records.jsonl") == sha256_file(
        second / "records.jsonl"
    )
    assert sha256_file(first / "summary.json") != sha256_file(
        second / "summary.json"
    )  # experiment id and timings differ


def test_tampering_is_detected(protocol_path: Path, tmp_path: Path) -> None:
    artifact, _ = _run(protocol_path, tmp_path / "runs")
    with (artifact / "summary.json").open("a", encoding="utf-8") as handle:
        handle.write(" ")
    report = verify_artifact(artifact)
    assert not report.ok
    assert any("checksum mismatch" in error for error in report.errors)


def test_manifest_tampering_is_detected(protocol_path: Path, tmp_path: Path) -> None:
    artifact, _ = _run(protocol_path, tmp_path / "runs")
    manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"]["summary.json"]["size_bytes"] += 1
    (artifact / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    report = verify_artifact(artifact)
    assert not report.ok
    assert any("checksum mismatch for manifest.json" in error for error in report.errors)


def test_missing_file_is_detected(protocol_path: Path, tmp_path: Path) -> None:
    artifact, _ = _run(protocol_path, tmp_path / "runs")
    (artifact / "report.md").unlink()
    report = verify_artifact(artifact)
    assert not report.ok
    assert any("missing file" in error for error in report.errors)


def test_package_requires_integrity_and_writes_manifest(
    protocol_path: Path, tmp_path: Path
) -> None:
    artifact, _ = _run(protocol_path, tmp_path / "runs")
    package = package_artifact(artifact)
    assert package.is_file()
    assert tarfile.is_tarfile(package)
    manifest = json.loads(
        package.with_suffix(package.suffix + ".manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["integrity_report"]["ok"]
    assert manifest["scientific_claim_status"] == "NOT_INDEPENDENTLY_VALIDATED"
    with pytest.raises(ArtifactError):
        package_artifact(artifact)  # destination already exists
    tampered = tmp_path / "tampered"
    tampered.mkdir()
    for path in artifact.iterdir():
        (tampered / path.name).write_bytes(path.read_bytes())
    with (tampered / "summary.json").open("a", encoding="utf-8") as handle:
        handle.write("x")
    with pytest.raises(ArtifactError):
        package_artifact(tampered)


def test_existing_identifier_is_never_overwritten(
    protocol_path: Path, tmp_path: Path
) -> None:
    protocol = load_protocol(protocol_path)
    assert isinstance(protocol, ExperimentProtocol)
    run_protocol(protocol, tmp_path, experiment_id="fixed-id")
    with pytest.raises(ArtifactError):
        run_protocol(protocol, tmp_path, experiment_id="fixed-id")


def test_failed_run_is_preserved(protocol_path: Path, tmp_path: Path) -> None:
    raw = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    raw["experiment"]["max_runtime_seconds"] = 1e-9
    raw["experiment"]["shots"] = 200_000
    path = tmp_path / "slow.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    protocol = load_protocol(path)
    assert isinstance(protocol, ExperimentProtocol)
    with pytest.raises(TimeoutError):
        run_protocol(protocol, tmp_path / "runs")
    failed = list((tmp_path / "runs").glob("failed-*"))
    assert len(failed) == 1
    error = json.loads((failed[0] / "error.json").read_text(encoding="utf-8"))
    assert error["error_type"] == "TimeoutError"
    assert "records.jsonl" in {item.name for item in failed[0].iterdir()}


def test_artifact_run_without_commit_is_moved_to_failure(tmp_path: Path) -> None:
    class Dummy:
        raw = {"name": "dummy"}

    with pytest.raises(RuntimeError):
        with ArtifactRun(tmp_path, "dummy", Dummy(), "abort-me") as run:  # type: ignore[arg-type]
            run.write_text("note.txt", "partial")
            raise RuntimeError("boom")
    assert (tmp_path / "failed-abort-me" / "note.txt").read_text() == "partial"
    assert ARTIFACT_SCHEMA_VERSION == "1.0"


def test_verify_missing_directory(tmp_path: Path) -> None:
    report = verify_artifact(tmp_path / "absent")
    assert not report.ok
    assert "does not exist" in report.errors[0]
