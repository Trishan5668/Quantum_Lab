"""Research verification orchestration."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from quantumlab.circuit import GatePlacement

from app.models import GatePlacementIn
from app.models_v2 import ResearchVerifyRequest
from app.wolfram.client import WolframClient, WolframUnavailableError, stable_hash
from app.wolfram.symbolic import (
    basis_labels,
    initial_state_vector,
    matrix_out,
    operator_dataset,
    vector_out,
    wolfram_language_payload,
)

VerificationStatus = Literal["VERIFIED", "DISCREPANCY", "UNAVAILABLE", "SIMULATED"]


def _placement(g: GatePlacementIn) -> GatePlacement:
    return GatePlacement(
        id=g.id,
        gate_type=g.gate_type,
        qubit_targets=list(g.qubit_targets),
        params=dict(g.params),
        time_step=g.time_step,
        stack_count=g.stack_count,
    )


async def verify_research_payload(
    payload: ResearchVerifyRequest,
    *,
    client: WolframClient | None = None,
) -> dict[str, Any]:
    placements = [_placement(g) for g in payload.gates]
    structured = _structured_input(payload, placements)
    query_hash = stable_hash(
        {
            "schema": "quantumlab.research.wolfram.v1",
            "structured": structured,
            "wolfram_query_version": 1,
        }
    )
    wolfram_query = wolfram_language_payload(structured)
    client = client or WolframClient()
    try:
        wolfram = await client.evaluate_research(cache_key=query_hash, wolfram_language=wolfram_query)
    except WolframUnavailableError as exc:
        return {
            "status": "UNAVAILABLE",
            "source": "QuantumLab simulated; Wolfram unavailable",
            "message": str(exc),
            "query_hash": query_hash,
            "structured_input": structured,
            "calculations": _unavailable_calculations(placements),
            "warnings": [
                {
                    "severity": "warning",
                    "message": "Wolfram verification is unavailable. Research derived sections are marked unavailable and native values remain simulated only.",
                }
            ],
        }

    calculations = _merge_wolfram_calculations(wolfram)
    warnings = _discrepancies(structured, wolfram)
    return {
        "status": "DISCREPANCY" if warnings else "VERIFIED",
        "source": "Wolfram verified",
        "message": "Wolfram verification completed",
        "query_hash": query_hash,
        "structured_input": structured,
        "calculations": calculations,
        "warnings": warnings,
    }


def _structured_input(payload: ResearchVerifyRequest, placements: list[GatePlacement]) -> dict[str, Any]:
    init = initial_state_vector(payload.num_qubits, payload.initial_basis_state)
    final_state = [
        {"real": amp.real, "imag": amp.imag}
        for amp in (payload.final_state or [])
    ]
    density = None
    if payload.density_real is not None and payload.density_imag is not None:
        density = {
            "real": payload.density_real,
            "imag": payload.density_imag,
        }
    return {
        "numQubits": payload.num_qubits,
        "basisOrdering": basis_labels(payload.num_qubits),
        "basisConvention": "big-endian; q[0] is most significant bit",
        "initialBasisState": payload.initial_basis_state or ("0" * payload.num_qubits),
        "initialState": vector_out(init),
        "gates": operator_dataset(payload.num_qubits, placements),
        "simulationMode": payload.simulation.mode,
        "noiseModel": payload.simulation.noise.model_dump(),
        "finalState": final_state,
        "densityMatrix": density,
        "measurementProbabilities": payload.measurement_probabilities,
    }


def _unavailable_calculations(placements: list[GatePlacement]) -> dict[str, Any]:
    gate_rows = [
        {
            "gate_id": p.id,
            "gate_type": p.gate_type,
            "status": "UNAVAILABLE",
            "unitarity": "UNAVAILABLE",
            "eigenvalues": [],
            "determinant": None,
            "trace": None,
            "rank": None,
        }
        for p in placements
        if p.gate_type != "M"
    ]
    return {
        "gates": gate_rows,
        "embeddings": [],
        "stateEvolution": [],
        "circuitUnitary": {"status": "UNAVAILABLE"},
        "densityMatrix": {"status": "UNAVAILABLE"},
        "schmidt": {"status": "UNAVAILABLE"},
        "partialTrace": {"status": "UNAVAILABLE"},
        "entropy": {"status": "UNAVAILABLE"},
        "fidelity": {"status": "UNAVAILABLE"},
        "traceDistance": {"status": "UNAVAILABLE"},
        "purity": {"status": "UNAVAILABLE"},
        "correlations": {"status": "UNAVAILABLE"},
    }


def _merge_wolfram_calculations(wolfram: dict[str, Any]) -> dict[str, Any]:
    calculations = wolfram.get("calculations")
    if isinstance(calculations, dict):
        return calculations
    return {
        "gates": wolfram.get("gates", []),
        "embeddings": wolfram.get("embeddings", []),
        "stateEvolution": wolfram.get("stateEvolution", []),
        "circuitUnitary": wolfram.get("circuitUnitary", {"status": "UNAVAILABLE"}),
        "densityMatrix": wolfram.get("densityMatrix", {"status": "UNAVAILABLE"}),
        "schmidt": wolfram.get("schmidt", {"status": "UNAVAILABLE"}),
        "partialTrace": wolfram.get("partialTrace", {"status": "UNAVAILABLE"}),
        "entropy": wolfram.get("entropy", {"status": "UNAVAILABLE"}),
        "fidelity": wolfram.get("fidelity", {"status": "UNAVAILABLE"}),
        "traceDistance": wolfram.get("traceDistance", {"status": "UNAVAILABLE"}),
        "purity": wolfram.get("purity", {"status": "UNAVAILABLE"}),
        "correlations": wolfram.get("correlations", {"status": "UNAVAILABLE"}),
    }


def _discrepancies(structured: dict[str, Any], wolfram: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = list(wolfram.get("warnings", [])) if isinstance(wolfram.get("warnings"), list) else []
    wolfram_final = wolfram.get("finalState")
    native_final = structured.get("finalState")
    if isinstance(wolfram_final, list) and isinstance(native_final, list) and len(wolfram_final) == len(native_final):
        diff = _vector_max_abs_diff(native_final, wolfram_final)
        if diff > 1e-8:
            warnings.append(
                {
                    "severity": "warning",
                    "message": "QuantumLab/Wolfram discrepancy detected in final statevector",
                    "difference": diff,
                    "affectedCalculation": "stateEvolution",
                    "quantumLab": native_final,
                    "wolfram": wolfram_final,
                }
            )
    return warnings


def _vector_max_abs_diff(a: list[dict[str, float]], b: list[dict[str, float]]) -> float:
    max_diff = 0.0
    for left, right in zip(a, b):
        dz = complex(left.get("real", 0.0), left.get("imag", 0.0)) - complex(right.get("real", 0.0), right.get("imag", 0.0))
        max_diff = max(max_diff, abs(dz))
    return max_diff
