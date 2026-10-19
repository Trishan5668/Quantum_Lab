"""Physically explicit noise models for the QEC research layer.

Two levels are deliberately separated:

* :class:`PauliChannel` is an *exact stochastic Pauli channel* with independent
  single-qubit action.  Its probabilities are explicit; ``I`` has probability
  ``1 - p_x - p_y - p_z``.  Depolarizing noise uses the convention
  ``P(X)=P(Y)=P(Z)=p/3`` (total non-identity probability ``p``).
* :class:`CircuitLevelNoiseModel` describes the four independent noise hooks
  of Stim's generated surface-code circuits.  Native QuantumLab sampling of
  those circuits is *not* implemented; the model is executed by Stim and this
  dependency is recorded in every artifact.

Amplitude and phase damping are non-Pauli channels implemented exactly in
``quantumlab.noise``.  They can be validated as CPTP maps and applied to small
density matrices, but they are not passed to a Pauli decoder as if they were
Pauli noise.  Leakage, coherent errors, correlated errors, and drifting noise
are *not implemented* and are rejected by :func:`require_supported_noise`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from quantumlab.research.qec.pauli import Pauli

Label = Literal["I", "X", "Y", "Z"]
_LABEL_ORDER: tuple[Label, ...] = ("I", "X", "Z", "Y")
_LABEL_CODE: dict[Label, int] = {"I": 0, "X": 1, "Z": 2, "Y": 3}
_CODE_LABEL: dict[int, Label] = {0: "I", 1: "X", 2: "Z", 3: "Y"}

UNSUPPORTED_NOISE_FEATURES: tuple[str, ...] = (
    "leakage",
    "coherent",
    "correlated",
    "drift",
    "non_markovian",
)


class NoiseModelError(ValueError):
    """Raised for invalid or unsupported noise-model parameters."""


def _finite_probability(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NoiseModelError(f"{name} must be a real number, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise NoiseModelError(f"{name} must be finite, got {result!r}")
    if result < 0.0 or result > 1.0:
        raise NoiseModelError(f"{name} must be in [0, 1], got {result!r}")
    return result


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise NoiseModelError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 1:
        raise NoiseModelError(f"{name} must be >= 1, got {value}")
    return value


@dataclass(frozen=True)
class PauliChannel:
    """Independent single-qubit Pauli channel ``(p_x, p_y, p_z)``."""

    p_x: float = 0.0
    p_y: float = 0.0
    p_z: float = 0.0

    def __post_init__(self) -> None:
        px = _finite_probability(self.p_x, "p_x")
        py = _finite_probability(self.p_y, "p_y")
        pz = _finite_probability(self.p_z, "p_z")
        total = px + py + pz
        if total > 1.0 + 1e-12:
            raise NoiseModelError(
                f"Pauli probabilities must sum to <= 1, got p_x+p_y+p_z={total!r}"
            )
        # Store the validated values without silently renormalising.
        object.__setattr__(self, "p_x", px)
        object.__setattr__(self, "p_y", py)
        object.__setattr__(self, "p_z", pz)

    @property
    def p_identity(self) -> float:
        """Identity probability, with exact boundary cleanup only.

        ``p/3 + p/3 + p/3`` can differ from ``p`` by one ulp; values within
        ``1e-15`` of an exact boundary are snapped so that ``p=1`` is truly
        noiseless-free identity probability zero and ``p=0`` is exactly one.
        Non-boundary values are never renormalised.
        """
        residual = 1.0 - self.p_x - self.p_y - self.p_z
        if residual <= 1e-15:
            return 0.0
        if residual >= 1.0 - 1e-15:
            return 1.0
        return residual

    @property
    def probabilities(self) -> tuple[float, float, float, float]:
        """Return ``(P(I), P(X), P(Z), P(Y))`` in label-code order."""
        return (self.p_identity, self.p_x, self.p_z, self.p_y)

    @property
    def total_error_probability(self) -> float:
        return self.p_x + self.p_y + self.p_z

    def sample_label(self, rng: np.random.Generator) -> Label:
        u = float(rng.random())
        cumulative = 0.0
        for label in _LABEL_ORDER:
            cumulative += float(self.probabilities[_LABEL_CODE[label]])
            if u < cumulative:
                return label
        return "I"

    def sample_labels(self, rng: np.random.Generator, shape: tuple[int, ...]) -> np.ndarray:
        """Vectorized deterministic sampling of labels (0=I, 1=X, 2=Z, 3=Y)."""
        probs = np.asarray(self.probabilities, dtype=np.float64)
        cumulative = np.cumsum(probs)
        cumulative[-1] = 1.0
        u = rng.random(shape)
        codes = np.searchsorted(cumulative, u, side="right")
        codes = np.clip(codes, 0, 3).astype(np.uint8)
        return codes

    def sample_pauli(self, rng: np.random.Generator, num_qubits: int) -> Pauli:
        codes = self.sample_labels(rng, (num_qubits,))
        x = 0
        z = 0
        phase = 0
        for qubit, code in enumerate(codes.tolist()):
            label = _CODE_LABEL[int(code)]
            bit = 1 << (num_qubits - 1 - qubit)
            if label == "X":
                x |= bit
            elif label == "Z":
                z |= bit
            elif label == "Y":
                x |= bit
                z |= bit
                phase += 1
        return Pauli(x, z, phase % 4, num_qubits)

    def log_probability(self, pauli: Pauli) -> float:
        """Log probability of an error under independent per-qubit action."""
        if pauli.num_qubits < 1:
            raise NoiseModelError("Pauli must act on at least one qubit")
        n = pauli.num_qubits
        x_only = ((pauli.x & ~pauli.z) & ((1 << n) - 1)).bit_count()
        z_only = ((pauli.z & ~pauli.x) & ((1 << n) - 1)).bit_count()
        both = (pauli.x & pauli.z).bit_count()
        identity = n - x_only - z_only - both
        if identity < 0:
            raise NoiseModelError("Pauli masks are inconsistent")
        terms = (
            (x_only, self.p_x),
            (z_only, self.p_z),
            (both, self.p_y),
            (identity, self.p_identity),
        )
        total = 0.0
        for count, probability in terms:
            if count == 0:
                continue
            if probability <= 0.0:
                return -math.inf
            total += count * math.log(probability)
        return total

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "pauli",
            "p_x": self.p_x,
            "p_z": self.p_z,
            "p_y": self.p_y,
            "p_identity": self.p_identity,
        }


def depolarizing(p: float) -> PauliChannel:
    """Total non-identity probability ``p``, split equally over X/Y/Z."""
    value = _finite_probability(p, "p")
    return PauliChannel(p_x=value / 3.0, p_y=value / 3.0, p_z=value / 3.0)


def bit_flip(p: float) -> PauliChannel:
    value = _finite_probability(p, "p")
    return PauliChannel(p_x=value)


def phase_flip(p: float) -> PauliChannel:
    value = _finite_probability(p, "p")
    return PauliChannel(p_z=value)


def biased_pauli(p_x: float, p_y: float, p_z: float) -> PauliChannel:
    return PauliChannel(p_x=p_x, p_y=p_y, p_z=p_z)


@dataclass(frozen=True)
class MeasurementErrorModel:
    """Independent classical bit-flip errors on syndrome measurements."""

    probability: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "probability", _finite_probability(self.probability, "measurement probability")
        )

    def flip(self, bit: int, rng: np.random.Generator) -> int:
        if bit not in (0, 1):
            raise NoiseModelError("measurement bit must be 0 or 1")
        return bit ^ int(rng.random() < self.probability)

    def flips(self, bits: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        array = np.asarray(bits)
        if not np.all((array == 0) | (array == 1)):
            raise NoiseModelError("measurement bits must be binary")
        noise = (rng.random(array.shape) < self.probability).astype(array.dtype)
        flipped: np.ndarray = np.bitwise_xor(array, noise)
        return flipped

    def to_dict(self) -> dict[str, Any]:
        return {"type": "measurement_bit_flip", "probability": self.probability}


@dataclass(frozen=True)
class PhenomenologicalNoiseModel:
    """Data-qubit Pauli errors plus faulty syndrome measurements.

    This is a *phenomenological* model.  It does not contain preparation,
    gate, idle, leakage, or correlated faults.  Syndrome extraction is ideal
    except that each measured bit is independently flipped with
    ``measurement_error``.
    """

    data_channel: PauliChannel
    measurement_error: float = 0.0
    rounds: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "measurement_error",
            _finite_probability(self.measurement_error, "measurement_error"),
        )
        object.__setattr__(self, "rounds", _positive_int(self.rounds, "rounds"))

    @property
    def kind(self) -> str:
        return "phenomenological"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "model": "phenomenological_pauli_plus_measurement",
            "data_channel": self.data_channel.to_dict(),
            "measurement_error": self.measurement_error,
            "rounds": self.rounds,
            "gate_error": False,
            "idle_error": False,
            "leakage": False,
            "correlated": False,
            "coherent": False,
        }


@dataclass(frozen=True)
class CircuitLevelNoiseModel:
    """Stim circuit-level depolarizing-noise specification.

    The four parameters map one-to-one onto
    ``stim.Circuit.generated(...)``.  Every artifact records that sampling and
    decoding were delegated to Stim/PyMatching; these numbers are not used by
    a native QuantumLab circuit executor.
    """

    p_gate: float
    p_measurement: float
    p_reset: float
    p_round: float

    def __post_init__(self) -> None:
        for name in ("p_gate", "p_measurement", "p_reset", "p_round"):
            object.__setattr__(self, name, _finite_probability(getattr(self, name), name))

    @property
    def kind(self) -> str:
        return "circuit_level"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "model": "stim_circuit_level_depolarizing",
            "after_clifford_depolarization": self.p_gate,
            "before_measure_flip_probability": self.p_measurement,
            "after_reset_flip_probability": self.p_reset,
            "before_round_data_depolarization": self.p_round,
            "native_sampling": False,
            "executor": "stim",
            "leakage": False,
            "correlated": False,
            "coherent": False,
        }

    @staticmethod
    def uniform(p: float) -> CircuitLevelNoiseModel:
        """Return the common one-parameter model with all four hooks equal."""
        value = _finite_probability(p, "p")
        return CircuitLevelNoiseModel(value, value, value, value)

    def stim_circuit(
        self,
        distance: int,
        rounds: int,
        *,
        task: str = "surface_code:rotated_memory_z",
    ) -> Any:
        """Generate the corresponding Stim circuit (optional dependency)."""
        _positive_int(distance, "distance")
        _positive_int(rounds, "rounds")
        if distance < 2:
            raise NoiseModelError("surface-code distance must be >= 2")
        try:
            import stim
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise NoiseModelError(
                "Stim is required for circuit-level simulation; install "
                "quantumlab[research] or pip install stim"
            ) from exc
        return stim.Circuit.generated(
            task,
            distance=distance,
            rounds=rounds,
            after_clifford_depolarization=self.p_gate,
            before_measure_flip_probability=self.p_measurement,
            after_reset_flip_probability=self.p_reset,
            before_round_data_depolarization=self.p_round,
        )


def require_supported_noise(model: object) -> None:
    """Reject models that QuantumLab does not physically implement."""
    if not isinstance(model, (PauliChannel, PhenomenologicalNoiseModel, CircuitLevelNoiseModel)):
        raise NoiseModelError(
            f"unsupported noise model type {type(model).__name__}; supported: "
            "PauliChannel, PhenomenologicalNoiseModel, CircuitLevelNoiseModel"
        )


def noise_model_from_dict(
    raw: dict[str, Any],
) -> PauliChannel | PhenomenologicalNoiseModel | CircuitLevelNoiseModel:
    """Build a noise model from a validated protocol-style dictionary."""
    model = raw.get("model")
    if model == "pauli":
        return PauliChannel(
            p_x=raw.get("p_x", 0.0),
            p_y=raw.get("p_y", 0.0),
            p_z=raw.get("p_z", 0.0),
        )
    if model == "depolarizing":
        return depolarizing(raw.get("p", 0.0))
    if model == "bit_flip":
        return bit_flip(raw.get("p", 0.0))
    if model == "phase_flip":
        return phase_flip(raw.get("p", 0.0))
    if model == "phenomenological":
        channel_raw = raw.get("data_channel", {})
        if not isinstance(channel_raw, dict):
            raise NoiseModelError("data_channel must be a mapping")
        return PhenomenologicalNoiseModel(
            data_channel=noise_model_from_dict(channel_raw),  # type: ignore[arg-type]
            measurement_error=raw.get("measurement_error", 0.0),
            rounds=raw.get("rounds", 1),
        )
    if model == "circuit_level":
        return CircuitLevelNoiseModel(
            p_gate=raw.get("p_gate", 0.0),
            p_measurement=raw.get("p_measurement", 0.0),
            p_reset=raw.get("p_reset", raw.get("p_gate", 0.0)),
            p_round=raw.get("p_round", raw.get("p_gate", 0.0)),
        )
    raise NoiseModelError(f"unknown noise model {model!r}")


# ----------------------------------------------------------------------
# CPTP verification for the core simulator's Kraus channels
# ----------------------------------------------------------------------
def kraus_completeness_error(kraus: list[np.ndarray]) -> float:
    """Return ``max |sum_i K_i^dagger K_i - I|`` for a Kraus list."""
    if not kraus:
        raise NoiseModelError("Kraus list must not be empty")
    dim = kraus[0].shape[0]
    total = np.zeros((dim, dim), dtype=np.complex128)
    for operator in kraus:
        if operator.shape != (dim, dim):
            raise NoiseModelError("all Kraus operators must have the same square shape")
        total += operator.conj().T @ operator
    return float(np.max(np.abs(total - np.eye(dim))))


def choi_matrix(kraus: list[np.ndarray]) -> np.ndarray:
    """Return the Choi matrix ``sum_i vec(K_i) vec(K_i)^dagger``.

    This convention has ``trace(J) = sum_i Tr(K_i^dagger K_i) = d`` for a
    trace-preserving map; positive semidefiniteness is equivalent to complete
    positivity.
    """
    if not kraus:
        raise NoiseModelError("Kraus list must not be empty")
    dim = kraus[0].shape[0]
    choi = np.zeros((dim * dim, dim * dim), dtype=np.complex128)
    for operator in kraus:
        if operator.shape != (dim, dim):
            raise NoiseModelError("all Kraus operators must have the same square shape")
        vector = operator.reshape(-1)
        choi += np.outer(vector, vector.conj())
    return choi


def cptp_report(kraus: list[np.ndarray], *, tolerance: float = 1e-9) -> dict[str, float | bool]:
    """Return trace-preservation, complete-positivity, and CPTP diagnostics."""
    completeness = kraus_completeness_error(kraus)
    choi = choi_matrix(kraus)
    eigenvalues = np.linalg.eigvalsh((choi + choi.conj().T) / 2)
    min_eigenvalue = float(np.min(eigenvalues))
    trace = float(np.real(np.trace(choi)))
    dimension = float(kraus[0].shape[0])
    return {
        "completeness_error": completeness,
        "choi_min_eigenvalue": min_eigenvalue,
        "choi_trace": trace,
        "expected_choi_trace": dimension,
        "trace_preserving": completeness <= tolerance,
        "completely_positive": min_eigenvalue >= -tolerance,
        "cptp": completeness <= tolerance and min_eigenvalue >= -tolerance,
    }


def validate_cptp(kraus: list[np.ndarray], *, tolerance: float = 1e-9) -> None:
    report = cptp_report(kraus, tolerance=tolerance)
    if not report["cptp"]:
        raise NoiseModelError(f"channel is not CPTP: {report}")
