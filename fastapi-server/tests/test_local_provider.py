from __future__ import annotations

import asyncio
import math

import pytest

from app.llm.base import ComplexAmplitude, ExplanationRequest
from app.llm.local_provider import LocalProvider


def _req(
    gate: str,
    state_after: list[ComplexAmplitude] | None = None,
    *,
    num_qubits: int = 1,
    qubit: int | None = 0,
    qubits: list[int] | None = None,
) -> ExplanationRequest:
    if state_after is None:
        state_after = [ComplexAmplitude(1.0, 0.0), ComplexAmplitude(0.0, 0.0)]
    return ExplanationRequest(
        gate=gate,
        num_qubits=num_qubits,
        state_before=[ComplexAmplitude(1.0, 0.0)]
        + [ComplexAmplitude(0.0, 0.0)] * (2**num_qubits - 1),
        state_after=state_after,
        qubit=qubit,
        qubits=qubits,
    )


def _collect(req: ExplanationRequest) -> str:
    provider = LocalProvider()

    async def go() -> str:
        out: list[str] = []
        async for tok in provider.stream_explanation(req):
            out.append(tok)
        return "".join(out)

    return asyncio.run(go())


HADAMARD_SUPERPOS = [
    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
]


@pytest.mark.parametrize(
    "gate, expect_keyword",
    [
        ("H", "Hadamard"),
        ("X", "NOT"),
        ("Y", "imaginary"),
        ("Z", "minus sign"),
        ("RX", "X axis"),
        ("RY", "Y axis"),
        ("RZ", "Z axis"),
        ("CNOT", "CNOT"),
        ("M", "measured"),
    ],
)
def test_each_supported_gate_has_tailored_text(gate: str, expect_keyword: str) -> None:
    if gate == "H":
        text = _collect(_req(gate, HADAMARD_SUPERPOS))
    elif gate == "CNOT":
        text = _collect(
            _req(
                gate,
                state_after=[
                    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
                    ComplexAmplitude(0.0, 0.0),
                    ComplexAmplitude(0.0, 0.0),
                    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
                ],
                num_qubits=2,
                qubit=None,
                qubits=[0, 1],
            )
        )
    else:
        text = _collect(_req(gate))
    assert expect_keyword.lower() in text.lower(), text


@pytest.mark.parametrize(
    "gate",
    ["H", "X", "Y", "Z", "RX", "RY", "RZ", "CNOT", "M"],
)
def test_under_120_words(gate: str) -> None:
    if gate == "H":
        text = _collect(_req(gate, HADAMARD_SUPERPOS))
    elif gate == "CNOT":
        text = _collect(
            _req(
                gate,
                state_after=[
                    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
                    ComplexAmplitude(0.0, 0.0),
                    ComplexAmplitude(0.0, 0.0),
                    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
                ],
                num_qubits=2,
                qubits=[0, 1],
                qubit=None,
            )
        )
    else:
        text = _collect(_req(gate))
    assert len(text.split()) < 120, f"{gate}: {len(text.split())} words"


def test_ends_with_wow_fact_for_supported_gates() -> None:
    for gate in ["H", "X", "Y", "Z", "RX", "RY", "RZ", "CNOT", "M"]:
        if gate == "CNOT":
            req = _req(
                gate,
                state_after=[
                    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
                    ComplexAmplitude(0.0, 0.0),
                    ComplexAmplitude(0.0, 0.0),
                    ComplexAmplitude(1.0 / math.sqrt(2.0), 0.0),
                ],
                num_qubits=2,
                qubits=[0, 1],
                qubit=None,
            )
        else:
            req = _req(gate, HADAMARD_SUPERPOS if gate == "H" else None)
        text = _collect(req)
        assert "Wow fact" in text, gate


def test_unknown_gate_falls_back_safely() -> None:
    text = _collect(_req("TFOLI", None, num_qubits=1))
    assert "TFOLI" in text
    assert len(text.split()) < 120


def test_deterministic_output_for_same_input() -> None:
    req = _req("H", HADAMARD_SUPERPOS)
    assert _collect(req) == _collect(req)


def test_references_state_numbers() -> None:
    req = _req("H", HADAMARD_SUPERPOS)
    text = _collect(req)
    assert "|0>" in text and "|1>" in text
    assert "50%" in text


def test_streams_word_by_word_chunks() -> None:
    provider = LocalProvider()
    req = _req("X")

    async def collect_chunks() -> list[str]:
        out: list[str] = []
        async for tok in provider.stream_explanation(req):
            out.append(tok)
        return out

    chunks = asyncio.run(collect_chunks())
    assert len(chunks) > 5
    assert all(isinstance(c, str) for c in chunks)
