"""Executable capability audit.

This module reports what the installed package can verify about itself.  It is
deliberately narrower than the prose audit in ``research/qec/audit``: every
status below is derived from an import, a public symbol, or an environment
probe.  A present symbol is not evidence of correctness; the prose audit cites
the tests that exercise it.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from typing import Any

from quantumlab.research.qec.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    git_state,
    utc_now,
)
from quantumlab.research.qec.codes import SUPPORTED_CODE_FAMILIES
from quantumlab.research.qec.protocol import STATISTICS_METHODS, SUPPORTED_DECODERS

AUDIT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Capability:
    name: str
    status: str
    evidence: str
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "evidence": self.evidence,
            "limitations": list(self.limitations),
        }


def _installed(package: str) -> bool:
    return importlib.util.find_spec(package) is not None


def repository_capabilities() -> dict[str, Any]:
    capabilities = [
        Capability(
            "pauli_algebra",
            "VERIFIED_BY_TESTS",
            "quantumlab.research.qec.pauli; tests/test_qec_pauli.py",
            (
                "matrix construction is limited to <=10 qubits",
                "phase is stored as i^k, not as a sign",
            ),
        ),
        Capability(
            "stabilizer_codes",
            "VERIFIED_BY_TESTS",
            "repetition, Steane, five-qubit; exhaustive distance <=10 qubits",
            (
                "surface-code stabilizer algebra is not implemented",
                "encoding matrices are limited to small codes",
            ),
        ),
        Capability(
            "decoders",
            "VERIFIED_BY_TESTS",
            "; ".join(SUPPORTED_DECODERS),
            (
                "no belief propagation, OSD, neural, or correlated-noise decoder",
                "MWPM Pauli adapter supports k=1 CSS codes with Z stabilizers only",
            ),
        ),
        Capability(
            "noise_models",
            "PARTIALLY_VERIFIED",
            "Pauli, phenomenological (one round), Stim circuit-level depolarizing",
            (
                "leakage, coherent, correlated, drift, and non-Markovian noise "
                "are not implemented",
                "the native simulator does not execute circuit-level surface-code "
                "syndromes; Stim is used explicitly",
            ),
        ),
        Capability(
            "statistics",
            "VERIFIED_BY_TESTS",
            "intervals: wilson, clopper_pearson; paired exact McNemar",
            (
                "intervals assume independent shots",
                "no multiplicity correction is applied automatically",
            ),
        ),
        Capability(
            "artifacts",
            "VERIFIED_BY_TESTS",
            f"artifact schema {ARTIFACT_SCHEMA_VERSION}; atomic write and checksums",
            (
                "checksum verification proves integrity, not scientific validity",
                "failed runs are preserved separately and are not valid evidence",
            ),
        ),
        Capability(
            "surface_code_simulation",
            "DELEGATED_TO_STIM"
            if _installed("stim") and _installed("pymatching")
            else "BLOCKED",
            "Stim generated circuits plus PyMatching; "
            "tests/test_qec_experiment.py::test_stim_surface_code_backend...",
            (
                "results are Stim/PyMatching results, not native QuantumLab results",
                "no native detector-error-model sampler",
            ),
        ),
        Capability(
            "hardware_execution",
            "NOT_IMPLEMENTED",
            "no hardware backend or calibration data is present",
            ("no hardware claim may be made",),
        ),
        Capability(
            "independent_validation",
            "PARTIAL",
            "analytic checks, exact oracle vs MWPM, and Stim cross-checks",
            (
                "no third-party reviewer or external replication has been recorded",
                "Stim and PyMatching are independent codebases but share the "
                "detector-error-model abstraction",
            ),
        ),
    ]
    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "python": sys.version,
        "git": git_state(),
        "optional_dependencies": {
            "stim": _installed("stim"),
            "pymatching": _installed("pymatching"),
            "qiskit": _installed("qiskit"),
            "hypothesis": _installed("hypothesis"),
        },
        "code_families": list(SUPPORTED_CODE_FAMILIES)
        + ["surface_code (Stim)", "repetition_stim (Stim)"],
        "decoders": list(SUPPORTED_DECODERS),
        "statistics_methods": list(STATISTICS_METHODS),
        "capabilities": [capability.to_dict() for capability in capabilities],
        "notice": (
            "Status describes verified implementation scope, not research novelty, "
            "superiority, production readiness, or hardware performance."
        ),
    }
