"""Pure quantum state representation and exact gate application.

The qubit-indexing convention used throughout the engine is BIG-ENDIAN:
``q[0]`` is the MOST significant bit when basis states are listed in
binary order. With ``num_qubits == 2``::

    index 0 -> |00>   (q[0]=0, q[1]=0)
    index 1 -> |01>   (q[0]=0, q[1]=1)
    index 2 -> |10>   (q[0]=1, q[1]=0)
    index 3 -> |11>   (q[0]=1, q[1]=1)

Gate application MUST use the full tensor product expansion via
``numpy.kron``. Non-adjacent two-qubit gates are routed onto the first
two qubits using SWAP operators which are themselves built from
``numpy.kron``. We never enumerate basis states by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from quantumlab._operators import full_unitary
from quantumlab.exceptions import (
    InvalidGateError,
    NormalizationError,
    QubitIndexError,
)
from quantumlab.gates import GateMatrix, assert_valid_gate

if TYPE_CHECKING:
    from quantumlab.density import DensityMatrix

_AMPLITUDE_EPS: float = 1e-10
_NORM_TOL: float = 1e-9


@dataclass
class StateVector:
    """Pure-state representation as a complex128 amplitude vector.

    The amplitude array has shape ``(2**num_qubits,)`` and is held in
    big-endian basis ordering as documented at the module level.
    """

    amplitudes: np.ndarray
    num_qubits: int
    _validated: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.num_qubits < 1:
            raise QubitIndexError(
                f"num_qubits must be >= 1, got {self.num_qubits}"
            )
        expected = 1 << self.num_qubits
        if self.amplitudes.shape != (expected,):
            raise NormalizationError(
                f"amplitude shape {self.amplitudes.shape} does not match "
                f"{self.num_qubits} qubits (expected ({expected},))"
            )
        if self.amplitudes.dtype != np.complex128:
            self.amplitudes = self.amplitudes.astype(np.complex128)
        norm_sq = float(np.vdot(self.amplitudes, self.amplitudes).real)
        if abs(norm_sq - 1.0) > _NORM_TOL:
            raise NormalizationError(
                f"state vector not normalized: <psi|psi> = {norm_sq}"
            )

    @classmethod
    def zero(cls, num_qubits: int) -> StateVector:
        """Return the all-zero computational basis state ``|0...0>``."""
        if num_qubits < 1:
            raise QubitIndexError(
                f"num_qubits must be >= 1, got {num_qubits}"
            )
        amps = np.zeros(1 << num_qubits, dtype=np.complex128)
        amps[0] = 1.0
        return cls(amplitudes=amps, num_qubits=num_qubits)

    @classmethod
    def from_amplitudes(cls, amplitudes: np.ndarray) -> StateVector:
        amps = np.asarray(amplitudes, dtype=np.complex128)
        if amps.ndim != 1:
            raise NormalizationError(
                f"amplitudes must be 1-D, got shape {amps.shape}"
            )
        dim = amps.shape[0]
        if dim < 2 or (dim & (dim - 1)) != 0:
            raise NormalizationError(
                f"amplitude length must be a power of two >= 2, got {dim}"
            )
        n = int(np.log2(dim))
        return cls(amplitudes=amps, num_qubits=n)

    def apply_gate(
        self, gate: GateMatrix, target_qubits: list[int]
    ) -> StateVector:
        """Return a new ``StateVector`` with ``gate`` applied to the targets.

        Parameters
        ----------
        gate:
            Unitary matrix of shape ``(2**k, 2**k)`` with ``k == len(target_qubits)``.
        target_qubits:
            For single-qubit gates, ``[q]``. For two-qubit gates the
            list ordering is ``[first_input_wire, second_input_wire]``;
            with ``CNOT()`` that means ``[control, target]``.
        """
        k = len(target_qubits)
        if k == 0:
            raise QubitIndexError("target_qubits must not be empty")
        if k > 2:
            raise InvalidGateError(
                f"gates with more than two target qubits are not supported "
                f"in v1 (got k={k})"
            )
        for q in target_qubits:
            if not (0 <= q < self.num_qubits):
                raise QubitIndexError(
                    f"qubit index {q} out of range for {self.num_qubits} qubits"
                )
        if len(set(target_qubits)) != k:
            raise QubitIndexError(
                f"target_qubits must be distinct, got {target_qubits}"
            )
        assert_valid_gate(gate, k_qubits=k)

        full = full_unitary(gate, target_qubits, self.num_qubits)
        new_amps = full @ self.amplitudes
        return StateVector(amplitudes=new_amps, num_qubits=self.num_qubits)

    def probabilities(self) -> np.ndarray:
        """Return the Born-rule probabilities ``|c_i|^2``."""
        probs = np.abs(self.amplitudes) ** 2
        return cast(np.ndarray, probs.astype(np.float64))

    def density_matrix(self) -> np.ndarray:
        """Return the full density matrix ``|psi><psi|``."""
        psi = self.amplitudes.reshape(-1, 1)
        return cast(np.ndarray, psi @ psi.conj().T)

    def to_density_matrix(self) -> DensityMatrix:
        """Return a :class:`~quantumlab.density.DensityMatrix` for this state."""
        from quantumlab.density import DensityMatrix

        return DensityMatrix.from_statevector(self)

    def reduced_density_matrix(self, qubit: int) -> np.ndarray:
        """Trace out all qubits except ``qubit``, returning a 2x2 matrix."""
        if not (0 <= qubit < self.num_qubits):
            raise QubitIndexError(
                f"qubit index {qubit} out of range for {self.num_qubits} qubits"
            )
        n = self.num_qubits
        tensor = self.amplitudes.reshape((2,) * n)
        keep = qubit
        others = [i for i in range(n) if i != keep]
        axes_order = [keep] + others
        tensor = np.transpose(tensor, axes=axes_order)
        flat = tensor.reshape(2, -1)
        rho = flat @ flat.conj().T
        return cast(np.ndarray, rho)

    def bloch_angles(self, qubit: int) -> tuple[float, float]:
        """Return ``(theta, phi)`` of the Bloch vector for a single qubit."""
        rho = self.reduced_density_matrix(qubit)
        rx = 2.0 * float(np.real(rho[0, 1]))
        ry = -2.0 * float(np.imag(rho[0, 1]))
        rz = float(np.real(rho[0, 0] - rho[1, 1]))
        r = float(np.sqrt(rx * rx + ry * ry + rz * rz))
        if r < _AMPLITUDE_EPS:
            return (0.0, 0.0)
        theta = float(np.arccos(max(-1.0, min(1.0, rz))))
        phi = float(np.arctan2(ry, rx))
        return (theta, phi)

    def bloch_vector(self, qubit: int) -> tuple[float, float, float]:
        rho = self.reduced_density_matrix(qubit)
        rx = 2.0 * float(np.real(rho[0, 1]))
        ry = -2.0 * float(np.imag(rho[0, 1]))
        rz = float(np.real(rho[0, 0] - rho[1, 1]))
        return (rx, ry, rz)

    def purity(self, qubit: int | None = None) -> float:
        """``tr(rho^2)``. If ``qubit`` is given, reduce to that qubit first."""
        if qubit is None:
            rho = self.density_matrix()
        else:
            rho = self.reduced_density_matrix(qubit)
        return float(np.real(np.trace(rho @ rho)))

    def basis_label(self, index: int) -> str:
        """Return the basis ket label, e.g. index 3 with 2 qubits -> ``|11>``."""
        if not (0 <= index < (1 << self.num_qubits)):
            raise QubitIndexError(
                f"basis index {index} out of range for {self.num_qubits} qubits"
            )
        bits = format(index, f"0{self.num_qubits}b")
        return f"|{bits}>"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the state."""
        amps = self.amplitudes
        probs = self.probabilities()
        return {
            "num_qubits": self.num_qubits,
            "amplitudes": [
                {"real": float(a.real), "imag": float(a.imag)} for a in amps
            ],
            "probabilities": [float(p) for p in probs],
            "basis_labels": [
                self.basis_label(i) for i in range(1 << self.num_qubits)
            ],
        }
