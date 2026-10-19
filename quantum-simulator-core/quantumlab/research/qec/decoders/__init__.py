"""Decoder implementations and contracts for QuantumLab QEC research."""

from quantumlab.research.qec.decoders.base import (
    DecoderError,
    DecoderInputError,
    DecoderSpec,
    DecoderUnavailableError,
    PauliDecoder,
    PauliDecodeResult,
    validate_syndrome,
)
from quantumlab.research.qec.decoders.exact import ExactDecoder, LookupDecoder
from quantumlab.research.qec.decoders.majority import RepetitionMajorityDecoder
from quantumlab.research.qec.decoders.mwpm import DetectorMWPMDecoder, PauliMWPMDecoder

__all__ = [
    "DecoderError",
    "DecoderInputError",
    "DecoderSpec",
    "DecoderUnavailableError",
    "DetectorMWPMDecoder",
    "ExactDecoder",
    "LookupDecoder",
    "PauliDecodeResult",
    "PauliDecoder",
    "PauliMWPMDecoder",
    "RepetitionMajorityDecoder",
    "validate_syndrome",
]
