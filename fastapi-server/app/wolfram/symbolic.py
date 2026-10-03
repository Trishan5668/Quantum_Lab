"""Structured circuit conversion for Wolfram verification."""

from __future__ import annotations

from typing import Any

import numpy as np

from quantumlab._operators import full_unitary
from quantumlab.circuit import GatePlacement, _effective_gate


def complex_out(z: complex) -> dict[str, float]:
    return {"real": float(np.real(z)), "imag": float(np.imag(z))}


def matrix_out(matrix: np.ndarray) -> dict[str, Any]:
    return {
        "real": [[float(np.real(v)) for v in row] for row in matrix],
        "imag": [[float(np.imag(v)) for v in row] for row in matrix],
        "shape": [int(matrix.shape[0]), int(matrix.shape[1])],
    }


def vector_out(vector: np.ndarray) -> list[dict[str, float]]:
    return [complex_out(complex(v)) for v in vector]


def basis_labels(num_qubits: int) -> list[str]:
    return [format(i, f"0{num_qubits}b") for i in range(1 << num_qubits)]


def initial_state_vector(num_qubits: int, basis: str | None) -> np.ndarray:
    clean = basis if basis and len(basis) == num_qubits and set(basis) <= {"0", "1"} else "0" * num_qubits
    vec = np.zeros(1 << num_qubits, dtype=np.complex128)
    vec[int(clean, 2)] = 1.0
    return vec


def operator_dataset(num_qubits: int, placements: list[GatePlacement]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for placement in sorted(placements, key=lambda g: (g.time_step, g.id)):
        local = _effective_gate(placement)
        if local is None:
            continue
        full = full_unitary(local, placement.qubit_targets, num_qubits)
        rows.append(
            {
                "gate_id": placement.id,
                "gate_type": placement.gate_type,
                "targets": list(placement.qubit_targets),
                "controls": [placement.qubit_targets[0]] if placement.gate_type == "CNOT" else [],
                "params": dict(placement.params),
                "time_step": placement.time_step,
                "stack_count": placement.stack_count,
                "local_matrix": matrix_out(local),
                "embedded_matrix": matrix_out(full),
            }
        )
    return rows


def wolfram_language_payload(structured_input: dict[str, Any]) -> str:
    density = (
        structured_input.get("density_matrix")
        or structured_input.get("densityMatrix")
    )

    state_data = (
        structured_input.get("final_state")
        or structured_input.get("finalState")
        or []
    )

    matrix = (
        _density_matrix_from_data(density)
        or _density_matrix_from_state(state_data)
    )

    if matrix is not None:
        return _matrix_expr(matrix)

    return _vector_expr(state_data)

def _vector_expr(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "unavailable"
    return "{" + ", ".join(_complex_expr(item) for item in values[:16]) + (" ..." if len(values) > 16 else "") + "}"


def _complex_expr(value: Any) -> str:
    if not isinstance(value, dict):
        return "0"
    real = float(value.get("real", 0.0))
    imag = float(value.get("imag", 0.0))
    if abs(imag) < 1e-12:
        return _number_expr(real)
    if abs(real) < 1e-12:
        return f"{_number_expr(imag)} i"
    sign = "+" if imag >= 0 else "-"
    return f"{_number_expr(real)} {sign} {_number_expr(abs(imag))} i"


def _number_expr(value: float) -> str:
    if abs(value) < 1e-12:
        return "0"
    if abs(value - 1.0) < 1e-12:
        return "1"
    if abs(value + 1.0) < 1e-12:
        return "-1"
    if abs(value - 2**-0.5) < 1e-9:
        return "1/sqrt(2)"
    if abs(value + 2**-0.5) < 1e-9:
        return "-1/sqrt(2)"
    return f"{value:.10g}"


def _probability_expr(labels: Any, probabilities: Any) -> str:
    if not isinstance(labels, list) or not isinstance(probabilities, list) or not probabilities:
        return "unavailable"
    pairs = [
        f"P(|{label}>)={_number_expr(float(prob))}"
        for label, prob in zip(labels[:16], probabilities[:16])
    ]
    return "; ".join(pairs) + ("; ..." if len(probabilities) > 16 else "")


def _gate_summary(gates: Any) -> str:
    if not isinstance(gates, list) or not gates:
        return "identity/no gates"
    rows: list[str] = []
    for gate in gates[:8]:
        if not isinstance(gate, dict):
            continue
        gate_type = gate.get("gate_type", "gate")
        targets = gate.get("targets", [])
        stack_count = gate.get("stack_count", 1)
        params = gate.get("params", {})
        matrix = _matrix_expr(gate.get("local_matrix"))
        rows.append(
            f"{gate_type}^{stack_count} on q{targets} params {params}, local matrix {matrix}"
        )
    return "; ".join(rows) + ("; ..." if len(gates) > 8 else "")


def _matrix_expr(matrix: Any) -> str:
    if not isinstance(matrix, dict):
        return "unavailable"
    real = matrix.get("real")
    imag = matrix.get("imag")
    if not isinstance(real, list):
        return "unavailable"
    rows: list[str] = []
    for row_index, row in enumerate(real):
        if not isinstance(row, list):
            continue
        out: list[str] = []
        for col_index, cell in enumerate(row):
            im = 0.0
            if isinstance(imag, list) and row_index < len(imag) and isinstance(imag[row_index], list) and col_index < len(imag[row_index]):
                im = float(imag[row_index][col_index])
            out.append(_complex_expr({"real": float(cell), "imag": im}))
        rows.append("{" + ", ".join(out) + "}")
    return "{" + ", ".join(rows) + "}"


def _density_summary(density: Any) -> str:
    if not isinstance(density, dict):
        return "Density matrix supplied: unavailable; derive rho from final pure state if applicable."
    return f"Density matrix rho = {_matrix_expr({'real': density.get('real'), 'imag': density.get('imag')})}."


def _density_matrix_from_data(density: Any) -> dict[str, Any] | None:
    if not isinstance(density, dict):
        return None
    real = density.get("real")
    imag = density.get("imag")
    if not isinstance(real, list) or not real:
        return None
    return {"real": real, "imag": imag if isinstance(imag, list) else None}


def _density_matrix_from_state(state: Any) -> dict[str, Any] | None:
    if not isinstance(state, list) or not state:
        return None
    vector = [_complex_value(item) for item in state]
    real: list[list[float]] = []
    imag: list[list[float]] = []
    for left in vector:
        real_row: list[float] = []
        imag_row: list[float] = []
        for right in vector:
            value = left * right.conjugate()
            real_row.append(float(value.real))
            imag_row.append(float(value.imag))
        real.append(real_row)
        imag.append(imag_row)
    return {"real": real, "imag": imag}


def _complex_value(value: Any) -> complex:
    if not isinstance(value, dict):
        return 0.0 + 0.0j
    return complex(float(value.get("real", 0.0)), float(value.get("imag", 0.0)))
