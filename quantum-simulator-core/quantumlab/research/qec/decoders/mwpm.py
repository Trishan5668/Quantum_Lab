"""Optional minimum-weight perfect matching adapters.

Two interfaces are kept separate:

* :class:`DetectorMWPMDecoder` decodes detector-event arrays produced by a
  Stim circuit and returns predicted logical-observable frames.  It is the
  decoder used by the circuit-level surface-code reproduction.
* :class:`PauliMWPMDecoder` decodes X-error syndromes of a CSS code whose
  stabilizers are Z-type (for example the repetition code).  It is used as an
  external MWPM baseline against the exact small-code oracle.

PyMatching and Stim are optional dependencies.  Importing this module is safe
without them; constructing a decoder raises an actionable error.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import numpy as np

from quantumlab.research.qec.decoders.base import (
    DecoderInputError,
    DecoderSpec,
    DecoderUnavailableError,
    DetectorDecodeResult,
    PauliDecoder,
)
from quantumlab.research.qec.pauli import Pauli
from quantumlab.research.qec.stabilizer import StabilizerCode


def _import_pymatching() -> Any:
    try:
        import pymatching
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise DecoderUnavailableError(
            "PyMatching is required for MWPM decoding; install "
            "quantumlab[research] or pip install pymatching"
        ) from exc
    return pymatching


class DetectorMWPMDecoder:
    """PyMatching MWPM decoder for a Stim detector error model."""

    VERSION = "1.0.0"

    def __init__(self, detector_error_model: Any) -> None:
        pymatching = _import_pymatching()
        if not hasattr(detector_error_model, "num_detectors"):
            raise DecoderInputError("expected a Stim DetectorErrorModel")
        self.detector_error_model = detector_error_model
        try:
            self.matching = pymatching.Matching.from_detector_error_model(
                detector_error_model
            )
        except Exception as exc:  # noqa: BLE001 - surface actionable dependency error
            raise DecoderInputError(
                f"PyMatching could not build a matching graph: {type(exc).__name__}: {exc}"
            ) from exc
        self.dem_text = str(detector_error_model)
        self.spec = DecoderSpec(
            name="pymatching_mwpm_detector",
            version=self.VERSION,
            decoder_type="detector",
            supported_code_families=("surface_code_stim", "repetition_code_stim"),
            noise_assumptions=("independent detector error model",),
            deterministic=True,
            config={
                "dem_sha256": hashlib.sha256(self.dem_text.encode("utf-8")).hexdigest(),
                "num_detectors": int(detector_error_model.num_detectors),
                "num_observables": int(detector_error_model.num_observables),
            },
        )

    @property
    def num_detectors(self) -> int:
        return int(self.detector_error_model.num_detectors)

    @property
    def num_observables(self) -> int:
        return int(self.detector_error_model.num_observables)

    def decode_batch(self, detector_samples: np.ndarray) -> np.ndarray:
        """Return one predicted logical frame per detector shot."""
        array = np.asarray(detector_samples)
        if array.ndim != 2 or array.shape[1] != self.num_detectors:
            raise DecoderInputError(
                f"detector_samples must have shape (shots, {self.num_detectors}), "
                f"got {array.shape}"
            )
        if not np.all((array == 0) | (array == 1)):
            raise DecoderInputError("detector samples must be binary")
        predictions = self.matching.decode_batch(array.astype(np.uint8))
        result = np.asarray(predictions)
        if result.ndim == 1:
            result = result.reshape(-1, 1)
        if result.shape != (array.shape[0], self.num_observables):
            raise DecoderInputError(
                f"decoder returned shape {result.shape}, expected "
                f"{(array.shape[0], self.num_observables)}"
            )
        return result.astype(np.uint8)

    def decode_batch_timed(
        self, detector_samples: np.ndarray
    ) -> tuple[np.ndarray, float]:
        start = time.perf_counter()
        predictions = self.decode_batch(detector_samples)
        return predictions, time.perf_counter() - start

    def decode_one(self, detectors: np.ndarray) -> DetectorDecodeResult:
        array = np.asarray(detectors)
        if array.ndim != 1:
            raise DecoderInputError("decode_one expects a one-dimensional detector shot")
        start = time.perf_counter()
        try:
            prediction = self.decode_batch(array.reshape(1, -1))[0]
        except Exception as exc:  # noqa: BLE001 - reported as data
            return DetectorDecodeResult(
                prediction=0,
                runtime_seconds=time.perf_counter() - start,
                status="error",
                message=f"{type(exc).__name__}: {exc}",
            )
        return DetectorDecodeResult(
            prediction=int(prediction[0]),
            runtime_seconds=time.perf_counter() - start,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.spec.to_dict()


class PauliMWPMDecoder(PauliDecoder):
    """MWPM decoder for X-error syndromes of a Z-type-stabilizer CSS code."""

    VERSION = "1.0.0"

    def __init__(self, code: StabilizerCode, *, error_probability: float) -> None:
        if not (0.0 < error_probability < 1.0):
            raise DecoderInputError("error_probability must be in (0, 1)")
        if code.num_logical_qubits != 1:
            raise DecoderInputError("PauliMWPMDecoder currently supports k=1 codes")
        for generator in code.stabilizers:
            if generator.x != 0:
                raise DecoderInputError(
                    "PauliMWPMDecoder requires Z-type stabilizers (X-error decoding)"
                )
        pymatching = _import_pymatching()
        matrix = np.zeros((len(code.stabilizers), code.num_qubits), dtype=np.uint8)
        for row, generator in enumerate(code.stabilizers):
            for qubit in range(code.num_qubits):
                if generator.z & (1 << (code.num_qubits - 1 - qubit)):
                    matrix[row, qubit] = 1
        try:
            self.matching = pymatching.Matching.from_check_matrix(
                matrix, error_probabilities=np.full(code.num_qubits, error_probability)
            )
        except Exception as exc:  # noqa: BLE001 - surface actionable dependency error
            raise DecoderInputError(
                f"PyMatching could not build a check-matrix graph: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        self.error_probability = error_probability
        super().__init__(
            code,
            DecoderSpec(
                name="pymatching_mwpm_pauli",
                version=self.VERSION,
                decoder_type="pauli",
                supported_code_families=("repetition",),
                noise_assumptions=("independent X errors", "perfect syndrome"),
                deterministic=True,
                config={"error_probability": error_probability},
            ),
        )

    def _decode(self, syndrome: tuple[int, ...]) -> Pauli:
        correction_bits = self.matching.decode(np.asarray(syndrome, dtype=np.uint8))
        array = np.asarray(correction_bits).reshape(-1)
        if array.size != self.code.num_qubits:
            raise DecoderInputError(
                f"MWPM returned {array.size} bits, expected {self.code.num_qubits}"
            )
        x = 0
        for qubit, bit in enumerate(array.tolist()):
            if int(bit) & 1:
                x |= 1 << (self.code.num_qubits - 1 - qubit)
        return Pauli(x, 0, 0, self.code.num_qubits)


__all__ = ["DetectorMWPMDecoder", "PauliMWPMDecoder"]
