"""Stable decoder contracts and failure separation.

A decoder must not report success merely because it returned a syntactically
valid array.  The wrapper in :class:`PauliDecoder` verifies the correction's
syndrome before returning ``status="ok"``.  Decoder failure (no correction),
timeout, invalid output, invalid input, and logical failure are distinct
concepts:

* ``status="ok"``: the correction satisfies the requested syndrome.
* ``status="invalid"``: the decoder returned a correction with the wrong
  syndrome.
* ``status="timeout"``: the configured wall-clock limit was exceeded.
* ``status="error"``: the decoder raised or could not produce a correction.
* logical failure is a property of the residual error and is evaluated by
  :class:`quantumlab.research.qec.stabilizer.StabilizerCode`, never by the
  decoder itself.
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from quantumlab.research.qec.pauli import Pauli
from quantumlab.research.qec.stabilizer import StabilizerCode


class DecoderError(Exception):
    """Root of decoder failures."""


class DecoderInputError(DecoderError):
    """Raised when a syndrome or configuration is malformed."""


class DecoderUnavailableError(DecoderError):
    """Raised when an optional decoder dependency is unavailable."""


DecodeStatus = Literal["ok", "invalid", "timeout", "error"]


@dataclass(frozen=True)
class DecoderSpec:
    """Machine-readable decoder identity and assumptions."""

    name: str
    version: str
    decoder_type: Literal["pauli", "detector"]
    supported_code_families: tuple[str, ...]
    noise_assumptions: tuple[str, ...]
    deterministic: bool
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def config_hash(self) -> str:
        payload = json.dumps(
            {"name": self.name, "version": self.version, "config": self.config},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "decoder_type": self.decoder_type,
            "supported_code_families": list(self.supported_code_families),
            "noise_assumptions": list(self.noise_assumptions),
            "deterministic": self.deterministic,
            "config": dict(self.config),
            "config_hash": self.config_hash,
        }


@dataclass(frozen=True)
class PauliDecodeResult:
    """Outcome of decoding one Pauli syndrome."""

    correction: Pauli | None
    status: DecodeStatus
    runtime_seconds: float
    syndrome_valid: bool
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.syndrome_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction": None if self.correction is None else self.correction.label(),
            "status": self.status,
            "runtime_seconds": self.runtime_seconds,
            "syndrome_valid": self.syndrome_valid,
            "message": self.message,
        }


def validate_syndrome(
    syndrome: Sequence[int], expected_length: int
) -> tuple[int, ...]:
    if isinstance(syndrome, (str, bytes)):
        raise DecoderInputError("syndrome must be a sequence of bits, not text")
    values = tuple(syndrome)
    if len(values) != expected_length:
        raise DecoderInputError(
            f"syndrome length {len(values)} != expected {expected_length}"
        )
    for index, value in enumerate(values):
        if isinstance(value, bool):
            continue
        if not isinstance(value, int) or value not in (0, 1):
            raise DecoderInputError(
                f"syndrome bit {index} must be 0 or 1, got {value!r}"
            )
    return tuple(int(value) & 1 for value in values)


class PauliDecoder(ABC):
    """Base class that enforces the correction-syndrome contract."""

    def __init__(self, code: StabilizerCode, spec: DecoderSpec) -> None:
        self.code = code
        self.spec = spec

    def decode(
        self, syndrome: Sequence[int], *, timeout_seconds: float | None = None
    ) -> PauliDecodeResult:
        try:
            bits = validate_syndrome(syndrome, self.code.num_stabilizers)
        except DecoderInputError as exc:
            return PauliDecodeResult(
                correction=None,
                status="error",
                runtime_seconds=0.0,
                syndrome_valid=False,
                message=str(exc),
            )
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise DecoderInputError("timeout_seconds must be positive or None")
        start = time.perf_counter()
        try:
            correction = self._decode(bits)
        except DecoderError as exc:
            return PauliDecodeResult(
                correction=None,
                status="error",
                runtime_seconds=time.perf_counter() - start,
                syndrome_valid=False,
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - decoder failures are data, not crashes
            return PauliDecodeResult(
                correction=None,
                status="error",
                runtime_seconds=time.perf_counter() - start,
                syndrome_valid=False,
                message=f"{type(exc).__name__}: {exc}",
            )
        elapsed = time.perf_counter() - start
        if timeout_seconds is not None and elapsed > timeout_seconds:
            return PauliDecodeResult(
                correction=correction,
                status="timeout",
                runtime_seconds=elapsed,
                syndrome_valid=False,
                message=f"decoder exceeded {timeout_seconds:.6g}s",
            )
        if correction.num_qubits != self.code.num_qubits:
            return PauliDecodeResult(
                correction=correction,
                status="invalid",
                runtime_seconds=elapsed,
                syndrome_valid=False,
                message="correction has the wrong number of qubits",
            )
        valid = self.code.correction_matches_syndrome(correction, bits)
        return PauliDecodeResult(
            correction=correction,
            status="ok" if valid else "invalid",
            runtime_seconds=elapsed,
            syndrome_valid=valid,
            message="" if valid else "correction does not satisfy the syndrome",
        )

    @abstractmethod
    def _decode(self, syndrome: tuple[int, ...]) -> Pauli:
        """Return a correction Pauli for a validated syndrome."""

    def decode_batch(
        self, syndromes: Sequence[Sequence[int]], *, timeout_seconds: float | None = None
    ) -> list[PauliDecodeResult]:
        return [self.decode(syndrome, timeout_seconds=timeout_seconds) for syndrome in syndromes]


@dataclass(frozen=True)
class DetectorDecodeResult:
    """Decoded logical frame for one detector shot."""

    prediction: int
    runtime_seconds: float
    status: Literal["ok", "error"] = "ok"
    message: str = ""
